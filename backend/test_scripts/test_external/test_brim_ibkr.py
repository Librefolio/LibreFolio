"""
Test Suite: the Interactive Brokers plugin — ``broker_ibkr``, its linked charges (project 66, lot P4a)

The rest of IBKR (parsing helpers, the default currency, the rows left out) is pinned in ``test_brim_providers.py`` and
``test_brim_row_skips.py``. This module pins what lot P4a adds, from the P2 contract (§2, §8) and the decisions of 16/11
(``domande-FEE.md``, «Plugin per plugin»):

- the ``IBCommission`` of a trade row is a FEE that names the trade of that row as its parent (``parent_ref`` = the
  trade's ``ref``), with its asset and its broker;
- the commission may be in another currency (``IBCommissionCurrency``): the currency is never judged (rule 4), so a
  CHF commission on a USD trade is linked all the same;
- a trade the validation refuses is not in the output, so its commission has no parent: it is still imported, free —
  never the previous trade of the same security;
- the link adds names only: every row equals the previous version's (snapshot taken at HEAD a2e85db13, plugin 1.1.0)
  except ``ref``/``parent_ref``, and reimporting a sample over the previous version's rows adds nothing;
- the plugin version goes up.

The trades sample has two commissions alike — 2023-06-09, -1 USD, the same ETF — on two different trades. A ``RowKey``
names exactly one row, so ``assert_expected_charge_links`` cannot list them; the sample test compares instead the multiset
of (charge, parent) pairs read through ``ref``/``parent_ref``, every charge of the output included (``_charge_pairs``).

Red before the code change: the expected links (samples and the cross-currency file) and the version. Green before and
after (guards): the structure, the snapshot comparison, the reimport, the refused trade whose commission stays free.

No ADJUSTMENT can be a parent here: the plugin emits none (rule 6 has no case in IBKR). The currency trades (rows without
an ISIN) are left out with their commission, as before (``test_brim_row_skips.py``): nothing to link.

Every input is a sample of ``sample_reports/`` or a file written in ``tmp_path`` (invented values, public ISINs). The
reimport opens a private in-memory SQLite per test and disposes it: no server, no shared database.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pytest

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import BRIMParseOutput
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.schemas.transactions.type_metadata import charge_types
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

PLUGIN_CODE = "broker_ibkr"
SAMPLE_DIR = SampleDir()
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7

# Securities of the samples (public identifiers; every amount and date around them is invented).
SWISS_ETF = "CH0111762537"
VANGUARD_ETF = "US9220427424"
APPLE = "US0378331005"

#: A row named by value, amount as a Decimal (so ``-1`` and ``-1.00`` are one key): type, ISO date, amount, currency,
#: identifier of the asset (ISIN, else symbol), None for no asset.
ValueKey = Tuple[str, str, Optional[Decimal], Optional[str], Optional[str]]


def _fee(day: str, amount: str, currency: str, isin: str) -> RowKey:
    return ("FEE", day, amount, currency, isin)


def _buy(day: str, amount: str, currency: str, isin: str) -> RowKey:
    return ("BUY", day, amount, currency, isin)


def _sell(day: str, amount: str, currency: str, isin: str) -> RowKey:
    return ("SELL", day, amount, currency, isin)


#: Per sample: every (charge, parent) pair of the output, a parent ``None`` for a free charge; a pair listed n times names
#: n charges. The whole multiset must match: a charge missing, added, or naming another row is a difference.
EXPECTED: Dict[str, List[Tuple[RowKey, Optional[RowKey]]]] = {
    "ibkr-trades-export.csv": [
        (_fee("2023-05-22", "-5", "CHF", SWISS_ETF), _buy("2023-05-22", "-1978.9", "CHF", SWISS_ETF)),
        (_fee("2023-05-22", "-1", "USD", VANGUARD_ETF), _buy("2023-05-22", "-8909.1", "USD", VANGUARD_ETF)),
        # Two commissions alike, on two trades of the same day and security: each names its own row's trade.
        (_fee("2023-06-09", "-1", "USD", VANGUARD_ETF), _buy("2023-06-09", "-10019.1", "USD", VANGUARD_ETF)),
        (_fee("2023-06-09", "-1", "USD", VANGUARD_ETF), _buy("2023-06-09", "-1050.06", "USD", VANGUARD_ETF)),
        (_fee("2023-08-03", "-0.979", "USD", VANGUARD_ETF), _buy("2023-08-03", "-97.84", "USD", VANGUARD_ETF)),
        (_fee("2023-12-28", "-1", "USD", VANGUARD_ETF), _buy("2023-12-28", "-206.36", "USD", VANGUARD_ETF)),
        (_fee("2024-01-26", "-1", "USD", VANGUARD_ETF), _buy("2024-01-26", "-10050.17", "USD", VANGUARD_ETF)),
        (_fee("2024-01-29", "-1", "USD", VANGUARD_ETF), _buy("2024-01-29", "-1243.92", "USD", VANGUARD_ETF)),
    ],
    # Empty CurrencyPrimary and IBCommissionCurrency: both default to USD.
    "ibkr-default-currency-export.csv": [
        (_fee("2024-01-30", "-1", "USD", APPLE), _sell("2024-01-30", "950", "USD", APPLE)),
    ],
}
SAMPLES = tuple(EXPECTED)

_HEADER = '"Buy/Sell","TradeDate","ISIN","Quantity","TradePrice","TradeMoney","CurrencyPrimary","IBCommission","IBCommissionCurrency"'


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, rows: Sequence[str]) -> Path:
    path = tmp_path / "ibkr-linked.csv"
    path.write_text("\n".join([_HEADER, *rows]) + "\n", encoding="utf-8")
    return path


def _value_key(out: BRIMParseOutput, tx: TXCreateItem) -> ValueKey:
    info = out.extracted_assets.get(tx.asset_id) if tx.asset_id is not None else None
    identifier = (info.extracted_isin or info.extracted_symbol) if info else (None if tx.asset_id is None else f"asset {tx.asset_id}")
    return (tx.type.value, tx.date.isoformat(), tx.cash.amount if tx.cash else None, tx.cash.code if tx.cash else None, identifier)


def _as_value_key(key: Optional[RowKey]) -> Optional[ValueKey]:
    if key is None:
        return None
    tx_type, day, amount, currency, identifier = key
    return (tx_type, day, Decimal(amount), currency, identifier)


def _charge_pairs(out: BRIMParseOutput) -> Tuple[Counter[Tuple[ValueKey, Optional[ValueKey]]], List[str]]:
    """Every charge of ``out`` with the row its ``parent_ref`` names (None when free), as a multiset; and what breaks a
    link besides the pair: a ``parent_ref`` naming no ``ref``, a charge without its parent's asset or broker."""
    by_ref = {tx.ref: tx for tx in out.transactions if tx.ref}
    pairs: Counter[Tuple[ValueKey, Optional[ValueKey]]] = Counter()
    problems: List[str] = []
    for tx in out.transactions:
        if tx.type not in charge_types():
            continue
        parent = by_ref.get(tx.parent_ref) if tx.parent_ref else None
        if tx.parent_ref and parent is None:
            problems.append(f"{_value_key(out, tx)} names {tx.parent_ref!r}, which is no ref of the output")
        if parent is not None and (parent.asset_id != tx.asset_id or parent.broker_id != tx.broker_id):
            problems.append(f"{_value_key(out, tx)}: asset/broker {tx.asset_id}/{tx.broker_id}, its parent's {parent.asset_id}/{parent.broker_id}")
        pairs[(_value_key(out, tx), _value_key(out, parent) if parent is not None else None)] += 1
    return pairs, problems


def assert_charge_pairs(out: BRIMParseOutput, label: str, expected: Sequence[Tuple[RowKey, Optional[RowKey]]]) -> None:
    """Fail unless the charges of ``out`` and the rows they name are exactly ``expected`` (a multiset)."""
    found, problems = _charge_pairs(out)
    wanted: Counter[Tuple[ValueKey, Optional[ValueKey]]] = Counter((_as_value_key(charge), _as_value_key(parent)) for charge, parent in expected)
    missing, extra = wanted - found, found - wanted
    problems += [f"expected, not found ({n}×): {pair[0]} → {pair[1]}" for pair, n in missing.items()]
    problems += [f"found, not expected ({n}×): {pair[0]} → {pair[1]}" for pair, n in extra.items()]
    assert not problems, f"{label}: {len(problems)} difference(s) in the charges and their parents:\n  " + "\n  ".join(problems)


class TestIbkrLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_each_commission_names_the_trade_of_its_row(self, sample: str):
        """RED before P4a: every commission names the trade of its row (contract §8, ibkr), and no other charge exists."""
        out = _plugin().parse(SAMPLE_DIR / sample, BROKER_ID)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert_charge_pairs(out, f"{PLUGIN_CODE} [{sample}]", EXPECTED[sample])

    def test_a_commission_in_another_currency_names_its_trade(self, tmp_path: Path):
        """RED before P4a. Rule 4: the currency of a charge is never judged — a CHF commission on a USD trade is linked.
        Invented row: the samples have no trade whose commission currency differs from the trade's."""
        path = _write(tmp_path, ['"BUY","20240301","US0378331005","3","180","540","USD","-1.5","CHF"'])

        out = _plugin().parse(path, BROKER_ID)

        assert out.validation_issues == [], out.validation_issues
        assert_expected_charge_links(out, "IBKR: CHF commission on a USD trade", linked=[(_fee("2024-03-01", "-1.5", "CHF", APPLE), _buy("2024-03-01", "-540", "USD", APPLE))], free=[])

    def test_a_refused_trade_leaves_its_commission_free(self, tmp_path: Path):
        """Guard: a trade the validation refuses (no ``TradeMoney``: ``cashRequired``) is not in the output, so its
        commission has no parent to name. It is still imported, free, with its own asset; it never names the trade of an
        earlier row of the same security, which is in the output just before it. Invented rows."""
        path = _write(
            tmp_path,
            [
                '"BUY","20240301","US0378331005","3","180","540","USD","-1.5","USD"',
                '"BUY","20240303","US0378331005","2","","","USD","-1","USD"',
            ],
        )

        out = _plugin().parse(path, BROKER_ID)

        assert [(issue.row, issue.code) for issue in out.validation_issues] == [(3, "cashRequired")], out.validation_issues
        assert [tx.type for tx in out.transactions] == [TransactionType.BUY, TransactionType.FEE, TransactionType.FEE], [tx.type for tx in out.transactions]
        # Not exhaustive: the commission of the valid trade is the subject of the other tests (linked after P4a).
        assert_expected_charge_links(out, "IBKR: refused trade", linked=[], free=[_fee("2024-03-03", "-1", "USD", APPLE)], exhaustive=False)

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
