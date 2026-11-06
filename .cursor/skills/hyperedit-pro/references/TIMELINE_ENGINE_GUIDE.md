# HyperEdit Pro Timeline & Editing Engine Technical Guide

This guide details the non-destructive, frame-accurate timeline editing model, operations architecture, and rendering pipeline of **HyperEdit Pro**.

---

## 1. Timeline Architectural Philosophy

HyperEdit Pro treats video editing as a **declarative, non-destructive graph of temporal operations**.

### Fundamental Guarantees:
1. **Discrete Frame Math**: Every cut, in-point, out-point, and transition offset is an integer frame count (`int`) resolved against the project's base framerate (`Fraction`).
2. **Hard Cuts as the Narrative Default**: Transitions are never applied indiscriminately. Hard cuts are the foundational default for visual storytelling, ensuring pacing integrity and avoiding amateurish visual clutter.
3. **Continuous Audio/Video Phase Sync**: Speed adjustments (`speed != 1.0`) automatically synchronize audio using chained `atempo` filters to maintain pitch and sync without drifting.
4. **Non-Destructive Operations**: Source media assets are strictly read-only. Slices, trims, speed changes, and transforms exist only as metadata in the project JSON until render dispatch.

---

## 2. Multi-Track Layering & Z-Index

The timeline supports stacked tracks evaluated in ascending order:

| Track Kind | Typical Identifier | Role | Compositing Behavior |
| :--- | :--- | :--- | :--- |
| `VIDEO` | `V1` | Primary narrative bed (A-roll) | Base layer, hard cuts & horizontal transitions (`xfade`) |
| `VIDEO` | `V2` | B-roll & cutaways | Overlays over V1 with optional positioning & scaling |
| `GRAPHIC` | `GRAPHIC` / `G1` | HyperFrames motion graphics, lower thirds | Alpha blended (`yuva420p`) over lower video layers |
| `AUDIO` | `A1` | Dialogue / Voiceover | Mixed with exact timeline delay and resampling to 48kHz |
| `AUDIO` | `A2` | Background music (BGM) | Ducked automatically via dialogue triggers |
| `AUDIO` | `A3` | Sound effects (SFX) & Foley | Spot sound effects triggered at frame markers |
| `SUBTITLE`| `SUB1` | Captions & subtitles | Burned in via `libass` or exported as sidecar SRT/ASS |

---

## 3. Editing Operations & Algorithms

### A. Insert (`insert_clip`)
- **Ripple Mode (`ripple=True`)**:
  Inserts a clip at `start_frame`. All clips already occupying `timeline_start_frame >= start_frame` are shifted forward by the inserted clip's duration (`timeline_duration_frames`).
- **Overwrite Mode (`ripple=False`)**:
  Punches the clip into the timeline. If the new clip collides with existing clips:
  - Completely covered clips are dropped.
  - Partially covered clip heads are shifted right.
  - Partially covered clip tails are trimmed.
  - Clips punched in the center are cleanly split into a head slice and a tail slice.

### B. Split (`split_clip`)
Takes a clip instance and splits it at an exact timeline frame `split_frame`:
$$\Delta_{\text{timeline}} = \text{split\_frame} - \text{clip.timeline\_start\_frame}$$
$$\Delta_{\text{source}} = \text{round}(\Delta_{\text{timeline}} \cdot \text{clip.speed})$$
$$\text{source\_split} = \text{clip.in\_frame} + \Delta_{\text{source}}$$
- **Clip Part 1 (Head)**: `in_frame` to `source_split`.
- **Clip Part 2 (Tail)**: `source_split` to `out_frame`, starting at `split_frame`.

### C. Trim (`trim_clip`)
- **Head Trim**: Adjusts `in_frame`. If `ripple=False`, shifts `timeline_start_frame` to preserve tail position. If `ripple=True`, downstream clips shift.
- **Tail Trim**: Adjusts `out_frame`, recalculating duration.

### D. Ripple Delete (`ripple_delete`)
Removes the clip and calculates its duration $D$. Pulls all subsequent clips on that track backward by $D$ frames, closing the gap instantly.

### E. Gap Closure (`close_gaps`)
Scans a track for accidental dead frames between clips and snaps each clip to the previous clip's `timeline_end_frame`.

---

## 4. Transitions Engine

HyperEdit Pro uses FFmpeg's `xfade` filter for seamless, frame-accurate transitions between adjacent clips on video tracks:

```
[c1][c2] xfade=transition={name}:duration={T}:offset={offset},settb=1/{fps}
```

### Supported Transitions:
- `fade` / `crossfade` / `dissolve`: Smooth luminance cross-dissolve.
- `dip_to_black` (`fadeblack`): Fades out to black and fades in from black.
- `dip_to_white` (`fadewhite`): Fades out to white and fades in from white.
- `wipe_left`, `wipe_right`, `wipe_up`, `wipe_down`: Directional linear wipes.
- `slide_left`, `slide_right`: Sliding push transition.
- `zoom_in`, `zoom_out`: Optical camera zooms.

### Hard Cuts:
Hard cuts do not use `xfade`. Adjacent clips with no transition are concatenated via `concat=n=2:v=1:a=0` with matching timebases (`settb=1/{fps}`), guaranteeing zero frame drops or black flicker.

---

## 5. Speed Control, Slow Motion & Reverse

- **Speed Adjustment**:
  - Video PTS is scaled: `setpts=(1.0 / speed)*PTS`.
  - Audio tempo is adjusted without pitch shifting: `atempo={speed}` (chained for speeds $> 2.0$ or $< 0.5$).
- **Reverse Motion**:
  - Video: `reverse` filter.
  - Audio: `areverse` filter.

---

## 6. Spatial Transforms, Keyframing & Reframing

Clips support 2D spatial transforms:
- `scale_x`, `scale_y`: Scaling multipliers.
- `position_x`, `position_y`: Pixel offset from anchor.
- `opacity`: Alpha multiplier ($0.0$ to $1.0$).
- `fit_mode`:
  - `fit` (Letterbox): Preserves source aspect ratio and pads empty borders.
  - `fill` (Crop): Zooms until canvas is completely filled, cropping excess.
  - `stretch`: Stretches non-proportionally to match canvas dimensions.

Supported canvas formats:
- **16:9** ($1920 \times 1080$, $3840 \times 2160$)
- **9:16** ($1080 \times 1920$, Reels / TikTok / Shorts)
- **1:1** ($1080 \times 1080$, Square)
- **4:5** ($1080 \times 1350$, Social Feeds)

---

## 7. CLI Reference for Timeline Operations

```bash
# 1. Create a fresh project
hyperedit project create my_edit.json --preset 1080p --fps 30.0

# 2. Inspect timeline tracks, clips, and gaps
hyperedit timeline inspect my_edit.json [--json]

# 3. Validate timeline integrity and check collisions
hyperedit timeline validate my_edit.json [--json]

# 4. Insert clip onto track
hyperedit timeline insert my_edit.json \
  --track V1 --asset cam_a --in 0 --out 90 --start 0 [--ripple]

# 5. Split clip at frame 45
hyperedit timeline split my_edit.json --track V1 --clip clip_cam_a_0 --frame 45

# 6. Trim clip
hyperedit timeline trim my_edit.json --track V1 --clip clip_cam_a_0_p1 --out 40 [--ripple]

# 7. Ripple delete clip
hyperedit timeline delete my_edit.json --track V1 --clip clip_cam_a_0_p2 --ripple

# 8. Close gaps on track
hyperedit timeline close-gaps my_edit.json --track V1

# 9. Render final master video
hyperedit render my_edit.json -o final_master.mp4 --preset web_1080p
```

