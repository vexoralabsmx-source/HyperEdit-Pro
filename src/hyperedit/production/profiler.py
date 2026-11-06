"""Resource profiler and compact telemetry reporter for AI Agent production runs."""

import sys
import time
from typing import Dict, List, Optional
from hyperedit.production.models import ProductionMetrics


def get_peak_memory_mb() -> float:
    """Measure peak resident set size (RSS) memory consumption in megabytes cross-platform."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            psapi = ctypes.WinDLL("psapi")
            kernel32 = ctypes.WinDLL("kernel32")
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE

            handle = kernel32.GetCurrentProcess()
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return counters.PeakWorkingSetSize / (1024 * 1024)
            return 0.0
        else:
            import resource

            factor = 1024 * 1024 if sys.platform == "darwin" else 1024
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / factor
    except Exception:
        return 0.0


class ProductionProfiler:
    """Tracks CPU time, elapsed wall time, memory, operations count, and cache telemetry."""

    def __init__(self) -> None:
        self.start_wall: float = 0.0
        self.start_cpu: float = 0.0
        self.analysis_time: float = 0.0
        self.render_time: float = 0.0

        self.operations_total: int = 0
        self.operations_cached: int = 0
        self.re_renders_avoided: int = 0
        self.remediation_attempts: int = 0

        self.stage_timings: Dict[str, float] = {}

    def start(self) -> None:
        self.start_wall = time.perf_counter()
        self.start_cpu = time.process_time()

    def record_operation(self, is_cached: bool = False, was_re_render_avoided: bool = False) -> None:
        self.operations_total += 1
        if is_cached:
            self.operations_cached += 1
        if was_re_render_avoided:
            self.re_renders_avoided += 1

    def add_analysis_time(self, seconds: float) -> None:
        self.analysis_time += seconds

    def add_render_time(self, seconds: float) -> None:
        self.render_time += seconds

    def finish(self) -> ProductionMetrics:
        total_wall = time.perf_counter() - self.start_wall
        total_cpu = time.process_time() - self.start_cpu
        peak_mem = get_peak_memory_mb()

        ratio = (
            (self.operations_cached / self.operations_total)
            if self.operations_total > 0
            else 0.0
        )

        return ProductionMetrics(
            total_elapsed_seconds=round(total_wall, 3),
            analysis_seconds=round(self.analysis_time, 3),
            render_seconds=round(self.render_time, 3),
            operations_total=self.operations_total,
            operations_cached=self.operations_cached,
            cache_hit_ratio=round(ratio, 3),
            re_renders_avoided=self.re_renders_avoided,
            peak_memory_mb=round(peak_mem, 2),
            cpu_seconds=round(total_cpu, 3),
            remediation_attempts=self.remediation_attempts,
        )

    @staticmethod
    def format_compact_summary(
        metrics: ProductionMetrics,
        mode: str,
        output_file: str,
        preview_file: Optional[str] = None,
        remediations: Optional[List[str]] = None,
    ) -> str:
        """Format an ultra-compact, high-density summary for AI Agents."""
        lines = [
            f"**HyperEdit Fast Production (`{mode}`) Completed**",
            f"- **Deliverable**: `{output_file}`" + (f" | Preview: `{preview_file}`" if preview_file else ""),
            f"- **Timing**: Total {metrics.total_elapsed_seconds}s (Analysis: {metrics.analysis_seconds}s | Render: {metrics.render_seconds}s | CPU: {metrics.cpu_seconds}s)",
            f"- **Efficiency**: {metrics.operations_total} ops ({metrics.operations_cached} cached, {metrics.re_renders_avoided} re-renders avoided, cache hit ratio: {metrics.cache_hit_ratio * 100:.1f}%)",
            f"- **Resources**: Peak Memory {metrics.peak_memory_mb:.1f} MB",
        ]
        if metrics.remediation_attempts > 0:
            lines.append(f"- **Remediations**: {metrics.remediation_attempts} auto-remediation(s) applied ({', '.join(remediations or [])})")
        return "\n".join(lines)

