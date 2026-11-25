"""Normalize bounded PAC and rebalancing drafts without inventing facts."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from babel.numbers import get_currency_precision

from backend.app.schemas.pac_allocator.base import PlannerIssueCode, PlannerMoneyInput
from backend.app.schemas.pac_allocator.exact import ExactNumber as WireExactNumber
from backend.app.schemas.pac_allocator.exact import ExactRatio as WireExactRatio
from backend.app.schemas.pac_allocator.exact import FiniteDecimal
from backend.app.schemas.pac_allocator.issues import CurrencyIssueParam, IdIssueParam, MoneyIssueParam, PlannerIssue, PlannerIssueParam, PlannerIssuePath, TextIssueParam
from backend.app.schemas.pac_allocator.request import (
    AmountFeeCap,
    ContributionFundingSourceRef,
    DomainAssetIdentity,
    DomainBrokerIdentity,
    DomainCopyProvenance,
    ManualProvenance,
    MonetaryAmountCapability,
    MonetaryAmountMinimum,
    NoOrderCap,
    NotionalOrderCap,
    PacPlannerRequest,
    PlannerFundingRouteInput,
    PlannerOrderRouteInput,
    RebalancerPlannerRequest,
    WholeQuantityCapability,
    WholeQuantityMinimum,
)
from backend.app.services.financial_math.fx_rates import oriented_rate
from backend.app.services.pac_allocator.evaluation.limits import entries_with_limits
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index
from backend.app.services.pac_allocator.issues import (
    PlannerAvailability,
    canonicalize_issues,
    entity_path,
    field_path,
    make_issue,
    normalization_availability,
    normalizer_issue_definition,
    section_path,
)
from backend.app.services.pac_allocator.limits import check_maximum_below_current, check_minimum_above_maximum, check_minimums_exceed_reference, limit_reference_of, trapped_cash_by_cell
from backend.app.services.pac_allocator.models import (
    FIDELITY_LEVEL_WEIGHTS,
    ExactAsset,
    ExactAssetQuote,
    ExactBroker,
    ExactCashEntry,
    ExactContribution,
    ExactCurrencySpec,
    ExactExistingCash,
    ExactExposure,
    ExactFeeSchedule,
    ExactFundingRoute,
    ExactFxRate,
    ExactHolding,
    ExactLimit,
    ExactMoney,
    ExactOrderCap,
    ExactOrderCapability,
    ExactOrderMinimum,
    ExactOrderRoute,
    ExactPlannerScenario,
    ExactProvenance,
    ExactSnapshot,
    ExactTargetFidelity,
    ExactTargetWeight,
    ExactTransferLane,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
)
from backend.app.services.pac_allocator.wire_numbers import ratio_to_display_decimal

# Shared by v2: these were defined inside the P1 block removed on 2026-09-21.
type _PlannerV2Request = PacPlannerRequest | RebalancerPlannerRequest
_RATIO_WIRE_INTEGER_CHARS = 192
# Half a unit of the tenth decimal: the rounding error of an FX rate stored as
# Numeric(24, 10) (``backend/app/db/models.py``, ``FxRate.rate``).
_FX_STORED_RATE_HALF_UNIT = ExactRatio(1, 2 * 10**10)


# The issues that keep a plan from running but not the preview from counting (F3a step 8 of project 67): the weights the
# user is still typing. A ready preview leaves them out of its issues: the screen shows the control total itself.
COUNTED_ANYWAY = frozenset({"allocation.target_total_not_one"})


@dataclass(frozen=True, slots=True)
class PlannerV2NormalizationResult:
    """The normalizer's answer. ``limit_problems`` are the three cross checks of the limits (M1, T12) that made it
    ``invalid`` (they are in ``issues`` too), and ``counted`` the scenario they were found on: the preview counts on it
    (B4, consultant's Q2), the plan never reads it."""

    availability: PlannerAvailability
    issues: tuple[PlannerIssue, ...]
    normalized: ExactPlannerScenario | None
    limit_problems: tuple[PlannerIssue, ...] = ()
    counted: ExactPlannerScenario | None = None

    @property
    def ready(self) -> bool:
        return self.availability == "ready"

    @property
    def scenario(self) -> ExactPlannerScenario | None:
        return self.normalized


def exact_number_to_ratio(value: WireExactNumber) -> ExactRatio:
    """Map a validated public exact number without float or Decimal rounding."""
    if isinstance(value, FiniteDecimal):
        return ExactRatio.from_decimal(Decimal(value.value))
    if isinstance(value, WireExactRatio):
        return ExactRatio(int(value.numerator), int(value.denominator))
    raise TypeError(f"Unsupported exact-number branch: {type(value).__name__}")


def currency_minor_unit(currency: str) -> ExactRatio:
    """ISO 4217 minor unit from CLDR via babel.

    Codes CLDR does not list follow its own ``DEFAULT`` rule (2 digits): that is
    the standard's fallback, not a planner default.
    """
    return ExactRatio(1, 10 ** get_currency_precision(currency))


def exact_fidelity(fidelity) -> ExactTargetFidelity:
    """The request's target fidelity as the exact one: a level reads its ``λ`` off ``FIDELITY_LEVEL_WEIGHTS``, the one table the
    scenario preview also reads (B4); a custom ``λ`` is taken as it is; «Target first» has none."""
    if fidelity.kind == "level":
        return ExactTargetFidelity(kind="weighted", distance_weight=FIDELITY_LEVEL_WEIGHTS[fidelity.level])
    if fidelity.kind == "custom":
        return ExactTargetFidelity(kind="weighted", distance_weight=ExactRatio.from_decimal(Decimal(fidelity.lambda_)))
    return ExactTargetFidelity(kind="target_first", distance_weight=None)


def _deposit_id(contribution_id: str, broker_id: str) -> str:
    """The ID of a generated deposit: both IDs length-prefixed (they may contain ``:``), as ``broker_transfer_key`` does, so two
    pairs never meet. Past the 128 characters of an ID, the SHA-256 of that same key: still one per pair, and still an ID."""
    key = f"{len(contribution_id)}:{contribution_id}{len(broker_id)}:{broker_id}"
    deposit_id = f"deposit:{key}"
    return deposit_id if len(deposit_id) <= 128 else f"deposit:{hashlib.sha256(key.encode()).hexdigest()}"


def _rebalancer_deposits(request: RebalancerPlannerRequest) -> list[PlannerFundingRouteInput]:
    """The Rebalancer's deposits (specification §15 n. 2): every contribution may go to every Broker that has a buy route, in
    the contribution's currency, with no cap of its own; the plan decides how much goes where. Each carries the provenance of
    its contribution."""
    buying = sorted({route.broker_id for route in request.order_routes if route.side == "buy"})
    return [
        PlannerFundingRouteInput(
            funding_route_id=_deposit_id(item.contribution_id, broker_id),
            source=ContributionFundingSourceRef(kind="contribution", contribution_id=item.contribution_id),
            broker_id=broker_id,
            currency=item.amount.currency,
            provenance_id=item.provenance_id,
        )
        for item in request.contributions
        for broker_id in buying
    ]


def _rebalancer_lanes(request: RebalancerPlannerRequest) -> tuple[ExactTransferLane, ...]:
    """Transfers between every ordered pair of the Brokers that hold cash, buy, or have a cash item, in every currency their
    cash, the contributions, the quotes of their buys or their cash items are in (specification §15 n. 2). Free and instant;
    the score prefers fewer of them only as a tie-break. A cash item on a Broker with no route and no cash is reached this way:
    the deposits go to the Brokers that buy, a lane carries the money on."""
    quote_by_asset = {asset.asset_id: asset.quote.currency for asset in request.assets if asset.quote is not None}
    cash_items = [item for item in request.target_weights if item.kind == "cash"]
    # An inactive Broker keeps its custody but moves nothing (a selected cash or a route there is already an issue).
    inactive = {broker.broker_id for broker in request.brokers if isinstance(broker.identity, DomainBrokerIdentity) and broker.identity.active is False}
    brokers = sorted(({route.broker_id for route in request.order_routes} | {item.broker_id for item in request.existing_cash} | {item.broker_id for item in cash_items}) - inactive)
    currencies = sorted({item.selected.currency for item in request.existing_cash} | {item.amount.currency for item in request.contributions} | {quote_by_asset[route.asset_id] for route in request.order_routes if route.asset_id in quote_by_asset} | {item.currency for item in cash_items})
    return tuple(ExactTransferLane(source_broker_id=source, destination_broker_id=destination, currency=currency) for source in brokers for destination in brokers if source != destination for currency in currencies)


class _PlannerV2Normalizer:
    def __init__(self, request: _PlannerV2Request, source_issues: tuple[PlannerIssue, ...]) -> None:
        self.request = request
        self.issues = list(source_issues)
        # The PAC declares its funding routes; the Rebalancer's deposits are generated (specification §15 n. 2).
        self.funding_routes = list(request.funding_routes) if isinstance(request, PacPlannerRequest) else _rebalancer_deposits(request)
        self.currency_references: dict[str, PlannerIssuePath] = {}
        self.provenance_ids: set[str] = set()
        self.asset_ids: set[str] = set()
        self.asset_by_id: dict[str, object] = {}
        self.broker_ids: set[str] = set()
        self.holding_ids: set[str] = set()
        self.cash_ids: set[str] = set()
        self.contribution_ids: set[str] = set()
        self.capability_by_broker: dict[str, dict[str, object]] = {}
        self.fee_by_broker: dict[str, dict[str, object]] = {}
        self.reported_fx_rate_missing: set[str] = set()
        self.reported_fx_rate_inconsistent: set[str] = set()

    def issue(self, code: PlannerIssueCode, path: PlannerIssuePath, *, params: tuple[PlannerIssueParam, ...] = ()) -> None:
        self.issues.append(make_issue(normalizer_issue_definition(code), path, params=params))

    def ratio(self, text: str, path: PlannerIssuePath) -> ExactRatio:
        value = ExactRatio.from_decimal(Decimal(text))
        if len(str(abs(value.numerator))) > _RATIO_WIRE_INTEGER_CHARS or len(str(value.denominator)) > _RATIO_WIRE_INTEGER_CHARS:
            self.issue("allocation.coefficient_envelope_unsupported", path)
        return value

    def currency(self, currency: str, path: PlannerIssuePath) -> None:
        self.currency_references.setdefault(currency, path)

    def provenance(self, provenance_id: str, path: PlannerIssuePath) -> None:
        if provenance_id not in self.provenance_ids:
            self.issue("allocation.provenance_not_found", path)

    def reference(self, reference_id: str, valid_ids: set[str], path: PlannerIssuePath) -> None:
        if reference_id not in valid_ids:
            self.issue("allocation.reference_not_found", path)

    def money(self, value: PlannerMoneyInput, path: PlannerIssuePath) -> ExactRatio:
        self.currency(value.currency, path)
        return self.ratio(value.amount, path)

    def duplicates(self, values, identifier, path) -> set[str]:
        counts: dict[str, int] = defaultdict(int)
        first: dict[str, object] = {}
        for value in values:
            item_id = identifier(value)
            counts[item_id] += 1
            first.setdefault(item_id, value)
        for item_id in sorted(item_id for item_id, count in counts.items() if count > 1):
            self.issue("allocation.duplicate_id", path(first[item_id], item_id))
        return set(counts)

    def duplicate_groups(self, values, key, anchor, path, params) -> None:
        groups: dict[object, list[object]] = defaultdict(list)
        for value in values:
            groups[key(value)].append(value)
        for group_key, members in sorted(groups.items(), key=lambda item: repr(item[0])):
            if len(members) < 2:
                continue
            canonical = min(members, key=anchor)
            self.issue("allocation.duplicate_id", path(canonical), params=params(group_key))

    @staticmethod
    def _ratio_in_unit_interval(value: ExactRatio) -> bool:
        return ExactRatio(0) <= value <= ExactRatio(1)

    @staticmethod
    def _rate_in_half_open_unit_interval(value: ExactRatio) -> bool:
        return ExactRatio(0) <= value < ExactRatio(1)

    @staticmethod
    def timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")

    def validate_snapshot_and_provenance(self) -> None:
        self.provenance_ids = self.duplicates(
            self.request.provenance,
            lambda item: item.provenance_id,
            lambda _item, _item_id: field_path("input", "scenario", self.request.snapshot.snapshot_id, "provenance.provenance_id"),
        )
        for item in self.request.provenance:
            if isinstance(item, ManualProvenance):
                continue
            if isinstance(item, DomainCopyProvenance) and self.timestamp(item.captured_at) > self.timestamp(self.request.snapshot.captured_at):
                self.issue("allocation.provenance_not_found", field_path("input", "scenario", self.request.snapshot.snapshot_id, "provenance.captured_at"))
        if self.request.as_of > self.request.snapshot.captured_at[:10]:
            self.issue("allocation.reference_not_found", field_path("input", "scenario", self.request.snapshot.snapshot_id, "as_of"))
        self.currency(self.request.valuation_currency, field_path("input", "scenario", self.request.snapshot.snapshot_id, "valuation_currency"))

    def validate_assets(self) -> None:
        self.asset_ids = self.duplicates(
            self.request.assets,
            lambda item: item.asset_id,
            lambda _item, item_id: field_path("assets", "asset", item_id, "asset_id"),
        )
        self.asset_by_id = {item.asset_id: item for item in self.request.assets}
        self.duplicate_groups(
            (item for item in self.request.assets if isinstance(item.identity, DomainAssetIdentity)),
            lambda item: item.identity.source_asset_id,
            lambda item: item.asset_id,
            lambda item: field_path("assets", "asset", item.asset_id, "identity.source_asset_id"),
            lambda source_asset_id: (TextIssueParam(kind="text", name="source_asset_id", value=source_asset_id),),
        )
        if not self.request.assets:
            self.issue("allocation.target_weight_missing", section_path("targets"))
        for item in self.request.assets:
            self.validate_asset_quote(item)
            self.validate_asset_exposures(item)

    def validate_asset_quote(self, item) -> None:
        if item.quote is None:
            self.issue("allocation.price_missing", field_path("assets", "asset", item.asset_id, "quote.amount"))
            self.issue("allocation.quote_base_quantity_missing", field_path("assets", "asset", item.asset_id, "quote.quote_base_quantity"))
            return
        price_path = field_path("assets", "asset", item.asset_id, "quote.amount")
        basis_path = field_path("assets", "asset", item.asset_id, "quote.quote_base_quantity")
        self.currency(item.quote.currency, price_path)
        self.provenance(item.quote.provenance_id, field_path("assets", "asset", item.asset_id, "quote.provenance_id"))
        if self.ratio(item.quote.amount, price_path) <= ExactRatio(0):
            self.issue("allocation.nonpositive_price", price_path)
        if self.ratio(item.quote.quote_base_quantity, basis_path) <= ExactRatio(0):
            self.issue("allocation.invalid_quote_basis", basis_path)

    def validate_asset_exposures(self, item) -> None:
        self.duplicate_groups(
            item.exposures,
            lambda exposure: (exposure.dimension, exposure.category_id),
            lambda exposure: (exposure.dimension, exposure.category_id, exposure.provenance_id),
            lambda _exposure: field_path("assets", "asset", item.asset_id, "exposures.dimension_category"),
            lambda key: (
                TextIssueParam(kind="text", name="dimension", value=key[0]),
                IdIssueParam(kind="id", name="category_id", value=key[1]),
            ),
        )
        exposure_path = field_path("assets", "asset", item.asset_id, "exposures.weight")
        totals: dict[str, ExactRatio] = defaultdict(lambda: ExactRatio(0))
        out_of_range_dimensions: set[str] = set()
        for exposure in item.exposures:
            self.provenance(exposure.provenance_id, field_path("assets", "asset", item.asset_id, "exposures.provenance_id"))
            weight = self.ratio(exposure.weight, exposure_path)
            totals[exposure.dimension] += weight
            if not self._ratio_in_unit_interval(weight):
                out_of_range_dimensions.add(exposure.dimension)
                self.issue("allocation.exposure_weight_out_of_range", exposure_path)
        # A dimension may stay below one (the report keeps the residual); above
        # one is contradictory. An out-of-range weight is already the root cause.
        for dimension, total in sorted(totals.items()):
            if dimension not in out_of_range_dimensions and total > ExactRatio(1):
                self.issue("allocation.exposure_total_exceeds_one", exposure_path, params=(TextIssueParam(kind="text", name="dimension", value=dimension),))

    def validate_limit(self, limit, entity_kind: str, entity_id: str, field: str) -> None:
        """One limit of a target entry: an amount in the valuation currency and not negative, or a share from 0 to 1."""
        if limit is None:
            return
        path = field_path("targets", entity_kind, entity_id, field)
        if limit.kind == "amount":
            if limit.amount.currency != self.request.valuation_currency:
                self.issue("allocation.currency_mismatch", path)
            if self.ratio(limit.amount.amount, path) < ExactRatio(0):
                self.issue("allocation.target_weight_out_of_range", path)
        elif not self._ratio_in_unit_interval(self.ratio(limit.share, path)):
            self.issue("allocation.target_weight_out_of_range", path)

    def validate_targets(self) -> None:
        asset_entries = [item for item in self.request.target_weights if item.kind == "asset"]
        cash_entries = [item for item in self.request.target_weights if item.kind == "cash"]
        target_ids = self.duplicates(
            asset_entries,
            lambda item: item.asset_id,
            lambda _item, item_id: field_path("targets", "asset", item_id, "asset_id"),
        )
        valid_values: list[ExactRatio] = []
        references_valid = True
        values_valid = True
        for item in asset_entries:
            path = field_path("targets", "asset", item.asset_id, "weight")
            if item.asset_id not in self.asset_ids:
                references_valid = False
                self.issue("allocation.reference_not_found", field_path("targets", "asset", item.asset_id, "asset_id"))
            weight = self.ratio(item.weight, path)
            valid_values.append(weight)
            if not self._ratio_in_unit_interval(weight):
                values_valid = False
                self.issue("allocation.target_weight_out_of_range", path)
            self.validate_limit(item.minimum, "asset", item.asset_id, "minimum")
            self.validate_limit(item.maximum, "asset", item.asset_id, "maximum")
        missing_targets = sorted(self.asset_ids - target_ids)
        for asset_id in missing_targets:
            self.issue("allocation.target_weight_missing", field_path("targets", "asset", asset_id, "weight"))
        cash_weights = self.validate_cash_entries(cash_entries)
        values_valid = values_valid and cash_weights is not None
        if not missing_targets and references_valid and values_valid and len(target_ids) == len(asset_entries):
            # The Rebalancer's weights of every entry, Assets and cash, sum to one (contract §5.2); the PAC's cash has none.
            total = sum((*valid_values, *(cash_weights or ())), ExactRatio(0))
            if len(str(abs(total.numerator))) > _RATIO_WIRE_INTEGER_CHARS or len(str(total.denominator)) > _RATIO_WIRE_INTEGER_CHARS:
                self.issue("allocation.coefficient_envelope_unsupported", section_path("targets"))
            if total != ExactRatio(1):
                self.issue("allocation.target_total_not_one", section_path("targets"))

    def validate_cash_entries(self, entries) -> list[ExactRatio] | None:
        """Cash entries (contract 2.0.0): one per Broker and currency cell, a known Broker, limits as for an Asset. A weight other
        than zero is the Rebalancer's (B3 of project 67) and unsupported in the PAC. Returns the weights, ``None`` when one is out
        of range."""
        rebalancer = isinstance(self.request, RebalancerPlannerRequest)
        weights: list[ExactRatio] | None = []
        seen: set[tuple[str, str]] = set()
        for item in entries:
            cell = f"{item.broker_id}:{item.currency}"
            if (item.broker_id, item.currency) in seen:
                self.issue("allocation.duplicate_id", field_path("targets", "cash", cell, "broker_id"))
            seen.add((item.broker_id, item.currency))
            if item.broker_id not in self.broker_ids:
                self.issue("allocation.reference_not_found", field_path("targets", "cash", cell, "broker_id"))
            weight_path = field_path("targets", "cash", cell, "weight")
            weight = self.ratio(item.weight, weight_path)
            # An entry with no weight and no limit says nothing: its currency needs no rate.
            if item.minimum is not None or item.maximum is not None or (rebalancer and weight != ExactRatio(0)):
                self.currency(item.currency, field_path("targets", "cash", cell, "currency"))
            if not self._ratio_in_unit_interval(weight):
                self.issue("allocation.target_weight_out_of_range", weight_path)
                weights = None
            elif weight != ExactRatio(0) and not rebalancer:
                self.issue("pac_allocator.cash_weight_unsupported", weight_path)
            elif weights is not None:
                weights.append(weight)
            self.validate_limit(item.minimum, "cash", cell, "minimum")
            self.validate_limit(item.maximum, "cash", cell, "maximum")
        return weights

    def validate_brokers(self) -> None:
        self.broker_ids = self.duplicates(
            self.request.brokers,
            lambda item: item.broker_id,
            lambda _item, item_id: field_path("brokers", "broker", item_id, "broker_id"),
        )
        self.duplicate_groups(
            (item for item in self.request.brokers if isinstance(item.identity, DomainBrokerIdentity)),
            lambda item: item.identity.source_broker_id,
            lambda item: item.broker_id,
            lambda item: field_path("brokers", "broker", item.broker_id, "identity.source_broker_id"),
            lambda source_broker_id: (TextIssueParam(kind="text", name="source_broker_id", value=source_broker_id),),
        )
        executable_broker_ids = {item.broker_id for item in self.funding_routes}
        executable_broker_ids.update(item.broker_id for item in self.request.order_routes)
        executable_broker_ids.update(item.broker_id for item in self.request.existing_cash if self.ratio(item.selected.amount, field_path("cash", "cash", item.cash_id, "selected")) > ExactRatio(0))
        for broker in self.request.brokers:
            self.provenance(broker.provenance_id, field_path("brokers", "broker", broker.broker_id, "provenance_id"))
            capability_ids = self.duplicates(
                broker.capabilities,
                lambda item: item.capability_id,
                lambda _item, _item_id, broker_id=broker.broker_id: field_path("brokers", "broker", broker_id, "capabilities.capability_id"),
            )
            capability_map = {item.capability_id: item for item in broker.capabilities}
            self.capability_by_broker[broker.broker_id] = capability_map
            self.duplicates(
                broker.fee_schedules,
                lambda item: item.fee_schedule_id,
                lambda _item, _item_id, broker_id=broker.broker_id: field_path("brokers", "broker", broker_id, "fee_schedules.fee_schedule_id"),
            )
            self.fee_by_broker[broker.broker_id] = {item.fee_schedule_id: item for item in broker.fee_schedules}
            if isinstance(broker.identity, DomainBrokerIdentity) and broker.identity.active is False and (broker.capabilities or broker.broker_id in executable_broker_ids):
                self.issue("allocation.broker_inactive", field_path("brokers", "broker", broker.broker_id, "active"))
            for capability in broker.capabilities:
                self.validate_capability(broker, capability)
            for fee in broker.fee_schedules:
                self.validate_fee_schedule(broker, fee, capability_ids)

    def validate_capability(self, broker, capability) -> None:
        capability_path = field_path("brokers", "broker", broker.broker_id, "capabilities.quantity_step")
        if isinstance(capability, WholeQuantityCapability):
            if self.ratio(capability.quantity_step, capability_path) <= ExactRatio(0):
                self.issue("allocation.nonpositive_quantity_step", capability_path)
            return
        step_path = field_path("brokers", "broker", broker.broker_id, "capabilities.order_amount_step")
        step = self.money(capability.order_amount_step, step_path)
        if step <= ExactRatio(0):
            self.issue("allocation.nonpositive_order_amount_step", step_path)

    @staticmethod
    def fee_schedule_currencies(fee) -> tuple[str, ...]:
        """Currencies of the money fields present on a fee schedule, in field order.

        An absent money field is zero. A schedule without any money field has no
        currency of its own: it is priced in the quote currency of each route using it.
        """
        present = [fee.fixed_fee, fee.variable_floor]
        if isinstance(fee.variable_cap, AmountFeeCap):
            present.append(fee.variable_cap.amount)
        return tuple(dict.fromkeys(money.currency for money in present if money is not None))

    def validate_fee_schedule(self, broker, fee, capability_ids: set[str]) -> None:
        fee_path = field_path("brokers", "broker", broker.broker_id, "fee_schedules")
        if fee.capability_id not in capability_ids:
            self.issue("allocation.reference_not_found", field_path("brokers", "broker", broker.broker_id, "fee_schedules.capability_id"))
        fixed_fee = ExactRatio(0) if fee.fixed_fee is None else self.money(fee.fixed_fee, fee_path)
        variable_floor = ExactRatio(0) if fee.variable_floor is None else self.money(fee.variable_floor, fee_path)
        rate = self.ratio(fee.rate, fee_path)
        cap = self.money(fee.variable_cap.amount, fee_path) if isinstance(fee.variable_cap, AmountFeeCap) else None
        money_values = (fixed_fee, variable_floor) if cap is None else (fixed_fee, variable_floor, cap)
        if any(value < ExactRatio(0) for value in money_values):
            self.issue("allocation.negative_fee_amount", fee_path)
        if not self._ratio_in_unit_interval(rate):
            self.issue("allocation.fee_rate_out_of_range", fee_path)
        if cap is not None and variable_floor > cap:
            self.issue("allocation.fee_floor_exceeds_cap", fee_path)
        if len(self.fee_schedule_currencies(fee)) > 1:
            self.issue("allocation.currency_mismatch", fee_path)

    def validate_holdings(self) -> None:
        if isinstance(self.request, PacPlannerRequest):
            self.holding_ids = set()
            return
        self.holding_ids = self.duplicates(
            self.request.holdings,
            lambda item: item.holding_id,
            lambda _item, item_id: field_path("holdings", "holding", item_id, "holding_id"),
        )
        self.duplicate_groups(
            self.request.holdings,
            lambda item: (item.asset_id, item.broker_id),
            lambda item: item.holding_id,
            lambda item: field_path("holdings", "holding", item.holding_id, "asset_id.broker_id"),
            lambda key: (
                IdIssueParam(kind="id", name="asset_id", value=key[0]),
                IdIssueParam(kind="id", name="broker_id", value=key[1]),
            ),
        )
        if not self.request.holdings:
            self.issue("portfolio_rebalancer.holdings_missing", section_path("holdings"))
        for item in self.request.holdings:
            self.reference(item.asset_id, self.asset_ids, field_path("holdings", "holding", item.holding_id, "asset_id"))
            self.reference(item.broker_id, self.broker_ids, field_path("holdings", "holding", item.holding_id, "broker_id"))
            self.provenance(item.provenance_id, field_path("holdings", "holding", item.holding_id, "provenance_id"))
            custody = self.ratio(item.custody_quantity, field_path("holdings", "holding", item.holding_id, "custody_quantity"))
            share = self.ratio(item.economic_share, field_path("holdings", "holding", item.holding_id, "economic_share"))
            planning = self.ratio(item.planning_quantity, field_path("holdings", "holding", item.holding_id, "planning_quantity"))
            if custody < ExactRatio(0):
                self.issue("allocation.negative_inventory_unsupported", field_path("holdings", "holding", item.holding_id, "custody_quantity"))
            if not self._ratio_in_unit_interval(share):
                self.issue("allocation.economic_share_out_of_range", field_path("holdings", "holding", item.holding_id, "economic_share"))
            if planning < ExactRatio(0):
                self.issue("allocation.planning_quantity_negative", field_path("holdings", "holding", item.holding_id, "planning_quantity"))
            economic_quantity = custody * share
            if len(str(abs(economic_quantity.numerator))) > _RATIO_WIRE_INTEGER_CHARS or len(str(economic_quantity.denominator)) > _RATIO_WIRE_INTEGER_CHARS:
                self.issue("allocation.coefficient_envelope_unsupported", field_path("holdings", "holding", item.holding_id, "economic_share"))

    def validate_cash_and_contributions(self) -> None:
        self.cash_ids = self.duplicates(
            self.request.existing_cash,
            lambda item: item.cash_id,
            lambda _item, item_id: field_path("cash", "cash", item_id, "cash_id"),
        )
        cash_by_id = {item.cash_id: item for item in self.request.existing_cash}
        for item in self.request.existing_cash:
            self.validate_cash(item)
        self.contribution_ids = self.duplicates(
            self.request.contributions,
            lambda item: item.contribution_id,
            lambda _item, item_id: field_path("contributions", "contribution", item_id, "contribution_id"),
        )
        contribution_by_id = {item.contribution_id: item for item in self.request.contributions}
        for item in self.request.contributions:
            self.validate_contribution(item)
        self.validate_funding_routes(cash_by_id, contribution_by_id)
        self.validate_selected_funding()

    def validate_cash(self, item) -> None:
        self.reference(item.broker_id, self.broker_ids, field_path("cash", "cash", item.cash_id, "broker_id"))
        self.provenance(item.provenance_id, field_path("cash", "cash", item.cash_id, "provenance_id"))
        available = self.money(item.available, field_path("cash", "cash", item.cash_id, "available"))
        selected = self.money(item.selected, field_path("cash", "cash", item.cash_id, "selected"))
        if item.available.currency != item.selected.currency:
            self.issue("allocation.currency_mismatch", field_path("cash", "cash", item.cash_id, "selected"))
        negative = False
        for amount, field in ((available, "available"), (selected, "selected")):
            if amount < ExactRatio(0):
                self.issue("allocation.negative_cash_unsupported", field_path("cash", "cash", item.cash_id, field))
                negative = True
        if not negative and selected > available:
            self.issue("allocation.cash_selection_invalid", field_path("cash", "cash", item.cash_id, "selected"))

    def validate_contribution(self, item) -> None:
        self.provenance(item.provenance_id, field_path("contributions", "contribution", item.contribution_id, "provenance_id"))
        amount = self.money(item.amount, field_path("contributions", "contribution", item.contribution_id, "amount"))
        if amount < ExactRatio(0):
            self.issue("allocation.negative_contribution", field_path("contributions", "contribution", item.contribution_id, "amount"))

    def validate_selected_funding(self) -> None:
        funding_values = [self.ratio(item.selected.amount, field_path("cash", "cash", item.cash_id, "selected")) for item in self.request.existing_cash]
        funding_values.extend(self.ratio(item.amount.amount, field_path("contributions", "contribution", item.contribution_id, "amount")) for item in self.request.contributions)
        # «Invest only» needs money to invest; C1 (project 67) exempts «Invest and sell», which can fund itself by selling.
        if not funding_values:
            self.issue("allocation.no_selected_funding", section_path("funding"))

    def validate_funding_routes(self, cash_by_id: dict[str, object], contribution_by_id: dict[str, object]) -> None:  # noqa: C901 — flat per-route field checks plus one source lookup per source kind
        self.duplicates(
            self.funding_routes,
            lambda item: item.funding_route_id,
            lambda _item, item_id: field_path("funding", "funding_route", item_id, "funding_route_id"),
        )
        for item in self.funding_routes:
            route_path = field_path("funding", "funding_route", item.funding_route_id, "transfer_cap")
            self.reference(item.broker_id, self.broker_ids, field_path("funding", "funding_route", item.funding_route_id, "broker_id"))
            self.provenance(item.provenance_id, field_path("funding", "funding_route", item.funding_route_id, "provenance_id"))
            self.currency(item.currency, route_path)
            if item.transfer_cap is not None:
                if self.money(item.transfer_cap, route_path) < ExactRatio(0):
                    self.issue("allocation.funding_cap_negative", route_path)
                if item.transfer_cap.currency != item.currency:
                    self.issue("allocation.currency_mismatch", route_path)
            if item.priority < 0:
                self.issue("allocation.route_priority_negative", field_path("funding", "funding_route", item.funding_route_id, "priority"))
            source = None
            if item.source.kind == "existing_cash":
                source = cash_by_id.get(item.source.cash_id)
                if source is None:
                    self.issue("allocation.reference_not_found", field_path("funding", "funding_route", item.funding_route_id, "source.cash_id"))
                else:
                    source_currency = source.selected.currency
                    if source_currency != item.currency:
                        self.issue("allocation.currency_mismatch", field_path("funding", "funding_route", item.funding_route_id, "currency"))
            else:
                source = contribution_by_id.get(item.source.contribution_id)
                if source is None:
                    self.issue("allocation.reference_not_found", field_path("funding", "funding_route", item.funding_route_id, "source.contribution_id"))
                else:
                    source_currency = source.amount.currency
                    if source_currency != item.currency:
                        self.issue("allocation.currency_mismatch", field_path("funding", "funding_route", item.funding_route_id, "currency"))

    def order_minimum(self, minimum, route: PlannerOrderRouteInput, field: str) -> tuple[ExactRatio, str, str | None]:
        path = field_path("routing", "order_route", route.route_id, field)
        if isinstance(minimum, WholeQuantityMinimum):
            return self.ratio(minimum.quantity, path), "quantity", None
        if isinstance(minimum, MonetaryAmountMinimum):
            return self.money(minimum.amount, path), "notional", minimum.amount.currency
        return ExactRatio(0), "none", None

    def order_cap(self, route: PlannerOrderRouteInput) -> tuple[ExactRatio | None, str, str | None]:
        path = field_path("routing", "order_route", route.route_id, "cap")
        if isinstance(route.cap, NoOrderCap):
            return None, "none", None
        if isinstance(route.cap, NotionalOrderCap):
            return self.money(route.cap.amount, path), "notional", route.cap.amount.currency
        return self.ratio(route.cap.quantity, path), "quantity", None

    def validate_order_routes(self) -> None:
        self.duplicates(
            self.request.order_routes,
            lambda item: item.route_id,
            lambda _item, item_id: field_path("routing", "order_route", item_id, "route_id"),
        )
        for route in self.request.order_routes:
            capability, quote_currency = self.validate_order_route_references(route)
            self.validate_order_route_limits(route, capability, quote_currency)

    def validate_order_route_references(self, route: PlannerOrderRouteInput):
        self.reference(route.asset_id, self.asset_ids, field_path("routing", "order_route", route.route_id, "asset_id"))
        self.reference(route.broker_id, self.broker_ids, field_path("routing", "order_route", route.route_id, "broker_id"))
        self.provenance(route.provenance_id, field_path("routing", "order_route", route.route_id, "provenance_id"))
        if route.priority < 0:
            self.issue("allocation.route_priority_negative", field_path("routing", "order_route", route.route_id, "priority"))
        margin_path = field_path("routing", "order_route", route.route_id, "execution_margin_rate")
        if not self._rate_in_half_open_unit_interval(self.ratio(route.execution_margin_rate, margin_path)):
            self.issue("allocation.execution_margin_rate_out_of_range", margin_path)
        capability = self.capability_by_broker.get(route.broker_id, {}).get(route.capability_id)
        if capability is None:
            self.issue("allocation.reference_not_found", field_path("routing", "order_route", route.route_id, "capability_id"))
        asset = self.asset_by_id.get(route.asset_id)
        quote_currency = asset.quote.currency if asset is not None and asset.quote is not None else None
        if quote_currency is not None:
            self.currency(quote_currency, entity_path("routing", "order_route", route.route_id))
        self.validate_order_route_fee_schedule(route, quote_currency)
        return capability, quote_currency

    def validate_order_route_fee_schedule(self, route: PlannerOrderRouteInput, quote_currency: str | None) -> None:
        if route.fee_schedule_id is None:
            # Only a BUY route may omit it (the SELL schema requires it): the order pays no fee.
            return
        path = field_path("routing", "order_route", route.route_id, "fee_schedule_id")
        fee_schedule = self.fee_by_broker.get(route.broker_id, {}).get(route.fee_schedule_id)
        if fee_schedule is None:
            code = "portfolio_rebalancer.sell_fee_missing" if route.side == "sell" else "allocation.fee_schedule_missing"
            self.issue(code, path)
            return
        if fee_schedule.side != route.side or fee_schedule.capability_id != route.capability_id:
            self.issue("allocation.reference_not_found", path)
            return
        currencies = self.fee_schedule_currencies(fee_schedule)
        if quote_currency is not None and currencies and currencies[0] != quote_currency:
            self.issue("allocation.currency_mismatch", path)

    def validate_order_route_limits(self, route: PlannerOrderRouteInput, capability, quote_currency: str | None) -> None:
        minimum_if_active, minimum_if_active_kind, minimum_if_active_currency = self.order_minimum(route.minimum_if_active, route, "minimum_if_active")
        cap, cap_kind, cap_currency = self.order_cap(route)
        if minimum_if_active < ExactRatio(0):
            self.issue("allocation.order_minimum_negative", field_path("routing", "order_route", route.route_id, "minimum_if_active"))
        if cap is not None and cap <= ExactRatio(0):
            self.issue("allocation.order_cap_nonpositive", field_path("routing", "order_route", route.route_id, "cap"))
        expected_kind = "quantity" if isinstance(capability, WholeQuantityCapability) else "notional" if isinstance(capability, MonetaryAmountCapability) else None
        self.validate_order_minimum_kind(route, capability, expected_kind, minimum_if_active_kind, minimum_if_active_currency, quote_currency, "minimum_if_active")
        if cap is None:
            return
        if expected_kind is not None and cap_kind != expected_kind:
            self.issue("allocation.reference_not_found", field_path("routing", "order_route", route.route_id, "cap"))
        if cap_currency is not None and isinstance(capability, MonetaryAmountCapability) and quote_currency is not None and cap_currency != quote_currency:
            self.issue("allocation.currency_mismatch", field_path("routing", "order_route", route.route_id, "cap"))
        if minimum_if_active_kind in {"none", cap_kind} and minimum_if_active > cap:
            self.issue("allocation.order_minimum_exceeds_cap", field_path("routing", "order_route", route.route_id, "minimum_if_active"))

    def validate_order_minimum_kind(self, route: PlannerOrderRouteInput, capability, expected_kind: str | None, minimum_kind: str, minimum_currency: str | None, quote_currency: str | None, field: str) -> None:
        if minimum_kind != "none" and expected_kind is not None and minimum_kind != expected_kind:
            self.issue("allocation.reference_not_found", field_path("routing", "order_route", route.route_id, field))
        if minimum_currency is not None and isinstance(capability, MonetaryAmountCapability) and quote_currency is not None and minimum_currency != quote_currency:
            self.issue("allocation.currency_mismatch", field_path("routing", "order_route", route.route_id, field))

    def validate_fx_rates(self) -> None:
        for pair, rate in sorted(self.request.fx_rates.items()):
            first, _, second = pair.partition("/")
            path = field_path("fx", "fx_rate", pair, "rate")
            self.currency(first, path)
            self.currency(second, path)
            value = self.ratio(rate, path)
            if first >= second:
                self.issue("allocation.identity_fx_rate_not_allowed", path)
            elif value <= ExactRatio(0):
                self.issue("allocation.nonpositive_fx_rate", path)
        spread_path = field_path("input", "scenario", self.request.snapshot.snapshot_id, "fx_spread_rate")
        spread = self.ratio(self.request.fx_spread_rate, spread_path)
        if not self._rate_in_half_open_unit_interval(spread):
            self.issue("allocation.fx_spread_rate_out_of_range", spread_path)

    @staticmethod
    def _fx_pair_key(first: str, second: str) -> str:
        return "/".join(sorted((first, second)))

    @staticmethod
    def _stored_fx_rate(rate: ExactRatio, source: str, destination: str) -> ExactRatio:
        """Return the stored value behind ``rate`` (source → destination): the key "A/B" with A < B stores B per A."""
        return oriented_rate(rate, source, destination)

    def fx_rate(self, source: str, destination: str) -> ExactRatio | None:
        if source == destination:
            return ExactRatio(1)
        raw = self.request.fx_rates.get(self._fx_pair_key(source, destination))
        if raw is None:
            return None
        rate = ExactRatio.from_decimal(Decimal(raw))
        if rate <= ExactRatio(0):
            # A nonpositive stored rate is already reported by validate_fx_rates();
            # treat it as unusable here too instead of dividing by zero/negative on
            # the reciprocal branch. Callers already handle a ``None`` return.
            return None
        return oriented_rate(rate, source, destination)

    def require_fx_pair(self, first: str, second: str) -> None:
        if first == second:
            return
        pair = self._fx_pair_key(first, second)
        if pair in self.request.fx_rates or pair in self.reported_fx_rate_missing:
            return
        self.reported_fx_rate_missing.add(pair)
        self.issue("allocation.fx_rate_missing", field_path("fx", "fx_rate", pair, "rate"))

    def _cash_pool_currencies_by_broker(self) -> dict[str, set[str]]:
        pool_currencies_by_broker: dict[str, set[str]] = defaultdict(set)
        for item in self.request.existing_cash:
            pool_currencies_by_broker[item.broker_id].add(item.available.currency)
        for item in self.funding_routes:
            pool_currencies_by_broker[item.broker_id].add(item.currency)
        for route in self.request.order_routes:
            if route.side != "sell":
                continue
            asset = self.asset_by_id.get(route.asset_id)
            if asset is not None and asset.quote is not None:
                pool_currencies_by_broker[route.broker_id].add(asset.quote.currency)
        return pool_currencies_by_broker

    def validate_fx_pair_closure(self) -> None:
        for currency in sorted(self.currency_references):
            self.require_fx_pair(currency, self.request.valuation_currency)
        pool_currencies_by_broker = self._cash_pool_currencies_by_broker()
        for route in self.request.order_routes:
            if route.side != "buy":
                continue
            asset = self.asset_by_id.get(route.asset_id)
            if asset is None or asset.quote is None:
                continue
            for pool_currency in sorted(pool_currencies_by_broker.get(route.broker_id, set())):
                self.require_fx_pair(pool_currency, asset.quote.currency)

    def validate_fx_coherence(self) -> None:
        """Refuse a cross rate that, net of the spread, beats the triangle through V.

        A BUY conversion from pool currency c into quote currency q is worth
        ``rate(c→q)·(1−spread)·rate(q→V)`` in the valuation currency V; above
        ``rate(c→V)`` it would create value. Rates are stored with ten
        decimals, so three coherent rates can miss the triangle by their
        storage error: the check tolerates the first-order relative error of
        the product, ``β = h·(1/R₁ + 1/R₂ + 1/R₃)`` over the three stored
        values, with h half a unit of the tenth decimal. Inside that band the
        evaluator plans the conversion at the triangle
        (``calculate_planning_fx_rate``), so it creates no value either. The
        checked conversions are exactly those ``validate_fx_pair_closure``
        requires; a conversion from or into V never forms a triangle. A
        missing or nonpositive rate and an out-of-range spread are reported
        elsewhere and skip the check.
        """
        valuation = self.request.valuation_currency
        spread = ExactRatio.from_decimal(Decimal(self.request.fx_spread_rate))
        if not self._rate_in_half_open_unit_interval(spread):
            return
        kept = ExactRatio(1) - spread
        pool_currencies_by_broker = self._cash_pool_currencies_by_broker()
        for route in self.request.order_routes:
            if route.side != "buy":
                continue
            asset = self.asset_by_id.get(route.asset_id)
            if asset is None or asset.quote is None or asset.quote.currency == valuation:
                continue
            quote_currency = asset.quote.currency
            for pool_currency in sorted(pool_currencies_by_broker.get(route.broker_id, set())):
                pair = self._fx_pair_key(pool_currency, quote_currency)
                if pool_currency in (quote_currency, valuation) or pair in self.reported_fx_rate_inconsistent:
                    continue
                cross = self.fx_rate(pool_currency, quote_currency)
                to_valuation = self.fx_rate(quote_currency, valuation)
                direct = self.fx_rate(pool_currency, valuation)
                if cross is None or to_valuation is None or direct is None:
                    continue
                band = _FX_STORED_RATE_HALF_UNIT * sum(
                    (
                        ExactRatio(1) / self._stored_fx_rate(rate, source, destination)
                        for rate, source, destination in (
                            (cross, pool_currency, quote_currency),
                            (to_valuation, quote_currency, valuation),
                            (direct, pool_currency, valuation),
                        )
                    ),
                    ExactRatio(0),
                )
                if cross * kept * to_valuation > direct * (ExactRatio(1) + band):
                    self.reported_fx_rate_inconsistent.add(pair)
                    self.issue(
                        "allocation.fx_rate_inconsistent",
                        field_path("fx", "fx_rate", pair, "rate"),
                        params=(
                            IdIssueParam(kind="id", name="pair", value=pair),
                            CurrencyIssueParam(kind="currency", name="source_currency", value=pool_currency),
                            CurrencyIssueParam(kind="currency", name="destination_currency", value=quote_currency),
                            CurrencyIssueParam(kind="currency", name="valuation_currency", value=valuation),
                        ),
                    )

    def validate_current_portfolio(self) -> None:
        if isinstance(self.request, PacPlannerRequest) or not self.request.holdings:
            return
        total = ExactRatio(0)
        complete = True
        for holding in self.request.holdings:
            asset = self.asset_by_id.get(holding.asset_id)
            if asset is None or asset.quote is None:
                complete = False
                continue
            quantity = self.ratio(holding.planning_quantity, field_path("holdings", "holding", holding.holding_id, "planning_quantity"))
            price = self.ratio(asset.quote.amount, field_path("assets", "asset", asset.asset_id, "quote.amount"))
            basis = self.ratio(asset.quote.quote_base_quantity, field_path("assets", "asset", asset.asset_id, "quote.quote_base_quantity"))
            if quantity < ExactRatio(0) or price <= ExactRatio(0) or basis <= ExactRatio(0):
                complete = False
                continue
            rate = self.fx_rate(asset.quote.currency, self.request.valuation_currency)
            if rate is None or rate <= ExactRatio(0):
                complete = False
                continue
            total += quantity * price * rate / basis
        if complete:
            if len(str(abs(total.numerator))) > _RATIO_WIRE_INTEGER_CHARS or len(str(total.denominator)) > _RATIO_WIRE_INTEGER_CHARS:
                self.issue("allocation.coefficient_envelope_unsupported", section_path("holdings"))
            if total <= ExactRatio(0):
                self.issue("portfolio_rebalancer.nonpositive_current_portfolio", section_path("holdings"))

    @staticmethod
    def build_money(value: PlannerMoneyInput) -> ExactMoney:
        return ExactMoney(amount=ExactRatio.from_decimal(Decimal(value.amount)), currency=value.currency)

    def build_provenance(self) -> tuple[ExactProvenance, ...]:
        result = []
        for item in sorted(self.request.provenance, key=lambda value: value.provenance_id):
            if isinstance(item, ManualProvenance):
                result.append(
                    ExactProvenance(
                        provenance_id=item.provenance_id,
                        kind="manual",
                        label=item.label,
                        entered_at=self.timestamp(item.entered_at),
                        domain=None,
                        source_ref=None,
                        source_label=None,
                        captured_at=None,
                    )
                )
            else:
                result.append(
                    ExactProvenance(
                        provenance_id=item.provenance_id,
                        kind="domain_copy",
                        label=None,
                        entered_at=None,
                        domain=item.domain,
                        source_ref=item.source_ref,
                        source_label=item.source_label,
                        captured_at=self.timestamp(item.captured_at),
                    )
                )
        return tuple(result)

    def build_assets(self) -> tuple[ExactAsset, ...]:
        result = []
        for item in sorted(self.request.assets, key=lambda value: value.asset_id):
            if item.quote is None:
                raise RuntimeError("Ready Planner v2 asset has no quote")
            identity_kind = "domain" if isinstance(item.identity, DomainAssetIdentity) else "manual"
            source_asset_id = item.identity.source_asset_id if isinstance(item.identity, DomainAssetIdentity) else None
            exposures = tuple(
                ExactExposure(
                    dimension=exposure.dimension,
                    category=exposure.category_id,
                    label=exposure.label,
                    weight=ExactRatio.from_decimal(Decimal(exposure.weight)),
                    provenance_id=exposure.provenance_id,
                )
                for exposure in sorted(item.exposures, key=lambda value: (value.dimension, value.category_id))
            )
            result.append(
                ExactAsset(
                    asset_id=item.asset_id,
                    identity_kind=identity_kind,
                    source_asset_id=source_asset_id,
                    name=item.identity.name,
                    ticker=item.identity.ticker,
                    asset_class=item.identity.asset_class,
                    quote=ExactAssetQuote(
                        price=ExactMoney(amount=ExactRatio.from_decimal(Decimal(item.quote.amount)), currency=item.quote.currency),
                        quote_base_quantity=ExactRatio.from_decimal(Decimal(item.quote.quote_base_quantity)),
                        provenance_id=item.quote.provenance_id,
                    ),
                    exposures=exposures,
                )
            )
        return tuple(result)

    def build_fee_schedule(self, fee_schedule_id: str, fee, currency: str) -> ExactFeeSchedule:
        def money_or_zero(value: PlannerMoneyInput | None) -> ExactMoney:
            return ExactMoney(amount=ExactRatio(0), currency=currency) if value is None else self.build_money(value)

        return ExactFeeSchedule(
            fee_schedule_id=fee_schedule_id,
            capability_id=fee.capability_id,
            side=fee.side,
            fixed_fee=money_or_zero(fee.fixed_fee),
            proportional_rate=ExactRatio.from_decimal(Decimal(fee.rate)),
            minimum_fee=money_or_zero(fee.variable_floor),
            maximum_fee=self.build_money(fee.variable_cap.amount) if isinstance(fee.variable_cap, AmountFeeCap) else None,
        )

    def build_fee_instances(self) -> tuple[dict[str, tuple[ExactFeeSchedule, ...]], dict[str, str]]:
        """Give every ready order route one single-currency fee schedule.

        A schedule with money fields keeps the caller's ID. A schedule without any
        becomes one instance per quote currency of the routes using it
        (``{id}~{CUR}``); an unused one produces none. A BUY route without a schedule
        gets the implicit zero instance ``~zero~{capability_id}~{CUR}``. ``~`` is not
        in the planner ID alphabet, so an instance ID cannot collide with a caller ID.
        Returns the schedules per Broker in canonical order and the schedule of each route.
        """
        schedules: dict[str, dict[str, ExactFeeSchedule]] = defaultdict(dict)
        for broker in self.request.brokers:
            for fee in broker.fee_schedules:
                currencies = self.fee_schedule_currencies(fee)
                if currencies:
                    schedules[broker.broker_id][fee.fee_schedule_id] = self.build_fee_schedule(fee.fee_schedule_id, fee, currencies[0])
        route_fee_ids: dict[str, str] = {}
        for route in self.request.order_routes:
            broker_schedules = schedules[route.broker_id]
            currency = self.asset_by_id[route.asset_id].quote.currency
            if route.fee_schedule_id is None:
                instance_id = f"~zero~{route.capability_id}~{currency}"
                if instance_id not in broker_schedules:
                    zero = ExactMoney(amount=ExactRatio(0), currency=currency)
                    broker_schedules[instance_id] = ExactFeeSchedule(
                        fee_schedule_id=instance_id,
                        capability_id=route.capability_id,
                        side="buy",
                        fixed_fee=zero,
                        proportional_rate=ExactRatio(0),
                        minimum_fee=zero,
                        maximum_fee=None,
                    )
            elif route.fee_schedule_id in broker_schedules:
                instance_id = route.fee_schedule_id
            else:
                instance_id = f"{route.fee_schedule_id}~{currency}"
                if instance_id not in broker_schedules:
                    fee = self.fee_by_broker[route.broker_id][route.fee_schedule_id]
                    broker_schedules[instance_id] = self.build_fee_schedule(instance_id, fee, currency)
            route_fee_ids[route.route_id] = instance_id
        ordered = {broker_id: tuple(sorted(rows.values(), key=lambda row: (row.capability_id, row.side, row.fee_schedule_id))) for broker_id, rows in schedules.items()}
        return ordered, route_fee_ids

    def build_brokers(self, fee_schedules: dict[str, tuple[ExactFeeSchedule, ...]]) -> tuple[ExactBroker, ...]:
        result = []
        for broker in sorted(self.request.brokers, key=lambda value: value.broker_id):
            capabilities = []
            for capability in sorted(broker.capabilities, key=lambda value: value.capability_id):
                if isinstance(capability, WholeQuantityCapability):
                    step = ExactRatio.from_decimal(Decimal(capability.quantity_step))
                else:
                    step = ExactRatio.from_decimal(Decimal(capability.order_amount_step.amount))
                capabilities.append(
                    ExactOrderCapability(
                        capability_id=capability.capability_id,
                        kind=capability.kind,
                        order_step=step,
                    )
                )
            result.append(
                ExactBroker(
                    broker_id=broker.broker_id,
                    identity_kind="domain" if isinstance(broker.identity, DomainBrokerIdentity) else "manual",
                    source_broker_id=broker.identity.source_broker_id if isinstance(broker.identity, DomainBrokerIdentity) else None,
                    name=broker.identity.name,
                    active=broker.identity.active if isinstance(broker.identity, DomainBrokerIdentity) else None,
                    provenance_id=broker.provenance_id,
                    capabilities=tuple(capabilities),
                    fee_schedules=fee_schedules.get(broker.broker_id, ()),
                    conversion_mode=broker.conversion_mode,
                )
            )
        return tuple(result)

    def build_holdings(self) -> tuple[ExactHolding, ...]:
        if isinstance(self.request, PacPlannerRequest):
            return ()
        result = []
        for item in sorted(self.request.holdings, key=lambda value: value.holding_id):
            custody = ExactRatio.from_decimal(Decimal(item.custody_quantity))
            share = ExactRatio.from_decimal(Decimal(item.economic_share))
            result.append(
                ExactHolding(
                    holding_id=item.holding_id,
                    asset_id=item.asset_id,
                    broker_id=item.broker_id,
                    custody_quantity=custody,
                    economic_share=share,
                    economic_quantity=custody * share,
                    planning_quantity=ExactRatio.from_decimal(Decimal(item.planning_quantity)),
                    provenance_id=item.provenance_id,
                )
            )
        return tuple(result)

    def build_order_minimum(self, minimum) -> ExactOrderMinimum:
        if isinstance(minimum, WholeQuantityMinimum):
            return ExactOrderMinimum(kind="whole_quantity", value=ExactRatio.from_decimal(Decimal(minimum.quantity)), currency=None)
        if isinstance(minimum, MonetaryAmountMinimum):
            return ExactOrderMinimum(kind="monetary_amount", value=ExactRatio.from_decimal(Decimal(minimum.amount.amount)), currency=minimum.amount.currency)
        return ExactOrderMinimum(kind="none", value=ExactRatio(0), currency=None)

    def build_order_cap(self, cap) -> ExactOrderCap | None:
        if isinstance(cap, NoOrderCap):
            return None
        if isinstance(cap, NotionalOrderCap):
            return ExactOrderCap(kind="notional", value=ExactRatio.from_decimal(Decimal(cap.amount.amount)), currency=cap.amount.currency)
        return ExactOrderCap(kind="quantity", value=ExactRatio.from_decimal(Decimal(cap.quantity)), currency=None)

    def build_transfer_cap(self, item) -> ExactMoney:
        """An absent cap is the whole selected amount of the source."""
        if item.transfer_cap is not None:
            return self.build_money(item.transfer_cap)
        if item.source.kind == "existing_cash":
            return self.build_money(next(cash.selected for cash in self.request.existing_cash if cash.cash_id == item.source.cash_id))
        return self.build_money(next(row.amount for row in self.request.contributions if row.contribution_id == item.source.contribution_id))

    @staticmethod
    def build_limit(limit) -> ExactLimit | None:
        if limit is None:
            return None
        if limit.kind == "amount":
            return ExactLimit(kind="amount", value=ExactRatio.from_decimal(Decimal(limit.amount.amount)))
        return ExactLimit(kind="share", value=ExactRatio.from_decimal(Decimal(limit.share)))

    def build_scenario(self, *, neutral_weights: bool = False) -> ExactPlannerScenario:
        """The exact scenario. ``neutral_weights`` (the preview's counted scenario of targets that do not sum to one, F3a step 8
        of project 67): every entry gets an equal share, so the scenario's invariants hold (the weights sum to one, a cash entry
        says something); the entries themselves, their limits and today's facts are the request's. Nothing the preview answers
        reads a weight; the plan never receives such a scenario."""
        asset_entries = sorted((value for value in self.request.target_weights if value.kind == "asset"), key=lambda value: value.asset_id)
        rebalancer = isinstance(self.request, RebalancerPlannerRequest)
        cash_items = [item for item in sorted((value for value in self.request.target_weights if value.kind == "cash"), key=lambda value: (value.broker_id, value.currency)) if item.minimum is not None or item.maximum is not None or (rebalancer and Decimal(item.weight) != 0)]

        weighted = len(asset_entries) + (len(cash_items) if rebalancer else 0)
        neutral = ExactRatio(1, weighted) if neutral_weights and weighted > 0 else ExactRatio(0)

        def weight_of(item) -> ExactRatio:
            return neutral if neutral_weights else ExactRatio.from_decimal(Decimal(item.weight))

        fx_rates = tuple(
            ExactFxRate(
                pair_first=pair.partition("/")[0],
                pair_second=pair.partition("/")[2],
                rate=ExactRatio.from_decimal(Decimal(rate)),
            )
            for pair, rate in sorted(self.request.fx_rates.items())
        )
        existing_cash = tuple(
            ExactExistingCash(
                cash_id=item.cash_id,
                broker_id=item.broker_id,
                available=self.build_money(item.available),
                selected=self.build_money(item.selected),
                provenance_id=item.provenance_id,
            )
            for item in sorted(self.request.existing_cash, key=lambda value: value.cash_id)
        )
        contributions = tuple(
            ExactContribution(
                contribution_id=item.contribution_id,
                label=item.label,
                amount=self.build_money(item.amount),
                provenance_id=item.provenance_id,
            )
            for item in sorted(self.request.contributions, key=lambda value: value.contribution_id)
        )
        funding_routes = tuple(
            ExactFundingRoute(
                route_id=item.funding_route_id,
                broker_id=item.broker_id,
                source_kind=item.source.kind,
                source_id=item.source.cash_id if item.source.kind == "existing_cash" else item.source.contribution_id,
                currency=item.currency,
                transfer_cap=self.build_transfer_cap(item),
                priority=item.priority,
                provenance_id=item.provenance_id,
            )
            for item in sorted(self.funding_routes, key=lambda value: value.funding_route_id)
        )
        fee_schedules, route_fee_ids = self.build_fee_instances()
        order_routes = tuple(
            ExactOrderRoute(
                route_id=item.route_id,
                broker_id=item.broker_id,
                asset_id=item.asset_id,
                capability_id=item.capability_id,
                fee_schedule_id=route_fee_ids[item.route_id],
                side=item.side,
                minimum_if_active=self.build_order_minimum(item.minimum_if_active),
                cap=self.build_order_cap(item.cap),
                execution_margin_rate=ExactRatio.from_decimal(Decimal(item.execution_margin_rate)),
                priority=item.priority,
                provenance_id=item.provenance_id,
            )
            for item in sorted(self.request.order_routes, key=lambda value: value.route_id)
        )
        return ExactPlannerScenario(
            snapshot=ExactSnapshot(
                snapshot_id=self.request.snapshot.snapshot_id,
                draft_revision=self.request.snapshot.draft_revision,
                captured_at=self.timestamp(self.request.snapshot.captured_at),
            ),
            product="pac" if isinstance(self.request, PacPlannerRequest) else "rebalancer",
            policy=self.request.policy,
            as_of_date=date.fromisoformat(self.request.as_of),
            valuation_currency=self.request.valuation_currency,
            currency_specs=tuple(ExactCurrencySpec(currency=currency, minor_unit=currency_minor_unit(currency)) for currency in sorted(self.currency_references)),
            provenance=self.build_provenance(),
            fx_rates=fx_rates,
            fx_spread_rate=ExactRatio.from_decimal(Decimal(self.request.fx_spread_rate)),
            assets=self.build_assets(),
            brokers=self.build_brokers(fee_schedules),
            holdings=self.build_holdings(),
            existing_cash=existing_cash,
            contributions=contributions,
            funding_routes=funding_routes,
            order_routes=order_routes,
            target_weights=tuple(ExactTargetWeight(asset_id=item.asset_id, weight=weight_of(item), minimum=self.build_limit(item.minimum), maximum=self.build_limit(item.maximum)) for item in asset_entries),
            # Sales and their tax facts enter with C1 and C2 (project 67): the request carries no sale before then.
            sell_context=None,
            # Transfers between Brokers: none in the PAC, whose funding routes stay as the user declares them; the Rebalancer
            # moves cash between every pair of its Brokers (specification §15 n. 2, B3 of project 67).
            transfer_lanes=_rebalancer_lanes(self.request) if isinstance(self.request, RebalancerPlannerRequest) else (),
            # A cash entry with no weight, no minimum and no maximum says nothing: it is left out. The PAC's weight is zero.
            cash_entries=tuple(ExactCashEntry(broker_id=item.broker_id, currency=item.currency, minimum=self.build_limit(item.minimum), maximum=self.build_limit(item.maximum), weight=weight_of(item) if rebalancer else ExactRatio(0)) for item in cash_items),
            # «Balanced» until B3 (project 67) reads the fidelity from the Rebalancer's request (specifica §14 n. 9).
            target_fidelity=exact_fidelity(self.request.target_fidelity) if isinstance(self.request, RebalancerPlannerRequest) else None,
        )

    def run(self) -> PlannerV2NormalizationResult:
        self.validate_snapshot_and_provenance()
        self.validate_assets()
        self.validate_brokers()
        self.validate_holdings()
        self.validate_cash_and_contributions()
        self.validate_order_routes()
        self.validate_fx_rates()
        self.validate_targets()
        self.validate_current_portfolio()
        self.validate_fx_pair_closure()
        self.validate_fx_coherence()
        issues = canonicalize_issues(self.issues)
        availability = normalization_availability(issues)
        normalized = self.build_scenario() if availability == "ready" else None
        # Targets that do not sum to one yet (F3a step 8 of project 67): the plan refuses them, as before (this branch is the
        # preview's only); the preview counts on the scenario anyway, because the total, today's items and the table do not
        # depend on the weights the user is still typing. As with the limits' cross checks, the scenario travels as `counted`.
        if normalized is None and self.request.operation == "preview" and availability == "invalid" and normalization_availability([issue for issue in issues if issue.code not in COUNTED_ANYWAY]) == "ready":
            counted = self._counted_with_neutral_weights()
            if counted is not None:
                limit_issues = self.check_limits(counted)
                self.issues.extend(limit_issues)
                return PlannerV2NormalizationResult(availability=availability, issues=canonicalize_issues(self.issues), normalized=None, limit_problems=canonicalize_issues(limit_issues), counted=counted)
        if normalized is not None:
            limit_issues = self.check_limits(normalized)
            if limit_issues:
                self.issues.extend(limit_issues)
                issues = canonicalize_issues(self.issues)
                return PlannerV2NormalizationResult(
                    availability=normalization_availability(issues),
                    issues=issues,
                    normalized=None,
                    limit_problems=canonicalize_issues(limit_issues),
                    counted=normalized,
                )
        return PlannerV2NormalizationResult(availability=availability, issues=issues, normalized=normalized)

    def _counted_with_neutral_weights(self) -> ExactPlannerScenario | None:
        """The preview's counted scenario of targets that do not sum to one; ``None`` when even neutral weights cannot make a
        scenario (no target entry at all): the preview then answers the refusal, as before."""
        try:
            return self.build_scenario(neutral_weights=True)
        except ValueError:
            # A model invariant the request breaks beyond its weights: the refusal already in `issues` is the answer.
            return None

    def check_limits(self, scenario: ExactPlannerScenario) -> list[PlannerIssue]:
        """The three checks before the calculation (M1, T12), on the built scenario; each names the entries that cause it.

        A scenario with no limit has nothing to check and the replay of the do-nothing plan is not run.
        """
        if not entries_with_limits(scenario):
            return []
        reference = limit_reference_of(scenario)
        problems = [
            *check_minimum_above_maximum(scenario, reference),
            *check_minimums_exceed_reference(scenario, reference, trapped_cash_by_cell(scenario)),
            *check_maximum_below_current(scenario, build_scenario_index(scenario), reference),
        ]
        found: list[PlannerIssue] = []
        for problem in problems:
            field = "maximum" if problem.code == "bound_max_below_current" else "minimum"
            # The sum of the minimums names the two figures it compared (TL-4 of project 67): the sentence says them.
            params = () if problem.sums is None else tuple(MoneyIssueParam(kind="money", name=name, value=PlannerMoneyInput(amount=ratio_to_display_decimal(value), currency=scenario.valuation_currency)) for name, value in zip(("minimums", "reference"), problem.sums, strict=True))
            for entry in problem.entries:
                entity_id = entry.asset_id if entry.kind == "asset" else f"{entry.broker_id}:{entry.currency}"
                found.append(make_issue(normalizer_issue_definition(f"allocation.{problem.code}"), field_path("targets", entry.kind, entity_id, field), params=params))
        return found


def normalize_planner_request(request: _PlannerV2Request, *, source_issues: tuple[PlannerIssue, ...] = ()) -> PlannerV2NormalizationResult:
    """Normalize one frozen Planner v2 request into immutable exact facts."""
    if not isinstance(request, (PacPlannerRequest, RebalancerPlannerRequest)):
        raise TypeError(f"Unsupported Planner v2 request: {type(request).__name__}")
    return _PlannerV2Normalizer(request, source_issues).run()


def normalize_pac_plan(request: PacPlannerRequest, *, source_issues: tuple[PlannerIssue, ...] = ()) -> PlannerV2NormalizationResult:
    """Normalize one frozen PAC v2 request without changing P1 behavior."""
    if not isinstance(request, PacPlannerRequest):
        raise TypeError(f"Expected PacPlannerRequest, got {type(request).__name__}")
    return normalize_planner_request(request, source_issues=source_issues)


def normalize_rebalancer_plan(request: RebalancerPlannerRequest, *, source_issues: tuple[PlannerIssue, ...] = ()) -> PlannerV2NormalizationResult:
    """Normalize one frozen Rebalancer v2 request without changing P1 behavior."""
    if not isinstance(request, RebalancerPlannerRequest):
        raise TypeError(f"Expected Rebalancer Planner request, got {type(request).__name__}")
    return normalize_planner_request(request, source_issues=source_issues)
