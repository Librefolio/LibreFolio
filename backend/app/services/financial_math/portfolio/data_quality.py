"""Data-quality helpers of the portfolio engine: the FX pair slug, the configured pair sets, and the data-quality report."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date as date_type
from datetime import timedelta

from sqlalchemy import select

from backend.app.db.models import FxConversionRoute
from backend.app.schemas.common import DateSpan, is_canonical_iso_currency, iso_currency_candidates, shown_currency_text, suggested_iso_currency
from backend.app.schemas.portfolio import (
    DataQualityIssue,
    DataQualityReport,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    StaleFxPair,
)
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, DailyStates, RowsBeforeFloor, ShareMismatch
from backend.app.services.financial_math.series_steps import merged_spans
from backend.app.utils.currency_units import minor_unit_factor


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


def transaction_implied_assets_to_report(
    implied_asset_ids: Iterable[int],
    last_quote_dates: Mapping[int, date_type | None],
    first_position_dates: Mapping[int, date_type],
    as_of: date_type,
    grace_days: int,
) -> set[int]:
    """The assets valued from their own trades on ``as_of`` that the data-quality report lists.

    A market price may simply not have landed yet (a BTP during its placement), so a grace of
    ``grace_days`` passes first. It counts from the asset's last market quote on or before
    ``as_of`` (developer decision 30): an asset quoted yesterday and bought again today is valued at
    today's trade, which is no gap, while a feed that stopped long ago is reported at once. An asset
    never quoted counts from its first position date, and is listed when that is unknown.
    """
    reported: set[int] = set()
    for asset_id in implied_asset_ids:
        start = last_quote_dates.get(asset_id) or first_position_dates.get(asset_id)
        if start is not None and (as_of - start).days <= grace_days:
            continue
        reported.add(asset_id)
    return reported


def build_data_quality_report(  # noqa: C901 — flat sequential issue-section assembly, one block per issue type
    daily_states: Sequence[DailyPortfolioState],
    missing_price_assets_dto: list | None = None,
    stale_prices_dto: list | None = None,
    missing_fx_pairs_dto: list | None = None,
    transaction_implied_assets_dto: list | None = None,
    missing_cost_basis_assets: list[tuple[int, str]] | None = None,
    invalid_split_assets: list[tuple[int, str]] | None = None,
    non_iso_currency_assets: list[tuple[int, str, str]] | None = None,
    report_currency: str | None = None,
    rows_before_floor: RowsBeforeFloor | None = None,
    valued_at_cost_assets_dto: list | None = None,
    classifier_warnings: list[str] | None = None,
    share_mismatches: Sequence[ShareMismatch] | None = None,
    mwrr_available: bool = True,
    configured_fx_pairs: set[str] | None = None,
    real_provider_fx_pairs: set[str] | None = None,
    period_from: date_type | None = None,
    period_to: date_type | None = None,
) -> DataQualityReport:
    """Aggregate the per-day data quality of ``daily_states`` into a DataQualityReport DTO.

    missing_price_assets_dto / stale_prices_dto / missing_fx_pairs_dto are
    pre-built DTO lists (caller constructs them with full asset/broker info).
    transaction_implied_assets_dto: assets valued at their last BUY or SELL price (no market price yet).
    valued_at_cost_assets_dto: assets with no price at all, valued at their book cost (J-17).
    missing_cost_basis_assets: (asset_id, name) of the assets with an acquisition whose cost
    is not known (a TRANSFER or ADJUSTMENT adding quantity without cost_basis_override): it
    counts at zero cost, so their purchase cost and P&L are incomplete.
    invalid_split_assets (MF-D4): (asset_id, name) of the assets with a SPLIT event whose stored ratio is unusable: it
    counts as missing (no ratio restates a trade price observed before it), so a valuation that rests on such a price may
    be wrong until the ratio is fixed on the asset's events.
    non_iso_currency_assets (E-19b): (asset_id, name, stored currency) of the held assets whose currency is not an ISO 4217
    code as stored (``978``, ``EURO``, ``eur``: what an earlier version saved as written). report_currency: the currency
    the report converts to. With the sides of the missing pairs, they make one NON_ISO_CURRENCY warning per stored value
    that is not canonical, and a missing pair with such a side is in no MISSING_FX_* issue: no FX pair can fix it.
    rows_before_floor (MF-SEC8-2a): the scope's transactions dated before 1 January 1900 (``EARLIEST_RANGE_START``), which
    an older version or a hand edit stored: they are replayed, but the histories start on the floor; one warning names
    their number and the earliest date, so the user corrects them.
    If None, the report still populates date-level fields.

    share_mismatches (J-43): the engine's linked internal pairs between brokers owned at
    different shares. Each leg counts at its own broker's share, so the gap between them is a
    result (D-MF4 = a); one INFO issue counts the pairs complete by ``period_to`` (a pair before
    ``period_from`` too: its result is in the cumulative figures), and
    ``share_mismatch_warnings`` names them. Neither changes ``data_quality_status``.

    period_from / period_to bound the window the caller is actually showing.
    ``daily_states`` always starts at the first transaction — ``get_summary``
    runs the engine with ``date_from=None`` on purpose, because cumulative
    figures need the whole history — so without these bounds a NAV gap from
    years ago is reported on a dashboard showing the last three months, and
    the user is told to fix something that changes nothing on screen. Every
    period figure is re-based (``period.period_pnl`` reads only
    the state at ``date_from`` and the one at ``date_to``; TWRR and MWRR are
    chained over period-scoped inputs), so a gap outside the window is
    genuinely invisible here. The day at ``period_from`` is kept: it is the
    opening state, and its NAV does move the period P&L.
    """
    incomplete_spans: list[tuple[date_type, date_type]] = []
    if isinstance(daily_states, DailyStates):
        # Every day of a segment shares its state's completeness (P4): no state is built
        incomplete_spans = [(segment.start, segment.end) for segment in daily_states.iter_segments(period_from, period_to) if not segment.state.nav_complete]
    else:
        incomplete_spans = [(s.date, s.date) for s in daily_states if not s.nav_complete and (period_from is None or s.date >= period_from) and (period_to is None or s.date <= period_to)]
    incomplete_nav_ranges = merged_spans(incomplete_spans)
    # The days one by one, until the risk side reads the ranges (workstream J removes them; D-P4)
    incomplete_nav = [first + timedelta(days=offset) for first, last in incomplete_nav_ranges for offset in range((last - first).days + 1)]
    incomplete_nav_days = sum((last - first).days + 1 for first, last in incomplete_nav_ranges)

    # NON_ISO_CURRENCY (E-19b): the stored values that are no ISO 4217 code, from the missing pairs' sides, the held assets
    # and the report currency; a missing pair with such a side leaves the MISSING_FX_* issues, which no FX pair can fix
    non_iso_values: set[str] = set()
    fixable_fx_pairs: list = []
    for item in missing_fx_pairs_dto or []:
        odd_sides = [side for side in _missing_pair_sides(item.pair, report_currency) if not is_canonical_iso_currency(side)]
        non_iso_values.update(odd_sides)
        if not odd_sides:
            fixable_fx_pairs.append(item)
    non_iso_assets_by_value: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for asset_id, name, currency in non_iso_currency_assets or []:
        if not is_canonical_iso_currency(currency):
            non_iso_assets_by_value[currency].append((asset_id, name))
            non_iso_values.add(currency)
    if report_currency is not None and not is_canonical_iso_currency(report_currency):
        non_iso_values.add(report_currency)

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

    # VALUED_AT_COST — warning: assets with no price at all (no quote, no BUY or SELL), counted at their
    # book cost as a declared estimate (developer's decision, J-17). The caller lists only assets with a
    # provider, past the grace: for a manual asset the cost is its intended value.
    if valued_at_cost_assets_dto:
        as_of_date = daily_states[-1].date.isoformat() if daily_states else None
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.VALUED_AT_COST,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.valuedAtCost",
                message_params={"count": len(valued_at_cost_assets_dto), "as_of_date": as_of_date},
                count=len(valued_at_cost_assets_dto),
                affected_asset_ids=[a.asset_id for a in valued_at_cost_assets_dto],
                affected_asset_names=[a.name for a in valued_at_cost_assets_dto],
                cta_action="navigate_asset",
                cta_target=str(valued_at_cost_assets_dto[0].asset_id),
                group_key="valued_at_cost",
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

    # INVALID_SPLIT_RATIO — warning (MF-D4): a SPLIT whose stored ratio is unusable counts as missing
    if invalid_split_assets:
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.INVALID_SPLIT_RATIO,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.invalidSplitRatio",
                message_params={"count": len(invalid_split_assets)},
                count=len(invalid_split_assets),
                affected_asset_ids=[asset_id for asset_id, _ in invalid_split_assets],
                affected_asset_names=[name for _, name in invalid_split_assets],
                cta_action="navigate_asset",
                cta_target=str(invalid_split_assets[0][0]),
                group_key="invalid_split_ratio",
            )
        )

    # NON_ISO_CURRENCY — warning (E-19b): one issue per stored value that is no ISO 4217 code, in the order of the values;
    # no CTA until the developer decides how such a code is corrected (D1/D2)
    for value in sorted(non_iso_values):
        issues.append(_non_iso_currency_issue(value, report_currency, non_iso_assets_by_value.get(value, [])))

    # TRANSACTIONS_BEFORE_FLOOR — warning (MF-SEC8-2a): rows dated before 1900, replayed, but the histories start on 1900
    if rows_before_floor is not None and rows_before_floor.count > 0:
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.TRANSACTIONS_BEFORE_FLOOR,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.transactionsBeforeFloor",
                message_params={"count": rows_before_floor.count, "earliest": rows_before_floor.earliest.isoformat()},
                count=rows_before_floor.count,
                group_key="transactions_before_floor",
            )
        )

    # MISSING_FX_MARKET / MISSING_FX_RATES — split missing route vs missing date data, among the pairs of ISO codes only
    if fixable_fx_pairs:
        configured_slugs = {normalize_fx_pair_slug(p) for p in (configured_fx_pairs or set())}
        real_provider_slugs = {normalize_fx_pair_slug(p) for p in (real_provider_fx_pairs or set())}
        # The days each pair misses: the movements' dates and the valuation days' ranges (D-P4), as day spans
        missing_by_slug: dict[str, list[tuple[date_type, date_type]]] = defaultdict(list)
        for item in fixable_fx_pairs:
            slug = normalize_fx_pair_slug(item.pair)
            missing_by_slug[slug].extend((day, day) for day in getattr(item, "dates", []) or [])
            missing_by_slug[slug].extend((span.start, span.end) for span in getattr(item, "ranges", []) or [])

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
            missing_spans = merged_spans(span for slug in configured_real_pairs for span in missing_by_slug[slug])
            date_from = missing_spans[0][0].isoformat() if missing_spans else ""
            date_to = missing_spans[-1][1].isoformat() if missing_spans else ""
            missing_days = sum((last - first).days + 1 for first, last in missing_spans)
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
                        "dates_count": missing_days,
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
    if incomplete_nav_ranges:
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.NAV_INCOMPLETE,
                severity=IssueSeverity.INFO,
                message_i18n_key="dataQuality.navIncomplete",
                message_params={
                    "count": incomplete_nav_days,
                    "date_from": incomplete_nav_ranges[0][0].isoformat(),
                    "date_to": incomplete_nav_ranges[-1][1].isoformat(),
                },
                count=incomplete_nav_days,
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

    # TRANSFER_SHARE_MISMATCH — info (J-43): the transfers between brokers owned at different shares, complete by period_to
    reported_mismatches = [mismatch for mismatch in share_mismatches or () if period_to is None or mismatch.date <= period_to]
    if reported_mismatches:
        issues.append(
            DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.TRANSFER_SHARE_MISMATCH,
                severity=IssueSeverity.INFO,
                message_i18n_key="dataQuality.transferShareMismatch",
                message_params={"count": len(reported_mismatches)},
                count=len(reported_mismatches),
                group_key="transfer_share_mismatch",
            )
        )

    return DataQualityReport(
        issues=issues,
        missing_price_assets=missing_price_assets_dto or [],
        missing_fx_pairs=missing_fx_pairs_dto or [],
        stale_prices=stale_prices_dto or [],
        incomplete_nav_dates=incomplete_nav,
        incomplete_nav_ranges=[DateSpan(start=first, end=last) for first, last in incomplete_nav_ranges],
        stale_fx_pairs=_stale_fx_pairs(daily_states, period_to),
        share_mismatch_warnings=[_share_mismatch_text(mismatch) for mismatch in reported_mismatches],
        warnings=classifier_warnings or [],
    )


def _stale_fx_pairs(daily_states: Sequence[DailyPortfolioState], period_to: date_type | None) -> list[StaleFxPair]:
    """The FX pairs stale on the valuation day (``period_to``, else the last day): each with the date of the stored row it
    reads and its age in days, oldest row first (D-P4, contract §3)."""
    if not daily_states:
        return []
    if isinstance(daily_states, DailyStates):
        day = daily_states.last_date if period_to is None else min(period_to, daily_states.last_date)
        state = daily_states.segment_at(day).state if day >= daily_states.first_date else None
    else:
        state = next((s for s in reversed(daily_states) if period_to is None or s.date <= period_to), None)
        day = state.date if state is not None else None
    # A state built by hand, without the field, has no stale pair
    stale = getattr(state, "stale_fx_pairs", None) if state is not None else None
    if not isinstance(stale, Mapping) or day is None:
        return []
    return [StaleFxPair(pair=pair, last_rate_date=row_date, stale_days=(day - row_date).days) for pair, row_date in sorted(stale.items(), key=lambda item: (item[1], item[0]))]


def _missing_pair_sides(pair: str, report_currency: str | None) -> tuple[str, ...]:
    """The two codes of a missing pair as its producers write it, ``FROM/TO`` with the stored codes (E-19b). The TO side
    is the report currency when the pair ends with it, so a stored value holding a ``/`` is never cut in two; otherwise the
    last ``/`` splits. A pair without ``/`` (an older dash form, ``EUR-USD``) gives no side: both count as ISO codes."""
    if "/" not in pair:
        return ()
    if report_currency and pair.endswith(f"/{report_currency}"):
        return pair[: -len(report_currency) - 1], report_currency
    from_side, _, to_side = pair.rpartition("/")
    return from_side, to_side


def _non_iso_currency_issue(value: str, report_currency: str | None, assets: Sequence[tuple[int, str]]) -> DataQualityIssue:
    """The NON_ISO_CURRENCY warning of one stored value (E-19b): its key says what the value stands for — one ISO code,
    several, or none — and whether it is the report's own currency. The value is quoted cut (``shown_currency_text``),
    whole in ``group_key``, which tells the issues of the code apart. A minor unit (``GBp``) gets no code: pence
    relabelled as pounds would count 100 times."""
    common = {
        "domain": IssueDomain.PORTFOLIO,
        "code": IssueCode.NON_ISO_CURRENCY,
        "severity": IssueSeverity.WARNING,
        "count": len(assets) or None,
        "affected_asset_ids": [asset_id for asset_id, _ in assets],
        "affected_asset_names": [name for _, name in assets],
        "group_key": f"non_iso_currency:{value}",
    }
    shown = shown_currency_text(value)
    minor_unit = minor_unit_factor(value) is not None
    suggestion = None if minor_unit else suggested_iso_currency(value)
    if value == report_currency:
        if suggestion:
            return DataQualityIssue(message_i18n_key="dataQuality.nonIsoReportCurrency", message_params={"value": shown, "suggestion": suggestion}, **common)
        return DataQualityIssue(message_i18n_key="dataQuality.nonIsoReportCurrencyUnknown", message_params={"value": shown}, **common)
    if suggestion:
        return DataQualityIssue(message_i18n_key="dataQuality.nonIsoCurrencySuggestion", message_params={"value": shown, "suggestion": suggestion}, **common)
    candidates = () if minor_unit else iso_currency_candidates(value)
    if len(candidates) > 1:
        return DataQualityIssue(message_i18n_key="dataQuality.nonIsoCurrencyCandidates", message_params={"value": shown, "candidates": ", ".join(candidates)}, **common)
    return DataQualityIssue(message_i18n_key="dataQuality.nonIsoCurrencyUnknown", message_params={"value": shown}, **common)


def _share_mismatch_text(mismatch: ShareMismatch) -> str:
    """One pair at different shares, in the shape of the classifier's warning (``Linked internal pair (id, id): …``)."""
    (low_id, high_id), (low_broker, high_broker), (low_share, high_share) = mismatch.tx_ids, mismatch.broker_ids, mismatch.shares
    return f"Linked internal pair ({low_id}, {high_id}): share mismatch broker {low_broker}={low_share} vs broker {high_broker}={high_share}, complete on {mismatch.date.isoformat()}"
