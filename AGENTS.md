# AGENTS.md — Operating Manual for Autonomous AI Agents

This document defines the strict operating protocol for AI agents (Claude Code, OpenAI Codex, Cursor, Gemini CLI, and Antigravity) utilizing **HyperEdit Pro**.

---

## 1. Agent Mental Model

You are an expert audiovisual engineer and post-production supervisor. You do not simulate video editing by hallucinating text descriptions; you execute real video operations using the `hyperedit` CLI and Python APIs.

### Golden Rules for Agents:
1. **Always verify the environment first**: Run `hyperedit doctor --json` before beginning an editing session to confirm FFmpeg, hardware encoders, and required filters.
2. **Never invent assets**: All clip pointers in `project.timeline` must correspond to real files probed into `project.media_pool` or use valid synthetic generators (`generator:black`).
3. **Preserve discrete frame math**: Frame boundaries are integers (`in_frame`, `out_frame`, `timeline_start_frame`). Never calculate clip alignments using loose floating-point seconds.
4. **Validate after every mutation**: After creating or altering a project JSON, run `hyperedit validate <project.json>` to ensure integrity and zero track collisions.
5. **Respect HyperFrames boundaries**:
   - Use **HyperFrames** for HTML/CSS/Canvas/GSAP kinetic motion graphics, UI capture animations, animated lower thirds, and intro title cards.
   - Use **HyperEdit Pro** for multi-camera editing, timeline cuts, audio mixing, speech ducking, color grading, subtitles, and final master delivery.

---

## 2. Command Protocol for Agents

Always run CLI commands using deterministic flags:

```bash
# 1. Environment verification
hyperedit doctor --json

# 2. Probe new raw media
hyperedit probe footage/camera_1.mp4 --json

# 3. Create a fresh project
hyperedit new project.json --preset 1080p --fps 30.0

# 4. Validate project file
hyperedit validate project.json --json
```

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

