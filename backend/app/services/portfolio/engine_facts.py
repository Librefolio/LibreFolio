"""Small pieces the portfolio mixins share: the holding and lot-affecting transaction types, the dust threshold, the facts of a held
asset's quote, the history steps, and the helpers that read the engine's output."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal
from typing import Any

from backend.app.db.models import (
    TransactionType,
)
from backend.app.schemas.common import Currency, DateSpan
from backend.app.schemas.portfolio import (
    MwrrLinePoint,
    PortfolioHistoryPoint,
    UnrealizedBreakdownRow,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math.native_cash import NativeCash
from backend.app.services.financial_math.portfolio import period as period_math
from backend.app.services.financial_math.portfolio.models import DailyStates
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.app.utils.day_spans import merged_spans


def _engine_missing_fx_pairs(engine_result: Any, period_from: date_type | None, period_to: date_type | None) -> list[WACMissingPairInfo]:
    """Every conversion the engine could not make, as pair + dates + ranges for the data-quality banner.

    ``dates``: the movements (cost, cash, external flows, in-transit cost), on whatever date they happened. ``ranges``:
    the valuation days, only those of the period shown, [period_from, period_to], whose first day is the opening state of
    the period, with the consecutive days merged (D-P4: no list of every day).
    """
    dates_by_pair: dict[str, set[date_type]] = defaultdict(set)
    for pair, dates in (getattr(engine_result, "missing_fx", None) or {}).items():
        dates_by_pair[pair].update(dates)
    spans_by_pair: dict[str, list[tuple[date_type, date_type]]] = defaultdict(list)
    daily_states = getattr(engine_result, "daily_states", None) or []
    if isinstance(daily_states, DailyStates):
        # Every day of a segment reads its state's pairs (P4): no state is built
        for segment in daily_states.iter_segments(period_from, period_to):
            for pair in segment.state.missing_fx_pairs:
                spans_by_pair[pair].append((segment.start, segment.end))
    else:
        for state in daily_states:
            if not state.missing_fx_pairs:
                continue
            if (period_from is not None and state.date < period_from) or (period_to is not None and state.date > period_to):
                continue
            for pair in state.missing_fx_pairs:
                spans_by_pair[pair].append((state.date, state.date))
    return [WACMissingPairInfo(pair=pair, dates=sorted(dates_by_pair.get(pair, ())), ranges=[DateSpan(start=first, end=last) for first, last in merged_spans(spans_by_pair.get(pair, ()))]) for pair in sorted(set(dates_by_pair) | set(spans_by_pair))]


@dataclass(frozen=True)
class HistorySteps:
    """The report's history in steps (D-P4): its ``range``, the steps, and the MWRR line of true points."""

    range: DateSpan | None
    history: list[PortfolioHistoryPoint]
    mwrr_line: list[MwrrLinePoint]


def _engine_native_cash(engine_result: Any, report_currency: str) -> NativeCash:
    """The engine's native cash of the scope; an empty one when the engine stopped early (no access, no transaction)."""
    native_cash = getattr(engine_result, "native_cash", None)
    return native_cash if native_cash is not None else NativeCash(report_currency=report_currency, movements=(), converted=(), unit_rates={})


def _unrealized_breakdown_rows(engine_result: Any, date_from: date_type | None, as_of: date_type, currency: str) -> list[UnrealizedBreakdownRow]:
    """The period's unrealized change by asset currency: assets' own change, exchange-rate effect, unsplit.

    Same boundary states as the period P&L (``financial_math.portfolio.period.period_boundaries``: the
    last state on or before ``date_from``, zero when there is none or no ``date_from``; the state at
    ``as_of``), so the rows add up to ``period_unrealized_gain_loss_delta`` exactly. Order: asset rows,
    then exchange-rate rows, then unsplit rows; the report currency first, then alphabetical.
    """
    boundaries = period_math.period_boundaries(getattr(engine_result, "daily_states", None) or [], date_from, as_of)
    if boundaries is None:
        return []
    start_state, end_state = boundaries.start, boundaries.end
    end_parts = end_state.unrealized_by_currency
    start_parts = start_state.unrealized_by_currency if start_state is not None else {}
    currencies = sorted(set(end_parts) | set(start_parts), key=lambda code: (code != currency, code))

    zero = Decimal("0")

    def delta(code: str, kind: str) -> tuple[Decimal, Decimal, Decimal]:
        end_value = getattr(end_parts[code], kind) if code in end_parts else zero
        start_value = getattr(start_parts[code], kind) if code in start_parts else zero
        return start_value, end_value, end_value - start_value

    rows: list[UnrealizedBreakdownRow] = []
    for code in currencies:
        rows.append(UnrealizedBreakdownRow(kind="asset", asset_currency=code, period_delta=Currency(code=currency, amount=delta(code, "asset")[2])))
    for code in currencies:
        if code != currency:
            rows.append(UnrealizedBreakdownRow(kind="fx", asset_currency=code, period_delta=Currency(code=currency, amount=delta(code, "fx")[2])))
    for code in currencies:
        start_value, end_value, change = delta(code, "unsplit")
        if start_value != zero or end_value != zero:
            rows.append(UnrealizedBreakdownRow(kind="unsplit", asset_currency=code, period_delta=Currency(code=currency, amount=change)))
    return rows


_HOLDING_TYPES = {TransactionType.BUY, TransactionType.SELL}


# Transaction types that move a position's quantity: its holding window comes from them
# (financial_math.holding_window; a split rescales the open lots, a transfer-in opens one
# dated at its arrival at the receiving broker).
_LOT_AFFECTING_TYPES = {TransactionType.BUY, TransactionType.SELL, TransactionType.ADJUSTMENT, TransactionType.TRANSFER}


# Some instruments (e.g. CROWDFUND real-estate loans redeemed via periodic partial
# buybacks) accrue a tiny non-zero quantity residual even after the position is
# economically fully closed — the platform computes each redemption tranche's
# quantity independently (rounded to its own precision), and those tranches don't
# always sum back to *exactly* the original quantity bought (observed real case:
# 8×(-0.031102) + (-0.751182) against a +1 buy leaves a +0.000002 residual). This
# is not Decimal arithmetic error — it's an artifact of the recorded transaction
# quantities themselves — so treat anything at or below this threshold as closed.
# The value lives in data_quality_thresholds, shared with the asset list's held-now flags
# and the closed-position window (financial_math.holding_window).
_QUANTITY_DUST_THRESHOLD = QUANTITY_DUST_THRESHOLD


@dataclass(frozen=True)
class HeldAssetQuoteFacts:
    """An asset held at the end of a report's period, with what the data-quality report's asset quote check reads: its
    stored currency (E-19b's NON_ISO_CURRENCY)."""

    asset_id: int
    name: str
    currency: str
