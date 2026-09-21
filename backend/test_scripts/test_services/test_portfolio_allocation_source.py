"""Bounded contract matrix for the PAC/Rebalancer portfolio domain copy.

The suite is intentionally source-only: every database boundary is represented by
deterministic fakes, provider/network entry points are never used, and no shared
database row or process cache is mutated.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from backend.app.db.models import AssetType, UserRole
from backend.app.schemas.common import Currency, FxBackwardFillInfo
from backend.app.schemas.portfolio import (
    PlannerSourceSection,
    PortfolioPlannerSourceRequest,
)
from backend.app.schemas.wac import WACPreviewResultItem, WACQualifyingTX
from backend.app.services import portfolio_allocation_source as source
from backend.app.services import portfolio_service
from backend.app.utils.financial.wac_utils import WACInputTX, compute_wac_from_txlist

AS_OF = date(2026, 9, 15)
CAPTURED_AT = datetime(2026, 9, 15, 12, 30, tzinfo=UTC)


class _Scalars:
    def __init__(self, values):
        self._values = list(values)

    def __iter__(self):
        return iter(self._values)

    def all(self):
        return list(self._values)


class _Rows:
    def __init__(self, rows=(), *, scalar_values=None):
        self._rows = list(rows)
        self._scalar_values = list(rows if scalar_values is None else scalar_values)

    def all(self):
        return list(self._rows)

    def scalars(self):
        return _Scalars(self._scalar_values)


class _QueuedReadSession:
    """Minimal AsyncSession witness that can only execute queued SELECT results."""

    def __init__(self, *results: _Rows):
        self._results = list(results)
        self.statements = []
        self.write_calls: list[str] = []

    async def execute(self, statement):
        self.statements.append(statement)
        if not self._results:
            raise AssertionError(f"Unexpected database read: {statement}")
        return self._results.pop(0)

    def add(self, _value):
        self.write_calls.append("add")
        raise AssertionError("The planner source must not add rows")

    async def delete(self, _value):
        self.write_calls.append("delete")
        raise AssertionError("The planner source must not delete rows")

    async def flush(self):
        self.write_calls.append("flush")
        raise AssertionError("The planner source must not flush rows")

    async def commit(self):
        self.write_calls.append("commit")
        raise AssertionError("The planner source must not commit rows")

    @property
    def pending_results(self) -> int:
        return len(self._results)


def _asset(
    asset_id: int,
    *,
    name: str | None = None,
    currency: str = "EUR",
    active: bool = True,
    quote_base_quantity: int | None = 1,
    classification_params: str | None = None,
    asset_type=AssetType.STOCK,
):
    return SimpleNamespace(
        id=asset_id,
        display_name=name or f"Asset {asset_id}",
        identifier_ticker=f"T{asset_id}",
        asset_type=asset_type,
        icon_url=f"https://example.test/assets/{asset_id}.svg",
        active=active,
        currency=currency,
        quote_base_quantity=quote_base_quantity,
        classification_params=classification_params,
    )


def _broker(
    broker_id: int,
    *,
    name: str | None = None,
    active: bool = True,
):
    return SimpleNamespace(
        id=broker_id,
        name=name or f"Broker {broker_id}",
        icon_url=f"https://example.test/brokers/{broker_id}.svg",
        portal_url=f"https://example.test/brokers/{broker_id}",
        default_import_plugin=f"broker-{broker_id}",
        is_active=active,
        allow_cash_overdraft=True,
        allow_asset_shorting=False,
    )


def _access(
    broker_id: int,
    *,
    user_id: int = 41,
    role: UserRole = UserRole.OWNER,
    share: str = "1",
):
    return SimpleNamespace(
        user_id=user_id,
        broker_id=broker_id,
        role=role,
        share_percentage=Decimal(share),
    )


def _price(
    asset_id: int,
    *,
    on: date = date(2026, 9, 10),
    close: str = "123.4500",
    currency: str = "EUR",
    source_name: str = "SAVED_PRICE",
):
    return SimpleNamespace(
        asset_id=asset_id,
        date=on,
        close=Decimal(close),
        currency=currency,
        source_plugin_key=source_name,
    )


def _fx(
    *,
    on: date = date(2026, 9, 10),
    base: str = "EUR",
    quote: str = "USD",
    rate: str = "1.25",
    source_name: str = "SAVED_FX",
):
    return SimpleNamespace(
        date=on,
        base=base,
        quote=quote,
        rate=Decimal(rate),
        source=source_name,
    )


def _valid_classification() -> str:
    return json.dumps(
        {
            "sector_area": {
                "distribution": {
                    "Technology": 0.6,
                    "Financials": 0.4,
                }
            },
            "geographic_area": {
                "distribution": {
                    "USA": 0.75,
                    "ITA": 0.25,
                }
            },
        }
    )


def _request_payload() -> dict[str, object]:
    return {
        "as_of": AS_OF.isoformat(),
        "target_currency": "eur",
        "requested_sections": [
            "assets",
            "holdings",
            "fx_quotes",
        ],
        "broker_ids": [7, 9],
        "asset_ids": None,
        "fx_pairs": ["EUR/USD"],
    }


def _request(**changes) -> PortfolioPlannerSourceRequest:
    payload = _request_payload()
    payload.update(changes)
    return PortfolioPlannerSourceRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("asset_ids", "expected"),
    [
        pytest.param(None, None, id="catalog"),
        pytest.param([], [], id="manual-only"),
    ],
)
def test_planner_request_preserves_nullable_asset_scope_and_exact_wire_shape(
    asset_ids,
    expected,
):
    request = _request(asset_ids=asset_ids)

    assert request.asset_ids == expected
    assert request.model_dump(mode="json") == {
        "as_of": "2026-09-15",
        "target_currency": "EUR",
        "requested_sections": [
            "assets",
            "holdings",
            "fx_quotes",
        ],
        "broker_ids": [7, 9],
        "asset_ids": expected,
        "fx_pairs": ["EUR/USD"],
    }


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("as_of", id="as-of"),
        pytest.param("target_currency", id="target-currency"),
        pytest.param("requested_sections", id="requested-sections"),
        pytest.param("broker_ids", id="broker-ids"),
        pytest.param("asset_ids", id="asset-ids-nullable-but-required"),
        pytest.param("fx_pairs", id="fx-pairs"),
    ],
)
def test_planner_request_requires_every_root_shape_field(field):
    payload = _request_payload()
    payload.pop(field)

    with pytest.raises(ValidationError):
        PortfolioPlannerSourceRequest.model_validate(payload)


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"broker_ids": []}, id="empty-brokers"),
        pytest.param({"broker_ids": [7, 7]}, id="duplicate-brokers"),
        pytest.param({"broker_ids": [True]}, id="boolean-broker"),
        pytest.param({"asset_ids": [11, 11]}, id="duplicate-assets"),
        pytest.param({"asset_ids": [True]}, id="boolean-asset"),
        pytest.param({"requested_sections": []}, id="empty-sections"),
        pytest.param(
            {"requested_sections": ["assets", "assets"]},
            id="duplicate-sections",
        ),
        pytest.param(
            {"requested_sections": ["recommendations"]},
            id="unknown-section",
        ),
        pytest.param({"target_currency": "NOT_A_CURRENCY"}, id="non-iso-target"),
        # fx_pairs items are now plain canonical strings ("AAA/BBB"), not
        # {source_currency, destination_currency} objects: the malformed
        # cases below exercise the string validator directly instead of a
        # nested-object shape that no longer exists. Note: a non-string list
        # item (e.g. `[True]`) is deliberately NOT a case here — verified
        # against the frozen validator, it partitions the raw value before
        # any type check and raises an uncaught AttributeError rather than a
        # ValidationError, so it would not fit this shared
        # pytest.raises(ValidationError) body; "fx-pairs-not-a-list" below
        # covers the equivalent "wrong type" contract at the field level.
        pytest.param({"fx_pairs": ["USD-EUR"]}, id="malformed-fx-separator"),
        pytest.param({"fx_pairs": ["ZZZ/EUR"]}, id="non-iso-fx-currency"),
        pytest.param({"fx_pairs": "EUR/USD"}, id="fx-pairs-not-a-list"),
        pytest.param({"fx_pairs": ["USD/EUR"]}, id="wrong-order-fx-pair"),
        pytest.param({"fx_pairs": ["EUR/EUR"]}, id="identity-fx-pair"),
        pytest.param(
            {"fx_pairs": ["EUR/USD", "EUR/USD"]},
            id="duplicate-fx-pair",
        ),
        pytest.param({"as_of": "15/09/2026"}, id="non-iso-date"),
    ],
)
def test_planner_request_rejects_only_structurally_malformed_inputs(changes):
    payload = _request_payload()
    payload.update(changes)

    with pytest.raises(ValidationError):
        PortfolioPlannerSourceRequest.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {
                **_request_payload(),
                "user_id": 99,
            },
            id="user-id-extra",
        ),
        pytest.param(
            {
                **_request_payload(),
                "as_user": 99,
            },
            id="as-user-extra",
        ),
        # nested-fx-extra removed: fx_pairs items are now plain canonical
        # strings ("AAA/BBB"), not objects, so there is no nested key left
        # to pollute with an unexpected field.
    ],
)
def test_planner_request_rejects_unknown_fields_recursively(payload):
    with pytest.raises(ValidationError):
        PortfolioPlannerSourceRequest.model_validate(payload)


def test_planner_request_has_no_withdrawn_16_4_32_4_collection_caps():
    request = _request(
        requested_sections=[section.value for section in PlannerSourceSection],
        broker_ids=list(range(1, 18)),
        asset_ids=list(range(101, 134)),
        fx_pairs=["/".join(sorted((currency, "EUR"))) for currency in ("USD", "GBP", "CHF", "JPY", "KWD")],
    )

    assert len(request.broker_ids) == 17
    assert len(request.requested_sections) == len(PlannerSourceSection)
    assert len(request.asset_ids or []) == 33
    assert len(request.fx_pairs) == 5


class _OwnerAccessSession:
    def __init__(
        self,
        *,
        broker_exists: bool,
        broker_id: int = 7,
        access_row=None,
    ):
        self.broker_exists = broker_exists
        self.broker_id = broker_id
        self.access_row = access_row
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 1:
            params = statement.compile().params.values()
            assert UserRole.OWNER in params or UserRole.OWNER.value in params
            return _Rows([self.access_row] if self.access_row is not None else [])
        raise AssertionError("Authorization must use exactly one non-enumerating preflight read")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        pytest.param(UserRole.OWNER, True, id="owner-zero-percent"),
        pytest.param(UserRole.EDITOR, False, id="editor"),
        pytest.param(UserRole.VIEWER, False, id="viewer"),
        pytest.param(None, False, id="nonmember"),
    ],
)
async def test_selected_broker_scope_requires_owner_and_accepts_owner_zero_percent(
    role,
    allowed,
):
    broker = _broker(7)
    row = (_access(7, role=role, share="0"), broker) if role == UserRole.OWNER else None
    session = _OwnerAccessSession(broker_exists=True, access_row=row)

    if not allowed:
        with pytest.raises(source.PortfolioPlannerSourceAccessError):
            await source._load_selected_owner_accesses(
                session,
                user_id=41,
                broker_ids=[7],
            )
        return

    rows, accesses = await source._load_selected_owner_accesses(
        session,
        user_id=41,
        broker_ids=[7],
    )
    assert rows == [row]
    owner_access, _owner_broker = accesses[7]
    assert owner_access.share_percentage == Decimal("0")


@pytest.mark.asyncio
async def test_missing_and_unauthorized_brokers_are_indistinguishable_before_private_reads():
    missing_session = _OwnerAccessSession(broker_exists=False)
    unauthorized_session = _OwnerAccessSession(
        broker_exists=True,
        access_row=None,
    )
    # Broker existence is out-of-band scenario truth; the access boundary must
    # expose the same error and read footprint for both cases.
    observable_errors = (
        source.PortfolioPlannerSourceAccessError,
        source.PortfolioPlannerSourceBrokerNotFoundError,
    )

    with pytest.raises(observable_errors) as missing_error:
        await source._load_selected_owner_accesses(
            missing_session,
            user_id=41,
            broker_ids=[7],
        )
    with pytest.raises(observable_errors) as unauthorized_error:
        await source._load_selected_owner_accesses(
            unauthorized_session,
            user_id=41,
            broker_ids=[7],
        )

    assert type(missing_error.value) is type(unauthorized_error.value)
    assert type(missing_error.value) is source.PortfolioPlannerSourceAccessError
    assert str(missing_error.value) == str(unauthorized_error.value)
    assert len(missing_session.statements) == len(unauthorized_session.statements)


@pytest.mark.asyncio
async def test_builder_authorizes_every_broker_before_all_private_reads(
    monkeypatch,
):
    events: list[str] = []
    broker = _broker(7)
    access = _access(7, share="0")
    asset = _asset(11, classification_params=_valid_classification())
    price = _price(11)

    async def authorize(*_args, **_kwargs):
        events.append("authorize")
        return [(access, broker)], {7: (access, broker)}

    async def holdings(*_args, **_kwargs):
        events.append("holdings")
        return [(7, 11, Decimal("2"))]

    async def assets(*_args, **_kwargs):
        events.append("assets")
        return [asset]

    async def cash(*_args, **_kwargs):
        events.append("cash")
        return {7: {"EUR": Decimal("5")}}

    async def prices(*_args, **_kwargs):
        events.append("prices")
        return {11: price}

    def classifications(*_args, **_kwargs):
        events.append("classifications")
        return []

    async def wac(*_args, **_kwargs):
        events.append("wac")
        return [], {"EUR"}

    async def fx(*_args, **_kwargs):
        events.append("fx")
        return [], {"EUR", "USD"}

    monkeypatch.setattr(source, "_load_selected_owner_accesses", authorize)
    monkeypatch.setattr(source, "_load_holding_rows", holdings)
    monkeypatch.setattr(source, "_load_planner_assets", assets)
    monkeypatch.setattr(source, "_load_cash_by_broker", cash)
    monkeypatch.setattr(source, "_load_latest_prices", prices)
    monkeypatch.setattr(source, "_build_planner_classifications", classifications)
    monkeypatch.setattr(source, "_build_planner_wac_contexts", wac)
    monkeypatch.setattr(source, "_build_planner_fx_quotes", fx)
    monkeypatch.setattr(source, "utcnow", lambda: CAPTURED_AT)

    await source.build_portfolio_planner_source(
        object(),
        user_id=41,
        request=_request(
            broker_ids=[7],
            asset_ids=[11],
            requested_sections=[section.value for section in PlannerSourceSection],
        ),
    )

    assert events == [
        "authorize",
        "holdings",
        "assets",
        "cash",
        "prices",
        "classifications",
        "wac",
        "fx",
    ]


@pytest.mark.asyncio
async def test_mixed_allowed_and_denied_broker_scope_is_atomic(
    monkeypatch,
):
    session = _QueuedReadSession(
        _Rows([(_access(7), _broker(7))]),
    )
    private_async = {
        name: AsyncMock(side_effect=AssertionError(f"{name} ran before auth"))
        for name in (
            "_load_holding_rows",
            "_load_planner_assets",
            "_load_cash_by_broker",
            "_load_latest_prices",
            "_build_planner_wac_contexts",
            "_build_planner_fx_quotes",
        )
    }
    classifications = MagicMock(side_effect=AssertionError("classification read ran before auth"))
    for name, spy in private_async.items():
        monkeypatch.setattr(source, name, spy)
    monkeypatch.setattr(
        source,
        "_build_planner_classifications",
        classifications,
    )

    with pytest.raises(source.PortfolioPlannerSourceAccessError):
        await source.build_portfolio_planner_source(
            session,
            user_id=41,
            request=_request(
                broker_ids=[7, 99],
                requested_sections=[section.value for section in PlannerSourceSection],
            ),
        )

    assert len(session.statements) == 1
    for spy in private_async.values():
        spy.assert_not_awaited()
    classifications.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "requested_asset_ids",
        "held_asset_ids",
        "catalog_rows",
        "expected_ids",
        "expected_reads",
    ),
    [
        pytest.param(
            None,
            {2},
            [
                _asset(1, active=True),
                _asset(2, active=False),
                _asset(3, active=False),
            ],
            {1, 2},
            1,
            id="null-active-global-plus-inactive-held",
        ),
        pytest.param(
            [],
            {2},
            [],
            set(),
            0,
            id="empty-manual-only",
        ),
        pytest.param(
            [3],
            set(),
            [_asset(3, active=False)],
            {3},
            1,
            id="explicit-unheld-inactive-global",
        ),
    ],
)
async def test_asset_scope_selector_contract(
    requested_asset_ids,
    held_asset_ids,
    catalog_rows,
    expected_ids,
    expected_reads,
):
    results = [_Rows(scalar_values=catalog_rows)] if expected_reads else []
    session = _QueuedReadSession(*results)

    assets = await source._load_planner_assets(
        session,
        requested_asset_ids=requested_asset_ids,
        held_asset_ids=held_asset_ids,
        include_catalog=True,
    )

    assert {asset.id for asset in assets} == expected_ids
    assert len(session.statements) == expected_reads


@pytest.mark.asyncio
async def test_missing_explicit_asset_fails_atomically(monkeypatch):
    session = _QueuedReadSession(
        _Rows(scalar_values=[_asset(11)]),
    )

    with pytest.raises(source.PortfolioPlannerSourceAssetNotFoundError):
        await source._load_planner_assets(
            session,
            requested_asset_ids=[11, 12],
            held_asset_ids=set(),
            include_catalog=True,
        )

    broker = _broker(7)
    access = _access(7)
    monkeypatch.setattr(
        source,
        "_load_selected_owner_accesses",
        AsyncMock(return_value=([(access, broker)], {7: (access, broker)})),
    )
    monkeypatch.setattr(
        source,
        "_load_holding_rows",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        source,
        "_load_planner_assets",
        AsyncMock(side_effect=source.PortfolioPlannerSourceAssetNotFoundError("Selected Asset scope contains a missing Asset")),
    )
    downstream = {
        name: AsyncMock(side_effect=AssertionError(f"{name} ran after missing Asset"))
        for name in (
            "_load_cash_by_broker",
            "_load_latest_prices",
            "_build_planner_wac_contexts",
            "_build_planner_fx_quotes",
        )
    }
    for name, spy in downstream.items():
        monkeypatch.setattr(source, name, spy)

    with pytest.raises(source.PortfolioPlannerSourceAssetNotFoundError):
        await source.build_portfolio_planner_source(
            object(),
            user_id=41,
            request=_request(
                broker_ids=[7],
                asset_ids=[11, 12],
                requested_sections=[section.value for section in PlannerSourceSection],
            ),
        )

    for spy in downstream.values():
        spy.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_asset_scope_emits_no_asset_holding_price_classification_or_wac_rows(
    monkeypatch,
):
    broker = _broker(7)
    access = _access(7)
    monkeypatch.setattr(
        source,
        "_load_selected_owner_accesses",
        AsyncMock(return_value=([(access, broker)], {7: (access, broker)})),
    )
    monkeypatch.setattr(
        source,
        "_load_holding_rows",
        AsyncMock(return_value=[(7, 11, Decimal("9"))]),
    )

    response = await source.build_portfolio_planner_source(
        object(),
        user_id=41,
        request=_request(
            broker_ids=[7],
            asset_ids=[],
            requested_sections=[
                "assets",
                "holdings",
                "prices",
                "classifications",
                "wac_contexts",
            ],
            fx_pairs=[],
        ),
    )

    assert response.assets == []
    assert response.holdings == []
    assert response.prices == []
    assert response.classifications == []
    assert response.wac_contexts == []


@pytest.mark.asyncio
async def test_explicit_unheld_global_asset_keeps_identity_price_and_classification(
    monkeypatch,
):
    broker = _broker(7)
    access = _access(7)
    asset = _asset(
        11,
        currency="USD",
        quote_base_quantity=100,
        classification_params=_valid_classification(),
    )
    price = _price(
        11,
        close="98.125000",
        currency="USD",
        source_name="MANUAL_SAVED",
    )
    monkeypatch.setattr(
        source,
        "_load_selected_owner_accesses",
        AsyncMock(return_value=([(access, broker)], {7: (access, broker)})),
    )
    monkeypatch.setattr(
        source,
        "_load_holding_rows",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        source,
        "_load_planner_assets",
        AsyncMock(return_value=[asset]),
    )
    monkeypatch.setattr(
        source,
        "_load_latest_prices",
        AsyncMock(return_value={11: price}),
    )

    response = await source.build_portfolio_planner_source(
        object(),
        user_id=41,
        request=_request(
            broker_ids=[7],
            asset_ids=[11],
            requested_sections=[
                "assets",
                "holdings",
                "prices",
                "classifications",
            ],
            fx_pairs=[],
        ),
    )
    dumped = response.model_dump(mode="json")

    assert {row["asset_id"] for row in dumped["assets"]} == {"asset:11"}
    assert dumped["holdings"] == []
    price_by_asset = {row["asset_id"]: row for row in dumped["prices"]}
    assert price_by_asset["asset:11"] == {
        "price_id": "price:asset:11:2026-09-10",
        "asset_id": "asset:11",
        "amount": "98.125000",
        "currency": "USD",
        "quote_base_quantity": "100",
        "reference_date": "2026-09-10",
        "source": "MANUAL_SAVED",
        "days_before_requested": 5,
        "provenance_id": "source:market-data",
    }
    assert {(row["dimension"], row["category_id"]) for row in dumped["classifications"]} == {
        ("asset_type", "STOCK"),
        ("sector", "Financials"),
        ("sector", "Technology"),
        ("geography", "ITA"),
        ("geography", "USA"),
    }


def test_inactive_unheld_explicit_asset_stays_visible_with_typed_issue():
    issues = []
    inactive_asset = _asset(31, active=False)
    rows = source._build_planner_assets(
        [inactive_asset],
        held_asset_ids=set(),
        explicit_asset_selection=True,
        issues=issues,
    )

    assert {row.asset_id for row in rows} == {"asset:31"}
    inactive = next(row for row in rows if row.asset_id == "asset:31")
    assert inactive.active is False
    assert [(issue.code, issue.kind, issue.path.entity_id, issue.path.field) for issue in issues] == [
        (
            "allocation.asset_inactive_not_buyable",
            "unsupported",
            "asset:31",
            "active",
        )
    ]

    held_issues = []
    held_rows = source._build_planner_assets(
        [inactive_asset],
        held_asset_ids={31},
        explicit_asset_selection=False,
        issues=held_issues,
    )
    assert {row.asset_id for row in held_rows} == {"asset:31"}
    assert held_issues == []


@pytest.mark.asyncio
async def test_w2_inactive_broker_keeps_holdings_cash_and_typed_warning(
    monkeypatch,
):
    """W2: inactive custody remains factual, not inferred as executable."""
    broker = _broker(7, name="Inactive Custodian", active=False)
    scenario_broker_id = f"broker:{broker.id}"
    assert scenario_broker_id == "broker:7"
    access = _access(7, share="0.125000")
    asset = _asset(11)
    session = _QueuedReadSession(
        _Rows([(access, broker)]),
        _Rows([(7, 11, Decimal("2.5000"))]),
        _Rows(scalar_values=[asset]),
        _Rows([(7, "EUR", Decimal("9.8700"))]),
    )
    monkeypatch.setattr(source, "utcnow", lambda: CAPTURED_AT)

    response = await source.build_portfolio_planner_source(
        session,
        user_id=41,
        request=_request(
            broker_ids=[7],
            asset_ids=[11],
            requested_sections=[
                "brokers",
                "holdings",
                "cash_balances",
            ],
            fx_pairs=[],
        ),
    )
    dumped = response.model_dump(mode="json")

    assert session.pending_results == 0
    assert session.write_calls == []
    brokers_by_id = {row["broker_id"]: row for row in dumped["brokers"]}
    assert brokers_by_id == {
        "broker:7": {
            "broker_id": "broker:7",
            "source_broker_id": 7,
            "name": "Inactive Custodian",
            "icon_url": "https://example.test/brokers/7.svg",
            "portal_url": "https://example.test/brokers/7",
            "default_import_plugin": "broker-7",
            "access_role": "OWNER",
            "ownership_share": "0.125000",
            "observed_currencies": ["EUR"],
            "active": False,
            "allow_cash_overdraft": True,
            "allow_asset_shorting": False,
            "execution_profile_status": "not_available",
            "provenance_id": "source:broker-domain",
        }
    }
    copied_broker = brokers_by_id[scenario_broker_id]
    inactive_broker_ids = {broker_id for broker_id, broker_payload in brokers_by_id.items() if broker_payload["active"] is False}
    assert inactive_broker_ids == {scenario_broker_id}
    assert {key for key in copied_broker if key == "opened_at" or any(fragment in key for fragment in ("filter", "route", "capabilit"))} == set()
    assert {
        "allow_cash_overdraft": copied_broker["allow_cash_overdraft"],
        "allow_asset_shorting": copied_broker["allow_asset_shorting"],
        "execution_profile_status": copied_broker["execution_profile_status"],
    } == {
        "allow_cash_overdraft": True,
        "allow_asset_shorting": False,
        "execution_profile_status": "not_available",
    }
    assert {row["holding_id"]: row for row in dumped["holdings"]} == {
        "holding:asset:11:broker:7": {
            "holding_id": "holding:asset:11:broker:7",
            "asset_id": "asset:11",
            "broker_id": "broker:7",
            "custody_quantity": "2.5000",
            "ownership_share": "0.125000",
            "economic_quantity": "0.3125000000",
            "quantity_unit": "asset_unit",
            "provenance_id": "source:portfolio-ledger",
        }
    }
    assert {row["cash_id"]: row for row in dumped["cash_balances"]} == {
        "cash:broker:7:EUR": {
            "cash_id": "cash:broker:7:EUR",
            "broker_id": "broker:7",
            "currency": "EUR",
            "custody_amount": "9.8700",
            "ownership_share": "0.125000",
            "economic_amount": "1.2337500000",
            "provenance_id": "source:portfolio-ledger",
        }
    }
    issue_codes = {issue["code"] for issue in dumped["issues"]}
    assert issue_codes == {
        "allocation.broker_inactive",
        "allocation.broker_execution_profile_unsupported",
    }
    inactive_broker_issues = [issue for issue in dumped["issues"] if issue["code"] == "allocation.broker_inactive"]
    assert len(inactive_broker_issues) == len(inactive_broker_ids) == 1
    assert {issue["path"]["entity_id"]: issue for issue in inactive_broker_issues} == {
        scenario_broker_id: {
            "code": "allocation.broker_inactive",
            "kind": "unsupported",
            "severity": "warning",
            "path": {
                "kind": "field",
                "section": "brokers",
                "entity_kind": "broker",
                "entity_id": scenario_broker_id,
                "field": "active",
            },
            "message_key": "allocation.broker_inactive",
            "params": [],
        }
    }
    execution_profile_issues = [issue for issue in dumped["issues"] if issue["code"] == "allocation.broker_execution_profile_unsupported"]
    assert execution_profile_issues == [
        {
            "code": "allocation.broker_execution_profile_unsupported",
            "kind": "unsupported",
            "severity": "error",
            "path": {
                "kind": "field",
                "section": "brokers",
                "entity_kind": "broker",
                "entity_id": scenario_broker_id,
                "field": "execution_profile_status",
            },
            "message_key": "allocation.broker_execution_profile_unsupported",
            "params": [],
        }
    ]
    assert inactive_broker_issues[0] != execution_profile_issues[0]


def test_holdings_preserve_exact_custody_economic_share_and_provenance():
    issues = []
    accesses = {
        7: (
            _access(7, share="0.250000"),
            _broker(7, name="Same Broker Name"),
        ),
        8: (
            _access(8, share="0"),
            _broker(8, name="Same Broker Name"),
        ),
    }
    rows = source._build_planner_holdings(
        [
            (8, 20, Decimal("-3.5000")),
            (7, 20, Decimal("12.3400")),
            (8, 10, Decimal("4.1250")),
        ],
        accesses=accesses,
        selected_asset_ids={10, 20},
        issues=issues,
    )
    dumped = {row.holding_id: row.model_dump(mode="json") for row in rows}

    assert set(dumped) == {
        "holding:asset:10:broker:8",
        "holding:asset:20:broker:7",
        "holding:asset:20:broker:8",
    }
    assert dumped["holding:asset:20:broker:7"] == {
        "holding_id": "holding:asset:20:broker:7",
        "asset_id": "asset:20",
        "broker_id": "broker:7",
        "custody_quantity": "12.3400",
        "ownership_share": "0.250000",
        "economic_quantity": "3.0850000000",
        "quantity_unit": "asset_unit",
        "provenance_id": "source:portfolio-ledger",
    }
    assert dumped["holding:asset:10:broker:8"]["custody_quantity"] == "4.1250"
    assert dumped["holding:asset:10:broker:8"]["economic_quantity"] == "0.0000"
    assert dumped["holding:asset:20:broker:8"]["custody_quantity"] == "-3.5000"
    assert [issue.model_dump(mode="json") for issue in issues] == [
        {
            "code": "allocation.negative_inventory_unsupported",
            "kind": "unsupported",
            "severity": "error",
            "path": {
                "kind": "field",
                "section": "holdings",
                "entity_kind": "holding",
                "entity_id": "holding:asset:20:broker:8",
                "field": "custody_quantity",
            },
            "message_key": "allocation.negative_inventory_unsupported",
            "params": [],
        }
    ]


def test_cash_preserves_each_native_broker_currency_and_negative_issue():
    broker_7 = _broker(7, name="Same Broker Name")
    broker_8 = _broker(8, name="Same Broker Name")
    access_7 = _access(7, share="0.125000")
    access_8 = _access(8, share="0")
    issues = []

    rows = source._build_planner_cash_balances(
        [(access_7, broker_7), (access_8, broker_8)],
        cash_by_broker={
            7: {
                "USD": Decimal("9.8700"),
                "EUR": Decimal("123.4500"),
            },
            8: {
                "JPY": Decimal("-2500"),
            },
        },
        issues=issues,
    )
    dumped = {row.cash_id: row.model_dump(mode="json") for row in rows}

    assert set(dumped) == {
        "cash:broker:7:EUR",
        "cash:broker:7:USD",
        "cash:broker:8:JPY",
    }
    assert dumped["cash:broker:7:EUR"] == {
        "cash_id": "cash:broker:7:EUR",
        "broker_id": "broker:7",
        "currency": "EUR",
        "custody_amount": "123.4500",
        "ownership_share": "0.125000",
        "economic_amount": "15.4312500000",
        "provenance_id": "source:portfolio-ledger",
    }
    assert dumped["cash:broker:8:JPY"]["custody_amount"] == "-2500"
    assert dumped["cash:broker:8:JPY"]["economic_amount"] == "-0"
    assert [issue.model_dump(mode="json") for issue in issues] == [
        {
            "code": "allocation.negative_cash_unsupported",
            "kind": "unsupported",
            "severity": "error",
            "path": {
                "kind": "field",
                "section": "cash_balances",
                "entity_kind": "cash_balance",
                "entity_id": "cash:broker:8:JPY",
                "field": "custody_amount",
            },
            "message_key": "allocation.negative_cash_unsupported",
            "params": [],
        }
    ]


@pytest.mark.asyncio
async def test_latest_saved_price_query_is_bounded_by_as_of_and_never_refreshes():
    saved = _price(11, on=date(2026, 9, 14))
    session = _QueuedReadSession(_Rows(scalar_values=[saved]))

    prices = await source._load_latest_prices(
        session,
        candidate_asset_ids={11},
        as_of_date=AS_OF,
    )

    assert prices == {11: saved}
    assert len(session.statements) == 1
    (only_statement,) = session.statements
    sql = str(only_statement)
    assert "max(price_history.date)" in sql
    assert "price_history.date <=" in sql
    assert "price_history.close IS NOT NULL" in sql


def test_saved_price_rows_preserve_quote_facts_and_make_missing_basis_explicit():
    priced = _asset(11, currency="KWD", quote_base_quantity=100)
    missing = _asset(12, currency="EUR", quote_base_quantity=None)
    issues = []

    rows = source._build_planner_prices(
        [priced, missing],
        prices={
            11: _price(
                11,
                on=date(2026, 9, 12),
                close="7.123400",
                currency="KWD",
                source_name="SAVED_ONLY",
            )
        },
        as_of=AS_OF,
        issues=issues,
    )
    dumped = {row.asset_id: row.model_dump(mode="json") for row in rows}

    assert dumped["asset:11"] == {
        "price_id": "price:asset:11:2026-09-12",
        "asset_id": "asset:11",
        "amount": "7.123400",
        "currency": "KWD",
        "quote_base_quantity": "100",
        "reference_date": "2026-09-12",
        "source": "SAVED_ONLY",
        "days_before_requested": 3,
        "provenance_id": "source:market-data",
    }
    assert dumped["asset:12"] == {
        "price_id": "price:asset:12:2026-09-15",
        "asset_id": "asset:12",
        "amount": None,
        "currency": "EUR",
        "quote_base_quantity": None,
        "reference_date": None,
        "source": None,
        "days_before_requested": None,
        "provenance_id": "source:market-data",
    }
    assert {(issue.code, issue.path.entity_id, issue.path.field) for issue in issues} == {
        ("allocation.price_missing", "price:asset:12:2026-09-15", "amount"),
        (
            "allocation.quote_base_quantity_missing",
            "price:asset:12:2026-09-15",
            "quote_base_quantity",
        ),
    }


def test_valid_saved_classification_is_exact_sorted_and_does_not_leak_raw_json():
    asset = _asset(
        11,
        classification_params=_valid_classification(),
    )
    issues = []

    rows = source._build_planner_classifications([asset], issues=issues)
    dumped = [row.model_dump(mode="json") for row in rows]
    by_dimension_category = {(row["dimension"], row["category_id"]): row for row in dumped}

    assert issues == []
    assert by_dimension_category[("sector", "Financials")]["weight"] == "0.4"
    assert by_dimension_category[("sector", "Technology")]["weight"] == "0.6"
    assert by_dimension_category[("geography", "ITA")]["weight"] == "0.25"
    assert by_dimension_category[("geography", "USA")]["weight"] == "0.75"
    assert all(row["label"] == row["category_id"] for row in dumped if row["dimension"] != "asset_type")
    serialized = json.dumps(dumped)
    assert "sector_area" not in serialized
    assert "geographic_area" not in serialized
    assert "distribution" not in serialized
    repeated = source._build_planner_classifications([asset], issues=[])
    assert [row.classification_id for row in repeated] == [row.classification_id for row in rows]
    assert {row.provenance_id for row in repeated} == {"source:market-data"}


@pytest.mark.parametrize(
    ("classification_params", "expected_code", "expected_field"),
    [
        pytest.param(
            None,
            "allocation.classification_sector_missing",
            "sector",
            id="missing",
        ),
        pytest.param(
            "{",
            "allocation.classification_invalid",
            "classification_params",
            id="malformed-json",
        ),
        pytest.param(
            json.dumps(
                {
                    "sector_area": {
                        "distribution": {
                            "Technology": 0.9,
                        }
                    },
                    "geographic_area": {
                        "distribution": {
                            "USA": 1,
                        }
                    },
                }
            ),
            "allocation.classification_invalid",
            "sector",
            id="invalid-sum",
        ),
        pytest.param(
            json.dumps(
                {
                    "sector_area": {
                        "distribution": {
                            "Invented Sector": 1,
                        }
                    },
                    "geographic_area": {
                        "distribution": {
                            "USA": 1,
                        }
                    },
                }
            ),
            "allocation.classification_invalid",
            "sector",
            id="invalid-sector-key",
        ),
        pytest.param(
            json.dumps(
                {
                    "sector_area": {
                        "distribution": {
                            "Technology": 1,
                        }
                    },
                    "geographic_area": {
                        "distribution": {
                            "US": 1,
                        }
                    },
                }
            ),
            "allocation.classification_invalid",
            "geography",
            id="invalid-geography-key",
        ),
    ],
)
def test_missing_and_invalid_saved_classifications_emit_typed_placeholders(
    classification_params,
    expected_code,
    expected_field,
):
    issues = []
    rows = source._build_planner_classifications(
        [_asset(11, classification_params=classification_params)],
        issues=issues,
    )

    assert any(issue.code == expected_code and issue.path.field == expected_field for issue in issues)
    if expected_field in {"sector", "geography"}:
        placeholder = next(row for row in rows if row.dimension == expected_field and row.category_id is None)
        assert placeholder.weight is None
        assert placeholder.provenance_id == "source:market-data"


def test_currency_specs_use_cldr_quantum_for_zero_two_and_three_decimals():
    issues = []

    rows = source._build_currency_specs(
        {"JPY", "USD", "KWD"},
        issues=issues,
    )
    dumped = {row.currency: row.model_dump(mode="json")["minor_unit"] for row in rows}

    assert dumped == {
        "JPY": "1",
        "KWD": "0.001",
        "USD": "0.01",
    }
    assert issues == []


def test_validated_currency_with_no_cldr_precision_falls_back_to_two_decimals(
    monkeypatch,
):
    monkeypatch.setattr(source, "get_currency_precision", lambda _code: None)
    issues = []

    rows = source._build_currency_specs({"EUR"}, issues=issues)

    assert {row.currency: row.model_dump(mode="json")["minor_unit"] for row in rows} == {"EUR": "0.01"}
    assert issues == []


def test_currency_precision_failure_is_typed_and_never_user_defaulted(
    monkeypatch,
):
    def fail_precision(_code):
        raise ValueError("CLDR unavailable")

    monkeypatch.setattr(source, "get_currency_precision", fail_precision)
    issues = []

    rows = source._build_currency_specs({"EUR"}, issues=issues)

    assert rows == []
    assert [(issue.code, issue.kind, issue.path.entity_id, issue.path.field) for issue in issues] == [
        (
            "allocation.currency_spec_missing",
            "missing",
            "currency:EUR",
            "minor_unit",
        )
    ]
    payload = _request_payload()
    payload["currency_specs"] = [{"currency": "EUR", "minor_unit": "0.01"}]
    with pytest.raises(ValidationError):
        PortfolioPlannerSourceRequest.model_validate(payload)


@pytest.mark.asyncio
async def test_saved_fx_prefill_returns_the_direct_saved_rate_for_a_canonical_pair(
    monkeypatch,
):
    saved = _fx(on=date(2026, 9, 10), rate="1.25", source_name="MANUAL_FX")
    loader = AsyncMock(return_value={("EUR", "USD"): saved})
    monkeypatch.setattr(source, "_load_latest_planner_fx_rows", loader)
    issues = []

    rows, currencies = await source._build_planner_fx_quotes(
        object(),
        request_pairs=["EUR/USD"],
        as_of=AS_OF,
        issues=issues,
    )
    (row,) = rows
    dumped = row.model_dump(mode="json")

    assert dumped["pair"] == "EUR/USD"
    assert dumped["rate"] == "1.25"
    assert dumped["reference_date"] == "2026-09-10"
    assert dumped["source"] == "MANUAL_FX"
    assert dumped["days_before_requested"] == 5
    assert currencies == {"EUR", "USD"}
    assert issues == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("saved_rows", "expected_code"),
    [
        pytest.param({}, "allocation.saved_fx_missing", id="missing"),
        pytest.param(
            {("EUR", "JPY"): _fx(quote="JPY", rate="0")},
            "allocation.saved_fx_invalid",
            id="invalid-nonpositive",
        ),
        pytest.param(
            {
                ("EUR", "USD"): _fx(),
                ("JPY", "USD"): _fx(base="JPY", quote="USD"),
            },
            "allocation.saved_fx_missing",
            id="no-chaining",
        ),
    ],
)
async def test_saved_fx_missing_invalid_and_no_chaining_are_explicit(
    monkeypatch,
    saved_rows,
    expected_code,
):
    monkeypatch.setattr(
        source,
        "_load_latest_planner_fx_rows",
        AsyncMock(return_value=saved_rows),
    )
    issues = []

    rows, _currencies = await source._build_planner_fx_quotes(
        object(),
        request_pairs=["EUR/JPY"],
        as_of=AS_OF,
        issues=issues,
    )
    (quote,) = rows

    assert quote.rate is None
    assert quote.pair == "EUR/JPY"
    assert {issue.code for issue in issues} == {expected_code}
    (only_issue,) = issues
    (only_param,) = only_issue.params
    assert only_param.model_dump(mode="json") == {
        "kind": "text",
        "name": "pair",
        "value": "EUR/JPY",
    }


@pytest.mark.asyncio
async def test_no_fx_prefill_rows_or_database_read_when_no_pairs_requested():
    session = _QueuedReadSession()
    issues = []

    rows, currencies = await source._build_planner_fx_quotes(
        session,
        request_pairs=[],
        as_of=AS_OF,
        issues=issues,
    )

    assert rows == []
    assert currencies == set()
    assert session.statements == []
    assert issues == []


def test_canonical_runtime_wac_buy_sell_and_fresh_pool_sequence():
    result = compute_wac_from_txlist(
        [
            WACInputTX(
                tx_id=1,
                type="BUY",
                date=date(2026, 1, 1),
                quantity=Decimal("10"),
                unit_cost_converted=Decimal("100"),
                original_currency="EUR",
            ),
            WACInputTX(
                tx_id=2,
                type="BUY",
                date=date(2026, 1, 2),
                quantity=Decimal("10"),
                unit_cost_converted=Decimal("300"),
                original_currency="EUR",
            ),
            WACInputTX(
                tx_id=3,
                type="SELL",
                date=date(2026, 1, 3),
                quantity=Decimal("-5"),
                unit_cost_converted=None,
                original_currency="EUR",
            ),
            WACInputTX(
                tx_id=4,
                type="SELL",
                date=date(2026, 1, 4),
                quantity=Decimal("-15"),
                unit_cost_converted=None,
                original_currency="EUR",
            ),
            WACInputTX(
                tx_id=5,
                type="BUY",
                date=date(2026, 1, 5),
                quantity=Decimal("4"),
                unit_cost_converted=Decimal("50"),
                original_currency="EUR",
            ),
        ],
        "EUR",
    )
    by_tx = {row.tx_id: row for row in result.qualifying}

    assert by_tx[1].running_wac == Decimal("100")
    assert by_tx[2].running_wac == Decimal("200")
    assert by_tx[3].effect == "reduce"
    assert by_tx[3].running_wac == Decimal("200")
    assert by_tx[4].running_wac == Decimal("0")
    assert by_tx[5].running_wac == Decimal("50")
    assert result.pool_qty == Decimal("4")
    assert result.wac_amount == Decimal("50")


@pytest.mark.asyncio
async def test_legacy_wac_cache_default_reuses_warm_result(
    monkeypatch,
):
    transaction = SimpleNamespace(
        id=101,
        updated_at=CAPTURED_AT,
        asset_event_id=None,
        type="BUY",
        date=date(2026, 1, 2),
        quantity=Decimal("2"),
        amount=Decimal("-20"),
        currency="EUR",
        cost_basis_override=None,
        cost_basis_currency=None,
    )
    session = _QueuedReadSession(
        _Rows(scalar_values=[transaction]),
        _Rows(scalar_values=[transaction]),
    )

    class _CacheProbe:
        def __init__(self):
            self.values: dict[object, WACPreviewResultItem] = {}
            self.events: list[str] = []
            self.get_calls: list[object] = []
            self.set_calls: list[tuple[object, WACPreviewResultItem]] = []

        def get(self, key):
            self.events.append("get")
            self.get_calls.append(key)
            if key in self.values:
                return self.values[key], True
            return None, False

        def set(self, key, value):
            self.events.append("set")
            self.set_calls.append((key, value))
            self.values[key] = value

    cache = _CacheProbe()
    provider_probe = AsyncMock(side_effect=AssertionError("Same-currency WAC must not request FX"))
    monkeypatch.setattr(portfolio_service, "_wac_cache", cache)
    monkeypatch.setattr(portfolio_service, "convert_bulk", provider_probe)

    cold_result = await portfolio_service.compute_wac_iterative(
        session=session,
        broker_id=7,
        asset_id=11,
        as_of_date=AS_OF,
        asset_currency="EUR",
    )
    warm_result = await portfolio_service.compute_wac_iterative(
        session=session,
        broker_id=7,
        asset_id=11,
        as_of_date=AS_OF,
        asset_currency="EUR",
    )

    expected = WACPreviewResultItem(
        wac=Currency(code="EUR", amount=Decimal("10")),
        wac_qualifying_txs=[
            WACQualifyingTX(
                tx_id=101,
                type="BUY",
                date=date(2026, 1, 2),
                quantity=Decimal("2"),
                unit_cost=Decimal("10"),
                currency="EUR",
                effect="add",
                running_wac=Decimal("10"),
            )
        ],
        wac_missing_pairs=[],
    )
    assert cold_result == expected
    assert warm_result == expected
    assert warm_result is cold_result
    assert cache.events == ["get", "set", "get"]
    assert len(cache.get_calls) == 2
    assert len(cache.set_calls) == 1
    first_get_key, second_get_key = cache.get_calls
    set_key, set_value = cache.set_calls[0]
    assert first_get_key == second_get_key == set_key
    assert set_value is cold_result
    assert len(session.statements) == 2
    assert all(getattr(statement, "is_select", False) for statement in session.statements)
    assert session.pending_results == 0
    assert session.write_calls == []
    provider_probe.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("cache_hit", [False, True], ids=["cold", "warm"])
async def test_wac_context_does_not_read_or_mutate_process_cache(
    monkeypatch,
    cache_hit,
):
    broker = _broker(7)
    access = _access(7)
    asset = _asset(11, currency="EUR")
    transaction = SimpleNamespace(
        id=101,
        updated_at=CAPTURED_AT,
        asset_event_id=None,
        type="BUY",
        date=date(2026, 1, 2),
        quantity=Decimal("2"),
        amount=Decimal("-20"),
        currency="EUR",
        cost_basis_override=None,
        cost_basis_currency=None,
    )
    session = _QueuedReadSession(
        _Rows([(access, broker)]),
        _Rows([(7, 11, Decimal("2"))]),
        _Rows(scalar_values=[asset]),
        _Rows(scalar_values=[transaction]),
    )

    cached_wac = (
        WACPreviewResultItem(
            wac=Currency(code="EUR", amount=Decimal("9999")),
            wac_qualifying_txs=[],
            wac_missing_pairs=[],
        )
        if cache_hit
        else None
    )

    class _CacheProbe:
        def __init__(self, value, hit):
            self.value = value
            self.hit = hit
            self.get_calls: list[object] = []
            self.set_calls: list[tuple[object, object]] = []

        def get(self, key):
            self.get_calls.append(key)
            return self.value, self.hit

        def set(self, key, value):
            self.set_calls.append((key, value))

    cache = _CacheProbe(cached_wac, cache_hit)
    provider_probe = AsyncMock(side_effect=AssertionError("Same-currency WAC must not request FX"))
    monkeypatch.setattr(portfolio_service, "_wac_cache", cache)
    monkeypatch.setattr(portfolio_service, "convert_bulk", provider_probe)
    monkeypatch.setattr(source, "utcnow", lambda: CAPTURED_AT)

    response = await source.build_portfolio_planner_source(
        session,
        user_id=41,
        request=_request(
            broker_ids=[7],
            asset_ids=[11],
            requested_sections=["wac_contexts"],
            fx_pairs=[],
        ),
    )
    dumped = response.model_dump(mode="json")
    wac = next(row for row in dumped["wac_contexts"] if row["wac_id"] == "wac:asset:11:broker:7:2026-09-15:EUR")

    assert wac["unit_cost"] == "10"
    assert session.pending_results == 0
    assert session.write_calls == []
    assert all(getattr(statement, "is_select", False) for statement in session.statements)
    assert cache.get_calls == []
    assert cache.set_calls == []
    provider_probe.assert_not_awaited()


@pytest.mark.asyncio
async def test_wac_contexts_call_canonical_runtime_sequentially_and_keep_fiscal_missing(
    monkeypatch,
):
    calls: list[tuple[int, int, bool]] = []

    async def compute(**kwargs):
        calls.append(
            (
                kwargs["broker_id"],
                kwargs["asset_id"],
                kwargs["use_cache"],
            )
        )
        return WACPreviewResultItem(
            wac=Currency(
                code="EUR",
                amount=Decimal(str(kwargs["asset_id"]) + ".1250"),
            ),
            wac_qualifying_txs=[],
            wac_missing_pairs=[],
        )

    monkeypatch.setattr(portfolio_service, "compute_wac_iterative", compute)
    issues = []
    rows, currencies = await source._build_planner_wac_contexts(
        object(),
        holding_rows=[
            (8, 20, Decimal("2")),
            (7, 10, Decimal("1")),
        ],
        selected_asset_ids={10, 20},
        assets_by_id={
            10: _asset(10, currency="EUR"),
            20: _asset(20, currency="EUR"),
        },
        as_of=AS_OF,
        target_currency="EUR",
        issues=issues,
    )
    by_asset = {row.asset_id: row.model_dump(mode="json") for row in rows}

    assert calls == [(7, 10, False), (8, 20, False)]
    assert by_asset["asset:10"]["unit_cost"] == "10.1250"
    assert by_asset["asset:20"]["unit_cost"] == "20.1250"
    assert all(
        set(row)
        == {
            "wac_id",
            "holding_id",
            "asset_id",
            "broker_id",
            "method",
            "unit_cost",
            "fiscal_currency",
            "target_currency",
            "as_of",
            "fx_evidence",
            "provenance_id",
        }
        for row in by_asset.values()
    )
    assert all(row["target_currency"] == "EUR" for row in by_asset.values())
    assert all(row["fiscal_currency"] is None for row in by_asset.values())
    assert {(issue.code, issue.path.entity_id, issue.path.field) for issue in issues} == {
        (
            "allocation.fiscal_currency_missing",
            "wac:asset:10:broker:7:2026-09-15:EUR",
            "fiscal_currency",
        ),
        (
            "allocation.fiscal_currency_missing",
            "wac:asset:20:broker:8:2026-09-15:EUR",
            "fiscal_currency",
        ),
    }
    assert currencies == {"EUR"}


def _converted_wac_result(*, rate: str = "0.8") -> WACPreviewResultItem:
    shared = {
        "type": "BUY",
        "quantity": Decimal("2"),
        "unit_cost": Decimal("80"),
        "currency": "EUR",
        "effect": "add",
        "running_wac": Decimal("80.0000"),
        "original_unit_cost": Decimal("100"),
        "original_currency": "USD",
        "fx_rate_used": Decimal(rate),
        "fx_info": FxBackwardFillInfo(
            fx_rate_date=date(2026, 1, 1),
            fx_days_back=2,
        ),
    }
    return WACPreviewResultItem(
        wac=Currency(code="EUR", amount=Decimal("80.0000")),
        wac_qualifying_txs=[
            WACQualifyingTX(
                tx_id=1,
                date=date(2026, 1, 3),
                **shared,
            ),
            WACQualifyingTX(
                tx_id=2,
                date=date(2026, 1, 4),
                **shared,
            ),
        ],
        wac_missing_pairs=[],
    )


@pytest.mark.asyncio
async def test_wac_fx_evidence_is_exact_deterministic_and_deduplicated(
    monkeypatch,
):
    result = _converted_wac_result()
    monkeypatch.setattr(
        portfolio_service,
        "compute_wac_iterative",
        AsyncMock(return_value=result),
    )
    saved = _fx(
        on=date(2026, 1, 1),
        rate="1.25",
        source_name="MANUAL_WAC_FX",
    )
    monkeypatch.setattr(
        source,
        "_load_current_wac_fx_rows",
        AsyncMock(
            return_value={
                ("EUR", "USD", date(2026, 1, 3)): saved,
                ("EUR", "USD", date(2026, 1, 4)): saved,
            }
        ),
    )
    issues = []

    rows, currencies = await source._build_planner_wac_contexts(
        object(),
        holding_rows=[(7, 11, Decimal("4"))],
        selected_asset_ids={11},
        assets_by_id={11: _asset(11, currency="USD")},
        as_of=AS_OF,
        target_currency="EUR",
        issues=issues,
    )
    row = next(row for row in rows if row.asset_id == "asset:11")
    dumped = row.model_dump(mode="json")

    assert dumped["unit_cost"] == "80.0000"
    assert dumped["fx_evidence"] == [
        {
            "source_currency": "USD",
            "destination_currency": "EUR",
            "rate": "0.8",
            "reference_date": "2026-01-01",
            "source": "MANUAL_WAC_FX",
            "inverted": True,
            "status": "available",
        }
    ]
    assert {issue.code for issue in issues} == {
        "allocation.fiscal_currency_missing",
    }
    assert currencies == {"EUR", "USD"}


@pytest.mark.asyncio
async def test_wac_fx_revalidation_loads_latest_saved_row_per_transaction_cutoff():
    old = _fx(
        on=date(2026, 1, 1),
        rate="1.25",
        source_name="OLD",
    )
    replacement = _fx(
        on=date(2026, 1, 2),
        rate="1.20",
        source_name="REPLACEMENT",
    )
    future = _fx(
        on=date(2026, 1, 5),
        rate="1.10",
        source_name="FUTURE",
    )
    session = _QueuedReadSession(
        _Rows(scalar_values=[old, future, replacement]),
    )

    rows = await source._load_current_wac_fx_rows(
        session,
        windows={
            (
                "EUR",
                "USD",
                date(2026, 1, 1),
                date(2026, 1, 3),
            )
        },
    )

    assert rows == {
        ("EUR", "USD", date(2026, 1, 3)): replacement,
    }
    (only_statement,) = session.statements
    sql = str(only_statement)
    assert "fx_rates.date >=" in sql
    assert "fx_rates.date <=" in sql


@pytest.mark.asyncio
async def test_warm_wac_result_with_changed_saved_fx_fails_closed(
    monkeypatch,
):
    stale_cached_result = _converted_wac_result()
    compute = AsyncMock(return_value=stale_cached_result)
    monkeypatch.setattr(
        portfolio_service,
        "compute_wac_iterative",
        compute,
    )
    changed = _fx(
        on=date(2026, 1, 1),
        rate="1.20",
        source_name="CHANGED_AFTER_CACHE",
    )
    monkeypatch.setattr(
        source,
        "_load_current_wac_fx_rows",
        AsyncMock(
            return_value={
                ("EUR", "USD", date(2026, 1, 3)): changed,
                ("EUR", "USD", date(2026, 1, 4)): changed,
            }
        ),
    )
    issues = []

    rows, _currencies = await source._build_planner_wac_contexts(
        object(),
        holding_rows=[(7, 11, Decimal("4"))],
        selected_asset_ids={11},
        assets_by_id={11: _asset(11, currency="USD")},
        as_of=AS_OF,
        target_currency="EUR",
        issues=issues,
    )
    row = next(row for row in rows if row.asset_id == "asset:11")

    assert row.unit_cost is None
    assert [evidence.model_dump(mode="json") for evidence in row.fx_evidence] == [
        {
            "source_currency": "USD",
            "destination_currency": "EUR",
            "rate": None,
            "reference_date": None,
            "source": None,
            "inverted": True,
            "status": "missing",
        }
    ]
    assert {issue.code for issue in issues} == {
        "allocation.fiscal_currency_missing",
        "allocation.wac_fx_missing",
    }
    compute.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_saved_domain_copy_is_select_only_private_and_stable(
    monkeypatch,
):
    broker = _broker(7, name="Private Broker Name")
    access = _access(7, share="0.125000")
    asset = _asset(
        11,
        name="Private Asset Name",
        currency="USD",
        quote_base_quantity=100,
        classification_params=_valid_classification(),
    )
    price = _price(
        11,
        close="123.4500",
        currency="USD",
        source_name="SAVED_PRICE",
    )
    fx = _fx(
        rate="1.25",
        source_name="SAVED_FX",
    )
    session = _QueuedReadSession(
        _Rows([(access, broker)]),
        _Rows([(7, 11, Decimal("2.5000"))]),
        _Rows(scalar_values=[asset]),
        _Rows([(7, "EUR", Decimal("9.8700"))]),
        _Rows(scalar_values=[price]),
        _Rows(scalar_values=[fx]),
    )
    usage_probe = AsyncMock(side_effect=AssertionError("New source must not read cross-user usage"))
    monkeypatch.setattr(source, "_load_usage_counts", usage_probe)
    monkeypatch.setattr(source, "utcnow", lambda: CAPTURED_AT)

    class _ForbiddenCache:
        def get(self, _key):
            raise AssertionError("Planner source must not read a response cache")

        def set(self, _key, _value):
            raise AssertionError("Planner source must not mutate a response cache")

    monkeypatch.setattr(portfolio_service, "_wac_cache", _ForbiddenCache())

    response = await source.build_portfolio_planner_source(
        session,
        user_id=41,
        request=_request(
            broker_ids=[7],
            asset_ids=[11],
            requested_sections=[
                "assets",
                "brokers",
                "holdings",
                "cash_balances",
                "prices",
                "classifications",
                "fx_quotes",
            ],
            fx_pairs=["EUR/USD"],
        ),
    )
    dumped = response.model_dump(mode="json")

    assert set(dumped) == {
        "snapshot",
        "currency_specs",
        "provenance",
        "assets",
        "brokers",
        "holdings",
        "cash_balances",
        "prices",
        "classifications",
        "wac_contexts",
        "fx_quotes",
        "issues",
    }
    assert session.pending_results == 0
    assert session.write_calls == []
    assert all(getattr(statement, "is_select", False) for statement in session.statements)
    fx_statement = next(statement for statement in session.statements if "FROM fx_rates" in str(statement))
    fx_sql = str(fx_statement)
    assert "max(fx_rates.date)" in fx_sql
    assert "fx_rates.date <=" in fx_sql
    usage_probe.assert_not_awaited()
    assert dumped["snapshot"] == {
        "as_of": "2026-09-15",
        "target_currency": "EUR",
        "generated_at": "2026-09-15T12:30:00Z",
        "requested_sections": [
            "assets",
            "brokers",
            "holdings",
            "cash_balances",
            "prices",
            "classifications",
            "fx_quotes",
        ],
        "source_revision": "2.0.0",
    }
    assert [row["provenance_id"] for row in dumped["provenance"]] == [
        "source:portfolio-ledger",
        "source:market-data",
        "source:broker-domain",
        "source:saved-fx",
    ]
    assert all(row["captured_at"] == dumped["snapshot"]["generated_at"] for row in dumped["provenance"])
    holding = next(row for row in dumped["holdings"] if row["holding_id"] == "holding:asset:11:broker:7")
    cash = next(row for row in dumped["cash_balances"] if row["cash_id"] == "cash:broker:7:EUR")
    saved_price = next(row for row in dumped["prices"] if row["asset_id"] == "asset:11")
    copied_asset = next(row for row in dumped["assets"] if row["asset_id"] == "asset:11")
    assert holding["custody_quantity"] == "2.5000"
    assert holding["economic_quantity"] == "0.3125000000"
    assert cash["custody_amount"] == "9.8700"
    assert cash["economic_amount"] == "1.2337500000"
    assert saved_price["amount"] == "123.4500"
    assert "usage_scope" not in copied_asset
    assert "user_id" not in json.dumps(dumped)

    private_metadata_json = json.dumps(
        {
            "issues": dumped["issues"],
            "provenance": dumped["provenance"],
        }
    )
    for private_value in (
        "Private Broker Name",
        "Private Asset Name",
        "123.4500",
        "9.8700",
        "2.5000",
        "0.125000",
    ):
        assert private_value not in private_metadata_json
