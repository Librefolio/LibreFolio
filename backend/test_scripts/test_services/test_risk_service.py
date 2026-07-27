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
    RiskScopeKind,
)
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk.base import RiskAnalytic, RiskComputation
from backend.app.services.risk.service import (
    RiskScopeAccessError,
    RiskService,
    _portfolio_twrr_returns,
    _ScopeInputs,
)


def make_prepared_set(
    returns_by_asset: dict[int, list[float]],
) -> PreparedAssetSeriesSet:
    baseline = date(2026, 1, 1)
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
                        "analytic_code": "portfolio_kpi",
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
        assert query.include_summary is True
        assert query.include_history is True
        return report

    monkeypatch.setattr(PortfolioService, "get_report", fake_get_report)
    service = RiskService(db=object())
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
                    "analytic_code": "portfolio_kpi",
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
    assert baseline == date(2026, 1, 1)
    assert dates == (date(2026, 1, 2), date(2026, 1, 3))
    assert returns == pytest.approx((0.1, -0.05))
    assert calendar_days == 2
    assert annualization == pytest.approx(365)
    assert coverage == pytest.approx(1)


class _MissingAccessResult:
    @staticmethod
    def scalar_one_or_none():
        return None


class _MissingAccessDb:
    async def execute(self, _statement):
        return _MissingAccessResult()


@pytest.mark.asyncio
async def test_broker_scope_requires_explicit_user_access():
    service = RiskService(db=_MissingAccessDb())
    request = RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "broker", "broker_id": 99},
            "date_range": {
                "start": "2026-01-01",
                "end": "2026-01-31",
            },
            "target_currency": "EUR",
            "mode": "historical",
            "analytics": [
                {
                    "instance_id": "kpi",
                    "analytic_code": "portfolio_kpi",
                }
            ],
        }
    )

    with pytest.raises(RiskScopeAccessError, match="not accessible"):
        await service._load_scope_inputs(
            user_id=7,
            request=request,
        )
