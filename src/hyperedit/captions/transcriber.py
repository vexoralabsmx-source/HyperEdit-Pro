"""Local AI speech transcription engine utilizing faster-whisper with word-level timestamps."""

from pathlib import Path
from typing import List, Optional

from hyperedit.captions.models import (
    SubtitleCue,
    SubtitleTrack,
    WordTimestamp,
)
from hyperedit.core.exceptions import DependencyMissingError, MediaNotFoundError


class SpeechTranscriber:
    """Acoustic speech-to-text transcriber leveraging local faster-whisper models."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "default",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    @staticmethod
    def is_available() -> bool:
        """Check whether faster-whisper is installed in the local Python environment."""
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def transcribe(
        self,
        audio_or_video_file: Path | str,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        track_id: str = "SUB1",
    ) -> SubtitleTrack:
        """Transcribe speech in an audiovisual file to a structured SubtitleTrack with word timestamps.

        Raises:
            DependencyMissingError: If faster-whisper is not installed.
            MediaNotFoundError: If media file does not exist.
        """
        path = Path(audio_or_video_file).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Media file for transcription not found: {path}")

        if not self.is_available():
            raise DependencyMissingError(
                "Local AI speech recognition requires 'faster-whisper'. "
                "Install it via: pip install faster-whisper\n"
                "HyperEdit Pro does not simulate or invent fake speech transcriptions."
            )

        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

        segments, info = model.transcribe(
            str(path),
            language=language,
            word_timestamps=word_timestamps,
        )

        cues: List[SubtitleCue] = []
        cue_idx = 1

        for segment in segments:
            start_ms = int(round(segment.start * 1000))
            end_ms = int(round(segment.end * 1000))

            words_list: List[WordTimestamp] = []
            if word_timestamps and hasattr(segment, "words") and segment.words:
                for w in segment.words:
                    w_start_ms = int(round(w.start * 1000))
                    w_end_ms = int(round(w.end * 1000))
                    words_list.append(
                        WordTimestamp(
                            word=w.word.strip(),
                            start_ms=w_start_ms,
                            end_ms=max(w_start_ms + 50, w_end_ms),
                            confidence=round(float(getattr(w, "probability", 0.95)), 2),
                        )
                    )

            cues.append(
                SubtitleCue(
                    cue_id=f"cue_{cue_idx:04d}",
                    start_ms=start_ms,
                    end_ms=max(start_ms + 100, end_ms),
                    text=segment.text.strip(),
                    words=words_list,
                )
            )
            cue_idx += 1

        detected_lang = language or getattr(info, "language", "eng")
        track = SubtitleTrack(
            track_id=track_id,
            language=detected_lang,
            cues=cues,
        )
        track.sort_cues()
        return track

