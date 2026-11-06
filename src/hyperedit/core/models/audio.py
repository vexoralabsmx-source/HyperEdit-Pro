"""Audio mixing, DSP and loudness models for HyperEdit Pro."""

from typing import List, Optional
from pydantic import BaseModel, Field

from hyperedit.core.constants import LOUDNESS_TARGETS
from hyperedit.core.models.effects import Effect


class DuckingConfig(BaseModel):
    """Sidechain ducking configuration for background music / ambiance tracks."""

    trigger_track_id: str = Field(
        ...,
        description="Track ID whose presence attenuates this track (e.g. voiceover track)"
    )
    attenuation_db: float = Field(
        default=-12.0,
        le=0.0,
        ge=-48.0,
        description="Volume attenuation in decibels when trigger track is active"
    )
    attack_ms: float = Field(
        default=80.0,
        ge=5.0,
        le=2000.0,
        description="Time taken to lower volume once trigger starts (milliseconds)"
    )
    release_ms: float = Field(
        default=400.0,
        ge=10.0,
        le=5000.0,
        description="Time taken to restore volume after trigger ends (milliseconds)"
    )
    threshold_db: float = Field(
        default=-26.0,
        le=0.0,
        ge=-60.0,
        description="Trigger audio detection threshold in dBFS"
    )


class LoudnessTarget(BaseModel):
    """EBU R128 / ITU-R BS.1770 broadcast and streaming loudness target."""

    target_i: float = Field(
        default=LOUDNESS_TARGETS["ebu_r128"],
        description="Integrated Loudness Target in LUFS (e.g. -23 for EBU, -14 for YouTube)"
    )
    target_lra: float = Field(
        default=7.0,
        ge=1.0,
        le=50.0,
        description="Loudness Range target in LU"
    )
    target_tp: float = Field(
        default=-1.0,
        le=0.0,
        description="Maximum True Peak in dBFS (typically -1.0 or -1.5)"
    )


class AudioMixConfig(BaseModel):
    """Audio bus or track mixing configuration."""

    volume_db: float = Field(default=0.0, ge=-96.0, le=12.0, description="Track fader in dB")
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Stereo pan (-1.0 Left, 1.0 Right)")
    mute: bool = Field(default=False)
    solo: bool = Field(default=False)
    ducking: Optional[DuckingConfig] = Field(default=None)
    loudness_normalization: Optional[LoudnessTarget] = Field(default=None)
    effects: List[Effect] = Field(default_factory=list)

