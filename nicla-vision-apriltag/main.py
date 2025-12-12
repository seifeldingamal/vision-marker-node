# Nicla Vision AprilTag Detection System - Configurable
import sensor
import image
import time
import gc
import machine
import ujson

# ==================== CONFIGURATION LOADER ====================
class ConfigLoader:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.profile = self.config['profiles'][self.config['active_profile']]

    def load_config(self, filename):
        """Load configuration from JSON file"""
        try:
            with open(filename) as f:
                return ujson.load(f)
        except Exception as e:
            print("Error loading config:", e)
            print("Using default QVGA configuration")
            return self.get_default_config()

    def get_default_config(self):
        """Fallback default configuration"""
        return {
            "active_profile": "qvga",
            "profiles": {
                "qvga": {
                    "resolution": "QVGA",
                    "x_res": 320,
                    "y_res": 240,
                    "focal_length_x": 450,
                    "focal_length_y": 450,
                    "fast_scale": 0.5,
                    "thorough_scale": 0.25,
                    "stride": 6,
                    "threshold": 100
                }
            },
            "apriltag": {"family": "TAG36H11", "tag_size": 0.20, "refine": 0},
            "wifi": {"ssid": "", "password": "", "udp_ip": "", "udp_port": 2390},
            "performance": {
                "gc_interval_ms": 1000,
                "print_interval_frames": 10,
                "status_interval_frames": 30,
                "loop_delay_ms": 20,
                "consecutive_detections_threshold": 5
            }
        }

# ==================== CAMERA INITIALIZER ====================
def initialize_camera(config):
    """Initialize camera with config settings"""
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)

    resolution = config.profile['resolution']
    if resolution == "QVGA":
        sensor.set_framesize(sensor.QVGA)
    elif resolution == "VGA":
        sensor.set_framesize(sensor.VGA)
    elif resolution == "QQVGA":
        sensor.set_framesize(sensor.QQVGA)
    else:
        print("Unknown resolution, defaulting to QVGA")
        sensor.set_framesize(sensor.QVGA)

    sensor.skip_frames(time=2000)
    print("Camera initialized: {}".format(resolution))

# ==================== APRIL TAG DETECTOR ====================
class AprilTagDetector:
    def __init__(self, config):
        self.config = config
        self.profile = config.profile
        self.apriltag_config = config.config['apriltag']
        self.perf_config = config.config['performance']

        self.cx = self.profile['x_res'] // 2
        self.cy = self.profile['y_res'] // 2
        self.consecutive_detections = 0
        self.use_fast_mode = False

        # Get tag family
        family_name = self.apriltag_config['family']
        self.tag_family = getattr(image, family_name, image.TAG36H11)

    def perform_coarse_search(self, img, scale):
        """Perform AprilTag detection on a scaled-down image"""
        coarse_img = img.scale(x_scale=scale, y_scale=scale,
                              hint=image.BILINEAR, copy=True)

        tag_list = coarse_img.find_apriltags(
            families=self.tag_family,
            fx=self.profile['focal_length_x'] * scale,
            fy=self.profile['focal_length_y'] * scale,
            cx=self.cx * scale,
            cy=self.cy * scale,
            tag_size=self.apriltag_config['tag_size'],
            stride=self.profile['stride'],
            threshold=self.profile['threshold'],
            refine=self.apriltag_config['refine']
        )

        return tag_list

    def detect_tags(self, img):
        """Multi-scale AprilTag detection with adaptive mode"""
        if self.use_fast_mode:
            scale = self.profile['fast_scale']
            tag_list = self.perform_coarse_search(img, scale)

            if not tag_list:
                self.use_fast_mode = False
                self.consecutive_detections = 0
                return self.detect_tags(img)
        else:
            # Try fast scale first
            scale = self.profile['fast_scale']
            tag_list = self.perform_coarse_search(img, scale)

            # Fall back to thorough scale if needed
            if not tag_list:
                scale = self.profile['thorough_scale']
                tag_list = self.perform_coarse_search(img, scale)

            # Enable fast mode after consistent detection
            if tag_list:
                self.consecutive_detections += 1
                threshold = self.perf_config['consecutive_detections_threshold']
                if self.consecutive_detections > threshold:
                    self.use_fast_mode = True
            else:
                self.consecutive_detections = 0

        # Scale coordinates back to full resolution
        scaling_factor = 1.0 / scale

        scaled_tags = []
        for tag in tag_list:
            scaled_tag = {
                'id': tag.id,
                'cx': tag.cx * scaling_factor,
                'cy': tag.cy * scaling_factor,
                'x': tag.x * scaling_factor,
                'y': tag.y * scaling_factor,
                'w': tag.w * scaling_factor,
                'h': tag.h * scaling_factor,
                'x_translation': tag.x_translation,
                'y_translation': tag.y_translation,
                'z_translation': tag.z_translation,
                'x_rotation': tag.x_rotation,
                'y_rotation': tag.y_rotation,
                'z_rotation': tag.z_rotation,
                'rotation': tag.rotation,
                'decision_margin': tag.decision_margin
            }
            scaled_tags.append(scaled_tag)

        return scaled_tags

    def find_centered_tag(self, tags):
        """Find the tag closest to the image center"""
        if not tags:
            return None

        best_tag = None
        best_dist = float('inf')

        for tag in tags:
            dx = tag['cx'] - self.cx
            dy = tag['cy'] - self.cy
            dist = dx*dx + dy*dy

            if dist < best_dist:
                best_dist = dist
                best_tag = tag

        return best_tag

# ==================== POSITION CALCULATOR ====================
class PositionCalculator:
    def calculate_relative_data(self, tag):
        """Calculate relative position data"""
        if tag is None:
            return None

        try:
            return {
                'id': tag['id'],
                'x_trans': tag['x_translation'],
                'y_trans': tag['y_translation'],
                'z_trans': tag['z_translation'],
                'x_rot': tag['x_rotation'],
                'y_rot': tag['y_rotation'],
                'z_rot': tag['z_rotation'],
                'rotation': tag['rotation'],
                'cx': tag['cx'],
                'cy': tag['cy'],
                'width': tag['w'],
                'height': tag['h'],
                'decision_margin': tag['decision_margin']
            }
        except Exception as e:
            print("Data extraction error:", e)
            return None

# ==================== DATA SENDER ====================
class DataSender:
    def __init__(self, config):
        self.wifi_config = config.config['wifi']
        self.sock = None
        self.send_errors = 0
        self.init_wifi()

    def init_wifi(self):
        """Initialize WiFi connection"""
        if not self.wifi_config['ssid']:
            print("WiFi not configured, skipping...")
            return

        import network
        import usocket

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.wifi_config['ssid'], self.wifi_config['password'])

        print("Connecting to WiFi...")
        timeout = 60
        while not wlan.isconnected() and timeout > 0:
            time.sleep_ms(2000)
            timeout -= 1

        if not wlan.isconnected():
            print("WiFi connection failed!")
            return

        print("Connected:", wlan.ifconfig())
        self.sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
        self.sock.setblocking(False)

    def send_raw_data(self, data):
        """Send raw tag data via UDP"""
        if not self.sock:
            return "No WiFi"

        message = "M20 {} X{:.3f} Y{:.3f} DZ{:.1f} Z{:.3f} ".format(
            data['id'],
            data['x_trans'],
            data['y_trans'],
            data['rotation'],
            data['z_trans'],
        )

        try:
            self.sock.sendto(message.encode(),
                           (self.wifi_config['udp_ip'],
                            self.wifi_config['udp_port']))
            self.send_errors = 0
            return message
        except OSError as e:
            self.send_errors += 1
            if self.send_errors % 10 == 0:
                print("UDP send error:", e)
            return "Send failed"
        
# ==================== PERFORMANCE TEST ====================
class PerformanceTest:
    def __init__(self):
        self.results = {}
        
    def test_profile(self, profile_name, duration_seconds=30):
        """Test a specific profile for a given duration"""
        print("\n" + "="*50)
        print("Testing profile: {}".format(profile_name))
        print("="*50)
        
        # Load config and set active profile
        config = ConfigLoader()
        config.config['active_profile'] = profile_name
        config.profile = config.config['profiles'][profile_name]
        
        # Initialize camera with new profile
        initialize_camera(config)
        
        # Initialize detector
        detector = AprilTagDetector(config)
        calculator = PositionCalculator()
        
        # Test metrics
        clock = time.clock()
        frame_count = 0
        detection_count = 0
        total_detection_time = 0
        fps_samples = []
        
        start_time = time.ticks_ms()
        last_gc = start_time
        
        print("Starting {} second test...".format(duration_seconds))
        
        while time.ticks_diff(time.ticks_ms(), start_time) < duration_seconds * 1000:
            # Periodic garbage collection
            current_time = time.ticks_ms()
            if time.ticks_diff(current_time, last_gc) > 1000:
                gc.collect()
                last_gc = current_time
            
            clock.tick()
            frame_count += 1
            
            try:
                # Capture and process frame
                img = sensor.snapshot()
                
                detection_start = time.ticks_ms()
                tags = detector.detect_tags(img)
                detection_time = time.ticks_diff(time.ticks_ms(), detection_start)
                
                total_detection_time += detection_time
                
                if tags:
                    detection_count += 1
                    centered_tag = detector.find_centered_tag(tags)
                    
                    if centered_tag:
                        raw_data = calculator.calculate_relative_data(centered_tag)
                        
                        # Visual feedback
                        img.draw_rectangle(
                            int(centered_tag['x']),
                            int(centered_tag['y']),
                            int(centered_tag['w']),
                            int(centered_tag['h']),
                            color=255
                        )
                
                # Record FPS every 10 frames
                if frame_count % 10 == 0:
                    fps = clock.fps()
                    fps_samples.append(fps)
                    print("Frame {}: {:.1f} FPS, {} detections, Mode: {}".format(
                        frame_count, fps, detection_count,
                        "FAST" if detector.use_fast_mode else "FULL"))
                
            except Exception as e:
                print("Error during test:", e)
                time.sleep_ms(100)
            
            time.sleep_ms(20)
            machine.idle()
        
        # Calculate results
        avg_fps = sum(fps_samples) / len(fps_samples) if fps_samples else 0
        detection_rate = (detection_count / frame_count * 100) if frame_count > 0 else 0
        avg_detection_time = total_detection_time / frame_count if frame_count > 0 else 0
        
        results = {
            'profile': profile_name,
            'resolution': "{}x{}".format(config.profile['x_res'], config.profile['y_res']),
            'total_frames': frame_count,
            'detections': detection_count,
            'detection_rate': detection_rate,
            'avg_fps': avg_fps,
            'avg_detection_ms': avg_detection_time,
            'free_memory': gc.mem_free()
        }
        
        self.results[profile_name] = results
        
        # Print summary
        print("\n--- Test Summary ---")
        print("Profile: {}".format(profile_name))
        print("Resolution: {}".format(results['resolution']))
        print("Total Frames: {}".format(results['total_frames']))
        print("Detections: {} ({:.1f}%)".format(results['detections'], results['detection_rate']))
        print("Average FPS: {:.2f}".format(results['avg_fps']))
        print("Avg Detection Time: {:.2f} ms".format(results['avg_detection_ms']))
        print("Free Memory: {} bytes".format(results['free_memory']))
        
        return results
    
    def run_all_tests(self, duration_per_test=30):
        """Run tests on all available profiles"""
        config = ConfigLoader()
        profiles = list(config.config['profiles'].keys())
        
        print("\n" + "="*50)
        print("PERFORMANCE TEST SUITE")
        print("Testing {} profiles for {} seconds each".format(len(profiles), duration_per_test))
        print("="*50)
        
        for profile_name in profiles:
            try:
                self.test_profile(profile_name, duration_per_test)
                time.sleep_ms(2000)  # Brief pause between tests
            except Exception as e:
                print("Failed to test profile {}: {}".format(profile_name, e))
        
        # Print final comparison
        self.print_comparison()
    
    def print_comparison(self):
        """Print comparison table of all test results"""
        print("\n" + "="*50)
        print("PERFORMANCE COMPARISON")
        print("="*50)
        print("{:<10} {:<12} {:<8} {:<10} {:<8}".format(
            "Profile", "Resolution", "FPS", "Det Rate", "Det Time"))
        print("-"*50)
        
        for profile_name, results in self.results.items():
            print("{:<10} {:<12} {:<8.2f} {:<10.1f} {:<8.2f}".format(
                results['profile'],
                results['resolution'],
                results['avg_fps'],
                results['detection_rate'],
                results['avg_detection_ms']
            ))
# ==================== CALIBRATION ROUTINES ====================
def _safe_set_framesize(resolution):
    """Set framesize with fallback for unsupported sizes."""
    try:
        if resolution == "QVGA":
            sensor.set_framesize(sensor.QVGA)
        elif resolution == "VGA":
            sensor.set_framesize(sensor.VGA)
        elif resolution == "QQVGA":
            sensor.set_framesize(sensor.QQVGA)
        else:
            # Default to QVGA
            sensor.set_framesize(sensor.QVGA)
    except Exception as e:
        print("Framesize set failed ({}), falling back to QVGA: {}".format(resolution, e))
        sensor.set_framesize(sensor.QVGA)


def run_calibration(config, profile_name=None, samples_per_distance=10, timeout_s=15):
    """
    Calibrate focal length (fx, fy) for a profile using a real AprilTag of known size.

    Procedure:
      - For each distance in config.config['calibration']['distances_m'] (or 'distance_m'):
        - The user places the tag at that distance.
        - The script collects detections for samples_per_distance successful frames.
        - Computes focal length using pinhole model:
            f = (pixel_tag_width * distance_m) / real_tag_size_m
      - Averages f over distances and writes focal_length_x/y back to the profile in config.json.

    Requirements:
      - config.apriltag['tag_size'] must be set to the actual size in meters.
      - Use the profile you want to calibrate (active_profile by default).
    """
    # Load profile
    if profile_name is None:
        profile_name = config.config.get('active_profile')

    if profile_name not in config.config['profiles']:
        print("Profile {} not found in config".format(profile_name))
        return

    profile = config.config['profiles'][profile_name]
    calib_cfg = config.config.get('calibration', {})
    tag_size_m = calib_cfg.get('tag_size_m', config.config.get('apriltag', {}).get('tag_size', 0.20))
    distances = calib_cfg.get('distances_m', calib_cfg.get('distance_m', [0.5]))  # meters
    distances = distances if isinstance(distances, (list, tuple)) else [distances]

    print("Calibration start: profile={}, tag_size_m={:.3f} m".format(profile_name, tag_size_m))
    print("Distances to sample (m):", distances)

    # Initialize camera for profile
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    _safe_set_framesize(profile.get('resolution', 'QVGA'))
    sensor.skip_frames(time=2000)

    detector = AprilTagDetector(config)  # uses profile settings for detection scale/stride

    focal_estimates = []

    for d in distances:
        print("\nPlace the calibration tag at {:.3f} m and press the OpenMV IDE 'Stop/Run' button\n"
              "or wait for automatic capture. Waiting 5s before collecting...".format(d))
        # give user time
        for i in range(5, 0, -1):
            print(i)
            time.sleep(1)

        collected = []
        start_t = time.ticks_ms()
        while len(collected) < samples_per_distance:
            if time.ticks_diff(time.ticks_ms(), start_t) > timeout_s * 1000:
                print("Timeout waiting for samples at {:.3f} m".format(d))
                break

            img = sensor.snapshot()
            tags = detector.detect_tags(img)

            if tags:
                tag = detector.find_centered_tag(tags)
                if tag:
                    px_w = tag.get('w', None)
                    px_h = tag.get('h', None)
                    if px_w and px_w > 0:
                        collected.append((px_w, px_h))
                        print("Got sample {}: px_w={:.1f}".format(len(collected), px_w))
            time.sleep_ms(100)

        if not collected:
            print("No samples collected for distance {:.3f} m, skipping.".format(d))
            continue

        # compute focal per sample and then mean
        f_list = []
        for (px_w, px_h) in collected:
            f_x = (px_w * d) / tag_size_m
            f_y = (px_h * d) / tag_size_m
            f_list.append((f_x, f_y))

        # average for this distance
        mean_fx = sum([f[0] for f in f_list]) / len(f_list)
        mean_fy = sum([f[1] for f in f_list]) / len(f_list)
        focal_estimates.append((mean_fx, mean_fy))
        print("Distance {:.3f} m -> mean fx={:.1f}, fy={:.1f} (based on {} samples)".format(d, mean_fx, mean_fy, len(collected)))

    if not focal_estimates:
        print("No focal estimates obtained, calibration failed.")
        return

    # overall average
    avg_fx = sum([f[0] for f in focal_estimates]) / len(focal_estimates)
    avg_fy = sum([f[1] for f in focal_estimates]) / len(focal_estimates)

    # write back to config object and to file
    profile['focal_length_x'] = int(round(avg_fx))
    profile['focal_length_y'] = int(round(avg_fy))

    try:
        # update active profile block and write file
        with open('config.json', 'r') as f:
            cfg_disk = ujson.load(f)
        if 'profiles' not in cfg_disk:
            cfg_disk['profiles'] = {}
        cfg_disk['profiles'][profile_name] = cfg_disk['profiles'].get(profile_name, {})
        cfg_disk['profiles'][profile_name]['focal_length_x'] = profile['focal_length_x']
        cfg_disk['profiles'][profile_name]['focal_length_y'] = profile['focal_length_y']
        # preserve tag_size in apriltag if present
        with open('config.json', 'w') as f:
            ujson.dump(cfg_disk, f)
        print("Calibration saved to config.json for profile '{}'".format(profile_name))
    except Exception as e:
        print("Failed to write config.json:", e)

    print("\nCalibration results (averaged): fx={}, fy={}".format(profile['focal_length_x'], profile['focal_length_y']))
    return profile['focal_length_x'], profile['focal_length_y']

# ==================== MAIN APPLICATION ====================
def main():
    # Load configuration
    config = ConfigLoader()

    # Initialize camera
    initialize_camera(config)

    # Initialize components
    detector = AprilTagDetector(config)
    calculator = PositionCalculator()
    sender = DataSender(config)

    perf = config.config['performance']

    clock = time.clock()
    frame_count = 0
    last_gc = 0

    print("Starting AprilTag detection system...")
    print("Profile: {}".format(config.config['active_profile']))
    print("Resolution: {}x{}".format(
        config.profile['x_res'], config.profile['y_res']))

    while True:
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, last_gc) > perf['gc_interval_ms']:
            gc.collect()
            last_gc = current_time

        clock.tick()
        frame_count += 1

        try:
            img = sensor.snapshot()
            tags = detector.detect_tags(img)

            if tags:
                centered_tag = detector.find_centered_tag(tags)

                if centered_tag:
                    raw_data = calculator.calculate_relative_data(centered_tag)

                    if raw_data:
                        message = sender.send_raw_data(raw_data)

                        if frame_count % perf['print_interval_frames'] == 0:
                            print("Sent:", message)

                        img.draw_rectangle(
                            int(centered_tag['x']),
                            int(centered_tag['y']),
                            int(centered_tag['w']),
                            int(centered_tag['h']),
                            color=255
                        )

            if frame_count % perf['status_interval_frames'] == 0:
                fps = clock.fps()
                mem_free = gc.mem_free()
                print("FPS: {:.1f}, Free: {} bytes, Mode: {}".format(
                    fps, mem_free, "FAST" if detector.use_fast_mode else "FULL"))

        except Exception as e:
            print("Error:", e)
            time.sleep_ms(100)

        time.sleep_ms(perf['loop_delay_ms'])
        machine.idle()

# ==================== DEBUG MODE ====================
def run_performance_test(config):
    """Run performance tests based on config settings"""
    print("Nicla Vision AprilTag Performance Test")
    print("======================================")
    
    tester = PerformanceTest()
    debug_config = config.config.get('debug', {})
    
    if debug_config.get('test_all_profiles', True):
        # Test all profiles
        tester.run_all_tests(duration_per_test=debug_config.get('test_duration', 30))
    else:
        # Test single profile
        profile = debug_config.get('test_profile', 'qvga')
        tester.test_profile(profile, duration_seconds=debug_config.get('test_duration', 30))
    
    print("\n" + "="*50)
    print("All tests completed!")
    print("="*50)

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    cfg = ConfigLoader()
    mode = cfg.config.get('mode', 'normal').lower()

    if mode == "debug":
        run_performance_test(cfg)
    elif mode == "calibrate" or mode == "calibration":
        # optional: read profile to calibrate from config.calibration.profile
        profile_to_cal = cfg.config.get('calibration', {}).get('profile', cfg.config.get('active_profile'))
        run_calibration(cfg, profile_name=profile_to_cal,
                        samples_per_distance=cfg.config.get('calibration', {}).get('samples_per_distance', 10),
                        timeout_s=cfg.config.get('calibration', {}).get('timeout_s', 15))
    else:
        main()
