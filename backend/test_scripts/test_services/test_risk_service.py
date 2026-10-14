"""Bulk orchestration tests for RiskService."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import BaseModel, ConfigDict

from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityExcludedAsset,
    DataQualityExclusionReason,
    DataQualityReport,
    DataQualityStatus,
    MissingPriceAsset,
    PortfolioHistoryPoint,
    PortfolioHolding,
    PortfolioReportResponse,
    PortfolioSummary,
    StalePriceAsset,
)
from backend.app.schemas.risk import (
    AssetReturnPoint,
    AssetReturnSeries,
    AssetValuationPoint,
    AssetValuationSeries,
    PreparedAssetSeries,
    PreparedAssetSeriesSet,
    RiskAnalyticRequest,
    RiskAnalyticResult,
    RiskError,
    RiskErrorCode,
    RiskExcludedAsset,
    RiskFreeReference,
    RiskKpiOutput,
    RiskMode,
    RiskOutputKind,
    RiskQueryRequest,
    RiskResultStatus,
    RiskReturnBasis,
    RiskScopeKind,
    RiskWarning,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk import service as risk_service_module
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskAssetClassification,
    RiskComputation,
    RiskExecutionContext,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import annualized_sharpe, annualized_sortino, beta, pearson_correlation
from backend.app.services.risk.service import (
    RiskScopeAccessError,
    RiskScopeNotFoundError,
    RiskService,
    _assets_excluded_warnings,
    _data_quality_warnings,
    _portfolio_twrr_returns,
    _scope_reference,
    _ScopeInputs,
)


class NamesDb:
    """Stands in for the session where the only query is the warning-name lookup.

    `_with_warning_asset_names` reads `(Asset.id, Asset.display_name)` for the ids its warnings
    name; this answers from a dict and records the ids of every lookup, so a test can say how many
    queries were issued and for which assets.
    """

    def __init__(self, names: dict[int, str]) -> None:
        self.names = names
        self.lookups: list[list[int]] = []

    async def execute(self, statement):
        (requested,) = statement.compile().params.values()
        self.lookups.append(list(requested))
        return _Rows([(asset_id, self.names[asset_id]) for asset_id in requested if asset_id in self.names])


class _Rows:
    def __init__(self, rows: list[tuple[int, str]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[int, str]]:
        return list(self._rows)


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
    names_db = NamesDb({1: "Original asset", 3: "Proxy asset"})
    service = RiskService(db=names_db)
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

    coverage_probes = []

    async def fake_window_facts(session, **kwargs):
        # The automatic exclusion reads each asset's own quotes over the replay window. A proxied
        # asset replays through its proxy, which the user chose explicitly: it is never probed.
        assert session is names_db
        coverage_probes.append(kwargs)
        return {}

    # The holiday table the request awaits once: Presidents' Day 2020, inside the replay window.
    served_holidays = frozenset({date(2020, 2, 17)})

    async def serve_holidays() -> frozenset[date]:
        return served_holidays

    monkeypatch.setattr(service, "_load_scope_inputs", fake_scope)
    monkeypatch.setattr(service, "_existing_asset_ids", fake_assets)
    monkeypatch.setattr(service, "_prepare_asset_series", fake_prepare)
    monkeypatch.setattr(risk_service_module, "load_price_window_facts", fake_window_facts)
    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", serve_holidays)

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
    # The coverage probe runs over the replay window, not the analysis period, with the request's
    # holiday table, and leaves the proxied asset out; nothing is excluded automatically.
    assert coverage_probes == [
        {
            "asset_ids": [],
            "window_start": date(2020, 2, 2),
            "window_end": date(2020, 2, 21),
            "target_currency": "EUR",
            "market_holidays": served_holidays,
        }
    ]
    assert result.metadata.historical_replay_audit.excluded_assets == []
    # The proxy warning names the asset it stands in for, from one lookup for the whole response.
    (proxy_warning,) = [warning for warning in result.warnings if warning.code == "historical_replay_proxies_used"]
    assert proxy_warning.message_i18n_key == "risk.warnings.historical_replay_proxies_used"
    assert proxy_warning.message_params == {"names": "Original asset", "count": 1}
    assert names_db.lookups == [[1]]


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
    names_db = NamesDb({1: "Unclassified asset"})
    service = RiskService(db=names_db)
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
    # The fallback names its asset (a single `details.asset_id`) next to the dimension it lacked.
    assert result.warnings[0].message_i18n_key == "risk.warnings.hypothetical_metadata_other_fallback"
    assert result.warnings[0].message_params == {"dimension": "sector", "names": "Unclassified asset", "count": 1}
    assert names_db.lookups == [[1]]


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


# Translatable warnings (developer's decision of 24/09/2026): one sentence per exclusion reason and
# per data-quality cause, each with a key the frontend renders and the names of the assets it lists.


def test_excluded_assets_get_one_warning_per_reason_with_its_own_key():
    warnings = _assets_excluded_warnings(
        (
            RiskExcludedAsset(asset_id=3, reason="missing_price"),
            RiskExcludedAsset(asset_id=2, reason="missing_fx"),
            RiskExcludedAsset(asset_id=1, reason="missing_price"),
            RiskExcludedAsset(asset_id=5, reason="invalid_currency"),
            RiskExcludedAsset(asset_id=4, reason="insufficient_history"),
        )
    )

    assert {warning.code for warning in warnings} == {"assets_excluded"}
    by_reason = {warning.details["reason"]: warning for warning in warnings}
    # One warning per reason, never one per asset.
    assert len(warnings) == len(by_reason)
    assert {reason: (warning.message_i18n_key, sorted(warning.details["asset_ids"])) for reason, warning in by_reason.items()} == {
        "missing_price": ("risk.warnings.assets_excluded_missing_price", [1, 3]),
        "missing_fx": ("risk.warnings.assets_excluded_missing_fx", [2]),
        "invalid_currency": ("risk.warnings.assets_excluded_invalid_currency", [5]),
        "insufficient_history": ("risk.warnings.assets_excluded_insufficient_history", [4]),
    }
    assert _assets_excluded_warnings(()) == []


def test_an_unrecognised_exclusion_reason_reads_as_insufficient_history():
    (warning,) = _assets_excluded_warnings((RiskExcludedAsset(asset_id=9, reason="not_a_known_reason"),))

    assert warning.message_i18n_key == "risk.warnings.assets_excluded_insufficient_history"
    assert warning.details == {"asset_ids": [9], "reason": "not_a_known_reason"}


def _stale_price(asset_id: int) -> StalePriceAsset:
    return StalePriceAsset(asset_id=asset_id, name=f"Stale {asset_id}", last_price_date=date(2026, 1, 2), stale_days=30)


def _missing_price(asset_id: int) -> MissingPriceAsset:
    return MissingPriceAsset(asset_id=asset_id, name=f"Missing {asset_id}", broker_id=1, broker_name="Fixture broker", quantity=Decimal("1"), currency="EUR")


@pytest.mark.parametrize(
    ("fields", "cause", "key"),
    [
        pytest.param({"stale_prices": [_stale_price(7)]}, "stale_prices", "risk.warnings.data_quality_stale_prices", id="stale-price"),
        pytest.param({"carried_forward_price_points": 2, "carried_forward_price_asset_ids": [8]}, "stale_prices", "risk.warnings.data_quality_stale_prices", id="carried-price"),
        pytest.param({"carried_forward_fx_points": 1, "carried_forward_fx_pairs": ["USD/EUR"]}, "stale_fx_rates", "risk.warnings.data_quality_stale_fx_rates", id="carried-fx"),
        pytest.param({"missing_price_assets": [_missing_price(9)]}, "missing_prices", "risk.warnings.data_quality_missing_prices", id="missing-price"),
        pytest.param({"unresolved_fx_pairs": ["GBP/EUR"]}, "missing_fx_rates", "risk.warnings.data_quality_missing_fx_rates", id="unresolved-fx"),
        pytest.param({"missing_fx_pairs": [WACMissingPairInfo(pair="CHF/EUR")]}, "missing_fx_rates", "risk.warnings.data_quality_missing_fx_rates", id="missing-fx"),
        pytest.param({"incomplete_nav_dates": [date(2026, 1, 5)]}, "incomplete_dates", "risk.warnings.data_quality_incomplete_dates", id="incomplete-nav"),
        pytest.param({"incomplete_book_value_dates": [date(2026, 1, 5)]}, "incomplete_dates", "risk.warnings.data_quality_incomplete_dates", id="incomplete-book-value"),
        pytest.param({"incomplete_allocation_dates": [date(2026, 1, 5)]}, "incomplete_dates", "risk.warnings.data_quality_incomplete_dates", id="incomplete-allocation"),
        pytest.param({"incomplete_valuation_dates": [date(2026, 1, 5)]}, "incomplete_dates", "risk.warnings.data_quality_incomplete_dates", id="incomplete-valuation"),
    ],
)
def test_each_data_quality_cause_alone_gets_exactly_its_own_warning(fields, cause, key):
    report = DataQualityReport(**fields)
    assert report.data_quality_status != DataQualityStatus.OK

    (warning,) = _data_quality_warnings(report)

    assert warning.code == "data_quality_degraded"
    assert warning.message_i18n_key == key
    assert warning.details["cause"] == cause
    assert warning.details["status"] == report.data_quality_status.value


def test_every_data_quality_cause_together_gets_one_warning_each_and_no_generic_one():
    report = DataQualityReport(
        stale_prices=[_stale_price(7)],
        carried_forward_price_points=2,
        carried_forward_price_asset_ids=[8, 7],
        carried_forward_fx_points=1,
        carried_forward_fx_pairs=["USD/EUR"],
        missing_price_assets=[_missing_price(9)],
        unresolved_fx_pairs=["GBP/EUR"],
        missing_fx_pairs=[WACMissingPairInfo(pair="CHF/EUR", dates=[date(2026, 1, 5)])],
        incomplete_nav_dates=[date(2026, 1, 5), date(2026, 1, 6)],
        incomplete_valuation_dates=[date(2026, 1, 6), date(2026, 1, 7)],
    )

    warnings = _data_quality_warnings(report)

    by_cause = {warning.details["cause"]: warning for warning in warnings}
    assert len(warnings) == len(by_cause)
    assert set(by_cause) == {"stale_prices", "stale_fx_rates", "missing_prices", "missing_fx_rates", "incomplete_dates"}
    assert all(warning.details["status"] == "partial" for warning in warnings)
    # Stale and carried prices are one cause: each asset named once.
    assert by_cause["stale_prices"].details["asset_ids"] == [7, 8]
    assert by_cause["stale_prices"].message_params == {"days": STALE_PRICE_THRESHOLD_DAYS}
    assert by_cause["stale_fx_rates"].details["pairs"] == ["USD/EUR"]
    assert by_cause["stale_fx_rates"].message_params == {"days": STALE_PRICE_THRESHOLD_DAYS, "pairs": "USD/EUR"}
    assert by_cause["missing_prices"].details["asset_ids"] == [9]
    # Unresolved and missing pairs are one cause too.
    assert by_cause["missing_fx_rates"].details["pairs"] == ["CHF/EUR", "GBP/EUR"]
    assert by_cause["missing_fx_rates"].message_params == {"pairs": "CHF/EUR, GBP/EUR"}
    # Dates are counted once across the four lists, not summed.
    assert by_cause["incomplete_dates"].message_params == {"count": 3}


def test_the_generic_data_quality_warning_appears_only_when_no_cause_applies():
    # A carried count with no asset to name: degraded, and nothing more specific to say.
    unnamed = DataQualityReport(carried_forward_price_points=3)
    assert unnamed.data_quality_status == DataQualityStatus.CARRIED_FORWARD

    (warning,) = _data_quality_warnings(unnamed)

    assert warning.code == "data_quality_degraded"
    assert warning.message_i18n_key == "risk.warnings.data_quality_degraded"
    assert warning.details == {"status": "carried_forward"}
    assert warning.message_params == {}

    # Unusable assets alone: `assets_excluded` already names them, so nothing is added here.
    only_unusable = DataQualityReport(unusable_assets=[DataQualityExcludedAsset(asset_id=4, reason=DataQualityExclusionReason.MISSING_PRICE)])
    assert only_unusable.data_quality_status == DataQualityStatus.PARTIAL
    assert _data_quality_warnings(only_unusable) == []


def _unavailable_with(*warnings: RiskWarning, instance_id: str) -> RiskAnalyticResult:
    return RiskAnalyticResult(
        instance_id=instance_id,
        analytic_code="stress",
        status=RiskResultStatus.UNAVAILABLE,
        error=RiskError(code=RiskErrorCode.INSUFFICIENT_HISTORY, message="fixture"),
        warnings=list(warnings),
    )


@pytest.mark.asyncio
async def test_warning_names_come_from_one_lookup_for_the_whole_response():
    names_db = NamesDb({1: "Alpha", 2: "Beta", 3: "Gamma", 5: "Delta"})
    listed = RiskWarning(code="assets_excluded", message="fallback", details={"asset_ids": [2, 1]}, message_i18n_key="risk.warnings.assets_excluded_missing_fx", message_params={"kept": "yes"})
    unkeyed = RiskWarning(code="legacy_code", message="fallback", details={"asset_ids": [5]})
    single = RiskWarning(code="hypothetical_metadata_other_fallback", message="fallback", details={"asset_id": 3}, message_i18n_key="risk.warnings.hypothetical_metadata_other_fallback", message_params={"dimension": "sector"})
    unknown = RiskWarning(code="assets_excluded", message="fallback", details={"asset_ids": [4]}, message_i18n_key="risk.warnings.assets_excluded_missing_price")
    about_no_asset = RiskWarning(code="flat_series", message="fallback", message_i18n_key="risk.warnings.flat_series")
    items = [
        _unavailable_with(listed, unkeyed, instance_id="first"),
        _unavailable_with(single, unknown, about_no_asset, instance_id="second"),
    ]

    first, second = await RiskService(db=names_db)._with_warning_asset_names(items)

    # Names in the warning's own order, next to the params it already had.
    assert first.warnings[0].message_params == {"kept": "yes", "names": "Beta, Alpha", "count": 2}
    # Without a key the English message is the fallback: left exactly as it was.
    assert first.warnings[1] == unkeyed
    # A single `details.asset_id` is named as well.
    assert second.warnings[0].message_params == {"dimension": "sector", "names": "Gamma", "count": 1}
    # An asset the lookup does not know still reads as something.
    assert second.warnings[1].message_params == {"names": "#4", "count": 1}
    # A keyed warning about no asset in particular gains nothing.
    assert second.warnings[2] == about_no_asset
    # One lookup for the whole response, for the assets of the keyed warnings only.
    assert names_db.lookups == [[1, 2, 3, 4]]
    assert [item.instance_id for item in (first, second)] == ["first", "second"]


@pytest.mark.asyncio
async def test_warning_names_issue_no_query_when_no_warning_needs_them():
    names_db = NamesDb({1: "Alpha"})
    items = [
        _unavailable_with(
            RiskWarning(code="legacy_code", message="fallback", details={"asset_ids": [1]}),
            RiskWarning(code="flat_series", message="fallback", message_i18n_key="risk.warnings.flat_series"),
            instance_id="only",
        )
    ]

    enriched = await RiskService(db=names_db)._with_warning_asset_names(items)

    assert enriched == items
    assert names_db.lookups == []


# ---------------------------------------------------------------------------
# «Partial» only where the number lost something (developer's decision of 29/09/2026)
#
# A holding that nothing prices is excluded from the per-asset series. In portfolio historical mode
# the primary series is the portfolio TWRR, which already values that holding at its last trade
# price. Each analytic declares the series it reads (`RiskAnalytic.series_inputs`):
#   PRIMARY (KPI, VaR, drawdown) reads the TWRR alone — it inherits no exclusion of the scope and is
#     judged on the portfolio's own data quality;
#   PRIMARY_AND_BENCHMARK (comparison) inherits no exclusion either, but its benchmark is prepared on
#     the joint calendar of the scope, so the per-asset data quality stays its own;
#   SCOPE_ASSETS (correlation, the current-composition backtest, a slice…) keeps everything.
# ---------------------------------------------------------------------------

UNPRICED_ASSET_ID = 3
BENCHMARK_ASSET_ID = 9
OBSERVATIONS = 24
PORTFOLIO_TWRR_RETURNS = [round(0.004 * math.sin(index * 0.8) + 0.0005, 10) for index in range(OBSERVATIONS)]
PRICED_RETURNS = {
    1: [round(0.009 * math.sin(index * 0.7) + 0.001, 10) for index in range(OBSERVATIONS)],
    2: [round(0.006 * math.cos(index * 0.45) - 0.0005, 10) for index in range(OBSERVATIONS)],
    BENCHMARK_ASSET_ID: [round(0.007 * math.sin(index * 0.55 + 1.0), 10) for index in range(OBSERVATIONS)],
}
# The four analytics that, in portfolio historical mode, read nothing but the TWRR (and, for
# comparison, a benchmark that is not a scope asset).
TWRR_READERS = {
    "kpi": {"instance_id": "kpi", "analytic_code": "historical_kpi"},
    "var": {"instance_id": "var", "analytic_code": "historical_var"},
    "drawdown": {"instance_id": "drawdown", "analytic_code": "drawdown_summary"},
    "comparison": {"instance_id": "comparison", "analytic_code": "comparison", "parameters": {"comparison_asset_id": BENCHMARK_ASSET_ID}},
}
PRIMARY_READERS = ("kpi", "var", "drawdown")
CORRELATION = {"instance_id": "correlation", "analytic_code": "correlation"}
CONTRIBUTION = {"instance_id": "contribution", "analytic_code": "risk_contribution"}
RISK_RETURN = {"instance_id": "risk_return", "analytic_code": "asset_risk_return"}
SPY = {"instance_id": "spy", "analytic_code": "context_spy"}
# Two ways the per-asset preparation degrades without excluding anything: a benchmark quote carried
# past the staleness threshold, and a date dropped from the joint calendar. Each names its own cause.
JOINT_CALENDAR_DEGRADATIONS = [
    pytest.param({"carried_forward_price_points": 3, "carried_forward_price_asset_ids": [BENCHMARK_ASSET_ID]}, "stale_prices", id="carried-benchmark-price"),
    pytest.param({"incomplete_valuation_dates": [date(2026, 1, 12)]}, "incomplete_dates", id="dropped-calendar-date"),
]


class _NoRows:
    """A query result without rows, whichever accessor reads it."""

    def all(self) -> list:
        return []

    def fetchall(self) -> list:
        return []

    def first(self) -> None:
        return None

    def one_or_none(self) -> None:
        return None

    def scalar(self) -> None:
        return None

    def scalar_one_or_none(self) -> None:
        return None

    def scalars(self) -> _NoRows:
        return self

    def mappings(self) -> _NoRows:
        return self

    def unique(self) -> _NoRows:
        return self

    def tuples(self) -> _NoRows:
        return self

    def __iter__(self):
        return iter(())


class EmptyRowsDb:
    """A session in which every query finds nothing, and which keeps what it was asked.

    Scope, series and asset lookups are stubbed around it, so what reaches it is whatever else the
    service reads: the warning names and — when an exclusion is a missing price — the one query
    that asks, per asset, whether a provider is assigned and whether any price row exists. What
    "no row" means for that query depends on how it is phrased, so the tests using this double
    assert nothing that hinges on the answer: only which statements were issued, and what does not
    depend on the reason at all.
    """

    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement, *_args, **_kwargs) -> _NoRows:
        self.statements.append(str(statement))
        return _NoRows()

    async def scalars(self, statement, *_args, **_kwargs) -> _NoRows:
        self.statements.append(str(statement))
        return _NoRows()

    async def scalar(self, statement, *_args, **_kwargs) -> None:
        self.statements.append(str(statement))
        return None

    def source_reads(self) -> list[str]:
        """Statements that read the provider assignments or the stored prices."""
        return [statement for statement in self.statements if "asset_provider_assignments" in statement or "price_history" in statement]


def unpriced_holding_report(data_quality: DataQualityReport | None = None) -> PortfolioReportResponse:
    """A portfolio worth 600: 300 and 100 in priced holdings, 100 in one nothing prices, 100 in cash."""
    report = slice_report(
        holdings={1: "300", 2: "100", UNPRICED_ASSET_ID: "100"},
        cash="100",
        twrr=twrr_history(PORTFOLIO_TWRR_RETURNS),
    )
    return report if data_quality is None else report.model_copy(update={"data_quality": data_quality})


def priced_portfolio_report(**money: str) -> PortfolioReportResponse:
    """A portfolio of priced holdings only (300 and 200), 100 in cash unless told otherwise."""
    return slice_report(holdings={1: "300", 2: "200"}, **({"cash": "100"} | money), twrr=twrr_history(PORTFOLIO_TWRR_RETURNS))


def prepared_with(data_quality: DataQualityReport) -> PreparedAssetSeriesSet:
    """The priced series and the benchmark, with the per-asset data quality `data_quality`."""
    return make_prepared_set(PRICED_RETURNS).model_copy(update={"data_quality": data_quality})


def prepared_without(
    asset_id: int = UNPRICED_ASSET_ID,
    reason: DataQualityExclusionReason | None = DataQualityExclusionReason.MISSING_PRICE,
) -> PreparedAssetSeriesSet:
    """The priced series and the benchmark; `asset_id` is left out for `reason`, or for none recorded."""
    if reason is None:
        return make_prepared_set(PRICED_RETURNS)
    return prepared_with(DataQualityReport(unusable_assets=[DataQualityExcludedAsset(asset_id=asset_id, reason=reason)]))


async def query_unpriced_holding(
    monkeypatch,
    *,
    analytics: list[dict[str, object]],
    mode: str = "historical",
    asset_ids: list[int] | None = None,
    report: PortfolioReportResponse | None = None,
    prepared: PreparedAssetSeriesSet | None = None,
    db: EmptyRowsDb | None = None,
) -> dict[str, RiskAnalyticResult]:
    """Run one portfolio request over the unpriced-holding fixture; results keyed by instance."""
    service = RiskService(db=db if db is not None else EmptyRowsDb())
    install_portfolio_report(monkeypatch, service, report if report is not None else unpriced_holding_report())
    install_prepared_series(monkeypatch, service, prepared if prepared is not None else prepared_without())
    request = slice_request(
        mode=mode,
        asset_ids=asset_ids,
        analytics=analytics,
        start=date(2026, 1, 1),
        end=date(2026, 1, 1) + timedelta(days=OBSERVATIONS),
    )
    response = await service.execute(user_id=7, request=request)
    return {item.instance_id: item for item in response.items}


def exclusion_ids(result: RiskAnalyticResult) -> list[int]:
    return [item.asset_id for item in result.metadata.excluded_assets]


def warning_codes(result: RiskAnalyticResult) -> list[str]:
    return [warning.code for warning in result.warnings]


def warning_causes(result: RiskAnalyticResult) -> list[str]:
    return [warning.details["cause"] for warning in result.warnings if "cause" in warning.details]


def assert_the_exclusion_is_real(correlation: RiskAnalyticResult) -> None:
    """Presence barrier, in the same request: a SCOPE_ASSETS reader still carries the exclusion.

    Without it, every absence asserted about the other results would be vacuous.
    """
    assert correlation.status == RiskResultStatus.PARTIAL
    assert exclusion_ids(correlation) == [UNPRICED_ASSET_ID]
    assert [warning.details["asset_ids"] for warning in correlation.warnings if warning.code == "assets_excluded"] == [[UNPRICED_ASSET_ID]]
    assert UNPRICED_ASSET_ID in {item.asset_id for item in correlation.data_quality.unusable_assets}


@pytest.mark.parametrize("instance_id", PRIMARY_READERS)
@pytest.mark.asyncio
async def test_a_primary_reader_on_the_portfolio_twrr_does_not_inherit_the_exclusions(monkeypatch, instance_id):
    report = unpriced_holding_report()
    results = await query_unpriced_holding(monkeypatch, analytics=[*TWRR_READERS.values(), CORRELATION], report=report)
    assert_the_exclusion_is_real(results["correlation"])

    result = results[instance_id]
    assert result.output is not None, result.error
    assert result.metadata.return_basis == RiskReturnBasis.TWRR
    # The TWRR already values the unpriced holding at its last trade price: nothing was lost.
    assert result.status == RiskResultStatus.OK, warning_codes(result)
    assert "assets_excluded" not in warning_codes(result)
    assert result.metadata.excluded_assets == []
    # Judged on the portfolio's own report, not on per-asset data the TWRR never needed.
    assert result.data_quality == report.data_quality


@pytest.mark.asyncio
async def test_comparison_on_the_portfolio_twrr_is_not_partial_for_a_scope_exclusion_alone(monkeypatch):
    results = await query_unpriced_holding(monkeypatch, analytics=[*TWRR_READERS.values(), CORRELATION])
    assert_the_exclusion_is_real(results["correlation"])

    comparison = results["comparison"]
    assert comparison.output is not None, comparison.error
    assert comparison.metadata.return_basis == RiskReturnBasis.TWRR
    assert comparison.status == RiskResultStatus.OK, warning_codes(comparison)
    assert "assets_excluded" not in warning_codes(comparison)
    assert comparison.metadata.excluded_assets == []
    # Its data quality stays the per-asset one (next test), but the exclusion is not part of it: the
    # excluded holding never entered the joint calendar the benchmark was prepared on.
    assert comparison.data_quality.data_quality_status == DataQualityStatus.OK


@pytest.mark.parametrize(("degradation", "cause"), JOINT_CALENDAR_DEGRADATIONS)
@pytest.mark.asyncio
async def test_a_degraded_joint_calendar_makes_comparison_partial_on_the_twrr(monkeypatch, degradation, cause):
    """The benchmark is prepared on the joint calendar of the scope: what degrades it is comparison's own."""
    results = await query_unpriced_holding(
        monkeypatch,
        analytics=[TWRR_READERS["comparison"]],
        report=priced_portfolio_report(),
        prepared=prepared_with(DataQualityReport(**degradation)),
    )

    comparison = results["comparison"]
    assert comparison.output is not None, comparison.error
    assert comparison.metadata.return_basis == RiskReturnBasis.TWRR
    assert comparison.status == RiskResultStatus.PARTIAL
    assert cause in warning_causes(comparison), warning_codes(comparison)


@pytest.mark.parametrize(("degradation", "cause"), JOINT_CALENDAR_DEGRADATIONS)
@pytest.mark.asyncio
async def test_comparison_on_the_twrr_stays_partial_for_its_calendar_not_for_the_exclusion(monkeypatch, degradation, cause):
    prepared = prepared_with(DataQualityReport(unusable_assets=[DataQualityExcludedAsset(asset_id=UNPRICED_ASSET_ID, reason=DataQualityExclusionReason.MISSING_PRICE)], **degradation))

    results = await query_unpriced_holding(monkeypatch, analytics=[*TWRR_READERS.values(), CORRELATION], prepared=prepared)
    assert_the_exclusion_is_real(results["correlation"])

    comparison = results["comparison"]
    assert comparison.output is not None, comparison.error
    assert comparison.status == RiskResultStatus.PARTIAL
    assert cause in warning_causes(comparison), warning_codes(comparison)
    # Partial for the degraded calendar, not for the holding the TWRR already values.
    assert "assets_excluded" not in warning_codes(comparison)
    assert comparison.metadata.excluded_assets == []
    # Neither is any of it the TWRR's: the primary readers of the same request stay whole.
    for instance_id in PRIMARY_READERS:
        assert results[instance_id].status == RiskResultStatus.OK, (instance_id, warning_codes(results[instance_id]))


@pytest.mark.asyncio
async def test_a_held_benchmark_without_a_series_keeps_its_own_entry_in_the_comparison_data_quality(monkeypatch):
    """Benchmarked against a holding nothing prices, comparison cannot run — and its data quality says why.

    The scope's exclusions leave a comparison's per-asset data quality because the excluded holdings
    never entered the joint calendar its benchmark was prepared on. The benchmark's own entry is the
    exception: it is the reason the comparison is unavailable. Against another benchmark, in the same
    request, the entry is not the comparison's own and is dropped as usual.
    """
    held_benchmark = {"instance_id": "held_benchmark", "analytic_code": "comparison", "parameters": {"comparison_asset_id": UNPRICED_ASSET_ID}}

    results = await query_unpriced_holding(monkeypatch, analytics=[held_benchmark, TWRR_READERS["comparison"], CORRELATION])
    assert_the_exclusion_is_real(results["correlation"])

    unavailable = results["held_benchmark"]
    assert unavailable.status == RiskResultStatus.UNAVAILABLE
    assert unavailable.error.code == RiskErrorCode.DATA_UNAVAILABLE
    assert unavailable.error.details == {"asset_id": UNPRICED_ASSET_ID}
    assert unavailable.metadata.return_basis == RiskReturnBasis.TWRR
    assert UNPRICED_ASSET_ID in {item.asset_id for item in unavailable.data_quality.unusable_assets}

    other = results["comparison"]
    assert other.status == RiskResultStatus.OK, warning_codes(other)
    assert UNPRICED_ASSET_ID not in {item.asset_id for item in other.data_quality.unusable_assets}


@pytest.mark.asyncio
async def test_the_twrr_readers_drop_the_residual_warning_of_the_composition(monkeypatch):
    """The in-transit warning describes the zero-return residual of the composition, which the TWRR never uses.

    Net worth 600 against 500 of holdings and 50 of cash: the other 50 is in transit, so the
    residual (1/6) is not the cash (1/12) and the scope says so.
    """
    residual = "zero_risk_residual_includes_in_transit"
    results = await query_unpriced_holding(
        monkeypatch,
        analytics=[*TWRR_READERS.values(), CORRELATION],
        report=priced_portfolio_report(cash="50", in_transit="50", net_worth="600"),
        prepared=prepared_without(reason=None),
    )

    # Presence barrier: the scope raised it, and a reader of the per-asset series keeps it.
    assert residual in warning_codes(results["correlation"])
    for instance_id in TWRR_READERS:
        result = results[instance_id]
        assert result.metadata.return_basis == RiskReturnBasis.TWRR, instance_id
        assert residual not in warning_codes(result), instance_id
        assert result.status == RiskResultStatus.OK, (instance_id, warning_codes(result))


@pytest.mark.asyncio
async def test_a_degraded_portfolio_still_makes_the_twrr_readers_partial(monkeypatch):
    """The request's exclusion stops counting; the portfolio's own data quality does not."""
    results = await query_unpriced_holding(
        monkeypatch,
        analytics=list(TWRR_READERS.values()),
        report=unpriced_holding_report(DataQualityReport(stale_prices=[_stale_price(1)])),
    )

    assert set(results) == set(TWRR_READERS)
    for instance_id, result in results.items():
        assert result.output is not None, (instance_id, result.error)
        assert result.metadata.return_basis == RiskReturnBasis.TWRR, instance_id
        assert result.status == RiskResultStatus.PARTIAL, instance_id
        assert result.data_quality.data_quality_status != DataQualityStatus.OK, instance_id
        stale = [warning.details["asset_ids"] for warning in result.warnings if warning.details.get("cause") == "stale_prices"]
        assert stale == [[1]], (instance_id, warning_codes(result))


@pytest.mark.asyncio
async def test_on_the_current_composition_every_result_keeps_the_exclusion(monkeypatch):
    """The backtest replays today's weights over the per-asset series: it did lose the holding."""
    analytics = [TWRR_READERS["kpi"], TWRR_READERS["var"], TWRR_READERS["comparison"], CORRELATION, CONTRIBUTION, RISK_RETURN]
    results = await query_unpriced_holding(monkeypatch, mode="current_composition", analytics=analytics)

    for instance_id in ("kpi", "var", "comparison"):
        assert results[instance_id].metadata.return_basis == RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST, instance_id
    assert len(results) == len(analytics)
    for instance_id, result in results.items():
        assert result.output is not None, (instance_id, result.error)
        assert result.status == RiskResultStatus.PARTIAL, instance_id
        assert exclusion_ids(result) == [UNPRICED_ASSET_ID], instance_id
        assert "assets_excluded" in warning_codes(result), instance_id


@pytest.mark.asyncio
async def test_a_sliced_portfolio_keeps_the_exclusion_in_historical_mode(monkeypatch):
    """A slice cannot be cut out of the TWRR (K4), so historical mode replays it from the per-asset series."""
    results = await query_unpriced_holding(monkeypatch, asset_ids=[1, UNPRICED_ASSET_ID], analytics=list(TWRR_READERS.values()))

    assert set(results) == set(TWRR_READERS)
    for instance_id, result in results.items():
        assert result.output is not None, (instance_id, result.error)
        assert result.metadata.return_basis == RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST, instance_id
        assert result.status == RiskResultStatus.PARTIAL, instance_id
        assert exclusion_ids(result) == [UNPRICED_ASSET_ID], instance_id
        assert "assets_excluded" in warning_codes(result), instance_id


@pytest.mark.parametrize("instance_id", list(TWRR_READERS))
@pytest.mark.asyncio
async def test_a_sliced_historical_result_is_judged_on_the_series_it_consumed(monkeypatch, instance_id):
    """The other half of the generalized rule: the portfolio's data quality follows the basis, not the mode.

    KPI and VaR used to take the portfolio's report whenever the mode was historical, sliced or not.
    A slice is replayed from the per-asset series, so that report alone hides the holding the replay
    lost.
    """
    results = await query_unpriced_holding(monkeypatch, asset_ids=[1, UNPRICED_ASSET_ID], analytics=list(TWRR_READERS.values()))

    result = results[instance_id]
    assert result.metadata.return_basis == RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST
    assert UNPRICED_ASSET_ID in {item.asset_id for item in result.data_quality.unusable_assets}


# `excluded_weight`: Σ weights of the scope assets left without a series. `cash_weight` keeps its
# meaning — the zero-return residual, clamped at zero — and no other number moves. With non-negative
# true cash the excluded part sits inside that residual; with negative true cash the two are not
# nested, and no rule pretends they are.


def install_context_spy(monkeypatch) -> list[RiskExecutionContext]:
    """Serve one more analytic, which records the context the service hands it in any scope and mode."""
    seen: list[RiskExecutionContext] = []

    class ContextSpy(GoodAnalytic):
        analytic_code = "context_spy"
        supported_scopes = (RiskScopeKind.ASSET, RiskScopeKind.ASSET_SET, RiskScopeKind.PORTFOLIO)
        supported_modes = (RiskMode.HISTORICAL, RiskMode.CURRENT_COMPOSITION)
        # The history gate counts the primary series, which a weightless scope lacks. The spy
        # measures nothing, so nothing may keep it from being called.
        min_observations = 0

        def compute(self, params, context):
            seen.append(context)
            return super().compute(params, context)

    registered = RiskAnalyticRegistry.get_plugin
    monkeypatch.setattr(
        RiskAnalyticRegistry,
        "get_plugin",
        classmethod(lambda cls, code: ContextSpy if code == ContextSpy.analytic_code else registered(code)),
    )
    return seen


@pytest.mark.parametrize("mode", ["historical", "current_composition"])
@pytest.mark.asyncio
async def test_the_excluded_weight_is_the_share_of_the_portfolio_left_without_a_series(monkeypatch, mode):
    seen = install_context_spy(monkeypatch)
    prepared = make_prepared_set(PRICED_RETURNS).model_copy(
        update={
            "data_quality": DataQualityReport(
                unusable_assets=[
                    DataQualityExcludedAsset(asset_id=3, reason=DataQualityExclusionReason.MISSING_PRICE),
                    DataQualityExcludedAsset(asset_id=4, reason=DataQualityExclusionReason.MISSING_FX),
                ]
            )
        }
    )

    await query_unpriced_holding(
        monkeypatch,
        mode=mode,
        analytics=[SPY],
        report=slice_report(holdings={1: "300", 2: "100", 3: "100", 4: "50"}, cash="50"),
        prepared=prepared,
    )

    (context,) = seen
    assert {item.asset_id for item in context.excluded_assets} == {3, 4}
    # Whatever the reason: 150 of a 600 portfolio lost its series.
    assert context.excluded_weight == pytest.approx(150 / 600, abs=1e-12)
    # `cash_weight` keeps its meaning — the whole zero-return residual — and holds the excluded part.
    assert context.cash_weight == pytest.approx(200 / 600, abs=1e-12)
    assert context.cash_weight - context.excluded_weight == pytest.approx(50 / 600, abs=1e-12)


@pytest.mark.asyncio
async def test_a_slice_counts_its_excluded_holding_against_the_slice(monkeypatch):
    seen = install_context_spy(monkeypatch)

    await query_unpriced_holding(monkeypatch, mode="current_composition", asset_ids=[1, UNPRICED_ASSET_ID], analytics=[SPY])

    (context,) = seen
    assert [item.asset_id for item in context.excluded_assets] == [UNPRICED_ASSET_ID]
    # The slice is 100% of itself (300 + 100) and holds no true cash: its whole residual is the
    # excluded holding, so the two weights meet at the bound.
    assert context.excluded_weight == pytest.approx(0.25, abs=1e-12)
    assert context.cash_weight == pytest.approx(0.25, abs=1e-12)


@pytest.mark.parametrize(
    "scope",
    [
        pytest.param({"kind": "asset_set", "asset_ids": [1, 2, UNPRICED_ASSET_ID]}, id="asset-set"),
        pytest.param({"kind": "asset", "asset_id": UNPRICED_ASSET_ID}, id="asset"),
    ],
)
@pytest.mark.asyncio
async def test_a_scope_without_weights_has_no_excluded_weight(monkeypatch, scope):
    seen = install_context_spy(monkeypatch)
    service = RiskService(db=EmptyRowsDb())
    install_prepared_series(monkeypatch, service, prepared_without())

    await service.execute(
        user_id=7,
        request=RiskQueryRequest.model_validate(
            {
                "scope": scope,
                "date_range": {"start": "2026-01-01", "end": "2026-01-25"},
                "target_currency": "EUR",
                "mode": "historical",
                "analytics": [SPY],
            }
        ),
    )

    (context,) = seen
    assert [item.asset_id for item in context.excluded_assets] == [UNPRICED_ASSET_ID]
    assert context.excluded_weight == 0.0


@pytest.mark.asyncio
async def test_with_negative_true_cash_the_excluded_weight_is_not_nested_in_the_residual(monkeypatch):
    """Net worth 500 against 600 of holdings (true cash -100); the 200 that nothing prices is excluded.

    Weights 0.8 and 0.4: the residual left by the priced holding is 0.2, the excluded weight 0.4.
    Both are stated as they are, and the result is produced.
    """
    seen = install_context_spy(monkeypatch)

    results = await query_unpriced_holding(
        monkeypatch,
        mode="current_composition",
        analytics=[SPY],
        report=slice_report(holdings={1: "400", UNPRICED_ASSET_ID: "200"}, cash="-100"),
    )

    assert results["spy"].output is not None, results["spy"].error
    (context,) = seen
    assert [item.asset_id for item in context.excluded_assets] == [UNPRICED_ASSET_ID]
    assert dict(context.weights) == pytest.approx({1: 0.8, UNPRICED_ASSET_ID: 0.4})
    assert context.cash_weight == pytest.approx(0.2, abs=1e-12)
    assert context.excluded_weight == pytest.approx(0.4, abs=1e-12)


@pytest.mark.asyncio
async def test_contribution_and_risk_return_name_the_excluded_weight_inside_cash(monkeypatch):
    results = await query_unpriced_holding(monkeypatch, mode="current_composition", analytics=[CONTRIBUTION, RISK_RETURN])

    for instance_id in ("contribution", "risk_return"):
        result = results[instance_id]
        assert result.output is not None, (instance_id, result.error)
        assert exclusion_ids(result) == [UNPRICED_ASSET_ID], instance_id
        # 100 of 600 has no series; with 100 of true cash, the zero-return residual is 200 — true
        # cash is not negative here, so the excluded part sits inside the residual.
        assert result.output.cash_weight == pytest.approx(2 / 6, abs=1e-12), instance_id
        assert result.output.excluded_weight == pytest.approx(1 / 6, abs=1e-12), instance_id
        assert result.output.excluded_weight <= result.output.cash_weight, instance_id

    # The versions that publish `excluded_weight`: a zero must be told apart from a server that predates the field.
    # `asset_risk_return` is at 1.2.0 since k6 (06/10/2026), which adds each point's own Sharpe and Sortino.
    assert results["contribution"].metadata.algorithm_version == "1.2.0"
    assert results["risk_return"].metadata.algorithm_version == "1.2.0"


# Captured on `ffe41c5ba`, before `excluded_weight` existed, from exactly the current-composition
# inputs of `query_unpriced_holding`. Publishing the split must not move any of them. The relative
# tolerance only absorbs BLAS differences in `np.cov` between machines.
GOLDEN_REL = 1e-12
GOLDEN_CONTRIBUTION = {
    "portfolio_volatility": 0.06237752322585717,
    "cash_weight": 0.33333333333333337,
    "effective_number_of_assets": 3.5999999999999996,
    "diversification_ratio": 1.1846014602790187,
    "weight": [0.5, 0.16666666666666666],
    "marginal_contribution": [0.11643684887967204, 0.02495459271612689],
    "component_contribution": [0.05821842443983602, 0.004159098786021148],
    "percentage_contribution": [0.9333237587686538, 0.06667624123134612],
}
GOLDEN_RISK_RETURN = {
    "portfolio_volatility": 0.06298800939876324,
    "portfolio_expected_annual_return": 0.29920378381701246,
    "cash_weight": 0.33333333333333337,
    "weight": [0.5, 0.16666666666666666],
    "volatility": [0.11952753719204096, 0.08477241903551005],
    "expected_annual_return": [0.6995987272083334, -0.32355274133333334],
}


@pytest.mark.asyncio
async def test_publishing_the_excluded_weight_moves_no_other_number(monkeypatch):
    analytics = [CONTRIBUTION, RISK_RETURN]
    results = await query_unpriced_holding(monkeypatch, mode="current_composition", analytics=analytics)
    contribution = results["contribution"].output
    risk_return = results["risk_return"].output

    # One field more, none less.
    assert set(contribution.model_dump()) - {"excluded_weight"} == {"kind", "portfolio_volatility", "cash_weight", "items", "effective_number_of_assets", "diversification_ratio"}
    assert set(risk_return.model_dump()) - {"excluded_weight"} == {"kind", "portfolio_volatility", "portfolio_expected_annual_return", "cash_weight", "items"}

    assert [item.asset_id for item in contribution.items] == [1, 2]
    for field in ("portfolio_volatility", "cash_weight", "effective_number_of_assets", "diversification_ratio"):
        assert getattr(contribution, field) == pytest.approx(GOLDEN_CONTRIBUTION[field], rel=GOLDEN_REL), field
    for field in ("weight", "marginal_contribution", "component_contribution", "percentage_contribution"):
        assert [getattr(item, field) for item in contribution.items] == pytest.approx(GOLDEN_CONTRIBUTION[field], rel=GOLDEN_REL), field

    assert [item.asset_id for item in risk_return.items] == [1, 2]
    for field in ("portfolio_volatility", "portfolio_expected_annual_return", "cash_weight"):
        assert getattr(risk_return, field) == pytest.approx(GOLDEN_RISK_RETURN[field], rel=GOLDEN_REL), field
    for field in ("weight", "volatility", "expected_annual_return"):
        assert [getattr(item, field) for item in risk_return.items] == pytest.approx(GOLDEN_RISK_RETURN[field], rel=GOLDEN_REL), field

    # And the reason no number may move: an excluded holding weighs exactly as the same money in
    # cash would (G6). Same portfolio, the unpriced 100 held as cash instead, nothing excluded.
    as_cash = await query_unpriced_holding(
        monkeypatch,
        mode="current_composition",
        analytics=analytics,
        report=slice_report(holdings={1: "300", 2: "100"}, cash="200"),
        prepared=prepared_without(reason=None),
    )
    for instance_id in ("contribution", "risk_return"):
        assert as_cash[instance_id].status == RiskResultStatus.OK, (instance_id, warning_codes(as_cash[instance_id]))
        assert results[instance_id].output.model_dump(exclude={"excluded_weight"}) == as_cash[instance_id].output.model_dump(exclude={"excluded_weight"}), instance_id


# ---------------------------------------------------------------------------
# k6 through the service (agreed with the Dashboard owner on 06/10/2026). The arithmetic is pinned on
# the plugins (`test_risk_analytics.py`); what only the request path adds is pinned here: the two
# rates reach `asset_risk_return` from the request and come back in its metadata, a warning about
# undefined ratios gets the names its sentence lists, and `comparison` measures each priced holding of
# the composition held today — never the benchmark, never a holding left without a series.
# ---------------------------------------------------------------------------


class NamedRowsDb(EmptyRowsDb):
    """`EmptyRowsDb`, except that the warning-name lookup finds the display names it is given."""

    def __init__(self, names: dict[int, str]) -> None:
        super().__init__()
        self.names = names

    async def execute(self, statement, *args, **kwargs):
        if "display_name" not in str(statement):
            return await super().execute(statement, *args, **kwargs)
        self.statements.append(str(statement))
        (requested,) = statement.compile().params.values()
        return _Rows([(asset_id, self.names[asset_id]) for asset_id in requested if asset_id in self.names])


# One holding that moves but never loses (a Sharpe, no Sortino), one that never moves (neither).
RATIO_HOLDINGS = {
    1: [round(0.002 + 0.0015 * math.cos(index * 0.7), 10) for index in range(OBSERVATIONS)],
    2: [0.0015] * OBSERVATIONS,
}


@pytest.mark.asyncio
async def test_risk_return_takes_the_rates_from_the_request_and_names_the_holdings_whose_ratios_are_undefined(monkeypatch):
    db = NamedRowsDb({1: "Steady Gainer", 2: "Flat Note", BENCHMARK_ASSET_ID: "Benchmark"})
    prepared = make_prepared_set({**RATIO_HOLDINGS, BENCHMARK_ASSET_ID: PRICED_RETURNS[BENCHMARK_ASSET_ID]})
    analytic = {**RISK_RETURN, "parameters": {"risk_free_annual_rate": 0.03, "target_annual_return": 0.0}}

    results = await query_unpriced_holding(monkeypatch, mode="current_composition", analytics=[analytic], report=priced_portfolio_report(), prepared=prepared, db=db)

    result = results["risk_return"]
    assert result.output is not None, result.error
    assert result.metadata.params == {"risk_free_annual_rate": 0.03, "target_annual_return": 0.0}
    assert result.metadata.risk_free == RiskFreeReference(annual_rate=0.03, source="analytic_param", currency="EUR")
    items = {item.asset_id: item for item in result.output.items}
    assert sorted(items) == [1, 2]
    assert items[1].sharpe == pytest.approx(annualized_sharpe(RATIO_HOLDINGS[1], result.metadata.annualization_factor, annual_risk_free_rate=0.03), rel=1e-12)
    assert (items[1].sortino, items[2].sharpe, items[2].sortino) == (None, None, None)
    # The holdings each sentence lists, by name, in the order of the points.
    named = {warning.code: warning for warning in result.warnings if warning.code in {"sharpe_undefined", "sortino_undefined"}}
    assert named["sharpe_undefined"].message_i18n_key == "risk.warnings.sharpe_undefined_assets"
    assert named["sharpe_undefined"].message_params == {"names": "Flat Note", "count": 1}
    assert named["sortino_undefined"].message_i18n_key == "risk.warnings.sortino_undefined_assets"
    assert named["sortino_undefined"].message_params == {"names": "Steady Gainer, Flat Note", "count": 2}


@pytest.mark.asyncio
async def test_comparison_measures_each_priced_holding_of_today_but_not_the_held_benchmark_nor_the_unpriced_one(monkeypatch):
    """A portfolio worth 600: 300 and 100 priced, 100 nothing prices, 50 in the benchmark itself, 50 in cash.

    In `current_composition` every holding sits on the request's joint calendar with the benchmark, so
    each pairing is the date match and each figure the plain metric of the two series.
    """
    report = slice_report(holdings={1: "300", 2: "100", UNPRICED_ASSET_ID: "100", BENCHMARK_ASSET_ID: "50"}, cash="50", twrr=twrr_history(PORTFOLIO_TWRR_RETURNS))

    results = await query_unpriced_holding(monkeypatch, mode="current_composition", analytics=[TWRR_READERS["comparison"], CONTRIBUTION], report=report)

    comparison = results["comparison"]
    assert comparison.output is not None, comparison.error
    # Presence barrier, in the same request: the benchmark is a priced holding of the scope, and the
    # unpriced one was left out — so both absences below are the comparison's own doing.
    contribution = results["contribution"]
    assert contribution.output is not None, contribution.error
    assert sorted(item.asset_id for item in contribution.output.items) == [1, 2, BENCHMARK_ASSET_ID]
    assert exclusion_ids(comparison) == [UNPRICED_ASSET_ID]
    assert comparison.metadata.comparison_asset_id == BENCHMARK_ASSET_ID
    benchmark = PRICED_RETURNS[BENCHMARK_ASSET_ID]
    assert [item.asset_id for item in comparison.output.items] == [1, 2]
    for item in comparison.output.items:
        assert item.beta == pytest.approx(beta(PRICED_RETURNS[item.asset_id], benchmark), rel=1e-12), item.asset_id
        assert item.correlation == pytest.approx(pearson_correlation(PRICED_RETURNS[item.asset_id], benchmark), rel=1e-12), item.asset_id


# An undefined ratio's warning degrades its result, as `historical_kpi`'s `sharpe_undefined` does: a figure
# the reader expects is missing, so the result is `partial` (developer's decision of 06/10/2026). Every
# case runs on a clean report with nothing excluded, so the warnings are the only thing that can make the
# result partial; and each case isolates one warning, so a single warning that stopped degrading shows.
FLAT_GAINING = [0.0015] * OBSERVATIONS  # no volatility and no downside: neither ratio
FLAT_LOSING = [-0.0005] * OBSERVATIONS  # no volatility, but a downside: a Sortino and no Sharpe
NEVER_LOSING = RATIO_HOLDINGS[1]  # moves, never loses: a Sharpe and no Sortino


def holding_beside(second_holding: list[float]) -> PreparedAssetSeriesSet:
    """Holding 1 (gains and losses, every ratio defined) beside `second_holding`, and the benchmark."""
    return make_prepared_set({1: PRICED_RETURNS[1], 2: second_holding, BENCHMARK_ASSET_ID: PRICED_RETURNS[BENCHMARK_ASSET_ID]})


@pytest.mark.parametrize(
    ("second_holding", "undefined"),
    [
        pytest.param(PRICED_RETURNS[2], {}, id="every-ratio-defined"),
        pytest.param(FLAT_GAINING, {"sharpe_undefined": [2], "sortino_undefined": [2]}, id="a-flat-holding"),
        pytest.param(FLAT_LOSING, {"sharpe_undefined": [2]}, id="only-the-sharpe-undefined"),
        pytest.param(NEVER_LOSING, {"sortino_undefined": [2]}, id="only-the-sortino-undefined"),
    ],
)
@pytest.mark.asyncio
async def test_an_undefined_ratio_makes_the_risk_return_partial(monkeypatch, second_holding, undefined):
    results = await query_unpriced_holding(monkeypatch, mode="current_composition", analytics=[RISK_RETURN], report=priced_portfolio_report(), prepared=holding_beside(second_holding))

    result = results["risk_return"]
    assert result.output is not None, result.error
    # Nothing else can make it partial: no exclusion, a clean report, and no warning but the ratios'.
    assert result.metadata.excluded_assets == []
    assert result.data_quality.data_quality_status == DataQualityStatus.OK
    assert sorted((warning.code, warning.details.get("asset_ids")) for warning in result.warnings) == sorted(undefined.items())
    assert result.status == (RiskResultStatus.PARTIAL if undefined else RiskResultStatus.OK)
    assert all(warning.degrades_result for warning in result.warnings)


@pytest.mark.parametrize(
    ("second_holding", "undefined_correlation"),
    [
        pytest.param(PRICED_RETURNS[2], [], id="every-holding-measured"),
        pytest.param(FLAT_GAINING, [2], id="a-flat-holding"),
    ],
)
@pytest.mark.asyncio
async def test_a_holding_without_a_correlation_makes_the_comparison_partial(monkeypatch, second_holding, undefined_correlation):
    results = await query_unpriced_holding(monkeypatch, mode="current_composition", analytics=[TWRR_READERS["comparison"]], report=priced_portfolio_report(), prepared=holding_beside(second_holding))

    comparison = results["comparison"]
    assert comparison.output is not None, comparison.error
    assert comparison.metadata.excluded_assets == []
    assert comparison.data_quality.data_quality_status == DataQualityStatus.OK
    # The portfolio's own figures and the benchmark's ratios are defined: the per-holding warning is the only one.
    assert None not in (comparison.output.beta, comparison.output.correlation, comparison.output.comparison_sharpe, comparison.output.comparison_sortino)
    expected = [("comparison_correlation_undefined", "risk.warnings.comparison_correlation_undefined_assets", undefined_correlation)] if undefined_correlation else []
    assert [(warning.code, warning.message_i18n_key, warning.details.get("asset_ids")) for warning in comparison.warnings] == expected
    assert comparison.status == (RiskResultStatus.PARTIAL if undefined_correlation else RiskResultStatus.OK)
    assert all(warning.degrades_result for warning in comparison.warnings)


# `no_price_source`: an asset excluded for a missing price that has no provider assigned AND no price
# row at all — never priced, and nothing will price it: a permanent state. A source that returned
# nothing, or manual prices outside the period, stay `missing_price` (occasional). The two facts are
# read in one query per request, and only when some exclusion is a missing price.


def test_an_asset_nothing_can_price_gets_a_sentence_of_its_own():
    warnings = _assets_excluded_warnings(
        (
            RiskExcludedAsset(asset_id=7, reason="no_price_source"),
            RiskExcludedAsset(asset_id=5, reason="missing_price"),
            RiskExcludedAsset(asset_id=8, reason="no_price_source"),
        )
    )

    by_reason = {warning.details["reason"]: warning for warning in warnings}
    assert len(warnings) == len(by_reason) == 2
    permanent = by_reason["no_price_source"]
    assert permanent.code == "assets_excluded"
    assert permanent.message_i18n_key == "risk.warnings.assets_excluded_no_price_source"
    assert permanent.details == {"asset_ids": [7, 8], "reason": "no_price_source"}
    # The occasional cause keeps its own sentence.
    assert by_reason["missing_price"].message_i18n_key == "risk.warnings.assets_excluded_missing_price"


@pytest.mark.asyncio
async def test_a_missing_price_is_qualified_by_one_statement_that_asks_both_facts(monkeypatch):
    """Two analytics, one exclusion to qualify: one read for the request, asking provider and prices at once.

    Which reason the empty answer leads to depends on how the query is phrased, so it is pinned on
    stored rows (`test_risk_exclusion_reasons.py`), not here.
    """
    db = EmptyRowsDb()

    results = await query_unpriced_holding(monkeypatch, db=db, mode="current_composition", analytics=[CORRELATION, CONTRIBUTION])

    assert all(exclusion_ids(result) == [UNPRICED_ASSET_ID] for result in results.values())
    (read,) = db.source_reads()
    assert "asset_provider_assignments" in read and "price_history" in read, read


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        pytest.param(DataQualityExclusionReason.MISSING_FX, "missing_fx", id="missing-fx"),
        pytest.param(DataQualityExclusionReason.INVALID_CURRENCY, "invalid_currency", id="invalid-currency"),
        pytest.param(None, "insufficient_history", id="no-return-series"),
    ],
)
@pytest.mark.asyncio
async def test_only_a_missing_price_can_become_a_missing_price_source(monkeypatch, reason, expected):
    """An exclusion for any other cause keeps its reason, and gives no cause to read the price sources."""
    db = EmptyRowsDb()

    results = await query_unpriced_holding(monkeypatch, db=db, mode="current_composition", analytics=[CORRELATION], prepared=prepared_without(reason=reason))

    assert [(item.asset_id, item.reason) for item in results["correlation"].metadata.excluded_assets] == [(UNPRICED_ASSET_ID, expected)]
    assert db.source_reads() == [], db.statements


# ---------------------------------------------------------------------------
# The portfolio TWRR is read on observation days (developer's decision of 30/09/2026)
#
# The TWRR has a point every calendar day by construction. It is read only on the days at least one
# held scope asset has a genuine quote — the union of their `quote_dates` — and the return between two
# consecutive observation days is chain-linked from the cumulative TWRR, so none of it is lost. A
# benchmark's quotes do not count. Without any held quote date (only unpriced holdings, or synthetic
# series built without quote dates) the TWRR keeps every calendar day, as before.
# ---------------------------------------------------------------------------

OBSERVATION_START = date(2026, 1, 5)  # a Monday: the TWRR baseline, and itself a quote date
OBSERVATION_SPAN = 34  # to Sunday 8 February: five weeks
OBSERVATION_END = OBSERVATION_START + timedelta(days=OBSERVATION_SPAN)
# The TWRR moves every calendar day, weekends included, so a reading that drops a day instead of
# chain-linking across it loses something measurable.
DAILY_TWRR = [round(0.003 * math.sin(index * 0.9) + 0.0004, 10) for index in range(OBSERVATION_SPAN)]
EVERY_DAY = [OBSERVATION_START + timedelta(days=offset) for offset in range(OBSERVATION_SPAN + 1)]
WEEKDAYS = [day for day in EVERY_DAY if day.weekday() < 5]
HELD_RETURNS = {
    1: [round(0.008 * math.sin(index * 0.6) + 0.0006, 10) for index in range(OBSERVATION_SPAN)],
    2: [round(0.005 * math.cos(index * 0.4) - 0.0002, 10) for index in range(OBSERVATION_SPAN)],
}
BENCHMARK_RETURNS = [round(0.006 * math.sin(index * 0.5 + 0.3), 10) for index in range(OBSERVATION_SPAN)]


def with_quote_dates(prepared: PreparedAssetSeriesSet, quote_dates: dict[int, list[date]]) -> PreparedAssetSeriesSet:
    """The same prepared set, each series declaring the genuine quote dates it came from."""
    series = [PreparedAssetSeries.model_validate({**item.model_dump(), "quote_dates": quote_dates.get(item.valuations.asset_id, [])}) for item in prepared.series]
    return prepared.model_copy(update={"series": series})


def twrr_read_on(observation_days: list[date]) -> tuple[list[date], list[float]]:
    """The TWRR read on `observation_days` after the baseline: dates, and chain-linked period returns."""
    cumulative = {point_date: float(value) for point_date, value in twrr_history(DAILY_TWRR, start=OBSERVATION_START)}
    days = [OBSERVATION_START, *[day for day in observation_days if day > OBSERVATION_START]]
    return days[1:], [(1 + cumulative[current]) / (1 + cumulative[previous]) - 1 for previous, current in zip(days, days[1:], strict=False)]


async def observe_the_portfolio_twrr(
    monkeypatch,
    *,
    holdings: dict[int, str],
    prepared: PreparedAssetSeriesSet,
    analytics: tuple[dict[str, object], ...] = (SPY,),
) -> tuple[RiskExecutionContext, dict[str, RiskAnalyticResult]]:
    """One historical request on the whole portfolio: the context the spy saw, and the results by instance."""
    seen = install_context_spy(monkeypatch)

    async def no_holiday_table() -> frozenset[date]:
        return frozenset()

    # Never the real build here: these tests are about what the service does with the quote dates.
    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", no_holiday_table, raising=False)
    service = RiskService(db=EmptyRowsDb())
    install_portfolio_report(monkeypatch, service, slice_report(holdings=holdings, cash="100", twrr=twrr_history(DAILY_TWRR, start=OBSERVATION_START)))
    install_prepared_series(monkeypatch, service, prepared)
    response = await service.execute(user_id=7, request=slice_request(mode="historical", analytics=list(analytics), start=OBSERVATION_START, end=OBSERVATION_END))
    (context,) = seen
    return context, {item.instance_id: item for item in response.items}


@pytest.mark.asyncio
async def test_the_portfolio_twrr_is_read_only_on_the_days_a_held_asset_is_quoted(monkeypatch):
    prepared = with_quote_dates(make_prepared_set(HELD_RETURNS, baseline=OBSERVATION_START), {1: WEEKDAYS, 2: WEEKDAYS})

    context, results = await observe_the_portfolio_twrr(monkeypatch, holdings={1: "300", 2: "200"}, prepared=prepared, analytics=(SPY, TWRR_READERS["kpi"]))

    dates, returns = twrr_read_on(WEEKDAYS)
    assert len(dates) == 24  # the weekdays after the baseline Monday
    assert context.primary_return_basis == RiskReturnBasis.TWRR
    assert context.primary_baseline_date == OBSERVATION_START
    assert list(context.primary_return_dates) == dates
    # Monday's return spans the weekend: (1 + cumulative on Monday) / (1 + cumulative on Friday) − 1.
    assert dates[dates.index(date(2026, 1, 12)) - 1] == date(2026, 1, 9)
    assert list(context.primary_returns) == pytest.approx(returns, rel=1e-12, abs=1e-15)
    # Chain-linked, the TWRR stays exact: the returns compound to its growth up to the last observation.
    cumulative = dict(twrr_history(DAILY_TWRR, start=OBSERVATION_START))
    assert math.prod(1 + value for value in context.primary_returns) == pytest.approx((1 + float(cumulative[date(2026, 2, 6)])) / (1 + float(cumulative[OBSERVATION_START])), rel=1e-12)
    assert context.n_observations == 24
    assert context.calendar_days == 32  # Monday 5 January to Friday 6 February
    assert context.annualization_factor == pytest.approx(24 * 365 / 32)
    # Observations over observation days — not over calendar days, which would read 24/32.
    assert context.coverage == pytest.approx(1.0)

    kpi = results["kpi"]
    assert kpi.output is not None, kpi.error
    assert kpi.metadata.n_observations == 24
    assert kpi.metadata.annualization_factor == pytest.approx(24 * 365 / 32)
    assert kpi.metadata.coverage == pytest.approx(1.0)
    assert kpi.metadata.analyzed_range == DateRangeModel(start=date(2026, 1, 6), end=date(2026, 2, 6))


@pytest.mark.asyncio
async def test_a_benchmark_quote_does_not_make_an_observation_day(monkeypatch):
    held_holiday = date(2026, 1, 14)  # a Wednesday the held assets' exchange is closed
    held_days = [day for day in WEEKDAYS if day != held_holiday]
    prepared = with_quote_dates(
        make_prepared_set({**HELD_RETURNS, BENCHMARK_ASSET_ID: BENCHMARK_RETURNS}, baseline=OBSERVATION_START),
        {1: held_days, 2: held_days, BENCHMARK_ASSET_ID: EVERY_DAY},
    )

    context, _results = await observe_the_portfolio_twrr(monkeypatch, holdings={1: "300", 2: "200"}, prepared=prepared, analytics=(SPY, TWRR_READERS["comparison"]))

    # Neither the benchmark's weekends nor its Wednesday are observations: Thursday chain-links from Tuesday.
    dates, returns = twrr_read_on(held_days)
    assert held_holiday not in context.primary_return_dates
    assert list(context.primary_return_dates) == dates
    assert list(context.primary_returns) == pytest.approx(returns, rel=1e-12, abs=1e-15)
    assert context.annualization_factor == pytest.approx(23 * 365 / 32)


@pytest.mark.asyncio
async def test_the_comparison_keeps_the_benchmark_moves_between_two_observation_days(monkeypatch):
    """Benchmark returns on days no holding is quoted are compounded into the next pair, not dropped.

    Each TWRR return spans the days since the previous observation day; the benchmark's return over the
    same span is its own returns dated inside it, compounded. A date-by-date match paired Thursday's
    TWRR, which spans the held holiday, with the benchmark's Thursday move alone.
    """
    held_holiday = date(2026, 1, 14)  # a Wednesday the held assets' exchange is closed
    held_days = [day for day in WEEKDAYS if day != held_holiday]
    prepared = with_quote_dates(
        make_prepared_set({**HELD_RETURNS, BENCHMARK_ASSET_ID: BENCHMARK_RETURNS}, baseline=OBSERVATION_START),
        {1: held_days, 2: held_days, BENCHMARK_ASSET_ID: EVERY_DAY},
    )

    _context, results = await observe_the_portfolio_twrr(monkeypatch, holdings={1: "300", 2: "200"}, prepared=prepared, analytics=(SPY, TWRR_READERS["comparison"]))

    comparison = results["comparison"]
    assert comparison.output is not None, comparison.error
    dates, _returns = twrr_read_on(held_days)
    own = dict(zip(EVERY_DAY[1:], BENCHMARK_RETURNS, strict=True))

    def benchmark_move(start: date, end: date) -> float:
        return math.prod(1 + value for day, value in own.items() if start < day <= end) - 1

    cumulative = {point.date: point.comparison_cumulative_return for point in comparison.output.series}
    assert list(cumulative) == dates
    # Thursday pairs with the benchmark's Wednesday and Thursday: its move on the held holiday is kept...
    assert (1 + cumulative[date(2026, 1, 15)]) / (1 + cumulative[date(2026, 1, 13)]) - 1 == pytest.approx(benchmark_move(date(2026, 1, 13), date(2026, 1, 15)), rel=1e-12)
    # ...and so are its weekends: Monday pairs with Saturday, Sunday and Monday.
    assert (1 + cumulative[date(2026, 1, 12)]) / (1 + cumulative[date(2026, 1, 9)]) - 1 == pytest.approx(benchmark_move(date(2026, 1, 9), date(2026, 1, 12)), rel=1e-12)
    # Over the window the benchmark returns what it returned, from the TWRR's baseline to the last observation.
    assert cumulative[dates[-1]] == pytest.approx(benchmark_move(OBSERVATION_START, dates[-1]), rel=1e-12)
    assert comparison.output.observations == comparison.metadata.n_observations == len(dates)
    assert comparison.metadata.coverage == pytest.approx(1.0)
    assert comparison.metadata.annualization_factor == pytest.approx(len(dates) * 365 / (dates[-1] - OBSERVATION_START).days)


@pytest.mark.asyncio
async def test_each_holding_meets_the_benchmark_on_the_joint_calendar_not_over_the_twrr_observation_spans(monkeypatch):
    """The reading chosen for k6 (06/10/2026): a holding is paired with the benchmark on the joint calendar.

    Holdings and benchmark were prepared together, so a holding pairs with the benchmark date for date,
    and its beta and correlation are the plain metrics of the two prepared series. The portfolio's own
    TWRR is read on observation days only, and its pairs compound the benchmark over those spans.
    Reading the holdings over the same spans was the other candidate. On this fixture it gives other
    numbers, which is the positive control that lets this pin tell the two readings apart.
    """
    held_holiday = date(2026, 1, 14)  # a Wednesday the held assets' exchange is closed
    held_days = [day for day in WEEKDAYS if day != held_holiday]
    prepared = with_quote_dates(
        make_prepared_set({**HELD_RETURNS, BENCHMARK_ASSET_ID: BENCHMARK_RETURNS}, baseline=OBSERVATION_START),
        {1: held_days, 2: held_days, BENCHMARK_ASSET_ID: EVERY_DAY},
    )

    context, results = await observe_the_portfolio_twrr(monkeypatch, holdings={1: "300", 2: "200"}, prepared=prepared, analytics=(SPY, TWRR_READERS["comparison"]))

    # Premise: a historical TWRR, read on fewer days than the joint calendar the holdings sit on.
    assert context.primary_return_basis == RiskReturnBasis.TWRR
    assert list(prepared.joint_return_dates) == EVERY_DAY[1:]
    assert list(context.primary_return_dates) == twrr_read_on(held_days)[0]
    assert len(context.primary_return_dates) < len(prepared.joint_return_dates)

    def over_twrr_spans(returns: list[float]) -> list[float]:
        """`returns`, dated on the joint calendar, compounded over each span between two TWRR observation days."""
        own = dict(zip(EVERY_DAY[1:], returns, strict=True))
        starts = [context.primary_baseline_date, *context.primary_return_dates[:-1]]
        return [math.prod(1 + value for day, value in own.items() if start < day <= end) - 1 for start, end in zip(starts, context.primary_return_dates, strict=True)]

    expected: dict[int, tuple[float, float]] = {}
    for asset_id, returns in HELD_RETURNS.items():
        joint = (beta(returns, BENCHMARK_RETURNS), pearson_correlation(returns, BENCHMARK_RETURNS))
        spanned = (beta(over_twrr_spans(returns), over_twrr_spans(BENCHMARK_RETURNS)), pearson_correlation(over_twrr_spans(returns), over_twrr_spans(BENCHMARK_RETURNS)))
        # Positive control: the two readings are different numbers here, so the pin below can tell them apart.
        assert spanned[0] != pytest.approx(joint[0], rel=1e-3), (asset_id, spanned, joint)
        assert spanned[1] != pytest.approx(joint[1], rel=1e-3), (asset_id, spanned, joint)
        expected[asset_id] = joint

    comparison = results["comparison"]
    assert comparison.output is not None, comparison.error
    assert [item.asset_id for item in comparison.output.items] == [1, 2]
    for item in comparison.output.items:
        assert item.beta == pytest.approx(expected[item.asset_id][0], rel=1e-12), item.asset_id
        assert item.correlation == pytest.approx(expected[item.asset_id][1], rel=1e-12), item.asset_id


@pytest.mark.asyncio
async def test_the_benchmark_ratios_are_annualized_with_the_comparison_own_factor(monkeypatch):
    """The benchmark's Sharpe and Sortino use the factor of the pairs they are measured on (K7, 06/10/2026).

    The comparison annualizes over its own pairs, `len(pairs) * 365 / days since the first pair's span
    start`, and its volatility and expected return already do. On the joint-calendar fixture above
    that factor equals the context's — the TWRR's, which `require_annualization_factor` hands back — so
    a ratio annualized with the request's factor would read the same there. Here the benchmark is
    listed two days into the window: the TWRR still observes those two days (the held assets were
    quoted on them, though the joint calendar starts after), the comparison cannot pair them, and the
    two factors part. Only the comparison's own factor keeps the benchmark on its own line,
    `sharpe * volatility == expected - f * rf_p`.
    """
    listing = date(2026, 1, 7)  # the benchmark's first close, so the joint calendar's baseline
    offset = (listing - OBSERVATION_START).days
    benchmark_days = [day for day in EVERY_DAY if day > listing]  # the joint calendar's return dates
    held_holiday = date(2026, 1, 14)  # a Wednesday the held assets' exchange is closed
    held_days = [day for day in WEEKDAYS if day != held_holiday]
    prepared = with_quote_dates(
        make_prepared_set({**{asset_id: returns[offset:] for asset_id, returns in HELD_RETURNS.items()}, BENCHMARK_ASSET_ID: BENCHMARK_RETURNS[offset:]}, baseline=listing),
        {1: held_days, 2: held_days, BENCHMARK_ASSET_ID: benchmark_days},
    )
    rf, target = 0.03, 0.05
    comparison_request = {**TWRR_READERS["comparison"], "parameters": {**TWRR_READERS["comparison"]["parameters"], "risk_free_annual_rate": rf, "target_annual_return": target}}

    context, results = await observe_the_portfolio_twrr(monkeypatch, holdings={1: "300", 2: "200"}, prepared=prepared, analytics=(SPY, comparison_request))

    comparison = results["comparison"]
    assert comparison.output is not None, comparison.error
    factor = comparison.metadata.annualization_factor
    # The pairs, computed here: the TWRR dates the benchmark can answer, the first span opening at its
    # listing and every later one at the previous TWRR date.
    assert context.primary_return_basis == RiskReturnBasis.TWRR
    assert [day for day in context.primary_return_dates if day <= listing] == [date(2026, 1, 6), listing]
    paired_dates = [day for day in context.primary_return_dates if day > listing]
    own = dict(zip(benchmark_days, BENCHMARK_RETURNS[offset:], strict=True))
    starts = [listing, *paired_dates[:-1]]
    benchmark_pairs = [math.prod(1 + value for day, value in own.items() if start < day <= end) - 1 for start, end in zip(starts, paired_dates, strict=True)]
    assert comparison.output.observations == len(paired_dates)
    assert factor == pytest.approx(len(paired_dates) * 365 / (paired_dates[-1] - listing).days, rel=1e-12)
    # Positive control: here the comparison's factor is neither the context's, which the request's
    # factor would be, nor the prepared calendar's.
    assert factor != pytest.approx(context.annualization_factor, rel=1e-3)
    assert factor != pytest.approx(prepared.annualization_factor, rel=1e-3)

    output = comparison.output
    period_rate = math.expm1(math.log1p(rf) / factor)
    line = output.comparison_expected_annual_return - factor * period_rate
    assert output.comparison_sharpe * output.comparison_volatility == pytest.approx(line, rel=1e-12, abs=1e-15)
    # ...a line a Sharpe annualized with the context's factor would miss, so the identity can tell the two apart.
    assert annualized_sharpe(benchmark_pairs, context.annualization_factor, annual_risk_free_rate=rf) * output.comparison_volatility != pytest.approx(line, rel=1e-6)
    # The Sortino is measured on the same pairs with the same factor, and charged the target.
    assert output.comparison_sortino == pytest.approx(annualized_sortino(benchmark_pairs, factor, annual_target_return=target), rel=1e-12)


@pytest.mark.parametrize(
    ("holdings", "held_returns"),
    [
        pytest.param({UNPRICED_ASSET_ID: "300"}, {}, id="only-an-unpriced-holding"),
        pytest.param({1: "300", 2: "200"}, HELD_RETURNS, id="held-series-without-quote-dates"),
    ],
)
@pytest.mark.asyncio
async def test_without_any_held_quote_date_the_twrr_keeps_every_calendar_day(monkeypatch, holdings, held_returns):
    # The benchmark is quoted on weekdays only: were its dates taken for the scope's, the weekends would go.
    prepared = with_quote_dates(make_prepared_set({**held_returns, BENCHMARK_ASSET_ID: BENCHMARK_RETURNS}, baseline=OBSERVATION_START), {BENCHMARK_ASSET_ID: WEEKDAYS})
    if not held_returns:
        prepared = prepared.model_copy(update={"data_quality": DataQualityReport(unusable_assets=[DataQualityExcludedAsset(asset_id=UNPRICED_ASSET_ID, reason=DataQualityExclusionReason.MISSING_PRICE)])})

    context, _results = await observe_the_portfolio_twrr(monkeypatch, holdings=holdings, prepared=prepared, analytics=(SPY, TWRR_READERS["comparison"]))

    dates, returns = twrr_read_on(EVERY_DAY)
    assert list(context.primary_return_dates) == dates
    assert context.n_observations == OBSERVATION_SPAN
    assert context.annualization_factor == pytest.approx(365.0)
    assert list(context.primary_returns) == pytest.approx(returns, rel=1e-12, abs=1e-15)


@pytest.mark.asyncio
async def test_a_day_any_held_asset_is_quoted_is_an_observation(monkeypatch):
    # A held crypto is quoted on weekends: the union of the held quote dates keeps every day.
    prepared = with_quote_dates(make_prepared_set(HELD_RETURNS, baseline=OBSERVATION_START), {1: WEEKDAYS, 2: EVERY_DAY})

    context, _results = await observe_the_portfolio_twrr(monkeypatch, holdings={1: "300", 2: "200"}, prepared=prepared)

    dates, _returns = twrr_read_on(EVERY_DAY)
    assert list(context.primary_return_dates) == dates
    assert context.n_observations == OBSERVATION_SPAN


@pytest.mark.asyncio
async def test_the_first_twrr_point_is_the_baseline_even_on_a_day_nothing_held_is_quoted(monkeypatch):
    """A range that opens on a holiday is measured from its opening, not from the first quote after it.

    The first TWRR point is always kept as the baseline (developer's decision of 30/09/2026): only the
    points after it are read on observation days. Here the baseline Monday is a holiday of the held
    assets' exchange, so Tuesday's return chain-links from Monday's cumulative TWRR.
    """
    held_days = [day for day in WEEKDAYS if day != OBSERVATION_START]
    prepared = with_quote_dates(make_prepared_set(HELD_RETURNS, baseline=OBSERVATION_START), {1: held_days, 2: held_days})

    context, _results = await observe_the_portfolio_twrr(monkeypatch, holdings={1: "300", 2: "200"}, prepared=prepared)

    dates, returns = twrr_read_on(held_days)
    assert OBSERVATION_START not in held_days  # nothing held is quoted on the baseline
    assert context.primary_baseline_date == OBSERVATION_START
    assert list(context.primary_return_dates) == dates
    assert dates[0] == date(2026, 1, 6)
    assert list(context.primary_returns) == pytest.approx(returns, rel=1e-12, abs=1e-15)
    assert context.n_observations == 24
    assert context.calendar_days == 32  # Monday 5 January to Friday 6 February
