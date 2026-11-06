# HyperEdit Pro: Motion Graphics & HyperFrames Integration Guide

## 1. Executive Summary & Design Mission

HyperEdit Pro integrates a professional motion graphics and animation pipeline specifically architected for autonomous AI agents. Rather than simulating visual design through text descriptions or relying on generic canned templates, HyperEdit Pro bridges **HyperFrames** (the web-standard HTML/CSS/GSAP kinetic motion framework) with **FFmpeg** (the deterministic audiovisual processing standard).

### Guiding Principles (Compliant with `AGENTS.md`):
- **Never Settle for Generic AI Aesthetics**: Avoid random neon gradients, floating meaningless geometric shapes, and cheap template cards.
- **Artistic Discipline & Restraint**: Animations communicate visual hierarchy, narrative progression, and editorial emphasis.
- **Physical Plausibility & Easing**: All transitions utilize deliberate easing curves, cubic Bézier polynomials, or damped spring physics.
- **Seek-Safe & Deterministic**: Every animation is strictly driven by an integer-frame or timestamp clock. No continuous drift, no asynchronous timers, and no unsynchronized loops.
- **True Alpha Channel Transparency**: Rendered graphic overlays maintain authentic pixel transparency (`yuva444p12le` Apple ProRes 4444 or `yuva420p` VP9 WebM) for artifact-free compositing over video timelines.

---

## 2. The HyperFrames Composition Contract

When authoring or generating animations, HyperEdit Pro strictly adheres to the official **HyperFrames Composition Contract**. This ensures that HTML assets can be rendered deterministically by headless Chrome or previewed in real time.

### 2.1 DOM Specification
The root element must specify composition metadata attributes:

```html
<div 
  data-composition-id="cinematic_intro_01" 
  data-width="1920" 
  data-height="1080" 
  data-duration="4.0"
  style="position: relative; width: 100%; height: 100%; overflow: hidden; background: transparent;">
  <!-- Graphic elements -->
</div>
```

### 2.2 Layout & Centering Constraints
- **Zero Transform Centering Conflict**: Never center animated elements using `transform: translate(-50%, -50%)`. Doing so directly clashes with GSAP `x`, `y`, and `scale` tweens.
- **Preferred Centering**: Use modern Flexbox (`display: flex; align-items: center; justify-content: center;`) or inset CSS properties (`top: 0; left: 0; right: 0; bottom: 0; margin: auto;`).

### 2.3 Timeline Registration & Determinism
Every composition must create and register exactly **one paused GSAP timeline** on the global window object:

```javascript
window.__timelines = window.__timelines || {};
const tl = gsap.timeline({ paused: true });

// Choreograph animation steps
tl.fromTo(".title-text", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 1.2, ease: "power2.out" }, 0.4);

// Register for seek-safe headless capture
window.__timelines["cinematic_intro_01"] = tl;
```

---

## 3. Curated Motion Art Direction Presets

HyperEdit Pro provides 6 non-generic, production-grade art direction presets. Each preset defines strict typography, refined color palettes, curated easing curves, and design constraints:

| Preset ID | Name | Primary Font | Easing Curve | Palette Highlights | Art Direction Character |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `minimal_editorial` | Minimal Editorial | Neue Haas Grotesk / Inter | `power2.out` | `#0A0A0A`, `#F5F5F3`, `#9E9E98` | Understated Swiss typography, generous negative space, zero decoration. |
| `cinematic_luxury` | Cinematic Luxury | Playfair Display / Cormorant | `power3.inOut` | `#08080A`, `#F9F9FB`, `#D4AF37` | High contrast, dramatic serif headlines, subtle gold accents, slow elegant reveals. |
| `tech_product` | Tech Product | Geist Sans / SF Pro | `cubic-bezier(0.16, 1, 0.3, 1)` | `#030712`, `#F9FAFB`, `#00F0FF` | Precision engineering, cyan tech accents, spring-damped micro-interactions. |
| `corporate_clean` | Corporate Clean | Inter / Roboto | `power1.out` | `#0F172A`, `#FFFFFF`, `#2563EB` | Executive trustworthiness, clean cobalt accents, authoritative clarity. |
| `energetic_social`| Energetic Social | Montserrat / Impact | `back.out(1.7)` / `overshoot` | `#111827`, `#FFFFFF`, `#FF0055` | Punchy pops, rapid rhythm, high contrast accents, bold kinetic hooks. |
| `typography_focus` | Typography Focus | Clash Display / Space Grotesk | `power4.out` | `#050505`, `#FAFAFA`, `#E11D48` | Monolithic text scale, tracking reveals, stark monochrome with carmine emphasis. |

---

## 4. Keyframe Interpolation & Physics Engine

HyperEdit Pro features an internal numerical interpolation engine (`KeyframeInterpolator`) capable of computing continuous transforms at any fractional progress $t \in [0, 1]$:

### 4.1 Supported Interpolation Modes
1. **`LINEAR`**: $f(t) = t$
2. **`EASE_IN`**: $f(t) = t^2$
3. **`EASE_OUT`**: $f(t) = t(2 - t)$
4. **`EASE_IN_OUT`**: Cubic S-curve $f(t) = 3t^2 - 2t^3$
5. **`BEZIER`**: Exact 2D Cubic Bézier polynomial:
   $$B(t) = 3(1-t)^2 t P_1 + 3(1-t) t^2 P_2 + t^3$$
   Solved iteratively for time $t$ given parameter $x$ using high-precision **Newton-Raphson inversion**:
   $$t_{k+1} = t_k - \frac{B_x(t_k) - x}{B'_x(t_k)}$$
6. **`SPRING`**: Damped harmonic oscillator simulation:
   $$f(t) = 1 - e^{-\zeta \omega t} \cdot \cos\left(\omega\sqrt{1-\zeta^2} \cdot t\right)$$
   Yields realistic mechanical settling without sudden artificial halts.
7. **`OVERSHOOT`**: Anticipatory / bounce curve:
   $$f(t) = (s + 1)(t - 1)^3 + s(t - 1)^2 + 1 \quad \text{where } s \approx 1.70158$$

---

## 5. Virtual Camera & Ken Burns Trajectories

HyperEdit Pro enables smooth virtual camera movements (pan, zoom, tilt) across static imagery and video clips:

```python
from hyperedit.motion.engine import MotionEngine

# Apply 8% push-in drift with slow pan right over 5 seconds
filter_str = MotionEngine.apply_ken_burns(
    start_zoom=1.00,
    end_zoom=1.08,
    pan_x=0.04,
    pan_y=0.00,
    duration_sec=5.0,
    width=1920,
    height=1080,
    fps=30.0,
)
```

The resulting expression uses FFmpeg's `scale` and `crop` sub-pixel filtergraph expressions without introducing jitter or rounding artifacts.

---

## 6. Beat-Reactive Audio Synchronization

Motion elements can pulse, scale, or flash synchronously with the rhythm of the project's audio track.

### 6.1 Workflow:
1. Run `hyperedit audio beats <music.mp3> --json` to detect real onset timestamps and BPM.
2. Inject beat timestamps into the motion composition using `hyperedit motion sync <composition.html> <music.mp3>`.
3. The adapter generates dedicated CSS/GSAP keyframes matching each beat onset:
   ```javascript
   // Auto-injected beat pulse timeline
   const beats = [0.000, 0.499, 1.000, 1.498, 2.000];
   beats.forEach(t => {
     tl.fromTo(".beat-pulse", { scale: 1.08, opacity: 1.0 }, { scale: 1.0, opacity: 0.85, duration: 0.25, ease: "power2.out" }, t);
   });
   ```

---

## 7. Rendering & Transparent Alpha Channels

A major technical hurdle in automated video assembly is rendering motion graphics with an intact alpha channel so they can overlay existing footage.

### 7.1 Primary Route: Headless HyperFrames CLI
If `npx hyperframes` is available with headless Chrome:
```bash
npx hyperframes render composition.html -o overlay.mov --format mov --fps 30.0
```
This produces an Apple ProRes 4444 QuickTime movie with uncompressed 12-bit alpha (`yuva444p12le`).

### 7.2 Autonomous Local Fallback Route: FFmpeg Alpha Pipeline
When operating offline or in headless environments without a browser display server, HyperEdit Pro features an autonomous fallback generator:
1. Generates an authentic transparent canvas:
   `color=c=black@0.0:s=1920x1080:d=4.0:r=30,format=yuva444p10le`
2. Encodes using FFmpeg's `prores_ks` encoder:
   `-c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le`
3. Probed with FFprobe, the resulting file reports:
   `Stream: Video: prores (4444), yuva444p12le`
   Confirming 100% transparency compatibility for compositing.

---

## 8. Multi-Track Timeline Integration

To composite rendered motion graphics over an existing timeline:
1. Add or select a track with `TrackKind.GRAPHIC` (e.g. track `GRAPHIC` or `V2`).
2. Insert the transparent clip specifying `timeline_start_frame`.
3. HyperEdit Pro's `FiltergraphCompiler` automatically compiles the dual video streams into an `[input][overlay] overlay=format=auto` node chain.
4. Render the master deliverable:
   ```bash
   hyperedit project render project.json -o master_film.mp4
   ```

---

## 9. CLI Command Reference

### `hyperedit motion presets`
List all 6 curated motion art direction presets with typography and palettes.
```bash
hyperedit motion presets --json
```

### `hyperedit motion create <template>`
Generate an official HyperFrames composition HTML file.
```bash
hyperedit motion create cinematic_intro -o title.html --title "THE HORIZON" --preset cinematic_luxury
```
Supported templates: `cinematic_intro`, `product_showcase`, `audio_reactive`.

### `hyperedit motion sync <composition.html> <audio.mp3>`
Inject real detected audio beat markers into the composition timeline.
```bash
hyperedit motion sync title.html music_bed.mp3 -o title_synced.html
```

### `hyperedit motion render <composition.html>`
Render the motion composition to a transparent video overlay (`.mov` or `.webm`).
```bash
hyperedit motion render title_synced.html -o overlay.mov --format mov --fps 30.0
```

### `hyperedit motion overlay <project.json> <overlay.mov>`
Attach the rendered motion overlay directly onto a project timeline.
```bash
hyperedit motion overlay project.json overlay.mov --track GRAPHIC --start-frame 0
```

