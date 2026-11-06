"""CLI commands for VFX, motion tracking, masking, compositing and 3D integration."""

import json
from pathlib import Path
from typing import Optional, Tuple
import click

from hyperedit.adapters.blender import BlenderAdapter
from hyperedit.vfx.compositing import LayerCompositor
from hyperedit.vfx.effects import CinematicEffects
from hyperedit.vfx.masks import MaskDefinition, MaskGenerator, MaskShape
from hyperedit.vfx.models import (
    BlenderRenderConfig,
    BlenderRenderEngine,
    BloomGlowConfig,
    CameraShakeConfig,
    ChromaKeyConfig,
    FilmGrainConfig,
    MotionBlurConfig,
    TrackingMethod,
)
from hyperedit.vfx.tracking import MotionTracker


@click.group(name="vfx")
def vfx_group() -> None:
    """Motion tracking, masking, compositing, cinematic VFX and 3D integration."""
    pass


@vfx_group.command(name="track")
@click.argument("video_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_json", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--bbox", "bbox_str", required=True, help="Initial bounding box 'x,y,w,h' in pixels")
@click.option("--method", type=click.Choice(["template", "lk"]), default="template", help="Tracking algorithm")
@click.option("--max-frames", default=None, type=int, help="Optional frame limit for tracking")
def track_command(video_file: Path, output_json: Path, bbox_str: str, method: str, max_frames: Optional[int]) -> None:
    """Track a moving object across video frames and output tracking telemetry JSON."""
    try:
        parts = [float(p.strip()) for p in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError("Expected 4 comma-separated values: x,y,w,h")
        bbox = (parts[0], parts[1], parts[2], parts[3])
    except Exception as e:
        click.secho(f"Invalid bounding box '{bbox_str}': {e}", fg="red", err=True)
        raise click.Abort()

    tracker = MotionTracker()
    track_method = TrackingMethod.REGION_TEMPLATE if method == "template" else TrackingMethod.POINT_LK

    try:
        telemetry = tracker.track_region(video_file, initial_bbox=bbox, method=track_method, max_frames=max_frames)
        with open(output_json, "w", encoding="utf-8") as f:
            f.write(telemetry.model_dump_json(indent=2))

        click.secho(
            f"Tracking completed: {telemetry.tracked_frames}/{telemetry.total_frames} frames tracked "
            f"(mean confidence: {telemetry.mean_confidence:.2f}, lost: {telemetry.lost_frames}). "
            f"Saved to: {output_json}",
            fg="green",
        )
    except Exception as e:
        click.secho(f"Tracking error: {e}", fg="red", err=True)
        raise click.Abort()


@vfx_group.command(name="stabilize")
@click.argument("video_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_video", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--smoothing", default=15, type=int, help="Temporal trajectory smoothing window")
@click.option("--crop-border", default=0.05, type=float, help="Safe border crop margin ratio (0.0 to 0.2)")
def stabilize_command(video_file: Path, output_video: Path, smoothing: int, crop_border: float) -> None:
    """Stabilize video footage using 2D affine trajectory smoothing."""
    tracker = MotionTracker()
    try:
        tel = tracker.stabilize_video(video_file, output_video, smoothing_window=smoothing, crop_border_pct=crop_border)
        click.secho(
            f"Video stabilized: {tel.total_frames} frames (max displacement: {tel.max_displacement_px:.1f}px, "
            f"mean: {tel.mean_displacement_px:.1f}px). Output: {output_video}",
            fg="green",
        )
    except Exception as e:
        click.secho(f"Stabilization error: {e}", fg="red", err=True)
        raise click.Abort()


@vfx_group.command(name="key")
@click.argument("video_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_video", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--color", default="0x00FF00", help="Hex key color e.g. 0x00FF00 (green) or 0x0000FF (blue)")
@click.option("--similarity", default=0.3, type=float, help="Color distance similarity threshold (0.01 to 1.0)")
@click.option("--smoothness", default=0.1, type=float, help="Edge transition smoothness ramp")
def key_command(video_file: Path, output_video: Path, color: str, similarity: float, smoothness: float) -> None:
    """Chroma key green/blue screen footage into transparent ProRes 4444 video."""
    try:
        hex_val = int(color.replace("#", "").replace("0x", ""), 16)
        r = (hex_val >> 16) & 0xFF
        g = (hex_val >> 8) & 0xFF
        b = hex_val & 0xFF
    except Exception:
        r, g, b = 0, 255, 0

    config = ChromaKeyConfig(key_color_rgb=(r, g, b), similarity=similarity, smoothness=smoothness)
    try:
        out = LayerCompositor.render_chroma_keyed_video(video_file, output_video, config)
        click.secho(f"Chroma keying rendered with alpha channel: {out}", fg="green")
    except Exception as e:
        click.secho(f"Chroma keying error: {e}", fg="red", err=True)
        raise click.Abort()


@vfx_group.command(name="effect")
@click.argument("video_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_video", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--effect",
    "effect_type",
    required=True,
    type=click.Choice(["grain", "shake", "bloom", "motion_blur"]),
    help="Cinematic effect to apply",
)
@click.option("--intensity", default=0.2, type=float, help="Effect intensity")
def effect_command(video_file: Path, output_video: Path, effect_type: str, intensity: float) -> None:
    """Render a cinematic visual effect (grain, camera shake, bloom/glow, motion blur) onto video."""
    if effect_type == "grain":
        filt = CinematicEffects.build_film_grain_filter(FilmGrainConfig(intensity=intensity))
    elif effect_type == "shake":
        filt = CinematicEffects.build_camera_shake_filter(CameraShakeConfig(intensity_px=intensity * 20.0))
    elif effect_type == "bloom":
        filt = CinematicEffects.build_bloom_glow_filter(BloomGlowConfig(intensity=intensity * 1.5))
    elif effect_type == "motion_blur":
        filt = CinematicEffects.build_motion_blur_filter(MotionBlurConfig())
    else:
        filt = "null"

    try:
        out = CinematicEffects.render_effect_to_video(video_file, output_video, filt)
        click.secho(f"Applied cinematic effect '{effect_type}': {out}", fg="green")
    except Exception as e:
        click.secho(f"Effect render error: {e}", fg="red", err=True)
        raise click.Abort()


@vfx_group.command(name="blender-check")
@click.option("--json", "as_json", is_flag=True, help="Output diagnostic report as JSON")
def blender_check_command(as_json: bool) -> None:
    """Audit Blender CLI installation, version, and rendering capabilities."""
    adapter = BlenderAdapter()
    avail = adapter.is_available()
    version = adapter.get_version() if avail else None

    report = {
        "blender_available": avail,
        "executable_path": adapter.blender_bin,
        "version": version,
        "supported_engines": ["CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
        "transparency_supported": True,
    }

    if as_json:
        click.echo(json.dumps(report, indent=2))
    else:
        status_color = "green" if avail else "yellow"
        click.secho(f"Blender Available: {avail}", fg=status_color, bold=True)
        if avail:
            click.echo(f"Binary: {adapter.blender_bin}")
            click.echo(f"Version: {version}")
        else:
            click.secho(
                "Notice: Blender CLI is not installed or not in PATH. 3D features can still be dry-run validated.",
                fg="yellow",
            )

