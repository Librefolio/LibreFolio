"""The broker's operating profile: how a broker takes orders, what it charges, how it converts, how it treats taxes.

P1 of project 67 (contract §7; decisioni-REB §2, M6, M18, M21). The account keeps it as one JSON document in
``brokers.operating_profile`` (a text column, decision D1 (a)), read and written only through this module:

- ``BrokerOperatingProfile`` is the document. It refuses keys it does not declare, at every level.
- One row per currency (M21): the order mode with its step, and its fees, at most one per side. The broker's
  ``conversion_mode`` and ``tax_regime`` sit at the root.
- The order mode and fee shapes have **the same JSON form as the planner request's** (a copied mode reaches the planner
  unchanged), written as classes of this module (decision D2 (c)). D2 (a), importing the request's classes, put them in
  the brokers' OpenAPI, where the client generator cannot read them: the planner's models are strict, so their
  discriminators are a bare ``const``, and they declare their defaults as required (P1 plan, «Rischi»: the way out is
  D2 (c), never a change to ``schemas/pac_allocator``). A test holds the two forms equal in both directions. The value
  types (ids, decimals, currencies) are still imported from ``schemas/pac_allocator/base``; that package never imports
  this one, and nothing here touches the database.
- ``tax_regime`` is ``administered`` or ``declarative``; an absent one reads ``declarative`` in one place only,
  ``effective_tax_regime`` (M6, M18). There is no «not said» value.
- ``stored_operating_profile`` reads a stored text tolerantly (never raises: an unreadable document is «no profile»);
  ``operating_profile_text`` writes the canonical text and enforces the weight cap (decision D6).

A new optional field keeps ``profile_version`` 1; a change of shape or meaning of a field is a new version, and the
reader converts the old one (decision D15). A test pins the JSON schema's fingerprint. The default of
``conversion_mode`` moved from ``manual`` to ``automatic`` in version 1 (TL-6 of project 67): every saved text carries
the key, so only a profile never saved reads the new default.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import Field, ValidationError, field_validator, model_validator

from backend.app.schemas.common import StrictModel
from backend.app.schemas.pac_allocator.base import CurrencyCode, OrderSide, PlannerConversionMode, PlannerFixedDecimal, PlannerId, PlannerWholeQuantityStep, QuantityUnit

#: The largest stored document, in bytes of its canonical text (decision D6): a mode with two fees weighs about 600 bytes.
OPERATING_PROFILE_MAX_BYTES = 16_384

TaxRegime = Literal["administered", "declarative"]


class OperatingProfileTooLarge(ValueError):
    """The canonical text of a profile is over ``OPERATING_PROFILE_MAX_BYTES``: nothing is written."""


# ---------------------------------------------------------------------------
# The request's order mode and fee shapes, in the same JSON form (D2 (c); test 4 compares them both ways)
# ---------------------------------------------------------------------------


class BrokerProfileMoney(StrictModel):
    """``PlannerMoneyInput``: an amount and its currency."""

    amount: PlannerFixedDecimal
    currency: CurrencyCode


class BrokerProfileWholeQuantityMode(StrictModel):
    """``WholeQuantityCapability``: orders by number of units, a multiple of the step."""

    kind: Literal["whole_quantity"] = Field(json_schema_extra={"enum": ["whole_quantity"]})
    capability_id: PlannerId
    quantity_unit: QuantityUnit = Field(json_schema_extra={"enum": ["asset_unit"]})
    quantity_step: PlannerWholeQuantityStep


class BrokerProfileAmountMode(StrictModel):
    """``MonetaryAmountCapability``: orders by amount, a multiple of the step."""

    kind: Literal["monetary_amount"] = Field(json_schema_extra={"enum": ["monetary_amount"]})
    capability_id: PlannerId
    order_amount_step: BrokerProfileMoney


type BrokerProfileOrderCapability = Annotated[Union[BrokerProfileWholeQuantityMode, BrokerProfileAmountMode], Field(discriminator="kind")]


class BrokerProfileNoFeeCap(StrictModel):
    """``NoFeeCap``."""

    kind: Literal["none"] = Field(json_schema_extra={"enum": ["none"]})


class BrokerProfileAmountFeeCap(StrictModel):
    """``AmountFeeCap``."""

    kind: Literal["amount"] = Field(json_schema_extra={"enum": ["amount"]})
    amount: BrokerProfileMoney


type BrokerProfileFeeCap = Annotated[Union[BrokerProfileNoFeeCap, BrokerProfileAmountFeeCap], Field(discriminator="kind")]


class BrokerProfileFeeSchedule(StrictModel):
    """``BrokerFeeScheduleInput``: an absent money field is zero."""

    fee_schedule_id: PlannerId
    capability_id: PlannerId
    side: OrderSide
    fixed_fee: BrokerProfileMoney | None = None
    rate: PlannerFixedDecimal = "0"
    variable_floor: BrokerProfileMoney | None = None
    variable_cap: BrokerProfileFeeCap = Field(default_factory=lambda: BrokerProfileNoFeeCap(kind="none"))


def _money_amounts(money: BrokerProfileMoney | None) -> list[BrokerProfileMoney]:
    return [] if money is None else [money]


class BrokerProfileOrderMode(StrictModel):
    """One currency's rules (M21): how the broker takes an order in it, and what it charges on each side."""

    currency: CurrencyCode
    capability: BrokerProfileOrderCapability
    fees: list[BrokerProfileFeeSchedule] = Field(default=[], max_length=2)

    @model_validator(mode="after")
    def _the_checks_the_planner_makes(self) -> BrokerProfileOrderMode:
        """What the planner checks locally (decision D4 (b)): a refused input is recognised, a stored one is never fixed."""
        moneys = [*_capability_moneys(self.capability), *_fee_moneys(self.fees, self.capability.capability_id)]
        if any(money.currency != self.currency for money in moneys):
            raise ValueError(f"every amount of the {self.currency} row must be in {self.currency}")
        return self


def _capability_moneys(capability: BrokerProfileWholeQuantityMode | BrokerProfileAmountMode) -> list[BrokerProfileMoney]:
    """The step must be greater than zero; an amount step is a money of the row."""
    if isinstance(capability, BrokerProfileWholeQuantityMode):
        if int(capability.quantity_step) <= 0:
            raise ValueError("the order step must be greater than zero")
        return []
    if Decimal(capability.order_amount_step.amount) <= 0:
        raise ValueError("the order amount step must be greater than zero")
    return [capability.order_amount_step]


def _fee_moneys(fees: list[BrokerProfileFeeSchedule], capability_id: str) -> list[BrokerProfileMoney]:
    """Each fee names the row's mode, one per side, nothing negative; its amounts are moneys of the row."""
    moneys: list[BrokerProfileMoney] = []
    sides: set[str] = set()
    for fee in fees:
        if fee.capability_id != capability_id:
            raise ValueError(f"the fee {fee.fee_schedule_id!r} names another order mode")
        if fee.side in sides:
            raise ValueError(f"two fees on the {fee.side} side")
        sides.add(fee.side)
        fee_moneys = [*_money_amounts(fee.fixed_fee), *_money_amounts(fee.variable_floor)]
        if isinstance(fee.variable_cap, BrokerProfileAmountFeeCap):
            fee_moneys.append(fee.variable_cap.amount)
        if Decimal(fee.rate) < 0 or any(Decimal(money.amount) < 0 for money in fee_moneys):
            raise ValueError("a fee cannot be negative")
        moneys.extend(fee_moneys)
    return moneys


class BrokerOperatingProfile(StrictModel):
    """The broker's operating profile, version 1 (contract §7)."""

    profile_version: Literal[1] = Field(json_schema_extra={"enum": [1]})
    order_modes: list[BrokerProfileOrderMode] = []
    #: Absent reads ``automatic``, the Broker converting when the orders execute (TL-6 of project 67, the developer's choice
    #: of 23/11: «per tutti, prima di essere specificato»). It was ``manual`` until then; ``operating_profile_text`` writes
    #: the key in every profile it saves, so no stored profile changes meaning and the version stays 1 (D15).
    conversion_mode: PlannerConversionMode = "automatic"
    #: Absent means ``declarative``: read it through ``effective_tax_regime``. An explicit ``null`` is refused, and an absent
    #: one is served absent (``exclude_if``), so what GET serves a PATCH takes back.
    tax_regime: TaxRegime | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("profile_version", mode="before")
    @classmethod
    def _an_integer_version(cls, value: object) -> object:
        """``1`` only: the lax mode would also take ``1.0`` or ``True``."""
        if type(value) is not int:
            raise ValueError("profile_version is a whole number")
        return value

    @field_validator("tax_regime", mode="before")
    @classmethod
    def _no_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("tax_regime is 'administered' or 'declarative'; leave the key out for the default")
        return value

    @model_validator(mode="after")
    def _one_row_per_currency(self) -> BrokerOperatingProfile:
        currencies = [row.currency for row in self.order_modes]
        if len(currencies) != len(set(currencies)):
            raise ValueError("two order modes in the same currency: one row per currency")
        return self

    @property
    def effective_tax_regime(self) -> TaxRegime:
        """The one place where an absent regime becomes ``declarative`` (M6, M18)."""
        return self.tax_regime or "declarative"


def stored_operating_profile(raw: str | None) -> BrokerOperatingProfile | None:
    """The profile a stored text holds, or ``None``: never raises.

    ``NULL``, an empty text, text that is not JSON, a JSON that is not an object, an unknown version or an invalid shape all
    read as «no profile», and the text stays where it is (no clean-up of saved data).
    """
    if not raw:
        return None
    try:
        return BrokerOperatingProfile.model_validate_json(raw)
    except ValidationError:
        # The answer is «no profile»: the caller that knows the broker logs it (``BrokerService.get_by_id``).
        return None


def operating_profile_text(profile: BrokerOperatingProfile) -> str:
    """The canonical text of ``profile``: sorted keys, no spaces, absent fields left out; over the cap it raises."""
    text = json.dumps(profile.model_dump(mode="json", exclude_none=True), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(text.encode()) > OPERATING_PROFILE_MAX_BYTES:
        raise OperatingProfileTooLarge(f"the operating profile is {len(text.encode())} bytes, over {OPERATING_PROFILE_MAX_BYTES}")
    return text
