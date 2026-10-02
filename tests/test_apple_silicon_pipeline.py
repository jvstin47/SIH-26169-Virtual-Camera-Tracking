"""
Unit tests for Apple Silicon (MPS / MLX) and BeaconNet-Nano pipelines.
Problem Statement ID: SIH 26169 (ISRO / SAC)
"""

import unittest
import numpy as np
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vision.beacon_onnx_model import BeaconNetNanoNumPy, MODEL_CONFIG
from src.vision.beacon_mlx_model import is_mlx_available
from scripts.train_beacon_net import generate_gaussian_target, get_optimal_device

class TestAppleSiliconPipeline(unittest.TestCase):
    def test_model_specs(self):
        self.assertEqual(MODEL_CONFIG["name"], "BeaconNet-Nano")
        self.assertLess(MODEL_CONFIG["memory_kb"], 15.0)
        self.assertEqual(MODEL_CONFIG["param_count"], 2417)

    def test_gaussian_heatmap_generation(self):
        h, w = 240, 320
        target = generate_gaussian_target(h, w, 160.0, 120.0, sigma=2.0)
        self.assertEqual(target.shape, (h, w))
        self.assertAlmostEqual(target[120, 160], 1.0, places=4)
        self.assertLess(target[0, 0], 1e-4)

    def test_numpy_fallback_inference(self):
        model = BeaconNetNanoNumPy()
        dummy_fpa = np.random.uniform(0.0, 1.0, size=(120, 160)).astype(np.float32)
        out = model.forward(dummy_fpa)
        self.assertEqual(out.shape, (120, 160))
        self.assertTrue(np.all(out >= 0.0) and np.all(out <= 1.0))

    def test_optimal_device_detection(self):
        dev = get_optimal_device(force_cpu=True)
        # When torch is not installed, returns "numpy"; otherwise returns cpu device
        self.assertTrue(dev == "numpy" or str(dev) in ("cpu", "mps", "cuda"))

    def test_mlx_beacon_net_forward(self):
        """Validates Apple MLX BeaconNetNanoMLX inference when MLX is installed."""
        if not is_mlx_available():
            self.skipTest("Apple MLX not installed on this machine — skipping MLX inference test.")
        from src.vision.beacon_mlx_model import BeaconNetNanoMLX
        import mlx.core as mx
        model = BeaconNetNanoMLX()
        # Small input in NHWC layout (MLX convention)
        dummy = mx.zeros((1, 60, 80, 1))
        heatmap = model(dummy)
        mx.eval(heatmap)
        self.assertEqual(heatmap.shape, (1, 60, 80, 1))
        # Sigmoid output must be in [0, 1]
        h_np = np.array(heatmap.tolist())
        self.assertTrue(np.all(h_np >= 0.0) and np.all(h_np <= 1.0))

if __name__ == "__main__":
    unittest.main()
