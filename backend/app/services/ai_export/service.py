"""Standalone orchestration boundary for AI Export snapshot requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess
from backend.app.schemas.ai_export import (
    AiExportAssetSnapshotRequest,
    AiExportBrokerSnapshotRequest,
    AiExportCatalogResponse,
    AiExportFxSnapshotRequest,
    AiExportPortfolioSnapshotRequest,
    AiExportSnapshotRequest,
    AiExportSnapshotResponse,
)
from backend.app.services.ai_export.models import ResolvedProfile
from backend.app.services.ai_export.resolver import get_catalog_response, resolve_profile


@dataclass(frozen=True, slots=True)
class AiExportPreparedRequest:
    """Validated request context passed to domain assemblers."""

    request: AiExportSnapshotRequest
    resolved_profile: ResolvedProfile
    user_id: int
    broker_scope: tuple[int, ...]

    @property
    def broker_ids(self) -> tuple[int, ...]:
        return self.broker_scope


class AiExportSnapshotAssembler(Protocol):
    """Structural contract shared by domain snapshot assemblers."""

    async def assemble(
        self,
        prepared: AiExportPreparedRequest,
        session: AsyncSession,
    ) -> AiExportSnapshotResponse: ...


AiExportSnapshotAssemblerFactory = Callable[[], AiExportSnapshotAssembler]


class AiExportBrokerAccessDeniedError(PermissionError):
    """Raised when any explicitly requested broker is outside user scope."""

    def __init__(self, denied_broker_ids: Sequence[int]) -> None:
        self.denied_broker_ids = tuple(sorted(set(denied_broker_ids)))
        if not self.denied_broker_ids:
            raise ValueError("denied_broker_ids must not be empty")
        super().__init__(f"Access denied for broker IDs: {', '.join(map(str, self.denied_broker_ids))}")


class AiExportSnapshotSourceError(RuntimeError):
    """Raised when a required snapshot source cannot produce output."""

    def __init__(self, source_code: str, *, retryable: bool) -> None:
        self.source_code = source_code
        self.retryable = retryable
        super().__init__(f"AI Export snapshot source failed: {source_code}")


class AiExportSnapshotSourceNotImplementedError(AiExportSnapshotSourceError):
    """Reserved for future internal snapshot domains without an assembler."""

    def __init__(self) -> None:
        super().__init__("assembler_not_implemented", retryable=False)


def _default_asset_assembler() -> AiExportSnapshotAssembler:
    from backend.app.services.ai_export.assemblers.asset import AiExportAssetAssembler  # noqa: PLC0415 — avoid circular import

    return AiExportAssetAssembler()


def _default_fx_assembler() -> AiExportSnapshotAssembler:
    from backend.app.services.ai_export.assemblers.fx import AiExportFxAssembler  # noqa: PLC0415 — avoid circular import

    return AiExportFxAssembler()


def _default_portfolio_assembler() -> AiExportSnapshotAssembler:
    from backend.app.services.ai_export.assemblers.portfolio import AiExportPortfolioAssembler  # noqa: PLC0415 — avoid circular import

    return AiExportPortfolioAssembler()


def _default_broker_assembler() -> AiExportSnapshotAssembler:
    from backend.app.services.ai_export.assemblers.broker import AiExportBrokerAssembler  # noqa: PLC0415 — avoid circular import

    return AiExportBrokerAssembler()


def _select_assembler_factory(
    *,
    instance: AiExportSnapshotAssembler | None,
    factory: AiExportSnapshotAssemblerFactory | None,
    default_factory: AiExportSnapshotAssemblerFactory,
    domain: str,
) -> AiExportSnapshotAssemblerFactory:
    if instance is not None and factory is not None:
        raise ValueError(f"{domain} assembler instance and factory are mutually exclusive")
    if factory is not None:
        return factory
    if instance is not None:
        return lambda: instance
    return default_factory


class AiExportSnapshotService:
    """Prepare authenticated AI Export requests without FastAPI dependencies."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        asset_assembler: AiExportSnapshotAssembler | None = None,
        fx_assembler: AiExportSnapshotAssembler | None = None,
        portfolio_assembler: AiExportSnapshotAssembler | None = None,
        broker_assembler: AiExportSnapshotAssembler | None = None,
        asset_assembler_factory: AiExportSnapshotAssemblerFactory | None = None,
        fx_assembler_factory: AiExportSnapshotAssemblerFactory | None = None,
        portfolio_assembler_factory: AiExportSnapshotAssemblerFactory | None = None,
        broker_assembler_factory: AiExportSnapshotAssemblerFactory | None = None,
    ) -> None:
        self.db = db
        self._asset_assembler_factory = _select_assembler_factory(
            instance=asset_assembler,
            factory=asset_assembler_factory,
            default_factory=_default_asset_assembler,
            domain="asset",
        )
        self._fx_assembler_factory = _select_assembler_factory(
            instance=fx_assembler,
            factory=fx_assembler_factory,
            default_factory=_default_fx_assembler,
            domain="fx",
        )
        self._portfolio_assembler_factory = _select_assembler_factory(
            instance=portfolio_assembler,
            factory=portfolio_assembler_factory,
            default_factory=_default_portfolio_assembler,
            domain="portfolio",
        )
        self._broker_assembler_factory = _select_assembler_factory(
            instance=broker_assembler,
            factory=broker_assembler_factory,
            default_factory=_default_broker_assembler,
            domain="broker",
        )

    @staticmethod
    def get_catalog() -> AiExportCatalogResponse:
        return get_catalog_response()

    @staticmethod
    def catalog() -> AiExportCatalogResponse:
        return get_catalog_response()

    async def prepare_request(self, user_id: int, request: AiExportSnapshotRequest) -> AiExportPreparedRequest:
        resolved_profile = resolve_profile(request.domain, request.task, request.detail_level)

        result = await self.db.execute(select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id))
        accessible_broker_ids = tuple(sorted(set(result.scalars().all())))

        if isinstance(request, AiExportBrokerSnapshotRequest):
            requested_broker_ids = (request.broker_id,)
        elif request.broker_ids is None:
            requested_broker_ids = accessible_broker_ids
        else:
            requested_broker_ids = tuple(sorted(request.broker_ids))

        denied_broker_ids = tuple(sorted(set(requested_broker_ids).difference(accessible_broker_ids)))
        if denied_broker_ids:
            raise AiExportBrokerAccessDeniedError(denied_broker_ids)

        return AiExportPreparedRequest(
            request=request,
            resolved_profile=resolved_profile,
            user_id=user_id,
            broker_scope=tuple(sorted(requested_broker_ids)),
        )

    async def build_snapshot(self, user_id: int, request: AiExportSnapshotRequest) -> AiExportSnapshotResponse:
        prepared = await self.prepare_request(user_id, request)
        if isinstance(request, AiExportAssetSnapshotRequest):
            return await self._asset_assembler_factory().assemble(prepared, self.db)
        if isinstance(request, AiExportFxSnapshotRequest):
            return await self._fx_assembler_factory().assemble(prepared, self.db)
        if isinstance(request, AiExportPortfolioSnapshotRequest):
            return await self._portfolio_assembler_factory().assemble(prepared, self.db)
        if isinstance(request, AiExportBrokerSnapshotRequest):
            return await self._broker_assembler_factory().assemble(prepared, self.db)
        raise TypeError(f"Unsupported AI Export request type: {type(request).__name__}")


__all__ = [
    "AiExportBrokerAccessDeniedError",
    "AiExportPreparedRequest",
    "AiExportSnapshotAssembler",
    "AiExportSnapshotAssemblerFactory",
    "AiExportSnapshotService",
    "AiExportSnapshotSourceError",
    "AiExportSnapshotSourceNotImplementedError",
]
