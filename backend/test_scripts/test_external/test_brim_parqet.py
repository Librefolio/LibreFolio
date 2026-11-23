"""
Test Suite: the Parqet plugin — ``broker_parqet``, its linked charges (project 66, lot P4a)

Parqet is an aggregator: one row of its export is one booking, with its ``tax`` and ``fee`` columns. The plugin emits
the booking, then a TAX for a non-zero ``tax``, then a FEE for a non-zero ``fee``. This module pins what lot P4a adds,
from the P2 contract (§2, §8) and the decisions of 16/11 (``domande-FEE.md``, «Plugin per plugin»):

- the TAX and the FEE of a trade or dividend row name that row as their parent (``parent_ref`` = its ``ref``), with its
  asset and its broker;
- the same holds for the other parent types a Parqet row can be — an interest (with or without a security), a deposit
  (``TransferIn``), a withdrawal (``TransferOut``). Contract §8 names trades and dividends for Parqet; its general rule
  («a FEE or TAX born from the same row as its operation is linked») and the transaction rules (a charge may name a
  buy, a sell, a dividend, an interest, a deposit or a withdrawal) give the rest. This reading has its own test, so a
  different decision changes one place;
- a booking the validation refuses is not in the output, so its tax and fee have no parent: they are imported, free —
  never linked to the previous booking of the same security;
- the link adds names only: every row equals the previous version's (snapshot taken at HEAD a2e85db13, plugin 1.0.0)
  except ``ref``/``parent_ref``, and reimporting the sample over the previous version's rows adds nothing;
- the plugin version goes up.

Not tested here (amounts are not P4's): the sample's sale of 2024-05-15 has ``tax`` -12,64, emitted today as a TAX of
-12.64 (``-abs(tax)``): a refund booked as a charge (doubt 8 of the census). Its link is pinned like any other; its sign
is left as it is.

Red before the code change: the expected links (sample and invented rows) and the version. Green before and after
(guards): the structure, the snapshot comparison, the reimport, the refused booking whose charges stay free.

No ADJUSTMENT can be a parent here: the plugin emits none (rule 6 has no case in Parqet).

Every input is the sample of ``sample_reports/`` or a file written in ``tmp_path`` (invented values, public ISINs). The
reimport opens a private in-memory SQLite and disposes it: no server, no shared database.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

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

PLUGIN_CODE = "broker_parqet"
SAMPLE_DIR = SampleDir()
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7

# Securities of the sample (public identifiers; every amount and date around them is invented).
REALTY_INCOME = "US7561091049"
ALPHABET = "US02079K3059"
ALLIANZ = "DE0008404005"
FIVERR = "IL0011582033"
APPLE = "US0378331005"
BUND = "DE0001102580"


def _row(tx_type: str, day: str, amount: str, isin: Optional[str]) -> RowKey:
    """A Parqet row: always EUR in the sample and in the invented files (the ``currency`` column)."""
    return (tx_type, day, amount, "EUR", isin)


#: Per sample: (linked (charge, parent), free charges). Every FEE/TAX of the output must be in one of the two.
EXPECTED: Dict[str, Tuple[List[Tuple[RowKey, RowKey]], List[RowKey]]] = {
    "parqet-export.csv": (
        [
            (_row("TAX", "2024-07-15", "-2.48", REALTY_INCOME), _row("DIVIDEND", "2024-07-15", "9.66", REALTY_INCOME)),
            (_row("TAX", "2024-06-17", "-0.27", ALPHABET), _row("DIVIDEND", "2024-06-17", "1.11", ALPHABET)),
            (_row("TAX", "2024-06-14", "-2.5", REALTY_INCOME), _row("DIVIDEND", "2024-06-14", "9.76", REALTY_INCOME)),
            # A sale with both columns: the tax and the fee name the same sale.
            (_row("TAX", "2024-06-04", "-14.83", ALLIANZ), _row("SELL", "2024-06-04", "1578", ALLIANZ)),
            (_row("FEE", "2024-06-04", "-1", ALLIANZ), _row("SELL", "2024-06-04", "1578", ALLIANZ)),
            # ``tax`` -12,64 in the file (doubt 8: a refund?), emitted as a TAX of -12.64: linked as it is.
            (_row("TAX", "2024-05-15", "-12.64", FIVERR), _row("SELL", "2024-05-15", "320.32", FIVERR)),
            (_row("FEE", "2024-05-15", "-1", FIVERR), _row("SELL", "2024-05-15", "320.32", FIVERR)),
            (_row("TAX", "2024-05-15", "-0.42", APPLE), _row("DIVIDEND", "2024-05-15", "1.61", APPLE)),
            (_row("TAX", "2024-05-14", "-2.51", REALTY_INCOME), _row("DIVIDEND", "2024-05-14", "9.6", REALTY_INCOME)),
            (_row("TAX", "2024-05-10", "-11.46", ALLIANZ), _row("DIVIDEND", "2024-05-10", "82.8", ALLIANZ)),
        ],
        [],
    ),
}
SAMPLES = tuple(EXPECTED)

_HEADER = '"datetime";"date";"time";"price";"shares";"amount";"tax";"fee";"realizedgains";"type";"broker";"assettype";"identifier";"wkn";"originalcurrency";"currency";"fxrate";"holding";"holdingname";"holdingnickname";"exchange";"avgholdingperiod";'


def _line(day: str, kind: str, *, price: str = "", shares: str = "", amount: str, tax: str = "0", fee: str = "0", isin: str = "", wkn: str = "", name: str = "", assettype: str = "Security") -> str:
    """One Parqet row, in the sample's shape (``;``, comma decimals, ISO ``datetime`` in UTC at 07:00)."""
    return f'"{day}T07:00:00.000Z";"";"09:00:00";{price};{shares};{amount};{tax};{fee};;"{kind}";;"{assettype}";"{isin}";"{wkn}";;"EUR";;;"{name}";;;'


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, rows: Sequence[str]) -> Path:
    path = tmp_path / "parqet-linked.csv"
    path.write_text("\n".join([_HEADER, *rows]) + "\n", encoding="utf-8")
    return path


class TestParqetLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_each_tax_and_fee_names_the_booking_of_its_row(self, sample: str):
        """RED before P4a: every tax and fee of the sample names the trade or dividend of its row (contract §8, parqet)."""
        linked, free = EXPECTED[sample]
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{sample}]", linked=linked, free=free)

    def test_a_dividend_with_both_a_tax_and_a_fee_links_both(self, tmp_path: Path):
        """RED before P4a: the sample's dividends carry a tax only; a fee on a dividend row names the dividend too. Invented row."""
        path = _write(tmp_path, [_line("2024-09-07", "Dividend", price="0,5", shares="10", amount="5", tax="1,2", fee="0,3", isin=ALLIANZ, wkn="840400", name="Allianz")])

        out = _plugin().parse(path, BROKER_ID)

        assert out.validation_issues == [], out.validation_issues
        dividend = _row("DIVIDEND", "2024-09-07", "5", ALLIANZ)
        assert_expected_charge_links(out, "Parqet: dividend with tax and fee", linked=[(_row("TAX", "2024-09-07", "-1.2", ALLIANZ), dividend), (_row("FEE", "2024-09-07", "-0.3", ALLIANZ), dividend)], free=[])

    def test_the_charges_of_an_interest_a_deposit_and_a_withdrawal_name_their_row(self, tmp_path: Path):
        """RED before P4a. The reading of contract §8's general rule for the other parent types (module docstring): the
        tax of an interest — on a security or on cash, without an asset — and the fee of a ``TransferIn`` / ``TransferOut``
        name the row they come from. Invented rows: the sample has none."""
        path = _write(
            tmp_path,
            [
                _line("2024-09-02", "Interest", amount="12,5", tax="3,3", isin=BUND, wkn="110258", name="Bund"),
                _line("2024-09-03", "Interest", amount="4,2", tax="1,1", assettype="Cash"),
                _line("2024-09-04", "TransferOut", amount="250", fee="1,5", assettype="Cash"),
                _line("2024-09-05", "TransferIn", amount="300", fee="0,5", assettype="Cash"),
            ],
        )

        out = _plugin().parse(path, BROKER_ID)

        assert out.validation_issues == [], out.validation_issues
        assert_expected_charge_links(
            out,
            "Parqet: interest, deposit, withdrawal",
            linked=[
                (_row("TAX", "2024-09-02", "-3.3", BUND), _row("INTEREST", "2024-09-02", "12.5", BUND)),
                # Cash interest: neither row has an asset, and that is a valid link.
                (_row("TAX", "2024-09-03", "-1.1", None), _row("INTEREST", "2024-09-03", "4.2", None)),
                (_row("FEE", "2024-09-04", "-1.5", None), _row("WITHDRAWAL", "2024-09-04", "-250", None)),
                (_row("FEE", "2024-09-05", "-0.5", None), _row("DEPOSIT", "2024-09-05", "300", None)),
            ],
            free=[],
        )

    def test_a_refused_booking_leaves_its_tax_and_fee_free(self, tmp_path: Path):
        """Guard: a sale the validation refuses (``shares`` 0: ``qtyNegative``) is not in the output, so its tax and fee
        have no parent to name. They are still imported, free, with the sale's asset; they never name the sale of an earlier
        row of the same security, which is in the output just before them. Invented rows."""
        path = _write(
            tmp_path,
            [
                _line("2024-09-05", "Sell", price="10", shares="4", amount="40", tax="0,8", fee="1", isin=ALLIANZ, wkn="840400", name="Allianz"),
                _line("2024-09-06", "Sell", price="10", shares="0", amount="100", tax="2", fee="1", isin=ALLIANZ, wkn="840400", name="Allianz"),
            ],
        )

        out = _plugin().parse(path, BROKER_ID)

        assert [(issue.row, issue.code) for issue in out.validation_issues] == [(3, "qtyNegative")], out.validation_issues
        assert [tx.type.value for tx in out.transactions] == ["SELL", "TAX", "FEE", "TAX", "FEE"], [tx.type.value for tx in out.transactions]
        # Not exhaustive: the charges of the valid sale are linked after P4a, the subject of the other tests.
        assert_expected_charge_links(out, "Parqet: refused sale", linked=[], free=[_row("TAX", "2024-09-06", "-2", ALLIANZ), _row("FEE", "2024-09-06", "-1", ALLIANZ)], exhaustive=False)

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_links_are_well_formed(self, sample: str):
        """Guard: every ``ref`` unique, every ``parent_ref`` names a ``ref`` of the output (vacuous before P4a)."""
        assert_charge_link_structure(_plugin().parse(SAMPLE_DIR / sample, BROKER_ID), f"{PLUGIN_CODE} [{sample}]")

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
