#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_camera.h"
#include "ArucoLite.h"
#include "config.h"
#include <math.h>

// ====================== CAMERA CONFIG ======================
const camera_config_t camConfig = {
    .pin_pwdn = 32,
    .pin_reset = -1,
    .pin_xclk = 0,
    .pin_sscb_sda = 26,
    .pin_sscb_scl = 27,
    .pin_d7 = 35,
    .pin_d6 = 34,
    .pin_d5 = 39,
    .pin_d4 = 36,
    .pin_d3 = 21,
    .pin_d2 = 19,
    .pin_d1 = 18,
    .pin_d0 = 5,
    .pin_vsync = 25,
    .pin_href = 23,
    .pin_pclk = 22,
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,
    .pixel_format = PIXFORMAT_GRAYSCALE,
    .frame_size = CAMERA_FRAME_SIZE,
    .jpeg_quality = 12,
    .fb_count = 1};

// ====================== DATA STRUCTURES ======================
struct Point2D
{
  float x, y;
};

struct Point3D
{
  float x, y, z;
};

struct Pose
{
  int id;
  float x_meters;
  float y_meters;
  float z_meters;
  float rotation_deg;
  uint32_t timestamp_ms;
};

// Use fixed-size array instead of deque to save heap memory
Pose poseHistory[SMOOTHING_WINDOW_SIZE];
int poseHistoryCount = 0;
int poseHistoryIdx = 0;

WiFiUDP udp;
ArucoLite<IMG_WIDTH, IMG_HEIGHT, 16, false> aruco;

// ====================== LIGHTWEIGHT PNP SOLVER ======================
class SimplePnPSolver
{
public:
  SimplePnPSolver(float fx, float fy, float cx, float cy, float marker_size)
      : fx_(fx), fy_(fy), cx_(cx), cy_(cy), half_size_(marker_size / 2.0f)
  {

    Serial.printf("PnP initialized: fx=%.1f fy=%.1f marker=%.3fm\n",
                  fx_, fy_, marker_size);
  }

  bool estimatePose(Point2D corners[4], Point3D &translation)
  {
    // Convert to normalized camera coordinates
    Point2D norm[4];
    for (int i = 0; i < 4; i++)
    {
      norm[i].x = (corners[i].x - cx_) / fx_;
      norm[i].y = (corners[i].y - cy_) / fy_;
    }

    // Estimate Z from marker apparent size
    float diag1 = sqrtf((norm[0].x - norm[2].x) * (norm[0].x - norm[2].x) +
                        (norm[0].y - norm[2].y) * (norm[0].y - norm[2].y));
    float diag2 = sqrtf((norm[1].x - norm[3].x) * (norm[1].x - norm[3].x) +
                        (norm[1].y - norm[3].y) * (norm[1].y - norm[3].y));

    float avg_diag = (diag1 + diag2) / 2.0f;
    if (avg_diag < 0.001f)
      return false;

    float marker_diag_3d = sqrtf(2.0f) * (half_size_ * 2.0f);
    translation.z = marker_diag_3d / avg_diag;

    // Estimate X, Y from center position
    float cx = (norm[0].x + norm[1].x + norm[2].x + norm[3].x) / 4.0f;
    float cy = (norm[0].y + norm[1].y + norm[2].y + norm[3].y) / 4.0f;

    translation.x = cx * translation.z;
    translation.y = cy * translation.z;

    return true;
  }

private:
  float fx_, fy_, cx_, cy_, half_size_;
};

SimplePnPSolver pnpSolver(FOCAL_LENGTH_X, FOCAL_LENGTH_Y,
                          PRINCIPAL_POINT_X, PRINCIPAL_POINT_Y,
                          MARKER_SIZE);

// ====================== FUNCTION DECLARATIONS ======================
Pose detectMarkerPose(camera_fb_t *frame);
Pose smoothPose();
void sendUDP(Pose p);
float getAngle(Point2D a, Point2D b, Point2D c);

// ====================== SETUP ======================
void setup()
{
  Serial.begin(115200);
  delay(500);

  Serial.println("\n=== ESP32-CAM ArUco 3D Pose Detection ===");
  Serial.printf("Resolution: %s (%dx%d)\n", PROFILE_NAME, IMG_WIDTH, IMG_HEIGHT);
  Serial.printf("Marker size: %.3f meters\n", MARKER_SIZE);
  Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());

  // Camera init
  if (esp_camera_init(&camConfig) != ESP_OK)
  {
    Serial.println("ERROR: Camera init failed!");
    while (true)
      delay(1000);
  }
  Serial.println("Camera OK");

  // WiFi init
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20)
  {
    delay(1000);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.printf("\nWiFi connected: %s\n", WiFi.localIP().toString().c_str());
    udp.begin(UDP_TARGET_PORT);
    Serial.println("UDP ready");
  }
  else
  {
    Serial.println("\nWiFi connection failed!");
  }

  Serial.printf("Free heap after init: %d bytes\n", ESP.getFreeHeap());
  Serial.println("System ready!\n");
}

// ====================== MAIN LOOP ======================
void loop()
{
  uint32_t loop_start = millis();

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb)
  {
    Serial.println("Frame capture failed");
    delay(100);
    return;
  }

  Pose current = detectMarkerPose(fb);

  if (current.id != -1)
  {
    // Add to circular buffer
    poseHistory[poseHistoryIdx] = current;
    poseHistoryIdx = (poseHistoryIdx + 1) % SMOOTHING_WINDOW_SIZE;
    if (poseHistoryCount < SMOOTHING_WINDOW_SIZE)
    {
      poseHistoryCount++;
    }

    Pose smoothed = smoothPose();
    sendUDP(smoothed);
  }

  esp_camera_fb_return(fb);

  uint32_t loop_time = millis() - loop_start;
  Serial.printf("Loop: %u ms | Heap: %d\n\n", loop_time, ESP.getFreeHeap());

  delay(LOOP_DELAY_MS);
}

// ====================== POSE DETECTION ======================
Pose detectMarkerPose(camera_fb_t *frame)
{
  Pose result = {-1, 0, 0, 0, 0, millis()};

  // Copy frame to ArUco buffer
  for (int y = 0; y < frame->height; y++)
  {
    memcpy(aruco.frame[y], &frame->buf[y * frame->width], frame->width);
  }

  aruco.process();

  if (aruco.arucos_found > 0)
  {
    // Find marker closest to center
    int bestIdx = -1;
    float minDist = 1e9;
    Point2D center = {IMG_WIDTH / 2.0f, IMG_HEIGHT / 2.0f};

    for (int i = 0; i < aruco.arucos_found; i++)
    {
      aruco_t &m = aruco.result[i];
      float cx = (m.pt[0].x + m.pt[1].x + m.pt[2].x + m.pt[3].x) / 4.0f;
      float cy = (m.pt[0].y + m.pt[1].y + m.pt[2].y + m.pt[3].y) / 4.0f;
      float dist = sqrtf((cx - center.x) * (cx - center.x) +
                         (cy - center.y) * (cy - center.y));

      if (dist < minDist)
      {
        minDist = dist;
        bestIdx = i;
      }
    }

    if (bestIdx != -1)
    {
      aruco_t &marker = aruco.result[bestIdx];
      result.id = marker.aruco_idx;

      Point2D corners[4];
      for (int i = 0; i < 4; i++)
      {
        corners[i].x = marker.pt[i].x;
        corners[i].y = marker.pt[i].y;
      }

      Point3D trans;
      if (pnpSolver.estimatePose(corners, trans))
      {
        result.x_meters = trans.x;
        result.y_meters = trans.y;
        result.z_meters = trans.z;

        // Calculate 2D rotation
        Point2D ref = {-500, marker.pt[0].y};
        result.rotation_deg = getAngle(
            {marker.pt[0].x, marker.pt[0].y},
            {marker.pt[1].x, marker.pt[1].y},
            ref);

        Serial.printf("ID=%d X=%.3f Y=%.3f Z=%.3f R=%.1f\n",
                      result.id, result.x_meters, result.y_meters,
                      result.z_meters, result.rotation_deg);
      }
    }
  }

  return result;
}

// ====================== SMOOTHING ======================
Pose smoothPose()
{
  if (poseHistoryCount == 0)
    return {-1};

  Pose avg = {0};
  float totalWeight = 0;

  // Exponential weights: newest = highest weight
  for (int i = 0; i < poseHistoryCount; i++)
  {
    int idx = (poseHistoryIdx - 1 - i + SMOOTHING_WINDOW_SIZE) % SMOOTHING_WINDOW_SIZE;
    float weight = 1.0f / (i + 1); // Simple exponential decay

    const Pose &p = poseHistory[idx];
    avg.x_meters += p.x_meters * weight;
    avg.y_meters += p.y_meters * weight;
    avg.z_meters += p.z_meters * weight;
    avg.rotation_deg += p.rotation_deg * weight;
    avg.id = p.id;
    totalWeight += weight;
  }

  // Normalize
  avg.x_meters /= totalWeight;
  avg.y_meters /= totalWeight;
  avg.z_meters /= totalWeight;
  avg.rotation_deg /= totalWeight;

  int lastIdx = (poseHistoryIdx - 1 + SMOOTHING_WINDOW_SIZE) % SMOOTHING_WINDOW_SIZE;
  avg.timestamp_ms = poseHistory[lastIdx].timestamp_ms;

  return avg;
}

// ====================== UDP SENDER ======================
void sendUDP(Pose p)
{
  String msg = "M20 " + String(p.id) +
               " X" + String(p.x_meters, 3) +
               " Y" + String(p.y_meters, 3) +
               " DZ" + String(p.rotation_deg, 1) +
               " Z" + String(p.z_meters, 3);

  udp.beginPacket(UDP_TARGET_IP, UDP_TARGET_PORT);
  udp.print(msg);
  udp.endPacket();

  Serial.println("UDP: " + msg);
}

// ====================== UTILITY ======================
float getAngle(Point2D a, Point2D b, Point2D c)
{
  float ang = atan2f(c.y - b.y, c.x - b.x) - atan2f(a.y - b.y, a.x - b.x);
  ang = ang * 180.0f / PI;
  return ang < 0 ? ang + 360.0f : ang;
}