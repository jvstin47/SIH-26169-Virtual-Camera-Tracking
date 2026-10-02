"""
Phoenix-X Core Mathematical Primitives and Physical Constants
Converts between Pixel Coordinates, Physical Angles (degrees, arcseconds, radians),
and Gimbal Azimuth/Elevation angles for Mobile FSOC terminals.
"""

import math
from dataclasses import dataclass
from typing import Tuple

# Optical & Actuation Constants from ISRO SAC Problem Statement 26169
UNIVERSE_WIDTH_PX = 2000
UNIVERSE_HEIGHT_PX = 2000
CAMERA_WIDTH_PX = 640
CAMERA_HEIGHT_PX = 480

FOV_AZ_DEG = 4.0   # 4 degrees azimuth
FOV_EL_DEG = 3.0   # 3 degrees elevation

# Angular resolution per pixel
# 4 degrees / 640 pixels = 0.00625 deg/px = 22.5 arcseconds/px = 109.083 microradians/px
DEG_PER_PIXEL = FOV_AZ_DEG / CAMERA_WIDTH_PX
ARCSEC_PER_PIXEL = DEG_PER_PIXEL * 3600.0
RAD_PER_PIXEL = math.radians(DEG_PER_PIXEL)
URAD_PER_PIXEL = RAD_PER_PIXEL * 1e6

def pixels_to_arcsec(px: float) -> float:
    return px * ARCSEC_PER_PIXEL

def arcsec_to_pixels(arcsec: float) -> float:
    return arcsec / ARCSEC_PER_PIXEL

def pixels_to_urad(px: float) -> float:
    return px * URAD_PER_PIXEL

def urad_to_pixels(urad: float) -> float:
    return urad / URAD_PER_PIXEL

# Gimbal Constraints
DEFAULT_MAX_SLEW_RATE_DEG_S = 5.0   # 5 degrees / second default
MAX_SLEW_RATE_PX_S = DEFAULT_MAX_SLEW_RATE_DEG_S / DEG_PER_PIXEL  # 800 px / second

@dataclass
class Point2D:
    x: float
    y: float

@dataclass
class TelemetryFrame:
    frame_id: int
    timestamp_s: float
    true_target: Point2D       # Global coordinates
    estimated_target: Point2D  # Global coordinates
    camera_pos: Point2D        # Global coordinates (center of viewport)
    centroid_error_px: float   # Distance between true and estimated/viewport center
    centroid_error_arcsec: float
    slew_rate_deg_s: float
    fps: float
    locked: bool
    snr_db: float
    s_and_p_noise: bool
    poisson_noise: bool
    fog_active: bool
    jitter_active: bool
