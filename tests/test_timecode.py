"""Tests for SMPTE Timecode calculations and frame conversions."""

from fractions import Fraction
import pytest

from hyperedit.core.exceptions import ProjectValidationError
from hyperedit.core.models.timecode import Timecode, resolve_fps_fraction


def test_resolve_fps_fraction():
    assert resolve_fps_fraction("24") == Fraction(24, 1)
    assert resolve_fps_fraction(30) == Fraction(30, 1)
    assert resolve_fps_fraction("23.976") == Fraction(24000, 1001)
    assert resolve_fps_fraction("29.97") == Fraction(30000, 1001)
    assert resolve_fps_fraction("59.94") == Fraction(60000, 1001)


def test_timecode_from_frames():
    tc = Timecode.from_frames(90, fps=30.0)
    assert tc.frames == 90
    assert tc.seconds == 3.0
    assert tc.to_smpte() == "00:00:03:00"


def test_timecode_from_seconds():
    tc = Timecode.from_seconds(1.5, fps=24.0)
    assert tc.frames == 36
    assert tc.to_smpte() == "00:00:01:12"


def test_timecode_from_smpte():
    tc = Timecode.from_smpte("01:02:03:15", fps=30.0)
    assert tc.to_smpte() == "01:02:03:15"
    assert tc.frames == (1 * 3600 + 2 * 60 + 3) * 30 + 15


def test_timecode_drop_frame_smpte():
    # 29.97 drop frame uses semicolon
    tc = Timecode.from_smpte("00:01:00;00", fps=29.97)
    smpte_str = tc.to_smpte(drop_frame=True)
    assert ";" in smpte_str


def test_timecode_arithmetic():
    tc1 = Timecode.from_frames(100, fps=30.0)
    tc2 = Timecode.from_frames(50, fps=30.0)
    res = tc1 + tc2
    assert res.frames == 150
    diff = tc1 - tc2
    assert diff.frames == 50
    # Boundary check: negative frames clamped to 0
    clamped = tc2 - tc1
    assert clamped.frames == 0


def test_timecode_invalid_smpte():
    with pytest.raises(ProjectValidationError):
        Timecode.from_smpte("invalid_string", fps=30.0)

