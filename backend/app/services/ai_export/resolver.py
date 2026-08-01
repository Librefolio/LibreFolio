"""Deterministic exact resolver for the static AI Export profile catalog."""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import Sequence

from backend.app.schemas.ai_export import AiExportCatalogResponse
from backend.app.services.ai_export.models import (
    SCHEMA_VERSION,
    ResolvedProfile,
    UnsupportedAiExportProfileError,
    build_resolved_profiles,
    profile_request,
)
from backend.app.services.ai_export.profiles import DETAIL_OVERLAYS, TASK_SPECS

ALL_PROFILES = build_resolved_profiles(TASK_SPECS, DETAIL_OVERLAYS)
PROFILE_CATALOG = ALL_PROFILES
SUPPORTED_PROFILE_IDS = tuple(profile.profile_id for profile in ALL_PROFILES)

_PROFILE_BY_KEY = MappingProxyType(
    {
        (
            profile.domain.value,
            profile.task.value,
            profile.detail_level.value,
        ): profile
        for profile in ALL_PROFILES
    }
)


def _exact_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, str):
        return value
    return str(value)


def resolve_profile(
    domain: object,
    task: object,
    detail_level: object,
) -> ResolvedProfile:
    """Resolve one exact allow-listed profile without defaults or normalization."""

    key = (
        _exact_value(domain),
        _exact_value(task),
        _exact_value(detail_level),
    )
    try:
        return _PROFILE_BY_KEY[key]
    except KeyError as exc:
        raise UnsupportedAiExportProfileError(
            profile_request(domain, task, detail_level),
            SUPPORTED_PROFILE_IDS,
        ) from exc


def all_profiles() -> tuple[ResolvedProfile, ...]:
    return ALL_PROFILES


def to_catalog_response(
    profiles: Sequence[ResolvedProfile] = ALL_PROFILES,
) -> AiExportCatalogResponse:
    return AiExportCatalogResponse(
        schema_version=SCHEMA_VERSION,
        entries=[profile.to_catalog_entry() for profile in profiles],
    )


def get_catalog_response() -> AiExportCatalogResponse:
    return to_catalog_response()


get_profile = resolve_profile
catalog_response = get_catalog_response

__all__ = [
    "ALL_PROFILES",
    "PROFILE_CATALOG",
    "SUPPORTED_PROFILE_IDS",
    "all_profiles",
    "catalog_response",
    "get_catalog_response",
    "get_profile",
    "resolve_profile",
    "to_catalog_response",
]
