"""Media asset and stream models for HyperEdit Pro."""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StreamType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    DATA = "data"


class VideoStreamInfo(BaseModel):
    """Detailed video stream parameters probed via ffprobe."""

    index: int = Field(default=0, ge=0)
    codec: str = Field(..., description="FFmpeg codec identifier, e.g. h264, hevc, prores")
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    fps: float = Field(..., gt=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    pixel_format: str = Field(default="yuv420p")
    bit_depth: int = Field(default=8, ge=8, le=16)
    aspect_ratio: Optional[str] = Field(default="16:9")
    color_space: Optional[str] = Field(default=None)
    color_primaries: Optional[str] = Field(default=None)
    color_transfer: Optional[str] = Field(default=None)
    bitrate_kbps: Optional[int] = Field(default=None, ge=0)


class AudioStreamInfo(BaseModel):
    """Detailed audio stream parameters probed via ffprobe."""

    index: int = Field(default=0, ge=0)
    codec: str = Field(..., description="Audio codec identifier, e.g. aac, pcm_s16le, opus, mp3")
    sample_rate: int = Field(default=48000, gt=0)
    channels: int = Field(default=2, ge=1)
    channel_layout: str = Field(default="stereo")
    duration_seconds: float = Field(default=0.0, ge=0.0)
    bitrate_kbps: Optional[int] = Field(default=None, ge=0)


class SubtitleStreamInfo(BaseModel):
    """Embedded subtitle stream probed via ffprobe."""

    index: int = Field(default=0, ge=0)
    codec: str = Field(default="subrip")
    language: Optional[str] = Field(default="und")


class MediaAsset(BaseModel):
    """Registered media asset in the project media pool."""

    asset_id: str = Field(..., description="Unique alphanumeric identifier for the asset")
    file_path: str = Field(..., description="Absolute or project-relative file path")
    format_name: Optional[str] = Field(default=None, description="Container format, e.g. mov,mp4,m4a,3gp,3g2,mj2")
    duration_seconds: float = Field(default=0.0, ge=0.0)
    size_bytes: int = Field(default=0, ge=0)
    video_streams: List[VideoStreamInfo] = Field(default_factory=list)
    audio_streams: List[AudioStreamInfo] = Field(default_factory=list)
    subtitle_streams: List[SubtitleStreamInfo] = Field(default_factory=list)
    hash_sha256: Optional[str] = Field(default=None)

    @property
    def has_video(self) -> bool:
        return len(self.video_streams) > 0

    @property
    def has_audio(self) -> bool:
        return len(self.audio_streams) > 0

    @property
    def primary_video(self) -> Optional[VideoStreamInfo]:
        return self.video_streams[0] if self.video_streams else None

    @property
    def primary_audio(self) -> Optional[AudioStreamInfo]:
        return self.audio_streams[0] if self.audio_streams else None


class MediaPool(BaseModel):
    """Dictionary of registered media assets keyed by asset_id."""

    assets: Dict[str, MediaAsset] = Field(default_factory=dict)

    def add_asset(self, asset: MediaAsset) -> None:
        self.assets[asset.asset_id] = asset

    def get_asset(self, asset_id: str) -> Optional[MediaAsset]:
        return self.assets.get(asset_id)

