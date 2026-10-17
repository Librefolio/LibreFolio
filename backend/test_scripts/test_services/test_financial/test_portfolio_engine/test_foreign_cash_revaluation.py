"""Tests for lot 41 step F — foreign cash revalued on every rate-change day.

The defect (portfolio_engine before step F, @ 251067435). The builder booked each cash
movement at the rate of its own date and never looked at it again: 1000 USD deposited at
0.90 stayed 900 EUR of cash however the dollar moved, while the same dollars once spent on
a security were valued at the day's rate. Foreign cash showed no exchange-rate gain or
loss, and the first purchase after a rate move left a negative cash balance behind (B1).

The approved fix (spec §2, D-beta). The builder takes ``native_cash`` (a ``NativeCash``,
required). On every rate-change day of the replay — one replay from the first movement, the
days before ``date_from`` included, states emitted from ``date_from`` on (J1) —
after that day's cash deltas and before its transaction pool rules, each broker holding
foreign cash takes ``fxr = native_cash.value_at(day)[b] - cumulative_cash_by_broker[b]``:
the cash moves by ``fxr`` (aggregate and broker alike), the returns pool R takes it, and a
negative R is covered by the capital pool K (the FEE/TAX rule). Capital — the cumulative
external cash flow — never moves because of FX. An EUR-only portfolio keeps the path it
had before step F.

Notation: target EUR; brokers A = 10 and B = 20; asset X = 100 quoted in USD;
D0 = 2025-01-01 ... D5 = 2025-01-06. Rates are exact-day ``("USD", "EUR", day)`` entries
of ``fx_rate_map``: a day that is not listed has no rate. P is ``total_pnl``, capital the
cumulative external cash flow, contributed / generated the cash split
(``cash_from_contributed_capital`` / ``cash_from_generated_returns``), K / R the end pools
of ``result.end_state``. B1-B12, B3w and B4v are the scenarios of the spec table; each
test's docstring also quotes, as "Before F", the value the engine gave before the fix:
what a regression would bring back. The G1a invariant (broker lines add up to the
aggregate, ``P_b = V_b - C_b``) is asserted on every day of every run.

Pure tests — no DB, no server. The helpers are copies of test_eur_cash_exponents.py and
test_broker_internal_flows.py (this directory has no cross-test-module imports);
``native_cash`` is built from the builder's own rate map by ``engine_native_cash``.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, DailyPortfolioState, PortfolioCalculationResult
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X = 100

D0 = date(2025, 1, 1)
D1 = date(2025, 1, 2)
D2 = date(2025, 1, 3)
D3 = date(2025, 1, 4)
D4 = date(2025, 1, 5)
D5 = date(2025, 1, 6)
DAYS = (D0, D1, D2, D3, D4, D5)

# =============================================================================
# HELPERS — copies of test_eur_cash_exponents.py:51-160 (plus native_cash)
# =============================================================================


def _tx(
    *,
    id: int = 1,
    broker_id: int = 10,
    type: str = "DEPOSIT",
    dt: str | date = "2025-01-01",
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
    tx.date = dt if isinstance(dt, date) else date.fromisoformat(dt)
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = related_id
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override else None
    tx.cost_basis_currency = cost_basis_currency
    return tx


def _ctxn(
    tx: MagicMock,
    classification: str = "normal",
    share: str = "1",
    paired: MagicMock | None = None,
) -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal(share), paired_tx=paired)


def _mark_series_from(classified_txs, price_map, asset_currencies, quote_base_map=None, split_linked_tx_ids=None):
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
            split_linked_tx_ids=split_linked_tx_ids or set(),
            asset_currency=(asset_currencies or {}).get(aid, "EUR"),
            quote_base_quantity=(quote_base_map or {}).get(aid) or 1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _builder_kwargs(**overrides) -> dict:
    """The kwargs ``_builder`` passes to DailyStateBuilder: defaults, overrides, then the
    mark series, average costs and native cash computed once."""
    defaults = {
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
        "date_from": date(2025, 1, 1),
        "date_to": date(2025, 1, 1),
    }
    defaults.update(overrides)
    if "mark_series" not in defaults:
        defaults["mark_series"] = _mark_series_from(
            defaults["classified_txs"],
            defaults["price_map"],
            defaults["asset_currencies"],
            defaults["quote_base_map"],
            defaults.get("split_linked_tx_ids"),
        )
    if "average_costs" not in defaults:
        defaults["average_costs"] = engine_average_costs(
            defaults["classified_txs"],
            asset_currencies=defaults["asset_currencies"],
            target_currency=defaults["target_currency"],
            fx_rate_map=defaults["fx_rate_map"],
            split_linked_tx_ids=defaults.get("split_linked_tx_ids"),
            date_to=defaults["date_to"],
        )
    if "native_cash" not in defaults:
        defaults["native_cash"] = engine_native_cash(
            defaults["classified_txs"],
            target_currency=defaults["target_currency"],
            fx_rate_map=defaults["fx_rate_map"],
            date_to=defaults["date_to"],
        )
    return defaults


def _builder(**overrides) -> DailyStateBuilder:
    """Create a DailyStateBuilder with sensible defaults, overriding any kwarg."""
    return DailyStateBuilder(**_builder_kwargs(**overrides))


def _build(**overrides):
    return _builder(**overrides).build()


# =============================================================================
# HELPERS — copies of test_broker_internal_flows.py:184-315 (assets may be USD)
# =============================================================================


def _assert_broker_contribution_invariant(state: DailyPortfolioState) -> None:
    """The G1a mandatory invariant (plan §4.2): broker slices are built from the SAME
    Decimal components as the scope aggregate, so summing them reproduces the
    aggregate exactly — never a residual/plug line computed after the fact.
    """
    zero = Decimal("0")
    nav_sum = sum((bc.nav_contribution for bc in state.broker_contributions.values()), zero)
    capital_sum = sum((bc.capital_contribution for bc in state.broker_contributions.values()), zero)
    pnl_sum = sum((bc.pnl_contribution for bc in state.broker_contributions.values()), zero)
    assert nav_sum == state.nav_value, f"{state.date}: sum(nav_contribution)={nav_sum} != nav_value={state.nav_value}"
    assert capital_sum == state.cumulative_external_cash_flow, f"{state.date}: sum(capital_contribution)={capital_sum} != cumulative_external_cash_flow={state.cumulative_external_cash_flow}"
    assert pnl_sum == state.total_pnl, f"{state.date}: sum(pnl_contribution)={pnl_sum} != total_pnl={state.total_pnl}"
    for bc in state.broker_contributions.values():
        assert bc.pnl_contribution == bc.nav_contribution - bc.capital_contribution, f"{state.date}/broker {bc.broker_id}: pnl_contribution={bc.pnl_contribution} != nav_contribution({bc.nav_contribution}) - capital_contribution({bc.capital_contribution})"


def _assert_invariant_every_day(states: list[DailyPortfolioState]) -> None:
    for s in states:
        _assert_broker_contribution_invariant(s)


def _cash_pair(
    out_id: int,
    in_id: int,
    *,
    sender: int,
    receiver: int,
    out_dt: date,
    in_dt: date,
    out_amount: str,
    in_amount: str,
    out_currency: str = "EUR",
    in_currency: str = "EUR",
    type: str = "CASH_TRANSFER",
) -> tuple[MagicMock, MagicMock]:
    """Two linked cash legs: -out_amount on the sender, +in_amount on the receiver."""
    out_leg = _tx(id=out_id, broker_id=sender, type=type, dt=out_dt, amount=f"-{out_amount}", currency=out_currency, related_id=in_id)
    in_leg = _tx(id=in_id, broker_id=receiver, type=type, dt=in_dt, amount=in_amount, currency=in_currency, related_id=out_id)
    return out_leg, in_leg


def _usd_rates(rates: dict[date, str]) -> dict[tuple[str, str, date], Decimal]:
    """USD->EUR on the given days only (the map is exact-day: any other day has no rate)."""
    return {("USD", "EUR", day): Decimal(rate) for day, rate in rates.items()}


def _classify(txs, scope, *, shares=None, external_paired=None):
    """Run the real classifier, transactions in loading order (date, id); share 1 unless given."""
    broker_shares = dict.fromkeys(scope, Decimal("1"))
    broker_shares.update({broker_id: Decimal(share) for broker_id, share in (shares or {}).items()})
    classifier = ScopeAwareTransactionClassifier(
        scope_broker_ids=set(scope),
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares=broker_shares,
    )
    return classifier.classify(external_paired=external_paired)


def _overrides(classification, *, date_to, date_from=D0, price_map=None, fx_rate_map=None, asset_currencies=None) -> dict:
    """Builder kwargs for a classified scenario; every asset is a "Stock" with no classification,
    quoted in EUR unless ``asset_currencies`` says otherwise. A ``date_from`` after the first
    transaction is a window run: one replay from the first movement, with the same rules every
    day, and the states emitted from ``date_from`` on (J1)."""
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
        "date_from": date_from,
        "date_to": date_to,
    }


# =============================================================================
# SCENARIO HELPERS
# =============================================================================


def _usd_deposit() -> MagicMock:
    """D0: broker A deposits 1000 USD."""
    return _tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="1000", currency="USD")


def _buy_x(*, id: int = 2, dt: date = D2) -> MagicMock:
    """Broker A buys 10 X for 1000 USD."""
    return _tx(id=id, broker_id=A, type="BUY", dt=dt, amount="-1000", currency="USD", quantity="10", asset_id=X)


def _x_prices(*days: date) -> dict[int, list[tuple[date, Decimal, str]]]:
    """X quoted 100 USD on the given days."""
    return {X: [(day, Decimal("100"), "USD") for day in days]}


def _deposit_only(rates: dict[date, str], *, date_to: date, date_from: date = D0, shares=None) -> dict:
    """Builder kwargs of the USD deposit alone, scope {A}, under the given USD->EUR rates."""
    classification = _classify([_usd_deposit()], {A}, shares=shares)
    return _overrides(classification, date_to=date_to, date_from=date_from, fx_rate_map=_usd_rates(rates))


def _deposit_and_withdrawal(rate_d1: str) -> dict:
    """B4 / B4v: the USD deposit, then a 500 USD withdrawal on D1; D0 rate 0.90."""
    withdrawal = _tx(id=2, broker_id=A, type="WITHDRAWAL", dt=D1, amount="-500", currency="USD")
    classification = _classify([_usd_deposit(), withdrawal], {A})
    return _overrides(classification, date_to=D1, fx_rate_map=_usd_rates({D0: "0.90", D1: rate_d1}))


def _b3_overrides(*, date_from: date = D0) -> dict:
    """B3: the USD deposit, then all of it sent from A on D1 and received at B on D5, scope {A, B}."""
    out_leg, in_leg = _cash_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D5, out_amount="1000", in_amount="1000", out_currency="USD", in_currency="USD")
    classification = _classify([_usd_deposit(), out_leg, in_leg], {A, B})
    rates = _usd_rates({D0: "0.90", D1: "0.90", D2: "0.95", D3: "1.00", D4: "1.00", D5: "1.05"})
    return _overrides(classification, date_to=D5, date_from=date_from, fx_rate_map=rates)


def _b10_overrides(*, date_from: date) -> dict:
    """B10: the USD deposit, X bought on D2 and sold on D4 at 100 USD, rates 0.90 then 0.95 from D1."""
    sell = _tx(id=3, broker_id=A, type="SELL", dt=D4, amount="1000", currency="USD", quantity="-10", asset_id=X)
    classification = _classify([_usd_deposit(), _buy_x(), sell], {A})
    rates = _usd_rates({D0: "0.90", D1: "0.95", D2: "0.95", D3: "0.95", D4: "0.95"})
    return _overrides(classification, date_to=D4, date_from=date_from, price_map=_x_prices(D2, D3, D4), fx_rate_map=rates, asset_currencies={X: "USD"})


# =============================================================================
# EXPECTATION CHECKERS — collect every mismatch, so a red shows the whole line at once
# =============================================================================

# Short names of the DailyPortfolioState fields the spec table speaks of.
_STATE_FIELDS = {
    "cash": "cash_value",
    "nav": "nav_value",
    "capital": "cumulative_external_cash_flow",
    "P": "total_pnl",
    "contributed": "cash_from_contributed_capital",
    "generated": "cash_from_generated_returns",
}
_LINE_FIELDS = ("nav_contribution", "capital_contribution", "pnl_contribution")


def _states(result: PortfolioCalculationResult) -> dict[date, DailyPortfolioState]:
    return {s.date: s for s in result.daily_states}


def _labelled(run: str, problems: list[str]) -> list[str]:
    return [f"{run} run — {problem}" for problem in problems]


def _state_problems(result: PortfolioCalculationResult, expected: dict[date, dict[str, str]]) -> list[str]:
    """``expected``: {day: {field: value}} of the scope aggregate, fields named as in ``_STATE_FIELDS``."""
    states = _states(result)
    problems: list[str] = []
    for day, fields in expected.items():
        if day not in states:
            problems.append(f"{day}: no state emitted")
            continue
        for name, value in fields.items():
            actual = getattr(states[day], _STATE_FIELDS[name])
            if actual != Decimal(value):
                problems.append(f"{day}: {_STATE_FIELDS[name]}={actual}, expected {value}")
    return problems


def _contribution_problems(state: DailyPortfolioState, broker_id: int, expected: tuple[str | None, str | None, str | None]) -> list[str]:
    """One broker line against ``(nav, capital, pnl)``; None leaves a value unchecked."""
    contribution = state.broker_contributions.get(broker_id)
    if contribution is None:
        return [f"{state.date}/broker {broker_id}: no broker contribution"]
    return [f"{state.date}/broker {broker_id}: {name}={getattr(contribution, name)}, expected {value}" for name, value in zip(_LINE_FIELDS, expected, strict=True) if value is not None and getattr(contribution, name) != Decimal(value)]


def _line_problems(result: PortfolioCalculationResult, expected: dict[date, dict[int, tuple[str | None, str | None, str | None]]]) -> list[str]:
    """``expected``: {day: {broker_id: (nav, capital, pnl)}} of the broker lines; None leaves a value unchecked."""
    states = _states(result)
    problems: list[str] = []
    for day, lines in expected.items():
        if day not in states:
            problems.append(f"{day}: no state emitted")
            continue
        for broker_id, values in lines.items():
            problems.extend(_contribution_problems(states[day], broker_id, values))
    return problems


def _pool_problems(result: PortfolioCalculationResult, *, capital: dict[int, str], returns: dict[int, str]) -> list[str]:
    """The end pools K (``capital_pool``) and R (``returns_pool``), each compared as a whole."""
    problems: list[str] = []
    for name, actual, expected in (("capital_pool", result.end_state.capital_pool, capital), ("returns_pool", result.end_state.returns_pool, returns)):
        wanted = {broker_id: Decimal(value) for broker_id, value in expected.items()}
        if actual != wanted:
            problems.append(f"end_state.{name}={actual}, expected {wanted}")
    return problems


def _broker_end_problems(result: PortfolioCalculationResult, broker_id: int, *, cash: str, capital: str, returns: str) -> list[str]:
    """One broker's end cash, K and R (``result.end_state``), in a scope with other brokers."""
    end = result.end_state
    checks = (("cumulative_cash_by_broker", end.cumulative_cash_by_broker, cash), ("capital_pool", end.capital_pool, capital), ("returns_pool", end.returns_pool, returns))
    return [f"end_state.{name}[{broker_id}]={pool.get(broker_id)}, expected {value}" for name, pool, value in checks if pool.get(broker_id) != Decimal(value)]


def _funding_problems(result: PortfolioCalculationResult, day: date, *, new: str, reinvested: str) -> list[str]:
    """The day's acquisition funding split: ``from_new_capital`` and ``from_reinvested``."""
    state = _states(result).get(day)
    if state is None:
        return [f"{day}: no state emitted"]
    funding = state.acquisition_funding
    if funding is None:
        return [f"{day}: acquisition_funding is None"]
    checks = (("from_new_capital", funding.from_new_capital, new), ("from_reinvested", funding.from_reinvested, reinvested))
    return [f"{day}: acquisition_funding.{name}={actual}, expected {value}" for name, actual, value in checks if actual != Decimal(value)]


def _emitted_problems(result: PortfolioCalculationResult, days: tuple[date, ...]) -> list[str]:
    emitted = [s.date for s in result.daily_states]
    return [] if emitted == list(days) else [f"emitted days {emitted}, expected {list(days)}"]


def _field_mismatches(window: PortfolioCalculationResult, full: PortfolioCalculationResult, days: tuple[date, ...], fields: tuple[str, ...]) -> list[str]:
    """Days on which an aggregate field of the window run differs from the full run (Decimal equality)."""
    window_states, full_states = _states(window), _states(full)
    problems: list[str] = []
    for day in days:
        if day not in window_states or day not in full_states:
            problems.append(f"{day}: emitted by the window run {day in window_states}, by the full run {day in full_states}")
            continue
        for name in fields:
            left, right = getattr(window_states[day], _STATE_FIELDS[name]), getattr(full_states[day], _STATE_FIELDS[name])
            if left != right:
                problems.append(f"{day}: {_STATE_FIELDS[name]} window={left} != full={right}")
    return problems


# _broker_line and _line_mismatches: copies of test_broker_internal_flows.py:385-401.


def _broker_line(result, day: date) -> dict[int, tuple[Decimal, Decimal, Decimal]]:
    """{broker_id: (nav, capital, pnl)} on ``day``; empty when no state was emitted that day."""
    state = {s.date: s for s in result.daily_states}.get(day)
    if state is None:
        return {}
    return {bid: (bc.nav_contribution, bc.capital_contribution, bc.pnl_contribution) for bid, bc in state.broker_contributions.items()}


def _line_mismatches(left, right, broker_id: int, days) -> list[str]:
    """Days on which a broker's (nav, capital, pnl) differ between two results."""
    problems: list[str] = []
    for day in days:
        left_line = _broker_line(left, day).get(broker_id)
        right_line = _broker_line(right, day).get(broker_id)
        if left_line != right_line:
            problems.append(f"{day}/broker {broker_id}: {left_line} != {right_line}")
    return problems


def _end_pool_mismatches(window: PortfolioCalculationResult, full: PortfolioCalculationResult) -> list[str]:
    problems: list[str] = []
    for name in ("capital_pool", "returns_pool"):
        left, right = getattr(window.end_state, name), getattr(full.end_state, name)
        if left != right:
            problems.append(f"end_state.{name} window={left} != full={right}")
    return problems


# =============================================================================
# RATE-CHANGE DAYS — one USD deposit at A, the rate moves
# =============================================================================


class TestRevaluationOnRateChangeDays:
    """The cash follows the rate on every day it changes; capital never does."""

    def test_b5_a_rate_known_only_days_later_revalues_on_that_day(self):
        """B5 — rates only on D0 (0.90) and D3 (0.95): D3 is a rate-change day, D1 and D2 are not.

        Before F: cash 900, P 0 — the cash keeps its D0 value.
        """
        result = _build(**_deposit_only({D0: "0.90", D3: "0.95"}, date_to=D3))

        problems = _state_problems(result, {D0: {"cash": "900"}, D1: {"cash": "900"}, D2: {"cash": "900"}, D3: {"cash": "950", "P": "50"}})
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_b6_a_deposit_without_a_rate_on_its_date_stays_missing(self):
        """B6 — rates only on D2 (0.90) and D3 (0.95): the D0 deposit has no rate on its own date, so
        it is a missing conversion, never a zero, and there is no counted USD cash to revalue.

        Before F: the same (non-regression).
        """
        result = _build(**_deposit_only({D2: "0.90", D3: "0.95"}, date_to=D3))

        problems = _state_problems(result, {day: {"cash": "0", "nav": "0", "capital": "0"} for day in (D0, D1, D2, D3)})
        assert not problems, "\n".join(problems)
        assert D0 in result.missing_fx.get("USD/EUR", set()), f"missing_fx={result.missing_fx}"
        _assert_invariant_every_day(result.daily_states)

    def test_b9_a_loss_covered_by_capital_then_a_gain_kept_in_returns(self):
        """B9 — rates D0 0.90, D1 0.85, D2 0.90: the D1 loss finds R empty and K covers it; the D2
        gain goes to R, so K stays reduced.

        Before F: cash 900, P 0.
        """
        result = _build(**_deposit_only({D0: "0.90", D1: "0.85", D2: "0.90"}, date_to=D2))

        problems = [
            *_state_problems(
                result,
                {
                    D1: {"cash": "850", "P": "-50", "contributed": "850", "generated": "0"},
                    D2: {"cash": "900", "P": "0", "contributed": "850", "generated": "50"},
                },
            ),
            *_pool_problems(result, capital={A: "850"}, returns={A: "50"}),
        ]
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_b12_a_gain_then_a_larger_loss_spends_the_gain_then_capital(self):
        """B12 — rates D0 0.90, D1 0.95, D2 0.85: the D1 gain goes to R; the D2 loss takes it back
        and the rest from K.

        Before F: cash 900, P 0.
        """
        result = _build(**_deposit_only({D0: "0.90", D1: "0.95", D2: "0.85"}, date_to=D2))

        problems = [
            *_state_problems(
                result,
                {
                    D1: {"cash": "950", "P": "50", "generated": "50"},
                    D2: {"cash": "850", "capital": "900", "P": "-50", "contributed": "850", "generated": "0"},
                },
            ),
            *_pool_problems(result, capital={A: "850"}, returns={A: "0"}),
        ]
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# TRANSACTIONS ON A RATE-CHANGE DAY — after the day's cash deltas, before its pool rules
# =============================================================================


class TestRevaluationAroundTransactions:
    """The revaluation lands after the day's cash deltas and before the day's pool rules."""

    def test_b1_a_purchase_after_a_rate_move_spends_the_revalued_cash(self):
        """B1 — rates D0 0.90, D1 0.90, D2 0.95; on D2 A buys 10 X (quoted 100 USD) with its 1000 USD.
        Revalued first, the cash pays the purchase exactly: 900 of new capital, 50 of FX gain.

        Before F: D2 cash -50, nav 900, P 0.
        """
        classification = _classify([_usd_deposit(), _buy_x()], {A})
        rates = _usd_rates({D0: "0.90", D1: "0.90", D2: "0.95"})
        overrides = _overrides(classification, date_to=D2, price_map=_x_prices(D2), fx_rate_map=rates, asset_currencies={X: "USD"})
        result = _build(**overrides, compute_acquisition_funding=True)

        problems = [
            *_state_problems(
                result,
                {
                    D0: {"cash": "900", "nav": "900", "P": "0"},
                    D1: {"cash": "900", "nav": "900", "P": "0"},
                    D2: {"cash": "0", "nav": "950", "capital": "900", "P": "50"},
                },
            ),
            *_funding_problems(result, D2, new="900", reinvested="50"),
        ]
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_b4_a_withdrawal_on_a_rate_rise_day_leaves_the_gain_in_cash(self):
        """B4 — on D1 A withdraws 500 USD; rates D0 0.90, D1 0.95. The 500 USD left are worth 475:
        the gain of 50 is generated cash, the withdrawal (475) comes out of capital.

        Before F: cash 425, P 0, generated 0.
        """
        result = _build(**_deposit_and_withdrawal("0.95"))

        problems = _state_problems(result, {D1: {"cash": "475", "capital": "425", "P": "50", "contributed": "425", "generated": "50"}})
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_b4v_a_withdrawal_on_a_rate_drop_day_charges_the_loss_to_capital(self):
        """B4v — B4 with the D1 rate at 0.85: the 500 USD left are worth 425, and the loss of 50,
        with no returns to absorb it, reduces K.

        Before F: cash 475, capital 475, P 0.
        """
        result = _build(**_deposit_and_withdrawal("0.85"))

        problems = [
            *_state_problems(result, {D1: {"cash": "425", "capital": "475", "P": "-50", "contributed": "425", "generated": "0"}}),
            *_pool_problems(result, capital={A: "425"}, returns={A: "0"}),
        ]
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_b8_the_revaluation_is_taken_at_the_broker_share(self):
        """B8 — the USD deposit with A held at share 0.5 (classifier shares); rates D0 0.90, D1 0.95.
        Half of 1000 USD: 450 of capital, worth 475 on D1.

        Before F: cash 450.
        """
        result = _build(**_deposit_only({D0: "0.90", D1: "0.95"}, date_to=D1, shares={A: "0.5"}))

        problems = _state_problems(result, {D1: {"cash": "475", "capital": "450", "P": "25"}})
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_b11_dollars_bought_with_euros_follow_the_rate_after_the_conversion(self):
        """B11 — scope {A, B}: on D0 A deposits 1000 EUR and B 500 EUR; on D1 A converts 900 EUR into
        1000 USD (a linked FX_CONVERSION pair at the same broker); rates D1 0.90, D2 0.95. On D2
        the dollars are worth 950: A's cash is 1050 and its gain of 50 is generated cash; B
        never moves.

        Before F: A D2 cash 1000, pnl 0.
        """
        deposits = [_tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="1000"), _tx(id=2, broker_id=B, type="DEPOSIT", dt=D0, amount="500")]
        out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=A, out_dt=D1, in_dt=D1, out_amount="900", in_amount="1000", in_currency="USD", type="FX_CONVERSION")
        classification = _classify([*deposits, out_leg, in_leg], {A, B})
        result = _build(**_overrides(classification, date_to=D2, fx_rate_map=_usd_rates({D1: "0.90", D2: "0.95"})))

        b_line = ("500", "500", "0")
        problems = [
            *_line_problems(result, {D0: {B: b_line}, D1: {B: b_line}, D2: {A: (None, "1000", "50"), B: b_line}}),
            *_broker_end_problems(result, A, cash="1050", capital="1000", returns="50"),
            *_state_problems(result, {D2: {"cash": "1550", "contributed": "1500", "generated": "50"}}),
        ]
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# ACROSS BROKERS — native dollars change hands
# =============================================================================


class TestRevaluationAcrossBrokers:
    """A transfer between brokers moves native dollars; each broker's line follows the rate."""

    def test_b2_a_same_day_transfer_on_a_rate_move_day(self):
        """B2 — scope {A, B}: the USD deposit at A, all of it sent to B on D1 (both legs that day);
        rates D0 0.90, D1 0.95. A keeps the gain on the dollars it held; B receives 950.

        Before F: D1 A -50/-50/0 (nav/capital/pnl); total P 0.
        """
        out_leg, in_leg = _cash_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="1000", in_amount="1000", out_currency="USD", in_currency="USD")
        classification = _classify([_usd_deposit(), out_leg, in_leg], {A, B})
        result = _build(**_overrides(classification, date_to=D1, fx_rate_map=_usd_rates({D0: "0.90", D1: "0.95"})))

        problems = [
            *_line_problems(result, {D1: {A: ("0", "-50", "50"), B: ("950", "950", "0")}}),
            *_state_problems(result, {D1: {"cash": "950", "nav": "950", "capital": "900", "P": "50"}}),
        ]
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_b3_dollars_in_transit_follow_the_rate_until_they_arrive(self):
        """B3 — scope {A, B}: the USD deposit at A, all of it sent on D1 and received at B on D5;
        rates D0 0.90, D1 0.90, D2 0.95, D3 1.00, D4 1.00, D5 1.05. Each rate move shows in A's
        line on its own day, until B receives 1050 on D5.

        Before F: pnl A D1..D5: 0, 0, 0, 100, 150.
        """
        result = _build(**_b3_overrides())

        lines = {day: {A: (None, None, pnl)} for day, pnl in zip(DAYS, ("0", "0", "50", "100", "100", "150"), strict=True)}
        lines[D5][B] = ("1050", "1050", "0")
        problems = [*_line_problems(result, lines), *_state_problems(result, {D5: {"P": "150"}})]
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# WINDOWS — a run starting after the first transaction replays the earlier rate moves
# =============================================================================


class TestRevaluationInAWindow:
    """A window run (``date_from`` after the first transaction) replays the pre-frame rate moves
    too, so it agrees with the full run on every day the two share."""

    def test_b3w_a_window_inside_the_transit_matches_the_full_run(self):
        """B3w — B3 run with ``date_from=D3``: on D3-D5 it equals the full B3 run (broker lines
        nav/capital/pnl; aggregate cash, nav, capital, P), with B3's numbers.

        Before F: - (no value in the spec table).
        """
        full = _build(**_b3_overrides())
        window = _build(**_b3_overrides(date_from=D3))

        days = (D3, D4, D5)
        lines = {D3: {A: (None, None, "100")}, D4: {A: (None, None, "100")}, D5: {A: (None, None, "150"), B: ("1050", "1050", "0")}}
        problems = [
            *_emitted_problems(window, days),
            *_field_mismatches(window, full, days, ("cash", "nav", "capital", "P")),
            *_line_mismatches(window, full, A, days),
            *_line_mismatches(window, full, B, days),
        ]
        for run, result in (("full", full), ("window", window)):
            problems.extend(_labelled(run, [*_line_problems(result, lines), *_state_problems(result, {D5: {"P": "150"}})]))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(full.daily_states)
        _assert_invariant_every_day(window.daily_states)

    def test_b7_a_one_day_window_on_a_rate_move_day(self):
        """B7 — the USD deposit; rates D0-D2 0.90, D3 0.95; ``date_from = date_to = D3``. D0's rate is
        replayed pre-frame and D3's move revalues the only emitted day.

        Before F: cash 900, P 0.
        """
        result = _build(**_deposit_only({D0: "0.90", D1: "0.90", D2: "0.90", D3: "0.95"}, date_from=D3, date_to=D3))

        problems = [
            *_emitted_problems(result, (D3,)),
            *_state_problems(result, {D3: {"cash": "950", "capital": "900", "P": "50", "contributed": "900", "generated": "50"}}),
        ]
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_b10_a_window_after_a_pre_frame_rate_move_matches_the_full_run(self):
        """B10 — the USD deposit; rates D0 0.90, D1-D4 0.95; X bought on D2 for 1000 USD and sold on
        D4 for 1000 USD, quoted 100 USD D2-D4. The D1 move happens before a window that starts
        on D3: replayed pre-frame, it funds the purchase exactly as in the full run.

        Before F: window run without pre-frame FX gives 902.5 / 47.5.
        """
        full = _build(**_b10_overrides(date_from=D0))
        window = _build(**_b10_overrides(date_from=D3))

        days = (D3, D4)
        expected = {D3: {"nav": "950", "P": "50", "contributed": "0", "generated": "0"}, D4: {"cash": "950", "contributed": "950", "generated": "0"}}
        problems = [
            *_emitted_problems(window, days),
            *_field_mismatches(window, full, days, ("cash", "capital", "P", "contributed", "generated")),
            *_end_pool_mismatches(window, full),
        ]
        for run, result in (("full", full), ("window", window)):
            problems.extend(_labelled(run, [*_state_problems(result, expected), *_pool_problems(result, capital={A: "950"}, returns={A: "0"})]))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(full.daily_states)
        _assert_invariant_every_day(window.daily_states)
