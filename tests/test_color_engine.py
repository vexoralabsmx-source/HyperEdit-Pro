"""Comprehensive test suite for HyperEdit Pro Color Correction and Grading Engine."""

import json
from pathlib import Path
from click.testing import CliRunner
import cv2
import numpy as np
import pytest

from hyperedit.cli.main import cli
from hyperedit.color.cube_lut import CubeLUT
from hyperedit.color.engine import ColorGradingEngine
from hyperedit.color.presets import COLOR_PRESETS, blend_color_grades
from hyperedit.core.models.color import (
    ColorGradeConfig,
)
from hyperedit.core.models.export import ExportPreset, HardwareAccel
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Clip, Timeline, Track, TrackKind
from hyperedit.rendering.engine import RenderEngine


@pytest.fixture
def synthetic_neutral_video(tmp_path: Path) -> Path:
    """Generate a 1-second 640x360 30fps clip with neutral mid-gray (IRE 50 = ~128)."""
    out_file = tmp_path / "neutral_gray.mp4"
    width, height, fps, total_frames = 640, 360, 30.0, 30

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    for _ in range(total_frames):
        # 50% neutral gray with slight gradient to test tonal range
        frame = np.full((height, width, 3), 128, dtype=np.uint8)
        # Add color patches: skin tone, blue patch, highlight, shadow
        cv2.rectangle(frame, (50, 50), (150, 150), (140, 160, 210), -1)  # Warm skin tone BGR
        cv2.rectangle(frame, (200, 50), (300, 150), (220, 120, 50), -1)  # Teal/blue patch
        cv2.rectangle(frame, (350, 50), (450, 150), (235, 235, 235), -1) # Highlight
        cv2.rectangle(frame, (500, 50), (600, 150), (25, 25, 25), -1)    # Shadow
        writer.write(frame)

    writer.release()
    return out_file


@pytest.fixture
def synthetic_dark_cool_video(tmp_path: Path) -> Path:
    """Generate an underexposed, cool-tinted clip to test shot matching."""
    out_file = tmp_path / "dark_cool.mp4"
    width, height, fps, total_frames = 640, 360, 30.0, 30

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_file), fourcc, fps, (width, height))

    for _ in range(total_frames):
        # Dark bluish gray
        frame = np.full((height, width, 3), (90, 70, 50), dtype=np.uint8)
        cv2.rectangle(frame, (50, 50), (150, 150), (110, 80, 60), -1)
        writer.write(frame)

    writer.release()
    return out_file


def test_color_presets_and_blending() -> None:
    """Verify presence of all 6 curated presets and fractional look strength blending."""
    assert len(COLOR_PRESETS) == 6
    assert "cinematic_neutral" in COLOR_PRESETS
    assert "film_stock_5207" in COLOR_PRESETS
    assert "monochrome_panchro" in COLOR_PRESETS

    base = ColorGradeConfig()
    target = COLOR_PRESETS["warm_editorial"]

    # 50% blend
    blended_50 = blend_color_grades(base, target, factor=0.5)
    assert abs(blended_50.temperature - 9.0) <= 0.1
    assert abs(blended_50.contrast - 1.02) <= 0.01

    # 100% blend
    blended_100 = blend_color_grades(base, target, factor=1.0)
    assert blended_100.temperature == target.temperature


def test_histogram_analysis_and_clipping(synthetic_neutral_video: Path, tmp_path: Path) -> None:
    """Verify multi-channel histogram evaluation, dynamic range estimation, and visual graph generation."""
    metrics = ColorGradingEngine.analyze_histogram(synthetic_neutral_video)

    assert 110.0 <= metrics.mean_luma <= 140.0
    assert metrics.min_luma <= 35.0
    assert metrics.max_luma >= 220.0
    assert metrics.shadow_clipping_pct < 5.0
    assert metrics.highlight_clipping_pct < 5.0

    # Test visual histogram PNG chart generation
    chart_png = tmp_path / "test_histogram.png"
    ColorGradingEngine.generate_histogram_image(synthetic_neutral_video, chart_png)
    assert chart_png.is_file()
    assert chart_png.stat().st_size > 2000


def test_exposure_contrast_saturation_modifications(synthetic_neutral_video: Path, tmp_path: Path) -> None:
    """Verify quantitative image alterations produced by exposure, contrast, and saturation controls."""
    engine = ColorGradingEngine()
    initial_metrics = engine.analyze_histogram(synthetic_neutral_video)

    # 1. Test Exposure boost (+1.5 EV)
    exp_cfg = ColorGradeConfig(exposure_ev=1.5)
    exp_out = tmp_path / "exp_boost.mp4"
    engine.apply_color_grade_to_video(synthetic_neutral_video, exp_out, exp_cfg)
    exp_metrics = engine.analyze_histogram(exp_out)
    assert exp_metrics.mean_luma > initial_metrics.mean_luma + 15.0

    # 2. Test Monochrome (Saturation = 0.0)
    mono_cfg = ColorGradeConfig(saturation=0.0)
    mono_out = tmp_path / "mono.mp4"
    engine.apply_color_grade_to_video(synthetic_neutral_video, mono_out, mono_cfg)
    mono_metrics = engine.analyze_histogram(mono_out)
    mr, mg, mb = mono_metrics.mean_rgb
    # In pure monochrome, R, G, B channel means should be nearly identical (within YUV compression margin)
    assert abs(mr - mg) <= 3.0
    assert abs(mg - mb) <= 3.0


def test_shot_matching_tonal_consistency(
    synthetic_neutral_video: Path,
    synthetic_dark_cool_video: Path,
    tmp_path: Path,
) -> None:
    """Verify shot matching aligns underexposed cool target clip to warm neutral reference."""
    engine = ColorGradingEngine()

    # Match target (dark_cool) to reference (neutral)
    telemetry = engine.match_shots(
        reference_media=synthetic_neutral_video,
        target_media=synthetic_dark_cool_video,
    )

    # Corrective exposure should be positive to lift dark target
    assert telemetry.applied_grade.exposure_ev > 0.3
    # Corrective temperature should be warm (> 0) to neutralize cool cast
    assert telemetry.applied_grade.temperature > 0.0

    # Render matched shot
    matched_out = tmp_path / "matched_result.mp4"
    engine.apply_color_grade_to_video(synthetic_dark_cool_video, matched_out, telemetry.applied_grade)

    # Measure output luma: should be significantly closer to reference
    matched_metrics = engine.analyze_histogram(matched_out)
    ref_metrics = engine.analyze_histogram(synthetic_neutral_video)
    orig_diff = abs(telemetry.source_metrics.mean_luma - ref_metrics.mean_luma)
    new_diff = abs(matched_metrics.mean_luma - ref_metrics.mean_luma)

    assert new_diff < orig_diff, f"Expected matched diff {new_diff} to be less than original diff {orig_diff}"


def test_cube_lut_parse_apply_and_render(synthetic_neutral_video: Path, tmp_path: Path) -> None:
    """Verify generating, saving, parsing, and applying a .cube 3D LUT."""
    # 1. Generate programmatic 17x17x17 warm golden LUT
    lut = CubeLUT.generate_creative_lut(size=17, style="warm_golden")
    lut_file = tmp_path / "warm_golden.cube"
    lut.save(lut_file)

    assert lut_file.is_file()

    # 2. Parse from file
    parsed_lut = CubeLUT.from_file(lut_file)
    assert parsed_lut.size == 17
    assert parsed_lut.table.shape == (17, 17, 17, 3)

    # 3. Apply via FFmpeg lut3d filter
    engine = ColorGradingEngine()
    grade_cfg = ColorGradeConfig(lut_path=str(lut_file))
    graded_mov = tmp_path / "lut_graded.mp4"
    engine.apply_color_grade_to_video(synthetic_neutral_video, graded_mov, grade_cfg)

    assert graded_mov.is_file()
    assert graded_mov.stat().st_size > 1000


def test_sdr_rec709_color_space_audit(synthetic_neutral_video: Path) -> None:
    """Verify color management audit correctly identifies SDR Rec.709 characteristics."""
    report = ColorGradingEngine.audit_color_space(synthetic_neutral_video)

    assert report.is_hdr is False
    assert report.is_sdr_rec709_compliant is True
    assert len(report.recommendations) > 0


def test_timeline_integration_with_color_grade(synthetic_neutral_video: Path, tmp_path: Path) -> None:
    """Verify Project timeline with clip-level color grade renders properly into master deliverable."""
    # Build Project with 1 graded clip on track V1
    project = Project(
        metadata=ProjectMetadata(title="ColorGradeTimelineTest"),
        settings=ProjectSettings(width=640, height=360, fps=30.0),
        timeline=Timeline(
            tracks=[
                Track(
                    track_id="V1",
                    kind=TrackKind.VIDEO,
                    clips=[
                        Clip(
                            clip_id="c1",
                            asset_id="neutral_asset",
                            in_frame=0,
                            out_frame=30,
                            timeline_start_frame=0,
                            color_grade=ColorGradeConfig(
                                preset_name="warm_editorial",
                                preset_strength=0.8,
                            ),
                        )
                    ],
                )
            ]
        ),
    )
    project.media_pool.add_asset(
        MediaAsset(
            asset_id="neutral_asset",
            file_path=str(synthetic_neutral_video),
            file_size_bytes=synthetic_neutral_video.stat().st_size,
            duration_seconds=1.0,
            width=640,
            height=360,
            fps=30.0,
        )
    )

    engine = RenderEngine()
    preset = ExportPreset(
        name="web_test",
        width=640,
        height=360,
        fps=30.0,
        hwaccel=HardwareAccel.NONE,
    )
    output_mp4 = tmp_path / "final_graded_film.mp4"
    rendered = engine.render_project(project, preset, output_mp4)

    assert rendered.is_file()
    assert rendered.stat().st_size > 1000


def test_cli_color_commands(
    synthetic_neutral_video: Path,
    synthetic_dark_cool_video: Path,
    tmp_path: Path,
) -> None:
    """Verify execution of CLI color subcommands: presets, grade, analyze, match, audit."""
    runner = CliRunner()

    # 1. hyperedit color presets --json
    res_pres = runner.invoke(cli, ["color", "presets", "--json"])
    assert res_pres.exit_code == 0
    pres_dict = json.loads(res_pres.output)
    assert "film_stock_5207" in pres_dict

    # 2. hyperedit color analyze --json
    res_an = runner.invoke(cli, ["color", "analyze", str(synthetic_neutral_video), "--json"])
    assert res_an.exit_code == 0
    an_dict = json.loads(res_an.output)
    assert "mean_luma" in an_dict

    # 3. hyperedit color audit --json
    res_aud = runner.invoke(cli, ["color", "audit", str(synthetic_neutral_video), "--json"])
    assert res_aud.exit_code == 0
    aud_dict = json.loads(res_aud.output)
    assert "is_sdr_rec709_compliant" in aud_dict

    # 4. hyperedit color grade
    graded_mp4 = tmp_path / "cli_graded.mp4"
    res_gr = runner.invoke(
        cli,
        ["color", "grade", str(synthetic_neutral_video), "-o", str(graded_mp4), "--preset", "warm_editorial"],
    )
    assert res_gr.exit_code == 0
    assert graded_mp4.is_file()

    # 5. hyperedit color match
    matched_mp4 = tmp_path / "cli_matched.mp4"
    res_m = runner.invoke(
        cli,
        ["color", "match", str(synthetic_neutral_video), str(synthetic_dark_cool_video), "-o", str(matched_mp4), "--json"],
    )
    assert res_m.exit_code == 0
    assert matched_mp4.is_file()
