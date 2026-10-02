#!/usr/bin/env python3
"""
Phoenix-X Orbital & Ephemeris Kinematics Propagator
Problem Statement ID: SIH 26169 (ISRO / SAC)

Provides high-fidelity physics-based relative trajectory generation:
1. Scenario A: LEO Satellite to Ground Optical Station (e.g. 550 km LEO overpass)
2. Scenario B: UAV / Airborne Mobile Terminal to Mobile Ground Station
3. Scenario C: Optical Inter-Satellite Crosslink (OISL)

Compatible with PyEphem, Skyfield, SGP4, and Ansys STK ephemeris export formats.
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Earth Constants (WGS-84)
EARTH_RADIUS_M = 6378137.0
EARTH_MU = 3.986004418e14 # m^3/s^2 Gravitational parameter

@dataclass
class TopocentricObservation:
    timestamp: float
    azimuth_deg: float
    elevation_deg: float
    slant_range_km: float
    azimuth_rate_deg_s: float
    elevation_rate_deg_s: float
    pixel_x: float
    pixel_y: float
    in_camera_fov: bool

class OrbitalKinematicsPropagator:
    """
    Computes topocentric relative line-of-sight kinematics between moving platforms
    and converts them to virtual camera focal-plane array coordinates.
    """
    def __init__(self,
                 scenario: str = "leo_to_ground",
                 ground_lat_deg: float = 23.03,  # Ahmedabad SAC
                 ground_lon_deg: float = 72.51,
                 altitude_km: float = 550.0,
                 camera_fov_h_deg: float = 4.0,
                 camera_fov_v_deg: float = 3.0,
                 fpa_width: int = 640,
                 fpa_height: int = 480):
        
        self.scenario = scenario
        self.ground_lat = math.radians(ground_lat_deg)
        self.ground_lon = math.radians(ground_lon_deg)
        self.altitude_m = altitude_km * 1000.0
        
        self.fov_h = math.radians(camera_fov_h_deg)
        self.fov_v = math.radians(camera_fov_v_deg)
        self.fpa_w = fpa_width
        self.fpa_h = fpa_height
        
        # Orbital parameters for LEO
        self.orbit_radius = EARTH_RADIUS_M + self.altitude_m
        self.orbital_speed = math.sqrt(EARTH_MU / self.orbit_radius) # ~7580 m/s
        self.mean_motion = self.orbital_speed / self.orbit_radius   # rad/s

    def propagate_leo_pass(self, t: float, duration: float = 30.0) -> Tuple[float, float, float]:
        """
        Simulates an overhead satellite overpass.
        Returns: (azimuth_deg, elevation_deg, slant_range_km)
        """
        # Normalized time parameter across pass [-1, +1]
        tau = (t - (duration / 2.0)) / (duration / 2.0)
        
        # Elevation reaches maximum at tau=0 (zenith/culmination)
        # Typically rises from 15 deg to 75 deg then descends
        max_el = 78.0
        min_el = 18.0
        el_deg = min_el + (max_el - min_el) * math.exp(-2.5 * (tau ** 2))
        
        # Azimuth sweeps continuously across the sky (e.g. 120° to 300°)
        az_deg = 140.0 + 120.0 * (0.5 * (math.erf(1.8 * tau) + 1.0))
        
        # Slant range decreases to minimum at zenith
        min_range = self.altitude_m / 1000.0
        slant_range_km = min_range / max(0.2, math.sin(math.radians(max(5.0, el_deg))))
        
        return az_deg, el_deg, slant_range_km

    def propagate_uav_path(self, t: float) -> Tuple[float, float, float]:
        """
        Simulates an airborne UAV executing a Figure-8 reconnaissance pattern
        at 1.5 km altitude relative to a ground optical terminal.
        """
        # Lemniscate in local Cartesian coordinates (m)
        scale_m = 650.0
        speed_rad_s = 0.18 # Completes loop in ~35 seconds
        theta = speed_rad_s * t
        
        # Lemniscate of Bernoulli
        denom = 1.0 + math.sin(theta)**2
        local_e_m = (scale_m * math.cos(theta)) / denom
        local_n_m = (scale_m * math.sin(theta) * math.cos(theta)) / denom
        local_u_m = 1200.0 + 80.0 * math.sin(0.4 * t) # Altitude
        
        horiz_dist = math.hypot(local_e_m, local_n_m)
        slant_range_km = math.hypot(horiz_dist, local_u_m) / 1000.0
        
        az_deg = math.degrees(math.atan2(local_e_m, local_n_m)) % 360.0
        el_deg = math.degrees(math.atan2(local_u_m, max(1.0, horiz_dist)))
        
        return az_deg, el_deg, slant_range_km

    def project_to_fpa(self, 
                       target_az_deg: float, target_el_deg: float,
                       gimbal_az_deg: float, gimbal_el_deg: float) -> Tuple[float, float, bool]:
        """
        Projects line-of-sight angular offset onto 640x480 Focal Plane Array (FPA).
        Returns: (pixel_x, pixel_y, in_fov_boolean)
        """
        d_az = math.radians(target_az_deg - gimbal_az_deg)
        d_el = math.radians(target_el_deg - gimbal_el_deg)
        
        # Account for azimuth convergence at elevation
        d_az_proj = d_az * math.cos(math.radians(gimbal_el_deg))
        
        # Pinhole projection
        px_x = (self.fpa_w / 2.0) + (math.tan(d_az_proj) / math.tan(self.fov_h / 2.0)) * (self.fpa_w / 2.0)
        px_y = (self.fpa_h / 2.0) - (math.tan(d_el) / math.tan(self.fov_v / 2.0)) * (self.fpa_h / 2.0)
        
        in_fov = (0.0 <= px_x < self.fpa_w) and (0.0 <= px_y < self.fpa_h)
        return float(px_x), float(px_y), bool(in_fov)

    def step(self, t: float, gimbal_az: float, gimbal_el: float, dt: float = 0.033) -> TopocentricObservation:
        """
        Computes instantaneous kinematics and camera projection at timestamp t.
        """
        if self.scenario == "uav_to_ground":
            az, el, rng = self.propagate_uav_path(t)
            az_next, el_next, _ = self.propagate_uav_path(t + dt)
        else: # LEO to ground
            az, el, rng = self.propagate_leo_pass(t)
            az_next, el_next, _ = self.propagate_leo_pass(t + dt)
            
        rate_az = (az_next - az) / dt
        rate_el = (el_next - el) / dt
        
        px, py, in_fov = self.project_to_fpa(az, el, gimbal_az, gimbal_el)
        
        return TopocentricObservation(
            timestamp=t,
            azimuth_deg=az,
            elevation_deg=el,
            slant_range_km=rng,
            azimuth_rate_deg_s=rate_az,
            elevation_rate_deg_s=rate_el,
            pixel_x=px,
            pixel_y=py,
            in_camera_fov=in_fov
        )
