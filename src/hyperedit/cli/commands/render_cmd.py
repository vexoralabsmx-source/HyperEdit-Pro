"""CLI command for rendering timelines to playable video masters."""

from pathlib import Path
import sys
from typing import Optional
import click

from hyperedit.core.exceptions import HyperEditError
from hyperedit.core.models.export import ExportPreset, HardwareAccel
from hyperedit.core.models.project import Project
from hyperedit.rendering.engine import RenderEngine


@click.command("render")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), required=True, help="Destination MP4/MOV output path.")
@click.option("--preset", default="web_1080p", help="Export preset name (e.g. web_1080p, reels_vertical).")
@click.option("--hwaccel", type=click.Choice(["auto", "none", "nvenc"]), default="auto", help="Hardware acceleration mode.")
@click.option("--dry-run", is_flag=True, default=False, help="Compile filtergraph without executing render.")
def render_command(
    project_file: Path,
    output_path: Path,
    preset: str,
    hwaccel: str,
    dry_run: bool,
) -> None:
    """Render a HyperEdit project timeline to a playable audiovisual deliverable."""
    try:
        project = Project.load_from_file(project_file)
        engine = RenderEngine()

        # Resolve export preset
        export_preset = project.export_presets.get(preset)
        if not export_preset:
            # Fallback default preset matching canvas
            export_preset = ExportPreset(
                name=preset,
                width=project.settings.width,
                height=project.settings.height,
                fps=project.settings.fps,
                hwaccel=HardwareAccel(hwaccel),
            )

        if dry_run:
            fc = engine.compile_filtergraph(project, export_preset)
            click.secho("=== Filtergraph Complex (Dry Run) ===", bold=True, fg="cyan")
            click.echo(fc)
            return

        click.secho(f"Rendering '{project.metadata.title}' -> '{output_path.name}'...", bold=True, fg="cyan")
        click.echo(f"  Canvas: {export_preset.width or project.settings.width}x{export_preset.height or project.settings.height} @ {project.settings.fps} fps")
        click.echo(f"  Timeline Duration: {project.duration_seconds:.2f}s ({project.duration_frames} frames)")

        rendered_file = engine.render_project(project, export_preset, output_path)

        size_mb = rendered_file.stat().st_size / (1024 * 1024)
        click.secho(f"✓ Master deliverable created: {rendered_file}", fg="green", bold=True)
        click.echo(f"  File Size: {size_mb:.2f} MB")
    except HyperEditError as e:
        click.secho(f"Render Error: {e}", fg="red", err=True)
        sys.exit(1)

