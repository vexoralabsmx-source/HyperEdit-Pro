"""Professional Captions and Subtitle Engine for HyperEdit Pro."""

from pathlib import Path
import shutil
import subprocess
from typing import List, Optional, Tuple, Union

from hyperedit.captions.formats import (
    ASSGenerator,
    SRTParser,
    VTTParser,
)
from hyperedit.captions.kinetic import (
    KineticTypographyCompiler,
)
from hyperedit.captions.models import (
    KineticAnimationMode,
    ReadabilityIssue,
    STANDARD_CAPTION_PRESETS,
    SubtitleCue,
    SubtitleFormat,
    SubtitleStyle,
    SubtitleTrack,
)
from hyperedit.core.exceptions import (
    DependencyMissingError,
    MediaNotFoundError,
    ProjectValidationError,
    RenderExecutionError,
)
from hyperedit.core.protocols import CaptionsEngineProtocol


class CaptionsEngine(CaptionsEngineProtocol):
    """Production-grade captions, subtitle parser, kinetic typography, and burn-in renderer."""

    def __init__(self, ffmpeg_bin: Optional[str] = None) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")

    def _ensure_ffmpeg(self) -> None:
        if not self.ffmpeg_bin:
            raise DependencyMissingError("ffmpeg executable not found in PATH.")

    def import_subtitles(
        self,
        file_path: Path | str,
        track_id: str = "SUB1",
        style: Optional[SubtitleStyle] = None,
    ) -> SubtitleTrack:
        """Import subtitles from .srt, .vtt, or .ass file into a SubtitleTrack."""
        path = Path(file_path).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Subtitle file not found: {path}")

        raw_content = path.read_text(encoding="utf-8")
        ext = path.suffix.lower()

        if ext == ".srt" or "-->" in raw_content and not raw_content.startswith("WEBVTT"):
            track = SRTParser.parse(raw_content, track_id=track_id)
        elif ext == ".vtt" or raw_content.startswith("WEBVTT"):
            track = VTTParser.parse(raw_content, track_id=track_id)
        elif ext == ".ass" or "[Script Info]" in raw_content:
            # Parse ASS Events
            cues: List[SubtitleCue] = []
            cue_count = 1
            for line in raw_content.splitlines():
                if line.startswith("Dialogue:"):
                    parts = line.split(",", 9)
                    if len(parts) >= 10:
                        start_str = parts[1].strip()
                        end_str = parts[2].strip()
                        text_raw = parts[9]
                        # Remove ASS override tags {\...} for clean text representation
                        import re
                        clean = re.sub(r"\{[^\}]+\}", "", text_raw).replace(r"\N", "\n").strip()
                        from hyperedit.captions.formats import parse_timestamp_to_ms
                        cues.append(
                            SubtitleCue(
                                cue_id=f"cue_{cue_count:04d}",
                                start_ms=parse_timestamp_to_ms(start_str),
                                end_ms=parse_timestamp_to_ms(end_str),
                                text=clean,
                            )
                        )
                        cue_count += 1
            track = SubtitleTrack(track_id=track_id, cues=cues)
            track.sort_cues()
        else:
            raise ProjectValidationError(f"Unsupported subtitle format for file: {path.name}")

        if style:
            track.default_style = style

        return track

    def export_srt(self, track: SubtitleTrack, output_path: Path | str) -> Path:
        """Export subtitle track to SubRip (.srt) format."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        content = SRTParser.serialize(track)
        out.write_text(content, encoding="utf-8")
        return out

    def export_vtt(self, track: SubtitleTrack, output_path: Path | str) -> Path:
        """Export subtitle track to WebVTT (.vtt) format."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        content = VTTParser.serialize(track)
        out.write_text(content, encoding="utf-8")
        return out

    def export_ass(
        self,
        track: SubtitleTrack,
        output_path: Path | str,
        width: int = 1920,
        height: int = 1080,
    ) -> Path:
        """Export subtitle track to Advanced SubStation Alpha (.ass) format with typographic styling."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        if track.default_style.animation_mode != KineticAnimationMode.NONE:
            content = KineticTypographyCompiler.compile_ass(track, width=width, height=height)
        else:
            content = ASSGenerator.generate(track, width=width, height=height)

        out.write_text(content, encoding="utf-8")
        return out

    def build_burn_filter(self, track: SubtitleTrack, ass_path: Path | str) -> str:
        """Generate safe, cross-platform FFmpeg filter argument for burning subtitles via libass."""
        path = Path(ass_path).resolve()
        forward = path.as_posix()
        # Escape Windows drive colon: C:/... -> C\:/...
        escaped = forward.replace(":", r"\:")
        return f"ass=filename='{escaped}'"

    def burn_subtitles(
        self,
        video_input: Path | str,
        subtitle_input: Union[SubtitleTrack, Path, str],
        output_path: Path | str,
        preset_name: Optional[str] = None,
        width: int = 1920,
        height: int = 1080,
    ) -> Path:
        """Burn styled subtitles into video using FFmpeg and libass with kinetic animations."""
        self._ensure_ffmpeg()
        in_vid = Path(video_input).resolve()
        out_vid = Path(output_path).resolve()
        out_vid.parent.mkdir(parents=True, exist_ok=True)

        if not in_vid.is_file():
            raise MediaNotFoundError(f"Input video file not found: {in_vid}")

        # Resolve or compile subtitle track to ASS
        temp_ass = out_vid.with_suffix(".tmp.ass")
        if isinstance(subtitle_input, SubtitleTrack):
            track = subtitle_input
            if preset_name and preset_name in STANDARD_CAPTION_PRESETS:
                track.default_style = STANDARD_CAPTION_PRESETS[preset_name]
            self.export_ass(track, temp_ass, width=width, height=height)
        else:
            sub_path = Path(subtitle_input).resolve()
            if not sub_path.is_file():
                raise MediaNotFoundError(f"Subtitle source file not found: {sub_path}")
            if sub_path.suffix.lower() == ".ass" and not preset_name:
                temp_ass = sub_path
            else:
                track = self.import_subtitles(sub_path)
                if preset_name and preset_name in STANDARD_CAPTION_PRESETS:
                    track.default_style = STANDARD_CAPTION_PRESETS[preset_name]
                self.export_ass(track, temp_ass, width=width, height=height)

        burn_filter = self.build_burn_filter(track if 'track' in locals() else None, temp_ass)

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-v",
            "error",
            "-i",
            str(in_vid),
            "-vf",
            burn_filter,
            "-c:a",
            "copy",
            str(out_vid),
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                raise RenderExecutionError(f"Subtitle burn-in render failed: {proc.stderr}")
        finally:
            is_temp = isinstance(subtitle_input, SubtitleTrack) or (
                isinstance(subtitle_input, (str, Path)) and temp_ass != Path(subtitle_input).resolve()
            )
            if is_temp and temp_ass.exists():
                temp_ass.unlink(missing_ok=True)

        return out_vid

    def validate_readability(self, track: SubtitleTrack) -> List[ReadabilityIssue]:
        """Perform visual and cognitive QA checks on subtitle pacing, line length, and durations."""
        issues: List[ReadabilityIssue] = []
        track.sort_cues()
        cues = track.cues
        max_cpl = track.default_style.max_chars_per_line

        for i, cue in enumerate(cues):
            text_clean = cue.text.strip()
            if not text_clean:
                issues.append(
                    ReadabilityIssue(
                        cue_id=cue.cue_id,
                        issue_type="empty_text",
                        message="Subtitle cue has no text content.",
                        severity="error",
                    )
                )
                continue

            # CPS check (Characters Per Second: standard maximum is 20-25 CPS)
            cps = cue.characters_per_second
            if cps > 25.0:
                issues.append(
                    ReadabilityIssue(
                        cue_id=cue.cue_id,
                        issue_type="too_fast",
                        message=f"Pacing is too fast: {cps:.1f} characters/sec (max recommended: 25 CPS).",
                        severity="warning",
                    )
                )

            # Minimum reading duration (at least 700ms for cognitive retention)
            if cue.duration_ms < 700:
                issues.append(
                    ReadabilityIssue(
                        cue_id=cue.cue_id,
                        issue_type="too_short",
                        message=f"Duration too brief ({cue.duration_ms}ms). Minimum readable cue is 700ms.",
                        severity="warning",
                    )
                )

            # Characters Per Line (CPL) check
            lines = text_clean.splitlines()
            for line in lines:
                if len(line) > max_cpl:
                    issues.append(
                        ReadabilityIssue(
                            cue_id=cue.cue_id,
                            issue_type="line_too_long",
                            message=f"Line exceeds length limit ({len(line)} > {max_cpl} chars): '{line[:25]}...'",
                            severity="warning",
                        )
                    )

            # Overlapping cues check
            if i < len(cues) - 1:
                next_cue = cues[i + 1]
                if cue.end_ms > next_cue.start_ms:
                    overlap_ms = cue.end_ms - next_cue.start_ms
                    issues.append(
                        ReadabilityIssue(
                            cue_id=cue.cue_id,
                            issue_type="overlap",
                            message=f"Cue overlaps next cue '{next_cue.cue_id}' by {overlap_ms}ms.",
                            severity="error",
                        )
                    )

        return issues

    def adjust_safe_areas(
        self,
        track: SubtitleTrack,
        aspect_ratio: str = "16:9",
        resolution: Tuple[int, int] = (1920, 1080),
    ) -> SubtitleTrack:
        """Enforce platform safe area margins to prevent subtitles colliding with player UI or cutoffs."""
        width, height = resolution
        style = track.default_style

        if aspect_ratio == "9:16":
            # Vertical video (TikTok / Reels / Shorts): reserve bottom 180-220px for captions/author info
            if style.margin_v < 180:
                style.margin_v = 200
            if style.margin_h < 40:
                style.margin_h = 50
            style.max_chars_per_line = min(style.max_chars_per_line, 26)
        else:
            # 16:9 horizontal: reserve bottom 50-80px
            if style.margin_v < 40:
                style.margin_v = 60
            if style.margin_h < 50:
                style.margin_h = 60

        return track
