"""Curated professional motion graphics presets and art direction systems."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class MotionPreset(BaseModel):
    """Artistic and kinematic preset governing typography, timing, easing, and visual hierarchy."""

    name: str = Field(..., description="Preset identifier")
    display_name: str
    description: str
    design_principles: List[str] = Field(default_factory=list)
    recommended_fps: float = Field(default=30.0)
    color_palette: Dict[str, str] = Field(default_factory=dict)
    typography: Dict[str, Any] = Field(default_factory=dict)
    motion: Dict[str, Any] = Field(default_factory=dict)
    restrictions: List[str] = Field(default_factory=list)


STANDARD_MOTION_PRESETS: Dict[str, MotionPreset] = {
    "minimal_editorial": MotionPreset(
        name="minimal_editorial",
        display_name="Minimal Editorial",
        description="Restrained, timeless luxury editorial aesthetic with generous whitespace and calm pacing.",
        design_principles=[
            "Content-first editorial layout with spacious margins.",
            "Subtle opacity fades and micro-scale drifts (1.00 -> 1.03x).",
            "Monochrome foundation with warm muted accents.",
            "Never crowd the canvas with artificial boxes or loud widgets.",
        ],
        recommended_fps=24.0,
        color_palette={
            "background": "transparent",
            "surface": "rgba(255, 255, 255, 0.04)",
            "text_primary": "#FFFFFF",
            "text_secondary": "#A1A1AA",
            "accent": "#E4E4E7",
        },
        typography={
            "title_font": "Helvetica Neue, Arial, sans-serif",
            "subtitle_font": "Georgia, serif",
            "title_weight": "500",
            "letter_spacing": "0.08em",
            "line_height": "1.2",
            "all_caps": True,
        },
        motion={
            "enter_duration_sec": 1.2,
            "exit_duration_sec": 0.8,
            "ease_curve": "power2.out",
            "bezier": (0.16, 1.0, 0.3, 1.0),  # expo.out
            "stagger_sec": 0.12,
            "scale_drift": 1.03,
        },
        restrictions=[
            "No bright saturated neon colors.",
            "No abrupt jerky mechanical movements.",
            "No heavy drop shadows or glows.",
        ],
    ),
    "cinematic_luxury": MotionPreset(
        name="cinematic_luxury",
        display_name="Cinematic Luxury",
        description="Prestige automotive and haute horlogerie art direction (Porsche / Apple benchmark).",
        design_principles=[
            "Deep cinematic contrast with refined ivory and champagne typography.",
            "Smooth cubic-bezier reveals with letter-spacing expansion.",
            "Carefully choreographed staggered reveals.",
            "Confidence, restraint, and exceptional optical balance.",
        ],
        recommended_fps=30.0,
        color_palette={
            "background": "transparent",
            "surface": "rgba(18, 18, 22, 0.65)",
            "text_primary": "#F4F1EA",
            "text_secondary": "#B5AFA4",
            "accent": "#C9A86A",  # Champagne gold
        },
        typography={
            "title_font": "Georgia, Garamond, serif",
            "subtitle_font": "Arial, -apple-system, sans-serif",
            "title_weight": "400",
            "letter_spacing": "0.15em",
            "line_height": "1.15",
            "all_caps": True,
        },
        motion={
            "enter_duration_sec": 1.4,
            "exit_duration_sec": 0.9,
            "ease_curve": "cubic-bezier(0.25, 0.1, 0.25, 1.0)",
            "bezier": (0.25, 0.1, 0.25, 1.0),
            "stagger_sec": 0.18,
            "scale_drift": 1.04,
        },
        restrictions=[
            "Never use bouncy cartoon springs.",
            "Avoid generic blue gradients.",
            "Preserve high-end editorial calm.",
        ],
    ),
    "tech_product": MotionPreset(
        name="tech_product",
        display_name="Tech Product Showcase",
        description="Precision engineering aesthetic for software UI, developer tools, and physical devices.",
        design_principles=[
            "Crisp geometric hierarchy with glassmorphic backing pills.",
            "Subtle 3D perspective elevation and soft directional shadows.",
            "Micro-interaction feedback for specifications, badges, and metrics.",
            "Fast, confident ease-out motion with high frame rate fidelity.",
        ],
        recommended_fps=60.0,
        color_palette={
            "background": "transparent",
            "surface": "rgba(24, 24, 27, 0.75)",
            "text_primary": "#FAFAFA",
            "text_secondary": "#71717A",
            "accent": "#3B82F6",  # Electric blue
            "border": "rgba(255, 255, 255, 0.12)",
        },
        typography={
            "title_font": "SF Pro Display, -apple-system, Inter, sans-serif",
            "subtitle_font": "SF Mono, Consolas, monospace",
            "title_weight": "600",
            "letter_spacing": "-0.02em",
            "line_height": "1.25",
            "all_caps": False,
        },
        motion={
            "enter_duration_sec": 0.7,
            "exit_duration_sec": 0.5,
            "ease_curve": "power3.out",
            "bezier": (0.215, 0.61, 0.355, 1.0),
            "stagger_sec": 0.08,
            "scale_drift": 1.02,
        },
        restrictions=[
            "No fake sci-fi HUD elements.",
            "No ungrounded random rotating wireframes.",
        ],
    ),
    "corporate_clean": MotionPreset(
        name="corporate_clean",
        display_name="Corporate Clean",
        description="High-trust, professional clarity for business communication, executive decks, and reports.",
        design_principles=[
            "Rock-solid readability across all screen sizes.",
            "Neutral, highly accessible color contrast (WCAG AAA compliant).",
            "Predictable, smooth ease-in-out slides and clean lower thirds.",
            "Disciplined data presentation.",
        ],
        recommended_fps=30.0,
        color_palette={
            "background": "transparent",
            "surface": "rgba(255, 255, 255, 0.92)",
            "text_primary": "#0F172A",
            "text_secondary": "#475569",
            "accent": "#0284C7",
            "border": "#E2E8F0",
        },
        typography={
            "title_font": "Arial, Helvetica, sans-serif",
            "subtitle_font": "Arial, Helvetica, sans-serif",
            "title_weight": "700",
            "letter_spacing": "0.0em",
            "line_height": "1.3",
            "all_caps": False,
        },
        motion={
            "enter_duration_sec": 0.6,
            "exit_duration_sec": 0.4,
            "ease_curve": "power2.out",
            "bezier": (0.4, 0.0, 0.2, 1.0),
            "stagger_sec": 0.06,
            "scale_drift": 1.0,
        },
        restrictions=[
            "No distracting particle effects.",
            "No rotation or tilted angles.",
        ],
    ),
    "energetic_social": MotionPreset(
        name="energetic_social",
        display_name="Energetic Social",
        description="High-impact kinetic design for vertical 9:16 reels, shorts, and fast-paced hooks.",
        design_principles=[
            "Immediate visual engagement within the first 300 milliseconds.",
            "Safe-zone compliant layout (elevated above platform UI icons).",
            "Punchy scale entrances with controlled overshoot bounce.",
            "Beat-reactive pulsation and vibrant high-contrast accents.",
        ],
        recommended_fps=30.0,
        color_palette={
            "background": "transparent",
            "surface": "#000000",
            "text_primary": "#FFFFFF",
            "text_secondary": "#E4E4E7",
            "accent": "#00FFCC",  # Neon mint
            "highlight": "#FFE600",
        },
        typography={
            "title_font": "Impact, Arial Black, sans-serif",
            "subtitle_font": "Arial Bold, sans-serif",
            "title_weight": "900",
            "letter_spacing": "0.02em",
            "line_height": "1.05",
            "all_caps": True,
        },
        motion={
            "enter_duration_sec": 0.45,
            "exit_duration_sec": 0.35,
            "ease_curve": "back.out(1.7)",
            "bezier": (0.34, 1.56, 0.64, 1.0),
            "stagger_sec": 0.04,
            "scale_drift": 1.06,
        },
        restrictions=[
            "Avoid tiny unreadable body text.",
            "Do not place key content in the bottom 250px or top 150px safe zones.",
        ],
    ),
    "typography_focus": MotionPreset(
        name="typography_focus",
        display_name="Typography Focus",
        description="Architectural kinetic typography, editorial word reveal, and typographic masking.",
        design_principles=[
            "Type is the visual hero, not a decorative subtitle.",
            "Masked container reveals (sliding out of an invisible clip-path).",
            "Tight proportional line height and dynamic scale contrast.",
            "Rhythmic synchronization with spoken cadences and musical downbeats.",
        ],
        recommended_fps=30.0,
        color_palette={
            "background": "transparent",
            "surface": "rgba(0, 0, 0, 0.8)",
            "text_primary": "#FFFFFF",
            "text_secondary": "#888888",
            "accent": "#FF3366",  # Crimson punch
        },
        typography={
            "title_font": "Arial, Helvetica, -apple-system, sans-serif",
            "subtitle_font": "Arial, monospace",
            "title_weight": "800",
            "letter_spacing": "-0.03em",
            "line_height": "0.95",
            "all_caps": True,
        },
        motion={
            "enter_duration_sec": 0.9,
            "exit_duration_sec": 0.6,
            "ease_curve": "expo.out",
            "bezier": (0.19, 1.0, 0.22, 1.0),
            "stagger_sec": 0.08,
            "scale_drift": 1.02,
        },
        restrictions=[
            "Do not obscure the typography with busy visual clutter.",
        ],
    ),
}

