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

The rules are pure; `load_price_window_facts` is the only function that touches the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, PriceHistory
from backend.app.schemas.common import Currency
from backend.app.schemas.risk import RiskEligibilityLevel, RiskEligibilityReason, RiskHistoricalReplayExclusionReason
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS, STALE_PRICE_THRESHOLD_DAYS
from backend.app.services.fx import convert_bulk


@dataclass(frozen=True, slots=True)
class PriceWindowFacts:
    """What one asset's own quotes say about one window.

    A quote is a stored price row. Rows a provider writes for days its market was closed (a weekend
    repeating Friday's close) are quotes too: the price pipeline treats them as fresh, and so does
    this reading.
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


def _days(later: date, earlier: date) -> int:
    return (later - earlier).days


def analysis_eligibility(facts: PriceWindowFacts, window_start: date, window_end: date) -> tuple[RiskEligibilityLevel, tuple[RiskEligibilityReason, ...]]:
    """Whether an asset can take part in an analysis of `window_start..window_end`.

    Blocking reasons make it ineligible; otherwise lateness at either end is a warning. The quote
    floor counts the asset's own quotes, so it is necessary but not sufficient: the analytics count
    returns on the joint calendar of the whole selection.
    """
    blocking: list[RiskEligibilityReason] = []
    if facts.quotes_in_window == 0:
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


async def load_price_window_facts(
    session: AsyncSession,
    *,
    asset_ids: Sequence[int],
    window_start: date,
    window_end: date,
    target_currency: str,
) -> dict[int, PriceWindowFacts]:
    """Read the facts of every asset for one window: one aggregate query, plus one FX probe per currency."""
    ids = sorted(set(asset_ids))
    if not ids:
        return {}

    rows = (
        await session.execute(
            select(
                PriceHistory.asset_id,
                func.min(PriceHistory.date),
                func.max(PriceHistory.date),
                func.max(case((PriceHistory.date < window_start, PriceHistory.date))),
                func.sum(case((and_(PriceHistory.date >= window_start, PriceHistory.date <= window_end), 1), else_=0)),
            )
            .where(PriceHistory.asset_id.in_(ids), PriceHistory.date <= window_end)
            .group_by(PriceHistory.asset_id)
        )
    ).all()
    by_asset = {asset_id: (first, last, before, int(count or 0)) for asset_id, first, last, before, count in rows}

    currencies = dict((await session.execute(select(Asset.id, Asset.currency).where(Asset.id.in_(ids)))).all())
    fx_ok: dict[str, bool] = {}
    for currency in sorted({code for code in currencies.values() if code and code != target_currency}):
        probes = [(Currency(code=currency, amount=1), target_currency, window_start), (Currency(code=currency, amount=1), target_currency, window_end)]
        results, _errors = await convert_bulk(session, probes, raise_on_error=False)
        fx_ok[currency] = all(result is not None for result in results)

    facts: dict[int, PriceWindowFacts] = {}
    for asset_id in ids:
        first, last, before, count = by_asset.get(asset_id, (None, None, None, 0))
        currency = currencies.get(asset_id)
        facts[asset_id] = PriceWindowFacts(
            first_quote=first,
            last_quote=last,
            last_quote_before_start=before,
            quotes_in_window=count,
            fx_available=True if not currency or currency == target_currency else fx_ok.get(currency, False),
        )
    return facts
