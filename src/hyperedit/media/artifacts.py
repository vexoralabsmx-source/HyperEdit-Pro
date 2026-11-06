"""Artifact generation engine: thumbnails, contact sheets, waveforms, proxies, and audio extraction."""

from pathlib import Path
import shutil
import subprocess
from typing import Optional

from hyperedit.core.exceptions import (
    DependencyMissingError,
    MediaNotFoundError,
    RenderExecutionError,
)


class MediaArtifactGenerator:
    """Produces derived visual and acoustic assets using FFmpeg."""

    def __init__(self, ffmpeg_bin: Optional[str] = None) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")

    def _ensure_ffmpeg(self) -> None:
        if not self.ffmpeg_bin:
            raise DependencyMissingError("ffmpeg binary not found in PATH.")

    def extract_thumbnail(
        self,
        media_file: Path | str,
        output_path: Path | str,
        timestamp_sec: float = 0.0,
        width: int = 480,
    ) -> Path:
        """Extract a single representative frame image."""
        self._ensure_ffmpeg()
        src = Path(media_file).resolve()
        dst = Path(output_path).resolve()
        if not src.is_file():
            raise MediaNotFoundError(f"Media file not found: {src}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-ss",
            f"{max(0.0, timestamp_sec):.3f}",
            "-i",
            str(src),
            "-vf",
            f"scale={width}:-1",
            "-vframes",
            "1",
            str(dst),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise RenderExecutionError(f"Thumbnail extraction failed: {res.stderr}")
        return dst

    def generate_contact_sheet(
        self,
        media_file: Path | str,
        output_path: Path | str,
        duration_seconds: float = 1.0,
        cols: int = 3,
        rows: int = 3,
        tile_width: int = 320,
    ) -> Path:
        """Generate a mosaic storyboard grid (e.g. 3x3) across the video duration."""
        self._ensure_ffmpeg()
        src = Path(media_file).resolve()
        dst = Path(output_path).resolve()
        if not src.is_file():
            raise MediaNotFoundError(f"Media file not found: {src}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        total_tiles = cols * rows
        safe_duration = max(0.5, duration_seconds)
        fps_rate = total_tiles / safe_duration

        filter_str = f"fps={fps_rate:.4f},scale={tile_width}:-1,tile={cols}x{rows}"

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(src),
            "-vf",
            filter_str,
            "-frames:v",
            "1",
            str(dst),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise RenderExecutionError(f"Contact sheet generation failed: {res.stderr}")
        return dst

    def generate_waveform(
        self,
        media_file: Path | str,
        output_path: Path | str,
        width: int = 1920,
        height: int = 240,
        color: str = "0x00FF88",
    ) -> Path:
        """Generate audio waveform PNG using FFmpeg showwavespic."""
        self._ensure_ffmpeg()
        src = Path(media_file).resolve()
        dst = Path(output_path).resolve()
        if not src.is_file():
            raise MediaNotFoundError(f"Media file not found: {src}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(src),
            "-filter_complex",
            f"aformat=channel_layouts=mono,showwavespic=s={width}x{height}:colors={color}",
            "-frames:v",
            "1",
            str(dst),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise RenderExecutionError(f"Waveform generation failed: {res.stderr}")
        return dst

    def create_proxy(
        self,
        media_file: Path | str,
        output_path: Path | str,
        scale: str = "720p",
        crf: int = 24,
    ) -> Path:
        """Transcode a fast, responsive editing proxy."""
        self._ensure_ffmpeg()
        src = Path(media_file).resolve()
        dst = Path(output_path).resolve()
        if not src.is_file():
            raise MediaNotFoundError(f"Media file not found: {src}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        scale_map = {
            "720p": "scale=1280:-2",
            "540p": "scale=960:-2",
            "360p": "scale=640:-2",
        }
        scale_filter = scale_map.get(scale, "scale=1280:-2")

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(src),
            "-vf",
            scale_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(crf),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(dst),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise RenderExecutionError(f"Proxy generation failed: {res.stderr}")
        return dst

    def extract_audio(
        self,
        media_file: Path | str,
        output_path: Path | str,
        format_ext: str = "wav",
        sample_rate: int = 48000,
        channels: int = 2,
    ) -> Path:
        """Extract uncompressed or lightly compressed audio stem for transcription / mixing."""
        self._ensure_ffmpeg()
        src = Path(media_file).resolve()
        dst = Path(output_path).resolve()
        if not src.is_file():
            raise MediaNotFoundError(f"Media file not found: {src}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        codec = "pcm_s16le" if format_ext == "wav" else ("flac" if format_ext == "flac" else "libmp3lame")

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(src),
            "-vn",
            "-acodec",
            codec,
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            str(dst),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise RenderExecutionError(f"Audio extraction failed: {res.stderr}")
        return dst

