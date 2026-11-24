"""
Test Suite: the Relai plugin — ``broker_relai``, its linked charges (project 66, wave P4a)

The rest of Relai (detection, the parse of its sample) is pinned by the suite parametrized over every plugin, ``test_brim_providers.py``. This module pins what wave
P4a adds, from the P2 contract (§2, §8) and the decisions D10/D10b of 16/11 (``domande-FEE.md``, «Plugin per plugin»,
«Regole che valgono per ogni plugin»):

- the ``Fee`` of a Buy or Sell row names the trade of that same row as its parent (``parent_ref`` = its ``ref``), with
  its asset (BTC) and its broker; the ``Fee Currency`` may differ from the ``Fiat Currency`` (rule 4: never judged);
- a ``Fee`` of 0 emits no charge;
- the link adds names only: every row equals the previous version's (snapshot at HEAD a2e85db13, plugin 1.0.0) except
  ``ref``/``parent_ref``, and reimporting the sample over the previous version's rows adds nothing;
- the plugin version goes up.

The sample has two Buy fees and a Sell with a fee of 0. A Sell with a fee and a fee in another currency are INVENTED rows
written in ``tmp_path``, never in the repository's sample. Relai has no account fee and no ADJUSTMENT: no charge stays
free by rule. No simple input makes a Relai trade fail the validation (the plugin skips a row with a zero BTC or fiat
amount before creating it): the refused-parent path has no test here.

Red before the code change: the expected links (sample and invented rows) and the version. Green before and after
(guards): the structure, the snapshot comparison, the reimport.

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

PLUGIN_CODE = "broker_relai"
SAMPLE_DIR = SampleDir()
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7


def _row(tx_type: str, day: str, amount: str, currency: str) -> RowKey:
    """A row of the output: every Relai row is on BTC (a symbol, no ISIN)."""
    return (tx_type, day, amount, currency, "BTC")


#: Per sample: (linked (charge, parent), free charges). Every FEE/TAX of the output must be in one of the two. The Sell
#: of 2024-09-15 has a fee of 0.00: no charge.
EXPECTED: Dict[str, Tuple[List[Tuple[RowKey, RowKey]], List[RowKey]]] = {
    "relai-export.csv": (
        [
            (_row("FEE", "2024-07-22", "-2.45", "CHF"), _row("BUY", "2024-07-22", "-271.05", "CHF")),
            (_row("FEE", "2024-06-18", "-2.90", "CHF"), _row("BUY", "2024-06-18", "-321.45", "CHF")),
        ],
        [],
    ),
}
SAMPLES = tuple(EXPECTED)

_HEADER = "Date,Transaction Type,BTC Amount,BTC Price,Currency Pair,Fiat Amount (excl. fees),Fiat Currency,Fee,Fee Currency,Destination,Operation ID,Counterparty"

# INVENTED rows (amounts, dates and identifiers made up).
_INVENTED = [
    "2024-10-01T10:00:00Z,Sell,0.01000000,90000.00,BTC/CHF,900.00,CHF,3.10,CHF,CH0000000000000000000,op-invented-1,Relai Switzerland",
    # A EUR fee on a CHF trade.
    "2024-10-02T10:00:00Z,Buy,0.00200000,91000.00,BTC/CHF,182.00,CHF,1.75,EUR,bc1qinvented,op-invented-2,Relai Switzerland",
]
_INVENTED_LINKED: List[Tuple[RowKey, RowKey]] = [
    (_row("FEE", "2024-10-01", "-3.10", "CHF"), _row("SELL", "2024-10-01", "900.00", "CHF")),
    # Rule 4: the currency of a charge is never judged.
    (_row("FEE", "2024-10-02", "-1.75", "EUR"), _row("BUY", "2024-10-02", "-182.00", "CHF")),
]
_INVENTED_TYPES = ["SELL", "FEE", "BUY", "FEE"]


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, rows: Sequence[str]) -> Path:
    path = tmp_path / "relai-linked.csv"
    path.write_text("\n".join([_HEADER, *rows]) + "\n", encoding="utf-8")
    return path


def _parse_invented(tmp_path: Path):
    """The invented file, with its presence barrier: no refused row, and the types in order (green before and after)."""
    out = _plugin().parse(_write(tmp_path, _INVENTED), BROKER_ID)
    assert out.validation_issues == [], out.validation_issues
    assert [tx.type.value for tx in out.transactions] == _INVENTED_TYPES, [tx.type.value for tx in out.transactions]
    return out


class TestRelaiLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_each_fee_names_the_trade_of_its_row(self, sample: str):
        """RED before P4a: the fee of each Buy names that Buy; the Sell with a fee of 0 emits no charge."""
        linked, free = EXPECTED[sample]
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{sample}]", linked=linked, free=free)

    def test_invented_rows_a_sell_and_a_fee_in_another_currency(self, tmp_path: Path):
        """RED before P4a. Invented rows: the fee of a Sell names the Sell; a EUR fee names its CHF Buy (exhaustive)."""
        out = _parse_invented(tmp_path)

        assert_expected_charge_links(out, "invented rows", linked=_INVENTED_LINKED, free=[])

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_links_are_well_formed(self, sample: str):
        """Guard: every ``ref`` unique, every ``parent_ref`` names a ``ref`` of the output (vacuous before P4a)."""
        assert_charge_link_structure(_plugin().parse(SAMPLE_DIR / sample, BROKER_ID), f"{PLUGIN_CODE} [{sample}]")

    def test_the_links_of_the_invented_rows_are_well_formed(self, tmp_path: Path):
        """Guard: the structure on the invented rows too (vacuous before P4a)."""
        assert_charge_link_structure(_parse_invented(tmp_path), "invented rows")

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
