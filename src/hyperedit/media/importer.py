"""End-to-end media ingestion, analysis, artifact generation, and project registration."""

from pathlib import Path
from typing import Optional

from hyperedit.core.exceptions import MediaNotFoundError, MediaProbeError
from hyperedit.core.models.media import (
    AudioStreamInfo,
    MediaAsset,
    VideoStreamInfo,
)
from hyperedit.core.models.project import Project
from hyperedit.media.artifacts import MediaArtifactGenerator
from hyperedit.media.cache import MediaCacheManager
from hyperedit.media.models import (
    ComprehensiveMediaAsset,
    MediaArtifacts,
    MediaValidationReport,
)
from hyperedit.media.prober import FFprobeProber
from hyperedit.media.signal import AudioSignalAnalyzer


class MediaImporter:
    """Orchestrates the complete media ingestion pipeline.

    Flow: Import -> Analyze -> Validate -> Create Proxy -> Generate Thumbnails -> Deliver Metadata.
    """

    def __init__(
        self,
        prober: Optional[FFprobeProber] = None,
        artifacts_generator: Optional[MediaArtifactGenerator] = None,
        signal_analyzer: Optional[AudioSignalAnalyzer] = None,
        cache_manager: Optional[MediaCacheManager] = None,
    ) -> None:
        self.prober = prober or FFprobeProber()
        self.artifacts = artifacts_generator or MediaArtifactGenerator()
        self.signal_analyzer = signal_analyzer or AudioSignalAnalyzer()
        self.cache = cache_manager or MediaCacheManager()

    def import_media(
        self,
        media_file: Path | str,
        project: Optional[Project] = None,
        generate_thumbnail: bool = False,
        generate_contact_sheet: bool = False,
        generate_waveform: bool = False,
        generate_proxy: bool = False,
        extract_audio: bool = False,
        analyze_signals: bool = False,
        proxy_scale: str = "720p",
        assets_dir: Optional[Path | str] = None,
    ) -> ComprehensiveMediaAsset:
        """Execute full end-to-end media import pipeline."""
        path = Path(media_file).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Media file does not exist: {path}")

        # Capture original file fingerprint to verify immutability
        initial_stat = path.stat()
        initial_size = initial_stat.st_size
        initial_mtime = initial_stat.st_mtime

        # 1. Validation & Corruption Check
        validation: MediaValidationReport = self.prober.validate_media(path)
        if not validation.is_valid:
            raise MediaProbeError(f"Validation failed for '{path.name}': {validation.error_message}")

        # 2. Cached Probe or Fresh Analysis
        cached_asset = self.cache.get(path)
        if cached_asset:
            asset = cached_asset
        else:
            asset = self.prober.probe_file(path, compute_hash=True)
            self.cache.set(path, asset)

        # 3. Audio Signal Telemetry (if audio present)
        if analyze_signals and asset.has_audio and not asset.signal_metrics:
            asset.signal_metrics = self.signal_analyzer.analyze_signal(path)

        # 4. Artifact Generation
        target_dir = Path(assets_dir).resolve() if assets_dir else path.parent / ".hyperedit_cache"
        artifact_paths = MediaArtifacts(
            thumbnail_path=asset.artifacts.thumbnail_path,
            contact_sheet_path=asset.artifacts.contact_sheet_path,
            waveform_path=asset.artifacts.waveform_path,
            proxy_path=asset.artifacts.proxy_path,
            extracted_audio_path=asset.artifacts.extracted_audio_path,
        )

        # A. Thumbnail
        if generate_thumbnail and asset.has_video:
            thumb_file = target_dir / "thumbnails" / f"{asset.asset_id}_thumb.jpg"
            if not thumb_file.exists():
                self.artifacts.extract_thumbnail(path, thumb_file, timestamp_sec=min(0.5, asset.duration_seconds))
            artifact_paths.thumbnail_path = str(thumb_file)

        # B. Contact Sheet (3x3 grid)
        if generate_contact_sheet and asset.has_video:
            sheet_file = target_dir / "contact_sheets" / f"{asset.asset_id}_sheet.jpg"
            if not sheet_file.exists():
                self.artifacts.generate_contact_sheet(
                    path,
                    sheet_file,
                    duration_seconds=asset.duration_seconds,
                    cols=3,
                    rows=3,
                )
            artifact_paths.contact_sheet_path = str(sheet_file)

        # C. Waveform
        if generate_waveform and asset.has_audio:
            wave_file = target_dir / "waveforms" / f"{asset.asset_id}_waveform.png"
            if not wave_file.exists():
                self.artifacts.generate_waveform(path, wave_file)
            artifact_paths.waveform_path = str(wave_file)

        # D. Proxy
        if generate_proxy and asset.has_video:
            proxy_file = target_dir / "proxies" / f"{asset.asset_id}_proxy_{proxy_scale}.mp4"
            if not proxy_file.exists():
                self.artifacts.create_proxy(path, proxy_file, scale=proxy_scale)
            artifact_paths.proxy_path = str(proxy_file)

        # E. Extracted Audio
        if extract_audio and asset.has_audio:
            audio_stem = target_dir / "audio_stems" / f"{asset.asset_id}_stem.wav"
            if not audio_stem.exists():
                self.artifacts.extract_audio(path, audio_stem)
            artifact_paths.extracted_audio_path = str(audio_stem)

        asset.artifacts = artifact_paths
        self.cache.set(path, asset)

        # 5. Project Registration (if project supplied)
        if project is not None:
            # Map ComprehensiveMediaAsset to core MediaAsset
            v_streams = [
                VideoStreamInfo(
                    index=v.index,
                    codec=v.codec,
                    width=v.width,
                    height=v.height,
                    fps=v.frame_rate_info.fps,
                    duration_seconds=v.duration_seconds,
                    pixel_format=v.pixel_format,
                    bit_depth=v.bit_depth,
                    aspect_ratio=v.aspect_ratio,
                    color_space=v.color_space,
                    color_primaries=v.color_primaries,
                    color_transfer=v.color_transfer,
                    bitrate_kbps=v.bitrate_kbps,
                )
                for v in asset.video_streams
            ]

            a_streams = [
                AudioStreamInfo(
                    index=a.index,
                    codec=a.codec,
                    sample_rate=a.sample_rate,
                    channels=a.channels,
                    channel_layout=a.channel_layout,
                    duration_seconds=a.duration_seconds,
                    bitrate_kbps=a.bitrate_kbps,
                )
                for a in asset.audio_streams
            ]

            core_asset = MediaAsset(
                asset_id=asset.asset_id,
                file_path=str(path),
                format_name=asset.format_name,
                duration_seconds=asset.duration_seconds,
                size_bytes=asset.size_bytes,
                video_streams=v_streams,
                audio_streams=a_streams,
                hash_sha256=asset.hash_sha256,
            )
            project.media_pool.add_asset(core_asset)

        # 6. Safety check: ensure original media was never mutated
        post_stat = path.stat()
        if post_stat.st_size != initial_size or post_stat.st_mtime != initial_mtime:
            raise RuntimeError(f"Safety violation: Original media file was modified during import! {path}")

        return asset

