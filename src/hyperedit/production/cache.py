"""Multi-tier production cache for intermediate assets, audio analysis, and motion graphics."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from hyperedit.audio.models import BeatInfo
from hyperedit.media.cache import compute_fast_file_signature


class ProductionCache:
    """Manages disk-backed caching of intermediate production assets to prevent duplicate renders."""

    def __init__(self, cache_dir: Path | str = ".hyperedit_cache") -> None:
        self.cache_dir = Path(cache_dir).resolve()
        self.audio_dir = self.cache_dir / "audio"
        self.motion_dir = self.cache_dir / "motion"
        self.preview_dir = self.cache_dir / "preview"
        self.stems_dir = self.cache_dir / "stems"

        for d in (self.cache_dir, self.audio_dir, self.motion_dir, self.preview_dir, self.stems_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.index_file = self.cache_dir / "production_cache_index.json"
        self.index: Dict[str, Any] = self._load_index()
        self.hits: int = 0
        self.misses: int = 0

    def _load_index(self) -> Dict[str, Any]:
        if not self.index_file.exists():
            return {}
        try:
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_index(self) -> None:
        try:
            temp = self.index_file.with_suffix(".tmp")
            temp.write_text(json.dumps(self.index, indent=2), encoding="utf-8")
            temp.replace(self.index_file)
        except Exception:
            pass

    # --- Audio Beat Analysis Caching ---
    def get_audio_beats(self, audio_file: Path | str, bpm_hint: Optional[float] = None) -> Optional[BeatInfo]:
        """Retrieve cached BeatInfo if audio file signature matches."""
        path = Path(audio_file).resolve()
        if not path.is_file():
            return None

        sig = compute_fast_file_signature(path)
        cache_key = f"beats:{sig}:{bpm_hint}"
        entry = self.index.get(cache_key)
        if entry:
            self.hits += 1
            bpm = entry["bpm"]
            interval = entry.get("beat_interval_sec") or (60.0 / bpm if bpm > 0 else 0.5)
            return BeatInfo(
                bpm=bpm,
                confidence=entry.get("confidence", 1.0),
                beat_interval_sec=interval,
                beat_timestamps=entry["beat_timestamps"],
                onset_timestamps=entry.get("onset_timestamps", []),
                time_signature=entry.get("time_signature", "4/4"),
            )
        self.misses += 1
        return None

    def store_audio_beats(
        self,
        audio_file: Path | str,
        beats: BeatInfo,
        bpm_hint: Optional[float] = None,
    ) -> None:
        """Store BeatInfo in persistent cache."""
        path = Path(audio_file).resolve()
        if not path.is_file():
            return

        sig = compute_fast_file_signature(path)
        cache_key = f"beats:{sig}:{bpm_hint}"
        self.index[cache_key] = {
            "bpm": beats.bpm,
            "confidence": beats.confidence,
            "beat_interval_sec": beats.beat_interval_sec,
            "beat_timestamps": beats.beat_timestamps,
            "onset_timestamps": beats.onset_timestamps,
            "time_signature": beats.time_signature,
        }
        self._save_index()

    # --- Motion Graphics Overlay Caching ---
    def get_motion_overlay(
        self,
        template: str,
        title: str,
        subtitle: Optional[str],
        preset: str,
        width: int,
        height: int,
        fps: float,
        duration: float,
        format: str = "mov",
    ) -> Optional[Path]:
        """Retrieve pre-rendered transparent motion graphic video overlay if available."""
        key_raw = f"{template}:{title}:{subtitle}:{preset}:{width}x{height}:{fps}:{duration:.3f}:{format}"
        hash_val = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]
        expected_file = self.motion_dir / f"overlay_{hash_val}.{format}"

        if expected_file.is_file() and expected_file.stat().st_size > 1000:
            self.hits += 1
            return expected_file

        self.misses += 1
        return None

    def store_motion_overlay_path(
        self,
        template: str,
        title: str,
        subtitle: Optional[str],
        preset: str,
        width: int,
        height: int,
        fps: float,
        duration: float,
        source_file: Path | str,
        format: str = "mov",
    ) -> Path:
        """Cache a rendered transparent motion graphic overlay."""
        src = Path(source_file).resolve()
        key_raw = f"{template}:{title}:{subtitle}:{preset}:{width}x{height}:{fps}:{duration:.3f}:{format}"
        hash_val = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]
        dest = self.motion_dir / f"overlay_{hash_val}.{format}"

        if src != dest and src.is_file():
            import shutil
            shutil.copy2(src, dest)

        return dest

    # --- Ducked Audio Stem Caching ---
    def get_ducked_audio(
        self,
        music_file: Path | str,
        dialogue_file: Path | str,
        threshold_db: float,
        attenuation_db: float,
    ) -> Optional[Path]:
        """Retrieve pre-ducked audio stem if signatures match."""
        m_path = Path(music_file).resolve()
        d_path = Path(dialogue_file).resolve()
        if not m_path.is_file() or not d_path.is_file():
            return None

        m_sig = compute_fast_file_signature(m_path)
        d_sig = compute_fast_file_signature(d_path)
        key_raw = f"duck:{m_sig}:{d_sig}:{threshold_db}:{attenuation_db}"
        hash_val = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]
        stem_path = self.stems_dir / f"ducked_{hash_val}.wav"

        if stem_path.is_file() and stem_path.stat().st_size > 4096:
            self.hits += 1
            return stem_path

        self.misses += 1
        return None

    def store_ducked_audio(
        self,
        music_file: Path | str,
        dialogue_file: Path | str,
        threshold_db: float,
        attenuation_db: float,
        ducked_file: Path | str,
    ) -> Path:
        """Cache a ducked audio stem."""
        src = Path(ducked_file).resolve()
        m_path = Path(music_file).resolve()
        d_path = Path(dialogue_file).resolve()

        m_sig = compute_fast_file_signature(m_path)
        d_sig = compute_fast_file_signature(d_path)
        key_raw = f"duck:{m_sig}:{d_sig}:{threshold_db}:{attenuation_db}"
        hash_val = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]
        dest = self.stems_dir / f"ducked_{hash_val}.wav"

        if src != dest and src.is_file():
            import shutil
            shutil.copy2(src, dest)

        return dest

    def clear(self) -> None:
        """Flush all cache directories."""
        import shutil
        for d in (self.audio_dir, self.motion_dir, self.preview_dir, self.stems_dir):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)
        if self.index_file.exists():
            self.index_file.unlink()
        self.index = {}

