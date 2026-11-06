"""HyperEdit Pro standard constants and defaults."""

from fractions import Fraction
from typing import Dict

# Standard frame rates mapped to exact rational fractions
STANDARD_FRAME_RATES: Dict[str, Fraction] = {
    "23.976": Fraction(24000, 1001),
    "23.98": Fraction(24000, 1001),
    "24": Fraction(24, 1),
    "25": Fraction(25, 1),
    "29.97": Fraction(30000, 1001),
    "30": Fraction(30, 1),
    "50": Fraction(50, 1),
    "59.94": Fraction(60000, 1001),
    "60": Fraction(60, 1),
}

# Standard audiovisual resolutions
STANDARD_RESOLUTIONS: Dict[str, tuple[int, int]] = {
    "1080p_horizontal": (1920, 1080),
    "1080p_vertical": (1080, 1920),
    "4k_horizontal": (3840, 2160),
    "4k_vertical": (2160, 3840),
    "square_1080": (1080, 1080),
    "cinema_4k": (4096, 2160),
    "720p_horizontal": (1280, 720),
}

# Standard Audio sample rates
STANDARD_SAMPLE_RATES = (44100, 48000, 96000)

# EBU R128 and broadcast loudness targets (in LUFS / LKFS)
LOUDNESS_TARGETS = {
    "ebu_r128": -23.0,
    "atsc_a85": -24.0,
    "youtube": -14.0,
    "spotify": -14.0,
    "apple_music": -16.0,
    "podcast_standard": -16.0,
}

# Project format specification version
HYPEREDIT_PROJECT_SCHEMA_VERSION = "2.0.0"

