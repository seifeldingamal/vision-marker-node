# ESP32-CAM ArUco 3D Pose Detection

Real-time ArUco marker detection and 3D pose estimation on ESP32-CAM with OV2640 camera module. Optimized for minimal memory footprint and maximum performance.

## Features

-   ✅ On-board 3D pose estimation (X, Y, Z position + rotation)
-   ✅ UDP transmission of pose data
-   ✅ QQVGA resolution (160×120) for DRAM compatibility
-   ✅ Exponential smoothing for stable pose output
-   ✅ ArUco 4x4 dictionary (50 markers)
-   ✅ Built-in camera calibration tool
-   ✅ Lightweight PnP solver (~2KB memory)

## Hardware Requirements

-   **ESP32-CAM module** with OV2640 camera
-   **ArUco markers** (4x4 dictionary, IDs 0-49)
-   Printed markers should be **exactly 200mm × 200mm** (configurable in `config.h`)
-   WiFi network for UDP transmission
-   **FTDI USB-to-Serial adapter** or **ESP32-CAM-MB programmer** for uploading

## Quick Start

### 1. Arduino IDE Setup

1.  **Install Arduino IDE** (version 1.8.19 or newer, or Arduino IDE 2.x)
    -   Download from: https://www.arduino.cc/en/software

2.  **Add ESP32 Board Support:**
    -   Open Arduino IDE
    -   Go to `File > Preferences`
    -   Add to "Additional Board Manager URLs":
        ```
        https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
        ```
    -   Go to `Tools > Board > Boards Manager`
    -   Search for "esp32" and install "esp32 by Espressif Systems"

3.  **Install ArUcoLite Library:**
    -   Download from: https://github.com/cyberreefguru/ArucoLite
    -   Extract to your Arduino `libraries` folder
    -   Or use `Sketch > Include Library > Add .ZIP Library`

4.  **Select Board:**
    -   Go to `Tools > Board > ESP32 Arduino`
    -   Select "AI Thinker ESP32-CAM"

5.  **Configure Upload Settings:**
    -   `Tools > Upload Speed`: 115200
    -   `Tools > Flash Frequency`: 80MHz
    -   `Tools > Partition Scheme`: Huge APP (3MB No OTA)

### 2. Hardware Setup

1.  Connect ESP32-CAM to MB Programmer

2.  Print ArUco markers from [ArUco Generator](https://chev.me/arucogen/)
    -   Dictionary: `4x4 (50 markers)`
    -   Marker size: **200mm × 200mm** (or update `MARKER_SIZE` in `config.h`)

### 3. Configuration

Edit `config.h`:

```cpp
// Network settings
#define WIFI_SSID "YourNetwork"
#define WIFI_PASSWORD "YourPassword"
#define UDP_TARGET_IP "192.168.1.100"  // Computer receiving pose data
#define UDP_TARGET_PORT 2390

// WiFi connection timeout
#define WIFI_TIMEOUT_S 20  // Increase if WiFi is slow to connect

// Marker physical size (meters)
#define MARKER_SIZE 0.2f  // 200mm marker
```

### 4. Upload Sketch

1.  Open `esp32-aruco-marker.ino` in Arduino IDE
2.  Verify configuration in `config.h`
3.  Click **Upload** button
4.  Wait for "Done uploading" message
5.  Disconnect **IO0** from **GND**
6.  Press **Reset** button on ESP32-CAM
7.  Open **Serial Monitor** (115200 baud) to verify operation

### 5. Camera Calibration (Required)

**Why calibrate?** Each OV2640 lens varies slightly in focal length. Without calibration, position estimates will be inaccurate (±30% error typical).

#### Method 1: Automatic Calibration (Recommended)

1.  Upload the `calibration.ino` sketch to your ESP32-CAM

2.  Run calibration routine:
    -   Place marker at **exactly** 0.5m, 1.0m, 1.5m, 2.0m, 2.5m, 3m (Might be too much with QQVGA)
    -   Tool collects 10 samples per distance
    -   Outputs calibrated focal lengths to Serial Monitor

3.  Copy values to `config.h`:

    ```cpp
    #define FOCAL_LENGTH_X 120.5f  // Replace with calibration output
    #define FOCAL_LENGTH_Y 120.5f  // Replace with calibration output
    ```

4.  Upload the main `esp32-aruco-marker.ino` sketch again

#### Method 2: Manual Calibration

1.  Place 200mm marker at **exactly 1.0 meter** distance
2.  Run detection and measure diagonal in pixels from Serial output
3.  Calculate: `focal_length = (diagonal_pixels × 1.0) / (0.2 × √2)`
4.  Update `FOCAL_LENGTH_X` and `FOCAL_LENGTH_Y` in `config.h`

**Typical values for OV2640 at QQVGA (160×120):**

-   `FOCAL_LENGTH_X`: 110-130 pixels
-   `FOCAL_LENGTH_Y`: 110-130 pixels

## UDP Output Format

```
M20 <ID> X<x_meters> Y<y_meters> DZ<rotation_deg> Z<z_meters>
```

**Example:**

```
M20 5 X0.123 Y-0.045 DZ87.3 Z1.234
```

**Coordinate System:**

-   **X**: Right (+) / Left (-)
-   **Y**: Up (+) / Down (-)
-   **Z**: Distance from camera (always positive)
-   **DZ**: 2D rotation angle (0-360°)

## Configuration Reference

### Resolution Settings

| Profile | Resolution | Status     | Notes                   |
| ------- | ---------- | ---------- | ----------------------- |
| QQVGA   | 160×120    | ✅ Working | **Only supported size** |
| QVGA    | 320×240    | ❌ OOM     | Exceeds ESP32 DRAM      |
| VGA     | 640×480    | ❌ OOM     | Exceeds ESP32 DRAM      |

**Why only QQVGA?** ArUco detection requires full frame buffer in DRAM. Higher resolutions cause out-of-memory errors.

### Performance Tuning

In `config.h`:

```cpp
// Smoothing (trades latency for stability)
#define SMOOTHING_WINDOW_SIZE 3  // 3-5 recommended

// Update rate
#define LOOP_DELAY_MS 50  // 20 Hz (decrease for faster updates)

// PnP solver
#define USE_ITERATIVE_PNP false  // Keep false (saves 200ms/frame)

// WiFi timeout
#define WIFI_TIMEOUT_S 20  // Increase if connection is slow
```

### Memory Budget

```
Total DRAM: 160 KB
- Frame buffer: 19.2 KB (160×120×1 byte)
- ArUco detection: ~50 KB
- WiFi/UDP stack: ~40 KB
- Application: ~30 KB
Remaining: ~20 KB margin
```

## Camera Specifications

**OV2640 Module (Standard ESP32-CAM lens)**

| Parameter       | Value                                |
| --------------- | ------------------------------------ |
| Sensor          | OV2640 CMOS                          |
| Lens FOV        | ~66° diagonal (typical)              |
| Focus           | Fixed focus (30cm to infinity)       |
| Resolution      | QQVGA (160×120) grayscale            |
| Frame rate      | ~5-10 FPS                            |
| Detection range | 0.3m - 3.0m (depends on marker size) |

**Optimal detection conditions:**

-   Marker fills 20-80% of frame
-   Good lighting (avoid shadows on marker)
-   Marker parallel to camera (±15° tilt OK)
-   Marker centered in view (detection prioritizes center)

## Troubleshooting

### Upload Issues

**"Failed to connect to ESP32":**

1.  Ensure **IO0** is connected to **GND** during upload
2.  Check FTDI connections (TX↔RX are crossed)
3.  Try pressing **Reset** button while uploading starts
4.  Verify correct COM port selected in Arduino IDE
5.  Try lower upload speed (57600 baud)

**"Brownout detector was triggered":**

1.  Use external 5V power supply (not USB power)
2.  FTDI adapter may not provide enough current
3.  Consider using ESP32-CAM-MB programmer board

### No Markers Detected

1.  Check marker print quality (sharp black/white contrast)
2.  Verify marker size matches `MARKER_SIZE` in `config.h`
3.  Ensure marker is 4x4 dictionary (not 5x5 or 6x6)
4.  Improve lighting
5.  Check Serial Monitor for `arucos_found > 0`

### Inaccurate Position Estimates

1.  **Run calibration!** Uncalibrated cameras have ±30% error
2.  Verify marker size is exact (measure with ruler)
3.  Check marker is flat (not warped/curved)
4.  Ensure distance is within 0.3m - 3.0m range

### WiFi Connection Fails

1.  Check SSID/password in `config.h`
2.  Verify 2.4GHz WiFi (ESP32 doesn't support 5GHz)
3.  **Increase `WIFI_TIMEOUT_S` to 20-30 seconds**
4.  Check Serial Monitor for IP address
5.  Ensure UDP port isn't blocked by firewall
6.  Try moving closer to WiFi router

### Out of Memory Errors

1.  Only QQVGA resolution is supported
2.  Reduce `SMOOTHING_WINDOW_SIZE` to 2-3
3.  Check for memory leaks with `ESP.getFreeHeap()` in Serial Monitor

### Jittery/Unstable Pose

1.  Increase `SMOOTHING_WINDOW_SIZE` to 5
2.  Improve lighting (shadows cause detection noise)
3.  Stabilize camera mount (vibration amplifies noise)
4.  Use larger markers (better detection accuracy)

## Performance Metrics

**Typical performance (QQVGA, single marker):**

-   Detection time: 40-60 ms/frame
-   Total loop time: 50-80 ms/frame
-   Effective rate: ~15-20 Hz
-   Heap usage: ~25-30 KB free

**Detection accuracy (after calibration):**

-   Position (X, Y): ±2-5% at 1m distance
-   Depth (Z): ±3-8% at 1m distance
-   Rotation: ±2-5°

## File Structure

```
esp32-aruco-marker/
├── esp32-aruco-marker.ino   # Main detection sketch
├── calibration.ino          # Camera calibration sketch
├── config.h                 # Configuration parameters
└── readme.md                # This file
```

## Required Libraries

-   **ESP32 Board Support** (by Espressif Systems)
-   **ArUcoLite** - Lightweight ArUco detection library
    -   GitHub: https://github.com/cyberreefguru/ArucoLite
    -   Must be installed manually to the Arduino IDE

## References

-   [ArUco Documentation](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html)
-   [ArUcoLite Library](https://github.com/cyberreefguru/ArucoLite)
-   [ESP32-CAM Pinout](https://randomnerdtutorials.com/esp32-cam-ai-thinker-pinout/)
-   [ESP32 Arduino Core](https://github.com/espressif/arduino-esp32)
-   [Camera Calibration Theory](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)

## License

MIT License - See project LICENSE file

## Version

Current Version: 1.0  
Last Updated: December 2025
