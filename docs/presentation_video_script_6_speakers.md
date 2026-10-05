# Phoenix-X: Master Presentation Video Script
### Team Phoenix X (Team ID: 141943) — SIH 26169 (ISRO / Space Applications Centre)
**Target Video Runtime:** ~7 minutes 45 seconds (~1,200 words at a natural, conversational 150 wpm)

---

### Speaker Lineup & Roles
1. **Eby** — *Team Lead / Systems Architect* (Mission Framing & Scope Boundary)
2. **Clament** — *Optical & Sensor Physicist* (Sensor Geometry & Channel Physics)
3. **Anna** — *Computer Vision & Edge AI Engineer* (Perception & Sub-Pixel Localization)
4. **Kieran** — *Controls & Dynamics Engineer* (The Controls Dilemma & Latency Compensation $H_1$)
5. **Justin** — *State Estimation & Re-acquisition Specialist* (Uncertainty-Guided Re-acquisition $H_2$)
6. **Lewin** — *Lead Systems Integrator / Compliance Officer* (The Evaluator Engine & Mission Impact)

---

## 🎬 Video Recording Script

```
[00:00 - 01:15] Eby: Mission Framing & Scope Boundary
[01:15 - 02:30] Clament: Sensor Geometry & Channel Physics
[02:30 - 03:45] Anna: Perception & Sub-Pixel Localization Engine
[03:45 - 05:00] Kieran: The Controls Dilemma & Latency (H1)
[05:00 - 06:15] Justin: Uncertainty-Guided Re-acquisition (H2)
[06:15 - 07:45] Lewin: The Evaluator Engine & Mission Impact
```

---

### 1. Eby: Mission Framing & Scope Boundary
**Duration:** ~01:15 (00:00 – 01:15)  
**Tone:** Authoritative, clear, mission-focused  

`[Visual Cue: Slide 1 — Title & Headline Capabilities on screen. Camera begins on a wide shot of the team or on Eby in medium-close-up.]`

> **Eby:**  
> "Free Space Optical Communication is fundamentally changing how satellites, aircraft, and ground stations exchange data. When you replace traditional radio waves with infrared laser beams, your bandwidth skyrockets and your transmission becomes completely tap-proof. 
> 
> But physics gives you nothing for free. 
> 
> Because an optical beam diverges by only tens of microradians, hitting a receiver thousands of kilometers away is like trying to strike a coin across an entire football stadium while both platforms are vibrating at high speed. 
> 
> In aerospace, this is solved by a disciplined two-stage Pointing, Acquisition, and Tracking—or PAT—chain. 
> 
> First, a motorized gimbal uses a wide-angle camera to locate the remote beacon and coarsely pull it onto the optical bore-sight. Once it’s inside a tight angular cone, downstream fine-steering mirrors take over at kilohertz speeds for sub-microradian optical link communication.
> 
> We engineered **Phoenix-X** specifically for that vital first stage: the coarse tracking and re-acquisition stage of the PAT chain defined by ISRO and the Space Applications Centre under Problem Statement 26169. We are not claiming to solve fine-pointing, fast steering mirrors, or quantum link budgets here. Our mission is concrete: deliver a validated software-in-the-loop testbed that brings an erratic, noise-corrupted optical beacon within ten pixels of bore-sight and holds it there under extreme conditions.
> 
> To explain how we model this reality from the photon level up, here is Clament with our sensor and channel physics."

`[Handoff: Eby turns and gestures toward Clament. Camera cuts to Clament / Slide 2.]`

---

### 2. Clament: Sensor Geometry & Channel Physics
**Duration:** ~01:15 (01:15 – 02:30)  
**Tone:** Scientific, grounded, precise  

`[Visual Cue: Slide 2 — Proposed Solution & 3-Tier Architecture. Cut to Tier 1 (Kinematics) & Tier 2 (Optics) zoom.]`

> **Clament:**  
> "Thank you, Eby. When evaluating any vision-based tracker, the very first question a domain expert asks is: *What is your angular scale?* 
> 
> Under our default sensor geometry—a four-by-three degree field of view across a standard six-forty by four-eighty pixel focal plane—each pixel represents exactly one hundred and nine point one microradians, or twenty-two point five arcseconds. That means ISRO’s requirement of keeping the target within ten pixels of center is not an arbitrary number; it corresponds to a precise physical capture cone of approximately one point zero nine milliradians.
> 
> Now, in synthetic demos, people love to draw clean circles. But real space and aerial optical channels are hostile.
> 
> In Phoenix-X, the remote beacon doesn't look like a computer icon; it forms a diffraction-limited Airy spot profile between five and twenty pixels across. As that light traverses the atmosphere, it suffers Beer-Lambert extinction from dynamic fog, Poisson shot noise from ambient photons, and severe sensor degradation. 
> 
> The problem statement explicitly challenges us with a ten percent Salt-and-Pepper noise condition—and we even stress-tested our pipeline all the way up to twenty-five percent. On top of that, satellite reaction wheels and aerodynamic buffeting inject multi-harmonic platform jitter of up to plus-or-minus twenty pixels. 
> 
> If you throw a generic computer vision model like YOLO at this, it completely collapses. A deep object detector expects edges, textures, and shape context—none of which exist in a faint, twinkling optical point source. 
> 
> To show how we solved detection without bloated neural networks, Anna will walk you through our perception engine."

`[Handoff: Clament gestures toward Anna. Camera cuts to Anna / Slide 3.]`

---

### 3. Anna: Perception & Sub-Pixel Localization Engine
**Duration:** ~01:15 (02:30 – 03:45)  
**Tone:** Analytical, engaging, demonstrating elegance over brute force  

`[Visual Cue: Slide 3 — Left Column Workflow Step 5 & 4-Quadrant Disturbance Panel from Slide 4.]`

> **Anna:**  
> "Thanks, Clament. As Clament pointed out, generic AI object detectors are the wrong tool for free-space optics. They are slow, require discrete GPUs, and hallucinate under impulsive noise.
> 
> Instead, Phoenix-X takes a scientifically defensible approach: **Adaptive Beacon Localization**.
> 
> When a degraded frame arrives, our first stage runs a fast rank-order median filter. This strips out one hundred percent of impulsive salt-and-pepper noise in under zero point eight milliseconds. Next, we apply morphological Top-Hat filtering to estimate and subtract non-uniform background haze and sensor dark current.
> 
> Once the candidate region is isolated, we don't just pick the brightest pixel. Real optical spots spread light across neighboring sensor elements. We perform two-dimensional sub-pixel Intensity-Weighted Centroiding, refined with analytical continuous Gaussian surface fitting. 
> 
> Mathematically, by evaluating local surface curvature around the spot's energy peak, we eliminate pixel quantization entirely. In our empirical sweeps, this brings centroid error down to less than zero point two pixels—well inside the ten-pixel boundary.
> 
> For extreme atmospheric scintillation where the beacon fades into the noise floor, we also engineered a four-layer fully convolutional edge network called DeepBeaconSaliencyNet. It runs in under zero point nine milliseconds on a standard CPU, and we even built a native Apple Silicon MLX GPU pipeline running at point nine-six milliseconds.
> 
> But as our mentors taught us: *detection is only half the battle. In a real tracking terminal, loop latency and actuator limits matter far more than the tracker.* 
> 
> Here is Kieran with how we turned tracking into a genuine controls problem."

`[Handoff: Anna turns to Kieran. Camera cuts to Kieran / Slide 3 Right Column & Slide 4 Latency focus.]`

---

### 4. Kieran: The Controls Dilemma & Latency ($H_1$)
**Duration:** ~01:15 (03:45 – 05:00)  
**Tone:** Practical, engineering-minded, focused on physical constraints  

`[Visual Cue: Slide 3 — Servo Control Loop & Slide 4 Challenge 2 & 3. Equation on screen: $\hat{\mathbf{x}}_{t+\tau} = \mathbf{F}^\kappa \hat{\mathbf{x}}_t$.]`

> **Kieran:**  
> "Thanks, Anna. In academic demos, people often assume that as soon as a camera sees an object, the gimbal can point directly at it. 
> 
> In reality, that is physically impossible. 
> 
> By the time photons hit the sensor, the frame is exposed, the image is processed, and a command travels over the bus to a mechanical pan-tilt motor, several frame intervals have elapsed. That cumulative loop latency—denoted by tau—typically sits between thirty and two hundred milliseconds. If you command a gimbal based on where the beacon *was* two hundred milliseconds ago, you get phase lag, severe overshoot, and broken links.
> 
> Furthermore, physical gimbals have motor torque limits. The problem statement sets a statutory slew limit between five and ten degrees per second. If your controller commands an instantaneous step velocity, your actuators saturate.
> 
> This is our second core research innovation: **Latency-Compensated Predictive Pointing**, which we formally tested as Hypothesis H1.
> 
> Phoenix-X deploys an Interacting Multiple Model Kalman Filter that dynamically blends Constant Velocity and Coordinated Turn kinematic models. But instead of passing the current state estimate to the motor, the filter projects the target’s position forward in time to $t$ plus tau. 
> 
> We feed this future pointing error into an anti-windup PID servo controller equipped with velocity feedforward and strict five-degree-per-second velocity clamping.
> 
> In our controlled sweeps, this latency-aware feedforward compensation reduces steady-state pointing lag by up to thirty-two percent under heavy loop delays.
> 
> But what happens when the beam is cut off entirely? To explain how we recover the optical link, here is Justin."

`[Handoff: Kieran gestures toward Justin. Camera cuts to Justin / Slide 4 Challenge 4 & Slide 2 Innovation Card 1.]`

---

### 5. Justin: Uncertainty-Guided Re-acquisition ($H_2$)
**Duration:** ~01:15 (05:00 – 06:15)  
**Tone:** Passionate, intellectual, highlighting the standout research breakthrough  

`[Visual Cue: Slide 4 Challenge 4 & Slide 2 Innovation Card 1. Display graphic or animation of expanding covariance ellipse vs Archimedean spiral.]`

> **Justin:**  
> "Thank you, Kieran. In real operational flight, target loss is inevitable. A cloud bank sweeps through, an aircraft banks sharply, or a building temporarily occludes the line of sight. 
> 
> When other systems lose a track, their standard response is simple: enter a blind, fixed Archimedean spiral centered on the bore-sight. 
> 
> But think about how inefficient that is. If your target was moving northeast at fifty pixels per second when the cloud hit it, why on earth would you search southwest first?
> 
> This brings us to our primary scientific innovation: **Uncertainty-Guided Re-acquisition**, tested as Hypothesis H2.
> 
> In Phoenix-X, when optical observations cease, the Kalman filter doesn’t simply stop. It continues propagating kinematics in coast mode. As time elapses without measurements, the filter's state covariance matrix, $\mathbf{P}_k$, grows. 
> 
> By taking the eigenvalues and eigenvectors of this covariance, our controller synthesizes a real-time uncertainty ellipse. The semi-major axis naturally aligns along the direction of highest target uncertainty, and the semi-minor axis reflects orthogonal drift.
> 
> Instead of an arbitrary circular spiral, our gimbal commands an expanding scan pattern that matches the shape and orientation of this uncertainty ellipse. We search the highest probability space first.
> 
> The empirical results are staggering: for short optical outages of two hundred milliseconds, uncertainty-guided re-acquisition recovers the lock up to ninety-seven percent faster than a blind spiral. Even across extended multi-second outages, it consistently delivers a thirty-four to forty-five percent speedup.
> 
> That difference is the line between maintaining a continuous satellite data downlink and losing the pass completely.
> 
> Now, Lewin will demonstrate how any evaluator can independently verify these claims with a single click."

`[Handoff: Justin turns toward Lewin. Screen cuts to Lewin / Live Cockpit Demo / Slide 5 & 6.]`

---

### 6. Lewin: The Evaluator Engine & Mission Impact
**Duration:** ~01:30 (06:15 – 07:45)  
**Tone:** Confident, transparent, bringing the presentation home to a memorable close  

`[Visual Cue: Slide 6 & Brief screen share of Phoenix-X running in live dual-viewport cockpit or web mission control.]`

> **Lewin:**  
> "Thanks, Justin. Everything our team just described isn’t a collection of slide claims or mockups—it is running, fully tested code.
> 
> One of our highest design priorities was making Phoenix-X completely defensible to technical evaluators. That’s why the software has two decoupled operating modes.
> 
> First, our **Interactive SIL Physics Simulator**, which runs full closed-loop orbital and aerial maneuvers with real-time multi-harmonic jitter and disturbance injection.
> 
> Second, what we call the **Evaluator's Weapon: Decoupled MP4 Mode**. 
> Evaluators do not have to take our simulator's word for it. You can drag and drop any external recorded optical video file—synthetic or real—and Phoenix-X will ingest the frames, track the beacon, and compare the trajectory against a ground-truth CSV file. 
> 
> At the end of every run, our engine automatically exports a timestamped CSV compliance audit logging root-mean-square error, frame rate, slew rate enforcement, and lock retention rates against ISRO’s criteria.
> 
> And to ensure zero barrier to entry, we built native one-click bundles: a standalone sixty-one megabyte macOS disk image optimized for Apple Silicon, and an automated GitHub Actions CI workflow that compiles Windows executables on every commit. No Anaconda environments, no dependency hell—one click, and the entire mission control launches in under thirty seconds.
> 
> All twenty unit tests pass cleanly, our literature foundation is anchored in six peer-reviewed IEEE, MDPI, and CVPR papers with active DOIs, and the entire repository is open-sourced under the MIT license.
> 
> Phoenix-X bridges the gap between theoretical optical communication and rigorous, reproducible controls engineering. 
> 
> On behalf of Team Phoenix X—Eby, Clament, Anna, Kieran, Justin, and myself—thank you for your time. We look forward to your questions."

`[Final Shot: All 6 team members on screen or Title Card showing Team Phoenix X (Team ID: 141943) and GitHub repository link.]`

---

## 📋 Speaker Quick-Reference Card

| Order | Speaker | Core Responsibility | Key Concepts & Soundbites | Timing |
|:---:|:---:|:---|:---|:---:|
| **1** | **Eby** | Mission & Scope | • Tens of $\mu\text{rad}$ beams<br>• 2-stage PAT hierarchy<br>• Coarse tracking boundary ($\le 10\text{ px}$) | 00:00 – 01:15 |
| **2** | **Clament** | Optics & Geometry | • $109.1\ \mu\text{rad/px}$ scale ($1.09\text{ mrad}$ cone)<br>• Diffraction Airy PSF profile<br>• PS ~10% to 25% S&P & $\pm 20\text{ px}$ jitter | 01:15 – 02:30 |
| **3** | **Anna** | Perception Engine | • Why YOLO fails for spot detection<br>• Top-Hat background suppression<br>• Sub-pixel IWC (< 0.2 px RMSE)<br>• 0.9 ms edge AI inference | 02:30 – 03:45 |
| **4** | **Kieran** | Controls & Latency ($H_1$) | • "Actuators & latency matter more than trackers"<br>• Loop delay $\tau \in [0, 200]\text{ ms}$<br>• Forward state projection $\hat{\mathbf{x}}_{t+\tau}$<br>• $5^\circ/\text{s}$ slew clamp (up to 32% lag cut) | 03:45 – 05:00 |
| **5** | **Justin** | Re-acquisition ($H_2$) | • Flaws of blind fixed spirals<br>• State covariance $\mathbf{P}_k$ growth in coast<br>• Uncertainty ellipse expansion<br>• Up to 97% faster re-lock on short outages | 05:00 – 06:15 |
| **6** | **Lewin** | Verification & Impact | • Evaluator's Decoupled MP4 mode<br>• Automated CSV compliance audits<br>• 1-click 61 MB macOS DMG & Windows EXE<br>• 20/20 unit tests, 6 DOI citations | 06:15 – 07:45 |

---

### 💡 Filming & Rehearsal Checklist
1. **Pacing:** Each speaker should speak for approximately **70 to 75 seconds**. Keep the pace steady and conversational—don't rush through the technical terms.
2. **Audio Levels:** Have all speakers do a 10-second sound check to ensure volume levels are balanced across transitions.
3. **Screen Cues:** During Kieran's and Justin's sections, having the animated trajectory or covariance search diagram on screen adds tremendous visual authority. During Lewin's section, showing the actual live application running or the terminal CSV export proves full working implementation.