#!/usr/bin/env python3
"""
Phoenix-X PPTX Review and Polish Script
Updates terminology in Phoenix_X_SIH26169_Improved.pptx to perfectly match
our working 3-terminal distributed architecture, web cockpit, and aerospace network protocol.
Saves the finalized deck as Phoenix_X_SIH26169_Final.pptx.
"""

import pptx

def amend_presentation():
    prs = pptx.Presentation("presentation/Phoenix_X_SIH26169_Improved.pptx")
    
    # -------------------------------------------------------------
    # SLIDE 3: Technical Approach
    # -------------------------------------------------------------
    slide3 = prs.slides[2]
    for shape in slide3.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                if "PyQt6 / QPainter" in p.text:
                    p.text = "OpenCV Tactical Cockpit & Web Mission Control (Chart.js / HTTP 8080) with operator PTZ override"
                    print("[+] Slide 3: Updated Tactical Cockpit text.")

    # -------------------------------------------------------------
    # SLIDE 4: Feasibility & Viability (Challenge 5)
    # -------------------------------------------------------------
    slide4 = prs.slides[3]
    for shape in slide4.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                if "GUI Paint Lag Bottleneck" in p.text:
                    p.text = "Distributed Network & Multi-Node IPC Latency"
                    print("[+] Slide 4: Updated Challenge 5 heading.")
                elif "Double-buffered QThread decoupling" in p.text:
                    p.text = "→ Non-blocking UDP transport with 8KB MTU fragmentation: decouples 30 Hz edge vision from 60 Hz web cockpit with zero network lag."
                    print("[+] Slide 4: Updated Challenge 5 mitigation text.")

    # -------------------------------------------------------------
    # SLIDE 6: Research & References (Subsystems list)
    # -------------------------------------------------------------
    slide6 = prs.slides[5]
    for shape in slide6.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                if "PyQt6 Dual-Viewport Cockpit" in p.text:
                    p.text = "Tactical Dual-Viewport Cockpit & Live Web Radar Mission Control (localhost:8080)"
                    print("[+] Slide 6: Updated Cockpit subsystem bullet.")

    prs.save("presentation/Phoenix_X_SIH26169_Final.pptx")
    print("[+] Successfully saved finalized deck as: presentation/Phoenix_X_SIH26169_Final.pptx")

if __name__ == '__main__':
    amend_presentation()
