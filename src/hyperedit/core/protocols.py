"""Public contract interfaces (typing.Protocol) for HyperEdit Pro subsystems."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from hyperedit.core.models.captions import SubtitleTrack
from hyperedit.core.models.export import ExportPreset
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project
from hyperedit.core.models.timeline import Clip, Timeline, Track


@runtime_checkable
class MediaProberProtocol(Protocol):
    """Contract for probing media files and extracting technical stream metadata."""

    def probe_file(self, file_path: Path | str) -> MediaAsset:
        """Inspect file using ffprobe and return a populated MediaAsset."""
        ...

    def generate_waveform(self, file_path: Path | str, output_path: Path | str, width: int = 1920, height: int = 240) -> Path:
        """Render audio waveform visualization image."""
        ...

    def extract_thumbnail(self, file_path: Path | str, output_path: Path | str, frame_time_seconds: float = 0.0) -> Path:
        """Extract a single frame image thumbnail at the given timestamp."""
        ...


@runtime_checkable
class TimelineEngineProtocol(Protocol):
    """Contract for non-linear timeline operations and editing logic."""

    def insert_clip(self, timeline: Timeline, track_id: str, clip: Clip, ripple: bool = False) -> Timeline:
        """Insert a clip onto a track, optionally rippling subsequent clips."""
        ...

    def split_clip(self, timeline: Timeline, track_id: str, clip_id: str, split_frame: int) -> tuple[Clip, Clip]:
        """Split a clip into two separate segments at the specified timeline frame."""
        ...

    def trim_clip(self, timeline: Timeline, track_id: str, clip_id: str, in_frame: Optional[int] = None, out_frame: Optional[int] = None) -> Clip:
        """Modify in-point or out-point of an existing clip."""
        ...

    def ripple_delete(self, timeline: Timeline, track_id: str, clip_id: str) -> Timeline:
        """Remove a clip and close the gap by pulling later clips backward."""
        ...


@runtime_checkable
class RenderEngineProtocol(Protocol):
    """Contract for compiling filtergraphs and executing video renders via FFmpeg."""

    def compile_filtergraph(self, project: Project, preset: ExportPreset) -> str:
        """Compile a complete deterministic FFmpeg -filter_complex string."""
        ...

    def render_project(
        self,
        project: Project,
        preset: ExportPreset,
        output_file: Path | str,
        progress_callback: Optional[Callable[[float, float], None]] = None,
    ) -> Path:
        """Execute FFmpeg render pipeline to produce output media."""
        ...


@runtime_checkable
class AudioMixerProtocol(Protocol):
    """Contract for multi-track audio bus mixing, sidechain ducking and EBU R128 loudness."""

    def build_audio_filterchain(self, project: Project) -> str:
        """Generate audio filter graph connections for volume, ducking, EQ and loudness."""
        ...

    def analyze_loudness(self, audio_file: Path | str) -> Dict[str, float]:
        """Analyze integrated LUFS, LRA and True Peak of an audio track."""
        ...


@runtime_checkable
class CaptionsEngineProtocol(Protocol):
    """Contract for generating and styling captions (SRT, WebVTT, ASS)."""

    def export_srt(self, track: SubtitleTrack, output_path: Path | str) -> Path:
        """Export subtitle track to SubRip (.srt) format."""
        ...

    def export_vtt(self, track: SubtitleTrack, output_path: Path | str) -> Path:
        """Export subtitle track to WebVTT (.vtt) format."""
        ...

    def export_ass(self, track: SubtitleTrack, output_path: Path | str, width: int = 1920, height: int = 1080) -> Path:
        """Export subtitle track to Advanced SubStation Alpha (.ass) format with styling."""
        ...

    def build_burn_filter(self, track: SubtitleTrack, ass_path: Path | str) -> str:
        """Generate FFmpeg subtitles/ass filter argument for burning into video."""
        ...


@runtime_checkable
class MotionEngineProtocol(Protocol):
    """Contract for keyframed spatial motion, cropping, and Ken Burns effects."""

    def interpolate_transform(self, clip: Clip, current_frame: int) -> Dict[str, float]:
        """Calculate spatial transform parameters at a specific frame index."""
        ...

    def build_video_filter(self, clip: Clip, target_w: int, target_h: int) -> str:
        """Generate FFmpeg scale, pad, crop, and overlay filters for clip transform."""
        ...


@runtime_checkable
class TrackingEngineProtocol(Protocol):
    """Contract for visual point/object tracking and auto-reframing."""

    def track_bounding_box(self, video_path: Path | str, start_frame: int, end_frame: int, initial_bbox: tuple[float, float, float, float]) -> List[tuple[float, float, float, float]]:
        """Track bounding box across frame range."""
        ...

    def calculate_auto_reframe(self, video_path: Path | str, target_aspect: str = "9:16") -> List[Dict[str, Any]]:
        """Compute camera pan/crop trajectory to reframe landscape video to portrait/square."""
        ...


@runtime_checkable
class IntelligenceEngineProtocol(Protocol):
    """Contract for audiovisual AI analysis: scene cuts, silence detection, speech-to-text."""

    def detect_scenes(self, video_path: Path | str, threshold: float = 0.3) -> List[tuple[float, float]]:
        """Detect scene cut boundaries (start_time, end_time)."""
        ...

    def detect_silence(self, audio_path: Path | str, silence_threshold_db: float = -35.0, min_duration_sec: float = 0.5) -> List[tuple[float, float]]:
        """Detect silent sections in audio for automated jump-cuts."""
        ...


@runtime_checkable
class ColorGradeProtocol(Protocol):
    """Contract for primary color adjustments, ASC-CDL and 3D LUT pipelines."""

    def build_color_filter(self, project: Project, track_or_clip: Any) -> str:
        """Compile color adjustments and LUT applications into FFmpeg video filter string."""
        ...


@runtime_checkable
class QAEngineProtocol(Protocol):
    """Contract for automated audiovisual quality assurance checks."""

    def verify_black_frames(self, video_path: Path | str, max_duration_sec: float = 0.5) -> List[Dict[str, Any]]:
        """Scan for accidental black frame gaps in rendered video."""
        ...

    def verify_freeze_frames(self, video_path: Path | str, max_duration_sec: float = 1.0) -> List[Dict[str, Any]]:
        """Scan for frozen video frames."""
        ...

    def verify_audio_clipping(self, audio_path: Path | str) -> bool:
        """Check if audio waveform exceeds 0.0 dBFS true peak."""
        ...

    def run_full_qa(self, video_path: Path | str, target_preset: ExportPreset) -> Dict[str, Any]:
        """Execute complete QA suite and return structured compliance report."""
        ...


@runtime_checkable
class HyperFramesAdapterProtocol(Protocol):
    """Contract for integrating HyperFrames HTML motion graphics into HyperEdit Pro."""

    def is_hyperframes_available(self) -> bool:
        """Check if HyperFrames CLI (npx hyperframes) is detected and functional."""
        ...

    def render_composition(
        self,
        project_dir: Path | str,
        composition_id: str,
        output_path: Path | str,
        transparent: bool = True,
    ) -> Path:
        """Invoke HyperFrames headless renderer to produce video asset with alpha channel."""
        ...

    def import_as_clip(
        self,
        project: Project,
        hf_project_dir: Path | str,
        composition_id: str,
        target_track_id: str,
        timeline_start_frame: int,
    ) -> Clip:
        """Render and mount a HyperFrames composition onto the timeline."""
        ...

