"""Normalize bounded PAC and rebalancing drafts without inventing facts."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext

from backend.app.schemas.common import Currency
from backend.app.schemas.pac_allocator import (
    P1_MAX_CURRENCIES,
    P1_MAX_NATIVE_AMOUNT_CHARS,
    AllocationBuyGridInput,
    AllocationContributionInput,
    AllocationInfoIssue,
    AllocationInvalidIssue,
    AllocationIssue,
    AllocationIssueParams,
    AllocationMissingIssue,
    AllocationMoneyInput,
    AllocationUnsupportedIssue,
    AllocationValuationRateInput,
    InfoCode,
    InvalidCode,
    IssueUnit,
    MissingCode,
    PacAnalyzeInput,
    PacAssetInput,
    PathField,
    RebalanceAnalyzeInput,
    RebalanceHoldingInput,
    RebalanceQuoteInput,
    UnsupportedCode,
)
from backend.app.services.pac_allocator.models import (
    Checkpoint,
    Holding,
    PacAsset,
    PacNormalizationResult,
    PacScenario,
    ParsedAsset,
    ParsedContributionVector,
    ParsedGrid,
    ParsedHolding,
    ParsedMoneyVector,
    ParsedQuote,
    ParsedRate,
    ParsedTarget,
    ParsedValue,
    RebalanceNormalizationResult,
    RebalanceScenario,
    Target,
    check_budget,
    unavailable_reason,
)
from backend.app.services.pac_allocator.numeric import (
    HUNDRED,
    ONE,
    ZERO,
    decimal_context,
    decimal_text,
    exact_holding_value,
)

_FIXED_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_CURRENCY = re.compile(r"[A-Z]{3}")
_MAX_DECIMAL_DIGITS = 12
_MAX_QUOTE_BASE = 10**_MAX_DECIMAL_DIGITS - 1
_Path = tuple[PathField | int, ...]
type _AnalyzeInput = PacAnalyzeInput | RebalanceAnalyzeInput


class _Normalizer:
    def __init__(self, request: _AnalyzeInput, checkpoint: Checkpoint | None) -> None:
        self.request = request
        self.checkpoint = checkpoint
        self.issues: list[AllocationIssue] = []
        self.cross_issues: list[AllocationIssue] = []
        self.currencies: set[str] = set()

    @staticmethod
    def _related(path: _Path, indices: list[int] | None) -> list[int]:
        if indices is not None:
            return sorted(set(indices))
        if len(path) > 1 and path[0] in {"assets", "holdings", "targets"} and isinstance(path[1], int):
            return [path[1]]
        return []

    def missing(
        self,
        code: MissingCode,
        path: _Path,
        params: AllocationIssueParams | None = None,
        indices: list[int] | None = None,
        *,
        cross: bool = False,
    ) -> None:
        target = self.cross_issues if cross else self.issues
        target.append(
            AllocationMissingIssue(
                kind="missing",
                code=code,
                path=list(path),
                related_indices=self._related(path, indices),
                params=params or AllocationIssueParams(),
            )
        )

    def invalid(
        self,
        code: InvalidCode,
        path: _Path,
        params: AllocationIssueParams | None = None,
        indices: list[int] | None = None,
        *,
        cross: bool = False,
    ) -> None:
        target = self.cross_issues if cross else self.issues
        target.append(
            AllocationInvalidIssue(
                kind="invalid",
                code=code,
                path=list(path),
                related_indices=self._related(path, indices),
                params=params or AllocationIssueParams(),
            )
        )

    def unsupported(
        self,
        code: UnsupportedCode,
        path: _Path,
        params: AllocationIssueParams | None = None,
        *,
        cross: bool = False,
    ) -> None:
        target = self.cross_issues if cross else self.issues
        target.append(
            AllocationUnsupportedIssue(
                kind="unsupported",
                code=code,
                path=list(path),
                related_indices=self._related(path, None),
                params=params or AllocationIssueParams(),
            )
        )

    def info(self, code: InfoCode, path: _Path, params: AllocationIssueParams | None = None) -> None:
        self.issues.append(
            AllocationInfoIssue(
                kind="info",
                code=code,
                path=list(path),
                related_indices=self._related(path, None),
                params=params or AllocationIssueParams(),
            )
        )

    def number(self, text: str | None, path: _Path, unit: IssueUnit) -> ParsedValue[Decimal]:
        params = AllocationIssueParams(unit=unit)
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
        if len(whole) > _MAX_DECIMAL_DIGITS or len(fraction) > _MAX_DECIMAL_DIGITS:
            self.unsupported(
                "numeric_domain_exceeded",
                path,
                AllocationIssueParams(unit=unit, limit=_MAX_DECIMAL_DIGITS),
            )
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

    def reference_date(
        self,
        raw: str | None,
        path: _Path,
        as_of: date | None = None,
    ) -> tuple[date | None, bool]:
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

    def grid(
        self,
        item: AllocationBuyGridInput | None,
        path: _Path,
        quantity: ParsedValue[Decimal] | None = None,
    ) -> ParsedGrid | None:
        if item is None:
            return None
        mode = item.mode
        if mode is None:
            self.missing("field_required", (*path, "mode"))
        step = self.number(item.quantity_step, (*path, "quantity_step"), "quantity")
        if step.available and step.require() <= ZERO:
            self.invalid("nonpositive_quantity_step", (*path, "quantity_step"))
            step = ParsedValue(None, "input_invalid")
        elif step.available and mode == "whole" and step.require() != step.require().to_integral_value():
            self.invalid("noninteger_whole_step", (*path, "quantity_step"))
            step = ParsedValue(None, "input_invalid")
        if quantity is not None and quantity.available and step.available and mode is not None:
            if quantity.require() % step.require() != ZERO:
                self.info("inventory_off_buy_grid", path[:-1] + ("quantity",))
        return ParsedGrid(mode, step)

    def asset(self, index: int, item: PacAssetInput) -> ParsedAsset:
        path: _Path = ("assets", index)
        name = item.name.strip() if item.name is not None else None
        if not name:
            self.missing("field_required", (*path, "name"))
            name = None
        return ParsedAsset(
            instrument_key=item.instrument_key,
            name=name,
            grid=self.grid(item.buy_grid, (*path, "buy_grid")),
        )

    def quote(
        self,
        item: RebalanceQuoteInput | None,
        path: _Path,
        as_of: date | None,
    ) -> ParsedQuote:
        if item is None:
            self.missing("quote_required", path)
            unavailable = ParsedValue(None, "input_missing")
            return ParsedQuote(unavailable, unavailable, unavailable, None, True)
        price = self.number(item.raw_price, (*path, "raw_price"), "quote")
        if price.available and price.require() <= ZERO:
            self.invalid("nonpositive_price", (*path, "raw_price"))
            price = ParsedValue(None, "input_invalid")
        currency = self.currency(item.currency, (*path, "currency"))
        raw_basis = item.quote_base_quantity
        if raw_basis is None:
            self.missing("field_required", (*path, "quote_base_quantity"))
            basis = ParsedValue(None, "input_missing")
        elif raw_basis <= 0:
            self.invalid("invalid_quote_basis", (*path, "quote_base_quantity"))
            basis = ParsedValue(None, "input_invalid")
        elif raw_basis > _MAX_QUOTE_BASE:
            self.unsupported(
                "numeric_domain_exceeded",
                (*path, "quote_base_quantity"),
                AllocationIssueParams(
                    unit="quantity",
                    limit=_MAX_DECIMAL_DIGITS,
                ),
            )
            basis = ParsedValue(None, "outside_p1_domain")
        else:
            basis = ParsedValue(raw_basis)
        reference, valid_date = self.reference_date(
            item.reference_date,
            (*path, "reference_date"),
            as_of,
        )
        return ParsedQuote(price, currency, basis, reference, valid_date)

    def holding(
        self,
        index: int,
        item: RebalanceHoldingInput,
        as_of: date | None,
    ) -> ParsedHolding:
        path: _Path = ("holdings", index)
        name = item.name.strip() if item.name is not None else None
        if not name:
            self.missing("field_required", (*path, "name"))
            name = None
        quantity = self.number(item.quantity, (*path, "quantity"), "quantity")
        if quantity.available and quantity.require() < ZERO:
            self.unsupported("short_inventory_unsupported", (*path, "quantity"))
            quantity = ParsedValue(None, "outside_p1_domain")
        quote = self.quote(item.quote, (*path, "quote"), as_of)
        if quantity.available and quote.price.available and quote.basis.available:
            try:
                native_value = exact_holding_value(
                    quantity.require(),
                    quote.price.require(),
                    quote.basis.require(),
                )
                if len(decimal_text(native_value)) > P1_MAX_NATIVE_AMOUNT_CHARS:
                    raise ArithmeticError("Holding value exceeds the P1 output domain")
            except ArithmeticError:
                self.unsupported(
                    "numeric_domain_exceeded",
                    (*path, "quote"),
                    AllocationIssueParams(unit="quote", limit=256),
                )
                quote = ParsedQuote(
                    ParsedValue(None, "outside_p1_domain"),
                    quote.currency,
                    quote.basis,
                    quote.reference_date,
                    quote.date_valid,
                )
        return ParsedHolding(
            row_key=item.row_key,
            instrument_key=item.instrument_key,
            name=name,
            quantity=quantity,
            quote=quote,
            grid=self.grid(item.buy_grid, (*path, "buy_grid"), quantity),
        )

    def cash_vector(self, entries: list[AllocationMoneyInput] | None) -> ParsedMoneyVector:
        vector = "cash_balances"
        if entries is None:
            self.missing(
                "cash_vector_required",
                (vector,),
                AllocationIssueParams(vector=vector),
            )
            return ParsedMoneyVector((), "input_missing")
        parsed: list[tuple[ParsedValue[str], ParsedValue[Decimal]]] = []
        indices_by_currency: dict[str, list[int]] = defaultdict(list)
        for index, item in enumerate(entries):
            check_budget(self.checkpoint)
            currency = self.currency(item.currency, (vector, index, "currency"))
            amount = self.number(item.amount, (vector, index, "amount"), "native_amount")
            if amount.available and amount.require() < ZERO:
                self.unsupported("initial_debt_unsupported", (vector, index, "amount"))
                amount = ParsedValue(None, "outside_p1_domain")
            if currency.available:
                indices_by_currency[currency.require()].append(index)
            parsed.append((currency, amount))
        duplicates = {code for code, indices in indices_by_currency.items() if len(indices) > 1}
        for code in sorted(duplicates):
            self.invalid(
                "duplicate_currency",
                (vector, indices_by_currency[code][0], "currency"),
                AllocationIssueParams(currency=code, vector=vector),
                indices=indices_by_currency[code],
                cross=True,
            )
        reason = unavailable_reason(tuple(field for pair in parsed for field in pair))
        if duplicates:
            reason = "input_invalid"
        amounts = tuple((currency.require(), amount.require()) for currency, amount in parsed if currency.available and amount.available and currency.require() not in duplicates)
        return ParsedMoneyVector(amounts, reason)

    def contribution_vector(
        self,
        entries: list[AllocationContributionInput] | None,
    ) -> ParsedContributionVector:
        vector = "contributions"
        if entries is None:
            self.missing(
                "cash_vector_required",
                (vector,),
                AllocationIssueParams(vector=vector),
            )
            return ParsedContributionVector((), "input_missing")
        parsed: list[tuple[ParsedValue[str], ParsedValue[Decimal], ParsedValue[Decimal]]] = []
        for index, item in enumerate(entries):
            check_budget(self.checkpoint)
            currency = self.currency(item.currency, (vector, index, "currency"))
            amount = self.number(item.amount, (vector, index, "amount"), "native_amount")
            if amount.available and amount.require() < ZERO:
                self.invalid("negative_contribution", (vector, index, "amount"))
                amount = ParsedValue(None, "input_invalid")
            monetary_step = self.number(
                item.monetary_step,
                (vector, index, "monetary_step"),
                "native_amount",
            )
            if monetary_step.available and monetary_step.require() <= ZERO:
                self.invalid(
                    "nonpositive_monetary_step",
                    (vector, index, "monetary_step"),
                )
                monetary_step = ParsedValue(None, "input_invalid")
            if amount.available and monetary_step.available and amount.require() % monetary_step.require() != ZERO:
                self.invalid(
                    "contribution_not_multiple_of_monetary_step",
                    (vector, index, "amount"),
                    AllocationIssueParams(unit="native_amount"),
                )
                amount = ParsedValue(None, "input_invalid")
            parsed.append((currency, amount, monetary_step))
        reason = unavailable_reason(tuple(field for entry in parsed for field in entry))
        contributions = tuple((currency.require(), amount.require(), monetary_step.require()) for currency, amount, monetary_step in parsed if currency.available and amount.available and monetary_step.available)
        return ParsedContributionVector(contributions, reason)

    def rate(
        self,
        index: int,
        item: AllocationValuationRateInput,
        report_currency: ParsedValue[str],
        as_of: date | None,
    ) -> ParsedRate | None:
        path: _Path = ("valuation_rates", index)
        currency = self.currency(item.currency, (*path, "currency"), active=False)
        rate = self.number(item.rate_to_report, (*path, "rate_to_report"), "rate")
        if rate.available and rate.require() <= ZERO:
            self.invalid("nonpositive_fx_rate", (*path, "rate_to_report"))
            rate = ParsedValue(None, "input_invalid")
        reference, valid_date = self.reference_date(
            item.reference_date,
            (*path, "reference_date"),
            as_of,
        )
        if currency.available and report_currency.available and currency.require() == report_currency.require() and rate.available:
            if rate.require() != ONE:
                self.invalid(
                    "identity_rate_mismatch",
                    (*path, "rate_to_report"),
                    AllocationIssueParams(currency=currency.require()),
                )
                rate = ParsedValue(None, "input_invalid")
            else:
                self.info(
                    "identity_rate_redundant",
                    path,
                    AllocationIssueParams(currency=currency.require()),
                )
        elif currency.available and rate.available and currency.require() not in self.currencies:
            self.info(
                "unused_valuation_reference",
                path,
                AllocationIssueParams(currency=currency.require()),
            )
        if not valid_date:
            rate = ParsedValue(None, "input_invalid")
        return ParsedRate(currency.require(), rate, reference) if currency.available else None

    def rates(
        self,
        report_currency: ParsedValue[str],
        as_of: date | None,
    ) -> tuple[ParsedRate, ...]:
        by_currency: dict[str, list[tuple[int, ParsedRate]]] = defaultdict(list)
        for index, item in enumerate(self.request.valuation_rates):
            check_budget(self.checkpoint)
            parsed = self.rate(index, item, report_currency, as_of)
            if parsed is not None:
                by_currency[parsed.currency].append((index, parsed))
        result: dict[str, ParsedRate] = {}
        for currency, group in sorted(by_currency.items()):
            if len(group) > 1:
                self.invalid(
                    "duplicate_currency",
                    ("valuation_rates", group[0][0], "currency"),
                    AllocationIssueParams(
                        currency=currency,
                        vector="valuation_rates",
                    ),
                    indices=[index for index, _rate in group],
                    cross=True,
                )
                result[currency] = ParsedRate(
                    currency,
                    ParsedValue(None, "input_invalid"),
                    None,
                )
            else:
                result[currency] = group[0][1]
        if report_currency.available:
            result[report_currency.require()] = ParsedRate(
                report_currency.require(),
                ParsedValue(ONE),
                None,
            )
        return tuple(result[currency] for currency in sorted(result))

    def reference_coverage(
        self,
        report_currency: ParsedValue[str],
        rates: tuple[ParsedRate, ...],
        holdings: list[ParsedHolding] | None = None,
    ) -> bool:
        currency_domain_valid = len(self.currencies) <= P1_MAX_CURRENCIES
        if not currency_domain_valid:
            self.unsupported(
                "currency_domain_exceeded",
                ("report_currency",),
                AllocationIssueParams(limit=P1_MAX_CURRENCIES),
                cross=True,
            )
        elif report_currency.available:
            declared = {item.currency for item in rates}
            for currency in sorted(self.currencies - declared):
                related = []
                if holdings is not None:
                    related = [index for index, holding in enumerate(holdings) if holding.quote.currency.value == currency]
                self.missing(
                    "valuation_rate_required",
                    ("valuation_rates",),
                    AllocationIssueParams(
                        currency=currency,
                        vector="valuation_rates",
                    ),
                    indices=related,
                    cross=True,
                )
        return currency_domain_valid

    def targets(  # noqa: C901 — flat typed validation for identity, coverage, range, and exact total
        self,
        selected: dict[str, list[int]],
        selected_identity_valid: bool,
    ) -> tuple[tuple[ParsedTarget, ...], bool, ParsedValue[Decimal], bool]:
        if not self.request.targets:
            self.missing("targets_required", ("targets",))
        targets: list[ParsedTarget] = []
        indices_by_instrument: dict[str, list[int]] = defaultdict(list)
        for index, item in enumerate(self.request.targets):
            check_budget(self.checkpoint)
            percent = self.number(
                item.target_percent,
                ("targets", index, "target_percent"),
                "percent",
            )
            if percent.available and not ZERO <= percent.require() <= HUNDRED:
                self.invalid(
                    "target_percent_out_of_range",
                    ("targets", index, "target_percent"),
                )
                percent = ParsedValue(None, "input_invalid")
            indices_by_instrument[item.instrument_key].append(index)
            targets.append(ParsedTarget(item.instrument_key, percent))

        target_identity_valid = True
        for instrument_key, indices in sorted(indices_by_instrument.items()):
            if len(indices) > 1:
                target_identity_valid = False
                self.invalid(
                    "duplicate_target_instrument",
                    ("targets", indices[0], "instrument_key"),
                    AllocationIssueParams(instrument_key=instrument_key),
                    indices=indices,
                    cross=True,
                )
            if instrument_key not in selected:
                target_identity_valid = False
                self.invalid(
                    "target_instrument_not_selected",
                    ("targets", indices[0], "instrument_key"),
                    AllocationIssueParams(instrument_key=instrument_key),
                    indices=indices,
                    cross=True,
                )

        for instrument_key, indices in sorted(selected.items()):
            if instrument_key not in indices_by_instrument:
                target_identity_valid = False
                self.missing(
                    "target_required",
                    ("targets",),
                    AllocationIssueParams(instrument_key=instrument_key),
                    indices=indices,
                    cross=True,
                )

        reason = unavailable_reason(tuple(target.percent for target in targets))
        if not targets:
            total = ParsedValue(None, "input_missing")
        elif not selected_identity_valid or not target_identity_valid:
            total = ParsedValue(None, "input_invalid")
        elif reason is not None:
            total = ParsedValue(None, reason)
        else:
            total = ParsedValue(sum((target.percent.require() for target in targets), ZERO))
        targets_valid = total.available and total.require() == HUNDRED
        if total.available and not targets_valid:
            self.invalid(
                "target_total_not_100",
                ("targets",),
                indices=list(range(len(targets))),
                cross=True,
            )
        return tuple(targets), target_identity_valid, total, targets_valid

    @staticmethod
    def _normal_grid(grid: ParsedGrid | None) -> tuple[object | None, Decimal | None]:
        if grid is None:
            return None, None
        if grid.mode is None:
            raise RuntimeError("Ready allocation grid has no mode")
        return grid.mode, grid.step.require()

    def normalized_pac(
        self,
        report_currency: ParsedValue[str],
        as_of: date | None,
        assets: list[ParsedAsset],
        targets: tuple[ParsedTarget, ...],
        cash: ParsedMoneyVector,
        contributions: ParsedContributionVector,
        rates: tuple[ParsedRate, ...],
    ) -> PacScenario:
        normalized_assets = []
        for asset in assets:
            mode, step = self._normal_grid(asset.grid)
            if asset.name is None:
                raise RuntimeError("Ready PAC asset has no name")
            normalized_assets.append(PacAsset(asset.instrument_key, asset.name, mode, step))
        return PacScenario(
            report_currency=report_currency.require(),
            as_of_date=as_of,
            assets=tuple(normalized_assets),
            targets=tuple(Target(target.instrument_key, target.percent.require()) for target in targets),
            cash_balances=tuple(sorted(cash.entries)),
            contributions=tuple(sorted(contributions.entries)),
            valuation_rates=rates,
        )

    def normalized_rebalance(
        self,
        report_currency: ParsedValue[str],
        as_of: date | None,
        holdings: list[ParsedHolding],
        targets: tuple[ParsedTarget, ...],
        cash: ParsedMoneyVector,
        contributions: ParsedContributionVector,
        rates: tuple[ParsedRate, ...],
    ) -> RebalanceScenario:
        normalized_holdings = []
        for holding in holdings:
            mode, step = self._normal_grid(holding.grid)
            if holding.name is None:
                raise RuntimeError("Ready rebalancing holding has no name")
            normalized_holdings.append(
                Holding(
                    row_key=holding.row_key,
                    instrument_key=holding.instrument_key,
                    name=holding.name,
                    quantity=holding.quantity.require(),
                    raw_price=holding.quote.price.require(),
                    currency=holding.quote.currency.require(),
                    quote_base_quantity=holding.quote.basis.require(),
                    reference_date=holding.quote.reference_date,
                    grid_mode=mode,
                    quantity_step=step,
                )
            )
        return RebalanceScenario(
            report_currency=report_currency.require(),
            as_of_date=as_of,
            holdings=tuple(normalized_holdings),
            targets=tuple(Target(target.instrument_key, target.percent.require()) for target in targets),
            cash_balances=tuple(sorted(cash.entries)),
            contributions=tuple(sorted(contributions.entries)),
            valuation_rates=rates,
        )

    def run_pac(self, request: PacAnalyzeInput) -> PacNormalizationResult:
        report_currency = self.currency(request.report_currency, ("report_currency",))
        as_of, _valid_as_of = self.reference_date(
            request.as_of_date,
            ("as_of_date",),
        )
        if not request.assets:
            self.missing("assets_required", ("assets",))
        assets = [self.asset(index, item) for index, item in enumerate(request.assets)]
        by_instrument: dict[str, list[int]] = defaultdict(list)
        for index, asset in enumerate(assets):
            by_instrument[asset.instrument_key].append(index)
        asset_identity_valid = True
        for instrument_key, indices in sorted(by_instrument.items()):
            if len(indices) > 1:
                asset_identity_valid = False
                self.invalid(
                    "duplicate_instrument",
                    ("assets", indices[0], "instrument_key"),
                    AllocationIssueParams(instrument_key=instrument_key),
                    indices=indices,
                    cross=True,
                )
        cash = self.cash_vector(request.cash_balances)
        contributions = self.contribution_vector(request.contributions)
        rates = self.rates(report_currency, as_of)
        currency_domain_valid = self.reference_coverage(report_currency, rates)
        targets, target_identity_valid, target_total, targets_valid = self.targets(
            by_instrument,
            asset_identity_valid,
        )
        issues = tuple(self.issues + self.cross_issues)
        normalized = None
        if all(issue.kind == "info" for issue in issues):
            normalized = self.normalized_pac(
                report_currency,
                as_of,
                assets,
                targets,
                cash,
                contributions,
                rates,
            )
        return PacNormalizationResult(
            report_currency=report_currency,
            as_of_date=as_of,
            assets=tuple(assets),
            targets=targets,
            cash=cash,
            contributions=contributions,
            rates=rates,
            currencies=tuple(sorted(self.currencies)),
            currency_domain_valid=currency_domain_valid,
            asset_identity_valid=asset_identity_valid,
            target_identity_valid=target_identity_valid,
            target_total=target_total,
            targets_valid=targets_valid,
            issues=issues,
            normalized=normalized,
        )

    def run_rebalance(
        self,
        request: RebalanceAnalyzeInput,
    ) -> RebalanceNormalizationResult:
        report_currency = self.currency(request.report_currency, ("report_currency",))
        as_of, _valid_as_of = self.reference_date(
            request.as_of_date,
            ("as_of_date",),
        )
        if not request.holdings:
            self.missing("holdings_required", ("holdings",))
        holdings = [self.holding(index, item, as_of) for index, item in enumerate(request.holdings)]
        rows_by_key: dict[str, list[int]] = defaultdict(list)
        by_instrument: dict[str, list[int]] = defaultdict(list)
        for index, holding in enumerate(holdings):
            rows_by_key[holding.row_key].append(index)
            by_instrument[holding.instrument_key].append(index)
        row_identity_valid = True
        for indices in rows_by_key.values():
            if len(indices) > 1:
                row_identity_valid = False
                self.invalid(
                    "duplicate_row_key",
                    ("holdings", indices[0], "row_key"),
                    indices=indices,
                    cross=True,
                )
        cash = self.cash_vector(request.cash_balances)
        contributions = self.contribution_vector(request.contributions)
        rates = self.rates(report_currency, as_of)
        currency_domain_valid = self.reference_coverage(
            report_currency,
            rates,
            holdings,
        )
        targets, target_identity_valid, target_total, targets_valid = self.targets(
            by_instrument,
            row_identity_valid,
        )
        issues = tuple(self.issues + self.cross_issues)
        normalized = None
        if all(issue.kind == "info" for issue in issues):
            normalized = self.normalized_rebalance(
                report_currency,
                as_of,
                holdings,
                targets,
                cash,
                contributions,
                rates,
            )
        return RebalanceNormalizationResult(
            report_currency=report_currency,
            as_of_date=as_of,
            holdings=tuple(holdings),
            targets=targets,
            cash=cash,
            contributions=contributions,
            rates=rates,
            currencies=tuple(sorted(self.currencies)),
            currency_domain_valid=currency_domain_valid,
            row_identity_valid=row_identity_valid,
            target_identity_valid=target_identity_valid,
            target_total=target_total,
            targets_valid=targets_valid,
            issues=issues,
            normalized=normalized,
        )


def normalize_pac(
    request: PacAnalyzeInput,
    *,
    checkpoint: Checkpoint | None = None,
) -> PacNormalizationResult:
    """Parse a PAC budget-allocation draft and preserve partial dependencies."""
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        result = _Normalizer(request, checkpoint).run_pac(request)
        check_budget(checkpoint)
        return result


def normalize_rebalance(
    request: RebalanceAnalyzeInput,
    *,
    checkpoint: Checkpoint | None = None,
) -> RebalanceNormalizationResult:
    """Parse a portfolio-target draft and preserve partial dependencies."""
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        result = _Normalizer(request, checkpoint).run_rebalance(request)
        check_budget(checkpoint)
        return result
