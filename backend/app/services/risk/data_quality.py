"""The data quality of a risk result: the plan's report, its merge, its warnings and an asset set's banner issues."""

from __future__ import annotations

import json
from collections.abc import Set as AbstractSet

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset
from backend.app.schemas.portfolio import (
    DataQualityExclusionReason,
    DataQualityIssue,
    DataQualityReport,
    IssueCode,
    IssueDomain,
    IssueSeverity,
)
from backend.app.schemas.risk import (
    RiskAnalyticResult,
    RiskReturnBasis,
    RiskScopeKind,
    RiskWarning,
)
from backend.app.services.financial_math.portfolio.data_quality import load_configured_fx_pair_sets, normalize_fx_pair_slug
from backend.app.services.platform.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.risk.base import (
    RiskExecutionContext,
    RiskSeriesInputs,
)
from backend.app.services.risk.plan import AnalyticPlan, is_historical_replay_plan, is_hypothetical_plan

_PRICE_EXCLUSION_REASONS = frozenset({DataQualityExclusionReason.MISSING_PRICE.value, "no_price_source"})


def _stale_price_ids(data_quality: DataQualityReport) -> list[int]:
    return sorted({item.asset_id for item in data_quality.stale_prices} | set(data_quality.carried_forward_price_asset_ids))


def _missing_price_ids(data_quality: DataQualityReport) -> list[int]:
    unusable = {item.asset_id for item in data_quality.unusable_assets if str(item.reason) in _PRICE_EXCLUSION_REASONS}
    return sorted({item.asset_id for item in data_quality.missing_price_assets} | unusable)


def _issue_asset_ids(data_quality: DataQualityReport) -> set[int]:
    return set(_stale_price_ids(data_quality)) | set(_missing_price_ids(data_quality))


def _issue_fx_pairs(data_quality: DataQualityReport) -> list[str]:
    """Every pair the report names, as the slug the FX pages and the banner's actions use."""
    raw = [*data_quality.unresolved_fx_pairs, *(item.pair for item in data_quality.missing_fx_pairs), *data_quality.carried_forward_fx_pairs]
    return sorted({normalize_fx_pair_slug(pair) for pair in raw})


def _asset_issue(code: IssueCode, severity: IssueSeverity, *, message_i18n_key: str, action: str, group_key: str, ids: list[int], names: dict[int, str]) -> DataQualityIssue:
    return DataQualityIssue(
        domain=IssueDomain.ASSET,
        code=code,
        severity=severity,
        message_i18n_key=message_i18n_key,
        message_params={"count": len(ids)},
        count=len(ids),
        affected_asset_ids=ids,
        affected_asset_names=[names.get(asset_id, f"#{asset_id}") for asset_id in ids],
        cta_action=action,
        cta_target=str(ids[0]),
        group_key=group_key,
    )


def _fx_issue(code: IssueCode, *, message_i18n_key: str, action: str, group_key: str, pairs: list[str], target: bool, extra: dict | None = None) -> DataQualityIssue:
    return DataQualityIssue(
        domain=IssueDomain.FOREX,
        code=code,
        severity=IssueSeverity.WARNING,
        message_i18n_key=message_i18n_key,
        message_params={"count": len(pairs), **(extra or {})},
        count=len(pairs),
        affected_fx_pairs=pairs,
        cta_action=action,
        cta_target=pairs[0] if target else None,
        group_key=group_key,
    )


def _data_quality_issues(data_quality: DataQualityReport, *, names: dict[int, str], configured_pairs: AbstractSet[str], provider_pairs: AbstractSet[str]) -> list[DataQualityIssue]:
    """The banner's issues for an asset set's report: one per category, `code + group_key` unique.

    The categories and their actions are the portfolio engine's, so the lab's banner reads like the
    Dashboard's: stale prices sync, a missing price opens the asset, a pair with no route asks for one,
    a pair with a provider syncs, a manual pair opens the pair. The sentences are the lab's own where the
    portfolio's speak of a NAV or of dates this report does not carry.
    """
    issues: list[DataQualityIssue] = []
    stale = _stale_price_ids(data_quality)
    if stale:
        issues.append(_asset_issue(IssueCode.STALE_PRICE, IssueSeverity.WARNING, message_i18n_key="dataQuality.stalePrice", action="sync_asset_prices", group_key="stale_price", ids=stale, names=names))
    missing = _missing_price_ids(data_quality)
    if missing:
        # A warning, not an error (developer and designer, 17/10): the analysis runs on the other assets, a partial
        # result still worth reading. The portfolio's MISSING_PRICE, out of the NAV, stays an error.
        issues.append(_asset_issue(IssueCode.MISSING_PRICE, IssueSeverity.WARNING, message_i18n_key="risk.quality.missingPrice", action="navigate_asset", group_key="missing_price", ids=missing, names=names))
    pairs = _issue_fx_pairs(data_quality)
    no_route = [pair for pair in pairs if pair not in configured_pairs]
    synced = [pair for pair in pairs if pair in configured_pairs and pair in provider_pairs]
    manual = [pair for pair in pairs if pair in configured_pairs and pair not in provider_pairs]
    if no_route:
        issues.append(_fx_issue(IssueCode.MISSING_FX_MARKET, message_i18n_key="risk.quality.missingFx", action="add_fx_pair", group_key="missing_fx", pairs=no_route, target=False))
    if synced:
        issues.append(_fx_issue(IssueCode.MISSING_FX_RATES, message_i18n_key="risk.quality.missingFxRates", action="sync_fx_pair", group_key="missing_fx_rates", pairs=synced, target=True, extra={"days": STALE_PRICE_THRESHOLD_DAYS}))
    if manual:
        issues.append(_fx_issue(IssueCode.MISSING_FX_RATES, message_i18n_key="risk.quality.missingFxRatesManual", action="navigate_fx", group_key="missing_fx_rates_manual", pairs=manual, target=True))
    return issues


def data_quality_warnings(data_quality: DataQualityReport) -> list[RiskWarning]:
    """One `data_quality_degraded` warning per cause, each naming what is affected.

    Excluded assets are not repeated here: `assets_excluded` already names them. A degraded report
    with none of the causes below still says so, in a generic sentence.
    """
    code = "data_quality_degraded"
    message = "Risk result uses incomplete or carried-forward source data."
    status = data_quality.data_quality_status.value
    warnings: list[RiskWarning] = []
    stale_ids = sorted({item.asset_id for item in data_quality.stale_prices} | set(data_quality.carried_forward_price_asset_ids))
    if stale_ids:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "stale_prices", "asset_ids": stale_ids}, message_i18n_key="risk.warnings.data_quality_stale_prices", message_params={"days": STALE_PRICE_THRESHOLD_DAYS}))
    if data_quality.carried_forward_fx_pairs:
        pairs = sorted(data_quality.carried_forward_fx_pairs)
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "stale_fx_rates", "pairs": pairs}, message_i18n_key="risk.warnings.data_quality_stale_fx_rates", message_params={"days": STALE_PRICE_THRESHOLD_DAYS, "pairs": ", ".join(pairs)}))
    missing_ids = sorted({item.asset_id for item in data_quality.missing_price_assets})
    if missing_ids:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "missing_prices", "asset_ids": missing_ids}, message_i18n_key="risk.warnings.data_quality_missing_prices"))
    fx_pairs = sorted(set(data_quality.unresolved_fx_pairs) | {item.pair for item in data_quality.missing_fx_pairs})
    if fx_pairs:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "missing_fx_rates", "pairs": fx_pairs}, message_i18n_key="risk.warnings.data_quality_missing_fx_rates", message_params={"pairs": ", ".join(fx_pairs)}))
    incomplete_dates = set(data_quality.incomplete_nav_dates) | set(data_quality.incomplete_book_value_dates) | set(data_quality.incomplete_allocation_dates) | set(data_quality.incomplete_valuation_dates)
    if incomplete_dates:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status, "cause": "incomplete_dates", "count": len(incomplete_dates)}, message_i18n_key="risk.warnings.data_quality_incomplete_dates", message_params={"count": len(incomplete_dates)}))
    if not warnings and not data_quality.unusable_assets:
        warnings.append(RiskWarning(code=code, message=message, details={"status": status}, message_i18n_key="risk.warnings.data_quality_degraded"))
    return warnings


def merge_data_quality(
    left: DataQualityReport,
    right: DataQualityReport,
) -> DataQualityReport:
    payload: dict[str, object] = {}
    for field_name in DataQualityReport.model_fields:
        left_value = getattr(left, field_name)
        right_value = getattr(right, field_name)
        if isinstance(left_value, int):
            payload[field_name] = left_value + right_value
            continue
        combined = [*left_value, *right_value]
        seen: set[str] = set()
        deduped = []
        for item in combined:
            if isinstance(item, BaseModel):
                key = item.model_dump_json()
            else:
                key = json.dumps(item, default=str, sort_keys=True)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        payload[field_name] = deduped
    return DataQualityReport.model_validate(payload)


async def with_asset_set_quality_issues(db: AsyncSession, items: list[RiskAnalyticResult]) -> list[RiskAnalyticResult]:
    """Give an asset set's reports the banner's issues, which only the portfolio engine builds (D373).

    The Asset Global lab shows the data-quality banner, with its «Sync» actions, above its notice. A
    portfolio's report carries the engine's issues; an asset set's report comes from series
    preparation, which builds none, so the banner could never appear there. They are built here, one
    per category, from the same lists `data_quality_warnings` words. Names are read once per
    response, and the FX routes only when some report names a pair.
    """
    reports = [item.data_quality for item in items if item.data_quality is not None]
    ids = sorted({asset_id for report in reports for asset_id in _issue_asset_ids(report)})
    names = dict((await db.execute(select(Asset.id, Asset.display_name).where(Asset.id.in_(ids)))).all()) if ids else {}
    configured: set[str] = set()
    with_provider: set[str] = set()
    if any(_issue_fx_pairs(report) for report in reports):
        # The portfolio's own reading of the routes, so the two banners split the pairs alike.
        configured, with_provider = await load_configured_fx_pair_sets(db)
    enriched: list[RiskAnalyticResult] = []
    for item in items:
        if item.data_quality is None:
            enriched.append(item)
            continue
        issues = _data_quality_issues(item.data_quality, names=names, configured_pairs=configured, provider_pairs=with_provider)
        enriched.append(item.model_copy(update={"data_quality": item.data_quality.model_copy(update={"issues": issues})}))
    return enriched


def plan_data_quality(
    plan: AnalyticPlan,
    context: RiskExecutionContext,
) -> DataQualityReport:
    if is_historical_replay_plan(plan) and context.historical_replay is not None:
        return context.historical_replay.data_quality
    if is_hypothetical_plan(plan):
        if context.scope_kind == RiskScopeKind.PORTFOLIO and context.portfolio_data_quality is not None:
            return context.portfolio_data_quality
        return DataQualityReport()
    if context.primary_return_basis == RiskReturnBasis.TWRR and context.portfolio_data_quality is not None:
        # Judged on the series it consumed. The TWRR is the portfolio's own, so its report is the
        # whole story for a PRIMARY reader. A benchmark is prepared on the scope's joint calendar,
        # which the assets excluded from the scope never entered: their entries are not its own.
        series_inputs = plan.analytic_class.series_inputs
        if series_inputs == RiskSeriesInputs.PRIMARY:
            return context.portfolio_data_quality
        if series_inputs == RiskSeriesInputs.PRIMARY_AND_BENCHMARK and context.prepared_data_quality is not None:
            benchmark_asset_id = getattr(plan.params, "comparison_asset_id", None)
            foreign_asset_ids = {item.asset_id for item in context.excluded_assets} - {benchmark_asset_id}
            prepared = context.prepared_data_quality
            return merge_data_quality(
                context.portfolio_data_quality,
                prepared.model_copy(update={"unusable_assets": [item for item in prepared.unusable_assets if item.asset_id not in foreign_asset_ids]}),
            )
    return context.data_quality
