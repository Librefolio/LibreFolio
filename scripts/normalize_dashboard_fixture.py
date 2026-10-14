#!/usr/bin/env python3
"""Normalize the gallery dashboard fixture to a fixed net worth (anonymization).

`frontend/e2e/dashboard-report.json` is a REAL user capture committed to the repo.
To keep it useful but anonymous, every monetary figure is rescaled so the total net
worth lands on TARGET_NET_WORTH (50,000). Ratios, percentages, quantities, dates,
ids and counts are scale-invariant and are left untouched.

Policy (keep this logic stable; if the report schema evolves, extend the lists —
see `.github/agents/test-author.agent.md` rule 12 and the frontend-testing rules):

- Currency objects `{"code": ..., "amount": ...}` → amount × ratio.
- Plain numeric strings under MONEY-ish field names (see SCALE_NAME_RE) → × ratio.
  This covers per-unit prices (`current_price`, `wac_per_unit`), so that
  `value ≈ price × quantity` stays coherent while `quantity` is never scaled.
- Plain numeric strings under ratio/percent/count/id/date-ish names
  (see NEVER_SCALE_RE) → untouched.
- Plain numeric strings at the paths of NOT_MONEY_PATH_RE → untouched, checked
  before the names. They carry a money-like name but are not money: the allocation
  shares (`allocation_by_<dim>[*].value`, `allocation_history.<dim>[*].components[*].value`,
  percentages of their list's total), the yield on cost (`yield_on_cost.value`) and
  the one-day price change (`holdings[*].price_change_1d`), both fractions. Scaled,
  they stop meaning what the dashboard says they mean (plan 54, lot I-M30).

After the transform the script verifies its invariants and exits 1 on violation,
writing nothing:
- net worth equals the target, and per-holding value ≈ price × quantity;
- every allocation list that is neither empty nor worth zero sums to 100, within
  the rounding of its 2-decimal shares;
- every available yield on cost equals gross_income_per_unit / wac_per_unit;
- every one-day price change at market price is, in magnitude, a hundredth of
  gain_loss_change_1d_percent, within their two roundings.
The last three checks print a path family and a count, never a figure: the input
is a real user's report.

Capturing a fresh snapshot (the developer does it, from a recent build whose report
schema matches the code; never invent or patch fields):

1. Log in on that build, then in the browser console (DevTools) run, with your own
   broker ids, the last year ending today, and EUR:

       const lfPayload = {include_summary:true, include_history:true, include_allocation_history:true,
         include_breakdown:true, include_positions_contribution:true, include_broker_pnl_history:true,
         include_pnl_candles:true, include_income_history:true, include_cost_history:true,
         include_deposit_history:true, include_acquisition_funding:true, broker_ids:[2,1],
         date_range:{start:'2025-10-07', end:'2026-10-07'}, target_currency:'EUR'};
       const lfRes = await fetch('/api/v1/portfolio/report', {method:'POST', credentials:'include',
         headers:{'Content-Type':'application/json'}, body: JSON.stringify(lfPayload)});
       window.lfReport = await lfRes.json();

   then, as a SEPARATE console command (Chrome does not define `copy()` inside a block
   that uses `await`: "ReferenceError: copy is not defined"):

       copy(JSON.stringify(window.lfReport))

   Alternatively copy the response of that POST from the Network panel (Response tab).
   One snapshot with every section on, so the gallery serves it to every report request
   (main view, positions tab, P&L candles) and the shots stay coherent. Use at least two
   brokers: the per-broker P&L overlay needs them.
2. Paste the clipboard into a file OUTSIDE the repository (e.g. /tmp/…_raw.json).
3. Normalize that file with this script (`--dry-run` first), check that every money
   field moved by the same factor, validate it against the generated Zod
   `PortfolioReportResponse`, and only then copy it to `frontend/e2e/dashboard-report.json`.
   Delete the raw file afterwards. The Vitest guard `src/lib/api/dashboardReportFixture.test.ts`
   fails in seconds if the fixture stops matching the schema.
"""

import argparse
import json
import re
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

TARGET_NET_WORTH = Decimal("50000")

# Field names whose plain-string numbers are money → scale them.
# `gross_gains` / `gross_losses` / `period_unrealized_delta` are plain-number money in
# `positions_contribution` (captured since the single all-sections snapshot).
SCALE_NAME_RE = re.compile(
    r"(?:^|_)(value|price|amount|cost|cash|nav|income|fee|fees|tax|taxes|deposit|deposited|" r"withdrawn|withdrawal|pnl|capital|book|baseline|flow|flows|result|contribution|invested|" r"gain_loss|gain|gains|loss|losses|wac)(?:$|_)" r"|^period_unrealized_delta$",
    re.IGNORECASE,
)

# Field names whose numbers must never be scaled (ratios, percents, counts, ids, dates).
NEVER_SCALE_RE = re.compile(
    r"(?:^|_)(percent|rate|ratio|weight|count|days|id|date|quantity|qty|units|year|month)(?:$|_)" r"|^(mwrr|twrr|roi|mwrr_annualized|mwrr_cumulative|mwrr_annualized_percent|" r"mwrr_cumulative_percent|twrr_percent|simple_roi_percent)$",
    re.IGNORECASE,
)

# Paths of plain numbers with a money-like name that are not money, matched with every
# list index written as `[*]`: the allocation shares and two fractions (see the docstring).
NOT_MONEY_PATH_RE = re.compile(r"(?:^|\.)allocation_by_\w+\[\*\]\.value$" r"|(?:^|\.)allocation_history\.\w+\[\*\]\.components\[\*\]\.value$" r"|(?:^|\.)yield_on_cost\.value$" r"|(?:^|\.)holdings\[\*\]\.price_change_1d$")
LIST_INDEX_RE = re.compile(r"\[\d+\]")

# Each share is quantized to 0.01: a list of n shares misses 100 by at most 0.005 × n.
SHARE_ROUNDING_PER_ITEM = Decimal("0.005")
# The backend writes the yield on cost unquantized: only Decimal's precision separates it from the quotient.
YIELD_ON_COST_RELATIVE_TOLERANCE = Decimal("1e-6")
# price_change_1d is quantized to 4 decimals and the percent to 2: times 100, two roundings of 0.005.
PRICE_CHANGE_TOLERANCE = Decimal("0.0101")
SCHEMA_HINT = "schema changed? Update this script (same logic)."

CURRENCY_AMOUNT_RE = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")


def _is_number_str(v: object) -> bool:
    return isinstance(v, str) and CURRENCY_AMOUNT_RE.match(v) is not None


def _scale(value: str, ratio: Decimal) -> str:
    # Fixed-point rendering: never scientific notation ("5E+4") — Zod/JSON consumers
    # and human readers expect plain decimals.
    return f"{(Decimal(value) * ratio):f}"


def _walk(node: object, ratio: Decimal, scaled: list[str], path: str = "") -> object:
    """Recursively scale money in place-shaped copies. Returns the transformed node."""
    if isinstance(node, dict):
        # Currency object: {"code": "EUR", "amount": "123.45"}
        if set(node.keys()) >= {"code", "amount"} and _is_number_str(node.get("amount")):
            node["amount"] = _scale(node["amount"], ratio)
            scaled.append(f"{path}.amount")
            return node
        for key, val in node.items():
            child_path = f"{path}.{key}" if path else key
            if _is_number_str(val):
                if NEVER_SCALE_RE.search(key):
                    continue  # percent / ratio / id / quantity — scale-invariant
                if NOT_MONEY_PATH_RE.search(LIST_INDEX_RE.sub("[*]", child_path)):
                    continue  # a share or a fraction under a money-like name
                if SCALE_NAME_RE.search(key):
                    node[key] = _scale(val, ratio)
                    scaled.append(child_path)
                # unknown plain numbers are left alone on purpose (fail-safe)
            else:
                node[key] = _walk(val, ratio, scaled, child_path)
        return node
    if isinstance(node, list):
        for i, item in enumerate(node):
            node[i] = _walk(item, ratio, scaled, f"{path}[{i}]")
        return node
    return node


def _holding_relations(data: dict) -> dict[str, Decimal]:
    """Per-holding ratio value/(qty×price) — captures quoting conventions (e.g. bonds
    quoted per-100) so the check below validates *consistency*, not an absolute formula."""
    relations: dict[str, Decimal] = {}
    for h in (data.get("summary") or {}).get("holdings") or []:
        try:
            qty = Decimal(h["quantity"])
            price = Decimal(h["current_price"])
            raw_value = h["current_value"]
            value = Decimal(raw_value["amount"] if isinstance(raw_value, dict) else raw_value)
        except (KeyError, TypeError) as e:
            raise ValueError(f"holding {h.get('asset_name', '?')}: expected quantity/current_price/current_value fields ({e}) — schema changed?") from e
        if qty and price:
            relations[h.get("asset_name", "?")] = value / (qty * price)
    return relations


def _verify(data: dict, before_relations: dict[str, Decimal]) -> list[str]:
    """Invariant checks — a schema drift should fail HERE, loudly, not in a red screenshot."""
    errors: list[str] = []
    summary = data.get("summary") or {}
    net_worth = (summary.get("net_worth") or {}).get("amount")
    if net_worth is None:
        errors.append("summary.net_worth.amount not found — schema changed? Update this script (same logic).")
    elif abs(Decimal(net_worth) - TARGET_NET_WORTH) > Decimal("0.01"):
        errors.append(f"net_worth after normalization is {net_worth}, expected {TARGET_NET_WORTH}")

    for name, rel in _holding_relations(data).items():
        before = before_relations.get(name)
        if before is None:
            continue
        if before == 0:
            if rel != 0:
                errors.append(f"holding {name}: relation changed 0 → {rel}")
        elif abs(rel / before - 1) > Decimal("0.0001"):
            errors.append(f"holding {name}: value/(qty×price) drifted from {before} to {rel} after scaling")

    holdings = summary.get("holdings") or []
    errors += _share_errors(data)
    errors += _yield_on_cost_errors(holdings)
    errors += _price_change_errors(holdings)
    return errors


def _number(node: object) -> Decimal | None:
    """A plain numeric string, or the amount of a Currency object; None for anything else."""
    if isinstance(node, dict):
        node = node.get("amount")
    return Decimal(node) if _is_number_str(node) else None


def _allocation_lists(data: dict) -> dict[str, list[object]] | None:
    """Every allocation list, by path family: the summary's, then each day's of the history. None without the summary's."""
    families: dict[str, list[object]] = {}
    for key, items in (data.get("summary") or {}).items():
        if key.startswith("allocation_by_"):
            families.setdefault(f"summary.{key}", []).append(items)
    if not families:
        return None
    for dim, days in (data.get("allocation_history") or {}).items():
        lists = families.setdefault(f"allocation_history.{dim}", [])
        for day in days if isinstance(days, list) else [days]:
            lists.append(day.get("components") if isinstance(day, dict) and "components" in day else None)
    return families


def _share_verdict(items: object) -> str:
    """`skipped` (empty, or worth zero: the backend then divides by 1), `malformed`, `refused` or `accepted`."""
    if items == []:
        return "skipped"
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        return "malformed"
    shares = [_number(item.get("value")) for item in items]
    amounts = [_number(item.get("amount")) for item in items]
    if any(number is None for number in shares + amounts):
        return "malformed"
    if sum(amounts) == 0:
        return "skipped"
    return "refused" if abs(sum(shares) - 100) > SHARE_ROUNDING_PER_ITEM * len(items) else "accepted"


def _share_errors(data: dict) -> list[str]:
    """Every allocation list that is neither empty nor worth zero sums to 100, within the rounding of its shares.

    The backend emits every item, `amount / total × 100` quantized to 0.01 (`total` is 1 for a list worth zero).
    Value-free: one line per failing path family, with a count."""
    families = _allocation_lists(data)
    if families is None:
        return [f"summary.allocation_by_* not found — {SCHEMA_HINT}"]
    errors: list[str] = []
    for family, lists in families.items():
        verdicts = Counter(_share_verdict(items) for items in lists)
        if verdicts["malformed"]:
            errors.append(f"{family}: {verdicts['malformed']} allocation list(s) without numeric shares and amounts — {SCHEMA_HINT}")
        if verdicts["refused"]:
            checked = verdicts["refused"] + verdicts["accepted"]
            errors.append(f"{family}: the shares of {verdicts['refused']} of {checked} allocation list(s) do not sum to 100 within rounding — scaled as money? A share is a percentage: see NOT_MONEY_PATH_RE.")
    return errors


def _yield_on_cost_errors(holdings: list) -> list[str]:
    """Every available yield on cost is gross_income_per_unit / wac_per_unit (yield_on_cost.py). Value-free."""
    checked = refused = malformed = 0
    for holding in holdings:
        yoc = holding.get("yield_on_cost") if isinstance(holding, dict) else None
        if not isinstance(yoc, dict):
            malformed += 1
            continue
        if yoc.get("status") != "available":
            continue  # no_income and unavailable carry no quotient
        value = _number(yoc.get("value"))
        gross = _number((yoc.get("provenance") or {}).get("gross_income_per_unit"))
        wac = _number(holding.get("wac_per_unit"))
        if value is None or gross is None or not wac:
            malformed += 1
            continue
        checked += 1
        expected = gross / wac
        if abs(value - expected) > YIELD_ON_COST_RELATIVE_TOLERANCE * abs(expected):
            refused += 1
    errors: list[str] = []
    if malformed:
        errors.append(f"summary.holdings[*].yield_on_cost: {malformed} holding(s) without a yield on cost, or with an available one lacking its value, gross income per unit or a non-zero wac_per_unit — {SCHEMA_HINT}")
    if refused:
        errors.append(f"summary.holdings[*].yield_on_cost: {refused} of {checked} available yield(s) on cost differ from gross_income_per_unit / wac_per_unit — scaled as money? A yield on cost is a fraction: see NOT_MONEY_PATH_RE.")
    return errors


def _price_change_errors(holdings: list) -> list[str]:
    """At market price, |price_change_1d × 100| matches |gain_loss_change_1d_percent| within two roundings.

    Both come from the same quantity and the same two prices (portfolio_service.py); magnitudes, because a short
    position gains when the price falls. Value-free."""
    checked = refused = 0
    for holding in holdings:
        if not isinstance(holding, dict) or holding.get("valuation_source") != "MARKET_PRICE":
            continue
        change = _number(holding.get("price_change_1d"))
        percent = _number(holding.get("gain_loss_change_1d_percent"))
        if change is None or percent is None:
            continue
        checked += 1
        if abs(abs(change * 100) - abs(percent)) > PRICE_CHANGE_TOLERANCE:
            refused += 1
    if not refused:
        return []
    return [f"summary.holdings[*].price_change_1d: {refused} of {checked} market-price holding(s) have a one-day price change that is not a hundredth of gain_loss_change_1d_percent — scaled as money? A price change is a fraction: see NOT_MONEY_PATH_RE."]


def normalize_file(path: Path, dry_run: bool = False) -> int:
    data = json.loads(path.read_text())
    current = Decimal((data["summary"]["net_worth"] or {})["amount"])
    ratio = TARGET_NET_WORTH / current

    try:
        before_relations = _holding_relations(data)
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    scaled: list[str] = []
    _walk(data, ratio, scaled, path="")

    errors = _verify(data, before_relations)
    if errors:
        for e in errors:
            print(f"❌ {e}")
        return 1

    print(f"net_worth: {current} → {TARGET_NET_WORTH} (ratio {ratio:.8f}); scaled {len(scaled)} fields")
    if dry_run:
        print("(dry-run: file not written)")
        return 0

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"✅ written: {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="frontend/e2e/dashboard-report.json", help="Fixture path (default: the gallery dashboard snapshot)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"❌ file not found: {target}")
        return 1
    return normalize_file(target, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
