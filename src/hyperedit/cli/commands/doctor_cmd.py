"""CLI command: hyperedit doctor."""

import sys
import click

from hyperedit.diagnostics.checker import DiagnosticStatus, EnvironmentChecker
from hyperedit.diagnostics.formatter import DiagnosticFormatter


@click.command("doctor")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output full diagnostic report in machine-readable JSON format.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Display detailed diagnostic properties and configuration details.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit with non-zero status code if warnings are detected.",
)
def doctor_command(output_json: bool, verbose: bool, strict: bool) -> None:
    """Check system environment, FFmpeg/FFprobe binaries, hardware acceleration, and dependencies."""
    checker = EnvironmentChecker()
    report = checker.run_all_checks()

    if output_json:
        click.echo(DiagnosticFormatter.to_json(report))
    else:
        click.echo(DiagnosticFormatter.to_terminal(report, verbose=verbose))

    if report.overall_status == DiagnosticStatus.ERROR:
        sys.exit(1)
    if strict and report.overall_status == DiagnosticStatus.WARNING:
        sys.exit(2)

