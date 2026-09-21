"""Normalize bounded PAC and rebalancing drafts without inventing facts."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, localcontext

from backend.app.schemas.common import Currency
from backend.app.schemas.pac_allocator import (
    P1_MAX_CURRENCIES,
    P1_MAX_NATIVE_AMOUNT_CHARS,
    AcceptedStaleObservation,
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
    AmountFeeCap,
    DomainAssetIdentity,
    DomainBrokerIdentity,
    DomainCopyProvenance,
    FiniteDecimal,
    IdIssueParam,
    InfoCode,
    InvalidCode,
    IssueUnit,
    ManualProvenance,
    MissingCode,
    MonetaryAmountCapability,
    MonetaryAmountMinimum,
    NotionalOrderCap,
    PacAnalyzeInput,
    PacAssetInput,
    PacPlannerRequest,
    PathField,
    PlannerIssue,
    PlannerIssueCode,
    PlannerIssueParam,
    PlannerIssuePath,
    PlannerMoneyInput,
    PlannerOrderRouteInput,
    RebalanceAnalyzeInput,
    RebalanceHoldingInput,
    RebalanceQuoteInput,
    RebalancerInvestAndSellRequest,
    RebalancerInvestOnlyRequest,
    RebalancerPlannerRequest,
    TextIssueParam,
    UnsupportedCode,
    WholeQuantityCapability,
    WholeQuantityMinimum,
)
from backend.app.schemas.pac_allocator import (
    ExactNumber as WireExactNumber,
)
from backend.app.schemas.pac_allocator import (
    ExactRatio as WireExactRatio,
)
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
from backend.app.services.pac_allocator.models import (
    Checkpoint,
    ExactAsset,
    ExactAssetQuote,
    ExactAssetTax,
    ExactBroker,
    ExactContribution,
    ExactCostBasis,
    ExactCurrencySpec,
    ExactExistingCash,
    ExactExposure,
    ExactFeeSchedule,
    ExactFreshness,
    ExactFundingRoute,
    ExactFxRate,
    ExactHolding,
    ExactMoney,
    ExactOrderCap,
    ExactOrderCapability,
    ExactOrderMinimum,
    ExactOrderRoute,
    ExactPlannerScenario,
    ExactProvenance,
    ExactSellContext,
    ExactSnapshot,
    ExactTargetWeight,
    ExactWithholding,
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
    ExactRatio,
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


# Planner v2 exact normalization --------------------------------------------

type _PlannerV2Request = PacPlannerRequest | RebalancerInvestOnlyRequest | RebalancerInvestAndSellRequest
_RATIO_WIRE_INTEGER_CHARS = 192


@dataclass(frozen=True, slots=True)
class PlannerV2NormalizationResult:
    availability: PlannerAvailability
    issues: tuple[PlannerIssue, ...]
    normalized: ExactPlannerScenario | None

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


class _PlannerV2Normalizer:
    def __init__(self, request: _PlannerV2Request, source_issues: tuple[PlannerIssue, ...]) -> None:
        self.request = request
        self.issues = list(source_issues)
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

    def freshness(self, freshness, path: PlannerIssuePath) -> None:
        if not isinstance(freshness, AcceptedStaleObservation):
            return
        if freshness.age_days < 0:
            self.issue("allocation.stale_age_negative", path)
        if freshness.accepted is not True:
            self.issue("allocation.stale_observation_not_accepted", path)

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

    def validate_currency_specs(self) -> None:
        currency_ids = self.duplicates(
            self.request.currency_specs,
            lambda item: item.currency,
            lambda _item, item_id: field_path("input", "currency", item_id, "currency"),
        )
        for item in self.request.currency_specs:
            minor_unit_path = field_path("input", "currency", item.currency, "minor_unit")
            if self.ratio(item.minor_unit, minor_unit_path) <= ExactRatio(0):
                self.issue("allocation.currency_minor_unit_nonpositive", minor_unit_path)
        for currency, _path in sorted(self.currency_references.items()):
            if currency not in currency_ids:
                self.issue("allocation.currency_spec_missing", field_path("input", "currency", currency, "minor_unit"))

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
            self.issue("allocation.price_date_missing", field_path("assets", "asset", item.asset_id, "quote.reference_date"))
            return
        price_path = field_path("assets", "asset", item.asset_id, "quote.amount")
        basis_path = field_path("assets", "asset", item.asset_id, "quote.quote_base_quantity")
        self.currency(item.quote.currency, price_path)
        self.provenance(item.quote.provenance_id, field_path("assets", "asset", item.asset_id, "quote.provenance_id"))
        self.freshness(item.quote.freshness, field_path("assets", "asset", item.asset_id, "quote.freshness"))
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
        for exposure in item.exposures:
            exposure_path = field_path("assets", "asset", item.asset_id, "exposures.weight")
            self.provenance(exposure.provenance_id, field_path("assets", "asset", item.asset_id, "exposures.provenance_id"))
            weight = self.ratio(exposure.weight, exposure_path)
            if not self._ratio_in_unit_interval(weight):
                self.issue("allocation.exposure_weight_out_of_range", exposure_path)

    def validate_targets(self) -> None:
        target_ids = self.duplicates(
            self.request.target_weights,
            lambda item: item.asset_id,
            lambda _item, item_id: field_path("targets", "asset", item_id, "asset_id"),
        )
        valid_values: list[ExactRatio] = []
        references_valid = True
        values_valid = True
        for item in self.request.target_weights:
            path = field_path("targets", "asset", item.asset_id, "weight")
            if item.asset_id not in self.asset_ids:
                references_valid = False
                self.issue("allocation.reference_not_found", field_path("targets", "asset", item.asset_id, "asset_id"))
            weight = self.ratio(item.weight, path)
            valid_values.append(weight)
            if not self._ratio_in_unit_interval(weight):
                values_valid = False
                self.issue("allocation.target_weight_out_of_range", path)
        missing_targets = sorted(self.asset_ids - target_ids)
        for asset_id in missing_targets:
            self.issue("allocation.target_weight_missing", field_path("targets", "asset", asset_id, "weight"))
        if not missing_targets and references_valid and values_valid and len(target_ids) == len(self.request.target_weights):
            total = sum(valid_values, ExactRatio(0))
            if len(str(abs(total.numerator))) > _RATIO_WIRE_INTEGER_CHARS or len(str(total.denominator)) > _RATIO_WIRE_INTEGER_CHARS:
                self.issue("allocation.coefficient_envelope_unsupported", section_path("targets"))
            if total != ExactRatio(1):
                self.issue("allocation.target_total_not_one", section_path("targets"))

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
        executable_broker_ids = {item.broker_id for item in self.request.funding_routes}
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

    def validate_fee_schedule(self, broker, fee, capability_ids: set[str]) -> None:
        fee_path = field_path("brokers", "broker", broker.broker_id, "fee_schedules")
        if fee.capability_id not in capability_ids:
            self.issue("allocation.reference_not_found", field_path("brokers", "broker", broker.broker_id, "fee_schedules.capability_id"))
        fixed_fee = self.money(fee.fixed_fee, fee_path)
        variable_floor = self.money(fee.variable_floor, fee_path)
        rate = self.ratio(fee.rate, fee_path)
        cap = self.money(fee.variable_cap.amount, fee_path) if isinstance(fee.variable_cap, AmountFeeCap) else None
        money_values = (fixed_fee, variable_floor) if cap is None else (fixed_fee, variable_floor, cap)
        if any(value < ExactRatio(0) for value in money_values):
            self.issue("allocation.negative_fee_amount", fee_path)
        if not self._ratio_in_unit_interval(rate):
            self.issue("allocation.fee_rate_out_of_range", fee_path)
        if cap is not None and variable_floor > cap:
            self.issue("allocation.fee_floor_exceeds_cap", fee_path)
        currencies = {fee.fixed_fee.currency, fee.variable_floor.currency}
        if isinstance(fee.variable_cap, AmountFeeCap):
            currencies.add(fee.variable_cap.amount.currency)
        if len(currencies) != 1:
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
        if available < ExactRatio(0) or selected < ExactRatio(0):
            self.issue("allocation.negative_cash_unsupported", field_path("cash", "cash", item.cash_id, "available"))
        elif selected > available:
            self.issue("allocation.cash_selection_invalid", field_path("cash", "cash", item.cash_id, "selected"))

    def validate_contribution(self, item) -> None:
        self.provenance(item.provenance_id, field_path("contributions", "contribution", item.contribution_id, "provenance_id"))
        amount = self.money(item.amount, field_path("contributions", "contribution", item.contribution_id, "amount"))
        if amount < ExactRatio(0):
            self.issue("allocation.negative_contribution", field_path("contributions", "contribution", item.contribution_id, "amount"))

    def validate_selected_funding(self) -> None:
        funding_values = [self.ratio(item.selected.amount, field_path("cash", "cash", item.cash_id, "selected")) for item in self.request.existing_cash]
        funding_values.extend(self.ratio(item.amount.amount, field_path("contributions", "contribution", item.contribution_id, "amount")) for item in self.request.contributions)
        if not funding_values and not isinstance(self.request, RebalancerInvestAndSellRequest):
            self.issue("allocation.no_selected_funding", section_path("funding"))

    def validate_funding_routes(self, cash_by_id: dict[str, object], contribution_by_id: dict[str, object]) -> None:
        self.duplicates(
            self.request.funding_routes,
            lambda item: item.funding_route_id,
            lambda _item, item_id: field_path("funding", "funding_route", item_id, "funding_route_id"),
        )
        for item in self.request.funding_routes:
            route_path = field_path("funding", "funding_route", item.funding_route_id, "transfer_cap")
            self.reference(item.broker_id, self.broker_ids, field_path("funding", "funding_route", item.funding_route_id, "broker_id"))
            self.provenance(item.provenance_id, field_path("funding", "funding_route", item.funding_route_id, "provenance_id"))
            self.currency(item.currency, route_path)
            transfer_cap = self.money(item.transfer_cap, route_path)
            if transfer_cap < ExactRatio(0):
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

    def order_cap(self, route: PlannerOrderRouteInput) -> tuple[ExactRatio, str, str | None]:
        path = field_path("routing", "order_route", route.route_id, "cap")
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
        fee_schedule = self.fee_by_broker.get(route.broker_id, {}).get(route.fee_schedule_id)
        if fee_schedule is None:
            code = "portfolio_rebalancer.sell_fee_missing" if route.side == "sell" else "allocation.fee_schedule_missing"
            self.issue(code, field_path("routing", "order_route", route.route_id, "fee_schedule_id"))
        elif fee_schedule.side != route.side or fee_schedule.capability_id != route.capability_id:
            self.issue("allocation.reference_not_found", field_path("routing", "order_route", route.route_id, "fee_schedule_id"))
        elif quote_currency is not None and fee_schedule.fixed_fee.currency != quote_currency:
            self.issue("allocation.currency_mismatch", field_path("routing", "order_route", route.route_id, "fee_schedule_id"))
        return capability, quote_currency

    def validate_order_route_limits(self, route: PlannerOrderRouteInput, capability, quote_currency: str | None) -> None:
        minimum_if_active, minimum_if_active_kind, minimum_if_active_currency = self.order_minimum(route.minimum_if_active, route, "minimum_if_active")
        required_minimum, required_minimum_kind, required_minimum_currency = self.order_minimum(route.required_minimum, route, "required_minimum")
        cap, cap_kind, cap_currency = self.order_cap(route)
        if minimum_if_active < ExactRatio(0):
            self.issue("allocation.order_minimum_negative", field_path("routing", "order_route", route.route_id, "minimum_if_active"))
        if required_minimum < ExactRatio(0):
            self.issue("allocation.order_minimum_negative", field_path("routing", "order_route", route.route_id, "required_minimum"))
        if cap <= ExactRatio(0):
            self.issue("allocation.order_cap_nonpositive", field_path("routing", "order_route", route.route_id, "cap"))
        expected_kind = "quantity" if isinstance(capability, WholeQuantityCapability) else "notional" if isinstance(capability, MonetaryAmountCapability) else None
        self.validate_order_minimum_kind(route, capability, expected_kind, minimum_if_active_kind, minimum_if_active_currency, quote_currency, "minimum_if_active")
        self.validate_order_minimum_kind(route, capability, expected_kind, required_minimum_kind, required_minimum_currency, quote_currency, "required_minimum")
        if expected_kind is not None and cap_kind != expected_kind:
            self.issue("allocation.reference_not_found", field_path("routing", "order_route", route.route_id, "cap"))
        if cap_currency is not None and isinstance(capability, MonetaryAmountCapability) and quote_currency is not None and cap_currency != quote_currency:
            self.issue("allocation.currency_mismatch", field_path("routing", "order_route", route.route_id, "cap"))
        if minimum_if_active_kind in {"none", cap_kind} and minimum_if_active > cap:
            self.issue("allocation.order_minimum_exceeds_cap", field_path("routing", "order_route", route.route_id, "minimum_if_active"))
        if required_minimum_kind in {"none", cap_kind} and required_minimum > cap:
            self.issue("allocation.order_minimum_exceeds_cap", field_path("routing", "order_route", route.route_id, "required_minimum"))

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
        return rate if source < destination else ExactRatio(1) / rate

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
        for item in self.request.funding_routes:
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

    def validate_sell_context(self) -> None:
        if not isinstance(self.request, RebalancerInvestAndSellRequest):
            return
        context = self.request.sell_context
        cost_by_holding = self.validate_cost_basis_rows(context)
        tax_by_asset = self.validate_asset_tax_rows(context)
        withholding_by_broker = self.validate_withholding_rows(context)
        self.validate_sell_route_requirements(cost_by_holding, tax_by_asset, withholding_by_broker)

    def validate_cost_basis_rows(self, context) -> dict[str, object]:
        self.duplicates(
            context.cost_bases,
            lambda item: item.holding_id,
            lambda _item, item_id: field_path("policy", "holding", item_id, "holding_id"),
        )
        cost_by_holding = {item.holding_id: item for item in context.cost_bases}
        for item in context.cost_bases:
            path = field_path("policy", "holding", item.holding_id, "average_unit_cost")
            self.reference(item.holding_id, self.holding_ids, field_path("policy", "holding", item.holding_id, "holding_id"))
            self.provenance(item.provenance_id, field_path("policy", "holding", item.holding_id, "provenance_id"))
            if self.money(item.average_unit_cost, path) < ExactRatio(0):
                self.issue("portfolio_rebalancer.cost_basis_negative", path)
        return cost_by_holding

    def validate_asset_tax_rows(self, context) -> dict[str, object]:
        self.duplicates(
            context.asset_taxes,
            lambda item: item.asset_id,
            lambda _item, item_id: field_path("policy", "asset", item_id, "asset_id"),
        )
        tax_by_asset = {item.asset_id: item for item in context.asset_taxes}
        for item in context.asset_taxes:
            self.reference(item.asset_id, self.asset_ids, field_path("policy", "asset", item.asset_id, "asset_id"))
            self.provenance(item.provenance_id, field_path("policy", "asset", item.asset_id, "provenance_id"))
            tax_path = field_path("policy", "asset", item.asset_id, "tax_rate")
            tax_rate = self.ratio(item.tax_rate, tax_path)
            if not self._ratio_in_unit_interval(tax_rate):
                self.issue("portfolio_rebalancer.tax_rate_out_of_range", tax_path)
            if item.fiscal_currency is None:
                self.issue("allocation.fiscal_currency_missing", field_path("policy", "asset", item.asset_id, "fiscal_currency"))
            else:
                self.currency(item.fiscal_currency, field_path("policy", "asset", item.asset_id, "fiscal_currency"))
        return tax_by_asset

    def validate_withholding_rows(self, context) -> dict[str, object]:
        self.duplicates(
            context.broker_withholding,
            lambda item: item.broker_id,
            lambda _item, item_id: field_path("policy", "broker", item_id, "broker_id"),
        )
        withholding_by_broker = {item.broker_id: item for item in context.broker_withholding}
        for item in context.broker_withholding:
            path = field_path("policy", "broker", item.broker_id, "carried_loss")
            self.reference(item.broker_id, self.broker_ids, field_path("policy", "broker", item.broker_id, "broker_id"))
            self.provenance(item.provenance_id, field_path("policy", "broker", item.broker_id, "provenance_id"))
            if self.money(item.carried_loss, path) < ExactRatio(0):
                self.issue("portfolio_rebalancer.carried_loss_negative", path)
        return withholding_by_broker

    def validate_sell_route_requirements(self, cost_by_holding: dict[str, object], tax_by_asset: dict[str, object], withholding_by_broker: dict[str, object]) -> None:
        if not isinstance(self.request, RebalancerInvestAndSellRequest):
            raise RuntimeError("SELL requirements require invest_and_sell")
        holding_groups: dict[tuple[str, str], list[object]] = defaultdict(list)
        for holding in self.request.holdings:
            holding_groups[(holding.asset_id, holding.broker_id)].append(holding)
        holdings_by_pair = {key: values[0] for key, values in holding_groups.items() if len(values) == 1}
        ambiguous_holding_pairs = {key for key, values in holding_groups.items() if len(values) > 1}
        fiscal_by_broker: dict[str, set[str]] = defaultdict(set)
        for route in self.request.order_routes:
            if route.side != "sell":
                continue
            self.validate_sell_route_requirement(route, holdings_by_pair, ambiguous_holding_pairs, cost_by_holding, tax_by_asset, withholding_by_broker, fiscal_by_broker)
        for broker_id, fiscal_currencies in sorted(fiscal_by_broker.items()):
            if len(fiscal_currencies) > 1:
                self.issue("allocation.tax_netting_unsupported", field_path("policy", "broker", broker_id, "fiscal_currency"))
                continue
            withholding = withholding_by_broker.get(broker_id)
            if withholding is not None and fiscal_currencies and withholding.carried_loss.currency not in fiscal_currencies:
                self.issue("allocation.currency_mismatch", field_path("policy", "broker", broker_id, "carried_loss.currency"))

    def validate_sell_route_requirement(
        self,
        route,
        holdings_by_pair: dict[tuple[str, str], object],
        ambiguous_holding_pairs: set[tuple[str, str]],
        cost_by_holding: dict[str, object],
        tax_by_asset: dict[str, object],
        withholding_by_broker: dict[str, object],
        fiscal_by_broker: dict[str, set[str]],
    ) -> None:
        tax = tax_by_asset.get(route.asset_id)
        if tax is None:
            self.issue("portfolio_rebalancer.tax_rate_missing", field_path("policy", "asset", route.asset_id, "tax_rate"))
        elif tax.fiscal_currency is not None:
            fiscal_by_broker[route.broker_id].add(tax.fiscal_currency)
            asset = self.asset_by_id.get(route.asset_id)
            quote_currency = asset.quote.currency if asset is not None and asset.quote is not None else None
            # SELL always settles tax/withholding in the asset's own quote currency
            # (no conversion at SELL time); the evaluator hard-asserts this, so it
            # must be a typed issue here rather than a boundary crash.
            if quote_currency is not None and tax.fiscal_currency != quote_currency:
                self.issue("allocation.currency_mismatch", field_path("policy", "asset", route.asset_id, "fiscal_currency"))
        if route.broker_id not in withholding_by_broker:
            self.issue("portfolio_rebalancer.withholding_missing", field_path("policy", "broker", route.broker_id, "withholding"))
        holding_pair = (route.asset_id, route.broker_id)
        if holding_pair in ambiguous_holding_pairs:
            return
        holding = holdings_by_pair.get(holding_pair)
        if holding is None:
            self.issue("allocation.wac_missing", field_path("policy", "order_route", route.route_id, "cost_basis"))
            return
        cost_basis = cost_by_holding.get(holding.holding_id)
        if cost_basis is None:
            self.issue("allocation.wac_missing", field_path("policy", "holding", holding.holding_id, "average_unit_cost"))
        elif tax is not None and tax.fiscal_currency is not None:
            self.require_fx_pair(cost_basis.average_unit_cost.currency, tax.fiscal_currency)

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

    def build_freshness(self, freshness) -> ExactFreshness:
        if isinstance(freshness, AcceptedStaleObservation):
            return ExactFreshness(kind="stale", age_days=freshness.age_days, accepted=freshness.accepted)
        return ExactFreshness(kind="fresh", age_days=None, accepted=False)

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
                        reference_date=date.fromisoformat(item.quote.reference_date),
                        freshness=self.build_freshness(item.quote.freshness),
                        provenance_id=item.quote.provenance_id,
                    ),
                    exposures=exposures,
                )
            )
        return tuple(result)

    def build_brokers(self) -> tuple[ExactBroker, ...]:
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
            fees = []
            for fee in sorted(broker.fee_schedules, key=lambda value: (value.capability_id, value.side, value.fee_schedule_id)):
                maximum_fee = self.build_money(fee.variable_cap.amount) if isinstance(fee.variable_cap, AmountFeeCap) else None
                fees.append(
                    ExactFeeSchedule(
                        fee_schedule_id=fee.fee_schedule_id,
                        capability_id=fee.capability_id,
                        side=fee.side,
                        fixed_fee=self.build_money(fee.fixed_fee),
                        proportional_rate=ExactRatio.from_decimal(Decimal(fee.rate)),
                        minimum_fee=self.build_money(fee.variable_floor),
                        maximum_fee=maximum_fee,
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
                    fee_schedules=tuple(fees),
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

    def build_order_cap(self, cap) -> ExactOrderCap:
        if isinstance(cap, NotionalOrderCap):
            return ExactOrderCap(kind="notional", value=ExactRatio.from_decimal(Decimal(cap.amount.amount)), currency=cap.amount.currency)
        return ExactOrderCap(kind="quantity", value=ExactRatio.from_decimal(Decimal(cap.quantity)), currency=None)

    def build_sell_context(self) -> ExactSellContext | None:
        if not isinstance(self.request, RebalancerInvestAndSellRequest):
            return None
        return ExactSellContext(
            cost_basis=tuple(
                ExactCostBasis(
                    holding_id=item.holding_id,
                    average_unit_cost=self.build_money(item.average_unit_cost),
                    reference_date=date.fromisoformat(item.reference_date),
                    provenance_id=item.provenance_id,
                )
                for item in sorted(self.request.sell_context.cost_bases, key=lambda value: value.holding_id)
            ),
            asset_tax=tuple(
                ExactAssetTax(
                    asset_id=item.asset_id,
                    fiscal_currency=item.fiscal_currency or "",
                    gain_tax_rate=ExactRatio.from_decimal(Decimal(item.tax_rate)),
                    provenance_id=item.provenance_id,
                )
                for item in sorted(self.request.sell_context.asset_taxes, key=lambda value: value.asset_id)
            ),
            withholding=tuple(
                ExactWithholding(
                    broker_id=item.broker_id,
                    fiscal_currency=item.carried_loss.currency,
                    carried_loss_available=self.build_money(item.carried_loss),
                    withholding_kind=item.withholding_kind,
                    reference_date=date.fromisoformat(item.reference_date),
                    provenance_id=item.provenance_id,
                )
                for item in sorted(self.request.sell_context.broker_withholding, key=lambda value: value.broker_id)
            ),
        )

    def build_scenario(self) -> ExactPlannerScenario:
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
                source_kind=item.source_kind,
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
                transfer_cap=self.build_money(item.transfer_cap),
                priority=item.priority,
                provenance_id=item.provenance_id,
            )
            for item in sorted(self.request.funding_routes, key=lambda value: value.funding_route_id)
        )
        order_routes = tuple(
            ExactOrderRoute(
                route_id=item.route_id,
                broker_id=item.broker_id,
                asset_id=item.asset_id,
                capability_id=item.capability_id,
                fee_schedule_id=item.fee_schedule_id,
                side=item.side,
                minimum_if_active=self.build_order_minimum(item.minimum_if_active),
                required_minimum=self.build_order_minimum(item.required_minimum),
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
            currency_specs=tuple(ExactCurrencySpec(currency=item.currency, minor_unit=ExactRatio.from_decimal(Decimal(item.minor_unit))) for item in sorted(self.request.currency_specs, key=lambda value: value.currency)),
            provenance=self.build_provenance(),
            fx_rates=fx_rates,
            fx_spread_rate=ExactRatio.from_decimal(Decimal(self.request.fx_spread_rate)),
            assets=self.build_assets(),
            brokers=self.build_brokers(),
            holdings=self.build_holdings(),
            existing_cash=existing_cash,
            contributions=contributions,
            funding_routes=funding_routes,
            order_routes=order_routes,
            target_weights=tuple(ExactTargetWeight(asset_id=item.asset_id, weight=ExactRatio.from_decimal(Decimal(item.weight))) for item in sorted(self.request.target_weights, key=lambda value: value.asset_id)),
            sell_context=self.build_sell_context(),
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
        self.validate_sell_context()
        self.validate_current_portfolio()
        self.validate_currency_specs()
        self.validate_fx_pair_closure()
        issues = canonicalize_issues(self.issues)
        availability = normalization_availability(issues)
        normalized = self.build_scenario() if availability == "ready" else None
        return PlannerV2NormalizationResult(availability=availability, issues=issues, normalized=normalized)


def normalize_planner_request(request: _PlannerV2Request, *, source_issues: tuple[PlannerIssue, ...] = ()) -> PlannerV2NormalizationResult:
    """Normalize one frozen Planner v2 request into immutable exact facts."""
    if not isinstance(request, (PacPlannerRequest, RebalancerInvestOnlyRequest, RebalancerInvestAndSellRequest)):
        raise TypeError(f"Unsupported Planner v2 request: {type(request).__name__}")
    return _PlannerV2Normalizer(request, source_issues).run()


def normalize_pac_plan(request: PacPlannerRequest, *, source_issues: tuple[PlannerIssue, ...] = ()) -> PlannerV2NormalizationResult:
    """Normalize one frozen PAC v2 request without changing P1 behavior."""
    if not isinstance(request, PacPlannerRequest):
        raise TypeError(f"Expected PacPlannerRequest, got {type(request).__name__}")
    return normalize_planner_request(request, source_issues=source_issues)


def normalize_rebalancer_plan(request: RebalancerPlannerRequest, *, source_issues: tuple[PlannerIssue, ...] = ()) -> PlannerV2NormalizationResult:
    """Normalize one frozen Rebalancer v2 request without changing P1 behavior."""
    if not isinstance(request, (RebalancerInvestOnlyRequest, RebalancerInvestAndSellRequest)):
        raise TypeError(f"Expected Rebalancer Planner request, got {type(request).__name__}")
    return normalize_planner_request(request, source_issues=source_issues)
