#!/usr/bin/env python3
"""Explicit schema-only Tool export; does not import the application or start workers."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import TextIO
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "frontend" / "src" / "lib" / "api" / "tool-contracts.openapi.json"


def _release_created_lock(lock: Path, handle: TextIO, identity: os.stat_result, ownership: str | None) -> None:
    def assert_identity(current: os.stat_result) -> None:
        if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise RuntimeError(f"Tool codegen lock path was replaced; refusing to remove it: {lock}")

    assert_identity(lock.lstat())
    if ownership is not None:
        handle.seek(0)
        if handle.read(len(ownership) + 1) != ownership:
            raise RuntimeError(f"Tool codegen lock ownership changed: {lock}")
    # Retain the original handle until unlink so its inode cannot be reused.
    assert_identity(lock.lstat())
    lock.unlink()


def _write_lock_header(lock: Path, handle: TextIO, ownership: str) -> None:
    if handle.write(ownership) != len(ownership):
        raise OSError(f"Incomplete Tool codegen lock initialization: {lock}")
    handle.flush()


def _tool_contract_bytes() -> bytes:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from backend.app.services.tools.schema_export import export_tool_contracts_document  # noqa: PLC0415 — discover schemas only inside the explicit export command

    document = export_tool_contracts_document()
    return json.dumps(document, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _raise_export_failures(lock: Path, failures: list[BaseException]) -> None:
    if len(failures) == 1:
        raise failures[0]
    if failures:
        raise BaseExceptionGroup(f"Tool export and lock cleanup failed: {lock}", failures)


def export_tool_contracts(output_path: str | Path = DEFAULT_OUTPUT) -> Path:
    """Discover real schema roots and atomically write their unadapted build document."""
    output = Path(os.path.abspath(output_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.parent / ".tools-codegen.lock"
    pending = output.with_name(f"{output.name}.{os.getpid()}.{uuid4().hex}.pending")
    ownership = json.dumps({"pid": os.getpid(), "token": uuid4().hex})
    try:
        lock_handle = lock.open("x+", encoding="utf-8")
    except FileExistsError as exc:
        raise RuntimeError(f"Tool codegen is locked: {lock}. Verify its owner before removing a stale lock.") from exc
    lock_identity: os.stat_result | None = None
    lock_initialized = False
    pending_created = False
    failures: list[BaseException] = []
    try:
        lock_identity = os.fstat(lock_handle.fileno())
        _write_lock_header(lock, lock_handle, ownership)
        lock_initialized = True
        encoded = _tool_contract_bytes()
        if output.is_symlink() or (output.exists() and not output.is_file()):
            raise ValueError(f"Refusing non-file Tool schema output: {output}")
        with pending.open("xb") as handle:
            pending_created = True
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        pending.replace(output)
    except BaseException as exc:
        failures.append(exc)
    try:
        if pending_created:
            pending.unlink(missing_ok=True)
    except BaseException as exc:
        failures.append(exc)
    try:
        if lock_identity is None:
            lock_identity = os.fstat(lock_handle.fileno())
        _release_created_lock(lock, lock_handle, lock_identity, ownership if lock_initialized else None)
    except BaseException as exc:
        failures.append(exc)
    try:
        lock_handle.close()
    except BaseException as exc:
        failures.append(exc)
    _raise_export_failures(lock, failures)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = export_tool_contracts(args.output)
    print(f"Tool contracts exported to: {output}")


if __name__ == "__main__":
    main()
