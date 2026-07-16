"""Unit tests for ScopeAwareTransactionClassifier.

Pure tests — no DB, no async, no fixtures. Uses mock Transaction objects.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.portfolio_engine import (
    ScopeAwareTransactionClassifier,
)

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
        assert result.external_cash_flows[0] == (date(2025, 1, 1), Decimal("1000"), "EUR")

    def test_unlinked_withdrawal(self):
        """WITHDRAWAL → normal + external cash flow (negative)."""
        txs = [_tx(id=2, broker_id=10, type="WITHDRAWAL", dt="2025-02-01", amount="-500")]
        c = ScopeAwareTransactionClassifier(scope_broker_ids={10}, all_transactions=txs, broker_shares={10: Decimal("1")})
        result = c.classify()

        assert result.classified[0].classification == "normal"
        assert result.external_cash_flows[0][1] == Decimal("-500")

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
        assert result.external_cash_flows[0][1] == Decimal("-3000")

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
        assert result.external_cash_flows[0][1] == Decimal("3000")

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
        # No cash flow for asset transfer (amount=0)
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

        assert result.external_cash_flows[0][1] == Decimal("1000")
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
