"""Report-set routes of BRIM: preview and combine the members of a set, fix gaps in the combined ledger."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.brokers.guards import require_broker_editor
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.brim import (
    BRIMGapFixRequest,
    BRIMGapFixResponse,
    BRIMSetCombineResponse,
    BRIMSetPreview,
    BRIMSetRequest,
)
from backend.app.services.brim import brim_gap_fix, brim_report_sets
from backend.app.services.brim.brim_report_sets import BRIMLedgerUnreadable, BRIMSetError, BRIMSetIncomplete, BRIMSetStorageLimit
from backend.app.services.platform.storage_limit import storage_limit_detail

logger = get_logger(__name__)

set_router = APIRouter()


def _set_error_detail(error: BRIMSetError) -> dict:
    detail = {"code": error.code, "message": error.message}
    if isinstance(error, BRIMSetStorageLimit):
        # C8: the space limit would be passed by the combined file; the numbers for the message, as an upload's refusal gives them.
        detail = storage_limit_detail(error.problem)
    if isinstance(error, BRIMSetIncomplete):
        detail["missing_roles"] = error.missing_roles
    if isinstance(error, BRIMLedgerUnreadable):
        # E-21: the wizard shows ``importWizard.reportSet.gapFix.ledgerUnreadable.<reason>`` with ``params``; ``message`` stays English.
        detail["reason"] = error.reason
        detail["params"] = error.params
    return detail


@set_router.post("/sets/preview", response_model=BRIMSetPreview)
async def preview_report_set(
    request: BRIMSetRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMSetPreview:
    """
    Preview a report set: the files uploaded together for a broker and read by one plugin.

    Returns each file's role and coverage, the roles still missing (with the period
    their export must cover), segments, gaps, the broker history already in
    LibreFolio and warnings with stable codes. Writes nothing. The files listed in
    ``exclude_file_ids`` (originals of the upload the user left out) are no members.
    """
    await require_broker_editor(request.broker_id, current_user, session)
    try:
        return await brim_report_sets.preview_set(session, broker_id=request.broker_id, plugin_code=request.plugin_code, batch_id=request.batch_id, exclude_file_ids=request.exclude_file_ids)
    except BRIMSetError as e:
        raise HTTPException(status_code=e.status_code, detail=_set_error_detail(e)) from e


@set_router.post("/sets/combine", response_model=BRIMSetCombineResponse)
async def combine_report_set(
    request: BRIMSetRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMSetCombineResponse:
    """
    Combine a complete report set into its combined file, or reuse the identical one.

    The combined file is saved next to the originals and parsed like any other file.
    An incomplete set answers 422 with the missing roles.
    """
    await require_broker_editor(request.broker_id, current_user, session)
    try:
        return await brim_report_sets.combine_set(session, broker_id=request.broker_id, plugin_code=request.plugin_code, batch_id=request.batch_id, user_id=current_user.id, exclude_file_ids=request.exclude_file_ids)
    except BRIMSetError as e:
        raise HTTPException(status_code=e.status_code, detail=_set_error_detail(e)) from e


@set_router.post("/gap-fix", response_model=BRIMGapFixResponse)
async def gap_fix(
    request: BRIMGapFixRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> BRIMGapFixResponse:
    """
    Compare the bank's truth points with what LibreFolio will know, and propose the corrections.

    For each checkpoint, in date order, LibreFolio's state is the saved transactions
    (minus the ones the editor is deleting) plus the editor's unsaved rows, the
    wizard's selection and the corrections of the earlier checkpoints. Only the
    differences are proposed, as transactions tagged ``gap_fix``. Verifications are
    compared, never corrected. Writes nothing.
    """
    await require_broker_editor(request.broker_id, current_user, session)
    try:
        return await brim_gap_fix.compute_gap_fix(session, request)
    except BRIMSetError as e:
        raise HTTPException(status_code=e.status_code, detail=_set_error_detail(e)) from e
