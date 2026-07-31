"""Focused tests for AI Export request, catalog, snapshot, and problem contracts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from backend.app.schemas.ai_export import (
    AiExportAllocationEntry,
    AiExportAssetFacts,
    AiExportAssetSnapshotResponse,
    AiExportBrokerSnapshotResponse,
    AiExportCatalogEntry,
    AiExportCatalogResponse,
    AiExportDerivedState,
    AiExportEvent,
    AiExportFxSnapshotResponse,
    AiExportMethodology,
    AiExportNormalizedReturn,
    AiExportPortfolioSnapshotResponse,
    AiExportPosition,
    AiExportProblem,
    AiExportProblemCode,
    AiExportSampledPoint,
    AiExportSelectionMetadata,
    AiExportSnapshotRequest,
    AiExportSnapshotResponse,
    AiExportTargetReference,
    AiExportTask,
    AiExportTechnicalSnapshot,
    AiExportValuationReference,
)
from backend.app.schemas.common import DateRangeModel

START = date(2026, 1, 1)
END = date(2026, 7, 25)


def money(amount: str, code: str = "EUR") -> dict[str, str]:
    return {"code": code, "amount": amount}


def request_payload(domain: str, task: str) -> dict[str, object]:
    return {
        "domain": domain,
        "task": task,
        "detail_level": "standard",
        "date_range": {"start": START, "end": END},
        "target_currency": " eur ",
    }


def snapshot_meta(domain: str, task: str, detail_level: str = "standard") -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_id": f"{domain}.{task}.{detail_level}",
        "profile_version": 1,
        "frontend_response_contract_id": f"{domain}.{task}",
        "frontend_response_contract_version": 1,
        "generated_at": "2026-07-26T10:00:00+02:00",
        "snapshot_as_of": END,
        "selected_range": {"start": START, "end": END},
        "technical_window": {"start": date(2026, 4, 25), "end": END},
        "calculation_range": {"start": date(2025, 7, 1), "end": END},
        "calculation_warmup_start": date(2025, 7, 1),
        "target_currency": "eur",
    }


def export_stats() -> dict[str, object]:
    return {
        "canonical_json": {
            "positions": 1,
            "technical_assets": 1,
            "series_points": 2,
            "events": 1,
            "serialized_characters": 1200,
        },
        "token_estimate": {
            "method": "chars_div_4_v1",
            "estimated_tokens": 300,
        },
    }


def response_payload(domain: str, task: str, facts: dict[str, object]) -> dict[str, object]:
    return {
        "domain": domain,
        "task": task,
        "detail_level": "standard",
        "meta": snapshot_meta(domain, task),
        "methodology": {
            "position_cost_basis_method": "weighted_average_cost",
            "position_cost_basis_is_not_market_price": True,
            "lot_matching_method": "runtime_fifo",
            "cash_decomposition_source": "portfolio_engine",
        },
        "facts": facts,
        "export_stats": export_stats(),
    }


def portfolio_response_payload() -> dict[str, object]:
    facts: dict[str, object] = {
        "summary": {
            "base_currency": "eur",
            "nav": money("125000"),
            "market_value": money("115000"),
            "cash": money("10000"),
            "book_value": money("100000"),
            "period_pnl_amount": money("2500"),
            "twrr_cumulative_pct": "2.50",
        },
        "positions": [
            {
                "asset_id": 11,
                "name": "Global Equity Fund",
                "ticker": "GEF",
                "broker_ids": [3, 1],
                "quantity": "100.5",
                "trading_currency": "usd",
                "valuation_currency": "eur",
                "valuation_source": "market_price",
                "market_value": money("80000"),
                "weight_pct": "64",
            }
        ],
        "contributions": [
            {
                "asset_id": 11,
                "name": "Global Equity Fund",
                "period_pnl_amount": money("2000"),
                "contribution_pct": "1.60",
            }
        ],
        "unallocated_contributions": [
            {
                "broker_id": 1,
                "broker_name": "Primary Broker",
                "unallocated_income_amount": money("25"),
                "unallocated_fees_taxes_amount": money("5"),
            }
        ],
        "other_period_effects": [
            {
                "description": "Residual period reconciliation",
                "category": "Other",
                "period_pnl_amount": money("-2"),
            }
        ],
        "allocations": {
            "by_asset": [{"key": "11", "label": "Global Equity Fund", "weight_pct": "64"}],
            "by_asset_type": [{"key": "etf", "weight_pct": "64"}],
            "by_sector": [{"key": "technology", "weight_pct": "30"}],
            "by_geography": [{"key": "global", "weight_pct": "64"}],
            "by_currency": [{"key": "EUR", "weight_pct": "100"}],
            "by_broker": [{"key": "1", "label": "Primary Broker", "weight_pct": "64"}],
        },
        "cash_context": {
            "total_cash": money("10000"),
            "cash_from_capital": money("7000"),
            "cash_from_generated_returns": money("3000"),
        },
    }
    return response_payload("portfolio", "pac_planning", facts)


def asset_response_payload() -> dict[str, object]:
    facts: dict[str, object] = {
        "identity": {
            "asset_id": 11,
            "name": "Global Equity Fund",
            "ticker": "GEF",
            "asset_type": "ETF",
            "sector": "Diversified",
            "geography": "Global",
            "trading_currency": "usd",
            "valuation_currency": "eur",
        },
        "market": {
            "current_price": money("123.45", "USD"),
            "price_date": END,
            "period_change_pct": "8.72",
            "drawdown_from_period_high_pct": "-4.20",
            "sampled_prices": [
                {"date": START, "close": money("113.56", "USD"), "volume": "1000000"},
                {"date": END, "close": money("123.45", "USD"), "volume": "1200000"},
            ],
        },
        "current_position": {
            "asset_id": 11,
            "name": "Global Equity Fund",
            "broker_ids": [2, 1],
            "quantity": "100.5",
            "valuation_source": "market_price",
            "market_value": money("80000"),
            "weight_pct": "64",
        },
        "lot_summary": {
            "open_lot_count": 3,
            "partial_lot_count": 1,
            "closed_lot_count": 2,
            "average_age_days": "420.5",
            "oldest_lot_date": date(2023, 1, 10),
            "residual_cost_basis": money("65000"),
        },
        "normalized_return": {
            "requested_range": {"start": START, "end": END},
            "base_date": START,
            "base_source": "observed_market_price",
            "base_value": "113.56",
            "source_currency": "usd",
            "window_complete": True,
            "points": [
                {"date": START, "source_value": "113.56", "return_from_base_pct": "0"},
                {"date": END, "source_value": "123.45", "return_from_base_pct": "8.72"},
            ],
        },
    }
    payload = response_payload("asset", "asset_snapshot", facts)
    payload.update(
        {
            "states": [
                {
                    "target": {"kind": "asset", "asset_id": 11},
                    "code": "price_vs_ema200",
                    "state": "above",
                    "as_of": END,
                    "signal_instance_id": "ema200",
                    "signal_code": "EMA",
                    "value": "3.42",
                }
            ],
            "technical": {
                "targets": [
                    {
                        "target": {"kind": "asset", "asset_id": 11},
                        "signals": [
                            {
                                "instance_id": "ema20",
                                "signal_code": "EMA",
                                "implementation_version": "1.0.0",
                                "normalized_params": {"length": 20},
                                "status": "ok",
                                "components": [
                                    {
                                        "component_code": "ema20",
                                        "semantic_id": "ema20",
                                        "unit": "price",
                                        "latest": {"date": END, "value": "121.25"},
                                        "sampled_points": [
                                            {"date": START, "value": "110.10"},
                                            {"date": END, "value": "121.25"},
                                        ],
                                    }
                                ],
                            },
                        ],
                    }
                ]
            },
            "events": [
                {
                    "target": {"kind": "asset", "asset_id": 11},
                    "date": date(2026, 7, 21),
                    "code": "price_crossed_above_ema20",
                    "signal_instance_id": "ema20",
                    "signal_code": "EMA",
                    "direction": "up",
                    "values": {"close": "121.00", "ema20": "120.50"},
                }
            ],
            "coverage": {
                "technical": {
                    "portfolio_assets": 1,
                    "technically_eligible_assets": 1,
                    "technically_analyzed_assets": 1,
                    "analyzed_nav_weight_pct": "100",
                },
                "volume": {
                    "eligible_assets": 1,
                    "analyzed_assets": 1,
                    "analyzed_nav_weight_pct": "100",
                },
                "weighted_breadth": {
                    "eligible_assets": 1,
                    "eligible_nav_weight_pct": "100",
                    "metrics": [
                        {
                            "code": "above_ema200",
                            "asset_count": 1,
                            "eligible_asset_count": 1,
                            "portfolio_nav_weight_pct": "100",
                            "eligible_nav_weight_pct": "100",
                        }
                    ],
                },
            },
            "semantics": {
                "metric_semantics": [
                    {
                        "metric_code": "period_pnl_pct",
                        "unit": "percentage_points",
                        "denominator": "absolute_start_position_value",
                        "annualized": False,
                    }
                ],
                "signal_semantics": [
                    {
                        "semantic_id": "ema20",
                        "description": "Short-term exponential moving average over 20 observations.",
                    }
                ],
                "currency_semantics": {
                    "trading_currency": "usd",
                    "valuation_currency": "eur",
                    "underlying_currency_exposure_available": False,
                },
            },
            "domain_notes": [
                {
                    "subject": "asset",
                    "source": "provider_or_user",
                    "text": "Long-term diversified holding.",
                    "subject_reference": "asset:11",
                }
            ],
        }
    )
    return payload


def fx_response_payload() -> dict[str, object]:
    facts: dict[str, object] = {
        "identity": {
            "base_currency": "eur",
            "quote_currency": "usd",
        },
        "current_rate": {
            "date": END,
            "rate": "1.172345",
            "provider": "ECB",
        },
        "sampled_rates": [
            {"date": START, "rate": "1.100000", "provider": "ECB"},
            {"date": END, "rate": "1.172345", "provider": "ECB"},
        ],
        "extrema": {
            "low_rate": "1.080000",
            "low_date": date(2026, 2, 3),
            "high_rate": "1.190000",
            "high_date": date(2026, 7, 1),
        },
        "volatility": {
            "period_return_pct": "6.58",
            "annualized_volatility_pct": "8.25",
            "max_drawdown_pct": "-3.10",
        },
        "normalized_return": {
            "requested_range": {"start": START, "end": END},
            "base_date": START,
            "base_source": "observed_market_price",
            "base_value": "1.100000",
            "window_complete": True,
            "points": [
                {"date": START, "source_value": "1.100000", "return_from_base_pct": "0"},
                {"date": END, "source_value": "1.172345", "return_from_base_pct": "6.58"},
            ],
        },
        "exposure_links": [
            {
                "kind": "position",
                "linkage": "trading_currency",
                "linked_currency": "usd",
                "exposure_amount": money("80000"),
                "asset_id": 11,
                "broker_id": 1,
            }
        ],
    }
    return response_payload("fx", "fx_trend_review", facts)


def broker_response_payload() -> dict[str, object]:
    facts: dict[str, object] = {
        "summary": {
            "broker_id": 1,
            "name": "Primary Broker",
            "base_currency": "eur",
            "nav": money("90000"),
            "market_value": money("80000"),
            "cash": money("10000"),
            "book_value": money("75000"),
            "net_contributed_capital": money("70000"),
            "start_nav": money("87000"),
            "net_deposits": money("1200"),
            "lifetime_pnl_amount": money("20000"),
            "period_pnl_amount": money("1800"),
            "fees_taxes_amount": money("-120"),
        },
        "positions": [
            {
                "asset_id": 11,
                "name": "Global Equity Fund",
                "broker_ids": [1],
                "quantity": "100.5",
                "valuation_source": "market_price",
                "market_value": money("80000"),
                "weight_pct": "88.89",
            }
        ],
        "contributions": [
            {
                "asset_id": 11,
                "name": "Global Equity Fund",
                "broker_id": 1,
                "period_pnl_amount": money("1800"),
                "fees_taxes_amount": money("100"),
            }
        ],
        "unallocated_contributions": [
            {
                "broker_id": 1,
                "broker_name": "Primary Broker",
                "unallocated_fees_taxes_amount": money("20"),
            }
        ],
        "other_period_effects": [
            {
                "description": "Rounding residual",
                "category": "Other",
                "period_pnl_amount": money("-1"),
                "broker_id": 1,
            }
        ],
        "concentration": {
            "position_count": 1,
            "largest_position_weight_pct": "88.89",
            "top_five_weight_pct": "88.89",
            "herfindahl_index": "0.7901",
            "entries": [
                {
                    "asset_id": 11,
                    "name": "Global Equity Fund",
                    "market_value": money("80000"),
                    "weight_pct": "88.89",
                }
            ],
        },
        "latest_transaction": {
            "transaction_date": date(2026, 7, 20),
            "transaction_type": "BUY",
            "asset_id": 11,
            "quantity": "5",
            "gross_amount": money("600"),
        },
        "fifo_summary": {
            "open_lot_count": 3,
            "partial_lot_count": 1,
            "closed_lot_count": 2,
            "residual_cost_basis": money("65000"),
            "market_value": money("80000"),
            "unrealized_pnl_amount": money("15000"),
        },
    }
    return response_payload("broker", "broker_review", facts)


def ema_signal(length: int, status: str = "ok") -> dict[str, object]:
    instance_id = f"ema{length}"
    return {
        "instance_id": instance_id,
        "signal_code": "EMA",
        "implementation_version": "1.0.0",
        "normalized_params": {"length": length},
        "status": status,
        "components": [
            {
                "component_code": instance_id,
                "semantic_id": instance_id,
                "unit": "price",
                "latest": {"date": END, "value": str(100 + length)},
            }
        ],
    }


def normalized_return_payload() -> dict[str, object]:
    return {
        "requested_range": {"start": START, "end": END},
        "base_date": START,
        "base_source": "observed_market_price",
        "base_value": "100",
        "source_currency": "EUR",
        "window_complete": True,
        "points": [
            {"date": START, "source_value": "100", "return_from_base_pct": "0"},
            {"date": END, "source_value": "110", "return_from_base_pct": "10"},
        ],
    }


def test_global_task_enum_contains_all_19_ids():
    assert len(AiExportTask) == 19


@pytest.mark.parametrize(
    ("domain", "task", "domain_fields"),
    [
        ("portfolio", "pac_planning", {"broker_ids": [3, 1]}),
        ("asset", "asset_snapshot", {"asset_id": 11, "broker_ids": [2, 1]}),
        ("fx", "fx_trend_review", {"base_currency": " eur ", "quote_currency": "usd"}),
        ("broker", "broker_review", {"broker_id": 1}),
    ],
)
def test_valid_request_per_domain(domain: str, task: str, domain_fields: dict[str, object]):
    payload = request_payload(domain, task)
    payload.update(domain_fields)

    request = TypeAdapter(AiExportSnapshotRequest).validate_python(payload)

    assert request.domain.value == domain
    assert request.task.value == task
    assert request.target_currency == "EUR"


def test_request_accepts_explicit_technical_window_ending_at_snapshot():
    payload = request_payload("portfolio", "pac_planning")
    payload["technical_window"] = {
        "start": date(2025, 7, 25),
        "end": END,
    }

    request = TypeAdapter(AiExportSnapshotRequest).validate_python(payload)

    assert request.technical_window == DateRangeModel(start=date(2025, 7, 25), end=END)


def test_request_rejects_technical_window_not_ending_at_snapshot():
    payload = request_payload("portfolio", "pac_planning")
    payload["technical_window"] = {
        "start": date(2025, 7, 1),
        "end": date(2026, 7, 24),
    }

    with pytest.raises(ValidationError, match="technical_window.end must equal snapshot_as_of"):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)


def test_request_and_response_json_schema_expose_domain_discriminator():
    request_schema = TypeAdapter(AiExportSnapshotRequest).json_schema()
    response_schema = TypeAdapter(AiExportSnapshotResponse).json_schema()

    assert request_schema["discriminator"]["propertyName"] == "domain"
    assert response_schema["discriminator"]["propertyName"] == "domain"
    assert set(request_schema["discriminator"]["mapping"]) == {"portfolio", "asset", "fx", "broker"}
    assert set(response_schema["discriminator"]["mapping"]) == {"portfolio", "asset", "fx", "broker"}


def test_cross_domain_task_is_rejected_structurally():
    payload = request_payload("asset", "fx_trend_review")
    payload["asset_id"] = 11

    with pytest.raises(ValidationError):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)


def test_request_rejects_extra_fields_including_user_id():
    payload = request_payload("portfolio", "pac_planning")
    payload["user_id"] = 99

    with pytest.raises(ValidationError, match="extra_forbidden"):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)


def test_currency_codes_are_normalized():
    payload = request_payload("fx", "fx_trend_review")
    payload.update({"base_currency": " eur ", "quote_currency": " UsD "})

    request = TypeAdapter(AiExportSnapshotRequest).validate_python(payload)

    assert request.target_currency == "EUR"
    assert request.base_currency == "EUR"
    assert request.quote_currency == "USD"


@pytest.mark.parametrize(
    "updates",
    [
        {"base_currency": "EUR", "quote_currency": "EUR"},
        {"base_currency": "EUR", "quote_currency": "NOT_A_CURRENCY"},
    ],
)
def test_fx_request_rejects_same_or_invalid_pair(updates: dict[str, str]):
    payload = request_payload("fx", "fx_trend_review")
    payload.update(updates)

    with pytest.raises(ValidationError):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)


def test_broker_ids_are_sorted_deterministically():
    payload = request_payload("portfolio", "pac_planning")
    payload["broker_ids"] = [5, 1, 3]

    request = TypeAdapter(AiExportSnapshotRequest).validate_python(payload)

    assert request.broker_ids == [1, 3, 5]


@pytest.mark.parametrize("broker_ids", [[1, 1], [0, 2], [-1, 2]])
def test_broker_ids_must_be_positive_and_unique(broker_ids: list[int]):
    payload = request_payload("portfolio", "pac_planning")
    payload["broker_ids"] = broker_ids

    with pytest.raises(ValidationError):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)


@pytest.mark.parametrize(
    ("domain", "task", "domain_fields"),
    [
        ("portfolio", "pac_planning", {}),
        ("asset", "asset_snapshot", {"asset_id": 11}),
        ("fx", "fx_trend_review", {"base_currency": "EUR", "quote_currency": "USD"}),
    ],
)
def test_explicit_empty_broker_ids_are_rejected(domain: str, task: str, domain_fields: dict[str, object]):
    payload = request_payload(domain, task)
    payload.update(domain_fields)
    payload["broker_ids"] = []

    with pytest.raises(ValidationError):
        TypeAdapter(AiExportSnapshotRequest).validate_python(payload)


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        (portfolio_response_payload(), AiExportPortfolioSnapshotResponse),
        (asset_response_payload(), AiExportAssetSnapshotResponse),
        (fx_response_payload(), AiExportFxSnapshotResponse),
        (broker_response_payload(), AiExportBrokerSnapshotResponse),
    ],
)
def test_representative_response_per_domain(
    payload: dict[str, object],
    expected_type: type[AiExportPortfolioSnapshotResponse | AiExportAssetSnapshotResponse | AiExportFxSnapshotResponse | AiExportBrokerSnapshotResponse],
):
    response = TypeAdapter(AiExportSnapshotResponse).validate_python(payload)

    assert isinstance(response, expected_type)
    assert response.meta.target_currency == "EUR"


def test_portfolio_non_position_contribution_rows_are_typed_and_strict():
    response = AiExportPortfolioSnapshotResponse.model_validate(portfolio_response_payload())

    assert response.facts.unallocated_contributions[0].unallocated_income_amount.code == "EUR"
    assert response.facts.unallocated_contributions[0].unallocated_fees_taxes_amount.amount == Decimal("5")
    assert response.facts.other_period_effects[0].category == "Other"
    assert response.facts.other_period_effects[0].period_pnl_amount.code == "EUR"
    assert response.facts.other_period_effects[0].period_pnl_amount.amount == Decimal("-2")

    payload = portfolio_response_payload()
    payload["facts"]["other_period_effects"][0]["category"] = "Unknown"
    with pytest.raises(ValidationError):
        AiExportPortfolioSnapshotResponse.model_validate(payload)


def test_broker_summary_and_complete_contribution_rows_are_typed_and_strict():
    response = AiExportBrokerSnapshotResponse.model_validate(broker_response_payload())

    assert response.facts.summary.lifetime_pnl_amount.amount == Decimal("20000")
    assert response.facts.summary.start_nav.amount == Decimal("87000")
    assert response.facts.contributions[0].fees_taxes_amount.amount == Decimal("100")
    assert response.facts.unallocated_contributions[0].unallocated_fees_taxes_amount.amount == Decimal("20")
    assert response.facts.other_period_effects[0].period_pnl_amount.amount == Decimal("-1")

    payload = broker_response_payload()
    payload["facts"]["contributions"][0]["description"] = "not allowed"
    with pytest.raises(ValidationError):
        AiExportBrokerSnapshotResponse.model_validate(payload)


@pytest.mark.parametrize(
    ("payload", "expected_kind"),
    [
        ({"kind": "portfolio"}, "portfolio"),
        ({"kind": "broker", "broker_id": 7}, "broker"),
        ({"kind": "asset", "asset_id": 11}, "asset"),
        (
            {"kind": "fx_pair", "base_currency": " eur ", "quote_currency": " UsD "},
            "fx_pair",
        ),
    ],
)
def test_target_reference_supports_all_target_kinds(payload: dict[str, object], expected_kind: str):
    target = TypeAdapter(AiExportTargetReference).validate_python(payload)

    assert target.kind == expected_kind
    if expected_kind == "fx_pair":
        assert target.base_currency == "EUR"
        assert target.quote_currency == "USD"


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "broker"},
        {"kind": "asset", "asset_id": 0},
        {"kind": "fx_pair", "base_currency": "EUR"},
        {"kind": "fx_pair", "base_currency": "EUR", "quote_currency": "EUR"},
        {"kind": "portfolio", "broker_id": 1},
    ],
)
def test_target_reference_rejects_missing_or_inconsistent_identity(payload: dict[str, object]):
    with pytest.raises(ValidationError):
        TypeAdapter(AiExportTargetReference).validate_python(payload)


def test_technical_snapshot_groups_multiple_targets_and_ema_instances():
    snapshot = AiExportTechnicalSnapshot.model_validate(
        {
            "targets": [
                {
                    "target": {"kind": "asset", "asset_id": 11},
                    "signals": [ema_signal(20), ema_signal(50), ema_signal(200, "partial")],
                },
                {
                    "target": {"kind": "asset", "asset_id": 12},
                    "signals": [ema_signal(20)],
                },
            ]
        }
    )

    assert len(snapshot.targets) == 2
    assert [signal.instance_id for signal in snapshot.targets[0].signals] == [
        "ema20",
        "ema50",
        "ema200",
    ]
    assert {signal.signal_code for signal in snapshot.targets[0].signals} == {"EMA"}
    assert snapshot.targets[0].signals[-1].status.value == "partial"


def test_technical_signal_identity_is_canonical_and_unique_by_instance_id():
    signal = ema_signal(20)
    signal["instance_id"] = " EMA20 "
    signal["signal_code"] = " ema "
    snapshot = AiExportTechnicalSnapshot.model_validate(
        {
            "targets": [
                {
                    "target": {"kind": "asset", "asset_id": 11},
                    "signals": [signal],
                }
            ]
        }
    )

    assert snapshot.targets[0].signals[0].instance_id == "ema20"
    assert snapshot.targets[0].signals[0].signal_code == "EMA"

    with pytest.raises(ValidationError, match="instance_id"):
        AiExportTechnicalSnapshot.model_validate(
            {
                "targets": [
                    {
                        "target": {"kind": "asset", "asset_id": 11},
                        "signals": [ema_signal(20), ema_signal(20)],
                    }
                ]
            }
        )


@pytest.mark.parametrize("status", ["unavailable", "failed"])
def test_exported_technical_signal_status_only_allows_ok_or_partial(status: str):
    signal = ema_signal(20, status=status)

    with pytest.raises(ValidationError):
        AiExportTechnicalSnapshot.model_validate(
            {
                "targets": [
                    {
                        "target": {"kind": "asset", "asset_id": 11},
                        "signals": [signal],
                    }
                ]
            }
        )


@pytest.mark.parametrize(
    "invalid_value",
    [Decimal("20"), date(2026, 1, 1), float("nan"), {"nested": {1, 2}}],
)
def test_technical_normalized_params_must_be_json_safe(invalid_value: object):
    signal = ema_signal(20)
    signal["normalized_params"] = {"length": invalid_value}

    with pytest.raises(ValidationError, match="normalized_params"):
        AiExportTechnicalSnapshot.model_validate(
            {
                "targets": [
                    {
                        "target": {"kind": "asset", "asset_id": 11},
                        "signals": [signal],
                    }
                ]
            }
        )


def test_technical_targets_only_allow_asset_or_fx_pair_references():
    with pytest.raises(ValidationError):
        AiExportTechnicalSnapshot.model_validate(
            {
                "targets": [
                    {
                        "target": {"kind": "portfolio"},
                        "signals": [ema_signal(20)],
                    }
                ]
            }
        )


def test_states_and_events_carry_targets_and_signal_instance_ids():
    state = AiExportDerivedState.model_validate(
        {
            "target": {"kind": "asset", "asset_id": 11},
            "code": "price_vs_ema20",
            "state": "above",
            "as_of": END,
            "signal_instance_id": "ema20",
            "signal_code": "EMA",
            "value": "2.5",
        }
    )
    event = AiExportEvent.model_validate(
        {
            "target": {"kind": "fx_pair", "base_currency": "EUR", "quote_currency": "USD"},
            "date": END,
            "code": "price_crossed_above_ema20",
            "signal_instance_id": "ema20",
            "signal_code": "EMA",
            "direction": "up",
            "values": {"close": "1.17", "ema20": "1.16"},
        }
    )

    assert state.target.kind == "asset"
    assert state.signal_instance_id == "ema20"
    assert event.target.kind == "fx_pair"
    assert event.values == {"close": Decimal("1.17"), "ema20": Decimal("1.16")}

    with pytest.raises(ValidationError):
        AiExportDerivedState.model_validate({"code": "price_vs_ema20", "state": "above", "as_of": END})
    with pytest.raises(ValidationError):
        AiExportEvent.model_validate(
            {
                "target": {"kind": "asset", "asset_id": 11},
                "date": END,
                "code": "price_crossed_above_ema20",
                "values": {},
            }
        )


def test_missing_price_position_preserves_cost_data_without_market_value():
    position = AiExportPosition.model_validate(
        {
            "asset_id": 11,
            "name": "Unpriced Asset",
            "quantity": "5",
            "valuation_source": "missing",
            "average_unit_cost": money("20"),
            "cost_basis": money("100"),
            "realized_pnl_amount": money("4"),
        }
    )

    assert position.market_value is None
    assert position.cost_basis is not None


def test_position_and_allocation_nav_weights_are_signed_and_unbounded():
    short_position = AiExportPosition.model_validate(
        {
            "asset_id": 11,
            "name": "Short Asset",
            "quantity": "-2",
            "valuation_source": "market_price",
            "market_value": money("-200"),
            "weight_pct": "-20",
        }
    )
    leveraged_position = AiExportPosition.model_validate(
        {
            "asset_id": 12,
            "name": "Leveraged Asset",
            "quantity": "5",
            "valuation_source": "market_price",
            "market_value": money("1250"),
            "weight_pct": "125",
        }
    )
    short_allocation = AiExportAllocationEntry(key="short", amount=money("-200"), weight_pct="-20")
    leveraged_allocation = AiExportAllocationEntry(key="leveraged", amount=money("1250"), weight_pct="125")

    assert short_position.weight_pct == Decimal("-20")
    assert leveraged_position.weight_pct == Decimal("125")
    assert short_allocation.weight_pct == Decimal("-20")
    assert leveraged_allocation.weight_pct == Decimal("125")


def test_compact_selection_metadata_is_typed_and_exposes_contract_aliases():
    selection = AiExportSelectionMetadata(
        rule="largest_nav",
        limit=10,
        total_entity_count=12,
        included_entity_count=10,
        total_nav_weight_pct="182.5",
        included_nav_weight_pct="175",
    )

    assert selection.selection_rule == "largest_nav"
    assert selection.rule == "largest_nav"
    assert selection.entity_limit == 10
    assert selection.model_dump()["selection_rule"] == "largest_nav"


@pytest.mark.parametrize(
    "updates",
    [
        {"included_entity_count": 13},
        {"included_nav_weight_pct": "190"},
    ],
)
def test_compact_selection_metadata_rejects_inconsistent_coverage(updates: dict[str, object]):
    payload: dict[str, object] = {
        "rule": "largest_nav",
        "limit": 10,
        "total_entity_count": 12,
        "included_entity_count": 10,
        "total_nav_weight_pct": "182.5",
        "included_nav_weight_pct": "175",
    }
    payload.update(updates)

    with pytest.raises(ValidationError):
        AiExportSelectionMetadata.model_validate(payload)


def test_mixed_valuation_source_preserves_only_complete_aggregate_fields():
    position = AiExportPosition.model_validate(
        {
            "asset_id": 11,
            "name": "Multi-broker Asset",
            "broker_ids": [2, 7],
            "quantity": "5",
            "valuation_source": "mixed",
            "average_unit_cost": money("20"),
            "cost_basis": money("100"),
        }
    )

    assert position.valuation_source == "mixed"
    assert position.market_value is None
    assert position.broker_ids == [2, 7]


@pytest.mark.parametrize(
    "updates",
    [
        {"valuation_source": "missing", "market_value": money("100")},
        {"valuation_source": "missing", "weight_pct": "10"},
        {"valuation_source": "market_price"},
    ],
)
def test_position_rejects_inconsistent_valuation_metadata(updates: dict[str, object]):
    payload: dict[str, object] = {
        "asset_id": 11,
        "name": "Asset",
        "quantity": "5",
    }
    payload.update(updates)

    with pytest.raises(ValidationError, match="valuation"):
        AiExportPosition.model_validate(payload)


@pytest.mark.parametrize("source", ["last_observed_trade_price"])
def test_reference_valuation_source_survives_missing_target_fx(source: str):
    position = AiExportPosition.model_validate(
        {
            "asset_id": 11,
            "name": "FX-unconverted reference",
            "quantity": "5",
            "valuation_source": source,
        }
    )

    assert position.valuation_source == source
    assert position.market_value is None


def test_valuation_reference_source_controls_semantics():
    reference = AiExportValuationReference.model_validate(
        {
            "date": date(2026, 7, 10),
            "source": "last_observed_trade_price",
            "unit_price": money("25.40", "USD"),
        }
    )

    assert reference.semantics == "valuation_fallback_not_observed_market_return"

    with pytest.raises(ValidationError):
        AiExportValuationReference.model_validate(
            {
                "date": date(2026, 7, 10),
                "source": "last_observed_trade_price",
                "unit_price": money("25.40", "USD"),
                "semantics": "estimated_at_cost_not_observed_market_return",
            }
        )


def test_valuation_reference_positive_price_and_split_adjustment_contract():
    with pytest.raises(ValidationError, match="strictly positive"):
        AiExportValuationReference.model_validate(
            {
                "date": date(2026, 7, 10),
                "source": "last_observed_trade_price",
                "unit_price": money("0", "EUR"),
            }
        )

    with pytest.raises(ValidationError, match="effective_unit_price"):
        AiExportValuationReference.model_validate(
            {
                "date": date(2026, 7, 10),
                "source": "last_observed_trade_price",
                "unit_price": money("100", "EUR"),
                "split_adjusted": True,
            }
        )

    adjusted = AiExportValuationReference.model_validate(
        {
            "date": date(2026, 7, 10),
            "source": "last_observed_trade_price",
            "unit_price": money("100", "USD"),
            "effective_unit_price": money("50", "EUR"),
            "split_adjusted": True,
        }
    )
    assert adjusted.unit_price.amount == Decimal("100")
    assert adjusted.effective_unit_price is not None
    assert adjusted.effective_unit_price.amount == Decimal("50")
    assert adjusted.split_adjusted is True


def test_normalized_return_accepts_exact_and_first_on_or_after_bases():
    exact = AiExportNormalizedReturn.model_validate(normalized_return_payload())
    first_payload = normalized_return_payload()
    first_payload.update(
        {
            "base_date": date(2026, 1, 2),
            "base_source": "first_observed_market_price_in_window",
            "window_complete": False,
            "points": [
                {
                    "date": date(2026, 1, 2),
                    "source_value": "100",
                    "return_from_base_pct": "0",
                },
                {"date": END, "source_value": "110", "return_from_base_pct": "10"},
            ],
        }
    )
    first = AiExportNormalizedReturn.model_validate(first_payload)

    assert exact.base_date == START
    assert first.base_date > START


@pytest.mark.parametrize(
    "case",
    [
        "zero_base_value",
        "negative_base_value",
        "base_before_range",
        "base_after_range",
        "first_date_not_base",
        "first_value_not_base",
        "first_return_not_zero",
        "point_outside_range",
        "points_not_increasing",
        "exact_source_not_requested_start",
        "first_on_or_after_source_at_requested_start",
    ],
)
def test_normalized_return_rejects_invalid_contracts(case: str):
    payload = normalized_return_payload()

    if case == "zero_base_value":
        payload["base_value"] = "0"
        payload["points"][0]["source_value"] = "0"
    elif case == "negative_base_value":
        payload["base_value"] = "-1"
        payload["points"][0]["source_value"] = "-1"
    elif case == "base_before_range":
        payload["base_date"] = date(2025, 12, 31)
        payload["points"][0]["date"] = date(2025, 12, 31)
    elif case == "base_after_range":
        payload["base_date"] = date(2026, 7, 26)
        payload["points"][0]["date"] = date(2026, 7, 26)
    elif case == "first_date_not_base":
        payload["points"][0]["date"] = date(2026, 1, 2)
    elif case == "first_value_not_base":
        payload["points"][0]["source_value"] = "99"
    elif case == "first_return_not_zero":
        payload["points"][0]["return_from_base_pct"] = "0.01"
    elif case == "point_outside_range":
        payload["points"][1]["date"] = date(2026, 7, 26)
    elif case == "points_not_increasing":
        payload["points"][1]["date"] = START
    elif case == "exact_source_not_requested_start":
        payload["base_date"] = date(2026, 1, 2)
        payload["points"][0]["date"] = date(2026, 1, 2)
    elif case == "first_on_or_after_source_at_requested_start":
        payload["base_source"] = "first_observed_market_price_in_window"

    with pytest.raises(ValidationError):
        AiExportNormalizedReturn.model_validate(payload)


@pytest.mark.parametrize("source", ["last_observed_trade_price"])
def test_asset_facts_never_mix_fallback_reference_with_normalized_return(source: str):
    payload = asset_response_payload()["facts"]
    assert isinstance(payload, dict)
    payload["valuation_reference"] = {
        "date": date(2026, 7, 10),
        "source": source,
        "unit_price": money("25.40", "USD"),
    }

    with pytest.raises(ValidationError, match="cannot contain both"):
        AiExportAssetFacts.model_validate(payload)

    payload["normalized_return"] = None
    payload["market"] = None
    current_position = payload["current_position"]
    assert isinstance(current_position, dict)
    current_position["valuation_source"] = source
    facts = AiExportAssetFacts.model_validate(payload)
    assert facts.normalized_return is None
    assert facts.valuation_reference is not None


@pytest.mark.parametrize("source", ["last_observed_trade_price"])
def test_asset_facts_reject_market_facts_with_fallback_reference(source: str):
    payload = asset_response_payload()["facts"]
    assert isinstance(payload, dict)
    payload["normalized_return"] = None
    payload["valuation_reference"] = {
        "date": date(2026, 7, 10),
        "source": source,
        "unit_price": money("25.40", "USD"),
    }
    current_position = payload["current_position"]
    assert isinstance(current_position, dict)
    current_position["valuation_source"] = source

    with pytest.raises(ValidationError, match="cannot contain market facts"):
        AiExportAssetFacts.model_validate(payload)


@pytest.mark.parametrize(
    ("reference_source", "position_source"),
    [
        ("last_observed_trade_price", "market_price"),
        ("last_observed_trade_price", "missing"),
        ("last_observed_trade_price", "mixed"),
    ],
)
def test_asset_facts_reject_position_source_contradictions(reference_source: str, position_source: str):
    payload = asset_response_payload()["facts"]
    assert isinstance(payload, dict)
    payload["market"] = None
    payload["normalized_return"] = None
    payload["valuation_reference"] = {
        "date": date(2026, 7, 10),
        "source": reference_source,
        "unit_price": money("25.40", "USD"),
    }
    current_position = payload["current_position"]
    assert isinstance(current_position, dict)
    current_position["valuation_source"] = position_source
    if position_source == "missing":
        current_position.pop("market_value", None)
        current_position.pop("weight_pct", None)

    with pytest.raises(ValidationError, match="must match"):
        AiExportAssetFacts.model_validate(payload)


def test_methodology_distinguishes_wac_from_runtime_fifo():
    response = TypeAdapter(AiExportSnapshotResponse).validate_python(portfolio_response_payload())

    assert response.methodology.position_cost_basis_method == "weighted_average_cost"
    assert response.methodology.position_cost_basis_is_not_market_price is True
    assert response.methodology.lot_matching_method == "runtime_fifo"

    domain_neutral = AiExportMethodology()
    assert domain_neutral.position_cost_basis_method is None
    assert domain_neutral.position_cost_basis_is_not_market_price is None
    assert domain_neutral.lot_matching_method is None


def test_empty_technical_snapshot_must_be_omitted_instead():
    with pytest.raises(ValidationError, match="at least 1"):
        AiExportTechnicalSnapshot(targets=[])


def test_asset_and_transaction_types_accept_uppercase_values():
    asset_response = TypeAdapter(AiExportSnapshotResponse).validate_python(asset_response_payload())
    broker_response = TypeAdapter(AiExportSnapshotResponse).validate_python(broker_response_payload())

    assert asset_response.facts.identity.asset_type == "ETF"
    assert broker_response.facts.latest_transaction is not None
    assert broker_response.facts.latest_transaction.transaction_type == "BUY"


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_non_finite_numeric_values_are_rejected(value: Decimal):
    with pytest.raises(ValidationError, match="finite"):
        AiExportSampledPoint(date=END, value=value)


def test_catalog_entry_and_ordered_response_validate():
    compact = AiExportCatalogEntry(
        domain="portfolio",
        task="pac_planning",
        detail_level="compact",
        profile_id="portfolio.pac_planning.compact",
        profile_version=1,
        frontend_response_contract_id="portfolio.pac_planning",
        frontend_response_contract_version=1,
        applicability_code="portfolio_accessible",
        supports_user_notes=True,
        supports_web_research=True,
    )
    standard = AiExportCatalogEntry(
        domain="portfolio",
        task="pac_planning",
        detail_level="standard",
        profile_id="portfolio.pac_planning.standard",
        profile_version=1,
        frontend_response_contract_id="portfolio.pac_planning",
        frontend_response_contract_version=1,
        applicability_code="portfolio_accessible",
        supports_user_notes=True,
        supports_web_research=True,
    )

    catalog = AiExportCatalogResponse(schema_version=1, entries=[compact, standard])

    assert [entry.detail_level.value for entry in catalog.entries] == ["compact", "standard"]


def test_catalog_rejects_cross_domain_task_and_prompt_fields():
    with pytest.raises(ValidationError, match="task does not belong"):
        AiExportCatalogEntry(
            domain="asset",
            task="pac_planning",
            detail_level="compact",
            profile_id="asset.pac_planning.compact",
            profile_version=1,
            frontend_response_contract_id="asset.pac_planning",
            frontend_response_contract_version=1,
            applicability_code="asset_exists",
            supports_user_notes=True,
            supports_web_research=False,
        )

    with pytest.raises(ValidationError, match="extra_forbidden"):
        AiExportCatalogEntry.model_validate(
            {
                "domain": "portfolio",
                "task": "pac_planning",
                "detail_level": "compact",
                "profile_id": "portfolio.pac_planning.compact",
                "profile_version": 1,
                "frontend_response_contract_id": "portfolio.pac_planning",
                "frontend_response_contract_version": 1,
                "applicability_code": "portfolio_accessible",
                "supports_user_notes": True,
                "supports_web_research": True,
                "prompt": "Do something",
            }
        )


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        (
            {
                "code": "unsupported_profile",
                "message": "Requested profile is not supported.",
                "domain": "portfolio",
                "task": "pac_planning",
                "detail_level": "full",
                "supported_profiles": [
                    "portfolio.pac_planning.compact",
                    "portfolio.pac_planning.standard",
                ],
            },
            AiExportProblemCode.UNSUPPORTED_PROFILE,
        ),
        (
            {
                "code": "profile_contract_mismatch",
                "message": "Frontend contract version is stale.",
                "profile_id": "asset.asset_snapshot.standard",
                "expected_frontend_response_contract_id": "asset.asset_snapshot",
                "expected_frontend_response_contract_version": 2,
                "actual_frontend_response_contract_id": "asset.asset_snapshot",
                "actual_frontend_response_contract_version": 1,
            },
            AiExportProblemCode.PROFILE_CONTRACT_MISMATCH,
        ),
        (
            {
                "code": "task_not_applicable",
                "message": "No linked FX exposure exists.",
                "domain": "fx",
                "task": "fx_exposure_impact",
                "detail_level": "standard",
                "profile_id": "fx.fx_exposure_impact.standard",
                "applicability_code": "linked_fx_exposure_required",
            },
            AiExportProblemCode.TASK_NOT_APPLICABLE,
        ),
        (
            {
                "code": "broker_access_denied",
                "message": "One or more brokers are inaccessible.",
                "denied_broker_ids": [5, 2],
            },
            AiExportProblemCode.BROKER_ACCESS_DENIED,
        ),
        (
            {
                "code": "entity_not_found",
                "message": "Requested asset does not exist.",
                "entity_reference": {"kind": "asset", "asset_id": 999},
            },
            AiExportProblemCode.ENTITY_NOT_FOUND,
        ),
        (
            {
                "code": "snapshot_source_failure",
                "message": "Portfolio engine failed.",
                "source_code": "portfolio_engine",
                "retryable": True,
            },
            AiExportProblemCode.SNAPSHOT_SOURCE_FAILURE,
        ),
    ],
)
def test_problem_union_validates_each_typed_variant(payload: dict[str, object], expected_code: AiExportProblemCode):
    problem = TypeAdapter(AiExportProblem).validate_python(payload)

    assert problem.code == expected_code
    if expected_code == AiExportProblemCode.BROKER_ACCESS_DENIED:
        assert problem.denied_broker_ids == [2, 5]


@pytest.mark.parametrize(
    ("payload", "required_field"),
    [
        (
            {
                "code": "unsupported_profile",
                "message": "Unsupported.",
                "domain": "portfolio",
                "task": "pac_planning",
                "detail_level": "full",
                "supported_profiles": ["portfolio.pac_planning.standard"],
            },
            "supported_profiles",
        ),
        (
            {
                "code": "profile_contract_mismatch",
                "message": "Mismatch.",
                "profile_id": "asset.asset_snapshot.standard",
                "expected_frontend_response_contract_id": "asset.asset_snapshot",
                "expected_frontend_response_contract_version": 2,
                "actual_frontend_response_contract_id": "asset.asset_snapshot",
                "actual_frontend_response_contract_version": 1,
            },
            "actual_frontend_response_contract_version",
        ),
        (
            {
                "code": "task_not_applicable",
                "message": "Not applicable.",
                "domain": "fx",
                "task": "fx_exposure_impact",
                "detail_level": "standard",
                "profile_id": "fx.fx_exposure_impact.standard",
                "applicability_code": "linked_fx_exposure_required",
            },
            "applicability_code",
        ),
        (
            {
                "code": "broker_access_denied",
                "message": "Denied.",
                "denied_broker_ids": [2],
            },
            "denied_broker_ids",
        ),
        (
            {
                "code": "entity_not_found",
                "message": "Missing.",
                "entity_reference": {"kind": "asset", "asset_id": 999},
            },
            "entity_reference",
        ),
        (
            {
                "code": "snapshot_source_failure",
                "message": "Failure.",
                "source_code": "portfolio_engine",
                "retryable": False,
            },
            "source_code",
        ),
    ],
)
def test_problem_variants_require_machine_readable_fields(payload: dict[str, object], required_field: str):
    payload.pop(required_field)

    with pytest.raises(ValidationError):
        TypeAdapter(AiExportProblem).validate_python(payload)


def test_problem_union_exposes_code_discriminator_and_rejects_unknown_code():
    schema = TypeAdapter(AiExportProblem).json_schema()

    assert schema["discriminator"]["propertyName"] == "code"
    assert set(schema["discriminator"]["mapping"]) == {code.value for code in AiExportProblemCode}

    with pytest.raises(ValidationError):
        TypeAdapter(AiExportProblem).validate_python({"code": "unknown_problem", "message": "Invalid"})


def test_json_serialization_uses_fixed_point_safe_decimals():
    payload = asset_response_payload()
    facts = payload["facts"]
    assert isinstance(facts, dict)
    market = facts["market"]
    assert isinstance(market, dict)
    market["current_price"] = money("1.29E+5", "USD")
    normalized_return = facts["normalized_return"]
    assert isinstance(normalized_return, dict)
    normalized_return["base_value"] = "1E-7"
    points = normalized_return["points"]
    assert isinstance(points, list)
    first_point = points[0]
    assert isinstance(first_point, dict)
    first_point["source_value"] = "1E-7"

    response = TypeAdapter(AiExportSnapshotResponse).validate_python(payload)
    serialized = response.model_dump_json()

    assert '"amount":"129000"' in serialized
    assert '"base_value":"0.0000001"' in serialized
    assert "1.29E+5" not in serialized
    assert '"1E-7"' not in serialized
