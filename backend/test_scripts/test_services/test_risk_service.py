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
)
from backend.app.services.risk.service import (
    RiskScopeAccessError,
    RiskService,
    _portfolio_twrr_returns,
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
