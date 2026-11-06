"""Spatial transforms, keyframing and motion models for HyperEdit Pro."""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class InterpolationMode(str, Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BEZIER = "bezier"
    SPRING = "spring"
    OVERSHOOT = "overshoot"
    HOLD = "hold"


class Keyframe(BaseModel):
    """A value keyframe along a clip or effect timeline."""

    frame: int = Field(..., ge=0, description="Relative frame index from clip start")
    value: float = Field(..., description="Interpolated target value")
    interpolation: InterpolationMode = Field(default=InterpolationMode.LINEAR)
    bezier_handles: Optional[Tuple[float, float, float, float]] = Field(
        default=None,
        description="Cubic bezier control points (p1_x, p1_y, p2_x, p2_y)"
    )


class AnimatedProperty(BaseModel):
    """Dynamic property driven by keyframes."""

    property_name: str = Field(..., description="e.g. position_x, scale, opacity, volume")
    base_value: float = Field(default=0.0)
    keyframes: List[Keyframe] = Field(default_factory=list)


class Transform(BaseModel):
    """2D spatial transform and opacity configuration."""

    position_x: float = Field(default=0.0, description="Horizontal pixel offset from anchor")
    position_y: float = Field(default=0.0, description="Vertical pixel offset from anchor")
    scale_x: float = Field(default=1.0, ge=0.0, description="Horizontal scale multiplier")
    scale_y: float = Field(default=1.0, ge=0.0, description="Vertical scale multiplier")
    rotation_deg: float = Field(default=0.0, description="Clockwise rotation in degrees")
    anchor_x: float = Field(default=0.5, ge=0.0, le=1.0, description="Normalized anchor X (0.5 = center)")
    anchor_y: float = Field(default=0.5, ge=0.0, le=1.0, description="Normalized anchor Y (0.5 = center)")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, description="Opacity (0.0 to 1.0)")
    crop_top: float = Field(default=0.0, ge=0.0, le=1.0)
    crop_bottom: float = Field(default=0.0, ge=0.0, le=1.0)
    crop_left: float = Field(default=0.0, ge=0.0, le=1.0)
    crop_right: float = Field(default=0.0, ge=0.0, le=1.0)
    animated: List[AnimatedProperty] = Field(default_factory=list)

