"""CLI commands for professional color correction, grading, histogram analysis, and shot matching."""

import json
from pathlib import Path
from typing import Optional
import click

from hyperedit.color.engine import ColorGradingEngine
from hyperedit.color.presets import COLOR_PRESETS
from hyperedit.core.models.color import ColorGradeConfig


@click.group(name="color")
def color_group() -> None:
    """Professional color correction, grading, histogram analysis, and shot matching."""
    pass


@color_group.command(name="presets")
@click.option("--json", "as_json", is_flag=True, help="Output presets as JSON")
def presets_command(as_json: bool) -> None:
    """List available curated cinematographic color grading presets."""
    payload = {name: cfg.model_dump() for name, cfg in COLOR_PRESETS.items()}
    if as_json:
        click.echo(json.dumps(payload, indent=2))
    else:
        click.secho("Available HyperEdit Pro Color Presets:", fg="cyan", bold=True)
        for name, cfg in COLOR_PRESETS.items():
            click.secho(f"\n  • {name}", fg="green", bold=True)
            click.echo(f"    Exposure: {cfg.exposure_ev:+.2f} EV | Contrast: {cfg.contrast:.2f}x | Saturation: {cfg.saturation:.2f}x")
            click.echo(f"    Temperature: {cfg.temperature:+.1f} | Tint: {cfg.tint:+.1f}")
            click.echo(f"    Black Point: {cfg.black_point:+.3f} | White Point: {cfg.white_point:.3f}")


@color_group.command(name="grade")
@click.argument("video_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_video", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--preset", default=None, type=click.Choice(list(COLOR_PRESETS.keys())), help="Preset look to apply")
@click.option("--strength", default=1.0, type=float, help="Preset blend strength (0.0 to 1.0)")
@click.option("--exposure", default=0.0, type=float, help="Exposure compensation in EV stops (-3.0 to +3.0)")
@click.option("--contrast", default=1.0, type=float, help="Contrast multiplier (e.g. 1.10)")
@click.option("--saturation", default=1.0, type=float, help="Saturation multiplier (e.g. 0.95)")
@click.option("--temp", default=0.0, type=float, help="Color temperature shift (-50 to +50)")
@click.option("--tint", default=0.0, type=float, help="Tint shift green to magenta (-50 to +50)")
@click.option("--lut", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Optional .cube 3D LUT")
def grade_command(
    video_file: Path,
    output_video: Path,
    preset: Optional[str],
    strength: float,
    exposure: float,
    contrast: float,
    saturation: float,
    temp: float,
    tint: float,
    lut: Optional[Path],
) -> None:
    """Apply non-destructive color grade to a video file."""
    config = ColorGradeConfig(
        preset_name=preset,
        preset_strength=strength,
        exposure_ev=exposure,
        contrast=contrast,
        saturation=saturation,
        temperature=temp,
        tint=tint,
        lut_path=str(lut) if lut else None,
    )
    engine = ColorGradingEngine()
    try:
        out = engine.apply_color_grade_to_video(video_file, output_video, config)
        click.secho(f"Rendered color graded video: {out}", fg="green")
    except Exception as e:
        click.secho(f"Color grading error: {e}", fg="red", err=True)
        raise click.Abort()


@color_group.command(name="analyze")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output metrics as JSON")
@click.option("--histogram-output", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Save histogram PNG")
def analyze_command(media_file: Path, as_json: bool, histogram_output: Optional[Path]) -> None:
    """Analyze luminance, RGB balance, dynamic range, and clipping metrics."""
    engine = ColorGradingEngine()
    try:
        metrics = engine.analyze_histogram(media_file)
        if histogram_output:
            engine.generate_histogram_image(media_file, histogram_output)
            click.secho(f"Histogram chart saved to: {histogram_output}", fg="cyan")

        if as_json:
            click.echo(metrics.model_dump_json(indent=2))
        else:
            click.secho(f"\nColor & Tonal Telemetry for: {media_file.name}", fg="cyan", bold=True)
            click.echo(f"  • Mean Luminance: {metrics.mean_luma:.1f} IRE (std: {metrics.std_luma:.1f})")
            click.echo(f"  • Luma Range: {metrics.min_luma:.1f} to {metrics.max_luma:.1f} (DR: ~{metrics.dynamic_range_stops:.1f} stops)")
            click.echo(f"  • Average RGB: R={metrics.mean_rgb[0]:.1f}, G={metrics.mean_rgb[1]:.1f}, B={metrics.mean_rgb[2]:.1f}")
            shadow_color = "red" if metrics.shadow_clipping_pct > 3.0 else "green"
            highlight_color = "red" if metrics.highlight_clipping_pct > 3.0 else "green"
            click.secho(f"  • Shadow Clipping: {metrics.shadow_clipping_pct:.2f}%", fg=shadow_color)
            click.secho(f"  • Highlight Clipping: {metrics.highlight_clipping_pct:.2f}%", fg=highlight_color)
    except Exception as e:
        click.secho(f"Analysis error: {e}", fg="red", err=True)
        raise click.Abort()


@color_group.command(name="match")
@click.argument("reference_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("target_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_video", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output shot matching telemetry JSON")
def match_command(reference_file: Path, target_file: Path, output_video: Path, as_json: bool) -> None:
    """Align target shot tonal consistency and color balance to a reference shot."""
    engine = ColorGradingEngine()
    try:
        telemetry = engine.match_shots(reference_file, target_file)
        out = engine.apply_color_grade_to_video(target_file, output_video, telemetry.applied_grade)

        if as_json:
            click.echo(telemetry.model_dump_json(indent=2))
        else:
            g = telemetry.applied_grade
            click.secho(f"Matched '{target_file.name}' to '{reference_file.name}'", fg="green", bold=True)
            click.echo(f"  • Corrective Exposure: {g.exposure_ev:+.2f} EV")
            click.echo(f"  • Corrective Contrast: {g.contrast:.2f}x")
            click.echo(f"  • Corrective Temp/Tint: Temp={g.temperature:+.1f}, Tint={g.tint:+.1f}")
            click.echo(f"  • Output Render: {out}")
    except Exception as e:
        click.secho(f"Shot matching error: {e}", fg="red", err=True)
        raise click.Abort()


@color_group.command(name="audit")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output audit report as JSON")
def audit_command(media_file: Path, as_json: bool) -> None:
    """Audit color space, primaries, transfer function, and SDR/HDR conformity."""
    engine = ColorGradingEngine()
    try:
        report = engine.audit_color_space(media_file)
        if as_json:
            click.echo(report.model_dump_json(indent=2))
        else:
            m = report.metadata
            click.secho(f"\nColor Space Audit: {Path(report.file_path).name}", fg="cyan", bold=True)
            click.echo(f"  • Standard: {m.standard.value.upper()}")
            click.echo(f"  • Color Space: {m.color_space} | Primaries: {m.color_primaries}")
            click.echo(f"  • Transfer Function: {m.color_transfer}")
            click.echo(f"  • Range: {m.color_range.value.upper()} | Bit Depth: {m.bit_depth}-bit")
            hdr_color = "yellow" if report.is_hdr else "green"
            click.secho(f"  • HDR Content: {report.is_hdr} (Rec.709 SDR Compliant: {report.is_sdr_rec709_compliant})", fg=hdr_color)

            if report.warnings:
                click.secho("\n  Warnings:", fg="yellow", bold=True)
                for w in report.warnings:
                    click.secho(f"    - {w}", fg="yellow")

            if report.recommendations:
                click.secho("\n  Recommendations:", fg="green")
                for r in report.recommendations:
                    click.echo(f"    - {r}")
    except Exception as e:
        click.secho(f"Audit error: {e}", fg="red", err=True)
        raise click.Abort()

