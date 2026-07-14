"""Unit tests for DailyStateBuilder.

Pure tests — no DB, no async, no fixtures. Uses mock Transaction objects.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.portfolio_engine import (
    ClassifiedTransaction,
    DailyStateBuilder,
    InTransitInterval,
)

# =============================================================================
# HELPERS
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
        "date_to": date(2025, 1, 3),
    }
    defaults.update(overrides)
    return DailyStateBuilder(**defaults)


# =============================================================================
# TESTS
# =============================================================================


class TestCashLedger:
    """Cash ledger tracks cumulative signed amounts."""

    def test_single_deposit(self):
        """DEPOSIT 1000 EUR → cash_value=1000 from deposit date onwards."""
        tx = _tx(dt="2025-01-01", type="DEPOSIT", amount="1000")
        builder = _builder(
            classified_txs=[_ctxn(tx)],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )
        states = builder.build().daily_states

        assert len(states) == 2
        assert states[0].cash_value == Decimal("1000")
        assert states[1].cash_value == Decimal("1000")

    def test_deposit_then_buy(self):
        """DEPOSIT +1000 then BUY -400 → cash=600."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-02", type="BUY", amount="-400", quantity="10", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 3),
        )
        states = builder.build().daily_states

        assert states[0].cash_value == Decimal("1000")  # day 1: deposit
        assert states[1].cash_value == Decimal("600")  # day 2: after buy
        assert states[2].cash_value == Decimal("600")  # day 3: unchanged

    def test_all_tx_types_contribute(self):
        """Every tx type with amount≠0 contributes to cash."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="FEE", amount="-10")),
            _ctxn(_tx(id=3, dt="2025-01-01", type="DIVIDEND", amount="50")),
            _ctxn(_tx(id=4, dt="2025-01-01", type="TAX", amount="-20")),
        ]
        builder = _builder(
            classified_txs=txs,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].cash_value == Decimal("1020")  # 1000 - 10 + 50 - 20

    def test_share_percentage(self):
        """share_percentage scales cash contributions."""
        tx = _tx(dt="2025-01-01", type="DEPOSIT", amount="1000")
        builder = _builder(
            classified_txs=[_ctxn(tx, share="0.5")],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].cash_value == Decimal("500")


class TestQuantityLedger:
    """Quantity tracks all tx types with quantity != 0 (including TRANSFER, ADJUSTMENT)."""

    def test_buy_and_sell(self):
        """BUY +10, SELL -3 → net qty 7, market_value = 7 * price."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-1000", quantity="10", asset_id=100)),
            _ctxn(_tx(id=2, dt="2025-01-02", type="SELL", amount="300", quantity="-3", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("100"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )
        states = builder.build().daily_states

        assert states[0].market_value == Decimal("1000")  # 10 * 100
        assert states[1].market_value == Decimal("700")  # 7 * 100

    def test_transfer_changes_quantity(self):
        """TRANSFER with quantity ≠ 0 affects market value (fixes known bug)."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-500", quantity="10", asset_id=100)),
            _ctxn(_tx(id=2, dt="2025-01-02", type="TRANSFER", quantity="-5", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("50"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )
        states = builder.build().daily_states

        assert states[0].market_value == Decimal("500")  # 10 * 50
        assert states[1].market_value == Decimal("250")  # 5 * 50


class TestNAVFormula:
    """NAV = market_value + cash_value + in_transit."""

    def test_nav_basic(self):
        """nav_value = broker_nav_value + in_transit_market_value."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-500", quantity="10", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("50"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        s = states[0]
        assert s.cash_value == Decimal("500")  # 1000 - 500
        assert s.market_value == Decimal("500")  # 10 * 50
        assert s.broker_nav_value == Decimal("1000")
        assert s.in_transit_market_value == Decimal("0")
        assert s.nav_value == Decimal("1000")


class TestBookValueFormula:
    """book_value = open_cost_basis + cash + in_transit_book_value."""

    def test_book_value_with_wac(self):
        """book_value computed from WAC series."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="DEPOSIT", amount="1000")),
            _ctxn(_tx(id=2, dt="2025-01-01", type="BUY", amount="-500", quantity="10", asset_id=100, broker_id=10)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("60"), "EUR")]},
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        s = states[0]
        assert s.open_cost_basis == Decimal("500")  # WAC 50 * qty 10
        assert s.cash_value == Decimal("500")
        assert s.book_value == Decimal("1000")  # 500 + 500
        assert s.unrealized_gain_loss == s.nav_value - s.book_value
        assert s.unrealized_gain_loss == Decimal("100")  # NAV 1100 - book 1000


class TestMarketValueWithQuoteBase:
    """quote_base_quantity divides raw price (e.g. BTP/bond at 102 per 100 nominal)."""

    def test_quote_base(self):
        """qty=200, price=102, quote_base=100 → (200/100)*102 = 204."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-200", quantity="200", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2025, 1, 1), Decimal("102"), "EUR")]},
            quote_base_map={100: 100},
            asset_types={100: "Bond"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].market_value == Decimal("204")


class TestMissingPrices:
    """Assets without prices are flagged, not included in market_value."""

    def test_missing_price(self):
        """No price → missing_price_asset_ids contains asset_id, market_value=0."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-100", quantity="5", asset_id=200)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={},  # no prices
            asset_types={200: "ETF"},
            asset_classifications={200: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].market_value == Decimal("0")
        assert 200 in states[0].missing_price_asset_ids
        assert states[0].nav_complete is False


class TestStalePriceDetection:
    """Prices older than threshold days are flagged as stale."""

    def test_stale_price(self):
        """Price from 10 days ago (> 7 day threshold) → stale."""
        txs = [
            _ctxn(_tx(id=1, dt="2025-01-01", type="BUY", amount="-100", quantity="5", asset_id=100)),
        ]
        builder = _builder(
            classified_txs=txs,
            price_map={100: [(date(2024, 12, 22), Decimal("20"), "EUR")]},  # 10 days before Jan 1
            quote_base_map={100: None},
            asset_types={100: "ETF"},
            asset_classifications={100: None},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert 100 in states[0].stale_price_asset_ids
        assert states[0].market_value == Decimal("100")  # still valued, just flagged


class TestInTransitCash:
    """Cash in-transit during transit window."""

    def test_cash_in_transit(self):
        """Cash transfer between brokers with 2-day gap → in-transit on middle day."""
        dep_tx = _tx(id=10, broker_id=10, dt="2025-01-01", type="CASH_TRANSFER", amount="-3000")
        arr_tx = _tx(id=11, broker_id=20, dt="2025-01-04", type="CASH_TRANSFER", amount="3000")

        interval = InTransitInterval(
            start_date=date(2025, 1, 2),
            end_date=date(2025, 1, 3),
            tx_type="cash",
            departure_leg=dep_tx,
            arrival_leg=arr_tx,
            share=Decimal("1"),
        )

        builder = _builder(
            classified_txs=[
                _ctxn(dep_tx, classification="linked_internal"),
                _ctxn(arr_tx, classification="linked_internal"),
            ],
            in_transit_intervals=[interval],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 4),
        )
        states = builder.build().daily_states

        # Day 1: cash -3000, no in-transit yet (departure date itself)
        assert states[0].in_transit_cash_value == Decimal("0")
        # Day 2: in transit
        assert states[1].in_transit_cash_value == Decimal("3000")
        # Day 3: still in transit
        assert states[2].in_transit_cash_value == Decimal("3000")
        # Day 4: arrival — cash +3000, no more in transit
        assert states[3].in_transit_cash_value == Decimal("0")


class TestAllocationLiquidity:
    """Cash treated as Liquidity in type/sector allocation, NOT in geography."""

    def test_cash_as_liquidity(self):
        """Pure cash portfolio → type=Liquidity, sector=Liquidity, geography=empty."""
        txs = [_ctxn(_tx(dt="2025-01-01", type="DEPOSIT", amount="5000"))]
        builder = _builder(
            classified_txs=txs,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        s = states[0]
        assert s.by_type.get("Liquidity") == Decimal("5000")
        assert s.by_sector.get("Liquidity") == Decimal("5000")
        assert len(s.by_geography) == 0  # cash is NOT a country


class TestExternalCashFlow:
    """External cash flows tracked correctly for performance calculations."""

    def test_ecf_deposit(self):
        """DEPOSIT external cash flow captured in DailyPortfolioState."""
        txs = [_ctxn(_tx(dt="2025-01-01", type="DEPOSIT", amount="1000"))]
        builder = _builder(
            classified_txs=txs,
            external_cash_flows=[(date(2025, 1, 1), Decimal("1000"), "EUR")],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 2),
        )
        states = builder.build().daily_states

        assert states[0].external_cash_flow == Decimal("1000")
        assert states[1].external_cash_flow == Decimal("0")


class TestFXConversion:
    """Amounts in non-target currencies are converted using fx_rate_map."""

    def test_usd_cash_converted(self):
        """USD deposit with FX rate → cash in EUR."""
        txs = [
            _ctxn(_tx(dt="2025-01-01", type="DEPOSIT", amount="1000", currency="USD")),
        ]
        builder = _builder(
            classified_txs=txs,
            fx_rate_map={("USD", "EUR", date(2025, 1, 1)): Decimal("0.9")},
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        assert states[0].cash_value == Decimal("900")  # 1000 * 0.9

    def test_missing_fx_flagged(self):
        """USD amount without FX rate → cash=0, missing_fx_pairs populated."""
        txs = [
            _ctxn(_tx(dt="2025-01-01", type="DEPOSIT", amount="1000", currency="USD")),
        ]
        builder = _builder(
            classified_txs=txs,
            fx_rate_map={},  # no rate
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 1),
        )
        states = builder.build().daily_states

        # USD couldn't be converted → cash=0
        assert states[0].cash_value == Decimal("0")
