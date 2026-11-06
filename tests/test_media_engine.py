"""Comprehensive test suite for HyperEdit Pro Professional Media Engine."""

import hashlib
from pathlib import Path
import subprocess
import time
import pytest
from click.testing import CliRunner

from hyperedit.cli.main import cli
from hyperedit.core.exceptions import MediaNotFoundError, MediaProbeError
from hyperedit.core.models.project import Project
from hyperedit.media.artifacts import MediaArtifactGenerator
from hyperedit.media.cache import MediaCacheManager
from hyperedit.media.importer import MediaImporter
from hyperedit.media.models import MediaType
from hyperedit.media.prober import FFprobeProber
from hyperedit.media.signal import AudioSignalAnalyzer


@pytest.fixture(scope="session")
def media_fixtures(tmp_path_factory) -> dict:
    """Generate minimal synthetic media fixtures using FFmpeg."""
    base_dir = tmp_path_factory.mktemp("media_fixtures")

    fixtures = {}

    # 1. 24 fps video with audio (1 sec)
    f_24 = base_dir / "clip_24fps.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:v", "libx264", "-c:a", "aac", str(f_24)
    ], capture_output=True, check=True)
    fixtures["video_24fps"] = f_24

    # 2. 29.97 fps video with audio (1 sec)
    f_2997 = base_dir / "clip_2997fps.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30000/1001",
        "-f", "lavfi", "-i", "sine=frequency=800:duration=1",
        "-c:v", "libx264", "-c:a", "aac", str(f_2997)
    ], capture_output=True, check=True)
    fixtures["video_2997fps"] = f_2997

    # 3. 60 fps video with audio (1 sec)
    f_60 = base_dir / "clip_60fps.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=60",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-c:v", "libx264", "-c:a", "aac", str(f_60)
    ], capture_output=True, check=True)
    fixtures["video_60fps"] = f_60

    # 4. Silent video (no audio stream)
    f_silent = base_dir / "clip_silent.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
        "-c:v", "libx264", str(f_silent)
    ], capture_output=True, check=True)
    fixtures["video_silent"] = f_silent

    # 5. Audio only WAV (1 sec, stereo)
    f_audio = base_dir / "audio_stereo.wav"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-ac", "2", "-c:a", "pcm_s16le", str(f_audio)
    ], capture_output=True, check=True)
    fixtures["audio_stereo"] = f_audio

    # 6. Audio with silence in middle (sine 0.5s + silence 1.0s + sine 0.5s)
    f_silence = base_dir / "audio_with_silence.wav"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=0.5",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo:d=1.0",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=0.5",
        "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[outa]",
        "-map", "[outa]", str(f_silence)
    ], capture_output=True, check=True)
    fixtures["audio_with_silence"] = f_silence

    # 7. Vertical video (540x960 portrait)
    f_vertical = base_dir / "clip_vertical_9_16.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=540x960:rate=30",
        "-c:v", "libx264", str(f_vertical)
    ], capture_output=True, check=True)
    fixtures["video_vertical"] = f_vertical

    # 8. Static image (PNG)
    f_image = base_dir / "photo_test.png"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=0.1:size=320x240:rate=10",
        "-vframes", "1", str(f_image)
    ], capture_output=True, check=True)
    fixtures["image_png"] = f_image

    # 9. Unicode and spaces filename: 'clip ñ á ü 🎬 test.mp4'
    f_unicode = base_dir / "clip ñ á ü 🎬 test.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
        "-c:v", "libx264", str(f_unicode)
    ], capture_output=True, check=True)
    fixtures["video_unicode"] = f_unicode

    # 10. Corrupted video file (truncated / broken header)
    f_corrupt = base_dir / "corrupted_media.mp4"
    f_corrupt.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00garbage_broken_data_123456789")
    fixtures["corrupted"] = f_corrupt

    # 11. Incompatible text file
    f_incomp = base_dir / "plain_document.txt"
    f_incomp.write_text("Hello, this is just plain text, not an audiovisual file.", encoding="utf-8")
    fixtures["incompatible"] = f_incomp

    return fixtures


# ----------------------------------------------------------------------
# 1. Inspection and Probing Tests
# ----------------------------------------------------------------------

def test_probe_exact_framerates(media_fixtures):
    prober = FFprobeProber()

    # 24 fps
    asset_24 = prober.probe_file(media_fixtures["video_24fps"])
    assert asset_24.media_type == MediaType.VIDEO
    assert asset_24.has_video is True
    assert asset_24.has_audio is True
    assert round(asset_24.primary_video.frame_rate_info.fps) == 24
    assert asset_24.primary_video.frame_rate_info.is_vfr is False

    # 29.97 fps
    asset_2997 = prober.probe_file(media_fixtures["video_2997fps"])
    assert abs(asset_2997.primary_video.frame_rate_info.fps - 29.97) < 0.05

    # 60 fps
    asset_60 = prober.probe_file(media_fixtures["video_60fps"])
    assert round(asset_60.primary_video.frame_rate_info.fps) == 60


def test_probe_silent_video(media_fixtures):
    prober = FFprobeProber()
    asset = prober.probe_file(media_fixtures["video_silent"])
    assert asset.has_video is True
    assert asset.has_audio is False
    assert len(asset.audio_streams) == 0


def test_probe_audio_only(media_fixtures):
    prober = FFprobeProber()
    asset = prober.probe_file(media_fixtures["audio_stereo"])
    assert asset.media_type == MediaType.AUDIO
    assert asset.has_video is False
    assert asset.has_audio is True
    assert asset.primary_audio.channels == 2
    assert asset.primary_audio.channel_layout == "stereo"


def test_probe_vertical_video(media_fixtures):
    prober = FFprobeProber()
    asset = prober.probe_file(media_fixtures["video_vertical"])
    assert asset.primary_video.is_vertical is True
    assert asset.primary_video.width == 540
    assert asset.primary_video.height == 960


def test_probe_unicode_path(media_fixtures):
    prober = FFprobeProber()
    asset = prober.probe_file(media_fixtures["video_unicode"])
    assert asset.has_video is True
    assert Path(asset.file_path).exists()
    assert "ñ" in asset.file_path


# ----------------------------------------------------------------------
# 2. Validation & Corruption Handling Tests
# ----------------------------------------------------------------------

def test_validation_healthy_file(media_fixtures):
    prober = FFprobeProber()
    report = prober.validate_media(media_fixtures["video_24fps"])
    assert report.is_valid is True
    assert report.is_corrupted is False
    assert report.is_supported is True


def test_validation_corrupted_file(media_fixtures):
    prober = FFprobeProber()
    report = prober.validate_media(media_fixtures["corrupted"])
    assert report.is_valid is False
    assert report.is_corrupted is True


def test_validation_incompatible_file(media_fixtures):
    prober = FFprobeProber()
    report = prober.validate_media(media_fixtures["incompatible"])
    assert report.is_valid is False


# ----------------------------------------------------------------------
# 3. Artifact Generation Tests
# ----------------------------------------------------------------------

def test_artifact_generation(media_fixtures, tmp_path: Path):
    artifacts = MediaArtifactGenerator()

    # 1. Thumbnail
    thumb_path = tmp_path / "thumb.jpg"
    out_thumb = artifacts.extract_thumbnail(media_fixtures["video_24fps"], thumb_path)
    assert out_thumb.exists()
    assert out_thumb.stat().st_size > 500

    # 2. Contact sheet (3x3)
    sheet_path = tmp_path / "contact_sheet.jpg"
    out_sheet = artifacts.generate_contact_sheet(
        media_fixtures["video_24fps"],
        sheet_path,
        duration_seconds=1.0,
        cols=3,
        rows=3,
    )
    assert out_sheet.exists()
    assert out_sheet.stat().st_size > 1000

    # 3. Waveform
    wave_path = tmp_path / "waveform.png"
    out_wave = artifacts.generate_waveform(media_fixtures["video_24fps"], wave_path)
    assert out_wave.exists()
    assert out_wave.stat().st_size > 500

    # 4. Proxy (720p)
    proxy_path = tmp_path / "proxy_720p.mp4"
    out_proxy = artifacts.create_proxy(media_fixtures["video_24fps"], proxy_path, scale="720p")
    assert out_proxy.exists()
    assert out_proxy.stat().st_size > 1000

    # 5. Audio Extraction
    audio_stem = tmp_path / "extracted_stem.wav"
    out_audio = artifacts.extract_audio(media_fixtures["video_24fps"], audio_stem)
    assert out_audio.exists()
    assert out_audio.stat().st_size > 1000


# ----------------------------------------------------------------------
# 4. Audio Signal Telemetry Tests
# ----------------------------------------------------------------------

def test_signal_metrics_silence_detection(media_fixtures):
    analyzer = AudioSignalAnalyzer()
    metrics = analyzer.analyze_signal(media_fixtures["audio_with_silence"], silence_threshold_db=-30.0, min_silence_duration=0.4)
    assert metrics.mean_volume_db < 0.0
    assert metrics.dynamic_range_db > 0.0
    # Should detect the 1-second silence in the middle
    assert len(metrics.silence_intervals) >= 1
    silence = metrics.silence_intervals[0]
    assert silence.duration_seconds >= 0.8


# ----------------------------------------------------------------------
# 5. Caching and Invalidation Tests
# ----------------------------------------------------------------------

def test_cache_and_invalidation(media_fixtures, tmp_path: Path):
    cache_file = tmp_path / "cache_index.json"
    cache = MediaCacheManager(cache_file)
    prober = FFprobeProber()

    src = media_fixtures["video_24fps"]

    # 1. Initial probe & cache
    asset = prober.probe_file(src)
    cache.set(src, asset)

    cached_asset = cache.get(src)
    assert cached_asset is not None
    assert cached_asset.asset_id == asset.asset_id

    # 2. Modify file timestamp -> cache must invalidate
    # Make a temporary copy to mutate
    mut_file = tmp_path / "mutating_clip.mp4"
    mut_file.write_bytes(src.read_bytes())

    asset_mut = prober.probe_file(mut_file)
    cache.set(mut_file, asset_mut)
    assert cache.get(mut_file) is not None

    # Append 1 byte to invalidate signature
    with open(mut_file, "ab") as f:
        f.write(b"\x00")

    assert cache.get(mut_file) is None


# ----------------------------------------------------------------------
# 6. Safety & Immutability Verification
# ----------------------------------------------------------------------

def test_original_file_immutability(media_fixtures, tmp_path: Path):
    src = media_fixtures["video_2997fps"]
    h_before = hashlib.sha256(src.read_bytes()).hexdigest()
    mtime_before = src.stat().st_mtime

    importer = MediaImporter()
    importer.import_media(
        media_file=src,
        generate_thumbnail=True,
        generate_contact_sheet=True,
        generate_waveform=True,
        generate_proxy=True,
        extract_audio=True,
        analyze_signals=True,
        assets_dir=tmp_path / "cache",
    )

    h_after = hashlib.sha256(src.read_bytes()).hexdigest()
    mtime_after = src.stat().st_mtime

    assert h_before == h_after
    assert mtime_before == mtime_after


# ----------------------------------------------------------------------
# 7. End-to-End Pipeline & CLI Execution Tests
# ----------------------------------------------------------------------

def test_cli_media_probe_json(media_fixtures):
    runner = CliRunner()
    result = runner.invoke(cli, ["media", "probe", str(media_fixtures["video_24fps"]), "--json"])
    assert result.exit_code == 0
    assert "asset_id" in result.output
    assert "video_streams" in result.output


def test_cli_media_signal_metrics_json(media_fixtures):
    runner = CliRunner()
    result = runner.invoke(cli, ["media", "signal-metrics", str(media_fixtures["audio_with_silence"]), "--json"])
    assert result.exit_code == 0
    assert "mean_volume_db" in result.output
    assert "silence_intervals" in result.output


def test_cli_media_import_into_project(media_fixtures, tmp_path: Path):
    runner = CliRunner()
    proj_path = tmp_path / "proj.json"

    # Create boilerplate project
    res_new = runner.invoke(cli, ["new", str(proj_path)])
    assert res_new.exit_code == 0

    # Import media file with all artifacts enabled
    res_import = runner.invoke(
        cli,
        [
            "media", "import",
            str(proj_path),
            str(media_fixtures["video_24fps"]),
            "--thumbnail",
            "--contact-sheet",
            "--waveform",
            "--proxy",
            "--extract-audio",
            "--signal-metrics",
        ]
    )
    assert res_import.exit_code == 0
    assert "Imported 'clip_24fps' into project" in res_import.output

    # Validate that project media_pool now contains clip_24fps
    proj = Project.load_from_file(proj_path)
    assert "clip_24fps" in proj.media_pool.assets
    asset = proj.media_pool.assets["clip_24fps"]
    assert asset.has_video is True
    assert asset.has_audio is True

