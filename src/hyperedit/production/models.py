"""Data models and schemas for HyperEdit Pro Fast Production Mode."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProductionMode(str, Enum):
    """Execution mode determining speed, depth of verification, and resource allocation."""

    FAST = "fast"
    BALANCED = "balanced"
    CINEMATIC = "cinematic"


class ProductionStage(str, Enum):
    """Pipeline progression stages for recovery and checkpoints."""

    INIT = "init"
    ASSETS_PROBED = "assets_probed"
    AUDIO_ANALYZED = "audio_analyzed"
    MOTION_COMPOSED = "motion_composed"
    TIMELINE_ASSEMBLED = "timeline_assembled"
    PREVIEW_VERIFIED = "preview_verified"
    MASTER_RENDERED = "master_rendered"
    COMPLETED = "completed"


class SceneCut(BaseModel):
    """A single discrete edit cut on the production timeline."""

    clip_id: str
    source_asset: str
    in_seconds: Optional[float] = None
    out_seconds: Optional[float] = None
    speed: float = Field(default=1.0, gt=0.0)
    reverse: bool = False
    transition: Optional[str] = None  # e.g. "crossfade", "dip_black", "wipe_left"
    transition_duration_sec: float = Field(default=0.5, ge=0.0)
    color_preset: Optional[str] = None  # e.g. "warm_editorial", "cinematic_neutral"
    track: str = "V1"


class AudioDesign(BaseModel):
    """Audio configuration for background music, dialogue ducking, and master loudness."""

    music_file: Optional[str] = None
    dialogue_file: Optional[str] = None
    sfx_files: List[str] = Field(default_factory=list)
    ducking: bool = True
    ducking_threshold_db: float = -20.0
    ducking_attenuation_db: float = -14.0
    target_lufs: float = -14.0
    beat_sync: bool = False
    beat_sync_max_shift_frames: int = 8


class MotionGraphicOverlay(BaseModel):
    """Motion graphic overlay configuration (HyperFrames integration)."""

    template: str = "cinematic_intro"  # cinematic_intro, product_showcase, audio_reactive
    title: str
    subtitle: Optional[str] = None
    preset: str = "cinematic_luxury"
    start_seconds: float = 0.0
    duration_seconds: float = 3.0
    track: str = "GRAPHIC"
    sync_beats: bool = False


class CaptionConfig(BaseModel):
    """Captions and kinetic typography configuration."""

    source_file: Optional[str] = None
    burn_in: bool = False
    style_preset: str = "modern_bold"
    kinetic_mode: Optional[str] = None  # karaoke_highlight, pop_scale
    auto_transcribe: bool = False


class VFXConfig(BaseModel):
    """Visual effects and camera stabilization."""

    stabilize_assets: List[str] = Field(default_factory=list)
    film_grain: float = Field(default=0.0, ge=0.0, le=1.0)
    color_grade_master: Optional[str] = None


class ProductionPlan(BaseModel):
    """Declarative, structured post-production plan generated once by an AI Agent."""

    title: str = "HyperEdit Fast Production"
    mode: ProductionMode = ProductionMode.FAST
    preset: str = "1080p"  # 1080p, vertical_1080p, square, 4k
    width: Optional[int] = None
    height: Optional[int] = None
    fps: float = Field(default=30.0, gt=0.0)
    assets: List[str] = Field(default_factory=list)
    cuts: List[SceneCut] = Field(default_factory=list)
    audio: AudioDesign = Field(default_factory=AudioDesign)
    motion_graphics: List[MotionGraphicOverlay] = Field(default_factory=list)
    captions: CaptionConfig = Field(default_factory=CaptionConfig)
    vfx: VFXConfig = Field(default_factory=VFXConfig)
    output_path: str = "output/master.mp4"
    preview_path: Optional[str] = None
    cache_dir: str = ".hyperedit_cache"

    def get_dimensions(self) -> tuple[int, int]:
        """Resolve master width and height based on preset or explicit dimensions."""
        if self.width and self.height:
            return self.width, self.height
        preset_clean = self.preset.lower()
        if "vertical" in preset_clean or "9:16" in preset_clean:
            return 1080, 1920
        elif "square" in preset_clean or "1:1" in preset_clean:
            return 1080, 1080
        elif "4k" in preset_clean:
            return 3840, 2160
        else:
            return 1920, 1080

    def compute_plan_hash(self) -> str:
        """Compute deterministic hash of the plan structure for caching and checkpoints."""
        import hashlib
        import json

        data = self.model_dump(exclude={"preview_path", "cache_dir"})
        raw = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    @classmethod
    def load_from_file(cls, path: Path | str) -> "ProductionPlan":
        """Load plan from JSON file."""
        import json

        content = Path(path).read_text(encoding="utf-8")
        return cls.model_validate(json.loads(content))

    def save_to_file(self, path: Path | str) -> Path:
        """Save plan to JSON file."""
        out = Path(path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return out


class ProductionMetrics(BaseModel):
    """Telemetry and performance metrics recorded during production."""

    total_elapsed_seconds: float = 0.0
    analysis_seconds: float = 0.0
    render_seconds: float = 0.0
    operations_total: int = 0
    operations_cached: int = 0
    cache_hit_ratio: float = 0.0
    re_renders_avoided: int = 0
    peak_memory_mb: float = 0.0
    cpu_seconds: float = 0.0
    remediation_attempts: int = 0


class ProductionResult(BaseModel):
    """Outcome and summary of a production pipeline run."""

    success: bool
    mode: ProductionMode
    output_file: str
    preview_file: Optional[str] = None
    metrics: ProductionMetrics = Field(default_factory=ProductionMetrics)
    compact_summary: str = ""
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

