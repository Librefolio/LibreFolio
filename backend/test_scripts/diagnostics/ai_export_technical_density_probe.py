#!/usr/bin/env python3
"""Versioned, repeatable technical-density diagnostics for public AI Export."""

from __future__ import annotations

import argparse
import asyncio
import calendar
import copy
import hashlib
import json
import os
import platform
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping, Sequence
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
    AiExportPeriod,
    AiExportPortfolioSnapshotRequest,
    AiExportSnapshotRequest,
)
from backend.app.schemas.common import DateRangeModel  # noqa: E402
from backend.app.schemas.prices import FAPriceQueryItem  # noqa: E402
from backend.app.services.ai_export.components import portfolio_broker_technical  # noqa: E402
from backend.app.services.ai_export.components.technical_shared import (  # noqa: E402
    ASSET_CURATED_SIGNALS,
    build_asset_annotation_requests,
    build_asset_signal_requests,
    signal_results_to_discrete_events,
)
from backend.app.services.ai_export.runtime_service import (  # noqa: E402
    CATALOG_VERSION,
    AiExportSnapshotService,
)
from backend.app.services.ai_export.telemetry import (  # noqa: E402
    canonical_json,
    estimate_tokens_chars_div_4,
)
from backend.app.services.asset_source import AssetSourceManager  # noqa: E402

SCHEMA_VERSION = "1.1.0"
TARGET_CURRENCY = "USD"
PERIOD_ORDER = ("3M", "6M", "1Y")
DETAIL_ORDER = ("compact", "standard", "full")
SELECTION_ORDER = (
    "asset.market_technical",
    "broker.technical",
    "portfolio.technical",
)
PRIMARY_INDICATOR_INSTANCES = frozenset(
    {
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "macd_12_26_9",
    }
)
KNOWN_PRE_FIX_PROBE = {
    "historical": True,
    "label": "known_pre_fix_probe",
    "request": {
        "selection": "portfolio.technical",
        "broker_ids": [5],
        "detail_level": "full",
        "target_currency": "USD",
        "period": {
            "start": "2025-07-31",
            "end": "2026-07-30",
            "inclusive_day_count": 365,
        },
    },
    "facts": {
        "asset_count": 3,
        "indicators_per_asset": 20,
        "bucket_count": 75,
        "event_count": 1639,
        "serialized_characters": 2665012,
        "estimated_tokens": 666253,
        "token_estimation_method": "chars_div_4_v1",
    },
}


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from exc


def _subtract_calendar_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def _period(label: str, snapshot_as_of: date) -> AiExportPeriod:
    months = {"3M": 3, "6M": 6, "1Y": 12}[label]
    start = _subtract_calendar_months(snapshot_as_of, months) + timedelta(days=1)
    return AiExportPeriod(start=start, end=snapshot_as_of)


def _canonical_fragment(value: Any) -> str:
    wrapped = canonical_json({"_": value})
    return wrapped[5:-1]


def _serialized_chars(value: Any) -> int:
    return len(_canonical_fragment(value))


def _percent(part: int, whole: int) -> float:
    return round((part / whole * 100.0) if whole else 0.0, 6)


def _size_metrics(payload: Mapping[str, Any]) -> dict[str, Any]:
    serialized = canonical_json(payload)
    chars = len(serialized)
    return {
        "chars": chars,
        "utf8_bytes": len(serialized.encode("utf-8")),
        "estimated_tokens": estimate_tokens_chars_div_4(chars),
        "token_estimation_method": "chars_div_4_v1",
    }


def _walk(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _walk(item, (*path, str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, (*path, str(index)))


def _count_lists_for_keys(value: Any, keys: set[str]) -> int:
    total = 0
    for path, item in _walk(value):
        if path and path[-1] in keys and isinstance(item, list):
            total += len(item)
    return total


def _max_list_for_keys(value: Any, keys: set[str]) -> int:
    lengths = [len(item) for path, item in _walk(value) if path and path[-1] in keys and isinstance(item, list)]
    return max(lengths, default=0)


def _field_measurement(value: Any, key_tokens: Sequence[str]) -> dict[str, Any]:
    matches: list[tuple[str, Any]] = []
    lowered = tuple(token.lower() for token in key_tokens)
    for path, item in _walk(value):
        if not path:
            continue
        key = path[-1].lower()
        if any(token in key for token in lowered) and item not in (None, "", [], {}):
            matches.append((path[-1], item))
    chars = sum(_serialized_chars({key: item}) for key, item in matches)
    return {
        "present": bool(matches),
        "count": len(matches),
        "chars": chars,
    }


def _section_category(component_id: str) -> str:
    if "indicators" in component_id:
        return "indicators"
    if "events" in component_id or "states_events" in component_id:
        return "events"
    if "breadth" in component_id:
        return "breadth"
    if any(token in component_id for token in ("technical_prices", "ohlc_returns", "rate_ohlc", "returns_volatility")):
        return "technical_prices"
    if any(token in component_id for token in ("provenance", "diagnostic", "reconciliation")):
        return "provenance_diagnostics"
    return "other"


def _component_measurements(response: dict[str, Any], total_chars: int) -> dict[str, Any]:
    sections = response.get("sections", [])
    skeleton = copy.deepcopy(response)
    skeleton["sections"] = []
    top_level_chars = _serialized_chars(skeleton)
    components: list[dict[str, Any]] = []
    category_chars: Counter[str] = Counter()
    section_chars_total = 0
    for section in sections:
        chars = _serialized_chars(section)
        section_chars_total += chars
        category = _section_category(str(section.get("component_id", "")))
        category_chars[category] += chars
        payload = section.get("payload", {})
        element_counts = {
            "assets": _count_lists_for_keys(payload, {"assets"}),
            "indicators": _count_lists_for_keys(payload, {"indicators"}),
            "rows": _count_lists_for_keys(payload, {"rows"}),
            "buckets": _count_lists_for_keys(payload, {"buckets"}),
            "events": _count_lists_for_keys(payload, {"events"}),
            "states": _count_lists_for_keys(payload, {"states"}),
        }
        denominator = max(element_counts.values(), default=0)
        components.append(
            {
                "component_id": section.get("component_id"),
                "category": category,
                "chars": chars,
                "percent_of_total": _percent(chars, total_chars),
                "element_counts": element_counts,
                "average_chars_per_largest_collection_element": (round(chars / denominator, 3) if denominator else None),
            }
        )
    wrapper_chars = total_chars - top_level_chars - section_chars_total
    categories = {
        key: {
            "chars": category_chars.get(key, 0),
            "percent_of_total": _percent(category_chars.get(key, 0), total_chars),
        }
        for key in ("technical_prices", "indicators", "events", "breadth", "provenance_diagnostics", "other")
    }
    categories["top_level_metadata_manifest"] = {
        "chars": top_level_chars,
        "percent_of_total": _percent(top_level_chars, total_chars),
    }
    categories["wrapper_unattributed_overhead"] = {
        "chars": wrapper_chars,
        "percent_of_total": _percent(wrapper_chars, total_chars),
    }
    reconciled = top_level_chars + section_chars_total + wrapper_chars
    return {
        "measurement_definition": "Canonical chars of top-level response with empty sections plus each canonical section. Cross-cutting fields overlap component blocks and are reported separately.",
        "categories": categories,
        "components": components,
        "cross_cutting": {
            "semantic_descriptions": _field_measurement(response, ("semantic_description",)),
            "provenance_diagnostics": _field_measurement(response, ("provenance", "diagnostic", "warning")),
        },
        "reconciliation": {
            "total_chars": total_chars,
            "reconciled_chars": reconciled,
            "matches": reconciled == total_chars,
        },
    }


def _iter_indicator_instances(response: dict[str, Any]) -> Iterator[tuple[str, int | None, dict[str, Any]]]:
    target = response.get("target", {})
    target_asset_id = target.get("asset_id") if target.get("kind") == "asset" else None
    for section in response.get("sections", []):
        component_id = str(section.get("component_id", ""))
        payload = section.get("payload", {})
        indicators = payload.get("indicators")
        if isinstance(indicators, list):
            for indicator in indicators:
                if isinstance(indicator, dict):
                    yield component_id, target_asset_id, indicator
        assets = payload.get("assets")
        if isinstance(assets, list):
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                for indicator in asset.get("indicators", []):
                    if isinstance(indicator, dict):
                        yield component_id, asset.get("asset_id"), indicator


def _indicator_measurements(response: dict[str, Any], total_chars: int) -> list[dict[str, Any]]:
    measurements = []
    for component_id, asset_id, indicator in _iter_indicator_instances(response):
        full_chars = _serialized_chars(indicator)
        without_rows = {key: value for key, value in indicator.items() if key != "rows"}
        scalar_metadata = {key: value for key, value in indicator.items() if key not in {"rows", "columns"}}
        columns = indicator.get("columns", [])
        static_columns = [{key: value for key, value in column.items() if key != "latest"} for column in columns if isinstance(column, dict)]
        latest_columns = [{"column_key": column.get("column_key"), "latest": column.get("latest")} for column in columns if isinstance(column, dict) and column.get("latest") is not None]
        rows = indicator.get("rows", [])
        output_keys = {column.get("output_key") for column in columns if isinstance(column, dict) and column.get("output_key") is not None}
        measurements.append(
            {
                "component_id": component_id,
                "asset_id": asset_id,
                "signal_code": indicator.get("signal_code"),
                "instance_id": indicator.get("instance_id"),
                "output_count": len(output_keys),
                "column_count": len(columns),
                "row_count": len(rows),
                "full_serialized_chars": full_chars,
                "metadata_chars_without_rows": _serialized_chars(without_rows),
                "scalar_metadata_chars_without_columns_or_rows": _serialized_chars(scalar_metadata),
                "column_definition_chars_without_latest": _serialized_chars(static_columns),
                "column_latest_state_chars": _serialized_chars(latest_columns),
                "row_history_chars": _serialized_chars(rows),
                "percent_of_indicator_component": None,
                "percent_of_total": _percent(full_chars, total_chars),
                "description": _field_measurement(indicator, ("description",)),
                "params": _field_measurement(indicator, ("params", "parameters")),
                "reference": _field_measurement(indicator, ("reference",)),
                "warning": _field_measurement(indicator, ("warning",)),
                "diagnostic": _field_measurement(indicator, ("diagnostic",)),
            }
        )
    component_totals: Counter[str] = Counter()
    for section in response.get("sections", []):
        component_totals[str(section.get("component_id", ""))] = _serialized_chars(section)
    for measurement in measurements:
        measurement["percent_of_indicator_component"] = _percent(
            measurement["full_serialized_chars"],
            component_totals[measurement["component_id"]],
        )
    return measurements


def _iter_events(response: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for section in response.get("sections", []):
        component_id = str(section.get("component_id", ""))
        payload = section.get("payload", {})
        buckets = payload.get("buckets")
        if not isinstance(buckets, list):
            continue
        for bucket in buckets:
            if not isinstance(bucket, dict) or not isinstance(bucket.get("events"), list):
                continue
            bucket_key = f"{component_id}:{bucket.get('start_date')}:{bucket.get('end_date')}"
            for event in bucket["events"]:
                if isinstance(event, dict):
                    yield component_id, bucket_key, event


def _event_measurements(response: dict[str, Any]) -> dict[str, Any]:
    target = response.get("target", {})
    fallback_asset_id = target.get("asset_id") if target.get("kind") == "asset" else None
    events = list(_iter_events(response))
    by_signal: Counter[str] = Counter()
    by_asset: Counter[str] = Counter()
    by_key: Counter[str] = Counter()
    by_bucket: Counter[str] = Counter()
    full_fingerprints: Counter[str] = Counter()
    semantic_fingerprints: Counter[str] = Counter()
    semantic_to_full: defaultdict[str, set[str]] = defaultdict(set)
    event_chars = 0
    description_chars = 0
    for _component_id, bucket_key, event in events:
        signal_code = str(event.get("signal_code"))
        asset_id = event.get("asset_id", fallback_asset_id)
        annotation_key = str(event.get("key"))
        by_signal[signal_code] += 1
        by_asset[str(asset_id)] += 1
        by_key[annotation_key] += 1
        by_bucket[bucket_key] += 1
        full = _canonical_fragment(event)
        semantic_event = {key: value for key, value in event.items() if key != "semantic_description"}
        semantic = _canonical_fragment(semantic_event)
        full_fingerprints[full] += 1
        semantic_fingerprints[semantic] += 1
        semantic_to_full[semantic].add(full)
        event_chars += len(full)
        if event.get("semantic_description") is not None:
            description_chars += _serialized_chars(event["semantic_description"])
    exact_duplicates = sum(count - 1 for count in full_fingerprints.values() if count > 1)
    semantic_beyond_first = sum(count - 1 for count in semantic_fingerprints.values() if count > 1)
    semantic_non_exact_variants = sum(max(len(fulls) - 1, 0) for fulls in semantic_to_full.values())
    return {
        "total": len(events),
        "by_signal_plugin": dict(sorted(by_signal.items())),
        "by_asset": dict(sorted(by_asset.items())),
        "by_annotation_key": dict(sorted(by_key.items())),
        "by_bucket": dict(sorted(by_bucket.items())),
        "average_chars_per_event": (round(event_chars / len(events), 3) if events else None),
        "description_chars": description_chars,
        "exact_duplicate_events": exact_duplicates,
        "semantic_equivalent_events_beyond_first": semantic_beyond_first,
        "semantic_equivalent_non_exact_variants": semantic_non_exact_variants,
        "semantic_equivalence_definition": "Canonical event equality after removing only semantic_description; exact duplicates use the full canonical event.",
    }


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_fragment(value).encode("utf-8")).hexdigest()


def _policy_annotations(*, observed_only: bool, epsilon: float, relative_epsilon: float) -> list[Any]:
    return [
        annotation.model_copy(
            update={
                "observed_only": observed_only,
                "epsilon": epsilon,
                "relative_epsilon": relative_epsilon,
            }
        )
        for annotation in build_asset_annotation_requests()
    ]


def _event_policy_summary(events: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_key = Counter(str(event.get("key")) for event in events)
    by_signal = Counter(str(event.get("signal_code")) for event in events)
    weekend_events = [event for event in events if date.fromisoformat(str(event["date"])).weekday() >= 5]
    value_candidates = [(abs(float(value)), event) for event in events for value in event.get("values", {}).values() if isinstance(value, (int, float)) and value != 0]
    smallest = min(value_candidates, key=lambda item: item[0], default=None)
    return {
        "total_events": len(events),
        "weekend_events": len(weekend_events),
        "counts_by_annotation_key": dict(sorted(by_key.items())),
        "counts_by_signal": dict(sorted(by_signal.items())),
        "smallest_absolute_nonzero_event_value": (smallest[0] if smallest is not None else None),
        "smallest_absolute_nonzero_event": (smallest[1] if smallest is not None else None),
    }


def _event_policy_delta(before: Sequence[dict[str, Any]], after: Sequence[dict[str, Any]]) -> dict[str, Any]:
    before_by_fingerprint = {_canonical_fragment(event): event for event in before}
    after_by_fingerprint = {_canonical_fragment(event): event for event in after}
    before_counts = Counter(_canonical_fragment(event) for event in before)
    after_counts = Counter(_canonical_fragment(event) for event in after)
    removed_counts = before_counts - after_counts
    added_counts = after_counts - before_counts
    removed = [before_by_fingerprint[fingerprint] for fingerprint, count in removed_counts.items() for _ in range(count)]
    added = [after_by_fingerprint[fingerprint] for fingerprint, count in added_counts.items() for _ in range(count)]
    removed_summary = _event_policy_summary(removed)
    added_summary = _event_policy_summary(added)
    before_weekends = sum(date.fromisoformat(str(event["date"])).weekday() >= 5 for event in before)
    after_weekends = sum(date.fromisoformat(str(event["date"])).weekday() >= 5 for event in after)
    return {
        "before_total": len(before),
        "after_total": len(after),
        "total_delta_after_minus_before": len(after) - len(before),
        "before_weekend_events": before_weekends,
        "after_weekend_events": after_weekends,
        "weekend_delta_after_minus_before": after_weekends - before_weekends,
        "removed_events": removed_summary,
        "added_events": added_summary,
    }


async def _run_annotation_policy_diagnostic(session: AsyncSession, *, asset_id: int, snapshot_as_of: date) -> dict[str, Any]:
    period = _period("1Y", snapshot_as_of)
    current_annotations = list(build_asset_annotation_requests())
    absolute_epsilons = sorted({float(annotation.epsilon) for annotation in current_annotations})
    relative_epsilons = sorted({float(annotation.relative_epsilon) for annotation in current_annotations})
    policies = (
        {
            "name": "legacy_unobserved_zero_epsilon",
            "observed_only": False,
            "absolute_epsilon": 0.0,
            "relative_epsilon": 0.0,
            "annotations": _policy_annotations(
                observed_only=False,
                epsilon=0.0,
                relative_epsilon=0.0,
            ),
        },
        {
            "name": "observed_only_zero_epsilon",
            "observed_only": True,
            "absolute_epsilon": 0.0,
            "relative_epsilon": 0.0,
            "annotations": _policy_annotations(
                observed_only=True,
                epsilon=0.0,
                relative_epsilon=0.0,
            ),
        },
        {
            "name": "current_observed_only_configured_epsilon",
            "observed_only": True,
            "absolute_epsilon": absolute_epsilons,
            "relative_epsilon": relative_epsilons,
            "annotations": current_annotations,
        },
    )
    requests = [
        FAPriceQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=period.start, end=period.end),
            include_price=True,
            include_events=False,
            target_currency=None,
            signals=list(build_asset_signal_requests()),
            annotation_requests=policy["annotations"],
        )
        for policy in policies
    ]
    results = await AssetSourceManager.get_prices_bulk(requests, session)
    if len(results) != len(policies):
        raise RuntimeError(f"annotation policy diagnostic expected {len(policies)} results, got {len(results)}")

    policy_events: dict[str, list[dict[str, Any]]] = {}
    policy_summaries: dict[str, Any] = {}
    price_fingerprints: dict[str, str] = {}
    indicator_fingerprints: dict[str, str] = {}
    for policy, result in zip(policies, results, strict=True):
        name = policy["name"]
        events = []
        seen_event_keys = set()
        for event in signal_results_to_discrete_events(
            result.signals,
            entity_id=f"asset:{asset_id}",
            asset_id=asset_id,
        ):
            if event.dedup_key in seen_event_keys:
                continue
            seen_event_keys.add(event.dedup_key)
            events.append(
                json.loads(
                    _canonical_fragment(
                        {
                            "date": event.date.isoformat(),
                            **event.payload,
                        }
                    )
                )
            )
        policy_events[name] = events
        price_fingerprints[name] = _sha256([point.model_dump(mode="json") for point in result.prices])
        indicator_fingerprints[name] = _sha256([{key: value for key, value in signal.model_dump(mode="json").items() if key != "annotations"} for signal in result.signals])
        policy_summaries[name] = {
            "policy": {
                "observed_only": policy["observed_only"],
                "absolute_epsilon": policy["absolute_epsilon"],
                "relative_epsilon": policy["relative_epsilon"],
            },
            "price_input_sha256": price_fingerprints[name],
            "indicator_output_without_annotations_sha256": indicator_fingerprints[name],
            **_event_policy_summary(events),
        }

    price_inputs_identical = len(set(price_fingerprints.values())) == 1
    indicator_outputs_identical = len(set(indicator_fingerprints.values())) == 1
    if not price_inputs_identical or not indicator_outputs_identical:
        raise RuntimeError("annotation policy comparison changed price input or indicator output")

    legacy_name, observed_name, current_name = (policy["name"] for policy in policies)
    historical_total = 517
    historical_weekends = 52
    historical_near_zero = 7e-15
    legacy_summary = policy_summaries[legacy_name]
    return {
        "status": "ok",
        "asset_id": asset_id,
        "period": {
            "start": period.start.isoformat(),
            "end": period.end.isoformat(),
            "inclusive_day_count": (period.end - period.start).days + 1,
        },
        "historical_reference": {
            "label": "historical_aapl_pre_fix",
            "total_events": historical_total,
            "weekend_events": historical_weekends,
            "near_zero_event_value_approx": historical_near_zero,
        },
        "historical_reference_comparison": {
            "legacy_total_event_delta": legacy_summary["total_events"] - historical_total,
            "legacy_weekend_event_delta": legacy_summary["weekend_events"] - historical_weekends,
            "legacy_smallest_value_absolute_difference_from_approx": (abs(legacy_summary["smallest_absolute_nonzero_event_value"] - historical_near_zero) if legacy_summary["smallest_absolute_nonzero_event_value"] is not None else None),
        },
        "execution": {
            "loader": "AssetSourceManager.get_prices_bulk",
            "signal_service": "current SignalService via loader execution plan",
            "event_projection": "signal_results_to_discrete_events",
            "single_batched_db_load": True,
            "native_prices": True,
            "curated_signal_instance_count": len(ASSET_CURATED_SIGNALS),
            "annotation_request_count": len(current_annotations),
            "configured_observed_only_values": sorted({bool(annotation.observed_only) for annotation in current_annotations}),
            "configured_absolute_epsilon_values": absolute_epsilons,
            "configured_relative_epsilon_values": relative_epsilons,
        },
        "input_invariants": {
            "price_inputs_identical": price_inputs_identical,
            "indicator_outputs_without_annotations_identical": indicator_outputs_identical,
            "price_input_sha256": next(iter(price_fingerprints.values())),
            "indicator_output_without_annotations_sha256": next(iter(indicator_fingerprints.values())),
        },
        "policies": policy_summaries,
        "attributable_deltas": {
            "observed_only": {
                "comparison": f"{legacy_name} -> {observed_name}",
                **_event_policy_delta(
                    policy_events[legacy_name],
                    policy_events[observed_name],
                ),
            },
            "epsilon": {
                "comparison": f"{observed_name} -> {current_name}",
                **_event_policy_delta(
                    policy_events[observed_name],
                    policy_events[current_name],
                ),
            },
        },
    }


def _collect_asset_ids(response: dict[str, Any]) -> set[int]:
    asset_ids: set[int] = set()
    target = response.get("target", {})
    if isinstance(target.get("asset_id"), int):
        asset_ids.add(target["asset_id"])
    for path, item in _walk(response):
        if path and path[-1] == "asset_id" and isinstance(item, int):
            asset_ids.add(item)
    return asset_ids


def _row_value_candidates(cell: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if cell.get("kind") == "single":
        point = {"value": cell.get("value"), "date": cell.get("date")}
        return {"first": point, "min": point, "max": point, "last": point}
    if cell.get("kind") == "range":
        return {
            "first": cell.get("first"),
            "min": cell.get("min"),
            "max": cell.get("max"),
            "last": cell.get("last"),
        }
    return {}


def _period_summary(indicator: dict[str, Any]) -> dict[str, Any]:
    rows = indicator.get("rows", [])
    columns = indicator.get("columns", [])
    summary_columns: dict[str, Any] = {}
    for column in columns:
        if not isinstance(column, dict):
            continue
        key = column.get("column_key")
        if not isinstance(key, str):
            continue
        first = minimum = maximum = last = None
        observation_count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            cell = row.get("cells", {}).get(key)
            if not isinstance(cell, dict):
                continue
            candidates = _row_value_candidates(cell)
            if not candidates:
                continue
            observation_count += 1 if cell.get("kind") == "single" else int(cell.get("observation_count", 0))
            first = first or candidates["first"]
            last = candidates["last"]
            candidate_min = candidates["min"]
            candidate_max = candidates["max"]
            if candidate_min is not None and (minimum is None or candidate_min["value"] < minimum["value"]):
                minimum = candidate_min
            if candidate_max is not None and (maximum is None or candidate_max["value"] > maximum["value"]):
                maximum = candidate_max
        summary_columns[key] = {
            "observation_count": observation_count,
            "first": first,
            "min": minimum,
            "max": maximum,
            "last": last,
        }
    return {
        "period_start": (rows[0].get("start_date") if rows else None),
        "period_end": (rows[-1].get("end_date") if rows else None),
        "columns": summary_columns,
    }


def _latest_state(indicator: dict[str, Any]) -> dict[str, Any]:
    return {column.get("column_key"): column.get("latest") for column in indicator.get("columns", []) if isinstance(column, dict) and column.get("column_key") is not None}


def _iter_indicator_refs(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if {"instance_id", "signal_code", "columns", "rows"}.issubset(value):
            yield value
        for item in value.values():
            yield from _iter_indicator_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_indicator_refs(item)


def _count_indicator_rows(value: Any) -> int:
    return _count_lists_for_keys(value, {"rows"})


def _count_events(value: Any) -> int:
    return sum(1 for path, item in _walk(value) if path and path[-1] == "events" and isinstance(item, list) for _event in item)


def _simulation_metrics(
    *,
    name: str,
    payload: dict[str, Any],
    baseline_chars: int,
    baseline_rows: int,
    baseline_events: int,
    note: dict[str, Any],
) -> dict[str, Any]:
    metrics = _size_metrics(payload)
    rows = _count_indicator_rows(payload)
    events = _count_events(payload)
    return {
        "name": name,
        **metrics,
        "reduction_percent": round((1.0 - metrics["chars"] / baseline_chars) * 100.0, 6) if baseline_chars else 0.0,
        "indicator_rows_retained": rows,
        "indicator_row_retention_percent": _percent(rows, baseline_rows),
        "events_retained": events,
        "event_retention_percent": _percent(events, baseline_events),
        "information_retention": note,
    }


def _simulate_last_rows(response: dict[str, Any], count: int) -> dict[str, Any]:
    simulated = copy.deepcopy(response)
    for indicator in _iter_indicator_refs(simulated):
        indicator["period_summary"] = _period_summary(indicator)
        indicator["rows"] = indicator.get("rows", [])[-count:]
    return simulated


def _simulate_primary_history(response: dict[str, Any]) -> dict[str, Any]:
    simulated = copy.deepcopy(response)
    for indicator in _iter_indicator_refs(simulated):
        if indicator.get("instance_id") in PRIMARY_INDICATOR_INSTANCES:
            continue
        indicator["period_summary"] = _period_summary(indicator)
        indicator.pop("rows", None)
    return simulated


def _simulate_shared_metadata(response: dict[str, Any]) -> dict[str, Any]:
    simulated = copy.deepcopy(response)
    shared: dict[str, Any] = {}
    fingerprint_to_ref: dict[str, str] = {}
    for indicator in _iter_indicator_refs(simulated):
        static_columns = [{key: value for key, value in column.items() if key != "latest"} for column in indicator.get("columns", [])]
        metadata = {key: value for key, value in indicator.items() if key not in {"rows", "columns"}}
        metadata["columns"] = static_columns
        fingerprint = _canonical_fragment(metadata)
        reference = fingerprint_to_ref.get(fingerprint)
        if reference is None:
            reference = f"{indicator.get('signal_code')}:{indicator.get('instance_id')}"
            if reference in shared:
                reference = f"{reference}:{len(shared) + 1}"
            fingerprint_to_ref[fingerprint] = reference
            shared[reference] = metadata
        replacement = {
            "metadata_ref": reference,
            "latest_state": _latest_state(indicator),
            "rows": indicator.get("rows", []),
        }
        indicator.clear()
        indicator.update(replacement)
    simulated["diagnostic_shared_indicator_metadata"] = shared
    return simulated


def _simulate_latest_summary_events(response: dict[str, Any]) -> dict[str, Any]:
    simulated = copy.deepcopy(response)
    for indicator in _iter_indicator_refs(simulated):
        indicator["period_summary"] = _period_summary(indicator)
        indicator.pop("rows", None)
    return simulated


def _simulation_results(response: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = copy.deepcopy(response)
    baseline_metrics = _size_metrics(baseline)
    baseline_rows = _count_indicator_rows(baseline)
    baseline_events = _count_events(baseline)
    results = [
        _simulation_metrics(
            name="A_baseline_full_history",
            payload=baseline,
            baseline_chars=baseline_metrics["chars"],
            baseline_rows=baseline_rows,
            baseline_events=baseline_events,
            note={
                "strategy": "unaltered_baseline",
                "indicator_history": "full",
                "events": "full",
                "baseline_response_mutated": False,
            },
        )
    ]
    for count in (1, 3, 5, 10, 15):
        results.append(
            _simulation_metrics(
                name=f"B_last_{count}_indicator_rows",
                payload=_simulate_last_rows(response, count),
                baseline_chars=baseline_metrics["chars"],
                baseline_rows=baseline_rows,
                baseline_events=baseline_events,
                note={
                    "strategy": "last_n_rows_plus_period_summary_and_latest",
                    "last_n_rows": count,
                    "period_summary": "first/min/max/last with dates when derivable",
                    "latest_state": "retained in existing column latest values",
                    "events": "untouched",
                },
            )
        )
    results.append(
        _simulation_metrics(
            name="C_primary_full_secondary_summary",
            payload=_simulate_primary_history(response),
            baseline_chars=baseline_metrics["chars"],
            baseline_rows=baseline_rows,
            baseline_events=baseline_events,
            note={
                "strategy": "primary_full_history_secondary_summary_latest",
                "primary_instance_ids": sorted(PRIMARY_INDICATOR_INSTANCES),
                "primary_set_rationale": "Long/medium/short trend regime plus RSI momentum and MACD momentum/crossover coverage; explicit candidate, not public policy.",
                "secondary_history": "removed; period summary and latest retained",
                "latest_state": "retained in existing column latest values",
                "events": "untouched",
            },
        )
    )
    results.append(
        _simulation_metrics(
            name="D_shared_indicator_metadata",
            payload=_simulate_shared_metadata(response),
            baseline_chars=baseline_metrics["chars"],
            baseline_rows=baseline_rows,
            baseline_events=baseline_events,
            note={
                "strategy": "hoist_identical_static_indicator_metadata",
                "asset_instances": "metadata_ref plus latest state and full rows",
                "events": "untouched",
            },
        )
    )
    results.append(
        _simulation_metrics(
            name="E_latest_period_statistics_full_events",
            payload=_simulate_latest_summary_events(response),
            baseline_chars=baseline_metrics["chars"],
            baseline_rows=baseline_rows,
            baseline_events=baseline_events,
            note={
                "strategy": "latest_plus_period_statistics_without_detailed_indicator_history",
                "indicator_history": "removed",
                "period_summary": "first/min/max/last with dates when derivable",
                "latest_state": "retained in existing column latest values",
                "events": "full",
            },
        )
    )
    return results


def _probe_id(selection: str, detail: str, period_label: str) -> str:
    return f"{selection}:{detail}:{period_label}"


def _selector_matches(probe_id: str, selectors: Sequence[str]) -> bool:
    if not selectors:
        return True
    probe_parts = probe_id.split(":")
    for selector in selectors:
        selector_parts = selector.split(":")
        if len(selector_parts) <= len(probe_parts) and probe_parts[: len(selector_parts)] == selector_parts:
            return True
    return False


def _build_request(
    *,
    selection_id: str,
    detail: str,
    period: AiExportPeriod,
    asset_id: int,
    broker_id: int,
    selection_version: int,
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
    return AiExportPortfolioSnapshotRequest(domain="portfolio", broker_ids=[broker_id], **common)


def _position_measurements(captured_bundles: Sequence[Any]) -> dict[str, Any]:
    if not captured_bundles:
        return {
            "positions_count": 0,
            "duplicate_asset_legs_across_brokers": 0,
            "measurement_source": "not_applicable_to_single_asset_market_technical_response",
        }
    bundle = captured_bundles[-1]
    positions = tuple(bundle.positions)
    counts = Counter(position.asset_id for position in positions)
    duplicate_legs = sum(max(count - 1, 0) for count in counts.values())
    return {
        "positions_count": len(positions),
        "duplicate_asset_legs_across_brokers": duplicate_legs,
        "measurement_source": "instrumented current load_technical_universe_bundle return; helper delegated unchanged",
    }


async def _run_probe(
    *,
    service: AiExportSnapshotService,
    user_id: int,
    request: AiExportSnapshotRequest,
    probe_id: str,
    period_label: str,
) -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
    started = time.perf_counter()
    captured_bundles: list[Any] = []
    original_loader = portfolio_broker_technical.load_technical_universe_bundle

    async def _capturing_loader(*args, **kwargs):
        bundle = await original_loader(*args, **kwargs)
        captured_bundles.append(bundle)
        return bundle

    portfolio_broker_technical.load_technical_universe_bundle = _capturing_loader
    try:
        prepared = await service.prepare_request(user_id, request)
        response_model = await service.build_snapshot(user_id, request)
    except Exception as exc:
        return (
            {
                "probe_id": probe_id,
                "status": "failed",
                "request": request.model_dump(mode="json"),
                "period_label": period_label,
                "inclusive_day_count": (request.period.end - request.period.start).days + 1,
                "duration_seconds": round(time.perf_counter() - started, 6),
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
            None,
        )
    finally:
        portfolio_broker_technical.load_technical_universe_bundle = original_loader

    response = response_model.model_dump(mode="json")
    canonical = canonical_json(response)
    chars = len(canonical)
    indicators = _indicator_measurements(response, chars)
    events = _event_measurements(response)
    asset_ids = _collect_asset_ids(response)
    position_metrics = _position_measurements(captured_bundles)
    requested_per_asset = len(ASSET_CURATED_SIGNALS)
    requested_total = requested_per_asset * len(asset_ids)
    bucket_count = max(_max_list_for_keys(section.get("payload", {}), {"buckets", "rows"}) for section in response.get("sections", []))
    counts = {
        "bucket_count": bucket_count,
        "bucket_rows_total": _count_lists_for_keys(response.get("sections", []), {"buckets", "rows"}),
        "event_count": events["total"],
        "indicators_requested_per_asset": requested_per_asset,
        "indicators_requested_total": requested_total,
        "indicators_exported_total": len(indicators),
        "indicators_exported_unique_instances": len({item["instance_id"] for item in indicators}),
        "asset_count": len(asset_ids),
        "broker_count": len(prepared.broker_scope),
        **position_metrics,
    }
    probe = {
        "probe_id": probe_id,
        "status": "ok",
        "request": request.model_dump(mode="json"),
        "resolved_broker_scope": list(prepared.broker_scope),
        "period_label": period_label,
        "period": {
            "start": request.period.start.isoformat(),
            "end": request.period.end.isoformat(),
            "inclusive_day_count": (request.period.end - request.period.start).days + 1,
        },
        "duration_seconds": round(time.perf_counter() - started, 6),
        "canonical_response": {
            "chars": chars,
            "utf8_bytes": len(canonical.encode("utf-8")),
            "estimated_tokens": estimate_tokens_chars_div_4(chars),
            "token_estimation_method": "chars_div_4_v1",
            "runtime_reported_chars": response.get("stats", {}).get("serialized_characters"),
            "runtime_reported_tokens": response.get("stats", {}).get("estimated_tokens"),
        },
        "counts": counts,
        "sections": _component_measurements(response, chars),
        "indicators": indicators,
        "events": events,
    }
    return probe, _simulation_results(response)


def _aggregate_group(successes: Sequence[dict[str, Any]], key_getter) -> dict[str, Any]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for probe in successes:
        grouped[str(key_getter(probe))].append(probe)
    output = {}
    for key, probes in sorted(grouped.items()):
        chars = [probe["canonical_response"]["chars"] for probe in probes]
        events = [probe["counts"]["event_count"] for probe in probes]
        rows = [probe["counts"]["bucket_rows_total"] for probe in probes]
        output[key] = {
            "probe_count": len(probes),
            "chars": {
                "min": min(chars),
                "max": max(chars),
                "average": round(sum(chars) / len(chars), 3),
                "total": sum(chars),
            },
            "events": {
                "min": min(events),
                "max": max(events),
                "average": round(sum(events) / len(events), 3),
                "total": sum(events),
            },
            "bucket_rows_total": sum(rows),
        }
    return output


def _aggregate_summaries(probes: Sequence[dict[str, Any]]) -> dict[str, Any]:
    successes = [probe for probe in probes if probe["status"] == "ok"]
    failures = [probe for probe in probes if probe["status"] == "failed"]
    if not successes:
        return {
            "probe_count": len(probes),
            "success_count": 0,
            "failure_count": len(failures),
            "failed_probe_ids": [probe["probe_id"] for probe in failures],
        }
    return {
        "probe_count": len(probes),
        "success_count": len(successes),
        "failure_count": len(failures),
        "failed_probe_ids": [probe["probe_id"] for probe in failures],
        "overall": _aggregate_group(successes, lambda _probe: "all")["all"],
        "by_selection": _aggregate_group(successes, lambda probe: probe["request"]["selection"]["id"]),
        "by_detail_level": _aggregate_group(successes, lambda probe: probe["request"]["detail_level"]),
        "by_period": _aggregate_group(successes, lambda probe: probe["period_label"]),
    }


async def _run_matrix(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    catalog = AiExportSnapshotService.get_catalog()
    dataset_versions = {entry.id: entry.version for entry in catalog.datasets}
    all_probe_ids = [_probe_id(selection, detail, period_label) for selection in SELECTION_ORDER for detail in DETAIL_ORDER for period_label in PERIOD_ORDER]
    selected_probe_ids = [probe_id for probe_id in all_probe_ids if _selector_matches(probe_id, args.only)]
    if not selected_probe_ids:
        raise ValueError(f"--only selectors matched no probes: {args.only}")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await session.execute(select(User).where(User.username == args.username))
        user = result.scalar_one_or_none()
        if user is None or user.id is None:
            raise ValueError(f"test DB user not found: {args.username}")
        service = AiExportSnapshotService(session)
        probes: list[dict[str, Any]] = []
        simulations: list[dict[str, Any]] = []
        for selection in SELECTION_ORDER:
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
                    )
                    probe, probe_simulations = await _run_probe(
                        service=service,
                        user_id=user.id,
                        request=request,
                        probe_id=probe_id,
                        period_label=period_label,
                    )
                    probes.append(probe)
                    if probe_simulations is not None:
                        simulations.append(
                            {
                                "probe_id": probe_id,
                                "variants": probe_simulations,
                            }
                        )
        try:
            annotation_policy_diagnostic = await _run_annotation_policy_diagnostic(
                session,
                asset_id=args.asset_id,
                snapshot_as_of=args.snapshot_as_of,
            )
        except Exception as exc:
            annotation_policy_diagnostic = {
                "status": "failed",
                "asset_id": args.asset_id,
                "period": {
                    "start": _period("1Y", args.snapshot_as_of).start.isoformat(),
                    "end": args.snapshot_as_of.isoformat(),
                    "inclusive_day_count": (_period("1Y", args.snapshot_as_of).end - _period("1Y", args.snapshot_as_of).start).days + 1,
                },
                "error_type": type(exc).__name__,
                "message": str(exc),
            }

    document = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "repository_root": ".",
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "test_mode": True,
            "database_path": str((get_data_dir() / "sqlite" / "app.db").relative_to(REPOSITORY_ROOT)),
            "runtime_service": "backend.app.services.ai_export.runtime_service.AiExportSnapshotService",
            "canonical_serializer": "backend.app.services.ai_export.telemetry.canonical_json",
            "catalog": {
                "schema_version": catalog.schema_version,
                "catalog_version": catalog.catalog_version,
                "dataset_count": len(catalog.datasets),
                "analysis_count": len(catalog.analyses),
            },
        },
        "config": {
            "username": args.username,
            "asset_id": args.asset_id,
            "broker_id": args.broker_id,
            "snapshot_as_of": args.snapshot_as_of.isoformat(),
            "target_currency": TARGET_CURRENCY,
            "period_construction": "start = calendar-month anchor + 1 day; end = snapshot_as_of; both bounds inclusive",
            "periods": {
                label: {
                    "start": _period(label, args.snapshot_as_of).start.isoformat(),
                    "end": args.snapshot_as_of.isoformat(),
                    "inclusive_day_count": (_period(label, args.snapshot_as_of).end - _period(label, args.snapshot_as_of).start).days + 1,
                }
                for label in PERIOD_ORDER
            },
            "details": list(DETAIL_ORDER),
            "selections": list(SELECTION_ORDER),
            "only_selectors": list(args.only),
            "selected_probe_count": len(selected_probe_ids),
            "technical_policy_guardrails": [
                "unique asset_id technical universe",
                "native technical prices",
                "observed-only epsilon events",
                "previous-bucket returns",
                "no truncation or segmentation",
            ],
            "simulation_primary_set": {
                "instance_ids": sorted(PRIMARY_INDICATOR_INSTANCES),
                "rationale": "Candidate only: EMA20/50/200 spans trend horizons; RSI14 and MACD cover momentum/state changes. No runtime or public-format policy change.",
            },
        },
        "known_pre_fix_probe": KNOWN_PRE_FIX_PROBE,
        "annotation_policy_diagnostic": annotation_policy_diagnostic,
        "probes": probes,
        "aggregate_summaries": _aggregate_summaries(probes),
        "simulation_results": simulations,
    }
    return document, any(probe["status"] == "failed" for probe in probes) or annotation_policy_diagnostic["status"] == "failed"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic AI Export technical-density probes against the real LibreFolio test SQLite DB.",
    )
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument("--snapshot-as-of", type=_parse_date, default=date(2026, 7, 30), help="Inclusive period end (default: 2026-07-30).")
    parser.add_argument("--username", default="e2e_test_user", help="Test DB username (default: e2e_test_user).")
    parser.add_argument("--asset-id", type=int, default=1, help="Asset target for asset.market_technical (default: 1).")
    parser.add_argument("--broker-id", type=int, default=5, help="Broker target/scope for Broker and Portfolio probes (default: 5).")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="SELECTION[:DETAIL[:PERIOD]]",
        help="Run matching probe subset; repeatable. Example: --only asset.market_technical:compact:3M.",
    )
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.asset_id < 1:
        parser.error("--asset-id must be positive")
    if args.broker_id < 1:
        parser.error("--broker-id must be positive")
    for selector in args.only:
        parts = selector.split(":")
        if len(parts) > 3 or not parts[0]:
            parser.error(f"invalid --only selector: {selector}")
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
        parser.error(f"test SQLite DB not found: {database_path}")
    try:
        document, failed = asyncio.run(_run_matrix(args))
    except Exception as exc:
        parser.exit(2, f"fatal: {type(exc).__name__}: {exc}\n")
    rendered = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {len(document['probes'])} probe(s) to {output_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
