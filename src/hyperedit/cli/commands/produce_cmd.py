"""CLI command for Fast Production Mode: hyperedit produce."""

import json
import click

from hyperedit.core.exceptions import HyperEditError
from hyperedit.production.engine import FastProductionEngine
from hyperedit.production.models import ProductionMode, ProductionPlan


@click.command(name="produce")
@click.argument("plan_file", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", "output_path", type=click.Path(dir_okay=False), help="Override destination path for master render.")
@click.option(
    "--mode",
    type=click.Choice(["fast", "balanced", "cinematic"], case_sensitive=False),
    default=None,
    help="Execution mode (fast: minimal checks, balanced: standard QA, cinematic: deep review).",
)
@click.option("--preview/--no-preview", default=True, help="Generate technical preflight preview before master render.")
@click.option("--resume/--no-resume", default=True, help="Resume from previous checkpoint if available.")
@click.option("--json", "json_output", is_flag=True, help="Output machine-readable JSON telemetry.")
def produce_command(
    plan_file: str,
    output_path: str | None,
    mode: str | None,
    preview: bool,
    resume: bool,
    json_output: bool,
) -> None:
    """Execute end-to-end automated video production from a single declarative plan."""
    try:
        plan = ProductionPlan.load_from_file(plan_file)

        if output_path:
            plan.output_path = output_path
        if mode:
            plan.mode = ProductionMode(mode.lower())

        engine = FastProductionEngine()
        result = engine.run(plan, resume=resume)

        if json_output:
            click.echo(result.model_dump_json(indent=2))
        else:
            click.echo(result.compact_summary)

    except HyperEditError as e:
        if json_output:
            click.echo(json.dumps(e.to_dict(), indent=2))
        else:
            click.echo(f"Error: {e.message}", err=True)
            if e.details:
                click.echo(f"Details: {e.details}", err=True)
        raise click.exceptions.Exit(1)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": "UnexpectedError", "message": str(e)}, indent=2))
        else:
            click.echo(f"Unexpected error during production: {e}", err=True)
        raise click.exceptions.Exit(1)

