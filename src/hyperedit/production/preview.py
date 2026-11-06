"""Fast low-resolution preflight preview and technical validator."""

from pathlib import Path
import shutil
import subprocess
from typing import Optional, Tuple

from hyperedit.core.exceptions import RenderExecutionError
from hyperedit.core.models.export import ExportPreset, HardwareAccel
from hyperedit.core.models.project import Project
from hyperedit.production.models import ProductionMode
from hyperedit.rendering.compiler import FiltergraphCompiler


class FastPreviewGenerator:
    """Generates low-overhead technical previews to validate filtergraphs before master render."""

    def __init__(self, ffmpeg_bin: Optional[str] = None) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")
        self.compiler = FiltergraphCompiler()

    def generate_preview(
        self,
        project: Project,
        mode: ProductionMode,
        output_file: Path | str,
    ) -> Tuple[Path, float]:
        """Render a fast low-resolution preview to verify technical integrity.

        Returns:
            (preview_path, render_elapsed_seconds)
        """
        import time

        start_time = time.perf_counter()
        preview_path = Path(output_file).resolve()
        preview_path.parent.mkdir(parents=True, exist_ok=True)

        # Scale down resolution according to production mode
        orig_w = project.settings.width
        orig_h = project.settings.height
        is_vertical = orig_h > orig_w

        if mode == ProductionMode.FAST:
            prev_w, prev_h = (360, 640) if is_vertical else (640, 360)
            prev_fps = min(30.0, project.settings.fps)
            max_duration = min(3.0, project.duration_seconds)
        elif mode == ProductionMode.BALANCED:
            prev_w, prev_h = (540, 960) if is_vertical else (960, 540)
            prev_fps = min(30.0, project.settings.fps)
            max_duration = min(5.0, project.duration_seconds)
        else:  # CINEMATIC
            prev_w, prev_h = (720, 1280) if is_vertical else (1280, 720)
            prev_fps = project.settings.fps
            max_duration = min(8.0, project.duration_seconds)

        # Ensure even dimensions
        prev_w = (prev_w // 2) * 2
        prev_h = (prev_h // 2) * 2

        preset = ExportPreset(
            name="technical_preview",
            width=prev_w,
            height=prev_h,
            fps=prev_fps,
            video_bitrate_kbps=1500,
            audio_bitrate_kbps=96,
            audio_sample_rate=48000,
            hwaccel=HardwareAccel.NONE,  # Use software CPU for preflight preview
        )

        input_args, filter_complex, output_maps, _ = self.compiler.compile(project, preset)

        cmd = [
            self.ffmpeg_bin,
            "-y",
            *input_args,
            "-filter_complex",
            filter_complex,
            *output_maps,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-ar",
            "48000",
            "-t",
            f"{max_duration:.3f}",
            str(preview_path),
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            err = proc.stderr or "Unknown preview FFmpeg failure"
            raise RenderExecutionError(f"Technical preview preflight failed (code {proc.returncode}):\n{err}")

        if not preview_path.exists() or preview_path.stat().st_size == 0:
            raise RenderExecutionError(f"Preview file not written: {preview_path}")

        elapsed = time.perf_counter() - start_time
        return preview_path, elapsed

