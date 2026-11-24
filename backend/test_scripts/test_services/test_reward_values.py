"""79 STK-4b — the value on receipt of a reward in kind, read from the stored price history.

``services/assets/reward_values.py`` is the one reader behind the transaction form's suggestion (STK-2a) and the bulk
workspace's «fill from price history» (STK-4b), served by ``POST /assets/prices/reward-values``. The domain rule pinned
here:

- ``reward_unit_value_from_close(close, quote_base_quantity)``: the close over the quote base
  (``financial_math.valuation.compute_holding_value(1, close, base)``; a base of None, 0 or below is 1), rounded to what
  ``Transaction.cost_basis_override`` keeps (RealDecimal(24, 12): 12 decimals, 15 significant digits, half-even), the
  form of a value that already fits kept; None for a close that is None, not finite, 0 or negative — no price is never a
  value of 0.
- ``reward_values_on_receipt(session, items)``: per item, in the order asked (a repeated item answered twice), the close
  of THAT day only — never the day before or after —, per unit, in the price row's own currency. ``NO_HISTORY`` when the
  asset does not exist or has no stored price at all; ``NO_PRICE_THAT_DAY`` when it has a history but no usable close
  that day (no row, or a row whose close is missing or not positive); ``FILLED`` with the value otherwise.
- The route refuses more than ``MAX_BULK_ITEMS`` (1 000) items with 422 ``bulk_too_many_items``; exactly 1 000 pass.

Two ways in. The SERVICE runs on a private in-memory SQLite database (``SQLModel.metadata.create_all``), its rows written
by the ORM — which also lets a close of 0 or None be stored on a day, a state the upsert route refuses. The ROUTE is
mounted on a fresh ``FastAPI`` app of the test's own, served in this process by ``httpx.ASGITransport`` (no server, no
port), its session the private one and its user dependency overridden.

Isolation: PURE — no lane database, no server, no network. Every engine is disposed at teardown.
The same contract through the real server is ``test_api/test_reward_values_api.py``.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.api.v1.assets import prices
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetType, PriceHistory
from backend.app.schemas.prices import FARewardValueItem, FARewardValueResult, RewardValueStatus
from backend.app.services.assets.reward_values import reward_unit_value_from_close, reward_values_on_receipt

# The contract's numbers, written here and not read from the code under test
BULK_MAX_ITEMS = 1_000

D1 = date(2024, 3, 4)  # a close
D2 = date(2024, 3, 5)  # no close: the gap between two closes
D3 = date(2024, 3, 6)  # a close
FAR_AWAY_ASSET_ID = 987_654_321  # an id no row of the private database carries


# =============================================================================
# A. THE PURE RULE: reward_unit_value_from_close
# =============================================================================


class TestRewardUnitValueFromClose:
    """The value of one unit from a day's close: close ÷ quote base, rounded to the cost-basis column."""

    @pytest.mark.parametrize(
        ("close", "base", "expected"),
        [
            pytest.param("61.25", 1, "61.25", id="base-1-the-close-itself"),
            pytest.param("98.5", 100, "0.985", id="base-100-a-bond-per-100"),
            pytest.param("101.25", 100, "1.0125", id="base-100-above-par"),
            pytest.param("100", 3, "33.333333333333", id="rounded-to-12-decimals"),
            pytest.param("5", 3, "1.666666666667", id="rounded-half-even-up-at-12-decimals"),
            pytest.param("123456789.123456789", 1, "123456789.123457", id="capped-at-15-significant-digits"),
            pytest.param("0.000000000001", 1, "0.000000000001", id="the-smallest-value-the-column-keeps"),
            pytest.param("98.5", None, "98.5", id="no-base-is-base-1"),
            pytest.param("98.5", 0, "98.5", id="base-0-is-base-1"),
            pytest.param("98.5", -100, "98.5", id="negative-base-is-base-1"),
        ],
    )
    def test_value_per_unit(self, close: str, base: Optional[int], expected: str):
        value = reward_unit_value_from_close(Decimal(close), base)
        assert value is not None, f"close {close} base {base}: expected {expected}, got None"
        assert value == Decimal(expected), f"close {close} base {base}: expected {expected}, got {value}"

    def test_the_form_of_a_close_that_fits_is_kept(self):
        """At base 1 the close comes back as stored: 61.250000 stays 61.250000 (the form shows it as the history holds it)."""
        assert str(reward_unit_value_from_close(Decimal("61.250000"), 1)) == "61.250000"

    @pytest.mark.parametrize(
        "close",
        [
            pytest.param(None, id="no-close"),
            pytest.param("0", id="zero"),
            pytest.param("0.000000", id="zero-with-decimals"),
            pytest.param("-3", id="negative"),
            pytest.param("NaN", id="not-a-number"),
            pytest.param("Infinity", id="infinite"),
            pytest.param("-Infinity", id="minus-infinite"),
        ],
    )
    @pytest.mark.parametrize("base", [1, 100])
    def test_no_value_without_a_positive_close(self, close: Optional[str], base: int):
        """No price is never a value of 0 the history does not hold."""
        assert reward_unit_value_from_close(None if close is None else Decimal(close), base) is None


# =============================================================================
# B. THE READER: reward_values_on_receipt on a private database
# =============================================================================


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """This test's own in-memory database with the ORM schema: never the lane's database. Disposed on the way out."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as private_session:
            yield private_session
    finally:
        await engine.dispose()


async def _asset(session: AsyncSession, label: str, *, currency: str = "EUR", quote_base: Optional[int] = 1) -> int:
    asset = Asset(display_name=f"STK-4b {label} {uuid.uuid4().hex[:6]}", currency=currency, asset_type=AssetType.STOCK, quote_base_quantity=quote_base)
    session.add(asset)
    await session.commit()
    return asset.id


async def _closes(session: AsyncSession, asset_id: int, closes: dict[date, Optional[str]], currency: str = "EUR") -> None:
    """Rows of the price history, written by the ORM: a close of None or 0 is stored as given."""
    for day, close in closes.items():
        session.add(PriceHistory(asset_id=asset_id, date=day, close=None if close is None else Decimal(close), currency=currency, source_plugin_key="stk4b_test"))
    await session.commit()


def _items(*pairs: tuple[int, date]) -> list[FARewardValueItem]:
    return [FARewardValueItem(asset_id=asset_id, date=day) for asset_id, day in pairs]


def _shape(results: list[FARewardValueResult]) -> list[tuple]:
    """``(asset_id, date, status, value code, value amount)`` of every result, in order."""
    return [(r.asset_id, r.date, r.status, r.value.code if r.value else None, r.value.amount if r.value else None) for r in results]


@pytest.mark.asyncio
class TestRewardValuesOnReceipt:
    async def test_the_close_of_that_very_day_per_unit_in_its_currency(self, session: AsyncSession):
        asset_id = await _asset(session, "filled")
        await _closes(session, asset_id, {D1: "61.25", D3: "70"})

        (result,) = await reward_values_on_receipt(session, _items((asset_id, D1)))

        assert result.status == RewardValueStatus.FILLED
        assert result.value is not None and (result.value.code, result.value.amount) == ("EUR", Decimal("61.25")), result.value

    async def test_a_gap_day_is_no_price_never_the_day_before_or_after(self, session: AsyncSession):
        """D2 lies between two closes: a backward fill would answer D1's 61.25, a forward fill D3's 70. Neither may."""
        asset_id = await _asset(session, "gap")
        await _closes(session, asset_id, {D1: "61.25", D3: "70"})

        results = await reward_values_on_receipt(session, _items((asset_id, D1), (asset_id, D2), (asset_id, D3)))

        assert _shape(results) == [
            (asset_id, D1, RewardValueStatus.FILLED, "EUR", Decimal("61.25")),
            (asset_id, D2, RewardValueStatus.NO_PRICE_THAT_DAY, None, None),
            (asset_id, D3, RewardValueStatus.FILLED, "EUR", Decimal("70")),
        ], "the day before (D1) and after (D3) have a close, and still D2 has none"

    @pytest.mark.parametrize("close", [None, "0", "-1"], ids=["no-close", "close-0", "negative-close"])
    async def test_a_row_without_a_positive_close_is_no_price_that_day(self, session: AsyncSession, close: Optional[str]):
        """A row on the day whose close is missing or not positive: the day has no price, the asset still has a history."""
        asset_id = await _asset(session, "unusable")
        await _closes(session, asset_id, {D1: "61.25", D2: close})

        (result,) = await reward_values_on_receipt(session, _items((asset_id, D2)))

        assert (result.status, result.value) == (RewardValueStatus.NO_PRICE_THAT_DAY, None)

    async def test_an_asset_without_any_stored_price_is_no_history(self, session: AsyncSession):
        asset_id = await _asset(session, "no history")

        (result,) = await reward_values_on_receipt(session, _items((asset_id, D1)))

        assert (result.asset_id, result.date, result.status, result.value) == (asset_id, D1, RewardValueStatus.NO_HISTORY, None)

    async def test_an_unknown_asset_is_no_history(self, session: AsyncSession):
        (result,) = await reward_values_on_receipt(session, _items((FAR_AWAY_ASSET_ID, D1)))

        assert (result.asset_id, result.date, result.status, result.value) == (FAR_AWAY_ASSET_ID, D1, RewardValueStatus.NO_HISTORY, None)

    async def test_the_quote_base_divides_the_close(self, session: AsyncSession):
        bond_id = await _asset(session, "bond", quote_base=100)
        await _closes(session, bond_id, {D1: "98.5"})

        (result,) = await reward_values_on_receipt(session, _items((bond_id, D1)))

        assert result.status == RewardValueStatus.FILLED
        assert result.value is not None and result.value.amount == Decimal("0.985"), f"98.5 per 100 is 0.985 per unit: {result.value}"

    async def test_the_currency_is_the_price_rows_never_the_assets(self, session: AsyncSession):
        """Never converted: a row stored in USD on a EUR asset (written by the ORM; the upsert route refuses it) gives USD."""
        asset_id = await _asset(session, "currency", currency="EUR")
        await _closes(session, asset_id, {D1: "12.5"}, currency="USD")

        (result,) = await reward_values_on_receipt(session, _items((asset_id, D1)))

        assert result.value is not None and (result.value.code, result.value.amount) == ("USD", Decimal("12.5")), result.value

    async def test_results_in_the_order_asked_a_repeated_item_answered_twice(self, session: AsyncSession):
        priced = await _asset(session, "order priced")
        bond = await _asset(session, "order bond", quote_base=100)
        empty = await _asset(session, "order empty")
        await _closes(session, priced, {D1: "10", D3: "30"})
        await _closes(session, bond, {D2: "99"})

        asked = _items((empty, D1), (priced, D3), (FAR_AWAY_ASSET_ID, D2), (bond, D2), (priced, D2), (priced, D3), (bond, D1))
        results = await reward_values_on_receipt(session, asked)

        assert _shape(results) == [
            (empty, D1, RewardValueStatus.NO_HISTORY, None, None),
            (priced, D3, RewardValueStatus.FILLED, "EUR", Decimal("30")),
            (FAR_AWAY_ASSET_ID, D2, RewardValueStatus.NO_HISTORY, None, None),
            (bond, D2, RewardValueStatus.FILLED, "EUR", Decimal("0.99")),
            (priced, D2, RewardValueStatus.NO_PRICE_THAT_DAY, None, None),
            (priced, D3, RewardValueStatus.FILLED, "EUR", Decimal("30")),
            (bond, D1, RewardValueStatus.NO_PRICE_THAT_DAY, None, None),
        ]

    async def test_no_item_no_result(self, session: AsyncSession):
        assert await reward_values_on_receipt(session, []) == []

    async def test_a_day_far_from_the_history_is_no_price(self, session: AsyncSession):
        """Guard: a reward ten years after the last close is not valued at that close."""
        asset_id = await _asset(session, "far day")
        await _closes(session, asset_id, {D1: "61.25"})

        (result,) = await reward_values_on_receipt(session, _items((asset_id, D1 + timedelta(days=3650))))

        assert result.status == RewardValueStatus.NO_PRICE_THAT_DAY


# =============================================================================
# C. THE ROUTE: the item cap, through an app of the test's own
# =============================================================================


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    """A client of a fresh app holding the price router under ``/api/v1/assets``, served in this process: signed in, its
    session the private database. The process's app is never touched."""
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.include_router(prices.price_router, prefix="/api/v1/assets")
    app.dependency_overrides[prices.get_session_generator] = lambda: session
    app.dependency_overrides[prices.get_current_user] = lambda: None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://stk4b.test") as http:
        yield http


def _body(count: int, asset_id: int = FAR_AWAY_ASSET_ID) -> list[dict]:
    return [{"asset_id": asset_id, "date": D1.isoformat()} for _ in range(count)]


@pytest.mark.asyncio
class TestRewardValuesRoute:
    async def test_more_than_1000_items_refused(self, client: httpx.AsyncClient):
        resp = await client.post("/api/v1/assets/prices/reward-values", json=_body(BULK_MAX_ITEMS + 1))

        assert resp.status_code == 422, f"{resp.status_code}: {resp.text[:300]}"
        detail = resp.json()["detail"]
        assert isinstance(detail, dict) and detail.get("code") == "bulk_too_many_items", detail
        assert isinstance(detail.get("message"), str) and detail["message"].strip(), detail
        assert {key: value for key, value in detail.items() if key not in ("code", "message")} == {"max_items": BULK_MAX_ITEMS, "items": BULK_MAX_ITEMS + 1}

    async def test_exactly_1000_items_pass(self, client: httpx.AsyncClient):
        resp = await client.post("/api/v1/assets/prices/reward-values", json=_body(BULK_MAX_ITEMS))

        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
        items = resp.json()["items"]
        assert len(items) == BULK_MAX_ITEMS, "one result per item asked"
        assert {(item["asset_id"], item["status"], item["value"]) for item in items} == {(FAR_AWAY_ASSET_ID, "NO_HISTORY", None)}

    async def test_the_answer_shape(self, client: httpx.AsyncClient, session: AsyncSession):
        asset_id = await _asset(session, "route")
        await _closes(session, asset_id, {D1: "61.25"})

        resp = await client.post("/api/v1/assets/prices/reward-values", json=[{"asset_id": asset_id, "date": D1.isoformat()}, {"asset_id": asset_id, "date": D2.isoformat()}])

        assert resp.status_code == 200, resp.text
        first, second = resp.json()["items"]
        assert (first["asset_id"], first["date"], first["status"], first["value"]["code"]) == (asset_id, D1.isoformat(), "FILLED", "EUR")
        assert Decimal(str(first["value"]["amount"])) == Decimal("61.25")
        assert (second["asset_id"], second["date"], second["status"], second["value"]) == (asset_id, D2.isoformat(), "NO_PRICE_THAT_DAY", None)

    async def test_an_unknown_field_is_refused(self, client: httpx.AsyncClient):
        """The items are strict: a misspelled key is a 422, never an item read without it."""
        resp = await client.post("/api/v1/assets/prices/reward-values", json=[{"asset_id": 1, "date": D1.isoformat(), "quote_base": 100}])

        assert resp.status_code == 422, f"{resp.status_code}: {resp.text[:300]}"
