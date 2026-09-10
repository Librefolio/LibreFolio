"""Owned POSIX job cleanup; all methods perform I/O and run off the event loop."""

from __future__ import annotations

import multiprocessing
import os
import signal
import time
from dataclasses import dataclass

import psutil


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

    def __init__(self, process: multiprocessing.Process):
        self.process = process
        self.root: ProcessIdentity | None = None
        self.group_id: int | None = None
        self.known: dict[int, ProcessIdentity] = {}
        self.closed = False

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

    def _signal(self, *, force: bool) -> None:
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
            if not members and not root_alive and not self._group_exists():
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.02, remaining))

    def cleanup(self, deadline: float) -> bool:
        """Return true only after observed termination; false retains every handle."""
        if self.closed:
            return True
        try:
            if self.process.pid is None:
                self.process.close()
                self.closed = True
                return True
            self.running_members()
            if not self._wait_empty(min(deadline, time.monotonic() + 0.02)):
                self._signal(force=False)
                if not self._wait_empty(min(deadline, time.monotonic() + 0.2)):
                    self._signal(force=True)
                    if not self._wait_empty(deadline):
                        return False
            self.process.join(timeout=0)
            if self.process.is_alive():
                return False
            self.process.close()
            self.closed = True
            return True
        except (psutil.AccessDenied, PermissionError, OSError, ValueError):
            return False
