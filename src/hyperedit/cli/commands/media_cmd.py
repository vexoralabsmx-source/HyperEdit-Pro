"""CLI commands for HyperEdit Pro Professional Media Engine."""

import json
from pathlib import Path
import sys
from typing import Optional
import click

from hyperedit.core.exceptions import HyperEditError
from hyperedit.core.models.project import Project
from hyperedit.media.artifacts import MediaArtifactGenerator
from hyperedit.media.importer import MediaImporter
from hyperedit.media.prober import FFprobeProber
from hyperedit.media.signal import AudioSignalAnalyzer


@click.group("media")
def media_group() -> None:
    """Professional Media Engine: probe, import, proxies, waveforms, and signal analysis."""
    pass


@media_group.command("probe")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "output_json", is_flag=True, default=False, help="Output metadata in JSON format.")
@click.option("--hash", "compute_hash", is_flag=True, default=True, help="Compute SHA-256 asset checksum.")
def probe_subcommand(media_file: Path, output_json: bool, compute_hash: bool) -> None:
    """Deeply inspect media file using FFprobe and return structured telemetry."""
    try:
        prober = FFprobeProber()
        asset = prober.probe_file(media_file, compute_hash=compute_hash)

        if output_json:
            click.echo(asset.model_dump_json(indent=2))
        else:
            click.secho(f"Asset ID: {asset.asset_id}", bold=True, fg="cyan")
            click.echo(f"  Path: {asset.file_path}")
            click.echo(f"  Type: {asset.media_type.value.upper()} | Container: {asset.format_name}")
            click.echo(f"  Size: {asset.size_bytes / (1024 * 1024):.2f} MB | Duration: {asset.duration_seconds:.2f}s")
            if asset.bitrate_kbps:
                click.echo(f"  Overall Bitrate: {asset.bitrate_kbps} kbps")
            if asset.hash_sha256:
                click.echo(f"  SHA-256: {asset.hash_sha256}")

            if asset.video_streams:
                click.secho("  Video Streams:", bold=True, fg="yellow")
                for v in asset.video_streams:
                    vfr_tag = " [VFR]" if v.frame_rate_info.is_vfr else " [CFR]"
                    orient = " (Vertical / Portrait)" if v.is_vertical else ""
                    click.echo(
                        f"    • Stream #{v.index}: {v.codec} | {v.width}x{v.height}{orient} "
                        f"@ {v.frame_rate_info.fps:.2f}fps{vfr_tag} ({v.pixel_format}, {v.bit_depth}-bit)"
                    )
                    if v.rotation_deg:
                        click.echo(f"      Rotation: {v.rotation_deg}°")

            if asset.audio_streams:
                click.secho("  Audio Streams:", bold=True, fg="green")
                for a in asset.audio_streams:
                    click.echo(
                        f"    • Stream #{a.index}: {a.codec} | {a.sample_rate} Hz | "
                        f"{a.channels} ch ({a.channel_layout}) | {a.bits_per_sample}-bit"
                    )
            elif asset.media_type == "video":
                click.secho("  Audio Streams: None (Silent video)", fg="bright_black")

    except HyperEditError as e:
        if output_json:
            click.echo(json.dumps({"error": str(e)}, indent=2))
        else:
            click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@media_group.command("validate")
@click.argument("media_file", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--json", "output_json", is_flag=True, default=False, help="Output validation as JSON.")
def validate_subcommand(media_file: Path, output_json: bool) -> None:
    """Audit media file for corruption, readability, and compatibility."""
    prober = FFprobeProber()
    report = prober.validate_media(media_file)

    if output_json:
        click.echo(report.model_dump_json(indent=2))
    else:
        if report.is_valid:
            click.secho(f"✓ '{media_file.name}' is valid and healthy.", fg="green", bold=True)
            click.echo(f"  Detected Type: {report.media_type.value.upper()}")
            if report.warnings:
                for w in report.warnings:
                    click.secho(f"  ▲ Warning: {w}", fg="yellow")
        else:
            click.secho(f"✗ '{media_file.name}' is INVALID or CORRUPTED.", fg="red", bold=True)
            click.echo(f"  Reason: {report.error_message}")
            sys.exit(1)


@media_group.command("import")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--proxy", is_flag=True, default=False, help="Generate lightweight editing proxy.")
@click.option("--waveform", is_flag=True, default=False, help="Render audio waveform image.")
@click.option("--thumbnail", is_flag=True, default=False, help="Extract video thumbnail.")
@click.option("--contact-sheet", is_flag=True, default=False, help="Create 3x3 contact sheet mosaic.")
@click.option("--extract-audio", is_flag=True, default=False, help="Extract pristine audio stem.")
@click.option("--signal-metrics", is_flag=True, default=False, help="Analyze peak/mean volume and silences.")
@click.option("--proxy-scale", type=click.Choice(["720p", "540p", "360p"]), default="720p")
@click.option("-o", "--output", "output_project", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--json", "output_json", is_flag=True, default=False, help="Output asset metadata as JSON.")
def import_subcommand(
    project_file: Path,
    media_file: Path,
    proxy: bool,
    waveform: bool,
    thumbnail: bool,
    contact_sheet: bool,
    extract_audio: bool,
    signal_metrics: bool,
    proxy_scale: str,
    output_project: Optional[Path],
    output_json: bool,
) -> None:
    """Import media file into a project, generate artifacts, and register in media pool."""
    try:
        project = Project.load_from_file(project_file)
        importer = MediaImporter()

        asset = importer.import_media(
            media_file=media_file,
            project=project,
            generate_thumbnail=thumbnail,
            generate_contact_sheet=contact_sheet,
            generate_waveform=waveform,
            generate_proxy=proxy,
            extract_audio=extract_audio,
            analyze_signals=signal_metrics,
            proxy_scale=proxy_scale,
        )

        save_target = output_project or project_file
        project.save_to_file(save_target)

        if output_json:
            click.echo(asset.model_dump_json(indent=2))
        else:
            click.secho(f"✓ Imported '{asset.asset_id}' into project '{save_target.name}'", fg="green", bold=True)
            click.echo(f"  Source: {asset.file_path}")
            click.echo(f"  Duration: {asset.duration_seconds:.2f}s | Type: {asset.media_type.value.upper()}")
            if asset.artifacts.thumbnail_path:
                click.echo(f"  Thumbnail: {asset.artifacts.thumbnail_path}")
            if asset.artifacts.contact_sheet_path:
                click.echo(f"  Contact Sheet: {asset.artifacts.contact_sheet_path}")
            if asset.artifacts.waveform_path:
                click.echo(f"  Waveform: {asset.artifacts.waveform_path}")
            if asset.artifacts.proxy_path:
                click.echo(f"  Proxy ({proxy_scale}): {asset.artifacts.proxy_path}")
            if asset.artifacts.extracted_audio_path:
                click.echo(f"  Audio Stem: {asset.artifacts.extracted_audio_path}")
    except HyperEditError as e:
        click.secho(f"Error during import: {e}", fg="red", err=True)
        sys.exit(1)


@media_group.command("thumbnail")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
@click.option("--time", "timestamp_sec", type=float, default=0.0, help="Timestamp in seconds.")
@click.option("--width", type=int, default=480, help="Thumbnail width in pixels.")
def thumbnail_subcommand(media_file: Path, output_path: Path, timestamp_sec: float, width: int) -> None:
    """Extract a single frame image from a video file."""
    generator = MediaArtifactGenerator()
    out = generator.extract_thumbnail(media_file, output_path, timestamp_sec=timestamp_sec, width=width)
    click.secho(f"✓ Thumbnail extracted: {out}", fg="green")


@media_group.command("contact-sheet")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
@click.option("--cols", type=int, default=3, help="Grid columns count.")
@click.option("--rows", type=int, default=3, help="Grid rows count.")
@click.option("--tile-width", type=int, default=320, help="Width of individual tiles in pixels.")
def contact_sheet_subcommand(media_file: Path, output_path: Path, cols: int, rows: int, tile_width: int) -> None:
    """Generate a storyboard mosaic contact sheet across the video duration."""
    prober = FFprobeProber()
    asset = prober.probe_file(media_file, compute_hash=False)

    generator = MediaArtifactGenerator()
    out = generator.generate_contact_sheet(
        media_file,
        output_path,
        duration_seconds=asset.duration_seconds,
        cols=cols,
        rows=rows,
        tile_width=tile_width,
    )
    click.secho(f"✓ Contact sheet ({cols}x{rows}) created: {out}", fg="green")


@media_group.command("waveform")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
@click.option("--width", type=int, default=1920, help="Waveform image width.")
@click.option("--height", type=int, default=240, help="Waveform image height.")
@click.option("--color", default="0x00FF88", help="Waveform color in hex e.g. 0x00FF88.")
def waveform_subcommand(media_file: Path, output_path: Path, width: int, height: int, color: str) -> None:
    """Generate an audio waveform visualization PNG."""
    generator = MediaArtifactGenerator()
    out = generator.generate_waveform(media_file, output_path, width=width, height=height, color=color)
    click.secho(f"✓ Waveform image generated: {out}", fg="green")


@media_group.command("proxy")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
@click.option("--scale", type=click.Choice(["720p", "540p", "360p"]), default="720p")
@click.option("--crf", type=int, default=24, help="Constant Rate Factor quality (default 24).")
def proxy_subcommand(media_file: Path, output_path: Path, scale: str, crf: int) -> None:
    """Transcode a fast, lightweight editing proxy."""
    generator = MediaArtifactGenerator()
    out = generator.create_proxy(media_file, output_path, scale=scale, crf=crf)
    click.secho(f"✓ Proxy ({scale}) created: {out}", fg="green")


@media_group.command("extract-audio")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), required=True)
@click.option("--format", "format_ext", type=click.Choice(["wav", "flac", "mp3"]), default="wav")
@click.option("--sample-rate", type=int, default=48000, help="Audio sample rate in Hz.")
@click.option("--channels", type=int, default=2, help="Number of audio channels (1=mono, 2=stereo).")
def extract_audio_subcommand(media_file: Path, output_path: Path, format_ext: str, sample_rate: int, channels: int) -> None:
    """Extract audio stem for mixing, transcription or DSP analysis."""
    generator = MediaArtifactGenerator()
    out = generator.extract_audio(
        media_file,
        output_path,
        format_ext=format_ext,
        sample_rate=sample_rate,
        channels=channels,
    )
    click.secho(f"✓ Audio extracted ({format_ext.upper()}, {sample_rate}Hz, {channels}ch): {out}", fg="green")


@media_group.command("signal-metrics")
@click.argument("media_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "output_json", is_flag=True, default=False, help="Output metrics as JSON.")
def signal_metrics_subcommand(media_file: Path, output_json: bool) -> None:
    """Analyze peak volume, RMS level, clipping, and silence intervals."""
    analyzer = AudioSignalAnalyzer()
    metrics = analyzer.analyze_signal(media_file)

    if output_json:
        click.echo(metrics.model_dump_json(indent=2))
    else:
        click.secho(f"Audio Signal Metrics for '{media_file.name}':", bold=True, fg="cyan")
        click.echo(f"  Peak Volume: {metrics.peak_db:.2f} dBFS")
        click.echo(f"  Mean Volume (RMS): {metrics.mean_volume_db:.2f} dBFS")
        click.echo(f"  Dynamic Range: {metrics.dynamic_range_db:.2f} dB")
        if metrics.has_clipping:
            click.secho("  ▲ Clipping Alert: Signal reaches or exceeds 0.0 dBFS!", fg="red", bold=True)
        else:
            click.secho("  ✓ Headroom OK: No digital clipping detected.", fg="green")

        if metrics.silence_intervals:
            click.secho(f"  Detected Silence Intervals ({len(metrics.silence_intervals)}):", bold=True)
            for s in metrics.silence_intervals:
                click.echo(f"    • {s.start_seconds:.2f}s -> {s.end_seconds:.2f}s ({s.duration_seconds:.2f}s)")
        else:
            click.echo("  Detected Silence Intervals: None")
