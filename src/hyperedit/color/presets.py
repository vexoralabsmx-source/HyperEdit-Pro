"""Curated, non-generic cinematographic color grading presets for HyperEdit Pro."""

from typing import Dict
from hyperedit.core.models.color import (
    ASC_CDL,
    ColorCurves,
    ColorGradeConfig,
    CurvePoint,
    LiftGammaGain,
)


COLOR_PRESETS: Dict[str, ColorGradeConfig] = {
    "cinematic_neutral": ColorGradeConfig(
        preset_name="cinematic_neutral",
        exposure_ev=0.0,
        contrast=1.08,
        saturation=0.96,
        temperature=2.0,
        tint=-1.0,
        black_point=0.01,
        white_point=0.98,
        lift_gamma_gain=LiftGammaGain(
            lift=(-0.01, -0.005, 0.0),
            gamma=(1.02, 1.0, 0.98),
            gain=(1.0, 1.0, 1.0),
        ),
        curves=ColorCurves(
            master=[
                CurvePoint(x=0.0, y=0.0),
                CurvePoint(x=0.25, y=0.22),
                CurvePoint(x=0.75, y=0.78),
                CurvePoint(x=1.0, y=0.98),
            ]
        ),
    ),
    "warm_editorial": ColorGradeConfig(
        preset_name="warm_editorial",
        exposure_ev=0.1,
        contrast=1.04,
        saturation=1.05,
        temperature=18.0,
        tint=2.0,
        black_point=0.02,
        white_point=0.99,
        lift_gamma_gain=LiftGammaGain(
            lift=(0.02, 0.01, -0.01),
            gamma=(1.05, 1.02, 0.95),
            gain=(1.04, 1.01, 0.96),
        ),
    ),
    "cool_scandi": ColorGradeConfig(
        preset_name="cool_scandi",
        exposure_ev=0.0,
        contrast=1.12,
        saturation=0.88,
        temperature=-16.0,
        tint=-4.0,
        black_point=0.0,
        white_point=0.97,
        lift_gamma_gain=LiftGammaGain(
            lift=(-0.02, 0.0, 0.02),
            gamma=(0.96, 0.99, 1.03),
            gain=(0.98, 1.0, 1.02),
        ),
    ),
    "film_stock_5207": ColorGradeConfig(
        preset_name="film_stock_5207",
        exposure_ev=0.05,
        contrast=1.10,
        saturation=1.02,
        temperature=8.0,
        tint=-2.0,
        black_point=0.025,
        white_point=0.96,
        cdl=ASC_CDL(
            slope=(1.03, 1.01, 0.97),
            offset=(0.02, 0.015, -0.01),
            power=(0.98, 1.0, 1.02),
            saturation=1.02,
        ),
        lift_gamma_gain=LiftGammaGain(
            lift=(0.01, 0.02, -0.02),
            gamma=(1.04, 1.01, 0.96),
            gain=(1.02, 1.0, 0.98),
        ),
    ),
    "monochrome_panchro": ColorGradeConfig(
        preset_name="monochrome_panchro",
        exposure_ev=0.0,
        contrast=1.28,
        saturation=0.0,
        temperature=0.0,
        tint=0.0,
        black_point=-0.02,
        white_point=1.0,
        curves=ColorCurves(
            master=[
                CurvePoint(x=0.0, y=0.0),
                CurvePoint(x=0.2, y=0.14),
                CurvePoint(x=0.8, y=0.86),
                CurvePoint(x=1.0, y=1.0),
            ]
        ),
    ),
    "bleach_bypass": ColorGradeConfig(
        preset_name="bleach_bypass",
        exposure_ev=0.0,
        contrast=1.40,
        saturation=0.55,
        temperature=-5.0,
        tint=1.0,
        black_point=-0.01,
        white_point=1.0,
        lift_gamma_gain=LiftGammaGain(
            lift=(-0.03, -0.03, -0.03),
            gamma=(0.92, 0.92, 0.92),
            gain=(1.10, 1.10, 1.10),
        ),
    ),
}


def blend_color_grades(base: ColorGradeConfig, target: ColorGradeConfig, factor: float) -> ColorGradeConfig:
    """Linearly interpolate between a base color grade and a target preset grade by factor (0.0 to 1.0)."""
    f = max(0.0, min(1.0, float(factor)))
    if f <= 0.0:
        return base.model_copy()
    if f >= 1.0:
        return target.model_copy()

    exp = base.exposure_ev + f * (target.exposure_ev - base.exposure_ev)
    contrast = base.contrast + f * (target.contrast - base.contrast)
    sat = base.saturation + f * (target.saturation - base.saturation)
    vib = base.vibrance + f * (target.vibrance - base.vibrance)
    temp = base.temperature + f * (target.temperature - base.temperature)
    tint = base.tint + f * (target.tint - base.tint)
    black = base.black_point + f * (target.black_point - base.black_point)
    white = base.white_point + f * (target.white_point - base.white_point)

    return ColorGradeConfig(
        enabled=True,
        preset_name=target.preset_name,
        preset_strength=f,
        exposure_ev=round(exp, 3),
        contrast=round(contrast, 3),
        saturation=round(sat, 3),
        vibrance=round(vib, 3),
        temperature=round(temp, 2),
        tint=round(tint, 2),
        black_point=round(black, 3),
        white_point=round(white, 3),
        lift_gamma_gain=target.lift_gamma_gain if f > 0.5 else base.lift_gamma_gain,
        cdl=target.cdl if f > 0.5 else base.cdl,
        curves=target.curves if f > 0.5 else base.curves,
        lut_path=target.lut_path if f > 0.5 else base.lut_path,
        lut_interpolation=target.lut_interpolation,
    )

