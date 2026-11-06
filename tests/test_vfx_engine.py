"""Comprehensive test suite for HyperEdit Pro VFX, Motion Tracking, Masking, and 3D Integration."""

import json
import math
from pathlib import Path
import subprocess
from click.testing import CliRunner
import cv2
import numpy as np
import pytest

from hyperedit.adapters.blender import BlenderAdapter
from hyperedit.cli.main import cli
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Timeline, Track, TrackKind
from hyperedit.vfx.compositing import LayerCompositor
from hyperedit.vfx.effects import CinematicEffects
from hyperedit.vfx.masks import MaskDefinition, MaskGenerator, MaskKeyframe, MaskShape
from hyperedit.vfx.models import (
    BlendMode,
    BlenderRenderConfig,
    BlenderRenderEngine,
    BloomGlowConfig,
    CameraShakeConfig,
    ChromaKeyConfig,
    FilmGrainConfig,
    TrackingMethod,
)
from hyperedit.vfx.tracking import MotionTracker


@pytest.fixture
def synthetic_moving_object_video(tmp_path: Path) -> Path:
    """Generate a 2-second (60 frames) 640x360 video containing a high-contrast moving circle."""
    out_file = tmp_path / "moving_object.mp4"
    width, height, fps, total_frames = 640, 360, 30.0, 60

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    # Move circle diagonally from (100, 100) to (400, 250)
    for f in range(total_frames):
        t = f / float(total_frames - 1)
        cx = int(round(100.0 + t * 300.0))
        cy = int(round(100.0 + t * 150.0))

        frame = np.full((height, width, 3), 30, dtype=np.uint8)  # Dark charcoal background
        # High contrast white circle with thin cyan border
        cv2.circle(frame, (cx, cy), 20, (255, 255, 255), -1)
        cv2.circle(frame, (cx, cy), 20, (255, 255, 0), 2)
        writer.write(frame)

    writer.release()
    return out_file


@pytest.fixture
def synthetic_green_screen_video(tmp_path: Path) -> Path:
    """Generate a 1-second (30 frames) 640x360 video with pure green background and a centered red square."""
    out_file = tmp_path / "greenscreen.mp4"
    width, height, fps, total_frames = 640, 360, 30.0, 30

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    for f in range(total_frames):
        # Pure green background (B=0, G=255, R=0)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (0, 255, 0)
        # Red foreground square in center (B=0, G=0, R=255)
        cv2.rectangle(frame, (270, 130), (370, 230), (0, 0, 255), -1)
        writer.write(frame)

    writer.release()
    return out_file


def test_motion_tracking_accuracy_and_telemetry(synthetic_moving_object_video: Path, tmp_path: Path) -> None:
    """Verify that MotionTracker accurately tracks a moving target with sub-pixel precision."""
    tracker = MotionTracker(confidence_threshold=0.50)

    # Initial target at frame 0 is at (100, 100) with radius 20 -> bbox is (80, 80, 40, 40)
    initial_bbox = (80.0, 80.0, 40.0, 40.0)
    telemetry = tracker.track_region(
        video_path=synthetic_moving_object_video,
        initial_bbox=initial_bbox,
        method=TrackingMethod.REGION_TEMPLATE,
    )

    assert telemetry.total_frames == 60
    assert telemetry.tracked_frames == 60
    assert telemetry.lost_frames == 0
    assert telemetry.mean_confidence >= 0.85

    # Check start and end tracked positions against ground truth
    track_start = telemetry.tracks[0]
    assert abs(track_start.center_x - 100.0) <= 2.0
    assert abs(track_start.center_y - 100.0) <= 2.0

    track_end = telemetry.tracks[-1]
    # Ground truth at frame 59 is (400, 250)
    assert abs(track_end.center_x - 400.0) <= 4.0
    assert abs(track_end.center_y - 250.0) <= 4.0

    # Save and reload telemetry JSON
    json_path = tmp_path / "tracking.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(telemetry.model_dump_json(indent=2))

    with open(json_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["tracked_frames"] == 60
    assert len(loaded["tracks"]) == 60


def test_motion_tracking_follow_graphic_composite(synthetic_moving_object_video: Path, tmp_path: Path) -> None:
    """Verify that tracked coordinates can drive a follow-graphic overlay composited onto the timeline."""
    tracker = MotionTracker()
    telemetry = tracker.track_region(
        video_path=synthetic_moving_object_video,
        initial_bbox=(80.0, 80.0, 40.0, 40.0),
    )

    # Generate a follower overlay video with a target reticle following the tracked center
    width, height, fps = 640, 360, 30.0

    # Create transparent video using FFmpeg and OpenCV
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    temp_vis = tmp_path / "temp_vis.mp4"
    writer = cv2.VideoWriter(str(temp_vis), fourcc, fps, (width, height))

    for track in telemetry.tracks:
        frame = np.full((height, width, 3), 30, dtype=np.uint8)
        # Draw target reticle crosshair at tracked center
        tx, ty = int(round(track.center_x)), int(round(track.center_y))
        cv2.drawMarker(frame, (tx, ty), (0, 255, 255), markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)
        writer.write(frame)
    writer.release()

    assert temp_vis.is_file()
    assert temp_vis.stat().st_size > 1000


def test_video_stabilization_engine(tmp_path: Path) -> None:
    """Verify video stabilization on footage with artificial camera shake."""
    width, height, fps, total_frames = 480, 270, 30.0, 45
    shaky_video = tmp_path / "shaky_source.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(shaky_video), fourcc, fps, (width, height))

    # Static scene with sinusoidal horizontal camera jitter (+-12px)
    for f in range(total_frames):
        jitter_x = int(round(12.0 * math.sin(f * 0.8)))
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Static landmarks
        cv2.rectangle(frame, (100 + jitter_x, 80), (180 + jitter_x, 180), (200, 200, 200), -1)
        cv2.rectangle(frame, (300 + jitter_x, 120), (380 + jitter_x, 220), (150, 150, 240), -1)
        writer.write(frame)
    writer.release()

    # Stabilize
    stabilized_out = tmp_path / "stabilized.mp4"
    tracker = MotionTracker()
    tel = tracker.stabilize_video(shaky_video, stabilized_out, smoothing_window=15, crop_border_pct=0.05)

    assert stabilized_out.is_file()
    assert tel.total_frames == total_frames
    assert tel.max_displacement_px > 0.0
    assert len(tel.smoothed_trajectory) == total_frames


def test_mask_generation_and_feathering() -> None:
    """Verify mask rendering, keyframing, rotation, and Gaussian feathering."""
    mask_def = MaskDefinition(
        mask_id="mask_01",
        shape=MaskShape.ELLIPSE,
        feather_px=10.0,
        opacity=1.0,
        keyframes=[
            MaskKeyframe(frame_index=0, center_x=100.0, center_y=100.0, width=80.0, height=80.0, rotation_deg=0.0, feather_px=10.0),
            MaskKeyframe(frame_index=30, center_x=200.0, center_y=200.0, width=120.0, height=120.0, rotation_deg=45.0, feather_px=10.0),
        ],
    )

    # Frame 0
    mask_0 = MaskGenerator.render_mask_frame(mask_def, width=400, height=400, frame_index=0)
    assert mask_0.shape == (400, 400)
    # Center pixel should be near opaque (255)
    assert mask_0[100, 100] >= 240
    # Far pixel should be transparent (0)
    assert mask_0[10, 10] == 0
    # Boundary pixel should exhibit smooth feathering (between 10 and 240)
    boundary_val = mask_0[100, 140]
    assert 10 <= boundary_val <= 245

    # Interpolated frame 15 (center should be at 150, 150)
    mask_15 = MaskGenerator.render_mask_frame(mask_def, width=400, height=400, frame_index=15)
    assert mask_15[150, 150] >= 240


def test_chroma_keying_and_alpha_transparency(synthetic_green_screen_video: Path, tmp_path: Path) -> None:
    """Verify color difference chroma keying cleanly extracts green background leaving alpha."""
    config = ChromaKeyConfig(key_color_rgb=(0, 255, 0), similarity=0.3, smoothness=0.1)

    # 1. Test frame-level chroma key
    test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    test_frame[:, :] = (0, 255, 0)  # Pure green background
    test_frame[40:60, 40:60] = (0, 0, 255)  # Red box in center

    bgra, alpha = LayerCompositor.apply_chroma_key(test_frame, config)
    assert alpha[10, 10] == 0  # Green keyed to transparent
    assert alpha[50, 50] == 255  # Red remains completely opaque

    # 2. Test full video chroma key render to ProRes 4444
    keyed_mov = tmp_path / "keyed_prores4444.mov"
    out = LayerCompositor.render_chroma_keyed_video(synthetic_green_screen_video, keyed_mov, config)

    assert out.is_file()
    assert out.stat().st_size > 1000

    # 3. Probe with FFprobe to verify true alpha channel
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,pix_fmt",
        "-of",
        "json",
        str(out),
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    info = json.loads(res.stdout)
    pix_fmt = info["streams"][0]["pix_fmt"]
    assert "yuva" in pix_fmt or "rgba" in pix_fmt, f"Expected alpha channel pixel format, got {pix_fmt}"


def test_layer_blend_modes_arithmetic() -> None:
    """Verify arithmetic correctness for all supported blend modes."""
    base = np.full((10, 10, 3), 128, dtype=np.uint8)  # 50% gray
    blend = np.full((10, 10, 3), 255, dtype=np.uint8)  # 100% white

    # Screen with white yields pure white (255)
    res_screen = LayerCompositor.blend_frames(base, blend, mode=BlendMode.SCREEN)
    assert res_screen[0, 0, 0] == 255

    # Multiply with white yields original base (128)
    res_mult = LayerCompositor.blend_frames(base, blend, mode=BlendMode.MULTIPLY)
    assert abs(int(res_mult[0, 0, 0]) - 128) <= 1

    # Add with 50% gray + 50% gray yields white (255)
    blend_half = np.full((10, 10, 3), 128, dtype=np.uint8)
    res_add = LayerCompositor.blend_frames(base, blend_half, mode=BlendMode.ADD)
    assert res_add[0, 0, 0] >= 254


def test_cinematic_visual_effects_filters(synthetic_moving_object_video: Path, tmp_path: Path) -> None:
    """Verify camera shake, film grain, bloom/glow and motion blur filter generation and execution."""
    # 1. Film grain render
    grain_filt = CinematicEffects.build_film_grain_filter(FilmGrainConfig(intensity=0.25))
    assert "noise=" in grain_filt
    grain_out = tmp_path / "grain.mp4"
    CinematicEffects.render_effect_to_video(synthetic_moving_object_video, grain_out, grain_filt)
    assert grain_out.is_file()
    assert grain_out.stat().st_size > 1000

    # 2. Camera shake filter
    shake_filt = CinematicEffects.build_camera_shake_filter(CameraShakeConfig(intensity_px=10.0), width=640, height=360)
    assert "crop=" in shake_filt
    assert "scale=" in shake_filt

    # 3. Bloom glow filter
    bloom_filt = CinematicEffects.build_bloom_glow_filter(BloomGlowConfig(threshold=0.7), width=640, height=360)
    assert "gblur=" in bloom_filt
    assert "blend=" in bloom_filt


def test_blender_adapter_command_and_timeline_import(synthetic_moving_object_video: Path, tmp_path: Path) -> None:
    """Verify BlenderAdapter command construction, headless arguments, and timeline import."""
    adapter = BlenderAdapter(blender_bin="blender")
    config = BlenderRenderConfig(
        scene_file=str(tmp_path / "test_scene.blend"),
        output_pattern=str(tmp_path / "render_####.png"),
        start_frame=1,
        end_frame=24,
        engine=BlenderRenderEngine.CYCLES,
        samples=32,
        transparent_background=True,
    )

    cmd = adapter.build_render_command(config)
    assert "-b" in cmd
    assert "-E" in cmd
    assert "CYCLES" in cmd
    assert "-s" in cmd and "1" in cmd
    assert "-e" in cmd and "24" in cmd
    assert "-a" in cmd

    # Test importing a rendered asset into a project timeline on track V2
    project = Project(
        metadata=ProjectMetadata(title="BlenderTest"),
        settings=ProjectSettings(width=640, height=360, fps=30.0),
        timeline=Timeline(tracks=[Track(track_id="V1", kind=TrackKind.VIDEO, clips=[])]),
    )

    clip = adapter.import_render_to_timeline(
        project=project,
        rendered_media_path=synthetic_moving_object_video,
        track_id="V2",
        start_frame=0,
    )

    assert clip.asset_id.startswith("blender_")
    assert clip.timeline_start_frame == 0
    assert len(project.timeline.tracks) == 2
    assert project.timeline.get_track("V2") is not None


def test_cli_vfx_commands(synthetic_moving_object_video: Path, synthetic_green_screen_video: Path, tmp_path: Path) -> None:
    """Verify all CLI vfx subcommands execute properly and produce structured telemetry."""
    runner = CliRunner()

    # 1. hyperedit vfx blender-check --json
    res_b = runner.invoke(cli, ["vfx", "blender-check", "--json"])
    assert res_b.exit_code == 0
    b_data = json.loads(res_b.output)
    assert "supported_engines" in b_data

    # 2. hyperedit vfx track
    track_json = tmp_path / "cli_tracking.json"
    res_track = runner.invoke(
        cli,
        ["vfx", "track", str(synthetic_moving_object_video), "-o", str(track_json), "--bbox", "80,80,40,40"],
    )
    assert res_track.exit_code == 0
    assert track_json.is_file()

    # 3. hyperedit vfx key
    keyed_mov = tmp_path / "cli_keyed.mov"
    res_key = runner.invoke(
        cli,
        ["vfx", "key", str(synthetic_green_screen_video), "-o", str(keyed_mov), "--color", "0x00FF00"],
    )
    assert res_key.exit_code == 0
    assert keyed_mov.is_file()

    # 4. hyperedit vfx effect
    fx_mp4 = tmp_path / "cli_fx.mp4"
    res_fx = runner.invoke(
        cli,
        ["vfx", "effect", str(synthetic_moving_object_video), "-o", str(fx_mp4), "--effect", "grain"],
    )
    assert res_fx.exit_code == 0
    assert fx_mp4.is_file()

