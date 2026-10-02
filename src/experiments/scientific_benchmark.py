"""
Phoenix-X: Scientific Experiment Engine v1.0
Implements the formal Experiment Specification v1:
- Parameterized Camera (IFOV, FOV, Resolution)
- Parameterized Beacon (Gaussian PSF, Poisson + Gaussian Noise, SNR control)
- Latency Queue (Cumulative frame, processing, transport, and actuator delay)
- Algorithm Ladder (Baseline 0 -> B1 -> B2 -> B3/Phoenix-X)
- Formal Hypotheses Verification:
    H1: Latency Compensation (RMSE vs Latency tau in [0, 200] ms)
    H2: Uncertainty-Guided Reacquisition (Reacquisition Time vs Outage duration in [0.1, 5.0] s)
"""

import math
import time
import numpy as np
import cv2
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

@dataclass
class OpticalCameraParams:
    width: int = 640
    height: int = 480
    fov_az_deg: float = 4.0
    fov_el_deg: float = 3.0
    fps: float = 30.0

    @property
    def dt(self) -> float:
        return 1.0 / self.fps

    @property
    def deg_per_pixel(self) -> float:
        return self.fov_az_deg / self.width

    @property
    def arcsec_per_pixel(self) -> float:
        return self.deg_per_pixel * 3600.0

    @property
    def urad_per_pixel(self) -> float:
        return math.radians(self.deg_per_pixel) * 1e6


class SyntheticOpticalSource:
    """Generates a physical Gaussian PSF beacon on a detector with Poisson + Gaussian noise."""
    def __init__(self, psf_sigma: float = 1.5, background_mean: float = 20.0, read_noise_sigma: float = 2.0):
        self.psf_sigma = psf_sigma
        self.background_mean = background_mean
        self.read_noise_sigma = read_noise_sigma

    def render_spot(self, width: int, height: int, x0: float, y0: float, snr: float = 10.0) -> np.ndarray:
        """
        Renders a Gaussian PSF spot with controlled Signal-to-Noise Ratio (SNR).
        SNR is defined as Peak Signal / Read Noise Sigma.
        """
        peak_signal = max(10.0, snr * self.read_noise_sigma)
        
        # Fast localized patch rendering
        r = int(math.ceil(4.0 * self.psf_sigma))
        ix0, iy0 = int(round(x0)), int(round(y0))
        
        frame = np.full((height, width), self.background_mean, dtype=np.float32)
        
        if 0 <= ix0 < width and 0 <= iy0 < height:
            x1 = max(0, ix0 - r)
            x2 = min(width, ix0 + r + 1)
            y1 = max(0, iy0 - r)
            y2 = min(height, iy0 + r + 1)
            
            gy, gx = np.ogrid[y1:y2, x1:x2]
            dist_sq = (gx - x0)**2 + (gy - y0)**2
            spot = peak_signal * np.exp(-dist_sq / (2.0 * self.psf_sigma**2))
            frame[y1:y2, x1:x2] += spot

        # Noise Model: Poisson shot noise on photon counts + Gaussian read noise
        # Photon shot noise approximation
        shot_noise = np.random.normal(0, np.sqrt(np.maximum(1.0, frame)))
        read_noise = np.random.normal(0, self.read_noise_sigma, frame.shape)
        
        noisy = frame + shot_noise + read_noise
        return np.clip(noisy, 0, 255).astype(np.uint8)


class LatencyQueue:
    """Simulates cumulative closed-loop transport, computation, and mechanical delay."""
    def __init__(self, latency_ms: float, dt: float):
        self.latency_ms = latency_ms
        self.delay_steps = max(0, int(round(latency_ms / (dt * 1000.0))))
        self.buffer: List[Tuple[float, float]] = []

    def push_and_pop(self, commanded_vx: float, commanded_vy: float) -> Tuple[float, float]:
        self.buffer.append((commanded_vx, commanded_vy))
        if len(self.buffer) <= self.delay_steps:
            return (0.0, 0.0) # Pipeline filling
        return self.buffer.pop(0)


# =============================================================================
# Algorithmic Building Blocks (The Baseline Ladder)
# =============================================================================

def detect_center_of_gravity(frame: np.ndarray, thresh_val: float = 40.0) -> Optional[Tuple[float, float]]:
    """Baseline 0/1: Classical global thresholding and center of mass."""
    _, bin_img = cv2.threshold(frame, thresh_val, 255, cv2.THRESH_BINARY)
    M = cv2.moments(bin_img)
    if M["m00"] > 0:
        return (M["m10"] / M["m00"], M["m01"] / M["m00"])
    return None

def detect_intensity_weighted_centroid(frame: np.ndarray, psf_sigma: float = 1.5) -> Optional[Tuple[float, float]]:
    """Baseline 2 / Phoenix-X: Morphological background removal + subpixel IWC."""
    # Top-hat morphological background suppression
    kernel_size = int(round(4 * psf_sigma)) | 1 # Odd kernel
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    tophat = cv2.morphologyEx(frame, cv2.MORPH_TOPHAT, kernel)
    
    min_val, max_val, _, max_loc = cv2.minMaxLoc(tophat)
    if max_val < 10.0:
        return None
        
    px, py = max_loc
    r = int(math.ceil(2.5 * psf_sigma))
    h, w = frame.shape
    y1, y2 = max(0, py - r), min(h, py + r + 1)
    x1, x2 = max(0, px - r), min(w, px + r + 1)
    patch = tophat[y1:y2, x1:x2].astype(np.float32)
    tot = np.sum(patch)
    if tot <= 0:
        return (float(px), float(py))
        
    gy, gx = np.ogrid[y1:y2, x1:x2]
    sub_x = float(np.sum(gx * patch) / tot)
    sub_y = float(np.sum(gy * patch) / tot)
    return (sub_x, sub_y)


class KalmanEstimator:
    """State estimator with support for normal filtering and forward latency compensation."""
    def __init__(self, dt: float, q_var: float = 10.0, r_var: float = 0.5):
        self.dt = dt
        self.state = np.zeros((4, 1)) # [x, y, vx, vy]^T
        self.cov = np.eye(4) * 50.0
        self.Q = np.diag([0.2, 0.2, q_var, q_var])
        self.R = np.diag([r_var, r_var])
        self.is_initialized = False

    def update(self, measurement: Optional[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        """Runs standard Kalman predict + update. Returns (x, y, vx, vy)."""
        dt = self.dt
        F = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]])
        H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])

        if measurement is None:
            if self.is_initialized:
                self.state = F @ self.state
                self.cov = F @ self.cov @ F.T + self.Q
            return (float(self.state[0, 0]), float(self.state[1, 0]),
                    float(self.state[2, 0]), float(self.state[3, 0]))

        mx, my = measurement
        meas = np.array([[mx], [my]])
        if not self.is_initialized:
            self.state = np.array([[mx], [my], [0.0], [0.0]])
            self.is_initialized = True
        else:
            # Predict
            self.state = F @ self.state
            self.cov = F @ self.cov @ F.T + self.Q
            # Update
            y_res = meas - H @ self.state
            S = H @ self.cov @ H.T + self.R
            K = self.cov @ H.T @ np.linalg.inv(S)
            self.state = self.state + K @ y_res
            self.cov = (np.eye(4) - K @ H) @ self.cov

        return (float(self.state[0, 0]), float(self.state[1, 0]),
                float(self.state[2, 0]), float(self.state[3, 0]))

    def predict_forward(self, latency_s: float) -> Tuple[float, float]:
        """
        HYPOTHESIS H1: Forward state projection compensating for cumulative loop latency.
        x(t + tau) = x(t) + vx * tau
        y(t + tau) = y(t) + vy * tau
        """
        pred_x = float(self.state[0, 0] + self.state[2, 0] * latency_s)
        pred_y = float(self.state[1, 0] + self.state[3, 0] * latency_s)
        return (pred_x, pred_y)

    def get_position_covariance_ellipse(self) -> Tuple[float, float, float]:
        """
        HYPOTHESIS H2: Extracts semi-major axis (a), semi-minor axis (b), and orientation angle (theta)
        from the 2x2 position error covariance submatrix.
        """
        P_pos = self.cov[0:2, 0:2]
        eigvals, eigvecs = np.linalg.eigh(P_pos)
        # Sort descending
        idx = np.argsort(eigvals)[::-1]
        eigvals = eigvals[idx]
        eigvecs = eigvecs[:, idx]

        # 2-sigma confidence envelope
        semi_major = 2.0 * math.sqrt(max(1.0, eigvals[0]))
        semi_minor = 2.0 * math.sqrt(max(1.0, eigvals[1]))
        angle = math.atan2(eigvecs[1, 0], eigvecs[0, 0])
        return (semi_major, semi_minor, angle)


class RateLimitedPTZ:
    """Enforces mechanical angular velocity limits (e.g. 5.0 deg/s default)."""
    def __init__(self, max_slew_deg_s: float = 5.0, deg_per_pixel: float = 0.00625):
        self.pan_x = 0.0
        self.tilt_y = 0.0
        self.max_slew_px_s = max_slew_deg_s / deg_per_pixel

    def update(self, cmd_vx: float, cmd_vy: float, dt: float):
        speed = math.hypot(cmd_vx, cmd_vy)
        if speed > self.max_slew_px_s:
            scale = self.max_slew_px_s / speed
            cmd_vx *= scale
            cmd_vy *= scale
        self.pan_x += cmd_vx * dt
        self.tilt_y += cmd_vy * dt
