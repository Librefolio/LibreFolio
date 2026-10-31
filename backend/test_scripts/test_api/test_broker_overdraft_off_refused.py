"""
Broker settings: turning the overdraft flag OFF on a broker whose cash already went below zero (W6-12 observation).

``PATCH /brokers/{id}`` -> ``BrokerService.update_bulk`` sets ``broker.allow_cash_overdraft = False`` in the session and
THEN calls ``_validate_broker_balances(broker_id, None)``; on a ``BalanceValidationError`` it answers ``success=False``
and ``continue``s. The question is whether the flag stays False in the database after the refused update.

Observed (guard, green today): it does NOT. The service leaves the flag False in its session, but the endpoint
(``api/v1/brokers.py::update_broker``) rolls the session back unless the update succeeded, so the stored broker is
unchanged and a read-back still says ``allow_cash_overdraft == True``. The correctness of the refusal rests on that
rollback of the caller, not on the service (a caller that committed after a refused item would persist the flag).

Reference: backend/app/api/v1/brokers.py (update_broker), backend/app/services/brokers/broker_service.py (update_bulk).
"""

import uuid
from datetime import date

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


def _uid() -> str:
    return f"od_{uuid.uuid4().hex[:8]}"


async def _login(client: httpx.AsyncClient) -> None:
    username = _uid()
    pwd = "TestPass123!"
    r = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": pwd}, timeout=TIMEOUT)
    assert r.status_code == 201, r.text
    r = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": pwd}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text


async def _broker_with_negative_cash(client: httpx.AsyncClient, *, overdraft: bool = True) -> int:
    """A broker of this test that allows the overdraft and holds a WITHDRAWAL of 100 EUR from a zero cash: its cash is -100 EUR."""
    r = await client.post(f"{API_BASE}/brokers", json=[{"name": f"OdBroker_{_uid()}", "allow_cash_overdraft": overdraft, "allow_asset_shorting": False}], timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    broker_id = r.json()["results"][0]["broker_id"]
    r = await client.post(
        f"{API_BASE}/transactions/commit",
        json={"creates": [{"broker_id": broker_id, "type": "WITHDRAWAL", "date": str(date.today()), "quantity": "0", "cash": {"code": "EUR", "amount": "-100"}}]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    assert r.json()["committed"] is True, f"scaffold: the overdraft broker must accept the withdrawal: {r.json()}"
    return broker_id


async def _read_broker(client: httpx.AsyncClient, broker_id: int) -> dict:
    r = await client.get(f"{API_BASE}/brokers/{broker_id}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as mgr:
        if not mgr.start_server():
            pytest.fail("Failed to start test server")
        yield mgr


@pytest.mark.asyncio
class TestOverdraftFlagOffRefused:
    @pytest.fixture(autouse=True)
    def _server(self, test_server):
        yield

    async def test_a_refused_flag_off_leaves_the_stored_flag_on(self):
        """Guard: cash -100 EUR under an overdraft broker; ``allow_cash_overdraft: false`` is refused (success False, validation
        triggered) and the broker read back still allows the overdraft."""
        print_section("Broker PATCH: overdraft OFF on a negative cash is refused and not stored")
        async with httpx.AsyncClient() as client:
            await _login(client)
            broker_id = await _broker_with_negative_cash(client)
            assert (await _read_broker(client, broker_id))["allow_cash_overdraft"] is True, "scaffold: the broker starts with the overdraft allowed"

            r = await client.patch(f"{API_BASE}/brokers/{broker_id}", json={"allow_cash_overdraft": False}, timeout=TIMEOUT)

            assert r.status_code == 200, r.text
            result = r.json()["results"][0]
            assert result["id"] == broker_id
            assert result["success"] is False, f"the flag cannot go off over a -100 EUR cash: {result}"
            assert result["validation_triggered"] is True, result
            assert r.json()["success_count"] == 0

            stored = await _read_broker(client, broker_id)
            assert stored["allow_cash_overdraft"] is True, f"the refused update must not leave the flag off in the database: {stored}"
            print_success("refused, and the stored flag is still True")

    async def test_a_refused_flag_off_does_not_store_the_other_fields_of_the_same_update(self):
        """Guard: the whole refused update is rolled back, a rename sent with it included."""
        async with httpx.AsyncClient() as client:
            await _login(client)
            broker_id = await _broker_with_negative_cash(client)
            before = await _read_broker(client, broker_id)
            renamed = f"OdRenamed_{_uid()}"

            r = await client.patch(f"{API_BASE}/brokers/{broker_id}", json={"name": renamed, "allow_cash_overdraft": False}, timeout=TIMEOUT)

            assert r.status_code == 200, r.text
            assert r.json()["results"][0]["success"] is False
            after = await _read_broker(client, broker_id)
            assert after["name"] == before["name"], f"the rename of a refused update must not be stored: {after['name']!r}"
            assert after["allow_cash_overdraft"] is True

    async def test_the_flag_off_is_accepted_when_the_cash_is_not_negative(self):
        """Guard: the counterpart, so the refusal above is the balance and not the PATCH: a broker with positive cash goes to
        overdraft off and the stored flag follows."""
        async with httpx.AsyncClient() as client:
            await _login(client)
            r = await client.post(f"{API_BASE}/brokers", json=[{"name": f"OdBroker_{_uid()}", "allow_cash_overdraft": True}], timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            broker_id = r.json()["results"][0]["broker_id"]
            r = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"creates": [{"broker_id": broker_id, "type": "DEPOSIT", "date": str(date.today()), "quantity": "0", "cash": {"code": "EUR", "amount": "100"}}]},
                timeout=TIMEOUT,
            )
            assert r.status_code == 200 and r.json()["committed"] is True, r.text

            r = await client.patch(f"{API_BASE}/brokers/{broker_id}", json={"allow_cash_overdraft": False}, timeout=TIMEOUT)

            assert r.status_code == 200, r.text
            assert r.json()["results"][0]["success"] is True
            assert (await _read_broker(client, broker_id))["allow_cash_overdraft"] is False
