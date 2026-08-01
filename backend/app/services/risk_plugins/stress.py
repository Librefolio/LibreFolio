"""Deterministic hypothetical and historical-replay stress analytics."""

from __future__ import annotations

import math
import re
from datetime import date
from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, PositiveInt, field_validator, model_validator

from backend.app.db.models import AssetType
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.risk import (
    RiskCompositionPolicy,
    RiskErrorCode,
    RiskExcludedAsset,
    RiskHistoricalReplayAudit,
    RiskHistoricalReplayExcludedAsset,
    RiskHistoricalReplayExclusionTreatment,
    RiskHistoricalReplayProxyAsset,
    RiskMode,
    RiskOutputKind,
    RiskReturnBasis,
    RiskScopeKind,
    RiskStressApplicationRule,
    RiskStressBucketAudit,
    RiskStressConfiguredBucketImpact,
    RiskStressImpact,
    RiskStressMethod,
    RiskStressOutput,
    RiskWarning,
)
from backend.app.schemas.risk_scenarios import (
    RiskScenarioDimension,
    RiskScenarioMissingHistoryPolicy,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskAssetClassification,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import (
    compounded_return,
    current_buy_and_hold_returns,
    hypothetical_stress_return,
)
from backend.app.utils.geo_utils import normalize_country_to_iso3
from backend.app.utils.sector_fin_utils import FinancialSector

_GROUP_BUCKET_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_SECTOR_BUCKETS = {sector.value.casefold(): sector.value for sector in FinancialSector}


class StressParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: RiskStressMethod
    dimension: Optional[RiskScenarioDimension] = None
    bucket_shocks: Dict[str, FiniteFloat] = Field(
        default_factory=dict,
        max_length=100,
    )
    replay_range: Optional[DateRangeModel] = None
    missing_history_policy: Optional[RiskScenarioMissingHistoryPolicy] = None
    proxy_assets: list[RiskHistoricalReplayProxyAsset] = Field(default_factory=list, max_length=100)
    excluded_assets: list[PositiveInt] = Field(default_factory=list, max_length=100)

    @field_validator("proxy_assets")
    @classmethod
    def normalize_proxy_assets(
        cls,
        value: list[RiskHistoricalReplayProxyAsset],
    ) -> list[RiskHistoricalReplayProxyAsset]:
        original_asset_ids = [item.asset_id for item in value]
        if len(original_asset_ids) != len(set(original_asset_ids)):
            raise ValueError("historical replay proxy assets must be unique")
        return sorted(value, key=lambda item: item.asset_id)

    @field_validator("excluded_assets")
    @classmethod
    def normalize_excluded_assets(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("historical replay excluded assets must be unique")
        return sorted(value)

    @field_validator("bucket_shocks")
    @classmethod
    def validate_bucket_shock_keys(
        cls,
        value: Dict[str, float],
    ) -> Dict[str, float]:
        if any(not isinstance(bucket, str) or not bucket.strip() for bucket in value):
            raise ValueError("hypothetical stress bucket IDs must be non-empty strings")
        if any(len(bucket.strip()) > 80 for bucket in value):
            raise ValueError("hypothetical stress bucket IDs must be at most 80 characters")
        return value

    @model_validator(mode="after")
    def validate_method_inputs(self) -> StressParams:
        if self.method == RiskStressMethod.HYPOTHETICAL:
            if self.dimension is None:
                raise ValueError("hypothetical stress requires one dimension")
            if not self.bucket_shocks:
                raise ValueError("hypothetical stress requires bucket_shocks")
            if self.replay_range is not None:
                raise ValueError("hypothetical stress cannot declare replay_range")
            if any(value < -1 for value in self.bucket_shocks.values()):
                raise ValueError("stress shocks must be greater than or equal to -1")
            if self.missing_history_policy is not None or self.proxy_assets or self.excluded_assets:
                raise ValueError("hypothetical stress cannot declare historical replay options")
            self.bucket_shocks = _normalize_bucket_shocks(
                self.dimension,
                self.bucket_shocks,
            )
        else:
            if self.replay_range is None:
                raise ValueError("historical replay requires replay_range")
            if self.dimension is not None or self.bucket_shocks:
                raise ValueError("historical replay cannot declare hypothetical shock options")
            if self.missing_history_policy is None:
                self.missing_history_policy = RiskScenarioMissingHistoryPolicy.MANUAL_PROXY_OR_EXCLUDE
            proxied_asset_ids = {item.asset_id for item in self.proxy_assets}
            overlap = proxied_asset_ids & set(self.excluded_assets)
            if overlap:
                raise ValueError(f"historical replay assets cannot be both proxied and excluded: {sorted(overlap)}")
        return self


def _amount(value: Optional[Decimal], return_value: float) -> Optional[Decimal]:
    if value is None:
        return None
    stable_return = Decimal(str(return_value)).quantize(Decimal("0.000000000001"))
    return value * stable_return


def _normalize_bucket_shocks(
    dimension: RiskScenarioDimension,
    bucket_shocks: Dict[str, float],
) -> Dict[str, float]:
    normalized: dict[str, float] = {}
    for raw_bucket, shock in bucket_shocks.items():
        bucket = raw_bucket.strip()
        if dimension == RiskScenarioDimension.ASSET_CLASS:
            bucket = bucket.upper()
            try:
                AssetType(bucket)
            except ValueError as exc:
                raise ValueError(f"unknown asset-class stress bucket: {raw_bucket}") from exc
        elif dimension == RiskScenarioDimension.SECTOR:
            canonical_sector = _SECTOR_BUCKETS.get(bucket.casefold())
            if canonical_sector is None:
                raise ValueError(f"unknown sector stress bucket: {raw_bucket}")
            bucket = canonical_sector
        else:
            if bucket.casefold() == "other":
                bucket = "Other"
            elif len(bucket) == 3 and bucket.isalpha():
                try:
                    bucket = normalize_country_to_iso3(bucket)
                except ValueError:
                    bucket = bucket.lower()
                    if not _GROUP_BUCKET_PATTERN.fullmatch(bucket):
                        raise ValueError(f"invalid geography group bucket: {raw_bucket}") from None
            else:
                bucket = bucket.lower()
                if not _GROUP_BUCKET_PATTERN.fullmatch(bucket):
                    raise ValueError(f"invalid geography group bucket: {raw_bucket}")
        if bucket in normalized:
            raise ValueError(f"duplicate stress bucket after normalization: {bucket}")
        normalized[bucket] = float(shock)

    if (
        dimension
        in {
            RiskScenarioDimension.SECTOR,
            RiskScenarioDimension.GEOGRAPHY,
        }
        and "Other" not in normalized
    ):
        raise ValueError("sector and geography stress require an Other bucket")
    return dict(sorted(normalized.items()))


def _classification_exposures(
    dimension: RiskScenarioDimension,
    classification: RiskAssetClassification,
) -> tuple[dict[str, float], bool]:
    if dimension == RiskScenarioDimension.ASSET_CLASS:
        return {classification.asset_class: 1.0}, False
    if dimension == RiskScenarioDimension.SECTOR:
        if classification.sector_exposures:
            return dict(classification.sector_exposures), False
        return {"Other": 1.0}, True
    if classification.geography_exposures:
        return dict(classification.geography_exposures), False
    return {"Other": 1.0}, True


def _resolve_bucket(
    *,
    dimension: RiskScenarioDimension,
    exposure_bucket_id: str,
    bucket_shocks: Dict[str, float],
    geography_groups: Dict[str, frozenset[str]],
    metadata_fallback: bool,
) -> tuple[list[str], Optional[str], float, RiskStressApplicationRule]:
    if metadata_fallback:
        return (
            ["Other"],
            "Other",
            bucket_shocks["Other"],
            RiskStressApplicationRule.MISSING_METADATA_OTHER,
        )

    if dimension == RiskScenarioDimension.ASSET_CLASS:
        if exposure_bucket_id not in bucket_shocks:
            return (
                [],
                None,
                0.0,
                RiskStressApplicationRule.UNCONFIGURED_ZERO,
            )
        return (
            [exposure_bucket_id],
            exposure_bucket_id,
            bucket_shocks[exposure_bucket_id],
            RiskStressApplicationRule.DIRECT,
        )

    if dimension == RiskScenarioDimension.SECTOR:
        candidates = [exposure_bucket_id, "Other"] if exposure_bucket_id in bucket_shocks and exposure_bucket_id != "Other" else ["Other"]
        applied = exposure_bucket_id if exposure_bucket_id in bucket_shocks else "Other"
        rule = RiskStressApplicationRule.DIRECT if applied != "Other" else RiskStressApplicationRule.OTHER
        return candidates, applied, bucket_shocks[applied], rule

    if exposure_bucket_id == "Other":
        return (
            ["Other"],
            "Other",
            bucket_shocks["Other"],
            RiskStressApplicationRule.OTHER,
        )

    candidates: list[str] = []
    if exposure_bucket_id in bucket_shocks:
        candidates.append(exposure_bucket_id)
    matching_groups = sorted(group_id for group_id, members in geography_groups.items() if group_id in bucket_shocks and exposure_bucket_id in members)
    candidates.extend(matching_groups)
    candidates.append("Other")

    if exposure_bucket_id in bucket_shocks:
        applied = exposure_bucket_id
        rule = RiskStressApplicationRule.COUNTRY
    elif matching_groups:
        if len(matching_groups) > 1:
            raise RiskUnavailableError(
                "Geography stress has ambiguous overlapping groups",
                code=RiskErrorCode.INVALID_PARAMETERS,
                details={
                    "country": exposure_bucket_id,
                    "group_ids": matching_groups,
                },
            )
        applied = matching_groups[0]
        rule = RiskStressApplicationRule.GEOGRAPHY_GROUP
    else:
        applied = "Other"
        rule = RiskStressApplicationRule.OTHER
    return candidates, applied, bucket_shocks[applied], rule


@register_plugin(RiskAnalyticRegistry)
class StressAnalytic(RiskAnalytic):
    analytic_code = "stress"
    algorithm_version = "3.0.0"
    name_i18n_key = "risk.analytics.stress.name"
    description_i18n_key = "risk.analytics.stress.description"
    output_kind = RiskOutputKind.STRESS
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.ASSET_SET,
        RiskScopeKind.PORTFOLIO,
    )
    supported_modes = (RiskMode.CURRENT_COMPOSITION,)
    params_model = StressParams
    min_observations = 1

    def compute(self, params, context):
        if params.method == RiskStressMethod.HYPOTHETICAL:
            return self._hypothetical(params, context)
        return self._historical(params, context)

    @staticmethod
    def _hypothetical(params, context):
        scope_asset_ids = context.requested_scope_asset_ids or context.scope_asset_ids
        missing_classifications = sorted(set(scope_asset_ids) - set(context.asset_classifications))
        if missing_classifications:
            raise RiskUnavailableError(
                "Hypothetical stress is missing canonical asset classifications",
                code=RiskErrorCode.DATA_UNAVAILABLE,
                details={"asset_ids": missing_classifications},
            )
        if params.dimension == RiskScenarioDimension.GEOGRAPHY:
            unknown_groups = sorted(bucket for bucket in params.bucket_shocks if bucket != "Other" and not (len(bucket) == 3 and bucket.isupper()) and bucket not in context.geography_groups)
            if unknown_groups:
                raise RiskUnavailableError(
                    "Hypothetical stress references unknown geography groups",
                    code=RiskErrorCode.INVALID_PARAMETERS,
                    details={"group_ids": unknown_groups},
                )

        shocks: dict[int, float] = {}
        audits_by_asset: dict[int, list[RiskStressBucketAudit]] = {}
        fallback_by_asset: dict[int, bool] = {}
        warnings: list[RiskWarning] = []
        configured_asset_ids: dict[str, set[int]] = {bucket: set() for bucket in params.bucket_shocks}
        configured_exposures = dict.fromkeys(params.bucket_shocks, 0.0)
        configured_contributions = dict.fromkeys(params.bucket_shocks, 0.0)

        for asset_id in scope_asset_ids:
            classification = context.asset_classifications[asset_id]
            exposures, metadata_fallback = _classification_exposures(
                params.dimension,
                classification,
            )
            fallback_by_asset[asset_id] = metadata_fallback
            if metadata_fallback:
                warnings.append(
                    RiskWarning(
                        code="hypothetical_metadata_other_fallback",
                        message=("Sector or geography metadata was unavailable; " "the asset was treated as Other at 100%."),
                        details={
                            "asset_id": asset_id,
                            "dimension": params.dimension.value,
                            "reason": (classification.metadata_error or "missing_classification_metadata"),
                        },
                        degrades_result=False,
                    )
                )

            audits: list[RiskStressBucketAudit] = []
            for exposure_bucket_id, exposure in sorted(exposures.items()):
                (
                    candidates,
                    applied_bucket,
                    bucket_shock,
                    rule,
                ) = _resolve_bucket(
                    dimension=params.dimension,
                    exposure_bucket_id=exposure_bucket_id,
                    bucket_shocks=params.bucket_shocks,
                    geography_groups=dict(context.geography_groups),
                    metadata_fallback=metadata_fallback,
                )
                shock_contribution = float(exposure) * bucket_shock
                audit = RiskStressBucketAudit(
                    exposure_bucket_id=exposure_bucket_id,
                    exposure=float(exposure),
                    candidate_bucket_ids=candidates,
                    applied_bucket_id=applied_bucket,
                    bucket_shock=bucket_shock,
                    shock_contribution=shock_contribution,
                    rule=rule,
                )
                audits.append(audit)
                if applied_bucket is not None:
                    configured_asset_ids[applied_bucket].add(asset_id)
                    configured_exposures[applied_bucket] += float(exposure)
                    if context.scope_kind == RiskScopeKind.PORTFOLIO:
                        configured_contributions[applied_bucket] += context.weights.get(asset_id, 0.0) * shock_contribution
            audits_by_asset[asset_id] = audits
            shocks[asset_id] = math.fsum(item.shock_contribution for item in audits)

        weighted_scope = context.scope_kind == RiskScopeKind.PORTFOLIO
        portfolio_return: Optional[float] = None
        contributions: dict[int, float] = {}
        if weighted_scope:
            portfolio_return, contributions = hypothetical_stress_return(
                shocks,
                {asset_id: context.weights[asset_id] for asset_id in scope_asset_ids},
            )
        elif context.scope_kind == RiskScopeKind.ASSET:
            portfolio_return = shocks[scope_asset_ids[0]]

        impacts = [
            RiskStressImpact(
                asset_id=asset_id,
                weight=context.weights.get(asset_id) if weighted_scope else None,
                shock_return=shock,
                contribution_return=contributions.get(asset_id),
                impact_amount=_amount(context.asset_values.get(asset_id), shock),
                dimension=params.dimension,
                metadata_fallback=fallback_by_asset[asset_id],
                bucket_audit=audits_by_asset[asset_id],
            )
            for asset_id, shock in shocks.items()
        ]
        configured_buckets = [
            RiskStressConfiguredBucketImpact(
                bucket_id=bucket,
                shock=shock,
                applied_asset_count=len(configured_asset_ids[bucket]),
                asset_exposure_total=configured_exposures[bucket],
                contribution_return=(configured_contributions[bucket] if weighted_scope else None),
            )
            for bucket, shock in params.bucket_shocks.items()
        ]
        analyzed_date = context.composition_as_of or context.requested_range.end or context.requested_range.start
        classification_coverage = math.fsum(0.0 if fallback_by_asset[asset_id] else 1.0 for asset_id in scope_asset_ids) / len(scope_asset_ids) if scope_asset_ids else 0.0
        return RiskComputation(
            output=RiskStressOutput(
                method=RiskStressMethod.HYPOTHETICAL,
                dimension=params.dimension,
                portfolio_return=portfolio_return,
                impact_amount=_amount(context.scope_value, portfolio_return) if portfolio_return is not None else None,
                classification_coverage=classification_coverage,
                impacts=impacts,
                configured_buckets=configured_buckets,
            ),
            method=f"hypothetical_shock_{params.dimension.value}",
            warnings=tuple(warnings),
            analyzed_range=DateRangeModel(
                start=analyzed_date,
                end=analyzed_date,
            ),
            n_observations=0,
            calendar_days=0,
            annualization_factor=None,
            coverage=classification_coverage,
            return_basis=RiskReturnBasis.PRICE_ONLY,
        )

    @staticmethod
    def _historical(params, context):
        replay = context.historical_replay
        if replay is None:
            raise RiskUnavailableError(
                "Historical replay series were not prepared",
                code=RiskErrorCode.DATA_UNAVAILABLE,
            )

        scope_asset_ids = context.requested_scope_asset_ids or context.scope_asset_ids
        excluded_asset_ids = set(replay.excluded_asset_ids)
        prepared_by_source = {item.returns.asset_id: item for item in replay.prepared_series.series}
        unusable_reasons = {item.asset_id: item.reason.value for item in replay.data_quality.unusable_assets}
        selected: dict[int, tuple[int, list[date], list[float]]] = {}
        for asset_id in scope_asset_ids:
            if asset_id in excluded_asset_ids:
                continue
            source_asset_id = replay.source_asset_ids[asset_id]
            prepared = prepared_by_source.get(source_asset_id)
            if prepared is None or not prepared.returns.points:
                is_proxy = source_asset_id != asset_id
                raise RiskUnavailableError(
                    (f"Historical replay proxy {source_asset_id} has insufficient usable history" if is_proxy else f"Asset {asset_id} requires a manual proxy or explicit exclusion"),
                    code=(RiskErrorCode.INVALID_PARAMETERS if is_proxy else RiskErrorCode.INSUFFICIENT_HISTORY),
                    details={
                        "asset_id": asset_id,
                        "return_source_asset_id": source_asset_id,
                        "reason": unusable_reasons.get(source_asset_id, "insufficient_history"),
                    },
                )
            selected[asset_id] = (
                source_asset_id,
                [point.date for point in prepared.returns.points],
                [float(point.value) for point in prepared.returns.points],
            )

        if selected and replay.prepared_series.n_observations == 0:
            raise RiskUnavailableError(
                "Historical replay has no observations in the requested range",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
            )

        asset_returns = {asset_id: compounded_return(values) for asset_id, (_source_asset_id, _dates, values) in selected.items()}
        weighted_scope = context.scope_kind == RiskScopeKind.PORTFOLIO
        portfolio_return: Optional[float] = None
        excluded_weight_total = sum(context.weights.get(asset_id, 0.0) for asset_id in excluded_asset_ids) if weighted_scope else 0.0
        if weighted_scope:
            if selected:
                portfolio_returns = current_buy_and_hold_returns(
                    {asset_id: values for asset_id, (_source_asset_id, _dates, values) in selected.items()},
                    {asset_id: context.weights[asset_id] for asset_id in selected},
                    cash_weight=context.cash_weight + excluded_weight_total,
                )
                portfolio_return = compounded_return(portfolio_returns)
            else:
                portfolio_return = 0.0
        elif context.scope_kind == RiskScopeKind.ASSET and asset_returns:
            portfolio_return = asset_returns[scope_asset_ids[0]]

        exclusion_treatment = RiskHistoricalReplayExclusionTreatment.ZERO_RETURN_RESIDUAL if weighted_scope else RiskHistoricalReplayExclusionTreatment.OMITTED_FROM_REPLAY
        excluded_audit = [
            RiskHistoricalReplayExcludedAsset(
                asset_id=asset_id,
                weight=context.weights.get(asset_id) if weighted_scope else None,
                treatment=exclusion_treatment,
            )
            for asset_id in sorted(excluded_asset_ids)
        ]
        audit = RiskHistoricalReplayAudit(
            proxy_count=len(params.proxy_assets),
            proxy_assets=params.proxy_assets,
            excluded_count=len(excluded_audit),
            excluded_assets=excluded_audit,
            excluded_weight_total=excluded_weight_total,
            missing_history_policy=params.missing_history_policy,
            composition_policy=context.composition_policy or RiskCompositionPolicy.CURRENT_BUY_AND_HOLD,
        )
        warnings: list[RiskWarning] = []
        if params.proxy_assets:
            warnings.append(
                RiskWarning(
                    code="historical_replay_proxies_used",
                    message="Historical replay used one or more manually selected proxy return series.",
                    details={"asset_ids": [item.asset_id for item in params.proxy_assets]},
                )
            )
        if excluded_audit:
            warnings.append(
                RiskWarning(
                    code="historical_replay_assets_excluded",
                    message="Historical replay omitted one or more assets using the declared exclusion policy.",
                    details={
                        "asset_ids": [item.asset_id for item in excluded_audit],
                        "treatment": exclusion_treatment.value,
                    },
                )
            )

        impacts = [
            RiskStressImpact(
                asset_id=asset_id,
                return_source_asset_id=source_asset_id,
                weight=context.weights.get(asset_id) if weighted_scope else None,
                shock_return=asset_returns[asset_id],
                contribution_return=(context.weights.get(asset_id, 0.0) * asset_returns[asset_id] if weighted_scope else None),
                impact_amount=_amount(context.asset_values.get(asset_id), asset_returns[asset_id]),
            )
            for asset_id, (source_asset_id, _dates, _values) in selected.items()
        ]
        if weighted_scope:
            impacts.extend(
                RiskStressImpact(
                    asset_id=asset_id,
                    weight=context.weights.get(asset_id),
                    shock_return=0.0,
                    contribution_return=0.0,
                    impact_amount=_amount(context.asset_values.get(asset_id), 0.0),
                )
                for asset_id in sorted(excluded_asset_ids)
            )

        prepared = replay.prepared_series
        analyzed_range = prepared.effective_range or params.replay_range
        return RiskComputation(
            output=RiskStressOutput(
                method=RiskStressMethod.HISTORICAL_REPLAY,
                portfolio_return=portfolio_return,
                impact_amount=_amount(context.scope_value, portfolio_return) if portfolio_return is not None else None,
                replay_range=params.replay_range,
                impacts=impacts,
            ),
            method="historical_replay_current_buy_and_hold",
            warnings=tuple(warnings),
            excluded_assets=tuple(
                RiskExcludedAsset(
                    asset_id=asset_id,
                    reason="manual_historical_replay_exclusion",
                )
                for asset_id in sorted(excluded_asset_ids)
            ),
            analyzed_range=analyzed_range,
            n_observations=prepared.n_observations,
            calendar_days=prepared.calendar_days,
            annualization_factor=prepared.annualization_factor,
            coverage=prepared.calendar_coverage,
            return_basis=RiskReturnBasis.PRICE_ONLY,
            historical_replay_audit=audit,
        )
