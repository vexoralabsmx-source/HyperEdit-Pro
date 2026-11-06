"""Persistent cache with mtime and chunk-hash invalidation for media probes."""

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel

from hyperedit.media.models import ComprehensiveMediaAsset


def compute_fast_file_signature(path: Path) -> str:
    """Compute a lightweight, deterministic signature without reading multi-gigabyte files.

    Uses file size, mtime nanoseconds, and hashes the first 64KB and last 64KB of data.
    """
    stat = path.stat()
    size = stat.st_size
    mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9))

    h = hashlib.sha256()
    h.update(f"{size}:{mtime_ns}:".encode("utf-8"))

    if size > 0:
        with open(path, "rb") as f:
            # Read first chunk up to 64KB
            chunk_size = min(65536, size)
            h.update(f.read(chunk_size))
            if size > chunk_size * 2:
                # Seek to last 64KB
                f.seek(size - chunk_size)
                h.update(f.read(chunk_size))

    return h.hexdigest()


class CacheEntry(BaseModel):
    """Cached probe record with file signature."""

    signature: str
    asset: ComprehensiveMediaAsset


class MediaCacheManager:
    """Manages persistent cache storage for probed media assets and artifacts."""

    def __init__(self, cache_file: Optional[Path | str] = None) -> None:
        if cache_file:
            self.cache_file = Path(cache_file).resolve()
        else:
            self.cache_file = Path(".hyperedit_cache") / "media_cache_index.json"

        self.entries: Dict[str, CacheEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.cache_file.exists():
            return
        try:
            content = self.cache_file.read_text(encoding="utf-8")
            data = json.loads(content)
            for key, val in data.items():
                self.entries[key] = CacheEntry.model_validate(val)
        except Exception:
            # Cache corruption fallback: reset cache
            self.entries = {}

    def save(self) -> None:
        """Write in-memory cache records to disk atomically."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.cache_file.with_suffix(".tmp")
        serialized = {k: v.model_dump() for k, v in self.entries.items()}
        temp_file.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
        temp_file.replace(self.cache_file)

    def get(self, file_path: Path | str) -> Optional[ComprehensiveMediaAsset]:
        """Retrieve cached asset if file exists and signature is unchanged."""
        path = Path(file_path).resolve()
        if not path.is_file():
            return None

        key = str(path)
        entry = self.entries.get(key)
        if not entry:
            return None

        current_sig = compute_fast_file_signature(path)
        if current_sig != entry.signature:
            # Signature mismatch: invalidated
            del self.entries[key]
            return None

        return entry.asset

    def set(self, file_path: Path | str, asset: ComprehensiveMediaAsset) -> None:
        """Store probed asset in cache."""
        path = Path(file_path).resolve()
        if not path.is_file():
            return

        key = str(path)
        sig = compute_fast_file_signature(path)
        self.entries[key] = CacheEntry(signature=sig, asset=asset)
        self.save()

    def invalidate(self, file_path: Path | str) -> None:
        """Explicitly invalidate a cached file."""
        key = str(Path(file_path).resolve())
        if key in self.entries:
            del self.entries[key]
            self.save()

    def clear(self) -> None:
        """Clear all cache records."""
        self.entries = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

