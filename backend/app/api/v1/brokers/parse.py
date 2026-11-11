"""Parse route of BRIM (``POST /brokers/import/files/{file_id}/parse``) and the report-set rules it applies."""

import asyncio
from datetime import date
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.brokers.guards import get_brim_file_with_access, require_broker_editor
from backend.app.db.models import User, UserRole
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.brim import (
    BRIMAssetMapping,
    BRIMCheckpoint,
    BRIMFileInfo,
    BRIMParseOutput,
    BRIMParseRequest,
    BRIMParseResponse,
    BRIMVerification,
)
from backend.app.services.brim import brim_report_sets, storage
from backend.app.services.brim.brim_parse_pool import parse_file_offloaded
from backend.app.services.brim.brim_provider import BRIMCannotParseError, BRIMParseError, BRIMProvider, BRIMSetRequiredError
from backend.app.services.brim.candidates import search_asset_candidates_bulk
from backend.app.services.brim.duplicates import detect_tx_duplicates
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.plugin_settings.runtime import bound_settings_for

logger = get_logger(__name__)

parse_router = APIRouter()

# =============================================================================
# PARSING & IMPORT
# =============================================================================


def _set_required_http_error(error: BRIMSetRequiredError) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": "set_required", "message": error.message, "missing_roles": error.missing_roles})


def _refuse_report_set_member(plugin_code: str, file_info: BRIMFileInfo) -> Optional[BRIMProvider]:
    """The plugin instance; a report-set member alone answers 422 and is NOT moved to failed."""
    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    if plugin is not None:
        try:
            brim_report_sets.ensure_parseable(plugin, file_info)
        except BRIMSetRequiredError as e:
            raise _set_required_http_error(e) from e
    return plugin


async def _report_set_truth(session: AsyncSession, plugin: Optional[BRIMProvider], broker_id: int, parse_output: BRIMParseOutput) -> Tuple[List[BRIMCheckpoint], List[BRIMVerification], Optional[date]]:
    """Checkpoints, verifications and history start of a combined report-set file; empty otherwise."""
    if plugin is None or not plugin.is_report_set_plugin:
        return [], [], None
    return await brim_report_sets.apply_history(session, broker_id=broker_id, plugin=plugin, output=parse_output)


@parse_router.post("/files/{file_id}/parse", response_model=BRIMParseResponse)
async def parse_file(
    file_id: str,
    request: BRIMParseRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMParseResponse:
    """
    Parse a file and return transactions for preview.

    This is a preview operation - no data is persisted to the database.
    The user can review and modify the parsed transactions before
    sending them to POST /transactions endpoint.

    Requires EDITOR or OWNER access on the file's broker, and on the request's ``broker_id``: the broker the parse
    imports into and compares duplicates and report-set history against (decision 36). The administrator passes.

    If plugin_code is 'auto' (default), the system will automatically
    detect the best plugin based on file content analysis.

    Returns:
    - transactions: Parsed transactions (may have fake asset IDs)
    - asset_mappings: Mapping from fake IDs to candidate real assets
    - duplicates: Report of potential duplicate transactions
    - warnings: Parser warnings (skipped rows, etc.)

    Note: Asset mapping and duplicate detection are done in CORE,
    not in the plugin. Plugins only parse the file format.
    """
    # Get file info and check permissions
    file_info = await get_brim_file_with_access(
        file_id,
        current_user,
        session,
        min_role=UserRole.EDITOR,
        denied_detail="EDITOR or OWNER access required to parse files",
    )
    # The broker the parse compares against (duplicates, report-set history) is read too: the caller must be its
    # EDITOR or OWNER, as on /duplicates (decision 36: nobody works on the data of a broker they cannot see).
    await require_broker_editor(request.broker_id, current_user, session)

    # Determine plugin to use
    plugin_code = request.plugin_code
    if plugin_code == "auto":
        # Auto-detect plugin based on file content
        file_path = await asyncio.to_thread(storage.get_file_path, file_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="File not found")

        # Detection sniffs the file itself — blocking read, same rule as the parse below.
        detected_plugin = await asyncio.to_thread(BRIMProviderRegistry.auto_detect_plugin, file_path)
        if detected_plugin:
            plugin_code = detected_plugin
            logger.info("Auto-detected plugin for file", file_id=file_id, detected_plugin=plugin_code)
        else:
            # Fallback to generic CSV
            plugin_code = "broker_generic_csv"
            logger.info("No specific plugin detected, using generic CSV", file_id=file_id)

    plugin = _refuse_report_set_member(plugin_code, file_info)

    try:
        # 1. Parse file using plugin (plugin only reads file format)
        # The values are resolved once, for the user who imports: they reach the parse, and their fingerprint is stored with the
        # result, so that a later change of a setting makes the file stale (CP12).
        bound = await bound_settings_for(BRIMProviderRegistry, plugin_code, user_id=current_user.id)
        parse_output = await parse_file_offloaded(file_id, plugin_code, request.broker_id, user_id=current_user.id, bound=bound)
        transactions = parse_output.transactions
        warnings = parse_output.warnings
        validation_issues = parse_output.validation_issues
        field_todos = parse_output.field_todos
        extracted_assets = parse_output.extracted_assets
        checkpoints, verifications, history_start = await _report_set_truth(session, plugin, request.broker_id, parse_output)

        # 2. Build asset mappings (CORE responsibility)
        # Search DB for candidates for each extracted asset
        # One round-trip for the whole file: the per-asset helper issued up to five
        # queries each, so a thirty-instrument report spent a hundred-odd sequential
        # waits inside a single request.
        bulk = await search_asset_candidates_bulk(
            session,
            [(info.extracted_symbol, info.extracted_isin, info.extracted_name) for info in extracted_assets.values()],
        )

        asset_mappings = []
        for fake_id, info in extracted_assets.items():
            candidates, auto_selected = bulk.get(
                (info.extracted_symbol, info.extracted_isin, info.extracted_name),
                ([], None),
            )
            asset_mappings.append(
                BRIMAssetMapping(
                    fake_asset_id=fake_id,
                    extracted_symbol=info.extracted_symbol,
                    extracted_isin=info.extracted_isin,
                    extracted_name=info.extracted_name,
                    candidates=candidates,
                    selected_asset_id=auto_selected,
                    notices=info.notices,
                )
            )

        # 3. Detect duplicates (CORE responsibility)
        # Query DB for existing transactions that match
        # Pass asset_mappings for asset-aware duplicate detection
        duplicates = await detect_tx_duplicates(
            transactions=transactions,
            broker_id=request.broker_id,
            session=session,
            asset_mappings=asset_mappings,
        )

        # Move file to parsed folder on success. Four filesystem operations
        # (rename, read, write, unlink) — off the event loop like every other
        # blocking call in this handler.
        await asyncio.to_thread(storage.move_to_parsed, file_id)

        # Build response
        response = BRIMParseResponse(
            file_id=file_id,
            plugin_code=plugin_code,  # Return actual plugin used (after auto-detection)
            broker_id=request.broker_id,
            transactions=transactions,
            asset_mappings=asset_mappings,
            duplicates=duplicates,
            warnings=warnings,
            validation_issues=validation_issues,
            field_todos=field_todos,
            checkpoints=checkpoints,
            verifications=verifications,
            history_start=history_start,
        )

        # Cache the parse result in file metadata for later retrieval.
        # The current plugin_version is resolved by save_parse_result via
        # the registry (single source of truth) and persisted alongside
        # plugin_code so BRIMFileInfo can compute parse_is_stale if the
        # plugin is bumped later. Off the event loop: the write holds the broker's metadata lock.
        await asyncio.to_thread(
            storage.save_parse_result,
            file_id,
            response.model_dump(mode="json"),
            plugin_code=plugin_code,
            settings_fingerprint=bound.fingerprint if bound is not None else None,
        )

        logger.info(
            "File parsed with asset mapping and duplicate detection",
            file_id=file_id,
            plugin_code=plugin_code,
            transaction_count=len(transactions),
            asset_mappings_count=len(asset_mappings),
            unique_tx_count=len(duplicates.tx_unique_indices),
            possible_duplicates=len(duplicates.tx_possible_duplicates),
            likely_duplicates=len(duplicates.tx_likely_duplicates),
        )

        return response

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None

    except BRIMSetRequiredError as e:
        # A valid export that belongs to a set: never a failure of the file.
        raise _set_required_http_error(e) from e

    except ValueError as e:
        # Parse failed - move to failed folder
        await asyncio.to_thread(storage.move_to_failed, file_id, str(e))
        if isinstance(e, BRIMCannotParseError):
            refusal = e.refusal or {}
            reason = {"code": refusal.get("code"), "message": refusal.get("message"), "context": refusal.get("context") or {}}
            raise HTTPException(status_code=400, detail=_parse_failed_detail(str(e), e.plugin_code or plugin_code, e.plugin_name, reason)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e

    except BRIMParseError as e:
        # Parse failed - move to failed folder
        await asyncio.to_thread(storage.move_to_failed, file_id, e.message)
        reason = {"code": e.details.get("code"), "message": e.message, "context": e.details.get("context") or {}}
        raise HTTPException(status_code=400, detail=_parse_failed_detail(f"Parse error: {e.message}", plugin_code, _plugin_name(plugin_code), reason)) from e


def _plugin_name(plugin_code: str) -> str:
    """The plugin's ``provider_name``, its code when it is not registered."""
    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    return (getattr(plugin, "provider_name", None) if plugin is not None else None) or plugin_code


def _parse_failed_detail(message: str, plugin_code: str, plugin_name: str, reason: dict) -> dict:
    """The 400 of a failed parse (C-70b): a code the wizard translates, the plugin and its reason; ``message`` is the English text."""
    return {"code": "parse_failed", "message": message, "plugin_code": plugin_code, "plugin_name": plugin_name, "reason": reason}
