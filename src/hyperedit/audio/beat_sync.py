"""Temporal beat synchronization and cut snapping for HyperEdit Pro."""

from typing import List, Optional, Tuple, Union

from hyperedit.audio.models import BeatAlignmentReport, BeatInfo, CutShiftDetail
from hyperedit.core.exceptions import TimelineIntegrityError
from hyperedit.core.models.timeline import Marker, Timeline


class BeatSynchronizer:
    """Intelligent audiovisual synchronizer that aligns cuts and transitions to musical beats."""

    def __init__(self, default_fps: float = 30.0) -> None:
        self.default_fps = default_fps

    def find_nearest_beat(
        self,
        target_time_sec: float,
        beats: Union[BeatInfo, List[float]],
    ) -> Tuple[float, float]:
        """Find the closest beat timestamp to a given time in seconds.

        Returns:
            Tuple of (nearest_beat_timestamp_sec, delta_sec) where delta = nearest - target.
        """
        timestamps = beats.beat_timestamps if isinstance(beats, BeatInfo) else beats
        if not timestamps:
            return target_time_sec, 0.0

        nearest = min(timestamps, key=lambda t: abs(t - target_time_sec))
        delta = nearest - target_time_sec
        return nearest, delta

    def add_beat_markers(
        self,
        timeline: Timeline,
        beat_info: BeatInfo,
        fps: Optional[float] = None,
        marker_color: str = "#FF00AA",
        clear_existing_beat_markers: bool = True,
    ) -> int:
        """Inject musical beat markers into the project timeline.

        Returns:
            Number of beat markers added.
        """
        active_fps = fps or self.default_fps

        if clear_existing_beat_markers:
            timeline.markers = [m for m in timeline.markers if not m.marker_id.startswith("beat_")]

        added = 0
        for idx, t in enumerate(beat_info.beat_timestamps, start=1):
            frame = int(round(t * active_fps))
            marker = Marker(
                marker_id=f"beat_{idx:03d}",
                frame=frame,
                name=f"Beat {idx} ({beat_info.bpm:.0f} BPM)",
                color=marker_color,
                comment=f"Beat at t={t:.3f}s",
            )
            timeline.markers.append(marker)
            added += 1

        timeline.markers.sort(key=lambda m: m.frame)
        return added

    def snap_cuts_to_beats(
        self,
        timeline: Timeline,
        track_id: str,
        beats: Union[BeatInfo, List[float]],
        max_shift_frames: int = 8,
        mode: str = "ripple",
        fps: Optional[float] = None,
    ) -> BeatAlignmentReport:
        """Snap edit points (cuts) on a track to the nearest musical beats.

        Args:
            timeline: The project timeline to mutate.
            track_id: Track ID whose cuts should be snapped (e.g. 'V1').
            beats: BeatInfo instance or list of beat timestamps in seconds.
            max_shift_frames: Maximum allowable shift in frames (+/-).
            mode: 'ripple' (shift cut and ripple downstream clips) or 'roll' (adjust adjacent in/out points).
            fps: Frame rate for conversion.

        Returns:
            BeatAlignmentReport containing detailed telemetry for every shifted cut.
        """
        track = timeline.get_track(track_id)
        if not track:
            raise TimelineIntegrityError(f"Track '{track_id}' not found on timeline.")

        track.sort_clips()
        clips = track.clips
        if len(clips) < 2:
            return BeatAlignmentReport(
                track_id=track_id,
                total_cuts_evaluated=0,
                cuts_snapped=0,
                max_shift_allowed_frames=max_shift_frames,
                mean_shift_ms=0.0,
                max_shift_ms=0.0,
                details=[],
            )

        active_fps = fps or self.default_fps
        beat_timestamps = beats.beat_timestamps if isinstance(beats, BeatInfo) else beats
        if not beat_timestamps:
            return BeatAlignmentReport(
                track_id=track_id,
                total_cuts_evaluated=len(clips) - 1,
                cuts_snapped=0,
                max_shift_allowed_frames=max_shift_frames,
                mean_shift_ms=0.0,
                max_shift_ms=0.0,
                details=[],
            )

        details: List[CutShiftDetail] = []
        total_cuts = len(clips) - 1

        for i in range(total_cuts):
            prev_clip = clips[i]
            next_clip = clips[i + 1]

            cut_frame = prev_clip.timeline_end_frame
            cut_time_sec = cut_frame / active_fps

            nearest_beat_t, delta_t = self.find_nearest_beat(cut_time_sec, beat_timestamps)
            beat_frame = int(round(nearest_beat_t * active_fps))
            shift_frames = beat_frame - cut_frame

            if abs(shift_frames) == 0:
                continue

            if abs(shift_frames) > max_shift_frames:
                continue

            shift_ms = (shift_frames / active_fps) * 1000.0

            if mode == "roll":
                # Roll mode: extend/trim prev_clip tail, trim/extend next_clip head
                new_prev_out = prev_clip.out_frame + shift_frames
                new_next_in = next_clip.in_frame + shift_frames

                # Check boundary validity
                if new_prev_out <= prev_clip.in_frame:
                    continue
                if new_next_in >= next_clip.out_frame:
                    continue

                prev_clip.out_frame = new_prev_out
                next_clip.in_frame = new_next_in
                next_clip.timeline_start_frame += shift_frames

            elif mode == "ripple":
                # Ripple mode: shift prev_clip out_frame and ripple all subsequent clips
                new_prev_out = prev_clip.out_frame + shift_frames
                if new_prev_out <= prev_clip.in_frame:
                    continue

                prev_clip.out_frame = new_prev_out
                for j in range(i + 1, len(clips)):
                    clips[j].timeline_start_frame += shift_frames
            else:
                raise ValueError(f"Unknown snap mode: '{mode}'. Must be 'ripple' or 'roll'.")

            details.append(
                CutShiftDetail(
                    clip_id=prev_clip.clip_id,
                    original_frame=cut_frame,
                    snapped_frame=beat_frame,
                    shift_frames=shift_frames,
                    shift_ms=round(shift_ms, 2),
                    beat_time_sec=round(nearest_beat_t, 4),
                )
            )

        mean_ms = (
            sum(abs(d.shift_ms) for d in details) / len(details) if details else 0.0
        )
        max_ms = max((abs(d.shift_ms) for d in details), default=0.0)

        return BeatAlignmentReport(
            track_id=track_id,
            total_cuts_evaluated=total_cuts,
            cuts_snapped=len(details),
            max_shift_allowed_frames=max_shift_frames,
            mean_shift_ms=round(mean_ms, 2),
            max_shift_ms=round(max_ms, 2),
            details=details,
        )

