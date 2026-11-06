"""Circuit breaker and deterministic auto-remediation engine for video production."""

from typing import Dict, List
from hyperedit.core.exceptions import ProductionBlockedError


class RemediationCircuitBreaker:
    """Enforces a strict upper bound of 2 automated remediation attempts per error category.

    Prevents infinite LLM reasoning/retry loops and quickly escalates permanent blocks.
    """

    MAX_RETRIES: int = 2

    def __init__(self, max_retries: int = MAX_RETRIES) -> None:
        self.max_retries = max_retries
        self.failure_counts: Dict[str, int] = {}
        self.applied_remediations: List[str] = []

    def record_attempt(self, category: str, error: Exception) -> str:
        """Register a failure. Returns the selected remediation strategy or raises ProductionBlockedError.

        Args:
            category: High-level classification of error (e.g. 'hwaccel', 'subtitles', 'filtergraph', 'dimensions').
            error: The captured exception.

        Returns:
            Strategy name to apply.

        Raises:
            ProductionBlockedError: If failure count exceeds MAX_RETRIES (persists on 3rd attempt).
        """
        current_count = self.failure_counts.get(category, 0) + 1
        self.failure_counts[category] = current_count

        if current_count > self.max_retries:
            raise ProductionBlockedError(
                f"Automated production halted for '{category}': exceeded maximum allowed attempts ({self.max_retries}).\n"
                f"Underlying error: {str(error)}\n"
                f"Applied remediations prior to halt: {', '.join(self.applied_remediations) if self.applied_remediations else 'None'}",
                details={
                    "category": category,
                    "attempts": current_count,
                    "remediations": self.applied_remediations,
                    "underlying_error": str(error),
                },
            )

        # Determine deterministic remediation strategy based on category and attempt index
        remediation_strategy = self._select_strategy(category, current_count, error)
        self.applied_remediations.append(f"[{category} attempt {current_count}]: {remediation_strategy}")
        return remediation_strategy

    def _select_strategy(self, category: str, attempt: int, error: Exception) -> str:
        err_str = str(error).lower()
        cat = category.lower()

        if "hwaccel" in cat or "encoder" in cat or "nvenc" in err_str:
            return "fallback_software_x264"
        elif "subtitle" in cat or "ass" in err_str or "no such filter: 'ass'" in err_str:
            if attempt == 1:
                return "fallback_subtitles_filter"
            return "disable_burned_subtitles"
        elif "dimension" in cat or "divisible" in err_str or "pad" in err_str:
            return "force_even_dimensions"
        elif "filter" in cat or "filtergraph" in cat:
            if attempt == 1:
                return "simplify_filtergraph_scaling"
            return "fallback_clean_canvas"
        elif "audio" in cat or "sample" in err_str:
            return "force_resample_48k"
        elif "collision" in cat or "overlap" in err_str:
            return "ripple_shift_colliding_clips"
        else:
            return f"generic_safe_fallback_level_{attempt}"

    @property
    def total_remediations(self) -> int:
        return len(self.applied_remediations)

