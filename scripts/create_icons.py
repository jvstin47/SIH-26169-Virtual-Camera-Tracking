#!/usr/bin/env python3
"""
Generates high-resolution App Icons for macOS (.icns) and Windows (.ico)
"""
import os
import cv2
import numpy as np
import subprocess

def create_app_icon():
    os.makedirs("assets", exist_ok=True)
    size = 512
    # Dark tactical background
    img = np.zeros((size, size, 4), dtype=np.uint8)
    
    # Outer rounded background / circle
    center = (size // 2, size // 2)
    radius = size // 2 - 20
    cv2.circle(img, center, radius, (20, 24, 30, 255), -1) # Dark space slate
    cv2.circle(img, center, radius, (0, 160, 255, 255), 6) # Outer cyan/orange border
    
    # Radar rings
    cv2.circle(img, center, int(radius * 0.75), (40, 50, 65, 255), 2)
    cv2.circle(img, center, int(radius * 0.50), (45, 60, 80, 255), 2)
    cv2.circle(img, center, int(radius * 0.25), (55, 75, 100, 255), 2)
    
    # Crosshairs
    cv2.line(img, (center[0] - radius, center[1]), (center[0] + radius, center[1]), (50, 70, 90, 255), 2)
    cv2.line(img, (center[0], center[1] - radius), (center[0], center[1] + radius), (50, 70, 90, 255), 2)
    
    # Central Optical Reticle (Cyan & Emerald)
    cv2.circle(img, center, 48, (0, 230, 115, 255), 4) # Lock ring
    cv2.circle(img, center, 12, (0, 215, 255, 255), -1) # Core optical spot
    cv2.circle(img, center, 4, (255, 255, 255, 255), -1) # Hot white core
    
    # Save base 512x512 PNG
    png_path = "assets/icon_512.png"
    cv2.imwrite(png_path, img)
    print(f"[+] Created {png_path}")

    # Generate macOS .iconset -> .icns
    iconset_dir = "assets/PhoenixX.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    sizes = [16, 32, 64, 128, 256, 512]
    for s in sizes:
        resized = cv2.resize(img, (s, s), interpolation=cv2.INTER_AREA)
        cv2.imwrite(f"{iconset_dir}/icon_{s}x{s}.png", resized)
        if s <= 256:
            resized_2x = cv2.resize(img, (s * 2, s * 2), interpolation=cv2.INTER_AREA)
            cv2.imwrite(f"{iconset_dir}/icon_{s}x{s}@2x.png", resized_2x)
            
    try:
        subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", "assets/PhoenixX.icns"], check=True)
        print("[+] Created macOS icon: assets/PhoenixX.icns")
    except Exception as e:
        print(f"[-] iconutil failed: {e}")

if __name__ == "__main__":
    create_app_icon()
