"""Mask authoring, keyframe animation, feathering and assisted rotoscoping."""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from hyperedit.core.exceptions import AdapterError, MediaNotFoundError
from hyperedit.vfx.models import MaskDefinition, MaskKeyframe, MaskShape


class MaskGenerator:
    """Generates 8-bit alpha mattes (0=transparent, 255=opaque) for static, animated, and rotoscoped shapes."""

    @staticmethod
    def render_mask_frame(
        mask_def: MaskDefinition,
        width: int,
        height: int,
        frame_index: int = 0,
    ) -> np.ndarray:
        """Render a single 8-bit grayscale mask image (values 0..255)."""
        canvas = np.zeros((height, width), dtype=np.uint8)

        # 1. Resolve keyframe values or default definition
        center_x = width / 2.0
        center_y = height / 2.0
        w = float(width) * 0.5
        h = float(height) * 0.5
        rot_deg = 0.0
        feather = mask_def.feather_px
        opacity = mask_def.opacity
        points: Optional[List[Tuple[float, float]]] = None

        if mask_def.keyframes:
            # Interpolate between surrounding keyframes
            kfs = sorted(mask_def.keyframes, key=lambda k: k.frame_index)
            if frame_index <= kfs[0].frame_index:
                kf = kfs[0]
                center_x, center_y = kf.center_x, kf.center_y
                w, h = kf.width, kf.height
                rot_deg = kf.rotation_deg
                feather = kf.feather_px
                opacity = kf.opacity
                points = kf.points
            elif frame_index >= kfs[-1].frame_index:
                kf = kfs[-1]
                center_x, center_y = kf.center_x, kf.center_y
                w, h = kf.width, kf.height
                rot_deg = kf.rotation_deg
                feather = kf.feather_px
                opacity = kf.opacity
                points = kf.points
            else:
                # Find bracket
                for i in range(len(kfs) - 1):
                    k_curr = kfs[i]
                    k_next = kfs[i + 1]
                    if k_curr.frame_index <= frame_index <= k_next.frame_index:
                        span = k_next.frame_index - k_curr.frame_index
                        t = (frame_index - k_curr.frame_index) / float(span) if span > 0 else 0.0
                        center_x = k_curr.center_x + t * (k_next.center_x - k_curr.center_x)
                        center_y = k_curr.center_y + t * (k_next.center_y - k_curr.center_y)
                        w = k_curr.width + t * (k_next.width - k_curr.width)
                        h = k_curr.height + t * (k_next.height - k_curr.height)
                        rot_deg = k_curr.rotation_deg + t * (k_next.rotation_deg - k_curr.rotation_deg)
                        feather = k_curr.feather_px + t * (k_next.feather_px - k_curr.feather_px)
                        opacity = k_curr.opacity + t * (k_next.opacity - k_curr.opacity)
                        points = k_curr.points
                        break

        # 2. Draw geometric primitive
        cx, cy = int(round(center_x)), int(round(center_y))
        half_w, half_h = int(round(w / 2.0)), int(round(h / 2.0))

        if mask_def.shape == MaskShape.RECTANGLE:
            if abs(rot_deg) > 0.01:
                rect = ((float(cx), float(cy)), (float(w), float(h)), float(rot_deg))
                box = cv2.boxPoints(rect)
                box = np.int32(np.round(box))
                cv2.fillPoly(canvas, [box], 255)
            else:
                x1, y1 = max(0, cx - half_w), max(0, cy - half_h)
                x2, y2 = min(width, cx + half_w), min(height, cy + half_h)
                cv2.rectangle(canvas, (x1, y1), (x2, y2), 255, -1)

        elif mask_def.shape == MaskShape.ELLIPSE:
            axes = (max(1, half_w), max(1, half_h))
            cv2.ellipse(canvas, (cx, cy), axes, rot_deg, 0.0, 360.0, 255, -1)

        elif mask_def.shape in (MaskShape.POLYGON, MaskShape.BEZIER_SPLINE):
            if points and len(points) >= 3:
                poly_pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
                cv2.fillPoly(canvas, [poly_pts], 255)
            else:
                # Default diamond polygon
                diamond = np.array([[cx, cy - half_h], [cx + half_w, cy], [cx, cy + half_h], [cx - half_w, cy]], dtype=np.int32)
                cv2.fillPoly(canvas, [diamond], 255)

        else:
            # Default fallback full canvas
            canvas[:] = 255

        # 3. Apply Gaussian feathering
        if feather > 0.5:
            # Kernel size must be odd
            ksize = int(round(feather * 3.0)) * 2 + 1
            ksize = max(3, min(201, ksize))
            canvas = cv2.GaussianBlur(canvas, (ksize, ksize), sigmaX=feather, sigmaY=feather)

        # 4. Apply opacity scaling
        if opacity < 0.999:
            canvas = (canvas.astype(np.float32) * float(opacity)).astype(np.uint8)

        # 5. Invert if specified
        if mask_def.inverted:
            canvas = cv2.bitwise_not(canvas)

        return canvas

    @staticmethod
    def assisted_rotoscope_grabcut(
        image_or_path: np.ndarray | Path | str,
        bounding_box: Tuple[int, int, int, int],
        iterations: int = 5,
        feather_px: float = 2.0,
    ) -> np.ndarray:
        """Assisted rotoscoping using GrabCut algorithm.
        
        Args:
            image_or_path: Input BGR image array or path to frame.
            bounding_box: (x, y, w, h) enclosing foreground subject.
            iterations: Number of GrabCut refinement iterations.
            feather_px: Edge feathering blur.
            
        Returns:
            8-bit single-channel alpha matte (0..255).
        """
        if isinstance(image_or_path, (str, Path)):
            p = Path(image_or_path).resolve()
            if not p.is_file():
                raise MediaNotFoundError(f"Frame image not found: {p}")
            img = cv2.imread(str(p))
            if img is None:
                raise AdapterError(f"Could not load image: {p.name}")
        else:
            img = image_or_path

        h, w = img.shape[:2]
        bx, by, bw, bh = bounding_box
        bx, by = max(0, bx), max(0, by)
        bw, bh = min(w - bx, bw), min(h - by, bh)

        if bw <= 4 or bh <= 4:
            raise AdapterError("Bounding box too small for GrabCut rotoscoping.")

        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        rect = (bx, by, bw, bh)
        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_RECT)

        # 0 & 2 are background, 1 & 3 are foreground
        output_mask = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)

        if feather_px > 0.5:
            ksize = int(round(feather_px * 3.0)) * 2 + 1
            output_mask = cv2.GaussianBlur(output_mask, (ksize, ksize), sigmaX=feather_px, sigmaY=feather_px)

        return output_mask

    @staticmethod
    def build_ffmpeg_mask_filter(
        mask_def: MaskDefinition,
        width: int,
        height: int,
    ) -> str:
        """Compile a static mask into an FFmpeg geq / drawbox filter expression."""
        cx = width / 2.0
        cy = height / 2.0
        rx = width * 0.4
        ry = height * 0.4

        if mask_def.keyframes:
            kf = mask_def.keyframes[0]
            cx, cy = kf.center_x, kf.center_y
            rx, ry = kf.width / 2.0, kf.height / 2.0

        if mask_def.shape == MaskShape.ELLIPSE:
            # geq ellipse equation ((X-cx)/rx)^2 + ((Y-cy)/ry)^2 <= 1
            inv = "0" if mask_def.inverted else "255"
            non_inv = "255" if mask_def.inverted else "0"
            expr = f"if(lte(pow((X-{cx})/{rx},2)+pow((Y-{cy})/{ry},2),1),{inv},{non_inv})"
            return f"format=yuva420p,geq=a='{expr}'"
        else:
            x1 = int(cx - rx)
            y1 = int(cy - ry)
            x2 = int(cx + rx)
            y2 = int(cy + ry)
            inv = "0" if mask_def.inverted else "255"
            non_inv = "255" if mask_def.inverted else "0"
            expr = f"if(between(X,{x1},{x2})*between(Y,{y1},{y2}),{inv},{non_inv})"
            return f"format=yuva420p,geq=a='{expr}'"

