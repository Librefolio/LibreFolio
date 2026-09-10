"""Typed projection of evaluated facts; no trade proposal or optimality claim."""

from __future__ import annotations

from decimal import Decimal, localcontext

from backend.app.schemas.pac_allocator import AvailableFact, CanonicalScalar, CashPoolFacts, CashPoolList, FactReason, GapRatio, InitialStateTotals, NativeMoney, NormalizedBuyGrid, NormalizedInitialRow, NormalizedMoney, NormalizedQuote, NormalizedValuationRate, PacAnalyzeInvalid, PacAnalyzeNeedsInput, PacAnalyzeOutput, PacAnalyzeReady, PacAnalyzeRowFacts, PacAnalyzeUnsupported, PacInfoIssue, PacNormalizedInitialState, PercentRatio, ReportingMoney, SquaredGapRatio, UnavailableFact
from backend.app.services.pac_allocator.evaluator import reporting_value
from backend.app.services.pac_allocator.models import Checkpoint, InitialEvaluation, InitialState, NormalizationResult, ParsedValue, check_budget
from backend.app.services.pac_allocator.numeric import HUNDRED, RATIO_DECIMAL_PLACES, ZERO, decimal_context, decimal_text, ratio_approximation


def _unavailable(reason: FactReason) -> UnavailableFact:
    return UnavailableFact(availability="unavailable", value=None, reason_codes=[reason])


def _scalar(value: ParsedValue[Decimal]) -> AvailableFact[CanonicalScalar] | UnavailableFact:
    if not value.available:
        return _unavailable(value.reason or "dependency_unavailable")
    return AvailableFact[CanonicalScalar](availability="available", value=decimal_text(value.require()), reason_codes=[])


def _reporting_money(value: ParsedValue[Decimal], currency: ParsedValue[str]) -> AvailableFact[ReportingMoney] | UnavailableFact:
    if not value.available:
        return _unavailable(value.reason or "dependency_unavailable")
    return AvailableFact[ReportingMoney](availability="available", value=ReportingMoney(currency=currency.require(), amount=decimal_text(value.require())), reason_codes=[])


def _percent(numerator: Decimal, denominator: Decimal) -> AvailableFact[PercentRatio]:
    approximation, exact = ratio_approximation(numerator, denominator)
    ratio = PercentRatio(numerator=decimal_text(numerator), denominator=decimal_text(denominator), unit="percent", approximation=approximation, approximation_decimal_places=RATIO_DECIMAL_PLACES, approximation_exact=exact)
    return AvailableFact[PercentRatio](availability="available", value=ratio, reason_codes=[])


def _gap(numerator: Decimal, denominator: Decimal) -> AvailableFact[GapRatio]:
    approximation, exact = ratio_approximation(numerator, denominator)
    ratio = GapRatio(numerator=decimal_text(numerator), denominator=decimal_text(denominator), unit="percentage_points", approximation=approximation, approximation_decimal_places=RATIO_DECIMAL_PLACES, approximation_exact=exact)
    return AvailableFact[GapRatio](availability="available", value=ratio, reason_codes=[])


def _squared_gap(numerator: Decimal, denominator: Decimal) -> AvailableFact[SquaredGapRatio]:
    approximation, exact = ratio_approximation(numerator, denominator)
    ratio = SquaredGapRatio(numerator=decimal_text(numerator), denominator=decimal_text(denominator), unit="percentage_points_squared", approximation=approximation, approximation_decimal_places=RATIO_DECIMAL_PLACES, approximation_exact=exact)
    return AvailableFact[SquaredGapRatio](availability="available", value=ratio, reason_codes=[])


def _ratio_reason(state: NormalizationResult, evaluated: InitialEvaluation, *, target: bool) -> FactReason | None:
    if not evaluated.invested.available:
        return evaluated.invested.reason or "dependency_unavailable"
    if evaluated.invested.require() == ZERO:
        return "zero_initial_invested_value"
    if target and not state.targets_valid:
        return state.target_total.reason or "input_invalid"
    return None


def _normalized(state: InitialState) -> PacNormalizedInitialState:
    return PacNormalizedInitialState(
        report_currency=state.report_currency,
        as_of_date=state.as_of_date.isoformat() if state.as_of_date is not None else None,
        rows=[
            NormalizedInitialRow(
                row_key=row.row_key,
                instrument_key=row.instrument_key,
                name=row.name,
                initial_quantity=decimal_text(row.quantity),
                quote=NormalizedQuote(raw_price=decimal_text(row.raw_price), currency=row.currency, quote_base_quantity=row.quote_base_quantity, reference_date=row.reference_date.isoformat() if row.reference_date is not None else None),
                target_percent=decimal_text(row.target_percent),
                buy_grid=NormalizedBuyGrid(mode=row.grid_mode, quantity_step=decimal_text(row.quantity_step)),
            )
            for row in state.rows
        ],
        cash_balances=[NormalizedMoney(currency=currency, amount=decimal_text(amount)) for currency, amount in state.cash_balances],
        contributions=[NormalizedMoney(currency=currency, amount=decimal_text(amount)) for currency, amount in state.contributions],
        valuation_rates=[NormalizedValuationRate(currency=rate.currency, rate_to_report=decimal_text(rate.rate.require()), reference_date=rate.reference_date.isoformat() if rate.reference_date is not None else None) for rate in state.valuation_rates],
    )


def _cash_pools(state: NormalizationResult, checkpoint: Checkpoint | None) -> AvailableFact[CashPoolList] | UnavailableFact:
    if not state.currency_domain_valid:
        return _unavailable("outside_p1_domain")
    for reason in ("input_invalid", "outside_p1_domain", "input_missing", "dependency_unavailable"):
        if reason in (state.cash.reason, state.contributions.reason):
            return _unavailable(reason)
    existing, contributions = state.cash.amounts(), state.contributions.amounts()
    pools = []
    for currency in state.currencies:
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
                existing_reporting=_reporting_money(reporting_value(ParsedValue(start), currency, state), state.report_currency),
                contribution_reporting=_reporting_money(reporting_value(ParsedValue(new), currency, state), state.report_currency),
                combined_reporting=_reporting_money(reporting_value(ParsedValue(combined), currency, state), state.report_currency),
            )
        )
    return AvailableFact[CashPoolList](availability="available", value=pools, reason_codes=[])


def _finish_report(state: NormalizationResult, rows: list[PacAnalyzeRowFacts], cash_pools: AvailableFact[CashPoolList] | UnavailableFact, totals: InitialStateTotals) -> PacAnalyzeOutput:
    fields = {
        "operation": "analyze",
        "result_kind": "initial_state_analysis",
        "numeric_policy_id": "pac-initial-state-v1",
        "trade_feasibility": "not_evaluated",
        "optimization": "not_run",
        "rows": rows,
        "cash_pools": cash_pools,
        "totals": totals,
    }
    kinds = {issue.kind for issue in state.issues}
    if "invalid" in kinds:
        return PacAnalyzeInvalid(**fields, availability="invalid", normalized=None, issues=list(state.issues))
    if "unsupported" in kinds:
        return PacAnalyzeUnsupported(**fields, availability="unsupported", normalized=None, issues=list(state.issues))
    if "missing" in kinds:
        return PacAnalyzeNeedsInput(**fields, availability="needs_input", normalized=None, issues=list(state.issues))
    if state.normalized is None:
        raise RuntimeError("Ready PAC analysis has no normalized model")
    information = [issue for issue in state.issues if isinstance(issue, PacInfoIssue)]
    return PacAnalyzeReady(**fields, availability="ready", normalized=_normalized(state.normalized), issues=information)


def build_initial_report(state: NormalizationResult, evaluated: InitialEvaluation, *, checkpoint: Checkpoint | None = None) -> PacAnalyzeOutput:
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        rows = []
        weight_reason = _ratio_reason(state, evaluated, target=False)
        gap_reason = _ratio_reason(state, evaluated, target=True)
        for index, (row, values) in enumerate(zip(state.rows, evaluated.rows, strict=True)):
            check_budget(checkpoint)
            native = _unavailable(values.native_value.reason or "dependency_unavailable")
            if values.native_value.available:
                native = AvailableFact[NativeMoney](availability="available", value=NativeMoney(currency=row.quote.currency.require(), amount=decimal_text(values.native_value.require())), reason_codes=[])
            weight = _unavailable(weight_reason) if weight_reason is not None else _percent(HUNDRED * values.reporting_value.require(), evaluated.invested.require())
            if gap_reason is not None:
                gap = _unavailable(gap_reason)
            elif evaluated.gap_numerators is not None:
                gap = _gap(evaluated.gap_numerators[index], evaluated.invested.require())
            else:
                raise RuntimeError("Available PAC target score has no numerator")
            rows.append(
                PacAnalyzeRowFacts(
                    row_index=index,
                    row_key=row.row_key,
                    instrument_key=row.instrument_key,
                    name=row.name,
                    quantity=_scalar(row.quantity),
                    initial_value_native=native,
                    initial_value_reporting=_reporting_money(values.reporting_value, state.report_currency),
                    current_weight_percent=weight,
                    target_percent=_scalar(row.target),
                    deviation_pp=gap,
                )
            )
        if gap_reason is not None:
            maximum = _unavailable(gap_reason)
            squared = _unavailable(gap_reason)
        elif evaluated.max_gap_numerator is not None and evaluated.squared_gap_numerator is not None:
            maximum = _gap(evaluated.max_gap_numerator, evaluated.invested.require())
            squared = _squared_gap(evaluated.squared_gap_numerator, evaluated.invested.require() ** 2)
        else:
            raise RuntimeError("Available PAC total score has no numerator")
        totals = InitialStateTotals(
            initial_invested_reporting=_reporting_money(evaluated.invested, state.report_currency),
            existing_cash_reporting=_reporting_money(evaluated.existing_cash, state.report_currency),
            contributions_reporting=_reporting_money(evaluated.contributions, state.report_currency),
            cash_plus_contributions_reporting=_reporting_money(evaluated.combined_cash, state.report_currency),
            target_total_percent=_scalar(state.target_total),
            max_abs_gap_pp=maximum,
            squared_gap_pp2=squared,
        )
        check_budget(checkpoint)
        return _finish_report(state, rows, _cash_pools(state, checkpoint), totals)
