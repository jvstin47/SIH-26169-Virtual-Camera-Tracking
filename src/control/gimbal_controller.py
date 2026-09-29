"""
Predictive Gimbal Servo Controller with Kalman State Estimation
Calculates velocity commands for virtual PTZ gimbal with Anti-Windup PID
and Feedforward velocity compensation.
"""

import math
import numpy as np
from src.core.coordinates import Point2D, CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX

class GimbalController:
    def __init__(self, kp: float = 6.5, ki: float = 1.4, kd: float = 0.6):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.prev_error_x = 0.0
        self.prev_error_y = 0.0
        
        # Simple Linear Kalman Filter for target tracking & velocity estimation
        # State vector: [x, y, vx, vy]^T
        self.kf_state = np.zeros((4, 1))
        self.kf_cov = np.eye(4) * 100.0
        
        # Process Noise & Measurement Noise Covariances
        self.Q = np.diag([1.0, 1.0, 20.0, 20.0])
        self.R = np.diag([0.2, 0.2])  # High confidence in sub-pixel centroid
        self.is_initialized = False

    def reset(self):
        self.integral_x = 0.0
        self.integral_y = 0.0
        self.prev_error_x = 0.0
        self.prev_error_y = 0.0
        self.is_initialized = False

    def update(self, detected_pos: Point2D, dt: float) -> tuple:
        """
        Takes detected beacon position in local camera viewport (0..640, 0..480),
        computes commanded velocity (vx_px_s, vy_px_s) to drive spot to center (320, 240).
        """
        center_x = CAMERA_WIDTH_PX / 2.0
        center_y = CAMERA_HEIGHT_PX / 2.0
        
        if detected_pos is None:
            # Coast on Kalman state prediction if beacon is temporarily lost
            if self.is_initialized:
                F = np.array([
                    [1, 0, dt, 0],
                    [0, 1, 0, dt],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]
                ])
                self.kf_state = F @ self.kf_state
                est_vx = float(self.kf_state[2, 0])
                est_vy = float(self.kf_state[3, 0])
                return (est_vx, est_vy)
            return (0.0, 0.0)

        # Kalman Filter Step
        meas = np.array([[detected_pos.x], [detected_pos.y]])
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])

        if not self.is_initialized:
            self.kf_state = np.array([[detected_pos.x], [detected_pos.y], [0.0], [0.0]])
            self.is_initialized = True
        else:
            # Predict
            self.kf_state = F @ self.kf_state
            self.kf_cov = F @ self.kf_cov @ F.T + self.Q
            # Update
            y_res = meas - H @ self.kf_state
            S = H @ self.kf_cov @ H.T + self.R
            K = self.kf_cov @ H.T @ np.linalg.inv(S)
            self.kf_state = self.kf_state + K @ y_res
            self.kf_cov = (np.eye(4) - K @ H) @ self.kf_cov

        filtered_x = float(self.kf_state[0, 0])
        filtered_y = float(self.kf_state[1, 0])
        est_vx = float(self.kf_state[2, 0])
        est_vy = float(self.kf_state[3, 0])

        # Error is displacement from optical bore-sight (320, 240)
        error_x = filtered_x - center_x
        error_y = filtered_y - center_y

        # Anti-windup integration
        self.integral_x += error_x * dt
        self.integral_y += error_y * dt
        self.integral_x = np.clip(self.integral_x, -100.0, 100.0)
        self.integral_y = np.clip(self.integral_y, -100.0, 100.0)

        # Derivative
        deriv_x = (error_x - self.prev_error_x) / max(1e-4, dt)
        deriv_y = (error_y - self.prev_error_y) / max(1e-4, dt)
        self.prev_error_x = error_x
        self.prev_error_y = error_y

        # PID + Feedforward command
        # Moving camera in direction of error reduces error
        cmd_vx = (self.kp * error_x) + (self.ki * self.integral_x) + (self.kd * deriv_x) + est_vx
        cmd_vy = (self.kp * error_y) + (self.ki * self.integral_y) + (self.kd * deriv_y) + est_vy

        return (cmd_vx, cmd_vy)
