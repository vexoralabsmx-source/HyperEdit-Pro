"""Tests for Environment Diagnostics checker."""

from unittest.mock import MagicMock, patch
from hyperedit.diagnostics.checker import DiagnosticReport, DiagnosticStatus, EnvironmentChecker
from hyperedit.diagnostics.formatter import DiagnosticFormatter


def test_real_environment_checker():
    checker = EnvironmentChecker()
    report = checker.run_all_checks()
    assert isinstance(report, DiagnosticReport)
    assert report.python_version != ""
    assert report.ffmpeg_detected is True
    assert report.ffprobe_detected is True
    assert len(report.checks) >= 5


def test_doctor_missing_ffmpeg():
    checker = EnvironmentChecker(ffmpeg_bin="/non/existent/path/ffmpeg", ffprobe_bin="/non/existent/path/ffprobe")
    report = checker.run_all_checks()
    assert report.ffmpeg_detected is False
    assert report.ffprobe_detected is False
    assert report.overall_status == DiagnosticStatus.ERROR


def test_doctor_hardware_encoder_parsing():
    checker = EnvironmentChecker()
    dummy_encoder_lines = [
        "Encoders:",
        " V..... h264_nvenc           NVIDIA NVENC H.264 encoder",
        " V..... hevc_nvenc           NVIDIA NVENC hevc encoder",
        " V..... libx264              libx264 H.264 / AVC",
    ]
    item, detected = checker._check_hardware_encoders(dummy_encoder_lines)
    assert item.status == DiagnosticStatus.OK
    assert "h264_nvenc" in detected
    assert "hevc_nvenc" in detected


def test_diagnostic_formatter():
    checker = EnvironmentChecker()
    report = checker.run_all_checks()

    # Terminal output
    term_text = DiagnosticFormatter.to_terminal(report, verbose=True, use_color=False)
    assert "HyperEdit Pro System & Environment Diagnostics" in term_text

    # JSON output
    json_text = DiagnosticFormatter.to_json(report)
    assert '"overall_status"' in json_text

