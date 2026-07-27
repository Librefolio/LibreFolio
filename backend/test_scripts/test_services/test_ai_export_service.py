"""Focused tests for AI Export request preparation."""

from dataclasses import FrozenInstanceError
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.ai_export import (
    AiExportAssetSnapshotRequest,
    AiExportAssetTask,
    AiExportBrokerSnapshotRequest,
    AiExportBrokerTask,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportFxSnapshotRequest,
    AiExportFxTask,
    AiExportPortfolioSnapshotRequest,
    AiExportPortfolioTask,
)
from backend.app.services.ai_export.assemblers import (
    AiExportAssetAssembler,
    AiExportBrokerAssembler,
    AiExportEntityNotFoundError,
    AiExportFxAssembler,
    AiExportPortfolioAssembler,
    AiExportSourceFailureError,
    AiExportTaskNotApplicableError,
)
from backend.app.services.ai_export.resolver import resolve_profile
from backend.app.services.ai_export.service import (
    AiExportBrokerAccessDeniedError,
    AiExportSnapshotService,
)

START = date(2026, 1, 1)
END = date(2026, 7, 26)


def _session_with_accessible_brokers(broker_ids: list[int]) -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars.return_value.all.return_value = broker_ids
    session.execute.return_value = result
    return session


def _portfolio_request(broker_ids: list[int] | None = None) -> AiExportPortfolioSnapshotRequest:
    return AiExportPortfolioSnapshotRequest(
        domain=AiExportDomain.PORTFOLIO,
        task=AiExportPortfolioTask.PAC_PLANNING,
        detail_level=AiExportDetailLevel.STANDARD,
        date_range={"start": START, "end": END},
        target_currency="EUR",
        broker_ids=broker_ids,
    )


def _broker_request(broker_id: int) -> AiExportBrokerSnapshotRequest:
    return AiExportBrokerSnapshotRequest(
        domain=AiExportDomain.BROKER,
        task=AiExportBrokerTask.BROKER_REVIEW,
        detail_level=AiExportDetailLevel.COMPACT,
        date_range={"start": START, "end": END},
        target_currency="EUR",
        broker_id=broker_id,
    )


def _asset_request(
    broker_ids: list[int] | None = None,
    *,
    task: AiExportAssetTask = AiExportAssetTask.ASSET_SNAPSHOT,
) -> AiExportAssetSnapshotRequest:
    return AiExportAssetSnapshotRequest(
        domain=AiExportDomain.ASSET,
        task=task,
        detail_level=AiExportDetailLevel.COMPACT,
        date_range={"start": START, "end": END},
        target_currency="EUR",
        asset_id=7,
        broker_ids=broker_ids,
    )


def _fx_request(
    broker_ids: list[int] | None = None,
    *,
    task: AiExportFxTask = AiExportFxTask.FX_TREND_REVIEW,
) -> AiExportFxSnapshotRequest:
    return AiExportFxSnapshotRequest(
        domain=AiExportDomain.FX,
        task=task,
        detail_level=AiExportDetailLevel.STANDARD,
        date_range={"start": START, "end": END},
        target_currency="EUR",
        base_currency="EUR",
        quote_currency="USD",
        broker_ids=broker_ids,
    )


def _assembler(*, result: object | None = None, error: Exception | None = None) -> MagicMock:
    assembler = MagicMock()
    assembler.assemble = AsyncMock(return_value=result, side_effect=error)
    return assembler


@pytest.mark.asyncio
async def test_prepare_request_uses_all_accessible_brokers_for_none_scope():
    session = _session_with_accessible_brokers([9, 2, 5])
    prepared = await AiExportSnapshotService(session).prepare_request(41, _portfolio_request())

    assert prepared.user_id == 41
    assert prepared.broker_scope == (2, 5, 9)
    assert prepared.broker_ids == (2, 5, 9)
    session.execute.assert_awaited_once()
    assert "broker_user_access.user_id" in str(session.execute.await_args.args[0])


@pytest.mark.asyncio
async def test_prepare_request_allows_empty_accessible_scope():
    session = _session_with_accessible_brokers([])
    prepared = await AiExportSnapshotService(session).prepare_request(41, _portfolio_request())

    assert prepared.request.broker_ids is None
    assert prepared.broker_scope == ()
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_prepare_request_preserves_exact_explicit_scope_as_sorted_tuple():
    session = _session_with_accessible_brokers([8, 1, 3, 5])
    prepared = await AiExportSnapshotService(session).prepare_request(41, _portfolio_request([5, 1, 3]))

    assert prepared.broker_scope == (1, 3, 5)
    assert prepared.request.broker_ids == [1, 3, 5]


@pytest.mark.asyncio
async def test_prepare_request_rejects_every_inaccessible_broker_without_filtering():
    session = _session_with_accessible_brokers([1, 5])

    with pytest.raises(AiExportBrokerAccessDeniedError) as caught:
        await AiExportSnapshotService(session).prepare_request(41, _portfolio_request([5, 4, 1, 3]))

    assert caught.value.denied_broker_ids == (3, 4)
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_prepare_request_checks_broker_domain_scope():
    allowed_session = _session_with_accessible_brokers([7, 3])
    prepared = await AiExportSnapshotService(allowed_session).prepare_request(41, _broker_request(7))
    assert prepared.broker_scope == (7,)

    denied_session = _session_with_accessible_brokers([3])
    with pytest.raises(AiExportBrokerAccessDeniedError) as caught:
        await AiExportSnapshotService(denied_session).prepare_request(41, _broker_request(7))
    assert caught.value.denied_broker_ids == (7,)


@pytest.mark.asyncio
async def test_prepare_request_resolves_exact_profile_into_immutable_context():
    session = _session_with_accessible_brokers([2])
    request = _portfolio_request([2])
    prepared = await AiExportSnapshotService(session).prepare_request(41, request)

    assert prepared.resolved_profile is resolve_profile(request.domain, request.task, request.detail_level)
    assert prepared.resolved_profile.profile_id == "portfolio.pac_planning.standard"
    with pytest.raises(FrozenInstanceError):
        prepared.user_id = 99


def test_static_catalog_has_54_validated_entries_without_db_access():
    catalog = AiExportSnapshotService.get_catalog()

    assert len(catalog.entries) == 54
    assert all("prompt" not in key and "label" not in key for entry in catalog.entries for key in entry.model_dump())


def test_default_factories_create_all_four_real_assemblers():
    service = AiExportSnapshotService(_session_with_accessible_brokers([]))

    assert isinstance(service._asset_assembler_factory(), AiExportAssetAssembler)
    assert isinstance(service._fx_assembler_factory(), AiExportFxAssembler)
    assert isinstance(service._portfolio_assembler_factory(), AiExportPortfolioAssembler)
    assert isinstance(service._broker_assembler_factory(), AiExportBrokerAssembler)


@pytest.mark.asyncio
@pytest.mark.parametrize("use_factory", [False, True], ids=["instance", "factory"])
@pytest.mark.parametrize(
    ("domain", "snapshot_request", "expected_scope"),
    [
        ("asset", _asset_request([5, 1]), (1, 5)),
        ("fx", _fx_request([3]), (3,)),
        ("portfolio", _portfolio_request([5, 2]), (2, 5)),
        ("broker", _broker_request(2), (2,)),
    ],
)
async def test_build_snapshot_dispatches_every_valid_domain_and_preserves_result_and_scope(
    use_factory: bool,
    domain: str,
    snapshot_request: AiExportAssetSnapshotRequest | AiExportFxSnapshotRequest | AiExportPortfolioSnapshotRequest | AiExportBrokerSnapshotRequest,
    expected_scope: tuple[int, ...],
):
    session = _session_with_accessible_brokers([9, 5, 3, 2, 1])
    expected = object()
    assembler = _assembler(result=expected)
    factory = MagicMock(return_value=assembler)
    dependency = f"{domain}_assembler_factory" if use_factory else f"{domain}_assembler"
    service = AiExportSnapshotService(session, **{dependency: factory if use_factory else assembler})

    result = await service.build_snapshot(41, snapshot_request)

    assert result is expected
    if use_factory:
        factory.assert_called_once_with()
    else:
        factory.assert_not_called()
    assembler.assemble.assert_awaited_once()
    prepared, passed_session = assembler.assemble.await_args.args
    assert prepared.request is snapshot_request
    assert prepared.user_id == 41
    assert prepared.broker_scope == expected_scope
    assert passed_session is session


@pytest.mark.parametrize("domain", ["asset", "fx", "portfolio", "broker"])
def test_assembler_instance_and_factory_are_mutually_exclusive(domain: str):
    assembler = _assembler()

    with pytest.raises(ValueError, match=rf"{domain} assembler instance and factory are mutually exclusive"):
        AiExportSnapshotService(
            _session_with_accessible_brokers([]),
            **{
                f"{domain}_assembler": assembler,
                f"{domain}_assembler_factory": MagicMock(return_value=assembler),
            },
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("domain", "snapshot_request"),
    [
        ("asset", _asset_request([2])),
        ("fx", _fx_request([2])),
        ("portfolio", _portfolio_request([2])),
        ("broker", _broker_request(2)),
    ],
)
@pytest.mark.parametrize(
    "error_factory",
    [
        pytest.param(
            lambda: AiExportEntityNotFoundError("entity", 7),
            id="entity-not-found",
        ),
        pytest.param(
            lambda: AiExportTaskNotApplicableError(
                "positive_open_quantity_in_scope",
                "no_positive_open_position",
            ),
            id="task-not-applicable",
        ),
        pytest.param(
            lambda: AiExportSourceFailureError(
                "snapshot_source",
                "load",
                retryable=True,
            ),
            id="source-failure",
        ),
    ],
)
async def test_build_snapshot_propagates_typed_assembler_errors_for_every_domain(
    domain: str,
    snapshot_request: AiExportAssetSnapshotRequest | AiExportFxSnapshotRequest | AiExportPortfolioSnapshotRequest | AiExportBrokerSnapshotRequest,
    error_factory,
):
    session = _session_with_accessible_brokers([2])
    error = error_factory()
    service = AiExportSnapshotService(
        session,
        **{f"{domain}_assembler": _assembler(error=error)},
    )

    with pytest.raises(type(error)) as caught:
        await service.build_snapshot(41, snapshot_request)

    assert caught.value is error
