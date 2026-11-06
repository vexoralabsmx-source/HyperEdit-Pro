"""Production checkpoint manager for fault-tolerant workflow resumption."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hyperedit.production.models import ProductionStage


class ProductionCheckpointManager:
    """Records and restores pipeline execution checkpoints across agent invocations."""

    def __init__(self, plan_hash: str, cache_dir: Path | str = ".hyperedit_cache") -> None:
        self.plan_hash = plan_hash
        self.cache_dir = Path(cache_dir).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.cache_dir / f"checkpoint_{plan_hash}.json"
        self.state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.checkpoint_file.exists():
            return {
                "plan_hash": self.plan_hash,
                "current_stage": ProductionStage.INIT.value,
                "completed_stages": [],
                "intermediate_files": {},
                "remediation_attempts": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        try:
            return json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
        except Exception:
            return {
                "plan_hash": self.plan_hash,
                "current_stage": ProductionStage.INIT.value,
                "completed_stages": [],
                "intermediate_files": {},
                "remediation_attempts": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

    def save(self) -> None:
        """Atomically persist checkpoint state to disk."""
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp = self.checkpoint_file.with_suffix(".tmp")
        temp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        temp.replace(self.checkpoint_file)

    def is_stage_completed(self, stage: ProductionStage) -> bool:
        """Check if a specific stage has already successfully finished."""
        return stage.value in self.state.get("completed_stages", [])

    def record_stage(
        self,
        stage: ProductionStage,
        intermediate_files: Optional[Dict[str, str]] = None,
    ) -> None:
        """Advance the checkpoint to a completed stage and record intermediate artifacts."""
        self.state["current_stage"] = stage.value
        completed: List[str] = self.state.setdefault("completed_stages", [])
        if stage.value not in completed:
            completed.append(stage.value)

        if intermediate_files:
            stored_files: Dict[str, str] = self.state.setdefault("intermediate_files", {})
            stored_files.update(intermediate_files)

        self.save()

    def get_intermediate_file(self, key: str) -> Optional[Path]:
        """Retrieve path to a previously generated intermediate file if it still exists."""
        stored = self.state.get("intermediate_files", {}).get(key)
        if stored:
            p = Path(stored)
            if p.exists():
                return p
        return None

    def increment_remediation(self) -> int:
        """Track automatic remediation retry attempts."""
        self.state["remediation_attempts"] = self.state.get("remediation_attempts", 0) + 1
        self.save()
        return self.state["remediation_attempts"]

    @property
    def remediation_attempts(self) -> int:
        return self.state.get("remediation_attempts", 0)

    def reset(self) -> None:
        """Clear the checkpoint."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        self.state = self._load()

