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
    RiskComparisonPoint,
    RiskCompositionPolicy,
    RiskDrawdownOutput,
    RiskDrawdownPoint,
    RiskDrawdownRecoveryStatus,
    RiskError,
    RiskErrorCode,
    RiskHistoricalReplayAudit,
    RiskHistoricalReplayExcludedAsset,
    RiskHistoricalReplayExclusionTreatment,
    RiskHistoricalReplayProxyAsset,
    RiskKpiOutput,
    RiskMode,
    RiskOutputKind,
    RiskQueryRequest,
    RiskResultMetadata,
    RiskResultStatus,
    RiskReturnBasis,
    RiskReturnItem,
    RiskReturnOutput,
    RiskSamplingStrategy,
    RiskScopeKind,
    RiskStressApplicationRule,
    RiskStressBucketAudit,
    RiskStressConfiguredBucketImpact,
    RiskStressImpact,
    RiskStressMethod,
    RiskStressOutput,
    RiskVarCvarBin,
    RiskVarCvarOutput,
)
from backend.app.schemas.risk_scenarios import (
    RiskHistoricalReplayScenario,
    RiskHypotheticalShockScenario,
    RiskScenarioDimension,
    RiskScenarioLocalizedText,
    RiskScenarioMissingHistoryPolicy,
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
        scope=RiskScopeKind.PORTFOLIO,
        scope_reference="portfolio:3,9",
        broker_ids=[9, 3],
        composition_as_of=date(2026, 1, 4),
        mode=RiskMode.HISTORICAL,
        return_basis=RiskReturnBasis.TWRR,
        algorithm_version="risk-test@1.0.0",
        computed_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    assert metadata.frequency.value == "daily"
    assert metadata.broker_ids == [3, 9]

    simulation_metadata = RiskResultMetadata.model_validate(
        {
            **metadata.model_dump(mode="json"),
            "sampling_method": RiskSamplingStrategy.QMC,
            "path_count": 1024,
            "sobol_start_index": 4096,
        },
    )
    assert simulation_metadata.sobol_start_index == 4096

    with pytest.raises(ValidationError, match="QMC metadata"):
        RiskResultMetadata.model_validate(
            {
                **metadata.model_dump(mode="json"),
                "sampling_method": "qmc",
                "path_count": 1024,
                "random_seed": 1,
            },
        )

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


def test_historical_replay_audit_is_strict_and_serializable():
    audit = RiskHistoricalReplayAudit(
        proxy_count=1,
        proxy_assets=[
            RiskHistoricalReplayProxyAsset(
                asset_id=7,
                proxy_asset_id=9,
            )
        ],
        excluded_count=1,
        excluded_assets=[
            RiskHistoricalReplayExcludedAsset(
                asset_id=11,
                weight=0.2,
                treatment=RiskHistoricalReplayExclusionTreatment.ZERO_RETURN_RESIDUAL,
            )
        ],
        excluded_weight_total=0.2,
        missing_history_policy=RiskScenarioMissingHistoryPolicy.MANUAL_PROXY_OR_EXCLUDE,
        composition_policy=RiskCompositionPolicy.CURRENT_BUY_AND_HOLD,
    )

    assert audit.model_dump(mode="json") == {
        "proxy_count": 1,
        "proxy_assets": [{"asset_id": 7, "proxy_asset_id": 9}],
        "excluded_count": 1,
        "excluded_assets": [
            {
                "asset_id": 11,
                "reason": "manual_exclusion",
                "weight": 0.2,
                "treatment": "zero_return_residual",
            }
        ],
        "excluded_weight_total": 0.2,
        "missing_history_policy": "manual_proxy_or_exclude",
        "composition_policy": "current_buy_and_hold",
        "proxy_series_usage": "returns_only",
    }

    with pytest.raises(ValidationError, match="proxy_count"):
        RiskHistoricalReplayAudit.model_validate(
            {
                **audit.model_dump(mode="json"),
                "proxy_count": 0,
            }
        )
    with pytest.raises(ValidationError, match="must differ"):
        RiskHistoricalReplayProxyAsset(
            asset_id=7,
            proxy_asset_id=7,
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

    portfolio_scope = PortfolioRiskScope(
        kind="portfolio",
        broker_ids=[9, 3],
    )
    assert portfolio_scope.broker_ids == [3, 9]

    with pytest.raises(ValidationError, match="asset_ids must be unique"):
        AssetSetRiskScope(kind="asset_set", asset_ids=[7, 7])
    with pytest.raises(ValidationError, match="broker_ids must be unique"):
        PortfolioRiskScope(kind="portfolio", broker_ids=[3, 3])
    with pytest.raises(ValidationError):
        PortfolioRiskScope(kind="portfolio", broker_ids=[])
    with pytest.raises(ValidationError):
        RiskQueryRequest.model_validate(
            {
                "scope": {"kind": "broker", "broker_id": 3},
                "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
                "target_currency": "EUR",
                "mode": "historical",
                "analytics": [
                    {
                        "instance_id": "legacy",
                        "analytic_code": "historical_kpi",
                    }
                ],
            }
        )
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
        algorithm_version="historical_kpi@2.0.0",
        computed_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    result = RiskAnalyticResult(
        instance_id="kpi-main",
        analytic_code="historical_kpi",
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
            analytic_code="historical_kpi",
            status=RiskResultStatus.OK,
        )
    with pytest.raises(ValidationError, match="require error"):
        RiskAnalyticResult(
            instance_id="bad",
            analytic_code="historical_kpi",
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


def test_risk_scenario_schemas_keep_localization_and_tags_typed():
    scenario = RiskHistoricalReplayScenario.model_validate(
        {
            "schema_version": 1,
            "id": "host_replay",
            "kind": "historical_replay",
            "tags": ["rates", "custom"],
            "name": {"it": "Replay host"},
            "description": {"it": "Scenario host"},
            "defaults": {
                "start": "2020-01-01",
                "end": "2020-01-31",
            },
        }
    )

    assert scenario.tags == ["custom", "rates"]
    assert scenario.name.resolve("fr") == "Replay host"
    assert RiskScenarioLocalizedText.model_validate({"es": "Solo español"}).resolve("de") == "Solo español"

    with pytest.raises(ValidationError, match="lowercase ASCII"):
        RiskHistoricalReplayScenario.model_validate(
            {
                **scenario.model_dump(mode="json"),
                "tags": ["Not_Canonical"],
            }
        )


def test_hypothetical_scenario_requires_other_for_sector_and_geography():
    payload = {
        "schema_version": 1,
        "id": "sector_shock",
        "kind": "hypothetical_shock",
        "name": {"en": "Sector shock"},
        "description": {"en": "Sector shock description"},
        "allowed_dimensions": ["sector"],
        "defaults": {
            "dimension": "sector",
            "bucket_shocks": {"Financials": -0.3},
        },
    }

    with pytest.raises(ValidationError, match="require an Other bucket"):
        RiskHypotheticalShockScenario.model_validate(payload)

    scenario = RiskHypotheticalShockScenario.model_validate(
        {
            **payload,
            "defaults": {
                "dimension": "sector",
                "bucket_shocks": {
                    "Financials": -0.3,
                    "Other": 0,
                },
            },
        }
    )
    assert scenario.defaults.bucket_shocks["Other"] == 0


def test_hypothetical_stress_output_keeps_bucket_audit_strict():
    output = RiskStressOutput(
        method=RiskStressMethod.HYPOTHETICAL,
        dimension=RiskScenarioDimension.SECTOR,
        classification_coverage=1,
        impacts=[
            RiskStressImpact(
                asset_id=7,
                shock_return=-0.16,
                dimension=RiskScenarioDimension.SECTOR,
                bucket_audit=[
                    RiskStressBucketAudit(
                        exposure_bucket_id="Technology",
                        exposure=0.6,
                        candidate_bucket_ids=["Technology", "Other"],
                        applied_bucket_id="Technology",
                        bucket_shock=-0.2,
                        shock_contribution=-0.12,
                        rule=RiskStressApplicationRule.DIRECT,
                    ),
                    RiskStressBucketAudit(
                        exposure_bucket_id="Financials",
                        exposure=0.4,
                        candidate_bucket_ids=["Other"],
                        applied_bucket_id="Other",
                        bucket_shock=-0.1,
                        shock_contribution=-0.04,
                        rule=RiskStressApplicationRule.OTHER,
                    ),
                ],
            )
        ],
        configured_buckets=[
            RiskStressConfiguredBucketImpact(
                bucket_id="Other",
                shock=-0.1,
                applied_asset_count=1,
                asset_exposure_total=0.4,
            ),
            RiskStressConfiguredBucketImpact(
                bucket_id="Technology",
                shock=-0.2,
                applied_asset_count=1,
                asset_exposure_total=0.6,
            ),
        ],
    )
    assert output.model_dump(mode="json")["impacts"][0]["bucket_audit"][1]["applied_bucket_id"] == "Other"

    with pytest.raises(ValidationError, match="must sum to 1"):
        RiskStressImpact(
            asset_id=7,
            shock_return=-0.1,
            dimension=RiskScenarioDimension.SECTOR,
            bucket_audit=[
                RiskStressBucketAudit(
                    exposure_bucket_id="Other",
                    exposure=0.5,
                    candidate_bucket_ids=["Other"],
                    applied_bucket_id="Other",
                    bucket_shock=-0.2,
                    shock_contribution=-0.1,
                    rule=RiskStressApplicationRule.OTHER,
                )
            ],
        )


def _drawdown_output(**overrides):
    base = {
        "current_drawdown": -0.02,
        "current_peak_date": date(2026, 1, 5),
        "current_drawdown_duration_days": 3,
        "maximum_drawdown": -0.25,
        "maximum_drawdown_peak_date": date(2026, 1, 2),
        "maximum_drawdown_trough_date": date(2026, 1, 4),
        "maximum_drawdown_recovery_status": RiskDrawdownRecoveryStatus.RECOVERED,
        "maximum_drawdown_recovery_date": date(2026, 1, 6),
        "maximum_drawdown_duration_days": 4,
        "maximum_drawdown_recovered_ratio": 1.0,
        "remaining_to_peak_ratio": 0.02,
        "available_start": date(2026, 1, 2),
        "available_end": date(2026, 1, 8),
        "n_observations": 6,
        "coverage": 1.0,
        "calculation_basis": "price_only_close",
        "return_basis": RiskReturnBasis.PRICE_ONLY,
    }
    base.update(overrides)
    return base


def test_risk_drawdown_output_serializes_and_round_trips_via_result():
    output = RiskDrawdownOutput(**_drawdown_output())
    payload = output.model_dump(mode="json")
    assert payload["kind"] == "drawdown"
    assert payload["maximum_drawdown_recovery_status"] == "recovered"

    result = RiskAnalyticResult(
        instance_id="dd",
        analytic_code="drawdown_summary",
        status=RiskResultStatus.OK,
        output=payload,
        metadata=RiskResultMetadata(
            analyzed_range=DateRangeModel(start=date(2026, 1, 2), end=date(2026, 1, 8)),
            n_observations=6,
            calendar_days=6,
            annualization_factor=6 * 365 / 6,
            coverage=1.0,
            currency="EUR",
            scope=RiskScopeKind.ASSET,
            scope_reference="asset:1",
            return_basis=RiskReturnBasis.PRICE_ONLY,
            algorithm_version="1.0.0",
            computed_at=datetime.now(UTC),
        ),
        data_quality=DataQualityReport(),
    )
    assert isinstance(result.output, RiskDrawdownOutput)
    assert result.output.kind == RiskOutputKind.DRAWDOWN


def test_risk_drawdown_output_no_drawdown_forbids_episode_dates():
    with pytest.raises(ValidationError, match="no_drawdown must not expose episode dates"):
        RiskDrawdownOutput(
            **_drawdown_output(
                current_drawdown=0.0,
                current_drawdown_duration_days=0,
                maximum_drawdown=0.0,
                maximum_drawdown_recovery_status=RiskDrawdownRecoveryStatus.NO_DRAWDOWN,
                maximum_drawdown_recovery_date=None,
                maximum_drawdown_duration_days=0,
                maximum_drawdown_recovered_ratio=None,
                remaining_to_peak_ratio=0.0,
            )
        )


def test_risk_drawdown_output_open_episode_forbids_recovery_date():
    with pytest.raises(ValidationError, match="open episodes must not expose a recovery date"):
        RiskDrawdownOutput(
            **_drawdown_output(
                maximum_drawdown_recovery_status=RiskDrawdownRecoveryStatus.OPEN,
                maximum_drawdown_recovered_ratio=0.4,
            )
        )


def test_risk_drawdown_output_recovered_requires_recovery_date():
    with pytest.raises(ValidationError, match="recovered episodes require a recovery date"):
        RiskDrawdownOutput(**_drawdown_output(maximum_drawdown_recovery_date=None))


def _risk_return_output(**overrides):
    base = {
        "portfolio_volatility": 0.06,
        "portfolio_expected_annual_return": 0.09,
        "cash_weight": 0.25,
        "items": [
            {
                "asset_id": 1,
                "weight": 0.5,
                "volatility": 0.29,
                "expected_annual_return": 0.46,
            },
            {
                "asset_id": 6,
                "weight": 0.25,
                "volatility": 0.88,
                "expected_annual_return": -0.11,
            },
        ],
    }
    base.update(overrides)
    return base


def test_risk_return_output_round_trips_through_the_discriminated_result_union():
    output = RiskReturnOutput(**_risk_return_output())
    payload = output.model_dump(mode="json")
    assert payload["kind"] == "risk_return"
    assert [item["asset_id"] for item in payload["items"]] == [1, 6]

    result = RiskAnalyticResult(
        instance_id="rr",
        analytic_code="asset_risk_return",
        status=RiskResultStatus.OK,
        output=payload,
        metadata=RiskResultMetadata(
            analyzed_range=DateRangeModel(start=date(2026, 1, 2), end=date(2026, 1, 8)),
            n_observations=6,
            calendar_days=6,
            annualization_factor=6 * 365 / 6,
            coverage=1.0,
            currency="EUR",
            scope=RiskScopeKind.PORTFOLIO,
            scope_reference="portfolio",
            mode=RiskMode.CURRENT_COMPOSITION,
            composition_policy=RiskCompositionPolicy.CURRENT_BUY_AND_HOLD,
            return_basis=RiskReturnBasis.PRICE_ONLY,
            algorithm_version="1.0.0",
            computed_at=datetime.now(UTC),
        ),
        data_quality=DataQualityReport(),
    )
    assert isinstance(result.output, RiskReturnOutput)
    assert result.output.kind == RiskOutputKind.RISK_RETURN

    # The plugin drops any holding it cannot measure a dispersion for, so a plot with
    # no points at all is a reachable state rather than a malformed one: the whole is
    # still measured on the primary series, and cash still accounts for the rest.
    empty = RiskReturnOutput(portfolio_volatility=0.06, portfolio_expected_annual_return=0.09)
    assert empty.items == []
    assert empty.cash_weight == 0
    assert RiskReturnOutput.model_validate(empty.model_dump(mode="json")) == empty


def test_risk_return_output_bounds_the_risk_axis_but_not_the_reward_axis():
    """The asymmetry the two constraints encode, one case per axis.

    A holding that lost money over the window has a negative expected return and has
    to stay plottable — clamping it at zero would move the point onto a coordinate
    nobody measured. A negative volatility is not a measurement but a sign error, and
    ``ge=0`` is what stops one reaching an axis.
    """
    losing = RiskReturnItem(asset_id=6, weight=0.25, volatility=0.88, expected_annual_return=-0.11)
    assert losing.expected_annual_return < 0
    assert RiskReturnOutput(**_risk_return_output(portfolio_expected_annual_return=-0.4)).portfolio_expected_annual_return < 0

    with pytest.raises(ValidationError):
        RiskReturnItem(asset_id=6, weight=0.25, volatility=-0.88, expected_annual_return=-0.11)
    with pytest.raises(ValidationError):
        RiskReturnOutput(**_risk_return_output(portfolio_volatility=-0.01))
    with pytest.raises(ValidationError):
        RiskReturnOutput(**_risk_return_output(cash_weight=-0.01))
    with pytest.raises(ValidationError):
        RiskReturnItem(asset_id=0, weight=0.25, volatility=0.88, expected_annual_return=-0.11)
    with pytest.raises(ValidationError):
        RiskReturnOutput(**_risk_return_output(portfolio_volatility=float("nan")))

    # The pair is published *because* the slope through a zero intercept already is
    # the Sharpe ratio. Adding it as a field would state it twice and let the two
    # disagree, so the strict model refuses the key rather than accepting a duplicate.
    with pytest.raises(ValidationError):
        RiskReturnOutput(**_risk_return_output(portfolio_sharpe=1.45))


def test_portfolio_scope_asset_slice_is_unique_sorted_and_bounded():
    scope = PortfolioRiskScope(
        kind="portfolio",
        broker_ids=[9, 3],
        asset_ids=[7, 2],
    )
    assert scope.kind == RiskScopeKind.PORTFOLIO
    assert scope.asset_ids == [2, 7]
    assert scope.model_dump(mode="json") == {
        "kind": "portfolio",
        "broker_ids": [3, 9],
        "asset_ids": [2, 7],
    }
    assert PortfolioRiskScope(kind="portfolio").asset_ids is None
    assert PortfolioRiskScope(kind="portfolio", asset_ids=list(range(1, 101))).asset_ids[-1] == 100

    sliced_request = RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "portfolio", "asset_ids": [4, 1]},
            "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
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
    assert isinstance(sliced_request.scope, PortfolioRiskScope)
    assert sliced_request.scope.kind == RiskScopeKind.PORTFOLIO
    assert sliced_request.scope.asset_ids == [1, 4]

    with pytest.raises(ValidationError, match="asset_ids must be unique"):
        PortfolioRiskScope(kind="portfolio", asset_ids=[3, 3])
    with pytest.raises(ValidationError):
        PortfolioRiskScope(kind="portfolio", asset_ids=[])
    with pytest.raises(ValidationError):
        PortfolioRiskScope(kind="portfolio", asset_ids=list(range(1, 102)))
    with pytest.raises(ValidationError):
        PortfolioRiskScope(kind="portfolio", asset_ids=[0])
    with pytest.raises(ValidationError):
        PortfolioRiskScope.model_validate({"kind": "portfolio", "asset_id": [1]})


def test_risk_result_metadata_asset_slice_requires_portfolio_scope():
    base = {
        "analyzed_range": DateRangeModel(start=date(2026, 1, 2), end=date(2026, 1, 4)),
        "n_observations": 2,
        "calendar_days": 2,
        "annualization_factor": 365.0,
        "coverage": 1.0,
        "currency": "EUR",
        "return_basis": RiskReturnBasis.PRICE_ONLY,
        "algorithm_version": "risk-test@1.0.0",
        "computed_at": datetime(2026, 1, 5, tzinfo=UTC),
    }
    metadata = RiskResultMetadata(
        **base,
        scope=RiskScopeKind.PORTFOLIO,
        scope_reference="portfolio:3,5/assets:2,7",
        broker_ids=[3, 5],
        sliced_asset_ids=[7, 2],
        mode=RiskMode.HISTORICAL,
    )
    assert metadata.sliced_asset_ids == [2, 7]
    assert metadata.model_dump(mode="json")["sliced_asset_ids"] == [2, 7]
    assert RiskResultMetadata(**base, scope=RiskScopeKind.PORTFOLIO, scope_reference="portfolio:3,5").sliced_asset_ids is None

    with pytest.raises(ValidationError, match="sliced_asset_ids must be unique"):
        RiskResultMetadata(
            **base,
            scope=RiskScopeKind.PORTFOLIO,
            scope_reference="portfolio:3,5/assets:7",
            sliced_asset_ids=[7, 7],
        )
    with pytest.raises(ValidationError, match="sliced_asset_ids cannot be empty"):
        RiskResultMetadata(
            **base,
            scope=RiskScopeKind.PORTFOLIO,
            scope_reference="portfolio:3,5",
            sliced_asset_ids=[],
        )
    with pytest.raises(ValidationError, match="sliced_asset_ids metadata requires portfolio scope"):
        RiskResultMetadata(
            **base,
            scope=RiskScopeKind.ASSET,
            scope_reference="asset:7",
            sliced_asset_ids=[7],
        )


# =============================================================================
# K1 — the three additive chart fields, and the three decisions ratified with them
#
# ``RiskVarCvarOutput.return_bins`` / ``.var_bin_edge`` and
# ``RiskDrawdownOutput.underwater_series`` exist so a client can draw the
# distribution and the underwater curve. Three decisions were ratified with them,
# and each is pinned below:
#
#   1. UNIT — decimal ratio everywhere, never percentages. ``-0.1`` is minus ten
#      percent, the same convention ``RiskComparisonPoint.primary_drawdown`` already
#      publishes. Percentage formatting stays a renderer concern.
#   2. TWO SIGN CONVENTIONS IN ONE OBJECT — ``return_bins`` and ``var_bin_edge`` live
#      in SIGNED RETURN space (losses negative), while ``value_at_risk`` and
#      ``conditional_value_at_risk`` on the SAME object are POSITIVE loss magnitudes,
#      because the producer applies a zero floor and the schema declares ``ge=0``.
#      D76 warns against exactly this, so it was accepted deliberately and is pinned
#      PER FIELD: a test that checks only one side would pass under a "harmonisation"
#      that broke the other.
#   3. TRIMMED BASELINE — ``underwater_series`` is a PER-OBSERVATION series. The
#      wealth grid it comes from spans ``(baseline, *dates)``, and the baseline entry
#      is dropped, as ``RiskComparisonPoint`` does with its ``[1:]`` slice.
#
# WHAT THIS LAYER CANNOT CHECK, recorded so no consumer over-trusts a 200:
#   * No field bound distinguishes a ratio from a percentage: a payload pre-scaled by
#     100 validates. The unit is a documented contract, not an enforced one.
#   * ``underwater_series`` has no length, ordering or alignment validator, so an
#     untrimmed (observation + 1) grid would validate here. Decision 3 is enforced by
#     the producer instead — ``drawdown_summary`` zips ``dates`` against
#     ``report.drawdowns[1:]`` with ``strict=True``, so dropping the slice raises.
#   * ``validate_return_bins`` polices ASCENDING LOWER BOUNDS ONLY. It does not
#     require contiguity, so a gapped or overlapping grid validates; a renderer must
#     not infer ``bins[i].upper_bound == bins[i + 1].lower_bound`` from a 200 alone.
#   * Bin counts are not required to sum to ``observations``.
# =============================================================================


def _chart_var_cvar_payload(**overrides):
    # Uniform 0.031-wide grid whose edges fall exactly on the negated VaR, which is the
    # shape ``return_distribution_histogram`` produces once it is pinned on ``var_bin_edge``.
    base = {
        "confidence_level": 0.95,
        "horizon_days": 1,
        "observations": 40,
        "value_at_risk": 0.031,
        "conditional_value_at_risk": 0.042,
        "return_bins": [
            RiskVarCvarBin(lower_bound=-0.093, upper_bound=-0.062, count=2),
            RiskVarCvarBin(lower_bound=-0.062, upper_bound=-0.031, count=6),
            RiskVarCvarBin(lower_bound=-0.031, upper_bound=0.0, count=13),
            RiskVarCvarBin(lower_bound=0.0, upper_bound=0.031, count=15),
            RiskVarCvarBin(lower_bound=0.031, upper_bound=0.062, count=4),
        ],
        "var_bin_edge": -0.031,
    }
    base.update(overrides)
    return base


def _chart_underwater_dates():
    # Six observation dates with a weekend gap, so nothing here can pass by assuming a
    # dense calendar. ``date(2026, 1, 1)`` is the pre-return baseline and is NOT a point.
    return [date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7), date(2026, 1, 8), date(2026, 1, 9)]


def _chart_underwater_series():
    # Coherent with the episode below: a dip already open at the first observation, a
    # new peak on the 5th, the -0.25 trough on the 6th, recovery on the 8th, fresh -0.03.
    depths = [-0.01, 0.0, -0.25, -0.12, 0.0, -0.03]
    return [RiskDrawdownPoint(date=observed, drawdown=depth) for observed, depth in zip(_chart_underwater_dates(), depths, strict=True)]


def _chart_drawdown_payload(**overrides):
    base = {
        "current_drawdown": -0.03,
        "current_peak_date": date(2026, 1, 8),
        "current_drawdown_duration_days": 1,
        "maximum_drawdown": -0.25,
        "maximum_drawdown_peak_date": date(2026, 1, 5),
        "maximum_drawdown_trough_date": date(2026, 1, 6),
        "maximum_drawdown_recovery_status": RiskDrawdownRecoveryStatus.RECOVERED,
        "maximum_drawdown_recovery_date": date(2026, 1, 8),
        "maximum_drawdown_duration_days": 3,
        "maximum_drawdown_recovered_ratio": 1.0,
        "remaining_to_peak_ratio": 0.03 / 0.97,
        "available_start": date(2026, 1, 2),
        "available_end": date(2026, 1, 9),
        "n_observations": 6,
        "coverage": 1.0,
        "calculation_basis": "price_only_close",
        "return_basis": RiskReturnBasis.PRICE_ONLY,
        "underwater_series": _chart_underwater_series(),
    }
    base.update(overrides)
    return base


def test_chart_series_fields_are_decimal_ratios_matching_the_comparison_point_convention():
    # Decision 1. ``-0.1`` means minus ten percent in every one of these fields, and it
    # is the SAME number ``RiskComparisonPoint`` has always published for a drawdown.
    comparison = RiskComparisonPoint(
        date=date(2026, 1, 6),
        primary_cumulative_return=-0.1,
        comparison_cumulative_return=0.04,
        primary_drawdown=-0.1,
        comparison_drawdown=-0.02,
    )
    underwater = RiskDrawdownPoint(date=date(2026, 1, 6), drawdown=-0.1)
    assert underwater.drawdown == comparison.primary_drawdown
    assert underwater.model_dump(mode="json")["drawdown"] == comparison.model_dump(mode="json")["primary_drawdown"] == -0.1

    # Both sides of the convention reject the mirrored sign, so neither model can be
    # quietly flipped into "positive depth" without this failing.
    with pytest.raises(ValidationError, match="less than or equal to 0"):
        RiskDrawdownPoint(date=date(2026, 1, 6), drawdown=0.1)
    with pytest.raises(ValidationError, match="less than or equal to 0"):
        RiskComparisonPoint(
            date=date(2026, 1, 6),
            primary_cumulative_return=-0.1,
            comparison_cumulative_return=0.04,
            primary_drawdown=0.1,
            comparison_drawdown=-0.02,
        )

    # The ratios survive JSON unscaled: no serializer multiplies by 100 on the way out.
    var_payload = RiskVarCvarOutput(**_chart_var_cvar_payload()).model_dump(mode="json")
    assert var_payload["return_bins"][0]["lower_bound"] == -0.093
    assert var_payload["return_bins"][-1]["upper_bound"] == 0.062
    assert var_payload["var_bin_edge"] == -0.031
    assert var_payload["value_at_risk"] == 0.031
    drawdown_payload = RiskDrawdownOutput(**_chart_drawdown_payload()).model_dump(mode="json")
    assert [point["drawdown"] for point in drawdown_payload["underwater_series"]] == [-0.01, 0.0, -0.25, -0.12, 0.0, -0.03]
    # A ten-percent decline is a tenth, never a ten: the bins that a percentage payload
    # would need are two orders of magnitude wider than the ones this contract carries.
    assert max(abs(point["drawdown"]) for point in drawdown_payload["underwater_series"]) < 1.0


def test_var_cvar_output_carries_positive_tail_magnitudes_and_a_negative_return_space_bin_edge():
    # Decision 2, demonstrated on ONE object: two opposite sign conventions coexist.
    output = RiskVarCvarOutput(**_chart_var_cvar_payload())

    # Loss-magnitude half — positive, floored at zero by the producer and by ``ge=0``.
    assert output.value_at_risk > 0
    assert output.conditional_value_at_risk > 0
    assert output.conditional_value_at_risk >= output.value_at_risk

    # Signed-return half — the cut is negative, and the histogram spans both sides of
    # zero because it has to show the gains as well as the tail.
    assert output.var_bin_edge is not None
    assert output.var_bin_edge < 0
    assert output.var_bin_edge == -output.value_at_risk
    assert min(item.lower_bound for item in output.return_bins) < 0
    assert max(item.upper_bound for item in output.return_bins) > 0
    # The crossing point is a real bin boundary, not an interpolated one.
    assert output.var_bin_edge in {item.lower_bound for item in output.return_bins} | {item.upper_bound for item in output.return_bins}

    # PER FIELD, identified by ERROR LOCATION rather than by message. A payload that
    # made both fields negative at once was measured BLIND to removing either floor:
    # each field's surviving constraint stood in for the other's, and the ``pytest.raises``
    # passed for the wrong reason. One field is moved at a time, and the error has to be
    # that field's ``ge=0`` — a model-level ordering complaint does not count.
    for field in ("value_at_risk", "conditional_value_at_risk"):
        overrides = {"value_at_risk": 0.0, "conditional_value_at_risk": 0.0, "var_bin_edge": None, field: -0.031}
        with pytest.raises(ValidationError) as caught:
            RiskVarCvarOutput(**_chart_var_cvar_payload(**overrides))
        errors = caught.value.errors()
        assert [item["loc"] for item in errors] == [(field,)]
        assert errors[0]["type"] == "greater_than_equal"

    # And the other direction: the edge MUST stay free to be negative. Adding ``ge=0``
    # to ``var_bin_edge`` to "make the signs agree" would break exactly this line.
    assert RiskVarCvarOutput(**_chart_var_cvar_payload(var_bin_edge=-0.5)).var_bin_edge == -0.5

    # Both conventions survive serialization side by side, which is what the client reads.
    payload = output.model_dump(mode="json")
    assert payload["value_at_risk"] > 0 > payload["var_bin_edge"]


def test_underwater_series_is_a_per_observation_grid_that_excludes_the_baseline_point():
    # Decision 3. The wealth grid is (baseline, *dates); the published series is the
    # ``[1:]`` slice of it, so it has one point per observation and starts at the first
    # observation date, never at the baseline.
    output = RiskDrawdownOutput(**_chart_drawdown_payload())
    series = output.underwater_series

    assert len(series) == output.n_observations
    assert series[0].date == output.available_start
    assert series[-1].date == output.available_end
    assert [point.date for point in series] == sorted({point.date for point in series})

    # The tell of a trimmed series: its first point is a real observation and may
    # already be underwater. An untrimmed grid would lead with the baseline, which is
    # 0.0 by construction, and would carry ``n_observations + 1`` points.
    assert series[0].drawdown < 0
    assert output.available_start > date(2026, 1, 1)

    # ``[]`` means "this server does not publish the curve"; a genuinely flat series is
    # ``n_observations`` points of exactly 0.0. A renderer must not conflate them.
    absent = RiskDrawdownOutput(**{key: value for key, value in _chart_drawdown_payload().items() if key != "underwater_series"})
    assert absent.underwater_series == []
    flat = RiskDrawdownOutput(
        **_chart_drawdown_payload(
            current_drawdown=0.0,
            current_drawdown_duration_days=0,
            maximum_drawdown=0.0,
            maximum_drawdown_peak_date=None,
            maximum_drawdown_trough_date=None,
            maximum_drawdown_recovery_status=RiskDrawdownRecoveryStatus.NO_DRAWDOWN,
            maximum_drawdown_recovery_date=None,
            maximum_drawdown_duration_days=0,
            maximum_drawdown_recovered_ratio=None,
            remaining_to_peak_ratio=0.0,
            underwater_series=[RiskDrawdownPoint(date=observed, drawdown=0.0) for observed in _chart_underwater_dates()],
        )
    )
    assert len(flat.underwater_series) == flat.n_observations
    assert all(point.drawdown == 0.0 for point in flat.underwater_series)
    assert flat.underwater_series != absent.underwater_series


def test_chart_series_bounds_admit_no_floating_point_epsilon():
    # ``le=0`` and ``ge=0`` are exact: they carry no tolerance at all, so the producer's
    # ``min(0.0, value)`` / ``max(-value, 0.0)`` clamps are the only thing standing
    # between a sub-epsilon sign artefact and a 500 at the serialization boundary.
    # Anyone tempted to "simplify" a clamp away has to get past these four lines.
    for rejected in (1e-17, 1e-300, 5e-324):
        with pytest.raises(ValidationError, match="less than or equal to 0"):
            RiskDrawdownPoint(date=date(2026, 1, 6), drawdown=rejected)
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        RiskVarCvarOutput(**_chart_var_cvar_payload(value_at_risk=-5e-324, var_bin_edge=5e-324))

    # The boundary itself is admissible on both sides, including the negative zero a
    # clamp can hand back.
    assert RiskDrawdownPoint(date=date(2026, 1, 6), drawdown=0.0).drawdown == 0.0
    assert RiskDrawdownPoint(date=date(2026, 1, 6), drawdown=-0.0).drawdown == 0.0
    assert RiskVarCvarOutput(**_chart_var_cvar_payload(value_at_risk=0.0, conditional_value_at_risk=0.0, var_bin_edge=-0.0)).value_at_risk == 0.0

    # A bin count is a population: never negative, allowed to be empty.
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        RiskVarCvarBin(lower_bound=-0.062, upper_bound=-0.031, count=-1)
    assert RiskVarCvarBin(lower_bound=-0.062, upper_bound=-0.031, count=0).count == 0


def test_return_bins_are_policed_for_strictly_ascending_lower_bounds():
    # What the validator actually enforces, pinned as it is rather than as it reads:
    # strictly ascending ``lower_bound`` across the series, and a strictly positive
    # width within each bin. Contiguity is NOT among the guarantees (see the block
    # comment above), so this pins the rejections and claims nothing more.
    ascending = RiskVarCvarOutput(**_chart_var_cvar_payload())
    assert [item.lower_bound for item in ascending.return_bins] == sorted({item.lower_bound for item in ascending.return_bins})

    reversed_bins = list(reversed(_chart_var_cvar_payload()["return_bins"]))
    with pytest.raises(ValidationError, match="ordered by ascending lower_bound"):
        RiskVarCvarOutput(**_chart_var_cvar_payload(return_bins=reversed_bins))
    with pytest.raises(ValidationError, match="ordered by ascending lower_bound"):
        RiskVarCvarOutput(
            **_chart_var_cvar_payload(
                return_bins=[
                    RiskVarCvarBin(lower_bound=-0.031, upper_bound=0.0, count=13),
                    RiskVarCvarBin(lower_bound=-0.031, upper_bound=0.031, count=15),
                ]
            )
        )

    # A zero-width or inverted bin is not a degenerate bar, it is an unplottable one.
    with pytest.raises(ValidationError, match="upper_bound must be greater than lower_bound"):
        RiskVarCvarBin(lower_bound=-0.031, upper_bound=-0.031, count=1)
    with pytest.raises(ValidationError, match="upper_bound must be greater than lower_bound"):
        RiskVarCvarBin(lower_bound=0.0, upper_bound=-0.031, count=1)


def test_var_cvar_chart_fields_are_omissible_because_the_additive_design_rests_on_it():
    # THE LOAD-BEARING GUARANTEE OF K1, and the one that had no test.
    #
    # Both chart fields are additive: every consumer written before they existed — the
    # generated TypeScript client, the E2E mocks, any producer not yet taught to fill
    # them — keeps validating. That is not a convenience, it is the whole reason the
    # pair was introduced as ``default_factory``/``None`` rather than as required
    # fields. If either is later "tidied up" into a mandatory one, all of those break
    # at once, and this is the test that says so first.
    #
    # Built by SUBTRACTION from the live payload instead of from a hand-copied field
    # list, so a future required field added to the model fails here too rather than
    # escaping a stale literal.
    pre_k1 = {key: value for key, value in _chart_var_cvar_payload().items() if key not in {"return_bins", "var_bin_edge"}}
    assert set(pre_k1) == {"confidence_level", "horizon_days", "observations", "value_at_risk", "conditional_value_at_risk"}

    output = RiskVarCvarOutput(**pre_k1)
    assert output.return_bins == []
    assert output.var_bin_edge is None
    assert output.kind == RiskOutputKind.VAR_CVAR

    # ``None`` is NOT interchangeable with ``0.0``, and the difference is REACHABLE in
    # production rather than theoretical: the producer floors the tail at zero, so a
    # portfolio that never lost money across the window publishes ``value_at_risk ==
    # 0.0`` and therefore a cut at ``-0.0``. A renderer testing ``if not var_bin_edge``
    # would read "no cut published" off a well-formed result whose cut is simply at
    # zero — the one case where the two states are told apart only by ``is None``.
    at_zero = RiskVarCvarOutput(**_chart_var_cvar_payload(value_at_risk=0.0, conditional_value_at_risk=0.0, var_bin_edge=-0.0))
    assert at_zero.var_bin_edge is not None
    assert at_zero.var_bin_edge == 0.0

    # The two are INDEPENDENTLY omissible: a producer may publish the histogram without
    # pinning the cut, or pin the cut without the histogram. Neither half drags in the
    # other, so a partial migration is a valid state rather than a broken one.
    bins_only = {key: value for key, value in _chart_var_cvar_payload().items() if key != "var_bin_edge"}
    assert RiskVarCvarOutput(**bins_only).var_bin_edge is None
    edge_only = {key: value for key, value in _chart_var_cvar_payload().items() if key != "return_bins"}
    assert RiskVarCvarOutput(**edge_only).return_bins == []

    # What the client actually receives for an omitted pair: an empty array and a null,
    # both PRESENT in the serialized body rather than dropped, so the generated parser
    # meets the keys its schema declares.
    payload = output.model_dump(mode="json")
    assert payload["return_bins"] == []
    assert payload["var_bin_edge"] is None
    assert RiskVarCvarOutput.model_validate(payload) == output
