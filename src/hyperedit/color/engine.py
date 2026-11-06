"""Core color grading, tonal evaluation, histogram analysis, and shot matching engine."""

import math
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from hyperedit.color.models import (
    ColorAuditReport,
    HistogramMetrics,
    ShotMatchTelemetry,
)
from hyperedit.color.presets import COLOR_PRESETS, blend_color_grades
from hyperedit.core.exceptions import AdapterError, MediaNotFoundError, MediaProbeError
from hyperedit.core.models.color import (
    ColorGradeConfig,
    ColorMetadata,
    ColorRange,
    ColorStandard,
    LUTInterpolation,
)
from hyperedit.media.prober import FFprobeProber


class ColorGradingEngine:
    """Production color grading compiler, shot matching, and color management engine."""

    def __init__(self, ffmpeg_bin: Optional[str] = None) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")

    @staticmethod
    def build_ffmpeg_filter(config: ColorGradeConfig) -> str:
        """Compile a ColorGradeConfig model into a deterministic FFmpeg filtergraph chain."""
        if not config.enabled:
            return "null"

        # Apply preset look blending if a preset is referenced
        effective_cfg = config
        if config.preset_name and config.preset_name in COLOR_PRESETS:
            preset_target = COLOR_PRESETS[config.preset_name]
            effective_cfg = blend_color_grades(config, preset_target, config.preset_strength)

        filter_steps: List[str] = []

        # 1. Exposure and Contrast and Saturation via eq filter
        # In FFmpeg eq: brightness is [-1.0, 1.0], contrast is [0.0, 3.0], saturation is [0.0, 3.0]
        # 1 EV stop ≈ +0.10 brightness in eq
        b_offset = max(-0.8, min(0.8, effective_cfg.exposure_ev * 0.12))
        c_mult = max(0.1, min(3.0, effective_cfg.contrast))
        s_mult = max(0.0, min(3.0, effective_cfg.saturation))

        if abs(b_offset) > 0.001 or abs(c_mult - 1.0) > 0.001 or abs(s_mult - 1.0) > 0.001:
            filter_steps.append(f"eq=brightness={b_offset:.4f}:contrast={c_mult:.4f}:saturation={s_mult:.4f}")

        # 2. Color Balance (Temperature, Tint, Lift/Gamma/Gain)
        # Temperature: blue (-) to orange (+). Tint: green (-) to magenta (+)
        # rs, gs, bs (shadows); rm, gm, bm (midtones); rh, gh, bh (highlights) in [-1.0, 1.0]
        rm_shift = max(-1.0, min(1.0, effective_cfg.temperature * 0.008))
        bm_shift = max(-1.0, min(1.0, -effective_cfg.temperature * 0.008))
        gm_shift = max(-1.0, min(1.0, -effective_cfg.tint * 0.008))

        # Merge with LiftGammaGain if present
        lgg = effective_cfg.lift_gamma_gain
        rs = lgg.lift[0] if lgg else 0.0
        gs = lgg.lift[1] if lgg else 0.0
        bs = lgg.lift[2] if lgg else 0.0

        rm = (lgg.gamma[0] - 1.0 + rm_shift) if lgg else rm_shift
        gm = (lgg.gamma[1] - 1.0 + gm_shift) if lgg else gm_shift
        bm = (lgg.gamma[2] - 1.0 + bm_shift) if lgg else bm_shift

        rh = (lgg.gain[0] - 1.0 + rm_shift * 0.5) if lgg else (rm_shift * 0.5)
        gh = (lgg.gain[1] - 1.0 + gm_shift * 0.5) if lgg else (gm_shift * 0.5)
        bh = (lgg.gain[2] - 1.0 + bm_shift * 0.5) if lgg else (bm_shift * 0.5)

        has_balance = any(abs(v) > 0.002 for v in [rs, gs, bs, rm, gm, bm, rh, gh, bh])
        if has_balance:
            filter_steps.append(
                f"colorbalance=rs={rs:.4f}:gs={gs:.4f}:bs={bs:.4f}:"
                f"rm={rm:.4f}:gm={gm:.4f}:bm={bm:.4f}:"
                f"rh={rh:.4f}:gh={gh:.4f}:bh={bh:.4f}"
            )

        # 3. Tonal Curves (Black point, White point, S-curves)
        curve_parts: List[str] = []
        # Black and white points
        bp = max(-0.2, min(0.2, effective_cfg.black_point))
        wp = max(0.8, min(1.2, effective_cfg.white_point))
        has_custom_levels = abs(bp) > 0.001 or abs(wp - 1.0) > 0.001

        if effective_cfg.curves and effective_cfg.curves.master:
            pts_str = " ".join(f"{p.x:.3f}/{p.y:.3f}" for p in effective_cfg.curves.master)
            curve_parts.append(f"m='{pts_str}'")
        elif has_custom_levels:
            curve_parts.append(f"m='0/{max(0.0, bp):.3f} 1/{min(1.0, wp):.3f}'")

        if effective_cfg.curves:
            if effective_cfg.curves.red:
                curve_parts.append("r='" + " ".join(f"{p.x:.3f}/{p.y:.3f}" for p in effective_cfg.curves.red) + "'")
            if effective_cfg.curves.green:
                curve_parts.append("g='" + " ".join(f"{p.x:.3f}/{p.y:.3f}" for p in effective_cfg.curves.green) + "'")
            if effective_cfg.curves.blue:
                curve_parts.append("b='" + " ".join(f"{p.x:.3f}/{p.y:.3f}" for p in effective_cfg.curves.blue) + "'")

        if curve_parts:
            filter_steps.append(f"curves={':'.join(curve_parts)}")

        # 4. 3D Look-Up Table (.cube)
        if effective_cfg.lut_path:
            lut_p = Path(effective_cfg.lut_path).resolve()
            if lut_p.is_file():
                escaped_path = lut_p.as_posix().replace(":", r"\:")
                interp = effective_cfg.lut_interpolation.value
                filter_steps.append(f"lut3d=file='{escaped_path}':interp={interp}")

        return ",".join(filter_steps) if filter_steps else "null"

    def apply_color_grade_to_video(
        self,
        input_video: Path | str,
        output_video: Path | str,
        config: ColorGradeConfig,
    ) -> Path:
        """Apply color grade filtergraph and render deliverable video."""
        in_p = Path(input_video).resolve()
        out_p = Path(output_video).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if not in_p.is_file():
            raise MediaNotFoundError(f"Input video not found: {in_p}")
        if not self.ffmpeg_bin:
            raise AdapterError("FFmpeg executable required for rendering color grades.")

        filt = self.build_ffmpeg_filter(config)
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(in_p),
            "-vf",
            filt,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "copy",
            str(out_p),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            err = res.stderr or "Unknown color grading error"
            raise AdapterError(f"Failed to render graded video:\n{err}")

        return out_p

    @staticmethod
    def analyze_histogram(media_path: Path | str, sample_frames: int = 15) -> HistogramMetrics:
        """Extract multi-frame luma/chroma signal telemetry and clipping statistics."""
        p = Path(media_path).resolve()
        if not p.is_file():
            raise MediaNotFoundError(f"Media file not found for histogram analysis: {p}")

        cap = cv2.VideoCapture(str(p))
        if not cap.isOpened():
            raise MediaProbeError(f"Could not open media file for color analysis: {p.name}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        step = max(1, total_frames // sample_frames)

        luma_samples: List[np.ndarray] = []
        r_means: List[float] = []
        g_means: List[float] = []
        b_means: List[float] = []
        shadow_clipped_pixels = 0
        highlight_clipped_pixels = 0
        total_pixels_inspected = 0

        current_frame = 0
        read_count = 0

        while cap.isOpened() and read_count < sample_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Convert to float and Rec.709 Luma: Y = 0.2126*R + 0.7152*G + 0.0722*B
            b = frame[:, :, 0].astype(np.float32)
            g = frame[:, :, 1].astype(np.float32)
            r = frame[:, :, 2].astype(np.float32)

            luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
            luma_samples.append(luma.flatten())

            r_means.append(float(np.mean(r)))
            g_means.append(float(np.mean(g)))
            b_means.append(float(np.mean(b)))

            # Clipping audit: black clipping (<16 IRE), white clipping (>240 IRE)
            shadow_clipped_pixels += int(np.sum(luma < 16.0))
            highlight_clipped_pixels += int(np.sum(luma > 240.0))
            total_pixels_inspected += luma.size

            current_frame += step
            read_count += 1

        cap.release()

        if not luma_samples:
            raise MediaProbeError("No readable video frames found for color analysis.")

        all_luma = np.concatenate(luma_samples)
        mean_y = float(np.mean(all_luma))
        std_y = float(np.std(all_luma))
        min_y = float(np.min(all_luma))
        max_y = float(np.max(all_luma))

        mr = float(np.mean(r_means))
        mg = float(np.mean(g_means))
        mb = float(np.mean(b_means))

        shadow_pct = (shadow_clipped_pixels / max(1, total_pixels_inspected)) * 100.0
        highlight_pct = (highlight_clipped_pixels / max(1, total_pixels_inspected)) * 100.0

        # Estimated dynamic range in stops: log2(max_y / min_y)
        dr_stops = math.log2(max(1.0, max_y) / max(1.0, min_y)) if min_y > 0 else 8.0

        return HistogramMetrics(
            mean_luma=round(mean_y, 2),
            std_luma=round(std_y, 2),
            min_luma=round(min_y, 2),
            max_luma=round(max_y, 2),
            mean_rgb=(round(mr, 2), round(mg, 2), round(mb, 2)),
            shadow_clipping_pct=round(shadow_pct, 2),
            highlight_clipping_pct=round(highlight_pct, 2),
            dynamic_range_stops=round(dr_stops, 2),
        )

    @staticmethod
    def generate_histogram_image(media_path: Path | str, output_image: Path | str) -> Path:
        """Render a 4-channel RGB + Luma histogram visualization chart to PNG."""
        p = Path(media_path).resolve()
        out_p = Path(output_image).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(p))
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise MediaProbeError("Failed to extract frame for histogram graphic.")

        h, w = 300, 512
        hist_canvas = np.full((h, w, 3), 20, dtype=np.uint8)  # Dark slate background

        # Calculate histograms for R, G, B
        colors = [(255, 60, 60), (60, 255, 60), (60, 120, 255)]  # BGR
        for ch, color in enumerate(colors):
            hist = cv2.calcHist([frame], [ch], None, [256], [0, 256])
            cv2.normalize(hist, hist, alpha=0, beta=h - 30, norm_type=cv2.NORM_MINMAX)
            hist_flat = hist.flatten()

            pts = []
            for i in range(256):
                x = int(i * 2)
                y = int(h - 15 - float(hist_flat[i]))
                pts.append((x, y))

            for j in range(len(pts) - 1):
                cv2.line(hist_canvas, pts[j], pts[j + 1], color, 1, cv2.LINE_AA)

        cv2.imwrite(str(out_p), hist_canvas)
        return out_p

    def match_shots(
        self,
        reference_media: Path | str,
        target_media: Path | str,
    ) -> ShotMatchTelemetry:
        """Calculate corrective grade parameters to align target shot tonal consistency to reference shot."""
        ref_metrics = self.analyze_histogram(reference_media)
        tgt_metrics = self.analyze_histogram(target_media)

        # 1. Compute Exposure EV delta
        # EV = log2(target_luma / ref_luma)
        if tgt_metrics.mean_luma > 0 and ref_metrics.mean_luma > 0:
            luma_ratio = ref_metrics.mean_luma / tgt_metrics.mean_luma
            ev_delta = math.log2(luma_ratio)
            # Restrict compensation to conservative range [-2.0, 2.0] EV
            ev_delta = max(-2.0, min(2.0, ev_delta))
        else:
            ev_delta = 0.0

        # 2. Compute Contrast Ratio
        if tgt_metrics.std_luma > 0:
            contrast_ratio = ref_metrics.std_luma / tgt_metrics.std_luma
            # Conservative contrast clamping [0.75, 1.35]
            contrast_ratio = max(0.75, min(1.35, contrast_ratio))
        else:
            contrast_ratio = 1.0

        # 3. Compute Chromatic RGB Balance using normalized chromaticity coordinates (independent of exposure)
        ref_r, ref_g, ref_b = ref_metrics.mean_rgb
        tgt_r, tgt_g, tgt_b = tgt_metrics.mean_rgb

        ref_sum = max(1.0, ref_r + ref_g + ref_b)
        tgt_sum = max(1.0, tgt_r + tgt_g + tgt_b)

        ref_rn = ref_r / ref_sum
        ref_gn = ref_g / ref_sum
        ref_bn = ref_b / ref_sum

        tgt_rn = tgt_r / tgt_sum
        tgt_gn = tgt_g / tgt_sum
        tgt_bn = tgt_b / tgt_sum

        # Temp: shift toward red/away from blue. Tint: shift toward magenta/away from green.
        delta_temp = (ref_rn - tgt_rn) - (ref_bn - tgt_bn)
        delta_tint = (ref_rn + ref_bn) / 2.0 - ref_gn - ((tgt_rn + tgt_bn) / 2.0 - tgt_gn)

        temp_deg = max(-50.0, min(50.0, delta_temp * 150.0))
        tint_deg = max(-50.0, min(50.0, delta_tint * 150.0))

        matched_grade = ColorGradeConfig(
            exposure_ev=round(ev_delta, 3),
            contrast=round(contrast_ratio, 3),
            saturation=1.0,
            temperature=round(temp_deg, 2),
            tint=round(tint_deg, 2),
        )

        residual_luma = abs(ref_metrics.mean_luma - tgt_metrics.mean_luma)
        residual_color = math.sqrt(
            (ref_r - tgt_r) ** 2 + (ref_g - tgt_g) ** 2 + (ref_b - tgt_b) ** 2
        )

        return ShotMatchTelemetry(
            reference_clip=Path(reference_media).name,
            target_clip=Path(target_media).name,
            source_metrics=tgt_metrics,
            reference_metrics=ref_metrics,
            applied_grade=matched_grade,
            residual_luma_error=round(residual_luma, 2),
            residual_color_error=round(residual_color, 2),
        )

    @staticmethod
    def audit_color_space(media_path: Path | str) -> ColorAuditReport:
        """Inspect FFprobe stream properties to audit SDR vs HDR color space conformity."""
        p = Path(media_path).resolve()
        if not p.is_file():
            raise MediaNotFoundError(f"Media file not found: {p}")

        prober = FFprobeProber()
        asset = prober.probe_file(p)
        pv = asset.primary_video

        # Defaults
        color_space = "bt709"
        color_primaries = "bt709"
        color_transfer = "bt709"
        color_range = ColorRange.LIMITED_TV

        # Raw ffprobe inspection for color tags
        probe_cmd = [
            prober.ffprobe_bin or "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=color_space,color_primaries,color_transfer,color_range,bits_per_raw_sample",
            "-of",
            "json",
            str(p),
        ]
        try:
            res = subprocess.run(probe_cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                import json
                data = json.loads(res.stdout)
                streams = data.get("streams", [])
                if streams:
                    s = streams[0]
                    color_space = s.get("color_space") or "bt709"
                    color_primaries = s.get("color_primaries") or "bt709"
                    color_transfer = s.get("color_transfer") or "bt709"
                    rng = s.get("color_range")
                    if rng == "pc":
                        color_range = ColorRange.FULL_PC
                    elif rng == "tv":
                        color_range = ColorRange.LIMITED_TV
        except Exception:
            pass

        # Identify HDR vs SDR
        is_hdr = any(hdr_tag in color_transfer.lower() for hdr_tag in ("smpte2084", "arib-std-b67", "pq", "hlg"))
        standard = ColorStandard.REC709
        if is_hdr:
            standard = ColorStandard.REC2020_HDR_PQ if "smpte2084" in color_transfer.lower() else ColorStandard.REC2020_HDR_HLG
        elif "bt2020" in color_space.lower():
            standard = ColorStandard.REC709  # Wide gamut SDR
        elif "srgb" in color_space.lower() or "iec61966" in color_transfer.lower():
            standard = ColorStandard.SRGB

        is_sdr_rec709 = (not is_hdr) and ("709" in color_space or "srgb" in color_space or color_space == "unknown")

        warnings: List[str] = []
        recommendations: List[str] = []

        if is_hdr:
            warnings.append(
                f"File uses HDR transfer curve ({color_transfer}). Direct export to standard SDR Rec.709 "
                f"requires tone-mapping to avoid washed-out highlights."
            )
            recommendations.append("Apply tone-mapping filter (zscale / tonemap) before SDR delivery.")
        else:
            recommendations.append("Safe for standard SDR Rec.709 broadcast and web distribution.")

        meta = ColorMetadata(
            color_space=color_space,
            color_primaries=color_primaries,
            color_transfer=color_transfer,
            color_range=color_range,
            standard=standard,
            is_hdr=is_hdr,
            bit_depth=8,
        )

        return ColorAuditReport(
            file_path=str(p),
            metadata=meta,
            is_sdr_rec709_compliant=is_sdr_rec709,
            is_hdr=is_hdr,
            has_broadcast_clipping=False,
            warnings=warnings,
            recommendations=recommendations,
        )
