# HyperEdit Pro Engineering Roadmap

## Phase 1: Foundation, CLI & Architecture Contracts (Current)
- [x] Standard Agent Skills scaffolding with `SKILL.md` and YAML frontmatter.
- [x] Python 3.11+ project setup with `pyproject.toml` (PEP 517/621).
- [x] Public contracts and data models (`Project`, `Timeline`, `Track`, `Clip`, `MediaAsset`, `Timecode`, `ExportPreset`, `AudioMixConfig`, `ColorGradeConfig`, `SubtitleTrack`).
- [x] Real environment diagnostics engine (`hyperedit doctor`) checking FFmpeg, FFprobe, hardware encoders, core filters, Python runtime, and optional packages.
- [x] Core CLI commands: `doctor`, `version`, `new`, `validate`, `probe`.
- [x] Automated test suite (`pytest`) with 100% pass rate.
- [x] GitHub Actions multi-platform CI configuration (Ubuntu, macOS, Windows).
- [x] Full JSON project specification and exported JSON schema (`assets/project.schema.json`).

---

## Phase 2: Professional Media Engine (Completed)
- [x] Complete media ingestion pipeline: Import -> Analyze -> Validate -> Proxy -> Artifacts -> Metadata.
- [x] Production-grade FFprobe inspection with exact rational frame rates (23.976, 24, 25, 29.97, 30, 50, 59.94, 60).
- [x] Constant (CFR) vs Variable Frame Rate (VFR) detection.
- [x] Audio channel topology support (mono, stereo, 5.1 surround, silent video detection).
- [x] Metadata orientation & vertical video (9:16 portrait) detection.
- [x] Health & corruption audit identifying empty, broken, truncated, and incompatible files.
- [x] Artifact generators:
  - High-resolution thumbnails (`hyperedit media thumbnail`).
  - Mosaic contact sheets e.g. 3x3 (`hyperedit media contact-sheet`).
  - Waveform PNG visualizations (`hyperedit media waveform`).
  - Fast editing proxies at 720p, 540p, 360p (`hyperedit media proxy`).
  - Uncompressed/lightly compressed audio stem extraction (`hyperedit media extract-audio`).
- [x] Acoustic signal telemetry (`hyperedit media signal-metrics`): peak dBFS, mean volume (RMS), clipping warnings, and silence interval detection.
- [x] High-performance persistent cache (`MediaCacheManager`) with fast size/mtime/chunk-hash invalidation.
- [x] Cross-platform Unicode, space, and path normalization without mutating source media.
- [x] End-to-end testing with synthetic fixtures in `tests/test_media_engine.py` (39/39 passing tests).

---

## Phase 3: Multi-Track Timeline Engine & Assembly (Completed)
- [x] Discrete-frame multi-track timeline engine (`TimelineEngine`) implementing `TimelineEngineProtocol`.
- [x] Non-destructive editing operations:
  - `insert_clip`: Overwrite (punch-in & middle-slice) and ripple modes.
  - `split_clip`: Frame-accurate cut with source in/out frame mapping and speed compensation.
  - `trim_clip`: Head and tail trimming with optional downstream ripple.
  - `ripple_delete`: Deletes clip and automatically pulls subsequent clips backward.
  - `move_clip`: Shifts start frame and supports moving clips between tracks.
  - `close_gaps`: Automated detection and elimination of dead frames/black gaps.
  - `detect_collisions`: Detects unauthorized overlapping clips without transitions.
- [x] Transitions engine: Hard cuts (default narrative pacing) and `xfade` transitions (`fade`, `crossfade`, `dissolve`, `dip_to_black`, `dip_to_white`, `wipe_left`, `wipe_right`, `slide_left`, `zoom_in`).
- [x] Speed, slow motion, fast motion and reverse motion (`speed`, `reverse`, `atempo`, `areverse`).
- [x] 2D spatial transforms: scale, position, opacity, letterboxing, and reframing (16:9, 9:16, 1:1, 4:5).
- [x] Multi-layer composition (V1 base, V2 overlays, Graphic/title layers).
- [x] Undo/Redo reversible operation history (`TimelineHistory`).
- [x] Deterministic filtergraph compiler (`FiltergraphCompiler`) and render execution engine (`RenderEngine`).
- [x] CLI commands: `project create`, `timeline inspect`, `timeline validate`, `timeline insert/split/trim/delete/close-gaps`, `render`.
- [x] Real montage test rendering playable MP4 with 4 clips, 2 cuts, 2 transitions, and overlay layer (48/48 passing tests).

---

## Phase 4: Intelligent Audio Engineering & Beat Sync (Completed)
- [x] Real acoustic signal beat tracking (`BeatTracker`) using short-time RMS energy novelty and autocorrelation.
- [x] Zero-dependency pure Python streaming PCM decoder from FFmpeg stdout (`s16le`).
- [x] Accurate tempo (BPM), beat interval, transient onset detection, and first downbeat phase alignment.
- [x] Timeline beat marker generator (`BeatSynchronizer.add_beat_markers`) creating visual bookmarks (`Marker`).
- [x] Non-destructive cut snapping to nearest musical beats (`BeatSynchronizer.snap_cuts_to_beats`) with `ripple` and `roll` modes.
- [x] Beat alignment telemetry and deviation report (`BeatAlignmentReport`, `CutShiftDetail`) tracking exact frame and millisecond shifts.
- [x] Professional multi-bus audio mixer (`AudioMixer.mix_timeline_audio`) handling dialogue, music, SFX, and original audio.
- [x] Real hardware/FFmpeg sidechain ducking (`AudioMixer.apply_sidechain_ducking`) utilizing `sidechaincompress` with configurable threshold, ratio, attack, and release.
- [x] Platform loudness measurement (`AudioMixer.measure_loudness`) via EBU R128 filter parsing integrated LUFS, True Peak dBFS, LRA, and gated threshold.
- [x] Standard platform loudness presets: YouTube (-14 LUFS), Spotify (-14 LUFS), Apple Podcasts (-16 LUFS), EBU R128 (-23 LUFS), ATSC A/85 (-24 LUFS).
- [x] Automated loudness normalization filter (`AudioMixer.normalize_loudness`) via FFmpeg `loudnorm`.
- [x] Complete CLI audio command group (`hyperedit audio beats`, `markers`, `snap`, `loudness`, `normalize`, `duck`, `mix`).
- [x] 100% test coverage with synthetic metronomes, sidechain attenuation measurements, and loudness compliance tests in `tests/test_audio_engine.py` (55/55 passing tests).

---

## Phase 5: Professional Captions & Kinetic Typography (Completed)
- [x] Multi-format subtitle parser and bidirectional converter for SubRip (`.srt`), WebVTT (`.vtt`), and Advanced SubStation Alpha (`.ass`).
- [x] ASS v4.00+ typographic compilation with exact font, size, outline, shadow, box backings, and alignment geometry.
- [x] Kinetic typography engine (`KineticTypographyCompiler`):
  - `karaoke_highlight`: synchronized active word accent coloring maintaining sentence context.
  - `pop_scale`: active word scale emphasis (`\fscx115\fscy115`).
  - `word_reveal`: progressive word accumulation as spoken.
  - `fade_word` and `slide_up`: smooth entrance and vector transitions.
- [x] Proportional word duration estimator (`estimate_word_timestamps`) when ASR word timestamps are absent.
- [x] Professional typographic presets (`netflix`, `modern_bold`, `cinema_serif`, `tiktok_reels_neon`, `impact_pop`, `minimalist`).
- [x] Cross-platform burn-in video renderer with safe Windows path escaping for FFmpeg `libass`.
- [x] Safe area margins and layout rules for 16:9 landscape and 9:16 vertical video (TikTok, IG Reels, Shorts).
- [x] Visual readability QA auditor (`validate_readability`) checking CPS reading pace, minimum durations, line length limits, and temporal overlaps.
- [x] Local speech-to-text transcription engine (`SpeechTranscriber`) leveraging `faster-whisper` as an optional dependency without fake simulations.
- [x] HyperFrames motion typography adapter (`HyperFramesCaptionsAdapter`) generating standalone HTML/CSS/GSAP compositions.
- [x] Complete CLI captions group (`hyperedit captions import`, `export`, `burn`, `transcribe`, `kinetic`, `hyperframes`, `validate`).
- [x] 100% test coverage with real traditional and kinetic video renders in `tests/test_captions_engine.py` (66/66 passing tests).

---

## Phase 6: Professional Motion Graphics & HyperFrames Integration (Completed)
- [x] HyperFrames composition adapter (`HyperFramesAdapter`) adhering to the official HyperFrames composition contract (`<div data-composition-id...>`, paused GSAP timeline `window.__timelines`, seek-safe).
- [x] Dynamic template authoring for `cinematic_intro`, `product_showcase`, and `audio_reactive` compositions.
- [x] Curated art direction motion presets (`minimal_editorial`, `cinematic_luxury`, `tech_product`, `corporate_clean`, `energetic_social`, `typography_focus`) with strict typography, palettes, and easing.
- [x] High-precision keyframe interpolator (`KeyframeInterpolator`) with mathematical evaluation of:
  - `linear`, `ease_in`, `ease_out`, `ease_in_out`
  - Exact 2D Cubic Bézier polynomial solved via Newton-Raphson inversion
  - Damped spring harmonic oscillator physics
  - Overshoot anticipation/bounce curves
- [x] Virtual camera and Ken Burns trajectories (`MotionEngine.apply_ken_burns`) generating jitter-free sub-pixel pan and zoom filter expressions.
- [x] Audio-reactive beat synchronization (`HyperFramesAdapter.sync_with_audio_beats`) injecting real detected musical pulses into GSAP timelines.
- [x] Multi-path transparent video overlay rendering:
  - Primary path: Headless Chrome / HyperFrames CLI rendering Apple ProRes 4444 QuickTime movie (`yuva444p12le`).
  - Autonomous fallback path: Local FFmpeg ProRes 4444 transparent alpha generator (`prores_ks` with `yuva444p10le`) or VP9 WebM (`yuva420p`).
- [x] Multi-track timeline integration (`HyperFramesAdapter.import_to_timeline`) probing overlay properties and compositing on `GRAPHIC` tracks with dual-stream alpha compositing.
- [x] Automatic software encoder fallback (`libx264`) in `RenderEngine` when hardware acceleration (e.g. NVENC) is unavailable on host.
- [x] Complete CLI motion command group (`hyperedit motion presets`, `create`, `sync`, `render`, `overlay`).
- [x] 100% test coverage with real transparent ProRes 4444 alpha checks, composite renders, and CLI execution in `tests/test_motion_graphics.py` (73/73 passing tests).

---

## Phase 7: Visual Effects, Motion Tracking & 3D Integration (Completed)
- [x] Computer vision motion tracking engine (`MotionTracker`) with normalized cross-correlation template matching (`REGION_TEMPLATE`) and Lucas-Kanade optical flow (`POINT_LK`).
- [x] Confidence scoring metric (0.0 to 1.0), lost tracking detection, and frame-by-frame telemetry (`TrackingTelemetry`).
- [x] Trajectory estimation and camera video stabilization (`stabilize_video`) with 2D affine smoothing, compensation warp, and border cropping.
- [x] Follow-graphic motion coupling driving timeline overlays from tracked coordinates.
- [x] Mask engine (`MaskGenerator`) supporting rectangle, ellipse, polygon, keyframe animation, and Gaussian feathering.
- [x] Assisted rotoscoping with GrabCut (`assisted_rotoscope_grabcut`) using bounding-box segmentation.
- [x] Alpha compositing and 8 layer blend modes (`LayerCompositor.blend_frames`: Normal, Multiply, Screen, Overlay, Add, Soft Light, Darken, Lighten).
- [x] Color difference chroma keying (`LayerCompositor.apply_chroma_key`) with green/blue screen extraction, smoothness ramp, and spill suppression.
- [x] Headless 3D Blender integration adapter (`BlenderAdapter`) supporting Cycles/Eevee, transparent RGBA sequences, and timeline mounting on track `V2`.
- [x] Non-destructive cinematic visual effects (`CinematicEffects`): deterministic camera shake, film grain, bloom/glow, and motion blur.
- [x] Complete CLI VFX command group (`hyperedit vfx track`, `stabilize`, `key`, `effect`, `blender-check`).
- [x] 100% test coverage with 82/82 passing tests across all stages in `tests/test_vfx_engine.py`.

---

## Phase 8: Professional Color Correction & Grading Engine (Completed)
- [x] Non-destructive color grading compiler (`ColorGradingEngine`) compiling `ColorGradeConfig` to FFmpeg filtergraphs (`eq`, `colorbalance`, `curves`, `lut3d`).
- [x] Quantitative exposure in EV stops, contrast multiplier, saturation, vibrance, black point and white point adjustments.
- [x] Color temperature and tint balance using normalized chromaticity coordinates and three-way color wheels (Lift/Gamma/Gain).
- [x] Standardized ASC-CDL transfer evaluation (slope, offset, power, saturation).
- [x] Industry-standard `.cube` 3D LUT parser, generator, and trilinear/tetrahedral vector interpolator (`CubeLUT`).
- [x] 6 curated cinematographic presets (`cinematic_neutral`, `warm_editorial`, `cool_scandi`, `film_stock_5207`, `monochrome_panchro`, `bleach_bypass`) with fractional look strength blending.
- [x] Shot matching engine (`ColorGradingEngine.match_shots`) analyzing source and reference histograms to automatically produce corrective grades aligning tonal consistency.
- [x] Signal metrics and histogram analysis (`analyze_histogram`) reporting mean luma, standard deviation, shadow clipping (<16 IRE), highlight clipping (>240 IRE), and rendering 3-channel RGB visual histogram charts to PNG.
- [x] Color management audit (`audit_color_space`) inspecting color primaries, transfer functions, and dynamic range to enforce SDR Rec.709 conformity and flag HDR tonemapping requirements.
- [x] Native timeline integration: `Clip.color_grade` automatically compiled in `FiltergraphCompiler` for primary and overlay video tracks.
- [x] Complete CLI color command group (`hyperedit color presets`, `grade`, `analyze`, `match`, `audit`).
- [x] 100% test coverage with 90/90 passing tests across all stages in `tests/test_color_engine.py`.

---

## Phase 9: Intelligence & Audio-Visual Automation
- [ ] Scene cut boundary detection via FFmpeg `select='gt(scene,0.4)'` and PySceneDetect.
- [ ] Audio silence detector (`silencedetect`) for automated podcast jump-cutting.
- [ ] Intelligent auto-reframing for vertical (9:16) social media clips.

---

## Phase 10: Audiovisual QA & Delivery Pipeline
- [ ] Automated quality assurance scanner:
  - Black frame gap detector (`blackdetect`).
  - Freeze frame detector (`freezedetect`).
  - Audio clipping (>0 dBFS true peak) and phase cancellation check.
- [ ] Multi-preset batch render dispatch (Master ProRes 422 HQ, YouTube 4K, Vertical Reels).

