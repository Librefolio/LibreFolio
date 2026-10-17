"""J1 — one replay, the same rules every day.

``DailyStateBuilder`` replays every movement from ``min(date_from, first movement)`` to ``date_to`` with
the same rules every day, and emits the states from ``date_from`` on. Before J1 the days before the
emitted window ran in a separate, accounting-only *pre-frame* with rules of its own: a SELL's whole
proceeds into the capital pool K (no split of the realized gain into the returns pool R), a day's pool
rules in loading order (the frame applies additions, then reductions, then the rest) and no end-of-day
clamp of the pools. A run whose ``date_from`` falls after the first movement therefore started from pools
the run from the first movement never had.

- ``TestWindowEqualsFullReplay`` — the invariant. For hand-built ledgers with movements before ``D``, a
  builder with ``date_from=D`` emits, for every day >= D, states equal field by field to those of a
  builder from the first movement: every ``DailyPortfolioState`` field, ``broker_contributions``,
  ``cash_from_contributed_capital`` / ``cash_from_generated_returns``, ``unrealized_by_currency``, P&L
  candles and acquisition funding included (both computed). ``realized_sales``, ``position_states_start``
  (the full run given ``period_start=D``), ``position_states_end``, ``end_state`` and ``missing_fx`` are
  equal too. Each ledger runs twice: ``D`` a quiet day, and ``D`` a day with a movement.
- ``TestExactPoolsBeforeDateFrom`` — the exact rule where the pre-frame approximated, in numbers.
- ``TestCleanDaysShareNoContainer`` — a day nothing changes on carries the previous state with every dict
  and set copied: mutating one day's container never changes another day's.
- ``TestApplyPoolRule`` — ``DailyStateBuilder._apply_pool_rule``, the K/R/W rule of one movement that is
  not a position reduction, as a pure function.

On HEAD f32a04f46 (the pre-frame still there): ``TestWindowEqualsFullReplay`` is red for the SELL, the
same-day DEPOSIT+BUY after withdrawn returns and the overdraft BUY before D, green for the others (the
pre-frame applied the frame's rule to income, fees, withdrawals, linked cash legs and foreign cash
revaluation); ``TestExactPoolsBeforeDateFrom`` red; ``TestCleanDaysShareNoContainer`` green (a parity
pin); ``TestApplyPoolRule`` red (the method does not exist).

Notation: target EUR; brokers A = 10, B = 20; X = 100 a EUR stock, Y = 200 a USD stock; D0 = 2025-01-01
... D7 = 2025-01-08. Rates are exact-day ``("USD", "EUR", day)`` entries.

Pure tests — no DB, no server. Helpers are copies of test_broker_internal_flows.py (this directory has
no cross-test-module imports).
"""

import dataclasses
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, DailyPortfolioState
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X = 100
Y = 200

D0 = date(2025, 1, 1)
D1 = date(2025, 1, 2)
D2 = date(2025, 1, 3)
D3 = date(2025, 1, 4)
D4 = date(2025, 1, 5)
D5 = date(2025, 1, 6)
D6 = date(2025, 1, 7)
D7 = date(2025, 1, 8)

# =============================================================================
# HELPERS — copies of test_broker_internal_flows.py
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
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _ctxn(tx: MagicMock, classification: str = "normal", share: str = "1") -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal(share))


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
    """DailyStateBuilder kwargs: defaults, overrides, then the mark series, average costs and native cash
    computed once, so the two builders of a comparison get the very same inputs."""
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
        "date_from": D0,
        "date_to": D0,
    }
    kwargs.update(overrides)
    kwargs.setdefault("mark_series", _mark_series_from(kwargs["classified_txs"], kwargs["price_map"], kwargs["asset_currencies"]))
    kwargs.setdefault(
        "average_costs",
        engine_average_costs(kwargs["classified_txs"], asset_currencies=kwargs["asset_currencies"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]),
    )
    kwargs.setdefault("native_cash", engine_native_cash(kwargs["classified_txs"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]))
    return kwargs


def _classify(txs, scope):
    """Run the real classifier, transactions in loading order (date, id), share 1."""
    classifier = ScopeAwareTransactionClassifier(
        scope_broker_ids=set(scope),
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares=dict.fromkeys(scope, Decimal("1")),
    )
    return classifier.classify()


def _ledger(txs, scope, *, date_to, price_map=None, fx_rate_map=None, asset_currencies=None) -> dict:
    """Builder overrides of a classified ledger (``date_from`` is the comparison's to set); every asset is a "Stock"."""
    classification = _classify(txs, scope)
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


def _usd_rates(rates: dict[date, str]) -> dict[tuple[str, str, date], Decimal]:
    """USD->EUR on the given days only (the map is exact-day: any other day has no rate)."""
    return {("USD", "EUR", day): Decimal(rate) for day, rate in rates.items()}


def _calendar(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


# =============================================================================
# LEDGERS — each returns the builder overrides; every one has movements before both of its D
# =============================================================================


def _ledger_sell_before_d() -> dict:
    """A deposits 1000 on D0, buys 10 X for 1000 on D1, sells 5 for 700 on D2 (cost 500, gain 200),
    buys 2 X for 300 on D5. X closes 100 / 140 / 150 on D0 / D2 / D4."""
    txs = [
        _tx(id=1, dt=D0, amount="1000"),
        _tx(id=2, type="BUY", dt=D1, amount="-1000", quantity="10", asset_id=X),
        _tx(id=3, type="SELL", dt=D2, amount="700", quantity="-5", asset_id=X),
        _tx(id=4, type="BUY", dt=D5, amount="-300", quantity="2", asset_id=X),
    ]
    return _ledger(txs, {A}, date_to=D6, price_map=_prices(X, "EUR", {D0: "100", D2: "140", D4: "150"}))


def _ledger_income_fee_withdrawal_before_d() -> dict:
    """A deposits 1000 on D0, buys 5 X for 500 on D1, gets a DIVIDEND of 80 on X and pays a FEE of 30 on
    D2, withdraws 520 on D3 (500 of capital, 20 of returns into the withdrawn pool), deposits 100 on D5
    (20 restored to the returns, 80 to capital). X closes 100 / 110 on D1 / D4."""
    txs = [
        _tx(id=1, dt=D0, amount="1000"),
        _tx(id=2, type="BUY", dt=D1, amount="-500", quantity="5", asset_id=X),
        _tx(id=3, type="DIVIDEND", dt=D2, amount="80", asset_id=X),
        _tx(id=4, type="FEE", dt=D2, amount="-30"),
        _tx(id=5, type="WITHDRAWAL", dt=D3, amount="-520"),
        _tx(id=6, dt=D5, amount="100"),
    ]
    return _ledger(txs, {A}, date_to=D6, price_map=_prices(X, "EUR", {D1: "100", D4: "110"}))


def _ledger_linked_cash_transfer_arriving_before_d() -> dict:
    """A deposits 1000 on D0 and earns 100 of INTEREST on D1; 400 leave A on D2 and reach B on D3 (a linked
    CASH_TRANSFER, in transit on D2); B buys 3 X for 300 on D5. X closes 100 on D5."""
    txs = [
        _tx(id=1, dt=D0, amount="1000"),
        _tx(id=2, type="INTEREST", dt=D1, amount="100"),
        _tx(id=3, type="CASH_TRANSFER", dt=D2, amount="-400", related_id=4),
        _tx(id=4, broker_id=B, type="CASH_TRANSFER", dt=D3, amount="400", related_id=3),
        _tx(id=5, broker_id=B, type="BUY", dt=D5, amount="-300", quantity="3", asset_id=X),
    ]
    return _ledger(txs, {A, B}, date_to=D6, price_map=_prices(X, "EUR", {D5: "100"}))


def _ledger_foreign_cash_rate_change_before_d() -> dict:
    """A deposits 1000 USD on D0 (0.90), the dollar moves to 0.95 on D1 and 1.00 on D3; A buys 5 Y for
    500 USD on D2 and 2 more for 200 USD on D5 (0.98). Y closes 100 / 104 USD on D2 / D4."""
    txs = [
        _tx(id=1, dt=D0, amount="1000", currency="USD"),
        _tx(id=2, type="BUY", dt=D2, amount="-500", currency="USD", quantity="5", asset_id=Y),
        _tx(id=3, type="BUY", dt=D5, amount="-200", currency="USD", quantity="2", asset_id=Y),
    ]
    rates = _usd_rates({D0: "0.90", D1: "0.95", D2: "0.95", D3: "1.00", D4: "1.00", D5: "0.98", D6: "0.98"})
    return _ledger(txs, {A}, date_to=D6, price_map=_prices(Y, "USD", {D2: "100", D4: "104"}), fx_rate_map=rates, asset_currencies={Y: "USD"})


def _ledger_in_transit_straddling_d() -> dict:
    """A deposits 600 and buys 10 X for 100 on D0; the 10 X leave A on D1 and reach B on D5 (in transit
    D1-D4); 200 of cash leave A on D2 and reach B on D6 (in transit D2-D5). X closes 10 ... 16 on D0-D6."""
    txs = [
        _tx(id=1, dt=D0, amount="600"),
        _tx(id=2, type="BUY", dt=D0, amount="-100", quantity="10", asset_id=X),
        _tx(id=3, type="TRANSFER", dt=D1, currency=None, quantity="-10", asset_id=X, related_id=4),
        _tx(id=4, broker_id=B, type="TRANSFER", dt=D5, currency=None, quantity="10", asset_id=X, related_id=3),
        _tx(id=5, type="CASH_TRANSFER", dt=D2, amount="-200", related_id=6),
        _tx(id=6, broker_id=B, type="CASH_TRANSFER", dt=D6, amount="200", related_id=5),
    ]
    closes = {day: str(10 + offset) for offset, day in enumerate(_calendar(D0, D6))}
    return _ledger(txs, {A, B}, date_to=D6, price_map=_prices(X, "EUR", closes))


def _ledger_same_day_deposit_and_buy_after_withdrawn_returns() -> dict:
    """A deposits 1000 on D0, earns 100 of INTEREST on D1, withdraws 1050 on D2 (all the capital, then 50
    of returns into the withdrawn pool); on D3 it deposits 500 and buys 4 X for 400. The day's rules run
    additions first: the BUY draws the 50 of returns, then the DEPOSIT restores the 50 withdrawn — K 100,
    R 50. The pre-frame ran them in loading order (DEPOSIT, then BUY): K 150, R 0. X closes 100 on D3."""
    txs = [
        _tx(id=1, dt=D0, amount="1000"),
        _tx(id=2, type="INTEREST", dt=D1, amount="100"),
        _tx(id=3, type="WITHDRAWAL", dt=D2, amount="-1050"),
        _tx(id=4, dt=D3, amount="500"),
        _tx(id=5, type="BUY", dt=D3, amount="-400", quantity="4", asset_id=X),
        _tx(id=6, type="INTEREST", dt=D5, amount="10"),
    ]
    return _ledger(txs, {A}, date_to=D6, price_map=_prices(X, "EUR", {D3: "100"}))


def _ledger_overdraft_buy_before_d() -> dict:
    """A deposits 500 on D0 and buys 8 X for 800 on D1 (cash -300, K -300 clamped to 0 at the day's end),
    deposits 300 on D2 (K 300; the pre-frame, which never clamped, had K 0), sells the 8 X for 1000 on D5.
    X closes 100 / 125 on D1 / D5."""
    txs = [
        _tx(id=1, dt=D0, amount="500"),
        _tx(id=2, type="BUY", dt=D1, amount="-800", quantity="8", asset_id=X),
        _tx(id=3, dt=D2, amount="300"),
        _tx(id=4, type="SELL", dt=D5, amount="1000", quantity="-8", asset_id=X),
    ]
    return _ledger(txs, {A}, date_to=D6, price_map=_prices(X, "EUR", {D1: "100", D5: "125"}))


# (ledger, D) pairs: D4 is quiet in every ledger, D5 carries a movement in every ledger.
_REPLAY_CASES = [
    pytest.param(ledger, day, id=f"{name}-{label}")
    for name, ledger in (
        ("sell_before_d", _ledger_sell_before_d),
        ("income_fee_withdrawal_before_d", _ledger_income_fee_withdrawal_before_d),
        ("linked_cash_transfer_arriving_before_d", _ledger_linked_cash_transfer_arriving_before_d),
        ("foreign_cash_rate_change_before_d", _ledger_foreign_cash_rate_change_before_d),
        ("in_transit_straddling_d", _ledger_in_transit_straddling_d),
        ("same_day_deposit_and_buy_after_withdrawn_returns", _ledger_same_day_deposit_and_buy_after_withdrawn_returns),
        ("overdraft_buy_before_d", _ledger_overdraft_buy_before_d),
    )
    for label, day in (("quiet_d", D4), ("movement_on_d", D5))
]

# =============================================================================
# COMPARISON — field by field, Decimals byte for byte
# =============================================================================


def _first_difference(a, b, path: str) -> str | None:
    """Path and values of the first difference between two values, or None.

    Dataclasses field by field, dicts by key set then value, sequences by length then item, Decimals
    byte for byte (as_tuple), the rest (sets, dates, ...) by ==.
    """
    if a is b:
        return None
    if type(a) is not type(b):
        return f"{path}: type {type(a).__name__} != {type(b).__name__}"
    if dataclasses.is_dataclass(a):
        return _dataclass_difference(a, b, path)
    if isinstance(a, dict):
        return _dict_difference(a, b, path)
    if isinstance(a, (list, tuple)):
        return _sequence_difference(a, b, path)
    if isinstance(a, Decimal):
        return None if a.as_tuple() == b.as_tuple() else f"{path}: {a!r} != {b!r}"
    return None if a == b else f"{path}: {a!r} != {b!r}"


def _dataclass_difference(a, b, path: str) -> str | None:
    for field in dataclasses.fields(a):
        difference = _first_difference(getattr(a, field.name), getattr(b, field.name), f"{path}.{field.name}")
        if difference is not None:
            return difference
    return None


def _dict_difference(a: dict, b: dict, path: str) -> str | None:
    if set(a) != set(b):
        return f"{path}: keys only on one side: {sorted(map(repr, set(a) ^ set(b)))}"
    for key in a:
        difference = _first_difference(a[key], b[key], f"{path}[{key!r}]")
        if difference is not None:
            return difference
    return None


def _sequence_difference(a, b, path: str) -> str | None:
    if len(a) != len(b):
        return f"{path}: length {len(a)} != {len(b)}"
    for index, (left, right) in enumerate(zip(a, b, strict=True)):
        difference = _first_difference(left, right, f"{path}[{index}]")
        if difference is not None:
            return difference
    return None


def _window_and_full(ledger, day: date):
    """The run from ``date_from=day`` and the run from the first movement (``period_start=day``), same inputs."""
    kwargs = _builder_kwargs(**ledger(), compute_candles=True, compute_acquisition_funding=True)
    first_movement = min(ctxn.tx.date for ctxn in kwargs["classified_txs"])
    assert first_movement < day, "the ledger must have movements before D, or the comparison proves nothing"
    window = DailyStateBuilder(**{**kwargs, "date_from": day}).build()
    full = DailyStateBuilder(**{**kwargs, "date_from": first_movement, "period_start": day}).build()
    return window, full


def _replay_problems(window, full, day: date) -> list[str]:
    """Every day >= D compared state by state (first difference of each day), then the result's other outputs."""
    problems: list[str] = []
    window_days = [s.date for s in window.daily_states]
    if window_days != _calendar(day, window.date_to):
        problems.append(f"window emitted {window_days}, expected every day from {day} to {window.date_to}")
    full_by_day = {s.date: s for s in full.daily_states}
    for state in window.daily_states:
        reference = full_by_day.get(state.date)
        if reference is None:
            problems.append(f"{state.date}: no state in the run from the first movement")
            continue
        difference = _first_difference(state, reference, f"state<{state.date}>")
        if difference is not None:
            problems.append(difference)
    for name in ("realized_sales", "position_states_start", "position_states_end", "end_state", "missing_fx"):
        difference = _first_difference(getattr(window, name), getattr(full, name), name)
        if difference is not None:
            problems.append(difference)
    return problems


# =============================================================================
# THE INVARIANT
# =============================================================================


class TestWindowEqualsFullReplay:
    """A run from ``date_from=D`` is the run from the first movement, seen from D."""

    @pytest.mark.parametrize(("ledger", "day"), _REPLAY_CASES)
    def test_states_from_d_and_outputs_equal_the_run_from_the_first_movement(self, ledger, day):
        window, full = _window_and_full(ledger, day)

        problems = _replay_problems(window, full, day)

        assert not problems, "\n".join(problems)

    def test_the_comparison_is_not_vacuous(self):
        """The two runs differ before D: the run from the first movement emits those days, the window does not."""
        window, full = _window_and_full(_ledger_sell_before_d, D4)

        assert [s.date for s in full.daily_states][:4] == [D0, D1, D2, D3]
        assert window.daily_states[0].date == D4
        assert window.position_states_start_date == full.position_states_start_date == D4


# =============================================================================
# THE EXACT RULE WHERE THE PRE-FRAME APPROXIMATED
# =============================================================================


def _state(result, day: date) -> DailyPortfolioState:
    return next(s for s in result.daily_states if s.date == day)


class TestExactPoolsBeforeDateFrom:
    """J1: the pre-frame's approximations are gone. The pools a window starts from are the exact ones."""

    def test_a_sell_before_d_splits_its_proceeds_into_cost_and_gain(self):
        """The SELL on D2 returns its cost (500) to K and its gain (200) to R, as on any day. The pre-frame put
        all 700 in K: on D4 contributed 700 / generated 0, and the D5 BUY of 300 all new capital."""
        window, _ = _window_and_full(_ledger_sell_before_d, D4)

        first = _state(window, D4)
        assert (first.cash_value, first.cash_from_contributed_capital, first.cash_from_generated_returns) == (Decimal("700"), Decimal("500"), Decimal("200"))
        funding = _state(window, D5).acquisition_funding
        assert funding is not None
        assert (funding.from_new_capital, funding.from_reinvested) == (Decimal("100"), Decimal("200")), "the D5 BUY spends the 200 of returns first"
        assert window.end_state.capital_pool == {A: Decimal("400")}
        assert window.end_state.returns_pool == {A: Decimal("0")}

    def test_a_same_day_deposit_and_buy_before_d_run_additions_first(self):
        """D3: the BUY draws the 50 of returns before the DEPOSIT restores the 50 withdrawn (K 100, R 50); the
        pre-frame took them in loading order (K 150, R 0): on D4 contributed 150 / generated 0."""
        window, _ = _window_and_full(_ledger_same_day_deposit_and_buy_after_withdrawn_returns, D4)

        first = _state(window, D4)
        assert (first.cash_value, first.cash_from_contributed_capital, first.cash_from_generated_returns) == (Decimal("150"), Decimal("100"), Decimal("50"))

    def test_an_overdraft_buy_before_d_is_clamped_at_its_days_end(self):
        """D1: the BUY of 800 against K 500 leaves K -300, clamped to 0 at the end of the day; the D2 deposit makes
        it 300. The pre-frame never clamped (K 0), so after the D5 SELL (cost 800, gain 200) its pools were
        K 800, R 200 instead of K 1100, R 200."""
        window, _ = _window_and_full(_ledger_overdraft_buy_before_d, D4)

        assert window.end_state.capital_pool == {A: Decimal("1100")}
        assert window.end_state.returns_pool == {A: Decimal("200")}


# =============================================================================
# CLEAN DAYS — carried, never shared
# =============================================================================


class TestCleanDaysShareNoContainer:
    """A day nothing changes on carries the previous state; its dicts and sets are copies, never the same
    object as another day's. A parity pin: HEAD copied them already, J1 must keep doing it."""

    def _quiet_result(self, monkeypatch):
        """A deposits 1000 and buys 5 X for 500 on D0, X closes 100 on D0 only; D1-D3 change nothing (the
        price turns stale only on D8). Returns the result and the days a state was computed on."""
        computed: list[date] = []
        original = DailyStateBuilder._compute_in_transit

        def counting(self, dt, missing_fx, it_by_broker=None):
            computed.append(dt)
            return original(self, dt, missing_fx, it_by_broker)

        monkeypatch.setattr(DailyStateBuilder, "_compute_in_transit", counting)
        txs = [_tx(id=1, dt=D0, amount="1000"), _tx(id=2, type="BUY", dt=D0, amount="-500", quantity="5", asset_id=X)]
        result = DailyStateBuilder(**_builder_kwargs(**_ledger(txs, {A}, date_to=D3, price_map=_prices(X, "EUR", {D0: "100"})))).build()
        return result, computed

    def test_quiet_days_are_carried(self, monkeypatch):
        """Keeps the test below from passing vacuously: D1-D3 must take the carried path."""
        result, computed = self._quiet_result(monkeypatch)

        assert [s.date for s in result.daily_states] == [D0, D1, D2, D3]
        assert computed == [D0], f"only D0 is computed, D1-D3 carry it; computed on {computed}"

    def test_mutating_a_days_container_never_changes_another_days(self, monkeypatch):
        result, _ = self._quiet_result(monkeypatch)
        states = {s.date: s for s in result.daily_states}
        containers = [field.name for field in dataclasses.fields(DailyPortfolioState) if isinstance(getattr(states[D0], field.name), (dict, set))]
        assert {"by_type", "missing_price_asset_ids", "broker_contributions"} <= set(containers), containers

        problems: list[str] = []
        for left_day, right_day in ((D0, D1), (D1, D2), (D2, D1), (D2, D3)):
            for name in containers:
                left, right = getattr(states[left_day], name), getattr(states[right_day], name)
                if left is right:
                    problems.append(f"{name}: {left_day} and {right_day} share one object")
                    continue
                before = type(right)(right)
                if isinstance(left, set):
                    left.add(-1)
                else:
                    left[-1] = None
                if right != before:
                    problems.append(f"{name}: mutating {left_day}'s changed {right_day}'s")
        assert not problems, "\n".join(problems)


# =============================================================================
# _apply_pool_rule — the K/R/W rule of one movement, pure
# =============================================================================


def _pools(a_capital: str, a_returns: str) -> tuple[defaultdict, defaultdict]:
    """K and R as the replay holds them (defaultdicts), with broker B as a bystander the rule must not touch."""
    return defaultdict(Decimal, {A: Decimal(a_capital), B: Decimal("7")}), defaultdict(Decimal, {A: Decimal(a_returns), B: Decimal("3")})


def _apply(tx_type: str, signed_amount: str, *, capital: str, returns: str, withdrawn: str = "0", classification: str = "normal", asset_id: int | None = None):
    """Run the rule on broker A's movement; ``amount`` is |signed_amount|, as the replay passes it."""
    capital_pool, returns_pool = _pools(capital, returns)
    ctxn = _ctxn(_tx(type=tx_type, amount=signed_amount, asset_id=asset_id), classification=classification)
    withdrawn_after, from_k, from_r = DailyStateBuilder._apply_pool_rule(ctxn, abs(Decimal(signed_amount)), capital_pool, returns_pool, Decimal(withdrawn))
    assert (capital_pool[B], returns_pool[B]) == (Decimal("7"), Decimal("3")), "another broker's pools moved"
    return capital_pool[A], returns_pool[A], withdrawn_after, from_k, from_r


def _d(*values: str) -> tuple[Decimal, ...]:
    return tuple(Decimal(value) for value in values)


class TestApplyPoolRule:
    """``_apply_pool_rule(ctxn, amount, K, R, withdrawn) -> (withdrawn, buy_from_k, buy_from_r)``; ``amount`` is the
    movement's absolute value in the target currency, the sign is read from ``tx.amount``."""

    def test_a_deposit_restores_withdrawn_returns_first_then_feeds_capital(self):
        assert _apply("DEPOSIT", "100", capital="0", returns="0", withdrawn="30") == _d("70", "30", "0", "0", "0")

    def test_a_deposit_smaller_than_the_withdrawn_returns_restores_only_returns(self):
        assert _apply("DEPOSIT", "100", capital="5", returns="0", withdrawn="150") == _d("5", "100", "50", "0", "0")

    def test_a_withdrawal_takes_capital_first_then_returns_into_the_withdrawn_pool(self):
        assert _apply("WITHDRAWAL", "-70", capital="50", returns="40", withdrawn="5") == _d("0", "20", "25", "0", "0")

    def test_a_withdrawal_beyond_both_pools_empties_them(self):
        """The 10 neither pool holds comes out of none: K 0, R 0, withdrawn += the 40 of returns."""
        assert _apply("WITHDRAWAL", "-100", capital="50", returns="40") == _d("0", "0", "40", "0", "0")

    @pytest.mark.parametrize("tx_type", ["DIVIDEND", "INTEREST"])
    @pytest.mark.parametrize(("signed_amount", "returns_after"), [("50", "60"), ("-30", "-20")])
    def test_income_feeds_returns_with_its_sign(self, tx_type, signed_amount, returns_after):
        """A negative correction lowers R, below zero if it must: the clamp is the day's, not the rule's."""
        assert _apply(tx_type, signed_amount, capital="100", returns="10", asset_id=X) == _d("100", returns_after, "0", "0", "0")

    @pytest.mark.parametrize("tx_type", ["FEE", "TAX"])
    def test_a_fee_or_tax_comes_out_of_returns_then_capital(self, tx_type):
        assert _apply(tx_type, "-50", capital="100", returns="20") == _d("70", "0", "0", "0", "0")

    @pytest.mark.parametrize("tx_type", ["FEE", "TAX"])
    def test_a_fee_or_tax_within_the_returns_leaves_capital_alone(self, tx_type):
        assert _apply(tx_type, "-30", capital="100", returns="100") == _d("100", "70", "0", "0", "0")

    def test_a_buy_spends_returns_first_and_returns_the_split(self):
        assert _apply("BUY", "-50", capital="100", returns="30", withdrawn="9", asset_id=X) == _d("80", "0", "9", "20", "30")

    def test_a_buy_covered_by_the_returns_draws_no_capital(self):
        assert _apply("BUY", "-40", capital="100", returns="100", asset_id=X) == _d("100", "60", "0", "0", "40")

    @pytest.mark.parametrize("tx_type", ["CASH_TRANSFER", "FX_CONVERSION"])
    def test_a_linked_internal_cash_departure_leaves_returns_first_then_capital(self, tx_type):
        assert _apply(tx_type, "-60", capital="100", returns="40", classification="linked_internal") == _d("80", "0", "0", "0", "0")

    @pytest.mark.parametrize("tx_type", ["CASH_TRANSFER", "FX_CONVERSION"])
    def test_a_linked_internal_cash_arrival_lands_in_capital(self, tx_type):
        """All of it into K: the departure's K/R split does not travel with it (J2 carries the split)."""
        assert _apply(tx_type, "60", capital="100", returns="40", classification="linked_internal") == _d("160", "40", "0", "0", "0")

    @pytest.mark.parametrize("tx_type", ["CASH_TRANSFER", "FX_CONVERSION"])
    @pytest.mark.parametrize("classification", ["normal", "linked_external_inflow", "linked_external_outflow"])
    @pytest.mark.parametrize("signed_amount", ["60", "-60"])
    def test_a_cash_transfer_that_is_not_linked_internal_moves_no_pool(self, tx_type, classification, signed_amount):
        """An orphan leg, or one whose partner is outside the scope, is an external cash flow: no pool moves."""
        assert _apply(tx_type, signed_amount, capital="100", returns="40", withdrawn="5", classification=classification) == _d("100", "40", "5", "0", "0")
