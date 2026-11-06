"""CLI commands for motion graphics, HyperFrames integration, and keyframe animation."""

import json
from pathlib import Path
from typing import Optional
import click

from hyperedit.adapters.hyperframes import HyperFramesAdapter
from hyperedit.audio.beat_tracker import BeatTracker
from hyperedit.core.models.project import Project
from hyperedit.motion.presets import STANDARD_MOTION_PRESETS


@click.group(name="motion")
def motion_group() -> None:
    """Motion graphics, HyperFrames integration, and keyframe animations."""
    pass


@motion_group.command(name="presets")
@click.option("--json", "as_json", is_flag=True, help="Output presets as JSON")
def presets_command(as_json: bool) -> None:
    """List curated professional motion graphics presets and art direction rules."""
    if as_json:
        data = {k: v.model_dump() for k, v in STANDARD_MOTION_PRESETS.items()}
        click.echo(json.dumps(data, indent=2))
        return

    click.secho("\n--- HyperEdit Pro: Motion Graphics & Art Direction Presets ---", fg="cyan", bold=True)
    for key, p in STANDARD_MOTION_PRESETS.items():
        click.secho(f"\n[{key.upper()}] — {p.display_name}", fg="yellow", bold=True)
        click.echo(f"  Description:    {p.description}")
        click.echo(f"  Target FPS:     {p.recommended_fps:.0f} fps")
        click.echo(f"  Typography:     {p.typography.get('title_font')}")
        click.echo(f"  Motion Easing:  {p.motion.get('ease_curve')}")
        click.echo("  Principles:")
        for princ in p.design_principles:
            click.echo(f"    • {princ}")
    click.echo()


@motion_group.command(name="create")
@click.argument("template_type", type=click.Choice(["cinematic_intro", "product_showcase", "audio_reactive"]))
@click.option("-o", "--output", "output_html", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--title", default="HYPEREDIT PRO", help="Primary title / product name")
@click.option("--subtitle", default="AUTONOMOUS POST-PRODUCTION", help="Subtitle or kicker")
@click.option(
    "--preset",
    type=click.Choice(list(STANDARD_MOTION_PRESETS.keys()), case_sensitive=False),
    default="cinematic_luxury",
    help="Motion art direction preset",
)
@click.option("--duration", default=4.0, type=float, help="Composition duration in seconds")
@click.option("--width", default=1920, type=int, help="Canvas width in pixels")
@click.option("--height", default=1080, type=int, help="Canvas height in pixels")
def create_command(
    template_type: str,
    output_html: Path,
    title: str,
    subtitle: str,
    preset: str,
    duration: float,
    width: int,
    height: int,
) -> None:
    """Create a validated HyperFrames HTML/CSS/GSAP motion graphic composition."""
    adapter = HyperFramesAdapter()
    params = {
        "title": title,
        "name": title,
        "subtitle": subtitle,
        "kicker": "HYPEREDIT PRO MOTION",
        "badge": "AI POST-PRODUCTION",
        "specs": ["Frame-Accurate Cuts", "Sidechain Ducking", "ProRes 4444 Alpha"],
        "price": "ACTIVE MASTER",
        "bpm": 120.0,
    }

    try:
        out = adapter.create_composition(
            composition_id=output_html.stem,
            template_type=template_type,
            params=params,
            output_file=output_html,
            preset_name=preset,
            width=width,
            height=height,
            duration_sec=duration,
        )
        click.secho(f"HyperFrames motion composition created: {out}", fg="green")
    except Exception as e:
        click.secho(f"Error creating motion composition: {e}", fg="red", err=True)
        raise click.Abort()


@motion_group.command(name="sync")
@click.argument("composition_html", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("audio_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_html", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--bpm-hint", type=float, default=None, help="Approximate expected tempo")
def sync_command(composition_html: Path, audio_file: Path, output_html: Optional[Path], bpm_hint: Optional[float]) -> None:
    """Analyze audio beats and inject beat-reactive pulsation keyframes into composition HTML."""
    tracker = BeatTracker()
    try:
        beat_info = tracker.analyze_beats(audio_file, bpm_hint=bpm_hint)
    except Exception as e:
        click.secho(f"Audio analysis error: {e}", fg="red", err=True)
        raise click.Abort()

    adapter = HyperFramesAdapter()
    try:
        out = adapter.sync_with_audio_beats(composition_html, beats=beat_info, output_file=output_html)
        click.secho(
            f"Injected {len(beat_info.beat_timestamps)} beat keyframes ({beat_info.bpm:.1f} BPM) into: {out.name}",
            fg="green",
        )
    except Exception as e:
        click.secho(f"Beat sync error: {e}", fg="red", err=True)
        raise click.Abort()


@motion_group.command(name="render")
@click.argument("composition_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_path", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--format", "fmt", type=click.Choice(["mov", "webm", "mp4"]), default="mov", help="Output format")
@click.option("--fps", default=30.0, type=float, help="Render frame rate")
def render_command(composition_file: Path, output_path: Path, fmt: str, fps: float) -> None:
    """Render a HyperFrames composition into a transparent video overlay."""
    adapter = HyperFramesAdapter()
    try:
        out = adapter.render_composition(
            composition_file=composition_file,
            output_path=output_path,
            format=fmt,
            fps=fps,
            transparent=True,
        )
        click.secho(f"Rendered transparent motion overlay: {out}", fg="green")
    except Exception as e:
        click.secho(f"Motion render error: {e}", fg="red", err=True)
        raise click.Abort()


@motion_group.command(name="overlay")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("overlay_video", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--track", "track_id", default="GRAPHIC", help="Target overlay track ID (default: GRAPHIC)")
@click.option("--start-frame", default=0, type=int, help="Timeline start frame index")
def overlay_command(project_file: Path, overlay_video: Path, track_id: str, start_frame: int) -> None:
    """Import and attach a motion overlay clip directly onto the project timeline."""
    try:
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        project = Project.model_validate(data)
    except Exception as e:
        click.secho(f"Error loading project file: {e}", fg="red", err=True)
        raise click.Abort()

    adapter = HyperFramesAdapter()
    try:
        clip = adapter.import_to_timeline(project, overlay_video, track_id=track_id, start_frame=start_frame)
        with open(project_file, "w", encoding="utf-8") as f:
            f.write(project.model_dump_json(indent=2))

        click.secho(
            f"Attached overlay '{overlay_video.name}' to track '{track_id}' at frame {start_frame} "
            f"({clip.timeline_duration_frames} frames).",
            fg="green",
        )
    except Exception as e:
        click.secho(f"Error attaching overlay: {e}", fg="red", err=True)
        raise click.Abort()

