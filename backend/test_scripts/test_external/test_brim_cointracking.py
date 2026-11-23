"""
Test Suite: the CoinTracking plugin — ``broker_cointracking``, its linked charges (project 66, wave P4a)

The rest of CoinTracking (detection, the parse of its sample) is pinned by the suite parametrized over every plugin, ``test_brim_providers.py``. This module pins what
wave P4a adds, from the P2 contract (§2, §8) and the decisions D10/D10b of 16/11 (``domande-FEE.md``, «Plugin per
plugin», «Regole che valgono per ogni plugin»):

- the fiat ``Fee`` of a row names the operation of that same row as its parent (``parent_ref`` = its ``ref``), with its
  asset and its broker: a fiat-backed Trade (BUY or SELL), a fiat Deposit or Withdrawal, a fiat Staking reward (an
  INTEREST); the currency of the fee is never judged (rule 4);
- a row whose operation is an ADJUSTMENT (a crypto deposit, a crypto withdrawal, a crypto staking reward) gives no
  parent: its fiat fee stays free (an ADJUSTMENT is not a parent type; ``_create_linked_charge`` decides it);
- a crypto-denominated fee is itself an ADJUSTMENT, not a charge: it names nothing;
- a Trade the validation refuses leaves its fee free;
- the link adds names only: every row equals the previous version's (snapshot at HEAD a2e85db13, plugin 1.0.0) except
  ``ref``/``parent_ref``, and reimporting the sample over the previous version's rows adds nothing;
- the plugin version goes up.

The sample has no fiat deposit, withdrawal or staking with a fee, no crypto fee and no fee in another currency: those
cases are INVENTED rows written in ``tmp_path``, never in the repository's sample.

Red before the code change: the expected links (sample and invented rows) and the version. Green before and after
(guards): the structure, the snapshot comparison, the reimport, the free charges, the crypto fee, the refused trade.

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

PLUGIN_CODE = "broker_cointracking"
SAMPLE_DIR = SampleDir()
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7


def _row(tx_type: str, day: str, amount: str, currency: str, symbol: str | None) -> RowKey:
    """A row of the output: CoinTracking assets have no ISIN, they are named by their symbol."""
    return (tx_type, day, amount, currency, symbol)


#: Per sample: (linked (charge, parent), free charges). Every FEE/TAX of the output must be in one of the two.
EXPECTED: Dict[str, Tuple[List[Tuple[RowKey, RowKey]], List[RowKey]]] = {
    "cointracking-export.csv": (
        [
            (_row("FEE", "2025-01-01", "-19", "EUR", "BTC"), _row("BUY", "2025-01-01", "-500", "EUR", "BTC")),
            (_row("FEE", "2024-12-06", "-1", "EUR", "BTC"), _row("BUY", "2024-12-06", "-100", "EUR", "BTC")),
            (_row("FEE", "2025-01-11", "-2", "EUR", "BTC"), _row("SELL", "2025-01-11", "200", "EUR", "BTC")),
        ],
        # The EUR fee of a crypto staking reward: its operation is an ADJUSTMENT, not a parent.
        [_row("FEE", "2025-01-18", "-2", "EUR", "BTC")],
    ),
}
SAMPLES = tuple(EXPECTED)

_HEADER = '"Type","Buy","Cur.","Sell","Cur.","Fee","Cur.","Exchange","Group","Comment","Date","Tx-ID"'

# INVENTED rows (amounts, dates and symbols made up), one per case the sample lacks; every key below is unique.
_FIAT_DEPOSIT = '"Deposit","1000.00","EUR","","","1.50","EUR","Kraken","","","2025-02-01 09:00:00",""'
_FIAT_WITHDRAWAL = '"Withdrawal","","","300.00","EUR","0.90","EUR","Kraken","","","2025-02-02 09:00:00",""'
_FIAT_STAKING = '"Staking","4.20","EUR","","","0.10","EUR","Kraken","","","2025-02-03 09:00:00",""'
_CRYPTO_DEPOSIT = '"Deposit","0.00200000","ETH","","","3.00","EUR","Kraken","","","2025-02-04 09:00:00",""'
_CRYPTO_WITHDRAWAL = '"Withdrawal","","","0.00300000","ETH","2.50","EUR","Kraken","","","2025-02-05 09:00:00",""'
_TRADE_CRYPTO_FEE = '"Trade","0.01000000","ETH","250.00","EUR","0.00010000","ETH","Kraken","","","2025-02-06 09:00:00",""'
_TRADE_USD_FEE = '"Trade","0.02000000","ETH","500.00","EUR","1.20","USD","Kraken","","","2025-02-07 09:00:00",""'
_INVENTED = [_FIAT_DEPOSIT, _FIAT_WITHDRAWAL, _FIAT_STAKING, _CRYPTO_DEPOSIT, _CRYPTO_WITHDRAWAL, _TRADE_CRYPTO_FEE, _TRADE_USD_FEE]

_INVENTED_LINKED: List[Tuple[RowKey, RowKey]] = [
    (_row("FEE", "2025-02-01", "-1.50", "EUR", None), _row("DEPOSIT", "2025-02-01", "1000.00", "EUR", None)),
    (_row("FEE", "2025-02-02", "-0.90", "EUR", None), _row("WITHDRAWAL", "2025-02-02", "-300.00", "EUR", None)),
    (_row("FEE", "2025-02-03", "-0.10", "EUR", None), _row("INTEREST", "2025-02-03", "4.20", "EUR", None)),
    # A USD fee on a EUR trade (rule 4: the currency of a charge is never judged).
    (_row("FEE", "2025-02-07", "-1.20", "USD", "ETH"), _row("BUY", "2025-02-07", "-500.00", "EUR", "ETH")),
]
#: The fiat fees of a crypto deposit and a crypto withdrawal: their operation is an ADJUSTMENT. The plugin gives them
#: the crypto's asset; a free charge keeps the plugin's values.
_INVENTED_FREE: List[RowKey] = [
    _row("FEE", "2025-02-04", "-3.00", "EUR", "ETH"),
    _row("FEE", "2025-02-05", "-2.50", "EUR", "ETH"),
]
_INVENTED_TYPES = ["DEPOSIT", "FEE", "WITHDRAWAL", "FEE", "INTEREST", "FEE", "ADJUSTMENT", "FEE", "ADJUSTMENT", "FEE", "BUY", "ADJUSTMENT", "BUY", "FEE"]


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, rows: Sequence[str]) -> Path:
    path = tmp_path / "cointracking-linked.csv"
    path.write_text("\n".join([_HEADER, *rows]) + "\n", encoding="utf-8")
    return path


def _parse_invented(tmp_path: Path):
    """The invented file, with its presence barrier: no refused row, and the types in order (green before and after)."""
    out = _plugin().parse(_write(tmp_path, _INVENTED), BROKER_ID)
    assert out.validation_issues == [], out.validation_issues
    assert [tx.type.value for tx in out.transactions] == _INVENTED_TYPES, [tx.type.value for tx in out.transactions]
    return out


class TestCoinTrackingLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_each_fiat_fee_names_the_trade_of_its_row(self, sample: str):
        """RED before P4a: the fiat fee of a fiat-backed trade names its trade; the staking reward's fee stays free."""
        linked, free = EXPECTED[sample]
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{sample}]", linked=linked, free=free)

    def test_invented_rows_link_every_parent_type_of_the_file(self, tmp_path: Path):
        """RED before P4a. Invented rows: the fee of a fiat deposit, a fiat withdrawal, a fiat staking reward (INTEREST)
        and of a trade paid in another currency names its row; the fees of crypto transfers stay free; the crypto fee is an
        ADJUSTMENT and names nothing (exhaustive)."""
        out = _parse_invented(tmp_path)

        assert_expected_charge_links(out, "invented rows", linked=_INVENTED_LINKED, free=_INVENTED_FREE)

    def test_a_fee_beside_an_adjustment_stays_free(self, tmp_path: Path):
        """Guard (contract §8): a crypto deposit or withdrawal is an ADJUSTMENT, not a parent, so its fiat fee stays free —
        before and after the link."""
        out = _parse_invented(tmp_path)

        assert_expected_charge_links(out, "invented rows: fees beside an ADJUSTMENT", linked=[], free=_INVENTED_FREE, exhaustive=False)

    def test_a_crypto_fee_is_an_adjustment_that_names_nothing(self, tmp_path: Path):
        """Guard: a crypto-denominated fee is an ADJUSTMENT of quantity (no cash), not a charge — it carries no
        ``parent_ref``, and its trade emits no FEE."""
        out = _parse_invented(tmp_path)
        crypto_fees = [tx for tx in out.transactions if tx.type == TransactionType.ADJUSTMENT and tx.cash is None and str(tx.date) == "2025-02-06"]
        assert len(crypto_fees) == 1, f"presence barrier: one crypto fee on 2025-02-06; {[(tx.type.value, str(tx.date)) for tx in out.transactions]}"

        assert crypto_fees[0].parent_ref is None, f"a crypto fee is not a charge: parent_ref={crypto_fees[0].parent_ref!r}"
        assert not [tx for tx in out.transactions if tx.type == TransactionType.FEE and str(tx.date) == "2025-02-06"], "a crypto fee must not also be a FEE"

    def test_a_refused_trade_leaves_its_fee_free(self, tmp_path: Path):
        """Guard: a trade the validation refuses (``Buy`` 0: a BUY needs a quantity > 0) is not in the output, so its fee has
        no parent to name: it is still imported, free, and nothing raises (``_create_linked_charge`` needs a parent of
        the output). Invented row."""
        path = _write(tmp_path, ['"Trade","0","ETH","100.00","EUR","0.75","EUR","Kraken","","","2025-02-08 09:00:00",""'])

        out = _plugin().parse(path, BROKER_ID)

        assert [(issue.row, issue.code) for issue in out.validation_issues] == [(2, "qtyPositive")], out.validation_issues
        assert [tx.type for tx in out.transactions] == [TransactionType.FEE], [tx.type for tx in out.transactions]
        assert_expected_charge_links(out, "refused trade", linked=[], free=[_row("FEE", "2025-02-08", "-0.75", "EUR", "ETH")])

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
