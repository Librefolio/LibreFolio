"""Strict PAC/Rebalancer v2 planner wire-contract tests.

The candidate-max fixtures are structural specimens only.  Their successful
validation and remaining byte headroom are deliberately not treated as runtime
or solver-capacity proof.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from backend.app.schemas.pac_allocator import base as pac_schema_base
from backend.app.schemas.pac_allocator.base import PlannerFixedDecimal
from backend.app.schemas.pac_allocator.evidence import SolverStageEvidence, ValuationMoneyUnit
from backend.app.schemas.pac_allocator.exact import AvailableExactNumber, ExactNumber
from backend.app.schemas.pac_allocator.issues import PlannerIssue
from backend.app.schemas.pac_allocator.preview import PAC_TOOL_INPUT_ADAPTER, PAC_TOOL_OUTPUT_ADAPTER, REBALANCER_TOOL_INPUT_ADAPTER, REBALANCER_TOOL_OUTPUT_ADAPTER
from backend.app.schemas.pac_allocator.request import PacPlannerRequest, PlannerBrokerIdentity, RebalancerPlannerRequest, RebalancerTaxInput
from backend.app.schemas.pac_allocator.results import (
    PAC_PLAN_INPUT_ADAPTER,
    PAC_PLAN_OUTPUT_ADAPTER,
    REBALANCER_PLAN_INPUT_ADAPTER,
    REBALANCER_PLAN_OUTPUT_ADAPTER,
    PacPlannerInvalidResult,
    PacPlannerNeedsInputResult,
    PacPlannerReadyIncumbentResult,
    PacPlannerReadyInfeasibleResult,
    PacPlannerReadyNoIncumbentResult,
    PacPlannerReadyNoOpResult,
    PacPlannerUnsupportedResult,
    RebalancerPlannerInvalidResult,
    RebalancerPlannerNeedsInputResult,
    RebalancerPlannerReadyIncumbentResult,
    RebalancerPlannerReadyInfeasibleResult,
    RebalancerPlannerReadyNoIncumbentResult,
    RebalancerPlannerReadyNoOpResult,
    RebalancerPlannerUnsupportedResult,
    _validate_rebalancer_weights,
)
from backend.app.schemas.pac_allocator.rows import ObjectiveStageResult, PlannerSellOrderRow, RebalancerAssetTypeTaxRow, RebalancerExposureCashRow, RebalancerTaxBasketRow, RebalancerTaxReserveRow, RebalancerTaxScopeRow, RebalancerUnavailableWeight
from backend.app.services.tools.registry import ToolPluginRegistry
from backend.app.services.tools.schema import (
    declared_operations,
    generate_tool_schema,
    resolve_schema_reference,
    root_models,
    schema_fingerprint,
    walk_schema,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator"
GENERATED_CONTRACT = ROOT / "frontend" / "src" / "lib" / "api" / "tool-contracts.openapi.json"

PLANNER_PARAMETER_BYTES = 131_072
from backend.app.schemas.pac_allocator.base import AllocationStrictModel, NotProvenReasonCode, PlannerIntegerText, PlannerIssueCode, PlannerPositiveWholeDecimal, PlannerWholeQuantityStep
from backend.app.schemas.pac_allocator.evidence import InfeasibilityProvenProof, NotProvenProof, ObjectiveSense, OptimalProvenProof, ReadyPlanProof, ReportedFloatingSolverEvidence, SolverStatusWitness
from backend.app.schemas.pac_allocator.request import NoFeeCap, NoOrderCap, NoOrderMinimum, PlannerOrderRouteInput, PlannerSellOrderRouteInput, QuantityOrderCap, WholeQuantityCapability, WholeQuantityMinimum
from backend.app.schemas.pac_allocator.rows import PlannerCatalogAsset, PlannerFundingAction
from backend.app.schemas.pac_allocator.solutions import DeploymentCoincident, DeploymentUnavailable

PLANNER_RESULT_BYTES = 262_144
CANDIDATE_FIXTURE_STATUS = "structural specimen only; not capacity proof"

JsonObject = dict[str, Any]
PayloadFactory = Callable[[], JsonObject]


def _wire(payload: Any) -> bytes:
    return json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()


def _fixture(name: str) -> JsonObject:
    payload = json.loads(_fixture_bytes(name))
    assert isinstance(payload, dict)
    return payload


def _strict_roundtrip(adapter: TypeAdapter[Any], payload: Any) -> tuple[BaseModel, bytes]:
    model = adapter.validate_json(_wire(payload), strict=True)
    emitted = adapter.dump_json(model)
    assert adapter.validate_json(emitted, strict=True) == model
    assert json.loads(emitted) == adapter.dump_python(model, mode="json")
    return model, emitted


def _reject(adapter: TypeAdapter[Any], payload: Any) -> None:
    with pytest.raises(ValidationError):
        adapter.validate_json(_wire(payload), strict=True)


def _reject_because(adapter: TypeAdapter[Any], payload: Any, message: str) -> None:
    """Reject ``payload`` for the stated rule, not for whatever else happens to break first."""
    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_json(_wire(payload), strict=True)
    assert message in str(exc_info.value), exc_info.value


def _assert_extra_forbidden(adapter: TypeAdapter[Any], payload: Any, field_name: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_json(_wire(payload), strict=True)

    errors = exc_info.value.errors(include_url=False)
    assert any(error["type"] == "extra_forbidden" and error["loc"][-1] == field_name for error in errors), errors


def _find(rows: list[JsonObject], field: str, value: Any) -> JsonObject:
    matches = [row for row in rows if row.get(field) == value]
    assert len(matches) == 1, f"expected exactly one {field}={value!r} row"
    return matches.pop()


def _finite(value: str) -> JsonObject:
    return {"kind": "finite_decimal", "value": value}


def _ratio(numerator: str, denominator: str, display_decimal: str) -> JsonObject:
    return {
        "kind": "exact_ratio",
        "numerator": numerator,
        "denominator": denominator,
        "display_decimal": display_decimal,
        "display_scale": len(display_decimal.partition(".")[2]),
        "display_authority": "non_authoritative",
    }


def _exact_wire_fraction(value: JsonObject) -> Fraction:
    if value["kind"] == "finite_decimal":
        return Fraction(value["value"])
    assert value["kind"] == "exact_ratio"
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _money_wire_fraction(value: JsonObject) -> Fraction:
    return _exact_wire_fraction(value["value"])


def _money(value: str, currency: str = "EUR") -> JsonObject:
    return {"value": _finite(value), "currency": currency}


def _available(value: str) -> JsonObject:
    return {"kind": "available", "value": _finite(value)}


def _available_ratio(numerator: str, denominator: str, display_decimal: str) -> JsonObject:
    return {"kind": "available", "value": _ratio(numerator, denominator, display_decimal)}


def _wire_number(value: Fraction) -> JsonObject:
    """``value`` as the wire writes it: a finite decimal when it terminates, else a reduced ratio with a six-digit display."""
    rest = value.denominator
    for prime in (2, 5):
        while rest % prime == 0:
            rest //= prime
    if rest == 1:
        scale = 0
        while (value * 10**scale).denominator != 1:
            scale += 1
        return _finite(f"{Decimal(value.numerator) / Decimal(value.denominator):.{scale}f}")
    return _ratio(str(value.numerator), str(value.denominator), f"{Decimal(value.numerator) / Decimal(value.denominator):.6f}")


def _wire_money(value: Fraction, currency: str = "EUR") -> JsonObject:
    return {"value": _wire_number(value), "currency": currency}


_MONEY_LOST_FIELDS = ("buy_fees", "sell_fees", "fx_spread_loss", "execution_margin_cost", "broker_withheld_tax", "self_reserved_tax", "foreign_withholding_tax", "rounding")


def _reprice_rebalancer(
    solution: JsonObject,
    *,
    final: dict[str, Fraction],
    before: dict[str, Fraction] | None = None,
    cash_final: dict[tuple[str, str], Fraction] | None = None,
    money_lost: dict[str, Fraction] | None = None,
) -> None:
    """Recompute, exactly, what a Rebalancer solution reads off its values (B3 of project 67): the Asset and cash item rows on
    ``F``, the uninvested row, the plan accounts' ``N`` and ``W``, the score and its stages, and the accounting's invested
    totals. The validators compare exactly, so a variant of the medium fixture is never edited by hand."""
    wealth = _money_wire_fraction(solution["plan_accounts"]["initial_wealth"])
    rows = [*solution["asset_rows"], *solution["cash_rows"]]
    # The items of the distance: the Assets and the cash rows with a target; a limit-only cash row sits inside N.
    items = [*solution["asset_rows"], *(row for row in solution["cash_rows"] if _exact_wire_fraction(row["target_weight"]) != 0)]
    for row in solution["asset_rows"]:
        if before is not None:
            row["before_value"] = _wire_money(before[row["asset_id"]])
        row["final_value"] = _wire_money(final[row["asset_id"]])
    for row in solution["cash_rows"]:
        if cash_final is not None:
            row["final_value"] = _wire_money(cash_final[(row["broker_id"], row["currency"])])
    for row in rows:
        for side in ("before", "final"):
            row[f"{side}_weight"] = _wire_number(_money_wire_fraction(row[f"{side}_value"]) / wealth)
        row["residual"] = _wire_money(_money_wire_fraction(row["final_value"]) - _money_wire_fraction(row["target_value"]))
    lost = money_lost if money_lost is not None else {name: _money_wire_fraction(value) for name, value in solution["plan_accounts"]["money_lost"].items()}
    accounts = solution["plan_accounts"]
    accounts["money_lost"] = {name: _wire_money(lost.get(name, Fraction())) for name in _MONEY_LOST_FIELDS}
    loss = sum(lost.values(), Fraction())
    accounts["final_wealth"] = _wire_money(wealth - loss)
    uninvested = {side: wealth - sum((_money_wire_fraction(row[f"{side}_value"]) for row in items), Fraction()) for side in ("before", "final")}
    left = uninvested["final"] - loss
    solution["uninvested_row"] = {
        "before_value": _wire_money(uninvested["before"]),
        "before_weight": _wire_number(uninvested["before"] / wealth),
        "final_value": _wire_money(uninvested["final"]),
        "final_weight": _wire_number(uninvested["final"] / wealth),
        # TL-5 of project 67: the cash with no target (``N`` less the money lost after the plan) and the money lost.
        "untargeted_cash": {"before_value": _wire_money(uninvested["before"]), "before_weight": _wire_number(uninvested["before"] / wealth), "final_value": _wire_money(left), "final_weight": _wire_number(left / wealth)},
        "costs": {"before_value": _wire_money(Fraction()), "before_weight": _wire_number(Fraction()), "final_value": _wire_money(loss), "final_weight": _wire_number(loss / wealth)},
    }
    accounts["uninvested"] = _wire_money(uninvested["final"])
    solution["accounting"]["current_invested"] = _wire_money(sum((_money_wire_fraction(row["before_value"]) for row in solution["asset_rows"]), Fraction()))
    solution["accounting"]["final_invested"] = _wire_money(sum((_money_wire_fraction(row["final_value"]) for row in solution["asset_rows"]), Fraction()))
    accounts["final_cash"] = _wire_money(wealth - loss - _money_wire_fraction(solution["accounting"]["final_invested"]))
    _reprice_score(solution, items, wealth, uninvested["final"], loss)


def _reprice_score(solution: JsonObject, items: list[JsonObject], wealth: Fraction, uninvested: Fraction, loss: Fraction) -> None:
    """The score and its stages, read off the repriced items (``_reprice_rebalancer``)."""
    distance = sum((_money_wire_fraction(row["residual"]) ** 2 for row in items), Fraction()) + uninvested**2
    score = solution["score"]
    score["target_distance"] = _wire_number(distance)
    score["distance_per_wealth"] = _wire_money(distance / wealth)
    score["wealth_loss"] = _wire_money(loss)
    if score["distance_weight"] is not None:
        score["plan_score"] = _wire_money(_exact_wire_fraction(score["distance_weight"]) * distance / wealth + loss)
    for side, field in (("before", "largest_deviation_before"), ("final", "largest_deviation_after")):
        deviations = [abs(_exact_wire_fraction(row[f"{side}_weight"]) - _exact_wire_fraction(row["target_weight"])) for row in items]
        largest = max(deviations, default=Fraction())
        score[field] = _wire_number(largest)
        # X14: the first item at the largest deviation, in the published order; none when no item is off its target.
        score[f"{field}_item"] = None if largest == 0 else _wire_item(items[deviations.index(largest)])
    by_code = {"target_distance": score["target_distance"], "wealth_loss": score["wealth_loss"]["value"]}
    if score["plan_score"] is not None:
        by_code["plan_score"] = score["plan_score"]["value"]
    for stage in solution["objectives"]["stages"]:
        if stage["objective_code"] in by_code:
            stage["value"] = deepcopy(by_code[stage["objective_code"]])


def test_the_largest_deviation_names_the_first_item_in_the_published_order_on_a_tie() -> None:
    """X14: an Asset at 60 % and a cash item at 40 % against 50/50 are ten points off each way, an exact tie. The Asset rows
    come first in the published order, so the Asset is named; with the cash item ahead, the cash item would be. No item
    off its target names none."""
    from types import SimpleNamespace  # noqa: PLC0415

    from backend.app.schemas.pac_allocator.exact import FiniteDecimal  # noqa: PLC0415
    from backend.app.schemas.pac_allocator.results import _largest_deviation_item  # noqa: PLC0415

    def share(value: str) -> FiniteDecimal:
        return FiniteDecimal.model_validate(_finite(value))

    asset = SimpleNamespace(asset_id="asset-a", final_weight=share("0.6"), target_weight=share("0.5"))
    cash = SimpleNamespace(broker_id="broker-alpha", currency="EUR", final_weight=share("0.4"), target_weight=share("0.5"))
    assert _largest_deviation_item([asset, cash], "final_weight") == ("asset", "asset-a")
    assert _largest_deviation_item([cash, asset], "final_weight") == ("cash", "broker-alpha", "EUR")
    on_target = SimpleNamespace(asset_id="asset-a", final_weight=share("0.5"), target_weight=share("0.5"))
    assert _largest_deviation_item([on_target], "final_weight") is None


def _wire_item(row: JsonObject) -> JsonObject:
    """The wire reference of an Asset row or a cash row of a Rebalancer plan."""
    if "asset_id" in row:
        return {"kind": "asset", "asset_id": row["asset_id"]}
    return {"kind": "cash", "broker_id": row["broker_id"], "currency": row["currency"]}


def _pac_request() -> JsonObject:
    return _fixture("pac_plan_request.min.2-0-0.json")


def _compact_pac_request() -> JsonObject:
    """`min` in the form the UI sends: every default omitted, the all-zero fee schedule too."""
    return _fixture("pac_plan_request.compact.2-0-0.json")


def _rebalancer_request() -> JsonObject:
    """The medium Rebalancer request in its final form (B3, project 67): «Invest only», a fidelity, the ``tax`` section."""
    return _fixture("rebalancer_plan_request.medium.2-0-0.json")


# The two SELL routes of the medium fixture before B3. Until C1 a Rebalancer request refuses any sale route (S1), so the
# tests of the SELL route class read them here, on their own.
_MEDIUM_SELL_ROUTES: dict[str, JsonObject] = {
    "route-a-alpha-sell": {
        "route_id": "route-a-alpha-sell",
        "asset_id": "asset-a",
        "broker_id": "broker-alpha",
        "capability_id": "cap-alpha-eur-whole",
        "side": "sell",
        "priority": 1,
        "minimum_if_active": {"kind": "whole_quantity", "quantity": "0", "unit": "asset_unit"},
        "cap": {"kind": "quantity", "quantity": "3", "unit": "asset_unit"},
        "execution_margin_rate": "0",
        "fee_schedule_id": "fee-alpha-eur-sell",
        "provenance_id": "prov-manual",
    },
    "route-b-beta-sell": {
        "route_id": "route-b-beta-sell",
        "asset_id": "asset-b",
        "broker_id": "broker-beta",
        "capability_id": "cap-beta-eur-money",
        "side": "sell",
        "priority": 1,
        "minimum_if_active": {"kind": "monetary_amount", "amount": {"amount": "5.00", "currency": "EUR"}},
        "cap": {"kind": "notional", "amount": {"amount": "20.00", "currency": "EUR"}},
        "execution_margin_rate": "0.01",
        "fee_schedule_id": "fee-beta-eur-sell",
        "provenance_id": "prov-manual",
    },
}


def _medium_sell_route(route_id: str) -> JsonObject:
    return deepcopy(_MEDIUM_SELL_ROUTES[route_id])


def _pac_no_op_result() -> JsonObject:
    return _fixture("pac_plan_result.min.2-0-0.json")


def _rebalancer_incumbent_result() -> JsonObject:
    return _fixture("rebalancer_plan_result.medium.2-0-0.json")


def _failure_result(product: str, state: str) -> JsonObject:
    source = _pac_no_op_result() if product == "PAC" else _rebalancer_incumbent_result()
    issue_code, issue_kind = {
        "needs_input": ("allocation.valuation_currency_missing", "missing"),
        "invalid": ("allocation.duplicate_id", "invalid"),
        "unsupported": ("allocation.capacity_unsupported", "unsupported"),
    }[state]
    return {
        "operation": "plan",
        "result_state": state,
        "availability": state,
        "snapshot": deepcopy(source["snapshot"]),
        "issues": [
            {
                "code": issue_code,
                "severity": "error",
                "kind": issue_kind,
                "path": {"kind": "section", "section": "input"},
                "message_key": issue_code,
                "params": [],
            }
        ],
    }


def _restate_pac_plan_accounts(solution: JsonObject) -> None:
    """The PAC's plan accounts as the report fills them (contract §6.1), from the solution's own accounting and costs:
    ``F`` = current + selected, the money lost by entry (costs and rounding), ``W`` = ``F`` less it, ``N`` = ``F`` less
    the final invested value. A variant of the min fixture that moves the accounting restates them through here."""
    accounting, costs = solution["accounting"], solution["costs"]
    wealth = _money_wire_fraction(accounting["current_invested"]) + _money_wire_fraction(accounting["selected_funding"])
    lost = {name: _money_wire_fraction(costs[name]) for name in _MONEY_LOST_FIELDS if name != "rounding"} | {"rounding": _money_wire_fraction(accounting["rounding_delta"])}
    solution["plan_accounts"] = {
        "initial_wealth": _wire_money(wealth),
        "final_wealth": _wire_money(wealth - sum(lost.values(), Fraction())),
        "money_lost": {name: _wire_money(lost[name]) for name in _MONEY_LOST_FIELDS},
        "uninvested": _wire_money(wealth - _money_wire_fraction(accounting["final_invested"])),
        "final_cash": _wire_money(wealth - sum(lost.values(), Fraction()) - _money_wire_fraction(accounting["final_invested"])),
        "cash_by_currency": _restated_cash_by_currency(solution, accounting["current_invested"]["currency"]),
    }


def _restated_cash_by_currency(solution: JsonObject, valuation: str) -> list[JsonObject]:
    """TL-5 of project 67: the cash by currency of a variant, read off its own ledger — at the start the cash chosen plus the
    contributions deposited (``funding_in`` less ``funding_out``: a contribution comes from outside, a cash from another
    Broker), at the end the spendable balances; the variants carry no contribution left undeposited."""
    initial: dict[str, Fraction] = {}
    final: dict[str, Fraction] = {}
    for row in solution["ledger_rows"]:
        code = row["currency"]
        initial[code] = initial.get(code, Fraction()) + Fraction(row["initial_selected"]) + Fraction(row["funding_in"]) - Fraction(row["funding_out"])
        final[code] = final.get(code, Fraction()) + Fraction(row["final_spendable"])
    codes = sorted((code for code in initial if initial[code] != 0 or final[code] != 0), key=lambda code: (code != valuation, code))
    return [{"currency": code, "initial": _wire_money(initial[code], code), "final": _wire_money(final[code], code), "unused_contributions": _wire_money(Fraction(), code)} for code in codes]


def _pac_incumbent_result() -> JsonObject:
    payload = _pac_no_op_result()
    payload["result_state"] = "ready_incumbent"
    payload["outcome"] = "incumbent_found"

    solution = payload["primary_solution"]
    solution["solution_id"] = "pac-primary-incumbent"
    asset = _find(solution["asset_rows"], "asset_id", "asset-one")
    asset["final_value"] = _money("5")
    asset["residual"] = _money("0")
    asset["final_weight"] = _available("1")
    asset["buy_mid_value"] = _money("5")
    for exposure in solution["exposure_rows"]:
        exposure["final_weight"] = {"kind": "available", "value": deepcopy(exposure["target_weight"])}

    accounting = solution["accounting"]
    for field, value in {
        "current_invested": "0",
        "selected_funding": "5",
        "reachable_funding": "5",
        "trapped_funding": "0",
        "fixed_reference": "5",
        "final_invested": "5",
        "shortfall": "0",
        "free_cash": "0",
        "physical_reserves": "0",
        "economic_losses": "0",
        "rounding_delta": "0",
        "rounding_bound": "0",
        "identity_delta": "0",
    }.items():
        accounting[field] = _money(value)
    for field in ("current_invested", "selected_funding", "reachable_funding", "trapped_funding", "fixed_reference"):
        accounting[field] = deepcopy(payload["scenario_basis"][field])

    source_order = _find(_rebalancer_incumbent_result()["primary_solution"]["order_rows"], "order_id", "order-buy-b-beta")
    order = deepcopy(source_order)
    order["order_id"] = "order-buy-asset-one"
    order["sequence"] = 1
    order["asset_id"] = "asset-one"
    order["broker_id"] = "broker-one"
    order["route_id"] = "route-one"
    order["instruction"]["amount"] = {"amount": "5", "currency": "EUR"}
    order["economic_quantity"]["value"] = {
        "kind": "exact_ratio",
        "numerator": "1",
        "denominator": "4",
        "display_decimal": "0.25",
        "display_scale": 4,
        "display_authority": "non_authoritative",
    }
    for price_field in ("source_price", "mid_price", "charge_price"):
        order[price_field]["value"] = _finite("20")
        order[price_field]["currency"] = "EUR"
    order["mid_value"] = _money("5")
    order["execution_margin_cost"] = _money("0")
    order["cash_debit"] = {"amount": "5", "currency": "EUR"}
    order["fee"] = {"amount": "0", "currency": "EUR"}
    order["buffer"] = {"amount": "0", "currency": "EUR"}
    order["provenance_ids"] = ["prov-manual"]
    solution["order_rows"] = [order]

    ledger = _find(solution["ledger_rows"], "broker_id", "broker-one")
    ledger.update(
        {
            "initial_selected": "5",
            "funding_in": "0",
            "funding_out": "0",
            "fx_debit": "0",
            "fx_credit": "0",
            "buy_debit": "5",
            "gross_sell_credit": "0",
            "buy_fees": "0",
            "sell_fees": "0",
            "broker_withheld_tax": "0",
            "self_reserved_tax": "0",
            "rounding_delta": _finite("0"),
            "final_spendable": "0",
            "final_physical": "0",
        }
    )

    for objective_code, value in {
        "fixed_l2": "0",
        "shortfall": "0",
        "route_priority": "1",
        "explicit_cost": "0",
        "active_order_rows": "1",
    }.items():
        _find(solution["objectives"]["stages"], "objective_code", objective_code)["value"] = _finite(value)
    solution["objectives"]["tie_break"]["ordered_keys"] = ["order-buy-asset-one"]
    _restate_pac_plan_accounts(solution)
    payload["issues"] = []
    payload["deployment"] = {"kind": "coincident", "reason_code": "allocation.primary_is_deployment"}
    return payload


_MEDIUM_BEFORE = {"asset-a": Fraction(80), "asset-b": Fraction(20), "asset-c": Fraction(40), "asset-d": Fraction(10)}
_LEDGER_FLOW_FIELDS = (
    "funding_in",
    "funding_out",
    "transfer_in",
    "transfer_out",
    "fx_debit",
    "fx_credit",
    "buy_debit",
    "gross_sell_credit",
    "buy_fees",
    "sell_fees",
    "broker_withheld_tax",
    "foreign_withholding_tax",
    "self_reserved_tax",
)


def _restate_rebalancer_cash(solution: JsonObject, *, unused: dict[str, Fraction]) -> None:
    """TL-5 of project 67: a Rebalancer variant's cash at the end, currency by currency, read off its own ledger plus the
    contributions it leaves undeposited; the cash at the start does not move with the plan."""
    final: dict[str, Fraction] = dict(unused)
    for row in solution["ledger_rows"]:
        final[row["currency"]] = final.get(row["currency"], Fraction()) + Fraction(row["final_spendable"])
    for row in solution["plan_accounts"]["cash_by_currency"]:
        code = row["currency"]
        row["final"] = _wire_money(final.get(code, Fraction()), code)
        row["unused_contributions"] = _wire_money(unused.get(code, Fraction()), code)


def _rebalancer_no_op_result() -> JsonObject:
    """The medium scenario with nothing done: the contribution stays where it is, so ``N`` is its 50 EUR."""
    payload = _rebalancer_incumbent_result()
    payload["result_state"] = "ready_no_op"
    payload["outcome"] = "no_op"

    solution = payload["primary_solution"]
    solution["solution_id"] = "rebalancer-primary-no-op"
    for section in ("funding_actions", "conversions", "transfers", "order_rows", "rounding_top_ups", "tax_basket_rows", "tax_scope_rows", "tax_reserves", "asset_type_tax_rows"):
        solution[section] = []
    for asset in solution["asset_rows"]:
        asset["buy_mid_value"] = _money("0")
        asset["sell_mid_value"] = _money("0")
    for exposure in solution["exposure_rows"]:
        exposure["final_weight"] = deepcopy(exposure["before_weight"])
    _reprice_rebalancer(solution, final=_MEDIUM_BEFORE, cash_final={("broker-alpha", "EUR"): Fraction(0)}, money_lost={})

    accounting = solution["accounting"]
    for field, value in {"shortfall": "50", "free_cash": "50", "physical_reserves": "0", "economic_losses": "0", "rounding_delta": "0", "identity_delta": "0"}.items():
        accounting[field] = _money(value)
    for cost_field in solution["costs"]:
        solution["costs"][cost_field] = _money("0")

    for ledger in solution["ledger_rows"]:
        for field in _LEDGER_FLOW_FIELDS:
            ledger[field] = "0"
        ledger["rounding_delta"] = _finite("0")
        ledger["final_spendable"] = ledger["initial_selected"]
        ledger["final_physical"] = ledger["initial_selected"]
    # The 50 EUR contribution is not deposited: it stays at the end, not deposited (TL-5 of project 67).
    _restate_rebalancer_cash(solution, unused={"EUR": Fraction(50)})

    for objective_code in ("operation_count", "route_priority"):
        _find(solution["objectives"]["stages"], "objective_code", objective_code)["value"] = _finite("0")
    solution["objectives"]["tie_break"]["ordered_keys"] = []
    payload["deployment"] = {"kind": "coincident", "reason_code": "allocation.no_actions_selected"}
    return payload


def _rebalancer_no_op_with_zero_asset_result() -> JsonObject:
    payload = _rebalancer_no_op_result()
    holdings = {**_MEDIUM_BEFORE, "asset-a": Fraction(100), "asset-b": Fraction(0)}
    _reprice_rebalancer(payload["primary_solution"], before=holdings, final=holdings)
    return payload


def _ready_infeasible_result(product: str) -> JsonObject:
    """A ``ready_infeasible`` payload exactly as SCIP's verdict publishes it.

    The only infeasibility the product emits is SCIP closing the first, global
    stage ``infeasible`` (D-X1): one reported stage, no primal/dual/gap, and a
    ``solver_status`` witness naming that stage's objective and nothing else.
    """
    payload = _pac_no_op_result() if product == "PAC" else _rebalancer_incumbent_result()
    payload["result_state"] = "ready_infeasible"
    payload["outcome"] = "infeasible_proven"
    payload.pop("primary_solution")
    payload.pop("deployment")
    payload["stop_reason"] = "completed"
    (stage,) = _with_only_an_infeasible_first_stage(payload)["solver_evidence"]["stages"]
    payload["proof"] = {
        "kind": "infeasibility_proven",
        "proof_source": "solver_status",
        "witness": {"kind": "solver_status", "objective_codes": [stage["objective_code"]]},
    }
    return payload


SOLVER_OBSERVATIONS = ("primal", "dual", "absolute_gap", "relative_gap")


def _infeasible_solver_stage(payload: JsonObject, objective_code: str) -> JsonObject:
    """The payload's own stage for ``objective_code``, closed ``infeasible`` by SCIP."""
    stage = deepcopy(_find(payload["solver_evidence"]["stages"], "objective_code", objective_code))
    assert stage["ordinal"] == 1 and stage["scope"] == "global", stage
    stage["status"] = "infeasible"
    for observation in SOLVER_OBSERVATIONS:
        stage[observation] = None
    return stage


def _with_only_an_infeasible_first_stage(payload: JsonObject) -> JsonObject:
    """Replace the payload's evidence with its first stage closed ``infeasible``: nothing runs after it."""
    first_code = _find(payload["solver_evidence"]["stages"], "ordinal", 1)["objective_code"]
    payload["solver_evidence"] = {"kind": "reported_floating", "stages": [_infeasible_solver_stage(payload, first_code)]}
    return payload


def _infeasible_stage_specimen() -> JsonObject:
    stage = _reported_solver_stage(status="infeasible")
    for observation in SOLVER_OBSERVATIONS:
        stage[observation] = None
    return stage


def _ready_no_incumbent_result(product: str) -> JsonObject:
    """SCIP stopped at a limit before holding any solution: nothing is published.

    This is the only way to reach ``ready_no_incumbent`` since the exact replay
    became authoritative (QX1-b): a replay rejection either publishes the plan
    with its rounding top-ups or raises, so it never produces this state.  The
    stop is therefore a limit (``time_limit``) and the evidence carries the
    stage the limit interrupted (``unfinished``), as the stop-evidence rule
    requires of every limit stop.
    """
    payload = _pac_no_op_result() if product == "PAC" else _rebalancer_incumbent_result()
    payload["result_state"] = "ready_no_incumbent"
    payload["outcome"] = "no_incumbent"
    payload.pop("primary_solution")
    payload.pop("deployment")
    payload["proof"] = {"kind": "not_proven", "reason_code": "allocation.exact_proof_not_established"}
    payload["stop_reason"] = "time_limit"
    payload["solver_evidence"] = {"kind": "reported_floating", "stages": [_reported_solver_stage(status="unfinished")]}
    return payload


def _reported_solver_stage(status: str = "unfinished") -> JsonObject:
    objective = _find(_pac_no_op_result()["primary_solution"]["objectives"]["stages"], "objective_code", "fixed_l2")
    return {
        "kind": "reported_floating",
        "stage": "solver-fixed-l2",
        "objective_code": "fixed_l2",
        "ordinal": 1,
        "status": status,
        "scope": "global",
        "sense": "min",
        "unit": deepcopy(objective["unit"]),
        "primal": "25",
        "dual": "24",
        "absolute_gap": "1",
        "relative_gap": "0.04",
        "tolerances": {
            "feasibility": "0.000001",
            "integrality": "0.000001",
            "absolute_gap": "0",
            "relative_gap": "0",
        },
        "engine": "SCIP",
        "version": "9.2.4",
        "settings": [],
    }


def _primary_objective_codes(payload: JsonObject) -> list[str]:
    codes = [stage["objective_code"] for stage in payload["primary_solution"]["objectives"]["stages"]]
    assert codes
    return codes


def _optimal_proven_proof(objective_codes: list[str], product: str = "PAC") -> JsonObject:
    """An optimum as the product wires it: SCIP's own status, over ``objective_codes``. The Rebalancer's has no
    ``tie_break_closed``: its tie-breaks may stay open (specifica §15 n. 10, B3 of project 67)."""
    proof = {"kind": "optimal_proven", "proof_source": "solver_status", "witness": {"kind": "solver_status", "objective_codes": list(objective_codes)}}
    return proof if product == "Rebalancer" else {**proof, "tie_break_closed": True}


def _finished_evidence_codes(payload: JsonObject) -> list[str]:
    stages = payload["solver_evidence"]["stages"]
    assert stages and all(stage["status"] == "finished" for stage in stages), stages
    return [stage["objective_code"] for stage in stages]


def _distinct_deployment_pac_result() -> JsonObject:
    payload = _pac_incumbent_result()
    primary = payload["primary_solution"]
    deployed = deepcopy(primary)
    deployed["solution_id"] = "pac-deployment-distinct"
    deployed["solution_kind"] = "deployment"
    changed_order = _find(deployed["order_rows"], "order_id", "order-buy-asset-one")
    changed_order["explanation_keys"] = [*changed_order["explanation_keys"], "tools.allocation.explanations.deploymentRounding"]
    deltas = [
        {
            "objective_code": stage["objective_code"],
            "ordinal": stage["ordinal"],
            "sense": stage["sense"],
            "unit": deepcopy(stage["unit"]),
            "primary_value": deepcopy(stage["value"]),
            "deployment_value": deepcopy(stage["value"]),
            "delta": _finite("0"),
        }
        for stage in primary["objectives"]["stages"]
    ]
    payload["deployment"] = {
        "kind": "distinct",
        "solution": deployed,
        "comparison": {
            "primary_solution_id": primary["solution_id"],
            "deployment_solution_id": deployed["solution_id"],
            "changed_order_rows": 1,
            "objective_deltas": deltas,
        },
    }
    return payload


def _distinct_deployment_rebalancer_result() -> JsonObject:
    payload = _rebalancer_no_op_result()
    primary = payload["primary_solution"]
    deployed = deepcopy(_rebalancer_incumbent_result()["primary_solution"])
    deployed["solution_id"] = "rebalancer-deployment-distinct"
    deployed["solution_kind"] = "deployment"

    deltas: list[JsonObject] = []
    for primary_stage, deployment_stage in zip(primary["objectives"]["stages"], deployed["objectives"]["stages"], strict=True):
        assert (primary_stage["objective_code"], primary_stage["ordinal"], primary_stage["sense"], primary_stage["unit"]) == (
            deployment_stage["objective_code"],
            deployment_stage["ordinal"],
            deployment_stage["sense"],
            deployment_stage["unit"],
        )
        difference = _exact_wire_fraction(deployment_stage["value"]) - _exact_wire_fraction(primary_stage["value"])
        deltas.append(
            {
                "objective_code": primary_stage["objective_code"],
                "ordinal": primary_stage["ordinal"],
                "sense": primary_stage["sense"],
                "unit": deepcopy(primary_stage["unit"]),
                "primary_value": deepcopy(primary_stage["value"]),
                "deployment_value": deepcopy(deployment_stage["value"]),
                "delta": _wire_number(difference),
            }
        )

    payload["deployment"] = {
        "kind": "distinct",
        "solution": deployed,
        "comparison": {
            "primary_solution_id": primary["solution_id"],
            "deployment_solution_id": deployed["solution_id"],
            "changed_order_rows": len(deployed["order_rows"]),
            "objective_deltas": deltas,
        },
    }
    return payload


def _result_payload(product: str, state: str) -> JsonObject:
    if state in {"needs_input", "invalid", "unsupported"}:
        return _failure_result(product, state)
    if state == "ready_no_op":
        return _pac_no_op_result() if product == "PAC" else _rebalancer_no_op_result()
    if state == "ready_incumbent":
        return _pac_incumbent_result() if product == "PAC" else _rebalancer_incumbent_result()
    if state == "ready_infeasible":
        return _ready_infeasible_result(product)
    if state == "ready_no_incumbent":
        return _ready_no_incumbent_result(product)
    raise AssertionError(f"unhandled result state {state!r}")


REQUEST_CASES = (
    pytest.param(PAC_PLAN_INPUT_ADAPTER, PacPlannerRequest, _pac_request, id="pac"),
    pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, RebalancerPlannerRequest, _rebalancer_request, id="rebalancer"),
)

RESULT_CASES = (
    pytest.param("PAC", "needs_input", PAC_PLAN_OUTPUT_ADAPTER, PacPlannerNeedsInputResult, id="pac-needs-input"),
    pytest.param("PAC", "invalid", PAC_PLAN_OUTPUT_ADAPTER, PacPlannerInvalidResult, id="pac-invalid"),
    pytest.param("PAC", "unsupported", PAC_PLAN_OUTPUT_ADAPTER, PacPlannerUnsupportedResult, id="pac-unsupported"),
    pytest.param("PAC", "ready_no_op", PAC_PLAN_OUTPUT_ADAPTER, PacPlannerReadyNoOpResult, id="pac-ready-no-op"),
    pytest.param("PAC", "ready_incumbent", PAC_PLAN_OUTPUT_ADAPTER, PacPlannerReadyIncumbentResult, id="pac-ready-incumbent"),
    pytest.param("PAC", "ready_infeasible", PAC_PLAN_OUTPUT_ADAPTER, PacPlannerReadyInfeasibleResult, id="pac-ready-infeasible"),
    pytest.param("PAC", "ready_no_incumbent", PAC_PLAN_OUTPUT_ADAPTER, PacPlannerReadyNoIncumbentResult, id="pac-ready-no-incumbent"),
    pytest.param("Rebalancer", "needs_input", REBALANCER_PLAN_OUTPUT_ADAPTER, RebalancerPlannerNeedsInputResult, id="rebalancer-needs-input"),
    pytest.param("Rebalancer", "invalid", REBALANCER_PLAN_OUTPUT_ADAPTER, RebalancerPlannerInvalidResult, id="rebalancer-invalid"),
    pytest.param("Rebalancer", "unsupported", REBALANCER_PLAN_OUTPUT_ADAPTER, RebalancerPlannerUnsupportedResult, id="rebalancer-unsupported"),
    pytest.param("Rebalancer", "ready_no_op", REBALANCER_PLAN_OUTPUT_ADAPTER, RebalancerPlannerReadyNoOpResult, id="rebalancer-ready-no-op"),
    pytest.param("Rebalancer", "ready_incumbent", REBALANCER_PLAN_OUTPUT_ADAPTER, RebalancerPlannerReadyIncumbentResult, id="rebalancer-ready-incumbent"),
    pytest.param("Rebalancer", "ready_infeasible", REBALANCER_PLAN_OUTPUT_ADAPTER, RebalancerPlannerReadyInfeasibleResult, id="rebalancer-ready-infeasible"),
    pytest.param("Rebalancer", "ready_no_incumbent", REBALANCER_PLAN_OUTPUT_ADAPTER, RebalancerPlannerReadyNoIncumbentResult, id="rebalancer-ready-no-incumbent"),
)

FIXTURE_CASES = (
    pytest.param("pac_plan_request.min.2-0-0.json", PAC_PLAN_INPUT_ADAPTER, PLANNER_PARAMETER_BYTES, False, id="pac-request-min"),
    pytest.param("pac_plan_result.min.2-0-0.json", PAC_PLAN_OUTPUT_ADAPTER, PLANNER_RESULT_BYTES, False, id="pac-result-min"),
    pytest.param("pac_plan_request.candidate-max.2-0-0.json", PAC_PLAN_INPUT_ADAPTER, PLANNER_PARAMETER_BYTES, True, id="pac-request-candidate"),
    pytest.param("pac_plan_result.candidate-max.2-0-0.json", PAC_PLAN_OUTPUT_ADAPTER, PLANNER_RESULT_BYTES, True, id="pac-result-candidate"),
    pytest.param("rebalancer_plan_request.medium.2-0-0.json", REBALANCER_PLAN_INPUT_ADAPTER, PLANNER_PARAMETER_BYTES, False, id="rebalancer-request-medium"),
    pytest.param("rebalancer_plan_result.medium.2-0-0.json", REBALANCER_PLAN_OUTPUT_ADAPTER, PLANNER_RESULT_BYTES, False, id="rebalancer-result-medium"),
)


# Contract compaction (plan-phase00PacContractCompaction §2): a request root may omit
# exactly these fields, which validation fills with the neutral value; every other root
# field (operation, snapshot, as_of, valuation_currency, provenance, assets, brokers,
# order_routes, target_weights, policy; the Rebalancer's target_fidelity) stays required. The Rebalancer has no funding
# routes (the normalizer generates its deposits, B3 of project 67) and defaults its holdings and its tax section.
ROOT_DEFAULTED_FIELDS: dict[str, Any] = {
    "fx_rates": {},
    "fx_spread_rate": "0",
    "existing_cash": [],
    "contributions": [],
    "funding_routes": [],
}
REBALANCER_ROOT_DEFAULTED_FIELDS: dict[str, Any] = {
    **{name: value for name, value in ROOT_DEFAULTED_FIELDS.items() if name != "funding_routes"},
    "holdings": [],
    "tax": RebalancerTaxInput(),
}
REBALANCER_ROOT_SCHEMA_DEFAULTS: dict[str, Any] = {
    **REBALANCER_ROOT_DEFAULTED_FIELDS,
    "tax": {"baskets": [], "assets": [], "brokers": [], "carried_losses": [], "cost_bases": []},
}


def _root_defaulted_fields(model_type: type[BaseModel]) -> dict[str, Any]:
    return ROOT_DEFAULTED_FIELDS if model_type is PacPlannerRequest else REBALANCER_ROOT_DEFAULTED_FIELDS


@pytest.mark.parametrize("adapter,model_type,factory", REQUEST_CASES)
def test_all_three_request_roots_strict_roundtrip_and_reject_impossible_shapes(
    adapter: TypeAdapter[Any],
    model_type: type[BaseModel],
    factory: PayloadFactory,
) -> None:
    payload = factory()
    model, _emitted = _strict_roundtrip(adapter, payload)

    assert type(model) is model_type
    defaulted = _root_defaulted_fields(model_type)
    assert {name for name, field in model_type.model_fields.items() if not field.is_required()} == set(defaulted)

    wrong_operation = deepcopy(payload)
    wrong_operation["operation"] = "analyze"
    _reject(adapter, wrong_operation)

    wrong_policy = deepcopy(payload)
    wrong_policy["policy"] = "unsupported_policy"
    _reject(adapter, wrong_policy)

    extra = deepcopy(payload)
    extra["planner_private_state"] = {}
    _reject(adapter, extra)

    for field_name in model_type.model_fields:
        missing = deepcopy(payload)
        # An optional field the fixture leaves out (the preview's euros) is already missing.
        missing.pop(field_name, None)
        if field_name not in defaulted:
            _reject(adapter, missing)
            continue
        filled = adapter.validate_json(_wire(missing), strict=True)
        assert type(filled) is model_type
        assert getattr(filled, field_name) == defaulted[field_name], field_name
        wire_default = adapter.dump_python(filled, mode="json")[field_name]
        assert filled == adapter.validate_json(_wire({**missing, field_name: wire_default}), strict=True)


@pytest.mark.parametrize("product,state,adapter,result_type", RESULT_CASES)
def test_all_fourteen_result_branches_strict_roundtrip_and_reject_impossible_states(
    product: str,
    state: str,
    adapter: TypeAdapter[Any],
    result_type: type[BaseModel],
) -> None:
    payload = _result_payload(product, state)
    model, _emitted = _strict_roundtrip(adapter, payload)

    assert type(model) is result_type
    assert all(field.is_required() for field in result_type.model_fields.values())

    wrong_operation = deepcopy(payload)
    wrong_operation["operation"] = "analyze"
    _reject(adapter, wrong_operation)

    wrong_availability = deepcopy(payload)
    wrong_availability["availability"] = "ready" if state in {"needs_input", "invalid", "unsupported"} else "invalid"
    _reject(adapter, wrong_availability)

    wrong_state = deepcopy(payload)
    wrong_state["result_state"] = "impossible_state"
    _reject(adapter, wrong_state)

    extra = deepcopy(payload)
    extra["planner_private_state"] = {}
    _reject(adapter, extra)

    impossible = deepcopy(payload)
    if state in {"needs_input", "invalid", "unsupported"}:
        impossible["outcome"] = "incumbent"
    elif state in {"ready_no_op", "ready_incumbent"}:
        impossible.pop("primary_solution")
    else:
        impossible["deployment"] = {"kind": "coincident", "reason_code": "allocation.impossible_state"}
    _reject(adapter, impossible)


@pytest.mark.parametrize("product,state,adapter,_result_type", RESULT_CASES)
def test_failure_and_ready_issue_severity_cannot_misrepresent_availability(
    product: str,
    state: str,
    adapter: TypeAdapter[Any],
    _result_type: type[BaseModel],
) -> None:
    payload = _result_payload(product, state)
    if state in {"needs_input", "invalid", "unsupported"}:
        payload["issues"] = [
            {
                **payload["issues"].pop(),
                "severity": "warning",
            }
        ]
    else:
        payload["issues"] = _failure_result(product, "invalid")["issues"]
    _reject(adapter, payload)


@pytest.mark.parametrize("name,adapter,ceiling,is_candidate", FIXTURE_CASES)
def test_six_authoritative_fixtures_strict_roundtrip_with_byte_headroom(
    name: str,
    adapter: TypeAdapter[Any],
    ceiling: int,
    is_candidate: bool,
    record_property: Callable[[str, Any], None],
) -> None:
    source = _fixture_bytes(name)
    model = adapter.validate_json(source, strict=True)
    emitted = adapter.dump_json(model)
    assert adapter.validate_json(emitted, strict=True) == model
    wire = adapter.dump_python(model, mode="json")

    source_size = len(source)
    emitted_size = len(emitted)
    assert source_size <= ceiling
    assert emitted_size <= ceiling
    record_property("fixture", name)
    record_property("source_bytes", source_size)
    record_property("emitted_bytes", emitted_size)
    record_property("byte_ceiling", ceiling)
    record_property("source_headroom_bytes", ceiling - source_size)
    record_property("emitted_headroom_bytes", ceiling - emitted_size)
    if is_candidate:
        assert "not capacity proof" in CANDIDATE_FIXTURE_STATUS
        record_property("capacity_claim", CANDIDATE_FIXTURE_STATUS)
    if "_request." in name:
        source_wire = json.loads(source)
        assert all("gross_amount_requested" not in route for route in source_wire["order_routes"])
        assert all("gross_amount_requested" not in route for route in wire["order_routes"])
    if name == "rebalancer_plan_result.medium.2-0-0.json":
        # The hand-written medium plan sells at a gain and fills every tax part a sale can (B3 of project 67, test 22).
        solution = wire["primary_solution"]
        assert any(row["kind"] == "sell" and _money_wire_fraction(row["realized_gain"]) > 0 for row in solution["order_rows"])
        assert solution["tax_basket_rows"] and solution["tax_scope_rows"] and solution["asset_type_tax_rows"] and solution["transfers"] and solution["cash_rows"]


FIXED_DECIMAL_ADAPTER = TypeAdapter(PlannerFixedDecimal)
INTEGER_TEXT_ADAPTER = TypeAdapter(PlannerIntegerText)
WHOLE_QUANTITY_STEP_ADAPTER = TypeAdapter(PlannerWholeQuantityStep)
POSITIVE_WHOLE_DECIMAL_ADAPTER = TypeAdapter(PlannerPositiveWholeDecimal)

WHOLE_QUANTITY_STEP_CASES = (
    pytest.param("1", True, id="one"),
    pytest.param("0", True, id="zero"),
    pytest.param("-1", True, id="negative-one"),
    pytest.param("1" * 96, True, id="positive-max-length"),
    pytest.param("-" + "1" * 95, True, id="negative-max-length"),
    pytest.param("1.5", False, id="fractional"),
    pytest.param("+1", False, id="leading-plus"),
    pytest.param("01", False, id="leading-zero"),
    pytest.param("-0", False, id="negative-zero"),
    pytest.param("-0.000", False, id="negative-zero-decimal"),
    pytest.param("", False, id="empty"),
    pytest.param("1" * 97, False, id="positive-overlength"),
    pytest.param("-" + "1" * 96, False, id="negative-overlength"),
    pytest.param(1, False, id="json-positive-integer"),
    pytest.param(0, False, id="json-zero"),
    pytest.param(-1, False, id="json-negative-integer"),
    pytest.param(1.5, False, id="json-number"),
)


@pytest.mark.parametrize(("value", "accepted"), WHOLE_QUANTITY_STEP_CASES)
def test_planner_whole_quantity_step_strictly_accepts_only_canonical_signed_bounded_integer_strings(
    value: Any,
    accepted: bool,
) -> None:
    if not accepted:
        _reject(WHOLE_QUANTITY_STEP_ADAPTER, value)
        return

    parsed = WHOLE_QUANTITY_STEP_ADAPTER.validate_json(_wire(value), strict=True)
    assert isinstance(parsed, str)
    assert parsed == value
    assert WHOLE_QUANTITY_STEP_ADAPTER.validate_json(WHOLE_QUANTITY_STEP_ADAPTER.dump_json(parsed), strict=True) == parsed


def test_whole_quantity_step_schema_is_signed_request_only_while_output_whole_decimal_stays_positive() -> None:
    keys = ("type", "pattern", "minLength", "maxLength")

    def contract(schema: JsonObject) -> JsonObject:
        return {key: schema[key] for key in keys}

    signed_contract = {
        "type": "string",
        "pattern": r"^(?:0|[1-9][0-9]*|-[1-9][0-9]*)$",
        "minLength": 1,
        "maxLength": 96,
    }
    positive_contract = {
        "type": "string",
        "pattern": r"^[1-9][0-9]*$",
        "minLength": 1,
        "maxLength": 96,
    }

    assert contract(WHOLE_QUANTITY_STEP_ADAPTER.json_schema()) == signed_contract
    assert contract(POSITIVE_WHOLE_DECIMAL_ADAPTER.json_schema()) == positive_contract
    assert signed_contract["pattern"] != positive_contract["pattern"]
    for pattern in (signed_contract["pattern"], positive_contract["pattern"]):
        re.compile(pattern)
        assert not any(fragment in pattern for fragment in ("(?=", "(?!", "(?<=", "(?<!"))

    capability_schema = TypeAdapter(WholeQuantityCapability).json_schema()
    assert contract(capability_schema["properties"]["quantity_step"]) == signed_contract

    for adapter in (PAC_PLAN_INPUT_ADAPTER, REBALANCER_PLAN_INPUT_ADAPTER):
        schema = generate_tool_schema(adapter, "validation")
        assert contract(schema["$defs"]["WholeQuantityCapability"]["properties"]["quantity_step"]) == signed_contract
        assert "WholeQuantityInstruction" not in schema["$defs"]

    for adapter in (PAC_PLAN_OUTPUT_ADAPTER, REBALANCER_PLAN_OUTPUT_ADAPTER):
        schema = generate_tool_schema(adapter, "serialization")
        assert contract(schema["$defs"]["WholeQuantityInstruction"]["properties"]["quantity_step"]) == positive_contract
        assert "WholeQuantityCapability" not in schema["$defs"]

    for value in ("1", "1" * 96):
        parsed = POSITIVE_WHOLE_DECIMAL_ADAPTER.validate_json(_wire(value), strict=True)
        assert POSITIVE_WHOLE_DECIMAL_ADAPTER.validate_json(POSITIVE_WHOLE_DECIMAL_ADAPTER.dump_json(parsed), strict=True) == value
    for value in ("0", "-1", "1.5", "+1", "01", "1" * 97):
        _reject(POSITIVE_WHOLE_DECIMAL_ADAPTER, value)


@pytest.mark.parametrize("quantity_step", ("0", "-1"))
def test_option_b_whole_quantity_step_defers_nonpositive_semantics_to_the_downstream_issue(
    quantity_step: str,
) -> None:
    payload = _rebalancer_request()
    broker = _find(payload["brokers"], "broker_id", "broker-alpha")
    capability = _find(broker["capabilities"], "capability_id", "cap-alpha-eur-whole")
    assert capability["kind"] == "whole_quantity"
    capability["quantity_step"] = quantity_step

    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_INPUT_ADAPTER, payload)
    wire = REBALANCER_PLAN_INPUT_ADAPTER.dump_python(model, mode="json")
    emitted_broker = _find(wire["brokers"], "broker_id", "broker-alpha")
    emitted_capability = _find(emitted_broker["capabilities"], "capability_id", "cap-alpha-eur-whole")

    assert emitted_capability["quantity_step"] == quantity_step
    assert "allocation.nonpositive_quantity_step" in get_args(PlannerIssueCode)


@pytest.mark.parametrize(
    "value",
    (
        "",
        " ",
        "+1",
        "01",
        "-01",
        ".1",
        "1.",
        "1e3",
        "1E+3",
        "1,25",
        "NaN",
        "nan",
        "Infinity",
        "-Infinity",
        "-0",
        "-0.000",
        "1" * 97,
    ),
)
def test_option_b_fixed_decimal_rejects_malformed_noncanonical_nonfinite_and_overlength_strings(value: str) -> None:
    _reject(FIXED_DECIMAL_ADAPTER, value)


@pytest.mark.parametrize("value", ("0", "0.0", "1", "-1", "1.2300", "-999999.0001"))
def test_option_b_fixed_decimal_accepts_canonical_fixed_point_strings(value: str) -> None:
    model = FIXED_DECIMAL_ADAPTER.validate_json(_wire(value), strict=True)
    assert model == value


@pytest.mark.parametrize("value", (0, 1, -1, 1.25, None, True))
def test_option_b_fixed_decimal_rejects_json_numbers_and_other_non_strings(value: Any) -> None:
    _reject(FIXED_DECIMAL_ADAPTER, value)


PLANNER_NUMERIC_ZERO_REGEX_CASES = (
    pytest.param(FIXED_DECIMAL_ADAPTER, ("0", "0.000"), ("-0", "-0.000"), id="fixed-decimal"),
    pytest.param(INTEGER_TEXT_ADAPTER, ("0",), ("-0", "0.000", "-0.000"), id="integer-text"),
)


@pytest.mark.parametrize(("adapter", "accepted", "rejected"), PLANNER_NUMERIC_ZERO_REGEX_CASES)
def test_backend_and_exported_numeric_text_regexes_have_identical_canonical_zero_semantics(
    adapter: TypeAdapter[Any],
    accepted: tuple[str, ...],
    rejected: tuple[str, ...],
) -> None:
    schema = adapter.json_schema()
    pattern = schema["pattern"]
    assert not any(fragment in pattern for fragment in ("(?=", "(?!", "(?<=", "(?<!"))

    exported_patterns = {
        node["pattern"]
        for root_adapter, mode in (
            (PAC_PLAN_INPUT_ADAPTER, "validation"),
            (REBALANCER_PLAN_INPUT_ADAPTER, "validation"),
            (PAC_PLAN_OUTPUT_ADAPTER, "serialization"),
            (REBALANCER_PLAN_OUTPUT_ADAPTER, "serialization"),
        )
        for node in walk_schema(generate_tool_schema(root_adapter, mode))
        if isinstance(node.get("pattern"), str)
    }
    assert pattern in exported_patterns

    for value in accepted:
        assert adapter.validate_json(_wire(value), strict=True) == value
        assert re.fullmatch(pattern, value)
    for value in rejected:
        _reject(adapter, value)
        assert re.fullmatch(pattern, value) is None


def test_option_b_shape_layer_accepts_economically_invalid_but_lexically_valid_strings() -> None:
    payload = _fixture("pac_plan_request.candidate-max.2-0-0.json")
    model, _emitted = _strict_roundtrip(PAC_PLAN_INPUT_ADAPTER, payload)
    wire = PAC_PLAN_INPUT_ADAPTER.dump_python(model, mode="json")

    asset = _find(wire["assets"], "asset_id", "asset-01")
    broker = _find(wire["brokers"], "broker_id", "broker-eur")
    cash = _find(wire["existing_cash"], "cash_id", "cash-eur")
    route = _find(wire["order_routes"], "route_id", "route-01-eur")
    target = _find(wire["target_weights"], "asset_id", "asset-01")

    # C0b.1: the currency quantum is no longer a wire input (babel derives it).
    assert "currency_specs" not in wire
    assert asset["quote"]["amount"] == "-10"
    assert asset["quote"]["quote_base_quantity"] == "0"
    assert _find(asset["exposures"], "dimension", "asset_type")["weight"] == "1.25"
    assert _find(broker["capabilities"], "capability_id", "cap-eur-whole")["quantity_step"] == "0"
    assert _find(broker["fee_schedules"], "fee_schedule_id", "fee-eur-buy")["rate"] == "1.5"
    assert cash["available"]["amount"] == "-1"
    assert cash["selected"]["amount"] == "2"
    assert route["minimum_if_active"]["quantity"] == "-1"
    assert route["execution_margin_rate"] == "1.1"
    assert target["weight"] == "-0.25"


def test_option_b_shape_layer_accepts_foreign_key_contradictions_for_future_normalizer() -> None:
    payload = _pac_request()
    route = _find(payload["order_routes"], "route_id", "route-asset-one-broker-one-buy")
    target = _find(payload["target_weights"], "asset_id", "asset-one")
    cash = _find(payload["existing_cash"], "cash_id", "cash-broker-one-eur")
    asset = _find(payload["assets"], "asset_id", "asset-one")

    route["asset_id"] = "asset-not-in-snapshot"
    route["broker_id"] = "broker-not-in-snapshot"
    route["fee_schedule_id"] = "fee-not-in-snapshot"
    target["asset_id"] = "asset-not-in-snapshot"
    cash["broker_id"] = "broker-not-in-snapshot"
    asset["quote"]["provenance_id"] = "provenance-not-in-snapshot"

    model, _emitted = _strict_roundtrip(PAC_PLAN_INPUT_ADAPTER, payload)
    wire = PAC_PLAN_INPUT_ADAPTER.dump_python(model, mode="json")
    emitted_route = _find(wire["order_routes"], "route_id", "route-asset-one-broker-one-buy")
    assert emitted_route["asset_id"] == "asset-not-in-snapshot"
    assert emitted_route["broker_id"] == "broker-not-in-snapshot"


def test_domain_broker_active_is_required_while_manual_broker_excludes_it() -> None:
    adapter = TypeAdapter(PlannerBrokerIdentity)
    domain = {
        "kind": "domain_broker",
        "source_broker_id": "17",
        "name": "Synthetic domain broker",
        "active": False,
    }
    model, _emitted = _strict_roundtrip(adapter, domain)
    assert adapter.dump_python(model, mode="json")["active"] is False

    missing_active = deepcopy(domain)
    missing_active.pop("active")
    _reject(adapter, missing_active)

    manual = {"kind": "manual_broker", "name": "Synthetic manual broker"}
    _strict_roundtrip(adapter, manual)
    manual["active"] = True
    _reject(adapter, manual)


DOMAIN_BROKER_SOURCE_ONLY_FIELD_CASES = (
    pytest.param("allow_cash_overdraft", False, id="allow-cash-overdraft"),
    pytest.param("allow_asset_shorting", False, id="allow-asset-shorting"),
    pytest.param("execution_profile_status", "supported", id="execution-profile-status"),
    pytest.param("opened_at", "2024-01-01", id="opened-at"),
)


@pytest.mark.parametrize(
    ("source_only_field", "source_value"),
    DOMAIN_BROKER_SOURCE_ONLY_FIELD_CASES,
)
def test_domain_broker_strictly_rejects_source_only_fields(
    source_only_field: str,
    source_value: Any,
) -> None:
    adapter = TypeAdapter(PlannerBrokerIdentity)
    domain = {
        "kind": "domain_broker",
        "source_broker_id": "17",
        "name": "Synthetic domain broker",
        "active": False,
        source_only_field: source_value,
    }

    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_json(_wire(domain), strict=True)

    errors = exc_info.value.errors(include_url=False)
    assert len(errors) == 1
    assert errors[0]["type"] == "extra_forbidden"
    assert errors[0]["loc"][-1] == source_only_field


PLANNER_ISSUE_ADAPTER = TypeAdapter(PlannerIssue)
PLANNER_ISSUE_CODE_ADAPTER = TypeAdapter(PlannerIssueCode)

EXPECTED_PLANNER_ISSUE_CODES = (
    "allocation.asset_inactive_not_buyable",
    "allocation.asset_type_missing",
    "allocation.bound_max_below_current",
    "allocation.bound_min_above_max",
    "allocation.bounds_min_sum_exceeds_reference",
    "allocation.bounds_unsatisfiable",
    "allocation.broker_execution_profile_unsupported",
    "allocation.broker_inactive",
    "allocation.capacity_unsupported",
    # Lot ZB (project 67): a plan of the wide model, published with a cash limit missed by its rounding (a few cents).
    "allocation.cash_limit_exceeded_by_rounding",
    "allocation.cash_selection_invalid",
    "allocation.classification_geography_missing",
    "allocation.classification_invalid",
    "allocation.classification_sector_missing",
    "allocation.coefficient_envelope_unsupported",
    "allocation.currency_mismatch",
    "allocation.deployment_omitted",
    "allocation.duplicate_id",
    "allocation.dynamic_fee_unsupported",
    "allocation.economic_share_out_of_range",
    "allocation.execution_margin_missing",
    "allocation.execution_margin_rate_out_of_range",
    "allocation.exposure_total_exceeds_one",
    "allocation.exposure_weight_out_of_range",
    "allocation.fee_floor_exceeds_cap",
    "allocation.fee_rate_out_of_range",
    "allocation.fee_schedule_missing",
    "allocation.funding_cap_negative",
    "allocation.fx_rate_inconsistent",
    "allocation.fx_rate_missing",
    "allocation.fx_spread_rate_out_of_range",
    "allocation.identity_fx_rate_not_allowed",
    "allocation.invalid_quote_basis",
    "allocation.negative_cash_unsupported",
    "allocation.negative_contribution",
    "allocation.negative_fee_amount",
    "allocation.negative_inventory_unsupported",
    "allocation.no_additional_buy_feasible",
    "allocation.no_positive_order_fundable",
    "allocation.no_selected_funding",
    "allocation.nonpositive_fx_rate",
    "allocation.nonpositive_order_amount_step",
    "allocation.nonpositive_price",
    "allocation.nonpositive_quantity_step",
    "allocation.order_amount_step_missing",
    "allocation.order_cap_nonpositive",
    "allocation.order_minimum_exceeds_cap",
    "allocation.order_minimum_negative",
    "allocation.planning_quantity_negative",
    "allocation.price_missing",
    "allocation.price_order_invalid",
    "allocation.provenance_not_found",
    "allocation.provenance_stale_confirmed",
    "allocation.quote_base_quantity_missing",
    "allocation.reference_not_found",
    "allocation.route_priority_negative",
    "allocation.saved_fx_invalid",
    "allocation.solver_limit_no_incumbent",
    # Lot SE (project 67): SCIP failed inside a stage after a plan was held; the plan is published, not proven.
    "allocation.solver_numerical_error",
    "allocation.target_total_not_one",
    "allocation.target_weight_missing",
    "allocation.target_weight_out_of_range",
    "allocation.valuation_currency_missing",
    "allocation.wac_missing",
    "allocation.zero_selected_funding",
    "pac_allocator.cash_weight_unsupported",
    "pac_allocator.initial_holding_forbidden",
    "pac_allocator.sell_forbidden",
    "portfolio_rebalancer.carried_loss_negative",
    "portfolio_rebalancer.cost_basis_negative",
    "portfolio_rebalancer.holdings_missing",
    "portfolio_rebalancer.nonpositive_current_portfolio",
    "portfolio_rebalancer.sell_fee_missing",
    "portfolio_rebalancer.sell_inventory_exceeded",
    "portfolio_rebalancer.tax_basket_unknown",
    "portfolio_rebalancer.tax_data_missing",
    "portfolio_rebalancer.tax_rate_missing",
    "portfolio_rebalancer.tax_rate_out_of_range",
    "portfolio_rebalancer.withholding_missing",
)

SUPERSEDED_PLANNER_ISSUE_CODES = (
    # Contract 2.0.0 (A4, project 67): M19 takes the route's «required minimum» out; D14 takes out the codes of the two-phase
    # SELL and of the old fiscal rows (a fiscal currency per Asset, netting across currencies), which B3 and C2 rebuild.
    "allocation.required_min_notional_unfunded",
    "allocation.required_buy_sell_conflict",
    "allocation.tax_netting_unsupported",
    "allocation.fiscal_currency_missing",
    "portfolio_rebalancer.baseline_incumbent_missing",
    "portfolio_rebalancer.sell_irreducibility_unresolved",
    "portfolio_rebalancer.sell_to_idle_forbidden",
    "allocation.target_weights_not_one",
    "allocation.reference_unknown",
    "allocation.selected_cash_exceeds_available",
    "allocation.fee_bounds_invalid",
    "allocation.fx_rate_invalid",
    "allocation.cardinality_exceeded",
    "allocation.fx_quote_stale_unconfirmed",
    "portfolio_rebalancer.pmc_missing",
    "portfolio_rebalancer.fiscal_currency_missing",
    "allocation.fx_buffer_rate_out_of_range",
    "allocation.fx_cycle_invalid",
    "allocation.fx_multi_hop_unsupported",
    "allocation.fx_quote_missing",
    "allocation.identity_fx_quote_not_allowed",
    "allocation.identity_valuation_rate_not_allowed",
    "allocation.negative_fx_fee",
    "allocation.nonpositive_fx_source_step",
    "allocation.nonpositive_valuation_rate",
    "allocation.saved_fx_missing",
    "allocation.wac_fx_missing",
    # C0b.1: the quantum comes from babel, so no planner input can be missing or
    # non-positive any more. The domain copy keeps its own
    # allocation.currency_spec_missing in PortfolioPlannerSourceIssueCode.
    "allocation.currency_minor_unit_nonpositive",
    "allocation.currency_spec_missing",
    # Contract compaction: the quote no longer carries a freshness or a reference
    # date, so the planner cannot report a stale or undated price. The
    # allocation-source API keeps its own allocation.price_date_missing in
    # PortfolioPlannerSourceIssueCode.
    "allocation.price_date_missing",
    "allocation.stale_age_negative",
    "allocation.stale_observation_not_accepted",
)


def _catalogue_issue_specimen(code: str) -> JsonObject:
    return {
        "code": code,
        "severity": "info",
        "kind": "info",
        "path": {"kind": "section", "section": "result"},
        "message_key": code,
        "params": [],
    }


def test_planner_issue_code_catalogue_is_exact_closed_and_sorted() -> None:
    assert len(EXPECTED_PLANNER_ISSUE_CODES) == 79
    assert EXPECTED_PLANNER_ISSUE_CODES == tuple(sorted(EXPECTED_PLANNER_ISSUE_CODES))
    assert get_args(PlannerIssueCode) == EXPECTED_PLANNER_ISSUE_CODES
    assert PLANNER_ISSUE_CODE_ADAPTER.json_schema()["enum"] == list(EXPECTED_PLANNER_ISSUE_CODES)


@pytest.mark.parametrize("code", EXPECTED_PLANNER_ISSUE_CODES)
def test_every_closed_planner_issue_code_strictly_roundtrips_with_typed_path(code: str) -> None:
    issue = _catalogue_issue_specimen(code)
    model, _emitted = _strict_roundtrip(PLANNER_ISSUE_ADAPTER, issue)
    assert PLANNER_ISSUE_ADAPTER.dump_python(model, mode="json") == issue


def test_well_shaped_future_planner_issue_code_is_rejected() -> None:
    _reject(PLANNER_ISSUE_ADAPTER, _catalogue_issue_specimen("allocation.future_code"))


def test_required_min_notional_unfunded_is_not_a_code() -> None:
    """M19: the route's «required minimum» is gone, so the code that said it could not be funded is gone with it."""
    assert "allocation.required_min_notional_unfunded" not in get_args(PlannerIssueCode)
    _reject(PLANNER_ISSUE_ADAPTER, _catalogue_issue_specimen("allocation.required_min_notional_unfunded"))


@pytest.mark.parametrize("code", SUPERSEDED_PLANNER_ISSUE_CODES)
def test_superseded_planner_issue_code_aliases_are_rejected(code: str) -> None:
    _reject(PLANNER_ISSUE_ADAPTER, _catalogue_issue_specimen(code))


NON_ISSUE_REASON_CATALOGUE_CASES = (
    pytest.param(
        "FundingActionReasonCode",
        ("allocation.fund_declared_orders",),
        ((PlannerFundingAction, "reason_code"),),
        id="funding-action",
    ),
    pytest.param(
        "DeploymentReasonCode",
        (
            "allocation.deployment_omitted",
            "allocation.no_actions_selected",
            "allocation.no_additional_buy_feasible",
            "allocation.primary_is_deployment",
        ),
        (
            (DeploymentUnavailable, "reason_code"),
            (DeploymentCoincident, "reason_code"),
        ),
        id="deployment",
    ),
    pytest.param(
        "NotProvenReasonCode",
        # Lot SEEDS of project 67: a wide model's plan, and a run's own proof no second run confirmed.
        ("allocation.exact_proof_not_established", "allocation.limits_leave_no_rounding_room", "allocation.proof_not_confirmed"),
        ((NotProvenProof, "reason_code"),),
        id="not-proven",
    ),
)

REASON_ONLY_CODES = (
    "allocation.fund_declared_orders",
    "allocation.no_actions_selected",
    "allocation.primary_is_deployment",
    "allocation.exact_proof_not_established",
    "allocation.limits_leave_no_rounding_room",
    "allocation.proof_not_confirmed",
)


@pytest.mark.parametrize(("type_name", "expected_codes", "bound_fields"), NON_ISSUE_REASON_CATALOGUE_CASES)
def test_non_issue_reason_catalogues_are_closed_and_bound_to_their_fields(
    type_name: str,
    expected_codes: tuple[str, ...],
    bound_fields: tuple[tuple[type[BaseModel], str], ...],
) -> None:
    reason_type = getattr(pac_schema_base, type_name, None)
    assert reason_type is not None, f"{type_name} must be a public closed alias"
    assert get_args(reason_type) == expected_codes

    adapter = TypeAdapter(reason_type)
    schema = adapter.json_schema()
    schema_codes = [schema["const"]] if "const" in schema else schema["enum"]
    assert schema_codes == list(expected_codes)
    for code in expected_codes:
        encoded = _wire(code)
        parsed = adapter.validate_json(encoded, strict=True)
        assert parsed == code
        assert adapter.validate_json(adapter.dump_json(parsed), strict=True) == code

    with pytest.raises(ValidationError):
        adapter.validate_json(_wire("allocation.future_reason"), strict=True)

    for model_type, field_name in bound_fields:
        assert get_args(model_type.model_fields[field_name].annotation) == expected_codes


@pytest.mark.parametrize(
    "reason_code",
    (
        pytest.param("portfolio_rebalancer.future_reason", id="unknown-namespaced"),
        pytest.param("SELL_IRREDUCIBILITY_UNRESOLVED", id="uppercase-legacy-name"),
    ),
)
def test_not_proven_reason_code_rejects_unknown_namespaced_and_uppercase_values(reason_code: str) -> None:
    adapter = TypeAdapter(NotProvenReasonCode)
    with pytest.raises(ValidationError):
        adapter.validate_json(_wire(reason_code), strict=True)


@pytest.mark.parametrize("code", REASON_ONLY_CODES)
def test_reason_only_codes_do_not_pollute_planner_issue_catalogue(code: str) -> None:
    assert code not in EXPECTED_PLANNER_ISSUE_CODES
    _reject(PLANNER_ISSUE_ADAPTER, _catalogue_issue_specimen(code))


INACTIVE_BROKER_ID = "broker-inactive"
INACTIVE_BUY_ROUTE_PATH = {
    "kind": "field",
    "section": "routing",
    "entity_kind": "order_route",
    "entity_id": "buy-route-inactive",
    "field": "broker_id",
}

BROKER_INACTIVE_EXECUTABLE_CASES = (
    pytest.param(
        "capability",
        {
            "kind": "field",
            "section": "brokers",
            "entity_kind": "broker",
            "entity_id": INACTIVE_BROKER_ID,
            "field": "capabilities",
        },
        id="capability",
    ),
    pytest.param(
        "funding_route",
        {
            "kind": "field",
            "section": "funding",
            "entity_kind": "funding_route",
            "entity_id": "funding-route-inactive",
            "field": "broker_id",
        },
        id="funding-route",
    ),
    pytest.param(
        "buy_route",
        INACTIVE_BUY_ROUTE_PATH,
        id="buy-route",
    ),
    pytest.param(
        "sell_route",
        {
            "kind": "field",
            "section": "routing",
            "entity_kind": "order_route",
            "entity_id": "sell-route-inactive",
            "field": "broker_id",
        },
        id="sell-route",
    ),
)

BROKER_INACTIVE_TRIGGER_CASES = (
    pytest.param("domain_broker", False, True, True, True, id="inactive-domain-executable"),
    pytest.param("domain_broker", False, False, False, True, id="inactive-domain-custody-only"),
    pytest.param("domain_broker", True, True, False, False, id="active-domain-executable"),
    pytest.param("manual_broker", None, True, False, False, id="manual-executable"),
)


def _inactive_domain_broker_identity() -> JsonObject:
    return {
        "kind": "domain_broker",
        "source_broker_id": "broker-source-inactive",
        "name": "Synthetic inactive broker",
        "active": False,
    }


def _broker_issue(code: str, severity: str, path: JsonObject) -> JsonObject:
    return {
        "code": code,
        "severity": severity,
        "kind": "unsupported",
        "path": deepcopy(path),
        "message_key": code,
        "params": [],
    }


def _broker_inactive_source_warning(broker_id: str = INACTIVE_BROKER_ID) -> JsonObject:
    return _broker_issue(
        "allocation.broker_inactive",
        "warning",
        {
            "kind": "field",
            "section": "brokers",
            "entity_kind": "broker",
            "entity_id": broker_id,
            "field": "active",
        },
    )


def _broker_execution_profile_error() -> JsonObject:
    return _broker_issue(
        "allocation.broker_execution_profile_unsupported",
        "error",
        {
            "kind": "field",
            "section": "brokers",
            "entity_kind": "broker",
            "entity_id": INACTIVE_BROKER_ID,
            "field": "execution_profile_status",
        },
    )


SOURCE_COPY_OPTIONAL_WARNING_CASES = (
    pytest.param("allocation.asset_type_missing", "missing", "asset_class", id="asset-type-missing"),
    pytest.param("allocation.classification_sector_missing", "missing", "classification.sector", id="sector-missing"),
    pytest.param("allocation.classification_geography_missing", "missing", "classification.geography", id="geography-missing"),
    pytest.param("allocation.classification_invalid", "invalid", "classification", id="classification-invalid"),
)


@pytest.mark.parametrize(("code", "kind", "field"), SOURCE_COPY_OPTIONAL_WARNING_CASES)
def test_source_copy_optional_asset_and_classification_issues_remain_noncontrolling_warnings(
    code: str,
    kind: str,
    field: str,
) -> None:
    issue = {
        "code": code,
        "severity": "warning",
        "kind": kind,
        "path": {
            "kind": "field",
            "section": "assets",
            "entity_kind": "asset",
            "entity_id": "asset-one",
            "field": field,
        },
        "message_key": code,
        "params": [],
    }
    parsed_issue, _issue_wire = _strict_roundtrip(PLANNER_ISSUE_ADAPTER, issue)
    assert PLANNER_ISSUE_ADAPTER.dump_python(parsed_issue, mode="json") == issue

    ready = _pac_no_op_result()
    ready["issues"] = [issue]
    parsed_result, _result_wire = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, ready)
    wire_result = PAC_PLAN_OUTPUT_ADAPTER.dump_python(parsed_result, mode="json")
    assert wire_result["availability"] == "ready"
    assert wire_result["issues"] == [issue]


@pytest.mark.parametrize("reference_kind,path", BROKER_INACTIVE_EXECUTABLE_CASES)
def test_downstream_normalizer_spec_rejects_every_inactive_broker_executable_reference(reference_kind: str, path: JsonObject) -> None:
    identity, _identity_wire = _strict_roundtrip(TypeAdapter(PlannerBrokerIdentity), _inactive_domain_broker_identity())
    assert identity.active is False
    assert reference_kind in {"capability", "funding_route", "buy_route", "sell_route"}

    issue = _broker_issue("allocation.broker_inactive", "error", path)
    issue_model, _issue_wire = _strict_roundtrip(PLANNER_ISSUE_ADAPTER, issue)
    assert PLANNER_ISSUE_ADAPTER.dump_python(issue_model, mode="json") == issue

    failure = _failure_result("PAC", "unsupported")
    failure["issues"] = [issue]
    result, _result_wire = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, failure)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(result, mode="json")
    assert wire["availability"] == "unsupported"
    assert wire["issues"] == [issue]
    assert not {"outcome", "primary_solution", "deployment"} & wire.keys()


@pytest.mark.parametrize(("identity_kind", "active", "has_executable_reference", "expects_error", "expects_source_warning"), BROKER_INACTIVE_TRIGGER_CASES)
def test_downstream_normalizer_broker_inactive_trigger_is_an_exact_iff_spec(
    identity_kind: str,
    active: bool | None,
    has_executable_reference: bool,
    expects_error: bool,
    expects_source_warning: bool,
) -> None:
    identity = (
        {
            **_inactive_domain_broker_identity(),
            "active": active,
        }
        if identity_kind == "domain_broker"
        else {"kind": "manual_broker", "name": "Synthetic manual broker"}
    )
    parsed, _emitted = _strict_roundtrip(TypeAdapter(PlannerBrokerIdentity), identity)
    wire = TypeAdapter(PlannerBrokerIdentity).dump_python(parsed, mode="json")
    is_inactive_domain = wire["kind"] == "domain_broker" and wire["active"] is False

    assert (is_inactive_domain and has_executable_reference) is expects_error
    assert is_inactive_domain is expects_source_warning


def test_inactive_broker_custody_only_spec_keeps_current_facts_as_noncontrolling_warning() -> None:
    request = _rebalancer_request()
    broker = _find(request["brokers"], "broker_id", "broker-alpha")
    broker["identity"] = _inactive_domain_broker_identity()
    broker["capabilities"] = []
    broker["fee_schedules"] = []
    request["order_routes"] = [route for route in request["order_routes"] if route["broker_id"] != "broker-alpha"]

    parsed_request, _request_wire = _strict_roundtrip(REBALANCER_PLAN_INPUT_ADAPTER, request)
    wire_request = REBALANCER_PLAN_INPUT_ADAPTER.dump_python(parsed_request, mode="json")
    inactive_broker = _find(wire_request["brokers"], "broker_id", "broker-alpha")
    assert inactive_broker["identity"]["active"] is False
    assert inactive_broker["capabilities"] == []
    assert any(holding["broker_id"] == "broker-alpha" for holding in wire_request["holdings"])
    assert not any(route["broker_id"] == "broker-alpha" for route in wire_request["order_routes"])

    warning = _broker_inactive_source_warning("broker-alpha")
    warning_model, _warning_wire = _strict_roundtrip(PLANNER_ISSUE_ADAPTER, warning)
    assert PLANNER_ISSUE_ADAPTER.dump_python(warning_model, mode="json") == warning

    ready = _rebalancer_no_op_result()
    ready["issues"] = [warning]
    parsed_result, _result_wire = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, ready)
    wire_result = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(parsed_result, mode="json")
    assert wire_result["availability"] == "ready"
    assert wire_result["issues"] == [warning]
    assert wire_result["primary_solution"]["asset_rows"]
    assert wire_result["primary_solution"]["funding_actions"] == []
    assert wire_result["primary_solution"]["conversions"] == []
    assert wire_result["primary_solution"]["order_rows"] == []


def test_inactive_broker_cash_spec_preserves_frozen_cash_but_cannot_fund_or_transfer_it() -> None:
    request = _pac_request()
    broker = _find(request["brokers"], "broker_id", "broker-one")
    broker["identity"] = _inactive_domain_broker_identity()
    broker["capabilities"] = []
    broker["fee_schedules"] = []
    request["funding_routes"] = []
    request["order_routes"] = []
    cash = _find(request["existing_cash"], "cash_id", "cash-broker-one-eur")
    cash["selected"]["amount"] = "0"

    parsed, _emitted = _strict_roundtrip(PAC_PLAN_INPUT_ADAPTER, request)
    wire = PAC_PLAN_INPUT_ADAPTER.dump_python(parsed, mode="json")
    frozen_cash = _find(wire["existing_cash"], "cash_id", "cash-broker-one-eur")
    assert frozen_cash["available"]["amount"] == "5.00"
    assert frozen_cash["selected"]["amount"] == "0"
    assert wire["funding_routes"] == []
    assert wire["order_routes"] == []


@pytest.mark.parametrize(
    ("include_inactive_error", "include_execution_profile_error"),
    (
        pytest.param(True, False, id="inactive-only"),
        pytest.param(False, True, id="execution-profile-only"),
        pytest.param(True, True, id="both-independent"),
    ),
)
def test_broker_execution_profile_unsupported_remains_independent_of_broker_inactive(
    include_inactive_error: bool,
    include_execution_profile_error: bool,
) -> None:
    inactive_error = _broker_issue("allocation.broker_inactive", "error", INACTIVE_BUY_ROUTE_PATH)
    execution_profile_error = _broker_execution_profile_error()
    issues = [
        issue
        for included, issue in (
            (include_inactive_error, inactive_error),
            (include_execution_profile_error, execution_profile_error),
        )
        if included
    ]

    failure = _failure_result("PAC", "unsupported")
    failure["issues"] = issues
    parsed, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, failure)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(parsed, mode="json")
    expected_codes = {
        code
        for included, code in (
            (include_inactive_error, "allocation.broker_inactive"),
            (include_execution_profile_error, "allocation.broker_execution_profile_unsupported"),
        )
        if included
    }
    assert {issue["code"] for issue in wire["issues"]} == expected_codes
    assert wire["issues"] == issues
    if include_inactive_error and include_execution_profile_error:
        assert inactive_error["path"] != execution_profile_error["path"]


def _planner_field_path(section: str, entity_kind: str, entity_id: str, field: str) -> JsonObject:
    return {
        "kind": "field",
        "section": section,
        "entity_kind": entity_kind,
        "entity_id": entity_id,
        "field": field,
    }


def _normalizer_issue_case(code: str, availability: str, frozen_path: JsonObject | None = None) -> Any:
    return pytest.param(code, availability, "error", frozen_path, id=f"{availability}-{code}")


PRICE_AMOUNT_ISSUE_PATH = _planner_field_path("assets", "asset", "asset-one", "quote.amount")
QUOTE_BASIS_ISSUE_PATH = _planner_field_path("assets", "asset", "asset-one", "quote.quote_base_quantity")
EXPOSURE_WEIGHT_ISSUE_PATH = _planner_field_path("assets", "asset", "asset-one", "exposures.weight")
TARGET_WEIGHT_ISSUE_PATH = _planner_field_path("targets", "asset", "asset-one", "weight")
TARGET_TOTAL_ISSUE_PATH = {"kind": "section", "section": "targets"}
ECONOMIC_SHARE_ISSUE_PATH = _planner_field_path("holdings", "holding", "holding-one", "economic_share")
CASH_SELECTION_ISSUE_PATH = _planner_field_path("cash", "cash", "cash-one", "selected")
FX_RATE_ISSUE_PATH = _planner_field_path("fx", "fx_rate", "EUR/USD", "rate")
TAX_RATE_ISSUE_PATH = _planner_field_path("policy", "asset", "asset-one", "tax_rate")
UNFROZEN_ISSUE_PATH_SPECIMEN = {"kind": "section", "section": "input"}

DOWNSTREAM_NORMALIZER_ISSUE_CASES = (
    _normalizer_issue_case("allocation.nonpositive_price", "invalid", PRICE_AMOUNT_ISSUE_PATH),
    _normalizer_issue_case("allocation.invalid_quote_basis", "invalid", QUOTE_BASIS_ISSUE_PATH),
    _normalizer_issue_case("allocation.exposure_weight_out_of_range", "invalid", EXPOSURE_WEIGHT_ISSUE_PATH),
    # C0b.3: same frozen path as the per-weight range issue; the real issue also
    # names its dimension in a text param (asserted by the normalizer tests).
    _normalizer_issue_case("allocation.exposure_total_exceeds_one", "invalid", EXPOSURE_WEIGHT_ISSUE_PATH),
    _normalizer_issue_case("allocation.target_weight_out_of_range", "invalid", TARGET_WEIGHT_ISSUE_PATH),
    _normalizer_issue_case("allocation.target_total_not_one", "invalid", TARGET_TOTAL_ISSUE_PATH),
    _normalizer_issue_case("allocation.economic_share_out_of_range", "invalid", ECONOMIC_SHARE_ISSUE_PATH),
    _normalizer_issue_case("allocation.planning_quantity_negative", "invalid"),
    _normalizer_issue_case("allocation.negative_inventory_unsupported", "unsupported"),
    _normalizer_issue_case("allocation.negative_cash_unsupported", "unsupported"),
    _normalizer_issue_case("allocation.cash_selection_invalid", "invalid", CASH_SELECTION_ISSUE_PATH),
    _normalizer_issue_case("allocation.negative_contribution", "invalid"),
    _normalizer_issue_case("allocation.funding_cap_negative", "invalid"),
    _normalizer_issue_case("allocation.nonpositive_quantity_step", "invalid"),
    _normalizer_issue_case("allocation.nonpositive_order_amount_step", "invalid"),
    _normalizer_issue_case("allocation.order_minimum_negative", "invalid"),
    _normalizer_issue_case("allocation.order_cap_nonpositive", "invalid"),
    _normalizer_issue_case("allocation.order_minimum_exceeds_cap", "invalid"),
    _normalizer_issue_case("allocation.route_priority_negative", "invalid"),
    _normalizer_issue_case("allocation.execution_margin_rate_out_of_range", "invalid"),
    _normalizer_issue_case("allocation.negative_fee_amount", "invalid"),
    _normalizer_issue_case("allocation.fee_rate_out_of_range", "invalid"),
    _normalizer_issue_case("allocation.fee_floor_exceeds_cap", "invalid"),
    _normalizer_issue_case("allocation.nonpositive_fx_rate", "invalid", FX_RATE_ISSUE_PATH),
    _normalizer_issue_case("allocation.identity_fx_rate_not_allowed", "invalid", FX_RATE_ISSUE_PATH),
    _normalizer_issue_case("allocation.fx_spread_rate_out_of_range", "invalid"),
    _normalizer_issue_case("portfolio_rebalancer.tax_rate_missing", "needs_input", TAX_RATE_ISSUE_PATH),
    _normalizer_issue_case("portfolio_rebalancer.tax_rate_out_of_range", "invalid", TAX_RATE_ISSUE_PATH),
    _normalizer_issue_case("allocation.wac_missing", "needs_input"),
    _normalizer_issue_case("allocation.fx_rate_missing", "needs_input", FX_RATE_ISSUE_PATH),
    # FX conversion fix: once every needed pair is present, the rates are checked for coherence.
    _normalizer_issue_case("allocation.fx_rate_inconsistent", "invalid", FX_RATE_ISSUE_PATH),
    _normalizer_issue_case("portfolio_rebalancer.cost_basis_negative", "invalid"),
    _normalizer_issue_case("portfolio_rebalancer.withholding_missing", "needs_input"),
    _normalizer_issue_case("portfolio_rebalancer.carried_loss_negative", "invalid"),
    _normalizer_issue_case("allocation.duplicate_id", "invalid"),
    _normalizer_issue_case("allocation.reference_not_found", "invalid"),
    _normalizer_issue_case("allocation.provenance_not_found", "invalid"),
    _normalizer_issue_case("allocation.currency_mismatch", "invalid"),
    _normalizer_issue_case("allocation.capacity_unsupported", "unsupported"),
    _normalizer_issue_case("allocation.coefficient_envelope_unsupported", "unsupported"),
)

NORMALIZER_ISSUE_KIND_BY_AVAILABILITY = {
    "needs_input": "missing",
    "invalid": "invalid",
    "unsupported": "unsupported",
}


@pytest.mark.parametrize(
    ("code", "availability", "severity", "frozen_path"),
    DOWNSTREAM_NORMALIZER_ISSUE_CASES,
)
def test_downstream_normalizer_issue_code_precedence_map_is_frozen(
    code: str,
    availability: str,
    severity: str,
    frozen_path: JsonObject | None,
) -> None:
    # A section path is only a schema-valid specimen when the handoff did not
    # freeze an exact path; it deliberately defines no additional path policy.
    path = deepcopy(frozen_path if frozen_path is not None else UNFROZEN_ISSUE_PATH_SPECIMEN)
    issue = {
        "code": code,
        "severity": severity,
        "kind": NORMALIZER_ISSUE_KIND_BY_AVAILABILITY[availability],
        "path": path,
        "message_key": code,
        "params": [],
    }
    parsed_issue, _issue_wire = _strict_roundtrip(PLANNER_ISSUE_ADAPTER, issue)
    wire_issue = PLANNER_ISSUE_ADAPTER.dump_python(parsed_issue, mode="json")

    assert wire_issue["code"] == code
    assert wire_issue["severity"] == "error"
    assert wire_issue["kind"] == NORMALIZER_ISSUE_KIND_BY_AVAILABILITY[availability]
    assert wire_issue["path"] == path
    if frozen_path is not None:
        assert wire_issue["path"] == frozen_path

    failure = _failure_result("Rebalancer", availability)
    failure["issues"] = [issue]
    parsed_result, _result_wire = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, failure)
    wire_result = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(parsed_result, mode="json")

    assert wire_result["result_state"] == availability
    assert wire_result["availability"] == availability
    assert wire_result["issues"] == [issue]
    assert not {"outcome", "primary_solution", "deployment"} & wire_result.keys()


def test_pac_policy_accepts_only_proportional() -> None:
    payload = _pac_request()
    payload["policy"] = "proportional"
    model, _emitted = _strict_roundtrip(PAC_PLAN_INPUT_ADAPTER, payload)
    assert PAC_PLAN_INPUT_ADAPTER.dump_python(model, mode="json")["policy"] == "proportional"


def test_pac_min_fragmentation_policy_is_wire_invalid() -> None:
    # C0b.2: min_fragmentation survives only as an internal ExactScenario branch.
    payload = _pac_request()
    payload["policy"] = "min_fragmentation"
    with pytest.raises(ValidationError) as exc_info:
        PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)

    errors = exc_info.value.errors(include_url=False)
    assert [(error["type"], error["loc"][-1]) for error in errors] == [("literal_error", "policy")]


@pytest.mark.parametrize(
    ("adapter", "payload_factory"),
    (
        pytest.param(PAC_PLAN_INPUT_ADAPTER, _pac_request, id="pac"),
        pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, _rebalancer_request, id="rebalancer"),
    ),
)
def test_request_roots_reject_the_withdrawn_currency_specs_input(adapter: TypeAdapter[Any], payload_factory: Any) -> None:
    # C0b.1: the quantum is derived from babel; the former input is now an extra field.
    payload = payload_factory()
    _strict_roundtrip(adapter, payload)
    payload["currency_specs"] = [{"currency": "EUR", "minor_unit": "0.01"}]
    _assert_extra_forbidden(adapter, payload, "currency_specs")


# --- Contract compaction (plan-phase00PacContractCompaction §1-§2) ---------------------------
#
# The wire is compact: a field whose value is the neutral default may be omitted, and
# validation fills it with that default as a model INSTANCE, never a dict.  Three inputs
# that no longer influence a plan are withdrawn and become extra fields.

_NO_SCHEMA_DEFAULT = "<no default in schema>"


def _select(node: Any, path: tuple[Any, ...]) -> Any:
    """Walk a payload or a validated model; a ``(field, value)`` step selects one list row by identity."""
    for step in path:
        if isinstance(step, tuple):
            field, value = step
            rows = [row for row in node if (row.get(field) if isinstance(row, dict) else getattr(row, field)) == value]
            assert len(rows) == 1, f"expected exactly one {field}={value!r} row"
            node = rows[0]
        else:
            node = node[step] if isinstance(node, (dict, list)) else getattr(node, step)
    return node


WITHDRAWN_PAC_INPUT_FIELD_CASES = (
    pytest.param(("assets", 0, "quote"), "freshness", {"kind": "fresh"}, id="quote-freshness"),
    pytest.param(("assets", 0, "quote"), "reference_date", "2026-09-15", id="quote-reference-date"),
    pytest.param(("existing_cash", 0), "source_kind", "local_broker_cash", id="existing-cash-source-kind"),
)


@pytest.mark.parametrize(("container_path", "field_name", "value"), WITHDRAWN_PAC_INPUT_FIELD_CASES)
def test_pac_request_rejects_the_withdrawn_quote_and_cash_fields_as_extra_fields(
    container_path: tuple[str | int, ...],
    field_name: str,
    value: Any,
) -> None:
    # `min` has exactly one asset and one cash row, so index 0 is the row this test edits.
    payload = _pac_request()
    container = _select(payload, container_path)
    assert field_name not in container
    container[field_name] = value

    with pytest.raises(ValidationError) as exc_info:
        PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)

    errors = exc_info.value.errors(include_url=False)
    assert [(error["type"], error["loc"]) for error in errors] == [("extra_forbidden", (*container_path, field_name))]


def test_compact_pac_request_fills_every_omitted_default_as_a_model_instance() -> None:
    twin = _compact_pac_request()
    model = PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(twin), strict=True)

    assert type(model) is PacPlannerRequest
    assert model.fx_rates == {}
    assert model.fx_spread_rate == "0"
    assert model.contributions == []
    assert model.funding_routes == []
    assert _select(model, ("brokers", ("broker_id", "broker-one"))).fee_schedules == []
    route = _select(model, ("order_routes", ("route_id", "route-asset-one-broker-one-buy")))
    assert route.execution_margin_rate == "0"
    assert route.fee_schedule_id is None
    # What the twin does say is kept as sent.
    assert route.priority == 1
    assert type(route.minimum_if_active) is WholeQuantityMinimum
    assert type(route.cap) is QuantityOrderCap
    assert [row.cash_id for row in model.existing_cash] == ["cash-broker-one-eur"]

    sparse = deepcopy(twin)
    sparse.pop("existing_cash")
    asset = _find(sparse["assets"], "asset_id", "asset-one")
    asset.pop("exposures")
    broker = _find(sparse["brokers"], "broker_id", "broker-one")
    broker.pop("capabilities")
    broker["fee_schedules"] = [{"fee_schedule_id": "fee-broker-one-buy", "capability_id": "cap-broker-one-eur-whole", "side": "buy"}]
    sparse_route = _find(sparse["order_routes"], "route_id", "route-asset-one-broker-one-buy")
    for key in ("priority", "minimum_if_active", "cap"):
        sparse_route.pop(key)

    model = PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(sparse), strict=True)

    assert model.existing_cash == []
    assert _select(model, ("assets", ("asset_id", "asset-one"))).exposures == []
    filled_broker = _select(model, ("brokers", ("broker_id", "broker-one")))
    assert filled_broker.capabilities == []
    schedule = _select(filled_broker.fee_schedules, (("fee_schedule_id", "fee-broker-one-buy"),))
    assert schedule.fixed_fee is None
    assert schedule.rate == "0"
    assert schedule.variable_floor is None
    assert type(schedule.variable_cap) is NoFeeCap
    filled_route = _select(model, ("order_routes", ("route_id", "route-asset-one-broker-one-buy")))
    assert filled_route.priority == 0
    assert type(filled_route.minimum_if_active) is NoOrderMinimum
    assert type(filled_route.cap) is NoOrderCap
    assert filled_route.execution_margin_rate == "0"


def test_reduced_rebalancer_request_fills_holdings_and_the_tax_lists() -> None:
    payload = _rebalancer_request()
    payload.pop("holdings")
    payload["tax"] = {}

    model = REBALANCER_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)

    assert type(model) is RebalancerPlannerRequest
    assert model.holdings == []
    assert model.tax == RebalancerTaxInput(baskets=[], assets=[], brokers=[], carried_losses=[], cost_bases=[])
    payload.pop("tax")
    assert REBALANCER_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True).tax == model.tax


def test_reduced_pac_request_fills_the_funding_priority() -> None:
    payload = _pac_request()
    payload["contributions"] = [{"contribution_id": "contribution-one", "label": "Monthly", "amount": {"amount": "50", "currency": "EUR"}, "provenance_id": payload["provenance"][0]["provenance_id"]}]
    payload["funding_routes"] = [
        {"funding_route_id": "fund-one", "source": {"kind": "contribution", "contribution_id": "contribution-one"}, "broker_id": payload["brokers"][0]["broker_id"], "currency": "EUR", "transfer_cap": {"amount": "10", "currency": "EUR"}, "provenance_id": payload["provenance"][0]["provenance_id"]},
    ]

    model = PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)

    assert [(row.priority, row.transfer_cap.amount) for row in model.funding_routes] == [(0, "10")]


OPTIONAL_INPUT_FIELD_CASES = (
    pytest.param(PAC_PLAN_INPUT_ADAPTER, _pac_request, ("assets", ("asset_id", "asset-one"), "identity"), "asset_class", id="manual-asset-class"),
    pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, _rebalancer_request, ("assets", ("asset_id", "asset-a"), "identity"), "asset_class", id="domain-asset-class"),
    pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, _rebalancer_request, ("provenance", ("provenance_id", "prov-portfolio")), "source_label", id="domain-copy-source-label"),
    pytest.param(
        PAC_PLAN_INPUT_ADAPTER,
        _pac_request,
        ("brokers", ("broker_id", "broker-one"), "fee_schedules", ("fee_schedule_id", "fee-broker-one-eur-buy")),
        "fixed_fee",
        id="fee-fixed-fee",
    ),
    pytest.param(
        PAC_PLAN_INPUT_ADAPTER,
        _pac_request,
        ("brokers", ("broker_id", "broker-one"), "fee_schedules", ("fee_schedule_id", "fee-broker-one-eur-buy")),
        "variable_floor",
        id="fee-variable-floor",
    ),
    pytest.param(PAC_PLAN_INPUT_ADAPTER, _pac_request, ("order_routes", ("route_id", "route-asset-one-broker-one-buy")), "fee_schedule_id", id="pac-buy-fee-schedule-id"),
    pytest.param(
        REBALANCER_PLAN_INPUT_ADAPTER,
        _rebalancer_request,
        ("order_routes", ("route_id", "route-a-alpha-buy")),
        "fee_schedule_id",
        id="rebalancer-buy-fee-schedule-id",
    ),
)


@pytest.mark.parametrize(("adapter", "factory", "path", "field_name"), OPTIONAL_INPUT_FIELD_CASES)
def test_optional_input_fields_may_be_omitted_and_read_back_as_absent(
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    path: tuple[Any, ...],
    field_name: str,
) -> None:
    payload = factory()
    assert _select(payload, path)[field_name] is not None, "the fixture must state the field for its omission to mean anything"
    _select(payload, path).pop(field_name)

    model = adapter.validate_json(_wire(payload), strict=True)

    assert getattr(_select(model, path), field_name) is None
    assert field_name not in _select(adapter.dump_python(model, mode="json", exclude_defaults=True), path)


REQUIRED_KEPT_INPUT_FIELD_CASES = (
    pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, _rebalancer_request, ("provenance", ("provenance_id", "prov-manual")), "label", id="manual-provenance-label"),
    pytest.param(TypeAdapter(PlannerSellOrderRouteInput), lambda: _medium_sell_route("route-a-alpha-sell"), (), "fee_schedule_id", id="sell-route-fee-schedule-id"),
)


@pytest.mark.parametrize(("adapter", "factory", "path", "field_name"), REQUIRED_KEPT_INPUT_FIELD_CASES)
def test_manual_provenance_label_and_sell_route_fee_schedule_stay_required(adapter: TypeAdapter[Any], factory: PayloadFactory, path: tuple[Any, ...], field_name: str) -> None:
    payload = factory()
    _strict_roundtrip(adapter, payload)
    _select(payload, path).pop(field_name)

    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_json(_wire(payload), strict=True)

    errors = exc_info.value.errors(include_url=False)
    assert [(error["type"], error["loc"][-1]) for error in errors] == [("missing", field_name)]


def test_catalog_asset_class_is_required_but_nullable() -> None:
    assert PlannerCatalogAsset.model_fields["asset_class"].is_required()

    result = _pac_no_op_result()
    catalog_asset = _find(result["catalogs"]["assets"], "asset_id", "asset-one")
    catalog_asset["asset_class"] = None
    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, result)
    assert _select(model, ("catalogs", "assets", ("asset_id", "asset-one"))).asset_class is None

    catalog_asset.pop("asset_class")
    with pytest.raises(ValidationError) as exc_info:
        PAC_PLAN_OUTPUT_ADAPTER.validate_json(_wire(result), strict=True)
    errors = exc_info.value.errors(include_url=False)
    assert [(error["type"], error["loc"][-1]) for error in errors] == [("missing", "asset_class")]


def test_input_defaults_are_optional_in_validation_schema_and_required_in_serialization_schema() -> None:
    assert AllocationStrictModel.model_config.get("json_schema_serialization_defaults_required") is True

    validation = generate_tool_schema(PAC_PLAN_INPUT_ADAPTER, "validation")
    serialization = generate_tool_schema(PAC_PLAN_INPUT_ADAPTER, "serialization")
    assert validation["title"] == serialization["title"] == "PacPlannerRequest"

    assert "fx_rates" not in validation["required"]
    assert validation["properties"]["fx_rates"]["default"] == {}
    assert "fx_rates" in serialization["required"]

    validation_route = validation["$defs"]["PacOrderRouteInput"]
    serialization_route = serialization["$defs"]["PacOrderRouteInput"]
    for field_name, default in (("priority", 0), ("cap", {"kind": "none"})):
        assert field_name not in validation_route["required"], field_name
        assert validation_route["properties"][field_name]["default"] == default, field_name
        assert field_name in serialization_route["required"], field_name
    # A field without a default stays required in both modes.
    assert "route_id" in validation_route["required"]
    assert "route_id" in serialization_route["required"]


_ROUTE_SCHEMA_DEFAULTS: dict[str, Any] = {
    "priority": 0,
    "minimum_if_active": {"kind": "none"},
    "cap": {"kind": "none"},
    "execution_margin_rate": "0",
}
_BUY_ROUTE_SCHEMA_DEFAULTS: dict[str, Any] = {**_ROUTE_SCHEMA_DEFAULTS, "fee_schedule_id": None}
_SHARED_INPUT_SCHEMA_DEFAULTS: dict[str, dict[str, Any]] = {
    "PlannerAssetInput": {"exposures": []},
    "ManualAssetIdentity": {"asset_class": None},
    "DomainAssetIdentity": {"asset_class": None},
    "DomainCopyProvenance": {"source_label": None},
    "PlannerBrokerInput": {"capabilities": [], "fee_schedules": []},
    "BrokerFeeScheduleInput": {"fixed_fee": None, "rate": "0", "variable_floor": None, "variable_cap": {"kind": "none"}},
    "PlannerFundingRouteInput": {"priority": 0, "transfer_cap": None},
    "PlannerAssetTargetInput": {"minimum": None, "maximum": None},
    "PlannerCashTargetInput": {"minimum": None, "maximum": None},
    "PacOrderRouteInput": _BUY_ROUTE_SCHEMA_DEFAULTS,
}
INPUT_SCHEMA_DEFAULT_CASES = (
    pytest.param(PAC_PLAN_INPUT_ADAPTER, {**_SHARED_INPUT_SCHEMA_DEFAULTS, "PacPlannerRequest": ROOT_DEFAULTED_FIELDS}, id="pac"),
    pytest.param(
        REBALANCER_PLAN_INPUT_ADAPTER,
        {
            # No funding routes in the Rebalancer request (B3, project 67), and its BUY routes are not the PAC's class.
            **{name: value for name, value in _SHARED_INPUT_SCHEMA_DEFAULTS.items() if name not in ("PlannerFundingRouteInput", "PacOrderRouteInput")},
            "RebalancerPlannerRequest": REBALANCER_ROOT_SCHEMA_DEFAULTS,
            "RebalancerTaxInput": {"baskets": [], "assets": [], "brokers": [], "carried_losses": [], "cost_bases": []},
            "RebalancerAssetTaxInput": {"foreign_withholding_rate": "0"},
            "PlannerBuyOrderRouteInput": _BUY_ROUTE_SCHEMA_DEFAULTS,
            # A SELL route keeps `fee_schedule_id` required.
            "PlannerSellOrderRouteInput": _ROUTE_SCHEMA_DEFAULTS,
        },
        id="rebalancer",
    ),
)


@pytest.mark.parametrize(("adapter", "expected"), INPUT_SCHEMA_DEFAULT_CASES)
def test_input_schema_defaults_exactly_the_compaction_fields(adapter: TypeAdapter[Any], expected: dict[str, dict[str, Any]]) -> None:
    schema = generate_tool_schema(adapter, "validation")
    objects = {name: node for name, node in schema.get("$defs", {}).items() if isinstance(node.get("properties"), dict)}
    if isinstance(schema.get("properties"), dict):
        objects[schema["title"]] = schema

    # Pydantic omits `required` altogether when every field of a model has a default.
    observed = {name: {field: node["properties"][field].get("default", _NO_SCHEMA_DEFAULT) for field in node["properties"] if field not in node.get("required", [])} for name, node in objects.items()}
    assert {name: fields for name, fields in observed.items() if fields} == expected


EXPLICIT_REQUEST_FIXTURE_CASES = (
    pytest.param("pac_plan_request.min.2-0-0.json", PAC_PLAN_INPUT_ADAPTER, id="pac-min"),
    pytest.param("pac_plan_request.candidate-max.2-0-0.json", PAC_PLAN_INPUT_ADAPTER, id="pac-candidate-max"),
    pytest.param("rebalancer_plan_request.medium.2-0-0.json", REBALANCER_PLAN_INPUT_ADAPTER, id="rebalancer-medium"),
)


@pytest.mark.parametrize(("name", "adapter"), EXPLICIT_REQUEST_FIXTURE_CASES)
def test_explicit_request_fixture_survives_the_defaults_omitted_roundtrip(name: str, adapter: TypeAdapter[Any]) -> None:
    payload = _fixture(name)
    explicit = adapter.validate_json(_wire(payload), strict=True)

    compact = explicit.model_dump(mode="json", exclude_defaults=True)

    # Every explicit fixture spells out at least one default, so the compact form is a real change.
    assert compact != explicit.model_dump(mode="json")
    assert len(_wire(compact)) < len(_wire(payload))
    assert adapter.validate_json(_wire(compact), strict=True) == explicit


def test_compact_twin_is_min_without_its_defaults_and_a_fixed_point_of_the_compact_dump() -> None:
    twin = _compact_pac_request()

    expected = _pac_request()
    for key in ("fx_rates", "fx_spread_rate", "contributions", "funding_routes"):
        expected.pop(key)
    _find(expected["brokers"], "broker_id", "broker-one").pop("fee_schedules")
    route = _find(expected["order_routes"], "route_id", "route-asset-one-broker-one-buy")
    for key in ("execution_margin_rate", "fee_schedule_id"):
        route.pop(key)
    for entry in expected["target_weights"]:
        for key in ("minimum", "maximum"):
            entry.pop(key)
    assert twin == expected

    model = PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(twin), strict=True)
    assert model.model_dump(mode="json", exclude_defaults=True) == twin


def test_target_entries_roundtrip_with_amount_and_share_limits() -> None:
    """Contract 2.0.0 §5: an entry is an Asset or a cash cell, each with an optional minimum and maximum as an amount or a share.
    Asset and cash entries share one list, told apart by ``kind``; the compact dump leaves every absent limit out and reads back."""
    payload = _pac_request()
    payload["target_weights"] = [
        {"kind": "asset", "asset_id": "asset-one", "weight": "1", "minimum": {"kind": "amount", "amount": {"amount": "2", "currency": "EUR"}}, "maximum": {"kind": "share", "share": "0.9"}},
        {"kind": "cash", "broker_id": "broker-one", "currency": "EUR", "weight": "0", "minimum": None, "maximum": {"kind": "amount", "amount": {"amount": "1", "currency": "EUR"}}},
    ]

    model = PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)

    asset, cash = model.target_weights
    assert (asset.kind, asset.minimum.kind, asset.maximum.kind, asset.maximum.share) == ("asset", "amount", "share", "0.9")
    assert (cash.kind, cash.minimum, cash.maximum.kind) == ("cash", None, "amount")
    compact = model.model_dump(mode="json", exclude_defaults=True)
    assert "minimum" not in compact["target_weights"][1]
    assert PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(compact), strict=True) == model


TARGET_ENTRY_REJECTION_CASES = (
    pytest.param({"asset_id": "asset-one", "weight": "1"}, id="no-kind"),
    pytest.param({"kind": "sector", "asset_id": "asset-one", "weight": "1"}, id="unknown-kind"),
    pytest.param({"kind": "asset", "asset_id": "asset-one", "weight": "1", "broker_id": "broker-one"}, id="cash-field-on-an-asset"),
    pytest.param({"kind": "cash", "broker_id": "broker-one", "weight": "0"}, id="cash-without-currency"),
    pytest.param({"kind": "asset", "asset_id": "asset-one", "weight": "1", "minimum": {"kind": "ratio", "share": "0.1"}}, id="unknown-limit-kind"),
    pytest.param({"kind": "asset", "asset_id": "asset-one", "weight": "1", "minimum": {"kind": "amount", "share": "0.1"}}, id="amount-limit-with-a-share"),
    pytest.param({"kind": "asset", "asset_id": "asset-one", "weight": "1", "maximum": {"kind": "share", "share": 0.5}}, id="share-not-a-fixed-decimal-string"),
    pytest.param({"kind": "asset", "asset_id": "asset-one", "weight": "1", "maximum": {"kind": "amount", "amount": {"amount": "1"}}}, id="amount-without-currency"),
)


@pytest.mark.parametrize("entry", TARGET_ENTRY_REJECTION_CASES)
def test_target_entry_shapes_the_contract_does_not_define_are_rejected(entry: JsonObject) -> None:
    payload = _pac_request()
    payload["target_weights"] = [entry]

    with pytest.raises(ValidationError):
        PAC_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)


@pytest.mark.parametrize(("adapter", "request_factory"), [pytest.param(PAC_PLAN_INPUT_ADAPTER, _pac_request, id="pac"), pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, _rebalancer_request, id="rebalancer")])
def test_pac_request_refuses_required_minimum(adapter: TypeAdapter[Any], request_factory: Callable[[], JsonObject]) -> None:
    """M19: a route no longer carries a «required minimum» (the field of «Acquisto obbligatorio»). Anyone who wants a buy obliged
    uses the minimum of the entry (A3), so the schema, which forbids unknown fields, refuses the old one."""
    payload = request_factory()
    payload["order_routes"][0]["required_minimum"] = {"kind": "none"}

    with pytest.raises(ValidationError):
        adapter.validate_json(_wire(payload), strict=True)

    assert "required_minimum" not in PlannerOrderRouteInput.model_fields


# ---------------------------------------------------------------------------
# A4 step 5 (project 67): the ledger's new columns, the cost line, the limits on the rows
# ---------------------------------------------------------------------------


def test_ledger_row_reconciles_with_the_transfer_columns() -> None:
    """Contract 2.0.0 §6.5: a ledger row carries ``transfer_in`` and ``transfer_out`` (between Brokers) and ``foreign_withholding_tax``.
    The schema still checks the identity: spendable = initial + inflows - outflows, the three new columns included."""
    payload = _pac_incumbent_result()
    ledger = _find(payload["primary_solution"]["ledger_rows"], "broker_id", "broker-one")
    ledger.update({"transfer_in": "1", "transfer_out": "1"})  # a round trip changes nothing
    _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)

    broken = _pac_incumbent_result()
    _find(broken["primary_solution"]["ledger_rows"], "broker_id", "broker-one").update({"transfer_in": "1"})
    _reject(PAC_PLAN_OUTPUT_ADAPTER, broken)

    withheld = _pac_incumbent_result()
    _find(withheld["primary_solution"]["ledger_rows"], "broker_id", "broker-one")["foreign_withholding_tax"] = "1"
    _reject(PAC_PLAN_OUTPUT_ADAPTER, withheld)

    negative = _pac_incumbent_result()
    _find(negative["primary_solution"]["ledger_rows"], "broker_id", "broker-one")["transfer_out"] = "-1"
    _reject(PAC_PLAN_OUTPUT_ADAPTER, negative)


@pytest.mark.parametrize("column", ("transfer_in", "transfer_out", "foreign_withholding_tax"))
def test_ledger_row_requires_the_new_columns(column: str) -> None:
    payload = _pac_incumbent_result()
    del _find(payload["primary_solution"]["ledger_rows"], "broker_id", "broker-one")[column]
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)


def test_cost_totals_carry_the_foreign_withholding_tax_line_and_a_no_op_publishes_none() -> None:
    payload = _pac_incumbent_result()
    assert payload["primary_solution"]["costs"]["foreign_withholding_tax"] == _money("0")
    del payload["primary_solution"]["costs"]["foreign_withholding_tax"]
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)

    no_op = _pac_no_op_result()
    no_op["primary_solution"]["costs"]["foreign_withholding_tax"] = _money("1")
    _reject(PAC_PLAN_OUTPUT_ADAPTER, no_op)


def test_pac_asset_row_and_cash_row_publish_their_limits() -> None:
    """Contract §6.2: an Asset row says its minimum and maximum when they are set (amounts in the valuation currency, ``null``
    otherwise), and a PAC cash entry with a limit has a row of its own: the Broker, the currency, its final spendable cash in
    the valuation currency and its limits."""
    payload = _pac_incumbent_result()
    solution = payload["primary_solution"]
    asset = _find(solution["asset_rows"], "asset_id", "asset-one")
    asset["minimum"] = _money("2")
    asset["maximum"] = _money("5")
    solution["cash_rows"] = [{"broker_id": "broker-one", "currency": "EUR", "final_value": _money("0"), "minimum": None, "maximum": _money("1")}]

    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]
    assert (wire["asset_rows"][0]["minimum"], wire["asset_rows"][0]["maximum"]) == (_money("2"), _money("5"))
    assert [(row["broker_id"], row["currency"]) for row in wire["cash_rows"]] == [("broker-one", "EUR")]

    for mutate in (
        lambda solution: solution["cash_rows"].append(deepcopy(solution["cash_rows"][0])),  # one row per cell
        lambda solution: solution["cash_rows"][0].update({"broker_id": "broker-nowhere"}),  # the Broker must be in the catalogue
        lambda solution: solution["cash_rows"][0].update({"minimum": _money("2"), "maximum": _money("1")}),  # a minimum above its maximum
        lambda solution: solution["cash_rows"][0].pop("final_value"),
    ):
        broken = deepcopy(payload)
        mutate(broken["primary_solution"])
        _reject(PAC_PLAN_OUTPUT_ADAPTER, broken)


def test_pac_asset_row_limits_are_never_absent() -> None:
    payload = _pac_incumbent_result()
    asset = _find(payload["primary_solution"]["asset_rows"], "asset_id", "asset-one")
    assert "minimum" in asset and "maximum" in asset
    del asset["minimum"]
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)


def test_pac_request_excludes_holdings_tax_and_sell_routes() -> None:
    assert "holdings" not in PacPlannerRequest.model_fields
    assert "tax" not in PacPlannerRequest.model_fields
    pac = _pac_request()
    rebalancer = _rebalancer_request()

    for field in ("holdings", "tax", "target_fidelity"):
        impossible = deepcopy(pac)
        impossible[field] = deepcopy(rebalancer[field])
        _reject(PAC_PLAN_INPUT_ADAPTER, impossible)

    impossible = deepcopy(pac)
    impossible["order_routes"].append(_medium_sell_route("route-a-alpha-sell"))
    _reject(PAC_PLAN_INPUT_ADAPTER, impossible)


REBALANCER_FIDELITY_CASES = (
    pytest.param({"kind": "level", "level": "cost_aware"}, id="level-cost-aware"),
    pytest.param({"kind": "level", "level": "balanced"}, id="level-balanced"),
    pytest.param({"kind": "level", "level": "faithful"}, id="level-faithful"),
    pytest.param({"kind": "custom", "lambda": "2.5"}, id="custom"),
    pytest.param({"kind": "target_first"}, id="target-first"),
)


@pytest.mark.parametrize("fidelity", REBALANCER_FIDELITY_CASES)
def test_rebalancer_request_is_one_class_with_strategy_and_fidelity(fidelity: JsonObject) -> None:
    """B3 test 1 (S1, M31): one request class whose strategy and fidelity are fields; a strict roundtrip with
    «Invest only»; the custom ``λ`` travels as ``lambda`` on the wire. A wrong fidelity, a missing one and a field that
    caps the spending are refused by the schema."""
    payload = _rebalancer_request()
    payload["target_fidelity"] = fidelity
    model, emitted = _strict_roundtrip(REBALANCER_PLAN_INPUT_ADAPTER, payload)

    assert type(model) is RebalancerPlannerRequest
    assert model.policy == "invest_only"
    assert json.loads(emitted)["target_fidelity"] == fidelity
    if fidelity["kind"] == "custom":
        assert model.target_fidelity.lambda_ == "2.5"

    for wrong in (
        {"kind": "level", "level": "strict"},
        {"kind": "custom"},
        {"kind": "custom", "lambda": "0"},
        {"kind": "custom", "lambda": "-1"},
        {"kind": "custom", "lambda_": "2"},
        {"kind": "target_first", "lambda": "1"},
        {"kind": "weighted"},
    ):
        _reject(REBALANCER_PLAN_INPUT_ADAPTER, {**payload, "target_fidelity": wrong})
    without = deepcopy(payload)
    without.pop("target_fidelity")
    _reject(REBALANCER_PLAN_INPUT_ADAPTER, without)
    for spending_cap in ("max_spend", "spending_cap", "budget"):
        _assert_extra_forbidden(REBALANCER_PLAN_INPUT_ADAPTER, {**payload, spending_cap: {"amount": "10", "currency": "EUR"}}, spending_cap)


def test_rebalancer_request_has_no_funding_routes() -> None:
    """The normalizer generates the Rebalancer's deposits (specification §15 n. 2): the request has no funding routes."""
    assert "funding_routes" not in RebalancerPlannerRequest.model_fields
    payload = _rebalancer_request()
    _assert_extra_forbidden(REBALANCER_PLAN_INPUT_ADAPTER, {**payload, "funding_routes": []}, "funding_routes")


INVEST_AND_SELL_REJECTION_CASES = (
    pytest.param(lambda payload: {**payload, "policy": "invest_and_sell"}, ("literal_error", "policy"), id="strategy"),
    pytest.param(lambda payload: {**payload, "order_routes": [*payload["order_routes"], _medium_sell_route("route-a-alpha-sell")]}, ("value_error", ()), id="sell-route"),
    pytest.param(
        lambda payload: {**payload, "policy": "invest_and_sell", "order_routes": [*payload["order_routes"], _medium_sell_route("route-b-beta-sell")]},
        ("literal_error", "policy"),
        id="strategy-and-sell-route",
    ),
)


@pytest.mark.parametrize(("mutate", "error"), INVEST_AND_SELL_REJECTION_CASES)
def test_invest_and_sell_is_rejected_by_the_schema_until_c1(mutate: Callable[[JsonObject], JsonObject], error: tuple[str, Any]) -> None:
    """B3 test 19, the adapter's half (S1, D10): «Invest and sell» and any sale route are refused by the schema, so a sale
    never reaches an engine that does not model it yet. C1 widens the strategy field."""
    payload = mutate(_rebalancer_request())
    with pytest.raises(ValidationError) as exc_info:
        REBALANCER_PLAN_INPUT_ADAPTER.validate_json(_wire(payload), strict=True)
    errors = exc_info.value.errors(include_url=False)
    assert [(item["type"], item["loc"][-1] if item["loc"] else ()) for item in errors] == [error]


def test_rebalancer_request_carries_the_final_tax_section() -> None:
    """B3 test 17 (contract §5.4, M6, M19): the ``tax`` section's classes make a strict roundtrip, each on the medium
    fixture's own rows; ``tax_regime`` admits only ``administered`` and ``declarative``; ``sell_context`` and an unknown
    field are refused; a route has no ``required_minimum``. C1 adds the whole request that uses them for a sale."""
    payload = _rebalancer_request()
    tax = payload["tax"]
    assert all(tax[name] for name in ("baskets", "assets", "brokers", "carried_losses", "cost_bases")), "the fixture fills every list"
    model, emitted = _strict_roundtrip(TypeAdapter(RebalancerTaxInput), tax)
    assert json.loads(emitted) == tax
    assert {row.scope.kind for row in model.carried_losses} == {"broker", "declared"}

    for regime in ("administered", "declarative"):
        _strict_roundtrip(TypeAdapter(RebalancerTaxInput), {**tax, "brokers": [{**tax["brokers"][0], "tax_regime": regime}]})
    for regime in ("withheld", "self_reserved", "none"):
        _reject(TypeAdapter(RebalancerTaxInput), {**tax, "brokers": [{**tax["brokers"][0], "tax_regime": regime}]})
    _reject(TypeAdapter(RebalancerTaxInput), {**tax, "carried_losses": [{**tax["carried_losses"][0], "scope": {"kind": "everywhere"}}]})
    _assert_extra_forbidden(TypeAdapter(RebalancerTaxInput), {**tax, "asset_taxes": []}, "asset_taxes")

    _assert_extra_forbidden(REBALANCER_PLAN_INPUT_ADAPTER, {**payload, "sell_context": {}}, "sell_context")
    with_required_minimum = deepcopy(payload)
    with_required_minimum["order_routes"][0]["required_minimum"] = {"kind": "none"}
    _assert_extra_forbidden(REBALANCER_PLAN_INPUT_ADAPTER, with_required_minimum, "required_minimum")


MEDIUM_SELL_ROUTE_CASES = (
    pytest.param("route-a-alpha-sell", "whole_quantity", id="whole-quantity"),
    pytest.param("route-b-beta-sell", "monetary_amount", id="monetary-amount"),
)


@pytest.mark.parametrize(("route_id", "capability_kind"), MEDIUM_SELL_ROUTE_CASES)
def test_medium_fixture_sell_routes_strict_roundtrip_without_gross_amount_requested(
    route_id: str,
    capability_kind: str,
) -> None:
    payload = _rebalancer_request()
    route = _medium_sell_route(route_id)
    broker = _find(payload["brokers"], "broker_id", route["broker_id"])
    capability = _find(broker["capabilities"], "capability_id", route["capability_id"])

    assert route["side"] == "sell"
    assert route["minimum_if_active"]["kind"] == capability_kind
    assert capability["kind"] == capability_kind
    assert "gross_amount_requested" not in route

    adapter = TypeAdapter(PlannerSellOrderRouteInput)
    model, emitted = _strict_roundtrip(adapter, route)
    assert json.loads(emitted) == route
    assert "gross_amount_requested" not in adapter.dump_python(model, mode="json")

    with_obsolete_field = deepcopy(route)
    with_obsolete_field["gross_amount_requested"] = None
    _assert_extra_forbidden(adapter, with_obsolete_field, "gross_amount_requested")


OBSOLETE_GROSS_AMOUNT_ROOT_CASES = (
    pytest.param(PAC_PLAN_INPUT_ADAPTER, _pac_request, "route-asset-one-broker-one-buy", id="pac"),
    pytest.param(
        REBALANCER_PLAN_INPUT_ADAPTER,
        _rebalancer_request,
        "route-b-beta-buy",
        id="rebalancer",
    ),
)


@pytest.mark.parametrize(("adapter", "factory", "route_id"), OBSOLETE_GROSS_AMOUNT_ROOT_CASES)
def test_planner_roots_reject_gross_amount_requested_as_an_extra_field(
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    route_id: str,
) -> None:
    payload = factory()
    route = _find(payload["order_routes"], "route_id", route_id)
    assert "gross_amount_requested" not in route
    route["gross_amount_requested"] = None

    _assert_extra_forbidden(adapter, payload, "gross_amount_requested")


REBALANCER_READY_SELL_POLICY_CASES = (
    pytest.param(_rebalancer_incumbent_result, "primary_solution", id="primary"),
    pytest.param(_distinct_deployment_rebalancer_result, "deployment", id="distinct-deployment"),
)


@pytest.mark.parametrize(("factory", "sell_location"), REBALANCER_READY_SELL_POLICY_CASES)
@pytest.mark.parametrize(("policy", "accepted"), (pytest.param("invest_and_sell", True, id="invest-and-sell"), pytest.param("invest_only", False, id="invest-only")))
def test_rebalancer_ready_sell_orders_are_forbidden_only_for_invest_only(
    factory: PayloadFactory,
    sell_location: str,
    policy: str,
    accepted: bool,
) -> None:
    payload = factory()
    payload["scenario_basis"]["policy"] = policy
    solution = payload["primary_solution"] if sell_location == "primary_solution" else payload["deployment"]["solution"]
    assert any(row["kind"] == "sell" for row in solution["order_rows"])

    if accepted:
        model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
        assert REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["scenario_basis"]["policy"] == "invest_and_sell"
    else:
        _reject(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)


EXACT_NUMBER_ADAPTER = TypeAdapter(ExactNumber)
OBJECTIVE_STAGE_ADAPTER = TypeAdapter(ObjectiveStageResult)
SOLVER_STAGE_ADAPTER = TypeAdapter(SolverStageEvidence)
SOLVER_EVIDENCE_ADAPTER = TypeAdapter(ReportedFloatingSolverEvidence)
SOLVER_STATUS_WITNESS_ADAPTER = TypeAdapter(SolverStatusWitness)
INFEASIBILITY_PROOF_ADAPTER = TypeAdapter(InfeasibilityProvenProof)

VALUATION_OBJECTIVE_CASES = (
    pytest.param("fixed_l2", {"kind": "valuation_money_squared", "currency_code": "EUR"}, id="fixed-l2"),
    pytest.param("plan_score", {"kind": "valuation_money", "currency_code": "EUR"}, id="plan-score"),
    pytest.param("target_distance", {"kind": "valuation_money_squared", "currency_code": "EUR"}, id="target-distance"),
    pytest.param("wealth_loss", {"kind": "valuation_money", "currency_code": "EUR"}, id="wealth-loss"),
    pytest.param("explicit_cost", {"kind": "valuation_money", "currency_code": "EUR"}, id="explicit-cost"),
    pytest.param("incremental_cost", {"kind": "valuation_money", "currency_code": "EUR"}, id="incremental-cost"),
)

DISCRETE_OBJECTIVE_CASES = (
    pytest.param("split_asset_count", {"kind": "count"}, id="split-asset-count"),
    pytest.param("operation_count", {"kind": "count"}, id="operation-count"),
    pytest.param("active_order_rows", {"kind": "count"}, id="active-order-rows"),
    pytest.param("incremental_order_rows", {"kind": "count"}, id="incremental-order-rows"),
    pytest.param("route_priority", {"kind": "ordinal_penalty"}, id="route-priority"),
)


def _objective_stage_payload(objective_code: str, unit: JsonObject, value: JsonObject) -> JsonObject:
    return {
        "objective_code": objective_code,
        "ordinal": 1,
        "sense": "min",
        "unit": deepcopy(unit),
        "value": deepcopy(value),
    }


@pytest.mark.parametrize("objective_code,unit", VALUATION_OBJECTIVE_CASES)
@pytest.mark.parametrize(
    "negative_value",
    (
        pytest.param({"kind": "finite_decimal", "value": "-1"}, id="finite-decimal"),
        pytest.param(
            {
                "kind": "exact_ratio",
                "numerator": "-1",
                "denominator": "2",
                "display_decimal": "-0.5",
                "display_scale": 1,
                "display_authority": "non_authoritative",
            },
            id="exact-ratio",
        ),
    ),
)
def test_non_shortfall_valuation_objectives_reject_negative_exact_values(objective_code: str, unit: JsonObject, negative_value: JsonObject) -> None:
    _reject(OBJECTIVE_STAGE_ADAPTER, _objective_stage_payload(objective_code, unit, negative_value))


@pytest.mark.parametrize("objective_code,unit", VALUATION_OBJECTIVE_CASES)
def test_non_shortfall_valuation_objectives_accept_exact_zero(objective_code: str, unit: JsonObject) -> None:
    payload = _objective_stage_payload(objective_code, unit, _finite("0"))
    model, _emitted = _strict_roundtrip(OBJECTIVE_STAGE_ADAPTER, payload)
    wire = OBJECTIVE_STAGE_ADAPTER.dump_python(model, mode="json")
    assert wire["value"] == _finite("0")
    assert wire["unit"] == unit


def test_shortfall_accepts_negative_exact_value_and_preserves_typed_valuation_currency_unit() -> None:
    unit = {"kind": "valuation_money", "currency_code": "EUR"}
    negative_shortfall = {
        "kind": "exact_ratio",
        "numerator": "-1",
        "denominator": "100",
        "display_decimal": "-0.01",
        "display_scale": 2,
        "display_authority": "non_authoritative",
    }
    model, _emitted = _strict_roundtrip(OBJECTIVE_STAGE_ADAPTER, _objective_stage_payload("shortfall", unit, negative_shortfall))
    wire = OBJECTIVE_STAGE_ADAPTER.dump_python(model, mode="json")

    assert isinstance(model.unit, ValuationMoneyUnit)
    assert model.unit.currency_code == "EUR"
    assert wire["unit"] == unit
    assert wire["value"] == negative_shortfall


@pytest.mark.parametrize("objective_code,unit", DISCRETE_OBJECTIVE_CASES)
@pytest.mark.parametrize(
    ("value", "accepted"),
    (
        pytest.param({"kind": "finite_decimal", "value": "0"}, True, id="zero"),
        pytest.param(
            {
                "kind": "exact_ratio",
                "numerator": "2",
                "denominator": "1",
                "display_decimal": "2",
                "display_scale": 0,
                "display_authority": "non_authoritative",
            },
            True,
            id="positive-integral-ratio",
        ),
        pytest.param({"kind": "finite_decimal", "value": "-1"}, False, id="negative"),
        pytest.param(
            {
                "kind": "exact_ratio",
                "numerator": "1",
                "denominator": "2",
                "display_decimal": "0.5",
                "display_scale": 1,
                "display_authority": "non_authoritative",
            },
            False,
            id="fractional",
        ),
    ),
)
def test_count_and_ordinal_objectives_remain_nonnegative_and_integral(objective_code: str, unit: JsonObject, value: JsonObject, accepted: bool) -> None:
    payload = _objective_stage_payload(objective_code, unit, value)
    if accepted:
        model, _emitted = _strict_roundtrip(OBJECTIVE_STAGE_ADAPTER, payload)
        assert OBJECTIVE_STAGE_ADAPTER.dump_python(model, mode="json")["value"] == value
    else:
        _reject(OBJECTIVE_STAGE_ADAPTER, payload)


@pytest.mark.parametrize(
    "payload",
    (
        {"kind": "finite_decimal", "value": "0.125"},
        {
            "kind": "exact_ratio",
            "numerator": "-3",
            "denominator": "20",
            "display_decimal": "-0.15",
            "display_scale": 2,
            "display_authority": "non_authoritative",
        },
        {
            "kind": "exact_ratio",
            "numerator": "1",
            "denominator": "2",
            "display_decimal": "999",
            "display_scale": 0,
            "display_authority": "non_authoritative",
        },
    ),
)
def test_exact_numbers_strict_roundtrip_and_keep_ratio_display_non_authoritative(payload: JsonObject) -> None:
    model, _emitted = _strict_roundtrip(EXACT_NUMBER_ADAPTER, payload)
    wire = EXACT_NUMBER_ADAPTER.dump_python(model, mode="json")
    if wire["kind"] == "exact_ratio":
        assert wire["display_authority"] == "non_authoritative"


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    (
        ("2", "4"),
        ("-2", "4"),
        ("0", "2"),
        ("1", "0"),
        ("1", "-2"),
        ("01", "2"),
        ("+" + "1", "2"),
        ("1" * 193, "2"),
    ),
)
def test_exact_ratio_rejects_noncanonical_or_unbounded_integer_terms(numerator: str, denominator: str) -> None:
    payload = {
        "kind": "exact_ratio",
        "numerator": numerator,
        "denominator": denominator,
        "display_decimal": "0",
        "display_scale": 0,
        "display_authority": "non_authoritative",
    }
    _reject(EXACT_NUMBER_ADAPTER, payload)


def test_reported_floating_solver_evidence_uses_decimal_strings_not_exact_numbers() -> None:
    stage = _reported_solver_stage(status="finished")
    model, _emitted = _strict_roundtrip(SOLVER_STAGE_ADAPTER, stage)
    wire = SOLVER_STAGE_ADAPTER.dump_python(model, mode="json")
    assert wire["kind"] == "reported_floating"
    assert wire["primal"] == "25"
    assert isinstance(wire["primal"], str)

    exact_primal = deepcopy(stage)
    exact_primal["primal"] = _finite("25")
    _reject(SOLVER_STAGE_ADAPTER, exact_primal)


def test_ready_result_non_optimal_proof_matrix_remains_typed() -> None:
    """A ready result that claims no optimum says so with ``not_proven``: the ready proof union has no third member."""
    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, _pac_no_op_result())
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")
    assert wire["proof"]["kind"] == "not_proven"

    ready_proof_union, _discriminator = get_args(ReadyPlanProof.__value__)
    ready_proof_kinds = {get_args(member.model_fields["kind"].annotation) for member in get_args(ready_proof_union)}
    assert ready_proof_kinds == {("optimal_proven",), ("not_proven",)}


def test_objective_sense_schema_explicitly_preserves_min_and_max() -> None:
    expected = ("min", "max")
    assert get_args(ObjectiveSense) == expected
    assert TypeAdapter(ObjectiveSense).json_schema()["enum"] == list(expected)
    for model_type in (ObjectiveStageResult, SolverStageEvidence):
        assert get_args(model_type.model_fields["sense"].annotation) == expected


OPTIMAL_PROOF_PRODUCT_CASES = (
    pytest.param("PAC", PAC_PLAN_OUTPUT_ADAPTER, _pac_no_op_result, "wealth_loss", id="pac"),
    pytest.param("Rebalancer", REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, "wealth_loss", id="rebalancer"),
)
OPTIMAL_PROOF_MUTATION_CASES = (
    pytest.param("missing", id="missing-interior-code"),
    pytest.param("subset", id="prefix-subset"),
    pytest.param("reordered", id="reordered"),
    pytest.param("duplicate", id="duplicate"),
    pytest.param("extra", id="extra-known-code"),
    pytest.param("unknown", id="unknown-code"),
    pytest.param("tie-closure-missing", id="tie-closure-missing"),
    pytest.param("tie-closure-false", id="tie-closure-false"),
)


@pytest.mark.parametrize(("product", "adapter", "factory", "_extra_code"), OPTIMAL_PROOF_PRODUCT_CASES)
def test_optimal_proven_witness_covers_every_published_objective_stage_in_exact_order(
    product: str,
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    _extra_code: str,
) -> None:
    payload = factory()
    published_codes = _primary_objective_codes(payload)
    assert _finished_evidence_codes(payload) == published_codes, product
    payload["proof"] = _optimal_proven_proof(published_codes, product)

    model, _emitted = _strict_roundtrip(adapter, payload)
    wire = adapter.dump_python(model, mode="json")
    witness = wire["proof"]["witness"]

    assert wire["proof"]["proof_source"] == "solver_status"
    assert witness == {"kind": "solver_status", "objective_codes": published_codes}, product
    assert witness["objective_codes"] == [stage["objective_code"] for stage in wire["solver_evidence"]["stages"]]
    assert wire["proof"].get("tie_break_closed", "absent") == ("absent" if product == "Rebalancer" else True)


def _mutated_witness_codes(mutation: str, published_codes: list[str], extra_code: str) -> list[str]:
    """The witness codes of one objective-closure mutation; the tie-closure mutations keep them as published."""
    mutated = {
        "missing": lambda: [published_codes[0], *published_codes[2:]],
        "subset": lambda: published_codes[:2],
        "reordered": lambda: [published_codes[1], published_codes[0], *published_codes[2:]],
        "duplicate": lambda: [*published_codes, published_codes[-1]],
        "extra": lambda: [*published_codes, extra_code],
        "unknown": lambda: [*published_codes[:-1], "unknown_objective"],
        "tie-closure-missing": lambda: published_codes,
        "tie-closure-false": lambda: published_codes,
    }
    assert mutation in mutated, f"unhandled objective-closure mutation {mutation!r}"
    return mutated[mutation]()


@pytest.mark.parametrize(("product", "adapter", "factory", "extra_code"), OPTIMAL_PROOF_PRODUCT_CASES)
@pytest.mark.parametrize("mutation", OPTIMAL_PROOF_MUTATION_CASES)
def test_optimal_proven_witness_rejects_incomplete_or_false_objective_closure(
    product: str,
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    extra_code: str,
    mutation: str,
) -> None:
    payload = factory()
    published_codes = _primary_objective_codes(payload)
    if mutation == "extra":
        assert extra_code not in published_codes, product
    witness_codes = _mutated_witness_codes(mutation, published_codes, extra_code)

    payload["proof"] = _optimal_proven_proof(witness_codes, product)
    if mutation == "tie-closure-missing" and product == "Rebalancer":
        # The Rebalancer's proof has no such field: carrying it is the error.
        payload["proof"]["tie_break_closed"] = True
    elif mutation == "tie-closure-missing":
        payload["proof"].pop("tie_break_closed")
    elif mutation == "tie-closure-false":
        payload["proof"]["tie_break_closed"] = False
    _reject(adapter, payload)


READY_PRODUCT_CASES = (
    pytest.param("PAC", PAC_PLAN_OUTPUT_ADAPTER, id="pac"),
    pytest.param("Rebalancer", REBALANCER_PLAN_OUTPUT_ADAPTER, id="rebalancer"),
)


def _ready_source_result(product: str) -> JsonObject:
    return _pac_no_op_result() if product == "PAC" else _rebalancer_incumbent_result()


@pytest.mark.parametrize(("product", "adapter"), READY_PRODUCT_CASES)
def test_infeasible_result_requires_a_matching_exact_infeasibility_witness(product: str, adapter: TypeAdapter[Any]) -> None:
    model, _emitted = _strict_roundtrip(adapter, _ready_infeasible_result(product))
    wire = adapter.dump_python(model, mode="json")
    (stage,) = wire["solver_evidence"]["stages"]

    assert wire["proof"] == {
        "kind": "infeasibility_proven",
        "proof_source": "solver_status",
        "witness": {"kind": "solver_status", "objective_codes": [stage["objective_code"]]},
    }
    assert stage["objective_code"] == _primary_objective_codes(_ready_source_result(product))[0]


@pytest.mark.parametrize(("product", "adapter"), READY_PRODUCT_CASES)
def test_ready_infeasible_is_one_infeasible_first_stage_with_a_completed_stop(product: str, adapter: TypeAdapter[Any]) -> None:
    """SCIP's verdict ends the search: one stage, first and global, nothing observed, and ``completed``."""
    payload = _ready_infeasible_result(product)
    model, _emitted = _strict_roundtrip(adapter, payload)
    wire = adapter.dump_python(model, mode="json")

    assert (wire["result_state"], wire["outcome"], wire["stop_reason"]) == ("ready_infeasible", "infeasible_proven", "completed")
    assert "primary_solution" not in wire and "deployment" not in wire
    (stage,) = wire["solver_evidence"]["stages"]
    assert (stage["status"], stage["ordinal"], stage["scope"]) == ("infeasible", 1, "global")
    assert {observation: stage[observation] for observation in SOLVER_OBSERVATIONS} == dict.fromkeys(SOLVER_OBSERVATIONS)

    payload["stop_reason"] = "time_limit"
    _reject(adapter, payload)


def _completed_no_incumbent_result(product: str) -> JsonObject:
    """Yesterday's replay-rejected shape: every stage ``finished``, ``completed``, and no plan."""
    payload = _ready_no_incumbent_result(product)
    payload["stop_reason"] = "completed"
    payload["solver_evidence"] = deepcopy(_ready_source_result(product)["solver_evidence"])
    assert _finished_evidence_codes(payload)
    return payload


@pytest.mark.parametrize(("product", "adapter"), READY_PRODUCT_CASES)
def test_ready_no_incumbent_is_a_limit_stop_or_a_completed_search_with_no_accepted_plan(product: str, adapter: TypeAdapter[Any]) -> None:
    """ "No plan" is a limit stop, or a completed search that holds no plan the replay accepts.

    Since QX1-b the exact replay no longer suppresses a plan of the prudent model: it publishes it with its rounding
    top-ups or raises. Lot ZB of project 67 adds the other way: the prudent model closed infeasible, the outer one (which
    holds every plan the replay could accept) returned only plans the replay refused. The search completed, its stages
    finished, and nothing is proven. A ``completed`` stop still needs no unfinished stage, as for every ready result.
    """
    for stop_reason in ("time_limit", "node_limit"):
        payload = _ready_no_incumbent_result(product)
        payload["stop_reason"] = stop_reason
        model, _emitted = _strict_roundtrip(adapter, payload)
        wire = adapter.dump_python(model, mode="json")
        assert (wire["result_state"], wire["stop_reason"]) == ("ready_no_incumbent", stop_reason)
        assert "primary_solution" not in wire and "deployment" not in wire

    model, _emitted = _strict_roundtrip(adapter, _completed_no_incumbent_result(product))
    wire = adapter.dump_python(model, mode="json")
    assert (wire["result_state"], wire["stop_reason"], wire["proof"]["kind"]) == ("ready_no_incumbent", "completed", "not_proven")

    unfinished = _ready_no_incumbent_result(product)
    unfinished["stop_reason"] = "completed"
    with pytest.raises(ValidationError, match="Completed stops require no unfinished stage"):
        adapter.validate_json(_wire(unfinished), strict=True)


def _optimal_ready_result(product: str) -> JsonObject:
    payload = _ready_source_result(product)
    payload["proof"] = _optimal_proven_proof(_primary_objective_codes(payload), product)
    return payload


def _optimal_over_an_unfinished_stage(product: str) -> JsonObject:
    """The PAC's last stage left open; for the Rebalancer, whose last stages are named tie-breaks that may stay open (D4),
    the score stage itself and everything after it."""
    payload = _optimal_ready_result(product)
    stages = payload["solver_evidence"]["stages"]
    for stage in stages if product == "Rebalancer" else [max(stages, key=lambda stage: stage["ordinal"])]:
        stage["status"] = "unfinished"
    payload["stop_reason"] = "time_limit"
    return payload


def _optimal_over_reordered_evidence(product: str) -> JsonObject:
    payload = _optimal_ready_result(product)
    stages = payload["solver_evidence"]["stages"]
    second, third = _find(stages, "ordinal", 2), _find(stages, "ordinal", 3)
    second["ordinal"], third["ordinal"] = 3, 2
    stages.sort(key=lambda stage: stage["ordinal"])
    return payload


def _optimal_over_evidence_missing_a_stage(product: str) -> JsonObject:
    payload = _optimal_ready_result(product)
    stages = payload["solver_evidence"]["stages"]
    stages.remove(max(stages, key=lambda stage: stage["ordinal"]))
    return payload


def _infeasibility_over_a_finished_stage(product: str) -> JsonObject:
    payload = _ready_infeasible_result(product)
    finished_first = deepcopy(_find(_ready_source_result(product)["solver_evidence"]["stages"], "ordinal", 1))
    assert finished_first["status"] == "finished"
    payload["solver_evidence"] = {"kind": "reported_floating", "stages": [finished_first]}
    return payload


def _infeasibility_naming_another_stage(product: str) -> JsonObject:
    payload = _ready_infeasible_result(product)
    (stage,) = payload["solver_evidence"]["stages"]
    other = next(code for code in _primary_objective_codes(_ready_source_result(product)) if code != stage["objective_code"])
    payload["proof"]["witness"]["objective_codes"] = [other]
    return payload


def _state_over_only_an_infeasible_stage(state: str) -> Callable[[str], JsonObject]:
    def build(product: str) -> JsonObject:
        payload = _result_payload(product, state)
        assert payload["proof"]["kind"] == "not_proven", payload["proof"]
        return _with_only_an_infeasible_first_stage(payload)

    return build


SOLVER_STATUS_BINDING_CASES = (
    pytest.param(_optimal_over_an_unfinished_stage, "optimal_proven requires every solver stage finished", id="optimal-over-unfinished-stage"),
    pytest.param(_optimal_over_reordered_evidence, "Optimal proof witness must name exactly the finished solver stages in order", id="optimal-witness-order-differs-from-evidence"),
    pytest.param(_optimal_over_evidence_missing_a_stage, "Optimal proof witness must name exactly the finished solver stages in order", id="optimal-witness-names-an-unreported-stage"),
    pytest.param(_infeasibility_over_a_finished_stage, "infeasibility_proven requires an infeasible first solver stage", id="infeasibility-without-infeasible-stage"),
    pytest.param(_infeasibility_naming_another_stage, "Infeasibility proof witness must name the infeasible solver stage", id="infeasibility-witness-names-another-stage"),
    # A no-incumbent can no longer sit on an infeasible stage at all: ``completed`` is
    # not its stop literal, and its limit stop needs an unfinished stage, which the
    # lone infeasible stage is not.  So the stop-evidence rule, which runs before the
    # solver-status binding, is what rejects it.
    pytest.param(_state_over_only_an_infeasible_stage("ready_no_incumbent"), "Completed stops require no unfinished stage; limit stops require an unfinished stage", id="no-incumbent-over-infeasible-stage"),
    pytest.param(_state_over_only_an_infeasible_stage("ready_no_op"), "An infeasible solver stage requires an infeasibility proof", id="no-op-over-infeasible-stage"),
    pytest.param(_state_over_only_an_infeasible_stage("ready_incumbent"), "An infeasible solver stage requires an infeasibility proof", id="incumbent-over-infeasible-stage"),
)


@pytest.mark.parametrize(("product", "adapter"), READY_PRODUCT_CASES)
@pytest.mark.parametrize(("build", "message"), SOLVER_STATUS_BINDING_CASES)
def test_solver_status_proof_is_bound_to_the_solver_evidence(
    product: str,
    adapter: TypeAdapter[Any],
    build: Callable[[str], JsonObject],
    message: str,
) -> None:
    """The proof is SCIP's status, so the evidence must show that status - and an infeasible stage backs nothing else."""
    _reject_because(adapter, build(product), message)


def _second_stage_left_open(product: str, *, rejected: bool = False) -> JsonObject:
    """The ready result with its second stage unfinished and the third finished after it. The Rebalancer's second stage is
    its named tie-break ``operation_count``: ``score.tie_breaks`` says why it is open, rejected by the exact comparison
    (D4) or not closed (a limit)."""
    payload = _ready_source_result(product)
    second = _find(payload["solver_evidence"]["stages"], "ordinal", 2)
    second["status"] = "unfinished"
    assert _find(payload["solver_evidence"]["stages"], "ordinal", 3)["status"] == "finished"
    if product == "Rebalancer":
        _find(payload["primary_solution"]["score"]["tie_breaks"], "objective_code", second["objective_code"])["status"] = "rejected" if rejected else "unfinished"
    payload["stop_reason"] = "completed" if rejected else "time_limit"
    return payload


@pytest.mark.parametrize(("product", "adapter"), READY_PRODUCT_CASES)
def test_an_unfinished_stage_before_a_finished_one_is_refused(product: str, adapter: TypeAdapter[Any]) -> None:
    """Finished solver stages precede unfinished ones, for the PAC and the Rebalancer. Since lot CR of project 67 the ready
    result checks it (``results._validate_stage_order``), no longer the evidence alone, so both products are pinned here."""
    _reject_because(adapter, _second_stage_left_open(product), "Finished solver stages must precede unfinished stages")


def test_a_rejected_tie_break_never_follows_a_stage_a_limit_left_open() -> None:
    """The consultant's invariant (D4): D4 rejects only outside the tail, so a rejected tie-break never comes after a stage
    a limit left unfinished. [finished, unfinished by the clock, rejected] is a wire the cascade cannot produce."""
    payload = _second_stage_left_open("Rebalancer")
    third = _find(payload["solver_evidence"]["stages"], "ordinal", 3)
    third["status"] = "unfinished"
    _find(payload["primary_solution"]["score"]["tie_breaks"], "objective_code", third["objective_code"])["status"] = "rejected"
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, payload, "A rejected tie-break cannot follow a stage a limit left unfinished")


def test_a_rejected_tie_break_may_precede_a_finished_stage() -> None:
    """D4 (B2 review of project 67): a tie-break whose plan the exact comparison rejected is reported unfinished and the
    cascade goes on, so a later stage may finish after it. ``score.tie_breaks`` names it rejected, and the wire accepts the
    order (lot CR; G5 seed 8 failed to publish without this)."""
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, _second_stage_left_open("Rebalancer", rejected=True))
    wire = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")
    assert [stage["status"] for stage in wire["solver_evidence"]["stages"]] == ["finished", "unfinished", "finished"]
    assert wire["stop_reason"] == "completed"


def test_infeasible_solver_stage_is_accepted_only_as_the_first_global_stage_without_observations() -> None:
    model, _emitted = _strict_roundtrip(SOLVER_STAGE_ADAPTER, _infeasible_stage_specimen())
    wire = SOLVER_STAGE_ADAPTER.dump_python(model, mode="json")
    assert (wire["status"], wire["ordinal"], wire["scope"]) == ("infeasible", 1, "global")
    assert {observation: wire[observation] for observation in SOLVER_OBSERVATIONS} == dict.fromkeys(SOLVER_OBSERVATIONS)


INFEASIBLE_STAGE_REJECTION_CASES = (
    pytest.param("ordinal", 2, "Only the first, global solver stage can report infeasibility", id="second-ordinal"),
    pytest.param("scope", "incumbent_face", "Only the first, global solver stage can report infeasibility", id="incumbent-face"),
    pytest.param("primal", "25", "An infeasible solver stage has no primal, dual, or gap", id="primal"),
    pytest.param("dual", "24", "An infeasible solver stage has no primal, dual, or gap", id="dual"),
    pytest.param("absolute_gap", "1", "An infeasible solver stage has no primal, dual, or gap", id="absolute-gap"),
    pytest.param("relative_gap", "0.04", "An infeasible solver stage has no primal, dual, or gap", id="relative-gap"),
)


@pytest.mark.parametrize(("field", "value", "message"), INFEASIBLE_STAGE_REJECTION_CASES)
def test_infeasible_solver_stage_rejects_a_later_stage_a_face_or_any_observation(field: str, value: Any, message: str) -> None:
    stage = _infeasible_stage_specimen()
    stage[field] = value
    _reject_because(SOLVER_STAGE_ADAPTER, stage, message)


@pytest.mark.parametrize("other_status", ("finished", "unfinished"))
def test_infeasible_solver_stage_must_be_the_only_reported_stage(other_status: str) -> None:
    source = _pac_no_op_result()
    first_code = _find(source["solver_evidence"]["stages"], "ordinal", 1)["objective_code"]
    alone = {"kind": "reported_floating", "stages": [_infeasible_solver_stage(source, first_code)]}
    _strict_roundtrip(SOLVER_EVIDENCE_ADAPTER, alone)

    later = deepcopy(_find(source["solver_evidence"]["stages"], "ordinal", 2))
    later["status"] = other_status
    followed = {"kind": "reported_floating", "stages": [_infeasible_solver_stage(source, first_code), later]}
    _reject_because(SOLVER_EVIDENCE_ADAPTER, followed, "An infeasible solver stage must be the only reported stage")


@pytest.mark.parametrize(
    ("objective_codes", "message"),
    (
        pytest.param(["fixed_l2", "fixed_l2"], "Solver-status witness objective codes must be unique", id="duplicate-codes"),
        pytest.param([], "at least 1 item", id="empty-codes"),
    ),
)
def test_solver_status_witness_rejects_duplicate_or_empty_codes(objective_codes: list[str], message: str) -> None:
    _strict_roundtrip(SOLVER_STATUS_WITNESS_ADAPTER, {"kind": "solver_status", "objective_codes": ["fixed_l2", "shortfall"]})
    _reject_because(SOLVER_STATUS_WITNESS_ADAPTER, {"kind": "solver_status", "objective_codes": objective_codes}, message)


def _infeasibility_proof_specimen() -> JsonObject:
    return {"kind": "infeasibility_proven", "proof_source": "solver_status", "witness": {"kind": "solver_status", "objective_codes": ["fixed_l2"]}}


def _optimal_proof_specimen() -> JsonObject:
    return _optimal_proven_proof(["fixed_l2", "shortfall"])


def test_infeasibility_proof_names_exactly_one_objective_code() -> None:
    proof = _infeasibility_proof_specimen()
    _strict_roundtrip(INFEASIBILITY_PROOF_ADAPTER, proof)
    proof["witness"]["objective_codes"] = ["fixed_l2", "shortfall"]
    _reject_because(INFEASIBILITY_PROOF_ADAPTER, proof, "An infeasibility proof names exactly the first objective stage")


SOLVER_STATUS_PROOF_CASES = (
    pytest.param(OptimalProvenProof, _optimal_proof_specimen, id="optimal"),
    pytest.param(InfeasibilityProvenProof, _infeasibility_proof_specimen, id="infeasibility"),
)


@pytest.mark.parametrize(("proof_type", "factory"), SOLVER_STATUS_PROOF_CASES)
@pytest.mark.parametrize("field", ("proof_source", "witness_kind"))
@pytest.mark.parametrize("foreign", ("exhaustive_oracle", "deterministic_conflict", "reported_floating"))
def test_solver_status_is_the_only_proof_source_and_witness_kind(
    proof_type: type[BaseModel],
    factory: PayloadFactory,
    field: str,
    foreign: str,
) -> None:
    assert get_args(proof_type.model_fields["proof_source"].annotation) == ("solver_status",)
    assert get_args(SolverStatusWitness.model_fields["kind"].annotation) == ("solver_status",)
    adapter = TypeAdapter(proof_type)
    proof = factory()
    _strict_roundtrip(adapter, proof)

    if field == "proof_source":
        proof["proof_source"] = foreign
    else:
        proof["witness"]["kind"] = foreign
    _reject(adapter, proof)


EXACT_PROOF_MUTATION_CASES = (
    pytest.param("optimal", "reported-floating-proof-source", id="reported-floating-proof-source"),
    pytest.param("optimal", "foreign-witness-kind", id="foreign-optimal-witness-kind"),
    pytest.param("optimal", "oracle-counts-on-witness", id="oracle-counts-on-optimal-witness"),
    pytest.param("infeasibility", "foreign-proof-source", id="foreign-infeasibility-proof-source"),
    pytest.param("infeasibility", "oracle-counts-on-witness", id="oracle-counts-on-infeasibility-witness"),
    pytest.param("infeasibility", "second-code", id="infeasibility-witness-with-two-codes"),
)


@pytest.mark.parametrize(("proof_kind", "mutation"), EXACT_PROOF_MUTATION_CASES)
def test_false_or_incomplete_exact_proof_is_rejected(proof_kind: str, mutation: str) -> None:
    payload = _optimal_ready_result("PAC") if proof_kind == "optimal" else _ready_infeasible_result("PAC")
    _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    proof = payload["proof"]

    if mutation == "reported-floating-proof-source":
        proof["proof_source"] = "reported_floating"
    elif mutation == "foreign-proof-source":
        proof["proof_source"] = "deterministic_conflict"
    elif mutation == "foreign-witness-kind":
        proof["witness"]["kind"] = "exhaustive_oracle"
    elif mutation == "oracle-counts-on-witness":
        proof["witness"].update({"enumerated_candidates": 1, "feasible_candidates": 1 if proof_kind == "optimal" else 0})
        _assert_extra_forbidden(PAC_PLAN_OUTPUT_ADAPTER, payload, "feasible_candidates")
        return
    elif mutation == "second-code":
        proof["witness"]["objective_codes"] = [*proof["witness"]["objective_codes"], "shortfall"]
    else:
        raise AssertionError(f"unhandled exact-proof mutation {mutation!r}")
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)


@pytest.mark.parametrize(
    "mutation",
    (
        "selected-funding-decomposition",
        "fixed-reference",
        "rounding-bound",
        "identity-delta",
        "ledger-posting",
        "asset-residual",
        "shortfall-objective",
    ),
)
def test_exact_accounting_ledger_projection_and_objective_identities_are_enforced(mutation: str) -> None:
    payload = _pac_incumbent_result()
    solution = payload["primary_solution"]

    if mutation == "selected-funding-decomposition":
        solution["accounting"]["selected_funding"] = _money("6")
    elif mutation == "fixed-reference":
        solution["accounting"]["fixed_reference"] = _money("6")
    elif mutation == "rounding-bound":
        solution["accounting"]["rounding_delta"] = _money("0.01")
    elif mutation == "identity-delta":
        solution["accounting"]["identity_delta"] = _money("0.01")
    elif mutation == "ledger-posting":
        _find(solution["ledger_rows"], "broker_id", "broker-one")["final_spendable"] = "1"
    elif mutation == "asset-residual":
        _find(solution["asset_rows"], "asset_id", "asset-one")["residual"] = _money("1")
    else:
        _find(solution["objectives"]["stages"], "objective_code", "shortfall")["value"] = _finite("1")
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)


def _top_up_row(amount: str, *, rounded_postings: int = 1, valuation: JsonObject | None = None) -> JsonObject:
    """One broker-one/EUR rounding top-up, valued at its own amount unless told otherwise."""
    return {
        "broker_id": "broker-one",
        "currency": "EUR",
        "amount": amount,
        "rounded_postings": rounded_postings,
        "valuation_amount": _money(amount) if valuation is None else valuation,
    }


def _pac_top_up_result(deficit: str = "0.01", *, rounded_postings: int = 1) -> JsonObject:
    """The €5 PAC incumbent bought with ``deficit`` less cash, published with the top-up that covers it.

    This is the shape the exact replay publishes when a candidate, rounded
    against the plan, leaves a pool a few minor units short (QX1-b, the top-up
    safety net): the plan stands, the pool goes negative, and the top-up tells
    the user what to add.  Every field that
    reports the selected cash moves with it - the scenario basis and the
    accounting (selected, reachable, fixed reference ``5 - deficit``; shortfall
    and free cash ``-deficit``), the Asset's fixed-reference target and
    residual, the ledger row (initial ``5 - deficit``, final balances
    ``-deficit``) and the shortfall and fixed-L2 objectives - so the negative
    pool is the only unusual thing in the payload, and the top-up the only
    thing that excuses it.  The payload is derived from the JSON fixture
    (through ``_pac_incumbent_result``), whose ``rounding_top_ups`` is ``[]``
    because every pool there balances; the helper sets the top-up rows
    itself, one row covering ``deficit`` over ``rounded_postings``.
    """
    gap = Decimal(deficit)
    cash = str(Decimal("5") - gap)
    payload = _pac_incumbent_result()
    for field in ("selected_funding", "reachable_funding", "fixed_reference"):
        payload["scenario_basis"][field] = _money(cash)

    solution = payload["primary_solution"]
    accounting = solution["accounting"]
    for field in ("current_invested", "selected_funding", "reachable_funding", "trapped_funding", "fixed_reference"):
        accounting[field] = deepcopy(payload["scenario_basis"][field])
    accounting["final_invested"] = _money("5")
    accounting["shortfall"] = _money(str(-gap))
    accounting["free_cash"] = _money(str(-gap))
    accounting["rounding_delta"] = _money("0")

    asset = _find(solution["asset_rows"], "asset_id", "asset-one")
    asset["target_value"] = _money(cash)
    asset["residual"] = _money(deficit)

    ledger = _find(solution["ledger_rows"], "broker_id", "broker-one")
    ledger["initial_selected"] = cash
    ledger["final_spendable"] = str(-gap)
    ledger["final_physical"] = str(-gap)

    _find(solution["objectives"]["stages"], "objective_code", "shortfall")["value"] = _finite(str(-gap))
    _find(solution["objectives"]["stages"], "objective_code", "fixed_l2")["value"] = _finite(str(gap * gap))
    solution["rounding_top_ups"] = [_top_up_row(deficit, rounded_postings=rounded_postings)]
    _restate_pac_plan_accounts(solution)
    return payload


@pytest.mark.parametrize(
    ("deficit", "rounded_postings"),
    (
        pytest.param("0.01", 1, id="one-cent-over-one-posting"),
        pytest.param("0.02", 2, id="two-cents-over-two-postings"),
    ),
)
def test_pac_rounding_top_up_publishes_the_negative_pool_it_covers(deficit: str, rounded_postings: int) -> None:
    """A negative pool is publishable when a top-up names it, to the cent, within its rounded postings.

    The ledger row keeps its negative balances instead of the schema refusing
    them, and the top-up travels unchanged: the wire is a projection of what
    the classifier decided.  The two-cent case is what the one-cent case
    cannot tell apart from a flat one-minor-unit cap: the threshold is
    ``rounded_postings`` minor units (an order can round twice, debit and
    fee).
    """
    payload = _pac_top_up_result(deficit, rounded_postings=rounded_postings)
    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")

    assert type(model) is PacPlannerReadyIncumbentResult
    solution = wire["primary_solution"]
    (top_up,) = solution["rounding_top_ups"]
    assert (top_up["broker_id"], top_up["currency"], top_up["rounded_postings"]) == ("broker-one", "EUR", rounded_postings)
    assert Fraction(top_up["amount"]) == Fraction(deficit)
    assert top_up["valuation_amount"]["currency"] == wire["scenario_basis"]["valuation_currency"]
    assert _money_wire_fraction(top_up["valuation_amount"]) == Fraction(deficit)
    ledger = _find(solution["ledger_rows"], "broker_id", "broker-one")
    assert Fraction(ledger["final_spendable"]) == Fraction(ledger["final_physical"]) == -Fraction(deficit)
    assert _money_wire_fraction(solution["accounting"]["free_cash"]) == -Fraction(deficit)


def _negative_pool_without_top_up() -> JsonObject:
    """The nonnegative incumbent with only its ledger pool one cent short, and no top-up for it.

    Nothing else reports the deficit - the accounting stays nonnegative - so
    the cover rule is the only one this payload breaks.
    """
    payload = _pac_incumbent_result()
    ledger = _find(payload["primary_solution"]["ledger_rows"], "broker_id", "broker-one")
    ledger.update({"initial_selected": "4.99", "final_spendable": "-0.01", "final_physical": "-0.01"})
    payload["primary_solution"]["rounding_top_ups"] = []
    return payload


def _top_up_without_negative_pool() -> JsonObject:
    payload = _pac_incumbent_result()
    payload["primary_solution"]["rounding_top_ups"] = [_top_up_row("0.01")]
    return payload


def _top_up_larger_than_its_deficit() -> JsonObject:
    # Valued at its own amount and within 2 x 0.01, so only the cover rule breaks.
    payload = _pac_top_up_result()
    payload["primary_solution"]["rounding_top_ups"] = [_top_up_row("0.02", rounded_postings=2)]
    return payload


def _duplicate_top_up_scope() -> JsonObject:
    payload = _pac_top_up_result()
    payload["primary_solution"]["rounding_top_ups"] = [_top_up_row("0.01"), _top_up_row("0.01")]
    return payload


def _more_rounded_postings_than_the_scope_carries() -> JsonObject:
    # broker-one/EUR carries one order row (BUY debit and fee: 2) and no FX credit.
    payload = _pac_top_up_result()
    payload["primary_solution"]["rounding_top_ups"] = [_top_up_row("0.01", rounded_postings=3)]
    return payload


def _deficit_beyond_its_rounded_postings() -> JsonObject:
    # A coherent two-cent pool, but one rounded posting only excuses one cent.
    return _pac_top_up_result("0.02", rounded_postings=1)


def _zero_valued_top_up() -> JsonObject:
    # The cent is booked as rounding (inside a one-cent bound), so neither the free-cash
    # nor the shortfall rule needs the valuation: only the valuation's own rules remain.
    payload = _pac_top_up_result()
    payload["primary_solution"]["rounding_top_ups"] = [_top_up_row("0.01", valuation=_money("0"))]
    accounting = payload["primary_solution"]["accounting"]
    accounting["free_cash"] = _money("0")
    accounting["rounding_delta"] = _money("-0.01")
    accounting["rounding_bound"] = _money("0.01")
    return payload


def _top_up_valued_off_its_own_amount() -> JsonObject:
    payload = _pac_top_up_result()
    payload["primary_solution"]["rounding_top_ups"] = [_top_up_row("0.01", valuation=_money("0.02"))]
    return payload


def _free_cash_negative_beyond_the_top_ups() -> JsonObject:
    # Two cents of negative free cash, one reported as economic loss so the decomposition
    # and the shortfall (-0.01 + 0.01 >= 0) still hold: one cent is left uncovered.
    payload = _pac_top_up_result()
    accounting = payload["primary_solution"]["accounting"]
    accounting["free_cash"] = _money("-0.02")
    accounting["economic_losses"] = _money("0.01")
    return payload


def _shortfall_beyond_the_top_ups() -> JsonObject:
    # The shortfall and everything that reports it (fixed reference, target, residual,
    # objective) move to -0.02 while free cash, the pool and its top-up stay at one cent.
    # No coherent payload breaks this rule alone - free cash + top-ups >= 0, the
    # decomposition and |rounding| <= bound together imply it - so the decomposition,
    # checked after it as today, is the one other rule broken here.
    payload = _pac_top_up_result()
    for field in ("selected_funding", "reachable_funding", "fixed_reference"):
        payload["scenario_basis"][field] = _money("4.98")
    solution = payload["primary_solution"]
    for field in ("selected_funding", "reachable_funding", "fixed_reference"):
        solution["accounting"][field] = deepcopy(payload["scenario_basis"][field])
    solution["accounting"]["shortfall"] = _money("-0.02")
    asset = _find(solution["asset_rows"], "asset_id", "asset-one")
    asset["target_value"] = _money("4.98")
    asset["residual"] = _money("0.02")
    _find(solution["objectives"]["stages"], "objective_code", "shortfall")["value"] = _finite("-0.02")
    _find(solution["objectives"]["stages"], "objective_code", "fixed_l2")["value"] = _finite("0.0004")
    return payload


def _top_up_valued_in_another_currency() -> JsonObject:
    # USD joins the catalogue so the catalogue rules pass and the valuation-currency rule speaks.
    payload = _pac_top_up_result()
    payload["catalogs"]["currencies"].append({"currency": "USD", "minor_unit": "0.01"})
    payload["scenario_basis"]["counts"]["currencies"] = len(payload["catalogs"]["currencies"])
    payload["primary_solution"]["rounding_top_ups"] = [_top_up_row("0.01", valuation=_money("0.01", "USD"))]
    return payload


PAC_ROUNDING_TOP_UP_REJECTION_CASES = (
    pytest.param(_top_up_larger_than_its_deficit, "PAC rounding top-ups must cover exactly the negative ledger balances", id="amount-differs-from-the-deficit"),
    pytest.param(_negative_pool_without_top_up, "PAC rounding top-ups must cover exactly the negative ledger balances", id="negative-pool-without-top-up"),
    pytest.param(_top_up_without_negative_pool, "PAC rounding top-ups must cover exactly the negative ledger balances", id="top-up-without-negative-pool"),
    pytest.param(_duplicate_top_up_scope, "PAC rounding top-up scopes must be unique", id="duplicate-scope"),
    pytest.param(_more_rounded_postings_than_the_scope_carries, "A PAC rounding top-up cannot count more rounded postings than its ledger scope carries", id="more-postings-than-the-scope"),
    pytest.param(_deficit_beyond_its_rounded_postings, "A rounding top-up cannot exceed its rounded postings times the currency minor unit", id="beyond-postings-times-minor-unit"),
    pytest.param(_zero_valued_top_up, "PAC rounding top-up valuations must be positive", id="zero-valuation"),
    pytest.param(_top_up_valued_off_its_own_amount, "A rounding top-up in the valuation currency must be valued at its own amount", id="valued-off-its-own-amount"),
    pytest.param(_free_cash_negative_beyond_the_top_ups, "Free cash cannot be negative beyond the rounding top-ups", id="free-cash-beyond-top-ups"),
    pytest.param(_shortfall_beyond_the_top_ups, "Shortfall cannot exceed the favorable rounding bound", id="shortfall-beyond-top-ups"),
    pytest.param(_top_up_valued_in_another_currency, "Asset, accounting, and cost projections must use the valuation currency", id="valued-in-another-currency"),
)


@pytest.mark.parametrize(("build", "message"), PAC_ROUNDING_TOP_UP_REJECTION_CASES)
def test_pac_rounding_top_up_rejects_a_top_up_the_ledger_does_not_justify(build: PayloadFactory, message: str) -> None:
    """A top-up excuses exactly its own pool's rounding deficit, and nothing else.

    Each payload breaks one rule (or, where no coherent payload can, the one
    the comment names) and the test pins that rule's message, since a bare
    rejection would also pass for whatever else breaks first.  The contract:
    every PAC solution requires ``rounding_top_ups`` - empty when every pool
    balances, pinned empty by ``PacNoOpSolution`` - while Rebalancer
    solutions forbid it as an extra field.
    """
    _reject_because(PAC_PLAN_OUTPUT_ADAPTER, build(), message)


def test_pac_no_op_publishes_no_rounding_top_up() -> None:
    """A no-op posts nothing, so nothing rounds: its top-up list exists and is empty by type."""
    payload = _pac_no_op_result()
    payload["primary_solution"]["rounding_top_ups"] = []
    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    assert PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]["rounding_top_ups"] == []

    payload["primary_solution"]["rounding_top_ups"] = [_top_up_row("0.01")]
    with pytest.raises(ValidationError) as exc_info:
        PAC_PLAN_OUTPUT_ADAPTER.validate_json(_wire(payload), strict=True)
    errors = exc_info.value.errors(include_url=False)
    assert any(error["type"] == "too_long" and error["loc"][-1] == "rounding_top_ups" for error in errors), errors


def _exposure_after_with_top_ups(solution: JsonObject) -> None:
    """Lot ZB-b of project 67: the exposure after is on ``W`` plus the rounding top-ups, the cash after counting them as
    added. As the report publishes it: a category keeps its value on the new base, the cash row is that base less the final
    invested value."""
    final = _money_wire_fraction(solution["plan_accounts"]["final_wealth"])
    base = final + sum((_money_wire_fraction(row["valuation_amount"]) for row in solution["rounding_top_ups"]), Fraction())
    invested = _money_wire_fraction(solution["accounting"]["final_invested"])
    for row in solution["exposure_rows"]:
        if row["final_weight"]["kind"] != "available":
            continue
        after = (base - invested) / base if row["kind"] == "cash" else _exact_wire_fraction(row["final_weight"]["value"]) * final / base
        row["final_weight"] = {"kind": "available", "value": _wire_number(after)}


def test_rebalancer_ledger_publishes_its_rounding_top_up() -> None:
    """B3 test 3 (contract §6.5, specifica §15 n. 15): a Rebalancer pool a minor unit short to rounding against the plan is
    published with the top-up that covers it, as in the PAC; without one, the negative pool is refused. The short row is
    internally reconciled (a one-cent larger BUY debit), so only the missing top-up is wrong."""
    payload = _rebalancer_incumbent_result()
    ledger = next(row for row in payload["primary_solution"]["ledger_rows"] if (row["broker_id"], row["currency"]) == ("broker-beta", "EUR"))
    assert (Fraction(ledger["buy_debit"]), Fraction(ledger["final_spendable"]), Fraction(ledger["final_physical"])) == (30, 0, 0)
    ledger.update({"buy_debit": "30.01", "final_spendable": "-0.01", "final_physical": "-0.01"})
    _restate_rebalancer_cash(payload["primary_solution"], unused={})
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, payload, "Rebalancer rounding top-ups must cover exactly the negative ledger balances")

    payload["primary_solution"]["rounding_top_ups"] = [{"broker_id": "broker-beta", "currency": "EUR", "amount": "0.01", "rounded_postings": 1, "valuation_amount": _money("0.01")}]
    # Lot ZB-b: the exposure after counts the top-up as added; left on W alone, it is refused.
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, payload, "asset_type exposure cash must be the cash of the accounts, before on F and after on W with the rounding top-ups")
    _exposure_after_with_top_ups(payload["primary_solution"])
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
    assert [row["amount"] for row in REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]["rounding_top_ups"]] == ["0.01"]

    payload["primary_solution"]["rounding_top_ups"][0]["rounded_postings"] = 3
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, payload, "A Rebalancer rounding top-up cannot count more rounded postings than its ledger scope carries")


# FX conversion fix - a ledger row's rounding residual is an exact number.  USD->EUR at the
# reciprocal of a stored EUR/USD leaves a residual that repeats (-47/21700), which no
# fixed-decimal text can carry, so ``rounding_delta`` is an ``ExactNumber`` like every other
# exact value of the contract: ``finite_decimal`` when it terminates, ``exact_ratio`` when it
# does not.  Every test below sets the field on every ledger row explicitly, so none of them
# depends on what the builders and fixtures happen to publish.

LEDGER_ROUNDING_RATIO = _ratio("-47", "21700", "-0.002166")
NO_OP_LEDGER_ROUNDING_CASES = (
    pytest.param(PAC_PLAN_OUTPUT_ADAPTER, _pac_no_op_result, ("broker-one", "EUR"), id="pac"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_no_op_result, ("broker-alpha", "EUR"), id="rebalancer"),
)


def _with_ledger_rounding(payload: JsonObject, value: Any, *, only: tuple[str, str] | None = None) -> JsonObject:
    """Set ``rounding_delta`` on every ledger row: ``value`` on the ``only`` row (on all of them when ``None``), an exact zero elsewhere."""
    rows = payload["primary_solution"]["ledger_rows"]
    assert only is None or only in [(row["broker_id"], row["currency"]) for row in rows], only
    for row in rows:
        row["rounding_delta"] = deepcopy(value) if only in (None, (row["broker_id"], row["currency"])) else _finite("0")
    return payload


def _ledger_rounding_by_row(rows: list[JsonObject]) -> dict[tuple[str, str], Any]:
    return {(row["broker_id"], row["currency"]): row["rounding_delta"] for row in rows}


@pytest.mark.parametrize(
    "rounding",
    (
        pytest.param(_finite("0"), id="finite-zero"),
        pytest.param(LEDGER_ROUNDING_RATIO, id="repeating-ratio"),
    ),
)
def test_ledger_rounding_delta_is_an_exact_number(rounding: JsonObject) -> None:
    """Both branches of the exact number are accepted, and published back exactly as given."""
    payload = _with_ledger_rounding(_pac_incumbent_result(), rounding, only=("broker-one", "EUR"))
    expected = _ledger_rounding_by_row(payload["primary_solution"]["ledger_rows"])

    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)

    published = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]["ledger_rows"]
    assert _ledger_rounding_by_row(published) == expected


def test_ledger_rounding_delta_rejects_bare_decimal_text() -> None:
    """The field has one type: a reader dispatches on ``kind`` and never has to guess whether it received text."""
    payload = _with_ledger_rounding(_pac_incumbent_result(), "0")

    with pytest.raises(ValidationError) as exc_info:
        PAC_PLAN_OUTPUT_ADAPTER.validate_json(_wire(payload), strict=True)

    errors = exc_info.value.errors(include_url=False)
    assert any("rounding_delta" in error["loc"] for error in errors), errors


@pytest.mark.parametrize(("adapter", "build", "residual_row"), NO_OP_LEDGER_ROUNDING_CASES)
def test_no_op_ledger_accepts_an_exact_zero_rounding_delta(adapter: TypeAdapter[Any], build: PayloadFactory, residual_row: tuple[str, str]) -> None:
    """A no-op posts nothing, so every residual is an exact zero, the row the next test breaks included."""
    payload = _with_ledger_rounding(build(), _finite("0"), only=residual_row)
    rows = payload["primary_solution"]["ledger_rows"]
    assert all(row["rounding_delta"] == _finite("0") for row in rows), rows

    model, _emitted = _strict_roundtrip(adapter, payload)

    published = adapter.dump_python(model, mode="json")["primary_solution"]["ledger_rows"]
    assert _ledger_rounding_by_row(published) == _ledger_rounding_by_row(rows)


@pytest.mark.parametrize(("adapter", "build", "residual_row"), NO_OP_LEDGER_ROUNDING_CASES)
def test_no_op_ledger_refuses_a_nonzero_rounding_residual(adapter: TypeAdapter[Any], build: PayloadFactory, residual_row: tuple[str, str]) -> None:
    """A nonzero residual is action-derived whatever its expansion: a ratio is refused by the no-op rule, not by its type."""
    payload = _with_ledger_rounding(build(), LEDGER_ROUNDING_RATIO, only=residual_row)

    _reject_because(adapter, payload, "No-op ledger rows cannot contain action-derived postings")


# R4.9 - conversions.  An FX action is an engine decision keyed by order route; what
# the user executes is its Broker x currency-pair conversion, numbered only when the
# Broker converts manually.  The medium Rebalancer fixture carries one of each: the
# beta EUR->USD action and its manual conversion, step 3 between funding (1-2) and
# orders (4-7).  Every rejection below starts from that coherent pair and breaks one
# rule, so the pinned message is the rule under test, not whatever broke first.

BETA_FX_ACTION_ID = "fx-action-beta-eur-usd"
BETA_CONVERSION_ID = "conversion-beta-eur-usd"
REQUEST_BROKER_CONVERSION_MODE_CASES = (
    pytest.param(PAC_PLAN_INPUT_ADAPTER, _pac_request, "broker-one", id="pac"),
    pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, _rebalancer_request, "broker-beta", id="rebalancer"),
)


@pytest.mark.parametrize(("adapter", "factory", "broker_id"), REQUEST_BROKER_CONVERSION_MODE_CASES)
@pytest.mark.parametrize("mode", ("manual", "automatic"))
def test_request_broker_conversion_mode_accepts_manual_and_automatic(
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    broker_id: str,
    mode: str,
) -> None:
    payload = factory()
    _find(payload["brokers"], "broker_id", broker_id)["conversion_mode"] = mode
    model, _emitted = _strict_roundtrip(adapter, payload)
    wire = adapter.dump_python(model, mode="json")
    assert _find(wire["brokers"], "broker_id", broker_id)["conversion_mode"] == mode


_MISSING = object()


@pytest.mark.parametrize(("adapter", "factory", "broker_id"), REQUEST_BROKER_CONVERSION_MODE_CASES)
@pytest.mark.parametrize(
    ("value", "error_type"),
    (
        pytest.param(_MISSING, "missing", id="missing"),
        pytest.param(None, "literal_error", id="null"),
        pytest.param("Manual", "literal_error", id="capitalised"),
        pytest.param("auto", "literal_error", id="unknown"),
    ),
)
def test_request_broker_conversion_mode_is_required_and_closed(
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    broker_id: str,
    value: Any,
    error_type: str,
) -> None:
    """The mode is a Broker input with no default: the planner never guesses how a Broker converts."""
    payload = factory()
    broker = _find(payload["brokers"], "broker_id", broker_id)
    if value is _MISSING:
        broker.pop("conversion_mode")
    else:
        broker["conversion_mode"] = value
    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_json(_wire(payload), strict=True)
    errors = exc_info.value.errors(include_url=False)
    assert any(error["type"] == error_type and error["loc"][-1] == "conversion_mode" for error in errors), errors


def _beta_conversion(solution: JsonObject) -> JsonObject:
    return _find(solution["conversions"], "conversion_id", BETA_CONVERSION_ID)


def _fx_rate(source_currency: str, destination_currency: str, value: JsonObject) -> JsonObject:
    return {"source_currency": source_currency, "destination_currency": destination_currency, "value": value}


def _with_beta_conversion(**fields: Any) -> PayloadFactory:
    """The medium fixture with fields of the beta conversion replaced."""

    def build() -> JsonObject:
        payload = _rebalancer_incumbent_result()
        _beta_conversion(payload["primary_solution"]).update(deepcopy(fields))
        return payload

    return build


def _with_beta_conversion_renamed(conversion_id: str) -> PayloadFactory:
    def build() -> JsonObject:
        payload = _rebalancer_incumbent_result()
        _beta_conversion(payload["primary_solution"])["conversion_id"] = conversion_id
        return payload

    return build


def _add_conversion(solution: JsonObject, *, broker_id: str, source: str, destination: str, rate: str, mode: str, sequence: int | None) -> JsonObject:
    """Publish one more conversion, coherent on its own (no spread), so a case can break one rule on top of it.

    The catalogue of the medium fixture holds EUR and USD, at brokers alpha and beta.
    """
    spot = _fx_rate(source, destination, _finite(rate))
    conversion = {
        "conversion_id": f"conversion-{broker_id.removeprefix('broker-')}-{source.lower()}-{destination.lower()}",
        "mode": mode,
        "sequence": sequence,
        "broker_id": broker_id,
        "source_debit": {"amount": "10", "currency": source},
        "destination_credit": {"amount": "10", "currency": destination},
        "spot_rate": deepcopy(spot),
        "effective_rate": deepcopy(spot),
        "spread_loss": _money("0"),
        "provenance_ids": ["prov-manual"],
    }
    solution["conversions"].append(conversion)
    return conversion


def _conversion_over_one_pair_at_another_broker() -> JsonObject:
    payload = _rebalancer_incumbent_result()
    _add_conversion(payload["primary_solution"], broker_id="broker-alpha", source="EUR", destination="USD", rate="1.25", mode="manual", sequence=8)
    return payload


def _conversion_rates_in_another_exact_form() -> JsonObject:
    # 5/4 and 12.5 are 1.25 and 12.50: the rule compares numbers, not text.
    payload = _rebalancer_incumbent_result()
    conversion = _beta_conversion(payload["primary_solution"])
    for field in ("spot_rate", "effective_rate"):
        conversion[field]["value"] = _ratio("5", "4", "1.25")
    conversion["destination_credit"]["amount"] = "12.5"
    return payload


def _automatic_conversions_take_no_step() -> JsonObject:
    # Two automatic conversions both publish a null sequence - which must not collide -
    # and the orders follow the funding directly, as the planner numbers them.
    payload = _rebalancer_incumbent_result()
    solution = payload["primary_solution"]
    _beta_conversion(solution).update(mode="automatic", sequence=None)
    _add_conversion(solution, broker_id="broker-alpha", source="EUR", destination="USD", rate="1.25", mode="automatic", sequence=None)
    for sequence, order in enumerate(sorted(solution["order_rows"], key=lambda row: row["sequence"]), start=3):
        order["sequence"] = sequence
    return payload


CONVERSION_ACCEPTED_CASES = (
    pytest.param(_rebalancer_incumbent_result, id="fixture-manual-conversion"),
    pytest.param(_conversion_over_one_pair_at_another_broker, id="same-pair-at-another-broker"),
    pytest.param(_conversion_rates_in_another_exact_form, id="exact-not-lexical-rates"),
    pytest.param(_automatic_conversions_take_no_step, id="automatic-conversions-take-no-step"),
)


@pytest.mark.parametrize("build", CONVERSION_ACCEPTED_CASES)
def test_conversion_shapes_the_contract_accepts(build: PayloadFactory) -> None:
    payload = build()
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
    assert type(model) is RebalancerPlannerReadyIncumbentResult
    solution = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]
    assert solution["conversions"] == payload["primary_solution"]["conversions"]
    assert "fx_actions" not in solution


def test_medium_fixture_numbers_its_steps_in_one_executable_order() -> None:
    """Deposit, transfer, manual conversion, then the orders: one counter across the step lists (contract §6.3)."""
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result())
    solution = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]

    conversion = _beta_conversion(solution)
    assert (conversion["mode"], conversion["broker_id"]) == ("manual", "broker-beta")
    assert [row["sequence"] for row in solution["funding_actions"]] == [1]
    assert [row["sequence"] for row in solution["transfers"]] == [2]
    assert [row["sequence"] for row in solution["conversions"]] == [3]
    assert [row["sequence"] for row in solution["order_rows"]] == [4, 5, 6, 7]


def test_conversion_lists_at_least_one_provenance() -> None:
    payload = _rebalancer_incumbent_result()
    _beta_conversion(payload["primary_solution"])["provenance_ids"] = []
    with pytest.raises(ValidationError) as exc_info:
        REBALANCER_PLAN_OUTPUT_ADAPTER.validate_json(_wire(payload), strict=True)
    errors = exc_info.value.errors(include_url=False)
    assert any(error["type"] == "too_short" and error["loc"][-1] == "provenance_ids" for error in errors), errors


CONVERSION_ROW_REJECTION_CASES = (
    pytest.param(_with_beta_conversion(sequence=None), "A conversion has an execution sequence exactly when it is manual", id="manual-without-sequence"),
    pytest.param(_with_beta_conversion(mode="automatic"), "A conversion has an execution sequence exactly when it is manual", id="automatic-with-sequence"),
    pytest.param(_with_beta_conversion(spot_rate=_fx_rate("USD", "EUR", _finite("0.8"))), "Conversion rates must follow the source-to-destination direction", id="spot-rate-reversed"),
    pytest.param(_with_beta_conversion(effective_rate=_fx_rate("USD", "EUR", _finite("0.8"))), "Conversion rates must follow the source-to-destination direction", id="effective-rate-reversed"),
    pytest.param(_with_beta_conversion(effective_rate=_fx_rate("EUR", "USD", _finite("1.26"))), "Effective conversion rate cannot exceed the approved spot rate", id="effective-above-spot"),
    pytest.param(_with_beta_conversion(spread_loss=_money("-0.01")), "Conversion spread loss cannot be negative", id="negative-spread"),
)


@pytest.mark.parametrize(("build", "message"), CONVERSION_ROW_REJECTION_CASES)
def test_conversion_row_rejects_an_inconsistent_conversion(build: PayloadFactory, message: str) -> None:
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, build(), message)


def _second_conversion_with_the_beta_id() -> JsonObject:
    payload = _rebalancer_incumbent_result()
    solution = payload["primary_solution"]
    conversion = _add_conversion(solution, broker_id="broker-alpha", source="EUR", destination="USD", rate="1.25", mode="manual", sequence=8)
    conversion["conversion_id"] = BETA_CONVERSION_ID
    return payload


def _manual_conversions_out_of_order() -> JsonObject:
    # Step 8 is free (orders end at 7): only the order inside the conversion section is wrong.
    payload = _rebalancer_incumbent_result()
    solution = payload["primary_solution"]
    _add_conversion(solution, broker_id="broker-alpha", source="EUR", destination="USD", rate="1.25", mode="manual", sequence=8)
    solution["conversions"].reverse()
    return payload


ACTION_ID_AND_SEQUENCE_REJECTION_CASES = (
    pytest.param(_with_beta_conversion_renamed("order-buy-b-beta"), "Rebalancer action IDs must be unique", id="conversion-id-is-an-order-id"),
    pytest.param(_with_beta_conversion_renamed("funding-action-alpha"), "Rebalancer action IDs must be unique", id="conversion-id-is-a-funding-id"),
    pytest.param(_with_beta_conversion_renamed("transfer-alpha-beta-eur"), "Rebalancer action IDs must be unique", id="conversion-id-is-a-transfer-id"),
    pytest.param(_second_conversion_with_the_beta_id, "Rebalancer action IDs must be unique", id="duplicate-conversion-id"),
    pytest.param(_with_beta_conversion(sequence=1), "Rebalancer action sequences must be unique", id="manual-conversion-on-a-funding-step"),
    pytest.param(_with_beta_conversion(sequence=2), "Rebalancer action sequences must be unique", id="manual-conversion-on-a-transfer-step"),
    pytest.param(_with_beta_conversion(sequence=4), "Rebalancer action sequences must be unique", id="manual-conversion-on-an-order-step"),
    pytest.param(_manual_conversions_out_of_order, "Rebalancer action sections must be sequence-ordered", id="conversion-section-out-of-order"),
)


@pytest.mark.parametrize(("build", "message"), ACTION_ID_AND_SEQUENCE_REJECTION_CASES)
def test_conversions_share_the_action_id_space_and_manual_ones_the_step_numbering(build: PayloadFactory, message: str) -> None:
    """Conversion IDs collide with every action ID; only a manual conversion holds an execution step.

    The positive half - automatic conversions publish no step, even two of them -
    is ``automatic-conversions-take-no-step`` in ``CONVERSION_ACCEPTED_CASES``.
    """
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, build(), message)


def _second_conversion_for_the_beta_pair() -> JsonObject:
    payload = _rebalancer_incumbent_result()
    conversion = _add_conversion(payload["primary_solution"], broker_id="broker-beta", source="EUR", destination="USD", rate="1.25", mode="manual", sequence=8)
    conversion["conversion_id"] = "conversion-beta-eur-usd-twice"
    return payload


def _broker_with_manual_and_automatic_conversions() -> JsonObject:
    payload = _rebalancer_incumbent_result()
    _add_conversion(payload["primary_solution"], broker_id="broker-beta", source="USD", destination="EUR", rate="0.8", mode="automatic", sequence=None)
    return payload


CONVERSION_BINDING_REJECTION_CASES = (
    pytest.param(_second_conversion_for_the_beta_pair, "Rebalancer conversion pairs must be unique", id="two-conversions-for-one-pair"),
    pytest.param(_broker_with_manual_and_automatic_conversions, "Rebalancer conversions must use one mode per Broker", id="two-modes-for-one-broker"),
)


@pytest.mark.parametrize(("build", "message"), CONVERSION_BINDING_REJECTION_CASES)
def test_conversions_are_unique_per_pair_and_one_mode_per_broker(build: PayloadFactory, message: str) -> None:
    """A conversion is the engine's decision: one per Broker x ordered pair, one mode per Broker."""
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, build(), message)


def test_pac_solution_binds_its_conversions_under_its_own_label() -> None:
    payload = _pac_incumbent_result()
    payload["primary_solution"]["conversions"] = [deepcopy(_beta_conversion(_rebalancer_incumbent_result()["primary_solution"]))] * 2
    _reject_because(PAC_PLAN_OUTPUT_ADAPTER, payload, "PAC action IDs must be unique")


CONVERSION_READY_REJECTION_CASES = (
    pytest.param(_with_beta_conversion(spread_loss=_money("0", "USD")), "Asset, accounting, and cost projections must use the valuation currency", id="spread-outside-the-valuation-currency"),
    pytest.param(_with_beta_conversion(provenance_ids=["prov-unpublished"]), "Solution rows must reference top-level provenance IDs", id="provenance-not-published"),
    pytest.param(_with_beta_conversion(provenance_ids=["prov-manual", "prov-market", "prov-manual"]), "Result-row provenance IDs must be unique", id="duplicate-provenance-in-the-row"),
)


@pytest.mark.parametrize(("build", "message"), CONVERSION_READY_REJECTION_CASES)
def test_ready_result_holds_conversions_to_valuation_currency_and_provenance(build: PayloadFactory, message: str) -> None:
    """The spread is valued on the conversion, in the valuation currency."""
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, build(), message)


NO_OP_CONVERSION_CASES = (
    pytest.param(PAC_PLAN_OUTPUT_ADAPTER, _pac_no_op_result, id="pac"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_no_op_result, id="rebalancer"),
)


@pytest.mark.parametrize(("adapter", "factory"), NO_OP_CONVERSION_CASES)
def test_no_op_publishes_no_conversion(adapter: TypeAdapter[Any], factory: PayloadFactory) -> None:
    payload = factory()
    model, _emitted = _strict_roundtrip(adapter, payload)
    assert adapter.dump_python(model, mode="json")["primary_solution"]["conversions"] == []

    payload["primary_solution"]["conversions"] = [deepcopy(_beta_conversion(_rebalancer_incumbent_result()["primary_solution"]))]
    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_json(_wire(payload), strict=True)
    errors = exc_info.value.errors(include_url=False)
    assert any(error["type"] == "too_long" and error["loc"][-1] == "conversions" for error in errors), errors


def _assert_available_weight_identities(rows: list[JsonObject], weight_field: str, value_field: str, total: Fraction, zero_reason: str) -> None:
    if total == 0:
        assert all(row[weight_field] == {"kind": "unavailable", "reason": zero_reason} for row in rows)
        return
    for row in rows:
        weight = row[weight_field]
        assert weight["kind"] == "available"
        assert _exact_wire_fraction(weight["value"]) * total == _money_wire_fraction(row[value_field])


ASSET_WEIGHT_IDENTITY_CASES = (
    pytest.param(PAC_PLAN_OUTPUT_ADAPTER, _pac_no_op_result, False, id="pac-zero-final"),
    pytest.param(PAC_PLAN_OUTPUT_ADAPTER, _pac_incumbent_result, False, id="pac-invested"),
)


@pytest.mark.parametrize(("adapter", "factory", "has_before_weights"), ASSET_WEIGHT_IDENTITY_CASES)
def test_asset_weights_match_values_by_exact_cross_multiplication_and_preserve_valid_zero_cases(
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    has_before_weights: bool,
) -> None:
    model, _emitted = _strict_roundtrip(adapter, factory())
    solution = adapter.dump_python(model, mode="json")["primary_solution"]
    rows = solution["asset_rows"]
    accounting = solution["accounting"]

    fixed_reference = _money_wire_fraction(accounting["fixed_reference"])
    target_weights = [_exact_wire_fraction(row["target_weight"]) for row in rows]
    assert sum(target_weights, Fraction()) == 1
    assert all(weight * fixed_reference == _money_wire_fraction(row["target_value"]) for row, weight in zip(rows, target_weights, strict=True))

    final_invested = _money_wire_fraction(accounting["final_invested"])
    _assert_available_weight_identities(rows, "final_weight", "final_value", final_invested, "zero_final_invested")
    if has_before_weights:
        current_invested = _money_wire_fraction(accounting["current_invested"])
        _assert_available_weight_identities(rows, "before_weight", "before_value", current_invested, "zero_current_invested")


REBALANCER_ITEM_WEIGHT_CASES = (
    pytest.param(_rebalancer_no_op_with_zero_asset_result, id="zero-asset"),
    pytest.param(_rebalancer_incumbent_result, id="invested"),
    pytest.param(_rebalancer_no_op_result, id="no-op"),
)


@pytest.mark.parametrize("factory", REBALANCER_ITEM_WEIGHT_CASES)
def test_rebalancer_item_weights_are_shares_of_the_initial_wealth(factory: PayloadFactory) -> None:
    """Contract §6.2: every weight of an Asset, a cash item and the uninvested row is its value over ``F``; the target weights
    of the Assets and the cash items sum to one, and the items with the uninvested row add up to ``F`` before and after."""
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, factory())
    solution = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]
    wealth = _money_wire_fraction(solution["plan_accounts"]["initial_wealth"])
    rows = [*solution["asset_rows"], *solution["cash_rows"]]
    items = [*solution["asset_rows"], *(row for row in solution["cash_rows"] if _exact_wire_fraction(row["target_weight"]) != 0)]
    assert sum((_exact_wire_fraction(row["target_weight"]) for row in items), Fraction()) == 1
    for row in [*rows, solution["uninvested_row"]]:
        for side in ("before", "final"):
            assert _exact_wire_fraction(row[f"{side}_weight"]) * wealth == _money_wire_fraction(row[f"{side}_value"])
    for side in ("before", "final"):
        assert sum((_money_wire_fraction(row[f"{side}_value"]) for row in [*items, solution["uninvested_row"]]), Fraction()) == wealth


@pytest.mark.parametrize("weight_kind", ("target", "before", "final"))
def test_rebalancer_rejects_weight_vectors_that_sum_to_one_but_mismatch_asset_values(weight_kind: str) -> None:
    payload = _rebalancer_no_op_result()
    rows = payload["primary_solution"]["asset_rows"]
    asset_a = _find(rows, "asset_id", "asset-a")
    asset_b = _find(rows, "asset_id", "asset-b")

    if weight_kind == "target":
        asset_a["target_weight"] = _ratio("1", "5", "0.2")
        asset_b["target_weight"] = _ratio("3", "10", "0.3")
    else:
        field = f"{weight_kind}_weight"
        asset_a[field], asset_b[field] = deepcopy(asset_b[field]), deepcopy(asset_a[field])
    _reject(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)


@pytest.mark.parametrize(
    "replacement",
    (
        pytest.param({"kind": "available", "value": _finite("0")}, id="available-at-zero-total"),
        pytest.param({"kind": "unavailable", "reason": "zero_current_invested"}, id="wrong-zero-reason"),
    ),
)
def test_zero_final_invested_requires_exact_unavailable_reason(replacement: JsonObject) -> None:
    payload = _pac_no_op_result()
    _find(payload["primary_solution"]["asset_rows"], "asset_id", "asset-one")["final_weight"] = deepcopy(replacement)
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)


@pytest.mark.parametrize(
    ("product", "mutation"),
    (
        ("PAC", "cost"),
        ("PAC", "ledger-flow"),
        ("PAC", "order"),
        ("PAC", "final-value"),
        ("Rebalancer", "cost"),
        ("Rebalancer", "ledger-flow"),
        ("Rebalancer", "order"),
        ("Rebalancer", "final-value"),
    ),
)
def test_no_op_results_forbid_actions_costs_and_portfolio_changes(product: str, mutation: str) -> None:
    if product == "PAC":
        payload = _pac_no_op_result()
        adapter = PAC_PLAN_OUTPUT_ADAPTER
        action_source = _pac_incumbent_result()
    else:
        payload = _rebalancer_no_op_result()
        adapter = REBALANCER_PLAN_OUTPUT_ADAPTER
        action_source = _rebalancer_incumbent_result()
    solution = payload["primary_solution"]

    if mutation == "cost":
        solution["costs"]["buy_fees"] = _money("0.01")
    elif mutation == "ledger-flow":
        broker_id = "broker-one" if product == "PAC" else "broker-alpha"
        _find(solution["ledger_rows"], "broker_id", broker_id)["funding_in"] = "1"
    elif mutation == "order":
        order_id = "order-buy-asset-one" if product == "PAC" else "order-buy-b-beta"
        solution["order_rows"] = [deepcopy(_find(action_source["primary_solution"]["order_rows"], "order_id", order_id))]
    else:
        asset_id = "asset-one" if product == "PAC" else "asset-a"
        asset = _find(solution["asset_rows"], "asset_id", asset_id)
        asset["final_value"] = _money("1")
    _reject(adapter, payload)


def test_distinct_deployment_strict_roundtrip_covers_every_order_and_objective_delta() -> None:
    payload = _distinct_deployment_pac_result()
    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")
    primary = wire["primary_solution"]
    deployment = wire["deployment"]
    comparison = deployment["comparison"]

    assert deployment["kind"] == "distinct"
    assert primary["solution_id"] != deployment["solution"]["solution_id"]
    assert comparison["primary_solution_id"] == primary["solution_id"]
    assert comparison["deployment_solution_id"] == deployment["solution"]["solution_id"]
    assert comparison["changed_order_rows"] == 1
    assert len(comparison["objective_deltas"]) == len(primary["objectives"]["stages"])


DISTINCT_DEPLOYMENT_PRODUCT_CASES = (
    pytest.param(PAC_PLAN_OUTPUT_ADAPTER, _distinct_deployment_pac_result, id="pac"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _distinct_deployment_rebalancer_result, id="rebalancer"),
)


@pytest.mark.parametrize(("adapter", "factory"), DISTINCT_DEPLOYMENT_PRODUCT_CASES)
def test_distinct_deployment_solution_has_no_inherited_proof_and_strictly_rejects_one(
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
) -> None:
    payload = factory()
    assert "proof" in payload
    assert "proof" not in payload["deployment"]["solution"]

    model, _emitted = _strict_roundtrip(adapter, payload)
    wire = adapter.dump_python(model, mode="json")
    assert "proof" not in wire["deployment"]["solution"]

    payload["deployment"]["solution"]["proof"] = deepcopy(payload["proof"])
    _assert_extra_forbidden(adapter, payload, "proof")


@pytest.mark.parametrize(
    "mutation",
    (
        "same-solution-id",
        "wrong-primary-reference",
        "wrong-deployment-reference",
        "wrong-changed-row-count",
        "identical-order-rows",
        "missing-objective-delta",
        "wrong-objective-identity",
        "wrong-objective-arithmetic",
    ),
)
def test_distinct_deployment_rejects_identity_count_coverage_and_arithmetic_errors(mutation: str) -> None:
    payload = _distinct_deployment_pac_result()
    primary = payload["primary_solution"]
    deployment = payload["deployment"]
    comparison = deployment["comparison"]

    if mutation == "same-solution-id":
        deployment["solution"]["solution_id"] = primary["solution_id"]
    elif mutation == "wrong-primary-reference":
        comparison["primary_solution_id"] = "pac-primary-wrong"
    elif mutation == "wrong-deployment-reference":
        comparison["deployment_solution_id"] = "pac-deployment-wrong"
    elif mutation == "wrong-changed-row-count":
        comparison["changed_order_rows"] = 2
    elif mutation == "identical-order-rows":
        deployment["solution"]["order_rows"] = deepcopy(primary["order_rows"])
    elif mutation == "missing-objective-delta":
        comparison["objective_deltas"] = [delta for delta in comparison["objective_deltas"] if delta["objective_code"] != "fixed_l2"]
    elif mutation == "wrong-objective-identity":
        _find(comparison["objective_deltas"], "objective_code", "fixed_l2")["unit"] = {"kind": "count"}
    else:
        _find(comparison["objective_deltas"], "objective_code", "fixed_l2")["delta"] = _finite("1")
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)


# Contract 2.0.0 (A4, project 67), final: conversions without fx actions, target entries with limits, no required minimum, the closed issue and
# objective codes, an empty request_fingerprint on a failure, the ledger columns (transfers, foreign withholding), the cost line, the limit rows.
# The PAC fingerprint is the gate of blocks B and C: it does not move again in A4.
# Rounding direction fix: recomputed for description-only changes (``PlannerRoundingTopUp`` docstring, ``rounding_top_ups`` description, new ``rounding_bound`` description).
# B4 (project 67, decisioni-REB §11.6): both move once more, for ``operation`` = ``plan`` | ``preview`` and the preview's euros.
# B3 (project 67, S1, D11): only the Rebalancer's moves, to its final request (one class, fidelity, ``tax``, no funding routes)
# and result (items on F, cash items, uninvested, transfers, top-ups, plan accounts, score, tax parts, the final sale row);
# the PAC's stays where A4 left it. C1 moves the Rebalancer's once more, to widen the strategy field.
# The PAC accounts on the wire (B3, coordinator's instruction against X1): the PAC's moves once, for ``plan_accounts`` on its
# solution, the shared type both Tools publish (contract §6.1); the PAC's screen does not change (X17).
# Lot SE (project 67, the coordinator's decision of 16/11) moves both: one more closed issue code,
# allocation.solver_numerical_error, in the shared PlannerIssueCode.
# Lot ZB (project 67, the developer's decision of 17/11, specification §16.16) moves both: one more closed issue code,
# allocation.cash_limit_exceeded_by_rounding, and ``completed`` among a ready_no_incumbent's stops.
# Lot SEEDS (project 67) moves both: two not-proven reasons in the shared NotProvenReasonCode.
# The largest deviation's item (X14, project 67) moves the Rebalancer's alone: two references on its score.
# R1-A (project 67, contract §6.8) moves the PAC's alone: a plan needs a step, not an order (``order_rows`` loses its minimum).
# R1-F (b) (project 67, developer decision of 21/11) moves the Rebalancer's alone: its request loses the preview's euros
# (``custom_reference_amount``), since the page turns them into λ itself.
# TL-5 (project 67, the developer's answers of 24/11) moves both: the plan accounts gain the cash at the end and the cash
# by currency, and the Rebalancer's uninvested row its two parts, the cash with no target and the costs.
PLANNER_FULL_SCHEMA_FINGERPRINT_CASES = (
    pytest.param(
        PAC_PLAN_INPUT_ADAPTER,
        PAC_PLAN_OUTPUT_ADAPTER,
        "96aefec9524787fa1d001b313bb818abf7174c1c5caa1fba0fd218422a2bfab4",
        id="pac",
    ),
    pytest.param(
        REBALANCER_PLAN_INPUT_ADAPTER,
        REBALANCER_PLAN_OUTPUT_ADAPTER,
        "6f652b2f34bb77f23c222b35046272287bf76f3c9104d825b725a27f5d5592f1",
        id="rebalancer",
    ),
)


@pytest.mark.parametrize(("input_adapter", "output_adapter", "expected_fingerprint"), PLANNER_FULL_SCHEMA_FINGERPRINT_CASES)
def test_full_planner_schema_fingerprints_are_frozen(
    input_adapter: TypeAdapter[Any],
    output_adapter: TypeAdapter[Any],
    expected_fingerprint: str,
) -> None:
    input_schema = generate_tool_schema(input_adapter, "validation")
    output_schema = generate_tool_schema(output_adapter, "serialization")
    assert schema_fingerprint(input_schema, output_schema, frozenset({"plan"})) == expected_fingerprint


PLANNER_SCHEMA_CASES = (
    pytest.param("pac-input", PAC_PLAN_INPUT_ADAPTER, "validation", 1, None, id="pac-input"),
    pytest.param("rebalancer-input", REBALANCER_PLAN_INPUT_ADAPTER, "validation", 1, None, id="rebalancer-input"),
    pytest.param("pac-output", PAC_PLAN_OUTPUT_ADAPTER, "serialization", 7, "result_state", id="pac-output"),
    pytest.param("rebalancer-output", REBALANCER_PLAN_OUTPUT_ADAPTER, "serialization", 7, "result_state", id="rebalancer-output"),
    # What each service serves since B4 (project 67): one request model whose ``operation`` is ``plan`` or ``preview``, and
    # one output union on ``result_state`` with both operations' results.
    pytest.param("pac-tool-output", PAC_TOOL_OUTPUT_ADAPTER, "serialization", 11, "result_state", id="pac-tool-output"),
    pytest.param("rebalancer-tool-output", REBALANCER_TOOL_OUTPUT_ADAPTER, "serialization", 11, "result_state", id="rebalancer-tool-output"),
)


def _assert_acyclic_local_references(schema: JsonObject) -> None:
    definitions = schema.get("$defs", {})
    assert isinstance(definitions, dict)
    dependencies: dict[str, set[str]] = {}
    for name, definition in definitions.items():
        assert isinstance(name, str)
        assert isinstance(definition, dict)
        dependencies[name] = set()
        for node in walk_schema(definition):
            reference = node.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                dependencies[name].add(reference.removeprefix("#/$defs/").replace("~1", "/").replace("~0", "~"))

    visited: set[str] = set()
    active: set[str] = set()

    def visit(name: str) -> None:
        assert name not in active, f"recursive schema reference through {name}"
        if name in visited:
            return
        active.add(name)
        for dependency in dependencies.get(name, set()):
            visit(dependency)
        active.remove(name)
        visited.add(name)

    for name in definitions:
        visit(name)


def _open_map_property_schema_node_ids(schema: JsonObject) -> frozenset[int]:
    """Node identities for the `fx_rates` property's own schema, wherever it is declared.

    `fx_rates` is a product-decided canonical currency-pair map (open string keys); JSON
    Schema represents it as `additionalProperties: <value-schema>`, which is structurally
    incompatible with the closed/named-property invariant enforced below. This locates
    exactly that field's node by declared property key (not by shape), so the invariant is
    relaxed there and nowhere else.
    """
    node_ids: set[int] = set()
    for node in walk_schema(schema):
        properties = node.get("properties")
        if not isinstance(properties, dict):
            continue
        value = properties.get("fx_rates")
        if isinstance(value, dict) and value.get("type") == "object":
            node_ids.add(id(value))
    return frozenset(node_ids)


def _property_schema_node_ids(schema: JsonObject) -> frozenset[int]:
    """Node identities of every property schema: the only place a `default` may be published."""
    return frozenset(id(value) for node in walk_schema(schema) if isinstance(node.get("properties"), dict) for value in node["properties"].values() if isinstance(value, dict))


@pytest.mark.parametrize("_label,adapter,mode,expected_roots,_root_discriminator", PLANNER_SCHEMA_CASES)
def test_exported_planner_schema_profile_has_only_closed_required_codegen_safe_shapes(
    _label: str,
    adapter: TypeAdapter[Any],
    mode: str,
    expected_roots: int,
    _root_discriminator: str | None,
) -> None:
    schema = generate_tool_schema(adapter, mode)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    # A request serves both operations; a ``plan`` result union says only ``plan``, a service's output union both.
    assert declared_operations(schema) == (frozenset({"plan", "preview"}) if mode == "validation" or "-tool-" in _label else frozenset({"plan"}))
    assert len(list(root_models(schema))) == expected_roots
    _assert_acyclic_local_references(schema)
    open_map_node_ids = _open_map_property_schema_node_ids(schema)
    property_schema_ids = _property_schema_node_ids(schema)

    for node in walk_schema(schema):
        # Contract compaction: a neutral default is published on the property that has it, never on a type.
        assert "default" not in node or id(node) in property_schema_ids
        assert "prefixItems" not in node
        assert "patternProperties" not in node
        assert "$dynamicRef" not in node
        assert "$recursiveRef" not in node
        assert "$id" not in node
        assert node.get("type") != "number"

        reference = node.get("$ref")
        if reference is not None:
            assert isinstance(reference, str)
            assert reference.startswith("#/")
            resolve_schema_reference(schema, reference)

        if node.get("type") == "object":
            if id(node) in open_map_node_ids:
                additional = node.get("additionalProperties")
                assert isinstance(additional, dict)
                assert "properties" not in node
                assert "required" not in node
            else:
                assert node.get("additionalProperties") is False
                properties = node.get("properties")
                assert isinstance(properties, dict)
                assert all(isinstance(property_schema, dict) for property_schema in properties.values())
                if mode == "validation":
                    # An input property is either required or carries its neutral default: never
                    # both, never neither.  Pydantic omits `required` when it would be empty.
                    required = node.get("required", [])
                    assert isinstance(required, list)
                    assert set(required) <= set(properties)
                    for name, property_schema in properties.items():
                        assert (name in required) != ("default" in property_schema), name
                else:
                    # json_schema_serialization_defaults_required: an emitted object carries every field.
                    required = node.get("required")
                    assert isinstance(required, list)
                    assert set(required) == set(properties)

        pattern = node.get("pattern")
        if isinstance(pattern, str):
            re.compile(pattern)
            for unsupported in ("(?P", "(?<=", "(?<!", "\\A", "\\Z", "\\g<", "\\k<", "(?i", "(?m", "(?s", "(?x"):
                assert unsupported not in pattern
            assert not re.search(r"\\[1-9]", pattern)


@pytest.mark.parametrize("_label,adapter,mode,_expected_roots,root_discriminator", PLANNER_SCHEMA_CASES)
def test_every_exported_object_union_has_named_local_discriminator_mappings(
    _label: str,
    adapter: TypeAdapter[Any],
    mode: str,
    _expected_roots: int,
    root_discriminator: str | None,
) -> None:
    schema = generate_tool_schema(adapter, mode)
    observed: set[str] = set()
    for node in walk_schema(schema):
        branches = node.get("oneOf")
        if not isinstance(branches, list):
            continue
        resolved = [resolve_schema_reference(schema, branch["$ref"]) for branch in branches if isinstance(branch, dict) and isinstance(branch.get("$ref"), str)]
        if len(resolved) != len(branches) or not all(branch.get("type") == "object" for branch in resolved):
            continue

        discriminator = node.get("discriminator")
        assert isinstance(discriminator, dict)
        property_name = discriminator.get("propertyName")
        mapping = discriminator.get("mapping")
        assert isinstance(property_name, str)
        assert isinstance(mapping, dict)
        observed.add(property_name)
        assert set(mapping.values()) == {branch["$ref"] for branch in branches}
        for target in mapping.values():
            branch = resolve_schema_reference(schema, target)
            assert property_name in branch["required"]
            literal = branch["properties"][property_name]
            assert "const" in literal or "enum" in literal
            assert "default" not in literal

    if root_discriminator is not None:
        root_marker = schema.get("discriminator")
        assert isinstance(root_marker, dict)
        assert root_marker["propertyName"] == root_discriminator
        assert root_discriminator in observed
    assert observed <= {"result_state", "kind", "side"}


def test_exported_planner_contract_uses_all_required_named_discriminator_families() -> None:
    observed: set[str] = set()
    for adapter, mode in (
        (PAC_PLAN_INPUT_ADAPTER, "validation"),
        (REBALANCER_PLAN_INPUT_ADAPTER, "validation"),
        (PAC_PLAN_OUTPUT_ADAPTER, "serialization"),
        (REBALANCER_PLAN_OUTPUT_ADAPTER, "serialization"),
        (REBALANCER_TOOL_OUTPUT_ADAPTER, "serialization"),
    ):
        schema = generate_tool_schema(adapter, mode)
        for node in walk_schema(schema):
            discriminator = node.get("discriminator")
            if isinstance(discriminator, dict) and isinstance(discriminator.get("propertyName"), str):
                observed.add(discriminator["propertyName"])
    # The Rebalancer request is one class since B3 (project 67): no union on ``policy`` any more. Since B4 a request's
    # ``operation`` is ``plan`` or ``preview`` on the same model, so validation paths stay the same for both.
    assert observed == {"result_state", "kind", "side"}


# ---------------------------------------------------------------------------
# A4 step 2 (project 67): one conversion per engine decision, no FX actions, no FX cost on a buy row
# ---------------------------------------------------------------------------


def _without_fx_actions(payload: JsonObject) -> JsonObject:
    """``payload`` as contract 2.0.0 publishes it: no ``fx_actions`` list, no ``fx_action_ids``, no ``fx_cost`` on a buy row."""
    result = deepcopy(payload)
    solution = result["primary_solution"]
    solution.pop("fx_actions", None)
    for conversion in solution["conversions"]:
        conversion.pop("fx_action_ids", None)
    for order in solution["order_rows"]:
        order.pop("fx_cost", None)
    return result


def test_buy_order_row_has_no_fx_cost() -> None:
    """The field was always zero (the spread lives on the conversion) and goes away: a buy row without it is the row, and one
    that still carries it is refused as an extra field."""
    payload = _without_fx_actions(_rebalancer_incumbent_result())
    _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
    buy = _find(payload["primary_solution"]["order_rows"], "order_id", "order-buy-b-beta")
    buy["fx_cost"] = _money("0")
    _reject(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)


@pytest.mark.parametrize(("adapter", "factory"), [pytest.param(PAC_PLAN_OUTPUT_ADAPTER, _pac_incumbent_result, id="pac"), pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, id="rebalancer")])
def test_solution_publishes_conversions_and_no_fx_actions(adapter: TypeAdapter[Any], factory: PayloadFactory) -> None:
    """One list only: the conversions, each the engine's own decision. The action list and the ids that tied an action to its
    conversion are gone."""
    payload = _without_fx_actions(factory())
    model, _emitted = _strict_roundtrip(adapter, payload)
    solution = adapter.dump_python(model, mode="json")["primary_solution"]
    assert "fx_actions" not in solution
    assert all("fx_action_ids" not in conversion for conversion in solution["conversions"])

    with_actions = deepcopy(payload)
    with_actions["primary_solution"]["fx_actions"] = []
    _reject(adapter, with_actions)
    if payload["primary_solution"]["conversions"]:
        with_ids = deepcopy(payload)
        with_ids["primary_solution"]["conversions"][0]["fx_action_ids"] = ["fx-action"]
        _reject(adapter, with_ids)


def _conversion_back_at_broker_beta(payload: JsonObject, *, source: str, destination: str, rate: str) -> JsonObject:
    """``payload`` with a second conversion at broker-beta, automatic like the first, so only V7 can speak."""
    solution = payload["primary_solution"]
    _add_conversion(solution, broker_id="broker-beta", source=source, destination=destination, rate=rate, mode="automatic", sequence=None)
    solution["conversions"][0]["mode"] = "automatic"
    solution["conversions"][0]["sequence"] = None
    for sequence, order in enumerate(sorted(solution["order_rows"], key=lambda row: row["sequence"]), start=3):
        order["sequence"] = sequence
    return payload


def test_conversions_never_run_both_ways_on_one_broker() -> None:
    """V7 in the contract, widened as the engine has it: on a Broker a currency that receives a conversion gives none. The two
    directions of one pair are refused; the same pair at another Broker is fine."""
    base = _without_fx_actions(_rebalancer_incumbent_result())
    both_ways = _conversion_back_at_broker_beta(deepcopy(base), source="USD", destination="EUR", rate="0.8")
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, both_ways, "a currency that receives a conversion cannot give one")

    solution = deepcopy(base)
    _add_conversion(solution["primary_solution"], broker_id="broker-alpha", source="EUR", destination="USD", rate="1.25", mode="manual", sequence=8)
    _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, solution)


# ---------------------------------------------------------------------------
# B3 (project 67): the Rebalancer's result in its final form (S1)
# ---------------------------------------------------------------------------


def _sell_row() -> JsonObject:
    return deepcopy(next(row for row in _rebalancer_incumbent_result()["primary_solution"]["order_rows"] if row["kind"] == "sell"))


SELL_ROW_ADAPTER = TypeAdapter(PlannerSellOrderRow)


def test_sell_row_net_reconciles_gross_fee_withholding_and_tax() -> None:
    """B3 test 18 (contract §6.3): ``net = gross − fee − foreign withholding − tax``; a loss is a negative gain, admitted; the
    net may be zero or negative; the gain and the cost basis share one currency, the order amounts another."""
    row = _sell_row()
    _strict_roundtrip(SELL_ROW_ADAPTER, row)

    loss = deepcopy(row)
    loss["realized_gain"] = _money("-4")
    loss["tax"] = {"amount": "0", "currency": "EUR"}
    loss["net_credit"] = {"amount": "30", "currency": "EUR"}
    loss["reason"] = "loss_offset"
    _strict_roundtrip(SELL_ROW_ADAPTER, loss)

    negative = deepcopy(row)
    negative.update(fee={"amount": "29", "currency": "EUR"}, foreign_withholding_tax={"amount": "0.57", "currency": "EUR"}, net_credit={"amount": "-1", "currency": "EUR"})
    _strict_roundtrip(SELL_ROW_ADAPTER, negative)
    zero = deepcopy(negative)
    zero.update(fee={"amount": "28", "currency": "EUR"}, net_credit={"amount": "0", "currency": "EUR"})
    _strict_roundtrip(SELL_ROW_ADAPTER, zero)

    wrong = deepcopy(row)
    wrong["net_credit"] = {"amount": "30", "currency": "EUR"}
    _reject_because(SELL_ROW_ADAPTER, wrong, "SELL net credit must equal gross credit less fee, foreign withholding and tax")
    other_currency = deepcopy(row)
    other_currency["tax"] = {"amount": "1.43", "currency": "USD"}
    _reject_because(SELL_ROW_ADAPTER, other_currency, "SELL fee, taxes and net credit must use the order currency")
    for field, value in (("tax_handling", "self_reserved"), ("reason", "funding")):
        _reject(SELL_ROW_ADAPTER, {**row, field: value})
    for withdrawn in ("taxable_gain", "tax_reserve", "withholding_kind", "spendable_credit", "irreducibility_evidence_ref"):
        _assert_extra_forbidden(SELL_ROW_ADAPTER, {**row, withdrawn: None}, withdrawn)


def test_rebalancer_ready_result_may_end_fully_in_cash() -> None:
    """B3 test 4 (contract §3, specifica §15 n. 14): a ready Rebalancer plan may sell every Asset; final invested zero, the
    items on ``F`` still adding up. The exposure is on the whole portfolio (developer's decision of 13/11): after, on ``W``,
    it is all cash, every category at zero."""
    payload = _rebalancer_incumbent_result()
    solution = payload["primary_solution"]
    for asset in solution["asset_rows"]:
        asset["buy_mid_value"] = _money("0")
        asset["sell_mid_value"] = deepcopy(asset["before_value"])
    _reprice_rebalancer(solution, final=dict.fromkeys(_MEDIUM_BEFORE, Fraction(0)))
    for exposure in solution["exposure_rows"]:
        exposure["final_weight"] = {"kind": "available", "value": _finite("1" if exposure["kind"] == "cash" else "0")}
    accounting = solution["accounting"]
    accounting["shortfall"] = _money("200")
    accounting["free_cash"] = _money("198.57")

    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
    wire = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]
    assert _money_wire_fraction(wire["accounting"]["final_invested"]) == 0
    assert _money_wire_fraction(wire["uninvested_row"]["final_value"]) == Fraction(19643, 100) - 0


def test_invest_only_result_publishes_empty_tax_parts() -> None:
    """B3 test 21 (contract §6.4): a plan that sells nothing publishes its tax parts, empty; one that is not empty is refused."""
    payload = _rebalancer_no_op_result()
    payload["scenario_basis"]["policy"] = "invest_only"
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
    wire = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]
    assert all(wire[name] == [] for name in ("tax_basket_rows", "tax_scope_rows", "tax_reserves", "asset_type_tax_rows"))
    assert not any(row["kind"] == "sell" for row in wire["order_rows"])

    medium = _rebalancer_incumbent_result()["primary_solution"]
    for name in ("tax_basket_rows", "tax_scope_rows", "asset_type_tax_rows"):
        filled = deepcopy(payload)
        filled["primary_solution"][name] = deepcopy(medium[name])
        _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, filled, "A plan that sells nothing publishes empty tax parts")


TAX_PART_ADAPTERS = {
    "tax_basket_rows": TypeAdapter(RebalancerTaxBasketRow),
    "tax_scope_rows": TypeAdapter(RebalancerTaxScopeRow),
    "asset_type_tax_rows": TypeAdapter(RebalancerAssetTypeTaxRow),
}


@pytest.mark.parametrize("section", sorted(TAX_PART_ADAPTERS))
def test_tax_summary_shapes_round_trip(section: str) -> None:
    """B3 test 22 (contract §6.4): each tax part of the hand-written medium plan makes a strict roundtrip on its own; a reserve
    too, in the currency it is set aside in; magnitudes cannot be negative."""
    rows = _rebalancer_incumbent_result()["primary_solution"][section]
    assert rows
    adapter = TAX_PART_ADAPTERS[section]
    for row in rows:
        model, emitted = _strict_roundtrip(adapter, row)
        assert json.loads(emitted) == row
    if section != "tax_scope_rows":
        negative = deepcopy(rows[0])
        negative["tax"] = _money("-1")
        _reject(adapter, negative)
    _strict_roundtrip(TypeAdapter(RebalancerTaxReserveRow), {"broker_id": "broker-beta", "amount": {"amount": "1.43", "currency": "USD"}})
    _reject(TypeAdapter(RebalancerTaxReserveRow), {"broker_id": "broker-beta", "amount": {"amount": "0", "currency": "USD"}})


def _medium_mutated(mutate: Callable[[JsonObject], None]) -> Callable[[], JsonObject]:
    def build() -> JsonObject:
        payload = _rebalancer_incumbent_result()
        mutate(payload)
        return payload

    return build


def _set(path: tuple[Any, ...], value: Any) -> Callable[[JsonObject], None]:
    def mutate(payload: JsonObject) -> None:
        _select(payload, path[:-1])[path[-1]] = value

    return mutate


def _strip_steps(payload: JsonObject) -> None:
    for section in ("funding_actions", "conversions", "transfers", "order_rows"):
        payload["primary_solution"][section] = []


def _costs_before_the_plan(payload: JsonObject) -> None:
    """A cent of costs before the plan, moved from the cash with no target so the parts still sum to the row."""
    row = payload["primary_solution"]["uninvested_row"]
    row["costs"]["before_value"] = _money("0.01")
    row["untargeted_cash"]["before_value"] = _money("49.99")


def _cash_in_a_currency_before_the_valuation(payload: JsonObject) -> None:
    """A USD row with nothing at either end, listed before EUR, the valuation currency."""
    rows = payload["primary_solution"]["plan_accounts"]["cash_by_currency"]
    rows.insert(0, {"currency": "USD", "initial": _money("0", "USD"), "final": _money("0", "USD"), "unused_contributions": _money("0", "USD")})


REBALANCER_RESULT_REJECTION_CASES = (
    pytest.param(_medium_mutated(_set(("primary_solution", "plan_accounts", "money_lost", "broker_withheld_tax"), _money("1.42"))), "The money lost, by entry, must sum to the initial less the final wealth", id="money-lost-off-by-a-cent"),
    pytest.param(_medium_mutated(_set(("primary_solution", "score", "plan_score"), _money("2.27"))), "The plan score must equal λ·D/F plus the money lost", id="plan-score"),
    pytest.param(_medium_mutated(_set(("primary_solution", "score", "target_distance"), _finite("168"))), "The target distance must be the squared residuals of the items plus the uninvested squared", id="target-distance"),
    pytest.param(_medium_mutated(_set(("primary_solution", "score", "largest_deviation_after"), _finite("0.04"))), "The largest deviation must be read off the items' weights", id="largest-deviation"),
    # X14, «which entry»: after the plan asset-c is 5 points off, the furthest; naming another item, an item that is not one of
    # the distance (a cash cell with no target, the uninvested row has no reference at all), or none, is refused.
    pytest.param(_medium_mutated(_set(("primary_solution", "score", "largest_deviation_after_item"), {"kind": "asset", "asset_id": "asset-d"})), "The largest deviation must name the first item at it, in the published order", id="largest-deviation-item"),
    pytest.param(_medium_mutated(_set(("primary_solution", "score", "largest_deviation_after_item"), {"kind": "cash", "broker_id": "broker-alpha", "currency": "USD"})), "The largest deviation must name the first item at it, in the published order", id="largest-deviation-item-not-an-item"),
    pytest.param(_medium_mutated(_set(("primary_solution", "score", "largest_deviation_after_item"), None)), "The largest deviation names its item exactly when some item is off its target", id="largest-deviation-item-missing"),
    pytest.param(
        _medium_mutated(_set(("primary_solution", "score", "largest_deviation_after"), _finite("0"))),
        "The largest deviation names its item exactly when some item is off its target",
        id="largest-deviation-zero-with-an-item",
    ),
    pytest.param(_medium_mutated(_set(("primary_solution", "plan_accounts", "uninvested"), _money("1.42"))), "The uninvested value must be the initial wealth less the final invested value and the cash items with a target", id="uninvested"),
    pytest.param(_medium_mutated(_set(("primary_solution", "objectives", "stages", ("objective_code", "plan_score"), "value"), _finite("2.27"))), "The published objective stages must match the score", id="plan-score-stage"),
    pytest.param(_medium_mutated(_set(("scenario_basis", "initial_wealth"), _money("199"))), "Rebalancer initial wealth must equal current invested plus selected funding", id="basis-initial-wealth"),
    pytest.param(_medium_mutated(_set(("primary_solution", "transfers", ("transfer_id", "transfer-alpha-beta-eur"), "destination_broker_id"), "broker-alpha")), "A transfer moves cash between two different Brokers", id="transfer-to-itself"),
    pytest.param(_medium_mutated(_set(("primary_solution", "transfers", ("transfer_id", "transfer-alpha-beta-eur"), "destination_broker_id"), "broker-gamma")), "Transfer rows must reference catalog Broker IDs", id="transfer-unknown-broker"),
    pytest.param(_medium_mutated(_set(("primary_solution", "transfers", ("transfer_id", "transfer-alpha-beta-eur"), "sequence"), 4)), "Rebalancer action sequences must be unique", id="transfer-on-an-order-step"),
    pytest.param(_medium_mutated(_set(("primary_solution", "score", "distance_weight"), None)), "both present (a weighted fidelity) or both absent", id="score-without-lambda"),
    pytest.param(_medium_mutated(_set(("primary_solution", "cash_rows", ("broker_id", "broker-alpha"), "target_weight"), _finite("0.06"))), "An item's target value must be its target weight of the initial wealth", id="cash-item-target"),
    pytest.param(_medium_mutated(_strip_steps), "A Rebalancer plan with no step is a no-op solution", id="incumbent-without-a-step"),
    # TL-5 of project 67: the uninvested row's two parts and the cash by currency.
    pytest.param(_medium_mutated(_set(("primary_solution", "uninvested_row", "untargeted_cash", "final_value"), _money("0.01"))), "The uninvested row's parts must sum to its final_value", id="uninvested-parts-value"),
    pytest.param(_medium_mutated(_set(("primary_solution", "uninvested_row", "costs", "final_weight"), _finite("0.0072"))), "The uninvested row's parts must sum to its final_weight", id="uninvested-parts-weight"),
    pytest.param(_medium_mutated(_costs_before_the_plan), "Nothing is lost before the plan", id="costs-before-the-plan"),
    pytest.param(_medium_mutated(_set(("primary_solution", "plan_accounts", "cash_by_currency", ("currency", "EUR"), "final"), _money("3.56"))), "Rebalancer cash at the end of a currency must be its ledger's spendable balance plus the contributions not deposited", id="cash-end-off-the-ledger"),
    pytest.param(_medium_mutated(_cash_in_a_currency_before_the_valuation), "the valuation currency first, then by code", id="cash-currencies-order"),
    pytest.param(_medium_mutated(_set(("primary_solution", "plan_accounts", "final_cash"), _money("3.58"))), "Rebalancer cash at the end must be the final wealth less the Assets after the plan", id="final-cash"),
    pytest.param(_medium_mutated(_set(("primary_solution", "plan_accounts", "cash_by_currency", ("currency", "EUR"), "initial"), _money("-1"))), "The cash at the start and the unused contributions cannot be negative", id="cash-start-negative"),
)


@pytest.mark.parametrize(("build", "message"), REBALANCER_RESULT_REJECTION_CASES)
def test_rebalancer_result_rejects_an_inconsistent_plan(build: PayloadFactory, message: str) -> None:
    """The Rebalancer's plan accounts, score, items and steps are read off one another exactly; each case breaks one rule."""
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, build(), message)


def test_pac_incumbent_needs_a_step_not_an_order() -> None:
    """Contract §6.8 (20/11/2026): a PAC plan has at least one step, an order, a deposit or a conversion, as the
    Rebalancer's (§6.3); none of the lists is required alone. A plan with no step at all is a no-op solution."""
    payload = _pac_incumbent_result()
    for section in ("funding_actions", "conversions", "order_rows"):
        payload["primary_solution"][section] = []
    _reject_because(PAC_PLAN_OUTPUT_ADAPTER, payload, "A PAC plan with no step is a no-op solution")


def test_rebalancer_no_op_publishes_no_transfer() -> None:
    """A plan of transfers alone is not «no operation» (contract §6.3): a no-op solution has none."""
    payload = _rebalancer_no_op_result()
    payload["primary_solution"]["transfers"] = deepcopy(_rebalancer_incumbent_result()["primary_solution"]["transfers"])
    with pytest.raises(ValidationError) as exc_info:
        REBALANCER_PLAN_OUTPUT_ADAPTER.validate_json(_wire(payload), strict=True)
    errors = exc_info.value.errors(include_url=False)
    assert any(error["type"] == "too_long" and error["loc"][-1] == "transfers" for error in errors), errors


def _medium_with_a_limit_only_cash_row() -> JsonObject:
    """The medium plan with broker-alpha's EUR cash carrying only a maximum (weight zero) and C back at a quarter: the 3.57 EUR
    left there are part of ``N``, not an item of the distance, as in the exact replay."""
    payload = _rebalancer_incumbent_result()
    solution = payload["primary_solution"]
    asset_c = _find(solution["asset_rows"], "asset_id", "asset-c")
    asset_c["target_weight"], asset_c["target_value"] = _finite("0.25"), _money("50")
    cash = _find(solution["cash_rows"], "broker_id", "broker-alpha")
    cash.update(target_weight=_finite("0"), target_value=_money("0"), maximum=_money("5"))
    _reprice_rebalancer(solution, final={"asset-a": Fraction(50), "asset-b": Fraction(50), "asset-c": Fraction(50), "asset-d": Fraction(45)})
    # The exposure targets follow the items' weights: no cash target, a quarter on each sector, the whole on one category.
    for exposure in solution["exposure_rows"]:
        whole = exposure["kind"] == "category" and exposure["dimension"] != "sector"
        exposure["target_weight"] = _finite("0" if exposure["kind"] == "cash" else "1" if whole else "0.25")
    return payload


def test_limit_only_cash_row_sits_inside_the_uninvested_row() -> None:
    """A cash row with only a limit is published (its value and its limit) but is no item of the distance: ``N`` holds its
    cash, ``D`` = 5² + 5² (D and N), and the largest deviation reads the Assets alone."""
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, _medium_with_a_limit_only_cash_row())
    solution = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["primary_solution"]
    assert _money_wire_fraction(solution["uninvested_row"]["final_value"]) == 5
    assert _exact_wire_fraction(solution["score"]["target_distance"]) == 50
    assert _exact_wire_fraction(solution["score"]["largest_deviation_after"]) == Fraction(1, 40)

    counted_twice = _medium_with_a_limit_only_cash_row()
    counted_twice["primary_solution"]["score"]["target_distance"] = _finite("62.7449")  # 5² + 3.57² + 1.43² + ... as if the row were an item
    _reject(REBALANCER_PLAN_OUTPUT_ADAPTER, counted_twice)


def _medium_target_first() -> JsonObject:
    payload = _rebalancer_incumbent_result()
    payload["scenario_basis"]["target_fidelity"] = {"kind": "target_first"}
    solution = payload["primary_solution"]
    solution["score"]["distance_weight"] = None
    solution["score"]["plan_score"] = None
    money_squared = {"kind": "valuation_money_squared", "currency_code": "EUR"}
    stages = solution["objectives"]["stages"]
    by_code = {stage["objective_code"]: stage for stage in stages}
    solution["objectives"]["stages"] = [
        {"objective_code": "target_distance", "ordinal": 1, "sense": "min", "unit": money_squared, "value": _finite("0")},
        {"objective_code": "wealth_loss", "ordinal": 2, "sense": "min", "unit": deepcopy(by_code["plan_score"]["unit"]), "value": _finite("0")},
        {**by_code["operation_count"], "ordinal": 3},
        {**by_code["route_priority"], "ordinal": 4},
    ]
    evidence = {stage["objective_code"]: stage for stage in payload["solver_evidence"]["stages"]}
    payload["solver_evidence"]["stages"] = [
        {**evidence["plan_score"], "stage": "target_distance", "objective_code": "target_distance", "unit": money_squared, "primal": "168.3898", "dual": "168.3898"},
        {**evidence["plan_score"], "stage": "wealth_loss", "objective_code": "wealth_loss", "ordinal": 2, "primal": "1.43", "dual": "1.43"},
        {**evidence["operation_count"], "ordinal": 3},
        {**evidence["route_priority"], "ordinal": 4},
    ]
    _reprice_rebalancer(solution, final={"asset-a": Fraction(50), "asset-b": Fraction(50), "asset-c": Fraction(50), "asset-d": Fraction(45)})
    return payload


def _medium_custom_lambda() -> JsonObject:
    payload = _rebalancer_incumbent_result()
    payload["scenario_basis"]["target_fidelity"] = {"kind": "custom", "lambda": "2.5"}
    payload["primary_solution"]["score"]["distance_weight"] = _finite("2.5")
    _reprice_rebalancer(payload["primary_solution"], final={"asset-a": Fraction(50), "asset-b": Fraction(50), "asset-c": Fraction(50), "asset-d": Fraction(45)})
    return payload


@pytest.mark.parametrize("build", [pytest.param(_medium_target_first, id="target-first"), pytest.param(_medium_custom_lambda, id="custom-lambda")])
def test_rebalancer_result_carries_every_fidelity(build: PayloadFactory) -> None:
    """The basis carries the request's fidelity (``lambda`` on the wire for a custom one); «Target first» publishes no ``λ``
    and no ``J`` and its two stages, distance then money lost; a custom ``λ`` scales ``J``."""
    payload = build()
    model, emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
    wire = json.loads(emitted)
    assert wire["scenario_basis"]["target_fidelity"] == payload["scenario_basis"]["target_fidelity"]
    score = wire["primary_solution"]["score"]
    if payload["scenario_basis"]["target_fidelity"]["kind"] == "target_first":
        assert (score["distance_weight"], score["plan_score"]) == (None, None)
        assert [stage["objective_code"] for stage in wire["primary_solution"]["objectives"]["stages"]][:2] == ["target_distance", "wealth_loss"]
    else:
        assert _money_wire_fraction(score["plan_score"]) == Fraction(5, 2) * Fraction(841949, 1000000) + Fraction(143, 100)


def _optimal_with_open_tie_break(status: str) -> JsonObject:
    """The medium plan proven optimal on ``J`` with ``route_priority`` left open: by a limit, or rejected by the exact
    comparison (D4). The witness names the stages that closed."""
    payload = _rebalancer_incumbent_result()
    _find(payload["solver_evidence"]["stages"], "objective_code", "route_priority")["status"] = "unfinished"
    _find(payload["primary_solution"]["score"]["tie_breaks"], "objective_code", "route_priority")["status"] = status
    payload["proof"] = _optimal_proven_proof(["plan_score", "operation_count"], "Rebalancer")
    payload["stop_reason"] = "completed" if status == "rejected" else "time_limit"
    return payload


@pytest.mark.parametrize("status", ["rejected", "unfinished"])
def test_open_named_tie_break_keeps_the_proof_on_the_score(status: str) -> None:
    """D4 (the B2 review of project 67): a named tie-break left open does not downgrade ``optimal_proven``; the witness names
    the closed stages, ``score.tie_breaks`` says how the open one ended, and a rejected one ends a completed search."""
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, _optimal_with_open_tie_break(status))
    wire = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")
    assert wire["proof"]["witness"]["objective_codes"] == ["plan_score", "operation_count"]


OPEN_TIE_BREAK_REJECTION_CASES = (
    pytest.param(lambda: {**_optimal_with_open_tie_break("rejected"), "proof": _optimal_proven_proof(["plan_score", "operation_count", "route_priority"], "Rebalancer")}, "Optimal proof witness must cover every published objective stage in order", id="witness-names-the-open-stage"),
    pytest.param(lambda: {**_optimal_with_open_tie_break("unfinished"), "stop_reason": "completed"}, "Completed stops require no unfinished stage", id="limit-reported-as-completed"),
    pytest.param(lambda: _medium_mutated(_set(("primary_solution", "score", "tie_breaks", ("objective_code", "operation_count"), "status"), "unfinished"))(), "A tie-break is closed exactly when its solver stage finished", id="status-against-the-evidence"),
    pytest.param(lambda: _medium_mutated(_set(("primary_solution", "score", "tie_breaks"), [{"objective_code": "route_priority", "status": "closed"}]))(), "The score's tie-breaks must name the published tie-break stages in order", id="a-tie-break-missing"),
)


@pytest.mark.parametrize(("build", "message"), OPEN_TIE_BREAK_REJECTION_CASES)
def test_open_named_tie_break_is_reported_consistently(build: PayloadFactory, message: str) -> None:
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, build(), message)


def _optimal_with_open_canonical_vector(stop_reason: str) -> JsonObject:
    """The medium plan proven optimal with the canonical vector left open by a limit: it has no evidence row of its own, so
    its entry in ``score.tie_breaks`` is what the stop rule reads."""
    payload = _rebalancer_incumbent_result()
    _find(payload["primary_solution"]["score"]["tie_breaks"], "objective_code", "canonical")["status"] = "unfinished"
    payload["proof"] = _optimal_proven_proof(["plan_score", "operation_count", "route_priority"], "Rebalancer")
    payload["stop_reason"] = stop_reason
    return payload


def test_open_canonical_vector_keeps_the_proof_and_reads_as_a_limit() -> None:
    """The consultant's answer to the B3 checkpoint (2b): the canonical vector is a tie-break like the named ones; left open
    by a limit it keeps ``optimal_proven``, and the stop is that limit, never «completed»."""
    _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, _optimal_with_open_canonical_vector("time_limit"))
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, _optimal_with_open_canonical_vector("completed"), "Completed stops require no unfinished stage")
    missing = _rebalancer_incumbent_result()
    missing["primary_solution"]["score"]["tie_breaks"] = [stage for stage in missing["primary_solution"]["score"]["tie_breaks"] if stage["objective_code"] != "canonical"]
    _reject_because(REBALANCER_PLAN_OUTPUT_ADAPTER, missing, "The score's tie-breaks must name the published tie-break stages in order")


# B4 (project 67, decisioni-REB §11.6): what each service serves is ``plan`` and ``preview``, one request model and one output
# union, so the fingerprint the catalog publishes covers both. It moves for both services here, the PAC's included (accepted:
# 1.4 still serves one contract 2.0.0). The two fingerprints above stay the ``plan`` contract alone (its own result union).
# G5-2 of project 67 moves the Rebalancer's alone: its preview gains the «other cash» item (the PAC's preview has no items).
# Lots SE and ZB of project 67 move both: a closed issue code each; ZB also ``completed`` among a ready_no_incumbent's stops.
# Lot SEEDS of project 67 moves both: two not-proven reasons in the shared NotProvenReasonCode.
# The largest deviation's item (X14, project 67) moves the Rebalancer's alone: two references on its score.
# R1-A (project 67, contract §6.8) moves the PAC's alone: a plan needs a step, not an order (``order_rows`` loses its minimum).
# R1-F (b) (project 67, developer decision of 21/11) moves the Rebalancer's alone: the page computes the table «maximum
# acceptable cost», so the request loses ``custom_reference_amount`` and the preview its ``table`` and ``custom`` for the
# levels' λ (``fidelity_level_weights``).
# TL-5 (project 67) moves both: the plan accounts' cash at the end and by currency, the uninvested row's two parts.
TOOL_SCHEMA_FINGERPRINT_CASES = (
    pytest.param("pac_allocator", PAC_TOOL_INPUT_ADAPTER, PAC_TOOL_OUTPUT_ADAPTER, "dd1709317f7aa5306b7a1421b1072087dd738aa30d76dabd28b2b9bf736f0235", id="pac"),
    pytest.param("portfolio_rebalancer", REBALANCER_TOOL_INPUT_ADAPTER, REBALANCER_TOOL_OUTPUT_ADAPTER, "bc392e62c112e61131381e7558092445c4b955268326912c4cf421f467a36c15", id="rebalancer"),
)


@pytest.mark.parametrize(("tool_code", "input_adapter", "output_adapter", "expected_fingerprint"), TOOL_SCHEMA_FINGERPRINT_CASES)
def test_tool_schema_fingerprints_are_frozen_and_served(tool_code: str, input_adapter: TypeAdapter[Any], output_adapter: TypeAdapter[Any], expected_fingerprint: str) -> None:
    input_schema = generate_tool_schema(input_adapter, "validation")
    output_schema = generate_tool_schema(output_adapter, "serialization")
    assert declared_operations(input_schema) == frozenset({"plan", "preview"})
    fingerprint = schema_fingerprint(input_schema, output_schema, frozenset({"plan", "preview"}))
    assert fingerprint == expected_fingerprint
    assert ToolPluginRegistry.get_definition(tool_code).descriptor.schema_fingerprint == fingerprint


@pytest.mark.parametrize("operation", ["plan", "preview"])
def test_custom_reference_amount_is_gone(operation: str) -> None:
    """R1-F (b) of project 67: the page turns the euros of the «custom» fidelity into λ itself, so no request carries them
    any more; the field is refused as any unknown one, the preview's included."""
    payload = {**_rebalancer_request(), "operation": operation, "custom_reference_amount": {"amount": "60", "currency": "EUR"}}
    _assert_extra_forbidden(REBALANCER_PLAN_INPUT_ADAPTER, payload, "custom_reference_amount")


# ---------------------------------------------------------------------------
# The Rebalancer's exposure on the whole portfolio (developer's decision 4 of 13/11, project 67)
# ---------------------------------------------------------------------------

# The medium plan (F = 200, W = 200 − 1.43 of tax): before on F, target on the items' weights, after on W.
_MEDIUM_F = Fraction(200)
_MEDIUM_W = Fraction(200) - Fraction(143, 100)
_MEDIUM_FINAL_INVESTED = Fraction(80 - 30) + Fraction(20 + 30) + Fraction(40 + 10) + Fraction(10 + 35)
_MEDIUM_ALPHA_CASH = Fraction(50 - 40 + 30 - 35) - Fraction(143, 100)


def _exposure_weights(row: JsonObject) -> tuple[Fraction | None, Fraction, Fraction | None]:
    def available(value: JsonObject) -> Fraction | None:
        return _wire_fraction(value["value"]) if value["kind"] == "available" else None

    return available(row["before_weight"]), _wire_fraction(row["target_weight"]), available(row["final_weight"])


def _wire_fraction(number: JsonObject) -> Fraction:
    if number["kind"] == "finite_decimal":
        return Fraction(Decimal(number["value"]))
    return Fraction(int(number["numerator"]), int(number["denominator"]))


def test_rebalancer_exposure_rows_cover_the_whole_portfolio() -> None:
    """Every dimension of the medium plan has one ``cash`` row, and its three bases each sum to one: before on F (the 50
    EUR contribution is the cash before), the target on the items' weights (cash 5 %), after on W."""
    payload = _rebalancer_incumbent_result()
    REBALANCER_PLAN_OUTPUT_ADAPTER.validate_python(payload)
    rows = payload["primary_solution"]["exposure_rows"]
    for dimension in ("asset_type", "sector", "geography"):
        dimension_rows = [row for row in rows if row["dimension"] == dimension]
        cash_rows = [row for row in dimension_rows if row["kind"] == "cash"]
        assert len(cash_rows) == 1, dimension
        assert "category_id" not in cash_rows[0] and "label" not in cash_rows[0]
        assert _exposure_weights(cash_rows[0]) == (Fraction(50) / _MEDIUM_F, Fraction(1, 20), _MEDIUM_ALPHA_CASH / _MEDIUM_W)
        weights = [_exposure_weights(row) for row in dimension_rows]
        assert [sum(column) for column in zip(*weights, strict=True)] == [1, 1, 1], dimension
    (equity,) = [row for row in rows if row["dimension"] == "asset_type" and row["kind"] == "category"]
    assert _exposure_weights(equity) == (Fraction(150) / _MEDIUM_F, Fraction(19, 20), _MEDIUM_FINAL_INVESTED / _MEDIUM_W)


def _exposure_payload(mutate: Callable[[list[JsonObject]], None]) -> JsonObject:
    payload = _rebalancer_incumbent_result()
    mutate(payload["primary_solution"]["exposure_rows"])
    return payload


def _without_sector_cash(rows: list[JsonObject]) -> None:
    rows.remove(next(row for row in rows if row["dimension"] == "sector" and row["kind"] == "cash"))


def _two_sector_cash_rows(rows: list[JsonObject]) -> None:
    cash = next(row for row in rows if row["dimension"] == "sector" and row["kind"] == "cash")
    rows.append(deepcopy(cash))


def _before_on_the_invested_part(rows: list[JsonObject]) -> None:
    for row in rows:
        if row["dimension"] == "asset_type" and row["kind"] == "category":
            row["before_weight"] = {"kind": "available", "value": {"kind": "finite_decimal", "value": "1"}}


def _target_renormalised(rows: list[JsonObject]) -> None:
    for row in rows:
        if row["dimension"] == "asset_type":
            row["target_weight"] = {"kind": "finite_decimal", "value": "1" if row["kind"] == "category" else "0"}


def _cash_row_with_a_category(rows: list[JsonObject]) -> None:
    cash = next(row for row in rows if row["kind"] == "cash")
    cash["category_id"] = "cash"
    cash["label"] = "Cash"


def _invested_part_reason(rows: list[JsonObject]) -> None:
    rows[0]["final_weight"] = {"kind": "unavailable", "reason": "zero_final_invested"}


def _without_the_sector_dimension(rows: list[JsonObject]) -> None:
    rows[:] = [row for row in rows if row["dimension"] != "sector"]


def _without_any_row(rows: list[JsonObject]) -> None:
    rows.clear()


def _cash_traded_with_a_category(rows: list[JsonObject]) -> None:
    """A tenth of the weight moved from the cash row to a category: every sum still one, the cash off the accounts."""
    cash = next(row for row in rows if row["dimension"] == "asset_type" and row["kind"] == "cash")
    category = next(row for row in rows if row["dimension"] == "asset_type" and row["kind"] == "category")
    cash_before, category_before = (_wire_fraction(row["before_weight"]["value"]) for row in (cash, category))
    cash["before_weight"] = {"kind": "available", "value": _finite(str(Decimal(cash_before.numerator) / cash_before.denominator - Decimal("0.1")))}
    category["before_weight"] = {"kind": "available", "value": _finite(str(Decimal(category_before.numerator) / category_before.denominator + Decimal("0.1")))}


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(_without_sector_cash, id="no-cash-row"),
        pytest.param(_two_sector_cash_rows, id="two-cash-rows"),
        pytest.param(_before_on_the_invested_part, id="before-not-on-F"),
        pytest.param(_target_renormalised, id="target-renormalised-off-the-items"),
        pytest.param(_cash_row_with_a_category, id="cash-row-with-a-category"),
        pytest.param(_invested_part_reason, id="the-pac-unavailable-reason"),
        pytest.param(_without_the_sector_dimension, id="a-dimension-missing"),
        pytest.param(_without_any_row, id="no-exposure-at-all"),
        pytest.param(_cash_traded_with_a_category, id="cash-off-the-accounts"),
    ],
)
def test_rebalancer_exposure_rows_are_refused_off_their_bases(mutate: Callable[[list[JsonObject]], None]) -> None:
    """Exactly one cash row per dimension; before sums to one on F and after on W (a renormalised target no longer closes
    with the cash row); a cash row has no category; the Rebalancer's unavailable reasons are its own."""
    with pytest.raises(ValidationError):
        REBALANCER_PLAN_OUTPUT_ADAPTER.validate_python(_exposure_payload(mutate))


def test_rebalancer_exposure_weights_have_their_own_unavailable_reasons() -> None:
    """At zero wealth a Rebalancer weight is unavailable with its own reason: before at a zero F, after at a zero W."""
    for reason in ("zero_initial_wealth", "zero_final_wealth"):
        unavailable = {"kind": "unavailable", "reason": reason}
        row = RebalancerExposureCashRow.model_validate({"kind": "cash", "dimension": "sector", "before_weight": unavailable, "target_weight": {"kind": "finite_decimal", "value": "0"}, "final_weight": unavailable, "provenance_ids": []})
        assert row.before_weight.reason == reason


def test_rebalancer_exposure_weights_at_a_zero_base() -> None:
    """At a zero base every weight is unavailable for that base's own reason: an available weight, or the other reason,
    is refused; on a positive base the weights are available and sum to one."""
    validate = _validate_rebalancer_weights
    initial = RebalancerUnavailableWeight(kind="unavailable", reason="zero_initial_wealth")
    final = RebalancerUnavailableWeight(kind="unavailable", reason="zero_final_wealth")
    half = AvailableExactNumber.model_validate({"kind": "available", "value": {"kind": "finite_decimal", "value": "0.5"}})
    validate([initial, initial], Fraction(0), "zero_initial_wealth", "before")
    for refused in ([initial, half], [final, final]):
        with pytest.raises(ValueError):
            validate(refused, Fraction(0), "zero_initial_wealth", "before")
    validate([half, half], Fraction(10), "zero_initial_wealth", "before")
    with pytest.raises(ValueError):
        validate([half, initial], Fraction(10), "zero_initial_wealth", "before")


# ---------------------------------------------------------------------------- lot MG of project 67: the proof's margin

_BROWSER_RESULT = Path(__file__).resolve().parents[3] / "frontend/src/lib/features/tools/pac-allocator/planner/result/__fixtures__/rebalancer-browser.json"


def _not_proven_browser(margin: dict | None) -> dict:
    """The engine's G5 answer (a proven plan) made not proven, with ``margin`` on its proof."""
    result = json.loads(_BROWSER_RESULT.read_text())["result"]
    result["proof"] = {"kind": "not_proven", "reason_code": "allocation.proof_not_confirmed", "margin": margin}
    return result


def test_a_plan_not_proven_carries_its_margin_in_the_valuation_currency() -> None:
    """Lot MG: «ottimo locale (entro X)». A positive amount in the valuation currency, beside a published plan; none for a
    plan of the wide model, never zero, never in another currency, never without a plan."""
    REBALANCER_TOOL_OUTPUT_ADAPTER.validate_python(_not_proven_browser({"amount": "0.14", "currency": "EUR"}))
    REBALANCER_TOOL_OUTPUT_ADAPTER.validate_python(_not_proven_browser(None))
    with pytest.raises(ValidationError, match="valuation currency"):
        REBALANCER_TOOL_OUTPUT_ADAPTER.validate_python(_not_proven_browser({"amount": "0.14", "currency": "USD"}))
    with pytest.raises(ValidationError):
        REBALANCER_TOOL_OUTPUT_ADAPTER.validate_python(_not_proven_browser({"amount": "0", "currency": "EUR"}))
    with pytest.raises(ValidationError, match="wide model"):
        NotProvenProof.model_validate({"kind": "not_proven", "reason_code": "allocation.limits_leave_no_rounding_room", "margin": {"amount": "0.01", "currency": "EUR"}})


def test_a_result_without_a_plan_carries_no_margin() -> None:
    """A run with no time (T4, 0 s) ends with no plan: a margin there is refused."""
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415
    from backend.test_scripts.test_services import _reb_small_cases as cases  # noqa: PLC0415

    result = planner.plan_exact_scenario(cases.t4(), solver_time_budget_seconds=0.0).result
    assert result.result_state == "ready_no_incumbent", "PREMISE: no plan in no time"
    data = json.loads(REBALANCER_TOOL_OUTPUT_ADAPTER.dump_json(result))
    data["proof"]["margin"] = {"amount": "0.01", "currency": "EUR"}
    with pytest.raises(ValidationError, match="published plan"):
        REBALANCER_TOOL_OUTPUT_ADAPTER.validate_python(data)


def test_the_pac_never_carries_a_margin() -> None:
    """Lot MG, the consultant's ruling of 17/11: the PAC is one search, one bound, never the second a margin needs. Its
    contract refuses one, even beside a published plan in the valuation currency."""
    result = _pac_no_op_result()
    currency = result["scenario_basis"]["valuation_currency"]
    PAC_PLAN_OUTPUT_ADAPTER.validate_python(result)
    result["proof"]["margin"] = {"amount": "0.01", "currency": currency}
    with pytest.raises(ValidationError, match="PAC"):
        PAC_PLAN_OUTPUT_ADAPTER.validate_python(result)
