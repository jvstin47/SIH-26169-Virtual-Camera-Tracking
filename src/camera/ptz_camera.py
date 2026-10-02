"""
Virtual PTZ Camera Model with Physical Slew Rate Constraints
Strictly enforces physical angular rate limits (5-10 deg/s) and crops 640x480 FPA viewport.
"""

import math
import numpy as np
from src.core.coordinates import (
    Point2D, UNIVERSE_WIDTH_PX, UNIVERSE_HEIGHT_PX,
    CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX, DEG_PER_PIXEL,
    DEFAULT_MAX_SLEW_RATE_DEG_S, MAX_SLEW_RATE_PX_S
)

class VirtualPTZCamera:
    def __init__(self, initial_x: float = UNIVERSE_WIDTH_PX / 2.0, initial_y: float = UNIVERSE_HEIGHT_PX / 2.0):
        # Current camera center in global universe coordinates
        self.x = initial_x
        self.y = initial_y
        
        # Current angular velocity (deg/s)
        self.vx_deg_s = 0.0
        self.vy_deg_s = 0.0
        
        # PS-defined speed limit (5.0 deg/s default, configurable 5-10 deg/s)
        self.max_slew_rate_deg_s = DEFAULT_MAX_SLEW_RATE_DEG_S
        self.max_slew_rate_px_s = self.max_slew_rate_deg_s / DEG_PER_PIXEL

    def set_slew_limit(self, max_deg_s: float):
        self.max_slew_rate_deg_s = float(np.clip(max_deg_s, 5.0, 10.0))
        self.max_slew_rate_px_s = self.max_slew_rate_deg_s / DEG_PER_PIXEL

    def update_actuator(self, commanded_vx_px_s: float, commanded_vy_px_s: float, dt: float):
        """
        Updates camera gimbal position using rate-limited servo dynamics.
        Ensures camera never jumps instantaneously and strictly obeys slew limits.
        """
        # Convert commanded velocity to deg/s
        cmd_vx_deg_s = commanded_vx_px_s * DEG_PER_PIXEL
        cmd_vy_deg_s = commanded_vy_px_s * DEG_PER_PIXEL
        
        # Enforce PS-defined slew limit
        speed_deg_s = math.hypot(cmd_vx_deg_s, cmd_vy_deg_s)
        if speed_deg_s > self.max_slew_rate_deg_s:
            scale = self.max_slew_rate_deg_s / speed_deg_s
            cmd_vx_deg_s *= scale
            cmd_vy_deg_s *= scale
            
        self.vx_deg_s = cmd_vx_deg_s
        self.vy_deg_s = cmd_vy_deg_s
        
        # Integrate position in pixels
        dx_px = (self.vx_deg_s / DEG_PER_PIXEL) * dt
        dy_px = (self.vy_deg_s / DEG_PER_PIXEL) * dt
        
        self.x += dx_px
        self.y += dy_px
        
        # Clamp camera center to universe bounds
        half_w = CAMERA_WIDTH_PX / 2.0
        half_h = CAMERA_HEIGHT_PX / 2.0
        self.x = np.clip(self.x, half_w, UNIVERSE_WIDTH_PX - half_w)
        self.y = np.clip(self.y, half_h, UNIVERSE_HEIGHT_PX - half_h)

    def global_to_local(self, gx: float, gy: float) -> Point2D:
        """Converts global universe coordinates to active 640x480 camera viewport coordinates."""
        top_left_x = self.x - (CAMERA_WIDTH_PX / 2.0)
        top_left_y = self.y - (CAMERA_HEIGHT_PX / 2.0)
        return Point2D(gx - top_left_x, gy - top_left_y)

    def local_to_global(self, lx: float, ly: float) -> Point2D:
        """Converts camera viewport coordinates back to global universe coordinates."""
        top_left_x = self.x - (CAMERA_WIDTH_PX / 2.0)
        top_left_y = self.y - (CAMERA_HEIGHT_PX / 2.0)
        return Point2D(top_left_x + lx, top_left_y + ly)
