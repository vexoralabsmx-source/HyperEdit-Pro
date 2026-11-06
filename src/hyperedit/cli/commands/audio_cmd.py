"""CLI commands for audio engineering, beat tracking, mixing, ducking, and loudness."""

import json
from pathlib import Path
from typing import Optional
import click

from hyperedit.audio.beat_sync import BeatSynchronizer
from hyperedit.audio.beat_tracker import BeatTracker
from hyperedit.audio.mixer import AudioMixer
from hyperedit.audio.models import STANDARD_LOUDNESS_PROFILES
from hyperedit.core.models.project import Project


@click.group(name="audio")
def audio_group() -> None:
    """Intelligent audio engineering, beat tracking, mixing, ducking, and loudness normalization."""
    pass


@audio_group.command(name="beats")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--bpm-hint", type=float, default=None, help="Approximate expected BPM to assist autocorrelation")
@click.option("--override", type=float, default=None, help="Manual BPM override")
@click.option("--json", "as_json", is_flag=True, help="Output structured JSON telemetry")
def beats_command(file: Path, bpm_hint: Optional[float], override: Optional[float], as_json: bool) -> None:
    """Analyze real acoustic signal to detect BPM, beat grid timestamps, and transient onsets."""
    tracker = BeatTracker()
    try:
        beat_info = tracker.analyze_beats(file, bpm_hint=bpm_hint, manual_override=override)
    except Exception as e:
        click.secho(f"Error analyzing audio beats: {e}", fg="red", err=True)
        raise click.Abort()

    if as_json:
        click.echo(beat_info.model_dump_json(indent=2))
        return

    click.secho("\n--- HyperEdit Pro: Beat & Tempo Analysis ---", fg="cyan", bold=True)
    click.echo(f"  Target File:     {file.name}")
    click.echo(f"  Detected BPM:    {beat_info.bpm:.2f} BPM")
    click.echo(f"  Confidence:      {beat_info.confidence * 100:.1f}%")
    click.echo(f"  Beat Interval:   {beat_info.beat_interval_sec * 1000:.1f} ms")
    click.echo(f"  Total Beats:     {len(beat_info.beat_timestamps)}")
    click.echo(f"  Detected Onsets: {len(beat_info.onset_timestamps)}")
    if beat_info.beat_timestamps:
        sample_beats = beat_info.beat_timestamps[:8]
        click.echo(f"  First Beats (s): {', '.join(f'{t:.3f}' for t in sample_beats)} ...")
    click.echo()


@audio_group.command(name="markers")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("audio_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--color", default="#FF00AA", help="Hex color for timeline beat markers")
@click.option("--clear/--no-clear", default=True, help="Clear existing beat markers first")
@click.option("--bpm-hint", type=float, default=None, help="Approximate expected BPM")
@click.option("--json", "as_json", is_flag=True, help="Output structured JSON")
def markers_command(
    project_file: Path,
    audio_file: Path,
    color: str,
    clear: bool,
    bpm_hint: Optional[float],
    as_json: bool,
) -> None:
    """Analyze audio beats and inject temporal markers into the project timeline."""
    try:
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        project = Project.model_validate(data)
    except Exception as e:
        click.secho(f"Error loading project file: {e}", fg="red", err=True)
        raise click.Abort()

    tracker = BeatTracker()
    beat_info = tracker.analyze_beats(audio_file, bpm_hint=bpm_hint)

    synchronizer = BeatSynchronizer(default_fps=project.fps)
    added = synchronizer.add_beat_markers(
        project.timeline,
        beat_info,
        fps=project.fps,
        marker_color=color,
        clear_existing_beat_markers=clear,
    )

    with open(project_file, "w", encoding="utf-8") as f:
        f.write(project.model_dump_json(indent=2))

    if as_json:
        click.echo(
            json.dumps(
                {
                    "project": str(project_file),
                    "audio_file": str(audio_file),
                    "bpm": beat_info.bpm,
                    "markers_added": added,
                    "total_markers": len(project.timeline.markers),
                },
                indent=2,
            )
        )
        return

    click.secho(
        f"Injected {added} beat markers ({beat_info.bpm:.1f} BPM) into '{project_file.name}'.",
        fg="green",
    )


@audio_group.command(name="snap")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("audio_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--track", "track_id", default="V1", help="Track ID whose cuts will be snapped (default: V1)")
@click.option("--max-shift", default=8, type=int, help="Maximum allowed frame shift (+/-)")
@click.option("--mode", type=click.Choice(["ripple", "roll"]), default="ripple", help="Snap mode")
@click.option("--bpm-hint", type=float, default=None, help="Approximate expected BPM")
@click.option("--json", "as_json", is_flag=True, help="Output structured report JSON")
def snap_command(
    project_file: Path,
    audio_file: Path,
    track_id: str,
    max_shift: int,
    mode: str,
    bpm_hint: Optional[float],
    as_json: bool,
) -> None:
    """Snap timeline video cuts to musical beats within a frame tolerance."""
    try:
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        project = Project.model_validate(data)
    except Exception as e:
        click.secho(f"Error loading project file: {e}", fg="red", err=True)
        raise click.Abort()

    tracker = BeatTracker()
    beat_info = tracker.analyze_beats(audio_file, bpm_hint=bpm_hint)

    synchronizer = BeatSynchronizer(default_fps=project.fps)
    report = synchronizer.snap_cuts_to_beats(
        timeline=project.timeline,
        track_id=track_id,
        beats=beat_info,
        max_shift_frames=max_shift,
        mode=mode,
        fps=project.fps,
    )

    with open(project_file, "w", encoding="utf-8") as f:
        f.write(project.model_dump_json(indent=2))

    if as_json:
        click.echo(report.model_dump_json(indent=2))
        return

    click.secho("\n--- HyperEdit Pro: Beat Snap Report ---", fg="cyan", bold=True)
    click.echo(f"  Track ID:              {report.track_id}")
    click.echo(f"  Cuts Evaluated:        {report.total_cuts_evaluated}")
    click.echo(f"  Cuts Snapped:          {report.cuts_snapped}")
    click.echo(f"  Max Shift Allowed:     ±{report.max_shift_allowed_frames} frames")
    click.echo(f"  Mean Shift:            {report.mean_shift_ms:.1f} ms")
    click.echo(f"  Max Shift:             {report.max_shift_ms:.1f} ms")
    if report.details:
        click.echo("\n  Details:")
        for d in report.details:
            click.echo(
                f"    Clip {d.clip_id}: frame {d.original_frame} -> {d.snapped_frame} "
                f"({d.shift_frames:+d} frames / {d.shift_ms:+.1f} ms)"
            )
    click.echo()


@audio_group.command(name="loudness")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--profile",
    type=click.Choice(list(STANDARD_LOUDNESS_PROFILES.keys()), case_sensitive=False),
    default="youtube",
    help="Platform standard profile",
)
@click.option("--json", "as_json", is_flag=True, help="Output structured JSON")
def loudness_command(file: Path, profile: str, as_json: bool) -> None:
    """Measure integrated loudness (LUFS), True Peak (dBFS), and LRA via FFmpeg EBU R128."""
    mixer = AudioMixer()
    try:
        measurement = mixer.measure_loudness(file, target_profile=profile)
    except Exception as e:
        click.secho(f"Error measuring loudness: {e}", fg="red", err=True)
        raise click.Abort()

    if as_json:
        click.echo(measurement.model_dump_json(indent=2))
        return

    status_color = "green" if measurement.is_compliant else "yellow"
    status_text = "COMPLIANT" if measurement.is_compliant else "NON-COMPLIANT"

    click.secho("\n--- HyperEdit Pro: Loudness Telemetry (EBU R128) ---", fg="cyan", bold=True)
    click.echo(f"  File:               {file.name}")
    click.echo(f"  Profile Target:     {profile} ({measurement.target_lufs:.1f} LUFS)")
    click.echo(f"  Integrated Loudness:{measurement.integrated_lufs:.2f} LUFS")
    click.echo(f"  True Peak:          {measurement.true_peak_dbfs:.2f} dBFS")
    click.echo(f"  Loudness Range:     {measurement.lra:.2f} LU")
    click.echo(f"  Target Deviation:   {measurement.deviation_lu:+.2f} LU")
    click.secho(f"  Status:             {status_text}", fg=status_color, bold=True)
    click.echo()


@audio_group.command(name="normalize")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_file", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--profile",
    type=click.Choice(list(STANDARD_LOUDNESS_PROFILES.keys()), case_sensitive=False),
    default="youtube",
    help="Platform standard profile (default: youtube -14 LUFS)",
)
@click.option("--sample-rate", default=48000, type=int, help="Sample rate in Hz (default: 48000)")
def normalize_command(input_file: Path, output_file: Path, profile: str, sample_rate: int) -> None:
    """Normalize audio loudness according to broadcast or streaming platform standards (loudnorm)."""
    mixer = AudioMixer()
    try:
        out = mixer.normalize_loudness(input_file, output_file, profile=profile, sample_rate=sample_rate)
        # Measure resulting normalized file
        meas = mixer.measure_loudness(out, target_profile=profile)
        click.secho(
            f"Normalized '{input_file.name}' -> '{out.name}' "
            f"({meas.integrated_lufs:.2f} LUFS, True Peak: {meas.true_peak_dbfs:.2f} dBFS).",
            fg="green",
        )
    except Exception as e:
        click.secho(f"Loudness normalization error: {e}", fg="red", err=True)
        raise click.Abort()


@audio_group.command(name="duck")
@click.argument("music_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("dialogue_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_file", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--threshold", default=-20.0, type=float, help="Trigger threshold in dBFS (default: -20 dBFS)")
@click.option("--ratio", default=4.0, type=float, help="Compression ratio (default: 4.0)")
@click.option("--attack", default=20.0, type=float, help="Attack time in ms (default: 20 ms)")
@click.option("--release", default=250.0, type=float, help="Release time in ms (default: 250 ms)")
@click.option("--mix/--music-only", default=True, help="Mix dialogue into output or output ducked music only")
@click.option("--sample-rate", default=48000, type=int, help="Master sample rate in Hz (default: 48000)")
def duck_command(
    music_file: Path,
    dialogue_file: Path,
    output_file: Path,
    threshold: float,
    ratio: float,
    attack: float,
    release: float,
    mix: bool,
    sample_rate: int,
) -> None:
    """Apply real sidechain ducking to compress music bed whenever speech is active."""
    mixer = AudioMixer()
    try:
        out = mixer.apply_sidechain_ducking(
            music_file=music_file,
            dialogue_file=dialogue_file,
            output_file=output_file,
            threshold_db=threshold,
            ratio=ratio,
            attack_ms=attack,
            release_ms=release,
            mix_with_dialogue=mix,
            sample_rate=sample_rate,
        )
        click.secho(f"Sidechain ducked audio written to: {out}", fg="green")
    except Exception as e:
        click.secho(f"Sidechain ducking error: {e}", fg="red", err=True)
        raise click.Abort()


@audio_group.command(name="mix")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", "output_file", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--profile",
    type=click.Choice(list(STANDARD_LOUDNESS_PROFILES.keys()), case_sensitive=False),
    default=None,
    help="Target platform loudness normalization on master bus",
)
@click.option("--sample-rate", default=48000, type=int, help="Master audio sample rate in Hz (default: 48000)")
def mix_command(
    project_file: Path,
    output_file: Path,
    profile: Optional[str],
    sample_rate: int,
) -> None:
    """Mix all project audio tracks into a master stem with optional loudness compliance."""
    try:
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        project = Project.model_validate(data)
    except Exception as e:
        click.secho(f"Error loading project file: {e}", fg="red", err=True)
        raise click.Abort()

    mixer = AudioMixer()
    try:
        out = mixer.mix_timeline_audio(
            project=project,
            output_file=output_file,
            target_profile=profile,
            sample_rate=sample_rate,
        )
        click.secho(f"Master audio stem successfully mixed to: {out}", fg="green")
    except Exception as e:
        click.secho(f"Audio mix error: {e}", fg="red", err=True)
        raise click.Abort()

