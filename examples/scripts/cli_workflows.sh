#!/usr/bin/env bash
# ==============================================================================
# HyperEdit Pro: Reproducible End-to-End Command Workflows
# ==============================================================================
set -e

echo "=== 1. Environment & Diagnostics ==="
hyperedit doctor --json
hyperedit version

echo "=== 2. Media Engine Probing & Proxies ==="
# Probe footage metadata and evaluate CFR/VFR timing
# hyperedit media probe footage.mp4 --json --hash
# Generate waveform and editing proxy
# hyperedit media waveform audio.wav -o waveform.png
# hyperedit media proxy footage.mp4 -o proxy.mp4 --scale 720p

echo "=== 3. Audio Engineering & Beat Sync ==="
# Detect BPM and transient onsets from real acoustic signal
# hyperedit audio beats music.mp3 --json
# Align video cuts on track V1 to musical beats within 8 frames
# hyperedit audio snap project.json music.mp3 --track V1 --max-shift 8 --mode ripple
# Master bus loudness normalization to YouTube (-14 LUFS)
# hyperedit audio mix project.json -o master_audio.wav --profile youtube

echo "=== 4. Kinetic Typography & Captions ==="
# Transcribe speech with word-level timestamps
# hyperedit captions transcribe speech.mp3 -o subtitles.srt --model base
# Generate ASS kinetic typography with karaoke word highlighting
# hyperedit captions kinetic subtitles.srt -o kinetic.ass --mode karaoke_highlight --preset tiktok_reels_neon
# Burn subtitles directly into master video
# hyperedit captions burn raw.mp4 kinetic.ass -o burned_video.mp4

echo "=== 5. Motion Graphics & HyperFrames ==="
# Create HyperFrames HTML motion graphic composition
# hyperedit motion create cinematic_intro -o title.html --title "THE HORIZON" --preset cinematic_luxury
# Inject audio beat pulses into the composition
# hyperedit motion sync title.html music.mp3 -o title_synced.html
# Render transparent ProRes 4444 overlay
# hyperedit motion render title_synced.html -o overlay.mov --format mov --fps 30.0
# Attach overlay directly onto track GRAPHIC
# hyperedit motion overlay project.json overlay.mov --track GRAPHIC --start-frame 0

echo "=== 6. VFX, Tracking & Chroma Key ==="
# Track moving object and export telemetry JSON
# hyperedit vfx track footage.mp4 --bbox 80,80,40,40 -o tracking.json
# Stabilize shaky camera footage
# hyperedit vfx stabilize shaky.mp4 -o stabilized.mp4 --smoothing 15
# Key green screen footage to transparent ProRes 4444 video
# hyperedit vfx key greenscreen.mp4 -o keyed.mov --color 0x00FF00
# Apply film grain noise
# hyperedit vfx effect raw.mp4 -o film_look.mp4 --effect grain --intensity 0.18

echo "=== 7. Color Grading & Shot Matching ==="
# List available curated cinematographic presets
hyperedit color presets --json
# Match tonal consistency between target shot and reference shot
# hyperedit color match hero_shot.mp4 secondary_shot.mp4 -o secondary_matched.mp4
# Apply warm editorial color grade preset with 85% strength
# hyperedit color grade secondary_matched.mp4 -o graded_master.mp4 --preset warm_editorial --strength 0.85

echo "=== 8. Render Final Master Deliverable ==="
# hyperedit render project.json -o final_master.mp4 --preset web_1080p
echo "HyperEdit Pro workflows completed successfully."

