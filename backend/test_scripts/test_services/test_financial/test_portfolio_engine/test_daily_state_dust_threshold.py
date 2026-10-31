"""MF6-2 (backlog MF-A6) — the daily state holds a position only above ``QUANTITY_DUST_THRESHOLD``.

What changes. ``DailyStateBuilder.build`` (``backend/app/services/financial_math/portfolio/daily_state.py``) values
every quantity > 0 — the valuation loop (step 4c), the start snapshot (``position_states_start``) and the end snapshot
(``position_states_end``) — while the Performance rows (``PortfolioService.get_positions_contribution``) and the
position series (``financial_math/portfolio/position_series.py``) treat a quantity ≤ ``QUANTITY_DUST_THRESHOLD``
(0.00001) as not held. The fix gives the daily state the same predicate, ``qty > QUANTITY_DUST_THRESHOLD``, in those
three places: a dust residual then counts nothing in ``market_value``, ``open_cost_basis``, ``nav_value``,
``by_asset``/``by_type``, the broker's ``nav_contribution``, the position frames, the snapshots, and a dust residual
with no price no longer makes the day MISSING.

The book (pure: no DB, no server, no network; every amount EUR, the report in EUR). Prices are 100 000 a unit so that
the residual's value is a readable number of cents: 0.00001 units × 120 000 = 1.20, at a cost of 0.00001 × 100 000 =
1.00.

- 01-01: DEPOSIT 1 000 000, BUY 10 X for 1 000 000 (close 100 000);
- 01-02: SELL 10 − 0.00001 = 9.99999 X at 120 000 for 1 199 998.80 (close 120 000); 0.00001 X left — exactly the
  threshold, so dust;
- 01-03: nothing happens; the residual is valued at the 01-02 close.

Red on the current tree, green after the fix (expected / current):

- ``TestDustIsNotValued::test_dust_residual_counts_nothing_in_the_day`` — 01-03: market value 0 / 1.20, open cost
  basis 0 / 1.00, NAV 1 199 998.80 / 1 200 000.00, by_asset[X] 0 / 1.20, by_type["ETF"] 0 / 1.20;
- ``TestDustIsNotValued::test_dust_residual_is_not_in_the_end_snapshot`` — position_states_end has no (X, A) / has it
  with quantity 0.00001;
- ``TestDustIsNotValued::test_dust_residual_has_no_position_frame_after_the_sale`` — X at A has a frame on 01-01 only
  / one through 01-03;
- ``TestDustAtThePeriodStart::test_dust_residual_is_not_in_the_start_snapshot`` — the same sale before the period
  (BUY 2024-12-30, SELL 2024-12-31, period 2025-01-01 → 01-02): position_states_start has no (X, A) / has it; the
  period's first day has market value 0 / 1.20;
- ``TestUnpricedDust::test_unpriced_dust_does_not_make_the_day_missing`` — a quantity-only ADJUSTMENT +10 Y (no price,
  no cost: MISSING while held) and −9.99999 on 01-02: on 01-02 and 01-03 nav_complete True / False, Y not in
  missing_price_asset_ids / in it, the P&L candle available / None;
- ``TestDustOnOneBrokerBesideARealPosition::test_the_dust_broker_contributes_only_its_cash`` — the dust book at broker
  A, and at broker B DEPOSIT 500 000 + BUY 5 X for 500 000 on 01-01: on 01-03 A's nav_contribution is its cash
  1 199 998.80 / 1 200 000.00, B's 5 × 120 000 = 600 000 on both; NAV 1 799 998.80 / 1 800 000.00; by_asset[X]
  600 000 / 600 001.20; open cost basis 500 000 / 500 001.00. Σ nav_contribution == NAV holds on both trees (a guard).

Green on both trees (guards):

- ``TestJustAboveTheThreshold::test_a_residual_above_the_threshold_is_held`` — SELL 9.999989 instead, 0.000011 X left
  (above 0.00001): valued 0.000011 × 120 000 = 1.32 at a cost of 0.000011 × 100 000 = 1.10, in by_asset and in the end
  snapshot; NAV 1 199 998.68 + 1.32 = 1 200 000.00.

Runs in ``./dev.py test services roi-fifo-utils`` (which runs ``test_financial/`` whole); alone:
``./dev.py test services roi-fifo-utils test_daily_state_dust_threshold``.

Reference: mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/index.en.md (§7,
«Dust aside»), backend/app/services/platform/data_quality_thresholds.py (QUANTITY_DUST_THRESHOLD),
test_positions_contribution_dust_identity.py (the same defect through the Performance table and the summary).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, DailyPortfolioState, PortfolioCalculationResult
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

D = Decimal
ZERO = D("0")

BROKER_A = 10
BROKER_B = 20
ASSET_X = 100  # priced: closes and trades
ASSET_Y = 200  # never priced, no cost: MISSING while held

DAY_1 = date(2025, 1, 1)
DAY_2 = date(2025, 1, 2)
DAY_3 = date(2025, 1, 3)

#: 10 − 0.00001 = 9.99999: what the SELL takes, leaving exactly the threshold
DUST_SALE = D("10") - QUANTITY_DUST_THRESHOLD
#: 10 − 0.000011 = 9.999989: leaves 0.000011, just above the threshold
ABOVE_DUST_SALE = D("10") - D("0.000011")


# =============================================================================
# HELPERS — the shape of test_daily_state_builder.py's, without its defaults for other scenarios
# =============================================================================


def _tx(*, id: int, broker_id: int = BROKER_A, type: str, dt: date, amount: str = "0", quantity: Decimal | str = "0", asset_id: int | None = None) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = D(amount)
    tx.currency = "EUR"
    tx.quantity = D(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = None
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _normal(tx: MagicMock) -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification="normal", share=D("1"), paired_tx=None)


def _build(txs: list[MagicMock], *, prices: dict[int, list[tuple[date, str]]], date_from: date = DAY_1, date_to: date = DAY_3, **flags) -> PortfolioCalculationResult:
    """One replay of ``txs`` as PortfolioCalculationEngine runs it: per-asset mark series from closes and trades,
    average costs and native cash from the same transactions."""
    classified = [_normal(tx) for tx in txs]
    asset_ids = {tx.asset_id for tx in txs if tx.asset_id is not None} | set(prices)
    price_map = {aid: [(day, D(close), "EUR") for day, close in rows] for aid, rows in prices.items()}
    mark_series = {}
    for aid in asset_ids:
        series = build_asset_price_series(
            price_rows=price_map.get(aid, []),
            transactions=[tx for tx in txs if tx.asset_id == aid],
            split_linked_tx_ids=set(),
            asset_currency="EUR",
            quote_base_quantity=1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return DailyStateBuilder(
        classified_txs=classified,
        in_transit_intervals=[],
        external_cash_flows=[],
        price_map=price_map,
        quote_base_map=dict.fromkeys(asset_ids),
        fx_rate_map={},
        asset_classifications=dict.fromkeys(asset_ids),
        asset_types=dict.fromkeys(asset_ids, "ETF"),
        asset_currencies=dict.fromkeys(asset_ids, "EUR"),
        average_costs=engine_average_costs(classified, asset_currencies=dict.fromkeys(asset_ids, "EUR"), target_currency="EUR", fx_rate_map={}, split_linked_tx_ids=None, date_to=date_to),
        native_cash=engine_native_cash(classified, target_currency="EUR", fx_rate_map={}, date_to=date_to),
        target_currency="EUR",
        date_from=date_from,
        date_to=date_to,
        mark_series=mark_series,
        **flags,
    ).build()


def _on(result: PortfolioCalculationResult, day: date) -> DailyPortfolioState:
    """The state of ``day``, found by its date."""
    matches = [state for state in result.daily_states if state.date == day]
    assert len(matches) == 1, f"one state for {day}, got {[state.date for state in result.daily_states]}"
    return matches[0]


def _positions(snapshot) -> dict[tuple[int, int], Decimal]:
    """A snapshot as {(asset, broker): quantity}."""
    return {(ps.asset_id, ps.broker_id): ps.quantity for ps in snapshot}


def _dust_book(sale: Decimal = DUST_SALE, *, broker_id: int = BROKER_A, first_id: int = 1) -> list[MagicMock]:
    """DEPOSIT 1 000 000 and BUY 10 X for 1 000 000 on 01-01, SELL ``sale`` X at 120 000 on 01-02."""
    return [
        _tx(id=first_id, broker_id=broker_id, type="DEPOSIT", dt=DAY_1, amount="1000000"),
        _tx(id=first_id + 1, broker_id=broker_id, type="BUY", dt=DAY_1, amount="-1000000", quantity="10", asset_id=ASSET_X),
        _tx(id=first_id + 2, broker_id=broker_id, type="SELL", dt=DAY_2, amount=str(sale * D("120000")), quantity=-sale, asset_id=ASSET_X),
    ]


X_CLOSES = {ASSET_X: [(DAY_1, "100000"), (DAY_2, "120000")]}


# =============================================================================
# THE TESTS
# =============================================================================


class TestDustIsNotValued:
    """0.00001 X left after the sale — exactly the threshold — is not a position."""

    def test_dust_residual_counts_nothing_in_the_day(self):
        """01-03: cash 1 000 000 − 1 000 000 + 9.99999 × 120 000 = 1 199 998.80 and nothing else."""
        result = _build(_dust_book(), prices=X_CLOSES)
        day_1, day_3 = _on(result, DAY_1), _on(result, DAY_3)

        assert day_1.market_value == D("1000000"), f"precondition: 10 X × 100 000 on 01-01, got {day_1.market_value}"
        assert day_3.cash_value == D("1199998.80"), f"precondition: the sale's cash, got {day_3.cash_value}"
        assert day_3.market_value == ZERO, f"market_value {day_3.market_value}: the 0.00001 X left (dust) valued at 0.00001 × 120 000 = 1.20"
        assert day_3.open_cost_basis == ZERO, f"open_cost_basis {day_3.open_cost_basis}: the dust's cost 0.00001 × 100 000 = 1.00 counted"
        assert day_3.nav_value == D("1199998.80"), f"nav_value {day_3.nav_value}: the cash 1 199 998.80 plus the dust's 1.20"
        assert day_3.by_asset.get(ASSET_X, ZERO) == ZERO, f"by_asset[X] {day_3.by_asset.get(ASSET_X)}: the dust in the allocation"
        assert day_3.by_type.get("ETF", ZERO) == ZERO, f"by_type[ETF] {day_3.by_type.get('ETF')}: the dust in the allocation"
        assert day_3.nav_complete is True

    def test_dust_residual_is_not_in_the_end_snapshot(self):
        """position_states_end (t1 = 01-03) lists only what is held: the dust is not."""
        result = _build(_dust_book(), prices=X_CLOSES)

        assert result.end_state.cumulative_qty[(ASSET_X, BROKER_A)] == QUANTITY_DUST_THRESHOLD, "precondition: 10 − 9.99999 = 0.00001 X left in the ledger"
        assert (ASSET_X, BROKER_A) not in _positions(result.position_states_end), f"position_states_end {_positions(result.position_states_end)}: the dust is a held position"

    def test_dust_residual_has_no_position_frame_after_the_sale(self):
        """A position not held on a day has no frame there: X at A ends on 01-01, the day before the sale."""
        result = _build(_dust_book(), prices=X_CLOSES, compute_position_frames=True)
        frames = [frame for frame in result.position_frames if (frame.asset_id, frame.broker_id) == (ASSET_X, BROKER_A)]

        assert frames, "precondition: X at A is held on 01-01"
        assert max(frame.end for frame in frames) == DAY_1, f"frames {[(frame.start, frame.end, frame.quantity) for frame in frames]}: the dust held after 01-01"


class TestDustAtThePeriodStart:
    """The same sale before the period: the start snapshot and the first day hold nothing."""

    def test_dust_residual_is_not_in_the_start_snapshot(self):
        """BUY 10 X on 2024-12-30 at 100 000, SELL 9.99999 on 2024-12-31 at 120 000; period 2025-01-01 → 01-02."""
        txs = [
            _tx(id=1, type="DEPOSIT", dt=date(2024, 12, 30), amount="1000000"),
            _tx(id=2, type="BUY", dt=date(2024, 12, 30), amount="-1000000", quantity="10", asset_id=ASSET_X),
            _tx(id=3, type="SELL", dt=date(2024, 12, 31), amount=str(DUST_SALE * D("120000")), quantity=-DUST_SALE, asset_id=ASSET_X),
        ]
        result = _build(txs, prices={ASSET_X: [(date(2024, 12, 30), "100000"), (date(2024, 12, 31), "120000")]}, date_from=DAY_1, date_to=DAY_2)
        first = _on(result, DAY_1)

        assert result.position_states_start_date == DAY_1, "precondition: the start snapshot is taken at the end of 01-01"
        assert (ASSET_X, BROKER_A) not in _positions(result.position_states_start), f"position_states_start {_positions(result.position_states_start)}: the dust is a held position"
        assert first.market_value == ZERO, f"market_value {first.market_value} on the period's first day: the dust valued at 1.20"
        assert first.nav_value == D("1199998.80"), f"nav_value {first.nav_value}: the cash 1 199 998.80 plus the dust's 1.20"


class TestUnpricedDust:
    """Y has no price and no cost: held, it is MISSING. Its dust is not held, so it is not MISSING."""

    def test_unpriced_dust_does_not_make_the_day_missing(self):
        """ADJUSTMENT +10 Y on 01-01 (quantity only), −9.99999 Y on 01-02: 0.00001 Y left."""
        txs = [
            _tx(id=1, type="ADJUSTMENT", dt=DAY_1, quantity="10", asset_id=ASSET_Y),
            _tx(id=2, type="ADJUSTMENT", dt=DAY_2, quantity=-DUST_SALE, asset_id=ASSET_Y),
        ]
        result = _build(txs, prices={}, compute_candles=True)
        day_1 = _on(result, DAY_1)

        assert ASSET_Y in day_1.missing_price_asset_ids and day_1.nav_complete is False, "precondition: 10 Y with no price and no cost is MISSING on 01-01"
        for day in (DAY_2, DAY_3):
            state = _on(result, day)
            assert ASSET_Y not in state.missing_price_asset_ids, f"{day}: missing_price_asset_ids {state.missing_price_asset_ids} — the dust of Y flagged MISSING"
            assert state.nav_complete is True, f"{day}: nav_complete False for 0.00001 Y of dust"
            assert state.pnl_candle is not None, f"{day}: no P&L candle — the dust of Y made the day's valuation MISSING"
        assert (ASSET_Y, BROKER_A) not in _positions(result.position_states_end), f"position_states_end {_positions(result.position_states_end)}: the dust of Y is a held position"


class TestDustOnOneBrokerBesideARealPosition:
    """The dust at A, 5 X really held at B: only B's units count."""

    def test_the_dust_broker_contributes_only_its_cash(self):
        """01-03: A = cash 1 199 998.80; B = 5 × 120 000 = 600 000 (its cash 500 000 − 500 000 = 0)."""
        txs = [
            *_dust_book(),
            _tx(id=11, broker_id=BROKER_B, type="DEPOSIT", dt=DAY_1, amount="500000"),
            _tx(id=12, broker_id=BROKER_B, type="BUY", dt=DAY_1, amount="-500000", quantity="5", asset_id=ASSET_X),
        ]
        day_3 = _on(_build(txs, prices=X_CLOSES), DAY_3)
        contributions = day_3.broker_contributions

        assert contributions[BROKER_B].nav_contribution == D("600000"), f"precondition: B's 5 X × 120 000, got {contributions[BROKER_B].nav_contribution}"
        assert sum((c.nav_contribution for c in contributions.values()), ZERO) == day_3.nav_value, "Σ nav_contribution == NAV (by construction)"
        assert contributions[BROKER_A].nav_contribution == D("1199998.80"), f"A's nav_contribution {contributions[BROKER_A].nav_contribution}: its cash 1 199 998.80 plus the dust's 1.20"
        assert day_3.nav_value == D("1799998.80"), f"nav_value {day_3.nav_value}: 1 199 998.80 + 600 000, plus the dust's 1.20"
        assert day_3.by_asset.get(ASSET_X) == D("600000"), f"by_asset[X] {day_3.by_asset.get(ASSET_X)}: B's 600 000 plus the dust's 1.20"
        assert day_3.open_cost_basis == D("500000"), f"open_cost_basis {day_3.open_cost_basis}: B's 500 000 plus the dust's 1.00"


class TestJustAboveTheThreshold:
    """Guard, green on both trees: 0.000011 X is above the threshold, so it is held and valued."""

    def test_a_residual_above_the_threshold_is_held(self):
        """SELL 9.999989 X at 120 000 for 1 199 998.68; 0.000011 X left, worth 1.32 at a cost of 1.10."""
        result = _build(_dust_book(ABOVE_DUST_SALE), prices=X_CLOSES)
        day_3 = _on(result, DAY_3)

        assert day_3.market_value == D("1.32"), f"market_value {day_3.market_value}: 0.000011 × 120 000"
        assert day_3.open_cost_basis == D("1.10"), f"open_cost_basis {day_3.open_cost_basis}: 0.000011 × 100 000"
        assert day_3.nav_value == D("1200000.00"), f"nav_value {day_3.nav_value}: 1 199 998.68 + 1.32"
        assert day_3.by_asset.get(ASSET_X) == D("1.32")
        assert _positions(result.position_states_end).get((ASSET_X, BROKER_A)) == D("0.000011"), f"position_states_end {_positions(result.position_states_end)}"
