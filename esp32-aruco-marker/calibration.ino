#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_camera.h"
#include "ArucoLite.h"
#include "config.h"
#include <math.h>

// ====================== CALIBRATION CONFIG ======================
#define CALIBRATION_DISTANCES 5  // Number of distance measurements
#define SAMPLES_PER_DISTANCE 10  // Samples to collect at each distance
#define CALIBRATION_TIMEOUT_S 30 // Timeout per distance

// Test distances in meters
const float TEST_DISTANCES[CALIBRATION_DISTANCES] = {0.5, 1.0, 1.5, 2.0, 2.5};

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

// ====================== GLOBAL OBJECTS ======================
ArucoLite<IMG_WIDTH, IMG_HEIGHT, 16, false> aruco;

struct CalibrationSample
{
    float distance_m;
    float diagonal_pixels;
    float fx_calculated;
    float fy_calculated;
};

CalibrationSample samples[CALIBRATION_DISTANCES * SAMPLES_PER_DISTANCE];
int totalSamples = 0;

// ====================== FUNCTIONS ======================

bool detectMarkerDiagonal(camera_fb_t *frame, float &diagonal_pixels, int &marker_id)
{
    // Copy frame to ArUco buffer
    for (int y = 0; y < frame->height; y++)
    {
        memcpy(aruco.frame[y], &frame->buf[y * frame->width], frame->width);
    }

    aruco.process();

    if (aruco.arucos_found == 0)
    {
        return false;
    }

    // Find marker closest to center
    int bestIdx = -1;
    float minDist = 1e9;
    float centerX = IMG_WIDTH / 2.0f;
    float centerY = IMG_HEIGHT / 2.0f;

    for (int i = 0; i < aruco.arucos_found; i++)
    {
        aruco_t &m = aruco.result[i];
        float cx = (m.pt[0].x + m.pt[1].x + m.pt[2].x + m.pt[3].x) / 4.0f;
        float cy = (m.pt[0].y + m.pt[1].y + m.pt[2].y + m.pt[3].y) / 4.0f;
        float dist = sqrtf((cx - centerX) * (cx - centerX) + (cy - centerY) * (cy - centerY));

        if (dist < minDist)
        {
            minDist = dist;
            bestIdx = i;
        }
    }

    if (bestIdx == -1)
        return false;

    aruco_t &marker = aruco.result[bestIdx];
    marker_id = marker.aruco_idx;

    // Calculate diagonal lengths (both diagonals)
    float diag1 = sqrtf(
        (marker.pt[0].x - marker.pt[2].x) * (marker.pt[0].x - marker.pt[2].x) +
        (marker.pt[0].y - marker.pt[2].y) * (marker.pt[0].y - marker.pt[2].y));
    float diag2 = sqrtf(
        (marker.pt[1].x - marker.pt[3].x) * (marker.pt[1].x - marker.pt[3].x) +
        (marker.pt[1].y - marker.pt[3].y) * (marker.pt[1].y - marker.pt[3].y));

    diagonal_pixels = (diag1 + diag2) / 2.0f;
    return true;
}

float calculateFocalLength(float diagonal_pixels, float distance_m, float marker_size_m)
{
    // Using pinhole camera model:
    // f = (diagonal_pixels * distance_m) / marker_diagonal_3d
    // where marker_diagonal_3d = sqrt(2) * marker_size

    float marker_diag_3d = sqrtf(2.0f) * marker_size_m;
    return (diagonal_pixels * distance_m) / marker_diag_3d;
}

void collectSamplesAtDistance(float distance_m)
{
    Serial.println("\n========================================");
    Serial.printf("Place marker at %.2f meters distance\n", distance_m);
    Serial.println("Marker should be:");
    Serial.println("  - Centered in camera view");
    Serial.println("  - Parallel to camera (not tilted)");
    Serial.println("  - Well lit");
    Serial.printf("\nWill collect %d samples...\n", SAMPLES_PER_DISTANCE);
    Serial.println("========================================\n");

    delay(3000); // Give user time to position marker

    int samplesCollected = 0;
    uint32_t startTime = millis();

    while (samplesCollected < SAMPLES_PER_DISTANCE)
    {
        // Check timeout
        if ((millis() - startTime) > (CALIBRATION_TIMEOUT_S * 1000))
        {
            Serial.println("TIMEOUT! Moving to next distance...");
            break;
        }

        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb)
        {
            Serial.println("Frame capture failed");
            delay(100);
            continue;
        }

        float diagonal_px;
        int marker_id;

        if (detectMarkerDiagonal(fb, diagonal_px, marker_id))
        {
            // Calculate focal lengths
            float fx = calculateFocalLength(diagonal_px, distance_m, MARKER_SIZE);
            float fy = fx; // Assume square pixels (fx = fy)

            // Store sample
            samples[totalSamples].distance_m = distance_m;
            samples[totalSamples].diagonal_pixels = diagonal_px;
            samples[totalSamples].fx_calculated = fx;
            samples[totalSamples].fy_calculated = fy;
            totalSamples++;
            samplesCollected++;

            Serial.printf("[%d/%d] ID=%d diag=%.1fpx fx=%.1f fy=%.1f\n",
                          samplesCollected, SAMPLES_PER_DISTANCE,
                          marker_id, diagonal_px, fx, fy);

            delay(200); // Small delay between samples
        }
        else
        {
            Serial.print("."); // No marker detected
        }

        esp_camera_fb_return(fb);
        delay(50);
    }

    Serial.printf("\nCollected %d samples at %.2fm\n", samplesCollected, distance_m);
}

void calculateFinalCalibration()
{
    if (totalSamples == 0)
    {
        Serial.println("\nERROR: No samples collected!");
        return;
    }

    Serial.println("\n========================================");
    Serial.println("CALIBRATION RESULTS");
    Serial.println("========================================\n");

    // Calculate statistics per distance
    Serial.println("Per-Distance Statistics:");
    Serial.println("Distance(m) | Samples | Avg fx | Avg fy | StdDev fx");
    Serial.println("-------------------------------------------------------");

    for (int d = 0; d < CALIBRATION_DISTANCES; d++)
    {
        float dist = TEST_DISTANCES[d];

        // Collect samples for this distance
        float fx_sum = 0, fy_sum = 0;
        int count = 0;

        for (int i = 0; i < totalSamples; i++)
        {
            if (fabs(samples[i].distance_m - dist) < 0.01f)
            {
                fx_sum += samples[i].fx_calculated;
                fy_sum += samples[i].fy_calculated;
                count++;
            }
        }

        if (count > 0)
        {
            float fx_avg = fx_sum / count;
            float fy_avg = fy_sum / count;

            // Calculate standard deviation
            float fx_var_sum = 0;
            for (int i = 0; i < totalSamples; i++)
            {
                if (fabs(samples[i].distance_m - dist) < 0.01f)
                {
                    float diff = samples[i].fx_calculated - fx_avg;
                    fx_var_sum += diff * diff;
                }
            }
            float fx_stddev = sqrtf(fx_var_sum / count);

            Serial.printf("   %.2f     |   %2d    | %6.1f | %6.1f | %6.2f\n",
                          dist, count, fx_avg, fy_avg, fx_stddev);
        }
    }

    // Calculate overall average
    float fx_total = 0, fy_total = 0;
    for (int i = 0; i < totalSamples; i++)
    {
        fx_total += samples[i].fx_calculated;
        fy_total += samples[i].fy_calculated;
    }
    float fx_final = fx_total / totalSamples;
    float fy_final = fy_total / totalSamples;

    // Calculate overall standard deviation
    float fx_var_sum = 0, fy_var_sum = 0;
    for (int i = 0; i < totalSamples; i++)
    {
        float fx_diff = samples[i].fx_calculated - fx_final;
        float fy_diff = samples[i].fy_calculated - fy_final;
        fx_var_sum += fx_diff * fx_diff;
        fy_var_sum += fy_diff * fy_diff;
    }
    float fx_stddev = sqrtf(fx_var_sum / totalSamples);
    float fy_stddev = sqrtf(fy_var_sum / totalSamples);

    Serial.println("\n========================================");
    Serial.println("FINAL CALIBRATION VALUES");
    Serial.println("========================================");
    Serial.printf("Total samples: %d\n", totalSamples);
    Serial.printf("\nFocal Length X (fx): %.1f ± %.1f pixels\n", fx_final, fx_stddev);
    Serial.printf("Focal Length Y (fy): %.1f ± %.1f pixels\n", fy_final, fy_stddev);
    Serial.printf("\nPrincipal Point X (cx): %.1f (image center)\n", IMG_WIDTH / 2.0f);
    Serial.printf("Principal Point Y (cy): %.1f (image center)\n", IMG_HEIGHT / 2.0f);

    Serial.println("\n========================================");
    Serial.println("UPDATE config.h WITH THESE VALUES:");
    Serial.println("========================================");
    Serial.printf("#define FOCAL_LENGTH_X %.1ff\n", fx_final);
    Serial.printf("#define FOCAL_LENGTH_Y %.1ff\n", fy_final);
    Serial.printf("#define PRINCIPAL_POINT_X %.1ff\n", IMG_WIDTH / 2.0f);
    Serial.printf("#define PRINCIPAL_POINT_Y %.1ff\n", IMG_HEIGHT / 2.0f);
    Serial.println("========================================\n");

    // Quality assessment
    float coefficient_of_variation = (fx_stddev / fx_final) * 100.0f;
    Serial.println("Calibration Quality:");
    if (coefficient_of_variation < 2.0f)
    {
        Serial.println("  ✓ EXCELLENT - Very consistent measurements");
    }
    else if (coefficient_of_variation < 5.0f)
    {
        Serial.println("  ✓ GOOD - Acceptable consistency");
    }
    else if (coefficient_of_variation < 10.0f)
    {
        Serial.println("  ⚠ FAIR - Consider recalibrating with steadier setup");
    }
    else
    {
        Serial.println("  ✗ POOR - Recalibration strongly recommended");
    }
    Serial.printf("  Coefficient of variation: %.2f%%\n", coefficient_of_variation);
}

// ====================== SETUP ======================
void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n");
    Serial.println("╔════════════════════════════════════════╗");
    Serial.println("║  ESP32-CAM CAMERA CALIBRATION TOOL     ║");
    Serial.println("╚════════════════════════════════════════╝");
    Serial.println();
    Serial.printf("Resolution: %dx%d (%s)\n", IMG_WIDTH, IMG_HEIGHT, PROFILE_NAME);
    Serial.printf("Marker size: %.3f meters (%.0f mm)\n", MARKER_SIZE, MARKER_SIZE * 1000);
    Serial.printf("Distances to test: ");
    for (int i = 0; i < CALIBRATION_DISTANCES; i++)
    {
        Serial.printf("%.1fm ", TEST_DISTANCES[i]);
    }
    Serial.println("\n");

    // Camera init
    Serial.println("Initializing camera...");
    if (esp_camera_init(&camConfig) != ESP_OK)
    {
        Serial.println("ERROR: Camera initialization failed!");
        while (true)
            delay(1000);
    }
    Serial.println("✓ Camera OK\n");

    Serial.println("========================================");
    Serial.println("CALIBRATION INSTRUCTIONS:");
    Serial.println("========================================");
    Serial.println("1. Print an ArUco marker (ID 0-49)");
    Serial.printf("2. Ensure marker is exactly %.0f mm x %.0f mm\n",
                  MARKER_SIZE * 1000, MARKER_SIZE * 1000);
    Serial.println("3. Use a ruler/tape measure for distances");
    Serial.println("4. Keep marker parallel to camera");
    Serial.println("5. Center marker in camera view");
    Serial.println("6. Ensure good lighting");
    Serial.println("========================================\n");

    Serial.println("Press any key to start calibration...");
    while (!Serial.available())
    {
        delay(100);
    }
    while (Serial.available())
        Serial.read(); // Clear buffer

    Serial.println("\nStarting calibration in 3 seconds...\n");
    delay(3000);
}

// ====================== MAIN LOOP ======================
void loop()
{
    // Collect samples at each distance
    for (int i = 0; i < CALIBRATION_DISTANCES; i++)
    {
        collectSamplesAtDistance(TEST_DISTANCES[i]);
        delay(1000);
    }

    // Calculate and display results
    calculateFinalCalibration();

    // Done - wait forever
    Serial.println("\nCalibration complete! You can now close this window.");
    Serial.println("Remember to update config.h with the new values!\n");

    while (true)
    {
        delay(10000);
    }
}