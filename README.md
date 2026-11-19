# Autonomous Flappy Bird Robot (Hardware-in-the-Loop)

An autonomous Raspberry Pi robot that plays **Turff Flappy** on an upright iPad using real-time Computer Vision (OpenCV) and a custom physical solenoid actuator.

<!-- PLACEHOLDER: Replace with your best short demo GIF or MP4 once you have a clean run -->
![Demo of the autonomous Flappy Bird robot in action](assets/demo_phone_pov.mp4)
![Demo of the autonomous Flappy Bird robot in action](assets/flappyvid.mp4)


https://github.com/user-attachments/assets/34876749-0c50-48d6-b0c4-58ebbfad55ad



## The Motivation
In our student house, we have a wall-mounted tablet running a custom Flappy Bird game (*Turff Flappy*). The monthly high-score winner gets a crates of beer. Instead of spending hours practicing tapping a screen, I decided to engineer a robot to beat it for me, no API, no jailbreak, just a camera and a mechanical finger.

## How It Works
* **Vision Sensor:** A Raspberry Pi Camera Module 3 captures the upright iPad screen via `Picamera2`.
* **Computer Vision:** Pure OpenCV (HSV color thresholding, ROI masking, and morphological filtering) tracks the bird and pipe gaps with minimal overhead.
* **Control Loop:** A non-blocking Python state machine (`live_test.py`) predicts jump arcs, applies ceiling protection ("Ghost Bird"), and dynamically hot-reloads tuning parameters from `config.json`.
* **Physical Actuation:** A 180°-inverted JF-0530B push-pull solenoid, driven by a TIP120 Darlington transistor circuit and grounded for capacitive touch, physically taps the screen.

## Current Status & Milestones
- [x] **Laptop Proof of Concept:** Validated the OpenCV tracking and look-ahead logic on a browser version (High score: **90**).
- [x] **Hardware & Circuit:** Built and tested the TIP120 low-side switching circuit, vertical rig, inverted solenoid hack, and capacitive GND tip.
- [x] **Raspberry Pi Integration:** Migrated to `Picamera2`, added live browser-based ROI calibration (`kaliberen_camera.py`), live `config.json` hot-reloading, and Black Box `.avi`/`.csv` telemetry.
- [ ] **In Progress:** Overcoming the ~150–200 ms physical Hardware-in-the-Loop (HIL) latency via an automated calibration script (`kalibratie_variabelen.py`) to measure exact jump height, fall speed, and actuator delay.

## Documentation
* **[Development Log (`README-DEV.md`)](README-DEVLOG.md)** — The full engineering story, design decisions, hardware hacks, and why I dropped Machine Learning.
* **[Build & Setup Guide (`SETUP.md`)](SETUP.md)** — Bill of Materials (BOM), wiring schematic, mechanical setup, and how to run the code yourself.
