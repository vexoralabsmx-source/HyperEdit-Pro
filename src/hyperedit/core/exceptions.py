"""HyperEdit Pro exception hierarchy."""

from typing import Any, Dict, Optional


class HyperEditError(Exception):
    """Base exception for all HyperEdit Pro errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ProjectValidationError(HyperEditError):
    """Raised when project JSON or parameters fail schema validation."""
    pass


class MediaNotFoundError(HyperEditError):
    """Raised when a media file cannot be found on disk."""
    pass


class MediaProbeError(HyperEditError):
    """Raised when ffprobe fails to parse or read a media file."""
    pass


class DependencyMissingError(HyperEditError):
    """Raised when a required system tool (ffmpeg, ffprobe) or library is missing."""
    pass


class FiltergraphCompileError(HyperEditError):
    """Raised when constructing an invalid FFmpeg filter complex."""
    pass


class RenderExecutionError(HyperEditError):
    """Raised when FFmpeg execution terminates with a non-zero exit code."""
    pass


class TimelineIntegrityError(HyperEditError):
    """Raised when timeline tracks or clips have invalid overlaps, gaps, or out-of-bound cuts."""
    pass


class AdapterError(HyperEditError):
    """Raised when an external adapter (e.g. HyperFrames) fails to communicate or execute."""
    pass

