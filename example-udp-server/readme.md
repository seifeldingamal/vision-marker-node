# Example UDP Server

A Python reference implementation for receiving and processing marker detection data from ESP32-CAM ArUco or Nicla Vision AprilTag detection systems.

## Features

-   ✅ UDP socket server for real-time marker data reception
-   ✅ Packet parsing and validation
-   ✅ Multi-marker tracking
-   ✅ CSV data logging
-   ✅ Configurable port and IP binding
-   ✅ Statistics and performance monitoring
-   ✅ Command-line interface

## Requirements

-   **Python 3.7 or higher**
-   **Network connectivity** to ESP32-CAM or Nicla Vision device

## Quick Start

### 1. Installation

Install dependencies (Only if you need to analyze the data):

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install numpy pandas matplotlib
```

### 2. Basic Usage

Start the server on default port (2390):

```bash
python udp_server.py
```

Start on custom port:

```bash
python udp_server.py --port 5000
```

Bind to specific IP address:

```bash
python udp_server.py --host 192.168.1.100 --port 2390
```

Enable CSV logging:

```bash
python udp_server.py --log markers.csv
```

### 3. Configuration

The server automatically:

-   Binds to all network interfaces (0.0.0.0) by default
-   Listens on UDP port 2390
-   Displays incoming marker data in real-time
-   Tracks multiple markers simultaneously

## UDP Data Format

The server expects packets in the format:

```
M20 <ID> X<x_meters> Y<y_meters> DZ<rotation_deg> Z<z_meters>
```

**Example packet:**

```
M20 5 X0.123 Y-0.045 DZ87.3 Z1.234
```

**Parsed data:**

-   **Protocol**: M20
-   **Marker ID**: 5
-   **X Position**: 0.123 meters (right)
-   **Y Position**: -0.045 meters (down)
-   **Rotation**: 87.3 degrees
-   **Z Distance**: 1.234 meters

## Command-Line Options

```bash
python udp_server.py [OPTIONS]
```

| Option      | Description               | Default                    |
| ----------- | ------------------------- | -------------------------- |
| `--host`    | IP address to bind to     | `0.0.0.0` (all interfaces) |
| `--port`    | UDP port to listen on     | `2390`                     |
| `--log`     | CSV file path for logging | None (disabled)            |
| `--buffer`  | UDP buffer size in bytes  | `1024`                     |
| `--timeout` | Socket timeout in seconds | `1.0`                      |
| `--verbose` | Enable verbose output     | False                      |

**Examples:**

```bash
# Listen on specific interface
python udp_server.py --host 192.168.1.100

# Custom port with logging
python udp_server.py --port 5000 --log data.csv

# Verbose mode with large buffer
python udp_server.py --verbose --buffer 2048
```

## Output Format

### Console Output

**Normal mode:**

```
[2025-12-11 10:30:45] Marker 5: X=0.123m Y=-0.045m Z=1.234m Rot=87.3°
[2025-12-11 10:30:45] Marker 12: X=-0.456m Y=0.078m Z=2.100m Rot=45.2°
```

**Verbose mode:**

```
[2025-12-11 10:30:45.123] Raw: b'M20 5 X0.123 Y-0.045 DZ87.3 Z1.234'
[2025-12-11 10:30:45.123] Parsed: ID=5, X=0.123, Y=-0.045, Z=1.234, Rot=87.3
[2025-12-11 10:30:45.123] Marker 5: X=0.123m Y=-0.045m Z=1.234m Rot=87.3°
```

### CSV Logging

When logging is enabled, data is saved to CSV with columns:

| Column      | Description          | Units   |
| ----------- | -------------------- | ------- |
| `timestamp` | ISO 8601 timestamp   | -       |
| `marker_id` | Marker identifier    | -       |
| `x`         | Horizontal position  | meters  |
| `y`         | Vertical position    | meters  |
| `z`         | Distance from camera | meters  |
| `rotation`  | 2D rotation angle    | degrees |

**CSV example:**

```csv
timestamp,marker_id,x,y,z,rotation
2025-12-11T10:30:45.123456,5,0.123,-0.045,1.234,87.3
2025-12-11T10:30:45.234567,12,-0.456,0.078,2.100,45.2
```

## Integration Examples

### Python Script Integration

```python
import socket

def receive_markers(port=2390):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))

    while True:
        data, addr = sock.recvfrom(1024)
        packet = data.decode('utf-8').strip()

        # Parse packet: M20 <ID> X<x> Y<y> DZ<rot> Z<z>
        parts = packet.split()
        if parts[0] == 'M20':
            marker_id = int(parts[1])
            x = float(parts[2][1:])  # Remove 'X' prefix
            y = float(parts[3][1:])  # Remove 'Y' prefix
            rotation = float(parts[4][2:])  # Remove 'DZ' prefix
            z = float(parts[5][1:])  # Remove 'Z' prefix

            print(f"Marker {marker_id}: ({x}, {y}, {z}) @ {rotation}°")

if __name__ == '__main__':
    receive_markers()
```

### ROS Integration

```python
#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
import socket

def udp_to_ros():
    rospy.init_node('marker_udp_receiver')
    pub = rospy.Publisher('/marker_pose', PoseStamped, queue_size=10)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 2390))

    while not rospy.is_shutdown():
        data, addr = sock.recvfrom(1024)
        packet = data.decode('utf-8').strip()

        # Parse and publish to ROS
        # (parsing code here)

        pose = PoseStamped()
        pose.header.stamp = rospy.Time.now()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = z
        pub.publish(pose)

if __name__ == '__main__':
    udp_to_ros()
```

## Troubleshooting

### No Data Received

1. **Check firewall settings:**

    ```bash
    # Windows - Allow UDP port
    netsh advfirewall firewall add rule name="UDP 2390" dir=in action=allow protocol=UDP localport=2390

    # Linux - Allow UDP port
    sudo ufw allow 2390/udp
    ```

2. **Verify network connectivity:**

    - Ensure server and device are on same network
    - Check device UDP target IP matches server host IP
    - Ping device from server: `ping <device_ip>`

3. **Test with netcat:**

    ```bash
    # Linux/Mac - Listen on port
    nc -ul 2390

    # Should display incoming packets
    ```

4. **Check device configuration:**
    - ESP32-CAM: Verify `UDP_TARGET_IP` and `UDP_TARGET_PORT` in `config.h`
    - Nicla Vision: Verify `udp_ip` and `udp_port` in `config.json`

### Malformed Packets

1. Check packet format matches: `M20 <ID> X<x> Y<y> DZ<rot> Z<z>`
2. Verify device firmware is up to date
3. Enable verbose mode: `python udp_server.py --verbose`
4. Check for network packet corruption (increase buffer size)

### High Packet Loss

1. **Reduce device update rate:**

    - ESP32-CAM: Increase `LOOP_DELAY_MS` in `config.h`
    - Nicla Vision: Increase `loop_delay_ms` in `config.json`

2. **Increase UDP buffer:**

    ```bash
    python udp_server.py --buffer 2048
    ```

3. **Check network congestion:**
    - Use wired connection if possible
    - Reduce WiFi interference
    - Move device closer to access point

### CSV Logging Issues

1. **Check file permissions:**

    ```bash
    # Linux/Mac
    chmod 644 markers.csv
    ```

2. **Verify disk space:**

    ```bash
    df -h
    ```

3. **Use absolute paths:**
    ```bash
    python udp_server.py --log /home/user/data/markers.csv
    ```

## Performance Considerations

### Network Bandwidth

Typical bandwidth usage per marker:

-   Packet size: ~40 bytes
-   Update rate: 10-20 Hz
-   Bandwidth: ~400-800 bytes/sec per marker

For 10 markers at 20 Hz:

-   Total bandwidth: ~8 KB/sec (negligible)

### CPU Usage

Server CPU usage is minimal:

-   Parsing overhead: <1% CPU
-   Logging overhead: <2% CPU
-   Suitable for embedded systems (Raspberry Pi, etc.)

### Latency

Typical end-to-end latency:

-   Detection: 30-60 ms
-   WiFi transmission: 5-10 ms
-   Processing: <1 ms
-   **Total**: ~40-70 ms

## Advanced Usage

### Multi-Device Setup

Run multiple servers for different devices:

```bash
# Terminal 1 - ESP32-CAM on port 2390
python udp_server.py --port 2390 --log esp32_data.csv

# Terminal 2 - Nicla Vision on port 2391
python udp_server.py --port 2391 --log nicla_data.csv
```

### Data Processing Pipeline

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load logged data
df = pd.read_csv('markers.csv')

# Filter specific marker
marker_5 = df[df['marker_id'] == 5]

# Plot trajectory
plt.plot(marker_5['x'], marker_5['y'])
plt.xlabel('X Position (m)')
plt.ylabel('Y Position (m)')
plt.title('Marker 5 Trajectory')
plt.show()
```

### Real-Time Visualization

Use the server as a data source for real-time visualization tools:

-   Processing (Java)
-   p5.js (JavaScript)
-   Unity (C#)
-   Unreal Engine (C++)

## File Structure

```
example-udp-server/
├── udp_server.py         # Main server implementation
├── requirements.txt      # Python dependencies
└── readme.md            # This file
```

## References

-   [Python Socket Documentation](https://docs.python.org/3/library/socket.html)
-   [UDP Protocol](https://en.wikipedia.org/wiki/User_Datagram_Protocol)
-   [CSV Format Specification](https://tools.ietf.org/html/rfc4180)

## License

MIT License - See project LICENSE file

## Version

Current Version: 1.0  
Last Updated: December 2025
