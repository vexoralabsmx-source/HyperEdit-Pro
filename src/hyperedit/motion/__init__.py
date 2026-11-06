"""Spatial motion, keyframing, virtual camera, and motion graphics presets."""

from hyperedit.core.models.transforms import (
    AnimatedProperty,
    InterpolationMode,
    Keyframe,
    Transform,
)
from hyperedit.core.protocols import MotionEngineProtocol
from hyperedit.motion.engine import MotionEngine
from hyperedit.motion.interpolator import (
    KeyframeInterpolator,
    evaluate_cubic_bezier,
    solve_bezier_y_for_x,
)
from hyperedit.motion.presets import (
    STANDARD_MOTION_PRESETS,
    MotionPreset,
)

__all__ = [
    "Transform",
    "Keyframe",
    "InterpolationMode",
    "AnimatedProperty",
    "MotionEngineProtocol",
    "MotionEngine",
    "KeyframeInterpolator",
    "evaluate_cubic_bezier",
    "solve_bezier_y_for_x",
    "MotionPreset",
    "STANDARD_MOTION_PRESETS",
]
