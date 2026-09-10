"""Normalize a bounded manual draft without inventing missing financial values."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext
from typing import Literal

from backend.app.schemas.common import Currency
from backend.app.schemas.pac_allocator import (
    P1_MAX_CURRENCIES,
    InfoCode,
    InvalidCode,
    IssueUnit,
    MissingCode,
    PacAnalyzeInput,
    PacAnalyzeIssue,
    PacAnalyzeRowInput,
    PacInfoIssue,
    PacInvalidIssue,
    PacIssueParams,
    PacMissingIssue,
    PacMoneyInput,
    PacQuoteInput,
    PacUnsupportedIssue,
    PacValuationRateInput,
    PathField,
    UnsupportedCode,
)
from backend.app.services.pac_allocator.models import Checkpoint, InitialRow, InitialState, NormalizationResult, ParsedGrid, ParsedMoneyVector, ParsedQuote, ParsedRate, ParsedRow, ParsedValue, check_budget, unavailable_reason
from backend.app.services.pac_allocator.numeric import HUNDRED, ONE, ZERO, decimal_context

_FIXED_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_CURRENCY = re.compile(r"[A-Z]{3}")
_Path = tuple[PathField | int, ...]


class _Normalizer:
    def __init__(self, request: PacAnalyzeInput, checkpoint: Checkpoint | None) -> None:
        self.request = request
        self.checkpoint = checkpoint
        self.issues: list[PacAnalyzeIssue] = []
        self.cross_issues: list[PacAnalyzeIssue] = []
        self.currencies: set[str] = set()

    @staticmethod
    def _related(path: _Path, indices: list[int] | None) -> list[int]:
        if indices is not None:
            return sorted(set(indices))
        return [path[1]] if len(path) > 1 and path[0] == "rows" and isinstance(path[1], int) else []

    def missing(self, code: MissingCode, path: _Path, params: PacIssueParams | None = None, indices: list[int] | None = None, *, cross: bool = False) -> None:
        target = self.cross_issues if cross else self.issues
        target.append(PacMissingIssue(kind="missing", code=code, path=list(path), related_row_indices=self._related(path, indices), params=params or PacIssueParams()))

    def invalid(self, code: InvalidCode, path: _Path, params: PacIssueParams | None = None, indices: list[int] | None = None, *, cross: bool = False) -> None:
        target = self.cross_issues if cross else self.issues
        target.append(PacInvalidIssue(kind="invalid", code=code, path=list(path), related_row_indices=self._related(path, indices), params=params or PacIssueParams()))

    def unsupported(self, code: UnsupportedCode, path: _Path, params: PacIssueParams | None = None, *, cross: bool = False) -> None:
        target = self.cross_issues if cross else self.issues
        target.append(PacUnsupportedIssue(kind="unsupported", code=code, path=list(path), related_row_indices=self._related(path, None), params=params or PacIssueParams()))

    def info(self, code: InfoCode, path: _Path, params: PacIssueParams | None = None) -> None:
        self.issues.append(PacInfoIssue(kind="info", code=code, path=list(path), related_row_indices=self._related(path, None), params=params or PacIssueParams()))

    def number(self, text: str | None, path: _Path, unit: IssueUnit) -> ParsedValue[Decimal]:
        params = PacIssueParams(unit=unit)
        if text is None or not text.strip():
            self.missing("field_required", path, params)
            return ParsedValue(None, "input_missing")
        raw = text.strip()
        if raw in ("+", "-", ".", "+.", "-."):
            self.missing("incomplete_decimal", path, params)
            return ParsedValue(None, "input_missing")
        if _FIXED_DECIMAL.fullmatch(raw) is None:
            self.invalid("invalid_decimal_syntax", path, params)
            return ParsedValue(None, "input_invalid")
        negative = raw.startswith("-")
        unsigned = raw.lstrip("+-")
        whole, _, fraction = unsigned.partition(".")
        whole = whole.lstrip("0") or "0"
        fraction = fraction.rstrip("0")
        if len(whole) > 12 or len(fraction) > 12:
            self.unsupported("numeric_domain_exceeded", path, PacIssueParams(unit=unit, limit=12))
            return ParsedValue(None, "outside_p1_domain")
        canonical = f"{whole}.{fraction}" if fraction else whole
        if negative and canonical != "0":
            canonical = f"-{canonical}"
        return ParsedValue(Decimal(canonical))

    def currency(self, raw: str | None, path: _Path, *, active: bool = True) -> ParsedValue[str]:
        if raw is None or not raw.strip():
            self.missing("field_required", path)
            return ParsedValue(None, "input_missing")
        code = raw.strip().upper()
        if _CURRENCY.fullmatch(code) is None:
            self.invalid("invalid_currency", path)
            return ParsedValue(None, "input_invalid")
        try:
            code = Currency.validate_code(code)
        except ValueError:
            self.invalid("invalid_currency", path)
            return ParsedValue(None, "input_invalid")
        if active:
            self.currencies.add(code)
        return ParsedValue(code)

    def reference_date(self, raw: str | None, path: _Path, as_of: date | None = None) -> tuple[date | None, bool]:
        if raw is None or not raw.strip():
            self.info("reference_date_unspecified", path)
            return None, True
        if _DATE.fullmatch(raw) is None:
            self.invalid("invalid_date", path)
            return None, False
        try:
            parsed = date.fromisoformat(raw)
        except ValueError:
            self.invalid("invalid_date", path)
            return None, False
        if as_of is not None and parsed > as_of:
            self.invalid("reference_after_asof", path)
            return parsed, False
        return parsed, True

    def quote(self, quote: PacQuoteInput | None, path: _Path, as_of: date | None) -> ParsedQuote:
        if quote is None:
            self.missing("quote_required", path)
            return ParsedQuote(ParsedValue(None, "input_missing"), ParsedValue(None, "input_missing"), ParsedValue(None, "input_missing"), None, True)
        price = self.number(quote.raw_price, (*path, "raw_price"), "quote")
        if price.available and price.require() <= ZERO:
            self.invalid("nonpositive_price", (*path, "raw_price"))
            price = ParsedValue(None, "input_invalid")
        currency = self.currency(quote.currency, (*path, "currency"))
        raw_basis = quote.quote_base_quantity
        if raw_basis is None:
            self.missing("field_required", (*path, "quote_base_quantity"))
            basis = ParsedValue(None, "input_missing")
        elif raw_basis <= 0:
            self.invalid("invalid_quote_basis", (*path, "quote_base_quantity"))
            basis = ParsedValue(None, "input_invalid")
        elif raw_basis not in (1, 100):
            self.unsupported("quote_basis_unsupported", (*path, "quote_base_quantity"), PacIssueParams(allowed_quote_bases=[1, 100]))
            basis = ParsedValue(None, "outside_p1_domain")
        else:
            basis = ParsedValue(raw_basis)
        reference, valid_date = self.reference_date(quote.reference_date, (*path, "reference_date"), as_of)
        return ParsedQuote(price, currency, basis, reference, valid_date)

    def row(self, index: int, row: PacAnalyzeRowInput, as_of: date | None) -> ParsedRow:
        path: _Path = ("rows", index)
        name = row.name.strip() if row.name is not None else None
        if not name:
            self.missing("field_required", (*path, "name"))
            name = None
        quantity = self.number(row.initial_quantity, (*path, "initial_quantity"), "quantity")
        if quantity.available and quantity.require() < ZERO:
            self.unsupported("short_inventory_unsupported", (*path, "initial_quantity"))
            quantity = ParsedValue(None, "outside_p1_domain")
        quote = self.quote(row.quote, (*path, "quote"), as_of)
        target = self.number(row.target_percent, (*path, "target_percent"), "percent")
        if target.available and not ZERO <= target.require() <= HUNDRED:
            self.invalid("target_percent_out_of_range", (*path, "target_percent"))
            target = ParsedValue(None, "input_invalid")
        if row.buy_grid is None:
            self.missing("grid_required", (*path, "buy_grid"))
            grid = ParsedGrid(None, ParsedValue(None, "input_missing"))
        else:
            mode = row.buy_grid.mode
            if mode is None:
                self.missing("field_required", (*path, "buy_grid", "mode"))
            step = self.number(row.buy_grid.quantity_step, (*path, "buy_grid", "quantity_step"), "quantity")
            if step.available and step.require() <= ZERO:
                self.invalid("nonpositive_quantity_step", (*path, "buy_grid", "quantity_step"))
                step = ParsedValue(None, "input_invalid")
            elif step.available and mode == "whole" and step.require() != step.require().to_integral_value():
                self.invalid("noninteger_whole_step", (*path, "buy_grid", "quantity_step"))
                step = ParsedValue(None, "input_invalid")
            grid = ParsedGrid(mode, step)
            if quantity.available and step.available and mode is not None and quantity.require() % step.require() != ZERO:
                self.info("inventory_off_buy_grid", (*path, "initial_quantity"))
        return ParsedRow(row.row_key, row.instrument_key, name, quantity, quote, target, grid)

    def money_vector(self, entries: list[PacMoneyInput] | None, vector: Literal["cash_balances", "contributions"]) -> ParsedMoneyVector:
        if entries is None:
            self.missing("cash_vector_required", (vector,), PacIssueParams(vector=vector))
            return ParsedMoneyVector((), "input_missing")
        parsed: list[tuple[ParsedValue[str], ParsedValue[Decimal]]] = []
        indices_by_currency: dict[str, list[int]] = defaultdict(list)
        for index, item in enumerate(entries):
            check_budget(self.checkpoint)
            currency = self.currency(item.currency, (vector, index, "currency"))
            amount = self.number(item.amount, (vector, index, "amount"), "native_amount")
            if amount.available and amount.require() < ZERO:
                if vector == "contributions":
                    self.invalid("negative_contribution", (vector, index, "amount"))
                    amount = ParsedValue(None, "input_invalid")
                else:
                    self.unsupported("initial_debt_unsupported", (vector, index, "amount"))
                    amount = ParsedValue(None, "outside_p1_domain")
            if currency.available:
                indices_by_currency[currency.require()].append(index)
            parsed.append((currency, amount))
        duplicates = {code for code, indices in indices_by_currency.items() if len(indices) > 1}
        for code in sorted(duplicates):
            self.invalid("duplicate_currency", (vector, indices_by_currency[code][0], "currency"), PacIssueParams(currency=code, vector=vector), cross=True)
        reason = unavailable_reason(tuple(field for pair in parsed for field in pair))
        if duplicates:
            reason = "input_invalid"
        amounts = tuple((currency.require(), amount.require()) for currency, amount in parsed if currency.available and amount.available and currency.require() not in duplicates)
        return ParsedMoneyVector(amounts, reason)

    def _rate(self, index: int, item: PacValuationRateInput, report_currency: ParsedValue[str], as_of: date | None) -> ParsedRate | None:
        path: _Path = ("valuation_rates", index)
        currency = self.currency(item.currency, (*path, "currency"), active=False)
        rate = self.number(item.rate_to_report, (*path, "rate_to_report"), "rate")
        if rate.available and rate.require() <= ZERO:
            self.invalid("nonpositive_fx_rate", (*path, "rate_to_report"))
            rate = ParsedValue(None, "input_invalid")
        reference, valid_date = self.reference_date(item.reference_date, (*path, "reference_date"), as_of)
        if currency.available and report_currency.available and currency.require() == report_currency.require() and rate.available:
            if rate.require() != ONE:
                self.invalid("identity_rate_mismatch", (*path, "rate_to_report"), PacIssueParams(currency=currency.require()))
                rate = ParsedValue(None, "input_invalid")
            else:
                self.info("identity_rate_redundant", path, PacIssueParams(currency=currency.require()))
        elif currency.available and rate.available and currency.require() not in self.currencies:
            self.info("unused_valuation_reference", path, PacIssueParams(currency=currency.require()))
        if not valid_date:
            rate = ParsedValue(None, "input_invalid")
        return ParsedRate(currency.require(), rate, reference) if currency.available else None

    def rates(self, report_currency: ParsedValue[str], as_of: date | None) -> tuple[ParsedRate, ...]:
        by_currency: dict[str, list[tuple[int, ParsedRate]]] = defaultdict(list)
        for index, item in enumerate(self.request.valuation_rates):
            check_budget(self.checkpoint)
            parsed = self._rate(index, item, report_currency, as_of)
            if parsed is not None:
                by_currency[parsed.currency].append((index, parsed))
        result: dict[str, ParsedRate] = {}
        for currency, group in sorted(by_currency.items()):
            if len(group) > 1:
                self.invalid("duplicate_currency", ("valuation_rates", group[0][0], "currency"), PacIssueParams(currency=currency, vector="valuation_rates"), cross=True)
                result[currency] = ParsedRate(currency, ParsedValue(None, "input_invalid"), None)
            else:
                result[currency] = group[0][1]
        if report_currency.available:
            # Identity is mathematical, not a supplied quote that can redefine R/R.
            result[report_currency.require()] = ParsedRate(report_currency.require(), ParsedValue(ONE), None)
        return tuple(result[currency] for currency in sorted(result))

    def _row_identity(self, row_groups: dict[str, list[int]]) -> bool:
        identity_valid = True
        for indices in row_groups.values():
            if len(indices) > 1:
                identity_valid = False
                self.invalid("duplicate_row_key", ("rows", indices[0], "row_key"), indices=indices, cross=True)
        return identity_valid

    def _reference_coverage(self, report_currency: ParsedValue[str], rows: list[ParsedRow], rates: tuple[ParsedRate, ...]) -> bool:
        currency_domain_valid = len(self.currencies) <= P1_MAX_CURRENCIES
        if not currency_domain_valid:
            self.unsupported("currency_domain_exceeded", ("report_currency",), PacIssueParams(limit=P1_MAX_CURRENCIES), cross=True)
        elif report_currency.available:
            declared = {item.currency for item in rates}
            for currency in sorted(self.currencies - declared):
                related = [index for index, row in enumerate(rows) if row.quote.currency.value == currency]
                self.missing("valuation_rate_required", ("valuation_rates",), PacIssueParams(currency=currency, vector="valuation_rates"), indices=related, cross=True)
        return currency_domain_valid

    def _targets(self, rows: list[ParsedRow], identity_valid: bool) -> tuple[ParsedValue[Decimal], bool]:
        target_reason = unavailable_reason(tuple(row.target for row in rows))
        if not rows:
            target_total = ParsedValue(None, "input_missing")
        elif not identity_valid:
            target_total = ParsedValue(None, "input_invalid")
        elif target_reason is not None:
            target_total = ParsedValue(None, target_reason)
        else:
            target_total = ParsedValue(sum((row.target.require() for row in rows), ZERO))
        targets_valid = target_total.available and target_total.require() == HUNDRED
        if target_total.available and not targets_valid:
            self.invalid("target_total_not_100", ("rows",), indices=list(range(len(rows))), cross=True)
        return target_total, targets_valid

    def _normalized_state(self, rows: list[ParsedRow], cash: ParsedMoneyVector, contributions: ParsedMoneyVector, rates: tuple[ParsedRate, ...], report_currency: ParsedValue[str], as_of: date | None) -> InitialState:
        normalized_rows: list[InitialRow] = []
        for row in rows:
            if row.name is None or row.grid.mode is None:
                raise RuntimeError("Ready PAC row is incomplete")
            normalized_rows.append(InitialRow(row.row_key, row.instrument_key, row.name, row.quantity.require(), row.quote.price.require(), row.quote.currency.require(), row.quote.basis.require(), row.quote.reference_date, row.target.require(), row.grid.mode, row.grid.step.require()))
        cash_map, contribution_map = cash.amounts(), contributions.amounts()
        return InitialState(report_currency.require(), as_of, tuple(normalized_rows), tuple((code, cash_map.get(code, ZERO)) for code in sorted(self.currencies)), tuple((code, contribution_map.get(code, ZERO)) for code in sorted(self.currencies)), rates)

    def run(self) -> NormalizationResult:
        check_budget(self.checkpoint)
        report_currency = self.currency(self.request.report_currency, ("report_currency",))
        as_of, _ = self.reference_date(self.request.as_of_date, ("as_of_date",))
        if not self.request.rows:
            self.missing("rows_required", ("rows",))
        rows: list[ParsedRow] = []
        row_groups: dict[str, list[int]] = defaultdict(list)
        for index, item in enumerate(self.request.rows):
            check_budget(self.checkpoint)
            rows.append(self.row(index, item, as_of))
            row_groups[item.row_key].append(index)
        cash = self.money_vector(self.request.cash_balances, "cash_balances")
        contributions = self.money_vector(self.request.contributions, "contributions")
        rates = self.rates(report_currency, as_of)
        identity_valid = self._row_identity(row_groups)
        currency_domain_valid = self._reference_coverage(report_currency, rows, rates)
        target_total, targets_valid = self._targets(rows, identity_valid)
        issues = tuple(self.issues + self.cross_issues)
        normalized = self._normalized_state(rows, cash, contributions, rates, report_currency, as_of) if all(item.kind == "info" for item in issues) else None
        check_budget(self.checkpoint)
        return NormalizationResult(report_currency, as_of, tuple(rows), cash, contributions, rates, tuple(sorted(self.currencies)), currency_domain_valid, identity_valid, target_total, targets_valid, issues, normalized)


def normalize_initial_state(request: PacAnalyzeInput, *, checkpoint: Checkpoint | None = None) -> NormalizationResult:
    """Parse and validate all bounded draft fields; keep independent partial values."""
    with localcontext(decimal_context()):
        return _Normalizer(request, checkpoint).run()
