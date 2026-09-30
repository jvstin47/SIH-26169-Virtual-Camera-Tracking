import unittest
import numpy as np
import cv2
from src.core.coordinates import (
    Point2D, CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX,
    arcsec_to_pixels, pixels_to_urad, FOV_AZ_DEG
)
from src.camera.ptz_camera import VirtualPTZCamera
from src.vision.tracker import BeaconTracker
from src.vision.deep_saliency_net import DeepBeaconSaliencyNet
from src.control.gimbal_controller import GimbalController
from src.optics.atmosphere_and_noise import inject_salt_and_pepper_noise

class TestFSOCPipeline(unittest.TestCase):

    def test_coordinate_conversions(self):
        # 1 pixel = 22.5 arcseconds = 109.08 urad
        px = 10.0
        urad = pixels_to_urad(px)
        self.assertAlmostEqual(urad, 1090.83, places=1)
        
        arcsec = 22.5
        calc_px = arcsec_to_pixels(arcsec)
        self.assertAlmostEqual(calc_px, 1.0, places=2)

    def test_ptz_slew_rate_limit(self):
        cam = VirtualPTZCamera(initial_x=960.0, initial_y=540.0)
        # Attempt to command an extreme velocity (e.g. 5000 px/s)
        # Slew rate max is 800 px/s => with dt = 1/30s, max travel is 800 / 30 = 26.67 px
        cam.update_actuator(5000.0, 0.0, dt=1.0/30.0)
        delta_x = cam.x - 960.0
        self.assertLessEqual(delta_x, 26.7)
        self.assertGreater(delta_x, 25.0)

    def test_deep_saliency_net_shape(self):
        net = DeepBeaconSaliencyNet()
        dummy_frame = np.zeros((480, 640), dtype=np.uint8)
        # Place synthetic beacon
        cv2.circle(dummy_frame, (320, 240), 5, 255, -1)
        heatmap, (px, py), conf = net.forward(dummy_frame)
        self.assertEqual(heatmap.shape, (480, 640))
        self.assertAlmostEqual(px, 320, delta=5.0)
        self.assertAlmostEqual(py, 240, delta=5.0)
        self.assertGreater(conf, 0.5)

    def test_tracker_under_10_percent_sp_noise(self):
        tracker = BeaconTracker()
        frame = np.zeros((CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX), dtype=np.uint8)
        true_x, true_y = 312.4, 238.7
        # Inject Gaussian beacon
        for r in range(-6, 7):
            for c in range(-6, 7):
                y = int(round(true_y)) + r
                x = int(round(true_x)) + c
                if 0 <= y < CAMERA_HEIGHT_PX and 0 <= x < CAMERA_WIDTH_PX:
                    val = 240.0 * np.exp(-((x - true_x)**2 + (y - true_y)**2) / (2.0 * 2.5**2))
                    frame[y, x] = np.clip(val, 0, 255).astype(np.uint8)
        
        # Inject 10% Salt & Pepper noise
        noisy_frame = inject_salt_and_pepper_noise(frame, noise_ratio=0.10)
        
        # Detect
        centroid, err_px, snr = tracker.process_frame(noisy_frame)
        self.assertIsNotNone(centroid)
        self.assertAlmostEqual(centroid.x, true_x, delta=0.5)
        self.assertAlmostEqual(centroid.y, true_y, delta=0.5)

    def test_gimbal_controller_response_and_coast(self):
        controller = GimbalController()
        # Initialize at center
        vx, vy = controller.update(Point2D(320.0, 240.0), dt=1.0/30.0)
        self.assertAlmostEqual(vx, 0.0, delta=0.1)
        self.assertAlmostEqual(vy, 0.0, delta=0.1)

        # Off-center target displaced to the right (+10 px)
        vx, vy = controller.update(Point2D(330.0, 240.0), dt=1.0/30.0)
        self.assertGreater(vx, 0.0)  # Should command positive X velocity

        # Coasting when target is lost
        coast_vx, coast_vy = controller.update(None, dt=1.0/30.0)
        self.assertIsInstance(coast_vx, float)
        self.assertIsInstance(coast_vy, float)

    def test_atmospheric_channel_emulator(self):
        from distributed_demo.atmospheric_channel import AtmosphericChannelEmulator
        channel = AtmosphericChannelEmulator()
        frame = np.full((CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX), 20, dtype=np.uint8)
        # Place beacon
        cv2.circle(frame, (320, 240), 6, 250, -1)
        
        corrupted = channel.apply_channel_effects(frame, t=1.0)
        self.assertEqual(corrupted.shape, (CAMERA_HEIGHT_PX, CAMERA_WIDTH_PX))
        
        # Test tracker on channel-corrupted frame (should stay within ISRO 10 px SLA despite turbulence displacement)
        tracker = BeaconTracker()
        centroid, err_px, snr = tracker.process_frame(corrupted)
        self.assertIsNotNone(centroid)
        self.assertAlmostEqual(centroid.x, 320.0, delta=10.0)
        self.assertAlmostEqual(centroid.y, 240.0, delta=10.0)

if __name__ == '__main__':
    unittest.main()
