"""Comprehensive test suite for HyperEdit Pro Captions & Kinetic Typography (Stage 5)."""

import json
from pathlib import Path
import subprocess
import pytest
from click.testing import CliRunner

from hyperedit.adapters.hyperframes_captions import HyperFramesCaptionsAdapter
from hyperedit.captions.engine import CaptionsEngine
from hyperedit.captions.formats import (
    hex_to_ass_color,
    ms_to_ass_time,
    ms_to_srt_time,
    ms_to_vtt_time,
    parse_timestamp_to_ms,
)
from hyperedit.captions.kinetic import (
    KineticTypographyCompiler,
    estimate_word_timestamps,
)
from hyperedit.captions.models import (
    KineticAnimationMode,
    SubtitleCue,
    SubtitleStyle,
    SubtitleTrack,
    WordTimestamp,
)
from hyperedit.captions.transcriber import SpeechTranscriber
from hyperedit.cli.main import cli
from hyperedit.core.exceptions import DependencyMissingError
from hyperedit.diagnostics.checker import EnvironmentChecker


@pytest.fixture
def sample_srt_content() -> str:
    return """1
00:00:00,500 --> 00:00:02,000
Bienvenido a HyperEdit Pro

2
00:00:02,200 --> 00:00:04,500
Edición audiovisual real para agentes de IA
"""


@pytest.fixture
def synthetic_video_mp4(tmp_path: Path) -> Path:
    """Generate a 2.0s 720p synthetic MP4 video clip."""
    video_path = tmp_path / "test_background.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=navy:s=1280x720:d=2.0:r=30",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=48000:cl=stereo",
        "-t",
        "2.0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(video_path),
    ]
    subprocess.run(cmd, check=True)
    return video_path


def test_timecode_and_color_conversions() -> None:
    """Verify exact timecode conversions and ASS hex color byte ordering."""
    # Milliseconds to string timecodes
    ms = 3661234  # 1h 1m 1s 234ms
    assert ms_to_srt_time(ms) == "01:01:01,234"
    assert ms_to_vtt_time(ms) == "01:01:01.234"
    assert ms_to_ass_time(ms) == "1:01:01.23"

    # Parsing back
    assert parse_timestamp_to_ms("01:01:01,234") == 3661234
    assert parse_timestamp_to_ms("01:01:01.234") == 3661234
    assert parse_timestamp_to_ms("1:01:01.23") == 3661230

    # ASS Hex Color: standard CSS #RRGGBB -> ASS &HAABBGGRR (Blue, Green, Red)
    # Pure red #FF0000 -> &H000000FF (Blue=00, Green=00, Red=FF)
    assert hex_to_ass_color("#FF0000") == "&H000000FF"
    # Pure blue #0000FF -> &H00FF0000 (Blue=FF, Green=00, Red=00)
    assert hex_to_ass_color("#0000FF") == "&H00FF0000"
    # Yellow #FFE600 -> &H0000E6FF
    assert hex_to_ass_color("#FFE600") == "&H0000E6FF"


def test_import_and_export_srt_vtt_ass(sample_srt_content: str, tmp_path: Path) -> None:
    """Verify parsing and bidirectional conversion between SRT, WebVTT, and ASS formats."""
    engine = CaptionsEngine()
    srt_file = tmp_path / "input.srt"
    srt_file.write_text(sample_srt_content, encoding="utf-8")

    # Import SRT
    track = engine.import_subtitles(srt_file)
    assert len(track.cues) == 2
    assert track.cues[0].start_ms == 500
    assert track.cues[0].end_ms == 2000
    assert track.cues[0].text == "Bienvenido a HyperEdit Pro"
    assert track.cues[1].start_ms == 2200
    assert track.cues[1].end_ms == 4500

    # Export to WebVTT
    vtt_file = tmp_path / "output.vtt"
    engine.export_vtt(track, vtt_file)
    assert vtt_file.is_file()
    vtt_content = vtt_file.read_text(encoding="utf-8")
    assert vtt_content.startswith("WEBVTT")

    # Re-import WebVTT and verify cue parity
    reimported_vtt = engine.import_subtitles(vtt_file)
    assert len(reimported_vtt.cues) == 2
    assert reimported_vtt.cues[0].start_ms == 500
    assert reimported_vtt.cues[0].text == track.cues[0].text

    # Export to ASS
    ass_file = tmp_path / "output.ass"
    engine.export_ass(track, ass_file)
    assert ass_file.is_file()
    ass_content = ass_file.read_text(encoding="utf-8")
    assert "[Script Info]" in ass_content
    assert "[V4+ Styles]" in ass_content
    assert "Dialogue:" in ass_content


def test_kinetic_karaoke_highlight_ass_generation() -> None:
    """Verify ASS compilation for karaoke highlight generates active word accent tags."""
    cue = SubtitleCue(
        cue_id="c1",
        start_ms=0,
        end_ms=2000,
        text="Alpha Beta Gamma",
        words=[
            WordTimestamp(word="Alpha", start_ms=0, end_ms=600),
            WordTimestamp(word="Beta", start_ms=600, end_ms=1300),
            WordTimestamp(word="Gamma", start_ms=1300, end_ms=2000),
        ],
    )
    style = SubtitleStyle(
        font_name="Arial",
        primary_color_hex="#FFFFFF",
        highlight_color_hex="#FFE600",
        animation_mode=KineticAnimationMode.KARAOKE_HIGHLIGHT,
    )
    track = SubtitleTrack(default_style=style, cues=[cue])

    ass_text = KineticTypographyCompiler.compile_ass(track)

    # In ASS, yellow highlight #FFE600 translates to &H0000E6FF
    assert r"\c&H0000E6FF&" in ass_text
    # Check that 3 separate dialogue lines were generated for word highlights
    dialogue_lines = [line for line in ass_text.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogue_lines) == 3
    assert r"{\c&H0000E6FF&}Alpha{\r} Beta Gamma" in dialogue_lines[0]
    assert r"Alpha {\c&H0000E6FF&}Beta{\r} Gamma" in dialogue_lines[1]
    assert r"Alpha Beta {\c&H0000E6FF&}Gamma{\r}" in dialogue_lines[2]


def test_kinetic_pop_scale_ass_generation() -> None:
    """Verify active word receives scale emphasis tags (fscx / fscy) in POP_SCALE mode."""
    cue = SubtitleCue(
        cue_id="c1",
        start_ms=0,
        end_ms=1000,
        text="Impact Now",
        words=[
            WordTimestamp(word="Impact", start_ms=0, end_ms=500),
            WordTimestamp(word="Now", start_ms=500, end_ms=1000),
        ],
    )
    style = SubtitleStyle(
        animation_mode=KineticAnimationMode.POP_SCALE,
        highlight_color_hex="#00FFCC",
    )
    track = SubtitleTrack(default_style=style, cues=[cue])
    ass_text = KineticTypographyCompiler.compile_ass(track)

    dialogue_lines = [line for line in ass_text.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogue_lines) == 2
    # Verify scale tags \fscx115\fscy115
    assert r"\fscx115\fscy115" in dialogue_lines[0]
    assert r"\fscx115\fscy115" in dialogue_lines[1]


def test_word_timestamp_proportional_estimation() -> None:
    """Verify proportional word duration estimator distributes timing based on word length."""
    cue = SubtitleCue(
        cue_id="c1",
        start_ms=1000,
        end_ms=3000,
        text="Short and Extraordinary word",
    )
    words = estimate_word_timestamps(cue)
    assert len(words) == 4
    assert words[0].word == "Short"
    assert words[2].word == "Extraordinary"
    # The word 'Extraordinary' (13 chars) must receive more time than 'and' (3 chars)
    dur_extraordinary = words[2].duration_ms
    dur_and = words[1].duration_ms
    assert dur_extraordinary > dur_and * 2
    # Verify timeline spans exactly cue start to end
    assert words[0].start_ms == 1000
    assert words[-1].end_ms == 3000


def test_readability_validation_qa() -> None:
    """Verify automated subtitle readability QA catches pacing, duration, and line length issues."""
    track = SubtitleTrack(
        default_style=SubtitleStyle(max_chars_per_line=30),
        cues=[
            # Issue 1: line exceeds 30 characters
            SubtitleCue(
                cue_id="c1",
                start_ms=0,
                end_ms=2000,
                text="Esta línea es definitivamente demasiado larga para el límite establecido",
            ),
            # Issue 2: cue too brief (< 700ms)
            SubtitleCue(
                cue_id="c2",
                start_ms=2500,
                end_ms=2800,
                text="Rápido",
            ),
            # Issue 3 & 4: overlapping cues (c3 ends at 4500ms, c4 starts at 4000ms)
            SubtitleCue(
                cue_id="c3",
                start_ms=3000,
                end_ms=4500,
                text="Tercer subtítulo",
            ),
            SubtitleCue(
                cue_id="c4",
                start_ms=4000,
                end_ms=5500,
                text="Cuarto subtítulo",
            ),
        ],
    )

    engine = CaptionsEngine()
    issues = engine.validate_readability(track)

    issue_types = [i.issue_type for i in issues]
    assert "line_too_long" in issue_types
    assert "too_short" in issue_types
    assert "overlap" in issue_types


def test_safe_areas_vertical_and_horizontal() -> None:
    """Verify vertical safe area clamps bottom margin to prevent collision with Reels/TikTok footer UI."""
    engine = CaptionsEngine()

    # Vertical 9:16
    v_track = SubtitleTrack(default_style=SubtitleStyle(margin_v=40, margin_h=20))
    engine.adjust_safe_areas(v_track, aspect_ratio="9:16", resolution=(1080, 1920))
    assert v_track.default_style.margin_v >= 180
    assert v_track.default_style.margin_h >= 40
    assert v_track.default_style.max_chars_per_line <= 26

    # Horizontal 16:9
    h_track = SubtitleTrack(default_style=SubtitleStyle(margin_v=20, margin_h=20))
    engine.adjust_safe_areas(h_track, aspect_ratio="16:9", resolution=(1920, 1080))
    assert h_track.default_style.margin_v >= 50
    assert h_track.default_style.margin_h >= 50


def test_real_burn_in_traditional_and_kinetic(synthetic_video_mp4: Path, tmp_path: Path) -> None:
    """Verify real video render with burned-in subtitles: traditional preset vs kinetic typography."""
    checker = EnvironmentChecker()
    report = checker.run_all_checks()
    if "subtitles" not in report.available_filters and "ass" not in report.available_filters:
        pytest.skip("FFmpeg lacks libass filter ('subtitles' or 'ass'); skipping burn-in test.")

    engine = CaptionsEngine()

    track = SubtitleTrack(
        cues=[
            SubtitleCue(
                cue_id="c1",
                start_ms=200,
                end_ms=1800,
                text="Prueba de renderizado real",
                words=[
                    WordTimestamp(word="Prueba", start_ms=200, end_ms=600),
                    WordTimestamp(word="de", start_ms=600, end_ms=900),
                    WordTimestamp(word="renderizado", start_ms=900, end_ms=1400),
                    WordTimestamp(word="real", start_ms=1400, end_ms=1800),
                ],
            )
        ]
    )

    # 1. Traditional Burn-in (netflix preset)
    trad_output = tmp_path / "traditional_sub_burned.mp4"
    out_trad = engine.burn_subtitles(
        video_input=synthetic_video_mp4,
        subtitle_input=track,
        output_path=trad_output,
        preset_name="netflix",
    )
    assert out_trad.is_file()
    assert out_trad.stat().st_size > 1000

    # 2. Kinetic Typography Burn-in (tiktok_reels_neon preset)
    kinetic_output = tmp_path / "kinetic_sub_burned.mp4"
    out_kinetic = engine.burn_subtitles(
        video_input=synthetic_video_mp4,
        subtitle_input=track,
        output_path=kinetic_output,
        preset_name="tiktok_reels_neon",
    )
    assert out_kinetic.is_file()
    assert out_kinetic.stat().st_size > 1000

    # Verify both output videos have exact 2.0s duration via FFprobe
    for vid in (out_trad, out_kinetic):
        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(vid),
        ]
        proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        dur = float(proc.stdout.strip())
        assert abs(dur - 2.0) < 0.2


def test_speech_transcription_missing_dependency(tmp_path: Path) -> None:
    """Verify speech transcriber gracefully raises DependencyMissingError when faster-whisper is absent."""
    transcriber = SpeechTranscriber()
    if not transcriber.is_available():
        test_file = tmp_path / "dummy.wav"
        test_file.write_bytes(b"RIFF" + b"\x00" * 40)
        with pytest.raises(DependencyMissingError) as exc_info:
            transcriber.transcribe(test_file)
        assert "pip install faster-whisper" in str(exc_info.value)
        assert "does not simulate or invent" in str(exc_info.value)


def test_hyperframes_captions_adapter(tmp_path: Path) -> None:
    """Verify HyperFrames adapter generates valid HTML/CSS/GSAP composition with kinetic word data."""
    track = SubtitleTrack(
        cues=[
            SubtitleCue(
                cue_id="c1",
                start_ms=0,
                end_ms=2500,
                text="Motion Captions HyperFrames",
                words=[
                    WordTimestamp(word="Motion", start_ms=0, end_ms=800),
                    WordTimestamp(word="Captions", start_ms=800, end_ms=1600),
                    WordTimestamp(word="HyperFrames", start_ms=1600, end_ms=2500),
                ],
            )
        ]
    )

    adapter = HyperFramesCaptionsAdapter()
    html_out = tmp_path / "kinetic_captions.html"
    res = adapter.export_html_composition(track, html_out)

    assert res.is_file()
    content = res.read_text(encoding="utf-8")
    assert '<div class="kinetic-cue"' in content
    assert '<span class="kinetic-word"' in content
    assert 'data-start="0.000"' in content
    assert 'data-end="0.800"' in content
    assert "window.seek =" in content


def test_cli_captions_commands(sample_srt_content: str, tmp_path: Path) -> None:
    """Verify CLI captions subcommands (import, export, kinetic, hyperframes, validate)."""
    runner = CliRunner()
    srt_file = tmp_path / "test.srt"
    srt_file.write_text(sample_srt_content, encoding="utf-8")

    # 1. hyperedit captions import --json
    res_import = runner.invoke(cli, ["captions", "import", str(srt_file), "--json"])
    assert res_import.exit_code == 0
    data = json.loads(res_import.output)
    assert len(data["cues"]) == 2

    # 2. hyperedit captions export to VTT
    vtt_out = tmp_path / "exported.vtt"
    res_exp = runner.invoke(cli, ["captions", "export", str(srt_file), "-o", str(vtt_out)])
    assert res_exp.exit_code == 0
    assert vtt_out.is_file()

    # 3. hyperedit captions kinetic to ASS
    ass_out = tmp_path / "kinetic.ass"
    res_kin = runner.invoke(
        cli,
        ["captions", "kinetic", str(srt_file), "-o", str(ass_out), "--mode", "karaoke_highlight"],
    )
    assert res_kin.exit_code == 0
    assert ass_out.is_file()

    # 4. hyperedit captions hyperframes to HTML
    html_out = tmp_path / "captions.html"
    res_hf = runner.invoke(
        cli,
        ["captions", "hyperframes", str(srt_file), "-o", str(html_out), "--preset", "modern_bold"],
    )
    assert res_hf.exit_code == 0
    assert html_out.is_file()

    # 5. hyperedit captions validate --json
    res_val = runner.invoke(cli, ["captions", "validate", str(srt_file), "--json"])
    assert res_val.exit_code == 0
    issues = json.loads(res_val.output)
    assert isinstance(issues, list)

