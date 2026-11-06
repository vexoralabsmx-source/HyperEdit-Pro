"""Domain models and data schemas for HyperEdit Pro VFX, Tracking & Compositing."""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class TrackingMethod(str, Enum):
    """Computer vision tracking algorithm."""
    POINT_LK = "point_lk"               # Lucas-Kanade sparse optical flow
    REGION_TEMPLATE = "region_template" # Normalized cross-correlation template matching
    REGION_MIL = "region_mil"           # Multiple Instance Learning bounding box tracker


class PointTrack(BaseModel):
    """Tracked 2D coordinate for a single frame."""
    frame_index: int = Field(..., ge=0)
    time_seconds: float = Field(..., ge=0.0)
    x: float = Field(..., description="Horizontal pixel coordinate")
    y: float = Field(..., description="Vertical pixel coordinate")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Tracking confidence metric (0.0 to 1.0)")
    lost: bool = Field(default=False, description="True if tracking failed or confidence fell below threshold")


class RegionTrack(BaseModel):
    """Tracked bounding box and affine transform for a single frame."""
    frame_index: int = Field(..., ge=0)
    time_seconds: float = Field(..., ge=0.0)
    x: float = Field(..., description="Top-left horizontal pixel coordinate")
    y: float = Field(..., description="Top-left vertical pixel coordinate")
    width: float = Field(..., gt=0.0, description="Bounding box width in pixels")
    height: float = Field(..., gt=0.0, description="Bounding box height in pixels")
    center_x: float = Field(..., description="Bounding box center X")
    center_y: float = Field(..., description="Bounding box center Y")
    rotation_deg: float = Field(default=0.0, description="Evaluated rotation in degrees")
    scale: float = Field(default=1.0, gt=0.0, description="Evaluated uniform scale factor")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Matching confidence score (0.0 to 1.0)")
    lost: bool = Field(default=False, description="True if tracker lost the target")


class TrackingTelemetry(BaseModel):
    """Complete tracking telemetry for an audiovisual shot."""
    method: TrackingMethod
    video_path: str
    total_frames: int = Field(..., ge=1)
    tracked_frames: int = Field(..., ge=0)
    lost_frames: int = Field(..., ge=0)
    mean_confidence: float = Field(..., ge=0.0, le=1.0)
    tracks: List[RegionTrack] = Field(default_factory=list)
    initial_bbox: Tuple[float, float, float, float] = Field(..., description="(x, y, width, height)")


class StabilizationTelemetry(BaseModel):
    """Telemetry and metrics for video stabilization."""
    total_frames: int = Field(..., ge=1)
    max_displacement_px: float = Field(..., ge=0.0, description="Maximum camera shake displacement in pixels")
    mean_displacement_px: float = Field(..., ge=0.0)
    crop_margin_pct: float = Field(default=0.05, ge=0.0, le=0.3, description="Recommended safe crop percentage to avoid border artifacts")
    smoothed_trajectory: List[Tuple[float, float, float]] = Field(default_factory=list, description="Smoothed (dx, dy, da) compensation offsets")


class MaskShape(str, Enum):
    """Geometric mask primitive."""
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    POLYGON = "polygon"
    BEZIER_SPLINE = "bezier_spline"
    ALPHA_MATTE = "alpha_matte"


class MaskKeyframe(BaseModel):
    """Temporal keyframe for an animated mask."""
    frame_index: int = Field(..., ge=0)
    center_x: float = Field(..., description="Center horizontal coordinate in pixels")
    center_y: float = Field(..., description="Center vertical coordinate in pixels")
    width: float = Field(..., gt=0.0, description="Mask width in pixels")
    height: float = Field(..., gt=0.0, description="Mask height in pixels")
    rotation_deg: float = Field(default=0.0, description="Mask rotation in degrees")
    points: Optional[List[Tuple[float, float]]] = Field(default=None, description="Optional polygon vertex coordinates")
    feather_px: float = Field(default=0.0, ge=0.0, description="Edge blur radius in pixels")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, description="Mask opacity density")


class MaskDefinition(BaseModel):
    """Non-destructive mask applied to a clip or composite layer."""
    mask_id: str = Field(..., description="Unique mask identifier")
    shape: MaskShape = Field(default=MaskShape.ELLIPSE)
    inverted: bool = Field(default=False, description="True to invert mask (cut out inside)")
    feather_px: float = Field(default=0.0, ge=0.0, description="Edge softness / blur in pixels")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    keyframes: List[MaskKeyframe] = Field(default_factory=list, description="Optional animated mask keyframes")


class BlendMode(str, Enum):
    """Layer blend mode for compositing."""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    ADD = "add"
    SOFT_LIGHT = "soft_light"
    DARKEN = "darken"
    LIGHTEN = "lighten"


class ChromaKeyConfig(BaseModel):
    """Color difference / green screen keying parameters."""
    key_color_rgb: Tuple[int, int, int] = Field(default=(0, 255, 0), description="Target key color (R, G, B)")
    similarity: float = Field(default=0.3, ge=0.01, le=1.0, description="Color distance tolerance threshold")
    smoothness: float = Field(default=0.1, ge=0.0, le=1.0, description="Edge transition ramp softness")
    spill_reduction: float = Field(default=0.5, ge=0.0, le=1.0, description="Desaturate green/blue reflections on subject")


class CameraShakeConfig(BaseModel):
    """Deterministic camera shake simulation."""
    enabled: bool = Field(default=True)
    intensity_px: float = Field(default=8.0, ge=0.0, description="Maximum pixel displacement")
    frequency_hz: float = Field(default=3.5, gt=0.0, description="Oscillation frequency in Hz")
    rotation_deg: float = Field(default=0.4, ge=0.0, description="Maximum camera tilt in degrees")
    seed: int = Field(default=42, description="Deterministic pseudo-random seed")


class FilmGrainConfig(BaseModel):
    """Photochemical film grain synthesis."""
    enabled: bool = Field(default=True)
    intensity: float = Field(default=0.15, ge=0.0, le=1.0, description="Grain visibility (0.0 to 1.0)")
    size: str = Field(default="medium", description="fine, medium, coarse")
    chromatic: bool = Field(default=False, description="Monochrome vs chromatic noise")


class BloomGlowConfig(BaseModel):
    """Cinematic highlight diffusion and glow."""
    enabled: bool = Field(default=True)
    threshold: float = Field(default=0.72, ge=0.0, le=1.0, description="Luminance cutoff threshold (0.0 to 1.0)")
    radius_px: int = Field(default=18, ge=1, le=100, description="Gaussian blur radius in pixels")
    intensity: float = Field(default=0.8, ge=0.0, le=3.0, description="Additive glow blend multiplier")


class MotionBlurConfig(BaseModel):
    """Temporal motion blur accumulation."""
    enabled: bool = Field(default=True)
    shutter_angle_deg: float = Field(default=180.0, ge=0.0, le=360.0, description="Simulated rotary camera shutter angle")
    samples: int = Field(default=4, ge=2, le=16, description="Temporal frame blending samples")


class DepthParallaxLayer(BaseModel):
    """Layer depth specification for multi-plane parallax movement."""
    layer_id: str
    z_depth: float = Field(default=1.0, gt=0.0, description="Virtual distance (0.5=background slow, 1.0=midground, 2.0=foreground fast)")
    horizontal_offset_px: float = Field(default=0.0)
    vertical_offset_px: float = Field(default=0.0)


class BlenderRenderEngine(str, Enum):
    """Blender rendering engine."""
    CYCLES = "CYCLES"
    EEVEE = "BLENDER_EEVEE_NEXT"
    EEVEE_LEGACY = "BLENDER_EEVEE"


class BlenderRenderConfig(BaseModel):
    """Specification for headless Blender 3D rendering."""
    scene_file: str = Field(..., description="Path to .blend file")
    output_pattern: str = Field(..., description="Destination output pattern (e.g. renders/frame_####.png)")
    start_frame: int = Field(default=1, ge=0)
    end_frame: int = Field(default=30, ge=0)
    engine: BlenderRenderEngine = Field(default=BlenderRenderEngine.CYCLES)
    samples: int = Field(default=64, ge=1)
    transparent_background: bool = Field(default=True, description="Render with RGBA alpha channel")
    script_file: Optional[str] = Field(default=None, description="Optional Python automation script to execute in Blender")
    width: Optional[int] = Field(default=None, gt=0)
    height: Optional[int] = Field(default=None, gt=0)
    fps: Optional[float] = Field(default=None, gt=0.0)


class BlenderRenderResult(BaseModel):
    """Result payload from Blender rendering execution."""
    success: bool
    output_files: List[str] = Field(default_factory=list)
    total_frames: int = Field(default=0)
    render_time_seconds: float = Field(default=0.0)
    is_transparent: bool = Field(default=True)
    diagnostics: Optional[str] = Field(default=None)

