"""Numerical keyframe interpolator supporting linear, bezier, spring, and overshoot easing."""

import math
from typing import Optional, Tuple

from hyperedit.core.models.transforms import (
    AnimatedProperty,
    InterpolationMode,
)


def evaluate_cubic_bezier(
    t: float,
    p1_x: float,
    p1_y: float,
    p2_x: float,
    p2_y: float,
) -> Tuple[float, float]:
    """Calculate 2D point along cubic bezier with P0=(0,0) and P3=(1,1)."""
    # B(t) = (1-t)^3 * P0 + 3(1-t)^2*t * P1 + 3(1-t)*t^2 * P2 + t^3 * P3
    inv_t = 1.0 - t
    c1 = 3.0 * inv_t * inv_t * t
    c2 = 3.0 * inv_t * t * t
    c3 = t * t * t

    x = c1 * p1_x + c2 * p2_x + c3
    y = c1 * p1_y + c2 * p2_y + c3
    return x, y


def solve_bezier_y_for_x(
    target_x: float,
    p1_x: float = 0.25,
    p1_y: float = 0.1,
    p2_x: float = 0.25,
    p2_y: float = 1.0,
) -> float:
    """Solve for bezier curve Y value at target X using Newton-Raphson root finding."""
    target_x = max(0.0, min(1.0, target_x))
    if target_x <= 0.0:
        return 0.0
    if target_x >= 1.0:
        return 1.0

    # Initial guess
    t = target_x
    for _ in range(8):
        x, y = evaluate_cubic_bezier(t, p1_x, p1_y, p2_x, p2_y)
        dx = x - target_x
        if abs(dx) < 1e-5:
            return y

        # Derivative dx/dt
        inv_t = 1.0 - t
        dxdt = (
            3.0 * inv_t * inv_t * p1_x
            + 6.0 * inv_t * t * (p2_x - p1_x)
            + 3.0 * t * t * (1.0 - p2_x)
        )
        if abs(dxdt) < 1e-6:
            break
        t = max(0.0, min(1.0, t - dx / dxdt))

    _, y = evaluate_cubic_bezier(t, p1_x, p1_y, p2_x, p2_y)
    return y


class KeyframeInterpolator:
    """Evaluates time-varying animated properties at continuous or discrete frames."""

    @classmethod
    def apply_easing(
        cls,
        progress: float,
        mode: InterpolationMode,
        bezier_handles: Optional[Tuple[float, float, float, float]] = None,
    ) -> float:
        """Apply mathematical easing curve to normalized progression alpha in [0, 1]."""
        alpha = max(0.0, min(1.0, progress))

        if mode == InterpolationMode.LINEAR:
            return alpha

        elif mode == InterpolationMode.EASE_IN:
            return alpha * alpha * alpha

        elif mode == InterpolationMode.EASE_OUT:
            inv = 1.0 - alpha
            return 1.0 - inv * inv * inv

        elif mode == InterpolationMode.EASE_IN_OUT:
            if alpha < 0.5:
                return 4.0 * alpha * alpha * alpha
            else:
                return 1.0 - ((-2.0 * alpha + 2.0) ** 3) / 2.0

        elif mode == InterpolationMode.SPRING:
            # Damped spring oscillator with gentle organic settle
            return 1.0 - math.exp(-6.0 * alpha) * math.cos(8.0 * alpha)

        elif mode == InterpolationMode.OVERSHOOT:
            # Back ease-out with slight 10% overshoot
            s = 1.70158
            a = alpha - 1.0
            return 1.0 + (s + 1.0) * (a ** 3) + s * (a ** 2)

        elif mode == InterpolationMode.BEZIER:
            handles = bezier_handles or (0.25, 0.1, 0.25, 1.0)
            return solve_bezier_y_for_x(alpha, *handles)

        elif mode == InterpolationMode.HOLD:
            return 0.0

        return alpha

    @classmethod
    def evaluate(cls, prop: AnimatedProperty, frame: int) -> float:
        """Evaluate the animated property at a given relative frame index."""
        if not prop.keyframes:
            return prop.base_value

        sorted_kfs = sorted(prop.keyframes, key=lambda k: k.frame)

        # Before first keyframe
        if frame <= sorted_kfs[0].frame:
            return sorted_kfs[0].value

        # After last keyframe
        if frame >= sorted_kfs[-1].frame:
            return sorted_kfs[-1].value

        # Locate interval
        for i in range(len(sorted_kfs) - 1):
            kf_start = sorted_kfs[i]
            kf_end = sorted_kfs[i + 1]

            if kf_start.frame <= frame < kf_end.frame:
                span = kf_end.frame - kf_start.frame
                if span <= 0:
                    return kf_start.value

                alpha = (frame - kf_start.frame) / span
                eased_alpha = cls.apply_easing(
                    alpha,
                    kf_start.interpolation,
                    kf_start.bezier_handles,
                )
                return kf_start.value + eased_alpha * (kf_end.value - kf_start.value)

        return sorted_kfs[-1].value

