#!/usr/bin/env python3
"""
Unit tests for Orbital & Ephemeris Kinematics Propagator
Problem Statement ID: SIH 26169 (ISRO / SAC)
"""

import unittest
import math
from src.simulation.orbital_propagator import OrbitalKinematicsPropagator

class TestOrbitalPropagator(unittest.TestCase):

    def test_leo_pass_kinematics(self):
        prop = OrbitalKinematicsPropagator(scenario="leo_to_ground")
        
        # Test start, peak, and end
        az_0, el_0, rng_0 = prop.propagate_leo_pass(0.0)
        az_mid, el_mid, rng_mid = prop.propagate_leo_pass(15.0)
        az_end, el_end, rng_end = prop.propagate_leo_pass(30.0)

        # Elevation should culminate at midpoint (zenith)
        self.assertGreater(el_mid, el_0)
        self.assertGreater(el_mid, el_end)
        
        # Range should be minimum at culmination
        self.assertLess(rng_mid, rng_0)
        self.assertLess(rng_mid, rng_end)

        # Slant range should be physically plausible for 550 km LEO (550 km to 2000 km)
        self.assertGreaterEqual(rng_mid, 500.0)
        self.assertLessEqual(rng_0, 2500.0)

    def test_uav_path_kinematics(self):
        prop = OrbitalKinematicsPropagator(scenario="uav_to_ground")
        az_0, el_0, rng_0 = prop.propagate_uav_path(0.0)
        az_1, el_1, rng_1 = prop.propagate_uav_path(5.0)

        # Azimuth should be in valid degree range [0, 360)
        self.assertGreaterEqual(az_0, 0.0)
        self.assertLess(az_0, 360.0)

        # Range should be in airborne altitude range (1.0 to 3.0 km)
        self.assertGreaterEqual(rng_0, 0.8)
        self.assertLessEqual(rng_0, 5.0)

    def test_pinhole_projection_and_fov(self):
        prop = OrbitalKinematicsPropagator()
        
        # When gimbal matches target perfectly, projection must be at center (320, 240)
        px, py, in_fov = prop.project_to_fpa(140.0, 45.0, 140.0, 45.0)
        self.assertAlmostEqual(px, 320.0, places=1)
        self.assertAlmostEqual(py, 240.0, places=1)
        self.assertTrue(in_fov)

        # When target is far outside FOV (e.g. 10 degrees away when FOV is 4x3)
        px_out, py_out, in_fov_out = prop.project_to_fpa(155.0, 45.0, 140.0, 45.0)
        self.assertFalse(in_fov_out)

if __name__ == '__main__':
    unittest.main()
