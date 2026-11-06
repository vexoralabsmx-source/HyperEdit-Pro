"""Color grading, ASC-CDL and 3D LUT models for HyperEdit Pro."""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class LUTInterpolation(str, Enum):
    NEAREST = "nearest"
    TRILINEAR = "trilinear"
    TETRAHEDRAL = "tetrahedral"


class ColorStandard(str, Enum):
    """Standard color gamuts and dynamic range classifications."""
    REC709 = "rec709"                # Standard SDR broadcast and web
    REC2020_HDR_PQ = "rec2020_pq"   # HDR10 / Dolby Vision (SMPTE ST 2084)
    REC2020_HDR_HLG = "rec2020_hlg" # Hybrid Log-Gamma broadcast HDR
    SRGB = "srgb"                    # Standard computer display sRGB
    DCI_P3 = "dci_p3"                # Digital Cinema Initiatives P3
    UNKNOWN = "unknown"


class ColorRange(str, Enum):
    """Luminance quantization range."""
    LIMITED_TV = "tv"  # Broadcast 16-235 (8-bit) or 64-940 (10-bit)
    FULL_PC = "pc"     # Full data range 0-255 (8-bit) or 0-1023 (10-bit)
    UNKNOWN = "unknown"


class ColorMetadata(BaseModel):
    """Probed color space, primaries, transfer function, and dynamic range."""
    color_space: str = Field(default="bt709")
    color_primaries: str = Field(default="bt709")
    color_transfer: str = Field(default="bt709")
    color_range: ColorRange = Field(default=ColorRange.LIMITED_TV)
    standard: ColorStandard = Field(default=ColorStandard.REC709)
    is_hdr: bool = Field(default=False, description="True if transfer characteristic is PQ or HLG")
    bit_depth: int = Field(default=8, ge=8, le=16)


class CurvePoint(BaseModel):
    """2D control point on a tonal curve (normalized 0.0 to 1.0)."""
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class ColorCurves(BaseModel):
    """Per-channel and master luminance tonal transfer curves."""
    master: List[CurvePoint] = Field(default_factory=list)
    red: List[CurvePoint] = Field(default_factory=list)
    green: List[CurvePoint] = Field(default_factory=list)
    blue: List[CurvePoint] = Field(default_factory=list)


class ASC_CDL(BaseModel):
    """ASC Color Decision List (Slope, Offset, Power, Saturation)."""

    slope: Tuple[float, float, float] = Field(default=(1.0, 1.0, 1.0), description="RGB slope (multiplication)")
    offset: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="RGB offset (addition)")
    power: Tuple[float, float, float] = Field(default=(1.0, 1.0, 1.0), description="RGB power (gamma exponent)")
    saturation: float = Field(default=1.0, ge=0.0, le=4.0, description="Color saturation multiplier")


class LiftGammaGain(BaseModel):
    """Three-way color wheel adjustments."""

    lift: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="Shadows (RGB)")
    gamma: Tuple[float, float, float] = Field(default=(1.0, 1.0, 1.0), description="Midtones (RGB)")
    gain: Tuple[float, float, float] = Field(default=(1.0, 1.0, 1.0), description="Highlights (RGB)")


class ColorGradeConfig(BaseModel):
    """Color grading pipeline configuration applied via FFmpeg eq / curves / lut3d."""

    enabled: bool = Field(default=True, description="Enable or bypass this color grade")
    preset_name: Optional[str] = Field(default=None, description="Curated look preset name")
    preset_strength: float = Field(default=1.0, ge=0.0, le=1.0, description="Blend strength for preset look")
    exposure_ev: float = Field(default=0.0, ge=-5.0, le=5.0, description="Exposure bias in EV stops")
    contrast: float = Field(default=1.0, ge=0.0, le=3.0, description="Contrast multiplier (1.0 = neutral)")
    saturation: float = Field(default=1.0, ge=0.0, le=3.0, description="Saturation multiplier (1.0 = neutral)")
    vibrance: float = Field(default=0.0, ge=-1.0, le=1.0, description="Selective vibrance adjustment")
    temperature: float = Field(default=0.0, ge=-100.0, le=100.0, description="Color temp shift: blue (-) to orange (+)")
    tint: float = Field(default=0.0, ge=-100.0, le=100.0, description="Tint shift: green (-) to magenta (+)")
    black_point: float = Field(default=0.0, ge=-0.2, le=0.2, description="Black level offset (lift/crush)")
    white_point: float = Field(default=1.0, ge=0.8, le=1.2, description="White level clip/ceiling")
    cdl: Optional[ASC_CDL] = Field(default=None)
    lift_gamma_gain: Optional[LiftGammaGain] = Field(default=None)
    curves: Optional[ColorCurves] = Field(default=None)
    lut_path: Optional[str] = Field(default=None, description="Path to .cube or .3dl 3D LUT")
    lut_interpolation: LUTInterpolation = Field(default=LUTInterpolation.TETRAHEDRAL)

