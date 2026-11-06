"""Professional Multi-Track Timeline and Non-Destructive Editing Engine for HyperEdit Pro."""

from typing import Dict, List, Optional, Tuple

from hyperedit.core.exceptions import TimelineIntegrityError
from hyperedit.core.models.timeline import Clip, Timeline, Track, TrackKind
from hyperedit.core.protocols import TimelineEngineProtocol


class TimelineEngine(TimelineEngineProtocol):
    """Discrete-frame non-linear editing engine for multi-track compositions."""

    def get_track(self, timeline: Timeline, track_id: str) -> Track:
        """Find track by track_id or raise TimelineIntegrityError."""
        track = timeline.get_track(track_id)
        if not track:
            raise TimelineIntegrityError(f"Track '{track_id}' not found on timeline.")
        return track

    def find_clip(self, track: Track, clip_id: str) -> Tuple[int, Clip]:
        """Find clip index and clip instance on a track."""
        for idx, clip in enumerate(track.clips):
            if clip.clip_id == clip_id:
                return idx, clip
        raise TimelineIntegrityError(f"Clip '{clip_id}' not found on track '{track.track_id}'.")

    def insert_clip(
        self,
        timeline: Timeline,
        track_id: str,
        clip: Clip,
        ripple: bool = False,
    ) -> Timeline:
        """Insert a clip onto a track in either ripple or overwrite mode."""
        track = self.get_track(timeline, track_id)

        if ripple:
            # Shift all downstream clips forward
            insert_start = clip.timeline_start_frame
            insert_duration = clip.timeline_duration_frames
            for c in track.clips:
                if c.timeline_start_frame >= insert_start:
                    c.timeline_start_frame += insert_duration
            track.clips.append(clip)
        else:
            # Overwrite mode: slice, trim, or remove colliding segments
            new_start = clip.timeline_start_frame
            new_end = clip.timeline_end_frame
            surviving_clips: List[Clip] = []

            for c in track.clips:
                c_start = c.timeline_start_frame
                c_end = c.timeline_end_frame

                # Case 1: No overlap
                if c_end <= new_start or c_start >= new_end:
                    surviving_clips.append(c)
                # Case 2: Existing clip is completely covered by new clip -> drop it
                elif new_start <= c_start and new_end >= c_end:
                    continue
                # Case 3: Overwrite right side of existing clip (trim its tail)
                elif c_start < new_start and c_end <= new_end:
                    cut_duration = new_start - c_start
                    source_frames = int(round(cut_duration * c.speed))
                    c.out_frame = c.in_frame + max(1, source_frames)
                    surviving_clips.append(c)
                # Case 4: Overwrite left side of existing clip (trim its head)
                elif new_start <= c_start and c_end > new_end:
                    shift_timeline = new_end - c_start
                    source_shift = int(round(shift_timeline * c.speed))
                    c.in_frame = c.in_frame + source_shift
                    c.timeline_start_frame = new_end
                    surviving_clips.append(c)
                # Case 5: Overwrite middle of existing clip (punches a hole -> split into two)
                elif c_start < new_start and new_end < c_end:
                    # Head slice
                    head_duration = new_start - c_start
                    head_src = c.in_frame + int(round(head_duration * c.speed))
                    clip_left = c.model_copy(deep=True)
                    clip_left.clip_id = f"{c.clip_id}_ov_head"
                    clip_left.out_frame = head_src
                    surviving_clips.append(clip_left)

                    # Tail slice
                    tail_start_src = c.in_frame + int(round((new_end - c_start) * c.speed))
                    clip_right = c.model_copy(deep=True)
                    clip_right.clip_id = f"{c.clip_id}_ov_tail"
                    clip_right.in_frame = tail_start_src
                    clip_right.timeline_start_frame = new_end
                    surviving_clips.append(clip_right)

            surviving_clips.append(clip)
            track.clips = surviving_clips

        track.sort_clips()
        return timeline

    def split_clip(
        self,
        timeline: Timeline,
        track_id: str,
        clip_id: str,
        split_frame: int,
    ) -> Tuple[Clip, Clip]:
        """Split a clip into two independent segments at the given timeline frame."""
        track = self.get_track(timeline, track_id)
        idx, clip = self.find_clip(track, clip_id)

        if not (clip.timeline_start_frame < split_frame < clip.timeline_end_frame):
            raise TimelineIntegrityError(
                f"Split frame {split_frame} is outside clip '{clip_id}' bounds "
                f"[{clip.timeline_start_frame}, {clip.timeline_end_frame}]."
            )

        delta_tl = split_frame - clip.timeline_start_frame
        source_delta = int(round(delta_tl * clip.speed))
        source_split = clip.in_frame + source_delta

        # Safeguard boundaries
        if source_split <= clip.in_frame:
            source_split = clip.in_frame + 1
        elif source_split >= clip.out_frame:
            source_split = clip.out_frame - 1

        # Clip Part 1 (Head)
        clip1 = clip.model_copy(deep=True)
        clip1.clip_id = f"{clip.clip_id}_p1"
        clip1.out_frame = source_split
        clip1.transition_out = None

        # Clip Part 2 (Tail)
        clip2 = clip.model_copy(deep=True)
        clip2.clip_id = f"{clip.clip_id}_p2"
        clip2.in_frame = source_split
        clip2.timeline_start_frame = split_frame
        clip2.transition_in = None

        # Replace original with the two slices
        track.clips.pop(idx)
        track.clips.insert(idx, clip2)
        track.clips.insert(idx, clip1)
        track.sort_clips()

        return clip1, clip2

    def trim_clip(
        self,
        timeline: Timeline,
        track_id: str,
        clip_id: str,
        in_frame: Optional[int] = None,
        out_frame: Optional[int] = None,
        ripple: bool = False,
    ) -> Clip:
        """Modify in-point or out-point of an existing clip."""
        track = self.get_track(timeline, track_id)
        idx, clip = self.find_clip(track, clip_id)

        old_duration = clip.timeline_duration_frames
        old_end = clip.timeline_end_frame

        if in_frame is not None:
            if in_frame >= clip.out_frame:
                raise TimelineIntegrityError(f"Trim in_frame ({in_frame}) must be less than out_frame ({clip.out_frame}).")
            shift_src = in_frame - clip.in_frame
            shift_tl = int(round(shift_src / clip.speed))
            clip.in_frame = in_frame
            if not ripple:
                clip.timeline_start_frame += shift_tl

        if out_frame is not None:
            if out_frame <= clip.in_frame:
                raise TimelineIntegrityError(f"Trim out_frame ({out_frame}) must be greater than in_frame ({clip.in_frame}).")
            clip.out_frame = out_frame

        new_duration = clip.timeline_duration_frames
        delta = new_duration - old_duration

        if ripple and delta != 0:
            for c in track.clips:
                if c.timeline_start_frame >= old_end and c.clip_id != clip.clip_id:
                    c.timeline_start_frame += delta

        track.sort_clips()
        return clip

    def ripple_delete(
        self,
        timeline: Timeline,
        track_id: str,
        clip_id: str,
    ) -> Timeline:
        """Remove a clip and pull subsequent clips backward to close the resulting gap."""
        track = self.get_track(timeline, track_id)
        idx, clip = self.find_clip(track, clip_id)

        del_duration = clip.timeline_duration_frames
        del_end = clip.timeline_end_frame

        track.clips.pop(idx)

        for c in track.clips:
            if c.timeline_start_frame >= del_end:
                c.timeline_start_frame = max(0, c.timeline_start_frame - del_duration)

        track.sort_clips()
        return timeline

    def move_clip(
        self,
        timeline: Timeline,
        source_track_id: str,
        clip_id: str,
        new_start_frame: int,
        target_track_id: Optional[str] = None,
    ) -> Clip:
        """Move a clip in time and optionally transfer to another track."""
        if new_start_frame < 0:
            raise TimelineIntegrityError(f"Timeline start frame cannot be negative: {new_start_frame}")

        src_track = self.get_track(timeline, source_track_id)
        idx, clip = self.find_clip(src_track, clip_id)

        target_track = src_track
        if target_track_id and target_track_id != source_track_id:
            target_track = self.get_track(timeline, target_track_id)
            if target_track.kind != src_track.kind:
                raise TimelineIntegrityError(
                    f"Cannot move clip across incompatible track types ({src_track.kind} -> {target_track.kind})."
                )
            src_track.clips.pop(idx)
            target_track.clips.append(clip)

        clip.timeline_start_frame = new_start_frame
        target_track.sort_clips()
        return clip

    def close_gaps(self, timeline: Timeline, track_id: str) -> int:
        """Close empty temporal gaps between adjacent clips on a track."""
        track = self.get_track(timeline, track_id)
        track.sort_clips()
        gaps_closed = 0

        current_playhead = 0
        for clip in track.clips:
            if clip.timeline_start_frame > current_playhead:
                clip.timeline_start_frame = current_playhead
                gaps_closed += 1
            current_playhead = clip.timeline_end_frame

        return gaps_closed

    def detect_collisions(self, timeline: Timeline, track_id: str) -> List[dict]:
        """Audit track for overlapping clips without active transitions."""
        track = self.get_track(timeline, track_id)
        track.sort_clips()
        collisions = []

        for i in range(len(track.clips) - 1):
            c1 = track.clips[i]
            c2 = track.clips[i + 1]
            if c1.timeline_end_frame > c2.timeline_start_frame:
                if not (c2.transition_in or c1.transition_out):
                    overlap = c1.timeline_end_frame - c2.timeline_start_frame
                    collisions.append({
                        "clip1": c1.clip_id,
                        "clip2": c2.clip_id,
                        "overlap_frames": overlap,
                    })
        return collisions

    def find_clips_at_frame(self, timeline: Timeline, frame: int) -> Dict[str, Clip]:
        """Query active clip on each track at a given timeline frame index."""
        active: Dict[str, Clip] = {}
        for track in timeline.tracks:
            for clip in track.clips:
                if clip.timeline_start_frame <= frame < clip.timeline_end_frame:
                    active[track.track_id] = clip
                    break
        return active

