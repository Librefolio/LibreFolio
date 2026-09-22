"""Bulk orchestration tests for RiskService."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import BaseModel, ConfigDict

from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityReport,
    PortfolioHistoryPoint,
    PortfolioHolding,
    PortfolioReportResponse,
    PortfolioSummary,
)
from backend.app.schemas.risk import (
    AssetReturnPoint,
    AssetReturnSeries,
    AssetValuationPoint,
    AssetValuationSeries,
    PreparedAssetSeries,
    PreparedAssetSeriesSet,
    RiskAnalyticRequest,
    RiskErrorCode,
    RiskKpiOutput,
    RiskMode,
    RiskOutputKind,
    RiskQueryRequest,
    RiskResultStatus,
    RiskReturnBasis,
    RiskScopeKind,
)
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskAssetClassification,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.service import (
    RiskScopeAccessError,
    RiskScopeNotFoundError,
    RiskService,
    _portfolio_twrr_returns,
    _scope_reference,
    _ScopeInputs,
)


def make_prepared_set(
    returns_by_asset: dict[int, list[float]],
    *,
    baseline: date = date(2026, 1, 1),
) -> PreparedAssetSeriesSet:
    observations = len(next(iter(returns_by_asset.values())))
    valuation_dates = [baseline + timedelta(days=index) for index in range(observations + 1)]
    prepared: list[PreparedAssetSeries] = []
    for asset_id, returns in returns_by_asset.items():
        wealth = Decimal("100")
        valuation_points = [
            AssetValuationPoint(
                valuation_date=baseline,
                effective_price_date=baseline,
                is_price_carried_forward=False,
                native_close=wealth,
                native_currency="EUR",
                target_close=wealth,
                target_currency="EUR",
            )
        ]
        return_points = []
        for previous_date, point_date, value in zip(
            valuation_dates[:-1],
            valuation_dates[1:],
            returns,
            strict=True,
        ):
            wealth *= Decimal(str(1 + value))
            valuation_points.append(
                AssetValuationPoint(
                    valuation_date=point_date,
                    effective_price_date=point_date,
                    is_price_carried_forward=False,
                    native_close=wealth,
                    native_currency="EUR",
                    target_close=wealth,
                    target_currency="EUR",
                )
            )
            return_points.append(
                AssetReturnPoint(
                    date=point_date,
                    previous_valuation_date=previous_date,
                    value=value,
                )
            )
        prepared.append(
            PreparedAssetSeries(
                valuations=AssetValuationSeries(
                    asset_id=asset_id,
                    target_currency="EUR",
                    points=valuation_points,
                ),
                returns=AssetReturnSeries(
                    asset_id=asset_id,
                    target_currency="EUR",
                    points=return_points,
                ),
            )
        )
    return PreparedAssetSeriesSet(
        requested_range=DateRangeModel(
            start=valuation_dates[1],
            end=valuation_dates[-1],
        ),
        baseline_date=baseline,
        effective_range=DateRangeModel(
            start=valuation_dates[1],
            end=valuation_dates[-1],
        ),
        target_currency="EUR",
        series=prepared,
        joint_valuation_dates=valuation_dates,
        joint_return_dates=valuation_dates[1:],
        n_observations=observations,
        calendar_days=observations,
        annualization_factor=365,
        calendar_coverage=1,
        fresh_quote_coverage=1,
        data_quality=DataQualityReport(),
        fx_fingerprint="0" * 64,
    )


def scope_inputs(asset_ids: tuple[int, ...]) -> _ScopeInputs:
    return _ScopeInputs(
        requested_asset_ids=asset_ids,
        weights={},
        asset_values={},
        cash_weight=0,
        scope_value=None,
        portfolio_report=None,
        data_quality=DataQualityReport(),
        warnings=(),
    )


@pytest.mark.asyncio
async def test_bulk_query_isolates_catalog_scope_and_param_errors(monkeypatch):
    service = RiskService(db=object())
    prepared = make_prepared_set(
        {
            1: [0.01, -0.01] * 10,
            2: [-0.01, 0.01] * 10,
        }
    )
    calls = {"scope": 0, "assets": 0, "prepare": 0}

    async def fake_scope(**_kwargs):
        calls["scope"] += 1
        return scope_inputs((1, 2))

    async def fake_assets(_asset_ids):
        calls["assets"] += 1
        return {1, 2}

    async def fake_prepare(**_kwargs):
        calls["prepare"] += 1
        return prepared

    monkeypatch.setattr(service, "_load_scope_inputs", fake_scope)
    monkeypatch.setattr(service, "_existing_asset_ids", fake_assets)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)

    response = await service.execute(
        user_id=7,
        request=RiskQueryRequest.model_validate(
            {
                "scope": {"kind": "asset_set", "asset_ids": [1, 2]},
                "date_range": {
                    "start": "2026-01-02",
                    "end": "2026-01-21",
                },
                "target_currency": "EUR",
                "mode": "historical",
                "analytics": [
                    {
                        "instance_id": "matrix",
                        "analytic_code": "correlation",
                    },
                    {
                        "instance_id": "wrong-scope",
                        "analytic_code": "historical_kpi",
                    },
                    {
                        "instance_id": "bad-params",
                        "analytic_code": "correlation",
                        "parameters": {"min_observations": 1},
                    },
                    {
                        "instance_id": "unknown",
                        "analytic_code": "does_not_exist",
                    },
                ],
            }
        ),
    )

    assert [item.status for item in response.items] == [
        RiskResultStatus.OK,
        RiskResultStatus.UNAVAILABLE,
        RiskResultStatus.UNAVAILABLE,
        RiskResultStatus.UNAVAILABLE,
    ]
    assert response.items[0].output is not None
    assert response.items[1].error.code.value == "incompatible_scope"
    assert response.items[2].error.code.value == "invalid_parameters"
    assert response.items[3].error.code.value == "analytic_not_found"
    assert calls == {"scope": 1, "assets": 1, "prepare": 1}


class EmptyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GoodAnalytic(RiskAnalytic):
    analytic_code = "good_analytic"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.good.name"
    description_i18n_key = "risk.good.description"
    output_kind = RiskOutputKind.KPI
    supported_scopes = (RiskScopeKind.ASSET,)
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = EmptyParams
    min_observations = 2

    def compute(self, params, context):
        return RiskComputation(
            output=RiskKpiOutput(
                volatility=0.1,
                max_drawdown=-0.2,
                max_drawdown_duration_days=3,
            ),
            method="test",
        )


class BrokenAnalytic(GoodAnalytic):
    analytic_code = "broken_analytic"

    def compute(self, params, context):
        raise RuntimeError("isolated failure")


@pytest.mark.asyncio
async def test_runtime_failure_does_not_abort_other_analytics(monkeypatch):
    service = RiskService(db=object())
    prepared = make_prepared_set({1: [0.01, -0.01] * 10})

    async def fake_scope(**_kwargs):
        return scope_inputs((1,))

    async def fake_assets(_asset_ids):
        return {1}

    async def fake_prepare(**_kwargs):
        return prepared

    plugin_map = {
        GoodAnalytic.analytic_code: GoodAnalytic,
        BrokenAnalytic.analytic_code: BrokenAnalytic,
    }
    monkeypatch.setattr(
        RiskAnalyticRegistry,
        "get_plugin",
        classmethod(lambda cls, code: plugin_map.get(code)),
    )
    monkeypatch.setattr(service, "_load_scope_inputs", fake_scope)
    monkeypatch.setattr(service, "_existing_asset_ids", fake_assets)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)

    response = await service.execute(
        user_id=7,
        request=RiskQueryRequest(
            scope={"kind": "asset", "asset_id": 1},
            date_range=prepared.requested_range,
            target_currency="EUR",
            mode=RiskMode.HISTORICAL,
            analytics=[
                RiskAnalyticRequest(
                    instance_id="good",
                    analytic_code=GoodAnalytic.analytic_code,
                ),
                RiskAnalyticRequest(
                    instance_id="broken",
                    analytic_code=BrokenAnalytic.analytic_code,
                ),
            ],
        ),
    )

    assert response.items[0].status == RiskResultStatus.OK
    assert response.items[1].status == RiskResultStatus.FAILED
    assert response.items[1].error.code.value == "execution_failed"


@pytest.mark.asyncio
async def test_historical_replay_uses_dedicated_period_and_proxy_series(
    monkeypatch,
):
    service = RiskService(db=object())
    main_prepared = PreparedAssetSeriesSet(
        requested_range=DateRangeModel(
            start=date(2026, 1, 2),
            end=date(2026, 1, 21),
        ),
        target_currency="EUR",
        data_quality=DataQualityReport(),
        fx_fingerprint="0" * 64,
    )
    replay_prepared = make_prepared_set(
        {3: [0.1] + [0.0] * 19},
        baseline=date(2020, 2, 1),
    )
    prepare_calls = []

    async def fake_scope(**_kwargs):
        return _ScopeInputs(
            requested_asset_ids=(1,),
            weights={1: 1.0},
            asset_values={1: Decimal("100")},
            cash_weight=0.0,
            scope_value=Decimal("100"),
            portfolio_report=None,
            data_quality=DataQualityReport(),
            warnings=(),
            broker_ids=(3,),
            composition_as_of=date(2026, 1, 21),
        )

    async def fake_assets(asset_ids):
        assert asset_ids == {1, 3}
        return {1, 3}

    async def fake_prepare(**kwargs):
        prepare_calls.append(kwargs)
        if kwargs["date_range"].start.year == 2020:
            return replay_prepared
        return main_prepared

    monkeypatch.setattr(service, "_load_scope_inputs", fake_scope)
    monkeypatch.setattr(service, "_existing_asset_ids", fake_assets)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)

    response = await service.execute(
        user_id=7,
        request=RiskQueryRequest.model_validate(
            {
                "scope": {"kind": "portfolio", "broker_ids": [3]},
                "date_range": {
                    "start": "2026-01-02",
                    "end": "2026-01-21",
                },
                "target_currency": "EUR",
                "mode": "current_composition",
                "composition_policy": "current_buy_and_hold",
                "analytics": [
                    {
                        "instance_id": "replay",
                        "analytic_code": "stress",
                        "parameters": {
                            "method": "historical_replay",
                            "replay_range": {
                                "start": "2020-02-02",
                                "end": "2020-02-21",
                            },
                            "proxy_assets": [
                                {
                                    "asset_id": 1,
                                    "proxy_asset_id": 3,
                                }
                            ],
                        },
                    }
                ],
            }
        ),
    )

    result = response.items[0]
    assert result.status == RiskResultStatus.PARTIAL
    assert result.output.portfolio_return == pytest.approx(0.1)
    assert result.output.impacts[0].asset_id == 1
    assert result.output.impacts[0].return_source_asset_id == 3
    assert result.metadata.composition_as_of == date(2026, 1, 21)
    assert result.metadata.analyzed_range == replay_prepared.effective_range
    assert result.metadata.historical_replay_audit.proxy_count == 1
    assert [call["asset_ids"] for call in prepare_calls] == [(1,), (3,)]
    assert [call["date_range"].start.year for call in prepare_calls] == [
        2026,
        2020,
    ]


@pytest.mark.asyncio
async def test_historical_replay_rejects_missing_proxy_explicitly(monkeypatch):
    service = RiskService(db=object())
    prepared = make_prepared_set({1: [0.0] * 20})
    prepare_calls = 0

    async def fake_scope(**_kwargs):
        return scope_inputs((1,))

    async def fake_assets(_asset_ids):
        return {1}

    async def fake_prepare(**_kwargs):
        nonlocal prepare_calls
        prepare_calls += 1
        return prepared

    monkeypatch.setattr(service, "_load_scope_inputs", fake_scope)
    monkeypatch.setattr(service, "_existing_asset_ids", fake_assets)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)

    response = await service.execute(
        user_id=7,
        request=RiskQueryRequest.model_validate(
            {
                "scope": {"kind": "asset", "asset_id": 1},
                "date_range": {
                    "start": "2026-01-02",
                    "end": "2026-01-21",
                },
                "target_currency": "EUR",
                "mode": "current_composition",
                "composition_policy": "current_buy_and_hold",
                "analytics": [
                    {
                        "instance_id": "replay",
                        "analytic_code": "stress",
                        "parameters": {
                            "method": "historical_replay",
                            "replay_range": {
                                "start": "2020-02-02",
                                "end": "2020-02-21",
                            },
                            "proxy_assets": [
                                {
                                    "asset_id": 1,
                                    "proxy_asset_id": 99,
                                }
                            ],
                        },
                    }
                ],
            }
        ),
    )

    result = response.items[0]
    assert result.status == RiskResultStatus.UNAVAILABLE
    assert result.error.code.value == "invalid_parameters"
    assert result.error.details == {"proxy_asset_ids": [99]}
    assert prepare_calls == 1


@pytest.mark.asyncio
async def test_hypothetical_stress_uses_classification_context_without_partial_status(
    monkeypatch,
):
    service = RiskService(db=object())
    prepared = make_prepared_set({1: [0.0] * 20})

    async def fake_scope(**_kwargs):
        return scope_inputs((1,))

    async def fake_assets(_asset_ids):
        return {1}

    async def fake_prepare(**_kwargs):
        return prepared

    async def fake_classifications(_asset_ids):
        return {
            1: RiskAssetClassification(
                asset_class="ETF",
            )
        }

    monkeypatch.setattr(service, "_load_scope_inputs", fake_scope)
    monkeypatch.setattr(service, "_existing_asset_ids", fake_assets)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)
    monkeypatch.setattr(
        service,
        "_load_asset_classifications",
        fake_classifications,
    )
    monkeypatch.setattr(
        service,
        "_geography_group_members",
        lambda: {"european_union": frozenset({"ITA"})},
    )

    response = await service.execute(
        user_id=7,
        request=RiskQueryRequest.model_validate(
            {
                "scope": {"kind": "asset_set", "asset_ids": [1]},
                "date_range": {
                    "start": "2026-01-02",
                    "end": "2026-01-21",
                },
                "target_currency": "EUR",
                "mode": "current_composition",
                "composition_policy": "current_buy_and_hold",
                "analytics": [
                    {
                        "instance_id": "shock",
                        "analytic_code": "stress",
                        "parameters": {
                            "method": "hypothetical",
                            "dimension": "sector",
                            "bucket_shocks": {"Other": -0.2},
                        },
                    }
                ],
            }
        ),
    )

    result = response.items[0]
    assert result.status == RiskResultStatus.OK
    assert result.output.dimension.value == "sector"
    assert result.output.impacts[0].shock_return == pytest.approx(-0.2)
    assert result.output.impacts[0].metadata_fallback is True
    assert result.metadata.params["bucket_shocks"] == {"Other": -0.2}
    assert result.metadata.n_observations == 0
    assert result.warnings[0].code == "hypothetical_metadata_other_fallback"
    assert result.warnings[0].degrades_result is False


@pytest.mark.asyncio
async def test_portfolio_scope_reuses_one_report_for_weights_and_twrr(monkeypatch):
    report = PortfolioReportResponse.model_construct(
        summary=PortfolioSummary.model_construct(
            net_worth=Currency(code="EUR", amount=Decimal("200")),
            cash_total=Currency(code="EUR", amount=Decimal("50")),
            in_transit_market_value=Currency(code="EUR", amount=Decimal("0")),
            holdings=[
                PortfolioHolding.model_construct(
                    asset_id=1,
                    current_value=Decimal("100"),
                ),
                PortfolioHolding.model_construct(
                    asset_id=2,
                    current_value=Decimal("50"),
                ),
            ],
        ),
        history=[
            PortfolioHistoryPoint.model_construct(
                date=date(2026, 1, 1),
                twrr=Decimal("0"),
            ),
            PortfolioHistoryPoint.model_construct(
                date=date(2026, 1, 2),
                twrr=Decimal("0.1"),
            ),
            PortfolioHistoryPoint.model_construct(
                date=date(2026, 1, 3),
                twrr=Decimal("0.045"),
            ),
        ],
        data_quality=DataQualityReport(),
    )
    calls = {"report": 0}

    async def fake_get_report(_self, *, user_id, query):
        calls["report"] += 1
        assert user_id == 7
        assert query.broker_ids is None
        assert query.include_summary is True
        assert query.include_history is True
        return report

    monkeypatch.setattr(PortfolioService, "get_report", fake_get_report)
    service = RiskService(db=object())

    async def fake_accessible_broker_ids(_user_id):
        return (3, 5)

    monkeypatch.setattr(service, "_accessible_broker_ids", fake_accessible_broker_ids)
    request = RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "portfolio"},
            "date_range": {
                "start": "2026-01-01",
                "end": "2026-01-03",
            },
            "target_currency": "EUR",
            "mode": "historical",
            "analytics": [
                {
                    "instance_id": "kpi",
                    "analytic_code": "historical_kpi",
                }
            ],
        }
    )

    inputs = await service._load_scope_inputs(
        user_id=7,
        request=request,
    )
    baseline, dates, returns, calendar_days, annualization, coverage = _portfolio_twrr_returns(report)

    assert calls["report"] == 1
    assert inputs.weights == pytest.approx({1: 0.5, 2: 0.25})
    assert inputs.cash_weight == pytest.approx(0.25)
    assert inputs.broker_ids == (3, 5)
    assert inputs.composition_as_of == date(2026, 1, 3)
    assert baseline == date(2026, 1, 1)
    assert dates == (date(2026, 1, 2), date(2026, 1, 3))
    assert returns == pytest.approx((0.1, -0.05))
    assert calendar_days == 2
    assert annualization == pytest.approx(365)
    assert coverage == pytest.approx(1)


@pytest.mark.asyncio
async def test_asset_historical_kpi_uses_canonical_close_returns(monkeypatch):
    service = RiskService(db=object())
    prepared = make_prepared_set({1: [0.01, -0.005] * 10})

    async def fake_scope(**_kwargs):
        return scope_inputs((1,))

    async def fake_assets(_asset_ids):
        return {1}

    async def fake_prepare(**_kwargs):
        return prepared

    monkeypatch.setattr(service, "_load_scope_inputs", fake_scope)
    monkeypatch.setattr(service, "_existing_asset_ids", fake_assets)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)

    response = await service.execute(
        user_id=7,
        request=RiskQueryRequest.model_validate(
            {
                "scope": {"kind": "asset", "asset_id": 1},
                "date_range": {
                    "start": "2026-01-02",
                    "end": "2026-01-21",
                },
                "target_currency": "EUR",
                "mode": "historical",
                "analytics": [
                    {
                        "instance_id": "kpi",
                        "analytic_code": "historical_kpi",
                    }
                ],
            }
        ),
    )

    result = response.items[0]
    assert result.status == RiskResultStatus.OK
    assert result.output is not None
    assert result.output.kind.value == "kpi"
    assert result.metadata is not None
    assert result.metadata.scope == RiskScopeKind.ASSET
    assert result.metadata.return_basis == RiskReturnBasis.PRICE_ONLY
    assert result.metadata.method == "historical_close_returns"


@pytest.mark.asyncio
async def test_portfolio_subset_requires_exact_user_access(monkeypatch):
    service = RiskService(db=object())

    async def fake_accessible_broker_ids(_user_id):
        return (3, 5)

    monkeypatch.setattr(service, "_accessible_broker_ids", fake_accessible_broker_ids)
    request = RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "portfolio", "broker_ids": [5, 99]},
            "date_range": {
                "start": "2026-01-01",
                "end": "2026-01-31",
            },
            "target_currency": "EUR",
            "mode": "historical",
            "analytics": [
                {
                    "instance_id": "kpi",
                    "analytic_code": "historical_kpi",
                }
            ],
        }
    )

    with pytest.raises(RiskScopeAccessError, match="not fully accessible: 99"):
        await service._load_scope_inputs(
            user_id=7,
            request=request,
        )


# ---------------------------------------------------------------------------
# Portfolio asset slicing (PortfolioRiskScope.asset_ids)
# ---------------------------------------------------------------------------


class ForbiddenDb:
    """Session double that fails if scope resolution touches the database.

    The asset slice is resolved by intersecting the request with the holdings of
    the portfolio report, never by querying ``Asset``: the report is what the
    broker-access check already filtered. A direct asset lookup would hand back
    rows no broker of the user holds, so any DB access here is a contract
    violation rather than an implementation detail.
    """

    def __getattr__(self, name: str):
        raise AssertionError(f"scope resolution must not touch the database (attempted '{name}')")


def slice_report(
    *,
    holdings: dict[int, str],
    cash: str = "0",
    in_transit: str = "0",
    net_worth: str | None = None,
    twrr: list[tuple[date, Decimal]] | None = None,
) -> PortfolioReportResponse:
    """Build the portfolio report the risk scope reads, with explicit money."""
    holdings_total = sum((Decimal(value) for value in holdings.values()), Decimal("0"))
    total = Decimal(net_worth) if net_worth is not None else holdings_total + Decimal(cash)
    return PortfolioReportResponse.model_construct(
        summary=PortfolioSummary.model_construct(
            net_worth=Currency(code="EUR", amount=total),
            cash_total=Currency(code="EUR", amount=Decimal(cash)),
            in_transit_market_value=Currency(code="EUR", amount=Decimal(in_transit)),
            holdings=[
                PortfolioHolding.model_construct(
                    asset_id=asset_id,
                    current_value=Decimal(value),
                )
                for asset_id, value in holdings.items()
            ],
        ),
        history=[PortfolioHistoryPoint.model_construct(date=point_date, twrr=value) for point_date, value in (twrr or [])],
        data_quality=DataQualityReport(),
    )


def twrr_history(
    returns: list[float],
    *,
    start: date = date(2026, 1, 1),
) -> list[tuple[date, Decimal]]:
    """Cumulative daily TWRR points whose period returns are exactly `returns`."""
    points = [(start, Decimal("0"))]
    wealth = Decimal("1")
    for index, value in enumerate(returns, start=1):
        wealth *= Decimal("1") + Decimal(str(value))
        points.append((start + timedelta(days=index), wealth - Decimal("1")))
    return points


def install_portfolio_report(
    monkeypatch,
    service: RiskService,
    report: PortfolioReportResponse,
    *,
    accessible_broker_ids: tuple[int, ...] = (3, 5),
) -> dict[str, object]:
    """Serve one fixed report and record how the scope asked for it."""
    calls: dict[str, object] = {"report": 0, "broker_ids": []}

    async def fake_get_report(_self, *, user_id, query):
        calls["report"] = int(calls["report"]) + 1
        calls["user_id"] = user_id
        calls["broker_ids"].append(query.broker_ids)
        return report

    async def fake_accessible_broker_ids(_user_id):
        return accessible_broker_ids

    monkeypatch.setattr(PortfolioService, "get_report", fake_get_report)
    monkeypatch.setattr(service, "_accessible_broker_ids", fake_accessible_broker_ids)
    return calls


def install_prepared_series(
    monkeypatch,
    service: RiskService,
    prepared: PreparedAssetSeriesSet,
) -> None:
    """Skip price/FX I/O: the slice is decided before series preparation."""

    async def fake_existing_asset_ids(asset_ids):
        return set(asset_ids)

    async def fake_prepare(**_kwargs):
        return prepared

    monkeypatch.setattr(service, "_existing_asset_ids", fake_existing_asset_ids)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)


def slice_request(
    *,
    mode: str = "current_composition",
    asset_ids: list[int] | None = None,
    broker_ids: list[int] | None = None,
    analytics: list[dict[str, object]] | None = None,
    start: date = date(2026, 1, 1),
    end: date = date(2026, 1, 21),
) -> RiskQueryRequest:
    """Portfolio-scope request, optionally sliced to an asset subset."""
    scope: dict[str, object] = {"kind": "portfolio"}
    if asset_ids is not None:
        scope["asset_ids"] = asset_ids
    if broker_ids is not None:
        scope["broker_ids"] = broker_ids
    default_analytic = "risk_contribution" if mode == "current_composition" else "historical_kpi"
    payload: dict[str, object] = {
        "scope": scope,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "target_currency": "EUR",
        "mode": mode,
        "analytics": analytics or [{"instance_id": "main", "analytic_code": default_analytic}],
    }
    if mode == "current_composition":
        payload["composition_policy"] = "current_buy_and_hold"
    return RiskQueryRequest.model_validate(payload)


@pytest.mark.asyncio
async def test_portfolio_slice_renormalizes_weights_and_scope_value_to_the_slice(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(
            holdings={1: "100", 2: "300", 3: "100"},
            cash="100",
        ),
    )

    inputs = await service._load_scope_inputs(
        user_id=7,
        request=slice_request(asset_ids=[3, 1]),
    )

    assert inputs.slice_asset_ids == (1, 3)
    assert inputs.requested_asset_ids == (1, 3)
    assert set(inputs.asset_values) == {1, 3}
    assert inputs.asset_values[1] == Decimal("100")
    assert inputs.asset_values[3] == Decimal("100")
    assert inputs.scope_value == Decimal("200")
    assert inputs.weights == pytest.approx({1: 0.5, 3: 0.5})
    assert sum(inputs.weights.values()) == pytest.approx(1.0)
    assert inputs.cash_weight == pytest.approx(0.0)
    assert inputs.composition_error is None


@pytest.mark.asyncio
async def test_unsliced_portfolio_scope_keeps_net_worth_denominator_and_cash_residual(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(
            holdings={1: "100", 2: "300", 3: "100"},
            cash="100",
        ),
    )

    inputs = await service._load_scope_inputs(
        user_id=7,
        request=slice_request(),
    )

    assert inputs.slice_asset_ids == ()
    assert inputs.requested_asset_ids == (1, 2, 3)
    assert inputs.scope_value == Decimal("600")
    assert inputs.weights == pytest.approx({1: 1 / 6, 2: 0.5, 3: 1 / 6})
    assert inputs.cash_weight == pytest.approx(1 / 6)


@pytest.mark.asyncio
async def test_portfolio_slice_ignores_requested_assets_that_are_not_held(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(holdings={1: "100", 2: "300"}),
    )

    inputs = await service._load_scope_inputs(
        user_id=7,
        request=slice_request(asset_ids=[1, 77, 99]),
    )

    warning = next(item for item in inputs.warnings if item.code == "slice_assets_not_held")
    assert warning.details["asset_ids"] == [77, 99]
    # The user asked for something they do not hold: the answer is still produced,
    # but it is a degraded (PARTIAL) one, not a silently smaller slice.
    assert warning.degrades_result is True
    assert inputs.slice_asset_ids == (1,)
    assert inputs.requested_asset_ids == (1,)
    assert inputs.weights == pytest.approx({1: 1.0})
    assert inputs.scope_value == Decimal("100")


@pytest.mark.asyncio
async def test_portfolio_slice_without_any_held_asset_is_not_found(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(holdings={1: "100", 2: "300"}),
    )

    with pytest.raises(RiskScopeNotFoundError, match=r"\[77, 99\]"):
        await service._load_scope_inputs(
            user_id=7,
            request=slice_request(asset_ids=[99, 77]),
        )


@pytest.mark.asyncio
async def test_portfolio_slice_never_reaches_an_asset_outside_the_accessible_report(monkeypatch):
    holdings_by_broker = {3: {1: "100", 2: "300"}, 9: {42: "1000"}}
    accessible_broker_ids = (3,)
    seen_broker_ids: list[list[int] | None] = []

    async def fake_get_report(_self, *, user_id, query):
        del user_id
        seen_broker_ids.append(query.broker_ids)
        visible = query.broker_ids if query.broker_ids is not None else list(accessible_broker_ids)
        holdings: dict[int, str] = {}
        for broker_id in visible:
            holdings.update(holdings_by_broker.get(broker_id, {}))
        return slice_report(holdings=holdings)

    async def fake_accessible_broker_ids(_user_id):
        return accessible_broker_ids

    service = RiskService(db=ForbiddenDb())
    monkeypatch.setattr(PortfolioService, "get_report", fake_get_report)
    monkeypatch.setattr(service, "_accessible_broker_ids", fake_accessible_broker_ids)

    inputs = await service._load_scope_inputs(
        user_id=7,
        request=slice_request(asset_ids=[1, 42]),
    )

    assert seen_broker_ids == [None]
    assert inputs.broker_ids == (3,)
    assert inputs.slice_asset_ids == (1,)
    assert 42 not in inputs.asset_values
    assert 42 not in inputs.weights
    warning = next(item for item in inputs.warnings if item.code == "slice_assets_not_held")
    assert warning.details["asset_ids"] == [42]


def test_scope_reference_encodes_the_asset_slice_of_a_portfolio_scope():
    unsliced = _scope_reference(slice_request(), broker_ids=(3, 5))
    first_slice = _scope_reference(
        slice_request(asset_ids=[2, 1]),
        broker_ids=(3, 5),
        slice_asset_ids=(2, 1),
    )
    second_slice = _scope_reference(
        slice_request(asset_ids=[1, 3]),
        broker_ids=(3, 5),
        slice_asset_ids=(1, 3),
    )

    assert unsliced == "portfolio:3,5"
    assert first_slice == "portfolio:3,5/assets:1,2"
    assert second_slice == "portfolio:3,5/assets:1,3"
    assert first_slice != second_slice
    assert _scope_reference(slice_request(asset_ids=[1]), slice_asset_ids=(1,)) == "portfolio:none/assets:1"


@pytest.mark.asyncio
async def test_portfolio_slice_changes_the_current_composition_result(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(
            holdings={1: "100", 2: "200", 3: "100"},
            cash="100",
        ),
    )
    install_prepared_series(
        monkeypatch,
        service,
        make_prepared_set(
            {
                1: [0.012, -0.004, 0.003, -0.011] * 5,
                2: [-0.006, 0.009, -0.002, 0.007] * 5,
                3: [0.001, 0.002, -0.015, 0.004] * 5,
            }
        ),
    )

    whole = (await service.execute(user_id=7, request=slice_request())).items[0]
    sliced = (await service.execute(user_id=7, request=slice_request(asset_ids=[1, 2]))).items[0]

    assert whole.status == RiskResultStatus.OK
    assert sliced.status == RiskResultStatus.OK
    assert {item.asset_id for item in whole.output.items} == {1, 2, 3}
    assert {item.asset_id for item in sliced.output.items} == {1, 2}
    assert whole.output.cash_weight == pytest.approx(0.2)
    assert sliced.output.cash_weight == pytest.approx(0.0)
    assert {item.asset_id: item.weight for item in sliced.output.items} == pytest.approx({1: 1 / 3, 2: 2 / 3})
    assert sum(item.weight for item in sliced.output.items) == pytest.approx(1.0)
    # The point of the whole change: a proper slice is a different portfolio.
    assert sliced.output.portfolio_volatility != pytest.approx(whole.output.portfolio_volatility)
    assert sliced.metadata.sliced_asset_ids == [1, 2]
    assert whole.metadata.sliced_asset_ids is None
    assert sliced.metadata.scope_reference == "portfolio:3,5/assets:1,2"
    assert whole.metadata.scope_reference == "portfolio:3,5"
    assert sliced.metadata.scope == RiskScopeKind.PORTFOLIO
    assert sliced.metadata.broker_ids == [3, 5]
    # risk_contribution never consumes the composite series: it works on weights and the
    # per-asset series, so it reports that series' own basis. The composition backtest
    # basis belongs to the results that actually replay the weighted series.
    assert whole.metadata.return_basis == RiskReturnBasis.PRICE_ONLY
    assert sliced.metadata.return_basis == RiskReturnBasis.PRICE_ONLY


@pytest.mark.asyncio
async def test_portfolio_slice_changes_the_historical_result_and_leaves_twrr(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(
            holdings={1: "100", 2: "300"},
            cash="100",
            twrr=twrr_history([0.004, -0.002, 0.006, -0.005] * 5),
        ),
    )
    install_prepared_series(
        monkeypatch,
        service,
        make_prepared_set(
            {
                1: [0.012, -0.004, 0.003, -0.011] * 5,
                2: [-0.006, 0.009, -0.002, 0.007] * 5,
            }
        ),
    )

    whole = (await service.execute(user_id=7, request=slice_request(mode="historical"))).items[0]
    sliced = (
        await service.execute(
            user_id=7,
            request=slice_request(mode="historical", asset_ids=[1]),
        )
    ).items[0]

    assert whole.status == RiskResultStatus.OK
    assert sliced.status == RiskResultStatus.OK
    # Unsliced keeps the portfolio TWRR; a slice cannot be filtered out of it.
    assert whole.metadata.return_basis == RiskReturnBasis.TWRR
    assert whole.metadata.method == "historical_twrr"
    assert sliced.metadata.return_basis == RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST
    # `method` names the series, not the requested mode. A slice asked for in
    # `historical` cannot be filtered out of the report's TWRR, so the backend rebuilds
    # it from today's weights — the basis above has always said so, and the method now
    # agrees instead of calling a backtest "close returns". Two identical series may not
    # carry different method names just because they were reached through different modes.
    assert sliced.metadata.method == "current_composition_backtest"
    assert sliced.output.volatility != pytest.approx(whole.output.volatility)
    assert sliced.metadata.sliced_asset_ids == [1]
    assert whole.metadata.sliced_asset_ids is None
    assert sliced.metadata.scope_reference == "portfolio:3,5/assets:1"
    assert whole.metadata.scope_reference == "portfolio:3,5"


@pytest.mark.asyncio
async def test_sliced_historical_context_replays_the_slice_instead_of_portfolio_twrr(monkeypatch):
    asset_returns = {
        1: [0.012, -0.004, 0.003],
        2: [-0.006, 0.009, -0.002],
    }
    report = slice_report(
        holdings={1: "100", 2: "300"},
        cash="100",
        twrr=twrr_history([0.004, -0.002, 0.006]),
    )
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(monkeypatch, service, report)
    prepared = make_prepared_set(asset_returns)

    whole_request = slice_request(mode="historical")
    sliced_request = slice_request(mode="historical", asset_ids=[1])
    full_slice_request = slice_request(mode="historical", asset_ids=[1, 2])
    whole_context = service._build_context(
        request=whole_request,
        scope_inputs=await service._load_scope_inputs(user_id=7, request=whole_request),
        prepared=prepared,
    )
    sliced_context = service._build_context(
        request=sliced_request,
        scope_inputs=await service._load_scope_inputs(user_id=7, request=sliced_request),
        prepared=prepared,
    )
    full_slice_context = service._build_context(
        request=full_slice_request,
        scope_inputs=await service._load_scope_inputs(user_id=7, request=full_slice_request),
        prepared=prepared,
    )
    twrr_returns = _portfolio_twrr_returns(report)[2]

    assert whole_context.primary_return_basis == RiskReturnBasis.TWRR
    assert whole_context.primary_returns == pytest.approx(twrr_returns)
    assert sliced_context.primary_return_basis == RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST
    assert sliced_context.primary_returns == pytest.approx(tuple(asset_returns[1]))
    assert sliced_context.primary_returns != pytest.approx(twrr_returns)
    assert sliced_context.sliced_asset_ids == (1,)
    assert whole_context.sliced_asset_ids == ()
    # Even a slice that names every held asset stays off TWRR: it renormalizes cash
    # away, so the portfolio's own TWRR no longer describes what it holds. The basis
    # names the series it did consume, so the UI never has to infer the backtest.
    assert full_slice_context.primary_return_basis == RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST
    assert full_slice_context.primary_returns != pytest.approx(twrr_returns)


@pytest.mark.asyncio
async def test_full_slice_matches_the_unsliced_scope_when_no_cash_is_held(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(holdings={1: "100", 2: "300"}),
    )
    prepared = make_prepared_set(
        {
            1: [0.012, -0.004, 0.003],
            2: [-0.006, 0.009, -0.002],
        }
    )

    whole_request = slice_request()
    sliced_request = slice_request(asset_ids=[1, 2])
    whole_inputs = await service._load_scope_inputs(user_id=7, request=whole_request)
    sliced_inputs = await service._load_scope_inputs(user_id=7, request=sliced_request)
    whole_context = service._build_context(
        request=whole_request,
        scope_inputs=whole_inputs,
        prepared=prepared,
    )
    sliced_context = service._build_context(
        request=sliced_request,
        scope_inputs=sliced_inputs,
        prepared=prepared,
    )

    assert sliced_inputs.scope_value == whole_inputs.scope_value
    assert sliced_inputs.weights == pytest.approx(whole_inputs.weights)
    assert sliced_inputs.cash_weight == pytest.approx(whole_inputs.cash_weight)
    assert sliced_context.primary_returns == pytest.approx(whole_context.primary_returns)
    # Same numbers, different provenance: the result still declares it is a slice.
    assert sliced_context.sliced_asset_ids == (1, 2)
    assert whole_context.sliced_asset_ids == ()
    assert sliced_context.scope_reference != whole_context.scope_reference


@pytest.mark.asyncio
async def test_sliced_asset_without_usable_history_stays_a_zero_return_residual(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(
            holdings={1: "100", 2: "100"},
            cash="200",
        ),
    )
    asset_one_returns = [0.012, -0.004, 0.003]
    prepared = make_prepared_set({1: asset_one_returns})

    request = slice_request(asset_ids=[1, 2])
    inputs = await service._load_scope_inputs(user_id=7, request=request)
    context = service._build_context(
        request=request,
        scope_inputs=inputs,
        prepared=prepared,
    )

    # User choice renormalizes: the slice is 100% of itself, cash excluded.
    assert inputs.scope_value == Decimal("200")
    assert inputs.weights == pytest.approx({1: 0.5, 2: 0.5})
    assert sum(inputs.weights.values()) == pytest.approx(1.0)
    assert inputs.cash_weight == pytest.approx(0.0)
    # Missing data does not renormalize: it becomes a zero-return residual (G6).
    assert context.weights == pytest.approx({1: 0.5, 2: 0.5})
    assert context.scope_asset_ids == (1,)
    assert context.requested_scope_asset_ids == (1, 2)
    assert context.cash_weight == pytest.approx(0.5)
    assert [item.asset_id for item in context.excluded_assets] == [2]
    assert "assets_excluded" in {warning.code for warning in context.execution_warnings}
    # Half the slice sits at zero return, so the replay is damped, not rescaled.
    assert context.primary_returns[0] == pytest.approx(0.5 * asset_one_returns[0])
    assert context.primary_returns != pytest.approx(tuple(asset_one_returns))


@pytest.mark.asyncio
async def test_worthless_slice_fails_on_its_own_value_not_on_net_worth(monkeypatch):
    service = RiskService(db=ForbiddenDb())
    install_portfolio_report(
        monkeypatch,
        service,
        slice_report(
            holdings={1: "0", 2: "300"},
            cash="100",
        ),
    )

    sliced = await service._load_scope_inputs(user_id=7, request=slice_request(asset_ids=[1]))
    whole = await service._load_scope_inputs(user_id=7, request=slice_request())

    # The denominator is the slice, so a worthless slice has no composition at all,
    # even though the portfolio it comes from is worth 400.
    assert sliced.scope_value == Decimal("0")
    assert sliced.weights == {}
    assert sliced.composition_error == "Current composition requires positive slice value"
    assert whole.scope_value == Decimal("400")
    assert whole.composition_error is None


# ---------------------------------------------------------------------------
# A failure the plugin did not declare is OURS, not a verdict on the user's data
# ---------------------------------------------------------------------------


class ValueErrorAnalytic(GoodAnalytic):
    """A violated internal invariant, which is what a bare ValueError means here."""

    analytic_code = "value_error_analytic"

    def compute(self, params, context):
        raise ValueError("covariance matrix is not symmetric")


class DeclaredUndefinedAnalytic(GoodAnalytic):
    """A metric a plugin DECLARES undefined, through the documented mechanism."""

    analytic_code = "declared_undefined_analytic"

    def compute(self, params, context):
        raise RiskUnavailableError(
            "the ratio has no denominator for this window",
            code=RiskErrorCode.UNDEFINED_METRIC,
        )


@pytest.mark.asyncio
async def test_undeclared_value_error_is_reported_as_ours_while_a_declared_one_survives(monkeypatch):
    """The two halves of the same rule, asserted together on purpose.

    `ValueError` used to be caught one branch earlier than `Exception` and
    answered with `UNDEFINED_METRIC` -- "The metric is undefined for these
    data." -- and without any log. So a violated invariant was delivered as a
    statement about the user's portfolio: unfixable for them, and invisible to
    us. Nobody files a bug against a limitation they have been told is theirs.

    Removing that branch must remove the PRESUMPTION without removing the
    CAPABILITY, which is why both analytics run in one query:

      * the undeclared `ValueError` must now read `execution_failed`;
      * a plugin that deliberately declares `UNDEFINED_METRIC` must still get
        it, unchanged.

    Asserted in a single response because that is the pair that can regress:
    re-adding a blanket `except ValueError` would keep the second assertion
    green while silently breaking the first.
    """
    service = RiskService(db=object())
    prepared = make_prepared_set({1: [0.01, -0.01] * 10})

    async def fake_scope(**_kwargs):
        return scope_inputs((1,))

    async def fake_assets(_asset_ids):
        return {1}

    async def fake_prepare(**_kwargs):
        return prepared

    plugin_map = {
        ValueErrorAnalytic.analytic_code: ValueErrorAnalytic,
        DeclaredUndefinedAnalytic.analytic_code: DeclaredUndefinedAnalytic,
        GoodAnalytic.analytic_code: GoodAnalytic,
    }
    monkeypatch.setattr(
        RiskAnalyticRegistry,
        "get_plugin",
        classmethod(lambda cls, code: plugin_map.get(code)),
    )
    monkeypatch.setattr(service, "_load_scope_inputs", fake_scope)
    monkeypatch.setattr(service, "_existing_asset_ids", fake_assets)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)

    response = await service.execute(
        user_id=7,
        request=RiskQueryRequest(
            scope={"kind": "asset", "asset_id": 1},
            date_range=prepared.requested_range,
            target_currency="EUR",
            mode=RiskMode.HISTORICAL,
            analytics=[
                RiskAnalyticRequest(instance_id="undeclared", analytic_code=ValueErrorAnalytic.analytic_code),
                RiskAnalyticRequest(instance_id="declared", analytic_code=DeclaredUndefinedAnalytic.analytic_code),
                RiskAnalyticRequest(instance_id="fine", analytic_code=GoodAnalytic.analytic_code),
            ],
        ),
    )

    undeclared, declared, fine = response.items
    assert undeclared.status == RiskResultStatus.FAILED
    assert undeclared.error.code == RiskErrorCode.EXECUTION_FAILED
    # The internal sentence stays server-side. It reached the payload before,
    # under a code saying the data were at fault -- prose the client never
    # renders anyway, since it translates the CODE. The traceback goes to the
    # log, where it can be acted on; only `error_type` crosses the wire.
    assert "covariance" not in undeclared.error.message
    assert undeclared.error.details == {"error_type": "ValueError"}

    # The declared refusal is untouched: same exception base class, opposite
    # treatment, because this one carries an intent.
    assert declared.status == RiskResultStatus.UNAVAILABLE
    assert declared.error.code == RiskErrorCode.UNDEFINED_METRIC

    # And neither failure aborts the query for its neighbours.
    assert fine.status == RiskResultStatus.OK
