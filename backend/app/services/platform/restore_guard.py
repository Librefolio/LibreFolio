"""An instance whose restore stopped half way serves no data (lot B-33, the start's part).

Owner: workstream H (platform). When the state of the restore (``.restore/restore.json``) cannot be read — its owner or
permissions changed, a disk error, a link or a folder in its place, content no LibreFolio wrote — a restore may have
stopped half way, and LibreFolio cannot tell which data it holds. The start asks once, right after ``pending-restore``
(``app_lifespan.py``, step ``restore-state``), through workstream B's ``apply.restore_state_problem``. When it cannot
read it, the process serves no data until the administrator chooses with ``./dev.py backup pending --recover previous`` and
starts LibreFolio again:

- the steps that repair, write or warm up the data are skipped (``skip_when``);
- every API route but the probes, the public configuration and the hosting panel's answers 423
  ``instance_restore_interrupted`` (``api/v1/instance_block.py``);
- ``GET /system/instance`` says ``restore_interrupted: true``, and the app shows a page that asks for the administrator.

The answer is the process's, from its start: a state made readable while LibreFolio runs counts at the next start.

A second reason closes the instance the same way (lot H5-3): a restore from the app on a managed instance names the
account that becomes the owner's, and the first start gives it (``restore-owner``, right after ``restore-commit``).
Until that is done the process serves no data — a backup may come from anywhere, and its accounts are not the owner's
to trust. ``apply.owner_assignment_problem`` says ``pending`` (not done yet) or the code of the refusal; the step probes
it once it ran. With several workers only one gives the owner their account, so a worker that found ``pending`` asks
again, at most every ``OWNER_RECHECK_SECONDS`` (``refresh_restore_state``, from the router dependency), and opens when
another worker records the outcome. A code is final for the process: the administrator chooses
``./dev.py backup pending --recover owner`` and starts LibreFolio again.
"""

import asyncio
import time
from pathlib import Path
from typing import Literal

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup import apply as restore_apply

logger = get_logger(__name__)

#: The last probe's answer, in this process; False until a probe found the state unreadable.
_interrupted = False

#: What keeps the owner from their account (``pending`` or a refusal's code), as the last probe found it; ``None`` when
#: nothing does.
_owner_problem: str | None = None

#: How often a worker that found the owner ``pending`` asks again whether another worker gave it, and the clock of it.
OWNER_RECHECK_SECONDS = 2.0
_monotonic = time.monotonic
_owner_checked_at = 0.0

PROBE_OWNER_MESSAGE = "The owner of the restored data has no account yet: LibreFolio serves no data until it is set"

RestoreInterruptedReason = Literal["restore_state", "owner_assignment"]


def probe_restore_state(data_dir: Path | None = None) -> bool:
    """Ask whether the state of the restore can be read, keep the answer for ``restore_interrupted()``, and return it.
    One error line when it cannot, with B's reason (``io``, ``not_a_file``, ``invalid``), never the state's content."""
    global _interrupted
    problem = restore_apply.restore_state_problem(data_dir or get_data_dir())
    _interrupted = problem is not None
    if problem is not None:
        logger.error("The state of the restore cannot be read: LibreFolio serves no data until the administrator runs ./dev.py backup pending --recover previous", reason=problem.reason)
    return _interrupted


def probe_owner_assignment(data_dir: Path | None = None) -> str | None:
    """Ask what keeps the owner from their account after a restore from the app, keep the answer, and return it
    (``None``, ``pending`` or the code of the refusal). One error line when there is a problem: the value only, never a
    path or an address."""
    global _owner_problem, _owner_checked_at
    problem = restore_apply.owner_assignment_problem(data_dir or get_data_dir())
    _owner_problem = problem
    _owner_checked_at = _monotonic()
    if problem is not None:
        logger.error(PROBE_OWNER_MESSAGE, problem=problem)
    return problem


async def refresh_restore_state() -> None:
    """Ask again, when it is due, whether the owner's account was given meanwhile: only for ``pending`` (another worker
    of this start holds the assignment and records its outcome), and at most every ``OWNER_RECHECK_SECONDS``. A code is
    never asked again. Never raises: a probe that fails keeps the answer of before."""
    global _owner_problem, _owner_checked_at
    if _owner_problem != "pending" or _monotonic() - _owner_checked_at < OWNER_RECHECK_SECONDS:
        return
    _owner_checked_at = _monotonic()
    try:
        _owner_problem = await asyncio.to_thread(restore_apply.owner_assignment_problem, get_data_dir())
    except Exception as exc:  # noqa: BLE001 — a probe: the answer of before stands, the next request asks again
        logger.warning("The owner's assignment could not be probed again", error=type(exc).__name__)


def restore_interrupted() -> bool:
    """Whether this process serves no data: it found the state of the restore unreadable at its start, or the owner of a
    restored instance has no account yet."""
    return _interrupted or _owner_problem is not None


def restore_interrupted_reason() -> RestoreInterruptedReason | None:
    """Why this process serves no data: ``restore_state`` (it wins) or ``owner_assignment``; ``None`` when it does."""
    if _interrupted:
        return "restore_state"
    return "owner_assignment" if _owner_problem is not None else None
