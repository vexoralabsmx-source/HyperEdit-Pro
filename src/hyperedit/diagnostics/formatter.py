"""Formatting utilities for diagnostic reports."""

import json
from typing import Optional
from hyperedit.diagnostics.checker import DiagnosticReport, DiagnosticStatus


class DiagnosticFormatter:
    """Renders DiagnosticReport into plain text, colored ANSI or JSON."""

    @staticmethod
    def to_json(report: DiagnosticReport, indent: int = 2) -> str:
        return report.model_dump_json(indent=indent)

    @staticmethod
    def to_terminal(report: DiagnosticReport, verbose: bool = False, use_color: bool = True) -> str:
        lines = []

        # Color codes
        green = "\033[92m" if use_color else ""
        yellow = "\033[93m" if use_color else ""
        red = "\033[91m" if use_color else ""
        cyan = "\033[96m" if use_color else ""
        bold = "\033[1m" if use_color else ""
        reset = "\033[0m" if use_color else ""

        # Status badge
        if report.overall_status == DiagnosticStatus.OK:
            badge = f"{green}{bold}[PASSED]{reset}"
        elif report.overall_status == DiagnosticStatus.WARNING:
            badge = f"{yellow}{bold}[WARNING]{reset}"
        else:
            badge = f"{red}{bold}[FAILED]{reset}"

        lines.append(f"{bold}======================================================{reset}")
        lines.append(f"{bold} HyperEdit Pro System & Environment Diagnostics {badge}")
        lines.append(f"{bold}======================================================{reset}")
        lines.append(f"OS: {report.os_info}")
        lines.append(f"Python: {report.python_version}")
        lines.append(f"FFmpeg detected: {'Yes' if report.ffmpeg_detected else 'No'}")
        lines.append(f"FFprobe detected: {'Yes' if report.ffprobe_detected else 'No'}")
        lines.append(f"HyperFrames ready: {'Yes' if report.hyperframes_available else 'No (optional)'}")
        lines.append("------------------------------------------------------")
        lines.append(f"{bold}Component Checks:{reset}")

        for check in report.checks:
            if check.status == DiagnosticStatus.OK:
                icon = f"{green}✓{reset}"
            elif check.status == DiagnosticStatus.WARNING:
                icon = f"{yellow}▲{reset}"
            else:
                icon = f"{red}✗{reset}"

            lines.append(f"  {icon} {bold}{check.name}{reset}: {check.message}")

            if verbose and check.details:
                for k, v in check.details.items():
                    lines.append(f"      {cyan}• {k}:{reset} {v}")

            if check.remediation and check.status != DiagnosticStatus.OK:
                lines.append(f"      {yellow}Remedy:{reset} {check.remediation}")

        lines.append("------------------------------------------------------")
        if report.hardware_encoders:
            hw_str = ", ".join(report.hardware_encoders)
            lines.append(f"{green}Active Hardware Encoders:{reset} {hw_str}")
        else:
            lines.append(f"{yellow}Active Hardware Encoders:{reset} None (CPU fallback)")

        lines.append(f"{bold}======================================================{reset}")
        return "\n".join(lines)

