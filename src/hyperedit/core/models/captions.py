"""Captions and subtitle domain models and presets for HyperEdit Pro."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class SubtitleFormat(str, Enum):
    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"


class SubtitleAlignment(str, Enum):
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP_CENTER = "top_center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    MIDDLE_CENTER = "middle_center"


class KineticAnimationMode(str, Enum):
    NONE = "none"                            # Classic static subtitles
    KARAOKE_HIGHLIGHT = "karaoke_highlight"  # Active word switches to accent color
    POP_SCALE = "pop_scale"                  # Active word scales up slightly with emphasis
    WORD_REVEAL = "word_reveal"              # Words appear sequentially as spoken
    FADE_WORD = "fade_word"                  # Smooth fade-in for each word/phrase
    SLIDE_UP = "slide_up"                    # Slide up transition from lower boundary


class WordTimestamp(BaseModel):
    """Word-level alignment timestamp."""

    word: str = Field(..., description="The spoken word text")
    start_ms: int = Field(..., ge=0, description="Start offset in milliseconds")
    end_ms: int = Field(..., ge=0, description="End offset in milliseconds")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_duration(self) -> "WordTimestamp":
        if self.end_ms < self.start_ms:
            raise ValueError(f"Word end_ms ({self.end_ms}) cannot be before start_ms ({self.start_ms})")
        return self

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class SubtitleStyle(BaseModel):
    """ASS / libass compatible typographic subtitle styling."""

    font_name: str = Field(default="Arial", description="System font family name")
    font_size: int = Field(default=38, ge=8, le=180)
    primary_color_hex: str = Field(default="#FFFFFF", description="Base font color (hex, e.g. #FFFFFF)")
    highlight_color_hex: str = Field(default="#FFE600", description="Active word accent color in kinetic modes")
    outline_color_hex: str = Field(default="#000000", description="Outline stroke color")
    outline_width: float = Field(default=2.5, ge=0.0, le=15.0)
    shadow_color_hex: str = Field(default="#000000", description="Drop shadow color")
    shadow_offset: float = Field(default=1.5, ge=0.0, le=15.0)
    background_box: bool = Field(default=False, description="Render semi-transparent rectangular background box")
    background_box_color_hex: str = Field(default="#80000000", description="Background box color with alpha")
    bold: bool = Field(default=True)
    italic: bool = Field(default=False)
    all_caps: bool = Field(default=False, description="Convert all text to uppercase")
    letter_spacing: float = Field(default=0.0, description="Font tracking / character spacing in points")
    alignment: SubtitleAlignment = Field(default=SubtitleAlignment.BOTTOM_CENTER)
    margin_v: int = Field(default=60, ge=0, description="Vertical margin from boundary in pixels")
    margin_h: int = Field(default=50, ge=0, description="Horizontal margin from side boundary in pixels")
    animation_mode: KineticAnimationMode = Field(default=KineticAnimationMode.NONE)
    max_chars_per_line: int = Field(default=38, ge=10, le=80, description="Recommended maximum characters per line")
    max_lines_per_cue: int = Field(default=2, ge=1, le=4)


class SubtitleCue(BaseModel):
    """A timed subtitle segment with optional word-level kinetic alignment."""

    cue_id: str = Field(..., description="Unique cue identifier")
    start_ms: int = Field(..., ge=0, description="Start offset in milliseconds")
    end_ms: int = Field(..., gt=0, description="End offset in milliseconds")
    text: str = Field(..., description="Caption text content")
    speaker: Optional[str] = Field(default=None, description="Speaker name or label")
    words: List[WordTimestamp] = Field(default_factory=list, description="Word timestamps if available")
    style_override: Optional[SubtitleStyle] = Field(default=None)

    @model_validator(mode="after")
    def validate_cue_timing(self) -> "SubtitleCue":
        if self.end_ms <= self.start_ms:
            raise ValueError(f"Cue end_ms ({self.end_ms}) must be strictly greater than start_ms ({self.start_ms})")
        return self

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0

    @property
    def characters_per_second(self) -> float:
        clean_text = self.text.strip()
        dur = self.duration_seconds
        return len(clean_text) / dur if dur > 0 else 0.0


class SubtitleTrack(BaseModel):
    """Subtitle track containing timed cues, language metadata, and styling."""

    track_id: str = Field(default="SUB1", description="Unique track identifier")
    name: str = Field(default="Subtitles")
    language: str = Field(default="eng", description="ISO 639-2 language code (e.g. eng, spa, fra)")
    burn_in: bool = Field(default=True, description="Whether to render burned-in into video or export sidecar")
    default_style: SubtitleStyle = Field(default_factory=SubtitleStyle)
    cues: List[SubtitleCue] = Field(default_factory=list)

    def sort_cues(self) -> None:
        self.cues.sort(key=lambda c: c.start_ms)


class ReadabilityIssue(BaseModel):
    """Diagnostic telemetry on subtitle pacing and line layout."""

    cue_id: str
    issue_type: str
    message: str
    severity: str


# --- Built-in Professional Styling Presets ---

STANDARD_CAPTION_PRESETS: Dict[str, SubtitleStyle] = {
    "netflix": SubtitleStyle(
        font_name="Arial",
        font_size=36,
        primary_color_hex="#FFFFFF",
        outline_color_hex="#000000",
        outline_width=2.0,
        shadow_color_hex="#000000",
        shadow_offset=1.5,
        bold=False,
        italic=False,
        alignment=SubtitleAlignment.BOTTOM_CENTER,
        margin_v=50,
        margin_h=60,
        animation_mode=KineticAnimationMode.NONE,
        max_chars_per_line=38,
    ),
    "modern_bold": SubtitleStyle(
        font_name="Arial",
        font_size=42,
        primary_color_hex="#FFFFFF",
        highlight_color_hex="#FFE600",
        outline_color_hex="#000000",
        outline_width=3.0,
        shadow_color_hex="#000000",
        shadow_offset=2.0,
        bold=True,
        alignment=SubtitleAlignment.BOTTOM_CENTER,
        margin_v=70,
        margin_h=50,
        animation_mode=KineticAnimationMode.KARAOKE_HIGHLIGHT,
        max_chars_per_line=32,
    ),
    "cinema_serif": SubtitleStyle(
        font_name="Georgia",
        font_size=34,
        primary_color_hex="#F0EDE6",
        outline_color_hex="#111111",
        outline_width=1.8,
        shadow_color_hex="#000000",
        shadow_offset=1.2,
        bold=False,
        italic=False,
        alignment=SubtitleAlignment.BOTTOM_CENTER,
        margin_v=60,
        margin_h=70,
        animation_mode=KineticAnimationMode.NONE,
        max_chars_per_line=40,
    ),
    "tiktok_reels_neon": SubtitleStyle(
        font_name="Arial",
        font_size=52,
        primary_color_hex="#FFFFFF",
        highlight_color_hex="#00FFCC",
        outline_color_hex="#000000",
        outline_width=4.0,
        shadow_color_hex="#000000",
        shadow_offset=2.5,
        background_box=True,
        background_box_color_hex="#80000000",
        bold=True,
        all_caps=True,
        alignment=SubtitleAlignment.MIDDLE_CENTER,
        margin_v=220,
        margin_h=40,
        animation_mode=KineticAnimationMode.KARAOKE_HIGHLIGHT,
        max_chars_per_line=24,
    ),
    "impact_pop": SubtitleStyle(
        font_name="Impact",
        font_size=48,
        primary_color_hex="#FFFFFF",
        highlight_color_hex="#FF3366",
        outline_color_hex="#000000",
        outline_width=3.5,
        shadow_color_hex="#000000",
        shadow_offset=2.0,
        bold=True,
        all_caps=True,
        alignment=SubtitleAlignment.BOTTOM_CENTER,
        margin_v=120,
        margin_h=40,
        animation_mode=KineticAnimationMode.POP_SCALE,
        max_chars_per_line=22,
    ),
    "minimalist": SubtitleStyle(
        font_name="Arial",
        font_size=28,
        primary_color_hex="#E8E8E8",
        outline_color_hex="#000000",
        outline_width=1.0,
        shadow_offset=0.0,
        background_box=True,
        background_box_color_hex="#60000000",
        bold=False,
        alignment=SubtitleAlignment.BOTTOM_CENTER,
        margin_v=40,
        margin_h=40,
        animation_mode=KineticAnimationMode.NONE,
        max_chars_per_line=42,
    ),
}
