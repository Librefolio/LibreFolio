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
from fractions import Fraction
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from backend.app.schemas import pac_allocator as pac_schemas
from backend.app.schemas.pac_allocator import (
    PAC_PLAN_INPUT_ADAPTER,
    PAC_PLAN_OUTPUT_ADAPTER,
    REBALANCER_PLAN_INPUT_ADAPTER,
    REBALANCER_PLAN_OUTPUT_ADAPTER,
    ExactNumber,
    ObjectiveStageResult,
    PacPlannerInvalidResult,
    PacPlannerNeedsInputResult,
    PacPlannerReadyIncumbentResult,
    PacPlannerReadyInfeasibleResult,
    PacPlannerReadyNoIncumbentResult,
    PacPlannerReadyNoOpResult,
    PacPlannerRequest,
    PacPlannerUnsupportedResult,
    PlannerBrokerIdentity,
    PlannerFixedDecimal,
    PlannerIssue,
    RebalancerInvestAndSellRequest,
    RebalancerInvestOnlyRequest,
    RebalancerPlannerInvalidResult,
    RebalancerPlannerNeedsInputResult,
    RebalancerPlannerReadyIncumbentResult,
    RebalancerPlannerReadyInfeasibleResult,
    RebalancerPlannerReadyNoIncumbentResult,
    RebalancerPlannerReadyNoOpResult,
    RebalancerPlannerUnsupportedResult,
    SolverStageEvidence,
    ValuationMoneyUnit,
)
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


def _pac_request() -> JsonObject:
    return _fixture("pac_plan_request.min.v2.json")


def _rebalancer_invest_and_sell_request() -> JsonObject:
    return _fixture("rebalancer_plan_request.medium.v2.json")


def _rebalancer_invest_only_request() -> JsonObject:
    payload = _rebalancer_invest_and_sell_request()
    payload["policy"] = "invest_only"
    payload.pop("sell_context")
    payload["order_routes"] = [row for row in payload["order_routes"] if row["side"] == "buy"]
    return payload


def _pac_no_op_result() -> JsonObject:
    return _fixture("pac_plan_result.min.v2.json")


def _rebalancer_incumbent_result() -> JsonObject:
    return _fixture("rebalancer_plan_result.medium.v2.json")


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
    order["fx_cost"] = _money("0")
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
            "rounding_delta": "0",
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
    payload["issues"] = []
    payload["deployment"] = {"kind": "coincident", "reason_code": "allocation.primary_is_deployment"}
    return payload


def _rebalancer_no_op_result() -> JsonObject:
    payload = _rebalancer_incumbent_result()
    payload["result_state"] = "ready_no_op"
    payload["outcome"] = "no_op"

    solution = payload["primary_solution"]
    solution["solution_id"] = "rebalancer-primary-no-op"
    solution["funding_actions"] = []
    solution["fx_actions"] = []
    solution["order_rows"] = []
    solution["sell_irreducibility"] = []

    residuals = {
        "asset-a": "30",
        "asset-b": "-30",
        "asset-c": "-10",
        "asset-d": "-40",
    }
    for asset in solution["asset_rows"]:
        asset["final_value"] = deepcopy(asset["before_value"])
        asset["residual"] = _money(residuals[asset["asset_id"]])
        asset["final_weight"] = deepcopy(asset["before_weight"])
        asset["buy_mid_value"] = _money("0")
        asset["sell_mid_value"] = _money("0")
    for exposure in solution["exposure_rows"]:
        exposure["final_weight"] = deepcopy(exposure["before_weight"])

    accounting = solution["accounting"]
    for field, value in {
        "current_invested": "150",
        "selected_funding": "50",
        "reachable_funding": "50",
        "trapped_funding": "0",
        "fixed_reference": "200",
        "final_invested": "150",
        "shortfall": "50",
        "free_cash": "50",
        "physical_reserves": "0",
        "economic_losses": "0",
        "rounding_delta": "0",
        "rounding_bound": "0.02",
        "identity_delta": "0",
    }.items():
        accounting[field] = _money(value)
    for cost_field in solution["costs"]:
        solution["costs"][cost_field] = _money("0")

    for ledger in solution["ledger_rows"]:
        for field in (
            "funding_in",
            "funding_out",
            "fx_debit",
            "fx_credit",
            "buy_debit",
            "gross_sell_credit",
            "buy_fees",
            "sell_fees",
            "broker_withheld_tax",
            "self_reserved_tax",
            "rounding_delta",
        ):
            ledger[field] = "0"
        ledger["final_spendable"] = ledger["initial_selected"]
        ledger["final_physical"] = ledger["initial_selected"]

    for objective_code, value in {
        "fixed_l2": "3500",
        "shortfall": "50",
        "turnover": "0",
        "explicit_cost": "0",
        "active_order_rows": "0",
    }.items():
        _find(solution["objectives"]["stages"], "objective_code", objective_code)["value"] = _finite(value)
    solution["objectives"]["tie_break"]["ordered_keys"] = []
    payload["deployment"] = {"kind": "coincident", "reason_code": "allocation.no_actions_selected"}
    return payload


def _rebalancer_no_op_with_zero_asset_result() -> JsonObject:
    payload = _rebalancer_no_op_result()
    solution = payload["primary_solution"]
    asset_a = _find(solution["asset_rows"], "asset_id", "asset-a")
    asset_b = _find(solution["asset_rows"], "asset_id", "asset-b")

    asset_a["before_value"] = _money("100")
    asset_a["final_value"] = _money("100")
    asset_a["residual"] = _money("50")
    asset_a["before_weight"] = _available_ratio("2", "3", "0.666667")
    asset_a["final_weight"] = deepcopy(asset_a["before_weight"])

    asset_b["before_value"] = _money("0")
    asset_b["final_value"] = _money("0")
    asset_b["residual"] = _money("-50")
    asset_b["before_weight"] = _available("0")
    asset_b["final_weight"] = deepcopy(asset_b["before_weight"])
    _find(solution["objectives"]["stages"], "objective_code", "fixed_l2")["value"] = _finite("6700")
    return payload


def _ready_infeasible_result(product: str) -> JsonObject:
    payload = _pac_no_op_result() if product == "PAC" else _rebalancer_incumbent_result()
    payload["result_state"] = "ready_infeasible"
    payload["outcome"] = "infeasible_proven"
    payload.pop("primary_solution")
    payload.pop("deployment")
    payload["proof"] = {
        "kind": "infeasibility_proven",
        "proof_source": "exhaustive_oracle",
        "witness": {
            "kind": "exhaustive_oracle",
            "enumerated_candidates": 1,
            "feasible_candidates": 0,
            "objective_codes": ["fixed_l2"],
        },
    }
    return payload


def _ready_no_incumbent_result(product: str) -> JsonObject:
    payload = _pac_no_op_result() if product == "PAC" else _rebalancer_incumbent_result()
    payload["result_state"] = "ready_no_incumbent"
    payload["outcome"] = "no_incumbent"
    payload.pop("primary_solution")
    payload.pop("deployment")
    payload["proof"] = {"kind": "not_proven", "reason_code": "allocation.exact_proof_not_established"}
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


def _optimal_proven_proof(proof_source: str, objective_codes: list[str]) -> JsonObject:
    if proof_source == "exhaustive_oracle":
        witness = {
            "kind": "exhaustive_oracle",
            "enumerated_candidates": 1,
            "feasible_candidates": 1,
            "objective_codes": objective_codes,
        }
    elif proof_source == "score_lattice_closure":
        witness = {
            "kind": "score_lattice_closure",
            "objective_codes": objective_codes,
            "closed_stage_count": len(objective_codes),
        }
    else:
        raise AssertionError(f"unhandled optimal proof source {proof_source!r}")
    return {
        "kind": "optimal_proven",
        "proof_source": proof_source,
        "witness": witness,
        "tie_break_closed": True,
    }


def _gap_bounded_pac_result() -> JsonObject:
    payload = _pac_no_op_result()
    payload["stop_reason"] = "time_limit"
    stage = _reported_solver_stage()
    payload["solver_evidence"] = {"kind": "reported_floating", "stages": [stage]}
    payload["proof"] = {
        "kind": "gap_bounded",
        "stage_bounds": [
            {
                "stage": stage["stage"],
                "objective_code": stage["objective_code"],
                "ordinal": stage["ordinal"],
                "scope": stage["scope"],
                "sense": stage["sense"],
                "unit": deepcopy(stage["unit"]),
                "primal": stage["primal"],
                "dual": stage["dual"],
                "absolute_gap": stage["absolute_gap"],
                "relative_gap": stage["relative_gap"],
            }
        ],
    }
    return payload


def _gap_bounded_pac_result_for_sense(sense: str, primal: str, exact_value: str, dual: str) -> JsonObject:
    payload = _gap_bounded_pac_result()
    objective = _find(payload["primary_solution"]["objectives"]["stages"], "objective_code", "fixed_l2")
    solver_stage = _find(payload["solver_evidence"]["stages"], "objective_code", "fixed_l2")
    bound = _find(payload["proof"]["stage_bounds"], "objective_code", "fixed_l2")
    absolute_gap = Fraction(primal) - Fraction(dual)

    objective["sense"] = sense
    objective["value"] = _finite(exact_value)
    for stage in (solver_stage, bound):
        stage["sense"] = sense
        stage["primal"] = primal
        stage["dual"] = dual
        stage["absolute_gap"] = str(abs(absolute_gap))
        stage["relative_gap"] = "0"
    return payload


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
        assert difference.denominator == 1
        deltas.append(
            {
                "objective_code": primary_stage["objective_code"],
                "ordinal": primary_stage["ordinal"],
                "sense": primary_stage["sense"],
                "unit": deepcopy(primary_stage["unit"]),
                "primary_value": deepcopy(primary_stage["value"]),
                "deployment_value": deepcopy(deployment_stage["value"]),
                "delta": _finite(str(difference.numerator)),
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
    pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, RebalancerInvestOnlyRequest, _rebalancer_invest_only_request, id="rebalancer-invest-only"),
    pytest.param(REBALANCER_PLAN_INPUT_ADAPTER, RebalancerInvestAndSellRequest, _rebalancer_invest_and_sell_request, id="rebalancer-invest-and-sell"),
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
    pytest.param("pac_plan_request.min.v2.json", PAC_PLAN_INPUT_ADAPTER, PLANNER_PARAMETER_BYTES, False, id="pac-request-min"),
    pytest.param("pac_plan_result.min.v2.json", PAC_PLAN_OUTPUT_ADAPTER, PLANNER_RESULT_BYTES, False, id="pac-result-min"),
    pytest.param("pac_plan_request.candidate-max.v2.json", PAC_PLAN_INPUT_ADAPTER, PLANNER_PARAMETER_BYTES, True, id="pac-request-candidate"),
    pytest.param("pac_plan_result.candidate-max.v2.json", PAC_PLAN_OUTPUT_ADAPTER, PLANNER_RESULT_BYTES, True, id="pac-result-candidate"),
    pytest.param("rebalancer_plan_request.medium.v2.json", REBALANCER_PLAN_INPUT_ADAPTER, PLANNER_PARAMETER_BYTES, False, id="rebalancer-request-medium"),
    pytest.param("rebalancer_plan_result.medium.v2.json", REBALANCER_PLAN_OUTPUT_ADAPTER, PLANNER_RESULT_BYTES, False, id="rebalancer-result-medium"),
)


@pytest.mark.parametrize("adapter,model_type,factory", REQUEST_CASES)
def test_all_three_request_roots_strict_roundtrip_and_reject_impossible_shapes(
    adapter: TypeAdapter[Any],
    model_type: type[BaseModel],
    factory: PayloadFactory,
) -> None:
    payload = factory()
    model, _emitted = _strict_roundtrip(adapter, payload)

    assert type(model) is model_type
    assert all(field.is_required() for field in model_type.model_fields.values())

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
        missing.pop(field_name)
        _reject(adapter, missing)


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
    if name == "rebalancer_plan_result.medium.v2.json":
        blocking_codes = {code for evidence in wire["primary_solution"]["sell_irreducibility"] for check in evidence["checks"] for code in check["blocking_issue_codes"]}
        assert blocking_codes == {"portfolio_rebalancer.sell_irreducibility_unresolved"}
        assert blocking_codes <= set(EXPECTED_PLANNER_ISSUE_CODES)


FIXED_DECIMAL_ADAPTER = TypeAdapter(PlannerFixedDecimal)
INTEGER_TEXT_ADAPTER = TypeAdapter(pac_schemas.PlannerIntegerText)
WHOLE_QUANTITY_STEP_ADAPTER = TypeAdapter(pac_schemas.PlannerWholeQuantityStep)
POSITIVE_WHOLE_DECIMAL_ADAPTER = TypeAdapter(pac_schemas.PlannerPositiveWholeDecimal)

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

    capability_schema = TypeAdapter(pac_schemas.WholeQuantityCapability).json_schema()
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
    payload = _rebalancer_invest_and_sell_request()
    broker = _find(payload["brokers"], "broker_id", "broker-alpha")
    capability = _find(broker["capabilities"], "capability_id", "cap-alpha-eur-whole")
    assert capability["kind"] == "whole_quantity"
    capability["quantity_step"] = quantity_step

    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_INPUT_ADAPTER, payload)
    wire = REBALANCER_PLAN_INPUT_ADAPTER.dump_python(model, mode="json")
    emitted_broker = _find(wire["brokers"], "broker_id", "broker-alpha")
    emitted_capability = _find(emitted_broker["capabilities"], "capability_id", "cap-alpha-eur-whole")

    assert emitted_capability["quantity_step"] == quantity_step
    assert "allocation.nonpositive_quantity_step" in get_args(pac_schemas.PlannerIssueCode)


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
    payload = _fixture("pac_plan_request.candidate-max.v2.json")
    model, _emitted = _strict_roundtrip(PAC_PLAN_INPUT_ADAPTER, payload)
    wire = PAC_PLAN_INPUT_ADAPTER.dump_python(model, mode="json")

    euro = _find(wire["currency_specs"], "currency", "EUR")
    asset = _find(wire["assets"], "asset_id", "asset-01")
    broker = _find(wire["brokers"], "broker_id", "broker-eur")
    cash = _find(wire["existing_cash"], "cash_id", "cash-eur")
    route = _find(wire["order_routes"], "route_id", "route-01-eur")
    target = _find(wire["target_weights"], "asset_id", "asset-01")

    assert euro["minor_unit"] == "0"
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
PLANNER_ISSUE_CODE_ADAPTER = TypeAdapter(pac_schemas.PlannerIssueCode)

EXPECTED_PLANNER_ISSUE_CODES = (
    "allocation.asset_inactive_not_buyable",
    "allocation.asset_type_missing",
    "allocation.broker_execution_profile_unsupported",
    "allocation.broker_inactive",
    "allocation.capacity_unsupported",
    "allocation.cash_selection_invalid",
    "allocation.classification_geography_missing",
    "allocation.classification_invalid",
    "allocation.classification_sector_missing",
    "allocation.coefficient_envelope_unsupported",
    "allocation.currency_minor_unit_nonpositive",
    "allocation.currency_mismatch",
    "allocation.currency_spec_missing",
    "allocation.deployment_omitted",
    "allocation.duplicate_id",
    "allocation.dynamic_fee_unsupported",
    "allocation.economic_share_out_of_range",
    "allocation.execution_margin_missing",
    "allocation.execution_margin_rate_out_of_range",
    "allocation.exposure_weight_out_of_range",
    "allocation.fee_floor_exceeds_cap",
    "allocation.fee_rate_out_of_range",
    "allocation.fee_schedule_missing",
    "allocation.fiscal_currency_missing",
    "allocation.funding_cap_negative",
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
    "allocation.price_date_missing",
    "allocation.price_missing",
    "allocation.price_order_invalid",
    "allocation.provenance_not_found",
    "allocation.provenance_stale_confirmed",
    "allocation.quote_base_quantity_missing",
    "allocation.reference_not_found",
    "allocation.required_buy_sell_conflict",
    "allocation.required_min_notional_unfunded",
    "allocation.route_priority_negative",
    "allocation.saved_fx_invalid",
    "allocation.solver_limit_no_incumbent",
    "allocation.stale_age_negative",
    "allocation.stale_observation_not_accepted",
    "allocation.target_total_not_one",
    "allocation.target_weight_missing",
    "allocation.target_weight_out_of_range",
    "allocation.tax_netting_unsupported",
    "allocation.valuation_currency_missing",
    "allocation.wac_missing",
    "allocation.zero_selected_funding",
    "pac_allocator.initial_holding_forbidden",
    "pac_allocator.sell_forbidden",
    "portfolio_rebalancer.baseline_incumbent_missing",
    "portfolio_rebalancer.carried_loss_negative",
    "portfolio_rebalancer.cost_basis_negative",
    "portfolio_rebalancer.holdings_missing",
    "portfolio_rebalancer.nonpositive_current_portfolio",
    "portfolio_rebalancer.sell_fee_missing",
    "portfolio_rebalancer.sell_inventory_exceeded",
    "portfolio_rebalancer.sell_irreducibility_unresolved",
    "portfolio_rebalancer.sell_to_idle_forbidden",
    "portfolio_rebalancer.tax_rate_missing",
    "portfolio_rebalancer.tax_rate_out_of_range",
    "portfolio_rebalancer.withholding_missing",
)

SUPERSEDED_PLANNER_ISSUE_CODES = (
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
    assert len(EXPECTED_PLANNER_ISSUE_CODES) == 80
    assert EXPECTED_PLANNER_ISSUE_CODES == tuple(sorted(EXPECTED_PLANNER_ISSUE_CODES))
    assert get_args(pac_schemas.PlannerIssueCode) == EXPECTED_PLANNER_ISSUE_CODES
    assert PLANNER_ISSUE_CODE_ADAPTER.json_schema()["enum"] == list(EXPECTED_PLANNER_ISSUE_CODES)


@pytest.mark.parametrize("code", EXPECTED_PLANNER_ISSUE_CODES)
def test_every_closed_planner_issue_code_strictly_roundtrips_with_typed_path(code: str) -> None:
    issue = _catalogue_issue_specimen(code)
    model, _emitted = _strict_roundtrip(PLANNER_ISSUE_ADAPTER, issue)
    assert PLANNER_ISSUE_ADAPTER.dump_python(model, mode="json") == issue


def test_well_shaped_future_planner_issue_code_is_rejected() -> None:
    _reject(PLANNER_ISSUE_ADAPTER, _catalogue_issue_specimen("allocation.future_code"))


@pytest.mark.parametrize("code", SUPERSEDED_PLANNER_ISSUE_CODES)
def test_superseded_planner_issue_code_aliases_are_rejected(code: str) -> None:
    _reject(PLANNER_ISSUE_ADAPTER, _catalogue_issue_specimen(code))


NON_ISSUE_REASON_CATALOGUE_CASES = (
    pytest.param(
        "FundingActionReasonCode",
        ("allocation.fund_declared_orders",),
        ((pac_schemas.PlannerFundingAction, "reason_code"),),
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
            (pac_schemas.DeploymentUnavailable, "reason_code"),
            (pac_schemas.DeploymentCoincident, "reason_code"),
        ),
        id="deployment",
    ),
    pytest.param(
        "NotProvenReasonCode",
        (
            "allocation.exact_proof_not_established",
            "portfolio_rebalancer.sell_irreducibility_unresolved",
        ),
        ((pac_schemas.NotProvenProof, "reason_code"),),
        id="not-proven",
    ),
    pytest.param(
        "SolverNotRunReasonCode",
        ("allocation.solver_not_required",),
        ((pac_schemas.SolverNotRunEvidence, "reason"),),
        id="solver-not-run",
    ),
)

REASON_ONLY_CODES = (
    "allocation.fund_declared_orders",
    "allocation.no_actions_selected",
    "allocation.primary_is_deployment",
    "allocation.exact_proof_not_established",
    "allocation.solver_not_required",
)


@pytest.mark.parametrize(("type_name", "expected_codes", "bound_fields"), NON_ISSUE_REASON_CATALOGUE_CASES)
def test_non_issue_reason_catalogues_are_closed_and_bound_to_their_fields(
    type_name: str,
    expected_codes: tuple[str, ...],
    bound_fields: tuple[tuple[type[BaseModel], str], ...],
) -> None:
    reason_type = getattr(pac_schemas, type_name, None)
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
    adapter = TypeAdapter(pac_schemas.NotProvenReasonCode)
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
    request = _rebalancer_invest_only_request()
    broker = _find(request["brokers"], "broker_id", "broker-alpha")
    broker["identity"] = _inactive_domain_broker_identity()
    broker["capabilities"] = []
    broker["fee_schedules"] = []
    request["funding_routes"] = [route for route in request["funding_routes"] if route["broker_id"] != "broker-alpha"]
    request["order_routes"] = [route for route in request["order_routes"] if route["broker_id"] != "broker-alpha"]

    parsed_request, _request_wire = _strict_roundtrip(REBALANCER_PLAN_INPUT_ADAPTER, request)
    wire_request = REBALANCER_PLAN_INPUT_ADAPTER.dump_python(parsed_request, mode="json")
    inactive_broker = _find(wire_request["brokers"], "broker_id", "broker-alpha")
    assert inactive_broker["identity"]["active"] is False
    assert inactive_broker["capabilities"] == []
    assert any(holding["broker_id"] == "broker-alpha" for holding in wire_request["holdings"])
    assert not any(route["broker_id"] == "broker-alpha" for route in wire_request["funding_routes"])
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
    assert wire_result["primary_solution"]["fx_actions"] == []
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


CURRENCY_MINOR_UNIT_ISSUE_PATH = _planner_field_path("input", "currency", "EUR", "minor_unit")
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
    _normalizer_issue_case("allocation.currency_minor_unit_nonpositive", "invalid", CURRENCY_MINOR_UNIT_ISSUE_PATH),
    _normalizer_issue_case("allocation.nonpositive_price", "invalid", PRICE_AMOUNT_ISSUE_PATH),
    _normalizer_issue_case("allocation.invalid_quote_basis", "invalid", QUOTE_BASIS_ISSUE_PATH),
    _normalizer_issue_case("allocation.exposure_weight_out_of_range", "invalid", EXPOSURE_WEIGHT_ISSUE_PATH),
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
    _normalizer_issue_case("allocation.stale_age_negative", "invalid"),
    _normalizer_issue_case("allocation.stale_observation_not_accepted", "invalid"),
    _normalizer_issue_case("portfolio_rebalancer.tax_rate_missing", "needs_input", TAX_RATE_ISSUE_PATH),
    _normalizer_issue_case("portfolio_rebalancer.tax_rate_out_of_range", "invalid", TAX_RATE_ISSUE_PATH),
    _normalizer_issue_case("allocation.fiscal_currency_missing", "needs_input"),
    _normalizer_issue_case("allocation.wac_missing", "needs_input"),
    _normalizer_issue_case("allocation.fx_rate_missing", "needs_input", FX_RATE_ISSUE_PATH),
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


@pytest.mark.parametrize("policy", ("proportional", "min_fragmentation"))
def test_pac_policy_accepts_only_its_two_named_literals(policy: str) -> None:
    payload = _pac_request()
    payload["policy"] = policy
    model, _emitted = _strict_roundtrip(PAC_PLAN_INPUT_ADAPTER, payload)
    assert PAC_PLAN_INPUT_ADAPTER.dump_python(model, mode="json")["policy"] == policy


def test_pac_request_excludes_holdings_sell_context_and_sell_routes() -> None:
    assert "holdings" not in PacPlannerRequest.model_fields
    assert "sell_context" not in PacPlannerRequest.model_fields
    pac = _pac_request()
    rebalancer = _rebalancer_invest_and_sell_request()

    for field in ("holdings", "sell_context"):
        impossible = deepcopy(pac)
        impossible[field] = deepcopy(rebalancer[field])
        _reject(PAC_PLAN_INPUT_ADAPTER, impossible)

    sell_route = _find(rebalancer["order_routes"], "route_id", "route-a-alpha-sell")
    impossible = deepcopy(pac)
    impossible["order_routes"].append(deepcopy(sell_route))
    _reject(PAC_PLAN_INPUT_ADAPTER, impossible)


def test_rebalancer_invest_only_excludes_sell_context_and_sell_routes() -> None:
    assert "sell_context" not in RebalancerInvestOnlyRequest.model_fields
    invest_only = _rebalancer_invest_only_request()
    _strict_roundtrip(REBALANCER_PLAN_INPUT_ADAPTER, invest_only)
    sell_source = _rebalancer_invest_and_sell_request()

    with_context = deepcopy(invest_only)
    with_context["sell_context"] = deepcopy(sell_source["sell_context"])
    _reject(REBALANCER_PLAN_INPUT_ADAPTER, with_context)

    with_sell_route = deepcopy(invest_only)
    with_sell_route["order_routes"].append(deepcopy(_find(sell_source["order_routes"], "route_id", "route-a-alpha-sell")))
    _reject(REBALANCER_PLAN_INPUT_ADAPTER, with_sell_route)


def test_rebalancer_invest_and_sell_requires_sell_context_and_at_least_one_sell_route() -> None:
    assert RebalancerInvestAndSellRequest.model_fields["sell_context"].is_required()
    request = _rebalancer_invest_and_sell_request()
    _strict_roundtrip(REBALANCER_PLAN_INPUT_ADAPTER, request)

    for removed_route_id, remaining_route_id in (
        ("route-a-alpha-sell", "route-b-beta-sell"),
        ("route-b-beta-sell", "route-a-alpha-sell"),
    ):
        with_one_sell = deepcopy(request)
        with_one_sell["order_routes"] = [row for row in with_one_sell["order_routes"] if row["route_id"] != removed_route_id]
        assert _find(with_one_sell["order_routes"], "route_id", remaining_route_id)["side"] == "sell"
        _strict_roundtrip(REBALANCER_PLAN_INPUT_ADAPTER, with_one_sell)

    without_context = deepcopy(request)
    without_context.pop("sell_context")
    _reject(REBALANCER_PLAN_INPUT_ADAPTER, without_context)

    buy_only = deepcopy(request)
    buy_only["order_routes"] = [row for row in buy_only["order_routes"] if row["side"] == "buy"]
    assert buy_only["order_routes"]
    assert not any(row["side"] == "sell" for row in buy_only["order_routes"])
    _reject(REBALANCER_PLAN_INPUT_ADAPTER, buy_only)


MEDIUM_SELL_ROUTE_CASES = (
    pytest.param("route-a-alpha-sell", "whole_quantity", id="whole-quantity"),
    pytest.param("route-b-beta-sell", "monetary_amount", id="monetary-amount"),
)


@pytest.mark.parametrize(("route_id", "capability_kind"), MEDIUM_SELL_ROUTE_CASES)
def test_medium_fixture_sell_routes_strict_roundtrip_without_gross_amount_requested(
    route_id: str,
    capability_kind: str,
) -> None:
    payload = _rebalancer_invest_and_sell_request()
    route = _find(payload["order_routes"], "route_id", route_id)
    broker = _find(payload["brokers"], "broker_id", route["broker_id"])
    capability = _find(broker["capabilities"], "capability_id", route["capability_id"])

    assert route["side"] == "sell"
    assert route["minimum_if_active"]["kind"] == capability_kind
    assert capability["kind"] == capability_kind
    assert "gross_amount_requested" not in route

    adapter = TypeAdapter(pac_schemas.PlannerSellOrderRouteInput)
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
        _rebalancer_invest_only_request,
        "route-b-beta-buy",
        id="rebalancer-invest-only",
    ),
    pytest.param(
        REBALANCER_PLAN_INPUT_ADAPTER,
        _rebalancer_invest_and_sell_request,
        "route-a-alpha-sell",
        id="rebalancer-invest-and-sell",
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
def test_rebalancer_ready_sell_orders_and_irreducibility_are_forbidden_only_for_invest_only(
    factory: PayloadFactory,
    sell_location: str,
    policy: str,
    accepted: bool,
) -> None:
    payload = factory()
    payload["scenario_basis"]["policy"] = policy
    solution = payload["primary_solution"] if sell_location == "primary_solution" else payload["deployment"]["solution"]
    assert any(row["kind"] == "sell" for row in solution["order_rows"])
    assert solution["sell_irreducibility"]

    if accepted:
        model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
        assert REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")["scenario_basis"]["policy"] == "invest_and_sell"
    else:
        _reject(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)


EXACT_NUMBER_ADAPTER = TypeAdapter(ExactNumber)
OBJECTIVE_STAGE_ADAPTER = TypeAdapter(ObjectiveStageResult)
SOLVER_STAGE_ADAPTER = TypeAdapter(SolverStageEvidence)

VALUATION_OBJECTIVE_CASES = (
    pytest.param("fixed_l2", {"kind": "valuation_money_squared", "currency_code": "EUR"}, id="fixed-l2"),
    pytest.param("turnover", {"kind": "valuation_money", "currency_code": "EUR"}, id="turnover"),
    pytest.param("explicit_cost", {"kind": "valuation_money", "currency_code": "EUR"}, id="explicit-cost"),
    pytest.param("incremental_cost", {"kind": "valuation_money", "currency_code": "EUR"}, id="incremental-cost"),
)

DISCRETE_OBJECTIVE_CASES = (
    pytest.param("split_asset_count", {"kind": "count"}, id="split-asset-count"),
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


@pytest.mark.parametrize("proof_kind", ("not_proven", "gap_bounded"))
def test_ready_result_non_optimal_proof_matrix_remains_typed(proof_kind: str) -> None:
    if proof_kind == "gap_bounded":
        payload = _gap_bounded_pac_result()
    else:
        payload = _pac_no_op_result()
    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")
    expected_kind = "gap_bounded" if proof_kind == "gap_bounded" else "not_proven"
    assert wire["proof"]["kind"] == expected_kind


def test_objective_sense_schema_explicitly_preserves_min_and_max() -> None:
    expected = ("min", "max")
    assert get_args(pac_schemas.ObjectiveSense) == expected
    assert TypeAdapter(pac_schemas.ObjectiveSense).json_schema()["enum"] == list(expected)
    for model_type in (ObjectiveStageResult, SolverStageEvidence, pac_schemas.BoundedObjectiveStage):
        assert get_args(model_type.model_fields["sense"].annotation) == expected


GAP_BOUND_SENSE_CASES = (
    pytest.param("min", "26", "25.000", "24", True, id="min-interior"),
    pytest.param("min", "26", "24", "24", True, id="min-dual-boundary"),
    pytest.param("min", "26", "26", "24", True, id="min-primal-boundary"),
    pytest.param("min", "26", "27", "24", False, id="min-above-primal"),
    pytest.param("min", "26", "23", "24", False, id="min-below-dual"),
    pytest.param("min", "24", "25", "26", False, id="min-contradictory-order"),
    pytest.param("max", "24", "25.000", "26", True, id="max-interior"),
    pytest.param("max", "24", "24", "26", True, id="max-primal-boundary"),
    pytest.param("max", "24", "26", "26", True, id="max-dual-boundary"),
    pytest.param("max", "24", "27", "26", False, id="max-above-dual"),
    pytest.param("max", "24", "23", "26", False, id="max-below-primal"),
    pytest.param("max", "26", "25", "24", False, id="max-contradictory-order"),
)


@pytest.mark.parametrize(("sense", "primal", "exact_value", "dual", "accepted"), GAP_BOUND_SENSE_CASES)
def test_gap_proof_bounds_contain_exact_objective_according_to_sense(
    sense: str,
    primal: str,
    exact_value: str,
    dual: str,
    accepted: bool,
) -> None:
    payload = _gap_bounded_pac_result_for_sense(sense, primal, exact_value, dual)
    if not accepted:
        _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)
        return

    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")
    objective = _find(wire["primary_solution"]["objectives"]["stages"], "objective_code", "fixed_l2")
    solver_stage = _find(wire["solver_evidence"]["stages"], "objective_code", "fixed_l2")
    bound = _find(wire["proof"]["stage_bounds"], "objective_code", "fixed_l2")
    exact = _exact_wire_fraction(objective["value"])

    assert (bound["stage"], bound["scope"], bound["unit"]) == (solver_stage["stage"], solver_stage["scope"], solver_stage["unit"])
    assert all(isinstance(bound[field], str) and isinstance(solver_stage[field], str) for field in ("primal", "dual", "absolute_gap", "relative_gap"))
    if sense == "min":
        assert Fraction(dual) <= exact <= Fraction(primal)
    else:
        assert Fraction(primal) <= exact <= Fraction(dual)


@pytest.mark.parametrize("mutation", ("stage", "scope", "unit"))
def test_gap_proof_rejects_bound_identity_mismatches_against_solver_stage(mutation: str) -> None:
    payload = _gap_bounded_pac_result_for_sense("min", "26", "25", "24")
    bound = _find(payload["proof"]["stage_bounds"], "objective_code", "fixed_l2")
    if mutation == "stage":
        bound["stage"] = "solver-other-stage"
    elif mutation == "scope":
        bound["scope"] = "incumbent_face"
    else:
        bound["unit"] = {"kind": "valuation_money_squared", "currency_code": "USD"}
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)


SELL_IRREDUCIBILITY_UNRESOLVED = "portfolio_rebalancer.sell_irreducibility_unresolved"


def _sell_irreducibility_issue(code: str, *, kind: str = "proof", severity: str = "warning") -> JsonObject:
    issue = _catalogue_issue_specimen(code)
    issue["severity"] = severity
    issue["kind"] = kind
    return issue


def _sell_irreducibility_not_proven_result(
    factory: PayloadFactory,
    *,
    policy: str | None = None,
    issue_code: str | None = SELL_IRREDUCIBILITY_UNRESOLVED,
    issue_kind: str = "proof",
    issue_severity: str = "warning",
    stop_reason: str = "completed",
) -> JsonObject:
    payload = factory()
    if policy is not None:
        payload["scenario_basis"]["policy"] = policy
    payload["proof"] = {
        "kind": "not_proven",
        "reason_code": SELL_IRREDUCIBILITY_UNRESOLVED,
    }
    payload["issues"] = [] if issue_code is None else [_sell_irreducibility_issue(issue_code, kind=issue_kind, severity=issue_severity)]
    payload["stop_reason"] = stop_reason
    payload["solver_evidence"] = {"kind": "not_run", "reason": "allocation.solver_not_required"} if stop_reason == "completed" else {"kind": "reported_floating", "stages": [_reported_solver_stage(status="unfinished")]}
    return payload


@pytest.mark.parametrize("stop_reason", ("completed", "time_limit", "node_limit"))
def test_rebalancer_sell_irreducibility_not_proven_binding_is_orthogonal_to_valid_stop_reason(stop_reason: str) -> None:
    payload = _sell_irreducibility_not_proven_result(_rebalancer_incumbent_result, stop_reason=stop_reason)
    model, _emitted = _strict_roundtrip(REBALANCER_PLAN_OUTPUT_ADAPTER, payload)
    wire = REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")

    reason_code = wire["proof"]["reason_code"]
    assert reason_code == SELL_IRREDUCIBILITY_UNRESOLVED
    assert [issue["code"] for issue in wire["issues"]] == [reason_code]
    assert wire["issues"][0]["kind"] == "proof"
    assert wire["issues"][0]["severity"] == "warning"
    assert wire["stop_reason"] == stop_reason
    expected_solver_kind = "not_run" if stop_reason == "completed" else "reported_floating"
    assert wire["solver_evidence"]["kind"] == expected_solver_kind


SELL_IRREDUCIBILITY_BINDING_REJECTION_CASES = (
    pytest.param(PAC_PLAN_OUTPUT_ADAPTER, _pac_no_op_result, None, SELL_IRREDUCIBILITY_UNRESOLVED, "proof", "warning", id="pac"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_no_op_result, "invest_only", SELL_IRREDUCIBILITY_UNRESOLVED, "proof", "warning", id="rebalancer-invest-only"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, None, None, "proof", "warning", id="missing-issue"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, None, "allocation.no_positive_order_fundable", "proof", "warning", id="wrong-code"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, None, SELL_IRREDUCIBILITY_UNRESOLVED, "constraint", "warning", id="wrong-kind"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, None, SELL_IRREDUCIBILITY_UNRESOLVED, "proof", "error", id="error-severity"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, None, SELL_IRREDUCIBILITY_UNRESOLVED, "proof", "info", id="info-severity"),
)


@pytest.mark.parametrize(
    ("adapter", "factory", "policy", "issue_code", "issue_kind", "issue_severity"),
    SELL_IRREDUCIBILITY_BINDING_REJECTION_CASES,
)
def test_sell_irreducibility_not_proven_reason_rejects_invalid_product_policy_or_issue_binding(
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    policy: str | None,
    issue_code: str | None,
    issue_kind: str,
    issue_severity: str,
) -> None:
    payload = _sell_irreducibility_not_proven_result(
        factory,
        policy=policy,
        issue_code=issue_code,
        issue_kind=issue_kind,
        issue_severity=issue_severity,
    )
    _reject(adapter, payload)


OPTIMAL_PROOF_PRODUCT_CASES = (
    pytest.param("PAC", PAC_PLAN_OUTPUT_ADAPTER, _pac_no_op_result, "turnover", id="pac"),
    pytest.param("Rebalancer", REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, "route_priority", id="rebalancer"),
)
OPTIMAL_PROOF_SOURCE_CASES = (
    pytest.param("exhaustive_oracle", id="exhaustive-oracle"),
    pytest.param("score_lattice_closure", id="score-lattice-closure"),
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
@pytest.mark.parametrize("proof_source", OPTIMAL_PROOF_SOURCE_CASES)
def test_optimal_proven_witness_covers_every_published_objective_stage_in_exact_order(
    product: str,
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    _extra_code: str,
    proof_source: str,
) -> None:
    payload = factory()
    published_codes = _primary_objective_codes(payload)
    payload["proof"] = _optimal_proven_proof(proof_source, published_codes)

    model, _emitted = _strict_roundtrip(adapter, payload)
    wire = adapter.dump_python(model, mode="json")
    witness = wire["proof"]["witness"]

    assert witness["objective_codes"] == published_codes, product
    assert wire["proof"]["tie_break_closed"] is True
    if proof_source == "score_lattice_closure":
        assert witness["closed_stage_count"] == len(published_codes)


@pytest.mark.parametrize(("product", "adapter", "factory", "extra_code"), OPTIMAL_PROOF_PRODUCT_CASES)
@pytest.mark.parametrize("proof_source", OPTIMAL_PROOF_SOURCE_CASES)
@pytest.mark.parametrize("mutation", OPTIMAL_PROOF_MUTATION_CASES)
def test_optimal_proven_witness_rejects_incomplete_or_false_objective_closure(
    product: str,
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    extra_code: str,
    proof_source: str,
    mutation: str,
) -> None:
    payload = factory()
    published_codes = _primary_objective_codes(payload)

    if mutation == "missing":
        witness_codes = [published_codes[0], *published_codes[2:]]
    elif mutation == "subset":
        witness_codes = published_codes[:2]
    elif mutation == "reordered":
        witness_codes = [published_codes[1], published_codes[0], *published_codes[2:]]
    elif mutation == "duplicate":
        witness_codes = [*published_codes, published_codes[-1]]
    elif mutation == "extra":
        assert extra_code not in published_codes, product
        witness_codes = [*published_codes, extra_code]
    elif mutation == "unknown":
        witness_codes = [*published_codes[:-1], "unknown_objective"]
    elif mutation in {"tie-closure-missing", "tie-closure-false"}:
        witness_codes = published_codes
    else:
        raise AssertionError(f"unhandled objective-closure mutation {mutation!r}")

    payload["proof"] = _optimal_proven_proof(proof_source, witness_codes)
    if mutation == "tie-closure-missing":
        payload["proof"].pop("tie_break_closed")
    elif mutation == "tie-closure-false":
        payload["proof"]["tie_break_closed"] = False
    _reject(adapter, payload)


@pytest.mark.parametrize(("product", "adapter", "factory", "_extra_code"), OPTIMAL_PROOF_PRODUCT_CASES)
@pytest.mark.parametrize("closed_stage_count_delta", (-1, 1), ids=("too-few", "too-many"))
def test_score_lattice_closed_stage_count_equals_full_objective_vector_length(
    product: str,
    adapter: TypeAdapter[Any],
    factory: PayloadFactory,
    _extra_code: str,
    closed_stage_count_delta: int,
) -> None:
    payload = factory()
    published_codes = _primary_objective_codes(payload)
    payload["proof"] = _optimal_proven_proof("score_lattice_closure", published_codes)
    payload["proof"]["witness"]["closed_stage_count"] = len(published_codes) + closed_stage_count_delta

    assert payload["proof"]["witness"]["objective_codes"] == published_codes, product
    _reject(adapter, payload)


@pytest.mark.parametrize("proof_source", ("exhaustive_oracle", "deterministic_conflict"))
def test_infeasible_result_requires_a_matching_exact_infeasibility_witness(proof_source: str) -> None:
    payload = _ready_infeasible_result("PAC")
    if proof_source == "deterministic_conflict":
        payload["proof"] = {
            "kind": "infeasibility_proven",
            "proof_source": "deterministic_conflict",
            "witness": {
                "kind": "deterministic_conflict",
                "issue_codes": [
                    "allocation.required_min_notional_unfunded",
                    "allocation.no_positive_order_fundable",
                ],
                "summary_code": "allocation.no_positive_order_fundable",
            },
        }
    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")
    assert wire["proof"]["proof_source"] == proof_source
    if proof_source == "deterministic_conflict":
        witness = wire["proof"]["witness"]
        assert witness["summary_code"] in witness["issue_codes"]
        assert set(witness["issue_codes"]) <= set(EXPECTED_PLANNER_ISSUE_CODES)


def test_deterministic_conflict_summary_code_must_reference_a_listed_issue() -> None:
    payload = _ready_infeasible_result("PAC")
    payload["proof"] = {
        "kind": "infeasibility_proven",
        "proof_source": "deterministic_conflict",
        "witness": {
            "kind": "deterministic_conflict",
            "issue_codes": ["allocation.required_min_notional_unfunded"],
            "summary_code": "allocation.no_positive_order_fundable",
        },
    }
    _reject(PAC_PLAN_OUTPUT_ADAPTER, payload)


def test_finished_floating_solver_report_does_not_become_exact_proof() -> None:
    payload = _pac_no_op_result()
    payload["stop_reason"] = "completed"
    payload["solver_evidence"] = {"kind": "reported_floating", "stages": [_reported_solver_stage(status="finished")]}
    payload["proof"] = {"kind": "not_proven", "reason_code": "allocation.exact_proof_not_established"}

    model, _emitted = _strict_roundtrip(PAC_PLAN_OUTPUT_ADAPTER, payload)
    wire = PAC_PLAN_OUTPUT_ADAPTER.dump_python(model, mode="json")
    assert wire["solver_evidence"]["kind"] == "reported_floating"
    assert wire["proof"]["kind"] == "not_proven"


@pytest.mark.parametrize(
    "mutation",
    (
        "reported-floating-proof-source",
        "mismatched-optimal-witness",
        "zero-feasible-optimal-oracle",
        "feasible-infeasibility-oracle",
        "gap-without-reported-solver",
        "gap-missing-unfinished-stage",
    ),
)
def test_false_or_incomplete_exact_proof_is_rejected(mutation: str) -> None:
    if mutation == "feasible-infeasibility-oracle":
        payload = _ready_infeasible_result("PAC")
        payload["proof"]["witness"]["feasible_candidates"] = 1
    elif mutation in {"gap-without-reported-solver", "gap-missing-unfinished-stage"}:
        payload = _gap_bounded_pac_result()
        if mutation == "gap-without-reported-solver":
            payload["solver_evidence"] = {"kind": "not_run", "reason": "allocation.solver_not_required"}
            payload["stop_reason"] = "completed"
        else:
            payload["proof"]["stage_bounds"] = []
    else:
        payload = _pac_no_op_result()
        payload["proof"] = _optimal_proven_proof("exhaustive_oracle", _primary_objective_codes(payload))
        if mutation == "reported-floating-proof-source":
            payload["proof"]["proof_source"] = "reported_floating"
        elif mutation == "mismatched-optimal-witness":
            payload["proof"]["proof_source"] = "score_lattice_closure"
        else:
            payload["proof"]["witness"]["feasible_candidates"] = 0
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
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_no_op_with_zero_asset_result, True, id="rebalancer-zero-asset"),
    pytest.param(REBALANCER_PLAN_OUTPUT_ADAPTER, _rebalancer_incumbent_result, True, id="rebalancer-invested"),
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


PLANNER_FULL_SCHEMA_FINGERPRINT_CASES = (
    pytest.param(
        PAC_PLAN_INPUT_ADAPTER,
        PAC_PLAN_OUTPUT_ADAPTER,
        "e2b70735f589d376d5c105416b5b9e30c3a0b927bf7713222af21dcfdb0eaa28",
        id="pac",
    ),
    pytest.param(
        REBALANCER_PLAN_INPUT_ADAPTER,
        REBALANCER_PLAN_OUTPUT_ADAPTER,
        "61ed6bdeaef112cf0df461468da3f536033d51f34d0abafea9ca22c645a7c12b",
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
    pytest.param("rebalancer-input", REBALANCER_PLAN_INPUT_ADAPTER, "validation", 2, "policy", id="rebalancer-input"),
    pytest.param("pac-output", PAC_PLAN_OUTPUT_ADAPTER, "serialization", 7, "result_state", id="pac-output"),
    pytest.param("rebalancer-output", REBALANCER_PLAN_OUTPUT_ADAPTER, "serialization", 7, "result_state", id="rebalancer-output"),
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
    assert declared_operations(schema) == frozenset({"plan"})
    assert len(list(root_models(schema))) == expected_roots
    _assert_acyclic_local_references(schema)
    open_map_node_ids = _open_map_property_schema_node_ids(schema)

    for node in walk_schema(schema):
        assert "default" not in node
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
                required = node.get("required")
                assert isinstance(properties, dict)
                assert isinstance(required, list)
                assert set(required) == set(properties)
                for property_schema in properties.values():
                    assert isinstance(property_schema, dict)
                    assert "default" not in property_schema

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
    assert observed <= {"policy", "result_state", "kind", "side"}


def test_exported_planner_contract_uses_all_required_named_discriminator_families() -> None:
    observed: set[str] = set()
    for adapter, mode in (
        (PAC_PLAN_INPUT_ADAPTER, "validation"),
        (REBALANCER_PLAN_INPUT_ADAPTER, "validation"),
        (PAC_PLAN_OUTPUT_ADAPTER, "serialization"),
        (REBALANCER_PLAN_OUTPUT_ADAPTER, "serialization"),
    ):
        schema = generate_tool_schema(adapter, mode)
        for node in walk_schema(schema):
            discriminator = node.get("discriminator")
            if isinstance(discriminator, dict) and isinstance(discriminator.get("propertyName"), str):
                observed.add(discriminator["propertyName"])
    assert observed == {"policy", "result_state", "kind", "side"}
