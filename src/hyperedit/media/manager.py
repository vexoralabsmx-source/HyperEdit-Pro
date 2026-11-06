"""Media pool management, asset caching and artifact generation for HyperEdit Pro."""

from pathlib import Path
from typing import Dict, List, Optional

from hyperedit.core.exceptions import MediaNotFoundError
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project
from hyperedit.media.prober import FFprobeProber


class MediaManager:
    """Manages project media ingestion, caching, and proxy/thumbnail/waveform artifacts."""

    def __init__(self, prober: Optional[FFprobeProber] = None) -> None:
        self.prober = prober or FFprobeProber()

    def add_media(
        self,
        project: Project,
        media_file: Path | str,
        generate_proxy: bool = False,
        generate_waveform: bool = False,
        generate_thumbnail: bool = False,
        assets_dir: Optional[Path | str] = None,
        compute_hash: bool = True,
    ) -> MediaAsset:
        """Probe media file and register it into the project's media pool."""
        path = Path(media_file).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Media file does not exist: {path}")

        asset = self.prober.probe_file(path, compute_hash=compute_hash)

        # Artifact storage root
        base_dir = Path(assets_dir).resolve() if assets_dir else path.parent / ".hyperedit_cache"

        if generate_thumbnail and asset.has_video:
            thumb_path = base_dir / "thumbnails" / f"{asset.asset_id}_thumb.jpg"
            self.prober.extract_thumbnail(path, thumb_path, timestamp_sec=0.5)

        if generate_waveform and asset.has_audio:
            wave_path = base_dir / "waveforms" / f"{asset.asset_id}_waveform.png"
            self.prober.generate_waveform(path, wave_path)

        if generate_proxy and asset.has_video:
            proxy_path = base_dir / "proxies" / f"{asset.asset_id}_proxy.mp4"
            self.prober.create_proxy(path, proxy_path)

        project.media_pool.add_asset(asset)
        return asset

    def verify_assets(self, project: Project) -> Dict[str, bool]:
        """Verify that all media assets in the project media pool exist on disk."""
        status = {}
        for asset_id, asset in project.media_pool.assets.items():
            file_exists = Path(asset.file_path).is_file()
            status[asset_id] = file_exists
        return status

    def get_missing_assets(self, project: Project) -> List[str]:
        """Return list of asset_ids whose source files are missing on disk."""
        statuses = self.verify_assets(project)
        return [asset_id for asset_id, exists in statuses.items() if not exists]

