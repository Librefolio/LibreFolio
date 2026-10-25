"""MF5-1b — position frames: every position's daily values as maximal runs, from the engine's own replay.

Today the engine gives a position's values on two days only: ``position_states_start`` (the end of ``period_start``)
and ``position_states_end`` (``date_to``), each a ``DailyPositionState`` built by
``DailyStateBuilder._build_position_state(asset_id, broker_id, qty, day, cost_pool)``. Workstreams J and Y need them on
every day of the period; asking the engine once per day replays the whole history once per day. The cure (contract):

```python
@dataclass(frozen=True, slots=True)
class PositionFrame:            # financial_math/portfolio/models.py
    broker_id: int
    asset_id: int
    start: date                 # first day, inclusive
    end: date                   # last day, inclusive
    quantity: Decimal
    market_value: Decimal | None
    cost_basis: Decimal
    cost_complete: bool
    valuation_source: ValuationSource
    unrealized_pnl: Decimal | None
```

- ``DailyStateBuilder(..., compute_position_frames=False)``; ``PortfolioCalculationEngine.calculate(...,
  include_positions=False)`` (part of the blob-cache key: ``test_financial/test_position_frames_engine.py``);
- ``PortfolioCalculationResult.position_frames: tuple[PositionFrame, ...] | None = None``: None when not asked, a tuple
  (possibly empty) when asked;
- for every day d of ``[date_from, date_to]`` and every (broker, asset) whose quantity is > 0 at the end of d: exactly
  one frame of that position covers d, with the values ``_build_position_state`` gives that day; a position not held on
  d has no frame covering d (no zero-quantity frame);
- maximal merge: two adjacent frames of a position never carry identical values (Decimals by ``as_tuple()``); a frame
  changes only when its own position changes;
- order: grouped by position, positions in the order the replay first met them (the engine's ``cumulative_qty``
  insertion order, read here from ``end_state.cumulative_qty``), each group ascending by start;
- bit parity: on every day, ``Decimal("0")`` + the non-None ``market_value`` of the frames covering it, in tuple order,
  is ``daily_states.state_on(d).market_value`` (value and ``as_tuple()``);
- off by default, and the flag changes nothing else.

The reference (the choice the brief left open). For each day d the oracle is the engine's own snapshot at the end of d:
the same book built with ``period_start=d`` — same ``date_from``, same ``date_to`` — whose ``position_states_start`` is,
by construction, ``_build_position_state(aid, bid, qty, d, cost_pool)`` for every position with qty > 0 after d's
movements (``build()`` step 4b2), on the very replay the frames come from. It asks nothing private, it is exact to the
exponent, and it cannot drift from the method the contract names. (``position_states_end`` of builds with
``date_to=d`` was the alternative: it changes ``date_to``, hence the average costs and the native cash handed to the
builder, so it is a near oracle, not the same replay.)

The books (pure: the builder fed by hand, helpers copied from ``test_engine_state_segments.py``):

- ``two-assets`` (January, share 1): X and Y quoted on different days (a Y quote never splits X's frame, nor the
  reverse), X sold in part then in full (its frames end the day before the full sale, none until it is bought again),
  then reopened (the reopened frames stay in X's group, before Y's);
- ``fx`` (February, broker at share 0.5): a USD asset whose rate changes (its frame splits on the rate days), a GBP asset
  with no rate at all (market value None, out of the sum), an asset with no price valued at cost (ESTIMATED_AT_COST: one
  frame for the whole holding, untouched by the others' quotes and rates), a partial sale;
- ``transfer`` (March, two brokers): the same asset held on two brokers, a security transfer between them with three
  days in transit, ``date_from`` after the first movements (no frame before it; the first frames start on it).

RED on HEAD 5dc68b650, by absence: ``PositionFrame`` does not exist, the module fails at collection with
``ImportError``. After a cure without ``compute_position_frames`` every builder test fails with ``TypeError``.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from functools import cache
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import DailyPositionState, DailyStates, PortfolioCalculationResult, PositionFrame, ValuationSource
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
#: U is met first by the fx book's replay but has the largest id, and B before A in the transfer book: the replay order
#: is never a sorted order, so the order test cannot pass on a sort.
X, Y, G, W, U = 100, 200, 400, 500, 600

FRAME_FIELDS = ["broker_id", "asset_id", "start", "end", "quantity", "market_value", "cost_basis", "cost_complete", "valuation_source", "unrealized_pnl"]
VALUE_FIELDS = ("quantity", "market_value", "cost_basis", "cost_complete", "valuation_source", "unrealized_pnl")

# =============================================================================
# HELPERS — copies of test_engine_state_segments.py (plus a cost override and broker shares)
# =============================================================================


def _tx(
    *,
    id: int,
    broker_id: int = A,
    type: str = "DEPOSIT",
    dt: date,
    amount: str = "0",
    currency: str | None = "EUR",
    quantity: str = "0",
    asset_id: int | None = None,
    related_id: int | None = None,
    cost_basis_override: str | None = None,
    cost_basis_currency: str | None = None,
) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = related_id
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override is not None else None
    tx.cost_basis_currency = cost_basis_currency
    return tx


def _mark_series_from(classified_txs, price_map, asset_currencies):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from prices + trades."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        tx = ctxn.tx
        if tx.asset_id is not None:
            txs_by_asset.setdefault(tx.asset_id, []).append(tx)
    mark_series = {}
    for aid in set(txs_by_asset) | set(price_map or {}):
        series = build_asset_price_series(
            price_rows=(price_map or {}).get(aid, []),
            transactions=txs_by_asset.get(aid, []),
            split_linked_tx_ids=set(),
            asset_currency=(asset_currencies or {}).get(aid, "EUR"),
            quote_base_quantity=1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _builder_kwargs(**overrides) -> dict:
    kwargs = {
        "classified_txs": [],
        "in_transit_intervals": [],
        "external_cash_flows": [],
        "price_map": {},
        "quote_base_map": {},
        "asset_currencies": {},
        "fx_rate_map": {},
        "asset_classifications": {},
        "asset_types": {},
        "target_currency": "EUR",
    }
    kwargs.update(overrides)
    kwargs.setdefault("mark_series", _mark_series_from(kwargs["classified_txs"], kwargs["price_map"], kwargs["asset_currencies"]))
    kwargs.setdefault(
        "average_costs",
        engine_average_costs(kwargs["classified_txs"], asset_currencies=kwargs["asset_currencies"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]),
    )
    kwargs.setdefault("native_cash", engine_native_cash(kwargs["classified_txs"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]))
    return kwargs


def _ledger(txs, shares: dict[int, Decimal], *, date_to, price_map=None, fx_rate_map=None, asset_currencies=None) -> dict:
    """Builder overrides of a classified ledger (the real classifier, loading order (date, id), the brokers' shares)."""
    classification = ScopeAwareTransactionClassifier(
        scope_broker_ids=set(shares),
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares=dict(shares),
    ).classify()
    price_map = price_map or {}
    asset_ids = {ctxn.tx.asset_id for ctxn in classification.classified if ctxn.tx.asset_id is not None} | set(price_map)
    return {
        "classified_txs": classification.classified,
        "in_transit_intervals": classification.in_transit_intervals,
        "external_cash_flows": classification.external_cash_flows,
        "price_map": price_map,
        "fx_rate_map": fx_rate_map or {},
        "asset_currencies": dict.fromkeys(asset_ids, "EUR") | (asset_currencies or {}),
        "asset_types": dict.fromkeys(asset_ids, "Stock"),
        "asset_classifications": dict.fromkeys(asset_ids),
        "date_to": date_to,
    }


def _prices(asset_id: int, currency: str, closes: dict[date, str]) -> dict[int, list[tuple[date, Decimal, str]]]:
    return {asset_id: [(day, Decimal(close), currency) for day, close in sorted(closes.items())]}


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _build(ledger: dict, *, date_from: date, **overrides) -> PortfolioCalculationResult:
    return DailyStateBuilder(**_builder_kwargs(**ledger, date_from=date_from, **overrides)).build()


def _key(value: Any) -> Any:
    """A value compared to the exponent: a Decimal by ``as_tuple()``."""
    return ("Decimal", value.as_tuple()) if isinstance(value, Decimal) else value


def _values(item: PositionFrame | DailyPositionState) -> tuple:
    """The six values a frame carries, as a frame or a DailyPositionState holds them, Decimals by ``as_tuple()``."""
    return tuple(_key(getattr(item, name)) for name in VALUE_FIELDS)


def _deep(value: Any) -> Any:
    """A structural snapshot: dataclasses field by field, containers element by element, Decimals by ``as_tuple()``."""
    if isinstance(value, Decimal):
        return ("Decimal", value.as_tuple())
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return (type(value).__name__, tuple((f.name, _deep(getattr(value, f.name))) for f in dataclasses.fields(value)))
    if isinstance(value, DailyStates):
        return ("DailyStates", tuple((seg.start, seg.end, _deep(seg.state)) for seg in value.segments))
    if isinstance(value, dict):
        return ("dict", tuple((_deep(k), _deep(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_deep(v) for v in value))
    if isinstance(value, (set, frozenset)):
        return ("set", tuple(sorted((_deep(v) for v in value), key=repr)))
    if isinstance(value, MagicMock):
        return ("tx", value.id)
    return value


# =============================================================================
# BOOKS
# =============================================================================


@dataclass(frozen=True)
class Book:
    name: str
    date_from: date
    date_to: date

    def ledger(self) -> dict:
        return _MAKERS[self.name]()


TWO_FROM, TWO_TO = date(2025, 1, 1), date(2025, 1, 31)
X_SOLD_OUT, X_REOPENED = date(2025, 1, 20), date(2025, 1, 24)
X_QUOTES = (date(2025, 1, 6), date(2025, 1, 13), date(2025, 1, 27))
Y_QUOTES = (date(2025, 1, 9), date(2025, 1, 16), date(2025, 1, 30))


def _two_assets() -> dict:
    """A deposits 10 000 (01-02), buys 10 X for 1000 (01-03) and 5 Y for 500 (01-04), sells 4 X for 420 (01-10) and the
    other 6 for 650 (01-20), buys 2 X again for 210 (01-24). X closes on 01-06, 01-13, 01-27; Y on 01-09, 01-16, 01-30."""
    txs = [
        _tx(id=1, dt=date(2025, 1, 2), amount="10000"),
        _tx(id=2, type="BUY", dt=date(2025, 1, 3), amount="-1000", quantity="10", asset_id=X),
        _tx(id=3, type="BUY", dt=date(2025, 1, 4), amount="-500", quantity="5", asset_id=Y),
        _tx(id=4, type="SELL", dt=date(2025, 1, 10), amount="420", quantity="-4", asset_id=X),
        _tx(id=5, type="SELL", dt=X_SOLD_OUT, amount="650", quantity="-6", asset_id=X),
        _tx(id=6, type="BUY", dt=X_REOPENED, amount="-210", quantity="2", asset_id=X),
    ]
    prices = _prices(X, "EUR", dict(zip(X_QUOTES, ("101", "103", "106"), strict=True))) | _prices(Y, "EUR", dict(zip(Y_QUOTES, ("98", "99.5", "97"), strict=True)))
    return _ledger(txs, {A: Decimal("1")}, date_to=TWO_TO, price_map=prices)


FX_FROM, FX_TO = date(2025, 2, 1), date(2025, 2, 28)
USD_RATE_DAYS = (date(2025, 2, 10), date(2025, 2, 20))
W_ARRIVES = date(2025, 2, 7)
HALF = Decimal("0.5")


def _usd_rate(day: date) -> str:
    if day < USD_RATE_DAYS[0]:
        return "0.90"
    return "0.92" if day < USD_RATE_DAYS[1] else "0.91"


def _fx() -> dict:
    """Broker A at share 0.5. A deposits 5000 EUR and 1200 USD (02-01); buys 10 U (a USD stock) for 1000 USD (02-03);
    buys 3 G (a GBP stock) for 300 GBP (02-05) — no GBP rate exists at all; receives 4 W (EUR, never priced) by an
    ADJUSTMENT at a cost of 25 a unit (02-07); sells 4 U for 440 USD (02-17). U closes 100 (02-04) and 102 USD (02-14),
    G 80 GBP (02-06). USD->EUR on every day from 01-25: 0.90, 0.92 from 02-10, 0.91 from 02-20."""
    txs = [
        _tx(id=1, dt=date(2025, 2, 1), amount="5000"),
        _tx(id=2, dt=date(2025, 2, 1), amount="1200", currency="USD"),
        _tx(id=3, type="BUY", dt=date(2025, 2, 3), amount="-1000", currency="USD", quantity="10", asset_id=U),
        _tx(id=4, type="BUY", dt=date(2025, 2, 5), amount="-300", currency="GBP", quantity="3", asset_id=G),
        _tx(id=5, type="ADJUSTMENT", dt=W_ARRIVES, quantity="4", asset_id=W, currency=None, cost_basis_override="25", cost_basis_currency="EUR"),
        _tx(id=6, type="SELL", dt=date(2025, 2, 17), amount="440", currency="USD", quantity="-4", asset_id=U),
    ]
    rates = {("USD", "EUR", day): Decimal(_usd_rate(day)) for day in _days(date(2025, 1, 25), FX_TO)}
    prices = _prices(U, "USD", {date(2025, 2, 4): "100", date(2025, 2, 14): "102"}) | _prices(G, "GBP", {date(2025, 2, 6): "80"})
    return _ledger(txs, {A: HALF}, date_to=FX_TO, price_map=prices, fx_rate_map=rates, asset_currencies={U: "USD", G: "GBP", W: "EUR"})


TRANSFER_FROM, TRANSFER_TO = date(2025, 3, 4), date(2025, 3, 20)
DEPARTURE, ARRIVAL = date(2025, 3, 8), date(2025, 3, 11)


def _transfer() -> dict:
    """A deposits 5000 and B 2000 (03-01); B buys 4 X for 420 (03-02), A buys 10 X for 1000 (03-03); 3 X leave A on 03-08
    and reach B on 03-11. X closes 104 (03-05) and 108 (03-15). date_from 03-04: after every buy."""
    txs = [
        _tx(id=1, dt=date(2025, 3, 1), amount="5000"),
        _tx(id=2, broker_id=B, dt=date(2025, 3, 1), amount="2000"),
        _tx(id=3, broker_id=B, type="BUY", dt=date(2025, 3, 2), amount="-420", quantity="4", asset_id=X),
        _tx(id=4, type="BUY", dt=date(2025, 3, 3), amount="-1000", quantity="10", asset_id=X),
        _tx(id=5, type="TRANSFER", dt=DEPARTURE, quantity="-3", asset_id=X, currency=None, related_id=6),
        _tx(id=6, broker_id=B, type="TRANSFER", dt=ARRIVAL, quantity="3", asset_id=X, currency=None, related_id=5),
    ]
    return _ledger(txs, {A: Decimal("1"), B: Decimal("1")}, date_to=TRANSFER_TO, price_map=_prices(X, "EUR", {date(2025, 3, 5): "104", date(2025, 3, 15): "108"}))


_MAKERS = {"two-assets": _two_assets, "fx": _fx, "transfer": _transfer}
BOOKS = {
    "two-assets": Book("two-assets", TWO_FROM, TWO_TO),
    "fx": Book("fx", FX_FROM, FX_TO),
    "transfer": Book("transfer", TRANSFER_FROM, TRANSFER_TO),
}
BOOK_IDS = list(BOOKS)


@cache
def _with_frames(name: str) -> PortfolioCalculationResult:
    book = BOOKS[name]
    return _build(book.ledger(), date_from=book.date_from, compute_position_frames=True)


@cache
def _reference(name: str) -> dict[date, dict[tuple[int, int], DailyPositionState]]:
    """For each day d: the engine's snapshot at the end of d (``period_start=d``), by (broker_id, asset_id)."""
    book = BOOKS[name]
    reference: dict[date, dict[tuple[int, int], DailyPositionState]] = {}
    for day in _days(book.date_from, book.date_to):
        result = _build(book.ledger(), date_from=book.date_from, period_start=day)
        assert result.position_states_start_date == day
        snapshot: dict[tuple[int, int], DailyPositionState] = {}
        for ps in result.position_states_start:
            assert ps.date == day and ps.quantity > 0
            assert (ps.broker_id, ps.asset_id) not in snapshot
            snapshot[(ps.broker_id, ps.asset_id)] = ps
        reference[day] = snapshot
    return reference


def _frames(name: str) -> tuple[PositionFrame, ...]:
    frames = _with_frames(name).position_frames
    assert isinstance(frames, tuple), f"position_frames is {type(frames).__name__}, not a tuple"
    return frames


def _of(frames, broker_id: int, asset_id: int) -> list[PositionFrame]:
    return [frame for frame in frames if (frame.broker_id, frame.asset_id) == (broker_id, asset_id)]


def _covering(frames, day: date) -> list[PositionFrame]:
    return [frame for frame in frames if frame.start <= day <= frame.end]


# =============================================================================
# 1. THE TYPES
# =============================================================================


class TestTheTypes:
    def test_position_frame_is_a_frozen_slotted_dataclass_with_the_contracts_fields(self):
        assert [f.name for f in dataclasses.fields(PositionFrame)] == FRAME_FIELDS
        frame = PositionFrame(
            broker_id=A,
            asset_id=X,
            start=date(2025, 1, 1),
            end=date(2025, 1, 2),
            quantity=Decimal("1"),
            market_value=None,
            cost_basis=Decimal("0"),
            cost_complete=True,
            valuation_source=ValuationSource.MISSING,
            unrealized_pnl=None,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            frame.end = date(2025, 1, 3)  # type: ignore[misc]
        assert not hasattr(frame, "__dict__"), "slots=True"

    def test_the_result_field_defaults_to_none(self):
        assert PortfolioCalculationResult(daily_states=DailyStates()).position_frames is None


# =============================================================================
# 2. OFF BY DEFAULT
# =============================================================================


class TestOffByDefault:
    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_without_the_flag_there_are_no_frames(self, name):
        book = BOOKS[name]
        assert _build(book.ledger(), date_from=book.date_from).position_frames is None
        assert _build(book.ledger(), date_from=book.date_from, compute_position_frames=False).position_frames is None

    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_the_flag_changes_nothing_else(self, name):
        """Every other field of the result — the daily states (segments, values, exponents), the snapshots, the sales,
        the end state, the missing conversions — is identical with the flag on and off."""
        book = BOOKS[name]
        off = _build(book.ledger(), date_from=book.date_from)
        on = _with_frames(name)
        for f in dataclasses.fields(PortfolioCalculationResult):
            if f.name in {"position_frames", "native_cash"}:
                continue
            assert _deep(getattr(on, f.name)) == _deep(getattr(off, f.name)), f"{f.name} differs with the flag on"

    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_asked_the_frames_are_a_tuple_of_position_frames(self, name):
        frames = _frames(name)
        assert frames, "precondition: the book holds positions"
        assert all(isinstance(frame, PositionFrame) for frame in frames)

    def test_asked_on_a_book_with_no_position_the_frames_are_an_empty_tuple(self):
        ledger = _ledger([_tx(id=1, dt=date(2025, 1, 2), amount="100")], {A: Decimal("1")}, date_to=date(2025, 1, 10))
        assert _build(ledger, date_from=date(2025, 1, 1), compute_position_frames=True).position_frames == ()


# =============================================================================
# 3. EVERY DAY, EVERY HELD POSITION: ONE FRAME, THE ENGINE'S VALUES
# =============================================================================


class TestCoverage:
    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_every_frame_lies_in_the_range(self, name):
        book = BOOKS[name]
        for frame in _frames(name):
            assert book.date_from <= frame.start <= frame.end <= book.date_to, frame

    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_every_held_position_has_exactly_one_frame_a_day_with_the_engines_values(self, name):
        frames = _frames(name)
        for day, held in _reference(name).items():
            covering = _covering(frames, day)
            by_position: dict[tuple[int, int], list[PositionFrame]] = {}
            for frame in covering:
                by_position.setdefault((frame.broker_id, frame.asset_id), []).append(frame)
            assert set(by_position) == set(held), f"{day}: frames for {sorted(by_position)}, held {sorted(held)}"
            for position, found in by_position.items():
                assert len(found) == 1, f"{day} {position}: {len(found)} frames cover the day"
                assert _values(found[0]) == _values(held[position]), f"{day} {position}: frame {_values(found[0])}, engine {_values(held[position])}"

    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_no_frame_has_a_quantity_at_or_below_zero(self, name):
        assert all(frame.quantity > 0 for frame in _frames(name))


# =============================================================================
# 4. MAXIMAL MERGE AND ORDER
# =============================================================================


class TestMergeAndOrder:
    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_adjacent_frames_of_a_position_never_carry_the_same_values(self, name):
        frames = _frames(name)
        for position in {(frame.broker_id, frame.asset_id) for frame in frames}:
            mine = _of(frames, *position)
            for previous, following in zip(mine, mine[1:], strict=False):
                if following.start == previous.end + timedelta(days=1):
                    assert _values(following) != _values(previous), f"{position}: {previous.start}..{previous.end} and {following.start}..{following.end} carry the same values"

    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_grouped_by_position_in_replay_order_each_group_ascending(self, name):
        frames = _frames(name)
        result = _with_frames(name)
        assert result.end_state is not None
        replay_order = [(broker_id, asset_id) for asset_id, broker_id in result.end_state.cumulative_qty]
        assert replay_order != sorted(replay_order) or len(replay_order) < 2 or name == "two-assets", "precondition: the replay order is not a sort"
        groups: list[tuple[int, int]] = []
        for frame in frames:
            position = (frame.broker_id, frame.asset_id)
            if not groups or groups[-1] != position:
                assert position not in groups, f"{position}'s frames are not contiguous in the tuple"
                groups.append(position)
        assert groups == [position for position in replay_order if position in set(groups)]
        for position in groups:
            mine = _of(frames, *position)
            for previous, following in zip(mine, mine[1:], strict=False):
                assert following.start > previous.end, f"{position}: {following.start} does not follow {previous.end}"


# =============================================================================
# 5. BIT PARITY WITH THE DAILY STATES
# =============================================================================


class TestBitParity:
    @pytest.mark.parametrize("name", BOOK_IDS)
    def test_the_frames_market_values_add_up_to_the_days_market_value(self, name):
        book = BOOKS[name]
        result = _with_frames(name)
        frames = _frames(name)
        for day in _days(book.date_from, book.date_to):
            total = Decimal("0")
            for frame in frames:
                if frame.start <= day <= frame.end and frame.market_value is not None:
                    total += frame.market_value
            state = result.daily_states.state_on(day)
            assert state is not None
            assert total == state.market_value and total.as_tuple() == state.market_value.as_tuple(), f"{day}: frames {total!r}, state {state.market_value!r}"


# =============================================================================
# 6. THE BOOKS' OWN CASES
# =============================================================================


class TestTwoAssets:
    def test_preconditions(self):
        ref = _reference("two-assets")
        for quote in Y_QUOTES:
            before = quote - timedelta(days=1)
            if (A, X) in ref[quote]:
                assert _values(ref[quote][(A, X)]) == _values(ref[before][(A, X)]), f"X changes on Y's quote day {quote}"
        for day in _days(X_SOLD_OUT, X_REOPENED - timedelta(days=1)):
            assert (A, X) not in ref[day]
        assert (A, X) in ref[X_SOLD_OUT - timedelta(days=1)] and (A, X) in ref[X_REOPENED]

    def test_a_quote_of_the_other_asset_never_splits_a_frame(self):
        frames = _frames("two-assets")
        x_starts = {frame.start for frame in _of(frames, A, X)}
        y_starts = {frame.start for frame in _of(frames, A, Y)}
        assert not x_starts & set(Y_QUOTES), f"X frames start on Y's quote days {sorted(x_starts & set(Y_QUOTES))}"
        x_only_days = set(X_QUOTES) | {date(2025, 1, 10), X_SOLD_OUT, X_REOPENED}
        assert not y_starts & x_only_days, f"Y frames start on X's days {sorted(y_starts & x_only_days)}"

    def test_the_full_sale_ends_the_position_and_the_rebuy_opens_it_again(self):
        x_frames = _of(_frames("two-assets"), A, X)
        before = [frame for frame in x_frames if frame.start < X_SOLD_OUT]
        after = [frame for frame in x_frames if frame.start >= X_SOLD_OUT]
        assert before[-1].end == X_SOLD_OUT - timedelta(days=1), "the last frame before the full sale ends the day before it"
        assert after and after[0].start == X_REOPENED, "nothing until the rebuy, which opens a new frame"
        assert not _covering(x_frames, X_SOLD_OUT) and not _covering(x_frames, X_REOPENED - timedelta(days=1))

    def test_the_partial_sale_starts_a_frame_with_the_quantity_left(self):
        x_frames = _of(_frames("two-assets"), A, X)
        (frame,) = _covering(x_frames, date(2025, 1, 10))
        assert frame.start == date(2025, 1, 10)
        assert frame.quantity == Decimal("6")


class TestFx:
    def test_preconditions(self):
        ref = _reference("fx")
        for day in USD_RATE_DAYS:
            assert _values(ref[day][(A, U)]) != _values(ref[day - timedelta(days=1)][(A, U)]), f"U does not change on the rate day {day}"
        held_g = [day for day, held in ref.items() if (A, G) in held]
        assert held_g and all(ref[day][(A, G)].market_value is None for day in held_g), "G has no rate: never valued"
        held_w = [day for day, held in ref.items() if (A, W) in held]
        assert held_w and all(ref[day][(A, W)].valuation_source == ValuationSource.ESTIMATED_AT_COST for day in held_w)
        assert ref[date(2025, 2, 5)][(A, U)].quantity == Decimal("5.0"), "U at the broker's share 0.5"

    def test_the_foreign_assets_frame_splits_on_the_rate_days(self):
        u_starts = {frame.start for frame in _of(_frames("fx"), A, U)}
        assert set(USD_RATE_DAYS) <= u_starts

    def test_the_unpriced_asset_valued_at_cost_is_one_frame(self):
        (frame,) = _of(_frames("fx"), A, W)
        assert (frame.start, frame.end) == (W_ARRIVES, FX_TO)
        assert frame.valuation_source == ValuationSource.ESTIMATED_AT_COST
        assert frame.market_value == Decimal("50") and frame.quantity == Decimal("2")

    def test_the_asset_without_a_rate_has_no_market_value_and_ignores_the_usd_rate(self):
        g_frames = _of(_frames("fx"), A, G)
        assert g_frames and all(frame.market_value is None and frame.unrealized_pnl is None for frame in g_frames)
        assert not {frame.start for frame in g_frames} & set(USD_RATE_DAYS)


class TestTransfer:
    def test_preconditions(self):
        ref = _reference("transfer")
        assert _values(ref[DEPARTURE][(B, X)]) == _values(ref[DEPARTURE - timedelta(days=1)][(B, X)]), "B does not change on A's departure"
        assert _values(ref[ARRIVAL][(A, X)]) == _values(ref[ARRIVAL - timedelta(days=1)][(A, X)]), "A does not change on B's arrival"
        assert ref[DEPARTURE][(A, X)].quantity == Decimal("7") and ref[ARRIVAL][(B, X)].quantity == Decimal("7")

    def test_no_frame_before_date_from_and_the_first_frames_start_on_it(self):
        frames = _frames("transfer")
        assert min(frame.start for frame in frames) == TRANSFER_FROM
        for position in ((A, X), (B, X)):
            assert _of(frames, *position)[0].start == TRANSFER_FROM, position

    def test_each_broker_splits_on_its_own_leg_only(self):
        frames = _frames("transfer")
        a_starts = {frame.start for frame in _of(frames, A, X)}
        b_starts = {frame.start for frame in _of(frames, B, X)}
        assert DEPARTURE in a_starts and ARRIVAL not in a_starts
        assert ARRIVAL in b_starts and DEPARTURE not in b_starts
