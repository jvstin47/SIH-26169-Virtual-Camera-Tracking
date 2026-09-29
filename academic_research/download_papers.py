#!/usr/bin/env python3
"""
Paper Downloader for Project Phoenix-X Academic Defense
Downloads open-access PDFs and arXiv preprints for verified research citations.
"""

import os
import urllib.request
import ssl

PAPERS = [
    {
        "filename": "2024_CVPR_Turb_Seg_Res.pdf",
        "url": "https://arxiv.org/pdf/2404.13605.pdf",
        "title": "Turb-Seg-Res: A Segment-then-Restore Pipeline for Dynamic Videos with Atmospheric Turbulence (CVPR 2024)"
    },
    {
        "filename": "2024_ECCV_Moving_Object_Turbulence.pdf",
        "url": "https://arxiv.org/pdf/2311.03572.pdf",
        "title": "Unsupervised Moving Object Segmentation with Atmospheric Turbulence (ECCV 2024)"
    },
    {
        "filename": "2024_MDPI_FSOC_Mobile_Platforms.pdf",
        "url": "https://www.mdpi.com/2304-6732/11/10/900/pdf",
        "title": "High-Precision Tracking of Free-Space Optical Communication System on Mobile Platforms (Photonics 2024)"
    },
    {
        "filename": "2023_MDPI_Centroid_Extraction_Laser_Spots.pdf",
        "url": "https://www.mdpi.com/2072-4292/15/8/2129/pdf",
        "title": "Centroid Extraction of Laser Spots Captured by Infrared Detectors (Remote Sensing 2023)"
    },
    {
        "filename": "2024_MDPI_Closed_Loop_Steering_Mirror.pdf",
        "url": "https://www.mdpi.com/2226-4310/11/4/330/pdf",
        "title": "Steering Mirror System with Closed-Loop Feedback for FSOC Terminals (Aerospace 2024)"
    }
]

def main():
    dest_dir = os.path.join(os.path.dirname(__file__), "papers")
    os.makedirs(dest_dir, exist_ok=True)
    
    # Custom headers to bypass simple bot blocks
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    ctx = ssl.create_default_context()
    
    print(f"[*] Downloading verified academic papers to: {dest_dir}\n")
    for paper in PAPERS:
        dest_path = os.path.join(dest_dir, paper["filename"])
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
            print(f"[+] Already downloaded: {paper['filename']}")
            continue
            
        print(f"[-] Fetching: {paper['title']}...")
        try:
            req = urllib.request.Request(paper["url"], headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=30) as response, open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
            size_kb = os.path.getsize(dest_path) / 1024
            print(f"    --> Saved: {paper['filename']} ({size_kb:.1f} KB)")
        except Exception as e:
            print(f"    [!] Failed to download from {paper['url']}: {e}")
            
    print("\n[+] Download process completed.")

if __name__ == "__main__":
    main()
