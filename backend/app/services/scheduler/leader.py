"""Leader election via psutil — lowest-PID among uvicorn sibling workers."""

import os

import psutil


def am_i_leader() -> bool:
    """
    Determine if the current process is the scheduler leader.

    Strategy for multi-worker uvicorn (--workers N):
      Among sibling worker processes (children of the uvicorn master),
      the one with the lowest PID is the leader. Re-evaluated every tick
      for self-healing (if leader crashes, next tick promotes new lowest-PID).

    Fast-paths (always leader):
      - PID 1 or no parent (Docker single-container)
      - Parent is the uvicorn master with --reload (dev mode, single logical worker)
      - Exception during introspection (safe: jobs are idempotent)
    """
    try:
        me = psutil.Process(os.getpid())
        parent = me.parent()
        if parent is None:
            return True

        # In dev mode (uvicorn --reload), the parent IS the uvicorn process
        # that spawns reload workers. There's only 1 logical worker at a time.
        # Detect by checking if parent cmdline contains "uvicorn" + "--reload".
        try:
            parent_cmdline = " ".join(parent.cmdline())
            if "--reload" in parent_cmdline:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        # Multi-worker production mode: parent is uvicorn master with N children.
        # Compete via lowest-PID among running, non-zombie siblings.
        siblings = [
            p
            for p in parent.children(recursive=False)
            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        ]
        if len(siblings) <= 1:
            return True
        return me.pid == min(p.pid for p in siblings)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
        # If we can't determine, assume leader (safe: jobs are idempotent)
        return True
