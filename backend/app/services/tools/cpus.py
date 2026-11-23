"""The CPUs a process can use at once (lot SEEDS-c of project 67; moved here by TURNI).

The count is the smaller of the process's CPU affinity and the whole CPUs of its CPU quota (cgroup v2 ``cpu.max``, v1
``cpu.cfs_quota_us`` over ``cpu.cfs_period_us``; every ancestor of the process's cgroup counts), never below 1. A quota
shares its CPUs among a group's processes whatever their priority, so the affinity alone overstates a container's CPUs.

Two readers, one count: the Tool platform, which picks an operation's limits by the CPUs of the machine when it builds
its executor (TURNI), and the Rebalancer's engine, which never runs more searches at once than it can use (``seed_runs``).
A leaf: only the standard library.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["cpu_count_usable"]


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _whole_cpus(quota: str | None, period: str | None) -> int | None:
    """A quota over its period, in whole CPUs rounded down, at least 1; None when there is no quota or it cannot be read."""
    try:
        quota_us, period_us = int(quota or ""), int(period or "")
    except ValueError:
        return None
    if quota_us <= 0 or period_us <= 0:
        return None
    return max(1, quota_us // period_us)


def _quota_cpus(proc_cgroup: Path, cgroup_root: Path) -> int | None:
    """The smallest CPU quota over the process's cgroup and every ancestor, cgroup v2 or v1; None without one."""
    text = _read(proc_cgroup)
    if text is None:
        return None
    limits: list[int] = []
    for line in text.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        _hierarchy, controllers, path = parts
        chain = [Path(path.lstrip("/")), *Path(path.lstrip("/")).parents]
        if controllers == "":  # cgroup v2: `cpu.max` reads «max <period>» or «<quota> <period>»
            for directory in chain:
                fields = (_read(cgroup_root / directory / "cpu.max") or "").split()
                cpus = _whole_cpus(fields[0], fields[1]) if len(fields) == 2 else None
                if cpus is not None:
                    limits.append(cpus)
        elif "cpu" in controllers.split(","):  # cgroup v1: the `cpu` controller, mounted under its controllers' names
            mount = cgroup_root / controllers
            for directory in chain:
                cpus = _whole_cpus(_read(mount / directory / "cpu.cfs_quota_us"), _read(mount / directory / "cpu.cfs_period_us"))
                if cpus is not None:
                    limits.append(cpus)
    return min(limits) if limits else None


def cpu_count_usable(*, proc_cgroup: Path = Path("/proc/self/cgroup"), cgroup_root: Path = Path("/sys/fs/cgroup"), affinity: int | None = None) -> int:
    """The CPUs this process can use at once: the smaller of the affinity's CPUs and the quota's whole CPUs, never below 1.
    A file that cannot be read means no quota."""
    if affinity is None:
        affinity = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    quota = _quota_cpus(proc_cgroup, cgroup_root)
    return max(1, min(affinity, quota) if quota is not None else affinity)
