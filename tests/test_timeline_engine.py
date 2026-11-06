"""Tests for HyperEdit Pro Professional Timeline & Editing Engine."""

from pathlib import Path
import subprocess
import pytest
from click.testing import CliRunner

from hyperedit.cli.main import cli
from hyperedit.core.models.export import ExportPreset, HardwareAccel
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Clip, Timeline, Track, TrackKind
from hyperedit.core.models.transforms import Transform
from hyperedit.core.models.transitions import Transition, TransitionType
from hyperedit.media.prober import FFprobeProber
from hyperedit.rendering.engine import RenderEngine
from hyperedit.timeline.engine import TimelineEngine
from hyperedit.timeline.history import TimelineHistory


@pytest.fixture
def empty_timeline() -> Timeline:
    return Timeline(
        tracks=[
            Track(track_id="V1", name="Video 1", kind=TrackKind.VIDEO, index=0),
            Track(track_id="V2", name="Video 2 (Overlay)", kind=TrackKind.GRAPHIC, index=1),
            Track(track_id="A1", name="Audio 1", kind=TrackKind.AUDIO, index=2),
        ]
    )


# ----------------------------------------------------------------------
# 1. Timeline Engine Non-Destructive Operations
# ----------------------------------------------------------------------

def test_timeline_insert_ripple_mode(empty_timeline):
    engine = TimelineEngine()

    c1 = Clip(clip_id="c1", asset_id="vid1", in_frame=0, out_frame=60, timeline_start_frame=0)
    c2 = Clip(clip_id="c2", asset_id="vid2", in_frame=0, out_frame=60, timeline_start_frame=60)
    engine.insert_clip(empty_timeline, "V1", c1)
    engine.insert_clip(empty_timeline, "V1", c2)

    # Insert c3 at frame 30 with ripple=True
    c3 = Clip(clip_id="c3", asset_id="vid3", in_frame=0, out_frame=30, timeline_start_frame=30)
    engine.insert_clip(empty_timeline, "V1", c3, ripple=True)

    track_v1 = empty_timeline.get_track("V1")
    assert len(track_v1.clips) == 3

    # c1 starts at 0, c3 starts at 30 (duration 30, ends at 60)
    # c2 had start_frame=60, which is >= 30, so it ripples to 60 + 30 = 90
    clips_by_id = {c.clip_id: c for c in track_v1.clips}
    assert clips_by_id["c1"].timeline_start_frame == 0
    assert clips_by_id["c3"].timeline_start_frame == 30
    assert clips_by_id["c2"].timeline_start_frame == 90


def test_timeline_insert_overwrite_mode(empty_timeline):
    engine = TimelineEngine()

    # Base clip: 0 to 120 (4 seconds at 30 fps)
    c_base = Clip(clip_id="c_base", asset_id="vid1", in_frame=0, out_frame=120, timeline_start_frame=0)
    engine.insert_clip(empty_timeline, "V1", c_base)

    # Punch in middle: frame 30 to 60 (overwrite)
    c_punch = Clip(clip_id="c_punch", asset_id="vid2", in_frame=0, out_frame=30, timeline_start_frame=30)
    engine.insert_clip(empty_timeline, "V1", c_punch, ripple=False)

    track_v1 = empty_timeline.get_track("V1")
    # c_base should be split into head (0-30) and tail (60-120), plus c_punch (30-60)
    assert len(track_v1.clips) == 3

    clips = track_v1.clips
    assert clips[0].timeline_start_frame == 0
    assert clips[0].timeline_end_frame == 30
    assert clips[1].timeline_start_frame == 30
    assert clips[1].timeline_end_frame == 60
    assert clips[2].timeline_start_frame == 60
    assert clips[2].timeline_end_frame == 120


def test_timeline_split_clip(empty_timeline):
    engine = TimelineEngine()
    c = Clip(clip_id="clip_long", asset_id="vid1", in_frame=100, out_frame=200, timeline_start_frame=50)
    engine.insert_clip(empty_timeline, "V1", c)

    # Split at timeline frame 80 (delta = 30 frames from start)
    c1, c2 = engine.split_clip(empty_timeline, "V1", "clip_long", split_frame=80)

    assert c1.clip_id == "clip_long_p1"
    assert c1.in_frame == 100
    assert c1.out_frame == 130
    assert c1.timeline_start_frame == 50
    assert c1.timeline_end_frame == 80

    assert c2.clip_id == "clip_long_p2"
    assert c2.in_frame == 130
    assert c2.out_frame == 200
    assert c2.timeline_start_frame == 80
    assert c2.timeline_end_frame == 150


def test_timeline_trim_clip(empty_timeline):
    engine = TimelineEngine()
    c = Clip(clip_id="c_trim", asset_id="vid1", in_frame=0, out_frame=100, timeline_start_frame=0)
    c_after = Clip(clip_id="c_after", asset_id="vid2", in_frame=0, out_frame=50, timeline_start_frame=100)
    engine.insert_clip(empty_timeline, "V1", c)
    engine.insert_clip(empty_timeline, "V1", c_after)

    # Trim out_frame from 100 to 80 with ripple=True
    engine.trim_clip(empty_timeline, "V1", "c_trim", out_frame=80, ripple=True)

    track_v1 = empty_timeline.get_track("V1")
    clips = {cl.clip_id: cl for cl in track_v1.clips}
    assert clips["c_trim"].timeline_end_frame == 80
    # c_after should have shifted backward from 100 to 80
    assert clips["c_after"].timeline_start_frame == 80


def test_timeline_ripple_delete(empty_timeline):
    engine = TimelineEngine()
    c1 = Clip(clip_id="c1", asset_id="v1", in_frame=0, out_frame=50, timeline_start_frame=0)
    c2 = Clip(clip_id="c2", asset_id="v2", in_frame=0, out_frame=30, timeline_start_frame=50)
    c3 = Clip(clip_id="c3", asset_id="v3", in_frame=0, out_frame=40, timeline_start_frame=80)
    engine.insert_clip(empty_timeline, "V1", c1)
    engine.insert_clip(empty_timeline, "V1", c2)
    engine.insert_clip(empty_timeline, "V1", c3)

    # Delete c2 (duration 30) with ripple
    engine.ripple_delete(empty_timeline, "V1", "c2")

    track_v1 = empty_timeline.get_track("V1")
    assert len(track_v1.clips) == 2
    # c3 should have shifted from 80 to 50
    assert track_v1.clips[1].clip_id == "c3"
    assert track_v1.clips[1].timeline_start_frame == 50


def test_timeline_close_gaps(empty_timeline):
    engine = TimelineEngine()
    c1 = Clip(clip_id="c1", asset_id="v1", in_frame=0, out_frame=30, timeline_start_frame=0)
    c2 = Clip(clip_id="c2", asset_id="v2", in_frame=0, out_frame=30, timeline_start_frame=50)  # Gap of 20 frames
    c3 = Clip(clip_id="c3", asset_id="v3", in_frame=0, out_frame=30, timeline_start_frame=100) # Gap of 20 frames
    engine.insert_clip(empty_timeline, "V1", c1)
    engine.insert_clip(empty_timeline, "V1", c2)
    engine.insert_clip(empty_timeline, "V1", c3)

    gaps = engine.close_gaps(empty_timeline, "V1")
    assert gaps == 2

    track_v1 = empty_timeline.get_track("V1")
    assert track_v1.clips[0].timeline_start_frame == 0
    assert track_v1.clips[1].timeline_start_frame == 30
    assert track_v1.clips[2].timeline_start_frame == 60


# ----------------------------------------------------------------------
# 2. Undo / Redo History Tests
# ----------------------------------------------------------------------

def test_timeline_history_undo_redo():
    history = TimelineHistory()
    proj = Project(metadata=ProjectMetadata(title="Version 1"))

    history.record_operation(proj, "Initial setup")
    assert history.can_undo is True

    # Mutate project
    proj.metadata.title = "Version 2 (After cut)"
    history.record_operation(proj, "Cut applied")

    proj.metadata.title = "Version 3 (After delete)"

    # Undo
    restored, desc = history.undo(proj)
    assert restored.metadata.title == "Version 2 (After cut)"

    # Undo again
    restored2, desc2 = history.undo(restored)
    assert restored2.metadata.title == "Version 1"

    # Redo
    redone, desc_redo = history.redo(restored2)
    assert redone.metadata.title == "Version 2 (After cut)"


# ----------------------------------------------------------------------
# 3. Comprehensive Rendering Test (4 clips, 2 cuts, 2 transitions, 1 overlay)
# ----------------------------------------------------------------------

def test_real_render_complex_montage(tmp_path: Path):
    """Produces a real MP4 montage with 4 clips, 2 hard cuts, 2 transitions, and an overlay layer."""
    # 1. Generate 5 synthetic media files with video & audio
    clips_dir = tmp_path / "raw_footage"
    clips_dir.mkdir(parents=True, exist_ok=True)

    colors = ["red", "blue", "green", "yellow", "white"]
    freqs = [440, 554, 659, 880, 1000]
    media_paths = {}

    for idx, (color, freq) in enumerate(zip(colors, freqs)):
        fn = clips_dir / f"clip_{color}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s=480x270:d=2:r=30",
            "-f", "lavfi", "-i", f"sine=frequency={freq}:duration=2",
            "-c:v", "libx264", "-c:a", "aac", str(fn)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        media_paths[color] = fn

    # 2. Build Project
    prober = FFprobeProber()
    pool_assets = {}
    for color, p in media_paths.items():
        prober.probe_file(p)
        pool_assets[f"asset_{color}"] = MediaAsset(
            asset_id=f"asset_{color}",
            file_path=str(p),
            format_name="mp4",
            duration_seconds=2.0,
            size_bytes=p.stat().st_size,
            video_streams=[],
            audio_streams=[],
        )

    # Timeline layout:
    # 4 clips on V1 (each 2 seconds = 60 frames):
    # - Clip 1: Red (0 -> 60)
    # - Clip 2: Blue (60 -> 120) [Cut 1: Hard Cut from Clip 1]
    # - Clip 3: Green (120 -> 180) [Cut 2: Transition 1 (crossfade 15 frames = 0.5s)]
    # - Clip 4: Yellow (180 -> 240) [Cut 3: Transition 2 (wipe_left 15 frames = 0.5s)]
    # Plus Track V2 (Overlay): White box overlaying at frame 30 to frame 90 (t=1.0s to 3.0s)
    c1 = Clip(clip_id="c_red", asset_id="asset_red", in_frame=0, out_frame=60, timeline_start_frame=0)
    c2 = Clip(clip_id="c_blue", asset_id="asset_blue", in_frame=0, out_frame=60, timeline_start_frame=60)
    c3 = Clip(
        clip_id="c_green",
        asset_id="asset_green",
        in_frame=0,
        out_frame=60,
        timeline_start_frame=120,
        transition_in=Transition(type=TransitionType.CROSSFADE, duration_frames=15),
    )
    c4 = Clip(
        clip_id="c_yellow",
        asset_id="asset_yellow",
        in_frame=0,
        out_frame=60,
        timeline_start_frame=180,
        transition_in=Transition(type=TransitionType.WIPE_LEFT, duration_frames=15),
    )

    # Overlay clip on V2 with scale 0.5 and opacity 0.8
    c_overlay = Clip(
        clip_id="c_overlay_white",
        asset_id="asset_white",
        in_frame=0,
        out_frame=60,
        timeline_start_frame=30,
        transform=Transform(scale_x=0.5, scale_y=0.5, opacity=0.8, position_x=50, position_y=30),
    )

    # Audio track A1
    a1_c1 = Clip(clip_id="a_red", asset_id="asset_red", in_frame=0, out_frame=60, timeline_start_frame=0)
    a1_c2 = Clip(clip_id="a_blue", asset_id="asset_blue", in_frame=0, out_frame=60, timeline_start_frame=60)
    a1_c3 = Clip(clip_id="a_green", asset_id="asset_green", in_frame=0, out_frame=60, timeline_start_frame=120)
    a1_c4 = Clip(clip_id="a_yellow", asset_id="asset_yellow", in_frame=0, out_frame=60, timeline_start_frame=180)

    proj = Project(
        metadata=ProjectMetadata(title="Full Montage Test"),
        settings=ProjectSettings(width=480, height=270, fps=30.0),
        media_pool={"assets": pool_assets},
        timeline=Timeline(
            tracks=[
                Track(track_id="V1", name="Main Story", kind=TrackKind.VIDEO, index=0, clips=[c1, c2, c3, c4]),
                Track(track_id="V2", name="Graphic Overlay", kind=TrackKind.GRAPHIC, index=1, clips=[c_overlay]),
                Track(track_id="A1", name="Dialogue & Bed", kind=TrackKind.AUDIO, index=2, clips=[a1_c1, a1_c2, a1_c3, a1_c4]),
            ]
        ),
    )

    proj_file = tmp_path / "montage_project.json"
    proj.save_to_file(proj_file)

    # 3. Render MP4 deliverable
    output_mp4 = tmp_path / "final_montage.mp4"
    engine = RenderEngine()
    preset = ExportPreset(
        name="web_test",
        width=480,
        height=270,
        fps=30.0,
        hwaccel=HardwareAccel.NONE,
    )

    rendered_path = engine.render_project(proj, preset, output_mp4)

    # 4. Verification of the real reproducible MP4 file
    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 1000

    # Probe the rendered deliverable
    inspected = prober.probe_file(rendered_path)
    assert inspected.has_video is True
    assert inspected.has_audio is True
    assert inspected.primary_video.width == 480
    assert inspected.primary_video.height == 270
    assert round(inspected.primary_video.frame_rate_info.fps) == 30
    # Expected duration: 4 clips of 2s with two 0.5s transitions = 2 + 2 + 1.5 + 1.5 = 7.0s
    assert abs(inspected.duration_seconds - 7.0) < 0.3


# ----------------------------------------------------------------------
# 4. CLI Timeline and Render Commands
# ----------------------------------------------------------------------

def test_cli_timeline_inspect_and_render(tmp_path: Path):
    runner = CliRunner()
    proj_path = tmp_path / "cli_test_proj.json"

    # Create project via 'hyperedit project create'
    res_create = runner.invoke(cli, ["project", "create", str(proj_path), "--title", "CLI Render Test", "--preset", "1080p"])
    assert res_create.exit_code == 0

    # Inspect timeline
    res_inspect = runner.invoke(cli, ["timeline", "inspect", str(proj_path)])
    assert res_inspect.exit_code == 0
    assert "Timeline Inspection" in res_inspect.output

    # Validate timeline
    res_val = runner.invoke(cli, ["timeline", "validate", str(proj_path)])
    assert res_val.exit_code == 0
    assert "Zero collisions" in res_val.output

    # Dry-run render
    res_render_dry = runner.invoke(cli, ["render", str(proj_path), "-o", str(tmp_path / "out.mp4"), "--dry-run"])
    assert res_render_dry.exit_code == 0
    assert "Filtergraph Complex" in res_render_dry.output

