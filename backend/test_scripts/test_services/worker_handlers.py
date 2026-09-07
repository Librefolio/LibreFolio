"""Small spawned handlers used by process-boundary tests."""

from __future__ import annotations

import os
import time
from pathlib import Path


def dispatch_worker_fixture(payload: dict) -> dict:
    action = payload["action"]
    if action == "echo":
        return {
            "value": payload["value"],
            "pid": os.getpid(),
        }
    if action == "sleep":
        time.sleep(payload["seconds"])
        return {"slept": payload["seconds"]}
    if action == "mark_and_sleep":
        Path(payload["marker"]).write_text(
            "started",
            encoding="utf-8",
        )
        time.sleep(payload["seconds"])
        return {"slept": payload["seconds"]}
    if action == "fail":
        raise ValueError("fixture failure")
    raise ValueError(f"unknown fixture action: {action}")
