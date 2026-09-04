#!/usr/bin/env python3
"""Generate and measure real AI Export prompts through production HTTP and frontend runtime paths."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import html
import json
import os
import platform
import re
import selectors
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
import unicodedata
from collections import defaultdict
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence
from urllib.parse import urlsplit

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.signals import SignalTemporalClass  # noqa: E402
from backend.app.services.ai_export.temporal.policy import (  # noqa: E402
    BucketDetailLevel,
    BucketingPolicy,
)
from backend.app.services.auth_service import hash_password, verify_password  # noqa: E402

DEFAULT_SOURCE_DB = PROJECT_ROOT / "backend" / "data" / "prod" / "sqlite" / "app.db"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "LibreFolio_developer_journal" / "Release_2" / "Phase_0" / "01_signalMigration" / "02_aiExport" / "real_prompt_probe"
FRONTEND_BRIDGE = PROJECT_ROOT / "frontend" / "scripts" / "run-ai-export-render-prompt-probe.mjs"
API_PREFIX = "/api/v1"
DEFAULT_USERS = ("alfy", "marco")
DEFAULT_REPRESENTATIVE_USER = "marco"
DEFAULT_PERIODS = ("3M", "6M", "1Y")
DEFAULT_DETAILS = ("compact", "standard", "full")
PUBLIC_CATALOG_V1_PROFILE = "public-catalog-v1"
PUBLIC_CATALOG_V1_PERIODS = ("3M", "1Y")
PUBLIC_CATALOG_V1_DATASETS = (
    "portfolio.overview_and_history",
    "portfolio.asset_history",
    "broker.overview_and_history",
    "broker.asset_history",
    "asset.position_and_history",
    "asset.market_history",
    "fx.market_and_exposure",
    "fx.market_history",
)
PUBLIC_CATALOG_V1_ANALYSES = (
    "portfolio.pac_planning",
    "portfolio.rebalancing",
    "portfolio.performance_market_drivers",
    "portfolio.fiscal_lots",
    "broker.review",
    "broker.performance_market_drivers",
    "broker.fiscal_lots",
    "asset.position_review",
    "asset.market_analysis",
    "fx.pair_analysis",
    "fx.exposure_impact",
)
PUBLIC_CATALOG_V1_SELECTIONS = PUBLIC_CATALOG_V1_DATASETS + PUBLIC_CATALOG_V1_ANALYSES
PUBLIC_CATALOG_V1_EXPECTED_CASE_COUNT = len(PUBLIC_CATALOG_V1_SELECTIONS) * len(PUBLIC_CATALOG_V1_PERIODS) * len(DEFAULT_DETAILS)
PROMPT_CATEGORY_CLASSES = (
    "financial",
    "financial_with_context",
    "explicit_technical",
    "fifo",
    "fx",
    "unavailable_partial",
)
COMPOSITION_COMPONENTS = (
    "financial",
    "technical",
    "coverage/provenance",
    "instructions/contracts",
)
DISTRIBUTION_PERCENTILES = (10, 25, 75, 90, 95, 99)
NAMED_PROMPT_RETENTION: Mapping[tuple[str, str, str], tuple[str, ...]] = {
    ("portfolio.overview_and_history", "3M", "compact"): ("named_portfolio_general_3m_compact",),
    ("portfolio.overview_and_history", "3M", "standard"): ("named_portfolio_general_3m_standard",),
    ("portfolio.overview_and_history", "3M", "full"): ("named_portfolio_general_3m_full",),
    ("portfolio.overview_and_history", "1Y", "standard"): ("named_portfolio_general_1y_standard",),
    ("portfolio.overview_and_history", "1Y", "full"): ("named_portfolio_general_1y_full",),
    ("portfolio.asset_history", "3M", "standard"): ("named_portfolio_detailed_3m_standard",),
    ("portfolio.asset_history", "1Y", "compact"): ("named_portfolio_detailed_1y_compact",),
    ("portfolio.asset_history", "1Y", "standard"): ("named_portfolio_detailed_1y_standard",),
    ("portfolio.pac_planning", "3M", "standard"): ("named_portfolio_pac_3m_standard",),
    ("portfolio.rebalancing", "1Y", "standard"): ("named_portfolio_rebalancing_1y_standard",),
    ("portfolio.performance_market_drivers", "3M", "standard"): ("named_portfolio_performance_drivers_3m_standard",),
    ("portfolio.fiscal_lots", "1Y", "standard"): ("named_portfolio_fiscal_lots_1y_standard",),
    ("broker.overview_and_history", "3M", "standard"): ("named_broker_general_3m_standard",),
    ("broker.overview_and_history", "1Y", "standard"): ("named_broker_general_1y_standard",),
    ("broker.asset_history", "3M", "standard"): ("named_broker_detailed_3m_standard",),
    ("broker.review", "3M", "standard"): ("named_broker_review_3m_standard",),
    ("broker.performance_market_drivers", "3M", "standard"): ("named_broker_performance_drivers_3m_standard",),
    ("broker.fiscal_lots", "1Y", "standard"): ("named_broker_fiscal_lots_1y_standard",),
    ("asset.position_and_history", "3M", "standard"): ("named_asset_general_3m_standard",),
    ("asset.position_and_history", "1Y", "full"): ("named_asset_general_1y_full",),
    ("asset.market_history", "3M", "standard"): ("named_asset_detailed_3m_standard",),
    ("asset.position_review", "1Y", "standard"): ("named_asset_position_review_1y_standard",),
    ("asset.market_analysis", "3M", "standard"): ("named_asset_market_analysis_3m_standard",),
    ("fx.market_and_exposure", "3M", "standard"): ("named_fx_general_3m_standard",),
    ("fx.market_and_exposure", "1Y", "full"): ("named_fx_general_1y_full",),
    ("fx.market_history", "3M", "standard"): ("named_fx_detailed_3m_standard",),
    ("fx.pair_analysis", "3M", "standard"): ("named_fx_pair_analysis_3m_standard",),
    ("fx.exposure_impact", "3M", "standard"): ("named_fx_exposure_impact_3m_standard",),
}
EXPLICIT_TECHNICAL_SELECTIONS = frozenset(
    {
        "portfolio.asset_history",
        "broker.asset_history",
        "asset.market_history",
        "portfolio.performance_market_drivers",
        "broker.performance_market_drivers",
        "asset.market_analysis",
        "fx.market_history",
        "fx.pair_analysis",
    }
)
FINANCIAL_WITH_CONTEXT_SELECTIONS = frozenset(
    {
        "portfolio.overview_and_history",
        "broker.overview_and_history",
        "asset.position_and_history",
        "fx.market_and_exposure",
        "portfolio.pac_planning",
        "portfolio.rebalancing",
        "broker.review",
        "asset.position_review",
        "fx.exposure_impact",
    }
)
FIFO_SELECTIONS = frozenset({"portfolio.fiscal_lots", "broker.fiscal_lots"})
SEMANTIC_V2_NEW_DATASETS = frozenset(
    {
        "portfolio.technical_summary",
        "portfolio.asset_snapshot",
        "portfolio.asset_comparison",
        "portfolio.drawdown_context",
        "portfolio.income_evidence",
        "broker.technical_summary",
        "broker.asset_comparison",
        "broker.drawdown_context",
        "broker.concentration_evidence",
        "broker.cost_efficiency_evidence",
        "asset.position_context",
        "asset.drawdown_context",
        "fx.market_context",
        "fx.conversion_timing_context",
    }
)
LANGUAGE_BY_LOCALE = {"en": "English", "it": "Italian", "fr": "French", "es": "Spanish"}
SECRET_PATTERNS = (
    ("authorization_header", re.compile(r'(?im)(?:^|[,{]\s*)["\']?authorization["\']?\s*:\s*["\']?(?:bearer\s+)?[A-Za-z0-9*._~+/=-]{6,}')),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("access_token", re.compile(r'(?i)\baccess_token\b\s*[:=]\s*["\']?[A-Za-z0-9._~+/=-]{8,}')),
    ("refresh_token", re.compile(r'(?i)\brefresh_token\b\s*[:=]\s*["\']?[A-Za-z0-9._~+/=-]{8,}')),
    ("session_cookie", re.compile(r'(?im)(?:^|[,{]\s*)["\']?(?:set-cookie|cookie)["\']?\s*:\s*["\']?\S{8,}')),
)


@dataclass(frozen=True)
class AssetCandidate:
    asset_id: int
    history_start: str
    history_end: str
    observation_count: int
    current_price_valid: bool = True
    held: bool = True
    broker_ids: tuple[int, ...] = ()
    technical_indicator_count: int | None = None


@dataclass(frozen=True)
class FxCandidate:
    base: str
    quote: str
    history_start: str
    history_end: str
    observation_count: int
    current_rate_valid: bool = True

    @property
    def canonical_key(self) -> str:
        return f"{self.base.upper()}_{self.quote.upper()}"


@dataclass(frozen=True)
class TargetProbeCase:
    """One exact user/selection/period/detail/scope case for a targeted run."""

    user_alias: str
    selection_id: str
    period_label: str
    detail_level: str
    scope_selector: str


class ProbeError(RuntimeError):
    """Expected probe orchestration error."""


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_iso_date(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def history_days(start: str | date, end: str | date) -> int:
    return (parse_iso_date(end) - parse_iso_date(start)).days


def sanitize_filename_part(value: object, *, fallback: str = "unknown", max_length: int = 100) -> str:
    """Return a deterministic, portable filename component."""
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").lower()
    sanitized = re.sub(r"[^a-z0-9._-]+", "_", normalized)
    sanitized = re.sub(r"[_-]{2,}", "_", sanitized).strip("._-")
    if not sanitized:
        sanitized = fallback
    if sanitized in {".", ".."}:
        sanitized = fallback
    if len(sanitized) > max_length:
        suffix = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()[:10]
        sanitized = f"{sanitized[: max_length - len(suffix) - 1].rstrip('._-')}_{suffix}"
    return sanitized.rstrip("._-") or fallback


def build_prompt_filename(
    user_alias: str,
    mode: str,
    domain: str,
    selection_id: str,
    scope_alias: str,
    period_label: str,
    detail_level: str,
    *,
    extension: str = "md",
) -> str:
    parts = (user_alias, mode, domain, selection_id, scope_alias, period_label, detail_level)
    return "__".join(sanitize_filename_part(part) for part in parts) + f".{sanitize_filename_part(extension)}"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def repository_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return f"<outside-repository>/{resolved.name}"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def measure_text(value: str) -> dict[str, int | str | float]:
    stripped = value.strip()
    chars = len(value)
    return {
        "chars": chars,
        "unicode_characters": chars,
        "bytes": len(value.encode("utf-8")),
        "lines": 0 if not value else value.count("\n") + 1,
        "words": 0 if not stripped else len(re.findall(r"\S+", stripped, flags=re.UNICODE)),
        "sha256": sha256_text(value),
        "estimated_token_equivalent_chars_div_4": chars / 4,
    }


def parse_target_case(value: str) -> TargetProbeCase:
    """Parse ``user|selection_id|period|detail|scope`` without exposing it in artifacts."""
    parts = tuple(part.strip() for part in value.split("|"))
    if len(parts) != 5 or any(not part for part in parts):
        raise ProbeError("--target-case must use user|selection_id|period|detail|scope")
    user_alias, selection_id, period_label, detail_level, scope_selector = parts
    if user_alias not in DEFAULT_USERS:
        raise ProbeError(f"Unsupported target-case user alias: {user_alias}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", selection_id):
        raise ProbeError(f"Invalid target-case selection ID: {selection_id}")
    if period_label not in DEFAULT_PERIODS:
        raise ProbeError(f"Unsupported target-case period: {period_label}")
    if detail_level not in DEFAULT_DETAILS:
        raise ProbeError(f"Unsupported target-case detail: {detail_level}")
    if scope_selector not in {"all", "representative"} and not scope_selector.lower().startswith("broker="):
        raise ProbeError("Target-case scope must be 'all', 'representative', or 'broker=<display name>'")
    return TargetProbeCase(
        user_alias=user_alias,
        selection_id=selection_id,
        period_label=period_label,
        detail_level=detail_level,
        scope_selector=scope_selector,
    )


def select_target_scope(scopes: Sequence[Mapping[str, object]], target: TargetProbeCase, *, domain: str) -> dict[str, object]:
    """Resolve one exact anonymized runtime scope from a targeted case."""
    if target.scope_selector == "all":
        matches = [scope for scope in scopes if scope.get("domain") == domain and scope.get("scope_alias") == "all"]
    elif target.scope_selector == "representative":
        matches = [scope for scope in representative_scopes(scopes) if scope.get("domain") == domain]
    else:
        requested_name = target.scope_selector.split("=", maxsplit=1)[1].strip().casefold()
        matches = [scope for scope in scopes if scope.get("domain") == domain and str(scope.get("selector_name") or "").casefold() == requested_name]
    if len(matches) != 1:
        raise ProbeError(f"Target scope {target.scope_selector!r} for {target.selection_id} resolved to {len(matches)} scopes")
    return dict(matches[0])


def _component_prompt_block(prompt: str, component_id: str) -> str:
    marker = f"COMPONENT {component_id}\n"
    start = prompt.find(marker)
    if start < 0:
        return ""
    end = prompt.find("\nCOMPONENT ", start + len(marker))
    if end < 0:
        end = prompt.find("\n```", start + len(marker))
    return prompt[start : (len(prompt) if end < 0 else end)]


def _public_table_data_row_count(block: str) -> int:
    count = 0
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or cells[0] in {"field", "row"} or all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        count += 1
    return count


def _checklist_item_count(prompt: str, marker: str) -> int:
    count = 0
    for line in prompt.splitlines():
        if marker not in line:
            continue
        items = line.split(marker, maxsplit=1)[1].strip().rstrip(".")
        count += len([item for item in items.split(";") if item.strip()])
    return count


def measure_targeted_adequacy_diagnostics(selection_id: str, prompt: str) -> dict[str, object]:
    """Small prompt-content diagnostics used only by targeted adequacy runs."""
    if selection_id == "portfolio.pac_planning":
        categories = [category for category in ("Capital and cadence", "Goals and horizon", "Risk preferences", "Operational constraints") if category in prompt]
        portfolio_block = _component_prompt_block(prompt, "portfolio.drawdown_summary")
        asset_block = _component_prompt_block(prompt, "portfolio.asset_drawdown_snapshot")
        required_questions = _checklist_item_count(prompt, "REQUIRED WHEN MISSING:")
        required_material_questions = _checklist_item_count(prompt, "REQUIRED WHEN MISSING AND MATERIAL:")
        return {
            "question_categories": categories,
            "question_category_count": len(categories),
            "required_question_count": required_questions + required_material_questions,
            "required_material_question_count": required_material_questions,
            "optional_question_count": _checklist_item_count(prompt, "OPTIONAL WHEN MATERIAL:"),
            "portfolio_drawdown_rows": _public_table_data_row_count(portfolio_block),
            "asset_drawdown_rows": _public_table_data_row_count(asset_block),
            "drawdown_rows": _public_table_data_row_count(portfolio_block) + _public_table_data_row_count(asset_block),
        }
    if selection_id in {"broker.cost_efficiency", "broker.cost_efficiency_evidence"}:
        block = _component_prompt_block(prompt, "broker.cost_efficiency")
        ratio_statuses: dict[str, str] = {}
        for line in block.splitlines():
            match = re.fullmatch(r"\|((?:fees|total_costs)_to_[^|]+)\.status\|([^|]+)\|", line)
            if match:
                ratio_statuses[match.group(1)] = match.group(2)
        return {
            "cost_ratio_statuses": ratio_statuses,
            "available_ratio_count": sum(status == "recorded" for status in ratio_statuses.values()),
            "unavailable_ratio_count": sum(status == "unavailable" for status in ratio_statuses.values()),
            "not_applicable_ratio_count": sum(status == "not_applicable" for status in ratio_statuses.values()),
        }
    return {}


def measure_broker_scope_diagnostics(snapshot: Mapping[str, object]) -> dict[str, object] | None:
    """Expose public Broker universes without persisting raw database IDs."""
    sections = snapshot.get("sections")
    directory = snapshot.get("entity_directory")
    if not isinstance(sections, list) or not isinstance(directory, Mapping):
        return None
    by_component = {str(section.get("component_id")): section.get("payload") for section in sections if isinstance(section, Mapping) and isinstance(section.get("payload"), Mapping)}
    summary = by_component.get("portfolio.summary")
    provenance = by_component.get("portfolio.provenance")
    performance = by_component.get("portfolio.performance")
    if not any(isinstance(value, Mapping) for value in (summary, provenance, performance)):
        return None

    broker_entries = directory.get("brokers")
    broker_entries = broker_entries if isinstance(broker_entries, list) else []
    broker_ref_by_id = {
        str(entry["broker_id"]): f"B{index}"
        for index, entry in enumerate(
            (entry for entry in broker_entries if isinstance(entry, Mapping) and entry.get("broker_id") is not None),
            start=1,
        )
    }
    raw_scope = provenance.get("broker_scope") if isinstance(provenance, Mapping) else []
    raw_scope = raw_scope if isinstance(raw_scope, list) else []
    scope_refs = [broker_ref_by_id.get(str(broker_id), "unmapped") for broker_id in raw_scope]
    scoped_count = int(provenance.get("scoped_broker_count") or 0) if isinstance(provenance, Mapping) else len(raw_scope)
    position_count = None
    if isinstance(summary, Mapping):
        raw_position_count = summary.get("position_broker_count", summary.get("broker_count"))
        if raw_position_count is not None:
            position_count = int(raw_position_count)
    contributor_count = None
    if isinstance(performance, Mapping) and performance.get("period_contributor_broker_count") is not None:
        contributor_count = int(performance["period_contributor_broker_count"])
    return {
        "broker_scope_refs": scope_refs,
        "scoped_broker_count": scoped_count,
        "position_broker_count": position_count,
        "period_contributor_broker_count": contributor_count,
        "entity_directory_broker_count": len(broker_ref_by_id),
        "scope_directory_consistent": len(scope_refs) == scoped_count and "unmapped" not in scope_refs,
    }


def measure_canonical_breakdown(snapshot: Mapping[str, object], catalog: Mapping[str, object]) -> dict[str, object]:
    """Measure compact canonical response sections and attribute each once to a manifest dataset."""
    raw_sections = snapshot.get("sections")
    raw_manifest = snapshot.get("dataset_manifest")
    raw_catalog_datasets = catalog.get("datasets")
    if not isinstance(raw_sections, list) or not isinstance(raw_manifest, list) or not isinstance(raw_catalog_datasets, list):
        raise ProbeError("Snapshot/catalog lacks sections, dataset_manifest, or datasets")
    catalog_by_id = {str(entry["id"]): entry for entry in raw_catalog_datasets if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
    manifest_entries = [entry for entry in raw_manifest if isinstance(entry, dict) and isinstance(entry.get("dataset_id"), str)]
    manifest_order = [str(entry["dataset_id"]) for entry in manifest_entries]
    sections_by_dataset: dict[str, list[Mapping[str, object]]] = {dataset_id: [] for dataset_id in manifest_order}
    component_measurements: list[dict[str, object]] = []
    unattributed_sections: list[Mapping[str, object]] = []
    for index, section in enumerate(raw_sections):
        if not isinstance(section, dict) or not isinstance(section.get("component_id"), str):
            raise ProbeError(f"Snapshot section {index} lacks component_id")
        component_id = str(section["component_id"])
        dataset_ids: list[str] = []
        for dataset_id in manifest_order:
            dataset = catalog_by_id.get(dataset_id)
            if not isinstance(dataset, dict):
                continue
            declared_components = [
                *dataset.get("required_component_ids", []),
                *dataset.get("optional_component_ids", []),
            ]
            if component_id in {str(item) for item in declared_components}:
                dataset_ids.append(dataset_id)
        attributed_dataset_id = dataset_ids[0] if dataset_ids else "__unattributed__"
        if attributed_dataset_id == "__unattributed__":
            unattributed_sections.append(section)
        else:
            sections_by_dataset[attributed_dataset_id].append(section)
        serialized = canonical_json(section)
        measurement = measure_text(serialized)
        component_measurements.append(
            {
                "section_index": index,
                "component_id": component_id,
                "component_version": section.get("component_version"),
                "schema_id": section.get("schema_id"),
                "schema_version": section.get("schema_version"),
                "dataset_ids": dataset_ids,
                "attributed_dataset_id": attributed_dataset_id,
                "canonical_chars": measurement["chars"],
                "canonical_bytes": measurement["bytes"],
                "canonical_estimated_token_equivalent_chars_div_4": measurement["estimated_token_equivalent_chars_div_4"],
                "canonical_sha256": measurement["sha256"],
            }
        )
    dataset_measurements: list[dict[str, object]] = []
    manifest_by_id = {str(entry["dataset_id"]): entry for entry in manifest_entries}
    for dataset_id in manifest_order:
        attributed_sections = sections_by_dataset[dataset_id]
        serialized = canonical_json(attributed_sections)
        measurement = measure_text(serialized)
        component_rows = [item for item in component_measurements if item["attributed_dataset_id"] == dataset_id]
        manifest_entry = manifest_by_id[dataset_id]
        dataset_measurements.append(
            {
                "dataset_id": dataset_id,
                "dataset_version": manifest_entry.get("dataset_version"),
                "manifest_role": manifest_entry.get("role"),
                "component_ids": [str(item["component_id"]) for item in component_rows],
                "component_count": len(component_rows),
                "attributed_component_canonical_chars_sum": sum(int(item["canonical_chars"]) for item in component_rows),
                "attributed_component_canonical_bytes_sum": sum(int(item["canonical_bytes"]) for item in component_rows),
                "canonical_chars": measurement["chars"],
                "canonical_bytes": measurement["bytes"],
                "canonical_estimated_token_equivalent_chars_div_4": measurement["estimated_token_equivalent_chars_div_4"],
                "canonical_sha256": measurement["sha256"],
            }
        )
    if unattributed_sections:
        serialized = canonical_json(unattributed_sections)
        measurement = measure_text(serialized)
        component_rows = [item for item in component_measurements if item["attributed_dataset_id"] == "__unattributed__"]
        dataset_measurements.append(
            {
                "dataset_id": "__unattributed__",
                "dataset_version": None,
                "manifest_role": None,
                "component_ids": [str(item["component_id"]) for item in component_rows],
                "component_count": len(component_rows),
                "attributed_component_canonical_chars_sum": sum(int(item["canonical_chars"]) for item in component_rows),
                "attributed_component_canonical_bytes_sum": sum(int(item["canonical_bytes"]) for item in component_rows),
                "canonical_chars": measurement["chars"],
                "canonical_bytes": measurement["bytes"],
                "canonical_estimated_token_equivalent_chars_div_4": measurement["estimated_token_equivalent_chars_div_4"],
                "canonical_sha256": measurement["sha256"],
            }
        )
    return {
        "attribution_policy": "first_manifest_dataset_declaring_component_v1",
        "components": component_measurements,
        "datasets": dataset_measurements,
    }


def measure_technical_diagnostics(snapshot: Mapping[str, object]) -> dict[str, object] | None:  # noqa: C901 — flat component-id dispatch extracting diagnostic fields
    sections = snapshot.get("sections")
    if not isinstance(sections, list):
        return None
    diagnostics: dict[str, object] = {
        "price_bucket_rows": 0,
        "indicator_asset_count": 0,
        "indicator_instance_count": 0,
        "detected_event_count": 0,
        "exported_event_count": 0,
        "detailed_event_rows": 0,
        "period_position_leg_count": None,
        "period_contributor_asset_count": None,
        "selected_entity_count": None,
        "eligible_asset_count": None,
        "covered_asset_count": None,
        "eligible_portfolio_weight_ratio": None,
        "covered_portfolio_weight_ratio": None,
        "covered_weight_ratio": None,
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
    latest_event_categories: set[str] = set()
    technical = False
    meta = snapshot.get("meta")
    if isinstance(meta, Mapping) and isinstance(meta.get("history_coverage"), Mapping):
        diagnostics["history_coverage"] = dict(meta["history_coverage"])
        technical = True
    for section in sections:
        if not isinstance(section, dict):
            continue
        component_id = str(section.get("component_id") or "")
        payload = section.get("payload")
        if not isinstance(payload, dict):
            continue
        if any(token in component_id for token in ("technical_prices", "ohlc_returns", "rate_ohlc")):
            technical = True
            assets = payload.get("assets")
            if isinstance(assets, list):
                diagnostics["price_bucket_rows"] = sum(len(asset.get("buckets", [])) for asset in assets if isinstance(asset, dict) and isinstance(asset.get("buckets"), list))
            elif isinstance(payload.get("buckets"), list):
                diagnostics["price_bucket_rows"] = len(payload["buckets"])
        if component_id.endswith(".indicators") or "technical_indicators" in component_id:
            technical = True
            assets = payload.get("assets")
            if isinstance(assets, list):
                diagnostics["indicator_asset_count"] = len(assets)
                diagnostics["indicator_instance_count"] = sum(len(asset.get("indicators", [])) for asset in assets if isinstance(asset, dict) and isinstance(asset.get("indicators"), list))
            elif isinstance(payload.get("indicators"), list):
                diagnostics["indicator_asset_count"] = 1
                diagnostics["indicator_instance_count"] = len(payload["indicators"])
        if "technical_events" in component_id or component_id.endswith(".states_events"):
            technical = True
            diagnostics["detected_event_count"] = int(payload.get("detected_event_count") or 0)
            diagnostics["exported_event_count"] = int(payload.get("exported_event_count") or 0)
            buckets = payload.get("buckets")
            if isinstance(buckets, list):
                diagnostics["detailed_event_rows"] = int(diagnostics["detailed_event_rows"]) + sum(len(bucket.get("events", [])) for bucket in buckets if isinstance(bucket, Mapping) and isinstance(bucket.get("events"), list))
        if "technical_breadth" in component_id:
            technical = True
            for field in (
                "period_position_leg_count",
                "period_contributor_asset_count",
                "eligible_asset_count",
                "covered_asset_count",
                "eligible_portfolio_weight_ratio",
                "covered_portfolio_weight_ratio",
                "covered_weight_ratio",
            ):
                diagnostics[field] = payload.get(field)
        if "technical_coverage" in component_id:
            technical = True
            if "period_position_leg_count" in payload:
                # Portfolio/Broker multi-asset universe coverage.
                diagnostics["period_position_leg_count"] = payload.get("period_position_leg_count")
                diagnostics["period_contributor_asset_count"] = payload.get("period_contributor_asset_count")
                diagnostics["eligible_asset_count"] = payload.get("eligible_asset_count")
                diagnostics["covered_asset_count"] = payload.get("covered_asset_count")
            else:
                # Asset/FX single-entity coverage: explicit single-entity tallies.
                diagnostics["selected_entity_count"] = payload.get("selected_entity_count")
                diagnostics["eligible_asset_count"] = payload.get("eligible_entity_count")
                diagnostics["covered_asset_count"] = payload.get("covered_entity_count")
            for field in (
                "eligible_portfolio_weight_ratio",
                "covered_portfolio_weight_ratio",
                "covered_weight_ratio",
            ):
                if payload.get(field) is not None:
                    diagnostics[field] = payload.get(field)
            signals = payload.get("signals")
            if isinstance(signals, list):
                diagnostics["signal_ok_count"] = sum(int(item.get("ok_count") or 0) for item in signals if isinstance(item, Mapping))
                diagnostics["signal_partial_count"] = sum(int(item.get("partial_count") or 0) for item in signals if isinstance(item, Mapping))
                diagnostics["signal_unavailable_count"] = sum(int(item.get("unavailable_count") or 0) for item in signals if isinstance(item, Mapping))
                diagnostics["signal_failed_count"] = sum(int(item.get("failed_count") or 0) for item in signals if isinstance(item, Mapping))
        if component_id.endswith(".asset_market_context") or component_id.endswith(".position_market_context") or component_id.endswith(".market_summary"):
            technical = True
            history = payload.get("history")
            events = payload.get("events")
            latest_events = payload.get("latest_events")
            diagnostics["context_history_rows"] = int(diagnostics["context_history_rows"]) + (len(history) if isinstance(history, list) else 0)
            event_rows = len(events) if isinstance(events, list) else 0
            diagnostics["context_event_count"] = int(diagnostics["context_event_count"]) + event_rows
            diagnostics["context_event_rows"] = int(diagnostics["context_event_rows"]) + event_rows
            if isinstance(latest_events, list):
                diagnostics["latest_event_rows"] = int(diagnostics["latest_event_rows"]) + len(latest_events)
                for latest in latest_events:
                    if isinstance(latest, Mapping) and latest.get("signal_category") is not None:
                        latest_event_categories.add(str(latest.get("signal_category")))
        if component_id.endswith(".context_events"):
            technical = True
            exported = int(payload.get("exported_event_count") or 0)
            diagnostics["context_event_count"] = int(diagnostics["context_event_count"]) + exported
            diagnostics["context_event_rows"] = int(diagnostics["context_event_rows"]) + exported
        if component_id.endswith(".event_digest"):
            technical = True
            rows = payload.get("rows")
            if isinstance(rows, list):
                valid_rows = [row for row in rows if isinstance(row, Mapping)]
                diagnostics["event_digest_group_count"] = int(diagnostics["event_digest_group_count"]) + len(valid_rows)
                diagnostics["event_digest_underlying_event_count"] = int(diagnostics["event_digest_underlying_event_count"]) + sum(int(row.get("event_count") or 0) for row in valid_rows)
    diagnostics["latest_event_category_count"] = len(latest_event_categories)
    return diagnostics if technical else None


def prompt_size_category(token_equivalent: float | int) -> str:
    value = float(token_equivalent)
    if value <= 10_000:
        return "light"
    if value <= 50_000:
        return "medium"
    return "heavy"


def _as_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, Decimal, str)):
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        return parsed if parsed.is_finite() else None
    return None


def _walk_records(value: object) -> Iterator[Mapping[str, object]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_records(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            yield from _walk_records(nested)


def _split_pipe_row(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"):
        raise ValueError("pipe row must start and end with |")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in line[1:-1]:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            current.append(character)
            escaped = True
        elif character == "|":
            cells.append("".join(current))
            current = []
        else:
            current.append(character)
    cells.append("".join(current))
    return cells


def audit_public_tables(prompt: str) -> dict[str, object]:  # noqa: C901 — flat audit passes over parsed prompt tables
    tables: list[tuple[list[str], list[list[str]]]] = []
    lines = prompt.splitlines()
    index = 0
    while index < len(lines):
        if not lines[index].startswith("|") or not lines[index].endswith("|"):
            index += 1
            continue
        block: list[str] = []
        while index < len(lines) and lines[index].startswith("|") and lines[index].endswith("|"):
            block.append(lines[index])
            index += 1
        parsed = [_split_pipe_row(line) for line in block]
        if parsed:
            tables.append((parsed[0], parsed[1:]))

    empty_columns: list[str] = []
    parent_columns: list[str] = []
    duplicate_headers: list[str] = []
    percent_violations: list[str] = []
    bounded_summary_percent_fields = {
        "broker_largest_position_weight_percent",
        "portfolio_largest_position_weight_percent",
        "largest_position_weight_delta_percent",
    }
    width_violations = 0
    percent_cells_checked = 0
    for headers, rows in tables:
        if len(headers) != len(set(headers)):
            duplicate_headers.extend(header for header in headers if headers.count(header) > 1)
        for row in rows:
            if len(row) != len(headers):
                width_violations += 1
        if not rows or any(len(row) != len(headers) for row in rows):
            continue
        if headers == ["field", "value"]:
            for field_name, value in rows:
                if not field_name.endswith("_percent") or value in {"", "null"}:
                    continue
                if value.endswith("_percent"):
                    # Defensive: a malformed fixture may concatenate the next
                    # table's header without a separator; do not treat a header
                    # name as a SUMMARY value.
                    continue
                percent_cells_checked += 1
                if not value.endswith("%"):
                    percent_violations.append(f"{field_name}={value}")
                    continue
                if field_name in bounded_summary_percent_fields:
                    try:
                        numeric = Decimal(value[:-1])
                    except InvalidOperation:
                        percent_violations.append(f"{field_name}={value}")
                    else:
                        if numeric < -100 or numeric > 100:
                            percent_violations.append(f"{field_name}={value}")
        for column_index, header in enumerate(headers):
            values = [row[column_index] for row in rows]
            if all(value in {"", "null"} for value in values):
                empty_columns.append(header)
                if any(candidate.startswith(f"{header}.") for candidate in headers):
                    parent_columns.append(header)
            if header.endswith("_percent"):
                for value in values:
                    if value in {"", "null"}:
                        continue
                    percent_cells_checked += 1
                    if not value.endswith("%"):
                        percent_violations.append(f"{header}={value}")
    return {
        "table_count": len(tables),
        "width_violations": width_violations,
        "empty_column_count": len(empty_columns),
        "empty_columns": empty_columns,
        "empty_parent_column_count": len(parent_columns),
        "empty_parent_columns": parent_columns,
        "duplicate_header_count": len(set(duplicate_headers)),
        "duplicate_headers": sorted(set(duplicate_headers)),
        "percent_cells_checked": percent_cells_checked,
        "percent_violation_count": len(percent_violations),
        "percent_violations": percent_violations,
    }


def audit_snapshot_semantics(  # noqa: C901 — flat battery of independent audit checks
    snapshot: Mapping[str, object],
    prompt: str,
    render_result: Mapping[str, object],
) -> dict[str, object]:
    sections = snapshot.get("sections")
    section_rows = [section for section in sections if isinstance(section, Mapping)] if isinstance(sections, list) else []
    violations: list[str] = []

    hhi_checks = 0
    hhi_values: list[str] = []
    unit_price_checks = 0
    unit_price_violations = 0
    fifo_lot_rows = 0
    fifo_refs: list[str] = []
    fifo_missing_refs = 0
    fifo_duplicate_ref_count = 0
    fifo_economic_duplicate_groups = 0
    fifo_economic_duplicate_rows = 0
    fifo_custody_rows = 0
    fifo_in_transit_rows = 0
    weight_checks = 0
    weight_violations = 0
    bounded_output_definitions = 0

    for section in section_rows:
        component_id = str(section.get("component_id") or "")
        payload = section.get("payload")
        if not isinstance(payload, Mapping):
            continue
        for record in _walk_records(payload):
            if "herfindahl_index_percent" in record:
                violations.append(f"{component_id}: deprecated herfindahl_index_percent")
            if "herfindahl_index_points" in record:
                hhi_checks += 1
                value = _as_decimal(record.get("herfindahl_index_points"))
                if value is None or value < 0 or value > 10_000:
                    violations.append(f"{component_id}: invalid HHI points")
                else:
                    hhi_values.append(str(value))

            quantity = _as_decimal(record.get("quantity"))
            current_value = record.get("current_value")
            unit_price = record.get("unit_price")
            if quantity is not None:
                current_amount = _as_decimal(current_value.get("amount")) if isinstance(current_value, Mapping) else _as_decimal(current_value)
                unit_amount = _as_decimal(unit_price.get("amount")) if isinstance(unit_price, Mapping) else _as_decimal(unit_price)
                if current_amount is not None and unit_amount is not None:
                    unit_price_checks += 1
                    if abs(quantity * unit_amount - current_amount) > Decimal("0.01"):
                        unit_price_violations += 1

            if "minimum" in record or "maximum" in record:
                if "column_key" in record and (record.get("minimum") is not None or record.get("maximum") is not None):
                    bounded_output_definitions += 1

        if component_id.endswith(".fifo_lots") or component_id.endswith(".lot_detail"):
            lots = payload.get("lots")
            lot_rows = [lot for lot in lots if isinstance(lot, Mapping)] if isinstance(lots, list) else []
            fifo_lot_rows += len(lot_rows)
            signatures: dict[str, int] = defaultdict(int)
            for lot in lot_rows:
                lot_ref = lot.get("lot_ref")
                if not isinstance(lot_ref, str) or re.fullmatch(r"L[1-9]\d*", lot_ref) is None:
                    fifo_missing_refs += 1
                else:
                    fifo_refs.append(lot_ref)
                if "lot_id" in lot or "opening_transaction_id" in lot:
                    violations.append(f"{component_id}: database lot identifier exposed")
                if "opening_broker_name" in lot:
                    violations.append(f"{component_id}: redundant opening_broker_name exposed")
                custody = lot.get("current_custody")
                if isinstance(custody, list):
                    fifo_custody_rows += len(custody)
                    fifo_in_transit_rows += sum(1 for row in custody if isinstance(row, Mapping) and row.get("custody_type") == "IN_TRANSIT")
                signature = canonical_json({key: value for key, value in lot.items() if key != "lot_ref"})
                signatures[signature] += 1
            fifo_economic_duplicate_groups += sum(1 for count in signatures.values() if count > 1)
            fifo_economic_duplicate_rows += sum(count for count in signatures.values() if count > 1)

        if "technical_indicators" in component_id:
            assets = payload.get("assets")
            asset_rows = [asset for asset in assets if isinstance(asset, Mapping)] if isinstance(assets, list) else []
            portfolio_weights = [value for asset in asset_rows if (value := _as_decimal(asset.get("portfolio_weight_ratio"))) is not None]
            covered_assets = [asset for asset in asset_rows if isinstance(asset.get("indicators"), list) and bool(asset.get("indicators"))]
            normalized_by_instance: dict[str, list[Decimal]] = defaultdict(list)
            indicator_portfolio_weight_violations = 0
            for asset in asset_rows:
                asset_weight = _as_decimal(asset.get("portfolio_weight_ratio"))
                indicators = asset.get("indicators")
                if not isinstance(indicators, list):
                    continue
                for indicator in indicators:
                    if not isinstance(indicator, Mapping):
                        continue
                    normalized = _as_decimal(indicator.get("technical_normalized_weight_ratio"))
                    if normalized is not None:
                        normalized_by_instance[str(indicator.get("instance_id"))].append(normalized)
                    if _as_decimal(indicator.get("portfolio_weight_ratio")) != asset_weight:
                        indicator_portfolio_weight_violations += 1
            eligible_weight = _as_decimal(payload.get("eligible_portfolio_weight_ratio"))
            covered_weight = _as_decimal(payload.get("covered_portfolio_weight_ratio"))
            covered_ratio = _as_decimal(payload.get("covered_weight_ratio"))
            covered_count = int(payload.get("covered_asset_count") or 0)
            weight_checks += 5 + len(normalized_by_instance)
            checks = (
                eligible_weight is not None and abs(sum(portfolio_weights, Decimal(0)) - eligible_weight) <= Decimal("1e-9"),
                len(covered_assets) == covered_count,
                covered_weight is not None and abs(sum((_as_decimal(asset.get("portfolio_weight_ratio")) or Decimal(0) for asset in covered_assets), Decimal(0)) - covered_weight) <= Decimal("1e-9"),
                eligible_weight is not None and covered_weight is not None and covered_ratio is not None and abs(covered_ratio - (covered_weight / eligible_weight if eligible_weight else Decimal(0))) <= Decimal("1e-9"),
                indicator_portfolio_weight_violations == 0,
            )
            weight_violations += sum(not check for check in checks)
            weight_violations += sum(abs(sum(weights, Decimal(0)) - Decimal(1)) > Decimal("1e-9") for weights in normalized_by_instance.values())

        if "technical_breadth" in component_id:
            eligible_weight = _as_decimal(payload.get("eligible_portfolio_weight_ratio"))
            covered_weight = _as_decimal(payload.get("covered_portfolio_weight_ratio"))
            covered_ratio = _as_decimal(payload.get("covered_weight_ratio"))
            weight_checks += 1
            if eligible_weight is None or covered_weight is None or covered_ratio is None or abs(covered_ratio - (covered_weight / eligible_weight if eligible_weight else Decimal(0))) > Decimal("1e-9"):
                weight_violations += 1
            states = payload.get("states")
            grouped: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
            if isinstance(states, list):
                for state in states:
                    if isinstance(state, Mapping):
                        grouped[(str(state.get("signal_code")), str(state.get("output_key")))].append(state)
            for group in grouped.values():
                weight_checks += 2
                unweighted = sum((_as_decimal(state.get("unweighted_ratio")) or Decimal(0) for state in group), Decimal(0))
                normalized = sum(
                    (_as_decimal(state.get("technical_normalized_weight_ratio")) or Decimal(0) for state in group),
                    Decimal(0),
                )
                if abs(unweighted - Decimal(1)) > Decimal("1e-9"):
                    weight_violations += 1
                if abs(normalized - Decimal(1)) > Decimal("1e-9"):
                    weight_violations += 1

    fifo_duplicate_ref_count = len(fifo_refs) - len(set(fifo_refs))
    if fifo_missing_refs:
        violations.append(f"FIFO lots missing local refs: {fifo_missing_refs}")
    if fifo_duplicate_ref_count:
        violations.append(f"FIFO duplicate local refs: {fifo_duplicate_ref_count}")
    if unit_price_violations:
        violations.append(f"unit price reconciliation violations: {unit_price_violations}")
    if weight_violations:
        violations.append(f"technical weight reconciliation violations: {weight_violations}")

    table_audit = audit_public_tables(prompt)
    if table_audit["width_violations"]:
        violations.append("public table width violation")
    if table_audit["empty_column_count"]:
        violations.append("public table contains all-empty columns")
    if table_audit["empty_parent_column_count"]:
        violations.append("public table contains empty parent columns")
    if table_audit["duplicate_header_count"]:
        violations.append("public table contains duplicate headers")
    if table_audit["percent_violation_count"]:
        violations.append("public percentage cell lacks %")

    forbidden_prompt_patterns = {
        "schema_metadata": r"\b(?:schema_id|schema_version|component_version)\b",
        "database_entity_ref": r"\b(?:asset|broker):\d+\b",
        "raw_entity_id_field": r"\b(?:asset_id|broker_id)\b",
        "raw_entity_id_array": r'"(?:asset_ids|broker_ids|broker_scope)"\s*:',
        "legacy_fx_ref": r"\bFX[1-9]\d*\b",
        "database_lot_id": r"\b(?:lot_id|opening_transaction_id)\b",
        "unmapped_entity_ref": r"\b(?:asset_unmapped|broker_unmapped):",
        "raw_ratio_weight_name": r"\b(?:portfolio_weight_ratio|technical_normalized_weight_ratio|eligible_portfolio_weight_ratio|covered_portfolio_weight_ratio|covered_weight_ratio|eligible_current_scope_weight_ratio|covered_current_scope_weight_ratio|excluded_current_scope_weight_ratio|coverage_ratio|return_1m_ratio|return_3m_ratio|return_30d_ratio|return_91d_ratio|return_period_ratio|daily_return_volatility_ratio)\b",
        "deprecated_hhi_percent": r"\bherfindahl_index_percent\b",
    }
    prompt_pattern_counts = {name: len(re.findall(pattern, prompt)) for name, pattern in forbidden_prompt_patterns.items()}
    raw_scope_values = 0
    lines = prompt.splitlines()
    expected_scope_prefix = {
        "TABLE broker_scope": "B",
        "TABLE broker_ids": "B",
        "TABLE asset_ids": "A",
    }
    for index, line in enumerate(lines):
        expected_prefix = expected_scope_prefix.get(line)
        if expected_prefix is None:
            continue
        for row in lines[index + 2 :]:
            if not row.startswith("|"):
                break
            cells = row.strip("|").split("|")
            if len(cells) >= 2 and not re.fullmatch(rf"{expected_prefix}[1-9]\d*|null", cells[1]):
                raw_scope_values += 1
    prompt_pattern_counts["raw_scope_numeric_value"] = raw_scope_values
    for name, count in prompt_pattern_counts.items():
        if count:
            violations.append(f"forbidden public prompt pattern {name}: {count}")
    missing_price_policy_count = prompt.count("missing_price_policy=")
    if missing_price_policy_count > 1:
        violations.append("missing price policy repeated")
    if re.search(r"herfindahl_index_points\|[^|\n]*%", prompt):
        violations.append("HHI points rendered as percent")

    breakdown = render_result.get("breakdown")
    format_diagnostics = breakdown.get("format_diagnostics") if isinstance(breakdown, Mapping) and isinstance(breakdown.get("format_diagnostics"), Mapping) else {}
    return {
        "format_diagnostics": dict(format_diagnostics),
        "table_audit": table_audit,
        "hhi": {
            "checks": hhi_checks,
            "values": hhi_values,
            "violations": sum(1 for violation in violations if "HHI" in violation or "herfindahl" in violation),
        },
        "weights": {
            "checks": weight_checks,
            "violations": weight_violations,
        },
        "unit_price": {
            "checks": unit_price_checks,
            "violations": unit_price_violations,
            "tolerance": "0.01",
        },
        "fifo": {
            "lot_rows": fifo_lot_rows,
            "local_refs": len(fifo_refs),
            "missing_refs": fifo_missing_refs,
            "duplicate_refs": fifo_duplicate_ref_count,
            "economic_duplicate_groups": fifo_economic_duplicate_groups,
            "economic_duplicate_rows": fifo_economic_duplicate_rows,
            "custody_rows": fifo_custody_rows,
            "in_transit_rows": fifo_in_transit_rows,
        },
        "bounded_output_definitions": bounded_output_definitions,
        "missing_price_policy_count": missing_price_policy_count,
        "prompt_pattern_counts": prompt_pattern_counts,
        "violations": sorted(set(violations)),
    }


def save_and_reread_prompt(path: Path, content: str, renderer_measurement: Mapping[str, object] | None = None) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")
    reread = path.read_text(encoding="utf-8")
    measured = measure_text(reread)
    measured["matches_renderer_content"] = reread == content
    if renderer_measurement is not None:
        measured["matches_renderer_characters"] = measured["unicode_characters"] == renderer_measurement.get("unicode_characters")
        measured["matches_renderer_bytes"] = measured["bytes"] == renderer_measurement.get("utf8_bytes")
        measured["matches_renderer_lines"] = measured["lines"] == renderer_measurement.get("lines")
        measured["matches_renderer_words"] = measured["words"] == renderer_measurement.get("words")
    measured["renderer_sha256"] = sha256_text(content)
    measured["hash_matches_renderer"] = measured["sha256"] == measured["renderer_sha256"]
    return measured


def discover_catalog(catalog: Mapping[str, object], *, mode: str | None = None, domain: str | None = None) -> list[dict[str, object]]:
    """Discover selections from runtime catalog without fixed counts or IDs."""
    datasets = catalog.get("datasets")
    analyses = catalog.get("analyses")
    if not isinstance(datasets, list) or not isinstance(analyses, list):
        raise ProbeError("AI Export catalog must contain dataset and analysis arrays")
    selections: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for kind, entries in (("dataset", datasets), ("analysis", analyses)):
        for raw in entries:
            if not isinstance(raw, dict):
                raise ProbeError(f"Catalog {kind} entry must be an object")
            entry = dict(raw)
            entry_id = entry.get("id")
            entry_domain = entry.get("domain")
            if not isinstance(entry_id, str) or not isinstance(entry_domain, str):
                raise ProbeError(f"Catalog {kind} entry lacks string id/domain")
            key = (kind, entry_id)
            if key in seen:
                raise ProbeError(f"Duplicate catalog selection: {kind}:{entry_id}")
            seen.add(key)
            entry["kind"] = kind
            entry_mode = "data" if kind == "dataset" else "analysis"
            if mode is not None and entry_mode != mode:
                continue
            if domain is not None and entry_domain != domain:
                continue
            selections.append(entry)
    return sorted(selections, key=lambda item: (str(item["kind"]), str(item["domain"]), str(item["id"])))


def rank_asset_candidates(candidates: Iterable[AssetCandidate], *, minimum_history_days: int = 365) -> list[AssetCandidate]:
    eligible = [candidate for candidate in candidates if candidate.held and candidate.current_price_valid and candidate.observation_count > 0 and history_days(candidate.history_start, candidate.history_end) >= minimum_history_days]
    return sorted(
        eligible,
        key=lambda candidate: (
            -history_days(candidate.history_start, candidate.history_end),
            -candidate.observation_count,
            candidate.asset_id,
        ),
    )


def rank_fx_candidates(candidates: Iterable[FxCandidate], *, minimum_history_days: int = 365) -> list[FxCandidate]:
    eligible = [candidate for candidate in candidates if candidate.current_rate_valid and candidate.observation_count > 0 and candidate.base.upper() != candidate.quote.upper() and history_days(candidate.history_start, candidate.history_end) >= minimum_history_days]
    return sorted(
        eligible,
        key=lambda candidate: (
            -history_days(candidate.history_start, candidate.history_end),
            -candidate.observation_count,
            candidate.canonical_key,
        ),
    )


def build_period_detail_matrix(
    *,
    periods: Sequence[str] | None = None,
    details: Sequence[str] | None = None,
    custom_start: str | date | None = None,
    snapshot_as_of: str | date | None = None,
) -> list[dict[str, object]]:
    requested_periods = tuple(periods or DEFAULT_PERIODS)
    requested_details = tuple(details or DEFAULT_DETAILS)
    output: list[dict[str, object]] = []
    preset_map = {"3M": "3m", "6M": "6m", "1Y": "1y"}
    for period_label in requested_periods:
        if period_label == "Custom":
            continue
        if period_label not in preset_map:
            raise ValueError(f"Unsupported period: {period_label}")
        for detail in requested_details:
            output.append(
                {
                    "period_label": period_label,
                    "detail_level": detail,
                    "period": {"preset": preset_map[period_label], "customAmount": 1, "customUnit": "months"},
                    "is_custom": False,
                }
            )
    custom_requested = "Custom" in requested_periods or periods is None
    if custom_requested and custom_start is not None and snapshot_as_of is not None:
        custom_days = history_days(custom_start, snapshot_as_of)
        if custom_days > 365:
            for detail in requested_details:
                output.append(
                    {
                        "period_label": "Custom",
                        "detail_level": detail,
                        "period": {"preset": "custom", "customAmount": custom_days, "customUnit": "days"},
                        "is_custom": True,
                    }
                )
    return output


def is_technical_dataset(selection: Mapping[str, object]) -> bool:
    if selection.get("kind") != "dataset":
        return False
    selection_id = str(selection.get("id", ""))
    if selection_id.endswith(".all_data"):
        return False
    component_ids = [
        *selection.get("required_component_ids", []),
        *selection.get("optional_component_ids", []),
    ]
    return any(
        token in str(component_id)
        for component_id in component_ids
        for token in (
            "technical_",
            ".indicators",
            ".states_events",
            ".ohlc_returns",
            ".rate_ohlc",
        )
    )


def representative_cases(
    selection: Mapping[str, object],
    *,
    period_filter: str | None = None,
    detail_filter: str | None = None,
) -> list[dict[str, object]]:
    if period_filter or detail_filter:
        return build_period_detail_matrix(
            periods=(period_filter or "1Y",),
            details=(detail_filter or "standard",),
        )
    cases = build_period_detail_matrix(periods=("1Y",), details=("standard",))
    if is_technical_dataset(selection):
        cases.extend(
            build_period_detail_matrix(
                periods=("3M", "6M"),
                details=("standard",),
            )
        )
        cases.extend(
            build_period_detail_matrix(
                periods=("1Y",),
                details=("compact", "full"),
            )
        )
    elif str(selection.get("id", "")).endswith(".all_data"):
        cases.extend(
            build_period_detail_matrix(
                periods=("1Y",),
                details=("full",),
            )
        )
    return cases


def tuning_v2_exclusions(catalog: Mapping[str, object]) -> list[dict[str, object]]:
    datasets = [item for item in catalog.get("datasets", []) if isinstance(item, dict)]
    catalog_dataset_ids = {str(item.get("id", "")) for item in datasets}
    by_domain: defaultdict[str, list[str]] = defaultdict(list)
    for dataset in datasets:
        dataset_id = str(dataset.get("id", ""))
        if not dataset_id.endswith(".all_data") and dataset_id not in SEMANTIC_V2_NEW_DATASETS:
            by_domain[str(dataset.get("domain", ""))].append(dataset_id)
    return [
        {
            "dataset_id": str(dataset["id"]),
            "reason": "pure deduplicated composition already covered by domain base datasets",
            "composed_from": sorted(by_domain[str(dataset.get("domain", ""))]),
            "excluded_semantic_projections": sorted(dataset_id for dataset_id in SEMANTIC_V2_NEW_DATASETS if dataset_id in catalog_dataset_ids and dataset_id.startswith(f"{dataset.get('domain')}.")),
        }
        for dataset in datasets
        if str(dataset.get("id", "")).endswith(".all_data")
    ]


def tuning_v2_cases(
    selection: Mapping[str, object],
    catalog: Mapping[str, object],
    *,
    period_filter: str | None = None,
    detail_filter: str | None = None,
) -> list[dict[str, object]]:
    if selection.get("kind") == "dataset":
        periods = (period_filter,) if period_filter else DEFAULT_PERIODS
        details = (detail_filter,) if detail_filter else DEFAULT_DETAILS
        return build_period_detail_matrix(periods=periods, details=details)

    datasets = {str(item.get("id")): item for item in catalog.get("datasets", []) if isinstance(item, dict)}
    dataset_ids = [
        *selection.get("required_dataset_ids", []),
        *selection.get("optional_dataset_ids", []),
    ]
    temporal = any(str(datasets.get(str(dataset_id), {}).get("period_semantics")) in {"windowed", "aggregated"} for dataset_id in dataset_ids)
    periods = (period_filter,) if period_filter else (("3M", "1Y") if temporal else ("1Y",))
    details = (detail_filter,) if detail_filter else (DEFAULT_DETAILS if temporal else ("standard",))
    return build_period_detail_matrix(periods=periods, details=details)


def public_catalog_v1_selections(
    selections: Sequence[Mapping[str, object]],
    *,
    mode: str | None = None,
    domain: str | None = None,
) -> list[dict[str, object]]:
    """Select the exact public V1 catalog, failing closed when an expected entry is absent."""
    by_id = {str(selection.get("id")): dict(selection) for selection in selections}
    expected = [selection_id for selection_id in PUBLIC_CATALOG_V1_SELECTIONS if (mode is None or ("data" if selection_id in PUBLIC_CATALOG_V1_DATASETS else "analysis") == mode) and (domain is None or selection_id.startswith(f"{domain}."))]
    missing = [selection_id for selection_id in expected if selection_id not in by_id]
    if missing:
        raise ProbeError(f"Public catalog V1 selections absent from runtime catalog: {missing}")
    selected = [by_id[selection_id] for selection_id in expected]
    for selection in selected:
        expected_kind = "dataset" if str(selection["id"]) in PUBLIC_CATALOG_V1_DATASETS else "analysis"
        if selection.get("kind") != expected_kind:
            raise ProbeError(f"Public catalog V1 selection has wrong kind: {selection.get('id')}")
        if str(selection.get("domain")) != str(selection["id"]).partition(".")[0]:
            raise ProbeError(f"Public catalog V1 selection has wrong domain: {selection.get('id')}")
        supported_details = {str(detail) for detail in selection.get("supported_detail_levels", DEFAULT_DETAILS)}
        if not set(DEFAULT_DETAILS) <= supported_details:
            raise ProbeError(f"Public catalog V1 selection lacks compact/standard/full support: {selection.get('id')}")
    return selected


def public_catalog_v1_cases(
    selection: Mapping[str, object],
    *,
    period_filter: str | None = None,
    detail_filter: str | None = None,
) -> list[dict[str, object]]:
    """Return the exact 3M/1Y × compact/standard/full V1 matrix for one public selection."""
    selection_id = str(selection.get("id") or "")
    if selection_id not in PUBLIC_CATALOG_V1_SELECTIONS:
        raise ProbeError(f"Selection is outside public catalog V1: {selection_id}")
    periods = (period_filter,) if period_filter else PUBLIC_CATALOG_V1_PERIODS
    if any(period not in PUBLIC_CATALOG_V1_PERIODS for period in periods):
        raise ProbeError("Public catalog V1 supports only 3M and 1Y periods")
    details = (detail_filter,) if detail_filter else DEFAULT_DETAILS
    return build_period_detail_matrix(periods=periods, details=details)


def representative_scopes(scopes: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    portfolio = next(
        (dict(scope) for scope in scopes if scope.get("domain") == "portfolio" and scope.get("scope_alias") == "all"),
        None,
    )
    if portfolio is not None:
        selected.append(portfolio)
    broker_scopes = [dict(scope) for scope in scopes if scope.get("domain") == "broker"]
    if broker_scopes:
        selected.append(
            min(
                broker_scopes,
                key=lambda scope: (
                    -int(scope.get("inventory", {}).get("position_count", 0) if isinstance(scope.get("inventory"), dict) else 0),
                    str(scope.get("custom_start") or "9999-12-31"),
                    str(scope.get("scope_alias")),
                ),
            )
        )
    for domain in ("asset", "fx"):
        scope = next(
            (dict(item) for item in scopes if item.get("domain") == domain),
            None,
        )
        if scope is not None:
            selected.append(scope)
    return selected


def public_catalog_v1_scope(scopes: Sequence[Mapping[str, object]], selection: Mapping[str, object]) -> dict[str, object] | None:
    """Choose one deterministic scope per V1 selection without adding Cartesian scope cases."""
    domain = str(selection.get("domain") or "")
    if domain == "portfolio":
        selected = next((dict(scope) for scope in scopes if scope.get("domain") == "portfolio" and scope.get("scope_alias") == "all"), None)
        if selected is not None:
            selected["profile_selection_reason"] = "portfolio_all_accessible_brokers"
        return selected
    if domain == "broker":
        candidates = [dict(scope) for scope in scopes if scope.get("domain") == "broker"]
        if not candidates:
            return None
        selected = min(
            candidates,
            key=lambda scope: (
                -int(scope.get("inventory", {}).get("position_count", 0) if isinstance(scope.get("inventory"), Mapping) else 0),
                str(scope.get("custom_start") or "9999-12-31"),
                str(scope.get("scope_alias")),
            ),
        )
        selected["profile_selection_reason"] = "most_positions_then_longest_history_then_scope_key"
        return selected
    selected = next((dict(scope) for scope in scopes if scope.get("domain") == domain), None)
    if selected is not None:
        selected["profile_selection_reason"] = "longest_history_at_least_configured_minimum_then_observations_key"
    return selected


def legacy_sampling_manifest(
    snapshot: Mapping[str, object],
) -> dict[str, object] | None:
    public = snapshot.get("technical_sampling")
    if not isinstance(public, dict):
        return None
    detail = BucketDetailLevel(str(public["detail_level"]))
    result: dict[str, object] = {}
    price = public.get("price_policy")
    if isinstance(price, dict):
        policy = BucketingPolicy.for_detail_level(detail)
        result["price_policy"] = {
            "detail_level": detail.value,
            "p": policy.exponent,
            "m": policy.half_life_offset,
            "k": policy.max_bucket_days,
            "bucket_count": price["bucket_count"],
        }
    indicators = []
    for item in public.get("indicator_policies", []):
        if not isinstance(item, dict):
            continue
        temporal_class = SignalTemporalClass(str(item["temporal_class"]))
        policy = BucketingPolicy.for_indicator(detail, temporal_class)
        indicators.append(
            {
                "signal_instance_id": item["signal_instance_id"],
                "signal_code": item["signal_code"],
                "temporal_class": temporal_class.value,
                "detail_level": detail.value,
                "p": policy.exponent,
                "m": policy.half_life_offset,
                "k": policy.max_bucket_days,
                "bucket_count": item["bucket_count"],
            }
        )
    result["indicator_policies"] = indicators
    return result


def validate_reconciled_breakdown(render_result: Mapping[str, object]) -> None:
    measurement = render_result.get("prompt_measurement")
    breakdown = render_result.get("breakdown")
    if not isinstance(measurement, dict) or not isinstance(breakdown, dict):
        raise ProbeError("Frontend render result lacks measurement/breakdown")
    reconciliation = breakdown.get("reconciliation")
    if not isinstance(reconciliation, dict):
        raise ProbeError("Frontend render result lacks reconciliation")
    if reconciliation.get("unicode_characters_match") is not True or reconciliation.get("utf8_bytes_match") is not True:
        raise ProbeError("Frontend prompt breakdown does not reconcile")
    if reconciliation.get("reconciled_unicode_characters") != measurement.get("unicode_characters"):
        raise ProbeError("Frontend character reconciliation total differs from prompt measurement")
    if reconciliation.get("reconciled_utf8_bytes") != measurement.get("utf8_bytes"):
        raise ProbeError("Frontend byte reconciliation total differs from prompt measurement")


def validate_manifest_checks(manifest_checks: Mapping[str, object], component_breakdown: object, manifest_shape: str = "slim") -> None:
    if manifest_shape not in {"legacy", "slim"}:
        raise ValueError(f"Unsupported manifest shape: {manifest_shape}")
    implementation_lines = int(manifest_checks.get("implementation_parameter_lines") or 0)
    components = component_breakdown if isinstance(component_breakdown, list) else []
    categories = {str(item.get("category")) for item in components if isinstance(item, dict)}
    technical_categories = {category for category in categories if category.startswith("technical_")}
    has_technical_sampling = manifest_checks.get("has_technical_sampling") is True
    if manifest_shape == "legacy":
        if has_technical_sampling and implementation_lines == 0:
            raise ProbeError("Legacy manifest expectation not met: technical prompt lacks P/M/K")
        return
    if implementation_lines != 0:
        raise ProbeError("Slim public prompt contains P/M/K implementation parameters")
    if has_technical_sampling and manifest_checks.get("has_detail_level") is not True:
        raise ProbeError("Rendered technical sampling manifest lacks detail_level")
    if technical_categories & {"technical_prices"} and manifest_checks.get("has_price_bucket_count") is not True:
        raise ProbeError("Rendered technical sampling manifest lacks price_bucket_count")
    has_indicator_instances = manifest_checks.get("has_indicator_instances") is True
    if technical_categories & {"technical_indicators"} and has_indicator_instances and manifest_checks.get("has_instance_bucket_count") is not True:
        raise ProbeError("Rendered technical instance tables lack bucket_count")
    if technical_categories & {"technical_indicators"} and has_indicator_instances and manifest_checks.get("has_instance_temporal_class") is not True:
        raise ProbeError("Rendered technical instance tables lack temporal_class")


def scan_text_for_secrets(text: str, actual_secrets: Iterable[str] = ()) -> list[str]:
    findings: list[str] = []
    for secret in {secret for secret in actual_secrets if secret}:
        if secret in text:
            findings.append("actual_password")
            break
    for code, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(code)
    return sorted(set(findings))


def scan_generated_files(paths: Iterable[Path], actual_secrets: Iterable[str] = ()) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in sorted({candidate.resolve() for candidate in paths if candidate.is_file()}):
        codes = scan_text_for_secrets(path.read_text(encoding="utf-8", errors="replace"), actual_secrets)
        if codes:
            findings.append({"file": path.name, "codes": codes})
    return findings


def stable_metric_key(metric: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(str(metric.get(field, "")) for field in ("user_alias", "mode", "domain", "selection_id", "scope_alias", "period_label", "detail_level"))


def stable_metric_key_text(metric: Mapping[str, object]) -> str:
    return "|".join(stable_metric_key(metric))


def _metric_is_unavailable_or_partial(metric: Mapping[str, object]) -> bool:
    if metric.get("status") == "skipped":
        return True
    omitted = metric.get("optional_datasets_omitted")
    if isinstance(omitted, list) and omitted:
        return True
    diagnostics = metric.get("technical_diagnostics")
    if isinstance(diagnostics, Mapping):
        coverage = diagnostics.get("history_coverage")
        if isinstance(coverage, Mapping) and coverage.get("complete") is False:
            return True
        if any(int(diagnostics.get(field) or 0) > 0 for field in ("signal_partial_count", "signal_unavailable_count", "signal_failed_count")):
            return True
    adequacy = metric.get("targeted_adequacy_diagnostics")
    if isinstance(adequacy, Mapping) and int(adequacy.get("unavailable_ratio_count") or 0) > 0:
        return True
    return False


def classify_prompt_category(metric: Mapping[str, object]) -> tuple[str, list[str]]:
    """Return one primary prompt class plus deterministic supporting tags."""
    selection_id = str(metric.get("selection_id") or "")
    domain = str(metric.get("domain") or selection_id.partition(".")[0])
    tags: list[str] = []
    if selection_id in FIFO_SELECTIONS:
        tags.append("fifo")
    if domain == "fx":
        tags.append("fx")
    if selection_id in EXPLICIT_TECHNICAL_SELECTIONS:
        tags.append("explicit_technical")
    if selection_id in FINANCIAL_WITH_CONTEXT_SELECTIONS:
        tags.append("financial_with_context")
    if not tags:
        tags.append("financial")
    if _metric_is_unavailable_or_partial(metric):
        tags.append("unavailable_partial")
    ordered_tags = [category for category in PROMPT_CATEGORY_CLASSES if category in tags]
    primary = next(
        (
            category
            for category in (
                "unavailable_partial",
                "fifo",
                "fx",
                "explicit_technical",
                "financial_with_context",
                "financial",
            )
            if category in ordered_tags
        ),
        "financial",
    )
    return primary, ordered_tags


def apply_prompt_category(metric: dict[str, object]) -> None:
    primary, tags = classify_prompt_category(metric)
    metric["category"] = primary
    metric["category_tags"] = tags


def _breakdown_chars(value: object) -> int:
    return int(value.get("unicode_characters") or 0) if isinstance(value, Mapping) else 0


def measure_prompt_composition(breakdown: Mapping[str, object], rendered_chars: int) -> dict[str, object]:
    """Classify official renderer diagnostic blocks without rendering a second prompt."""
    sources: dict[str, list[dict[str, object]]] = {component: [] for component in COMPOSITION_COMPONENTS}

    def add(component: str, source_id: str, chars: int) -> None:
        if chars > 0:
            sources[component].append({"source": source_id, "chars": chars})

    sections = [row for row in breakdown.get("sections", []) if isinstance(row, Mapping)]
    for section in sections:
        section_id = str(section.get("id") or "")
        if section_id in {"snapshot_metadata", "snapshot_data"}:
            continue
        add("instructions/contracts", f"section:{section_id}", _breakdown_chars(section))

    component_rows = [row for row in breakdown.get("snapshot_data_components", []) if isinstance(row, Mapping)]
    for row in component_rows:
        component_id = str(row.get("id") or "")
        renderer_category = str(row.get("category") or "")
        if "coverage" in component_id or "provenance" in component_id or renderer_category == "technical_coverage":
            composition_component = "coverage/provenance"
        elif renderer_category.startswith("technical_"):
            composition_component = "technical"
        else:
            composition_component = "financial"
        add(composition_component, f"component:{component_id}", _breakdown_chars(row))

    snapshot_metadata = next((row for row in sections if row.get("id") == "snapshot_metadata"), None)
    add("coverage/provenance", "section:snapshot_metadata", _breakdown_chars(snapshot_metadata))
    add("coverage/provenance", "wrapper:snapshot_data", _breakdown_chars(breakdown.get("snapshot_data_wrapper")))
    add("instructions/contracts", "separators", _breakdown_chars(breakdown.get("separators")))

    measured_total = sum(int(source["chars"]) for rows in sources.values() for source in rows)
    residual = rendered_chars - measured_total
    if residual:
        add("instructions/contracts", "renderer_reconciliation_residual", residual)
    measured_total = sum(int(source["chars"]) for rows in sources.values() for source in rows)

    components: dict[str, dict[str, object]] = {}
    for component in COMPOSITION_COMPONENTS:
        rows = sorted(sources[component], key=lambda row: (-int(row["chars"]), str(row["source"])))
        chars = sum(int(row["chars"]) for row in rows)
        dominant = rows[0] if rows else None
        components[component] = {
            "chars": chars,
            "percent": chars / rendered_chars * 100 if rendered_chars else 0.0,
            "dominant_source": dominant["source"] if dominant else None,
            "dominant_source_chars": dominant["chars"] if dominant else 0,
        }
    dominant_component = max(
        COMPOSITION_COMPONENTS,
        key=lambda component: (int(components[component]["chars"]), -COMPOSITION_COMPONENTS.index(component)),
    )
    return {
        "method": "official_frontend_renderer_breakdown_v1",
        "total_chars": rendered_chars,
        "classified_chars": measured_total,
        "reconciles": measured_total == rendered_chars,
        "components": components,
        "dominant_component": dominant_component,
    }


def nearest_rank_percentile(values: Sequence[float | int], percentile: int) -> float | None:
    """Nearest-rank percentile: ceil(P/100*N), with sorted numeric values."""
    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100")
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    index = max(0, (len(ordered) * percentile + 99) // 100 - 1)
    return ordered[index]


def nearest_metric_entry(entries: Sequence[Mapping[str, object]], target_chars: float) -> Mapping[str, object] | None:
    """Choose nearest measured prompt; equal distance resolves by stable metric key."""
    candidates = [entry for entry in entries if entry.get("status") == "ok" and isinstance(entry.get("rendered_prompt_chars"), int)]
    return min(candidates, key=lambda entry: (abs(int(entry["rendered_prompt_chars"]) - target_chars), stable_metric_key(entry)), default=None)


def select_prompt_retention_reasons(entries: Sequence[Mapping[str, object]]) -> dict[str, list[str]]:
    """Return deduplicated named + global representative retention reasons."""
    successful = [entry for entry in entries if entry.get("status") == "ok" and isinstance(entry.get("rendered_prompt_chars"), int)]
    reasons: defaultdict[str, list[str]] = defaultdict(list)
    for entry in sorted(successful, key=stable_metric_key):
        named = NAMED_PROMPT_RETENTION.get(
            (
                str(entry.get("selection_id") or ""),
                str(entry.get("period_label") or ""),
                str(entry.get("detail_level") or ""),
            ),
            (),
        )
        reasons[stable_metric_key_text(entry)].extend(named)
    if not successful:
        return {}
    chars = [int(entry["rendered_prompt_chars"]) for entry in successful]
    targets: list[tuple[str, float]] = [
        ("global_minimum", float(min(chars))),
        ("global_maximum", float(max(chars))),
        ("global_median", float(statistics.median(chars))),
        *[(f"global_p{percentile}", float(nearest_rank_percentile(chars, percentile) or 0)) for percentile in DISTRIBUTION_PERCENTILES],
    ]
    for reason, target in targets:
        selected = nearest_metric_entry(successful, target)
        if selected is not None:
            reasons[stable_metric_key_text(selected)].append(reason)
    return {key: list(dict.fromkeys(values)) for key, values in sorted(reasons.items()) if values}


def _id_set(metric: Mapping[str, object], field: str) -> set[str]:
    value = metric.get(field, [])
    if isinstance(value, list):
        return {str(item) for item in value}
    return set()


def signal_metric_summary(metric: Mapping[str, object] | None) -> dict[str, object]:
    rows = metric.get("signal_breakdown") if isinstance(metric, Mapping) else None
    rows = rows if isinstance(rows, list) else []
    valid = [row for row in rows if isinstance(row, Mapping)]
    return {
        "signal_codes": sorted({str(row.get("signal_code")) for row in valid if row.get("signal_code")}),
        "instance_count": sum(int(row.get("instance_count") or 0) for row in valid),
        "history_row_count": sum(int(row.get("history_row_count") or 0) for row in valid),
        "source_history_row_count": sum(int(row.get("source_history_row_count") or 0) for row in valid),
        "sampled_history_row_count": sum(int(row.get("sampled_history_row_count") or 0) for row in valid),
        "history_chars": sum(int(row.get("history_chars") or 0) for row in valid),
        "event_count": sum(int(row.get("event_count") or 0) for row in valid),
        "event_chars": sum(int(row.get("event_chars") or 0) for row in valid),
        "definition_chars": sum(int(row.get("definition_chars") or 0) for row in valid),
        "summary_chars": sum(int(row.get("summary_chars") or 0) for row in valid),
    }


# When comparing against an OLD metrics file, its technical_diagnostics still
# use the pre-rename ambiguous `considered_asset_count`, which was the raw
# pre-eligibility period LEG count (`len(positions_contribution.positions)`).
# Map only the equivalent new name back onto it so leg comparisons stay stable.
# `period_contributor_asset_count` is a genuinely NEW metric with no legacy
# equivalent, so it deliberately has no fallback (see metric_change_reasons,
# which skips fields the old run never recorded rather than flagging a change).
_TECHNICAL_DIAGNOSTIC_BACKWARD_FALLBACKS: Mapping[str, tuple[str, ...]] = {
    "period_position_leg_count": ("considered_asset_count",),
}


def _technical_diagnostic_value(diagnostics: Mapping[str, object] | None, field: str) -> object | None:
    if not isinstance(diagnostics, Mapping):
        return None
    value = diagnostics.get(field)
    if value is not None:
        return value
    if field in diagnostics:
        return value
    for legacy_field in _TECHNICAL_DIAGNOSTIC_BACKWARD_FALLBACKS.get(field, ()):
        if legacy_field in diagnostics:
            return diagnostics.get(legacy_field)
    return None


def _technical_diagnostic_int(metric: Mapping[str, object] | None, field: str) -> int | None:
    diagnostics = metric.get("technical_diagnostics") if isinstance(metric, Mapping) else None
    value = _technical_diagnostic_value(diagnostics, field)
    return int(value) if isinstance(value, (int, float)) else None


def _coverage_field_changed(current: Mapping[str, object], previous: Mapping[str, object], field: str) -> bool:
    """True only when both runs resolve a value for ``field`` and they differ.

    Skips comparison when either side is unresolvable (e.g. a NEW metric the OLD
    comparator run never recorded, and which has no backward fallback), so that
    adding a metric never spuriously flags a coverage change - preserving stable
    cross-run comparisons.
    """
    current_value = _technical_diagnostic_value(current, field)
    previous_value = _technical_diagnostic_value(previous, field)
    if current_value is None or previous_value is None:
        return False
    return current_value != previous_value


def _metric_entries(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return [item for item in payload["entries"] if isinstance(item, dict)]
    raise ValueError("Metrics payload must be a list or contain an entries list")


def metric_change_reasons(  # noqa: C901 — flat reason-flag mapping
    metric: Mapping[str, object] | None,
    previous: Mapping[str, object] | None = None,
) -> list[str]:
    if not metric:
        return []
    checks = metric.get("public_output_checks")
    checks = checks if isinstance(checks, Mapping) else {}
    formatting = checks.get("format_diagnostics")
    formatting = formatting if isinstance(formatting, Mapping) else {}
    fifo = checks.get("fifo")
    fifo = fifo if isinstance(fifo, Mapping) else {}
    weights = checks.get("weights")
    weights = weights if isinstance(weights, Mapping) else {}
    hhi = checks.get("hhi")
    hhi = hhi if isinstance(hhi, Mapping) else {}
    reasons: list[str] = []
    if int(formatting.get("floating_point_noise_normalized") or 0) > 0:
        reasons.append("numeric_formatting")
    if int(formatting.get("normalized_ratio_percent_values") or 0) > 0 or int(formatting.get("already_scaled_percent_values") or 0) > 0:
        reasons.append("percentage_correction")
    if int(formatting.get("empty_columns_removed") or 0) > 0 or int(formatting.get("empty_parent_columns_removed") or 0) > 0:
        reasons.append("empty_column_removal")
    if int(formatting.get("empty_temporal_rows_omitted") or 0) > 0:
        reasons.append("empty_temporal_row_removal")
    if int(fifo.get("local_refs") or 0) > 0:
        reasons.append("fifo_lot_reference")
    if int(weights.get("checks") or 0) > 0:
        reasons.append("breadth_weight_clarification")
    if int(hhi.get("checks") or 0) > 0:
        reasons.append("hhi_semantic_correction")
    if previous:
        current_technical = metric.get("technical_diagnostics")
        previous_technical = previous.get("technical_diagnostics")
        coverage_fields = (
            "period_position_leg_count",
            "period_contributor_asset_count",
            "eligible_asset_count",
            "covered_asset_count",
            "indicator_asset_count",
            "indicator_instance_count",
        )
        if (
            isinstance(current_technical, Mapping)
            and isinstance(
                previous_technical,
                Mapping,
            )
            and any(_coverage_field_changed(current_technical, previous_technical, field) for field in coverage_fields)
        ):
            reasons.append("technical_coverage_changed")
        if metric.get("scope_inventory") != previous.get("scope_inventory"):
            reasons.append("scope_inventory_changed")
        current_signals = signal_metric_summary(metric)
        previous_signals = signal_metric_summary(previous)
        if current_signals["signal_codes"] != previous_signals["signal_codes"] or current_signals["instance_count"] != previous_signals["instance_count"]:
            reasons.append("signal_composition_changed")
        if current_signals["history_row_count"] != previous_signals["history_row_count"]:
            reasons.append("history_depth_changed")
        if current_signals["event_count"] != previous_signals["event_count"]:
            reasons.append("event_policy_changed")
        if _id_set(metric, "datasets_included") != _id_set(previous, "datasets_included") or _id_set(metric, "components_included") != _id_set(previous, "components_included"):
            reasons.append("semantic_composition_changed")
    return reasons or ["other"]


def metric_size_category(metric: Mapping[str, object] | None) -> str | None:
    if not metric or metric.get("status") != "ok":
        return None
    declared = metric.get("size_category")
    if isinstance(declared, str):
        return declared
    token_equivalent = metric.get("rendered_prompt_estimated_token_equivalent")
    if isinstance(token_equivalent, (int, float)):
        return prompt_size_category(token_equivalent)
    chars = metric.get("rendered_prompt_chars")
    if isinstance(chars, int):
        return prompt_size_category(chars / 4)
    return None


def compare_metric_runs(
    current_payload: object,
    previous_payload: object,
    *,
    include_removed: bool = True,
) -> list[dict[str, object]]:
    current = {stable_metric_key(item): item for item in _metric_entries(current_payload)}
    previous = {stable_metric_key(item): item for item in _metric_entries(previous_payload)}
    comparison: list[dict[str, object]] = []
    comparison_keys = current.keys() | previous.keys() if include_removed else current.keys()
    for key in sorted(comparison_keys):
        now = current.get(key)
        before = previous.get(key)
        if before is None:
            status = "added"
        elif now is None:
            status = "removed"
        elif before.get("status") != "ok" and now.get("status") == "ok":
            status = "recovered"
        elif now.get("status") != "ok":
            status = "failed"
        else:
            before_chars = int(before.get("rendered_prompt_chars") or 0)
            now_chars = int(now.get("rendered_prompt_chars") or 0)
            datasets_changed = _id_set(before, "datasets_included") != _id_set(now, "datasets_included")
            components_changed = _id_set(before, "components_included") != _id_set(now, "components_included")
            status = "changed" if before_chars != now_chars or datasets_changed or components_changed else "unchanged"
        before_chars = int(before.get("rendered_prompt_chars") or 0) if before else None
        now_chars = int(now.get("rendered_prompt_chars") or 0) if now else None
        delta = now_chars - before_chars if now_chars is not None and before_chars is not None else None
        previous_prompt_sha256 = str(before.get("rendered_prompt_sha256")) if before and before.get("rendered_prompt_sha256") else None
        current_prompt_sha256 = str(now.get("rendered_prompt_sha256")) if now and now.get("rendered_prompt_sha256") else None
        previous_signals = signal_metric_summary(before)
        current_signals = signal_metric_summary(now)
        comparison.append(
            {
                "stable_key": "|".join(key),
                "status": status,
                "comparison_basis": "functional_metrics_v1",
                "previous_chars": before_chars,
                "current_chars": now_chars,
                "previous_prompt_sha256": previous_prompt_sha256,
                "current_prompt_sha256": current_prompt_sha256,
                "prompt_content_changed": bool(previous_prompt_sha256 and current_prompt_sha256 and previous_prompt_sha256 != current_prompt_sha256),
                "absolute_delta": delta,
                "percentage_delta": None if delta is None or before_chars in (None, 0) else delta / before_chars * 100,
                "previous_category": metric_size_category(before),
                "current_category": metric_size_category(now),
                "previous_very_heavy": (float(before.get("rendered_prompt_estimated_token_equivalent") or 0) > 100_000 if before and before.get("status") == "ok" else None),
                "current_very_heavy": (float(now.get("rendered_prompt_estimated_token_equivalent") or 0) > 100_000 if now and now.get("status") == "ok" else None),
                "reason_for_change": (metric_change_reasons(now, before) if status in {"added", "changed", "recovered"} else []),
                "previous_technical_diagnostics": (before.get("technical_diagnostics") if before else None),
                "current_technical_diagnostics": (now.get("technical_diagnostics") if now else None),
                "previous_signal_summary": previous_signals,
                "current_signal_summary": current_signals,
                "signal_instance_delta": int(current_signals["instance_count"]) - int(previous_signals["instance_count"]),
                "history_row_delta": int(current_signals["history_row_count"]) - int(previous_signals["history_row_count"]),
                "source_history_row_delta": int(current_signals["source_history_row_count"]) - int(previous_signals["source_history_row_count"]),
                "sampled_history_row_delta": int(current_signals["sampled_history_row_count"]) - int(previous_signals["sampled_history_row_count"]),
                "event_delta": int(current_signals["event_count"]) - int(previous_signals["event_count"]),
                "definition_chars_delta": int(current_signals["definition_chars"]) - int(previous_signals["definition_chars"]),
                "eligible_entity_delta": (
                    _technical_diagnostic_int(now, "eligible_asset_count") - _technical_diagnostic_int(before, "eligible_asset_count") if _technical_diagnostic_int(now, "eligible_asset_count") is not None and _technical_diagnostic_int(before, "eligible_asset_count") is not None else None
                ),
                "covered_entity_delta": (
                    _technical_diagnostic_int(now, "covered_asset_count") - _technical_diagnostic_int(before, "covered_asset_count") if _technical_diagnostic_int(now, "covered_asset_count") is not None and _technical_diagnostic_int(before, "covered_asset_count") is not None else None
                ),
                "datasets_added": sorted(_id_set(now or {}, "datasets_included") - _id_set(before or {}, "datasets_included")),
                "datasets_removed": sorted(_id_set(before or {}, "datasets_included") - _id_set(now or {}, "datasets_included")),
                "components_added": sorted(_id_set(now or {}, "components_included") - _id_set(before or {}, "components_included")),
                "components_removed": sorted(_id_set(before or {}, "components_included") - _id_set(now or {}, "components_included")),
                "regression": bool(before and now and before.get("status") == "ok" and now.get("status") == "ok" and delta is not None and delta > 0),
            }
        )
    return comparison


def _problem_detail(payload: object) -> Mapping[str, object]:
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, dict):
            return detail
        return payload
    return {}


def classify_http_failure(status_code: int, payload: object, domain: str) -> dict[str, object]:
    detail = _problem_detail(payload)
    code = str(detail.get("code") or f"http_{status_code}")
    skipped = status_code == 422 and code == "selection_not_applicable"
    return {
        "status": "skipped" if skipped else "failed",
        "failure_code": code,
        "source_reason_code": detail.get("reason_code"),
        "failure_message_sanitized": str(detail.get("message") or f"HTTP {status_code}"),
        "retryable": bool(detail.get("retryable", False)),
        "nonfatal": domain == "fx" or skipped,
    }


def should_continue_after_failure(domain: str, status_code: int) -> bool:
    """Probe is batch diagnostics: every individual failure is nonfatal, explicitly including FX 503."""
    return domain == "fx" or status_code >= 400


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_sqlite_family(database_path: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for candidate in (database_path, Path(f"{database_path}-wal"), Path(f"{database_path}-shm")):
        result[candidate.name] = {
            "exists": candidate.exists(),
            "size": candidate.stat().st_size if candidate.exists() else None,
            "sha256": hash_file(candidate) if candidate.exists() else None,
        }
    return result


def sqlite_primary_unchanged(
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> bool:
    return before.get("app.db") == after.get("app.db")


def sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{source.resolve()}?mode=ro&immutable=1"
    with sqlite3.connect(source_uri, uri=True) as source_connection, sqlite3.connect(destination) as destination_connection:
        source_connection.backup(destination_connection)
        result = destination_connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise ProbeError(f"SQLite backup integrity check failed: {result}")


def prepare_runtime_credentials(database_path: Path, passwords: Mapping[str, str], *, normalize: bool) -> dict[str, str]:
    statuses: dict[str, str] = {}
    with sqlite3.connect(database_path) as connection:
        for username, password in passwords.items():
            row = connection.execute("SELECT hashed_password FROM users WHERE username = ?", (username,)).fetchone()
            if row is None:
                raise ProbeError(f"User alias is unavailable in copied database: {username}")
            if verify_password(password, str(row[0])):
                statuses[username] = "matched"
                continue
            if not normalize:
                statuses[username] = "mismatch"
                continue
            connection.execute(
                "UPDATE users SET hashed_password = ? WHERE username = ?",
                (hash_password(password), username),
            )
            statuses[username] = "normalized_on_copy"
        connection.commit()
    return statuses


def sanitize_error(error: BaseException | str, actual_secrets: Iterable[str] = ()) -> str:
    message = str(error).replace("\r", " ").replace("\n", " ").strip()
    for secret in {secret for secret in actual_secrets if secret}:
        message = message.replace(secret, "[REDACTED]")
    message = re.sub(r"(?i)(authorization|cookie|set-cookie)\s*:\s*\S+", r"\1: [REDACTED]", message)
    message = re.sub(r"(?i)\bbearer\s+\S+", "Bearer [REDACTED]", message)
    return message[:500]


class FrontendBridge:
    """Persistent JSON-lines client for the official frontend prompt probe."""

    def __init__(self, script_path: Path = FRONTEND_BRIDGE, *, timeout: float = 600.0):
        self.script_path = script_path
        self.timeout = timeout
        self.process: subprocess.Popen[str] | None = None
        self._request_counter = 0

    def __enter__(self) -> FrontendBridge:
        if not self.script_path.exists():
            raise ProbeError(f"Frontend bridge not found: {self.script_path}")
        self.process = subprocess.Popen(
            ["node", "--no-deprecation", str(self.script_path)],
            cwd=PROJECT_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self.process is None:
            return
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None

    def request(self, message: Mapping[str, object]) -> dict[str, object]:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise ProbeError("Frontend bridge is not running")
        self._request_counter += 1
        request_id = str(message.get("request_id") or f"bridge-{self._request_counter:06d}")
        payload = dict(message)
        payload["request_id"] = request_id
        self.process.stdin.write(canonical_json(payload) + "\n")
        self.process.stdin.flush()
        selector = selectors.DefaultSelector()
        selector.register(self.process.stdout, selectors.EVENT_READ)
        events = selector.select(self.timeout)
        selector.close()
        if not events:
            raise ProbeError(f"Frontend bridge timed out for request {request_id}")
        line = self.process.stdout.readline()
        if not line:
            return_code = self.process.poll()
            raise ProbeError(f"Frontend bridge closed unexpectedly (exit={return_code})")
        response = json.loads(line)
        if not isinstance(response, dict) or response.get("request_id") != request_id:
            raise ProbeError(f"Frontend bridge response identity mismatch for {request_id}")
        if response.get("ok") is not True:
            error = response.get("error")
            message_text = error.get("message") if isinstance(error, dict) else error
            raise ProbeError(f"Frontend bridge failed: {message_text or 'unknown error'}")
        return response


@contextmanager
def local_api_server(runtime_data_dir: Path, port: int) -> Iterator[str]:
    env = os.environ.copy()
    env.update(
        {
            "LIBREFOLIO_TEST_MODE": "0",
            "LIBREFOLIO_DATA_DIR": str(runtime_data_dir.resolve()),
            "LIBREFOLIO_NO_SCHEDULER": "1",
            "LIBREFOLIO_LOG_LEVEL": "WARNING",
        }
    )
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.test_scripts.diagnostics.ai_export_probe_app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--lifespan",
        "off",
    ]
    process = subprocess.Popen(command, cwd=PROJECT_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 90
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise ProbeError(f"Diagnostic API exited before readiness (exit={process.returncode})")
            try:
                response = httpx.get(f"{base_url}{API_PREFIX}/system/health", timeout=2)
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        else:
            raise ProbeError("Diagnostic API did not become ready")
        yield base_url
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _readonly_connection(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{database_path.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _accessible_brokers(connection: sqlite3.Connection, user_id: int) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT b.id, b.name, bua.role
        FROM broker_user_access AS bua
        JOIN brokers AS b ON b.id = bua.broker_id
        WHERE bua.user_id = ?
        ORDER BY b.id
        """,
        (user_id,),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "role": str(row["role"]),
        }
        for row in rows
    ]


def _asset_candidates(connection: sqlite3.Connection, broker_ids: Sequence[int]) -> list[AssetCandidate]:
    if not broker_ids:
        return []
    placeholders = ",".join("?" for _ in broker_ids)
    rows = connection.execute(
        f"""
        WITH position_legs AS (
            SELECT broker_id, asset_id
            FROM transactions
            WHERE broker_id IN ({placeholders}) AND asset_id IS NOT NULL
            GROUP BY broker_id, asset_id
            HAVING ABS(SUM(CAST(quantity AS REAL))) > 0.000000001
        ),
        held AS (
            SELECT asset_id, GROUP_CONCAT(broker_id) AS broker_ids
            FROM position_legs
            GROUP BY asset_id
        ),
        histories AS (
            SELECT asset_id, MIN(date) AS history_start, MAX(date) AS history_end,
                   COUNT(DISTINCT date) AS observation_count
            FROM price_history
            GROUP BY asset_id
        ),
        latest_prices AS (
            SELECT ph.asset_id, COALESCE(ph.adjusted_close, ph.close) AS latest_close
            FROM price_history AS ph
            JOIN histories ON histories.asset_id = ph.asset_id AND histories.history_end = ph.date
        )
        SELECT held.asset_id, held.broker_ids, histories.history_start, histories.history_end,
               histories.observation_count, latest_prices.latest_close
        FROM held
        JOIN histories ON histories.asset_id = held.asset_id
        JOIN latest_prices ON latest_prices.asset_id = held.asset_id
        """,
        tuple(broker_ids),
    ).fetchall()
    candidates: list[AssetCandidate] = []
    for row in rows:
        if row["history_start"] is None or row["history_end"] is None:
            continue
        candidates.append(
            AssetCandidate(
                asset_id=int(row["asset_id"]),
                history_start=str(row["history_start"]),
                history_end=str(row["history_end"]),
                observation_count=int(row["observation_count"]),
                current_price_valid=float(row["latest_close"] or 0) > 0,
                broker_ids=tuple(sorted(int(value) for value in str(row["broker_ids"]).split(","))),
            )
        )
    return candidates


def _portfolio_currencies(connection: sqlite3.Connection, broker_ids: Sequence[int], target_currency: str) -> set[str]:
    currencies = {target_currency.upper()}
    if not broker_ids:
        return currencies
    placeholders = ",".join("?" for _ in broker_ids)
    rows = connection.execute(
        f"""
        SELECT currency FROM transactions
        WHERE broker_id IN ({placeholders}) AND currency IS NOT NULL
        UNION
        SELECT a.currency
        FROM transactions AS t
        JOIN assets AS a ON a.id = t.asset_id
        WHERE t.broker_id IN ({placeholders})
        """,
        tuple(broker_ids) + tuple(broker_ids),
    ).fetchall()
    currencies.update(str(row[0]).upper() for row in rows if row[0])
    return currencies


def _fx_candidates(connection: sqlite3.Connection, currencies: set[str]) -> list[FxCandidate]:
    if not currencies:
        return []
    placeholders = ",".join("?" for _ in currencies)
    ordered = sorted(currencies)
    rows = connection.execute(
        f"""
        WITH histories AS (
            SELECT base, quote, MIN(date) AS history_start, MAX(date) AS history_end,
                   COUNT(DISTINCT date) AS observation_count
            FROM fx_rates
            WHERE base IN ({placeholders}) OR quote IN ({placeholders})
            GROUP BY base, quote
        )
        SELECT histories.*, fx_rates.rate AS latest_rate
        FROM histories
        JOIN fx_rates
          ON fx_rates.base = histories.base
         AND fx_rates.quote = histories.quote
         AND fx_rates.date = histories.history_end
        """,
        tuple(ordered) + tuple(ordered),
    ).fetchall()
    return [
        FxCandidate(
            base=str(row["base"]),
            quote=str(row["quote"]),
            history_start=str(row["history_start"]),
            history_end=str(row["history_end"]),
            observation_count=int(row["observation_count"]),
            current_rate_valid=float(row["latest_rate"] or 0) > 0,
        )
        for row in rows
        if row["history_start"] is not None and row["history_end"] is not None
    ]


def _scope_history(connection: sqlite3.Connection, broker_ids: Sequence[int]) -> tuple[str | None, str | None]:
    if not broker_ids:
        return None, None
    placeholders = ",".join("?" for _ in broker_ids)
    transaction_bounds = connection.execute(
        f"""
        SELECT MIN(date) AS earliest, MAX(date) AS latest
        FROM transactions
        WHERE broker_id IN ({placeholders})
        """,
        tuple(broker_ids),
    ).fetchone()
    price_bounds = connection.execute(
        f"""
        WITH held AS (
            SELECT asset_id FROM transactions
            WHERE broker_id IN ({placeholders}) AND asset_id IS NOT NULL
            GROUP BY asset_id
            HAVING ABS(SUM(CAST(quantity AS REAL))) > 0.000000001
        )
        SELECT MAX(ph.date) AS latest
        FROM price_history AS ph JOIN held ON held.asset_id = ph.asset_id
        """,
        tuple(broker_ids),
    ).fetchone()
    earliest = transaction_bounds["earliest"] if transaction_bounds else None
    latest_price = price_bounds["latest"] if price_bounds else None
    latest_transaction = transaction_bounds["latest"] if transaction_bounds else None
    latest = max(str(value) for value in (latest_price, latest_transaction) if value) if latest_price or latest_transaction else None
    return (str(earliest) if earliest else None, latest)


def _scope_inventory(connection: sqlite3.Connection, broker_ids: Sequence[int], *, snapshot_as_of: str | None = None) -> dict[str, int]:
    if not broker_ids:
        return {
            "scoped_broker_count": 0,
            "position_count": 0,
            "unique_held_asset_count": 0,
            "duplicate_asset_legs": 0,
            "recorded_cost_transaction_count": 0,
            "recorded_cost_transaction_count_1y": 0,
        }
    placeholders = ",".join("?" for _ in broker_ids)
    rows = connection.execute(
        f"""
        SELECT broker_id, asset_id
        FROM transactions
        WHERE broker_id IN ({placeholders}) AND asset_id IS NOT NULL
        GROUP BY broker_id, asset_id
        HAVING ABS(SUM(CAST(quantity AS REAL))) > 0.000000001
        """,
        tuple(broker_ids),
    ).fetchall()
    per_asset: dict[int, int] = {}
    for row in rows:
        asset_id = int(row["asset_id"])
        per_asset[asset_id] = per_asset.get(asset_id, 0) + 1
    recorded_cost_transaction_count = int(
        connection.execute(
            f"SELECT COUNT(*) FROM transactions WHERE broker_id IN ({placeholders}) AND type IN ('FEE', 'TAX')",
            tuple(broker_ids),
        ).fetchone()[0]
    )
    recorded_cost_transaction_count_1y = (
        int(
            connection.execute(
                f"SELECT COUNT(*) FROM transactions WHERE broker_id IN ({placeholders}) AND type IN ('FEE', 'TAX') AND date >= date(?, '-1 year') AND date <= date(?)",
                (*broker_ids, snapshot_as_of, snapshot_as_of),
            ).fetchone()[0]
        )
        if snapshot_as_of
        else recorded_cost_transaction_count
    )
    return {
        "scoped_broker_count": len(broker_ids),
        "position_count": len(rows),
        "unique_held_asset_count": len(per_asset),
        "duplicate_asset_legs": sum(max(0, count - 1) for count in per_asset.values()),
        "recorded_cost_transaction_count": recorded_cost_transaction_count,
        "recorded_cost_transaction_count_1y": recorded_cost_transaction_count_1y,
    }


def collect_user_inventory(database_path: Path, username: str, *, minimum_fx_history_days: int = 365) -> dict[str, object]:
    """Collect anonymizable counts plus deterministic scope candidates from copied DB."""
    with closing(_readonly_connection(database_path)) as connection:
        user = connection.execute(
            """
            SELECT u.id, COALESCE(us.base_currency, 'EUR') AS base_currency,
                   COALESCE(us.language, 'en') AS language
            FROM users AS u
            LEFT JOIN user_settings AS us ON us.user_id = u.id
            WHERE u.username = ?
            """,
            (username,),
        ).fetchone()
        if user is None:
            raise ProbeError(f"User alias is unavailable in copied database: {username}")
        user_id = int(user["id"])
        target_currency = str(user["base_currency"]).upper()
        locale = str(user["language"]).split("-", maxsplit=1)[0].lower()
        if locale not in LANGUAGE_BY_LOCALE:
            locale = "en"
        brokers = _accessible_brokers(connection, user_id)
        broker_ids = [int(item["id"]) for item in brokers]
        asset_candidates = _asset_candidates(connection, broker_ids)
        ranked_assets = rank_asset_candidates(asset_candidates)
        currencies = _portfolio_currencies(connection, broker_ids, target_currency)
        fx_candidates = _fx_candidates(connection, currencies)
        ranked_fx = rank_fx_candidates(fx_candidates, minimum_history_days=minimum_fx_history_days)
        all_start, all_end = _scope_history(connection, broker_ids)
        earliest_price = min((candidate.history_start for candidate in asset_candidates), default=None)
        latest_price = max((candidate.history_end for candidate in asset_candidates), default=None)
        placeholders = ",".join("?" for _ in broker_ids) or "NULL"
        position_rows = (
            connection.execute(
                f"""
                SELECT broker_id, asset_id
                FROM transactions
                WHERE broker_id IN ({placeholders}) AND asset_id IS NOT NULL
                GROUP BY broker_id, asset_id
                HAVING ABS(SUM(CAST(quantity AS REAL))) > 0.000000001
                """,
                tuple(broker_ids),
            ).fetchall()
            if broker_ids
            else []
        )
        held_asset_ids = sorted({int(row["asset_id"]) for row in position_rows})
        per_asset_leg_count: dict[int, int] = {}
        for row in position_rows:
            asset_id = int(row["asset_id"])
            per_asset_leg_count[asset_id] = per_asset_leg_count.get(asset_id, 0) + 1
        historical_ids = {candidate.asset_id for candidate in asset_candidates if candidate.observation_count > 0}
        priced_ids = {candidate.asset_id for candidate in asset_candidates if candidate.current_price_valid}
        technical_ids = {candidate.asset_id for candidate in asset_candidates if history_days(candidate.history_start, candidate.history_end) >= 365 and candidate.observation_count >= 250}
        transaction_count = int(connection.execute(f"SELECT COUNT(*) FROM transactions WHERE broker_id IN ({placeholders})", tuple(broker_ids)).fetchone()[0]) if broker_ids else 0
        fifo_lot_count = (
            int(
                connection.execute(
                    f"SELECT COUNT(*) FROM transactions WHERE broker_id IN ({placeholders}) AND asset_id IS NOT NULL AND CAST(quantity AS REAL) > 0",
                    tuple(broker_ids),
                ).fetchone()[0]
            )
            if broker_ids
            else 0
        )
        broker_histories = {broker_id: _scope_history(connection, [broker_id]) for broker_id in broker_ids}
        scope_inventories = {
            "all": _scope_inventory(connection, broker_ids, snapshot_as_of=all_end),
            **{broker_id: _scope_inventory(connection, [broker_id], snapshot_as_of=all_end) for broker_id in broker_ids},
        }
    inventory = {
        "accessible_broker_count": len(broker_ids),
        "position_legs": len(position_rows),
        "unique_held_assets": len(held_asset_ids),
        "historical_assets": len(historical_ids),
        "priced_assets": len(priced_ids),
        "technical_eligible_assets": len(technical_ids),
        "technical_covered_assets": None,
        "runtime_period_position_leg_count": None,
        "runtime_period_contributor_asset_count": None,
        "runtime_period_eligible_asset_count": None,
        "runtime_period_covered_asset_count": None,
        "duplicate_asset_legs": sum(max(0, count - 1) for count in per_asset_leg_count.values()),
        "currency_count": len(currencies),
        "fx_pair_count": len(fx_candidates),
        "earliest_price": earliest_price,
        "latest_price": latest_price,
        "transactions": transaction_count,
        "fifo_lot_count": fifo_lot_count,
    }
    return {
        "user_id": user_id,
        "username": username,
        "target_currency": target_currency,
        "locale": locale,
        "response_language": LANGUAGE_BY_LOCALE[locale],
        "brokers": brokers,
        "broker_histories": broker_histories,
        "scope_inventories": scope_inventories,
        "portfolio_custom_start": all_start,
        "asset": ranked_assets[0] if ranked_assets else None,
        "fx": ranked_fx[0] if ranked_fx else None,
        "inventory": inventory,
        "snapshot_as_of": all_end or date.today().isoformat(),
    }


def build_user_scopes(user_data: Mapping[str, object]) -> list[dict[str, object]]:
    brokers = user_data["brokers"]
    if not isinstance(brokers, list):
        raise ProbeError("User broker inventory is invalid")
    broker_items = [item for item in brokers if isinstance(item, dict)]
    broker_ids = [int(item["id"]) for item in broker_items]
    snapshot_as_of = str(user_data["snapshot_as_of"])
    target_currency = str(user_data["target_currency"])
    scopes: list[dict[str, object]] = []
    all_start = user_data.get("portfolio_custom_start")
    scope_inventories = user_data.get("scope_inventories")
    scope_inventories = scope_inventories if isinstance(scope_inventories, dict) else {}
    if broker_ids:
        scopes.append(
            {
                "domain": "portfolio",
                "scope_alias": "all",
                "context": {"domain": "portfolio", "snapshotAsOf": snapshot_as_of, "targetCurrency": target_currency, "brokerIds": broker_ids},
                "custom_start": all_start,
                "inventory": scope_inventories.get("all", {}),
                "actual": {"broker_ids": broker_ids},
            }
        )
    histories = user_data.get("broker_histories")
    histories = histories if isinstance(histories, dict) else {}
    for index, broker in enumerate(broker_items, start=1):
        broker_id = int(broker["id"])
        broker_name = str(broker.get("name") or "")
        alias = f"broker_anon_{index:02d}"
        history = histories.get(broker_id) or histories.get(str(broker_id)) or (None, None)
        scopes.extend(
            [
                {
                    "domain": "portfolio",
                    "scope_alias": alias,
                    "selector_name": broker_name,
                    "context": {"domain": "portfolio", "snapshotAsOf": snapshot_as_of, "targetCurrency": target_currency, "brokerIds": [broker_id]},
                    "custom_start": history[0],
                    "inventory": scope_inventories.get(broker_id, {}),
                    "actual": {"broker_ids": [broker_id]},
                },
                {
                    "domain": "broker",
                    "scope_alias": alias,
                    "selector_name": broker_name,
                    "context": {"domain": "broker", "snapshotAsOf": snapshot_as_of, "targetCurrency": target_currency, "brokerId": broker_id},
                    "custom_start": history[0],
                    "inventory": scope_inventories.get(broker_id, {}),
                    "actual": {"broker_id": broker_id},
                },
            ]
        )
    asset = user_data.get("asset")
    if isinstance(asset, AssetCandidate):
        scopes.append(
            {
                "domain": "asset",
                "scope_alias": "asset_anon_01",
                "context": {
                    "domain": "asset",
                    "snapshotAsOf": snapshot_as_of,
                    "targetCurrency": target_currency,
                    "assetId": asset.asset_id,
                },
                "custom_start": asset.history_start,
                "inventory": {
                    "position_broker_count": len(asset.broker_ids),
                    "position_count": len(asset.broker_ids),
                    "unique_held_asset_count": 1,
                    "duplicate_asset_legs": max(0, len(asset.broker_ids) - 1),
                },
                "actual": {
                    "asset_id": asset.asset_id,
                    "broker_ids": list(asset.broker_ids),
                    "selection_reason": "longest_history_at_least_1y",
                    "history_start": asset.history_start,
                    "history_end": asset.history_end,
                    "observation_count": asset.observation_count,
                    "technical_indicator_count": asset.technical_indicator_count,
                },
            }
        )
    fx = user_data.get("fx")
    if isinstance(fx, FxCandidate):
        scopes.append(
            {
                "domain": "fx",
                "scope_alias": "fx_pair_anon_01",
                "context": {
                    "domain": "fx",
                    "snapshotAsOf": snapshot_as_of,
                    "targetCurrency": target_currency,
                    "baseCurrency": fx.base,
                    "quoteCurrency": fx.quote,
                },
                "custom_start": fx.history_start,
                "inventory": scope_inventories.get("all", {}),
                "actual": {
                    "canonical_key": fx.canonical_key,
                    "base": fx.base,
                    "quote": fx.quote,
                    "selection_reason": "longest_history_at_least_1y",
                    "history_start": fx.history_start,
                    "history_end": fx.history_end,
                    "observation_count": fx.observation_count,
                },
            }
        )
    return scopes


def _request_json(client: httpx.Client, method: str, route: str, **kwargs: object) -> tuple[httpx.Response, object, float]:
    started = time.perf_counter()
    response = client.request(method, route, **kwargs)
    duration_ms = (time.perf_counter() - started) * 1000
    try:
        payload: object = response.json()
    except ValueError:
        payload = {"message": response.text[:500]}
    return response, payload, duration_ms


def _base_metric(
    run_id: str,
    user_alias: str,
    selection: Mapping[str, object],
    scope: Mapping[str, object],
    case: Mapping[str, object],
) -> dict[str, object]:
    kind = str(selection["kind"])
    metric: dict[str, object] = {
        "run_id": run_id,
        "user_alias": user_alias,
        "mode": "data" if kind == "dataset" else "analysis",
        "domain": selection["domain"],
        "selection_id": selection["id"],
        "selection_kind": kind,
        "comparison_cohort": "new_semantic_dataset" if kind == "dataset" and str(selection["id"]) in SEMANTIC_V2_NEW_DATASETS else "stable_baseline",
        "selection_version": selection.get("version"),
        "instruction_template_id": selection.get("instruction_template_id"),
        "instruction_template_version": selection.get("instruction_template_version"),
        "response_contract_id": selection.get("response_contract_id"),
        "response_contract_version": selection.get("response_contract_version"),
        "scope_alias": scope["scope_alias"],
        "scope_id": scope["scope_alias"],
        "scope_inventory": dict(scope.get("inventory", {})) if isinstance(scope.get("inventory"), dict) else {},
        "scope_selection_reason": scope.get("profile_selection_reason"),
        "period_label": case["period_label"],
        "period_start": None,
        "period_end": None,
        "effective_period_start": None,
        "effective_period_end": None,
        "detail_level": case["detail_level"],
        "status": "failed",
        "failure_code": None,
        "source_reason_code": None,
        "failure_message_sanitized": None,
        "required_datasets": list(selection.get("required_dataset_ids", [])) if kind == "analysis" else [selection["id"]],
        "optional_datasets_declared": list(selection.get("optional_dataset_ids", [])) if kind == "analysis" else [],
        "optional_datasets_included": [],
        "optional_datasets_omitted": [],
        "datasets_included": [],
        "components_included": [],
        "canonical_backend_chars": None,
        "canonical_backend_bytes": None,
        "canonical_backend_estimated_token_equivalent": None,
        "canonical_backend_estimated_token_equivalent_chars_div_4": None,
        "canonical_component_breakdown": None,
        "canonical_dataset_breakdown": None,
        "canonical_dataset_attribution_policy": None,
        "canonical_file": None,
        "prompt_file": None,
        "retained": False,
        "retention_reasons": [],
        "rendered_prompt_chars": None,
        "rendered_prompt_bytes": None,
        "rendered_prompt_lines": None,
        "rendered_prompt_words": None,
        "rendered_prompt_sha256": None,
        "rendered_prompt_estimated_token_equivalent": None,
        "rendered_prompt_estimated_token_equivalent_chars_div_4": None,
        "size_category": None,
        "very_heavy": None,
        "largest_section_id": None,
        "largest_section_chars": None,
        "largest_component_id": None,
        "largest_component_chars": None,
        "largest_dataset_id": None,
        "largest_dataset_chars": None,
        "technical_chars": None,
        "technical_percentage": None,
        "category": None,
        "category_tags": [],
        "composition": None,
        "renderer_prompt_sha256": None,
        "section_breakdown": None,
        "metadata_field_breakdown": None,
        "entity_directory_breakdown": None,
        "dataset_breakdown": None,
        "component_breakdown": None,
        "signal_breakdown": None,
        "technical_diagnostics": None,
        "broker_diagnostics": None,
        "format_diagnostics": None,
        "public_output_checks": None,
        "http": {"method": "POST", "route": f"{API_PREFIX}/ai-export/snapshot", "status": None, "duration_ms": None},
        "response_sha256": None,
        "renderer_measurement_match": None,
        "renderer_equivalence": None,
        "manifest_checks": None,
        "manifest_impact": None,
        "manifest_shape_expectation": None,
    }
    apply_prompt_category(metric)
    return metric


def _missing_scope_metrics(
    run_id: str,
    user_alias: str,
    selection: Mapping[str, object],
    *,
    period_filter: str | None,
    detail_filter: str | None,
    manifest_shape: str,
    profile: str = "representative",
    catalog: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    domain = str(selection["domain"])
    scope_alias = {"asset": "asset_anon_01", "fx": "fx_pair_anon_01", "broker": "broker_anon_01"}.get(domain, "all")
    supported_details = {str(item) for item in selection.get("supported_detail_levels", DEFAULT_DETAILS)}
    metrics: list[dict[str, object]] = []
    if profile == "tuning-v2":
        cases = tuning_v2_cases(
            selection,
            catalog or {},
            period_filter=period_filter,
            detail_filter=detail_filter,
        )
    elif profile == "representative":
        cases = representative_cases(
            selection,
            period_filter=period_filter,
            detail_filter=detail_filter,
        )
    elif profile == PUBLIC_CATALOG_V1_PROFILE:
        cases = public_catalog_v1_cases(
            selection,
            period_filter=period_filter,
            detail_filter=detail_filter,
        )
    else:
        cases = build_period_detail_matrix(
            periods=((period_filter,) if period_filter else DEFAULT_PERIODS),
            details=((detail_filter,) if detail_filter else DEFAULT_DETAILS),
        )
    for case in cases:
        if str(case["detail_level"]) not in supported_details:
            continue
        metric = _base_metric(run_id, user_alias, selection, {"scope_alias": scope_alias}, case)
        metric.update(
            {
                "status": "skipped",
                "failure_code": "no_applicable_scope",
                "failure_message_sanitized": f"No deterministic applicable {domain} scope was available",
                "manifest_shape_expectation": manifest_shape,
            }
        )
        apply_prompt_category(metric)
        metrics.append(metric)
    return metrics


def _included_ids(snapshot: Mapping[str, object]) -> tuple[list[str], list[str]]:
    manifest = snapshot.get("dataset_manifest")
    sections = snapshot.get("sections")
    dataset_ids = [str(item["dataset_id"]) for item in manifest if isinstance(item, dict) and "dataset_id" in item] if isinstance(manifest, list) else []
    component_ids = [str(item["component_id"]) for item in sections if isinstance(item, dict) and "component_id" in item] if isinstance(sections, list) else []
    return dataset_ids, component_ids


def _run_case(  # noqa: C901 — flat probe step driver
    *,
    run_id: str,
    user_alias: str,
    catalog: Mapping[str, object],
    selection: Mapping[str, object],
    scope: Mapping[str, object],
    case: Mapping[str, object],
    client: httpx.Client,
    bridge: FrontendBridge,
    prompts_dir: Path,
    canonical_dir: Path,
    artifact_root: Path,
    keep_canonical: bool,
    locale: str,
    response_language: str,
    actual_secrets: Iterable[str],
    manifest_shape: str,
    stage_prompt: bool = False,
) -> tuple[dict[str, object], dict[str, object] | None]:
    metric = _base_metric(run_id, user_alias, selection, scope, case)
    metric["manifest_shape_expectation"] = manifest_shape
    identity = {
        "catalog": catalog,
        "selection_kind": selection["kind"],
        "selection_id": selection["id"],
        "context": scope["context"],
        "detail_level": case["detail_level"],
        "period": case["period"],
        "response_language": response_language,
    }
    try:
        prepared = bridge.request({"action": "prepare", **identity})
        request_body = prepared.get("request")
        if not isinstance(request_body, dict):
            raise ProbeError("Frontend prepare response lacks official request")
        period = request_body.get("period")
        if isinstance(period, dict):
            metric["period_start"] = period.get("start")
            metric["period_end"] = period.get("end")
        response, payload, duration_ms = _request_json(client, "POST", f"{API_PREFIX}/ai-export/snapshot", json=request_body)
        metric["http"] = {
            "method": "POST",
            "route": f"{API_PREFIX}/ai-export/snapshot",
            "status": response.status_code,
            "duration_ms": round(duration_ms, 3),
        }
        if response.status_code != 200 or not isinstance(payload, dict):
            failure = classify_http_failure(response.status_code, payload, str(selection["domain"]))
            failure["failure_message_sanitized"] = sanitize_error(str(failure["failure_message_sanitized"]), actual_secrets)
            metric.update(failure)
            apply_prompt_category(metric)
            return metric, dict(metric)
        snapshot = payload
        canonical = canonical_json(snapshot)
        canonical_measurement = measure_text(canonical)
        metric["response_sha256"] = canonical_measurement["sha256"]
        metric["canonical_backend_chars"] = canonical_measurement["chars"]
        metric["canonical_backend_bytes"] = canonical_measurement["bytes"]
        metric["canonical_backend_estimated_token_equivalent"] = canonical_measurement["estimated_token_equivalent_chars_div_4"]
        metric["canonical_backend_estimated_token_equivalent_chars_div_4"] = canonical_measurement["estimated_token_equivalent_chars_div_4"]
        canonical_breakdown = measure_canonical_breakdown(snapshot, catalog)
        metric["canonical_component_breakdown"] = canonical_breakdown["components"]
        metric["canonical_dataset_breakdown"] = canonical_breakdown["datasets"]
        metric["canonical_dataset_attribution_policy"] = canonical_breakdown["attribution_policy"]
        stem = Path(
            build_prompt_filename(
                user_alias,
                str(metric["mode"]),
                str(selection["domain"]),
                str(selection["id"]),
                str(scope["scope_alias"]),
                str(case["period_label"]),
                str(case["detail_level"]),
            )
        ).stem
        if keep_canonical:
            canonical_path = canonical_dir / f"{stem}.json"
            canonical_path.write_text(canonical + "\n", encoding="utf-8", newline="")
            metric["canonical_file"] = str(canonical_path.relative_to(artifact_root))
        rendered = bridge.request(
            {
                "action": "render",
                "snapshot": snapshot,
                "locale": locale,
                "legacy_technical_sampling": legacy_sampling_manifest(snapshot),
                **identity,
            }
        )
        validate_reconciled_breakdown(rendered)
        prompt = rendered.get("prompt")
        renderer_measurement = rendered.get("prompt_measurement")
        if not isinstance(prompt, str) or not isinstance(renderer_measurement, dict):
            raise ProbeError("Frontend render response lacks prompt/measurement")
        manifest_checks = rendered.get("manifest_checks")
        if not isinstance(manifest_checks, dict):
            raise ProbeError("Frontend render response lacks manifest checks")
        breakdown = rendered["breakdown"]
        validate_manifest_checks(manifest_checks, breakdown.get("snapshot_data_components"), manifest_shape)
        prompt_path = prompts_dir / f"{stem}.md"
        file_measurement = save_and_reread_prompt(prompt_path, prompt, renderer_measurement)
        if not all(
            file_measurement.get(field) is True
            for field in (
                "matches_renderer_content",
                "matches_renderer_characters",
                "matches_renderer_bytes",
                "matches_renderer_lines",
                "matches_renderer_words",
                "hash_matches_renderer",
            )
        ):
            raise ProbeError("Saved prompt measurement differs from frontend renderer")
        dataset_ids, component_ids = _included_ids(snapshot)
        required = {str(item) for item in metric["required_datasets"]}
        optional = {str(item) for item in metric["optional_datasets_declared"]}
        included = set(dataset_ids)
        missing_required = sorted(required - included)
        if missing_required:
            raise ProbeError(f"Snapshot manifest omits required datasets: {', '.join(missing_required)}")
        meta = snapshot.get("meta")
        if isinstance(meta, dict):
            exported_period = meta.get("exported_period")
            if isinstance(exported_period, dict):
                metric["effective_period_start"] = exported_period.get("start")
                metric["effective_period_end"] = exported_period.get("end")
        rendered_chars = int(file_measurement["chars"])
        token_equivalent = float(file_measurement["estimated_token_equivalent_chars_div_4"])
        section_rows = [row for row in breakdown.get("sections", []) if isinstance(row, Mapping)]
        component_rows = [row for row in breakdown.get("snapshot_data_components", []) if isinstance(row, Mapping)]
        dataset_rows = [row for row in breakdown.get("snapshot_data_datasets", []) if isinstance(row, Mapping)]
        largest_section = max(
            section_rows,
            key=lambda row: int(row.get("unicode_characters") or 0),
            default={},
        )
        largest_component = max(
            component_rows,
            key=lambda row: int(row.get("unicode_characters") or 0),
            default={},
        )
        largest_dataset = max(
            dataset_rows,
            key=lambda row: int(row.get("unicode_characters") or 0),
            default={},
        )
        technical_chars = sum(int(row.get("unicode_characters") or 0) for row in component_rows if str(row.get("category") or "").startswith("technical_"))
        composition = measure_prompt_composition(breakdown, rendered_chars)
        if composition["reconciles"] is not True:
            raise ProbeError("Frontend composition breakdown does not reconcile")
        public_output_checks = audit_snapshot_semantics(snapshot, prompt, rendered)
        if public_output_checks["violations"]:
            raise ProbeError("Public output checks failed: " + "; ".join(str(item) for item in public_output_checks["violations"]))
        format_diagnostics = public_output_checks["format_diagnostics"]
        metric.update(
            {
                "status": "ok",
                "datasets_included": dataset_ids,
                "components_included": component_ids,
                "optional_datasets_included": sorted(optional & included),
                "optional_datasets_omitted": sorted(optional - included),
                "required_datasets_missing": [],
                **({"_staged_prompt_file": str(prompt_path.relative_to(artifact_root))} if stage_prompt else {"prompt_file": str(prompt_path.relative_to(artifact_root))}),
                "rendered_prompt_chars": rendered_chars,
                "rendered_prompt_bytes": file_measurement["bytes"],
                "rendered_prompt_lines": file_measurement["lines"],
                "rendered_prompt_words": file_measurement["words"],
                "rendered_prompt_sha256": file_measurement["sha256"],
                "rendered_prompt_estimated_token_equivalent": token_equivalent,
                "rendered_prompt_estimated_token_equivalent_chars_div_4": token_equivalent,
                "size_category": prompt_size_category(token_equivalent),
                "very_heavy": token_equivalent > 100_000,
                "largest_section_id": largest_section.get("id"),
                "largest_section_chars": largest_section.get("unicode_characters"),
                "largest_component_id": largest_component.get("id"),
                "largest_component_chars": largest_component.get("unicode_characters"),
                "largest_dataset_id": largest_dataset.get("dataset_id"),
                "largest_dataset_chars": largest_dataset.get("unicode_characters"),
                "technical_chars": technical_chars,
                "technical_percentage": (technical_chars / rendered_chars * 100 if rendered_chars else 0.0),
                "composition": composition,
                "renderer_prompt_sha256": file_measurement["renderer_sha256"],
                "section_breakdown": breakdown.get("sections"),
                "metadata_field_breakdown": breakdown.get("snapshot_metadata_fields"),
                "entity_directory_breakdown": breakdown.get("entity_directory"),
                "dataset_breakdown": breakdown.get("snapshot_data_datasets"),
                "component_breakdown": breakdown.get("snapshot_data_components"),
                "signal_breakdown": breakdown.get("signal_metrics"),
                "technical_diagnostics": measure_technical_diagnostics(snapshot),
                "broker_diagnostics": measure_broker_scope_diagnostics(snapshot),
                "format_diagnostics": format_diagnostics,
                "empty_temporal_rows_before": int(format_diagnostics.get("empty_temporal_rows_detected") or 0),
                "empty_temporal_rows_omitted": int(format_diagnostics.get("empty_temporal_rows_omitted") or 0),
                "remaining_temporal_rows": int(format_diagnostics.get("temporal_rows_rendered") or 0),
                "public_output_checks": public_output_checks,
                "breakdown_wrappers": {
                    "separators": breakdown.get("separators"),
                    "snapshot_metadata_wrapper": breakdown.get("snapshot_metadata_wrapper"),
                    "snapshot_data_wrapper": breakdown.get("snapshot_data_wrapper"),
                },
                "renderer_measurement_match": True,
                "renderer_equivalence": rendered.get("renderer_equivalence"),
                "manifest_checks": manifest_checks,
                "manifest_impact": rendered.get("manifest_impact"),
                "targeted_adequacy_diagnostics": measure_targeted_adequacy_diagnostics(str(selection["id"]), prompt),
            }
        )
        apply_prompt_category(metric)
        return metric, None
    except Exception as error:
        metric["status"] = "failed"
        metric["failure_code"] = type(error).__name__
        metric["failure_message_sanitized"] = sanitize_error(error, actual_secrets)
        apply_prompt_category(metric)
        return metric, dict(metric)


def _git_state() -> dict[str, object]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False).stdout
    return {"commit": commit or None, "dirty": bool(status.strip())}


def _active_production_processes() -> list[dict[str, object]]:
    result = subprocess.run(
        ["ps", "-ax", "-o", "pid=,command="],
        capture_output=True,
        text=True,
        check=False,
    )
    processes: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, command = stripped.partition(" ")
        if not pid_text.isdigit():
            continue
        if "6040" not in command or ("uvicorn" not in command and "dev.py server" not in command):
            continue
        processes.append(
            {
                "pid": int(pid_text),
                "command_kind": "dev.py server" if "dev.py server" in command else "uvicorn",
            }
        )
    return processes


def _median(values: Iterable[int]) -> float | None:
    materialized = list(values)
    return statistics.median(materialized) if materialized else None


def _entry_tokens(entry: Mapping[str, object]) -> float:
    return float(entry.get("rendered_prompt_estimated_token_equivalent") or 0)


def _entry_descriptor(entry: Mapping[str, object]) -> dict[str, object]:
    return {
        "mode": entry.get("mode"),
        "domain": entry.get("domain"),
        "selection_id": entry.get("selection_id"),
        "period": entry.get("period_label"),
        "detail": entry.get("detail_level"),
        "rendered_chars": entry.get("rendered_prompt_chars"),
        "estimated_token_equivalent": entry.get("rendered_prompt_estimated_token_equivalent"),
        "size_category": metric_size_category(entry),
        "very_heavy": entry.get("very_heavy"),
        "largest_section": entry.get("largest_section_id"),
        "technical_percentage": entry.get("technical_percentage"),
        "category": entry.get("category"),
        "retained": entry.get("retained"),
        "prompt_file": entry.get("prompt_file"),
    }


def numeric_distribution_stats(values: Sequence[float | int]) -> dict[str, float | int | None]:
    materialized = [float(value) for value in values]
    if not materialized:
        return {
            "count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "iqr": None,
            "population_stdev": None,
        }
    p25 = nearest_rank_percentile(materialized, 25)
    p75 = nearest_rank_percentile(materialized, 75)
    return {
        "count": len(materialized),
        "minimum": min(materialized),
        "maximum": max(materialized),
        "mean": statistics.fmean(materialized),
        "median": statistics.median(materialized),
        "p10": nearest_rank_percentile(materialized, 10),
        "p25": p25,
        "p75": p75,
        "p90": nearest_rank_percentile(materialized, 90),
        "p95": nearest_rank_percentile(materialized, 95),
        "p99": nearest_rank_percentile(materialized, 99),
        "iqr": (p75 - p25) if p25 is not None and p75 is not None else None,
        "population_stdev": statistics.pstdev(materialized),
    }


def _distribution_stats(entries: Sequence[Mapping[str, object]]) -> dict[str, object]:
    tokens = [_entry_tokens(entry) for entry in entries]
    characters = [int(entry.get("rendered_prompt_chars") or 0) for entry in entries]
    categories = {category: sum(1 for entry in entries if metric_size_category(entry) == category) for category in ("light", "medium", "heavy")}
    return {
        **numeric_distribution_stats(tokens),
        "value_metric": "rendered_prompt_estimated_token_equivalent_chars_div_4",
        "rendered_characters": numeric_distribution_stats(characters),
        "light": categories["light"],
        "medium": categories["medium"],
        "heavy": categories["heavy"],
        "very_heavy": sum(1 for entry in entries if _entry_tokens(entry) > 100_000),
    }


def _group_distributions(
    entries: Sequence[Mapping[str, object]],
    field: str,
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for entry in entries:
        grouped[str(entry.get(field))].append(entry)
    return {key: _distribution_stats(rows) for key, rows in sorted(grouped.items())}


def _aggregate_largest_breakdown(
    entries: Sequence[Mapping[str, object]],
    *,
    field: str,
    id_field: str,
) -> str | None:
    totals: dict[str, int] = defaultdict(int)
    for entry in entries:
        breakdown = entry.get(field)
        if not isinstance(breakdown, list):
            continue
        for row in breakdown:
            if not isinstance(row, Mapping):
                continue
            identifier = row.get(id_field)
            if identifier is not None:
                totals[str(identifier)] += int(row.get("unicode_characters") or 0)
    return max(totals, key=totals.get) if totals else None


def build_dimension_summary(entries: Sequence[Mapping[str, object]]) -> dict[str, object]:
    successful = [entry for entry in entries if entry.get("status") == "ok"]
    category_distribution: dict[str, object] = {}
    representatives: dict[str, object] = {}
    for category in ("light", "medium", "heavy"):
        rows = sorted(
            (entry for entry in successful if metric_size_category(entry) == category),
            key=_entry_tokens,
        )
        category_distribution[category] = {
            **_distribution_stats(rows),
            "percentage_of_corpus": (len(rows) / len(successful) * 100 if successful else 0.0),
        }
        if rows:
            representatives[category] = {
                "smallest": _entry_descriptor(rows[0]),
                "median": _entry_descriptor(rows[(len(rows) - 1) // 2]),
                "largest": _entry_descriptor(rows[-1]),
                **({"very_heavy": [_entry_descriptor(entry) for entry in rows if _entry_tokens(entry) > 100_000]} if category == "heavy" else {}),
            }

    analyses: dict[str, object] = {}
    analysis_groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for entry in successful:
        if entry.get("mode") == "analysis":
            analysis_groups[str(entry.get("selection_id"))].append(entry)
    for selection_id, rows in sorted(analysis_groups.items()):
        by_case = {(str(entry.get("period_label")), str(entry.get("detail_level"))): entry for entry in rows}
        technical_percentages = [float(entry.get("technical_percentage") or 0) for entry in rows]
        analyses[selection_id] = {
            **_distribution_stats(rows),
            "category_3m_compact": metric_size_category(by_case.get(("3M", "compact"))),
            "category_1y_standard": metric_size_category(by_case.get(("1Y", "standard"))),
            "category_1y_full": metric_size_category(by_case.get(("1Y", "full"))),
            "technical_share_median": (statistics.median(technical_percentages) if technical_percentages else None),
            "technical_share_maximum": max(
                technical_percentages,
                default=None,
            ),
            "largest_included_dataset": _aggregate_largest_breakdown(
                rows,
                field="dataset_breakdown",
                id_field="dataset_id",
            ),
        }

    datasets: dict[str, object] = {}
    dataset_groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for entry in successful:
        if entry.get("mode") == "data":
            dataset_groups[str(entry.get("selection_id"))].append(entry)
    for selection_id, rows in sorted(dataset_groups.items()):
        by_case = {(str(entry.get("period_label")), str(entry.get("detail_level"))): entry for entry in rows}
        datasets[selection_id] = {
            **_distribution_stats(rows),
            "category_3m_compact": metric_size_category(by_case.get(("3M", "compact"))),
            "category_1y_standard": metric_size_category(by_case.get(("1Y", "standard"))),
            "category_1y_full": metric_size_category(by_case.get(("1Y", "full"))),
            "largest_component": _aggregate_largest_breakdown(
                rows,
                field="component_breakdown",
                id_field="id",
            ),
        }

    return {
        "metric": "rendered final prompt estimated token-equivalent = rendered chars / 4",
        "thresholds": {
            "light_maximum": 10_000,
            "medium_maximum": 50_000,
            "very_heavy_minimum_exclusive": 100_000,
        },
        "overall": _distribution_stats(successful),
        "category_distribution": category_distribution,
        "by_mode": _group_distributions(successful, "mode"),
        "by_type": _group_distributions(successful, "selection_kind"),
        "by_domain": _group_distributions(successful, "domain"),
        "by_category": _group_distributions(successful, "category"),
        "by_detail": _group_distributions(successful, "detail_level"),
        "by_period": _group_distributions(successful, "period_label"),
        "by_comparison_cohort": _group_distributions(successful, "comparison_cohort"),
        "representatives": representatives,
        "analyses": analyses,
        "datasets": datasets,
    }


def build_composition_summary(entries: Sequence[Mapping[str, object]]) -> dict[str, object]:
    successful = [entry for entry in entries if entry.get("status") == "ok" and isinstance(entry.get("composition"), Mapping)]
    totals = dict.fromkeys(COMPOSITION_COMPONENTS, 0)
    source_totals: dict[str, defaultdict[str, int]] = {component: defaultdict(int) for component in COMPOSITION_COMPONENTS}
    total_chars = 0
    for entry in successful:
        composition = entry["composition"]
        if not isinstance(composition, Mapping):
            continue
        total_chars += int(composition.get("total_chars") or 0)
        components = composition.get("components")
        if not isinstance(components, Mapping):
            continue
        for component in COMPOSITION_COMPONENTS:
            row = components.get(component)
            if not isinstance(row, Mapping):
                continue
            chars = int(row.get("chars") or 0)
            totals[component] += chars
            source = row.get("dominant_source")
            if source is not None:
                source_totals[component][str(source)] += int(row.get("dominant_source_chars") or 0)
    components: dict[str, dict[str, object]] = {}
    for component in COMPOSITION_COMPONENTS:
        dominant_source = min(
            source_totals[component],
            key=lambda source: (-source_totals[component][source], source),
            default=None,
        )
        components[component] = {
            "chars": totals[component],
            "percent": totals[component] / total_chars * 100 if total_chars else 0.0,
            "dominant_source": dominant_source,
            "dominant_source_chars": source_totals[component][dominant_source] if dominant_source is not None else 0,
        }
    return {
        "prompt_count": len(successful),
        "total_chars": total_chars,
        "components": components,
        "dominant_component": max(COMPOSITION_COMPONENTS, key=lambda component: (totals[component], -COMPOSITION_COMPONENTS.index(component))) if successful else None,
    }


def build_quality_summary(entries: Sequence[Mapping[str, object]]) -> dict[str, object]:
    successful = [entry for entry in entries if entry.get("status") == "ok"]
    format_totals: dict[str, int] = defaultdict(int)
    prompt_pattern_totals: dict[str, int] = defaultdict(int)
    totals = {
        "hhi_checks": 0,
        "hhi_violations": 0,
        "weight_checks": 0,
        "weight_violations": 0,
        "unit_price_checks": 0,
        "unit_price_violations": 0,
        "fifo_lot_rows": 0,
        "fifo_local_refs": 0,
        "fifo_missing_refs": 0,
        "fifo_duplicate_refs": 0,
        "fifo_economic_duplicate_groups": 0,
        "fifo_economic_duplicate_rows": 0,
        "fifo_custody_rows": 0,
        "fifo_in_transit_rows": 0,
        "table_count": 0,
        "empty_column_violations": 0,
        "empty_parent_column_violations": 0,
        "duplicate_header_violations": 0,
        "percentage_violations": 0,
        "missing_price_policy_repetitions": 0,
        "public_output_violations": 0,
        "renderer_equivalence_violations": 0,
    }
    for entry in successful:
        checks = entry.get("public_output_checks")
        checks = checks if isinstance(checks, Mapping) else {}
        formatting = checks.get("format_diagnostics")
        if isinstance(formatting, Mapping):
            for key, value in formatting.items():
                if isinstance(value, int):
                    format_totals[str(key)] += value
        patterns = checks.get("prompt_pattern_counts")
        if isinstance(patterns, Mapping):
            for key, value in patterns.items():
                if isinstance(value, int):
                    prompt_pattern_totals[str(key)] += value
        hhi = checks.get("hhi") if isinstance(checks.get("hhi"), Mapping) else {}
        weights = checks.get("weights") if isinstance(checks.get("weights"), Mapping) else {}
        unit_price = checks.get("unit_price") if isinstance(checks.get("unit_price"), Mapping) else {}
        fifo = checks.get("fifo") if isinstance(checks.get("fifo"), Mapping) else {}
        tables = checks.get("table_audit") if isinstance(checks.get("table_audit"), Mapping) else {}
        totals["hhi_checks"] += int(hhi.get("checks") or 0)
        totals["hhi_violations"] += int(hhi.get("violations") or 0)
        totals["weight_checks"] += int(weights.get("checks") or 0)
        totals["weight_violations"] += int(weights.get("violations") or 0)
        totals["unit_price_checks"] += int(unit_price.get("checks") or 0)
        totals["unit_price_violations"] += int(unit_price.get("violations") or 0)
        totals["fifo_lot_rows"] += int(fifo.get("lot_rows") or 0)
        totals["fifo_local_refs"] += int(fifo.get("local_refs") or 0)
        totals["fifo_missing_refs"] += int(fifo.get("missing_refs") or 0)
        totals["fifo_duplicate_refs"] += int(fifo.get("duplicate_refs") or 0)
        totals["fifo_economic_duplicate_groups"] += int(fifo.get("economic_duplicate_groups") or 0)
        totals["fifo_economic_duplicate_rows"] += int(fifo.get("economic_duplicate_rows") or 0)
        totals["fifo_custody_rows"] += int(fifo.get("custody_rows") or 0)
        totals["fifo_in_transit_rows"] += int(fifo.get("in_transit_rows") or 0)
        totals["table_count"] += int(tables.get("table_count") or 0)
        totals["empty_column_violations"] += int(tables.get("empty_column_count") or 0)
        totals["empty_parent_column_violations"] += int(tables.get("empty_parent_column_count") or 0)
        totals["duplicate_header_violations"] += int(tables.get("duplicate_header_count") or 0)
        totals["percentage_violations"] += int(tables.get("percent_violation_count") or 0)
        totals["missing_price_policy_repetitions"] += max(
            0,
            int(checks.get("missing_price_policy_count") or 0) - 1,
        )
        violations = checks.get("violations")
        totals["public_output_violations"] += len(violations) if isinstance(violations, list) else 0
        equivalence = entry.get("renderer_equivalence")
        if not isinstance(equivalence, Mapping) or equivalence.get("exact_string_match") is not True or equivalence.get("utf8_bytes_match") is not True:
            totals["renderer_equivalence_violations"] += 1
    return {
        "prompt_sample": len(successful),
        **totals,
        "format_diagnostics": dict(sorted(format_totals.items())),
        "prompt_pattern_counts": dict(sorted(prompt_pattern_totals.items())),
    }


def mark_direct_prompt_retention(entries: Sequence[dict[str, object]], reason: str) -> None:
    for entry in entries:
        retained = entry.get("status") == "ok" and isinstance(entry.get("prompt_file"), str)
        entry["retained"] = retained
        entry["retention_reasons"] = [reason] if retained else []


def collect_staged_prompt_paths(entries: Sequence[dict[str, object]], artifact_root: Path) -> dict[str, Path]:
    staged: dict[str, Path] = {}
    for entry in entries:
        relative = entry.pop("_staged_prompt_file", None)
        if not isinstance(relative, str):
            continue
        key = stable_metric_key_text(entry)
        if key in staged:
            raise ProbeError(f"Duplicate staged prompt stable key: {key}")
        staged[key] = artifact_root / relative
    return staged


def finalize_public_catalog_prompt_retention(
    entries: Sequence[dict[str, object]],
    staged_paths: Mapping[str, Path],
    *,
    artifact_root: Path,
    prompts_dir: Path,
    allow_retention: bool,
) -> dict[str, list[str]]:
    retention_reasons = select_prompt_retention_reasons(entries)
    for entry in entries:
        key = stable_metric_key_text(entry)
        reasons = retention_reasons.get(key, [])
        entry["retained"] = False
        entry["retention_reasons"] = reasons
        entry["prompt_file"] = None
        source = staged_paths.get(key)
        if not allow_retention or not reasons or source is None or not source.is_file():
            continue
        mode_dir = "data" if entry.get("mode") == "data" else "analysis"
        destination = prompts_dir / mode_dir / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
        entry["retained"] = True
        entry["prompt_file"] = str(destination.relative_to(artifact_root))
    return retention_reasons


def build_retained_prompt_manifest(
    entries: Sequence[Mapping[str, object]],
    *,
    run_id: str,
    retention_reasons: Mapping[str, Sequence[str]],
    retention_blocked: bool = False,
) -> dict[str, object]:
    retained_entries = [
        {
            "stable_key": stable_metric_key_text(entry),
            "prompt_path": entry.get("prompt_file"),
            "reasons": list(entry.get("retention_reasons", [])) if isinstance(entry.get("retention_reasons"), list) else [],
            "chars": entry.get("rendered_prompt_chars"),
            "bytes": entry.get("rendered_prompt_bytes"),
            "sha256": entry.get("rendered_prompt_sha256"),
            "category": entry.get("category"),
            "category_tags": entry.get("category_tags"),
        }
        for entry in sorted(entries, key=stable_metric_key)
        if entry.get("retained") is True
    ]
    measured_count = sum(1 for entry in entries if entry.get("status") == "ok")
    return {
        "schema_version": 1,
        "run_id": run_id,
        "status": "blocked_by_secret_scan" if retention_blocked else "complete",
        "stable_key_fields": ["user_alias", "mode", "domain", "selection_id", "scope_alias", "period_label", "detail_level"],
        "selection_policy": {
            "named_case_count": len(NAMED_PROMPT_RETENTION),
            "global_representatives": ["minimum", "maximum", "median", "p10", "p25", "p75", "p90", "p95", "p99"],
            "percentile_method": "nearest_rank_ceil_p_times_n_v1",
            "nearest_prompt_tie_break": "absolute_character_distance_then_lexicographic_stable_key_v1",
            "deduplication": "stable_key_with_ordered_unique_reasons_v1",
        },
        "measured_count": measured_count,
        "planned_retention_count": len(retention_reasons),
        "retained_count": len(retained_entries),
        "entries": retained_entries,
    }


def build_manual_review_placeholder(run_id: str, review_kind: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "review_kind": review_kind,
        "status": "not_performed",
        "reviews": [],
    }


def build_comparison_baseline_manifest(
    run_id: str,
    baseline_path: Path | None,
    comparisons: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    if baseline_path is None:
        return {
            "schema_version": 1,
            "run_id": run_id,
            "status": "not_provided",
            "baseline_metrics_path": None,
            "baseline_sha256": None,
            "comparison_row_count": 0,
        }
    resolved = baseline_path.expanduser().resolve()
    return {
        "schema_version": 1,
        "run_id": run_id,
        "status": "compared",
        "baseline_metrics_path": repository_path(resolved),
        "baseline_sha256": hash_file(resolved),
        "comparison_row_count": len(comparisons),
    }


def _svg_text(x: float, y: float, text: object, *, size: int = 13, anchor: str = "start", weight: str = "normal") -> str:
    return f'<text x="{x:.2f}" y="{y:.2f}" font-family="sans-serif" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="#111827">{html.escape(str(text))}</text>'


def _svg_document(title: str, width: int, height: int, body: Sequence[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            _svg_text(width / 2, 28, title, size=18, anchor="middle", weight="bold"),
            *body,
            "</svg>",
            "",
        ]
    )


def build_category_range_box_svg(entries: Sequence[Mapping[str, object]]) -> str:
    successful = [entry for entry in entries if entry.get("status") == "ok"]
    grouped: defaultdict[str, list[int]] = defaultdict(list)
    for entry in successful:
        grouped[str(entry.get("category") or "financial")].append(int(entry.get("rendered_prompt_chars") or 0))
    categories = [category for category in PROMPT_CATEGORY_CLASSES if category in grouped]
    width = 1000
    height = max(150, 75 + len(categories) * 52)
    max_chars = max(1, max((max(values) for values in grouped.values()), default=1))

    def x(value: float) -> float:
        return 230 + value / max_chars * 720

    body: list[str] = []
    for index, category in enumerate(categories):
        stats = numeric_distribution_stats(grouped[category])
        y = 70 + index * 52
        minimum = float(stats["minimum"] or 0)
        maximum = float(stats["maximum"] or 0)
        p25 = float(stats["p25"] or 0)
        median = float(stats["median"] or 0)
        p75 = float(stats["p75"] or 0)
        body.extend(
            [
                _svg_text(215, y + 5, category, anchor="end"),
                f'<line x1="{x(minimum):.2f}" y1="{y:.2f}" x2="{x(maximum):.2f}" y2="{y:.2f}" stroke="#475569" stroke-width="2"/>',
                f'<rect x="{x(p25):.2f}" y="{y - 11:.2f}" width="{max(1.0, x(p75) - x(p25)):.2f}" height="22" fill="#bfdbfe" stroke="#2563eb"/>',
                f'<line x1="{x(median):.2f}" y1="{y - 13:.2f}" x2="{x(median):.2f}" y2="{y + 13:.2f}" stroke="#1d4ed8" stroke-width="3"/>',
                _svg_text(960, y + 5, f"n={stats['count']}", size=11),
            ]
        )
    return _svg_document("Prompt characters by category: range and quartile box", width, height, body)


def build_period_detail_svg(entries: Sequence[Mapping[str, object]]) -> str:
    successful = [entry for entry in entries if entry.get("status") == "ok"]
    grouped: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
    for entry in successful:
        grouped[(str(entry.get("period_label")), str(entry.get("detail_level")))].append(int(entry.get("rendered_prompt_chars") or 0))
    keys = [(period, detail) for period in PUBLIC_CATALOG_V1_PERIODS for detail in DEFAULT_DETAILS if (period, detail) in grouped]
    means = {key: statistics.fmean(grouped[key]) for key in keys}
    maximum = max(1, max(means.values(), default=1))
    width = 1000
    height = 390
    body: list[str] = []
    for index, key in enumerate(keys):
        value = means[key]
        bar_width = 105
        x = 95 + index * 145
        bar_height = value / maximum * 245
        y = 315 - bar_height
        body.extend(
            [
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width}" height="{bar_height:.2f}" fill="#60a5fa"/>',
                _svg_text(x + bar_width / 2, 338, f"{key[0]} {key[1]}", size=11, anchor="middle"),
                _svg_text(x + bar_width / 2, y - 7, f"{value:.0f}", size=11, anchor="middle"),
            ]
        )
    return _svg_document("Mean prompt characters by period and detail", width, height, body)


def build_composition_share_svg(entries: Sequence[Mapping[str, object]]) -> str:
    summary = build_composition_summary(entries)
    components = summary["components"]
    width = 1000
    height = 260
    colors = {
        "financial": "#16a34a",
        "technical": "#2563eb",
        "coverage/provenance": "#f59e0b",
        "instructions/contracts": "#7c3aed",
    }
    body: list[str] = []
    cursor = 80.0
    usable = 840.0
    for index, component in enumerate(COMPOSITION_COMPONENTS):
        row = components[component] if isinstance(components, Mapping) else {}
        percent = float(row.get("percent") or 0) if isinstance(row, Mapping) else 0.0
        segment = usable * percent / 100
        body.append(f'<rect x="{cursor:.2f}" y="75" width="{segment:.2f}" height="48" fill="{colors[component]}"/>')
        if segment >= 55:
            body.append(_svg_text(cursor + segment / 2, 105, f"{percent:.1f}%", size=12, anchor="middle", weight="bold"))
        legend_y = 160 + index * 22
        body.append(f'<rect x="190" y="{legend_y - 12}" width="14" height="14" fill="{colors[component]}"/>')
        body.append(_svg_text(215, legend_y, f"{component}: {percent:.2f}%", size=12))
        cursor += segment
    return _svg_document("Corpus composition share", width, height, body)


def build_before_after_svg(comparisons: Sequence[Mapping[str, object]]) -> str:
    grouped_before: defaultdict[str, list[int]] = defaultdict(list)
    grouped_after: defaultdict[str, list[int]] = defaultdict(list)
    for row in comparisons:
        before = row.get("previous_chars")
        after = row.get("current_chars")
        stable_key = str(row.get("stable_key") or "").split("|")
        if isinstance(before, int) and isinstance(after, int) and len(stable_key) >= 3:
            domain = stable_key[2]
            grouped_before[domain].append(before)
            grouped_after[domain].append(after)
    domains = [domain for domain in ("portfolio", "broker", "asset", "fx") if grouped_before[domain]]
    width = 1000
    height = 390
    maximum = max(
        1,
        max(
            [
                *(statistics.fmean(grouped_before[domain]) for domain in domains),
                *(statistics.fmean(grouped_after[domain]) for domain in domains),
            ],
            default=1,
        ),
    )
    body: list[str] = []
    for index, domain in enumerate(domains):
        before = statistics.fmean(grouped_before[domain])
        after = statistics.fmean(grouped_after[domain])
        x = 125 + index * 205
        for offset, value, color, label in ((0, before, "#94a3b8", "before"), (58, after, "#2563eb", "after")):
            bar_height = value / maximum * 245
            y = 315 - bar_height
            body.extend(
                [
                    f'<rect x="{x + offset:.2f}" y="{y:.2f}" width="48" height="{bar_height:.2f}" fill="{color}"/>',
                    _svg_text(x + offset + 24, y - 7, f"{value:.0f}", size=10, anchor="middle"),
                    _svg_text(x + offset + 24, 338, label, size=10, anchor="middle"),
                ]
            )
        body.append(_svg_text(x + 53, 365, domain, size=12, anchor="middle", weight="bold"))
    return _svg_document("Mean prompt characters before and after", width, height, body)


def build_probe_svgs(entries: Sequence[Mapping[str, object]], comparisons: Sequence[Mapping[str, object]]) -> dict[str, str]:
    charts = {
        "category_range_box.svg": build_category_range_box_svg(entries),
        "period_detail.svg": build_period_detail_svg(entries),
        "composition_share.svg": build_composition_share_svg(entries),
    }
    if comparisons:
        charts["before_after.svg"] = build_before_after_svg(comparisons)
    return charts


def write_probe_svgs(charts_dir: Path, entries: Sequence[Mapping[str, object]], comparisons: Sequence[Mapping[str, object]]) -> list[str]:
    charts_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for filename, content in sorted(build_probe_svgs(entries, comparisons).items()):
        path = charts_dir / filename
        path.write_text(content, encoding="utf-8", newline="")
        paths.append(str(path.name))
    return paths


def _summary_markdown(metrics_payload: Mapping[str, object], manifest: Mapping[str, object]) -> str:
    entries = _metric_entries(metrics_payload)
    successful = [entry for entry in entries if entry.get("status") == "ok"]
    data_entries = [entry for entry in successful if entry.get("mode") == "data"]
    analysis_entries = [entry for entry in successful if entry.get("mode") == "analysis"]
    failed = [entry for entry in entries if entry.get("status") == "failed"]
    skipped = [entry for entry in entries if entry.get("status") == "skipped"]
    retained = [entry for entry in successful if entry.get("retained") is True]
    new_semantic_dataset_entries = [entry for entry in successful if entry.get("comparison_cohort") == "new_semantic_dataset"]
    heaviest_data = max(data_entries, key=lambda item: int(item.get("rendered_prompt_chars") or 0), default=None)
    heaviest_analysis = max(analysis_entries, key=lambda item: int(item.get("rendered_prompt_chars") or 0), default=None)

    def describe(entry: Mapping[str, object] | None) -> str:
        if not entry:
            return "n/a"
        return f"{entry.get('user_alias')}/{entry.get('selection_id')}/{entry.get('scope_alias')}/{entry.get('period_label')}/{entry.get('detail_level')} ({entry.get('rendered_prompt_chars')} chars)"

    catalog = manifest.get("catalog", {})
    read_only = manifest.get("read_only_verification", {})
    secret_scan = manifest.get("secret_scan", {})
    environment = manifest.get("environment", {})
    filters = manifest.get("filters", {})
    dimensions = metrics_payload.get("dimension_summary", {})
    dimensions = dimensions if isinstance(dimensions, Mapping) else {}
    overall_dimensions = dimensions.get("overall", {})
    overall_dimensions = overall_dimensions if isinstance(overall_dimensions, Mapping) else {}
    quality = metrics_payload.get("quality_summary", {})
    quality = quality if isinstance(quality, Mapping) else {}
    lines = [
        "# AI Export Real Prompt Probe Summary",
        "",
        f"- Timestamp: {manifest.get('timestamp')}",
        f"- Run ID: {manifest.get('run_id')}",
        f"- Commit: {manifest.get('git', {}).get('commit') if isinstance(manifest.get('git'), dict) else None}",
        f"- Dirty worktree: {manifest.get('git', {}).get('dirty') if isinstance(manifest.get('git'), dict) else None}",
        f"- Environment: Python {environment.get('python')}, {environment.get('platform')}, production-mode API on SQLite backup",
        f"- Expected public manifest shape: {filters.get('manifest_shape') if isinstance(filters, dict) else None}",
        f"- Successful users: {', '.join(str(item) for item in manifest.get('successful_users', [])) or 'none'}",
        f"- Discovered catalog: {catalog.get('dataset_count', 0)} datasets, {catalog.get('analysis_count', 0)} analyses",
        f"- Expected prompts: {len(entries)}",
        f"- Measured prompts: {len(successful)}",
        f"- Retained prompt files: {len(retained)}",
        f"- Generated data prompts: {len(data_entries)}",
        f"- Generated analysis prompts: {len(analysis_entries)}",
        f"- New semantic-dataset prompts: {len(new_semantic_dataset_entries)}",
        f"- Failed prompts: {len(failed)}",
        f"- Skipped prompts: {len(skipped)}",
        f"- Diagnostic corpus rendered characters: {sum(int(entry.get('rendered_prompt_chars') or 0) for entry in successful)}",
        f"- Diagnostic corpus rendered bytes: {sum(int(entry.get('rendered_prompt_bytes') or 0) for entry in successful)}",
        f"- Diagnostic corpus estimated token-equivalents (chars/4): {sum(float(entry.get('rendered_prompt_estimated_token_equivalent') or 0) for entry in successful)}",
        f"- Heaviest data prompt: {describe(heaviest_data)}",
        f"- Heaviest analysis prompt: {describe(heaviest_analysis)}",
        f"- Median data prompt chars: {_median(int(entry.get('rendered_prompt_chars') or 0) for entry in data_entries)}",
        f"- Median analysis prompt chars: {_median(int(entry.get('rendered_prompt_chars') or 0) for entry in analysis_entries)}",
        f"- Light prompts (<=10,000 estimated token-equivalents): {overall_dimensions.get('light', 0)}",
        f"- Medium prompts (>10,000 and <=50,000 estimated token-equivalents): {overall_dimensions.get('medium', 0)}",
        f"- Heavy prompts (>50,000 estimated token-equivalents): {overall_dimensions.get('heavy', 0)}",
        f"- Very heavy prompts (>100,000 estimated token-equivalents, heavy subset): {overall_dimensions.get('very_heavy', 0)}",
        f"- Public-output check violations: {quality.get('public_output_violations', 0)}",
        f"- FX failures: {sum(1 for entry in failed if entry.get('domain') == 'fx')}",
        f"- Secret scan: {secret_scan.get('status', 'pending')}",
        f"- Source DB read-only: {read_only.get('source_unchanged')}",
        f"- Excluded composed datasets: {len(manifest.get('excluded_datasets', []))}",
        "",
        "Corpus totals and character/token-equivalent measurements are diagnostic only. Final prompt files are retained selectively; canonical backend JSON measurements are also diagnostic only.",
        "",
    ]
    return "\n".join(lines)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="")


def _passwords_for_users(users: Sequence[str]) -> dict[str, str]:
    common = os.environ.get("LIBREFOLIO_AI_EXPORT_PROBE_PASSWORD") or os.environ.get("LIBREFOLIO_AI_EXPORT_PASSWORD")
    passwords: dict[str, str] = {}
    for user in users:
        suffix = re.sub(r"[^A-Z0-9]+", "_", user.upper())
        password = os.environ.get(f"LIBREFOLIO_AI_EXPORT_PROBE_PASSWORD_{suffix}") or os.environ.get(f"LIBREFOLIO_AI_EXPORT_PASSWORD_{suffix}") or common
        if password is None:
            password = getpass.getpass(f"Password for {user}: ")
        if not password:
            raise ProbeError(f"Empty password supplied for user alias: {user}")
        passwords[user] = password
    return passwords


def build_artifact_aliases(users: Sequence[str], *, anonymize: bool) -> dict[str, str]:
    """Map runtime login aliases to artifact-safe user labels."""

    unique_users = tuple(dict.fromkeys(users))
    if anonymize:
        return {user: f"user_anon_{index:02d}" for index, user in enumerate(unique_users, start=1)}
    return {user: user for user in unique_users}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user",
        action="append",
        choices=DEFAULT_USERS,
        help=("User alias to probe; repeatable. Default: marco for representative, " "alfy + marco for exhaustive"),
    )
    parser.add_argument("--mode", choices=("data", "analysis"))
    parser.add_argument("--domain", choices=("portfolio", "broker", "asset", "fx"))
    parser.add_argument("--period", choices=(*DEFAULT_PERIODS, "Custom"))
    parser.add_argument("--detail", choices=DEFAULT_DETAILS)
    parser.add_argument(
        "--target-case",
        action="append",
        default=[],
        metavar="USER|SELECTION|PERIOD|DETAIL|SCOPE",
        help="Run one exact targeted case; repeatable. Scope is 'all', 'representative', or 'broker=<display name>'.",
    )
    parser.add_argument(
        "--profile",
        choices=("tuning-v2", "representative", PUBLIC_CATALOG_V1_PROFILE, "exhaustive"),
        default="tuning-v2",
        help="tuning-v2 keeps the internal tuning matrix; public-catalog-v1 runs 19 public selections × 3M/1Y × compact/standard/full",
    )
    parser.add_argument("--manifest-shape", choices=("legacy", "slim"), default="slim", help="Expected public technical manifest shape")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-url", help="Local URL used to reach the copied-DB diagnostic API; must match --port")
    parser.add_argument("--keep-canonical", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--compare-with", type=Path)
    parser.add_argument("--fail-on-regression", action="store_true")
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument(
        "--minimum-fx-history-days",
        type=int,
        default=365,
        help="Minimum source-history span used only to select the representative FX pair",
    )
    parser.add_argument("--port", type=int, default=6043)
    parser.add_argument(
        "--normalize-copy-credentials",
        action="store_true",
        help="If documented credentials no longer match, reset password hashes on the disposable DB copy only",
    )
    return parser.parse_args(argv)


def run_probe(args: argparse.Namespace) -> int:  # noqa: C901 — sequential probe orchestration driver
    target_cases = tuple(parse_target_case(value) for value in args.target_case)
    public_catalog_v1_run = args.profile == PUBLIC_CATALOG_V1_PROFILE and not target_cases
    if len(target_cases) != len(set(target_cases)):
        raise ProbeError("Duplicate --target-case entries are not allowed")
    if target_cases and any(value is not None for value in (args.mode, args.domain, args.period, args.detail)):
        raise ProbeError("--target-case cannot be combined with --mode/--domain/--period/--detail")
    if public_catalog_v1_run and any(value is not None for value in (args.mode, args.domain, args.period, args.detail)):
        raise ProbeError(f"public-catalog-v1 is an exact {PUBLIC_CATALOG_V1_EXPECTED_CASE_COUNT}-case profile and cannot be filtered")
    if public_catalog_v1_run and args.user and len(set(args.user)) != 1:
        raise ProbeError("public-catalog-v1 requires exactly one deterministic user")
    default_users = (DEFAULT_REPRESENTATIVE_USER,) if args.profile in {"tuning-v2", "representative", PUBLIC_CATALOG_V1_PROFILE} else DEFAULT_USERS
    users = tuple(dict.fromkeys(case.user_alias for case in target_cases)) if target_cases else tuple(dict.fromkeys(args.user or default_users))
    artifact_aliases = build_artifact_aliases(users, anonymize=bool(target_cases) or public_catalog_v1_run)
    passwords = _passwords_for_users(users)
    actual_secrets = tuple(passwords.values())
    source_db = args.source_db.expanduser().resolve()
    if not source_db.is_file():
        raise ProbeError(f"Source database not found: {source_db}")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = args.output_dir.expanduser().resolve() / run_id
    prompts_dir = run_dir / "prompts"
    data_prompts_dir = prompts_dir / "data"
    analysis_prompts_dir = prompts_dir / "analysis"
    prompt_staging_dir = run_dir / ".prompt_staging"
    staging_data_prompts_dir = prompt_staging_dir / "data"
    staging_analysis_prompts_dir = prompt_staging_dir / "analysis"
    canonical_dir = run_dir / "canonical"
    runtime_data_dir = run_dir / ".runtime_data"
    source_snapshot_dir = run_dir / ".source_snapshot"
    data_prompts_dir.mkdir(parents=True)
    analysis_prompts_dir.mkdir(parents=True)
    if public_catalog_v1_run:
        staging_data_prompts_dir.mkdir(parents=True)
        staging_analysis_prompts_dir.mkdir(parents=True)
    canonical_dir.mkdir()
    source_snapshot_db = source_snapshot_dir / "sqlite" / "app.db"
    runtime_db = runtime_data_dir / "sqlite" / "app.db"
    production_source_hash_before = hash_sqlite_family(source_db)
    active_production_processes_before = _active_production_processes()
    sqlite_backup(source_db, source_snapshot_db)
    source_snapshot_hash_before = hash_sqlite_family(source_snapshot_db)
    sqlite_backup(source_snapshot_db, runtime_db)
    credential_status = prepare_runtime_credentials(
        runtime_db,
        passwords,
        normalize=args.normalize_copy_credentials,
    )
    copy_hash_before = hash_sqlite_family(runtime_db)
    inventories: dict[str, dict[str, object]] = {}
    entries: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    successful_users: list[str] = []
    actual_id_map: dict[str, object] = {}
    catalog_record: dict[str, object] = {}
    excluded_datasets: list[dict[str, object]] = []
    http_events: list[dict[str, object]] = []

    @contextmanager
    def api_context() -> Iterator[str]:
        requested_url = args.base_url.rstrip("/") if args.base_url else None
        if requested_url:
            parsed = urlsplit(requested_url)
            if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != args.port or parsed.path not in ("", "/"):
                raise ProbeError("--base-url must identify the local copied-DB probe server and match --port")
            yield requested_url
            return
        with local_api_server(runtime_data_dir, args.port) as url:
            yield url

    try:
        for user in users:
            inventories[user] = collect_user_inventory(runtime_db, user, minimum_fx_history_days=args.minimum_fx_history_days)
        with api_context() as base_url, FrontendBridge() as bridge:
            for user_alias in users:
                user_data = inventories[user_alias]
                with httpx.Client(base_url=base_url, timeout=600, follow_redirects=False) as client:
                    artifact_user_alias = artifact_aliases[user_alias]
                    login_response, _login_payload, login_duration = _request_json(
                        client,
                        "POST",
                        f"{API_PREFIX}/auth/login",
                        json={"username": user_alias, "password": passwords[user_alias]},
                    )
                    http_events.append(
                        {
                            "user_alias": artifact_user_alias,
                            "method": "POST",
                            "route": f"{API_PREFIX}/auth/login",
                            "status": login_response.status_code,
                            "duration_ms": round(login_duration, 3),
                        }
                    )
                    if login_response.status_code != 200:
                        failures.append(
                            {
                                "user_alias": artifact_user_alias,
                                "status": "failed",
                                "failure_code": f"login_http_{login_response.status_code}",
                                "failure_message_sanitized": "Login failed",
                            }
                        )
                        continue
                    successful_users.append(artifact_user_alias)
                    catalog_response, catalog_payload, catalog_duration = _request_json(client, "GET", f"{API_PREFIX}/ai-export/catalog")
                    http_events.append(
                        {
                            "user_alias": artifact_user_alias,
                            "method": "GET",
                            "route": f"{API_PREFIX}/ai-export/catalog",
                            "status": catalog_response.status_code,
                            "duration_ms": round(catalog_duration, 3),
                        }
                    )
                    if catalog_response.status_code != 200 or not isinstance(catalog_payload, dict):
                        failures.append(
                            {
                                "user_alias": artifact_user_alias,
                                "status": "failed",
                                "failure_code": f"catalog_http_{catalog_response.status_code}",
                                "failure_message_sanitized": "Catalog discovery failed",
                            }
                        )
                        continue
                    selections = (
                        public_catalog_v1_selections(
                            discover_catalog(catalog_payload),
                            mode=args.mode,
                            domain=args.domain,
                        )
                        if public_catalog_v1_run
                        else discover_catalog(catalog_payload, mode=args.mode, domain=args.domain)
                    )
                    user_target_cases = tuple(case for case in target_cases if case.user_alias == user_alias)
                    if user_target_cases:
                        target_selection_ids = {case.selection_id for case in user_target_cases}
                        selections = [selection for selection in selections if str(selection["id"]) in target_selection_ids]
                        missing_selection_ids = target_selection_ids - {str(selection["id"]) for selection in selections}
                        if missing_selection_ids:
                            raise ProbeError(f"Target selections absent from runtime catalog: {sorted(missing_selection_ids)}")
                    if args.profile == "tuning-v2" and not target_cases:
                        excluded_datasets = tuning_v2_exclusions(catalog_payload)
                        excluded_ids = {str(item["dataset_id"]) for item in excluded_datasets}
                        selections = [selection for selection in selections if not (selection["kind"] == "dataset" and str(selection["id"]) in excluded_ids)]
                    catalog_hash = sha256_text(canonical_json(catalog_payload))
                    if catalog_record and catalog_record.get("sha256") != catalog_hash:
                        failures.append(
                            {
                                "user_alias": artifact_user_alias,
                                "status": "failed",
                                "failure_code": "catalog_changed_between_users",
                                "failure_message_sanitized": "Runtime catalog changed during probe",
                            }
                        )
                        continue
                    catalog_record = {
                        "schema_version": catalog_payload.get("schema_version"),
                        "catalog_version": catalog_payload.get("catalog_version"),
                        "dataset_count": len(catalog_payload.get("datasets", [])),
                        "analysis_count": len(catalog_payload.get("analyses", [])),
                        "dataset_ids": sorted(str(item.get("id")) for item in catalog_payload.get("datasets", []) if isinstance(item, dict)),
                        "analysis_ids": sorted(str(item.get("id")) for item in catalog_payload.get("analyses", []) if isinstance(item, dict)),
                        "sha256": catalog_hash,
                    }
                    scopes = build_user_scopes(user_data)
                    if args.profile in {"tuning-v2", "representative"} and not target_cases:
                        scopes = representative_scopes(scopes)
                    scopes = [scope for scope in scopes if args.domain is None or scope["domain"] == args.domain]
                    actual_id_map[artifact_user_alias] = {
                        "user_id": user_data["user_id"],
                        "brokers": {scope["scope_alias"]: scope["actual"] for scope in scopes if scope["domain"] in ("broker", "portfolio") and scope["scope_alias"] != "all"},
                        "asset": next((scope["actual"] for scope in scopes if scope["domain"] == "asset"), None),
                        "fx": next((scope["actual"] for scope in scopes if scope["domain"] == "fx"), None),
                    }
                    periods = (args.period,) if args.period else None
                    details = (args.detail,) if args.detail else None
                    for selection in selections:
                        if user_target_cases:
                            selection_targets = tuple(case for case in user_target_cases if case.selection_id == str(selection["id"]))
                            for target in selection_targets:
                                scope = select_target_scope(scopes, target, domain=str(selection["domain"]))
                                case = build_period_detail_matrix(
                                    periods=(target.period_label,),
                                    details=(target.detail_level,),
                                )[0]
                                group = sanitize_filename_part(target.selection_id)
                                target_prompts_dir = prompts_dir / group
                                target_prompts_dir.mkdir(parents=True, exist_ok=True)
                                metric, failure = _run_case(
                                    run_id=run_id,
                                    user_alias=artifact_user_alias,
                                    catalog=catalog_payload,
                                    selection=selection,
                                    scope=scope,
                                    case=case,
                                    client=client,
                                    bridge=bridge,
                                    prompts_dir=target_prompts_dir,
                                    canonical_dir=canonical_dir,
                                    artifact_root=run_dir,
                                    keep_canonical=args.keep_canonical,
                                    locale=str(user_data["locale"]),
                                    response_language=str(user_data["response_language"]),
                                    actual_secrets=actual_secrets,
                                    manifest_shape=args.manifest_shape,
                                )
                                entries.append(metric)
                                if failure is not None:
                                    failures.append(failure)
                            continue
                        if public_catalog_v1_run:
                            selected_scope = public_catalog_v1_scope(scopes, selection)
                            matching_scopes = [selected_scope] if selected_scope is not None else []
                        else:
                            matching_scopes = [scope for scope in scopes if scope["domain"] == selection["domain"]]
                        if not matching_scopes:
                            skipped_metrics = _missing_scope_metrics(
                                run_id,
                                artifact_user_alias,
                                selection,
                                period_filter=args.period,
                                detail_filter=args.detail,
                                manifest_shape=args.manifest_shape,
                                profile=args.profile,
                                catalog=catalog_payload,
                            )
                            entries.extend(skipped_metrics)
                            failures.extend(dict(metric) for metric in skipped_metrics)
                            continue
                        for scope in matching_scopes:
                            cases = (
                                tuning_v2_cases(
                                    selection,
                                    catalog_payload,
                                    period_filter=args.period,
                                    detail_filter=args.detail,
                                )
                                if args.profile == "tuning-v2"
                                else (
                                    public_catalog_v1_cases(
                                        selection,
                                        period_filter=args.period,
                                        detail_filter=args.detail,
                                    )
                                    if public_catalog_v1_run
                                    else (
                                        representative_cases(
                                            selection,
                                            period_filter=args.period,
                                            detail_filter=args.detail,
                                        )
                                        if args.profile == "representative"
                                        else build_period_detail_matrix(
                                            periods=periods,
                                            details=details,
                                            custom_start=scope.get("custom_start"),
                                            snapshot_as_of=user_data["snapshot_as_of"],
                                        )
                                    )
                                )
                            )
                            supported_details = {str(item) for item in selection.get("supported_detail_levels", DEFAULT_DETAILS)}
                            for case in cases:
                                if str(case["detail_level"]) not in supported_details:
                                    continue
                                metric, failure = _run_case(
                                    run_id=run_id,
                                    user_alias=artifact_user_alias,
                                    catalog=catalog_payload,
                                    selection=selection,
                                    scope=scope,
                                    case=case,
                                    client=client,
                                    bridge=bridge,
                                    prompts_dir=(staging_data_prompts_dir if public_catalog_v1_run and selection["kind"] == "dataset" else (staging_analysis_prompts_dir if public_catalog_v1_run else (data_prompts_dir if selection["kind"] == "dataset" else analysis_prompts_dir))),
                                    canonical_dir=canonical_dir,
                                    artifact_root=run_dir,
                                    keep_canonical=args.keep_canonical,
                                    locale=str(user_data["locale"]),
                                    response_language=str(user_data["response_language"]),
                                    actual_secrets=actual_secrets,
                                    manifest_shape=args.manifest_shape,
                                    stage_prompt=public_catalog_v1_run,
                                )
                                entries.append(metric)
                                if failure is not None:
                                    failures.append(failure)
    finally:
        copy_hash_after = hash_sqlite_family(runtime_db) if runtime_db.exists() else {}
        source_snapshot_hash_after = hash_sqlite_family(source_snapshot_db) if source_snapshot_db.exists() else {}
        production_source_hash_after = hash_sqlite_family(source_db)
        active_production_processes_after = _active_production_processes()
        shutil.rmtree(runtime_data_dir, ignore_errors=True)
        shutil.rmtree(source_snapshot_dir, ignore_errors=True)

    for user_alias, user_data in inventories.items():
        artifact_user_alias = artifact_aliases[user_alias]
        breadth = next(
            (
                entry.get("technical_diagnostics")
                for entry in entries
                if entry.get("user_alias") == artifact_user_alias
                and entry.get("domain") == "portfolio"
                and entry.get("scope_alias") == "all"
                and entry.get("status") == "ok"
                and isinstance(entry.get("technical_diagnostics"), dict)
                and entry["technical_diagnostics"].get("covered_asset_count") is not None
            ),
            None,
        )
        if isinstance(breadth, dict) and isinstance(user_data.get("inventory"), dict):
            # Period-scoped runtime counts kept DISTINCT from the all-time raw
            # SQL fields (position_legs/unique_held_assets): never conflate the
            # all-time leg count with the period leg/contributor counts.
            user_data["inventory"]["technical_covered_assets"] = breadth.get("covered_asset_count")
            user_data["inventory"]["runtime_period_position_leg_count"] = breadth.get("period_position_leg_count")
            user_data["inventory"]["runtime_period_contributor_asset_count"] = breadth.get("period_contributor_asset_count")
            user_data["inventory"]["runtime_period_eligible_asset_count"] = breadth.get("eligible_asset_count")
            user_data["inventory"]["runtime_period_covered_asset_count"] = breadth.get("covered_asset_count")
        asset_diagnostics = next(
            (
                entry.get("technical_diagnostics")
                for entry in entries
                if entry.get("user_alias") == artifact_user_alias and entry.get("domain") == "asset" and entry.get("status") == "ok" and isinstance(entry.get("technical_diagnostics"), dict) and int(entry["technical_diagnostics"].get("indicator_instance_count") or 0) > 0
            ),
            None,
        )
        mapped_asset = actual_id_map.get(artifact_user_alias, {}).get("asset") if isinstance(actual_id_map.get(artifact_user_alias), dict) else None
        if isinstance(mapped_asset, dict) and isinstance(asset_diagnostics, dict):
            mapped_asset["technical_indicator_count"] = asset_diagnostics.get("indicator_instance_count")

    comparisons: list[dict[str, object]] = []
    if args.compare_with:
        previous = json.loads(args.compare_with.expanduser().read_text(encoding="utf-8"))
        comparisons = compare_metric_runs(
            {"entries": entries},
            previous,
            include_removed=not bool(target_cases),
        )
    staged_prompt_paths = collect_staged_prompt_paths(entries, run_dir)
    staged_prompt_file_count = sum(1 for path in prompt_staging_dir.rglob("*") if path.is_file()) if public_catalog_v1_run else 0
    retention_reasons: dict[str, list[str]] = {}
    if public_catalog_v1_run:
        retention_reasons = select_prompt_retention_reasons(entries)
        for entry in entries:
            entry["retention_reasons"] = retention_reasons.get(stable_metric_key_text(entry), [])
    else:
        mark_direct_prompt_retention(entries, "target_case" if target_cases else f"{args.profile}_profile_full_retention")
    metrics_payload: dict[str, object] = {
        "run_id": run_id,
        "generated_at": utc_now_iso(),
        "entries": entries,
        "comparison": comparisons,
        "dimension_summary": build_dimension_summary(entries),
        "composition_summary": build_composition_summary(entries),
        "quality_summary": build_quality_summary(entries),
    }
    manifest: dict[str, object] = {
        "run_id": run_id,
        "timestamp": utc_now_iso(),
        "git": _git_state(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "source_db": repository_path(source_db),
            "api_mode": "external_local_url" if args.base_url else "managed_local_copied_db",
            "base_url": args.base_url or f"http://127.0.0.1:{args.port}",
        },
        "users_requested": [artifact_aliases[user] for user in users],
        "successful_users": successful_users,
        "catalog": catalog_record,
        "filters": {
            "mode": args.mode,
            "domain": args.domain,
            "period": args.period,
            "detail": args.detail,
            "manifest_shape": args.manifest_shape,
            "profile": args.profile,
            "target_case_count": len(target_cases),
            "target_selection_ids": sorted({case.selection_id for case in target_cases}),
        },
        "excluded_datasets": excluded_datasets,
        "sampling_profile": {
            "representative_user_default": DEFAULT_REPRESENTATIVE_USER,
            "representative_scope_policy": (
                "explicit target-case scopes"
                if target_cases
                else ("one deterministic representative scope per public selection" if public_catalog_v1_run else "portfolio all; broker with most positions then longest history; one deterministic longest-history asset; one deterministic longest-history FX pair")
            ),
            "case_policy": (
                "exact explicit target cases only"
                if target_cases
                else (
                    "exact 19 selections x 3M/1Y x compact/standard/full; no 6M"
                    if public_catalog_v1_run
                    else ("base datasets: 3M/6M/1Y x compact/standard/full; analyses with temporal data: 3M/1Y x compact/standard/full; all_data excluded from tuning" if args.profile == "tuning-v2" else "representative or exhaustive legacy profile")
                )
            ),
            "selection_reason_policy": (
                {
                    "asset": "longest history meeting minimum, then observations and stable asset key",
                    "fx": "longest history meeting configured minimum, then observations and canonical pair key; partial/unavailable state is classified from measured output rather than extra Cartesian cases",
                }
                if public_catalog_v1_run
                else {}
            ),
            "public_selection_ids": list(PUBLIC_CATALOG_V1_SELECTIONS) if public_catalog_v1_run else [],
            "expected_case_count": len(PUBLIC_CATALOG_V1_SELECTIONS) * len(PUBLIC_CATALOG_V1_PERIODS) * len(DEFAULT_DETAILS) if public_catalog_v1_run else None,
        },
        "inventory": {artifact_aliases[alias]: data["inventory"] for alias, data in inventories.items()},
        "inventory_methods": {
            "accessible_broker_count": "ALL-TIME access universe: BrokerUserAccess rows available to the probed user. It is not reduced by current positions or the selected period.",
            "scoped_broker_count": "REQUEST scope: broker IDs selected for one Portfolio/Broker calculation after access validation. A scoped broker may have no current positions.",
            "position_broker_count": "AS-OF position universe: distinct brokers with current open holdings at snapshot_as_of.",
            "period_contributor_broker_count": "PERIOD-SCOPED contributor universe: distinct brokers represented by performance contribution rows in the selected period, including historical-only contributors.",
            "position_legs": "ALL-TIME raw SQL: count of (broker_id, asset_id) groups with nonzero net all-time transaction quantity. NOT period-scoped and NOT directly comparable to runtime_period_position_leg_count.",
            "unique_held_assets": "ALL-TIME raw SQL: distinct asset IDs with nonzero net all-time quantity, broker-deduplicated.",
            "technical_eligible_assets": "ALL-TIME heuristic SQL: assets with at least 365 calendar days and 250 stored price observations. NOT the period eligible universe.",
            "runtime_period_position_leg_count": "PERIOD-SCOPED runtime: portfolio.technical_breadth.period_position_leg_count (period (broker_id, asset_id) legs before eligibility, incl. fully-sold-in-period). Compare against period counts only, never against all-time position_legs.",
            "runtime_period_contributor_asset_count": "PERIOD-SCOPED runtime: portfolio.technical_breadth.period_contributor_asset_count (unique assets across period legs before eligibility).",
            "runtime_period_eligible_asset_count": "PERIOD-SCOPED runtime: portfolio.technical_breadth.eligible_asset_count (currently-held nonzero-end-value eligible assets, broker-deduplicated).",
            "runtime_period_covered_asset_count": "PERIOD-SCOPED runtime: portfolio.technical_breadth.covered_asset_count (eligible assets with classifiable technical coverage).",
            "recorded_cost_transaction_count": "ALL-TIME deterministic scope selector input: typed FEE/TAX rows for an accessible Broker. Period-specific recorded/unavailable status remains measured from rendered output.",
            "recorded_cost_transaction_count_1y": "LATEST-1Y deterministic cost-efficiency selector input: typed FEE/TAX rows ending at snapshot_as_of. Rendered output remains authoritative for recorded/unavailable status.",
            "fifo_lot_count": "ALL-TIME raw SQL: positive-quantity asset transactions; diagnostic SQL count.",
        },
        "credential_check": {
            "statuses": {artifact_aliases.get(alias, alias): status for alias, status in credential_status.items()},
            "normalization_requested": args.normalize_copy_credentials,
            "source_credentials_modified": False,
        },
        "actual_id_map": actual_id_map,
        "http_events": http_events,
        "read_only_verification": {
            "source_snapshot_before": source_snapshot_hash_before,
            "source_snapshot_after": source_snapshot_hash_after,
            "source_unchanged": sqlite_primary_unchanged(
                source_snapshot_hash_before,
                source_snapshot_hash_after,
            ),
            "source_family_unchanged": source_snapshot_hash_before == source_snapshot_hash_after,
            "production_source_before": production_source_hash_before,
            "production_source_after": production_source_hash_after,
            "production_source_unchanged": sqlite_primary_unchanged(
                production_source_hash_before,
                production_source_hash_after,
            ),
            "production_source_family_unchanged": production_source_hash_before == production_source_hash_after,
            "active_production_processes_before": active_production_processes_before,
            "active_production_processes_after": active_production_processes_after,
            "production_source_drift_interpretation": (
                "concurrent external production writer detected"
                if not sqlite_primary_unchanged(
                    production_source_hash_before,
                    production_source_hash_after,
                )
                and (active_production_processes_before or active_production_processes_after)
                else (
                    "no production source drift detected"
                    if sqlite_primary_unchanged(
                        production_source_hash_before,
                        production_source_hash_after,
                    )
                    else "production source changed without a detected port-6040 process"
                )
            ),
            "copy_before_http": copy_hash_before,
            "copy_after_http": copy_hash_after,
            "copy_writes_expected": "optional credential normalization and successful login update the disposable copied DB only",
        },
        "corpus": {
            "expected_row_count": PUBLIC_CATALOG_V1_EXPECTED_CASE_COUNT if public_catalog_v1_run else len(entries),
            "actual_row_count": len(entries),
            "matrix_complete": len(entries) == PUBLIC_CATALOG_V1_EXPECTED_CASE_COUNT if public_catalog_v1_run else True,
            "measured_row_count": sum(1 for entry in entries if entry.get("status") == "ok"),
            "retained_prompt_count": sum(1 for entry in entries if entry.get("retained") is True),
            "rendered_chars_diagnostic_total": sum(int(entry.get("rendered_prompt_chars") or 0) for entry in entries if entry.get("status") == "ok"),
            "rendered_bytes_diagnostic_total": sum(int(entry.get("rendered_prompt_bytes") or 0) for entry in entries if entry.get("status") == "ok"),
        },
        "review_artifacts": {},
        "charts": [],
        "retention": {
            "mode": "selective_named_and_global_representatives" if public_catalog_v1_run else "profile_full_retention",
            "staged_prompt_count": staged_prompt_file_count,
            "planned_retention_count": len(retention_reasons),
            "retained_prompt_count": sum(1 for entry in entries if entry.get("retained") is True),
        },
        "secret_scan": {"status": "pending", "findings": []},
    }
    failures_payload: dict[str, object] = {"run_id": run_id, "failures": failures}
    retained_manifest_path = run_dir / "retained_prompt_manifest.json"
    if public_catalog_v1_run:
        task_reviews_path = run_dir / "task_adequacy_reviews.json"
        export_reviews_path = run_dir / "export_data_reviews.json"
        comparison_manifest_path = run_dir / "comparison_baseline_manifest.json"
        _write_json(task_reviews_path, build_manual_review_placeholder(run_id, "task_adequacy"))
        _write_json(export_reviews_path, build_manual_review_placeholder(run_id, "export_data"))
        _write_json(comparison_manifest_path, build_comparison_baseline_manifest(run_id, args.compare_with, comparisons))
        chart_names = write_probe_svgs(run_dir / "charts", entries, comparisons)
        manifest["review_artifacts"] = {
            "task_adequacy": task_reviews_path.name,
            "export_data": export_reviews_path.name,
            "comparison_baseline": comparison_manifest_path.name,
        }
        manifest["charts"] = [f"charts/{name}" for name in chart_names]

    def write_core_artifacts() -> None:
        _write_json(run_dir / "metrics.json", metrics_payload)
        _write_json(run_dir / "run_manifest.json", manifest)
        _write_json(run_dir / "failures.json", failures_payload)
        (run_dir / "summary.md").write_text(_summary_markdown(metrics_payload, manifest), encoding="utf-8", newline="")

    write_core_artifacts()
    staged_scan_paths = list(run_dir.rglob("*"))
    pre_retention_findings = scan_generated_files(staged_scan_paths, actual_secrets)

    if public_catalog_v1_run:
        retention_reasons = finalize_public_catalog_prompt_retention(
            entries,
            staged_prompt_paths,
            artifact_root=run_dir,
            prompts_dir=prompts_dir,
            allow_retention=not pre_retention_findings,
        )
        shutil.rmtree(prompt_staging_dir, ignore_errors=True)
        retained_manifest = build_retained_prompt_manifest(
            entries,
            run_id=run_id,
            retention_reasons=retention_reasons,
            retention_blocked=bool(pre_retention_findings),
        )
        _write_json(retained_manifest_path, retained_manifest)

    manifest["corpus"]["retained_prompt_count"] = sum(1 for entry in entries if entry.get("retained") is True)
    manifest["retention"]["retained_prompt_count"] = manifest["corpus"]["retained_prompt_count"]
    provisional_secret_scan = {
        "status": "failed" if pre_retention_findings else "passed",
        "findings": pre_retention_findings,
        "staged_prompt_files_scanned": staged_prompt_file_count,
    }
    manifest["secret_scan"] = provisional_secret_scan
    metrics_payload["secret_scan"] = provisional_secret_scan
    failures_payload["secret_scan"] = provisional_secret_scan
    write_core_artifacts()

    post_retention_findings = scan_generated_files(list(run_dir.rglob("*")), actual_secrets)

    def deduplicate_findings(*groups: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
        return [json.loads(serialized) for serialized in sorted({canonical_json(dict(finding)) for group in groups for finding in group})]

    combined_findings = deduplicate_findings(pre_retention_findings, post_retention_findings)
    if public_catalog_v1_run and post_retention_findings:
        for entry in entries:
            prompt_file = entry.get("prompt_file")
            if entry.get("retained") is True and isinstance(prompt_file, str):
                (run_dir / prompt_file).unlink(missing_ok=True)
                entry["retained"] = False
                entry["prompt_file"] = None
        retained_manifest = build_retained_prompt_manifest(
            entries,
            run_id=run_id,
            retention_reasons=retention_reasons,
            retention_blocked=True,
        )
        _write_json(retained_manifest_path, retained_manifest)
        manifest["corpus"]["retained_prompt_count"] = 0
        manifest["retention"]["retained_prompt_count"] = 0

    final_secret_scan = {
        "status": "failed" if combined_findings else "passed",
        "findings": combined_findings,
        "staged_prompt_files_scanned": staged_prompt_file_count,
    }
    manifest["secret_scan"] = final_secret_scan
    metrics_payload["secret_scan"] = final_secret_scan
    failures_payload["secret_scan"] = final_secret_scan
    write_core_artifacts()
    verification_findings = scan_generated_files(list(run_dir.rglob("*")), actual_secrets)
    final_findings = deduplicate_findings(combined_findings, verification_findings)
    if final_findings != combined_findings:
        final_secret_scan = {
            "status": "failed",
            "findings": final_findings,
            "staged_prompt_files_scanned": staged_prompt_file_count,
        }
        manifest["secret_scan"] = final_secret_scan
        metrics_payload["secret_scan"] = final_secret_scan
        failures_payload["secret_scan"] = final_secret_scan
        write_core_artifacts()
    print(f"Run: {run_dir}")
    print(f"Prompts measured: {sum(1 for entry in entries if entry.get('status') == 'ok')}/{len(entries)}; " f"retained: {sum(1 for entry in entries if entry.get('retained') is True)}")
    print(f"Failures: {sum(1 for entry in entries if entry.get('status') == 'failed')}; skipped: {sum(1 for entry in entries if entry.get('status') == 'skipped')}")
    print(
        "Probe source unchanged: "
        f"{sqlite_primary_unchanged(source_snapshot_hash_before, source_snapshot_hash_after)}; "
        "production source unchanged: "
        f"{sqlite_primary_unchanged(production_source_hash_before, production_source_hash_after)}; "
        f"secret scan: {'passed' if not final_findings else 'failed'}"
    )
    regression_failure = args.fail_on_regression and any(item.get("regression") for item in comparisons)
    matrix_failure = public_catalog_v1_run and len(entries) != PUBLIC_CATALOG_V1_EXPECTED_CASE_COUNT
    return 2 if final_findings or not sqlite_primary_unchanged(source_snapshot_hash_before, source_snapshot_hash_after) or regression_failure or matrix_failure else 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run_probe(_parse_args(argv))
    except KeyboardInterrupt:
        print("Probe interrupted", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Probe failed: {sanitize_error(error)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
