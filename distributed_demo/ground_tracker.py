#!/usr/bin/env python3
"""
Node B: Autonomous Ground Optical Tracking Station (Terminal 2)
Closed-loop PTZ tracking station with both Autonomous & Manual Operator PTZ controls.
Sends real-time gimbal pointing coordinates back to Node A (UDP 9998).
Serves interactive mission control dashboard at http://localhost:8080/live.html.
"""

import sys
import os
import time
import math
import socket
import json
import threading
import http.server
import urllib.parse
import numpy as np
import cv2

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.coordinates import (
    CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX, UNIVERSE_WIDTH_PX, UNIVERSE_HEIGHT_PX,
    ARCSEC_PER_PIXEL, DEFAULT_MAX_SLEW_RATE_DEG_S, DEG_PER_PIXEL
)
from src.vision.tracker import BeaconTracker
from src.control.gimbal_controller import GimbalController
from src.core.network import UDPReceiver, UDPSender

# Shared global state for gimbal and telemetry
GIMBAL_STATE = {
    "cam_x": UNIVERSE_WIDTH_PX / 2.0,
    "cam_y": UNIVERSE_HEIGHT_PX / 2.0,
    "auto_track": True,
    "manual_vx": 0.0,
    "manual_vy": 0.0
}

LATEST_TELEMETRY = {
    "frame_id": 0,
    "timestamp": 0.0,
    "centroid_x": 320.0,
    "centroid_y": 240.0,
    "cam_x": 1000.0,
    "cam_y": 1000.0,
    "error_px": 0.0,
    "error_arcsec": 0.0,
    "slew_rate_deg_s": 0.0,
    "fps": 30.0,
    "locked": True,
    "auto_track": True,
    "true_x": 320.0,
    "true_y": 240.0
}

class TelemetryServer(http.server.SimpleHTTPRequestHandler):
    """Serves real-time telemetry and receives PTZ commands from the web UI."""
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(LATEST_TELEMETRY).encode('utf-8'))
            
        elif parsed.path == "/ptz":
            query = urllib.parse.parse_qs(parsed.query)
            cmd = query.get("cmd", [""])[0]
            step_px = 35.0
            
            if cmd == "pan_left":
                GIMBAL_STATE["auto_track"] = False
                GIMBAL_STATE["cam_x"] -= step_px
            elif cmd == "pan_right":
                GIMBAL_STATE["auto_track"] = False
                GIMBAL_STATE["cam_x"] += step_px
            elif cmd == "tilt_up":
                GIMBAL_STATE["auto_track"] = False
                GIMBAL_STATE["cam_y"] -= step_px
            elif cmd == "tilt_down":
                GIMBAL_STATE["auto_track"] = False
                GIMBAL_STATE["cam_y"] += step_px
            elif cmd == "toggle_auto":
                GIMBAL_STATE["auto_track"] = not GIMBAL_STATE["auto_track"]
            elif cmd == "recenter":
                GIMBAL_STATE["cam_x"] = UNIVERSE_WIDTH_PX / 2.0
                GIMBAL_STATE["cam_y"] = UNIVERSE_HEIGHT_PX / 2.0
                GIMBAL_STATE["auto_track"] = True
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            
        else:
            web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_demo")
            self.directory = web_dir
            super().do_GET()

    def log_message(self, format, *args):
        pass

def start_http_server():
    server = http.server.HTTPServer(("127.0.0.1", 8080), TelemetryServer)
    server.serve_forever()

def main():
    print("=" * 70)
    print("  NODE B: GROUND OPTICAL TRACKING TERMINAL WITH PTZ CONTROL (TERMINAL 2)")
    print("=" * 70)
    import argparse
    parser = argparse.ArgumentParser(description="Node B: Autonomous Ground Optical Tracking Station")
    parser.add_argument("--port", type=int, default=9997,
                        help="UDP port to listen on (default: 9997 for 3-Terminal Mode via Node C Channel; use 9999 for Direct 2-Terminal Mode)")
    parser.add_argument("--headless", action="store_true", help="Run without native GUI windows")
    parser.add_argument("--stream-port", type=int, default=0, help="UDP port to mirror tracker HUD JPEG for Web Streaming")
    parser.add_argument("--telemetry-port", type=int, default=0, help="UDP port to broadcast telemetry JSON")
    parser.add_argument("--cmd-port", type=int, default=9995, help="UDP port to receive PTZ commands")
    parser.add_argument("--no-http", action="store_true", help="Disable internal HTTP server")
    args = parser.parse_args()

    listen_port = args.port
    print(f"[*] Ingesting optical feed on UDP 127.0.0.1:{listen_port}...")
    if listen_port == 9997:
        print("    [Mode: 3-TERMINAL MULTI-HOP via Node C Atmospheric Channel]")
    else:
        print("    [Mode: 2-TERMINAL DIRECT LINK from Node A Satellite]")
    print("[*] Transmitting closed-loop PTZ feedback to Node A on 127.0.0.1:9998...")
    if not args.no_http:
        print("[+] Live Mission Control Dashboard active at: http://localhost:8080/live.html")
    print("\nOperator PTZ Controls:")
    print("  [W / Up]    Tilt Up")
    print("  [S / Down]  Tilt Down")
    print("  [A / Left]  Pan Left")
    print("  [D / Right] Pan Right")
    print("  [M / Space] Toggle Autonomous Auto-Track vs Manual Operator Override")
    print("  [R]         Re-Center Camera to Global Origin")
    print("  [Q]         Quit Node B\n")

    # Command listener thread for remote web PTZ commands
    def ptz_cmd_listener():
        sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_cmd.bind(("127.0.0.1", args.cmd_port))
        sock_cmd.settimeout(1.0)
        step_px = 65.0
        while True:
            try:
                data, _ = sock_cmd.recvfrom(1024)
                if data == b"STOP":
                    break
                msg = json.loads(data.decode('utf-8'))
                cmd = msg.get("cmd") or msg.get("action")
                if cmd == "pan_left":
                    GIMBAL_STATE["auto_track"] = False
                    GIMBAL_STATE["cam_x"] -= step_px
                    print(f"[*] Node C Ground Tracker: PTZ PAN LEFT -> Cam: ({GIMBAL_STATE['cam_x']:.1f}, {GIMBAL_STATE['cam_y']:.1f})")
                elif cmd == "pan_right":
                    GIMBAL_STATE["auto_track"] = False
                    GIMBAL_STATE["cam_x"] += step_px
                    print(f"[*] Node C Ground Tracker: PTZ PAN RIGHT -> Cam: ({GIMBAL_STATE['cam_x']:.1f}, {GIMBAL_STATE['cam_y']:.1f})")
                elif cmd == "tilt_up":
                    GIMBAL_STATE["auto_track"] = False
                    GIMBAL_STATE["cam_y"] -= step_px
                    print(f"[*] Node C Ground Tracker: PTZ TILT UP -> Cam: ({GIMBAL_STATE['cam_x']:.1f}, {GIMBAL_STATE['cam_y']:.1f})")
                elif cmd == "tilt_down":
                    GIMBAL_STATE["auto_track"] = False
                    GIMBAL_STATE["cam_y"] += step_px
                    print(f"[*] Node C Ground Tracker: PTZ TILT DOWN -> Cam: ({GIMBAL_STATE['cam_x']:.1f}, {GIMBAL_STATE['cam_y']:.1f})")
                elif cmd in ("toggle_auto", "toggle_track"):
                    GIMBAL_STATE["auto_track"] = not GIMBAL_STATE["auto_track"]
                    print(f"[*] Node C Ground Tracker: PTZ Mode Toggled -> {'AUTO-TRACK' if GIMBAL_STATE['auto_track'] else 'MANUAL OVERRIDE'}")
                elif cmd == "recenter":
                    GIMBAL_STATE["cam_x"] = UNIVERSE_WIDTH_PX / 2.0
                    GIMBAL_STATE["cam_y"] = UNIVERSE_HEIGHT_PX / 2.0
                    GIMBAL_STATE["auto_track"] = True
                    tracker.loss_frames = 0
                    print("[*] Node C Ground Tracker: PTZ Re-Centered to (1000.0, 1000.0) [AUTO-TRACK]")
            except Exception:
                continue
        sock_cmd.close()

    t_cmd = threading.Thread(target=ptz_cmd_listener, daemon=True)
    t_cmd.start()

    # Start HTTP Telemetry Server if requested
    if not args.no_http:
        http_thread = threading.Thread(target=start_http_server, daemon=True)
        http_thread.start()

    sock_stream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if args.stream_port > 0 else None
    stream_addr = ("127.0.0.1", args.stream_port) if args.stream_port > 0 else None
    stream_sender = UDPSender(sock_stream, stream_addr) if args.stream_port > 0 else None

    sock_telem = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if args.telemetry_port > 0 else None
    telem_addr = ("127.0.0.1", args.telemetry_port) if args.telemetry_port > 0 else None

    # UDP Sockets
    sock_rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_rx.bind(("127.0.0.1", listen_port))
    sock_rx.settimeout(2.0)
    receiver = UDPReceiver(sock_rx)

    sock_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    node_a_addr = ("127.0.0.1", 9998)

    tracker = BeaconTracker()
    controller = GimbalController()

    frame_count = 0
    t_start = time.time()
    last_t = time.time()
    fps_timer = time.time()
    measured_fps = 30.0

    max_slew_deg_s = DEFAULT_MAX_SLEW_RATE_DEG_S
    max_slew_px_s = max_slew_deg_s / DEG_PER_PIXEL

    while True:
        res = receiver.receive_frame()
        if res is None:
            continue

        frame_id, data = res

        if data == b"STOP":
            print("[*] Node A signaled shutdown.")
            break

        meta_len = int.from_bytes(data[:4], 'big')
        meta_json = json.loads(data[4:4 + meta_len].decode('utf-8'))
        jpg_bytes = data[4 + meta_len:]

        nparr = np.frombuffer(jpg_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if frame is None:
            continue

        frame_count += 1
        now = time.time()
        dt = max(0.001, now - last_t)
        last_t = now

        if frame_count % 15 == 0:
            elapsed = now - fps_timer
            if elapsed > 0:
                measured_fps = 15.0 / elapsed
            fps_timer = now

        # -----------------------------------------------------------------
        # Vision Detection & Sub-Pixel Centroiding
        # -----------------------------------------------------------------
        detected_pos, error_px, snr_db = tracker.process_frame(frame)
        error_arcsec = error_px * ARCSEC_PER_PIXEL if detected_pos else 999.0

        # -----------------------------------------------------------------
        # PTZ Slew & Gimbal Motion Control
        # -----------------------------------------------------------------
        cmd_vx = 0.0
        cmd_vy = 0.0

        if GIMBAL_STATE["auto_track"]:
            if tracker.loss_frames > 35:
                # Autonomous Expanding Spiral Re-Acquisition Scan (IEEE ICSOS 2025 PAT standard)
                # When lock is broken by blackout or extreme flare, sweep in an expanding spiral
                if tracker.loss_frames > 110:
                    tracker.loss_frames = 36 # reset spiral search back to center
                    GIMBAL_STATE["cam_x"] = UNIVERSE_WIDTH_PX / 2.0
                    GIMBAL_STATE["cam_y"] = UNIVERSE_HEIGHT_PX / 2.0

                scan_t = (tracker.loss_frames - 35) * 0.033
                scan_radius = min(220.0, 25.0 + scan_t * 50.0)
                scan_angle = scan_t * 3.8
                cmd_vx = scan_radius * 3.8 * (-math.sin(scan_angle))
                cmd_vy = scan_radius * 3.8 * (math.cos(scan_angle))
            else:
                # Autonomous AI Tracking Mode (PID + Kalman Feedforward)
                cmd_vx, cmd_vy = controller.update(detected_pos, dt)
        else:
            # Manual Operator Override Mode
            cmd_vx = GIMBAL_STATE["manual_vx"]
            cmd_vy = GIMBAL_STATE["manual_vy"]

        # Enforce statutory slew rate limit (5.0 deg/s)
        speed = math.hypot(cmd_vx, cmd_vy)
        if speed > max_slew_px_s:
            scale = max_slew_px_s / speed
            cmd_vx *= scale
            cmd_vy *= scale

        # Move PTZ camera
        GIMBAL_STATE["cam_x"] += cmd_vx * dt
        GIMBAL_STATE["cam_y"] += cmd_vy * dt

        # Universe boundaries
        half_w = CAMERA_WIDTH_PX / 2.0
        half_h = CAMERA_HEIGHT_PX / 2.0
        GIMBAL_STATE["cam_x"] = float(np.clip(GIMBAL_STATE["cam_x"], half_w, UNIVERSE_WIDTH_PX - half_w))
        GIMBAL_STATE["cam_y"] = float(np.clip(GIMBAL_STATE["cam_y"], half_h, UNIVERSE_HEIGHT_PX - half_h))

        slew_rate = (math.hypot(cmd_vx, cmd_vy) * DEG_PER_PIXEL)

        # -----------------------------------------------------------------
        # Closed-Loop Feedback to Node A (Sends updated camera center)
        # -----------------------------------------------------------------
        fb_msg = json.dumps({
            "cam_x": GIMBAL_STATE["cam_x"],
            "cam_y": GIMBAL_STATE["cam_y"]
        }).encode('utf-8')
        try:
            sock_tx.sendto(fb_msg, node_a_addr)
        except Exception:
            pass

        # Update telemetry object
        LATEST_TELEMETRY["frame_id"] = meta_json["frame_id"]
        LATEST_TELEMETRY["timestamp"] = meta_json["timestamp"]
        LATEST_TELEMETRY["centroid_x"] = detected_pos.x if detected_pos else 320.0
        LATEST_TELEMETRY["centroid_y"] = detected_pos.y if detected_pos else 240.0
        LATEST_TELEMETRY["cam_x"] = GIMBAL_STATE["cam_x"]
        LATEST_TELEMETRY["cam_y"] = GIMBAL_STATE["cam_y"]
        LATEST_TELEMETRY["error_px"] = float(error_px)
        LATEST_TELEMETRY["error_arcsec"] = float(error_arcsec)
        LATEST_TELEMETRY["slew_rate_deg_s"] = float(slew_rate)
        LATEST_TELEMETRY["fps"] = float(measured_fps)
        LATEST_TELEMETRY["locked"] = bool(detected_pos and error_px <= 10.0)
        LATEST_TELEMETRY["auto_track"] = GIMBAL_STATE["auto_track"]
        LATEST_TELEMETRY["true_x"] = float(meta_json["apparent_local_x"])
        LATEST_TELEMETRY["true_y"] = float(meta_json["apparent_local_y"])
        # Forward physical channel states from upstream meta_json
        LATEST_TELEMETRY["turbulence_active"] = meta_json.get("turbulence_active", True)
        LATEST_TELEMETRY["fog_active"] = meta_json.get("fog_active", False)
        LATEST_TELEMETRY["noise_ratio"] = meta_json.get("sp_noise_ratio", 0.10)

        # -----------------------------------------------------------------
        # Terminal 2 Visual Cockpit Window
        # -----------------------------------------------------------------
        bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        cx, cy = int(CAMERA_WIDTH_PX / 2), int(CAMERA_HEIGHT_PX / 2)

        # Crosshairs & 10px SLA circle
        cv2.line(bgr, (cx - 20, cy), (cx + 20, cy), (80, 80, 80), 1)
        cv2.line(bgr, (cx, cy - 20), (cx, cy + 20), (80, 80, 80), 1)
        cv2.circle(bgr, (cx, cy), 10, (100, 100, 100), 1)

        if detected_pos:
            dx, dy = int(round(detected_pos.x)), int(round(detected_pos.y))
            lock_color = (0, 230, 115) if error_px <= 10.0 else (0, 165, 255)
            cv2.rectangle(bgr, (dx - 14, dy - 14), (dx + 14, dy + 14), lock_color, 2)
            cv2.circle(bgr, (dx, dy), 2, (0, 255, 255), -1)
            cv2.line(bgr, (cx, cy), (dx, dy), (0, 140, 255), 1)
            cv2.putText(bgr, f"TRACK LOCKED ({dx}, {dy})", (dx + 16, dy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, lock_color, 1)

        mode_txt = "AUTO-TRACK" if GIMBAL_STATE["auto_track"] else "MANUAL OPERATOR OVERRIDE"
        mode_col = (0, 230, 115) if GIMBAL_STATE["auto_track"] else (0, 200, 255)

        cv2.putText(bgr, f"NODE B: GROUND OPTICAL TERMINAL [{mode_txt}]", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, mode_col, 2)
        cv2.putText(bgr, f"CAM POS: ({GIMBAL_STATE['cam_x']:.1f}, {GIMBAL_STATE['cam_y']:.1f}) | ERR: {error_px:4.2f} px | {measured_fps:4.1f} FPS",
                    (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 220, 220), 1)

        # Broadcast telemetry JSON to orchestrator if requested
        if sock_telem is not None:
            try:
                telem_bytes = json.dumps(LATEST_TELEMETRY).encode('utf-8')
                sock_telem.sendto(telem_bytes, telem_addr)
            except Exception:
                pass

        # Stream BGR tracking frame to web server if requested
        if stream_sender is not None:
            try:
                _, jpg_stream = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, 60])
                stream_sender.send_frame(frame_count, jpg_stream.tobytes())
            except Exception:
                pass

        if not args.headless:
            cv2.imshow("Node B: Ground Optical Tracker (Terminal 2)", bgr)
            key = cv2.waitKey(1) & 0xFF
            
            # Interactive PTZ Controls
            step_manual = 400.0 # px/s
            if key == ord('q') or key == 27:
                break
            elif key in (ord('w'), 0):  # Tilt Up (W or Up Arrow)
                GIMBAL_STATE["auto_track"] = False
                GIMBAL_STATE["manual_vy"] = -step_manual
                GIMBAL_STATE["manual_vx"] = 0.0
                print("[*] Operator PTZ Command: TILT UP")
            elif key in (ord('s'), 1):  # Tilt Down (S or Down Arrow)
                GIMBAL_STATE["auto_track"] = False
                GIMBAL_STATE["manual_vy"] = step_manual
                GIMBAL_STATE["manual_vx"] = 0.0
                print("[*] Operator PTZ Command: TILT DOWN")
            elif key in (ord('a'), 2):  # Pan Left (A or Left Arrow)
                GIMBAL_STATE["auto_track"] = False
                GIMBAL_STATE["manual_vx"] = -step_manual
                GIMBAL_STATE["manual_vy"] = 0.0
                print("[*] Operator PTZ Command: PAN LEFT")
            elif key in (ord('d'), 3):  # Pan Right (D or Right Arrow)
                GIMBAL_STATE["auto_track"] = False
                GIMBAL_STATE["manual_vx"] = step_manual
                GIMBAL_STATE["manual_vy"] = 0.0
                print("[*] Operator PTZ Command: PAN RIGHT")
            elif key in (ord('m'), ord('M'), 32):  # Space or M toggles Auto/Manual
                GIMBAL_STATE["auto_track"] = not GIMBAL_STATE["auto_track"]
                GIMBAL_STATE["manual_vx"] = 0.0
                GIMBAL_STATE["manual_vy"] = 0.0
                print(f"[*] PTZ Mode: {'AUTONOMOUS' if GIMBAL_STATE['auto_track'] else 'MANUAL OVERRIDE'}")
            elif key in (ord('r'), ord('R')):
                GIMBAL_STATE["cam_x"] = UNIVERSE_WIDTH_PX / 2.0
                GIMBAL_STATE["cam_y"] = UNIVERSE_HEIGHT_PX / 2.0
                GIMBAL_STATE["auto_track"] = True
                GIMBAL_STATE["manual_vx"] = 0.0
                GIMBAL_STATE["manual_vy"] = 0.0
                print("[*] PTZ Camera Re-Centered.")
            else:
                # Damp manual velocity if key not pressed
                GIMBAL_STATE["manual_vx"] *= 0.5
                GIMBAL_STATE["manual_vy"] *= 0.5

    sock_rx.close()
    sock_tx.close()
    if sock_stream is not None:
        sock_stream.close()
    if sock_telem is not None:
        sock_telem.close()
    if not args.headless:
        cv2.destroyAllWindows()
    print("[+] Node B stopped.")

if __name__ == "__main__":
    main()
