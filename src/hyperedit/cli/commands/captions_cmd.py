"""CLI commands for captions, subtitles, speech transcription, and kinetic typography."""

import json
from pathlib import Path
from typing import Optional
import click

from hyperedit.adapters.hyperframes_captions import HyperFramesCaptionsAdapter
from hyperedit.captions.engine import CaptionsEngine
from hyperedit.captions.models import (
    KineticAnimationMode,
    STANDARD_CAPTION_PRESETS,
)
from hyperedit.captions.transcriber import SpeechTranscriber


@click.group(name="captions")
def captions_group() -> None:
    """Captions, subtitles, speech-to-text transcription, and kinetic typography."""
    pass


@captions_group.command(name="import")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--preset",
    type=click.Choice(list(STANDARD_CAPTION_PRESETS.keys()), case_sensitive=False),
    default=None,
    help="Apply typographic style preset",
)
@click.option("--json", "as_json", is_flag=True, help="Output parsed subtitle track as JSON")
def import_command(file: Path, preset: Optional[str], as_json: bool) -> None:
    """Import and inspect subtitle files (.srt, .vtt, .ass)."""
    engine = CaptionsEngine()
    try:
        track = engine.import_subtitles(file)
        if preset:
            track.default_style = STANDARD_CAPTION_PRESETS[preset]
    except Exception as e:
        click.secho(f"Error importing subtitles: {e}", fg="red", err=True)
        raise click.Abort()

    if as_json:
        click.echo(track.model_dump_json(indent=2))
        return

    click.secho("\n--- HyperEdit Pro: Subtitle Track Inspection ---", fg="cyan", bold=True)
    click.echo(f"  Source File:     {file.name}")
    click.echo(f"  Total Cues:      {len(track.cues)}")
    click.echo(f"  Language:        {track.language}")
    click.echo(f"  Font Family:     {track.default_style.font_name}")
    click.echo(f"  Font Size:       {track.default_style.font_size} pt")
    click.echo(f"  Animation Mode:  {track.default_style.animation_mode.value}")
    if track.cues:
        duration_sec = track.cues[-1].end_ms / 1000.0
        click.echo(f"  Timeline Span:   0.0s -> {duration_sec:.2f}s")
        sample_cues = track.cues[:3]
        click.echo("\n  First Cues:")
        for c in sample_cues:
            click.echo(f"    [{c.start_ms}ms -> {c.end_ms}ms]: {c.text}")
    click.echo()


@captions_group.command(name="export")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_path", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["srt", "vtt", "ass"], case_sensitive=False),
    default=None,
    help="Target subtitle format (default: inferred from output extension)",
)
@click.option(
    "--preset",
    type=click.Choice(list(STANDARD_CAPTION_PRESETS.keys()), case_sensitive=False),
    default=None,
    help="Typographic style preset for ASS export",
)
def export_command(file: Path, output_path: Path, fmt: Optional[str], preset: Optional[str]) -> None:
    """Convert and export subtitle tracks to SRT, WebVTT, or ASS."""
    engine = CaptionsEngine()
    try:
        track = engine.import_subtitles(file)
        if preset:
            track.default_style = STANDARD_CAPTION_PRESETS[preset]

        target_fmt = fmt.lower() if fmt else output_path.suffix.lstrip(".").lower()
        if target_fmt == "srt":
            out = engine.export_srt(track, output_path)
        elif target_fmt == "vtt":
            out = engine.export_vtt(track, output_path)
        elif target_fmt == "ass":
            out = engine.export_ass(track, output_path)
        else:
            click.secho(f"Unsupported format '{target_fmt}'. Choose 'srt', 'vtt', or 'ass'.", fg="red", err=True)
            raise click.Abort()

        click.secho(f"Successfully exported {len(track.cues)} cues to: {out}", fg="green")
    except Exception as e:
        click.secho(f"Error exporting subtitles: {e}", fg="red", err=True)
        raise click.Abort()


@captions_group.command(name="burn")
@click.argument("video_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("subtitles_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_file", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--preset",
    type=click.Choice(list(STANDARD_CAPTION_PRESETS.keys()), case_sensitive=False),
    default="modern_bold",
    help="Typographic style preset (default: modern_bold)",
)
def burn_command(video_file: Path, subtitles_file: Path, output_file: Path, preset: str) -> None:
    """Burn styled typography and subtitles into a video file via FFmpeg and libass."""
    engine = CaptionsEngine()
    try:
        out = engine.burn_subtitles(
            video_input=video_file,
            subtitle_input=subtitles_file,
            output_path=output_file,
            preset_name=preset,
        )
        click.secho(f"Subtitles burned successfully: {out}", fg="green")
    except Exception as e:
        click.secho(f"Subtitle burn error: {e}", fg="red", err=True)
        raise click.Abort()


@captions_group.command(name="transcribe")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_file", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--model", default="base", help="Whisper model size (tiny, base, small, medium, large-v3)")
@click.option("--language", default=None, help="Explicit language code (e.g. en, es, fr)")
@click.option(
    "--preset",
    type=click.Choice(list(STANDARD_CAPTION_PRESETS.keys()), case_sensitive=False),
    default="modern_bold",
    help="Style preset if saving to ASS",
)
def transcribe_command(
    file: Path,
    output_file: Path,
    model: str,
    language: Optional[str],
    preset: str,
) -> None:
    """Transcribe speech in an audiovisual file using local faster-whisper with word timestamps."""
    transcriber = SpeechTranscriber(model_size=model)
    try:
        track = transcriber.transcribe(file, language=language, word_timestamps=True)
        track.default_style = STANDARD_CAPTION_PRESETS[preset]

        engine = CaptionsEngine()
        ext = output_file.suffix.lower()
        if ext == ".srt":
            out = engine.export_srt(track, output_file)
        elif ext == ".vtt":
            out = engine.export_vtt(track, output_file)
        else:
            out = engine.export_ass(track, output_file)

        click.secho(
            f"Transcribed {len(track.cues)} cues ({track.language}) -> {out}",
            fg="green",
        )
    except Exception as e:
        click.secho(f"Speech transcription error: {e}", fg="red", err=True)
        raise click.Abort()


@captions_group.command(name="kinetic")
@click.argument("subtitles_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_file", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--mode",
    type=click.Choice(["karaoke_highlight", "pop_scale", "word_reveal", "fade_word", "slide_up"]),
    default="karaoke_highlight",
    help="Kinetic animation mode",
)
@click.option(
    "--preset",
    type=click.Choice(list(STANDARD_CAPTION_PRESETS.keys()), case_sensitive=False),
    default="tiktok_reels_neon",
    help="Visual styling preset",
)
def kinetic_command(subtitles_file: Path, output_file: Path, mode: str, preset: str) -> None:
    """Generate kinetic typography ASS script with word-by-word highlights and animations."""
    engine = CaptionsEngine()
    try:
        track = engine.import_subtitles(subtitles_file)
        style = STANDARD_CAPTION_PRESETS[preset].model_copy()
        style.animation_mode = KineticAnimationMode(mode)
        track.default_style = style

        out = engine.export_ass(track, output_file)
        click.secho(f"Kinetic typography ({mode}) compiled to: {out}", fg="green")
    except Exception as e:
        click.secho(f"Kinetic compilation error: {e}", fg="red", err=True)
        raise click.Abort()


@captions_group.command(name="hyperframes")
@click.argument("subtitles_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_html", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--preset",
    type=click.Choice(list(STANDARD_CAPTION_PRESETS.keys()), case_sensitive=False),
    default="modern_bold",
    help="Visual styling preset",
)
def hyperframes_command(subtitles_file: Path, output_html: Path, preset: str) -> None:
    """Export kinetic typography as a HyperFrames HTML/CSS/GSAP motion graphic composition."""
    engine = CaptionsEngine()
    try:
        track = engine.import_subtitles(subtitles_file)
        track.default_style = STANDARD_CAPTION_PRESETS[preset]

        adapter = HyperFramesCaptionsAdapter()
        out = adapter.export_html_composition(track, output_html)
        click.secho(f"HyperFrames composition exported to: {out}", fg="green")
    except Exception as e:
        click.secho(f"HyperFrames adapter error: {e}", fg="red", err=True)
        raise click.Abort()


@captions_group.command(name="validate")
@click.argument("subtitles_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output issues as JSON")
def validate_command(subtitles_file: Path, as_json: bool) -> None:
    """Perform readability and pacing QA (CPS, line length, overlaps)."""
    engine = CaptionsEngine()
    try:
        track = engine.import_subtitles(subtitles_file)
        issues = engine.validate_readability(track)
    except Exception as e:
        click.secho(f"Validation error: {e}", fg="red", err=True)
        raise click.Abort()

    if as_json:
        click.echo(json.dumps([i.model_dump() for i in issues], indent=2))
        return

    click.secho("\n--- HyperEdit Pro: Subtitle Readability & QA Audit ---", fg="cyan", bold=True)
    click.echo(f"  File:            {subtitles_file.name}")
    click.echo(f"  Total Cues:      {len(track.cues)}")
    click.echo(f"  Issues Found:    {len(issues)}")

    if not issues:
        click.secho("  Status:          100% COMPLIANT (Optimal reading pace and line length)", fg="green", bold=True)
    else:
        click.echo("\n  Telemetry Issues:")
        for iss in issues:
            color = "red" if iss.severity == "error" else "yellow"
            click.secho(f"    [{iss.severity.upper()}] Cue {iss.cue_id} ({iss.issue_type}): {iss.message}", fg=color)

    click.echo()

