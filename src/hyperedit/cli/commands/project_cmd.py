"""CLI commands under 'hyperedit project' namespace."""

from pathlib import Path
import sys
import click

from hyperedit.cli.commands.new_cmd import new_command
from hyperedit.cli.commands.validate_cmd import validate_command


@click.group("project")
def project_group() -> None:
    """Project management commands: create, validate, and inspect project packages."""
    pass


# Map 'hyperedit project create' to new_command
project_group.add_command(new_command, name="create")
project_group.add_command(validate_command, name="validate")

