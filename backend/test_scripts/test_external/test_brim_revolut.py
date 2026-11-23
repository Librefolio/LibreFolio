"""
Test Suite: the Revolut plugin — ``broker_revolut``, its linked charges (project 66, lot P4a)

Revolut writes two exports, both read by the plugin: «Invest» (stocks) and «Crypto». The rest of Revolut (helpers, rows
left out, stock splits) is pinned in ``test_brim_providers.py``, ``test_brim_row_skips.py`` and
``test_brim_economic_rows.py``. This module pins what lot P4a adds, from the P2 contract (§2, §8) and the decisions of
16/11 (``domande-FEE.md``, «Plugin per plugin»):

- **Crypto:** the ``Fees`` column of a buy or sell row is a FEE that names the trade of that row as its parent
  (``parent_ref`` = the trade's ``ref``), on its broker. Today the plugin emits that FEE **without an asset**; linked, it
  **takes the parent's asset** (``_create_linked_charge`` fills an asset the plugin left out, never one it passed). The
  fee may be in another currency than the trade (rule 4: never judged).
- **Invest:** a «CUSTODY FEE» row is an account charge, its own row with no operation: it stays free, with or without a
  ticker.
- A trade the validation refuses is not in the output, so its fee has no parent: it is imported, free and without an
  asset, as today — never linked to the previous trade of the same coin.
- **Only the names change — with one exception, written down here (contract §8, rule 7).** Every row equals the previous
  version's (snapshot taken at HEAD a2e85db13, plugin 1.3.0) except ``ref``/``parent_ref`` and, for a crypto FEE the
  previous version emitted without an asset, ``asset_id``: it gains the asset of the trade it names, and nothing else
  changes. The reimport still recognises those fees: a saved row without an asset stays a duplicate candidate of an
  incoming one with an asset (``detect_tx_duplicates``, the branch ``asset_id == real OR asset_id IS NULL``), so
  reimporting either sample over the previous version's rows adds nothing.
- The plugin version goes up.

Not tested here (amounts are not P4's): the Invest sample's sale of 2023-07-14 differs by 0.02 from quantity × price
(0.1998348 × 402.13 = 80.36, ``Total Amount`` 80.34) and the file has no fee column (doubt 6 of the census): a charge
inside the total, or a rounded price.

Red before the code change: the expected crypto links (sample and invented rows), the asset the crypto fees gain, and
the version. Green before and after (guards): the custody fees stay free, the refused trade's fee stays free, the
structure, the snapshot comparison with its one exception, the reimport.

The only ADJUSTMENT the plugin emits is an Invest stock split, which carries no charge (rule 6 has no case in Revolut).

Every input is a sample of ``sample_reports/`` or a file written in ``tmp_path`` (invented values). The reimport opens a
private in-memory SQLite per test and disposes it: no server, no shared database.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

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
    assert_sample_reimport_adds_nothing,
    changes_besides_links,
    load_previous_snapshot,
    version_tuple,
)
from backend.test_scripts.brim_samples import SampleDir

PLUGIN_CODE = "broker_revolut"
SAMPLE_DIR = SampleDir()
CRYPTO_SAMPLE = "revolut-crypto-export.csv"
INVEST_SAMPLE = "revolut-invest-export.csv"
# Not 1: every row must carry the broker parse was given, and the snapshot is rebuilt on the same one.
BROKER_ID = 7

CRYPTO_HEADER = "Symbol,Type,Quantity,Price,Value,Fees,Date"
INVEST_HEADER = "Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency,FX Rate"


def _row(tx_type: str, day: str, amount: str, currency: str, symbol: str | None) -> RowKey:
    return (tx_type, day, amount, currency, symbol)


#: Per sample: (linked (charge, parent), free charges). Every FEE/TAX of the output must be in one of the two. A crypto
#: FEE is keyed by the coin of its trade: the asset it gains with the link (none before P4a, so "0 rows match" today).
EXPECTED: Dict[str, Tuple[List[Tuple[RowKey, RowKey]], List[RowKey]]] = {
    CRYPTO_SAMPLE: (
        [
            (_row("FEE", "2022-03-08", "-0.24", "EUR", "BTC"), _row("BUY", "2022-03-08", "-10.00", "EUR", "BTC")),
            (_row("FEE", "2024-02-09", "-0.14", "EUR", "ETH"), _row("BUY", "2024-02-09", "-10.00", "EUR", "ETH")),
            (_row("FEE", "2025-05-09", "-0.24", "USD", "BTC"), _row("BUY", "2025-05-09", "-10.00", "USD", "BTC")),
        ],
        [],
    ),
    # The custody fee: an account charge, no ticker, no parent.
    INVEST_SAMPLE: ([], [_row("FEE", "2021-09-01", "-0.01", "USD", None)]),
}
SAMPLES = tuple(EXPECTED)
#: The crypto fees the previous version emitted without an asset: by P4a each gains its trade's (rule 7's exception).
CRYPTO_FEES_GAINING_AN_ASSET = {CRYPTO_SAMPLE: 3, INVEST_SAMPLE: 0}


def _plugin() -> BRIMProvider:
    """The registered plugin; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _write(tmp_path: Path, header: str, rows: Sequence[str]) -> Path:
    path = tmp_path / "revolut-linked.csv"
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def _changed_fields(before: TXCreateItem, after: TXCreateItem) -> Set[str]:
    old, new = (tx.model_dump(mode="json", exclude=set(LINK_FIELDS)) for tx in (before, after))
    return {field for field in old if old[field] != new[field]}


def _asset_fills(previous: Sequence[TXCreateItem], current: Sequence[TXCreateItem]) -> Tuple[List[int], List[str]]:
    """The indices of the rows where the one allowed exception happened — a FEE the previous version emitted without an
    asset, now with the asset of the row its ``parent_ref`` names, and no other field changed — and the problems of any
    row that gained an asset otherwise (no parent, another asset, another field changed too)."""
    by_ref = {tx.ref: tx for tx in current if tx.ref}
    fills: List[int] = []
    problems: List[str] = []
    for index, (before, after) in enumerate(zip(previous, current, strict=False)):
        if not (before.asset_id is None and after.asset_id is not None):
            continue
        parent = by_ref.get(after.parent_ref) if after.parent_ref else None
        if before.type != TransactionType.FEE or after.type != TransactionType.FEE:
            problems.append(f"#{index} {before.type.value} {before.date}: gained an asset, and is not a FEE")
        elif parent is None:
            problems.append(f"#{index} FEE {before.date}: gained asset {after.asset_id} without naming a parent")
        elif parent.asset_id != after.asset_id:
            problems.append(f"#{index} FEE {before.date}: gained asset {after.asset_id}, its parent's is {parent.asset_id}")
        elif _changed_fields(before, after) != {"asset_id"}:
            problems.append(f"#{index} FEE {before.date}: changed {sorted(_changed_fields(before, after))}, only asset_id may")
        else:
            fills.append(index)
    return fills, problems


def _without_the_fills(current: Sequence[TXCreateItem], fills: Sequence[int]) -> List[TXCreateItem]:
    """``current`` with the filled assets taken off again: what the comparison with the snapshot must find equal."""
    return [tx.model_copy(update={"asset_id": None}) if index in fills else tx for index, tx in enumerate(current)]


def _parse(path: Path) -> BRIMParseOutput:
    return _plugin().parse(path, BROKER_ID)


class TestRevolutLinkedCharges:
    @pytest.mark.parametrize("sample", SAMPLES)
    def test_each_crypto_fee_names_its_trade_and_the_custody_fee_stays_free(self, sample: str):
        """RED before P4a (crypto): every ``Fees`` FEE names the trade of its row and carries its coin. Green before and
        after (invest): the custody fee names nothing."""
        linked, free = EXPECTED[sample]
        out = _parse(SAMPLE_DIR / sample)

        assert out.validation_issues == [], f"{sample}: {out.validation_issues}"
        assert_expected_charge_links(out, f"{PLUGIN_CODE} [{sample}]", linked=linked, free=free)

    def test_a_crypto_fee_in_another_currency_and_on_a_sale_names_its_trade(self, tmp_path: Path):
        """RED before P4a. Rule 4: a USD fee on a EUR buy is linked (the currency is never judged); the fee of a sale names
        the sale. Both take their trade's coin. Invented rows: the sample has only buys, each fee in its trade's currency."""
        path = _write(
            tmp_path,
            CRYPTO_HEADER,
            [
                'BTC,Buy,0.0001,"€60,000.00",€6.00,$0.10,"Mar 8, 2024, 2:08:54 PM"',
                'ETH,Sell,0.002,"€3,000.00",€6.00,€0.09,"Mar 9, 2024, 2:08:54 PM"',
            ],
        )

        out = _parse(path)

        assert out.validation_issues == [], out.validation_issues
        assert_expected_charge_links(
            out,
            "Revolut crypto: invented",
            linked=[
                (_row("FEE", "2024-03-08", "-0.10", "USD", "BTC"), _row("BUY", "2024-03-08", "-6.00", "EUR", "BTC")),
                (_row("FEE", "2024-03-09", "-0.09", "EUR", "ETH"), _row("SELL", "2024-03-09", "6.00", "EUR", "ETH")),
            ],
            free=[],
        )

    def test_a_refused_crypto_trade_leaves_its_fee_free_and_without_an_asset(self, tmp_path: Path):
        """Guard: a buy the validation refuses (``Quantity`` 0: ``qtyPositive``) is not in the output, so its fee has no
        parent to name and no asset to take. It is still imported, free and without an asset, as today; it never names the
        buy of an earlier row of the same coin, which is in the output just before it. Invented rows."""
        path = _write(
            tmp_path,
            CRYPTO_HEADER,
            [
                'BTC,Buy,0.0001,"€60,000.00",€6.00,€0.08,"Mar 8, 2024, 2:08:54 PM"',
                'BTC,Buy,0,"€60,000.00",€6.00,€0.11,"Mar 10, 2024, 2:08:54 PM"',
            ],
        )

        out = _parse(path)

        assert [(issue.row, issue.code) for issue in out.validation_issues] == [(3, "qtyPositive")], out.validation_issues
        assert [tx.type.value for tx in out.transactions] == ["BUY", "FEE", "FEE"], [tx.type.value for tx in out.transactions]
        # Not exhaustive: the fee of the valid buy is linked after P4a, the subject of the other tests.
        assert_expected_charge_links(out, "Revolut crypto: refused buy", linked=[], free=[_row("FEE", "2024-03-10", "-0.11", "EUR", None)], exhaustive=False)

    def test_a_custody_fee_with_a_ticker_stays_free(self, tmp_path: Path):
        """Guard (contract §8, revolut): a «CUSTODY FEE» row is an account charge — even with a ticker, the day after a buy
        of that ticker, it names nothing and keeps its own asset. Invented rows."""
        path = _write(
            tmp_path,
            INVEST_HEADER,
            [
                "2024-03-01T08:00:00.000Z,AAPL,BUY - MARKET,1,$180,$180,USD,1.08",
                "2024-03-02T08:00:00.000Z,AAPL,CUSTODY FEE,,,-$0.02,USD,1.08",
            ],
        )

        out = _parse(path)

        assert out.validation_issues == [], out.validation_issues
        assert_expected_charge_links(out, "Revolut invest: custody fee with a ticker", linked=[], free=[_row("FEE", "2024-03-02", "-0.02", "USD", "AAPL")])

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_crypto_fees_gain_their_trades_asset_and_nothing_else(self, sample: str):
        """RED before P4a (crypto): rule 7's exception, stated on its own — the three crypto fees of the sample, emitted
        without an asset by the previous version, now carry the asset of the trade they name, and no other field of theirs
        changes. Green before and after (invest): no row gains an asset."""
        previous = load_previous_snapshot(PLUGIN_CODE, sample, BROKER_ID)
        out = _parse(SAMPLE_DIR / sample)

        fills, problems = _asset_fills(previous.transactions, out.transactions)
        assert not problems, f"{sample}: an asset gained outside the rule:\n  " + "\n  ".join(problems)
        assert len(fills) == CRYPTO_FEES_GAINING_AN_ASSET[sample], f"{sample}: {len(fills)} fee(s) gained their trade's asset, expected {CRYPTO_FEES_GAINING_AN_ASSET[sample]} (rows {fills})"

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_the_links_are_well_formed(self, sample: str):
        """Guard: every ``ref`` unique, every ``parent_ref`` names a ``ref`` of the output (vacuous before P4a)."""
        assert_charge_link_structure(_parse(SAMPLE_DIR / sample), f"{PLUGIN_CODE} [{sample}]")

    @pytest.mark.parametrize("sample", SAMPLES)
    def test_only_the_names_change_from_the_previous_version_besides_the_filled_assets(self, sample: str):
        """Guard: every row equals the snapshot's, in order, but for ``ref``/``parent_ref`` — and for the asset a crypto
        fee takes from the trade it names (rule 7's exception, checked field by field by ``_asset_fills``): with those
        assets taken off again, nothing differs (type, date, quantity, cash, broker, description, tags)."""
        previous = load_previous_snapshot(PLUGIN_CODE, sample, BROKER_ID)
        out = _parse(SAMPLE_DIR / sample)

        fills, problems = _asset_fills(previous.transactions, out.transactions)
        problems += changes_besides_links(previous.transactions, _without_the_fills(out.transactions, fills))
        assert not problems, f"{sample}: the output changed besides its links (snapshot HEAD {previous.source_head}):\n  " + "\n  ".join(problems)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("sample", SAMPLES)
    async def test_reimport_over_the_previous_version_adds_nothing(self, sample: str):
        """Guard (P2 contract §2.1, §8): the sample, reimported over the rows the previous version saved (without links,
        the crypto fees without an asset), adds no row — a fee that gained its trade's asset is still recognised."""
        out = await assert_sample_reimport_adds_nothing(_plugin(), sample)

        assert out.transactions, f"{sample}: the criterion ran on an empty output"

    def test_the_version_is_above_the_previous_one(self):
        """RED before P4a: every touched plugin goes up a version (contract §8)."""
        plugin = _plugin()
        for sample in SAMPLES:
            previous = load_previous_snapshot(PLUGIN_CODE, sample, BROKER_ID)
            assert version_tuple(plugin.plugin_version) > version_tuple(previous.plugin_version), f"{PLUGIN_CODE} {plugin.plugin_version}: not above the snapshot's {previous.plugin_version} ({sample})"
