"""Execution engine for rendering compiled timelines to playable delivery files."""

from pathlib import Path
import shutil
import subprocess
from typing import Callable, Optional

from hyperedit.core.exceptions import DependencyMissingError, RenderExecutionError
from hyperedit.core.models.export import ExportPreset, HardwareAccel
from hyperedit.core.models.project import Project
from hyperedit.core.protocols import RenderEngineProtocol
from hyperedit.diagnostics.checker import EnvironmentChecker
from hyperedit.rendering.compiler import FiltergraphCompiler


class RenderEngine(RenderEngineProtocol):
    """Executes FFmpeg rendering for HyperEdit Pro compositions."""

    def __init__(
        self,
        ffmpeg_bin: Optional[str] = None,
        compiler: Optional[FiltergraphCompiler] = None,
    ) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")
        self.compiler = compiler or FiltergraphCompiler()

    def compile_filtergraph(self, project: Project, preset: ExportPreset) -> str:
        """Return the compiled -filter_complex string for inspection."""
        _, fc, _, _ = self.compiler.compile(project, preset)
        return fc

    def render_project(
        self,
        project: Project,
        preset: ExportPreset,
        output_file: Path | str,
        progress_callback: Optional[Callable[[float, float], None]] = None,
    ) -> Path:
        """Render complete timeline to disk as playable video file."""
        if not self.ffmpeg_bin:
            raise DependencyMissingError("ffmpeg binary not found in PATH.")

        dst_path = Path(output_file).resolve()
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        input_args, filter_complex, output_maps, duration_sec = self.compiler.compile(project, preset)

        # Detect video encoder (Hardware acceleration vs libx264)
        video_encoder = "libx264"
        if preset.hwaccel in (HardwareAccel.AUTO, HardwareAccel.NVENC):
            checker = EnvironmentChecker(ffmpeg_bin=self.ffmpeg_bin)
            report = checker.run_all_checks()
            if "h264_nvenc" in report.hardware_encoders:
                video_encoder = "h264_nvenc"

        cmd = [
            self.ffmpeg_bin,
            "-y",
            *input_args,
            "-filter_complex",
            filter_complex,
            *output_maps,
            "-c:v",
            video_encoder,
            "-pix_fmt",
            preset.pixel_format,
            "-c:a",
            "aac",
            "-b:a",
            f"{preset.audio_bitrate_kbps}k",
            "-ar",
            str(preset.audio_sample_rate),
            "-t",
            f"{duration_sec:.4f}",
            str(dst_path),
        ]

        # Execute FFmpeg
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0 and video_encoder != "libx264" and preset.hwaccel == HardwareAccel.AUTO:
            # Automatic fallback to software encoding if hardware encoder fails at runtime
            cmd_fallback = list(cmd)
            for idx, arg in enumerate(cmd_fallback):
                if arg == "-c:v" and idx + 1 < len(cmd_fallback):
                    cmd_fallback[idx + 1] = "libx264"
                    break
            res = subprocess.run(cmd_fallback, capture_output=True, text=True, check=False)

        if res.returncode != 0:
            err_msg = res.stderr or "Unknown FFmpeg render error"
            raise RenderExecutionError(f"Rendering failed (code {res.returncode}):\n{err_msg}")

        if not dst_path.exists() or dst_path.stat().st_size == 0:
            raise RenderExecutionError(f"Rendered file is empty or was not created: {dst_path}")

        return dst_path

