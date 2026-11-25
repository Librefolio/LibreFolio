"""The asset profile (FA): the voice of its catalogue and the shapes of their values (plan 68, §3.6).

A voice is one fact of an asset's profile (its TER, its countries, the maturity of a bond…), stored as one row per change in
``asset_profile_updates`` with a JSON ``value``. The catalogue (``services/assets/profile/catalogue.py``) lists every voice
with its :class:`FAProfileVoice` and turns a raw value into its stored form; a voice it does not list is refused.

How a value is stored, one rule per shape:

========== ========================================== =======================================================
Shape      Example                                    Rule
========== ========================================== =======================================================
number     ``"1.78"``                                 a decimal as a string, never a float
percentage ``"0.0022"`` (0.22 %)                      a fraction, like the rest of the project
amount     ``{"amount": "55173000000", "currency": "EUR"}``  a decimal as a string plus the source's ISO 4217 code
date       ``"2028-10-10"``                           ISO
text       ``"…"``                                    as the source gives it, in its language
choice     ``"physical_sampling"``                    one of the voice's codes
country    ``"IRL"``                                  ISO 3166 alpha-3
currency   ``"USD"``                                  ISO 4217
map        ``{"JPN": "0.0604", "USA": "0.9396"}``     key → weight, four decimals summing to 1 (``metadata.py``)
table      ``[{"from": …, "to": …, "rate": …}]``      rows in order
========== ========================================== =======================================================

``null`` is a value left empty on purpose («Lascia vuoto»).
"""

from __future__ import annotations

from datetime import date, datetime
from datetime import date as date_type
from enum import StrEnum
from typing import Any, Dict, List, Optional

from pydantic import ConfigDict, Field, model_validator

from backend.app.db.models import AssetType
from backend.app.schemas.assets.enrichers import FAEnricherBinding
from backend.app.schemas.common import BaseBulkDeleteResponse, BaseDeleteResult, DateRangeModel, MinStartDateRangeModel, StepSpan, StrictModel


class ProfileShape(StrEnum):
    """The shape of a voice's value: how it is written in ``value`` and checked."""

    NUMBER = "number"
    PERCENTAGE = "percentage"
    AMOUNT = "amount"
    DATE = "date"
    TEXT = "text"
    CHOICE = "choice"
    COUNTRY = "country"
    CURRENCY = "currency"
    MAP = "map"
    TABLE = "table"


class ProfileSign(StrEnum):
    """Which signs a numeric voice (number, percentage, amount, the rate of a table row) accepts."""

    ANY = "any"
    NON_NEGATIVE = "non_negative"
    POSITIVE = "positive"


class ProfileGroup(StrEnum):
    """Where the «Profilo» tab shows a voice. A voice with no group has a place of its own (the description) or is read
    by someone else only (the issuer's LEI, the lane 62 voices)."""

    CLASSIFICATION = "classification"
    KEY_FIGURES = "key_figures"
    FUND = "fund"
    COMPANY = "company"
    BOND = "bond"
    IDENTITY = "identity"


class ProfileMapKeys(StrEnum):
    """What the keys of a map voice are: ISO 3166 alpha-3 countries, or the standard sectors."""

    COUNTRY = "country"
    SECTOR = "sector"


class ProfileTopic(StrEnum):
    """What a voice is about, in one short word (plan 68, E7b): the enrichers' window says what each enricher fills by
    these («costi, struttura, paesi, settori»), not by the voices' names. Declared by each voice of the catalogue; the
    order of the members is the order the window shows them in."""

    COSTS = "costs"
    STRUCTURE = "structure"
    MANAGER = "manager"
    COUNTRIES = "countries"
    SECTORS = "sectors"
    COUPONS = "coupons"
    MATURITY = "maturity"
    YIELD = "yield"
    DURATION = "duration"
    SIZE = "size"
    FINANCIALS = "financials"
    LEGAL_FORM = "legal_form"
    ISSUER = "issuer"
    DESCRIPTION = "description"


class ProfilePeriod(StrEnum):
    """The span a voice's value covers, when it is a figure of a period (BI-PROF): the tab names the period beside the
    value, from the value's source date."""

    FISCAL_YEAR = "fiscal_year"


class FAProfileVoice(StrictModel):
    """One voice of the catalogue: its key, the shape of its value and how the «Profilo» tab shows it."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(..., description="The voice's key, stored in asset_profile_updates.key")
    shape: ProfileShape = Field(..., description="How the value is written and checked")
    sign: Optional[ProfileSign] = Field(None, description="Signs accepted by a numeric voice; None for the others")
    unit: Optional[str] = Field(None, description="What the number counts, when the shape does not say it (years, per_100_nominal)")
    groups: tuple[ProfileGroup, ...] = Field((), description="The tab groups that show it; empty for a voice with no cell of its own")
    key_figure: bool = Field(False, description="Shown as a key figure card")
    charted: bool = Field(False, description="A key figure with a chart of its history")
    volatile: bool = Field(False, description="Changes at every read (fund size, yields, duration…): «Ultime variazioni» leaves its source rows out")
    choices: tuple[str, ...] = Field((), description="The codes a choice voice accepts; empty for the others")
    map_keys: Optional[ProfileMapKeys] = Field(None, description="What a map voice's keys are; None for the others")
    topic: ProfileTopic = Field(..., description="What the voice is about, in one word: the enrichers' window says what an enricher fills by its voices' topics")
    period: Optional[ProfilePeriod] = Field(None, description="fiscal_year: the value is a figure of the fiscal year that ends on its source date; None for a voice that is not a period's figure")


class FAProfileReadOutcome(StrictModel):
    """One enricher's read for one asset (``ask`` and ``refresh``)."""

    code: str
    identifier_type: str
    identifier: str
    status: str = Field(..., description="ok, not_found, error")
    voices: list[str] = Field(default_factory=list, description="The voices it gave, after the catalogue")
    error_code: Optional[str] = Field(None, description="RATE_LIMITED for a refusal for too many requests")
    retry_after: Optional[float] = None
    from_cache: bool = False


class FAProfileAskVoice(StrictModel):
    """One voice as the enrichers give it: the merged value and its enricher, and what the others gave."""

    value: Any = Field(None, description="The value in its stored form (never null: a source never empties a voice)")
    source: str
    source_date: Optional[date] = None
    others: Dict[str, Any] = Field(default_factory=dict, description="Enricher code → its value, for the others that gave it")


class FAProfileAskRequest(StrictModel):
    """``POST /assets/profile/ask``: read an asset's enrichers without saving. Either ``asset_id`` (its bindings and
    type), or ``asset_type`` with ``enrichers`` (an asset not created yet). Without ``keys``, every voice («Chiedi tutto»)."""

    asset_id: Optional[int] = None
    asset_type: Optional[AssetType] = None
    enrichers: Optional[Dict[str, FAEnricherBinding]] = None
    keys: Optional[List[str]] = None

    @model_validator(mode="after")
    def _one_asset(self) -> FAProfileAskRequest:
        if self.asset_id is None and (self.asset_type is None or self.enrichers is None):
            raise ValueError("asset_id, or asset_type with enrichers")
        if self.asset_id is not None and self.enrichers is not None:
            raise ValueError("asset_id or enrichers, not both")
        return self


class FAProfileAskResponse(StrictModel):
    """What the enrichers give now, merged, and how each read went. Nothing was written."""

    voices: Dict[str, FAProfileAskVoice]
    outcomes: List[FAProfileReadOutcome]


class FAProfileRefreshResult(StrictModel):
    """«Aggiorna» for one asset: the voices written and how each enricher's read went."""

    asset_id: int
    written: List[str] = Field(default_factory=list)
    outcomes: List[FAProfileReadOutcome] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Why nothing was read (an asset that does not exist)")
    enrichers_read: int = Field(0, ge=0, description="How many enrichers this refresh read for the asset: 0 when none bound can be used here (turned off, not installed, not configured)")


class FAProfileRefreshResponse(StrictModel):
    """``POST /assets/profile/refresh``."""

    results: List[FAProfileRefreshResult]


# =============================================================================
# READ, CATALOGUE, FORGET (plan 68, D1)
# =============================================================================


class FAProfileCatalogueResponse(StrictModel):
    """``GET /assets/profile/catalogue``: every voice of the profile, in the catalogue's order (for the forms)."""

    voices: List[FAProfileVoice]


class FAProfileChangesQuery(StrictModel):
    """Which changes a profile read adds: without ``key`` the «Ultime variazioni» panel (a volatile voice only with the
    rows written by hand and the source row that replaces one), with ``key`` every row of that voice («Storia del dato»).
    Never filtered by the read's ``date_range``."""

    key: Optional[str] = Field(None, description="One voice: all its rows. None: the panel, every voice")
    page: int = Field(0, ge=0, description="The page, 0 first; 20 changes per page, newest first")


class FAProfileQueryItem(StrictModel):
    """One asset of ``POST /assets/profile/query``: its voices (all when ``keys`` is absent) as steps in ``date_range``."""

    asset_id: int
    keys: Optional[List[str]] = Field(None, description="The voices to read; None for every voice, [] for none (only the changes)")
    date_range: DateRangeModel | MinStartDateRangeModel = Field(..., description="Two days, one day (end absent), or start `min`: the first day the asset's profile has among the voices asked; nothing stored answers no voice")
    changes: Optional[FAProfileChangesQuery] = Field(None, description="Add a page of changes; None for none")


class FAProfileStepPoint(StepSpan):
    """One step of a voice: from ``date`` to ``through`` the value is ``value`` (stored form; null: empty on purpose),
    given by ``source``. ``update_id`` is the row the step starts with.

    ``date`` is cut to the range read; ``opened_on`` and ``source_date`` never are (D1c): the «dati al» of the tab."""

    value: Any = None
    source: str
    update_id: int
    opened_on: date_type = Field(..., description="The read_on of the row that opens the step: the day it was really read, never cut to the range")
    source_date: Optional[date_type] = Field(None, description="The day the source says the value is of («data at 30/09»), when it says one")
    confirmed_on: Optional[date_type] = Field(
        None,
        description="D1d, a volatile voice's last step when it holds «now»: the day «now» was last confirmed (its source last gave the voice, else the row's day); null elsewhere",
    )
    stale: Optional[bool] = Field(None, description="D1d, with confirmed_on: the confirmation is more than 30 days old («non aggiornato»); null elsewhere")


class FAProfileChange(StrictModel):
    """One change: a row of ``asset_profile_updates`` and the voice's value before it."""

    id: int = Field(..., description="The row's id, for «Dimentica»")
    key: str
    value: Any = Field(None, description="The new value, stored form; null: emptied on purpose")
    previous: Any = Field(None, description="The value before it; null with has_previous false for the voice's first row")
    has_previous: bool
    source: str = Field(..., description="An enricher's code, user, or legacy")
    user_id: Optional[int] = Field(None, description="Who wrote a user row; null for the sources and for a deleted user")
    user_name: Optional[str] = Field(None, description="The username of who wrote a user row (never the email); null for the sources and for a deleted user")
    user_avatar_url: Optional[str] = Field(None, description="The avatar of who wrote a user row, when it has one")
    read_on: date
    source_date: Optional[date] = None
    created_at: datetime
    previous_source: Optional[str] = Field(None, description="Who gave the value before (an enricher's code, user, legacy); null for the voice's first row")
    previous_user_id: Optional[int] = Field(None, description="Who wrote the value before, when it was written by hand")
    previous_user_name: Optional[str] = Field(None, description="The username of who wrote the value before, when it was written by hand")
    previous_read_on: Optional[date] = Field(None, description="The day of the value before")
    previous_source_date: Optional[date] = Field(None, description="The source's own date of the value before («prima, del 31 agosto»)")


class FAProfileChangesPage(StrictModel):
    """One page of changes, newest first."""

    items: List[FAProfileChange]
    total: int = Field(..., description="How many changes there are in all")
    page: int
    page_size: int


class FAProfileQueryResult(StrictModel):
    """The profile of one asset: voice → its steps (a voice with none left out), and the changes when asked.

    An asset that does not exist answers ``error`` «Asset not found», no voice and no changes (as the price read does);
    an asset that exists with no rows answers no voice and no error («no profile yet»)."""

    asset_id: int
    voices: Dict[str, List[FAProfileStepPoint]] = Field(default_factory=dict)
    changes: Optional[FAProfileChangesPage] = None
    error: Optional[str] = Field(None, description="«Asset not found» for an asset that does not exist; None otherwise")


class FAProfileQueryResponse(StrictModel):
    """``POST /assets/profile/query``: one result per item, in order. ``as_of`` is the server's time before the read: a
    «Dimentica» sends it back, and a row written after it is not forgotten."""

    as_of: datetime
    items: List[FAProfileQueryResult]


class FAProfileForgetItem(StrictModel):
    """One asset of ``DELETE /assets/profile``: the rows to forget, and ``as_of`` of the read the page shows."""

    asset_id: int
    update_ids: List[int] = Field(..., min_length=1)
    as_of: datetime = Field(..., description="The as_of of the profile read the page shows; a row written after it is not forgotten")


class FAProfileForgetResult(BaseDeleteResult):
    """The rows forgotten for one asset."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int


class FAProfileForgetResponse(BaseBulkDeleteResponse[FAProfileForgetResult]):
    """``DELETE /assets/profile``: all or nothing over the whole request."""
