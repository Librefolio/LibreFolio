"""
Test Suite: the Fineco plugin — ``broker_fineco``, its linked charges (project 66, wave P2a)

The rest of Fineco (samples row by row, safe rows N74 / W-B83, the operation date B-52, the commission inside the
Controvalore W-B92) is pinned in ``test_brim_providers.py``. This module pins what wave P2a adds, from the P2 contract
(§2, §3) and the decisions of 16/11 (``domande-FEE.md``, «Plugin per plugin»):

- the FEE of a «Compravendita titoli» row of the layout with commission columns (Variant B) names the trade of that row
  as its parent (``parent_ref`` = the trade's ``ref``), with its asset and its broker; the FEE is in EUR while the trade
  may be in the row's ``Divisa`` (rule 4: the currency is never judged);
- the 11-column layout (Variant A, ``fineco_variant_a.csv``) has no commission: no charge at all; the BTP samples belong
  to Variant B and link like it;
- the link adds names only: every row equals the previous version's (snapshot taken at HEAD 890343101, plugin 1.5.0)
  except ``ref``/``parent_ref``, and reimporting a sample over the previous version's rows adds nothing;
- the plugin version goes up.

Red before the code change: the expected links and the version. Green before and after (guards): the structure, the
snapshot comparison, the reimport, a refused trade whose commission stays free.

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

PLUGIN_CODE = "broker_fineco"
SAMPLE_DIR = SampleDir()
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7

# Securities of the samples (public identifiers; every amount and date around them is invented).
MSCI_WORLD = "IE00B4L5Y983"
EM_IMI = "IE00BKM4GZ66"
APPLE = "US0378331005"
BTP_VALORE = "IT0005583478"
BTP_2025 = "IT0005416570"
BTP_2025_CUM = "IT0005410912"
COVERED_BOND = "IE00B3B8Q275"


def _fee(day: str, amount: str, isin: str) -> RowKey:
    """A Fineco commission: always EUR (``FEE_CURRENCY``), on the security of its row."""
    return ("FEE", day, amount, "EUR", isin)


def _buy(day: str, amount: str, isin: str, currency: str = "EUR") -> RowKey:
    return ("BUY", day, amount, currency, isin)


def _sell(day: str, amount: str, isin: str, currency: str = "EUR") -> RowKey:
    return ("SELL", day, amount, currency, isin)


#: Per sample: (linked (charge, parent), free charges). Every FEE/TAX of the output must be in one of the two.
EXPECTED: Dict[str, Tuple[List[Tuple[RowKey, RowKey]], List[RowKey]]] = {
    "fineco-export.csv": (
        [
            (_fee("2024-01-15", "-2.95", MSCI_WORLD), _buy("2024-01-15", "-528.55", MSCI_WORLD)),
            # Same day, same commission: told apart by the security.
            (_fee("2024-01-15", "-2.95", EM_IMI), _buy("2024-01-15", "-330.50", EM_IMI)),
            (_fee("2024-03-15", "-2.95", EM_IMI), _sell("2024-03-15", "136.80", EM_IMI)),
            # EUR commission on a USD trade (rule 4).
            (_fee("2024-02-20", "-12.95", APPLE), _buy("2024-02-20", "-329.03", APPLE, "USD")),
            (_fee("2024-05-15", "-12.95", APPLE), _sell("2024-05-15", "176.10", APPLE, "USD")),
            (_fee("2024-01-10", "-5.00", BTP_VALORE), _buy("2024-01-10", "-1990.00", BTP_VALORE)),
        ],
        [],
    ),
    "fineco_btp_market.csv": (
        [
            (_fee("2023-09-04", "-3.50", BTP_2025), _buy("2023-09-04", "-4920.00", BTP_2025)),
            (_fee("2023-09-11", "-2.95", MSCI_WORLD), _buy("2023-09-11", "-208.20", MSCI_WORLD)),
            (_fee("2023-09-18", "-2.95", COVERED_BOND), _buy("2023-09-18", "-420.00", COVERED_BOND)),
        ],
        [],
    ),
    "fineco_btp_placement.csv": (
        [
            (_fee("2023-05-12", "-3.50", BTP_2025_CUM), _buy("2023-05-12", "-10000.00", BTP_2025_CUM)),
            (_fee("2023-06-20", "-2.95", MSCI_WORLD), _buy("2023-06-20", "-409.20", MSCI_WORLD)),
        ],
        [],
    ),
    # Variant A: 11 columns, no commission in the file — no charge to link, none to emit.
    "fineco_variant_a.csv": ([], []),
}
SAMPLES = tuple(EXPECTED)

# A Variant-B file, for the synthetic case: the preamble and header of the samples.
_PREAMBLE = ["Dossier: 123456789" + "," * 15, "Intestatario: ROSSI MARIO" + "," * 15, "," * 15, "Titoli e operazioni" + "," * 15, "," * 15]
_HEADER = "Operazione,Data valuta,Descrizione,Titolo,Isin,Segno,Quantita,Divisa,Prezzo,Cambio,Controvalore,Commissioni Fondi Sw/Ingr/Uscita,Commissioni Fondi Banca Corrispondente,Spese Fondi Sgr,Commissioni amministrato"


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, rows: Sequence[str]) -> Path:
    path = tmp_path / "fineco-linked.csv"
    path.write_text("\n".join([*_PREAMBLE, _HEADER, *rows]) + "\n", encoding="utf-8")
    return path


class TestFinecoLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_each_commission_names_the_trade_of_its_row(self, sample: str):
        """RED before P2a: every Variant-B commission names its trade; Variant A has no charge (green before and after)."""
        linked, free = EXPECTED[sample]
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{sample}]", linked=linked, free=free)

    def test_a_fee_in_eur_names_a_trade_in_usd(self):
        """RED before P2a. Rule 4: the currency of a charge is never judged — the EUR commission of a USD trade is linked."""
        out = _plugin().parse(SAMPLE_DIR / "fineco-export.csv", BROKER_ID)
        fee_key, buy_key = _fee("2024-02-20", "-12.95", APPLE), _buy("2024-02-20", "-329.03", APPLE, "USD")

        assert_expected_charge_links(out, "fineco-export.csv: the cross-currency pair", linked=[(fee_key, buy_key)], free=[], exhaustive=False)

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_links_are_well_formed(self, sample: str):
        """Guard: every ``ref`` unique, every ``parent_ref`` names a ``ref`` of the output (vacuous before P2a)."""
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
        """Guard (P2 contract §2.1): the sample, reimported over the rows the previous version saved (without links), adds no row."""
        out = await assert_sample_reimport_adds_nothing(_plugin(), sample)

        assert out.transactions, f"{sample}: the criterion ran on an empty output"

    def test_the_version_is_above_the_previous_one(self):
        """RED before P2a: every touched plugin goes up a version (the decisions of 16/11)."""
        plugin = _plugin()
        for sample in SAMPLES:
            previous = load_previous_snapshot(PLUGIN_CODE, sample, BROKER_ID)
            assert version_tuple(plugin.plugin_version) > version_tuple(previous.plugin_version), f"{PLUGIN_CODE} {plugin.plugin_version}: not above the snapshot's {previous.plugin_version} ({sample})"

    def test_a_refused_trade_leaves_its_commission_free(self, tmp_path: Path):
        """Guard: a trade the validation refuses (``Quantita`` unreadable, as in W-B83) is not in the output, so its
        commission has no parent to name: it is still imported, free, and nothing raises (``_create_linked_charge``
        needs a parent of the output)."""
        path = _write(tmp_path, ["10/01/2024,12/01/2024,Compravendita titoli,BTP VALORE SC MZ30,IT0005583478,A,n.d.,EUR,99.75000,,1995.00,,,,5.00"])

        out = _plugin().parse(path, BROKER_ID)

        assert [(issue.row, issue.code) for issue in out.validation_issues] == [(7, "qtyPositive")], out.validation_issues
        assert [tx.type for tx in out.transactions] == [TransactionType.FEE], [tx.type for tx in out.transactions]
        assert_expected_charge_links(out, "refused trade", linked=[], free=[_fee("2024-01-10", "-5.00", BTP_VALORE)])
