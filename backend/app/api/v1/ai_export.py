"""Catalog and authenticated snapshot endpoints for component-based AI Export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.schemas.ai_export_runtime import (
    AiExportAssetSnapshotRequest,
    AiExportAssetTargetReference,
    AiExportBrokerAccessDeniedProblem,
    AiExportBrokerSnapshotRequest,
    AiExportBrokerTargetReference,
    AiExportCatalogResponse,
    AiExportEntityNotFoundProblem,
    AiExportFxPairTargetReference,
    AiExportFxSnapshotRequest,
    AiExportPortfolioSnapshotRequest,
    AiExportPortfolioTargetReference,
    AiExportProblem,
    AiExportProblemBase,
    AiExportProblemResponse,
    AiExportSelectionNotApplicableProblem,
    AiExportSnapshotRequest,
    AiExportSnapshotResponse,
    AiExportSnapshotSourceFailureProblem,
    AiExportTargetReference,
    AiExportUnsupportedSelectionProblem,
    AiExportVersionMismatchProblem,
)
from backend.app.services.ai_export.runtime_service import (
    AiExportBrokerAccessDeniedError,
    AiExportEntityNotFoundError,
    AiExportSelectionNotApplicableError,
    AiExportSnapshotService,
    AiExportSnapshotSourceError,
    AiExportUnsupportedSelectionError,
    AiExportVersionMismatchError,
)

router = APIRouter(prefix="/ai-export", tags=["AI Export"])

_PROBLEM_ADAPTER = TypeAdapter(AiExportProblem)


def _problem_detail(problem: AiExportProblemBase) -> dict[str, object]:
    validated = _PROBLEM_ADAPTER.validate_python(problem)
    return validated.model_dump(mode="json", exclude_none=True)


def _target_reference(request: AiExportSnapshotRequest) -> AiExportTargetReference:
    if isinstance(request, AiExportPortfolioSnapshotRequest):
        return AiExportPortfolioTargetReference(kind="portfolio")
    if isinstance(request, AiExportBrokerSnapshotRequest):
        return AiExportBrokerTargetReference(kind="broker", broker_id=request.broker_id)
    if isinstance(request, AiExportAssetSnapshotRequest):
        return AiExportAssetTargetReference(kind="asset", asset_id=request.asset_id)
    if isinstance(request, AiExportFxSnapshotRequest):
        return AiExportFxPairTargetReference(
            kind="fx_pair",
            base_currency=request.base_currency,
            quote_currency=request.quote_currency,
        )
    raise TypeError(f"unsupported AI Export request type: {type(request).__name__}")


def _problem_base(request: AiExportSnapshotRequest) -> dict[str, object]:
    return {
        "domain": request.domain,
        "selection_kind": request.selection.kind,
        "selection_id": request.selection.id,
        "detail_level": request.detail_level,
    }


def get_ai_export_snapshot_service(
    session: AsyncSession = Depends(get_session_generator),
) -> AiExportSnapshotService:
    return AiExportSnapshotService(session)


@router.get(
    "/catalog",
    response_model=AiExportCatalogResponse,
    summary="List AI Export datasets and analyses",
)
def get_ai_export_catalog() -> AiExportCatalogResponse:
    return AiExportSnapshotService.get_catalog()


@router.post(
    "/snapshot",
    response_model=AiExportSnapshotResponse,
    summary="Build an AI Export dataset or analysis snapshot",
    responses={
        403: {
            "model": AiExportProblemResponse,
            "description": "Requested broker scope is not fully accessible.",
        },
        404: {
            "model": AiExportProblemResponse,
            "description": "Requested entity was not found.",
        },
        409: {
            "model": AiExportProblemResponse,
            "description": "Catalog, selection, template, or contract version mismatch.",
        },
        422: {
            "model": AiExportProblemResponse,
            "description": "Selection is unsupported or not applicable.",
        },
        503: {
            "model": AiExportProblemResponse,
            "description": "A required snapshot component is unavailable.",
        },
    },
)
async def build_ai_export_snapshot(
    body: AiExportSnapshotRequest,
    service: AiExportSnapshotService = Depends(get_ai_export_snapshot_service),
    current_user: User = Depends(get_current_user),
) -> AiExportSnapshotResponse:
    try:
        return await service.build_snapshot(current_user.id, body)
    except AiExportBrokerAccessDeniedError as exc:
        problem = AiExportBrokerAccessDeniedProblem(
            code="broker_access_denied",
            message="Access denied for one or more requested brokers.",
            denied_broker_ids=list(exc.denied_broker_ids),
            **_problem_base(body),
        )
        raise HTTPException(status_code=403, detail=_problem_detail(problem)) from exc
    except AiExportEntityNotFoundError as exc:
        problem = AiExportEntityNotFoundProblem(
            code="entity_not_found",
            message="Requested AI Export entity was not found.",
            entity_reference=_target_reference(body),
            **_problem_base(body),
        )
        raise HTTPException(status_code=404, detail=_problem_detail(problem)) from exc
    except AiExportVersionMismatchError as exc:
        problem = AiExportVersionMismatchProblem(
            code="version_mismatch",
            message="AI Export catalog or contract version mismatch.",
            field=exc.field,
            expected=exc.expected,
            actual=exc.actual,
            **_problem_base(body),
        )
        raise HTTPException(status_code=409, detail=_problem_detail(problem)) from exc
    except AiExportUnsupportedSelectionError as exc:
        problem = AiExportUnsupportedSelectionProblem(
            code="unsupported_selection",
            message="Requested AI Export selection is not supported.",
            **_problem_base(body),
        )
        raise HTTPException(status_code=422, detail=_problem_detail(problem)) from exc
    except AiExportSelectionNotApplicableError as exc:
        problem = AiExportSelectionNotApplicableProblem(
            code="selection_not_applicable",
            message="Requested AI Export selection is not applicable.",
            applicability_code=exc.applicability_code,
            reason_code=exc.reason_code,
            **_problem_base(body),
        )
        raise HTTPException(status_code=422, detail=_problem_detail(problem)) from exc
    except AiExportSnapshotSourceError as exc:
        problem = AiExportSnapshotSourceFailureProblem(
            code="snapshot_source_failure",
            message="A required AI Export component is unavailable.",
            component_id=exc.component_id,
            retryable=exc.retryable,
            **_problem_base(body),
        )
        raise HTTPException(status_code=503, detail=_problem_detail(problem)) from exc


__all__ = ["get_ai_export_snapshot_service", "router"]
