"""Process-local Tool resource capabilities and cgroup-v2 memory containment."""

from __future__ import annotations

import hashlib
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from backend.app.schemas.tools import ToolMemoryCapability

MEMORY_OBSERVATION_INTERVAL_MS = 50
_CGROUP_ROOT = Path("/sys/fs/cgroup")
_PROC_SELF_CGROUP = Path("/proc/self/cgroup")


@dataclass(frozen=True, slots=True)
class MemoryObservation:
    current_bytes: int | None
    peak_observed_bytes: int | None
    limit_exceeded: bool


def _read_cgroup_events(path: Path) -> dict[str, int]:
    events: dict[str, int] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, separator, raw_value = line.partition(" ")
        if separator and raw_value.isascii() and raw_value.isdecimal():
            events[key] = int(raw_value)
    return events


class CgroupV2MemoryGroup:
    """One private cgroup whose membership is inherited by job descendants."""

    def __init__(self, path: Path, limit_bytes: int):
        self.path = path
        self.limit_bytes = limit_bytes
        self._baseline_events = _read_cgroup_events(path / "memory.events")
        self._peak_observed_bytes: int | None = None
        self._closed = False

    @staticmethod
    def _write(path: Path, value: str) -> None:
        path.write_text(value, encoding="ascii")

    def attach(self, pid: int) -> None:
        self._write(self.path / "cgroup.procs", str(pid))
        members = {int(value) for value in (self.path / "cgroup.procs").read_text(encoding="ascii").splitlines() if value.isascii() and value.isdecimal()}
        if pid not in members:
            raise RuntimeError("Tool worker was not attached to its memory cgroup")

    def observe(self) -> MemoryObservation:
        current_raw = (self.path / "memory.current").read_text(encoding="ascii").strip()
        current = int(current_raw) if current_raw.isascii() and current_raw.isdecimal() else None
        peak_path = self.path / "memory.peak"
        peak: int | None = None
        if peak_path.is_file():
            peak_raw = peak_path.read_text(encoding="ascii").strip()
            peak = int(peak_raw) if peak_raw.isascii() and peak_raw.isdecimal() else None
        if current is not None:
            peak = current if peak is None else max(current, peak)
        if peak is not None:
            self._peak_observed_bytes = peak if self._peak_observed_bytes is None else max(self._peak_observed_bytes, peak)
        events = _read_cgroup_events(self.path / "memory.events")
        exceeded = any(events.get(key, 0) > self._baseline_events.get(key, 0) for key in ("oom", "oom_kill", "oom_group_kill"))
        return MemoryObservation(current, self._peak_observed_bytes, exceeded)

    def populated(self) -> bool:
        try:
            return _read_cgroup_events(self.path / "cgroup.events").get("populated") != 0
        except (OSError, ValueError):
            return True

    def kill(self) -> None:
        kill_path = self.path / "cgroup.kill"
        if kill_path.is_file():
            self._write(kill_path, "1")

    def close_if_empty(self) -> bool:
        if self._closed:
            return True
        if self.populated():
            return False
        try:
            self.path.rmdir()
        except OSError:
            return False
        self._closed = True
        return True

    @property
    def peak_observed_bytes(self) -> int | None:
        return self._peak_observed_bytes


class ToolResourceController:
    """Select hard cgroup containment only when delegation is observable."""

    def __init__(self, *, cgroup_root: Path = _CGROUP_ROOT, proc_self_cgroup: Path = _PROC_SELF_CGROUP):
        self._cgroup_root = cgroup_root
        self._proc_self_cgroup = proc_self_cgroup
        self._lock = threading.RLock()
        self._parent_checked = False
        self._cgroup_parent: Path | None = None
        self._hard_disabled = False

    def _discover_cgroup_parent(self) -> Path | None:
        if os.name != "posix" or sys.platform != "linux":
            return None
        try:
            root = self._cgroup_root.resolve(strict=True)
            if not (root / "cgroup.controllers").is_file():
                return None
            relative: str | None = None
            for line in self._proc_self_cgroup.read_text(encoding="ascii").splitlines():
                hierarchy, controllers, path = line.split(":", 2)
                if hierarchy == "0" and controllers == "":
                    relative = path
                    break
            if relative is None:
                return None
            parent = (root / relative.lstrip("/")).resolve(strict=True)
            if parent != root and root not in parent.parents:
                return None
            controllers = set((parent / "cgroup.controllers").read_text(encoding="ascii").split())
            enabled = set((parent / "cgroup.subtree_control").read_text(encoding="ascii").split())
            required_files = ("cgroup.procs", "cgroup.events")
            if "memory" not in controllers or "memory" not in enabled or any(not (parent / name).is_file() for name in required_files):
                return None
            if not os.access(parent, os.W_OK | os.X_OK):
                return None
            return parent
        except (OSError, RuntimeError, ValueError):
            return None

    def _parent(self) -> Path | None:
        with self._lock:
            if not self._parent_checked:
                self._cgroup_parent = self._discover_cgroup_parent()
                self._parent_checked = True
            return None if self._hard_disabled else self._cgroup_parent

    def disable_hard_mode(self) -> None:
        with self._lock:
            self._hard_disabled = True

    def memory_capability(self) -> ToolMemoryCapability:
        if os.name != "posix":
            return ToolMemoryCapability(mode="unavailable")
        if self._parent() is not None:
            return ToolMemoryCapability(mode="cgroup_v2_hard")
        return ToolMemoryCapability(mode="process_tree_observed", observation_interval_ms=MEMORY_OBSERVATION_INTERVAL_MS)

    def prepare_memory_group(self, execution_id: str, limit_bytes: int) -> CgroupV2MemoryGroup | None:
        parent = self._parent()
        if parent is None:
            return None
        digest = hashlib.sha256(execution_id.encode("utf-8")).hexdigest()[:24]
        path = parent / f"librefolio-tool-{os.getpid()}-{digest}"
        created = False
        try:
            path.mkdir(mode=0o700)
            created = True
            CgroupV2MemoryGroup._write(path / "memory.max", str(limit_bytes))
            if (path / "memory.max").read_text(encoding="ascii").strip() != str(limit_bytes):
                raise RuntimeError("Tool memory cgroup did not retain its hard limit")
            oom_group = path / "memory.oom.group"
            if oom_group.is_file() and os.access(oom_group, os.W_OK):
                CgroupV2MemoryGroup._write(oom_group, "1")
            return CgroupV2MemoryGroup(path, limit_bytes)
        except (OSError, RuntimeError, ValueError):
            self.disable_hard_mode()
            if created:
                try:
                    path.rmdir()
                except OSError as exc:
                    raise RuntimeError("Failed to remove an unusable Tool memory cgroup") from exc
            return None
