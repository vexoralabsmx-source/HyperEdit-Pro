"""Real environment diagnostics engine for HyperEdit Pro."""

import importlib
from enum import Enum
import platform
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiagnosticStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


class DiagnosticItem(BaseModel):
    """An individual diagnostic check result."""

    name: str
    status: DiagnosticStatus
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    remediation: Optional[str] = Field(default=None)


class DiagnosticReport(BaseModel):
    """Aggregated environment diagnosis report."""

    overall_status: DiagnosticStatus
    python_version: str
    os_info: str
    ffmpeg_detected: bool
    ffprobe_detected: bool
    hardware_encoders: List[str] = Field(default_factory=list)
    available_filters: List[str] = Field(default_factory=list)
    optional_packages: Dict[str, bool] = Field(default_factory=dict)
    hyperframes_available: bool = False
    checks: List[DiagnosticItem] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(c.status == DiagnosticStatus.ERROR for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.status == DiagnosticStatus.WARNING for c in self.checks)


class EnvironmentChecker:
    """Executes real system and dependency checks."""

    def __init__(self, ffmpeg_bin: Optional[str] = None, ffprobe_bin: Optional[str] = None) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")
        self.ffprobe_bin = ffprobe_bin or shutil.which("ffprobe")

    def run_all_checks(self) -> DiagnosticReport:
        checks: List[DiagnosticItem] = []

        # 1. Python check
        py_check = self._check_python()
        checks.append(py_check)

        # 2. FFmpeg check
        ffmpeg_check, ffmpeg_version, raw_encoders, raw_filters = self._check_ffmpeg()
        checks.append(ffmpeg_check)

        # 3. FFprobe check
        ffprobe_check, ffprobe_version = self._check_ffprobe()
        checks.append(ffprobe_check)

        # 4. Hardware Encoders check
        hw_check, detected_hw = self._check_hardware_encoders(raw_encoders)
        checks.append(hw_check)

        # 5. FFmpeg Filters check
        filters_check, detected_filters = self._check_filters(raw_filters)
        checks.append(filters_check)

        # 6. Optional Python packages check
        pkg_check, pkg_status = self._check_optional_packages()
        checks.append(pkg_check)

        # 7. HyperFrames Integration check
        hf_check, hf_available = self._check_hyperframes()
        checks.append(hf_check)

        # Calculate overall status
        if any(c.status == DiagnosticStatus.ERROR for c in checks):
            overall = DiagnosticStatus.ERROR
        elif any(c.status == DiagnosticStatus.WARNING for c in checks):
            overall = DiagnosticStatus.WARNING
        else:
            overall = DiagnosticStatus.OK

        return DiagnosticReport(
            overall_status=overall,
            python_version=platform.python_version(),
            os_info=f"{platform.system()} {platform.release()} ({platform.machine()})",
            ffmpeg_detected=(ffmpeg_check.status != DiagnosticStatus.ERROR),
            ffprobe_detected=(ffprobe_check.status != DiagnosticStatus.ERROR),
            hardware_encoders=detected_hw,
            available_filters=detected_filters,
            optional_packages=pkg_status,
            hyperframes_available=hf_available,
            checks=checks,
        )

    def _check_python(self) -> DiagnosticItem:
        ver = sys.version_info
        ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
        if ver.major == 3 and ver.minor >= 11:
            return DiagnosticItem(
                name="Python Runtime",
                status=DiagnosticStatus.OK,
                message=f"Python {ver_str} satisfies minimum requirement (>= 3.11)",
                details={"version": ver_str, "executable": sys.executable},
            )
        return DiagnosticItem(
            name="Python Runtime",
            status=DiagnosticStatus.ERROR,
            message=f"Python {ver_str} does not satisfy minimum requirement (>= 3.11)",
            details={"version": ver_str, "executable": sys.executable},
            remediation="Upgrade Python to version 3.11 or later.",
        )

    def _check_ffmpeg(self) -> tuple[DiagnosticItem, Optional[str], List[str], List[str]]:
        if not self.ffmpeg_bin:
            return (
                DiagnosticItem(
                    name="FFmpeg Binary",
                    status=DiagnosticStatus.ERROR,
                    message="ffmpeg executable not found in system PATH",
                    remediation="Install FFmpeg (e.g. winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg) and add to PATH.",
                ),
                None,
                [],
                [],
            )

        try:
            res = subprocess.run(
                [self.ffmpeg_bin, "-version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            first_line = res.stdout.splitlines()[0] if res.stdout else "unknown"
            match = re.search(r"ffmpeg version ([^\s]+)", first_line)
            version_str = match.group(1) if match else first_line

            # Fetch encoders list
            encoders_res = subprocess.run(
                [self.ffmpeg_bin, "-encoders"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            encoders = encoders_res.stdout.splitlines() if encoders_res.stdout else []

            # Fetch filters list
            filters_res = subprocess.run(
                [self.ffmpeg_bin, "-filters"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            filters = filters_res.stdout.splitlines() if filters_res.stdout else []

            return (
                DiagnosticItem(
                    name="FFmpeg Binary",
                    status=DiagnosticStatus.OK,
                    message=f"FFmpeg {version_str} operational",
                    details={"path": str(self.ffmpeg_bin), "version": version_str},
                ),
                version_str,
                encoders,
                filters,
            )
        except Exception as e:
            return (
                DiagnosticItem(
                    name="FFmpeg Binary",
                    status=DiagnosticStatus.ERROR,
                    message=f"Failed to execute ffmpeg: {e}",
                    remediation="Ensure FFmpeg binary is not corrupted and has execution permissions.",
                ),
                None,
                [],
                [],
            )

    def _check_ffprobe(self) -> tuple[DiagnosticItem, Optional[str]]:
        if not self.ffprobe_bin:
            return (
                DiagnosticItem(
                    name="FFprobe Binary",
                    status=DiagnosticStatus.ERROR,
                    message="ffprobe executable not found in system PATH",
                    remediation="Ensure ffprobe is installed alongside ffmpeg and accessible in system PATH.",
                ),
                None,
            )

        try:
            res = subprocess.run(
                [self.ffprobe_bin, "-version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            first_line = res.stdout.splitlines()[0] if res.stdout else "unknown"
            match = re.search(r"ffprobe version ([^\s]+)", first_line)
            version_str = match.group(1) if match else first_line
            return (
                DiagnosticItem(
                    name="FFprobe Binary",
                    status=DiagnosticStatus.OK,
                    message=f"FFprobe {version_str} operational",
                    details={"path": str(self.ffprobe_bin), "version": version_str},
                ),
                version_str,
            )
        except Exception as e:
            return (
                DiagnosticItem(
                    name="FFprobe Binary",
                    status=DiagnosticStatus.ERROR,
                    message=f"Failed to execute ffprobe: {e}",
                    remediation="Ensure ffprobe binary is executable.",
                ),
                None,
            )

    def _check_hardware_encoders(self, encoder_lines: List[str]) -> tuple[DiagnosticItem, List[str]]:
        if not encoder_lines:
            return (
                DiagnosticItem(
                    name="Hardware Acceleration",
                    status=DiagnosticStatus.WARNING,
                    message="No encoder information retrieved from FFmpeg",
                    remediation="Software encoding (libx264/libx265) will be used as fallback.",
                ),
                [],
            )

        full_text = "\n".join(encoder_lines)
        known_hw = [
            ("h264_nvenc", "NVIDIA NVENC H.264"),
            ("hevc_nvenc", "NVIDIA NVENC HEVC"),
            ("av1_nvenc", "NVIDIA NVENC AV1"),
            ("h264_qsv", "Intel QuickSync H.264"),
            ("hevc_qsv", "Intel QuickSync HEVC"),
            ("h264_amf", "AMD AMF H.264"),
            ("hevc_amf", "AMD AMF HEVC"),
            ("h264_videotoolbox", "Apple VideoToolbox H.264"),
            ("hevc_videotoolbox", "Apple VideoToolbox HEVC"),
            ("h264_vaapi", "VAAPI H.264"),
            ("hevc_vaapi", "VAAPI HEVC"),
        ]

        detected = [code for code, desc in known_hw if re.search(rf"\b{code}\b", full_text)]

        if detected:
            return (
                DiagnosticItem(
                    name="Hardware Acceleration",
                    status=DiagnosticStatus.OK,
                    message=f"Detected {len(detected)} hardware acceleration encoder(s)",
                    details={"encoders": detected},
                ),
                detected,
            )
        return (
            DiagnosticItem(
                name="Hardware Acceleration",
                status=DiagnosticStatus.WARNING,
                message="No hardware encoders found; software encoding (CPU) active",
                details={"fallback": ["libx264", "libx265"]},
                remediation="For faster renders, install appropriate GPU drivers (NVIDIA, Intel, or AMD).",
            ),
            [],
        )

    def _check_filters(self, filter_lines: List[str]) -> tuple[DiagnosticItem, List[str]]:
        if not filter_lines:
            return (
                DiagnosticItem(
                    name="FFmpeg Core Filters",
                    status=DiagnosticStatus.WARNING,
                    message="Filter capabilities could not be verified",
                ),
                [],
            )

        full_text = "\n".join(filter_lines)
        essential_filters = [
            "loudnorm",
            "subtitles",
            "lut3d",
            "blackdetect",
            "freezedetect",
            "silencedetect",
            "xfade",
            "acrossfade",
            "palettegen",
            "paletteuse",
        ]

        found = [f for f in essential_filters if re.search(rf"\b{f}\b", full_text)]
        missing = [f for f in essential_filters if f not in found]

        if not missing:
            return (
                DiagnosticItem(
                    name="FFmpeg Core Filters",
                    status=DiagnosticStatus.OK,
                    message=f"All {len(essential_filters)} post-production filters verified",
                    details={"verified_filters": found},
                ),
                found,
            )
        return (
            DiagnosticItem(
                name="FFmpeg Core Filters",
                status=DiagnosticStatus.WARNING,
                message=f"Missing {len(missing)} filters: {', '.join(missing)}",
                details={"found": found, "missing": missing},
                remediation="Ensure FFmpeg was compiled with libass and standard filter packages.",
            ),
            found,
        )

    def _check_optional_packages(self) -> tuple[DiagnosticItem, Dict[str, bool]]:
        targets = ["numpy", "scipy", "cv2", "scenedetect", "faster_whisper"]
        results: Dict[str, bool] = {}
        for pkg in targets:
            try:
                importlib.import_module(pkg)
                results[pkg] = True
            except ImportError:
                results[pkg] = False

        installed_count = sum(1 for v in results.values() if v)
        return (
            DiagnosticItem(
                name="Optional AI & Vision Packages",
                status=DiagnosticStatus.OK if installed_count > 0 else DiagnosticStatus.WARNING,
                message=f"{installed_count}/{len(targets)} optional AI/Vision packages present",
                details=results,
                remediation="Install optional packages with `pip install hyperedit[ai,vision]` for automated scene cuts and speech transcription.",
            ),
            results,
        )

    def _check_hyperframes(self) -> tuple[DiagnosticItem, bool]:
        # Check direct PATH executable or npx availability
        hf_path = shutil.which("hyperframes")
        if hf_path:
            return (
                DiagnosticItem(
                    name="HyperFrames Integration",
                    status=DiagnosticStatus.OK,
                    message=f"HyperFrames CLI detected at {hf_path}",
                    details={"path": hf_path},
                ),
                True,
            )

        # Check node
        node_path = shutil.which("node")
        if node_path:
            return (
                DiagnosticItem(
                    name="HyperFrames Integration",
                    status=DiagnosticStatus.OK,
                    message="Node.js detected; HyperFrames can be invoked on-demand via npx",
                    details={"node_path": node_path},
                ),
                True,
            )

        return (
            DiagnosticItem(
                name="HyperFrames Integration",
                status=DiagnosticStatus.WARNING,
                message="HyperFrames CLI and Node.js not detected in PATH",
                remediation="Install Node.js (https://nodejs.org) to enable HTML motion graphics integration with HyperFrames.",
            ),
            False,
        )

