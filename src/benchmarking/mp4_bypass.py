"""
ISRO Benchmark-2 Video Ingestion & External Target Tracking Module
Problem Statement ID: SIH 26169 (ISRO / SAC)

Ingests external .mp4 video files @ 30 FPS, bypassing the virtual PTZ camera.
Supports:
1. Autonomous Laser Beacon Detection & Sub-Pixel Centroiding
2. Interactive ROI Selection (click & drag to track ANY moving target in an arbitrary video)
3. Automated CSV Performance Log & RMSE Audit Generation
"""

import os
import time
import math
import csv
import numpy as np
import cv2
from typing import Optional

from src.core.coordinates import Point2D, CAMERA_WIDTH_PX, CAMERA_HEIGHT_PX
from src.vision.tracker import BeaconTracker

class VideoBenchmarkRunner:
    def __init__(self, video_path: str, select_roi: bool = False, ground_truth_path: Optional[str] = None, headless: bool = False):
        self.video_path = video_path
        self.select_roi = select_roi
        self.ground_truth_path = ground_truth_path
        self.headless = headless
        
        self.tracker = BeaconTracker()
        self.opencv_tracker = None
        self.roi = None
        
        self.frame_records = []
        self.ground_truth = []
        
        if self.ground_truth_path and os.path.exists(self.ground_truth_path):
            self._load_ground_truth()

    def _load_ground_truth(self):
        """Loads ground truth coordinates (x, y) per frame if provided."""
        try:
            with open(self.ground_truth_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        try:
                            self.ground_truth.append((float(row[0]), float(row[1])))
                        except ValueError:
                            continue
            print(f"[+] Loaded {len(self.ground_truth)} ground truth positions.")
        except Exception as e:
            print(f"[!] Warning: Could not load ground truth file: {e}")

    def run(self):
        if not os.path.exists(self.video_path):
            print(f"[!] Error: Video file not found: {self.video_path}")
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"[!] Error: Failed to open video: {self.video_path}")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps_video = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print("\n" + "=" * 70)
        print("  PHOENIX-X: ISRO BENCHMARK-2 EXTERNAL VIDEO TRACKER")
        print("=" * 70)
        print(f"[*] Ingesting Video: {os.path.basename(self.video_path)}")
        print(f"    Resolution    : {width} x {height}")
        print(f"    Native FPS    : {fps_video:.1f}")
        print(f"    Total Frames  : {total_frames}")
        print(f"    Tracking Mode : {'Interactive ROI Selection' if self.select_roi else 'Autonomous Optical Beacon'}\n")

        ret, first_frame = cap.read()
        if not ret:
            print("[!] Error: Could not read first frame.")
            return

        # Interactive Target Selection Mode (if requested)
        if self.select_roi:
            print("[*] Please drag a bounding box around the target on the screen, then press SPACE or ENTER.")
            self.roi = cv2.selectROI("Phoenix-X: Select Target to Track", first_frame, fromCenter=False, showCrosshair=True)
            cv2.destroyWindow("Phoenix-X: Select Target to Track")
            
            if self.roi[2] > 0 and self.roi[3] > 0:
                # Initialize OpenCV high-accuracy CSRT tracker
                self.opencv_tracker = cv2.TrackerCSRT_create()
                self.opencv_tracker.init(first_frame, self.roi)
                print(f"[+] Tracker initialized on selected ROI: {self.roi}")
            else:
                print("[!] No ROI selected. Defaulting to autonomous beacon detection.")
                self.select_roi = False

        frame_idx = 0
        start_time = time.time()
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Rewind

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            t_frame = time.time()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

            detected_x = 0.0
            detected_y = 0.0
            lock_success = False

            # Branch A: Interactive Generic Object Tracking
            if self.select_roi and self.opencv_tracker:
                success, box = self.opencv_tracker.update(frame)
                if success:
                    x, y, w, h = [int(v) for v in box]
                    detected_x = x + w / 2.0
                    detected_y = y + h / 2.0
                    lock_success = True
                    
                    # Draw green bounding box & centroid cross
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 230, 115), 2)
                    cv2.drawMarker(frame, (int(detected_x), int(detected_y)), (0, 255, 255), cv2.MARKER_CROSS, 14, 2)
                    cv2.putText(frame, "TARGET LOCKED", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 115), 1)

            # Branch B: Autonomous Laser Beacon / Optical Centroiding
            else:
                pt, err_px, snr = self.tracker.process_frame(gray)
                if pt:
                    detected_x = pt.x
                    detected_y = pt.y
                    lock_success = True
                    
                    # Draw reticle
                    dx, dy = int(round(pt.x)), int(round(pt.y))
                    cv2.rectangle(frame, (dx - 12, dy - 12), (dx + 12, dy + 12), (0, 230, 115), 2)
                    cv2.circle(frame, (dx, dy), 2, (0, 255, 255), -1)
                    cv2.putText(frame, f"BEACON ({detected_x:.1f}, {detected_y:.1f})", (dx + 15, dy - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 230, 115), 1)

            # Ground truth comparison (if available)
            error_gt = 0.0
            if frame_idx <= len(self.ground_truth):
                gt_x, gt_y = self.ground_truth[frame_idx - 1]
                if lock_success:
                    error_gt = math.hypot(detected_x - gt_x, detected_y - gt_y)
                cv2.circle(frame, (int(gt_x), int(gt_y)), 5, (0, 0, 255), 1) # Red GT circle

            self.frame_records.append({
                "frame": frame_idx,
                "timestamp_s": frame_idx / fps_video,
                "detected_x": detected_x if lock_success else None,
                "detected_y": detected_y if lock_success else None,
                "locked": lock_success,
                "gt_error_px": error_gt if self.ground_truth else None
            })

            # Live HUD Overlay
            elapsed = time.time() - start_time
            current_fps = frame_idx / max(0.001, elapsed)
            
            cv2.rectangle(frame, (10, 10), (320, 95), (20, 24, 30), -1)
            cv2.rectangle(frame, (10, 10), (320, 95), (60, 70, 85), 1)
            
            cv2.putText(frame, f"PHOENIX-X BENCHMARK-2 EVALUATOR", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 200, 255), 1)
            cv2.putText(frame, f"FRAME: {frame_idx}/{total_frames} | {current_fps:.1f} FPS", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 220, 220), 1)
            
            status_txt = "LOCK: RETAINED" if lock_success else "SEARCHING..."
            status_col = (0, 230, 115) if lock_success else (0, 165, 255)
            cv2.putText(frame, status_txt, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.42, status_col, 1)
            
            if self.ground_truth:
                cv2.putText(frame, f"RMSE vs GT: {error_gt:.2f} px", (20, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 255), 1)

            if not self.headless:
                cv2.imshow("Phoenix-X: Benchmark-2 Video Evaluation", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("[*] Evaluation stopped by user.")
                    break

        cap.release()
        if not self.headless:
            cv2.destroyAllWindows()
        self._export_benchmark_audit()

    def _export_benchmark_audit(self):
        """Exports timestamped ISRO Benchmark-2 audit CSV."""
        os.makedirs("output_reports", exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_path = f"output_reports/isro_benchmark2_audit_{timestamp}.csv"

        locked_count = sum(1 for r in self.frame_records if r["locked"])
        lock_rate = (locked_count / max(1, len(self.frame_records))) * 100.0
        
        gt_errors = [r["gt_error_px"] for r in self.frame_records if r["gt_error_px"] is not None]
        rmse = math.sqrt(sum(e**2 for e in gt_errors) / len(gt_errors)) if gt_errors else None

        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["--- ISRO BENCHMARK-2 VIDEO TRACKING AUDIT REPORT ---"])
            writer.writerow(["Video Source", self.video_path])
            writer.writerow(["Total Frames Processed", len(self.frame_records)])
            writer.writerow(["Lock Retention Rate", f"{lock_rate:.2f}%"])
            if rmse is not None:
                writer.writerow(["RMSE vs Ground Truth", f"{rmse:.3f} px"])
                writer.writerow(["ISRO SLA Status", "PASSED (<= 10.0 px)" if rmse <= 10.0 else "REVIEW"])
            writer.writerow([])
            writer.writerow(["Frame_ID", "Timestamp_s", "Detected_X", "Detected_Y", "Lock_Status", "GT_Error_px"])
            for r in self.frame_records:
                writer.writerow([
                    r["frame"],
                    f"{r['timestamp_s']:.3f}",
                    f"{r['detected_x']:.2f}" if r["detected_x"] is not None else "N/A",
                    f"{r['detected_y']:.2f}" if r["detected_y"] is not None else "N/A",
                    "LOCKED" if r["locked"] else "LOST",
                    f"{r['gt_error_px']:.3f}" if r["gt_error_px"] is not None else "N/A"
                ])

        print("\n" + "=" * 70)
        print(f"[+] Benchmark-2 Evaluation Complete!")
        print(f"    Lock Retention Rate : {lock_rate:.2f}%")
        if rmse is not None:
            print(f"    RMSE Centroid Error : {rmse:.3f} px (ISRO Mandate: <= 10.0 px)")
        print(f"    Saved Audit Report  : {csv_path}")
        print("=" * 70 + "\n")
