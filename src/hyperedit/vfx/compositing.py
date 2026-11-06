"""Alpha compositing, blend modes, chroma keying and multi-layer depth engine."""

from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from hyperedit.core.exceptions import AdapterError, MediaNotFoundError
from hyperedit.vfx.models import BlendMode, ChromaKeyConfig


class LayerCompositor:
    """Production compositor supporting 8 blend modes, alpha compositing, and chroma keying."""

    @staticmethod
    def blend_frames(
        base_bgr: np.ndarray,
        blend_bgr: np.ndarray,
        mode: BlendMode = BlendMode.NORMAL,
        opacity: float = 1.0,
        blend_alpha: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Blend two images together according to specified BlendMode and opacity."""
        h, w = base_bgr.shape[:2]
        if blend_bgr.shape[:2] != (h, w):
            blend_bgr = cv2.resize(blend_bgr, (w, h), interpolation=cv2.INTER_LINEAR)
        if blend_alpha is not None and blend_alpha.shape[:2] != (h, w):
            blend_alpha = cv2.resize(blend_alpha, (w, h), interpolation=cv2.INTER_LINEAR)

        # Normalize to float 0.0 .. 1.0
        A = base_bgr.astype(np.float32) / 255.0
        B = blend_bgr.astype(np.float32) / 255.0

        if mode == BlendMode.NORMAL:
            R = B
        elif mode == BlendMode.MULTIPLY:
            R = A * B
        elif mode == BlendMode.SCREEN:
            R = 1.0 - (1.0 - A) * (1.0 - B)
        elif mode == BlendMode.OVERLAY:
            R = np.where(A < 0.5, 2.0 * A * B, 1.0 - 2.0 * (1.0 - A) * (1.0 - B))
        elif mode == BlendMode.ADD:
            R = np.clip(A + B, 0.0, 1.0)
        elif mode == BlendMode.SOFT_LIGHT:
            # Pegtop formula: (1 - 2B) A^2 + 2B A
            R = (1.0 - 2.0 * B) * (A ** 2) + 2.0 * B * A
        elif mode == BlendMode.DARKEN:
            R = np.minimum(A, B)
        elif mode == BlendMode.LIGHTEN:
            R = np.maximum(A, B)
        else:
            R = B

        # Alpha blending
        if blend_alpha is not None:
            alpha_f = (blend_alpha.astype(np.float32) / 255.0) * float(opacity)
            if len(alpha_f.shape) == 2:
                alpha_f = np.expand_dims(alpha_f, axis=2)
            out = A * (1.0 - alpha_f) + R * alpha_f
        else:
            op = float(opacity)
            out = A * (1.0 - op) + R * op

        out_uint8 = np.clip(out * 255.0, 0, 255).astype(np.uint8)
        return out_uint8

    @staticmethod
    def apply_chroma_key(
        frame_bgr: np.ndarray,
        config: ChromaKeyConfig,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Perform color difference chroma keying on an input frame.
        
        Returns:
            (keyed_bgra_frame, single_channel_alpha_matte)
        """
        h, w = frame_bgr.shape[:2]
        img = frame_bgr.astype(np.float32) / 255.0

        # Target key color in normalized BGR
        kr, kg, kb = config.key_color_rgb
        target_bgr = np.array([kb / 255.0, kg / 255.0, kr / 255.0], dtype=np.float32)

        # Euclidean color distance in RGB space
        dist = np.linalg.norm(img - target_bgr, axis=2)

        # Softness ramp calculation
        sim = float(config.similarity)
        smooth = max(0.001, float(config.smoothness))

        # Alpha is 0 inside similarity sphere, ramps to 1 at similarity + smoothness
        alpha = np.clip((dist - sim) / smooth, 0.0, 1.0)

        # Green / blue spill suppression
        b = img[:, :, 0]
        g = img[:, :, 1]
        r = img[:, :, 2]

        if kg > kr and kg > kb:
            # Green spill suppression: clamp green channel to average of red and blue
            max_rb = (r + b) * 0.5
            g_suppressed = np.minimum(g, max_rb)
            g_final = g * alpha + g_suppressed * (1.0 - alpha) * config.spill_reduction
            img[:, :, 1] = g_final
        elif kb > kr and kb > kg:
            # Blue spill suppression
            max_rg = (r + g) * 0.5
            b_suppressed = np.minimum(b, max_rg)
            b_final = b * alpha + b_suppressed * (1.0 - alpha) * config.spill_reduction
            img[:, :, 0] = b_final

        alpha_uint8 = (alpha * 255.0).astype(np.uint8)
        bgr_uint8 = np.clip(img * 255.0, 0, 255).astype(np.uint8)
        bgra_uint8 = cv2.merge([bgr_uint8[:, :, 0], bgr_uint8[:, :, 1], bgr_uint8[:, :, 2], alpha_uint8])

        return bgra_uint8, alpha_uint8

    @staticmethod
    def render_chroma_keyed_video(
        input_video: Path | str,
        output_video: Path | str,
        config: ChromaKeyConfig,
        ffmpeg_bin: Optional[str] = None,
    ) -> Path:
        """Extract green/blue screen footage and encode to transparent ProRes 4444 video."""
        in_path = Path(input_video).resolve()
        out_path = Path(output_video).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not in_path.is_file():
            raise MediaNotFoundError(f"Input video for keying not found: {in_path}")

        ff_bin = ffmpeg_bin or shutil.which("ffmpeg")
        if not ff_bin:
            raise AdapterError("FFmpeg is required to encode keyed transparent video.")

        # Convert RGB tuple to 0xRRGGBB hex string
        r, g, b = config.key_color_rgb
        hex_color = f"0x{r:02X}{g:02X}{b:02X}"

        # FFmpeg colorkey filter: colorkey=color:similarity:blend
        colorkey_filter = f"colorkey=color={hex_color}:similarity={config.similarity:.3f}:blend={config.smoothness:.3f},format=yuva444p10le"

        cmd = [
            ff_bin,
            "-y",
            "-i",
            str(in_path),
            "-vf",
            colorkey_filter,
            "-c:v",
            "prores_ks",
            "-profile:v",
            "4444",
            "-pix_fmt",
            "yuva444p10le",
            "-an",
            str(out_path),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            err = res.stderr or "Unknown keying error"
            raise AdapterError(f"FFmpeg colorkey render failed:\n{err}")

        return out_path

