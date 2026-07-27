"""Strict schema tests for canonical risk series and metadata."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import (
    DataQualityExcludedAsset,
    DataQualityExclusionReason,
    DataQualityReport,
    DataQualityStatus,
)
from backend.app.schemas.risk import (
    AssetReturnPoint,
    AssetReturnSeries,
    AssetRiskScope,
    AssetSetRiskScope,
    AssetValuationPoint,
    AssetValuationSeries,
    PortfolioRiskScope,
    PreparedAssetSeries,
    PreparedAssetSeriesSet,
    RiskAnalyticRequest,
    RiskAnalyticResult,
    RiskCompositionPolicy,
    RiskError,
    RiskErrorCode,
    RiskKpiOutput,
    RiskMode,
    RiskQueryRequest,
    RiskResultMetadata,
    RiskResultStatus,
    RiskReturnBasis,
    RiskScopeKind,
    RiskVarCvarOutput,
)


def make_valuation(
    valuation_date: date,
    target_close: str,
    *,
    effective_price_date: date | None = None,
) -> AssetValuationPoint:
    effective = effective_price_date or valuation_date
    return AssetValuationPoint(
        valuation_date=valuation_date,
        effective_price_date=effective,
        is_price_carried_forward=effective < valuation_date,
        native_close=Decimal(target_close) / Decimal("0.9"),
        native_currency="USD",
        fx_rate=Decimal("0.9"),
        fx_rate_date=valuation_date,
        target_close=Decimal(target_close),
        target_currency="EUR",
        price_source="fixture",
    )


def test_risk_schemas_serialize_strict_canonical_series():
    day_0 = date(2026, 1, 1)
    day_1 = date(2026, 1, 2)
    valuations = AssetValuationSeries(
        asset_id=7,
        target_currency="EUR",
        points=[
            make_valuation(day_0, "90"),
            make_valuation(day_1, "99"),
        ],
    )
    returns = AssetReturnSeries(
        asset_id=7,
        target_currency="EUR",
        points=[
            AssetReturnPoint(
                date=day_1,
                previous_valuation_date=day_0,
                value=0.1,
            )
        ],
    )
    prepared = PreparedAssetSeries(
        valuations=valuations,
        returns=returns,
    )
    result = PreparedAssetSeriesSet(
        requested_range=DateRangeModel(start=day_1, end=day_1),
        baseline_date=day_0,
        effective_range=DateRangeModel(start=day_1, end=day_1),
        target_currency="EUR",
        series=[prepared],
        joint_valuation_dates=[day_0, day_1],
        joint_return_dates=[day_1],
        n_observations=1,
        calendar_days=1,
        annualization_factor=365.0,
        calendar_coverage=1.0,
        fresh_quote_coverage=1.0,
        data_quality=DataQualityReport(),
        fx_fingerprint="0" * 64,
    )

    payload = result.model_dump(mode="json")
    assert payload["series"][0]["valuations"]["points"][0]["target_close"] == "90"
    assert payload["series"][0]["returns"]["return_basis"] == "price_only"
    assert payload["data_quality"]["data_quality_status"] == "ok"

    with pytest.raises(ValidationError):
        AssetReturnPoint.model_validate(
            {
                "date": day_1,
                "previous_valuation_date": day_0,
                "value": 0.1,
                "unexpected": True,
            }
        )


def test_risk_series_rejects_inconsistent_provenance_and_calendars():
    day_0 = date(2026, 1, 1)
    day_1 = date(2026, 1, 2)
    with pytest.raises(ValidationError, match="is_price_carried_forward"):
        AssetValuationPoint(
            valuation_date=day_1,
            effective_price_date=day_0,
            is_price_carried_forward=False,
            native_close=Decimal("100"),
            native_currency="EUR",
            fx_rate=Decimal("1"),
            target_close=Decimal("100"),
            target_currency="EUR",
        )

    with pytest.raises(ValidationError, match="annualization_factor"):
        PreparedAssetSeriesSet(
            requested_range=DateRangeModel(start=day_1, end=day_1),
            baseline_date=day_0,
            effective_range=DateRangeModel(start=day_1, end=day_1),
            target_currency="EUR",
            joint_valuation_dates=[day_0, day_1],
            joint_return_dates=[day_1],
            n_observations=1,
            calendar_days=1,
            annualization_factor=252.0,
            fx_fingerprint="0" * 64,
        )


def test_data_quality_status_is_derived_with_explicit_precedence():
    assert DataQualityReport().data_quality_status == DataQualityStatus.OK
    assert DataQualityReport(carried_forward_price_points=1).data_quality_status == DataQualityStatus.CARRIED_FORWARD
    partial = DataQualityReport(
        carried_forward_price_points=1,
        unusable_assets=[
            DataQualityExcludedAsset(
                asset_id=9,
                reason=DataQualityExclusionReason.MISSING_PRICE,
            )
        ],
    )
    assert partial.data_quality_status == DataQualityStatus.PARTIAL


def test_risk_result_metadata_enforces_observed_annualization_and_mode():
    metadata = RiskResultMetadata(
        analyzed_range=DateRangeModel(
            start=date(2026, 1, 2),
            end=date(2026, 1, 4),
        ),
        n_observations=2,
        calendar_days=2,
        annualization_factor=365.0,
        coverage=0.75,
        currency="EUR",
        mode=RiskMode.HISTORICAL,
        return_basis=RiskReturnBasis.TWRR,
        algorithm_version="risk-test@1.0.0",
        computed_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    assert metadata.frequency.value == "daily"

    with pytest.raises(ValidationError, match="annualization_factor"):
        RiskResultMetadata(
            analyzed_range=metadata.analyzed_range,
            n_observations=2,
            calendar_days=2,
            annualization_factor=252.0,
            coverage=1.0,
            currency="EUR",
            return_basis=RiskReturnBasis.TWRR,
            algorithm_version="risk-test@1.0.0",
            computed_at=datetime(2026, 1, 5, tzinfo=UTC),
        )

    with pytest.raises(ValidationError, match="timezone-aware"):
        RiskResultMetadata(
            analyzed_range=metadata.analyzed_range,
            n_observations=0,
            calendar_days=0,
            coverage=0.0,
            currency="EUR",
            return_basis=RiskReturnBasis.PRICE_ONLY,
            algorithm_version="risk-test@1.0.0",
            computed_at=datetime(2026, 1, 5),
        )


def test_risk_query_uses_strict_discriminated_scopes_and_mode_policy():
    request = RiskQueryRequest(
        scope=AssetSetRiskScope(kind="asset_set", asset_ids=[7, 9]),
        date_range=DateRangeModel(start=date(2026, 1, 1), end=date(2026, 1, 31)),
        target_currency="eur",
        mode=RiskMode.HISTORICAL,
        analytics=[
            RiskAnalyticRequest(
                instance_id="correlation-main",
                analytic_code="correlation",
            )
        ],
    )
    assert request.target_currency == "EUR"
    assert request.scope.kind == RiskScopeKind.ASSET_SET

    payload = request.model_dump(mode="json")
    assert payload["scope"] == {"kind": "asset_set", "asset_ids": [7, 9]}

    validated = RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "asset", "asset_id": 7},
            "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
            "target_currency": "EUR",
            "mode": "current_composition",
            "composition_policy": "current_buy_and_hold",
            "analytics": [
                {
                    "instance_id": "var-main",
                    "analytic_code": "historical_var",
                    "parameters": {"confidence_level": 0.95},
                }
            ],
        }
    )
    assert isinstance(validated.scope, AssetRiskScope)
    assert validated.composition_policy == RiskCompositionPolicy.CURRENT_BUY_AND_HOLD

    with pytest.raises(ValidationError, match="asset_ids must be unique"):
        AssetSetRiskScope(kind="asset_set", asset_ids=[7, 7])
    with pytest.raises(ValidationError, match="requires composition_policy"):
        RiskQueryRequest(
            scope=PortfolioRiskScope(kind="portfolio"),
            date_range=request.date_range,
            target_currency="EUR",
            mode=RiskMode.CURRENT_COMPOSITION,
            analytics=request.analytics,
        )
    with pytest.raises(ValidationError, match="instance_id values must be unique"):
        RiskQueryRequest(
            scope=PortfolioRiskScope(kind="portfolio"),
            date_range=request.date_range,
            target_currency="EUR",
            mode=RiskMode.HISTORICAL,
            analytics=[request.analytics[0], request.analytics[0]],
        )


def test_risk_result_contract_enforces_status_and_var_tail_ordering():
    metadata = RiskResultMetadata(
        analyzed_range=DateRangeModel(start=date(2026, 1, 2), end=date(2026, 1, 4)),
        n_observations=2,
        calendar_days=2,
        annualization_factor=365.0,
        coverage=1.0,
        currency="EUR",
        scope=RiskScopeKind.PORTFOLIO,
        mode=RiskMode.HISTORICAL,
        return_basis=RiskReturnBasis.TWRR,
        algorithm_version="portfolio_kpi@1.0.0",
        computed_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    result = RiskAnalyticResult(
        instance_id="kpi-main",
        analytic_code="portfolio_kpi",
        status=RiskResultStatus.OK,
        output=RiskKpiOutput(
            volatility=0.2,
            max_drawdown=-0.1,
            max_drawdown_duration_days=7,
            sharpe=1.2,
            sortino=1.6,
        ),
        metadata=metadata,
        data_quality=DataQualityReport(),
    )
    payload = result.model_dump(mode="json")
    assert payload["output"]["kind"] == "kpi"
    assert payload["metadata"]["scope"] == "portfolio"

    with pytest.raises(ValidationError, match="successful results require"):
        RiskAnalyticResult(
            instance_id="bad",
            analytic_code="portfolio_kpi",
            status=RiskResultStatus.OK,
        )
    with pytest.raises(ValidationError, match="require error"):
        RiskAnalyticResult(
            instance_id="bad",
            analytic_code="portfolio_kpi",
            status=RiskResultStatus.UNAVAILABLE,
        )

    unavailable = RiskAnalyticResult(
        instance_id="missing",
        analytic_code="unknown",
        status=RiskResultStatus.UNAVAILABLE,
        error=RiskError(
            code=RiskErrorCode.ANALYTIC_NOT_FOUND,
            message="Unknown analytic",
        ),
    )
    assert unavailable.error is not None

    with pytest.raises(ValidationError, match="conditional_value_at_risk"):
        RiskVarCvarOutput(
            confidence_level=0.95,
            horizon_days=1,
            observations=4,
            value_at_risk=0.2,
            conditional_value_at_risk=0.1,
        )
