"""
Test Suite: rewards in kind imported as REWARD (project 79, lot STK-4a)

Four BRIM plugins learn the REWARD type (units received with no cash, valued on receipt) and bump to 1.1.0:

- Coinbase: «staking income», «rewards income», «learning reward» → REWARD, its per-unit value the Subtotal ÷ the quantity in
  the Price Currency; an empty Subtotal → REWARD with no value and the blocking ``reward_value`` todo. A fee on the row is
  still a separate FEE.
- Crypto.com: a reward kind in a crypto asset with Amount > 0 → REWARD at Native Amount ÷ Amount in the Native Currency (the
  todo when either is blank); a crypto Amount < 0 → ADJUSTMENT as before; a fiat reward → cash INTEREST as before; a reward
  with no crypto units but a value (no symbol, or a crypto Amount of 0) → NOT imported, a warning naming row, date and value;
  nothing at all → the old «no importable amount» warning.
- Freetrade: ``FREESHARE_ORDER`` → REWARD, no cash, its value the «Price per Share in Account Currency» read verbatim; an empty
  price → the todo.
- Generic CSV: the aliases reward, rewards, staking, staking reward, staking_reward, airdrop, premio → REWARD, an asset always
  (``UNKNOWN_ROW_n`` when missing), the ``reward_value`` todo on every REWARD and never the ``corporate_action`` one; an
  ``amount`` on a REWARD row is cash, which a REWARD refuses (a validation issue, as for an ADJUSTMENT).

And the two shared helpers of ``_brim_io``: ``reward_unit_value`` and ``reward_value_todo``.

Every synthetic file is written in ``tmp_path`` and owned by its test, so its whole output is asserted exactly; a row is
found by its file line, never by position in an unowned list. The real samples are only read, never edited.

PURE: samples and files of ``tmp_path``, no server, no database, no network, no clock.
"""

from __future__ import annotations

import csv
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pytest

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import BRIMParseOutput
from backend.app.schemas.common import is_fiat_currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim_providers import _brim_io as brim_io
from backend.app.services.brim_providers.broker_coinbase.plugin import CoinbaseBrokerProvider
from backend.app.services.brim_providers.broker_cryptocom.plugin import CryptoComBrokerProvider
from backend.app.services.brim_providers.broker_freetrade.plugin import FreetradeBrokerProvider
from backend.app.services.brim_providers.broker_generic_csv.plugin import GenericCSVBrokerProvider
from backend.test_scripts.brim_samples import plugin_samples_dir

# =============================================================================
# CONSTANTS
# =============================================================================

BROKER_ID = 1
NEW_VERSION = "1.1.0"
REWARD_VALUE = "reward_value"
COST_FIELD = "cost_basis_override"
# The amount column keeps 6 decimals (RealDecimal(18, 6)): a reward's value × its quantity must give back the file's
# Subtotal closer than that, or the stored row could not reproduce the total the file states.
AMOUNT_RESOLUTION = Decimal("0.000001")

COINBASE_HEADER = ["ID", "Timestamp", "Transaction Type", "Asset", "Quantity Transacted", "Price Currency", "Price at Transaction", "Subtotal", "Total (inclusive of fees and/or spread)", "Fees and/or Spread", "Notes"]
CRYPTOCOM_HEADER = ["Timestamp (UTC)", "Transaction Description", "Currency", "Amount", "To Currency", "To Amount", "Native Currency", "Native Amount", "Native Amount (in USD)", "Transaction Kind", "Transaction Hash"]
FREETRADE_HEADER = [
    "Title",
    "Type",
    "Timestamp",
    "Account Currency",
    "Total Amount",
    "Buy / Sell",
    "Ticker",
    "ISIN",
    "Price per Share in Account Currency",
    "Stamp Duty",
    "Quantity",
    "Venue",
    "Order ID",
    "Order Type",
    "Instrument Currency",
    "Total Shares Amount",
    "Price per Share",
    "FX Rate",
    "Base FX Rate",
    "FX Fee (BPS)",
    "FX Fee Amount",
    "Dividend Ex Date",
    "Dividend Pay Date",
    "Dividend Eligible Quantity",
    "Dividend Amount Per Share",
    "Dividend Gross Distribution Amount",
    "Dividend Net Distribution Amount",
    "Dividend Withheld Tax Percentage",
    "Dividend Withheld Tax Amount",
]

COINBASE_SAMPLE = plugin_samples_dir("broker_coinbase") / "coinbase-export.csv"
CRYPTOCOM_SAMPLE = plugin_samples_dir("broker_cryptocom") / "cryptocom-export.csv"
FREETRADE_SAMPLE = plugin_samples_dir("broker_freetrade") / "freetrade-export.csv"

COINBASE_REWARD_TYPES = ("staking income", "rewards income", "learning reward")
GENERIC_REWARD_ALIASES = ("reward", "rewards", "staking", "staking reward", "staking_reward", "airdrop", "premio")


# =============================================================================
# HELPERS
# =============================================================================


def _write_csv(path: Path, header: Sequence[str], rows: Sequence[Dict[str, str]]) -> Path:
    """A CSV of ``rows`` under ``header`` (missing cells empty); row ``i`` of ``rows`` is file line ``i + 2``."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(header))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in header})
    return path


def _shape(output: BRIMParseOutput) -> List[tuple]:
    """``(type, quantity)`` of every parsed transaction, in file order: the whole output of a file this test owns."""
    return [(tx.type, tx.quantity) for tx in output.transactions]


def _todos(output: BRIMParseOutput) -> List[tuple]:
    """``(tx_index, field, severity, reason_code)`` of every field todo."""
    return [(todo.tx_index, todo.field, todo.severity, todo.reason_code) for todo in output.field_todos]


def _warning_of_line(output: BRIMParseOutput, line: int) -> List[str]:
    """The messages of the warnings that name file line ``line`` («Row N: …»)."""
    return [notice.message for notice in output.warnings if notice.message.startswith(f"Row {line}:")]


def _assert_reward(tx: TXCreateItem, quantity: str, value: Optional[str], currency: Optional[str], where: str) -> None:
    """A REWARD of ``quantity`` units, no cash, valued ``value`` ``currency`` per unit (``value`` None: no value yet)."""
    assert tx.type == TransactionType.REWARD, f"{where}: type {tx.type}, expected REWARD"
    assert tx.quantity == Decimal(quantity) and tx.quantity > 0, f"{where}: quantity {tx.quantity}, expected {quantity} (> 0)"
    assert tx.cash is None, f"{where}: a REWARD moves no cash, got {tx.cash}"
    if value is None:
        assert tx.cost_basis_override is None, f"{where}: no value in the file, so no override; got {tx.cost_basis_override}"
    else:
        assert tx.cost_basis_override is not None, f"{where}: expected a value of {value} {currency} per unit, got none"
        assert (tx.cost_basis_override.amount, tx.cost_basis_override.code) == (Decimal(value), currency), f"{where}: value {tx.cost_basis_override}, expected {value} {currency} per unit"


def _half_unit_of_last_digit(value: Decimal) -> Decimal:
    """Half a unit of the last digit ``value`` keeps: the most its rounding can have moved it."""
    return Decimal(1).scaleb(value.as_tuple().exponent) / 2


def _sample_rows(path: Path) -> List[tuple]:
    """``(file line, row)`` of every data row of a sample."""
    with path.open(encoding="utf-8", newline="") as handle:
        return [(line, row) for line, row in enumerate(csv.DictReader(handle), start=2)]


# =============================================================================
# A. THE SHARED HELPERS
# =============================================================================


class TestRewardUnitValue:
    """``reward_unit_value(total, quantity)``: the per-unit value on receipt, rounded to what the column keeps."""

    @pytest.mark.parametrize(
        ("total", "quantity", "expected"),
        [
            pytest.param("10.00", "0.5", "20", id="exact-quotient"),
            pytest.param("-10", "4", "2.5", id="a-negative-total-is-taken-as-its-size"),
            pytest.param("1", "3", "0.333333333333", id="rounded-to-12-decimals"),
            pytest.param("2", "3", "0.666666666667", id="rounded-to-12-decimals-up"),
            pytest.param("0.0000000000025", "1", "0.000000000002", id="half-even-tie-at-12-decimals"),
            pytest.param("0.0000000000035", "1", "0.000000000004", id="half-even-tie-to-the-even-digit"),
            pytest.param("100000", "3", "33333.3333333333", id="capped-at-15-significant-digits"),
            pytest.param("0", "3", "0", id="a-total-of-0-is-a-value"),
        ],
    )
    def test_value_from_total_and_quantity(self, total: str, quantity: str, expected: str):
        value = brim_io.reward_unit_value(Decimal(total), Decimal(quantity))
        assert value is not None, f"{total} ÷ {quantity}: expected {expected}, got None"
        assert value == Decimal(expected), f"{total} ÷ {quantity}: expected {expected}, got {value}"

    def test_the_form_of_a_value_that_fits_is_kept(self):
        """``round_computed_value`` leaves a value that fits as it is: 100.00 ÷ 100 stays 1.00, not 1.000000000000."""
        assert str(brim_io.reward_unit_value(Decimal("100.00"), Decimal("100"))) == "1.00"

    @pytest.mark.parametrize(
        ("total", "quantity"),
        [
            pytest.param(None, "1", id="no-total"),
            pytest.param("NaN", "1", id="total-not-a-number"),
            pytest.param("Infinity", "1", id="total-infinite"),
            pytest.param("5", "0", id="no-units"),
            pytest.param("5", "-2", id="units-taken-out"),
        ],
    )
    def test_no_value(self, total: Optional[str], quantity: str):
        assert brim_io.reward_unit_value(None if total is None else Decimal(total), Decimal(quantity)) is None


class TestRewardValueTodo:
    """``reward_value_todo``: the blocking todo of a REWARD with no value."""

    @pytest.mark.parametrize("symbol", [None, "ETH"])
    def test_shape(self, symbol: Optional[str]):
        todo = brim_io.reward_value_todo(4, 7, symbol)
        assert (todo.tx_index, todo.field, todo.severity, todo.reason_code) == (4, COST_FIELD, "blocker", REWARD_VALUE)
        assert brim_io.REWARD_VALUE == REWARD_VALUE
        assert todo.message.startswith("Line 7:"), f"the message names the file line: {todo.message!r}"
        if symbol:
            assert symbol in todo.message, f"the message names the asset {symbol}: {todo.message!r}"


# =============================================================================
# B. COINBASE
# =============================================================================


def _coinbase_row(kind: str, asset: str, quantity: str, subtotal: str, total: str, fees: str = "€0.00", when: str = "2025-01-17 16:57:02 UTC", currency: str = "EUR") -> Dict[str, str]:
    return {
        "ID": "synthetic",
        "Timestamp": when,
        "Transaction Type": kind,
        "Asset": asset,
        "Quantity Transacted": quantity,
        "Price Currency": currency,
        "Price at Transaction": "€1.00",
        "Subtotal": subtotal,
        "Total (inclusive of fees and/or spread)": total,
        "Fees and/or Spread": fees,
    }


class TestCoinbaseRewards:
    """Coinbase 1.1.0: rewards income in kind is a REWARD at the Subtotal's value."""

    def test_version(self):
        assert CoinbaseBrokerProvider().plugin_version == NEW_VERSION

    def test_each_reward_type_with_and_without_a_value(self, tmp_path: Path):
        """A buy with a fee (two transactions) comes first, so a todo's tx_index is not its row's position; the reward with no
        Subtotal carries its own fee, which stays a separate FEE right after it."""
        rows = [
            _coinbase_row("Buy", "BTC", "0.01", "€500.00", "€505.00", fees="€5.00"),  # line 2 → BUY, FEE
            _coinbase_row("Staking Income", "ETH", "0.5", "€10.00", "€10.25", fees="€0.25"),  # line 3 → REWARD 20 EUR (Subtotal, not Total), FEE
            _coinbase_row("Rewards Income", "SOL", "2", "", "€5.00", fees="€0.10", currency="USD"),  # line 4 → REWARD (todo: no Subtotal, the Total is not a value), FEE
            _coinbase_row("Learning Reward", "GRT", "3", "€1.00", "€1.00", currency="GBP"),  # line 5 → REWARD 0.333333333333 GBP
        ]
        output = CoinbaseBrokerProvider().parse(_write_csv(tmp_path / "coinbase-rewards.csv", COINBASE_HEADER, rows), broker_id=BROKER_ID)

        assert output.validation_issues == [], f"no row may be refused: {output.validation_issues}"
        assert _shape(output) == [
            (TransactionType.BUY, Decimal("0.01")),
            (TransactionType.FEE, Decimal("0")),
            (TransactionType.REWARD, Decimal("0.5")),
            (TransactionType.FEE, Decimal("0")),
            (TransactionType.REWARD, Decimal("2")),
            (TransactionType.FEE, Decimal("0")),
            (TransactionType.REWARD, Decimal("3")),
        ], f"the file's rows, in order: {_shape(output)}"
        _assert_reward(output.transactions[2], "0.5", "20", "EUR", "staking income (line 3): Subtotal 10.00 ÷ 0.5, never the Total 10.25")
        _assert_reward(output.transactions[4], "2", None, None, "rewards income without Subtotal (line 4)")
        _assert_reward(output.transactions[6], "3", "0.333333333333", "GBP", "learning reward (line 5)")
        for index, line, fee_amount, currency in ((3, 3, "-0.25", "EUR"), (5, 4, "-0.10", "USD")):
            fee = output.transactions[index]
            assert fee.cash is not None and (fee.cash.amount, fee.cash.code) == (Decimal(fee_amount), currency), f"line {line}: the reward's fee stays a FEE: {fee.cash}"

        assert _todos(output) == [(4, COST_FIELD, "blocker", REWARD_VALUE)], f"one todo, on the REWARD with no Subtotal: {_todos(output)}"
        todo_tx = output.transactions[output.field_todos[0].tx_index]
        assert (todo_tx.type, todo_tx.cost_basis_override) == (TransactionType.REWARD, None), f"the todo points at a REWARD with no value: {todo_tx}"
        assert output.field_todos[0].message.startswith("Line 4:") and "SOL" in output.field_todos[0].message, output.field_todos[0].message

    def test_the_reward_is_bound_to_its_asset(self, tmp_path: Path):
        output = CoinbaseBrokerProvider().parse(_write_csv(tmp_path / "coinbase-one.csv", COINBASE_HEADER, [_coinbase_row("Staking Income", "ETH", "0.5", "€10.00", "€10.00")]), broker_id=BROKER_ID)
        (reward,) = output.transactions
        assert reward.asset_id in output.extracted_assets
        assert output.extracted_assets[reward.asset_id].extracted_symbol == "ETH"

    def test_sample_rewards_are_valued_rewards(self):
        """Every reward row of the real sample is a REWARD with a value, and value × quantity gives back its Subtotal within
        what the rounding can move and well within what the amount column keeps."""
        expected = []
        for line, row in _sample_rows(COINBASE_SAMPLE):
            if row["Transaction Type"].strip().lower() in COINBASE_REWARD_TYPES:
                when = datetime.strptime(row["Timestamp"].replace(" UTC", ""), "%Y-%m-%d %H:%M:%S").date()
                expected.append((line, when, Decimal(row["Quantity Transacted"]), Decimal(row["Subtotal"].replace("€", "")), row["Price Currency"]))
        assert expected, f"setup: {COINBASE_SAMPLE.name} has reward rows"

        output = CoinbaseBrokerProvider().parse(COINBASE_SAMPLE, broker_id=BROKER_ID)
        assert output.field_todos == [], f"every sample reward has a Subtotal: {_todos(output)}"
        rewards = [tx for tx in output.transactions if tx.type == TransactionType.REWARD]
        assert Counter((tx.date, tx.quantity) for tx in rewards) == Counter((when, qty) for _, when, qty, _, _ in expected), "one REWARD per reward row of the sample"

        for line, when, quantity, subtotal, currency in expected:
            reward = next(tx for tx in rewards if (tx.date, tx.quantity) == (when, quantity))
            assert reward.cash is None, f"line {line}: a REWARD moves no cash"
            override = reward.cost_basis_override
            assert override is not None and override.code == currency, f"line {line}: valued in {currency}, got {override}"
            gap = abs(override.amount * quantity - subtotal)
            bound = quantity * _half_unit_of_last_digit(override.amount)
            assert gap <= bound, f"line {line}: {override.amount} × {quantity} is {gap} from the Subtotal {subtotal}, more than the rounding allows ({bound})"
            assert gap < AMOUNT_RESOLUTION, f"line {line}: {override.amount} × {quantity} is {gap} from the Subtotal {subtotal}, not below {AMOUNT_RESOLUTION}"


# =============================================================================
# C. CRYPTO.COM
# =============================================================================


def _cryptocom_row(when: str, description: str, currency: str, amount: str, native_currency: str, native_amount: str, kind: str, tx_hash: str = "") -> Dict[str, str]:
    return {
        "Timestamp (UTC)": when,
        "Transaction Description": description,
        "Currency": currency,
        "Amount": amount,
        "Native Currency": native_currency,
        "Native Amount": native_amount,
        "Transaction Kind": kind,
        "Transaction Hash": tx_hash,
    }


class TestCryptoComRewards:
    """Crypto.com 1.1.0: a crypto reward is a REWARD at its Native Amount; a reward with no crypto units is not imported."""

    # file lines of the synthetic file below
    LINE_NO_SYMBOL = 8
    LINE_CRYPTO_ZERO = 9
    LINE_NOTHING = 10

    @pytest.fixture
    def output(self, tmp_path: Path) -> BRIMParseOutput:
        rows = [
            _cryptocom_row("2025-02-01 10:00:00", "Buy BTC", "BTC", "0.01", "EUR", "500.00", "crypto_purchase"),  # line 2 → BUY
            _cryptocom_row("2025-02-02 00:10:00", "CRO Stake Reward", "CRO", "10", "CHF", "2.5", "crypto_earn_interest_paid"),  # line 3 → REWARD 0.25 CHF
            _cryptocom_row("2025-02-03 00:10:00", "Card Cashback", "CRO", "4", "EUR", "", "referral_card_cashback"),  # line 4 → REWARD, todo
            _cryptocom_row("2025-02-04 00:10:00", "Card Cashback", "CRO", "4", "", "1.00", "referral_card_cashback"),  # line 5 → REWARD, todo
            _cryptocom_row("2025-02-05 00:10:00", "Cashback Reversal", "CRO", "-2", "EUR", "0.5", "referral_card_cashback"),  # line 6 → ADJUSTMENT -2
            _cryptocom_row("2025-02-06 00:10:00", "EUR Interest", "EUR", "1.5", "EUR", "1.5", "crypto_earn_interest_paid"),  # line 7 → INTEREST
            _cryptocom_row("2025-02-07 00:10:00", "Mystery Reward", "", "", "EUR", "0.75", "referral_card_cashback"),  # line 8 → not imported
            _cryptocom_row("2025-02-08 00:10:00", "Zero Reward", "CRO", "0", "EUR", "0.40", "crypto_earn_interest_paid"),  # line 9 → not imported
            _cryptocom_row("2025-02-09 00:10:00", "Empty Reward", "", "", "", "", "referral_card_cashback"),  # line 10 → not imported
            _cryptocom_row("2025-02-10 10:00:00", "Sell BTC", "BTC", "-0.01", "EUR", "510.00", "crypto_sale"),  # line 11 → SELL
        ]
        return CryptoComBrokerProvider().parse(_write_csv(tmp_path / "cryptocom-rewards.csv", CRYPTOCOM_HEADER, rows), broker_id=BROKER_ID)

    def test_version(self):
        assert CryptoComBrokerProvider().plugin_version == NEW_VERSION

    def test_the_rows_imported(self, output: BRIMParseOutput):
        assert output.validation_issues == [], f"no row may be refused: {output.validation_issues}"
        assert _shape(output) == [
            (TransactionType.BUY, Decimal("0.01")),
            (TransactionType.REWARD, Decimal("10")),
            (TransactionType.REWARD, Decimal("4")),
            (TransactionType.REWARD, Decimal("4")),
            (TransactionType.ADJUSTMENT, Decimal("-2")),
            (TransactionType.INTEREST, Decimal("0")),
            (TransactionType.SELL, Decimal("-0.01")),
        ], f"lines 8-10 have no crypto units and are not imported; the rest in file order: {_shape(output)}"

    def test_a_crypto_reward_is_a_valued_reward(self, output: BRIMParseOutput):
        reward = output.transactions[1]
        _assert_reward(reward, "10", "0.25", "CHF", "CRO stake reward (line 3): in the Native Currency")
        assert reward.description == "CRO Stake Reward", f"no «(Value: …)» in the description any more: {reward.description!r}"
        assert output.extracted_assets[reward.asset_id].extracted_symbol == "CRO"

    def test_a_reward_without_native_amount_or_currency_asks_for_its_value(self, output: BRIMParseOutput):
        _assert_reward(output.transactions[2], "4", None, None, "no Native Amount (line 4)")
        _assert_reward(output.transactions[3], "4", None, None, "no Native Currency (line 5)")
        assert _todos(output) == [(2, COST_FIELD, "blocker", REWARD_VALUE), (3, COST_FIELD, "blocker", REWARD_VALUE)], _todos(output)
        assert [todo.message.split(":")[0] for todo in output.field_todos] == ["Line 4", "Line 5"]

    def test_a_negative_reward_stays_an_adjustment(self, output: BRIMParseOutput):
        reversal = output.transactions[4]
        assert (reversal.type, reversal.quantity, reversal.cash, reversal.cost_basis_override) == (TransactionType.ADJUSTMENT, Decimal("-2"), None, None)
        assert reversal.description == "Cashback Reversal (Value: 0.5 EUR)", f"the outgoing ADJUSTMENT keeps its 1.0.0 description: {reversal.description!r}"

    def test_a_fiat_reward_stays_cash_interest(self, output: BRIMParseOutput):
        interest = output.transactions[5]
        assert (interest.type, interest.quantity, interest.asset_id) == (TransactionType.INTEREST, Decimal("0"), None)
        assert interest.cash is not None and (interest.cash.amount, interest.cash.code) == (Decimal("1.5"), "EUR")

    @pytest.mark.parametrize(("line", "day", "value"), [(LINE_NO_SYMBOL, "2025-02-07", "0.75"), (LINE_CRYPTO_ZERO, "2025-02-08", "0.40")], ids=["no-symbol", "crypto-amount-0"])
    def test_a_reward_without_crypto_units_is_not_imported_but_named(self, output: BRIMParseOutput, line: int, day: str, value: str):
        """Never cash INTEREST (money that never arrived), never a guessed asset: a warning names the row, its date and value."""
        messages = _warning_of_line(output, line)
        assert len(messages) == 1, f"line {line}: one warning, got {messages}"
        for token in (day, value, "EUR"):
            assert token in messages[0], f"line {line}: the warning names {token}: {messages[0]!r}"
        assert not any(tx.date == date.fromisoformat(day) for tx in output.transactions), f"line {line}: nothing imported on {day}"

    def test_a_reward_with_nothing_keeps_the_old_warning(self, output: BRIMParseOutput):
        messages = _warning_of_line(output, self.LINE_NOTHING)
        assert len(messages) == 1 and "no importable amount" in messages[0], f"line {self.LINE_NOTHING}: {messages}"

    def test_imported_rows_have_no_warning(self, output: BRIMParseOutput):
        for line in (2, 3, 4, 5, 6, 7, 11):
            assert _warning_of_line(output, line) == [], f"line {line} is imported: no warning"

    def test_sample_rewards_are_valued_rewards(self):
        """Every reward kind of the real sample in a crypto asset with Amount > 0 is a REWARD at Native Amount ÷ Amount."""
        provider = CryptoComBrokerProvider()
        expected = []
        for line, row in _sample_rows(CRYPTOCOM_SAMPLE):
            kind = row["Transaction Kind"].strip().lower()
            if kind in ("crypto_purchase", "viban_purchase", "crypto_sell", "viban_sell", "crypto_sale") or not provider._is_reward_kind(kind):
                continue
            amount = Decimal(row["Amount"])
            if row["Currency"] and amount > 0 and not is_fiat_currency(row["Currency"]):
                when = datetime.strptime(row["Timestamp (UTC)"], "%Y-%m-%d %H:%M:%S").date()
                expected.append((line, when, amount, Decimal(row["Native Amount"]), row["Native Currency"]))
        assert expected, f"setup: {CRYPTOCOM_SAMPLE.name} has crypto reward rows"

        output = provider.parse(CRYPTOCOM_SAMPLE, broker_id=BROKER_ID)
        assert output.field_todos == [], f"every sample reward has its Native Amount: {_todos(output)}"
        rewards = [tx for tx in output.transactions if tx.type == TransactionType.REWARD]
        assert Counter((tx.date, tx.quantity) for tx in rewards) == Counter((when, qty) for _, when, qty, _, _ in expected), "one REWARD per crypto reward row of the sample"
        for line, when, quantity, native, currency in expected:
            reward = next(tx for tx in rewards if (tx.date, tx.quantity) == (when, quantity))
            assert reward.cash is None, f"line {line}: a REWARD moves no cash"
            override = reward.cost_basis_override
            assert override is not None and override.code == currency, f"line {line}: valued in {currency}, got {override}"
            assert override.amount == brim_io.reward_unit_value(native, quantity), f"line {line}: {override.amount} ≠ {native} ÷ {quantity} rounded"
            assert abs(override.amount * quantity - native) < AMOUNT_RESOLUTION, f"line {line}: {override.amount} × {quantity} does not give back {native}"


# =============================================================================
# D. FREETRADE
# =============================================================================


def _freetrade_row(kind: str, when: str, total: str, quantity: str, price_account: str, direction: str = "BUY", title: str = "FTSE All World", ticker: str = "VWRL", isin: str = "IE00B3RBWM25", price_instrument: Optional[str] = None, instrument_currency: str = "GBP") -> Dict[str, str]:
    return {
        "Title": title,
        "Type": kind,
        "Timestamp": when,
        "Account Currency": "GBP",
        "Total Amount": total,
        "Buy / Sell": direction,
        "Ticker": ticker,
        "ISIN": isin,
        "Price per Share in Account Currency": price_account,
        "Stamp Duty": "0.00",
        "Quantity": quantity,
        "Instrument Currency": instrument_currency,
        "Price per Share": price_account if price_instrument is None else price_instrument,
    }


class TestFreetradeRewards:
    """Freetrade 1.1.0: a free share is a REWARD at its price per share, read verbatim, with no cash."""

    def test_version(self):
        assert FreetradeBrokerProvider().plugin_version == NEW_VERSION

    def test_free_shares(self, tmp_path: Path):
        """The price is the file's, verbatim and in the account currency: 2.5 shares, a Total of 9.99, a price of 3.21000000 GBP
        and an instrument price of 4.05 USD, so neither the Total, Total ÷ quantity (3.996) nor the instrument's price could pass
        for it."""
        rows = [
            _freetrade_row("ORDER", "2024-03-01T10:00:00.000Z", "100.00", "10.00000000", "10.00000000"),  # line 2 → BUY
            _freetrade_row("FREESHARE_ORDER", "2024-03-02T10:00:00.000Z", "9.99", "2.50000000", "3.21000000", price_instrument="4.05", instrument_currency="USD"),  # line 3 → REWARD
            _freetrade_row("FREESHARE_ORDER", "2024-03-03T10:00:00.000Z", "4.95", "1.00000000", "", title="Apple", ticker="AAPL", isin="US0378331005"),  # line 4 → REWARD, todo
        ]
        output = FreetradeBrokerProvider().parse(_write_csv(tmp_path / "freetrade-rewards.csv", FREETRADE_HEADER, rows), broker_id=BROKER_ID)

        assert output.validation_issues == [], f"no row may be refused: {output.validation_issues}"
        assert _shape(output) == [(TransactionType.BUY, Decimal("10")), (TransactionType.REWARD, Decimal("2.5")), (TransactionType.REWARD, Decimal("1"))], _shape(output)
        _assert_reward(output.transactions[1], "2.5", "3.21", "GBP", "free share (line 3)")
        assert str(output.transactions[1].cost_basis_override.amount) == "3.21000000", "the price is read verbatim, digits included"
        _assert_reward(output.transactions[2], "1", None, None, "free share with no price (line 4)")
        assert _todos(output) == [(2, COST_FIELD, "blocker", REWARD_VALUE)], _todos(output)
        assert output.field_todos[0].message.startswith("Line 4:") and "AAPL" in output.field_todos[0].message, output.field_todos[0].message
        assert output.extracted_assets[output.transactions[1].asset_id].extracted_isin == "IE00B3RBWM25"

    def test_sample_free_share_is_a_valued_reward(self):
        expected = [(line, row) for line, row in _sample_rows(FREETRADE_SAMPLE) if row["Type"] == "FREESHARE_ORDER"]
        assert expected, f"setup: {FREETRADE_SAMPLE.name} has a free share"

        output = FreetradeBrokerProvider().parse(FREETRADE_SAMPLE, broker_id=BROKER_ID)
        assert output.field_todos == [], _todos(output)
        rewards = [tx for tx in output.transactions if tx.type == TransactionType.REWARD]
        assert len(rewards) == len(expected), f"one REWARD per FREESHARE_ORDER of the sample: {len(rewards)} for {len(expected)}"
        for line, row in expected:
            when = datetime.strptime(row["Timestamp"][:19], "%Y-%m-%dT%H:%M:%S").date()
            reward = next(tx for tx in rewards if tx.date == when)
            _assert_reward(reward, row["Quantity"], row["Price per Share in Account Currency"], row["Account Currency"], f"sample line {line}")
            assert str(reward.cost_basis_override.amount) == row["Price per Share in Account Currency"], f"sample line {line}: verbatim"
        assert not any(tx.type == TransactionType.BUY and tx.description and tx.description.startswith("freeshare_order") for tx in output.transactions), "no free share is a BUY any more"


# =============================================================================
# E. GENERIC CSV
# =============================================================================


class TestGenericCsvRewards:
    """Generic CSV 1.1.0: the REWARD aliases, each REWARD with the ``reward_value`` todo."""

    def test_version(self):
        assert GenericCSVBrokerProvider().plugin_version == NEW_VERSION

    @pytest.mark.parametrize("alias", [*GENERIC_REWARD_ALIASES, "Airdrop", "STAKING REWARD"])
    def test_each_alias_is_a_reward_that_asks_for_its_value(self, tmp_path: Path, alias: str):
        csv_file = tmp_path / "reward.csv"
        csv_file.write_text(f"date,type,asset,quantity\n2025-03-01,{alias},ACME,3\n", encoding="utf-8")
        output = GenericCSVBrokerProvider().parse(csv_file, broker_id=BROKER_ID)

        assert output.validation_issues == [], f"{alias!r}: {output.validation_issues}"
        assert _shape(output) == [(TransactionType.REWARD, Decimal("3"))], f"{alias!r}: {_shape(output)} {output.warnings}"
        _assert_reward(output.transactions[0], "3", None, None, alias)
        assert _todos(output) == [(0, COST_FIELD, "blocker", REWARD_VALUE)], f"{alias!r}: the reward_value todo alone, never corporate_action: {_todos(output)}"

    def test_mixed_file_todos(self, tmp_path: Path):
        """An incoming ADJUSTMENT keeps ``corporate_action``, an outgoing one gets nothing, every REWARD gets ``reward_value``;
        a REWARD with no asset gets the placeholder of its row."""
        csv_file = tmp_path / "mixed.csv"
        csv_file.write_text(
            "date,type,asset,quantity\n"
            "2025-03-01,adjustment,ACME,3\n"  # line 2 → index 0, corporate_action
            "2025-03-02,staking,ETH,2\n"  # line 3 → index 1, reward_value
            "2025-03-03,adjustment,ACME,-1\n"  # line 4 → index 2, none
            "2025-03-04,airdrop,,5\n",  # line 5 → index 3, reward_value, asset UNKNOWN_ROW_5
            encoding="utf-8",
        )
        output = GenericCSVBrokerProvider().parse(csv_file, broker_id=BROKER_ID)

        assert _shape(output) == [(TransactionType.ADJUSTMENT, Decimal("3")), (TransactionType.REWARD, Decimal("2")), (TransactionType.ADJUSTMENT, Decimal("-1")), (TransactionType.REWARD, Decimal("5"))], _shape(output)
        assert [(todo.tx_index, todo.reason_code) for todo in output.field_todos] == [(0, "corporate_action"), (1, REWARD_VALUE), (3, REWARD_VALUE)]
        assert output.field_todos[2].message.startswith("Line 5:"), output.field_todos[2].message
        placeholder = output.transactions[3].asset_id
        assert placeholder is not None and placeholder in output.extracted_assets, "a REWARD always has an asset to map"
        assert placeholder not in {output.transactions[0].asset_id, output.transactions[1].asset_id}, "the placeholder is the row's own asset"

    def test_an_amount_on_a_reward_is_cash_not_a_value(self, tmp_path: Path):
        """The generic CSV reads no value column: an ``amount`` on a REWARD row is cash, which a REWARD refuses."""
        csv_file = tmp_path / "reward-amount.csv"
        csv_file.write_text("date,type,asset,quantity,amount,currency\n2025-03-01,reward,ACME,2,10,EUR\n2025-03-02,reward,ACME,1,,\n", encoding="utf-8")
        output = GenericCSVBrokerProvider().parse(csv_file, broker_id=BROKER_ID)

        assert _shape(output) == [(TransactionType.REWARD, Decimal("1"))], f"line 2 is refused, line 3 imported: {_shape(output)}"
        assert output.transactions[0].cost_basis_override is None, "the amount is never read as a value"
        assert {issue.row for issue in output.validation_issues} == {2}, f"the refusal is on line 2: {output.validation_issues}"
        assert _todos(output) == [(0, COST_FIELD, "blocker", REWARD_VALUE)], f"only the imported REWARD asks for its value: {_todos(output)}"
