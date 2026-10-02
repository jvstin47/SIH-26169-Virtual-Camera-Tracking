#!/usr/bin/env python3
"""
Phoenix-X: Master Unified Launcher & Multi-Node Orchestrator
Problem Statement ID: SIH 26169 (ISRO / SAC)
AI-Based Virtual Camera Tracking System for Mobile Free Space Optical Communication

Launches and synchronizes all subsystems in one unified application:
  1. Terminal 1 / Node A: Remote Maneuvering Satellite Transmitter (UDP 9999)
  2. Terminal 2 / Node B: Active Physical Atmospheric Channel (UDP 9997)
  3. Terminal 3 / Node C: Autonomous Ground Optical Tracking Station (UDP 9998 feedback)
  4. Unified HTTP Telemetry & Multi-Stream Web Cockpit (http://localhost:8080/unified.html)
"""

import sys
import os
import time
import socket
import json
import threading
import subprocess
import webbrowser
import argparse
import http.server
import socketserver
import urllib.parse
from datetime import datetime

# Workspace root
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORKSPACE_DIR)

# Global State & Buffers
STREAM_FRAMES = {
    "node_a": None,
    "node_b": None,
    "node_c": None
}
LATEST_TELEMETRY = {
    "frame_id": 0,
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
    "turbulence_active": True,
    "fog_active": False,
    "noise_ratio": 0.10
}
LOG_BUFFER = []
LOG_LOCK = threading.Lock()
MAX_LOG_ENTRIES = 400
IS_SHUTTING_DOWN = False

def append_log(node_name: str, message: str):
    """Appends timestamped log message to rolling buffer."""
    ts = datetime.now().strftime("%H:%M:%S")
    entry = {
        "timestamp": ts,
        "node": node_name,
        "message": message.strip()
    }
    with LOG_LOCK:
        LOG_BUFFER.append(entry)
        if len(LOG_BUFFER) > MAX_LOG_ENTRIES:
            LOG_BUFFER.pop(0)

# -----------------------------------------------------------------------------
# Background UDP Stream Capture Receivers
# -----------------------------------------------------------------------------
def udp_stream_receiver(port: int, key: str):
    """Captures JPEG frames mirrored by child nodes."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", port))
    sock.settimeout(0.5)
    while not IS_SHUTTING_DOWN:
        try:
            data, _ = sock.recvfrom(65535)
            STREAM_FRAMES[key] = data
        except socket.timeout:
            continue
        except Exception:
            break
    sock.close()

def udp_telemetry_receiver(port: int):
    """Captures telemetry JSON broadcast from Ground Tracker."""
    global LATEST_TELEMETRY
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", port))
    sock.settimeout(0.5)
    while not IS_SHUTTING_DOWN:
        try:
            data, _ = sock.recvfrom(4096)
            parsed = json.loads(data.decode('utf-8'))
            LATEST_TELEMETRY.update(parsed)
        except socket.timeout:
            continue
        except Exception:
            break
    sock.close()

# -----------------------------------------------------------------------------
# Master HTTP & MJPEG Telemetry Server
# -----------------------------------------------------------------------------
class MasterUnifiedHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Redirect root to unified dashboard
        if parsed.path in ("/", "/index", "/unified"):
            self.send_response(302)
            self.send_header("Location", "/unified.html")
            self.end_headers()
            return

        # Real-time Telemetry JSON API
        if parsed.path == "/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(LATEST_TELEMETRY).encode('utf-8'))
            return

        # Real-time Multi-Terminal Logs API
        if parsed.path == "/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            with LOG_LOCK:
                logs_copy = list(LOG_BUFFER)
            self.wfile.write(json.dumps(logs_copy).encode('utf-8'))
            return

        # MJPEG Video Feeds
        if parsed.path in ("/stream/node_a", "/stream/node_b", "/stream/node_c"):
            node_key = parsed.path.split("/")[-1]
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            while not IS_SHUTTING_DOWN:
                frame_data = STREAM_FRAMES.get(node_key)
                if frame_data:
                    try:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                        self.wfile.write(frame_data)
                        self.wfile.write(b"\r\n")
                    except (BrokenPipeError, ConnectionResetError):
                        break
                time.sleep(0.033) # ~30 FPS
            return

        # Operator Remote Controls
        if parsed.path.startswith("/control"):
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get("target", [""])[0]
            action = qs.get("action", [""])[0]
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if target == "satellite":
                sock.sendto(json.dumps({"cmd": action}).encode('utf-8'), ("127.0.0.1", 9998))
                append_log("MASTER", f"Dispatched to Satellite: {action}")
            elif target == "channel":
                sock.sendto(json.dumps({"action": action}).encode('utf-8'), ("127.0.0.1", 9996))
                append_log("MASTER", f"Dispatched to Channel: {action}")
            elif target == "tracker":
                sock.sendto(json.dumps({"cmd": action}).encode('utf-8'), ("127.0.0.1", 9995))
                append_log("MASTER", f"Dispatched to Tracker: {action}")
            elif action == "shutdown":
                append_log("MASTER", "Shutdown signal received from Web UI")
                threading.Thread(target=trigger_shutdown, daemon=True).start()
            sock.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            return

        # Legacy PTZ endpoint compatibility
        if parsed.path.startswith("/ptz"):
            qs = urllib.parse.parse_qs(parsed.query)
            cmd = qs.get("cmd", [""])[0]
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(json.dumps({"cmd": cmd}).encode('utf-8'), ("127.0.0.1", 9995))
            sock.close()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            return

        # Serve static assets from web_demo
        web_dir = os.path.join(WORKSPACE_DIR, "web_demo")
        self.directory = web_dir
        super().do_GET()

    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def trigger_shutdown():
    """Triggers graceful shutdown across all nodes."""
    global IS_SHUTTING_DOWN
    if IS_SHUTTING_DOWN:
        return
    IS_SHUTTING_DOWN = True
    print("\n[!] Shutting down all distributed nodes...")
    stop_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for port in (9998, 9999, 9997, 9996, 9995):
        try:
            stop_sock.sendto(b"STOP", ("127.0.0.1", port))
        except Exception:
            pass
    stop_sock.close()

# -----------------------------------------------------------------------------
# Process Piping & Log Streaming
# -----------------------------------------------------------------------------
def stream_process_output(proc: subprocess.Popen, tag: str, color_code: str):
    """Pipes subprocess stdout to master terminal and rolling web log buffer."""
    for line in iter(proc.stdout.readline, ''):
        if not line:
            break
        cleaned = line.rstrip()
        # Print with terminal color
        print(f"\033[{color_code}m[{tag}]\033[0m {cleaned}")
        append_log(tag, cleaned)
    proc.stdout.close()

# -----------------------------------------------------------------------------
# Master Application Orchestrator
# -----------------------------------------------------------------------------
def launch_all(headless: bool = False, open_browser: bool = True, http_port: int = 8080):
    global IS_SHUTTING_DOWN
    print("=" * 75)
    print("  PHOENIX-X: ALL-IN-ONE DISTRIBUTED MISSION CONTROL ORCHESTRATOR")
    print("  Smart India Hackathon 2026 | Problem Statement ID: 26169 (ISRO / SAC)")
    print("=" * 75)
    print(f"[*] Workspace Root: {WORKSPACE_DIR}")
    print(f"[*] Visual Display Mode: {'Web Cockpit (Headless Terminal Nodes)' if headless else 'Desktop GUI (OpenCV Windows + Web Cockpit)'}")
    print(f"[*] Web Server Address: http://localhost:{http_port}/unified.html\n")

    # 1. Start Stream and Telemetry UDP Listeners
    threading.Thread(target=udp_stream_receiver, args=(9981, "node_a"), daemon=True).start()
    threading.Thread(target=udp_stream_receiver, args=(9982, "node_b"), daemon=True).start()
    threading.Thread(target=udp_stream_receiver, args=(9983, "node_c"), daemon=True).start()
    threading.Thread(target=udp_telemetry_receiver, args=(9984,), daemon=True).start()

    # 2. Start Master Web Server
    httpd = ThreadedHTTPServer(("127.0.0.1", http_port), MasterUnifiedHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    append_log("MASTER", f"Unified HTTP Server active on http://127.0.0.1:{http_port}")

    # Build node command arguments
    py_exec = sys.executable
    gui_arg = ["--headless"] if headless else []

    # 3. Launch Node C Ground Tracker first (starts listening on 9997)
    cmd_track = [
        py_exec, "distributed_demo/ground_tracker.py",
        "--port", "9997",
        "--stream-port", "9983",
        "--telemetry-port", "9984",
        "--cmd-port", "9995",
        "--no-http"
    ] + gui_arg
    proc_track = subprocess.Popen(
        cmd_track, cwd=WORKSPACE_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    threading.Thread(target=stream_process_output, args=(proc_track, "TRACKER", "92"), daemon=True).start()
    time.sleep(0.4)

    # 4. Launch Node B Active Atmospheric Channel (listens on 9999, forwards to 9997)
    cmd_chan = [
        py_exec, "distributed_demo/atmospheric_channel.py",
        "--stream-port", "9982",
        "--cmd-port", "9996"
    ] + gui_arg
    proc_chan = subprocess.Popen(
        cmd_chan, cwd=WORKSPACE_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    threading.Thread(target=stream_process_output, args=(proc_chan, "CHANNEL", "93"), daemon=True).start()
    time.sleep(0.4)

    # 5. Launch Node A Satellite Transmitter (broadcasts to 9999)
    cmd_sat = [
        py_exec, "distributed_demo/target_satellite.py",
        "--port", "9999",
        "--stream-port", "9981"
    ] + gui_arg
    proc_sat = subprocess.Popen(
        cmd_sat, cwd=WORKSPACE_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    threading.Thread(target=stream_process_output, args=(proc_sat, "NODE A", "94"), daemon=True).start()

    print("\n[+] All 3 Distributed Nodes & Web Server successfully launched!")
    print(f"[+] Opening Unified Browser Cockpit: http://localhost:{http_port}/unified.html\n")
    append_log("MASTER", "All 3 nodes synchronized and streaming.")

    if open_browser:
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{http_port}/unified.html")

    # Main thread monitor loop
    try:
        while not IS_SHUTTING_DOWN:
            time.sleep(0.5)
            # Check if any process died unexpectedly
            if proc_sat.poll() is not None:
                append_log("MASTER", "Node A terminated.")
                break
            if proc_chan.poll() is not None:
                append_log("MASTER", "Atmospheric Channel terminated.")
                break
            if proc_track.poll() is not None:
                append_log("MASTER", "Ground Tracker terminated.")
                break
    except KeyboardInterrupt:
        print("\n[*] Ctrl+C received. Initiating graceful shutdown...")
    finally:
        trigger_shutdown()
        # Cleanly terminate subprocesses
        for p in (proc_sat, proc_chan, proc_track):
            try:
                p.terminate()
                p.wait(timeout=1.5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        try:
            httpd.shutdown()
        except Exception:
            pass
        print("[+] Unified application cleanly stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phoenix-X Unified Multi-Node Application")
    parser.add_argument("--headless", action="store_true", help="Run nodes without OpenCV desktop windows (pure web mode)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port for unified web cockpit (default: 8080)")
    args = parser.parse_args()

    launch_all(headless=args.headless, open_browser=not args.no_browser, http_port=args.port)
