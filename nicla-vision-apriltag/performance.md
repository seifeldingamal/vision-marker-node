<!-- filepath: c:\Users\seifa\Documents\JB\airship_camera\code\performance.md -->

# Nicla Vision April Tags Detection — Performance Summary

Concise, consistent recording of AprilTag detection runs across camera profiles (QQVGA, QVGA, VGA). Each session shows observed FPS range, free memory range, modes, a short representative log excerpt, and a few performance samples.

### Performance comparison

| Profile | Resolution | FPS    | Detect Rate | Detect Time |
| ------- | ---------- | ------ | ----------- | ----------- |
| qqvga   | 160x120    | 44.47  | 97.7        | 14.92       |
| qvga    | 320x240    | 49.30  | 99.9        | 15.06       |
| vga     | 640x480    | 119.43 | 69.2        | 4.63        |

---

## Session: QQVGA (profile: qqvga — 160×120)

Observed:

-   FPS range: ~40.4 — 50.0 (Very FAST ~45)
-   Free memory: ~173,248 bytes
-   Modes: FULL, FAST

Performance samples:

-   Frame 10: 50.0 FPS, 10 detections, Mode: FULL
-   Frame 100: 43.1 FPS, 35 detections, Mode: FAST
-   Frame 690: 44.5 FPS, 618 detections, Mode: FAST

---

## Session: QVGA (profile: qvga — 320×240)

Observed:

-   FPS range: ~15.4 — 30.6 (FAST ~20–27)
-   Free memory: ~41,312 — 320,416 bytes
-   Modes: FULL, FAST
-   Network: WiFi connected (example IP: 10.101.21.48)

Performance samples:

-   FPS: 15.4, Free: 236,416 bytes, Mode: FULL
-   FPS: 24.7, Free: 300,480 bytes, Mode: FAST
-   FPS: 30.6, Free: 180,864 bytes, Mode: FAST

---

## Session: VGA (profile: vga — 640×480)

Observed:

-   FPS range: ~15.3 — 16.4 (SLOWer ~14-15)
-   Free memory: ~38,880 — 270,720 bytes
-   Modes: FAST, FULL
-   Network: WiFi connected (example IP: 10.101.21.48)

Performance samples:

-   FPS: 16.4, Free: 250,784 bytes, Mode: FAST
-   FPS: 15.3, Free: 97,824 bytes, Mode: FULL
-   FPS: 15.5, Free: 270,720 bytes, Mode: FULL
