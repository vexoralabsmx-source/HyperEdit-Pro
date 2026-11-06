"""HyperFrames kinetic typography adapter for HTML/CSS/GSAP motion captions."""

import html
from pathlib import Path
import shutil
import subprocess
from typing import Optional

from hyperedit.captions.models import (
    KineticAnimationMode,
    SubtitleStyle,
    SubtitleTrack,
)
from hyperedit.core.exceptions import DependencyMissingError, RenderExecutionError


class HyperFramesCaptionsAdapter:
    """Adapter bridging HyperEdit Pro subtitle tracks into HyperFrames HTML motion graphic compositions."""

    def __init__(self, hyperframes_bin: Optional[str] = None) -> None:
        self.hyperframes_bin = hyperframes_bin or shutil.which("hyperframes")

    def export_html_composition(
        self,
        track: SubtitleTrack,
        output_html: Path | str,
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
    ) -> Path:
        """Generate a standalone HTML/CSS/GSAP kinetic typography composition adhering to HyperFrames contract."""
        out_path = Path(output_html).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        from hyperedit.captions.kinetic import estimate_word_timestamps

        track.sort_cues()
        total_duration_sec = (track.cues[-1].end_ms / 1000.0) if track.cues else 5.0
        style = track.default_style

        # Generate HTML markup for cues and words
        cues_html = []
        for cue_idx, cue in enumerate(track.cues):
            words = cue.words if cue.words else estimate_word_timestamps(cue)
            words_markup = []

            for w in words:
                w_start_sec = w.start_ms / 1000.0
                w_end_sec = w.end_ms / 1000.0
                escaped_text = html.escape(w.word.upper() if style.all_caps else w.word)
                words_markup.append(
                    f'<span class="kinetic-word" data-start="{w_start_sec:.3f}" data-end="{w_end_sec:.3f}">{escaped_text}</span>'
                )

            cue_start_sec = cue.start_ms / 1000.0
            cue_end_sec = cue.end_ms / 1000.0
            cues_html.append(
                f'<div class="kinetic-cue" id="cue-{cue_idx}" data-start="{cue_start_sec:.3f}" data-end="{cue_end_sec:.3f}">\n'
                f'  {" ".join(words_markup)}\n'
                f'</div>'
            )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HyperEdit Pro — HyperFrames Kinetic Captions</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      width: {width}px;
      height: {height}px;
      background: transparent;
      overflow: hidden;
      font-family: "{style.font_name}", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    #stage {{
      position: relative;
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      align-items: center;
      padding-bottom: {style.margin_v}px;
      padding-left: {style.margin_h}px;
      padding-right: {style.margin_h}px;
    }}
    .kinetic-cue {{
      display: none;
      text-align: center;
      line-height: 1.25;
      font-size: {style.font_size}px;
      font-weight: {"bold" if style.bold else "normal"};
      color: {style.primary_color_hex};
      text-shadow: 0 0 {style.outline_width}px {style.outline_color_hex},
                   {style.shadow_offset}px {style.shadow_offset}px 0px {style.shadow_color_hex};
      {"background: " + style.background_box_color_hex + "; padding: 12px 24px; border-radius: 8px;" if style.background_box else ""}
    }}
    .kinetic-cue.active {{
      display: block;
    }}
    .kinetic-word {{
      display: inline-block;
      transition: color 0.12s ease, transform 0.12s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}
    .kinetic-word.highlighted {{
      color: {style.highlight_color_hex};
      transform: scale({"1.15" if style.animation_mode == KineticAnimationMode.POP_SCALE else "1.06"});
    }}
  </style>
</head>
<body>
  <div id="stage" data-duration="{total_duration_sec:.3f}" data-fps="{fps}">
    {"".join(cues_html)}
  </div>

  <script>
    // HyperFrames deterministic timeline runner
    const cues = document.querySelectorAll('.kinetic-cue');
    const words = document.querySelectorAll('.kinetic-word');

    function updateTime(currentTime) {{
      cues.forEach(cue => {{
        const start = parseFloat(cue.dataset.start);
        const end = parseFloat(cue.dataset.end);
        if (currentTime >= start && currentTime < end) {{
          cue.classList.add('active');
        }} else {{
          cue.classList.remove('active');
        }}
      }});

      words.forEach(word => {{
        const start = parseFloat(word.dataset.start);
        const end = parseFloat(word.dataset.end);
        if (currentTime >= start && currentTime < end) {{
          word.classList.add('highlighted');
        }} else {{
          word.classList.remove('highlighted');
        }}
      }});
    }}

    // Exported HyperFrames seek hook
    window.seek = function(timeSec) {{
      updateTime(timeSec);
    }};

    // Auto-playback preview if loaded directly in browser
    let startTimestamp = null;
    function step(timestamp) {{
      if (!startTimestamp) startTimestamp = timestamp;
      const progressSec = ((timestamp - startTimestamp) / 1000) % {total_duration_sec:.3f};
      updateTime(progressSec);
      requestAnimationFrame(step);
    }}
    requestAnimationFrame(step);
  </script>
</body>
</html>
"""
        out_path.write_text(html_content, encoding="utf-8")
        return out_path

    def render_overlay_clip(
        self,
        html_file: Path | str,
        output_video: Path | str,
    ) -> Path:
        """Render the HTML composition to transparent video overlay using HyperFrames CLI if available."""
        if not self.hyperframes_bin:
            raise DependencyMissingError(
                "HyperFrames CLI ('hyperframes') not found in PATH. "
                "Install HyperFrames or use native FFmpeg libass burning."
            )

        in_html = Path(html_file).resolve()
        out_clip = Path(output_video).resolve()
        out_clip.parent.mkdir(parents=True, exist_ok=True)

        cmd = [self.hyperframes_bin, "render", str(in_html), "-o", str(out_clip)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                raise RenderExecutionError(f"HyperFrames render failed: {proc.stderr}")
        except Exception as e:
            raise RenderExecutionError(f"HyperFrames render execution error: {e}") from e

        return out_clip
