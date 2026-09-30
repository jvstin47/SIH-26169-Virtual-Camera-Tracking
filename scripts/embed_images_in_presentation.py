#!/usr/bin/env python3
"""
Phoenix-X Master Slide Visual & Content Finalizer
Problem Statement ID: SIH 26169 (ISRO / SAC)

Transforms Phoenix_X_SIH26169_Improved.pptx into a flawless, publication-grade deck:
1. Slide 1: Embeds Hero Satellite-to-Ground Optical Laser Link (16:9)
2. Slide 2: Preserves pristine 3-column Problem vs Solution vs Architecture layout (zero overlap)
3. Slide 3: Embeds 3-Node Distributed Architecture Diagram + compact clean Tech Stack table
4. Slide 4: Embeds 4-Quadrant Optical Disturbance Scientific Panel (Noise/Fog Proof) + compact Challenge 5 text
5. Slide 5: Preserves pristine 4-sector impact matrix + 5-step measurable pipeline
6. Slide 6: Replaces redundant subsystem bullets with real Tactical Cockpit Simulator screenshot (undeniable proof)
"""

import os
import shutil
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

BASE_PPTX = "Phoenix_X_SIH26169_Improved.pptx"
FINAL_PPTX = "Phoenix_X_SIH26169_Final.pptx"
IMG_DIR = "submission_images"

def finalize_deck():
    # Start fresh from the clean improved deck
    prs = pptx.Presentation(BASE_PPTX)

    # =========================================================================
    # SLIDE 1: Title Slide with Hero Space Laser Link
    # =========================================================================
    slide1 = prs.slides[0]
    img1 = os.path.join(IMG_DIR, "01_satellite_ground_laser_link.jpg")
    if os.path.exists(img1):
        # Remove old placeholder picture 4 if present
        for s in list(slide1.shapes):
            if s.name == "Picture 4":
                sp = s._element
                sp.getparent().remove(sp)
                
        # Add Hero Laser Link Render
        slide1.shapes.add_picture(
            img1,
            left=Inches(8.85),
            top=Inches(1.30),
            width=Inches(3.95),
            height=Inches(2.45)
        )
        print("[+] Slide 1: Hero laser link image embedded.")

    # =========================================================================
    # SLIDE 3: Technical Approach (3-Node Architecture + Clean Tech Stack)
    # =========================================================================
    slide3 = prs.slides[2]
    img5 = os.path.join(IMG_DIR, "05_distributed_3node_architecture.png")
    if os.path.exists(img5):
        # Remove old picture if exists
        for s in list(slide3.shapes):
            if s.name == "Picture 17478" or (hasattr(s, 'image') and "05_distributed" in str(getattr(s, 'name', ''))):
                sp = s._element
                sp.getparent().remove(sp)

        # Remove all old tech stack shapes and connectors in the right card (left >= 6.7)
        shapes_to_remove = []
        for s in slide3.shapes:
            if s.left.inches >= 6.7 and s.top.inches >= 1.95:
                shapes_to_remove.append(s)

        for s in shapes_to_remove:
            sp = s._element
            sp.getparent().remove(sp)

        # Place 3-Node Architecture Diagram at top of right column
        # Aspect ratio of 05_distributed_3node_architecture.png is ~1200x570 (approx 2.1:1)
        slide3.shapes.add_picture(
            img5,
            left=Inches(6.90),
            top=Inches(2.00),
            width=Inches(5.68),
            height=Inches(2.50)
        )
        
        # Add 4 cleanly spaced tech stack rows below the architecture diagram
        tech_rows = [
            ("IMM Kinematics", "Dual-mode Kalman filter combining CV and CT models to eliminate lag"),
            ("Servo Control Loop", "Feedforward predictive anti-windup PID (strict 5-10°/s slew clamping)"),
            ("Tactical Cockpit GUI", "OpenCV Tactical HUD & Live Web Radar (HTTP 8080) with manual PTZ override"),
            ("Compliance & CI", "Automated CSV/PDF Benchmark-2 audit engine logging RMSE & lock retention")
        ]
        
        y_starts = [4.65, 5.20, 5.75, 6.30]
        for idx, (label, desc) in enumerate(tech_rows):
            y = Inches(y_starts[idx])
            # Category label
            tb_lbl = slide3.shapes.add_textbox(Inches(6.90), y, Inches(1.70), Inches(0.40))
            tf_lbl = tb_lbl.text_frame
            tf_lbl.word_wrap = True
            p_lbl = tf_lbl.paragraphs[0]
            p_lbl.text = label
            p_lbl.font.size = Pt(8.5)
            p_lbl.font.bold = True
            p_lbl.font.color.rgb = RGBColor(15, 34, 64)
            
            # Description
            tb_desc = slide3.shapes.add_textbox(Inches(8.65), y, Inches(3.93), Inches(0.45))
            tf_desc = tb_desc.text_frame
            tf_desc.word_wrap = True
            p_desc = tf_desc.paragraphs[0]
            p_desc.text = desc
            p_desc.font.size = Pt(8.0)
            p_desc.font.color.rgb = RGBColor(60, 60, 60)
            
            # Separator line above row (except first)
            if idx > 0:
                slide3.shapes.add_connector(
                    pptx.enum.shapes.MSO_CONNECTOR.STRAIGHT,
                    Inches(6.90), y - Inches(0.06),
                    Inches(12.58), y - Inches(0.06)
                )

        print("[+] Slide 3: 3-Node Architecture diagram and tech stack integrated cleanly.")

    # =========================================================================
    # SLIDE 4: Feasibility & Disturbance Rejection Panel
    # =========================================================================
    slide4 = prs.slides[3]
    img4 = os.path.join(IMG_DIR, "04_optical_disturbances_comparison.png")
    if os.path.exists(img4):
        # Embed 4-quadrant disturbance panel in middle column below Air-Gapped card
        for s in list(slide4.shapes):
            if s.has_text_frame and "SPACE AVIONICS ROADMAP" in s.text_frame.text:
                s.text_frame.text = "OPTICAL CHANNEL VALIDATION"
                for p in s.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(9.0)
                        r.font.bold = True
            elif s.has_text_frame and "Algorithmic Flight Readiness" in s.text_frame.text:
                sp = s._element
                sp.getparent().remove(sp)

        # Add 4-quadrant image
        slide4.shapes.add_picture(
            img4,
            left=Inches(4.85),
            top=Inches(4.55),
            width=Inches(3.55),
            height=Inches(2.20)
        )

        # Compact Challenge 5 text to fit perfectly inside the card
        for s in slide4.shapes:
            if s.has_text_frame:
                for p in s.text_frame.paragraphs:
                    if "GUI Paint Lag Bottleneck" in p.text:
                        p.text = "Multi-Terminal Network Latency"
                        for r in p.runs:
                            r.font.size = Pt(9.0)
                    elif "Double-buffered QThread" in p.text:
                        p.text = "→ Non-blocking UDP with 8KB MTU fragmentation decouples 30 Hz edge vision from 60 Hz web cockpit with zero packet lag."
                        for r in p.runs:
                            r.font.size = Pt(8.0)

        print("[+] Slide 4: Optical disturbance comparison panel embedded & Challenge 5 fitted.")

    # =========================================================================
    # SLIDE 6: Research, References & Working Prototype Proof
    # =========================================================================
    slide6 = prs.slides[5]
    img3 = os.path.join(IMG_DIR, "03_tactical_dual_viewport_cockpit.png")
    if os.path.exists(img3):
        # Remove all shapes in the lower half of the right column (top >= 4.15 and left >= 8.35)
        # to ensure zero leftover bullet icons, text, or old pictures
        shapes_to_remove = []
        for s in slide6.shapes:
            if s.left.inches >= 8.35 and s.top.inches >= 4.15:
                shapes_to_remove.append(s)

        for s in shapes_to_remove:
            sp = s._element
            sp.getparent().remove(sp)

        # Update Documented Engineering Deliverables text to be concise (items 1 & 2 only)
        for s in slide6.shapes:
            if s.has_text_frame and "docs/system_architecture_plan.md" in s.text_frame.text:
                s.text_frame.clear()
                s.text_frame.word_wrap = True
                p1 = s.text_frame.paragraphs[0]
                p1.text = "1. docs/system_architecture_plan.md (System Blueprint)"
                p1.font.size = Pt(8.0)
                p1.font.color.rgb = RGBColor(60, 60, 60)
                
                p2 = s.text_frame.add_paragraph()
                p2.text = "2. academic_research/ (Literature Review & Papers)"
                p2.font.size = Pt(8.0)
                p2.font.color.rgb = RGBColor(60, 60, 60)

                p3 = s.text_frame.add_paragraph()
                p3.text = "3. distributed_demo/ (3-Node Networked Simulation)"
                p3.font.size = Pt(8.0)
                p3.font.color.rgb = RGBColor(60, 60, 60)

        # Add heading: LIVE TACTICAL COCKPIT DELIVERABLE
        tx_box = slide6.shapes.add_textbox(Inches(8.55), Inches(4.25), Inches(3.95), Inches(0.28))
        tf = tx_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = "Operational Software Cockpit (main.py)"
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0, 115, 230)

        # Embed Tactical Cockpit Image
        slide6.shapes.add_picture(
            img3,
            left=Inches(8.55),
            top=Inches(4.55),
            width=Inches(3.95),
            height=Inches(2.25)
        )
        print("[+] Slide 6: Real Tactical Cockpit screenshot embedded cleanly.")

    prs.save(FINAL_PPTX)
    print(f"\n[+] Master presentation successfully created: {FINAL_PPTX}")

if __name__ == '__main__':
    finalize_deck()
