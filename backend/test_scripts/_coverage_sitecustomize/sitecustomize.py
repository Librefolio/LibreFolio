"""Start coverage in spawned child processes (P1-13).

The test runner prepends this directory to ``PYTHONPATH`` whenever a run
collects coverage, so Python's ``site`` module imports this file at the startup
of *every* interpreter in the process tree — including the ``multiprocessing``
**spawn** children of ``backend/app/services/risk/quant/spawn_worker.py``.

Why this exists: ``.coveragerc`` already declares
``concurrency = multiprocessing,thread,gevent``, which lets a *running* tracer
follow forked children. A spawn child is a fresh interpreter, though: it
inherits the environment but no tracer, so ``_worker_main`` and friends
measured 0 % while being live. This is coverage.py's documented subprocess
recipe — the child reads ``COVERAGE_PROCESS_START`` (the repo ``.coveragerc``,
which has ``parallel = true``), starts its own tracer, and writes
``{COVERAGE_FILE|.coverage}.<host>.<pid>.<rand>`` next to the parent's data
file, where the existing combine steps already collect it.

The guard is load-bearing: outside a coverage run the variable is unset and
this module is a no-op, so production interpreters pay nothing for it. When the
variable *is* set, a failure to start coverage must not be swallowed — a child
that cannot measure itself crashes the spawn bootstrap, which surfaces as a
test failure instead of silently missing data (``coverage.process_startup`` is
itself idempotent, so coexisting with the ``a1_coverage.pth`` that coverage
7.14 installs in the virtualenv is safe).
"""

import os

if os.environ.get("COVERAGE_PROCESS_START"):
    try:
        import coverage
    except ModuleNotFoundError:
        # Interpreters along the spawn/exec chain that never run measured code
        # (e.g. the Homebrew Python hosting the `pipenv` launcher) do not have
        # coverage installed. Only the venv children measure; let the rest pass.
        coverage = None
    if coverage is not None:
        coverage.process_startup()

# ---------------------------------------------------------------------------
# Coexistence chain — do not remove.
#
# Python imports only ONE `sitecustomize` module: the first found on sys.path.
# Because the runner prepends this directory to PYTHONPATH, this file shadows
# any sitecustomize shipped by the interpreter itself. Homebrew Python ships
# one (lib/pythonX.Y/sitecustomize.py) that rewrites sys.prefix from the Cellar
# path to the opt prefix and exposes /opt/homebrew/lib/pythonX.Y/site-packages;
# when it is shadowed, `pipenv` (installed there) becomes unimportable and every
# `pipenv run …` child of the server/test flow dies at import. Chain-exec the
# next sitecustomize down sys.path so the interpreter's own startup still runs.
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
for _entry in sys.path:
    _candidate = Path(_entry or ".").resolve() / "sitecustomize.py"
    try:
        if _candidate.is_file() and _candidate.parent != _here:
            exec(compile(_candidate.read_bytes(), str(_candidate), "exec"), globals())
            break
    except OSError:
        continue
