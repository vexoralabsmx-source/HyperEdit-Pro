"""Reversible operation history (Undo/Redo) for HyperEdit Pro timeline editing."""

from copy import deepcopy
from typing import List, Optional, Tuple

from hyperedit.core.models.project import Project


class HistoryRecord:
    """A snapshot record in the undo/redo stack."""

    def __init__(self, project_data: dict, description: str) -> None:
        self.project_data = project_data
        self.description = description


class TimelineHistory:
    """Manages undo/redo stacks for non-destructive editing operations."""

    def __init__(self, max_history: int = 50) -> None:
        self.max_history = max_history
        self._undo_stack: List[HistoryRecord] = []
        self._redo_stack: List[HistoryRecord] = []

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def record_operation(self, project_before: Project, description: str) -> None:
        """Capture the project state before applying a mutation."""
        snapshot = HistoryRecord(project_before.model_dump(), description)
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)
        # Any new mutation invalidates the redo branch
        self._redo_stack.clear()

    def undo(self, current_project: Project) -> Tuple[Optional[Project], str]:
        """Revert to the previous timeline state."""
        if not self._undo_stack:
            return None, "Nothing to undo"

        # Push current state onto redo stack
        current_snapshot = HistoryRecord(current_project.model_dump(), "Current State")
        self._redo_stack.append(current_snapshot)

        # Pop previous state from undo stack
        target_record = self._undo_stack.pop()
        restored = Project.model_validate(target_record.project_data)
        return restored, target_record.description

    def redo(self, current_project: Project) -> Tuple[Optional[Project], str]:
        """Re-apply the previously undone operation."""
        if not self._redo_stack:
            return None, "Nothing to redo"

        # Push current state onto undo stack
        current_snapshot = HistoryRecord(current_project.model_dump(), "Undone State")
        self._undo_stack.append(current_snapshot)

        # Pop forward state from redo stack
        target_record = self._redo_stack.pop()
        restored = Project.model_validate(target_record.project_data)
        return restored, target_record.description

    def get_history_summary(self) -> List[dict]:
        """Return list of undo records."""
        return [
            {"index": idx, "description": rec.description}
            for idx, rec in enumerate(self._undo_stack)
        ]

