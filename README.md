# HyperEdit Pro 🎬

> **Autonomous Audiovisual Post-Production & Non-Linear Editing (NLE) Engine for AI Agents, Complementary to HyperFrames.**

[![CI](https://github.com/vexoralabsmx-source/HyperEdit-Pro/actions/workflows/ci.yml/badge.svg)](https://github.com/vexoralabsmx-source/HyperEdit-Pro/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-vexoralabsmx--source%2FHyperEdit--Pro-181717?logo=github)](https://github.com/vexoralabsmx-source/HyperEdit-Pro)
[![Agent Skills](https://img.shields.io/badge/Standard-Agent%20Skills%20v1.0-8A2BE2)](SKILL.md)

[English](README.md) | [Español](README_ES.md)

---

## 1. What is HyperEdit Pro?

**HyperEdit Pro** is an open-source, non-destructive audiovisual post-production engine built specifically for autonomous AI coding agents (**Codex**, **Claude Code**, **Cursor**, **Gemini CLI** / **Antigravity**). 

Unlike prompt-based simulations that hallucinate video operations, HyperEdit Pro provides genuine, executable software tools. It directly operates **FFmpeg**, **FFprobe**, **OpenCV**, and hardware encoders through a versioned JSON timeline specification (`schema_version: 2.0.0`).

### Core Design Principles:
- **No Hallucinated Tools**: All edits, audio mixes, kinetic captions, color grades, and renders execute real code verified against signal telemetry.
- **Discrete Frame Math**: Integer frame boundaries (`in_frame`, `out_frame`, `timeline_start_frame`) prevent cumulative floating-point timing drift.
- **Source Immutability**: Raw footage and audio files are never modified in-place; all operations are non-destructive.
- **Local-First Operation**: Runs completely on local CPU/GPU hardware without mandatory cloud dependencies.

---

## 2. Implemented Capabilities Matrix

| Subsystem | Capabilities | Status |
| :--- | :--- | :--- |
| **Media Engine** | FFprobe multi-stream inspection (CFR/VFR 23.976–60 fps), thumbnails, contact sheets, waveform visualization PNGs, 720p editing proxies, atomic caching. | ✅ Operational |
| **Timeline & Editing** | Multi-track timeline (`V1`–`V2`, `A1`–`A3`, `GRAPHIC`), cuts, ripple/overwrite inserts, splits, trims, ripple delete, transitions (`xfade`), reversible undo/redo history. | ✅ Operational |
| **Audio Engineering** | Streaming acoustic beat tracking (BPM & onsets), cut snapping to beats, multi-track mixing, sidechain ducking (`sidechaincompress`), EBU R128 loudness normalization. | ✅ Operational |
| **Captions & Kinetic Typography** | SRT/VTT/ASS parsing, ASS v4.00+ typographic compilation, kinetic word highlighting (`karaoke_highlight`, `pop_scale`, `word_reveal`), local `faster-whisper` transcription. | ✅ Operational |
| **Motion Graphics (HyperFrames)** | Official HyperFrames composition contract (`data-composition-id`, `window.__timelines`), 6 curated art direction presets, cubic Bézier & damped spring keyframes, Ken Burns camera, transparent ProRes 4444 export. | ✅ Operational |
| **VFX & Tracking** | Normalized cross-correlation template tracking, Lucas-Kanade optical flow, 2D affine video stabilization, animated masks with Gaussian feathering, chroma keying, film grain, camera shake, bloom, and headless Blender 3D integration. | ✅ Operational |
| **Color Grading** | Exposure in EV stops, contrast, saturation, vibrance, black/white point roll-off, normalized chromaticity white balance (temp/tint), 3-way color wheels, ASC-CDL, `.cube` 3D LUT parser/interpolator, and automated shot matching. | ✅ Operational |

---

## 3. HyperEdit Pro vs HyperFrames

HyperEdit Pro is designed as the non-destructive editing counterpart to **HyperFrames**:

```
┌──────────────────────────────────────────────────────────┐
│                   CREATIVE WORKFLOW                      │
├─────────────────────────────┬────────────────────────────┤
│         HYPERFRAMES         │       HYPEREDIT PRO        │
│   (Kinetic Motion Engine)   │   (NLE Post-Production)    │
├─────────────────────────────┼────────────────────────────┤
│ • HTML/CSS/GSAP Animation   │ • Multi-camera editing     │
│ • UI Capture & Title Cards  │ • Trimming, ripple cuts    │
│ • Animated Lower-Thirds     │ • Audio ducking & EBU R128 │
│ • 2D/3D Kinetic Graphics    │ • Chroma keying & VFX      │
│ • Renders Transparent .mov  │ • Color grading & 3D LUTs  │
└──────────────┬──────────────┴─────────────┬──────────────┘
               │                            │
               └────────► [COMPOSITOR] ◄────┘
               Rendered ProRes 4444 overlay
               layered on track 'GRAPHIC'
```

---

## 4. Installation

### Requirements
- **Python**: $\ge 3.11$
- **FFmpeg & FFprobe**: $\ge 5.0$ installed and available in system `PATH`.
- **Git**

### Standard Installation
```bash
# Clone repository
git clone https://github.com/vexoralabsmx-source/HyperEdit-Pro.git
cd HyperEdit-Pro

# Install in editable mode
pip install -e .

# Or install with vision (OpenCV for tracking and chroma keying)
pip install -e ".[vision]"

# Install all optional dependencies (ASR transcription, scene detect, vision)
pip install -e ".[all]"
```

---

## 5. Agent Skills Setup (Codex, Claude, Cursor, Gemini)

HyperEdit Pro complies with the **Agent Skills standard** (`SKILL.md`). You can install it into any agent with one command:

```bash
# Install skill for all detected agent environments in current workspace
python scripts/install_skill.py --agent all --workspace .

# Or install globally for all sessions on your system:
python scripts/install_skill.py --agent all --global
```

- **OpenAI Codex**: Discovers `<workspace>/.codex/skills/hyperedit-pro/SKILL.md` or `~/.codex/skills/`.
- **Claude Code**: Discovers `<workspace>/.claude/skills/hyperedit-pro/SKILL.md` or `~/.claude/skills/`.
- **Cursor**: Discovers `<workspace>/.cursor/skills/hyperedit-pro/SKILL.md`.
- **Gemini CLI / Antigravity**: Discovers `~/.gemini/antigravity/skills/hyperedit-pro/` or `~/.agents/skills/`.

For complete details, see [docs/AGENT_INSTALLATION.md](docs/AGENT_INSTALLATION.md).

---

## 6. Environment Diagnostics

Verify local dependencies, hardware encoders, and filters before editing:

```bash
hyperedit doctor --verbose
```

For AI agents requiring machine-readable output:
```bash
hyperedit doctor --json
```

---

## 7. CLI Quick Start

### 1. Initialize a Project
```bash
hyperedit project create my_vlog.json --preset 1080p --fps 30.0
```

### 2. Probe Media Files
```bash
hyperedit media probe footage/interview.mp4 --json
```

### 3. Synchronize Cuts to Audio Beats
```bash
hyperedit audio snap my_vlog.json audio/soundtrack.mp3 --track V1 --max-shift 8 --mode ripple
```

### 4. Apply Subtitles with Word Highlighting
```bash
hyperedit captions transcribe audio/dialogue.wav -o subs.srt --model base
hyperedit captions kinetic subs.srt -o kinetic.ass --mode karaoke_highlight --preset tiktok_reels_neon
hyperedit captions burn footage.mp4 kinetic.ass -o subbed.mp4
```

### 5. Color Grade & Match Shots
```bash
# Match target shot tonal consistency to reference shot
hyperedit color match hero.mp4 b_roll.mp4 -o b_roll_matched.mp4

# Apply curated 35mm film stock preset look
hyperedit color grade b_roll_matched.mp4 -o final_graded.mp4 --preset film_stock_5207 --strength 0.85
```

### 6. Render Master Deliverable
```bash
hyperedit render my_vlog.json -o final_master.mp4 --preset web_1080p --hwaccel auto
```

---

## 8. Current Limitations & Boundaries

- **GPU Acceleration**: Hardware encoders (NVENC, VideoToolbox, QSV) are automatically detected; if drivers are missing at runtime, HyperEdit Pro safely falls back to CPU encoding (`libx264`).
- **Neural Rotoscoping**: Deep learning segmentation models (e.g. SAM) require dedicated external weights; native rotoscoping operates via bounding-box GrabCut.
- **3D Integration**: Blender integration requires local installation of the `blender` executable; HyperEdit Pro drives headless rendering via CLI but does not simulate a 3D engine in Python.

---

## 9. Documentation

- [Operating Manual for AI Agents](AGENTS.md)
- [Agent Skill Specification](SKILL.md)
- [CLI Reference Manual](references/CLI_REFERENCE.md)
- [Color Grading & Tonal Engine Guide](references/COLOR_GRADING_GUIDE.md)
- [VFX, Tracking & 3D Integration Guide](references/VFX_AND_TRACKING_GUIDE.md)
- [Motion Graphics & HyperFrames Guide](references/MOTION_GRAPHICS_GUIDE.md)
- [Captions & Kinetic Typography Guide](references/CAPTIONS_AND_TYPOGRAPHY_GUIDE.md)
- [Audio Engineering & Beat Sync Guide](references/AUDIO_ENGINE_GUIDE.md)
- [Project Format Specification](references/PROJECT_FORMAT.md)
- [Filtergraph Compiler Architecture](references/FILTERGRAPH_ARCHITECTURE.md)
- [Engineering Roadmap](ROADMAP.md)

---

## 10. Contributing

We welcome community contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for our pull request process, code standards, and testing protocols.

---

## 11. License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details. Proposed for community approval.
