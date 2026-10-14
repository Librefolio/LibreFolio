"""Scenario catalog loading, startup, and host-extension tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app import main
from backend.app.db.models import AssetType
from backend.app.schemas.risk_scenarios import RiskScenarioCatalogEntry, RiskScenarioCatalogResponse, RiskScenarioDimension, RiskScenarioKind, RiskScenarioSource
from backend.app.services.risk.scenario_catalog import (
    BUILT_IN_SCENARIO_CATALOG_DIR,
    RiskScenarioCatalogLoadError,
    get_loaded_risk_scenario_catalog,
    initialize_risk_scenario_catalog,
    load_risk_scenario_catalog,
    loader,
    reset_risk_scenario_catalog,
)

EUROPEAN_UNION_MEMBERS = {
    "AUT",
    "BEL",
    "BGR",
    "HRV",
    "CYP",
    "CZE",
    "DNK",
    "EST",
    "FIN",
    "FRA",
    "DEU",
    "GRC",
    "HUN",
    "IRL",
    "ITA",
    "LVA",
    "LTU",
    "LUX",
    "MLT",
    "NLD",
    "POL",
    "PRT",
    "ROU",
    "SVK",
    "SVN",
    "ESP",
    "SWE",
}


def _write_host_scenario(path: Path, *, scenario_id: str, languages: str = "  it: Scenario host") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""schema_version: 1
id: {scenario_id}
kind: historical_replay
tags: [host]
name:
{languages}
description:
  it: Descrizione host
defaults:
  start: 2020-01-01
  end: 2020-01-31
""",
        encoding="utf-8",
    )


def test_builtin_catalog_contains_approved_presets_and_eu_membership(tmp_path):
    catalog = load_risk_scenario_catalog(
        host_dir=tmp_path / "missing-host",
        loaded_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    ids = {entry.scenario.id for entry in catalog.items}

    assert ids == {
        "banking_crisis",
        "covid_crash_2020",
        "custom_period",
        "equity_crash",
        "european_union_shock",
        "global_financial_crisis",
        "global_risk_off",
        "inflation_rates_2022",
    }
    assert all(entry.source == RiskScenarioSource.BUILT_IN for entry in catalog.items)
    assert catalog.status.built_in_count == 8
    assert catalog.status.host_count == 0
    assert catalog.warnings == []

    group = next(group for group in catalog.geography_groups if group.id == "european_union")
    assert set(group.members) == EUROPEAN_UNION_MEMBERS
    assert group.name.resolve("fr") == "Union européenne"


def test_host_catalog_accepts_partial_localization_with_deterministic_fallback(tmp_path):
    host_dir = tmp_path / "scenario_catalog"
    _write_host_scenario(
        host_dir / "historical" / "host_replay.yml",
        scenario_id="host_replay",
    )

    catalog = load_risk_scenario_catalog(host_dir=host_dir)
    entry = next(entry for entry in catalog.items if entry.scenario.id == "host_replay")

    assert entry.source == RiskScenarioSource.HOST
    assert entry.source_file == "historical/host_replay.yml"
    assert entry.scenario.name.resolve("fr") == "Scenario host"
    assert catalog.status.host_count == 1
    assert catalog.status.warning_count == 0


def test_invalid_and_duplicate_host_files_are_rejected_without_hiding_builtins(tmp_path):
    host_dir = tmp_path / "scenario_catalog"
    _write_host_scenario(
        host_dir / "historical" / "duplicate.yml",
        scenario_id="covid_crash_2020",
    )
    invalid = host_dir / "hypothetical" / "invalid.yml"
    invalid.parent.mkdir(parents=True, exist_ok=True)
    invalid.write_text("schema_version: 1\nid: broken\nkind: hypothetical_shock\n", encoding="utf-8")

    catalog = load_risk_scenario_catalog(host_dir=host_dir)

    assert catalog.status.built_in_count == 8
    assert catalog.status.host_count == 0
    assert catalog.status.warning_count == 2
    assert {warning.source_file for warning in catalog.warnings} == {
        "historical/duplicate.yml",
        "hypothetical/invalid.yml",
    }


def test_invalid_builtin_file_fails_catalog_loading(tmp_path):
    built_in_dir = tmp_path / "built_in"
    scenario = built_in_dir / "historical" / "invalid.yml"
    scenario.parent.mkdir(parents=True, exist_ok=True)
    scenario.write_text(
        """schema_version: 1
id: invalid_builtin
kind: historical_replay
name:
  en: Invalid
description:
  en: Missing required built-in languages
defaults:
  start: 2020-01-01
  end: 2020-01-31
""",
        encoding="utf-8",
    )

    with pytest.raises(RiskScenarioCatalogLoadError, match="missing built-in languages"):
        load_risk_scenario_catalog(
            built_in_dir=built_in_dir,
            host_dir=tmp_path / "host",
        )


@pytest.mark.asyncio
async def test_initialize_catalog_uses_to_thread_and_publishes_state(monkeypatch, tmp_path):
    reset_risk_scenario_catalog()
    expected = load_risk_scenario_catalog(host_dir=tmp_path / "host")
    calls: list[object] = []

    def fake_load():
        return expected

    async def fake_to_thread(function, *args, **kwargs):
        calls.append(function)
        return function(*args, **kwargs)

    monkeypatch.setattr(loader, "load_risk_scenario_catalog", fake_load)
    monkeypatch.setattr(loader.asyncio, "to_thread", fake_to_thread)

    loaded = await initialize_risk_scenario_catalog()

    assert calls == [fake_load]
    assert loaded is expected
    assert get_loaded_risk_scenario_catalog() is expected
    reset_risk_scenario_catalog()


@pytest.mark.asyncio
async def test_lifespan_fails_before_mutating_state_when_builtin_catalog_is_invalid(monkeypatch):
    catalog_called = False
    avatars_called = False

    def fake_signal_runtime():
        return SimpleNamespace(
            pandas_ta_classic_version="test",
            talib_version="test",
        )

    async def fail_catalog():
        nonlocal catalog_called
        catalog_called = True
        raise RiskScenarioCatalogLoadError("invalid built-in catalog")

    def track_avatars():
        nonlocal avatars_called
        avatars_called = True
        return 0

    monkeypatch.setattr(main, "validate_signal_runtime", fake_signal_runtime)
    monkeypatch.setattr(main.SignalPluginRegistry, "auto_discover", lambda: None)
    monkeypatch.setattr(main.SignalPluginRegistry, "list_plugin_codes", lambda: [])
    monkeypatch.setattr(main, "ensure_data_dirs", lambda: None)
    monkeypatch.setattr(main, "initialize_risk_scenario_catalog", fail_catalog)
    monkeypatch.setattr(main, "seed_default_avatars", track_avatars)

    with pytest.raises(RiskScenarioCatalogLoadError, match="invalid built-in catalog"):
        async with main.lifespan(main.app):
            pass

    assert catalog_called is True
    assert avatars_called is False


def test_builtin_catalog_directory_is_package_owned():
    assert BUILT_IN_SCENARIO_CATALOG_DIR.is_dir()
    assert BUILT_IN_SCENARIO_CATALOG_DIR.parent.name == "scenario_catalog"


# =============================================================================
# asset_class buckets <-> AssetType — the enum/table gate
# =============================================================================
#
# A hypothetical shock on the `asset_class` dimension is keyed by AssetType.
# When a type has no bucket the engine does not fail: it shocks that exposure by
# 0.0 and flags it UNCONFIGURED_ZERO. So a scenario that forgot BOND reports a
# bond book as perfectly immune to an equity crash, silently and forever.
#
# These tests are the only place that failure becomes visible, and they assert
# BOTH directions: no AssetType without a bucket (the forgotten-type hazard) and
# no bucket without an AssetType (the typo / post-rename-leftover hazard — this
# enum really did carry CROWDFUND_LOAN before it became CROWDFUND).
#
# Scenarios are selected by their DECLARED dimension, never by their folder:
# built_in/hypothetical/ holds four YAMLs of which only two are asset_class
# (banking_crisis is sector, european_union_shock is geography), so a
# directory-based selection would assert against the wrong files.


def _built_in_catalog(tmp_path: Path) -> RiskScenarioCatalogResponse:
    """Load the package-owned catalog alone, with host_dir aimed at nothing."""
    return load_risk_scenario_catalog(
        host_dir=tmp_path / "missing-host",
        loaded_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _built_in_hypothetical_entries(catalog: RiskScenarioCatalogResponse) -> list[RiskScenarioCatalogEntry]:
    return [entry for entry in catalog.items if entry.source == RiskScenarioSource.BUILT_IN and entry.scenario.kind == RiskScenarioKind.HYPOTHETICAL_SHOCK]


def _asset_class_entries(catalog: RiskScenarioCatalogResponse) -> list[RiskScenarioCatalogEntry]:
    return [entry for entry in _built_in_hypothetical_entries(catalog) if entry.scenario.defaults.dimension == RiskScenarioDimension.ASSET_CLASS]


def _require_asset_class_entries(tmp_path: Path) -> list[RiskScenarioCatalogEntry]:
    """Select the asset_class scenarios and refuse to proceed on an empty selection.

    Every assertion below is a loop over this list: if the selection ever comes
    back empty the loops become no-ops and the gate reports green while checking
    nothing. That is the one failure mode worse than the one it guards.
    """
    entries = _asset_class_entries(_built_in_catalog(tmp_path))
    assert entries, "no built-in scenario declares defaults.dimension == asset_class: the selection is empty, so every assertion in this gate would pass vacuously"
    return entries


def test_asset_class_selection_is_driven_by_dimension_not_by_directory(tmp_path):
    catalog = _built_in_catalog(tmp_path)
    hypothetical = _built_in_hypothetical_entries(catalog)
    asset_class_ids = {entry.scenario.id for entry in _asset_class_entries(catalog)}
    other_dimension_ids = {entry.scenario.id for entry in hypothetical if entry.scenario.defaults.dimension != RiskScenarioDimension.ASSET_CLASS}

    assert {"equity_crash", "global_risk_off"} <= asset_class_ids
    # The filter has to be load-bearing: hypothetical scenarios on other
    # dimensions exist, and their buckets are sectors or geographies, not
    # AssetType values. Selecting the folder instead of the dimension would drag
    # them into the gate and assert AssetType membership on the string "Financials".
    assert other_dimension_ids, "every built-in hypothetical scenario is asset_class, so this gate can no longer prove that the dimension filter excludes sector/geography buckets"
    assert not (asset_class_ids & other_dimension_ids)


def test_every_asset_type_has_a_bucket_in_every_asset_class_scenario(tmp_path):
    entries = _require_asset_class_entries(tmp_path)

    missing: list[str] = []
    for entry in entries:
        configured = set(entry.scenario.defaults.bucket_shocks)
        absent = [asset_type.value for asset_type in AssetType if asset_type.value not in configured]
        if absent:
            missing.append(f"  {entry.scenario.id} ({entry.source_file}) is missing: {', '.join(absent)}")

    assert not missing, "asset_class scenarios do not cover every AssetType. An exposure with no bucket is shocked by 0.0 and flagged UNCONFIGURED_ZERO — no error is raised, the number is simply wrong:\n" + "\n".join(missing)


def test_every_asset_class_bucket_key_is_a_valid_asset_type(tmp_path):
    entries = _require_asset_class_entries(tmp_path)
    known = {asset_type.value for asset_type in AssetType}

    unknown: list[str] = []
    for entry in entries:
        strays = [bucket for bucket in entry.scenario.defaults.bucket_shocks if bucket not in known]
        if strays:
            unknown.append(f"  {entry.scenario.id} ({entry.source_file}) declares: {', '.join(sorted(strays))}")

    assert not unknown, "asset_class scenarios declare buckets that are not AssetType values. A bucket nobody matches is dead configuration: the shock is never applied and nothing says so — the usual cause is a typo or a key left behind by an enum rename:\n" + "\n".join(unknown)


def test_every_built_in_scenario_file_is_reachable_by_the_loader():
    """A YAML the loader never opens is a scenario this gate never checks.

    `_built_in_entries` does not walk the catalog root: it reads exactly
    `historical/` and `hypothetical/` (plus `geography/` for group definitions).
    A scenario dropped into any other folder is not rejected — it is ignored,
    which would put it outside every assertion above while looking installed.
    """
    on_disk = {path.relative_to(BUILT_IN_SCENARIO_CATALOG_DIR).as_posix() for path in (*BUILT_IN_SCENARIO_CATALOG_DIR.rglob("*.yml"), *BUILT_IN_SCENARIO_CATALOG_DIR.rglob("*.yaml"))}
    assert on_disk, f"no YAML found under {BUILT_IN_SCENARIO_CATALOG_DIR}: the scan itself failed, so its result proves nothing"

    catalog = load_risk_scenario_catalog(host_dir=BUILT_IN_SCENARIO_CATALOG_DIR / "does-not-exist")
    loaded = {entry.source_file for entry in catalog.items if entry.source == RiskScenarioSource.BUILT_IN}
    geography_groups = {name for name in on_disk if name.startswith("geography/")}
    assert geography_groups, "geography/ holds no YAML any more: this exclusion is now hiding whatever moved there"

    ignored = sorted(on_disk - loaded - geography_groups)
    assert not ignored, "these built-in YAML files are not loaded by the catalog, because the loader only scans historical/ and hypothetical/. Move them there or teach the loader the new folder:\n" + "\n".join(f"  {name}" for name in ignored)
