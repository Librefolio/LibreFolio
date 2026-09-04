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

After the transform the script verifies its invariants and exits 1 on violation:
net worth equals the target and per-holding value ≈ price × quantity.
"""

import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

TARGET_NET_WORTH = Decimal("50000")

# Field names whose plain-string numbers are money → scale them.
SCALE_NAME_RE = re.compile(
    r"(?:^|_)(value|price|amount|cost|cash|nav|income|fee|fees|tax|taxes|deposit|deposited|" r"withdrawn|withdrawal|pnl|capital|book|baseline|flow|flows|result|contribution|invested|" r"gain_loss|gain|loss|wac)(?:$|_)",
    re.IGNORECASE,
)

# Field names whose numbers must never be scaled (ratios, percents, counts, ids, dates).
NEVER_SCALE_RE = re.compile(
    r"(?:^|_)(percent|rate|ratio|weight|count|days|id|date|quantity|qty|units|year|month)(?:$|_)" r"|^(mwrr|twrr|roi|mwrr_annualized|mwrr_cumulative|mwrr_annualized_percent|" r"mwrr_cumulative_percent|twrr_percent|simple_roi_percent)$",
    re.IGNORECASE,
)

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
    return errors


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
