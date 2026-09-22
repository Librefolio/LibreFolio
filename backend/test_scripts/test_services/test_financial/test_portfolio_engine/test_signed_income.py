"""Regression tests for G1c — signed personal income history (engine layer).

Covers the DailyStateBuilder DIVIDEND/INTEREST touch points (plan §4.4): both the
pre-frame loop (accounting-only, line ~725) and the frame loop (full evaluation +
period accumulators, line ~1021) now preserve the sign of the *original*
``tx.amount`` instead of unconditionally converting through ``abs(tx.amount)``.
A legacy negative DIVIDEND/INTEREST correction must reduce the returns pool
``R[bid]`` (and, in the frame loop, ``per_income``/``unalloc_income``), never be
added to it as if it were positive income.

Two outputs matter here, and they are NOT interchangeable:

- CANONICAL, non-cosmetic: ``total_pnl`` and ``capital_baseline``
  (``cumulative_external_cash_flow``). These must be exactly right — DIVIDEND/
  INTEREST is not an external cash flow, so a correction moves total_pnl but
  never capital_baseline.
- COSMETIC: the 3-pool ``cash_from_contributed_capital`` /
  ``cash_from_generated_returns`` split. Pre-existing step "4g. Clamp pools
  per-broker (rounding safety)" clamps a negative-enough ``R[bid]`` to 0 at the
  end of every frame day — that clamp is OUT OF SCOPE for this plan (it existed
  before G1c and is not asserted to have changed here); this file only asserts
  it still exists and does not crash.

IMPORTANT — verified empirically (see this file's docstring notes per test),
NOT merely hand-traced: within a single calendar day the unified loop processes
transactions in a fixed bucket order — additions (BUY, qty>0) first, then
reductions (SELL, qty<0), then everything else (DEPOSIT/WITHDRAWAL/DIVIDEND/
INTEREST/FEE/TAX) — regardless of any nominal "chronological" intent encoded by
insertion order. This is pre-existing engine architecture (see the "Single
pass: for each tx, in additions-first order" comment above the loop; the
existing test_portfolio_engine_vnext.py::TestThreePool::test_buy_consumes_returns_first
independently confirms it by using a DIVIDEND dated *before* its BUY, never the
same day). Consequently, a same-day DIVIDEND/INTEREST correction can never
reduce the R pool a same-day BUY draws from — only a correction dated on an
earlier day can. Both orderings are covered below; the same-day case documents
the real (verified) behaviour instead of asserting the intuitive-but-false one.

Pure tests — no DB, no async. Mirrors the conventions established in
test_cash_decomposition.py / test_broker_pnl_contributions.py in this directory
(mock Transaction objects + DailyStateBuilder).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.portfolio_engine import (
    ClassifiedTransaction,
    DailyStateBuilder,
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
    tx.related_transaction_id = None
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _ctxn(tx: MagicMock, classification: str = "normal", share: str = "1") -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal(share), paired_tx=None)


# Market price for asset 100 = its BUY unit cost, so market_value == open_cost_basis
# (no unrealized gain/loss) — same convention as test_cash_decomposition.py, so
# every number below is attributable to the DIVIDEND/INTEREST sign fix alone.
_PRICE_MAP_100 = {100: [(date(2025, 1, 1), Decimal("100"), "EUR")]}


def _mark_series_from(txs, price_map, asset_currencies, quote_base_map):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from prices + trades."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in txs:
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
            quote_base_quantity=(quote_base_map or {}).get(aid) or 1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _builder(txs, ecfs, *, date_from=date(2025, 1, 1), date_to=date(2025, 1, 1), frame_start=None, price_map=None, **overrides) -> DailyStateBuilder:
    defaults = {
        "classified_txs": txs,
        "in_transit_intervals": [],
        "external_cash_flows": ecfs,
        "price_map": price_map or {},
        "quote_base_map": {},
        "fx_rate_map": {},
        "asset_classifications": {},
        "asset_types": {},
        "asset_currencies": {},
        "target_currency": "EUR",
        "date_from": date_from,
        "date_to": date_to,
        "frame_start": frame_start,
    }
    defaults.update(overrides)
    if "mark_series" not in defaults:
        defaults["mark_series"] = _mark_series_from(
            defaults["classified_txs"],
            defaults["price_map"],
            defaults["asset_currencies"],
            defaults["quote_base_map"],
        )
    return DailyStateBuilder(**defaults)


def _assert_decomposition_invariants(state) -> None:
    """The pre-existing cash-decomposition invariants must hold under a signed
    correction too — same check as test_cash_decomposition.py's
    _assert_invariants, duplicated here per this directory's per-file convention."""
    zero = Decimal("0")
    assert state.cash_from_contributed_capital >= zero, f"cash_from_contributed_capital must be >= 0, got {state.cash_from_contributed_capital}"
    assert state.cash_from_generated_returns >= zero, f"cash_from_generated_returns must be >= 0, got {state.cash_from_generated_returns}"
    cash_like = state.cash_value + state.in_transit_cash_value
    decomp_sum = state.cash_from_contributed_capital + state.cash_from_generated_returns
    assert abs(decomp_sum - cash_like) < Decimal("0.01"), f"Decomposition sum {decomp_sum} != cash_like {cash_like}"
    expected_pnl = state.nav_value - state.cumulative_external_cash_flow
    assert abs(state.total_pnl - expected_pnl) < Decimal("0.01"), f"total_pnl {state.total_pnl} != nav {state.nav_value} - baseline {state.cumulative_external_cash_flow} = {expected_pnl}"


# =============================================================================
# GOLDEN SCENARIO — DEPOSIT then a negative INTEREST correction, no assets
# =============================================================================


class TestGoldenDepositThenNegativeInterest:
    """DEPOSIT 1000 (day1), INTEREST -50 (day2), no BUY, no assets.

    Hand-traced expectation: cash=950, nav=950, capital_baseline=1000 (unaffected —
    INTEREST is not an external cash flow), total_pnl=950-1000=-50. Verified via
    DailyStateBuilder directly (this test) — independently re-derived, not merely
    trusted from the hand trace.
    """

    def test_day1_deposit_only(self):
        txs = [_ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000"))]
        ecfs = [(date(2025, 1, 1), 10, Decimal("1000"), "EUR")]
        builder = _builder(txs, ecfs, date_to=date(2025, 1, 2))
        result = builder.build()
        day1 = result.daily_states[0]

        assert day1.cash_value == Decimal("1000")
        assert day1.nav_value == Decimal("1000")
        assert day1.cumulative_external_cash_flow == Decimal("1000")
        assert day1.total_pnl == Decimal("0")
        _assert_decomposition_invariants(day1)

    def test_day2_negative_interest_correction(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-02", type="INTEREST", amount="-50")),
        ]
        ecfs = [(date(2025, 1, 1), 10, Decimal("1000"), "EUR")]
        builder = _builder(txs, ecfs, date_to=date(2025, 1, 2))
        result = builder.build()
        day2 = result.daily_states[-1]

        assert day2.date == date(2025, 1, 2)
        assert day2.cash_value == Decimal("950"), f"cash must be 950 (1000-50), got {day2.cash_value}"
        assert day2.nav_value == Decimal("950"), f"nav must be 950 (no assets, nav=cash), got {day2.nav_value}"
        assert day2.cumulative_external_cash_flow == Decimal("1000"), "capital_baseline must stay 1000 — INTEREST is not an external cash flow"
        assert day2.total_pnl == Decimal("-50"), f"total_pnl must be 950-1000=-50, got {day2.total_pnl}"
        _assert_decomposition_invariants(day2)

        # Broker-level (asset_id=None): lands in unalloc_income, signed, never per_income.
        assert result.unalloc_income == {10: Decimal("-50")}
        assert result.per_income == {}


# =============================================================================
# PURE-POSITIVE REGRESSION — the ordinary (no correction) path is unaffected
# =============================================================================


class TestPurePositiveIncomeRegression:
    """No correction anywhere: DIVIDEND/INTEREST amounts are already >= 0, so
    ``signed_amt = amt if tx.amount >= 0 else -amt`` reduces to ``signed_amt = amt``
    — bit-for-bit the old abs()-based conversion. This locks in that the common
    (non-correction) path produces the same numbers a hand computation gives,
    i.e. no regression was introduced in the ordinary case.
    """

    def test_deposit_buy_dividend_interest_all_positive(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-500", quantity="5", asset_id=100)),
            _ctxn(_tx(id=3, dt="2025-01-01", type="DIVIDEND", amount="80", asset_id=100)),
            _ctxn(_tx(id=4, dt="2025-01-01", type="INTEREST", amount="20")),
        ]
        ecfs = [(date(2025, 1, 1), 10, Decimal("1000"), "EUR")]
        builder = _builder(txs, ecfs, price_map=_PRICE_MAP_100)
        result = builder.build()
        state = result.daily_states[-1]

        # Hand arithmetic: cash = 1000 - 500 + 80 + 20 = 600.
        # market_value at cost (BUY unit cost == price) = 500 -> nav = 1100.
        # capital_baseline = 1000 (DEPOSIT only); total_pnl = 1100 - 1000 = 100.
        assert state.cash_value == Decimal("600")
        assert state.nav_value == Decimal("1100")
        assert state.cumulative_external_cash_flow == Decimal("1000")
        assert state.total_pnl == Decimal("100")
        _assert_decomposition_invariants(state)

        # Asset-linked DIVIDEND -> per_income keyed (asset_id, broker_id); note this
        # is the ENGINE's own per_income (PortfolioCalculationResult field), keyed in
        # the OPPOSITE tuple order from portfolio_service.py's local per_income /
        # income_by_pos dicts (broker_id, asset_id) — the two are independent
        # accumulators, never compared against each other, so the order mismatch is
        # not a bug; it is called out here so nobody "fixes" one to match the other.
        assert result.per_income == {(100, 10): Decimal("80")}
        assert result.unalloc_income == {10: Decimal("20")}


# =============================================================================
# (a) NEGATIVE CORRECTION REDUCES THE RETURNS POOL A LATER BUY DRAWS FROM
# =============================================================================


class TestNegativeCorrectionReducesReturnsPoolForLaterBuy:
    """A negative DIVIDEND/INTEREST correction must leave a *smaller* R[bid] for
    a subsequent BUY to consume than it would if the same magnitude had been
    wrongly treated as positive (the pre-fix bug: unconditional abs()).

    Constructed across 3 days so the effect is unambiguous and not swallowed by
    the pre-existing end-of-day clamp (rule: never assert on a value the clamp
    could equally have produced by coincidence):
      day1: DEPOSIT 1000, DIVIDEND +100            -> K=1000, R=100
      day2: DIVIDEND -30  (the correction)          -> R=70  (still positive, no clamp)
      day3: BUY 5@100=500                           -> from_r=min(500,70)=70; R=0; K=1000-(500-70)=570

    Mirror (what the pre-fix abs()-based bug would have computed for the same
    "-30" input, i.e. treating it as if it were a genuine +30):
      day2: DIVIDEND +30                            -> R=130
      day3: BUY 5@100=500                           -> from_r=min(500,130)=130; K=1000-(500-130)=630

    K=570 (correct, less capital preserved because more was funded from real
    returns... wait: BUY draws LESS from R when the correction is negative, so
    MORE is funded from K, hence K=570 < mirror's K=630 by exactly 2x the
    correction magnitude (60 = 2x30) — asserted directly below.
    """

    def _run(self, day2_dividend_amount: str):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="DIVIDEND", amount="100")),
            _ctxn(_tx(id=3, dt="2025-01-02", type="DIVIDEND", amount=day2_dividend_amount)),
            _ctxn(_tx(id=4, dt="2025-01-03", type="BUY", amount="-500", quantity="5", asset_id=100)),
        ]
        ecfs = [(date(2025, 1, 1), 10, Decimal("1000"), "EUR")]
        builder = _builder(txs, ecfs, date_to=date(2025, 1, 3), price_map=_PRICE_MAP_100)
        return builder.build()

    def test_signed_negative_correction(self):
        result = self._run("-30")
        day2, day3 = result.daily_states[1], result.daily_states[2]

        # day2: R correctly reduced to 70, still positive (no clamp interference).
        assert day2.cash_from_generated_returns == Decimal("70")
        assert day2.total_pnl == Decimal("70")

        # day3: the direct, unclamped internal pools — not the cosmetic display —
        # settle the question of how much the BUY actually drew from each pool.
        assert result.end_state.returns_pool == {10: Decimal("0")}, "BUY must fully drain the (correctly smaller) R=70"
        assert result.end_state.capital_pool == {10: Decimal("570")}, "K must absorb the remaining 430 (500-70), landing at 1000-430=570"
        assert day3.total_pnl == Decimal("70"), "total_pnl must still read the -30 correction, regardless of the R/K split"
        assert day3.cumulative_external_cash_flow == Decimal("1000"), "capital_baseline unaffected by DIVIDEND"
        _assert_decomposition_invariants(day3)

    def test_mirror_of_pre_fix_bug_draws_more_from_returns(self):
        """Same magnitude (30), but genuinely positive — stands in for what the
        pre-fix abs()-based bug would have computed from a "-30" input. Comparing
        this against test_signed_negative_correction is what proves "the BUY
        draws less from R" (mirror draws MORE): 130 vs 70, and K settles 60 apart
        (2x the corrected amount) at 630 vs 570.
        """
        result = self._run("30")
        day3 = result.daily_states[2]

        assert result.end_state.returns_pool == {10: Decimal("0")}
        assert result.end_state.capital_pool == {10: Decimal("630")}, "mirror: BUY draws 130 from R (wrongly inflated), leaving K at 1000-(500-130)=630"
        assert day3.total_pnl == Decimal("130")


# =============================================================================
# SAME CALENDAR DAY — verified real behaviour (not the intuitive-but-false one)
# =============================================================================


class TestSameDayCorrectionBucketOrdering:
    """Same calendar day: DEPOSIT, a negative DIVIDEND correction, and a BUY.

    Empirically verified (see this file's module docstring): the unified
    per-day loop processes BUY (additions bucket) BEFORE DIVIDEND (non-position
    bucket) regardless of insertion order, so the BUY reads R as it stood at the
    *start* of the day (0 here) — the same-day correction cannot reduce what a
    same-day BUY draws from R. This is pre-existing bucket-ordering architecture,
    not something G1c changed, and it does not compromise correctness: the
    canonical total_pnl/capital_baseline are still exactly right.
    """

    def test_same_day_buy_is_unaffected_by_same_day_correction_but_pnl_is_correct(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="DIVIDEND", amount="-20")),
            _ctxn(_tx(id=3, dt="2025-01-01", type="BUY", amount="-500", quantity="5", asset_id=100)),
        ]
        ecfs = [(date(2025, 1, 1), 10, Decimal("1000"), "EUR")]
        builder = _builder(txs, ecfs, price_map=_PRICE_MAP_100)
        result = builder.build()
        state = result.daily_states[-1]

        # Verified real behaviour: BUY drew entirely from K (R was still 0 when it
        # ran); the correction landed in R afterward, then got clamped to 0.
        assert result.end_state.capital_pool == {10: Decimal("500")}
        assert result.end_state.returns_pool == {10: Decimal("0")}

        # Canonical figures are correct regardless of the intra-day bucket order.
        assert state.cash_value == Decimal("480"), "1000 - 20 - 500 = 480"
        assert state.cumulative_external_cash_flow == Decimal("1000")
        assert state.total_pnl == Decimal("-20"), "nav(480 cash + 500 mv at cost) - baseline(1000) = -20"
        _assert_decomposition_invariants(state)


# =============================================================================
# PRE-FRAME LOOP — the sign fix applies there too (line ~725), and per_income /
# unalloc_income are frame-only (pre-frame never populates them)
# =============================================================================


class TestPreFrameSignedCorrection:
    """A DIVIDEND/INTEREST correction dated before frame_start is handled by the
    pre-frame (accounting-only) loop, not the frame loop — a structurally
    different code path (line ~725, no per_income/unalloc_income side effect,
    no per-day clamp of its own). This must still carry the *signed* value
    forward into the first emitted frame day.
    """

    def test_negative_correction_before_frame_start_carries_into_frame(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-02", type="DIVIDEND", amount="-30")),
        ]
        ecfs = [(date(2025, 1, 1), 10, Decimal("1000"), "EUR")]
        builder = _builder(txs, ecfs, date_from=date(2025, 1, 1), date_to=date(2025, 1, 6), frame_start=date(2025, 1, 5))
        result = builder.build()

        assert [s.date for s in result.daily_states] == [date(2025, 1, 5), date(2025, 1, 6)], "pre-frame days must emit no DailyPortfolioState"
        first_frame_day = result.daily_states[0]

        assert first_frame_day.cash_value == Decimal("970"), "1000 - 30 = 970, carried from the pre-frame loop"
        assert first_frame_day.cumulative_external_cash_flow == Decimal("1000")
        assert first_frame_day.total_pnl == Decimal("-30")
        _assert_decomposition_invariants(first_frame_day)

        # Pre-frame processing never touches the frame-only period accumulators.
        assert result.per_income == {}
        assert result.unalloc_income == {}

    def test_mirror_positive_correction_before_frame_start(self):
        """Same construction, genuinely positive +30 — proves the sign, not just
        the magnitude, survives the pre-frame -> frame boundary."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-02", type="DIVIDEND", amount="30")),
        ]
        ecfs = [(date(2025, 1, 1), 10, Decimal("1000"), "EUR")]
        builder = _builder(txs, ecfs, date_from=date(2025, 1, 1), date_to=date(2025, 1, 6), frame_start=date(2025, 1, 5))
        result = builder.build()
        first_frame_day = result.daily_states[0]

        assert first_frame_day.cash_value == Decimal("1030")
        assert first_frame_day.cumulative_external_cash_flow == Decimal("1000")
        assert first_frame_day.total_pnl == Decimal("30")
        assert first_frame_day.cash_from_generated_returns == Decimal("30"), "positive correction sits entirely in R, undisturbed by any clamp"
        _assert_decomposition_invariants(first_frame_day)


# =============================================================================
# CLAMP STILL EXISTS AND DOES NOT CRASH (out of scope: do not assert it changed)
# =============================================================================


class TestClampStillExistsAndDoesNotCrash:
    """Step "4g. Clamp pools per-broker (rounding safety)" pre-dates G1c and is
    out of scope for this plan. This only proves it is still present (no
    exception on a deeply negative R) and that the invariants it protects
    (non-negative cosmetic split) still hold — never that its behaviour changed.

    Correction magnitude (-500) exceeds K (600) by design so R is driven deeply
    negative and clamped, while DEPOSIT (600) is kept large enough that cash
    itself stays >= 0 — the decomposition-sum invariant (contributed+generated
    == cash_like) is only ever satisfiable for cash_like >= 0 by construction
    (both components are individually clamped to >= 0), a pre-existing domain
    restriction of the formula that has nothing to do with this plan; a
    negative-cash variant would fail that specific invariant on its own terms,
    not because of anything G1c touched.
    """

    def test_deep_negative_correction_does_not_crash_and_keeps_invariants(self):
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="600")),
            _ctxn(_tx(id=2, dt="2025-01-02", type="INTEREST", amount="-500")),
        ]
        ecfs = [(date(2025, 1, 1), 10, Decimal("600"), "EUR")]
        builder = _builder(txs, ecfs, date_to=date(2025, 1, 2))
        result = builder.build()  # must not raise
        state = result.daily_states[-1]

        assert state.cash_value == Decimal("100"), "600 - 500 = 100"
        assert state.cumulative_external_cash_flow == Decimal("600"), "capital_baseline unaffected by INTEREST"
        assert state.total_pnl == Decimal("-500"), "nav(100) - baseline(600) = -500"
        assert result.end_state.returns_pool == {10: Decimal("0")}, "R (-500) must be clamped to 0, not left negative or crash"
        assert result.end_state.capital_pool == {10: Decimal("600")}, "K is untouched by DIVIDEND/INTEREST — the deficit is clamped away, not borrowed from K (unlike FEE/TAX)"
        # The clamp still guarantees a non-negative cosmetic split even though the
        # true pool went deeply negative — this is the pre-existing behaviour this
        # test locks in, not a new invariant introduced by G1c.
        _assert_decomposition_invariants(state)
