"""
Test Suite: the Delta plugin — ``broker_delta``, its linked charges (project 66, wave P4a)

The rest of Delta (detection, the parse of its sample) is pinned by the suite parametrized over every plugin, ``test_brim_providers.py``. This module pins what wave
P4a adds, from the P2 contract (§2, §8) and the decisions D10/D10b of 16/11 (``domande-FEE.md``, «Plugin per plugin»,
«Regole che valgono per ogni plugin»):

- the fiat ``Fee amount`` of a row names the operation of that same row as its parent (``parent_ref`` = its ``ref``),
  with its asset and its broker: a fiat-backed BUY or SELL, a DIVIDEND, a fiat DEPOSIT or WITHDRAW; the currency of the
  fee is never judged (rule 4);
- a row whose operation is an ADJUSTMENT (a crypto-to-crypto BUY/SELL, a crypto DEPOSIT or WITHDRAW) gives no parent:
  its fiat fee stays free (an ADJUSTMENT is not a parent type; ``_create_linked_charge`` decides it);
- a crypto-denominated fee is itself an ADJUSTMENT, not a charge: it names nothing;
- the link adds names only: every row equals the previous version's (snapshot at HEAD a2e85db13, plugin 1.0.0) except
  ``ref``/``parent_ref``, and reimporting the sample over the previous version's rows adds nothing;
- the plugin version goes up.

The sample has one fiat fee (the dividend's); its other fees are in crypto. The fiat BUY/SELL, DEPOSIT/WITHDRAW, the fees
beside an ADJUSTMENT and the fee in another currency are INVENTED rows written in ``tmp_path``, never in the
repository's sample.

No simple input makes a Delta parent fail the validation while its fee passes (the plugin skips, before creating it, a
row whose amount or quantity would be refused): the refused-parent path has no test here.

Red before the code change: the expected links (sample and invented rows) and the version. Green before and after
(guards): the structure, the snapshot comparison, the reimport, the free charges, the crypto fees.

The reimport opens a private in-memory SQLite per test and disposes it: no server, no shared database.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import pytest

from backend.app.db.models import TransactionType
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

PLUGIN_CODE = "broker_delta"
SAMPLE_DIR = SampleDir()
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7


def _row(tx_type: str, day: str, amount: str, currency: str, symbol: str | None) -> RowKey:
    """A row of the output: Delta assets have no ISIN, they are named by their symbol."""
    return (tx_type, day, amount, currency, symbol)


#: Per sample: (linked (charge, parent), free charges). Every FEE/TAX of the output must be in one of the two. The
#: crypto fees of the sample (0.1 BNB, 0.001 DOT) are ADJUSTMENTs, not charges: the exhaustive check also proves they
#: name no parent.
EXPECTED: Dict[str, Tuple[List[Tuple[RowKey, RowKey]], List[RowKey]]] = {
    "delta-export.csv": (
        [(_row("FEE", "2023-05-08", "-0.5", "USD", "AAPL"), _row("DIVIDEND", "2023-05-08", "2.5", "USD", "AAPL"))],
        [],
    ),
}
SAMPLES = tuple(EXPECTED)

_HEADER = "Date,Way,Base amount,Base currency (name),Base type,Quote amount,Quote currency,Exchange,Sent/Received from,Sent to,Fee amount,Fee currency (name),Broker,Notes"

# INVENTED rows (amounts, dates and symbols made up), one per case the sample lacks; every key below is unique.
_INVENTED = [
    "2024-01-02 15:00:00-04:00,BUY,2,MSFT,STOCK,800,USD,Nasdaq,,,1.00,USD,eToro,",
    "2024-01-03 15:00:00-04:00,SELL,1,MSFT,STOCK,420,USD,Nasdaq,,,1.10,USD,eToro,",
    "2024-01-04 15:00:00-04:00,DEPOSIT,1000,EUR,FIAT,,,,,,2.00,EUR,eToro,",
    "2024-01-05 15:00:00-04:00,WITHDRAW,200,EUR,FIAT,,,,,,1.25,EUR,eToro,",
    # A crypto-to-crypto BUY (an ADJUSTMENT) with a fiat fee.
    "2024-01-06 15:00:00-04:00,BUY,1,ETH,CRYPTO,0.05,BTC,Binance,,,1.40,USD,,",
    # A crypto withdrawal and a crypto deposit (ADJUSTMENTs) with a fiat fee.
    "2024-01-07 15:00:00-04:00,WITHDRAW,0.5,ETH,CRYPTO,,,,MY_WALLET,OTHER,0.60,EUR,,",
    "2024-01-08 15:00:00-04:00,DEPOSIT,0.2,ETH,CRYPTO,,,,OTHER,MY_WALLET,0.30,EUR,,",
    # A fiat-backed BUY with a crypto fee (an ADJUSTMENT, not a charge).
    "2024-01-09 15:00:00-04:00,BUY,0.1,ETH,CRYPTO,300,EUR,Kraken,,,0.001,ETH,,",
    # A USD trade with a EUR fee.
    "2024-01-10 15:00:00-04:00,BUY,3,NVDA,STOCK,450,USD,Nasdaq,,,0.80,EUR,eToro,",
]
_INVENTED_LINKED: List[Tuple[RowKey, RowKey]] = [
    (_row("FEE", "2024-01-02", "-1.00", "USD", "MSFT"), _row("BUY", "2024-01-02", "-800", "USD", "MSFT")),
    (_row("FEE", "2024-01-03", "-1.10", "USD", "MSFT"), _row("SELL", "2024-01-03", "420", "USD", "MSFT")),
    (_row("FEE", "2024-01-04", "-2.00", "EUR", None), _row("DEPOSIT", "2024-01-04", "1000", "EUR", None)),
    (_row("FEE", "2024-01-05", "-1.25", "EUR", None), _row("WITHDRAWAL", "2024-01-05", "-200", "EUR", None)),
    # Rule 4: the currency of a charge is never judged.
    (_row("FEE", "2024-01-10", "-0.80", "EUR", "NVDA"), _row("BUY", "2024-01-10", "-450", "USD", "NVDA")),
]
#: The fiat fees beside an ADJUSTMENT. The plugin gives them the crypto's asset; a free charge keeps the plugin's values.
_INVENTED_FREE: List[RowKey] = [
    _row("FEE", "2024-01-06", "-1.40", "USD", "ETH"),
    _row("FEE", "2024-01-07", "-0.60", "EUR", "ETH"),
    _row("FEE", "2024-01-08", "-0.30", "EUR", "ETH"),
]
_INVENTED_TYPES = ["BUY", "FEE", "SELL", "FEE", "DEPOSIT", "FEE", "WITHDRAWAL", "FEE", "ADJUSTMENT", "FEE", "ADJUSTMENT", "FEE", "ADJUSTMENT", "FEE", "BUY", "ADJUSTMENT", "BUY", "FEE"]


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, rows: Sequence[str]) -> Path:
    path = tmp_path / "delta-linked.csv"
    path.write_text("\n".join([_HEADER, *rows]) + "\n", encoding="utf-8")
    return path


def _parse_invented(tmp_path: Path):
    """The invented file, with its presence barrier: no refused row, and the types in order (green before and after)."""
    out = _plugin().parse(_write(tmp_path, _INVENTED), BROKER_ID)
    assert out.validation_issues == [], out.validation_issues
    assert [tx.type.value for tx in out.transactions] == _INVENTED_TYPES, [tx.type.value for tx in out.transactions]
    return out


class TestDeltaLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_dividend_fee_names_the_dividend(self, sample: str):
        """RED before P4a: the fiat fee of the dividend row names that dividend; the crypto fees are ADJUSTMENTs and name nothing."""
        linked, free = EXPECTED[sample]
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{sample}]", linked=linked, free=free)

    def test_invented_rows_link_every_parent_type_of_the_file(self, tmp_path: Path):
        """RED before P4a. Invented rows: the fiat fee of a fiat BUY, a SELL, a fiat DEPOSIT, a fiat WITHDRAW and of a trade
        paid in another currency names its row; the fees beside an ADJUSTMENT stay free; the crypto fee names nothing
        (exhaustive)."""
        out = _parse_invented(tmp_path)

        assert_expected_charge_links(out, "invented rows", linked=_INVENTED_LINKED, free=_INVENTED_FREE)

    def test_a_fee_beside_an_adjustment_stays_free(self, tmp_path: Path):
        """Guard (contract §8): a crypto-to-crypto trade, a crypto deposit and a crypto withdrawal are ADJUSTMENTs, not
        parents, so their fiat fees stay free — before and after the link."""
        out = _parse_invented(tmp_path)

        assert_expected_charge_links(out, "invented rows: fees beside an ADJUSTMENT", linked=[], free=_INVENTED_FREE, exhaustive=False)

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_crypto_fees_of_the_sample_name_nothing(self, sample: str):
        """Guard: the sample's crypto fees (0.1 BNB, 0.001 DOT) are ADJUSTMENTs of quantity, not charges: no ``parent_ref``."""
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)
        crypto_fees = [tx for tx in out.transactions if tx.type == TransactionType.ADJUSTMENT and (tx.description or "").startswith("Delta crypto fee")]
        assert len(crypto_fees) == 2, f"presence barrier: two crypto fees; {[(tx.type.value, tx.description) for tx in out.transactions]}"

        assert [tx.parent_ref for tx in crypto_fees] == [None, None], [tx.parent_ref for tx in crypto_fees]

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
