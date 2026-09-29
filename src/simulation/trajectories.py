"""
Trajectory Generators for Mobile FSOC Target Beacon
Implements Lemniscate (Figure-of-8), Circular, Straight Line, Sinusoidal, and Random Walk.
"""

import math
import numpy as np
from src.core.coordinates import Point2D, UNIVERSE_WIDTH_PX, UNIVERSE_HEIGHT_PX

class TrajectoryGenerator:
    def __init__(self, mode: str = "figure_8", speed: float = 1.0):
        self.mode = mode.lower()
        self.speed = speed
        self.center_x = UNIVERSE_WIDTH_PX / 2.0
        self.center_y = UNIVERSE_HEIGHT_PX / 2.0
        self.scale_a = 450.0  # Amplitude scale
        
        # State for random walk
        self.rx = self.center_x
        self.ry = self.center_y
        self.rvx = 35.0
        self.rvy = 25.0

    def set_mode(self, mode: str, current_pos: Point2D = None):
        if current_pos is not None:
            self.rx = current_pos.x
            self.ry = current_pos.y
        self.mode = mode.lower()

    def get_position(self, t: float) -> Point2D:
        """Computes true global beacon position (X, Y) at time t (seconds)."""
        omega = 0.15 * self.speed  # Angular frequency

        if self.mode == "figure_8":
            # Lemniscate starting near center and expanding
            theta = omega * t
            denom = 1.0 + math.cos(theta)**2
            # Offset slightly by 120 px to demonstrate initial acquisition and convergence
            x = self.center_x + (self.scale_a * math.sin(theta)) / denom
            y = self.center_y + (self.scale_a * math.sin(theta) * math.cos(theta)) / denom
            return Point2D(x, y)

        elif self.mode == "circular":
            theta = omega * t
            radius = self.scale_a * 0.75
            x = self.center_x + radius * math.cos(theta)
            y = self.center_y + radius * math.sin(theta)
            return Point2D(x, y)

        elif self.mode == "sinusoidal":
            theta = omega * t
            x = self.center_x + (self.scale_a * 0.8) * math.sin(theta)
            y = self.center_y + (self.scale_a * 0.4) * math.sin(2.0 * theta)
            return Point2D(x, y)

        elif self.mode == "straight_line":
            vx = 80.0 * self.speed
            vy = 45.0 * self.speed
            cycle_x = (vx * t) % (UNIVERSE_WIDTH_PX * 0.6)
            cycle_y = (vy * t) % (UNIVERSE_HEIGHT_PX * 0.6)
            x = (UNIVERSE_WIDTH_PX * 0.2) + cycle_x
            y = (UNIVERSE_HEIGHT_PX * 0.2) + cycle_y
            return Point2D(x, y)

        elif self.mode == "random":
            # Smooth Singer random walk with boundary reflection
            dt = 0.033
            self.rvx += np.random.normal(0, 15.0) * dt
            self.rvy += np.random.normal(0, 15.0) * dt
            # Velocity clamping
            self.rvx = np.clip(self.rvx, -90.0, 90.0)
            self.rvy = np.clip(self.rvy, -90.0, 90.0)
            
            self.rx += self.rvx * dt
            self.ry += self.rvy * dt
            
            # Boundary reflection
            pad = 200.0
            if self.rx < pad or self.rx > UNIVERSE_WIDTH_PX - pad:
                self.rvx *= -1.0
                self.rx = np.clip(self.rx, pad, UNIVERSE_WIDTH_PX - pad)
            if self.ry < pad or self.ry > UNIVERSE_HEIGHT_PX - pad:
                self.rvy *= -1.0
                self.ry = np.clip(self.ry, pad, UNIVERSE_HEIGHT_PX - pad)
            return Point2D(self.rx, self.ry)

        else:
            return Point2D(self.center_x, self.center_y)
