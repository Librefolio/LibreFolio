"""BRIM parsing coordination: ask a plugin whether it reads a stored file, and run its ``parse()`` on it."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from backend.app.schemas.brim import (
    BRIMParseOutput,
    BRIMPluginCheck,
)
from backend.app.services.brim import storage
from backend.app.services.brim.brim_provider import BRIMCannotParseError, BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.utils.runtime.secret_masking import mask_exception, secrets_in_flight

logger = structlog.get_logger(__name__)


def _relocated_path(file_id: str, file_path: Path) -> Optional[Path]:
    """Return where a file went when a concurrent parse moved it, else ``None``.

    Parsing a report transitions it ``uploaded → parsed``, which physically renames
    the file. A path resolved a moment earlier is then stale, and every read through
    it fails for a reason that has nothing to do with the file's contents — the
    plugin reports "cannot read" about a file it reads perfectly well.

    ``None`` means the caller's failure was genuine and must be propagated: either
    the original path still exists (so the file never moved), or re-resolution finds
    nothing new. Only a *demonstrated* move earns a retry.
    """
    if file_path.exists():
        return None
    moved_path = storage.get_file_path(file_id)
    if moved_path is None or moved_path == file_path:
        return None
    return moved_path


def _refusal_message(plugin: Any, plugin_code: str, file_name: str, checked_path: Path) -> str:
    """The parse guard's refusal, completed with the plugin's reason when it gives one.

    It names the plugin by its name and the file by the name it was uploaded with, as the user
    knows them, never by the plugin code or the stored ``<file_id>.<ext>``. The reason is asked
    on ``checked_path``, the path the guard looked at last. It is read with ``getattr``, so a
    plugin without the method keeps the plain refusal; a reason that raises is logged and
    dropped, so the user still gets this 400 and never a 500.
    """
    plugin_name = getattr(plugin, "provider_name", None) or plugin_code
    message = f"Plugin '{plugin_name}' cannot parse file '{file_name}'"
    explain = getattr(plugin, "cannot_parse_reason", None)
    if explain is None:
        return message
    try:
        reason = explain(checked_path)
    except Exception as e:
        logger.warning("Plugin failed to explain its refusal", plugin_code=plugin_code, error=str(e))
        return message
    return f"{message}: {reason}" if reason else message


def _refusal_detail(plugin: Any, plugin_code: str, checked_path: Path) -> Optional[Dict[str, Any]]:
    """The plugin's refusal (``cannot_parse_detail``) as a plain dict, or ``None``: it has nothing to add, or it raised (logged)."""
    explain = getattr(plugin, "cannot_parse_detail", None)
    if explain is None:
        return None
    try:
        refusal = explain(checked_path)
    except Exception as e:  # noqa: BLE001 — isolation boundary: a plugin that fails to explain must not turn a 400 into a 500
        logger.warning("Plugin failed to explain its refusal", plugin_code=plugin_code, error=str(e))
        return None
    if refusal is None:
        return None
    return {"code": refusal.code, "message": refusal.message, "context": dict(refusal.context)}


def _check_path(plugin: BRIMProvider, file_path: Path) -> BRIMPluginCheck:
    """``plugin``'s answer about one path. A check or an explanation that raises is logged: it never reaches the caller."""
    code = plugin.provider_code
    try:
        accepted = bool(plugin.can_parse(file_path))
    except Exception as e:
        logger.warning("Plugin failed to check a file", plugin_code=code, error=str(e))
        accepted = False
    if accepted:
        return BRIMPluginCheck(plugin_code=code, can_parse=True)
    try:
        return BRIMPluginCheck(plugin_code=code, can_parse=False, refusal=plugin.cannot_parse_detail(file_path))
    except Exception as e:
        logger.warning("Plugin failed to explain its refusal", plugin_code=code, error=str(e))
        return BRIMPluginCheck(plugin_code=code, can_parse=False)


def check_file_with_plugin(file_id: str, plugin: BRIMProvider) -> Optional[BRIMPluginCheck]:
    """Whether ``plugin`` reads an uploaded file and, if not, why; ``None`` when the file's content is gone.

    A refusal on a path that a concurrent parse has just moved is asked again on the new path,
    as the parse guard does.
    """
    file_path = storage.get_file_path(file_id)
    if file_path is None:
        return None
    check = _check_path(plugin, file_path)
    if not check.can_parse:
        moved_path = _relocated_path(file_id, file_path)
        if moved_path is not None:
            check = _check_path(plugin, moved_path)
    return check


def parse_file(file_id: str, plugin_code: str, broker_id: int, settings: Optional[BoundSettings] = None) -> BRIMParseOutput:
    """
    Parse a file using the specified plugin (preview only, no DB persistence).

    ``settings`` (W-BS): the values of a plugin that declares settings fields, resolved by the caller (the parent of the parse
    pool, ``brim_parse_pool.parse_file_offloaded``): bound on the plugin instance before it parses, its secrets in flight for the
    length of the parse (masked in every line logged meanwhile, and in the exception the parse raises). ``None``, always the case
    for a plugin without fields: the parse is what it was.
    """
    secrets = settings.secret_values() if settings is not None else frozenset()
    with secrets_in_flight(secrets):
        try:
            return _parse_file(file_id, plugin_code, broker_id, settings)
        except BaseException as error:
            if settings is not None:
                mask_exception(error, secrets, whole=settings.carries_user_secrets)
            raise


def _parse_file(file_id: str, plugin_code: str, broker_id: int, settings: Optional[BoundSettings]) -> BRIMParseOutput:
    """
    The parse of ``parse_file``, with the plugin's settings bound.

    Process:
    1. Call get_file_path(file_id) to get actual file location
       - Raise FileNotFoundError if file doesn't exist
    2. Call BRIMProviderRegistry.get_provider_instance(plugin_code)
       - Raise ValueError if plugin not found
    3. Call plugin.can_parse(file_path)
       - Raise ValueError if plugin cannot parse this file type
    4. Call plugin.parse(file_path, broker_id) → BRIMParseOutput
    5. Return the BRIMParseOutput as-is

    IMPORTANT: This function does NOT persist anything to DB.
    It's used for preview so user can review/edit before confirming.

    Args:
        file_id: UUID of the uploaded file
        plugin_code: Provider code (e.g., "broker_generic_csv")
        broker_id: Target broker ID for the transactions

    Returns:
        BRIMParseOutput with transactions, warnings, extracted_assets, asset_events

    Raises:
        FileNotFoundError: File not found
        ValueError: Plugin not found or cannot parse file
        BRIMParseError: Plugin-specific parsing error
    """
    # Get file path
    file_path = storage.get_file_path(file_id)
    if not file_path:
        raise FileNotFoundError(f"File not found: {file_id}")

    # Get plugin instance
    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    if not plugin:
        raise ValueError(f"Plugin not found: {plugin_code}")
    if settings is not None:
        plugin.bind_settings(settings)

    # Verify plugin can parse this file. The guard reads the file, so it loses
    # the same race as the parse below and needs the same re-resolution: a stale
    # path makes can_parse() answer False, which would be reported to the user as
    # "this plugin cannot read your file" about a file the plugin reads fine.
    if not plugin.can_parse(file_path):
        moved_path = _relocated_path(file_id, file_path)
        if moved_path is None or not plugin.can_parse(moved_path):
            file_info = storage.get_file_info(file_id)
            file_name = file_info.filename if file_info else file_path.name
            refused_path = moved_path or file_path
            raise BRIMCannotParseError(
                _refusal_message(plugin, plugin_code, file_name, refused_path),
                plugin_code=plugin_code,
                plugin_name=getattr(plugin, "provider_name", None) or plugin_code,
                refusal=_refusal_detail(plugin, plugin_code, refused_path),
            )
        logger.info("File moved before parse check, retrying at new location", file_id=file_id, new_path=str(moved_path))
        file_path = moved_path

    # Parse file
    logger.info("Parsing file with plugin", file_id=file_id, plugin_code=plugin_code, broker_id=broker_id)

    try:
        output: BRIMParseOutput = plugin.parse(file_path, broker_id)
    except Exception:
        moved_path = _relocated_path(file_id, file_path)
        if moved_path is None:
            raise
        logger.info("File moved during parse, retrying at new location", file_id=file_id, new_path=str(moved_path))
        output = plugin.parse(moved_path, broker_id)

    logger.info(
        "File parsed successfully",
        file_id=file_id,
        plugin_code=plugin_code,
        transaction_count=len(output.transactions),
        warning_count=len(output.warnings),
        extracted_asset_count=len(output.extracted_assets),
    )

    return output
