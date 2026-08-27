"""Pydantic payload models for the FX non-technical/core AI Export components.

Covers exactly the five FX "core" components owned by this workstream:
`fx.pair_identity`, `fx.current_rate`, `fx.conversion_provenance`,
`fx.exposure_base_quote`, `fx.exposure_provenance` (see
`backend.app.services.ai_export.components.fx_core` for the matching
`ComponentSpec`/builder wiring). The FX *technical* components (`fx.rate_ohlc`,
`fx.returns_volatility`, `fx.indicators`, `fx.states_events`) belong to a sibling
workstream and are out of scope here.

Every model is deliberately `extra="forbid"` and Decimal/date-safe so it survives
`backend.app.services.ai_export.components.envelope.build_envelope`'s
`model_dump(mode="json")` round trip without leaking an untyped `Any`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.services.ai_export.components.types import normalize_currency_code


class FxRateDirection(StrEnum):
    """Direction of a resolved FX conversion relative to how the rate is stored.

    `FxRate` rows are always stored with `base < quote` alphabetically (see
    `backend.app.db.models.FxRate`): DIRECT means the requested (from, to)
    pair matches that storage order as-is, INVERSE means the stored row is
    the reverse of the requested pair (so the service divides instead of
    multiplying). There is deliberately no TRIANGULATED member: no backend
    service currently resolves a pair through a third currency at read time
    (`backend.app.services.fx.convert_bulk` only ever looks up a direct or
    inverse stored row and raises `RateNotFoundError` otherwise), so this
    runtime never fabricates that route.
    """

    DIRECT = "direct"
    INVERSE = "inverse"


def _validate_currency(value: str) -> str:
    return normalize_currency_code(value)


def _validate_finite_positive_decimal(value: Decimal, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal")
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{field_name} must be a finite, positive Decimal")
    return value


def _validate_finite_decimal(value: Decimal, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be a finite Decimal")
    return value


class FxPairIdentityPayload(BaseModel):
    """`fx.pair_identity`: explicit quote-per-base pair identity.

    `rate_semantics` documents the fixed convention (1 unit of `base_currency`
    is worth `rate` units of `quote_currency`); `stored_base_currency`/
    `stored_quote_currency` expose the alphabetical storage order backing
    `direction`, so callers never have to re-derive it themselves.
    """

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    rate_semantics: str = Field(default="quote_currency_per_base_currency", frozen=True)
    stored_base_currency: str
    stored_quote_currency: str
    direction: FxRateDirection

    @field_validator("base_currency", "quote_currency", "stored_base_currency", "stored_quote_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        if {self.stored_base_currency, self.stored_quote_currency} != {self.base_currency, self.quote_currency}:
            raise ValueError("stored_base_currency/stored_quote_currency must be the same pair as base_currency/quote_currency")
        if self.stored_base_currency >= self.stored_quote_currency:
            raise ValueError("stored_base_currency must be alphabetically before stored_quote_currency")
        expected_direction = FxRateDirection.DIRECT if self.base_currency == self.stored_base_currency else FxRateDirection.INVERSE
        if self.direction != expected_direction:
            raise ValueError("direction is inconsistent with stored_base_currency/stored_quote_currency ordering")
        return self


class FxCurrentRatePayload(BaseModel):
    """`fx.current_rate`: quote-per-base rate as of the snapshot instant.

    `requested_date` is always `BuildScope.snapshot_as_of`; `effective_date` is
    the actual stored rate date backing it (backward-filled when no exact
    match exists), never after `requested_date`.
    """

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    direction: FxRateDirection
    requested_date: date
    effective_date: date
    rate: Decimal = Field(..., description="Quote units per 1 base unit")
    is_backward_filled: bool
    staleness_days: int = Field(ge=0)

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @field_validator("rate")
    @classmethod
    def _validate_rate(cls, value: Decimal) -> Decimal:
        return _validate_finite_positive_decimal(value, field_name="rate")

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        if self.effective_date > self.requested_date:
            raise ValueError("effective_date must not be after requested_date")
        expected_staleness = (self.requested_date - self.effective_date).days
        if self.staleness_days != expected_staleness:
            raise ValueError("staleness_days must equal (requested_date - effective_date).days")
        if self.is_backward_filled != (self.staleness_days > 0):
            raise ValueError("is_backward_filled must match staleness_days > 0")
        return self


class FxConversionProvenancePayload(BaseModel):
    """`fx.conversion_provenance`: methodology/provenance for the base/quote pair itself.

    Distinct from `fx.exposure_provenance` (which documents exposure currency
    conversions towards `target_currency`, possibly a third currency): this
    component only ever describes the `base_currency`/`quote_currency` pair.
    """

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    direction: FxRateDirection
    requested_date: date
    effective_date: date
    is_backward_filled: bool
    source: str = Field(min_length=1, description="Authoritative FxRate.source for the resolved row (e.g. 'ECB', 'MANUAL')")

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        if self.effective_date > self.requested_date:
            raise ValueError("effective_date must not be after requested_date")
        expected_backward_filled = self.effective_date != self.requested_date
        if self.is_backward_filled != expected_backward_filled:
            raise ValueError("is_backward_filled must match effective_date != requested_date")
        return self


class FxExposureKind(StrEnum):
    """Whether an exposure row originates from cash or from a valued position."""

    CASH = "cash"
    POSITION = "position"


class FxExposureLinkage(StrEnum):
    """Why a row's currency directly matches base/quote (no look-through inference)."""

    CASH_CURRENCY = "cash_currency"
    TRADING_CURRENCY = "trading_currency"
    VALUATION_CURRENCY = "valuation_currency"


class FxExposureConversionBasis(StrEnum):
    """How a row's `target_amount` relates to its (possibly absent) `native_amount`.

    - IDENTITY: `linked_currency == target_currency`; no conversion applies,
      `native_amount == target_amount` by construction.
    - RESOLVED_RATE: a real FX rate resolved independently via
      `backend.app.services.fx.convert_bulk` reconciles (within an explicit
      tolerance) with the implied rate `target_amount / native_amount`; that
      resolved rate's `direction` is carried as provenance.
    - ENGINE_VALUATION: `target_amount` comes directly from the portfolio
      valuation engine (`PortfolioHolding.current_value`, already expressed in
      `target_currency`) and no honest `native_amount` could be derived (or an
      independently resolved rate did not reconcile with one that could) - no
      rate/direction is fabricated; `FxExposureRow.valuation_source` documents
      the engine's own valuation basis instead.
    """

    IDENTITY = "identity"
    RESOLVED_RATE = "resolved_rate"
    ENGINE_VALUATION = "engine_valuation"


class FxExposureConversion(BaseModel):
    """Per-row conversion facts from `linked_currency` towards `target_currency`.

    `direction` is only ever set for `basis=RESOLVED_RATE` (a genuine resolved
    FX rate applies); `IDENTITY` and `ENGINE_VALUATION` both carry
    `direction=None` - the former because no conversion is needed, the latter
    because none is honestly known.
    """

    model_config = ConfigDict(extra="forbid")

    basis: FxExposureConversionBasis
    direction: FxRateDirection | None = None
    requested_date: date
    effective_date: date
    is_backward_filled: bool

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.effective_date > self.requested_date:
            raise ValueError("effective_date must not be after requested_date")
        if self.basis is FxExposureConversionBasis.RESOLVED_RATE:
            if self.direction is None:
                raise ValueError("RESOLVED_RATE conversions require a resolved direction")
        elif self.direction is not None:
            raise ValueError(f"{self.basis.value} conversions must not carry a direction")
        if self.direction is None:
            if self.is_backward_filled:
                raise ValueError("identity/engine-valuation conversions (direction=None) cannot be backward-filled")
            if self.effective_date != self.requested_date:
                raise ValueError("identity/engine-valuation conversions (direction=None) must have effective_date == requested_date")
        return self


class FxExposureRow(BaseModel):
    """One preserved exposure row: exactly one cash balance or one valued position.

    Every row produced by the builder is kept (no top-N truncation); ordering
    is imposed by the builder, not by this model.

    `native_amount` is `None` exactly when `conversion.basis is
    FxExposureConversionBasis.ENGINE_VALUATION`: no honest native-currency
    amount could be derived for that position (see `FxExposureConversionBasis`
    docstring); `target_amount` is always known (cash: converted from a real
    native balance; position: `PortfolioHolding.current_value`, already
    expressed in `target_currency` by the portfolio valuation engine - never
    re-derived from `native_amount`). `valuation_source` mirrors
    `PortfolioHolding.valuation_source` for POSITION rows only (`None` for
    CASH), so callers still get an honest basis for the value even when no
    native amount/rate is available.
    """

    model_config = ConfigDict(extra="forbid")

    kind: FxExposureKind
    linkage: FxExposureLinkage
    linked_currency: str
    native_amount: Decimal | None = None
    target_amount: Decimal
    conversion: FxExposureConversion
    valuation_source: str | None = None
    asset_id: int | None = None
    broker_id: int | None = None

    @field_validator("linked_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @field_validator("target_amount")
    @classmethod
    def _validate_target_amount(cls, value: Decimal) -> Decimal:
        return _validate_finite_decimal(value, field_name="target_amount")

    @field_validator("native_amount")
    @classmethod
    def _validate_native_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return _validate_finite_decimal(value, field_name="native_amount")

    @field_validator("asset_id", "broker_id", mode="before")
    @classmethod
    def _reject_bool_id(cls, value, info):
        # `True` *is* `1` in Python, and pydantic coerces it to `1` before any "after"
        # validator runs — so the bool check that used to live in the validator below
        # could never fire, and `asset_id=True` was quietly accepted as asset #1, a real
        # asset. This runs on the raw input, the only place where a bool is still a bool.
        if isinstance(value, bool):
            raise ValueError(f"{info.field_name} must be a positive int when present")
        return value

    @field_validator("asset_id", "broker_id")
    @classmethod
    def _validate_positive_id(cls, value: int | None, info) -> int | None:
        if value is not None and value < 1:
            raise ValueError(f"{info.field_name} must be a positive int when present")
        return value

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        is_engine_valuation = self.conversion.basis is FxExposureConversionBasis.ENGINE_VALUATION
        if is_engine_valuation and self.native_amount is not None:
            raise ValueError("ENGINE_VALUATION rows must not carry a native_amount (none is honestly derivable)")
        if not is_engine_valuation and self.native_amount is None:
            raise ValueError("only ENGINE_VALUATION rows may omit native_amount")
        if self.conversion.basis is FxExposureConversionBasis.IDENTITY and self.native_amount != self.target_amount:
            raise ValueError("identity conversions must leave native_amount == target_amount")
        if self.kind is FxExposureKind.POSITION:
            if self.asset_id is None:
                raise ValueError("position exposure rows require asset_id")
            if self.linkage is FxExposureLinkage.CASH_CURRENCY:
                raise ValueError("position exposure rows cannot use CASH_CURRENCY linkage")
            if self.valuation_source is None:
                raise ValueError("position exposure rows must carry a valuation_source")
        else:  # CASH
            if self.asset_id is not None:
                raise ValueError("cash exposure rows cannot reference asset_id")
            if self.linkage is not FxExposureLinkage.CASH_CURRENCY:
                raise ValueError("cash exposure rows must use CASH_CURRENCY linkage")
            if is_engine_valuation:
                raise ValueError("cash exposure rows cannot use ENGINE_VALUATION basis (cash is always native-then-converted)")
            if self.valuation_source is not None:
                raise ValueError("cash exposure rows cannot carry a valuation_source")
        return self


class FxExposureRole(StrEnum):
    """Which leg of the pair an exposure row's currency matches."""

    BASE = "base"
    QUOTE = "quote"


class FxExposureRoleSummary(BaseModel):
    """Deterministic per-leg (base or quote) rollup of the preserved exposure rows.

    Every count/total is derived purely from the preserved ``rows`` (no row is
    dropped to produce it). ``has_direct_exposure`` is the explicit boolean
    zero-state: ``False`` here means a genuinely *computed* absence of any direct
    exposure in that currency, never "data missing" - the exposure builder always
    resolves the real portfolio report, so an absent row is a real zero.
    ``net_target_amount`` sums the signed ``target_amount``s (a net figure that
    can be negative, e.g. a net short/negative-cash leg); ``gross_target_amount``
    sums their absolute values, so a reader can tell an offsetting net-flat leg
    from a truly empty one.
    """

    model_config = ConfigDict(extra="forbid")

    currency: str
    role: FxExposureRole
    row_count: int = Field(..., ge=0)
    cash_row_count: int = Field(..., ge=0)
    position_row_count: int = Field(..., ge=0)
    net_target_amount: Decimal
    gross_target_amount: Decimal
    has_direct_exposure: bool

    @field_validator("currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @field_validator("net_target_amount")
    @classmethod
    def _validate_net(cls, value: Decimal) -> Decimal:
        return _validate_finite_decimal(value, field_name="net_target_amount")

    @field_validator("gross_target_amount")
    @classmethod
    def _validate_gross(cls, value: Decimal) -> Decimal:
        value = _validate_finite_decimal(value, field_name="gross_target_amount")
        if value < 0:
            raise ValueError("gross_target_amount must not be negative")
        return value

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.cash_row_count + self.position_row_count != self.row_count:
            raise ValueError("row_count must equal cash_row_count + position_row_count")
        if self.has_direct_exposure != (self.row_count > 0):
            raise ValueError("has_direct_exposure must match row_count > 0")
        if self.row_count == 0:
            if self.net_target_amount != 0 or self.gross_target_amount != 0:
                raise ValueError("a zero-row leg must carry zero net/gross totals")
        elif abs(self.net_target_amount) > self.gross_target_amount:
            raise ValueError("abs(net_target_amount) must not exceed gross_target_amount")
        return self


def _role_summary(rows: Sequence[FxExposureRow], *, currency: str, role: FxExposureRole) -> FxExposureRoleSummary:
    normalized = normalize_currency_code(currency)
    matching = [row for row in rows if row.linked_currency == normalized]
    cash_count = sum(row.kind is FxExposureKind.CASH for row in matching)
    position_count = sum(row.kind is FxExposureKind.POSITION for row in matching)
    net = sum((row.target_amount for row in matching), Decimal(0))
    gross = sum((abs(row.target_amount) for row in matching), Decimal(0))
    return FxExposureRoleSummary(
        currency=normalized,
        role=role,
        row_count=len(matching),
        cash_row_count=cash_count,
        position_row_count=position_count,
        net_target_amount=net,
        gross_target_amount=gross,
        has_direct_exposure=len(matching) > 0,
    )


class FxExposureSummary(BaseModel):
    """Explicit base/quote exposure rollup + zero-state for ``fx.exposure_base_quote``.

    Fully derived from the preserved rows (see ``FxExposureBaseQuotePayload`` -
    the rows themselves are never removed to build this). ``has_direct_quote_exposure``
    / ``has_direct_base_exposure`` make the direct-exposure zero-state explicit so
    an analysis never has to infer "no exposure" from an empty row list.
    """

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    target_currency: str
    total_row_count: int = Field(..., ge=0)
    base: FxExposureRoleSummary
    quote: FxExposureRoleSummary
    has_direct_base_exposure: bool
    has_direct_quote_exposure: bool
    has_any_direct_exposure: bool

    @field_validator("base_currency", "quote_currency", "target_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        if self.base.role is not FxExposureRole.BASE or self.base.currency != self.base_currency:
            raise ValueError("base summary must describe the base_currency with role BASE")
        if self.quote.role is not FxExposureRole.QUOTE or self.quote.currency != self.quote_currency:
            raise ValueError("quote summary must describe the quote_currency with role QUOTE")
        if self.total_row_count != self.base.row_count + self.quote.row_count:
            raise ValueError("total_row_count must equal base.row_count + quote.row_count")
        if self.has_direct_base_exposure != self.base.has_direct_exposure:
            raise ValueError("has_direct_base_exposure must match base.has_direct_exposure")
        if self.has_direct_quote_exposure != self.quote.has_direct_exposure:
            raise ValueError("has_direct_quote_exposure must match quote.has_direct_exposure")
        if self.has_any_direct_exposure != (self.has_direct_base_exposure or self.has_direct_quote_exposure):
            raise ValueError("has_any_direct_exposure must match base/quote exposure booleans")
        return self

    @classmethod
    def from_rows(cls, rows: Sequence[FxExposureRow], *, base_currency: str, quote_currency: str, target_currency: str) -> FxExposureSummary:
        base = _role_summary(rows, currency=base_currency, role=FxExposureRole.BASE)
        quote = _role_summary(rows, currency=quote_currency, role=FxExposureRole.QUOTE)
        return cls(
            base_currency=base_currency,
            quote_currency=quote_currency,
            target_currency=target_currency,
            total_row_count=base.row_count + quote.row_count,
            base=base,
            quote=quote,
            has_direct_base_exposure=base.has_direct_exposure,
            has_direct_quote_exposure=quote.has_direct_exposure,
            has_any_direct_exposure=base.has_direct_exposure or quote.has_direct_exposure,
        )


class FxExposureBaseQuotePayload(BaseModel):
    """`fx.exposure_base_quote`: every direct base/quote exposure row, preserved.

    `rows` deliberately preserves every candidate row across all detail
    levels (no top-N sampling): applicability/summarization is a higher-level
    concern outside this runtime. An empty `rows` tuple is a valid, successful
    "no direct exposure" result, not an error. `summary` is an explicit,
    fully-derived base/quote rollup (totals, counts, and an explicit
    `has_direct_quote_exposure`/`has_direct_base_exposure` zero-state) computed
    from those preserved rows - it never removes or overrides any row, and is
    recomputed on validation so it can never drift from `rows`.
    """

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    target_currency: str
    as_of: date
    broker_scope: tuple[int, ...] = ()
    rows: tuple[FxExposureRow, ...] = ()
    summary: FxExposureSummary | None = None

    @field_validator("base_currency", "quote_currency", "target_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        pair = {self.base_currency, self.quote_currency}
        for row in self.rows:
            if row.linked_currency not in pair:
                raise ValueError(f"exposure row linked_currency {row.linked_currency!r} is not base_currency/quote_currency")
            # `FxExposureRow` itself already enforces native_amount == target_amount for
            # IDENTITY conversions and native_amount is None for ENGINE_VALUATION ones.
        # Always (re)derive the explicit summary from the preserved rows so the
        # zero-state/totals can never diverge from `rows`, whether this payload
        # was built fresh or re-validated from a serialized envelope.
        self.summary = FxExposureSummary.from_rows(
            self.rows,
            base_currency=self.base_currency,
            quote_currency=self.quote_currency,
            target_currency=self.target_currency,
        )
        return self


class FxExposureConversionSummary(BaseModel):
    """One deduplicated exposure-currency conversion entry (`fx.exposure_provenance`).

    `source=None` is only valid for identity conversions (`direction=None`);
    every real conversion must carry the authoritative `FxRate.source`.
    """

    model_config = ConfigDict(extra="forbid")

    linked_currency: str
    target_currency: str
    direction: FxRateDirection | None
    requested_date: date
    effective_date: date
    is_backward_filled: bool
    source: str | None = None

    @field_validator("linked_currency", "target_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.effective_date > self.requested_date:
            raise ValueError("effective_date must not be after requested_date")
        if self.direction is None:
            if self.source is not None:
                raise ValueError("identity conversions (direction=None) must not carry a source")
        elif not self.source:
            raise ValueError("non-identity conversions must carry a non-empty source")
        return self


class FxExposureProvenancePayload(BaseModel):
    """`fx.exposure_provenance`: deduplicated conversion provenance for `fx.exposure_base_quote`.

    One entry per distinct `linked_currency` that has at least one sibling
    `fx.exposure_base_quote` row whose `conversion.basis` is not
    `ENGINE_VALUATION` (i.e. at least one row in that currency actually used a
    resolved/identity conversion), never per-row (rows can repeat the same
    linked currency across many brokers/assets). A currency whose *only* rows
    fell back to `ENGINE_VALUATION` (no honest native amount was derivable, so
    no rate was ever applied/reconciled - see `FxExposureRow.valuation_source`
    on those rows instead) is deliberately omitted here: this component never
    claims a conversion as provenance for a row that did not actually use it.
    """

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    target_currency: str
    conversions: tuple[FxExposureConversionSummary, ...] = ()

    @field_validator("base_currency", "quote_currency", "target_currency")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _validate_currency(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.base_currency == self.quote_currency:
            raise ValueError("base_currency and quote_currency must differ")
        currencies = [entry.linked_currency for entry in self.conversions]
        if len(currencies) != len(set(currencies)):
            raise ValueError("conversions must have unique linked_currency entries")
        return self


__all__ = [
    "FxConversionProvenancePayload",
    "FxCurrentRatePayload",
    "FxExposureBaseQuotePayload",
    "FxExposureConversion",
    "FxExposureConversionSummary",
    "FxExposureKind",
    "FxExposureLinkage",
    "FxExposureProvenancePayload",
    "FxExposureRole",
    "FxExposureRoleSummary",
    "FxExposureRow",
    "FxExposureSummary",
    "FxPairIdentityPayload",
    "FxRateDirection",
]
