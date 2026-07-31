"""Focused tests for the permanent AI Export real-prompt probe helpers."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from backend.app.services.auth_service import hash_password, verify_password
from backend.test_scripts.diagnostics.ai_export_real_prompt_probe import (
    AssetCandidate,
    FxCandidate,
    ProbeError,
    audit_public_tables,
    audit_snapshot_semantics,
    build_dimension_summary,
    build_period_detail_matrix,
    build_prompt_filename,
    build_user_scopes,
    classify_http_failure,
    compare_metric_runs,
    discover_catalog,
    hash_sqlite_family,
    is_technical_dataset,
    legacy_sampling_manifest,
    measure_canonical_breakdown,
    measure_technical_diagnostics,
    metric_change_reasons,
    prepare_runtime_credentials,
    prompt_size_category,
    rank_asset_candidates,
    rank_fx_candidates,
    representative_cases,
    representative_scopes,
    sanitize_filename_part,
    save_and_reread_prompt,
    scan_text_for_secrets,
    should_continue_after_failure,
    sqlite_backup,
    sqlite_primary_unchanged,
    tuning_v2_cases,
    tuning_v2_exclusions,
    validate_manifest_checks,
    validate_reconciled_breakdown,
)


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
        "id": "portfolio.description",
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
            "id": "portfolio.performance_attribution",
            "required_dataset_ids": [
                "portfolio.overview",
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
        }
    ]
    assert len(data_cases) == 9
    assert {(case["period_label"], case["detail_level"]) for case in temporal_analysis_cases} == {(period, detail) for period in ("3M", "1Y") for detail in ("compact", "standard", "full")}
    assert [(case["period_label"], case["detail_level"]) for case in as_of_analysis_cases] == [("1Y", "standard")]


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
                "has_instance_bucket_count": False,
                "has_instance_temporal_class": True,
            },
            [{"category": "technical_indicators"}],
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
    assert rows["portfolio.changed"]["reason_for_change"] == ["other"]
    assert rows["portfolio.added"]["status"] == "added"
    assert rows["portfolio.added"]["regression"] is False
    assert rows["portfolio.removed"]["status"] == "removed"
    assert rows["portfolio.recovered"]["status"] == "recovered"
    assert rows["portfolio.failed"]["status"] == "failed"


def test_http_failure_classification_and_fx_continuation():
    skipped = classify_http_failure(
        422,
        {"detail": {"code": "selection_not_applicable", "message": "No position"}},
        "asset",
    )
    fx_failure = classify_http_failure(
        503,
        {"detail": {"code": "snapshot_source_failure", "message": "FX unavailable", "retryable": True}},
        "fx",
    )

    assert skipped["status"] == "skipped"
    assert skipped["nonfatal"] is True
    assert fx_failure["status"] == "failed"
    assert fx_failure["retryable"] is True
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
            "all": {"broker_count": 2},
            3: {"broker_count": 1},
            7: {"broker_count": 1},
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
                    "considered_asset_count": 3,
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
        "considered_asset_count": 3,
        "eligible_asset_count": 2,
        "covered_asset_count": 2,
        "eligible_portfolio_weight_ratio": 1.0,
        "covered_portfolio_weight_ratio": 0.75,
        "covered_weight_ratio": 0.75,
    }


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
                    "considered_asset_count": 2,
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
                    "considered_asset_count": 2,
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
        ]
    )
    render_result = {
        "breakdown": {
            "format_diagnostics": {
                "floating_point_noise_normalized": 2,
                "empty_columns_removed": 3,
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
        "fifo_lot_reference",
        "breadth_weight_clarification",
        "hhi_semantic_correction",
    ]


def test_secret_scan_ignores_redacted_authorization_placeholder():
    assert scan_text_for_secrets("Authorization: [REDACTED]") == []


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
