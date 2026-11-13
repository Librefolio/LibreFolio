"""Constraint and objective references of a policy view: the canonical catalogue of every rule the replay checks and every objective it scores."""

from __future__ import annotations

from backend.app.services.pac_allocator.evaluation.keys import asset_broker_key, entity_refs
from backend.app.services.pac_allocator.evaluation.limits import limited_entries
from backend.app.services.pac_allocator.evaluation.reachability import fx_decision_specs, fx_relay_groups
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex
from backend.app.services.pac_allocator.models import (
    Checkpoint,
    ConstraintRef,
    EntityRef,
    ExactConstraintCode,
    ExactObjectiveCode,
    ExactPlannerScenario,
    ExactPolicyPurpose,
    ExactUnit,
    ObjectiveRef,
    check_budget,
)


def ledger_keys(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
) -> tuple[tuple[str, str], ...]:
    keys = {(cash.broker_id, cash.selected.currency) for cash in scenario.existing_cash}
    keys.update((route.broker_id, route.currency) for route in scenario.funding_routes)
    keys.update((route.broker_id, index.assets[route.asset_id].quote.price.currency) for route in scenario.order_routes)
    for lane in scenario.transfer_lanes:
        keys.update(((lane.source_broker_id, lane.currency), (lane.destination_broker_id, lane.currency)))
    keys.update((limit.broker_id, limit.currency) for limit in scenario.cash_entries)
    return tuple(sorted(keys))


def _constraint_ref(
    *,
    code: ExactConstraintCode,
    key: str,
    scope: str,
    entity_refs: tuple[EntityRef, ...],
    unit: ExactUnit,
    bound_source: str,
    public_issue_code: str | None = None,
) -> ConstraintRef:
    return ConstraintRef(
        ref_id=f"constraint:{code.lower()}:{key}",
        code=code,
        phase="exact",
        scope=scope,
        entity_refs=entity_refs,
        units=(unit,),
        enforcement="solver_and_exact",
        bound_source=bound_source,
        public_issue_code=public_issue_code,
        explanation_key=f"tools.allocation.constraints.{code.lower()}",
    )


def _funding_constraint_refs(
    scenario: ExactPlannerScenario,
    boolean_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    refs: list[ConstraintRef] = []
    for cash in scenario.existing_cash:
        check_budget(checkpoint)
        native = ExactUnit(
            kind="native_money",
            currency_code=cash.selected.currency,
        )
        source_ref = entity_refs(("funding_source", f"existing_cash:{cash.cash_id}"))
        refs.append(
            _constraint_ref(
                code="SELECTED_WITHIN_AVAILABLE",
                key=f"existing_cash:{cash.cash_id}",
                scope="funding_source",
                entity_refs=source_ref,
                unit=native,
                bound_source="existing_cash.available",
                public_issue_code="allocation.cash_selection_invalid",
            )
        )
    source_rows = [
        (
            "existing_cash",
            cash.cash_id,
            cash.selected.currency,
        )
        for cash in scenario.existing_cash
    ]
    source_rows.extend(
        (
            "contribution",
            contribution.contribution_id,
            contribution.amount.currency,
        )
        for contribution in scenario.contributions
    )
    for source_kind, source_id, currency in source_rows:
        check_budget(checkpoint)
        source_ref = entity_refs(("funding_source", f"{source_kind}:{source_id}"))
        native = ExactUnit(kind="native_money", currency_code=currency)
        refs.extend(
            (
                _constraint_ref(
                    code="FUNDING_WITHIN_SELECTED",
                    key=f"{source_kind}:{source_id}",
                    scope="funding_source",
                    entity_refs=source_ref,
                    unit=native,
                    bound_source="selected source amount",
                ),
                _constraint_ref(
                    code="FUNDING_SOURCE_CONSERVATION",
                    key=f"{source_kind}:{source_id}",
                    scope="funding_source",
                    entity_refs=source_ref,
                    unit=native,
                    bound_source="selected = transferred + remaining",
                ),
            )
        )
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        refs.append(
            _constraint_ref(
                code="NO_SELF_TRANSFER",
                key=route.route_id,
                scope="funding_route",
                entity_refs=entity_refs(
                    ("funding_route", route.route_id),
                ),
                unit=ExactUnit(
                    kind="native_money",
                    currency_code=route.currency,
                ),
                bound_source="source Broker identity",
            )
        )
    refs.append(
        _constraint_ref(
            code="NO_DOUBLE_COUNT",
            key="global",
            scope="scenario",
            entity_refs=(),
            unit=boolean_unit,
            bound_source="funding source conservation",
        )
    )
    return refs


def _fx_constraint_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    boolean_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    refs: list[ConstraintRef] = []
    for spec in fx_decision_specs(scenario, index, checkpoint):
        check_budget(checkpoint)
        currency, quote_currency, key, route_refs = spec.source_currency, spec.destination_currency, spec.key, spec.entity_refs
        refs.extend(
            (
                _constraint_ref(
                    code="FX_DEBIT_CREDIT_COUPLED",
                    key=key,
                    scope=spec.scope,
                    entity_refs=route_refs,
                    unit=ExactUnit(
                        kind="native_money",
                        currency_code=quote_currency,
                    ),
                    bound_source="approved rate and global spread",
                ),
                _constraint_ref(
                    code="FX_CREDIT_POSITIVE",
                    key=key,
                    scope=spec.scope,
                    entity_refs=route_refs,
                    unit=ExactUnit(
                        kind="native_money",
                        currency_code=quote_currency,
                    ),
                    bound_source="posted destination credit",
                ),
                _constraint_ref(
                    code="FX_NATIVE_QUANTUM",
                    key=key,
                    scope=spec.scope,
                    entity_refs=route_refs,
                    unit=ExactUnit(
                        kind="native_money",
                        currency_code=currency,
                    ),
                    bound_source="source currency minor unit",
                ),
                _constraint_ref(
                    code="FX_SOURCE_CASH",
                    key=key,
                    scope=spec.scope,
                    entity_refs=route_refs,
                    unit=ExactUnit(
                        kind="native_money",
                        currency_code=currency,
                    ),
                    bound_source="Broker source-currency ledger",
                ),
            )
        )
    return refs


def _fx_relay_constraint_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    """V7: one ref per Broker and currency that both receives and gives a conversion (``FX_NO_RELAY``)."""
    return [
        _constraint_ref(
            code="FX_NO_RELAY",
            key=group.key,
            scope="broker",
            entity_refs=entity_refs(("broker", group.broker_id), ("currency", group.currency)),
            unit=ExactUnit(kind="count"),
            bound_source="a currency that receives a conversion does not give one (V7)",
        )
        for group in fx_relay_groups(fx_decision_specs(scenario, index, checkpoint))
    ]


def _limit_constraint_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    valuation_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    """V5 (``ENTRY_VALUE_WITHIN_LIMITS``) for every entry that carries a limit.

    Nothing is added to a scenario without limits, so its view is what it was before A3.
    """
    refs: list[ConstraintRef] = []
    for entry in limited_entries(scenario):
        check_budget(checkpoint)
        refs.append(
            _constraint_ref(
                code="ENTRY_VALUE_WITHIN_LIMITS",
                key=entry.key,
                scope="asset" if entry.kind == "asset" else "cash",
                entity_refs=entity_refs(("asset", entry.asset_id)) if entry.kind == "asset" else entity_refs(("broker", entry.broker_id), ("currency", entry.currency)),
                unit=valuation_unit,
                bound_source="limits of the entry, resolved on the reference",
            )
        )
    return refs


def _order_constraint_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    purpose: ExactPolicyPurpose,
    boolean_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    refs: list[ConstraintRef] = []
    for route in scenario.order_routes:
        check_budget(checkpoint)
        capability = index.capabilities[(route.broker_id, route.capability_id)]
        quote_currency = index.assets[route.asset_id].quote.price.currency
        native_or_quantity = (
            ExactUnit(kind="asset_quantity", asset_id=route.asset_id)
            if capability.kind == "whole_quantity"
            else ExactUnit(
                kind="native_money",
                currency_code=quote_currency,
            )
        )
        route_refs = entity_refs(
            ("asset", route.asset_id),
            ("broker", route.broker_id),
            ("order_route", route.route_id),
        )
        for code, bound_source, public_issue_code in (
            (
                "ORDER_QUANTIZED",
                "capability order step",
                "allocation.nonpositive_order_amount_step",
            ),
            (
                "ORDER_MIN_IF_ACTIVE",
                "route minimum_if_active",
                "allocation.order_minimum_exceeds_cap",
            ),
            ("ORDER_CAP", "route cap", "allocation.order_cap_nonpositive"),
            ("ORDER_SIDE_ALLOWED", "declared route side", None),
            ("NO_IMPLICIT_ROUTE", "normalized order route", None),
        ):
            unit = boolean_unit if code in {"ORDER_SIDE_ALLOWED", "NO_IMPLICIT_ROUTE"} else native_or_quantity
            refs.append(
                _constraint_ref(
                    code=code,
                    key=route.route_id,
                    scope="order_route",
                    entity_refs=route_refs,
                    unit=unit,
                    bound_source=bound_source,
                    public_issue_code=public_issue_code,
                )
            )
        refs.append(
            _constraint_ref(
                code="FX_RATE_ORDER_SAFE",
                key=route.route_id,
                scope="order_route",
                entity_refs=route_refs,
                unit=boolean_unit,
                bound_source="mid and execution prices",
                public_issue_code="allocation.price_order_invalid",
            )
        )
        if route.side == "sell":
            refs.append(
                _constraint_ref(
                    code="SELL_NET_POSITIVE",
                    key=route.route_id,
                    scope="order_route",
                    entity_refs=route_refs,
                    unit=ExactUnit(
                        kind="native_money",
                        currency_code=quote_currency,
                    ),
                    bound_source="posted gross less posted fee and tax reserve",
                )
            )
        else:
            refs.append(
                _constraint_ref(
                    code="BUY_DEBIT_POSITIVE",
                    key=route.route_id,
                    scope="order_route",
                    entity_refs=route_refs,
                    unit=ExactUnit(
                        kind="native_money",
                        currency_code=quote_currency,
                    ),
                    bound_source="posted BUY cash debit",
                )
            )
    return refs


def _position_constraint_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    boolean_unit: ExactUnit,
    valuation_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    refs: list[ConstraintRef] = []
    for broker_id, currency in ledger_keys(scenario, index):
        check_budget(checkpoint)
        ledger_refs = entity_refs(
            ("broker", broker_id),
            ("currency", currency),
        )
        native = ExactUnit(kind="native_money", currency_code=currency)
        key = f"{broker_id}:{currency}"
        refs.extend(
            (
                _constraint_ref(
                    code="SPENDABLE_CASH_NONNEGATIVE",
                    key=key,
                    scope="broker_currency",
                    entity_refs=ledger_refs,
                    unit=native,
                    bound_source="native ledger",
                ),
                _constraint_ref(
                    code="PHYSICAL_CASH_RECONCILED",
                    key=key,
                    scope="broker_currency",
                    entity_refs=ledger_refs,
                    unit=native,
                    bound_source="spendable plus physical reserves",
                ),
            )
        )
    holding_keys = {(holding.asset_id, holding.broker_id) for holding in scenario.holdings}
    holding_keys.update((route.asset_id, route.broker_id) for route in scenario.order_routes)
    for asset_id, broker_id in sorted(holding_keys):
        check_budget(checkpoint)
        pair_refs = entity_refs(
            ("asset", asset_id),
            ("broker", broker_id),
        )
        unit = ExactUnit(kind="asset_quantity", asset_id=asset_id)
        key = asset_broker_key(asset_id, broker_id)
        refs.extend(
            (
                _constraint_ref(
                    code="FINAL_QUANTITY_NONNEGATIVE",
                    key=key,
                    scope="asset_broker",
                    entity_refs=pair_refs,
                    unit=unit,
                    bound_source="holding conservation",
                ),
                _constraint_ref(
                    code="SELL_WITHIN_INVENTORY",
                    key=key,
                    scope="asset_broker",
                    entity_refs=pair_refs,
                    unit=unit,
                    bound_source="exact planning quantity",
                    public_issue_code=("portfolio_rebalancer.sell_inventory_exceeded"),
                ),
            )
        )
    for asset in scenario.assets:
        check_budget(checkpoint)
        asset_refs = entity_refs(("asset", asset.asset_id))
        refs.extend(
            (
                _constraint_ref(
                    code="FINAL_VALUE_NONNEGATIVE",
                    key=asset.asset_id,
                    scope="asset",
                    entity_refs=asset_refs,
                    unit=valuation_unit,
                    bound_source="final exact holding value",
                ),
                _constraint_ref(
                    code="NO_ASSET_BUY_AND_SELL",
                    key=asset.asset_id,
                    scope="asset",
                    entity_refs=asset_refs,
                    unit=boolean_unit,
                    bound_source="active order sides",
                ),
            )
        )
    return refs


def _global_constraint_refs(
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    boolean_unit: ExactUnit,
    valuation_unit: ExactUnit,
    checkpoint: Checkpoint | None,
) -> list[ConstraintRef]:
    check_budget(checkpoint)
    refs: list[ConstraintRef] = []
    global_specs = (
        ("ROUTE_DECLARED", boolean_unit, "candidate decision domain"),
        ("COST_NOT_INVESTMENT", boolean_unit, "mid-value accounting"),
        ("SELL_POSTED_ONCE", boolean_unit, "closed posting families"),
        ("ROUNDING_BOUND", valuation_unit, "active monetary postings"),
        ("ACCOUNTING_IDENTITY", valuation_unit, "fixed-reference identity"),
        ("NO_SHORT_OR_LEVERAGE", boolean_unit, "native ledgers and holdings"),
    )
    for code, unit, bound_source in global_specs:
        refs.append(
            _constraint_ref(
                code=code,
                key="global",
                scope="scenario",
                entity_refs=(),
                unit=unit,
                bound_source=bound_source,
            )
        )
    if scenario.product == "rebalancer":
        refs.append(
            _constraint_ref(
                code="REBALANCER_NONEMPTY",
                key="global",
                scope="scenario",
                entity_refs=(),
                unit=valuation_unit,
                bound_source="current invested value",
                public_issue_code=("portfolio_rebalancer.nonpositive_current_portfolio"),
            )
        )
    return refs


def build_constraint_refs(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    purpose: ExactPolicyPurpose,
    checkpoint: Checkpoint | None,
) -> tuple[ConstraintRef, ...]:
    boolean_unit = ExactUnit(kind="boolean")
    valuation_unit = ExactUnit(
        kind="valuation_money",
        currency_code=scenario.valuation_currency,
    )
    refs = _funding_constraint_refs(
        scenario,
        boolean_unit,
        checkpoint,
    )
    refs.extend(
        _fx_constraint_refs(
            scenario,
            index,
            boolean_unit,
            checkpoint,
        )
    )
    refs.extend(_fx_relay_constraint_refs(scenario, index, checkpoint))
    refs.extend(_limit_constraint_refs(scenario, index, valuation_unit, checkpoint))
    refs.extend(
        _order_constraint_refs(
            scenario,
            index,
            purpose,
            boolean_unit,
            checkpoint,
        )
    )
    refs.extend(
        _position_constraint_refs(
            scenario,
            index,
            boolean_unit,
            valuation_unit,
            checkpoint,
        )
    )
    refs.extend(
        _global_constraint_refs(
            scenario,
            purpose,
            boolean_unit,
            valuation_unit,
            checkpoint,
        )
    )
    return tuple(sorted(refs, key=lambda item: item.ref_id))


def _objective_codes(
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
) -> tuple[ExactObjectiveCode, ...]:
    if purpose == "deployment":
        return (
            "shortfall",
            "fixed_l2",
            "incremental_cost",
            "incremental_order_rows",
        )
    if scenario.policy == "proportional":
        return (
            "fixed_l2",
            "shortfall",
            "route_priority",
            "explicit_cost",
            "active_order_rows",
        )
    if scenario.policy == "min_fragmentation":
        return (
            "fixed_l2",
            "shortfall",
            "split_asset_count",
            "active_order_rows",
            "route_priority",
            "explicit_cost",
        )
    # The Rebalancer (specifica §6.3): a weighted fidelity is one score, «Target first» the distance then the money lost.
    # Then the tie-breaks of specifica §6.4, which choose only among plans equal on what precedes them.
    tie_breaks: tuple[ExactObjectiveCode, ...] = ("operation_count", "route_priority")
    if scenario.target_fidelity is not None and scenario.target_fidelity.kind == "target_first":
        return ("target_distance", "wealth_loss", *tie_breaks)
    return ("plan_score", *tie_breaks)


def _objective_unit(
    scenario: ExactPlannerScenario,
    code: ExactObjectiveCode,
) -> ExactUnit:
    if code in {"fixed_l2", "target_distance"}:
        return ExactUnit(
            kind="valuation_money_squared",
            currency_code=scenario.valuation_currency,
        )
    if code in {
        "shortfall",
        "plan_score",
        "wealth_loss",
        "explicit_cost",
        "incremental_cost",
    }:
        return ExactUnit(
            kind="valuation_money",
            currency_code=scenario.valuation_currency,
        )
    if code in {
        "split_asset_count",
        "active_order_rows",
        "incremental_order_rows",
        "operation_count",
    }:
        return ExactUnit(kind="count")
    return ExactUnit(kind="ordinal_penalty")


def build_objective_refs(
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
) -> tuple[ObjectiveRef, ...]:
    result = []
    for ordinal, code in enumerate(
        _objective_codes(scenario, purpose),
        start=1,
    ):
        result.append(
            ObjectiveRef(
                ref_id=f"objective:{ordinal:02d}:{code}",
                code=code,
                ordinal=ordinal,
                sense="min",
                unit=_objective_unit(scenario, code),
                freeze_rule="exact_nonworsening_bound",
                report_field=code,
                closure_rule="exact_ratio_equality",
            )
        )
    return tuple(result)
