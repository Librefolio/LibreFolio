"""
Test Suite: the Trading 212 plugin — ``broker_trading212``, its linked charges (project 66, lot P4a)

The rest of Trading 212 (helpers, rows left out, stock splits) is pinned in ``test_brim_providers.py``,
``test_brim_row_skips.py`` and ``test_brim_economic_rows.py``. This module pins what lot P4a adds, from the P2 contract
(§2, §8) and the decisions of 16/11 (``domande-FEE.md``, «Plugin per plugin»):

- the ``Withholding tax`` column of a dividend row is a TAX that names the dividend of that row as its parent
  (``parent_ref`` = the dividend's ``ref``), with its asset and its broker;
- the tax is often in another currency (``Currency (Withholding tax)``: USD on a EUR dividend in the sample): the currency
  is never judged (rule 4), so it is linked all the same; with that column empty the tax takes the dividend's currency;
- the same holds for an ``Interest on cash`` row with a withholding tax (an INTEREST, no asset on either row): the reading
  of contract §8's general rule («a FEE or TAX born from the same row as its operation is linked»), in its own test;
- a dividend the validation refuses is not in the output, so its tax has no parent: it is imported, free — never linked
  to the previous dividend of the same security;
- the link adds names only: every row equals the previous version's (snapshot taken at HEAD a2e85db13, plugin 1.2.0)
  except ``ref``/``parent_ref``, and reimporting the sample over the previous version's rows adds nothing;
- the plugin version goes up.

Not tested here (amounts are not P4's): whether ``Total`` of a dividend is gross or net (doubt 7 of the census). If it is
net, the TAX would count the withholding twice; the sample's 0.03 EUR rows cannot tell.

Red before the code change: the expected links (sample and invented rows) and the version. Green before and after
(guards): the structure, the snapshot comparison, the reimport, the refused dividend whose tax stays free.

The only ADJUSTMENT the plugin emits is a stock split, which carries no charge (rule 6 has no case in Trading 212).

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

PLUGIN_CODE = "broker_trading212"
SAMPLE_DIR = SampleDir()
SAMPLE = "trading212-export.csv"
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7

# Securities of the sample (public identifiers; every amount and date around them is invented).
MAIN_STREET = "US56035L1044"
UNION_PACIFIC = "US9078181081"
CLEAN_ENERGY = "IE00B1XNHC34"
MICROSOFT = "US5949181045"
APPLE = "US0378331005"


def _tax(day: str, amount: str, currency: str, isin: Optional[str]) -> RowKey:
    return ("TAX", day, amount, currency, isin)


def _dividend(day: str, amount: str, isin: str) -> RowKey:
    """A dividend: ``Currency (Total)`` is EUR in the sample and in the invented rows."""
    return ("DIVIDEND", day, amount, "EUR", isin)


#: Per sample: (linked (charge, parent), free charges). Every FEE/TAX of the output must be in one of the two.
EXPECTED: Dict[str, Tuple[List[Tuple[RowKey, RowKey]], List[RowKey]]] = {
    SAMPLE: (
        [
            # USD withholding on EUR dividends (rule 4: the currency is never judged).
            (_tax("2023-12-27", "-0.01", "USD", MAIN_STREET), _dividend("2023-12-27", "0.03", MAIN_STREET)),
            (_tax("2023-12-28", "-0.01", "USD", UNION_PACIFIC), _dividend("2023-12-28", "0.03", UNION_PACIFIC)),
            (_tax("2024-01-12", "-15.02", "USD", CLEAN_ENERGY), _dividend("2024-01-12", "17.67", CLEAN_ENERGY)),
        ],
        [],
    ),
}
SAMPLES = tuple(EXPECTED)


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, rows: Sequence[str]) -> Path:
    """The sample's header (19 columns, read from the sample) and ``rows``."""
    header = (SAMPLE_DIR / SAMPLE).read_text(encoding="utf-8").splitlines()[0]
    path = tmp_path / "trading212-linked.csv"
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def _dividend_line(stamp: str, isin: str, ticker: str, name: str, total: str, tax: str, tax_currency: str) -> str:
    """A dividend row in the sample's shape: Action … Total, Currency (Total), Withholding tax, Currency (Withholding tax)."""
    return f'Dividend (Dividend),{stamp},{isin},{ticker},"{name}",1.0000000000,0.75,USD,Not available,,,{total},"EUR",{tax},{tax_currency},,,,'


class TestTrading212LinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_each_withholding_tax_names_the_dividend_of_its_row(self, sample: str):
        """RED before P4a: every withholding tax names the dividend of its row (contract §8, trading212)."""
        linked, free = EXPECTED[sample]
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{sample}]", linked=linked, free=free)

    def test_a_tax_without_its_currency_takes_the_dividends_and_is_linked(self, tmp_path: Path):
        """RED before P4a: ``Currency (Withholding tax)`` empty → the tax is in the dividend's currency, and names it. Invented row."""
        path = _write(tmp_path, [_dividend_line("2024-02-12 14:14:14", MICROSOFT, "MSFT", "Microsoft", "0.69", "0.11", "")])

        out = _plugin().parse(path, BROKER_ID)

        assert out.validation_issues == [], out.validation_issues
        assert_expected_charge_links(out, "Trading 212: tax without its currency", linked=[(_tax("2024-02-12", "-0.11", "EUR", MICROSOFT), _dividend("2024-02-12", "0.69", MICROSOFT))], free=[])

    def test_the_tax_on_interest_on_cash_names_the_interest(self, tmp_path: Path):
        """RED before P4a. The reading of contract §8's general rule for an INTEREST (module docstring): the withholding tax
        of an ``Interest on cash`` row names that interest; neither row has an asset, and that is a valid link. Invented row."""
        path = _write(tmp_path, ['Interest on cash,2024-02-06 22:06:41.36,,,,,,,,,,0.50,"EUR",0.13,EUR,"Interest on cash",8ffba791-cfc3-4002-b65d-bd63cf483d9e,,'])

        out = _plugin().parse(path, BROKER_ID)

        assert out.validation_issues == [], out.validation_issues
        assert_expected_charge_links(out, "Trading 212: interest with tax", linked=[(_tax("2024-02-06", "-0.13", "EUR", None), ("INTEREST", "2024-02-06", "0.50", "EUR", None))], free=[])

    def test_a_refused_dividend_leaves_its_tax_free(self, tmp_path: Path):
        """Guard: a dividend the validation refuses (``Total`` empty: ``cashRequired``) is not in the output, so its tax has
        no parent to name. It is still imported, free, with the dividend's asset; it never names the dividend of an earlier
        row of the same security, which is in the output just before it. Invented rows."""
        path = _write(
            tmp_path,
            [
                _dividend_line("2024-02-12 14:14:14", APPLE, "AAPL", "Apple", "0.21", "0.03", "USD"),
                _dividend_line("2024-02-13 14:14:14", APPLE, "AAPL", "Apple", "", "0.04", "USD"),
            ],
        )

        out = _plugin().parse(path, BROKER_ID)

        assert [(issue.row, issue.code) for issue in out.validation_issues] == [(3, "cashRequired")], out.validation_issues
        assert [tx.type.value for tx in out.transactions] == ["DIVIDEND", "TAX", "TAX"], [tx.type.value for tx in out.transactions]
        # Not exhaustive: the tax of the valid dividend is linked after P4a, the subject of the other tests.
        assert_expected_charge_links(out, "Trading 212: refused dividend", linked=[], free=[_tax("2024-02-13", "-0.04", "USD", APPLE)], exhaustive=False)

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
