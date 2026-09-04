"""Typed contracts for the startup-loaded Risk scenario catalog."""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import Field, FiniteFloat, PositiveInt, RootModel, field_validator, model_validator

from backend.app.schemas.common import StrictModel

RISK_SCENARIO_SCHEMA_VERSION = 1
RISK_SCENARIO_OFFICIAL_LANGUAGES = ("en", "it", "fr", "es")

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$")
_COUNTRY_PATTERN = re.compile(r"^[A-Z]{3}$")


class RiskScenarioKind(StrEnum):
    HISTORICAL_REPLAY = "historical_replay"
    HYPOTHETICAL_SHOCK = "hypothetical_shock"


class RiskScenarioSource(StrEnum):
    BUILT_IN = "built_in"
    HOST = "host"


class RiskScenarioDimension(StrEnum):
    ASSET_CLASS = "asset_class"
    SECTOR = "sector"
    GEOGRAPHY = "geography"


class RiskScenarioMissingHistoryPolicy(StrEnum):
    MANUAL_PROXY_OR_EXCLUDE = "manual_proxy_or_exclude"


class RiskScenarioLocalizedText(RootModel[Dict[str, str]]):
    """Language map stored directly in YAML."""

    @model_validator(mode="before")
    @classmethod
    def validate_language_map(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict) or not value:
            raise ValueError("localized text requires at least one language")
        if len(value) > 20:
            raise ValueError("localized text supports at most 20 languages")

        normalized: dict[str, str] = {}
        for raw_language, raw_text in value.items():
            if not isinstance(raw_language, str) or not isinstance(raw_text, str):
                raise ValueError("localized text keys and values must be strings")
            language = raw_language.strip().lower()
            text = raw_text.strip()
            if not _LANGUAGE_PATTERN.fullmatch(language):
                raise ValueError(f"invalid language code: {raw_language}")
            if not text:
                raise ValueError(f"localized text for {language} must not be empty")
            if len(text) > 2000:
                raise ValueError(f"localized text for {language} is too long")
            if language in normalized:
                raise ValueError(f"duplicate language after normalization: {language}")
            normalized[language] = text
        return normalized

    def resolve(self, language: str) -> str:
        requested = language.strip().lower()
        for candidate in (requested, "en", "it"):
            if candidate in self.root:
                return self.root[candidate]
        first_language = min(self.root)
        return self.root[first_language]


class RiskHistoricalReplayDefaults(StrictModel):

    start: Optional[date] = None
    end: Optional[date] = None
    missing_history_policy: RiskScenarioMissingHistoryPolicy = RiskScenarioMissingHistoryPolicy.MANUAL_PROXY_OR_EXCLUDE
    composition_policy: Literal["current_buy_and_hold"] = "current_buy_and_hold"

    @model_validator(mode="after")
    def validate_period(self) -> RiskHistoricalReplayDefaults:
        if (self.start is None) != (self.end is None):
            raise ValueError("historical replay defaults require both start and end or neither")
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("historical replay start must be on or before end")
        return self


class RiskHistoricalReplayEditable(StrictModel):

    dates: bool = True
    missing_history_policy: bool = True
    proxies: bool = True
    exclusions: bool = True


class RiskHistoricalReplayLimits(StrictModel):

    minimum_calendar_days: PositiveInt = 1
    maximum_calendar_days: Optional[PositiveInt] = None

    @model_validator(mode="after")
    def validate_calendar_bounds(self) -> RiskHistoricalReplayLimits:
        if self.maximum_calendar_days is not None and self.maximum_calendar_days < self.minimum_calendar_days:
            raise ValueError("maximum_calendar_days must be >= minimum_calendar_days")
        return self


class RiskHypotheticalShockDefaults(StrictModel):

    dimension: RiskScenarioDimension
    bucket_shocks: Dict[str, FiniteFloat] = Field(..., min_length=1, max_length=100)

    @field_validator("bucket_shocks")
    @classmethod
    def normalize_bucket_shocks(cls, value: Dict[str, float]) -> Dict[str, float]:
        normalized: dict[str, float] = {}
        for raw_bucket, shock in value.items():
            bucket = raw_bucket.strip()
            if not bucket:
                raise ValueError("bucket shock IDs must not be empty")
            if len(bucket) > 80:
                raise ValueError("bucket shock IDs must be at most 80 characters")
            if bucket in normalized:
                raise ValueError(f"duplicate bucket shock: {bucket}")
            normalized[bucket] = shock
        return normalized


class RiskHypotheticalShockEditable(StrictModel):

    dimension: bool = False
    bucket_shocks: bool = True
    manual_overrides: bool = True


class RiskHypotheticalShockLimits(StrictModel):

    minimum_shock: FiniteFloat = -1.0
    maximum_shock: FiniteFloat = 1.0
    maximum_buckets: PositiveInt = 100

    @model_validator(mode="after")
    def validate_shock_bounds(self) -> RiskHypotheticalShockLimits:
        if self.minimum_shock >= self.maximum_shock:
            raise ValueError("minimum_shock must be lower than maximum_shock")
        return self


class RiskScenarioBase(StrictModel):

    schema_version: Literal[RISK_SCENARIO_SCHEMA_VERSION]
    id: str = Field(..., min_length=1, max_length=80)
    kind: RiskScenarioKind
    tags: List[str] = Field(default_factory=list, max_length=12)
    name: RiskScenarioLocalizedText
    description: RiskScenarioLocalizedText

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if value != value.strip() or value != value.lower() or not _SLUG_PATTERN.fullmatch(value):
            raise ValueError("scenario id must be a lowercase ASCII snake-case slug")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]) -> List[str]:
        normalized: list[str] = []
        for raw_tag in value:
            if raw_tag != raw_tag.strip() or raw_tag != raw_tag.lower() or len(raw_tag) > 32 or not _SLUG_PATTERN.fullmatch(raw_tag):
                raise ValueError("scenario tags must be lowercase ASCII snake-case slugs up to 32 characters")
            normalized.append(raw_tag)
        if len(normalized) != len(set(normalized)):
            raise ValueError("scenario tags must be unique")
        return sorted(normalized)

    @model_validator(mode="after")
    def validate_localized_lengths(self) -> RiskScenarioBase:
        if any(len(text) > 160 for text in self.name.root.values()):
            raise ValueError("scenario names must be at most 160 characters")
        return self


class RiskHistoricalReplayScenario(RiskScenarioBase):
    kind: Literal[RiskScenarioKind.HISTORICAL_REPLAY] = Field(json_schema_extra={"enum": ["historical_replay"]})
    defaults: RiskHistoricalReplayDefaults
    editable: RiskHistoricalReplayEditable = Field(default_factory=RiskHistoricalReplayEditable)
    limits: RiskHistoricalReplayLimits = Field(default_factory=RiskHistoricalReplayLimits)


class RiskHypotheticalShockScenario(RiskScenarioBase):
    kind: Literal[RiskScenarioKind.HYPOTHETICAL_SHOCK] = Field(json_schema_extra={"enum": ["hypothetical_shock"]})
    allowed_dimensions: List[RiskScenarioDimension] = Field(..., min_length=1, max_length=3)
    defaults: RiskHypotheticalShockDefaults
    editable: RiskHypotheticalShockEditable = Field(default_factory=RiskHypotheticalShockEditable)
    limits: RiskHypotheticalShockLimits = Field(default_factory=RiskHypotheticalShockLimits)

    @field_validator("allowed_dimensions")
    @classmethod
    def validate_allowed_dimensions(cls, value: List[RiskScenarioDimension]) -> List[RiskScenarioDimension]:
        if len(value) != len(set(value)):
            raise ValueError("allowed_dimensions must be unique")
        return value

    @model_validator(mode="after")
    def validate_hypothetical_defaults(self) -> RiskHypotheticalShockScenario:
        if self.defaults.dimension not in self.allowed_dimensions:
            raise ValueError("default dimension must be listed in allowed_dimensions")
        if any(dimension in {RiskScenarioDimension.SECTOR, RiskScenarioDimension.GEOGRAPHY} for dimension in self.allowed_dimensions) and "Other" not in self.defaults.bucket_shocks:
            raise ValueError("sector and geography scenarios require an Other bucket")
        if len(self.defaults.bucket_shocks) > self.limits.maximum_buckets:
            raise ValueError("bucket_shocks exceeds maximum_buckets")
        for bucket, shock in self.defaults.bucket_shocks.items():
            if not math.isfinite(shock) or shock < self.limits.minimum_shock or shock > self.limits.maximum_shock:
                raise ValueError(f"shock for bucket {bucket} is outside configured limits")
        if self.editable.dimension and len(self.allowed_dimensions) < 2:
            raise ValueError("editable dimension requires at least two allowed_dimensions")
        return self


RiskScenarioDefinition = Annotated[
    Union[
        RiskHistoricalReplayScenario,
        RiskHypotheticalShockScenario,
    ],
    Field(discriminator="kind"),
]


class RiskScenarioCatalogEntry(StrictModel):

    source: RiskScenarioSource
    source_file: str
    scenario: RiskScenarioDefinition


class RiskScenarioCatalogWarning(StrictModel):

    code: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    source_file: str
    message: str


class RiskGeographyGroupDefinition(StrictModel):

    schema_version: Literal[RISK_SCENARIO_SCHEMA_VERSION]
    id: str = Field(..., min_length=1, max_length=80)
    name: RiskScenarioLocalizedText
    members: List[str] = Field(..., min_length=1, max_length=300)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if value != value.strip() or value != value.lower() or not _SLUG_PATTERN.fullmatch(value):
            raise ValueError("geography group id must be a lowercase ASCII snake-case slug")
        return value

    @field_validator("members")
    @classmethod
    def validate_members(cls, value: List[str]) -> List[str]:
        normalized = [member.strip().upper() for member in value]
        if any(not _COUNTRY_PATTERN.fullmatch(member) for member in normalized):
            raise ValueError("geography group members must be ISO-3166 alpha-3 codes")
        if len(normalized) != len(set(normalized)):
            raise ValueError("geography group members must be unique")
        return sorted(normalized)


class RiskScenarioCatalogStatus(StrictModel):

    schema_version: Literal[RISK_SCENARIO_SCHEMA_VERSION] = RISK_SCENARIO_SCHEMA_VERSION
    loaded_at: datetime
    built_in_count: int = Field(..., ge=0)
    host_count: int = Field(..., ge=0)
    warning_count: int = Field(..., ge=0)

    @field_validator("loaded_at")
    @classmethod
    def validate_loaded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("loaded_at must be timezone-aware")
        return value


class RiskScenarioCatalogResponse(StrictModel):

    items: List[RiskScenarioCatalogEntry] = Field(default_factory=list)
    geography_groups: List[RiskGeographyGroupDefinition] = Field(default_factory=list)
    status: RiskScenarioCatalogStatus
    warnings: List[RiskScenarioCatalogWarning] = Field(default_factory=list)


__all__ = [
    "RISK_SCENARIO_OFFICIAL_LANGUAGES",
    "RISK_SCENARIO_SCHEMA_VERSION",
    "RiskGeographyGroupDefinition",
    "RiskHistoricalReplayScenario",
    "RiskHypotheticalShockScenario",
    "RiskScenarioCatalogEntry",
    "RiskScenarioCatalogResponse",
    "RiskScenarioCatalogStatus",
    "RiskScenarioCatalogWarning",
    "RiskScenarioDefinition",
    "RiskScenarioDimension",
    "RiskScenarioKind",
    "RiskScenarioLocalizedText",
    "RiskScenarioMissingHistoryPolicy",
    "RiskScenarioSource",
]
