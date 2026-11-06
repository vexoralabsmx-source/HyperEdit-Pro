"""Domain models, histogram telemetry and shot matching schemas for Color Engine."""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from hyperedit.core.models.color import (
    ASC_CDL,
    ColorCurves,
    ColorGradeConfig,
    ColorMetadata,
    ColorRange,
    ColorStandard,
    CurvePoint,
    LiftGammaGain,
    LUTInterpolation,
)


class HistogramMetrics(BaseModel):
    """Luminance and chromatic signal metrics for quality audit and shot matching."""

    mean_luma: float = Field(..., ge=0.0, le=255.0, description="Average frame luminance (IRE/8-bit)")
    std_luma: float = Field(..., ge=0.0, description="Luminance standard deviation (contrast indicator)")
    min_luma: float = Field(..., ge=0.0, le=255.0, description="Minimum black point value")
    max_luma: float = Field(..., ge=0.0, le=255.0, description="Maximum white point value")
    mean_rgb: Tuple[float, float, float] = Field(..., description="Average R, G, B channel levels (0..255)")
    shadow_clipping_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of crushed black pixels (<16)")
    highlight_clipping_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of blown white pixels (>240)")
    dynamic_range_stops: float = Field(default=0.0, ge=0.0, description="Approximate dynamic range in stops")


class ShotMatchTelemetry(BaseModel):
    """Telemetry report comparing source and reference shot before and after matching."""

    reference_clip: str
    target_clip: str
    source_metrics: HistogramMetrics
    reference_metrics: HistogramMetrics
    applied_grade: ColorGradeConfig
    residual_luma_error: float = Field(default=0.0, description="Absolute difference in mean luma after matching")
    residual_color_error: float = Field(default=0.0, description="Color delta E / distance after matching")


class ColorAuditReport(BaseModel):
    """Color management audit detecting SDR/HDR, gamuts and broadcast legality."""

    file_path: str
    metadata: ColorMetadata
    is_sdr_rec709_compliant: bool
    is_hdr: bool
    has_broadcast_clipping: bool
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

