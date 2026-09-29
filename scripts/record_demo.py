#!/usr/bin/env python3
"""
Phoenix-X Automated Demonstration Video Recorder
Problem Statement ID: SIH 26169 (ISRO / SAC)
Generates an official high-definition demonstration MP4 video for submission
and evaluation. Showcases all disturbances, trajectory modes, and real-time telemetry HUD.
"""

import os
import sys
import time
import math
import numpy as np
import cv2

# Add workspace root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.coordinates import (
    Point2D, UNIVERSE_WIDTH_PX, UNIVERSE_HEIGHT_PX,
    CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX, ARCSEC_PER_PIXEL,
    DEG_PER_PIXEL
)
from src.simulation.trajectories import TrajectoryGenerator
from src.optics.atmosphere_and_noise import OpticalEngine
from src.camera.ptz_camera import VirtualPTZCamera
from src.vision.tracker import BeaconTracker
from src.control.gimbal_controller import GimbalController
from main import PhoenixXSimulator

def record_demonstration_video(output_path: str = "artifacts/phoenix_tracking_demo.mp4", duration_sec: float = 15.0, fps: int = 30):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    sim = PhoenixXSimulator(headless=True)
    total_frames = int(duration_sec * fps)
    dt = 1.0 / fps
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (1100, 640))
    
    if not out.isOpened():
        print(f"[-] Error: Could not open VideoWriter for {output_path}")
        return False

    print("=" * 70)
    print(f"  RECORDING PHOENIX-X DEMONSTRATION VIDEO: {output_path}")
    print(f"  Duration: {duration_sec}s | Total Frames: {total_frames} | Frame Rate: {fps} FPS")
    print("=" * 70)

    trail_points = []
    max_trail = 80

    for frame_idx in range(total_frames):
        sim_time = frame_idx * dt
        
        # Scenario Automation Schedule:
        # 0.0 - 3.0s: Clean Figure-8 Baseline
        # 3.0 - 6.0s: Inject 10% Salt & Pepper Noise
        # 6.0 - 9.0s: Inject Atmospheric Fog & Shot Noise
        # 9.0 - 12.0s: Inject Multi-harmonic Platform Jitter (+-20 px)
        # 12.0 - 15.0s: Deep Saliency Edge-AI Mode + Agile Random Walk
        
        if 3.0 <= sim_time < 6.0:
            sim.optics.enable_salt_and_pepper = True
        elif 6.0 <= sim_time < 9.0:
            sim.optics.enable_salt_and_pepper = True
            sim.optics.enable_fog = True
            sim.optics.enable_poisson = True
        elif 9.0 <= sim_time < 12.0:
            sim.optics.enable_salt_and_pepper = True
            sim.optics.enable_fog = True
            sim.optics.enable_jitter = True
        elif sim_time >= 12.0:
            sim.optics.enable_salt_and_pepper = True
            sim.optics.enable_fog = True
            sim.optics.enable_jitter = True
            sim.tracker.use_deep_ai = True

        # 1. Target kinematics & Jitter
        true_pos = sim.trajectory.get_position(sim_time)
        jx, jy = sim.optics.get_platform_jitter(sim_time)
        apparent_x = true_pos.x + jx
        apparent_y = true_pos.y + jy
        
        trail_points.append((int(true_pos.x), int(true_pos.y)))
        if len(trail_points) > max_trail:
            trail_points.pop(0)

        # 2. Render Virtual Camera Frame
        sensor_frame = np.full((CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX), 12, dtype=np.uint8)
        local_target = sim.camera.global_to_local(apparent_x, apparent_y)
        sensor_frame = sim.optics.render_beacon_on_frame(sensor_frame, local_target.x, local_target.y)
        degraded_frame = sim.optics.apply_disturbances(sensor_frame)

        # 3. Tracker Processing
        detected_point, error_px, snr_db = sim.tracker.process_frame(degraded_frame)
        error_arcsec = error_px * ARCSEC_PER_PIXEL if detected_point else 999.0

        # 4. Controller Servo Step
        cmd_vx, cmd_vy = sim.controller.update(detected_point, dt)
        sim.camera.update_actuator(cmd_vx, cmd_vy, dt)
        current_slew_deg_s = math.hypot(sim.camera.vx_deg_s, sim.camera.vy_deg_s)

        # 5. Render Tactical Cockpit Frame
        cockpit_frame = sim._render_cockpit(
            degraded_frame, local_target, detected_point,
            error_px, error_arcsec, current_slew_deg_s,
            fps=float(fps), snr_db=snr_db, trail=trail_points, sim_time=sim_time
        )
        
        # Add Demo Watermark & Active Scenario Stage Banner
        banner_text = ""
        if sim_time < 3.0:
            banner_text = "STAGE 1: CLEAN ACQUISITION & CENTERING (NOMINAL)"
            banner_color = (0, 230, 115)
        elif sim_time < 6.0:
            banner_text = "STAGE 2: 10% IMPULSIVE SALT & PEPPER NOISE INJECTION"
            banner_color = (0, 215, 255)
        elif sim_time < 9.0:
            banner_text = "STAGE 3: ATMOSPHERIC FOG SCATTERING & POISSON SHOT NOISE"
            banner_color = (0, 165, 255)
        elif sim_time < 12.0:
            banner_text = "STAGE 4: MULTI-HARMONIC PLATFORM JITTER (+-20 PX/FRAME)"
            banner_color = (0, 100, 255)
        else:
            banner_text = "STAGE 5: DEEP SALIENCY EDGE-AI + HIGH DYNAMICS RANDOM WALK"
            banner_color = (255, 105, 180)

        # Banner overlay at top-center of video
        cv2.rectangle(cockpit_frame, (350, 8), (1080, 36), (15, 18, 24), -1)
        cv2.rectangle(cockpit_frame, (350, 8), (1080, 36), banner_color, 1)
        cv2.putText(cockpit_frame, banner_text, (360, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, banner_color, 1, cv2.LINE_AA)

        out.write(cockpit_frame)

        if (frame_idx + 1) % 45 == 0 or frame_idx == total_frames - 1:
            progress = ((frame_idx + 1) / total_frames) * 100.0
            print(f"[*] Rendered Frame {frame_idx + 1}/{total_frames} ({progress:.1f}%) | Time: {sim_time:.2f}s | Error: {error_px:.3f} px")

    out.release()
    print(f"\n[+] Demonstration video successfully generated: {output_path}")
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[+] Output File Size: {file_size_mb:.2f} MB")
    return True

if __name__ == '__main__':
    record_demonstration_video()
