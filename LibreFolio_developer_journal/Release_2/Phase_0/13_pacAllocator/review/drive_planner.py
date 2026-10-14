"""PAC planner v2 — driven review harness.

``operation="plan"`` has NO route: it is not registered in the Tool plugin and
no UI reaches it (see the dossier, §2). This script is the substitute. It
drives ``plan_pac_allocation`` directly and prints, for each result state,
what the planner decided and why — so the mathematics can be reviewed without
a button.

Run from the repo root:

    PYTHONPATH=. PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python \
      LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/review/drive_planner.py

It touches no database and needs no server: the planner is pure, taking a
validated wire request and returning a validated wire result.
"""

from __future__ import annotations

import copy
from decimal import Decimal
from fractions import Fraction

from backend.app.schemas.pac_allocator import PAC_PLAN_INPUT_ADAPTER, PAC_PLAN_OUTPUT_ADAPTER
from backend.app.services.pac_allocator.planner import plan_pac_allocation
from backend.test_scripts.test_schemas.test_pac_planner_schemas import _pac_request

RULE = "=" * 78


def _fraction(exact) -> Fraction:
    """Read a wire ExactNumber back as an exact Fraction (never a float)."""
    if exact.kind == "finite_decimal":
        return Fraction(Decimal(exact.value))
    return Fraction(int(exact.numerator), int(exact.denominator))


def _money(value) -> str:
    return f"{float(_fraction(value.value)):,.2f} {value.currency}"


def _describe(title: str, payload: dict, note: str) -> None:
    print(RULE)
    print(title)
    print(RULE)
    print(f"  setup: {note}")
    request = PAC_PLAN_INPUT_ADAPTER.validate_python(payload)
    result = plan_pac_allocation(request)

    # Re-validating through the wire union re-runs every schema invariant:
    # accounting identity, ledger reconciliation, exposure unit vectors and
    # the proof/evidence binding.
    PAC_PLAN_OUTPUT_ADAPTER.validate_python(result.model_dump(mode="python"))

    print(f"  result_state : {result.result_state}")
    print(f"  availability : {result.availability}")
    if result.availability != "ready":
        print(f"  issues       : {[(i.code, i.kind, i.severity) for i in result.issues]}")
        print()
        return

    proof_detail = getattr(result.proof, "proof_source", None) or getattr(result.proof, "reason_code", "")
    solver_detail = f"({len(result.solver_evidence.stages)} stages)" if result.solver_evidence.kind == "reported_floating" else "- oracle settled it, solver not required"
    print(f"  outcome      : {result.outcome}")
    print(f"  proof        : {result.proof.kind}  [{proof_detail}]")
    print(f"  stop_reason  : {result.stop_reason}")
    print(f"  solver       : {result.solver_evidence.kind} {solver_detail}")

    solution = getattr(result, "primary_solution", None)
    if solution is None:
        print("  (no solution published - nothing is claimed)")
        print()
        return

    acc = solution.accounting
    print(f"  validation   : {solution.validation}")
    print()
    print("  ACCOUNTING (exact, valuation currency)")
    print(f"    fixed_reference (what targets are measured against) : {_money(acc.fixed_reference)}")
    print(f"    reachable funding                                   : {_money(acc.reachable_funding)}")
    print(f"    trapped funding (selected, no route can spend it)   : {_money(acc.trapped_funding)}")
    print(f"    final invested                                      : {_money(acc.final_invested)}")
    print(f"    shortfall = fixed_reference - final_invested        : {_money(acc.shortfall)}")
    print(f"      decomposes as free_cash {_money(acc.free_cash)} + reserves {_money(acc.physical_reserves)}")
    print(f"      + economic losses {_money(acc.economic_losses)} + rounding {_money(acc.rounding_delta)}")
    print(f"    identity_delta (MUST be exactly zero)               : {_money(acc.identity_delta)}")
    print()
    print("  ORDERS")
    if not solution.order_rows:
        print("    (none - doing nothing is what the planner chose)")
    for row in solution.order_rows:
        quantity = row.instruction.quantity if row.instruction.kind == "whole_quantity" else row.instruction.amount.amount
        print(f"    BUY {quantity} x {row.asset_id} @ {row.broker_id}   cash_debit={row.cash_debit.amount} {row.cash_debit.currency}   fee={row.fee.amount}")
    print()
    print("  PER-ASSET")
    for row in solution.asset_rows:
        weight = "unavailable" if row.final_weight.kind == "unavailable" else f"{float(_fraction(row.final_weight.value)) * 100:.2f}%"
        print(f"    {row.asset_id:<12} target={_money(row.target_value):>14}  final={_money(row.final_value):>14}  residual={_money(row.residual):>14}  weight={weight}")
    print()
    print("  OBJECTIVE CASCADE (lexicographic, exact rationals)")
    for stage in solution.objectives.stages:
        print(f"    {stage.ordinal}. {stage.objective_code:<20} {stage.sense}  = {_fraction(stage.value)}")
    print(f"    tie-break: {solution.objectives.tie_break.code} over {list(solution.objectives.tie_break.ordered_keys)}")
    print()
    print("  EXPOSURE (each dimension MUST sum to exactly 1)")
    dimensions: dict[str, list] = {}
    for row in solution.exposure_rows:
        dimensions.setdefault(row.dimension, []).append(row)
    for dimension, rows in dimensions.items():
        total = sum((_fraction(row.target_weight) for row in rows), Fraction())
        parts = ", ".join(f"{row.category_id}={float(_fraction(row.target_weight)):.3f}" for row in rows)
        print(f"    {dimension:<12} {parts}   sum={total}")
    print()


def _no_op_payload() -> dict:
    """Unmodified fixture: EUR5 available against a EUR10 unit price."""
    return _pac_request()


def _incumbent_payload() -> dict:
    payload = copy.deepcopy(_pac_request())
    for cash in payload["existing_cash"]:
        cash["available"]["amount"] = "50.00"
        cash["selected"]["amount"] = "50.00"
    for route in payload.get("funding_routes", []):
        if "transfer_cap" in route:
            route["transfer_cap"]["amount"] = "50.00"
    return payload


def _infeasible_payload() -> dict:
    """A per-order minimum the budget cannot meet - the case that used to crash."""
    payload = copy.deepcopy(_pac_request())
    payload["order_routes"][0]["required_minimum"] = {"kind": "whole_quantity", "quantity": "1", "unit": "asset_unit"}
    return payload


def _needs_input_payload() -> dict:
    payload = copy.deepcopy(_pac_request())
    payload["assets"] = []
    return payload


def main() -> None:
    print()
    print("PAC PLANNER v2 - DRIVEN REVIEW HARNESS")
    print("`operation=plan` has no route; this drives the service directly.")
    print()
    _describe("1. READY_NO_OP - doing nothing is provably optimal", _no_op_payload(), "EUR5 cash, EUR10 unit price: one share is unaffordable")
    _describe("2. READY_INCUMBENT - a real plan", _incumbent_payload(), "same fixture, cash raised to EUR50: five shares become affordable")
    _describe("3. READY_INFEASIBLE - proven impossible, not merely unfound", _infeasible_payload(), "per-order minimum of 1 share against EUR5 cash")
    _describe("4. NEEDS_INPUT - refused before any search", _needs_input_payload(), "no assets declared")
    print(RULE)
    print("On the fifth state, ready_no_incumbent: it is reachable when the domain is")
    print("too large for the exhaustive oracle AND the solver finds nothing within its")
    print("budget. test_pac_planner_planner.py exercises it by forcing the oracle over")
    print("its cap. It is not reproducible from a small fixture, which is the honest")
    print("situation rather than a gap: on toy domains the oracle always settles.")
    print(RULE)


if __name__ == "__main__":
    main()
