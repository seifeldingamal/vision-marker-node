"""
UDP Server for Vision Marker Node
Receives and processes marker detection data from ESP32-CAM or Nicla Vision devices.
"""

import socket
import sys
import argparse
import csv
from datetime import datetime
from typing import Optional, Tuple, Dict


class MarkerUDPServer:
    """UDP server for receiving marker detection data."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 2390, 
                 buffer_size: int = 1024, timeout: float = 1.0,
                 log_file: Optional[str] = None, verbose: bool = False):
        """
        Initialize UDP server.
        
        Args:
            host: IP address to bind to (0.0.0.0 for all interfaces)
            port: UDP port to listen on
            buffer_size: UDP receive buffer size in bytes
            timeout: Socket timeout in seconds
            log_file: Path to CSV log file (None to disable logging)
            verbose: Enable verbose output
        """
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.timeout = timeout
        self.log_file = log_file
        self.verbose = verbose
        
        self.sock = None
        self.csv_writer = None
        self.csv_file = None
        self.packet_count = 0
        self.error_count = 0
        self.marker_stats: Dict[int, int] = {}
        self.last_packet_time = None
        
    def setup_socket(self) -> None:
        """Create and configure UDP socket."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(self.timeout)
        self.sock.bind((self.host, self.port))
        print(f"UDP server listening on {self.host}:{self.port}")
        
    def setup_logging(self) -> None:
        """Setup CSV logging if enabled."""
        if self.log_file:
            self.csv_file = open(self.log_file, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(['timestamp', 'marker_id', 'x', 'y', 'z', 'rotation'])
            print(f"Logging to: {self.log_file}")
            
    def parse_packet(self, data: bytes) -> Optional[Tuple[int, float, float, float, float]]:
        """
        Parse marker detection packet.
        
        Expected format: M20 <ID> X<x> Y<y> DZ<rot> Z<z>
        Example: M20 5 X0.123 Y-0.045 DZ87.3 Z1.234
        
        Args:
            data: Raw packet data
            
        Returns:
            Tuple of (marker_id, x, y, z, rotation) or None if parsing fails
        """
        try:
            packet = data.decode('utf-8').strip()
            
            if self.verbose:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Raw: {data}")
            
            parts = packet.split()
            
            # Validate packet format
            if len(parts) != 6 or parts[0] != 'M20':
                if self.verbose:
                    print(f"Invalid packet format: {packet}")
                return None
                
            # Parse components
            marker_id = int(parts[1])
            x = float(parts[2][1:])  # Remove 'X' prefix
            y = float(parts[3][1:])  # Remove 'Y' prefix
            rotation = float(parts[4][2:])  # Remove 'DZ' prefix
            z = float(parts[5][1:])  # Remove 'Z' prefix
            
            if self.verbose:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] "
                      f"Parsed: ID={marker_id}, X={x}, Y={y}, Z={z}, Rot={rotation}")
            
            return marker_id, x, y, z, rotation
            
        except (ValueError, IndexError, UnicodeDecodeError) as e:
            if self.verbose:
                print(f"Parse error: {e}")
            return None
            
    def log_marker(self, marker_id: int, x: float, y: float, z: float, rotation: float) -> None:
        """
        Log marker data to CSV file.
        
        Args:
            marker_id: Marker identifier
            x: X position in meters
            y: Y position in meters
            z: Z distance in meters
            rotation: Rotation angle in degrees
        """
        if self.csv_writer:
            timestamp = datetime.now().isoformat()
            self.csv_writer.writerow([timestamp, marker_id, x, y, z, rotation])
            self.csv_file.flush()
            
    def display_marker(self, marker_id: int, x: float, y: float, z: float, rotation: float) -> None:
        """
        Display marker data to console.
        
        Args:
            marker_id: Marker identifier
            x: X position in meters
            y: Y position in meters
            z: Z distance in meters
            rotation: Rotation angle in degrees
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] Marker {marker_id}: X={x:+.3f}m Y={y:+.3f}m Z={z:.3f}m Rot={rotation:.1f}°")
        
    def update_stats(self, marker_id: int) -> None:
        """
        Update marker statistics.
        
        Args:
            marker_id: Marker identifier
        """
        self.packet_count += 1
        self.last_packet_time = datetime.now()
        if marker_id not in self.marker_stats:
            self.marker_stats[marker_id] = 0
        self.marker_stats[marker_id] += 1
        
    def print_stats(self) -> None:
        """Print server statistics."""
        print("\n" + "="*60)
        print("Server Statistics")
        print("="*60)
        print(f"Total packets received: {self.packet_count}")
        print(f"Parse errors: {self.error_count}")
        if self.packet_count > 0:
            print(f"Success rate: {100 * (1 - self.error_count / max(1, self.packet_count)):.1f}%")
        if self.last_packet_time:
            print(f"Last packet: {self.last_packet_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.marker_stats:
            print(f"\nMarker detections:")
            for marker_id, count in sorted(self.marker_stats.items()):
                print(f"  Marker {marker_id}: {count} packets")
        else:
            print("\nNo markers detected yet.")
        print("="*60 + "\n")
        
    def run(self) -> None:
        """Run the UDP server main loop."""
        try:
            self.setup_socket()
            self.setup_logging()
            
            print("Server ready. Press Ctrl+C to stop.")
            print("Waiting for data...")
            print()
            
            timeout_counter = 0
            
            while True:
                try:
                    # Receive packet
                    data, addr = self.sock.recvfrom(self.buffer_size)
                    
                    # Reset timeout counter on successful receive
                    timeout_counter = 0
                    
                    # Show we received something
                    if self.verbose:
                        print(f"Received {len(data)} bytes from {addr}")
                    
                    # Parse packet
                    result = self.parse_packet(data)
                    
                    if result:
                        marker_id, x, y, z, rotation = result
                        
                        # Display marker data
                        self.display_marker(marker_id, x, y, z, rotation)
                        
                        # Log to CSV if enabled
                        self.log_marker(marker_id, x, y, z, rotation)
                        
                        # Update statistics
                        self.update_stats(marker_id)
                    else:
                        self.error_count += 1
                        # Print raw data on error
                        print(f"Failed to parse: {data}")
                        
                except socket.timeout:
                    # Show waiting indicator every 10 timeouts (10 seconds with 1s timeout)
                    timeout_counter += 1
                    if timeout_counter >= 10:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Still waiting for data... (check device is sending)")
                        timeout_counter = 0
                    continue
                    
        except KeyboardInterrupt:
            print("\n\nShutting down server...")
            self.print_stats()
            
        finally:
            self.cleanup()
            
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.sock:
            self.sock.close()
            print("Socket closed.")
            
        if self.csv_file:
            self.csv_file.close()
            print(f"Log file closed: {self.log_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='UDP server for Vision Marker Node detection systems',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server on default port (2390)
  python udp_server.py
  
  # Use custom port
  python udp_server.py --port 5000
  
  # Enable logging to CSV
  python udp_server.py --log markers.csv
  
  # Bind to specific interface
  python udp_server.py --host 192.168.1.100
  
  # Verbose mode with large buffer
  python udp_server.py --verbose --buffer 2048
        """
    )
    
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='IP address to bind to (default: 0.0.0.0 - all interfaces)')
    parser.add_argument('--port', type=int, default=2390,
                       help='UDP port to listen on (default: 2390)')
    parser.add_argument('--buffer', type=int, default=1024,
                       help='UDP buffer size in bytes (default: 1024)')
    parser.add_argument('--timeout', type=float, default=1.0,
                       help='Socket timeout in seconds (default: 1.0)')
    parser.add_argument('--log', type=str, default=None,
                       help='Path to CSV log file (default: disabled)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Create and run server
    server = MarkerUDPServer(
        host=args.host,
        port=args.port,
        buffer_size=args.buffer,
        timeout=args.timeout,
        log_file=args.log,
        verbose=args.verbose
    )
    
    server.run()


if __name__ == '__main__':
    main()