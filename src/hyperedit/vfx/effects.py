"""Non-destructive cinematic visual effects: camera shake, film grain, bloom/glow, motion blur and parallax."""

import math
from pathlib import Path
import random
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from hyperedit.core.exceptions import AdapterError, MediaNotFoundError
from hyperedit.vfx.models import (
    BloomGlowConfig,
    CameraShakeConfig,
    DepthParallaxLayer,
    FilmGrainConfig,
    MotionBlurConfig,
)


class CinematicEffects:
    """Compiles and renders non-destructive cinematic visual effects."""

    @staticmethod
    def build_camera_shake_filter(
        config: CameraShakeConfig,
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Generate a deterministic trigonometric camera shake filter expression in FFmpeg."""
        if not config.enabled:
            return "null"

        amp = config.intensity_px
        freq = config.frequency_hz
        seed = config.seed

        # Safe crop zoom to avoid showing borders during shake (typically 3-6%)
        zoom = 1.0 + (amp * 2.5 / min(width, height))
        cw = int(round(width / zoom))
        ch = int(round(height / zoom))

        # Trigonometric multi-frequency pseudo-random series
        x_expr = (
            f"'(in_w-out_w)/2 + {amp:.2f}*sin(2*PI*{freq:.2f}*t + {seed:.1f}) "
            f"+ {amp*0.35:.2f}*cos(4.3*PI*{freq:.2f}*t + {seed+1:.1f})'"
        )
        y_expr = (
            f"'(in_h-out_h)/2 + {amp*0.85:.2f}*cos(2.4*PI*{freq:.2f}*t + {seed+2:.1f}) "
            f"+ {amp*0.25:.2f}*sin(5.1*PI*{freq:.2f}*t + {seed+3:.1f})'"
        )

        return f"crop={cw}:{ch}:{x_expr}:{y_expr},scale={width}:{height}"

    @staticmethod
    def build_film_grain_filter(config: FilmGrainConfig) -> str:
        """Generate organic photochemical film grain noise filter."""
        if not config.enabled:
            return "null"

        # Scale intensity (0.0 .. 1.0) to FFmpeg noise strength (0 .. 60)
        strength = max(1, int(round(config.intensity * 50.0)))
        # allf=t (temporal noise, changes every frame), allf=u (uniform distribution)
        flags = "t+u"
        if not config.chromatic:
            # Monochrome grain: apply only to luma channel
            return f"noise=c0s={strength}:c0f={flags}"
        else:
            # Chromatic grain: apply to luma and chroma
            c_strength = max(1, int(round(strength * 0.7)))
            return f"noise=c0s={strength}:c1s={c_strength}:c2s={c_strength}:allf={flags}"

    @staticmethod
    def build_bloom_glow_filter(
        config: BloomGlowConfig,
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Generate highlight extraction, Gaussian diffusion, and additive glow filtergraph."""
        if not config.enabled:
            return "null"

        cutoff = int(round(config.threshold * 255.0))
        radius = max(1, config.radius_px)
        opacity = min(1.0, config.intensity)

        # 1. Split stream into main and bloom branches
        # 2. Extract luma highlights above threshold
        # 3. Blur highlights with gblur
        # 4. Additive blend over original
        filter_str = (
            f"split[bg][high];"
            f"[high]format=gbrp,geq=r='if(gt(lum(X,Y),{cutoff}),r(X,Y),0)':"
            f"g='if(gt(lum(X,Y),{cutoff}),g(X,Y),0)':b='if(gt(lum(X,Y),{cutoff}),b(X,Y),0)',"
            f"gblur=sigma={radius}[blurred];"
            f"[bg][blurred]blend=all_mode=addition:all_opacity={opacity:.2f},format=yuv420p"
        )
        return filter_str

    @staticmethod
    def build_motion_blur_filter(config: MotionBlurConfig) -> str:
        """Generate temporal accumulation motion blur filter."""
        if not config.enabled:
            return "null"

        # tblend averages consecutive frames simulating shutter exposure
        # Shutter angle 180° = 50% exposure time
        return "tblend=all_mode=average"

    @staticmethod
    def render_effect_to_video(
        input_video: Path | str,
        output_video: Path | str,
        filter_complex_str: str,
        ffmpeg_bin: Optional[str] = None,
    ) -> Path:
        """Render a video file with an applied cinematic filtergraph."""
        in_path = Path(input_video).resolve()
        out_path = Path(output_video).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not in_path.is_file():
            raise MediaNotFoundError(f"Input video not found: {in_path}")

        ff_bin = ffmpeg_bin or shutil.which("ffmpeg")
        if not ff_bin:
            raise AdapterError("FFmpeg executable required to render cinematic effects.")

        # Determine if it's a simple filter or complex filtergraph
        is_complex = ";" in filter_complex_str or "[" in filter_complex_str
        filter_args = ["-filter_complex", filter_complex_str] if is_complex else ["-vf", filter_complex_str]

        cmd = [
            ff_bin,
            "-y",
            "-i",
            str(in_path),
            *filter_args,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "copy",
            str(out_path),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            err = res.stderr or "Unknown effect render error"
            raise AdapterError(f"Cinematic effect render failed:\n{err}")

        return out_path

