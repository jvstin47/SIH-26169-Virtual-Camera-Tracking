#!/usr/bin/env python3
"""
Node A: Remote Maneuvering Satellite / UAV Beacon Transmitter (Terminal 1)
Generates target kinematics with soft boundary repelling fields (never flies off-grid).
Receives closed-loop PTZ camera position from Node B (UDP 9998) to render exact sensor crop.
"""

import sys
import os
import time
import math
import socket
import json
import threading
import numpy as np
import cv2

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.coordinates import UNIVERSE_WIDTH_PX, UNIVERSE_HEIGHT_PX, CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX
from src.optics.atmosphere_and_noise import OpticalEngine
from src.core.network import UDPSender

# Shared state for camera center commanded by Node B
CAM_STATE = {
    "cam_x": UNIVERSE_WIDTH_PX / 2.0,
    "cam_y": UNIVERSE_HEIGHT_PX / 2.0
}

def ptz_listener():
    """Listens for PTZ camera updates sent from Node B on port 9998."""
    sock_rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_rx.bind(("127.0.0.1", 9998))
    sock_rx.settimeout(1.0)
    while True:
        try:
            data, _ = sock_rx.recvfrom(1024)
            if data == b"STOP":
                break
            msg = json.loads(data.decode('utf-8'))
            CAM_STATE["cam_x"] = float(msg.get("cam_x", CAM_STATE["cam_x"]))
            CAM_STATE["cam_y"] = float(msg.get("cam_y", CAM_STATE["cam_y"]))
        except Exception:
            continue
    sock_rx.close()

def main():
    print("=" * 70)
    print("  NODE A: REMOTE SATELLITE / UAV BEACON TRANSMITTER (TERMINAL 1)")
    print("=" * 70)
    print("[*] Broadcasting optical feed to Node B (127.0.0.1:9999)...")
    print("[*] Listening for closed-loop PTZ gimbal feedback on port 9998...")
    print("    Controls:")
    print("      [1] Toggle 10% Salt & Pepper Noise")
    print("      [3] Toggle Heavy Fog / Atmospheric Attenuation")
    print("      [4] Toggle Platform Multi-Harmonic Jitter")
    print("      [Space] Inject Evasive Maneuver Jump")
    print("      [Q] Quit Node A\n")

    import argparse
    parser = argparse.ArgumentParser(description="Node A: Remote Maneuvering Satellite Transmitter")
    parser.add_argument("--port", type=int, default=9999,
                        help="UDP port to stream optical frames to (default: 9999 for Node C Atmospheric Channel, or directly to Node B)")
    args = parser.parse_args()

    # Start PTZ receiver thread
    t_listener = threading.Thread(target=ptz_listener, daemon=True)
    t_listener.start()

    sock_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target_addr = ("127.0.0.1", args.port)
    udp_sender = UDPSender(sock_tx, target_addr)
    print(f"[*] Streaming video frames to UDP 127.0.0.1:{args.port}...")

    optics = OpticalEngine(spot_size_px=10, spot_peak_intensity=250)
    
    # Target state in global universe
    pos_x = UNIVERSE_WIDTH_PX / 2.0
    pos_y = UNIVERSE_HEIGHT_PX / 2.0
    vx = 35.0 # px/s
    vy = 25.0 # px/s

    frame_id = 0
    t_start = time.time()
    dt = 0.033

    while True:
        frame_id += 1
        t_now = time.time() - t_start

        # -------------------------------------------------------------
        # Smooth Singer Kinematics + Soft Boundary Repelling Potential
        # Ensures target stays safely within operational boundaries
        # -------------------------------------------------------------
        vx += np.random.normal(0, 18.0) * dt
        vy += np.random.normal(0, 18.0) * dt

        # Soft boundary repelling force (pushes target gently back to center)
        cx = UNIVERSE_WIDTH_PX / 2.0
        cy = UNIVERSE_HEIGHT_PX / 2.0
        dist_from_cx = pos_x - cx
        dist_from_cy = pos_y - cy

        if abs(dist_from_cx) > 550.0:
            vx -= np.sign(dist_from_cx) * 50.0 * dt
        if abs(dist_from_cy) > 550.0:
            vy -= np.sign(dist_from_cy) * 50.0 * dt

        vx = float(np.clip(vx, -85.0, 85.0))
        vy = float(np.clip(vy, -85.0, 85.0))

        pos_x += vx * dt
        pos_y += vy * dt

        # Absolute hard boundary clamp
        pos_x = float(np.clip(pos_x, 300.0, UNIVERSE_WIDTH_PX - 300.0))
        pos_y = float(np.clip(pos_y, 300.0, UNIVERSE_HEIGHT_PX - 300.0))

        # Platform multi-harmonic jitter
        jx, jy = optics.get_platform_jitter(t_now)
        app_x = pos_x + jx
        app_y = pos_y + jy

        # Local viewport position relative to current camera center from Node B
        cam_x = CAM_STATE["cam_x"]
        cam_y = CAM_STATE["cam_y"]
        local_x = app_x - (cam_x - CAMERA_WIDTH_PX / 2.0)
        local_y = app_y - (cam_y - CAMERA_HEIGHT_PX / 2.0)

        frame = np.full((CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX), 15, dtype=np.uint8)
        frame = optics.render_beacon_on_frame(frame, local_x, local_y)
        degraded = optics.apply_disturbances(frame)

        # Compress to JPEG
        _, encoded = cv2.imencode('.jpg', degraded, [cv2.IMWRITE_JPEG_QUALITY, 75])
        jpg_bytes = encoded.tobytes()

        # Packet metadata
        metadata = {
            "frame_id": frame_id,
            "timestamp": t_now,
            "true_global_x": float(pos_x),
            "true_global_y": float(pos_y),
            "cam_x": float(cam_x),
            "cam_y": float(cam_y),
            "apparent_local_x": float(local_x),
            "apparent_local_y": float(local_y),
            "payload_len": len(jpg_bytes)
        }
        meta_json = json.dumps(metadata).encode('utf-8')
        packet = len(meta_json).to_bytes(4, 'big') + meta_json + jpg_bytes

        udp_sender.send_frame(frame_id, packet)

        # Terminal 1 Display
        cv2.putText(degraded, f"NODE A: SATELLITE BEACON TRANSMITTER (FRAME {frame_id})", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 225, 235), 1)
        cv2.putText(degraded, f"TARGET GLOBAL: ({pos_x:.1f}, {pos_y:.1f}) | GIMBAL CAM: ({cam_x:.1f}, {cam_y:.1f})", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 255), 1)

        cv2.imshow("Node A: Remote Satellite / Target Beacon (Terminal 1)", degraded)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('1'):
            optics.enable_salt_and_pepper = not optics.enable_salt_and_pepper
            print(f"[*] Node A: 10% S&P Noise -> {optics.enable_salt_and_pepper}")
        elif key == ord('3'):
            optics.enable_fog = not optics.enable_fog
            print(f"[*] Node A: Fog Attenuation -> {optics.enable_fog}")
        elif key == ord('4'):
            optics.enable_jitter = not optics.enable_jitter
            print(f"[*] Node A: Platform Jitter -> {optics.enable_jitter}")
        elif key == 32:  # Spacebar
            vx = np.random.choice([-1, 1]) * 75.0
            vy = np.random.choice([-1, 1]) * 75.0
            print(f"[!] Node A: High-G Evasive Jump -> Vel: ({vx:.1f}, {vy:.1f})")

        time.sleep(max(0.001, dt - (time.time() - (t_start + t_now))))

    sock_tx.sendto(b"STOP", target_addr)
    sock_tx.close()
    cv2.destroyAllWindows()
    print("[+] Node A stopped.")

if __name__ == "__main__":
    main()
