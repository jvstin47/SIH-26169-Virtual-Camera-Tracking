#!/usr/bin/env python3
"""
Phoenix-X: Automated Scientific Research Ladder & Ablation Benchmark Runner
Problem Statement ID: SIH 26169 (ISRO / SAC)

Directly implements Direction A, B, C, D, and F:
Evaluates 3 distinct architectural tiers across identical simulated conditions:
  Tier 1: Naive Baseline (Simple Threshold -> Unweighted Centroid -> No Estimator -> P Controller)
  Tier 2: Classical Filtered (Median Filter -> Binary Moments -> CV Kalman -> PI Controller)
  Tier 3: Phoenix-X Proposed (Morphological Saliency -> IWC Subpixel -> Kalman Feedforward -> Anti-windup PID -> Spiral Reacquisition)

Sweeps across:
  - Trajectories: Linear, Circular, Figure-8, Random
  - Disturbance: 0%, 5%, 10% (PS Benchmark), 20% Salt & Pepper Noise
  - Temporary Loss: 15-frame dropout to measure Re-acquisition Latency
"""

import os
import sys
import math
import time
import csv
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import numpy as np
import cv2

# Project paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from src.core.coordinates import Point2D, CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX, DEG_PER_PIXEL
from src.simulation.trajectories import TrajectoryGenerator
from src.optics.atmosphere_and_noise import OpticalEngine, inject_salt_and_pepper_noise
from src.camera.ptz_camera import VirtualPTZCamera

@dataclass
class BenchmarkResult:
    tier_name: str
    trajectory: str
    noise_ratio: float
    rmse_px: float
    mae_px: float
    max_error_px: float
    compliance_rate_pct: float
    reacquisition_frames: Optional[int]
    fps: float

# =============================================================================
# Perception & Control Tiers
# =============================================================================

class Tier1NaiveBaseline:
    """Tier 1: Raw Thresholding, Unweighted Centroid, No Estimator, P-Control."""
    def __init__(self):
        self.kp = 3.5

    def detect(self, frame: np.ndarray) -> Optional[Point2D]:
        # Simple fixed global threshold without spatial filtering
        _, thresh = cv2.threshold(frame, 60, 255, cv2.THRESH_BINARY)
        M = cv2.moments(thresh)
        if M["m00"] > 0:
            return Point2D(M["m10"] / M["m00"], M["m01"] / M["m00"])
        return None

    def control(self, detected: Optional[Point2D], dt: float) -> Tuple[float, float]:
        cx, cy = CAMERA_WIDTH_PX / 2.0, CAMERA_HEIGHT_PX / 2.0
        if detected is None:
            return (0.0, 0.0) # No prediction, freezes in place
        err_x = detected.x - cx
        err_y = detected.y - cy
        return (self.kp * err_x, self.kp * err_y)


class Tier2ClassicalFiltered:
    """Tier 2: Median Denoising, Binary Moments, Constant Velocity Kalman, PI Controller."""
    def __init__(self):
        self.kp = 4.5
        self.ki = 0.5
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.state = np.zeros((4, 1)) # [x, y, vx, vy]
        self.cov = np.eye(4) * 50.0
        self.Q = np.diag([2.0, 2.0, 30.0, 30.0])
        self.R = np.diag([1.5, 1.5])
        self.initialized = False

    def detect(self, frame: np.ndarray) -> Optional[Point2D]:
        denoised = cv2.medianBlur(frame, 3)
        _, thresh = cv2.threshold(denoised, 50, 255, cv2.THRESH_BINARY)
        M = cv2.moments(thresh)
        if M["m00"] > 0:
            return Point2D(M["m10"] / M["m00"], M["m01"] / M["m00"])
        return None

    def control(self, detected: Optional[Point2D], dt: float) -> Tuple[float, float]:
        cx, cy = CAMERA_WIDTH_PX / 2.0, CAMERA_HEIGHT_PX / 2.0
        F = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]])
        H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])

        if detected is None:
            if self.initialized:
                self.state = F @ self.state
                return (float(self.state[2, 0]), float(self.state[3, 0]))
            return (0.0, 0.0)

        meas = np.array([[detected.x], [detected.y]])
        if not self.initialized:
            self.state = np.array([[detected.x], [detected.y], [0.0], [0.0]])
            self.initialized = True
        else:
            self.state = F @ self.state
            self.cov = F @ self.cov @ F.T + self.Q
            y_res = meas - H @ self.state
            S = H @ self.cov @ H.T + self.R
            K = self.cov @ H.T @ np.linalg.inv(S)
            self.state = self.state + K @ y_res
            self.cov = (np.eye(4) - K @ H) @ self.cov

        fx, fy = float(self.state[0, 0]), float(self.state[1, 0])
        err_x = fx - cx
        err_y = fy - cy
        self.integral_x += err_x * dt
        self.integral_y += err_y * dt
        return (self.kp * err_x + self.ki * self.integral_x,
                self.kp * err_y + self.ki * self.integral_y)


class Tier3PhoenixXProposed:
    """Tier 3: Morphological Saliency + IWC Subpixel + Kalman Velocity Feedforward + Anti-windup PID + Spiral Reacquisition."""
    def __init__(self):
        self.kp = 6.2
        self.ki = 1.2
        self.kd = 0.5
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.prev_err_x = 0.0
        self.prev_err_y = 0.0
        self.state = np.zeros((4, 1))
        self.cov = np.eye(4) * 20.0
        self.Q = np.diag([0.5, 0.5, 15.0, 15.0])
        self.R = np.diag([0.2, 0.2])
        self.initialized = False
        self.loss_counter = 0
        self.last_pos: Optional[Point2D] = None

    def detect(self, frame: np.ndarray) -> Optional[Point2D]:
        denoised = cv2.medianBlur(frame, 5)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        denoised = cv2.morphologyEx(denoised, cv2.MORPH_OPEN, kernel)
        bg = float(np.percentile(denoised, 60))
        fg = np.maximum(0, denoised.astype(np.float32) - bg)
        min_v, max_v, _, max_loc = cv2.minMaxLoc(fg)
        if max_v < 15.0:
            return None
        px, py = max_loc

        # Direction B: Kinematic gating to reject outlier noise clusters
        if self.last_pos is not None:
            if math.hypot(px - self.last_pos.x, py - self.last_pos.y) > 60.0:
                h, w = frame.shape
                gx1, gx2 = max(0, int(self.last_pos.x - 45)), min(w, int(self.last_pos.x + 46))
                gy1, gy2 = max(0, int(self.last_pos.y - 45)), min(h, int(self.last_pos.y + 46))
                local_gate = fg[gy1:gy2, gx1:gx2]
                _, l_max_v, _, l_max_loc = cv2.minMaxLoc(local_gate)
                if l_max_v > 15.0:
                    px = gx1 + l_max_loc[0]
                    py = gy1 + l_max_loc[1]

        r = 7
        h, w = frame.shape
        y1, y2 = max(0, py - r), min(h, py + r + 1)
        x1, x2 = max(0, px - r), min(w, px + r + 1)
        patch = fg[y1:y2, x1:x2]
        tot = np.sum(patch)
        if tot <= 0:
            pt = Point2D(float(px), float(py))
        else:
            gy, gx = np.ogrid[y1:y2, x1:x2]
            sub_x = float(np.sum(gx * patch) / tot)
            sub_y = float(np.sum(gy * patch) / tot)
            pt = Point2D(sub_x, sub_y)

        self.last_pos = pt
        return pt

    def control(self, detected: Optional[Point2D], dt: float) -> Tuple[float, float]:
        cx, cy = CAMERA_WIDTH_PX / 2.0, CAMERA_HEIGHT_PX / 2.0
        F = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]])
        H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])

        if detected is None:
            self.loss_counter += 1
            if self.loss_counter > 5:
                # Deterministic Archimedean spiral search
                t = (self.loss_counter - 5) * dt
                rad = min(180.0, 20.0 + t * 40.0)
                ang = t * 4.0
                return (rad * 4.0 * (-math.sin(ang)), rad * 4.0 * (math.cos(ang)))
            if self.initialized:
                self.state = F @ self.state
                return (float(self.state[2, 0]), float(self.state[3, 0]))
            return (0.0, 0.0)

        self.loss_counter = 0
        meas = np.array([[detected.x], [detected.y]])
        if not self.initialized:
            self.state = np.array([[detected.x], [detected.y], [0.0], [0.0]])
            self.initialized = True
        else:
            self.state = F @ self.state
            self.cov = F @ self.cov @ F.T + self.Q
            y_res = meas - H @ self.state
            S = H @ self.cov @ H.T + self.R
            K = self.cov @ H.T @ np.linalg.inv(S)
            self.state = self.state + K @ y_res
            self.cov = (np.eye(4) - K @ H) @ self.cov

        fx, fy = float(self.state[0, 0]), float(self.state[1, 0])
        vx_est, vy_est = float(self.state[2, 0]), float(self.state[3, 0])
        err_x = fx - cx
        err_y = fy - cy

        # Anti-windup clamped PID + Feedforward
        self.integral_x = np.clip(self.integral_x + err_x * dt, -40.0, 40.0)
        self.integral_y = np.clip(self.integral_y + err_y * dt, -40.0, 40.0)
        der_x = (err_x - self.prev_err_x) / dt if dt > 0 else 0.0
        der_y = (err_y - self.prev_err_y) / dt if dt > 0 else 0.0
        self.prev_err_x, self.prev_err_y = err_x, err_y

        cmd_x = (self.kp * err_x) + (self.ki * self.integral_x) + (self.kd * der_x) + (0.5 * vx_est)
        cmd_y = (self.kp * err_y) + (self.ki * self.integral_y) + (self.kd * der_y) + (0.5 * vy_est)
        return (cmd_x, cmd_y)


# =============================================================================
# Automated Benchmark Runner
# =============================================================================

def run_single_benchmark(tier_cls, trajectory_type: str, noise_ratio: float, inject_dropout: bool = False, num_frames: int = 150) -> BenchmarkResult:
    dt = 1.0 / 30.0
    traj = TrajectoryGenerator(mode=trajectory_type)
    optics = OpticalEngine()
    optics.enable_salt_and_pepper = (noise_ratio > 0.0)
    optics.salt_and_pepper_ratio = noise_ratio
    t0 = traj.get_position(0.0)
    # Coarse Handover initial offset: beacon starts inside FOV (~43 px from boresight)
    camera = VirtualPTZCamera(initial_x=t0.x + 35.0, initial_y=t0.y + 25.0)
    tier = tier_cls()

    errors_px = []
    reacquisition_frames = None
    dropout_start = 60
    dropout_duration = 15 # 0.5s loss
    dropout_reacquired = False

    t_start = time.perf_counter()

    for frame_idx in range(num_frames):
        t = frame_idx * dt
        # 1. Target true universe position
        pos = traj.get_position(t)
        tx, ty = pos.x, pos.y
        
        # 2. Camera Viewport Crop
        cx, cy = camera.x, camera.y
        local_tx = tx - (cx - CAMERA_WIDTH_PX / 2.0)
        local_ty = ty - (cy - CAMERA_HEIGHT_PX / 2.0)

        # 3. Render frame
        frame = np.zeros((CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX), dtype=np.uint8)
        
        # Inject artificial dropout
        is_dropped = inject_dropout and (dropout_start <= frame_idx < (dropout_start + dropout_duration))
        if not is_dropped and (0 <= local_tx < CAMERA_WIDTH_PX) and (0 <= local_ty < CAMERA_HEIGHT_PX):
            frame = optics.render_beacon_on_frame(frame, local_tx, local_ty)
        
        frame = optics.apply_disturbances(frame)
        if noise_ratio > 0.0:
            frame = inject_salt_and_pepper_noise(frame, noise_ratio=noise_ratio)

        # 4. Perception & Centroiding
        detected = tier.detect(frame)

        # 5. Measure True Tracking Error (Relative to bore-sight: 320, 240)
        optical_center_x = CAMERA_WIDTH_PX / 2.0
        optical_center_y = CAMERA_HEIGHT_PX / 2.0
        true_err = math.hypot(local_tx - optical_center_x, local_ty - optical_center_y)
        errors_px.append(true_err)

        # Measure reacquisition recovery
        if inject_dropout and frame_idx >= (dropout_start + dropout_duration) and not dropout_reacquired:
            if detected is not None and true_err <= 10.0:
                reacquisition_frames = frame_idx - (dropout_start + dropout_duration)
                dropout_reacquired = True

        # 6. Gimbal Actuation
        cmd_vx, cmd_vy = tier.control(detected, dt)
        camera.update_actuator(cmd_vx, cmd_vy, dt)

    t_total = time.perf_counter() - t_start
    fps = num_frames / max(1e-4, t_total)

    valid_errs = [e for e in errors_px if e < 800.0]
    rmse = math.sqrt(np.mean(np.square(valid_errs)))
    mae = float(np.mean(valid_errs))
    max_e = float(np.max(valid_errs))
    comp_rate = (sum(1 for e in valid_errs if e <= 10.0) / len(valid_errs)) * 100.0

    return BenchmarkResult(
        tier_name=tier_cls.__name__,
        trajectory=trajectory_type,
        noise_ratio=noise_ratio,
        rmse_px=rmse,
        mae_px=mae,
        max_error_px=max_e,
        compliance_rate_pct=comp_rate,
        reacquisition_frames=reacquisition_frames,
        fps=fps
    )


def main():
    print("=" * 80)
    print("  PHOENIX-X: AUTOMATED RESEARCH LADDER ABLATION BENCHMARK (SIH 26169)")
    print("=" * 80)
    print("[*] Running comparative ablation sweeps across 3 architectural tiers...")

    tiers = [
        ("Tier-1 Naive Baseline", Tier1NaiveBaseline),
        ("Tier-2 Classical Filtered", Tier2ClassicalFiltered),
        ("Tier-3 Phoenix-X Proposed", Tier3PhoenixXProposed)
    ]

    scenarios = [
        ("Linear (Nominal)", "straight_line", 0.0, False),
        ("Circular (Maneuver)", "circular", 0.05, False),
        ("Figure-8 + 10% Noise (PS Benchmark)", "figure_8", 0.10, False),
        ("Figure-8 + 20% Extreme Noise", "figure_8", 0.20, False),
        ("Random + 15-Frame Occlusion Dropout", "random", 0.10, True),
    ]

    results: List[BenchmarkResult] = []

    for sc_name, traj, noise, dropout in scenarios:
        print(f"\n--> Scenario: {sc_name}")
        for t_label, t_cls in tiers:
            res = run_single_benchmark(t_cls, traj, noise, inject_dropout=dropout, num_frames=120)
            res.tier_name = t_label
            results.append(res)
            reacq_str = f"{res.reacquisition_frames} frames" if res.reacquisition_frames is not None else "LOST / >1s"
            print(f"    [{t_label:<26}] RMSE: {res.rmse_px:5.2f} px | Compliance: {res.compliance_rate_pct:5.1f}% | Reacq: {reacq_str} | Speed: {res.fps:4.0f} FPS")

    # Export to CSV
    os.makedirs("output_reports", exist_ok=True)
    csv_file = "output_reports/research_ladder_ablation_results.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Tier", "Scenario_Trajectory", "Noise_Ratio", "RMSE_px", "MAE_px", "Max_Error_px", "Compliance_Rate_pct", "Reacquisition_Frames", "Throughput_FPS"])
        for r in results:
            writer.writerow([
                r.tier_name, r.trajectory, r.noise_ratio,
                f"{r.rmse_px:.3f}", f"{r.mae_px:.3f}", f"{r.max_error_px:.3f}",
                f"{r.compliance_rate_pct:.1f}", r.reacquisition_frames if r.reacquisition_frames is not None else "N/A",
                f"{r.fps:.1f}"
            ])

    print(f"\n[+] Full ablation audit exported to: {csv_file}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
