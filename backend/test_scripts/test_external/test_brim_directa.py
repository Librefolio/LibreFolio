"""
Test Suite: the Directa plugin — ``broker_directa``, its linked charges (project 66, lot P3)

The rest of Directa (detection, numbers, CSV/XLSX parity, the asset of a withholding) is pinned in
``test_brim_providers.py``; the rows it leaves out in ``test_brim_row_skips.py``; the operation date in
``test_brim_operation_date.py``. This module pins what lot P3 adds, from the P2 contract (§2, §7) and the decisions of
16/11 (``domande-FEE.md``, «Directa, sugli estratti veri» and answer (a) on «Rit.provento etf»):

- «Commissioni» names the one BUY/SELL with the same ``Riferimento ordine``;
- «Rit. etf» (capital gain withholding) names the one SELL with the same ``Riferimento ordine``;
- «Rit.cedola obb.» names the one «Cedola obb.» with the same operation date and ISIN (the ``Protocollo`` differs
  between the two rows: it is not the key);
- «Rit.provento etf» becomes a TAX, negative (version 1.1.0 read it as a positive DIVIDEND: the type map tries
  «provento» before «rit.»), and names the one «Provento etf» with the same date and ISIN;
- the Tobin tax names the one BUY/SELL with the same ``Riferimento ordine`` when the row carries one, else stays free;
- «Bollo portafoglio titoli» stays free (an account charge); so does «Ritenuta su plusvalenza» (no security);
- one parent candidate only, otherwise the charge stays free; the output order does not change;
- besides the names, only the «Rit.provento etf» rows change (type and sign): the reimport recognises every other row
  of the snapshot taken at HEAD b44c341c5 (plugin 1.1.0) and adds those two — the «delete and reimport» line of the
  changelog;
- the plugin version goes up.

The repository sample masks ``Riferimento ordine`` with one value on every trade and has no commission, no «Rit. etf»
and no Tobin tax, so the key rules are proved on rows written in ``tmp_path``: every reference, protocol and amount
there is invented; the ISINs are public identifiers. A test whose docstring starts with "RED" fails before the code
of P3 on its own assertion; one that starts with "Guard" passes before and after.

The reimport opens a private in-memory SQLite and disposes it: no server, no shared database.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pytest

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import BRIMParseOutput
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.test_scripts.brim_charge_links import (
    LINK_FIELDS,
    RowKey,
    assert_charge_link_structure,
    assert_expected_charge_links,
    load_previous_snapshot,
    sample_reimport_report,
    version_tuple,
)
from backend.test_scripts.brim_samples import SampleDir

PLUGIN_CODE = "broker_directa"
SAMPLE_DIR = SampleDir()
SAMPLE_NAME = "directa-export.csv"
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7
# The «Rit.provento etf» rows of the sample are found by the plugin's own description, never by position.
RIT_PROVENTO = "Rit.provento etf"

# Securities of the sample (public identifiers).
IEMB = "IE00B2NPKV68"
CNYB = "IE00BYPC1H27"
ALPER = "IT0005595373"
BTP_VALORE = "IT0005583478"
# Securities of the invented rows (public identifiers; every amount, date, protocol and reference is invented).
SWDA = "IE00B4L5Y983"
EIMI = "IE00BKM4GZ66"


def _plugin() -> BRIMProvider:
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"{PLUGIN_CODE} is not registered"
    return plugin


def _parse(path: Path) -> BRIMParseOutput:
    out = _plugin().parse(path, BROKER_ID)
    assert out.validation_issues == [], f"{path.name}: {out.validation_issues}"
    return out


def _key(tx_type: str, day: str, amount: str, isin: Optional[str]) -> RowKey:
    """A row of a Directa output: always EUR («Importo euro»)."""
    return (tx_type, day, amount, "EUR", isin)


# =============================================================================
# THE REPOSITORY SAMPLE
# =============================================================================

#: The sample after P3: every FEE/TAX either linked or free (``assert_expected_charge_links`` is exhaustive).
SAMPLE_LINKED: List[Tuple[RowKey, RowKey]] = [
    # «Rit.provento etf» → its «Provento etf» (same date, same ISIN), now a negative TAX.
    (_key("TAX", "2024-12-27", "-3.57", IEMB), _key("DIVIDEND", "2024-12-27", "20.95", IEMB)),
    (_key("TAX", "2024-12-27", "-2.15", CNYB), _key("DIVIDEND", "2024-12-27", "10.94", CNYB)),
    # «Rit.cedola obb.» → its «Cedola obb.» (same operation date, same ISIN).
    (_key("TAX", "2024-12-06", "-18.53", ALPER), _key("INTEREST", "2024-12-06", "71.25", ALPER)),
    (_key("TAX", "2024-12-02", "-3.05", BTP_VALORE), _key("INTEREST", "2024-12-02", "24.38", BTP_VALORE)),
]
SAMPLE_FREE: List[RowKey] = [
    # «Ritenuta su plusvalenza»: no security, no reference.
    _key("TAX", "2024-12-27", "-2.86", None),
]


def _rit_provento_indices(rows: Sequence[TXCreateItem]) -> List[int]:
    return [index for index, tx in enumerate(rows) if (tx.description or "").startswith(RIT_PROVENTO)]


class TestLinkedCharges:
    """P3 — project 66 (P2 contract §2 and §7): each Directa charge names its one parent; with zero or several
    candidates it stays free; «Rit.provento etf» becomes a negative TAX."""

    # -- the repository sample -----------------------------------------------------------------------------------------

    def test_each_charge_of_the_sample_names_its_one_parent(self):
        """RED before P3: the expected links of the sample, exhaustive (every FEE/TAX linked or declared free)."""
        out = _parse(SAMPLE_DIR / SAMPLE_NAME)

        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{SAMPLE_NAME}]", linked=SAMPLE_LINKED, free=SAMPLE_FREE)

    def test_rit_provento_etf_is_a_negative_tax(self):
        """RED before P3 (decision (a), 16/11): the two «Rit.provento etf» rows of the sample are TAX, negative, on the
        security of their «Provento etf»; 1.1.0 made them positive DIVIDENDs."""
        out = _parse(SAMPLE_DIR / SAMPLE_NAME)
        indices = _rit_provento_indices(out.transactions)
        assert len(indices) == 2, f"presence barrier: the sample holds two «{RIT_PROVENTO}» rows, found {len(indices)}"

        got = sorted((out.transactions[i].type.value, str(out.transactions[i].cash.amount) if out.transactions[i].cash else None, out.extracted_assets[out.transactions[i].asset_id].extracted_isin) for i in indices)
        assert got == [("TAX", "-2.15", CNYB), ("TAX", "-3.57", IEMB)]

    def test_the_links_of_the_sample_are_well_formed(self):
        """Guard: every ``ref`` unique, every ``parent_ref`` names a ``ref`` of the output."""
        assert_charge_link_structure(_parse(SAMPLE_DIR / SAMPLE_NAME), f"{PLUGIN_CODE} [{SAMPLE_NAME}]")

    def test_only_names_change_but_the_rit_provento_rows_change_type_and_sign(self):
        """RED before P3. Every row equals the snapshot's (1.1.0, HEAD b44c341c5), in order, but for ``ref``/``parent_ref``;
        the two «Rit.provento etf» rows change exactly their type (DIVIDEND → TAX) and the sign of their cash. The
        extracted assets are the snapshot's."""
        previous = load_previous_snapshot(PLUGIN_CODE, SAMPLE_NAME, BROKER_ID)
        out = _parse(SAMPLE_DIR / SAMPLE_NAME)
        assert len(out.transactions) == len(previous.transactions), f"{len(out.transactions)} rows, the snapshot has {len(previous.transactions)}"
        assert out.extracted_assets == previous.extracted_assets
        retyped = _rit_provento_indices(previous.transactions)
        assert len(retyped) == 2, f"presence barrier: the snapshot holds two «{RIT_PROVENTO}» rows, found {len(retyped)}"

        problems: List[str] = []
        for index, (before, after) in enumerate(zip(previous.transactions, out.transactions, strict=True)):
            old, new = before.model_dump(mode="json", exclude=set(LINK_FIELDS)), after.model_dump(mode="json", exclude=set(LINK_FIELDS))
            changed = sorted(field for field in old if old[field] != new[field])
            label = f"#{index} {before.type.value} {before.date} {before.description!r}"
            if index in retyped:
                assert before.type == TransactionType.DIVIDEND and before.cash is not None and before.cash.amount > 0, f"premise: 1.1.0 made {label} a positive DIVIDEND"
                expected_cash = (before.cash.code, -before.cash.amount)
                if changed != ["cash", "type"] or after.type != TransactionType.TAX or after.cash is None or (after.cash.code, after.cash.amount) != expected_cash:
                    problems.append(f"{label}: should become TAX {expected_cash}, changed {changed}: {after.type.value} {after.cash}")
            elif changed:
                problems.append(f"{label}: should not change besides its names, changed {changed}")
        assert not problems, f"{SAMPLE_NAME}: the output changed beyond the expected (snapshot HEAD {previous.source_head}):\n  " + "\n  ".join(problems)

    @pytest.mark.asyncio
    async def test_reimport_recognises_every_row_but_the_rit_provento_ones(self):
        """RED before P3 (P2 contract §7, changelog «delete and reimport»): over the rows 1.1.0 saved (without links), every
        row is found as a duplicate except the two «Rit.provento etf» rows, whose type changed."""
        report = await sample_reimport_report(_plugin(), SAMPLE_NAME)
        output = report.output
        changed = frozenset(_rit_provento_indices(output.transactions))
        assert len(changed) == 2, f"presence barrier: two «{RIT_PROVENTO}» rows in the new output, found {len(changed)}"

        assert sorted(report.unique) == sorted(changed), "the reimport adds exactly the two «Rit.provento etf» rows"
        assert report.duplicates == frozenset(range(len(output.transactions))) - changed, "every other row is recognised"

    def test_the_version_is_above_the_previous_one(self):
        """RED before P3: the plugin goes up a version (P2 contract §7)."""
        previous = load_previous_snapshot(PLUGIN_CODE, SAMPLE_NAME, BROKER_ID)
        assert version_tuple(_plugin().plugin_version) > version_tuple(previous.plugin_version), f"{PLUGIN_CODE} {_plugin().plugin_version}: not above the snapshot's {previous.plugin_version}"


# =============================================================================
# INVENTED ROWS
# =============================================================================

HEADER = ["Data operazione", "Data valuta", "Tipo operazione", "Ticker", "Isin", "Protocollo", "Descrizione", "Quantità", "Importo euro", "Importo Divisa", "Divisa", "Riferimento ordine"]
PREAMBLE = [
    ["Conto : CONTO DI PROVA"],
    ["Data estrazione : 3-11-2025 10:00:00"],
    [],
    ["Tutti i movimenti ordinati per Data Operazione"],
    ["Dal : 01-01-2025"],
    ["al : 31-10-2025"],
    [],
]
DAY = "15-10-2025"
ISO_DAY = "2025-10-15"
#: The three spellings of «no reference»: an empty cell, a cell of spaces (as on the sample's income rows), no cell.
NO_REFERENCE = [pytest.param("", id="empty"), pytest.param("              ", id="spaces"), pytest.param(None, id="no-cell")]


@dataclass(frozen=True)
class Row:
    """One data row of an invented Directa export. ``ref=None`` leaves the «Riferimento ordine» cell out (11 cells)."""

    kind: str
    amount: str
    isin: str = ""
    ticker: str = ""
    ref: Optional[str] = ""
    day: str = DAY
    value_day: Optional[str] = None
    protocol: str = ""
    name: str = ""
    quantity: str = "0"

    def cells(self) -> List[str]:
        row = [self.day, self.value_day or self.day, self.kind, self.ticker, self.isin, self.protocol, self.name, self.quantity, self.amount, "0", "EUR"]
        return row if self.ref is None else [*row, self.ref]


def _pad(row: List[str]) -> List[str]:
    return [*row, *[""] * (len(HEADER) - len(row))]


def _write(tmp_path: Path, rows: Sequence[Row], name: str = "directa-invented.csv") -> Path:
    path = tmp_path / name
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        for line in PREAMBLE:
            writer.writerow(_pad(line))
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow(row.cells())
    return path


def _write_xlsx(tmp_path: Path, rows: Sequence[Row]) -> Path:
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for line in PREAMBLE:
        sheet.append(line)
    sheet.append(HEADER)
    for row in rows:
        cells: List[object] = row.cells()
        cells[7], cells[8] = float(row.quantity), float(row.amount)  # native numbers, as Directa's XLSX writes them
        sheet.append(cells)
    path = tmp_path / "directa-invented.xlsx"
    workbook.save(path)
    return path


def _buy(amount: str, ref: Optional[str], *, isin: str = SWDA, quantity: str = "2", day: str = DAY) -> Row:
    return Row("Acquisto", amount, isin=isin, ticker="T" + isin[-4:], ref=ref, quantity=quantity, day=day, name="ETF DI PROVA")


def _sell(amount: str, ref: Optional[str], *, isin: str = SWDA, quantity: str = "2", day: str = DAY) -> Row:
    return Row("Vendita", amount, isin=isin, ticker="T" + isin[-4:], ref=ref, quantity=quantity, day=day, name="ETF DI PROVA")


def _commission(amount: str, ref: Optional[str], *, isin: str = SWDA, day: str = DAY) -> Row:
    return Row("Commissioni", amount, isin=isin, ticker="T" + isin[-4:] if isin else "", ref=ref, day=day, name="ETF DI PROVA" if isin else "")


def _rit_etf(amount: str, ref: Optional[str], *, isin: str = SWDA) -> Row:
    return Row("Rit. etf", amount, isin=isin, ticker="T" + isin[-4:], ref=ref, name="ETF DI PROVA")


def _tobin(amount: str, ref: Optional[str], *, isin: str = SWDA) -> Row:
    return Row("Tobin tax", amount, isin=isin, ticker="T" + isin[-4:], ref=ref, name="ETF DI PROVA")


def _coupon(kind: str, amount: str, *, isin: str = BTP_VALORE, day: str = DAY, value_day: Optional[str] = None, protocol: str = "") -> Row:
    return Row(kind, amount, isin=isin, ticker="M." + isin[-6:], ref="              ", day=day, value_day=value_day, protocol=protocol, name="BTP DI PROVA")


def _income(kind: str, amount: str, *, isin: str = IEMB, day: str = DAY, protocol: str = "") -> Row:
    return Row(kind, amount, isin=isin, ticker="T" + isin[-4:], ref="              ", day=day, protocol=protocol, name="ETF A DISTRIBUZIONE")


def _of_type(out: BRIMParseOutput, kind: str) -> List[TXCreateItem]:
    return [tx for tx in out.transactions if tx.type.value == kind]


def _types(out: BRIMParseOutput) -> List[str]:
    return [tx.type.value for tx in out.transactions]


class TestLinkedChargesInvented:
    """P3 on invented rows: the keys (``Riferimento ordine``; operation date + ISIN), «one candidate only» on both sides,
    the row shapes (charge above or below its parent, blank references), the order of the output, the XLSX path."""

    # -- «Commissioni» → the BUY/SELL of its order ---------------------------------------------------------------------

    @pytest.mark.parametrize(("trade", "kind"), [pytest.param(_buy("-200.00", "ORD-A1"), "BUY", id="buy"), pytest.param(_sell("210.00", "ORD-A1"), "SELL", id="sell")])
    def test_a_commission_names_the_trade_of_its_order(self, trade: Row, kind: str, tmp_path: Path):
        """RED before P3: a commission and the one trade with the same «Riferimento ordine»."""
        out = _parse(_write(tmp_path, [trade, _commission("-1.50", "ORD-A1")]))
        parent = _key(kind, ISO_DAY, trade.amount, SWDA)

        assert_expected_charge_links(out, "one order", linked=[(_key("FEE", ISO_DAY, "-1.50", SWDA), parent)], free=[])

    def test_a_commission_above_its_trade_names_it_and_the_order_stays(self, tmp_path: Path):
        """RED before P3: the commission is written before its trade; it is linked all the same, and the output keeps the
        file's order (the plugin links in a second pass, P2 contract §5)."""
        out = _parse(_write(tmp_path, [_commission("-1.50", "ORD-A1"), _buy("-200.00", "ORD-A1")]))
        assert _types(out) == ["FEE", "BUY"], f"the output keeps the file's order, got {_types(out)}"

        assert_expected_charge_links(out, "commission above its trade", linked=[(_key("FEE", ISO_DAY, "-1.50", SWDA), _key("BUY", ISO_DAY, "-200.00", SWDA))], free=[])

    def test_two_orders_of_one_day_each_commission_names_its_own_trade(self, tmp_path: Path):
        """RED before P3: two orders of the same security on the same day, their commissions interleaved — each names the
        trade of its own reference, never the neighbouring row (the key is the reference, not date and ISIN)."""
        rows = [_buy("-200.00", "ORD-B1"), _commission("-2.00", "ORD-B2"), _buy("-100.00", "ORD-B2", quantity="1"), _commission("-1.50", "ORD-B1")]
        out = _parse(_write(tmp_path, rows))

        linked = [
            (_key("FEE", ISO_DAY, "-1.50", SWDA), _key("BUY", ISO_DAY, "-200.00", SWDA)),
            (_key("FEE", ISO_DAY, "-2.00", SWDA), _key("BUY", ISO_DAY, "-100.00", SWDA)),
        ]
        assert_expected_charge_links(out, "two orders, one day", linked=linked, free=[])

    def test_a_commission_without_its_own_security_takes_its_trades(self, tmp_path: Path):
        """RED before P3: a commission row with a reference but no ticker/ISIN is linked and takes the trade's asset
        (``_create_linked_charge`` fills a missing asset, P1a-b)."""
        out = _parse(_write(tmp_path, [_buy("-200.00", "ORD-A1"), _commission("-1.50", "ORD-A1", isin="")]))
        [fee] = _of_type(out, "FEE")
        [buy] = _of_type(out, "BUY")

        assert fee.parent_ref and fee.parent_ref == buy.ref, f"the commission should name the BUY: parent_ref={fee.parent_ref!r}, ref={buy.ref!r}"
        assert fee.asset_id == buy.asset_id

    def test_a_commission_whose_order_has_two_trades_stays_free(self, tmp_path: Path):
        """Guard: two trades share the reference (the masked ``XXXXXXXXX`` of the sample, or two fills) — two candidates,
        the commission stays free."""
        rows = [_buy("-200.00", "XXXXXXXXX"), _buy("-100.00", "XXXXXXXXX", isin=EIMI, quantity="1"), _commission("-1.50", "XXXXXXXXX")]
        out = _parse(_write(tmp_path, rows))
        assert len(_of_type(out, "BUY")) == 2, f"presence barrier: two trades, got {_types(out)}"

        assert_expected_charge_links(out, "shared reference", linked=[], free=[_key("FEE", ISO_DAY, "-1.50", SWDA)])

    def test_a_commission_whose_order_has_no_trade_stays_free(self, tmp_path: Path):
        """Guard: the only trade of the day and ISIN carries another reference — zero candidates, the commission stays free
        (its twin with the same reference links)."""
        out = _parse(_write(tmp_path, [_buy("-200.00", "ORD-A1"), _commission("-1.50", "ORD-ZZ")]))
        assert len(_of_type(out, "BUY")) == 1, f"presence barrier: one trade, got {_types(out)}"

        assert_expected_charge_links(out, "reference of no trade", linked=[], free=[_key("FEE", ISO_DAY, "-1.50", SWDA)])

    @pytest.mark.parametrize("ref", NO_REFERENCE)
    def test_a_commission_without_a_reference_stays_free(self, ref: Optional[str], tmp_path: Path):
        """Guard: no reference on the commission, one trade of the same day and ISIN whose reference is blank too — a blank
        is no key, the commission stays free."""
        out = _parse(_write(tmp_path, [_buy("-200.00", ref), _commission("-1.50", ref)]))
        assert len(_of_type(out, "BUY")) == 1, f"presence barrier: one trade, got {_types(out)}"

        assert_expected_charge_links(out, "no reference", linked=[], free=[_key("FEE", ISO_DAY, "-1.50", SWDA)])

    # -- «Rit. etf» → the SELL of its order ----------------------------------------------------------------------------

    def test_a_sell_with_its_commission_and_its_capital_gain_withholding(self, tmp_path: Path):
        """RED before P3: one order, one SELL, one commission and one «Rit. etf» — both name the SELL; another order of the
        day (a BUY with its commission) keeps its own link."""
        rows = [_sell("210.00", "ORD-S1"), _commission("-1.50", "ORD-S1"), _rit_etf("-2.60", "ORD-S1"), _buy("-100.00", "ORD-B1", isin=EIMI, quantity="1"), _commission("-1.00", "ORD-B1", isin=EIMI)]
        out = _parse(_write(tmp_path, rows))

        sell = _key("SELL", ISO_DAY, "210.00", SWDA)
        linked = [
            (_key("FEE", ISO_DAY, "-1.50", SWDA), sell),
            (_key("TAX", ISO_DAY, "-2.60", SWDA), sell),
            (_key("FEE", ISO_DAY, "-1.00", EIMI), _key("BUY", ISO_DAY, "-100.00", EIMI)),
        ]
        assert_expected_charge_links(out, "sell with commission and withholding", linked=linked, free=[])

    def test_a_capital_gain_withholding_above_its_sell_names_it(self, tmp_path: Path):
        """RED before P3: the withholding is written before its SELL; linked, and the output keeps the file's order."""
        out = _parse(_write(tmp_path, [_rit_etf("-2.60", "ORD-S1"), _sell("210.00", "ORD-S1")]))
        assert _types(out) == ["TAX", "SELL"], f"the output keeps the file's order, got {_types(out)}"

        assert_expected_charge_links(out, "withholding above its sell", linked=[(_key("TAX", ISO_DAY, "-2.60", SWDA), _key("SELL", ISO_DAY, "210.00", SWDA))], free=[])

    def test_a_capital_gain_withholding_whose_order_is_a_buy_stays_free(self, tmp_path: Path):
        """Guard (contract §7: «Rit. etf» → the SELL): the reference names one BUY and no SELL — zero candidates, free."""
        out = _parse(_write(tmp_path, [_buy("-200.00", "ORD-A1"), _rit_etf("-2.60", "ORD-A1")]))
        assert len(_of_type(out, "BUY")) == 1, f"presence barrier: one BUY, got {_types(out)}"

        assert_expected_charge_links(out, "withholding on a buy order", linked=[], free=[_key("TAX", ISO_DAY, "-2.60", SWDA)])

    def test_a_capital_gain_withholding_with_two_sells_of_its_order_stays_free(self, tmp_path: Path):
        """Guard: two SELLs share the reference — two candidates, the withholding stays free."""
        rows = [_sell("210.00", "ORD-S1"), _sell("105.00", "ORD-S1", quantity="1"), _rit_etf("-2.60", "ORD-S1")]
        out = _parse(_write(tmp_path, rows))
        assert len(_of_type(out, "SELL")) == 2, f"presence barrier: two SELLs, got {_types(out)}"

        assert_expected_charge_links(out, "two sells, one reference", linked=[], free=[_key("TAX", ISO_DAY, "-2.60", SWDA)])

    # -- the Tobin tax: by reference when the row carries one ------------------------------------------------------------

    def test_a_tobin_tax_with_a_reference_names_its_trade(self, tmp_path: Path):
        """RED before P3: a Tobin tax with the reference of one BUY names it."""
        out = _parse(_write(tmp_path, [_buy("-200.00", "ORD-A1"), _commission("-1.50", "ORD-A1"), _tobin("-0.20", "ORD-A1")]))

        buy = _key("BUY", ISO_DAY, "-200.00", SWDA)
        assert_expected_charge_links(out, "tobin with reference", linked=[(_key("FEE", ISO_DAY, "-1.50", SWDA), buy), (_key("TAX", ISO_DAY, "-0.20", SWDA), buy)], free=[])

    @pytest.mark.parametrize("ref", NO_REFERENCE)
    def test_a_tobin_tax_without_a_reference_stays_free(self, ref: Optional[str], tmp_path: Path):
        """RED before P3 for the commission, guard for the tax: the Tobin tax carries no reference — it stays free even with
        the one trade of its day and ISIN beside it, while the commission of that trade links."""
        out = _parse(_write(tmp_path, [_buy("-200.00", "ORD-A1"), _commission("-1.50", "ORD-A1"), _tobin("-0.20", ref)]))

        linked = [(_key("FEE", ISO_DAY, "-1.50", SWDA), _key("BUY", ISO_DAY, "-200.00", SWDA))]
        assert_expected_charge_links(out, "tobin without reference", linked=linked, free=[_key("TAX", ISO_DAY, "-0.20", SWDA)])

    # -- «Rit.cedola obb.» → the «Cedola obb.» of its operation date and ISIN ----------------------------------------------

    def test_a_coupon_withholding_names_its_coupon_not_the_row_of_its_protocol(self, tmp_path: Path):
        """RED before P3: the withholding and its coupon have different protocols (as on the real statements); a coupon of
        another bond shares the withholding's protocol — the key is operation date + ISIN, never the protocol."""
        rows = [
            _coupon("Cedola obb.", "24.38", protocol="P-1001"),
            _coupon("Cedola obb.", "71.25", isin=ALPER, protocol="P-1002"),
            _coupon("Rit.cedola obb.", "-3.05", protocol="P-1002"),
        ]
        out = _parse(_write(tmp_path, rows))

        linked = [(_key("TAX", ISO_DAY, "-3.05", BTP_VALORE), _key("INTEREST", ISO_DAY, "24.38", BTP_VALORE))]
        assert_expected_charge_links(out, "coupon pair", linked=linked, free=[])

    def test_a_coupon_withholding_above_its_coupon_names_it(self, tmp_path: Path):
        """RED before P3: the withholding is written before its coupon; linked, the output keeps the file's order."""
        out = _parse(_write(tmp_path, [_coupon("Rit.cedola obb.", "-3.05"), _coupon("Cedola obb.", "24.38")]))
        assert _types(out) == ["TAX", "INTEREST"], f"the output keeps the file's order, got {_types(out)}"

        assert_expected_charge_links(out, "withholding above its coupon", linked=[(_key("TAX", ISO_DAY, "-3.05", BTP_VALORE), _key("INTEREST", ISO_DAY, "24.38", BTP_VALORE))], free=[])

    def test_the_key_is_the_operation_date_not_the_value_date(self, tmp_path: Path):
        """RED before P3: coupon and withholding share the operation date, not the value date (the plugin dates a row by
        «Data operazione», W-B88) — linked."""
        rows = [_coupon("Cedola obb.", "24.38", value_day="17-10-2025"), _coupon("Rit.cedola obb.", "-3.05", value_day="18-10-2025")]
        out = _parse(_write(tmp_path, rows))

        assert_expected_charge_links(out, "same operation date", linked=[(_key("TAX", ISO_DAY, "-3.05", BTP_VALORE), _key("INTEREST", ISO_DAY, "24.38", BTP_VALORE))], free=[])

    def test_two_coupons_of_one_bond_on_one_day_leave_the_withholding_free(self, tmp_path: Path):
        """Guard: two coupons of the same ISIN on the same operation date — two candidates, the withholding stays free."""
        rows = [_coupon("Cedola obb.", "24.38"), _coupon("Cedola obb.", "12.19"), _coupon("Rit.cedola obb.", "-3.05")]
        out = _parse(_write(tmp_path, rows))
        assert len(_of_type(out, "INTEREST")) == 2, f"presence barrier: two coupons, got {_types(out)}"

        assert_expected_charge_links(out, "two coupons, one day", linked=[], free=[_key("TAX", ISO_DAY, "-3.05", BTP_VALORE)])

    @pytest.mark.parametrize(
        "coupon",
        [
            pytest.param(_coupon("Cedola obb.", "24.38", day="14-10-2025", value_day=DAY), id="another-operation-date-same-value-date"),
            pytest.param(_coupon("Cedola obb.", "24.38", isin=ALPER), id="another-isin"),
        ],
    )
    def test_a_coupon_withholding_without_its_coupon_stays_free(self, coupon: Row, tmp_path: Path):
        """Guard: the one coupon differs from the withholding in its operation date (even with the same value date) or in
        its ISIN — zero candidates, the withholding stays free."""
        out = _parse(_write(tmp_path, [coupon, _coupon("Rit.cedola obb.", "-3.05")]))
        assert len(_of_type(out, "INTEREST")) == 1, f"presence barrier: one coupon, got {_types(out)}"

        assert_expected_charge_links(out, "no coupon of its date and ISIN", linked=[], free=[_key("TAX", ISO_DAY, "-3.05", BTP_VALORE)])

    # -- «Rit.provento etf» → a TAX, the «Provento etf» of its date and ISIN -----------------------------------------------

    def test_an_etf_income_withholding_is_a_tax_naming_its_income(self, tmp_path: Path):
        """RED before P3: «Rit.provento etf» is a negative TAX and names the «Provento etf» of its date and ISIN; the
        income of another ETF on the same day is not a candidate."""
        rows = [_income("Provento etf", "20.95"), _income("Rit.provento etf", "-3.57"), _income("Provento etf", "10.94", isin=CNYB)]
        out = _parse(_write(tmp_path, rows))
        assert _types(out) == ["DIVIDEND", "TAX", "DIVIDEND"], f"«Rit.provento etf» is a TAX, got {_types(out)}"

        assert_expected_charge_links(out, "etf income pair", linked=[(_key("TAX", ISO_DAY, "-3.57", IEMB), _key("DIVIDEND", ISO_DAY, "20.95", IEMB))], free=[])

    def test_an_etf_income_withholding_with_two_incomes_stays_a_free_tax(self, tmp_path: Path):
        """RED before P3 for the type: two «Provento etf» of the same ISIN and day — two candidates, the withholding stays
        free, and is still a negative TAX."""
        rows = [_income("Provento etf", "20.95"), _income("Provento etf", "5.00"), _income("Rit.provento etf", "-3.57")]
        out = _parse(_write(tmp_path, rows))
        assert _types(out)[:2] == ["DIVIDEND", "DIVIDEND"], f"presence barrier: two incomes, got {_types(out)}"

        assert _types(out)[2] == "TAX", f"«Rit.provento etf» is a TAX, got {_types(out)}"
        assert_expected_charge_links(out, "two incomes", linked=[], free=[_key("TAX", ISO_DAY, "-3.57", IEMB)])

    # -- any «Rit.» without a reference: the one DIVIDEND or INTEREST of its date and ISIN (rule (b), 21/11) ----------

    @pytest.mark.parametrize(
        ("withholding", "income"),
        [
            pytest.param("Rit. dividendi", "Dividendi", id="rit-dividendi"),
            pytest.param("Rit.dividendo azioni", "Dividendi", id="rit-dividendo-azioni"),
            pytest.param("Rit. coupon certif.", "Coupon certif.", id="rit-coupon-certif"),
        ],
    )
    def test_an_invented_rit_income_label_is_a_negative_tax_naming_its_one_income(self, withholding: str, income: str, tmp_path: Path):
        """RED before rule (b). «rit.» comes before «provento», «dividendi», «dividendo» and «coupon» in the type map, so any
        «Rit.» label with an income word is a negative TAX, never a positive DIVIDEND. Without an order reference but with
        an ISIN, its candidates are the DIVIDEND and INTEREST rows of its operation date and ISIN: here exactly one, so it
        names it. The labels are invented (today's statements only have «Rit. etf», «Rit.cedola obb.» and «Rit.provento
        etf»)."""
        out = _parse(_write(tmp_path, [_income(income, "20.95"), _income(withholding, "-3.57")]))
        assert len(out.transactions) == 2, f"presence barrier: both rows imported, got {_types(out)}"
        parent, tax = out.transactions

        assert (parent.type.value, parent.cash.amount if parent.cash else None) == ("DIVIDEND", Decimal("20.95")), f"the income «{income}» stays a positive DIVIDEND"
        assert (tax.type.value, tax.cash.amount if tax.cash else None) == ("TAX", Decimal("-3.57")), f"«{withholding}» is a negative TAX, got {tax.type.value} {tax.cash}"
        assert_expected_charge_links(out, withholding, linked=[(_key("TAX", ISO_DAY, "-3.57", IEMB), _key("DIVIDEND", ISO_DAY, "20.95", IEMB))], free=[])

    def test_a_rit_label_with_two_incomes_of_its_day_and_isin_stays_free(self, tmp_path: Path):
        """Guard (rule (b)): two DIVIDENDs of the withholding's operation date and ISIN — two candidates, free."""
        rows = [_income("Dividendi", "20.95"), _income("Dividendi", "5.00"), _income("Rit. dividendi", "-3.57")]
        out = _parse(_write(tmp_path, rows))
        assert _types(out) == ["DIVIDEND", "DIVIDEND", "TAX"], f"presence barrier: two incomes and the withholding, got {_types(out)}"

        assert_expected_charge_links(out, "two incomes", linked=[], free=[_key("TAX", ISO_DAY, "-3.57", IEMB)])

    @pytest.mark.parametrize(
        "income",
        [
            pytest.param(_income("Dividendi", "20.95", day="14-10-2025"), id="another-day"),
            pytest.param(_income("Dividendi", "20.95", isin=CNYB), id="another-isin"),
        ],
    )
    def test_a_rit_label_without_an_income_of_its_day_and_isin_stays_free(self, income: Row, tmp_path: Path):
        """Guard (rule (b)): the one income differs in its operation date or its ISIN — zero candidates, free."""
        out = _parse(_write(tmp_path, [income, _income("Rit. dividendi", "-3.57")]))
        assert _types(out) == ["DIVIDEND", "TAX"], f"presence barrier: one income and the withholding, got {_types(out)}"

        assert_expected_charge_links(out, "no income of its day and ISIN", linked=[], free=[_key("TAX", ISO_DAY, "-3.57", IEMB)])

    def test_a_rit_label_with_a_dividend_and_an_interest_of_its_day_stays_free(self, tmp_path: Path):
        """Guard (rule (b)): a DIVIDEND and an INTEREST of the same operation date and ISIN are both candidates — two, free."""
        rows = [_income("Dividendi", "20.95"), _coupon("Cedola obb.", "24.38", isin=IEMB), _income("Rit. dividendi", "-3.57")]
        out = _parse(_write(tmp_path, rows))
        assert _types(out) == ["DIVIDEND", "INTEREST", "TAX"], f"presence barrier: a dividend, an interest and the withholding, got {_types(out)}"

        assert_expected_charge_links(out, "dividend and interest", linked=[], free=[_key("TAX", ISO_DAY, "-3.57", IEMB)])

    def test_a_coupon_withholding_with_a_dividend_and_an_interest_of_its_day_stays_free(self, tmp_path: Path):
        """RED before rule (b): «Rit.cedola obb.» is a case of the same rule — a DIVIDEND and an INTEREST of its operation
        date and ISIN are two candidates, so it stays free (1.2.0 looks at INTEREST rows only and links it)."""
        rows = [_coupon("Cedola obb.", "24.38"), _income("Dividendi", "20.95", isin=BTP_VALORE), _coupon("Rit.cedola obb.", "-3.05")]
        out = _parse(_write(tmp_path, rows))
        assert _types(out) == ["INTEREST", "DIVIDEND", "TAX"], f"presence barrier: an interest, a dividend and the withholding, got {_types(out)}"

        assert_expected_charge_links(out, "coupon withholding, dividend and interest", linked=[], free=[_key("TAX", ISO_DAY, "-3.05", BTP_VALORE)])

    @pytest.mark.parametrize("income", ["Provento etf", "Dividendi", "Coupon certif."])
    def test_an_income_label_without_rit_stays_a_positive_dividend(self, income: str, tmp_path: Path):
        """Guard (control of the test above): an income label without «Rit.» is a positive DIVIDEND, also when Directa
        writes its amount negative (the sign flip of DIVIDEND/INTEREST)."""
        out = _parse(_write(tmp_path, [_income(income, "20.95"), _income(income, "-5.00", isin=CNYB)]))

        assert [(tx.type.value, tx.cash.amount if tx.cash else None) for tx in out.transactions] == [("DIVIDEND", Decimal("20.95")), ("DIVIDEND", Decimal("5.00"))]

    # -- account charges --------------------------------------------------------------------------------------------------

    def test_account_charges_stay_free(self, tmp_path: Path):
        """Guard: «Bollo portafoglio titoli» (an account charge) and «Ritenuta su plusvalenza» (no security, no reference)
        stay free beside a trade with its commission."""
        rows = [
            _buy("-200.00", "ORD-A1"),
            Row("Bollo portafoglio titoli", "-8.40", ref="              "),
            Row("Ritenuta su plusvalenza", "-2.86", ref="              "),
        ]
        out = _parse(_write(tmp_path, rows))
        assert len(_of_type(out, "TAX")) == 2, f"presence barrier: two account taxes, got {_types(out)}"

        assert_expected_charge_links(out, "account charges", linked=[], free=[_key("TAX", ISO_DAY, "-8.40", None), _key("TAX", ISO_DAY, "-2.86", None)])

    # -- one mixed statement: the order of the output, the structure ------------------------------------------------------

    MIXED = [
        _commission("-1.50", "ORD-S1"),
        _sell("210.00", "ORD-S1"),
        _rit_etf("-2.60", "ORD-S1"),
        _coupon("Rit.cedola obb.", "-3.05", protocol="P-2"),
        _coupon("Cedola obb.", "24.38", protocol="P-1"),
        _income("Provento etf", "20.95"),
        _income("Rit.provento etf", "-3.57"),
        _tobin("-0.20", "              "),
        Row("Bollo portafoglio titoli", "-8.40", ref="              "),
        _buy("-100.00", "ORD-B1", isin=EIMI, quantity="1"),
        _commission("-1.00", "ORD-B1", isin=EIMI),
    ]

    def test_a_mixed_statement_keeps_the_order_of_the_file(self, tmp_path: Path):
        """Guard (green today, must stay): one row per line, in the file's order — the links never move a row. The
        «Rit.provento etf» line is compared by its amount's size and its security, its type being the one change of P3."""
        out = _parse(_write(tmp_path, self.MIXED))

        got = [(abs(tx.cash.amount) if tx.cash else None, out.extracted_assets[tx.asset_id].extracted_isin if tx.asset_id is not None else None) for tx in out.transactions]
        expected = [(abs(Decimal(row.amount)), row.isin or None) for row in self.MIXED]
        assert got == expected

    def test_a_mixed_statement_links_every_charge(self, tmp_path: Path):
        """RED before P3: the mixed statement, exhaustive."""
        out = _parse(_write(tmp_path, self.MIXED))

        sell = _key("SELL", ISO_DAY, "210.00", SWDA)
        linked = [
            (_key("FEE", ISO_DAY, "-1.50", SWDA), sell),
            (_key("TAX", ISO_DAY, "-2.60", SWDA), sell),
            (_key("TAX", ISO_DAY, "-3.05", BTP_VALORE), _key("INTEREST", ISO_DAY, "24.38", BTP_VALORE)),
            (_key("TAX", ISO_DAY, "-3.57", IEMB), _key("DIVIDEND", ISO_DAY, "20.95", IEMB)),
            (_key("FEE", ISO_DAY, "-1.00", EIMI), _key("BUY", ISO_DAY, "-100.00", EIMI)),
        ]
        free = [_key("TAX", ISO_DAY, "-0.20", SWDA), _key("TAX", ISO_DAY, "-8.40", None)]
        assert_expected_charge_links(out, "mixed statement", linked=linked, free=free)
        assert_charge_link_structure(out, "mixed statement")

    # -- the XLSX variant ---------------------------------------------------------------------------------------------------

    def test_the_xlsx_variant_links_by_reference_too(self, tmp_path: Path):
        """RED before P3: the same keys through the XLSX reader (native number cells): a commission and a «Rit. etf» name
        their SELL, a coupon withholding its coupon."""
        rows = [_sell("210.00", "ORD-S1"), _commission("-1.50", "ORD-S1"), _rit_etf("-2.60", "ORD-S1"), _coupon("Cedola obb.", "24.38"), _coupon("Rit.cedola obb.", "-3.05")]
        out = _parse(_write_xlsx(tmp_path, rows))

        sell = _key("SELL", ISO_DAY, "210.00", SWDA)
        linked = [
            (_key("FEE", ISO_DAY, "-1.50", SWDA), sell),
            (_key("TAX", ISO_DAY, "-2.60", SWDA), sell),
            (_key("TAX", ISO_DAY, "-3.05", BTP_VALORE), _key("INTEREST", ISO_DAY, "24.38", BTP_VALORE)),
        ]
        assert_expected_charge_links(out, "xlsx", linked=linked, free=[])


def test_fixture_guard_invented_rows_read_as_intended(tmp_path: Path):
    """Fixture guard (this file's writer, not the plugin): the invented CSV is recognised by Directa and every row becomes
    one transaction of the expected type, today already («Rit.provento etf» aside, the P3 change)."""
    path = _write(tmp_path, TestLinkedChargesInvented.MIXED)
    assert _plugin().can_parse(path)
    out = _parse(path)

    assert len(out.transactions) == len(TestLinkedChargesInvented.MIXED)
    expected = ["FEE", "SELL", "TAX", "TAX", "INTEREST", "DIVIDEND", None, "TAX", "TAX", "BUY", "FEE"]
    got = [tx.type.value for tx in out.transactions]
    assert [g if e is not None else None for g, e in zip(got, expected, strict=True)] == expected
