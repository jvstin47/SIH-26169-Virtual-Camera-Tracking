#!/usr/bin/env python3
"""
Node C: Active Atmospheric Channel & Turbulence Emulator (Terminal 2 of 3)
Problem Statement ID: SIH 26169 (ISRO / SAC)

Acts as a real-time Physical Channel Man-in-the-Middle (MitM) Node.
Ingests clean/nominal satellite feed from Node A (UDP port 9999),
injects severe non-linear atmospheric optical phenomena:
  1. Kolmogorov Wavefront Turbulence & Heat Shimmer (cv2.remap)
  2. Dense Cloud Obscuration & Beer-Lambert Fog Attenuation
  3. Impulsive Solar Radiation & Cosmic Noise (10% - 25% S&P)
  4. Gamma-Gamma Scintillation Fading (Deep optical power dropouts)
  5. Optical Beam Jitter & Solar Glare Flashes
Transmits the degraded channel feed to Node B (UDP port 9997).
"""

import sys
import os
import time
import math
import socket
import json
import numpy as np
import cv2

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.coordinates import CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX

class AtmosphericChannelEmulator:
    def __init__(self):
        # Channel state toggles
        self.enable_turbulence = True
        self.enable_fog = False
        self.sp_noise_ratio = 0.10   # Default: ISRO 10% mandate
        self.enable_scintillation = True
        self.enable_glare = False
        self.dropout_frames = 0
        
        # Physical channel metrics
        self.cn2_turbulence_index = 5.0e-14  # Moderate-to-strong turbulence (m^-2/3)
        self.fog_optical_depth = 1.2
        self.fading_phase = 0.0

    def apply_channel_effects(self, frame: np.ndarray, t: float) -> np.ndarray:
        """Applies dynamic optical atmospheric transfer function to sensor frame."""
        h, w = frame.shape
        out = frame.astype(np.float32)

        # -------------------------------------------------------------
        # 1. Kolmogorov Wavefront Turbulence & Spatial Refractive Shimmer
        # -------------------------------------------------------------
        if self.enable_turbulence:
            # Dynamic spatio-temporal distortion field
            grid_y, grid_x = np.mgrid[0:h, 0:w].astype(np.float32)
            
            # Multi-scale phase ripple
            freq1, freq2 = 0.025, 0.04
            shimmer_amp = 3.5  # pixels displacement
            
            dx = shimmer_amp * np.sin(freq1 * grid_y + t * 4.0) + 1.5 * np.cos(freq2 * grid_x + t * 6.0)
            dy = shimmer_amp * np.cos(freq1 * grid_x + t * 3.5) + 1.5 * np.sin(freq2 * grid_y + t * 5.0)
            
            map_x = np.clip(grid_x + dx, 0, w - 1).astype(np.float32)
            map_y = np.clip(grid_y + dy, 0, h - 1).astype(np.float32)
            
            out = cv2.remap(out, map_x, map_y, interpolation=cv2.INTER_LINEAR)

        # -------------------------------------------------------------
        # 2. Scintillation (Gamma-Gamma Optical Power Fading)
        # -------------------------------------------------------------
        if self.enable_scintillation:
            # Optical intensity fluctuates according to atmospheric eddies
            fading = 0.70 + 0.30 * math.sin(t * 5.5) + 0.15 * math.sin(t * 13.2)
            fading = max(0.15, fading)
            out = out * fading

        # -------------------------------------------------------------
        # 3. Dense Cloud Obscuration & Beer-Lambert Fog
        # -------------------------------------------------------------
        if self.enable_fog:
            # High atmospheric backscatter + severe transmittance drop
            transmittance = 0.25
            skyglow = 85.0
            out = (out * transmittance) + skyglow

        # -------------------------------------------------------------
        # 4. Solar Glare / High-Intensity Sensor Flash
        # -------------------------------------------------------------
        if self.enable_glare:
            # Saturating thermal bloom in one sector of the sensor
            flare = np.zeros((h, w), dtype=np.float32)
            cv2.circle(flare, (int(w * 0.75), int(h * 0.35)), 120, 200.0, -1)
            flare = cv2.GaussianBlur(flare, (101, 101), 40)
            out = np.clip(out + flare, 0, 255)

        # -------------------------------------------------------------
        # 5. Stochastic Sensor & Impulsive Radiation Noise (10% - 25% S&P)
        # -------------------------------------------------------------
        out_uint8 = np.clip(out, 0, 255).astype(np.uint8)
        
        if self.sp_noise_ratio > 0.001:
            rnd = np.random.random((h, w))
            # Salt (255)
            out_uint8[rnd < (self.sp_noise_ratio / 2.0)] = 255
            # Pepper (0)
            out_uint8[(rnd >= (self.sp_noise_ratio / 2.0)) & (rnd < self.sp_noise_ratio)] = 0

        # -------------------------------------------------------------
        # 6. Channel Dropout / Fading Blackout (Drop packets or black frame)
        # -------------------------------------------------------------
        if self.dropout_frames > 0:
            self.dropout_frames -= 1
            out_uint8[:] = 5  # Complete link blackout

        return out_uint8

def main():
    print("=" * 75)
    print("  NODE C: ACTIVE ATMOSPHERIC CHANNEL & TURBULENCE EMULATOR (TERMINAL 2)")
    print("  Problem Statement ID: SIH 26169 (ISRO / SAC)")
    print("=" * 75)
    print("[*] Ingesting Satellite Stream from Node A (127.0.0.1:9999)...")
    print("[*] Broadcasting Corrupted Optical Channel to Node B (127.0.0.1:9997)...")
    print("\nInteractive Channel Controls:")
    print("  [1] Step Impulsive Noise: 0% -> 10% (ISRO SLA) -> 25% (Extreme Solar Storm)")
    print("  [2] Toggle Kolmogorov Optical Wavefront Turbulence / Heat Shimmer")
    print("  [3] Toggle Heavy Cloud Obscuration & Beer-Lambert Fog Attenuation")
    print("  [4] Trigger Solar Glare / Sensor Blinding Flare")
    print("  [5] Trigger Sudden Optical Channel Fading Dropout (1-second blackout)")
    print("  [Q] or [ESC] Quit Node C\n")

    # UDP Ingest from Node A
    sock_rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_rx.bind(("127.0.0.1", 9999))
    sock_rx.settimeout(1.5)

    # UDP Forward to Node B
    sock_tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    node_b_addr = ("127.0.0.1", 9997)

    channel = AtmosphericChannelEmulator()
    t_start = time.time()
    packet_count = 0

    while True:
        try:
            data, _ = sock_rx.recvfrom(65535)
        except socket.timeout:
            continue

        if data == b"STOP":
            sock_tx.sendto(b"STOP", node_b_addr)
            print("[*] Channel Emulator received STOP signal.")
            break

        packet_count += 1
        t_now = time.time() - t_start

        # Unpack Node A packet
        meta_len = int.from_bytes(data[:4], 'big')
        meta_json = data[4:4 + meta_len].decode('utf-8')
        metadata = json.loads(meta_json)
        jpg_bytes = data[4 + meta_len:]

        # Decode incoming frame from Node A
        raw_arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
        clean_frame = cv2.imdecode(raw_arr, cv2.IMREAD_GRAYSCALE)
        if clean_frame is None:
            continue

        # Inject Atmospheric Channel Degradations
        corrupted_frame = channel.apply_channel_effects(clean_frame, t_now)

        # Re-encode to JPEG
        _, enc_jpg = cv2.imencode('.jpg', corrupted_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        corrupted_bytes = enc_jpg.tobytes()

        # Update metadata with channel statistics
        metadata["channel_node"] = "ACTIVE_ATMOSPHERE_EMULATOR"
        metadata["sp_noise_ratio"] = float(channel.sp_noise_ratio)
        metadata["turbulence_active"] = bool(channel.enable_turbulence)
        metadata["fog_active"] = bool(channel.enable_fog)
        metadata["glare_active"] = bool(channel.enable_glare)
        metadata["scintillation_active"] = bool(channel.enable_scintillation)

        new_meta_json = json.dumps(metadata).encode('utf-8')
        fwd_packet = len(new_meta_json).to_bytes(4, 'big') + new_meta_json + corrupted_bytes

        if len(fwd_packet) < 65000:
            try:
                sock_tx.sendto(fwd_packet, node_b_addr)
            except Exception:
                pass

        # -------------------------------------------------------------
        # Channel Monitor HUD (Terminal 2 Display)
        # -------------------------------------------------------------
        hud = cv2.cvtColor(corrupted_frame, cv2.COLOR_GRAY2BGR)
        
        # Header banner
        cv2.rectangle(hud, (0, 0), (CAMERA_WIDTH_PX, 65), (15, 20, 28), -1)
        cv2.line(hud, (0, 65), (CAMERA_WIDTH_PX, 65), (0, 165, 255), 1)
        
        cv2.putText(hud, "NODE C: ATMOSPHERIC CHANNEL & TURBULENCE EMULATOR", (15, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 215, 255), 1, cv2.LINE_AA)
        
        # Telemetry metrics
        status_turb = "ACTIVE (Kolmogorov)" if channel.enable_turbulence else "BYPASS"
        status_noise = f"{int(channel.sp_noise_ratio * 100)}% S&P"
        status_fog = "DENSE FOG (Beer-Lambert)" if channel.enable_fog else "CLEAR SKY"
        
        cv2.putText(hud, f"WAVEFRONT: {status_turb} | IMPULSIVE NOISE: {status_noise}", (15, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 210, 220), 1, cv2.LINE_AA)
        cv2.putText(hud, f"ATMOSPHERE: {status_fog} | SCINTILLATION: {'ON' if channel.enable_scintillation else 'OFF'}", (15, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 210, 220), 1, cv2.LINE_AA)

        # Hotkey legend at bottom
        cv2.rectangle(hud, (0, CAMERA_HEIGHT_PX - 26), (CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX), (15, 20, 28), -1)
        cv2.putText(hud, "[1] Noise  [2] Turbulence  [3] Fog  [4] Solar Glare  [5] Blackout  [Q] Quit",
                    (15, CAMERA_HEIGHT_PX - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 180, 255), 1, cv2.LINE_AA)

        cv2.imshow("Node C: Physical Atmospheric Channel & Turbulence (Terminal 2)", hud)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == 27:
            break
        elif key == ord('1'):
            if channel.sp_noise_ratio == 0.0:
                channel.sp_noise_ratio = 0.10
            elif channel.sp_noise_ratio == 0.10:
                channel.sp_noise_ratio = 0.25
            else:
                channel.sp_noise_ratio = 0.0
            print(f"[*] Node C: Impulsive Noise set to {int(channel.sp_noise_ratio * 100)}%")
        elif key == ord('2'):
            channel.enable_turbulence = not channel.enable_turbulence
            print(f"[*] Node C: Kolmogorov Wavefront Turbulence -> {'ENABLED' if channel.enable_turbulence else 'DISABLED'}")
        elif key == ord('3'):
            channel.enable_fog = not channel.enable_fog
            print(f"[*] Node C: Cloud Obscuration & Fog -> {'ENABLED' if channel.enable_fog else 'DISABLED'}")
        elif key == ord('4'):
            channel.enable_glare = not channel.enable_glare
            print(f"[*] Node C: Solar Glare Flare -> {'ENABLED' if channel.enable_glare else 'DISABLED'}")
        elif key == ord('5'):
            channel.dropout_frames = 30  # 1 second blackout at 30 fps
            print("[!] Node C: Triggered Optical Channel Fading Dropout (1s)")

    sock_rx.close()
    sock_tx.close()
    cv2.destroyAllWindows()
    print("[+] Node C stopped.")

if __name__ == "__main__":
    main()
