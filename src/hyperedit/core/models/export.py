"""Export presets and delivery encoding models for HyperEdit Pro."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ContainerFormat(str, Enum):
    MP4 = "mp4"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"
    WAV = "wav"
    MP3 = "mp3"


class VideoCodec(str, Enum):
    H264 = "h264"
    HEVC = "hevc"
    PRORES = "prores"
    VP9 = "vp9"
    AV1 = "av1"
    COPY = "copy"


class AudioCodec(str, Enum):
    AAC = "aac"
    OPUS = "opus"
    PCM_S16LE = "pcm_s16le"
    PCM_S24LE = "pcm_s24le"
    MP3 = "mp3"
    COPY = "copy"


class HardwareAccel(str, Enum):
    AUTO = "auto"
    NONE = "none"
    NVENC = "nvenc"
    QSV = "qsv"
    VIDEOTOOLBOX = "videotoolbox"
    AMF = "amf"
    VAAPI = "vaapi"


class ExportPreset(BaseModel):
    """Specification for deterministic FFmpeg delivery encoding."""

    name: str = Field(..., description="Preset name, e.g. 'web_1080p', 'prores_422hq'")
    description: Optional[str] = Field(default=None)
    container: ContainerFormat = Field(default=ContainerFormat.MP4)
    video_codec: VideoCodec = Field(default=VideoCodec.H264)
    audio_codec: AudioCodec = Field(default=AudioCodec.AAC)
    width: Optional[int] = Field(default=None, gt=0)
    height: Optional[int] = Field(default=None, gt=0)
    fps: Optional[float] = Field(default=None, gt=0)
    crf: Optional[int] = Field(default=20, ge=0, le=51)
    bitrate_kbps: Optional[int] = Field(default=None, gt=0)
    preset_speed: str = Field(default="medium", description="FFmpeg preset e.g. veryfast, medium, slow, p4")
    pixel_format: str = Field(default="yuv420p")
    audio_bitrate_kbps: int = Field(default=192, gt=0)
    audio_sample_rate: int = Field(default=48000, gt=0)
    hwaccel: HardwareAccel = Field(default=HardwareAccel.AUTO)

