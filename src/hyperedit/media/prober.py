"""Professional media inspector and validator using FFprobe."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from hyperedit.core.exceptions import (
    DependencyMissingError,
    MediaNotFoundError,
    MediaProbeError,
)
from hyperedit.media.models import (
    AudioStreamDetails,
    ComprehensiveMediaAsset,
    FrameRateInfo,
    MediaType,
    MediaValidationReport,
    VideoStreamDetails,
)


def parse_fraction(frac_str: Optional[str]) -> Tuple[int, int]:
    """Safely parse rational fraction string 'NUM/DEN'."""
    if not frac_str or "/" not in frac_str:
        return (0, 1)
    try:
        num, den = map(int, frac_str.split("/"))
        return (num, den) if den != 0 else (num, 1)
    except ValueError:
        return (0, 1)


def evaluate_fps(r_str: Optional[str], avg_str: Optional[str]) -> FrameRateInfo:
    """Evaluate exact frame rate, time base, and detect Constant vs Variable Frame Rate (CFR/VFR)."""
    r_num, r_den = parse_fraction(r_str)
    avg_num, avg_den = parse_fraction(avg_str)

    r_fps = (r_num / r_den) if r_den > 0 and r_num > 0 else 0.0
    avg_fps = (avg_num / avg_den) if avg_den > 0 and avg_num > 0 else 0.0

    # Primary FPS determination
    final_fps = r_fps if r_fps > 0 else (avg_fps if avg_fps > 0 else 30.0)

    # Detect VFR if nominal and average differ by more than 0.05
    is_vfr = False
    if r_fps > 0 and avg_fps > 0:
        if abs(r_fps - avg_fps) > 0.05:
            is_vfr = True
            # For VFR media, average fps is closer to real world timing
            final_fps = avg_fps

    return FrameRateInfo(
        fps=round(final_fps, 4),
        r_frame_rate=r_str or "30/1",
        avg_frame_rate=avg_str or "30/1",
        is_vfr=is_vfr,
        time_base=f"1/{round(final_fps * 1000)}" if final_fps > 0 else "1/1000",
    )


class FFprobeProber:
    """Production-grade FFprobe inspector for video, audio, and image assets."""

    def __init__(self, ffprobe_bin: Optional[str] = None) -> None:
        self.ffprobe_bin = ffprobe_bin or shutil.which("ffprobe")

    def _ensure_ffprobe(self) -> None:
        if not self.ffprobe_bin:
            raise DependencyMissingError("ffprobe executable not found in PATH or environment.")

    def probe_file(
        self,
        file_path: Path | str,
        compute_hash: bool = True,
    ) -> ComprehensiveMediaAsset:
        """Inspect media file and return a fully populated ComprehensiveMediaAsset."""
        self._ensure_ffprobe()
        path = Path(file_path).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Media file does not exist: {path}")

        cmd = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format:stream:stream_tags:format_tags:side_data",
            "-print_format",
            "json",
            str(path),
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=20)
            if res.returncode != 0:
                err_text = res.stderr.strip() or "Unknown ffprobe error"
                raise MediaProbeError(f"Failed to probe file '{path.name}': {err_text}")
            data = json.loads(res.stdout)
        except subprocess.TimeoutExpired as e:
            raise MediaProbeError(f"ffprobe timed out while analyzing {path}") from e
        except json.JSONDecodeError as e:
            raise MediaProbeError(f"Invalid JSON from ffprobe for {path}: {e}") from e

        streams = data.get("streams", [])
        fmt = data.get("format", {})

        if not streams and not fmt:
            raise MediaProbeError(f"File contains no valid multimedia streams: {path.name}")

        video_streams: List[VideoStreamDetails] = []
        audio_streams: List[AudioStreamDetails] = []
        media_type = MediaType.UNKNOWN

        for s in streams:
            codec_type = s.get("codec_type")
            idx = int(s.get("index", 0))
            codec_name = s.get("codec_name", "unknown")

            if codec_type == "video":
                # Check if it's an image codec or motion video
                is_image_codec = codec_name in ("mjpeg", "png", "jpeg2000", "webp", "bmp", "tiff", "gif")
                w = int(s.get("width", 0))
                h = int(s.get("height", 0))
                fr_info = evaluate_fps(s.get("r_frame_rate"), s.get("avg_frame_rate"))

                # Rotation detection from stream tags or side_data
                rotation = 0
                tags = s.get("tags", {})
                if "rotate" in tags:
                    try:
                        rotation = int(tags["rotate"])
                    except ValueError:
                        pass
                for sd in s.get("side_data_list", []):
                    if "rotation" in sd:
                        rotation = int(sd["rotation"])

                # Check vertical orientation
                is_vertical = (h > w) if rotation in (0, 180) else (w > h)

                v_duration = float(s.get("duration", fmt.get("duration", 0.0)))
                nb_frames = int(s["nb_frames"]) if "nb_frames" in s and s["nb_frames"].isdigit() else None
                bit_depth = int(s.get("bits_per_raw_sample") or 8)

                video_streams.append(
                    VideoStreamDetails(
                        index=idx,
                        codec=codec_name,
                        width=max(1, w),
                        height=max(1, h),
                        aspect_ratio=s.get("display_aspect_ratio"),
                        pixel_format=s.get("pix_fmt", "yuv420p"),
                        bit_depth=bit_depth,
                        color_space=s.get("color_space"),
                        color_primaries=s.get("color_primaries"),
                        color_transfer=s.get("color_transfer"),
                        rotation_deg=rotation,
                        is_vertical=is_vertical,
                        frame_rate_info=fr_info,
                        duration_seconds=max(0.0, v_duration),
                        nb_frames=nb_frames,
                        bitrate_kbps=int(int(s["bit_rate"]) / 1000) if "bit_rate" in s and s["bit_rate"].isdigit() else None,
                    )
                )

            elif codec_type == "audio":
                sample_rate = int(s.get("sample_rate", 48000))
                channels = int(s.get("channels", 2))
                a_duration = float(s.get("duration", fmt.get("duration", 0.0)))
                bits_per_sample = int(s["bits_per_sample"]) if "bits_per_sample" in s and s["bits_per_sample"] else 16

                audio_streams.append(
                    AudioStreamDetails(
                        index=idx,
                        codec=codec_name,
                        sample_rate=sample_rate,
                        channels=channels,
                        channel_layout=s.get("channel_layout") or ("stereo" if channels == 2 else "mono"),
                        bits_per_sample=bits_per_sample,
                        duration_seconds=max(0.0, a_duration),
                        bitrate_kbps=int(int(s["bit_rate"]) / 1000) if "bit_rate" in s and s["bit_rate"].isdigit() else None,
                    )
                )

        # Classify media type
        if video_streams:
            if video_streams[0].codec in ("png", "mjpeg", "webp", "bmp", "tiff") and video_streams[0].duration_seconds == 0.0:
                media_type = MediaType.IMAGE
            else:
                media_type = MediaType.VIDEO
        elif audio_streams:
            media_type = MediaType.AUDIO

        # Hash calculation if requested
        file_hash = None
        if compute_hash:
            h_obj = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h_obj.update(chunk)
            file_hash = h_obj.hexdigest()

        asset_id = re.sub(r"[^a-zA-Z0-9_]", "_", path.stem).lower()
        stat = path.stat()

        return ComprehensiveMediaAsset(
            asset_id=asset_id,
            file_path=str(path),
            media_type=media_type,
            format_name=fmt.get("format_name", path.suffix.lstrip(".")),
            size_bytes=stat.st_size,
            duration_seconds=float(fmt.get("duration", 0.0)),
            bitrate_kbps=int(int(fmt["bit_rate"]) / 1000) if "bit_rate" in fmt and fmt["bit_rate"].isdigit() else None,
            hash_sha256=file_hash,
            file_mtime=stat.st_mtime,
            video_streams=video_streams,
            audio_streams=audio_streams,
            tags=fmt.get("tags", {}),
        )

    def validate_media(self, file_path: Path | str) -> MediaValidationReport:
        """Validate if a file is healthy, readable, and supported."""
        path = Path(file_path).resolve()
        if not path.exists():
            return MediaValidationReport(
                is_valid=False,
                error_message=f"File does not exist: {path}",
                is_corrupted=False,
                is_supported=False,
            )

        if path.stat().st_size == 0:
            return MediaValidationReport(
                is_valid=False,
                error_message="File is empty (0 bytes)",
                is_corrupted=True,
                is_supported=False,
            )

        try:
            asset = self.probe_file(path, compute_hash=False)
            warnings = []
            if asset.has_video and asset.primary_video:
                if asset.primary_video.frame_rate_info.is_vfr:
                    warnings.append("Video has Variable Frame Rate (VFR); proxy transcoding recommended.")
            if asset.has_video and not asset.has_audio:
                warnings.append("Video file has no audio streams.")

            return MediaValidationReport(
                is_valid=True,
                media_type=asset.media_type,
                is_corrupted=False,
                is_supported=True,
                warnings=warnings,
            )
        except MediaProbeError as e:
            return MediaValidationReport(
                is_valid=False,
                error_message=str(e),
                is_corrupted=True,
                is_supported=False,
            )
        except Exception as e:
            return MediaValidationReport(
                is_valid=False,
                error_message=f"Unexpected validation failure: {e}",
                is_corrupted=True,
                is_supported=False,
            )
