"""Root Project model, settings, metadata and serialization for HyperEdit Pro."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from hyperedit.core.constants import HYPEREDIT_PROJECT_SCHEMA_VERSION, STANDARD_SAMPLE_RATES
from hyperedit.core.exceptions import ProjectValidationError, TimelineIntegrityError
from hyperedit.core.models.captions import SubtitleTrack
from hyperedit.core.models.export import ExportPreset
from hyperedit.core.models.media import MediaPool
from hyperedit.core.models.timeline import Timeline


class ProjectSettings(BaseModel):
    """Global audiovisual configuration for the project master."""

    width: int = Field(default=1920, gt=0, description="Canvas master width in pixels")
    height: int = Field(default=1080, gt=0, description="Canvas master height in pixels")
    fps: float = Field(default=30.0, gt=0.0, description="Timeline base frame rate")
    sample_rate: int = Field(default=48000, description="Master audio sample rate in Hz")
    audio_channels: int = Field(default=2, ge=1, le=8, description="Master audio channels (2 = stereo)")
    color_space: str = Field(default="bt709", description="Master color space, e.g. bt709, bt2020nc")
    working_pixel_format: str = Field(default="yuv420p")


class ProjectMetadata(BaseModel):
    """Informational metadata for the project."""

    title: str = Field(default="Untitled HyperEdit Project")
    description: Optional[str] = Field(default=None)
    author: Optional[str] = Field(default="HyperEdit Agent")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Project(BaseModel):
    """Root HyperEdit Pro Project format (v2.0)."""

    schema_version: str = Field(default=HYPEREDIT_PROJECT_SCHEMA_VERSION)
    metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    media_pool: MediaPool = Field(default_factory=MediaPool)
    timeline: Timeline = Field(default_factory=Timeline)
    subtitles: List[SubtitleTrack] = Field(default_factory=list)
    export_presets: Dict[str, ExportPreset] = Field(default_factory=dict)

    @property
    def fps(self) -> float:
        return self.settings.fps

    @property
    def duration_frames(self) -> int:
        return self.timeline.duration_frames

    @property
    def duration_seconds(self) -> float:
        fps = self.settings.fps
        return self.duration_frames / fps if fps > 0 else 0.0

    def validate_integrity(self) -> None:
        """Validate references and structural integrity of the project."""
        # 1. Validate all clip asset references exist in media_pool or are valid generators
        for track in self.timeline.tracks:
            for clip in track.clips:
                if clip.asset_id.startswith("generator:"):
                    continue
                if clip.asset_id not in self.media_pool.assets:
                    raise TimelineIntegrityError(
                        f"Clip '{clip.clip_id}' on track '{track.track_id}' references unknown asset_id: '{clip.asset_id}'"
                    )

            # 2. Check for overlapping clips on the same track if track is video or graphic
            track.sort_clips()
            for i in range(len(track.clips) - 1):
                c1 = track.clips[i]
                c2 = track.clips[i + 1]
                if c1.timeline_end_frame > c2.timeline_start_frame:
                    # Unless a transition is defined, overlapping clips on a single video track is invalid
                    if not (c2.transition_in or c1.transition_out):
                        raise TimelineIntegrityError(
                            f"Clips '{c1.clip_id}' and '{c2.clip_id}' collide on track '{track.track_id}' "
                            f"(Clip 1 ends at {c1.timeline_end_frame}, Clip 2 starts at {c2.timeline_start_frame}) "
                            f"without an active transition."
                        )

    def to_json(self, indent: int = 2) -> str:
        """Serialize project to JSON string."""
        return self.model_dump_json(indent=indent)

    def save_to_file(self, file_path: Path | str) -> None:
        """Write project JSON to disk."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata.updated_at = datetime.now(timezone.utc).isoformat()
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load_from_file(cls, file_path: Path | str) -> "Project":
        """Load and validate project from JSON file."""
        path = Path(file_path)
        if not path.is_file():
            raise ProjectValidationError(f"Project file does not exist: {path}")
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            project = cls.model_validate(data)
            project.validate_integrity()
            return project
        except json.JSONDecodeError as e:
            raise ProjectValidationError(f"Invalid JSON in project file {path}: {e}") from e
        except Exception as e:
            if isinstance(e, (ProjectValidationError, TimelineIntegrityError)):
                raise
            raise ProjectValidationError(f"Failed to load project from {path}: {e}") from e

