"""Wire projection for PAC planner results (Step 3, Stage 5a).

Maps the exact domain — an ``ExactPlannerScenario`` plus the
``ExactEvaluation`` produced by replaying a candidate, plus ``solver.py``'s
floating evidence and ``proof.py``'s conclusion — onto the frozen wire
contract of the ``schemas/pac_allocator/`` package.

**This module computes no economics.** Every figure it publishes already
exists, exact, on the evaluation; its job is to re-express those figures in
wire form and to assemble them into the shapes the schema validators accept.
The one place it does arithmetic is the exposure projection, and even there
it only aggregates quantities the solve already decided (see
``build_exposure_rows``).

Scope: the rows both Tools share, and the PAC's own. What only the Rebalancer
publishes (the items on ``F``, the transfers, the plan accounts, the score) is
projected by ``rebalancer_report``, which reuses the shared builders here.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from backend.app.schemas.pac_allocator.base import PlannerNonNegativeMoneyInput, PlannerPositiveMoneyInput
from backend.app.schemas.pac_allocator.evidence import CanonicalKeyUnit, CountUnit, OrdinalPenaltyUnit, ReportedFloatingSolverEvidence, SolverSettingEvidence, SolverStageEvidence, SolverToleranceEvidence, ValuationMoneySquaredUnit, ValuationMoneyUnit
from backend.app.schemas.pac_allocator.exact import AvailableExactNumber, ExactFxRate, ExactMoney, UnavailableExactNumber
from backend.app.schemas.pac_allocator.request import ContributionFundingSourceRef, CurrencySpec, DomainCopyProvenance, ExistingCashFundingSourceRef, ManualProvenance, PlannerProvenance
from backend.app.schemas.pac_allocator.results import PacScenarioBasis, PlannerResultSnapshot
from backend.app.schemas.pac_allocator.rows import (
    ExactEconomicQuantity,
    MonetaryAmountInstruction,
    ObjectiveStageResult,
    PacAssetPlanRow,
    PacCashEntryRow,
    PacExposurePlanRow,
    PlannerAccountingSummary,
    PlannerBuyOrderRow,
    PlannerCatalogAsset,
    PlannerCatalogBroker,
    PlannerCatalogs,
    PlannerConversion,
    PlannerCostTotals,
    PlannerCurrencyCash,
    PlannerFundingAction,
    PlannerLedgerRow,
    PlannerMoneyLost,
    PlannerObjectiveResults,
    PlannerPlanAccounts,
    PlannerRoundingTopUp,
    PlannerScenarioCounts,
    TieBreakResult,
    WholeQuantityInstruction,
)
from backend.app.services.pac_allocator.evaluation.economics import final_cash_by_cell
from backend.app.services.pac_allocator.evaluation.limits import plan_reference, resolve_scenario_limits
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index, exact_scenario_fingerprint
from backend.app.services.pac_allocator.models import (
    ExactAsset,
    ExactEvaluation,
    ExactFxEvaluation,
    ExactPlannerScenario,
    ExactPolicyView,
    ExactRoundingTopUp,
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
    return PacScenarioBasis(**scenario_basis_fields(scenario, evaluation))


def scenario_basis_fields(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> dict:
    """The fields of the scenario basis both Tools share; the Rebalancer adds its own (``rebalancer_report``)."""
    accounting = evaluation.accounting
    if accounting is None:
        raise ValueError("scenario basis requires an evaluation that produced accounting")
    currency = scenario.valuation_currency
    capability_count = sum(len(broker.capabilities) for broker in scenario.brokers)
    return {
        "as_of": scenario.as_of_date.isoformat(),
        "valuation_currency": currency,
        "policy": scenario.policy,
        "counts": PlannerScenarioCounts(
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
        "current_invested": _money(accounting.current_invested, currency),
        "selected_funding": _money(accounting.selected_funding, currency),
        "reachable_funding": _money(accounting.reachable_funding, currency),
        "trapped_funding": _money(accounting.trapped_funding, currency),
        "fixed_reference": _money(accounting.fixed_reference, currency),
    }


def _money(value: ExactRatio, currency: str) -> ExactMoney:
    return ExactMoney(value=ratio_to_exact_number(value), currency=currency)


def _declared_weight(asset: ExactAsset, dimension: str) -> ExactRatio:
    """Total exposure weight this asset declares in one dimension.

    ``normalize.py`` validates each exposure's range, the uniqueness of
    ``(dimension, category)`` and that a dimension never totals more than one
    (``allocation.exposure_total_exceeds_one``), but never requires it to
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
    ``validate_weight_availability`` admits exactly two worlds per dimension:
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
    bounds = resolve_scenario_limits(scenario, plan_reference(scenario, accounting)).assets()
    rows: list[PacAssetPlanRow] = []
    for row in evaluation.assets:
        limit = bounds.get(row.asset_id)
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
                minimum=_money(limit.minimum, currency) if limit is not None and limit.minimum is not None else None,
                maximum=_money(limit.maximum, currency) if limit is not None and limit.maximum is not None else None,
            )
        )
    return rows


def build_cash_rows(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> list[PacCashEntryRow]:
    """One row per cash entry that carries a limit: the cell's final spendable cash in the valuation currency, and its limits.

    The value is the one the replay checks the limit against (``ENTRY_VALUE_WITHIN_LIMITS``): the cell's ``final_spendable``,
    valued with the scenario's own rates.
    """
    accounting = _require_accounting(evaluation)
    currency = scenario.valuation_currency
    index = build_scenario_index(scenario)
    bounds = resolve_scenario_limits(scenario, plan_reference(scenario, accounting)).cash()
    final_by_cell = final_cash_by_cell(index, evaluation.ledgers)
    return [
        PacCashEntryRow(
            broker_id=broker_id,
            currency=cell_currency,
            final_value=_money(final_by_cell.get((broker_id, cell_currency), _EXACT_ZERO), currency),
            minimum=_money(limit.minimum, currency) if limit.minimum is not None else None,
            maximum=_money(limit.maximum, currency) if limit.maximum is not None else None,
        )
        for (broker_id, cell_currency), limit in sorted(bounds.items())
    ]


def build_funding_actions(scenario: ExactPlannerScenario, evaluation: ExactEvaluation, sequence: _SequenceAllocator) -> list[PlannerFundingAction]:
    """Project posted funding transfers.

    ``sequence`` comes from a single allocator shared with the conversion and
    order builders: the schema requires each section to be sequence-ordered
    *and* every action id and sequence to be unique across the sections, so a
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


def _conversion_id(action: ExactFxEvaluation) -> str:
    return f"conversion:{action.broker_id}:{action.source_currency}:{action.destination_currency}"


def build_conversions(scenario: ExactPlannerScenario, evaluation: ExactEvaluation, sequence: _SequenceAllocator) -> list[PlannerConversion]:
    """One conversion per engine FX decision: the engine decides FX once per Broker and ordered currency pair (A2).

    The credit lands in the Broker's cash in the destination currency, which every order of that Broker in that currency
    shares, so the pair is what the plan presents. ``destination_credit`` publishes the **posted** credit, not the exact one:
    the ledger identity reconciles on posted amounts (an exact 9.504 USD credit posts as 10). ``spread_loss`` by contrast is an
    economic cost and stays exact, matching ``_evaluate_costs``. ``evaluation.fx`` is already in canonical (Broker, source,
    destination) order and holds each pair once (``ExactEvaluation`` refuses duplicates). Manual conversions take the next
    sequences of the shared counter, provisionally: ``planner._executable_steps`` renumbers every step in an order the
    balances can follow (``plan_sequence``). Automatic ones happen when a step spends their currency and carry none. The
    provenance is the Broker's: a conversion has no route of its own (D12).
    """
    broker_by_id = {broker.broker_id: broker for broker in scenario.brokers}
    conversions: list[PlannerConversion] = []
    for exact in evaluation.fx:
        broker = broker_by_id[exact.broker_id]
        conversions.append(
            PlannerConversion(
                conversion_id=_conversion_id(exact),
                mode=broker.conversion_mode,
                sequence=sequence.next() if broker.conversion_mode == "manual" else None,
                broker_id=exact.broker_id,
                source_debit=_positive_money(exact.source_debit, exact.source_currency),
                destination_credit=_positive_money(exact.posted_destination_credit, exact.destination_currency),
                spot_rate=ExactFxRate(source_currency=exact.source_currency, destination_currency=exact.destination_currency, value=ratio_to_exact_number(exact.approved_rate)),
                effective_rate=ExactFxRate(source_currency=exact.source_currency, destination_currency=exact.destination_currency, value=ratio_to_exact_number(exact.effective_rate)),
                spread_loss=_money(exact.spread_loss, scenario.valuation_currency),
                provenance_ids=_canonical_provenance_ids({broker.provenance_id}, context=f"conversion {exact.broker_id!r} {exact.source_currency}->{exact.destination_currency}", asset_ids=()),
            )
        )
    return conversions


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

    Every amount field is a **posted** amount, which is why the schema's own
    identity (``initial_selected + funding_in + fx_credit + gross_sell_credit −
    ...``) reconciles without any rounding term, and why each one terminates
    and goes out as fixed-decimal text. ``rounding_delta`` is the exception: it
    carries the *raw* posted-minus-exact residue, is informational only, and
    goes out as an exact number, because the exact credit of a conversion at
    the reciprocal of a stored rate (USD → EUR at 1/1.085) need not terminate,
    and then neither does the residue. Note that the identically-named field
    on ``PlannerAccountingSummary`` maps from a *different* source (see
    ``build_accounting``); the shared name is a trap, not a hint.
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
                transfer_in=ratio_to_fixed_decimal(ledger.transfer_in),
                transfer_out=ratio_to_fixed_decimal(ledger.transfer_out),
                fx_debit=ratio_to_fixed_decimal(ledger.fx_debit),
                fx_credit=ratio_to_fixed_decimal(ledger.fx_credit),
                buy_debit=ratio_to_fixed_decimal(ledger.buy_debit),
                gross_sell_credit=ratio_to_fixed_decimal(ledger.gross_sell_credit),
                buy_fees=ratio_to_fixed_decimal(ledger.buy_fees),
                sell_fees=ratio_to_fixed_decimal(ledger.sell_fees),
                broker_withheld_tax=ratio_to_fixed_decimal(ledger.broker_withheld_tax),
                # The engine posts no foreign withholding yet (C2 of project 67 adds the posting family): the column is zero until then.
                foreign_withholding_tax=ratio_to_fixed_decimal(_EXACT_ZERO),
                self_reserved_tax=ratio_to_fixed_decimal(ledger.self_reserved_tax),
                rounding_delta=ratio_to_exact_number(ledger.raw_rounding_delta),
                final_spendable=ratio_to_fixed_decimal(ledger.final_spendable),
                final_physical=ratio_to_fixed_decimal(ledger.final_physical),
            )
        )
    return rows


def build_rounding_top_ups(scenario: ExactPlannerScenario, top_ups: tuple[ExactRoundingTopUp, ...]) -> list[PlannerRoundingTopUp]:
    """Project the classifier's rounding top-ups, in the order it gave them.

    ``evaluator.rounding_top_ups`` decided every figure, the valuation
    included: the amount goes out as fixed-decimal text in the pool's own
    currency, the valuation as exact money in the valuation currency.
    """
    return [
        PlannerRoundingTopUp(
            broker_id=top_up.broker_id,
            currency=top_up.currency,
            amount=ratio_to_fixed_decimal(top_up.amount),
            rounded_postings=top_up.rounded_postings,
            valuation_amount=_money(top_up.valuation_amount, scenario.valuation_currency),
        )
        for top_up in top_ups
    ]


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
        # No foreign withholding is posted yet (see ``build_ledger_rows``): the line is zero until C2.
        foreign_withholding_tax=_money(_EXACT_ZERO, currency),
    )


def build_plan_accounts(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> PlannerPlanAccounts:
    """The plan's accounts (contract §6.1), the same for both Tools: ``F``, ``W``, the money lost by entry, ``N``, all read off
    B1's exact accounting and costs. The entries are the exact costs and the rounding adjustment, whose sum is ``F − W`` by the
    identity ``ExactAccountingEvaluation`` checks. In the PAC ``N`` is the shortfall plus the trapped cash."""
    accounting = _require_accounting(evaluation)
    costs = evaluation.costs
    if costs is None:
        raise ValueError("plan accounts require an evaluation that produced costs")
    currency = scenario.valuation_currency
    return PlannerPlanAccounts(
        initial_wealth=_money(accounting.initial_wealth, currency),
        final_wealth=_money(accounting.final_wealth, currency),
        money_lost=PlannerMoneyLost(
            buy_fees=_money(costs.buy_fees, currency),
            sell_fees=_money(costs.sell_fees, currency),
            fx_spread_loss=_money(costs.fx_spread_loss, currency),
            execution_margin_cost=_money(costs.execution_margin_loss, currency),
            broker_withheld_tax=_money(costs.broker_withheld_tax, currency),
            self_reserved_tax=_money(costs.self_reserved_tax, currency),
            # No foreign withholding is posted yet (C2 of project 67): the entry is zero until then.
            foreign_withholding_tax=_money(_EXACT_ZERO, currency),
            rounding=_money(accounting.rounding_adjustment + accounting.identity_delta, currency),
        ),
        uninvested=_money(accounting.uninvested, currency),
        final_cash=_money(accounting.final_wealth - accounting.final_invested, currency),
        cash_by_currency=build_cash_by_currency(scenario, evaluation),
    )


def build_cash_by_currency(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> list[PlannerCurrencyCash]:
    """The plan's cash currency by currency, each in its own (TL-5 of project 67, contract §6.1): at the start the cash chosen
    on every Broker plus the contributions declared; at the end the spendable balance of every Broker's ledger plus the
    contributions' part not deposited (a deposit is already in the ledger's ``funding_in``). A currency with no cash at
    either end has no row; the valuation currency comes first, then the others by code."""
    initial: dict[str, ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    final: dict[str, ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    unused: dict[str, ExactRatio] = defaultdict(lambda: _EXACT_ZERO)
    for cash in scenario.existing_cash:
        initial[cash.selected.currency] += cash.selected.amount
    for contribution in scenario.contributions:
        initial[contribution.amount.currency] += contribution.amount.amount
    for ledger in evaluation.ledgers:
        final[ledger.currency] += ledger.final_spendable
    for source in evaluation.funding_sources:
        if source.source_kind == "contribution":
            unused[source.currency] += source.remaining
            final[source.currency] += source.remaining
    shown = {code for code in (*initial, *final) if initial[code] != _EXACT_ZERO or final[code] != _EXACT_ZERO}
    valuation = scenario.valuation_currency
    return [PlannerCurrencyCash(currency=code, initial=_money(initial[code], code), final=_money(final[code], code), unused_contributions=_money(unused[code], code)) for code in sorted(shown, key=lambda code: (code != valuation, code))]


def build_objective_results(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation) -> PlannerObjectiveResults:
    """Project the objective cascade plus the canonical tie-break vector.

    Stage order comes from the view's own ascending ``ordinal``, never a
    hardcoded list, matching ``objectives.py`` and the order in which
    ``planner.py`` hands the objectives to ``proof.conclude_with_solver``.
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
    """One dense 1-based counter shared by the funding/conversion/order builders.

    The schema requires every action id *and* every sequence to be unique
    across the sections while each section stays internally ordered, so
    independent counters would collide on the first row.
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

    **One fact about the tie stages does need a row, so the PAC borrows one.**
    The wire accepts a limit ``stop_reason`` only when some row is
    ``unfinished`` (``_validate_stop_evidence``). When every named stage
    finished but a tie-break stage did not, no row could say so, and the result
    would fail validation. So when any tie-break stage is ``unfinished``, the
    named row with the highest ordinal is reported ``unfinished`` as well; its
    numbers stay the ones SCIP reported. The Rebalancer borrows none: its
    canonical vector is an entry of ``score.tie_breaks``, which the stop rule
    reads.

    **The absolute gap is recomputed, exactly.** The schema checks
    ``absolute_gap >= |primal - dual|`` in exact arithmetic on the published
    texts, and SCIP's float gap, printed on its own, can fall just short of
    that. Whenever both bounds are published, the gap is their exact distance
    instead (``_published_gap``).
    """
    unit_by_code = {ref.code: ref.unit for ref in view.objectives}
    # The Rebalancer's canonical vector has its own entry in ``score.tie_breaks`` (B3 of project 67): no row is borrowed.
    tie_unfinished = scenario.product != "rebalancer" and any(report.status == "unfinished" and report.objective_code not in unit_by_code for report in result.stages)
    last_ordinal = max((report.ordinal for report in result.stages if report.objective_code in unit_by_code), default=None)
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
        # SCIP minimizes ``scale ×`` the objective (D2 of the step-2 plan of project 67): the evidence publishes the
        # objective's own unit, the one of its value, so the bounds are divided by the stage's scale here and only here.
        scale = float(report.scale)
        primal = _float_text(None if report.primal is None else report.primal / scale)
        dual = _float_text(None if report.dual is None else report.dual / scale)
        stages.append(
            SolverStageEvidence(
                kind="reported_floating",
                stage=report.stage,
                objective_code=report.objective_code,
                ordinal=report.ordinal,
                status="unfinished" if tie_unfinished and report.ordinal == last_ordinal else report.status,
                scope=report.scope,
                sense=report.sense,
                unit=_objective_unit(unit_by_code[report.objective_code], scenario.valuation_currency),
                primal=primal,
                dual=dual,
                absolute_gap=_published_gap(primal, dual, None if report.absolute_gap is None else report.absolute_gap / scale),
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
    to re-derive it from the validator. An ``infeasible`` first stage is a
    verdict, not an interruption, so it ends a ``completed`` search.

    Which *limit* stopped a run is read from the stage that actually stopped,
    never assumed to be the clock: the first ``unfinished`` stage that SCIP
    did not close. After a limit the later stages still run inside pins
    nobody proved, and SCIP may close them (``optimal``), so their status says
    nothing about why the search stopped. If that stage reports ``nodelimit``
    the answer is ``node_limit``; anything else — the clock, or a budget spent
    before the stage could run — is ``time_limit``.

    **This field is also the plan's reproducibility statement**, which is worth
    stating because nothing in its name says so. SCIP's search is deterministic
    here — ``randomseedshift``/``permutationseed``/``lpseed`` are all 0 and no
    concurrent solve is enabled — so what varies between runs is *how much of
    the lexicographic cascade completes*: each stage gets all of the remaining
    budget (stage 1 keeps a reserve back for the stages after a limit, which
    split what is left; see ``solver.py``), and the cascade is what makes the
    answer unique. Therefore:

    - ``completed`` — every stage finished, the total order was fully applied,
      and the same input yields the same plan on any machine.
    - ``time_limit`` / ``node_limit`` — a stage stopped on a limit, and *which*
      stage, and how far the later ones got, depends on machine speed. The plan
      is valid and replayed in exact arithmetic, but **it is not guaranteed to
      be reproducible**.

    Measured 2026-09-22 at the real 30 000 ms engine budget. Since D-X1 every
    plan reaches the solver; on that date ``planner.py`` still routed views of
    up to 200 000 candidates to the exhaustive oracle, which is why the grid
    below was taken on scenarios large enough to reach SCIP.

    The cost driver is **the number of decisions, not the size of the domain**.
    Holding decisions fixed at 4 while growing the domain from 256 to
    584 968 183 800 candidates leaves the solve at ~6-11 ms and a single node;
    growing decisions from 2 to 16 at a fixed cap makes it climb linearly. A
    single node means the continuous relaxation already lands on the integer
    optimum, which is a property of how few decisions there are — not of how
    large the domain is.

    The search tree does open, and where matters:

    ```
    50 decisions     243 ms    0.8% of budget     1 node
    60 decisions     760 ms    2.5%              19 nodes
    80 decisions   7 128 ms   23.8%              82 nodes
    ```

    The knee is therefore **between 50 and 60 decisions** — measured at both
    ends, not interpolated, and worth re-probing at finer steps if anyone
    re-runs this grid.

    In portfolio terms that is **not** a fixed number of assets, because one
    asset costs between 1 and 4 decisions:

    ```
    1 currency, 1 cash source        1.0/asset     knee at ~55 assets
    multiple funding sources         1.5/asset     knee at ~36 assets
    multi-currency (buy+fund+fx)     3.0/asset     knee at ~18 assets   <- ordinary
    2 routes + 2 funding sources     4.0/asset     knee at ~14 assets
    ```

    **Read the 3.0 row, not the range.** An asset priced in a currency the cash
    is not held in costs three decisions — `buy_quantum` + `funding_transfer` +
    `fx_debit` — so a European investor holding EUR and buying USD-denominated
    ETFs is in that row by construction, not by misfortune. It is the ordinary
    case, and ~18 assets is an ordinary PAC. The extremes above and below are
    there to show the ratio is not fixed, not to suggest the midpoint.

    Reproducibility survives the knee: at 80 decisions, 3 runs give 85/85 stages
    and one distinct candidate, at 7.6-8.1 s. The cascade still completes, so
    ``completed`` still means what it says — it just costs a quarter of the
    budget instead of a thousandth.

    **Corrected 2026-10-06: brokers that sell the same asset bring the knee
    far below this grid.** The grid gave every asset a single route. When an
    asset can be bought at two brokers, the search must also choose between
    routes that cost nearly the same, and that choice, not the number of
    decisions, drives the cost: 5 assets with 2 brokers each closed stage 1
    only after 22-24 s of the 30 s budget, and 10 such assets never closed it,
    while the same 10 assets with one broker each took 85 ms (measured
    2026-10-05 and 2026-10-06, on a loaded machine). So size a scenario in
    assets x brokers, not in assets, and do not read the table above as a
    promise.
    """
    # D4: a tie-break whose plan the exact comparison rejected was closed by SCIP; no limit stopped the search there.
    unfinished = [stage for stage in result.stages if stage.status == "unfinished" and not stage.rejected]
    if not unfinished:
        return "completed"
    deciding = next((stage for stage in unfinished if stage.scip_status != "optimal"), None)
    return "node_limit" if deciding is not None and "nodelimit" in deciding.scip_status else "time_limit"


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


def _published_gap(primal: str | None, dual: str | None, absolute_gap: float | None) -> str | None:
    """The absolute gap of one evidence row: exact whenever both bounds are published.

    The solver measures the gap as the float ``abs(primal - dual)``
    (``solver._observe``), and each of the three numbers is then published as
    its own shortest text. The schema checks ``absolute_gap >= |primal - dual|``
    exactly, on those texts, and the float gap can print just below the exact
    distance: 7.965 - 7.770482487229448 is 0.194517512770552, while the float
    gap prints as 0.19451751277055163. So the gap is recomputed from the two
    published texts in exact rational arithmetic: the solver's definition
    without the float rounding, and without a Decimal context that would round
    a difference longer than 28 digits. Without both bounds there is nothing to
    subtract, and the solver's own number (absent in practice) is kept.

    A difference longer than the wire's 96 characters raises in
    ``ratio_to_fixed_decimal`` instead of being rounded; that needs the two
    bounds some 80 orders of magnitude apart.
    """
    if primal is None or dual is None:
        return _float_text(absolute_gap, nonnegative=True)
    return ratio_to_fixed_decimal(abs(ExactRatio.from_decimal(Decimal(primal)) - ExactRatio.from_decimal(Decimal(dual))))


def _decimal_text(value: Decimal) -> str:
    """Positional, canonical decimal text (no exponent, no trailing zeros).

    A zero of any sign or exponent is «0»: the wire pattern refuses «-0», and a
    solver's -0.0 is the same observation as 0.0.
    """
    if value.is_zero():
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
