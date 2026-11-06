# HyperEdit Pro: Visual Effects, Motion Tracking & 3D Integration Guide

## 1. Executive Architecture & Mission

HyperEdit Pro provides an executable, non-destructive visual effects (VFX) and motion tracking engine designed for autonomous AI agents. Rather than simulating effects with text prompts, HyperEdit Pro executes real computer vision algorithms, mathematical compositing, and headless 3D engine integration.

### Clear Boundary & Capability Matrix

| Feature | Ownership / Engine | Operational Requirements | Notes |
| :--- | :--- | :--- | :--- |
| **Point & Region Tracking** | **Native** (HyperEdit Pro / OpenCV) | Local CPU / OpenCV | Lucas-Kanade optical flow, normalized cross-correlation template matching, forward-backward validation. |
| **Video Stabilization** | **Native** (HyperEdit Pro / OpenCV) | Local CPU / OpenCV | 2D affine trajectory integration, Gaussian smoothing, border-reflect compensation warp. |
| **Masks & Feathering** | **Native** (HyperEdit Pro / OpenCV) | Local CPU / OpenCV | Rectangle, ellipse, polygon, animated keyframe interpolation, Gaussian feathering. |
| **Assisted Rotoscoping** | **Native** (HyperEdit Pro / OpenCV) | Local CPU / OpenCV | Bounding-box initialized GrabCut segmentation. *(Neural SAM requires optional GPU models)*. |
| **Alpha Compositing & Blend Modes** | **Native** (HyperEdit Pro / NumPy) | Local CPU | Premultiplied alpha, 8 standard blend modes (Normal, Multiply, Screen, Overlay, Add, Soft Light, etc.). |
| **Chroma Keying (Green/Blue Screen)** | **Native** (HyperEdit Pro / FFmpeg) | Local CPU / FFmpeg | Euclidean color distance, similarity threshold, smoothness ramp, green/blue spill suppression. |
| **Cinematic Camera Shake** | **Native** (HyperEdit Pro / FFmpeg) | Local CPU / FFmpeg | Deterministic multi-frequency trigonometric pseudo-random camera shake. |
| **Photochemical Film Grain** | **Native** (HyperEdit Pro / FFmpeg) | Local CPU / FFmpeg | Temporal uniform noise synthesis on luma/chroma channels. |
| **Bloom & Highlight Glow** | **Native** (HyperEdit Pro / FFmpeg) | Local CPU / FFmpeg | High-pass threshold luminance extraction, Gaussian diffusion, and additive blend. |
| **Motion Blur** | **Native** (HyperEdit Pro / FFmpeg) | Local CPU / FFmpeg | Temporal shutter angle accumulation (`tblend=all_mode=average`). |
| **Kinetic Motion Graphics** | **HyperFrames** (`/hyperframes`) | Node.js / Headless Chrome | HTML/CSS/GSAP kinetic titles, lower thirds, UI captures. |
| **3D Scene Renders** | **Blender Adapter** (`BlenderAdapter`) | Blender CLI (`blender`) | Headless command execution (`-b scene.blend -E CYCLES -a`), transparent RGBA sequences. |

---

## 2. Motion Tracking & Stabilization

### 2.1 Tracking Algorithms
HyperEdit Pro implements two primary computer vision tracking algorithms in [`MotionTracker`](file:///c:/Users/migue/Desktop/hyperedit%20pro/src/hyperedit/vfx/tracking.py):
1. **Normalized Cross-Correlation Template Matching (`TrackingMethod.REGION_TEMPLATE`)**:
   - Compares localized neighborhood patches using `cv2.TM_CCOEFF_NORMED`.
   - Produces a bounded similarity confidence score $\in [0.0, 1.0]$.
   - Employs a 5% adaptive template blend to track targets undergoing moderate illumination changes without drift.
   - Automatically falls back to the original keyframe template if localized confidence drops.
2. **Lucas-Kanade Sparse Optical Flow (`TrackingMethod.POINT_LK`)**:
   - Tracks prominent corner features with forward-backward error validation ($I_t \to I_{t+1} \to \hat{I}_t$).
   - Calculates Euclidean distance $\|\mathbf{x} - \hat{\mathbf{x}}\|$ to penalize occlusions and rapid scale changes.

### 2.2 Handling Lost Tracking
- If confidence drops below `confidence_threshold` (default: 0.50) or the target exits the screen boundaries, `lost` is flagged as `True`.
- Telemetry outputs exact counts: `total_frames`, `tracked_frames`, `lost_frames`, and `mean_confidence`.
- **Agent Rule**: Never assume tracking is accurate without inspecting telemetry. If `mean_confidence < 0.75` or `lost_frames > 0`, warn the user and inspect visually.

### 2.3 Video Stabilization Pipeline
The stabilizer computes frame-to-frame rigid transforms:
1. Feature point tracking across successive frames.
2. Partial affine estimation (dx, dy, da).
3. Trajectory accumulation: $T(t) = \sum \Delta(t)$.
4. Gaussian/moving-average smoothing filter: $\tilde{T}(t)$.
5. Compensation warp: $W(t) = \tilde{T}(t) - T(t)$.
6. Dynamic crop and scale (5% margin) to eliminate black borders.

---

## 3. Masks, Rotoscoping & Compositing

### 3.1 Mask Types & Feathering
In [`MaskGenerator`](file:///c:/Users/migue/Desktop/hyperedit%20pro/src/hyperedit/vfx/masks.py):
- Supports `RECTANGLE`, `ELLIPSE`, and `POLYGON` primitives.
- Keyframed interpolation between temporal keyframes (`MaskKeyframe`).
- Gaussian blur feathering: edge softness is applied via Gaussian convolution kernel $k = 2 \cdot \lceil 3\sigma \rceil + 1$.
- Non-destructive inversion (`inverted: bool = True`).

### 3.2 Assisted Rotoscoping (GrabCut)
- When a bounding box is supplied around a foreground subject, GrabCut iteratively clusters Gaussian Mixture Models (GMM) across color space.
- Produces an 8-bit alpha matte distinguishing foreground from background.
- *Limitations*: Fast and effective for high-contrast subjects. For complex hair detail or fast-moving motion blur, neural rotoscoping models (such as Segment Anything) are required.

### 3.3 Chroma Keying & Spill Suppression
In [`LayerCompositor`](file:///c:/Users/migue/Desktop/hyperedit%20pro/src/hyperedit/vfx/compositing.py):
- Calculates Euclidean color distance from target `key_color_rgb` (e.g. green `#00FF00` or blue `#0000FF`).
- Smoothness ramp:
  $$\alpha = \text{clip}\left(\frac{\text{dist} - \text{similarity}}{\text{smoothness}}, 0.0, 1.0\right)$$
- Spill suppression: Replaces green spill on subject borders with:
  $$G_{\text{clean}} = \min\left(G, \frac{R + B}{2}\right)$$
- Output can be encoded directly to Apple ProRes 4444 QuickTime movie (`yuva444p10le`) with true alpha transparency.

---

## 4. Cinematic Visual Effects

All cinematic effects are non-destructive and toggleable (`enabled: bool = True`):

### 4.1 Camera Shake (`CameraShakeConfig`)
- Simulates hand-held camera jitter using multi-frequency trigonometric series:
  $$x(t) = A \cdot \sin(2\pi f t + \phi_1) + 0.35 A \cdot \cos(4.3\pi f t + \phi_2)$$
- Automatically scales and crops the video (e.g. 1.03x) so that screen edges never reveal black bars.

### 4.2 Photochemical Film Grain (`FilmGrainConfig`)
- Synthesizes organic silver halide film grain using temporal uniform pseudo-random noise (`noise=c0s=strength:c0f=t+u`).
- Monochrome mode applies noise strictly to the luma channel (preserving color fidelity).

### 4.3 Bloom & Highlight Glow (`BloomGlowConfig`)
- High-pass luminance threshold filter isolates specular highlights ($Y > \text{threshold}$).
- High-radius Gaussian blur diffuses the highlights.
- Blended back onto the base footage using additive blend (`blend=all_mode=addition`).

### 4.4 Motion Blur (`MotionBlurConfig`)
- Simulates standard $180^\circ$ rotary camera shutter exposure using temporal frame averaging (`tblend=all_mode=average`).

---

## 5. 3D Integration: Blender Adapter

In [`BlenderAdapter`](file:///c:/Users/migue/Desktop/hyperedit%20pro/src/hyperedit/adapters/blender.py):
- Does **not** attempt to recreate 3D rendering in Python.
- Auto-detects Blender CLI in PATH or OS program directories (`C:\Program Files\Blender Foundation\...`, `/Applications/Blender.app`, `/usr/bin/blender`).
- Builds headless execution arguments:
  ```bash
  blender -b scene.blend -E CYCLES -s 1 -e 60 -o renders/frame_####.png -a
  ```
- Supports transparent background RGBA output.
- Mounts rendered image sequences or video directly onto track `V2` or `GRAPHIC` of the HyperEdit Pro timeline (`import_render_to_timeline`).
- Provides dry-run validation when Blender is not installed so AI agents can verify project pipelines without runtime crashes.

---

## 6. CLI Command Reference

### `hyperedit vfx track`
```bash
hyperedit vfx track footage.mp4 --bbox 80,80,40,40 -o tracking.json --method template
```

### `hyperedit vfx stabilize`
```bash
hyperedit vfx stabilize shaky.mp4 -o stabilized.mp4 --smoothing 15 --crop-border 0.05
```

### `hyperedit vfx key`
```bash
hyperedit vfx key greenscreen.mp4 -o keyed_alpha.mov --color 0x00FF00 --similarity 0.3 --smoothness 0.1
```

### `hyperedit vfx effect`
```bash
hyperedit vfx effect raw.mp4 -o final_grain.mp4 --effect grain --intensity 0.20
hyperedit vfx effect raw.mp4 -o final_shake.mp4 --effect shake --intensity 0.50
hyperedit vfx effect raw.mp4 -o final_bloom.mp4 --effect bloom --intensity 0.80
```

### `hyperedit vfx blender-check`
```bash
hyperedit vfx blender-check [--json]
```

