# HyperEdit Pro CLI Reference

## 1. Global Options

```bash
hyperedit [OPTIONS] COMMAND [ARGS]...
```

- `-h, --help`: Show help message and command list.
- `--version`: Display CLI version and project schema specification.

---

## 2. Command: `hyperedit doctor`

Performs an exhaustive audit of the local environment, runtime binaries, hardware acceleration encoders, and audio/video filters.

```bash
hyperedit doctor [OPTIONS]
```

### Options
- `--json`: Output full diagnostic payload as machine-readable JSON.
- `-v, --verbose`: Display detailed properties for each diagnostic item.
- `--strict`: Terminate with exit code `2` if warnings are present (e.g. missing optional AI packages).

### Exit Codes
- `0`: All required dependencies operational.
- `1`: Critical error (FFmpeg/FFprobe missing, Python < 3.11).
- `2`: Warnings present when `--strict` is enabled.

---

## 3. Command: `hyperedit version`

Prints the current engine version and schema specification.

```bash
hyperedit version [--json]
```

Example JSON output:
```json
{
  "hyperedit": "0.1.0",
  "schema_version": "2.0.0"
}
```

---

## 4. Command: `hyperedit new`

Scaffolds a new, structurally valid HyperEdit project file with default tracks.

```bash
hyperedit new <OUTPUT_FILE> [OPTIONS]
```

### Options
- `--title <TEXT>`: Project title string (default: `"New HyperEdit Project"`).
- `--preset [1080p|vertical_1080p|4k|square]`: Canvas aspect ratio and dimensions (default: `1080p`).
- `--fps <FLOAT>`: Base timeline frame rate (default: `30.0`).
- `--force`: Overwrite destination file if it already exists.

---

## 5. Command: `hyperedit validate`

Parses and validates a project JSON file against the Pydantic schema and timeline integrity rules.

```bash
hyperedit validate <PROJECT_FILE> [OPTIONS]
```

### Options
- `--json`: Output validation report in JSON.

### Integrity Checks Performed
1. JSON syntax validity.
2. Pydantic v2 schema conformity.
3. Media asset ID pointer resolution in `media_pool`.
4. Clip in-point / out-point frame ordering (`out_frame > in_frame`).
5. Track clip collision detection (overlapping clips without transitions).

---

## 6. Command Group: `hyperedit media`

The Professional Media Engine command suite for probing, validating, importing, and generating artifacts.

### 6.1 `hyperedit media probe <file>`
Deeply inspects media files using `ffprobe` and outputs technical telemetry.
- `--json`: Output full telemetry as structured JSON (`ComprehensiveMediaAsset`).
- `--hash`: Compute SHA-256 asset checksum.

### 6.2 `hyperedit media validate <file>`
Audits files for corruption, truncations, and compatibility.
- `--json`: Output report as JSON (`MediaValidationReport`).

### 6.3 `hyperedit media import <project.json> <media_file>`
Executes end-to-end import: validation -> cached probe -> artifact generation -> project media pool registration.
- `--proxy`: Create editing proxy.
- `--proxy-scale [720p|540p|360p]`: Resolution scale of editing proxy (default: `720p`).
- `--thumbnail`: Extract single-frame thumbnail.
- `--contact-sheet`: Create 3x3 mosaic storyboard sheet.
- `--waveform`: Generate audio waveform visualization.
- `--extract-audio`: Extract uncompressed audio stem (WAV).
- `--signal-metrics`: Analyze peak volume, RMS level, dynamic range, and silent sections.
- `-o, --output <file>`: Save modified project to a new JSON path instead of updating in-place.
- `--json`: Output imported asset metadata as JSON.

### 6.4 `hyperedit media thumbnail <media_file> -o <thumb.jpg>`
- `--time <sec>`: Timestamp offset in seconds.
- `--width <px>`: Thumbnail width in pixels (default: 480).

### 6.5 `hyperedit media contact-sheet <media_file> -o <sheet.jpg>`
- `--cols <int>`: Grid columns (default: 3).
- `--rows <int>`: Grid rows (default: 3).
- `--tile-width <px>`: Individual tile width (default: 320).

### 6.6 `hyperedit media waveform <media_file> -o <waveform.png>`
- `--width <px>`: Output image width (default: 1920).
- `--height <px>`: Output image height (default: 240).
- `--color <hex>`: Waveform color (default: `0x00FF88`).

### 6.7 `hyperedit media proxy <media_file> -o <proxy.mp4>`
- `--scale [720p|540p|360p]`: Target scale.
- `--crf <int>`: Constant Rate Factor (default: 24).

### 6.8 `hyperedit media extract-audio <media_file> -o <audio.wav>`
- `--format [wav|flac|mp3]`: Output audio format (default: `wav`).
- `--sample-rate <int>`: Sample rate in Hz (default: 48000).
- `--channels [1|2]`: 1 (mono) or 2 (stereo).

### 7. Command Group: `hyperedit timeline`

### 7.1 `hyperedit timeline inspect <project.json>`
Visually displays timeline tracks, active clips, timecodes, framerates, transitions, and collision warnings.
- `--json`: Output inspection telemetry as JSON.

### 7.2 `hyperedit timeline validate <project.json>`
Audits timeline tracks for unauthorized overlapping collisions and bounds errors.
- `--json`: Output validation result as JSON.

### 7.3 `hyperedit timeline insert <project.json>`
- `--track <id>`: Target track ID (e.g. `V1`, `V2`, `A1`).
- `--asset <id>`: Registered media asset ID.
- `--in <frame>`: Source media in-point frame index.
- `--out <frame>`: Source media out-point frame index.
- `--start <frame>`: Timeline start frame index.
- `--speed <float>`: Playback speed multiplier (default: 1.0).
- `--ripple`: Enable ripple mode (shifts downstream clips forward).

### 7.4 `hyperedit timeline split <project.json>`
- `--track <id>`: Track ID containing the clip.
- `--clip <id>`: Clip ID to split.
- `--frame <frame>`: Timeline frame index where cut occurs.

### 7.5 `hyperedit timeline trim <project.json>`
- `--track <id>`: Track ID.
- `--clip <id>`: Clip ID.
- `--in <frame>`: New source in-point frame index.
- `--out <frame>`: New source out-point frame index.
- `--ripple`: Ripple downstream clips to match adjusted length.

### 7.6 `hyperedit timeline delete <project.json>`
- `--track <id>`: Track ID.
- `--clip <id>`: Clip ID.
- `--ripple`: Pull downstream clips backward to eliminate resulting gap.

### 7.7 `hyperedit timeline close-gaps <project.json>`
- `--track <id>`: Track ID on which to close all temporal gaps between clips.

---

## 8. Command: `hyperedit render`

Compiles the multi-track timeline into an FFmpeg `-filter_complex` execution graph and encodes a playable master video file.

```bash
hyperedit render <PROJECT_FILE> -o <OUTPUT_FILE> [OPTIONS]
```

### Options
- `-o, --output <path>`: Destination video path (e.g. `output.mp4`).
- `--preset <name>`: Delivery preset (`web_1080p`, `reels_vertical`, `prores_422hq`).
- `--hwaccel [auto|none|nvenc]`: Hardware acceleration selector.
- `--dry-run`: Output compiled FFmpeg filtergraph string without executing render.

---

## 9. Command Group: `hyperedit audio`

Provides intelligent audio engineering, acoustic beat tracking, timeline snapping, sidechain ducking, and EBU R128 loudness normalization.

### 9.1 `hyperedit audio beats <file>`
Analyzes raw acoustic PCM signal to detect BPM, beat grid timestamps, and transient onsets.
- `--bpm-hint <float>`: Expected tempo hint to assist autocorrelation.
- `--override <float>`: Force explicit BPM override.
- `--json`: Output structured JSON telemetry payload.

### 9.2 `hyperedit audio markers <project.json> <audio_file>`
Analyzes audio beats and injects temporal markers into project timeline.
- `--color <hex>`: Marker color (default: `#FF00AA`).
- `--clear / --no-clear`: Clear existing beat markers prior to injection (default: clear).
- `--bpm-hint <float>`: Expected tempo hint.
- `--json`: Output JSON telemetry.

### 9.3 `hyperedit audio snap <project.json> <audio_file>`
Snaps edit cuts on a specified track (e.g. `V1`) to nearest musical beats within frame tolerance.
- `--track <id>`: Target track ID (default: `V1`).
- `--max-shift <int>`: Maximum allowed frame shift in either direction (default: `8`).
- `--mode [ripple|roll]`: Snapping edit mode (default: `ripple`).
- `--bpm-hint <float>`: Expected tempo hint.
- `--json`: Output detailed `BeatAlignmentReport` with ms/frame shift telemetry.

### 9.4 `hyperedit audio loudness <file>`
Measures acoustic integrated loudness (LUFS), True Peak (dBFS), and LRA via FFmpeg's `ebur128` filter.
- `--profile [youtube|spotify|apple_podcasts|ebu_r128|atsc_a85]`: Target platform standard (default: `youtube`).
- `--json`: Output structured JSON measurement.

### 9.5 `hyperedit audio normalize <input_file> <output_file>`
Applies broadcast-grade loudness normalization (`loudnorm`) to target platform standards.
- `--profile [youtube|spotify|apple_podcasts|ebu_r128|atsc_a85]`: Target standard (default: `youtube`).
- `--sample-rate <int>`: Target sample rate in Hz (default: `48000`).

### 9.6 `hyperedit audio duck <music_file> <dialogue_file> -o <output_file>`
Applies FFmpeg `sidechaincompress` ducking to attenuate background music during speech.
- `-o, --output <path>`: Destination audio path.
- `--threshold <float>`: Trigger speech detection threshold in dBFS (default: `-20.0`).
- `--ratio <float>`: Compression ratio when voice is present (default: `4.0`).
- `--attack <float>`: Attack time in milliseconds (default: `20.0`).
- `--release <float>`: Release time in milliseconds (default: `250.0`).
- `--mix / --music-only`: Mix dialogue into output or export ducked music bed only (default: mix).
- `--sample-rate <int>`: Sample rate in Hz (default: `48000`).

### 9.7 `hyperedit audio mix <project.json> -o <output_file>`
Mixes all project audio tracks (`A1`, `A2`, etc.) with trims, delays, ducking, and platform loudness into a master stem.
- `-o, --output <path>`: Destination master stem path.
- `--profile [youtube|spotify|apple_podcasts|ebu_r128|atsc_a85]`: Master bus loudness normalization.
- `--sample-rate <int>`: Master audio sample rate (default: `48000`).

---

## 10. Command Group: `hyperedit captions`

Provides parsing, conversion, styling, speech-to-text, and kinetic typography rendering.

### 10.1 `hyperedit captions import <file>`
Imports and inspects subtitle files (`.srt`, `.vtt`, `.ass`).
- `--preset [netflix|modern_bold|cinema_serif|tiktok_reels_neon|impact_pop|minimalist]`: Apply style preset.
- `--json`: Output full track JSON data.

### 10.2 `hyperedit captions export <file> -o <output>`
Converts and exports subtitle tracks across SRT, WebVTT, and ASS formats.
- `-o, --output <path>`: Output subtitle file.
- `--format [srt|vtt|ass]`: Target format (default: inferred from file extension).
- `--preset [name]`: Apply typographic styling preset when exporting to ASS.

### 10.3 `hyperedit captions burn <video_file> <subtitles_file> -o <output>`
Hardcodes/burns styled subtitles directly into a video file using FFmpeg and libass.
- `-o, --output <path>`: Destination video path (e.g. `output_burned.mp4`).
- `--preset [name]`: Typographic style preset (default: `modern_bold`).

### 10.4 `hyperedit captions transcribe <media_file> -o <output>`
Transcribes spoken audio using local `faster-whisper` models with word timestamps.
- `-o, --output <path>`: Output subtitle path (`.srt`, `.vtt`, or `.ass`).
- `--model [tiny|base|small|medium|large-v3]`: Whisper model size (default: `base`).
- `--language <code>`: Explicit ISO language code (e.g. `en`, `es`).
- `--preset [name]`: Typographic preset if outputting to ASS.

### 10.5 `hyperedit captions kinetic <subtitles_file> -o <output_ass>`
Generates an Advanced SubStation Alpha script with word-level synchronized kinetic animations.
- `-o, --output <path>`: Destination `.ass` file.
- `--mode [karaoke_highlight|pop_scale|word_reveal|fade_word|slide_up]`: Animation mode (default: `karaoke_highlight`).
- `--preset [name]`: Typographic styling preset (default: `tiktok_reels_neon`).

### 10.6 `hyperedit captions hyperframes <subtitles_file> -o <output_html>`
Exports subtitles as a standalone HyperFrames HTML/CSS/GSAP motion graphic composition.
- `-o, --output <path>`: Destination HTML path.
- `--preset [name]`: Typographic style preset (default: `modern_bold`).

### 10.7 `hyperedit captions validate <subtitles_file>`
Audits subtitle pacing, reading speed (CPS), line length (CPL), and temporal overlaps.
- `--json`: Output issues list as machine-readable JSON.

---

## 11. Command Group: `hyperedit motion`

Provides motion graphics creation, audio beat synchronization, transparent rendering, and timeline compositing.

### 11.1 `hyperedit motion presets`
Lists available motion art direction presets with typography, palettes, and easing curves.
```bash
hyperedit motion presets [--json]
```

### 11.2 `hyperedit motion create <template>`
Builds a renderable HyperFrames HTML/CSS/GSAP composition.
```bash
hyperedit motion create cinematic_intro -o title.html --title "THE HORIZON" --preset cinematic_luxury
```
- `<template>`: Template identifier (`cinematic_intro`, `product_showcase`, `audio_reactive`).
- `-o, --output <path>`: Destination `.html` composition file.
- `--title <text>`: Main headline or title text.
- `--subtitle <text>`: Secondary subtitle or descriptor.
- `--preset <name>`: Art direction preset (default: `cinematic_luxury`).
- `--width <int>`: Composition width in pixels (default: `1920`).
- `--height <int>`: Composition height in pixels (default: `1080`).
- `--duration <float>`: Total duration in seconds (default: `4.0`).

### 11.3 `hyperedit motion sync <composition_html> <audio_file>`
Analyzes real audio beat onsets and injects beat-reactive pulsation keyframes into the composition HTML.
```bash
hyperedit motion sync title.html soundtrack.mp3 -o title_synced.html
```
- `-o, --output <path>`: Synced output HTML file.
- `--bpm-hint <float>`: Optional tempo hint for beat tracking.

### 11.4 `hyperedit motion render <composition_file>`
Renders a motion composition into a video overlay with an authentic alpha channel.
```bash
hyperedit motion render title_synced.html -o overlay.mov --format mov --fps 30.0
```
- `-o, --output <path>`: Destination video file (`.mov` or `.webm`).
- `--format [mov|webm|mp4]`: Output format (default: `mov`).
- `--fps <float>`: Target frame rate (default: `30.0`).

### 11.5 `hyperedit motion overlay <project_file> <overlay_video>`
Attaches a rendered motion graphic overlay directly onto the project timeline.
```bash
hyperedit motion overlay project.json overlay.mov --track GRAPHIC --start-frame 0
```
- `--track <id>`: Destination graphic track ID (default: `GRAPHIC`).
- `--start-frame <int>`: Timeline start frame index (default: `0`).

---

## 12. Command Group: `hyperedit vfx`

Provides computer vision motion tracking, video stabilization, chroma keying, cinematic effects and 3D integration.

### 12.1 `hyperedit vfx track <video_file>`
Tracks a moving region across video frames and outputs telemetry JSON with frame-by-frame coordinates, bounding boxes, and confidence scores.
```bash
hyperedit vfx track footage.mp4 --bbox 80,80,40,40 -o tracking.json [--method template|lk] [--max-frames 120]
```
- `--bbox <x,y,w,h>`: Initial bounding box on frame 0 in pixels.
- `-o, --output <path>`: Destination telemetry JSON file.
- `--method [template|lk]`: Tracking algorithm (default: `template`).

### 12.2 `hyperedit vfx stabilize <video_file>`
Stabilizes camera jitter using 2D rigid affine trajectory smoothing.
```bash
hyperedit vfx stabilize shaky.mp4 -o stabilized.mp4 [--smoothing 15] [--crop-border 0.05]
```
- `-o, --output <path>`: Stabilized video destination path.
- `--smoothing <int>`: Trajectory smoothing window size in frames (default: `15`).
- `--crop-border <float>`: Safe crop margin ratio to eliminate black border edges (default: `0.05`).

### 12.3 `hyperedit vfx key <video_file>`
Extracts green/blue screen background into a transparent ProRes 4444 QuickTime video with alpha channel.
```bash
hyperedit vfx key greenscreen.mp4 -o keyed.mov [--color 0x00FF00] [--similarity 0.3] [--smoothness 0.1]
```
- `-o, --output <path>`: Destination transparent video path (`.mov`).
- `--color <hex>`: Key color in hex format (default: `0x00FF00`).
- `--similarity <float>`: Tolerance distance threshold (default: `0.3`).
- `--smoothness <float>`: Edge transition smoothness ramp (default: `0.1`).

### 12.4 `hyperedit vfx effect <video_file>`
Renders a non-destructive cinematic visual effect onto footage.
```bash
hyperedit vfx effect raw.mp4 -o output.mp4 --effect [grain|shake|bloom|motion_blur] [--intensity 0.2]
```
- `--effect [grain|shake|bloom|motion_blur]`: Effect type.
- `--intensity <float>`: Effect multiplier.

### 12.5 `hyperedit vfx blender-check`
Audits Blender CLI installation, version, rendering engines (Cycles, Eevee), and transparency capabilities.
```bash
hyperedit vfx blender-check [--json]
```

---

## 13. Command Group: `hyperedit color`

Provides professional color correction, grading, 3D LUT support, histogram telemetry, and shot matching.

### 13.1 `hyperedit color presets`
Lists available cinematographic color presets with exposure, contrast, temperature, and curves.
```bash
hyperedit color presets [--json]
```

### 13.2 `hyperedit color grade <video_file>`
Applies non-destructive color grading to video footage.
```bash
hyperedit color grade footage.mp4 -o graded.mp4 [--preset warm_editorial] [--strength 1.0] [--exposure 0.5] [--contrast 1.1] [--temp 10.0] [--lut creative.cube]
```
- `-o, --output <path>`: Destination video path.
- `--preset <name>`: Curated preset name (`cinematic_neutral`, `warm_editorial`, `cool_scandi`, `film_stock_5207`, `monochrome_panchro`, `bleach_bypass`).
- `--strength <float>`: Preset blend factor (0.0 to 1.0).
- `--exposure <float>`: Exposure offset in EV stops (-3.0 to +3.0).
- `--contrast <float>`: Contrast multiplier (default: 1.0).
- `--saturation <float>`: Saturation multiplier (default: 1.0).
- `--temp <float>`: Color temperature shift (-50 to +50).
- `--tint <float>`: Tint shift green to magenta (-50 to +50).
- `--lut <path>`: Path to optional `.cube` 3D LUT.

### 13.3 `hyperedit color analyze <media_file>`
Extracts luminance, average RGB, clipping percentages, dynamic range, and optional histogram PNG chart.
```bash
hyperedit color analyze footage.mp4 [--json] [--histogram-output hist.png]
```
- `--histogram-output <path>`: Optional PNG file path to save 3-channel RGB histogram visualization.
- `--json`: Output metrics as structured JSON.

### 13.4 `hyperedit color match <reference_file> <target_file>`
Aligns tonal consistency and color balance of target footage to match reference footage.
```bash
hyperedit color match reference.mp4 target.mp4 -o matched_target.mp4 [--json]
```
- `-o, --output <path>`: Destination path for color-matched video.
- `--json`: Output shot matching telemetry and corrective grade parameters.

### 13.5 `hyperedit color audit <media_file>`
Audits color space, primaries, transfer function, bit depth, and SDR/HDR conformity.
```bash
hyperedit color audit footage.mp4 [--json]
```
- `--json`: Output audit report as structured JSON.






