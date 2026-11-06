"""Real signal-based BPM detection, onset analysis, and beat grid tracking."""

import math
from pathlib import Path
import shutil
import struct
import subprocess
from typing import List, Optional, Tuple

from hyperedit.audio.models import BeatInfo
from hyperedit.core.exceptions import DependencyMissingError, MediaNotFoundError, RenderExecutionError
from hyperedit.core.models.timeline import Marker


class BeatTracker:
    """Acoustic signal beat tracker utilizing short-time energy flux and autocorrelation."""

    def __init__(self, ffmpeg_bin: Optional[str] = None) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")

    def _ensure_ffmpeg(self) -> None:
        if not self.ffmpeg_bin:
            raise DependencyMissingError("ffmpeg executable not found in PATH.")

    def stream_pcm_samples(
        self,
        audio_or_video_file: Path | str,
        sample_rate: int = 22050,
    ) -> Tuple[List[int], float]:
        """Stream decoded 16-bit mono PCM samples via FFmpeg stdout without intermediate files."""
        self._ensure_ffmpeg()
        path = Path(audio_or_video_file).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Audio/Video file not found: {path}")

        cmd = [
            self.ffmpeg_bin,
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "-",
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, check=False, timeout=60)
            if proc.returncode != 0:
                raise RenderExecutionError(f"Failed to stream audio PCM: {proc.stderr}")
            raw_bytes = proc.stdout
        except subprocess.TimeoutExpired as e:
            raise RenderExecutionError(f"Audio PCM streaming timed out for {path}") from e

        n_samples = len(raw_bytes) // 2
        if n_samples == 0:
            return [], 0.0

        samples = list(struct.unpack(f"<{n_samples}h", raw_bytes))
        duration_sec = n_samples / sample_rate
        return samples, duration_sec

    def analyze_beats(
        self,
        audio_file: Path | str,
        bpm_hint: Optional[float] = None,
        manual_override: Optional[float] = None,
        hop_sec: float = 0.01,
    ) -> BeatInfo:
        """Perform real signal analysis on audio file to detect tempo, beats, and transient onsets."""
        samples, duration_sec = self.stream_pcm_samples(audio_file)
        if not samples or duration_sec < 0.5:
            return BeatInfo(
                bpm=120.0,
                confidence=0.0,
                beat_interval_sec=0.5,
                beat_timestamps=[],
                onset_timestamps=[],
            )

        sample_rate = 22050
        hop_samples = int(sample_rate * hop_sec)

        # 1. Calculate Short-Time RMS Energy Envelope
        energies: List[float] = []
        for i in range(0, len(samples) - hop_samples, hop_samples):
            window = samples[i : i + hop_samples]
            sq_sum = sum(s * s for s in window)
            rms = math.sqrt(sq_sum / len(window))
            energies.append(rms)

        # 2. Compute Half-Wave Rectified Spectral Flux (Novelty Curve)
        novelty: List[float] = []
        for i in range(len(energies)):
            diff = energies[i] - energies[i - 1] if i > 0 else 0.0
            novelty.append(max(0.0, diff))

        # 3. Detect Transient Onsets (Local Peaks Above Dynamic Moving Threshold)
        onsets: List[float] = []
        mean_nov = sum(novelty) / max(1, len(novelty))
        threshold = mean_nov * 1.5

        for i in range(1, len(novelty) - 1):
            if novelty[i] > threshold and novelty[i] >= novelty[i - 1] and novelty[i] >= novelty[i + 1]:
                t_onset = round(i * hop_sec, 4)
                # Enforce minimum refractory interval (50ms) between onsets
                if not onsets or (t_onset - onsets[-1]) >= 0.05:
                    onsets.append(t_onset)

        # 4. Tempo Estimation via Autocorrelation
        if manual_override and manual_override > 0:
            detected_bpm = manual_override
            confidence = 1.0
            beat_interval = 60.0 / detected_bpm
        else:
            min_lag = int(0.27 / hop_sec)   # ~220 BPM max
            max_lag = int(1.33 / hop_sec)   # ~45 BPM min

            best_lag = None
            best_corr = -1.0
            all_corrs = []

            for lag in range(min_lag, min(max_lag, len(novelty) // 2)):
                corr = 0.0
                weight = 1.0

                # If bpm_hint is supplied, apply Gaussian weighting
                if bpm_hint and bpm_hint > 0:
                    hint_lag = (60.0 / bpm_hint) / hop_sec
                    weight = math.exp(-0.5 * ((lag - hint_lag) / 10.0) ** 2)

                for j in range(lag, len(novelty)):
                    corr += novelty[j] * novelty[j - lag]

                weighted_corr = corr * (weight if bpm_hint else 1.0)
                all_corrs.append(corr)

                if weighted_corr > best_corr:
                    best_corr = weighted_corr
                    best_lag = lag

            if best_lag and best_lag > 0:
                beat_interval = best_lag * hop_sec
                detected_bpm = round(60.0 / beat_interval, 2)
                # Compute confidence ratio
                median_corr = sorted(all_corrs)[len(all_corrs) // 2] if all_corrs else 1.0
                confidence = min(1.0, max(0.2, (best_corr / max(1.0, median_corr)) / 4.0))
            else:
                detected_bpm = 120.0
                beat_interval = 0.5
                confidence = 0.1

        # 5. Determine Beat Phase Alignment (First Downbeat Offset)
        # Find offset phi in [0, beat_interval) that maximizes novelty alignment
        phase_steps = 20
        best_phi = 0.0
        best_phase_score = -1.0

        for p_idx in range(phase_steps):
            phi = (p_idx / phase_steps) * beat_interval
            score = 0.0
            current_t = phi
            while current_t < duration_sec:
                idx = int(current_t / hop_sec)
                if idx < len(novelty):
                    score += novelty[idx]
                current_t += beat_interval

            if score > best_phase_score:
                best_phase_score = score
                best_phi = phi

        # 6. Generate Complete Beat Timestamps
        beat_timestamps: List[float] = []
        cur = best_phi
        while cur < duration_sec:
            beat_timestamps.append(round(cur, 4))
            cur += beat_interval

        return BeatInfo(
            bpm=detected_bpm,
            confidence=round(confidence, 2),
            beat_interval_sec=round(beat_interval, 4),
            beat_timestamps=beat_timestamps,
            onset_timestamps=onsets,
            manual_bpm_override=manual_override,
        )

    def generate_timeline_markers(
        self,
        beat_info: BeatInfo,
        fps: float = 30.0,
        marker_color: str = "#FF00AA",
    ) -> List[Marker]:
        """Convert detected beat timestamps into project Timeline markers."""
        markers: List[Marker] = []
        for idx, t in enumerate(beat_info.beat_timestamps, start=1):
            frame = int(round(t * fps))
            markers.append(
                Marker(
                    marker_id=f"beat_{idx:03d}",
                    frame=frame,
                    name=f"Beat {idx} ({beat_info.bpm:.0f} BPM)",
                    color=marker_color,
                    comment=f"Beat pulse at t={t:.3f}s",
                )
            )
        return markers

