"""Scenario catalog loading, startup, and host-extension tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app import main
from backend.app.schemas.risk_scenarios import RiskScenarioSource
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
