"""CLI command: hyperedit version."""

import json
import click
from hyperedit import __version__
from hyperedit.core.constants import HYPEREDIT_PROJECT_SCHEMA_VERSION


@click.command("version")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output version info as JSON.")
def version_command(output_json: bool) -> None:
    """Display HyperEdit Pro and project schema version."""
    info = {
        "hyperedit": __version__,
        "schema_version": HYPEREDIT_PROJECT_SCHEMA_VERSION,
    }
    if output_json:
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo(f"HyperEdit Pro v{__version__} (Schema v{HYPEREDIT_PROJECT_SCHEMA_VERSION})")

