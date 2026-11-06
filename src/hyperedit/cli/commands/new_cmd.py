"""CLI command: hyperedit new."""

from pathlib import Path
import sys
import click

from hyperedit.core.constants import STANDARD_RESOLUTIONS
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Timeline, Track, TrackKind


@click.command("new")
@click.argument("output_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--title", default="New HyperEdit Project", help="Title of the project.")
@click.option(
    "--preset",
    type=click.Choice(["1080p", "vertical_1080p", "4k", "square"], case_sensitive=False),
    default="1080p",
    help="Canvas preset aspect ratio and resolution.",
)
@click.option("--fps", type=float, default=30.0, help="Timeline base frame rate (e.g. 24, 25, 30, 60).")
@click.option("--force", is_flag=True, default=False, help="Overwrite target file if it already exists.")
def new_command(output_path: Path, title: str, preset: str, fps: float, force: bool) -> None:
    """Create a new valid HyperEdit project file with boilerplate tracks."""
    if output_path.exists() and not force:
        click.secho(f"Error: Target file '{output_path}' already exists. Use --force to overwrite.", fg="red", err=True)
        sys.exit(1)

    resolution_map = {
        "1080p": STANDARD_RESOLUTIONS["1080p_horizontal"],
        "vertical_1080p": STANDARD_RESOLUTIONS["1080p_vertical"],
        "4k": STANDARD_RESOLUTIONS["4k_horizontal"],
        "square": STANDARD_RESOLUTIONS["square_1080"],
    }
    width, height = resolution_map[preset]

    settings = ProjectSettings(
        width=width,
        height=height,
        fps=fps,
        sample_rate=48000,
        audio_channels=2,
    )
    metadata = ProjectMetadata(
        title=title,
        description=f"Scaffolded with preset {preset} ({width}x{height} @ {fps}fps)",
    )
    timeline = Timeline(
        tracks=[
            Track(track_id="V1", name="Main Video", kind=TrackKind.VIDEO, index=0),
            Track(track_id="A1", name="Dialogue / Voice", kind=TrackKind.AUDIO, index=1),
            Track(track_id="A2", name="Music / BGM", kind=TrackKind.AUDIO, index=2),
            Track(track_id="A3", name="Sound Effects / SFX", kind=TrackKind.AUDIO, index=3),
        ]
    )

    project = Project(
        metadata=metadata,
        settings=settings,
        timeline=timeline,
    )
    project.save_to_file(output_path)
    click.secho(f"✓ Project initialized: {output_path}", fg="green", bold=True)
    click.echo(f"  Canvas: {width}x{height} @ {fps} fps")
    click.echo("  Default tracks: V1 (Video), A1 (Voice), A2 (Music), A3 (SFX)")

