"""The PAC's reference values (project 67, lot A1): what the planner published before the engine changed, and the rules that
compare a later plan with it.

A2 changes the engine under the released PAC Tool: one FX decision per Broker and currency pair instead of one per buy route
and currency, plus the transfer family. The PAC must not get worse. This module holds, for the test and for the probe alike:

* ``extract_reference``: the quantities of a published plan that matter, read from the dumped wire result (never from engine
  internals) as exact fractions written as text, with no decision id, no fingerprint, no tie-break key and no clock;
* ``reference_violations``: the comparison rules R1-R7 of the block plan, as one function over two records (the recorded one
  and the current one) and the list of accepted differences;
* ``CASES``: the cases the test replans; every other grid variant (``GRID_VARIANTS``) is for the probe only.

The recorded file ``fixtures/pac_allocator/pac_reference_values.json`` is written once by
``diagnostics/pac_reference_recorder.py`` from the code of the commit it names, and frozen: A2, A3 and A4 do not rewrite it.
A difference they cause goes into ``pac_reference_accepted_differences.json``, approved by the coordinator.

The rules (R1-R7), in short. R1 state, proof kind and stop reason are equal. R2 the references and the target values are equal.
R3 the objective vector is not worse, lexicographically. R4 no more conversions and no new (broker, from, to) triple. R5 where
the old plan had more FX actions than conversions (a merge) and the vector is equal, every difference must be written in the
accepted file and the cells' final spendable may move by at most one minor unit of each currency per merged action; no more
rounding top-ups. R6 where it had not, nothing differs. R7 a strictly better vector is not an error but never passes alone:
it needs an accepted entry naming the cause.

Not a test module (leading underscore): pytest never collects it, and the runner catalogue does not list it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from typing import Any

from backend.app.schemas.pac_allocator.results import PAC_PLAN_INPUT_ADAPTER, PAC_PLAN_OUTPUT_ADAPTER
from backend.app.services.pac_allocator.planner import plan_pac_allocation
from backend.test_scripts.test_services import _pac_synthetic_requests as synthetic

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator"
REFERENCE_FILE = FIXTURE_DIR / "pac_reference_values.json"
ACCEPTED_FILE = FIXTURE_DIR / "pac_reference_accepted_differences.json"

# The time given to SCIP: the engine window the Tool claims for a plan (``tool_plugins/pac_allocator/plugin.py``,
# ``engine_timeout_ms=30_000``), as ``test_pac_planner_planner.py`` plans. A budget handed to SCIP, never an assertion.
REFERENCE_BUDGET_SECONDS = 30.0

OBJECTIVE_CODES = ("fixed_l2", "shortfall", "route_priority", "explicit_cost", "active_order_rows")
ACCOUNTING_FIELDS = ("final_invested", "shortfall", "free_cash", "economic_losses", "rounding_delta")
COST_FIELDS = ("buy_fees", "sell_fees", "fx_spread_loss", "execution_margin_cost", "broker_withheld_tax", "self_reserved_tax")
REFERENCE_FIELDS = ("fixed_reference", "selected_funding", "reachable_funding", "trapped_funding")
CELL_FIELDS = ("final_spendable", "fx_debit", "fx_credit")

# What a recorded file must never carry: decision and action ids (``fx:<route>:<currency>``), the tie-break keys, the request
# fingerprint, any wall time. Checked on the text of the file.
FORBIDDEN_IN_RECORD = ("fx:", "tie_break", "ordered_keys", "fingerprint", "wall")

type Record = dict[str, Any]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def wire_fraction(value: Any) -> Fraction:
    """One published number as an exact fraction: an ``ExactNumber``, a money, a money of an ``ExactNumber``, or a plain decimal text."""
    if isinstance(value, dict):
        kind = value.get("kind")
        if kind == "finite_decimal":
            return Fraction(value["value"])
        if kind == "exact_ratio":
            return Fraction(int(value["numerator"]), int(value["denominator"]))
        if "amount" in value:
            return wire_fraction(value["amount"])
        if "value" in value:
            return wire_fraction(value["value"])
        raise ValueError(f"not a published number: {value!r}")
    return Fraction(str(value))


def text_of(value: Fraction) -> str:
    """``numerator/denominator`` (or the integer): the exact, locale-free spelling the record uses."""
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _frac(value: Any) -> str:
    return text_of(wire_fraction(value))


def uses_required_minimum(request: dict) -> bool:
    """A route of the request carries a ``required_minimum`` other than ``none`` (M19 removes it from the PAC in A4)."""
    return any(route.get("required_minimum", {"kind": "none"}).get("kind", "none") != "none" for route in request.get("order_routes", []))


def _named_currencies(request: dict) -> set[str]:
    """Every currency a request holds money in: Asset quotes, cash, contributions, funding routes."""
    named = {asset["quote"]["currency"] for asset in request.get("assets", [])}
    named |= {cash["selected"]["currency"] for cash in request.get("existing_cash", [])}
    named |= {contribution["amount"]["currency"] for contribution in request.get("contributions", [])}
    named |= {route["currency"] for route in request.get("funding_routes", [])}
    return named


def valuation_rates(request: dict) -> dict[str, str]:
    """Units of the valuation currency per unit of each currency the request names, at the stored (mid) rate: the 'average rate' of R5.

    A named currency with no direct pair to the valuation currency raises ``ValueError``: valued at zero, its cells' differences would
    drop out of R5's sum and pass with no cap, so the recorder stops instead of weakening the rule.
    """
    valuation = request["valuation_currency"]
    rates = {valuation: Fraction(1)}
    for pair, rate in request.get("fx_rates", {}).items():
        base, quote = pair.split("/")
        if quote == valuation:
            rates[base] = Fraction(rate)
        elif base == valuation:
            rates[quote] = 1 / Fraction(rate)
    missing = sorted(_named_currencies(request) - set(rates))
    if missing:
        raise ValueError(f"no direct rate to {valuation} for {missing}: R5 could not value their cells")
    return {currency: text_of(rate) for currency, rate in sorted(rates.items())}


def minor_units(wire: dict) -> dict[str, str]:
    return {row["currency"]: _frac(row["minor_unit"]) for row in wire["catalogs"]["currencies"]}


def extract_reference(wire: dict, request: dict) -> Record:
    """The quantities of one published plan, from its dumped wire result and the request that produced it.

    Only what a plan says: states, references, the five objective stages, conversions, orders, fundings, cells, top-ups, accounting
    and the six costs. A result with no solution (no incumbent, infeasible) keeps its states and nothing else.
    """
    proof = wire.get("proof") or {}
    record: Record = {
        "uses_required_minimum": uses_required_minimum(request),
        "state": wire["result_state"],
        "proof_kind": proof.get("kind"),
        "stop_reason": wire.get("stop_reason"),
        "valuation_rates": valuation_rates(request),
    }
    solution = wire.get("primary_solution")
    if solution is None:
        return record
    accounting = solution["accounting"]
    stages = {stage["objective_code"]: stage for stage in solution["objectives"]["stages"]}
    actions_per_pair: dict[str, int] = {}
    for action in solution["fx_actions"]:
        key = _pair_key(action)
        actions_per_pair[key] = actions_per_pair.get(key, 0) + 1
    record.update(
        {
            "minor_units": minor_units(wire),
            "references": {name: _frac(accounting[name]) for name in REFERENCE_FIELDS},
            "asset_target_values": {row["asset_id"]: _frac(row["target_value"]) for row in sorted(solution["asset_rows"], key=lambda row: row["asset_id"])},
            "objective_vector": [_frac(stages[code]["value"]) for code in OBJECTIVE_CODES],
            "conversions": {_pair_key(conversion): {"debit": _frac(conversion["source_debit"]), "credit": _frac(conversion["destination_credit"]), "spread_loss": _frac(conversion["spread_loss"])} for conversion in solution["conversions"]},
            "fx_actions_per_pair": dict(sorted(actions_per_pair.items())),
            "orders": {row["route_id"]: {"asset_id": row["asset_id"], "broker_id": row["broker_id"], "quantity": _frac(row["economic_quantity"]["value"]), "cash_debit": _frac(row["cash_debit"]), "fee": _frac(row["fee"])} for row in sorted(solution["order_rows"], key=lambda row: row["route_id"])},
            "fundings": {row["funding_route_id"]: _frac(row["amount"]) for row in sorted(solution["funding_actions"], key=lambda row: row["funding_route_id"])},
            "cells": {f"{row['broker_id']}|{row['currency']}": {name: _frac(row[name]) for name in CELL_FIELDS} for row in sorted(solution["ledger_rows"], key=lambda row: (row["broker_id"], row["currency"]))},
            "rounding_top_ups": len(solution["rounding_top_ups"]),
            "accounting": {name: _frac(accounting[name]) for name in ACCOUNTING_FIELDS},
            "costs": {name: _frac(solution["costs"][name]) for name in COST_FIELDS},
        }
    )
    return record


def _pair_key(action: dict) -> str:
    """``broker|from|to`` of a conversion or of an FX action: the unit of the new decision (specification §15 n. 1)."""
    return f"{action['broker_id']}|{action['source_debit']['currency']}|{action['destination_credit']['currency']}"


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _vector(record: Record) -> list[Fraction]:
    return [Fraction(text) for text in record.get("objective_vector", [])]


def _flat_quantities(record: Record) -> dict[str, str]:
    """Every compared figure of a record under a stable path, for the R5/R6 differences."""
    flat: dict[str, str] = {}
    for key, entry in record.get("conversions", {}).items():
        flat.update({f"conversions.{key}.{name}": value for name, value in entry.items()})
    for key, entry in record.get("orders", {}).items():
        flat.update({f"orders.{key}.{name}": value for name, value in entry.items()})
    flat.update({f"fundings.{key}": value for key, value in record.get("fundings", {}).items()})
    for key, entry in record.get("cells", {}).items():
        flat.update({f"cells.{key}.{name}": value for name, value in entry.items()})
    flat.update({f"accounting.{key}": value for key, value in record.get("accounting", {}).items()})
    flat.update({f"costs.{key}": value for key, value in record.get("costs", {}).items()})
    return flat


def _same_value(left: str, right: str) -> bool:
    """Two spellings of one figure are the same: ``"0.01"`` and ``"1/100"``, or two JSON lists of such figures (the vector)."""
    try:
        left_value, right_value = json.loads(left), json.loads(right)
    except json.JSONDecodeError:
        left_value, right_value = left, right
    if isinstance(left_value, list) and isinstance(right_value, list):
        return len(left_value) == len(right_value) and all(_same_value(str(a), str(b)) for a, b in zip(left_value, right_value, strict=True))
    try:
        return Fraction(str(left_value)) == Fraction(str(right_value))
    except (ValueError, ZeroDivisionError):
        return left == right


def _is_accepted(accepted: list[dict], quantity: str, before: str, after: str) -> bool:
    """An accepted entry matches by quantity and by value: its ``before`` and ``after`` may use any exact spelling of the figures."""
    return any(entry["quantity"] == quantity and _same_value(entry["before"], before) and _same_value(entry["after"], after) for entry in accepted)


def merge_allowance(recorded: Record) -> Fraction:
    """R5's bound, in the valuation currency: per merged pair, (actions of A1 - 1) x (a minor unit of the destination + one of the source)."""
    rates = {currency: Fraction(text) for currency, text in recorded.get("valuation_rates", {}).items()}
    units = {currency: Fraction(text) for currency, text in recorded.get("minor_units", {}).items()}
    allowance = Fraction(0)
    for key, count in recorded.get("fx_actions_per_pair", {}).items():
        if count > 1:
            _, source, destination = key.split("|")
            allowance += (count - 1) * (units[destination] * rates[destination] + units[source] * rates[source])
    return allowance


def _vector_problems(recorded: Record, current: Record, accepted: list[dict]) -> tuple[list[str], bool]:
    """R3 and R7: the objective vector. Returns the problems and whether the vector is strictly better (and so R7 covers the rest)."""
    before, after = _vector(recorded), _vector(current)
    if after > before:
        return [f"R3 objective vector worse: {recorded['objective_vector']} -> {current['objective_vector']}"], False
    if after < before and not _is_accepted(accepted, "objective_vector", json.dumps(recorded["objective_vector"]), json.dumps(current["objective_vector"])):
        return [f"R7 objective vector strictly better and not in the accepted differences: before {json.dumps(recorded['objective_vector'])} after {json.dumps(current['objective_vector'])}"], True
    return [], after < before


def _conversion_problems(recorded: Record, current: Record) -> list[str]:
    """R4 and the top-ups of R5: no more conversions, no new (broker, from, to) pair, no more rounding top-ups."""
    problems = []
    # Conversions are keyed by pair: a set of pairs inside the old one can never be larger, so "no new pair" is also "no more conversions".
    new_pairs = sorted(set(current["conversions"]) - set(recorded["conversions"]))
    if new_pairs:
        problems.append(f"R4 new conversion pairs {new_pairs} ({len(recorded['conversions'])} -> {len(current['conversions'])} conversions)")
    if current["rounding_top_ups"] > recorded["rounding_top_ups"]:
        problems.append(f"R5 rounding top-ups {recorded['rounding_top_ups']} -> {current['rounding_top_ups']}")
    return problems


def _difference_problems(recorded: Record, current: Record, accepted: list[dict]) -> list[str]:
    """R6 and R5: what differs in a plan whose vector is equal."""
    flat_before, flat_after = _flat_quantities(recorded), _flat_quantities(current)
    differences = [(quantity, flat_before.get(quantity, "-"), flat_after.get(quantity, "-")) for quantity in sorted(set(flat_before) | set(flat_after)) if flat_before.get(quantity) != flat_after.get(quantity)]
    if not differences:
        return []
    if not any(count > 1 for count in recorded.get("fx_actions_per_pair", {}).values()):
        return [f"R6 {quantity}: {old} -> {new} (no merge in this case: nothing may differ)" for quantity, old, new in differences]
    rates = {currency: Fraction(text) for currency, text in recorded.get("valuation_rates", {}).items()}
    problems, moved = [], Fraction(0)
    for quantity, old, new in differences:
        if not _is_accepted(accepted, quantity, old, new):
            problems.append(f"R5 {quantity}: {old} -> {new} is not in the accepted differences")
        if quantity.startswith("cells.") and quantity.endswith(".final_spendable"):
            currency = quantity.split(".")[1].split("|")[1]
            moved += abs(Fraction(new if new != "-" else "0") - Fraction(old if old != "-" else "0")) * rates[currency]
    allowance = merge_allowance(recorded)
    if moved > allowance:
        problems.append(f"R5 cells' final spendable moved {text_of(moved)} > bound {text_of(allowance)} (valuation currency)")
    return problems


def reference_violations(recorded: Record, current: Record, accepted: list[dict]) -> list[str]:
    """What the current record breaks against the recorded one, one line per broken rule; empty means the plan holds.

    ``accepted`` are the accepted-difference entries of this case (``quantity``, ``before``, ``after``, ...). Each line starts with the rule.
    """
    problems = [f"R1 {field}: {recorded.get(field)!r} -> {current.get(field)!r}" for field in ("state", "proof_kind", "stop_reason") if recorded.get(field) != current.get(field)]
    if "objective_vector" not in recorded or "objective_vector" not in current:
        if ("objective_vector" in recorded) != ("objective_vector" in current):
            problems.append("R1 a plan appeared or vanished")
        return problems
    problems.extend(f"R2 {section}: {recorded[section]} -> {current[section]}" for section in ("references", "asset_target_values") if recorded[section] != current[section])
    vector_problems, better = _vector_problems(recorded, current, accepted)
    problems.extend(vector_problems)
    problems.extend(_conversion_problems(recorded, current))
    if not better:  # R7: a strictly better vector has no ceiling on its effects; its accepted entry names the cause
        problems.extend(_difference_problems(recorded, current, accepted))
    return problems


# ---------------------------------------------------------------------------
# The corpus
# ---------------------------------------------------------------------------

# FX cases: the plans ``test_pac_planner_planner.py`` pins by value, each a proven optimum.
_FX_CASES: dict[str, Callable[[], dict]] = {
    "fx-eur-funds-usd": lambda: synthetic.fx_conversion_request("ref-eur-funds-usd", funding_currency="EUR", assets=[("USD", "10.01")], fx_rates={"EUR/USD": "1.085"}),
    "fx-usd-funds-eur": lambda: synthetic.fx_conversion_request("ref-usd-funds-eur", funding_currency="USD", assets=[("EUR", "10.01")], fx_rates={"EUR/USD": "1.085"}),
    "fx-usd-funds-eur-spread": lambda: synthetic.fx_conversion_request("ref-usd-funds-eur-spread", funding_currency="USD", assets=[("EUR", "10.00")], fx_rates={"EUR/USD": "1.085"}, fx_spread_rate="0.01"),
    "fx-chf-funds-usd-implied": lambda: synthetic.fx_conversion_request("ref-chf-implied", funding_currency="CHF", assets=[("USD", "10.00")], fx_rates={**synthetic.FX_TRIANGLE, "CHF/USD": "1.1501"}),
    "fx-chf-funds-usd-spread": lambda: synthetic.fx_conversion_request("ref-chf-spread", funding_currency="CHF", assets=[("USD", "10.00")], fx_rates={**synthetic.FX_TRIANGLE, "CHF/USD": "1.16"}, fx_spread_rate="0.01"),
    "n1-two-usd-assets": synthetic.fx_two_assets_one_pair_request,
    "n2-two-way": synthetic.fx_two_way_request,
    "n3-two-brokers": synthetic.fx_two_brokers_request,
    "n4-two-sources": synthetic.fx_two_sources_request,
}

# Every variant of the two grids, by the probe's name: ``m-`` for ``synthetic.V``, ``r-`` for ``realistic_make``.
REALISTIC_SHAPES = ((3, 2), (5, 2), (8, 2), (12, 2), (3, 3), (5, 3), (8, 3), (10, 3))
GRID_VARIANTS: dict[str, Callable[[], dict]] = {
    **{f"m-{name}": (lambda settings=settings: synthetic.make(**settings)) for name, settings in synthetic.V.items()},
    **{f"r-{assets}x{brokers}": (lambda assets=assets, brokers=brokers: synthetic.realistic_make(assets, brokers)) for assets, brokers in REALISTIC_SHAPES},
}

# The grid variants the test replans: measured on 2026-11-12 (``pac_solver_robustness_probe.py``, budget 30 s) to close «proven» and
# «completed» in well under a third of it (one sixth). Every other variant is for the probe only.
GRID_CASES: tuple[str, ...] = (
    "m-5x1",
    "m-5x2_samefee",
    "m-5x2_nofee",
    "m-5x2_fixedonly",
    "m-5x2_cash1",
    "m-5x2_disjoint",
    "m-10x1",
    "m-10x2_disjoint",
    "m-2x2",
    "m-1x2",
    "r-3x2",
    "r-5x2",
    "r-12x2",
    "r-3x3",
    "r-5x3",
)

CASES: dict[str, Callable[[], dict]] = {**{name: GRID_VARIANTS[name] for name in GRID_CASES}, **_FX_CASES}


def plan_wire(request: dict, *, budget_seconds: float = REFERENCE_BUDGET_SECONDS) -> dict:
    """Plan ``request`` through the real ``plan_pac_allocation`` and return the dumped wire result, revalidated."""
    result = plan_pac_allocation(PAC_PLAN_INPUT_ADAPTER.validate_python(request), solver_time_budget_seconds=budget_seconds)
    PAC_PLAN_OUTPUT_ADAPTER.validate_python(result.model_dump(mode="python"))
    return PAC_PLAN_OUTPUT_ADAPTER.dump_python(result, mode="json", by_alias=True)


def plan_record(request: dict, *, budget_seconds: float = REFERENCE_BUDGET_SECONDS) -> Record:
    return extract_reference(plan_wire(request, budget_seconds=budget_seconds), request)


def load_reference() -> dict:
    return json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))


def load_accepted() -> list[dict]:
    return json.loads(ACCEPTED_FILE.read_text(encoding="utf-8"))["differences"]
