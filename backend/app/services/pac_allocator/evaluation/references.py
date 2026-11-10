"""Constraint and objective references of a policy view: the canonical catalogue of every rule the replay checks and every objective it scores."""

from __future__ import annotations

from backend.app.services.pac_allocator.evaluation.keys import asset_broker_key, entity_refs, fx_debit_key
from backend.app.services.pac_allocator.evaluation.reachability import buy_pool_currencies
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
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            key = fx_debit_key(route.route_id, currency)
            route_refs = entity_refs(
                ("order_route", route.route_id),
                ("currency", currency),
            )
            refs.extend(
                (
                    _constraint_ref(
                        code="FX_DEBIT_CREDIT_COUPLED",
                        key=key,
                        scope="order_route",
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
                        scope="order_route",
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
                        scope="order_route",
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
                        scope="order_route",
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
            (
                "ORDER_REQUIRED_MIN",
                "route required_minimum",
                "allocation.required_min_notional_unfunded",
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
        if purpose == "sell_extension" and route.side == "sell":
            refs.append(
                _constraint_ref(
                    code="SELL_ELIGIBLE",
                    key=route.route_id,
                    scope="order_route",
                    entity_refs=route_refs,
                    unit=boolean_unit,
                    bound_source="frozen invest-only baseline",
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
                    public_issue_code="allocation.required_buy_sell_conflict",
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
                bound_source="current and final invested value",
                public_issue_code=("portfolio_rebalancer.nonpositive_current_portfolio"),
            )
        )
    if purpose == "sell_extension":
        refs.append(
            _constraint_ref(
                code="SELL_FUNDS_INCREMENTAL_BUY",
                key="global",
                scope="scenario",
                entity_refs=(),
                unit=boolean_unit,
                bound_source="frozen baseline and incremental BUY",
                public_issue_code="portfolio_rebalancer.sell_to_idle_forbidden",
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
    return (
        "fixed_l2",
        "shortfall",
        "turnover",
        "explicit_cost",
        "active_order_rows",
    )


def _objective_unit(
    scenario: ExactPlannerScenario,
    code: ExactObjectiveCode,
) -> ExactUnit:
    if code == "fixed_l2":
        return ExactUnit(
            kind="valuation_money_squared",
            currency_code=scenario.valuation_currency,
        )
    if code in {
        "shortfall",
        "turnover",
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
