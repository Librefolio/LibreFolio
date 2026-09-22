"""Regression tests for G1a — additive per-broker P&L contribution tracking.

Mandatory invariant under test (plan §4.2, verbatim): "the implementation must build
the total and broker values from the same Decimal components, not calculate a
residual line after the fact." Concretely, for EVERY emitted DailyPortfolioState:

    sum(bc.nav_contribution for bc in s.broker_contributions.values()) == s.nav_value
    sum(bc.capital_contribution for ...) == s.cumulative_external_cash_flow
    sum(bc.pnl_contribution for ...) == s.total_pnl

Also covers:
- The F2 fix to InTransitInterval.share (was hardcoded to Decimal("1") at
  construction regardless of the departure broker's real ownership share;
  ScopeAwareTransactionClassifier.classify() must now override it from
  broker_shares right after building the interval).
- Broker-scoped in-kind ADJUSTMENT capital routing (pre-frame + frame code paths).
- EngineEndState.cumulative_cash_by_broker / cumulative_ecf_by_broker.
- DerivedViewsBuilder.build_broker_pnl_history().

Pure tests — no DB, no async. Uses mock Transaction objects + DailyStateBuilder,
mirroring the conventions in test_cash_decomposition.py / test_daily_state_builder.py
/ test_scope_classifier.py in this directory.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency as CurrencySchema
from backend.app.services.portfolio_engine import (
    BrokerDailyContribution,
    ClassifiedTransaction,
    DailyPortfolioState,
    DailyStateBuilder,
    DerivedViewsBuilder,
    PortfolioCalculationResult,
    ScopeAwareTransactionClassifier,
)
from backend.app.services.price_resolver import build_asset_price_series

# =============================================================================
# HELPERS — mirror the established conventions in this test directory
# =============================================================================


def _tx(
    *,
    id: int = 1,
    broker_id: int = 10,
    type: str = "DEPOSIT",
    dt: str = "2025-01-01",
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
    tx.date = date.fromisoformat(dt)
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


def _builder(**overrides) -> DailyStateBuilder:
    """Create a DailyStateBuilder with sensible defaults, overriding any kwarg."""
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
    return DailyStateBuilder(**defaults)


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
# SCENARIO A — multi-broker, no in-transit (hand-verified golden numbers)
# =============================================================================

_SCENARIO_A_PRICES = {
    100: [
        (date(2025, 1, 1), Decimal("100"), "EUR"),
        (date(2025, 2, 1), Decimal("120"), "EUR"),
        (date(2025, 3, 1), Decimal("130"), "EUR"),
    ]
}
_SCENARIO_A_ECF = [
    (date(2025, 1, 1), 10, Decimal("5000"), "EUR"),
    (date(2025, 1, 2), 20, Decimal("2000"), "EUR"),
    (date(2025, 2, 10), 20, Decimal("-200"), "EUR"),
]


def _scenario_a_txs() -> list[ClassifiedTransaction]:
    return [
        _ctxn(_tx(id=1, broker_id=10, type="DEPOSIT", dt="2025-01-01", amount="5000")),
        _ctxn(_tx(id=2, broker_id=10, type="BUY", dt="2025-01-01", amount="-5000", quantity="50", asset_id=100)),
        _ctxn(_tx(id=3, broker_id=10, type="SELL", dt="2025-02-01", amount="1200", quantity="-10", asset_id=100)),
        _ctxn(_tx(id=4, broker_id=10, type="DIVIDEND", dt="2025-02-05", amount="50")),
        _ctxn(_tx(id=5, broker_id=20, type="DEPOSIT", dt="2025-01-02", amount="2000")),
        _ctxn(_tx(id=6, broker_id=20, type="BUY", dt="2025-01-02", amount="-2000", quantity="20", asset_id=100)),
        _ctxn(_tx(id=7, broker_id=20, type="WITHDRAWAL", dt="2025-02-10", amount="-200")),
    ]


def _scenario_a_result() -> PortfolioCalculationResult:
    builder = _builder(
        classified_txs=_scenario_a_txs(),
        external_cash_flows=_SCENARIO_A_ECF,
        price_map=_SCENARIO_A_PRICES,
        asset_currencies={100: "EUR"},
        asset_types={100: "Stock"},
        asset_classifications={100: None},
        date_from=date(2025, 1, 1),
        date_to=date(2025, 3, 1),
    )
    return builder.build()


class TestScenarioAMultiBrokerContributions:
    """Broker 10: DEPOSIT 5000, BUY 50u@100, SELL 10u@120, DIVIDEND 50.
    Broker 20: DEPOSIT 2000, BUY 20u@100, WITHDRAWAL -200.
    Same asset (id=100), separate WAC pools per (asset_id, broker_id).
    """

    def test_final_day_matches_hand_verified_golden_numbers(self):
        result = _scenario_a_result()
        last = result.daily_states[-1]
        assert last.date == date(2025, 3, 1)

        b10 = last.broker_contributions[10]
        b20 = last.broker_contributions[20]
        assert isinstance(b10, BrokerDailyContribution)
        assert isinstance(b20, BrokerDailyContribution)

        # Broker 10: 40 remaining units @130 = 5200 + cash 1250 (5000 dep - 5000 buy
        # + 1200 sell + 50 div) = 6450 nav; capital = 5000 (deposit only); pnl = 1450.
        assert b10.nav_contribution == Decimal("6450")
        assert b10.capital_contribution == Decimal("5000")
        assert b10.pnl_contribution == Decimal("1450")

        # Broker 20: 20 units @130 = 2600 + cash -200 (2000 dep - 2000 buy - 200 wd)
        # = 2400 nav; capital = 1800 (2000 - 200); pnl = 600.
        assert b20.nav_contribution == Decimal("2400")
        assert b20.capital_contribution == Decimal("1800")
        assert b20.pnl_contribution == Decimal("600")

        assert last.total_pnl == Decimal("2050")
        _assert_broker_contribution_invariant(last)

    def test_invariant_holds_on_every_emitted_day(self):
        result = _scenario_a_result()
        # Sanity: no gaps in the emitted daily vector (Jan 1 .. Mar 1, 2025).
        assert len(result.daily_states) == (date(2025, 3, 1) - date(2025, 1, 1)).days + 1
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# SCENARIO B — in-transit cash + F2 share-assignment fix regression
# =============================================================================


def _scenario_b_transactions() -> list[MagicMock]:
    dep = _tx(id=1, broker_id=10, type="DEPOSIT", dt="2025-01-01", amount="5000")
    buy = _tx(id=2, broker_id=10, type="BUY", dt="2025-01-01", amount="-5000", quantity="50", asset_id=100)
    transfer_out = _tx(id=3, broker_id=10, type="CASH_TRANSFER", dt="2025-02-01", amount="-1000", related_id=4)
    transfer_in = _tx(id=4, broker_id=20, type="CASH_TRANSFER", dt="2025-02-05", amount="1000", related_id=3)
    return [dep, buy, transfer_out, transfer_in]


def _scenario_b_classify(broker_shares: dict[int, Decimal]):
    classifier = ScopeAwareTransactionClassifier(
        scope_broker_ids={10, 20},
        all_transactions=_scenario_b_transactions(),
        broker_shares=broker_shares,
    )
    return classifier.classify()


class TestScenarioBInTransitShareFix:
    """In-transit cash (departure broker 10 -> arrival broker 20) plus the F2 fix:
    InTransitInterval.share was hardcoded to Decimal("1") at construction regardless
    of the departure broker's real ownership share; classify() must override it.
    """

    def test_share_assignment_regression_dedicated(self):
        """Dedicated regression, separate from the NAV-composition scenario below:
        classify() must override InTransitInterval's constructor default (1) with the
        DEPARTURE broker's real ownership share (0.5), not the arrival broker's (1),
        and not the constructor's hardcoded default.
        """
        classification = _scenario_b_classify(broker_shares={10: Decimal("0.5"), 20: Decimal("1")})

        assert len(classification.in_transit_intervals) == 1
        it = classification.in_transit_intervals[0]
        assert it.departure_leg.broker_id == 10
        assert it.share == Decimal("0.5"), f"expected departure broker's share 0.5, got {it.share} (still the constructor's hardcoded default of 1?)"

    def test_nav_composition_mid_transit_and_post_arrival(self):
        """Full (100%) ownership on both brokers — isolates the NAV-composition
        assertions from the share-fix regression above. Checks the additive
        invariant across the mid-transit -> post-arrival transition, the
        highest-risk part of the G1a change.
        """
        classification = _scenario_b_classify(broker_shares={10: Decimal("1"), 20: Decimal("1")})
        assert len(classification.in_transit_intervals) == 1
        assert classification.in_transit_intervals[0].share == Decimal("1")
        # The internal transfer must never leak into external cash flow / capital.
        assert classification.external_cash_flows == [(date(2025, 1, 1), 10, Decimal("5000"), "EUR")]

        builder = _builder(
            classified_txs=classification.classified,
            in_transit_intervals=classification.in_transit_intervals,
            external_cash_flows=classification.external_cash_flows,
            price_map={100: [(date(2025, 1, 1), Decimal("100"), "EUR")]},  # only one point, ever
            asset_currencies={100: "EUR"},
            asset_types={100: "Stock"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 2, 10),
        )
        result = builder.build()
        states_by_date = {s.date: s for s in result.daily_states}

        # Mid-transit: broker 10 keeps ALL value (units-at-cost + in-transit cash);
        # broker 20 has nothing yet.
        mid = states_by_date[date(2025, 2, 3)]
        assert mid.nav_value == Decimal("5000")
        assert mid.in_transit_cash_value == Decimal("1000")
        assert mid.broker_contributions[10].nav_contribution == Decimal("5000")
        assert mid.broker_contributions[20].nav_contribution == Decimal("0")

        # Post-arrival: aggregate NAV unchanged, but the 1000 has moved from broker
        # 10's in-transit slice to broker 20's normal cash ledger.
        post = states_by_date[date(2025, 2, 6)]
        assert post.nav_value == Decimal("5000")
        assert post.broker_contributions[10].nav_contribution == Decimal("4000")
        assert post.broker_contributions[20].nav_contribution == Decimal("1000")

        # Dense check across the departure -> transit -> arrival transition window,
        # plus the full history — the invariant must never gap or double-count.
        for d in (date(2025, 1, 31), date(2025, 2, 1), date(2025, 2, 2), date(2025, 2, 3), date(2025, 2, 4), date(2025, 2, 5), date(2025, 2, 6), date(2025, 2, 7)):
            _assert_broker_contribution_invariant(states_by_date[d])
        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# In-kind ADJUSTMENT — broker-scoped capital routing (pre-frame + frame paths)
# =============================================================================


class TestInKindAdjustmentBrokerAttribution:
    """A priced in-kind ADJUSTMENT (opening/transfer/succession) is a capital
    contribution/distribution, not profit — its cost must move
    cumulative_ecf_by_broker for the SPECIFIC broker that carries it, symmetric to
    the scope-aggregate cumulative_ecf, whether the transaction falls in the
    pre-frame accounting-only window or inside the fully-evaluated frame.
    """

    def test_preframe_in_and_frame_out_track_broker_ecf(self):
        # Broker 10: opening in-kind ADJUSTMENT-in, dated BEFORE frame_start (pre-frame path).
        adj_in = _tx(id=1, broker_id=10, type="ADJUSTMENT", dt="2025-01-02", quantity="10", asset_id=100, cost_basis_override="100", cost_basis_currency="EUR")
        # Broker 20: unrelated external deposit (also pre-frame) — isolation control:
        # its own capital baseline must stay untouched by broker 10's in-kind event.
        dep20 = _tx(id=2, broker_id=20, type="DEPOSIT", dt="2025-01-03", amount="500")
        # Broker 10: in-kind ADJUSTMENT-out INSIDE the frame (frame path), same
        # qty/cost -> fully unwinds the capital contributed above.
        adj_out = _tx(id=3, broker_id=10, type="ADJUSTMENT", dt="2025-01-12", quantity="-10", asset_id=100, cost_basis_override="100", cost_basis_currency="EUR")

        txs = [_ctxn(adj_in), _ctxn(dep20), _ctxn(adj_out)]
        ecfs = [(date(2025, 1, 3), 20, Decimal("500"), "EUR")]

        builder = _builder(
            classified_txs=txs,
            external_cash_flows=ecfs,
            asset_currencies={100: "EUR"},
            date_from=date(2025, 1, 1),
            frame_start=date(2025, 1, 10),
            date_to=date(2025, 1, 15),
        )
        result = builder.build()

        # First frame day: the pre-frame ADJUSTMENT-in has already been carried into
        # cumulative_ecf_by_broker[10], alongside broker 20's unrelated deposit.
        first = result.daily_states[0]
        assert first.date == date(2025, 1, 10)
        assert first.broker_contributions[10].capital_contribution == Decimal("1000")
        assert first.broker_contributions[20].capital_contribution == Decimal("500")
        assert first.cumulative_external_cash_flow == Decimal("1500")
        _assert_broker_contribution_invariant(first)

        # After the frame-path ADJUSTMENT-out: broker 10's in-kind capital fully
        # unwinds; broker 20 is untouched (isolation control holds).
        last = result.daily_states[-1]
        assert last.broker_contributions[10].capital_contribution == Decimal("0")
        assert last.broker_contributions[20].capital_contribution == Decimal("500")
        assert last.cumulative_external_cash_flow == Decimal("500")
        _assert_broker_contribution_invariant(last)

        _assert_invariant_every_day(result.daily_states)


# =============================================================================
# EngineEndState — per-broker cumulative mirrors
# =============================================================================


class TestEngineEndStatePerBroker:
    """EngineEndState.cumulative_cash_by_broker / cumulative_ecf_by_broker — the
    forward-cache-resume accumulator mirrors, assembled directly inside
    DailyStateBuilder.build() (not in the async PortfolioCalculationEngine.calculate()
    wrapper), so this is testable without a DB/async fixture.
    """

    def test_populated_and_matches_last_day_per_broker_values(self):
        result = _scenario_a_result()
        last = result.daily_states[-1]
        end = result.end_state
        assert end is not None

        assert set(end.cumulative_cash_by_broker.keys()) == {10, 20}
        assert set(end.cumulative_ecf_by_broker.keys()) == {10, 20}

        # cumulative_ecf_by_broker is literally the same accumulator read at the end
        # of the loop as the last day's capital_contribution — must match exactly.
        assert end.cumulative_ecf_by_broker[10] == last.broker_contributions[10].capital_contribution == Decimal("5000")
        assert end.cumulative_ecf_by_broker[20] == last.broker_contributions[20].capital_contribution == Decimal("1800")

        # cumulative_cash_by_broker — hand-verified per-broker cash ledger.
        assert end.cumulative_cash_by_broker[10] == Decimal("1250")  # 5000 dep - 5000 buy + 1200 sell + 50 div
        assert end.cumulative_cash_by_broker[20] == Decimal("-200")  # 2000 dep - 2000 buy - 200 wd

        assert sum(end.cumulative_cash_by_broker.values()) == last.cash_value
        assert sum(end.cumulative_ecf_by_broker.values()) == last.cumulative_external_cash_flow


# =============================================================================
# DerivedViewsBuilder.build_broker_pnl_history()
# =============================================================================


class TestBrokerPnlHistory:
    """Per-broker additive P&L history: broker_id -> [{date, total_pnl}, ...],
    derived from DailyPortfolioState.broker_contributions.
    """

    def test_shape_and_sum_reproduces_aggregate_every_day(self):
        result = _scenario_a_result()
        states = result.daily_states
        history = DerivedViewsBuilder(states, "EUR").build_broker_pnl_history()

        assert set(history.keys()) == {10, 20}
        for points in history.values():
            assert len(points) == len(states)
            for point in points:
                assert set(point.keys()) == {"date", "total_pnl"}
                assert isinstance(point["total_pnl"], CurrencySchema)
                assert point["total_pnl"].code == "EUR"

        # Sum across brokers reproduces the aggregate DailyPortfolioState.total_pnl,
        # for EVERY date — not just the last one.
        points_by_broker_date = {bid: {p["date"]: p["total_pnl"].amount for p in points} for bid, points in history.items()}
        for s in states:
            total = sum(points_by_broker_date[bid][s.date] for bid in history)
            assert total == s.total_pnl, f"{s.date}: sum(broker total_pnl)={total} != aggregate total_pnl={s.total_pnl}"

    def test_final_day_matches_golden_numbers(self):
        result = _scenario_a_result()
        states = result.daily_states
        history = DerivedViewsBuilder(states, "EUR").build_broker_pnl_history()
        last_date = states[-1].date

        final_10 = next(p["total_pnl"].amount for p in history[10] if p["date"] == last_date)
        final_20 = next(p["total_pnl"].amount for p in history[20] if p["date"] == last_date)

        assert final_10 == Decimal("1450")
        assert final_20 == Decimal("600")
