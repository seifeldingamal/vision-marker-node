#ifndef CONFIG_H
#define CONFIG_H

// ====================== RESOLUTION ======================
// QQVGA is the ONLY resolution that fits in ESP32 DRAM
#define IMG_WIDTH 160
#define IMG_HEIGHT 120
#define CAMERA_FRAME_SIZE FRAMESIZE_QQVGA

// ====================== CAMERA CALIBRATION ======================
// These are placeholder values - YOU MUST CALIBRATE for your specific camera!
// To calibrate:
//   1. Place a 0.2m marker at exactly 1.0m distance
//   2. Measure diagonal in pixels from detection
//   3. Calculate: focal_length = (diagonal_pixels * 1.0) / (0.2 * sqrt(2))
//   4. Update these values

#define FOCAL_LENGTH_X 120.0f   // fx in pixels (CALIBRATE!)
#define FOCAL_LENGTH_Y 120.0f   // fy in pixels (CALIBRATE!)
#define PRINCIPAL_POINT_X 80.0f // cx - optical center X (IMG_WIDTH/2)
#define PRINCIPAL_POINT_Y 60.0f // cy - optical center Y (IMG_HEIGHT/2)

// ====================== NETWORK ======================
#define WIFI_SSID "SSID"
#define WIFI_PASSWORD "PASSWORD"
#define UDP_TARGET_IP "00.000.00.000"
#define UDP_TARGET_PORT 2390

// ====================== MARKER SETTINGS ======================
#define MARKER_SIZE 0.2f          // Physical marker size in meters
#define ARUCO_DICTIONARY "4X4_50" // ArUco dictionary type

// ====================== POSE ESTIMATION ======================
// Smoothing window (reduce if memory is tight)
#define SMOOTHING_WINDOW_SIZE 3 // Reduced from 5 to save memory

// PnP solver settings
#define USE_ITERATIVE_PNP true // set to false to save computation time
#define PNP_MAX_ITERATIONS 2   // Only used if iterative is enabled
#define PNP_CONVERGENCE_THRESHOLD 1.0f

// Lens distortion (set to 0 if uncalibrated)
#define DISTORTION_K1 0.0f
#define DISTORTION_K2 0.0f

// ====================== PERFORMANCE ======================
#define LOOP_DELAY_MS 50 // ~20 Hz update rate
#define PROFILE_NAME "QQVGA-160x120"

#endif // CONFIG_H