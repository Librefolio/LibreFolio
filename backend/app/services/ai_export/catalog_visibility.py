"""Visibility contract for AI Export dataset and analysis selections."""

from __future__ import annotations

from enum import StrEnum


class CatalogVisibility(StrEnum):
    """Controls whether a registered selection is directly public."""

    INTERNAL = "internal"
    PUBLIC = "public"
