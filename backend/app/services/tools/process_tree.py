"""Owned POSIX job cleanup; all methods perform I/O and run off the event loop."""

from __future__ import annotations

import multiprocessing
import os
import signal
import time
from dataclasses import dataclass

import psutil

from backend.app.schemas.tools import ToolMemoryLimitMode, ToolMemoryMetrics, ToolResourceMetrics
from backend.app.services.tools.base import ToolExecutionError
from backend.app.services.tools.resources import CgroupV2MemoryGroup, ToolResourceController


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    pid: int
    created_at: float

    def current(self) -> psutil.Process | None:
        try:
            process = psutil.Process(self.pid)
            if process.create_time() != self.created_at or not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                return None
            return process
        except psutil.NoSuchProcess:
            return None


class OwnedProcessTree:
    """A fresh job session plus captured descendants, never a process-name match."""

    def __init__(
        self,
        process: multiprocessing.Process,
        *,
        memory_limit_bytes: int = 1_073_741_824,
        resource_controller: ToolResourceController | None = None,
    ):
        self.process = process
        self.memory_limit_bytes = memory_limit_bytes
        self.resource_controller = resource_controller
        self.memory_group: CgroupV2MemoryGroup | None = None
        self.memory_mode: ToolMemoryLimitMode = "process_tree_observed"
        self.peak_observed_bytes: int | None = None
        self.memory_limit_exceeded = False
        self.root: ProcessIdentity | None = None
        self.group_id: int | None = None
        self.known: dict[int, ProcessIdentity] = {}
        self.closed = False

    def prepare_resources(self, execution_id: str) -> None:
        if self.resource_controller is None:
            return
        self.memory_group = self.resource_controller.prepare_memory_group(execution_id, self.memory_limit_bytes)
        if self.memory_group is not None:
            self.memory_mode = "cgroup_v2_hard"

    def bind_started_process(self) -> None:
        pid = self.process.pid
        if pid is None:
            raise RuntimeError("Tool process did not acquire a PID")
        try:
            process = psutil.Process(pid)
            identity = ProcessIdentity(pid, process.create_time())
        except psutil.NoSuchProcess:
            return
        if self.process.exitcode is None:
            self.root = identity
            self.known[pid] = identity
            if self.memory_group is not None:
                try:
                    self.memory_group.attach(pid)
                except (OSError, RuntimeError, ValueError):
                    if not self.memory_group.close_if_empty():
                        raise RuntimeError("Failed to release an unusable Tool memory cgroup") from None
                    if self.resource_controller is not None:
                        self.resource_controller.disable_hard_mode()
                    self.memory_group = None
                    self.memory_mode = "process_tree_observed"

    def confirm_session(self, *, pid: int, group_id: int, created_at: float) -> None:
        if pid != self.process.pid or group_id != pid or group_id == os.getpgrp():
            raise ValueError("Worker session does not belong to the Tool job")
        identity = ProcessIdentity(pid, created_at)
        if self.root is not None and self.root != identity:
            raise ValueError("Worker PID identity changed")
        self.root = identity
        self.known[pid] = identity
        self.group_id = group_id

    def _group_is_owned(self) -> bool:
        if self.group_id is None or self.root is None:
            return False
        try:
            leader = psutil.Process(self.group_id)
            return leader.create_time() == self.root.created_at
        except psutil.NoSuchProcess:
            for identity in self.known.values():
                process = identity.current()
                if process is None:
                    continue
                try:
                    if os.getpgid(process.pid) == self.group_id:
                        return True
                except ProcessLookupError:
                    continue
            return False

    def _group_exists(self) -> bool:
        if self.group_id is None:
            return False
        try:
            os.killpg(self.group_id, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def _capture_group(self) -> None:
        if not self._group_is_owned():
            return
        for process in psutil.process_iter(["pid", "create_time"]):
            try:
                if os.getpgid(process.pid) == self.group_id:
                    self.known[process.pid] = ProcessIdentity(process.pid, process.create_time())
            except (ProcessLookupError, psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
                continue

    def running_members(self) -> list[psutil.Process]:
        if self.closed:
            return []
        if self.root is not None:
            root = self.root.current()
            if root is not None:
                try:
                    descendants = root.children(recursive=True)
                except psutil.NoSuchProcess:
                    descendants = []
                for process in descendants:
                    try:
                        self.known[process.pid] = ProcessIdentity(process.pid, process.create_time())
                    except psutil.NoSuchProcess:
                        continue
        self._capture_group()
        members: list[psutil.Process] = []
        for identity in tuple(self.known.values()):
            process = identity.current()
            if process is not None:
                members.append(process)
        return members

    def observe_memory_limit(self) -> None:
        """Record process-tree memory and raise only for a measured limit breach."""
        try:
            if self.memory_group is not None:
                observation = self.memory_group.observe()
                self.peak_observed_bytes = observation.peak_observed_bytes
                exceeded = observation.limit_exceeded
            else:
                current = 0
                for process in self.running_members():
                    try:
                        current += process.memory_info().rss
                    except psutil.NoSuchProcess:
                        continue
                self.peak_observed_bytes = current if self.peak_observed_bytes is None else max(self.peak_observed_bytes, current)
                exceeded = current > self.memory_limit_bytes
        except (psutil.AccessDenied, PermissionError, OSError, RuntimeError, ValueError) as exc:
            raise ToolExecutionError("service_unavailable", retryable=True) from exc
        if exceeded:
            self.memory_limit_exceeded = True
            raise ToolExecutionError("memory_limit")

    def resource_metrics(self) -> ToolResourceMetrics:
        return ToolResourceMetrics(
            memory=ToolMemoryMetrics(
                mode=self.memory_mode,
                limit_bytes=self.memory_limit_bytes,
                peak_observed_bytes=self.peak_observed_bytes,
            )
        )

    def _signal(self, *, force: bool) -> None:
        if force and self.memory_group is not None:
            try:
                self.memory_group.kill()
            except OSError:
                pass
        if self._group_is_owned():
            try:
                os.killpg(self.group_id, signal.SIGKILL if force else signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
        for process in self.running_members():
            identity = self.known[process.pid]
            if identity.current() is None:
                continue
            try:
                process.kill() if force else process.terminate()
            except psutil.NoSuchProcess:
                continue
        if self.root is None and self.process.exitcode is None:
            # Before the ready frame no plugin code may run or create descendants.
            self.process.kill() if force else self.process.terminate()

    def _wait_empty(self, deadline: float) -> bool:
        while True:
            members = self.running_members()
            root_alive = self.process.exitcode is None
            memory_group_populated = self.memory_group is not None and self.memory_group.populated()
            if not members and not root_alive and not self._group_exists() and not memory_group_populated:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.02, remaining))

    def _terminate_before(self, deadline: float) -> bool:
        if self._wait_empty(min(deadline, time.monotonic() + 0.02)):
            return True
        self._signal(force=False)
        if self._wait_empty(min(deadline, time.monotonic() + 0.2)):
            return True
        self._signal(force=True)
        return self._wait_empty(deadline)

    def _close_empty_resources(self) -> bool:
        if self.memory_group is not None:
            try:
                self.memory_group.observe()
            except (OSError, RuntimeError, ValueError):
                pass
            self.peak_observed_bytes = self.memory_group.peak_observed_bytes
            if not self.memory_group.close_if_empty():
                return False
        self.process.close()
        self.closed = True
        return True

    def cleanup(self, deadline: float) -> bool:
        """Return true only after observed termination; false retains every handle."""
        if self.closed:
            return True
        try:
            if self.process.pid is None:
                return self._close_empty_resources()
            try:
                self.observe_memory_limit()
            except ToolExecutionError:
                pass
            if not self._terminate_before(deadline):
                return False
            self.process.join(timeout=0)
            if self.process.is_alive():
                return False
            return self._close_empty_resources()
        except (psutil.AccessDenied, PermissionError, OSError, ValueError):
            return False
