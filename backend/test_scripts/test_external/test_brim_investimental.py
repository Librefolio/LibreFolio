"""
Test Suite: the Investimental plugin — ``broker_investimental``, its linked charges (project 66, wave P4a)

The rest of Investimental (detection, the parse of its sample) is pinned by the suite parametrized over every plugin, ``test_brim_providers.py``. This module pins
what wave P4a adds, from the P2 contract (§2, §8) and the decisions D10/D10b of 16/11 (``domande-FEE.md``, «Plugin per
plugin», «Regole che valgono per ogni plugin»):

- the ``Fee`` of the row the plugin selects for an executed order names the trade it emits for that row as its parent
  (``parent_ref`` = its ``ref``), with its asset and its broker. The fee is always in the account's currency, like the
  trade: there is no cross-currency case;
- the link adds names only: every row equals the previous version's (snapshot at HEAD a2e85db13, plugin 1.0.0) except
  ``ref``/``parent_ref``, and reimporting the sample over the previous version's rows adds nothing;
- the plugin version goes up.

**The sample emits no charge** (doubt 4 of the census): the plugin reads the last row of each order that is not deleted
or rejected, and in the sample that row is always the final «Fil» with ``Value`` 0 and ``Fee`` 0 — the earlier rows of
the order carry a ``Fee``. Whether a commission is lost there is a question for the consultant, not this wave: the
sample's expectation below pins today's output (no charge) and assumes no fix. A selected row with a ``Fee`` above 0
never occurs in the sample, so the link is proved in ``tmp_path``, never in the repository's sample: on INVENTED orders
(a final «Fil» with its Value and Fee), and on the sample's own order 21368 cut after its last partial «Fil» (an
«Active» fill row carries a Fee). No simple input makes an Investimental trade fail the validation (the plugin skips an order with no volume or
no value before creating it): the refused-parent path has no test here.

Red before the code change: the link on the invented orders and on the cut order, and the version. Green before and after (guards): the
sample's expectation (no charge), the structure, the snapshot comparison, the reimport.

The reimport opens a private in-memory SQLite per test and disposes it: no server, no shared database.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import pytest

from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.test_scripts.brim_charge_links import (
    RowKey,
    assert_charge_link_structure,
    assert_expected_charge_links,
    assert_sample_reimport_adds_nothing,
    changes_besides_links,
    load_previous_snapshot,
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


def _order_row(order_id: int, side: str, symbol: str, price: str, volume: int, value: str, fee: str, trade_id: int, status: str, update: str, time: str) -> str:
    """One INVENTED order-log row (the sample's columns; account «[RON]»)."""
    return f"{order_id},5{order_id},{side},BVB,{symbol},REGS,{price},{volume},,{value},{fee},Day,,None,,T+2,,Net,No,AC000001,TEST ACCOUNT [RON]," f"{trade_id},{trade_id},{status},AC000001,AC000001,{update},{time},,,"


# INVENTED orders whose final «Fil» row carries the executed Value and its Fee: the shape the sample never has.
_INVENTED = [
    _order_row(90001, "Buy", "TVBETETF", "25.000000", 40, "1000.000000", "4.50", 0, "Active", "New", "2024-09-02 10:00:00"),
    _order_row(90001, "Buy", "TVBETETF", "25.000000", 40, "1000.000000", "4.50", 777, "Inactive", "Fil", "2024-09-02 10:05:00"),
    _order_row(90002, "Sell", "ICBETNETF", "80.000000", 10, "800.000000", "3.90", 0, "Active", "New", "2024-09-03 10:00:00"),
    _order_row(90002, "Sell", "ICBETNETF", "80.000000", 10, "800.000000", "3.90", 778, "Inactive", "Fil", "2024-09-03 10:05:00"),
]
_INVENTED_LINKED: List[Tuple[RowKey, RowKey]] = [
    (_row("FEE", "2024-09-02", "-4.50", "TVBETETF"), _row("BUY", "2024-09-02", "-1000", "TVBETETF")),
    (_row("FEE", "2024-09-03", "-3.90", "ICBETNETF"), _row("SELL", "2024-09-03", "800", "ICBETNETF")),
]
_INVENTED_TYPES = ["BUY", "FEE", "SELL", "FEE"]

#: Order 21368 of the sample, cut after its last partial «Fil» (the final «Inactive» row dropped): the only shape seen in
#: the sample's own rows where the selected row carries a Fee (43.06 on a Value of 14354.55) — so the plugin emits a FEE.
_CUT_ORDER = "21368"
_CUT_LINKED: List[Tuple[RowKey, RowKey]] = [(_row("FEE", "2024-08-05", "-43.06", "ICBETNETF"), _row("BUY", "2024-08-05", "-14354.55", "ICBETNETF"))]


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
    """The invented file, with its presence barrier: no refused row, and the types in order (green before and after)."""
    out = _plugin().parse(_write(tmp_path, _INVENTED), BROKER_ID)
    assert out.validation_issues == [], out.validation_issues
    assert [tx.type.value for tx in out.transactions] == _INVENTED_TYPES, [tx.type.value for tx in out.transactions]
    return out


class TestInvestimentalLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_sample_emits_no_charge(self, sample: str):
        """Guard: today's output of the sample has eight trades and no charge (doubt 4). It assumes no fix of the commission
        read from the final «Fil» row: a decision of the consultant changes this line, not the link."""
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

    def test_the_fee_of_a_partial_fill_of_the_sample_names_its_trade(self, tmp_path: Path):
        """RED before P4a. The sample's order 21368 written to ``tmp_path`` without its final «Inactive Fil» row (the
        repository's sample is untouched): the selected row is the last partial fill, its Fee names the BUY (exhaustive)."""
        with (SAMPLE_DIR / "investimental-export.csv").open(encoding="utf-8", newline="") as handle:
            lines = handle.read().splitlines()
        rows = [line for line in lines[1:] if line.startswith(f"{_CUT_ORDER},") and ",Inactive," not in line]
        assert len(rows) == 4, f"presence barrier: order {_CUT_ORDER} has 4 rows before its final fill in the sample; {rows}"
        out = _plugin().parse(_write(tmp_path, rows), BROKER_ID)
        assert out.validation_issues == [], out.validation_issues
        assert [tx.type.value for tx in out.transactions] == ["BUY", "FEE"], [tx.type.value for tx in out.transactions]

        assert_expected_charge_links(out, f"order {_CUT_ORDER} cut after its last partial fill", linked=_CUT_LINKED, free=[])

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_links_are_well_formed(self, sample: str):
        """Guard: every ``ref`` unique, every ``parent_ref`` names a ``ref`` of the output (vacuous before P4a)."""
        assert_charge_link_structure(_plugin().parse(SAMPLE_DIR / sample, BROKER_ID), f"{PLUGIN_CODE} [{sample}]")

    def test_the_links_of_the_invented_orders_are_well_formed(self, tmp_path: Path):
        """Guard: the structure on the invented orders too (vacuous before P4a)."""
        assert_charge_link_structure(_parse_invented(tmp_path), "invented orders")

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_only_the_names_change_from_the_previous_version(self, sample: str):
        """Guard: the link adds ``ref``/``parent_ref`` and nothing else — every row equals the snapshot's, in order (type,
        date, quantity, cash, asset, broker, description, tags)."""
        previous = load_previous_snapshot(PLUGIN_CODE, sample, BROKER_ID)
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        problems = changes_besides_links(previous.transactions, out.transactions)
        assert not problems, f"{sample}: the output changed besides its links (snapshot HEAD {previous.source_head}):\n  " + "\n  ".join(problems)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", SAMPLES)
    async def test_reimport_over_the_previous_version_adds_nothing(self, sample: str):
        """Guard (P2 contract §2.1, §8): the sample, reimported over the rows the previous version saved (without links), adds no row."""
        out = await assert_sample_reimport_adds_nothing(_plugin(), sample)

        assert out.transactions, f"{sample}: the criterion ran on an empty output"

    def test_the_version_is_above_the_previous_one(self):
        """RED before P4a: every touched plugin goes up a version (contract §8)."""
        plugin = _plugin()
        for sample in SAMPLES:
            previous = load_previous_snapshot(PLUGIN_CODE, sample, BROKER_ID)
            assert version_tuple(plugin.plugin_version) > version_tuple(previous.plugin_version), f"{PLUGIN_CODE} {plugin.plugin_version}: not above the snapshot's {previous.plugin_version} ({sample})"
