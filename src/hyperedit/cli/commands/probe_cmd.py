"""CLI command: hyperedit probe."""

import json
from pathlib import Path
import sys
import click

from hyperedit.core.exceptions import HyperEditError
from hyperedit.media.prober import FFprobeProber


@click.command("probe")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "output_json", is_flag=True, default=False, help="Output metadata in JSON format.")
@click.option("--hash", "compute_hash", is_flag=True, default=False, help="Calculate SHA-256 asset checksum.")
def probe_command(media_file: Path, output_json: bool, compute_hash: bool) -> None:
    """Probe a media file using ffprobe and display stream parameters."""
    try:
        prober = FFprobeProber()
        asset = prober.probe_file(media_file, compute_hash=compute_hash)

        if output_json:
            click.echo(asset.model_dump_json(indent=2))
        else:
            click.secho(f"Asset: {asset.asset_id}", bold=True, fg="cyan")
            click.echo(f"  Path: {asset.file_path}")
            click.echo(f"  Format: {asset.format_name} | Size: {asset.size_bytes / (1024 * 1024):.2f} MB")
            click.echo(f"  Duration: {asset.duration_seconds:.2f} seconds")
            if asset.hash_sha256:
                click.echo(f"  SHA-256: {asset.hash_sha256}")

            if asset.video_streams:
                click.secho("  Video Streams:", bold=True)
                for v in asset.video_streams:
                    click.echo(f"    [{v.index}] {v.codec} | {v.width}x{v.height} @ {v.fps:.2f}fps ({v.pixel_format}, {v.bit_depth}bit)")

            if asset.audio_streams:
                click.secho("  Audio Streams:", bold=True)
                for a in asset.audio_streams:
                    click.echo(f"    [{a.index}] {a.codec} | {a.sample_rate}Hz | {a.channels}ch ({a.channel_layout})")

            if asset.subtitle_streams:
                click.secho("  Subtitle Streams:", bold=True)
                for s in asset.subtitle_streams:
                    click.echo(f"    [{s.index}] {s.codec} | lang: {s.language}")
    except HyperEditError as e:
        if output_json:
            click.echo(json.dumps({"error": str(e)}, indent=2))
        else:
            click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

