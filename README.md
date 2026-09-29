# Phoenix-X: AI-Based Virtual Camera Tracking System
### Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals

[![SIH Problem ID](https://img.shields.io/badge/SIH%202024-Problem%20ID%2026169-blue.svg)](https://sih.gov.in)
[![Organization](https://img.shields.io/badge/Organization-ISRO%20%2F%20SAC-orange.svg)](https://www.isro.gov.in)
[![Category](https://img.shields.io/badge/Category-Software-green.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Cross--Platform%20(Windows%20%7C%20macOS%20%7C%20Linux)-purple.svg)]()
[![Target FPS](https://img.shields.io/badge/Target%20FPS-%E2%89%A5%2030%20Hz-brightgreen.svg)]()

---

## 1. Executive Summary & Problem Context

Free Space Optical Communication (FSOC) is the backbone of next-generation gigabit-to-terabit mobile and inter-satellite networks. Unlike conventional Radio Frequency (RF) systems, FSOC relies on extremely narrow, diffraction-limited laser beams with angular divergences in the range of **tens of microradians** ($\sim 10\text{--}100\ \mu\text{rad}$). Even microscopic angular jitter or tracking misalignments will cause complete signal dropouts.

Deploying optical links across high-mobility platforms (satellites in LEO/GEO, UAVs, airborne nodes) requires a robust two-stage **Pointing, Acquisition, and Tracking (PAT)** architecture:
1. **Coarse Alignment Stage (The Core of this Project)**: A wide Field-of-View (FOV) camera ($4^\circ \times 3^\circ$) on a motorized Pan-Tilt gimbal searches the spatial uncertainty zone, detects the remote optical beacon, acquires lock within $\le 2\text{ s}$, and centers the spot within $\le 10\text{ pixels}$ error.
2. **Fine Alignment Stage (Downstream Handover)**: Fast Steering Mirrors (FSMs) and Quadrant Photodiodes (QPDs) take over at kilohertz frequencies for sub-microradian precision data transmission.

**Project Phoenix-X** delivers a mathematically rigorous, Software-in-the-Loop (SIL) virtual camera tracking simulator and AI perception pipeline that reproduces the optical physics, atmospheric disturbances, and gimbal kinematics of real flight hardware without requiring expensive physical testbeds.

---

## 2. Technical Specifications & Performance SLAs (ISRO SAC 26169)

| Parameter Category | Specification | Reference Value | Phoenix-X Target |
| :--- | :--- | :--- | :--- |
| **Virtual Universe** | Coordinate Screen Size | $\ge 2000 \times 2000$ pixels | Configurable $2000\times 2000$ to $4000\times 4000$ |
| **Virtual Camera** | Sensor Array & Resolution | Monochrome FPA, $640 \times 480$ px | Monochrome (8-bit grayscale), $640\times 480$ px |
| | Field-of-View (FOV) | Default $4^\circ \times 3^\circ$ | $4^\circ \times 3^\circ$ ($22.5\text{ arcsec/px}$) |
| | Camera Frame Rate | $\ge 30\text{ Hz}$ | $30\text{--}60\text{ Hz}$ deterministic loop |
| **Target Beacon** | Geometry & Profile | Beacon spot, $5\times 5$ to $20\times 20$ px | Airy disc / 2D Gaussian profile ($10\times 10$ default) |
| | Kinematic Motions | 4+ trajectories | Straight Line, Circular, Lemniscate (Fig-8), Random, Sinusoidal |
| **Gimbal Constraints** | Slew Rate Limits | $5^\circ\text{--}10^\circ/\text{s}$ (Pan & Tilt) | Hard physical limits enforced via trapezoidal velocity profiling |
| | Update Rate | $\ge 20\text{ Hz}$ | Synchronous $30\text{ Hz}$ servo control loop |
| **Disturbances & Noise** | Image Degradation | Salt & Pepper (10%), Poisson, Gaussian ($\sigma \le 20$) | Real-time vectorized stochastic disturbance pipeline |
| | Platform Kinematics | Jitter $\pm 20\text{ px/frame}$, Platform motion $\pm 20\text{ px/frame}$ | Multi-harmonic vibrational synthesis + low-frequency drift |
| | Atmospheric Disturbance| Clear, Haze, Fog, Rain, Low Light | Beer-Lambert transmission attenuation + contrast degradation |
| **Evaluation SLAs** | Acquisition Time | $\le 2\text{ s}$ | $\le 0.8\text{ s}$ target |
| | Tracking Error | $\le 10\text{ px}$ | Sub-pixel accuracy ($\le 1.5\text{ px}$ under nominal; $\le 5\text{ px}$ under noise) |
| | Target Loss Rate | $< 5\%$ | $< 1\%$ across all standard test profiles |
| | Re-acquisition Time | $\le 1\text{ s}$ | $\le 0.4\text{ s}$ (via IMM-Kalman state extrapolation) |
| | Processing Throughput | $\ge 20\text{ FPS}$ | $\ge 35\text{ FPS}$ on basic CPU; $>100\text{ FPS}$ on Apple Silicon / GPU |

---

## 3. High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Phoenix-X FSOC Tracking System                       │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Core Simulation Engine                                              │
│    ├── Virtual Universe (2000x2000 px world coordinate frame)         │
│    ├── Trajectory Generators (Linear, Circular, Lemniscate/Fig-8, etc.)│
│    └── Kinematic Disturbance Generator (Platform 6-DoF drift & jitter) │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Optical & Atmospheric Degradation Pipeline                          │
│    ├── Optical Model (Diffraction-limited Airy disk / Gaussian spot)  │
│    ├── Atmospheric Attenuation (Beer-Lambert fog/haze/rain)            │
│    └── Stochastic Noise Injector (Salt & Pepper 10%, Poisson, Gauss)   │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Virtual Pan-Tilt Camera (PTZ) Subsystem                            │
│    ├── Viewport Windowing (640x480 crop from global universe)          │
│    ├── Kinematic Actuator Model (Slew rate limits 5-10°/s, inertia)    │
│    └── Mode Switcher: Internal Simulated Feed vs. External .mp4 Feed   │
├────────────────────────────────────────────────────────────────────────┤
│ 4. AI-Assisted Perception & Tracking Core                             │
│    ├── Stage 1: Fast Background Rejection & Noise Suppression          │
│    ├── Stage 2: AI Beacon Candidate Localizer (Heatmap / Deep Prior)   │
│    ├── Stage 3: Sub-Pixel Precision Centroiding                        │
│    └── Stage 4: IMM-Kalman Filter (Kinematic state estimation)         │
├────────────────────────────────────────────────────────────────────────┤
│ 5. PTZ Servo Controller                                                │
│    └── Predictive Lead-Lag PID / Velocity Feedforward Controller      │
├────────────────────────────────────────────────────────────────────────┤
│ 6. User Interface & Automated Benchmarking Suite                       │
│    ├── High-Performance GUI (PyQt6 / PySide6 with OpenGL/VisPy)        │
│    ├── Real-time HUD (Centroid error, FPS, SNR, Lock status)           │
│    ├── Real-time Interactive Disturbance Injection Panel              │
│    └── Automated Compliance Report Generator (CSV + PDF Export)        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Evaluation Strategy: Tackling "Benchmark Performance-2" (30 Marks)

ISRO's evaluation rubric assigns **30% of the entire grade** to a specific benchmark test:
> *"Each team will be given a few video files (.mp4) @30 fps, covering a complete screen with noise and moving beacon spot. The software needs to bypass its PTZ camera and take this video as an input to the coarse pointing system."*

To score maximum marks, Phoenix-X is architected with a **Dual-Mode Video Pipeline**:
* **Mode A (Closed-Loop Autonomous Tracking)**: Full end-to-end loop where the AI tracker commands the virtual PTZ camera viewport inside the virtual universe.
* **Mode B (ISRO Benchmark Bypass Mode)**: Ingests external `.mp4` video files directly into the perception pipeline, bypassing the PTZ simulator, and automatically generates:
  * Frame-by-frame centroid coordinate logs $(x_t, y_t)$
  * Root Mean Square Error (RMSE) against ground truth
  * Real-time acquisition latency, lock retention rate, and execution FPS.

---

## 5. Verified Academic Literature Foundations

All theoretical models in Phoenix-X are anchored in peer-reviewed literature with verified DOIs:

1. **Space Mission PAT Handover**: Liu et al., *"Pointing, Acquisition, and Tracking (PAT) for Optical Satellite Communications: Recent Trends and the ALIGN UK Mission's PAT Mechanism"*, IEEE ICSOS 2025. [DOI: 10.1109/icsos66026.2025.11443125](https://doi.org/10.1109/icsos66026.2025.11443125)
2. **Mobile FSOC Platform Dynamics**: Sun et al., *"High-Precision Tracking of Free-Space Optical Communication System on Mobile Platforms"*, *Photonics* 2024. [DOI: 10.3390/photonics11100900](https://doi.org/10.3390/photonics11100900)
3. **Computer Vision in Atmospheric Turbulence**: Saha et al., *"Turb-Seg-Res: A Segment-then-Restore Pipeline for Dynamic Videos with Atmospheric Turbulence"*, IEEE/CVF CVPR 2024. [DOI: 10.1109/CVPR52733.2024.02389](https://doi.org/10.1109/CVPR52733.2024.02389)
4. **Moving Object Segmentation Under Turbulence**: Qin et al., *"Unsupervised Moving Object Segmentation with Atmospheric Turbulence"*, ECCV 2024. [DOI: 10.1007/978-3-031-72658-3_2](https://doi.org/10.1007/978-3-031-72658-3_2)
5. **Sub-Pixel Centroiding on Space Detectors**: Yang et al., *"Centroid Extraction of Laser Spots Captured by Infrared Detectors"*, *Remote Sensing* 2023. [DOI: 10.3390/rs15082129](https://doi.org/10.3390/rs15082129)
6. **Actuator Kinematic Modeling**: Martinez et al., *"Steering Mirror System with Closed-Loop Feedback for FSOC Terminals"*, *Aerospace* 2024. [DOI: 10.3390/aerospace11040330](https://doi.org/10.3390/aerospace11040330)
7. **Foundational FSOC Survey**: Kaushal & Kaddoum, *"Free Space Optical Communication: Challenges and Mitigation Techniques"*, *IEEE Communications Surveys & Tutorials* 2016. [DOI: 10.1109/COMST.2016.2617691](https://doi.org/10.1109/COMST.2016.2617691)

---

## 6. Repository Layout

```
.
├── 26169.pdf                           # Official SAC/ISRO Problem Statement Document
├── README.md                           # Master Project Architecture & Specifications
├── .gitignore                          # Standard Python / macOS Git exclusions
├── academic_research/                  # Literature review & paper repository
│   ├── literature_review_and_citations.md
│   ├── download_papers.py
│   └── papers/                         # Downloaded peer-reviewed research PDFs
├── docs/                               # Engineering documentation & state machines
├── hardware_bom/                       # Avionics compute trade-offs & flight specifications
├── src/                                # Core Application Source Code
│   ├── simulation/                     # Virtual universe, trajectories & disturbances
│   ├── optics/                         # Airy disc, Beer-Lambert & noise injection
│   ├── camera/                         # Virtual PTZ camera & slew-rate mechanics
│   ├── vision/                         # Denoising, AI beacon detector & centroiding
│   ├── control/                        # IMM-Kalman filter & PID servo controller
│   └── gui/                            # PyQt6 interactive HUD, controls & benchmarking
└── tests/                              # Unit, integration & benchmark test suites
```
