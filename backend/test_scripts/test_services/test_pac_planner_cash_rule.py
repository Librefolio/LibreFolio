"""The Rebalancer's cash rule: every plan it publishes can be carried out (lot CR of project 67).

Found on the G5 browser scenario after lot S1 (journal ``67_rebalancer/notes/regola-cassa-eseguibilita.md``): the model
checked only the final balances, and with free transfers and no spread a plan could send cash round between two Brokers, two
opposite exchanges and two transfers, at no cost. No order of the steps can pay such a plan, and the planner refused it
(``PlanNotExecutableError``): on G5, 4 random seeds out of 11 at 30 s.

The rule, agreed with the developer on 16/11 (specification §16):
- R1: a cell (Broker × currency) that receives a conversion sends nothing to another Broker;
- R2: money travels only in the currency it already has: a cell sends at most its original money (its cash and its
  deposits), never converted money.

In the model each cell has one signed balance of what it receives from the other Brokers, the lanes' decisions are held at
zero, and the transfers are derived from the balances when the plan is read. The exact replay checks the same rule as
``TRANSFER_NO_RELAY``: in one currency, a Broker that receives (a conversion or a transfer) sends no transfer. With the final
balances never negative that is R1 and R2 together: a cell that sends receives nothing, so what it sends is its own money.

The PAC has no lanes (a test may set one by hand), and its model and refs do not move: the rule is the Rebalancer's.
"""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_INPUT_ADAPTER
from backend.app.services.pac_allocator import models as pac_models
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluation.bounds import transfer_decision_id
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.models import CandidateActionVector, CandidateDecision, ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.normalize import normalize_rebalancer_plan
from backend.app.services.pac_allocator.solver import solve_policy_program
from backend.test_scripts.test_services import _reb_small_cases as cases
from backend.test_scripts.test_services import test_pac_planner_solver as solver_tests
from backend.test_scripts.test_services.test_pac_planner_evaluator import _transfer_lane_scenario, _with_lane

R = cases.R
G5_REQUEST = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator" / "rebalancer_plan_request.g5-browser.2-0-0.json"
FX_1_EUR_USD = "fx:8:broker:1:EUR:USD"
FX_1_USD_EUR = "fx:8:broker:1:USD:EUR"
FX_2_USD_EUR = "fx:8:broker:2:USD:EUR"
LANE_12_EUR = "transfer:8:broker:18:broker:2:EUR"
LANE_12_USD = "transfer:8:broker:18:broker:2:USD"
LANE_21_EUR = "transfer:8:broker:28:broker:1:EUR"
LANE_21_USD = "transfer:8:broker:28:broker:1:USD"


def _g5(*, one_route: bool = False) -> ExactPlannerScenario:
    """The G5 scenario; ``one_route`` keeps only Broker 2's purchases, so Broker 1 holds nothing but its two cash targets."""
    request = json.loads(G5_REQUEST.read_text())
    if one_route:
        request["order_routes"] = [route for route in request["order_routes"] if route["broker_id"] == "broker:2"]
    outcome = normalize_rebalancer_plan(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(request))
    assert outcome.ready, [issue.code for issue in outcome.issues]
    return outcome.normalized


def _candidate(view: ExactPolicyView, quanta: dict[str, int]) -> CandidateActionVector:
    unknown = set(quanta) - {access.decision_id for access in view.decisions}
    assert not unknown, unknown
    return CandidateActionVector(view_id=view.view_id, candidate_id="candidate:cash-rule", decisions=tuple(CandidateDecision(decision_id=access.decision_id, quanta=quanta.get(access.decision_id, 0)) for access in view.decisions))


def _replay(scenario: ExactPlannerScenario, quanta: dict[str, int]):
    view = build_exact_policy_view(scenario)
    return evaluate_exact_candidate(scenario, view, _candidate(view, quanta))


# ---------------------------------------------------------------------------
# The exact replay: TRANSFER_NO_RELAY
# ---------------------------------------------------------------------------


def test_the_g5_cash_cycle_no_order_can_pay_is_refused() -> None:
    """The cycle of the refused plan of seed 1 (journal ``67-S1/refused-new-seed1-30s.json``), its exchanges and transfers
    without its purchases. Broker 1 changes 59 374 € holding 17 350 € and sends the dollars away; Broker 2 changes them back and
    returns the euros. The final balances are all positive, so the replay accepted it; no order of the steps can pay it."""
    evaluation = _replay(
        _g5(),
        {
            FX_1_EUR_USD: 5_937_426,
            FX_2_USD_EUR: 4_490_246,
            LANE_12_EUR: 750,
            LANE_12_USD: 6_652_618,
            LANE_21_EUR: 4_829_246,
            LANE_21_USD: 1_166_270,
        },
    )
    assert all(row.final_spendable >= 0 for row in evaluation.ledgers)
    assert evaluation.feasible is False
    assert "TRANSFER_NO_RELAY" in evaluation.conflict_codes


def test_a_cell_that_sends_and_receives_the_same_currency_is_refused() -> None:
    """100 € from Broker 1 to Broker 2 and 100 € back: each EUR cell both sends and receives."""
    evaluation = _replay(_g5(), {LANE_12_EUR: 10_000, LANE_21_EUR: 10_000})
    assert evaluation.feasible is False
    assert set(evaluation.conflict_codes) == {"TRANSFER_NO_RELAY"}


def test_a_cell_that_receives_a_conversion_sends_nothing() -> None:
    """R1: Broker 1 changes 1 000 € into dollars and sends 500 $ to Broker 2. It holds 5 344.53 $ of its own, so R2 alone
    would allow the transfer: the dollar cell receives a conversion, and R1 forbids it to send."""
    evaluation = _replay(_g5(), {FX_1_EUR_USD: 100_000, LANE_12_USD: 50_000})
    assert evaluation.feasible is False
    assert set(evaluation.conflict_codes) == {"TRANSFER_NO_RELAY"}


def test_original_money_travels_and_is_changed_where_it_is_spent() -> None:
    """What the rule allows: Broker 2 sends 1 000 € of its own to Broker 1, which changes them into dollars. Broker 1's EUR cell
    receives a transfer and gives a conversion: a conversion out of a cell is not a transfer, so the cell sends nothing."""
    evaluation = _replay(_g5(), {LANE_21_EUR: 100_000, FX_1_EUR_USD: 100_000})
    assert evaluation.feasible is True, evaluation.conflict_codes
    facts = [item for item in evaluation.constraints if item.ref_id.startswith("constraint:transfer_no_relay:")]
    assert facts and all(item.satisfied for item in facts)


def test_the_pac_has_no_cash_rule_even_with_a_lane_set_by_hand() -> None:
    """The PAC's refs do not move: a PAC scenario with a lane (D4 a) gets no ``TRANSFER_NO_RELAY``."""
    scenario = _with_lane(_transfer_lane_scenario(), "broker:a", "broker:b")
    view = build_exact_policy_view(scenario)
    assert not [ref for ref in view.constraints if ref.code == "TRANSFER_NO_RELAY"]


# ---------------------------------------------------------------------------
# The model: one signed balance per cell
# ---------------------------------------------------------------------------


def test_the_rebalancer_model_moves_cash_by_one_signed_balance_per_cell() -> None:
    """G5: one integer balance per Broker × currency, each bounded below by the cell's own money (R2, the tightest bound,
    which R1's rows read), one balance row per currency, the lanes held at zero in SCIP, and one R1 row per conversion."""
    scenario = _g5()
    program = compile_policy_program(scenario, build_exact_policy_view(scenario))
    variables = {var.name: var for var in program.model.getVars()}
    rows = {cons.name for cons in program.model.getConss()}
    nets = {name: (var.vtype(), var.getLbOriginal()) for name, var in variables.items() if name.startswith("pool_net:")}
    assert nets == {
        "pool_net:broker:1:EUR": ("INTEGER", -1_735_000),
        "pool_net:broker:1:USD": ("INTEGER", -534_453),
        "pool_net:broker:2:EUR": ("INTEGER", -820_000),
        "pool_net:broker:2:USD": ("INTEGER", 0),
    }
    assert {name for name in rows if name.startswith("pool_balance:")} == {"pool_balance:EUR", "pool_balance:USD"}
    for lane in scenario.transfer_lanes:
        assert variables[transfer_decision_id(lane)].getUbOriginal() == 0
    assert not [name for name in variables if name.startswith("active_transfer:")]
    fx = [access.decision_id for access in program.view.decisions if access.family == "fx_debit"]
    assert {name for name in rows if name.startswith("own_first:")} == {f"own_first:{decision_id}" for decision_id in fx}


def test_the_pac_model_with_a_lane_set_by_hand_keeps_its_transfer_decision() -> None:
    """The PAC's model does not move: its lane is a decision SCIP can set, and no balance variable appears."""
    scenario = _with_lane(_transfer_lane_scenario(), "broker:a", "broker:b")
    program = compile_policy_program(scenario, build_exact_policy_view(scenario))
    variables = {var.name: var for var in program.model.getVars()}
    assert variables[transfer_decision_id(scenario.transfer_lanes[0])].getUbOriginal() > 0
    assert not [name for name in variables if name.startswith("pool_")]


def test_a_cash_target_alone_gets_its_conversions() -> None:
    """§7 n. 3 of the note: G5 with only Broker 2's purchases. Broker 1 buys nothing but holds a target in euros and one in
    dollars; with the rule, its dollars can come only from a conversion on Broker 1 itself (converted money never travels),
    so the scenario needs that decision. Without it, the plan is 41 € worse (816.96 € against 775.82 €)."""
    scenario = _g5(one_route=True)
    fx = {access.decision_id for access in build_exact_policy_view(scenario).decisions if access.family == "fx_debit"}
    assert {FX_1_EUR_USD, FX_1_USD_EUR} <= fx


# ---------------------------------------------------------------------------
# The transfers of a plan, derived from the balances
# ---------------------------------------------------------------------------


def _lanes(brokers: tuple[str, ...], currency: str = "EUR") -> tuple[pac_models.ExactTransferLane, ...]:
    return tuple(pac_models.ExactTransferLane(source_broker_id=source, destination_broker_id=destination, currency=currency) for source in brokers for destination in brokers if source != destination)


def test_transfers_are_derived_from_the_balances_by_a_fixed_rule() -> None:
    """Senders and receivers in Broker order, the first sender serving the first receiver: a sends 3 to c, b sends 2 to c and
    3 to d. Every other lane is zero."""
    from backend.app.services.pac_allocator.constraints.pool import derive_transfer_quanta  # noqa: PLC0415 - the module comes with lot CR

    lanes = _lanes(("a", "b", "c", "d"))
    quanta = derive_transfer_quanta(lanes, {("a", "EUR"): -3, ("b", "EUR"): -5, ("c", "EUR"): 5, ("d", "EUR"): 3})
    moved = {decision_id: value for decision_id, value in quanta.items() if value}
    by_lane = {transfer_decision_id(lane): (lane.source_broker_id, lane.destination_broker_id) for lane in lanes}
    assert {by_lane[decision_id]: value for decision_id, value in moved.items()} == {("a", "c"): 3, ("b", "c"): 2, ("b", "d"): 3}
    assert set(quanta) == set(by_lane)


def _t4_on_two_brokers() -> ExactPlannerScenario:
    """T4 (cash 200 € on ``broker:x``, the best plan buys 195 € of B for a 5 € fee) with every purchase on ``broker:y``: the
    plan has to move the cash first."""
    base = cases.t4()
    broker_y = replace(base.brokers[0], broker_id="broker:y", name="broker:y")
    return replace(
        base,
        brokers=(base.brokers[0], broker_y),
        order_routes=tuple(replace(route, broker_id="broker:y") for route in base.order_routes),
        transfer_lanes=_lanes((cases.BROKER, "broker:y")),
    )


def test_the_solver_reads_the_transfers_off_the_balances() -> None:
    """T4 on two Brokers: SCIP's plan moves the 200 € from x to y through the balances, the candidate carries the transfer on
    its lane, the replay accepts it, and the plan counts two operations (the transfer and the purchase)."""
    scenario = _t4_on_two_brokers()
    view = build_exact_policy_view(scenario)
    result = solve_policy_program(compile_policy_program(scenario, view), time_budget_seconds=10)
    quanta = {item.decision_id: item.quanta for item in result.candidate.decisions}
    lane_xy, lane_yx = (transfer_decision_id(lane) for lane in scenario.transfer_lanes)
    assert (quanta[lane_xy], quanta[lane_yx]) == (20_000, 0)
    assert quanta[cases.buy_decision("asset:b")] == 195
    evaluation = evaluate_exact_candidate(scenario, view, result.candidate)
    assert evaluation.feasible is True, evaluation.conflict_codes
    count = next(item.value for item in evaluation.objectives if item.ref_id == next(ref.ref_id for ref in view.objectives if ref.code == "operation_count"))
    assert count == 2
    assert result.anomaly is None


def _operation_count(scenario: ExactPlannerScenario, quanta: dict[str, int]) -> int:
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, quanta))
    assert evaluation.feasible is True, evaluation.conflict_codes
    (ref_id,) = [ref.ref_id for ref in view.objectives if ref.code == "operation_count"]
    return next(item.value for item in evaluation.objectives if item.ref_id == ref_id)


def test_the_replay_counts_transfers_from_the_balances_as_the_model_does() -> None:
    """Specification §16.3 and §16.9 n. 6: per currency, the cells that move less one, on both sides. T4 on four Brokers, with
    200 € on x and 200 € on z: x sends 100 € to y and z sends 50 € to w. Two pairs balance each other exactly, so the plan lists
    2 transfers and the count is 3. Counted the same way as the model, the stage's bounds never contradict the plan's exact value
    (``solver._flag_contradicted_bounds`` checks ``operation_count``). With one sender, two receivers it is exact: 2."""
    base = cases.t4()
    brokers = (cases.BROKER, "broker:y", "broker:z", "broker:w")
    cash_z = replace(base.existing_cash[0], cash_id="cash:z:eur", broker_id="broker:z")
    scenario = replace(
        base,
        brokers=tuple(sorted((replace(base.brokers[0], broker_id=broker, name=broker) for broker in brokers), key=lambda item: item.broker_id)),
        existing_cash=tuple(sorted((*base.existing_cash, cash_z), key=lambda item: item.cash_id)),
        transfer_lanes=_lanes(tuple(sorted(brokers))),
    )
    lane = {(item.source_broker_id, item.destination_broker_id): transfer_decision_id(item) for item in scenario.transfer_lanes}
    assert _operation_count(scenario, {lane[(cases.BROKER, "broker:y")]: 10_000, lane[("broker:z", "broker:w")]: 5_000}) == 3
    assert _operation_count(scenario, {lane[(cases.BROKER, "broker:y")]: 10_000, lane[(cases.BROKER, "broker:w")]: 5_000}) == 2


# ---------------------------------------------------------------------------
# The model and the replay agree: the solver against the exhaustive oracle
# ---------------------------------------------------------------------------


def _two_brokers_with_a_conversion() -> ExactPlannerScenario:
    """The smallest case where cash must travel and be changed: 2 € on ``broker:x``, every purchase on ``broker:y`` (asset A
    in euros, at most 1 €; asset USD in dollars, 1 $ a unit), lanes both ways in euros, a conversion on y, no fee and no
    spread, whole units of money. The oracle walks every plan, so the model's rule must be exactly the replay's: x sends its
    2 €, y changes them and buys 2 units of USD."""
    base = cases.scenario(
        "cash-rule-oracle",
        holdings={"asset:a": cases.ONE},
        cash=R(2),
        weights={"asset:a": R(1, 2), "asset:usd": R(1, 2)},
        usd_asset="asset:usd",
        caps={"asset:a": cases.ONE},
    )
    no_fee = tuple(replace(item, fixed_fee=replace(item.fixed_fee, amount=cases.ZERO)) for item in base.brokers[0].fee_schedules)
    broker_x = replace(base.brokers[0], fee_schedules=no_fee)
    return replace(
        base,
        brokers=(broker_x, replace(broker_x, broker_id="broker:y", name="broker:y")),
        order_routes=tuple(replace(route, broker_id="broker:y") for route in base.order_routes),
        transfer_lanes=_lanes((cases.BROKER, "broker:y")),
        currency_specs=tuple(replace(spec, minor_unit=cases.ONE) for spec in base.currency_specs),
        fx_spread_rate=cases.ZERO,
    )


def test_the_solver_matches_the_oracle_with_lanes_both_ways_and_a_conversion() -> None:
    """Row 4 of the note: the same rule in the model and in the exact replay. The oracle sees every plan the replay accepts,
    «back and forth» and converted money sent away included; the solver's plan must be its optimum, quanta and key."""
    solver_tests.test_solver_incumbent_equals_exhaustive_oracle_optimum(_two_brokers_with_a_conversion)
    view = build_exact_policy_view(_two_brokers_with_a_conversion())
    moved = {access.decision_id for access in view.decisions if access.family in {"fx_debit", "broker_transfer"}}
    assert len(moved) == 3


def test_the_solver_counts_three_brokers_as_the_replay_does() -> None:
    """Two Brokers send, one receives (T4 with 200 € on x and 200 € on z, every purchase on w): the model's count of the
    transfers and the replay's agree, so no stage's bounds contradict the plan (no anomaly)."""
    base = cases.t4()
    brokers = (cases.BROKER, "broker:w", "broker:z")
    cash_z = replace(base.existing_cash[0], cash_id="cash:z:eur", broker_id="broker:z")
    scenario = replace(
        base,
        brokers=tuple(replace(base.brokers[0], broker_id=broker, name=broker) for broker in sorted(brokers)),
        existing_cash=tuple(sorted((*base.existing_cash, cash_z), key=lambda item: item.cash_id)),
        order_routes=tuple(replace(route, broker_id="broker:w") for route in base.order_routes),
        transfer_lanes=_lanes(tuple(sorted(brokers))),
    )
    view = build_exact_policy_view(scenario)
    result = solve_policy_program(compile_policy_program(scenario, view), time_budget_seconds=10)
    assert result.anomaly is None
    evaluation = evaluate_exact_candidate(scenario, view, result.candidate)
    assert evaluation.feasible is True, evaluation.conflict_codes
    into_w = sum(item.quanta for item in result.candidate.decisions if item.decision_id.endswith("8:broker:w:EUR") and item.quanta)
    assert into_w > 0


def test_four_brokers_and_two_balanced_pairs_count_three_on_both_sides_with_no_anomaly() -> None:
    """Spec §16.9 n. 6, the declared limit, pinned (the consultant's request): T4 with 200 € on x and on z, the purchases
    on w and on y, and the balances held at x −100 €, w +100 €, z −50 €, y +50 €. In Broker order (w, x, y, z) the fixed rule
    lists 2 transfers (x → w, z → y); the model and the replay both count 3 (four cells move, less one); the stage's bounds
    agree with the plan, so the solver flags no anomaly."""
    base = cases.t4()
    brokers = tuple(sorted((cases.BROKER, "broker:w", "broker:y", "broker:z")))
    cash_z = replace(base.existing_cash[0], cash_id="cash:z:eur", broker_id="broker:z")
    routes = tuple(replace(route, route_id=f"{route.route_id}:{broker}", broker_id=broker) for route in base.order_routes for broker in ("broker:w", "broker:y"))
    scenario = replace(
        base,
        brokers=tuple(replace(base.brokers[0], broker_id=broker, name=broker) for broker in brokers),
        existing_cash=tuple(sorted((*base.existing_cash, cash_z), key=lambda item: item.cash_id)),
        order_routes=tuple(sorted(routes, key=lambda item: item.route_id)),
        transfer_lanes=_lanes(brokers),
    )
    view = build_exact_policy_view(scenario)
    program = compile_policy_program(scenario, view)
    held = {(cases.BROKER, "EUR"): -10_000, ("broker:w", "EUR"): 10_000, ("broker:z", "EUR"): -5_000, ("broker:y", "EUR"): 5_000}
    for cell, value in held.items():
        program.model.chgVarLb(program.variables.pool.net[cell], value)
        program.model.chgVarUb(program.variables.pool.net[cell], value)
    result = solve_policy_program(program, time_budget_seconds=10)

    assert result.anomaly is None
    moved = {item.decision_id: item.quanta for item in result.candidate.decisions if item.decision_id.startswith("transfer:") and item.quanta}
    lane = {(item.source_broker_id, item.destination_broker_id): transfer_decision_id(item) for item in scenario.transfer_lanes}
    assert moved == {lane[(cases.BROKER, "broker:w")]: 10_000, lane[("broker:z", "broker:y")]: 5_000}
    (count_stage,) = [stage for stage in result.stages if stage.objective_code == "operation_count"]
    evaluation = evaluate_exact_candidate(scenario, view, result.candidate)
    (ref_id,) = [ref.ref_id for ref in view.objectives if ref.code == "operation_count"]
    exact = next(item.value for item in evaluation.objectives if item.ref_id == ref_id)
    orders = sum(1 for item in result.candidate.decisions if item.decision_id.startswith("buy:") and item.quanta)
    assert exact == orders + 3
    assert round(count_stage.primal) == exact


# ---------------------------------------------------------------------------
# A cash maximum the replay refuses by a cent (the consultant's «cashmax», spec §16.11)
# ---------------------------------------------------------------------------


def _t4_with_a_cash_maximum() -> ExactPlannerScenario:
    """T4 with B at 9.995 € a unit, bought in whole units: its debit rounds up, so it keeps a one-cent reserve in the model
    (row 6). The cash cell has a maximum of 175 €. Two units of B cost 19.99 € exactly and a 5 € fee: the cell ends at
    175.01 € in the replay, one cent above its maximum, while the model, which takes the reserve out, sees 175.00 €."""
    return cases.scenario(
        "t4-cash-maximum",
        holdings={"asset:a": R(5000), "asset:b": R(4800)},
        cash=R(200),
        weights={"asset:a": cases.HALF, "asset:b": cases.HALF},
        prices={"asset:b": R(1999, 200)},
        whole_units=frozenset({"asset:b"}),
        cash_entries=(pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=None, maximum=pac_models.ExactLimit(kind="amount", value=R(175)), weight=R(0)),),
    )


def test_a_cash_maximum_holds_in_the_replay_not_only_in_the_model() -> None:
    """The maximum's row reads the highest cash the replay can post: the model's cash plus the reserves the cell keeps back,
    since a rounding never adds cash. Two units of B would leave 175.01 €: the model must refuse them."""
    from pyscipopt import Model  # noqa: PLC0415, F401 - SCIP is what compile_policy_program builds

    scenario = _t4_with_a_cash_maximum()
    view = build_exact_policy_view(scenario)
    two_of_b = {cases.buy_decision("asset:b"): 2}
    replay = evaluate_exact_candidate(scenario, view, _candidate(view, two_of_b))
    assert "ENTRY_VALUE_WITHIN_LIMITS" in replay.conflict_codes, "PREMISE: the replay refuses two units of B by a cent"

    program = compile_policy_program(scenario, view)
    for access in view.decisions:
        variable = program.variables.quanta[access.decision_id]
        program.model.chgVarLb(variable, two_of_b.get(access.decision_id, 0))
        program.model.chgVarUb(variable, two_of_b.get(access.decision_id, 0))
    program.model.setObjective(program.objective_stages[0].expression, "minimize")
    program.model.optimize()
    assert program.model.getStatus() == "infeasible"


def test_a_cash_maximum_far_below_the_cell_holds_within_a_cent() -> None:
    """Seen on «cashmax», seed 1: SCIP accepts a row within a tolerance relative to the side it sees, and the cell's own
    cash moves to that side. Here the cell holds 19 996.01 € and its maximum is 2 000 €: the row reads «decisions ≤
    −1 799 601 cents», and a cent too many passes. 1 800 units of B (17 991 € and a 5 € fee) leave 2 000.01 € in the
    replay: the margin, taken on that side, makes the model refuse them."""
    scenario = cases.scenario(
        "t4-cash-maximum-far",
        holdings={"asset:a": R(5000), "asset:b": R(4800)},
        cash=R(1999601, 100),
        weights={"asset:a": cases.HALF, "asset:b": cases.HALF},
        prices={"asset:b": R(1999, 200)},
        whole_units=frozenset({"asset:b"}),
        cash_entries=(pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=None, maximum=pac_models.ExactLimit(kind="amount", value=R(2000)), weight=R(0)),),
    )
    view = build_exact_policy_view(scenario)
    bought = {cases.buy_decision("asset:b"): 1800}
    replay = evaluate_exact_candidate(scenario, view, _candidate(view, bought))
    assert "ENTRY_VALUE_WITHIN_LIMITS" in replay.conflict_codes, "PREMISE: the replay refuses 1 800 units of B by a cent"

    program = compile_policy_program(scenario, view)
    for access in view.decisions:
        variable = program.variables.quanta[access.decision_id]
        program.model.chgVarLb(variable, bought.get(access.decision_id, 0))
        program.model.chgVarUb(variable, bought.get(access.decision_id, 0))
    program.model.setObjective(program.objective_stages[0].expression, "minimize")
    program.model.optimize()
    assert program.model.getStatus() == "infeasible"


def test_a_cash_minimum_far_above_holds_within_a_cent() -> None:
    """The minimum's mirror of the case above: the cell holds 20 004.99 € and its minimum is 2 000 €, the row «decisions ≥
    −1 800 499 cents». B at 10 € in whole units and the fixed 5 € fee never round, so the model's cash is the replay's:
    1 800 units of B leave 1 999.99 €, a cent short, within SCIP's tolerance of that side. The margin refuses them."""
    scenario = cases.scenario(
        "t4-cash-minimum-far",
        holdings={"asset:a": R(5000), "asset:b": R(4800)},
        cash=R(2000499, 100),
        weights={"asset:a": cases.HALF, "asset:b": cases.HALF},
        prices={"asset:b": R(10)},
        whole_units=frozenset({"asset:b"}),
        cash_entries=(pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=pac_models.ExactLimit(kind="amount", value=R(2000)), maximum=None, weight=R(0)),),
    )
    view = build_exact_policy_view(scenario)
    bought = {cases.buy_decision("asset:b"): 1800}
    replay = evaluate_exact_candidate(scenario, view, _candidate(view, bought))
    assert "ENTRY_VALUE_WITHIN_LIMITS" in replay.conflict_codes, "PREMISE: the replay refuses 1 800 units of B by a cent"

    program = compile_policy_program(scenario, view)
    for access in view.decisions:
        variable = program.variables.quanta[access.decision_id]
        program.model.chgVarLb(variable, bought.get(access.decision_id, 0))
        program.model.chgVarUb(variable, bought.get(access.decision_id, 0))
    program.model.setObjective(program.objective_stages[0].expression, "minimize")
    program.model.optimize()
    assert program.model.getStatus() == "infeasible"


def test_a_candidate_the_replay_refuses_never_replaces_the_plan_held() -> None:
    """Seen on «cashmax», seed 0: a tie-break's plan left a cash cell a cent above its maximum, became the best plan all the
    same, and the planner raised ``ExactReplayRejectedError``: no plan for the user. A candidate whose replay is refused
    (and that no rounding top-up repairs) is flagged and never replaces the plan already held."""
    from backend.app.services.pac_allocator import solver as solver_module  # noqa: PLC0415

    scenario = _t4_with_a_cash_maximum()
    view = build_exact_policy_view(scenario)
    program = compile_policy_program(scenario, view)
    cascade = solver_module._Cascade(program=program, checkpoint=None, reports=[])
    held = _candidate(view, {cases.buy_decision("asset:b"): 3})  # 29.99 € and the fee: the cell ends at 165.01 €
    solver_module._take_candidate(cascade, held, 1)
    assert cascade.best is held and cascade.anomaly is None

    solver_module._take_candidate(cascade, _candidate(view, {cases.buy_decision("asset:b"): 2}), 1)
    assert cascade.best is held
    assert cascade.anomaly is not None and "exact replay" in cascade.anomaly


def test_a_plan_the_replay_refuses_found_first_gives_way_to_any_publishable_one() -> None:
    """The first plan found is held even when its replay is refused, for want of another; it is no yardstick. A publishable
    plan found later replaces it, in the tail too, however its values compare: two units of B score better than three,
    but they leave the cell a cent above its maximum."""
    from backend.app.services.pac_allocator import solver as solver_module  # noqa: PLC0415

    scenario = _t4_with_a_cash_maximum()
    view = build_exact_policy_view(scenario)
    program = compile_policy_program(scenario, view)
    cascade = solver_module._Cascade(program=program, checkpoint=None, reports=[])
    refused = _candidate(view, {cases.buy_decision("asset:b"): 2})
    solver_module._take_candidate(cascade, refused, 1)
    assert cascade.best is refused and cascade.best_values is None, "a refused plan is held without values"

    cascade.in_tail = True
    publishable = _candidate(view, {cases.buy_decision("asset:b"): 3})
    solver_module._take_candidate(cascade, publishable, 2)
    assert cascade.best is publishable


_ZERO_BAND_CASES = {
    # cell cash, B's price, units of B that leave exactly 2 000.00 € (B in whole units, a fixed 5 € fee), and R in cents:
    # the reserves of the cell's postings that can round (B's debit at 9.995 €; the 5 € fee never rounds)
    "far, B never rounds": (R(2000500, 100), R(10), 1800, 0),  # 18 000 € from the bounds: the margins of lot CM, 2 cents a row
    "far, B rounds": (R(1999600, 100), R(1999, 200), 1800, 1),  # the margins, and B's debit keeps a cent (row 6)
    "near, B rounds": (R(220490, 100), R(1999, 200), 20, 1),  # no margin; B's cent alone
}


def _cash_band_scenario(name: str, cash, price, minimum, maximum, **fields) -> ExactPlannerScenario:
    """T4 with B in whole units at ``price``, A by the euro, and the cash cell held between ``minimum`` and ``maximum``;
    ``fields`` go to ``cases.scenario`` (``caps``)."""
    return cases.scenario(
        name,
        holdings={"asset:a": R(5000), "asset:b": R(4800)},
        cash=cash,
        weights={"asset:a": cases.HALF, "asset:b": cases.HALF},
        prices={"asset:b": price},
        whole_units=frozenset({"asset:b"}),
        cash_entries=(pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=pac_models.ExactLimit(kind="amount", value=minimum), maximum=pac_models.ExactLimit(kind="amount", value=maximum), weight=R(0)),),
        **fields,
    )


def _spy_compile(monkeypatch) -> list[bool]:
    """Record, per model the planner compiles, whether it is the wide one."""
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415

    compiled: list[bool] = []
    real_compile = planner.compile_policy_program

    def spy(scenario, view, **kwargs):
        compiled.append(kwargs.get("outer", False))
        return real_compile(scenario, view, **kwargs)

    monkeypatch.setattr(planner, "compile_policy_program", spy)
    return compiled


_OVERSHOOT_CODE = "allocation.cash_limit_exceeded_by_rounding"


@pytest.mark.parametrize("case", sorted(_ZERO_BAND_CASES))
def test_a_zero_cash_band_is_planned_on_the_wide_model_and_published(case: str, monkeypatch) -> None:
    """Lot ZB of project 67 (specification §16.16): a cash cell held to exactly 2 000 € (minimum = maximum), and a plan the
    replay accepts. The prudent model is infeasible (its margins and reserves ask a wider band), so the wide model is
    solved: its plan is published, not proven, never «infeasibility proven». Where its rounding ends the cell off 2 000 €,
    by at most R (the reserves of its postings), the plan carries the note with that miss. ``proof.py`` keeps the plan
    unproven though the wide search closed: without its rule this reads ``optimal_proven``."""
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415

    cash, price, units, reserve_cents = _ZERO_BAND_CASES[case]
    scenario = _cash_band_scenario("zero-band", cash, price, R(2000), R(2000))
    view = build_exact_policy_view(scenario)
    assert evaluate_exact_candidate(scenario, view, _candidate(view, {cases.buy_decision("asset:b"): units})).feasible, "PREMISE: a plan meets the band"

    compiled = _spy_compile(monkeypatch)
    result = planner.plan_exact_scenario(scenario, solver_time_budget_seconds=10).result
    assert compiled == [False, True], "the prudent model closed infeasible, the wide one was solved"
    assert (result.result_state, result.proof.kind, result.stop_reason) == ("ready_incumbent", "not_proven", "completed")
    final = next(row.final_value for row in result.primary_solution.cash_rows if row.broker_id == cases.BROKER and row.currency == "EUR")
    miss = abs(_fraction(final) - 2000)
    notes = [(issue.path.entity_id, issue.params[0].value.amount) for issue in result.issues if issue.code == _OVERSHOOT_CODE]
    assert notes == ([(f"{cases.BROKER}:EUR", f"{miss:.2f}")] if miss else [])
    assert miss <= Fraction(reserve_cents, 100), "at most R"
    _roundtrip(result)


def test_a_cash_limit_missed_within_its_postings_reserves_is_a_note_beyond_them_a_refusal() -> None:
    """The replay's classification of the wide model's plans (``evaluator.cash_limit_overshoots``). T4, B at 9.995 €: two
    units leave 175.01 €, past a 175 € maximum by a cent. R is one cent: B's debit can round, the 5 € fee cannot. A note.
    Past a 174.99 € maximum by two cents, more than R (though two postings carry a quantum): refused."""
    from backend.app.services.pac_allocator.evaluation.errors import ExactReplayRejectedError  # noqa: PLC0415
    from backend.app.services.pac_allocator.evaluation.evaluator import cash_limit_overshoots  # noqa: PLC0415

    two_of_b = {cases.buy_decision("asset:b"): 2}
    scenario = _cash_band_scenario("overshoot", R(200), R(1999, 200), R(0), R(175))
    view = build_exact_policy_view(scenario)
    (overshoot,) = cash_limit_overshoots(scenario, evaluate_exact_candidate(scenario, view, _candidate(view, two_of_b)))
    assert (overshoot.broker_id, overshoot.currency, overshoot.side, overshoot.amount, overshoot.reserved_postings) == (cases.BROKER, "EUR", "maximum", R(1, 100), 1)

    scenario = _cash_band_scenario("overshoot", R(200), R(1999, 200), R(0), R(17499, 100))
    view = build_exact_policy_view(scenario)
    with pytest.raises(ExactReplayRejectedError):
        cash_limit_overshoots(scenario, evaluate_exact_candidate(scenario, view, _candidate(view, two_of_b)))


def _y_plan_scenario(minimum, maximum):
    """The consultant's case Y on a scenario: 29.99 € in the cell, B and C at 9.995 € in whole units, the band given."""
    return cases.scenario(
        "y-band",
        holdings={"asset:b": R(480), "asset:c": R(480)},
        cash=R(2999, 100),
        weights={"asset:b": cases.HALF, "asset:c": cases.HALF},
        prices={"asset:b": R(1999, 200), "asset:c": R(1999, 200)},
        whole_units=frozenset({"asset:b", "asset:c"}),
        cash_entries=(pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=None if minimum is None else pac_models.ExactLimit(kind="amount", value=minimum), maximum=pac_models.ExactLimit(kind="amount", value=maximum), weight=R(0)),),
    )


@pytest.mark.parametrize("minimum", [pytest.param(None, id="maximum-0"), pytest.param(R(0), id="band-0-0")])
def test_a_cash_limit_is_read_after_the_top_up_is_added(minimum) -> None:
    """Lot ZB-c of project 67 (contract §6.2, specification §16.16 p. 3): case Y spends 29.99 € and posts 30.00 €, the cell
    at −0.01 € and a top-up of 0.01 €. Once the cent is added the cell is at 0.00 €, inside a band 0–0 as inside a maximum
    of 0: the plan carries the top-up alone, never also «limit exceeded». The same plan reads the same under both bands."""
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415

    result = planner.plan_exact_scenario(_y_plan_scenario(minimum, R(0)), solver_time_budget_seconds=10).result
    assert (result.result_state, result.proof.kind) == ("ready_incumbent", "not_proven")
    assert [(row.broker_id, row.amount) for row in result.primary_solution.rounding_top_ups] == [(cases.BROKER, "0.01")]
    assert not [issue for issue in result.issues if issue.code == _OVERSHOOT_CODE]
    _roundtrip(result)


def test_a_cash_limit_still_missed_after_the_top_up_keeps_its_note_with_what_is_still_missing() -> None:
    """The plan of case Y replayed against a band 0.005–0.005 €: the cell posts −0.01 €, the top-up adds 0.01 €, and the cell
    is still 0.005 € under its minimum. The note stays, with what is still missing, in whole cents rounded up (0.01 €);
    the allowance is unchanged: the two debits that round keep a cent each."""
    from backend.app.services.pac_allocator.evaluation.evaluator import cash_limit_overshoots, rounding_top_ups  # noqa: PLC0415

    plan = {cases.buy_decision("asset:b"): 1, cases.buy_decision("asset:c"): 1}
    scenario = _y_plan_scenario(R(1, 200), R(1, 200))
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, plan))
    top_ups = rounding_top_ups(scenario, evaluation, tolerated=frozenset({"ENTRY_VALUE_WITHIN_LIMITS"}))
    assert [(row.broker_id, row.amount) for row in top_ups] == [(cases.BROKER, R(1, 100))], "PREMISE: a top-up of a cent"
    (overshoot,) = cash_limit_overshoots(scenario, evaluation, top_ups)
    assert (overshoot.side, overshoot.amount) == ("minimum", R(1, 100))

    scenario = _y_plan_scenario(R(0), R(0))
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, plan))
    assert cash_limit_overshoots(scenario, evaluation, rounding_top_ups(scenario, evaluation, tolerated=frozenset({"ENTRY_VALUE_WITHIN_LIMITS"}))) == ()


def test_a_plan_of_the_wide_model_that_misses_a_cash_limit_by_its_rounding_is_published_with_the_note(monkeypatch) -> None:
    """End to end: 200 € in the cell, held to exactly 175 €; B at 9.995 € in whole units, A by the euro capped at 4 €. No
    plan posts 175.00 € (the grid below says so); two units of B post 175.01 €, their exact cash 175.01 € inside the wide
    model's band (175.00 € once B's reserve is taken). The cascade on the wide model, the replay and the output union all
    carry it: published, not proven, with the note «exceeded by 0.01 EUR» on the cash entry."""
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415
    from backend.app.services.pac_allocator.evaluation.economics import final_cash_by_cell  # noqa: PLC0415
    from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index  # noqa: PLC0415

    scenario = _cash_band_scenario("overshoot-e2e", R(200), R(1999, 200), R(175), R(175), caps={"asset:a": R(4)})
    view = build_exact_policy_view(scenario)
    index = build_scenario_index(scenario)
    posted = set()
    for units in range(0, 4):
        for euros in range(0, 5):
            evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, {cases.buy_decision("asset:b"): units, cases.buy_decision("asset:a"): euros}))
            posted.add(final_cash_by_cell(index, evaluation.ledgers)[(cases.BROKER, "EUR")])
    assert R(175) not in posted and R(17501, 100) in posted, "PREMISE: no plan posts 175.00 €; two units of B post 175.01 €"

    compiled = _spy_compile(monkeypatch)
    result = planner.plan_exact_scenario(scenario, solver_time_budget_seconds=10).result
    assert compiled == [False, True]
    assert (result.result_state, result.proof.kind) == ("ready_incumbent", "not_proven")
    (note,) = [issue for issue in result.issues if issue.code == _OVERSHOOT_CODE]
    assert (note.severity, note.kind, note.path.section, note.path.entity_kind, note.path.entity_id) == ("warning", "constraint", "targets", "cash", f"{cases.BROKER}:EUR")
    assert [(param.kind, param.name, param.value.amount, param.value.currency) for param in note.params] == [("money", "exceeded_by", "0.01", "EUR")]
    _roundtrip(result)


def test_a_plan_the_prudent_model_holds_never_reaches_the_wide_model(monkeypatch) -> None:
    """Unchanged where the prudent model has a plan: the limits hold to the cent, and the wide model is never compiled."""
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415

    compiled = _spy_compile(monkeypatch)
    result = planner.plan_exact_scenario(_cash_band_scenario("wide-band", R(200), R(1999, 200), R(150), R(175)), solver_time_budget_seconds=10).result
    assert compiled == [False]
    assert result.result_state == "ready_incumbent" and not [issue for issue in result.issues if issue.code == _OVERSHOOT_CODE]
    final = next(row.final_value for row in result.primary_solution.cash_rows if row.broker_id == cases.BROKER and row.currency == "EUR")
    assert 150 <= _fraction(final) <= 175


def test_a_cash_band_no_plan_can_reach_stays_proven_infeasible_by_the_outer_model(monkeypatch) -> None:
    """The cell moves by whole euros (A by the euro, B at 10 €, the 5 € fee) and must end at exactly 2 003.50 €, 18 000 €
    away: no plan exists. The prudent model's «infeasible» is checked on the outer model, with no margin and the reserves
    on the side that admits every plan the replay could accept; that one is infeasible too, so the proof stands."""
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415

    compiled = _spy_compile(monkeypatch)
    scenario = _cash_band_scenario("unreachable-band", R(2000500, 100), R(10), R(200350, 100), R(200350, 100))
    result = planner.plan_exact_scenario(scenario, solver_time_budget_seconds=10).result
    assert compiled == [False, True], "the outer model is solved after the prudent one closed infeasible"
    assert result.proof.kind == "infeasibility_proven"
    _roundtrip(result)


def _fixed_feasible(program, view: ExactPolicyView, quanta: dict[str, int]) -> bool:
    """Whether ``quanta``, fixed in ``program``'s model, is feasible there (its first stage solved to optimal)."""
    for access in view.decisions:
        variable = program.variables.quanta[access.decision_id]
        program.model.chgVarLb(variable, quanta.get(access.decision_id, 0))
        program.model.chgVarUb(variable, quanta.get(access.decision_id, 0))
    program.model.setObjective(program.objective_stages[0].expression, "minimize")
    program.model.optimize()
    return program.model.getStatus() == "optimal"


# Plans the replay accepts exactly on a boundary the prudent model refuses: B's debit at 9.995 € rounds up a half cent, so
# its exact cash is half a cent above what the replay posts (one unit of B and the 5 € fee).
_WIDE_BOUNDARIES = {
    "a cell spent to zero": (R(15), R(0), R(1000)),  # 15 − 5 − 10.00 = 0.00 posted; 0.005 exact
    "cash exactly on its maximum": (R(200), R(0), R(185)),  # 185.00 posted, 185.005 exact
    "cash exactly on its minimum": (R(200), R(185), R(1000)),  # 185.00 posted, 185.005 exact
}


@pytest.mark.parametrize("case", sorted(_WIDE_BOUNDARIES))
def test_the_wide_model_holds_a_plan_on_a_boundary_the_prudent_one_refuses(case: str) -> None:
    """Each row of the wide model reads the cell on the side that admits: ``ledger_nonnegative`` and a minimum the highest
    cash the replay can post (the reserves back in), a maximum the lowest. One unit of B lands each case exactly on its
    boundary; the replay accepts it, the prudent model refuses it, the wide one must hold it. Moving any reserve to the
    other side of its row turns one case red."""
    cash, minimum, maximum = _WIDE_BOUNDARIES[case]
    scenario = _cash_band_scenario("wide-boundary", cash, R(1999, 200), minimum, maximum)
    view = build_exact_policy_view(scenario)
    one_of_b = {cases.buy_decision("asset:b"): 1}
    assert evaluate_exact_candidate(scenario, view, _candidate(view, one_of_b)).feasible, "PREMISE: the replay accepts it"
    assert not _fixed_feasible(compile_policy_program(scenario, view), view, one_of_b), "PREMISE: the prudent model refuses it"
    assert _fixed_feasible(compile_policy_program(scenario, view, outer=True), view, one_of_b)


def test_the_outer_model_holds_every_plan_the_replay_publishes() -> None:
    """The wide model's «infeasible» is a proof only if it holds every plan the replay accepts. T4 with a 150–175 € cash band
    and B at 9.995 €: every count of B units and A euros the replay accepts, fixed in the wide model, is feasible there.
    (Plans that need a rounding top-up, cash the user adds, are outside the claim: see the checkpoint of lot ZB.)"""
    scenario = _cash_band_scenario("outer-holds", R(200), R(1999, 200), R(150), R(175))
    view = build_exact_policy_view(scenario)
    accepted = 0
    for units in range(0, 6):
        for euros in (0, 1, 7):
            quanta = {cases.buy_decision("asset:b"): units, cases.buy_decision("asset:a"): euros}
            if not evaluate_exact_candidate(scenario, view, _candidate(view, quanta)).feasible:
                continue
            accepted += 1
            assert _fixed_feasible(compile_policy_program(scenario, view, outer=True), view, quanta), f"{units} units of B and {euros} € of A"
    assert accepted >= 6, "PREMISE: several plans are accepted"


def test_a_plan_of_the_wide_model_the_replay_refuses_is_no_plan_found_never_a_failure(monkeypatch) -> None:
    """The wide model admits plans the replay may refuse beyond a rounding (SCIP's tolerance on rows with no margin). Such a
    plan is «no plan found», not proven, its search completed: never an error, never a proof, and no note."""
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415
    from backend.app.services.pac_allocator.evaluation.errors import ExactReplayRejectedError  # noqa: PLC0415

    compiled = _spy_compile(monkeypatch)
    real_overshoots = planner.cash_limit_overshoots

    def refuse_on_the_wide_path(scenario, evaluation, top_ups=()):
        if compiled and compiled[-1]:
            raise ExactReplayRejectedError("refused for the test")
        return real_overshoots(scenario, evaluation, top_ups)

    monkeypatch.setattr(planner, "cash_limit_overshoots", refuse_on_the_wide_path)
    cash, price, _, _ = _ZERO_BAND_CASES["far, B rounds"]
    result = planner.plan_exact_scenario(_cash_band_scenario("zero-band", cash, price, R(2000), R(2000)), solver_time_budget_seconds=10).result
    assert (result.result_state, result.proof.kind, result.stop_reason) == ("ready_no_incumbent", "not_proven", "completed")
    assert not [issue for issue in result.issues if issue.code == _OVERSHOOT_CODE]
    _roundtrip(result)


@pytest.mark.parametrize("two_cells", [pytest.param(False, id="one-cell"), pytest.param(True, id="two-cells")])
def test_a_wide_plan_that_needs_a_top_up_is_published_with_it(two_cells: bool, monkeypatch) -> None:
    """Lot ZB-b of project 67, the consultant's case Y (``_reb_small_requests.y_top_up``): one unit of each Asset costs
    29.99 € exact, all the cash, and posts 30.00 €. The prudent model refuses it, the wide model holds it, and the replay
    asks a top-up of 0.01 €. The plan is published, not proven, with its top-up. With one cash cell the portfolio has no
    cash left after the plan: the result must still be built (it raised from the exposure rows), and roundtrip strictly."""
    from backend.app.services.pac_allocator.planner import plan_rebalancing  # noqa: PLC0415
    from backend.test_scripts.test_services import _reb_small_requests as reb  # noqa: PLC0415

    compiled = _spy_compile(monkeypatch)
    result = plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(reb.y_top_up(two_cells=two_cells)), solver_time_budget_seconds=10)
    assert compiled == [False, True], "the prudent model closed infeasible, the wide one was solved"
    assert (result.result_state, result.proof.kind) == ("ready_incumbent", "not_proven")
    assert [(row.broker_id, row.currency, row.amount) for row in result.primary_solution.rounding_top_ups] == [(reb.BROKER, "EUR", "0.01")]
    assert sorted(row.asset_id for row in result.primary_solution.order_rows) == ["asset-b", "asset-c"]
    _roundtrip(result)


_TOP_UP_GRID_PRICES = {"two rounding": (R(1999, 200), R(1999, 200)), "one rounding": (R(1999, 200), R(10))}
_TOP_UP_GRID_LIMITS = {"max 0": (None, R(0)), "min=max=0": (R(0), R(0)), "min=max=0.01": (R(1, 100), R(1, 100))}


@pytest.mark.parametrize("limits", sorted(_TOP_UP_GRID_LIMITS))
@pytest.mark.parametrize("cents", [2998, 2999, 3000])
@pytest.mark.parametrize("prices", sorted(_TOP_UP_GRID_PRICES))
def test_around_case_y_a_request_never_raises_and_its_result_roundtrips(prices: str, cents: int, limits: str) -> None:
    """Lot ZB-b: around the consultant's case Y (one unit of two Assets, each order with its 5 € fee, spending the cash to
    the cent), with one or two Assets whose price rounds, the cash a cent below, at, or above the exact spend, and three
    cash bands. Whatever the engine answers (a plan with or without a top-up or a note, or «impossible»), it never raises,
    and the result roundtrips strictly. Measured on 17/11: no case raises. Since lot ZB-c the limit is read after the top-up,
    so at 29.99 € with a 0–0 band the plan carries the 0.01 € top-up alone, as with a maximum of 0."""
    from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_OUTPUT_ADAPTER  # noqa: PLC0415
    from backend.app.services.pac_allocator import planner  # noqa: PLC0415

    price_b, price_c = _TOP_UP_GRID_PRICES[prices]
    lowest, highest = _TOP_UP_GRID_LIMITS[limits]
    entry = pac_models.ExactCashEntry(broker_id=cases.BROKER, currency="EUR", minimum=None if lowest is None else pac_models.ExactLimit(kind="amount", value=lowest), maximum=pac_models.ExactLimit(kind="amount", value=highest), weight=R(0))
    scenario = cases.scenario(
        "around-y",
        holdings={"asset:b": R(480), "asset:c": R(480)},
        cash=R(cents, 100),
        weights={"asset:b": cases.HALF, "asset:c": cases.HALF},
        prices={"asset:b": price_b, "asset:c": price_c},
        whole_units=frozenset({"asset:b", "asset:c"}),
        cash_entries=(entry,),
    )
    result = planner.plan_exact_scenario(scenario, solver_time_budget_seconds=5).result
    assert result.result_state in {"ready_incumbent", "ready_no_op", "ready_infeasible", "ready_no_incumbent"}
    assert REBALANCER_TOOL_OUTPUT_ADAPTER.validate_json(REBALANCER_TOOL_OUTPUT_ADAPTER.dump_json(result), strict=True) == result


def _fraction(money) -> Fraction:
    from backend.app.schemas.pac_allocator.exact import money_fraction  # noqa: PLC0415

    return money_fraction(money)


def _roundtrip(result) -> None:
    """The result survives the Rebalancer's output union, as JSON, strictly."""
    from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_OUTPUT_ADAPTER  # noqa: PLC0415

    assert REBALANCER_TOOL_OUTPUT_ADAPTER.validate_json(REBALANCER_TOOL_OUTPUT_ADAPTER.dump_json(result), strict=True) == result
