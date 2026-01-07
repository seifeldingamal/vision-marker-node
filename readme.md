# Vision Marker Node

A collection of optimized marker detection systems for embedded hardware, providing real-time 3D pose estimation with UDP transmission for robotics and computer vision applications.


> This project was supported and initiated by Windreiter to enable autonoumus indoor airships using just cameras and simple geo location tags. [www.windreiter.de](https://www.windreiter.com/) 

## Overview

This repository contains two marker detection implementations for different hardware platforms:

1. **ESP32-CAM ArUco Detection** - ArUco marker detection with 3D pose estimation on ESP32-CAM
2. **Nicla Vision AprilTag Detection** - AprilTag detection system for Arduino Nicla Vision
3. **Example UDP Server** - Python reference implementation for receiving and processing marker data

Both detection systems are optimized for minimal memory footprint, real-time performance, and provide UDP transmission of pose data for integration with external systems.

## Projects

### ESP32-CAM ArUco Marker Detection

Real-time ArUco marker detection and 3D pose estimation on ESP32-CAM with OV2640 camera module.

**Key Features:**

-   ✅ On-board 3D pose estimation (X, Y, Z + rotation)
-   ✅ QQVGA resolution (160×120) optimized for DRAM constraints
-   ✅ ArUco 4x4 dictionary (50 markers)
-   ✅ Built-in camera calibration tool
-   ✅ Exponential smoothing for stable output
-   ✅ Lightweight PnP solver (~2KB memory)

**Hardware:** ESP32-CAM module with OV2640 camera

[→ Full ESP32-CAM Documentation](esp32-aruco-marker/readme.md)

### Nicla Vision AprilTag Detection

Configurable AprilTag detection system with adaptive performance optimization and multi-resolution support.

**Key Features:**

-   ✅ Multi-resolution support (QQVGA/QVGA/VGA)
-   ✅ Adaptive detection modes (fast/thorough)
-   ✅ Multi-scale processing for efficiency
-   ✅ JSON configuration system
-   ✅ Built-in calibration routine
-   ✅ Performance benchmarking mode

**Hardware:** Arduino Nicla Vision board

[→ Full Nicla Vision Documentation](nicla-vision-apriltag/readme.md)

### Example UDP Server

Python reference implementation for receiving and processing marker detection data from ESP32-CAM or Nicla Vision devices.

**Key Features:**

-   ✅ UDP socket server for marker data reception
-   ✅ Packet parsing and validation
-   ✅ Real-time position tracking
-   ✅ CSV data logging
-   ✅ Configurable port and IP binding
-   ✅ Command-line interface

**Platform:** Any system with Python 3.7+

[→ Full UDP Server Documentation](example-udp-server/readme.md)

## Quick Comparison

| Feature           | ESP32-CAM        | Nicla Vision       |
| ----------------- | ---------------- | ------------------ |
| **Marker Type**   | ArUco 4x4        | AprilTag TAG36H11  |
| **Resolution**    | QQVGA (160×120)  | QQVGA/QVGA/VGA     |
| **3D Pose**       | Yes              | Yes                |
| **Frame Rate**    | ~5-10 Hz        | ~10-30 Hz (varies) |
| **Calibration**   | Built-in tool    | Built-in routine   |
| **Configuration** | config.h header | JSON config        |
| **WiFi/UDP**      | Yes              | Yes                |
| **Memory**        | ~160 KB DRAM     | ~512 KB RAM        |
| **IDE**           | Arduino IDE      | OpenMV IDE         |

## UDP Output Format

Both systems use the same UDP transmission format for consistency:

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

## Getting Started

### 1. Choose Your Hardware

-   **Budget/Simple Setup** → ESP32-CAM (~$10, single resolution)
-   **Performance/Flexibility** → Nicla Vision (~$100, multi-resolution, faster processor)

### 2. Setup Your Project

Navigate to the appropriate project folder:

```bash
# For ESP32-CAM
cd esp32-aruco-marker

# For Nicla Vision
cd nicla-vision-apriltag

# For UDP Server
cd example-udp-server
```

Follow the project-specific README for detailed setup instructions.

### 3. Calibration (Required)

Both systems require camera calibration for accurate position estimates:

-   **ESP32-CAM**: Use dedicated calibration sketch (see [calibration guide](esp32-aruco-marker/readme.md#camera-calibration-required))
-   **Nicla Vision**: Run calibration mode via JSON config (see [calibration guide](nicla-vision-apriltag/readme.md#camera-calibration-recommended))

**Why calibrate?** Each camera lens has slight variations. Without calibration, expect ±30% position error.

### 4. Configure Network

Update WiFi credentials in:

-   **ESP32-CAM**: `config.h`
-   **Nicla Vision**: `config.json`

Set UDP target IP to your computer's address (where the UDP server will run).

### 5. Setup UDP Server (Optional)

On your host computer:

```bash
cd example-udp-server
pip install -r requirements.txt
python udp_server.py --port 2390
```

### 6. Deploy

Upload firmware/code to your device and start detecting markers!

## Common Setup Steps

### Print Markers

**For ESP32-CAM (ArUco):**

-   Generator: [ArUco Generator](https://chev.me/arucogen/)
-   Dictionary: `4x4 (50 markers)`
-   Default size: **200mm × 200mm**

**For Nicla Vision (AprilTag):**

-   Generator: [AprilTag Generator](https://github.com/AprilRobotics/apriltag-imgs)
-   Family: `TAG36H11`
-   Default size: **200mm × 200mm**

**Printing tips:**

-   Use matte paper (reduce glare)
-   Ensure sharp black/white contrast
-   Mount on rigid surface (avoid warping)
-   Measure actual size with ruler

### Network Configuration

Both systems support UDP transmission to a host computer:

```
Target IP: 192.168.1.100  (your computer)
Target Port: 2390         (configurable)
```

Ensure your firewall allows UDP traffic on the configured port.

## Troubleshooting

### No Markers Detected

1. Verify marker type matches system (ArUco 4x4 vs AprilTag TAG36H11)
2. Check marker print quality (sharp contrast)
3. Confirm marker size matches config
4. Improve lighting conditions
5. Check Serial/console output for detection counts

### Inaccurate Positions

1. **Run calibration** (most common cause)
2. Verify physical marker size is exact
3. Ensure marker is flat (not curved)
4. Check detection distance is within supported range
5. Improve lighting (avoid shadows on marker)

### WiFi Connection Issues

1. Verify SSID/password
2. Ensure 2.4GHz network (not 5GHz)
3. Check device Serial/console for IP address
4. Verify UDP port is not blocked by firewall
5. **Increase WiFi connection timeout** if connection is slow/unreliable

### UDP Server Not Receiving Data

1. Check firewall settings on host computer
2. Verify UDP port matches device configuration
3. Confirm host IP address is correct in device config
4. Check devices are on same network/subnet
5. **Ensure WiFi is fully connected before devices start sending**
6. Test with `python udp_server.py` (example-udp-server folder)

### Performance Issues

1. Reduce resolution (if supported)
2. Increase loop delay / reduce update rate
3. Disable debug/status printing
4. Check for memory leaks (monitor free heap)

## Performance Characteristics

### ESP32-CAM (QQVGA)

-   Detection time: 40-60 ms/frame
-   Loop time: 50-80 ms/frame
-   Frame rate: ~5-10 Hz
-   Detection range: 0.3m - 3.0m
-   Position accuracy: ±2-5% (after calibration)

### Nicla Vision (QVGA)

-   Detection time: 30-50 ms/frame
-   Loop time: 50-100 ms/frame
-   Frame rate: ~15-30 Hz
-   Detection range: 0.3m - 5.0m (varies by resolution)
-   Position accuracy: ±2-5% (after calibration)

## Use Cases

-   **Robotics Navigation**: Real-time position tracking for mobile robots
-   **Drone Landing**: Precision landing pad detection
-   **AR Applications**: Marker-based augmented reality
-   **Industrial Automation**: Object tracking and positioning
-   **Research**: Computer vision prototyping and testing
-   **Multi-Robot Systems**: Coordinate tracking for robot swarms

## Repository Structure

```
vision-marker-node/
├── esp32-aruco-marker/       # ESP32-CAM ArUco detection
│   ├── esp32-aruco-marker.ino   # Main Arduino sketch
│   ├── calibration.ino          # Calibration sketch
│   ├── config.h                 # Configuration header
│   └── readme.md                # ESP32-CAM documentation
├── nicla-vision-apriltag/    # Nicla Vision AprilTag detection
│   ├── main.py               # Main detection script
│   ├── config.json           # Configuration file
│   └── readme.md             # Nicla Vision documentation
├── example-udp-server/       # Python UDP server example
│   ├── udp_server.py         # Server implementation
│   ├── requirements.txt      # Python dependencies
│   └── readme.md             # UDP server documentation
└── readme.md                 # This file
```


## References

-   [ArUco Documentation](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html)
-   [AprilTag Documentation](https://april.eecs.umich.edu/software/apriltag)
-   [ESP32-CAM Resources](https://randomnerdtutorials.com/esp32-cam-ai-thinker-pinout/)
-   [Nicla Vision Resources](https://docs.arduino.cc/hardware/nicla-vision)
-   [Camera Calibration Theory](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)
-   [Arduino IDE](https://www.arduino.cc/en/software)

## License

MIT License - See project LICENSE file

## Version

Current Version: 1.0  
Last Updated: December 2025
