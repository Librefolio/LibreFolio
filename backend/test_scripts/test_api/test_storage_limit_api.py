"""The space limit, applied, through the lane's server (release 1.3, lot C8).

``storage_limit_mb`` was only drawn on the space bar; now it stops what adds data (``services/platform/storage_limit.py``,
which has its own suite, ``services storage-limit``). Here the routes, as a client meets them. The limit is set to 1 MB,
which the lane's data directory (its database alone) already passes, so every addition is past it; 0 puts it away.

- SLIM-001, with the limit on: ``POST /uploads`` answers 507 with the ``storage_limit_exceeded`` detail (``required_mb``
  above the 1 MB limit, the numbers of the space) and nothing is stored; ``POST /brokers/import/upload`` answers the same
  for a broker report; ``POST /backup/instance`` (a backup started by hand) answers it too and starts nothing.
- SLIM-002, with no limit (0): the same upload and report are accepted, and removed.
- SLIM-003, transactions are never stopped: with the limit on, a broker can still be created and deleted.

Exclusive: it rewrites ``global_settings.storage_limit_mb``, one value for the whole instance; while it is 1 MB every
concurrent upload or backup of another unit would be refused. The original value is put back in a ``finally``.
"""

from __future__ import annotations

import io
import uuid

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_api.test_settings_api import get_admin_session
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
KEY = "storage_limit_mb"
DETAIL_KEYS = {"code", "message", "limit_mb", "used_bytes", "required_bytes", "required_mb", "disk_missing_bytes"}


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the tests of this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def read_limit(client: httpx.AsyncClient) -> str | None:
    response = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
    assert response.status_code == 200, f"the global settings: {response.status_code} {response.text[:300]}"
    return next((item["value"] for item in response.json()["items"] if item["key"] == KEY), None)


async def set_limit(client: httpx.AsyncClient, value: str) -> None:
    response = await client.patch(f"{API_BASE}/settings/global/bulk", json={"items": [{"key": KEY, "value": value}]}, timeout=TIMEOUT)
    assert response.status_code == 200, f"storage_limit_mb={value}: {response.status_code} {response.text[:300]}"


def assert_refusal(response: httpx.Response, what: str) -> dict:
    assert response.status_code == 507, f"{what}: 507, not {response.status_code} {response.text[:300]}"
    detail = response.json()["detail"]
    assert set(detail) == DETAIL_KEYS, f"{what}: the detail has exactly {sorted(DETAIL_KEYS)}, got {sorted(detail)}"
    assert detail["code"] == "storage_limit_exceeded"
    assert detail["limit_mb"] == 1
    assert detail["required_mb"] > 1, f"{what}: it names a limit above the 1 MB it passes: {detail}"
    assert detail["required_bytes"] > detail["used_bytes"] > 0
    return detail


async def new_broker(client: httpx.AsyncClient) -> int:
    response = await client.post(f"{API_BASE}/brokers", json=[{"name": f"SLIM_{uuid.uuid4().hex[:8]}", "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert response.status_code == 200, f"a broker is created: {response.status_code} {response.text[:300]}"
    return response.json()["results"][0]["broker_id"]


async def drop_broker(client: httpx.AsyncClient, broker_id: int) -> None:
    await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_with_the_limit_on_additions_are_refused_with_the_numbers(test_server):
    """SLIM-001: an upload, a broker report and a backup by hand are 507 ``storage_limit_exceeded``; nothing is stored."""
    print_section("SLIM-001: the limit on, additions refused")
    async with httpx.AsyncClient() as client:
        await get_admin_session(client)
        original = await read_limit(client)
        broker_id = None
        try:
            broker_id = await new_broker(client)
            await set_limit(client, "1")

            upload = await client.post(f"{API_BASE}/uploads", files={"file": ("slim.txt", io.BytesIO(b"hello"), "text/plain")}, timeout=TIMEOUT)
            assert_refusal(upload, "an uploaded file")

            report = await client.post(f"{API_BASE}/brokers/import/upload", files={"file": ("slim.csv", io.BytesIO(b"date,type\n"), "text/csv")}, data={"broker_id": broker_id}, timeout=TIMEOUT)
            assert_refusal(report, "a broker report")

            backup = await client.post(f"{API_BASE}/backup/instance", timeout=TIMEOUT)
            assert_refusal(backup, "a backup started by hand")
            running = await client.get(f"{API_BASE}/backup/instance/jobs", timeout=TIMEOUT)
            assert running.status_code == 200
        finally:
            if original is not None:
                await set_limit(client, original)
            if broker_id is not None:
                await drop_broker(client, broker_id)
        assert await read_limit(client) == original, "the original limit is back"
    print_success("507 storage_limit_exceeded with the numbers, for a file, a report and a backup")


@pytest.mark.asyncio
async def test_with_no_limit_the_same_additions_are_accepted(test_server):
    """SLIM-002 and SLIM-003: with 0 they pass (and are removed); and a broker is created and deleted with the limit on."""
    print_section("SLIM-002: no limit, additions accepted; SLIM-003: transactions never stopped")
    async with httpx.AsyncClient() as client:
        await get_admin_session(client)
        original = await read_limit(client)
        broker_id = None
        try:
            await set_limit(client, "0")
            upload = await client.post(f"{API_BASE}/uploads", files={"file": ("slim.txt", io.BytesIO(b"hello"), "text/plain")}, timeout=TIMEOUT)
            assert upload.status_code == 200, f"no limit: the upload is accepted: {upload.status_code} {upload.text[:300]}"
            file_id = upload.json()["file"]["id"]
            await client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            await set_limit(client, "1")
            broker_id = await new_broker(client)
        finally:
            if original is not None:
                await set_limit(client, original)
            if broker_id is not None:
                await drop_broker(client, broker_id)
    print_success("no limit: accepted; the limit on: a broker is still created")
