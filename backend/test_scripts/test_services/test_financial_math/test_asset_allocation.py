"""MF5-1b — the asset dimension of the allocations: ``by_asset`` in every daily state, and its two views.

Today a day's allocation has three dimensions (``by_type``, ``by_sector``, ``by_geography``, cash as «Liquidity» in the
first two); no dimension says which asset holds the value. Workstreams J and Y need it. The cure (contract):

- ``DailyPortfolioState.by_asset: dict[int, Decimal] = field(default_factory=dict)``: asset_id → the sum of the market
  values (report currency) of its held positions that day, every broker, only values that are not None — the very
  values summed into ``market_value``, so ``sum(by_asset.values())`` is ``market_value``. Cash is not in it; nor are
  securities in transit (they are not held positions). ``StateSegment.state_on`` copies it like the other containers;
- ``DerivedViewsBuilder.build_asset_allocation_current(names)`` and ``.build_asset_allocation_history(names,
  date_from=None)`` (items ``{"date", "components"}``, from ``date_from`` like ``build_allocation_history``): one
  component per asset of the day's ``by_asset`` — ``{"name": names.get(asset_id, f"Asset {asset_id}"), "id": asset_id,
  "value": pct, "amount": amount, "emoji": None}`` — plus ``{"name": "Liquidity", "id": None, ...}`` with amount
  ``cash_value + in_transit_cash_value``, always present; pct = ``weights.slice_percents`` over all the slices,
  quantized to 0.01; sorted by amount descending; the current one reads the last state;
- schemas: ``AllocationItem.id: Optional[int] = None``; ``PortfolioSummary.allocation_by_asset`` (default empty);
  ``AllocationHistoryDimensions.asset`` (default empty). The report's wiring is tested on a private database in
  ``test_financial/test_asset_allocation_report.py``.

What is tested (pure: the builder fed by hand as in ``test_position_frames.py``; hand-made states for the views):

1. ``TestByAssetFromTheEngine`` — on a book with one asset on two brokers, a security in transit between them, cash in
   transit, an asset with no rate (market value None: never in ``by_asset``), an asset valued at cost (in it), and a
   position closed: on every day ``by_asset`` is the per-asset sum of the engine's own position values at the end of
   that day (the snapshot of a build with ``period_start=d``, as in ``test_position_frames.py``), by value and
   exponent; ``sum(by_asset.values())`` from ``Decimal("0")`` is ``market_value``, by value and exponent; a quiet day
   gets a copy, never the stored dict.
2. ``TestTheViews`` — exact components on hand-made states (names and the ``Asset {id}`` fallback, ids, percentages
   to 0.01, amounts and their exponents, Liquidity always present, negative cash, the order), the history over a
   ``DailyStates`` with quiet days, ``date_from``, empty inputs.
3. ``TestTheSchemas`` — the three schema fields.

Ambiguities resolved: an asset whose every held position has no market value is ABSENT from ``by_asset`` (no zero
entry: «only values that are not None»); the history's components are checked on name, id, value and amount, and
their ``emoji`` must be None or absent (``build_allocation_history``'s components carry no emoji today; the current
view's carry ``"emoji": None``, as ``build_allocation_current``'s do); with no state the current view is ``[]``.
Amounts are distinct in every case, so «descending» never depends on how ties are broken.

RED on HEAD 5dc68b650, by absence: ``DailyPortfolioState`` has no ``by_asset`` (the builder tests fail with
``AttributeError``, the hand-made states with ``TypeError``), ``DerivedViewsBuilder`` has no asset views
(``AttributeError``), the schemas refuse ``id`` and lack the two fields (``ValidationError`` / ``KeyError`` /
``AttributeError``). The module collects.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

import dataclasses
from datetime import date, timedelta
from decimal import Decimal
from functools import cache
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.schemas.portfolio import AllocationHistoryDimensions, AllocationHistoryPoint, AllocationItem, PortfolioSummary
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, DailyStates, PortfolioCalculationResult, StateSegment
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.app.services.financial_math.weights import slice_percents
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X, G, W = 100, 400, 500
ZERO = Decimal("0")
CENT = Decimal("0.01")

# =============================================================================
# HELPERS — copies of test_position_frames.py
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
    txs_by_asset: dict[int, list] = {}
    for ctxn in kwargs["classified_txs"]:
        if ctxn.tx.asset_id is not None:
            txs_by_asset.setdefault(ctxn.tx.asset_id, []).append(ctxn.tx)
    mark_series = {}
    for aid in set(txs_by_asset) | set(kwargs["price_map"]):
        series = build_asset_price_series(
            price_rows=kwargs["price_map"].get(aid, []),
            transactions=txs_by_asset.get(aid, []),
            split_linked_tx_ids=set(),
            asset_currency=kwargs["asset_currencies"].get(aid, "EUR"),
            quote_base_quantity=1,
        )
        if series.has_observations:
            mark_series[aid] = series
    kwargs.setdefault("mark_series", mark_series)
    kwargs.setdefault(
        "average_costs",
        engine_average_costs(kwargs["classified_txs"], asset_currencies=kwargs["asset_currencies"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]),
    )
    kwargs.setdefault("native_cash", engine_native_cash(kwargs["classified_txs"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]))
    return kwargs


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _same(got, expected) -> bool:
    if not isinstance(got, Decimal) or not isinstance(expected, Decimal):
        return got == expected
    return got == expected and got.as_tuple() == expected.as_tuple()


def _by_day(steps: list[dict]) -> dict[date, dict]:
    """The history's steps (D-P4: each holds from ``date`` to ``through``, both included) as one entry per day.

    Also asserts the series' invariant: in order, no overlap, no gap (an allocation history has a state every day).
    """
    days: dict[date, dict] = {}
    for step in steps:
        assert step["date"] <= step["through"], f"step {step['date']}..{step['through']} ends before it starts"
        for day in _days(step["date"], step["through"]):
            assert day not in days, f"{day} is covered by two steps"
            days[day] = step
    ordered = sorted(days)
    assert ordered == _days(ordered[0], ordered[-1]) if ordered else True, "the steps leave a gap"
    assert list(days) == ordered, "the steps are not in order"
    return days


def _same_components(got: list[dict], expected: list[dict]) -> bool:
    """Two components lists equal field by field, the Decimals with their exponent."""
    return len(got) == len(expected) and all(a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a) for a, b in zip(got, expected, strict=True))


# =============================================================================
# 1. by_asset FROM THE ENGINE
# =============================================================================

BOOK_FROM, BOOK_TO = date(2025, 4, 1), date(2025, 4, 20)
IN_TRANSIT_DAY, CASH_IN_TRANSIT_DAY = date(2025, 4, 8), date(2025, 4, 13)
A_CLOSES = date(2025, 4, 17)


def _book() -> dict:
    """A deposits 3000 and B 2000 (04-01); A buys 10 X for 1000 and B 4 X for 400 (04-02); A buys 2 G (a GBP stock, no
    GBP rate at all) for 200 GBP (04-03); A receives 3 W (never priced) at a cost of 20 a unit (04-04); 2 X leave A on
    04-07 and reach B on 04-10; 300 EUR leave A on 04-12 and reach B on 04-15; A sells its last 8 X for 900 (04-17).
    X closes 105 (04-05) and 110 (04-14). Both brokers at share 1."""
    txs = [
        _tx(id=1, dt=date(2025, 4, 1), amount="3000"),
        _tx(id=2, broker_id=B, dt=date(2025, 4, 1), amount="2000"),
        _tx(id=3, type="BUY", dt=date(2025, 4, 2), amount="-1000", quantity="10", asset_id=X),
        _tx(id=4, broker_id=B, type="BUY", dt=date(2025, 4, 2), amount="-400", quantity="4", asset_id=X),
        _tx(id=5, type="BUY", dt=date(2025, 4, 3), amount="-200", currency="GBP", quantity="2", asset_id=G),
        _tx(id=6, type="ADJUSTMENT", dt=date(2025, 4, 4), quantity="3", asset_id=W, currency=None, cost_basis_override="20", cost_basis_currency="EUR"),
        _tx(id=7, type="TRANSFER", dt=date(2025, 4, 7), quantity="-2", asset_id=X, currency=None, related_id=8),
        _tx(id=8, broker_id=B, type="TRANSFER", dt=date(2025, 4, 10), quantity="2", asset_id=X, currency=None, related_id=7),
        _tx(id=9, type="CASH_TRANSFER", dt=date(2025, 4, 12), amount="-300", related_id=10),
        _tx(id=10, broker_id=B, type="CASH_TRANSFER", dt=date(2025, 4, 15), amount="300", related_id=9),
        _tx(id=11, type="SELL", dt=A_CLOSES, amount="900", quantity="-8", asset_id=X),
    ]
    shares = {A: Decimal("1"), B: Decimal("1")}
    classification = ScopeAwareTransactionClassifier(scope_broker_ids=set(shares), all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)), broker_shares=shares).classify()
    price_map = {X: [(date(2025, 4, 5), Decimal("105"), "EUR"), (date(2025, 4, 14), Decimal("110"), "EUR")]}
    return {
        "classified_txs": classification.classified,
        "in_transit_intervals": classification.in_transit_intervals,
        "external_cash_flows": classification.external_cash_flows,
        "price_map": price_map,
        "asset_currencies": {X: "EUR", G: "GBP", W: "EUR"},
        "asset_types": {X: "Stock", G: "Stock", W: "Stock"},
        "asset_classifications": {X: None, G: None, W: None},
        "date_to": BOOK_TO,
    }


def _build(**overrides) -> PortfolioCalculationResult:
    return DailyStateBuilder(**_builder_kwargs(**_book(), date_from=BOOK_FROM, **overrides)).build()


@cache
def _result() -> PortfolioCalculationResult:
    return _build()


@cache
def _expected_by_asset() -> dict[date, dict[int, Decimal]]:
    """For each day d: the engine's position values at the end of d (``period_start=d``), summed by asset from
    ``Decimal("0")`` in snapshot order, values that are not None only; an asset with none is absent."""
    expected: dict[date, dict[int, Decimal]] = {}
    for day in _days(BOOK_FROM, BOOK_TO):
        snapshot = _build(period_start=day).position_states_start
        by_asset: dict[int, Decimal] = {}
        for ps in snapshot:
            assert ps.date == day and ps.quantity > 0
            if ps.market_value is not None:
                by_asset[ps.asset_id] = by_asset.get(ps.asset_id, ZERO) + ps.market_value
        expected[day] = by_asset
    return expected


class TestByAssetFromTheEngine:
    def test_preconditions(self):
        result = _result()
        in_transit = result.daily_states.state_on(IN_TRANSIT_DAY)
        assert in_transit.in_transit_asset_market_value != 0, "a security is in transit on 04-08"
        assert result.daily_states.state_on(CASH_IN_TRANSIT_DAY).in_transit_cash_value != 0, "cash is in transit on 04-13"
        assert all(state.cash_value != 0 for state in result.daily_states), "cash every day"
        snapshot = {(ps.broker_id, ps.asset_id): ps for ps in _build(period_start=date(2025, 4, 6)).position_states_start}
        assert snapshot[(A, G)].market_value is None, "G has no rate"
        assert snapshot[(A, W)].market_value == Decimal("60"), "W valued at cost"
        assert (A, X) in snapshot and (B, X) in snapshot, "X on two brokers"
        assert (A, X) not in {(ps.broker_id, ps.asset_id) for ps in _build(period_start=A_CLOSES).position_states_start}

    def test_every_day_by_asset_is_the_per_asset_sum_of_the_engines_position_values(self):
        result = _result()
        for day, expected in _expected_by_asset().items():
            got = result.daily_states.state_on(day).by_asset
            assert isinstance(got, dict)
            assert set(got) == set(expected), f"{day}: assets {sorted(got)}, expected {sorted(expected)}"
            for asset_id, amount in expected.items():
                assert _same(got[asset_id], amount), f"{day} asset {asset_id}: {got[asset_id]!r}, expected {amount!r}"

    def test_by_asset_adds_up_to_the_market_value_to_the_exponent(self):
        for state in _result().daily_states:
            total = sum(state.by_asset.values(), ZERO)
            assert _same(total, state.market_value), f"{state.date}: by_asset {total!r}, market_value {state.market_value!r}"

    def test_no_cash_and_no_unvalued_asset(self):
        for state in _result().daily_states:
            assert G not in state.by_asset, f"{state.date}: G has no market value"
            assert all(isinstance(key, int) for key in state.by_asset), f"{state.date}: {sorted(map(repr, state.by_asset))}"

    def test_the_closed_position_leaves_only_the_other_broker(self):
        """From 04-17 X is held by B only (6 units): its amount is B's position value alone."""
        expected = _expected_by_asset()
        snapshot = {(ps.broker_id, ps.asset_id): ps for ps in _build(period_start=A_CLOSES).position_states_start}
        assert _same(expected[A_CLOSES][X], snapshot[(B, X)].market_value)
        assert _same(_result().daily_states.state_on(A_CLOSES).by_asset[X], snapshot[(B, X)].market_value)

    def test_a_quiet_day_gets_a_copy(self):
        ds = _result().daily_states
        quiet = [seg for seg in ds.segments if seg.end > seg.start and seg.state.by_asset]
        assert quiet, "precondition: a segment with quiet days and assets"
        for seg in quiet:
            day = seg.start + timedelta(days=1)
            materialized = seg.state_on(day)
            assert materialized.by_asset == seg.state.by_asset
            assert materialized.by_asset is not seg.state.by_asset, f"{day}: by_asset is shared with the stored state"


# =============================================================================
# 2. THE VIEWS
# =============================================================================

NAMES = {X: "Alpha Corp", W: "Omega Fund"}
UNNAMED = 7


def _state(day: date, *, by_asset: dict[int, str], cash: str, in_transit_cash: str = "0") -> DailyPortfolioState:
    """A hand-made state: its by_asset and its cash; every other figure consistent but irrelevant to the views."""
    amounts = {asset_id: Decimal(amount) for asset_id, amount in by_asset.items()}
    market_value = sum(amounts.values(), ZERO)
    cash_value, it_cash = Decimal(cash), Decimal(in_transit_cash)
    nav = market_value + cash_value + it_cash
    return DailyPortfolioState(
        date=day,
        cash_value=cash_value,
        market_value=market_value,
        broker_nav_value=market_value + cash_value,
        in_transit_cash_value=it_cash,
        in_transit_asset_market_value=ZERO,
        in_transit_market_value=it_cash,
        nav_value=nav,
        open_cost_basis=market_value,
        in_transit_asset_cost_basis=ZERO,
        in_transit_book_value=it_cash,
        book_value=nav,
        unrealized_gain_loss=ZERO,
        external_cash_flow=ZERO,
        cumulative_external_cash_flow=nav,
        book_asset_like=market_value,
        cash_from_contributed_capital=cash_value + it_cash,
        cash_from_generated_returns=ZERO,
        total_pnl=ZERO,
        by_type={"Stock": market_value, "Liquidity": cash_value + it_cash},
        by_asset=amounts,
    )


def _expected_components(state: DailyPortfolioState) -> list[dict]:
    """The contract's components of ``state``, every slice's percentage from ``weights.slice_percents``."""
    liquidity = state.cash_value + state.in_transit_cash_value
    slices = {str(asset_id): amount for asset_id, amount in state.by_asset.items()} | {"Liquidity": liquidity}
    percents = slice_percents(slices)
    components = [{"name": NAMES.get(asset_id, f"Asset {asset_id}"), "id": asset_id, "value": percents[str(asset_id)].quantize(CENT), "amount": amount, "emoji": None} for asset_id, amount in state.by_asset.items()]
    components.append({"name": "Liquidity", "id": None, "value": percents["Liquidity"].quantize(CENT), "amount": liquidity, "emoji": None})
    return sorted(components, key=lambda component: -component["amount"])


def _assert_components(got: list[dict], expected: list[dict], *, emoji_key_required: bool) -> None:
    assert [(c.get("name"), c.get("id")) for c in got] == [(c["name"], c["id"]) for c in expected], "names, ids and order"
    for mine, want in zip(got, expected, strict=True):
        if emoji_key_required:
            assert mine == want, f"{mine} != {want}"
        else:
            assert {k: mine.get(k) for k in ("name", "id", "value", "amount")} == {k: want[k] for k in ("name", "id", "value", "amount")}
            assert set(mine) <= {"name", "id", "value", "amount", "emoji"} and mine.get("emoji") is None
        assert _same(mine["value"], want["value"]), f"{mine['name']}: value {mine['value']!r}, expected {want['value']!r}"
        assert _same(mine["amount"], want["amount"]), f"{mine['name']}: amount {mine['amount']!r}, expected {want['amount']!r}"


D1, D2, D3, D4, D5 = (date(2025, 5, d) for d in (1, 2, 3, 4, 5))


class TestTheViews:
    def test_current_reads_the_last_state(self):
        states = [
            _state(D1, by_asset={X: "100"}, cash="50"),
            _state(D2, by_asset={X: "1234.567", W: "60.00", UNNAMED: "15.5"}, cash="200.10", in_transit_cash="25"),
        ]
        got = DerivedViewsBuilder(states, "EUR").build_asset_allocation_current(NAMES)
        assert isinstance(got, list)
        expected = _expected_components(states[-1])
        assert [c["name"] for c in expected] == ["Alpha Corp", "Liquidity", "Omega Fund", "Asset 7"], "precondition: the order"
        _assert_components(got, expected, emoji_key_required=True)

    def test_liquidity_is_cash_plus_cash_in_transit(self):
        state = _state(D1, by_asset={X: "10"}, cash="3.50", in_transit_cash="1.25")
        got = DerivedViewsBuilder([state], "EUR").build_asset_allocation_current(NAMES)
        (liquidity,) = [c for c in got if c["id"] is None]
        assert liquidity["name"] == "Liquidity"
        assert _same(liquidity["amount"], Decimal("4.75"))

    def test_liquidity_is_present_at_zero(self):
        state = _state(D1, by_asset={X: "80", W: "20"}, cash="0")
        got = DerivedViewsBuilder([state], "EUR").build_asset_allocation_current(NAMES)
        _assert_components(got, _expected_components(state), emoji_key_required=True)
        assert [c["name"] for c in got] == ["Alpha Corp", "Omega Fund", "Liquidity"]
        assert _same(got[-1]["amount"], ZERO) and got[-1]["value"] == ZERO

    def test_negative_cash_is_a_negative_slice(self):
        """Signed slices: cash below zero, the assets above 100 % (slice_percents divides by the signed sum)."""
        state = _state(D1, by_asset={X: "300", W: "100"}, cash="-150")
        got = DerivedViewsBuilder([state], "EUR").build_asset_allocation_current(NAMES)
        _assert_components(got, _expected_components(state), emoji_key_required=True)
        assert got[0]["value"] == Decimal("120.00") and got[-1]["name"] == "Liquidity" and got[-1]["value"] == Decimal("-60.00")

    def test_no_asset_only_liquidity(self):
        state = _state(D1, by_asset={}, cash="500")
        got = DerivedViewsBuilder([state], "EUR").build_asset_allocation_current(NAMES)
        _assert_components(got, [{"name": "Liquidity", "id": None, "value": Decimal("100.00"), "amount": Decimal("500"), "emoji": None}], emoji_key_required=True)

    def test_no_state_no_component(self):
        views = DerivedViewsBuilder([], "EUR")
        assert views.build_asset_allocation_current(NAMES) == []
        assert views.build_asset_allocation_history(NAMES) == []
        assert DerivedViewsBuilder(DailyStates(), "EUR").build_asset_allocation_history(NAMES) == []

    def test_history_on_a_list_every_day(self):
        states = [
            _state(D1, by_asset={X: "100"}, cash="900"),
            _state(D2, by_asset={X: "110", W: "40"}, cash="850.5"),
            _state(D3, by_asset={W: "45"}, cash="1000"),
        ]
        got = DerivedViewsBuilder(states, "EUR").build_asset_allocation_history(NAMES)
        # Steps (D-P4): on a plain list every state is a change day, and these three states differ, so one step a day
        assert [(point["date"], point["through"]) for point in got] == [(D1, D1), (D2, D2), (D3, D3)]
        for point, state in zip(got, states, strict=True):
            assert set(point) == {"date", "through", "components"}
            _assert_components(point["components"], _expected_components(state), emoji_key_required=False)

    def test_history_on_a_list_merges_identical_consecutive_states(self):
        """Steps are maximal (D-P4): on a plain list two consecutive days with the same components (Decimals with their
        exponent) are one step, while a day whose amount has another exponent starts a new one."""
        states = [
            _state(D1, by_asset={X: "100"}, cash="900"),
            _state(D2, by_asset={X: "100"}, cash="900"),
            _state(D3, by_asset={X: "100.0"}, cash="900"),
        ]
        got = DerivedViewsBuilder(states, "EUR").build_asset_allocation_history(NAMES)
        assert [(point["date"], point["through"]) for point in got] == [(D1, D2), (D3, D3)]
        _assert_components(got[0]["components"], _expected_components(states[0]), emoji_key_required=False)
        _assert_components(got[1]["components"], _expected_components(states[2]), emoji_key_required=False)

    def test_history_from_date_from(self):
        states = [_state(day, by_asset={X: str(100 + index)}, cash=str(50 - index)) for index, day in enumerate((D1, D2, D3, D4))]
        got = DerivedViewsBuilder(states, "EUR").build_asset_allocation_history(NAMES, date_from=D3)
        assert [(point["date"], point["through"]) for point in got] == [(D3, D3), (D4, D4)]
        _assert_components(got[0]["components"], _expected_components(states[2]), emoji_key_required=False)

    def test_history_over_segments_holds_each_quiet_day(self):
        """On the engine's DailyStates a quiet day is inside its segment's step (D-P4): the window start and the segment
        start are the change days, each step holds its segment's components from its ``date`` to its ``through``."""
        s1 = _state(D1, by_asset={X: "100", UNNAMED: "7"}, cash="20")
        s3 = _state(D4, by_asset={W: "70"}, cash="30", in_transit_cash="5")
        ds = DailyStates([StateSegment(start=D1, end=D3, state=s1), StateSegment(start=D4, end=D5, state=s3)])
        got = DerivedViewsBuilder(ds, "EUR").build_asset_allocation_history(NAMES, date_from=D2)
        assert [(point["date"], point["through"]) for point in got] == [(D2, D3), (D4, D5)], "window start D2 opens a step, the segment start D4 the next"
        for day, point in _by_day(got).items():
            state = s1 if day <= D3 else s3
            _assert_components(point["components"], _expected_components(state), emoji_key_required=False)
        whole = DerivedViewsBuilder(ds, "EUR").build_asset_allocation_history(NAMES)
        assert [(point["date"], point["through"]) for point in whole] == [(D1, D3), (D4, D5)]

    def test_current_on_segments_reads_the_last_day(self):
        s1 = _state(D1, by_asset={X: "100"}, cash="20")
        s2 = _state(D2, by_asset={X: "90", W: "15"}, cash="25")
        ds = DailyStates([StateSegment(start=D1, end=D1, state=s1), StateSegment(start=D2, end=D5, state=s2)])
        _assert_components(DerivedViewsBuilder(ds, "EUR").build_asset_allocation_current(NAMES), _expected_components(s2), emoji_key_required=True)

    def test_the_engines_states_give_the_views(self):
        """On the engine's book, the steps expanded to days (D-P4) cover every day of the book once, and on every day the
        components are the contract's on that day's state (G never one); two consecutive steps never hold the same
        components, so the steps are maximal."""
        ds = _result().daily_states
        names = {X: "X", W: "W", G: "G"}
        history = DerivedViewsBuilder(ds, "EUR").build_asset_allocation_history(names)
        by_day = _by_day(history)
        assert list(by_day) == _days(BOOK_FROM, BOOK_TO)
        assert len(history) < len(by_day), "the quiet days of the book are inside steps, not one step each"
        for earlier, later in zip(history, history[1:], strict=False):
            assert not _same_components(earlier["components"], later["components"]), f"steps ending {earlier['through']} and starting {later['date']} hold the same components"
        for day, point in by_day.items():
            state = ds.state_on(day)
            amounts = {c["id"]: c["amount"] for c in point["components"]}
            assert set(amounts) == set(state.by_asset) | {None}
            assert G not in amounts
            assert _same(amounts[None], state.cash_value + state.in_transit_cash_value)
            assert sum(amounts.values(), ZERO) == state.market_value + state.cash_value + state.in_transit_cash_value
            ordered = [c["amount"] for c in point["components"]]
            assert ordered == sorted(ordered, reverse=True)


# =============================================================================
# 3. THE SCHEMAS
# =============================================================================


class TestTheSchemas:
    def test_allocation_item_id_is_optional(self):
        assert AllocationItem(name="Liquidity", value=Decimal("10.00"), amount=Decimal("5")).id is None
        assert AllocationItem(name="Alpha Corp", value=Decimal("90.00"), amount=Decimal("45"), id=X).id == X

    def test_portfolio_summary_has_allocation_by_asset_empty_by_default(self):
        field = PortfolioSummary.model_fields["allocation_by_asset"]
        assert not field.is_required()
        assert field.get_default(call_default_factory=True) == []

    def test_allocation_history_dimensions_has_asset_empty_by_default(self):
        assert AllocationHistoryDimensions().asset == []
        point = AllocationHistoryPoint(date=D1, through=D2, components=[{"name": "Alpha Corp", "id": X, "value": Decimal("100.00"), "amount": Decimal("1"), "emoji": None}])
        assert AllocationHistoryDimensions(asset=[point]).asset[0].components[0].id == X

    def test_the_state_field_defaults_to_an_empty_dict(self):
        field = {f.name: f for f in dataclasses.fields(DailyPortfolioState)}["by_asset"]
        assert field.default_factory() == {}
