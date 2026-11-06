"""AV effect and filter models for HyperEdit Pro."""

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from hyperedit.core.models.transforms import Keyframe


class EffectKind(str, Enum):
    # Video filters
    COLOR_GRADE = "color_grade"
    LUT3D = "lut3d"
    GAUSSIAN_BLUR = "gaussian_blur"
    BOX_BLUR = "box_blur"
    SHARPEN = "sharpen"
    CHROMA_KEY = "chroma_key"
    DENOISE = "denoise"
    VIGNETTE = "vignette"
    FILM_GRAIN = "film_grain"
    CAMERA_SHAKE = "camera_shake"
    BLOOM_GLOW = "bloom_glow"
    MOTION_BLUR = "motion_blur"
    DEPTH_PARALLAX = "depth_parallax"
    MASK = "mask"
    STABILIZATION = "stabilization"
    CUSTOM_VIDEO_FILTER = "custom_video_filter"

    # Audio filters
    PARAMETRIC_EQ = "parametric_eq"
    COMPRESSOR = "compressor"
    LIMITER = "limiter"
    NOISE_GATE = "noise_gate"
    LOUDNORM = "loudnorm"
    REVERB = "reverb"
    CUSTOM_AUDIO_FILTER = "custom_audio_filter"


class Effect(BaseModel):
    """Filter or DSP effect applied to a clip, track, or master output."""

    effect_id: str = Field(..., description="Unique effect identifier")
    kind: EffectKind = Field(..., description="Category of filter / effect")
    enabled: bool = Field(default=True)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Filter-specific arguments")
    keyframes: List[Keyframe] = Field(default_factory=list, description="Optional parameter keyframing")

