# HyperEdit Pro Project Format Specification (v2.0.0)

## 1. Overview

The HyperEdit Pro project file (`.json`) is a deterministic, version-controlled declaration of an audiovisual composition. It specifies timeline geometry, media asset pointers, track arrangements, audio mixing topologies, color transformations, subtitle cues, and delivery presets.

All timestamps within the editing core use **discrete frame indices** coupled to a project base frame rate to eliminate floating-point drift over multi-hour master sequences.

---

## 2. Top-Level Structure

A valid project JSON matches the following root structure:

```json
{
  "schema_version": "2.0.0",
  "metadata": {
    "title": "string",
    "description": "string (optional)",
    "author": "string (optional)",
    "created_at": "ISO 8601 string",
    "updated_at": "ISO 8601 string"
  },
  "settings": {
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
    "sample_rate": 48000,
    "audio_channels": 2,
    "color_space": "bt709",
    "working_pixel_format": "yuv420p"
  },
  "media_pool": {
    "assets": {
      "<asset_id>": { ... }
    }
  },
  "timeline": {
    "tracks": [ ... ],
    "markers": [ ... ]
  },
  "subtitles": [ ... ],
  "export_presets": {
    "<preset_name>": { ... }
  }
}
```

---

## 3. Media Pool (`media_pool`)

The media pool stores technical probes of source media. Clips on the timeline reference assets via their unique `asset_id`.

```json
{
  "asset_id": "cam_a_wide",
  "file_path": "footage/cam_a.mp4",
  "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
  "duration_seconds": 120.45,
  "size_bytes": 268435456,
  "video_streams": [
    {
      "index": 0,
      "codec": "h264",
      "width": 1920,
      "height": 1080,
      "fps": 23.976,
      "duration_seconds": 120.45,
      "pixel_format": "yuv420p",
      "bit_depth": 8,
      "aspect_ratio": "16:9",
      "color_space": "bt709"
    }
  ],
  "audio_streams": [
    {
      "index": 1,
      "codec": "aac",
      "sample_rate": 48000,
      "channels": 2,
      "channel_layout": "stereo",
      "duration_seconds": 120.45
    }
  ],
  "subtitle_streams": [],
  "hash_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

Special synthetic generators can be referenced directly without pool registration:
- `generator:black`: Generates pure black video frames.
- `generator:color`: Generates uniform color background.

---

## 4. Multi-Track Timeline (`timeline`)

### 4.1 Tracks (`Track`)
Tracks represent parallel layers evaluated according to their kind and Z-index:
- `video`: Primary visual tracks. Higher index overlays lower index.
- `audio`: Audio tracks mixed into master buses.
- `subtitle`: Subtitle and caption cues.
- `graphic`: Dedicated overlay track for motion graphics or HyperFrames renders.
- `adjustment`: Non-destructive color or VFX layer applied to all tracks below.

```json
{
  "track_id": "V1",
  "name": "Main Camera",
  "kind": "video",
  "index": 0,
  "muted": false,
  "solo": false,
  "locked": false,
  "clips": [ ... ]
}
```

### 4.2 Clips (`Clip`)
A clip defines a temporal segment carved from a source asset:

```json
{
  "clip_id": "clip_001",
  "asset_id": "cam_a_wide",
  "name": "Opening statement",
  "in_frame": 120,
  "out_frame": 450,
  "timeline_start_frame": 0,
  "speed": 1.0,
  "volume_db": 0.0,
  "pan": 0.0,
  "transform": {
    "position_x": 0.0,
    "position_y": 0.0,
    "scale_x": 1.0,
    "scale_y": 1.0,
    "rotation_deg": 0.0,
    "opacity": 1.0
  },
  "color_grade": {
    "exposure_ev": 0.3,
    "contrast": 1.05,
    "saturation": 1.0
  },
  "transition_in": {
    "type": "crossfade",
    "duration_frames": 15,
    "alignment": "center",
    "easing": "ease_in_out"
  }
}
```

---

## 5. Audio Mixing and DSP

Tracks of kind `audio` support mixer configurations:
- **Fader gain**: `volume_db` (-96.0 dB to +12.0 dB).
- **Stereo Panning**: `pan` (-1.0 to 1.0).
- **Sidechain Ducking**: Attenuates background music when dialogue occurs on a trigger track.
- **EBU R128 Normalization**: Integrated LUFS target (-23 LUFS broadcast, -14 LUFS YouTube).

```json
{
  "volume_db": -12.0,
  "pan": 0.0,
  "ducking": {
    "trigger_track_id": "A1",
    "attenuation_db": -14.0,
    "attack_ms": 80.0,
    "release_ms": 400.0,
    "threshold_db": -26.0
  },
  "loudness_normalization": {
    "target_i": -14.0,
    "target_lra": 7.0,
    "target_tp": -1.0
  }
}
```

---

## 6. Validation and Integrity Rules

HyperEdit Pro enforces strict integrity guarantees:
1. Every `asset_id` on a clip must exist in `media_pool.assets` or begin with `generator:`.
2. `out_frame` must strictly exceed `in_frame`.
3. Clips on a single video track must not overlap unless an explicit transition is defined.
4. Total timeline duration is deterministically computed from the rightmost clip boundary.

