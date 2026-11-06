"""Acoustic signal telemetry, volume detection and silence analysis via FFmpeg."""

from pathlib import Path
import re
import shutil
import subprocess
from typing import List, Optional

from hyperedit.core.exceptions import DependencyMissingError, MediaNotFoundError, RenderExecutionError
from hyperedit.media.models import AudioSignalMetrics, SilenceInterval


class AudioSignalAnalyzer:
    """Analyzes audio volume levels, clipping, and silence intervals using FFmpeg."""

    def __init__(self, ffmpeg_bin: Optional[str] = None) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")

    def analyze_signal(
        self,
        file_path: Path | str,
        silence_threshold_db: float = -35.0,
        min_silence_duration: float = 0.5,
    ) -> AudioSignalMetrics:
        """Run volumedetect and silencedetect to produce AudioSignalMetrics."""
        path = Path(file_path).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Audio/Video file not found: {path}")
        if not self.ffmpeg_bin:
            raise DependencyMissingError("ffmpeg executable not found in PATH.")

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(path),
            "-af",
            f"volumedetect,silencedetect=noise={silence_threshold_db}dB:d={min_silence_duration}",
            "-f",
            "null",
            "-",
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
            stderr = res.stderr or ""
        except subprocess.TimeoutExpired as e:
            raise RenderExecutionError(f"Audio analysis timed out for {path}") from e

        # Parse volumedetect
        # e.g.: [Parsed_volumedetect_0 @ ...] max_volume: -2.3 dB
        # e.g.: [Parsed_volumedetect_0 @ ...] mean_volume: -24.1 dB
        max_vol_match = re.search(r"max_volume:\s*([-+]?\d*\.?\d+)\s*dB", stderr)
        mean_vol_match = re.search(r"mean_volume:\s*([-+]?\d*\.?\d+)\s*dB", stderr)

        max_vol = float(max_vol_match.group(1)) if max_vol_match else 0.0
        mean_vol = float(mean_vol_match.group(1)) if mean_vol_match else -96.0
        dynamic_range = abs(max_vol - mean_vol)
        has_clipping = max_vol >= 0.0

        # Parse silencedetect
        # e.g.: [silencedetect @ ...] silence_start: 3.456
        # e.g.: [silencedetect @ ...] silence_end: 5.123 | silence_duration: 1.667
        silence_intervals: List[SilenceInterval] = []
        current_start: Optional[float] = None

        for line in stderr.splitlines():
            start_m = re.search(r"silence_start:\s*([-+]?\d*\.?\d+)", line)
            if start_m:
                current_start = float(start_m.group(1))
                continue

            end_m = re.search(
                r"silence_end:\s*([-+]?\d*\.?\d+)(?:\s*\|\s*silence_duration:\s*([-+]?\d*\.?\d+))?",
                line,
            )
            if end_m and current_start is not None:
                end_time = float(end_m.group(1))
                duration = float(end_m.group(2)) if end_m.group(2) else max(0.0, end_time - current_start)
                silence_intervals.append(
                    SilenceInterval(
                        start_seconds=current_start,
                        end_seconds=end_time,
                        duration_seconds=duration,
                    )
                )
                current_start = None

        return AudioSignalMetrics(
            peak_db=max_vol,
            mean_volume_db=mean_vol,
            max_volume_db=max_vol,
            dynamic_range_db=round(dynamic_range, 2),
            has_clipping=has_clipping,
            silence_intervals=silence_intervals,
        )

