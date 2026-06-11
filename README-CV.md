# Autonomous Flappy Bird Robot (Hardware-in-the-Loop)

**Goal:** Build a physical hardware-in-the-loop (HIL) system that autonomously plays on a tablet.  
**Status:** Software validation successful (High score: 90), Physical integration in progress.

### 💡 The Motivation
This project started from a pragmatic (and highly competitive) need. In our student house, we use a wall-mounted 'Turff' tablet, which features a custom Flappy Bird variant. The monthly winner on the leaderboard earns a prize (usually a crate of beer). Instead of spending hours practicing, I decided to leverage my engineering background to build a robot that would "solve" this problem for me.

### ⚙️ The System
This project integrates three complex disciplines into a single working system:
1. **Computer Vision:** Real-time screen registration using a Raspberry Pi Camera Module 3.
2. **Embedded Logic:** Python algorithms for high-speed decision making and timing.
3. **Actuation:** An electromagnetic solenoid that executes physical 'taps' on the capacitive screen.

### 🚧 Biggest Technical Challenges

**1. Choosing between Machine Learning and Computer Vision**
Initially, I experimented with Machine Learning (ML) to recognize the pipes and the bird. However, I quickly hit the limits of latency and processing power. The major breakthrough was pivoting to pure Computer Vision (OpenCV). By using smart color and contour detection (HSV thresholding), the processing time was drastically reduced. This pure software approach on my laptop easily achieved a high score of 90.

**2. Hardware & Software Latency (Lag)**
Controlling physical hardware introduces inevitable delays. While a virtual spacebar press is instantaneous, a solenoid is bound by physical travel time and the build-up of a magnetic field. To protect the Raspberry Pi from inductive spikes, I designed a safe switching circuit using a TIP120 transistor and a flyback diode. The current focus is on fine-tuning the mechanical stroke limiter and positioning the stylus exactly 1 millimeter above the screen to minimize actuation lag.

### 🎯 Current Status
The software logic and the hardware circuit have been successfully validated independently. I am currently finalizing the rigid mechanical setup to eliminate vibrations and ambient light reflections (which disrupt the OpenCV algorithm), after which the full system integration will follow.

