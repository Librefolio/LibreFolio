"""The instance key check: tells an instance whose key is not the one its data was written with (decision D6).

Owner: workstream H (platform), lot H5-7. A key that is valid but different from the one used so far lets the instance
start: the stored plugin secrets can no longer be read, and the hosting panel's nightly backups would go on pushing the
good copies out of the archive. This module gives the panel a plain ``ok`` or ``mismatch``, from a reference the instance
keeps beside the key.

The reference is the *check value* in ``<data directory>/secrets/instance.key.check``: an HMAC of a fixed phrase under a
purpose key of its own (``derive_key("instance.key-check.v1")``), so it reveals nothing of the key. The instance keeps
serving with a mismatch; only the panel's backup jobs and ``wake-sync`` stop (``api/v1/backup/panel.py``,
``api/v1/system/wake.py``).

``instance_key_state()`` is computed at every call and remembers nothing, so the answer follows the key and the file as
they are now: the right key put back is ``ok`` at the next request. ``mismatch`` needs evidence:

1. no key to compare (none created yet, or one that cannot be used): ``ok``, and no key is generated here;
2. the check file is there: its value against the key's, equal or not; a file that cannot be read or is not a check value
   says nothing about the key: ``ok``, and one warning for the process;
3. no file yet (an instance before 1.3, or the first start): the stored plugin secrets. ``mismatch`` only when there is
   at least one and every one of them is under another key; otherwise ``ok``.

``check_instance_key_at_start()`` (startup step ``instance-key-check``) writes the check value on the first start and
never on a mismatch, since writing it would bless the wrong key. A deliberate change of key (a rotation, a lost key
replaced) is accepted by starting once with ``LIBREFOLIO_INSTANCE_KEY_ACCEPT=1``: the value is rewritten and the log says
so at every start while the variable is set. No log line holds a key, a check value, a key id or a file's content.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_data_dir
from backend.app.config.platform import instance_key_accept
from backend.app.db.models import PluginSystemSetting, PluginUserSetting
from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger
from backend.app.services.platform.config_audit import ConfigCheck
from backend.app.services.platform.instance_key import InstanceKeyError, _create_exclusively, _sync_directory, derive_key, instance_key_status
from backend.app.services.plugin_settings.crypto import key_id_of, settings_subkey

logger = get_logger(__name__)

KEY_CHECK_FILE = Path("secrets") / "instance.key.check"
ACCEPT_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_ACCEPT"
CHECK_ID = "platform.instance_key_check"

InstanceKeyState = Literal["ok", "mismatch"]

MISMATCH_MESSAGE = "The instance key is not the one this instance's data was written with: the hosting panel's backups and wake-sync are stopped"
ACCEPTED_MESSAGE = f"The instance key was accepted as the new reference ({ACCEPT_VARIABLE} is set): remove the variable"
UNREADABLE_MESSAGE = "The instance key check file cannot be read or is not a check value: the instance key is not checked"
_QUERY_FAILED_MESSAGE = "The stored plugin secrets could not be counted: the instance key is not checked against them"
_START_FAILED_MESSAGE = "The instance key check could not run at start"
_STATE_FAILED_MESSAGE = "The instance key state could not be worked out: the instance key is not checked"

_PURPOSE = "instance.key-check.v1"
_PURPOSE_KEY_LENGTH = 32
_LABEL = b"LibreFolio instance key check v1"
_CHECK_VALUE = re.compile(r"[0-9a-f]{64}")

#: The failures already warned of in this process: a failure that lasts is one line, not one per request.
_warned: set[str] = set()


def instance_key_check_path() -> Path:
    """Where the check value lives: ``secrets/instance.key.check`` in the current data directory."""
    return get_data_dir() / KEY_CHECK_FILE


def key_check_value() -> str:
    """The check value of the instance key in force: 64 lowercase hex characters, never the key nor a derived key.

    Raises ``InstanceKeyError`` when the key cannot be used.
    """
    return hmac.new(derive_key(_PURPOSE, _PURPOSE_KEY_LENGTH), _LABEL, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class _FileVerdict:
    """What the key and the check file say, before any stored secret is asked.

    ``kind``: ``unusable`` (no key to compare), ``absent`` (no check file), ``ok`` or ``mismatch`` (the file decided),
    ``unreadable`` (a file that says nothing). ``failure`` names why a file is ``unreadable``, for the one warning.
    """

    kind: Literal["unusable", "absent", "ok", "mismatch", "unreadable"]
    failure: str = ""


def _file_verdict() -> _FileVerdict:
    status = instance_key_status()
    if status.source == "not_created" or status.problem is not None:
        return _FileVerdict("unusable")
    try:
        current = key_check_value()
    except InstanceKeyError:
        return _FileVerdict("unusable")
    try:
        raw = instance_key_check_path().read_bytes()
    except FileNotFoundError:
        return _FileVerdict("absent")
    except OSError as exc:
        return _FileVerdict("unreadable", type(exc).__name__)
    text = raw.decode("ascii", errors="replace")
    stored = text[:-1] if text.endswith("\n") else text
    if not _CHECK_VALUE.fullmatch(stored):
        return _FileVerdict("unreadable", "NotACheckValue")
    return _FileVerdict("ok" if hmac.compare_digest(stored, current) else "mismatch")


def _warn_once(failure: str, message: str, **fields: str) -> None:
    if failure in _warned:
        return
    _warned.add(failure)
    logger.warning(message, **fields)


async def _secrets_verdict(session: AsyncSession) -> InstanceKeyState:
    """R1: ``mismatch`` only when a secret is stored and every stored secret is under another key than the current one."""
    try:
        total = foreign = 0
        current = key_id_of(await asyncio.to_thread(settings_subkey))
        for model in (PluginSystemSetting, PluginUserSetting):
            stored = model.secret_ciphertext.is_not(None)
            total += int(await session.scalar(select(func.count()).select_from(model).where(stored)) or 0)
            foreign += int(await session.scalar(select(func.count()).select_from(model).where(stored, model.key_id != current)) or 0)
    except Exception as exc:  # noqa: BLE001 — isolation boundary: a failing query must never stop the backups, so it says ok
        _warn_once("query", _QUERY_FAILED_MESSAGE, error=type(exc).__name__)
        return "ok"
    return "mismatch" if total and foreign == total else "ok"


async def _evaluate(session: AsyncSession) -> tuple[InstanceKeyState, _FileVerdict]:
    verdict = await asyncio.to_thread(_file_verdict)
    if verdict.kind == "unreadable":
        _warn_once("file", UNREADABLE_MESSAGE, error=verdict.failure)
    if verdict.kind == "mismatch":
        return "mismatch", verdict
    if verdict.kind == "absent":
        return await _secrets_verdict(session), verdict
    return "ok", verdict


async def instance_key_state(session: AsyncSession) -> InstanceKeyState:
    """``ok`` or ``mismatch`` for the instance key as it is now; never raises, creates nothing, remembers nothing."""
    try:
        state, _verdict = await _evaluate(session)
    except Exception as exc:  # noqa: BLE001 — isolation boundary: whatever fails, the answer is ok and one warning
        _warn_once("state", _STATE_FAILED_MESSAGE, error=type(exc).__name__)
        return "ok"
    return state


def _write_check_value(replace: bool) -> None:
    """Write the check value: ``replace`` swaps any file, otherwise the first of several workers to publish it stays.

    Written to a temporary file in the folder and published whole (a hard link that fails when the file exists, or an
    atomic replace), so a reader never meets half a value. The folder is ``0700`` when made, the file ``0600``.
    """
    path = instance_key_check_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    content = (key_check_value() + "\n").encode("ascii")
    descriptor, temporary = tempfile.mkstemp(prefix=".instance.key.check-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError:
                return
            except OSError:
                if not _create_exclusively(path, content):
                    return
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    _sync_directory(path.parent)


async def check_instance_key_at_start(session: AsyncSession) -> None:
    """Startup step ``instance-key-check``: write the check value on a first start, say a mismatch, accept a deliberate change.

    Never raises: a start that cannot write the file goes on with one warning naming the class of the failure.
    """
    try:
        state, verdict = await _evaluate(session)
        if verdict.kind == "unusable":
            return
        if instance_key_accept():
            await asyncio.to_thread(_write_check_value, True)
            logger.warning(ACCEPTED_MESSAGE, variable=ACCEPT_VARIABLE)
        elif state == "mismatch":
            logger.error(MISMATCH_MESSAGE, source="check_file" if verdict.kind == "mismatch" else "stored_secrets")
        elif verdict.kind == "absent":
            await asyncio.to_thread(_write_check_value, False)
    except Exception as exc:  # noqa: BLE001 — isolation boundary: a diagnostic must never stop the start; the class name only
        logger.warning(_START_FAILED_MESSAGE, error=type(exc).__name__)


async def run_instance_key_check_at_start() -> None:
    """The step's body: ``check_instance_key_at_start()`` on a session of its own."""
    async with AsyncSession(get_async_engine()) as session:
        await check_instance_key_at_start(session)


async def check_instance_key(session: AsyncSession) -> ConfigCheck:
    """The check of the admin's Security tab: ``ok``, or an ``error`` on a mismatch."""
    if await instance_key_state(session) == "ok":
        return ConfigCheck(CHECK_ID, "ok", "instance.checks.instanceKey.ok")
    return ConfigCheck(
        CHECK_ID,
        "error",
        "instance.checks.instanceKey.mismatch",
        {},
        "The instance key is not the one this instance's data was written with. Put the right key back and restart; " f"for a deliberate change start once with {ACCEPT_VARIABLE}=1",
    )
