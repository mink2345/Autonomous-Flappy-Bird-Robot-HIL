# Flappy Bird HIL (Hardware-in-the-Loop) System

This is the technical repository for an autonomous Flappy Bird robot based on a Raspberry Pi 4B. The system uses OpenCV for real-time object detection and controls a solenoid via GPIO to physically interact with a capacitive tablet screen.

---

## 1. Requirements & Dependencies

Ensure the following libraries are installed on your Raspberry Pi:
* `python3`
* `opencv-python`
* `numpy`
* `gpiozero`

> **Important OS Dependency Note:**
> This project runs on **Raspberry Pi OS (Bookworm)**. In this release, the legacy `cv2.VideoCapture(0)` method is no longer supported out-of-the-box for the Camera Module. Therefore, this project utilizes the official `Picamera2` library to load frames directly into a numpy array with minimal overhead.

---

## 2. Hardware Specifications & Circuit

* **Microcontroller:** Raspberry Pi 4B
* **Vision Sensor:** Raspberry Pi Camera Module 3 (Phase Detection Autofocus via CSI)
* **Actuator:** JF-0530B Solenoid Push-Pull (6V, 300mA)
* **Components:** 1x TIP120 Darlington Transistor, 1x 1N4007 Flyback Diode, 2x 1kΩ Resistor.

### Circuit Architecture
The Raspberry Pi GPIO pins (max ~16mA output) cannot directly drive the solenoid (300mA). An external power supply is used, switched by an NPN transistor acting as a low-side switch.

* **GPIO 18 (Pin 12)** -> 1kΩ base resistor -> **TIP120 Base**
* **Solenoid** is powered by a 5V/6V VCC rail. A **Flyback Diode** is placed in parallel across the solenoid terminals (cathode facing VCC) to safely dissipate flyback current.
* **TIP120 Collector** -> GND side of the solenoid.
* **TIP120 Emitter** -> Common GND.

---

## 3. Test Scripts & Validation

### Test A: Actuation (`motor_test.py`)
Validates the switching circuit and measures the mechanical response of the solenoid.
```python
from gpiozero import LED
from time import sleep

solenoid = LED(18)
try:
    while True:
        solenoid.on()
        sleep(0.1)  # Fingertip touch simulation
        solenoid.off()
        sleep(2.0)
except KeyboardInterrupt:
    solenoid.off()

### Test B: Vision + Actuation (test\_c\_camera.py)

Integrates the Camera Module with active color detection (HSV). Triggers the GPIO pin the moment the color red is detected._(Check the repository for the full code utilizing Picamera2 and cv2.inRange)_

4\. Debugging & Network Monitoring (VLC)
----------------------------------------

During physical calibration, it is highly recommended to monitor the camera stream live without disturbing the hardware setup.

1.  **Start TCP stream on the Raspberry Pi:**
    

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML   `rpicam-vid -t 0 --inline --listen -o tcp://0.0.0.0:8080`

1.  **Open stream on a client machine:**Open VLC Media Player on a laptop connected to the same local network. Navigate to _Open Network Stream..._ and enter: tcp://\[RASPBERRY\_PI\_IP\_ADDRESS\]:8080.
    

5\. Roadmap / To-Do
-------------------

*   \[x\] Validate vision algorithm via laptop simulation (High score achieved: 90).
    
*   \[x\] Design and protect the solenoid switching circuit.
    
*   \[x\] Integrate Picamera2 and configure HSV thresholding.
    
*   \[ \] **Current:** Build a rigid mechanical test rig (fixate camera height, calibrate actuation distance to 1mm).
    
*   \[ \] Shield ambient light to prevent HSV fluctuations.
    
*   \[ \] Merge subsystems into main.py and implement delay compensation for mechanical actuation lag.

