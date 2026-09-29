# Phoenix-X Software Engineering & Implementation Plan
## Problem Statement ID: SIH 26169 (ISRO / SAC)
**Document Status**: Baseline Architecture Specification

---

## 1. Architectural Blueprint & Directory Layout

The application is structured into decoupled, single-responsibility modules to ensure that the core vision and estimation algorithms can be tested independently of the GUI and simulation harness.

```
Phoenix-X-FSOC-Tracker/
├── 26169.pdf                           # Official SAC/ISRO Problem Statement Document
├── README.md                           # Master Project Architecture & Specifications
├── Phoenix_X_SIH26169_Submission.pptx  # Verified 6-Slide SIH Presentation Deck
├── academic_research/                  # Literature review & paper repository
│   ├── literature_review_and_citations.md
│   ├── download_papers.py
│   └── papers/                         # Downloaded peer-reviewed research PDFs
├── docs/                               # System specifications & mathematical derivations
│   └── system_architecture_plan.md     # This comprehensive engineering blueprint
├── presentation/                       # Presentation generation & automation scripts
│   └── generate_presentation.py
├── src/                                # Core Application Source Code
│   ├── __init__.py
│   ├── core/                           # Mathematical primitives & coordinate frames
│   │   ├── __init__.py
│   │   ├── coordinates.py              # Pixel <-> Arcsecond <-> Radian conversions
│   │   └── types.py                    # State vectors, telemetry schemas, dataclasses
│   ├── simulation/                     # Virtual universe & kinematic trajectory generators
│   │   ├── __init__.py
│   │   ├── universe.py                 # 2000x2000 px global world coordinate manager
│   │   ├── trajectories.py             # Linear, Circular, Lemniscate (Fig-8), Random
│   │   └── jitter.py                   # 6-DoF multi-harmonic platform vibration (±20 px)
│   ├── optics/                         # Optical propagation & atmospheric degradation
│   │   ├── __init__.py
│   │   ├── airy_disk.py                # Diffraction-limited Bessel/Gaussian spot generator
│   │   ├── atmosphere.py               # Beer-Lambert transmission (Fog, Haze, Rain)
│   │   └── noise.py                    # Vectorized 10% S&P, Poisson & Gaussian noise
│   ├── camera/                         # Virtual PTZ camera & actuator servo dynamics
│   │   ├── __init__.py
│   │   ├── ptz_camera.py               # 640x480 Monochrome FPA windowing & FOV logic
│   │   └── actuator.py                 # Slew rate limiters (5-10°/s) & S-curve inertia
│   ├── vision/                         # AI-assisted perception & sub-pixel centroiding
│   │   ├── __init__.py
│   │   ├── preprocessor.py             # Fast Rank-Order Median Filter (<1 ms)
│   │   ├── detector.py                 # Lightweight Saliency / Heatmap beacon localizer
│   │   └── centroid.py                 # Continuous 2D Gaussian gray-diffusion surface fit
│   ├── control/                        # Kinematic filtering & servo closed-loop control
│   │   ├── __init__.py
│   │   ├── imm_kalman.py               # Interacting Multiple Model (CV + CT + Singer)
│   │   └── pid_controller.py           # Predictive velocity feedforward + Anti-windup PID
│   ├── benchmarking/                   # ISRO Benchmark-2 video evaluation & audits
│   │   ├── __init__.py
│   │   ├── mp4_bypass.py               # Decoupled external video ingestion pipeline
│   │   └── audit_reporter.py           # Automated CSV, ICS-201 & PDF report generation
│   └── gui/                            # Hardware-accelerated user interface
│       ├── __init__.py
│       ├── main_window.py              # PyQt6 dark-theme tactical cockpit
│       ├── viewport_widget.py          # Real-time OpenGL / QPainter video display
│       ├── telemetry_hud.py            # Dynamic error plots, acquisition timer, RSSI
│       └── disturbance_panel.py        # Live judge edge-case injection controls
├── tests/                              # Comprehensive test suites
│   ├── test_kinematics.py              # Validates trajectory generators & slew limits
│   ├── test_noise_suppression.py       # Validates 10% S&P noise rejection
│   └── test_centroid_accuracy.py       # Validates < 0.2 px error under turbulence
└── main.py                             # Master entrypoint (CLI & GUI dispatcher)
```

---

## 2. Execution Modes (How the System Runs)

To satisfy all ISRO evaluation phases, the software supports 3 distinct execution modes:

### Mode 1: Interactive Cockpit GUI (`python3 main.py`)
* Launches the PyQt6 tactical desktop interface.
* Displays the dual viewport: Global Universe ($2000\times 2000\text{ px}$) on the left, and the Active Camera Viewport ($640\times 480\text{ px}$) on the right.
* Real-time telemetry HUD graphing Centroid Error, Gimbal Pan/Tilt Rates, FPS, and Signal Lock Status.
* **Interactive Triage Panel**: Allows judges to click buttons to dynamically inject 10% Salt & Pepper noise, dense fog, or extreme $\pm 20\text{ px}$ platform jitter.

### Mode 2: ISRO Benchmark-2 Bypass Mode (`python3 main.py --benchmark --video sample.mp4`)
* **Critical for 30% of Evaluation Marks**: Bypasses the virtual universe and PTZ camera completely.
* Ingests any external `.mp4` video @ 30 FPS.
* Runs the noise-suppression and sub-pixel AI centroiding pipeline frame-by-frame.
* Automatically outputs a timestamped `benchmark_results.csv` and summary PDF logging:
  * Frame number & timestamp
  * Detected centroid $(x_c, y_c)$ vs. Ground Truth
  * Instantaneous error, RMSE, lock retention rate, and execution FPS.

### Mode 3: Headless Monte Carlo Stress Test (`python3 main.py --monte-carlo --runs 100`)
* Executes 100 automated simulation runs across randomized initial positions, trajectories, and noise seeds.
* Verifies statistical compliance against ISRO SLAs: Acquisition Time $\le 2\text{ s}$, Tracking Error $\le 10\text{ px}$, Target Loss $< 5\%$.

---

## 3. Detailed Dataflow: Frame-by-Frame Pipeline

Every frame ($33.3\text{ ms}$ tick at $30\text{ Hz}$) executes the following deterministic lifecycle:

```
[Target Kinematics] ──► Global Position (X_t, Y_t) in 2000x2000 space
                                │
[Platform Jitter]   ──► Injects ±20 px Multi-harmonic Vibration
                                │
[Camera Window]     ──► Crops 640x480 Viewport based on Gimbal (θ_pan, θ_tilt)
                                │
[Optics Engine]     ──► Renders Airy Disc Profile + Beer-Lambert Fog Attenuation
                                │
[Noise Generator]   ──► Injects 10% Salt & Pepper + Poisson Shot Noise
                                │
                       [Camera Feed Frame]
                                │
[Preprocessor]      ──► Non-Linear Rank Median Filter (Clears S&P Noise in 0.8 ms)
                                │
[AI Localizer]      ──► Coarse Saliency / Heatmap Network isolates ROI [24x24 px]
                                │
[Centroid Engine]   ──► Continuous 2D Gaussian Surface Fit -> Sub-pixel (x_c, y_c)
                                │
[IMM-Kalman Filter] ──► State Prediction: Estimates Velocity (dx/dt, dy/dt)
                                │
[PID Servo Control] ──► Computes Slew Velocity (Clamped strictly to 5-10°/s)
                                │
[Virtual Gimbal]    ──► Updates Camera Viewport Position for Next Frame
```

---

## 4. Key Engineering Challenges Requiring Special Attention

### 1. Vectorized Real-Time Noise Generation & Rejection
* **The Danger**: Pure Python nested loops over a $640\times 480$ array ($307,200$ pixels) take $>150\text{ ms}$ per frame, causing massive frame drops.
* **The Solution**: 
  * Use vectorized NumPy SIMD operations for noise injection.
  * Apply OpenCV’s hardware-optimized `cv2.medianBlur` with a $3\times 3$ or $5\times 5$ kernel. This completely removes 100% of impulsive salt-and-pepper noise in **under $0.9\text{ ms}$**.

### 2. Enforcing Strict Gimbal Slew Rates ($5^\circ\text{--}10^\circ/\text{s}$)
* **The Danger**: If the target appears $400\text{ px}$ away from the center, a naive proportional controller commands a jump of $400\text{ px}$ in one frame ($2.5^\circ\text{ in } 33.3\text{ ms} = 75^\circ/\text{s}$), violating physical laws by $15\times$.
* **The Solution**: 
  * Convert all pixel errors to angular displacement: $\Delta\theta = \text{error}_{\text{px}} \times 0.00625^\circ/\text{px}$.
  * Enforce maximum velocity clamping: $|\omega_{\text{max}}| \le 5.0^\circ/\text{s} = 0.166^\circ/\text{frame} = 26.67\text{ px/frame}$.
  * Apply S-curve acceleration filtering to model motor torque limits.

### 3. Non-Blocking GUI Architecture (Thread Decoupling)
* **The Danger**: Running image processing inside the Qt GUI thread locks the interface, causing the telemetry graphs to stutter and fail the $30\text{ FPS}$ audit.
* **The Solution**:
  * Decouple the architecture into two threads:
    1. **`WorkerThread` (QThread / Python `threading.Thread`)**: Runs the $30\text{ Hz}$ deterministic simulation and vision loop.
    2. **`GUIThread`**: Consumes telemetry data via thread-safe Qt Signals/Slots or double-buffered locks, rendering at native screen refresh rate ($60\text{ Hz}$).

### 4. Tracking Non-Linear Trajectories (Figure-8) Without Phase Lag
* **The Danger**: A standard Constant Velocity (CV) Kalman filter assumes zero acceleration. When the target enters the sharp crossover loop of a Lemniscate (Figure-of-8), the filter overshoots and loses lock.
* **The Solution**:
  * Implement an **Interacting Multiple Model (IMM)** filter combining:
    - Model 1: Constant Velocity (CV) with low process noise (for smooth drift).
    - Model 2: Coordinated Turn (CT) with estimated turn rate $\omega$ (for circular & Figure-8 arcs).
    - Model 3: High process noise Singer Acceleration (for sudden random maneuvers).
  * The IMM filter dynamically adjusts model probabilities based on innovation residuals, eliminating tracking lag.
