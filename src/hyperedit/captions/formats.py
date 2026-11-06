"""SubRip (SRT), WebVTT (VTT), and Advanced SubStation Alpha (ASS) parsers and exporters."""

from pathlib import Path
import re
from typing import List, Optional, Tuple

from hyperedit.captions.models import (
    SubtitleAlignment,
    SubtitleCue,
    SubtitleFormat,
    SubtitleStyle,
    SubtitleTrack,
    WordTimestamp,
)
from hyperedit.core.exceptions import ProjectValidationError


def ms_to_srt_time(ms: int) -> str:
    """Format milliseconds as SRT timecode: HH:MM:SS,mmm."""
    total_sec, millis = divmod(max(0, ms), 1000)
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def ms_to_vtt_time(ms: int) -> str:
    """Format milliseconds as WebVTT timecode: HH:MM:SS.mmm."""
    total_sec, millis = divmod(max(0, ms), 1000)
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def ms_to_ass_time(ms: int) -> str:
    """Format milliseconds as ASS timecode: H:MM:SS.cc (centiseconds)."""
    total_sec, millis = divmod(max(0, ms), 1000)
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    centis = millis // 10
    return f"{hours:d}:{minutes:02d}:{seconds:02d}.{centis:02d}"


def parse_timestamp_to_ms(time_str: str) -> int:
    """Parse SRT, VTT, or ASS timestamp into discrete milliseconds."""
    clean = time_str.strip().replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 3:
        h, m, s = parts
        seconds = float(s)
        return int(round((int(h) * 3600 + int(m) * 60 + seconds) * 1000))
    elif len(parts) == 2:
        m, s = parts
        seconds = float(s)
        return int(round((int(m) * 60 + seconds) * 1000))
    else:
        return int(float(clean) * 1000)


def hex_to_ass_color(hex_color: str, default_alpha: int = 0) -> str:
    """Convert standard Hex color (#RRGGBB or #RRGGBBAA) to ASS &HAABBGGRR format.

    In ASS: &H[Alpha][Blue][Green][Red] where Alpha 00 = completely opaque, FF = fully transparent.
    """
    clean = hex_color.strip().lstrip("#")
    if len(clean) == 3:
        r = int(clean[0] * 2, 16)
        g = int(clean[1] * 2, 16)
        b = int(clean[2] * 2, 16)
        a = default_alpha
    elif len(clean) == 6:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
        a = default_alpha
    elif len(clean) == 8:
        # #RRGGBBAA where AA is standard CSS opacity (FF = opaque)
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
        css_alpha = int(clean[6:8], 16)
        a = 255 - css_alpha  # Invert for ASS
    else:
        r, g, b, a = 255, 255, 255, default_alpha

    return f"&H{a:02X}{b:02X}{g:02X}{r:02X}"


def alignment_to_ass_numpad(alignment: SubtitleAlignment) -> int:
    """Convert SubtitleAlignment to standard ASS numpad code (1-9)."""
    mapping = {
        SubtitleAlignment.BOTTOM_LEFT: 1,
        SubtitleAlignment.BOTTOM_CENTER: 2,
        SubtitleAlignment.BOTTOM_RIGHT: 3,
        SubtitleAlignment.MIDDLE_CENTER: 5,
        SubtitleAlignment.TOP_LEFT: 7,
        SubtitleAlignment.TOP_CENTER: 8,
        SubtitleAlignment.TOP_RIGHT: 9,
    }
    return mapping.get(alignment, 2)


class SRTParser:
    """SubRip (.srt) reader and writer."""

    @staticmethod
    def parse(content: str, track_id: str = "SUB1") -> SubtitleTrack:
        cues: List[SubtitleCue] = []
        # Standard SRT block regex: index, timestamp arrow, text, blank line
        blocks = re.split(r"\n\s*\n", content.strip())
        cue_counter = 1

        for block in blocks:
            lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
            if not lines:
                continue

            time_line_idx = -1
            for idx, line in enumerate(lines):
                if "-->" in line:
                    time_line_idx = idx
                    break

            if time_line_idx == -1:
                continue

            # Parse start --> end
            time_parts = lines[time_line_idx].split("-->")
            start_ms = parse_timestamp_to_ms(time_parts[0])
            end_ms = parse_timestamp_to_ms(time_parts[1])

            text_lines = lines[time_line_idx + 1 :]
            text = "\n".join(text_lines)

            # Strip basic HTML tags if present (e.g. <i>, <b>, <font>)
            clean_text = re.sub(r"<[^>]+>", "", text).strip()

            cues.append(
                SubtitleCue(
                    cue_id=f"cue_{cue_counter:04d}",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=clean_text,
                )
            )
            cue_counter += 1

        track = SubtitleTrack(track_id=track_id, cues=cues)
        track.sort_cues()
        return track

    @staticmethod
    def serialize(track: SubtitleTrack) -> str:
        lines: List[str] = []
        track.sort_cues()

        for idx, cue in enumerate(track.cues, start=1):
            t_start = ms_to_srt_time(cue.start_ms)
            t_end = ms_to_srt_time(cue.end_ms)
            lines.append(str(idx))
            lines.append(f"{t_start} --> {t_end}")
            lines.append(cue.text)
            lines.append("")

        return "\n".join(lines)


class VTTParser:
    """WebVTT (.vtt) reader and writer."""

    @staticmethod
    def parse(content: str, track_id: str = "SUB1") -> SubtitleTrack:
        cues: List[SubtitleCue] = []
        lines = content.strip().splitlines()
        cue_counter = 1

        idx = 0
        # Skip optional header and metadata
        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE"):
                idx += 1
                while idx < len(lines) and lines[idx].strip():
                    idx += 1
            else:
                break

        # Process cues
        raw_blocks = re.split(r"\n\s*\n", "\n".join(lines[idx:]).strip())
        for block in raw_blocks:
            b_lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not b_lines:
                continue

            time_idx = -1
            for b_i, b_l in enumerate(b_lines):
                if "-->" in b_l:
                    time_idx = b_i
                    break

            if time_idx == -1:
                continue

            time_part = b_lines[time_idx].split("-->")
            start_ms = parse_timestamp_to_ms(time_part[0])
            # Strip cue settings from end timestamp (e.g. line:90% align:center)
            end_token = time_part[1].strip().split()[0]
            end_ms = parse_timestamp_to_ms(end_token)

            text = "\n".join(b_lines[time_idx + 1 :])
            clean_text = re.sub(r"<[^>]+>", "", text).strip()

            cues.append(
                SubtitleCue(
                    cue_id=f"cue_{cue_counter:04d}",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=clean_text,
                )
            )
            cue_counter += 1

        track = SubtitleTrack(track_id=track_id, cues=cues)
        track.sort_cues()
        return track

    @staticmethod
    def serialize(track: SubtitleTrack) -> str:
        lines: List[str] = ["WEBVTT", ""]
        track.sort_cues()

        for idx, cue in enumerate(track.cues, start=1):
            t_start = ms_to_vtt_time(cue.start_ms)
            t_end = ms_to_vtt_time(cue.end_ms)
            lines.append(str(idx))
            lines.append(f"{t_start} --> {t_end}")
            lines.append(cue.text)
            lines.append("")

        return "\n".join(lines)


class ASSGenerator:
    """Advanced SubStation Alpha (.ass) generator and compiler."""

    @staticmethod
    def generate(
        track: SubtitleTrack,
        width: int = 1920,
        height: int = 1080,
        title: str = "HyperEdit Pro Subtitles",
    ) -> str:
        """Compile a SubtitleTrack into a valid ASS v4.00+ script with full typographic styling."""
        style = track.default_style
        primary_ass = hex_to_ass_color(style.primary_color_hex)
        secondary_ass = hex_to_ass_color(style.highlight_color_hex)
        outline_ass = hex_to_ass_color(style.outline_color_hex)
        back_ass = hex_to_ass_color(
            style.background_box_color_hex if style.background_box else style.shadow_color_hex,
            default_alpha=128 if style.background_box else 0,
        )

        bold_val = -1 if style.bold else 0
        italic_val = -1 if style.italic else 0
        border_style = 3 if style.background_box else 1
        align_code = alignment_to_ass_numpad(style.alignment)

        header = f"""[Script Info]
; Script generated by HyperEdit Pro v2.0
Title: {title}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{primary_ass},{secondary_ass},{outline_ass},{back_ass},{bold_val},{italic_val},0,0,100,100,{style.letter_spacing},0,{border_style},{style.outline_width},{style.shadow_offset},{align_code},{style.margin_h},{style.margin_h},{style.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines: List[str] = []
        track.sort_cues()

        for cue in track.cues:
            cue_style = cue.style_override or style
            start_str = ms_to_ass_time(cue.start_ms)
            end_str = ms_to_ass_time(cue.end_ms)

            cue_text = cue.text
            if cue_style.all_caps:
                cue_text = cue_text.upper()

            # Escape standard ASS special characters in text (\N for newline)
            formatted_text = cue_text.replace("\r\n", r"\N").replace("\n", r"\N")

            dialogue_lines.append(
                f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{formatted_text}"
            )

        return header + "\n".join(dialogue_lines) + "\n"

