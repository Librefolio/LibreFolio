"""
EUR-only byte-identity guard for the native cash ledger (lot 41, step F).

Step F gives the portfolio engine and service a native-currency cash ledger. For a portfolio
whose cash is all in the report currency nothing may change: not a number, not an exponent,
not an order. This test freezes what today's code returns for such a portfolio in a golden
file, and every later run must return the same bytes.

Scenario (dated 2091: no other test writes those days). User U sees three brokers: A, owned
at 100%; B, owned at 50%; C, only viewed (owned by user O; a viewer is scaled at 1). EQ is a
EUR stock with a provider and prices, MAN a EUR asset with neither (cost-valued), IDX an IDR
ETF bought with EUR. IDX is the trap: EUR/IDR moves on 01-04, 01-18 and 01-22, days without
a transaction or a price, and a currency held only through an asset, never as cash, must not
give step F rate-change days to revalue. Cash amounts carry assorted exponents ("10000.00",
"2000.0", "3000", "0.000"), so a change in how cash is summed or converted shows up as a
changed string. A deposit dated after both windows must not leak into them.

Dumped for W1 = (no start, 2091-01-25) and W2 = (2091-01-08, 2091-01-14): the full report
(every include_* flag on), get_summary with the broker breakdown, the eight series getters
and the engine's calculate() (an allow-list of its result fields).

Self-check: the scenario is built twice, for two users with their own brokers and assets.
Ids, names, tickers and emails become stable labels (U, O, A, B, C, EQ, MAN, IDX,
tx:<label>), and the two labelled dumps must match each other before either is compared
with the golden: an id or a name that escaped the labels, or a list ordered by absolute ids,
makes them differ.

Decimals: models are dumped in python mode and every Decimal is written with str(), which
keeps its exponent. mode="json" would not: SafeDecimal serializes with format(v, "f"), which
writes Decimal("1E+2") as "100" and hides an exponent drift.

Regenerate the golden only for a reviewed, intended change of these outputs:

    LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD=1 ./dev.py test services roi-fifo-utils native_cash_guard

The switch is a ``LIBREFOLIO_TEST_*`` name because a test lane drops every other ``LIBREFOLIO_*``
variable of the shell before pytest starts (``configure_test_runtime``, ``scripts/cli_base.py``).
"""

import dataclasses
import difflib
import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, ProviderInputType, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import DailyStates, PortfolioCalculationResult
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_services._range_bounds import lift_range_bound

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "native_cash_guard" / "eur_only_golden.json"
_REGEN_ENV = "LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD"
_REGEN_COMMAND = f"{_REGEN_ENV}=1 ./dev.py test services roi-fifo-utils native_cash_guard"
_DIFF_LINES = 120


def _day(day: int) -> date:
    return date(2091, 1, day)


# =============================================================================
# SCENARIO
# =============================================================================

# (broker, user, role, share_percentage)
_ACCESSES = (
    ("A", "U", UserRole.OWNER, "1.000000"),
    ("B", "U", UserRole.OWNER, "0.500000"),
    ("C", "U", UserRole.VIEWER, "0"),
    ("C", "O", UserRole.OWNER, "1.000000"),
)
# (label, currency, asset_type, priced by a provider): MAN has no provider and no price.
_ASSETS = (
    ("EQ", "EUR", AssetType.STOCK, True),
    ("MAN", "EUR", AssetType.HOLD, False),
    ("IDX", "IDR", AssetType.ETF, True),
)
# (asset, day, price, currency): open = high = low = close
_PRICES = (
    ("EQ", 3, "125.4321", "EUR"),
    ("EQ", 20, "131.07", "EUR"),
    ("IDX", 3, "160500", "IDR"),
    ("IDX", 20, "171250.5", "IDR"),
)
# 1 EUR = rate IDR (base EUR < quote IDR, as FxRate's check constraint requires).
# 01-04, 01-18 and 01-22 carry no transaction and no price.
_EUR_IDR_RATES = ((1, "17250.5"), (4, "17310.25"), (18, "17190.75"), (22, "17275"))
# (label, broker, asset, type, day, quantity, amount, currency): all cash is EUR; the
# TRANSFER legs move EQ without cash (amount 0, no currency).
_TRANSACTIONS = (
    ("dep_A", "A", None, TransactionType.DEPOSIT, 1, "0", "10000.00", "EUR"),
    ("dep_B", "B", None, TransactionType.DEPOSIT, 1, "0", "2000.0", "EUR"),
    ("dep_C", "C", None, TransactionType.DEPOSIT, 1, "0", "3000", "EUR"),
    ("buy_A_EQ", "A", "EQ", TransactionType.BUY, 2, "10", "-1234.56", "EUR"),
    ("buy_A_IDX", "A", "IDX", TransactionType.BUY, 2, "100", "-987.654", "EUR"),
    ("buy_B_MAN", "B", "MAN", TransactionType.BUY, 2, "5", "-500.5", "EUR"),
    ("div_A_EQ", "A", "EQ", TransactionType.DIVIDEND, 5, "0", "12.34", "EUR"),
    ("int_B", "B", None, TransactionType.INTEREST, 5, "0", "1.5", "EUR"),
    ("fee_A_EQ", "A", "EQ", TransactionType.FEE, 5, "0", "-2.50", "EUR"),
    ("tax_C", "C", None, TransactionType.TAX, 5, "0", "-0.75", "EUR"),
    ("div_corr_A_EQ", "A", "EQ", TransactionType.DIVIDEND, 5, "0", "-1.00", "EUR"),
    ("int_zero_A", "A", None, TransactionType.INTEREST, 6, "0", "0.000", "EUR"),
    ("sell_A_EQ", "A", "EQ", TransactionType.SELL, 7, "-4", "520.80", "EUR"),
    ("wdr_A", "A", None, TransactionType.WITHDRAWAL, 9, "0", "-300.00", "EUR"),
    ("ct_out_A", "A", None, TransactionType.CASH_TRANSFER, 10, "0", "-400.00", "EUR"),
    ("ct_in_B", "B", None, TransactionType.CASH_TRANSFER, 12, "0", "400.00", "EUR"),
    ("tr_out_A_EQ", "A", "EQ", TransactionType.TRANSFER, 13, "-2", "0", None),
    ("tr_in_B_EQ", "B", "EQ", TransactionType.TRANSFER, 16, "2", "0", None),
    ("dep_late_A", "A", None, TransactionType.DEPOSIT, 31, "0", "5000.00", "EUR"),
)
# Linked both ways: A -> B cash in transit 01-10..01-12, EQ in transit 01-13..01-16.
_LINKED_PAIRS = (("ct_out_A", "ct_in_B"), ("tr_out_A_EQ", "tr_in_B_EQ"))
# (window, date_from, date_to)
_WINDOWS = (("W1", None, _day(25)), ("W2", _day(8), _day(14)))
# The series getters, all called as (user_id, broker_ids=None, date_from, date_to, target_currency_override="EUR").
_SERIES_GETTERS = ("get_history", "get_broker_pnl_history", "get_pnl_candles", "get_income_history", "get_cost_history", "get_deposit_history", "get_acquisition_funding_history", "get_positions_contribution")
# Allow-list of PortfolioCalculationResult. Left out: per_realized, per_income, per_fees_taxes,
# unalloc_income, unalloc_fees (removed by step F) and native_cash (added by it).
_ENGINE_RESULT_FIELDS = ("daily_states", "position_states_start", "position_states_end", "scope_broker_ids", "target_currency", "date_from", "date_to", "average_costs", "realized_sales", "missing_fx")
# EngineEndState restricted to the fields it has today, so a field step F adds is not compared.
_ENGINE_END_STATE_FIELDS = ("cumulative_cash", "cumulative_ecf", "cumulative_qty", "wac_pool_qty", "wac_pool_cost", "capital_pool", "returns_pool", "withdrawn_pool", "cumulative_cash_by_broker", "cumulative_ecf_by_broker")


@dataclasses.dataclass(frozen=True)
class _Labels:
    """Stable labels for one copy of the scenario."""

    ids: dict[str, dict[int, str]]  # "user" / "broker" / "asset" / "tx" -> id -> label
    texts: tuple[tuple[str, str], ...]  # (name, label), longest name first

    def of(self, kind: str, raw_id: int) -> str | int:
        """The label of ``raw_id``. An id the scenario does not know stays as it is: it differs
        between the two copies, so the self-check reports it."""
        return self.ids[kind].get(raw_id, raw_id)

    def position(self, key: Any) -> str:
        """``"EQ@A"`` for the (asset_id, broker_id) key of a position."""
        if not (isinstance(key, tuple) and len(key) == 2):
            raise TypeError(f"expected an (asset_id, broker_id) key, got {key!r}")
        asset_id, broker_id = key
        return f"{self.of('asset', asset_id)}@{self.of('broker', broker_id)}"


@dataclasses.dataclass(frozen=True)
class _Copy:
    """One copy of the scenario: the id of its viewer U and the labels of its ids and names."""

    user_id: int
    labels: _Labels


async def _persist(session: AsyncSession, keep_alive: list[object], *rows: object) -> None:
    """Add and flush ``rows`` (never commit), keeping a strong reference to each one.

    The identity map holds flushed objects weakly: once nothing references one, a later query
    reloads it from the database, where a Numeric column comes back at its column scale
    (Decimal("10000.000000") for the Decimal("10000.00") written). Kept alive, every query of
    the test returns the rows exactly as built, in both copies, whatever the collector does."""
    session.add_all(rows)
    await session.flush()
    keep_alive.extend(rows)


def _access_rows(users: dict[str, User], brokers: dict[str, Broker]) -> list[BrokerUserAccess]:
    return [BrokerUserAccess(broker_id=brokers[broker].id, user_id=users[user].id, role=role, share_percentage=Decimal(share)) for broker, user, role, share in _ACCESSES]


def _market_rows(assets: dict[str, Asset]) -> list[object]:
    """A yfinance assignment for each priced asset (MAN stays manual) and the prices."""
    rows: list[object] = [AssetProviderAssignment(asset_id=assets[label].id, provider_code="yfinance", identifier=assets[label].identifier_ticker, identifier_type=ProviderInputType.TICKER) for label, _currency, _asset_type, priced in _ASSETS if priced]
    rows += [PriceHistory(asset_id=assets[label].id, date=_day(day), open=Decimal(price), high=Decimal(price), low=Decimal(price), close=Decimal(price), volume=None, currency=currency, source_plugin_key="manual_test") for label, day, price, currency in _PRICES]
    return rows


async def _add_transactions(session: AsyncSession, keep_alive: list[object], brokers: dict[str, Broker], assets: dict[str, Asset]) -> dict[str, Transaction]:
    """Every row of ``_TRANSACTIONS``, in order; then each linked pair points at each other
    (both legs flushed first: the foreign key of ``related_transaction_id`` is deferred)."""
    transactions = {label: Transaction(broker_id=brokers[broker].id, asset_id=assets[asset].id if asset else None, type=tx_type, date=_day(day), quantity=Decimal(quantity), amount=Decimal(amount), currency=currency) for label, broker, asset, tx_type, day, quantity, amount, currency in _TRANSACTIONS}
    await _persist(session, keep_alive, *transactions.values())
    for sent, received in _LINKED_PAIRS:
        transactions[sent].related_transaction_id = transactions[received].id
        transactions[received].related_transaction_id = transactions[sent].id
    await session.flush()
    return transactions


def _labels(users: dict[str, User], brokers: dict[str, Broker], assets: dict[str, Asset], transactions: dict[str, Transaction]) -> _Labels:
    ids = {
        "user": {row.id: label for label, row in users.items()},
        "broker": {row.id: label for label, row in brokers.items()},
        "asset": {row.id: label for label, row in assets.items()},
        "tx": {row.id: f"tx:{label}" for label, row in transactions.items()},
    }
    texts = [(row.email, f"{label}-email") for label, row in users.items()]
    texts += [(row.username, label) for label, row in users.items()]
    texts += [(row.name, label) for label, row in brokers.items()]
    texts += [(row.display_name, label) for label, row in assets.items()]
    texts += [(row.identifier_ticker, f"{label}-ticker") for label, row in assets.items()]
    # Longest first: an email contains its username.
    return _Labels(ids=ids, texts=tuple(sorted(texts, key=lambda pair: len(pair[0]), reverse=True)))


async def _build_copy(session: AsyncSession, keep_alive: list[object]) -> _Copy:
    """Write one copy of the scenario, its names made unique by one uuid suffix."""
    suffix = uuid4().hex
    users = {label: User(username=f"ncg_{label}_{suffix}", email=f"ncg_{label}_{suffix}@test.com", hashed_password="fakehash", is_active=True) for label in ("U", "O")}
    brokers = {label: Broker(name=f"NCG-{label}-{suffix}") for label in ("A", "B", "C")}
    assets = {label: Asset(display_name=f"NCG {label} {suffix}", currency=currency, asset_type=asset_type, identifier_ticker=f"NCG{label}{suffix[:8].upper()}") for label, currency, asset_type, _priced in _ASSETS}
    await _persist(session, keep_alive, *users.values(), *brokers.values(), *assets.values())
    await _persist(session, keep_alive, *_access_rows(users, brokers), *_market_rows(assets))
    transactions = await _add_transactions(session, keep_alive, brokers, assets)
    return _Copy(user_id=users["U"].id, labels=_labels(users, brokers, assets, transactions))


# =============================================================================
# LABELLED DUMP
# =============================================================================

# Fields whose int values are scenario ids, in the Pydantic models and in the engine dataclasses.
_ID_FIELDS: dict[str, str] = {
    **dict.fromkeys(("broker_id", "broker_ids", "scope_broker_ids", "source_broker_id", "destination_broker_id", "opening_broker_id"), "broker"),
    **dict.fromkeys(("asset_id", "affected_asset_ids", "carried_forward_price_asset_ids", "missing_price_asset_ids", "stale_price_asset_ids", "transaction_implied_asset_ids"), "asset"),
    **dict.fromkeys(("transaction_id", "movement_id", "unknown_cost_movement_ids", "oversold_movement_ids", "related_transaction_id", "source_transaction_ids", "opening_transaction_id", "operation_transaction_id"), "tx"),
    "user_id": "user",
    # MF5-1b: AllocationItem.id, the asset of a slice of the asset dimension (None on the other dimensions' slices and
    # on Liquidity). No other dumped field is named "id".
    "id": "asset",
}
# Fields holding an id as a digit string: a data-quality issue about an asset points at str(asset_id).
_DIGIT_ID_FIELDS: dict[str, str] = {"cta_target": "asset"}
# Dicts keyed by broker id, dicts keyed by asset id (V-11: the day of the last market quote of
# each transaction-implied asset; MF5-1b: by_asset, the day's market value of each asset), and dicts keyed by the
# (asset_id, broker_id) of a position.
_BROKER_KEYED_FIELDS = frozenset({"broker_contributions", "capital_pool", "returns_pool", "cumulative_cash_by_broker", "cumulative_ecf_by_broker"})
_ASSET_KEYED_FIELDS = frozenset({"transaction_implied_last_quote_dates", "by_asset"})
_POSITION_KEYED_FIELDS = frozenset({"cumulative_qty", "wac_pool_qty", "wac_pool_cost", "average_costs"})
# AverageCost.key is the (asset_id, broker_id) tuple of its position.
_POSITION_TUPLE_FIELDS = frozenset({"key"})
# Ids written into text (applied after the names, so a name never reaches them).
_ID_PATTERNS = (
    # ScopeAwareTransactionClassifier warnings (financial_math/portfolio/classifier.py): a linked pair with mismatched shares ...
    (re.compile(r"Linked internal pair \((\d+), (\d+)\)"), ("tx", "tx")),
    (re.compile(r"broker (\d+)="), ("broker",)),
    # ... and a pair whose other leg is missing
    (re.compile(r"Transaction (\d+)"), ("tx",)),
    (re.compile(r"related_transaction_id=(\d+)"), ("tx",)),
    # the service's fallback names when a broker or an asset row is not found
    (re.compile(r"Broker (\d+)"), ("broker",)),
    (re.compile(r"Asset (\d+)"), ("asset",)),
)


def _relabel_match(match: re.Match[str], *, kinds: tuple[str, ...], labels: _Labels) -> str:
    """The matched text with each captured id replaced by its label."""
    whole, offset = match.group(0), match.start(0)
    parts: list[str] = []
    cursor = 0
    for group, kind in enumerate(kinds, start=1):
        start, end = match.span(group)
        parts.append(whole[cursor : start - offset])
        parts.append(str(labels.of(kind, int(match.group(group)))))
        cursor = end - offset
    parts.append(whole[cursor:])
    return "".join(parts)


def _relabel_text(text: str, labels: _Labels) -> str:
    """``text`` with every scenario name, and every scenario id written into it, as its label."""
    for name, label in labels.texts:
        text = text.replace(name, label)
    for pattern, kinds in _ID_PATTERNS:
        text = pattern.sub(partial(_relabel_match, kinds=kinds, labels=labels), text)
    return text


def _keep(value: Any, field: str | None, labels: _Labels) -> Any:
    # None, bool, and float: no dumped model has a float today; json writes one with repr().
    return value


def _enum_value(value: Enum, field: str | None, labels: _Labels) -> Any:
    return value.value


def _walk_int(value: int, field: str | None, labels: _Labels) -> int | str:
    kind = _ID_FIELDS.get(field) if field else None
    return labels.of(kind, value) if kind else value


def _walk_str(value: str, field: str | None, labels: _Labels) -> str:
    kind = _DIGIT_ID_FIELDS.get(field) if field else None
    if kind and value.isdigit():
        label = labels.of(kind, int(value))
        return label if isinstance(label, str) else value
    return _relabel_text(value, labels)


def _decimal_text(value: Decimal, field: str | None, labels: _Labels) -> str:
    # str() keeps the exponent: "1100.00000000", "1.1E+3" and "0E-8" stay distinct.
    return str(value)


def _reject_datetime(value: datetime, field: str | None, labels: _Labels) -> Any:
    raise TypeError(f"{field!r} holds a datetime: a wall-clock value would make the golden age with the calendar")


def _date_text(value: date, field: str | None, labels: _Labels) -> str:
    return value.isoformat()


def _walk_model(value: BaseModel, field: str | None, labels: _Labels) -> Any:
    # python mode keeps Decimal, date and Enum as they are; mode="json" formats SafeDecimal with format(v, "f").
    return _walk(value.model_dump(mode="python"), field, labels)


def _key_label(key: Any, field: str | None, labels: _Labels) -> str:
    if field in _BROKER_KEYED_FIELDS:
        return str(labels.of("broker", key))
    if field in _ASSET_KEYED_FIELDS:
        return str(labels.of("asset", key))
    if field in _POSITION_KEYED_FIELDS:
        return labels.position(key)
    if isinstance(key, Enum):
        return str(key.value)
    if isinstance(key, str):
        return _relabel_text(key, labels)
    raise TypeError(f"{type(key).__name__} key {key!r} in {field!r}: add the field to the keyed-field tables")


def _walk_mapping(value: Mapping[Any, Any], field: str | None, labels: _Labels) -> dict[str, Any]:
    dumped: dict[str, Any] = {}
    for key, item in value.items():
        label = _key_label(key, field, labels)
        if label in dumped:
            raise ValueError(f"two keys of {field!r} map to the label {label!r}")
        # A name key (a model field) is the context of its value; an id key passes the dict's own field on.
        dumped[label] = _walk(item, key if isinstance(key, str) else field, labels)
    return dumped


def _walk_sequence(value: list[Any] | tuple[Any, ...], field: str | None, labels: _Labels) -> Any:
    if field in _POSITION_TUPLE_FIELDS:
        return labels.position(value)
    return [_walk(item, field, labels) for item in value]


def _canonical(item: Any) -> str:
    return json.dumps(item, sort_keys=True)


def _walk_daily_states(value: DailyStates, field: str | None, labels: _Labels) -> list[Any]:
    # P4: the engine keeps its computed days as segments; dumped as every day's state, the dump a list of them gave.
    return _walk_sequence(list(value), field, labels)


def _walk_set(value: set[Any] | frozenset[Any], field: str | None, labels: _Labels) -> list[Any]:
    # A set iterates in hash order, i.e. by absolute id: sorted once labelled.
    return sorted((_walk(item, field, labels) for item in value), key=_canonical)


def _walk_dataclass(value: Any, field: str | None, labels: _Labels) -> dict[str, Any]:
    # Public fields only: AverageCost's _step_dates and _steps_by_id are lookup caches built from its steps.
    return {item.name: _walk(getattr(value, item.name), item.name, labels) for item in dataclasses.fields(value) if not item.name.startswith("_")}


# Checked in order: bool before int, Enum before int and str, datetime before date.
_HANDLERS: tuple[tuple[type | tuple[type, ...], Callable[[Any, str | None, _Labels], Any]], ...] = (
    ((type(None), bool, float), _keep),
    (Enum, _enum_value),
    (int, _walk_int),
    (str, _walk_str),
    (Decimal, _decimal_text),
    (datetime, _reject_datetime),
    (date, _date_text),
    (BaseModel, _walk_model),
    (Mapping, _walk_mapping),
    (DailyStates, _walk_daily_states),
    ((list, tuple), _walk_sequence),
    ((set, frozenset), _walk_set),
)


def _walk(value: Any, field: str | None, labels: _Labels) -> Any:
    """``value`` as JSON-ready data: ids and names labelled, Decimal as str(), sets sorted.

    ``field`` is the name the value sits under: it decides whether an int is an id."""
    for kinds, handler in _HANDLERS:
        if isinstance(value, kinds):
            return handler(value, field, labels)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _walk_dataclass(value, field, labels)
    raise TypeError(f"no dump rule for {type(value).__name__} in {field!r}")


def _broker_order(entry: dict[str, Any]) -> tuple[bool, str]:
    """Labelled brokers in label order, the broker-less entry (the residual) last."""
    return entry["broker_id"] is None, str(entry["broker_id"] or "")


def _sorted_by_broker(entries: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    # Emitted while iterating a set of broker ids, so the order follows the absolute ids; a stable
    # sort on the label keeps the entries of one broker in their emission order.
    return None if entries is None else sorted(entries, key=_broker_order)


def _normalize_contribution(contribution: dict[str, Any] | None) -> dict[str, Any] | None:
    if contribution is not None:
        # get_positions_contribution fills both lists in `for bid in set(...)`.
        contribution["unallocated"] = _sorted_by_broker(contribution["unallocated"])
        contribution["other_effects"] = _sorted_by_broker(contribution["other_effects"])
    return contribution


# Kept as computed, after checking that neither the calendar nor other tests can move them:
# - every call passes date_to, so the service's `date_to or date.today()` fallbacks and the
#   engine's never run; calculate() reports the range it computed, not its today defaults;
# - price staleness counts the days back from the valued day (mark.price_backward_fill), not from today;
# - the missing/unresolved FX pair lists stay empty (EUR/IDR has a rate from 01-01 and fx.convert_bulk
#   backward-fills without an age limit), and the configured-pair lookup only runs for a missing pair,
#   so the global FX configuration never reaches the output; carried_forward_fx_pairs holds only IDR/EUR;
# - MWRR comes out of scipy's float Newton solver as Decimal(str(rate)) quantized: the same for the
#   same inputs and library build; a scipy/numpy upgrade could move its last digit, which shows up
#   as a diff confined to mwrr_* fields, to review before regenerating.


def _normalize_report(report: dict[str, Any]) -> dict[str, Any]:
    # generated_at is the day the report runs (date.today()): dropped so the golden does not age.
    del report["metadata"]["generated_at"]
    # broker_pnl_history follows broker_contributions, which the engine fills from its all_broker_ids set.
    report["broker_pnl_history"] = _sorted_by_broker(report["broker_pnl_history"])
    report["positions_contribution"] = _normalize_contribution(report["positions_contribution"])
    return report


_SERIES_NORMALIZERS: dict[str, Callable[[Any], Any]] = {
    "get_broker_pnl_history": _sorted_by_broker,
    "get_positions_contribution": _normalize_contribution,
}


def _dump_engine(result: PortfolioCalculationResult, labels: _Labels) -> dict[str, Any]:
    dump = {name: _walk(getattr(result, name), name, labels) for name in _ENGINE_RESULT_FIELDS}
    end_state = result.end_state
    dump["end_state"] = None if end_state is None else {name: _walk(getattr(end_state, name), name, labels) for name in _ENGINE_END_STATE_FIELDS}
    # calculate() fills scope_broker_ids with list(set(...)): the order follows the absolute ids.
    dump["scope_broker_ids"] = sorted(dump["scope_broker_ids"], key=str)
    return dump


def _report_query(date_from: date | None, date_to: date) -> PortfolioReportQuery:
    return PortfolioReportQuery(
        broker_ids=None,
        date_range=OpenDateRangeModel(start=date_from, end=date_to),
        target_currency="EUR",
        include_summary=True,
        include_history=True,
        include_allocation_history=True,
        include_breakdown=True,
        include_positions_contribution=True,
        include_broker_pnl_history=True,
        include_pnl_candles=True,
        include_income_history=True,
        include_cost_history=True,
        include_deposit_history=True,
        include_acquisition_funding=True,
    )


async def _dump_window(session: AsyncSession, copy: _Copy, date_from: date | None, date_to: date) -> dict[str, Any]:
    """Every dumped call for one window, labelled.

    Each call starts from cold caches, so each dump is what that call computes and not a slice
    of an earlier call's blob: the getters run the engine from the first transaction, and W2's
    direct calculate() would otherwise be cut out of the report's blob."""
    service = PortfolioService(session)
    labels = copy.labels
    dump: dict[str, Any] = {}

    _clear_portfolio_caches()
    report = await service.get_report(copy.user_id, _report_query(date_from, date_to))
    dump["get_report"] = _normalize_report(_walk(report, None, labels))

    _clear_portfolio_caches()
    summary = await service.get_summary(user_id=copy.user_id, broker_ids=None, include_breakdown=True, target_currency_override="EUR", date_from=date_from, date_to=date_to)
    dump["get_summary"] = _walk(summary, None, labels)

    for name in _SERIES_GETTERS:
        _clear_portfolio_caches()
        series = await getattr(service, name)(user_id=copy.user_id, broker_ids=None, date_from=date_from, date_to=date_to, target_currency_override="EUR")
        dumped = _walk(series, None, labels)
        normalize = _SERIES_NORMALIZERS.get(name)
        dump[name] = normalize(dumped) if normalize else dumped

    _clear_portfolio_caches()
    result = await PortfolioCalculationEngine(session).calculate(copy.user_id, None, date_from, date_to, "EUR", include_candles=True, include_acquisition_funding=True)
    dump["engine.calculate"] = _dump_engine(result, labels)
    return dump


async def _dump_copy(session: AsyncSession, copy: _Copy) -> str:
    """The golden's text for one copy: keys sorted, two-space indent, trailing newline."""
    dump = {window: await _dump_window(session, copy, date_from, date_to) for window, date_from, date_to in _WINDOWS}
    return json.dumps(dump, sort_keys=True, indent=2) + "\n"


def _diff(expected: str, actual: str, expected_name: str, actual_name: str) -> str:
    """The unified diff of two dumps, cut to its first ``_DIFF_LINES`` lines."""
    lines = list(difflib.unified_diff(expected.splitlines(), actual.splitlines(), expected_name, actual_name, lineterm=""))
    if len(lines) > _DIFF_LINES:
        lines = [*lines[:_DIFF_LINES], f"... {len(lines) - _DIFF_LINES} more lines of diff"]
    return "\n".join(lines)


# =============================================================================
# FIXTURES — own copies of the helpers of test_portfolio_service.py
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def range_bound_lifted():
    """R13-SEC7-1: the guarded portfolio lives in January 2091, after tomorrow, so the range bound is lifted for the
    whole module, before any fixture builds data (see ``lift_range_bound``): the golden keeps the unbounded outputs."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        lift_range_bound(monkeypatch)
        yield


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture
def clean_portfolio_caches(request):
    """No cached report, WAC or engine blob crosses into or out of the test."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


# =============================================================================
# TestNativeCashGuard
# =============================================================================


class TestNativeCashGuard:
    """EUR-only outputs of the portfolio service and engine, byte for byte."""

    @pytest.mark.asyncio
    async def test_eur_only_dump_is_byte_identical(self, session, clean_portfolio_caches):
        keep_alive: list[object] = []
        # FxRate rows are global (no owner): written once, shared by both copies.
        await _persist(session, keep_alive, *(FxRate(date=_day(day), base="EUR", quote="IDR", rate=Decimal(rate), source="TEST") for day, rate in _EUR_IDR_RATES))
        first = await _build_copy(session, keep_alive)
        second = await _build_copy(session, keep_alive)
        assert first.user_id != second.user_id

        first_text = await _dump_copy(session, first)
        second_text = await _dump_copy(session, second)
        assert first_text == second_text, "the two copies of the scenario dump differently: an id or a name escaped the labels, or a list follows the absolute ids\n" + _diff(first_text, second_text, "first copy", "second copy")

        if os.environ.get(_REGEN_ENV) == "1":
            GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN_PATH.write_text(first_text, encoding="utf-8")
            pytest.skip("golden regenerated")
        if not GOLDEN_PATH.exists():
            pytest.fail(f"golden file missing: {GOLDEN_PATH}\nGenerate it with: {_REGEN_COMMAND}")
        golden = GOLDEN_PATH.read_text(encoding="utf-8")
        assert first_text == golden, f"EUR-only outputs differ from {GOLDEN_PATH.name}:\n" + _diff(golden, first_text, "golden", "this run")
