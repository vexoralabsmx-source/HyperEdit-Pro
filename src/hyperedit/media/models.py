"""Domain models and structured metadata schemas for HyperEdit Pro Media Engine."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    IMAGE_SEQUENCE = "image_sequence"
    UNKNOWN = "unknown"


class FrameRateType(str, Enum):
    CONSTANT = "cfr"
    VARIABLE = "vfr"
    UNKNOWN = "unknown"


class FrameRateInfo(BaseModel):
    """Detailed frame rate and timing information."""

    fps: float = Field(..., gt=0, description="Evaluated frame rate in fps")
    r_frame_rate: str = Field(..., description="Nominal stream frame rate fraction (e.g. 24000/1001)")
    avg_frame_rate: str = Field(..., description="Average stream frame rate fraction")
    is_vfr: bool = Field(default=False, description="True if stream exhibits variable frame rate timing")
    time_base: str = Field(default="1/1000", description="Time base unit fraction")


class SilenceInterval(BaseModel):
    """Detected silent temporal interval in an audio stream."""

    start_seconds: float = Field(..., ge=0.0)
    end_seconds: float = Field(..., ge=0.0)
    duration_seconds: float = Field(..., ge=0.0)


class AudioSignalMetrics(BaseModel):
    """Acoustic signal metrics and loudness telemetry."""

    peak_db: float = Field(default=0.0, description="Maximum peak amplitude in dBFS")
    mean_volume_db: float = Field(default=-96.0, description="Mean volume / RMS in dBFS")
    max_volume_db: float = Field(default=0.0, description="Max volume detected in dBFS")
    dynamic_range_db: float = Field(default=0.0, description="Difference between max and mean volume")
    has_clipping: bool = Field(default=False, description="True if peak amplitude reaches or exceeds 0.0 dBFS")
    silence_intervals: List[SilenceInterval] = Field(default_factory=list)


class VideoStreamDetails(BaseModel):
    """In-depth video stream parameters probed via ffprobe."""

    index: int = Field(default=0, ge=0)
    codec: str = Field(..., description="Video codec name e.g. h264, hevc, prores, vp9, av1")
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    aspect_ratio: Optional[str] = Field(default="16:9")
    pixel_format: str = Field(default="yuv420p")
    bit_depth: int = Field(default=8, ge=8, le=16)
    color_space: Optional[str] = Field(default=None)
    color_primaries: Optional[str] = Field(default=None)
    color_transfer: Optional[str] = Field(default=None)
    rotation_deg: int = Field(default=0, description="Metadata orientation angle in degrees (0, 90, 180, 270)")
    is_vertical: bool = Field(default=False, description="True if height exceeds width or rotated 90/270")
    frame_rate_info: FrameRateInfo
    duration_seconds: float = Field(default=0.0, ge=0.0)
    nb_frames: Optional[int] = Field(default=None, ge=0)
    bitrate_kbps: Optional[int] = Field(default=None, ge=0)


class AudioStreamDetails(BaseModel):
    """In-depth audio stream parameters probed via ffprobe."""

    index: int = Field(default=0, ge=0)
    codec: str = Field(..., description="Audio codec name e.g. aac, pcm_s16le, opus, mp3")
    sample_rate: int = Field(default=48000, gt=0)
    channels: int = Field(default=2, ge=1)
    channel_layout: str = Field(default="stereo")
    bits_per_sample: Optional[int] = Field(default=16)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    bitrate_kbps: Optional[int] = Field(default=None, ge=0)


class MediaArtifacts(BaseModel):
    """Associated proxy, thumbnail, and visualization artifact paths."""

    thumbnail_path: Optional[str] = Field(default=None)
    contact_sheet_path: Optional[str] = Field(default=None)
    waveform_path: Optional[str] = Field(default=None)
    proxy_path: Optional[str] = Field(default=None)
    extracted_audio_path: Optional[str] = Field(default=None)


class MediaValidationReport(BaseModel):
    """Validation audit for imported media files."""

    is_valid: bool = Field(...)
    media_type: MediaType = Field(default=MediaType.UNKNOWN)
    is_corrupted: bool = Field(default=False)
    is_supported: bool = Field(default=True)
    error_message: Optional[str] = Field(default=None)
    warnings: List[str] = Field(default_factory=list)


class ComprehensiveMediaAsset(BaseModel):
    """Rich media asset container with complete stream telemetry, artifacts, and signal analysis."""

    asset_id: str = Field(..., description="Canonical sanitized asset identifier")
    file_path: str = Field(..., description="Resolved cross-platform file path")
    media_type: MediaType = Field(default=MediaType.UNKNOWN)
    format_name: str = Field(default="unknown")
    size_bytes: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    bitrate_kbps: Optional[int] = Field(default=None, ge=0)
    hash_sha256: Optional[str] = Field(default=None)
    file_mtime: float = Field(default=0.0)

    video_streams: List[VideoStreamDetails] = Field(default_factory=list)
    audio_streams: List[AudioStreamDetails] = Field(default_factory=list)
    signal_metrics: Optional[AudioSignalMetrics] = Field(default=None)
    artifacts: MediaArtifacts = Field(default_factory=MediaArtifacts)
    tags: Dict[str, str] = Field(default_factory=dict)

    @property
    def has_video(self) -> bool:
        return len(self.video_streams) > 0

    @property
    def has_audio(self) -> bool:
        return len(self.audio_streams) > 0

    @property
    def primary_video(self) -> Optional[VideoStreamDetails]:
        return self.video_streams[0] if self.video_streams else None

    @property
    def primary_audio(self) -> Optional[AudioStreamDetails]:
        return self.audio_streams[0] if self.audio_streams else None

