"""
Optical Physics, Atmospheric Degradation & Noise Injection Pipeline
Implements:
1. Diffraction-limited Airy Disc / 2D Gaussian Spot Profile
2. Multi-Harmonic Platform Jitter (+-20 px / frame)
3. Atmospheric Scattering (Beer-Lambert Fog / Haze attenuation)
4. Stochastic Sensor Noise: 10% Salt & Pepper, Poisson Shot Noise, and Gaussian Thermal Noise.
"""

import math
import numpy as np
import cv2

class OpticalEngine:
    def __init__(self, spot_size_px: int = 10, spot_peak_intensity: int = 250):
        self.spot_size_px = spot_size_px
        self.spot_peak_intensity = spot_peak_intensity
        self.sigma = spot_size_px / 3.0  # Gaussian spot radius
        
        # State toggles for disturbances
        self.enable_salt_and_pepper = False
        self.enable_poisson = False
        self.enable_gaussian = False
        self.enable_fog = False
        self.enable_jitter = False
        
        # Jitter parameters
        self.jitter_amplitude = 12.0  # px amplitude
        self.jitter_freq_1 = 17.3     # Hz (Satellite reaction wheel)
        self.jitter_freq_2 = 29.1     # Hz (UAV rotor resonance)

    def get_platform_jitter(self, t: float) -> tuple:
        """Computes instantaneous 2D jitter displacement (dx, dy) in pixels."""
        if not self.enable_jitter:
            return (0.0, 0.0)
            
        dx = (self.jitter_amplitude * 0.6 * math.sin(2.0 * math.pi * self.jitter_freq_1 * t) +
              self.jitter_amplitude * 0.4 * math.cos(2.0 * math.pi * self.jitter_freq_2 * t) +
              np.random.normal(0, 1.5))
        dy = (self.jitter_amplitude * 0.6 * math.cos(2.0 * math.pi * self.jitter_freq_1 * t) +
              self.jitter_amplitude * 0.4 * math.sin(2.0 * math.pi * self.jitter_freq_2 * t) +
              np.random.normal(0, 1.5))
        # Clamped to statutory +-20 px/frame limit
        dx = float(np.clip(dx, -20.0, 20.0))
        dy = float(np.clip(dy, -20.0, 20.0))
        return (dx, dy)

    def render_beacon_on_frame(self, frame: np.ndarray, target_local_x: float, target_local_y: float) -> np.ndarray:
        """Renders the sub-pixel diffraction spot on the 640x480 monochrome viewport."""
        h, w = frame.shape
        x0 = int(round(target_local_x))
        y0 = int(round(target_local_y))
        
        # Sub-pixel coordinate fractional offsets
        fx = target_local_x - x0
        fy = target_local_y - y0
        
        radius = int(self.spot_size_px * 2)
        y_min = max(0, y0 - radius)
        y_max = min(h, y0 + radius + 1)
        x_min = max(0, x0 - radius)
        x_max = min(w, x0 + radius + 1)
        
        if x_min >= x_max or y_min >= y_max:
            return frame  # Out of view
            
        yy, xx = np.mgrid[y_min - y0:y_max - y0, x_min - x0:x_max - x0]
        # 2D continuous Gaussian gray-diffusion surface
        dist_sq = (xx - fx)**2 + (yy - fy)**2
        spot = self.spot_peak_intensity * np.exp(-dist_sq / (2.0 * self.sigma**2))
        
        # Additive blending
        current_patch = frame[y_min:y_max, x_min:x_max].astype(np.float32)
        blended = np.clip(current_patch + spot, 0, 255).astype(np.uint8)
        frame[y_min:y_max, x_min:x_max] = blended
        return frame

    def apply_disturbances(self, frame: np.ndarray) -> np.ndarray:
        """Applies atmospheric attenuation, 10% S&P noise, Poisson, and Gaussian noise."""
        result = frame.copy().astype(np.float32)
        
        # 1. Atmospheric Attenuation / Fog (Beer-Lambert Law)
        if self.enable_fog:
            # Contrast reduction and elevated atmospheric background haze
            attenuation_factor = 0.35  # Transmittance
            sky_glow = 70.0            # Atmospheric ambient backscatter
            result = result * attenuation_factor + sky_glow
            
        # 2. Gaussian Thermal Sensor Noise (sigma <= 20)
        if self.enable_gaussian:
            gauss_noise = np.random.normal(0, 18.0, frame.shape)
            result += gauss_noise
            
        # 3. Poisson Shot Noise (Signal-dependent noise)
        if self.enable_poisson:
            vals = np.clip(result, 1.0, 255.0)
            # Poisson approximation scaled for 8-bit dynamic range
            poisson_scaled = np.random.poisson(vals / 5.0) * 5.0
            result = (result * 0.7) + (poisson_scaled * 0.3)
            
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        # 4. Salt and Pepper Noise (Around 10% of image area)
        if self.enable_salt_and_pepper:
            prob = 0.10  # 10% of total image pixels corrupted
            rnd = np.random.random(frame.shape)
            # Salt (255 intensity hot pixels)
            result[rnd < (prob / 2.0)] = 255
            # Pepper (0 intensity cold pixels)
            result[(rnd >= (prob / 2.0)) & (rnd < prob)] = 0
            
        return result
