"""CLI command: hyperedit validate."""

import json
from pathlib import Path
import sys
import click

from hyperedit.core.exceptions import HyperEditError
from hyperedit.core.models.project import Project


@click.command("validate")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "output_json", is_flag=True, default=False, help="Output validation result as JSON.")
def validate_command(project_file: Path, output_json: bool) -> None:
    """Validate a HyperEdit project JSON file against the official schema and integrity rules."""
    try:
        project = Project.load_from_file(project_file)
        result = {
            "valid": True,
            "project_file": str(project_file),
            "title": project.metadata.title,
            "schema_version": project.schema_version,
            "duration_frames": project.duration_frames,
            "duration_seconds": project.duration_seconds,
            "tracks_count": len(project.timeline.tracks),
            "assets_count": len(project.media_pool.assets),
            "message": "Project is valid and structurally consistent."
        }
        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.secho("✓ Project is valid and passed all integrity checks.", fg="green", bold=True)
            click.echo(f"  Title: {project.metadata.title}")
            click.echo(f"  Tracks: {len(project.timeline.tracks)} | Assets: {len(project.media_pool.assets)}")
            click.echo(f"  Duration: {project.duration_frames} frames ({project.duration_seconds:.2f}s)")
    except HyperEditError as e:
        result = {
            "valid": False,
            "project_file": str(project_file),
            "error_type": e.__class__.__name__,
            "message": str(e),
        }
        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.secho(f"✗ Validation Failed: {e}", fg="red", err=True, bold=True)
        sys.exit(1)
    except Exception as e:
        if output_json:
            click.echo(json.dumps({"valid": False, "error_type": "UnexpectedError", "message": str(e)}, indent=2))
        else:
            click.secho(f"✗ Unexpected Error: {e}", fg="red", err=True)
        sys.exit(1)

