#!/usr/bin/env python3
"""
Node B: Autonomous Ground Optical Tracking Station (Terminal 2)
Listens on UDP port 9999 for incoming noisy video frames from Node A.
Runs AI Denoising, Sub-Pixel Centroiding, and Kalman-PID Gimbal Servoing.
Serves real-time telemetry to the browser at http://localhost:8080.
"""

import sys
import os
import time
import math
import socket
import json
import threading
import http.server
import numpy as np
import cv2

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.coordinates import CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX, ARCSEC_PER_PIXEL
from src.vision.tracker import BeaconTracker
from src.control.gimbal_controller import GimbalController

# Shared global telemetry for web cockpit
LATEST_TELEMETRY = {
    "frame_id": 0,
    "timestamp": 0.0,
    "centroid_x": 320.0,
    "centroid_y": 240.0,
    "error_px": 0.0,
    "error_arcsec": 0.0,
    "slew_rate_deg_s": 0.0,
    "fps": 30.0,
    "locked": True,
    "true_x": 320.0,
    "true_y": 240.0
}

class TelemetryServer(http.server.SimpleHTTPRequestHandler):
    """Serves real-time JSON telemetry and static files to browser."""
    def do_GET(self):
        if self.path == "/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(LATEST_TELEMETRY).encode('utf-8'))
        else:
            # Serve web demo directory
            web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_demo")
            self.directory = web_dir
            super().do_GET()

    def log_message(self, format, *args):
        pass # Suppress HTTP logs in terminal

def start_http_server():
    server = http.server.HTTPServer(("127.0.0.1", 8080), TelemetryServer)
    server.serve_forever()

def main():
    print("=" * 70)
    print("  NODE B: AUTONOMOUS GROUND OPTICAL TRACKING TERMINAL (TERMINAL 2)")
    print("=" * 70)
    print("[*] Binding UDP listener on 127.0.0.1:9999...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 9999))
    sock.settimeout(2.0)

    # Start telemetry HTTP server in background thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    print("[+] Live Mission Control Dashboard active at: http://localhost:8080/live.html")
    print("[*] Waiting for optical beacon feed from Node A (target_satellite.py)...\n")

    tracker = BeaconTracker()
    controller = GimbalController()

    frame_count = 0
    t_start = time.time()
    last_t = time.time()
    measured_fps = 30.0

    while True:
        try:
            data, _ = sock.recvfrom(65535)
        except socket.timeout:
            continue

        if data == b"STOP":
            print("[*] Received STOP packet from Node A.")
            break

        # Parse packet: 4 bytes meta length + JSON + JPEG bytes
        meta_len = int.from_bytes(data[:4], 'big')
        meta_json = json.loads(data[4:4 + meta_len].decode('utf-8'))
        jpg_bytes = data[4 + meta_len:]

        # Decode JPEG frame
        nparr = np.frombuffer(jpg_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if frame is None:
            continue

        frame_count += 1
        now = time.time()
        dt = max(0.001, now - last_t)
        last_t = now
        
        if frame_count % 15 == 0:
            measured_fps = 15.0 / (now - (t_start + (frame_count - 15) * 0.033))

        # -----------------------------------------------------------------
        # Real-Time Perception & Tracking Core
        # -----------------------------------------------------------------
        detected_pos, error_px, snr_db = tracker.process_frame(frame)
        error_arcsec = error_px * ARCSEC_PER_PIXEL if detected_pos else 999.0

        # Gimbal servo control update
        cmd_vx, cmd_vy = controller.update(detected_pos, dt)
        slew_rate = math.hypot(cmd_vx, cmd_vy) * 0.00625  # deg/s

        # Update global telemetry dictionary
        LATEST_TELEMETRY["frame_id"] = meta_json["frame_id"]
        LATEST_TELEMETRY["timestamp"] = meta_json["timestamp"]
        LATEST_TELEMETRY["centroid_x"] = detected_pos.x if detected_pos else 320.0
        LATEST_TELEMETRY["centroid_y"] = detected_pos.y if detected_pos else 240.0
        LATEST_TELEMETRY["error_px"] = float(error_px)
        LATEST_TELEMETRY["error_arcsec"] = float(error_arcsec)
        LATEST_TELEMETRY["slew_rate_deg_s"] = float(slew_rate)
        LATEST_TELEMETRY["fps"] = float(measured_fps)
        LATEST_TELEMETRY["locked"] = bool(detected_pos and error_px <= 10.0)
        LATEST_TELEMETRY["true_x"] = float(meta_json["apparent_local_x"])
        LATEST_TELEMETRY["true_y"] = float(meta_json["apparent_local_y"])

        # Visual Cockpit HUD Rendering
        bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        cx, cy = int(CAMERA_WIDTH_PX / 2), int(CAMERA_HEIGHT_PX / 2)

        # Bore-sight crosshairs
        cv2.line(bgr, (cx - 20, cy), (cx + 20, cy), (80, 80, 80), 1)
        cv2.line(bgr, (cx, cy - 20), (cx, cy + 20), (80, 80, 80), 1)
        cv2.circle(bgr, (cx, cy), 10, (100, 100, 100), 1)

        # Draw lock reticle
        if detected_pos:
            dx, dy = int(round(detected_pos.x)), int(round(detected_pos.y))
            lock_color = (0, 230, 115) if error_px <= 10.0 else (0, 165, 255)
            cv2.rectangle(bgr, (dx - 14, dy - 14), (dx + 14, dy + 14), lock_color, 2)
            cv2.circle(bgr, (dx, dy), 2, (0, 255, 255), -1)
            cv2.line(bgr, (cx, cy), (dx, dy), (0, 140, 255), 1)
            cv2.putText(bgr, f"TRACK LOCKED ({dx}, {dy})", (dx + 16, dy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, lock_color, 1)

        # HUD Top Banner
        status_txt = "LOCKED" if (detected_pos and error_px <= 10.0) else "ACQUIRING..."
        status_col = (0, 230, 115) if (detected_pos and error_px <= 10.0) else (0, 165, 255)
        
        cv2.putText(bgr, f"NODE B: GROUND TRACKER // {status_txt}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, status_col, 2)
        cv2.putText(bgr, f"ERROR: {error_px:4.2f} px ({error_arcsec:5.1f}\") | SLEW: {slew_rate:4.2f} deg/s | {measured_fps:4.1f} FPS",
                    (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 220), 1)

        cv2.imshow("Node B: Autonomous Ground Optical Tracker (Terminal 2)", bgr)
        if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
            break

    sock.close()
    cv2.destroyAllWindows()
    print("[+] Node B stopped.")

if __name__ == "__main__":
    main()
