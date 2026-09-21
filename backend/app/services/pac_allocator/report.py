"""Typed P1 projections with no order, feasibility, or optimality claim."""

from __future__ import annotations

from decimal import Decimal, localcontext

from backend.app.schemas.pac_allocator import (
    AllocationInfoIssue,
    AllocationIssue,
    AvailableFact,
    CanonicalScalar,
    CashPoolFacts,
    CashPoolList,
    FactReason,
    GapRatio,
    NativeMoney,
    NormalizedBuyGrid,
    NormalizedContribution,
    NormalizedHolding,
    NormalizedMoney,
    NormalizedPacAsset,
    NormalizedTarget,
    NormalizedValuationRate,
    PacAllocationFacts,
    PacAnalyzeInvalid,
    PacAnalyzeNeedsInput,
    PacAnalyzeOutput,
    PacAnalyzeReady,
    PacAnalyzeUnsupported,
    PacNormalizedScenario,
    PacTotals,
    PercentRatio,
    RebalanceAnalyzeInvalid,
    RebalanceAnalyzeNeedsInput,
    RebalanceAnalyzeOutput,
    RebalanceAnalyzeReady,
    RebalanceAnalyzeUnsupported,
    RebalanceHoldingFacts,
    RebalanceInstrumentFacts,
    RebalanceNormalizedScenario,
    RebalanceTotals,
    ReportingMoney,
    SquaredGapRatio,
    UnavailableFact,
)
from backend.app.services.pac_allocator.evaluator import reporting_value
from backend.app.services.pac_allocator.models import (
    Checkpoint,
    NormalizationResult,
    PacEvaluation,
    PacNormalizationResult,
    PacScenario,
    ParsedValue,
    RebalanceEvaluation,
    RebalanceNormalizationResult,
    RebalanceScenario,
    check_budget,
)
from backend.app.services.pac_allocator.numeric import (
    HUNDRED,
    RATIO_DECIMAL_PLACES,
    ZERO,
    decimal_context,
    decimal_text,
    ratio_approximation,
)


def _unavailable(reason: FactReason) -> UnavailableFact:
    return UnavailableFact(
        availability="unavailable",
        value=None,
        reason_codes=[reason],
    )


def _scalar(
    value: ParsedValue[Decimal],
) -> AvailableFact[CanonicalScalar] | UnavailableFact:
    if not value.available:
        return _unavailable(value.reason or "dependency_unavailable")
    return AvailableFact[CanonicalScalar](
        availability="available",
        value=decimal_text(value.require()),
        reason_codes=[],
    )


def _reporting_money(
    value: ParsedValue[Decimal],
    currency: ParsedValue[str],
) -> AvailableFact[ReportingMoney] | UnavailableFact:
    if not value.available:
        return _unavailable(value.reason or "dependency_unavailable")
    return AvailableFact[ReportingMoney](
        availability="available",
        value=ReportingMoney(
            currency=currency.require(),
            amount=decimal_text(value.require()),
        ),
        reason_codes=[],
    )


def _native_money(
    value: ParsedValue[Decimal],
    currency: ParsedValue[str],
) -> AvailableFact[NativeMoney] | UnavailableFact:
    if not value.available:
        return _unavailable(value.reason or "dependency_unavailable")
    return AvailableFact[NativeMoney](
        availability="available",
        value=NativeMoney(
            currency=currency.require(),
            amount=decimal_text(value.require()),
        ),
        reason_codes=[],
    )


def _percent(
    numerator: Decimal,
    denominator: Decimal,
) -> AvailableFact[PercentRatio]:
    approximation, exact = ratio_approximation(numerator, denominator)
    return AvailableFact[PercentRatio](
        availability="available",
        value=PercentRatio(
            numerator=decimal_text(numerator),
            denominator=decimal_text(denominator),
            unit="percent",
            approximation=approximation,
            approximation_decimal_places=RATIO_DECIMAL_PLACES,
            approximation_exact=exact,
        ),
        reason_codes=[],
    )


def _gap(
    numerator: Decimal,
    denominator: Decimal,
) -> AvailableFact[GapRatio]:
    approximation, exact = ratio_approximation(numerator, denominator)
    return AvailableFact[GapRatio](
        availability="available",
        value=GapRatio(
            numerator=decimal_text(numerator),
            denominator=decimal_text(denominator),
            unit="percentage_points",
            approximation=approximation,
            approximation_decimal_places=RATIO_DECIMAL_PLACES,
            approximation_exact=exact,
        ),
        reason_codes=[],
    )


def _squared_gap(
    numerator: Decimal,
    denominator: Decimal,
) -> AvailableFact[SquaredGapRatio]:
    approximation, exact = ratio_approximation(numerator, denominator)
    return AvailableFact[SquaredGapRatio](
        availability="available",
        value=SquaredGapRatio(
            numerator=decimal_text(numerator),
            denominator=decimal_text(denominator),
            unit="percentage_points_squared",
            approximation=approximation,
            approximation_decimal_places=RATIO_DECIMAL_PLACES,
            approximation_exact=exact,
        ),
        reason_codes=[],
    )


def _normalized_common(
    state: PacScenario | RebalanceScenario,
) -> dict[str, object]:
    return {
        "report_currency": state.report_currency,
        "as_of_date": (state.as_of_date.isoformat() if state.as_of_date is not None else None),
        "targets": [
            NormalizedTarget(
                instrument_key=target.instrument_key,
                target_percent=decimal_text(target.percent),
            )
            for target in state.targets
        ],
        "cash_balances": [NormalizedMoney(currency=currency, amount=decimal_text(amount)) for currency, amount in state.cash_balances],
        "contributions": [
            NormalizedContribution(
                currency=currency,
                amount=decimal_text(amount),
                monetary_step=decimal_text(monetary_step),
            )
            for currency, amount, monetary_step in state.contributions
        ],
        "valuation_rates": [
            NormalizedValuationRate(
                currency=rate.currency,
                rate_to_report=decimal_text(rate.rate.require()),
                reference_date=(rate.reference_date.isoformat() if rate.reference_date is not None else None),
            )
            for rate in state.valuation_rates
        ],
    }


def _normalized_pac(state: PacScenario) -> PacNormalizedScenario:
    return PacNormalizedScenario(
        **_normalized_common(state),
        assets=[
            NormalizedPacAsset(
                instrument_key=asset.instrument_key,
                name=asset.name,
                buy_grid=(
                    NormalizedBuyGrid(
                        mode=asset.grid_mode,
                        quantity_step=decimal_text(asset.quantity_step),
                    )
                    if asset.grid_mode is not None and asset.quantity_step is not None
                    else None
                ),
            )
            for asset in state.assets
        ],
    )


def _normalized_rebalance(
    state: RebalanceScenario,
) -> RebalanceNormalizedScenario:
    return RebalanceNormalizedScenario(
        **_normalized_common(state),
        holdings=[
            NormalizedHolding(
                row_key=holding.row_key,
                instrument_key=holding.instrument_key,
                name=holding.name,
                quantity=decimal_text(holding.quantity),
                raw_price=decimal_text(holding.raw_price),
                currency=holding.currency,
                quote_base_quantity=holding.quote_base_quantity,
                reference_date=(holding.reference_date.isoformat() if holding.reference_date is not None else None),
                buy_grid=(
                    NormalizedBuyGrid(
                        mode=holding.grid_mode,
                        quantity_step=decimal_text(holding.quantity_step),
                    )
                    if holding.grid_mode is not None and holding.quantity_step is not None
                    else None
                ),
            )
            for holding in state.holdings
        ],
    )


def _cash_pools(
    state: NormalizationResult,
    checkpoint: Checkpoint | None,
) -> AvailableFact[CashPoolList] | UnavailableFact:
    if not state.currency_domain_valid:
        return _unavailable("outside_p1_domain")
    for reason in (
        "input_invalid",
        "outside_p1_domain",
        "input_missing",
        "dependency_unavailable",
    ):
        if reason in (state.cash.reason, state.contributions.reason):
            return _unavailable(reason)
    existing = state.cash.amounts()
    contributions = state.contributions.amounts()
    pool_currencies = sorted(set(existing) | set(contributions))
    pools = []
    for currency in pool_currencies:
        check_budget(checkpoint)
        start = existing.get(currency, ZERO)
        new = contributions.get(currency, ZERO)
        combined = start + new
        pools.append(
            CashPoolFacts(
                currency=currency,
                existing_amount=decimal_text(start),
                contribution_amount=decimal_text(new),
                combined_amount=decimal_text(combined),
                existing_reporting=_reporting_money(
                    reporting_value(ParsedValue(start), currency, state),
                    state.report_currency,
                ),
                contribution_reporting=_reporting_money(
                    reporting_value(ParsedValue(new), currency, state),
                    state.report_currency,
                ),
                combined_reporting=_reporting_money(
                    reporting_value(ParsedValue(combined), currency, state),
                    state.report_currency,
                ),
            )
        )
    return AvailableFact[CashPoolList](
        availability="available",
        value=pools,
        reason_codes=[],
    )


def _availability(issues: tuple[AllocationIssue, ...]) -> str:
    kinds = {issue.kind for issue in issues}
    if "invalid" in kinds:
        return "invalid"
    if "unsupported" in kinds:
        return "unsupported"
    if "missing" in kinds:
        return "needs_input"
    return "ready"


def build_pac_report(
    state: PacNormalizationResult,
    evaluated: PacEvaluation,
    *,
    checkpoint: Checkpoint | None = None,
) -> PacAnalyzeOutput:
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        names = {asset.instrument_key: asset.name for asset in state.assets}
        allocations = []
        for index, (target, ideal) in enumerate(zip(state.targets, evaluated.allocations, strict=True)):
            check_budget(checkpoint)
            allocations.append(
                PacAllocationFacts(
                    target_index=index,
                    instrument_key=target.instrument_key,
                    name=names.get(target.instrument_key),
                    target_percent=_scalar(target.percent),
                    ideal_allocation_reporting=_reporting_money(
                        ideal,
                        state.report_currency,
                    ),
                )
            )
        totals = PacTotals(
            existing_cash_reporting=_reporting_money(
                evaluated.money.existing_cash,
                state.report_currency,
            ),
            contributions_reporting=_reporting_money(
                evaluated.money.contributions,
                state.report_currency,
            ),
            investable_budget_reporting=_reporting_money(
                evaluated.money.combined_cash,
                state.report_currency,
            ),
            target_total_percent=_scalar(state.target_total),
        )
        fields = {
            "operation": "analyze",
            "result_kind": "pac_budget_analysis",
            "numeric_policy_id": "pac-budget-allocation-v1",
            "allocations": allocations,
            "cash_pools": _cash_pools(state, checkpoint),
            "totals": totals,
        }
        availability = _availability(state.issues)
        check_budget(checkpoint)
        if availability == "invalid":
            return PacAnalyzeInvalid(
                **fields,
                availability="invalid",
                normalized=None,
                issues=list(state.issues),
            )
        if availability == "unsupported":
            return PacAnalyzeUnsupported(
                **fields,
                availability="unsupported",
                normalized=None,
                issues=list(state.issues),
            )
        if availability == "needs_input":
            return PacAnalyzeNeedsInput(
                **fields,
                availability="needs_input",
                normalized=None,
                issues=list(state.issues),
            )
        if state.normalized is None:
            raise RuntimeError("Ready PAC analysis has no normalized scenario")
        information = [issue for issue in state.issues if isinstance(issue, AllocationInfoIssue)]
        return PacAnalyzeReady(
            **fields,
            availability="ready",
            normalized=_normalized_pac(state.normalized),
            issues=information,
        )


def build_rebalance_report(  # noqa: C901 — sequential projection of typed facts and availability branches
    state: RebalanceNormalizationResult,
    evaluated: RebalanceEvaluation,
    *,
    checkpoint: Checkpoint | None = None,
) -> RebalanceAnalyzeOutput:
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        holdings = []
        indices_by_instrument: dict[str, list[int]] = {}
        names: dict[str, str | None] = {}
        for index, (holding, values) in enumerate(zip(state.holdings, evaluated.holdings, strict=True)):
            check_budget(checkpoint)
            indices_by_instrument.setdefault(holding.instrument_key, []).append(index)
            names.setdefault(holding.instrument_key, holding.name)
            holdings.append(
                RebalanceHoldingFacts(
                    holding_index=index,
                    row_key=holding.row_key,
                    instrument_key=holding.instrument_key,
                    name=holding.name,
                    quantity=_scalar(holding.quantity),
                    current_value_native=_native_money(
                        values.native_value,
                        holding.quote.currency,
                    ),
                    current_value_reporting=_reporting_money(
                        values.reporting_value,
                        state.report_currency,
                    ),
                )
            )

        instruments = []
        for index, (target, values) in enumerate(zip(state.targets, evaluated.instruments, strict=True)):
            check_budget(checkpoint)
            if not evaluated.invested.available:
                ratio_reason = evaluated.invested.reason or "dependency_unavailable"
            elif evaluated.invested.require() == ZERO:
                ratio_reason = "zero_invested_value"
            elif not values.current_reporting.available:
                ratio_reason = values.current_reporting.reason or "dependency_unavailable"
            else:
                ratio_reason = None
            current_weight = (
                _unavailable(ratio_reason)
                if ratio_reason is not None
                else _percent(
                    HUNDRED * values.current_reporting.require(),
                    evaluated.invested.require(),
                )
            )
            if ratio_reason is not None:
                gap = _unavailable(ratio_reason)
            elif values.gap_numerator is None:
                gap = _unavailable(target.percent.reason or state.target_total.reason or "input_invalid")
            else:
                gap = _gap(
                    values.gap_numerator,
                    evaluated.invested.require(),
                )
            instruments.append(
                RebalanceInstrumentFacts(
                    target_index=index,
                    instrument_key=target.instrument_key,
                    name=names.get(target.instrument_key),
                    custody_context_count=len(indices_by_instrument.get(target.instrument_key, [])),
                    current_value_reporting=_reporting_money(
                        values.current_reporting,
                        state.report_currency,
                    ),
                    current_weight_percent=current_weight,
                    target_percent=_scalar(target.percent),
                    target_value_reporting=_reporting_money(
                        values.target_value_reporting,
                        state.report_currency,
                    ),
                    value_gap_to_target_reporting=_reporting_money(
                        values.value_gap_reporting,
                        state.report_currency,
                    ),
                    gap_to_target_pp=gap,
                )
            )

        if not evaluated.invested.available:
            total_gap_reason = evaluated.invested.reason or "dependency_unavailable"
        elif evaluated.invested.require() == ZERO:
            total_gap_reason = "zero_invested_value"
        elif not state.targets_valid:
            total_gap_reason = state.target_total.reason or "input_invalid"
        else:
            total_gap_reason = None
        if total_gap_reason is not None:
            maximum = _unavailable(total_gap_reason)
            squared = _unavailable(total_gap_reason)
        elif evaluated.max_gap_numerator is not None and evaluated.squared_gap_numerator is not None:
            maximum = _gap(
                evaluated.max_gap_numerator,
                evaluated.invested.require(),
            )
            squared = _squared_gap(
                evaluated.squared_gap_numerator,
                evaluated.invested.require() ** 2,
            )
        else:
            maximum = _unavailable("dependency_unavailable")
            squared = _unavailable("dependency_unavailable")

        totals = RebalanceTotals(
            current_invested_reporting=_reporting_money(
                evaluated.invested,
                state.report_currency,
            ),
            existing_cash_reporting=_reporting_money(
                evaluated.money.existing_cash,
                state.report_currency,
            ),
            contributions_reporting=_reporting_money(
                evaluated.money.contributions,
                state.report_currency,
            ),
            cash_plus_contributions_reporting=_reporting_money(
                evaluated.money.combined_cash,
                state.report_currency,
            ),
            target_total_percent=_scalar(state.target_total),
            max_abs_gap_pp=maximum,
            squared_gap_pp2=squared,
        )
        fields = {
            "operation": "analyze",
            "result_kind": "portfolio_rebalancing_analysis",
            "numeric_policy_id": "portfolio-rebalancing-v1",
            "holdings": holdings,
            "instruments": instruments,
            "cash_pools": _cash_pools(state, checkpoint),
            "totals": totals,
        }
        availability = _availability(state.issues)
        check_budget(checkpoint)
        if availability == "invalid":
            return RebalanceAnalyzeInvalid(
                **fields,
                availability="invalid",
                normalized=None,
                issues=list(state.issues),
            )
        if availability == "unsupported":
            return RebalanceAnalyzeUnsupported(
                **fields,
                availability="unsupported",
                normalized=None,
                issues=list(state.issues),
            )
        if availability == "needs_input":
            return RebalanceAnalyzeNeedsInput(
                **fields,
                availability="needs_input",
                normalized=None,
                issues=list(state.issues),
            )
        if state.normalized is None:
            raise RuntimeError("Ready rebalancing analysis has no normalized scenario")
        information = [issue for issue in state.issues if isinstance(issue, AllocationInfoIssue)]
        return RebalanceAnalyzeReady(
            **fields,
            availability="ready",
            normalized=_normalized_rebalance(state.normalized),
            issues=information,
        )
