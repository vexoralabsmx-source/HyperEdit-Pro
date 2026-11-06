# Professional Captions & Kinetic Typography Guide

**HyperEdit Pro** provides a complete captions, subtitles, speech recognition, and kinetic typography engine for AI agents.

It seamlessly handles traditional broadcast sidecar files (.srt, .vtt), typographic ASS v4.00+ scripts, word-level synchronized kinetic animations, and HyperFrames HTML/CSS/GSAP motion graphic overlays.

---

## 1. Supported Formats & Conversion Pipeline

HyperEdit Pro natively parses and exports:

| Format | Extension | Capabilities | Typical Use Case |
|---|---|---|---|
| **SubRip** | `.srt` | Timed cues with milliseconds | Universal streaming / raw sidecar exports |
| **WebVTT** | `.vtt` | HTML5 video cues, cue positioning | Modern web players, HLS / DASH streaming |
| **Advanced SubStation Alpha** | `.ass` | Full typography, fonts, colors, outlines, shadows, boxes, and kinetic animations | High-fidelity burn-in, anime, YouTube / Reels creator styling |
| **HyperFrames HTML** | `.html` | Full DOM, CSS keyframes, GSAP timelines, transparent background | Complex kinetic typography overlays, kinetic title cards |

---

## 2. Professional Typographic Presets

HyperEdit Pro includes 6 calibrated presets adhering to broadcast contrast standards:

### 2.1 `netflix`
- **Look**: Clean, unobtrusive white sans-serif with soft shadow.
- **Font**: Arial / Helvetica, 36 pt.
- **Positioning**: Bottom center, 50px vertical margin.
- **Use Case**: Narrative cinema, documentary, corporate presentations.

### 2.2 `modern_bold`
- **Look**: Crisp bold sans with heavy black stroke and yellow (`#FFE600`) word highlights.
- **Font**: Arial Bold, 42 pt.
- **Positioning**: Bottom center, 70px vertical margin.
- **Use Case**: Tech explainers, tutorials, modern YouTube videos.

### 2.3 `cinema_serif`
- **Look**: Warm ivory serif (`#F0EDE6`) with subtle outline.
- **Font**: Georgia / Times, 34 pt.
- **Positioning**: Bottom center, 60px vertical margin.
- **Use Case**: Period pieces, drama, prestige editorial content.

### 2.4 `tiktok_reels_neon`
- **Look**: All-caps bold typography with bright cyan (`#00FFCC`) active word highlight and semi-transparent pill box.
- **Font**: Arial Bold, 52 pt.
- **Positioning**: Middle-center / elevated bottom with 220px margin (safe above TikTok / Instagram Reels UI buttons).
- **Use Case**: 9:16 vertical social media clips, Reels, YouTube Shorts.

### 2.5 `impact_pop`
- **Look**: High-energy condensed uppercase with word pop scaling (`\fscx115\fscy115`) and crimson (`#FF3366`) accent.
- **Font**: Impact / Arial Black, 48 pt.
- **Positioning**: Bottom center, 120px vertical margin.
- **Use Case**: Creator vlogs, fitness, gaming, high-energy hooks.

### 2.6 `minimalist`
- **Look**: Subtle light gray with dark semi-transparent box.
- **Font**: Arial, 28 pt.
- **Positioning**: Bottom center, 40px margin.
- **Use Case**: Educational walkthroughs, code screencasts, webinars.

---

## 3. Kinetic Typography & Animation Modes

Kinetic typography creates synchronized word-level animations:

### 3.1 `karaoke_highlight`
Each word changes to `highlight_color_hex` during its spoken window $[t_{\text{start}}, t_{\text{end}}]$ while the full sentence remains visible, allowing the viewer to maintain reading context:
```text
Dialogue: 0,0:00:01.00,0:00:01.40,Default,,0,0,0,,{\c&H0000E6FF&}Bienvenido{\r} a HyperEdit Pro
Dialogue: 0,0:00:01.40,0:00:01.60,Default,,0,0,0,,Bienvenido {\c&H0000E6FF&}a{\r} HyperEdit Pro
Dialogue: 0,0:00:01.60,0:00:02.10,Default,,0,0,0,,Bienvenido a {\c&H0000E6FF&}HyperEdit{\r} Pro
```

### 3.2 `pop_scale`
The active word scales up by 15% (`{\fscx115\fscy115}`) with an accent color shift to draw eye focus.

### 3.3 `word_reveal`
Words accumulate progressively across the screen as they are spoken.

### 3.4 `fade_word` & `slide_up`
Smooth entry transitions using ASS `{\fad(150,150)}` or upward movement vectors `{\move(x, y+25, x, y)}`.

---

## 4. Safe Areas & Layout Rules

Subtitles must never collide with video player interfaces:

- **16:9 Landscape Video**:
  - Horizontal margins: $\ge 50\text{px}$.
  - Vertical bottom margin: $60-80\text{px}$.
  - Maximum characters per line: $37-42\text{ CPL}$.
- **9:16 Portrait Video (Reels / TikTok / Shorts)**:
  - Bottom margin: $\ge 180-220\text{px}$ (prevents overlap with account name, caption description, audio track, and like/comment buttons).
  - Horizontal margins: $\ge 50\text{px}$.
  - Maximum characters per line: $22-26\text{ CPL}$.

Automated safe area enforcement:
```python
engine = CaptionsEngine()
engine.adjust_safe_areas(track, aspect_ratio="9:16", resolution=(1080, 1920))
```

---

## 5. Readability & Cognitive QA

HyperEdit Pro audits subtitle tracks against international readability standards:

- **Reading Speed (CPS)**: Flags cues exceeding 25 characters per second (human reading ceiling).
- **Minimum Duration**: Flags cues under 700ms (insufficient time for eye fixation).
- **Line Length (CPL)**: Flags lines exceeding maximum character thresholds.
- **Temporal Overlaps**: Flags conflicting cues where `start_ms < previous.end_ms`.

```bash
hyperedit captions validate subtitles.srt
```

---

## 6. Burning Subtitles into Video via FFmpeg & libass

To hardcode subtitles permanently with zero quality loss:

```bash
# Burn with modern bold preset
hyperedit captions burn input.mp4 captions.srt -o output_burned.mp4 --preset modern_bold

# Burn vertical reels kinetic typography
hyperedit captions burn clip_9x16.mp4 captions.srt -o reels_burned.mp4 --preset tiktok_reels_neon
```

Cross-Platform Windows Path Escaping:
FFmpeg's `libass` requires forward slashes and escaped drive colons:
```python
forward = Path(ass_file).resolve().as_posix()
escaped = forward.replace(":", r"\:")
# Formats into: ass=filename='C\:/path/to/captions.ass'
```

---

## 7. Speech-to-Text Transcription (`faster-whisper`)

HyperEdit Pro integrates with `faster-whisper` for local, private speech recognition with word timestamps.

### Installation
```bash
pip install faster-whisper
```

### CLI Usage
```bash
hyperedit captions transcribe interview.mp4 -o interview.srt --model base --language es
```

> **Note**: If `faster-whisper` is not installed, HyperEdit Pro raises a clear `DependencyMissingError` and never hallucinates or simulates fake speech transcriptions.

---

## 8. HyperFrames HTML Motion Graphic Adapter

For complex motion graphics beyond libass (CSS transforms, GSAP timelines, blur/glow animations), export directly to a HyperFrames HTML composition:

```bash
hyperedit captions hyperframes subtitles.srt -o captions_overlay.html --preset modern_bold
```

The resulting HTML file can be rendered into a transparent video overlay via HyperFrames CLI (`hyperframes render`) and layered onto track `GRAPHIC`.

