"""Whether an asset's quotes can take part in a risk analysis over a window.

One set of facts per asset and window — its own quotes, not the joint calendar — read in two ways:

- **analysis eligibility** (a period chosen by the user): an asset with no quote, no FX route or
  fewer quotes than the analytics accept cannot be selected; one that starts late or stops quoting
  before the end can, with a warning (developer's decision of 24/09/2026);
- **replay coverage** (the window of a historical crisis): a buy-and-hold replay compares the value
  at the start with the value at the end, so an asset must be priced at both ends. One that is not
  is excluded automatically instead of blocking the whole replay — and instead of silently moving
  the joint baseline, which would shorten the replay of every other asset.

Both readings measure lateness with the project's staleness threshold, so "late" means the same
thing as "stale" in the portfolio's data-quality banner.

When the chosen window is what excludes an asset, a *common period* can bring it back: for an
analysis, the span where every chosen asset is quoted; for a replay, the part of the crisis window
where the assets its edges exclude are priced. Both are proposals, verified on a second reading of
the facts before they are offered, and never applied on their own.

The rules are pure; `load_price_window_facts` is the only function that touches the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import AbstractSet, Iterable, Mapping, Optional, Sequence

from sqlalchemy import and_, case, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, PriceHistory
from backend.app.schemas.common import Currency
from backend.app.schemas.risk import RiskEligibilityLevel, RiskEligibilityReason, RiskHistoricalReplayExclusionReason
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS, STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.fx import convert_bulk


@dataclass(frozen=True, slots=True)
class PriceWindowFacts:
    """What one asset's own quotes say about one window.

    A quote is a stored price row, except a stored carry: a row dated on a weekend or a market holiday
    that repeats the close of the row before it (developer's decision of 30/09/2026, see
    `market_calendar`). Such rows are left out of every fact below.
    """

    first_quote: Optional[date]
    """Earliest quote in the asset's history, up to the window end."""
    last_quote: Optional[date]
    """Latest quote on or before the window end."""
    last_quote_before_start: Optional[date]
    """Latest quote strictly before the window start — the price a replay would start from."""
    quotes_in_window: int
    """Quotes dated inside the window, both ends included."""
    fx_available: bool = True
    """Whether the asset's currency converts into the target currency at both ends of the window."""
    first_quote_in_window: Optional[date] = None
    """Earliest quote inside the window, both ends included."""
    first_quote_ever: Optional[date] = None
    """Earliest quote of the asset's whole history, even after the window."""
    last_quote_ever: Optional[date] = None
    """Latest quote of the asset's whole history, even after the window."""


def _days(later: date, earlier: date) -> int:
    return (later - earlier).days


def analysis_eligibility(facts: PriceWindowFacts, window_start: date, window_end: date) -> tuple[RiskEligibilityLevel, tuple[RiskEligibilityReason, ...]]:
    """Whether an asset can take part in an analysis of `window_start..window_end`.

    Blocking reasons make it ineligible; otherwise lateness at either end is a warning. An asset with
    no quote at all is told apart from one with no quote in the period, because no period helps the
    first. The quote floor counts the asset's own quotes, so it is necessary but not sufficient: the
    analytics count returns on the joint calendar of the whole selection.
    """
    blocking: list[RiskEligibilityReason] = []
    if facts.quotes_in_window == 0 and facts.first_quote is None and facts.first_quote_ever is None:
        blocking.append(RiskEligibilityReason.NO_PRICE_HISTORY)
    elif facts.quotes_in_window == 0:
        blocking.append(RiskEligibilityReason.NO_PRICES)
    elif facts.quotes_in_window < RISK_MIN_OBSERVATIONS:
        blocking.append(RiskEligibilityReason.TOO_FEW_QUOTES)
    if not facts.fx_available:
        blocking.append(RiskEligibilityReason.MISSING_FX)
    if blocking:
        return RiskEligibilityLevel.INELIGIBLE, tuple(blocking)

    warnings: list[RiskEligibilityReason] = []
    if facts.first_quote is not None and _days(facts.first_quote, window_start) > STALE_PRICE_THRESHOLD_DAYS:
        warnings.append(RiskEligibilityReason.STARTS_LATE)
    if facts.last_quote is not None and _days(window_end, facts.last_quote) > STALE_PRICE_THRESHOLD_DAYS:
        warnings.append(RiskEligibilityReason.STALE_AT_END)
    if warnings:
        return RiskEligibilityLevel.WARNING, tuple(warnings)
    return RiskEligibilityLevel.ELIGIBLE, ()


def period_limits_coverage(facts: PriceWindowFacts, window_start: date, window_end: date) -> bool:
    """Whether the chosen period, not the asset's own history, is what leaves the asset short.

    True when the asset is quoted but not in the period, starts quoting more than the threshold after
    the period starts, or stops more than the threshold before it ends. Read from the facts rather
    than from the eligibility reasons, because a blocking reason hides the warnings: a late listing
    with too few quotes in the period reports only `too_few_quotes`, yet a period fitted to its
    history mends it. A never-quoted asset is never limited by the period.
    """
    if facts.quotes_in_window == 0 and facts.first_quote is None and facts.first_quote_ever is None:
        return False
    if facts.quotes_in_window == 0:
        return True
    starts_late = facts.first_quote is not None and _days(facts.first_quote, window_start) > STALE_PRICE_THRESHOLD_DAYS
    stale_at_end = facts.last_quote is not None and _days(window_end, facts.last_quote) > STALE_PRICE_THRESHOLD_DAYS
    return starts_late or stale_at_end


def replay_coverage(facts: PriceWindowFacts, window_start: date, window_end: date) -> Optional[RiskHistoricalReplayExclusionReason]:
    """Why an asset cannot be replayed over `window_start..window_end`, or `None` when it can.

    Covered at the start: a quote before the start no older than the threshold, or — for an asset
    listed inside the window — a first quote no later than the threshold after it. An asset quoted
    before the window but not recently (a gap, or a sparse rhythm such as a monthly NAV) is stale at
    the start, not a late starter. Covered at the end: a last quote no older than the threshold; the
    facts stop at the window end, so a gap and a delisting share one neutral reason.
    """
    if not facts.fx_available:
        return RiskHistoricalReplayExclusionReason.MISSING_FX
    has_quote_near_window = facts.quotes_in_window > 0 or (facts.last_quote_before_start is not None and _days(window_start, facts.last_quote_before_start) <= STALE_PRICE_THRESHOLD_DAYS)
    if not has_quote_near_window:
        return RiskHistoricalReplayExclusionReason.NO_PRICES_IN_WINDOW

    priced_at_start = facts.last_quote_before_start is not None and _days(window_start, facts.last_quote_before_start) <= STALE_PRICE_THRESHOLD_DAYS
    if not priced_at_start:
        if facts.first_quote is not None and facts.first_quote < window_start:
            return RiskHistoricalReplayExclusionReason.STALE_AT_WINDOW_START
        # A listing inside the window must begin quoting within the threshold after the start.
        if facts.first_quote is None or _days(facts.first_quote, window_start) > STALE_PRICE_THRESHOLD_DAYS:
            return RiskHistoricalReplayExclusionReason.STARTS_AFTER_WINDOW_START

    if facts.last_quote is None or _days(window_end, facts.last_quote) > STALE_PRICE_THRESHOLD_DAYS:
        return RiskHistoricalReplayExclusionReason.STALE_AT_WINDOW_END
    return None


_LATE_START_REASONS = frozenset({RiskHistoricalReplayExclusionReason.STARTS_AFTER_WINDOW_START, RiskHistoricalReplayExclusionReason.STALE_AT_WINDOW_START})
_EDGE_REASONS = _LATE_START_REASONS | {RiskHistoricalReplayExclusionReason.STALE_AT_WINDOW_END}


def common_quoted_range(facts: Iterable[PriceWindowFacts]) -> Optional[tuple[date, date]]:
    """The span in which every quoted asset has quotes: from the latest first quote to the earliest last.

    An asset without any quote is left out, since no period can include it. `None` when nothing is
    quoted or the spans do not overlap.
    """
    spans = [(item.first_quote_ever, item.last_quote_ever) for item in facts if item.first_quote_ever is not None and item.last_quote_ever is not None]
    if not spans:
        return None
    start = max(first for first, _last in spans)
    end = min(last for _first, last in spans)
    return (start, end) if start < end else None


def suggested_analysis_ranges(common: Optional[tuple[date, date]], window_start: date, window_end: date) -> tuple[tuple[date, date], ...]:
    """The periods a "fit to the common period" proposal may set, in order of preference, unverified.

    The common span starts the day *after* the latest first quote, so that quote is the analysis's
    starting price instead of a baseline inside the period. First the chosen period trimmed to it;
    then the common span itself, for a chosen period that misses it or overlaps it too little to be
    analyzed. Nothing when the chosen period already lies inside the common span: its trouble is then
    a gap in some asset's quotes, which no choice of span can mend.
    """
    if common is None:
        return ()
    span = (common[0] + timedelta(days=1), common[1])
    if span[0] >= span[1]:
        return ()
    trimmed = (max(window_start, span[0]), min(window_end, span[1]))
    if trimmed == (window_start, window_end):
        return ()
    if trimmed[0] >= trimmed[1] or trimmed == span:
        return (span,)
    return trimmed, span


def suggested_replay_range(
    facts: Mapping[int, PriceWindowFacts],
    auto_excluded: Mapping[int, RiskHistoricalReplayExclusionReason],
    window_start: date,
    window_end: date,
) -> Optional[tuple[tuple[date, date], tuple[int, ...]]]:
    """The part of a replay window that would cover the assets its edges exclude, before it is verified.

    It starts the day *after* the latest first quote inside the window of an asset without a price
    at the start, so that fresh quote becomes the asset's starting price: a replay starts from the
    last price before its first day, and on the first quote's own day that price would be missing
    (a listing) or the stale one from before the gap. It ends at the earliest last quote of an asset
    without a recent price at the end. An asset with no price in the window, or without FX, is not an
    edge exclusion: no shorter window brings it back. Returns the range and the assets it would
    recover, or `None`.
    """
    edge = sorted(asset_id for asset_id, reason in auto_excluded.items() if reason in _EDGE_REASONS)
    if not edge:
        return None
    start, end = window_start, window_end
    for asset_id in edge:
        item = facts[asset_id]
        if auto_excluded[asset_id] in _LATE_START_REASONS:
            if item.first_quote_in_window is None:
                return None
            start = max(start, item.first_quote_in_window + timedelta(days=1))
        if item.last_quote is None:
            return None
        if _days(window_end, item.last_quote) > STALE_PRICE_THRESHOLD_DAYS:
            end = min(end, item.last_quote)
    if start >= end:
        return None
    return (start, end), tuple(edge)


async def load_price_window_facts(
    session: AsyncSession,
    *,
    asset_ids: Sequence[int],
    window_start: date,
    window_end: date,
    target_currency: str,
    market_holidays: AbstractSet[date] = frozenset(),
) -> dict[int, PriceWindowFacts]:
    """Read the facts of every asset for one window: one aggregate query, plus one FX probe per currency.

    The query skips stored carries — weekend or `market_holidays` rows repeating the close before them —
    with the same rule the series preparation applies (`market_calendar.is_market_closed_repeat`).
    """
    ids = sorted(set(asset_ids))
    if not ids:
        return {}

    previous_close = func.lag(PriceHistory.close).over(partition_by=PriceHistory.asset_id, order_by=PriceHistory.date)
    ordered = select(PriceHistory.asset_id.label("asset_id"), PriceHistory.date.label("date"), PriceHistory.close.label("close"), previous_close.label("previous_close")).where(PriceHistory.asset_id.in_(ids)).subquery("ordered")
    closed_day = func.strftime("%w", ordered.c.date).in_(("0", "6"))
    holidays = sorted(day for day in market_holidays if day <= window_end)
    if holidays:
        closed_day = or_(closed_day, ordered.c.date.in_(holidays))
    carry = and_(closed_day, ordered.c.previous_close.is_not(None), ordered.c.close == ordered.c.previous_close)
    quotes = select(ordered.c.asset_id, ordered.c.date).where(not_(carry)).subquery("quotes")

    up_to_end = quotes.c.date <= window_end
    in_window = and_(quotes.c.date >= window_start, up_to_end)
    rows = (
        await session.execute(
            select(
                quotes.c.asset_id,
                func.min(case((up_to_end, quotes.c.date))),
                func.max(case((up_to_end, quotes.c.date))),
                func.max(case((quotes.c.date < window_start, quotes.c.date))),
                func.sum(case((in_window, 1), else_=0)),
                func.min(case((in_window, quotes.c.date))),
                func.min(quotes.c.date),
                func.max(quotes.c.date),
            ).group_by(quotes.c.asset_id)
        )
    ).all()
    by_asset = {asset_id: (first, last, before, int(count or 0), first_in, first_ever, last_ever) for asset_id, first, last, before, count, first_in, first_ever, last_ever in rows}

    currencies = dict((await session.execute(select(Asset.id, Asset.currency).where(Asset.id.in_(ids)))).all())
    fx_ok: dict[str, bool] = {}
    for currency in sorted({code for code in currencies.values() if code and code != target_currency}):
        probes = [(Currency(code=currency, amount=1), target_currency, window_start), (Currency(code=currency, amount=1), target_currency, window_end)]
        results, _errors = await convert_bulk(session, probes, raise_on_error=False)
        fx_ok[currency] = all(result is not None for result in results)

    facts: dict[int, PriceWindowFacts] = {}
    for asset_id in ids:
        first, last, before, count, first_in, first_ever, last_ever = by_asset.get(asset_id, (None, None, None, 0, None, None, None))
        currency = currencies.get(asset_id)
        facts[asset_id] = PriceWindowFacts(
            first_quote=first,
            last_quote=last,
            last_quote_before_start=before,
            quotes_in_window=count,
            fx_available=True if not currency or currency == target_currency else fx_ok.get(currency, False),
            first_quote_in_window=first_in,
            first_quote_ever=first_ever,
            last_quote_ever=last_ever,
        )
    return facts
