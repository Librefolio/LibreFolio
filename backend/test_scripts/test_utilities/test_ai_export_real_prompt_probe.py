"""Focused tests for the permanent AI Export real-prompt probe helpers."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from backend.app.services.auth_service import hash_password, verify_password
from backend.test_scripts.diagnostics.ai_export_real_prompt_probe import (
    COMPOSITION_COMPONENTS,
    NAMED_PROMPT_RETENTION,
    PUBLIC_CATALOG_V1_ANALYSES,
    PUBLIC_CATALOG_V1_DATASETS,
    PUBLIC_CATALOG_V1_EXPECTED_CASE_COUNT,
    PUBLIC_CATALOG_V1_PROFILE,
    AssetCandidate,
    FxCandidate,
    ProbeError,
    TargetProbeCase,
    _parse_args,
    audit_public_tables,
    audit_snapshot_semantics,
    build_artifact_aliases,
    build_comparison_baseline_manifest,
    build_dimension_summary,
    build_manual_review_placeholder,
    build_period_detail_matrix,
    build_probe_svgs,
    build_prompt_filename,
    build_retained_prompt_manifest,
    build_user_scopes,
    classify_http_failure,
    classify_prompt_category,
    compare_metric_runs,
    discover_catalog,
    finalize_public_catalog_prompt_retention,
    hash_file,
    hash_sqlite_family,
    is_technical_dataset,
    legacy_sampling_manifest,
    measure_broker_scope_diagnostics,
    measure_canonical_breakdown,
    measure_prompt_composition,
    measure_targeted_adequacy_diagnostics,
    measure_technical_diagnostics,
    metric_change_reasons,
    nearest_metric_entry,
    nearest_rank_percentile,
    numeric_distribution_stats,
    parse_target_case,
    prepare_runtime_credentials,
    prompt_size_category,
    public_catalog_v1_cases,
    public_catalog_v1_scope,
    public_catalog_v1_selections,
    rank_asset_candidates,
    rank_fx_candidates,
    representative_cases,
    representative_scopes,
    run_probe,
    sanitize_filename_part,
    save_and_reread_prompt,
    scan_text_for_secrets,
    select_prompt_retention_reasons,
    select_target_scope,
    should_continue_after_failure,
    signal_metric_summary,
    sqlite_backup,
    sqlite_primary_unchanged,
    stable_metric_key_text,
    tuning_v2_cases,
    tuning_v2_exclusions,
    validate_manifest_checks,
    validate_reconciled_breakdown,
)


def test_public_catalog_artifact_aliases_are_anonymized_and_deterministic():
    assert build_artifact_aliases(("marco", "alfy", "marco"), anonymize=True) == {
        "marco": "user_anon_01",
        "alfy": "user_anon_02",
    }
    assert build_artifact_aliases(("marco",), anonymize=False) == {"marco": "marco"}


def _metric(
    selection_id: str,
    *,
    status: str = "ok",
    chars: int = 100,
    datasets: list[str] | None = None,
    components: list[str] | None = None,
) -> dict[str, object]:
    return {
        "user_alias": "alfy",
        "mode": "data",
        "domain": "portfolio",
        "selection_id": selection_id,
        "scope_alias": "all",
        "period_label": "1Y",
        "detail_level": "full",
        "status": status,
        "rendered_prompt_chars": chars,
        "datasets_included": datasets or [],
        "components_included": components or [],
    }


def _public_metric(
    selection_id: str,
    period: str,
    detail: str,
    chars: int,
    *,
    index: int = 0,
    status: str = "ok",
) -> dict[str, object]:
    domain = selection_id.partition(".")[0]
    mode = "data" if selection_id in PUBLIC_CATALOG_V1_DATASETS else "analysis"
    return {
        "user_alias": "marco",
        "mode": mode,
        "selection_kind": "dataset" if mode == "data" else "analysis",
        "domain": domain,
        "selection_id": selection_id,
        "scope_alias": f"{domain}_scope_{index:02d}",
        "period_label": period,
        "detail_level": detail,
        "status": status,
        "rendered_prompt_chars": chars,
        "rendered_prompt_bytes": chars + 5,
        "rendered_prompt_sha256": f"{index:064x}",
        "rendered_prompt_estimated_token_equivalent": chars / 4,
        "category": "financial",
        "category_tags": ["financial"],
        "prompt_file": None,
        "retained": False,
        "retention_reasons": [],
    }


def test_catalog_discovery_is_dynamic_and_filterable():
    catalog = {
        "datasets": [
            {"id": "portfolio.overview", "domain": "portfolio", "version": 1},
            {"id": "asset.technical", "domain": "asset", "version": 3},
        ],
        "analyses": [
            {"id": "portfolio.review", "domain": "portfolio", "version": 2},
            {"id": "fx.trend", "domain": "fx", "version": 4},
        ],
    }

    discovered = discover_catalog(catalog)
    filtered = discover_catalog(catalog, mode="analysis", domain="portfolio")

    assert {(item["kind"], item["id"]) for item in discovered} == {
        ("dataset", "portfolio.overview"),
        ("dataset", "asset.technical"),
        ("analysis", "portfolio.review"),
        ("analysis", "fx.trend"),
    }
    assert [(item["kind"], item["id"]) for item in filtered] == [("analysis", "portfolio.review")]


def test_catalog_discovery_rejects_duplicate_runtime_ids():
    catalog = {
        "datasets": [
            {"id": "portfolio.overview", "domain": "portfolio"},
            {"id": "portfolio.overview", "domain": "portfolio"},
        ],
        "analyses": [],
    }

    with pytest.raises(ProbeError, match="Duplicate catalog selection"):
        discover_catalog(catalog)


def test_filename_sanitation_and_deterministic_prompt_name():
    assert sanitize_filename_part(" À/Broker: One? ") == "a_broker_one"
    assert sanitize_filename_part("../") == "unknown"
    filename = build_prompt_filename("Alfy", "Data", "Portfolio", "portfolio.all data", "Broker #1", "1Y", "Full")
    assert filename == "alfy__data__portfolio__portfolio.all_data__broker_1__1y__full.md"
    assert "/" not in filename


def test_target_case_parser_and_scope_selection_are_exact():
    target = parse_target_case("alfy|broker.fiscal_lots|1Y|standard|broker=Directa")
    assert target == TargetProbeCase(
        user_alias="alfy",
        selection_id="broker.fiscal_lots",
        period_label="1Y",
        detail_level="standard",
        scope_selector="broker=Directa",
    )
    scope = select_target_scope(
        [
            {"domain": "broker", "scope_alias": "broker_anon_01", "selector_name": "directa"},
            {"domain": "broker", "scope_alias": "broker_anon_02", "selector_name": "Recrowd"},
        ],
        target,
        domain="broker",
    )
    assert scope["scope_alias"] == "broker_anon_01"


def test_target_case_parser_rejects_invalid_or_ambiguous_inputs():
    with pytest.raises(ProbeError, match="target-case"):
        parse_target_case("alfy|broker.fiscal_lots|1Y")
    target = TargetProbeCase("alfy", "broker.fiscal_lots", "1Y", "standard", "broker=Directa")
    with pytest.raises(ProbeError, match="resolved to 2 scopes"):
        select_target_scope(
            [
                {"domain": "broker", "scope_alias": "broker_anon_01", "selector_name": "Directa"},
                {"domain": "broker", "scope_alias": "broker_anon_02", "selector_name": "directa"},
            ],
            target,
            domain="broker",
        )


def test_target_case_representative_scope_supports_asset_and_fx_domains():
    scopes = [
        {"domain": "portfolio", "scope_alias": "all"},
        {"domain": "broker", "scope_alias": "broker_anon_01", "inventory": {"position_count": 3}},
        {"domain": "asset", "scope_alias": "asset_anon_01"},
        {"domain": "fx", "scope_alias": "fx_pair_anon_01"},
    ]

    asset = select_target_scope(
        scopes,
        TargetProbeCase("marco", "asset.market_analysis", "1Y", "standard", "representative"),
        domain="asset",
    )
    fx = select_target_scope(
        scopes,
        TargetProbeCase("marco", "fx.pair_analysis", "1Y", "standard", "representative"),
        domain="fx",
    )

    assert asset["scope_alias"] == "asset_anon_01"
    assert fx["scope_alias"] == "fx_pair_anon_01"


def test_targeted_pac_diagnostics_count_questions_and_drawdown_rows():
    prompt = """
Capital and cadence — REQUIRED WHEN MISSING: immediate capital; periodic amount.
Goals and horizon — REQUIRED WHEN MISSING: horizon; objective.
Risk preferences — OPTIONAL WHEN MATERIAL: high-risk cap; exclusions.
Operational constraints — REQUIRED WHEN MISSING AND MATERIAL: sales allowed; usable brokers.
COMPONENT portfolio.drawdown_summary
SUMMARY
|field|value|
|status|ok|
|current_drawdown_percent|-3%|
COMPONENT portfolio.asset_drawdown_snapshot
TABLE rows
|row|asset_ref|current_drawdown_percent|
|1|A1|-2%|
|2|A2|-4%|
"""
    diagnostics = measure_targeted_adequacy_diagnostics("portfolio.pac_planning", prompt)
    assert diagnostics["question_category_count"] == 4
    assert diagnostics["required_question_count"] == 6
    assert diagnostics["optional_question_count"] == 2
    assert diagnostics["portfolio_drawdown_rows"] == 2
    assert diagnostics["asset_drawdown_rows"] == 2


def test_broker_scope_diagnostics_distinguish_scope_positions_and_period_contributors():
    diagnostics = measure_broker_scope_diagnostics(
        {
            "entity_directory": {
                "brokers": [
                    {"broker_id": 5, "display_name": "First"},
                    {"broker_id": 7, "display_name": "Second"},
                ]
            },
            "sections": [
                {
                    "component_id": "portfolio.summary",
                    "payload": {"position_broker_count": 1},
                },
                {
                    "component_id": "portfolio.provenance",
                    "payload": {
                        "scoped_broker_count": 2,
                        "broker_scope": [5, 7],
                    },
                },
                {
                    "component_id": "portfolio.performance",
                    "payload": {"period_contributor_broker_count": 2},
                },
            ],
        }
    )

    assert diagnostics == {
        "broker_scope_refs": ["B1", "B2"],
        "scoped_broker_count": 2,
        "position_broker_count": 1,
        "period_contributor_broker_count": 2,
        "entity_directory_broker_count": 2,
        "scope_directory_consistent": True,
    }


def test_deterministic_asset_ranking_uses_history_observations_then_id():
    candidates = [
        AssetCandidate(9, "2020-01-01", "2026-01-01", 1000),
        AssetCandidate(8, "2020-01-01", "2026-01-01", 1200),
        AssetCandidate(7, "2020-01-01", "2026-01-01", 1200),
        AssetCandidate(1, "2025-06-01", "2026-01-01", 300),
        AssetCandidate(2, "2010-01-01", "2026-01-01", 5000, current_price_valid=False),
    ]

    assert [candidate.asset_id for candidate in rank_asset_candidates(candidates)] == [7, 8, 9]


def test_deterministic_fx_ranking_uses_history_observations_then_key():
    candidates = [
        FxCandidate("USD", "JPY", "2020-01-01", "2026-01-01", 1100),
        FxCandidate("EUR", "USD", "2020-01-01", "2026-01-01", 1200),
        FxCandidate("EUR", "GBP", "2020-01-01", "2026-01-01", 1200),
        FxCandidate("EUR", "CHF", "2025-06-01", "2026-01-01", 300),
    ]

    assert [candidate.canonical_key for candidate in rank_fx_candidates(candidates)] == ["EUR_GBP", "EUR_USD", "USD_JPY"]


def test_period_detail_matrix_adds_exact_custom_days_only_beyond_one_year():
    matrix = build_period_detail_matrix(custom_start="2024-01-01", snapshot_as_of="2026-01-01")

    assert len([item for item in matrix if not item["is_custom"]]) == 9
    custom = [item for item in matrix if item["is_custom"]]
    assert len(custom) == 3
    assert {item["period"]["customAmount"] for item in custom} == {731}
    assert {item["period"]["customUnit"] for item in custom} == {"days"}
    assert build_period_detail_matrix(periods=("Custom",), custom_start="2025-06-01", snapshot_as_of="2026-01-01") == []


def test_representative_profile_keeps_all_base_prompts_and_only_density_anchors():
    technical = {
        "kind": "dataset",
        "id": "portfolio.technical",
        "required_component_ids": ["portfolio.technical_indicators"],
        "optional_component_ids": [],
    }
    all_data = {
        "kind": "dataset",
        "id": "portfolio.all_data",
        "required_component_ids": ["portfolio.summary"],
        "optional_component_ids": [],
    }
    analysis = {
        "kind": "analysis",
        "id": "portfolio.pac_planning",
    }

    assert is_technical_dataset(technical) is True
    assert {(case["period_label"], case["detail_level"]) for case in representative_cases(technical)} == {
        ("3M", "standard"),
        ("6M", "standard"),
        ("1Y", "compact"),
        ("1Y", "standard"),
        ("1Y", "full"),
    }
    assert {(case["period_label"], case["detail_level"]) for case in representative_cases(all_data)} == {
        ("1Y", "standard"),
        ("1Y", "full"),
    }
    assert [(case["period_label"], case["detail_level"]) for case in representative_cases(analysis)] == [("1Y", "standard")]


def test_representative_catalog_profile_has_54_cases():
    selections = [
        *[
            {
                "kind": "dataset",
                "id": f"{domain}.technical",
                "required_component_ids": [f"{domain}.technical_indicators"],
                "optional_component_ids": [],
            }
            for domain in ("portfolio", "broker", "asset", "fx")
        ],
        *[
            {
                "kind": "dataset",
                "id": f"{domain}.all_data",
                "required_component_ids": [f"{domain}.technical_indicators"],
                "optional_component_ids": [],
            }
            for domain in ("portfolio", "broker", "asset", "fx")
        ],
        *[
            {
                "kind": "dataset",
                "id": f"dataset.{index}",
                "required_component_ids": ["summary"],
                "optional_component_ids": [],
            }
            for index in range(10)
        ],
        *[
            {
                "kind": "analysis",
                "id": f"analysis.{index}",
            }
            for index in range(16)
        ],
    ]

    assert sum(len(representative_cases(selection)) for selection in selections) == 54


def test_tuning_v2_excludes_only_all_data_and_builds_approved_matrices():
    catalog = {
        "datasets": [
            {
                "kind": "dataset",
                "id": "portfolio.overview",
                "domain": "portfolio",
                "period_semantics": "as_of",
            },
            {
                "kind": "dataset",
                "id": "portfolio.performance_flows",
                "domain": "portfolio",
                "period_semantics": "windowed",
            },
            {
                "kind": "dataset",
                "id": "portfolio.technical_summary",
                "domain": "portfolio",
                "period_semantics": "windowed",
            },
            {
                "kind": "dataset",
                "id": "portfolio.all_data",
                "domain": "portfolio",
                "period_semantics": "aggregated",
            },
        ]
    }
    exclusions = tuning_v2_exclusions(catalog)
    data_cases = tuning_v2_cases(
        {
            "kind": "dataset",
            "id": "portfolio.overview",
        },
        catalog,
    )
    temporal_analysis_cases = tuning_v2_cases(
        {
            "kind": "analysis",
            "id": "portfolio.performance_market_drivers",
            "required_dataset_ids": [
                "portfolio.performance_flows",
            ],
            "optional_dataset_ids": [],
        },
        catalog,
    )
    as_of_analysis_cases = tuning_v2_cases(
        {
            "kind": "analysis",
            "id": "portfolio.summary_only",
            "required_dataset_ids": ["portfolio.overview"],
            "optional_dataset_ids": [],
        },
        catalog,
    )

    assert exclusions == [
        {
            "dataset_id": "portfolio.all_data",
            "reason": "pure deduplicated composition already covered by domain base datasets",
            "composed_from": [
                "portfolio.overview",
                "portfolio.performance_flows",
            ],
            "excluded_semantic_projections": ["portfolio.technical_summary"],
        }
    ]
    assert len(data_cases) == 9
    assert {(case["period_label"], case["detail_level"]) for case in temporal_analysis_cases} == {(period, detail) for period in ("3M", "1Y") for detail in ("compact", "standard", "full")}
    assert [(case["period_label"], case["detail_level"]) for case in as_of_analysis_cases] == [("1Y", "standard")]


def test_public_catalog_v1_profile_is_exact_19_by_6_without_6m():
    selections = [
        {
            "kind": "dataset" if selection_id in PUBLIC_CATALOG_V1_DATASETS else "analysis",
            "id": selection_id,
            "domain": selection_id.partition(".")[0],
            "supported_detail_levels": ["compact", "standard", "full"],
        }
        for selection_id in reversed((*PUBLIC_CATALOG_V1_DATASETS, *PUBLIC_CATALOG_V1_ANALYSES))
    ]

    selected = public_catalog_v1_selections(selections)
    cases = [case for selection in selected for case in public_catalog_v1_cases(selection)]

    assert _parse_args(["--profile", PUBLIC_CATALOG_V1_PROFILE]).profile == PUBLIC_CATALOG_V1_PROFILE
    assert [selection["id"] for selection in selected] == [*PUBLIC_CATALOG_V1_DATASETS, *PUBLIC_CATALOG_V1_ANALYSES]
    assert len(selected) == 19
    assert len(cases) == PUBLIC_CATALOG_V1_EXPECTED_CASE_COUNT == 114
    assert {case["period_label"] for case in cases} == {"3M", "1Y"}
    assert {case["detail_level"] for case in cases} == {"compact", "standard", "full"}
    assert all(case["period_label"] != "6M" for case in cases)
    with pytest.raises(ProbeError, match="only 3M and 1Y"):
        public_catalog_v1_cases(selected[0], period_filter="6M")
    with pytest.raises(ProbeError, match="exact 114-case"):
        run_probe(_parse_args(["--profile", PUBLIC_CATALOG_V1_PROFILE, "--period", "3M"]))
    with pytest.raises(ProbeError, match="exactly one deterministic user"):
        run_probe(_parse_args(["--profile", PUBLIC_CATALOG_V1_PROFILE, "--user", "alfy", "--user", "marco"]))
    assert parse_target_case("marco|portfolio.pac_planning|6M|standard|all").period_label == "6M"


def test_public_catalog_v1_selection_fails_closed_and_filters_exactly():
    selections = [
        {
            "kind": "dataset" if selection_id in PUBLIC_CATALOG_V1_DATASETS else "analysis",
            "id": selection_id,
            "domain": selection_id.partition(".")[0],
        }
        for selection_id in (*PUBLIC_CATALOG_V1_DATASETS, *PUBLIC_CATALOG_V1_ANALYSES)
    ]
    selections.append({"kind": "dataset", "id": "portfolio.internal", "domain": "portfolio"})

    broker_analyses = public_catalog_v1_selections(selections, mode="analysis", domain="broker")

    assert [selection["id"] for selection in broker_analyses] == [
        "broker.review",
        "broker.performance_market_drivers",
        "broker.fiscal_lots",
    ]
    with pytest.raises(ProbeError, match="absent"):
        public_catalog_v1_selections(selections[:-2])


def test_representative_scopes_keep_dashboard_one_rich_broker_asset_and_fx():
    scopes = [
        {"domain": "portfolio", "scope_alias": "all", "inventory": {"position_count": 20}},
        {"domain": "portfolio", "scope_alias": "broker_anon_01", "inventory": {"position_count": 8}},
        {
            "domain": "broker",
            "scope_alias": "broker_anon_01",
            "inventory": {"position_count": 8},
            "custom_start": "2018-01-01",
        },
        {
            "domain": "broker",
            "scope_alias": "broker_anon_02",
            "inventory": {"position_count": 12},
            "custom_start": "2020-01-01",
        },
        {"domain": "asset", "scope_alias": "asset_anon_01"},
        {"domain": "fx", "scope_alias": "fx_pair_anon_01"},
    ]

    selected = representative_scopes(scopes)

    assert [(scope["domain"], scope["scope_alias"]) for scope in selected] == [
        ("portfolio", "all"),
        ("broker", "broker_anon_02"),
        ("asset", "asset_anon_01"),
        ("fx", "fx_pair_anon_01"),
    ]


def test_public_catalog_v1_scope_uses_broker_and_history_reasons_without_extra_cases():
    scopes = [
        {"domain": "portfolio", "scope_alias": "all", "inventory": {"position_count": 20}},
        {
            "domain": "broker",
            "scope_alias": "broker_anon_01",
            "custom_start": "2018-01-01",
            "inventory": {"position_count": 15, "recorded_cost_transaction_count": 99, "recorded_cost_transaction_count_1y": 0},
        },
        {
            "domain": "broker",
            "scope_alias": "broker_anon_02",
            "custom_start": "2020-01-01",
            "inventory": {"position_count": 8, "recorded_cost_transaction_count": 12, "recorded_cost_transaction_count_1y": 4},
        },
        {"domain": "asset", "scope_alias": "asset_anon_01"},
        {"domain": "fx", "scope_alias": "fx_pair_anon_01"},
    ]

    ordinary = public_catalog_v1_scope(scopes, {"id": "broker.review", "domain": "broker"})
    fx = public_catalog_v1_scope(scopes, {"id": "fx.pair_analysis", "domain": "fx"})

    assert ordinary is not None and ordinary["scope_alias"] == "broker_anon_01"
    assert fx is not None
    assert fx["profile_selection_reason"] == "longest_history_at_least_configured_minimum_then_observations_key"


def test_legacy_sampling_counterfactual_uses_backend_policy_source_of_truth():
    legacy = legacy_sampling_manifest(
        {
            "technical_sampling": {
                "detail_level": "full",
                "price_policy": {"bucket_count": 75},
                "indicator_policies": [
                    {
                        "signal_instance_id": "ema_200",
                        "signal_code": "EMA",
                        "temporal_class": "very_slow",
                        "bucket_count": 38,
                    }
                ],
            }
        }
    )

    assert legacy == {
        "price_policy": {
            "detail_level": "full",
            "p": 2,
            "m": 30,
            "k": 7,
            "bucket_count": 75,
        },
        "indicator_policies": [
            {
                "signal_instance_id": "ema_200",
                "signal_code": "EMA",
                "temporal_class": "very_slow",
                "detail_level": "full",
                "p": 2,
                "m": 9,
                "k": 14,
                "bucket_count": 38,
            }
        ],
    }


def test_save_reread_measurements_and_hash_match_renderer(tmp_path: Path):
    content = "# Prompt\n\nCaffè value\n"
    renderer_measurement = {
        "unicode_characters": len(content),
        "utf8_bytes": len(content.encode("utf-8")),
        "lines": content.count("\n") + 1,
        "words": 4,
    }

    measured = save_and_reread_prompt(tmp_path / "prompt.md", content, renderer_measurement)

    assert measured["chars"] == len(content)
    assert measured["bytes"] == len(content.encode("utf-8"))
    assert measured["matches_renderer_content"] is True
    assert measured["matches_renderer_characters"] is True
    assert measured["matches_renderer_bytes"] is True
    assert measured["matches_renderer_lines"] is True
    assert measured["matches_renderer_words"] is True
    assert measured["hash_matches_renderer"] is True


def test_canonical_component_measurements_and_dataset_attribution():
    catalog = {
        "datasets": [
            {
                "id": "portfolio.primary",
                "required_component_ids": ["portfolio.summary", "portfolio.shared"],
                "optional_component_ids": [],
            },
            {
                "id": "portfolio.secondary",
                "required_component_ids": ["portfolio.shared", "portfolio.performance"],
                "optional_component_ids": [],
            },
        ]
    }
    snapshot = {
        "dataset_manifest": [
            {"dataset_id": "portfolio.primary", "dataset_version": 1, "role": "required"},
            {"dataset_id": "portfolio.secondary", "dataset_version": 2, "role": "optional"},
        ],
        "sections": [
            {"component_id": "portfolio.summary", "component_version": 1, "payload": {"z": 2, "a": 1}},
            {"component_id": "portfolio.shared", "component_version": 1, "payload": {"ok": True}},
            {"component_id": "portfolio.performance", "component_version": 1, "payload": [1, 2]},
            {"component_id": "portfolio.unknown", "component_version": 1, "payload": None},
        ],
    }

    breakdown = measure_canonical_breakdown(snapshot, catalog)
    components = {item["component_id"]: item for item in breakdown["components"]}
    datasets = {item["dataset_id"]: item for item in breakdown["datasets"]}

    expected_summary = json.dumps(snapshot["sections"][0], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert components["portfolio.summary"]["canonical_chars"] == len(expected_summary)
    assert components["portfolio.summary"]["canonical_bytes"] == len(expected_summary.encode("utf-8"))
    assert components["portfolio.shared"]["dataset_ids"] == ["portfolio.primary", "portfolio.secondary"]
    assert components["portfolio.shared"]["attributed_dataset_id"] == "portfolio.primary"
    assert datasets["portfolio.primary"]["component_ids"] == ["portfolio.summary", "portfolio.shared"]
    assert datasets["portfolio.secondary"]["component_ids"] == ["portfolio.performance"]
    assert datasets["__unattributed__"]["component_ids"] == ["portfolio.unknown"]
    assert breakdown["attribution_policy"] == "first_manifest_dataset_declaring_component_v1"


def test_reconciled_breakdown_validation_accepts_exact_totals_and_rejects_mismatch():
    valid = {
        "prompt_measurement": {"unicode_characters": 20, "utf8_bytes": 21},
        "breakdown": {
            "reconciliation": {
                "unicode_characters_match": True,
                "utf8_bytes_match": True,
                "reconciled_unicode_characters": 20,
                "reconciled_utf8_bytes": 21,
            }
        },
    }
    validate_reconciled_breakdown(valid)

    invalid = json.loads(json.dumps(valid))
    invalid["breakdown"]["reconciliation"]["unicode_characters_match"] = False
    with pytest.raises(ProbeError, match="does not reconcile"):
        validate_reconciled_breakdown(invalid)


def test_prompt_composition_reuses_official_breakdown_and_reconciles():
    breakdown = {
        "sections": [
            {"id": "analysis_objective", "unicode_characters": 100},
            {"id": "snapshot_metadata", "unicode_characters": 50},
            {"id": "snapshot_data", "unicode_characters": 300},
        ],
        "separators": {"unicode_characters": 10},
        "snapshot_data_wrapper": {"unicode_characters": 100},
        "snapshot_data_components": [
            {"id": "portfolio.positions", "category": "holdings_allocation", "unicode_characters": 100},
            {"id": "portfolio.technical_indicators", "category": "technical_indicators", "unicode_characters": 80},
            {"id": "portfolio.technical_coverage", "category": "technical_coverage", "unicode_characters": 20},
        ],
    }

    composition = measure_prompt_composition(breakdown, 460)

    assert tuple(composition["components"]) == COMPOSITION_COMPONENTS
    assert composition["reconciles"] is True
    assert composition["components"]["financial"]["chars"] == 100
    assert composition["components"]["technical"]["chars"] == 80
    assert composition["components"]["coverage/provenance"]["chars"] == 170
    assert composition["components"]["instructions/contracts"]["chars"] == 110
    assert composition["components"]["coverage/provenance"]["dominant_source"] == "wrapper:snapshot_data"
    assert sum(component["percent"] for component in composition["components"].values()) == pytest.approx(100)


@pytest.mark.parametrize(
    ("metric", "expected_primary", "expected_tag"),
    [
        ({"selection_id": "portfolio.synthetic_financial", "domain": "portfolio", "status": "ok"}, "financial", "financial"),
        ({"selection_id": "portfolio.overview_and_history", "domain": "portfolio", "status": "ok"}, "financial_with_context", "financial_with_context"),
        ({"selection_id": "asset.market_analysis", "domain": "asset", "status": "ok"}, "explicit_technical", "explicit_technical"),
        ({"selection_id": "portfolio.fiscal_lots", "domain": "portfolio", "status": "ok"}, "fifo", "fifo"),
        ({"selection_id": "fx.pair_analysis", "domain": "fx", "status": "ok"}, "fx", "fx"),
        (
            {
                "selection_id": "fx.pair_analysis",
                "domain": "fx",
                "status": "ok",
                "technical_diagnostics": {"history_coverage": {"complete": False}},
            },
            "unavailable_partial",
            "fx",
        ),
    ],
)
def test_prompt_category_classes_have_one_primary_and_supporting_tags(metric, expected_primary, expected_tag):
    primary, tags = classify_prompt_category(metric)

    assert primary == expected_primary
    assert expected_tag in tags
    assert primary in tags


def test_manifest_validation_rejects_pmk_and_requires_interpretive_technical_fields():
    validate_manifest_checks(
        {
            "has_technical_sampling": True,
            "implementation_parameter_lines": 0,
            "has_detail_level": True,
            "has_price_bucket_count": False,
            "has_instance_bucket_count": True,
            "has_instance_temporal_class": True,
        },
        [{"category": "technical_indicators"}],
        "slim",
    )
    with pytest.raises(ProbeError, match="P/M/K"):
        validate_manifest_checks({"has_technical_sampling": True, "implementation_parameter_lines": 1}, [], "slim")
    with pytest.raises(ProbeError, match="detail_level"):
        validate_manifest_checks(
            {
                "implementation_parameter_lines": 0,
                "has_technical_sampling": True,
                "has_detail_level": False,
                "has_price_bucket_count": True,
            },
            [{"category": "technical_prices"}],
            "slim",
        )
    with pytest.raises(ProbeError, match="bucket_count"):
        validate_manifest_checks(
            {
                "implementation_parameter_lines": 0,
                "has_technical_sampling": True,
                "has_detail_level": True,
                "has_price_bucket_count": False,
            },
            [{"category": "technical_prices"}],
            "slim",
        )
    with pytest.raises(ProbeError, match="temporal_class"):
        validate_manifest_checks(
            {
                "implementation_parameter_lines": 0,
                "has_technical_sampling": True,
                "has_detail_level": True,
                "has_indicator_instances": True,
                "has_instance_bucket_count": True,
                "has_instance_temporal_class": False,
            },
            [{"category": "technical_indicators"}],
            "slim",
        )
    with pytest.raises(ProbeError, match="bucket_count"):
        validate_manifest_checks(
            {
                "implementation_parameter_lines": 0,
                "has_technical_sampling": True,
                "has_detail_level": True,
                "has_indicator_instances": True,
                "has_instance_bucket_count": False,
                "has_instance_temporal_class": True,
            },
            [{"category": "technical_indicators"}],
            "slim",
        )
    validate_manifest_checks(
        {
            "implementation_parameter_lines": 0,
            "has_technical_sampling": True,
            "has_detail_level": True,
            "has_indicator_instances": False,
            "has_instance_bucket_count": False,
            "has_instance_temporal_class": False,
        },
        [{"category": "technical_indicators"}, {"category": "technical_coverage"}],
        "slim",
    )
    validate_manifest_checks({"has_technical_sampling": True, "implementation_parameter_lines": 3}, [{"category": "technical_indicators"}], "legacy")
    with pytest.raises(ProbeError, match="Legacy manifest expectation"):
        validate_manifest_checks({"has_technical_sampling": True, "implementation_parameter_lines": 0}, [{"category": "technical_indicators"}], "legacy")
    validate_manifest_checks({"has_technical_sampling": False, "implementation_parameter_lines": 0}, [{"category": "technical_indicators"}], "legacy")


def test_secret_scan_ignores_generic_words_but_finds_real_credentials_and_tokens():
    assert scan_text_for_secrets("Password policy and cookie preferences are documented.") == []
    assert scan_text_for_secrets("The real value is S3cretValue!", ["S3cretValue!"]) == ["actual_password"]
    assert "authorization_header" in scan_text_for_secrets("Authorization: Bearer abcdefghijklmnopqrstuvwxyz")
    assert "jwt" in scan_text_for_secrets("eyJabcdefgh.abcdefghijk.abcdefghijkl")
    assert "access_token" in scan_text_for_secrets('access_token="abcdefghijklmnop"')
    assert "session_cookie" in scan_text_for_secrets("Set-Cookie: session=abcdefghijklmnop")


def test_run_comparison_reports_all_statuses_and_regression_rule():
    previous = {
        "entries": [
            _metric("portfolio.unchanged", chars=100),
            _metric("portfolio.changed", chars=100, datasets=["a"]),
            _metric("portfolio.removed", chars=50),
            _metric("portfolio.recovered", status="failed", chars=0),
            _metric("portfolio.failed", chars=90),
        ]
    }
    current = {
        "entries": [
            _metric("portfolio.unchanged", chars=100),
            _metric("portfolio.changed", chars=120, datasets=["b"]),
            _metric("portfolio.added", chars=200),
            _metric("portfolio.recovered", chars=80),
            _metric("portfolio.failed", status="failed", chars=0),
        ]
    }

    rows = {row["stable_key"].split("|")[3]: row for row in compare_metric_runs(current, previous)}

    assert rows["portfolio.unchanged"]["status"] == "unchanged"
    assert rows["portfolio.changed"]["status"] == "changed"
    assert rows["portfolio.changed"]["absolute_delta"] == 20
    assert rows["portfolio.changed"]["regression"] is True
    assert rows["portfolio.changed"]["previous_category"] == "light"
    assert rows["portfolio.changed"]["current_category"] == "light"
    assert rows["portfolio.changed"]["reason_for_change"] == ["semantic_composition_changed"]
    assert rows["portfolio.added"]["status"] == "added"
    assert rows["portfolio.added"]["regression"] is False
    assert rows["portfolio.removed"]["status"] == "removed"
    assert rows["portfolio.recovered"]["status"] == "recovered"
    assert rows["portfolio.failed"]["status"] == "failed"

    targeted_rows = {
        row["stable_key"].split("|")[3]: row
        for row in compare_metric_runs(
            current,
            previous,
            include_removed=False,
        )
    }
    assert "portfolio.removed" not in targeted_rows
    assert set(targeted_rows) == {
        "portfolio.unchanged",
        "portfolio.changed",
        "portfolio.added",
        "portfolio.recovered",
        "portfolio.failed",
    }


def test_run_comparison_reports_prompt_hash_changes_without_failing_functional_status():
    previous = _metric("portfolio.same_metrics")
    current = _metric("portfolio.same_metrics")
    previous["rendered_prompt_sha256"] = "a" * 64
    current["rendered_prompt_sha256"] = "b" * 64

    [row] = compare_metric_runs({"entries": [current]}, {"entries": [previous]})

    assert row["status"] == "unchanged"
    assert row["comparison_basis"] == "functional_metrics_v1"
    assert row["prompt_content_changed"] is True
    assert row["regression"] is False


def test_run_comparison_reports_signal_history_event_and_coverage_deltas():
    previous_metric = _metric("portfolio.rebalancing", chars=100)
    previous_metric["signal_breakdown"] = [
        {
            "signal_code": "EMA",
            "instance_count": 3,
            "history_row_count": 300,
            "history_chars": 3000,
            "event_count": 0,
            "event_chars": 0,
            "definition_chars": 100,
            "summary_chars": 200,
        }
    ]
    previous_metric["technical_diagnostics"] = {"eligible_asset_count": 17, "covered_asset_count": 12}
    current_metric = _metric("portfolio.rebalancing", chars=80)
    current_metric["signal_breakdown"] = []
    current_metric["technical_diagnostics"] = {"eligible_asset_count": 17, "covered_asset_count": 12}

    summary = signal_metric_summary(previous_metric)
    comparison = compare_metric_runs({"entries": [current_metric]}, {"entries": [previous_metric]})[0]

    assert summary["signal_codes"] == ["EMA"]
    assert summary["history_row_count"] == 300
    assert comparison["signal_instance_delta"] == -3
    assert comparison["history_row_delta"] == -300
    assert comparison["event_delta"] == 0
    assert comparison["eligible_entity_delta"] == 0
    assert comparison["covered_entity_delta"] == 0
    assert "signal_composition_changed" in comparison["reason_for_change"]
    assert "history_depth_changed" in comparison["reason_for_change"]


def test_run_comparison_backward_normalizes_legacy_considered_leg_count():
    # An OLD metrics file still labels period legs as `considered_asset_count`.
    # Comparing a NEW run (period_position_leg_count) against it must treat an
    # equal leg count as unchanged instead of spuriously flagging a coverage
    # change, so stable cross-run comparisons are preserved.
    previous_metric = _metric("portfolio.rebalancing", chars=100)
    previous_metric["technical_diagnostics"] = {"considered_asset_count": 20, "eligible_asset_count": 17, "covered_asset_count": 12}
    current_metric = _metric("portfolio.rebalancing", chars=100)
    current_metric["technical_diagnostics"] = {
        "period_position_leg_count": 20,
        "period_contributor_asset_count": 18,
        "eligible_asset_count": 17,
        "covered_asset_count": 12,
    }

    unchanged_reasons = metric_change_reasons(current_metric, previous_metric)
    assert "technical_coverage_changed" not in unchanged_reasons

    changed_metric = _metric("portfolio.rebalancing", chars=100)
    changed_metric["technical_diagnostics"] = {
        "period_position_leg_count": 21,
        "period_contributor_asset_count": 18,
        "eligible_asset_count": 17,
        "covered_asset_count": 12,
    }
    changed_reasons = metric_change_reasons(changed_metric, previous_metric)
    assert "technical_coverage_changed" in changed_reasons


def test_http_failure_classification_and_fx_continuation():
    skipped = classify_http_failure(
        422,
        {"detail": {"code": "selection_not_applicable", "message": "No position"}},
        "asset",
    )
    fx_failure = classify_http_failure(
        503,
        {"detail": {"code": "snapshot_source_failure", "message": "FX unavailable", "retryable": True, "reason_code": "fx_no_usable_rate"}},
        "fx",
    )

    assert skipped["status"] == "skipped"
    assert skipped["nonfatal"] is True
    assert fx_failure["status"] == "failed"
    assert fx_failure["retryable"] is True
    assert fx_failure["source_reason_code"] == "fx_no_usable_rate"
    assert fx_failure["nonfatal"] is True
    assert should_continue_after_failure("fx", 503) is True
    assert should_continue_after_failure("portfolio", 500) is True


def test_ui_representable_asset_and_fx_scopes_do_not_add_hidden_broker_filters():
    user_data = {
        "snapshot_as_of": "2026-01-01",
        "target_currency": "EUR",
        "brokers": [{"id": 3}, {"id": 7}],
        "broker_histories": {3: ("2024-01-01", "2026-01-01"), 7: ("2025-01-01", "2026-01-01")},
        "scope_inventories": {
            "all": {"scoped_broker_count": 2},
            3: {"scoped_broker_count": 1},
            7: {"scoped_broker_count": 1},
        },
        "portfolio_custom_start": "2024-01-01",
        "inventory": {"earliest_price": "2010-01-01"},
        "asset": AssetCandidate(11, "2010-01-01", "2026-01-01", 4000, broker_ids=(3, 7)),
        "fx": FxCandidate("EUR", "USD", "2020-01-01", "2026-01-01", 1500),
    }

    scopes = build_user_scopes(user_data)
    portfolio = next(scope for scope in scopes if scope["domain"] == "portfolio" and scope["scope_alias"] == "all")
    asset = next(scope for scope in scopes if scope["domain"] == "asset")
    fx = next(scope for scope in scopes if scope["domain"] == "fx")

    assert portfolio["custom_start"] == "2024-01-01"
    assert asset["context"] == {
        "domain": "asset",
        "snapshotAsOf": "2026-01-01",
        "targetCurrency": "EUR",
        "assetId": 11,
    }
    assert fx["context"] == {
        "domain": "fx",
        "snapshotAsOf": "2026-01-01",
        "targetCurrency": "EUR",
        "baseCurrency": "EUR",
        "quoteCurrency": "USD",
    }


def test_technical_diagnostics_count_runtime_payload_without_values():
    snapshot = {
        "sections": [
            {
                "component_id": "portfolio.technical_indicators",
                "payload": {
                    "assets": [
                        {"asset_id": 1, "indicators": [{"instance_id": "ema_20"}, {"instance_id": "rsi_14"}]},
                        {"asset_id": 2, "indicators": [{"instance_id": "ema_20"}]},
                    ]
                },
            },
            {
                "component_id": "portfolio.technical_events",
                "payload": {"detected_event_count": 12, "exported_event_count": 8},
            },
            {
                "component_id": "portfolio.technical_breadth",
                "payload": {
                    "period_position_leg_count": 4,
                    "period_contributor_asset_count": 3,
                    "eligible_asset_count": 2,
                    "covered_asset_count": 2,
                    "eligible_portfolio_weight_ratio": 1.0,
                    "covered_portfolio_weight_ratio": 0.75,
                    "covered_weight_ratio": 0.75,
                },
            },
        ]
    }

    assert measure_technical_diagnostics(snapshot) == {
        "price_bucket_rows": 0,
        "indicator_asset_count": 2,
        "indicator_instance_count": 3,
        "detected_event_count": 12,
        "exported_event_count": 8,
        "detailed_event_rows": 0,
        "period_position_leg_count": 4,
        "period_contributor_asset_count": 3,
        "selected_entity_count": None,
        "eligible_asset_count": 2,
        "covered_asset_count": 2,
        "eligible_portfolio_weight_ratio": 1.0,
        "covered_portfolio_weight_ratio": 0.75,
        "covered_weight_ratio": 0.75,
        "context_history_rows": 0,
        "context_event_count": 0,
        "context_event_rows": 0,
        "latest_event_rows": 0,
        "latest_event_category_count": 0,
        "event_digest_group_count": 0,
        "event_digest_underlying_event_count": 0,
        "signal_ok_count": 0,
        "signal_partial_count": 0,
        "signal_unavailable_count": 0,
        "signal_failed_count": 0,
        "history_coverage": None,
    }


def test_technical_diagnostics_include_context_signal_and_fx_history_coverage():
    history_coverage = {
        "requested_period": {"start": "2025-01-01", "end": "2025-12-31"},
        "available_period": {"start": "2025-10-01", "end": "2025-12-31"},
        "requested_calendar_days": 365,
        "covered_calendar_days": 92,
        "coverage_ratio": 92 / 365,
        "complete": False,
        "reason_code": "insufficient_source_history",
        "observed_count": 65,
        "backward_filled_count": 27,
        "earliest_source_date": "2025-10-01",
    }
    snapshot = {
        "meta": {"history_coverage": history_coverage},
        "sections": [
            {
                "component_id": "fx.technical_coverage",
                "payload": {
                    "selected_entity_count": 1,
                    "eligible_entity_count": 1,
                    "covered_entity_count": 1,
                    "signals": [
                        {"ok_count": 5, "partial_count": 2, "unavailable_count": 4, "failed_count": 1},
                    ],
                },
            },
            {
                "component_id": "fx.market_summary",
                "payload": {"history": [{}, {}, {}, {}], "events": [{}, {}]},
            },
        ],
    }

    diagnostics = measure_technical_diagnostics(snapshot)

    assert diagnostics is not None
    assert diagnostics["history_coverage"] == history_coverage
    assert diagnostics["selected_entity_count"] == 1
    assert diagnostics["period_position_leg_count"] is None
    assert diagnostics["eligible_asset_count"] == 1
    assert diagnostics["covered_asset_count"] == 1
    assert diagnostics["signal_ok_count"] == 5
    assert diagnostics["signal_partial_count"] == 2
    assert diagnostics["signal_unavailable_count"] == 4
    assert diagnostics["signal_failed_count"] == 1
    assert diagnostics["context_history_rows"] == 4
    assert diagnostics["context_event_count"] == 2
    assert diagnostics["context_event_rows"] == 2
    assert diagnostics["latest_event_rows"] == 0
    assert diagnostics["latest_event_category_count"] == 0


def test_technical_diagnostics_split_detailed_context_latest_and_digest_event_rows():
    snapshot = {
        "sections": [
            {
                "component_id": "portfolio.technical_events",
                "component_version": 2,
                "payload": {
                    "detected_event_count": 40,
                    "exported_event_count": 6,
                    "buckets": [
                        {"event_count": 4, "events": [{}, {}, {}, {}]},
                        {"event_count": 2, "events": [{}, {}]},
                    ],
                },
            },
            {
                "component_id": "portfolio.asset_market_context",
                "component_version": 1,
                "payload": {
                    "entities": [{"entity_id": "asset:1"}],
                    "latest_events": [
                        {"entity_id": "asset:1", "signal_code": "EMA", "signal_category": "trend"},
                        {"entity_id": "asset:1", "signal_code": "RSI", "signal_category": "momentum"},
                        {"entity_id": "asset:2", "signal_code": "EMA", "signal_category": "trend"},
                    ],
                },
            },
            {
                "component_id": "portfolio.context_events",
                "component_version": 1,
                "payload": {"detected_event_count": 20, "exported_event_count": 5, "events": [{}] * 5},
            },
            {
                "component_id": "portfolio.event_digest",
                "component_version": 1,
                "payload": {
                    "detected_event_count": 40,
                    "included_event_count": 9,
                    "rows": [
                        {"signal_code": "EMA", "signal_category": "trend", "key": "ema_50_ema_200", "event_count": 4},
                        {"signal_code": "RSI", "signal_category": "momentum", "key": "rsi_14_oversold_30", "event_count": 5},
                    ],
                },
            },
        ]
    }

    diagnostics = measure_technical_diagnostics(snapshot)

    assert diagnostics is not None
    # Full technical rendered event rows are counted separately from the exported total.
    assert diagnostics["detailed_event_rows"] == 6
    assert diagnostics["exported_event_count"] == 6
    # Market-context detailed events plus dedicated context_events rows (never latest_events).
    assert diagnostics["context_event_rows"] == 5
    assert diagnostics["context_event_count"] == 5
    # Latest-per-category rows and the distinct set of categories present in the prompt.
    assert diagnostics["latest_event_rows"] == 3
    assert diagnostics["latest_event_category_count"] == 2
    # Digest group count and underlying reconcile to the digest's own included_event_count.
    assert diagnostics["event_digest_group_count"] == 2
    assert diagnostics["event_digest_underlying_event_count"] == 9
    included = snapshot["sections"][3]["payload"]["included_event_count"]
    assert diagnostics["event_digest_underlying_event_count"] == included


def test_prompt_size_categories_use_approved_thresholds():
    assert prompt_size_category(10_000) == "light"
    assert prompt_size_category(10_000.25) == "medium"
    assert prompt_size_category(50_000) == "medium"
    assert prompt_size_category(50_000.25) == "heavy"


def test_public_table_audit_detects_empty_parent_and_percentage_violations():
    audit = audit_public_tables(
        "\n".join(
            [
                "|row|flow|flow.amount|flow.code|weight_percent|",
                "|1|null|10|EUR|17.04|",
                "|2|null|20|EUR|82.96%|",
            ]
        )
    )

    assert audit["table_count"] == 1
    assert audit["empty_column_count"] == 1
    assert audit["empty_parent_columns"] == ["flow"]
    assert audit["percent_violation_count"] == 1


def test_public_table_audit_detects_double_scaled_summary_percentages():
    audit = audit_public_tables(
        "\n".join(
            [
                "|field|value|",
                "|broker_largest_position_weight_percent|1502%|",
                "|portfolio_largest_position_weight_percent|11.74%|",
                "|largest_position_weight_delta_percent|3.28%|",
            ]
        )
    )

    assert audit["percent_violation_count"] == 1
    assert audit["percent_violations"] == ["broker_largest_position_weight_percent=1502%"]


def test_public_semantics_audit_reconciles_hhi_weights_fifo_and_unit_price():
    snapshot = {
        "sections": [
            {
                "component_id": "broker.allocation_concentration",
                "payload": {"herfindahl_index_points": "944.2335"},
            },
            {
                "component_id": "portfolio.positions",
                "payload": {
                    "positions": [
                        {
                            "quantity": "10",
                            "current_value": {"amount": "100", "code": "EUR"},
                            "unit_price": {"amount": "10", "code": "EUR"},
                        }
                    ]
                },
            },
            {
                "component_id": "portfolio.technical_indicators",
                "payload": {
                    "eligible_asset_count": 2,
                    "period_position_leg_count": 2,
                    "period_contributor_asset_count": 2,
                    "covered_asset_count": 2,
                    "eligible_portfolio_weight_ratio": 1.0,
                    "covered_portfolio_weight_ratio": 1.0,
                    "covered_weight_ratio": 1.0,
                    "assets": [
                        {
                            "portfolio_weight_ratio": 0.75,
                            "indicators": [
                                {
                                    "instance_id": "rsi_14",
                                    "portfolio_weight_ratio": 0.75,
                                    "technical_normalized_weight_ratio": 0.75,
                                }
                            ],
                        },
                        {
                            "portfolio_weight_ratio": 0.25,
                            "indicators": [
                                {
                                    "instance_id": "rsi_14",
                                    "portfolio_weight_ratio": 0.25,
                                    "technical_normalized_weight_ratio": 0.25,
                                }
                            ],
                        },
                    ],
                },
            },
            {
                "component_id": "portfolio.technical_breadth",
                "payload": {
                    "eligible_asset_count": 2,
                    "period_position_leg_count": 2,
                    "period_contributor_asset_count": 2,
                    "covered_asset_count": 2,
                    "eligible_portfolio_weight_ratio": 1.0,
                    "covered_portfolio_weight_ratio": 1.0,
                    "covered_weight_ratio": 1.0,
                    "states": [
                        {
                            "signal_code": "RSI",
                            "output_key": "rsi",
                            "state": "low",
                            "covered_asset_count": 2,
                            "covered_portfolio_weight_ratio": 1.0,
                            "unweighted_ratio": 0.5,
                            "technical_normalized_weight_ratio": 0.75,
                        },
                        {
                            "signal_code": "RSI",
                            "output_key": "rsi",
                            "state": "high",
                            "covered_asset_count": 2,
                            "covered_portfolio_weight_ratio": 1.0,
                            "unweighted_ratio": 0.5,
                            "technical_normalized_weight_ratio": 0.25,
                        },
                    ],
                },
            },
            {
                "component_id": "portfolio.fifo_lots",
                "payload": {
                    "lots": [
                        {
                            "lot_ref": "L1",
                            "asset_id": 1,
                            "opening_broker_id": 2,
                            "original_quantity": "10",
                            "current_custody": [
                                {
                                    "broker_id": None,
                                    "custody_type": "IN_TRANSIT",
                                    "quantity": "2",
                                }
                            ],
                        },
                        {
                            "lot_ref": "L2",
                            "asset_id": 1,
                            "opening_broker_id": 2,
                            "original_quantity": "10",
                            "current_custody": [
                                {
                                    "broker_id": None,
                                    "custody_type": "IN_TRANSIT",
                                    "quantity": "2",
                                }
                            ],
                        },
                    ]
                },
            },
        ]
    }
    prompt = "\n".join(
        [
            "|field|value|",
            "|herfindahl_index_points|944.2335|",
            "|portfolio_weight_percent|technical_normalized_weight_percent|",
            "|75%|75%|",
            "|25%|25%|",
            "TABLE broker_scope",
            "|row|value|",
            "|1|B1|",
        ]
    )
    render_result = {
        "breakdown": {
            "format_diagnostics": {
                "floating_point_noise_normalized": 2,
                "empty_columns_removed": 3,
                "empty_temporal_rows_detected": 5,
                "empty_temporal_rows_omitted": 5,
                "temporal_rows_rendered": 7,
            }
        }
    }

    audit = audit_snapshot_semantics(snapshot, prompt, render_result)

    assert audit["violations"] == []
    assert audit["hhi"]["checks"] == 1
    assert audit["weights"]["violations"] == 0
    assert audit["unit_price"]["checks"] == 1
    assert audit["fifo"]["local_refs"] == 2
    assert audit["fifo"]["economic_duplicate_groups"] == 1
    assert audit["fifo"]["in_transit_rows"] == 2
    assert audit["format_diagnostics"]["empty_temporal_rows_detected"] == 5
    assert audit["format_diagnostics"]["empty_temporal_rows_omitted"] == 5
    assert audit["format_diagnostics"]["temporal_rows_rendered"] == 7

    raw_scope_audit = audit_snapshot_semantics(snapshot, prompt.replace("|1|B1|", "|1|5|"), render_result)
    assert "forbidden public prompt pattern raw_scope_numeric_value: 1" in raw_scope_audit["violations"]


def test_nearest_rank_distribution_and_nearest_key_are_deterministic():
    values = list(range(1, 11))
    stats = numeric_distribution_stats(values)
    tie_a = _public_metric("portfolio.pac_planning", "3M", "compact", 90, index=1)
    tie_b = _public_metric("portfolio.pac_planning", "3M", "full", 110, index=2)

    assert nearest_rank_percentile(values, 10) == 1
    assert nearest_rank_percentile(values, 25) == 3
    assert nearest_rank_percentile(values, 50) == 5
    assert nearest_rank_percentile(values, 99) == 10
    assert stats == {
        "count": 10,
        "minimum": 1.0,
        "maximum": 10.0,
        "mean": 5.5,
        "median": 5.5,
        "p10": 1.0,
        "p25": 3.0,
        "p75": 8.0,
        "p90": 9.0,
        "p95": 10.0,
        "p99": 10.0,
        "iqr": 5.0,
        "population_stdev": pytest.approx(2.8722813232690143),
    }
    selected = nearest_metric_entry([tie_b, tie_a], 100)
    assert selected is not None
    assert stable_metric_key_text(selected) == min(stable_metric_key_text(tie_a), stable_metric_key_text(tie_b))
    with pytest.raises(ValueError, match="between 0 and 100"):
        nearest_rank_percentile(values, 101)


def test_named_and_global_retention_deduplicates_by_stable_key():
    entries = [_public_metric(selection_id, period, detail, 1_000 + index * 100, index=index) for index, (selection_id, period, detail) in enumerate(NAMED_PROMPT_RETENTION, start=1)]
    entries.extend(_public_metric("portfolio.pac_planning", "1Y", detail, 10_000 + index * 250, index=100 + index) for index, detail in enumerate(("compact", "full"), start=1))

    reasons = select_prompt_retention_reasons(entries)

    for entry in entries[: len(NAMED_PROMPT_RETENTION)]:
        key = stable_metric_key_text(entry)
        assert set(NAMED_PROMPT_RETENTION[(entry["selection_id"], entry["period_label"], entry["detail_level"])]) <= set(reasons[key])
    assert sum(reason.startswith("global_") for selected_reasons in reasons.values() for reason in selected_reasons) == 9
    assert all(len(selected_reasons) == len(set(selected_reasons)) for selected_reasons in reasons.values())


def test_selective_retention_promotes_only_selected_and_manifest_is_complete(tmp_path: Path):
    entries = [_public_metric("portfolio.pac_planning", "3M", "standard" if index == 0 else "compact", 1_000 + index * 73, index=index) for index in range(20)]
    staged: dict[str, Path] = {}
    for entry in entries:
        path = tmp_path / ".prompt_staging" / f"{entry['scope_alias']}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"prompt {entry['scope_alias']}", encoding="utf-8")
        staged[stable_metric_key_text(entry)] = path

    reasons = finalize_public_catalog_prompt_retention(
        entries,
        staged,
        artifact_root=tmp_path,
        prompts_dir=tmp_path / "prompts",
        allow_retention=True,
    )
    manifest = build_retained_prompt_manifest(entries, run_id="run", retention_reasons=reasons)

    retained = [entry for entry in entries if entry["retained"] is True]
    dropped = [entry for entry in entries if entry["retained"] is False]
    assert retained
    assert dropped
    assert all(entry["prompt_file"] is not None for entry in retained)
    assert all(entry["prompt_file"] is None for entry in dropped)
    assert manifest["retained_count"] == len(retained)
    assert manifest["planned_retention_count"] == len(reasons)
    assert set(manifest["entries"][0]) >= {"stable_key", "prompt_path", "reasons", "chars", "bytes", "sha256", "category"}


def test_dimension_summary_classifies_and_selects_representatives():
    entries = []
    for index, token_equivalent in enumerate((1_000, 10_000, 10_001, 50_000, 50_001, 100_001), start=1):
        entries.append(
            {
                "status": "ok",
                "mode": "data" if index <= 3 else "analysis",
                "domain": "portfolio",
                "selection_id": f"selection.{index}",
                "period_label": "3M",
                "detail_level": "compact",
                "rendered_prompt_chars": token_equivalent * 4,
                "rendered_prompt_estimated_token_equivalent": token_equivalent,
                "size_category": prompt_size_category(token_equivalent),
                "very_heavy": token_equivalent > 100_000,
                "largest_section_id": "snapshot_data",
                "technical_percentage": 50.0,
            }
        )

    summary = build_dimension_summary(entries)

    assert summary["overall"]["light"] == 2
    assert summary["overall"]["medium"] == 2
    assert summary["overall"]["heavy"] == 2
    assert summary["overall"]["very_heavy"] == 1
    assert summary["overall"]["mean"] == pytest.approx(36_833.833333333336)
    assert summary["overall"]["p10"] == 1_000
    assert summary["overall"]["p25"] == 10_000
    assert summary["overall"]["p75"] == 50_001
    assert summary["overall"]["p99"] == 100_001
    assert summary["overall"]["iqr"] == 40_001
    assert summary["overall"]["population_stdev"] > 0
    assert summary["overall"]["rendered_characters"]["maximum"] == 400_004
    assert summary["by_type"]["None"]["count"] == 6
    assert summary["by_category"]["None"]["count"] == 6
    assert summary["representatives"]["heavy"]["smallest"]["selection_id"] == "selection.5"
    assert summary["representatives"]["heavy"]["largest"]["selection_id"] == "selection.6"


def test_change_reasons_are_derived_from_public_format_diagnostics():
    reasons = metric_change_reasons(
        {
            "public_output_checks": {
                "format_diagnostics": {
                    "floating_point_noise_normalized": 1,
                    "normalized_ratio_percent_values": 2,
                    "empty_columns_removed": 3,
                    "empty_temporal_rows_omitted": 4,
                },
                "fifo": {"local_refs": 4},
                "weights": {"checks": 5},
                "hhi": {"checks": 1},
            }
        }
    )

    assert reasons == [
        "numeric_formatting",
        "percentage_correction",
        "empty_column_removal",
        "empty_temporal_row_removal",
        "fifo_lot_reference",
        "breadth_weight_clarification",
        "hhi_semantic_correction",
    ]


def test_secret_scan_ignores_redacted_authorization_placeholder():
    assert scan_text_for_secrets("Authorization: [REDACTED]") == []


def test_svg_charts_are_deterministic_and_comparison_chart_is_conditional():
    entries = [
        {
            **_public_metric("portfolio.overview_and_history", "3M", "compact", 1_000, index=1),
            "category": "financial_with_context",
            "composition": {
                "total_chars": 1_000,
                "components": {
                    "financial": {"chars": 500, "percent": 50, "dominant_source": "component:a", "dominant_source_chars": 500},
                    "technical": {"chars": 200, "percent": 20, "dominant_source": "component:b", "dominant_source_chars": 200},
                    "coverage/provenance": {"chars": 200, "percent": 20, "dominant_source": "section:snapshot_metadata", "dominant_source_chars": 200},
                    "instructions/contracts": {"chars": 100, "percent": 10, "dominant_source": "separators", "dominant_source_chars": 100},
                },
            },
        },
        {
            **_public_metric("asset.market_analysis", "1Y", "full", 2_000, index=2),
            "category": "explicit_technical",
            "composition": {
                "total_chars": 2_000,
                "components": {
                    "financial": {"chars": 400, "percent": 20, "dominant_source": "component:a", "dominant_source_chars": 400},
                    "technical": {"chars": 1_000, "percent": 50, "dominant_source": "component:b", "dominant_source_chars": 1_000},
                    "coverage/provenance": {"chars": 200, "percent": 10, "dominant_source": "section:snapshot_metadata", "dominant_source_chars": 200},
                    "instructions/contracts": {"chars": 400, "percent": 20, "dominant_source": "section:response_contract", "dominant_source_chars": 400},
                },
            },
        },
    ]
    comparisons = [
        {
            "stable_key": stable_metric_key_text(entries[0]),
            "previous_chars": 900,
            "current_chars": 1_000,
        }
    ]

    without_comparison = build_probe_svgs(entries, [])
    first = build_probe_svgs(entries, comparisons)
    second = build_probe_svgs(entries, comparisons)

    assert set(without_comparison) == {"category_range_box.svg", "period_detail.svg", "composition_share.svg"}
    assert set(first) == {*without_comparison, "before_after.svg"}
    assert first == second
    assert all(content.startswith("<svg") and content.endswith("</svg>\n") for content in first.values())
    assert "financial_with_context" in first["category_range_box.svg"]
    assert "coverage/provenance" in first["composition_share.svg"]


def test_manual_review_and_comparison_manifests_are_structured_without_ratings(tmp_path: Path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"entries":[]}\n', encoding="utf-8")

    task_reviews = build_manual_review_placeholder("run", "task_adequacy")
    export_reviews = build_manual_review_placeholder("run", "export_data")
    absent = build_comparison_baseline_manifest("run", None, [])
    compared = build_comparison_baseline_manifest("run", baseline, [{"status": "unchanged"}])

    assert task_reviews == {
        "schema_version": 1,
        "run_id": "run",
        "review_kind": "task_adequacy",
        "status": "not_performed",
        "reviews": [],
    }
    assert export_reviews["reviews"] == []
    assert "ratings" not in task_reviews
    assert absent["status"] == "not_provided"
    assert absent["baseline_metrics_path"] is None
    assert compared["status"] == "compared"
    assert compared["baseline_sha256"] == hash_file(baseline)
    assert compared["comparison_row_count"] == 1


def test_sqlite_backup_preserves_source_hash_and_creates_independent_copy(tmp_path: Path):
    source = tmp_path / "source.db"
    destination = tmp_path / "runtime" / "sqlite" / "app.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES ('original')")
    before = hash_sqlite_family(source)

    sqlite_backup(source, destination)

    after = hash_sqlite_family(source)
    assert before == after
    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "original"
        connection.execute("INSERT INTO sample(value) VALUES ('copy-only')")
    with sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sample").fetchone()[0] == 1


def test_frozen_source_snapshot_can_feed_an_independent_runtime_copy(tmp_path: Path):
    production = tmp_path / "production.db"
    source_snapshot = tmp_path / "source_snapshot" / "sqlite" / "app.db"
    runtime = tmp_path / "runtime" / "sqlite" / "app.db"
    with sqlite3.connect(production) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES ('frozen')")

    sqlite_backup(production, source_snapshot)
    source_before = hash_sqlite_family(source_snapshot)
    sqlite_backup(source_snapshot, runtime)
    with sqlite3.connect(runtime) as connection:
        connection.execute("INSERT INTO sample(value) VALUES ('runtime-only')")

    assert hash_sqlite_family(source_snapshot) == source_before
    with sqlite3.connect(f"file:{source_snapshot.resolve()}?mode=ro&immutable=1", uri=True) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sample").fetchone()[0] == 1


def test_sqlite_primary_hash_ignores_ephemeral_sidecar_lifecycle():
    primary = {
        "app.db": {"exists": True, "size": 10, "sha256": "same"},
        "app.db-wal": {"exists": True, "size": 0, "sha256": "empty"},
    }
    without_sidecar = {
        "app.db": {"exists": True, "size": 10, "sha256": "same"},
        "app.db-wal": {"exists": False, "size": None, "sha256": None},
    }
    changed_primary = {
        "app.db": {"exists": True, "size": 10, "sha256": "changed"},
    }

    assert sqlite_primary_unchanged(primary, without_sidecar) is True
    assert sqlite_primary_unchanged(primary, changed_primary) is False


def test_copy_only_credential_normalization_never_changes_source(tmp_path: Path):
    source = tmp_path / "source.db"
    destination = tmp_path / "runtime" / "sqlite" / "app.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE users (username TEXT PRIMARY KEY, hashed_password TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO users(username, hashed_password) VALUES (?, ?)",
            ("probe_user", hash_password("OldProbePass123!")),
        )
    source_before = hash_sqlite_family(source)
    sqlite_backup(source, destination)

    status = prepare_runtime_credentials(
        destination,
        {"probe_user": "NewProbePass123!"},
        normalize=True,
    )

    assert status == {"probe_user": "normalized_on_copy"}
    assert hash_sqlite_family(source) == source_before
    with sqlite3.connect(destination) as connection:
        copied_hash = connection.execute("SELECT hashed_password FROM users WHERE username = 'probe_user'").fetchone()[0]
    assert verify_password("NewProbePass123!", copied_hash) is True
    with sqlite3.connect(f"file:{source.resolve()}?mode=ro&immutable=1", uri=True) as connection:
        source_hash = connection.execute("SELECT hashed_password FROM users WHERE username = 'probe_user'").fetchone()[0]
    assert verify_password("OldProbePass123!", source_hash) is True
