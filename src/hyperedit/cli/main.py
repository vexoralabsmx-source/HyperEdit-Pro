"""Main CLI entrypoint for HyperEdit Pro."""

import sys
import click

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from hyperedit import __version__
from hyperedit.cli.commands.audio_cmd import audio_group
from hyperedit.cli.commands.captions_cmd import captions_group
from hyperedit.cli.commands.color_cmd import color_group
from hyperedit.cli.commands.doctor_cmd import doctor_command
from hyperedit.cli.commands.media_cmd import media_group
from hyperedit.cli.commands.motion_cmd import motion_group
from hyperedit.cli.commands.new_cmd import new_command
from hyperedit.cli.commands.probe_cmd import probe_command
from hyperedit.cli.commands.project_cmd import project_group
from hyperedit.cli.commands.render_cmd import render_command
from hyperedit.cli.commands.timeline_cmd import timeline_group
from hyperedit.cli.commands.validate_cmd import validate_command
from hyperedit.cli.commands.version_cmd import version_command
from hyperedit.cli.commands.vfx_cmd import vfx_group
from hyperedit.core.constants import HYPEREDIT_PROJECT_SCHEMA_VERSION


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    version=__version__,
    prog_name="hyperedit",
    message=f"%(prog_name)s %(version)s (Project Schema v{HYPEREDIT_PROJECT_SCHEMA_VERSION})",
)
def cli() -> None:
    """HyperEdit Pro: Professional audiovisual post-production and NLE engine for AI agents.

    Provides frame-accurate timeline editing, multi-track audio mixing, EBU R128
    loudness, subtitles, color grading, VFX, scene intelligence, and hardware-
    accelerated FFmpeg renders.
    """
    pass


# Register active command groups and top-level commands
cli.add_command(doctor_command)
cli.add_command(version_command)
cli.add_command(validate_command)
cli.add_command(new_command)
cli.add_command(probe_command)
cli.add_command(media_group)
cli.add_command(timeline_group)
cli.add_command(project_group)
cli.add_command(render_command)
cli.add_command(audio_group)
cli.add_command(captions_group)
cli.add_command(color_group)
cli.add_command(motion_group)
cli.add_command(vfx_group)


if __name__ == "__main__":
    cli()
