"""Comprehensive test suite for HyperEdit Pro Audio Engineering & Beat Sync (Stage 4)."""

import json
import math
from pathlib import Path
import struct
import wave
import pytest
from click.testing import CliRunner

from hyperedit.audio.beat_sync import BeatSynchronizer
from hyperedit.audio.beat_tracker import BeatTracker
from hyperedit.audio.mixer import AudioMixer
from hyperedit.cli.main import cli
from hyperedit.core.models.audio import AudioMixConfig, DuckingConfig
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Clip, Timeline, Track, TrackKind


@pytest.fixture
def synthetic_beat_audio(tmp_path: Path) -> Path:
    """Generate exact 120.0 BPM audio fixture with 50ms sine bursts every 0.5s (8 beats)."""
    wav_path = tmp_path / "metronome_120bpm.wav"
    sample_rate = 22050
    duration_sec = 4.0
    bpm = 120.0
    beat_interval = 60.0 / bpm  # 0.500 s

    total_samples = int(sample_rate * duration_sec)
    samples = [0] * total_samples

    # Write 8 beats at t = 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5 seconds
    burst_duration = 0.050  # 50ms burst
    burst_samples = int(sample_rate * burst_duration)
    freq = 880.0  # Concert A5 click

    for beat_idx in range(8):
        start_sample = int(beat_idx * beat_interval * sample_rate)
        for s in range(burst_samples):
            if start_sample + s < total_samples:
                # 880Hz percussive click with sharp transient attack
                t = s / sample_rate
                env = math.exp(-s / (sample_rate * 0.010))
                val = int(30000 * env * math.sin(2.0 * math.pi * freq * t))
                samples[start_sample + s] = val

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframes(raw)

    return wav_path


@pytest.fixture
def speech_and_music_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    """Generate background music tone and intermittent voiceover track."""
    music_path = tmp_path / "background_music.wav"
    speech_path = tmp_path / "dialogue_stem.wav"
    sample_rate = 22050
    duration = 4.0
    total_samples = int(sample_rate * duration)

    # 1. Background Music: Continuous 440Hz warm pad
    music_samples = [
        int(16000 * math.sin(2.0 * math.pi * 440.0 * (i / sample_rate)))
        for i in range(total_samples)
    ]
    with wave.open(str(music_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(music_samples)}h", *music_samples))

    # 2. Dialogue Stem: Speech active only from t=1.0s to 3.0s
    speech_samples = [0] * total_samples
    t_start = int(1.0 * sample_rate)
    t_end = int(3.0 * sample_rate)
    for i in range(t_start, t_end):
        speech_samples[i] = int(24000 * math.sin(2.0 * math.pi * 880.0 * (i / sample_rate)))

    with wave.open(str(speech_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(speech_samples)}h", *speech_samples))

    return music_path, speech_path


def test_real_signal_beat_detection(synthetic_beat_audio: Path) -> None:
    """Verify acoustic signal beat tracker accurately calculates 120 BPM and measures timestamp deviation."""
    tracker = BeatTracker()
    beat_info = tracker.analyze_beats(synthetic_beat_audio, bpm_hint=120.0)

    # Assert tempo is 120 BPM (+/- 1 BPM tolerance)
    assert abs(beat_info.bpm - 120.0) <= 1.0, f"Expected ~120 BPM, detected {beat_info.bpm}"
    assert beat_info.confidence >= 0.7
    assert len(beat_info.beat_timestamps) >= 7

    # Measure exact millisecond deviations from ground truth (k * 0.500s)
    deviations_ms = []
    for k in range(len(beat_info.beat_timestamps)):
        expected_t = k * 0.500
        detected_t = beat_info.beat_timestamps[k]
        diff_ms = abs(detected_t - expected_t) * 1000.0
        deviations_ms.append(diff_ms)

    mean_dev_ms = sum(deviations_ms) / len(deviations_ms)
    max_dev_ms = max(deviations_ms)

    # The beat tracker must achieve sub-15ms mean precision on clean metronome audio
    assert mean_dev_ms < 15.0, f"Mean deviation too high: {mean_dev_ms:.2f} ms"
    assert max_dev_ms < 30.0, f"Max deviation too high: {max_dev_ms:.2f} ms"


def test_timeline_beat_markers_generation(synthetic_beat_audio: Path) -> None:
    """Verify beat markers are correctly converted and placed at discrete frame indices."""
    tracker = BeatTracker()
    beat_info = tracker.analyze_beats(synthetic_beat_audio, bpm_hint=120.0)

    timeline = Timeline(tracks=[])
    synchronizer = BeatSynchronizer(default_fps=30.0)
    added = synchronizer.add_beat_markers(timeline, beat_info, fps=30.0, marker_color="#00FFCC")

    assert added == len(beat_info.beat_timestamps)
    assert len(timeline.markers) == added
    assert timeline.markers[0].frame == 0
    # At 30 fps, 0.5s beat interval corresponds to frame 15, 30, 45, etc.
    assert timeline.markers[1].frame == 15
    assert timeline.markers[2].frame == 30
    assert timeline.markers[0].color == "#00FFCC"


def test_snap_cuts_to_beats_with_telemetry(synthetic_beat_audio: Path) -> None:
    """Verify intelligent cut snapping shifts edit boundaries to nearest beats and records deviation report."""
    tracker = BeatTracker()
    beat_info = tracker.analyze_beats(synthetic_beat_audio, bpm_hint=120.0)

    # Create timeline with intentional slight cut misalignments at 30 fps:
    # Beat 1 is at frame 15 (0.500s). Cut 1 is at frame 17 (shift: -2 frames, -66.7ms).
    # Beat 2 is at frame 30 (1.000s). Cut 2 is at frame 28 (shift: +2 frames, +66.7ms).
    v1 = Track(
        track_id="V1",
        kind=TrackKind.VIDEO,
        clips=[
            Clip(clip_id="c1", asset_id="a1", in_frame=0, out_frame=17, timeline_start_frame=0),
            Clip(clip_id="c2", asset_id="a2", in_frame=0, out_frame=11, timeline_start_frame=17),
            Clip(clip_id="c3", asset_id="a3", in_frame=0, out_frame=20, timeline_start_frame=28),
        ],
    )
    timeline = Timeline(tracks=[v1])

    synchronizer = BeatSynchronizer(default_fps=30.0)
    report = synchronizer.snap_cuts_to_beats(
        timeline=timeline,
        track_id="V1",
        beats=beat_info,
        max_shift_frames=5,
        mode="ripple",
        fps=30.0,
    )

    assert report.total_cuts_evaluated == 2
    assert report.cuts_snapped == 2
    assert report.max_shift_allowed_frames == 5
    assert len(report.details) == 2

    # Check cut 1 snapped to frame 15
    d1 = report.details[0]
    assert d1.original_frame == 17
    assert d1.snapped_frame == 15
    assert d1.shift_frames == -2
    assert abs(d1.shift_ms - (-66.67)) < 1.0

    # Verify that clip 1 out_frame was updated
    assert v1.clips[0].out_frame == 15
    assert v1.clips[0].timeline_end_frame == 15

    # Check mean and max shift telemetry
    assert report.mean_shift_ms > 0.0
    assert report.max_shift_ms > 0.0


def test_sidechain_ducking_attenuation(
    speech_and_music_fixtures: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Verify real FFmpeg sidechaincompress ducks music when dialogue is present."""
    music_path, speech_path = speech_and_music_fixtures
    ducked_output = tmp_path / "ducked_music.wav"

    mixer = AudioMixer()
    out = mixer.apply_sidechain_ducking(
        music_file=music_path,
        dialogue_file=speech_path,
        output_file=ducked_output,
        threshold_db=-20.0,
        ratio=6.0,
        attack_ms=20.0,
        release_ms=200.0,
        mix_with_dialogue=False,
    )

    assert out.is_file()
    assert out.stat().st_size > 1000

    # Measure PCM RMS during un-ducked window (t=0.2 to 0.8s) vs ducked window (t=1.5 to 2.5s)
    with wave.open(str(out), "rb") as wf:
        n_samples = wf.getnframes()
        sr = wf.getframerate()
        raw = wf.readframes(n_samples)
        samples = list(struct.unpack(f"<{n_samples}h", raw))

    # Unducked slice (t = 0.2s to 0.8s)
    unducked_slice = samples[int(0.2 * sr) : int(0.8 * sr)]
    rms_unducked = math.sqrt(sum(s * s for s in unducked_slice) / len(unducked_slice))

    # Ducked slice during dialogue (t = 1.5s to 2.5s)
    ducked_slice = samples[int(1.5 * sr) : int(2.5 * sr)]
    rms_ducked = math.sqrt(sum(s * s for s in ducked_slice) / len(ducked_slice))

    # Verify that sidechain compression attenuated the signal by at least 35%
    attenuation_ratio = rms_ducked / rms_unducked
    assert attenuation_ratio < 0.65, (
        f"Music was not significantly ducked during speech: ratio={attenuation_ratio:.2f}"
    )


def test_loudness_measurement_and_normalization(tmp_path: Path) -> None:
    """Verify EBU R128 loudness measurement and loudnorm normalization to -14 LUFS (YouTube)."""
    # Create a quiet test audio fixture (~ -24 LUFS)
    quiet_path = tmp_path / "quiet_audio.wav"
    sample_rate = 44100
    duration = 3.0
    n_samples = int(sample_rate * duration)
    # Low amplitude sine wave
    samples = [int(1500 * math.sin(2.0 * math.pi * 1000.0 * (i / sample_rate))) for i in range(n_samples)]
    with wave.open(str(quiet_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_samples}h", *samples))

    mixer = AudioMixer()

    # Initial measurement
    initial_meas = mixer.measure_loudness(quiet_path, target_profile="youtube")
    assert initial_meas.integrated_lufs < -20.0
    assert not initial_meas.is_compliant

    # Normalize to YouTube standard (-14 LUFS)
    normalized_path = tmp_path / "normalized_youtube.wav"
    mixer.normalize_loudness(quiet_path, normalized_path, profile="youtube", sample_rate=48000)

    # Re-measure
    post_meas = mixer.measure_loudness(normalized_path, target_profile="youtube")
    # Verify compliant within +/- 1.0 LU tolerance
    assert abs(post_meas.integrated_lufs - (-14.0)) <= 1.0, (
        f"Expected -14.0 +/- 1.0 LUFS, got {post_meas.integrated_lufs}"
    )
    assert post_meas.true_peak_dbfs <= -1.0 + 0.5
    assert post_meas.is_compliant


def test_timeline_multi_track_mix(
    speech_and_music_fixtures: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Verify complete multi-bus audio mix with sidechain ducking and master stem export."""
    music_path, speech_path = speech_and_music_fixtures
    master_stem = tmp_path / "master_audio_stem.wav"

    # Construct Project with 2 audio tracks: A1 (Dialogue) and A2 (Music with ducking targeting A1)
    project = Project(
        metadata=ProjectMetadata(title="AudioMixTest"),
        settings=ProjectSettings(fps=30.0),
        timeline=Timeline(
            tracks=[
                Track(
                    track_id="A1",
                    kind=TrackKind.AUDIO,
                    clips=[
                        Clip(clip_id="dia1", asset_id="speech_asset", in_frame=0, out_frame=90, timeline_start_frame=30)
                    ],
                ),
                Track(
                    track_id="A2",
                    kind=TrackKind.AUDIO,
                    mix_config=AudioMixConfig(
                        volume_db=-2.0,
                        ducking=DuckingConfig(trigger_track_id="A1", threshold_db=-20.0, attack_ms=20.0, release_ms=250.0),
                    ),
                    clips=[
                        Clip(clip_id="mus1", asset_id="music_asset", in_frame=0, out_frame=120, timeline_start_frame=0)
                    ],
                ),
            ]
        ),
    )
    project.media_pool.add_asset(
        MediaAsset(asset_id="speech_asset", file_path=str(speech_path), file_size_bytes=speech_path.stat().st_size)
    )
    project.media_pool.add_asset(
        MediaAsset(asset_id="music_asset", file_path=str(music_path), file_size_bytes=music_path.stat().st_size)
    )

    mixer = AudioMixer()
    out = mixer.mix_timeline_audio(project, master_stem, target_profile="youtube")

    assert out.is_file()
    assert out.stat().st_size > 1000

    meas = mixer.measure_loudness(out, target_profile="youtube")
    assert meas.integrated_lufs > -70.0


def test_cli_audio_commands(synthetic_beat_audio: Path, tmp_path: Path) -> None:
    """Verify all CLI audio commands execute cleanly and output expected JSON/text."""
    runner = CliRunner()

    # 1. hyperedit audio beats --json
    res_beats = runner.invoke(cli, ["audio", "beats", str(synthetic_beat_audio), "--json"])
    assert res_beats.exit_code == 0
    beats_data = json.loads(res_beats.output)
    assert abs(beats_data["bpm"] - 120.0) <= 1.0
    assert "beat_timestamps" in beats_data

    # 2. hyperedit audio loudness --profile youtube --json
    res_loud = runner.invoke(cli, ["audio", "loudness", str(synthetic_beat_audio), "--profile", "youtube", "--json"])
    assert res_loud.exit_code == 0
    loud_data = json.loads(res_loud.output)
    assert "integrated_lufs" in loud_data
    assert loud_data["target_lufs"] == -14.0

    # 3. hyperedit audio markers
    proj_path = tmp_path / "test_proj.json"
    project = Project(
        metadata=ProjectMetadata(title="CliAudioTest"),
        settings=ProjectSettings(fps=30.0),
    )
    with open(proj_path, "w", encoding="utf-8") as f:
        f.write(project.model_dump_json(indent=2))

    res_markers = runner.invoke(
        cli,
        ["audio", "markers", str(proj_path), str(synthetic_beat_audio), "--bpm-hint", "120", "--json"],
    )
    assert res_markers.exit_code == 0
    marker_data = json.loads(res_markers.output)
    assert marker_data["markers_added"] > 0

    # 4. hyperedit audio normalize
    norm_path = tmp_path / "cli_normalized.wav"
    res_norm = runner.invoke(
        cli,
        ["audio", "normalize", str(synthetic_beat_audio), str(norm_path), "--profile", "youtube"],
    )
    assert res_norm.exit_code == 0
    assert norm_path.is_file()
