"""Comprehensive test suite for HyperEdit Pro Motion Graphics & HyperFrames Integration (Stage 6)."""

import json
from pathlib import Path
import subprocess
import pytest
from click.testing import CliRunner

from hyperedit.adapters.hyperframes import CompositionTemplate, HyperFramesAdapter
from hyperedit.audio.models import BeatInfo
from hyperedit.cli.main import cli
from hyperedit.core.models.export import ExportPreset
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Clip, Timeline, Track, TrackKind
from hyperedit.core.models.transforms import (
    AnimatedProperty,
    InterpolationMode,
    Keyframe,
    Transform,
)
from hyperedit.motion.engine import MotionEngine
from hyperedit.motion.interpolator import KeyframeInterpolator, solve_bezier_y_for_x
from hyperedit.motion.presets import STANDARD_MOTION_PRESETS
from hyperedit.rendering.engine import RenderEngine


@pytest.fixture
def synthetic_base_video(tmp_path: Path) -> Path:
    """Generate a 4.0s 1080p synthetic MP4 video clip."""
    video_path = tmp_path / "base_footage.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=0x111116:s=1920x1080:d=4.0:r=30",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=4.0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        str(video_path),
    ]
    subprocess.run(cmd, check=True)
    return video_path


def test_motion_presets_catalog() -> None:
    """Verify all curated motion graphics presets are populated with design principles and parameters."""
    expected_keys = [
        "minimal_editorial",
        "cinematic_luxury",
        "tech_product",
        "corporate_clean",
        "energetic_social",
        "typography_focus",
    ]
    for key in expected_keys:
        assert key in STANDARD_MOTION_PRESETS
        p = STANDARD_MOTION_PRESETS[key]
        assert len(p.design_principles) >= 3
        assert "background" in p.color_palette
        assert "title_font" in p.typography
        assert "ease_curve" in p.motion
        assert len(p.restrictions) >= 1


def test_keyframe_interpolator_curves() -> None:
    """Verify numerical interpolation for linear, ease_in, ease_out, bezier, spring, and overshoot."""
    # Linear: 0 -> 100 over 100 frames
    linear_prop = AnimatedProperty(
        property_name="position_x",
        base_value=0.0,
        keyframes=[
            Keyframe(frame=0, value=0.0, interpolation=InterpolationMode.LINEAR),
            Keyframe(frame=100, value=100.0, interpolation=InterpolationMode.LINEAR),
        ],
    )
    assert KeyframeInterpolator.evaluate(linear_prop, 0) == 0.0
    assert KeyframeInterpolator.evaluate(linear_prop, 50) == 50.0
    assert KeyframeInterpolator.evaluate(linear_prop, 100) == 100.0

    # Ease Out: progression is faster at start
    ease_out_prop = AnimatedProperty(
        property_name="opacity",
        base_value=0.0,
        keyframes=[
            Keyframe(frame=0, value=0.0, interpolation=InterpolationMode.EASE_OUT),
            Keyframe(frame=100, value=1.0, interpolation=InterpolationMode.EASE_OUT),
        ],
    )
    val_mid = KeyframeInterpolator.evaluate(ease_out_prop, 50)
    assert val_mid > 0.6  # Ease-out reaches more than 50% by halfway mark

    # Overshoot: reaches above 1.0 before settling
    overshoot_prop = AnimatedProperty(
        property_name="scale",
        base_value=0.0,
        keyframes=[
            Keyframe(frame=0, value=0.0, interpolation=InterpolationMode.OVERSHOOT),
            Keyframe(frame=100, value=1.0, interpolation=InterpolationMode.OVERSHOOT),
        ],
    )
    val_peak = KeyframeInterpolator.evaluate(overshoot_prop, 80)
    assert val_peak > 1.0  # Overshoot exceeds 1.0 target

    # Cubic Bezier
    y_val = solve_bezier_y_for_x(0.5, 0.25, 0.1, 0.25, 1.0)
    assert 0.0 < y_val < 1.0


def test_ken_burns_and_motion_engine() -> None:
    """Verify Ken Burns camera drift and spatial transform evaluation along clip timeline."""
    engine = MotionEngine()
    clip = Clip(clip_id="c1", asset_id="a1", in_frame=0, out_frame=90, timeline_start_frame=0)

    # Apply Ken Burns slow zoom-in from 1.0 to 1.12 with pan
    engine.apply_ken_burns(
        clip=clip,
        start_scale=1.0,
        end_scale=1.12,
        start_pan_x=0.0,
        end_pan_x=40.0,
    )

    t_start = engine.interpolate_transform(clip, 0)
    assert t_start["scale_x"] == 1.0
    assert t_start["position_x"] == 0.0

    t_mid = engine.interpolate_transform(clip, 45)
    assert 1.0 < t_mid["scale_x"] < 1.12
    assert 0.0 < t_mid["position_x"] < 40.0

    t_end = engine.interpolate_transform(clip, 90)
    assert t_end["scale_x"] == 1.12
    assert t_end["position_x"] == 40.0


def test_create_three_hyperframes_compositions(tmp_path: Path) -> None:
    """Verify authoring of the three required motion graphics compositions adhering to HyperFrames contract."""
    adapter = HyperFramesAdapter()

    # 1. Cinematic Intro
    intro_html = tmp_path / "cinematic_intro.html"
    adapter.create_composition(
        composition_id="intro_comp",
        template_type=CompositionTemplate.CINEMATIC_INTRO,
        params={"title": "PORSCHE 911 GT3", "subtitle": "MOTORSPORT HERITAGE", "kicker": "WEISSACH PACKAGE"},
        output_file=intro_html,
        preset_name="cinematic_luxury",
        duration_sec=3.0,
    )
    assert intro_html.is_file()
    intro_text = intro_html.read_text(encoding="utf-8")
    assert 'data-composition-id="intro_comp"' in intro_text
    assert 'window.__timelines["intro_comp"]' in intro_text
    assert "PORSCHE 911 GT3" in intro_text

    # 2. Product Showcase
    product_html = tmp_path / "product_showcase.html"
    adapter.create_composition(
        composition_id="product_comp",
        template_type=CompositionTemplate.PRODUCT_SHOWCASE,
        params={
            "name": "NEURAL ACCELERATOR X1",
            "badge": "TSMC 3NM",
            "specs": ["45 TOPS Compute", "Sub-1ms Latency"],
            "price": "$1,299",
        },
        output_file=product_html,
        preset_name="tech_product",
        duration_sec=3.0,
    )
    assert product_html.is_file()
    prod_text = product_html.read_text(encoding="utf-8")
    assert 'data-composition-id="product_comp"' in prod_text
    assert "NEURAL ACCELERATOR X1" in prod_text
    assert "TSMC 3NM" in prod_text

    # 3. Audio-Reactive Graphic
    reactive_html = tmp_path / "audio_reactive.html"
    adapter.create_composition(
        composition_id="reactive_comp",
        template_type=CompositionTemplate.AUDIO_REACTIVE,
        params={"title": "LIVE BEAT MONITOR", "bpm": 128.0},
        output_file=reactive_html,
        preset_name="energetic_social",
        duration_sec=3.0,
    )
    assert reactive_html.is_file()
    react_text = reactive_html.read_text(encoding="utf-8")
    assert 'data-composition-id="reactive_comp"' in react_text
    assert "LIVE BEAT MONITOR" in react_text

    # Sync reactive composition with beats
    beat_info = BeatInfo(
        bpm=120.0,
        confidence=0.9,
        beat_interval_sec=0.5,
        beat_timestamps=[0.5, 1.0, 1.5, 2.0, 2.5],
    )
    synced_html = tmp_path / "synced_reactive.html"
    adapter.sync_with_audio_beats(reactive_html, beats=beat_info, output_file=synced_html)
    synced_text = synced_html.read_text(encoding="utf-8")
    assert ".beat-pulse" in synced_text
    assert "scale: 1.08" in synced_text


def test_render_three_transparent_motion_compositions(tmp_path: Path) -> None:
    """Render all three compositions to transparent video overlays and verify alpha channels via FFprobe."""
    adapter = HyperFramesAdapter()

    # 1. Render Cinematic Intro to transparent ProRes 4444 (.mov)
    intro_html = tmp_path / "test_intro.html"
    adapter.create_composition(
        composition_id="test_intro",
        template_type="cinematic_intro",
        params={"title": "MASTER TITLES"},
        output_file=intro_html,
        duration_sec=2.0,
    )
    intro_mov = tmp_path / "intro_overlay.mov"
    out_mov = adapter.render_composition(intro_html, intro_mov, format="mov", fps=30.0)
    assert out_mov.is_file()
    assert out_mov.stat().st_size > 5000

    # 2. Render Product Showcase to transparent ProRes 4444 (.mov)
    prod_html = tmp_path / "test_prod.html"
    adapter.create_composition(
        composition_id="test_prod",
        template_type="product_showcase",
        params={"name": "SMART WATCH PRO"},
        output_file=prod_html,
        duration_sec=2.0,
    )
    prod_mov = tmp_path / "prod_overlay.mov"
    out_prod = adapter.render_composition(prod_html, prod_mov, format="mov", fps=30.0)
    assert out_prod.is_file()

    # 3. Render Audio-Reactive Graphic to transparent ProRes 4444 (.mov)
    react_html = tmp_path / "test_react.html"
    adapter.create_composition(
        composition_id="test_react",
        template_type="audio_reactive",
        params={"title": "BEAT SYNC"},
        output_file=react_html,
        duration_sec=2.0,
    )
    react_mov = tmp_path / "react_overlay.mov"
    out_react = adapter.render_composition(react_html, react_mov, format="mov", fps=30.0)
    assert out_react.is_file()

    # Verify that all 3 renders possess authentic alpha channel via FFprobe
    for mov_file in (out_mov, out_prod, out_react):
        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=pix_fmt,duration",
            "-of",
            "json",
            str(mov_file),
        ]
        proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)
        stream = data["streams"][0]
        # Pixel format must contain 'a' indicating alpha channel (e.g. yuva444p12le or yuva444p10le)
        assert "a" in stream["pix_fmt"], f"Expected alpha pixel format, got {stream['pix_fmt']}"
        assert abs(float(stream["duration"]) - 2.0) < 0.2


def test_timeline_integration_and_final_mp4_render(
    synthetic_base_video: Path,
    tmp_path: Path,
) -> None:
    """Verify complete end-to-end integration: overlaying rendered motion graphic on edited timeline."""
    adapter = HyperFramesAdapter()

    # 1. Author and render transparent motion overlay (2.0s duration)
    comp_html = tmp_path / "title_overlay.html"
    adapter.create_composition(
        composition_id="title_overlay",
        template_type=CompositionTemplate.CINEMATIC_INTRO,
        params={"title": "HYPEREDIT MASTER"},
        output_file=comp_html,
        duration_sec=2.0,
    )
    overlay_mov = tmp_path / "title_overlay.mov"
    adapter.render_composition(comp_html, overlay_mov, format="mov", fps=30.0)

    # 2. Build multi-track Project: V1 base video + GRAPHIC motion overlay
    project = Project(
        metadata=ProjectMetadata(title="MotionIntegrationTest"),
        settings=ProjectSettings(width=1920, height=1080, fps=30.0),
        timeline=Timeline(
            tracks=[
                Track(
                    track_id="V1",
                    kind=TrackKind.VIDEO,
                    clips=[
                        Clip(clip_id="base1", asset_id="base_vid", in_frame=0, out_frame=60, timeline_start_frame=0),
                        Clip(clip_id="base2", asset_id="base_vid", in_frame=60, out_frame=120, timeline_start_frame=60),
                    ],
                )
            ]
        ),
    )
    project.media_pool.add_asset(
        MediaAsset(
            asset_id="base_vid",
            file_path=str(synthetic_base_video),
            file_size_bytes=synthetic_base_video.stat().st_size,
            duration_seconds=4.0,
            width=1920,
            height=1080,
            fps=30.0,
        )
    )

    # 3. Attach overlay to GRAPHIC track at frame 0 (plays for first 2 seconds)
    graphic_clip = adapter.import_to_timeline(
        project=project,
        overlay_video_path=overlay_mov,
        track_id="GRAPHIC",
        start_frame=0,
    )
    assert graphic_clip.timeline_duration_frames == 60
    assert len(project.timeline.tracks) == 2

    # 4. Render master deliverable with RenderEngine
    engine = RenderEngine()
    preset = ExportPreset(
        preset_id="web_1080p",
        name="Web 1080p",
        width=1920,
        height=1080,
        fps=30.0,
    )
    final_output = tmp_path / "final_composite_with_motion.mp4"
    rendered_file = engine.render_project(project, preset, final_output)

    assert rendered_file.is_file()
    assert rendered_file.stat().st_size > 10000

    # 5. Probe final deliverable to verify frame-accurate duration and integrity
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=width,height",
        "-of",
        "json",
        str(rendered_file),
    ]
    proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    res_data = json.loads(proc.stdout)
    duration = float(res_data["format"]["duration"])
    # Base footage was 4.0s (120 frames at 30 fps)
    assert abs(duration - 4.0) < 0.2
    assert res_data["streams"][0]["width"] == 1920
    assert res_data["streams"][0]["height"] == 1080


def test_cli_motion_commands(synthetic_base_video: Path, tmp_path: Path) -> None:
    """Verify all CLI motion subcommands execute properly and emit structured output."""
    runner = CliRunner()

    # 1. hyperedit motion presets --json
    res_pres = runner.invoke(cli, ["motion", "presets", "--json"])
    assert res_pres.exit_code == 0
    pres_data = json.loads(res_pres.output)
    assert "cinematic_luxury" in pres_data

    # 2. hyperedit motion create
    comp_html = tmp_path / "cli_intro.html"
    res_create = runner.invoke(
        cli,
        ["motion", "create", "cinematic_intro", "-o", str(comp_html), "--title", "CLI SHOWCASE"],
    )
    assert res_create.exit_code == 0
    assert comp_html.is_file()

    # 3. hyperedit motion render
    overlay_mov = tmp_path / "cli_overlay.mov"
    res_render = runner.invoke(
        cli,
        ["motion", "render", str(comp_html), "-o", str(overlay_mov)],
    )
    assert res_render.exit_code == 0
    assert overlay_mov.is_file()

    # 4. hyperedit motion overlay onto project.json
    proj_path = tmp_path / "motion_proj.json"
    project = Project(
        metadata=ProjectMetadata(title="CliMotionTest"),
        settings=ProjectSettings(width=1920, height=1080, fps=30.0),
    )
    with open(proj_path, "w", encoding="utf-8") as f:
        f.write(project.model_dump_json(indent=2))

    res_overlay = runner.invoke(
        cli,
        ["motion", "overlay", str(proj_path), str(overlay_mov), "--track", "GRAPHIC", "--start-frame", "0"],
    )
    assert res_overlay.exit_code == 0

    # Verify project file was mutated and saved
    with open(proj_path, "r", encoding="utf-8") as f:
        updated_data = json.load(f)
    tracks = updated_data["timeline"]["tracks"]
    assert any(t["track_id"] == "GRAPHIC" for t in tracks)

