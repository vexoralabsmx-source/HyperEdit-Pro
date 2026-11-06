"""Audio processing, mixing, sidechain ducking, beat tracking and loudness engine."""

from hyperedit.audio.beat_sync import BeatSynchronizer
from hyperedit.audio.beat_tracker import BeatTracker
from hyperedit.audio.mixer import AudioMixer
from hyperedit.audio.models import (
    STANDARD_LOUDNESS_PROFILES,
    BeatAlignmentReport,
    BeatInfo,
    CutShiftDetail,
    LoudnessMeasurement,
    LoudnessProfile,
    TargetPlatform,
)
from hyperedit.core.models.audio import AudioMixConfig, DuckingConfig, LoudnessTarget
from hyperedit.core.protocols import AudioMixerProtocol

__all__ = [
    "AudioMixConfig",
    "DuckingConfig",
    "LoudnessTarget",
    "AudioMixerProtocol",
    "BeatTracker",
    "BeatSynchronizer",
    "AudioMixer",
    "BeatInfo",
    "BeatAlignmentReport",
    "CutShiftDetail",
    "LoudnessMeasurement",
    "LoudnessProfile",
    "TargetPlatform",
    "STANDARD_LOUDNESS_PROFILES",
]
