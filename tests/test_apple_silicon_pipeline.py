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
        # In CPU mode or NumPy fallback
        self.assertTrue(dev == "numpy" or str(dev) == "cpu")

if __name__ == "__main__":
    unittest.main()
