"""Fail-closed contract tests for the `fx.*` core AI Export payload models.

`test_ai_export_components_fx.py` builds these payloads through the real
components against the test database, which proves the *happy* shapes. This file
covers the other half - every `model_validator(mode="after")` rejection arm in
`components/fx_payloads.py` - without a database, a server or a network call.

Why these arms deserve non-regression tests rather than being written off as
defensive noise: each payload here is copied verbatim into a prompt an LLM will
reason about. A payload whose `staleness_days` disagrees with its own dates, or
whose `has_direct_exposure` disagrees with its own row count, is not a crash - it
is a *plausible lie*. These validators are the only thing standing between an
inconsistent builder and an exported inconsistency, so every test below names the
concrete builder mistake it protects against.

Isolation: PURE (models only, no DB/server/network).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.services.ai_export.components.fx_payloads import (
    FxConversionProvenancePayload,
    FxCurrentRatePayload,
    FxExposureBaseQuotePayload,
    FxExposureConversion,
    FxExposureConversionBasis,
    FxExposureConversionSummary,
    FxExposureKind,
    FxExposureLinkage,
    FxExposureProvenancePayload,
    FxExposureRole,
    FxExposureRoleSummary,
    FxExposureRow,
    FxExposureSummary,
    FxPairIdentityPayload,
    FxRateDirection,
)

AS_OF = date(2026, 4, 10)
EARLIER = date(2026, 4, 8)
LATER = date(2026, 4, 12)


# ---------------------------------------------------------------------------
# Builders: each returns a *valid* payload with every field overridable, so a
# test changes exactly one thing and the failure names exactly one invariant.
# ---------------------------------------------------------------------------


def _identity(**overrides) -> FxPairIdentityPayload:
    # EUR/USD: alphabetical storage order is EUR<USD, so EUR->USD is DIRECT.
    kwargs = {
        "base_currency": "EUR",
        "quote_currency": "USD",
        "stored_base_currency": "EUR",
        "stored_quote_currency": "USD",
        "direction": FxRateDirection.DIRECT,
    }
    kwargs.update(overrides)
    return FxPairIdentityPayload(**kwargs)


def _current_rate(**overrides) -> FxCurrentRatePayload:
    kwargs = {
        "base_currency": "EUR",
        "quote_currency": "USD",
        "direction": FxRateDirection.DIRECT,
        "requested_date": AS_OF,
        "effective_date": AS_OF,
        "rate": Decimal("1.0850"),
        "is_backward_filled": False,
        "staleness_days": 0,
    }
    kwargs.update(overrides)
    return FxCurrentRatePayload(**kwargs)


def _provenance(**overrides) -> FxConversionProvenancePayload:
    kwargs = {
        "base_currency": "EUR",
        "quote_currency": "USD",
        "direction": FxRateDirection.DIRECT,
        "requested_date": AS_OF,
        "effective_date": AS_OF,
        "is_backward_filled": False,
        "source": "ECB",
    }
    kwargs.update(overrides)
    return FxConversionProvenancePayload(**kwargs)


def _conversion(**overrides) -> FxExposureConversion:
    kwargs = {
        "basis": FxExposureConversionBasis.IDENTITY,
        "direction": None,
        "requested_date": AS_OF,
        "effective_date": AS_OF,
        "is_backward_filled": False,
    }
    kwargs.update(overrides)
    return FxExposureConversion(**kwargs)


def _cash_row(**overrides) -> FxExposureRow:
    kwargs = {
        "kind": FxExposureKind.CASH,
        "linkage": FxExposureLinkage.CASH_CURRENCY,
        "linked_currency": "EUR",
        "native_amount": Decimal("100"),
        "target_amount": Decimal("100"),
        "conversion": _conversion(),
    }
    kwargs.update(overrides)
    return FxExposureRow(**kwargs)


def _position_row(**overrides) -> FxExposureRow:
    kwargs = {
        "kind": FxExposureKind.POSITION,
        "linkage": FxExposureLinkage.TRADING_CURRENCY,
        "linked_currency": "USD",
        "native_amount": None,
        "target_amount": Decimal("250"),
        "conversion": _conversion(basis=FxExposureConversionBasis.ENGINE_VALUATION),
        "valuation_source": "portfolio_engine",
        "asset_id": 7,
    }
    kwargs.update(overrides)
    return FxExposureRow(**kwargs)


def _role_summary(**overrides) -> FxExposureRoleSummary:
    kwargs = {
        "currency": "EUR",
        "role": FxExposureRole.BASE,
        "row_count": 1,
        "cash_row_count": 1,
        "position_row_count": 0,
        "net_target_amount": Decimal("100"),
        "gross_target_amount": Decimal("100"),
        "has_direct_exposure": True,
    }
    kwargs.update(overrides)
    return FxExposureRoleSummary(**kwargs)


def _empty_role_summary(currency: str, role: FxExposureRole) -> FxExposureRoleSummary:
    return FxExposureRoleSummary(
        currency=currency,
        role=role,
        row_count=0,
        cash_row_count=0,
        position_row_count=0,
        net_target_amount=Decimal("0"),
        gross_target_amount=Decimal("0"),
        has_direct_exposure=False,
    )


def _exposure_summary(**overrides) -> FxExposureSummary:
    kwargs = {
        "base_currency": "EUR",
        "quote_currency": "USD",
        "target_currency": "EUR",
        "total_row_count": 0,
        "base": _empty_role_summary("EUR", FxExposureRole.BASE),
        "quote": _empty_role_summary("USD", FxExposureRole.QUOTE),
        "has_direct_base_exposure": False,
        "has_direct_quote_exposure": False,
        "has_any_direct_exposure": False,
    }
    kwargs.update(overrides)
    return FxExposureSummary(**kwargs)


def _conversion_summary(**overrides) -> FxExposureConversionSummary:
    kwargs = {
        "linked_currency": "USD",
        "target_currency": "EUR",
        "direction": FxRateDirection.DIRECT,
        "requested_date": AS_OF,
        "effective_date": AS_OF,
        "is_backward_filled": False,
        "source": "ECB",
    }
    kwargs.update(overrides)
    return FxExposureConversionSummary(**kwargs)


# ---------------------------------------------------------------------------
# 1. FxPairIdentityPayload - storage order vs requested order
# ---------------------------------------------------------------------------


def test_pair_identity_accepts_a_direct_and_an_inverse_pair():
    assert _identity().direction is FxRateDirection.DIRECT
    inverse = _identity(base_currency="USD", quote_currency="EUR", direction=FxRateDirection.INVERSE)
    assert inverse.direction is FxRateDirection.INVERSE
    # Storage order is preserved verbatim so the reader never re-derives it.
    assert (inverse.stored_base_currency, inverse.stored_quote_currency) == ("EUR", "USD")


def test_pair_identity_normalizes_lowercase_codes():
    assert _identity(base_currency="eur", quote_currency=" usd ").base_currency == "EUR"


def test_pair_identity_rejects_a_degenerate_pair():
    # Situation: an FX scope was built with base == quote; the whole component
    # would describe a 1.0 conversion that no user ever asked for.
    with pytest.raises(ValidationError, match="base_currency and quote_currency must differ"):
        _identity(quote_currency="EUR", stored_quote_currency="EUR")


def test_pair_identity_rejects_a_storage_pair_that_is_not_the_requested_pair():
    # Situation: the resolved FxRate row belongs to a different pair than the one
    # requested (a lookup keyed on the wrong currency).
    with pytest.raises(ValidationError, match="must be the same pair as"):
        _identity(stored_quote_currency="GBP")


def test_pair_identity_rejects_storage_order_that_is_not_alphabetical():
    # Situation: `FxRate` rows are always stored base<quote; a payload claiming
    # otherwise means the row was read with its columns swapped.
    with pytest.raises(ValidationError, match="alphabetically before"):
        _identity(base_currency="USD", quote_currency="EUR", stored_base_currency="USD", stored_quote_currency="EUR", direction=FxRateDirection.DIRECT)


def test_pair_identity_rejects_a_direction_that_contradicts_storage_order():
    # Situation: the builder hardcodes DIRECT instead of deriving it - the reader
    # would then believe the service multiplied when it actually divided.
    with pytest.raises(ValidationError, match="direction is inconsistent"):
        _identity(direction=FxRateDirection.INVERSE)


# ---------------------------------------------------------------------------
# 2. FxCurrentRatePayload - the as-of rate and its staleness
# ---------------------------------------------------------------------------


def test_current_rate_accepts_a_backward_filled_rate_with_matching_staleness():
    payload = _current_rate(effective_date=EARLIER, is_backward_filled=True, staleness_days=2)
    assert payload.staleness_days == 2


@pytest.mark.parametrize("bad_rate", [Decimal("0"), Decimal("-1.5")])
def test_current_rate_rejects_a_non_positive_rate(bad_rate: Decimal):
    # Situation: a provider returned 0 (or a sign-flipped value) for a pair. A
    # zero rate silently turns every converted exposure into 0 rather than
    # reporting the pair as missing.
    with pytest.raises(ValidationError, match="rate must be a finite, positive Decimal"):
        _current_rate(rate=bad_rate)


@pytest.mark.parametrize("bad_rate", [Decimal("NaN"), Decimal("Infinity")])
def test_current_rate_rejects_non_finite_rates_at_the_pydantic_layer(bad_rate: Decimal):
    # Pydantic's own Decimal core validator refuses NaN/Infinity before the
    # field validator runs, so the model's `is_finite()` half never fires. The
    # contract that matters - a non-finite rate never reaches the prompt - still
    # holds, and this test is what proves it keeps holding if the annotation
    # ever changes (e.g. to `allow_inf_nan=True`).
    with pytest.raises(ValidationError, match="finite number"):
        _current_rate(rate=bad_rate)


def test_current_rate_rejects_a_degenerate_pair():
    with pytest.raises(ValidationError, match="base_currency and quote_currency must differ"):
        _current_rate(quote_currency="EUR")


def test_current_rate_rejects_an_effective_date_in_the_future():
    # Situation: a rate dated after the snapshot instant leaked in - the export
    # would claim knowledge the snapshot could not have had.
    with pytest.raises(ValidationError, match="effective_date must not be after requested_date"):
        _current_rate(effective_date=LATER)


def test_current_rate_rejects_staleness_that_disagrees_with_its_own_dates():
    # Situation: staleness copied from a sibling pair. The user is then told the
    # rate is fresh while its date says otherwise.
    with pytest.raises(ValidationError, match=r"staleness_days must equal"):
        _current_rate(effective_date=EARLIER, is_backward_filled=True, staleness_days=5)


def test_current_rate_rejects_a_backfill_flag_that_disagrees_with_staleness():
    with pytest.raises(ValidationError, match="is_backward_filled must match staleness_days > 0"):
        _current_rate(effective_date=EARLIER, is_backward_filled=False, staleness_days=2)


# ---------------------------------------------------------------------------
# 3. FxConversionProvenancePayload
# ---------------------------------------------------------------------------


def test_conversion_provenance_accepts_an_exact_and_a_backfilled_row():
    assert _provenance().is_backward_filled is False
    assert _provenance(effective_date=EARLIER, is_backward_filled=True).is_backward_filled is True


def test_conversion_provenance_rejects_a_degenerate_pair():
    with pytest.raises(ValidationError, match="base_currency and quote_currency must differ"):
        _provenance(quote_currency="EUR")


def test_conversion_provenance_rejects_an_effective_date_in_the_future():
    with pytest.raises(ValidationError, match="effective_date must not be after requested_date"):
        _provenance(effective_date=LATER)


def test_conversion_provenance_rejects_a_backfill_flag_that_disagrees_with_the_dates():
    # Situation: provenance says "exact match" while the row it describes is
    # actually two days old - the provenance section would understate staleness.
    with pytest.raises(ValidationError, match="is_backward_filled must match effective_date"):
        _provenance(effective_date=EARLIER, is_backward_filled=False)


# ---------------------------------------------------------------------------
# 4. FxExposureConversion - basis vs direction vs backfill
# ---------------------------------------------------------------------------


def test_exposure_conversion_accepts_the_three_declared_bases():
    assert _conversion().direction is None
    assert _conversion(basis=FxExposureConversionBasis.ENGINE_VALUATION).direction is None
    resolved = _conversion(basis=FxExposureConversionBasis.RESOLVED_RATE, direction=FxRateDirection.INVERSE, effective_date=EARLIER, is_backward_filled=True)
    assert resolved.direction is FxRateDirection.INVERSE


def test_exposure_conversion_rejects_an_effective_date_in_the_future():
    with pytest.raises(ValidationError, match="effective_date must not be after requested_date"):
        _conversion(basis=FxExposureConversionBasis.RESOLVED_RATE, direction=FxRateDirection.DIRECT, effective_date=LATER)


def test_exposure_conversion_rejects_a_resolved_rate_without_a_direction():
    # Situation: a real rate was applied but its direction was dropped, so the
    # provenance can no longer say whether the service multiplied or divided.
    with pytest.raises(ValidationError, match="RESOLVED_RATE conversions require a resolved direction"):
        _conversion(basis=FxExposureConversionBasis.RESOLVED_RATE, direction=None)


@pytest.mark.parametrize("basis", [FxExposureConversionBasis.IDENTITY, FxExposureConversionBasis.ENGINE_VALUATION])
def test_exposure_conversion_rejects_a_fabricated_direction(basis: FxExposureConversionBasis):
    # Situation: a direction is attached to a conversion where no rate was ever
    # applied - inventing provenance for something that did not happen.
    with pytest.raises(ValidationError, match="conversions must not carry a direction"):
        _conversion(basis=basis, direction=FxRateDirection.DIRECT)


def test_exposure_conversion_rejects_a_backfilled_identity_conversion():
    # An identity/engine conversion applies no rate, so it can never be stale.
    with pytest.raises(ValidationError, match="cannot be backward-filled"):
        _conversion(is_backward_filled=True)


def test_exposure_conversion_rejects_an_identity_conversion_dated_in_the_past():
    with pytest.raises(ValidationError, match="must have effective_date == requested_date"):
        _conversion(effective_date=EARLIER)


# ---------------------------------------------------------------------------
# 5. FxExposureRow - cash vs position, and native vs target amounts
# ---------------------------------------------------------------------------


def test_exposure_rows_accept_a_valid_cash_and_a_valid_position_row():
    assert _cash_row().valuation_source is None
    assert _position_row().native_amount is None


@pytest.mark.parametrize("field", ["target_amount", "native_amount"])
def test_exposure_row_rejects_non_finite_amounts(field: str):
    # Same layering as the FX rate above: pydantic refuses NaN/Infinity for a
    # Decimal field before `_validate_finite_decimal` is reached. The guarantee
    # under test is the outcome (no NaN in an exported amount), not which layer
    # enforces it.
    with pytest.raises(ValidationError, match="finite number"):
        _cash_row(**{field: Decimal("NaN")})


@pytest.mark.parametrize("bad_id", [0, -3])
def test_exposure_row_rejects_a_non_positive_entity_id(bad_id: int):
    # Situation: a 0 sentinel is passed where a real asset ID is expected, which
    # would attach the row to a non-existent asset.
    with pytest.raises(ValidationError, match="must be a positive int when present"):
        _position_row(asset_id=bad_id)


@pytest.mark.parametrize("bad_id", [True, False])
def test_exposure_row_rejects_a_bool_entity_id(bad_id: bool):
    # `True` *is* `1` in Python. The field is annotated `int | None`, so pydantic used
    # to coerce `True` -> `1` before the after-mode validator ran: the bool arm could
    # never fire, and a row passed `asset_id=True` was silently attributed to asset #1,
    # a real asset. A before-mode validator now sees the raw value and refuses it.
    #
    # Only `True` was ever the hole. Removing the before-mode validator makes this test
    # fail on `True` alone: `False` coerces to `0`, which the "must be positive" check
    # below catches anyway. Both cases are kept because the reason they are rejected is
    # now the same one, and a future refactor should not be able to quietly re-open the
    # half that used to slip through.
    with pytest.raises(ValidationError, match="must be a positive int when present"):
        _position_row(asset_id=bad_id)


def test_exposure_row_still_accepts_a_plain_int_entity_id():
    # The guard above rejects bools, not ints — a before-mode validator is easy to
    # write too broadly, and this is what would catch that.
    assert _position_row(asset_id=1).asset_id == 1


def test_exposure_row_rejects_an_engine_valuation_row_carrying_a_native_amount():
    # ENGINE_VALUATION exists precisely because no honest native amount could be
    # derived; carrying one anyway would present a fabricated figure as observed.
    with pytest.raises(ValidationError, match="must not carry a native_amount"):
        _position_row(native_amount=Decimal("10"))


def test_exposure_row_rejects_a_non_engine_row_without_a_native_amount():
    with pytest.raises(ValidationError, match="only ENGINE_VALUATION rows may omit native_amount"):
        _cash_row(native_amount=None)


def test_exposure_row_rejects_an_identity_conversion_that_changed_the_amount():
    # Situation: the row claims linked_currency == target_currency yet the two
    # amounts differ, which means a conversion happened and was not declared.
    with pytest.raises(ValidationError, match=r"identity conversions must leave native_amount == target_amount"):
        _cash_row(native_amount=Decimal("100"), target_amount=Decimal("110"))


def test_position_row_requires_an_asset_id():
    with pytest.raises(ValidationError, match="position exposure rows require asset_id"):
        _position_row(asset_id=None)


def test_position_row_rejects_cash_linkage():
    with pytest.raises(ValidationError, match="cannot use CASH_CURRENCY linkage"):
        _position_row(linkage=FxExposureLinkage.CASH_CURRENCY)


def test_position_row_requires_a_valuation_source():
    # Without it the reader has no basis at all for a value that carries neither
    # a native amount nor a rate.
    with pytest.raises(ValidationError, match="must carry a valuation_source"):
        _position_row(valuation_source=None)


def test_cash_row_rejects_an_asset_id():
    with pytest.raises(ValidationError, match="cash exposure rows cannot reference asset_id"):
        _cash_row(asset_id=4)


def test_cash_row_rejects_a_non_cash_linkage():
    with pytest.raises(ValidationError, match="cash exposure rows must use CASH_CURRENCY linkage"):
        _cash_row(linkage=FxExposureLinkage.TRADING_CURRENCY)


def test_cash_row_rejects_engine_valuation():
    # Cash is always a real native balance converted at a real rate, so the
    # "no honest native amount" escape hatch can never apply to it.
    with pytest.raises(ValidationError, match="cannot use ENGINE_VALUATION basis"):
        _cash_row(native_amount=None, conversion=_conversion(basis=FxExposureConversionBasis.ENGINE_VALUATION))


def test_cash_row_rejects_a_valuation_source():
    with pytest.raises(ValidationError, match="cash exposure rows cannot carry a valuation_source"):
        _cash_row(valuation_source="portfolio_engine")


# ---------------------------------------------------------------------------
# 6. FxExposureRoleSummary - the per-leg rollup and its explicit zero state
# ---------------------------------------------------------------------------


def test_role_summary_accepts_an_offsetting_leg_where_net_is_below_gross():
    summary = _role_summary(row_count=2, cash_row_count=2, net_target_amount=Decimal("0"), gross_target_amount=Decimal("200"))
    # A net-flat leg must stay distinguishable from a genuinely empty one.
    assert summary.has_direct_exposure is True
    assert summary.gross_target_amount == Decimal("200")


def test_role_summary_rejects_a_negative_gross_total():
    # Gross is a sum of absolute values, so a negative one means signs leaked in.
    with pytest.raises(ValidationError, match="gross_target_amount must not be negative"):
        _role_summary(gross_target_amount=Decimal("-1"))


def test_role_summary_rejects_counts_that_do_not_add_up():
    with pytest.raises(ValidationError, match=r"row_count must equal cash_row_count \+ position_row_count"):
        _role_summary(row_count=3)


def test_role_summary_rejects_a_zero_state_flag_that_contradicts_the_row_count():
    # `has_direct_exposure=False` means a *computed* absence; asserting it while
    # holding rows would report "no exposure" for a leg that has some.
    with pytest.raises(ValidationError, match="has_direct_exposure must match row_count > 0"):
        _role_summary(has_direct_exposure=False)


def test_role_summary_rejects_a_zero_row_leg_with_non_zero_totals():
    with pytest.raises(ValidationError, match="zero-row leg must carry zero net/gross totals"):
        _role_summary(row_count=0, cash_row_count=0, position_row_count=0, has_direct_exposure=False, net_target_amount=Decimal("5"), gross_target_amount=Decimal("5"))


def test_role_summary_rejects_a_net_larger_than_its_own_gross():
    with pytest.raises(ValidationError, match=r"abs\(net_target_amount\) must not exceed gross_target_amount"):
        _role_summary(net_target_amount=Decimal("-500"), gross_target_amount=Decimal("100"))


# ---------------------------------------------------------------------------
# 7. FxExposureSummary - base/quote rollup coherence
# ---------------------------------------------------------------------------


def test_exposure_summary_from_rows_derives_every_counter():
    rows = (_cash_row(), _position_row())
    summary = FxExposureSummary.from_rows(rows, base_currency="EUR", quote_currency="USD", target_currency="EUR")
    assert summary.total_row_count == 2
    assert (summary.base.row_count, summary.quote.row_count) == (1, 1)
    assert summary.has_any_direct_exposure is True
    assert summary.base.cash_row_count == 1
    assert summary.quote.position_row_count == 1


def test_exposure_summary_from_rows_reports_an_explicit_zero_state():
    summary = FxExposureSummary.from_rows((), base_currency="EUR", quote_currency="USD", target_currency="EUR")
    assert summary.total_row_count == 0
    assert summary.has_any_direct_exposure is False
    assert summary.base.net_target_amount == Decimal("0")


def test_exposure_summary_rejects_a_degenerate_pair():
    with pytest.raises(ValidationError, match="base_currency and quote_currency must differ"):
        _exposure_summary(quote_currency="EUR", quote=_empty_role_summary("EUR", FxExposureRole.QUOTE))


def test_exposure_summary_rejects_a_base_leg_describing_another_currency():
    # Situation: the base/quote summaries were built in the wrong order.
    with pytest.raises(ValidationError, match="base summary must describe the base_currency with role BASE"):
        _exposure_summary(base=_empty_role_summary("GBP", FxExposureRole.BASE))


def test_exposure_summary_rejects_a_quote_leg_carrying_the_base_role():
    with pytest.raises(ValidationError, match="quote summary must describe the quote_currency with role QUOTE"):
        _exposure_summary(quote=_empty_role_summary("USD", FxExposureRole.BASE))


def test_exposure_summary_rejects_a_total_that_does_not_match_its_legs():
    with pytest.raises(ValidationError, match=r"total_row_count must equal base.row_count \+ quote.row_count"):
        _exposure_summary(total_row_count=2)


def test_exposure_summary_rejects_base_and_quote_flags_that_contradict_their_legs():
    with pytest.raises(ValidationError, match="has_direct_base_exposure must match"):
        _exposure_summary(has_direct_base_exposure=True, has_any_direct_exposure=True)
    with pytest.raises(ValidationError, match="has_direct_quote_exposure must match"):
        _exposure_summary(has_direct_quote_exposure=True, has_any_direct_exposure=True)


def test_exposure_summary_rejects_an_any_flag_that_contradicts_the_two_legs():
    with pytest.raises(ValidationError, match="has_any_direct_exposure must match"):
        _exposure_summary(has_any_direct_exposure=True)


# ---------------------------------------------------------------------------
# 8. FxExposureBaseQuotePayload - rows plus a summary that cannot drift
# ---------------------------------------------------------------------------


def test_exposure_payload_always_rederives_its_summary_from_the_rows():
    # The summary is recomputed on every validation, so a stale/hand-written one
    # supplied by a caller can never survive into the export.
    payload = FxExposureBaseQuotePayload(
        base_currency="EUR",
        quote_currency="USD",
        target_currency="EUR",
        as_of=AS_OF,
        rows=(_cash_row(), _position_row()),
        summary=_exposure_summary(),  # deliberately claims an empty portfolio
    )
    assert payload.summary is not None
    assert payload.summary.total_row_count == 2
    assert payload.summary.has_any_direct_exposure is True


def test_exposure_payload_accepts_an_empty_row_set_as_a_real_zero():
    payload = FxExposureBaseQuotePayload(base_currency="EUR", quote_currency="USD", target_currency="EUR", as_of=AS_OF)
    assert payload.rows == ()
    assert payload.summary is not None and payload.summary.has_any_direct_exposure is False


def test_exposure_payload_rejects_a_degenerate_pair():
    with pytest.raises(ValidationError, match="base_currency and quote_currency must differ"):
        FxExposureBaseQuotePayload(base_currency="EUR", quote_currency="EUR", target_currency="EUR", as_of=AS_OF)


def test_exposure_payload_rejects_a_row_in_a_third_currency():
    # Situation: a GBP row survives the base/quote filter. `fx.exposure_base_quote`
    # only ever describes the two pair legs, never look-through exposure.
    with pytest.raises(ValidationError, match="is not base_currency/quote_currency"):
        FxExposureBaseQuotePayload(
            base_currency="EUR",
            quote_currency="USD",
            target_currency="EUR",
            as_of=AS_OF,
            rows=(_cash_row(linked_currency="GBP"),),
        )


# ---------------------------------------------------------------------------
# 9. Exposure provenance - one entry per converted currency, source required
# ---------------------------------------------------------------------------


def test_conversion_summary_accepts_a_resolved_and_an_identity_entry():
    assert _conversion_summary().source == "ECB"
    assert _conversion_summary(direction=None, source=None).direction is None


def test_conversion_summary_rejects_an_effective_date_in_the_future():
    with pytest.raises(ValidationError, match="effective_date must not be after requested_date"):
        _conversion_summary(effective_date=LATER)


def test_conversion_summary_rejects_a_source_on_an_identity_conversion():
    # An identity conversion applied no FxRate row, so quoting one as provenance
    # would credit a source that was never consulted.
    with pytest.raises(ValidationError, match="must not carry a source"):
        _conversion_summary(direction=None, source="ECB")


@pytest.mark.parametrize("empty_source", [None, ""])
def test_conversion_summary_requires_a_source_for_a_real_conversion(empty_source):
    with pytest.raises(ValidationError, match="non-identity conversions must carry a non-empty source"):
        _conversion_summary(source=empty_source)


def test_provenance_payload_rejects_a_degenerate_pair():
    with pytest.raises(ValidationError, match="base_currency and quote_currency must differ"):
        FxExposureProvenancePayload(base_currency="EUR", quote_currency="EUR", target_currency="EUR")


def test_provenance_payload_rejects_duplicate_currency_entries():
    # Provenance is deduplicated per linked currency; two entries for the same
    # currency would let two different rates claim the same conversion.
    with pytest.raises(ValidationError, match="must have unique linked_currency entries"):
        FxExposureProvenancePayload(
            base_currency="EUR",
            quote_currency="USD",
            target_currency="EUR",
            conversions=(_conversion_summary(), _conversion_summary(source="MANUAL")),
        )


def test_provenance_payload_accepts_one_entry_per_distinct_currency():
    payload = FxExposureProvenancePayload(
        base_currency="EUR",
        quote_currency="USD",
        target_currency="EUR",
        conversions=(_conversion_summary(), _conversion_summary(linked_currency="EUR", direction=None, source=None)),
    )
    assert {entry.linked_currency for entry in payload.conversions} == {"USD", "EUR"}
