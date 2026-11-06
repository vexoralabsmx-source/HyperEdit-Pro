# Changelog

All notable changes to **HyperEdit Pro** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-11-06

### Added
- **Core Architecture & Schema v2.0.0**:
  - Deterministic discrete-frame timeline engine with integer frame boundary math (`in_frame`, `out_frame`, `timeline_start_frame`).
  - Full Pydantic v2 schemas: `Project`, `Timeline`, `Track`, `Clip`, `MediaAsset`, `ExportPreset`, `Timecode`.
  - Comprehensive local environment diagnostics via `hyperedit doctor` with strict dependency audits.
- **Professional Media Engine**:
  - FFprobe multi-stream inspection across CFR and VFR footage (23.976 to 60 fps).
  - Multi-channel audio detection, pixel format, color space, and orientation metadata extraction.
  - Automatic thumbnail generation, 3x3 contact sheets, waveform audio visualization PNGs, and 720p editing proxies.
  - Non-destructive media cache with SHA-256 and modification time invalidation.
- **Non-Linear Multi-Track Editing Engine**:
  - Multi-track timeline supporting video (`V1`, `V2`), audio (`A1`–`A3`), graphics (`GRAPHIC`), and adjustment layers.
  - Accurate ripple/overwrite inserts, temporal splits, trims, ripple deletes, and gap closures.
  - Non-destructive `TimelineHistory` providing reversible undo/redo stacks.
  - Video transitions compiler (`xfade` with crossfade, dip to black/white, wipes, and slides).
  - Overlapping dual-stream alpha compositing.
- **Intelligent Audio Engineering & Beat Sync**:
  - Signal-based transient onset detection and tempo (BPM) tracking using zero-dependency streaming PCM audio analysis from FFmpeg.
  - Timeline musical beat marker generation (`Marker`).
  - Automated non-destructive cut snapping to nearest musical beats (`snap_cuts_to_beats`) with deviation reporting.
  - Real hardware/FFmpeg sidechain ducking using `sidechaincompress` to duck BGM under dialogue.
  - EBU R128 loudness measurement and automated normalization filtergraph (`loudnorm`) targeting YouTube (-14 LUFS), Spotify (-14 LUFS), and EBU R128 (-23 LUFS).
- **Professional Captions & Kinetic Typography**:
  - Multi-format parser and bidirectional converter for SubRip (`.srt`), WebVTT (`.vtt`), and Advanced SubStation Alpha (`.ass`).
  - ASS v4.00+ typographic compilation with custom styling, box backings, and alignment geometry.
  - Kinetic typography engine supporting `karaoke_highlight`, `pop_scale`, `word_reveal`, `fade_word`, and `slide_up`.
  - Local speech-to-text transcription engine leveraging `faster-whisper` as an optional dependency without hallucinated outputs.
  - 16:9 landscape and 9:16 vertical safe area layout validation.
- **HyperFrames Motion Graphics Integration**:
  - Adapter strictly complying with the official HyperFrames composition contract (`data-composition-id`, paused GSAP timeline `window.__timelines`, seek-safe).
  - Templates for `cinematic_intro`, `product_showcase`, and `audio_reactive` compositions.
  - 6 curated motion art direction presets (`minimal_editorial`, `cinematic_luxury`, `tech_product`, `corporate_clean`, `energetic_social`, `typography_focus`).
  - High-precision keyframe interpolator evaluating linear, ease-in/out, exact 2D cubic Bézier (via Newton-Raphson), damped spring harmonic oscillator physics, and overshoot bounce.
  - Ken Burns virtual camera pan, tilt, and zoom filter expressions.
  - True alpha channel transparency rendering with Apple ProRes 4444 (`yuva444p12le`) and autonomous local fallback.
- **Visual Effects, Motion Tracking & 3D Integration**:
  - 2D region tracking using normalized cross-correlation template matching (`cv2.TM_CCOEFF_NORMED`) with confidence scoring and lost tracking detection.
  - Sparse optical flow tracking via Lucas-Kanade (`cv2.calcOpticalFlowPyrLK`) with forward-backward error validation.
  - Camera video stabilization via 2D rigid affine trajectory smoothing, compensation warping, and border cropping.
  - Geometric and keyframed mask engine with Gaussian feathering and assisted GrabCut rotoscoping.
  - Color difference chroma keyer extracting green/blue screen footage to transparent ProRes 4444 with spill suppression.
  - 8 layer blend modes (Normal, Multiply, Screen, Overlay, Add, Soft Light, Darken, Lighten).
  - Non-destructive cinematic visual effects: deterministic camera shake, film grain, bloom/glow, and motion blur.
  - Headless Blender 3D integration adapter (`BlenderAdapter`) supporting Cycles/Eevee renders and timeline mounting on track `V2`.
- **Professional Color Correction & Grading Engine**:
  - Exposure compensation in EV stops, contrast multiplier, saturation, vibrance, black point and white point adjustments.
  - White balance (temperature and tint) using normalized chromaticity coordinates and three-way color wheels (Lift/Gamma/Gain).
  - Standardized ASC-CDL transfer evaluation and tonal curves.
  - Industry-standard `.cube` 3D Look-Up Table parser, generator, and trilinear vector interpolator.
  - 6 curated cinematographic presets (`cinematic_neutral`, `warm_editorial`, `cool_scandi`, `film_stock_5207`, `monochrome_panchro`, `bleach_bypass`) with fractional look strength blending.
  - Automated shot matching engine aligning tonal consistency between shots without clipping.
  - Luma/RGB signal histogram analysis, dynamic range estimation, and visual 3-channel histogram PNG chart generation.
  - Color management audit verifying SDR Rec.709 conformity and flagging HDR transfer functions.
- **Agent Skills Distribution & Packaging**:
  - Standardized `SKILL.md` with complete YAML frontmatter metadata, command definitions, and workflow recipes.
  - Unified CLI entrypoint `hyperedit` with subcommands: `doctor`, `media`, `project`, `timeline`, `render`, `audio`, `captions`, `motion`, `vfx`, and `color`.
  - Multi-agent installation instructions for Codex, Claude Code, Cursor, and Gemini CLI.
  - GitHub Actions CI workflow running 90 unit and integration tests across Ubuntu, macOS, and Windows on Python 3.11, 3.12, and 3.13.

