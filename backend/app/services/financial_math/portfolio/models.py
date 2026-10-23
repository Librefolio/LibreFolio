"""Portfolio engine data: classified transactions, daily position and portfolio states, contributions, and the calculation result."""

from __future__ import annotations

import bisect
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field, replace
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Optional, overload

from backend.app.db.models import Transaction
from backend.app.services.financial_math.average_cost import (
    AverageCost,
)
from backend.app.services.financial_math.native_cash import NativeCash

# =============================================================================
# DATACLASSES — Internal runtime objects (not API DTOs)
# =============================================================================


ClassificationType = Literal[
    "normal",
    "linked_internal",
    "linked_external_inflow",
    "linked_external_outflow",
    "ignored",
]


class ValuationSource(StrEnum):
    MARKET_PRICE = "MARKET_PRICE"
    LAST_TRADE_PRICE = "LAST_TRADE_PRICE"
    # No price observation on or before the day, and the position's cost is known: it counts at its book
    # cost in the report currency, as a declared estimate, not a price (developer's decision, J-17).
    ESTIMATED_AT_COST = "ESTIMATED_AT_COST"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class SplitRecord:
    """Unique asset split used to restate historical unit-price references."""

    event_id: int
    asset_id: int
    date: date_type
    ratio: Decimal


SplitHistory = tuple[SplitRecord, ...]


@dataclass(frozen=True, slots=True)
class ValuationResult:
    """Immutable result of selecting and converting one position valuation."""

    market_value: Decimal | None
    source: ValuationSource
    effective_unit_price: Decimal | None
    effective_currency: str | None
    reference_date: date_type | None
    reference_unit_price: Decimal | None
    reference_currency: str | None
    split_adjusted: bool = False
    stale: bool = False
    missing_fx_pair: str | None = None
    # G1b — synthetic P&L candles (plan §4.3). Only ever populated when the caller passed
    # compute_ohlc=True AND the resolved mark is an exact MARKET day with a full OHLC triple
    # (never for CARRIED/TRADE_AVG/MISSING) — same conversion pipeline as market_value, applied
    # to open/high/low instead of close. None means "no intraday range known for this day";
    # the candle composer's flat fallback is open=high=low=close=market_value, not a guess here.
    market_value_open: Decimal | None = None
    market_value_high: Decimal | None = None
    market_value_low: Decimal | None = None


@dataclass
class ClassifiedTransaction:
    """Transaction classified by the ScopeAwareTransactionClassifier."""

    tx: Transaction
    classification: ClassificationType
    paired_tx: Optional[Transaction] = None
    share: Decimal = Decimal("1")


@dataclass
class InTransitInterval:
    """In-transit window for an internal linked pair with different dates.

    Window is [start_date, end_date] inclusive, representing the half-open
    convention [min(departure_date, arrival_date), max(departure_date, arrival_date))
    from plan v2 §7.2:
        start_date = min(departure_date, arrival_date)       # = departure_date (dep <= arr by construction)
        end_date   = max(departure_date, arrival_date) - 1   # last day still "in transit"
    The departure date itself is included (value leaves the source broker and
    enters transit on the same day — no value-hole), the arrival date itself is
    excluded (destination custody begins on arrival day, no double-count).
    If start_date > end_date the interval is empty (same-day transfer only).
    """

    start_date: date_type  # min(departure_date, arrival_date) == departure_date
    end_date: date_type  # max(departure_date, arrival_date) - 1
    tx_type: Literal["cash", "asset"]
    departure_leg: Transaction
    arrival_leg: Transaction
    share: Decimal
    # For asset transfers:
    asset_id: Optional[int] = None
    cost_basis_amount: Optional[Decimal] = None  # Frozen per-unit CBO or WAC fallback
    cost_basis_currency: Optional[str] = None


@dataclass
class ClassificationResult:
    """Output of ScopeAwareTransactionClassifier.classify()."""

    classified: list[ClassifiedTransaction] = field(default_factory=list)
    in_transit_intervals: list[InTransitInterval] = field(default_factory=list)
    external_cash_flows: list[tuple[date_type, int, Decimal, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # J-43: the linked internal pairs between brokers owned at different shares, one per pair.
    share_mismatches: list[ShareMismatch] = field(default_factory=list)

    def get_needed_paired_ids(self) -> set[int]:
        """IDs of linked txs whose pair is not in the scope transaction set."""
        return self._needed_paired_ids

    _needed_paired_ids: set[int] = field(default_factory=set, repr=False)


# =============================================================================
# DAILY PORTFOLIO STATE — Core daily snapshot
# =============================================================================

# The stale-price threshold and the transaction-implied grace period live in
# data_quality_thresholds, shared with the risk engine.


@dataclass
class DailyPositionState:
    """Per-position daily state — the atomic building block of portfolio computation.

    One instance per (broker_id, asset_id) per day with qty > 0.
    Portfolio-level DailyPortfolioState is aggregated from these.
    """

    date: date_type
    broker_id: int
    asset_id: int
    quantity: Decimal
    valuation_effective_unit_price: Decimal | None
    valuation_effective_currency: str | None
    valuation_reference_date: date_type | None
    valuation_reference_unit_price: Decimal | None
    valuation_reference_currency: str | None
    valuation_source: ValuationSource
    valuation_split_adjusted: bool
    valuation_stale: bool
    missing_fx_pair: str | None
    market_value: Decimal | None  # in target_currency
    wac: Decimal | None  # per unit, in target_currency: historical average cost; None when the cost is incomplete
    wac_currency: str  # target_currency
    cost_basis: Decimal  # in target_currency: historical cost of the open quantity (known part)
    unrealized_pnl: Decimal | None  # market_value - cost_basis (None if MV missing or cost incomplete)
    asset_currency: str | None = None
    wac_asset: Decimal | None = None  # per unit, in asset_currency; None when unknown
    cost_complete: bool = True  # False: a rate or a cost basis is missing for part of the open quantity


@dataclass(frozen=True, slots=True)
class UnrealizedSplit:
    """One asset currency's part of a day's unrealized gain or loss, split by cause.

    For the positions in assets priced in currency A, reported in currency T, with r(t) the
    rate A→T of the day, C_A and C_T their historical cost in A and in T:

    * ``asset`` = MV − C_A × r(t): what the assets did in their own currency, at today's rate;
    * ``fx`` = C_A × r(t) − C_T: what the exchange rate did to their cost;
    * ``unsplit`` = MV − C_T of the positions that cannot be split that day (no market value,
      no rate, or a cost incomplete in either currency).

    The three add up to the positions' MV − C_T exactly; for A = T, ``fx`` is always zero.
    """

    asset: Decimal = Decimal("0")
    fx: Decimal = Decimal("0")
    unsplit: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class RealizedSale:
    """A disposal replayed by the engine: a SELL, or an outgoing ADJUSTMENT (N78-1), with its proceeds and the
    historical cost it took from the pool.

    Amounts are in the target currency and scaled by the owner's share of the broker. A SELL's ``proceeds`` are
    its amount converted at its date; an outgoing ADJUSTMENT's are 0: it has no value, so its cost is realized as a
    loss. ``proceeds`` is None when they could not be converted (the pair is in the result's
    ``missing_fx``); ``cost_complete`` is False when the pool already lacked part of its cost.
    """

    transaction_id: int | None
    asset_id: int
    broker_id: int
    date: date_type
    quantity: Decimal
    proceeds: Decimal | None
    cost: Decimal
    cost_complete: bool


@dataclass
class BrokerDailyContribution:
    """One broker's additive slice of a given day's portfolio NAV/capital/P&L.

    Built from the exact same Decimal components as the scope-aggregate
    DailyPortfolioState fields (market value, cash, in-transit, external cash
    flow) at the same accumulation sites, so summing this across all brokers
    for a given day reproduces the aggregate exactly — never a residual/plug.
    """

    broker_id: int
    nav_contribution: Decimal  # market_value_by_broker + cash_by_broker + in_transit_by_broker
    capital_contribution: Decimal  # cumulative_ecf_by_broker (this broker's capital baseline)
    pnl_contribution: Decimal  # nav_contribution - capital_contribution
    # The in-transit part of nav_contribution, on the departure broker for the whole transit
    # window. Internal, never exported: the engine's own checks read it.
    in_transit_contribution: Decimal


@dataclass(frozen=True, slots=True)
class PnlCandleContribution:
    """One day's synthetic total-P&L candle (G1b, plan §4.3).

    Composed as: offset = total_pnl - sum(asset_close); {open,high,low} = offset +
    sum(asset_{open,high,low}); close = total_pnl exactly (by construction, never a
    residual check — the offset absorbs cash/capital-baseline/realized/income/
    in-transit/flat-fallback contributions that have no per-asset OHLC of their own).
    Cross-asset high/low are explicitly synthetic/non-simultaneous (plan §3.3) — this
    is a presentation candle, never an intraday series or a factual AI Export input.
    """

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class AcquisitionFundingContribution:
    """One day's aggregate BUY funding split (batch 2 follow-up — "new vs reinvested
    liquidity", plan §5.2). Surfaces the engine's own already-existing per-BUY K/R-pool
    draw (from_k/from_r — computed to update the running 3-pool balances, see the BUY
    branch in build()) as a new daily output, summed across every BUY that day. Not
    new business logic: from_new_capital + from_reinvested reproduces that day's total
    BUY cash outflow exactly, by construction (the same amount_target already consumed
    by the pool update, just also captured here instead of discarded)."""

    from_new_capital: Decimal  # sum of from_k across the day's BUYs
    from_reinvested: Decimal  # sum of from_r across the day's BUYs


@dataclass
class DailyPortfolioState:
    """Complete daily portfolio state — the heart of the calculation engine."""

    date: date_type
    # Valuation
    cash_value: Decimal
    market_value: Decimal
    broker_nav_value: Decimal
    in_transit_cash_value: Decimal
    in_transit_asset_market_value: Decimal
    in_transit_market_value: Decimal
    nav_value: Decimal
    # Accounting
    open_cost_basis: Decimal
    in_transit_asset_cost_basis: Decimal
    in_transit_book_value: Decimal
    book_value: Decimal
    unrealized_gain_loss: Decimal
    # Performance inputs
    external_cash_flow: Decimal
    cumulative_external_cash_flow: Decimal  # Running total of deposits - withdrawals (net invested capital)
    # Cash decomposition (Capital Baseline narrative: P&L = NAV - capital_baseline)
    # capital_baseline = cumulative_external_cash_flow (alias, same value)
    book_asset_like: Decimal  # open_cost_basis + in_transit_asset_cost_basis
    cash_from_contributed_capital: Decimal  # min(cash_like, max(capital_baseline - book_asset_like, 0))
    cash_from_generated_returns: Decimal  # cash_like - cash_from_contributed_capital
    total_pnl: Decimal  # nav_value - capital_baseline
    # Allocation
    by_type: dict[str, Decimal] = field(default_factory=dict)
    by_sector: dict[str, Decimal] = field(default_factory=dict)
    by_geography: dict[str, Decimal] = field(default_factory=dict)
    # Data quality
    missing_price_asset_ids: set[int] = field(default_factory=set)
    missing_fx_pairs: set[str] = field(default_factory=set)
    stale_price_asset_ids: set[int] = field(default_factory=set)
    transaction_implied_asset_ids: set[int] = field(default_factory=set)
    # V-11: for each asset of transaction_implied_asset_ids, the day of its last market quote on or before
    # this day (None when it was never quoted); the data-quality grace counts from it.
    transaction_implied_last_quote_dates: dict[int, date_type | None] = field(default_factory=dict)
    nav_complete: bool = True
    # G1a — per-broker additive NAV/capital/P&L slice (see BrokerDailyContribution)
    broker_contributions: dict[int, BrokerDailyContribution] = field(default_factory=dict)
    # G1b — synthetic P&L candle for this day (see PnlCandleContribution). None unless
    # the engine was run with compute_candles=True AND the day's candle is composable
    # (no MISSING held-asset valuation that day).
    pnl_candle: PnlCandleContribution | None = None
    # Batch 2 — new-vs-reinvested BUY funding split for this day (see
    # AcquisitionFundingContribution). None unless the engine was run with
    # compute_acquisition_funding=True AND at least one BUY happened this day (a
    # genuine "no acquisition today" gap, never a zero-valued contribution).
    acquisition_funding: AcquisitionFundingContribution | None = None
    # Unrealized gain/loss of the held positions (market_value - open_cost_basis) by asset
    # currency, split into asset and exchange-rate effect (see UnrealizedSplit).
    unrealized_by_currency: dict[str, UnrealizedSplit] = field(default_factory=dict)


# =============================================================================
# STATE SEGMENTS — one computed day and the quiet days that carry it (P4)
# =============================================================================


@dataclass(frozen=True, slots=True)
class StateSegment:
    """A computed day's state and the quiet days after it that carry it, up to ``end`` included.

    ``state.date == start`` always. On a quiet day every field keeps its value except three: ``date``,
    ``external_cash_flow`` (0) and ``acquisition_funding`` (None) — the engine marks dirty every day on which any
    other field can change (``DailyStateBuilder._collect_dirty_days``). The state is read-only: a reader never
    mutates it or its containers.
    """

    start: date_type
    end: date_type
    state: DailyPortfolioState

    def state_on(self, day: date_type) -> DailyPortfolioState:
        """The state of ``day``: the stored one on ``start``; on a quiet day a new state, its containers copied."""
        if day == self.start:
            return self.state
        if not self.start < day <= self.end:
            raise ValueError(f"{day} is outside the segment {self.start}..{self.end}")
        state = self.state
        return replace(
            state,
            date=day,
            external_cash_flow=Decimal("0"),
            by_type=dict(state.by_type),
            by_sector=dict(state.by_sector),
            by_geography=dict(state.by_geography),
            missing_price_asset_ids=set(state.missing_price_asset_ids),
            missing_fx_pairs=set(state.missing_fx_pairs),
            stale_price_asset_ids=set(state.stale_price_asset_ids),
            transaction_implied_asset_ids=set(state.transaction_implied_asset_ids),
            transaction_implied_last_quote_dates=dict(state.transaction_implied_last_quote_dates),
            broker_contributions=dict(state.broker_contributions),
            acquisition_funding=None,
            unrealized_by_currency=dict(state.unrealized_by_currency),
        )


class DailyStates(Sequence[DailyPortfolioState]):
    """One state a day from ``first_date`` to ``last_date``, held as segments: a quiet day is built when read.

    Indexing, slicing and iteration give the states a day-by-day list would hold (a quiet day as
    :meth:`StateSegment.state_on` builds it); memory and the engine's work grow with the computed days only. A reader
    that needs the values, not one object a day, walks :meth:`iter_segments` or asks one day (:meth:`state_on`,
    :meth:`state_as_of`).
    """

    __slots__ = ("segments", "_starts")

    def __init__(self, segments: Iterable[StateSegment] = ()) -> None:
        stored = tuple(segments)
        for index, segment in enumerate(stored):
            if segment.state.date != segment.start or segment.end < segment.start:
                raise ValueError(f"segment {segment.start}..{segment.end} holds the state of {segment.state.date}")
            if index and segment.start != stored[index - 1].end + timedelta(days=1):
                raise ValueError(f"segment {segment.start}..{segment.end} does not follow {stored[index - 1].start}..{stored[index - 1].end}")
        self.segments: tuple[StateSegment, ...] = stored
        self._starts: list[date_type] = [segment.start for segment in stored]

    @property
    def first_date(self) -> date_type | None:
        """The first day; None when there is none."""
        return self.segments[0].start if self.segments else None

    @property
    def last_date(self) -> date_type | None:
        """The last day; None when there is none."""
        return self.segments[-1].end if self.segments else None

    def __len__(self) -> int:
        if not self.segments:
            return 0
        return (self.segments[-1].end - self.segments[0].start).days + 1

    def _segment_index(self, day: date_type) -> int:
        """The index of the segment holding ``day``, which lies in ``[first_date, last_date]``."""
        return bisect.bisect_right(self._starts, day) - 1

    @overload
    def __getitem__(self, index: int) -> DailyPortfolioState: ...

    @overload
    def __getitem__(self, index: slice) -> list[DailyPortfolioState]: ...

    def __getitem__(self, index: int | slice) -> DailyPortfolioState | list[DailyPortfolioState]:
        if isinstance(index, slice):
            return [self._state_at(position) for position in range(*index.indices(len(self)))]
        length = len(self)
        position = index + length if index < 0 else index
        if not 0 <= position < length:
            raise IndexError("DailyStates index out of range")
        return self._state_at(position)

    def _state_at(self, position: int) -> DailyPortfolioState:
        day = self.segments[0].start + timedelta(days=position)
        return self.segments[self._segment_index(day)].state_on(day)

    def __iter__(self) -> Iterator[DailyPortfolioState]:
        for segment in self.segments:
            day = segment.start
            while day <= segment.end:
                yield segment.state_on(day)
                day += timedelta(days=1)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sequence) or isinstance(other, (str, bytes)):
            return NotImplemented
        if len(self) != len(other):
            return False
        return all(mine == theirs for mine, theirs in zip(self, other, strict=True))

    __hash__ = None  # type: ignore[assignment]  # mutable-like equality, as a list

    def __repr__(self) -> str:
        return f"DailyStates({self.first_date}..{self.last_date}, {len(self.segments)} segments)"

    def segment_at(self, day: date_type) -> StateSegment | None:
        """The stored segment holding ``day``; None outside ``[first_date, last_date]``."""
        if not self.segments or not self.segments[0].start <= day <= self.segments[-1].end:
            return None
        return self.segments[self._segment_index(day)]

    def state_on(self, day: date_type) -> DailyPortfolioState | None:
        """The state of ``day``; None outside ``[first_date, last_date]``."""
        segment = self.segment_at(day)
        return segment.state_on(day) if segment is not None else None

    def state_as_of(self, day: date_type) -> DailyPortfolioState | None:
        """The state of the last day on or before ``day`` (the last day's after ``last_date``); None before the first."""
        if not self.segments or day < self.segments[0].start:
            return None
        last = self.segments[-1]
        return self.state_on(min(day, last.end))

    def iter_segments(self, date_from: date_type | None = None, date_to: date_type | None = None) -> Iterator[StateSegment]:
        """The segments overlapping ``[date_from, date_to]`` (an open bound reaches the end), clipped to it.

        A segment whose start moves gets the state of its new start, so ``state.date == start`` still holds; one that
        is not clipped at its start keeps its stored state.
        """
        if not self.segments:
            return
        first = 0 if date_from is None or date_from <= self.segments[0].start else max(self._segment_index(date_from), 0)
        for segment in self.segments[first:]:
            if date_to is not None and segment.start > date_to:
                return
            if date_from is not None and segment.end < date_from:
                continue
            start = segment.start if date_from is None or date_from <= segment.start else date_from
            end = segment.end if date_to is None or segment.end <= date_to else date_to
            if start == segment.start and end == segment.end:
                yield segment
            else:
                yield StateSegment(start=start, end=end, state=segment.state_on(start))


# =============================================================================
# PORTFOLIO CALCULATION RESULT
# =============================================================================


@dataclass
class EngineEndState:
    """Serialized accumulator state at end of a computation blob.

    Used for forward cache extension: resume computation from this state
    instead of recomputing from scratch.
    """

    cumulative_cash: Decimal
    cumulative_ecf: Decimal
    cumulative_qty: dict[tuple[int, int], Decimal]
    wac_pool_qty: dict[tuple[int, int], Decimal]  # average-cost pool quantity
    wac_pool_cost: dict[tuple[int, int], Decimal]  # average-cost pool cost, historical, in target currency
    capital_pool: dict[int, Decimal]  # K per broker
    returns_pool: dict[int, Decimal]  # R per broker
    withdrawn_pool: Decimal  # W global
    # G1a — per-broker mirrors of cumulative_cash/cumulative_ecf, so a future
    # forward-cache resume carries broker attribution alongside the aggregate.
    cumulative_cash_by_broker: dict[int, Decimal]
    cumulative_ecf_by_broker: dict[int, Decimal]


@dataclass(frozen=True, slots=True)
class InternalAssetTransfer:
    """A security moved between two brokers of the scope by a linked internal TRANSFER pair (MF-A, P22).

    On arrival the sender's tract ends and the receiver's begins, at the same value: what the moved units are worth
    that day, at the sender's share, as the receiver's NAV values them (``DailyStateBuilder._internal_pair_value``).
    """

    departure: date_type
    arrival: date_type
    asset_id: int
    sender_broker_id: int
    receiver_broker_id: int
    # The moved units' value on arrival in the target currency; None when it cannot be computed (no rate, unknown cost).
    value_at_arrival: Decimal | None
    # The historical cost the sender's pool gave up for them, in the target currency; None when that cost is incomplete.
    cost_moved: Decimal | None


@dataclass(frozen=True, slots=True)
class ShareMismatch:
    """A linked internal pair between two brokers owned at different shares (J-43).

    Each leg counts at its own broker's share, so what the departure sends and what the arrival brings differ: that
    gap is a result, never capital (D-MF4 = a). This record lets the data-quality report explain it to the user.
    """

    # The pair's two transaction ids, lower id first; the brokers and the shares follow the same order.
    tx_ids: tuple[int, int]
    broker_ids: tuple[int, int]
    shares: tuple[Decimal, Decimal]
    # The later of the two legs' dates: the day the pair is complete.
    date: date_type


@dataclass(frozen=True, slots=True)
class InvalidSplitEvent:
    """A SPLIT asset event stored with a ratio the layer cannot use (None, not finite, or ≤ 0; MF-D4).

    It counts as missing: its linked ADJUSTMENT rows stay the split's rescale (cost kept, never in-kind capital), but no
    ratio restates a trade price observed before it (market quotes are never restated). The data-quality report names
    its asset.
    """

    event_id: int
    asset_id: int
    date: date_type


@dataclass(frozen=True, slots=True)
class RowsBeforeFloor:
    """The scope's transactions dated before ``EARLIEST_RANGE_START`` (1 January 1900; MF-SEC8-2a).

    Written by an older version or by hand (N74 refuses new ones). They are replayed on their own dates, but no state is
    emitted before the floor: the histories start on it. The data-quality report warns, with their number and the
    earliest date, so the user corrects them.
    """

    count: int
    earliest: date_type


@dataclass
class PortfolioCalculationResult:
    """Complete result from the portfolio calculation engine."""

    # One state a day from date_from to date_to, held as segments (P4): the computed days, each carried to the next.
    daily_states: DailyStates
    # Position snapshots for exposure + contribution views: the positions held at the end of the period's start day
    # (``period_start``, the first frame day unless the caller names it) and at date_to.
    position_states_start: list[DailyPositionState] = field(default_factory=list)
    # The day position_states_start was taken at the end of (None for a result built without a replay).
    position_states_start_date: date_type | None = None
    position_states_end: list[DailyPositionState] = field(default_factory=list)
    # Linked internal TRANSFER pairs of securities between two brokers, with their value on arrival (MF-A, P22).
    internal_asset_transfers: list[InternalAssetTransfer] = field(default_factory=list)
    # Every broker's cash in its own currencies (financial_math.native_cash): balances, values
    # and the period flows by type and position. None when calculate() returns early, with
    # no broker or no transaction in scope.
    native_cash: NativeCash | None = None
    # End state for cache forward extension
    end_state: EngineEndState | None = None
    # Metadata
    scope_broker_ids: list[int] = field(default_factory=list)
    target_currency: str = "EUR"
    date_from: date_type = field(default_factory=date_type.today)
    date_to: date_type = field(default_factory=date_type.today)
    # Average cost of every (asset_id, broker_id) position replayed (financial_math.average_cost)
    average_costs: dict[tuple[int, int], AverageCost] = field(default_factory=dict)
    # SELLs replayed, in replay order, with proceeds and historical cost in target_currency
    realized_sales: list[RealizedSale] = field(default_factory=list)
    # MF-D4: the SPLIT events whose stored ratio is unusable, counted as missing (one per event, by event id).
    invalid_split_events: list[InvalidSplitEvent] = field(default_factory=list)
    # MF-SEC8-2a: the scope's transactions dated before EARLIEST_RANGE_START (None when there is none).
    rows_before_floor: RowsBeforeFloor | None = None
    # Conversions a movement (cost, cash, external flow, in-transit cost) needed and could not
    # get: pair "FROM/TO" -> dates. Valuation failures are per day in DailyPortfolioState.missing_fx_pairs.
    missing_fx: dict[str, set[date_type]] = field(default_factory=dict)
    # J-43: the classification's linked internal pairs between brokers owned at different shares.
    share_mismatches: list[ShareMismatch] = field(default_factory=list)
