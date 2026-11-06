"""Deterministic FFmpeg filtergraph compiler for HyperEdit Pro timelines."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from hyperedit.core.exceptions import FiltergraphCompileError
from hyperedit.core.models.export import ExportPreset
from hyperedit.core.models.project import Project
from hyperedit.core.models.timeline import TrackKind


def sanitize_label(name: str) -> str:
    """Sanitize label string for FFmpeg filtergraph node IDs."""
    return "".join(c if c.isalnum() else "_" for c in name)


class FiltergraphCompiler:
    """Compiles multi-track timelines into deterministic FFmpeg filtergraph graphs."""

    def compile(
        self,
        project: Project,
        preset: ExportPreset,
    ) -> Tuple[List[str], str, List[str], float]:
        """Compile project timeline into FFmpeg inputs, -filter_complex script, and output maps.

        Returns:
            (input_args, filter_complex_string, output_maps, duration_seconds)
        """
        fps = float(project.settings.fps)
        width = preset.width or project.settings.width
        height = preset.height or project.settings.height
        duration_sec = max(0.5, project.duration_seconds)
        timebase_den = round(fps) if abs(fps - round(fps)) < 0.01 else 1000

        # 1. Collect inputs
        input_args: List[str] = []
        asset_input_map: Dict[str, int] = {}

        # Collect unique assets referenced by clips
        unique_asset_ids = set()
        for track in project.timeline.tracks:
            for clip in track.clips:
                if not clip.asset_id.startswith("generator:"):
                    unique_asset_ids.add(clip.asset_id)

        for asset_id in sorted(unique_asset_ids):
            media_asset = project.media_pool.get_asset(asset_id)
            if not media_asset:
                raise FiltergraphCompileError(f"Clip references missing asset '{asset_id}'")
            asset_path = Path(media_asset.file_path).resolve()
            if not asset_path.exists():
                raise FiltergraphCompileError(f"Source media file not found on disk: {asset_path}")

            asset_input_map[asset_id] = len(input_args) // 2
            input_args.extend(["-i", str(asset_path)])

        filter_nodes: List[str] = []

        # 2. Process Video Tracks
        video_tracks = [t for t in project.timeline.tracks if t.kind in (TrackKind.VIDEO, TrackKind.GRAPHIC)]
        video_tracks.sort(key=lambda t: t.index)

        has_video_clips = any(len(t.clips) > 0 for t in video_tracks)

        current_master_v: Optional[str] = None

        if has_video_clips:
            # Base track (V1)
            primary_track = video_tracks[0]
            track_label = sanitize_label(primary_track.track_id)

            clip_labels: List[str] = []
            for c_idx, clip in enumerate(primary_track.clips):
                c_lbl = f"v_{track_label}_c{c_idx}"
                in_idx = asset_input_map[clip.asset_id]
                src_in_sec = clip.in_frame / fps
                src_out_sec = clip.out_frame / fps

                filters = [
                    f"trim=start={src_in_sec:.4f}:end={src_out_sec:.4f}",
                    "setpts=PTS-STARTPTS",
                ]

                # Speed & Reverse
                if clip.speed != 1.0:
                    pts_mult = 1.0 / clip.speed
                    filters.append(f"setpts={pts_mult:.6f}*PTS")
                if clip.reverse:
                    filters.append("reverse")

                # Framing / Letterbox
                filters.extend([
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
                    "setsar=1",
                    f"fps=fps={fps}",
                    f"settb=1/{timebase_den}",
                ])

                # Color Grading
                if clip.color_grade and clip.color_grade.enabled:
                    from hyperedit.color.engine import ColorGradingEngine
                    cg_filt = ColorGradingEngine.build_ffmpeg_filter(clip.color_grade)
                    if cg_filt and cg_filt != "null":
                        filters.append(cg_filt)

                filter_nodes.append(f"[{in_idx}:v]{','.join(filters)}[{c_lbl}]")
                clip_labels.append(c_lbl)

            # Assemble primary track clips (transitions vs hard cuts)
            if len(clip_labels) == 1:
                current_master_v = clip_labels[0]
            elif len(clip_labels) > 1:
                # Sequential assembly
                active_stream = clip_labels[0]
                accumulated_duration = primary_track.clips[0].timeline_duration_frames / fps

                for i in range(1, len(clip_labels)):
                    c_prev = primary_track.clips[i - 1]
                    c_curr = primary_track.clips[i]
                    next_stream = clip_labels[i]
                    curr_duration = c_curr.timeline_duration_frames / fps

                    transition = c_curr.transition_in or c_prev.transition_out
                    merged_label = f"v_{track_label}_merge{i}"

                    if transition:
                        trans_type = transition.type.value
                        xfade_map = {
                            "fade": "fade",
                            "crossfade": "fade",
                            "dissolve": "dissolve",
                            "dip_to_black": "fadeblack",
                            "dip_to_white": "fadewhite",
                            "wipe_left": "wipeleft",
                            "wipe_right": "wiperight",
                            "wipe_up": "wipeup",
                            "wipe_down": "wipedown",
                            "slide_left": "slideleft",
                            "slide_right": "slideright",
                            "zoom_in": "zoomin",
                            "zoom_out": "zoomout",
                        }
                        xfade_name = xfade_map.get(trans_type, "fade")
                        t_dur = transition.duration_frames / fps
                        offset = max(0.0, accumulated_duration - t_dur)

                        filter_nodes.append(
                            f"[{active_stream}][{next_stream}]xfade=transition={xfade_name}:"
                            f"duration={t_dur:.4f}:offset={offset:.4f},settb=1/{timebase_den}[{merged_label}]"
                        )
                        accumulated_duration = offset + curr_duration
                    else:
                        # Hard Cut
                        filter_nodes.append(
                            f"[{active_stream}][{next_stream}]concat=n=2:v=1:a=0,settb=1/{timebase_den}[{merged_label}]"
                        )
                        accumulated_duration += curr_duration

                    active_stream = merged_label
                current_master_v = active_stream
                if accumulated_duration > 0:
                    duration_sec = accumulated_duration

            # Overlay subsequent tracks (V2, V3, Graphic)
            for track_idx, track in enumerate(video_tracks[1:], start=1):
                t_lbl = sanitize_label(track.track_id)
                for c_idx, clip in enumerate(track.clips):
                    overlay_lbl = f"ov_{t_lbl}_{c_idx}"
                    out_comp_lbl = f"v_comp_{t_lbl}_{c_idx}"
                    in_idx = asset_input_map[clip.asset_id]

                    src_in_sec = clip.in_frame / fps
                    src_out_sec = clip.out_frame / fps
                    start_sec = clip.timeline_start_frame / fps
                    end_sec = clip.timeline_end_frame / fps

                    # Clip processing
                    c_filters = [
                        f"trim=start={src_in_sec:.4f}:end={src_out_sec:.4f}",
                        "setpts=PTS-STARTPTS",
                    ]
                    if clip.speed != 1.0:
                        c_filters.append(f"setpts={1.0 / clip.speed:.6f}*PTS")
                    if clip.reverse:
                        c_filters.append("reverse")

                    # Spatial transform and scale
                    c_scale = clip.transform.scale_x if clip.transform else 1.0
                    c_opacity = clip.transform.opacity if clip.transform else 1.0
                    pos_x = int(clip.transform.position_x) if clip.transform else 0
                    pos_y = int(clip.transform.position_y) if clip.transform else 0

                    c_filters.extend([
                        f"scale={int(width * c_scale)}:-2",
                        "format=yuva420p",
                        f"colorchannelmixer=aa={c_opacity:.2f}",
                        f"fps=fps={fps}",
                        f"settb=1/{timebase_den}",
                    ])
                    if clip.color_grade and clip.color_grade.enabled:
                        from hyperedit.color.engine import ColorGradingEngine
                        cg_filt = ColorGradingEngine.build_ffmpeg_filter(clip.color_grade)
                        if cg_filt and cg_filt != "null":
                            c_filters.append(cg_filt)
                    filter_nodes.append(f"[{in_idx}:v]{','.join(c_filters)}[{overlay_lbl}]")

                    # Overlay onto master
                    x_pos = f"(W-w)/2+{pos_x}" if pos_x != 0 else "(W-w)/2"
                    y_pos = f"(H-h)/2+{pos_y}" if pos_y != 0 else "(H-h)/2"

                    filter_nodes.append(
                        f"[{current_master_v}][{overlay_lbl}]overlay=x={x_pos}:y={y_pos}:"
                        f"enable='between(t,{start_sec:.4f},{end_sec:.4f})',settb=1/{timebase_den}[{out_comp_lbl}]"
                    )
                    current_master_v = out_comp_lbl
        else:
            # Fallback black canvas
            current_master_v = "v_black"
            filter_nodes.append(f"color=c=black:s={width}x{height}:r={fps}:d={duration_sec}[{current_master_v}]")

        # 3. Process Audio Tracks
        audio_nodes: List[str] = []
        for track in project.timeline.tracks:
            for c_idx, clip in enumerate(track.clips):
                asset_obj = project.media_pool.get_asset(clip.asset_id)
                if not asset_obj or not asset_obj.has_audio:
                    continue

                in_idx = asset_input_map[clip.asset_id]
                src_in_sec = clip.in_frame / fps
                src_out_sec = clip.out_frame / fps
                start_ms = int(round((clip.timeline_start_frame / fps) * 1000))

                a_lbl = f"a_{sanitize_label(track.track_id)}_{c_idx}"
                a_filters = [
                    f"atrim=start={src_in_sec:.4f}:end={src_out_sec:.4f}",
                    "asetpts=PTS-STARTPTS",
                ]

                # Speed compensation via atempo
                if clip.speed != 1.0:
                    spd = clip.speed
                    while spd > 2.0:
                        a_filters.append("atempo=2.0")
                        spd /= 2.0
                    while spd < 0.5:
                        a_filters.append("atempo=0.5")
                        spd /= 0.5
                    a_filters.append(f"atempo={spd:.4f}")

                if clip.reverse:
                    a_filters.append("areverse")

                if clip.volume_db != 0.0:
                    a_filters.append(f"volume={clip.volume_db}dB")

                if start_ms > 0:
                    a_filters.append(f"adelay={start_ms}|{start_ms}")

                filter_nodes.append(f"[{in_idx}:a]{','.join(a_filters)}[{a_lbl}]")
                audio_nodes.append(a_lbl)

        # Mix audio or generate silent track
        if audio_nodes:
            if len(audio_nodes) == 1:
                filter_nodes.append(f"[{audio_nodes[0]}]aresample=48000:async=1[a_master]")
            else:
                inputs_str = "".join(f"[{node}]" for node in audio_nodes)
                filter_nodes.append(
                    f"{inputs_str}amix=inputs={len(audio_nodes)}:normalize=0:dropout_transition=0,"
                    f"aresample=48000:async=1[a_master]"
                )
        else:
            filter_nodes.append(f"anullsrc=r=48000:cl=stereo:d={duration_sec}[a_master]")

        filter_complex_str = ";\n".join(filter_nodes)
        output_maps = ["-map", f"[{current_master_v}]", "-map", "[a_master]"]

        return input_args, filter_complex_str, output_maps, duration_sec
