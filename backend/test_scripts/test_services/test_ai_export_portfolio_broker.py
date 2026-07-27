"""Focused Portfolio and Broker AI Export assembler tests."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.schemas.ai_export import (
    AiExportBrokerSnapshotRequest,
    AiExportBrokerSnapshotResponse,
    AiExportBrokerTask,
    AiExportDerivedState,
    AiExportDetailLevel,
    AiExportDomain,
    AiExportEvent,
    AiExportEventDirection,
    AiExportPortfolioSnapshotRequest,
    AiExportPortfolioSnapshotResponse,
    AiExportPortfolioTask,
    AiExportSignalSemantic,
    AiExportSignalStatus,
    AiExportTechnicalComponent,
    AiExportTechnicalSignal,
    AiExportTechnicalTarget,
)
from backend.app.schemas.common import Currency, DateRangeModel, OpenDateRangeModel
from backend.app.schemas.portfolio import LotAnalysisType
from backend.app.schemas.prices import FAPricePoint
from backend.app.services.ai_export.assemblers import (
    AiExportBrokerAssembler,
    AiExportPortfolioAssembler,
    AiExportSourceFailureError,
    AiExportTaskNotApplicableError,
)
from backend.app.services.ai_export.coverage import TargetCoverage
from backend.app.services.ai_export.resolver import resolve_profile
from backend.app.services.ai_export.service import AiExportPreparedRequest
from backend.app.services.ai_export.technical import TechnicalTargetResult

START = date(2026, 4, 1)
END = date(2026, 7, 1)
FIXED_NOW = datetime(2026, 7, 2, 12, 30, tzinfo=UTC)


def _fixed_clock() -> datetime:
    return FIXED_NOW


def _asset(
    asset_id: int,
    *,
    currency: str = "USD",
    description: str | None = None,
    user_url: str | None = "https://private.example/account/123",
) -> SimpleNamespace:
    classification = json.dumps({"short_description": description}) if description is not None else None
    return SimpleNamespace(
        id=asset_id,
        display_name=f"Asset {asset_id}",
        currency=currency,
        asset_type="ETF" if asset_id % 2 else "STOCK",
        identifier_ticker=f"A{asset_id}",
        classification_params=classification,
        user_url=user_url,
    )


def _broker(
    broker_id: int,
    *,
    description: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=broker_id,
        name=f"Broker {broker_id}",
        description=description,
        portal_url=f"https://private.example/broker/{broker_id}",
    )


def _holding(
    asset_id: int,
    broker_id: int,
    *,
    nav_weight: str | None = "20",
    current_value: str | None = "200",
    quantity: str = "2",
    source: str = "MARKET_PRICE",
    trading_price: str | None = "100",
) -> SimpleNamespace:
    valued = current_value is not None
    return SimpleNamespace(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_ticker=f"A{asset_id}",
        asset_type="ETF" if asset_id % 2 else "STOCK",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        quantity=Decimal(quantity),
        wac_per_unit=Decimal("80"),
        current_price=Decimal(trading_price) if valued and trading_price is not None else None,
        current_value=Decimal(current_value) if valued else None,
        valuation_source=source,
        valuation_effective_unit_price=Decimal("110") if valued else None,
        valuation_effective_currency="USD" if valued else None,
        valuation_reference_date=END - timedelta(days=1) if valued else None,
        valuation_reference_unit_price=Decimal("109") if valued else None,
        valuation_reference_currency="USD" if valued else None,
        valuation_split_adjusted=False,
        missing_fx_pair=None,
        gain_loss=Decimal("40") if valued else None,
        gain_loss_percent=Decimal("0.25") if valued else None,
        allocation_percent=Decimal(nav_weight) if nav_weight is not None else None,
        nav_weight_percent=Decimal(nav_weight) if nav_weight is not None else None,
    )


def _contribution(
    asset_id: int,
    broker_id: int,
    *,
    pnl: str = "12",
    income: str = "2",
    fees_taxes: str = "1",
    fully_sold: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_ticker=f"A{asset_id}",
        asset_type="ETF" if asset_id % 2 else "STOCK",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        period_unrealized_delta=Decimal("4"),
        period_realized_gain_loss=Decimal("5"),
        period_income=Decimal(income),
        period_fees_taxes=Decimal(fees_taxes),
        period_pnl=Decimal(pnl),
        period_pnl_percent=Decimal(pnl) / Decimal("100"),
        start_value=Decimal("100"),
        end_value=Decimal("112"),
        is_fully_sold=fully_sold,
    )


def _unallocated(
    broker_id: int,
    *,
    income: str | None = "7",
    fees_taxes: str | None = "2",
) -> SimpleNamespace:
    return SimpleNamespace(
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        unallocated_income=Decimal(income) if income is not None else None,
        unallocated_fees_taxes=Decimal(fees_taxes) if fees_taxes is not None else None,
    )


def _other_effect(
    description: str,
    *,
    category: str,
    amount: str,
    broker_id: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        description=description,
        category=category,
        period_pnl=Decimal(amount),
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}" if broker_id is not None else None,
    )


def _allocation(name: str, value: str, amount: str) -> SimpleNamespace:
    return SimpleNamespace(name=name, value=Decimal(value), amount=Decimal(amount))


def _history_point(
    point_date: date,
    *,
    cash: str,
    cash_capital: str,
    cash_returns: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        date=point_date,
        cash_value=Currency(code="EUR", amount=Decimal(cash)),
        cash_from_contributed_capital=Currency(code="EUR", amount=Decimal(cash_capital)),
        cash_from_generated_returns=Currency(code="EUR", amount=Decimal(cash_returns)),
    )


def _report(
    *,
    holdings: list[Any],
    contributions: list[Any],
    brokers: list[Any],
    nav: str = "1000",
    market: str = "800",
    cash: str = "200",
    history: list[Any] | None = None,
    allocation_by_type: list[Any] | None = None,
    allocation_by_sector: list[Any] | None = None,
    allocation_by_geography: list[Any] | None = None,
    broker_cash_balances: dict[int, list[Currency]] | None = None,
    summary_cash_balances: list[Currency] | None = None,
    unallocated: list[Any] | None = None,
    other_effects: list[Any] | None = None,
    total_invested: str = "700",
    net_deposited_capital: str = "650",
    total_gain_loss: str = "300",
) -> SimpleNamespace:
    resolved_broker_cash_balances = (
        {
            broker.id: [
                Currency(
                    code="EUR",
                    amount=Decimal(cash) / Decimal(len(brokers)),
                )
            ]
            for broker in brokers
        }
        if broker_cash_balances is None
        else broker_cash_balances
    )
    broker_rows = [
        SimpleNamespace(
            broker_id=broker.id,
            broker_name=broker.name,
            net_worth=Currency(code="EUR", amount=Decimal(nav) / Decimal(len(brokers))),
            cash_total=Currency(code="EUR", amount=Decimal(cash) / Decimal(len(brokers))),
            cash_balances=list(resolved_broker_cash_balances.get(broker.id, [])),
        )
        for broker in brokers
    ]
    if summary_cash_balances is None:
        aggregate_cash: dict[str, Decimal] = {}
        for balances in resolved_broker_cash_balances.values():
            for balance in balances:
                aggregate_cash[balance.code] = aggregate_cash.get(balance.code, Decimal("0")) + balance.amount
        summary_cash_balances = [Currency(code=code, amount=amount) for code, amount in sorted(aggregate_cash.items())]
    summary = SimpleNamespace(
        net_worth=Currency(code="EUR", amount=Decimal(nav)),
        market_value=Currency(code="EUR", amount=Decimal(market)),
        cash_total=Currency(code="EUR", amount=Decimal(cash)),
        cash_balances=list(summary_cash_balances),
        book_value=Currency(code="EUR", amount=Decimal("750")),
        total_invested=Currency(code="EUR", amount=Decimal(total_invested)),
        net_deposited_capital=Currency(code="EUR", amount=Decimal(net_deposited_capital)),
        period_nav_start=Currency(code="EUR", amount=Decimal("900")),
        period_net_flows=Currency(code="EUR", amount=Decimal("25")),
        total_gain_loss=Currency(code="EUR", amount=Decimal(total_gain_loss)),
        period_pnl=Currency(code="EUR", amount=Decimal("75")),
        period_realized_gain_loss=Currency(code="EUR", amount=Decimal("20")),
        unrealized_gain_loss=Currency(code="EUR", amount=Decimal("50")),
        period_income=Currency(code="EUR", amount=Decimal("10")),
        period_fees_taxes=Currency(code="EUR", amount=Decimal("3")),
        twrr_percent=Decimal("0.075"),
        mwrr_annualized_percent=Decimal("0.08"),
        simple_roi_percent=Decimal("0.06"),
        allocation_by_type=list(allocation_by_type or [_allocation("ETF", "80", "800"), _allocation("Liquidity", "20", "200")]),
        allocation_by_sector=list(allocation_by_sector or [_allocation("Technology", "80", "800"), _allocation("Liquidity", "20", "200")]),
        allocation_by_geography=list(allocation_by_geography or [_allocation("USA", "100", "800")]),
        holdings=list(holdings),
        by_broker=broker_rows,
    )
    resolved_history = (
        [
            _history_point(START, cash="100", cash_capital="70", cash_returns="30"),
            _history_point(END, cash="211", cash_capital="123", cash_returns="88"),
        ]
        if history is None
        else list(history)
    )
    return SimpleNamespace(
        summary=summary,
        history=resolved_history,
        positions_contribution=SimpleNamespace(
            positions=list(contributions),
            unallocated=list(unallocated or []),
            other_effects=list(other_effects or []),
        ),
    )


class _PortfolioService:
    def __init__(self, report: Any) -> None:
        self.report = report
        self.calls: list[tuple[int, Any]] = []

    async def get_report(self, user_id: int, query: Any) -> Any:
        self.calls.append((user_id, query))
        return self.report


class _MetadataLoader:
    def __init__(self, entities: list[Any], *, reverse: bool = False) -> None:
        self.entities = list(reversed(entities)) if reverse else list(entities)
        self.calls: list[tuple[int, ...]] = []

    async def __call__(self, session: Any, entity_ids: list[int]) -> list[Any]:
        self.calls.append(tuple(entity_ids))
        wanted = set(entity_ids)
        return [entity for entity in self.entities if entity.id in wanted]


class _PriceLoader:
    def __init__(self, present_asset_ids: set[int] | None = None) -> None:
        self.present_asset_ids = present_asset_ids
        self.calls: list[list[Any]] = []

    async def __call__(self, requests: list[Any], session: Any) -> list[Any]:
        self.calls.append(requests)
        present = self.present_asset_ids if self.present_asset_ids is not None else {request.asset_id for request in requests}
        return [
            SimpleNamespace(
                asset_id=request.asset_id,
                prices=[
                    FAPricePoint(
                        date=END,
                        open=Decimal("100"),
                        high=Decimal("101"),
                        low=Decimal("99"),
                        close=Decimal("100"),
                        volume=Decimal("1000"),
                        currency="EUR",
                    )
                ],
                events=[],
            )
            for request in requests
            if request.asset_id in present
        ]


class _CashConverter:
    def __init__(self, rates: dict[str, Decimal] | None = None, *, fail: bool = False) -> None:
        self.rates = rates or {}
        self.fail = fail
        self.calls: list[tuple[Any, list[Any], bool]] = []

    async def __call__(self, session: Any, conversions: list[Any], *, raise_on_error: bool) -> tuple[list[Any], list[str]]:
        self.calls.append((session, conversions, raise_on_error))
        if self.fail:
            return [None for _ in conversions], ["conversion unavailable"]
        return (
            [
                (
                    Currency(
                        code=target_currency,
                        amount=source.amount * self.rates[source.code],
                    ),
                    conversion_date,
                    False,
                )
                for source, target_currency, conversion_date in conversions
            ],
            [],
        )


class _TechnicalExecutor:
    def __init__(
        self,
        *,
        event_dates: dict[int, date] | None = None,
        emit_targets: bool = True,
    ) -> None:
        self.event_dates = event_dates or {}
        self.emit_targets = emit_targets
        self.calls: list[tuple[int, int]] = []

    async def __call__(
        self,
        prepared: Any,
        price_points: list[Any],
        event_points: list[Any],
        *,
        events_loaded: bool,
    ) -> TechnicalTargetResult:
        asset_id = prepared.target.asset_id
        self.calls.append((asset_id, len(price_points)))
        eligible = bool(price_points)
        analyzed = eligible
        technical_target = None
        states = ()
        events = ()
        semantics = ()
        if analyzed:
            states = (
                AiExportDerivedState(
                    target=prepared.target,
                    code="price_vs_ema200",
                    state="above",
                    as_of=END,
                    signal_instance_id="ema_200",
                    signal_code="EMA",
                    value=Decimal("1"),
                ),
            )
            if self.emit_targets:
                technical_target = AiExportTechnicalTarget(
                    target=prepared.target,
                    signals=[
                        AiExportTechnicalSignal(
                            instance_id="ema_200",
                            signal_code="EMA",
                            implementation_version="test",
                            normalized_params={"period": 200},
                            status=AiExportSignalStatus.OK,
                            components=[
                                AiExportTechnicalComponent(
                                    component_code="ema",
                                    semantic_id="ema",
                                    unit="price",
                                    latest={"date": END, "value": "99"},
                                )
                            ],
                        )
                    ],
                )
            event_date = self.event_dates.get(asset_id)
            if event_date is not None:
                events = (
                    AiExportEvent(
                        target=prepared.target,
                        date=event_date,
                        code="price_crossed_above_ema200",
                        signal_instance_id="ema_200",
                        signal_code="EMA",
                        direction=AiExportEventDirection.UP,
                        values={"price": Decimal("100"), "ema": Decimal("99")},
                    ),
                )
            semantics = (
                AiExportSignalSemantic(
                    semantic_id="ema",
                    description="Exponential moving average.",
                ),
            )
        return TechnicalTargetResult(
            resolved_profile=prepared.resolved_profile,
            target=prepared.target,
            technical_target=technical_target,
            states=states,
            events=events,
            signal_semantics=semantics,
            target_coverage=TargetCoverage(
                target_key=f"asset:{asset_id}",
                eligible=eligible,
                analyzed=analyzed,
                nav_weight_pct=prepared.nav_weight_pct,
                derived_states=({"price_vs_ema200": "above"} if analyzed else {}),
            ),
            calculation_range=prepared.calculation_range,
            calculation_warmup_start=prepared.calculation_warmup_start,
            event_limit=prepared.event_limit,
        )


def _prepared(
    task: AiExportPortfolioTask,
    detail: AiExportDetailLevel,
    *,
    broker_ids: tuple[int, ...] = (1,),
) -> AiExportPreparedRequest:
    request = AiExportPortfolioSnapshotRequest(
        domain=AiExportDomain.PORTFOLIO,
        task=task,
        detail_level=detail,
        date_range=DateRangeModel(start=START, end=END),
        target_currency="EUR",
        broker_ids=list(broker_ids),
    )
    return AiExportPreparedRequest(
        request=request,
        resolved_profile=resolve_profile(AiExportDomain.PORTFOLIO, task, detail),
        user_id=42,
        broker_scope=broker_ids,
    )


def _assembler(
    report: Any,
    *,
    assets: list[Any],
    brokers: list[Any],
    price_loader: _PriceLoader | None = None,
    technical_executor: _TechnicalExecutor | None = None,
    technical_preparer: Any = None,
    convert_bulk_fn: Any = None,
    reverse_metadata: bool = False,
) -> tuple[AiExportPortfolioAssembler, _PortfolioService, _PriceLoader]:
    service = _PortfolioService(report)
    prices = price_loader or _PriceLoader()
    kwargs: dict[str, Any] = {}
    if technical_preparer is not None:
        kwargs["technical_preparer"] = technical_preparer
    if convert_bulk_fn is not None:
        kwargs["convert_bulk_fn"] = convert_bulk_fn
    assembler = AiExportPortfolioAssembler(
        portfolio_service=service,
        price_bulk_loader=prices,
        asset_metadata_loader=_MetadataLoader(assets, reverse=reverse_metadata),
        broker_metadata_loader=_MetadataLoader(brokers, reverse=reverse_metadata),
        technical_executor=technical_executor or _TechnicalExecutor(),
        clock=_fixed_clock,
        **kwargs,
    )
    return assembler, service, prices


PORTFOLIO_TASKS = tuple(AiExportPortfolioTask)
DETAIL_LEVELS = tuple(AiExportDetailLevel)


@pytest.mark.asyncio
@pytest.mark.parametrize("task", PORTFOLIO_TASKS)
@pytest.mark.parametrize("detail", DETAIL_LEVELS)
async def test_all_18_portfolio_profiles_are_schema_and_meta_valid(task: AiExportPortfolioTask, detail: AiExportDetailLevel):
    assets = [_asset(1), _asset(2, currency="EUR")]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="30", current_value="300"), _holding(2, 1, nav_weight="50", current_value="500")],
        contributions=[_contribution(1, 1, pnl="15"), _contribution(2, 1, pnl="-5")],
        unallocated=[_unallocated(1)],
        other_effects=[_other_effect("Portfolio adjustment", category="Other", amount="-3")],
        brokers=brokers,
    )
    assembler, _service, _prices = _assembler(report, assets=assets, brokers=brokers)

    response = await assembler.assemble(_prepared(task, detail), None)
    validated = AiExportPortfolioSnapshotResponse.model_validate(response.model_dump())

    assert validated.meta.profile_id == f"portfolio.{task.value}.{detail.value}"
    assert validated.meta.generated_at == FIXED_NOW
    assert validated.meta.target_currency == "EUR"
    assert (validated.facts.selection is not None) is (detail == AiExportDetailLevel.COMPACT)
    assert validated.export_stats.canonical_json.positions == len(validated.facts.positions)
    contribution_context_allowed = task != AiExportPortfolioTask.TECHNICAL_BREADTH
    assert bool(validated.facts.contributions) is contribution_context_allowed
    assert bool(validated.facts.unallocated_contributions) is contribution_context_allowed
    assert bool(validated.facts.other_period_effects) is contribution_context_allowed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("allowed_section", "expected_counts"),
    (
        ("facts.contributions", (1, 0, 0)),
        ("facts.unallocated_contributions", (0, 1, 0)),
        ("facts.other_period_effects", (0, 0, 1)),
    ),
)
async def test_portfolio_contribution_categories_are_gated_independently(allowed_section: str, expected_counts: tuple[int, int, int]):
    assets = [_asset(1)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="80", current_value="800")],
        contributions=[_contribution(1, 1)],
        unallocated=[_unallocated(1)],
        other_effects=[_other_effect("Independent sidecar", category="Other", amount="-3")],
        brokers=brokers,
    )
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )
    prepared = _prepared(AiExportPortfolioTask.REBALANCING, AiExportDetailLevel.STANDARD)
    contribution_sections = {
        "facts.contributions",
        "facts.unallocated_contributions",
        "facts.other_period_effects",
    }
    task_spec = replace(
        prepared.resolved_profile.task_spec,
        required_sections=tuple(section for section in prepared.resolved_profile.required_sections if section not in contribution_sections),
        optional_sections=tuple(section for section in prepared.resolved_profile.optional_sections if section not in contribution_sections) + (allowed_section,),
    )
    prepared = replace(
        prepared,
        resolved_profile=replace(prepared.resolved_profile, task_spec=task_spec),
    )

    response = await assembler.assemble(prepared, None)

    assert (
        len(response.facts.contributions),
        len(response.facts.unallocated_contributions),
        len(response.facts.other_period_effects),
    ) == expected_counts


@pytest.mark.asyncio
async def test_summary_capital_fields_reconcile_lifetime_and_selected_period_values():
    assets = [_asset(1)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="80", current_value="800")],
        contributions=[_contribution(1, 1)],
        brokers=brokers,
        total_invested="700",
        net_deposited_capital="650",
        total_gain_loss="300",
    )
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION, AiExportDetailLevel.STANDARD), None)
    summary = response.facts.summary

    assert summary.net_contributed_capital == Currency(code="EUR", amount=Decimal("700"))
    assert summary.net_deposits == Currency(code="EUR", amount=Decimal("25"))
    assert summary.net_contributed_capital.amount + summary.lifetime_pnl_amount.amount == summary.nav.amount
    assert summary.start_nav.amount + summary.net_deposits.amount + summary.period_pnl_amount.amount == summary.nav.amount
    semantics = {item.metric_code: item for item in response.semantics.metric_semantics}
    assert semantics["portfolio.net_contributed_capital"].method == "portfolio_service_total_invested_lifetime"
    assert semantics["portfolio.net_contributed_capital"].period is None
    assert semantics["portfolio.net_deposits"].method == "portfolio_service_period_net_flows"
    assert semantics["portfolio.net_deposits"].period == DateRangeModel(start=START, end=END)


@pytest.mark.asyncio
async def test_single_report_and_price_bulk_call_use_required_scope_and_flags():
    assets = [_asset(1), _asset(2)]
    brokers = [_broker(1), _broker(2)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="40", current_value="400"), _holding(2, 2, nav_weight="40", current_value="400")],
        contributions=[_contribution(1, 1), _contribution(2, 2)],
        brokers=brokers,
    )
    assembler, service, prices = _assembler(report, assets=assets, brokers=brokers)

    await assembler.assemble(
        _prepared(AiExportPortfolioTask.PAC_PLANNING, AiExportDetailLevel.STANDARD, broker_ids=(1, 2)),
        None,
    )

    assert len(service.calls) == 1
    _user_id, query = service.calls[0]
    assert query.broker_ids == [1, 2]
    assert query.date_range.start == START
    assert query.date_range.end == END
    assert query.target_currency == "EUR"
    assert query.include_summary is True
    assert query.include_history is True
    assert query.include_breakdown is True
    assert query.include_positions_contribution is True
    assert query.include_allocation_history is False
    assert len(prices.calls) == 1
    assert {item.asset_id for item in prices.calls[0]} == {1, 2}
    assert all(item.target_currency == "EUR" and item.signals == [] and item.annotation_requests == [] for item in prices.calls[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("detail", [AiExportDetailLevel.STANDARD, AiExportDetailLevel.FULL])
async def test_standard_and_full_keep_all_positions_when_one_price_result_is_missing(detail: AiExportDetailLevel):
    assets = [_asset(1), _asset(2)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[
            _holding(1, 1, nav_weight="50", current_value="500"),
            _holding(2, 1, nav_weight=None, current_value=None, source="MISSING", trading_price=None),
        ],
        contributions=[_contribution(1, 1), _contribution(2, 1)],
        brokers=brokers,
    )
    executor = _TechnicalExecutor()
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        price_loader=_PriceLoader({1}),
        technical_executor=executor,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PAC_PLANNING, detail), None)

    assert [(position.asset_id, position.broker_id) for position in response.facts.positions] == [(1, 1), (2, 1)]
    assert response.facts.positions[1].valuation_source == "missing"
    assert response.facts.positions[1].cost_basis is not None
    assert response.coverage.technical is not None
    assert response.coverage.technical.portfolio_assets == 2
    assert response.coverage.technical.technically_eligible_assets == 1
    assert executor.calls == [(1, 1), (2, 0)]


@pytest.mark.asyncio
async def test_contribution_merge_requires_exact_asset_and_broker_and_maps_complete_rows():
    assets = [_asset(1), _asset(2)]
    brokers = [_broker(1), _broker(2)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="30", current_value="300"), _holding(1, 2, nav_weight="30", current_value="300")],
        contributions=[_contribution(1, 1, pnl="17"), _contribution(2, 2, pnl="-9", fully_sold=True)],
        brokers=brokers,
    )
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION, AiExportDetailLevel.STANDARD, broker_ids=(1, 2)), None)
    positions = {(item.asset_id, item.broker_id): item for item in response.facts.positions}

    assert positions[(1, 1)].period_pnl_amount == Currency(code="EUR", amount=Decimal("17"))
    assert positions[(1, 1)].period_unrealized_delta_amount == Currency(code="EUR", amount=Decimal("4"))
    assert positions[(1, 2)].period_pnl_amount is None
    assert positions[(1, 2)].period_income_amount is None
    assert [(item.asset_id, item.broker_id) for item in response.facts.contributions] == [(1, 1), (2, 2)]
    assert response.facts.contributions[1].is_fully_sold is True
    assert response.facts.contributions[1].period_realized_pnl_amount == Currency(code="EUR", amount=Decimal("5"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("unallocated", "other_effects"),
    (
        ([_unallocated(2, income="7", fees_taxes=None), _unallocated(1, income=None, fees_taxes="2")], []),
        ([], [_other_effect("Residual reconciliation", category="Other", amount="-3")]),
    ),
)
async def test_non_position_contributions_make_attribution_applicable_and_survive_compact_selection(
    unallocated: list[Any],
    other_effects: list[Any],
):
    brokers = [_broker(1), _broker(2)]
    report = _report(
        holdings=[],
        contributions=[],
        brokers=brokers,
        nav="0",
        market="0",
        cash="0",
        history=[],
        total_invested="0",
        total_gain_loss="0",
        unallocated=unallocated,
        other_effects=other_effects,
    )
    report.summary.book_value = None
    assembler, _service, _prices = _assembler(
        report,
        assets=[],
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(
        _prepared(AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION, AiExportDetailLevel.COMPACT, broker_ids=(1, 2)),
        None,
    )

    assert response.facts.positions == []
    assert response.facts.contributions == []
    assert [item.broker_id for item in response.facts.unallocated_contributions] == sorted(item.broker_id for item in response.facts.unallocated_contributions)
    assert all(amount is None or amount.code == "EUR" for item in response.facts.unallocated_contributions for amount in (item.unallocated_income_amount, item.unallocated_fees_taxes_amount))
    assert [item.description for item in response.facts.other_period_effects] == sorted(item.description for item in response.facts.other_period_effects)
    assert all(item.period_pnl_amount.code == "EUR" for item in response.facts.other_period_effects)
    assert len(response.facts.unallocated_contributions) == len(unallocated)
    assert len(response.facts.other_period_effects) == len(other_effects)


@pytest.mark.asyncio
async def test_zero_only_non_position_rows_do_not_make_attribution_applicable():
    brokers = [_broker(1)]
    report = _report(
        holdings=[],
        contributions=[],
        brokers=brokers,
        nav="0",
        market="0",
        cash="0",
        history=[],
        total_invested="0",
        total_gain_loss="0",
        unallocated=[_unallocated(1, income="0", fees_taxes="0")],
        other_effects=[_other_effect("Zero residual", category="Other", amount="0")],
    )
    report.summary.book_value = None
    assembler, _service, _prices = _assembler(report, assets=[], brokers=brokers)

    with pytest.raises(AiExportTaskNotApplicableError):
        await assembler.assemble(_prepared(AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION, AiExportDetailLevel.COMPACT), None)


@pytest.mark.asyncio
async def test_six_allocations_are_complete_and_currency_is_trading_or_valuation_not_lookthrough():
    assets = [_asset(1, currency="USD"), _asset(2, currency="EUR")]
    brokers = [_broker(1), _broker(2)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="60", current_value="600"), _holding(2, 2, nav_weight="20", current_value="200")],
        contributions=[_contribution(1, 1), _contribution(2, 2)],
        brokers=brokers,
        allocation_by_type=[_allocation("ETF", "60", "600"), _allocation("STOCK", "20", "200"), _allocation("Liquidity", "20", "200")],
        allocation_by_sector=[_allocation("Technology", "80", "800"), _allocation("Liquidity", "20", "200")],
        allocation_by_geography=[_allocation("USA", "75", "600"), _allocation("Italy", "25", "200")],
    )
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.REBALANCING, AiExportDetailLevel.STANDARD, broker_ids=(1, 2)), None)
    allocations = response.facts.allocations

    assert len(allocations.by_asset) == 3
    assert len(allocations.by_asset_type) == 3
    assert len(allocations.by_sector) == 2
    assert len(allocations.by_geography) == 2
    assert {item.key for item in allocations.by_currency} == {"EUR", "USD"}
    assert {item.key for item in allocations.by_broker} == {"1", "2"}
    currency = {item.key: item for item in allocations.by_currency}
    assert currency["USD"].weight_pct == Decimal("60.00")
    assert currency["EUR"].weight_pct == Decimal("40.00")
    assert response.semantics.currency_semantics is not None
    assert response.semantics.currency_semantics.underlying_currency_exposure_available is False
    assert response.semantics.currency_semantics.allocation_semantics == "position_or_valuation_currency_not_lookthrough_exposure"


@pytest.mark.asyncio
async def test_portfolio_preserves_signed_leveraged_weights_and_uses_gross_technical_coverage():
    assets = [_asset(1), _asset(2)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[
            _holding(1, 1, nav_weight="-20", current_value="-20", quantity="-1"),
            _holding(2, 1, nav_weight="120", current_value="120"),
        ],
        contributions=[_contribution(1, 1), _contribution(2, 1)],
        brokers=brokers,
        nav="100",
        market="100",
        cash="0",
        allocation_by_type=[
            _allocation("Short", "-20", "-20"),
            _allocation("Leveraged", "120", "120"),
        ],
    )
    assembler, _service, _prices = _assembler(report, assets=assets, brokers=brokers)

    response = await assembler.assemble(
        _prepared(AiExportPortfolioTask.REBALANCING, AiExportDetailLevel.STANDARD),
        None,
    )
    positions = {position.asset_id: position for position in response.facts.positions}
    by_asset = {entry.key: entry for entry in response.facts.allocations.by_asset}
    by_type = {entry.key: entry for entry in response.facts.allocations.by_asset_type}

    assert positions[1].weight_pct == Decimal("-20.00")
    assert positions[2].weight_pct == Decimal("120.00")
    assert by_asset["1"].weight_pct == Decimal("-20.00")
    assert by_asset["2"].weight_pct == Decimal("120.00")
    assert by_type["Short"].weight_pct == Decimal("-20.00")
    assert by_type["Leveraged"].weight_pct == Decimal("120.00")
    assert response.coverage.technical.analyzed_nav_weight_pct == Decimal("140.00")
    assert response.coverage.weighted_breadth.eligible_nav_weight_pct == Decimal("140.00")


@pytest.mark.asyncio
async def test_currency_allocation_preserves_native_usd_cash_and_converts_once_at_snapshot():
    assets = [_asset(1, currency="EUR")]
    brokers = [_broker(1)]
    usd_cash = Currency(code="USD", amount=Decimal("100"))
    report = _report(
        holdings=[_holding(1, 1, nav_weight="89.8876404494", current_value="800")],
        contributions=[_contribution(1, 1)],
        brokers=brokers,
        nav="890",
        market="800",
        cash="90",
        broker_cash_balances={1: [usd_cash]},
        summary_cash_balances=[usd_cash],
        total_invested="590",
        total_gain_loss="300",
    )
    converter = _CashConverter({"USD": Decimal("0.9")})
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        convert_bulk_fn=converter,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.REBALANCING, AiExportDetailLevel.STANDARD), None)

    assert len(converter.calls) == 1
    _session, conversions, raise_on_error = converter.calls[0]
    assert raise_on_error is False
    assert conversions == [(Currency(code="USD", amount=Decimal("100")), "EUR", END)]
    by_currency = {item.key: item for item in response.facts.allocations.by_currency}
    assert by_currency["EUR"].amount == Currency(code="EUR", amount=Decimal("800"))
    assert by_currency["EUR"].weight_pct == Decimal("89.89")
    assert by_currency["USD"].amount == Currency(code="EUR", amount=Decimal("90"))
    assert by_currency["USD"].weight_pct == Decimal("10.11")
    semantics = {item.metric_code: item for item in response.semantics.metric_semantics}
    assert semantics["portfolio.allocation_by_currency_pct"].denominator == "trading_currency_positions_plus_native_cash_snapshot_value"
    assert semantics["portfolio.allocation_by_currency_pct"].method == "trading_currency_positions_plus_native_cash_snapshot_conversion"


@pytest.mark.asyncio
async def test_currency_allocation_uses_snapshot_exposure_denominator_when_engine_cash_fx_basis_differs():
    assets = [_asset(1, currency="EUR")]
    brokers = [_broker(1)]
    usd_cash = Currency(code="USD", amount=Decimal("100"))
    report = _report(
        holdings=[_holding(1, 1, nav_weight="89.8876404494", current_value="800")],
        contributions=[_contribution(1, 1)],
        brokers=brokers,
        nav="890",
        market="800",
        cash="90",
        broker_cash_balances={1: [usd_cash]},
        summary_cash_balances=[usd_cash],
        total_invested="590",
        total_gain_loss="300",
    )
    converter = _CashConverter({"USD": Decimal("0.95")})
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        convert_bulk_fn=converter,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PORTFOLIO_DESCRIPTION, AiExportDetailLevel.COMPACT), None)

    by_currency = {item.key: item for item in response.facts.allocations.by_currency}
    assert by_currency["EUR"].amount == Currency(code="EUR", amount=Decimal("800"))
    assert by_currency["EUR"].weight_pct == Decimal("89.39")
    assert by_currency["USD"].amount == Currency(code="EUR", amount=Decimal("95"))
    assert by_currency["USD"].weight_pct == Decimal("10.61")
    assert sum((entry.weight_pct for entry in by_currency.values()), start=Decimal("0")) == Decimal("100.00")
    semantics = {item.metric_code: item for item in response.semantics.metric_semantics}
    assert semantics["portfolio.allocation_by_currency_pct"].denominator == "trading_currency_positions_plus_native_cash_snapshot_value"


@pytest.mark.asyncio
async def test_required_native_cash_conversion_failure_is_source_failure():
    brokers = [_broker(1)]
    usd_cash = Currency(code="USD", amount=Decimal("100"))
    report = _report(
        holdings=[],
        contributions=[],
        brokers=brokers,
        nav="90",
        market="0",
        cash="90",
        broker_cash_balances={1: [usd_cash]},
        summary_cash_balances=[usd_cash],
        total_invested="90",
        total_gain_loss="0",
    )
    converter = _CashConverter(fail=True)
    assembler, _service, _prices = _assembler(
        report,
        assets=[],
        brokers=brokers,
        convert_bulk_fn=converter,
        technical_preparer=lambda *args, **kwargs: None,
    )

    with pytest.raises(AiExportSourceFailureError) as exc_info:
        await assembler.assemble(_prepared(AiExportPortfolioTask.PORTFOLIO_DESCRIPTION, AiExportDetailLevel.STANDARD), None)

    assert exc_info.value.source_code == "fx_service"
    assert exc_info.value.operation == "portfolio_cash_conversion_failed"
    assert len(converter.calls) == 1


@pytest.mark.asyncio
async def test_inconsistent_broker_and_summary_native_cash_sources_are_source_failure():
    brokers = [_broker(1)]
    report = _report(
        holdings=[],
        contributions=[],
        brokers=brokers,
        nav="90",
        market="0",
        cash="90",
        broker_cash_balances={1: [Currency(code="USD", amount=Decimal("100"))]},
        summary_cash_balances=[Currency(code="USD", amount=Decimal("99"))],
        total_invested="90",
        total_gain_loss="0",
    )
    converter = _CashConverter({"USD": Decimal("0.9")})
    assembler, _service, _prices = _assembler(
        report,
        assets=[],
        brokers=brokers,
        convert_bulk_fn=converter,
        technical_preparer=lambda *args, **kwargs: None,
    )

    with pytest.raises(AiExportSourceFailureError) as exc_info:
        await assembler.assemble(_prepared(AiExportPortfolioTask.PORTFOLIO_DESCRIPTION, AiExportDetailLevel.STANDARD), None)

    assert exc_info.value.source_code == "portfolio_service"
    assert exc_info.value.operation == "cash_balance_source_mismatch"
    assert converter.calls == []


@pytest.mark.asyncio
async def test_cash_decomposition_uses_latest_history_values_without_reconstruction():
    assets = [_asset(1)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="80", current_value="800")],
        contributions=[_contribution(1, 1)],
        brokers=brokers,
        history=[
            _history_point(END, cash="211", cash_capital="123", cash_returns="88"),
            _history_point(START, cash="100", cash_capital="70", cash_returns="30"),
        ],
    )
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PORTFOLIO_DESCRIPTION, AiExportDetailLevel.STANDARD), None)

    assert response.facts.cash_context is not None
    assert response.facts.cash_context.total_cash.amount == Decimal("211.00")
    assert response.facts.cash_context.cash_from_capital.amount == Decimal("123.00")
    assert response.facts.cash_context.cash_from_generated_returns.amount == Decimal("88.00")
    assert response.methodology.cash_decomposition_source == "portfolio_engine"


@pytest.mark.asyncio
async def test_performance_attribution_is_not_applicable_without_range_data_or_contributions():
    assets: list[Any] = []
    brokers = [_broker(1)]
    report = _report(holdings=[], contributions=[], brokers=brokers, nav="0", market="0", cash="0", history=[])
    report.summary.book_value = None
    assembler, _service, _prices = _assembler(report, assets=assets, brokers=brokers)

    with pytest.raises(AiExportTaskNotApplicableError) as exc_info:
        await assembler.assemble(_prepared(AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION, AiExportDetailLevel.STANDARD), None)

    assert exc_info.value.applicability_code == "selected_range_has_data"
    assert exc_info.value.reason_code == "selected_range_has_no_contributions"


@pytest.mark.asyncio
async def test_other_tasks_allow_truthful_empty_portfolio_snapshot():
    brokers = [_broker(1)]
    report = _report(holdings=[], contributions=[], brokers=brokers, nav="0", market="0", cash="0", history=[])
    report.summary.book_value = None
    report.summary.total_invested = Currency(code="EUR", amount=Decimal("0"))
    report.summary.net_deposited_capital = Currency(code="EUR", amount=Decimal("0"))
    report.summary.total_gain_loss = Currency(code="EUR", amount=Decimal("0"))
    assembler, service, prices = _assembler(report, assets=[], brokers=brokers)

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PAC_PLANNING, AiExportDetailLevel.COMPACT), None)

    assert response.facts.positions == []
    assert response.facts.contributions == []
    assert response.facts.summary.nav.amount == 0
    assert response.facts.summary.book_value.amount == 0
    assert response.facts.cash_context is not None
    assert response.facts.cash_context.total_cash.amount == 0
    assert response.facts.selection is not None
    assert response.facts.selection.total_entity_count == 0
    assert len(service.calls) == 1
    assert prices.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task", "expected_limit", "expected_asset_ids"),
    (
        (AiExportPortfolioTask.PAC_PLANNING, 12, {1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14}),
        (AiExportPortfolioTask.REBALANCING, 12, set(range(3, 15))),
        (AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION, 10, {1, 2, 3, 4, 5, 10, 11, 12, 13, 14}),
        (AiExportPortfolioTask.INCOME_REVIEW, 10, set(range(5, 15))),
        (AiExportPortfolioTask.PORTFOLIO_DESCRIPTION, 10, set(range(5, 15))),
    ),
)
async def test_compact_selectors_publish_typed_metadata_and_preserve_aggregate_allocations(
    task: AiExportPortfolioTask,
    expected_limit: int,
    expected_asset_ids: set[int],
):
    assets = [_asset(asset_id) for asset_id in range(1, 15)]
    brokers = [_broker(1)]
    holdings = [_holding(asset_id, 1, nav_weight=str(Decimal(asset_id) / Decimal("3")), current_value=str(asset_id * 10)) for asset_id in range(1, 15)]
    contributions = [
        _contribution(
            asset_id,
            1,
            pnl=str(asset_id - 7),
            income=str(asset_id),
        )
        for asset_id in range(1, 15)
    ]
    report = _report(holdings=holdings, contributions=contributions, brokers=brokers)
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(task, AiExportDetailLevel.COMPACT), None)

    assert response.facts.selection is not None
    assert response.facts.selection.limit == expected_limit
    assert response.facts.selection.included_entity_count == len(expected_asset_ids)
    assert response.facts.selection.total_entity_count == 14
    assert response.facts.selection.included_nav_weight_pct <= response.facts.selection.total_nav_weight_pct
    assert {position.asset_id for position in response.facts.positions} == expected_asset_ids
    assert {contribution.asset_id for contribution in response.facts.contributions} == expected_asset_ids
    if task in {
        AiExportPortfolioTask.PAC_PLANNING,
        AiExportPortfolioTask.REBALANCING,
        AiExportPortfolioTask.PORTFOLIO_DESCRIPTION,
    }:
        assert len(response.facts.allocations.by_asset) == 15
    else:
        assert response.facts.allocations.by_asset == []


@pytest.mark.asyncio
async def test_compact_ranking_metadata_and_technical_weights_use_raw_micro_values():
    assets = [_asset(asset_id) for asset_id in range(1, 13)]
    brokers = [_broker(1), _broker(2)]
    holdings = [
        *[_holding(asset_id, 1, nav_weight="1", current_value="10") for asset_id in range(1, 12)],
        _holding(12, 1, nav_weight="0.0049", current_value="0.0049", quantity="0.0049"),
        _holding(12, 2, nav_weight="0.0048", current_value="0.0048", quantity="0.0048"),
    ]
    contributions = [_contribution(holding.asset_id, holding.broker_id) for holding in holdings]
    report = _report(holdings=holdings, contributions=contributions, brokers=brokers)
    assembler, _service, _prices = _assembler(report, assets=assets, brokers=brokers)

    response = await assembler.assemble(
        _prepared(AiExportPortfolioTask.REBALANCING, AiExportDetailLevel.COMPACT, broker_ids=(1, 2)),
        None,
    )

    selected_keys = {(position.asset_id, position.broker_id) for position in response.facts.positions}
    assert (12, 1) in selected_keys
    assert (12, 2) not in selected_keys
    selected_micro = next(position for position in response.facts.positions if (position.asset_id, position.broker_id) == (12, 1))
    assert selected_micro.weight_pct == Decimal("0.00")
    assert selected_micro.market_value == Currency(code="EUR", amount=Decimal("0.00"))
    assert response.facts.selection is not None
    assert response.facts.selection.total_entity_count == 13
    assert response.facts.selection.included_entity_count == 12
    assert response.facts.selection.total_nav_weight_pct == Decimal("11.01")
    assert response.facts.selection.included_nav_weight_pct == Decimal("11.00")
    assert response.coverage.technical is not None
    assert response.coverage.technical.analyzed_nav_weight_pct == Decimal("11.01")


@pytest.mark.asyncio
async def test_pac_compact_filters_entity_details_and_notes_but_keeps_full_aggregates():
    selected_asset_ids = {1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14}
    assets = [_asset(asset_id, description=f"Description {asset_id}") for asset_id in range(1, 15)]
    brokers = [_broker(1, description="Broker one note"), _broker(2, description="Broker two note"), _broker(3, description="Excluded broker note")]
    holdings = [
        _holding(
            asset_id,
            3 if asset_id in {7, 8} else (1 if asset_id % 2 else 2),
            nav_weight=str(asset_id),
            current_value=str(asset_id * 10),
        )
        for asset_id in range(1, 15)
    ]
    contributions = [_contribution(holding.asset_id, holding.broker_id) for holding in holdings]
    report = _report(holdings=holdings, contributions=contributions, brokers=brokers)
    executor = _TechnicalExecutor(event_dates={asset_id: END - timedelta(days=asset_id) for asset_id in range(1, 15)})
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_executor=executor,
    )

    response = await assembler.assemble(
        _prepared(AiExportPortfolioTask.PAC_PLANNING, AiExportDetailLevel.COMPACT, broker_ids=(1, 2, 3)),
        None,
    )

    assert response.coverage.technical is not None
    assert response.coverage.technical.portfolio_assets == 14
    assert len(response.facts.allocations.by_asset) == 15
    assert {position.asset_id for position in response.facts.positions} == selected_asset_ids
    assert {state.target.asset_id for state in response.states} == selected_asset_ids
    assert all(event.target.asset_id in selected_asset_ids for event in response.events)
    assert {note.subject_reference for note in response.domain_notes if note.subject.value == "asset"} == {f"asset:{asset_id}" for asset_id in selected_asset_ids}
    assert {note.subject_reference for note in response.domain_notes if note.subject.value == "broker"} == {"broker:1", "broker:2"}


@pytest.mark.asyncio
async def test_pac_smallest_satellites_use_unrounded_sub_cent_market_value():
    assets = [_asset(asset_id) for asset_id in range(1, 15)]
    brokers = [_broker(1)]
    holdings = [
        _holding(
            asset_id,
            1,
            nav_weight=("0.004" if asset_id == 6 else str(asset_id)),
            current_value=("0.004" if asset_id == 6 else str(asset_id * (100 if asset_id >= 9 else 1))),
            quantity=("0.001" if asset_id == 6 else "2"),
        )
        for asset_id in range(1, 15)
    ]
    report = _report(
        holdings=holdings,
        contributions=[_contribution(asset_id, 1) for asset_id in range(1, 15)],
        brokers=brokers,
    )
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PAC_PLANNING, AiExportDetailLevel.COMPACT), None)
    selected = {position.asset_id: position for position in response.facts.positions}

    assert set(selected) == {1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14}
    assert selected[6].market_value == Currency(code="EUR", amount=Decimal("0.00"))
    assert selected[6].weight_pct == Decimal("0.00")


@pytest.mark.asyncio
async def test_pac_missing_price_open_position_remains_satellite_candidate():
    assets = [_asset(asset_id) for asset_id in range(1, 15)]
    brokers = [_broker(1)]
    holdings = [
        (
            _holding(
                asset_id,
                1,
                nav_weight=None,
                current_value=None,
                quantity="0.0001",
                source="MISSING",
                trading_price=None,
            )
            if asset_id == 6
            else _holding(
                asset_id,
                1,
                nav_weight=str(asset_id),
                current_value=str(asset_id * (100 if asset_id >= 9 else 1)),
            )
        )
        for asset_id in range(1, 15)
    ]
    report = _report(
        holdings=holdings,
        contributions=[_contribution(asset_id, 1) for asset_id in range(1, 15)],
        brokers=brokers,
    )
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PAC_PLANNING, AiExportDetailLevel.COMPACT), None)
    selected = {position.asset_id: position for position in response.facts.positions}

    assert set(selected) == {1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14}
    assert selected[6].valuation_source == "missing"
    assert selected[6].market_value is None
    assert selected[6].weight_pct is None


@pytest.mark.asyncio
async def test_technical_breadth_uses_full_universe_then_filters_compact_targets():
    assets = [_asset(asset_id) for asset_id in range(1, 13)]
    brokers = [_broker(1)]
    holdings = [_holding(asset_id, 1, nav_weight=str(asset_id / 2), current_value=str(asset_id * 10)) for asset_id in range(1, 13)]
    contributions = [_contribution(asset_id, 1) for asset_id in range(1, 13)]
    report = _report(holdings=holdings, contributions=contributions, brokers=brokers)
    event_dates = {asset_id: END - timedelta(days=asset_id) for asset_id in range(1, 9)}
    executor = _TechnicalExecutor(event_dates=event_dates)
    assembler, _service, prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        price_loader=_PriceLoader(set(range(1, 13)) - {10}),
        technical_executor=executor,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.TECHNICAL_BREADTH, AiExportDetailLevel.COMPACT), None)

    assert len(prices.calls) == 1
    assert response.coverage.technical is not None
    assert response.coverage.technical.portfolio_assets == 12
    assert response.coverage.technical.technically_eligible_assets == 11
    assert response.coverage.weighted_breadth is not None
    assert response.coverage.weighted_breadth.eligible_assets == 11
    assert len(response.states) == 10
    assert len(response.events) == 8
    assert response.technical is not None
    assert len(response.technical.targets) == 10
    assert response.facts.selection is not None
    assert response.facts.selection.total_entity_count == 12
    assert response.facts.selection.included_entity_count == 10
    assert len(response.facts.positions) == 10
    assert {position.asset_id for position in response.facts.positions} == {1, 2, 3, 4, 5, 6, 7, 8, 11, 12}
    assert {target.target.asset_id for target in response.technical.targets} == {1, 2, 3, 4, 5, 6, 7, 8, 11, 12}
    assert {state.target.asset_id for state in response.states} == {1, 2, 3, 4, 5, 6, 7, 8, 11, 12}
    assert {event.target.asset_id for event in response.events} == set(range(1, 9))


@pytest.mark.asyncio
async def test_portfolio_compact_filters_events_before_common_quota():
    assets = [_asset(asset_id) for asset_id in range(1, 15)]
    brokers = [_broker(1)]
    holdings = [_holding(asset_id, 1, nav_weight=str(asset_id), current_value=str(asset_id * 10)) for asset_id in range(1, 15)]
    report = _report(
        holdings=holdings,
        contributions=[_contribution(asset_id, 1) for asset_id in range(1, 15)],
        brokers=brokers,
    )
    executor = _TechnicalExecutor(event_dates={asset_id: END - timedelta(days=asset_id) for asset_id in range(1, 15)})
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_executor=executor,
    )

    response = await assembler.assemble(
        _prepared(AiExportPortfolioTask.REBALANCING, AiExportDetailLevel.COMPACT),
        None,
    )

    assert {position.asset_id for position in response.facts.positions} == set(range(3, 15))
    assert len(response.events) == 10
    assert {event.target.asset_id for event in response.events} == set(range(3, 13))


@pytest.mark.asyncio
async def test_notes_keep_provenance_and_never_export_user_urls_or_transaction_descriptions():
    assets = [_asset(1, description="<script>alert('asset')</script> provider or user note", user_url="https://secret.example/account/ABC")]
    brokers = [_broker(1, description="<img src=x onerror=alert('broker')> user note")]
    report = _report(holdings=[_holding(1, 1, nav_weight="80", current_value="800")], contributions=[_contribution(1, 1)], brokers=brokers)
    assembler, _service, _prices = _assembler(
        report,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared(AiExportPortfolioTask.PORTFOLIO_DESCRIPTION, AiExportDetailLevel.STANDARD), None)
    dumped = response.model_dump_json()

    assert [(note.subject.value, note.source.value) for note in response.domain_notes] == [
        ("asset", "provider_or_user"),
        ("broker", "user"),
    ]
    assert "<script>" in dumped
    assert "https://secret.example/account/ABC" not in dumped
    assert "portal_url" not in dumped
    assert "transaction_description" not in dumped

    technical_response = await assembler.assemble(_prepared(AiExportPortfolioTask.TECHNICAL_BREADTH, AiExportDetailLevel.STANDARD), None)
    assert technical_response.domain_notes == []


@pytest.mark.asyncio
async def test_output_order_and_stats_are_deterministic_for_reversed_sources():
    assets = [_asset(1), _asset(2), _asset(3)]
    brokers = [_broker(1), _broker(2)]
    holdings = [_holding(3, 2, nav_weight="20", current_value="200"), _holding(1, 1, nav_weight="30", current_value="300"), _holding(2, 1, nav_weight="30", current_value="300")]
    contributions = [_contribution(3, 2), _contribution(1, 1), _contribution(2, 1)]
    report_a = _report(holdings=holdings, contributions=contributions, brokers=brokers)
    report_b = _report(holdings=list(reversed(holdings)), contributions=list(reversed(contributions)), brokers=list(reversed(brokers)))
    assembler_a, _service_a, _prices_a = _assembler(
        report_a,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )
    assembler_b, _service_b, _prices_b = _assembler(
        report_b,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
        reverse_metadata=True,
    )

    response_a = await assembler_a.assemble(_prepared(AiExportPortfolioTask.PAC_PLANNING, AiExportDetailLevel.STANDARD, broker_ids=(1, 2)), None)
    response_b = await assembler_b.assemble(_prepared(AiExportPortfolioTask.PAC_PLANNING, AiExportDetailLevel.STANDARD, broker_ids=(1, 2)), None)

    assert response_a.model_dump(mode="json") == response_b.model_dump(mode="json")
    assert [(item.asset_id, item.broker_id) for item in response_a.facts.positions] == [(1, 1), (2, 1), (3, 2)]
    assert response_a.export_stats.canonical_json.positions == 3


def _lot(
    lot_id: int,
    *,
    opened: date = START,
    original_quantity: str = "10",
    open_quantity: str = "10",
    realized_quantity: str = "0",
    original_cost: str = "800",
    open_value: str | None = "1000",
    market_pnl: str | None = "200",
    realized_pnl: str = "20",
    income: str = "5",
    value_source: str = "MARKET_PRICE",
    direction: str = "LONG",
    in_transit: str = "0",
) -> SimpleNamespace:
    custody = []
    if Decimal(in_transit) != 0:
        custody.append(SimpleNamespace(custody_type="IN_TRANSIT", quantity=Decimal(in_transit)))
    return SimpleNamespace(
        lot_id=lot_id,
        opening_date=opened,
        original_quantity=Decimal(original_quantity),
        open_quantity=Decimal(open_quantity),
        realized_quantity=Decimal(realized_quantity),
        original_cost=Decimal(original_cost),
        open_value=Decimal(open_value) if open_value is not None else None,
        market_pnl=Decimal(market_pnl) if market_pnl is not None else None,
        realized_pnl=Decimal(realized_pnl),
        asset_income=Decimal(income),
        value_source=value_source,
        direction=direction,
        current_custody=custody,
    )


def _lots_response(
    lots: list[Any],
    *,
    status: str = "COMPLETE",
) -> SimpleNamespace:
    return SimpleNamespace(calculation_status=status, lots=list(lots))


class _LotsService:
    def __init__(
        self,
        responses: dict[int, Any] | None = None,
        *,
        failing_asset_ids: set[int] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.failing_asset_ids = failing_asset_ids or set()
        self.calls: list[dict[str, Any]] = []

    async def get_lots_analysis(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        asset_id = kwargs["asset_id"]
        if asset_id in self.failing_asset_ids:
            raise RuntimeError(f"failed asset {asset_id}")
        return self.responses.get(asset_id, _lots_response([]))


class _LatestTransactionLoader:
    def __init__(self, transaction: Any | None = None) -> None:
        self.transaction = transaction
        self.calls: list[tuple[Any, int, date]] = []

    async def __call__(
        self,
        session: Any,
        broker_id: int,
        snapshot_as_of: date,
    ) -> Any | None:
        self.calls.append((session, broker_id, snapshot_as_of))
        return self.transaction


def _prepared_broker(
    task: AiExportBrokerTask,
    detail: AiExportDetailLevel,
    *,
    broker_id: int = 1,
) -> AiExportPreparedRequest:
    request = AiExportBrokerSnapshotRequest(
        domain=AiExportDomain.BROKER,
        task=task,
        detail_level=detail,
        date_range=DateRangeModel(start=START, end=END),
        target_currency="EUR",
        broker_id=broker_id,
    )
    return AiExportPreparedRequest(
        request=request,
        resolved_profile=resolve_profile(AiExportDomain.BROKER, task, detail),
        user_id=42,
        broker_scope=(broker_id,),
    )


def _broker_assembler(
    report: Any,
    *,
    assets: list[Any],
    brokers: list[Any],
    lots_service: _LotsService | None = None,
    latest_loader: _LatestTransactionLoader | None = None,
    price_loader: _PriceLoader | None = None,
    technical_executor: _TechnicalExecutor | None = None,
    technical_preparer: Any = None,
    reverse_metadata: bool = False,
) -> tuple[
    AiExportBrokerAssembler,
    _PortfolioService,
    _PriceLoader,
    _LotsService,
    _LatestTransactionLoader,
]:
    service = _PortfolioService(report)
    prices = price_loader or _PriceLoader()
    lots = lots_service or _LotsService()
    latest = latest_loader or _LatestTransactionLoader()
    kwargs: dict[str, Any] = {}
    if technical_preparer is not None:
        kwargs["technical_preparer"] = technical_preparer
    assembler = AiExportBrokerAssembler(
        portfolio_service=service,
        lots_service=lots,
        price_bulk_loader=prices,
        asset_metadata_loader=_MetadataLoader(assets, reverse=reverse_metadata),
        broker_metadata_loader=_MetadataLoader(brokers, reverse=reverse_metadata),
        latest_transaction_loader=latest,
        technical_executor=technical_executor or _TechnicalExecutor(),
        clock=_fixed_clock,
        **kwargs,
    )
    return assembler, service, prices, lots, latest


BROKER_TASKS = tuple(AiExportBrokerTask)


@pytest.mark.asyncio
@pytest.mark.parametrize("task", BROKER_TASKS)
@pytest.mark.parametrize("detail", DETAIL_LEVELS)
async def test_all_12_broker_profiles_are_schema_and_meta_valid(task: AiExportBrokerTask, detail: AiExportDetailLevel):
    assets = [_asset(1), _asset(2, currency="EUR")]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="30", current_value="300"), _holding(2, 1, nav_weight="50", current_value="500")],
        contributions=[_contribution(1, 1, pnl="15"), _contribution(2, 1, pnl="-5")],
        unallocated=[_unallocated(1)],
        other_effects=[_other_effect("Broker adjustment", category="Cost", amount="-3", broker_id=1)],
        brokers=brokers,
    )
    lots = _LotsService(
        {
            1: _lots_response([_lot(101, original_cost="240", open_value="300", market_pnl="60")]),
            2: _lots_response([_lot(201, original_cost="400", open_value="500", market_pnl="100")]),
        }
    )
    assembler, _service, _prices, _lots, _latest = _broker_assembler(
        report,
        assets=assets,
        brokers=brokers,
        lots_service=lots,
    )

    response = await assembler.assemble(_prepared_broker(task, detail), None)
    validated = AiExportBrokerSnapshotResponse.model_validate(response.model_dump())

    assert validated.meta.profile_id == f"broker.{task.value}.{detail.value}"
    assert validated.meta.generated_at == FIXED_NOW
    assert validated.meta.target_currency == "EUR"
    assert validated.facts.summary.broker_id == 1
    assert (validated.facts.selection is not None) is (detail == AiExportDetailLevel.COMPACT)
    assert validated.export_stats.canonical_json.positions == len(validated.facts.positions)
    contributions_allowed = task in {
        AiExportBrokerTask.BROKER_REVIEW,
        AiExportBrokerTask.BROKER_COST_EFFICIENCY,
    }
    assert bool(validated.facts.contributions) is contributions_allowed
    assert bool(validated.facts.unallocated_contributions) is contributions_allowed
    assert bool(validated.facts.other_period_effects) is contributions_allowed


@pytest.mark.asyncio
async def test_broker_uses_one_exactly_scoped_report_and_one_price_bulk_call():
    assets = [_asset(1), _asset(2)]
    brokers = [_broker(7)]
    report = _report(
        holdings=[_holding(1, 7, nav_weight="40", current_value="400"), _holding(2, 7, nav_weight="40", current_value="400")],
        contributions=[_contribution(1, 7), _contribution(2, 7)],
        brokers=brokers,
    )
    assembler, service, prices, lots, _latest = _broker_assembler(report, assets=assets, brokers=brokers)

    await assembler.assemble(
        _prepared_broker(AiExportBrokerTask.BROKER_REVIEW, AiExportDetailLevel.STANDARD, broker_id=7),
        None,
    )

    assert len(service.calls) == 1
    user_id, query = service.calls[0]
    assert user_id == 42
    assert query.broker_ids == [7]
    assert query.date_range == OpenDateRangeModel(start=START, end=END)
    assert query.target_currency == "EUR"
    assert query.include_summary is True
    assert query.include_history is True
    assert query.include_breakdown is True
    assert query.include_positions_contribution is True
    assert query.include_allocation_history is False
    assert len(prices.calls) == 1
    assert {item.asset_id for item in prices.calls[0]} == {1, 2}
    assert lots.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("detail", [AiExportDetailLevel.STANDARD, AiExportDetailLevel.FULL])
async def test_broker_standard_and_full_keep_all_positions_including_missing_price(detail: AiExportDetailLevel):
    assets = [_asset(1), _asset(2)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[
            _holding(1, 1, nav_weight="50", current_value="500"),
            _holding(2, 1, nav_weight=None, current_value=None, source="MISSING", trading_price=None),
        ],
        contributions=[_contribution(1, 1), _contribution(2, 1)],
        brokers=brokers,
    )
    lots = _LotsService(
        {
            1: _lots_response([_lot(1)]),
            2: _lots_response([_lot(2, open_value=None, market_pnl=None, value_source="ESTIMATED_AT_COST")]),
        }
    )
    executor = _TechnicalExecutor()
    assembler, _service, _prices, _lots, _latest = _broker_assembler(
        report,
        assets=assets,
        brokers=brokers,
        lots_service=lots,
        price_loader=_PriceLoader({1}),
        technical_executor=executor,
    )

    response = await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_REVIEW, detail), None)

    assert [position.asset_id for position in response.facts.positions] == [1, 2]
    assert response.facts.positions[1].valuation_source == "missing"
    assert response.facts.positions[1].cost_basis is not None
    assert response.coverage.technical is not None
    assert response.coverage.technical.portfolio_assets == 2
    assert response.coverage.technical.technically_eligible_assets == 1
    assert executor.calls == [(1, 1), (2, 0)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task", "expected_ids", "expected_rule"),
    (
        (AiExportBrokerTask.BROKER_REVIEW, set(range(3, 13)), "largest_nav"),
        (AiExportBrokerTask.BROKER_COST_EFFICIENCY, set(range(1, 11)), "largest_absolute_period_fees_taxes"),
        (AiExportBrokerTask.BROKER_CONCENTRATION_CONTEXT, set(range(3, 13)), "largest_nav"),
        (AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW, set(range(1, 11)), "largest_residual_cost_basis"),
    ),
)
async def test_broker_compact_selectors_are_exact_and_keep_full_aggregate_context(
    task: AiExportBrokerTask,
    expected_ids: set[int],
    expected_rule: str,
):
    assets = [_asset(asset_id) for asset_id in range(1, 13)]
    brokers = [_broker(1)]
    holdings = [_holding(asset_id, 1, nav_weight=str(asset_id), current_value=str(asset_id * 10)) for asset_id in range(1, 13)]
    contributions = [_contribution(asset_id, 1, fees_taxes=str(13 - asset_id)) for asset_id in range(1, 13)]
    lots = _LotsService(
        {
            asset_id: _lots_response(
                [
                    _lot(
                        asset_id,
                        original_quantity="1",
                        open_quantity="1",
                        original_cost=str(1000 - asset_id * 10),
                        open_value=str(asset_id * 10),
                    )
                ]
            )
            for asset_id in range(1, 13)
        }
    )
    report = _report(holdings=holdings, contributions=contributions, brokers=brokers)
    assembler, _service, _prices, used_lots, _latest = _broker_assembler(report, assets=assets, brokers=brokers, lots_service=lots)

    response = await assembler.assemble(_prepared_broker(task, AiExportDetailLevel.COMPACT), None)

    assert {position.asset_id for position in response.facts.positions} == expected_ids
    assert response.facts.selection is not None
    assert response.facts.selection.rule == expected_rule
    assert response.facts.selection.limit == 10
    assert response.facts.selection.total_entity_count == 12
    assert response.facts.selection.included_entity_count == 10
    assert response.facts.selection.total_nav_weight_pct == Decimal("78.00")
    assert response.facts.summary.nav.amount == Decimal("1000.00")
    if task in {
        AiExportBrokerTask.BROKER_REVIEW,
        AiExportBrokerTask.BROKER_COST_EFFICIENCY,
    }:
        assert {contribution.asset_id for contribution in response.facts.contributions} == expected_ids
    else:
        assert response.facts.contributions == []
    assert response.facts.unallocated_contributions == []
    assert response.facts.other_period_effects == []
    if response.facts.concentration is not None:
        assert response.facts.concentration.position_count == 12
        assert response.facts.concentration.largest_position_weight_pct == Decimal("15.38")
        assert response.facts.concentration.top_five_weight_pct == Decimal("64.10")
        assert response.facts.concentration.herfindahl_index == Decimal("0.106838")
        assert len(response.facts.concentration.entries) == 10
    if task == AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW:
        assert response.facts.fifo_summary is not None
        assert response.facts.fifo_summary.residual_cost_basis == Currency(code="EUR", amount=Decimal("11220.00"))
    assert len(used_lots.calls) == (12 if task == AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW else 0)


@pytest.mark.asyncio
async def test_compact_cost_efficiency_includes_fully_sold_candidates_and_all_broker_level_costs():
    open_asset_ids = list(range(1, 12))
    sold_asset_id = 99
    assets = [_asset(asset_id) for asset_id in [*open_asset_ids, sold_asset_id]]
    brokers = [_broker(1)]
    holdings = [_holding(asset_id, 1, nav_weight=str(asset_id), current_value=str(asset_id * 10)) for asset_id in open_asset_ids]
    contributions = [
        *[_contribution(asset_id, 1, fees_taxes="1") for asset_id in open_asset_ids],
        _contribution(sold_asset_id, 1, fees_taxes="100", fully_sold=True),
    ]
    report = _report(
        holdings=holdings,
        contributions=contributions,
        unallocated=[_unallocated(1, income="4", fees_taxes="7")],
        other_effects=[_other_effect("Broker custody fee", category="Cost", amount="-9", broker_id=1)],
        brokers=brokers,
    )
    assembler, _service, _prices, _lots, _latest = _broker_assembler(report, assets=assets, brokers=brokers)

    response = await assembler.assemble(
        _prepared_broker(AiExportBrokerTask.BROKER_COST_EFFICIENCY, AiExportDetailLevel.COMPACT),
        None,
    )

    assert response.facts.selection is not None
    assert response.facts.selection.total_entity_count == 12
    assert response.facts.selection.included_entity_count == 10
    assert sold_asset_id in {contribution.asset_id for contribution in response.facts.contributions}
    sold = next(contribution for contribution in response.facts.contributions if contribution.asset_id == sold_asset_id)
    assert sold.is_fully_sold is True
    assert sold.fees_taxes_amount == Currency(code="EUR", amount=Decimal("100.00"))
    assert sold_asset_id not in {position.asset_id for position in response.facts.positions}
    assert len(response.facts.positions) == 9
    assert response.facts.unallocated_contributions[0].unallocated_fees_taxes_amount == Currency(code="EUR", amount=Decimal("7.00"))
    assert response.facts.other_period_effects[0].period_pnl_amount == Currency(code="EUR", amount=Decimal("-9.00"))


@pytest.mark.asyncio
async def test_broker_concentration_counts_missing_values_without_fabricating_weights():
    assets = [_asset(1), _asset(2), _asset(3)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[
            _holding(1, 1, nav_weight="60", current_value="600"),
            _holding(2, 1, nav_weight="30", current_value="300"),
            _holding(3, 1, nav_weight=None, current_value=None, source="MISSING", trading_price=None),
        ],
        contributions=[_contribution(1, 1), _contribution(2, 1), _contribution(3, 1)],
        brokers=brokers,
    )
    assembler, _service, _prices, _lots, _latest = _broker_assembler(report, assets=assets, brokers=brokers)

    response = await assembler.assemble(
        _prepared_broker(AiExportBrokerTask.BROKER_CONCENTRATION_CONTEXT, AiExportDetailLevel.STANDARD),
        None,
    )
    concentration = response.facts.concentration

    assert concentration is not None
    assert concentration.position_count == 3
    assert concentration.largest_position_weight_pct == Decimal("66.67")
    assert concentration.top_five_weight_pct == Decimal("100.00")
    assert concentration.herfindahl_index == Decimal("0.555556")
    assert [entry.asset_id for entry in concentration.entries] == [1, 2]
    assert response.facts.positions[2].weight_pct is None
    assert response.facts.positions[2].market_value is None


@pytest.mark.asyncio
async def test_broker_concentration_uses_gross_absolute_market_exposure_for_long_and_short():
    assets = [_asset(1), _asset(2)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[
            _holding(1, 1, nav_weight="80", current_value="80"),
            _holding(2, 1, nav_weight="-70", current_value="-70", quantity="-1"),
        ],
        contributions=[_contribution(1, 1), _contribution(2, 1)],
        brokers=brokers,
        nav="100",
        market="10",
        cash="90",
    )
    assembler, _service, _prices, _lots, _latest = _broker_assembler(report, assets=assets, brokers=brokers)

    response = await assembler.assemble(
        _prepared_broker(AiExportBrokerTask.BROKER_CONCENTRATION_CONTEXT, AiExportDetailLevel.STANDARD),
        None,
    )
    concentration = response.facts.concentration

    assert concentration is not None
    assert [entry.asset_id for entry in concentration.entries] == [1, 2]
    assert [entry.weight_pct for entry in concentration.entries] == [Decimal("53.33"), Decimal("46.67")]
    assert concentration.largest_position_weight_pct == Decimal("53.33")
    assert concentration.top_five_weight_pct == Decimal("100.00")
    assert concentration.herfindahl_index == Decimal("0.502222")
    assert response.facts.positions[1].weight_pct == Decimal("-70.00")
    assert response.coverage.technical.analyzed_nav_weight_pct == Decimal("150.00")
    semantics = {item.metric_code: item for item in response.semantics.metric_semantics}
    assert semantics["broker.herfindahl_index"].denominator == "gross_absolute_open_position_market_value"


@pytest.mark.asyncio
async def test_latest_transaction_exports_only_authoritative_safe_fields():
    assets = [_asset(1)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="80", current_value="800")],
        contributions=[_contribution(1, 1)],
        brokers=brokers,
    )
    transaction = SimpleNamespace(
        id=99,
        broker_id=1,
        asset_id=1,
        date=END,
        type="BUY",
        quantity=Decimal("5"),
        amount=Decimal("-600"),
        currency="EUR",
        fees_taxes_amount=Currency(code="EUR", amount=Decimal("3")),
        description="secret transaction description",
        account_number="IT00SECRET",
        tags="private",
        source_file="broker-export.csv",
        last_import_at=FIXED_NOW,
    )
    latest = _LatestTransactionLoader(transaction)
    assembler, _service, _prices, _lots, used_latest = _broker_assembler(
        report,
        assets=assets,
        brokers=brokers,
        latest_loader=latest,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_REVIEW, AiExportDetailLevel.STANDARD), None)
    activity = response.facts.latest_transaction
    dumped = response.model_dump_json()

    assert used_latest.calls == [(None, 1, END)]
    assert activity is not None
    assert activity.transaction_date == END
    assert activity.transaction_type == "BUY"
    assert activity.asset_id == 1
    assert activity.quantity == Decimal("5")
    assert activity.gross_amount == Currency(code="EUR", amount=Decimal("600.00"))
    assert activity.fees_taxes_amount == Currency(code="EUR", amount=Decimal("3.00"))
    for secret in ("secret transaction description", "IT00SECRET", "private", "broker-export.csv", "last_import_at"):
        assert secret not in dumped


@pytest.mark.asyncio
async def test_fifo_calls_each_selected_asset_sequentially_and_aggregates_without_histories():
    assets = [_asset(1), _asset(2)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="40", current_value="400"), _holding(2, 1, nav_weight="40", current_value="400")],
        contributions=[_contribution(1, 1), _contribution(2, 1)],
        brokers=brokers,
    )
    lots = _LotsService(
        {
            1: _lots_response(
                [
                    _lot(11, opened=END - timedelta(days=100), original_cost="400", open_value="500", market_pnl="100"),
                    _lot(12, opened=END - timedelta(days=200), open_quantity="5", realized_quantity="5", original_cost="300", open_value="200", market_pnl="50"),
                ]
            ),
            2: _lots_response(
                [
                    _lot(21, opened=END - timedelta(days=50), open_quantity="0", realized_quantity="10", original_cost="200", open_value="0", market_pnl="0"),
                    _lot(22, opened=END - timedelta(days=20), original_cost="100", open_value="120", market_pnl="20", value_source="ESTIMATED_AT_COST", in_transit="2"),
                ]
            ),
        }
    )
    assembler, _service, _prices, used_lots, _latest = _broker_assembler(
        report,
        assets=assets,
        brokers=brokers,
        lots_service=lots,
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW, AiExportDetailLevel.STANDARD), None)
    fifo = response.facts.fifo_summary

    assert [call["asset_id"] for call in used_lots.calls] == [1, 2]
    assert all(call["broker_ids"] == [1] for call in used_lots.calls)
    assert all(call["date_from"] == START and call["date_to"] == END for call in used_lots.calls)
    assert all(call["requested_analyses"] == [LotAnalysisType.LOT_SUMMARY] for call in used_lots.calls)
    assert all(call["selected_lot_ids"] is None for call in used_lots.calls)
    assert fifo is not None
    assert fifo.open_lot_count == 3
    assert fifo.partial_lot_count == 1
    assert fifo.closed_lot_count == 1
    assert fifo.oldest_lot_date == END - timedelta(days=200)
    assert fifo.residual_cost_basis == Currency(code="EUR", amount=Decimal("650.00"))
    assert fifo.market_value == Currency(code="EUR", amount=Decimal("820.00"))
    assert fifo.realized_pnl_amount == Currency(code="EUR", amount=Decimal("80.00"))
    assert fifo.unrealized_pnl_amount == Currency(code="EUR", amount=Decimal("170.00"))
    assert fifo.income_amount == Currency(code="EUR", amount=Decimal("20.00"))
    assert fifo.in_transit_quantity == Decimal("2")
    assert fifo.estimated_at_cost_value == Currency(code="EUR", amount=Decimal("120.00"))
    assert response.methodology.lot_matching_method == "runtime_fifo"
    assert "gantt_segments" not in response.model_dump_json()
    assert "fragment" not in response.model_dump_json()


@pytest.mark.asyncio
async def test_fifo_is_not_called_for_unrelated_profiles_and_review_full_failure_is_omitted():
    assets = [_asset(1)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="80", current_value="800")],
        contributions=[_contribution(1, 1)],
        brokers=brokers,
    )
    lots = _LotsService(failing_asset_ids={1})
    assembler, _service, _prices, used_lots, _latest = _broker_assembler(
        report,
        assets=assets,
        brokers=brokers,
        lots_service=lots,
        technical_preparer=lambda *args, **kwargs: None,
    )

    standard = await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_REVIEW, AiExportDetailLevel.STANDARD), None)
    concentration = await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_CONCENTRATION_CONTEXT, AiExportDetailLevel.FULL), None)
    full = await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_REVIEW, AiExportDetailLevel.FULL), None)

    assert standard.facts.fifo_summary is None
    assert concentration.facts.fifo_summary is None
    assert full.facts.fifo_summary is None
    assert len(used_lots.calls) == 1


@pytest.mark.asyncio
async def test_required_fifo_failed_result_is_source_failure():
    assets = [_asset(1)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="80", current_value="800")],
        contributions=[_contribution(1, 1)],
        brokers=brokers,
    )
    lots = _LotsService({1: _lots_response([_lot(1)], status="FAILED")})
    assembler, _service, _prices, _lots, _latest = _broker_assembler(report, assets=assets, brokers=brokers, lots_service=lots)

    with pytest.raises(AiExportSourceFailureError) as exc_info:
        await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW, AiExportDetailLevel.FULL), None)

    assert exc_info.value.source_code == "lots_analysis_service"
    assert exc_info.value.operation == "unreliable_lot_summary"


@pytest.mark.asyncio
async def test_empty_broker_snapshots_are_truthful_but_fifo_is_not_applicable():
    brokers = [_broker(1)]
    report = _report(
        holdings=[],
        contributions=[],
        brokers=brokers,
        nav="0",
        market="0",
        cash="0",
        history=[],
        total_invested="0",
        total_gain_loss="0",
    )
    report.summary.book_value = None
    assembler, service, prices, lots, _latest = _broker_assembler(report, assets=[], brokers=brokers)

    for task in (
        AiExportBrokerTask.BROKER_REVIEW,
        AiExportBrokerTask.BROKER_COST_EFFICIENCY,
        AiExportBrokerTask.BROKER_CONCENTRATION_CONTEXT,
    ):
        response = await assembler.assemble(_prepared_broker(task, AiExportDetailLevel.COMPACT), None)
        assert response.facts.positions == []
        assert response.facts.summary.nav.amount == 0
        assert response.facts.summary.book_value.amount == 0
        assert response.facts.selection is not None
        assert response.facts.selection.total_entity_count == 0

    with pytest.raises(AiExportTaskNotApplicableError) as exc_info:
        await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW, AiExportDetailLevel.STANDARD), None)

    assert exc_info.value.reason_code == "broker_has_no_open_positions_or_lots"
    assert len(service.calls) == 4
    assert prices.calls == []
    assert lots.calls == []


@pytest.mark.asyncio
async def test_fifo_with_open_position_but_closed_only_lots_is_source_failure():
    assets = [_asset(1)]
    brokers = [_broker(1)]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="80", current_value="800")],
        contributions=[_contribution(1, 1)],
        brokers=brokers,
    )
    lots = _LotsService(
        {
            1: _lots_response(
                [
                    _lot(
                        1,
                        open_quantity="0",
                        realized_quantity="10",
                        open_value="0",
                        market_pnl="0",
                    )
                ]
            )
        }
    )
    assembler, _service, _prices, used_lots, _latest = _broker_assembler(
        report,
        assets=assets,
        brokers=brokers,
        lots_service=lots,
    )

    with pytest.raises(AiExportSourceFailureError) as exc_info:
        await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_FIFO_LOT_REVIEW, AiExportDetailLevel.STANDARD), None)

    assert exc_info.value.source_code == "lots_analysis_service"
    assert exc_info.value.operation == "missing_open_lot_summary"
    assert len(used_lots.calls) == 1


@pytest.mark.asyncio
async def test_broker_technical_coverage_uses_full_universe_then_filters_compact_details():
    assets = [_asset(asset_id) for asset_id in range(1, 13)]
    brokers = [_broker(1)]
    holdings = [_holding(asset_id, 1, nav_weight=str(asset_id), current_value=str(asset_id * 10)) for asset_id in range(1, 13)]
    report = _report(
        holdings=holdings,
        contributions=[_contribution(asset_id, 1) for asset_id in range(1, 13)],
        brokers=brokers,
    )
    executor = _TechnicalExecutor(event_dates={asset_id: END - timedelta(days=asset_id) for asset_id in range(1, 13)})
    assembler, _service, prices, _lots, _latest = _broker_assembler(
        report,
        assets=assets,
        brokers=brokers,
        price_loader=_PriceLoader(set(range(1, 13)) - {10}),
        technical_executor=executor,
    )

    response = await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_REVIEW, AiExportDetailLevel.COMPACT), None)

    assert len(prices.calls) == 1
    assert {query.asset_id for query in prices.calls[0]} == set(range(1, 13))
    assert len(executor.calls) == 12
    assert response.coverage.technical is not None
    assert response.coverage.technical.portfolio_assets == 12
    assert response.coverage.technical.technically_eligible_assets == 11
    assert response.coverage.weighted_breadth is not None
    assert response.coverage.weighted_breadth.eligible_assets == 11
    assert {position.asset_id for position in response.facts.positions} == set(range(3, 13))
    assert {state.target.asset_id for state in response.states} == set(range(3, 10)) | {11, 12}
    assert response.technical is not None
    assert {target.target.asset_id for target in response.technical.targets} == set(range(3, 10)) | {11, 12}
    assert {event.target.asset_id for event in response.events} == set(range(3, 10)) | {11, 12}


@pytest.mark.asyncio
async def test_broker_notes_provenance_sensitive_field_exclusion_and_complete_non_position_costs():
    assets = [_asset(1, description="<script>asset note</script>", user_url="https://private.example/asset")]
    brokers = [_broker(1, description="<img onerror=broker> user note")]
    report = _report(
        holdings=[_holding(1, 1, nav_weight="80", current_value="800")],
        contributions=[_contribution(1, 1, fees_taxes="11")],
        unallocated=[_unallocated(1, income="7", fees_taxes="2")],
        other_effects=[_other_effect("Residual reconciliation", category="Cost", amount="-3", broker_id=1)],
        brokers=brokers,
    )
    transaction = SimpleNamespace(
        id=1,
        broker_id=1,
        asset_id=1,
        date=END,
        type="BUY",
        quantity=Decimal("1"),
        amount=Decimal("-100"),
        currency="EUR",
        description="do not export me",
        tags="secret-tag",
        source_file="secret.csv",
    )
    assembler, _service, _prices, _lots, _latest = _broker_assembler(
        report,
        assets=assets,
        brokers=brokers,
        latest_loader=_LatestTransactionLoader(transaction),
        technical_preparer=lambda *args, **kwargs: None,
    )

    response = await assembler.assemble(_prepared_broker(AiExportBrokerTask.BROKER_COST_EFFICIENCY, AiExportDetailLevel.STANDARD), None)
    dumped = response.model_dump_json()

    assert [(note.subject.value, note.source.value) for note in response.domain_notes] == [
        ("asset", "provider_or_user"),
        ("broker", "user"),
    ]
    assert response.facts.positions[0].period_fees_taxes_amount == Currency(code="EUR", amount=Decimal("11.00"))
    assert len(response.facts.contributions) == 1
    assert response.facts.contributions[0].fees_taxes_amount == Currency(code="EUR", amount=Decimal("11.00"))
    assert response.facts.unallocated_contributions[0].unallocated_income_amount == Currency(code="EUR", amount=Decimal("7.00"))
    assert response.facts.unallocated_contributions[0].unallocated_fees_taxes_amount == Currency(code="EUR", amount=Decimal("2.00"))
    assert response.facts.other_period_effects[0].period_pnl_amount == Currency(code="EUR", amount=Decimal("-3.00"))
    assert response.facts.summary.fees_taxes_amount == Currency(code="EUR", amount=Decimal("3.00"))
    assert "<script>asset note</script>" in dumped
    assert "<img onerror=broker> user note" in dumped
    for secret in ("https://private.example/asset", "do not export me", "secret-tag", "secret.csv", "user_url"):
        assert secret not in dumped


@pytest.mark.asyncio
async def test_broker_output_and_stats_are_deterministic_for_reversed_sources():
    assets = [_asset(1), _asset(2), _asset(3)]
    brokers = [_broker(1)]
    holdings = [_holding(3, 1, nav_weight="20", current_value="200"), _holding(1, 1, nav_weight="30", current_value="300"), _holding(2, 1, nav_weight="30", current_value="300")]
    contributions = [_contribution(3, 1), _contribution(1, 1), _contribution(2, 1)]
    report_a = _report(holdings=holdings, contributions=contributions, brokers=brokers)
    report_b = _report(holdings=list(reversed(holdings)), contributions=list(reversed(contributions)), brokers=brokers)
    assembler_a, _service_a, _prices_a, _lots_a, _latest_a = _broker_assembler(
        report_a,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
    )
    assembler_b, _service_b, _prices_b, _lots_b, _latest_b = _broker_assembler(
        report_b,
        assets=assets,
        brokers=brokers,
        technical_preparer=lambda *args, **kwargs: None,
        reverse_metadata=True,
    )

    response_a = await assembler_a.assemble(_prepared_broker(AiExportBrokerTask.BROKER_CONCENTRATION_CONTEXT, AiExportDetailLevel.STANDARD), None)
    response_b = await assembler_b.assemble(_prepared_broker(AiExportBrokerTask.BROKER_CONCENTRATION_CONTEXT, AiExportDetailLevel.STANDARD), None)

    assert response_a.model_dump(mode="json") == response_b.model_dump(mode="json")
    assert [position.asset_id for position in response_a.facts.positions] == [1, 2, 3]
    assert response_a.export_stats.canonical_json.positions == 3
