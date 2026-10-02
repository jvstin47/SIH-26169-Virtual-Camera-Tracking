#!/usr/bin/env python3
"""
Phoenix-X Synthetic Dataset & Ephemeris Generator
Problem Statement ID: SIH 26169 (ISRO / SAC)

Generates benchmark synthetic datasets conforming to:
- Guideline 1: Simulation & Dataset Generation (LEO Satellite & UAV tracking)
- Exports relative 3D kinematics (Azimuth, Elevation, Range, Angular Rates)
- Renders simulated 640x480 FPA camera views with optical disturbances
- Produces paired ground truth CSV and bounding box manifests for AI training
"""

import os
import sys
import json
import csv
import math
import numpy as np
import cv2

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulation.orbital_propagator import OrbitalKinematicsPropagator
from src.optics.atmosphere_and_noise import OpticalEngine
from src.core.coordinates import CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX

OUTPUT_DIR = "data/synthetic_dataset"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

def generate_dataset(num_frames: int = 150, scenario: str = "leo_to_ground"):
    os.makedirs(IMAGES_DIR, exist_ok=True)
    csv_path = os.path.join(OUTPUT_DIR, "ground_truth.csv")
    meta_path = os.path.join(OUTPUT_DIR, "metadata.json")

    print(f"[*] Generating {num_frames} synthetic FSOC frames for scenario: '{scenario}'...")
    
    propagator = OrbitalKinematicsPropagator(scenario=scenario)
    optics = OpticalEngine(spot_size_px=8, spot_peak_intensity=245)

    # Initial gimbal pointing matching initial target state
    obs_0 = propagator.step(0.0, 0.0, 0.0)
    gimbal_az = obs_0.azimuth_deg
    gimbal_el = obs_0.elevation_deg

    records = []
    dt = 0.05 # 20 Hz generation

    for i in range(num_frames):
        t = i * dt

        # Step orbital kinematics
        obs = propagator.step(t, gimbal_az, gimbal_el, dt=dt)

        # Realistic gimbal coarse tracking response (follows with small servo delay + clamp)
        slew_limit = 5.0 * dt # 5 deg/s max physical motor slew
        d_az = float(np.clip(obs.azimuth_deg - gimbal_az, -slew_limit, slew_limit))
        d_el = float(np.clip(obs.elevation_deg - gimbal_el, -slew_limit, slew_limit))
        gimbal_az += d_az
        gimbal_el += d_el

        # Recalculate true projected pixel on FPA with updated gimbal position
        true_x, true_y, in_fov = propagator.project_to_fpa(
            obs.azimuth_deg, obs.elevation_deg, gimbal_az, gimbal_el
        )

        # Render 640x480 Focal Plane Array (FPA) Image
        # Ambient space background ~15 ADU
        base_frame = np.full((CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX), 14, dtype=np.uint8)

        # Multi-harmonic platform structural jitter
        jx, jy = optics.get_platform_jitter(t)
        app_x = true_x + jx
        app_y = true_y + jy

        # Inject optical beacon spot if in field-of-view
        if in_fov:
            # Beer-Lambert atmospheric transmission attenuation factor
            # Transmittance decreases with slant range
            extinction_gamma = 0.0018
            transmittance = math.exp(-extinction_gamma * obs.slant_range_km)
            spot_val = int(245 * max(0.25, transmittance))
            optics.spot_peak_intensity = spot_val
            base_frame = optics.render_beacon_on_frame(base_frame, app_x, app_y)

        # Apply multi-disturbance optical degradation
        # 1. Fog / Haze
        optics.enable_fog = (i > 30 and i < 90)
        # 2. 10% Salt & Pepper impulsive detector noise
        optics.enable_salt_and_pepper = (i > 15)
        # 3. Poisson detector shot noise
        optics.enable_poisson = True

        degraded = optics.apply_disturbances(base_frame)

        # Save Image Frame
        img_filename = f"frame_{i:04d}.png"
        img_full_path = os.path.join(IMAGES_DIR, img_filename)
        cv2.imwrite(img_full_path, degraded)

        # Compute Bounding Box [xmin, ymin, w, h] around target
        box_radius = 16
        xmin = max(0, int(true_x - box_radius))
        ymin = max(0, int(true_y - box_radius))
        xmax = min(CAMERA_WIDTH_PX, int(true_x + box_radius))
        ymax = min(CAMERA_HEIGHT_PX, int(true_y + box_radius))
        bw = max(0, xmax - xmin)
        bh = max(0, ymax - ymin)

        records.append({
            "frame_id": i,
            "filename": os.path.join("images", img_filename),
            "timestamp_s": round(t, 4),
            "scenario": scenario,
            "slant_range_km": round(obs.slant_range_km, 3),
            "azimuth_deg": round(obs.azimuth_deg, 4),
            "elevation_deg": round(obs.elevation_deg, 4),
            "gimbal_az_deg": round(gimbal_az, 4),
            "gimbal_el_deg": round(gimbal_el, 4),
            "true_pixel_x": round(true_x, 2),
            "true_pixel_y": round(true_y, 2),
            "in_fov": int(in_fov),
            "bbox_xmin": xmin,
            "bbox_ymin": ymin,
            "bbox_w": bw,
            "bbox_h": bh,
            "fog_active": int(optics.enable_fog),
            "sp_noise_active": int(optics.enable_salt_and_pepper)
        })

    # Write CSV
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    # Write Metadata Manifest
    metadata = {
        "dataset_name": f"Phoenix-X-FSOC-Synthetic-Dataset-{scenario.upper()}",
        "generator_version": "2.0.0",
        "problem_statement": "SIH 26169 (ISRO / SAC)",
        "sensor_specifications": {
            "resolution": f"{CAMERA_WIDTH_PX}x{CAMERA_HEIGHT_PX}",
            "fpa_format": "Monochrome CMOS / InGaAs PIN",
            "fov_azimuth_deg": 4.0,
            "fov_elevation_deg": 3.0,
            "angular_scale_arcsec_per_px": 22.5,
            "frame_rate_hz": 20.0
        },
        "optical_channel_disturbances": {
            "salt_and_pepper_noise_ratio": 0.10,
            "beer_lambert_extinction": "Active",
            "poisson_shot_noise": "Active",
            "multi_harmonic_platform_jitter": "±20 px/frame"
        },
        "total_frames_generated": len(records),
        "csv_manifest_path": csv_path
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"[+] Dataset successfully created at: {OUTPUT_DIR}")
    print(f"    - Frames: {len(records)} images in {IMAGES_DIR}/")
    print(f"    - Ground Truth CSV: {csv_path}")
    print(f"    - Metadata Manifest: {meta_path}")

if __name__ == "__main__":
    generate_dataset(num_frames=60, scenario="leo_to_ground")
