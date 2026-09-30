# Phoenix-X: Submission Image Assets & Visual Deliverables
**Problem Statement ID:** SIH 26169 (ISRO / Space Applications Centre)  
**Project:** AI-Based Virtual Camera Tracking System for Mobile Free Space Optical Communication (FSOC)  
**Team:** Phoenix X (ID: 141943)

This directory contains high-resolution visual deliverables, conceptual 3D renders, architectural schematics, and empirical benchmark figures generated for the SIH 2026 submission.

---

### Image Directory Index

| File Name | Description & Submission Context | Resolution / Format |
| :--- | :--- | :---: |
| **`01_satellite_ground_laser_link.jpg`** | **Operational Space Concept Render:** Photorealistic visual showing a low-Earth-orbit satellite transmitting a focused optical laser beam down through atmospheric fog and clouds to an automated mountain ground telescope terminal station at night. | 16:9 HD (1920x1080) |
| **`02_mobile_optical_gimbal_terminal.jpg`** | **Opto-Mechatronic Hardware Concept:** Technical CAD product design of the transportable ground tracking terminal, featuring dual-axis brushless servo motors, carbon fiber sunshade, optical Focal Plane Array (FPA) camera, and rugged field tripod. | 16:9 HD (1920x1080) |
| **`03_tactical_dual_viewport_cockpit.png`** | **Live Flight Simulation Cockpit:** Real captured frame from `main.py` showing the global $2000\times 2000$ orbital arena on the left and the active $640\times 480$ virtual camera viewport on the right, featuring optical crosshairs, $10\text{ px}$ SLA boundary circle, green tracking lock reticle, and real-time telemetry HUD. | 1100x640 PNG |
| **`04_optical_disturbances_comparison.png`** | **4-Quadrant Scientific Disturbance Panel:** Scientific side-by-side comparison of: <br>1. *Clean Diffraction-Limited Airy Disc* <br>2. *10% Impulsive Salt & Pepper Noise (ISRO Mandate)* <br>3. *Beer-Lambert Fog Attenuation & Ambient Backscatter* <br>4. *Resolved Kolmogorov Wavefront Turbulence with Sub-Pixel Lock* | 1280x960 PNG |
| **`05_distributed_3node_architecture.png`** | **Distributed Hardware-in-the-Loop Architecture:** System schematic detailing Node A (Satellite Transmitter), Node C (Atmospheric Channel Emulator), and Node B (Ground Optical Tracker) communicating over fragmented UDP sockets with closed-loop PTZ feedback. | 1200x650 PNG |
| **`06_tracking_performance_benchmarks.png`** | **Quantitative Performance Benchmarks:** Empirical validation plots showing rapid convergence from initial $25\text{ px}$ offset down to $< 0.5\text{ px}$ steady-state error (vs. $10\text{ px}$ SLA) and strict actuator slew-rate enforcement ($\le 5.0^\circ/\text{s}$). | 1000x600 PNG |

---

### Verification & Generation
All synthetic and empirical data in these figures are generated deterministically by the Phoenix-X software suite:
```bash
python3 scripts/generate_submission_images.py
```
