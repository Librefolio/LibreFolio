"""Data-quality helpers of the portfolio engine: the FX pair slug, the configured pair sets, and the data-quality report."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date as date_type

from sqlalchemy import select

from backend.app.db.models import FxConversionRoute
from backend.app.schemas.portfolio import (
    DataQualityIssue,
    DataQualityReport,
    IssueCode,
    IssueDomain,
    IssueSeverity,
)
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState


def normalize_fx_pair_slug(pair: str) -> str:
    """The slug of an FX pair: both codes upper-case, sorted, joined by a dash ("EUR/usd" -> "EUR-USD")."""
    parts = [p.strip().upper() for p in pair.replace("/", "-").split("-") if p.strip()]
    if len(parts) < 2:
        return pair.strip().upper()
    base, quote = sorted(parts[:2])
    return f"{base}-{quote}"


async def load_configured_fx_pair_sets(db) -> tuple[set[str], set[str]]:
    """Slugs ("AAA-BBB", alphabetical) of the configured FX pairs, and of those served by a real provider.

    A pair whose route only goes through the MANUAL sentinel is configured but has no provider
    to sync from; build_data_quality_report uses both sets to pick each missing pair's issue.
    """
    routes = (await db.execute(select(FxConversionRoute))).scalars().all()
    configured_pairs: set[str] = set()
    real_provider_pairs: set[str] = set()
    for route in routes:
        slug = normalize_fx_pair_slug(f"{route.base}/{route.quote}")
        configured_pairs.add(slug)
        if any(str(step.get("provider", "")).strip().upper() != "MANUAL" for step in route.parsed_steps):
            real_provider_pairs.add(slug)
    return configured_pairs, real_provider_pairs


def build_data_quality_report(  # noqa: C901 — flat sequential issue-section assembly, one block per issue type
    daily_states: Sequence[DailyPortfolioState],
    missing_price_assets_dto: list | None = None,
    stale_prices_dto: list | None = None,
    missing_fx_pairs_dto: list | None = None,
    transaction_implied_assets_dto: list | None = None,
    missing_cost_basis_assets: list[tuple[int, str]] | None = None,
    classifier_warnings: list[str] | None = None,
    mwrr_available: bool = True,
    configured_fx_pairs: set[str] | None = None,
    real_provider_fx_pairs: set[str] | None = None,
    period_from: date_type | None = None,
    period_to: date_type | None = None,
) -> DataQualityReport:
    """Aggregate the per-day data quality of ``daily_states`` into a DataQualityReport DTO.

    missing_price_assets_dto / stale_prices_dto / missing_fx_pairs_dto are
    pre-built DTO lists (caller constructs them with full asset/broker info).
    transaction_implied_assets_dto: assets valued at cost (no market price but WAC present).
    missing_cost_basis_assets: (asset_id, name) of the assets with an acquisition whose cost
    is not known (a TRANSFER or ADJUSTMENT adding quantity without cost_basis_override): it
    counts at zero cost, so their purchase cost and P&L are incomplete.
    If None, the report still populates date-level fields.

    period_from / period_to bound the window the caller is actually showing.
    ``daily_states`` always starts at the first transaction — ``get_summary``
    runs the engine with ``date_from=None`` on purpose, because cumulative
    figures need the whole history — so without these bounds a NAV gap from
    years ago is reported on a dashboard showing the last three months, and
    the user is told to fix something that changes nothing on screen. Every
    period figure is re-based (``_compute_period_summary_metrics`` reads only
    the state at ``date_from`` and the one at ``date_to``; TWRR and MWRR are
    chained over period-scoped inputs), so a gap outside the window is
    genuinely invisible here. The day at ``period_from`` is kept: it is the
    opening state, and its NAV does move the period P&L.
    """
    incomplete_nav: list[date_type] = []
    for s in daily_states:
        if s.nav_complete:
            continue
        if period_from is not None and s.date < period_from:
            continue
        if period_to is not None and s.date > period_to:
            continue
        incomplete_nav.append(s.date)

    # Build structured issues list
    issues: list[DataQualityIssue] = []

    # MISSING_PRICE — error: assets excluded from NAV
    if missing_price_assets_dto:
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MISSING_PRICE,
                severity=IssueSeverity.ERROR,
                message_i18n_key="dataQuality.missingPrice",
                message_params={"count": len(missing_price_assets_dto)},
                count=len(missing_price_assets_dto),
                affected_asset_ids=[a.asset_id for a in missing_price_assets_dto],
                affected_asset_names=[a.name for a in missing_price_assets_dto],
                cta_action="navigate_asset",
                cta_target=str(missing_price_assets_dto[0].asset_id),
                group_key="missing_price",
            )
        )

    # TRANSACTION_IMPLIED — warning: assets at cost (pre-market, e.g. BTP collocamento)
    if transaction_implied_assets_dto:
        as_of_date = daily_states[-1].date.isoformat() if daily_states else None
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.TRANSACTION_IMPLIED,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.transactionImplied",
                message_params={"count": len(transaction_implied_assets_dto), "as_of_date": as_of_date},
                count=len(transaction_implied_assets_dto),
                affected_asset_ids=[a.asset_id for a in transaction_implied_assets_dto],
                affected_asset_names=[a.name for a in transaction_implied_assets_dto],
                cta_action="navigate_asset",
                cta_target=str(transaction_implied_assets_dto[0].asset_id),
                group_key="transaction_implied",
            )
        )

    # STALE_PRICE — warning: market prices carried forward past the threshold. The CTA
    # syncs the affected assets' prices (the caller only reports provider assets).
    if stale_prices_dto:
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.STALE_PRICE,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.stalePrice",
                message_params={"count": len(stale_prices_dto)},
                count=len(stale_prices_dto),
                affected_asset_ids=[a.asset_id for a in stale_prices_dto],
                affected_asset_names=[a.name for a in stale_prices_dto],
                cta_action="sync_asset_prices",
                cta_target=str(stale_prices_dto[0].asset_id),
                group_key="stale_price",
            )
        )

    # MISSING_COST_BASIS — warning: an acquisition without a known cost counts at zero
    if missing_cost_basis_assets:
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MISSING_COST_BASIS,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.missingCostBasis",
                message_params={"count": len(missing_cost_basis_assets)},
                count=len(missing_cost_basis_assets),
                affected_asset_ids=[asset_id for asset_id, _ in missing_cost_basis_assets],
                affected_asset_names=[name for _, name in missing_cost_basis_assets],
                cta_action="navigate_asset",
                cta_target=str(missing_cost_basis_assets[0][0]),
                group_key="missing_cost_basis",
            )
        )

    # MISSING_FX_MARKET / MISSING_FX_RATES — split missing route vs missing date data
    if missing_fx_pairs_dto:
        configured_slugs = {normalize_fx_pair_slug(p) for p in (configured_fx_pairs or set())}
        real_provider_slugs = {normalize_fx_pair_slug(p) for p in (real_provider_fx_pairs or set())}
        missing_by_slug: dict[str, set[date_type]] = defaultdict(set)
        for item in missing_fx_pairs_dto:
            slug = normalize_fx_pair_slug(item.pair)
            missing_by_slug[slug].update(getattr(item, "dates", []) or [])

        not_configured_pairs: list[str] = []
        configured_real_pairs: list[str] = []
        configured_manual_pairs: list[str] = []
        for slug in sorted(missing_by_slug):
            if slug not in configured_slugs:
                not_configured_pairs.append(slug)
            elif slug in real_provider_slugs:
                configured_real_pairs.append(slug)
            else:
                configured_manual_pairs.append(slug)

        if not_configured_pairs:
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.MISSING_FX_MARKET,
                    severity=IssueSeverity.WARNING,
                    message_i18n_key="dataQuality.missingFx",
                    message_params={"count": len(not_configured_pairs)},
                    count=len(not_configured_pairs),
                    affected_fx_pairs=not_configured_pairs,
                    cta_action="add_fx_pair",
                    group_key="missing_fx",
                )
            )

        if configured_real_pairs:
            missing_dates = sorted({dt for slug in configured_real_pairs for dt in missing_by_slug[slug]})
            date_from = missing_dates[0].isoformat() if missing_dates else ""
            date_to = missing_dates[-1].isoformat() if missing_dates else ""
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.MISSING_FX_RATES,
                    severity=IssueSeverity.WARNING,
                    message_i18n_key="dataQuality.missingFxRates",
                    message_params={
                        "count": len(configured_real_pairs),
                        "date_from": date_from,
                        "date_to": date_to,
                        "dates_count": len(missing_dates),
                    },
                    count=len(configured_real_pairs),
                    affected_fx_pairs=configured_real_pairs,
                    cta_action="sync_fx_pair",
                    cta_target=configured_real_pairs[0],
                    group_key="missing_fx_rates",
                )
            )

        if configured_manual_pairs:
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.MISSING_FX_RATES,
                    severity=IssueSeverity.WARNING,
                    message_i18n_key="dataQuality.missingFxRatesManual",
                    message_params={"count": len(configured_manual_pairs)},
                    count=len(configured_manual_pairs),
                    affected_fx_pairs=configured_manual_pairs,
                    cta_action="navigate_fx",
                    cta_target=configured_manual_pairs[0],
                    group_key="missing_fx_rates_manual",
                )
            )

    # NAV_INCOMPLETE — info: some days had incomplete NAV
    if incomplete_nav:
        incomplete_nav_sorted = sorted(incomplete_nav)
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.NAV_INCOMPLETE,
                severity=IssueSeverity.INFO,
                message_i18n_key="dataQuality.navIncomplete",
                message_params={
                    "count": len(incomplete_nav_sorted),
                    "date_from": incomplete_nav_sorted[0].isoformat(),
                    "date_to": incomplete_nav_sorted[-1].isoformat(),
                },
                count=len(incomplete_nav_sorted),
                group_key="nav_incomplete",
            )
        )

    # MWRR_NOT_CALCULABLE — info
    if not mwrr_available:
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MWRR_NOT_CALCULABLE,
                severity=IssueSeverity.INFO,
                message_i18n_key="dataQuality.mwrrNotAvailable",
                group_key="mwrr",
            )
        )

    return DataQualityReport(
        issues=issues,
        missing_price_assets=missing_price_assets_dto or [],
        missing_fx_pairs=missing_fx_pairs_dto or [],
        stale_prices=stale_prices_dto or [],
        incomplete_nav_dates=incomplete_nav,
        warnings=classifier_warnings or [],
    )
