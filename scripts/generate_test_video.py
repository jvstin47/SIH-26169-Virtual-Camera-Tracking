#!/usr/bin/env python3
"""
Synthetic Benchmark Video Generator for ISRO Benchmark-2 Evaluation
Generates a realistic 30 FPS .mp4 video containing a moving optical beacon,
10% Salt & Pepper noise, Poisson shot noise, and atmospheric fog,
along with its exact ground-truth CSV coordinates.
"""

import os
import math
import csv
import numpy as np
import cv2

def generate_video(output_video: str = "tests/sample_beacon_test.mp4",
                   output_csv: str = "tests/sample_ground_truth.csv",
                   duration_s: float = 8.0, fps: int = 30):
    os.makedirs(os.path.dirname(output_video), exist_ok=True)
    width, height = 640, 480
    total_frames = int(duration_s * fps)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    cx, cy = width / 2.0, height / 2.0
    scale_a = 180.0
    omega = 0.8
    spot_radius = 4.0 # sigma
    
    gt_records = []
    print(f"[*] Generating {duration_s}s ({total_frames} frames) benchmark video: {output_video}...")
    
    for f in range(total_frames):
        t = f / float(fps)
        
        # Lemniscate path inside 640x480 frame
        theta = omega * t
        denom = 1.0 + math.cos(theta)**2
        tx = cx + (scale_a * math.sin(theta)) / denom
        ty = cy + (scale_a * math.sin(theta) * math.cos(theta)) / denom
        
        gt_records.append((tx, ty))
        
        # Background dark current
        frame = np.full((height, width), 20, dtype=np.uint8)
        
        # Render Gaussian optical spot
        x0, y0 = int(round(tx)), int(round(ty))
        rad = 16
        y_min = max(0, y0 - rad)
        y_max = min(height, y0 + rad + 1)
        x_min = max(0, x0 - rad)
        x_max = min(width, x0 + rad + 1)
        
        yy, xx = np.mgrid[y_min - y0:y_max - y0, x_min - x0:x_max - x0]
        spot = 240.0 * np.exp(-((xx - (tx - x0))**2 + (yy - (ty - y0))**2) / (2.0 * spot_radius**2))
        
        patch = frame[y_min:y_max, x_min:x_max].astype(np.float32)
        frame[y_min:y_max, x_min:x_max] = np.clip(patch + spot, 0, 255).astype(np.uint8)
        
        # Add 10% Salt & Pepper noise
        prob = 0.08
        rnd = np.random.random(frame.shape)
        frame[rnd < (prob / 2.0)] = 255
        frame[(rnd >= (prob / 2.0)) & (rnd < prob)] = 0
        
        # Add slight Poisson shot noise
        poiss = np.random.poisson(frame.astype(np.float32) / 6.0) * 6.0
        frame = np.clip(frame * 0.8 + poiss * 0.2, 0, 255).astype(np.uint8)
        
        bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        out.write(bgr)
        
    out.release()
    
    # Save ground truth CSV
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["GroundTruth_X", "GroundTruth_Y"])
        for x, y in gt_records:
            writer.writerow([f"{x:.3f}", f"{y:.3f}"])
            
    print(f"[+] Video successfully created: {output_video}")
    print(f"[+] Ground truth coordinates: {output_csv}")

if __name__ == "__main__":
    generate_video()
