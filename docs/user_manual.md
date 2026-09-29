# Phoenix-X User Manual & Operator Guide
## AI-Based Virtual Camera Tracking System for Mobile FSOC Terminals
**Problem Statement ID:** SIH 26169 (ISRO / SAC)  
**Deliverable:** Mandatory Deliverable 4 (User Manual)

---

## 1. System Requirements & Installation

Phoenix-X is designed for zero-install, cross-platform execution on macOS, Linux, and Windows 10/11.

### Prerequisites
* **Python 3.9+** (Python 3.10, 3.11, or 3.12 recommended)
* Standard Python scientific stack:
  ```bash
  pip install numpy opencv-python scipy matplotlib
  ```
  *(Note: No discrete GPU or CUDA installation is required. All vision and estimation algorithms run deterministically on CPU).*

### Verifying Installation
Clone the repository and verify the core modules:
```bash
git clone https://github.com/jvstin47/Phoenix-X-AI-Based-Virtual-Camera-Tracking-System-SIH26169.git
cd Phoenix-X-AI-Based-Virtual-Camera-Tracking-System-SIH26169
python3 -c "import cv2, numpy, scipy; print('Phoenix-X Environment Ready!')"
```

---

## 2. Application Operation & Execution Modes

Phoenix-X provides 3 primary operational modes tailored to different evaluation requirements:

### Mode 1: Interactive Cockpit Simulator (Single-Window Execution)
Launches the real-time simulation universe, optical degradation engine, and AI tracker in an interactive OpenCV HUD.
```bash
python3 main.py
```

#### Keyboard Hotkeys & Real-Time Controls:
| Key | Function | Expected System Response |
| :---: | :--- | :--- |
| **`1`** | **Toggle 10% Salt & Pepper Noise** | Injects 30,720 impulsive corrupted pixels; handled by $5\times 5$ rank median filter. |
| **`2`** | **Toggle Poisson & Gaussian Noise** | Injects quantum photon shot noise and sensor readout thermal noise. |
| **`3`** | **Toggle Fog / Haze Attenuation** | Reduces beacon optical contrast via Beer-Lambert scattering. |
| **`4`** | **Toggle Platform Jitter** | Injects $\pm 20\text{ px/frame}$ multi-harmonic vibration ($17.3\text{ Hz}$ & $29.1\text{ Hz}$). |
| **`T`** | **Cycle Target Trajectory** | Transitions path: Figure-8 $\rightarrow$ Circular $\rightarrow$ Sinusoid $\rightarrow$ Random Walk $\rightarrow$ Linear. |
| **`R`** | **Re-Center Gimbal Camera** | Slew camera back to global universe origin $(1000, 1000)$. |
| **`Q`** or **`ESC`** | **Quit & Export Report** | Terminates session and writes timestamped compliance CSV to `output_reports/`. |

---

### Mode 2: Distributed Multi-Terminal Satellite Demonstration (IPC over UDP)
Demonstrates multi-node flight avionics communication where Terminal 1 simulates a maneuvering satellite and Terminal 2 acts as the autonomous ground optical tracking station.

```
Terminal 1: target_satellite.py  ──► UDP:9999 (Frames) ──►  Terminal 2: ground_tracker.py
                                 ◄── UDP:9998 (PTZ)    ──◄           │
                                                                     ▼
                                                      http://localhost:8080/live.html
```

#### Step-by-Step Launch:
1. **Open Terminal 2 (Ground Optical Tracking Station)**:
   ```bash
   python3 distributed_demo/ground_tracker.py
   ```
2. **Open Terminal 1 (Remote Satellite Transmitter)**:
   ```bash
   python3 distributed_demo/target_satellite.py
   ```
3. **Open Your Browser**:
   Navigate to:
   ```
   http://localhost:8080/live.html
   ```

#### Interactive PTZ Operator Controls:
* **Keyboard in Terminal 2**:
  * `W` or `Up Arrow`: Tilt Up
  * `S` or `Down Arrow`: Tilt Down
  * `A` or `Left Arrow`: Pan Left
  * `D` or `Right Arrow`: Pan Right
  * `M` or `SPACE`: Toggle between **Autonomous Auto-Track** and **Manual Operator Override**
  * `R`: Re-Center Gimbal Camera
* **Web Cockpit Controls**:
  * Click the on-screen directional buttons: **Pan Left**, **Pan Right**, **Tilt Up**, **Tilt Down**, **Re-Center**, or toggle **Auto-Track**.

---

### Mode 3: ISRO Benchmark-2 External Video Evaluation Mode
Bypasses the virtual PTZ camera and directly ingests any external `.mp4` video file (as mandated for 30% of ISRO evaluation marks):

#### A. Autonomous Laser Beacon Tracking:
```bash
python3 main.py --video tests/sample_beacon_test.mp4 --ground-truth tests/sample_ground_truth.csv
```
* Ingests the video, suppresses noise, detects the beacon, draws tracking reticles, and outputs an automated RMSE audit.

#### B. Interactive "Select-to-Track" for Arbitrary Videos:
```bash
python3 main.py --video /path/to/any_video.mp4 --select-roi
```
* Frame 1 pauses; click and drag a bounding box over any object, press SPACE, and the CSRT tracker tracks it through the entire video!

---

## 3. Parameter Configuration Guide

Parameters can be adjusted in `src/core/coordinates.py` or via command-line flags:

| Parameter Name | Configuration File | Default Value | Valid Range | Operational Meaning |
| :--- | :--- | :---: | :---: | :--- |
| `DEFAULT_MAX_SLEW_RATE_DEG_S` | `src/core/coordinates.py` | `5.0` | $5.0\text{--}10.0^\circ/\text{s}$ | Maximum angular slew velocity of the virtual gimbal motors. |
| `UNIVERSE_WIDTH_PX` | `src/core/coordinates.py` | `2000` | $\ge 2000\text{ px}$ | Dimension of the global uncertainty simulation space. |
| `CAMERA_WIDTH_PX` / `HEIGHT` | `src/core/coordinates.py` | `640 x 480` | User-defined | Focal Plane Array (FPA) camera sensor resolution. |
| `FOV_AZ_DEG` / `FOV_EL_DEG` | `src/core/coordinates.py` | `4.0 x 3.0` | User-defined | Camera optical Field-of-View ($22.5\text{ arcsec/px}$). |
| `spot_size_px` | `src/optics/atmosphere_and_noise.py`| `10` | $5\text{--}20\text{ px}$ | Physical Airy disc spot diameter on the sensor array. |
| `prob` (S&P Noise) | `src/optics/atmosphere_and_noise.py`| `0.10` | $0.0\text{--}0.25$ | Fractional percentage of impulsive corrupted pixels. |

---

## 4. GUI & Cockpit Description

### 1. The OpenCV Visual Cockpit (`main.py`)
* **Left Viewport (Global Universe $360\times 360$)**: Shows the entire $2000\times 2000$ sky, the purple trajectory trail of the moving satellite, the yellow camera FOV bounding box, and the current line of sight.
* **Right Viewport (Active Camera Feed $640\times 480$)**: Shows the monochrome FPA feed with the laser spot, center crosshairs, green tracking reticle, and the $10\text{ px}$ ISRO SLA tolerance circle.
* **Bottom HUD**: Displays instantaneous centroid error (pixels and arcseconds), gimbal slew rate ($^\circ/\text{s}$), execution FPS, and SNR (dB).

### 2. The Mission Control Web Cockpit (`web_demo/live.html`)
* **Real-Time Radar Display**: Plots the true satellite position against the ground station tracking reticle.
* **Dynamic Waveform Chart (Chart.js)**: Plots real-time tracking error at 30 Hz against ISRO's red dashed $10\text{ px}$ SLA limit.
* **Operator PTZ D-Pad**: Clickable buttons allowing the operator to manually steer the gimbal camera or toggle auto-tracking.
* **Audit Exporter**: Click **"Export CSV Audit"** to download the session log.

---

## 5. Performance Report Interpretation

Performance reports are automatically saved to `output_reports/` in CSV format. Key columns include:
* `Frame_ID`: Sequential video frame number.
* `Timestamp_s`: Time offset in seconds from tracking initiation.
* `Detected_X`, `Detected_Y`: Sub-pixel coordinates $(x_c, y_c)$ of the beacon centroid.
* `GT_Error_px`: Euclidean error relative to ground truth coordinates.
* `Lock_Status`: `LOCKED` if within $10\text{ px}$ tolerance; `ALIGNING` or `LOST` otherwise.
