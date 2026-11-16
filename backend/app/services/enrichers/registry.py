"""Registry of the enrichers, discovered from ``services/enricher_providers/`` (plan 68, B1).

Registration refuses an enricher whose class declarations break the contract (``enrichers/base.py``) with
``EnricherDeclarationError``: a degree for every asset type, voices of the catalogue for covered types only, a class of
terms, the identifier types it accepts. Discovery records the refusal as a failure of that plugin
(``GET /system/plugin-diagnostics``); the other enrichers load.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Type

from backend.app.db.models import AssetType
from backend.app.services.assets.profile.catalogue import CATALOGUE
from backend.app.services.enrichers.base import EnricherTerms
from backend.app.services.platform.provider_registry import AbstractProviderRegistry

_CODE = re.compile(r"[a-z][a-z0-9_]*")
_IDENTIFIER_TYPE = re.compile(r"[A-Z][A-Z0-9_]*")


class EnricherDeclarationError(ValueError):
    """An enricher whose class declarations break the contract (``enrichers/base.py``): it is not registered."""


def _declaration_problems(plugin_class: type) -> list[str]:  # noqa: C901 — one flat check per declaration
    """What breaks the contract in the class declarations of ``plugin_class``; empty when nothing does."""
    problems: list[str] = []
    code = getattr(plugin_class, "code", None)
    if not isinstance(code, str) or not _CODE.fullmatch(code):
        problems.append("code must be a lowercase identifier")
    name = getattr(plugin_class, "name", None)
    if not isinstance(name, str) or not name.strip():
        problems.append("name must be a non-empty text")
    if not isinstance(getattr(plugin_class, "terms", None), EnricherTerms):
        problems.append("terms must be an EnricherTerms")
    identifier_types = getattr(plugin_class, "accepted_identifier_types", None)
    if not isinstance(identifier_types, tuple) or not identifier_types or not all(isinstance(kind, str) and _IDENTIFIER_TYPE.fullmatch(kind) for kind in identifier_types):
        problems.append("accepted_identifier_types must be a non-empty tuple of upper-case types")
    priority = getattr(plugin_class, "default_priority", None)
    if not isinstance(priority, Mapping):
        problems.append("default_priority must map every AssetType to a degree or None")
        priority = {}
    else:
        missing = [asset_type.value for asset_type in AssetType if asset_type not in priority]
        extra = [str(key) for key in priority if not isinstance(key, AssetType)]
        if missing:
            problems.append(f"default_priority has no degree for {', '.join(missing)}")
        if extra:
            problems.append(f"default_priority names what is not an AssetType: {', '.join(extra)}")
        wrong = [str(key) for key, degree in priority.items() if degree is not None and (isinstance(degree, bool) or not isinstance(degree, int) or degree < 0)]
        if wrong:
            problems.append(f"default_priority has a degree that is not a whole number >= 0 for {', '.join(wrong)}")
    voices = getattr(plugin_class, "voices", None)
    if not isinstance(voices, Mapping):
        problems.append("voices must map asset types to catalogue keys")
    else:
        for asset_type, keys in voices.items():
            if not isinstance(asset_type, AssetType):
                problems.append(f"voices names what is not an AssetType: {asset_type}")
                continue
            if priority.get(asset_type) is None:
                problems.append(f"voices for {asset_type.value}, a type it does not cover")
            unknown = sorted(key for key in keys if key not in CATALOGUE) if isinstance(keys, (set, frozenset)) else ["(not a set)"]
            if unknown:
                problems.append(f"voices for {asset_type.value} not in the catalogue: {', '.join(unknown)}")
    return problems


class EnricherRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "enricher_providers"

    @classmethod
    def _get_plugin_code_attr(cls) -> str:
        return "code"

    @classmethod
    def _get_registration_code(cls, provider_class: Type) -> object:
        # The code is a class attribute: no instance is built to read it
        return getattr(provider_class, "code", None)

    @classmethod
    def settings_family(cls) -> str:
        return "enricher"

    @classmethod
    def _validate_plugin_class(cls, plugin_class: Type) -> None:
        super()._validate_plugin_class(plugin_class)
        problems = _declaration_problems(plugin_class)
        if problems:
            raise EnricherDeclarationError(f"{plugin_class.__qualname__}: {'; '.join(problems)}")
