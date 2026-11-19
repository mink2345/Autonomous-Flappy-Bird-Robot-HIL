# Flappy Bird HIL (Hardware-in-the-Loop) System

This is the technical repository for an autonomous Flappy Bird robot running on a Raspberry Pi 4B. The system uses OpenCV and `Picamera2` for real-time computer vision and controls a push-pull solenoid via a non-blocking GPIO state machine to physically tap an upright capacitive iPad screen.

---

## 1. Requirements & Dependencies

Ensure the following libraries are installed on your Raspberry Pi:
- `python3`
- `opencv-python`
- `numpy`
- `gpiozero`
- `picamera2`

> **Important OS Dependency Note:**
> This project runs on **Raspberry Pi OS (Bookworm)**. In this release, the legacy `cv2.VideoCapture(0)` method is no longer supported out-of-the-box for the CSI Camera Module. Therefore, this project utilizes the official `Picamera2` library to load frames directly into a NumPy array with minimal latency.

---

## 2. Hardware Specifications & Circuit

- **Microcontroller:** Raspberry Pi 4B
- **Vision Sensor:** Raspberry Pi Camera Module 3 (Phase Detection Autofocus via CSI)
- **Actuator:** JF-0530B Solenoid Push-Pull (6V, 300mA)
- **Power Supply:** External 5V/6V DC rail (stripped USB power line / dedicated adapter)
- **Components:** 1x TIP120 Darlington NPN Transistor, 1x 1N4007 Flyback Diode, 2x 1kΩ Resistor, capacitive stylus tip with ground return.

### Circuit Architecture
The Raspberry Pi GPIO pins (max ~16mA output) cannot directly drive the solenoid (300mA). An external power supply is used, switched by a TIP120 transistor acting as a low-side switch:

- **GPIO 18 (Pin 12)** -> 1kΩ base resistor -> **TIP120 Base** (with an additional 1kΩ pull-down resistor to GND).
- **Solenoid** is powered by the external VCC rail. A **1N4007 Flyback Diode** is placed in parallel across the solenoid terminals (cathode facing VCC) to safely dissipate inductive flyback voltage spikes.
- **TIP120 Collector** -> Negative terminal of the solenoid & diode anode.
- **TIP120 Emitter** -> Common GND (shared between Pi Pin 6 and external power supply).

### Mechanical Setup ("Vampire Mode" & Inverted Actuator)
- **Vertical Orientation:** Both the iPad and the Camera Module 3 are mounted vertically to eliminate perspective skew and glare.
- **Inverted Solenoid Hack:** Standard pull-solenoids rest extended and retract when energized, fighting a stiff conical internal spring. To maximize impact force on a vertical screen, the solenoid is rotated **180 degrees**, utilizing the rear shaft protrusion to strike the screen upon energization, paired with a tensioned rubber return band.

---

## 3. Repository Structure & Scripts

```text
raspberrypi/
├── config.json               # Live hot-reloadable tuning parameters (margins, cooldowns, low-pipe thresholds)
├── kaliberen_camera.py       # Multithreaded HTTP MJPEG web server (:8080) with live ROI overlays
├── live_test.py              # Main autonomous HIL control loop, HUD renderer, and Black Box logger
├── maak_foto.py              # Static reference frame capture utility for HSV color profiling
├── solenoid_test.py          # Isolated GPIO/TIP120 hardware actuation unit test
├── test_cv_and_solenoid.py   # Initial closed-loop HSV color trigger validation script
└── vlucht_logs/              # Auto-generated session recordings (.avi HUD videos & .csv crash logs)
```

### Unit Test A: Actuation (`solenoid_test.py`)
Validates the TIP120 switching circuit and mechanical response of the inverted solenoid.
```python
from gpiozero import LED
from time import sleep

solenoid = LED(18)
try:
    while True:
        solenoid.on()
        sleep(0.1)  # 100ms capacitive touch simulation
        solenoid.off()
        sleep(2.0)
except KeyboardInterrupt:
    solenoid.off()
```

### Unit Test B: Vision + Actuation (`test_cv_and_solenoid.py`)
Integrates `Picamera2` with HSV color thresholding (`cv2.inRange`), firing GPIO 18 immediately when target color pixel density exceeds the threshold.

---

## 4. Live Calibration & Telemetry

### Method A: Browser-Based ROI Calibration (`kaliberen_camera.py`)
Because the Raspberry Pi runs headlessly via SSH, `kaliberen_camera.py` hosts a lightweight multithreaded HTTP MJPEG stream drawing the active playfield boundaries (`SPEELVELD_TOP = 350`, `SPEELVELD_BODEM = 830` to crop out the moving orange floor) and the bird detection corridor (`X = 20` to `140`).

1. Run on the Raspberry Pi:
   ```bash
   python3 kaliberen_camera.py
   ```
2. Open any browser on the local network and navigate to:
   ```text
   http://<RASPBERRY_PI_IP>:8080
   ```

### Method B: Low-Level CLI Stream (VLC)
For raw sensor latency validation without Python overhead:
```bash
rpicam-vid -t 0 --inline --listen -o tcp://0.0.0.0:8080
```
Open VLC Media Player on a client machine -> *Open Network Stream* -> `tcp://<RASPBERRY_PI_IP>:8080`.

---

## 5. Control Architecture (`live_test.py` & `config.json`)

The main loop in `live_test.py` runs at 20 FPS (1440x1080 rotated 90° clockwise) and incorporates several real-time engineering solutions to overcome the ~150–200ms total HIL latency:

1. **Non-Blocking GPIO State Machine:** Solenoid pulse duration (`KLIK_TIJD`) and cooldown (`MIN_TIJD_TUSSEN_SPRONGEN`) are evaluated asynchronously using `time.time()` deltas, ensuring image capture and contour detection never freeze during a tap.
2. **Morphological Pipe Grouping & Floor Cropping:** Strict ROI masking (`SPEELVELD_BODEM = 830`) isolates pipes from the identical-colored scrolling floor. Dilation and `MORPH_CLOSE` merge fragmented contours into unified pipe columns.
3. **Ghost Bird Ceiling Protection:** Before triggering a jump, the algorithm projects the bird's post-jump apex (`vogel_top - SPRONG_KRACHT`) against the upper pipe lip plus a safety helmet buffer (`VEILIGHEIDS_BUFFER`). Unsafe jumps are blocked (`BLOCKED` HUD alert).
4. **Preemptive Low-Pipe Mode ("Lage Buis Modus"):** When a pipe gap spawns below `LAGE_BUIS_GRENS`, the controller dynamically switches from `MARGE_SPRONG` to a much more aggressive negative threshold (`MARGE_SPRONG_LAAG`) to counteract high downward falling velocity prior to floor impact.
5. **Live Hot-Reloading (`config.json`):** `live_test.py` parses `config.json` on every frame (with fault-tolerant fallback on syntax errors), enabling real-time parameter tuning over SSH while the robot is mid-flight.
6. **Black Box Telemetry (`vlucht_logs/`):** Every run outputs a timestamped `.avi` video with full HUD telemetry (bounding boxes, target lines, Ghost Bird vector, and green solenoid trigger indicator) alongside a `.csv` crash log.

---

## 6. Roadmap / Status

- [x] Validate vision algorithm via laptop simulation (High score achieved: 90).
- [x] Design and protect the solenoid switching circuit (TIP120 + flyback diode).
- [x] Integrate `Picamera2` and configure HSV thresholding & morphological filtering.
- [x] Build vertical mechanical rig with inverted solenoid and elastic return mechanism.
- [x] Implement `kaliberen_camera.py` HTTP stream to crop out the moving floor.
- [x] Merge subsystems into `live_test.py` with non-blocking GPIO, Black Box `.avi`/`.csv` logging, and `config.json` live hot-reloading.
- [ ] **Current:** Fine-tune `MARGE_SPRONG`, `LAGE_BUIS_GRENS`, and `MARGE_SPRONG_LAAG` via frame-by-frame video latency analysis.
- [ ] Implement dynamic horizontal speed compensation for late-game acceleration.