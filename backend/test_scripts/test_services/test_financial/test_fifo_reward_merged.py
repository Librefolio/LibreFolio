"""Guards the MERGED reward allocation of the FIFO/LIFO lot engine (project 79, STK-3).

``RewardAllocation.MERGED`` («spread rewards across lots»): a REWARD becomes a ``REWARD_MERGE`` event, phase 3 of its day
(after transfers and splits, before BUY/REWARD/ADJUSTMENT_IN and SELL/ADJUSTMENT_OUT). Its units join the LONG lots held
in BROKER custody at the reward's broker at the close of D-1, pro rata to their open quantity there, at no cost: each
lot's original quantity grows, its cost stays, its unit cost falls. Shares are cut to 1e-10; the rest goes to the lot with
the most units (oldest, then lowest id, on a tie). With no lot held at D-1 the reward opens a lot of its own at cost 0 and
an informational issue ``REWARD_NOT_MERGED_NO_OPEN_LOT`` says so, which leaves the analysis COMPLETE.

``OWN_LOT`` (the default) is unchanged: the guards at the end prove it. Pure: ``run_fifo_lot_engine`` on hand-written
inputs, no DB, no FX.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import EconomicEvent, FifoEngineResult, FifoInputTransaction, LotMatchingMethod, ReferencePriceResolution, RewardAllocation

D = Decimal
ASSET = 7902
BROKER, OTHER_BROKER = 1, 2
MERGED, OWN_LOT = RewardAllocation.MERGED, RewardAllocation.OWN_LOT

LOT_A, LOT_B, REWARD_ID, SELL_ID = 1, 2, 3, 4
DAY_A = date(2024, 1, 10)
DAY_B = date(2025, 6, 10)
REWARD_DAY = date(2026, 3, 1)
SELL_DAY = date(2026, 4, 1)
# 150/510 and 300/510 do not terminate: figures built on them are compared within this bound, never with ==
TOLERANCE = D("1e-18")


def _tx(tx_id: int, tx_type: str, quantity: str, on: date, *, broker_id: int = BROKER, amount: str = "0", currency: str | None = "EUR", related: int | None = None, cbo: str | None = None, cbo_ccy: str | None = None) -> FifoInputTransaction:
    return FifoInputTransaction(
        id=tx_id,
        broker_id=broker_id,
        asset_id=ASSET,
        date=on,
        type=tx_type,
        quantity=D(quantity),
        amount=D(amount),
        currency=currency,
        related_transaction_id=related,
        cost_basis_override=None if cbo is None else D(cbo),
        cost_basis_currency=cbo_ccy,
    )


def _buy(tx_id: int, quantity: str, unit_price: str, on: date, *, broker_id: int = BROKER) -> FifoInputTransaction:
    return _tx(tx_id, "BUY", quantity, on, broker_id=broker_id, amount=str(-(D(quantity) * D(unit_price))))


def _sell(tx_id: int, quantity: str, unit_price: str, on: date, *, broker_id: int = BROKER) -> FifoInputTransaction:
    return _tx(tx_id, "SELL", f"-{quantity}", on, broker_id=broker_id, amount=str(D(quantity) * D(unit_price)))


def _reward(tx_id: int, quantity: str, unit_value: str | None, on: date, *, broker_id: int = BROKER, currency: str | None = "EUR") -> FifoInputTransaction:
    """A REWARD as stored: units in, amount 0 and no cash currency, the per-unit value in cost_basis_*."""
    return _tx(tx_id, "REWARD", quantity, on, broker_id=broker_id, currency=None, cbo=unit_value, cbo_ccy=currency)


def _transfer(out_id: int, in_id: int, quantity: str, *, out_on: date, in_on: date, source: int = BROKER, destination: int = OTHER_BROKER) -> list[FifoInputTransaction]:
    return [
        _tx(out_id, "TRANSFER", f"-{quantity}", out_on, broker_id=source, related=in_id),
        _tx(in_id, "TRANSFER", quantity, in_on, broker_id=destination, related=out_id),
    ]


def _run(
    transactions,
    *,
    allocation: RewardAllocation = MERGED,
    method: LotMatchingMethod = LotMatchingMethod.FIFO,
    events=(),
    split_ratios: dict[int, Decimal] | None = None,
    reference_price_lookup=None,
) -> FifoEngineResult:
    return run_fifo_lot_engine(
        transactions,
        {BROKER: False, OTHER_BROKER: False},
        split_ratios_by_tx_id=split_ratios,
        economic_events=list(events),
        target_currency="EUR",
        matching_method=method,
        reward_allocation=allocation,
        reference_price_lookup=reference_price_lookup,
    )


def _golden(sell_quantity: str | None = None) -> list[FifoInputTransaction]:
    """Plan §5: lot A 500 @0.30, lot B 500 @0.60, REWARD 20 (value 0.50 a unit) on 1 Mar 2026, then a sale @0.70."""
    rows = [_buy(LOT_A, "500", "0.30", DAY_A), _buy(LOT_B, "500", "0.60", DAY_B), _reward(REWARD_ID, "20", "0.50", REWARD_DAY)]
    return rows + ([_sell(SELL_ID, sell_quantity, "0.70", SELL_DAY)] if sell_quantity is not None else [])


def _realized(result: FifoEngineResult, sell_id: int = SELL_ID) -> Decimal:
    closures = [closure for closure in result.closures if closure.transaction_id == sell_id]
    assert closures, f"no closure for transaction {sell_id}"
    assert all(closure.realized_pnl is not None for closure in closures)
    return sum((closure.realized_pnl for closure in closures), D("0"))


def _merges(result: FifoEngineResult) -> dict[int, Decimal]:
    """lot_id → the units it took, for every RewardMerge of the run."""
    return {merge.lot_id: merge.added_quantity for merge in result.reward_merges}


def _issue_codes(result: FifoEngineResult) -> list[str]:
    return [issue.code for issue in result.issues]


def _close(actual: Decimal, expected: Decimal) -> bool:
    return abs(actual - expected) < TOLERANCE


# =============================================================================
# 1. The golden case of plan §5, MERGED
# =============================================================================


class TestGoldenMerged:
    def test_the_reward_is_classified_as_a_merge(self):
        result = _run(_golden())
        assert [(event.kind, event.unit_price) for event in result.classified_events if event.transaction_id == REWARD_ID] == [("REWARD_MERGE", D("0"))]
        assert result.reward_allocation is MERGED

    def test_a_and_b_take_10_each_and_keep_their_cost(self):
        result = _run(_golden())
        lot_a, lot_b = result.get_lot(LOT_A), result.get_lot(LOT_B)
        assert (lot_a.original_quantity, lot_a.open_quantity, lot_a.original_cost) == (D("510"), D("510"), D("150.00"))
        assert (lot_b.original_quantity, lot_b.open_quantity, lot_b.original_cost) == (D("510"), D("510"), D("300.00"))
        assert _close(lot_a.opening_unit_price, D("150") / D("510")), lot_a.opening_unit_price
        assert _close(lot_b.opening_unit_price, D("300") / D("510")), lot_b.opening_unit_price
        # The reward opened no lot of its own, and raised no issue
        assert REWARD_ID not in {lot.lot_id for lot in result.lots}
        assert result.issues == []
        assert result.analysis_status == "COMPLETE"

    def test_one_reward_merge_per_lot_with_its_ratio(self):
        result = _run(_golden())
        rows = sorted((merge.lot_id, merge.transaction_id, merge.date, merge.broker_id, merge.added_quantity, merge.ratio) for merge in result.reward_merges)
        assert rows == [(LOT_A, REWARD_ID, REWARD_DAY, BROKER, D("10"), D("510") / D("500")), (LOT_B, REWARD_ID, REWARD_DAY, BROKER, D("10"), D("510") / D("500"))]

    def test_the_fragments_unit_price_is_scaled_and_the_cost_kept(self):
        result = _run(_golden())
        for lot_id, cost in ((LOT_A, D("150")), (LOT_B, D("300"))):
            [fragment] = result.active_fragments(lot_id=lot_id)
            assert (fragment.quantity, fragment.broker_id, fragment.custody_type) == (D("510"), BROKER, "BROKER")
            assert _close(fragment.quantity * fragment.unit_price, cost), (lot_id, fragment.unit_price)

    def test_fifo_sale_of_20_realizes_8_1176(self):
        """FIFO takes the 20 from A: 20 × (0.70 − 150/510) = 14 − 3000/510 = 8.1176…"""
        result = _run(_golden("20"))
        assert {closure.lot_id for closure in result.closures if closure.transaction_id == SELL_ID} == {LOT_A}
        assert _close(_realized(result), D("14") - D("3000") / D("510")), _realized(result)
        assert _realized(result).quantize(D("0.0001")) == D("8.1176")

    def test_lifo_sale_of_20_realizes_2_2353(self):
        """LIFO takes the 20 from B, the newest lot: 20 × (0.70 − 300/510) = 14 − 6000/510 = 2.2352…"""
        result = _run(_golden("20"), method=LotMatchingMethod.LIFO)
        assert {closure.lot_id for closure in result.closures if closure.transaction_id == SELL_ID} == {LOT_B}
        assert _close(_realized(result), D("14") - D("6000") / D("510")), _realized(result)
        assert _realized(result).quantize(D("0.0001")) == D("2.2353")

    def test_full_sale_realizes_264_in_both_methods(self):
        """1 020 @0.70 = 714 of proceeds on 450 of cost: 264 realized, whatever the order."""
        for method in (LotMatchingMethod.FIFO, LotMatchingMethod.LIFO):
            result = _run(_golden("1020"), method=method)
            assert _close(_realized(result), D("264")), (method, _realized(result))
            assert all(result.get_lot(lot_id).open_quantity == D("0") for lot_id in (LOT_A, LOT_B)), method
            assert result.analysis_status == "COMPLETE", (method, _issue_codes(result))

    def test_own_lot_full_sale_is_254_realized_plus_10_income_the_same_264(self):
        """The OWN_LOT side of the same ledger: 254 realized and 10 of REWARD income — 264, the MERGED total."""
        income = EconomicEvent(transaction_id=REWARD_ID, broker_id=BROKER, asset_id=ASSET, date=REWARD_DAY, economic_type="REWARD", native_amount=D("10.00"), native_currency="EUR", target_amount=D("10.00"), target_currency="EUR")
        own = _run(_golden("1020"), allocation=OWN_LOT, events=[income])
        merged = _run(_golden("1020"))
        own_realized = _realized(own)
        own_income = sum((accumulator.gross_income for accumulator in own.economic_accumulators_by_lot.values()), D("0")) + own.asset_orphan_income
        assert (own_realized, own_income) == (D("254.00"), D("10.00"))
        assert _close(_realized(merged), own_realized + own_income)


# =============================================================================
# 2. Who takes a share: the lots held at the broker at the close of D-1
# =============================================================================


class TestWhoTakesAShare:
    def test_a_same_day_buy_takes_nothing(self):
        lot_c = 5
        result = _run([_buy(LOT_A, "100", "1", DAY_A), _buy(lot_c, "100", "1", REWARD_DAY), _reward(REWARD_ID, "10", "1", REWARD_DAY)])
        assert _merges(result) == {LOT_A: D("10")}
        assert (result.get_lot(LOT_A).original_quantity, result.get_lot(lot_c).original_quantity) == (D("110"), D("100"))

    def test_a_lot_arriving_on_the_reward_day_takes_nothing(self):
        """Lot A sits at broker 2 since 2025; lot B is bought at broker 1 and arrives at broker 2 on D itself (phase 1,
        before the merge): it is active there but was not held there at D-1, so A takes all of it."""
        transfer = _transfer(10, 11, "100", out_on=date(2026, 2, 20), in_on=REWARD_DAY, source=BROKER, destination=OTHER_BROKER)
        rows = [_buy(LOT_A, "100", "1", DAY_A, broker_id=OTHER_BROKER), _buy(LOT_B, "100", "1", DAY_B, broker_id=BROKER), *transfer, _reward(REWARD_ID, "10", "1", REWARD_DAY, broker_id=OTHER_BROKER)]
        result = _run(rows)
        # Precondition: B is at broker 2 after D, so pro rata to active quantity alone would have given it half
        assert [(fragment.broker_id, fragment.quantity) for fragment in result.active_fragments(lot_id=LOT_B)] == [(OTHER_BROKER, D("100"))]
        assert _merges(result) == {LOT_A: D("10")}
        assert "REWARD_NOT_MERGED_NO_OPEN_LOT" not in _issue_codes(result)

    def test_a_lot_held_at_another_broker_takes_nothing(self):
        result = _run([_buy(LOT_A, "100", "1", DAY_A), _buy(LOT_B, "300", "1", DAY_B, broker_id=OTHER_BROKER), _reward(REWARD_ID, "10", "1", REWARD_DAY)])
        assert _merges(result) == {LOT_A: D("10")}
        assert result.get_lot(LOT_B).original_quantity == D("300")

    def test_units_in_transit_take_no_part(self):
        """A 200 and B 100 at broker 1; 100 leave broker 1 before D (FIFO: from A) and arrive after D. At D the broker holds
        100 of A and 100 of B: 5 each. Counting the transit units would give A 2/3."""
        transfer = _transfer(10, 11, "100", out_on=date(2026, 2, 20), in_on=date(2026, 3, 10))
        rows = [_buy(LOT_A, "200", "1", DAY_A), _buy(LOT_B, "100", "2", DAY_B), *transfer, _reward(REWARD_ID, "10", "1", REWARD_DAY)]
        result = _run(rows)
        assert _merges(result) == {LOT_A: D("5"), LOT_B: D("5")}
        # The transit fragment of A kept its 100 units through the reward and arrived with them
        transit = [fragment for fragment in result.fragment_intervals if fragment.lot_id == LOT_A and fragment.custody_type == "IN_TRANSIT"]
        assert transit and all(fragment.quantity == D("100") for fragment in transit), [(fragment.fragment_id, fragment.quantity) for fragment in transit]
        assert {fragment.broker_id: fragment.quantity for fragment in result.active_fragments(lot_id=LOT_A)} == {BROKER: D("105"), OTHER_BROKER: D("100")}
        lot_a = result.get_lot(LOT_A)
        assert (lot_a.original_quantity, lot_a.original_cost) == (D("205"), D("200"))
        # The ratio is the whole lot's growth (its units in transit included): 205 / 200, the factor its unit cost falls by
        assert {merge.lot_id: merge.ratio for merge in result.reward_merges}[LOT_A] == D("205") / D("200")

    def test_a_split_on_the_reward_day_comes_first(self):
        """A 2:1 split on D (phase 2) before the merge (phase 3): lot A, held at D-1, takes the whole reward on its 200
        post-split units — ratio 210 / 200, not 110 / 100 — and the reward does not fall back to a lot of its own."""
        split = _tx(9, "ADJUSTMENT", "100", REWARD_DAY)
        result = _run([_buy(LOT_A, "100", "1", DAY_A), split, _reward(REWARD_ID, "10", "1", REWARD_DAY)], split_ratios={9: D("2")})
        assert [event.kind for event in result.classified_events if event.date == REWARD_DAY] == ["SPLIT", "REWARD_MERGE"]
        [merge] = result.reward_merges
        assert (merge.lot_id, merge.added_quantity, merge.ratio) == (LOT_A, D("10"), D("210") / D("200"))
        [fragment] = result.active_fragments(lot_id=LOT_A)
        assert fragment.quantity == D("210")
        assert _close(fragment.quantity * fragment.unit_price, D("100"))
        assert "REWARD_NOT_MERGED_NO_OPEN_LOT" not in _issue_codes(result)

    def test_a_reward_merge_comes_before_a_same_day_sale(self):
        """Phase 3 before phase 5: a same-day SELL finds the merged units (no oversell, no short)."""
        result = _run([_buy(LOT_A, "100", "1", DAY_A), _reward(REWARD_ID, "10", "1", REWARD_DAY), _sell(SELL_ID, "110", "2", REWARD_DAY)])
        assert result.get_lot(LOT_A).open_quantity == D("0")
        assert _close(_realized(result), D("220") - D("100"))
        assert result.analysis_status == "COMPLETE", _issue_codes(result)

    def test_the_reference_price_is_rescaled_like_a_split(self):
        """An ADJUSTMENT-in with no cost gets a reference price (10): the merge of 100 units into its 100 halves it."""
        adjustment = _tx(LOT_A, "ADJUSTMENT", "100", DAY_A)
        result = _run([adjustment, _reward(REWARD_ID, "100", "1", REWARD_DAY)], reference_price_lookup=lambda _asset, _day: ReferencePriceResolution(price=D("10"), source="exact"))
        lot = result.get_lot(LOT_A)
        assert (lot.original_quantity, lot.original_cost, lot.opening_unit_price) == (D("200"), D("0"), D("0"))
        assert lot.reference_unit_price == D("5")


# =============================================================================
# 3. Rounding: the shares add up to the reward exactly
# =============================================================================


class TestFragmentsOfOneLot:
    """Within a lot, the share is spread over its fragments at the broker, pro rata, the largest taking the rest."""

    def _ledger(self) -> list[FifoInputTransaction]:
        """Lot A, 200 at broker 1; 150 go to broker 2 in January, 100 come back in February: at D-1 broker 1 holds A in two
        fragments (50 that never left, 100 that came back), broker 2 holds the other 50."""
        away = _transfer(10, 11, "150", out_on=date(2026, 1, 5), in_on=date(2026, 1, 6))
        back = _transfer(12, 13, "100", out_on=date(2026, 2, 5), in_on=date(2026, 2, 6), source=OTHER_BROKER, destination=BROKER)
        return [_buy(LOT_A, "200", "1", DAY_A), *away, *back, _reward(REWARD_ID, "1", "1", REWARD_DAY)]

    def test_precondition_two_unequal_fragments_at_the_broker(self):
        rows = [row for row in self._ledger() if row.id != REWARD_ID]
        before = _run(rows)
        assert sorted(fragment.quantity for fragment in before.active_fragments(lot_id=LOT_A) if fragment.broker_id == BROKER) == [D("50"), D("100")]

    def test_the_fragments_take_one_third_and_two_thirds_and_add_up_exactly(self):
        result = _run(self._ledger())
        [merge] = result.reward_merges
        # The ratio is the whole lot's growth (its 50 units at broker 2 included): 201 / 200
        assert (merge.lot_id, merge.added_quantity, merge.ratio) == (LOT_A, D("1"), D("201") / D("200"))
        at_broker = {fragment.fragment_id: fragment.quantity for fragment in result.active_fragments(lot_id=LOT_A) if fragment.broker_id == BROKER}
        assert sum(at_broker.values(), D("0")) == D("151"), at_broker
        larger, smaller = sorted(at_broker.values(), reverse=True)
        assert larger - D("100") > smaller - D("50"), "the larger fragment did not take the larger part"
        # Each part cut to the quantity precision (1e-10), the larger fragment taking the rest
        assert (larger, smaller) == (D("100.6666666667"), D("50.3333333333")), at_broker
        # The units at broker 2 took no part
        assert [fragment.quantity for fragment in result.active_fragments(lot_id=LOT_A) if fragment.broker_id == OTHER_BROKER] == [D("50")]
        lot = result.get_lot(LOT_A)
        assert (lot.original_quantity, lot.open_quantity, lot.original_cost) == (D("201"), D("201"), D("200"))

    def test_a_full_sale_afterwards_leaves_nothing_open(self):
        rows = [*self._ledger(), _sell(SELL_ID, "151", "2", SELL_DAY), _sell(SELL_ID + 1, "50", "2", SELL_DAY, broker_id=OTHER_BROKER)]
        result = _run(rows)
        assert result.get_lot(LOT_A).open_quantity == D("0")
        assert result.active_fragments(lot_id=LOT_A) == []
        assert result.analysis_status == "COMPLETE", _issue_codes(result)
        assert _close(_realized(result, SELL_ID) + _realized(result, SELL_ID + 1), D("402") - D("200"))


class TestRounding:
    def test_thirds_add_up_and_the_largest_takes_the_rest(self):
        """Lots of 100 (the oldest, lowest id) and 200 share 1 unit: 1/3 and 2/3 cut to 1e-10 lose 1e-10, which goes to
        the 200 lot — the largest, though neither the oldest nor the lowest id."""
        result = _run([_buy(LOT_A, "100", "1", DAY_A), _buy(LOT_B, "200", "1", DAY_B), _reward(REWARD_ID, "1", "1", REWARD_DAY)])
        shares = _merges(result)
        assert shares == {LOT_A: D("0.3333333333"), LOT_B: D("0.6666666667")}
        assert sum(shares.values(), D("0")) == D("1")
        assert (result.get_lot(LOT_A).original_quantity, result.get_lot(LOT_B).original_quantity) == (D("100.3333333333"), D("200.6666666667"))

    def test_on_a_tie_the_oldest_takes_the_rest_whatever_its_id(self):
        """Three lots of 100: the oldest is lot 7, opened in 2023, with the highest id; it takes the 1e-10."""
        oldest = 7
        rows = [_buy(oldest, "100", "1", date(2023, 5, 1)), _buy(LOT_A, "100", "1", DAY_A), _buy(LOT_B, "100", "1", DAY_B), _reward(REWARD_ID, "1", "1", REWARD_DAY)]
        shares = _merges(_run(rows))
        assert shares == {oldest: D("0.3333333334"), LOT_A: D("0.3333333333"), LOT_B: D("0.3333333333")}
        assert sum(shares.values(), D("0")) == D("1")

    def test_on_a_tie_of_date_the_lowest_id_takes_the_rest(self):
        rows = [_buy(LOT_B, "100", "1", DAY_A), _buy(LOT_A, "100", "1", DAY_A), _buy(5, "100", "1", DAY_A), _reward(REWARD_ID, "1", "1", REWARD_DAY)]
        assert _merges(_run(rows)) == {LOT_A: D("0.3333333334"), LOT_B: D("0.3333333333"), 5: D("0.3333333333")}


# =============================================================================
# 4. No lot held the day before: a lot of its own at cost 0, informational issue
# =============================================================================


class TestNoLotHeldTheDayBefore:
    def test_an_airdrop_opens_its_own_lot_at_no_cost(self):
        result = _run([_reward(REWARD_ID, "20", "0.50", REWARD_DAY)])
        lot = result.get_lot(REWARD_ID)
        assert (lot.direction, lot.opening_date, lot.original_quantity, lot.opening_unit_price, lot.original_cost, lot.currency) == ("LONG", REWARD_DAY, D("20"), D("0"), D("0"), "EUR")
        assert result.reward_merges == []
        [issue] = result.issues
        assert (issue.code, issue.transaction_id, issue.lot_id, issue.broker_id) == ("REWARD_NOT_MERGED_NO_OPEN_LOT", REWARD_ID, REWARD_ID, BROKER)
        assert result.analysis_status == "COMPLETE"

    def test_a_same_day_buy_does_not_count_as_held(self):
        """A BUY on D is not held at D-1: the reward still keeps a lot of its own, and the BUY's lot does not grow."""
        result = _run([_buy(LOT_A, "100", "1", REWARD_DAY), _reward(REWARD_ID, "20", "0.50", REWARD_DAY)])
        assert result.reward_merges == []
        assert result.get_lot(LOT_A).original_quantity == D("100")
        assert result.get_lot(REWARD_ID).original_cost == D("0")
        assert _issue_codes(result) == ["REWARD_NOT_MERGED_NO_OPEN_LOT"]

    def test_the_own_lot_is_in_the_cost_basis_currency(self):
        lot = _run([_reward(REWARD_ID, "4", "1.25", REWARD_DAY, currency="USD")]).get_lot(REWARD_ID)
        assert (lot.currency, lot.opening_unit_price, lot.original_cost) == ("USD", D("0"), D("0"))

    def test_another_issue_still_degrades_the_analysis(self):
        """The informational code is left out of the status, not the others: an orphan DIVIDEND degrades it."""
        dividend = EconomicEvent(transaction_id=60, broker_id=BROKER, asset_id=ASSET, date=date(2026, 1, 15), economic_type="DIVIDEND", native_amount=D("3"), native_currency="EUR", target_amount=D("3"), target_currency="EUR")
        result = _run([_reward(REWARD_ID, "20", "0.50", REWARD_DAY)], events=[dividend])
        assert set(_issue_codes(result)) == {"REWARD_NOT_MERGED_NO_OPEN_LOT", "ASSET_INCOME_NO_ELIGIBLE_LOTS"}
        assert result.analysis_status == "DEGRADED"


# =============================================================================
# 5. OWN_LOT, the default, is unchanged
# =============================================================================


class TestOwnLotUnchanged:
    def test_the_default_is_own_lot(self):
        result = run_fifo_lot_engine(_golden(), {BROKER: False})
        assert result.reward_allocation is OWN_LOT
        assert result.reward_merges == []
        assert [event.kind for event in result.classified_events if event.transaction_id == REWARD_ID] == ["REWARD"]

    def test_own_lot_opens_the_dated_lot_at_its_value(self):
        result = _run(_golden(), allocation=OWN_LOT)
        assert result.reward_merges == []
        lot = result.get_lot(REWARD_ID)
        assert (lot.original_quantity, lot.opening_unit_price, lot.original_cost) == (D("20"), D("0.50"), D("10.00"))
        assert (result.get_lot(LOT_A).original_quantity, result.get_lot(LOT_B).original_quantity) == (D("500"), D("500"))

    def test_own_lot_airdrop_raises_no_merge_issue(self):
        result = _run([_reward(REWARD_ID, "20", "0.50", REWARD_DAY)], allocation=OWN_LOT)
        assert "REWARD_NOT_MERGED_NO_OPEN_LOT" not in _issue_codes(result)
        assert result.get_lot(REWARD_ID).original_cost == D("10.00")
