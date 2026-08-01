#!/usr/bin/env python3
"""Repeatable diagnostics for AI Export Signal Density V2."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
os.environ["LIBREFOLIO_TEST_MODE"] = "1"

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from backend.app.config import get_data_dir  # noqa: E402
from backend.app.db.models import User  # noqa: E402
from backend.app.db.session import get_async_engine  # noqa: E402
from backend.app.schemas.ai_export_runtime import (  # noqa: E402
    AiExportAssetSnapshotRequest,
    AiExportBrokerSnapshotRequest,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportFxSnapshotRequest,
    AiExportPeriod,
    AiExportPortfolioSnapshotRequest,
    AiExportSnapshotRequest,
)
from backend.app.schemas.signals import SignalTemporalClass  # noqa: E402
from backend.app.services.ai_export.components import (  # noqa: E402
    portfolio_broker_technical,
    technical_shared,
)
from backend.app.services.ai_export.components.technical_shared import (  # noqa: E402
    ASSET_CURATED_SIGNALS,
    FX_CURATED_SIGNALS,
)
from backend.app.services.ai_export.runtime_service import (  # noqa: E402
    CATALOG_VERSION,
    AiExportSnapshotService,
)
from backend.app.services.ai_export.telemetry import (  # noqa: E402
    canonical_json,
    estimate_tokens_chars_div_4,
)
from backend.app.services.ai_export.temporal.plan import BucketPlan  # noqa: E402
from backend.app.services.ai_export.temporal.policy import (  # noqa: E402
    BucketDetailLevel,
    BucketingPolicy,
)
from backend.app.services.provider_registry import SignalPluginRegistry  # noqa: E402
from backend.test_scripts.diagnostics import (  # noqa: E402
    ai_export_technical_density_probe as baseline_helpers,
)

SCHEMA_VERSION = "2.0.0"
TARGET_CURRENCY = "USD"
PERIOD_ORDER = ("3M", "6M", "1Y")
DETAIL_ORDER = ("compact", "standard", "full")
REQUIRED_SELECTIONS = (
    "asset.market_technical",
    "broker.technical",
    "portfolio.technical",
)
FX_SELECTION = "fx.market_technical"
DEFAULT_BASELINE = REPOSITORY_ROOT / "LibreFolio_developer_journal" / "Release_2" / "Phase_0" / "01_signalMigration" / "02_aiExport" / "probe-phase00AiExportTechnicalDensity.json"
TEMPORAL_CLASS_ORDER = (
    SignalTemporalClass.VERY_FAST,
    SignalTemporalClass.FAST,
    SignalTemporalClass.MEDIUM_FAST,
    SignalTemporalClass.MEDIUM,
    SignalTemporalClass.SLOW,
    SignalTemporalClass.VERY_SLOW,
)

# Approved reference counts from test_ai_export_temporal.py::INDICATOR_POLICY_CASES.
APPROVED_TEMPORAL_MATRIX = {
    ("compact", "very_fast"): (2, 30, 30, (20, 23, 29)),
    ("compact", "fast"): (2, 25, 35, (18, 21, 26)),
    ("compact", "medium_fast"): (2, 20, 42, (16, 18, 23)),
    ("compact", "medium"): (2, 10, 42, (14, 16, 20)),
    ("compact", "slow"): (2, 5, 49, (12, 14, 17)),
    ("compact", "very_slow"): (2, 5, 84, (11, 12, 14)),
    ("standard", "very_fast"): (2, 30, 14, (26, 33, 46)),
    ("standard", "fast"): (2, 21, 15, (23, 29, 41)),
    ("standard", "medium_fast"): (2, 20, 17, (21, 26, 37)),
    ("standard", "medium"): (2, 15, 20, (18, 23, 32)),
    ("standard", "slow"): (2, 10, 22, (16, 20, 28)),
    ("standard", "very_slow"): (2, 5, 28, (13, 16, 23)),
    ("full", "very_fast"): (2, 30, 7, (35, 49, 75)),
    ("full", "fast"): (2, 28, 8, (32, 44, 67)),
    ("full", "medium_fast"): (2, 23, 9, (28, 38, 59)),
    ("full", "medium"): (2, 16, 10, (24, 33, 51)),
    ("full", "slow"): (2, 10, 11, (21, 29, 46)),
    ("full", "very_slow"): (2, 9, 14, (18, 24, 38)),
}

HIGHLIGHT_RULES: dict[str, tuple[str, ...]] = {
    "stoch_rsi_k_d": ("stoch_rsi_k_d",),
    "stoch_rsi_20_80": (
        "stoch_rsi_k_oversold_20",
        "stoch_rsi_k_overbought_80",
    ),
    "macd_signal_histogram": ("macd_signal", "macd_histogram_zero"),
    "price_or_rate_ema20": ("price_ema_20", "rate_ema_20"),
    "ema_crosses": ("ema_20_ema_50", "ema_50_ema_200"),
    "bollinger": ("bollinger",),
    "donchian": ("donchian",),
    "rsi": ("rsi_",),
    "adx": ("adx_",),
    "mfi": ("mfi_",),
}


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from exc


def _repo_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(REPOSITORY_ROOT))
    except ValueError:
        return f"<outside-repository>/{resolved.name}"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(baseline_helpers._canonical_fragment(value).encode("utf-8"))


def _percent(part: int, whole: int) -> float:
    return round((part / whole * 100.0) if whole else 0.0, 6)


def _reduction(before: int | None, after: int | None) -> dict[str, Any] | None:
    if before is None or after is None:
        return None
    absolute = before - after
    return {
        "before": before,
        "after": after,
        "absolute_reduction": absolute,
        "percent_reduction": _percent(absolute, before),
    }


def _period(label: str, snapshot_as_of: date) -> AiExportPeriod:
    return baseline_helpers._period(label, snapshot_as_of)


def _probe_id(selection: str, detail: str, period_label: str) -> str:
    return baseline_helpers._probe_id(selection, detail, period_label)


def _selection_is_optional(selection: str) -> bool:
    return selection == FX_SELECTION


def _annotation_family(key: str) -> str:
    for family in (
        "stoch_rsi",
        "bollinger",
        "donchian",
        "macd",
        "mfi",
        "rsi",
        "adx",
        "ppo",
        "roc",
        "ema",
    ):
        if family in key:
            return family
    return "other"


def _signal_category(signal_code: str) -> str:
    plugin = SignalPluginRegistry.get_plugin(signal_code)
    if plugin is None:
        return "unknown"
    category = plugin.category
    return category.value if hasattr(category, "value") else str(category)


def _event_public_dict(event: Any) -> dict[str, Any]:
    payload = dict(event.payload)
    return {"date": event.date.isoformat(), **payload}


def _event_identity(event: Any) -> str:
    payload = dict(event.payload)
    payload.pop("semantic_description", None)
    return _sha256_json(
        {
            "date": event.date.isoformat(),
            "dedup_key": repr(event.dedup_key),
            "payload": payload,
        }
    )


def _event_group_key(payload: Mapping[str, Any]) -> tuple[str, str]:
    return str(payload.get("entity_id")), str(payload.get("key"))


def _temporal_threshold_offsets(policy: BucketingPolicy) -> dict[str, int | None]:
    thresholds = tuple(sorted({2, 3, 5, 7, 14, policy.max_bucket_days}))
    found: dict[int, int | None] = {threshold: None for threshold in thresholds if threshold <= policy.max_bucket_days}
    for offset in range(1_000_001):
        width = policy.bucket_width(offset)
        for threshold in found:
            if found[threshold] is None and width >= threshold:
                found[threshold] = offset
        if all(value is not None for value in found.values()):
            break
    output = {f"d_ge_{threshold}": (found.get(threshold) if threshold <= policy.max_bucket_days else None) for threshold in thresholds}
    output["d_ge_k"] = found[policy.max_bucket_days]
    return output


def _temporal_plan_measurement(
    *,
    detail: BucketDetailLevel,
    temporal_class: SignalTemporalClass,
    total_days: int,
    snapshot_as_of: date,
    expected_count: int,
) -> dict[str, Any]:
    policy = BucketingPolicy.for_indicator(detail, temporal_class)
    start = snapshot_as_of - timedelta(days=total_days - 1)
    plan = BucketPlan.build(start, snapshot_as_of, policy)
    newest_first = tuple(reversed(plan.buckets))
    boundaries = []
    for newest_index, bucket in enumerate(newest_first):
        offset_start = (snapshot_as_of - bucket.end_date).days
        offset_end = (snapshot_as_of - bucket.start_date).days + 1
        boundaries.append(
            {
                "index_newest_first": newest_index,
                "index_oldest_first": bucket.index,
                "start_date": bucket.start_date.isoformat(),
                "end_date": bucket.end_date.isoformat(),
                "offset_start_inclusive": offset_start,
                "offset_end_exclusive": offset_end,
                "actual_width_days": bucket.day_count,
                "formula_width_at_offset_start": policy.bucket_width(offset_start),
                "oldest_boundary_truncated": (newest_index == len(newest_first) - 1 and bucket.day_count < policy.bucket_width(offset_start)),
            }
        )
    first_non_daily = next(
        (boundary for boundary in boundaries if boundary["actual_width_days"] > 1),
        None,
    )
    newest_daily_count = 0
    for boundary in boundaries:
        if boundary["actual_width_days"] != 1:
            break
        newest_daily_count += 1
    actual_widths = [boundary["actual_width_days"] for boundary in boundaries]
    formula_widths = [boundary["formula_width_at_offset_start"] for boundary in boundaries]
    non_truncated_widths = actual_widths[:-1]
    contiguous = all(current.start_date == previous.end_date + timedelta(days=1) for previous, current in zip(plan.buckets, plan.buckets[1:], strict=False))
    assertions = {
        "full_coverage": sum(actual_widths) == total_days,
        "no_gaps_or_overlap": contiguous,
        "last_boundary_exact": (plan.buckets[0].start_date == start and plan.buckets[-1].end_date == snapshot_as_of),
        "monotonic_formula_width": all(current <= following for current, following in zip(formula_widths, formula_widths[1:], strict=False)),
        "monotonic_actual_width_except_oldest_truncation": all(current <= following for current, following in zip(non_truncated_widths, non_truncated_widths[1:], strict=False)),
        "all_widths_lte_k": all(width <= policy.max_bucket_days for width in actual_widths),
        "runtime_count_matches_approved_spec": len(plan.buckets) == expected_count,
    }
    return {
        "duration_days": total_days,
        "requested_start": start.isoformat(),
        "snapshot_as_of": snapshot_as_of.isoformat(),
        "theoretical_expected_count": expected_count,
        "runtime_count": len(plan.buckets),
        "difference": len(plan.buckets) - expected_count,
        "orientation": ("boundaries are newest-first; offsets are half-open calendar-day " "ranges measured backward from snapshot_as_of"),
        "boundaries": boundaries,
        "first_non_daily_bucket": first_non_daily,
        "consecutive_newest_daily_bucket_count": newest_daily_count,
        "formula_threshold_offsets": _temporal_threshold_offsets(policy),
        "actual_max_width_reached": max(actual_widths),
        "bucket_day_ratio": round(len(plan.buckets) / total_days, 9),
        "assertions": assertions,
        "valid": all(assertions.values()),
    }


def _temporal_policy_matrix(snapshot_as_of: date) -> dict[str, Any]:
    combinations = []
    for detail in BucketDetailLevel:
        for temporal_class in TEMPORAL_CLASS_ORDER:
            approved = APPROVED_TEMPORAL_MATRIX[(detail.value, temporal_class.value)]
            expected_p, expected_m, expected_k, expected_counts = approved
            policy = BucketingPolicy.for_indicator(detail, temporal_class)
            parameter_assertions = {
                "p_matches_approved_spec": policy.exponent == expected_p,
                "m_matches_approved_spec": policy.half_life_offset == expected_m,
                "k_matches_approved_spec": policy.max_bucket_days == expected_k,
            }
            durations = [
                _temporal_plan_measurement(
                    detail=detail,
                    temporal_class=temporal_class,
                    total_days=total_days,
                    snapshot_as_of=snapshot_as_of,
                    expected_count=expected_count,
                )
                for total_days, expected_count in zip((90, 180, 365), expected_counts, strict=True)
            ]
            combinations.append(
                {
                    "detail_level": detail.value,
                    "temporal_class": temporal_class.value,
                    "p": policy.exponent,
                    "m": policy.half_life_offset,
                    "k": policy.max_bucket_days,
                    "approved_spec": {
                        "p": expected_p,
                        "m": expected_m,
                        "k": expected_k,
                        "counts_90_180_365": list(expected_counts),
                        "source": ("backend/test_scripts/test_services/" "test_ai_export_temporal.py::INDICATOR_POLICY_CASES"),
                    },
                    "parameter_assertions": parameter_assertions,
                    "durations": durations,
                    "valid": all(parameter_assertions.values()) and all(item["valid"] for item in durations),
                }
            )
    return {
        "combination_count": len(combinations),
        "expected_combination_count": 18,
        "combinations": combinations,
        "valid": len(combinations) == 18 and all(item["valid"] for item in combinations),
    }


def _load_baseline(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    document = json.loads(raw)
    probes = document.get("probes")
    if not isinstance(probes, list):
        raise ValueError("baseline JSON has no probes list")
    probe_by_id = {str(probe["probe_id"]): probe for probe in probes if isinstance(probe, dict) and "probe_id" in probe}
    portfolio = probe_by_id.get("portfolio.technical:full:1Y")
    if portfolio is None:
        raise ValueError("baseline lacks portfolio.technical:full:1Y")
    indicator_rows = sum(int(indicator.get("row_count", 0)) for indicator in portfolio.get("indicators", []) if isinstance(indicator, dict))
    actual_facts = {
        "asset_count": portfolio.get("counts", {}).get("asset_count"),
        "indicator_instance_count": portfolio.get("counts", {}).get("indicators_exported_total"),
        "old_buckets_per_indicator": portfolio.get("counts", {}).get("bucket_count"),
        "indicator_rows": indicator_rows,
        "events": portfolio.get("counts", {}).get("event_count"),
        "chars": portfolio.get("canonical_response", {}).get("chars"),
        "tokens": portfolio.get("canonical_response", {}).get("estimated_tokens"),
    }
    expected_facts = {
        "asset_count": 3,
        "indicator_instance_count": 60,
        "old_buckets_per_indicator": 75,
        "indicator_rows": 4500,
        "events": 1615,
        "chars": 2676781,
        "tokens": 669196,
    }
    summary = {
        "path": _repo_path(path),
        "sha256": _sha256_bytes(raw),
        "schema_version": document.get("schema_version"),
        "generated_at": document.get("generated_at"),
        "probe_count": len(probe_by_id),
        "portfolio_full_1y_expected_facts": expected_facts,
        "portfolio_full_1y_actual_facts": actual_facts,
        "portfolio_full_1y_facts_match": actual_facts == expected_facts,
    }
    return document, summary


def _build_request(
    *,
    selection_id: str,
    detail: str,
    period: AiExportPeriod,
    asset_id: int,
    broker_id: int,
    selection_version: int,
    fx_base: str,
    fx_quote: str,
) -> AiExportSnapshotRequest:
    common = {
        "selection": AiExportDatasetSelection(kind="dataset", id=selection_id, version=selection_version),
        "detail_level": AiExportDetailLevel(detail),
        "period": period,
        "target_currency": TARGET_CURRENCY,
        "expected_catalog_version": CATALOG_VERSION,
    }
    if selection_id.startswith("asset."):
        return AiExportAssetSnapshotRequest(domain="asset", asset_id=asset_id, **common)
    if selection_id.startswith("broker."):
        return AiExportBrokerSnapshotRequest(domain="broker", broker_id=broker_id, **common)
    if selection_id.startswith("portfolio."):
        return AiExportPortfolioSnapshotRequest(domain="portfolio", broker_ids=[broker_id], **common)
    return AiExportFxSnapshotRequest(
        domain="fx",
        base_currency=fx_base,
        quote_currency=fx_quote,
        **common,
    )


def _baseline_indicator_map(
    baseline_probe: Mapping[str, Any] | None,
) -> dict[tuple[int | None, str, str], Mapping[str, Any]]:
    if baseline_probe is None:
        return {}
    return {
        (
            item.get("asset_id"),
            str(item.get("signal_code")),
            str(item.get("instance_id")),
        ): item
        for item in baseline_probe.get("indicators", [])
        if isinstance(item, Mapping)
    }


def _diagnostic_technical_sampling(response: Mapping[str, Any]) -> dict[str, Any] | None:
    public_manifest = response.get("technical_sampling")
    if not isinstance(public_manifest, Mapping):
        return None
    detail = BucketDetailLevel(str(public_manifest["detail_level"]))
    public_price = public_manifest.get("price_policy")
    price_policy = None
    if isinstance(public_price, Mapping):
        resolved = BucketingPolicy.for_detail_level(detail)
        price_policy = {
            "detail_level": detail.value,
            "p": resolved.exponent,
            "m": resolved.half_life_offset,
            "k": resolved.max_bucket_days,
            "bucket_count": public_price.get("bucket_count"),
        }
    indicator_policies = []
    for item in public_manifest.get("indicator_policies", []):
        if not isinstance(item, Mapping):
            continue
        temporal_class = SignalTemporalClass(str(item["temporal_class"]))
        resolved = BucketingPolicy.for_indicator(detail, temporal_class)
        indicator_policies.append(
            {
                "signal_instance_id": item.get("signal_instance_id"),
                "signal_code": item.get("signal_code"),
                "temporal_class": temporal_class.value,
                "detail_level": detail.value,
                "p": resolved.exponent,
                "m": resolved.half_life_offset,
                "k": resolved.max_bucket_days,
                "bucket_count": item.get("bucket_count"),
            }
        )
    return {
        "detail_level": detail.value,
        "price_policy": price_policy,
        "indicator_policies": indicator_policies,
    }


def _contains_sampling_implementation_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(key in {"p", "m", "k"} or _contains_sampling_implementation_key(nested) for key, nested in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_sampling_implementation_key(item) for item in value)
    return False


def _indicator_measurements(
    response: dict[str, Any],
    *,
    total_chars: int,
    baseline_probe: Mapping[str, Any] | None,
) -> dict[str, Any]:
    component_chars = {item["component_id"]: item["chars"] for item in baseline_helpers._component_measurements(response, total_chars)["components"]}
    manifest = _diagnostic_technical_sampling(response) or {}
    policy_by_instance = {item["signal_instance_id"]: item for item in manifest.get("indicator_policies", []) if isinstance(item, dict)}
    baseline_by_key = _baseline_indicator_map(baseline_probe)
    items = []
    by_class: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for component_id, asset_id, indicator in baseline_helpers._iter_indicator_instances(response):
        rows = indicator.get("rows", [])
        columns = indicator.get("columns", [])
        output_keys = sorted({str(column.get("output_key")) for column in columns if isinstance(column, dict) and column.get("output_key") is not None})
        full_chars = baseline_helpers._serialized_chars(indicator)
        period_summary_chars = baseline_helpers._serialized_chars(indicator.get("period_summary", {}))
        rows_chars = baseline_helpers._serialized_chars(rows)
        metadata = {key: value for key, value in indicator.items() if key not in {"period_summary", "rows"}}
        metadata_chars = baseline_helpers._serialized_chars(metadata)
        policy = policy_by_instance.get(indicator.get("instance_id"), {})
        baseline_item = baseline_by_key.get(
            (
                asset_id,
                str(indicator.get("signal_code")),
                str(indicator.get("instance_id")),
            )
        )
        baseline_chars = int(baseline_item["full_serialized_chars"]) if baseline_item is not None else None
        baseline_rows = int(baseline_item["row_count"]) if baseline_item is not None else None
        temporal_class = str(indicator.get("temporal_class"))
        measurement = {
            "component_id": component_id,
            "asset_id": asset_id,
            "signal_code": indicator.get("signal_code"),
            "instance_id": indicator.get("instance_id"),
            "temporal_class": temporal_class,
            "resolved_policy": {
                "p": policy.get("p"),
                "m": policy.get("m"),
                "k": policy.get("k"),
                "manifest_bucket_count": policy.get("bucket_count"),
            },
            "output_count": len(output_keys),
            "output_keys": output_keys,
            "column_count": len(columns),
            "bucket_count": len(rows),
            "serialized_chars": full_chars,
            "estimated_tokens": estimate_tokens_chars_div_4(full_chars),
            "percent_of_indicator_block": _percent(full_chars, component_chars.get(component_id, 0)),
            "percent_of_total": _percent(full_chars, total_chars),
            "period_summary_chars": period_summary_chars,
            "rows_chars": rows_chars,
            "metadata_chars": metadata_chars,
            "first_row_boundary": ({key: rows[0].get(key) for key in ("start_date", "end_date", "calendar_days")} if rows else None),
            "last_row_boundary": ({key: rows[-1].get(key) for key in ("start_date", "end_date", "calendar_days")} if rows else None),
            "row_orientation": "oldest-first",
            "baseline_comparison": {
                "matching_p0_indicator": baseline_item is not None,
                "chars": _reduction(baseline_chars, full_chars),
                "row_count": _reduction(baseline_rows, len(rows)),
            },
            "multi_output": len(output_keys) > 1,
        }
        items.append(measurement)
        by_class[temporal_class].append(measurement)
    items.sort(
        key=lambda item: (
            -1 if item["asset_id"] is None else item["asset_id"],
            str(item["instance_id"]),
        )
    )
    class_aggregates = {
        temporal_class: {
            "indicator_count": len(group),
            "bucket_rows": sum(item["bucket_count"] for item in group),
            "serialized_chars": sum(item["serialized_chars"] for item in group),
            "period_summary_chars": sum(item["period_summary_chars"] for item in group),
            "rows_chars": sum(item["rows_chars"] for item in group),
            "metadata_chars": sum(item["metadata_chars"] for item in group),
        }
        for temporal_class, group in sorted(by_class.items())
    }
    return {
        "items": items,
        "by_temporal_class": class_aggregates,
        "multi_output_indicators": [
            {
                "asset_id": item["asset_id"],
                "signal_code": item["signal_code"],
                "instance_id": item["instance_id"],
                "output_count": item["output_count"],
                "column_count": item["column_count"],
                "serialized_chars": item["serialized_chars"],
            }
            for item in items
            if item["multi_output"]
        ],
    }


def _runtime_event_payloads(
    response: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    selected_events: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    detected_total = 0
    exported_total = 0
    for section in response.get("sections", []):
        payload = section.get("payload", {})
        if not isinstance(payload, dict) or "selection_summaries" not in payload:
            continue
        detected_total += int(payload.get("detected_event_count", 0))
        exported_total += int(payload.get("exported_event_count", 0))
        summaries.extend(item for item in payload.get("selection_summaries", []) if isinstance(item, dict))
        for bucket in payload.get("buckets", []):
            if isinstance(bucket, dict):
                selected_events.extend(event for event in bucket.get("events", []) if isinstance(event, dict))
    return selected_events, summaries, detected_total, exported_total


def _captured_event_groups(
    captures: Sequence[dict[str, Any]],
) -> tuple[
    dict[tuple[str, str], list[Any]],
    dict[tuple[str, str], list[Any]],
    set[str],
    set[str],
]:
    detected_by_group: defaultdict[tuple[str, str], list[Any]] = defaultdict(list)
    selected_by_group: defaultdict[tuple[str, str], list[Any]] = defaultdict(list)
    detected_identities: set[str] = set()
    selected_identities: set[str] = set()
    detected_dedup: dict[str, Any] = {}
    selected_dedup: dict[str, Any] = {}
    for capture in captures:
        for event in capture["input_events"]:
            detected_dedup.setdefault(repr(event.dedup_key), event)
        for event in capture["selected_events"]:
            selected_dedup.setdefault(repr(event.dedup_key), event)
    for event in detected_dedup.values():
        group = _event_group_key(event.payload)
        detected_by_group[group].append(event)
        detected_identities.add(_event_identity(event))
    for event in selected_dedup.values():
        group = _event_group_key(event.payload)
        selected_by_group[group].append(event)
        selected_identities.add(_event_identity(event))
    return (
        dict(detected_by_group),
        dict(selected_by_group),
        detected_identities,
        selected_identities,
    )


def _highlight_event_groups(groups: Sequence[dict[str, Any]], selection_id: str) -> dict[str, Any]:
    output = {}
    for label, tokens in HIGHLIGHT_RULES.items():
        if label in {"rsi", "adx", "mfi"}:
            matches = [group for group in groups if group["annotation_key"].startswith(tokens[0])]
        else:
            matches = [group for group in groups if any(token == group["annotation_key"] or token in group["annotation_key"] for token in tokens)]
        output[label] = {
            "present": bool(matches),
            "group_count": len(matches),
            "detected": sum(group["detected"] for group in matches),
            "exported": sum(group["exported"] for group in matches),
            "omitted": sum(group["omitted"] for group in matches),
            "selected_chars": sum(group["selected_chars"] for group in matches),
        }
    fx_groups = groups if selection_id == FX_SELECTION else []
    output["fx_if_present"] = {
        "present": bool(fx_groups),
        "group_count": len(fx_groups),
        "detected": sum(group["detected"] for group in fx_groups),
        "exported": sum(group["exported"] for group in fx_groups),
        "omitted": sum(group["omitted"] for group in fx_groups),
        "selected_chars": sum(group["selected_chars"] for group in fx_groups),
    }
    return output


def _event_measurements(
    response: dict[str, Any],
    *,
    captures: Sequence[dict[str, Any]],
    selection_id: str,
) -> tuple[dict[str, Any], set[str], set[str]]:
    selected_events, summaries, detected_total, exported_total = _runtime_event_payloads(response)
    detected_groups, captured_selected_groups, detected_ids, selected_ids = _captured_event_groups(captures)
    runtime_selected_by_group: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in selected_events:
        runtime_selected_by_group[_event_group_key(event)].append(event)
    summary_by_group = {(str(item["entity_id"]), str(item["annotation_key"])): item for item in summaries}
    group_keys = sorted(set(summary_by_group) | set(detected_groups) | set(captured_selected_groups) | set(runtime_selected_by_group))
    groups = []
    for entity_id, annotation_key in group_keys:
        summary = summary_by_group.get((entity_id, annotation_key), {})
        detected = detected_groups.get((entity_id, annotation_key), [])
        selected = runtime_selected_by_group.get((entity_id, annotation_key), [])
        signal_codes = sorted({str(event.payload.get("signal_code")) for event in detected if isinstance(event.payload, Mapping)} | {str(event.get("signal_code")) for event in selected if event.get("signal_code") is not None})
        detected_chars = baseline_helpers._serialized_chars([_event_public_dict(event) for event in detected])
        selected_chars = baseline_helpers._serialized_chars(selected)
        detected_count = int(summary.get("detected_count", len(detected)))
        exported_count = int(summary.get("exported_count", len(selected)))
        groups.append(
            {
                "selection_scope": selection_id,
                "entity_id": entity_id,
                "asset_id": next(
                    (event.payload.get("asset_id") for event in detected if isinstance(event.payload, Mapping) and event.payload.get("asset_id") is not None),
                    next(
                        (event.get("asset_id") for event in selected if event.get("asset_id") is not None),
                        None,
                    ),
                ),
                "annotation_key": annotation_key,
                "annotation_family": _annotation_family(annotation_key),
                "signal_plugins": signal_codes,
                "signal_categories": sorted({_signal_category(code) for code in signal_codes}),
                "detected": detected_count,
                "recent_30d": int(summary.get("recent_30d_count", 0)),
                "exported": exported_count,
                "omitted": detected_count - exported_count,
                "first_detected": summary.get("oldest_detected_event_date"),
                "last_detected": summary.get("newest_detected_event_date"),
                "first_exported": summary.get("oldest_exported_event_date"),
                "last_exported": summary.get("newest_exported_event_date"),
                "directions": {
                    "up": int(summary.get("upward_count", 0)),
                    "down": int(summary.get("downward_count", 0)),
                    "other_or_none": max(
                        detected_count - int(summary.get("upward_count", 0)) - int(summary.get("downward_count", 0)),
                        0,
                    ),
                },
                "detected_chars": detected_chars,
                "selected_chars": selected_chars,
                "char_reduction": _reduction(detected_chars, selected_chars),
                "capture_detected_count": len(detected),
                "capture_selected_count": len(captured_selected_groups.get((entity_id, annotation_key), [])),
            }
        )
    by_plugin: Counter[str] = Counter()
    by_entity: Counter[str] = Counter()
    by_key: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_family: Counter[str] = Counter()
    for group in groups:
        for plugin in group["signal_plugins"]:
            by_plugin[plugin] += group["exported"]
        for category in group["signal_categories"]:
            by_category[category] += group["exported"]
        by_entity[group["entity_id"]] += group["exported"]
        by_key[group["annotation_key"]] += group["exported"]
        by_family[group["annotation_family"]] += group["exported"]
    capture_complete = bool(captures) and sum(len(group) for group in detected_groups.values()) == detected_total and sum(len(group) for group in captured_selected_groups.values()) == exported_total
    summary_reconciles = sum(int(item.get("detected_count", 0)) for item in summaries) == detected_total and sum(int(item.get("exported_count", 0)) for item in summaries) == exported_total and len(selected_events) == exported_total
    return (
        {
            "detected_event_count": detected_total,
            "exported_event_count": exported_total,
            "omitted_event_count": detected_total - exported_total,
            "selection_summary_count": len(summaries),
            "selection_summaries_serialized_chars": baseline_helpers._serialized_chars(summaries),
            "selected_serialized_chars": baseline_helpers._serialized_chars(selected_events),
            "detected_serialized_chars": baseline_helpers._serialized_chars([_event_public_dict(event) for group in detected_groups.values() for event in group]),
            "groups": groups,
            "aggregates": {
                "by_plugin": dict(sorted(by_plugin.items())),
                "by_asset_or_entity": dict(sorted(by_entity.items())),
                "by_annotation_key": dict(sorted(by_key.items())),
                "by_signal_category": dict(sorted(by_category.items())),
                "by_annotation_family": dict(sorted(by_family.items())),
                "by_selection_scope": {selection_id: exported_total},
            },
            "highlights": _highlight_event_groups(groups, selection_id),
            "identity_fingerprints": {
                "detected_count": len(detected_ids),
                "detected_sha256": _sha256_json(sorted(detected_ids)),
                "exported_count": len(selected_ids),
                "exported_sha256": _sha256_json(sorted(selected_ids)),
                "definition": ("SHA-256 over sorted event identities containing date, " "dedup key and payload without semantic_description"),
            },
            "validation": {
                "capture_complete": capture_complete,
                "selection_summaries_reconcile": summary_reconciles,
            },
        },
        detected_ids,
        selected_ids,
    )


def _baseline_comparison(probe: Mapping[str, Any], baseline_probe: Mapping[str, Any] | None) -> dict[str, Any]:
    if baseline_probe is None:
        return {"status": "no_matching_p0_probe"}
    before_total = int(baseline_probe["canonical_response"]["chars"])
    after_total = int(probe["canonical_response"]["chars"])
    before_tokens = int(baseline_probe["canonical_response"]["estimated_tokens"])
    after_tokens = int(probe["canonical_response"]["estimated_tokens"])
    before_categories = baseline_probe.get("sections", {}).get("categories", {})
    after_categories = probe.get("sections", {}).get("categories", {})
    before_indicator = int(before_categories.get("indicators", {}).get("chars", 0))
    after_indicator = int(after_categories.get("indicators", {}).get("chars", 0))
    before_event = int(before_categories.get("events", {}).get("chars", 0))
    after_event = int(after_categories.get("events", {}).get("chars", 0))
    indicator_reduction = before_indicator - after_indicator
    event_reduction = before_event - after_event
    total_reduction = before_total - after_total
    combined = indicator_reduction + event_reduction
    return {
        "status": "matched",
        "before": {
            "total_chars": before_total,
            "total_tokens": before_tokens,
            "events": baseline_probe.get("counts", {}).get("event_count"),
            "section_chars": {key: value.get("chars", 0) for key, value in sorted(before_categories.items()) if isinstance(value, Mapping)},
        },
        "after": {
            "total_chars": after_total,
            "total_tokens": after_tokens,
            "detected_events": probe["events"]["detected_event_count"],
            "exported_events": probe["events"]["exported_event_count"],
            "section_chars": {key: value.get("chars", 0) for key, value in sorted(after_categories.items()) if isinstance(value, Mapping)},
        },
        "reductions": {
            "total_chars": _reduction(before_total, after_total),
            "total_tokens": _reduction(before_tokens, after_tokens),
            "indicator_section_chars": _reduction(before_indicator, after_indicator),
            "event_section_chars": _reduction(before_event, after_event),
            "indicator_plus_event_chars": {
                "absolute_reduction": combined,
                "percent_of_total_p0": _percent(combined, before_total),
            },
            "total_combined_chars": {
                "absolute_reduction": total_reduction,
                "percent_reduction": _percent(total_reduction, before_total),
            },
            "residual_non_indicator_event_sections_and_top_level_chars": (total_reduction - combined),
        },
        "new_v2_summary_manifest_measurements": {
            "technical_sampling_manifest_chars": baseline_helpers._serialized_chars(probe.get("public_technical_sampling")),
            "diagnostic_sampling_policy_chars": baseline_helpers._serialized_chars(probe.get("technical_sampling")),
            "event_selection_manifest_chars": baseline_helpers._serialized_chars(probe.get("event_selection")),
            "indicator_period_summaries_chars": sum(item["period_summary_chars"] for item in probe["indicators"]["items"]),
            "event_selection_summaries_chars": probe["events"]["selection_summaries_serialized_chars"],
            "note": "Observed V2 overhead values overlap their owning indicator/event/top-level sections and are not added to the exact residual.",
        },
        "measurement_note": ("All before/after values are actual canonical serialized measurements; " "no linear estimates."),
    }


async def _run_probe(
    *,
    service: AiExportSnapshotService,
    user_id: int,
    request: AiExportSnapshotRequest,
    probe_id: str,
    period_label: str,
    baseline_probe: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], set[str], set[str]]:
    started = time.perf_counter()
    captured_bundles: list[Any] = []
    event_captures: list[dict[str, Any]] = []
    original_loader = portfolio_broker_technical.load_technical_universe_bundle
    original_selector = technical_shared.select_technical_events

    async def _capturing_loader(*args, **kwargs):
        bundle = await original_loader(*args, **kwargs)
        captured_bundles.append(bundle)
        return bundle

    def _capturing_selector(events, *, snapshot_as_of):
        selected = original_selector(events, snapshot_as_of=snapshot_as_of)
        event_captures.append(
            {
                "input_events": tuple(events),
                "selected_events": selected.events,
            }
        )
        return selected

    portfolio_broker_technical.load_technical_universe_bundle = _capturing_loader
    technical_shared.select_technical_events = _capturing_selector
    try:
        prepared = await service.prepare_request(user_id, request)
        response_model = await service.build_snapshot(user_id, request)
    except Exception as exc:
        return (
            {
                "probe_id": probe_id,
                "status": "failed",
                "optional": _selection_is_optional(request.selection.id),
                "failure_is_fatal": not _selection_is_optional(request.selection.id),
                "request": request.model_dump(mode="json"),
                "period_label": period_label,
                "effective_period_days": (request.period.end - request.period.start).days + 1,
                "duration_seconds": round(time.perf_counter() - started, 6),
                "error_type": type(exc).__name__,
                "message": str(exc),
                "known_fx_warmup_coupling_nonfatal": _selection_is_optional(request.selection.id),
            },
            set(),
            set(),
        )
    finally:
        portfolio_broker_technical.load_technical_universe_bundle = original_loader
        technical_shared.select_technical_events = original_selector

    response = response_model.model_dump(mode="json")
    canonical = canonical_json(response)
    total_chars = len(canonical)
    sections = baseline_helpers._component_measurements(response, total_chars)
    indicators = _indicator_measurements(
        response,
        total_chars=total_chars,
        baseline_probe=baseline_probe,
    )
    events, detected_ids, selected_ids = _event_measurements(
        response,
        captures=event_captures,
        selection_id=request.selection.id,
    )
    asset_ids = baseline_helpers._collect_asset_ids(response)
    positions = baseline_helpers._position_measurements(captured_bundles)
    requested_per_asset = len(FX_CURATED_SIGNALS) if request.selection.id == FX_SELECTION else len(ASSET_CURATED_SIGNALS)
    requested_total = requested_per_asset * (1 if request.selection.id == FX_SELECTION else len(asset_ids))
    exported_indicators = len(indicators["items"])
    public_technical_sampling = response.get("technical_sampling")
    technical_sampling = _diagnostic_technical_sampling(response)
    price_bucket_count = (public_technical_sampling or {}).get("price_policy", {}).get("bucket_count") if isinstance((public_technical_sampling or {}).get("price_policy"), dict) else None
    effective_period = response.get("meta", {}).get("exported_period", {})
    probe = {
        "probe_id": probe_id,
        "status": "ok",
        "optional": _selection_is_optional(request.selection.id),
        "failure_is_fatal": False,
        "request": request.model_dump(mode="json"),
        "effective_period": {
            "label": period_label,
            "start": effective_period.get("start", request.period.start.isoformat()),
            "end": effective_period.get("end", request.period.end.isoformat()),
            "inclusive_day_count": (request.period.end - request.period.start).days + 1,
        },
        "scope": {
            "resolved_broker_scope": list(prepared.broker_scope),
            "asset_count": len(asset_ids),
            "asset_ids": sorted(asset_ids),
            "scoped_broker_count": len(prepared.broker_scope),
            **positions,
        },
        "counts": {
            "requested_indicators_per_asset_or_pair": requested_per_asset,
            "requested_indicators_total": requested_total,
            "exported_indicators_total": exported_indicators,
            "exported_unique_instances": len({item["instance_id"] for item in indicators["items"]}),
            "price_bucket_count": price_bucket_count,
            "indicator_bucket_rows": sum(item["bucket_count"] for item in indicators["items"]),
            "event_detected": events["detected_event_count"],
            "event_exported": events["exported_event_count"],
            "event_omitted": events["omitted_event_count"],
        },
        "duration_seconds": round(time.perf_counter() - started, 6),
        "canonical_response": {
            "chars": total_chars,
            "utf8_bytes": len(canonical.encode("utf-8")),
            "estimated_tokens": estimate_tokens_chars_div_4(total_chars),
            "token_estimation_method": "chars_div_4_v1",
            "runtime_reported_chars": response.get("stats", {}).get("serialized_characters"),
            "runtime_reported_tokens": response.get("stats", {}).get("estimated_tokens"),
        },
        "technical_sampling": technical_sampling,
        "public_technical_sampling": public_technical_sampling,
        "event_selection": response.get("event_selection"),
        "sections": sections,
        "indicators": indicators,
        "events": events,
        "validation": {
            "runtime_chars_match_canonical": response.get("stats", {}).get("serialized_characters") == total_chars,
            "runtime_tokens_match_canonical": response.get("stats", {}).get("estimated_tokens") == estimate_tokens_chars_div_4(total_chars),
            "event_capture_complete": events["validation"]["capture_complete"],
            "event_summaries_reconcile": events["validation"]["selection_summaries_reconcile"],
            "manifest_present": public_technical_sampling is not None and response.get("event_selection") is not None,
            "public_manifest_omits_p_m_k": not _contains_sampling_implementation_key(public_technical_sampling),
            "diagnostic_manifest_retains_p_m_k": _contains_sampling_implementation_key(technical_sampling),
        },
    }
    probe["validation"]["valid"] = all(probe["validation"].values())
    probe["baseline_comparison"] = _baseline_comparison(probe, baseline_probe)
    return probe, detected_ids, selected_ids


def _aggregate_numeric(probes: Sequence[Mapping[str, Any]], key_path: tuple[str, ...]) -> dict[str, Any]:
    values = []
    for probe in probes:
        current: Any = probe
        for key in key_path:
            current = current[key]
        values.append(int(current))
    return {
        "min": min(values),
        "max": max(values),
        "total": sum(values),
        "average": round(sum(values) / len(values), 3),
    }


def _aggregate_probe_group(probes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "probe_count": len(probes),
        "chars": _aggregate_numeric(probes, ("canonical_response", "chars")),
        "tokens": _aggregate_numeric(probes, ("canonical_response", "estimated_tokens")),
        "detected_events": _aggregate_numeric(probes, ("counts", "event_detected")),
        "exported_events": _aggregate_numeric(probes, ("counts", "event_exported")),
        "indicator_bucket_rows": _aggregate_numeric(probes, ("counts", "indicator_bucket_rows")),
    }


def _aggregate_summaries(probes: Sequence[dict[str, Any]]) -> dict[str, Any]:
    successes = [probe for probe in probes if probe["status"] == "ok"]
    failures = [probe for probe in probes if probe["status"] == "failed"]
    grouped: dict[str, dict[str, Any]] = {}
    for field, resolver in (
        ("by_selection", lambda probe: probe["request"]["selection"]["id"]),
        ("by_detail_level", lambda probe: probe["request"]["detail_level"]),
        ("by_period", lambda probe: probe["period_label"] if "period_label" in probe else probe["effective_period"]["label"]),
    ):
        buckets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for probe in successes:
            buckets[str(resolver(probe))].append(probe)
        grouped[field] = {key: _aggregate_probe_group(items) for key, items in sorted(buckets.items())}
    event_by_plugin: Counter[str] = Counter()
    event_by_entity: Counter[str] = Counter()
    event_by_key: Counter[str] = Counter()
    event_by_category: Counter[str] = Counter()
    event_by_family: Counter[str] = Counter()
    event_by_scope: Counter[str] = Counter()
    indicator_by_class: Counter[str] = Counter()
    for probe in successes:
        for key, value in probe["events"]["aggregates"]["by_plugin"].items():
            event_by_plugin[key] += value
        for key, value in probe["events"]["aggregates"]["by_asset_or_entity"].items():
            event_by_entity[key] += value
        for key, value in probe["events"]["aggregates"]["by_annotation_key"].items():
            event_by_key[key] += value
        for key, value in probe["events"]["aggregates"]["by_signal_category"].items():
            event_by_category[key] += value
        for key, value in probe["events"]["aggregates"]["by_annotation_family"].items():
            event_by_family[key] += value
        for key, value in probe["events"]["aggregates"]["by_selection_scope"].items():
            event_by_scope[key] += value
        for key, value in probe["indicators"]["by_temporal_class"].items():
            indicator_by_class[key] += value["serialized_chars"]
    return {
        "probe_count": len(probes),
        "success_count": len(successes),
        "failure_count": len(failures),
        "failed_probe_ids": [probe["probe_id"] for probe in failures],
        "overall": _aggregate_probe_group(successes) if successes else None,
        **grouped,
        "events": {
            "by_plugin": dict(sorted(event_by_plugin.items())),
            "by_asset_or_entity": dict(sorted(event_by_entity.items())),
            "by_annotation_key": dict(sorted(event_by_key.items())),
            "by_signal_category": dict(sorted(event_by_category.items())),
            "by_annotation_family": dict(sorted(event_by_family.items())),
            "by_selection_scope": dict(sorted(event_by_scope.items())),
        },
        "indicator_chars_by_temporal_class": dict(sorted(indicator_by_class.items())),
    }


def _detail_independence(
    probes: Sequence[dict[str, Any]],
    identities: Mapping[str, tuple[set[str], set[str]]],
) -> dict[str, Any]:
    groups: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for probe in probes:
        if probe["status"] == "ok":
            groups[
                (
                    probe["request"]["selection"]["id"],
                    probe["effective_period"]["label"],
                )
            ].append(probe)
    comparisons = []
    for (selection, period_label), group in sorted(groups.items()):
        details = sorted(probe["request"]["detail_level"] for probe in group)
        evaluated = len(details) >= 2
        detected_sets = [identities[probe["probe_id"]][0] for probe in group]
        exported_sets = [identities[probe["probe_id"]][1] for probe in group]
        detected_match = all(item == detected_sets[0] for item in detected_sets[1:]) if evaluated else None
        exported_match = all(item == exported_sets[0] for item in exported_sets[1:]) if evaluated else None
        comparisons.append(
            {
                "selection": selection,
                "period": period_label,
                "details_present": details,
                "evaluated": evaluated,
                "detected_identities_match": detected_match,
                "exported_identities_match": exported_match,
                "valid": (detected_match is True and exported_match is True if evaluated else None),
                "optional": selection == FX_SELECTION,
            }
        )
    required_evaluated = [item for item in comparisons if item["evaluated"] and not item["optional"]]
    return {
        "definition": ("Detected and exported event identity sets must remain identical " "across detail levels for the same selection and period."),
        "comparisons": comparisons,
        "required_evaluated_group_count": len(required_evaluated),
        "required_mismatch_count": sum(item["valid"] is False for item in required_evaluated),
        "valid": all(item["valid"] is True for item in required_evaluated),
    }


def _baseline_comparison_summary(probes: Sequence[dict[str, Any]]) -> dict[str, Any]:
    comparisons = {probe["probe_id"]: probe.get("baseline_comparison", {"status": "probe_failed"}) for probe in probes}
    matched = [comparison for comparison in comparisons.values() if comparison.get("status") == "matched"]
    return {
        "matched_probe_count": len(matched),
        "unmatched_or_failed_probe_count": len(comparisons) - len(matched),
        "by_probe_id": comparisons,
        "total_actual_char_reduction_across_matches": sum(item["reductions"]["total_combined_chars"]["absolute_reduction"] for item in matched),
        "total_actual_token_reduction_across_matches": sum(item["reductions"]["total_tokens"]["absolute_reduction"] for item in matched),
    }


async def _run_matrix(
    args: argparse.Namespace,
    baseline_document: Mapping[str, Any],
    baseline_summary: Mapping[str, Any],
    temporal_matrix: Mapping[str, Any],
) -> tuple[dict[str, Any], bool]:
    catalog = AiExportSnapshotService.get_catalog()
    dataset_versions = {entry.id: entry.version for entry in catalog.datasets}
    selections = list(REQUIRED_SELECTIONS)
    if args.fx:
        selections.append(FX_SELECTION)
    all_probe_ids = [_probe_id(selection, detail, period_label) for selection in selections for detail in DETAIL_ORDER for period_label in PERIOD_ORDER]
    selected_probe_ids = [probe_id for probe_id in all_probe_ids if baseline_helpers._selector_matches(probe_id, args.only)]
    if not selected_probe_ids:
        raise ValueError(f"--only selectors matched no probes: {args.only}")
    missing_datasets = [selection for selection in selections if selection not in dataset_versions]
    if missing_datasets:
        raise ValueError("catalog lacks required diagnostic datasets: " + ", ".join(missing_datasets))
    baseline_by_id = {str(probe["probe_id"]): probe for probe in baseline_document["probes"] if isinstance(probe, dict) and "probe_id" in probe}

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await session.execute(select(User).where(User.username == args.username))
        user = result.scalar_one_or_none()
        if user is None or user.id is None:
            raise ValueError(f"test DB user not found: {args.username}")
        service = AiExportSnapshotService(session)
        probes = []
        identities: dict[str, tuple[set[str], set[str]]] = {}
        for selection in selections:
            for detail in DETAIL_ORDER:
                for period_label in PERIOD_ORDER:
                    probe_id = _probe_id(selection, detail, period_label)
                    if probe_id not in selected_probe_ids:
                        continue
                    request = _build_request(
                        selection_id=selection,
                        detail=detail,
                        period=_period(period_label, args.snapshot_as_of),
                        asset_id=args.asset_id,
                        broker_id=args.broker_id,
                        selection_version=dataset_versions[selection],
                        fx_base=args.fx_base,
                        fx_quote=args.fx_quote,
                    )
                    probe, detected_ids, exported_ids = await _run_probe(
                        service=service,
                        user_id=user.id,
                        request=request,
                        probe_id=probe_id,
                        period_label=period_label,
                        baseline_probe=baseline_by_id.get(probe_id),
                    )
                    if probe["status"] == "ok":
                        probe["period_label"] = period_label
                    probes.append(probe)
                    identities[probe_id] = (detected_ids, exported_ids)

    detail_independence = _detail_independence(probes, identities)
    required_failures = [probe["probe_id"] for probe in probes if probe["status"] == "failed" and not probe["optional"]]
    required_validation_failures = [probe["probe_id"] for probe in probes if probe["status"] == "ok" and not probe["optional"] and not probe["validation"]["valid"]]
    optional_fx_failures = [
        {
            "probe_id": probe["probe_id"],
            "error_type": probe["error_type"],
            "message": probe["message"],
            "known_fx_warmup_coupling_nonfatal": probe["known_fx_warmup_coupling_nonfatal"],
        }
        for probe in probes
        if probe["status"] == "failed" and probe["optional"]
    ]
    fatal = not temporal_matrix["valid"] or not baseline_summary["portfolio_full_1y_facts_match"] or bool(required_failures) or bool(required_validation_failures) or not detail_independence["valid"]
    validation_summary = {
        "status": "failed" if fatal else "passed",
        "temporal_policy_matrix_valid": temporal_matrix["valid"],
        "baseline_integrity_valid": baseline_summary["portfolio_full_1y_facts_match"],
        "selected_probe_count": len(selected_probe_ids),
        "required_matrix_probe_count": len(REQUIRED_SELECTIONS) * len(DETAIL_ORDER) * len(PERIOD_ORDER),
        "selected_required_probe_count": sum(probe_id.split(":", 1)[0] in REQUIRED_SELECTIONS for probe_id in selected_probe_ids),
        "optional_fx_matrix_probe_count": len(DETAIL_ORDER) * len(PERIOD_ORDER) if args.fx else 0,
        "selected_optional_fx_probe_count": sum(probe_id.startswith(f"{FX_SELECTION}:") for probe_id in selected_probe_ids),
        "required_probe_failure_count": len(required_failures),
        "required_probe_failures": required_failures,
        "required_probe_validation_failure_count": len(required_validation_failures),
        "required_probe_validation_failures": required_validation_failures,
        "optional_fx_failure_count": len(optional_fx_failures),
        "optional_fx_failures": optional_fx_failures,
        "detail_independence": detail_independence,
        "exit_nonzero": fatal,
    }
    document = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "repository_root": ".",
            "script": _repo_path(Path(__file__)),
            "database_path": _repo_path(get_data_dir() / "sqlite" / "app.db"),
            "baseline_path": baseline_summary["path"],
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "test_mode": True,
            "runtime_service": ("backend.app.services.ai_export.runtime_service." "AiExportSnapshotService"),
            "canonical_serializer": ("backend.app.services.ai_export.telemetry.canonical_json"),
            "catalog_schema_version": catalog.schema_version,
            "catalog_version": catalog.catalog_version,
        },
        "config": {
            "username": args.username,
            "asset_id": args.asset_id,
            "broker_id": args.broker_id,
            "snapshot_as_of": args.snapshot_as_of.isoformat(),
            "target_currency": TARGET_CURRENCY,
            "fx_enabled": args.fx,
            "fx_pair": f"{args.fx_base}/{args.fx_quote}",
            "periods": {
                label: {
                    "start": _period(label, args.snapshot_as_of).start.isoformat(),
                    "end": args.snapshot_as_of.isoformat(),
                    "inclusive_day_count": (_period(label, args.snapshot_as_of).end - _period(label, args.snapshot_as_of).start).days + 1,
                }
                for label in PERIOD_ORDER
            },
            "details": list(DETAIL_ORDER),
            "required_selections": list(REQUIRED_SELECTIONS),
            "optional_selections": [FX_SELECTION] if args.fx else [],
            "only_selectors": list(args.only),
            "selected_probe_ids": selected_probe_ids,
        },
        "baseline_source": dict(baseline_summary),
        "temporal_policy_matrix": dict(temporal_matrix),
        "probes": probes,
        "aggregate_summaries": _aggregate_summaries(probes),
        "baseline_comparison": _baseline_comparison_summary(probes),
        "validation_summary": validation_summary,
    }
    return document, fatal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=("Run deterministic AI Export Signal Density V2 diagnostics against " "the real LibreFolio test SQLite DB."))
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help=("P0 technical-density baseline JSON " f"(default: {_repo_path(DEFAULT_BASELINE)})."),
    )
    parser.add_argument(
        "--snapshot-as-of",
        type=_parse_date,
        default=date(2026, 7, 30),
        help="Inclusive period end (default: 2026-07-30).",
    )
    parser.add_argument(
        "--username",
        default="e2e_test_user",
        help="Test DB username (default: e2e_test_user).",
    )
    parser.add_argument(
        "--asset-id",
        type=int,
        default=1,
        help="Asset target (default: 1).",
    )
    parser.add_argument(
        "--broker-id",
        type=int,
        default=5,
        help="Broker target/scope (default: 5).",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="SELECTION[:DETAIL[:PERIOD]]",
        help=("Run matching probe subset; repeatable. Example: " "--only asset.market_technical:compact:3M."),
    )
    parser.add_argument(
        "--no-fx",
        dest="fx",
        action="store_false",
        help="Disable optional FX market-technical probes.",
    )
    parser.set_defaults(fx=True)
    parser.add_argument(
        "--fx-base",
        default="EUR",
        help="Optional FX base currency (default: EUR).",
    )
    parser.add_argument(
        "--fx-quote",
        default="USD",
        help="Optional FX quote currency (default: USD).",
    )
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.asset_id < 1:
        parser.error("--asset-id must be positive")
    if args.broker_id < 1:
        parser.error("--broker-id must be positive")
    if args.fx_base == args.fx_quote:
        parser.error("--fx-base and --fx-quote must differ")
    allowed_selections = set(REQUIRED_SELECTIONS) | {FX_SELECTION}
    for selector in args.only:
        parts = selector.split(":")
        if len(parts) > 3 or not parts[0]:
            parser.error(f"invalid --only selector: {selector}")
        if parts[0] not in allowed_selections:
            parser.error(f"invalid selection in --only selector: {selector}")
        if parts[0] == FX_SELECTION and not args.fx:
            parser.error("FX selector cannot be used with --no-fx")
        if len(parts) >= 2 and parts[1] not in DETAIL_ORDER:
            parser.error(f"invalid detail in --only selector: {selector}")
        if len(parts) == 3 and parts[2] not in PERIOD_ORDER:
            parser.error(f"invalid period in --only selector: {selector}")


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    _validate_args(parser, args)
    database_path = get_data_dir() / "sqlite" / "app.db"
    if not database_path.is_file():
        parser.error(f"test SQLite DB not found: {_repo_path(database_path)}")
    baseline_path = args.baseline.expanduser()
    if not baseline_path.is_file():
        parser.error(f"baseline JSON not found: {_repo_path(baseline_path)}")
    try:
        baseline_document, baseline_summary = _load_baseline(baseline_path)
        temporal_matrix = _temporal_policy_matrix(args.snapshot_as_of)
        document, failed = asyncio.run(
            _run_matrix(
                args,
                baseline_document,
                baseline_summary,
                temporal_matrix,
            )
        )
    except Exception as exc:
        parser.exit(2, f"fatal: {type(exc).__name__}: {exc}\n")
    rendered = (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {len(document['probes'])} probe(s) to {_repo_path(output_path)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
