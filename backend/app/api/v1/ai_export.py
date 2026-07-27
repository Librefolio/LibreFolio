"""Catalog and authenticated snapshot endpoints for AI Export."""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.schemas.ai_export import (
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
    AiExportProblemCode,
    AiExportProblemResponse,
    AiExportSnapshotRequest,
    AiExportSnapshotResponse,
    AiExportSnapshotSourceFailureProblem,
    AiExportTargetReference,
    AiExportTaskNotApplicableProblem,
    AiExportUnsupportedProfileProblem,
)
from backend.app.services.ai_export.assemblers import (
    AiExportEntityNotFoundError,
    AiExportSourceFailureError,
    AiExportTaskNotApplicableError,
)
from backend.app.services.ai_export.models import UnsupportedAiExportProfileError
from backend.app.services.ai_export.service import (
    AiExportBrokerAccessDeniedError,
    AiExportSnapshotService,
    AiExportSnapshotSourceError,
)

router = APIRouter(prefix="/ai-export", tags=["AI Export"])

_PROBLEM_ADAPTER = TypeAdapter(AiExportProblem)
_INVALID_CODE_CHARACTERS = re.compile(r"[^a-z0-9_.-]+")


def _profile_id(request: AiExportSnapshotRequest) -> str:
    return f"{request.domain.value}.{request.task.value}.{request.detail_level.value}"


def _problem_detail(problem: AiExportProblemBase) -> dict[str, object]:
    validated = _PROBLEM_ADAPTER.validate_python(problem)
    return validated.model_dump(mode="json", exclude_none=True)


def _target_reference(request: AiExportSnapshotRequest) -> AiExportTargetReference:
    if isinstance(request, AiExportAssetSnapshotRequest):
        return AiExportAssetTargetReference(kind="asset", asset_id=request.asset_id)
    if isinstance(request, AiExportFxSnapshotRequest):
        return AiExportFxPairTargetReference(
            kind="fx_pair",
            base_currency=request.base_currency,
            quote_currency=request.quote_currency,
        )
    if isinstance(request, AiExportBrokerSnapshotRequest):
        return AiExportBrokerTargetReference(kind="broker", broker_id=request.broker_id)
    if isinstance(request, AiExportPortfolioSnapshotRequest):
        return AiExportPortfolioTargetReference(kind="portfolio")
    raise TypeError(f"Unsupported AI Export request type: {type(request).__name__}")


def _code_part(value: str, fallback: str) -> str:
    normalized = _INVALID_CODE_CHARACTERS.sub("_", value.strip().lower()).strip("._-")
    if not normalized:
        normalized = fallback
    if not normalized[0].isalpha():
        normalized = f"{fallback}_{normalized}"
    return normalized[:63].rstrip("._-") or fallback


def _source_operation_code(error: AiExportSourceFailureError) -> str:
    return f"{_code_part(error.source_code, 'source')}.{_code_part(error.operation, 'operation')}"


def get_ai_export_snapshot_service(
    session: AsyncSession = Depends(get_session_generator),
) -> AiExportSnapshotService:
    return AiExportSnapshotService(session)


@router.get(
    "/catalog",
    response_model=AiExportCatalogResponse,
    summary="List supported AI Export profiles",
)
def get_ai_export_catalog() -> AiExportCatalogResponse:
    return AiExportSnapshotService.get_catalog()


@router.post(
    "/snapshot",
    response_model=AiExportSnapshotResponse,
    summary="Build an AI Export snapshot",
    responses={
        403: {"model": AiExportProblemResponse, "description": "Requested broker scope is not fully accessible."},
        404: {"model": AiExportProblemResponse, "description": "Requested snapshot entity was not found."},
        409: {"model": AiExportProblemResponse, "description": "Requested task is not applicable to the selected target."},
        422: {"model": AiExportProblemResponse, "description": "Requested profile is not supported."},
        503: {"model": AiExportProblemResponse, "description": "Required snapshot source is unavailable."},
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
            code=AiExportProblemCode.BROKER_ACCESS_DENIED,
            message="Access denied for one or more requested brokers.",
            domain=body.domain,
            task=body.task,
            detail_level=body.detail_level,
            profile_id=_profile_id(body),
            denied_broker_ids=list(exc.denied_broker_ids),
        )
        raise HTTPException(status_code=403, detail=_problem_detail(problem)) from exc
    except UnsupportedAiExportProfileError as exc:
        problem = AiExportUnsupportedProfileProblem(
            code=AiExportProblemCode.UNSUPPORTED_PROFILE,
            message="Requested AI Export profile is not supported.",
            domain=body.domain,
            task=body.task,
            detail_level=body.detail_level,
            profile_id=_profile_id(body),
            supported_profiles=list(exc.supported_profile_ids),
        )
        raise HTTPException(status_code=422, detail=_problem_detail(problem)) from exc
    except AiExportEntityNotFoundError as exc:
        problem = AiExportEntityNotFoundProblem(
            code=AiExportProblemCode.ENTITY_NOT_FOUND,
            message="Requested AI Export entity was not found.",
            domain=body.domain,
            task=body.task,
            detail_level=body.detail_level,
            profile_id=_profile_id(body),
            entity_reference=_target_reference(body),
        )
        raise HTTPException(status_code=404, detail=_problem_detail(problem)) from exc
    except AiExportTaskNotApplicableError as exc:
        problem = AiExportTaskNotApplicableProblem(
            code=AiExportProblemCode.TASK_NOT_APPLICABLE,
            message="Requested AI Export task is not applicable.",
            domain=body.domain,
            task=body.task,
            detail_level=body.detail_level,
            profile_id=_profile_id(body),
            applicability_code=exc.applicability_code,
            reason_code=exc.reason_code,
        )
        raise HTTPException(status_code=409, detail=_problem_detail(problem)) from exc
    except AiExportSourceFailureError as exc:
        problem = AiExportSnapshotSourceFailureProblem(
            code=AiExportProblemCode.SNAPSHOT_SOURCE_FAILURE,
            message="AI Export snapshot source is unavailable.",
            domain=body.domain,
            task=body.task,
            detail_level=body.detail_level,
            profile_id=_profile_id(body),
            source_code=_source_operation_code(exc),
            retryable=exc.retryable,
        )
        raise HTTPException(status_code=503, detail=_problem_detail(problem)) from exc
    except AiExportSnapshotSourceError as exc:
        problem = AiExportSnapshotSourceFailureProblem(
            code=AiExportProblemCode.SNAPSHOT_SOURCE_FAILURE,
            message="AI Export snapshot source is unavailable.",
            domain=body.domain,
            task=body.task,
            detail_level=body.detail_level,
            profile_id=_profile_id(body),
            source_code=exc.source_code,
            retryable=exc.retryable,
        )
        raise HTTPException(status_code=503, detail=_problem_detail(problem)) from exc


__all__ = ["get_ai_export_snapshot_service", "router"]
