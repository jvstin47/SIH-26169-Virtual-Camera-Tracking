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
REMOTE_COMMANDS = []

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
            if "cam_x" in msg:
                CAM_STATE["cam_x"] = float(msg.get("cam_x", CAM_STATE["cam_x"]))
            if "cam_y" in msg:
                CAM_STATE["cam_y"] = float(msg.get("cam_y", CAM_STATE["cam_y"]))
            if "cmd" in msg:
                REMOTE_COMMANDS.append(msg["cmd"])
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
    parser.add_argument("--headless", action="store_true", help="Run without native GUI windows")
    parser.add_argument("--stream-port", type=int, default=0, help="UDP port to mirror HUD JPEG for Web Streaming")
    args = parser.parse_args()

    # Start PTZ receiver thread
    t_listener = threading.Thread(target=ptz_listener, daemon=True)
    t_listener.start()

    sock_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target_addr = ("127.0.0.1", args.port)
    udp_sender = UDPSender(sock_tx, target_addr)
    print(f"[*] Streaming video frames to UDP 127.0.0.1:{args.port}...")

    sock_stream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if args.stream_port > 0 else None
    stream_addr = ("127.0.0.1", args.stream_port) if args.stream_port > 0 else None
    stream_sender = UDPSender(sock_stream, stream_addr) if args.stream_port > 0 else None

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

        # -------------------------------------------------------------
        # Terminal 1 Display: Global Universe Radar Cockpit (2000x2000)
        # -------------------------------------------------------------
        radar_size = 600
        scale = radar_size / float(UNIVERSE_WIDTH_PX) # 0.3x scaling
        
        # Canvas: 600x600 universe radar on left + 280x600 telemetry panel on right
        display_w = radar_size + 280
        display_h = radar_size
        hud = np.zeros((display_h, display_w, 3), dtype=np.uint8)
        hud[:] = (11, 15, 23) # Dark space background

        # 1. Draw Tactical Universe Radar Grid
        radar_view = hud[:, :radar_size]
        radar_view[:] = (8, 12, 18)

        # Minor Grid Lines (every 100 px in universe = 30 px on radar)
        for g in range(0, radar_size, int(100 * scale)):
            cv2.line(radar_view, (g, 0), (g, radar_size), (20, 28, 40), 1)
            cv2.line(radar_view, (0, g), (radar_size, g), (20, 28, 40), 1)

        # Major Grid Lines (every 500 px in universe = 150 px on radar)
        for g in range(0, radar_size + 1, int(500 * scale)):
            cv2.line(radar_view, (g, 0), (g, radar_size), (40, 58, 80), 1)
            cv2.line(radar_view, (0, g), (radar_size, g), (40, 58, 80), 1)

        # Range Rings from Center (radius: 250, 500, 750 px in universe)
        radar_center = (int(radar_size / 2), int(radar_size / 2))
        for r_ring in [250, 500, 750]:
            cv2.circle(radar_view, radar_center, int(r_ring * scale), (30, 45, 65), 1)

        # Center Crosshair
        cx, cy = radar_center
        cv2.line(radar_view, (cx - 10, cy), (cx + 10, cy), (0, 180, 255), 1)
        cv2.line(radar_view, (cx, cy - 10), (cx, cy + 10), (0, 180, 255), 1)

        # Coordinate Axis Tick Labels
        coord_ticks = [(0, "0"), (500, "500"), (1000, "1000"), (1500, "1500"), (2000, "2000")]
        for px_val, lbl in coord_ticks:
            pos = int(px_val * scale)
            if pos < radar_size - 10:
                cv2.putText(radar_view, lbl, (max(5, pos - 12), radar_size - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.32, (100, 125, 155), 1)
                if pos > 10:
                    cv2.putText(radar_view, lbl, (6, max(15, pos + 4)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (100, 125, 155), 1)

        # 2. Draw Target Trajectory Trail
        if not hasattr(main, "trail"):
            main.trail = []
        main.trail.append((float(pos_x), float(pos_y)))
        if len(main.trail) > 80:
            main.trail.pop(0)

        for i in range(1, len(main.trail)):
            p1 = (int(main.trail[i-1][0] * scale), int(main.trail[i-1][1] * scale))
            p2 = (int(main.trail[i][0] * scale), int(main.trail[i][1] * scale))
            alpha = i / len(main.trail)
            trail_col = (int(140 * alpha), int(80 * alpha), int(220 * alpha))
            cv2.line(radar_view, p1, p2, trail_col, 1)

        # 3. Draw Ground Station Camera Viewport Bounding Box (Node B FOV)
        cam_top_left = (int((cam_x - CAMERA_WIDTH_PX / 2.0) * scale),
                        int((cam_y - CAMERA_HEIGHT_PX / 2.0) * scale))
        cam_bot_right = (int((cam_x + CAMERA_WIDTH_PX / 2.0) * scale),
                         int((cam_y + CAMERA_HEIGHT_PX / 2.0) * scale))
        cv2.rectangle(radar_view, cam_top_left, cam_bot_right, (0, 165, 255), 2)
        # Center cross on camera box
        cam_center_m = (int(cam_x * scale), int(cam_y * scale))
        cv2.circle(radar_view, cam_center_m, 2, (0, 165, 255), -1)
        cv2.putText(radar_view, "NODE B FOV (640x480)", (cam_top_left[0] + 4, max(14, cam_top_left[1] - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 165, 255), 1)

        # 4. Draw Satellite Beacon Marker & Velocity Vector
        sat_pos_m = (int(pos_x * scale), int(pos_y * scale))
        cv2.circle(radar_view, sat_pos_m, 6, (0, 255, 255), -1) # Yellow core
        cv2.circle(radar_view, sat_pos_m, 12, (0, 220, 255), 1) # Halo
        vel_tip = (int((pos_x + vx * 0.8) * scale), int((pos_y + vy * 0.8) * scale))
        cv2.arrowedLine(radar_view, sat_pos_m, vel_tip, (0, 255, 120), 1, tipLength=0.3)
        cv2.putText(radar_view, "SATELLITE", (sat_pos_m[0] + 14, sat_pos_m[1] + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)

        # Radar Outer Border
        cv2.rectangle(radar_view, (0, 0), (radar_size - 1, radar_size - 1), (60, 85, 115), 2)

        # 5. Right Column: Telemetry & Beacon Preview
        panel_x = radar_size + 15
        cv2.putText(hud, "NODE A: SATELLITE TRANSMITTER", (panel_x, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (220, 225, 235), 1)
        cv2.putText(hud, "GLOBAL UNIVERSE (2000x2000)", (panel_x, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 200, 255), 1)

        # Optical Crop Thumbnail Preview (Transmitted Beacon)
        thumb_h, thumb_w = 120, 160
        thumb = cv2.resize(degraded, (thumb_w, thumb_h))
        thumb_bgr = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR) if len(thumb.shape) == 2 else thumb
        cv2.rectangle(thumb_bgr, (0, 0), (thumb_w - 1, thumb_h - 1), (0, 180, 255), 1)
        hud[70:70+thumb_h, panel_x:panel_x+thumb_w] = thumb_bgr
        cv2.putText(hud, "OPTICAL BEACON FEED", (panel_x, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (150, 165, 185), 1)

        # Kinematic & Link Telemetry
        ty = 220
        cv2.putText(hud, f"FRAME ID   : {frame_id}", (panel_x, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (200, 205, 215), 1)
        cv2.putText(hud, f"GLOBAL X   : {pos_x:6.1f} px", (panel_x, ty + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 255), 1)
        cv2.putText(hud, f"GLOBAL Y   : {pos_y:6.1f} px", (panel_x, ty + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 255), 1)
        cv2.putText(hud, f"VELOCITY   : ({vx:+4.1f}, {vy:+4.1f})", (panel_x, ty + 66), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (200, 205, 215), 1)
        cv2.putText(hud, f"CAM POS    : ({cam_x:6.1f}, {cam_y:6.1f})", (panel_x, ty + 88), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 165, 255), 1)

        in_fov = (0 <= local_x < CAMERA_WIDTH_PX and 0 <= local_y < CAMERA_HEIGHT_PX)
        fov_col = (0, 230, 115) if in_fov else (0, 140, 255)
        fov_txt = "INSIDE CAM FOV (TRACKING)" if in_fov else "OUT OF FOV (SWEEPING)"
        cv2.putText(hud, f"LINK STATUS: {fov_txt}", (panel_x, ty + 115), cv2.FONT_HERSHEY_SIMPLEX, 0.34, fov_col, 1)

        # Environmental Toggles Status
        dy = 375
        def tcol(flag): return (0, 230, 115) if flag else (90, 95, 105)
        cv2.putText(hud, f"[1] 10% S&P NOISE  : {'ACTIVE' if optics.enable_salt_and_pepper else 'OFF'}", (panel_x, dy), cv2.FONT_HERSHEY_SIMPLEX, 0.34, tcol(optics.enable_salt_and_pepper), 1)
        cv2.putText(hud, f"[3] FOG ATTENUATION: {'ACTIVE' if optics.enable_fog else 'OFF'}", (panel_x, dy + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.34, tcol(optics.enable_fog), 1)
        cv2.putText(hud, f"[4] PLATFORM JITTER: {'ACTIVE' if optics.enable_jitter else 'OFF'}", (panel_x, dy + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.34, tcol(optics.enable_jitter), 1)

        # Interactive Controls Guide
        cv2.putText(hud, "KEYBOARD CONTROLS:", (panel_x, 480), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 190, 255), 1)
        cv2.putText(hud, "  [1/3/4] Toggle Disturbances", (panel_x, 502), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (150, 160, 175), 1)
        cv2.putText(hud, "  [Space] Evasive Maneuver Jump", (panel_x, 522), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (150, 160, 175), 1)
        cv2.putText(hud, "  [Q/ESC] Quit Node A", (panel_x, 542), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (150, 160, 175), 1)

        # Process remote web commands
        while REMOTE_COMMANDS:
            rcmd = REMOTE_COMMANDS.pop(0)
            if rcmd == "evasive":
                vx = np.random.choice([-1, 1]) * 80.0
                vy = np.random.choice([-1, 1]) * 80.0
                print(f"[!] Node A: Remote Evasive Jump -> Vel: ({vx:.1f}, {vy:.1f})")
            elif rcmd == "toggle_noise":
                optics.enable_salt_and_pepper = not optics.enable_salt_and_pepper
                print(f"[*] Node A: Remote 10% S&P Noise -> {optics.enable_salt_and_pepper}")
            elif rcmd == "toggle_fog":
                optics.enable_fog = not optics.enable_fog
                print(f"[*] Node A: Remote Fog Attenuation -> {optics.enable_fog}")
            elif rcmd == "toggle_jitter":
                optics.enable_jitter = not optics.enable_jitter
                print(f"[*] Node A: Remote Platform Jitter -> {optics.enable_jitter}")

        # Stream HUD JPEG to web server if requested
        if stream_sender is not None:
            try:
                _, jpg_stream = cv2.imencode('.jpg', hud, [cv2.IMWRITE_JPEG_QUALITY, 60])
                stream_sender.send_frame(frame_id, jpg_stream.tobytes())
            except Exception:
                pass

        if not args.headless:
            cv2.imshow("Node A: Global Universe (2000x2000) & Satellite Transmitter (Terminal 1)", hud)
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
    if sock_stream is not None:
        sock_stream.close()
    if not args.headless:
        cv2.destroyAllWindows()
    print("[+] Node A stopped.")

if __name__ == "__main__":
    main()
