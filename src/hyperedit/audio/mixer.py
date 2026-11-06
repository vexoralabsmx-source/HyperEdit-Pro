"""Professional multi-bus audio mixer, sidechain ducking, and loudness normalization."""

from pathlib import Path
import re
import shutil
import subprocess
from typing import Optional, Union

from hyperedit.audio.models import (
    STANDARD_LOUDNESS_PROFILES,
    LoudnessMeasurement,
    LoudnessProfile,
)
from hyperedit.core.exceptions import (
    DependencyMissingError,
    MediaNotFoundError,
    RenderExecutionError,
)
from hyperedit.core.models.project import Project
from hyperedit.core.models.timeline import TrackKind


class AudioMixer:
    """Multi-bus audio mixing engine with sidechain ducking and EBU R128 loudness processing."""

    def __init__(self, ffmpeg_bin: Optional[str] = None) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")

    def _ensure_ffmpeg(self) -> None:
        if not self.ffmpeg_bin:
            raise DependencyMissingError("ffmpeg executable not found in PATH.")

    def measure_loudness(
        self,
        audio_or_video_file: Path | str,
        target_profile: Optional[Union[LoudnessProfile, str]] = None,
    ) -> LoudnessMeasurement:
        """Measure acoustic integrated loudness, true peak, and LRA via FFmpeg ebur128 filter."""
        self._ensure_ffmpeg()
        path = Path(audio_or_video_file).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Audio/video file not found: {path}")

        profile = self._resolve_profile(target_profile or "youtube")

        cmd = [
            self.ffmpeg_bin,
            "-v",
            "info",
            "-i",
            str(path),
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
            stderr = proc.stderr or ""
        except subprocess.TimeoutExpired as e:
            raise RenderExecutionError(f"Loudness measurement timed out for {path}") from e

        # Regex parse EBU R128 summary block
        i_match = re.search(r"Integrated loudness:\s+I:\s+([-\d\.]+)\s+LUFS", stderr)
        thresh_match = re.search(r"Integrated loudness:.*?Threshold:\s+([-\d\.]+)\s+LUFS", stderr, re.DOTALL)
        lra_match = re.search(r"Loudness range:\s+LRA:\s+([-\d\.]+)\s+LU", stderr)
        tp_match = re.search(r"True peak:\s+Peak:\s+([-\d\.]+)\s+dBFS", stderr)

        if not i_match or not tp_match:
            # Fallback if audio is completely silent or no summary printed
            return LoudnessMeasurement(
                integrated_lufs=-70.0,
                true_peak_dbfs=-70.0,
                lra=0.0,
                threshold_lufs=-70.0,
                target_lufs=profile.target_i,
                deviation_lu=-70.0 - profile.target_i,
                is_compliant=False,
            )

        integrated_lufs = float(i_match.group(1))
        thresh_lufs = float(thresh_match.group(1)) if thresh_match else -70.0
        lra = float(lra_match.group(1)) if lra_match else 0.0
        true_peak_dbfs = float(tp_match.group(1))

        deviation = round(integrated_lufs - profile.target_i, 2)
        is_compliant = abs(deviation) <= 1.0 and true_peak_dbfs <= (profile.target_tp + 0.5)

        return LoudnessMeasurement(
            integrated_lufs=integrated_lufs,
            true_peak_dbfs=true_peak_dbfs,
            lra=lra,
            threshold_lufs=thresh_lufs,
            target_lufs=profile.target_i,
            deviation_lu=deviation,
            is_compliant=is_compliant,
        )

    def normalize_loudness(
        self,
        input_file: Path | str,
        output_file: Path | str,
        profile: Union[LoudnessProfile, str] = "youtube",
        sample_rate: int = 48000,
    ) -> Path:
        """Apply EBU R128 / ITU-R BS.1770 loudness normalization filter (loudnorm)."""
        self._ensure_ffmpeg()
        in_path = Path(input_file).resolve()
        if not in_path.is_file():
            raise MediaNotFoundError(f"Input audio file not found: {in_path}")

        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        prof = self._resolve_profile(profile)

        # Build loudnorm filter string
        af_filter = f"loudnorm=I={prof.target_i}:LRA={prof.target_lra}:TP={prof.target_tp}"

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-v",
            "error",
            "-i",
            str(in_path),
            "-af",
            af_filter,
            "-ar",
            str(sample_rate),
            str(out_path),
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RenderExecutionError(f"Loudness normalization failed: {proc.stderr}")

        return out_path

    def apply_sidechain_ducking(
        self,
        music_file: Path | str,
        dialogue_file: Path | str,
        output_file: Path | str,
        threshold_db: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 20.0,
        release_ms: float = 250.0,
        makeup_db: float = 0.0,
        mix_with_dialogue: bool = False,
        sample_rate: int = 48000,
    ) -> Path:
        """Compress/duck background music when speech/dialogue is detected on the sidechain input.

        Args:
            music_file: Background music audio track (Input 0).
            dialogue_file: Dialogue/voiceover trigger track (Input 1).
            output_file: Target output audio file.
            threshold_db: Trigger threshold in dBFS (e.g. -20 dBFS).
            ratio: Compression ratio when voice is present (e.g. 4.0 to 8.0).
            attack_ms: Attack time in ms to dip music volume.
            release_ms: Release time in ms to recover music volume after voice ends.
            makeup_db: Makeup gain in dB.
            mix_with_dialogue: If True, output combined music + dialogue mix; if False, output ducked music only.
            sample_rate: Master sample rate (default 48000 Hz).
        """
        self._ensure_ffmpeg()
        m_path = Path(music_file).resolve()
        d_path = Path(dialogue_file).resolve()

        if not m_path.is_file():
            raise MediaNotFoundError(f"Music file not found: {m_path}")
        if not d_path.is_file():
            raise MediaNotFoundError(f"Dialogue file not found: {d_path}")

        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert threshold_db to linear amplitude for FFmpeg sidechaincompress
        # FFmpeg threshold range: 0.000976563 to 1.0 (default 0.125 ~ -18 dBFS)
        threshold_linear = max(0.001, min(1.0, 10.0 ** (threshold_db / 20.0)))
        makeup_linear = max(1.0, min(64.0, 10.0 ** (makeup_db / 20.0)))

        # Build filtergraph:
        # Pad dialogue with silence so sidechain doesn't truncate music prematurely
        if mix_with_dialogue:
            filtergraph = (
                f"[1:a]asplit=2[v_sc][v_mix];"
                f"[v_sc]apad[sc_pad];"
                f"[0:a][sc_pad]sidechaincompress=threshold={threshold_linear:.4f}:"
                f"ratio={ratio:.1f}:attack={attack_ms:.1f}:release={release_ms:.1f}:makeup={makeup_linear:.2f}[ducked];"
                f"[ducked][v_mix]amix=inputs=2:duration=first:dropout_transition=2[out]"
            )
        else:
            filtergraph = (
                f"[1:a]apad[sc_pad];"
                f"[0:a][sc_pad]sidechaincompress=threshold={threshold_linear:.4f}:"
                f"ratio={ratio:.1f}:attack={attack_ms:.1f}:release={release_ms:.1f}:makeup={makeup_linear:.2f}[out]"
            )

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-v",
            "error",
            "-i",
            str(m_path),
            "-i",
            str(d_path),
            "-filter_complex",
            filtergraph,
            "-map",
            "[out]",
            "-ar",
            str(sample_rate),
            str(out_path),
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RenderExecutionError(f"Sidechain ducking render failed: {proc.stderr}")

        return out_path

    def mix_timeline_audio(
        self,
        project: Project,
        output_file: Path | str,
        target_profile: Optional[Union[LoudnessProfile, str]] = None,
        sample_rate: int = 48000,
    ) -> Path:
        """Mix all timeline audio tracks into a master audio stem with ducking and loudness compliance."""
        self._ensure_ffmpeg()
        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        audio_tracks = [t for t in project.timeline.tracks if t.kind == TrackKind.AUDIO and not t.muted]
        if not audio_tracks:
            # Generate 1 second of silence if no audio tracks exist
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r={sample_rate}:cl=stereo",
                "-t",
                "1",
                str(out_path),
            ]
            subprocess.run(cmd, check=True)
            return out_path

        fps = project.fps

        # Build FFmpeg command inputs and filtergraph
        input_files: list[str] = []
        filter_chains: list[str] = []
        track_output_labels: list[str] = []

        # Find any ducking relationships
        ducking_configs = {}
        for track in audio_tracks:
            if track.mix_config and track.mix_config.ducking:
                ducking_configs[track.track_id] = track.mix_config.ducking

        for track_idx, track in enumerate(audio_tracks):
            track.sort_clips()
            if not track.clips:
                continue

            clip_labels: list[str] = []
            for clip_idx, clip in enumerate(track.clips):
                asset = project.media_pool.get_asset(clip.asset_id)
                if not asset or not asset.file_path:
                    continue

                input_idx = len(input_files)
                input_files.append(str(Path(asset.file_path).resolve()))

                in_sec = clip.in_frame / fps
                out_sec = clip.out_frame / fps
                delay_ms = int(round((clip.timeline_start_frame / fps) * 1000.0))

                clip_vol_linear = 10.0 ** (clip.volume_db / 20.0)

                # Trim, delay, volume
                clip_label = f"trk{track_idx}_clp{clip_idx}"
                filter_chains.append(
                    f"[{input_idx}:a]atrim=start={in_sec:.4f}:end={out_sec:.4f},"
                    f"asetpts=PTS-STARTPTS,adelay={delay_ms}|{delay_ms},"
                    f"volume={clip_vol_linear:.4f}[{clip_label}]"
                )
                clip_labels.append(f"[{clip_label}]")

            if not clip_labels:
                continue

            # Mix clips on this track
            raw_track_label = f"track_{track.track_id}_raw"
            if len(clip_labels) == 1:
                filter_chains.append(f"{clip_labels[0]}anull[{raw_track_label}]")
            else:
                inputs_str = "".join(clip_labels)
                filter_chains.append(
                    f"{inputs_str}amix=inputs={len(clip_labels)}:dropout_transition=0[{raw_track_label}]"
                )

            # Apply track fader volume and pan
            track_vol_db = track.mix_config.volume_db if track.mix_config else 0.0
            track_vol_linear = 10.0 ** (track_vol_db / 20.0)
            track_final_label = f"track_{track.track_id}"
            filter_chains.append(f"[{raw_track_label}]volume={track_vol_linear:.4f}[{track_final_label}]")
            track_output_labels.append(track_final_label)

        if not track_output_labels:
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r={sample_rate}:cl=stereo",
                "-t",
                "1",
                str(out_path),
            ]
            subprocess.run(cmd, check=True)
            return out_path

        # Handle ducking if configured
        for music_track_id, ducking in ducking_configs.items():
            trigger_id = ducking.trigger_track_id
            music_label = f"track_{music_track_id}"
            trigger_label = f"track_{trigger_id}"

            if music_label in track_output_labels and trigger_label in track_output_labels:
                t_linear = max(0.001, min(1.0, 10.0 ** (ducking.threshold_db / 20.0)))
                ducked_label = f"track_{music_track_id}_ducked"

                # Dialogue split & sidechain
                filter_chains.append(f"[{trigger_label}]asplit=2[{trigger_label}_sc][{trigger_label}_thru]")
                filter_chains.append(f"[{trigger_label}_sc]apad[{trigger_label}_pad]")
                filter_chains.append(
                    f"[{music_label}][{trigger_label}_pad]sidechaincompress="
                    f"threshold={t_linear:.4f}:ratio=4.0:attack={ducking.attack_ms:.1f}:"
                    f"release={ducking.release_ms:.1f}[{ducked_label}]"
                )

                # Replace music and trigger labels in final mix
                track_output_labels.remove(music_label)
                track_output_labels.remove(trigger_label)
                track_output_labels.append(ducked_label)
                track_output_labels.append(f"{trigger_label}_thru")

        # Master mix
        master_inputs = "".join(f"[{lbl}]" for lbl in track_output_labels)
        if len(track_output_labels) == 1:
            filter_chains.append(f"{master_inputs}anull[master_raw]")
        else:
            filter_chains.append(
                f"{master_inputs}amix=inputs={len(track_output_labels)}:dropout_transition=0[master_raw]"
            )

        # Master loudness normalization
        if target_profile:
            prof = self._resolve_profile(target_profile)
            filter_chains.append(
                f"[master_raw]loudnorm=I={prof.target_i}:LRA={prof.target_lra}:TP={prof.target_tp}[master_out]"
            )
            final_map = "[master_out]"
        else:
            final_map = "[master_raw]"

        cmd = [self.ffmpeg_bin, "-y", "-v", "error"]
        for inp in input_files:
            cmd.extend(["-i", inp])

        full_filtergraph = ";".join(filter_chains)
        cmd.extend([
            "-filter_complex",
            full_filtergraph,
            "-map",
            final_map,
            "-ar",
            str(sample_rate),
            str(out_path),
        ])

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RenderExecutionError(f"Multi-track audio mix failed: {proc.stderr}")

        return out_path

    def _resolve_profile(self, profile: Union[LoudnessProfile, str]) -> LoudnessProfile:
        if isinstance(profile, LoudnessProfile):
            return profile
        key = str(profile).lower()
        if key in STANDARD_LOUDNESS_PROFILES:
            return STANDARD_LOUDNESS_PROFILES[key]
        return STANDARD_LOUDNESS_PROFILES["youtube"]

