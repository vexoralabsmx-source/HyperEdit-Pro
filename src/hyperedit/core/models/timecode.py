"""SMPTE Timecode and frame math for HyperEdit Pro."""

from fractions import Fraction
import math
from typing import Any, Union
from pydantic import BaseModel, Field, model_validator

from hyperedit.core.constants import STANDARD_FRAME_RATES
from hyperedit.core.exceptions import ProjectValidationError


def resolve_fps_fraction(fps: Union[float, int, str, Fraction]) -> Fraction:
    """Resolve an FPS representation to an exact Fraction."""
    if isinstance(fps, Fraction):
        return fps
    if isinstance(fps, int):
        return Fraction(fps, 1)
    fps_str = str(fps).strip()
    if fps_str in STANDARD_FRAME_RATES:
        return STANDARD_FRAME_RATES[fps_str]
    try:
        val = float(fps)
        # Check close proximity to 23.976, 29.97, 59.94
        if abs(val - 23.976) < 0.01:
            return STANDARD_FRAME_RATES["23.976"]
        if abs(val - 29.97) < 0.01:
            return STANDARD_FRAME_RATES["29.97"]
        if abs(val - 59.94) < 0.01:
            return STANDARD_FRAME_RATES["59.94"]
        return Fraction(val).limit_denominator(10000)
    except (ValueError, ZeroDivisionError) as e:
        raise ProjectValidationError(f"Invalid frame rate value: {fps}") from e


class Timecode(BaseModel):
    """Accurate SMPTE timecode representation with frame, second, and string support."""

    frames: int = Field(default=0, ge=0, description="Absolute non-negative frame count")
    fps: float = Field(default=30.0, gt=0, description="Nominal frame rate in frames per second")

    @property
    def fps_fraction(self) -> Fraction:
        return resolve_fps_fraction(self.fps)

    @property
    def seconds(self) -> float:
        """Convert frame count to exact float seconds."""
        frac = self.fps_fraction
        return float(Fraction(self.frames, 1) / frac)

    def to_smpte(self, drop_frame: bool = False) -> str:
        """Convert frame count into SMPTE HH:MM:SS:FF representation."""
        nominal_fps = round(self.fps)
        total_frames = self.frames

        if drop_frame and nominal_fps in (30, 60):
            # SMPTE standard drop-frame calculation
            # For 29.97 fps (nominal 30): drop 2 frames every minute except tens of minutes
            drop = 2 if nominal_fps == 30 else 4
            frames_per_10min = round(nominal_fps * 600 - drop * 9)
            frames_per_min = round(nominal_fps * 60 - drop)
            d = total_frames // frames_per_10min
            m = total_frames % frames_per_10min
            if m > drop:
                total_frames += drop * 9 * d + drop * ((m - drop) // frames_per_min)
            else:
                total_frames += drop * 9 * d

        ff = total_frames % nominal_fps
        total_seconds = total_frames // nominal_fps
        ss = total_seconds % 60
        total_minutes = total_seconds // 60
        mm = total_minutes % 60
        hh = total_minutes // 60

        separator = ";" if drop_frame else ":"
        return f"{hh:02d}:{mm:02d}:{ss:02d}{separator}{ff:02d}"

    @classmethod
    def from_frames(cls, frames: int, fps: Union[float, int, str] = 30.0) -> "Timecode":
        return cls(frames=int(frames), fps=float(fps))

    @classmethod
    def from_seconds(cls, seconds: float, fps: Union[float, int, str] = 30.0) -> "Timecode":
        frac = resolve_fps_fraction(fps)
        frames = int(round(Fraction(str(seconds)) * frac))
        return cls(frames=max(0, frames), fps=float(fps))

    @classmethod
    def from_smpte(cls, smpte_str: str, fps: Union[float, int, str] = 30.0) -> "Timecode":
        clean = smpte_str.strip()
        is_drop = ";" in clean
        parts = clean.replace(";", ":").split(":")
        if len(parts) != 4:
            raise ProjectValidationError(
                f"Invalid SMPTE timecode format: '{smpte_str}'. Expected HH:MM:SS:FF"
            )
        try:
            hh, mm, ss, ff = [int(p) for p in parts]
        except ValueError as e:
            raise ProjectValidationError(
                f"Non-numeric values in SMPTE timecode: '{smpte_str}'"
            ) from e

        nominal_fps = round(float(fps))
        total_seconds = hh * 3600 + mm * 60 + ss
        total_frames = total_seconds * nominal_fps + ff

        if is_drop and nominal_fps in (30, 60):
            drop = 2 if nominal_fps == 30 else 4
            total_minutes = hh * 60 + mm
            dropped_frames = drop * (total_minutes - (total_minutes // 10))
            total_frames -= dropped_frames

        return cls(frames=max(0, total_frames), fps=float(fps))

    def __add__(self, other: Union["Timecode", int]) -> "Timecode":
        if isinstance(other, Timecode):
            return Timecode(frames=self.frames + other.frames, fps=self.fps)
        return Timecode(frames=self.frames + int(other), fps=self.fps)

    def __sub__(self, other: Union["Timecode", int]) -> "Timecode":
        if isinstance(other, Timecode):
            return Timecode(frames=max(0, self.frames - other.frames), fps=self.fps)
        return Timecode(frames=max(0, self.frames - int(other)), fps=self.fps)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Timecode):
            return self.frames == other.frames and abs(self.fps - other.fps) < 0.01
        return False

    def __str__(self) -> str:
        return self.to_smpte()

