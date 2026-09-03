"""Load and validate built-in and host Risk scenario YAML files."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import yaml
from pydantic import TypeAdapter, ValidationError

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.schemas.risk_scenarios import (
    RISK_SCENARIO_OFFICIAL_LANGUAGES,
    RiskGeographyGroupDefinition,
    RiskScenarioCatalogEntry,
    RiskScenarioCatalogResponse,
    RiskScenarioCatalogStatus,
    RiskScenarioCatalogWarning,
    RiskScenarioDefinition,
    RiskScenarioKind,
    RiskScenarioSource,
)

logger = get_logger(__name__)

BUILT_IN_SCENARIO_CATALOG_DIR = Path(__file__).resolve().parent / "built_in"
_SCENARIO_ADAPTER = TypeAdapter(RiskScenarioDefinition)
_loaded_catalog: Optional[RiskScenarioCatalogResponse] = None


class RiskScenarioCatalogLoadError(RuntimeError):
    """Built-in scenario catalog is invalid and startup must stop."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _yaml_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        (
            *directory.rglob("*.yml"),
            *directory.rglob("*.yaml"),
        ),
        key=lambda path: path.as_posix(),
    )


def _read_yaml(path: Path) -> dict:
    if path.stat().st_size > 1_000_000:
        raise ValueError("YAML file exceeds the 1 MB limit")
    payload = yaml.load(
        path.read_text(encoding="utf-8"),
        Loader=_UniqueKeySafeLoader,
    )
    if not isinstance(payload, dict):
        raise ValueError("YAML root must be an object")
    return payload


def _validate_built_in_localizations(definition) -> None:
    required = set(RISK_SCENARIO_OFFICIAL_LANGUAGES)
    for field_name in ("name", "description"):
        localized = getattr(definition, field_name)
        missing = sorted(required - set(localized.root))
        if missing:
            raise ValueError(f"{field_name} is missing built-in languages: {', '.join(missing)}")


def _validate_group_localizations(group: RiskGeographyGroupDefinition) -> None:
    missing = sorted(set(RISK_SCENARIO_OFFICIAL_LANGUAGES) - set(group.name.root))
    if missing:
        raise ValueError(f"name is missing built-in languages: {', '.join(missing)}")


def _parse_scenario(path: Path, expected_kind: RiskScenarioKind):
    definition = _SCENARIO_ADAPTER.validate_python(_read_yaml(path))
    if definition.kind != expected_kind:
        raise ValueError(f"directory expects {expected_kind.value}, got {definition.kind.value}")
    return definition


def _built_in_entries(built_in_dir: Path) -> tuple[list[RiskScenarioCatalogEntry], list[RiskGeographyGroupDefinition]]:  # noqa: C901 — per-file catalog load loops with error wrapping
    if not built_in_dir.is_dir():
        raise RiskScenarioCatalogLoadError(f"Built-in scenario catalog directory does not exist: {built_in_dir}")

    entries: list[RiskScenarioCatalogEntry] = []
    seen_ids: set[str] = set()
    for directory_name, expected_kind in (
        ("historical", RiskScenarioKind.HISTORICAL_REPLAY),
        ("hypothetical", RiskScenarioKind.HYPOTHETICAL_SHOCK),
    ):
        directory = built_in_dir / directory_name
        for path in _yaml_files(directory):
            relative = path.relative_to(built_in_dir).as_posix()
            try:
                definition = _parse_scenario(path, expected_kind)
                _validate_built_in_localizations(definition)
                if definition.id in seen_ids:
                    raise ValueError(f"duplicate built-in scenario id: {definition.id}")
            except (OSError, ValueError, ValidationError, yaml.YAMLError) as exc:
                raise RiskScenarioCatalogLoadError(f"Invalid built-in scenario {relative}: {exc}") from exc
            seen_ids.add(definition.id)
            entries.append(
                RiskScenarioCatalogEntry(
                    source=RiskScenarioSource.BUILT_IN,
                    source_file=relative,
                    scenario=definition,
                )
            )

    groups: list[RiskGeographyGroupDefinition] = []
    seen_group_ids: set[str] = set()
    for path in _yaml_files(built_in_dir / "geography"):
        relative = path.relative_to(built_in_dir).as_posix()
        try:
            group = RiskGeographyGroupDefinition.model_validate(_read_yaml(path))
            _validate_group_localizations(group)
            if group.id in seen_group_ids:
                raise ValueError(f"duplicate geography group id: {group.id}")
        except (OSError, ValueError, ValidationError, yaml.YAMLError) as exc:
            raise RiskScenarioCatalogLoadError(f"Invalid built-in geography group {relative}: {exc}") from exc
        seen_group_ids.add(group.id)
        groups.append(group)

    if not entries:
        raise RiskScenarioCatalogLoadError("Built-in scenario catalog contains no scenarios")
    if not any(group.id == "european_union" for group in groups):
        raise RiskScenarioCatalogLoadError("Built-in geography catalog must define european_union")

    return entries, groups


def _host_entries(
    host_dir: Path,
    existing_ids: set[str],
) -> tuple[list[RiskScenarioCatalogEntry], list[RiskScenarioCatalogWarning]]:
    entries: list[RiskScenarioCatalogEntry] = []
    warnings: list[RiskScenarioCatalogWarning] = []
    accepted_ids = set(existing_ids)

    for directory_name, expected_kind in (
        ("historical", RiskScenarioKind.HISTORICAL_REPLAY),
        ("hypothetical", RiskScenarioKind.HYPOTHETICAL_SHOCK),
    ):
        directory = host_dir / directory_name
        for path in _yaml_files(directory):
            relative = path.relative_to(host_dir).as_posix()
            try:
                definition = _parse_scenario(path, expected_kind)
                if definition.id in accepted_ids:
                    raise ValueError(f"scenario id already exists: {definition.id}")
            except (OSError, ValueError, ValidationError, yaml.YAMLError) as exc:
                warning = RiskScenarioCatalogWarning(
                    code="host_scenario_rejected",
                    source_file=relative,
                    message=str(exc),
                )
                warnings.append(warning)
                logger.exception(
                    "Host risk scenario rejected",
                    source_file=relative,
                    error=str(exc),
                )
                continue

            accepted_ids.add(definition.id)
            entries.append(
                RiskScenarioCatalogEntry(
                    source=RiskScenarioSource.HOST,
                    source_file=relative,
                    scenario=definition,
                )
            )

    return entries, warnings


def load_risk_scenario_catalog(
    *,
    built_in_dir: Path = BUILT_IN_SCENARIO_CATALOG_DIR,
    host_dir: Optional[Path] = None,
    loaded_at: Optional[datetime] = None,
) -> RiskScenarioCatalogResponse:
    """Synchronously load the complete typed catalog."""
    resolved_host_dir = host_dir if host_dir is not None else get_data_dir() / "scenario_catalog"
    built_in_entries, geography_groups = _built_in_entries(built_in_dir)
    host_entries, warnings = _host_entries(
        resolved_host_dir,
        {entry.scenario.id for entry in built_in_entries},
    )
    items = sorted(
        (*built_in_entries, *host_entries),
        key=lambda entry: (entry.scenario.kind.value, entry.scenario.id),
    )
    groups = sorted(geography_groups, key=lambda group: group.id)
    return RiskScenarioCatalogResponse(
        items=items,
        geography_groups=groups,
        status=RiskScenarioCatalogStatus(
            loaded_at=loaded_at or datetime.now(UTC),
            built_in_count=len(built_in_entries),
            host_count=len(host_entries),
            warning_count=len(warnings),
        ),
        warnings=warnings,
    )


async def initialize_risk_scenario_catalog() -> RiskScenarioCatalogResponse:
    """Load filesystem-backed YAML without blocking the event loop."""
    catalog = await asyncio.to_thread(load_risk_scenario_catalog)
    global _loaded_catalog
    _loaded_catalog = catalog
    return catalog


def get_loaded_risk_scenario_catalog() -> RiskScenarioCatalogResponse:
    if _loaded_catalog is None:
        raise RuntimeError("Risk scenario catalog has not been initialized")
    return _loaded_catalog


def reset_risk_scenario_catalog() -> None:
    """Clear process state for isolated tests."""
    global _loaded_catalog
    _loaded_catalog = None
