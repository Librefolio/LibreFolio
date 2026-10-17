"""Unit tests for ScopeAwareTransactionClassifier.

Pure tests — no DB, no async, no fixtures. Uses mock Transaction objects.

``TestShareMismatch`` (J-43) reads ``ShareMismatch`` and ``ClassificationResult.share_mismatches`` inside its tests, so
on a ``models`` without them only those tests fail, never the module's collection.
"""

import functools
import re
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

import backend.app.services.financial_math.portfolio.models as portfolio_models
from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier

# =============================================================================
# HELPERS — Mock Transaction builder
# =============================================================================


def _tx(
    *,
    id: int,
    broker_id: int,
    type: str,
    dt: str,
    amount: str = "0",
    currency: str | None = "EUR",
    quantity: str = "0",
    asset_id: int | None = None,
    related_id: int | None = None,
    cost_basis_override: str | None = None,
    cost_basis_currency: str | None = None,
) -> MagicMock:
    """Build a mock Transaction with the fields used by the classifier."""
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


# =============================================================================
# TESTS
# =============================================================================


class TestUnlinkedTransactions:
    """Unlinked transactions are always 'normal'."""

    def test_unlinked_deposit(self):
        """DEPOSIT without related_id → normal + external cash flow."""
        txs = [_tx(id=1, broker_id=10, type="DEPOSIT", dt="2025-01-01", amount="1000")]
        c = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=txs, broker_shares={10: Decimal("1")})
        result = c.classify()

        assert len(result.classified) == 1
        assert result.classified[0].classification == "normal"
        assert len(result.external_cash_flows) == 1
        assert result.external_cash_flows[0] == (date(2025, 1, 1), 10, Decimal("1000"), "EUR")

    def test_unlinked_withdrawal(self):
        """WITHDRAWAL → normal + external cash flow (negative)."""
        txs = [_tx(id=2, broker_id=10, type="WITHDRAWAL", dt="2025-02-01", amount="-500")]
        c = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=txs, broker_shares={10: Decimal("1")})
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert result.external_cash_flows[0][2] == Decimal("-500")

    def test_unlinked_buy(self):
        """BUY → normal, no external cash flow (internal capital movement)."""
        txs = [
            _tx(id=3, broker_id=10, type="BUY", dt="2025-01-15", amount="-400", quantity="10", asset_id=100),
        ]
        c = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=txs, broker_shares={10: Decimal("1")})
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert len(result.external_cash_flows) == 0

    def test_unlinked_fee(self):
        """FEE → normal, no external cash flow."""
        txs = [_tx(id=4, broker_id=10, type="FEE", dt="2025-01-20", amount="-10")]
        c = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=txs, broker_shares={10: Decimal("1")})
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert len(result.external_cash_flows) == 0


class TestLinkedInternalSameDay:
    """Linked internal pairs where both legs are in scope and same date."""

    def test_cash_transfer_same_day(self):
        """CASH_TRANSFER between two scope brokers, same day → linked_internal, no in-transit."""
        tx_out = _tx(id=10, broker_id=10, type="CASH_TRANSFER", dt="2025-03-01", amount="-5000", related_id=11)
        tx_in = _tx(id=11, broker_id=20, type="CASH_TRANSFER", dt="2025-03-01", amount="5000", related_id=10)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[tx_out, tx_in],
            broker_shares={10: Decimal("1"), 20: Decimal("1")},
        )
        result = c.classify()

        assert len(result.classified) == 2
        for ct in result.classified:
            assert ct.classification == "linked_internal"
        assert len(result.in_transit_intervals) == 0
        assert len(result.external_cash_flows) == 0

    def test_fx_conversion_same_day(self):
        """FX_CONVERSION between scope brokers, same day → linked_internal."""
        tx_eur = _tx(id=20, broker_id=10, type="FX_CONVERSION", dt="2025-04-01", amount="-1000", currency="EUR", related_id=21)
        tx_usd = _tx(id=21, broker_id=10, type="FX_CONVERSION", dt="2025-04-01", amount="1090", currency="USD", related_id=20)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx_eur, tx_usd],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify()

        assert all(ct.classification == "linked_internal" for ct in result.classified)
        assert len(result.in_transit_intervals) == 0
        assert len(result.external_cash_flows) == 0


class TestLinkedInternalDifferentDates:
    """Linked internal pairs with different dates → in-transit interval."""

    def test_cash_transfer_different_dates(self):
        """CASH_TRANSFER: departure 03-01, arrival 03-04 → in-transit [03-01, 03-03].

        [min(dep,arr), max(dep,arr)) convention (plan v2 §7.2): departure date is
        included (value leaves the source and enters transit same day, no hole),
        arrival date is excluded (destination custody starts there).
        """
        tx_out = _tx(id=30, broker_id=10, type="CASH_TRANSFER", dt="2025-03-01", amount="-5000", related_id=31)
        tx_in = _tx(id=31, broker_id=20, type="CASH_TRANSFER", dt="2025-03-04", amount="5000", related_id=30)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[tx_out, tx_in],
            broker_shares={10: Decimal("1"), 20: Decimal("1")},
        )
        result = c.classify()

        assert all(ct.classification == "linked_internal" for ct in result.classified)
        assert len(result.in_transit_intervals) == 1

        it = result.in_transit_intervals[0]
        assert it.start_date == date(2025, 3, 1)
        assert it.end_date == date(2025, 3, 3)
        assert it.tx_type == "cash"
        assert it.departure_leg.id == 30
        assert it.arrival_leg.id == 31

    def test_asset_transfer_different_dates(self):
        """TRANSFER: asset moves between brokers with different dates → in-transit [05-01, 05-04]."""
        tx_out = _tx(
            id=40,
            broker_id=10,
            type="TRANSFER",
            dt="2025-05-01",
            quantity="-100",
            asset_id=200,
            related_id=41,
            cost_basis_override="50.00",
            cost_basis_currency="EUR",
        )
        tx_in = _tx(
            id=41,
            broker_id=20,
            type="TRANSFER",
            dt="2025-05-05",
            quantity="100",
            asset_id=200,
            related_id=40,
        )
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[tx_out, tx_in],
            broker_shares={10: Decimal("1"), 20: Decimal("1")},
        )
        result = c.classify()

        assert len(result.in_transit_intervals) == 1
        it = result.in_transit_intervals[0]
        assert it.start_date == date(2025, 5, 1)
        assert it.end_date == date(2025, 5, 4)
        assert it.tx_type == "asset"
        assert it.asset_id == 200
        assert it.cost_basis_amount == Decimal("50.00")
        assert it.cost_basis_currency == "EUR"

    def test_adjacent_days_transit_covers_departure_day(self):
        """Adjacent days (T, T+1) → 1-day in-transit window on the departure day.

        Regression test for the value-hole fixed by the [min,max) convention: the
        old dep+1..arr-1 convention returned an EMPTY window here (start > end),
        meaning the value vanished entirely on day T (already 0 at the source
        broker, not yet counted anywhere else). The new convention covers day T.
        """
        tx_out = _tx(id=50, broker_id=10, type="CASH_TRANSFER", dt="2025-06-01", amount="-1000", related_id=51)
        tx_in = _tx(id=51, broker_id=20, type="CASH_TRANSFER", dt="2025-06-02", amount="1000", related_id=50)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[tx_out, tx_in],
            broker_shares={10: Decimal("1"), 20: Decimal("1")},
        )
        result = c.classify()

        assert all(ct.classification == "linked_internal" for ct in result.classified)
        assert len(result.in_transit_intervals) == 1
        it = result.in_transit_intervals[0]
        assert it.start_date == date(2025, 6, 1)
        assert it.end_date == date(2025, 6, 1)

    def test_same_day_transfer_no_transit(self):
        """Same-day transfer (both legs dated T) → no in-transit window at all.

        This is the ONLY case that still returns an empty window under the
        [min,max) convention (start == end + 1 day → start > end).
        """
        tx_out = _tx(id=52, broker_id=10, type="CASH_TRANSFER", dt="2025-06-10", amount="-1000", related_id=53)
        tx_in = _tx(id=53, broker_id=20, type="CASH_TRANSFER", dt="2025-06-10", amount="1000", related_id=52)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[tx_out, tx_in],
            broker_shares={10: Decimal("1"), 20: Decimal("1")},
        )
        result = c.classify()

        assert len(result.in_transit_intervals) == 0

    def test_out_leg_dated_after_in_leg_still_resolves_chronologically(self):
        """Negative-amount ("out") leg dated after positive-amount ("in") leg.

        Direction of the in-transit window depends on chronological order, not
        on which leg is semantically the outflow/inflow (plan v2 §7.1: "la
        direzione dipende dai segni, non dall'ordine delle date" for FIFO — but
        for the aggregate transit *bucket*, chronological min/max governs
        instead). Here the negative-amount leg is dated LATER than the
        positive-amount leg; departure/arrival must still follow chronology.
        """
        tx_negative_but_later = _tx(id=54, broker_id=10, type="CASH_TRANSFER", dt="2025-07-05", amount="-2000", related_id=55)
        tx_positive_but_earlier = _tx(id=55, broker_id=20, type="CASH_TRANSFER", dt="2025-07-01", amount="2000", related_id=54)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[tx_negative_but_later, tx_positive_but_earlier],
            broker_shares={10: Decimal("1"), 20: Decimal("1")},
        )
        result = c.classify()

        assert len(result.in_transit_intervals) == 1
        it = result.in_transit_intervals[0]
        # Chronologically earlier leg (id=55, 07-01) is the departure regardless
        # of its positive amount sign.
        assert it.departure_leg.id == 55
        assert it.arrival_leg.id == 54
        assert it.start_date == date(2025, 7, 1)
        assert it.end_date == date(2025, 7, 4)


class TestLinkedExternal:
    """Linked pairs where only one leg is in scope."""

    def test_external_outflow(self):
        """CASH_TRANSFER: only outflow leg in scope → linked_external_outflow."""
        tx_out = _tx(id=60, broker_id=10, type="CASH_TRANSFER", dt="2025-07-01", amount="-3000", related_id=61)
        # Paired tx is outside scope (broker 99)
        tx_in = _tx(id=61, broker_id=99, type="CASH_TRANSFER", dt="2025-07-02", amount="3000", related_id=60)

        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx_out],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify(external_paired={61: tx_in})

        assert len(result.classified) == 1
        assert result.classified[0].classification == "linked_external_outflow"
        assert len(result.external_cash_flows) == 1
        assert result.external_cash_flows[0][2] == Decimal("-3000")

    def test_external_inflow(self):
        """CASH_TRANSFER: only inflow leg in scope → linked_external_inflow."""
        tx_in = _tx(id=71, broker_id=10, type="CASH_TRANSFER", dt="2025-07-02", amount="3000", related_id=70)
        tx_out = _tx(id=70, broker_id=99, type="CASH_TRANSFER", dt="2025-07-01", amount="-3000", related_id=71)

        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx_in],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify(external_paired={70: tx_out})

        assert result.classified[0].classification == "linked_external_inflow"
        assert result.external_cash_flows[0][2] == Decimal("3000")

    def test_asset_transfer_external_inflow(self):
        """TRANSFER: asset arrives from outside scope → linked_external_inflow."""
        tx_in = _tx(
            id=81,
            broker_id=10,
            type="TRANSFER",
            dt="2025-08-01",
            quantity="50",
            asset_id=300,
            related_id=80,
        )
        tx_out = _tx(
            id=80,
            broker_id=99,
            type="TRANSFER",
            dt="2025-07-30",
            quantity="-50",
            asset_id=300,
            related_id=81,
        )

        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx_in],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify(external_paired={80: tx_out})

        assert result.classified[0].classification == "linked_external_inflow"
        # No cash flow for an asset transfer (amount=0): the capital of this leg is booked by
        # DailyStateBuilder at market value on the leg's own date (lot 41, D2), not here.
        assert len(result.external_cash_flows) == 0


class TestEdgeCases:
    """Edge cases: missing pairs, share mismatch, etc."""

    def test_missing_paired_tx_warning(self):
        """Linked tx whose pair doesn't exist → normal + warning."""
        tx = _tx(id=90, broker_id=10, type="CASH_TRANSFER", dt="2025-09-01", amount="-1000", related_id=999)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert len(result.warnings) == 1
        assert "999" in result.warnings[0]
        # Still treated as external cash flow since pair is missing
        assert len(result.external_cash_flows) == 1

    def test_share_mismatch_warning(self):
        """Internal pair with different share percentages → warning."""
        tx_a = _tx(id=100, broker_id=10, type="CASH_TRANSFER", dt="2025-10-01", amount="-1000", related_id=101)
        tx_b = _tx(id=101, broker_id=20, type="CASH_TRANSFER", dt="2025-10-03", amount="1000", related_id=100)

        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[tx_a, tx_b],
            broker_shares={10: Decimal("0.5"), 20: Decimal("1")},
        )
        result = c.classify()

        assert any("share mismatch" in w for w in result.warnings)

    def test_share_applied_to_external_cash_flow(self):
        """Share percentage scales external cash flows."""
        tx = _tx(id=110, broker_id=10, type="DEPOSIT", dt="2025-11-01", amount="2000")
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx],
            broker_shares={10: Decimal("0.5")},
        )
        result = c.classify()

        assert result.external_cash_flows[0][2] == Decimal("1000")
        assert result.classified[0].share == Decimal("0.5")

    def test_get_needed_paired_ids(self):
        """get_needed_paired_ids returns IDs not in scope transactions."""
        tx = _tx(id=120, broker_id=10, type="CASH_TRANSFER", dt="2025-12-01", amount="-1000", related_id=999)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx],
            broker_shares={10: Decimal("1")},
        )
        needed = c.get_needed_paired_ids()
        assert needed == {999}

    def test_adjustment_linked(self):
        """ADJUSTMENT with related_transaction_id (e.g. stock split) → linked."""
        adj_a = _tx(id=130, broker_id=10, type="ADJUSTMENT", dt="2025-01-15", quantity="100", asset_id=400, related_id=131)
        adj_b = _tx(id=131, broker_id=20, type="ADJUSTMENT", dt="2025-01-15", quantity="-100", asset_id=400, related_id=130)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[adj_a, adj_b],
            broker_shares={10: Decimal("1"), 20: Decimal("1")},
        )
        result = c.classify()

        assert all(ct.classification == "linked_internal" for ct in result.classified)
        assert len(result.in_transit_intervals) == 0  # same day


class TestNoExternalCashFlowForInternalTransfers:
    """Internal transfers MUST NOT generate external cash flows."""

    def test_internal_cash_transfer_no_ecf(self):
        """Cash transfer between two scope brokers → zero external cash flows."""
        tx_a = _tx(id=200, broker_id=10, type="CASH_TRANSFER", dt="2025-03-01", amount="-5000", related_id=201)
        tx_b = _tx(id=201, broker_id=20, type="CASH_TRANSFER", dt="2025-03-03", amount="5000", related_id=200)

        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10, 20},
            all_transactions=[tx_a, tx_b],
            broker_shares={10: Decimal("1"), 20: Decimal("1")},
        )
        result = c.classify()

        assert len(result.external_cash_flows) == 0
        assert all(ct.classification == "linked_internal" for ct in result.classified)

    def test_internal_fx_conversion_no_ecf(self):
        """FX conversion within scope broker → zero external cash flows."""
        tx_eur = _tx(id=210, broker_id=10, type="FX_CONVERSION", dt="2025-04-01", amount="-1000", currency="EUR", related_id=211)
        tx_usd = _tx(id=211, broker_id=10, type="FX_CONVERSION", dt="2025-04-01", amount="1090", currency="USD", related_id=210)

        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx_eur, tx_usd],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify()

        assert len(result.external_cash_flows) == 0


class TestOrphanLinkedTypes:
    """Lot 41, D5: a linked type with no related_transaction_id at all (an orphan).

    A CASH_TRANSFER or FX_CONVERSION orphan with an amount moves money across the scope
    boundary like a DEPOSIT / WITHDRAWAL, so it is an external cash flow at the broker's
    share. An orphan TRANSFER has amount 0: the classifier gives it no cash flow, and its
    capital is booked by DailyStateBuilder at market value (D2).
    """

    def test_orphan_cash_transfer_is_external_cash_flow(self):
        """Today: no external cash flow (unlinked, only DEPOSIT / WITHDRAWAL get one)."""
        tx = _tx(id=300, broker_id=20, type="CASH_TRANSFER", dt="2025-05-01", amount="1000")
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={20},
            all_transactions=[tx],
            broker_shares={20: Decimal("0.5")},
        )
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert result.external_cash_flows == [(date(2025, 5, 1), 20, Decimal("500"), "EUR")]

    def test_orphan_fx_conversion_is_external_cash_flow(self):
        """Today: no external cash flow (unlinked, only DEPOSIT / WITHDRAWAL get one)."""
        tx = _tx(id=301, broker_id=10, type="FX_CONVERSION", dt="2025-05-02", amount="-1000", currency="USD")
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert result.external_cash_flows == [(date(2025, 5, 2), 10, Decimal("-1000"), "USD")]

    def test_orphan_transfer_has_no_external_cash_flow(self):
        """Guard: an orphan TRANSFER (asset, amount 0) gets no cash flow from the classifier."""
        tx = _tx(id=302, broker_id=10, type="TRANSFER", dt="2025-05-03", currency=None, quantity="10", asset_id=500)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert result.warnings == []
        assert result.external_cash_flows == []

    def test_dangling_transfer_has_no_external_cash_flow(self):
        """Guard: a TRANSFER whose partner (999) is not found is 'normal' with a warning, and
        still gets no cash flow from the classifier (amount 0)."""
        tx = _tx(id=303, broker_id=10, type="TRANSFER", dt="2025-05-04", currency=None, quantity="10", asset_id=500, related_id=999)
        c = ScopeAwareTransactionClassifier(
            scope_broker_ids={10},
            all_transactions=[tx],
            broker_shares={10: Decimal("1")},
        )
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert len(result.warnings) == 1
        assert "999" in result.warnings[0]
        assert result.external_cash_flows == []


# =============================================================================
# J-43 — A LINKED INTERNAL PAIR BETWEEN BROKERS OWNED AT DIFFERENT SHARES
# =============================================================================


def _share_mismatch(*, tx_ids: tuple[int, int], broker_ids: tuple[int, int], shares: tuple[str, str], dt: str):
    """A ``ShareMismatch`` (J-43), read from ``models`` when the test runs."""
    return portfolio_models.ShareMismatch(tx_ids=tx_ids, broker_ids=broker_ids, shares=(Decimal(shares[0]), Decimal(shares[1])), date=date.fromisoformat(dt))


def _share_mismatch_warnings(result) -> list[str]:
    """The classifier's warnings about a share mismatch (its text says "share mismatch", as on HEAD)."""
    return [warning for warning in result.warnings if "share mismatch" in warning]


def _numbers_in(text: str) -> set[int]:
    """Every integer written in ``text``, whole: 401 is not found in 4012."""
    return {int(number) for number in re.findall(r"\d+", text)}


def _classifications(result) -> dict[int, str]:
    return {ct.tx.id: ct.classification for ct in result.classified}


def _same_day_pair(listed: str) -> ScopeAwareTransactionClassifier:
    """1000 EUR from broker 10 (share 1) to broker 20 (share 0.5), both legs on 2025-10-01. The leg received has the
    lower id, 401, so the engine's loading order (date, id) meets it first; ``reversed`` meets the leg sent (402) first."""
    sent = _tx(id=402, broker_id=10, type="CASH_TRANSFER", dt="2025-10-01", amount="-1000", related_id=401)
    received = _tx(id=401, broker_id=20, type="CASH_TRANSFER", dt="2025-10-01", amount="1000", related_id=402)
    txs = [received, sent] if listed == "loading_order" else [sent, received]
    return ScopeAwareTransactionClassifier(scope_broker_ids={10, 20}, all_transactions=txs, broker_shares={10: Decimal("1"), 20: Decimal("0.5")})


def _different_day_pair(sent_id: int, received_id: int, listed: str) -> ScopeAwareTransactionClassifier:
    """1000 EUR from broker 10 (share 1), sent on 2025-10-01, to broker 20 (share 0.5), received on 2025-10-03.
    ``loading_order`` meets the leg sent first (the engine's order, by date); ``received_first`` the other one."""
    sent = _tx(id=sent_id, broker_id=10, type="CASH_TRANSFER", dt="2025-10-01", amount="-1000", related_id=received_id)
    received = _tx(id=received_id, broker_id=20, type="CASH_TRANSFER", dt="2025-10-03", amount="1000", related_id=sent_id)
    txs = [sent, received] if listed == "loading_order" else [received, sent]
    return ScopeAwareTransactionClassifier(scope_broker_ids={10, 20}, all_transactions=txs, broker_shares={10: Decimal("1"), 20: Decimal("0.5")})


# (id of the leg sent, id of the leg received, order met, the ShareMismatch's broker_ids and shares). The ids are 411 and
# 412 in every case, so the expected tx_ids are (411, 412) and the date the received leg's, 2025-10-03. Between them the
# cases tell the later leg's date from the date of the leg met first, of the leg met second and of either id, and the
# lower id first from the leg met first.
_DIFFERENT_DAY_CASES = [
    pytest.param(411, 412, "loading_order", (10, 20), ("1", "0.5"), id="sent_leg_first_with_the_lower_id"),
    pytest.param(412, 411, "loading_order", (20, 10), ("0.5", "1"), id="sent_leg_first_with_the_higher_id"),
    pytest.param(412, 411, "received_first", (20, 10), ("0.5", "1"), id="received_leg_first_with_the_lower_id"),
]


def _equal_shares_pair(share: str, received_on: str):
    """1000 EUR from broker 10 to broker 20, both owned at ``share``: sent on 2025-11-03, received on ``received_on``."""
    sent = _tx(id=601, broker_id=10, type="CASH_TRANSFER", dt="2025-11-03", amount="-1000", related_id=602)
    received = _tx(id=602, broker_id=20, type="CASH_TRANSFER", dt=received_on, amount="1000", related_id=601)
    classifier = ScopeAwareTransactionClassifier(scope_broker_ids={10, 20}, all_transactions=[sent, received], broker_shares={10: Decimal(share), 20: Decimal(share)})
    return classifier, None, {601: "linked_internal", 602: "linked_internal"}


def _conversion_at_one_broker():
    """EUR -> USD at broker 10, owned at 0.5: both legs at one broker, so at one share."""
    eur_leg = _tx(id=611, broker_id=10, type="FX_CONVERSION", dt="2025-11-04", amount="-1000", currency="EUR", related_id=612)
    usd_leg = _tx(id=612, broker_id=10, type="FX_CONVERSION", dt="2025-11-04", amount="1090", currency="USD", related_id=611)
    classifier = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=[eur_leg, usd_leg], broker_shares={10: Decimal("0.5")})
    return classifier, None, {611: "linked_internal", 612: "linked_internal"}


def _linked_external_leg():
    """Broker 10, owned at 0.5, sends 1000 EUR to broker 99, outside the scope (absent from ``broker_shares``, so at 1
    for the classifier): only one leg is in the scope."""
    sent = _tx(id=621, broker_id=10, type="CASH_TRANSFER", dt="2025-11-05", amount="-1000", related_id=622)
    received = _tx(id=622, broker_id=99, type="CASH_TRANSFER", dt="2025-11-05", amount="1000", related_id=621)
    classifier = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=[sent], broker_shares={10: Decimal("0.5")})
    return classifier, {622: received}, {621: "linked_external_outflow"}


def _unlinked_rows():
    """A DEPOSIT and an orphan CASH_TRANSFER (no related id) at broker 10, owned at 0.5."""
    deposit = _tx(id=631, broker_id=10, type="DEPOSIT", dt="2025-11-06", amount="2000")
    orphan = _tx(id=632, broker_id=10, type="CASH_TRANSFER", dt="2025-11-06", amount="-500")
    classifier = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=[deposit, orphan], broker_shares={10: Decimal("0.5")})
    return classifier, None, {631: "normal", 632: "normal"}


def _pair_not_found():
    """A CASH_TRANSFER at broker 10, owned at 0.5, whose related id (999) is nowhere."""
    dangling = _tx(id=641, broker_id=10, type="CASH_TRANSFER", dt="2025-11-07", amount="-1000", related_id=999)
    classifier = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=[dangling], broker_shares={10: Decimal("0.5")})
    return classifier, None, {641: "normal"}


# Everything that is not a linked internal pair between two different shares: (classifier, external_paired, the
# classification expected for each id).
_NO_MISMATCH_CASES = [
    pytest.param(functools.partial(_equal_shares_pair, "1", "2025-11-03"), id="equal_shares_full_same_day"),
    pytest.param(functools.partial(_equal_shares_pair, "0.5", "2025-11-03"), id="equal_shares_half_same_day"),
    pytest.param(functools.partial(_equal_shares_pair, "0.5", "2025-11-05"), id="equal_shares_half_two_days_later"),
    pytest.param(_conversion_at_one_broker, id="fx_conversion_at_one_broker"),
    pytest.param(_linked_external_leg, id="linked_external_leg"),
    pytest.param(_unlinked_rows, id="unlinked_rows"),
    pytest.param(_pair_not_found, id="pair_not_found"),
]


class TestShareMismatch:
    """J-43 — a linked internal pair whose two brokers the user owns at different shares.

    Each leg counts at its own broker's share (``broker_shares``), so the gap between the two legs is booked as P&L on
    purpose (D-MF4 = a, test_transfer_keeps_returns.py): the "share mismatch" warning is the user's only explanation of
    that P&L.

    - J-43a: the warning comes for every such pair, the same day or not, once per pair. On HEAD 252835dce it sits in
      the in-transit branch (``tx.date != paired.date``), so a same-day pair never warns.
    - J-43b: the classifier also returns it as data, ``ClassificationResult.share_mismatches``: one ``ShareMismatch`` per
      pair, its two transaction ids lower id first, each one's broker and share (``broker_shares``) in that order, dated
      at the later leg. On HEAD neither exists (AttributeError).

    Equal shares, a linked leg whose other leg is outside the scope, an unlinked row, a leg whose pair is not found:
    neither a warning nor a ``ShareMismatch``. ``TestEdgeCases.test_share_mismatch_warning`` stays as it is.
    """

    @pytest.mark.parametrize("listed", ["loading_order", "reversed"])
    def test_same_day_pair_at_different_shares_warns_once(self, listed):
        """Red (J-43a). The same-day pair 401/402 between shares 0.5 and 1 gives one "share mismatch" warning naming
        both legs, whichever leg the classifier meets first.

        HEAD: no warning at all — a same-day pair never enters the branch that warns."""
        result = _same_day_pair(listed).classify()

        assert _classifications(result) == {401: "linked_internal", 402: "linked_internal"}
        mismatch_warnings = _share_mismatch_warnings(result)
        assert len(mismatch_warnings) == 1, result.warnings
        assert {401, 402} <= _numbers_in(mismatch_warnings[0]), mismatch_warnings

    @pytest.mark.parametrize("listed", ["loading_order", "reversed"])
    def test_same_day_pair_at_different_shares_records_one_share_mismatch(self, listed):
        """Red (J-43b). The same pair as data: exactly one ShareMismatch — ids (401, 402), lower first; the brokers of
        401 and 402 in that order, (20, 10); their shares, (0.5, 1); dated 2025-10-01 — whichever leg comes first.

        HEAD: AttributeError — ClassificationResult has no ``share_mismatches`` (and ``models`` no ShareMismatch)."""
        result = _same_day_pair(listed).classify()

        assert _classifications(result) == {401: "linked_internal", 402: "linked_internal"}
        assert result.share_mismatches == [_share_mismatch(tx_ids=(401, 402), broker_ids=(20, 10), shares=("0.5", "1"), dt="2025-10-01")]

    @pytest.mark.parametrize(("sent_id", "received_id", "listed", "broker_ids", "shares"), _DIFFERENT_DAY_CASES)
    def test_different_day_pair_at_different_shares_warns_once(self, sent_id, received_id, listed, broker_ids, shares):
        """Guard (green on HEAD and after J-43). Two days apart the pair already warns, exactly once (the pair is
        processed once, not once per leg): taking the warning out of the in-transit branch must not double it."""
        result = _different_day_pair(sent_id, received_id, listed).classify()

        assert _classifications(result) == {411: "linked_internal", 412: "linked_internal"}
        mismatch_warnings = _share_mismatch_warnings(result)
        assert len(mismatch_warnings) == 1, result.warnings
        assert {411, 412} <= _numbers_in(mismatch_warnings[0]), mismatch_warnings

    @pytest.mark.parametrize(("sent_id", "received_id", "listed", "broker_ids", "shares"), _DIFFERENT_DAY_CASES)
    def test_different_day_pair_records_one_share_mismatch_dated_at_the_later_leg(self, sent_id, received_id, listed, broker_ids, shares):
        """Red (J-43b). Exactly one ShareMismatch for the pair two days apart, not one per leg: ids (411, 412), the
        brokers and shares of 411 and 412 in that order, dated 2025-10-03 — the later leg, whichever leg has the lower id
        and whichever the classifier meets first.

        HEAD: AttributeError — no ``share_mismatches``; the warning itself is given (guarded above)."""
        result = _different_day_pair(sent_id, received_id, listed).classify()

        assert _classifications(result) == {411: "linked_internal", 412: "linked_internal"}
        assert result.share_mismatches == [_share_mismatch(tx_ids=(411, 412), broker_ids=broker_ids, shares=shares, dt="2025-10-03")]

    def test_every_pair_at_different_shares_is_reported_once(self):
        """Red (J-43a + J-43b). Brokers 10 and 30 owned at 1, broker 20 at 0.5, three linked internal pairs: a same-day
        CASH_TRANSFER 10 -> 20 (501/502, 10-01), a TRANSFER of 5 units 20 -> 10 (503 on 10-02, 504 on 10-06), and a
        same-day CASH_TRANSFER 10 -> 30 (505/506, 10-03) between equal shares. Two warnings and two ShareMismatch, one per
        pair at different shares; nothing for the third.

        HEAD: one warning, the TRANSFER's (the only pair with a transit), and AttributeError on ``share_mismatches``."""
        txs = [
            _tx(id=501, broker_id=10, type="CASH_TRANSFER", dt="2025-10-01", amount="-1000", related_id=502),
            _tx(id=502, broker_id=20, type="CASH_TRANSFER", dt="2025-10-01", amount="1000", related_id=501),
            _tx(id=503, broker_id=20, type="TRANSFER", dt="2025-10-02", currency=None, quantity="-5", asset_id=700, related_id=504),
            _tx(id=505, broker_id=10, type="CASH_TRANSFER", dt="2025-10-03", amount="-300", related_id=506),
            _tx(id=506, broker_id=30, type="CASH_TRANSFER", dt="2025-10-03", amount="300", related_id=505),
            _tx(id=504, broker_id=10, type="TRANSFER", dt="2025-10-06", currency=None, quantity="5", asset_id=700, related_id=503),
        ]
        c = ScopeAwareTransactionClassifier(scope_broker_ids={10, 20, 30}, all_transactions=txs, broker_shares={10: Decimal("1"), 20: Decimal("0.5"), 30: Decimal("1")})
        result = c.classify()

        pair_ids = {501, 502, 503, 504, 505, 506}
        assert _classifications(result) == dict.fromkeys(pair_ids, "linked_internal")
        assert sorted(sorted(_numbers_in(warning) & pair_ids) for warning in _share_mismatch_warnings(result)) == [[501, 502], [503, 504]], result.warnings
        assert sorted(result.share_mismatches, key=lambda mismatch: mismatch.tx_ids) == [
            _share_mismatch(tx_ids=(501, 502), broker_ids=(10, 20), shares=("1", "0.5"), dt="2025-10-01"),
            _share_mismatch(tx_ids=(503, 504), broker_ids=(20, 10), shares=("0.5", "1"), dt="2025-10-06"),
        ]

    @pytest.mark.parametrize("scenario", _NO_MISMATCH_CASES)
    def test_no_share_mismatch_warning_outside_pairs_at_different_shares(self, scenario):
        """Guard (green on HEAD and after J-43). Equal shares (same day or not, two brokers or one), a linked leg whose
        other leg is outside the scope, unlinked rows, a leg whose pair is not found: no "share mismatch" warning. The
        classifications are checked first, so the absence is about the rows the case claims."""
        classifier, external_paired, expected = scenario()
        result = classifier.classify(external_paired)

        assert _classifications(result) == expected
        assert _share_mismatch_warnings(result) == []

    @pytest.mark.parametrize("scenario", _NO_MISMATCH_CASES)
    def test_no_share_mismatch_recorded_outside_pairs_at_different_shares(self, scenario):
        """Red (J-43b) on HEAD only by construction: AttributeError, ClassificationResult has no ``share_mismatches``.
        After J-43 it guards the same cases as the test above: nothing is recorded."""
        classifier, external_paired, expected = scenario()
        result = classifier.classify(external_paired)

        assert _classifications(result) == expected
        assert result.share_mismatches == []
