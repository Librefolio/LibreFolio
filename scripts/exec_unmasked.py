#!/usr/bin/env python3
"""Exec a command after clearing teardown signals inherited from its parent."""

import os
import signal
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("exec_unmasked.py requires a command", file=sys.stderr)
        return 2

    if hasattr(signal, "pthread_sigmask"):
        teardown_signals = {
            getattr(signal, name)
            for name in ("SIGINT", "SIGTERM", "SIGHUP")
            if hasattr(signal, name)
        }
        signal.pthread_sigmask(signal.SIG_UNBLOCK, teardown_signals)

    command = sys.argv[1:]
    os.execvpe(command[0], command, os.environ)
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
