# Nicla Vision AprilTag Detection System

A configurable AprilTag detection system for the Arduino Nicla Vision board with adaptive performance optimization, WiFi UDP transmission, and calibration support.

## Features

-   ✅ Multi-resolution support (QQVGA/QVGA/VGA)
-   ✅ Adaptive detection (automatically switches between fast/thorough modes)
-   ✅ Multi-scale processing (uses scaled-down images for efficient detection)
-   ✅ WiFi UDP transmission of pose data
-   ✅ JSON configuration system
-   ✅ Performance testing and benchmarking mode
-   ✅ Built-in focal-length calibration routine
-   ✅ Memory management with periodic garbage collection

> **Note:** SVGA and other non-standard frame sizes are generally not supported on Nicla Vision. Use QQVGA, QVGA or VGA.

## Hardware Requirements

-   **Arduino Nicla Vision board**
-   **AprilTag markers** (TAG36H11 family recommended)
-   **WiFi network** (for UDP transmission)

## Quick Start

### 1. Installation

1. Edit `config.json` with your WiFi credentials and settings
2. Copy `main.py` and `config.json` to your Nicla Vision board
3. Run `main.py` on the device (via OpenMV IDE / Run)

### 2. Configuration

Set the operating mode in `config.json`:

```json
"mode": "normal"  // Options: "normal", "debug", "calibrate"
```

**Mode descriptions:**

-   **normal** - Continuous detection with UDP transmission
-   **debug** - Performance benchmarking mode
-   **calibrate** (or **calibration**) - Run focal-length calibration routine

### 3. Camera Calibration (Recommended)

Add or update the `calibration` block in `config.json`:

```json
"calibration": {
  "profile": "qvga",             // Profile to calibrate (defaults to active_profile)
  "tag_size_m": 0.20,            // Physical tag size in meters (required)
  "distances_m": [0.5, 1.0],     // List of distances to sample for calibration
  "samples_per_distance": 10,    // Number of successful detections per distance
  "timeout_s": 15                // Per-distance timeout in seconds
}
```

**Calibration requirements:**

-   Ensure `tag_size_m` matches your physical tag size
-   Place the AprilTag at the listed distances one at a time when prompted
-   The script collects samples per distance and computes focal lengths using pinhole camera model:
    -   `focal_length = (pixel_tag_width × distance_m) / tag_size_m`
-   Results are written back to the selected profile in `config.json` as `focal_length_x` and `focal_length_y`

**How to run calibration:**

**Option A - Automatic via mode:**

-   Set `"mode": "calibrate"` in `config.json`
-   Run `main.py` - calibration executes automatically

**Option B - Manual from IDE:**

-   Call `run_calibration(cfg, profile_name, samples_per_distance, timeout_s)` directly in code

## Configuration Reference

### Resolution Profiles

Three pre-configured profiles available:

| Profile | Resolution | Use Case                   |
| ------- | ---------- | -------------------------- |
| qqvga   | 160×120    | Maximum speed, short range |
| qvga    | 320×240    | Balanced performance       |
| vga     | 640×480    | Maximum range, slower      |

Select active profile:

```json
"active_profile": "qvga"
```

Each profile includes:

-   `resolution`, `x_res`, `y_res`
-   `focal_length_x`, `focal_length_y` (calibration results stored here)
-   `fast_scale`, `thorough_scale`, `stride`, `threshold`

### AprilTag Settings

```json
"apriltag": {
  "family": "TAG36H11",
  "tag_size": 0.2,
  "refine": 0
}
```

### WiFi Configuration

```json
"wifi": {
  "ssid": "your_network",
  "password": "your_password",
  "udp_ip": "192.168.1.100",
  "udp_port": 2390
}
```

Leave `ssid` empty to disable WiFi.

### Performance Tuning

```json
"performance": {
  "gc_interval_ms": 1000,
  "print_interval_frames": 10,
  "status_interval_frames": 30,
  "loop_delay_ms": 20,
  "consecutive_detections_threshold": 5
}
```

## Operation Modes

### Normal Mode

Continuous detection, position calculation, optional UDP sending, and status prints.

### Debug Mode

Performance benchmarking:

```json
"debug": {
  "test_duration": 30,
  "test_all_profiles": true,
  "test_profile": "vga"
}
```

Set `"mode": "debug"` to enable.

### Calibration Mode

Set `"mode": "calibrate"` or `"mode": "calibration"` and configure `calibration` block. The routine:

-   Prompts for placement at each distance
-   Collects samples
-   Computes average focal lengths
-   Writes `focal_length_x` and `focal_length_y` back to chosen profile in `config.json`

## UDP Output Format

Detection data is sent as UDP packets in the format:

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

## Troubleshooting

### Frame Size Errors

-   Use QQVGA/QVGA/VGA only - SVGA typically unsupported on Nicla Vision

### No WiFi Connection

1. Verify SSID/password
2. Ensure 2.4GHz network (not 5GHz)
3. Check Serial/console for connection status

### Calibration Failures

1. Ensure good lighting and stable tag placement
2. Verify `tag_size_m` is correct
3. Increase `samples_per_distance` or `timeout_s`
4. Check tag is TAG36H11 family

### No Tags Detected

1. Check marker print quality (sharp contrast)
2. Verify marker size matches `tag_size` in config
3. Ensure marker is TAG36H11 family
4. Improve lighting conditions
5. Check console output for detection counts

### Inaccurate Positions

1. **Run calibration** (most common cause)
2. Verify physical tag size is exact
3. Ensure tag is flat (not curved)
4. Check detection distance is within supported range
5. Improve lighting (avoid shadows on tag)

## Performance Metrics

**Typical performance (QVGA, single tag):**

-   Detection time: 30-50 ms/frame
-   Loop time: 50-100 ms/frame
-   Frame rate: ~10-20 Hz
-   Detection range: 0.3m - 5.0m (varies by resolution)
-   Position accuracy: ±2-5% (after calibration)

## File Structure

```
nicla-vision-apriltag/
├── main.py                   # Main detection script
├── config.json               # Configuration file
└── readme.md                 # This file
```

## References

-   [AprilTag Documentation](https://april.eecs.umich.edu/software/apriltag)
-   [Nicla Vision Resources](https://docs.arduino.cc/hardware/nicla-vision)
-   [OpenMV Documentation](https://docs.openmv.io/)
-   [Camera Calibration Theory](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)

## License

MIT License - See project LICENSE file

## Version

Current Version: 1.0  
Last Updated: December 2025
