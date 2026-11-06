"""Multi-track timeline, tracks, clips, and markers for HyperEdit Pro."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

from hyperedit.core.models.audio import AudioMixConfig
from hyperedit.core.models.color import ColorGradeConfig
from hyperedit.core.models.effects import Effect
from hyperedit.core.models.transforms import Transform
from hyperedit.core.models.transitions import Transition


class TrackKind(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    GRAPHIC = "graphic"          # Motion graphic overlays / HyperFrames renders
    ADJUSTMENT = "adjustment"    # Adjustment layer applying color/effects to tracks below


class Clip(BaseModel):
    """A sliced segment of a media asset placed on the timeline."""

    clip_id: str = Field(..., description="Unique clip instance ID on the timeline")
    asset_id: str = Field(..., description="Referenced media asset ID in MediaPool")
    name: Optional[str] = Field(default=None)
    in_frame: int = Field(default=0, ge=0, description="Source media in-point (start frame)")
    out_frame: int = Field(..., gt=0, description="Source media out-point (end frame)")
    timeline_start_frame: int = Field(default=0, ge=0, description="Absolute frame on timeline")
    speed: float = Field(default=1.0, gt=0.0, le=32.0, description="Playback speed multiplier")
    reverse: bool = Field(default=False, description="Play clip in reverse")
    fit_mode: str = Field(default="fit", description="Framing fit mode: fit, fill, stretch, center")
    volume_db: float = Field(default=0.0, ge=-96.0, le=12.0)
    pan: float = Field(default=0.0, ge=-1.0, le=1.0)
    transform: Optional[Transform] = Field(default=None)
    color_grade: Optional[ColorGradeConfig] = Field(default=None)
    transition_in: Optional[Transition] = Field(default=None)
    transition_out: Optional[Transition] = Field(default=None)
    effects: List[Effect] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_in_out(self) -> "Clip":
        if self.out_frame <= self.in_frame:
            raise ValueError(f"Clip out_frame ({self.out_frame}) must be greater than in_frame ({self.in_frame})")
        return self

    @property
    def source_duration_frames(self) -> int:
        return self.out_frame - self.in_frame

    @property
    def timeline_duration_frames(self) -> int:
        return int(round(self.source_duration_frames / self.speed))

    @property
    def timeline_end_frame(self) -> int:
        return self.timeline_start_frame + self.timeline_duration_frames


class Track(BaseModel):
    """An ordered horizontal track on the timeline containing clips."""

    track_id: str = Field(..., description="Unique track ID (e.g. 'V1', 'A1', 'SUB1')")
    name: str = Field(default="Track")
    kind: TrackKind = Field(default=TrackKind.VIDEO)
    index: int = Field(default=0, ge=0, description="Z-index / track order (0 = lowest)")
    muted: bool = Field(default=False)
    solo: bool = Field(default=False)
    locked: bool = Field(default=False)
    mix_config: Optional[AudioMixConfig] = Field(default=None)
    color_grade: Optional[ColorGradeConfig] = Field(default=None)
    clips: List[Clip] = Field(default_factory=list)

    def sort_clips(self) -> None:
        """Sort clips in ascending order by timeline start frame."""
        self.clips.sort(key=lambda c: c.timeline_start_frame)


class Marker(BaseModel):
    """Timeline temporal bookmark or note."""

    marker_id: str = Field(...)
    frame: int = Field(..., ge=0)
    name: str = Field(default="Marker")
    color: str = Field(default="#00FF00")
    comment: Optional[str] = Field(default=None)


class Timeline(BaseModel):
    """Complete multi-track timeline container."""

    tracks: List[Track] = Field(default_factory=list)
    markers: List[Marker] = Field(default_factory=list)

    @property
    def duration_frames(self) -> int:
        """Calculate total timeline length in frames from the rightmost clip boundary."""
        max_frame = 0
        for track in self.tracks:
            for clip in track.clips:
                max_frame = max(max_frame, clip.timeline_end_frame)
        return max_frame

    def get_track(self, track_id: str) -> Optional[Track]:
        for t in self.tracks:
            if t.track_id == track_id:
                return t
        return None

    def add_track(self, track: Track) -> None:
        self.tracks.append(track)

