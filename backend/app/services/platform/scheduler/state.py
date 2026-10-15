"""Scheduler state persistence — atomic JSON file with write-then-rename."""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from backend.app.config import get_data_dir


@dataclass
class JobState:
    last_run_at: Optional[str] = None  # ISO datetime with tz
    last_duration_s: Optional[float] = None
    last_status: Optional[str] = None  # "ok" | "partial" | "error"
    last_items_ok: int = 0
    last_items_err: int = 0
    last_error: Optional[str] = None


@dataclass
class SchedulerState:
    current_price: JobState = field(default_factory=JobState)
    history_sync: JobState = field(default_factory=JobState)


def _state_path() -> Path:
    return Path(get_data_dir()) / "scheduler_state.json"


def load_state() -> SchedulerState:
    """Load scheduler state from JSON file. Returns fresh state if missing/corrupt."""
    path = _state_path()
    if not path.exists():
        return SchedulerState()
    try:
        data = json.loads(path.read_text())
        return SchedulerState(
            current_price=JobState(**data.get("current_price", {})),
            history_sync=JobState(**data.get("history_sync", {})),
        )
    except (json.JSONDecodeError, TypeError, KeyError):
        return SchedulerState()


def save_state(state: SchedulerState) -> None:
    """Save scheduler state atomically (write-then-rename)."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(asdict(state), indent=2))
    os.replace(str(tmp_path), str(path))
