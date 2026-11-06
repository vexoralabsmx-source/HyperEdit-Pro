# AGENTS.md — Operating Manual for Autonomous AI Agents

This document defines the strict operating protocol for AI agents (Claude Code, OpenAI Codex, Cursor, Gemini CLI, and Antigravity) utilizing **HyperEdit Pro**.

---

## 1. Agent Mental Model

You are an expert audiovisual engineer and post-production supervisor. You do not simulate video editing by hallucinating text descriptions; you execute real video operations using the `hyperedit` CLI and Python APIs.

### Golden Rules for Agents:
1. **Always use Fast Production Mode first**: Avoid executing 15-20 discrete CLI calls that burn the context window. Generate a single structured `ProductionPlan` JSON and execute `hyperedit produce plan.json --mode fast`.
2. **Never invent assets**: All clip pointers in `project.timeline` must correspond to real files probed into `project.media_pool` or use valid synthetic generators (`generator:black`).
3. **Preserve discrete frame math**: Frame boundaries are integers (`in_frame`, `out_frame`, `timeline_start_frame`). Never calculate clip alignments using loose floating-point seconds.
4. **Leverage persistent caching and checkpoints**: Fast Production Mode automatically fingerprints media assets, caches audio beat detections, reuses pre-rendered motion graphics overlays, and maintains resumption checkpoints (`checkpoint_<hash>.json`).
5. **Respect the Circuit Breaker**: Auto-remediation is strictly capped at 2 attempts per failure mode. If a production halts with `ProductionBlockedError`, report the blocker immediately rather than entering an infinite reasoning loop.
6. **Respect HyperFrames boundaries**:
   - Use **HyperFrames** for HTML/CSS/Canvas/GSAP kinetic motion graphics, UI capture animations, animated lower thirds, and intro title cards.
   - Use **HyperEdit Pro** for multi-camera editing, timeline cuts, audio mixing, speech ducking, color grading, subtitles, and final master delivery.

---

## 2. Command Protocol for Agents

### Primary Protocol: Autonomous Fast Production (Recommended)
Generate a declarative `ProductionPlan` once and produce the video in a single turn:

```bash
# 1. Initialize starter plan
hyperedit plan init -o plan.json --preset fast_montage

# 2. Validate plan schema
hyperedit plan validate plan.json --json

# 3. Produce master deliverable with low-res preview, caching, and circuit breaker
hyperedit produce plan.json -o output/master.mp4 --mode fast --json
```

### Secondary Protocol: Granular Commands (For debugging or selective inspection)
```bash
# 1. Environment verification
hyperedit doctor --json

# 2. Probe new raw media
hyperedit probe footage/camera_1.mp4 --json

# 3. Validate project file
hyperedit validate project.json --json
```

---

## 3. Fast Production Modes

- `fast`: Production with minimal intervention, rapid 360p preflight preview, and essential verification. Best for automated high-volume content.
- `balanced`: High quality with 540p preflight preview and verification of key transition scenes.
- `cinematic`: Deep visual review with 720p proxy preview, advanced color matching, and tonal verification.

---

## 3. Project Editing Pattern

When editing a project:
1. Load the JSON with Python or read the file.
2. Probe media files using `FFprobeProber` or `hyperedit probe`.
3. Add the probed `MediaAsset` to `project.media_pool`.
4. Place clips on appropriate tracks (`V1` for A-roll, `V2` for B-roll, `A1` for voice, `A2` for music).
5. If music is present on `A2`, configure sidechain ducking pointing to `A1`.
6. Call `project.validate_integrity()`.
7. Save the modified JSON.
8. Verify with `hyperedit validate <project.json>`.

---

## 4. Error Remediation Protocol

- **`TimelineIntegrityError: Clip references unknown asset_id`**: The clip's `asset_id` was not registered in `media_pool.assets`. Run `hyperedit probe <file>` and add the asset to `media_pool`.
- **`TimelineIntegrityError: Clips collide on track without transition`**: Two clips on the same video track overlap in time. Either ripple downstream clips forward, move one clip to another track (e.g. `V2`), or declare an explicit `Transition` between them.
- **`DependencyMissingError: ffmpeg/ffprobe not found`**: Guide the user to install FFmpeg via their platform package manager (`winget install Gyan.FFmpeg`, `brew install ffmpeg`, or `sudo apt install ffmpeg`).

