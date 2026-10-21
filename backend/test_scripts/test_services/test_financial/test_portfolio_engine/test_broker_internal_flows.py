"""Red-first tests for lot 41 — per-broker P&L lines without jumps at internal transfers.

The defect (portfolio_engine @ d59762e0a). A broker's P&L line is ``P_b = V_b - C_b``,
with ``C_b`` the broker's cumulative external cash flow. An internal pair
(``linked_internal``) carries no external cash flow, so on the arrival day the sender's
line drops by the moved value and the receiver's line jumps by it: capital moving
between brokers, reported as a loss and a gain. The scope aggregate is already right.

The approved fix (decisions D1-D6):

- D1, step 3b: every ``linked_internal`` TRANSFER / CASH_TRANSFER / FX_CONVERSION pair
  between DIFFERENT brokers books one zero-sum per-broker capital flow on the arrival
  day (the later leg date): ``C_sender -= X`` and ``C_receiver += X``. X is the value
  entering the receiver's NAV that day, at the SENDER's share: the receiver leg's
  ``|amount|`` converted at its own date for cash and FX, the market value of
  ``|receiver qty|`` (same valuation as the NAV) for securities. Nothing moves during
  the transit, and no aggregate changes (``TestAggregateRegressionGuard``).
- D2: a TRANSFER leg whose partner is outside the scope or not found is capital at
  market value on its own date: ``sign(qty) * MV(|qty * share|, leg date)``.
- D3: no value (MISSING mark, missing rate) means no flow.
- J-17: a security with no price at all (no quote, BUY or SELL) is valued at its book cost, so X is
  the book cost the arrival adds to the receiver's pool, rescaled to the sender's share, whether
  that pool's cost is complete or not: an arrival of unknown cost adds 0 (no flow), and the gap of
  an unknown cost stays with the broker whose cost it is.
- D4: ADJUSTMENT pairs keep the in-kind rule (capital at cost).
- D5: orphans (no related id): a CASH_TRANSFER / FX_CONVERSION with an amount is an
  external cash flow; an orphan TRANSFER follows D2 in the builder.
- D6: the share-mismatch warning stays; the residual ``(s_B - s_A) * X`` is expected.
- T2c: the FX preload also asks the rates that the market value of a TRANSFER leg dated
  before ``date_from`` needs on the leg date.

Notation: target EUR; brokers A = 10, B = 20, C = 30; d0 = 2025-01-01 ... d5 = 2025-01-06,
d10 = 2025-01-11. ``C_b`` / ``P_b`` are the ``capital_contribution`` / ``pnl_contribution``
of broker b. Each red test's docstring quotes the value before the fix ("today") that
its failure shows.

Pure tests — no DB, no server. Helpers mirror test_broker_pnl_contributions.py (this
directory has no cross-test-module imports).
"""

import dataclasses
import functools
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, DailyPortfolioState, EngineEndState
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash
from backend.test_scripts.test_services._unit_steps_double import UnitStepsDouble

A, B, C = 10, 20, 30
ASSET = 100
UNPRICED_ASSET = 200

D0 = date(2025, 1, 1)
D1 = date(2025, 1, 2)
D2 = date(2025, 1, 3)
D3 = date(2025, 1, 4)
D4 = date(2025, 1, 5)
D5 = date(2025, 1, 6)
D10 = date(2025, 1, 11)
D11 = date(2025, 1, 12)
DAYS = (D0, D1, D2, D3, D4, D5)

# =============================================================================
# HELPERS — mirror test_broker_pnl_contributions.py
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
    mark series, average costs and native cash computed once (the aggregate guard reuses them)."""
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


# =============================================================================
# SCENARIO HELPERS
# =============================================================================


def _setup_t() -> list[MagicMock]:
    """Setup T: broker A deposits 100 EUR and buys 10 units of asset 100 for 100 EUR, both on d0."""
    return [
        _tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="100"),
        _tx(id=2, broker_id=A, type="BUY", dt=D0, amount="-100", quantity="10", asset_id=ASSET),
    ]


def _setup_t_prices() -> dict[int, list[tuple[date, Decimal, str]]]:
    """Asset 100 (EUR) closes at 10, 11, 12, 13, 14, 15 on d0..d5."""
    return {ASSET: [(day, Decimal(price), "EUR") for day, price in zip(DAYS, ("10", "11", "12", "13", "14", "15"), strict=True)]}


def _setup_t_aggregate(last_day: date) -> dict[date, tuple[str, str]]:
    """Scope aggregate (C, P) of Setup T while its 10 units stay in scope: C 100, P = MV - 100."""
    return {day: ("100", str(10 * index)) for index, day in enumerate(DAYS) if day <= last_day}


def _setup_c() -> list[MagicMock]:
    """Setup C: broker A deposits 5000 EUR on d0."""
    return [_tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="5000")]


def _transfer_pair(
    out_id: int,
    in_id: int,
    *,
    sender: int,
    receiver: int,
    out_dt: date,
    in_dt: date,
    qty: str,
    asset_id: int = ASSET,
    type: str = "TRANSFER",
    cost_basis_override: str | None = None,
    cost_basis_currency: str | None = None,
) -> tuple[MagicMock, MagicMock]:
    """Two linked security legs: -qty on the sender, +qty on the receiver, amount 0, no currency."""
    common = {
        "type": type,
        "amount": "0",
        "currency": None,
        "asset_id": asset_id,
        "cost_basis_override": cost_basis_override,
        "cost_basis_currency": cost_basis_currency,
    }
    out_leg = _tx(id=out_id, broker_id=sender, dt=out_dt, quantity=f"-{qty}", related_id=in_id, **common)
    in_leg = _tx(id=in_id, broker_id=receiver, dt=in_dt, quantity=qty, related_id=out_id, **common)
    return out_leg, in_leg


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


def _overrides(classification, *, date_to, price_map=None, fx_rate_map=None, date_from=D0) -> dict:
    """Builder kwargs for a classified scenario; every asset is a EUR "Stock" with no classification.
    A ``date_from`` after the first transaction emits the states from it on (J1: one replay from the first movement)."""
    price_map = price_map or {}
    asset_ids = {ctxn.tx.asset_id for ctxn in classification.classified if ctxn.tx.asset_id is not None} | set(price_map)
    return {
        "classified_txs": classification.classified,
        "in_transit_intervals": classification.in_transit_intervals,
        "external_cash_flows": classification.external_cash_flows,
        "price_map": price_map,
        "fx_rate_map": fx_rate_map or {},
        "asset_currencies": dict.fromkeys(asset_ids, "EUR"),
        "asset_types": dict.fromkeys(asset_ids, "Stock"),
        "asset_classifications": dict.fromkeys(asset_ids),
        "date_from": date_from,
        "date_to": date_to,
    }


def _classifications(classification) -> dict[int, str]:
    return {ctxn.tx.id: ctxn.classification for ctxn in classification.classified}


def _intervals(classification) -> list[tuple[date, date, str, Decimal]]:
    return [(it.start_date, it.end_date, it.tx_type, it.share) for it in classification.in_transit_intervals]


# =============================================================================
# EXPECTATION CHECKERS — collect every mismatch, so a red shows today's whole line
# =============================================================================


def _contribution_problems(state: DailyPortfolioState, broker_id: int, capital: str | None, pnl: str | None) -> list[str]:
    contribution = state.broker_contributions.get(broker_id)
    if contribution is None:
        return [f"{state.date}/broker {broker_id}: no broker contribution"]
    problems = []
    if capital is not None and contribution.capital_contribution != Decimal(capital):
        problems.append(f"{state.date}/broker {broker_id}: capital_contribution={contribution.capital_contribution}, expected {capital}")
    if pnl is not None and contribution.pnl_contribution != Decimal(pnl):
        problems.append(f"{state.date}/broker {broker_id}: pnl_contribution={contribution.pnl_contribution}, expected {pnl}")
    return problems


def _line_problems(result, expected: dict[date, dict[int, tuple[str | None, str | None]]]) -> list[str]:
    """``expected``: {day: {broker_id: (C_b, P_b)}}; None leaves a value unchecked."""
    states = {s.date: s for s in result.daily_states}
    problems: list[str] = []
    for day, lines in expected.items():
        state = states.get(day)
        if state is None:
            problems.append(f"{day}: no state emitted")
            continue
        for broker_id, (capital, pnl) in lines.items():
            problems.extend(_contribution_problems(state, broker_id, capital, pnl))
    return problems


def _aggregate_problems(result, expected: dict[date, tuple[str | None, str | None]]) -> list[str]:
    """``expected``: {day: (C, P)} of the scope aggregate; None leaves a value unchecked."""
    states = {s.date: s for s in result.daily_states}
    problems: list[str] = []
    for day, (capital, pnl) in expected.items():
        state = states.get(day)
        if state is None:
            problems.append(f"{day}: no state emitted")
            continue
        if capital is not None and state.cumulative_external_cash_flow != Decimal(capital):
            problems.append(f"{day}: aggregate cumulative_external_cash_flow={state.cumulative_external_cash_flow}, expected {capital}")
        if pnl is not None and state.total_pnl != Decimal(pnl):
            problems.append(f"{day}: aggregate total_pnl={state.total_pnl}, expected {pnl}")
    return problems


def _transit_problems(result, departure: date, arrival: date, broker_ids) -> list[str]:
    """No flow during the transit: each broker's capital is constant on the emitted days of [departure, arrival)."""
    window = [s for s in result.daily_states if departure <= s.date < arrival]
    if not window:
        return [f"no state emitted in the transit window [{departure}, {arrival})"]
    problems: list[str] = []
    for broker_id in broker_ids:
        capitals = {s.date: (s.broker_contributions[broker_id].capital_contribution if broker_id in s.broker_contributions else None) for s in window}
        if len(set(capitals.values())) != 1:
            problems.append(f"broker {broker_id}: capital moved during the transit [{departure}, {arrival}): {capitals}")
    return problems


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


# =============================================================================
# CASE FACTORIES — each returns (classification, builder overrides)
# =============================================================================


def _case_01_cash_same_day():
    out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="1000", in_amount="1000")
    classification = _classify([*_setup_c(), out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D5)


def _case_03_foreign_cash_in_transit():
    deposit = _tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="1000", currency="USD")
    out_leg, in_leg = _cash_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D4, out_amount="1000", in_amount="1000", out_currency="USD", in_currency="USD")
    classification = _classify([deposit, out_leg, in_leg], {A, B})
    rates = _usd_rates({D0: "0.90", D1: "0.90", D2: "0.91", D3: "0.92", D4: "0.93", D5: "0.93"})
    return classification, _overrides(classification, date_to=D5, fx_rate_map=rates)


def _case_04a_securities_same_day():
    out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D2, qty="10")
    classification = _classify([*_setup_t(), out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D5, price_map=_setup_t_prices())


def _case_04b_securities_in_transit():
    out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10")
    classification = _classify([*_setup_t(), out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D5, price_map=_setup_t_prices())


def _case_05_missing_price_at_arrival():
    adjustment = _tx(id=1, broker_id=A, type="ADJUSTMENT", dt=D0, currency=None, quantity="10", asset_id=UNPRICED_ASSET)
    out_leg, in_leg = _transfer_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10", asset_id=UNPRICED_ASSET, cost_basis_override="10", cost_basis_currency="EUR")
    classification = _classify([adjustment, out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D5, price_map={UNPRICED_ASSET: [(D4, Decimal("15"), "EUR")]})


def _case_05c_unknown_cost_at_arrival():
    """Case 5 without any cost: the legs carry no cost_basis_override, so B's units have no known cost."""
    adjustment = _tx(id=1, broker_id=A, type="ADJUSTMENT", dt=D0, currency=None, quantity="10", asset_id=UNPRICED_ASSET)
    out_leg, in_leg = _transfer_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10", asset_id=UNPRICED_ASSET)
    classification = _classify([adjustment, out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D5, price_map={UNPRICED_ASSET: [(D4, Decimal("15"), "EUR")]})


def _case_05d_unpriced_with_known_cost_between_brokers():
    """Case 5 with A's cost known: A's 10 units arrive on d0 by an orphan TRANSFER (no related id) at 10 EUR a unit."""
    orphan_in = _tx(id=1, broker_id=A, type="TRANSFER", dt=D0, currency=None, quantity="10", asset_id=UNPRICED_ASSET, cost_basis_override="10", cost_basis_currency="EUR")
    out_leg, in_leg = _transfer_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10", asset_id=UNPRICED_ASSET, cost_basis_override="10", cost_basis_currency="EUR")
    classification = _classify([orphan_in, out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D5, price_map={UNPRICED_ASSET: [(D4, Decimal("15"), "EUR")]})


def _case_05e_unpriced_pair_between_shares(share_a: str, share_b: str, received_unit_cost: str = "10"):
    """Case 5d's book with ownership shares s_A / s_B and no price at all: A's 10 units arrive on d0 by an orphan
    TRANSFER at 10 EUR a unit, then move A -> B by a pair on d2 (one day, no transit) whose legs carry
    ``received_unit_cost`` EUR a unit."""
    orphan_in = _tx(id=1, broker_id=A, type="TRANSFER", dt=D0, currency=None, quantity="10", asset_id=UNPRICED_ASSET, cost_basis_override="10", cost_basis_currency="EUR")
    out_leg, in_leg = _transfer_pair(2, 3, sender=A, receiver=B, out_dt=D2, in_dt=D2, qty="10", asset_id=UNPRICED_ASSET, cost_basis_override=received_unit_cost, cost_basis_currency="EUR")
    classification = _classify([orphan_in, out_leg, in_leg], {A, B}, shares={A: share_a, B: share_b})
    return classification, _overrides(classification, date_to=D3)


def _case_05f_unpriced_arrival_into_a_receiver_of_unknown_cost():
    """Case 5d's sender with a receiver of unknown cost, no price ever: A's 10 units arrive on d0 by an orphan TRANSFER
    at 10 EUR a unit, B holds 5 units from an ADJUSTMENT without cost since d0, and the 10 move A -> B, d1 -> d3, their
    legs carrying 10 EUR a unit."""
    orphan_in = _tx(id=1, broker_id=A, type="TRANSFER", dt=D0, currency=None, quantity="10", asset_id=UNPRICED_ASSET, cost_basis_override="10", cost_basis_currency="EUR")
    held_at_b = _tx(id=2, broker_id=B, type="ADJUSTMENT", dt=D0, currency=None, quantity="5", asset_id=UNPRICED_ASSET)
    out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10", asset_id=UNPRICED_ASSET, cost_basis_override="10", cost_basis_currency="EUR")
    classification = _classify([orphan_in, held_at_b, out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D4)


def _case_05b_missing_fx_at_arrival():
    deposit = _tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="1000", currency="USD")
    out_leg, in_leg = _cash_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D2, out_amount="1000", in_amount="1000", out_currency="USD", in_currency="USD")
    classification = _classify([deposit, out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D3, fx_rate_map=_usd_rates({D0: "0.90", D1: "0.90"}))


def _case_06_partial_position():
    out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D2, qty="4")
    classification = _classify([*_setup_t(), out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D5, price_map=_setup_t_prices())


def _case_07_fx_conversion_between_brokers():
    deposit = _tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="1000", currency="USD")
    out_leg, in_leg = _cash_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="1000", in_amount="900", out_currency="USD", in_currency="EUR", type="FX_CONVERSION")
    classification = _classify([deposit, out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D2, fx_rate_map=_usd_rates({D0: "0.92", D1: "0.92", D2: "0.92"}))


def _case_08_shares(share_a: str, share_b: str):
    deposit = _tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="2000")
    out_leg, in_leg = _cash_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="1000", in_amount="1000")
    classification = _classify([deposit, out_leg, in_leg], {A, B}, shares={A: share_a, B: share_b})
    return classification, _overrides(classification, date_to=D2)


def _case_09_before_date_from(date_from: date = D10):
    out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10")
    classification = _classify([*_setup_t(), out_leg, in_leg], {A, B})
    prices = {ASSET: [(D0, Decimal("10"), "EUR"), (D1, Decimal("11"), "EUR"), (D2, Decimal("12"), "EUR"), (D3, Decimal("13"), "EUR"), (D10, Decimal("14"), "EUR")]}
    return classification, _overrides(classification, date_to=D10, price_map=prices, date_from=date_from)


def _case_10_transit_straddles_date_from():
    out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D5, qty="10")
    classification = _classify([*_setup_t(), out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D5, price_map=_setup_t_prices(), date_from=D3)


def _case_11_chain():
    a_out, b_in = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D2, qty="10")
    b_out, c_in = _transfer_pair(5, 6, sender=B, receiver=C, out_dt=D3, in_dt=D4, qty="10")
    classification = _classify([*_setup_t(), a_out, b_in, b_out, c_in], {A, B, C})
    return classification, _overrides(classification, date_to=D5, price_map=_setup_t_prices())


def _case_12_round_trip():
    a_out, b_in = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D2, qty="10")
    b_out, a_in = _transfer_pair(5, 6, sender=B, receiver=A, out_dt=D4, in_dt=D4, qty="10")
    classification = _classify([*_setup_t(), a_out, b_in, b_out, a_in], {A, B})
    return classification, _overrides(classification, date_to=D5, price_map=_setup_t_prices())


def _case_14a_fee_and_transfer():
    fee = _tx(id=2, broker_id=A, type="FEE", dt=D1, amount="-5")
    out_leg, in_leg = _cash_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="1000", in_amount="1000")
    classification = _classify([*_setup_c(), fee, out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D2)


def _case_14b_net_amount_received():
    out_leg, in_leg = _cash_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D1, out_amount="1000", in_amount="995")
    classification = _classify([*_setup_c(), out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D2)


def _case_15_pair_with_cost(pair_type: str):
    out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D2, qty="10", type=pair_type, cost_basis_override="10", cost_basis_currency="EUR")
    classification = _classify([*_setup_t(), out_leg, in_leg], {A, B})
    return classification, _overrides(classification, date_to=D3, price_map=_setup_t_prices())


def _case_15a_transfer_pair_with_cost():
    return _case_15_pair_with_cost("TRANSFER")


# =============================================================================
# D1 — CASH AND FX PAIRS BETWEEN BROKERS
# =============================================================================


class TestCashPairsBetweenBrokers:
    """D1 for cash legs: X = |receiver amount| converted at the receiver leg's date x s_A."""

    def test_case_01_same_day_cash_pair(self):
        """Case 1: 1000 EUR moved A -> B on d1. From d1 C_A 4000 / C_B 1000 and both lines
        flat; the aggregate capital stays 5000. Today d1: P_A -1000, P_B +1000."""
        classification, overrides = _case_01_cash_same_day()
        assert _classifications(classification) == {1: "normal", 3: "linked_internal", 4: "linked_internal"}
        assert classification.in_transit_intervals == []
        assert classification.external_cash_flows == [(D0, A, Decimal("5000"), "EUR")]

        result = _build(**overrides)

        expected = {D0: {A: ("5000", "0"), B: ("0", "0")}} | dict.fromkeys(DAYS[1:], {A: ("4000", "0"), B: ("1000", "0")})
        problems = _line_problems(result, expected) + _aggregate_problems(result, dict.fromkeys(DAYS, ("5000", "0")))
        assert not problems, "\n".join(problems)
        assert result.end_state.cumulative_ecf_by_broker == {A: Decimal("4000"), B: Decimal("1000")}
        _assert_invariant_every_day(result.daily_states)

    def test_case_03_foreign_cash_in_transit(self):
        """Case 3: 1000 USD leaves A on d1 and reaches B on d4 (USD->EUR .90 .90 .91 .92 .93 .93).

        The value in transit stays with A at the day's rate, so A keeps every FX swing:
        X = 1000 x .93 (receiver leg, its own date) x s_A = 930 on d4, C_A = 900 - 930 = -30
        and P_A = +30, the whole FX gain. No capital moves on d1-d3.
        Today d4: P_A -900, P_B +930.

        d2 is a USD rate-change day (.90 -> .91), and a rate change of a held foreign
        currency makes the day dirty, so the value in transit follows it: P_A(d2) = +10,
        as in the lot table.
        """
        classification, overrides = _case_03_foreign_cash_in_transit()
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}
        assert _intervals(classification) == [(D1, D3, "cash", Decimal("1"))]
        assert classification.external_cash_flows == [(D0, A, Decimal("1000"), "USD")]

        result = _build(**overrides)

        expected = {
            D0: {A: ("900", "0"), B: ("0", "0")},
            D1: {A: ("900", "0"), B: ("0", "0")},
            D2: {A: ("900", "10"), B: ("0", "0")},
            D3: {A: ("900", "20"), B: ("0", "0")},
            D4: {A: ("-30", "30"), B: ("930", "0")},
            D5: {A: ("-30", "30"), B: ("930", "0")},
        }
        aggregate = {D0: ("900", "0"), D1: ("900", "0"), D2: ("900", "10"), D3: ("900", "20"), D4: ("900", "30"), D5: ("900", "30")}
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate) + _transit_problems(result, D1, D4, (A, B))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_05b_missing_rate_at_arrival_moves_nothing(self):
        """Case 5b, guard (D3): no USD rate on the arrival date d2, so X is unavailable and
        no capital moves: C_A 900 and C_B 0 every day, and no exception. P is not pinned
        (the arriving cash itself cannot be valued). Green before and after the fix."""
        classification, overrides = _case_05b_missing_fx_at_arrival()
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}

        result = _build(**overrides)

        problems = _line_problems(result, dict.fromkeys((D0, D1, D2, D3), {A: ("900", None), B: ("0", None)}))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_07_fx_conversion_between_brokers(self):
        """Case 7: A converts 1000 USD (920 EUR of capital at .92) into 900 EUR credited at B
        on d1. X = 900 (receiver leg, EUR): B starts flat and A keeps the conversion loss
        of 20. Today d1: P_A -920, P_B +900."""
        classification, overrides = _case_07_fx_conversion_between_brokers()
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}
        assert classification.in_transit_intervals == []

        result = _build(**overrides)

        expected = {D0: {A: ("920", "0"), B: ("0", "0")}} | dict.fromkeys((D1, D2), {A: ("20", "-20"), B: ("900", "0")})
        aggregate = {D0: ("920", "0"), D1: ("920", "-20"), D2: ("920", "-20")}
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    @pytest.mark.parametrize(
        ("share_a", "share_b", "line_a_d0", "lines_after", "aggregate_after"),
        [
            pytest.param("0.5", "0.5", ("1000", "0"), {A: ("500", "0"), B: ("500", "0")}, ("1000", "0"), id="a50_b50"),
            pytest.param("0.5", "1", ("1000", "0"), {A: ("500", "0"), B: ("500", "500")}, ("1000", "500"), id="a50_b100"),
            pytest.param("1", "0.5", ("2000", "0"), {A: ("1000", "0"), B: ("1000", "-500")}, ("2000", "-500"), id="a100_b50"),
        ],
    )
    def test_case_08_shares(self, share_a, share_b, line_a_d0, lines_after, aggregate_after):
        """Case 8: 1000 EUR moved A -> B on d1 with ownership shares s_A / s_B.

        X = 1000 x s_A, at the SENDER's share. With s_A != s_B the receiver's line keeps the
        residual (s_B - s_A) x X (D6: the share-mismatch warning stays, the residual is
        expected); the aggregate P is unchanged. Today d1 (P_A/P_B): -500/+500 (a50_b50),
        -500/+1000 (a50_b100), -1000/+500 (a100_b50).
        """
        classification, overrides = _case_08_shares(share_a, share_b)
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}

        result = _build(**overrides)

        expected = {D0: {A: line_a_d0, B: ("0", "0")}} | dict.fromkeys((D1, D2), lines_after)
        aggregate = {D0: (line_a_d0[0], "0")} | dict.fromkeys((D1, D2), aggregate_after)
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_14a_fee_stays_with_the_sender(self):
        """Case 14a: an unlinked 5 EUR fee at A plus 1000 EUR moved A -> B, all on d1. Only
        the fee is a loss, and it is A's. Today d1: P_A -1005, P_B +1000."""
        classification, overrides = _case_14a_fee_and_transfer()
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}

        result = _build(**overrides)

        expected = {D0: {A: ("5000", "0"), B: ("0", "0")}} | dict.fromkeys((D1, D2), {A: ("4000", "-5"), B: ("1000", "0")})
        aggregate = {D0: ("5000", "0"), D1: ("5000", "-5"), D2: ("5000", "-5")}
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_14b_net_amount_received(self):
        """Case 14b: A sends 1000 EUR and B receives 995 on d1. X = 995 (what enters B's NAV),
        so the 5 EUR lost on the way stays with A. Today d1: P_A -1000, P_B +995."""
        classification, overrides = _case_14b_net_amount_received()
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}

        result = _build(**overrides)

        expected = {D0: {A: ("5000", "0"), B: ("0", "0")}} | dict.fromkeys((D1, D2), {A: ("4005", "-5"), B: ("995", "0")})
        aggregate = {D0: ("5000", "0"), D1: ("5000", "-5"), D2: ("5000", "-5")}
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# D1 — SECURITIES PAIRS BETWEEN BROKERS
# =============================================================================


class TestSecuritiesPairsBetweenBrokers:
    """D1 for TRANSFER legs: X = MV(|receiver qty| x s_A) on the arrival day, valued like the NAV.
    Setup T: A holds 10 units of asset 100 bought at 10, closes 10..15 on d0..d5."""

    def test_case_04a_same_day_transfer(self):
        """Case 4a: the 10 units move A -> B on d2: X = 120. A keeps the +20 earned before
        the move, B earns from d2 on. Today d2: P_A -100, P_B +120."""
        classification, overrides = _case_04a_securities_same_day()
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}
        assert classification.in_transit_intervals == []
        assert classification.external_cash_flows == [(D0, A, Decimal("100"), "EUR")]

        result = _build(**overrides)

        expected = {
            D0: {A: ("100", "0"), B: ("0", "0")},
            D1: {A: ("100", "10"), B: ("0", "0")},
            D2: {A: ("-20", "20"), B: ("120", "0")},
            D3: {A: ("-20", "20"), B: ("120", "10")},
            D4: {A: ("-20", "20"), B: ("120", "20")},
            D5: {A: ("-20", "20"), B: ("120", "30")},
        }
        problems = _line_problems(result, expected) + _aggregate_problems(result, _setup_t_aggregate(D5))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_04b_transfer_in_transit(self):
        """Case 4b: the 10 units leave A on d1 and reach B on d3. The value in transit stays
        with A (+10, +20), and X = MV(10, d3) = 130 on arrival, so A keeps +30. No capital
        moves on d1-d2. Today d3: P_A -100, P_B +130."""
        classification, overrides = _case_04b_securities_in_transit()
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}
        assert _intervals(classification) == [(D1, D2, "asset", Decimal("1"))]

        result = _build(**overrides)

        expected = {
            D0: {A: ("100", "0"), B: ("0", "0")},
            D1: {A: ("100", "10"), B: ("0", "0")},
            D2: {A: ("100", "20"), B: ("0", "0")},
            D3: {A: ("-30", "30"), B: ("130", "0")},
            D4: {A: ("-30", "30"), B: ("130", "10")},
            D5: {A: ("-30", "30"), B: ("130", "20")},
        }
        problems = _line_problems(result, expected) + _aggregate_problems(result, _setup_t_aggregate(D5)) + _transit_problems(result, D1, D3, (A, B))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_05_unpriced_arrival_moves_the_receivers_cost(self):
        """Case 5 (J-17): asset 200 has no price before d4. A's 10 units came by an ADJUSTMENT with no
        cost (A's pool has no known cost); the legs carry 10 EUR a unit. On d3 B's pool is complete — 100
        from its leg — so B values its units at that cost (ESTIMATED_AT_COST) and X = the 100 the arrival
        adds to B's pool: what it brings into B's NAV, as the NAV values it (lot 41). C_A -100, C_B 100:
        B starts flat and earns the +50 of the first quote on d4. A keeps the +100 its line showed while
        the units were in transit (the in-transit cost fallback values them at the legs' 100, against A's
        unknown cost): the artifact of A's own unknown cost, A's to answer for (P22: each broker answers
        for its own stretch), which MISSING_COST_BASIS reports. The aggregate does not depend on step 3b.

        Before J-17: on d3 B's units were MISSING and X unavailable, so no capital moved: d3 A (0, 0),
        B (0, 0); d4-d5 A (0, 0), B (0, 150); the aggregate P 100, 0, 150 on d2, d3, d4. (J-17's first
        version moved what A's pool gave up, unknown, so nothing: d3 A (0, 0), B (0, 100).)
        """
        classification, overrides = _case_05_missing_price_at_arrival()
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}
        assert _intervals(classification) == [(D1, D2, "asset", Decimal("1"))]

        result = _build(**overrides)

        expected = {
            D0: {A: ("0", "0"), B: ("0", "0")},
            D1: {A: ("0", "100"), B: ("0", "0")},
            D2: {A: ("0", "100"), B: ("0", "0")},
            D3: {A: ("-100", "100"), B: ("100", "0")},
            D4: {A: ("-100", "100"), B: ("100", "50")},
            D5: {A: ("-100", "100"), B: ("100", "50")},
        }
        aggregate = {D0: ("0", "0"), D1: ("0", "100"), D2: ("0", "100"), D3: ("0", "100"), D4: ("0", "150"), D5: ("0", "150")}
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate) + _transit_problems(result, D1, D3, (A, B))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_05d_unpriced_security_of_known_cost_moves_its_cost(self):
        """Case 5d (J-17): case 5 with A's cost known — A's 10 units came on d0 by an orphan TRANSFER
        carrying 10 EUR a unit. Asset 200 has no price before d4, so: on d0 the orphan leg is capital
        at its cost (100) and A holds the units at that cost (P_A 0); in transit A keeps the value at
        the legs' cost; on d3 X = the 100 the arrival adds to B's pool, the value B's NAV takes at cost
        (here also what A's pool gives up), so C_A 0, C_B 100 and both lines stay flat at 0 until B
        earns the +50 of the first quote on d4.

        Before J-17: the orphan leg could not be valued (no capital) and A's units were MISSING:
        d0 A (0, 0); d1-d2 A (0, 100); d3 no flow, B MISSING: A (0, 0), B (0, 0); d4-d5 B (0, 150).
        """
        classification, overrides = _case_05d_unpriced_with_known_cost_between_brokers()
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}
        assert _intervals(classification) == [(D1, D2, "asset", Decimal("1"))]

        result = _build(**overrides)

        expected = {
            D0: {A: ("100", "0"), B: ("0", "0")},
            D1: {A: ("100", "0"), B: ("0", "0")},
            D2: {A: ("100", "0"), B: ("0", "0")},
            D3: {A: ("0", "0"), B: ("100", "0")},
            D4: {A: ("0", "0"), B: ("100", "50")},
            D5: {A: ("0", "0"), B: ("100", "50")},
        }
        aggregate = {D0: ("100", "0"), D1: ("100", "0"), D2: ("100", "0"), D3: ("100", "0"), D4: ("100", "50"), D5: ("100", "50")}
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate) + _transit_problems(result, D1, D3, (A, B))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_05c_unknown_cost_at_arrival_moves_nothing(self):
        """Case 5c, guard (D3): the same pair with no cost at all — B's units have no price before d4
        and no known cost, so the arrival adds no known cost to B's pool: X = 0 and no capital moves.

        Before J-17: the same (guard, green before and after): d0-d3 (0, 0) for both, d4-d5 B (0, 150).
        """
        classification, overrides = _case_05c_unknown_cost_at_arrival()
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}

        result = _build(**overrides)

        expected = dict.fromkeys((D0, D1, D2, D3), {A: ("0", "0"), B: ("0", "0")}) | dict.fromkeys((D4, D5), {A: ("0", "0"), B: ("0", "150")})
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    @pytest.mark.parametrize(
        ("share_a", "share_b", "received_unit_cost", "capital_a_before", "lines_after", "aggregate_after"),
        [
            pytest.param("0.5", "0.5", "10", "50", {A: ("0", "0"), B: ("50", "0")}, ("50", "0"), id="a50_b50"),
            pytest.param("0.5", "1", "10", "50", {A: ("0", "0"), B: ("50", "50")}, ("50", "50"), id="a50_b100"),
            pytest.param("1", "0.5", "10", "100", {A: ("0", "0"), B: ("100", "-50")}, ("100", "-50"), id="a100_b50"),
            pytest.param("0.5", "1", "12", "50", {A: ("-10", "10"), B: ("60", "60")}, ("50", "70"), id="a50_b100_received_at_12"),
        ],
    )
    def test_case_05e_unpriced_pair_moves_the_receivers_cost_at_the_senders_share(self, share_a, share_b, received_unit_cost, capital_a_before, lines_after, aggregate_after):
        """Case 5e (J-17): case 5d's book with ownership shares s_A / s_B, the pair on one day (d2), no price
        at all. A's 10 units came on d0 by an orphan TRANSFER at 10 EUR a unit: capital at cost, 100 x s_A,
        and A's line flat. On d2 X is the book cost the arrival adds to B's pool — its leg's unit cost x 10 x
        s_B — rescaled from B's share to the SENDER's (/ s_B x s_A), like case 8: X = unit cost x 10 x s_A.
        As in case 8, B's line keeps the share-mismatch residual (s_B - s_A) x its leg's unit cost x 10 (D6),
        and the aggregate is B's NAV at cost against A's capital. The last row costs B's leg at 12 against
        A's 10: X follows B's cost, 60, not the 50 A's pool gives up, so A keeps (12 - 10) x 10 x s_A = 10
        (P22).

        Before J-17: no price, so no value, no capital for the orphan leg and no flow: both lines (0, 0)
        on every day, the aggregate too. (J-17's first version moved what A's pool gave up: the same lines,
        but for the last row, A (0, 0) and B (50, 70).)
        """
        classification, overrides = _case_05e_unpriced_pair_between_shares(share_a, share_b, received_unit_cost)
        assert _classifications(classification) == {1: "normal", 2: "linked_internal", 3: "linked_internal"}
        assert classification.in_transit_intervals == []

        result = _build(**overrides)

        expected = dict.fromkeys((D0, D1), {A: (capital_a_before, "0"), B: ("0", "0")}) | dict.fromkeys((D2, D3), lines_after)
        aggregate = dict.fromkeys((D0, D1), (capital_a_before, "0")) | dict.fromkeys((D2, D3), aggregate_after)
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_05f_unpriced_arrival_into_a_receiver_of_unknown_cost_moves_the_legs_cost(self):
        """Case 5f (J-17): case 5d's sender — A's 10 units came on d0 by an orphan TRANSFER at 10 EUR a unit
        (capital 100, A at cost and flat, in transit d1-d2 too) — but B already holds 5 units from an
        ADJUSTMENT without cost, so B's pool has no known cost and B's holding is MISSING: the NAV is
        incomplete on every day. No price ever. On d3 the arrival adds its leg's known cost, 100, to B's pool
        (the unknown part counts as zero), so X = 100 whatever that pool's completeness: C_A 0 and A neutral;
        C_B 100 and B's line -100, its 15 units MISSING — the gap of B's own unknown cost stays with B (P22).
        Aggregate (100, -100).

        Before J-17: A's orphan leg brought no capital and A's units were MISSING: d0 A (0, 0); d1-d2
        A (0, 100) by the in-transit cost fallback; from d3 no flow, A (0, 0) and B (0, 0); the aggregate
        (0, 0), then (0, 100), then (0, 0). (With the receiver-completeness check tried and reverted on 16/10
        there was no flow either: from d3 A (100, -100), B (0, 0).)
        """
        classification, overrides = _case_05f_unpriced_arrival_into_a_receiver_of_unknown_cost()
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}
        assert _intervals(classification) == [(D1, D2, "asset", Decimal("1"))]

        result = _build(**overrides)

        expected = dict.fromkeys((D0, D1, D2), {A: ("100", "0"), B: ("0", "0")}) | dict.fromkeys((D3, D4), {A: ("0", "0"), B: ("100", "-100")})
        aggregate = dict.fromkeys((D0, D1, D2), ("100", "0")) | dict.fromkeys((D3, D4), ("100", "-100"))
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate) + _transit_problems(result, D1, D3, (A, B))
        assert not problems, "\n".join(problems)
        completeness = {state.date: (state.nav_complete, state.missing_price_asset_ids) for state in result.daily_states}
        assert completeness == dict.fromkeys((D0, D1, D2, D3, D4), (False, {UNPRICED_ASSET})), "B's units of unknown cost are MISSING on every day, so the NAV is incomplete"
        _assert_invariant_every_day(result.daily_states)

    def test_case_06_partial_position(self):
        """Case 6: 4 of the 10 units move A -> B on d2: X = 4 x 12 = 48. A keeps its +20 and
        earns on its 6 units, B on its 4. Today d2: P_A -28, P_B +48."""
        classification, overrides = _case_06_partial_position()
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}

        result = _build(**overrides)

        expected = {
            D0: {A: ("100", "0"), B: ("0", "0")},
            D1: {A: ("100", "10"), B: ("0", "0")},
            D2: {A: ("52", "20"), B: ("48", "0")},
            D3: {A: ("52", "26"), B: ("48", "4")},
            D4: {A: ("52", "32"), B: ("48", "8")},
            D5: {A: ("52", "38"), B: ("48", "12")},
        }
        problems = _line_problems(result, expected) + _aggregate_problems(result, _setup_t_aggregate(D5))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_11_chain(self):
        """Case 11: A -> B on d2 (X = 120), then B -> C leaving d3 and arriving d4 (X = 140).
        Each broker keeps what it earned while holding: d5 P_A 20, P_B 20, P_C 10, total 50.
        Today d2: P_A -100, P_B +120."""
        classification, overrides = _case_11_chain()
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal", 5: "linked_internal", 6: "linked_internal"}
        assert _intervals(classification) == [(D3, D3, "asset", Decimal("1"))]

        result = _build(**overrides)

        expected = {
            D0: {A: ("100", "0"), B: ("0", "0"), C: ("0", "0")},
            D1: {A: ("100", "10"), B: ("0", "0"), C: ("0", "0")},
            D2: {A: ("-20", "20"), B: ("120", "0"), C: ("0", "0")},
            D3: {A: ("-20", "20"), B: ("120", "10"), C: ("0", "0")},
            D4: {A: ("-20", "20"), B: ("-20", "20"), C: ("140", "0")},
            D5: {A: ("-20", "20"), B: ("-20", "20"), C: ("140", "10")},
        }
        problems = _line_problems(result, expected) + _aggregate_problems(result, _setup_t_aggregate(D5))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_12_round_trip(self):
        """Case 12: A -> B on d2 (X = 120), B -> A on d4 (X = 140). B keeps the +20 earned
        while holding; A gets the units back as capital and earns again from d4.
        Today d2: P_A -100, P_B +120."""
        classification, overrides = _case_12_round_trip()
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal", 5: "linked_internal", 6: "linked_internal"}
        assert classification.in_transit_intervals == []

        result = _build(**overrides)

        expected = {
            D0: {A: ("100", "0"), B: ("0", "0")},
            D1: {A: ("100", "10"), B: ("0", "0")},
            D2: {A: ("-20", "20"), B: ("120", "0")},
            D3: {A: ("-20", "20"), B: ("120", "10")},
            D4: {A: ("120", "20"), B: ("-20", "20")},
            D5: {A: ("120", "30"), B: ("-20", "20")},
        }
        problems = _line_problems(result, expected) + _aggregate_problems(result, _setup_t_aggregate(D5))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_15a_transfer_pair_with_cost_basis(self):
        """Case 15a: a TRANSFER pair carrying cost_basis_override 10 EUR on both legs is
        still a TRANSFER: X = MV(10, d2) = 120, like case 4a (the cost does not matter).
        Today d2: P_A -100, P_B +120."""
        classification, overrides = _case_15a_transfer_pair_with_cost()
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}

        result = _build(**overrides)

        expected = {
            D0: {A: ("100", "0"), B: ("0", "0")},
            D1: {A: ("100", "10"), B: ("0", "0")},
            D2: {A: ("-20", "20"), B: ("120", "0")},
            D3: {A: ("-20", "20"), B: ("120", "10")},
        }
        problems = _line_problems(result, expected) + _aggregate_problems(result, _setup_t_aggregate(D3))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_15b_adjustment_pair_out_leg_has_no_value_and_in_leg_brings_its_cost(self):
        """Case 15b, the same pair typed ADJUSTMENT, as N78-1 reads it literally (the developer's decision,
        21/10/2026: an ADJUSTMENT-out has no value). A's leg keeps C_A at 100 and realizes 0 − the pool cost,
        −100, so P_A falls to −100 from d2; B's leg brings its override cost (100) into C_B, so B's line shows
        +20 on d2 and +30 on d3. The aggregate counts the capital twice, 200, and its P&L is 100 lower than
        Setup T's: −80 on d2, −70 on d3, for a move between two brokers of the scope. Step 3b must not touch it.

        OPEN QUESTION Q-N78-1k: a LINKED internal ADJUSTMENT pair could keep the in-kind rule at cost (A's leg
        taking its cost out of C_A, as before N78-1); the developer may change this pin. Before N78-1 (D4,
        green then): A (0, 0) from d2, the aggregate Setup T's (100, 20) and (100, 30)."""
        classification, overrides = _case_15_pair_with_cost("ADJUSTMENT")
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_internal", 4: "linked_internal"}

        result = _build(**overrides)

        expected = {
            D0: {A: ("100", "0"), B: ("0", "0")},
            D1: {A: ("100", "10"), B: ("0", "0")},
            D2: {A: ("100", "-100"), B: ("100", "20")},
            D3: {A: ("100", "-100"), B: ("100", "30")},
        }
        aggregate = {**_setup_t_aggregate(D1), D2: ("200", "-80"), D3: ("200", "-70")}
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# D1 — BEFORE date_from AND ACROSS IT
# =============================================================================


class TestBeforeDateFromAndAcrossIt:
    """Step 3b runs on the days replayed before date_from as on the emitted ones (J1: one replay, the same rules
    every day; before J1 those days ran in a separate pre-frame)."""

    def test_case_09_transfer_entirely_before_date_from(self):
        """Case 9: 10 units in transit A -> B from d1 to d3, all before date_from d10
        (closes 10, 11, 12, 13 on d0..d3, then 14 on d10). X = MV(10, d3) = 130 must be
        booked on the replayed days. First emitted state d10: C_A -30, P_A +30,
        C_B 130, P_B +10; the run from d0 gives the same d10 lines.
        Today d10: P_A -100, P_B +140."""
        classification, windowed_overrides = _case_09_before_date_from()
        assert _intervals(classification) == [(D1, D2, "asset", Decimal("1"))]

        windowed = _build(**windowed_overrides)
        _, full_overrides = _case_09_before_date_from(date_from=D0)
        full = _build(**full_overrides)

        assert [s.date for s in windowed.daily_states] == [D10]
        problems = _line_problems(windowed, {D10: {A: ("-30", "30"), B: ("130", "10")}}) + _aggregate_problems(windowed, {D10: ("100", "40")})
        assert not problems, "\n".join(problems)
        assert _broker_line(windowed, D10) == _broker_line(full, D10), "the d10 broker lines from date_from=d10 differ from the run from d0's"
        _assert_invariant_every_day(windowed.daily_states)
        _assert_invariant_every_day(full.daily_states)

    def test_case_10_transit_straddles_date_from(self):
        """Case 10: 10 units leave A on d1 (before date_from) and reach B on d5; date_from d3.
        The value in transit stays with A on d3-d4 (+30, +40, no capital moves); on d5
        X = MV(10, d5) = 150. Today d5: P_A -100, P_B +150."""
        classification, overrides = _case_10_transit_straddles_date_from()
        assert _intervals(classification) == [(D1, D4, "asset", Decimal("1"))]

        result = _build(**overrides)

        assert [s.date for s in result.daily_states] == [D3, D4, D5]
        expected = {
            D3: {A: ("100", "30"), B: ("0", "0")},
            D4: {A: ("100", "40"), B: ("0", "0")},
            D5: {A: ("-50", "50"), B: ("150", "0")},
        }
        aggregate = {D3: ("100", "30"), D4: ("100", "40"), D5: ("100", "50")}
        problems = _line_problems(result, expected) + _aggregate_problems(result, aggregate) + _transit_problems(result, D1, D5, (A, B))
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# D2 — SINGLE-BROKER VIEWS (partner outside the scope, or not found)
# =============================================================================


class TestSingleBrokerViews:
    """D2: in a filtered view, a TRANSFER leg whose partner is outside the scope (or not
    found) is capital at market value on its own date: sign(qty) x MV(|qty x share|).
    This changes the view's aggregate C and P on purpose, so these cases are not in the
    aggregate guard. Legs as in case 4b: A -10 on d1, B +10 on d3.
    """

    def test_case_13_receiver_alone(self):
        """B alone: the arriving 10 units are capital at MV(10, d3) = 130, so B's line is
        the same as in the combined view of case 4b. Today d3: P_B +130."""
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10")
        classification = _classify([in_leg], {B}, external_paired={out_leg.id: out_leg})
        assert _classifications(classification) == {4: "linked_external_inflow"}
        assert classification.external_cash_flows == []

        result = _build(**_overrides(classification, date_to=D5, price_map=_setup_t_prices()))

        expected = dict.fromkeys((D0, D1, D2), {B: ("0", "0")}) | {D3: {B: ("130", "0")}, D4: {B: ("130", "10")}, D5: {B: ("130", "20")}}
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _, combined_overrides = _case_04b_securities_in_transit()
        mismatches = _line_mismatches(result, _build(**combined_overrides), B, DAYS)
        assert not mismatches, "B alone differs from B in the combined view:\n" + "\n".join(mismatches)
        _assert_invariant_every_day(result.daily_states)

    def test_case_13_sender_alone(self):
        """A alone: the departing 10 units leave as capital at MV(10, d1) = 110, so
        C_A = 100 - 110 = -10 and P_A = +10 from d1 on.

        A alone = A combined - (MV at arrival - MV at departure) = 30 - (130 - 110) = 10:
        the swings of the value in transit stay with A only in the combined view, where
        A still owns that value. Today from d1: P_A -100.
        """
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D1, in_dt=D3, qty="10")
        classification = _classify([*_setup_t(), out_leg], {A}, external_paired={in_leg.id: in_leg})
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "linked_external_outflow"}
        assert classification.external_cash_flows == [(D0, A, Decimal("100"), "EUR")]

        result = _build(**_overrides(classification, date_to=D5, price_map=_setup_t_prices()))

        expected = {D0: {A: ("100", "0")}} | dict.fromkeys(DAYS[1:], {A: ("-10", "10")})
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_13_dangling_transfer_in(self):
        """A TRANSFER +10 at B on d3 whose related id (999) exists nowhere: the classifier
        keeps it 'normal' with a warning, and D2 books it at MV(10, d3) = 130 like B alone.
        Today d3: P_B +130."""
        dangling = _tx(id=4, broker_id=B, type="TRANSFER", dt=D3, currency=None, quantity="10", asset_id=ASSET, related_id=999)
        classification = _classify([dangling], {B})
        assert _classifications(classification) == {4: "normal"}
        assert len(classification.warnings) == 1
        assert "999" in classification.warnings[0]
        assert classification.external_cash_flows == []

        result = _build(**_overrides(classification, date_to=D5, price_map=_setup_t_prices()))

        expected = dict.fromkeys((D0, D1, D2), {B: ("0", "0")}) | {D3: {B: ("130", "0")}, D4: {B: ("130", "10")}, D5: {B: ("130", "20")}}
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# D5 — ORPHAN LEGS (no related id at all)
# =============================================================================


class TestOrphanLegs:
    """D5: a linked type with no related id. A cash orphan (CASH_TRANSFER / FX_CONVERSION
    with an amount) is an external cash flow, from the classifier; an orphan TRANSFER
    (amount 0) follows D2 in the builder. These change the aggregate C and P on purpose,
    so they are not in the aggregate guard.
    """

    def test_case_16_orphan_transfer_in(self):
        """10 units arrive at B on d2 with no partner: capital at MV(10, d2) = 120.
        Today d2: P_B +120."""
        orphan = _tx(id=7, broker_id=B, type="TRANSFER", dt=D2, currency=None, quantity="10", asset_id=ASSET)
        classification = _classify([orphan], {B})
        assert _classifications(classification) == {7: "normal"}

        result = _build(**_overrides(classification, date_to=D3, price_map=_setup_t_prices()))

        expected = dict.fromkeys((D0, D1), {B: ("0", "0")}) | {D2: {B: ("120", "0")}, D3: {B: ("120", "10")}}
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_16_orphan_cash_transfer_in(self):
        """1000 EUR arrive at B on d1 with no partner: an external cash flow, like a
        DEPOSIT. Today d1: P_B +1000."""
        orphan = _tx(id=7, broker_id=B, type="CASH_TRANSFER", dt=D1, amount="1000")
        classification = _classify([orphan], {B})
        assert _classifications(classification) == {7: "normal"}

        result = _build(**_overrides(classification, date_to=D2))

        expected = {D0: {B: ("0", "0")}} | dict.fromkeys((D1, D2), {B: ("1000", "0")})
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_16_orphan_transfer_out(self):
        """Setup T, then A's 10 units leave on d2 with no partner: capital out at
        MV(10, d2) = 120, so C_A = -20 and A keeps its +20. Today d2: P_A -100."""
        orphan = _tx(id=3, broker_id=A, type="TRANSFER", dt=D2, currency=None, quantity="-10", asset_id=ASSET)
        classification = _classify([*_setup_t(), orphan], {A})
        assert _classifications(classification) == {1: "normal", 2: "normal", 3: "normal"}

        result = _build(**_overrides(classification, date_to=D3, price_map=_setup_t_prices()))

        expected = {D0: {A: ("100", "0")}, D1: {A: ("100", "10")}} | dict.fromkeys((D2, D3), {A: ("-20", "20")})
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_16_orphan_cash_transfer_out(self):
        """Setup C, then 1000 EUR leave A on d1 with no partner: an external cash flow, like
        a WITHDRAWAL. Today d1: P_A -1000."""
        orphan = _tx(id=2, broker_id=A, type="CASH_TRANSFER", dt=D1, amount="-1000")
        classification = _classify([*_setup_c(), orphan], {A})
        assert _classifications(classification) == {1: "normal", 2: "normal"}

        result = _build(**_overrides(classification, date_to=D2))

        expected = {D0: {A: ("5000", "0")}} | dict.fromkeys((D1, D2), {A: ("4000", "0")})
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)

    def test_case_16_dangling_cash_transfer_is_already_external(self):
        """Guard: a CASH_TRANSFER +1000 at B whose related id (999) is not found is already
        an external cash flow (classifier, partner-not-found path), so P_B stays 0.
        Green before and after the fix."""
        dangling = _tx(id=7, broker_id=B, type="CASH_TRANSFER", dt=D1, amount="1000", related_id=999)
        classification = _classify([dangling], {B})
        assert _classifications(classification) == {7: "normal"}
        assert len(classification.warnings) == 1

        result = _build(**_overrides(classification, date_to=D2))

        expected = {D0: {B: ("0", "0")}} | dict.fromkeys((D1, D2), {B: ("1000", "0")})
        problems = _line_problems(result, expected)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# AGGREGATE REGRESSION GUARD — step 3b never changes an aggregate
# =============================================================================

_EXCLUDED_FIELDS = frozenset(
    {
        (DailyPortfolioState, "broker_contributions"),
        (EngineEndState, "cumulative_ecf_by_broker"),
    }
)


def _no_internal_transfer_flows(_self) -> list:
    """Neutral replacement for DailyStateBuilder._internal_transfer_flows: no step-3b flow."""
    return []


def _first_difference(a, b, path: str) -> str | None:
    """Path and values of the first difference between two results, or None.

    Dataclasses field by field (minus _EXCLUDED_FIELDS), dicts by key set then value,
    sequences by length then item, Decimals byte for byte (as_tuple), the rest by ==.
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
        if (type(a), field.name) in _EXCLUDED_FIELDS:
            continue
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
        label = f"{path}[{index}]" + (f"<{left.date}>" if isinstance(left, DailyPortfolioState) else "")
        difference = _first_difference(left, right, label)
        if difference is not None:
            return difference
    return None


def _broker_nav_problems(real, neutral) -> list[str]:
    """Step 3b moves capital only: each broker's NAV slice must be byte-identical too."""
    problems: list[str] = []
    for left, right in zip(real.daily_states, neutral.daily_states, strict=True):
        left_nav = {bid: bc.nav_contribution.as_tuple() for bid, bc in left.broker_contributions.items()}
        right_nav = {bid: bc.nav_contribution.as_tuple() for bid, bc in right.broker_contributions.items()}
        if left_nav != right_nav:
            problems.append(f"{left.date}: nav_contribution by broker {left_nav} != {right_nav}")
    return problems


_GUARD_CASES = [
    pytest.param(_case_01_cash_same_day, id="case01_cash_same_day"),
    pytest.param(_case_03_foreign_cash_in_transit, id="case03_foreign_cash_in_transit"),
    pytest.param(_case_04a_securities_same_day, id="case04a_securities_same_day"),
    pytest.param(_case_04b_securities_in_transit, id="case04b_securities_in_transit"),
    pytest.param(_case_05_missing_price_at_arrival, id="case05_missing_price_at_arrival"),
    pytest.param(_case_05c_unknown_cost_at_arrival, id="case05c_unknown_cost_at_arrival"),
    pytest.param(_case_05d_unpriced_with_known_cost_between_brokers, id="case05d_unpriced_with_known_cost_between_brokers"),
    pytest.param(functools.partial(_case_05e_unpriced_pair_between_shares, "0.5", "1"), id="case05e_unpriced_shares_a50_b100"),
    pytest.param(functools.partial(_case_05e_unpriced_pair_between_shares, "1", "0.5"), id="case05e_unpriced_shares_a100_b50"),
    pytest.param(functools.partial(_case_05e_unpriced_pair_between_shares, "0.5", "1", "12"), id="case05e_unpriced_shares_a50_b100_received_at_12"),
    pytest.param(_case_05f_unpriced_arrival_into_a_receiver_of_unknown_cost, id="case05f_unpriced_arrival_into_a_receiver_of_unknown_cost"),
    pytest.param(_case_05b_missing_fx_at_arrival, id="case05b_missing_fx_at_arrival"),
    pytest.param(_case_06_partial_position, id="case06_partial_position"),
    pytest.param(_case_07_fx_conversion_between_brokers, id="case07_fx_conversion_between_brokers"),
    pytest.param(functools.partial(_case_08_shares, "0.5", "0.5"), id="case08_shares_a50_b50"),
    pytest.param(functools.partial(_case_08_shares, "0.5", "1"), id="case08_shares_a50_b100"),
    pytest.param(functools.partial(_case_08_shares, "1", "0.5"), id="case08_shares_a100_b50"),
    pytest.param(_case_09_before_date_from, id="case09_before_date_from"),
    pytest.param(_case_10_transit_straddles_date_from, id="case10_transit_straddles_date_from"),
    pytest.param(_case_11_chain, id="case11_chain"),
    pytest.param(_case_12_round_trip, id="case12_round_trip"),
    pytest.param(_case_14a_fee_and_transfer, id="case14a_fee_and_transfer"),
    pytest.param(_case_14b_net_amount_received, id="case14b_net_amount_received"),
    pytest.param(_case_15a_transfer_pair_with_cost, id="case15a_transfer_pair_with_cost"),
]


class TestAggregateRegressionGuard:
    """Step 3b moves capital between brokers and nothing else. With the step neutralised
    (the hook ``DailyStateBuilder._internal_transfer_flows`` returning no flow) the result
    must be byte-identical — NAV, C, P, cash, in-transit values, candles, acquisition
    funding, missing data, K/R pools — except the per-broker capital:
    ``DailyPortfolioState.broker_contributions`` and
    ``EngineEndState.cumulative_ecf_by_broker`` are left out of the deep comparison
    (each broker's NAV slice is still compared on its own).

    Green today (the hook does not exist yet: ``raising=False`` adds an unused attribute)
    and must stay green after the fix. Cases 13 and 16 (D2, D5) change aggregates by
    design and are not here.
    """

    @pytest.mark.parametrize("case", _GUARD_CASES)
    def test_step_3b_changes_no_aggregate(self, case, monkeypatch):
        _, overrides = case()
        kwargs = _builder_kwargs(**overrides, compute_candles=True, compute_acquisition_funding=True)

        real = DailyStateBuilder(**kwargs).build()
        monkeypatch.setattr(DailyStateBuilder, "_internal_transfer_flows", _no_internal_transfer_flows, raising=False)
        neutral = DailyStateBuilder(**kwargs).build()

        difference = _first_difference(real, neutral, "result")
        assert difference is None, f"step 3b changed an aggregate: {difference}"
        problems = _broker_nav_problems(real, neutral)
        assert not problems, "\n".join(problems)
        _assert_invariant_every_day(real.daily_states)
        _assert_invariant_every_day(neutral.daily_states)

    def test_neutral_hook_restores_todays_lines(self, monkeypatch):
        """Keeps the guard above from passing vacuously: it means something only if the
        step-3b flows come from ``DailyStateBuilder._internal_transfer_flows(self)``, a
        list where ``[]`` means no flow. On case 1 the real build must show the fixed
        lines on d1 and the neutral build today's jump. If the hook had another name,
        both builds would be the fixed one and the guard would prove nothing.
        Today the real build is still the jump: d1 P_A -1000, P_B +1000."""
        _, overrides = _case_01_cash_same_day()
        kwargs = _builder_kwargs(**overrides)

        real = DailyStateBuilder(**kwargs).build()
        monkeypatch.setattr(DailyStateBuilder, "_internal_transfer_flows", _no_internal_transfer_flows, raising=False)
        neutral = DailyStateBuilder(**kwargs).build()

        problems = _line_problems(real, {D1: {A: ("4000", "0"), B: ("1000", "0")}})
        problems += [f"neutral build: {problem}" for problem in _line_problems(neutral, {D1: {A: ("5000", "-1000"), B: ("0", "1000")}})]
        assert not problems, "\n".join(problems)


# =============================================================================
# T2c — FX PRELOAD FOR TRANSFER LEGS BEFORE date_from
# =============================================================================


class TestPreloadTransferLegRates:
    """T2c: D1/D2 value a TRANSFER leg at market value on the leg date. For a leg dated
    before date_from the in-range loop never asks those rates, so the preload must add
    (asset currency, leg date) and (each non-target price-row currency of the asset, leg date).
    """

    @pytest.mark.asyncio
    async def test_preload_asks_rates_for_transfer_legs_before_the_range(self, monkeypatch):
        """Asset 1 (USD; price rows in USD and CHF) moves internally on d2; asset 2 (GBP)
        arrives from outside the scope on d5. Expected extra keys: (USD, d2), (CHF, d2),
        (GBP, d5). Not (GBP, d3): that BUY is settled in EUR. Nothing on d4: that TRANSFER
        has quantity 0. Today the three extra keys are missing."""
        internal_out = _tx(id=1, broker_id=A, type="TRANSFER", dt=D2, currency=None, quantity="-3", asset_id=1, related_id=2)
        internal_in = _tx(id=2, broker_id=B, type="TRANSFER", dt=D2, currency=None, quantity="3", asset_id=1, related_id=1)
        external_out = _tx(id=3, broker_id=99, type="TRANSFER", dt=D5, currency=None, quantity="-4", asset_id=2, related_id=4)
        external_in = _tx(id=4, broker_id=A, type="TRANSFER", dt=D5, currency=None, quantity="4", asset_id=2, related_id=3)
        buy = _tx(id=5, broker_id=A, type="BUY", dt=D3, amount="-70", currency="EUR", quantity="10", asset_id=2)
        zero_quantity = _tx(id=6, broker_id=A, type="TRANSFER", dt=D4, currency=None, quantity="0", asset_id=2)
        classified = [
            _ctxn(internal_out, "linked_internal", paired=internal_in),
            _ctxn(internal_in, "linked_internal", paired=internal_out),
            _ctxn(buy),
            _ctxn(zero_quantity),
            _ctxn(external_in, "linked_external_inflow", paired=external_out),
        ]

        # P3: one unit_rate_steps call with each currency's windows; every asked day reads 1
        steps = UnitStepsDouble()
        monkeypatch.setattr(portfolio_engine_module, "unit_rate_steps", steps)

        fx_map = await PortfolioCalculationEngine(object())._preload_fx_rates(
            classified_txs=classified,
            in_transit_intervals=[],
            external_cash_flows=[],
            price_map={
                1: [(D0, Decimal("5"), "USD"), (D1, Decimal("5"), "CHF")],
                2: [(D0, Decimal("7"), "GBP")],
            },
            asset_currencies={1: "USD", 2: "GBP"},
            target_currency="EUR",
            date_from=D10,
            date_to=D11,
        )

        keys = set(fx_map)
        assert ("GBP", "EUR", D3) not in keys, "a BUY settled in the target currency needs no rate on its date"
        assert not {key for key in keys if key[2] == D4}, "a TRANSFER with quantity 0 moves no value"
        expected = {(currency, "EUR", day) for currency in ("USD", "CHF", "GBP") for day in (D10, D11)}
        expected |= {("USD", "EUR", D2), ("CHF", "EUR", D2), ("GBP", "EUR", D5)}
        assert keys == expected, f"missing={sorted(expected - keys)} unexpected={sorted(keys - expected)}"
        assert steps.asked_keys() == expected, "the windows of the one unit_rate_steps call cover the same days"
        assert steps.runs() == {
            ("USD", "EUR"): [(D2, D2), (D10, D11)],
            ("CHF", "EUR"): [(D2, D2), (D10, D11)],
            ("GBP", "EUR"): [(D5, D5), (D10, D11)],
        }, "a leg's single day, apart from the range"
