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
"""

from pathlib import Path

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup import apply as restore_apply

logger = get_logger(__name__)

#: The last probe's answer, in this process; False until a probe found the state unreadable.
_interrupted = False


def probe_restore_state(data_dir: Path | None = None) -> bool:
    """Ask whether the state of the restore can be read, keep the answer for ``restore_interrupted()``, and return it.
    One error line when it cannot, with B's reason (``io``, ``not_a_file``, ``invalid``), never the state's content."""
    global _interrupted
    problem = restore_apply.restore_state_problem(data_dir or get_data_dir())
    _interrupted = problem is not None
    if problem is not None:
        logger.error("The state of the restore cannot be read: LibreFolio serves no data until the administrator runs ./dev.py backup pending --recover previous", reason=problem.reason)
    return _interrupted


def restore_interrupted() -> bool:
    """Whether this process found the state of the restore unreadable at its start: it then serves no data."""
    return _interrupted
