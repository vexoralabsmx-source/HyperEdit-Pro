"""CLI command suite for Timeline manipulation, inspection, and validation."""

import json
from pathlib import Path
import sys
from typing import Optional
import click

from hyperedit.core.exceptions import HyperEditError
from hyperedit.core.models.project import Project
from hyperedit.core.models.timecode import Timecode
from hyperedit.core.models.timeline import Clip
from hyperedit.timeline.engine import TimelineEngine


@click.group("timeline")
def timeline_group() -> None:
    """Timeline editing suite: inspect, validate, insert, split, trim, delete, and close gaps."""
    pass


@timeline_group.command("inspect")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "output_json", is_flag=True, default=False, help="Output timeline map as JSON.")
def inspect_subcommand(project_file: Path, output_json: bool) -> None:
    """Visually inspect tracks, clips, timings, transitions, and temporal gaps."""
    try:
        project = Project.load_from_file(project_file)
        fps = project.settings.fps
        engine = TimelineEngine()

        tracks_data = []
        for track in project.timeline.tracks:
            collisions = engine.detect_collisions(project.timeline, track.track_id)
            track_clips = []
            for c in track.clips:
                tc_start = Timecode.from_frames(c.timeline_start_frame, fps).to_smpte()
                tc_end = Timecode.from_frames(c.timeline_end_frame, fps).to_smpte()
                trans_info = None
                if c.transition_in:
                    trans_info = f"In: {c.transition_in.type.value} ({c.transition_in.duration_frames}f)"
                elif c.transition_out:
                    trans_info = f"Out: {c.transition_out.type.value} ({c.transition_out.duration_frames}f)"

                track_clips.append({
                    "clip_id": c.clip_id,
                    "asset_id": c.asset_id,
                    "in_frame": c.in_frame,
                    "out_frame": c.out_frame,
                    "start_frame": c.timeline_start_frame,
                    "end_frame": c.timeline_end_frame,
                    "duration_frames": c.timeline_duration_frames,
                    "timecode_start": tc_start,
                    "timecode_end": tc_end,
                    "speed": c.speed,
                    "reverse": c.reverse,
                    "transition": trans_info,
                })
            tracks_data.append({
                "track_id": track.track_id,
                "name": track.name,
                "kind": track.kind.value,
                "clips_count": len(track.clips),
                "collisions": len(collisions),
                "clips": track_clips,
            })

        report = {
            "title": project.metadata.title,
            "fps": fps,
            "canvas": f"{project.settings.width}x{project.settings.height}",
            "total_frames": project.duration_frames,
            "duration_timecode": Timecode.from_frames(project.duration_frames, fps).to_smpte(),
            "duration_seconds": project.duration_seconds,
            "tracks": tracks_data,
        }

        if output_json:
            click.echo(json.dumps(report, indent=2))
        else:
            click.secho(f"=== Timeline Inspection: {project.metadata.title} ===", bold=True, fg="cyan")
            click.echo(f"  Canvas: {project.settings.width}x{project.settings.height} @ {fps} fps")
            click.echo(f"  Total Duration: {project.duration_frames} frames ({report['duration_timecode']} / {project.duration_seconds:.2f}s)")
            click.echo("------------------------------------------------------------")

            for t in tracks_data:
                click.secho(f"Track [{t['track_id']}] '{t['name']}' ({t['kind'].upper()}) - {t['clips_count']} clip(s)", bold=True, fg="yellow")
                if t['collisions'] > 0:
                    click.secho(f"  ▲ Warning: {t['collisions']} collision(s) detected without transitions!", fg="red")

                if not t['clips']:
                    click.echo("    (empty track)")
                for c in t['clips']:
                    trans_str = f" | {c['transition']}" if c['transition'] else ""
                    spd_str = f" | {c['speed']}x" if c['speed'] != 1.0 else ""
                    rev_str = " | REV" if c['reverse'] else ""
                    click.echo(
                        f"    • [{c['start_frame']:05d} -> {c['end_frame']:05d}] '{c['clip_id']}' "
                        f"(src: {c['asset_id']}[{c['in_frame']}:{c['out_frame']}]{spd_str}{rev_str}{trans_str})"
                    )
            click.secho("============================================================", bold=True, fg="cyan")

    except HyperEditError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@timeline_group.command("validate")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "output_json", is_flag=True, default=False, help="Output validation result as JSON.")
def validate_subcommand(project_file: Path, output_json: bool) -> None:
    """Validate timeline consistency, clip references, and absence of collisions."""
    try:
        project = Project.load_from_file(project_file)
        engine = TimelineEngine()

        total_collisions = 0
        for track in project.timeline.tracks:
            collisions = engine.detect_collisions(project.timeline, track.track_id)
            total_collisions += len(collisions)

        if total_collisions > 0:
            raise HyperEditError(f"Timeline validation failed: {total_collisions} colliding clip overlap(s) found.")

        result = {
            "valid": True,
            "project": str(project_file),
            "tracks": len(project.timeline.tracks),
            "duration_frames": project.duration_frames,
            "message": "Timeline is structurally sound with zero unauthorized collisions."
        }
        if output_json:
            click.echo(json.dumps(result, indent=2))
        else:
            click.secho("✓ Timeline validated: Zero collisions, clean frame continuity.", fg="green", bold=True)
    except HyperEditError as e:
        if output_json:
            click.echo(json.dumps({"valid": False, "error": str(e)}, indent=2))
        else:
            click.secho(f"✗ Timeline Validation Failed: {e}", fg="red", err=True)
        sys.exit(1)


@timeline_group.command("insert")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--track", "track_id", required=True, help="Target track ID (e.g. V1, A1).")
@click.option("--asset", "asset_id", required=True, help="Asset ID registered in media pool.")
@click.option("--in", "in_frame", type=int, default=0, help="Source in-point frame index.")
@click.option("--out", "out_frame", type=int, required=True, help="Source out-point frame index.")
@click.option("--start", "start_frame", type=int, default=0, help="Timeline start frame index.")
@click.option("--speed", type=float, default=1.0, help="Playback speed multiplier.")
@click.option("--clip-id", default=None, help="Custom clip instance ID.")
@click.option("--ripple", is_flag=True, default=False, help="Ripple downstream clips forward.")
@click.option("-o", "--output", "output_file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def insert_subcommand(
    project_file: Path,
    track_id: str,
    asset_id: str,
    in_frame: int,
    out_frame: int,
    start_frame: int,
    speed: float,
    clip_id: Optional[str],
    ripple: bool,
    output_file: Optional[Path],
) -> None:
    """Insert a clip onto a timeline track with ripple or overwrite mode."""
    try:
        project = Project.load_from_file(project_file)
        engine = TimelineEngine()

        cid = clip_id or f"clip_{asset_id}_{start_frame}"
        new_clip = Clip(
            clip_id=cid,
            asset_id=asset_id,
            in_frame=in_frame,
            out_frame=out_frame,
            timeline_start_frame=start_frame,
            speed=speed,
        )

        engine.insert_clip(project.timeline, track_id=track_id, clip=new_clip, ripple=ripple)

        target_path = output_file or project_file
        project.save_to_file(target_path)
        mode_str = "ripple" if ripple else "overwrite"
        click.secho(f"✓ Inserted '{cid}' onto [{track_id}] in {mode_str} mode ({target_path.name})", fg="green")
    except HyperEditError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@timeline_group.command("split")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--track", "track_id", required=True, help="Track ID containing the clip.")
@click.option("--clip", "clip_id", required=True, help="Clip ID to split.")
@click.option("--frame", "split_frame", type=int, required=True, help="Timeline frame index to cut at.")
@click.option("-o", "--output", "output_file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def split_subcommand(
    project_file: Path,
    track_id: str,
    clip_id: str,
    split_frame: int,
    output_file: Optional[Path],
) -> None:
    """Split an existing clip into two segments at a precise timeline frame."""
    try:
        project = Project.load_from_file(project_file)
        engine = TimelineEngine()

        c1, c2 = engine.split_clip(project.timeline, track_id=track_id, clip_id=clip_id, split_frame=split_frame)

        target_path = output_file or project_file
        project.save_to_file(target_path)
        click.secho(f"✓ Split '{clip_id}' at frame {split_frame} -> '{c1.clip_id}' and '{c2.clip_id}'", fg="green")
    except HyperEditError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@timeline_group.command("trim")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--track", "track_id", required=True, help="Track ID.")
@click.option("--clip", "clip_id", required=True, help="Clip ID to trim.")
@click.option("--in", "in_frame", type=int, default=None, help="New in-point frame index.")
@click.option("--out", "out_frame", type=int, default=None, help="New out-point frame index.")
@click.option("--ripple", is_flag=True, default=False, help="Ripple downstream clips.")
@click.option("-o", "--output", "output_file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def trim_subcommand(
    project_file: Path,
    track_id: str,
    clip_id: str,
    in_frame: Optional[int],
    out_frame: Optional[int],
    ripple: bool,
    output_file: Optional[Path],
) -> None:
    """Trim a clip's head (in-point) or tail (out-point)."""
    try:
        project = Project.load_from_file(project_file)
        engine = TimelineEngine()

        trimmed = engine.trim_clip(
            project.timeline,
            track_id=track_id,
            clip_id=clip_id,
            in_frame=in_frame,
            out_frame=out_frame,
            ripple=ripple,
        )

        target_path = output_file or project_file
        project.save_to_file(target_path)
        click.secho(
            f"✓ Trimmed '{clip_id}': in={trimmed.in_frame}, out={trimmed.out_frame} "
            f"(timeline: {trimmed.timeline_start_frame} -> {trimmed.timeline_end_frame})",
            fg="green",
        )
    except HyperEditError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@timeline_group.command("delete")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--track", "track_id", required=True, help="Track ID.")
@click.option("--clip", "clip_id", required=True, help="Clip ID to delete.")
@click.option("--ripple", is_flag=True, default=False, help="Close gap by pulling subsequent clips backward.")
@click.option("-o", "--output", "output_file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def delete_subcommand(
    project_file: Path,
    track_id: str,
    clip_id: str,
    ripple: bool,
    output_file: Optional[Path],
) -> None:
    """Delete a clip from a track with optional ripple gap closure."""
    try:
        project = Project.load_from_file(project_file)
        engine = TimelineEngine()

        if ripple:
            engine.ripple_delete(project.timeline, track_id=track_id, clip_id=clip_id)
        else:
            track = engine.get_track(project.timeline, track_id)
            idx, _ = engine.find_clip(track, clip_id)
            track.clips.pop(idx)

        target_path = output_file or project_file
        project.save_to_file(target_path)
        mode_str = "with ripple gap closure" if ripple else "leaving gap"
        click.secho(f"✓ Deleted '{clip_id}' from [{track_id}] ({mode_str})", fg="green")
    except HyperEditError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@timeline_group.command("close-gaps")
@click.argument("project_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--track", "track_id", required=True, help="Track ID.")
@click.option("-o", "--output", "output_file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def close_gaps_subcommand(project_file: Path, track_id: str, output_file: Optional[Path]) -> None:
    """Eliminate all empty frames between consecutive clips on a track."""
    try:
        project = Project.load_from_file(project_file)
        engine = TimelineEngine()

        gaps = engine.close_gaps(project.timeline, track_id=track_id)
        target_path = output_file or project_file
        project.save_to_file(target_path)
        click.secho(f"✓ Closed {gaps} gap(s) on track [{track_id}]", fg="green")
    except HyperEditError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

