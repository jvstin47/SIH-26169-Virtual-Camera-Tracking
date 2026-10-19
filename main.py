#!/usr/bin/env python3
"""
SIH 26169 Master Application Entrypoint
Problem Statement ID: SIH 26169 (ISRO / SAC)
AI-Based Virtual Camera Tracking System for Mobile Free Space Optical Communication (FSOC)

Runs an interactive, real-time SIL simulator and vision tracking loop at 30-60 FPS.
"""

import sys
import os
import time
import math
import argparse
import csv
import numpy as np
import cv2

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.coordinates import (
    Point2D, UNIVERSE_WIDTH_PX, UNIVERSE_HEIGHT_PX,
    CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX, ARCSEC_PER_PIXEL,
    DEFAULT_MAX_SLEW_RATE_DEG_S, DEG_PER_PIXEL
)
from src.simulation.trajectories import TrajectoryGenerator
from src.optics.atmosphere_and_noise import OpticalEngine
from src.camera.ptz_camera import VirtualPTZCamera
from src.vision.tracker import BeaconTracker
from src.control.gimbal_controller import GimbalController

class PhoenixXSimulator:
    def __init__(self, headless: bool = False, light_mode: bool = False):
        self.headless = headless
        self.light_mode = light_mode
        
        # Subsystems
        self.trajectory = TrajectoryGenerator(mode="figure_8", speed=1.0)
        self.optics = OpticalEngine(spot_size_px=10, spot_peak_intensity=250)
        self.camera = VirtualPTZCamera()
        self.tracker = BeaconTracker()
        self.controller = GimbalController()
        
        # State & Telemetry History
        self.start_time = time.time()
        self.frame_count = 0
        self.history_errors = []
        self.history_timestamps = []
        self.trajectory_modes = ["figure_8", "circular", "sinusoidal", "random", "straight_line"]
        self.current_traj_idx = 0
        
        # Log directory
        os.makedirs("output_reports", exist_ok=True)

    def run(self, max_seconds: float = None):
        print("=" * 70)
        print("  PHOENIX-X: AI-BASED VIRTUAL CAMERA TRACKING SYSTEM (SIH 26169)")
        print("  Sponsoring Organization: ISRO / Space Applications Centre (SAC)")
        print("=" * 70)
        print("\n[+] Simulator initialized. Starting real-time tracking loop...")
        print("\nInteractive Keyboard Controls:")
        print("  [1] Toggle 10% Salt & Pepper Noise")
        print("  [2] Toggle Poisson & Gaussian Sensor Noise")
        print("  [3] Toggle Heavy Fog / Atmospheric Attenuation")
        print("  [4] Toggle Platform Multi-Harmonic Jitter (±20 px)")
        print("  [T] Cycle Target Trajectory (Figure-8 / Circular / Sinusoidal / etc.)")
        print("  [R] Reset Gimbal Pointing to Center")
        print("  [L] Toggle Light / Dark Cockpit Theme")
        print("  [Q] or [ESC] Quit and Export CSV Performance Audit Log\n")

        fps_timer = time.time()
        measured_fps = 30.0
        dt = 0.0333  # ~30 Hz nominal tick
        
        trail_points = []
        max_trail = 80

        while True:
            t_start = time.time()
            sim_time = t_start - self.start_time
            self.frame_count += 1
            
            # Check maximum duration if specified
            if max_seconds and sim_time >= max_seconds:
                break

            # -------------------------------------------------------------
            # STEP 1: Compute True Global Target Kinematics & Jitter
            # -------------------------------------------------------------
            true_pos = self.trajectory.get_position(sim_time)
            jx, jy = self.optics.get_platform_jitter(sim_time)
            
            # Target position with jitter relative to camera
            apparent_target_x = true_pos.x + jx
            apparent_target_y = true_pos.y + jy
            
            trail_points.append((int(true_pos.x), int(true_pos.y)))
            if len(trail_points) > max_trail:
                trail_points.pop(0)

            # -------------------------------------------------------------
            # STEP 2: Render Camera Sensor Frame (640x480)
            # -------------------------------------------------------------
            # Initialize sensor with low thermal background dark current
            sensor_frame = np.full((CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX), 12, dtype=np.uint8)
            
            # Convert global apparent target to local viewport coordinates
            local_target = self.camera.global_to_local(apparent_target_x, apparent_target_y)
            
            # Render diffraction-limited Airy spot profile
            sensor_frame = self.optics.render_beacon_on_frame(sensor_frame, local_target.x, local_target.y)
            
            # Convolve atmospheric fog and stochastic noise (10% S&P, Poisson, Gauss)
            degraded_frame = self.optics.apply_disturbances(sensor_frame)

            # -------------------------------------------------------------
            # STEP 3: Computer Vision & Sub-Pixel AI Centroiding Core
            # -------------------------------------------------------------
            detected_point, error_px, snr_db = self.tracker.process_frame(degraded_frame)
            error_arcsec = error_px * ARCSEC_PER_PIXEL if detected_point else 999.0
            
            if detected_point:
                self.history_errors.append(error_px)
            else:
                self.history_errors.append(999.0)
            self.history_timestamps.append(sim_time)

            # -------------------------------------------------------------
            # STEP 4: Predictive IMM-Kalman Filter & Gimbal Servo Control
            # -------------------------------------------------------------
            cmd_vx, cmd_vy = self.controller.update(detected_point, dt)
            self.camera.update_actuator(cmd_vx, cmd_vy, dt)
            
            current_slew_deg_s = math.hypot(self.camera.vx_deg_s, self.camera.vy_deg_s)

            # -------------------------------------------------------------
            # STEP 5: FPS Calculation & Telemetry
            # -------------------------------------------------------------
            if self.frame_count % 15 == 0:
                now = time.time()
                elapsed = now - fps_timer
                if elapsed > 0:
                    measured_fps = 15.0 / elapsed
                fps_timer = now

            # -------------------------------------------------------------
            # STEP 6: Render Visual Cockpit GUI (if not headless)
            # -------------------------------------------------------------
            if not self.headless:
                ui_frame = self._render_cockpit(
                    degraded_frame, local_target, detected_point,
                    error_px, error_arcsec, current_slew_deg_s,
                    measured_fps, snr_db, trail_points, sim_time
                )
                
                cv2.imshow("SIH 26169: FSOC Virtual Camera Tracker", ui_frame)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:  # Q or ESC
                    break
                elif key == ord('1'):
                    self.optics.enable_salt_and_pepper = not self.optics.enable_salt_and_pepper
                    print(f"[*] 10% Salt & Pepper Noise: {'ENABLED' if self.optics.enable_salt_and_pepper else 'DISABLED'}")
                elif key == ord('2'):
                    self.optics.enable_poisson = not self.optics.enable_poisson
                    self.optics.enable_gaussian = self.optics.enable_poisson
                    print(f"[*] Poisson & Gaussian Noise: {'ENABLED' if self.optics.enable_poisson else 'DISABLED'}")
                elif key == ord('3'):
                    self.optics.enable_fog = not self.optics.enable_fog
                    print(f"[*] Atmospheric Fog Attenuation: {'ENABLED' if self.optics.enable_fog else 'DISABLED'}")
                elif key == ord('4'):
                    self.optics.enable_jitter = not self.optics.enable_jitter
                    print(f"[*] Platform Jitter (±20 px): {'ENABLED' if self.optics.enable_jitter else 'DISABLED'}")
                elif key == ord('t') or key == ord('T'):
                    self.current_traj_idx = (self.current_traj_idx + 1) % len(self.trajectory_modes)
                    new_mode = self.trajectory_modes[self.current_traj_idx]
                    self.trajectory.set_mode(new_mode)
                    self.controller.reset()
                    print(f"[*] Trajectory Switched to: {new_mode.upper()}")
                elif key == ord('r') or key == ord('R'):
                    self.camera.x = UNIVERSE_WIDTH_PX / 2.0
                    self.camera.y = UNIVERSE_HEIGHT_PX / 2.0
                    self.controller.reset()
                    print("[*] Camera Reset to Center.")
                elif key == ord('l') or key == ord('L'):
                    self.light_mode = not self.light_mode
                    print(f"[*] Visual Theme Switched to: {'LIGHT MODE (Engineering HUD)' if self.light_mode else 'DARK MODE (Tactical Deep Space)'}")

            # Frame rate pacing to nominal ~30-40 Hz
            t_elapsed = time.time() - t_start
            sleep_time = max(0.001, dt - t_elapsed)
            time.sleep(sleep_time)

        if not self.headless:
            cv2.destroyAllWindows()
            
        self._export_performance_report()

    def _render_cockpit(self, camera_frame, local_target, detected_point,
                        error_px, error_arcsec, slew_rate, fps, snr_db, trail, sim_time):
        """Builds a high-resolution, dual-theme tactical dual-viewport cockpit."""
        # Theme color definitions
        if self.light_mode:
            bg_canvas = (244, 247, 252)         # Soft slate white
            bg_minimap = (235, 240, 248)        # Pale ice minimap
            border_viewport = (195, 205, 220)   # Clean slate border
            grid_minor_col = (220, 226, 236)    # Subtle grey grid
            grid_major_col = (190, 202, 218)    # Distinct grey grid
            grid_ring_col = (205, 215, 230)     # Pale ring
            axis_ticks_col = (100, 115, 135)    # Slate ticks
            crosshair_cam = (140, 140, 140)     # Visible crosshair
            crosshair_radius_col = (160, 160, 160)
            text_title = (20, 35, 55)           # Deep Space Navy
            text_subtitle = (180, 95, 0)        # Deep Azure
            text_label = (70, 85, 105)          # Muted Slate
            text_val = (15, 25, 40)             # Charcoal Black
            fov_box_col = (210, 110, 0)         # Royal Blue
            trail_col = (160, 50, 90)           # Deep Indigo
            target_spot_col = (0, 130, 255)     # Deep Amber/Orange
            btn_off_bg = (225, 230, 240)        # Inactive button BG
            btn_off_txt = (90, 105, 125)        # Inactive button text
            btn_on_bg = (200, 240, 210)         # Soft Mint Green
            btn_on_txt = (15, 80, 30)           # Active button text
        else:
            bg_canvas = (20, 24, 30)            # Dark Space Slate
            bg_minimap = (8, 12, 18)            # Deep Black Minimap
            border_viewport = (60, 70, 85)      # Slate Border
            grid_minor_col = (22, 32, 45)       # Faint Grid
            grid_major_col = (40, 58, 80)       # Major Grid
            grid_ring_col = (28, 42, 60)        # Range Ring
            axis_ticks_col = (80, 105, 135)     # Dim Ticks
            crosshair_cam = (80, 80, 80)        # Dim Crosshair
            crosshair_radius_col = (100, 100, 100)
            text_title = (220, 225, 235)        # Crisp White
            text_subtitle = (0, 190, 255)       # Bright Cyan/Amber
            text_label = (160, 170, 185)        # Slate Grey
            text_val = (200, 205, 215)          # Light Grey
            fov_box_col = (0, 180, 255)         # Bright Amber
            trail_col = (100, 70, 200)          # Purple Trail
            target_spot_col = (0, 255, 255)     # Bright Yellow
            btn_off_bg = (30, 35, 45)           # Inactive button BG
            btn_off_txt = (160, 160, 160)       # Inactive button text
            btn_on_bg = (0, 230, 115)           # Neon Green
            btn_on_txt = (0, 0, 0)              # Active button text

        # Canvas dimensions: 1100 x 640
        canvas = np.zeros((640, 1100, 3), dtype=np.uint8)
        canvas[:] = bg_canvas
        
        # -------------------------------------------------------------
        # Viewport 1: Active 640x480 Camera View (Right Side)
        # -------------------------------------------------------------
        cam_bgr = cv2.cvtColor(camera_frame, cv2.COLOR_GRAY2BGR)
        cx = int(CAMERA_WIDTH_PX / 2)
        cy = int(CAMERA_HEIGHT_PX / 2)
        
        # Draw central optical crosshairs
        cv2.line(cam_bgr, (cx - 20, cy), (cx + 20, cy), crosshair_cam, 1)
        cv2.line(cam_bgr, (cx, cy - 20), (cx, cy + 20), crosshair_cam, 1)
        cv2.circle(cam_bgr, (cx, cy), 10, crosshair_radius_col, 1) # 10 px PS threshold radius
        
        # Draw detected beacon reticle
        if detected_point:
            dx = int(round(detected_point.x))
            dy = int(round(detected_point.y))
            # Tracking lock box
            lock_color = (0, 200, 90) if error_px <= 10.0 else (0, 140, 255)
            cv2.rectangle(cam_bgr, (dx - 12, dy - 12), (dx + 12, dy + 12), lock_color, 1)
            cv2.circle(cam_bgr, (dx, dy), 2, (0, 255, 255) if not self.light_mode else (220, 100, 0), -1)
            # Line connecting centroid to center
            cv2.line(cam_bgr, (cx, cy), (dx, dy), (0, 140, 255), 1)
            
        # Border around camera view
        cv2.rectangle(cam_bgr, (0, 0), (CAMERA_WIDTH_PX - 1, CAMERA_HEIGHT_PX - 1), border_viewport, 2)
        canvas[40:520, 430:1070] = cam_bgr
        
        # -------------------------------------------------------------
        # Viewport 2: Global Universe 2000x2000 Minimap (Left Side)
        # -------------------------------------------------------------
        minimap_size = 360
        scale = minimap_size / float(UNIVERSE_WIDTH_PX)
        minimap = np.zeros((minimap_size, minimap_size, 3), dtype=np.uint8)
        minimap[:] = bg_minimap
        
        # Draw Minor Grid Lines
        for g in range(0, minimap_size, int(250 * scale)):
            cv2.line(minimap, (g, 0), (g, minimap_size), grid_minor_col, 1)
            cv2.line(minimap, (0, g), (minimap_size, g), grid_minor_col, 1)

        # Draw Major Grid Lines
        for g in range(0, minimap_size + 1, int(500 * scale)):
            cv2.line(minimap, (g, 0), (g, minimap_size), grid_major_col, 1)
            cv2.line(minimap, (0, g), (minimap_size, g), grid_major_col, 1)

        # Draw Range Rings from Center
        center_m = (int(minimap_size / 2), int(minimap_size / 2))
        for r_ring in [250, 500, 750]:
            cv2.circle(minimap, center_m, int(r_ring * scale), grid_ring_col, 1)

        # Center Crosshair
        cx_m, cy_m = center_m
        cv2.line(minimap, (cx_m - 8, cy_m), (cx_m + 8, cy_m), fov_box_col, 1)
        cv2.line(minimap, (cx_m, cy_m - 8), (cx_m, cy_m + 8), fov_box_col, 1)

        # Coordinate Axis Ticks
        for px_val in [500, 1000, 1500]:
            g_pos = int(px_val * scale)
            cv2.putText(minimap, str(px_val), (g_pos - 10, minimap_size - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, axis_ticks_col, 1)
            cv2.putText(minimap, str(px_val), (3, g_pos + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, axis_ticks_col, 1)
            
        # Draw trajectory trail
        for p1, p2 in zip(trail[:-1], trail[1:]):
            m1 = (int(p1[0] * scale), int(p1[1] * scale))
            m2 = (int(p2[0] * scale), int(p2[1] * scale))
            cv2.line(minimap, m1, m2, trail_col, 1)
            
        # Draw camera FOV box in universe
        cam_top_left = (int((self.camera.x - CAMERA_WIDTH_PX/2) * scale),
                        int((self.camera.y - CAMERA_HEIGHT_PX/2) * scale))
        cam_bot_right = (int((self.camera.x + CAMERA_WIDTH_PX/2) * scale),
                         int((self.camera.y + CAMERA_HEIGHT_PX/2) * scale))
        cv2.rectangle(minimap, cam_top_left, cam_bot_right, fov_box_col, 2)
        cv2.putText(minimap, "FOV", (cam_top_left[0] + 3, max(12, cam_top_left[1] - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, fov_box_col, 1)
        
        # Draw true target spot on minimap
        if trail:
            cur_tgt = (int(trail[-1][0] * scale), int(trail[-1][1] * scale))
            cv2.circle(minimap, cur_tgt, 5, target_spot_col, -1)
            cv2.circle(minimap, cur_tgt, 9, target_spot_col, 1)
            
        cv2.rectangle(minimap, (0, 0), (minimap_size - 1, minimap_size - 1), border_viewport, 1)
        canvas[40:400, 30:390] = minimap

        # -------------------------------------------------------------
        # Text Overlays, Headers & Telemetry Cards
        # -------------------------------------------------------------
        # Title Header
        cv2.putText(canvas, "SIH 26169 // FSOC VIRTUAL CAMERA TRACKING SYSTEM", (30, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, text_title, 2)
        cv2.putText(canvas, "ISRO SAC - PROBLEM STATEMENT 26169", (730, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, text_subtitle, 1)

        # Minimap Label
        cv2.putText(canvas, "GLOBAL UNIVERSE (2000x2000)", (30, 420),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, text_label, 1)
        # Camera Label
        status_txt = "LOCK ACQUIRED" if (detected_point and error_px <= 10.0) else "ACQUIRING..."
        status_col = (0, 180, 75) if (detected_point and error_px <= 10.0) else (0, 140, 255)
        cv2.putText(canvas, f"ACTIVE CAMERA FPA (640x480) - {status_txt}", (430, 540),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_col, 1)

        # Telemetry Block (Bottom Left)
        ty = 445
        cv2.putText(canvas, f"TRAJECTORY : {self.trajectory.mode.upper()}", (30, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.42, text_val, 1)
        cv2.putText(canvas, f"CENTROID ERR: {error_px:5.2f} px ({error_arcsec:5.1f}\")", (30, ty + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 160, 220) if self.light_mode else (0, 255, 255), 1)
        cv2.putText(canvas, f"PS REQ (<=10): <= 10.0 px (COMPLIANT)" if error_px <= 10.0 else "PS REQ (<=10): <= 10.0 px (ALIGNING)", (30, ty + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 160, 60) if error_px <= 10.0 else (0, 140, 255), 1)
        cv2.putText(canvas, f"SLEW RATE   : {slew_rate:4.2f} deg/s (Limit: 5.0)", (30, ty + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.42, text_val, 1)
        cv2.putText(canvas, f"THROUGHPUT  : {fps:4.1f} FPS (Target: >= 30)", (30, ty + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 160, 60), 1)
        cv2.putText(canvas, f"SNR (dB)    : {snr_db:4.1f} dB", (30, ty + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.42, text_val, 1)

        # Disturbance & Theme Buttons (Bottom Right)
        dy = 570
        def draw_btn(x1, x2, label, active):
            c_bg = btn_on_bg if active else btn_off_bg
            c_txt = btn_on_txt if active else btn_off_txt
            cv2.rectangle(canvas, (x1, dy), (x2, dy + 25), c_bg, -1)
            cv2.rectangle(canvas, (x1, dy), (x2, dy + 25), border_viewport, 1)
            cv2.putText(canvas, label, (x1 + 6, dy + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_txt, 1)
        
        draw_btn(430, 545, "[1] 10% S&P", self.optics.enable_salt_and_pepper)
        draw_btn(555, 675, "[2] POISSON", self.optics.enable_poisson)
        draw_btn(685, 795, "[3] FOG/HAZE", self.optics.enable_fog)
        draw_btn(805, 935, "[4] JITTER", self.optics.enable_jitter)
        draw_btn(945, 1070, "[L] LIGHT HUD" if self.light_mode else "[L] DARK HUD", self.light_mode)

        cv2.putText(canvas, "Press [T] trajectory | [R] reset | [L] theme | [Q] quit & save report", (430, 615),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, text_label, 1)

        return canvas

    def _export_performance_report(self):
        """Generates and exports an automated ISRO compliance CSV report."""
        valid_errors = [e for e in self.history_errors if e < 900.0]
        rmse = math.sqrt(sum(e**2 for e in valid_errors) / max(1, len(valid_errors))) if valid_errors else 999.0
        lock_rate = (len(valid_errors) / max(1, len(self.history_errors))) * 100.0
        mean_err = np.mean(valid_errors) if valid_errors else 999.0
        max_err = np.max(valid_errors) if valid_errors else 999.0
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_filename = f"output_reports/isro_benchmark_report_{timestamp}.csv"
        
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["--- PHOENIX-X FSOC TRACKING AUDIT REPORT (ISRO SAC SIH 26169) ---"])
            writer.writerow(["Metric", "Achieved Value", "PS Requirement Bound", "Compliance Status"])
            writer.writerow(["Simulation Duration (s)", f"{self.history_timestamps[-1]:.2f}" if self.history_timestamps else "0.0", "N/A", "COMPLETED"])
            writer.writerow(["Lock Retention Rate (%)", f"{lock_rate:.2f}%", "> 95.0%", "PASS" if lock_rate >= 95.0 else "REVIEW"])
            writer.writerow(["RMSE Centroid Error (px)", f"{rmse:.3f} px", "<= 10.0 px", "PASS" if rmse <= 10.0 else "FAIL"])
            writer.writerow(["Mean Centroid Error (px)", f"{mean_err:.3f} px", "<= 10.0 px", "PASS" if mean_err <= 10.0 else "FAIL"])
            writer.writerow(["Max Centroid Error (px)", f"{max_err:.3f} px", "N/A", "RECORDED"])
            writer.writerow(["Max Slew Rate Enforced", "5.0 deg/s", "5-10 deg/s", "COMPLIANT"])
            writer.writerow([])
            writer.writerow(["Frame_ID", "Timestamp_s", "Centroid_Error_px"])
            for idx, (t, err) in enumerate(zip(self.history_timestamps, self.history_errors)):
                writer.writerow([idx + 1, f"{t:.4f}", f"{err:.3f}"])
                
        print("\n" + "=" * 70)
        print(f"[+] Simulation session completed!")
        print(f"    Total Frames Simulated : {len(self.history_errors)}")
        print(f"    Lock Retention Rate    : {lock_rate:.2f}%")
        print(f"    Centroid RMSE Error    : {rmse:.3f} px (PS Requirement Target: <= 10.0 px)")
        print(f"    Saved Compliance Report: {csv_filename}")
        print("=" * 70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Phoenix-X FSOC Virtual Camera Tracker (SIH 26169)")
    parser.add_argument("--headless", action="store_true", help="Run without GUI window for automated testing")
    parser.add_argument("--light-mode", action="store_true", help="Launch with high-contrast light theme HUD")
    parser.add_argument("--duration", type=float, default=None, help="Run simulation for specific duration in seconds")
    parser.add_argument("--video", type=str, default=None, help="Path to external .mp4 video file (ISRO Benchmark-2 mode)")
    parser.add_argument("--select-roi", action="store_true", help="Click and drag to select any arbitrary object to track in video")
    parser.add_argument("--ground-truth", type=str, default=None, help="Path to ground truth CSV coordinates for verification")
    args = parser.parse_args()
    
    if args.video:
        # Launch ISRO Benchmark-2 Decoupled Video Processor
        from src.benchmarking.mp4_bypass import VideoBenchmarkRunner
        runner = VideoBenchmarkRunner(
            video_path=args.video,
            select_roi=args.select_roi,
            ground_truth_path=args.ground_truth
        )
        runner.run()
    else:
        # Launch Closed-Loop Interactive Simulator
        sim = PhoenixXSimulator(headless=args.headless, light_mode=args.light_mode)
        sim.run(max_seconds=args.duration)

if __name__ == "__main__":
    main()
