"""Wire projection for PAC planner results (Step 3, Stage 5a).

Maps the exact domain — an ``ExactPlannerScenario`` plus the
``ExactEvaluation`` produced by replaying a candidate, plus ``solver.py``'s
floating evidence and ``proof.py``'s conclusion — onto the frozen wire
contract in ``schemas/pac_allocator.py``.

**This module computes no economics.** Every figure it publishes already
exists, exact, on the evaluation; its job is to re-express those figures in
wire form and to assemble them into the shapes the schema validators accept.
The one place it does arithmetic is the exposure projection, and even there
it only aggregates quantities the solve already decided (see
``build_exposure_rows``).

Scope: PAC only. ``plan_rebalancing`` deliberately does not exist yet — every
Rebalancer policy and the SELL verifier are deferred, and a function that
exists but always fails is worse than an absent one because it invites
wiring, whereas an absent one fails at import in the exact place the missing
work is obvious.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from backend.app.schemas.pac_allocator import (
    AvailableExactNumber,
    CanonicalKeyUnit,
    ContributionFundingSourceRef,
    CountUnit,
    CurrencySpec,
    DomainCopyProvenance,
    ExactEconomicQuantity,
    ExactFxRate,
    ExactMoney,
    ExistingCashFundingSourceRef,
    ManualProvenance,
    MonetaryAmountInstruction,
    ObjectiveStageResult,
    OrdinalPenaltyUnit,
    PacAssetPlanRow,
    PacExposurePlanRow,
    PacScenarioBasis,
    PlannerAccountingSummary,
    PlannerBuyOrderRow,
    PlannerCatalogAsset,
    PlannerCatalogBroker,
    PlannerCatalogs,
    PlannerCostTotals,
    PlannerFundingAction,
    PlannerFxAction,
    PlannerLedgerRow,
    PlannerNonNegativeMoneyInput,
    PlannerObjectiveResults,
    PlannerPositiveMoneyInput,
    PlannerProvenance,
    PlannerResultSnapshot,
    PlannerScenarioCounts,
    ReportedFloatingSolverEvidence,
    SolverSettingEvidence,
    SolverStageEvidence,
    SolverToleranceEvidence,
    TieBreakResult,
    UnavailableExactNumber,
    ValuationMoneySquaredUnit,
    ValuationMoneyUnit,
    WholeQuantityInstruction,
)
from backend.app.services.pac_allocator.evaluator import exact_scenario_fingerprint
from backend.app.services.pac_allocator.models import (
    ExactAsset,
    ExactEvaluation,
    ExactPlannerScenario,
    ExactPolicyView,
)
from backend.app.services.pac_allocator.numeric import ExactRatio
from backend.app.services.pac_allocator.solver import SolverRunResult
from backend.app.services.pac_allocator.wire_numbers import ratio_to_exact_number, ratio_to_fixed_decimal, ratio_to_price

__all__ = [
    "UNCATEGORISED_EXPOSURE_CATEGORY_ID",
    "UNCATEGORISED_EXPOSURE_LABEL",
    "ExposureProvenanceError",
    "build_exposure_rows",
    "build_planner_catalogs",
    "build_planner_provenance",
    "build_result_snapshot",
    "build_scenario_basis",
]

_EXACT_ZERO = ExactRatio(0)
_EXACT_ONE = ExactRatio(1)

# The residual exposure slice's identity. A consumer must be able to
# recognise it *structurally* — by this id — rather than by matching a display
# string, which would break under localisation. Nothing cross-validates
# exposure category ids (``PlannerCatalogs`` carries assets, brokers and
# currencies only), so this sentinel is the contract.
#
# The label is deliberately shaped so it cannot be mistaken for a real
# category name coming from a data provider. Localising it for display is the
# frontend's job: the backend publishes a stable identity, not UI copy.
UNCATEGORISED_EXPOSURE_CATEGORY_ID = "allocation.uncategorised"
UNCATEGORISED_EXPOSURE_LABEL = "Uncategorised"

_EXPOSURE_DIMENSIONS = ("asset_type", "sector", "geography")


class ExposureProvenanceError(ValueError):
    """Raised when a residual exposure row would have no provenance at all.

    ``PacExposurePlanRow.provenance_ids`` is ``min_length=1``, so pydantic
    would reject an empty list anyway — but it would do so late and opaquely,
    pointing at a row rather than at the assets that caused it. This exists to
    make the diagnosis legible, exactly like ``LedgerPostingScopeError``: the
    guard is for the error message, not for an escape that was open.
    """


def _timestamp_text(value: datetime) -> str:
    """Render a timezone-aware datetime as the wire's UTC timestamp text."""
    return value.astimezone(tz=None).isoformat().replace("+00:00", "Z") if value.tzinfo is None else value.isoformat().replace("+00:00", "Z")


def build_result_snapshot(scenario: ExactPlannerScenario, view: ExactPolicyView) -> PlannerResultSnapshot:
    """Project the snapshot identity plus the verified scenario fingerprint.

    ``request_fingerprint`` is documented as emitted *only after* internal
    view and scenario-fingerprint verification, so this re-checks the view
    against the scenario rather than trusting that some earlier caller did.
    ``evaluate_exact_candidate`` performs the same check, but this function
    can be reached independently and the field's contract is explicit about
    the precondition.
    """
    fingerprint = exact_scenario_fingerprint(scenario)
    if view.scenario_fingerprint != fingerprint:
        raise ValueError("policy view scenario fingerprint does not match the scenario; refusing to publish a request fingerprint")
    return PlannerResultSnapshot(snapshot_id=scenario.snapshot.snapshot_id, request_fingerprint=fingerprint)


def build_planner_catalogs(scenario: ExactPlannerScenario) -> PlannerCatalogs:
    """Project the Asset/Broker/currency catalogs the result rows reference."""
    return PlannerCatalogs(
        assets=[PlannerCatalogAsset(asset_id=asset.asset_id, name=asset.name, ticker=asset.ticker, asset_class=asset.asset_class) for asset in scenario.assets],
        brokers=[PlannerCatalogBroker(broker_id=broker.broker_id, name=broker.name) for broker in scenario.brokers],
        currencies=[CurrencySpec(currency=spec.currency, minor_unit=ratio_to_fixed_decimal(spec.minor_unit)) for spec in scenario.currency_specs],
    )


def build_planner_provenance(scenario: ExactPlannerScenario) -> list[PlannerProvenance]:
    """Project every root provenance record the scenario carries.

    Publishes the scenario's whole provenance list rather than a "used only"
    subset. That is faithful to the field's own description — *root provenance
    records referenced by every copied or manually supplied fact* — and it
    also makes the containment rule at ``_validate_ready_solution`` total by
    construction: any id any row references is necessarily present. A filtered
    list would turn that rule into a conditional failure that only appears on
    scenarios with unusual row/provenance combinations.
    """
    records: list[PlannerProvenance] = []
    for item in scenario.provenance:
        if item.kind == "manual":
            records.append(ManualProvenance(kind="manual", provenance_id=item.provenance_id, label=item.label or item.provenance_id, entered_at=_timestamp_text(item.entered_at)))
        else:
            records.append(
                DomainCopyProvenance(
                    kind="domain_copy",
                    provenance_id=item.provenance_id,
                    domain=item.domain,
                    source_ref=item.source_ref,
                    source_label=item.source_label,
                    captured_at=_timestamp_text(item.captured_at),
                )
            )
    return records


def build_scenario_basis(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> PacScenarioBasis:
    """Project the scenario-level accounting basis and its object counts."""
    accounting = evaluation.accounting
    if accounting is None:
        raise ValueError("scenario basis requires an evaluation that produced accounting")
    currency = scenario.valuation_currency
    capability_count = sum(len(broker.capabilities) for broker in scenario.brokers)
    return PacScenarioBasis(
        as_of=scenario.as_of_date.isoformat(),
        valuation_currency=currency,
        policy=scenario.policy,
        counts=PlannerScenarioCounts(
            assets=len(scenario.assets),
            brokers=len(scenario.brokers),
            currencies=len(scenario.currency_specs),
            holdings=len(scenario.holdings),
            existing_cash=len(scenario.existing_cash),
            contributions=len(scenario.contributions),
            funding_routes=len(scenario.funding_routes),
            capabilities=capability_count,
            fx_rates=len(scenario.fx_rates),
            order_routes=len(scenario.order_routes),
            provenance=len(scenario.provenance),
        ),
        current_invested=_money(accounting.current_invested, currency),
        selected_funding=_money(accounting.selected_funding, currency),
        reachable_funding=_money(accounting.reachable_funding, currency),
        trapped_funding=_money(accounting.trapped_funding, currency),
        fixed_reference=_money(accounting.fixed_reference, currency),
    )


def _money(value: ExactRatio, currency: str) -> ExactMoney:
    return ExactMoney(value=ratio_to_exact_number(value), currency=currency)


def _declared_weight(asset: ExactAsset, dimension: str) -> ExactRatio:
    """Total exposure weight this asset declares in one dimension.

    ``normalize.py`` validates each exposure's range and the uniqueness of
    ``(dimension, category)`` but never requires a per-asset dimension to
    close, so this legitimately returns less than one — an asset declaring 60%
    Tech and nothing else contributes the remaining 40% to the residual.
    """
    total = _EXACT_ZERO
    for exposure in asset.exposures:
        if exposure.dimension == dimension:
            total = total + exposure.weight
    return total


def _canonical_provenance_ids(ids: set[str], *, context: str, asset_ids: tuple[str, ...]) -> list[str]:
    """Deduplicate and canonically order a row's provenance references.

    ``_validate_ready_solution`` enforces per-row uniqueness, and several
    assets legitimately share one ``market_data`` or ``portfolio`` record, so
    a naive concatenation across contributors would raise. Sorting also makes
    the row byte-reproducible across runs rather than merely valid today.
    """
    if not ids:
        raise ExposureProvenanceError(f"{context} has no provenance to reference; contributing assets: {', '.join(asset_ids) or '(none)'}")
    return sorted(ids)


def build_exposure_rows(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> list[PacExposurePlanRow]:
    """Project exposure tables that **close to exactly one, by identity**.

    The schema leaves far less freedom here than it first appears, and the
    validator — not the type union — is the specification.
    ``_validate_weight_availability`` admits exactly two worlds per dimension:
    with a zero denominator *every* weight must be unavailable carrying
    ``zero_final_invested``, and otherwise *every* weight must be available,
    in ``[0, 1]``, and the dimension must **sum to exactly one**. So neither
    "mark the uncovered part unavailable" nor "let the dimension sum to less
    than one" is emittable: the unavailable branch is rejected outright
    whenever the denominator is nonzero, and a short sum is rejected in both
    branches. ``target_weight`` must close unconditionally.

    Rather than omit the dimension or publish an empty table — both valid and
    both silent, leaving a consumer unable to tell "not computed" from "no
    exposure" — the uncategorised remainder is published as its own category
    row under ``UNCATEGORISED_EXPOSURE_CATEGORY_ID``. That keeps every real
    category's weight *true* (an asset that is genuinely half the portfolio
    still reads 0.5) and turns the gap from an absence a UI must infer into a
    named fact it can render.

    Closure is an **identity, never a normalisation**:

        Σ_categories (Σ_assets w·e) + Σ_assets w·(1 − Σ_categories e)
            = Σ_assets w = 1

    so the rows sum to one because the algebra says so, not because anything
    was rescaled. Rescaling is forbidden precisely because it would convert a
    data-quality gap into an invisible one. The identity is asserted in exact
    arithmetic below.

    The rule is uniform, with no special case for a dimension nobody declared:
    that emits the residual alone at weight one. Suppressing the dimension
    exactly when the data is at its worst would invert the signal, and a
    special case is where this would rot first.
    """
    accounting = evaluation.accounting
    if accounting is None:
        raise ValueError("exposure projection requires an evaluation that produced accounting")

    final_value_by_asset = {row.asset_id: row.final_value for row in evaluation.assets}
    target_weight_by_asset = {row.asset_id: row.target_weight for row in evaluation.assets}
    final_invested = accounting.final_invested

    rows: list[PacExposurePlanRow] = []
    for dimension in _EXPOSURE_DIMENSIONS:
        rows.extend(_exposure_rows_for_dimension(scenario, dimension, target_weight_by_asset, final_value_by_asset, final_invested))
    return rows


def _exposure_rows_for_dimension(
    scenario: ExactPlannerScenario,
    dimension: str,
    target_weight_by_asset: dict[str, ExactRatio],
    final_value_by_asset: dict[str, ExactRatio],
    final_invested: ExactRatio,
) -> list[PacExposurePlanRow]:
    zero_denominator = final_invested == _EXACT_ZERO

    target_by_category: dict[str, ExactRatio] = {}
    final_by_category: dict[str, ExactRatio] = {}
    label_by_category: dict[str, str] = {}
    provenance_by_category: dict[str, set[str]] = {}
    assets_by_category: dict[str, list[str]] = {}

    residual_target = _EXACT_ZERO
    residual_final = _EXACT_ZERO
    residual_provenance: set[str] = set()
    residual_assets: list[str] = []

    for asset in scenario.assets:
        target_weight = target_weight_by_asset.get(asset.asset_id, _EXACT_ZERO)
        final_value = final_value_by_asset.get(asset.asset_id, _EXACT_ZERO)
        final_share = _EXACT_ZERO if zero_denominator else final_value / final_invested

        for exposure in asset.exposures:
            if exposure.dimension != dimension:
                continue
            category = exposure.category
            target_by_category[category] = target_by_category.get(category, _EXACT_ZERO) + target_weight * exposure.weight
            final_by_category[category] = final_by_category.get(category, _EXACT_ZERO) + final_share * exposure.weight
            label_by_category.setdefault(category, exposure.label)
            provenance_by_category.setdefault(category, set()).add(exposure.provenance_id)
            assets_by_category.setdefault(category, []).append(asset.asset_id)

        undeclared = _EXACT_ONE - _declared_weight(asset, dimension)
        if undeclared == _EXACT_ZERO:
            continue
        residual_target = residual_target + target_weight * undeclared
        residual_final = residual_final + final_share * undeclared
        residual_assets.append(asset.asset_id)
        # A derived row cannot own a provenance record: `PlannerProvenance` is
        # `manual | domain_copy` with no `derived` kind and no authorship
        # field, so the union can only reference the records of the facts this
        # number consumed. The asset's own quote is exactly that — the fact
        # its weight was computed from. Minting a `ManualProvenance` to stand
        # for the missing classification would be a fabrication: an absent
        # declaration is not a manually supplied fact.
        residual_provenance.add(asset.quote.provenance_id)
        residual_provenance.update(exposure.provenance_id for exposure in asset.exposures if exposure.dimension == dimension)

    if not target_by_category and residual_target == _EXACT_ZERO and residual_final == _EXACT_ZERO and not residual_assets:
        return []

    categories = sorted(set(target_by_category) | set(final_by_category))
    rows: list[PacExposurePlanRow] = []
    for category in categories:
        rows.append(
            _exposure_row(
                dimension=dimension,
                category_id=category,
                label=label_by_category.get(category, category),
                target_weight=target_by_category.get(category, _EXACT_ZERO),
                final_weight=final_by_category.get(category, _EXACT_ZERO),
                zero_denominator=zero_denominator,
                provenance_ids=_canonical_provenance_ids(
                    provenance_by_category.get(category, set()),
                    context=f"{dimension} exposure category {category!r}",
                    asset_ids=tuple(assets_by_category.get(category, ())),
                ),
            )
        )

    if residual_assets:
        rows.append(
            _exposure_row(
                dimension=dimension,
                category_id=UNCATEGORISED_EXPOSURE_CATEGORY_ID,
                label=UNCATEGORISED_EXPOSURE_LABEL,
                target_weight=residual_target,
                final_weight=residual_final,
                zero_denominator=zero_denominator,
                provenance_ids=_canonical_provenance_ids(
                    residual_provenance,
                    context=f"{dimension} uncategorised exposure residual",
                    asset_ids=tuple(residual_assets),
                ),
            )
        )

    _require_unit_closure(rows, dimension, zero_denominator)
    return rows


def _exposure_row(
    *,
    dimension: str,
    category_id: str,
    label: str,
    target_weight: ExactRatio,
    final_weight: ExactRatio,
    zero_denominator: bool,
    provenance_ids: list[str],
) -> PacExposurePlanRow:
    # With no final invested value the weight is genuinely undefined rather
    # than merely unknown, which is the one case the unavailable branch is
    # for. `target_weight` still carries a real number: targets do not depend
    # on the denominator, and the schema requires them to close regardless.
    final = UnavailableExactNumber(kind="unavailable", reason="zero_final_invested") if zero_denominator else AvailableExactNumber(kind="available", value=ratio_to_exact_number(final_weight))
    return PacExposurePlanRow(
        dimension=dimension,
        category_id=category_id,
        label=label,
        target_weight=ratio_to_exact_number(target_weight),
        final_weight=final,
        provenance_ids=provenance_ids,
    )


def _require_unit_closure(rows: list[PacExposurePlanRow], dimension: str, zero_denominator: bool) -> None:
    """Assert the closure identity in exact arithmetic before publishing.

    The schema will reject a short vector anyway, but it would do so with a
    message about unit vectors rather than about the derivation that produced
    them. Checking here — on the exact ratios, not on the projected wire text
    — turns a downstream validation failure into a local one that names the
    dimension.
    """
    target_total = sum((_exact_of(row.target_weight) for row in rows), _EXACT_ZERO)
    if target_total != _EXACT_ONE:
        raise ValueError(f"{dimension} exposure targets do not close to one ({target_total.numerator}/{target_total.denominator}); the residual derivation is wrong")
    if zero_denominator:
        return
    final_total = sum((_exact_of(row.final_weight.value) for row in rows), _EXACT_ZERO)
    if final_total != _EXACT_ONE:
        raise ValueError(f"{dimension} final exposure weights do not close to one ({final_total.numerator}/{final_total.denominator}); the residual derivation is wrong")


def _exact_of(value) -> ExactRatio:
    """Read an exact ratio back out of a wire ``ExactNumber`` for the closure check."""
    if value.kind == "finite_decimal":
        return ExactRatio.from_decimal(Decimal(value.value))
    return ExactRatio(int(value.numerator), int(value.denominator))


# --------------------------------------------------------------------------
# Solution rows — pure projections of figures the evaluation already produced
# --------------------------------------------------------------------------


def build_asset_rows(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> list[PacAssetPlanRow]:
    """One authoritative row per catalog Asset.

    ``final_weight`` follows the same two-world rule the exposure tables do
    (`_validate_available_weight_identities`): undefined when nothing is
    invested, a real share otherwise.
    """
    accounting = _require_accounting(evaluation)
    currency = scenario.valuation_currency
    final_invested = accounting.final_invested
    zero_denominator = final_invested == _EXACT_ZERO
    rows: list[PacAssetPlanRow] = []
    for row in evaluation.assets:
        share = UnavailableExactNumber(kind="unavailable", reason="zero_final_invested") if zero_denominator else AvailableExactNumber(kind="available", value=ratio_to_exact_number(row.final_value / final_invested))
        rows.append(
            PacAssetPlanRow(
                asset_id=row.asset_id,
                target_weight=ratio_to_exact_number(row.target_weight),
                target_value=_money(row.target_value, currency),
                final_value=_money(row.final_value, currency),
                residual=_money(row.residual, currency),
                final_weight=share,
                buy_mid_value=_money(row.buy_mid_value, currency),
            )
        )
    return rows


def build_funding_actions(scenario: ExactPlannerScenario, evaluation: ExactEvaluation, sequence: _SequenceAllocator) -> list[PlannerFundingAction]:
    """Project posted funding transfers.

    ``sequence`` comes from a single allocator shared with the FX and order
    builders: the schema requires each section to be sequence-ordered *and*
    every action id and sequence to be unique across all three sections, so a
    per-section counter starting at one would collide.
    """
    provenance_by_route = {route.route_id: route.provenance_id for route in scenario.funding_routes}
    actions: list[PlannerFundingAction] = []
    for transfer in evaluation.funding_transfers:
        source = ExistingCashFundingSourceRef(kind="existing_cash", cash_id=transfer.source_id) if transfer.source_kind == "existing_cash" else ContributionFundingSourceRef(kind="contribution", contribution_id=transfer.source_id)
        actions.append(
            PlannerFundingAction(
                action_id=f"funding:{transfer.route_id}",
                sequence=sequence.next(),
                funding_route_id=transfer.route_id,
                source=source,
                destination_broker_id=transfer.destination_broker_id,
                amount=_positive_money(transfer.amount, transfer.currency),
                reason_code="allocation.fund_declared_orders",
                provenance_ids=_canonical_provenance_ids(
                    {provenance_by_route[transfer.route_id]} | _source_provenance(scenario, transfer.source_kind, transfer.source_id),
                    context=f"funding action for route {transfer.route_id!r}",
                    asset_ids=(),
                ),
            )
        )
    return actions


def build_fx_actions(scenario: ExactPlannerScenario, evaluation: ExactEvaluation, sequence: _SequenceAllocator) -> list[PlannerFxAction]:
    """Project posted FX conversions.

    ``destination_credit`` publishes the **posted** credit, not the exact one:
    the ledger identity reconciles on posted amounts (an exact 9.504 USD
    credit posts as 10), which is the same exact/posted distinction the
    compiled model had to learn in Step3 §16.11. ``spread_loss`` by contrast
    is an economic cost and stays exact, matching ``_evaluate_costs``.
    """
    provenance_by_route = {route.route_id: route.provenance_id for route in scenario.order_routes}
    actions: list[PlannerFxAction] = []
    for action in evaluation.fx:
        actions.append(
            PlannerFxAction(
                action_id=f"fx:{action.order_route_id}:{action.source_currency}",
                sequence=sequence.next(),
                order_route_id=action.order_route_id,
                broker_id=action.broker_id,
                source_debit=_positive_money(action.source_debit, action.source_currency),
                destination_credit=_positive_money(action.posted_destination_credit, action.destination_currency),
                spot_rate=ExactFxRate(source_currency=action.source_currency, destination_currency=action.destination_currency, value=ratio_to_exact_number(action.approved_rate)),
                effective_rate=ExactFxRate(source_currency=action.source_currency, destination_currency=action.destination_currency, value=ratio_to_exact_number(action.effective_rate)),
                spread_loss=_money(action.spread_loss, scenario.valuation_currency),
                provenance_ids=_canonical_provenance_ids(
                    {provenance_by_route[action.order_route_id]},
                    context=f"FX action on route {action.order_route_id!r}",
                    asset_ids=(),
                ),
            )
        )
    return actions


def build_order_rows(scenario: ExactPlannerScenario, evaluation: ExactEvaluation, sequence: _SequenceAllocator) -> list[PlannerBuyOrderRow]:
    """Project posted BUY orders. PAC never emits SELL rows.

    ``cash_debit`` and ``fee`` publish the **posted** amounts (they are what
    the ledger reconciles against); ``mid_value`` and
    ``execution_margin_cost`` are economic figures and stay exact.
    """
    provenance_by_route = {route.route_id: route.provenance_id for route in scenario.order_routes}
    capability_by_route = {route.route_id: _capability_for(scenario, route) for route in scenario.order_routes}
    rows: list[PlannerBuyOrderRow] = []
    for order in evaluation.orders:
        if order.side != "buy":
            raise ValueError(f"PAC results cannot contain a {order.side} order ({order.route_id})")
        capability = capability_by_route[order.route_id]
        rows.append(
            PlannerBuyOrderRow(
                kind="buy",
                order_id=f"order:{order.route_id}",
                sequence=sequence.next(),
                asset_id=order.asset_id,
                broker_id=order.broker_id,
                route_id=order.route_id,
                instruction=_order_instruction(order, capability),
                economic_quantity=ExactEconomicQuantity(kind="exact", value=ratio_to_exact_number(order.economic_quantity), unit="asset_unit"),
                source_price=ratio_to_price(order.source_unit_price, order.source_currency, order.source_quote_base_quantity),
                mid_price=ratio_to_price(order.mid_unit_price, order.native_currency, _EXACT_ONE),
                charge_price=ratio_to_price(order.execution_unit_price, order.native_currency, _EXACT_ONE),
                mid_value=_money(order.mid_value, scenario.valuation_currency),
                execution_margin_cost=_money(order.execution_margin_loss, scenario.valuation_currency),
                cash_debit=_positive_money(order.posted_cash_amount, order.native_currency),
                fee=_nonnegative_money(order.posted_fee, order.native_currency),
                fx_cost=_money(_EXACT_ZERO, scenario.valuation_currency),
                buffer=_nonnegative_money(_EXACT_ZERO, order.native_currency),
                explanation_keys=[],
                provenance_ids=_canonical_provenance_ids(
                    {provenance_by_route[order.route_id], _asset_by_id(scenario, order.asset_id).quote.provenance_id},
                    context=f"order row for route {order.route_id!r}",
                    asset_ids=(order.asset_id,),
                ),
            )
        )
    return rows


def build_ledger_rows(evaluation: ExactEvaluation) -> list[PlannerLedgerRow]:
    """Project Broker×currency ledgers.

    Every field is a **posted** amount, which is why the schema's own identity
    (``initial_selected + funding_in + fx_credit + gross_sell_credit − ...``)
    reconciles without any rounding term. ``rounding_delta`` carries the
    *raw* posted-minus-exact residue and is informational only — note that the
    identically-named field on ``PlannerAccountingSummary`` maps from a
    *different* source (see ``build_accounting``); the shared name is a trap,
    not a hint.
    """
    rows: list[PlannerLedgerRow] = []
    for ledger in evaluation.ledgers:
        rows.append(
            PlannerLedgerRow(
                broker_id=ledger.broker_id,
                currency=ledger.currency,
                initial_selected=ratio_to_fixed_decimal(ledger.initial_selected),
                funding_in=ratio_to_fixed_decimal(ledger.funding_in),
                funding_out=ratio_to_fixed_decimal(ledger.funding_out),
                fx_debit=ratio_to_fixed_decimal(ledger.fx_debit),
                fx_credit=ratio_to_fixed_decimal(ledger.fx_credit),
                buy_debit=ratio_to_fixed_decimal(ledger.buy_debit),
                gross_sell_credit=ratio_to_fixed_decimal(ledger.gross_sell_credit),
                buy_fees=ratio_to_fixed_decimal(ledger.buy_fees),
                sell_fees=ratio_to_fixed_decimal(ledger.sell_fees),
                broker_withheld_tax=ratio_to_fixed_decimal(ledger.broker_withheld_tax),
                self_reserved_tax=ratio_to_fixed_decimal(ledger.self_reserved_tax),
                rounding_delta=ratio_to_fixed_decimal(ledger.raw_rounding_delta),
                final_spendable=ratio_to_fixed_decimal(ledger.final_spendable),
                final_physical=ratio_to_fixed_decimal(ledger.final_physical),
            )
        )
    return rows


def build_accounting(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> PlannerAccountingSummary:
    """Project the accounting summary.

    ``rounding_delta`` maps from ``accounting.rounding_adjustment``, **not**
    from any "raw" field, despite the wire field's description saying "raw".
    The identity decides it, not the name: ``evaluator`` computes
    ``identity_delta = shortfall − (free_cash + physical_reserves +
    economic_losses + rounding_adjustment)`` and the schema requires
    ``shortfall == free_cash + physical_reserves + economic_losses +
    rounding_delta`` together with ``identity_delta == 0``. Only
    ``rounding_adjustment`` closes it.
    """
    accounting = _require_accounting(evaluation)
    currency = scenario.valuation_currency
    return PlannerAccountingSummary(
        current_invested=_money(accounting.current_invested, currency),
        selected_funding=_money(accounting.selected_funding, currency),
        reachable_funding=_money(accounting.reachable_funding, currency),
        trapped_funding=_money(accounting.trapped_funding, currency),
        fixed_reference=_money(accounting.fixed_reference, currency),
        final_invested=_money(accounting.final_invested, currency),
        shortfall=_money(accounting.shortfall, currency),
        free_cash=_money(accounting.free_cash, currency),
        physical_reserves=_money(accounting.physical_reserves, currency),
        economic_losses=_money(accounting.economic_losses, currency),
        rounding_delta=_money(accounting.rounding_adjustment, currency),
        rounding_bound=_money(accounting.rounding_bound, currency),
        identity_delta=_money(accounting.identity_delta, currency),
    )


def build_costs(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> PlannerCostTotals:
    """Project cost totals. Every figure is exact, never posted — costs are
    economic quantities, and ``_evaluate_costs`` sums ``exact_fee`` and
    ``spread_loss`` rather than their posted counterparts.
    """
    costs = evaluation.costs
    if costs is None:
        raise ValueError("cost projection requires an evaluation that produced costs")
    currency = scenario.valuation_currency
    return PlannerCostTotals(
        buy_fees=_money(costs.buy_fees, currency),
        sell_fees=_money(costs.sell_fees, currency),
        fx_spread_loss=_money(costs.fx_spread_loss, currency),
        execution_margin_cost=_money(costs.execution_margin_loss, currency),
        broker_withheld_tax=_money(costs.broker_withheld_tax, currency),
        self_reserved_tax=_money(costs.self_reserved_tax, currency),
    )


def build_objective_results(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation) -> PlannerObjectiveResults:
    """Project the objective cascade plus the canonical tie-break vector.

    Stage order comes from the view's own ascending ``ordinal``, never a
    hardcoded list, matching ``oracle.py`` and ``objectives.py``.
    """
    value_by_ref = {item.ref_id: item.value for item in evaluation.objectives}
    stages = [
        ObjectiveStageResult(
            objective_code=ref.code,
            ordinal=ref.ordinal,
            sense=ref.sense,
            unit=_objective_unit(ref.unit, scenario.valuation_currency),
            value=ratio_to_exact_number(value_by_ref[ref.ref_id]),
        )
        for ref in sorted(view.objectives, key=lambda ref: ref.ordinal)
    ]
    return PlannerObjectiveResults(
        stages=stages,
        tie_break=TieBreakResult(code="canonical_key", unit=CanonicalKeyUnit(kind="canonical_key"), ordered_keys=list(view.tie_breaks[0].decision_ids)),
    )


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


class _SequenceAllocator:
    """One dense 1-based counter shared by the funding/FX/order builders.

    The schema requires every action id *and* every sequence to be unique
    across all three sections while each section stays internally ordered, so
    three independent counters would collide on the first row.
    """

    def __init__(self) -> None:
        self._next = 0

    def next(self) -> int:
        self._next += 1
        return self._next


def _require_accounting(evaluation: ExactEvaluation):
    accounting = evaluation.accounting
    if accounting is None:
        raise ValueError("wire projection requires an evaluation that produced accounting")
    return accounting


def _positive_money(value: ExactRatio, currency: str) -> PlannerPositiveMoneyInput:
    return PlannerPositiveMoneyInput(amount=ratio_to_fixed_decimal(value), currency=currency)


def _nonnegative_money(value: ExactRatio, currency: str) -> PlannerNonNegativeMoneyInput:
    return PlannerNonNegativeMoneyInput(amount=ratio_to_fixed_decimal(value), currency=currency)


def _asset_by_id(scenario: ExactPlannerScenario, asset_id: str) -> ExactAsset:
    for asset in scenario.assets:
        if asset.asset_id == asset_id:
            return asset
    raise KeyError(f"unknown asset {asset_id}")


def _capability_for(scenario: ExactPlannerScenario, route) -> object:
    for broker in scenario.brokers:
        if broker.broker_id != route.broker_id:
            continue
        for capability in broker.capabilities:
            if capability.capability_id == route.capability_id:
                return capability
    raise KeyError(f"unknown capability {route.capability_id} on broker {route.broker_id}")


def _source_provenance(scenario: ExactPlannerScenario, source_kind: str, source_id: str) -> set[str]:
    if source_kind == "existing_cash":
        for cash in scenario.existing_cash:
            if cash.cash_id == source_id:
                return {cash.provenance_id}
    else:
        for contribution in scenario.contributions:
            if contribution.contribution_id == source_id:
                return {contribution.provenance_id}
    raise KeyError(f"unknown funding source {source_kind}:{source_id}")


def _order_instruction(order, capability):
    """Project the broker-facing instruction for one order."""
    if order.capability_kind == "whole_quantity":
        return WholeQuantityInstruction(
            kind="whole_quantity",
            quantity=ratio_to_fixed_decimal(order.order_measure),
            quantity_step=ratio_to_fixed_decimal(capability.order_step),
            unit="asset_unit",
        )
    return MonetaryAmountInstruction(
        kind="monetary_amount",
        amount=_positive_money(order.order_measure, order.native_currency),
        order_amount_step=_positive_money(capability.order_step, order.native_currency),
    )


def _objective_unit(unit, valuation_currency: str):
    """Map an exact objective unit onto the wire's numeric-unit union."""
    if unit.kind == "count":
        return CountUnit(kind="count")
    if unit.kind == "valuation_money":
        return ValuationMoneyUnit(kind="valuation_money", currency_code=unit.currency_code or valuation_currency)
    if unit.kind == "valuation_money_squared":
        return ValuationMoneySquaredUnit(kind="valuation_money_squared", currency_code=unit.currency_code or valuation_currency)
    if unit.kind == "ordinal_penalty":
        return OrdinalPenaltyUnit(kind="ordinal_penalty")
    raise ValueError(f"objective unit kind {unit.kind!r} has no wire numeric-unit projection")


# --------------------------------------------------------------------------
# Solver evidence and proof
# --------------------------------------------------------------------------


def build_solver_evidence(scenario: ExactPlannerScenario, view: ExactPolicyView, result: SolverRunResult) -> ReportedFloatingSolverEvidence:
    """Project the floating, explicitly non-authoritative solver report.

    **Tie stages are filtered out, and that is a schema consequence rather
    than a choice.** ``solver.py`` runs one ``tie:<decision_id>`` stage per
    canonical tie-break entry, but the wire ``ObjectiveCode`` enum has no
    ``tie:*`` member, so those stages simply cannot be expressed here. Worth
    stating explicitly because it is otherwise silent: a reader comparing the
    evidence list against the solver's stage count will see fewer rows and
    could reasonably suspect data loss. They are not lost — the tie-break is
    published separately, exactly once, as ``PlannerObjectiveResults.tie_break``.
    """
    unit_by_code = {ref.code: ref.unit for ref in view.objectives}
    settings = [SolverSettingEvidence(name=setting.name, value=setting.value) for setting in result.settings]
    tolerances = SolverToleranceEvidence(
        feasibility=_tolerance_text(result.tolerances.feasibility),
        integrality=_tolerance_text(result.tolerances.integrality),
        absolute_gap=_tolerance_text(result.tolerances.absolute_gap),
        relative_gap=_tolerance_text(result.tolerances.relative_gap),
    )
    stages = []
    for report in result.stages:
        if report.objective_code not in unit_by_code:
            continue  # a tie:* stage — see the docstring
        stages.append(
            SolverStageEvidence(
                kind="reported_floating",
                stage=report.stage,
                objective_code=report.objective_code,
                ordinal=report.ordinal,
                status=report.status,
                scope=report.scope,
                sense=report.sense,
                unit=_objective_unit(unit_by_code[report.objective_code], scenario.valuation_currency),
                primal=_float_text(report.primal),
                dual=_float_text(report.dual),
                absolute_gap=_float_text(report.absolute_gap, nonnegative=True),
                relative_gap=_float_text(report.relative_gap, nonnegative=True),
                tolerances=tolerances,
                engine=result.engine,
                version=result.version,
                settings=settings,
            )
        )
    return ReportedFloatingSolverEvidence(kind="reported_floating", stages=stages)


def build_stop_reason(result: SolverRunResult) -> str:
    """Map the solver run onto the wire ``stop_reason``.

    Determined, not chosen: ``_validate_stop_evidence`` requires
    ``completed`` **iff** no stage is ``unfinished``, so the only consistent
    mapping is the one below. Recorded here so the next reader does not have
    to re-derive it from the validator. Which *limit* stopped a run is read
    from the stage that actually stopped, never assumed to be the clock.

    **This field is also the plan's reproducibility statement**, which is worth
    stating because nothing in its name says so. SCIP's search is deterministic
    here — ``randomseedshift``/``permutationseed``/``lpseed`` are all 0 and no
    concurrent solve is enabled — so what varies between runs is *how much of
    the lexicographic cascade completes*: each stage gets a wall-clock slice of
    the remaining budget (``solver.py``), and the cascade is what makes the
    answer unique. Therefore:

    - ``completed`` — every stage finished, the total order was fully applied,
      and the same input yields the same plan on any machine.
    - ``time_limit`` / ``node_limit`` — the cascade was truncated, and *where*
      it truncated depends on machine speed. The plan is valid and replayed in
      exact arithmetic, but **it is not guaranteed to be reproducible**.

    Measured 2026-09-21 at the real 30 000 ms engine budget: both reference
    scenarios complete their cascade using 0.016% and 0.009% of it, 8 runs each,
    one distinct candidate. The truncated regime needed budgets around 3 ms to
    reproduce at all — so on current inputs this is a guarantee, not a hope.
    That is a statement about today's inputs, not a theorem: it is exactly what
    the deferred `benchmark capacity` work (Step 3 checklist item 13) is meant
    to probe at scale.
    """
    unfinished = [stage for stage in result.stages if stage.status == "unfinished"]
    if not unfinished:
        return "completed"
    return "node_limit" if any("nodelimit" in stage.scip_status for stage in unfinished) else "time_limit"


def _tolerance_text(value: float) -> str:
    """Render a SCIP tolerance as canonical wire fixed-decimal text.

    Tolerances arrive as floats like ``1e-06``, whose ``repr`` uses
    exponent notation the wire pattern rejects. Converting through
    ``Decimal(str(value))`` and formatting positionally keeps the value the
    engine actually reported while producing text the contract accepts.
    """
    return _decimal_text(Decimal(str(value)))


def _float_text(value: float | None, *, nonnegative: bool = False) -> str | None:
    """Render one floating solver observation, or ``None`` when absent.

    ``None`` is meaningful here and must survive: it is how an unfinished
    stage says it never produced a bound, and ``SolverStageEvidence`` requires
    finished stages to carry all four observations while allowing unfinished
    ones to omit them. Fabricating a zero would turn "not measured" into
    "measured as zero" — the silent degradation this package keeps removing.
    """
    if value is None:
        return None
    text = _decimal_text(Decimal(str(value)))
    if nonnegative and text.startswith("-"):
        # A gap is defined nonnegative; a tiny negative float here is solver
        # noise around zero, not a negative gap.
        return "0"
    return text


def _decimal_text(value: Decimal) -> str:
    """Positional, canonical decimal text (no exponent, no trailing zeros)."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
