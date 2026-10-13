"""
Gallery dashboard fixture normalizer (workstream I, lot I-M30, plan 54): ``scripts/normalize_dashboard_fixture.py``.

``frontend/e2e/dashboard-report.json`` is a real portfolio report, anonymized by scaling: every money figure is
multiplied by ``TARGET_NET_WORTH / net worth``, so that the net worth lands on 50 000, and nothing else moves. The script
recognizes money by its field name (``SCALE_NAME_RE``: ``value``, ``price``, ``amount``...), and three kinds of figure
that are not money, in four path families, carry such a name:

1. the allocation shares, ``summary.allocation_by_<dim>[*].value`` and
   ``allocation_history.<dim>[*].components[*].value``: percentages of their list's total, every item emitted and
   quantized to 2 decimals, so a list that is neither empty nor worth zero sums to 100 within ``0.005 * n``;
2. ``summary.holdings[*].yield_on_cost.value``: a fraction, ``gross_income_per_unit.amount / wac_per_unit`` when the
   status is ``available``;
3. ``summary.holdings[*].price_change_1d``: a fraction, for a holding valued at market price, whose magnitude times 100
   matches ``gain_loss_change_1d_percent`` within 0.0101 (two roundings of 0.005; magnitudes, for short positions).

Multiplied by the factor, they stop meaning what the dashboard says they mean. Proven here on synthetic reports under
``tmp_path``:

- at any ratio the four families come back string-equal and are never listed as scaled, while their money siblings
  (the allocation ``amount``s, the prices, ``wac_per_unit``, ``current_value``, ``gain_loss_change_1d``, the Currency
  ``gross_income_per_unit``, the net worth) are scaled, and quantities and percents are not;
- after the transform the script checks the three relations above. A violation prints a ``❌`` line naming the family
  and a count, never a figure (the real input is a user's data), returns 1 and writes nothing. Each check is proven on
  both sides of its tolerance, and on what it must skip: an empty list, a list worth zero, a yield that is not
  available, a holding not valued at market price, a null.

Then the committed fixture itself must pass its dry run and stay unwritten. It is read through the script only, and
asserted on a return code, a count and a digest, never on a figure: it is a real user snapshot.

PURE: synthetic reports and a copy of the fixture under ``tmp_path``; the repository is only read. No database, no
server, no network, no application import.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import re
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from scripts import normalize_dashboard_fixture as N

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "frontend" / "e2e" / "dashboard-report.json"
DIMENSIONS = ("type", "sector", "geography")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")

# (name, share, amount at the target): each list's shares sum to 100, its amounts to the net worth, 50 000.
SHARES = {
    "type": [("Stock", "47.31", "23655.00"), ("ETF", "38.52", "19260.00"), ("Bond", "14.17", "7085.00")],
    "sector": [("Technology", "61.84", "30920.00"), ("Unknown", "38.16", "19080.00")],
    "geography": [("US", "55.55", "27775.00"), ("IT", "29.47", "14735.00"), ("DE", "14.98", "7490.00")],
}
# Another day of history. Three thirds sum to 99.99: a rounding the check must accept.
DAY = {
    "type": [("Stock", "70.25", "35125.00"), ("ETF", "29.75", "14875.00")],
    "sector": [("Technology", "66.67", "33333.33"), ("Unknown", "33.33", "16666.67")],
    "geography": [("US", "33.33", "16666.67"), ("IT", "33.33", "16666.67"), ("DE", "33.33", "16666.66")],
}

# Paths with every index as ``[*]``. The four families that are not money...
NOT_MONEY = {
    *(f"summary.allocation_by_{dim}[*].value" for dim in DIMENSIONS),
    *(f"allocation_history.{dim}[*].components[*].value" for dim in DIMENSIONS),
    "summary.holdings[*].yield_on_cost.value",
    "summary.holdings[*].price_change_1d",
}
# ...their money siblings, which stay scaled...
MONEY = {
    "summary.net_worth.amount",
    *(f"summary.allocation_by_{dim}[*].amount" for dim in DIMENSIONS),
    *(f"allocation_history.{dim}[*].components[*].amount" for dim in DIMENSIONS),
    "summary.holdings[*].current_price",
    "summary.holdings[*].current_value",
    "summary.holdings[*].wac_per_unit",
    "summary.holdings[*].gain_loss_change_1d",
    "summary.holdings[*].yield_on_cost.provenance.gross_income_per_unit.amount",
}
# ...and figures the script never scaled, and must not start to.
UNSCALED = {"summary.holdings[*].quantity", "summary.holdings[*].gain_loss_change_1d_percent"}


def money(text: str, k: Decimal) -> str:
    """``text`` times ``k``, in the plain notation the script writes."""
    return f"{Decimal(text) * k:f}"


def allocation(rows: list[tuple[str, str, str]], k: Decimal) -> list[dict]:
    return [{"name": name, "value": share, "amount": money(amount, k), "emoji": None} for name, share, amount in rows]


def history(dim: str, k: Decimal) -> list[dict]:
    """A day like any other, a day without components, a day worth zero, and the day of the summary."""
    worth_zero = [(name, "0.00", "0") for name, _share, _amount in SHARES[dim]]
    return [
        {"date": "2025-12-28", "components": allocation(DAY[dim], k)},
        {"date": "2025-12-29", "components": []},
        {"date": "2025-12-30", "components": allocation(worth_zero, k)},
        {"date": "2025-12-31", "components": allocation(SHARES[dim], k)},
    ]


def yield_on_cost(status: str, value: str | None, gross: str | None, count: int, reason: str | None = None) -> dict:
    """``value`` is ``gross / wac_per_unit`` when ``available``, the quotient the backend writes."""
    return {
        "status": status,
        "value": value,
        "reason": reason,
        "provenance": {
            "source": "transactions",
            "window_start": "2025-01-01",
            "window_end": "2025-12-31",
            "first_pair_transaction_date": "2024-03-15",
            "gross_income_transaction_count": count,
            "gross_income_per_unit": None if gross is None else {"code": "EUR", "amount": gross},
            "net_zero": False,
            "fx": [],
            "issue_date": None,
            "issue_pair": None,
        },
    }


def holdings(k: Decimal) -> list[dict]:
    """A long position at market price with an available yield, a bond at its last trade price without income, and a
    short position at market price without a yield. ``current_value`` is ``quantity * current_price``, and
    ``price_change_1d * 100`` has the magnitude of ``gain_loss_change_1d_percent``."""
    return [
        {
            "asset_name": "Synthetic Equity A",
            "quantity": "100",
            "current_price": money("123.40", k),
            "current_value": money("12340.00", k),
            "wac_per_unit": money("62.50", k),
            "valuation_source": "MARKET_PRICE",
            "price_change_1d": "0.0137",
            "gain_loss_change_1d": money("166.77", k),
            "gain_loss_change_1d_percent": "1.37",
            "yield_on_cost": yield_on_cost("available", "0.04", money("2.50", k), 4),
        },
        {
            "asset_name": "Synthetic Bond B",
            "quantity": "50",
            "current_price": money("98.70", k),
            "current_value": money("4935.00", k),
            "wac_per_unit": money("97.10", k),
            "valuation_source": "LAST_TRADE_PRICE",
            "price_change_1d": None,
            "gain_loss_change_1d": None,
            "gain_loss_change_1d_percent": None,
            "yield_on_cost": yield_on_cost("no_income", "0", money("0", k), 0),
        },
        {
            "asset_name": "Synthetic Short C",
            "quantity": "-5",
            "current_price": money("210.00", k),
            "current_value": money("-1050.00", k),
            "wac_per_unit": money("215.00", k),
            "valuation_source": "MARKET_PRICE",
            "price_change_1d": "-0.0062",
            "gain_loss_change_1d": money("6.55", k),
            "gain_loss_change_1d_percent": "0.62",
            "yield_on_cost": yield_on_cost("unavailable", None, None, 0, reason="insufficient_history"),
        },
    ]


def make_report(k: Decimal = Decimal(1)) -> dict:
    """A report whose net worth is ``k`` times 50 000: its money times ``k``, everything else as at the target."""
    return {
        "summary": {
            "net_worth": {"code": "EUR", "amount": money("50000", k)},
            **{f"allocation_by_{dim}": allocation(SHARES[dim], k) for dim in DIMENSIONS},
            "holdings": holdings(k),
        },
        "allocation_history": {dim: history(dim, k) for dim in DIMENSIONS},
    }


def write_report(tmp_path: Path, report: dict) -> Path:
    path = tmp_path / "dashboard-report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def fingerprint(path: Path) -> tuple[str, int]:
    """Digest and modification time. The time also catches a write that puts the same bytes back, as one at ratio 1
    does (on any filesystem with sub-second timestamps)."""
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns


def leaves(node: object, path: str = "") -> dict[str, object]:
    """Every scalar under ``node``, by the path ``N._walk`` gives it: ``summary.holdings[0].quantity``."""
    found: dict[str, object] = {}
    if isinstance(node, dict):
        for key, child in node.items():
            found.update(leaves(child, f"{path}.{key}" if path else key))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            found.update(leaves(child, f"{path}[{index}]"))
    else:
        found[path] = node
    return found


def figures(report: dict) -> dict[str, str]:
    """The numeric strings: the only leaves the script may scale."""
    return {path: leaf for path, leaf in leaves(report).items() if isinstance(leaf, str) and NUMBER_RE.fullmatch(leaf)}


def family(path: str) -> str:
    return re.sub(r"\[\d+\]", "[*]", path)


def refusals(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith("❌")]


def at(report: dict, where: tuple[str | int, ...]) -> list:
    node = report
    for step in where:
        node = node[step]
    return node


def put_shares(items: list[dict], values: list[str], amounts: list[str] | None = None) -> None:
    """Rewrite one allocation list in place, item by item; no values empty it."""
    if not values:
        items.clear()
    kept = amounts if amounts is not None else [row["amount"] for row in items]
    for item, value, amount in zip(items, values, kept, strict=True):
        item["value"], item["amount"] = value, amount


# --- Scaling: money moves, the four families do not ---------------------------------------------------------------


def test_every_figure_of_the_synthetic_report_is_in_one_family_and_every_family_has_one():
    """Presence barrier for the tests below: no family they check is vacuous, and no figure escapes them."""
    assert not (NOT_MONEY & MONEY or NOT_MONEY & UNSCALED or MONEY & UNSCALED)
    assert {family(path) for path in figures(make_report())} == NOT_MONEY | MONEY | UNSCALED


def test_a_report_at_twice_the_target_is_halved_in_its_money_only(tmp_path, capsys):
    before = make_report(Decimal(2))
    path = write_report(tmp_path, before)

    assert N.normalize_file(path, False) == 0
    out = capsys.readouterr().out
    old, new = figures(before), figures(json.loads(path.read_text(encoding="utf-8")))

    assert new.keys() == old.keys()
    moved = sorted(p for p in old if family(p) in NOT_MONEY | UNSCALED and new[p] != old[p])
    assert moved == [], "scaled, though not money: a share, a yield on cost, a price change, a quantity or a percent"
    not_halved = sorted(p for p in old if family(p) in MONEY and Decimal(new[p]) != Decimal(old[p]) / 2)
    assert not_halved == [], "money that was not halved"
    assert Decimal(new["summary.net_worth.amount"]) == N.TARGET_NET_WORTH
    assert f"scaled {sum(family(p) in MONEY for p in old)} fields" in out


def test_walk_lists_the_money_and_never_a_share_a_yield_or_a_price_change():
    report = make_report()
    scaled: list[str] = []
    N._walk(copy.deepcopy(report), Decimal("0.5"), scaled)
    listed = {family(path) for path in scaled}

    assert sorted(listed & (NOT_MONEY | UNSCALED)) == []
    assert sorted(MONEY - listed) == []
    assert sorted(scaled) == sorted(path for path in figures(report) if family(path) in MONEY)


# --- Shares: every list sums to 100 --------------------------------------------------------------------------------

# The shares written below, their sums and their distances from 100: none may reach the output.
SHARE_FIGURES = ("43.21", "35.19", "12.97", "91.37", "8.63", "57.11", "31.04", "88.15", "11.85")


def test_shares_that_do_not_sum_to_100_are_refused_by_family_without_a_figure(tmp_path, capsys):
    report = make_report()
    put_shares(report["summary"]["allocation_by_type"], ["43.21", "35.19", "12.97"])
    put_shares(report["allocation_history"]["sector"][0]["components"], ["57.11", "31.04"])
    path = write_report(tmp_path, report)
    before = fingerprint(path)

    assert N.normalize_file(path, False) == 1
    out = capsys.readouterr().out
    refused = refusals(out)
    named = ("allocation_by_type", "allocation_history.sector")
    healthy = ("allocation_by_sector", "allocation_by_geography", "allocation_history.type", "allocation_history.geography")
    assert [name for name in named if not any(name in line for line in refused)] == []
    assert [name for name in healthy if any(name in line for line in refused)] == []
    assert [text for text in SHARE_FIGURES if text in out] == []
    assert fingerprint(path) == before


SHARE_LISTS = [
    pytest.param(("summary", "allocation_by_type"), "allocation_by_type", id="summary-list"),
    pytest.param(("allocation_history", "geography", 0, "components"), "allocation_history.geography", id="history-day"),
]
SHARE_CASES = [
    pytest.param(["33.34", "33.33", "33.34"], None, 0, id="100.01-accepted"),
    pytest.param(["33.33", "33.33", "33.33"], None, 0, id="99.99-accepted"),
    pytest.param(["33.34", "33.34", "33.34"], None, 1, id="100.02-refused"),
    pytest.param(["33.32", "33.33", "33.33"], None, 1, id="99.98-refused"),
    pytest.param([], None, 0, id="an-empty-list-skipped"),
    pytest.param(["0.00", "0.00", "0.00"], ["0", "0", "0"], 0, id="a-list-worth-zero-skipped"),
]


@pytest.mark.parametrize(("where", "named"), SHARE_LISTS)
@pytest.mark.parametrize(("values", "amounts", "code"), SHARE_CASES)
def test_a_share_list_may_miss_100_by_half_a_hundredth_per_item(tmp_path, capsys, where, named, values, amounts, code):
    """Three shares quantized to 2 decimals round by at most 0.005 each: within 0.015 of 100 is rounding, beyond it
    the list was scaled. An empty list, or one worth zero, has no share to sum."""
    report = make_report()
    put_shares(at(report, where), values, amounts)
    path = write_report(tmp_path, report)
    before = fingerprint(path)

    assert N.normalize_file(path, False) == code
    refused = refusals(capsys.readouterr().out)
    if code == 0:
        assert refused == []
    else:
        assert any(named in line for line in refused), refused
        assert fingerprint(path) == before


# --- Yield on cost: an available value is gross income over WAC ----------------------------------------------------


def test_an_available_yield_on_cost_that_is_not_gross_over_wac_is_refused_without_a_figure(tmp_path, capsys):
    report = make_report()
    report["summary"]["holdings"][0]["yield_on_cost"]["value"] = "0.0437"  # gross 2.50 / wac 62.50 is 0.04
    path = write_report(tmp_path, report)
    before = fingerprint(path)

    assert N.normalize_file(path, False) == 1
    out = capsys.readouterr().out
    assert any("yield_on_cost" in line for line in refusals(out)), out
    assert [text for text in ("0.0437", "4.37", "0.04", "2.50", "62.50") if text in out] == []
    assert fingerprint(path) == before


@pytest.mark.parametrize(
    ("value", "code"),
    [
        pytest.param("0.3333333333333333333333333333", 0, id="the-quotient-as-the-backend-writes-it"),
        pytest.param("0.3333334", 0, id="within-a-millionth"),
        pytest.param("0.33333", 1, id="beyond-a-millionth"),
    ],
)
def test_a_yield_on_cost_matches_gross_over_wac_within_a_millionth(tmp_path, capsys, value, code):
    """The backend writes the quotient unquantized: 1 / 3 carries every digit ``Decimal`` holds."""
    report = make_report()
    held = report["summary"]["holdings"][0]
    held["wac_per_unit"] = "3.00"
    held["yield_on_cost"]["provenance"]["gross_income_per_unit"]["amount"] = "1.00"
    held["yield_on_cost"]["value"] = value
    path = write_report(tmp_path, report)

    assert N.normalize_file(path, False) == code
    refused = refusals(capsys.readouterr().out)
    if code == 0:
        assert refused == []
    else:
        assert any("yield_on_cost" in line for line in refused), refused


# --- Price change: at market price, the fraction of the percent ----------------------------------------------------


def test_a_market_price_change_that_disagrees_with_its_percent_is_refused_without_a_figure(tmp_path, capsys):
    report = make_report()
    report["summary"]["holdings"][0]["price_change_1d"] = "0.0291"  # gain_loss_change_1d_percent stays 1.37
    path = write_report(tmp_path, report)
    before = fingerprint(path)

    assert N.normalize_file(path, False) == 1
    out = capsys.readouterr().out
    assert any("price_change_1d" in line for line in refusals(out)), out
    assert [text for text in ("0.0291", "2.91", "1.37", "0.0137", "1.54") if text in out] == []
    assert fingerprint(path) == before


@pytest.mark.parametrize(
    ("index", "change", "code"),
    [
        pytest.param(0, "0.0138", 0, id="long-a-hundredth-off-accepted"),
        pytest.param(0, "0.0139", 1, id="long-two-hundredths-off-refused"),
        pytest.param(2, "-0.0063", 0, id="short-a-hundredth-off-accepted"),
        pytest.param(2, "-0.0064", 1, id="short-two-hundredths-off-refused"),
    ],
)
def test_a_price_change_may_miss_its_percent_by_two_roundings(tmp_path, capsys, index, change, code):
    """``price_change_1d`` is rounded to 4 decimals and the percent to 2: times 100 they may differ by 0.005 + 0.005,
    compared by magnitude, since a short position gains when the price falls."""
    report = make_report()
    report["summary"]["holdings"][index]["price_change_1d"] = change
    path = write_report(tmp_path, report)

    assert N.normalize_file(path, False) == code
    refused = refusals(capsys.readouterr().out)
    if code == 0:
        assert refused == []
    else:
        assert any("price_change_1d" in line for line in refused), refused


@pytest.mark.parametrize(
    ("index", "changes"),
    [
        pytest.param(1, {"price_change_1d": "0.0291", "gain_loss_change_1d_percent": "1.37"}, id="a-holding-at-its-last-trade-price"),
        pytest.param(0, {"price_change_1d": "0.0291", "gain_loss_change_1d_percent": None}, id="a-null-percent"),
        pytest.param(0, {"price_change_1d": None}, id="a-null-price-change"),
    ],
)
def test_a_price_change_is_compared_only_at_market_price_and_with_both_figures(tmp_path, capsys, index, changes):
    report = make_report()
    report["summary"]["holdings"][index].update(changes)
    path = write_report(tmp_path, report)

    assert N.normalize_file(path, False) == 0
    assert refusals(capsys.readouterr().out) == []


# --- The committed fixture -----------------------------------------------------------------------------------------


def test_the_committed_fixture_passes_its_dry_run_and_is_not_written(tmp_path):
    """The repository's own snapshot, through the script that anonymized it.

    Expected for lot I-M30: GREEN while the script lacks the three checks above; RED once it has them and until the
    fixture is repaired, because the committed shares, yields on cost and price changes were scaled by the factor;
    GREEN after the repair.

    The output describes a real user's data (a refusal may quote a figure), so neither stream reaches pytest's capture,
    which would replay it on a failure: only the ``❌`` lines are counted. Asserted on the return code, that count and a
    digest, never on a figure.
    """
    assert FIXTURE.is_file(), "presence barrier: frontend/e2e/dashboard-report.json is missing"
    fixture = tmp_path / "dashboard-report.json"
    shutil.copyfile(FIXTURE, fixture)
    before = fingerprint(fixture)

    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(out):
        code = N.normalize_file(fixture, dry_run=True)
    refused = len(refusals(out.getvalue()))
    unchanged = fingerprint(fixture) == before

    assert code == 0 and refused == 0, f"the committed fixture fails {refused} of the normalizer's checks: read them with `./dev.py mkdocs normalize-dashboard-fixture --dry-run`, fix the script's path exceptions (plan 54) and re-normalize; never edit the fixture by hand"
    assert unchanged, "the dry run wrote the file"
