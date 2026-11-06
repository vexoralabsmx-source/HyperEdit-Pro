"""Blender 3D headless rendering and timeline integration adapter for HyperEdit Pro."""

import glob
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

from hyperedit.core.exceptions import AdapterError, DependencyMissingError, MediaNotFoundError
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project
from hyperedit.core.models.timeline import Clip, Track, TrackKind
from hyperedit.media.prober import FFprobeProber
from hyperedit.vfx.models import (
    BlenderRenderConfig,
    BlenderRenderEngine,
    BlenderRenderResult,
)


class BlenderAdapter:
    """Orchestrates headless 3D renders from Blender and imports assets into HyperEdit Pro timelines."""

    def __init__(self, blender_bin: Optional[str] = None) -> None:
        self.blender_bin = blender_bin or self._find_blender_binary()

    @staticmethod
    def _find_blender_binary() -> Optional[str]:
        """Auto-detect Blender executable across standard OS install locations."""
        # 1. System PATH
        which_path = shutil.which("blender")
        if which_path:
            return which_path

        # 2. Windows standard installations
        if os.name == "nt":
            candidates = glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe")
            if candidates:
                # Return the highest version found
                return sorted(candidates)[-1]
            # Check local AppData
            appdata_candidates = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation\Blender *\blender.exe"))
            if appdata_candidates:
                return sorted(appdata_candidates)[-1]

        # 3. macOS standard installations
        elif os.uname().sysname == "Darwin":
            mac_app = "/Applications/Blender.app/Contents/MacOS/blender"
            if Path(mac_app).is_file():
                return mac_app

        # 4. Linux standard installations
        linux_paths = ["/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender"]
        for lp in linux_paths:
            if Path(lp).is_file():
                return lp

        return None

    def is_available(self) -> bool:
        """Check if Blender CLI is installed and executable."""
        return bool(self.blender_bin and Path(self.blender_bin).is_file())

    def get_version(self) -> Optional[str]:
        """Query Blender version string."""
        if not self.is_available():
            return None
        try:
            res = subprocess.run([self.blender_bin, "--version"], capture_output=True, text=True, check=False, timeout=10)
            if res.returncode == 0:
                first_line = res.stdout.strip().split("\n")[0]
                return first_line
        except Exception:
            return None
        return None

    def build_render_command(self, config: BlenderRenderConfig) -> List[str]:
        """Build the deterministic headless CLI execution command for Blender."""
        bin_path = self.blender_bin or "blender"
        scene_path = Path(config.scene_file).resolve()

        cmd = [
            str(bin_path),
            "-b",
            str(scene_path),
            "-E",
            config.engine.value,
        ]

        if config.script_file:
            script_path = Path(config.script_file).resolve()
            cmd.extend(["-P", str(script_path)])

        cmd.extend([
            "-s", str(config.start_frame),
            "-e", str(config.end_frame),
            "-o", str(config.output_pattern),
            "-a",  # Render animation range
        ])

        return cmd

    def render_scene(self, config: BlenderRenderConfig) -> BlenderRenderResult:
        """Execute headless Blender render and collect output files."""
        if not self.is_available():
            raise DependencyMissingError(
                "Blender binary not found. Please install Blender or provide path via blender_bin."
            )

        cmd = self.build_render_command(config)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                err = res.stderr.strip() or res.stdout.strip() or "Unknown Blender render error"
                raise AdapterError(f"Blender render execution failed (code {res.returncode}):\n{err}")
        except Exception as e:
            if isinstance(e, AdapterError):
                raise
            raise AdapterError(f"Failed to execute Blender: {e}") from e

        # Resolve output directory to collect rendered frames
        out_pattern = Path(config.output_pattern)
        parent_dir = out_pattern.parent
        stem_prefix = out_pattern.name.split("#")[0]
        rendered_files = sorted(str(p) for p in parent_dir.glob(f"{stem_prefix}*.*"))

        return BlenderRenderResult(
            success=True,
            output_files=rendered_files,
            total_frames=len(rendered_files),
            is_transparent=config.transparent_background,
            diagnostics=f"Rendered {len(rendered_files)} frames with {config.engine.value}",
        )

    def import_render_to_timeline(
        self,
        project: Project,
        rendered_media_path: Path | str,
        track_id: str = "V2",
        start_frame: int = 0,
        name: Optional[str] = None,
    ) -> Clip:
        """Probe and mount rendered 3D visual asset directly onto the project timeline."""
        med_path = Path(rendered_media_path).resolve()
        if not med_path.is_file():
            raise MediaNotFoundError(f"Rendered 3D asset not found: {med_path}")

        prober = FFprobeProber()
        asset_info = prober.probe_file(med_path)
        fps = project.fps

        pv = asset_info.primary_video
        w = pv.width if pv else project.settings.width
        h = pv.height if pv else project.settings.height
        codec = pv.codec if pv else "prores"

        # Register in media pool
        asset_id = f"blender_{med_path.stem}"
        media_asset = MediaAsset(
            asset_id=asset_id,
            file_path=str(med_path),
            file_size_bytes=med_path.stat().st_size,
            duration_seconds=asset_info.duration_seconds,
            width=w,
            height=h,
            fps=fps,
            codec_video=codec,
        )
        project.media_pool.add_asset(media_asset)

        # Locate or create target video track
        track = project.timeline.get_track(track_id)
        if not track:
            track = Track(
                track_id=track_id,
                name=f"3D Visual Track ({track_id})",
                kind=TrackKind.VIDEO,
                index=len(project.timeline.tracks) + 1,
            )
            project.timeline.add_track(track)

        clip_duration_frames = int(round(asset_info.duration_seconds * fps))
        clip = Clip(
            clip_id=f"clip_{asset_id}",
            asset_id=asset_id,
            name=name or med_path.stem,
            in_frame=0,
            out_frame=max(1, clip_duration_frames),
            timeline_start_frame=start_frame,
        )
        track.clips.append(clip)
        track.sort_clips()
        return clip

