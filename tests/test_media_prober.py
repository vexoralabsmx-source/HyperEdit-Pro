"""Tests for Media Prober."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from hyperedit.core.exceptions import MediaNotFoundError
from hyperedit.media.prober import FFprobeProber


def test_media_not_found():
    prober = FFprobeProber()
    with pytest.raises(MediaNotFoundError):
        prober.probe_file("non_existent_file.mp4")


def test_prober_mocked_ffprobe(tmp_path: Path):
    dummy_file = tmp_path / "dummy.mp4"
    dummy_file.write_bytes(b"dummy data")

    fake_json = {
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "duration": "5.0",
                "pix_fmt": "yuv420p"
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
                "channel_layout": "stereo",
                "duration": "5.0"
            }
        ],
        "format": {
            "format_name": "mp4",
            "duration": "5.0",
            "size": "1024"
        }
    }

    prober = FFprobeProber(ffprobe_bin="ffprobe")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=str(fake_json).replace("'", '"'))
        asset = prober.probe_file(dummy_file, compute_hash=True)

        assert asset.has_video is True
        assert asset.has_audio is True
        assert asset.primary_video.width == 1920
        assert asset.primary_video.height == 1080
        assert asset.primary_audio.sample_rate == 48000
        assert asset.hash_sha256 is not None

