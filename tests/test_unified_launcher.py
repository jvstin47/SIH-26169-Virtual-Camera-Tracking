"""
Unit tests for Phoenix-X Master Unified Launcher and HTTP endpoints.
Problem Statement ID: SIH 26169 (ISRO / SAC)
"""

import unittest
import urllib.request
import json
import time
import socket
import threading
from launch_unified_app import ThreadedHTTPServer, MasterUnifiedHandler, LATEST_TELEMETRY, LOG_BUFFER, append_log

class TestUnifiedApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_port = 8899
        cls.httpd = ThreadedHTTPServer(("127.0.0.1", cls.test_port), MasterUnifiedHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_telemetry_endpoint(self):
        url = f"http://127.0.0.1:{self.test_port}/telemetry"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode('utf-8'))
        self.assertIn("error_px", data)
        self.assertIn("slew_rate_deg_s", data)
        self.assertIn("locked", data)

    def test_logs_endpoint(self):
        append_log("TEST_NODE", "Testing rolling log buffer functionality")
        url = f"http://127.0.0.1:{self.test_port}/logs"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode('utf-8'))
        self.assertIsInstance(data, list)
        self.assertTrue(any(e["node"] == "TEST_NODE" for e in data))

    def test_control_ptz_endpoint(self):
        url = f"http://127.0.0.1:{self.test_port}/ptz?cmd=recenter"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode('utf-8'))
        self.assertEqual(data.get("status"), "ok")

    def test_satellite_goto_and_steer_controls(self):
        # Test Map Click GOTO
        url_goto = f"http://127.0.0.1:{self.test_port}/control?target=satellite&action=goto&x=1350&y=850"
        req = urllib.request.urlopen(url_goto)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode('utf-8'))
        self.assertEqual(data.get("status"), "ok")

        # Test Directional Steering (I, K, J, L)
        for steer_cmd in ["steer_up", "steer_down", "steer_left", "steer_right", "evasive"]:
            url_steer = f"http://127.0.0.1:{self.test_port}/control?target=satellite&action={steer_cmd}"
            req = urllib.request.urlopen(url_steer)
            self.assertEqual(req.status, 200)

    def test_channel_disturbances_controls(self):
        # Test Channel 1-5 Actions
        for action in ["step_noise", "toggle_turbulence", "toggle_fog", "glare", "blackout"]:
            url_chan = f"http://127.0.0.1:{self.test_port}/control?target=channel&action={action}"
            req = urllib.request.urlopen(url_chan)
            self.assertEqual(req.status, 200)
            data = json.loads(req.read().decode('utf-8'))
            self.assertEqual(data.get("status"), "ok")

    def test_ground_tracker_ptz_controls(self):
        # Test Tracker WASD commands
        for cmd in ["pan_left", "pan_right", "tilt_up", "tilt_down", "toggle_auto", "recenter"]:
            url_ptz = f"http://127.0.0.1:{self.test_port}/ptz?cmd={cmd}"
            req = urllib.request.urlopen(url_ptz)
            self.assertEqual(req.status, 200)
            data = json.loads(req.read().decode('utf-8'))
            self.assertEqual(data.get("status"), "ok")

if __name__ == "__main__":
    unittest.main()
