"""
MF5-3 · B5 — securities that cross the scope boundary at market value: the records and the period result.

A TRANSFER leg with no internal partner in the scope (``linked_external_inflow`` / ``linked_external_outflow``, a
missing partner, an orphan) is in-kind capital at market value on its date (lot 41, D2/D5:
``DailyStateBuilder._transfer_leg_capital``), while the position's cost moves by the leg's cost step
(``step.cost_report_change``). In a view filtered on the sender the period identity
``pnl = ugl_delta + realized + income − fees + other`` therefore leaves MV − cost in «other»; for the receiver,
cost − MV. Today that amount hides in the waterfall's «Other / reconciliation residual».

The contract (lot MF5-3 · B5):

1. ``financial_math/portfolio/models.py``::

       @dataclass(frozen=True, slots=True)
       class MarketValueTransfer:
           transaction_id: int | None
           broker_id: int
           asset_id: int
           date: date
           capital: Decimal   # what _transfer_leg_capital returns: + received, − sent (report currency, owner's share)
           cost: Decimal      # step.cost_report_change (signed); Decimal("0") without a step

   ``PortfolioCalculationResult.market_value_transfers`` (default empty): one record for every leg for which
   ``_transfer_leg_capital`` returned a value (not None), in replay order, whatever its date (before date_from too).

2. ``financial_math/portfolio/period.py``::

       market_value_transfer_results(transfers, date_from, end) -> dict[int, Decimal]

   by broker, Σ (cost − capital) of the legs dated in (date_from, end] (date_from None: every leg dated ≤ end);
   a broker with no such leg is absent (one whose legs sum to 0 is present, at 0).

What is tested here (pure — no database, no server, no network):

- ``TestMarketValueTransferResults``: the period function on hand-made records — bounds (date_from exclusive, end
  inclusive), date_from None, several brokers and legs, a 0-result leg, absent brokers, any iterable, exact Decimals.
- ``TestBuilderRecords``: ``DailyStateBuilder.build()`` on books where a TRANSFER leaves or enters the scope (the
  helpers mirror ``test_services/test_financial/test_portfolio_engine/test_broker_internal_flows.py``, which builds
  the D2 cases): the records carry exactly ``_transfer_leg_capital``'s capital and the step's cost (checked against
  hand-computed numbers AND against a spy on ``_transfer_leg_capital``); an internal pair, a split-linked TRANSFER and
  a priced in-kind ADJUSTMENT give none; a leg before date_from is recorded; the owner's share scales both figures;
  the order is the replay's.

Red by absence on HEAD b6a25adcb: neither ``MarketValueTransfer``, ``market_value_transfer_results`` nor the result's
``market_value_transfers`` exist. Names are looked up while each test runs (never at import), so the file collects and
every test fails on its own with the missing name — except the spy's guard, which pins today's
``_transfer_leg_capital`` values and is green before and after the cure.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

import dataclasses
import importlib
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B, C, D = 10, 20, 30, 40
ASSET = 100
UNPRICED_ASSET = 200

D0 = date(2025, 1, 1)
D1 = date(2025, 1, 2)
D2 = date(2025, 1, 3)
D3 = date(2025, 1, 4)
D4 = date(2025, 1, 5)
D5 = date(2025, 1, 6)
DAYS = (D0, D1, D2, D3, D4, D5)

_MODELS = "backend.app.services.financial_math.portfolio.models"
_PERIOD = "backend.app.services.financial_math.portfolio.period"


# =============================================================================
# CONTRACT ACCESSORS — looked up per test, so a missing name fails that test only
# =============================================================================


def _contract(module_name: str, name: str):
    module = importlib.import_module(module_name)
    found = getattr(module, name, None)
    if found is None:
        pytest.fail(f"contract missing: {module_name}.{name} does not exist")
    return found


def _mvt(*, transaction_id: int | None = None, broker_id: int, asset_id: int = ASSET, on: date, capital: str, cost: str):
    """One MarketValueTransfer, by keyword (the contract's field names)."""
    cls = _contract(_MODELS, "MarketValueTransfer")
    return cls(transaction_id=transaction_id, broker_id=broker_id, asset_id=asset_id, date=on, capital=Decimal(capital), cost=Decimal(cost))


def _results(transfers, date_from: date | None, end: date) -> dict[int, Decimal]:
    return _contract(_PERIOD, "market_value_transfer_results")(transfers, date_from, end)


def _records(result) -> list:
    if not hasattr(result, "market_value_transfers"):
        pytest.fail("contract missing: PortfolioCalculationResult has no market_value_transfers")
    return list(result.market_value_transfers)


def _as_tuples(records) -> list[tuple]:
    """(transaction_id, broker_id, asset_id, date, capital, cost) of each record, in order."""
    return [(r.transaction_id, r.broker_id, r.asset_id, r.date, r.capital, r.cost) for r in records]


# =============================================================================
# 1 — THE PERIOD FUNCTION, ON HAND-MADE RECORDS
# =============================================================================


class TestMarketValueTransferRecord:
    def test_the_record_is_a_frozen_slotted_dataclass_with_the_contract_fields(self):
        cls = _contract(_MODELS, "MarketValueTransfer")
        assert dataclasses.is_dataclass(cls)
        assert [f.name for f in dataclasses.fields(cls)] == ["transaction_id", "broker_id", "asset_id", "date", "capital", "cost"]
        record = _mvt(transaction_id=3, broker_id=A, on=D1, capital="-800", cost="-500")
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.capital = Decimal("0")  # type: ignore[misc]
        assert not hasattr(record, "__dict__"), "slots=True: the record carries no instance __dict__"

    def test_the_engine_result_defaults_to_no_record(self):
        result_cls = _contract(_MODELS, "PortfolioCalculationResult")
        field = next((f for f in dataclasses.fields(result_cls) if f.name == "market_value_transfers"), None)
        assert field is not None, "contract missing: PortfolioCalculationResult.market_value_transfers"
        models = importlib.import_module(_MODELS)
        assert result_cls(daily_states=models.DailyStates()).market_value_transfers == []


class TestMarketValueTransferResults:
    def test_sender_and_receiver_of_the_contract_example(self):
        """10 units of cost 500 sent from A when worth 800 (capital −800, cost −500): +300 for A; received by B
        (capital +800, cost +500): −300."""
        transfers = [
            _mvt(transaction_id=3, broker_id=A, on=D2, capital="-800", cost="-500"),
            _mvt(transaction_id=4, broker_id=B, on=D2, capital="800", cost="500"),
        ]
        assert _results(transfers, D0, D5) == {A: Decimal("300"), B: Decimal("-300")}

    def test_window_is_exclusive_at_date_from_and_inclusive_at_end(self):
        transfers = [
            _mvt(transaction_id=1, broker_id=A, on=D1, capital="-110", cost="-100"),  # == date_from: out
            _mvt(transaction_id=2, broker_id=A, on=D2, capital="-120", cost="-100"),  # inside: +20
            _mvt(transaction_id=3, broker_id=A, on=D4, capital="-140", cost="-100"),  # == end: in, +40
            _mvt(transaction_id=4, broker_id=A, on=D5, capital="-150", cost="-100"),  # after end: out
        ]
        assert _results(transfers, D1, D4) == {A: Decimal("60")}

    def test_none_date_from_takes_every_leg_up_to_end(self):
        transfers = [
            _mvt(transaction_id=1, broker_id=A, on=D0, capital="-110", cost="-100"),
            _mvt(transaction_id=2, broker_id=A, on=D3, capital="-130", cost="-100"),
            _mvt(transaction_id=3, broker_id=A, on=D5, capital="-150", cost="-100"),  # after end: out
        ]
        assert _results(transfers, None, D3) == {A: Decimal("40")}

    def test_brokers_with_no_leg_in_the_window_are_absent(self):
        transfers = [
            _mvt(transaction_id=1, broker_id=A, on=D2, capital="-120", cost="-100"),
            _mvt(transaction_id=2, broker_id=B, on=D0, capital="110", cost="100"),  # before the window
            _mvt(transaction_id=3, broker_id=C, on=D5, capital="150", cost="100"),  # after the window
        ]
        got = _results(transfers, D1, D4)
        assert got == {A: Decimal("20")}
        assert B not in got and C not in got

    def test_a_leg_valued_at_its_cost_gives_zero_and_keeps_its_broker(self):
        """J-17: a security with no price is valued at the cost the leg moves, capital = cost → 0. The broker had a leg
        in the window, so it is present, at 0 (absent means: no leg at all)."""
        transfers = [_mvt(transaction_id=1, broker_id=D, asset_id=UNPRICED_ASSET, on=D2, capital="100", cost="100")]
        got = _results(transfers, D0, D5)
        assert set(got) == {D}
        assert got[D] == Decimal("0")

    def test_several_brokers_and_legs_sum_per_broker(self):
        transfers = [
            _mvt(transaction_id=1, broker_id=A, on=D1, capital="-110", cost="-100"),  # +10
            _mvt(transaction_id=2, broker_id=B, on=D1, capital="55.5", cost="50.25"),  # −5.25
            _mvt(transaction_id=3, broker_id=A, on=D3, capital="65", cost="50"),  # −15 (A received too)
            _mvt(transaction_id=4, broker_id=B, on=D4, capital="-0.000000001", cost="0"),  # +0.000000001
            _mvt(transaction_id=5, broker_id=C, on=D5, capital="-7", cost="-7"),  # 0
        ]
        got = _results(transfers, D0, D5)
        assert got == {A: Decimal("-5"), B: Decimal("-5.249999999"), C: Decimal("0")}

    def test_any_iterable_and_the_empty_case(self):
        records = [_mvt(transaction_id=1, broker_id=A, on=D2, capital="-120", cost="-100")]
        assert _results(iter(records), None, D5) == {A: Decimal("20")}
        assert _results((r for r in records), D2, D5) == {}
        assert _results([], None, D5) == {}

    def test_a_record_without_transaction_id_counts(self):
        transfers = [_mvt(transaction_id=None, broker_id=A, on=D2, capital="-120", cost="-100")]
        assert _results(transfers, D1, D2) == {A: Decimal("20")}

    def test_values_are_exact_decimals(self):
        transfers = [_mvt(transaction_id=1, broker_id=A, on=D2, capital="-123.456789012345678901", cost="-100.000000000000000001")]
        got = _results(transfers, None, D5)
        assert isinstance(got[A], Decimal)
        assert got[A] == Decimal("23.456789012345678900")


# =============================================================================
# 2 — THE BUILDER'S RECORDS (helpers mirror test_broker_internal_flows.py)
# =============================================================================


def _tx(
    *,
    id: int = 1,
    broker_id: int = A,
    type: str = "DEPOSIT",
    dt: date = D0,
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
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override else None
    tx.cost_basis_currency = cost_basis_currency
    return tx


def _mark_series_from(classified_txs, price_map, asset_currencies, split_linked_tx_ids=None):
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        if ctxn.tx.asset_id is not None:
            txs_by_asset.setdefault(ctxn.tx.asset_id, []).append(ctxn.tx)
    mark_series = {}
    for aid in set(txs_by_asset) | set(price_map or {}):
        series = build_asset_price_series(
            price_rows=(price_map or {}).get(aid, []),
            transactions=txs_by_asset.get(aid, []),
            split_linked_tx_ids=split_linked_tx_ids or set(),
            asset_currency=(asset_currencies or {}).get(aid, "EUR"),
            quote_base_quantity=1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _classify(txs, scope, *, shares=None, external_paired=None):
    broker_shares = dict.fromkeys(scope, Decimal("1"))
    broker_shares.update({broker_id: Decimal(share) for broker_id, share in (shares or {}).items()})
    classifier = ScopeAwareTransactionClassifier(scope_broker_ids=set(scope), all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)), broker_shares=broker_shares)
    return classifier.classify(external_paired=external_paired)


def _build(classification, *, date_to: date = D5, date_from: date = D0, price_map=None, split_linked_tx_ids=None):
    price_map = _prices() if price_map is None else price_map
    classified = classification.classified
    asset_ids = {ctxn.tx.asset_id for ctxn in classified if ctxn.tx.asset_id is not None} | set(price_map)
    asset_currencies = dict.fromkeys(asset_ids, "EUR")
    kwargs = {
        "classified_txs": classified,
        "in_transit_intervals": classification.in_transit_intervals,
        "external_cash_flows": classification.external_cash_flows,
        "price_map": price_map,
        "quote_base_map": {},
        "asset_currencies": asset_currencies,
        "fx_rate_map": {},
        "asset_classifications": dict.fromkeys(asset_ids),
        "asset_types": dict.fromkeys(asset_ids, "Stock"),
        "target_currency": "EUR",
        "date_from": date_from,
        "date_to": date_to,
        "mark_series": _mark_series_from(classified, price_map, asset_currencies, split_linked_tx_ids),
        "average_costs": engine_average_costs(classified, asset_currencies=asset_currencies, target_currency="EUR", fx_rate_map={}, split_linked_tx_ids=split_linked_tx_ids, date_to=date_to),
        "native_cash": engine_native_cash(classified, target_currency="EUR", fx_rate_map={}, date_to=date_to),
    }
    if split_linked_tx_ids is not None:
        kwargs["split_linked_tx_ids"] = set(split_linked_tx_ids)
    return DailyStateBuilder(**kwargs).build()


def _prices() -> dict[int, list[tuple[date, Decimal, str]]]:
    """Asset 100 (EUR) closes at 10, 11, 12, 13, 14, 15 on d0..d5."""
    return {ASSET: [(day, Decimal(price), "EUR") for day, price in zip(DAYS, ("10", "11", "12", "13", "14", "15"), strict=True)]}


def _setup_t() -> list[MagicMock]:
    """Broker A deposits 100 EUR and buys 10 units of asset 100 for 100 EUR, both on d0."""
    return [
        _tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="100"),
        _tx(id=2, broker_id=A, type="BUY", dt=D0, amount="-100", quantity="10", asset_id=ASSET),
    ]


def _transfer_pair(out_id: int, in_id: int, *, sender: int, receiver: int, out_dt: date, in_dt: date, qty: str, cost_basis_override: str | None = None):
    common = {"type": "TRANSFER", "amount": "0", "currency": None, "asset_id": ASSET, "cost_basis_override": cost_basis_override, "cost_basis_currency": "EUR" if cost_basis_override else None}
    out_leg = _tx(id=out_id, broker_id=sender, dt=out_dt, quantity=f"-{qty}", related_id=in_id, **common)
    in_leg = _tx(id=in_id, broker_id=receiver, dt=in_dt, quantity=qty, related_id=out_id, **common)
    return out_leg, in_leg


def _classifications(classification) -> dict[int, str]:
    return {ctxn.tx.id: ctxn.classification for ctxn in classification.classified}


@pytest.fixture
def leg_capital_spy(monkeypatch):
    """Every call of ``DailyStateBuilder._transfer_leg_capital`` during a build: (tx id, returned capital, step)."""
    calls: list[tuple[int | None, Decimal | None, object]] = []
    real = DailyStateBuilder._transfer_leg_capital

    def spy(self, ctxn, tx_qty, step=None):
        capital = real(self, ctxn, tx_qty, step)
        calls.append((ctxn.tx.id, capital, step))
        return capital

    monkeypatch.setattr(DailyStateBuilder, "_transfer_leg_capital", spy)
    return calls


def _spy_expectation(calls) -> list[tuple[int | None, Decimal, Decimal]]:
    """(tx id, capital, cost) the contract derives from the spy: one per leg valued, first call order, cost = the step's."""
    seen: set[int | None] = set()
    wanted = []
    for tx_id, capital, step in calls:
        if capital is None or tx_id in seen:
            continue
        seen.add(tx_id)
        wanted.append((tx_id, capital, step.cost_report_change if step is not None else Decimal("0")))
    return wanted


def _spy_problems(records, calls) -> list[str]:
    got = [(r.transaction_id, r.capital, r.cost) for r in records]
    wanted = _spy_expectation(calls)
    return [] if got == wanted else [f"records (id, capital, cost) {got} != what _transfer_leg_capital and the step gave {wanted}"]


class TestBuilderRecords:
    def test_sender_alone_records_minus_market_value_and_the_cost_given_up(self, leg_capital_spy):
        """A alone (case 13): A's 10 units (cost 100) leave on d1 for B, outside the scope, at MV(10, d1) = 110.
        One record (3, A, asset, d1, capital −110, cost −100)."""
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10")
        classification = _classify([*_setup_t(), out_leg], {A}, external_paired={in_leg.id: in_leg})
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_external_outflow"}

        records = _records(_build(classification))

        assert _as_tuples(records) == [(3, A, ASSET, D1, Decimal("-110"), Decimal("-100"))]
        assert not _spy_problems(records, leg_capital_spy), _spy_problems(records, leg_capital_spy)
        assert _results(records, D0, D5) == {A: Decimal("10")}

    def test_receiver_alone_records_plus_market_value_and_the_cost_it_brings(self, leg_capital_spy):
        """B alone: the 10 units arrive on d3 carrying 10 EUR a unit (cost +100), at MV(10, d3) = 130.
        One record (4, B, asset, d3, capital +130, cost +100) → B's period result −30."""
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10", cost_basis_override="10")
        classification = _classify([in_leg], {B}, external_paired={out_leg.id: out_leg})
        assert _classifications(classification) == {4: "linked_external_inflow"}

        records = _records(_build(classification))

        assert _as_tuples(records) == [(4, B, ASSET, D3, Decimal("130"), Decimal("100"))]
        assert not _spy_problems(records, leg_capital_spy), _spy_problems(records, leg_capital_spy)
        assert _results(records, D0, D5) == {B: Decimal("-30")}

    def test_an_internal_pair_gives_no_record(self, leg_capital_spy):
        """A and B both in scope (case 4a): the pair is linked_internal, step 3b moves the capital, no record."""
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D2, qty="10")
        classification = _classify([*_setup_t(), out_leg, in_leg], {A, B})
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}

        records = _records(_build(classification))

        assert records == []
        assert _spy_expectation(leg_capital_spy) == [], "precondition: _transfer_leg_capital values no leg of an internal pair"

    def test_orphan_legs_out_and_in_are_recorded_in_replay_order(self, leg_capital_spy):
        """Setup T in A; an orphan TRANSFER +5 arrives at B on d1 (id 8, no cost: cost step 0), A's 10 units leave by an
        orphan TRANSFER on d2 (id 3). Replay order is by date: id 8 (d1) before id 3 (d2)."""
        orphan_out = _tx(id=3, broker_id=A, type="TRANSFER", dt=D2, currency=None, quantity="-10", asset_id=ASSET)
        orphan_in = _tx(id=8, broker_id=B, type="TRANSFER", dt=D1, currency=None, quantity="5", asset_id=ASSET)
        classification = _classify([*_setup_t(), orphan_out, orphan_in], {A, B})
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "normal", 8: "normal"}

        records = _records(_build(classification))

        assert [(r.transaction_id, r.broker_id, r.date, r.capital) for r in records] == [(8, B, D1, Decimal("55")), (3, A, D2, Decimal("-120"))]
        assert records[1].cost == Decimal("-100")
        assert not _spy_problems(records, leg_capital_spy), _spy_problems(records, leg_capital_spy)

    def test_an_unpriced_leg_moves_at_its_cost_and_gives_zero(self, leg_capital_spy):
        """J-17 (case 5d): asset 200 has no price before d4; 10 units arrive at A on d0 by an orphan TRANSFER at 10 EUR a
        unit: capital = the cost the leg moves = 100, cost 100 → result 0, broker present."""
        orphan_in = _tx(id=1, broker_id=A, type="TRANSFER", dt=D0, currency=None, quantity="10", asset_id=UNPRICED_ASSET, cost_basis_override="10", cost_basis_currency="EUR")
        classification = _classify([orphan_in], {A})

        records = _records(_build(classification, price_map={UNPRICED_ASSET: [(D4, Decimal("15"), "EUR")]}))

        assert _as_tuples(records) == [(1, A, UNPRICED_ASSET, D0, Decimal("100"), Decimal("100"))]
        assert not _spy_problems(records, leg_capital_spy), _spy_problems(records, leg_capital_spy)
        assert _results(records, None, D5) == {A: Decimal("0")}

    def test_split_linked_transfer_and_priced_adjustment_give_no_record(self, leg_capital_spy):
        """A TRANSFER linked to a split (its id in split_linked_tx_ids) moves no capital; a priced in-kind ADJUSTMENT-in is
        capital at cost (``_is_capital_adjustment``), not a market-value transfer: neither is recorded."""
        split_leg = _tx(id=5, broker_id=A, type="TRANSFER", dt=D2, currency=None, quantity="10", asset_id=ASSET)
        adjustment = _tx(id=6, broker_id=A, type="ADJUSTMENT", dt=D3, currency=None, quantity="4", asset_id=ASSET, cost_basis_override="12", cost_basis_currency="EUR")
        classification = _classify([*_setup_t(), split_leg, adjustment], {A})

        records = _records(_build(classification, split_linked_tx_ids={5}))

        assert records == []
        assert _spy_expectation(leg_capital_spy) == [], "precondition: _transfer_leg_capital values neither row"

    def test_a_leg_before_date_from_is_recorded(self, leg_capital_spy):
        """A alone, date_from d3: the leg of d1 is replayed before the emitted states and still recorded (the period
        function, not the builder, picks the window)."""
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10")
        classification = _classify([*_setup_t(), out_leg], {A}, external_paired={in_leg.id: in_leg})

        result = _build(classification, date_from=D3)
        records = _records(result)

        assert [s.date for s in result.daily_states][0] == D3, "precondition: the states start at date_from"
        assert _as_tuples(records) == [(3, A, ASSET, D1, Decimal("-110"), Decimal("-100"))]
        assert not _spy_problems(records, leg_capital_spy), _spy_problems(records, leg_capital_spy)
        assert _results(records, D3, D5) == {}

    def test_the_owners_share_scales_capital_and_cost(self, leg_capital_spy):
        """A owned at 50 %: the leg moves 5 units, MV(5, d1) = 55, cost 50 (half the pool)."""
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10")
        classification = _classify([*_setup_t(), out_leg], {A}, shares={A: "0.5"}, external_paired={in_leg.id: in_leg})

        records = _records(_build(classification))

        assert [(r.transaction_id, r.broker_id, r.capital, r.cost) for r in records] == [(3, A, Decimal("-55.0"), Decimal("-50.0"))]
        assert not _spy_problems(records, leg_capital_spy), _spy_problems(records, leg_capital_spy)


class TestSpyGuard:
    """Green before and after the cure: the numbers the records must carry are today's ``_transfer_leg_capital``."""

    def test_todays_leg_capital_and_step_for_the_sender_alone(self, leg_capital_spy):
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10")
        classification = _classify([*_setup_t(), out_leg], {A}, external_paired={in_leg.id: in_leg})
        _build(classification)
        assert _spy_expectation(leg_capital_spy) == [(3, Decimal("-110"), Decimal("-100"))]
