"""
Test Suite: the Investimental plugin — ``broker_investimental``: its linked charges (project 66, wave P4a) and the
executed quantity of an order (lane 66, lot INV-1)

The rest of Investimental (detection, the parse of its sample) is pinned by the suite parametrized over every plugin, ``test_brim_providers.py``. This module pins
what wave P4a adds, from the P2 contract (§2, §8) and the decisions D10/D10b of 16/11 (``domande-FEE.md``, «Plugin per
plugin», «Regole che valgono per ogni plugin»):

- the ``Fee`` of the row the plugin selects for an executed order names the trade it emits for that row as its parent
  (``parent_ref`` = its ``ref``), with its asset and its broker. The fee is always in the account's currency, like the
  trade: there is no cross-currency case;
- the plugin version goes up.

**The sample emits no charge** (doubt 4 of the census): the plugin reads the fee of the last row of each order that is
not deleted or rejected, and in the sample that row is always the final «Fil» with ``Fee`` 0. The real fee is lot INV-2.
Until then (FEE consultant, 23/11, decision x) the FEE is emitted only when the order's last row is a closing fill
(executed and ``Inactive``): an order closed by «OOT»/«Exp»/«Can» after a partial fill carries, on that last row, the
commission of the part NOT executed, so it gives no FEE. A selected row with a ``Fee`` above 0 never occurs in the sample,
so the link is proved in ``tmp_path``, never in the repository's sample: on INVENTED orders (a closing «Fil» with
``Value`` 0, as every closing row of the sample, and a Fee). The sample's own order 21368 cut after its last partial «Fil»
(an «Active» fill row with Fee 43.06) now gives no FEE. No simple input makes an Investimental trade fail the validation
(the plugin skips an order with no volume or no value before creating it): the refused-parent path has no test here.

**INV-1, «a wrong quantity is wrong data»** (developer decision). The file is an order-update log: each row says how
much of the order is *still open*, not how much was executed. The rule, verified on the ten orders of the sample: the
rows of an order in time order, without the deleted/rejected requests; for each executed row (``Update Type`` «Fil» or
a ``Last Trade ID`` not 0), relative to the row before it (any kind, «Chg» included), the executed quantity is the
``Volume`` before minus the row's (the closing «Inactive» row: its own ``Volume``) and the executed amount the ``Value``
before minus the row's. One transaction per order, the sum of the fills, dated on the last fill. The warnings this lot
adds are pinned by a minimal keyword beside ``Order <id>``:

- quantity × (row before's) price off the amount by more than 0.01 → the order is emitted, a warning with «check»;
- fills on different days → one transaction on the last fill's date, a warning naming the first and the last fill day;
- total executed quantity 0 → skipped, the warning «no executed fill» (today's text);
- the estimate of a first row that is already a fill with ``Value`` 0 keeps today's «estimated cash as Price * Volume».

On the sample, orders 13268 (SELL 210, not 64) and 21368 (BUY 263, not 189) change; the six other executed orders keep
their quantity and amount, and no executed order of the sample is warned about any more (their amount comes from the
row before the closing fill, no estimate).

The snapshot of the previous version (``brim_previous_outputs/broker_investimental/investimental-export.json``) was
taken at plugin 1.0.0 (HEAD a2e85db13); 1.1.0 (P4a) emitted the same rows besides the links, so it stays the previous
output of INV-1 and is never re-taken. Over it, the reimport recognises every row but the two changed orders (the Danske
P2c criterion, inverted with ``sample_reimport_report``).

Red before INV-1: the two orders of the sample, the sample's warnings, the invented orders (expiry after a partial fill,
mismatch, two days, a rejected request between fills, no executed quantity), the cut order 21368, the snapshot
comparison, the reimport split, the version 1.2.0. Green before and after (guards): the charge on the invented orders,
the structure, the six unchanged orders, a first row that is already a fill.

**INV-1b, an order whose start the file does not show** (FEE consultant, 23/11). Every order of the sample starts with
a row ``Update Type`` «New». An executed order with no «New» row among its rows (deleted/rejected requests excluded)
started before the file: the open volume before its first visible row is unknown. Never a silent wrong number (order
21368 without its «New» row: never 398). An order whose only execution is an ``Active`` first row has nothing
computable: no trade, a warning «no executed fill».

**INV-1c, choice (a)** (FEE consultant, 24/11, replacing the INV-1b blocker on ``quantity``: the correction step could not
fix the amount, and after «Apply» the row reached the Bulk unsigned). Such an order — also when only its closing row is
visible — is **skipped**: no trade, no FEE, and one ``BRIMNotice`` ``severity`` «warning», ``code``
«investimental_order_start_missing», ``context`` with ``order``, ``date`` (ISO, the last fill), ``side``, ``symbol``,
``price`` (the last fill row's), ``quantity`` and ``amount`` (the visible part, plain decimal strings: ``199``,
``15114.05``) and ``currency``; ``evidence`` one table of the order's rows the file shows; a message naming the order
and sending the user to the statement to enter it by hand. No field todo, ever.

Red before INV-1b: the Active-only order and the two FEE cases (the cut 21368, the expiry after a partial fill with a
Fee on its «OOT» row). Red before INV-1c: every order without its start (21368 without «New» or with its closing row
only, the two «first row already a fill» cases, a deleted «New» request, a fee on an order without «New»).

**INV-1d** (FEE consultant, 24/11). An order whose only execution is an ``Active`` first row is an executed order
without its start too: the same notice, not «no executed fill», with ``quantity`` and ``amount`` «0», ``price`` and
``date`` of that row, and the new ``context`` key ``visible`` «no» (nothing executed is visible); every other order
without its start has ``visible`` «yes». An order skipped for its missing start is not «invalid»: it is counted in a
summary of its own, «Summary: skipped N orders without their start», and never in «skipped N invalid rows/orders».
Red before INV-1d: the Active-only order, ``visible`` on every notice, the summary.

The reimport opens a private in-memory SQLite per test and disposes it: no server, no shared database.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pytest

from backend.app.schemas.brim import BRIMExtractedAssetInfo, BRIMParseOutput
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.test_scripts.brim_charge_links import (
    RowKey,
    assert_charge_link_structure,
    assert_expected_charge_links,
    changes_besides_links,
    load_previous_snapshot,
    sample_reimport_report,
    version_tuple,
)
from backend.test_scripts.brim_samples import SampleDir

PLUGIN_CODE = "broker_investimental"
SAMPLE_DIR = SampleDir()
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7


def _row(tx_type: str, day: str, amount: str, symbol: str) -> RowKey:
    """A row of the output: the account of the samples is in RON; the file has tickers, no ISIN."""
    return (tx_type, day, amount, "RON", symbol)


#: Per sample: (linked (charge, parent), free charges). Every FEE/TAX of the output must be in one of the two.
#: The sample: eight executed orders, eight trades, no charge (doubt 4, see the module docstring).
EXPECTED: Dict[str, Tuple[List[Tuple[RowKey, RowKey]], List[RowKey]]] = {
    "investimental-export.csv": ([], []),
}
SAMPLES = tuple(EXPECTED)

_HEADER = (
    "Order ID,Order Number,Side,Exchange,Symbol,Market,Price,Volume,Disclosed,Value,Fee,Term,Validity,Trigger Type,Trigger Price,"
    "Settlement Term,Settlement Date,Settlement Type,Short Sell,Account ID,Account Name,Last Trade ID,Last Trade Ticket,Status,"
    "Initiated By,Updated By,Update Type,Update Time,Request ID,Request Type,Request Status"
)


def _order_row(order_id: int, side: str, symbol: str, price: str, volume: int, value: str, fee: str, trade_id: int, status: str, update: str, time: str, request_status: str = "") -> str:
    """One INVENTED order-log row (the sample's columns; account «[RON]»). ``request_status`` («Deleted», «Rejected»)
    makes it a change request, as the sample writes one (``Request ID``, ``Request Type`` «Change»)."""
    request = f"{order_id}9,Change,{request_status}" if request_status else ",,"
    return f"{order_id},5{order_id},{side},BVB,{symbol},REGS,{price},{volume},,{value},{fee},Day,,None,,T+2,,Net,No,AC000001,TEST ACCOUNT [RON]," f"{trade_id},{trade_id},{status},AC000001,AC000001,{update},{time},{request}"


# INVENTED orders whose closing «Fil» row carries a Fee: the shape the sample never has. Its Value is 0, as every closing
# row of the sample (nothing is left open): before INV-1 the plugin estimates the amount as Price * Volume, after it the
# amount is the Value of the row before — 1000 and 800 either way, so this case is green before and after.
_INVENTED = [
    _order_row(90001, "Buy", "TVBETETF", "25.000000", 40, "1000.000000", "4.50", 0, "Active", "New", "2024-09-02 10:00:00"),
    _order_row(90001, "Buy", "TVBETETF", "25.000000", 40, "0.000000", "4.50", 777, "Inactive", "Fil", "2024-09-02 10:05:00"),
    _order_row(90002, "Sell", "ICBETNETF", "80.000000", 10, "800.000000", "3.90", 0, "Active", "New", "2024-09-03 10:00:00"),
    _order_row(90002, "Sell", "ICBETNETF", "80.000000", 10, "0.000000", "3.90", 778, "Inactive", "Fil", "2024-09-03 10:05:00"),
]
_INVENTED_LINKED: List[Tuple[RowKey, RowKey]] = [
    (_row("FEE", "2024-09-02", "-4.50", "TVBETETF"), _row("BUY", "2024-09-02", "-1000", "TVBETETF")),
    (_row("FEE", "2024-09-03", "-3.90", "ICBETNETF"), _row("SELL", "2024-09-03", "800", "ICBETNETF")),
]
_INVENTED_TYPES = ["BUY", "FEE", "SELL", "FEE"]

#: Order 21368 of the sample, cut after its last partial «Fil» (the final «Inactive» row dropped): the only shape seen in
#: the sample's own rows where the last row carries a Fee (43.06). INV-1: the BUY is the executed part of the cut order,
#: three fills of 64 + 5 + 5 = 74 for 19974.85 − 14354.55 = 5620.30 (before INV-1 it was the 189 still open, −14354.55).
#: Decision (x) of 23/11: its last row is an «Active» fill, not a closing one, so no FEE (before: FEE −43.06 linked).
_CUT_ORDER = "21368"
_CUT_TRADE_AMOUNT = Decimal("-5620.30")


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, rows: Sequence[str]) -> Path:
    path = tmp_path / "investimental-linked.csv"
    path.write_text("\n".join([_HEADER, *rows]) + "\n", encoding="utf-8")
    return path


def _parse_invented(tmp_path: Path):
    """The invented file, with its presence barrier: no refused row, and the types in order (green before and after).
    Both orders start with «New» and close with a fill: no field todo, and their Fee stays a FEE (decision x)."""
    out = _plugin().parse(_write(tmp_path, _INVENTED), BROKER_ID)
    assert out.validation_issues == [], out.validation_issues
    assert [tx.type.value for tx in out.transactions] == _INVENTED_TYPES, [tx.type.value for tx in out.transactions]
    assert out.field_todos == [], [(todo.tx_index, todo.field, todo.reason_code) for todo in out.field_todos]
    return out


class TestInvestimentalLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_sample_emits_no_charge(self, sample: str):
        """Guard: the sample's output has eight trades and no charge (doubt 4). Decision (x) of 23/11: until INV-2 a FEE
        is emitted only when the order's last row is a closing fill (executed, ``Inactive``) — and on such rows the export
        writes ``Fee`` 0, so in practice the plugin emits no FEE until INV-2 reads the real commission."""
        linked, free = EXPECTED[sample]
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert [tx.type.value for tx in out.transactions].count("FEE") == 0, [tx.type.value for tx in out.transactions]
        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{sample}]", linked=linked, free=free)

    def test_the_fee_of_an_order_names_its_trade(self, tmp_path: Path):
        """RED before P4a. Invented orders: the Fee of the selected row of a Buy and of a Sell names the trade of that order
        (exhaustive)."""
        out = _parse_invented(tmp_path)

        assert_expected_charge_links(out, "invented orders", linked=_INVENTED_LINKED, free=[])

    def test_a_partial_fill_of_the_sample_that_does_not_close_the_order_gives_no_fee(self, tmp_path: Path):
        """RED before INV-1b (FEE decision x; today BUY 74 + FEE −43.06 linked to it). The sample's order 21368 written to
        ``tmp_path`` without its final «Inactive Fil» row (the repository's sample is untouched): its last row is an
        «Active» partial fill, whose Fee is the commission of what is still open — no FEE. The BUY stays the executed 74,
        and the order starts with «New»: no field todo."""
        with (SAMPLE_DIR / "investimental-export.csv").open(encoding="utf-8", newline="") as handle:
            lines = handle.read().splitlines()
        rows = [line for line in lines[1:] if line.startswith(f"{_CUT_ORDER},") and ",Inactive," not in line]
        assert len(rows) == 4, f"presence barrier: order {_CUT_ORDER} has 4 rows before its final fill in the sample; {rows}"
        out = _plugin().parse(_write(tmp_path, rows), BROKER_ID)
        assert out.validation_issues == [], out.validation_issues

        assert [tx.type.value for tx in out.transactions] == ["BUY"], [(tx.type.value, str(tx.cash.amount if tx.cash else None)) for tx in out.transactions]
        [tx] = out.transactions
        assert (tx.quantity, tx.cash.amount if tx.cash else None) == (Decimal("74"), _CUT_TRADE_AMOUNT), f"BUY 74 for {_CUT_TRADE_AMOUNT}: got {tx.quantity}, {tx.cash}"
        assert out.field_todos == [], [(todo.tx_index, todo.field, todo.reason_code) for todo in out.field_todos]

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_links_are_well_formed(self, sample: str):
        """Guard: every ``ref`` unique, every ``parent_ref`` names a ``ref`` of the output (vacuous before P4a)."""
        assert_charge_link_structure(_plugin().parse(SAMPLE_DIR / sample, BROKER_ID), f"{PLUGIN_CODE} [{sample}]")

    def test_the_links_of_the_invented_orders_are_well_formed(self, tmp_path: Path):
        """Guard: the structure on the invented orders too (vacuous before P4a)."""
        assert_charge_link_structure(_parse_invented(tmp_path), "invented orders")

    def test_the_version_is_above_the_previous_one(self):
        """RED before P4a: every touched plugin goes up a version (contract §8)."""
        plugin = _plugin()
        for sample in SAMPLES:
            previous = load_previous_snapshot(PLUGIN_CODE, sample, BROKER_ID)
            assert version_tuple(plugin.plugin_version) > version_tuple(previous.plugin_version), f"{PLUGIN_CODE} {plugin.plugin_version}: not above the snapshot's {previous.plugin_version} ({sample})"


# ─── INV-1: the executed quantity of an order ─────────────────────────────────────────────────────────────────────────

#: The version INV-1 bumps to: the output for the same file changes (two orders of the sample).
NEW_VERSION = "1.2.0"
SAMPLE = "investimental-export.csv"


@dataclass(frozen=True)
class Trade:
    """One trade of an output, named by what the file says of it: type, day, symbol; then what INV-1 computes."""

    tx_type: str
    day: str
    symbol: str
    quantity: str
    amount: str


#: Every executed order of the sample, after INV-1 (the two others, 9058 and 12779, expire unexecuted). The amounts are the
#: sums of the fills: 13268 is 271.85 + 1495.175 + 217.52 + 1984.87 + 1740.16, 21368 is 4860.80 + 379.75 + 379.75 + 14354.55.
SAMPLE_TRADES: Dict[str, Trade] = {
    "6750": Trade("BUY", "2024-03-05", "TVBETETF", "20", "-494.90"),
    "9202": Trade("BUY", "2024-04-12", "TVBETETF", "96", "-2489.28"),
    "9359": Trade("BUY", "2024-04-18", "R2704A", "300", "-30000"),
    "10938": Trade("BUY", "2024-05-13", "TVBETETF", "94", "-2480.66"),
    "12753": Trade("BUY", "2024-05-29", "ICBETNETF", "267", "-19904.85"),
    "13268": Trade("SELL", "2024-05-31", "TVBETETF", "-210", "5709.575"),  # before INV-1: −64, +1740.16 (the last chunk)
    "13375": Trade("BUY", "2024-05-31", "ICBETNETF", "77", "-5637.17"),
    "21368": Trade("BUY", "2024-08-05", "ICBETNETF", "263", "-19974.85"),  # before INV-1: 189, −14354.55
}
#: The orders INV-1 changes on the sample; every other executed order keeps the previous version's row.
CHANGED_ORDERS = ("13268", "21368")
#: The orders of the sample that expire unexecuted: the only ones its warnings may name after INV-1.
UNEXECUTED_ORDERS = ("9058", "12779")


def _identifier(assets: Dict[int, BRIMExtractedAssetInfo], asset_id: Optional[int]) -> Optional[str]:
    info = assets.get(asset_id) if asset_id is not None else None
    return info.extracted_symbol if info else None


def _index_of(rows: Sequence[TXCreateItem], assets: Dict[int, BRIMExtractedAssetInfo], trade: Trade) -> int:
    """The position of the one row of ``rows`` with the trade's type, day and symbol (never assumed: found)."""
    found = [index for index, tx in enumerate(rows) if tx.type.value == trade.tx_type and tx.date.isoformat() == trade.day and _identifier(assets, tx.asset_id) == trade.symbol]
    assert len(found) == 1, f"{len(found)} rows are a {trade.tx_type} of {trade.symbol} on {trade.day}: a trade names exactly one row"
    return found[0]


def _the_trade(output: BRIMParseOutput, trade: Trade) -> TXCreateItem:
    return output.transactions[_index_of(output.transactions, output.extracted_assets, trade)]


def _notice_texts(output: BRIMParseOutput) -> List[str]:
    """Every notice of the output as text: its message, then the values of its context (a plugin may move the figures
    there). A plain string the plugin appends becomes a ``BRIMNotice`` whose message is that string."""
    return [" ".join([notice.message, *(str(value) for value in (notice.context or {}).values())]) for notice in output.warnings]


def _warnings_of(output: BRIMParseOutput, order_id: int | str) -> List[str]:
    """The notices that name the order ``order_id`` (``Order <id>``, the plugin's form, the id as a whole word)."""
    pattern = re.compile(rf"\bOrder {order_id}\b")
    return [text for text in _notice_texts(output) if pattern.search(text)]


def _parse_order(tmp_path: Path, name: str, rows: Sequence[str]) -> BRIMParseOutput:
    """An INVENTED file of ``rows`` parsed, with its barrier: no refused row."""
    path = tmp_path / f"investimental-{name}.csv"
    path.write_text("\n".join([_HEADER, *rows]) + "\n", encoding="utf-8")
    out = _plugin().parse(path, BROKER_ID)
    assert out.validation_issues == [], out.validation_issues
    return out


def _assert_one_trade(output: BRIMParseOutput, expected: Trade) -> None:
    """The output is one trade, ``expected`` to the cent (quantity and amount as numbers, never as text)."""
    trades = [tx for tx in output.transactions if tx.type.value in {"BUY", "SELL"}]
    assert len(trades) == 1, f"one order, one trade: {[(tx.type.value, str(tx.date), str(tx.quantity), str(tx.cash.amount if tx.cash else None)) for tx in output.transactions]}"
    [tx] = trades
    got = (tx.type.value, _identifier(output.extracted_assets, tx.asset_id), tx.date.isoformat(), tx.quantity, tx.cash.amount if tx.cash else None, tx.cash.code if tx.cash else None)
    want = (expected.tx_type, expected.symbol, expected.day, Decimal(expected.quantity), Decimal(expected.amount), "RON")
    assert got == want, f"type, symbol, date, quantity, amount, currency: got {got}, expected {want}"


def _is_check_warning(warning: str) -> bool:
    return "check" in warning.lower()


class TestInvestimentalExecutedQuantity:
    """INV-1: an order is the sum of its fills, each the change of what is still open (module docstring)."""

    # -- the sample ---------------------------------------------------------------------------------------------------

    def test_the_sample_gives_one_trade_per_executed_order(self):
        """Guard (green before and after): eight executed orders, eight trades, no other trade."""
        out = _plugin().parse(SAMPLE_DIR / SAMPLE, BROKER_ID)
        assert out.validation_issues == [], out.validation_issues
        trades = [tx for tx in out.transactions if tx.type.value in {"BUY", "SELL"}]
        assert len(trades) == len(SAMPLE_TRADES), f"{len(trades)} trades, one per executed order expected ({len(SAMPLE_TRADES)})"

    def test_the_whole_sample_has_no_field_todo(self):
        """Guard (green before and after INV-1b/1c): every order of the sample starts with «New», so no order is skipped
        for its missing start — no notice «investimental_order_start_missing», no field todo; the numbers stay the ones
        pinned above."""
        out = _plugin().parse(SAMPLE_DIR / SAMPLE, BROKER_ID)
        assert out.transactions, "presence barrier: the sample gives trades"
        assert out.field_todos == [], [(todo.tx_index, todo.field, todo.reason_code) for todo in out.field_todos]
        assert _start_missing_notices(out) == [], f"no order of the sample lacks its start: {_start_missing_notices(out)}"

    @pytest.mark.parametrize("order_id", list(SAMPLE_TRADES), ids=list(SAMPLE_TRADES))
    def test_the_sample_gives_an_executed_order_its_whole_fill(self, order_id: str):
        """RED before INV-1 on 13268 and 21368 (the last chunk only), green on the six others (guards). Exact quantity,
        amount, currency, date and type of each executed order of the sample."""
        expected = SAMPLE_TRADES[order_id]
        out = _plugin().parse(SAMPLE_DIR / SAMPLE, BROKER_ID)
        tx = _the_trade(out, expected)

        got = (tx.quantity, tx.cash.amount if tx.cash else None, tx.cash.code if tx.cash else None)
        assert got == (Decimal(expected.quantity), Decimal(expected.amount), "RON"), f"order {order_id} {expected.tx_type} {expected.symbol} {expected.day}: quantity, amount, currency {got}; expected {expected.quantity}, {expected.amount} RON"

    def test_the_sample_warns_only_about_its_unexecuted_orders(self):
        """RED before INV-1: today every executed order of the sample is warned about («zero Value on final fill;
        estimated cash as Price * Volume»). After it the amount comes from the row before the closing fill: no estimate,
        no mismatch, every order filled on one day (21368's «New» row on 07-26 is no fill: no multi-day warning)."""
        out = _plugin().parse(SAMPLE_DIR / SAMPLE, BROKER_ID)

        named = {order_id: _warnings_of(out, order_id) for order_id in SAMPLE_TRADES}
        assert {order_id: found for order_id, found in named.items() if found} == {}, "an executed order of the sample is warned about"
        assert not [text for text in _notice_texts(out) if "estimated cash" in text], _notice_texts(out)
        for order_id in UNEXECUTED_ORDERS:
            assert _warnings_of(out, order_id), f"presence barrier: the unexecuted order {order_id} is still reported ({_notice_texts(out)})"

    def test_only_the_two_changed_orders_differ_from_the_previous_version(self):
        """RED before INV-1. Against the snapshot of the previous version, the rows of 13268 and 21368 change their
        quantity and cash, and nothing else changes in the whole output (``changes_besides_links``)."""
        previous = load_previous_snapshot(PLUGIN_CODE, SAMPLE, BROKER_ID)
        out = _plugin().parse(SAMPLE_DIR / SAMPLE, BROKER_ID)
        changed = sorted(_index_of(previous.transactions, previous.extracted_assets, SAMPLE_TRADES[order_id]) for order_id in CHANGED_ORDERS)
        assert changed == sorted(_index_of(out.transactions, out.extracted_assets, SAMPLE_TRADES[order_id]) for order_id in CHANGED_ORDERS), "the two orders keep their place in the output"

        problems = changes_besides_links(previous.transactions, out.transactions)
        assert sorted(int(line.split(" ", 1)[0].lstrip("#")) for line in problems if line.startswith("#")) == changed, f"the rows that changed (snapshot HEAD {previous.source_head}):\n  " + "\n  ".join(problems)
        assert len(problems) == len(changed), "\n  ".join(problems)
        for index in changed:
            old = previous.transactions[index].model_dump(mode="json")
            new = out.transactions[index].model_dump(mode="json")
            assert {field for field in old if field not in ("ref", "parent_ref") and old[field] != new[field]} == {"quantity", "cash"}, f"#{index}: {old} → {new}"

    @pytest.mark.asyncio
    async def test_reimport_recognises_every_row_but_the_two_changed_orders(self):
        """RED before INV-1 (P2 contract §2.5, the Danske P2c criterion): over the rows the previous version saved, every
        row is found as a duplicate except the two orders whose quantity and amount changed: the reimport adds those two
        (the expected «delete and reimport»)."""
        report = await sample_reimport_report(_plugin(), SAMPLE)
        output = report.output
        assert output.transactions, "the criterion ran on an empty output"
        changed = frozenset(_index_of(output.transactions, output.extracted_assets, SAMPLE_TRADES[order_id]) for order_id in CHANGED_ORDERS)

        assert sorted(report.unique) == sorted(changed), "the reimport adds exactly the two changed orders"
        assert report.duplicates == frozenset(range(len(output.transactions))) - changed, "every other row is recognised"

    def test_the_version_is_1_2_0(self):
        """RED before INV-1: the output for the same file changes, the plugin goes up to 1.2.0."""
        assert _plugin().plugin_version == NEW_VERSION, f"{PLUGIN_CODE}: plugin_version is {_plugin().plugin_version!r}, expected {NEW_VERSION}"

    # -- INVENTED orders (``tmp_path``, never real data) ---------------------------------------------------------------

    def test_an_order_that_expires_after_a_partial_fill_gives_its_executed_part(self, tmp_path: Path):
        """RED before INV-1 (today: the 60 still open, dated on the expiry), RED again before INV-1b (FEE decision x).
        100 ordered, 40 filled on 09-10, the rest expires at midnight: BUY 40 for 400.00 on the fill's day, and no
        multi-day warning (the expiry is no fill). Each row carries the commission of what is still open, as the sample's
        rows do (4.50 on the 100, 2.70 on the 60): the last row is the «OOT» one, whose 2.70 is the commission of the part
        NOT executed — no FEE (before: FEE −2.70)."""
        out = _parse_order(
            tmp_path,
            "expiry",
            [
                _order_row(91001, "Buy", "INVA", "10.000000", 100, "1000.000000", "4.50", 0, "Active", "New", "2024-09-10 10:00:00"),
                _order_row(91001, "Buy", "INVA", "10.000000", 60, "600.000000", "2.70", 801, "Active", "Fil", "2024-09-10 10:05:00"),
                _order_row(91001, "Buy", "INVA", "10.000000", 60, "600.000000", "2.70", 0, "Inactive", "OOT", "2024-09-11 00:00:12"),
            ],
        )

        _assert_one_trade(out, Trade("BUY", "2024-09-10", "INVA", "40", "-400.00"))
        assert not [warning for warning in _warnings_of(out, 91001) if "2024-09-10" in warning and "2024-09-11" in warning], f"one fill day, no multi-day warning: {_notice_texts(out)}"
        assert [tx.type.value for tx in out.transactions] == ["BUY"], f"no FEE on an order closed by its expiry: {[(tx.type.value, str(tx.cash.amount if tx.cash else None)) for tx in out.transactions]}"
        assert out.field_todos == [], [(todo.tx_index, todo.field, todo.reason_code) for todo in out.field_todos]

    def test_a_mismatch_between_quantity_price_and_amount_is_emitted_with_a_warning(self, tmp_path: Path):
        """RED before INV-1 (today: the estimate 50 × 20 = 1000, warned as an estimate). The row before the closing fill
        holds 990.00 for 50 at 20.00: off by 10 → the order is still emitted, SELL 50 for 990.00, with a warning «check»."""
        out = _parse_order(
            tmp_path,
            "mismatch",
            [
                _order_row(91002, "Sell", "INVB", "20.000000", 50, "990.000000", "0", 0, "Active", "New", "2024-09-20 10:00:00"),
                _order_row(91002, "Sell", "INVB", "20.000000", 50, "0.000000", "0", 821, "Inactive", "Fil", "2024-09-20 10:05:00"),
            ],
        )

        _assert_one_trade(out, Trade("SELL", "2024-09-20", "INVB", "-50", "990.00"))
        assert [warning for warning in _warnings_of(out, 91002) if _is_check_warning(warning)], f"a warning «Order 91002 … check»: {_notice_texts(out)}"

    def test_fills_on_two_days_are_one_trade_on_the_last_fill_with_a_warning(self, tmp_path: Path):
        """RED before INV-1 (today: the 5 still open, dated on the expiry 09-18). 10 filled on 09-16, 15 on 09-17, the rest
        expires on 09-18: BUY 25 for 375.00 on 09-17 (the last fill, not the last row), and a warning naming both days."""
        out = _parse_order(
            tmp_path,
            "two-days",
            [
                _order_row(91003, "Buy", "INVC", "15.000000", 30, "450.000000", "0", 0, "Active", "New", "2024-09-16 09:00:00"),
                _order_row(91003, "Buy", "INVC", "15.000000", 20, "300.000000", "0", 811, "Active", "Fil", "2024-09-16 10:00:00"),
                _order_row(91003, "Buy", "INVC", "15.000000", 5, "75.000000", "0", 812, "Active", "Fil", "2024-09-17 11:00:00"),
                _order_row(91003, "Buy", "INVC", "15.000000", 5, "75.000000", "0", 0, "Inactive", "OOT", "2024-09-18 00:00:12"),
            ],
        )

        _assert_one_trade(out, Trade("BUY", "2024-09-17", "INVC", "25", "-375.00"))
        assert [warning for warning in _warnings_of(out, 91003) if "2024-09-16" in warning and "2024-09-17" in warning], f"a warning «Order 91003 … 2024-09-16 … 2024-09-17»: {_notice_texts(out)}"

    def test_a_rejected_request_between_fills_is_skipped(self, tmp_path: Path):
        """RED before INV-1 (today: the closing 50, estimated). Fills of 30, 20, 50; between the first two a rejected
        change request claims 40 open: were it the row before, the second fill would be −10. BUY 100 for 500.00."""
        out = _parse_order(
            tmp_path,
            "rejected",
            [
                _order_row(91004, "Buy", "INVD", "5.000000", 100, "500.000000", "0", 0, "Active", "New", "2024-09-23 10:00:00"),
                _order_row(91004, "Buy", "INVD", "5.000000", 70, "350.000000", "0", 831, "Active", "Fil", "2024-09-23 10:05:00"),
                _order_row(91004, "Buy", "INVD", "5.000000", 40, "200.000000", "0", 0, "Active", "Chg", "2024-09-23 10:10:00", request_status="Rejected"),
                _order_row(91004, "Buy", "INVD", "5.000000", 50, "250.000000", "0", 832, "Active", "Fil", "2024-09-23 10:15:00"),
                _order_row(91004, "Buy", "INVD", "5.000000", 50, "0.000000", "0", 833, "Inactive", "Fil", "2024-09-23 10:20:00"),
            ],
        )

        _assert_one_trade(out, Trade("BUY", "2024-09-23", "INVD", "100", "-500.00"))
        assert not [warning for warning in _warnings_of(out, 91004) if _is_check_warning(warning)], _notice_texts(out)

    def test_an_order_with_no_executed_quantity_is_skipped(self, tmp_path: Path):
        """RED before INV-1 (today: a BUY of the 10 still open). A «Fil» marker that leaves the open volume unchanged
        executes nothing: the order is skipped as «no executed fill», as today for an order without fills."""
        out = _parse_order(
            tmp_path,
            "nothing-executed",
            [
                _order_row(91005, "Buy", "INVE", "10.000000", 10, "100.000000", "0", 0, "Active", "New", "2024-09-24 10:00:00"),
                _order_row(91005, "Buy", "INVE", "10.000000", 10, "100.000000", "0", 841, "Active", "Fil", "2024-09-24 10:05:00"),
                _order_row(91005, "Buy", "INVE", "10.000000", 10, "100.000000", "0", 0, "Inactive", "OOT", "2024-09-25 00:00:12"),
            ],
        )

        assert out.transactions == [], [(tx.type.value, str(tx.date), str(tx.quantity)) for tx in out.transactions]
        assert [warning for warning in _warnings_of(out, 91005) if "no executed fill" in warning], f"a warning «Order 91005 … no executed fill»: {_notice_texts(out)}"

    def test_a_first_row_that_is_already_a_fill_is_an_order_without_its_start(self, tmp_path: Path):
        """RED before INV-1c (today: BUY 12 for 600.00 with the blocker). The order's only row is its closing fill, with
        a Value: it has no «New» row, its start is not in the file — skipped, no trade, the notice with the visible part
        12 for 600 at 50."""
        rows = [_order_row(91006, "Buy", "INVF", "50.000000", 12, "600.000000", "0", 851, "Inactive", "Fil", "2024-09-26 10:00:00")]
        out = _parse_order(tmp_path, "first-fill", rows)

        assert out.transactions == [], [(tx.type.value, str(tx.date), str(tx.quantity)) for tx in out.transactions]
        _assert_start_missing_notice(out, StartMissing("91006", "2024-09-26", "buy", "INVF", "50", "12", "600"), _shown_rows([_HEADER, *rows], "91006"))

    def test_a_first_row_that_is_already_a_fill_with_no_value_is_an_order_without_its_start(self, tmp_path: Path):
        """RED before INV-1c (today: BUY 8 estimated at 200.00 with the blocker). The order's only row is its closing fill
        with Value 0: no «New» row — skipped, no trade, the notice with the visible part 8 and the estimate Price * Volume
        = 8 × 25 = 200. Whether the estimate warning survives for a skipped order is not decided: not pinned."""
        rows = [_order_row(91007, "Buy", "INVG", "25.000000", 8, "0.000000", "0", 852, "Inactive", "Fil", "2024-09-26 11:00:00")]
        out = _parse_order(tmp_path, "first-fill-estimated", rows)

        assert out.transactions == [], [(tx.type.value, str(tx.date), str(tx.quantity)) for tx in out.transactions]
        _assert_start_missing_notice(out, StartMissing("91007", "2024-09-26", "buy", "INVG", "25", "8", "200"), _shown_rows([_HEADER, *rows], "91007"))


# ─── INV-1b/1c: an order whose start the file does not show ────────────────────────────────────────────────────────────

#: The order of the sample INV-1b cuts: «New» 263 open, fills of 64 (Active), 5, 5, then the closing 189.
_STARTLESS_ORDER = "21368"
#: Its notice without the «New» row: the first visible row (199 open, Active) executed an unknown part; the visible part
#: is 5 + 5 + 189 = 199 for 379.75 + 379.75 + 14354.55 = 15114.05, at the last fill's price 75.95. Never 398.
#: Its notice with the closing row only: 189, today's estimate (no row before, Value 0) 189 × 75.95 = 14354.55.
_NOTICE_CODE = "investimental_order_start_missing"


@dataclass(frozen=True)
class StartMissing:
    """The notice of an order skipped because its start is not in the file (INV-1c): the context the plugin writes,
    figures as plain decimal strings (no trailing zeros)."""

    order: str
    date: str
    side: str
    symbol: str
    price: str
    quantity: str
    amount: str
    currency: str = "RON"
    #: INV-1d: «yes» when the file shows an executed part, «no» when nothing executed is visible (an Active first row).
    visible: str = "yes"


_STARTLESS = StartMissing(_STARTLESS_ORDER, "2024-08-05", "buy", "ICBETNETF", "75.95", "199", "15114.05")
_CLOSING_ONLY = StartMissing(_STARTLESS_ORDER, "2024-08-05", "buy", "ICBETNETF", "75.95", "189", "14354.55")


def _sample_copy(tmp_path: Path, name: str, drop) -> Tuple[Path, List[str], List[str]]:
    """The repository's sample written to ``tmp_path`` without the lines ``drop`` accepts (the sample is untouched):
    the path, the lines written (header first) and the lines dropped."""
    with (SAMPLE_DIR / SAMPLE).open(encoding="utf-8", newline="") as handle:
        lines = handle.read().splitlines()
    kept = [lines[0], *[line for line in lines[1:] if not drop(line)]]
    dropped = [line for line in lines[1:] if drop(line)]
    path = tmp_path / f"investimental-{name}.csv"
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return path, kept, dropped


def _shown_rows(written: Sequence[str], order_id: str) -> List[Tuple[int, str]]:
    """The rows of ``order_id`` in a written file (header first): their 1-based line number and their ``Update Time``."""
    header = next(csv.reader([written[0]]))
    time_column = header.index("Update Time")
    return [(number, next(csv.reader([line]))[time_column]) for number, line in enumerate(written, start=1) if number > 1 and line.startswith(f"{order_id},")]


def _summaries(output: BRIMParseOutput) -> List[str]:
    """The output's summary lines (the plugin's «Summary: …» strings, as notice messages)."""
    return [notice.message for notice in output.warnings if notice.message.startswith("Summary:")]


def _assert_start_missing_summary(output: BRIMParseOutput, count: int) -> None:
    """INV-1d: the orders skipped for their missing start have a summary of their own naming ``count``, and they are
    not counted as invalid — on these files no «invalid» summary at all."""
    summaries = _summaries(output)
    own = [line for line in summaries if "without their start" in line]
    assert len(own) == 1, f"one summary «… without their start» expected: {summaries}"
    assert re.search(rf"\b{count}\b", own[0]), f"the summary names {count} order(s): {own[0]!r}"
    assert [line for line in summaries if "invalid" in line] == [], f"an order without its start is not «invalid»: {summaries}"


def _start_missing_notices(output: BRIMParseOutput) -> List[str]:
    """The orders named by the output's notices with the INV-1c code (empty context → «?»)."""
    return [str((notice.context or {}).get("order", "?")) for notice in output.warnings if notice.code == _NOTICE_CODE]


def _assert_start_missing_notice(output: BRIMParseOutput, expected: StartMissing, shown: Optional[Sequence[Tuple[int, str]]]) -> None:
    """The output carries exactly one INV-1c notice, for ``expected``, and no field todo anywhere.

    Pinned: ``severity`` «warning», ``code``; ``context`` ``order``, ``date`` (ISO), ``side``, ``symbol``, ``currency``,
    ``visible`` (INV-1d) and the figures ``price``, ``quantity``, ``amount`` as the exact plain strings (no trailing
    zeros, no exponent); a
    message naming ``Order <id>`` and the statement; one evidence table whose rows are the order's rows the file shows,
    in file order — each identified by its ``Update Time`` among its cells and by its line number (``row_numbers``).
    ``shown`` None leaves the evidence rows unpinned (one table still required)."""
    todos = [(todo.tx_index, todo.field, todo.severity, todo.reason_code) for todo in output.field_todos]
    assert output.field_todos == [], f"choice (a): the order is skipped, no field todo anywhere: {todos}"
    notices = [notice for notice in output.warnings if notice.code == _NOTICE_CODE]
    assert len(notices) == 1, f"one notice {_NOTICE_CODE!r} expected (order {expected.order}), {len(notices)} found; codes {[notice.code for notice in output.warnings]}"
    notice = notices[0]
    assert notice.severity == "warning", f"severity {notice.severity!r}, «warning» expected"

    context = notice.context or {}
    got = {key: str(context.get(key)) for key in ("order", "date", "side", "symbol", "currency", "visible")}
    want = {"order": expected.order, "date": expected.date, "side": expected.side, "symbol": expected.symbol, "currency": expected.currency, "visible": expected.visible}
    assert got == want, f"context: {context}"
    for key, want in (("price", expected.price), ("quantity", expected.quantity), ("amount", expected.amount)):
        assert isinstance(context.get(key), str), f"context.{key} is a string: {context}"
        assert context[key] == want, f"context.{key} = {context[key]!r}, the plain {want!r} expected (no trailing zeros)"
    assert re.search(rf"\bOrder {expected.order}\b", notice.message), f"the message names the order: {notice.message!r}"
    assert "statement" in notice.message.lower(), f"the message sends the user to the statement: {notice.message!r}"

    assert len(notice.evidence) == 1, f"one evidence table, the order's rows: {notice.evidence}"
    evidence = notice.evidence[0]
    if shown is None:
        return
    assert len(evidence.rows) == len(shown), f"{len(evidence.rows)} evidence rows, the {len(shown)} rows of order {expected.order} the file shows expected: {evidence.rows}"
    assert evidence.row_numbers == [number for number, _ in shown], f"evidence row numbers {evidence.row_numbers}, file lines {[number for number, _ in shown]} expected"
    for cells, (number, time) in zip(evidence.rows, shown, strict=True):
        assert time in cells, f"evidence row for line {number} lacks its Update Time {time}: {cells}"


def _assert_skipped_from_the_sample(output: BRIMParseOutput) -> None:
    """The sample's output without 21368: the seven other orders exactly as before (presence barrier), and no row of
    ICBETNETF on 2024-08-05 (no trade, never 398, no FEE)."""
    trades = [tx for tx in output.transactions if tx.type.value in {"BUY", "SELL"}]
    assert len(trades) == len(SAMPLE_TRADES) - 1, f"{len(trades)} trades: the seven other executed orders expected"
    for order_id, trade in SAMPLE_TRADES.items():
        if order_id != _STARTLESS_ORDER:
            other = _the_trade(output, trade)
            assert (other.quantity, other.cash.amount if other.cash else None) == (Decimal(trade.quantity), Decimal(trade.amount)), f"order {order_id} unchanged"
    cut = [(tx.type.value, str(tx.quantity), str(tx.cash.amount if tx.cash else None)) for tx in output.transactions if tx.date.isoformat() == "2024-08-05" and _identifier(output.extracted_assets, tx.asset_id) == "ICBETNETF"]
    assert cut == [], f"order {_STARTLESS_ORDER} without its start is skipped: no row of ICBETNETF on 2024-08-05, got {cut}"


class TestInvestimentalOrderStartMissing:
    """INV-1c: an executed order without a «New» row is skipped, with one notice naming its visible part."""

    def test_the_sample_without_the_new_row_of_21368_skips_it_with_a_notice(self, tmp_path: Path):
        """RED before INV-1c (today: BUY 199 with the blocker). The whole sample without the «New» row of 21368: the
        whole quantity cannot be read from the file — no trade for the order, never 398; the notice with the visible
        part 199 for 15114.05 at 75.95; the other orders unchanged, no field todo."""
        path, written, dropped = _sample_copy(tmp_path, "start-missing", lambda line: line.startswith(f"{_STARTLESS_ORDER},") and ",New," in line)
        assert len(dropped) == 1, f"presence barrier: order {_STARTLESS_ORDER} has one «New» row in the sample: {dropped}"
        out = _plugin().parse(path, BROKER_ID)
        assert out.validation_issues == [], out.validation_issues

        _assert_skipped_from_the_sample(out)
        _assert_start_missing_notice(out, _STARTLESS, _shown_rows(written, _STARTLESS_ORDER))
        _assert_start_missing_summary(out, 1)

    def test_the_sample_with_only_the_closing_row_of_21368_skips_it_with_a_notice(self, tmp_path: Path):
        """RED before INV-1c (today: BUY 189 estimated with the blocker). The whole sample with only the closing row of
        21368 («Fil», «Inactive», Volume 189, Value 0): skipped, the notice with 189 and the estimate 14354.55."""
        path, written, dropped = _sample_copy(tmp_path, "closing-only", lambda line: line.startswith(f"{_STARTLESS_ORDER},") and ",Inactive," not in line)
        assert len(dropped) == 4, f"presence barrier: order {_STARTLESS_ORDER} has 4 rows before its closing fill in the sample: {dropped}"
        out = _plugin().parse(path, BROKER_ID)
        assert out.validation_issues == [], out.validation_issues

        _assert_skipped_from_the_sample(out)
        _assert_start_missing_notice(out, _CLOSING_ONLY, _shown_rows(written, _STARTLESS_ORDER))

    def test_an_order_whose_only_execution_is_an_active_first_row_gives_nothing(self, tmp_path: Path):
        """RED before INV-1d (INV-1b/1c: «no executed fill»). INVENTED: no «New» row, the first visible row is an
        «Active» fill (6 still open) and the order then expires — an executed order without its start, its execution
        unknown: no trade, no field todo, the INV-1c notice with nothing visible (quantity and amount «0», the row's
        price and date, ``visible`` «no»), no «no executed fill», and the summary of the orders without their start."""
        rows = [
            _order_row(91008, "Buy", "INVH", "10.000000", 6, "60.000000", "1.20", 861, "Active", "Fil", "2024-09-27 10:05:00"),
            _order_row(91008, "Buy", "INVH", "10.000000", 6, "60.000000", "1.20", 0, "Inactive", "OOT", "2024-09-28 00:00:12"),
        ]
        out = _parse_order(tmp_path, "active-first-only", rows)

        assert out.transactions == [], [(tx.type.value, str(tx.date), str(tx.quantity)) for tx in out.transactions]
        _assert_start_missing_notice(out, StartMissing("91008", "2024-09-27", "buy", "INVH", "10", "0", "0", visible="no"), _shown_rows([_HEADER, *rows], "91008"))
        assert [warning for warning in _warnings_of(out, 91008) if "no executed fill" in warning] == [], f"no «no executed fill» for 91008: {_notice_texts(out)}"
        _assert_start_missing_summary(out, 1)
        assert [line for line in _summaries(out) if "without executed fills" in line] == [], f"91008 is counted once, without its start: {_summaries(out)}"

    def test_an_order_without_its_start_gives_neither_trade_nor_fee(self, tmp_path: Path):
        """RED before INV-1c (today: BUY, BUY, FEE with the blocker on the second BUY). INVENTED: a complete order (91009,
        «New» then its closing fill) and then an order without «New» (91010) closed by a fill with a Fee above 0. 91010 is
        skipped with its notice — no trade and no FEE for it; 91009's BUY stays (presence barrier)."""
        rows = [
            _order_row(91009, "Buy", "INVI", "20.000000", 5, "100.000000", "0", 0, "Active", "New", "2024-09-30 10:00:00"),
            _order_row(91009, "Buy", "INVI", "20.000000", 5, "0.000000", "0", 871, "Inactive", "Fil", "2024-09-30 10:05:00"),
            _order_row(91010, "Buy", "INVJ", "50.000000", 12, "600.000000", "2.50", 872, "Inactive", "Fil", "2024-09-30 11:00:00"),
        ]
        out = _parse_order(tmp_path, "start-missing-fee", rows)

        assert [tx.type.value for tx in out.transactions] == ["BUY"], [(tx.type.value, str(tx.cash.amount if tx.cash else None)) for tx in out.transactions]
        _assert_one_trade(out, Trade("BUY", "2024-09-30", "INVI", "5", "-100"))
        assert_expected_charge_links(out, "order without «New» closed by a fill with a Fee", linked=[], free=[])
        _assert_start_missing_notice(out, StartMissing("91010", "2024-09-30", "buy", "INVJ", "50", "12", "600"), _shown_rows([_HEADER, *rows], "91010"))

    def test_a_deleted_new_request_is_no_start(self, tmp_path: Path):
        """RED before INV-1c (today: BUY 10 estimated with the blocker). INVENTED: the order's only «New» row is a deleted
        change request (the shape of the sample's 9058 and 10938, «New» + «Change» + «Deleted»); deleted/rejected requests
        are excluded, so the order has no start — skipped, the notice with 10 for the estimate 200 at 20. Its evidence rows
        are left unpinned: whether «the rows the file shows» includes the deleted request is not decided."""
        rows = [
            _order_row(91011, "Buy", "INVK", "20.000000", 10, "200.000000", "0", 0, "Active", "New", "2024-10-01 10:00:00", request_status="Deleted"),
            _order_row(91011, "Buy", "INVK", "20.000000", 10, "0.000000", "0", 881, "Inactive", "Fil", "2024-10-01 10:05:00"),
        ]
        out = _parse_order(tmp_path, "deleted-new", rows)

        assert out.transactions == [], [(tx.type.value, str(tx.date), str(tx.quantity)) for tx in out.transactions]
        _assert_start_missing_notice(out, StartMissing("91011", "2024-10-01", "buy", "INVK", "20", "10", "200"), None)
