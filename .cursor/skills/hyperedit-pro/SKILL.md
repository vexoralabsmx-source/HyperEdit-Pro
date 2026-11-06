---
name: hyperedit-pro
description: >
  Professional audiovisual post-production and non-linear editing (NLE) skill for AI agents.
  Provides frame-accurate timeline editing, multi-track audio mixing (EBU R128), sidechain ducking,
  captions/subtitles, color grading, VFX, scene/silence intelligence, QA, and hardware-accelerated
  FFmpeg renders. Complementary to HyperFrames.
---

# HyperEdit Pro — Audiovisual Post-Production & NLE Skill

HyperEdit Pro equips AI agents with professional, executable audiovisual editing capabilities. It directly operates FFmpeg, FFprobe, hardware encoders, and audio DSP pipelines to perform real video cuts, multi-track audio mixing, color correction, and master delivery.

---

## 1. When to Use HyperEdit Pro vs HyperFrames

Apply this routing rule to determine which tool or workflow owns the deliverable:

| Scenario / Task | Tool / Skill to Use |
| :--- | :--- |
| Trimming, cutting, slicing, or assembling camera footage and audio tracks | **HyperEdit Pro** |
| Multi-track audio mixing, dialogue leveling, BGM ducking, EBU R128 loudness | **HyperEdit Pro** |
| Adding burned-in or styled subtitles from transcripts | **HyperEdit Pro** |
| Color grading footage with 3D LUTs (.cube) or ASC-CDL color adjustments | **HyperEdit Pro** |
| Detecting scene cuts or removing audio silences (jump-cutting podcasts) | **HyperEdit Pro** |
| Audiovisual QA (verifying black frames, freeze frames, audio clipping) | **HyperEdit Pro** |
| Creating animated lower-thirds, kinetic typography, UI captures, or HTML motion graphics | **HyperFrames** (`/hyperframes`) |
| Compositing a HyperFrames motion graphic over edited video footage | **Both**: HyperFrames renders transparent ProRes 4444, HyperEdit Pro layers it onto track `GRAPHIC` |
| Motion tracking objects or stabilizing shaky camera footage | **HyperEdit Pro** (`hyperedit vfx track / stabilize`) |
| Chroma keying green/blue screen with alpha channel export | **HyperEdit Pro** (`hyperedit vfx key`) |
| Applying cinematic effects (film grain, camera shake, bloom, motion blur) | **HyperEdit Pro** (`hyperedit vfx effect`) |
| Rendering headless 3D scenes via Blender | **HyperEdit Pro** (`BlenderAdapter` / `hyperedit vfx blender-check`) |

---

## 2. Core CLI Commands

The `hyperedit` CLI is installed locally and executable across Windows, macOS, and Linux:

```bash
# Verify environment and hardware acceleration encoders
hyperedit doctor [--json] [--verbose]

# Display version and project schema specification
hyperedit version [--json]

# Deeply probe an audiovisual media file
hyperedit media probe <media_file> [--json] [--hash]

# Validate file health, readability, and corruption status
hyperedit media validate <media_file> [--json]

# Import file into project with automated proxy, waveform, thumbnail and signal metrics
hyperedit media import <project.json> <media_file> [--proxy] [--waveform] [--thumbnail] [--contact-sheet] [--extract-audio] [--signal-metrics]

# Generate standalone artifacts
hyperedit media thumbnail <media_file> -o <thumb.jpg> [--time 0.0]
hyperedit media contact-sheet <media_file> -o <sheet.jpg> [--cols 3] [--rows 3]
hyperedit media waveform <media_file> -o <waveform.png>
hyperedit media proxy <media_file> -o <proxy.mp4> [--scale 720p]
hyperedit media extract-audio <media_file> -o <stem.wav>
hyperedit media signal-metrics <media_file> [--json]

# Create a new boilerplate project
hyperedit project create <project.json> [--preset 1080p|vertical_1080p|4k|square] [--fps 30.0]

# Inspect and validate timeline
hyperedit timeline inspect <project.json> [--json]
hyperedit timeline validate <project.json> [--json]

# Timeline editing operations
hyperedit timeline insert <project.json> --track V1 --asset <asset_id> --in 0 --out 90 --start 0 [--ripple]
hyperedit timeline split <project.json> --track V1 --clip <clip_id> --frame 45
hyperedit timeline trim <project.json> --track V1 --clip <clip_id> [--in 10] [--out 80] [--ripple]
hyperedit timeline delete <project.json> --track V1 --clip <clip_id> [--ripple]
hyperedit timeline close-gaps <project.json> --track V1

# Audio engineering, beat tracking, ducking, and loudness
hyperedit audio beats <music_file> [--bpm-hint 120] [--json]
hyperedit audio markers <project.json> <music_file> [--color "#FF00AA"]
hyperedit audio snap <project.json> <music_file> --track V1 [--max-shift 8] [--mode ripple] [--json]
hyperedit audio loudness <audio_or_video_file> [--profile youtube] [--json]
hyperedit audio normalize <input_file> <output_file> [--profile youtube] [--sample-rate 48000]
hyperedit audio duck <music_file> <dialogue_file> -o <ducked.wav> [--threshold -20] [--ratio 4.0]
hyperedit audio mix <project.json> -o <master.wav> [--profile youtube]

# Captions, subtitles, and kinetic typography
hyperedit captions import <subtitles_file> [--preset modern_bold] [--json]
hyperedit captions export <subtitles_file> -o <output_file> [--format srt|vtt|ass] [--preset netflix]
hyperedit captions kinetic <subtitles_file> -o <kinetic.ass> [--mode karaoke_highlight|pop_scale] [--preset tiktok_reels_neon]
hyperedit captions burn <video_file> <subtitles_file> -o <burned.mp4> [--preset modern_bold]
hyperedit captions transcribe <media_file> -o <captions.srt> [--model base] [--language en]
hyperedit captions hyperframes <subtitles_file> -o <captions.html> [--preset modern_bold]
hyperedit captions validate <subtitles_file> [--json]

# Motion graphics and HyperFrames integration
hyperedit motion presets [--json]
hyperedit motion create <template> -o <output.html> [--title <str>] [--preset cinematic_luxury]
hyperedit motion sync <composition.html> <audio_file> -o <synced.html> [--bpm-hint 120]
hyperedit motion render <composition.html> -o <overlay.mov> [--format mov|webm] [--fps 30.0]
hyperedit motion overlay <project.json> <overlay.mov> [--track GRAPHIC] [--start-frame 0]

# Visual effects, tracking, compositing and 3D
hyperedit vfx track <video_file> --bbox <x,y,w,h> -o <tracking.json> [--method template|lk]
hyperedit vfx stabilize <video_file> -o <stabilized.mp4> [--smoothing 15] [--crop-border 0.05]
hyperedit vfx key <video_file> -o <keyed.mov> [--color 0x00FF00] [--similarity 0.3]
hyperedit vfx effect <video_file> -o <output.mp4> --effect [grain|shake|bloom|motion_blur] [--intensity 0.2]
hyperedit vfx blender-check [--json]

# Color correction, grading, histogram analysis, and shot matching
hyperedit color presets [--json]
hyperedit color grade <video_file> -o <graded.mp4> [--preset warm_editorial] [--strength 1.0] [--exposure 0.5]
hyperedit color analyze <media_file> [--json] [--histogram-output <chart.png>]
hyperedit color match <ref_file> <target_file> -o <matched.mp4> [--json]
hyperedit color audit <media_file> [--json]

# Render master deliverable
hyperedit render <project.json> -o final_master.mp4 [--preset web_1080p] [--hwaccel auto|none]
```

---

## 3. Workflow Recipes

### Recipe A: Initializing and Verifying an Edit
1. Check the local environment:
   ```bash
   hyperedit doctor --json
   ```
2. Probe all raw footage files to extract exact frame rates, dimensions, and audio sample rates:
   ```bash
   hyperedit probe footage/interview.mp4 --json
   hyperedit probe audio/music_bed.wav --json
   ```
3. Initialize the project with matching framerate and resolution:
   ```bash
   hyperedit new project.json --preset 1080p --fps 30.0
   ```

### Recipe B: Structuring Multi-Track Projects
Follow professional NLE track conventions:
- `V1`: Primary video (A-roll / host camera).
- `V2`: Secondary video / cutaways (B-roll / guest camera).
- `GRAPHIC`: Motion graphics overlays (e.g. HyperFrames animated titles and lower thirds).
- `A1`: Dialogue / vocal track (level target: -16 to -23 LUFS).
- `A2`: Background music (BGM) with sidechain ducking pointing to `A1`.
- `A3`: Sound effects (SFX) / Foley.
- `SUB1`: Subtitle cues with typographic styling.

### Recipe C: Validating Project Integrity
Before any export, validate structural consistency:
```bash
hyperedit validate project.json
```
The validator checks:
- All referenced asset IDs exist in `media_pool`.
- Every clip satisfies `out_frame > in_frame`.
- No colliding clips exist on the same video track unless an explicit transition is declared.

### Recipe D: Beat Synchronization & Sidechain Ducking
1. Detect tempo and inject beat markers onto timeline:
   ```bash
   hyperedit audio markers project.json soundtrack.mp3 --color "#FF00AA"
   ```
2. Automatically snap video cuts on `V1` to nearest musical beats within 8 frames:
   ```bash
   hyperedit audio snap project.json soundtrack.mp3 --track V1 --max-shift 8 --mode ripple
   ```
3. Mix dialogue on `A1` with ducked background music on `A2` and normalize master to YouTube (-14 LUFS):
   ```bash
   hyperedit audio mix project.json -o master_audio.wav --profile youtube --sample-rate 48000
   ```

### Recipe E: Kinetic Typography & Subtitle Burn-In
1. Audit pacing and readability of subtitle cues:
   ```bash
   hyperedit captions validate subtitles.srt
   ```
2. Generate word-level kinetic typography script (e.g. TikTok/Reels neon preset with karaoke highlight):
   ```bash
   hyperedit captions kinetic subtitles.srt -o kinetic.ass --mode karaoke_highlight --preset tiktok_reels_neon
   ```
3. Burn kinetic typography directly into master video:
   ```bash
   hyperedit captions burn raw_video.mp4 kinetic.ass -o final_video_subbed.mp4
   ```
4. Alternatively, export as HyperFrames HTML motion graphic:
   ```bash
   hyperedit captions hyperframes subtitles.srt -o captions_overlay.html --preset modern_bold
   ```

### Recipe F: Motion Graphics & HyperFrames Transparent Overlays
1. Generate an official HyperFrames HTML motion graphic (e.g. cinematic intro with luxury art direction):
   ```bash
   hyperedit motion create cinematic_intro -o title.html --title "THE HORIZON" --preset cinematic_luxury
   ```
2. Synchronize visual pulsations to soundtrack beats:
   ```bash
   hyperedit motion sync title.html music_bed.mp3 -o title_synced.html
   ```
3. Render transparent ProRes 4444 overlay (`.mov` with alpha channel):
   ```bash
   hyperedit motion render title_synced.html -o overlay.mov --format mov --fps 30.0
   ```
4. Attach directly onto the project timeline on track `GRAPHIC`:
   ```bash
   hyperedit motion overlay project.json overlay.mov --track GRAPHIC --start-frame 0
   ```
5. Render the final composite deliverable:
   ```bash
   hyperedit render project.json -o final_film_with_motion.mp4
   ```

### Recipe G: Visual Effects, Tracking & Chroma Keying
1. Track a moving object in a video clip to obtain motion coordinates:
   ```bash
   hyperedit vfx track footage.mp4 --bbox 120,80,60,60 -o tracking.json
   ```
2. Stabilize shaky camera footage using 2D trajectory smoothing:
   ```bash
   hyperedit vfx stabilize footage.mp4 -o stabilized.mp4 --smoothing 15
   ```
3. Key out green screen background into a transparent Apple ProRes 4444 video:
   ```bash
   hyperedit vfx key greenscreen.mp4 -o keyed_actor.mov --color 0x00FF00 --similarity 0.3
   ```
4. Layer the keyed actor over background footage on the timeline and apply film grain:
   ```bash
   hyperedit vfx effect raw_master.mp4 -o cinema_grain.mp4 --effect grain --intensity 0.18
   ```

### Recipe H: Professional Color Grading & Shot Matching
1. Audit input color space and SDR Rec.709 legality:
   ```bash
   hyperedit color audit raw_footage.mp4
   ```
2. Analyze luminance histogram, dynamic range, and shadow/highlight clipping:
   ```bash
   hyperedit color analyze raw_footage.mp4 --histogram-output histogram.png
   ```
3. Match an underexposed or cool shot to a warm reference shot:
   ```bash
   hyperedit color match hero_shot.mp4 secondary_shot.mp4 -o secondary_matched.mp4
   ```
4. Apply a cinematographic film stock preset look:
   ```bash
   hyperedit color grade secondary_matched.mp4 -o final_graded.mp4 --preset film_stock_5207 --strength 0.85
   ```

---

## 4. References & Documentation

- [Color Grading & Tonal Engine Guide](references/COLOR_GRADING_GUIDE.md): Color correction controls, ASC-CDL, 3D LUTs (.cube), shot matching, and SDR/HDR management.
- [VFX, Tracking & 3D Integration Guide](references/VFX_AND_TRACKING_GUIDE.md): OpenCV tracking algorithms, stabilization, masks, chroma keying, cinematic effects, and Blender adapter.
- [Motion Graphics & HyperFrames Guide](references/MOTION_GRAPHICS_GUIDE.md): HyperFrames contract, keyframe math, Ken Burns camera, and transparent overlay rendering.
- [Captions & Kinetic Typography Guide](references/CAPTIONS_AND_TYPOGRAPHY_GUIDE.md): Format conversions, kinetic typography, safe areas & presets.
- [Audio Engineering & Beat Sync Guide](references/AUDIO_ENGINE_GUIDE.md): Beat detection, snapping telemetry, sidechain ducking & loudness.
- [Project Format Specification](references/PROJECT_FORMAT.md): Detailed JSON schema definitions.
- [CLI Reference](references/CLI_REFERENCE.md): Full flag descriptions and exit codes.
- [Filtergraph Architecture](references/FILTERGRAPH_ARCHITECTURE.md): FFmpeg complex filter generation model.
- [Engineering Roadmap](ROADMAP.md): Milestones for Phases 1 through 10.

