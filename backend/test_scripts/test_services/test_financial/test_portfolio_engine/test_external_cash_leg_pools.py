"""B3 / MF-J3 — a cash leg that crosses the perimeter moves K and R as a DEPOSIT or a WITHDRAWAL would.

The engine splits each broker's cash into two pools, K (contributed capital) and R (generated returns), and keeps a
global W (returns withdrawn from the system); ``cash_from_contributed_capital`` / ``cash_from_generated_returns`` and
the BUY funding split (``acquisition_funding``: from new capital vs reinvested) read them. A CASH_TRANSFER or
FX_CONVERSION leg whose other leg is outside the perimeter (``linked_external_inflow`` / ``linked_external_outflow``)
and an orphan one (link cleared, or the paired row not found: ``normal``) already enter the capital baseline as an
external flow, but ``DailyStateBuilder._apply_pool_rule`` moves the pools only for ``linked_internal`` legs: the cash
moves, the pools do not, and the display rescales pools that no longer match the cash.

Decided rule (developer, wave 6; backlog ``BACKLOG_POST_1.2.md`` «B3» and «MF-J3»): such a leg moves K/R exactly as a
DEPOSIT (amount > 0) or a WITHDRAWAL (amount < 0) from outside the perimeter — an inflow first restores withdrawn
returns W into R (``min(amount, W)``), the rest into K; an outflow leaves K first, then R, and what leaves R goes to W.
``linked_internal`` legs keep J2's rule; asset TRANSFER legs and every other type are unchanged. The capital baseline,
the NAV and the P&L do not change.

- ``TestInflowFromOutsideThePerimeter`` — (a) {B} receives 650 from A; (b) B already holds K 100 / R 100.
- ``TestOutflowAndWithdrawnReturns`` — (c) 150 leaves B: K first, then R into W; a DEPOSIT, then an inflow, restore W.
- ``TestBuyFundingAfterAnExternalLeg`` — (d) the BUY split follows the pools the leg moved.
- ``TestOrphanCashTransfer`` — (e) a CASH_TRANSFER without its pair, +300 then -200.
- ``TestOrphanFxConversion`` — (f) an FX_CONVERSION leg without its pair, in EUR and in USD.
- ``TestSameAsDepositOrWithdrawal`` — every scenario against its twin ledger, the leg replaced by a DEPOSIT or a
  WITHDRAWAL of the same amount: identical pools, W, cash breakdown and BUY funding, day by day.
- ``TestApplyPoolRuleExternalLegs`` — ``_apply_pool_rule`` as a pure function on every non-internal leg.
- ``TestParityGuards`` — (g) green before and after: a linked-internal pair (J2's numbers), DEPOSIT/WITHDRAWAL alone,
  the capital baseline / NAV / P&L of every scenario, the pools never below zero, the asset TRANSFER leg.

RED on HEAD b48694f3f (every value quoted "HEAD:" in the docstrings): every test of the classes above except
``TestParityGuards``, ``TestApplyPoolRuleExternalLegs.test_an_asset_transfer_leg_moves_no_pool``,
``TestApplyPoolRuleExternalLegs.test_an_external_leg_never_touches_the_transfer_splits`` and
``TestBuyFundingAfterAnExternalLeg.test_without_withdrawn_returns_the_split_is_unchanged`` (declared parity pins).

Two existing tests pinned HEAD's rule and were repaired to this one with the fix:
``test_single_replay.py::TestApplyPoolRule::test_a_cash_transfer_that_is_not_linked_internal_moves_the_pools_as_a_deposit_or_withdrawal``
(formerly ``..._moves_no_pool``) and
``test_transfer_keeps_returns.py::TestApplyPoolRuleWithSplits::test_a_leg_that_is_not_linked_internal_neither_records_nor_takes_up_a_split``
(its pools half; the splits half is unchanged, as ``test_an_external_leg_never_touches_the_transfer_splits`` here).

Notation: target EUR; brokers A = 10, B = 20 (owned at 100 %); X = 100 a EUR stock; D0 = 2025-01-01 ... D4 =
2025-01-05. The perimeter is {B} unless a test says otherwise: A's leg, when there is one, is handed to the classifier
as ``external_paired``. Cash and pools are in EUR.

Pure tests — no DB, no server, no network. Helpers are copies of test_transfer_keeps_returns.py (this directory has no
cross-test-module imports).
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, PortfolioCalculationResult
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
DAYS = (D0, D1, D2, D3, D4)

ZERO = Decimal("0")

# =============================================================================
# HELPERS — copies of test_transfer_keeps_returns.py
# =============================================================================


def _tx(
    *,
    id: int,
    broker_id: int = B,
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


def _ctxn(tx: MagicMock, classification: str = "normal", paired: MagicMock | None = None) -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal("1"), paired_tx=paired)


def _usd_every_day(rate: str = "0.9") -> dict[tuple[str, str, date], Decimal]:
    """USD->EUR at one rate on every day D0..D4 (the map is exact-day): no exchange result on the cash at rest."""
    return {("USD", "EUR", day): Decimal(rate) for day in DAYS}


def _classify(txs, scope=frozenset({B}), *, external_paired=None):
    """Run the real classifier, transactions in loading order (date, id), every broker at share 1."""
    classifier = ScopeAwareTransactionClassifier(
        scope_broker_ids=set(scope),
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares=dict.fromkeys(scope, Decimal("1")),
    )
    return classifier.classify(external_paired=external_paired)


def _mark_series_from(classified_txs, asset_currencies):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from its trades (no quote here)."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        if ctxn.tx.asset_id is not None:
            txs_by_asset.setdefault(ctxn.tx.asset_id, []).append(ctxn.tx)
    mark_series = {}
    for aid, transactions in txs_by_asset.items():
        series = build_asset_price_series(price_rows=[], transactions=transactions, split_linked_tx_ids=set(), asset_currency=asset_currencies.get(aid, "EUR"), quote_base_quantity=1)
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _build(classification, *, date_to: date = D4, fx_rate_map=None, **builder_kwargs) -> PortfolioCalculationResult:
    """Build the states D0..date_to of a classified ledger; every asset is a EUR "Stock" with no classification.
    ``builder_kwargs`` reach DailyStateBuilder (``compute_acquisition_funding=True`` for the BUY split)."""
    fx_rate_map = fx_rate_map or {}
    classified = classification.classified
    asset_ids = {ctxn.tx.asset_id for ctxn in classified if ctxn.tx.asset_id is not None}
    asset_currencies = dict.fromkeys(asset_ids, "EUR")
    return DailyStateBuilder(
        classified_txs=classified,
        in_transit_intervals=classification.in_transit_intervals,
        external_cash_flows=classification.external_cash_flows,
        price_map={},
        quote_base_map={},
        fx_rate_map=fx_rate_map,
        asset_classifications=dict.fromkeys(asset_ids),
        asset_types=dict.fromkeys(asset_ids, "Stock"),
        asset_currencies=asset_currencies,
        mark_series=_mark_series_from(classified, asset_currencies),
        average_costs=engine_average_costs(classified, asset_currencies=asset_currencies, target_currency="EUR", fx_rate_map=fx_rate_map, date_to=date_to),
        native_cash=engine_native_cash(classified, target_currency="EUR", fx_rate_map=fx_rate_map, date_to=date_to),
        target_currency="EUR",
        date_from=D0,
        date_to=date_to,
        **builder_kwargs,
    ).build()


def _classifications(classification) -> dict[int, str]:
    return {ctxn.tx.id: ctxn.classification for ctxn in classification.classified}


def _breakdown_problems(result: PortfolioCalculationResult, expected: dict[date, tuple[str, str, str]]) -> list[str]:
    """``expected``: {day: (cash, cash_from_contributed_capital, cash_from_generated_returns)}. Collects every
    mismatch, so a red shows the whole line."""
    states = {s.date: s for s in result.daily_states}
    problems: list[str] = []
    for day, (cash, contributed, generated) in expected.items():
        state = states.get(day)
        if state is None:
            problems.append(f"{day}: no state emitted")
            continue
        actual = (state.cash_value + state.in_transit_cash_value, state.cash_from_contributed_capital, state.cash_from_generated_returns)
        if actual != (Decimal(cash), Decimal(contributed), Decimal(generated)):
            problems.append(f"{day}: (cash, contributed, generated)=({actual[0]}, {actual[1]}, {actual[2]}), expected ({cash}, {contributed}, {generated})")
    return problems


def _pool_problems(result: PortfolioCalculationResult, *, capital: str, returns: str, withdrawn: str | None = None, broker_id: int = B) -> list[str]:
    """B's K and R (and the global W) after the last day; a pool the replay never touched counts as 0. Also checks the
    pools reconcile with B's cash: with a EUR-only ledger K + R is the cash, no rescale needed."""
    end = result.end_state
    actual_k, actual_r = end.capital_pool.get(broker_id, ZERO), end.returns_pool.get(broker_id, ZERO)
    problems: list[str] = []
    if actual_k != Decimal(capital):
        problems.append(f"K[{broker_id}]={actual_k}, expected {capital}")
    if actual_r != Decimal(returns):
        problems.append(f"R[{broker_id}]={actual_r}, expected {returns}")
    if withdrawn is not None and end.withdrawn_pool != Decimal(withdrawn):
        problems.append(f"W={end.withdrawn_pool}, expected {withdrawn}")
    cash = end.cumulative_cash_by_broker.get(broker_id, ZERO)
    if cash >= ZERO and actual_k + actual_r != cash:
        problems.append(f"K[{broker_id}] + R[{broker_id}] = {actual_k + actual_r} != the broker's cash {cash}")
    return problems


def _funding(result: PortfolioCalculationResult, day: date) -> tuple[Decimal, Decimal] | None:
    state = next(s for s in result.daily_states if s.date == day)
    funding = state.acquisition_funding
    return None if funding is None else (funding.from_new_capital, funding.from_reinvested)


# ── B's own history: K 100 / R 100 by D1 ──


def _b_returns_by_income() -> list[MagicMock]:
    """B deposits 100 on D0 and earns 100 of INTEREST on D1: K_B 100, R_B 100, cash 200."""
    return [_tx(id=1, dt=D0, amount="100"), _tx(id=2, type="INTEREST", dt=D1, amount="100")]


def _b_returns_by_realized_gain() -> list[MagicMock]:
    """B deposits 100 and buys 5 X for 100 on D0, sells them for 200 on D1 (cost 100, gain 100): K_B 100, R_B 100."""
    return [
        _tx(id=1, dt=D0, amount="100"),
        _tx(id=2, type="BUY", dt=D0, amount="-100", quantity="5", asset_id=X),
        _tx(id=3, type="SELL", dt=D1, amount="200", quantity="-5", asset_id=X),
    ]


def _b_with_withdrawn_returns() -> list[MagicMock]:
    """K 100 / R 100 by D0 (deposit and interest), then a WITHDRAWAL of 150 on D1: K first (100), then R (50) -> W 50.
    K_B 0, R_B 50, W 50, cash 50."""
    return [_tx(id=1, dt=D0, amount="100"), _tx(id=2, type="INTEREST", dt=D0, amount="100"), _tx(id=3, type="WITHDRAWAL", dt=D1, amount="-150")]


_HISTORIES = [pytest.param(_b_returns_by_income, id="interest"), pytest.param(_b_returns_by_realized_gain, id="realized_gain")]


def _from_a(amount: str, *, dt: date = D2, out_id: int = 50, in_id: int = 51, type: str = "CASH_TRANSFER") -> tuple[MagicMock, dict]:
    """The leg arriving at B from A (outside {B}), and A's leg as ``external_paired``."""
    out_leg = _tx(id=out_id, broker_id=A, type=type, dt=dt, amount=f"-{amount}", related_id=in_id)
    in_leg = _tx(id=in_id, broker_id=B, type=type, dt=dt, amount=amount, related_id=out_id)
    return in_leg, {out_id: out_leg}


def _to_a(amount: str, *, dt: date = D2, out_id: int = 60, in_id: int = 61, type: str = "CASH_TRANSFER") -> tuple[MagicMock, dict]:
    """The leg leaving B for A (outside {B}), and A's leg as ``external_paired``."""
    out_leg = _tx(id=out_id, broker_id=B, type=type, dt=dt, amount=f"-{amount}", related_id=in_id)
    in_leg = _tx(id=in_id, broker_id=A, type=type, dt=dt, amount=amount, related_id=out_id)
    return out_leg, {in_id: in_leg}


# =============================================================================
# (a) (b) — AN INFLOW FROM OUTSIDE THE PERIMETER
# =============================================================================


class TestInflowFromOutsideThePerimeter:
    def test_into_an_empty_broker_it_is_all_capital(self):
        """(a) Perimeter {B}, B empty; 650 arrive from A on D2 (``linked_external_inflow``, capital baseline 650).

        Rule: as a DEPOSIT with W 0 -> K_B 650, R_B 0; D2..D4 cash 650 = contributed 650 + generated 0.
        HEAD: the pools stay empty, so the breakdown reads contributed 0 / generated 650; K_B 0, R_B 0.
        """
        in_leg, external = _from_a("650")
        classification = _classify([in_leg], external_paired=external)
        assert _classifications(classification) == {51: "linked_external_inflow"}

        result = _build(classification)

        problems = _breakdown_problems(result, {D2: ("650", "650", "0"), D3: ("650", "650", "0"), D4: ("650", "650", "0")})
        problems += _pool_problems(result, capital="650", returns="0", withdrawn="0")
        assert not problems, "\n".join(problems)

    @pytest.mark.parametrize("history", _HISTORIES)
    def test_into_a_broker_with_returns_the_returns_stay(self, history):
        """(b) B holds K 100 / R 100 on D1 (by income or by a realized gain); +650 from A on D2.

        Rule: K_B 750, R_B 100; D2..D4 cash 850 = contributed 750 + generated 100.
        HEAD: pools K 100 / R 100 against a cash of 850, rescaled x 4.25: contributed 425 / generated 425.
        """
        in_leg, external = _from_a("650")
        classification = _classify([*history(), in_leg], external_paired=external)
        assert _classifications(classification)[51] == "linked_external_inflow"

        result = _build(classification)

        problems = _breakdown_problems(result, {D1: ("200", "100", "100"), D2: ("850", "750", "100"), D4: ("850", "750", "100")})
        problems += _pool_problems(result, capital="750", returns="100", withdrawn="0")
        assert not problems, "\n".join(problems)


# =============================================================================
# (c) — AN OUTFLOW, AND THE WITHDRAWN RETURNS
# =============================================================================


class TestOutflowAndWithdrawnReturns:
    def test_an_outflow_leaves_capital_first_then_returns_into_withdrawn(self):
        """(c) B holds K 100 / R 100 (income); 150 leave B for A on D2 (``linked_external_outflow``).

        Rule: as a WITHDRAWAL -> K_B 0 (100), R_B 50 (50 from R), W 50; D2 cash 50 = contributed 0 + generated 50.
        HEAD: pools K 100 / R 100 against a cash of 50, rescaled x 0.25: contributed 25 / generated 25; W 0.
        """
        out_leg, external = _to_a("150")
        classification = _classify([*_b_returns_by_income(), out_leg], external_paired=external)
        assert _classifications(classification)[60] == "linked_external_outflow"

        result = _build(classification)

        problems = _breakdown_problems(result, {D2: ("50", "0", "50"), D4: ("50", "0", "50")})
        problems += _pool_problems(result, capital="0", returns="50", withdrawn="50")
        assert not problems, "\n".join(problems)

    def test_a_deposit_after_the_outflow_restores_the_withdrawn_returns(self):
        """(c) As above, then a real DEPOSIT of 100 on D3: it restores W 50 into R first, the other 50 into K.

        Rule: K_B 50, R_B 100, W 0; D3 cash 150 = contributed 50 + generated 100.
        HEAD: W was 0, so the deposit is all K: pools K 200 / R 100 against 150, x 0.5: contributed 100 / generated 50.
        """
        out_leg, external = _to_a("150")
        deposit = _tx(id=70, dt=D3, amount="100")
        result = _build(_classify([*_b_returns_by_income(), out_leg, deposit], external_paired=external))

        problems = _breakdown_problems(result, {D2: ("50", "0", "50"), D3: ("150", "50", "100"), D4: ("150", "50", "100")})
        problems += _pool_problems(result, capital="50", returns="100", withdrawn="0")
        assert not problems, "\n".join(problems)

    def test_an_inflow_restores_the_withdrawn_returns_too(self):
        """(c) K 0 / R 50 / W 50 after a real WITHDRAWAL of 150 on D1; +100 from A on D2.

        Rule: as a DEPOSIT -> 50 restores W into R, 50 into K: K_B 50, R_B 100, W 0; D2 cash 150 = 50 + 100.
        HEAD: the pools stay K 0 / R 50 against a cash of 150, x 3: contributed 0 / generated 150; W 50.
        """
        in_leg, external = _from_a("100")
        classification = _classify([*_b_with_withdrawn_returns(), in_leg], external_paired=external)
        assert _classifications(classification)[51] == "linked_external_inflow"

        result = _build(classification)

        problems = _breakdown_problems(result, {D1: ("50", "0", "50"), D2: ("150", "50", "100"), D4: ("150", "50", "100")})
        problems += _pool_problems(result, capital="50", returns="100", withdrawn="0")
        assert not problems, "\n".join(problems)


# =============================================================================
# (d) — THE BUY FUNDING SPLIT AFTER AN EXTERNAL LEG
# =============================================================================


def _buy_x(amount: str, quantity: str, *, id: int = 80, dt: date = D3) -> MagicMock:
    return _tx(id=id, type="BUY", dt=dt, amount=f"-{amount}", quantity=quantity, asset_id=X)


class TestBuyFundingAfterAnExternalLeg:
    @pytest.mark.parametrize("orphan", [pytest.param(False, id="from_A_outside_the_perimeter"), pytest.param(True, id="orphan_leg")])
    def test_after_an_inflow_that_restores_withdrawn_returns_the_buy_is_reinvested(self, orphan):
        """(d) K 0 / R 50 / W 50 on D1 (``_b_with_withdrawn_returns``); +100 on D2, from A or an orphan CASH_TRANSFER;
        a BUY of 2 X for 100 on D3 draws R first, then K.

        Rule: the inflow restores W -> R 100, K 50; the BUY: from_reinvested 100, from_new_capital 0.
        HEAD: R 50, K 0 -> from_reinvested 50, from_new_capital 50.
        """
        if orphan:
            in_leg, external = _tx(id=51, type="CASH_TRANSFER", dt=D2, amount="100"), None
        else:
            in_leg, external = _from_a("100")
        classification = _classify([*_b_with_withdrawn_returns(), in_leg, _buy_x("100", "2")], external_paired=external)
        assert _classifications(classification)[51] == ("normal" if orphan else "linked_external_inflow")

        result = _build(classification, compute_acquisition_funding=True)

        assert _funding(result, D3) == (Decimal("0"), Decimal("100")), f"(from_new_capital, from_reinvested) on D3: {_funding(result, D3)}, expected (0, 100)"

    def test_after_an_outflow_an_overdrawn_buy_takes_capital(self):
        """(d) K 100 / R 100 (income); 150 leave for A on D2 (cash 50); a BUY of 4 X for 80 on D3 overdraws B.

        Rule: the outflow leaves K 0 / R 50 -> the BUY: from_reinvested 50, from_new_capital 30.
        HEAD: R still 100 -> from_reinvested 80, from_new_capital 0.
        """
        out_leg, external = _to_a("150")
        result = _build(_classify([*_b_returns_by_income(), out_leg, _buy_x("80", "4")], external_paired=external), compute_acquisition_funding=True)

        assert _funding(result, D3) == (Decimal("30"), Decimal("50")), f"(from_new_capital, from_reinvested) on D3: {_funding(result, D3)}, expected (30, 50)"

    def test_without_withdrawn_returns_the_split_is_unchanged(self):
        """Parity pin. (d) B holds K 100 / R 100; +650 from A on D2; a BUY of 10 X for 400 on D3: R first (100), then K
        (300), whether the inflow went to K (rule) or nowhere (HEAD): from_reinvested 100, from_new_capital 300."""
        in_leg, external = _from_a("650")
        result = _build(_classify([*_b_returns_by_income(), in_leg, _buy_x("400", "10")], external_paired=external), compute_acquisition_funding=True)

        assert _funding(result, D3) == (Decimal("300"), Decimal("100"))


# =============================================================================
# (e) — AN ORPHAN CASH_TRANSFER
# =============================================================================

# related_transaction_id None (the link cleared with the other broker), or pointing at a row that is not found
_ORPHANS = [pytest.param(None, id="link_cleared"), pytest.param(999, id="pair_not_found")]


class TestOrphanCashTransfer:
    @pytest.mark.parametrize("related_id", _ORPHANS)
    def test_an_orphan_inflow_then_outflow(self, related_id):
        """(e) B holds K 100 / R 100 (income); an orphan CASH_TRANSFER +300 on D2 and -200 on D3 (``normal``, each an
        external flow: capital baseline 100 -> 400 -> 200).

        Rule: +300 as a DEPOSIT -> K 400 / R 100 (D2: 500 = 400 + 100); -200 as a WITHDRAWAL -> K 200 / R 100
        (D3: 300 = 200 + 100); W 0.
        HEAD: pools K 100 / R 100 throughout, rescaled: D2 x 2.5 -> 250 / 250; D3 x 1.5 -> 150 / 150.
        """
        inflow = _tx(id=51, type="CASH_TRANSFER", dt=D2, amount="300", related_id=related_id)
        outflow = _tx(id=52, type="CASH_TRANSFER", dt=D3, amount="-200", related_id=None if related_id is None else related_id + 1)
        classification = _classify([*_b_returns_by_income(), inflow, outflow])
        assert _classifications(classification)[51] == _classifications(classification)[52] == "normal"

        result = _build(classification)

        problems = _breakdown_problems(result, {D2: ("500", "400", "100"), D3: ("300", "200", "100"), D4: ("300", "200", "100")})
        problems += _pool_problems(result, capital="200", returns="100", withdrawn="0")
        assert not problems, "\n".join(problems)

    def test_an_orphan_outflow_beyond_capital_moves_returns_to_withdrawn(self):
        """(e) B holds K 100 / R 100; an orphan CASH_TRANSFER -150 on D2, as (c).

        Rule: K 0 / R 50 / W 50; D2 cash 50 = 0 + 50. HEAD: x 0.25 -> 25 / 25; W 0.
        """
        outflow = _tx(id=52, type="CASH_TRANSFER", dt=D2, amount="-150")
        result = _build(_classify([*_b_returns_by_income(), outflow]))

        problems = _breakdown_problems(result, {D2: ("50", "0", "50")})
        problems += _pool_problems(result, capital="0", returns="50", withdrawn="50")
        assert not problems, "\n".join(problems)


# =============================================================================
# (f) — AN ORPHAN FX_CONVERSION LEG
# =============================================================================


class TestOrphanFxConversion:
    @pytest.mark.parametrize("related_id", _ORPHANS)
    def test_the_eur_leg_of_a_conversion_whose_other_leg_is_gone(self, related_id):
        """(f) B holds K 100 / R 100 (income); +300 EUR on D2, the surviving leg of a conversion (``normal``).

        Rule: as a DEPOSIT -> K 400 / R 100; D2 cash 500 = 400 + 100. HEAD: x 2.5 -> 250 / 250.
        """
        leg = _tx(id=51, type="FX_CONVERSION", dt=D2, amount="300", related_id=related_id)
        classification = _classify([*_b_returns_by_income(), leg])
        assert _classifications(classification)[51] == "normal"

        result = _build(classification)

        problems = _breakdown_problems(result, {D2: ("500", "400", "100"), D4: ("500", "400", "100")})
        problems += _pool_problems(result, capital="400", returns="100", withdrawn="0")
        assert not problems, "\n".join(problems)

    def test_a_usd_inflow_leg(self):
        """(f) B holds K 100 / R 100 EUR; an orphan FX_CONVERSION +200 USD on D2, USD->EUR 0.9 on every day (180 EUR, no
        exchange result afterwards).

        Rule: K 280 / R 100; D2 cash 380 = 280 + 100. HEAD: pools 200 against 380, x 1.9: 190 / 190.
        """
        leg = _tx(id=51, type="FX_CONVERSION", dt=D2, amount="200", currency="USD")
        result = _build(_classify([*_b_returns_by_income(), leg]), fx_rate_map=_usd_every_day())

        problems = _breakdown_problems(result, {D2: ("380", "280", "100"), D4: ("380", "280", "100")})
        end = result.end_state
        if (end.capital_pool.get(B, ZERO), end.returns_pool.get(B, ZERO)) != (Decimal("280"), Decimal("100")):
            problems.append(f"(K_B, R_B)=({end.capital_pool.get(B, ZERO)}, {end.returns_pool.get(B, ZERO)}), expected (280, 100)")
        assert not problems, "\n".join(problems)

    def test_a_usd_outflow_leg(self):
        """(f) B holds K 100 / R 100 EUR; an orphan FX_CONVERSION -100 USD on D2 (90 EUR at 0.9): B's USD cash goes -100.

        Rule: as a WITHDRAWAL of 90 -> K 10 / R 100; D2 cash 110 = 10 + 100. HEAD: pools 200 against 110, x 0.55:
        55 / 55.
        """
        leg = _tx(id=51, type="FX_CONVERSION", dt=D2, amount="-100", currency="USD")
        result = _build(_classify([*_b_returns_by_income(), leg]), fx_rate_map=_usd_every_day())

        problems = _breakdown_problems(result, {D2: ("110", "10", "100"), D4: ("110", "10", "100")})
        end = result.end_state
        if (end.capital_pool.get(B, ZERO), end.returns_pool.get(B, ZERO)) != (Decimal("10"), Decimal("100")):
            problems.append(f"(K_B, R_B)=({end.capital_pool.get(B, ZERO)}, {end.returns_pool.get(B, ZERO)}), expected (10, 100)")
        assert not problems, "\n".join(problems)


# =============================================================================
# THE RULE AS AN EQUIVALENCE — every scenario against its DEPOSIT / WITHDRAWAL twin
# =============================================================================


def _twin(leg: MagicMock) -> MagicMock:
    """The same movement as a DEPOSIT (amount > 0) or a WITHDRAWAL (amount < 0), unlinked: same id, broker, day,
    amount and currency."""
    return _tx(id=leg.id, broker_id=leg.broker_id, type="DEPOSIT" if leg.amount > 0 else "WITHDRAWAL", dt=leg.date, amount=str(leg.amount), currency=leg.currency)


def _case_from_a(history, amount, *, followers=()):
    def make():
        in_leg, external = _from_a(amount)
        return [*history(), *followers], [in_leg], external

    return make


def _case_to_a(history, amount, *, followers=()):
    def make():
        out_leg, external = _to_a(amount)
        return [*history(), *followers], [out_leg], external

    return make


def _case_orphans(history, *legs: tuple[str, str, date, str]):
    """Orphan legs (type, amount, day, currency), ids 51, 52, ..."""

    def make():
        txs = [_tx(id=51 + i, type=tx_type, dt=day, amount=amount, currency=currency) for i, (tx_type, amount, day, currency) in enumerate(legs)]
        return list(history()), txs, None

    return make


def _empty() -> list:
    return []


_TWIN_CASES = [
    pytest.param(_case_from_a(_empty, "650"), id="a_inflow_into_empty_broker"),
    pytest.param(_case_from_a(_b_returns_by_income, "650"), id="b_inflow_with_returns"),
    pytest.param(_case_from_a(_b_returns_by_realized_gain, "650"), id="b_inflow_with_realized_gain"),
    pytest.param(_case_from_a(_b_with_withdrawn_returns, "100"), id="c_inflow_restores_withdrawn"),
    pytest.param(_case_from_a(_b_with_withdrawn_returns, "30"), id="c_inflow_within_withdrawn"),
    pytest.param(_case_to_a(_b_returns_by_income, "60"), id="c_outflow_within_capital"),
    pytest.param(_case_to_a(_b_returns_by_income, "150"), id="c_outflow_into_returns"),
    pytest.param(_case_to_a(_b_returns_by_income, "150", followers=(_tx(id=70, dt=D3, amount="100"),)), id="c_outflow_then_deposit"),
    pytest.param(_case_to_a(_b_returns_by_income, "300"), id="c_outflow_beyond_the_cash"),
    pytest.param(_case_from_a(_b_with_withdrawn_returns, "100", followers=(_buy_x("100", "2"),)), id="d_inflow_then_buy"),
    pytest.param(_case_to_a(_b_returns_by_income, "150", followers=(_buy_x("80", "4"),)), id="d_outflow_then_buy"),
    pytest.param(_case_orphans(_b_returns_by_income, ("CASH_TRANSFER", "300", D2, "EUR"), ("CASH_TRANSFER", "-200", D3, "EUR")), id="e_orphan_cash_transfer"),
    pytest.param(_case_orphans(_b_with_withdrawn_returns, ("CASH_TRANSFER", "80", D2, "EUR")), id="e_orphan_restores_withdrawn"),
    pytest.param(_case_orphans(_b_returns_by_income, ("FX_CONVERSION", "300", D2, "EUR"), ("FX_CONVERSION", "-250", D3, "EUR")), id="f_orphan_fx_eur"),
    pytest.param(_case_orphans(_b_returns_by_income, ("FX_CONVERSION", "200", D2, "USD"), ("FX_CONVERSION", "-100", D3, "USD")), id="f_orphan_fx_usd"),
]


def _observed(result: PortfolioCalculationResult) -> dict:
    end = result.end_state
    return {
        "days": [(s.date, s.cash_value, s.cash_from_contributed_capital, s.cash_from_generated_returns, None if s.acquisition_funding is None else (s.acquisition_funding.from_new_capital, s.acquisition_funding.from_reinvested)) for s in result.daily_states],
        "K": {bid: v for bid, v in end.capital_pool.items() if v != ZERO},
        "R": {bid: v for bid, v in end.returns_pool.items() if v != ZERO},
        "W": end.withdrawn_pool,
    }


class TestSameAsDepositOrWithdrawal:
    @pytest.mark.parametrize("case", _TWIN_CASES)
    def test_pools_breakdown_and_buy_funding_match_the_twin(self, case):
        """The leg(s) against the same ledger with each leg replaced by a DEPOSIT / WITHDRAWAL of the same amount: the
        decided rule says the pools must move identically, so K, R, W, the cash breakdown and the BUY split coincide
        on every day. HEAD: they differ on every case (the leg moves no pool)."""
        history, legs, external = case()
        fx = _usd_every_day() if any(leg.currency == "USD" for leg in legs) else None
        with_legs = _build(_classify([*history, *legs], external_paired=external), fx_rate_map=fx, compute_acquisition_funding=True)
        history_twin, legs_twin, _ = case()  # fresh mocks for the twin ledger
        with_twins = _build(_classify([*history_twin, *(_twin(leg) for leg in legs_twin)]), fx_rate_map=fx, compute_acquisition_funding=True)

        observed, expected = _observed(with_legs), _observed(with_twins)
        problems = [f"{key}: leg {observed[key]} != twin {expected[key]}" for key in ("K", "R", "W") if observed[key] != expected[key]]
        problems += [f"{leg_day[0]}: leg {leg_day[1:]} != twin {twin_day[1:]}" for leg_day, twin_day in zip(observed["days"], expected["days"], strict=True) if leg_day != twin_day]
        assert not problems, "\n".join(problems)


# =============================================================================
# _apply_pool_rule ON A LEG THAT IS NOT LINKED-INTERNAL, PURE
# =============================================================================


def _pools(capital: dict[int, str], returns: dict[int, str]) -> tuple[defaultdict, defaultdict]:
    """K and R as the replay holds them (defaultdicts)."""
    return defaultdict(Decimal, {bid: Decimal(v) for bid, v in capital.items()}), defaultdict(Decimal, {bid: Decimal(v) for bid, v in returns.items()})


def _external_leg(tx_type: str, classification: str, signed_amount: str) -> ClassifiedTransaction:
    """A leg at B; a linked-external one names A's leg as its pair, a ``normal`` one has none."""
    paired = None if classification == "normal" else _tx(id=4, broker_id=A, type=tx_type, dt=D1, amount=str(-Decimal(signed_amount)), related_id=3)
    tx = _tx(id=3, type=tx_type, dt=D1, amount=signed_amount, related_id=None if paired is None else 4)
    return _ctxn(tx, classification, paired=paired)


_CASH_LEG_TYPES = pytest.mark.parametrize("tx_type", ["CASH_TRANSFER", "FX_CONVERSION"])
_INFLOW_CLASSES = pytest.mark.parametrize("classification", ["normal", "linked_external_inflow"])
_OUTFLOW_CLASSES = pytest.mark.parametrize("classification", ["normal", "linked_external_outflow"])


def _d(value: str) -> Decimal:
    return Decimal(value)


class TestApplyPoolRuleExternalLegs:
    """``_apply_pool_rule(ctxn, amount, K, R, withdrawn, transfer_splits)``: ``amount`` is the leg's absolute value in
    the target currency, the direction is the sign of ``tx.amount``. Returns (withdrawn, buy_from_k, buy_from_r)."""

    @_CASH_LEG_TYPES
    @_INFLOW_CLASSES
    def test_an_inflow_without_withdrawn_returns_is_capital(self, tx_type, classification):
        """K 100 / R 40, W 0, +60 -> K 160, R 40, W 0. HEAD: K 100, R 40."""
        capital, returns = _pools({B: "100"}, {B: "40"})
        after = DailyStateBuilder._apply_pool_rule(_external_leg(tx_type, classification, "60"), _d("60"), capital, returns, _d("0"), {})
        assert (after, capital[B], returns[B]) == ((_d("0"), _d("0"), _d("0")), _d("160"), _d("40"))

    @_CASH_LEG_TYPES
    @_INFLOW_CLASSES
    def test_an_inflow_restores_withdrawn_returns_first(self, tx_type, classification):
        """K 100 / R 40, W 25, +60 -> 25 back into R, 35 into K: K 135, R 65, W 0. HEAD: K 100, R 40, W 25."""
        capital, returns = _pools({B: "100"}, {B: "40"})
        after = DailyStateBuilder._apply_pool_rule(_external_leg(tx_type, classification, "60"), _d("60"), capital, returns, _d("25"), {})
        assert (after, capital[B], returns[B]) == ((_d("0"), _d("0"), _d("0")), _d("135"), _d("65"))

    @_CASH_LEG_TYPES
    @_INFLOW_CLASSES
    def test_an_inflow_smaller_than_withdrawn_returns_is_all_returns(self, tx_type, classification):
        """K 100 / R 40, W 90, +60 -> all 60 back into R: K 100, R 100, W 30. HEAD: K 100, R 40, W 90."""
        capital, returns = _pools({B: "100"}, {B: "40"})
        after = DailyStateBuilder._apply_pool_rule(_external_leg(tx_type, classification, "60"), _d("60"), capital, returns, _d("90"), {})
        assert (after, capital[B], returns[B]) == ((_d("30"), _d("0"), _d("0")), _d("100"), _d("100"))

    @_CASH_LEG_TYPES
    @_OUTFLOW_CLASSES
    def test_an_outflow_within_capital_leaves_capital(self, tx_type, classification):
        """K 100 / R 40, W 5, -60 -> K 40, R 40, W 5. HEAD: K 100, R 40."""
        capital, returns = _pools({B: "100"}, {B: "40"})
        after = DailyStateBuilder._apply_pool_rule(_external_leg(tx_type, classification, "-60"), _d("60"), capital, returns, _d("5"), {})
        assert (after, capital[B], returns[B]) == ((_d("5"), _d("0"), _d("0")), _d("40"), _d("40"))

    @_CASH_LEG_TYPES
    @_OUTFLOW_CLASSES
    def test_an_outflow_beyond_capital_moves_returns_into_withdrawn(self, tx_type, classification):
        """K 100 / R 40, W 5, -130 -> K 0, R 10 (30 from R), W 35. HEAD: K 100, R 40, W 5."""
        capital, returns = _pools({B: "100"}, {B: "40"})
        after = DailyStateBuilder._apply_pool_rule(_external_leg(tx_type, classification, "-130"), _d("130"), capital, returns, _d("5"), {})
        assert (after, capital[B], returns[B]) == ((_d("35"), _d("0"), _d("0")), _d("0"), _d("10"))

    @_CASH_LEG_TYPES
    @_OUTFLOW_CLASSES
    def test_an_outflow_beyond_both_pools_empties_them(self, tx_type, classification):
        """K 100 / R 40, W 0, -300 -> K 0, R 0, W 40 (what R held): the 160 beyond the pools leaves no pool, as a
        WITHDRAWAL. HEAD: K 100, R 40, W 0."""
        capital, returns = _pools({B: "100"}, {B: "40"})
        after = DailyStateBuilder._apply_pool_rule(_external_leg(tx_type, classification, "-300"), _d("300"), capital, returns, _d("0"), {})
        assert (after, capital[B], returns[B]) == ((_d("40"), _d("0"), _d("0")), _d("0"), _d("0"))

    @_CASH_LEG_TYPES
    @pytest.mark.parametrize(("classification", "signed_amount"), [("normal", "60"), ("normal", "-60"), ("linked_external_inflow", "60"), ("linked_external_outflow", "-60")])
    def test_the_leg_matches_its_deposit_or_withdrawal(self, tx_type, classification, signed_amount):
        """The same pools and W, leg against a DEPOSIT / WITHDRAWAL of the same amount. HEAD: the leg moves nothing."""
        twin_type = "DEPOSIT" if Decimal(signed_amount) > 0 else "WITHDRAWAL"
        capital, returns = _pools({B: "100"}, {B: "40"})
        twin_capital, twin_returns = _pools({B: "100"}, {B: "40"})
        after = DailyStateBuilder._apply_pool_rule(_external_leg(tx_type, classification, signed_amount), _d("60"), capital, returns, _d("25"), {})
        twin_after = DailyStateBuilder._apply_pool_rule(_ctxn(_tx(id=9, type=twin_type, dt=D1, amount=signed_amount)), _d("60"), twin_capital, twin_returns, _d("25"), {})
        assert (after, dict(capital), dict(returns)) == (twin_after, dict(twin_capital), dict(twin_returns))

    @_CASH_LEG_TYPES
    @pytest.mark.parametrize(("classification", "signed_amount"), [("normal", "60"), ("normal", "-60"), ("linked_external_inflow", "60"), ("linked_external_outflow", "-60")])
    def test_an_external_leg_never_touches_the_transfer_splits(self, tx_type, classification, signed_amount):
        """Parity pin: J2's splits belong to linked-internal pairs only; a recorded departure stays for its arrival."""
        splits = {4: (_d("40"), _d("60")), 99: (_d("1"), _d("2"))}
        capital, returns = _pools({B: "100"}, {B: "40"})
        DailyStateBuilder._apply_pool_rule(_external_leg(tx_type, classification, signed_amount), _d("60"), capital, returns, _d("5"), splits)
        assert splits == {4: (_d("40"), _d("60")), 99: (_d("1"), _d("2"))}

    @pytest.mark.parametrize(("classification", "quantity"), [("linked_external_inflow", "5"), ("linked_external_outflow", "-5"), ("normal", "5")])
    def test_an_asset_transfer_leg_moves_no_pool(self, classification, quantity):
        """Parity pin: the pools are cash; an asset TRANSFER leg (amount 0), whatever its classification, leaves K, R
        and W as they were."""
        paired = None if classification == "normal" else _tx(id=4, broker_id=A, type="TRANSFER", dt=D1, quantity=str(-Decimal(quantity)), asset_id=X, related_id=3)
        ctxn = _ctxn(_tx(id=3, type="TRANSFER", dt=D1, quantity=quantity, asset_id=X, related_id=None if paired is None else 4), classification, paired=paired)
        capital, returns = _pools({B: "100"}, {B: "40"})
        after = DailyStateBuilder._apply_pool_rule(ctxn, _d("0"), capital, returns, _d("5"), {})
        assert (after, capital[B], returns[B]) == ((_d("5"), _d("0"), _d("0")), _d("100"), _d("40"))


# =============================================================================
# (g) — PARITY GUARDS: green before and after
# =============================================================================


def _ledger(history, legs, *, followers=(), fx=None):
    """A scenario for the parity guards: B's history, the leg(s) as ``(tx, external_paired)``, later movements."""

    def make():
        txs, external = list(history()), {}
        for leg, paired in (leg_factory() for leg_factory in legs):
            txs.append(leg)
            external.update(paired or {})
        return [*txs, *followers], external or None, fx

    return make


def _orphan(tx_id: int, tx_type: str, amount: str, day: date, currency: str = "EUR"):
    return lambda: (_tx(id=tx_id, type=tx_type, dt=day, amount=amount, currency=currency), None)


_BASELINE_LEDGERS = {
    "a": _ledger(_empty, [lambda: _from_a("650")]),
    "b": _ledger(_b_returns_by_income, [lambda: _from_a("650")]),
    "c_outflow_then_deposit": _ledger(_b_returns_by_income, [lambda: _to_a("150")], followers=(_tx(id=70, dt=D3, amount="100"),)),
    "c_inflow_restores": _ledger(_b_with_withdrawn_returns, [lambda: _from_a("100")]),
    "e": _ledger(_b_returns_by_income, [_orphan(51, "CASH_TRANSFER", "300", D2), _orphan(52, "CASH_TRANSFER", "-200", D3)]),
    "f_usd": _ledger(_b_returns_by_income, [_orphan(51, "FX_CONVERSION", "200", D2, "USD")], fx=_usd_every_day()),
}


# {scenario: {day: (capital baseline, NAV)}} — the same on HEAD and under the rule
_BASELINE_AND_NAV = {
    "a": {D1: ("0", "0"), D2: ("650", "650"), D4: ("650", "650")},
    "b": {D1: ("100", "200"), D2: ("750", "850"), D4: ("750", "850")},
    "c_outflow_then_deposit": {D2: ("-50", "50"), D3: ("50", "150"), D4: ("50", "150")},
    "c_inflow_restores": {D1: ("-50", "50"), D2: ("50", "150"), D4: ("50", "150")},
    "e": {D2: ("400", "500"), D3: ("200", "300"), D4: ("200", "300")},
    "f_usd": {D2: ("280", "380"), D4: ("280", "380")},
}


class TestParityGuards:
    """Green on HEAD and after the rule: what the rule must not change."""

    @pytest.mark.parametrize("scenario", sorted(_BASELINE_AND_NAV))
    def test_capital_baseline_nav_and_pnl_do_not_move(self, scenario):
        txs, external, fx = _BASELINE_LEDGERS[scenario]()
        result = _build(_classify(txs, external_paired=external), fx_rate_map=fx)
        states = {s.date: s for s in result.daily_states}
        problems = []
        for day, (baseline, nav) in _BASELINE_AND_NAV[scenario].items():
            state = states[day]
            actual = (state.cumulative_external_cash_flow, state.nav_value, state.total_pnl)
            expected = (Decimal(baseline), Decimal(nav), Decimal(nav) - Decimal(baseline))
            if actual != expected:
                problems.append(f"{scenario} {day}: (baseline, NAV, P&L)={actual}, expected {expected}")
        assert not problems, "\n".join(problems)

    @pytest.mark.parametrize("case", _TWIN_CASES)
    def test_the_pools_and_the_breakdown_never_go_below_zero(self, case):
        """K, R ≥ 0 at the end, and both halves of the cash breakdown ≥ 0 on every day the scope's cash is not negative."""
        history, legs, external = case()
        fx = _usd_every_day() if any(leg.currency == "USD" for leg in legs) else None
        result = _build(_classify([*history, *legs], external_paired=external), fx_rate_map=fx)
        end = result.end_state
        problems = [f"K[{bid}]={v} < 0" for bid, v in end.capital_pool.items() if v < ZERO]
        problems += [f"R[{bid}]={v} < 0" for bid, v in end.returns_pool.items() if v < ZERO]
        problems += [f"W={end.withdrawn_pool} < 0"] if end.withdrawn_pool < ZERO else []
        for s in result.daily_states:
            if s.cash_value >= ZERO and (s.cash_from_contributed_capital < ZERO or s.cash_from_generated_returns < ZERO):
                problems.append(f"{s.date}: cash {s.cash_value} = {s.cash_from_contributed_capital} + {s.cash_from_generated_returns}")
        assert not problems, "\n".join(problems)

    def test_a_linked_internal_pair_keeps_j2(self):
        """Perimeter {A, B}: A holds K 1000 / R 300 (deposit, interest); A -> B 650 on D2 (both ``linked_internal``):
        J2's numbers, K {A 650, B 350}, R {A 0, B 300}; contributed 1000 / generated 300; W 0."""
        a_txs = [_tx(id=1, broker_id=A, dt=D0, amount="1000"), _tx(id=2, broker_id=A, type="INTEREST", dt=D1, amount="300")]
        out_leg = _tx(id=4, broker_id=A, type="CASH_TRANSFER", dt=D2, amount="-650", related_id=5)
        in_leg = _tx(id=5, broker_id=B, type="CASH_TRANSFER", dt=D2, amount="650", related_id=4)
        classification = _classify([*a_txs, out_leg, in_leg], {A, B})
        assert _classifications(classification)[4] == _classifications(classification)[5] == "linked_internal"

        result = _build(classification)

        problems = _breakdown_problems(result, {D2: ("1300", "1000", "300"), D4: ("1300", "1000", "300")})
        end = result.end_state
        pools = ({bid: end.capital_pool.get(bid, ZERO) for bid in (A, B)}, {bid: end.returns_pool.get(bid, ZERO) for bid in (A, B)}, end.withdrawn_pool)
        if pools != ({A: Decimal("650"), B: Decimal("350")}, {A: Decimal("0"), B: Decimal("300")}, ZERO):
            problems.append(f"(K, R, W)={pools}")
        assert not problems, "\n".join(problems)

    def test_deposits_and_withdrawals_alone_are_unchanged(self):
        """B: DEPOSIT 100, INTEREST 100 (D0), WITHDRAWAL 150 (D1: K 0, R 50, W 50), DEPOSIT 100 (D2: W back into R,
        K 50 / R 100 / W 0): D1 50 = 0 + 50, D2 150 = 50 + 100."""
        result = _build(_classify([*_b_with_withdrawn_returns(), _tx(id=4, dt=D2, amount="100")]))

        problems = _breakdown_problems(result, {D1: ("50", "0", "50"), D2: ("150", "50", "100"), D4: ("150", "50", "100")})
        problems += _pool_problems(result, capital="50", returns="100", withdrawn="0")
        assert not problems, "\n".join(problems)
