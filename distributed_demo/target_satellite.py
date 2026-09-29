#!/usr/bin/env python3
"""
Node A: Remote Maneuvering Satellite / UAV Beacon Transmitter
Terminal 1: Moves target beacon randomly (or via arrow keys) across a 2000x2000 universe.
Injects disturbances (10% S&P noise, fog, jitter) and streams frames to Node B over UDP.
"""

import sys
import os
import time
import math
import socket
import json
import numpy as np
import cv2

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.coordinates import UNIVERSE_WIDTH_PX, UNIVERSE_HEIGHT_PX, CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX
from src.optics.atmosphere_and_noise import OpticalEngine

def main():
    print("=" * 70)
    print("  NODE A: REMOTE SATELLITE / UAV BEACON TRANSMITTER (TERMINAL 1)")
    print("=" * 70)
    print("[*] Broadcasting target beacon feed to Ground Tracker (127.0.0.1:9999)...")
    print("    Controls:")
    print("      [1] Toggle 10% Salt & Pepper Noise")
    print("      [3] Toggle Heavy Fog / Atmospheric Attenuation")
    print("      [4] Toggle Platform Multi-Harmonic Jitter")
    print("      [Space] Inject Evasive Maneuver Jump")
    print("      [Q] Quit Node A\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target_addr = ("127.0.0.1", 9999)

    optics = OpticalEngine(spot_size_px=10, spot_peak_intensity=250)
    
    # State: Target position in universe
    pos_x = UNIVERSE_WIDTH_PX / 2.0
    pos_y = UNIVERSE_HEIGHT_PX / 2.0
    vx = 45.0 # px/s
    vy = 30.0 # px/s
    
    # Simulated camera viewport center (can be updated from Node B feedback or tracking)
    cam_x = UNIVERSE_WIDTH_PX / 2.0
    cam_y = UNIVERSE_HEIGHT_PX / 2.0

    frame_id = 0
    t_start = time.time()
    dt = 0.033 # ~30 FPS

    while True:
        frame_id += 1
        t_now = time.time() - t_start

        # Continuous smooth random maneuvering (Singer acceleration model)
        vx += np.random.normal(0, 20.0) * dt
        vy += np.random.normal(0, 20.0) * dt
        vx = float(np.clip(vx, -80.0, 80.0))
        vy = float(np.clip(vy, -80.0, 80.0))

        pos_x += vx * dt
        pos_y += vy * dt

        # Boundary bounce
        pad = 250.0
        if pos_x < pad or pos_x > UNIVERSE_WIDTH_PX - pad:
            vx *= -1.0
            pos_x = np.clip(pos_x, pad, UNIVERSE_WIDTH_PX - pad)
        if pos_y < pad or pos_y > UNIVERSE_HEIGHT_PX - pad:
            vy *= -1.0
            pos_y = np.clip(pos_y, pad, UNIVERSE_HEIGHT_PX - pad)

        # Apply multi-harmonic platform jitter
        jx, jy = optics.get_platform_jitter(t_now)
        app_x = pos_x + jx
        app_y = pos_y + jy

        # Render 640x480 frame relative to current camera center
        local_x = app_x - (cam_x - CAMERA_WIDTH_PX / 2.0)
        local_y = app_y - (cam_y - CAMERA_HEIGHT_PX / 2.0)

        frame = np.full((CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX), 15, dtype=np.uint8)
        frame = optics.render_beacon_on_frame(frame, local_x, local_y)
        degraded = optics.apply_disturbances(frame)

        # Compress to JPEG for UDP transmission
        _, encoded = cv2.imencode('.jpg', degraded, [cv2.IMWRITE_JPEG_QUALITY, 75])
        jpg_bytes = encoded.tobytes()

        # Send header + payload packet
        metadata = {
            "frame_id": frame_id,
            "timestamp": t_now,
            "true_global_x": float(pos_x),
            "true_global_y": float(pos_y),
            "apparent_local_x": float(local_x),
            "apparent_local_y": float(local_y),
            "payload_len": len(jpg_bytes)
        }
        meta_json = json.dumps(metadata).encode('utf-8')
        # Format: 4 bytes meta length + meta json + jpeg bytes
        packet = len(meta_json).to_bytes(4, 'big') + meta_json + jpg_bytes

        try:
            # Send packet (if small enough for UDP datagram, split if needed)
            if len(packet) < 65000:
                sock.sendto(packet, target_addr)
        except Exception as e:
            pass

        # Interactive display for Terminal 1
        cv2.putText(degraded, f"NODE A: TRANSMITTING TARGET (FRAME {frame_id})", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, 255, 1)
        cv2.putText(degraded, f"TRUE POS: ({pos_x:.1f}, {pos_y:.1f}) | VEL: ({vx:.1f}, {vy:.1f}) px/s", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, 200, 1)

        cv2.imshow("Node A: Remote Satellite / Target Beacon (Terminal 1)", degraded)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('1'):
            optics.enable_salt_and_pepper = not optics.enable_salt_and_pepper
            print(f"[*] Node A: 10% S&P Noise -> {optics.enable_salt_and_pepper}")
        elif key == ord('3'):
            optics.enable_fog = not optics.enable_fog
            print(f"[*] Node A: Atmospheric Fog -> {optics.enable_fog}")
        elif key == ord('4'):
            optics.enable_jitter = not optics.enable_jitter
            print(f"[*] Node A: Platform Jitter -> {optics.enable_jitter}")
        elif key == 32:  # Spacebar evasive jump
            vx = np.random.choice([-1, 1]) * 75.0
            vy = np.random.choice([-1, 1]) * 75.0
            print(f"[!] Node A: Injected High-G Evasive Maneuver -> Vel: ({vx:.1f}, {vy:.1f})")

        time.sleep(max(0.001, dt - (time.time() - (t_start + t_now))))

    cap_msg = b"STOP"
    sock.sendto(cap_msg, target_addr)
    sock.close()
    cv2.destroyAllWindows()
    print("[+] Node A stopped.")

if __name__ == "__main__":
    main()
