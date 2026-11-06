"""Domain models for HyperEdit Pro Audio Engineering & Beat Synchronization."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TargetPlatform(str, Enum):
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"
    APPLE_PODCASTS = "apple_podcasts"
    EBU_R128 = "ebu_r128"
    ATSC_A85 = "atsc_a85"
    CUSTOM = "custom"


class LoudnessProfile(BaseModel):
    """Broadcast and streaming platform loudness configuration."""

    platform: TargetPlatform = Field(default=TargetPlatform.YOUTUBE)
    target_i: float = Field(default=-14.0, description="Target integrated loudness in LUFS")
    target_lra: float = Field(default=11.0, description="Target loudness range in LU")
    target_tp: float = Field(default=-1.0, description="Target maximum true peak in dBFS")
    description: str = Field(default="Standard YouTube web loudness profile (-14 LUFS / -1.0 dBFS True Peak)")


STANDARD_LOUDNESS_PROFILES: Dict[str, LoudnessProfile] = {
    "youtube": LoudnessProfile(
        platform=TargetPlatform.YOUTUBE,
        target_i=-14.0,
        target_lra=11.0,
        target_tp=-1.0,
        description="YouTube streaming standard: -14 LUFS, max true peak -1.0 dBFS",
    ),
    "spotify": LoudnessProfile(
        platform=TargetPlatform.SPOTIFY,
        target_i=-14.0,
        target_lra=11.0,
        target_tp=-1.0,
        description="Spotify loudness normalization standard: -14 LUFS, max true peak -1.0 dBFS",
    ),
    "apple_podcasts": LoudnessProfile(
        platform=TargetPlatform.APPLE_PODCASTS,
        target_i=-16.0,
        target_lra=9.0,
        target_tp=-1.0,
        description="Apple Podcasts & Music standard: -16 LUFS, max true peak -1.0 dBFS",
    ),
    "ebu_r128": LoudnessProfile(
        platform=TargetPlatform.EBU_R128,
        target_i=-23.0,
        target_lra=7.0,
        target_tp=-1.0,
        description="European Broadcast Union standard EBU R128: -23 LUFS, max true peak -1.0 dBFS",
    ),
    "atsc_a85": LoudnessProfile(
        platform=TargetPlatform.ATSC_A85,
        target_i=-24.0,
        target_lra=7.0,
        target_tp=-1.0,
        description="US Television broadcast standard ATSC A/85: -24 LUFS, max true peak -1.0 dBFS",
    ),
}


class LoudnessMeasurement(BaseModel):
    """Measured acoustic loudness telemetry via EBU R128 scanner."""

    integrated_lufs: float = Field(..., description="Integrated loudness in LUFS")
    true_peak_dbfs: float = Field(..., description="True peak level in dBFS")
    lra: float = Field(..., description="Loudness range in LU")
    threshold_lufs: float = Field(..., description="Gated threshold in LUFS")
    target_lufs: float = Field(default=-14.0)
    deviation_lu: float = Field(default=0.0, description="Deviation from target in LU")
    is_compliant: bool = Field(default=True, description="True if within +/- 1.0 LU tolerance")


class BeatInfo(BaseModel):
    """Signal-detected tempo, onsets, and beat positions."""

    bpm: float = Field(..., gt=0.0, description="Evaluated tempo in beats per minute")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    beat_interval_sec: float = Field(..., gt=0.0, description="Duration of single beat in seconds")
    beat_timestamps: List[float] = Field(default_factory=list, description="Timestamps of detected beats in seconds")
    onset_timestamps: List[float] = Field(default_factory=list, description="Raw detected transient onsets in seconds")
    time_signature: str = Field(default="4/4")
    manual_bpm_override: Optional[float] = Field(default=None)


class CutShiftDetail(BaseModel):
    """Telemetry for an individual cut snapped to a beat."""

    clip_id: str
    original_frame: int
    snapped_frame: int
    shift_frames: int
    shift_ms: float
    beat_time_sec: float


class BeatAlignmentReport(BaseModel):
    """Diagnostic audit of timeline cuts snapped to musical beats."""

    track_id: str
    total_cuts_evaluated: int
    cuts_snapped: int
    max_shift_allowed_frames: int
    mean_shift_ms: float
    max_shift_ms: float
    details: List[CutShiftDetail] = Field(default_factory=list)

