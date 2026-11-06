# HyperFrames & HyperEdit Pro Integration Architecture

## 1. Division of Responsibilities

HyperFrames and HyperEdit Pro solve distinct yet deeply complementary layers of the audiovisual stack:

| Dimension | HyperFrames | HyperEdit Pro |
| :--- | :--- | :--- |
| **Primary Domain** | Generative Motion Graphics & Web/DOM Rendering | Non-Linear Editing (NLE) & Audiovisual Post-Production |
| **Engine Core** | Headless Chromium + Puppeteer (HTML5/CSS/Canvas/GSAP) | Python 3.11+ Core driving FFmpeg, FFprobe & DSP Filters |
| **Source Media** | Code, DOM trees, SVG, WebGL, CSS Keyframes | Multi-track cameras, external audio, B-roll, voiceovers |
| **Timeline Model** | DOM `data-*` timing attributes and sub-compositions | Discrete-frame multi-track NLE timeline (V1..Vn, A1..An) |
| **Audio Processing** | Track triggers & basic browser playback | Multi-bus audio mixing, sidechain ducking, EBU R128 loudness |
| **Color Science** | CSS colors and Canvas filters | ASC-CDL, 3D LUTs (.cube), primary wheels, broadcast spaces |
| **Ideal Outputs** | Animated titles, lower thirds, UI explainers, stings | Finished films, podcasts, commercials, trailers, multi-cam |

---

## 2. Complementary Synergy

Instead of duplicating HTML rendering in Python or forcing multi-hour multi-track footage assembly through a headless browser, HyperEdit Pro and HyperFrames collaborate through a **clean producer-consumer pipeline**:

```
 ┌─────────────────────────────────────────────────────────┐
 │               HyperFrames Motion Studio                 │
 │  • Kinetic Lower Thirds                                 │
 │  • Animated Title Cards & Intros                        │
 │  • Product UI Walkthroughs / Code Visualizations        │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼  (npx hyperframes render --format prores4444)
                  [Intermediate Video with Alpha]
                              │
 ┌────────────────────────────▼────────────────────────────┐
 │                  HyperEdit Pro Core                     │
 │  • Track V2 (GRAPHIC): HyperFrames Alpha Render         │
 │  • Track V1 (VIDEO): Multi-camera Footage + B-Roll      │
 │  • Track A1 (AUDIO): Dialogue Master (EBU R128)         │
 │  • Track A2 (AUDIO): BGM with Sidechain Ducking         │
 │  • Color Grading: 3D LUT & ASC-CDL Master               │
 │  • Quality Assurance: Black frame & Audio clip checks   │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼  (Hardware-accelerated FFmpeg)
                     [Master Delivery MP4 / ProRes]
```

---

## 3. The HyperFrames Adapter Protocol

HyperEdit Pro provides an adapter module (`hyperedit.adapters.hyperframes.HyperFramesAdapter`) that implements the `HyperFramesAdapterProtocol`.

### 3.1 Detection
The adapter probes:
1. `hyperframes` binary on system PATH.
2. `node` runtime with `npx` capability.
3. Local project `package.json` with pinned `hyperframes` dependency.

### 3.2 Transparent Render Execution
When rendering motion graphics to be placed over video, the adapter executes:
```bash
npx hyperframes render --composition <composition_id> --output <output_path.mov> --format prores4444 --fps <project_fps>
```
The resulting ProRes 4444 file carries an uncompressed alpha channel that blends seamlessly into FFmpeg's `overlay` filter in HyperEdit Pro's filtergraph.

### 3.3 Timeline Mounting
Once rendered:
1. The rendered `.mov` is registered in `project.media_pool`.
2. A clip is created on a track of kind `graphic`.
3. Start frame and duration are synced to dialogue or beat markers.

