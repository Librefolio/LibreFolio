"""
Test Suite: the Trade Republic plugin — ``broker_traderepublic`` 1.2.0 (lane 73 TR)

The plugin reads two layouts: Trade Republic's «Transaction export» (the native CSV since April 2026, read by
``broker_traderepublic/_transactions_export.py``, whose module docstring is the spec) and the old Dutch 8-column CSV,
unchanged. The plugin is reached through the registry inside each test, never imported at module level.

What is pinned:

- A. identity: code, version 1.2.0, the ``.csv`` extension, a file of another extension refused;
- B. recognition by the header, never by the file name: the clean export (``,``, every cell quoted), the same rows as
  Excel re-saves them (one quoted cell per line, CRLF), a ``;`` variant, columns in another order and in upper case;
  the Dutch sample still recognised; a header missing any one of the required columns refused (``can_parse`` false,
  ``parse`` raising ``header_mismatch``); ``auto_detect_plugin`` answers ``broker_traderepublic``, never the generic CSV;
- C. the samples: the clean export row by row as a multiset (type, date, quantity, cash amount and currency, asset by its
  identifier or none), derived by hand from the sample's cells; the Excel shape and the ``;`` variant give identical
  transactions, assets and notices; the extracted assets (ISIN vs ticker, names, fake ids in order of first use); the
  one tax-refund notice and its evidence; the Dutch sample still gives its 9 transactions;
- D. the rules on synthetic files: the ``date`` column, never ``datetime`` (UTC); each non-zero amount/fee/tax column is
  its own transaction, read verbatim; a positive tax is an INTEREST «Tax refund» with an info notice counting the rows;
  a row dated (or with a ``value_date``) after today is left out whole with an info notice; a repeated
  ``transaction_id`` is dropped without a notice, and so is a row with nothing to book; each reason for
  ``rows_not_recognized`` and ``rows_unreadable``; ISIN vs ticker, CRYPTO always a ticker; a lone decimal comma read.

Every input is a sample of ``sample_reports/`` or a file written in ``tmp_path``; every synthetic value is invented (the
ISINs are public securities). The far-future day is in 2099, so no clock is patched. This module is pure: no server,
no database, no network.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pytest

from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMNotice, BRIMParseOutput
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.test_scripts.brim_samples import SampleDir

# =============================================================================
# CONSTANTS
# =============================================================================

PLUGIN_CODE = "broker_traderepublic"
PLUGIN_VERSION = "1.2.0"
SAMPLE_DIR = SampleDir()
CLEAN_SAMPLE = SAMPLE_DIR / "traderepublic-transactions.csv"
EXCEL_SAMPLE = SAMPLE_DIR / "traderepublic-transactions-excel.csv"
DUTCH_SAMPLE = SAMPLE_DIR / "traderepublic-export.csv"
# Not 1: every transaction must carry the broker parse was given.
BROKER_ID = 7
TAGS = ["import", "traderepublic"]

# The 23 columns of the export, as Trade Republic writes them; the second form replaces the four counterparty columns with value_date.
HEADER: Tuple[str, ...] = (
    "datetime",
    "date",
    "account_type",
    "category",
    "type",
    "asset_class",
    "name",
    "symbol",
    "shares",
    "price",
    "amount",
    "fee",
    "tax",
    "currency",
    "original_amount",
    "original_currency",
    "fx_rate",
    "description",
    "transaction_id",
    "counterparty_name",
    "counterparty_iban",
    "payment_reference",
    "mcc_code",
)
VALUE_DATE_HEADER: Tuple[str, ...] = (*HEADER[:19], "value_date")
# The columns the export is recognised by: dropping any one of them refuses the file.
REQUIRED_COLUMNS = ("datetime", "date", "category", "type", "symbol", "shares", "amount", "fee", "tax", "currency", "transaction_id")

# The notices.
TAX_REFUND = "traderepublic_tax_refund"
NOT_SETTLED = "traderepublic_not_yet_settled"
ROWS_NOT_RECOGNIZED = "rows_not_recognized"
ROWS_UNREADABLE = "rows_unreadable"

# Securities of the sample (public identifiers; every amount, date and id around them is invented).
MSCI_WORLD = "IE00B4L5Y983"
MSCI_EM = "IE00BKM4GZ66"
APPLE = "US0378331005"
ETH = "ETH"

FAR_FUTURE = "2099-01-02"


# =============================================================================
# HELPERS
# =============================================================================


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _parse(path: Path, *, allow_issues: bool = False) -> BRIMParseOutput:
    """The plugin's parse of ``path`` for ``BROKER_ID``. A leg rejected by ``TXCreateItem`` would vanish while its notice still counts it, so no validation issue is allowed unless asked."""
    try:
        out = _plugin().parse(path, broker_id=BROKER_ID)
    except BRIMParseError as exc:
        raise AssertionError(f"parse({path.name}) raised BRIMParseError: {exc.message} {exc.details}") from exc
    if not allow_issues:
        assert out.validation_issues == [], f"{path.name}: validation issues {[issue.model_dump() for issue in out.validation_issues]}"
    return out


def _num(value) -> Optional[str]:
    """A number as plain text without trailing zeros, so that ``-10.00``, ``-10`` and ``Decimal("-10.0000")`` compare equal."""
    if value is None:
        return None
    number = Decimal(str(value))
    return "0" if number == 0 else format(number.normalize(), "f")


Key = Tuple[str, str, Optional[str], Optional[str], Optional[str], Optional[str]]


def _asset_key(out: BRIMParseOutput, asset_id: Optional[int]) -> Optional[str]:
    """The identifier the plugin extracted for a fake asset id (its ISIN, else its symbol), None for no asset."""
    if asset_id is None:
        return None
    info = out.extracted_assets[asset_id]
    return info.extracted_isin or info.extracted_symbol


def _keys(out: BRIMParseOutput) -> Counter:
    """The transactions as a multiset of (type, date, quantity, cash amount, cash currency, asset identifier)."""
    keys: List[Key] = []
    for tx in out.transactions:
        keys.append(
            (
                tx.type.value,
                tx.date.isoformat(),
                _num(tx.quantity),
                _num(tx.cash.amount) if tx.cash else None,
                tx.cash.code if tx.cash else None,
                _asset_key(out, tx.asset_id),
            )
        )
    return Counter(keys)


def _codes(out: BRIMParseOutput) -> List[str]:
    return [notice.code for notice in out.warnings]


def _notice(out: BRIMParseOutput, code: str) -> BRIMNotice:
    found = [notice for notice in out.warnings if notice.code == code]
    assert len(found) == 1, f"expected one {code} notice, got {_codes(out)}"
    return found[0]


def _comparable(out: BRIMParseOutput) -> Dict[str, object]:
    """The whole output as plain data, for comparing two shapes of the same rows."""
    return {
        "transactions": [tx.model_dump(mode="json") for tx in out.transactions],
        "assets": {asset_id: info.model_dump(mode="json") for asset_id, info in out.extracted_assets.items()},
        "warnings": [notice.model_dump(mode="json") for notice in out.warnings],
        "validation_issues": [issue.model_dump(mode="json") for issue in out.validation_issues],
    }


# =============================================================================
# SYNTHETIC FILES — written in tmp_path the way Trade Republic writes them
# =============================================================================

# A settled cash deposit of 100 EUR: a test writes only the cells its case is about.
DEFAULTS: Dict[str, str] = {
    "datetime": "2025-04-01T09:00:00.000Z",
    "date": "2025-04-01",
    "account_type": "DEFAULT",
    "category": "CASH",
    "type": "TRANSFER_INBOUND",
    "amount": "100.00",
    "currency": "EUR",
    "description": "Synthetic movement",
}
# The known-good first row of every case file: its one transaction.
BASE_KEY: Key = ("DEPOSIT", "2025-04-01", "0", "100", "EUR", None)


def _row(**cells: str) -> Dict[str, str]:
    """A data row by column name: the defaults, then ``cells``."""
    return {**DEFAULTS, **cells}


def _buy(**cells: str) -> Dict[str, str]:
    """A settled BUY of 2 Apple shares for 400 EUR, then ``cells``."""
    return _row(**{"category": "TRADING", "type": "BUY", "asset_class": "STOCK", "name": "Apple", "symbol": APPLE, "shares": "2.0000000000", "price": "200.0000000000", "amount": "-400.00", "description": "Buy trade Apple", **cells})


def _sell(**cells: str) -> Dict[str, str]:
    """A settled SELL of 20 MSCI EM shares for 650 EUR, then ``cells``."""
    return _row(**{"category": "TRADING", "type": "SELL", "asset_class": "FUND", "name": "Core MSCI EM IMI USD (Acc)", "symbol": MSCI_EM, "shares": "-20.0000000000", "price": "32.5000000000", "amount": "650.00", "description": "Sell trade MSCI EM", **cells})


def _write(folder: Path, rows: Sequence[Dict[str, str]], *, header: Sequence[str] = HEADER, delimiter: str = ",", name: str = "transactions.csv") -> Path:
    """An export: the header, then one line per row, every cell quoted; a row without a transaction id gets a distinct one."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(header)
    for index, row in enumerate(rows, start=1):
        values = {"transaction_id": f"00000000-0000-4000-9000-{index:012d}", **row}
        writer.writerow([values.get(column, "") for column in header])
    path = folder / name
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return path


def _write_case(folder: Path, row: Dict[str, str], *, header: Sequence[str] = HEADER) -> Path:
    """A file with the base deposit on line 2 and the case's row on line 3."""
    return _write(folder, [_row(), row], header=header)


def _rewrite(source: Path, target: Path, *, delimiter: str = ",", order: Optional[Sequence[int]] = None, upper: bool = False) -> Path:
    """``source`` written again with another delimiter, its columns in ``order``, its header in upper case — the same rows."""
    rows = list(csv.reader(io.StringIO(source.read_text(encoding="utf-8"), newline="")))
    order = list(order) if order is not None else list(range(len(rows[0])))
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, quoting=csv.QUOTE_ALL, lineterminator="\n")
    for number, cells in enumerate(rows):
        cells = [cells[i] for i in order]
        writer.writerow([cell.upper() for cell in cells] if upper and number == 0 else cells)
    target.write_text(buffer.getvalue(), encoding="utf-8")
    return target


# =============================================================================
# FIXTURE GUARDS — this file's expectations against the samples, never the plugin
# =============================================================================


class TestFixtureGuards:
    def test_clean_sample_header_is_the_23_columns(self):
        """Fixture guard: the clean sample's header is ``HEADER``, so the synthetic files have the sample's shape."""
        header = next(csv.reader(io.StringIO(CLEAN_SAMPLE.read_text(encoding="utf-8"))))
        assert tuple(header) == HEADER

    def test_excel_sample_is_one_quoted_cell_per_crlf_line(self):
        """Fixture guard: the Excel sample is the other shape — CRLF lines, each one quoted cell holding the delimiter."""
        raw = EXCEL_SAMPLE.read_bytes()
        assert b"\r\n" in raw
        for line in raw.decode("utf-8").split("\r\n"):
            if line:
                cells = next(csv.reader([line]))
                assert len(cells) == 1 and "," in cells[0], line[:60]


# =============================================================================
# A. IDENTITY
# =============================================================================


class TestIdentity:
    def test_code_version_and_extension(self):
        """A: the code the brokers name, version 1.2.0 (the Transaction export), ``.csv`` only."""
        plugin = _plugin()
        assert plugin.provider_code == PLUGIN_CODE
        assert plugin.plugin_version == PLUGIN_VERSION
        assert plugin.supported_extensions == [".csv"]

    def test_other_extension_refused(self, tmp_path: Path):
        """A: the clean export renamed ``.txt`` is not read."""
        path = tmp_path / "transactions.txt"
        path.write_bytes(CLEAN_SAMPLE.read_bytes())
        assert _plugin().can_parse(path) is False


# =============================================================================
# B. RECOGNITION
# =============================================================================


class TestRecognition:
    @pytest.mark.parametrize("sample", [CLEAN_SAMPLE, EXCEL_SAMPLE, DUTCH_SAMPLE], ids=["clean", "excel", "dutch"])
    def test_samples_recognised(self, sample: Path):
        """B: both shapes of the Transaction export and the Dutch CSV."""
        assert _plugin().can_parse(sample) is True

    def test_semicolon_variant_recognised(self, tmp_path: Path):
        """B: the same columns separated by ``;``."""
        path = _rewrite(CLEAN_SAMPLE, tmp_path / "semicolon.csv", delimiter=";")
        assert _plugin().can_parse(path) is True

    def test_columns_in_another_order_and_upper_case_recognised(self, tmp_path: Path):
        """B: columns are read by name, in any order and case."""
        path = _rewrite(CLEAN_SAMPLE, tmp_path / "shuffled.csv", order=list(reversed(range(len(HEADER)))), upper=True)
        assert _plugin().can_parse(path) is True

    def test_value_date_header_recognised(self, tmp_path: Path):
        """B: the form with ``value_date`` instead of the four counterparty columns."""
        assert _plugin().can_parse(_write(tmp_path, [_row(value_date="2025-04-01")], header=VALUE_DATE_HEADER)) is True

    @pytest.mark.parametrize("missing", REQUIRED_COLUMNS)
    def test_header_missing_a_required_column_refused(self, missing: str, tmp_path: Path):
        """B: a header without one required column is not the export: refused, and parse says ``header_mismatch``."""
        header = [column for column in HEADER if column != missing]
        path = _write(tmp_path, [_row()], header=header)
        plugin = _plugin()
        assert plugin.can_parse(path) is False
        with pytest.raises(BRIMParseError) as raised:
            plugin.parse(path, broker_id=BROKER_ID)
        assert raised.value.details.get("code") == "header_mismatch"
        assert BRIMProviderRegistry.auto_detect_plugin(path) != PLUGIN_CODE

    @pytest.mark.parametrize("shape", ["clean", "excel", "semicolon", "dutch"])
    def test_auto_detect_picks_trade_republic(self, shape: str, tmp_path: Path):
        """B: what the upload offers first is Trade Republic, never the generic CSV nor another broker."""
        path = {"clean": CLEAN_SAMPLE, "excel": EXCEL_SAMPLE, "dutch": DUTCH_SAMPLE}.get(shape) or _rewrite(CLEAN_SAMPLE, tmp_path / "semicolon.csv", delimiter=";")
        detected = BRIMProviderRegistry.auto_detect_plugin(path)
        assert detected == PLUGIN_CODE, f"{shape}: detected as {detected!r}, compatible {BRIMProviderRegistry.get_compatible_plugins(path)}"


# =============================================================================
# C. THE SAMPLES
# =============================================================================

# The clean sample by hand, one entry per non-zero amount/fee/tax column (line numbers of the file in the comments).
CLEAN_EXPECTED: Counter = Counter(
    [
        # line 2: interest 5.00, withholding tax -1.30
        ("INTEREST", "2025-02-03", "0", "5", "EUR", None),
        ("TAX", "2025-02-03", "0", "-1.3", "EUR", None),
        # line 3: savings plan, 0.123456 shares for -10.00
        ("BUY", "2025-02-04", "0.123456", "-10", "EUR", MSCI_WORLD),
        # line 4: stamp duty, the tax column of a TAX_OPTIMIZATION row
        ("TAX", "2025-02-10", "0", "-3.5", "EUR", None),
        # line 5: sell of 20 shares for 650.00, fee -1.00, tax -12.35, all on the asset
        ("SELL", "2025-02-21", "-20", "650", "EUR", MSCI_EM),
        ("FEE", "2025-02-21", "0", "-1", "EUR", MSCI_EM),
        ("TAX", "2025-02-21", "0", "-12.35", "EUR", MSCI_EM),
        # line 6: crypto buy, 0.04 ETH for -100.00, fee -1.00
        ("BUY", "2025-02-25", "0.04", "-100", "EUR", ETH),
        ("FEE", "2025-02-25", "0", "-1", "EUR", ETH),
        # line 7: interest 4.00, withholding tax -1.04
        ("INTEREST", "2025-03-03", "0", "4", "EUR", None),
        ("TAX", "2025-03-03", "0", "-1.04", "EUR", None),
        # line 8: Apple, datetime 2025-03-03T23:15Z but date 2025-03-04: the date column wins
        ("BUY", "2025-03-04", "2", "-400", "EUR", APPLE),
        ("FEE", "2025-03-04", "0", "-1", "EUR", APPLE),
        # line 9: a positive tax, a refund booked as interest
        ("INTEREST", "2025-03-12", "0", "2.1", "EUR", None),
        # line 10: incoming transfer (a name, no symbol: no asset)
        ("DEPOSIT", "2025-03-15", "0", "1000", "EUR", None),
    ]
)


class TestSamples:
    def test_clean_sample_row_by_row(self):
        """C: the clean sample's 15 transactions, as a multiset."""
        out = _parse(CLEAN_SAMPLE)
        assert sum(CLEAN_EXPECTED.values()) == 15
        assert _keys(out) == CLEAN_EXPECTED

    def test_clean_sample_broker_tags_and_descriptions(self):
        """C: every transaction carries the broker and the tags; legs name their row's description."""
        out = _parse(CLEAN_SAMPLE)
        assert {tx.broker_id for tx in out.transactions} == {BROKER_ID}
        assert all(tx.tags == TAGS for tx in out.transactions)
        descriptions = {tx.description for tx in out.transactions}
        assert "Tax refund: Tax optimisation (refund)" in descriptions
        assert "Stamp Duty Tax (Portfolio)" not in descriptions and "Tax: Stamp Duty Tax (Portfolio)" in descriptions
        assert "Fee: Buy trade US0378331005 APPLE INC., quantity: 2" in descriptions

    def test_clean_sample_notices(self):
        """C: one info notice, the tax refund of line 9, nothing else."""
        out = _parse(CLEAN_SAMPLE)
        assert _codes(out) == [TAX_REFUND]
        notice = _notice(out, TAX_REFUND)
        assert notice.severity == "info"
        assert notice.context == {"count": 1}
        assert len(notice.evidence) == 1
        evidence = notice.evidence[0]
        assert evidence.row_numbers == [9]
        assert evidence.headers == list(HEADER)
        assert evidence.rows[0][HEADER.index("transaction_id")] == "00000000-0000-4000-8000-000000000008"

    def test_clean_sample_extracted_assets(self):
        """C: four securities in order of first use; ISINs as ISIN, the crypto symbol as a ticker; names from the name column."""
        out = _parse(CLEAN_SAMPLE)
        assets = [(asset_id, info.extracted_isin, info.extracted_symbol, info.extracted_name) for asset_id, info in sorted(out.extracted_assets.items(), reverse=True)]
        assert assets == [
            (FAKE_ASSET_ID_BASE, MSCI_WORLD, None, "Core MSCI World USD (Acc)"),
            (FAKE_ASSET_ID_BASE - 1, MSCI_EM, None, "Core MSCI EM IMI USD (Acc)"),
            (FAKE_ASSET_ID_BASE - 2, None, ETH, "Ethereum"),
            (FAKE_ASSET_ID_BASE - 3, APPLE, None, "Apple"),
        ]

    def test_excel_shape_gives_the_same_output(self):
        """C: the Excel re-save is the same rows: identical transactions, assets and notices."""
        assert _comparable(_parse(EXCEL_SAMPLE)) == _comparable(_parse(CLEAN_SAMPLE))

    def test_semicolon_variant_gives_the_same_output(self, tmp_path: Path):
        """C: the ``;`` variant is the same rows."""
        path = _rewrite(CLEAN_SAMPLE, tmp_path / "semicolon.csv", delimiter=";")
        assert _comparable(_parse(path)) == _comparable(_parse(CLEAN_SAMPLE))

    def test_columns_in_another_order_give_the_same_transactions(self, tmp_path: Path):
        """C: read by name, so reversing the columns (and upper-casing the header) changes no transaction nor asset."""
        path = _rewrite(CLEAN_SAMPLE, tmp_path / "shuffled.csv", order=list(reversed(range(len(HEADER)))), upper=True)
        shuffled, clean = _comparable(_parse(path)), _comparable(_parse(CLEAN_SAMPLE))
        assert shuffled["transactions"] == clean["transactions"]
        assert shuffled["assets"] == clean["assets"]

    def test_dutch_sample_still_gives_its_nine_transactions(self):
        """C: the Dutch 8-column CSV is read as before: 9 transactions; the two rows with Kosten are listed."""
        out = _parse(DUTCH_SAMPLE)
        assert Counter(tx.type.value for tx in out.transactions) == Counter({"BUY": 4, "SELL": 2, "DEPOSIT": 1, "WITHDRAWAL": 1, "DIVIDEND": 1})
        assert {tx.broker_id for tx in out.transactions} == {BROKER_ID}
        assert _codes(out) == [ROWS_NOT_RECOGNIZED]
        assert _notice(out, ROWS_NOT_RECOGNIZED).context["count"] == 2


# =============================================================================
# D. THE RULES, ON SYNTHETIC FILES
# =============================================================================


class TestDateColumn:
    def test_date_column_not_utc_datetime(self, tmp_path: Path):
        """D: an evening booking whose UTC instant falls on the day before is dated by ``date``."""
        out = _parse(_write_case(tmp_path, _buy(datetime="2025-03-03T23:15:02.618Z", date="2025-03-04")))
        assert _keys(out) == Counter([BASE_KEY, ("BUY", "2025-03-04", "2", "-400", "EUR", APPLE)])

    def test_unreadable_date_does_not_fall_back_to_datetime(self, tmp_path: Path):
        """D: a ``date`` that cannot be read leaves the row out, even with a readable ``datetime``."""
        out = _parse(_write_case(tmp_path, _buy(datetime="2025-03-04T10:00:00Z", date="04/03/2025")))
        assert _keys(out) == Counter([BASE_KEY])
        assert _codes(out) == [ROWS_UNREADABLE]


class TestLegs:
    def test_sell_with_fee_and_tax_is_three_transactions_verbatim(self, tmp_path: Path):
        """D: each non-zero column is its own transaction on the row's asset; nothing is netted."""
        out = _parse(_write_case(tmp_path, _sell(fee="-1.00", tax="-12.35")))
        assert _keys(out) == Counter(
            [
                BASE_KEY,
                ("SELL", "2025-04-01", "-20", "650", "EUR", MSCI_EM),
                ("FEE", "2025-04-01", "0", "-1", "EUR", MSCI_EM),
                ("TAX", "2025-04-01", "0", "-12.35", "EUR", MSCI_EM),
            ]
        )

    def test_dividend_with_withholding_tax(self, tmp_path: Path):
        """D: a dividend and its withheld tax, both on the asset."""
        row = _row(type="DIVIDEND", asset_class="STOCK", name="Apple", symbol=APPLE, amount="3.00", tax="-0.45")
        out = _parse(_write_case(tmp_path, row))
        assert _keys(out) == Counter([BASE_KEY, ("DIVIDEND", "2025-04-01", "0", "3", "EUR", APPLE), ("TAX", "2025-04-01", "0", "-0.45", "EUR", APPLE)])

    def test_currency_from_the_row_and_fx_columns_ignored(self, tmp_path: Path):
        """D: the row's ``currency``; ``original_*`` and ``fx_rate`` are not read."""
        row = _row(amount="50.00", currency="usd", original_amount="46.00", original_currency="EUR", fx_rate="1.0870")
        out = _parse(_write_case(tmp_path, row))
        assert _keys(out) == Counter([BASE_KEY, ("DEPOSIT", "2025-04-01", "0", "50", "USD", None)])

    def test_lone_decimal_comma_is_read(self, tmp_path: Path):
        """D: a file re-saved with a comma locale (``;`` and ``-400,00``) reads the same numbers."""
        path = _write(tmp_path, [_row(), _buy(amount="-400,00", shares="2,0", fee="-1,00")], delimiter=";")
        out = _parse(path)
        assert _keys(out) == Counter([BASE_KEY, ("BUY", "2025-04-01", "2", "-400", "EUR", APPLE), ("FEE", "2025-04-01", "0", "-1", "EUR", APPLE)])

    def test_withdrawal_and_fee_rows(self, tmp_path: Path):
        """D: money out by its type: a transfer out is a WITHDRAWAL, a card ordering fee a FEE, both read verbatim."""
        rows = [_row(), _row(type="TRANSFER_OUTBOUND", amount="-30.00"), _row(type="CARD_ORDERING_FEE", amount="-5.00")]
        out = _parse(_write(tmp_path, rows))
        assert _keys(out) == Counter([BASE_KEY, ("WITHDRAWAL", "2025-04-01", "0", "-30", "EUR", None), ("FEE", "2025-04-01", "0", "-5", "EUR", None)])


class TestTaxRefund:
    def test_positive_tax_on_a_sell_is_interest_on_the_asset(self, tmp_path: Path):
        """D: a positive tax is an INTEREST «Tax refund», on the row's asset, with an info notice counting it."""
        out = _parse(_write_case(tmp_path, _sell(tax="5.00")))
        assert _keys(out) == Counter([BASE_KEY, ("SELL", "2025-04-01", "-20", "650", "EUR", MSCI_EM), ("INTEREST", "2025-04-01", "0", "5", "EUR", MSCI_EM)])
        assert "Tax refund: Sell trade MSCI EM" in {tx.description for tx in out.transactions}
        notice = _notice(out, TAX_REFUND)
        assert notice.severity == "info"
        assert notice.context == {"count": 1}
        assert notice.evidence[0].row_numbers == [3]
        assert _codes(out) == [TAX_REFUND]

    def test_refunds_are_counted(self, tmp_path: Path):
        """D: two refund rows, one notice with count 2 and both lines."""
        rows = [_row(), _row(type="TAX_OPTIMIZATION", amount="0.000000", tax="2.10"), _row(type="TAX_OPTIMIZATION", amount="0", tax="0.40")]
        out = _parse(_write(tmp_path, rows))
        assert _keys(out) == Counter([BASE_KEY, ("INTEREST", "2025-04-01", "0", "2.1", "EUR", None), ("INTEREST", "2025-04-01", "0", "0.4", "EUR", None)])
        notice = _notice(out, TAX_REFUND)
        assert notice.context == {"count": 2}
        assert notice.evidence[0].row_numbers == [3, 4]


class TestNotYetSettled:
    def test_future_date_left_out_whole(self, tmp_path: Path):
        """D: a trade dated after today is left out with its fee and tax, with an info notice."""
        out = _parse(_write_case(tmp_path, _sell(date=FAR_FUTURE, datetime=f"{FAR_FUTURE}T10:00:00Z", fee="-1.00", tax="-2.00")))
        assert _keys(out) == Counter([BASE_KEY])
        notice = _notice(out, NOT_SETTLED)
        assert notice.severity == "info"
        assert notice.context == {"count": 1}
        assert notice.evidence[0].row_numbers == [3]
        assert _codes(out) == [NOT_SETTLED]

    def test_future_value_date_left_out_whole(self, tmp_path: Path):
        """D: a past ``date`` with a ``value_date`` after today is not settled either."""
        rows = [_row(value_date="2025-04-01"), _sell(value_date=FAR_FUTURE, fee="-1.00", tax="-2.00")]
        out = _parse(_write(tmp_path, rows, header=VALUE_DATE_HEADER))
        assert _keys(out) == Counter([BASE_KEY])
        assert _notice(out, NOT_SETTLED).context == {"count": 1}

    def test_past_value_date_is_imported(self, tmp_path: Path):
        """D: control — a past ``value_date`` changes nothing, and the transaction keeps the ``date`` column."""
        rows = [_row(value_date="2025-04-01"), _sell(value_date="2025-04-03")]
        out = _parse(_write(tmp_path, rows, header=VALUE_DATE_HEADER))
        assert _keys(out) == Counter([BASE_KEY, ("SELL", "2025-04-01", "-20", "650", "EUR", MSCI_EM)])
        assert _codes(out) == []


class TestSilentRows:
    def test_repeated_transaction_id_dropped_without_a_notice(self, tmp_path: Path):
        """D: the same booking twice is imported once, silently."""
        tid = "00000000-0000-4000-8000-00000000beef"
        rows = [_row(), _buy(transaction_id=tid, fee="-1.00"), _buy(transaction_id=tid, fee="-1.00")]
        out = _parse(_write(tmp_path, rows))
        assert _keys(out) == Counter([BASE_KEY, ("BUY", "2025-04-01", "2", "-400", "EUR", APPLE), ("FEE", "2025-04-01", "0", "-1", "EUR", APPLE)])
        assert _codes(out) == []

    def test_row_with_nothing_to_book_dropped_without_a_notice(self, tmp_path: Path):
        """D: an interest of zero with no tax books nothing and says nothing."""
        out = _parse(_write_case(tmp_path, _row(type="INTEREST_PAYMENT", amount="0.000000")))
        assert _keys(out) == Counter([BASE_KEY])
        assert _codes(out) == []


# Each row the plugin does not recognise, with the reason it gives (a substring of the last evidence cell).
NOT_RECOGNIZED_CASES = [
    pytest.param(_row(type="DIVIDEND", asset_class="STOCK", symbol=APPLE, amount="-3.00"), "DIVIDEND with an unexpected sign", id="negative-dividend"),
    pytest.param(_buy(fee="1.00"), "positive fee", id="positive-fee"),
    pytest.param(_row(type="SAVEBACK"), "unknown type: 'CASH/SAVEBACK'", id="unknown-cash-type"),
    pytest.param(_row(category="CORPORATE_ACTION", type="SPLIT", symbol=APPLE, amount="0"), "unknown type: 'CORPORATE_ACTION/SPLIT'", id="unknown-category"),
    pytest.param(_buy(account_type="JUNIOR"), "account_type JUNIOR", id="junior-account"),
    pytest.param(_sell(shares="20.0000000000"), "SELL with unexpected signs", id="sell-positive-shares"),
    pytest.param(_buy(amount="400.00"), "BUY with unexpected signs", id="buy-positive-amount"),
    pytest.param(_row(type="FEE", amount="5.00"), "FEE with an unexpected sign", id="positive-fee-row"),
    pytest.param(_row(type="TRANSFER_OUTBOUND", amount="30.00"), "TRANSFER_OUTBOUND with an unexpected sign", id="positive-withdrawal"),
    pytest.param(_row(type="TAX_OPTIMIZATION", amount="1.00", tax="-1.00"), "TAX_OPTIMIZATION with an amount", id="tax-optimization-with-amount"),
]

# Each row the plugin cannot read, with the reason it gives.
UNREADABLE_CASES = [
    pytest.param(_buy(date="2025-13-01"), HEADER, "invalid date", id="bad-date"),
    pytest.param(_buy(date=""), HEADER, "invalid date", id="empty-date"),
    pytest.param(_buy(amount="ten"), HEADER, "invalid number or date", id="bad-amount"),
    pytest.param(_buy(tax="1.2.3"), HEADER, "invalid number or date", id="bad-tax"),
    pytest.param(_buy(value_date="soon"), VALUE_DATE_HEADER, "invalid number or date", id="bad-value-date"),
    pytest.param(_buy(currency=""), HEADER, "invalid currency", id="empty-currency"),
    pytest.param(_buy(currency="EURO"), HEADER, "invalid currency", id="bad-currency"),
    pytest.param(_buy(symbol=""), HEADER, "BUY without a symbol", id="buy-without-symbol"),
    pytest.param(_row(type="DIVIDEND", amount="3.00"), HEADER, "DIVIDEND without a symbol", id="dividend-without-symbol"),
    pytest.param(_buy(shares=""), HEADER, "BUY without shares or amount", id="buy-without-shares"),
]


def _assert_listed(out: BRIMParseOutput, code: str, header: Sequence[str], row: Dict[str, str], reason: str) -> None:
    """Only the base deposit is imported; one ``code`` warning lists line 3 with its cells and ``reason``, and asks for an issue."""
    assert _keys(out) == Counter([BASE_KEY])
    assert _codes(out) == [code]
    notice = _notice(out, code)
    assert notice.severity == "warning"
    assert notice.context == {"count": 1, "report_issue": True}
    evidence = notice.evidence[0]
    assert evidence.row_numbers == [3]
    assert evidence.headers[: len(header)] == list(header)
    listed = evidence.rows[0]
    assert listed[HEADER.index("type")] == row["type"]
    assert reason in listed[-1], f"reason {listed[-1]!r} does not name {reason!r}"


class TestRowsLeftOut:
    @pytest.mark.parametrize(("row", "reason"), NOT_RECOGNIZED_CASES)
    def test_not_recognized(self, row: Dict[str, str], reason: str, tmp_path: Path):
        """D: a row the plugin does not import is listed in ``rows_not_recognized`` with its reason."""
        out = _parse(_write_case(tmp_path, row))
        _assert_listed(out, ROWS_NOT_RECOGNIZED, HEADER, row, reason)

    @pytest.mark.parametrize(("row", "header", "reason"), UNREADABLE_CASES)
    def test_unreadable(self, row: Dict[str, str], header: Sequence[str], reason: str, tmp_path: Path):
        """D: a row the plugin cannot read is listed in ``rows_unreadable`` with its reason."""
        out = _parse(_write_case(tmp_path, row, header=header))
        _assert_listed(out, ROWS_UNREADABLE, header, row, reason)

    def test_only_unknown_rows_warn_that_nothing_was_found(self, tmp_path: Path):
        """D: a file whose every row is left out imports nothing and says so, besides listing the row."""
        out = _parse(_write(tmp_path, [_row(type="SAVEBACK")]))
        assert out.transactions == []
        assert ROWS_NOT_RECOGNIZED in _codes(out)
        assert any("No valid transactions" in notice.message for notice in out.warnings)


class TestExtractedAssets:
    def test_isin_or_ticker(self, tmp_path: Path):
        """D: a symbol shaped as an ISIN is an ISIN; any other symbol, and every CRYPTO symbol, is a ticker; one asset per symbol."""
        rows = [
            _row(),
            _buy(asset_class="FUND", name="Core MSCI World USD (Acc)", symbol=MSCI_WORLD),
            _buy(asset_class="CRYPTO", name="Bitcoin", symbol="BTC"),
            _buy(asset_class="CRYPTO", name="Bitcoin ISIN-shaped", symbol="XF000BTC0017"),
            _buy(asset_class="STOCK", name="Apple ticker", symbol="AAPL"),
            _buy(asset_class="FUND", name="Core MSCI World again", symbol=MSCI_WORLD),
        ]
        out = _parse(_write(tmp_path, rows))
        assets = [(info.extracted_isin, info.extracted_symbol, info.extracted_name) for _, info in sorted(out.extracted_assets.items(), reverse=True)]
        assert assets == [
            (MSCI_WORLD, None, "Core MSCI World USD (Acc)"),
            (None, "BTC", "Bitcoin"),
            (None, "XF000BTC0017", "Bitcoin ISIN-shaped"),
            (None, "AAPL", "Apple ticker"),
        ]
        assert sorted(out.extracted_assets) == [FAKE_ASSET_ID_BASE - 3, FAKE_ASSET_ID_BASE - 2, FAKE_ASSET_ID_BASE - 1, FAKE_ASSET_ID_BASE]
        assert Counter(_asset_key(out, tx.asset_id) for tx in out.transactions if tx.type.value == "BUY") == Counter({MSCI_WORLD: 2, "BTC": 1, "XF000BTC0017": 1, "AAPL": 1})

    def test_cash_rows_have_no_asset(self, tmp_path: Path):
        """D: a transfer with a counterparty name and no symbol books no asset and extracts none."""
        out = _parse(_write(tmp_path, [_row(name="Jane Example", counterparty_name="Jane Example")]))
        assert _keys(out) == Counter([BASE_KEY])
        assert out.extracted_assets == {}
