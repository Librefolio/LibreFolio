"""
The two global settings of the backups' cleanup (lot FB-24 backend, interface §4), through the lane's real API:
``backup_cleanup_max_mb`` and ``backup_cleanup_max_days`` in ``GET /settings/global`` and ``PATCH /settings/global/bulk``.

- CLEAN-001, the keys exist and are off: both are in the list an administrator reads, type ``int``, value ``0`` on a
  self-hosted lane (0 = no cleanup). Red today: neither key exists.
- CLEAN-002, the range: ``backup_cleanup_max_mb`` takes ``0..1048576`` and ``backup_cleanup_max_days`` ``0..3650``, the
  edges included; one past an edge, a negative number or a text that is no integer is refused with 422 whose detail
  names the key, and the bulk is all or nothing (an accepted item beside a refused one is not saved). Red today: the
  keys are unknown (404).

The managed profile (effective defaults 250 MB and 30 days, the refusal of ``max_mb = 0``) is the service suite's
(``services``), not repeated here.

Isolation. The two rows are global (one value for the whole instance, whoever reads them), so the unit declares why it is
exclusive in the catalogue. Each test reads the original values first and restores them in a ``finally``, through the
same API, tolerating the keys being absent (which is the red of today and must not hide it behind a second error). The
values written are never small enough to make a concurrent backup delete anything (the cleanup keeps the newest backup
and, here, at most the edge values).
"""

from __future__ import annotations

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_api.test_settings_api import get_admin_session
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

MAX_MB = "backup_cleanup_max_mb"
MAX_DAYS = "backup_cleanup_max_days"
KEYS = (MAX_MB, MAX_DAYS)
#: The upper edges of the two ranges.
EDGES = {MAX_MB: 1048576, MAX_DAYS: 3650}


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the tests of this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def listed(client: httpx.AsyncClient) -> dict[str, dict]:
    """The global settings an administrator reads, by key."""
    response = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
    assert response.status_code == 200, f"an administrator lists the global settings: {response.status_code} {response.text[:300]}"
    return {item["key"]: item for item in response.json()["items"]}


async def patch(client: httpx.AsyncClient, **values: object) -> httpx.Response:
    return await client.patch(f"{API_BASE}/settings/global/bulk", json={"items": [{"key": key, "value": str(value)} for key, value in values.items()]}, timeout=TIMEOUT)


async def restore(client: httpx.AsyncClient, originals: dict[str, str]) -> None:
    """Put the original values back through the API; a key the lane does not know (today) has nothing to restore."""
    if originals:
        resp = await client.patch(f"{API_BASE}/settings/global/bulk", json={"items": [{"key": key, "value": value} for key, value in originals.items()]}, timeout=TIMEOUT)
        assert resp.status_code == 200, f"could not restore the original values {originals}: {resp.status_code} {resp.text[:300]}"


def originals_of(items: dict[str, dict]) -> dict[str, str]:
    """The values of the two settings as the lane has them now, for the keys that exist."""
    return {key: items[key]["value"] for key in KEYS if key in items}


@pytest.mark.asyncio
async def test_both_settings_exist_as_integers_and_are_off_on_a_selfhosted_lane(test_server):
    """CLEAN-001: both keys are listed, ``int``, with value ``0``."""
    print_section("CLEAN-001: backup_cleanup_max_mb and backup_cleanup_max_days exist, off")
    async with httpx.AsyncClient() as client:
        await get_admin_session(client)
        items = await listed(client)

    missing = [key for key in KEYS if key not in items]
    assert missing == [], f"the settings {missing} are missing from GET /settings/global"
    facts = {key: (items[key]["value_type"], items[key]["value"]) for key in KEYS}
    assert facts == {MAX_MB: ("int", "0"), MAX_DAYS: ("int", "0")}, f"integers, 0 (off) on a self-hosted lane: {facts}"
    print_success(f"{facts}")


@pytest.mark.asyncio
async def test_the_range_is_accepted_to_its_edges_and_refused_past_them(test_server):
    """CLEAN-002: 0 and the upper edge are accepted (and read back); one past an edge, a negative number or a text that is
    no integer answers 422 naming the key; an accepted item beside a refused one is not saved. The original values are put
    back in a ``finally``."""
    print_section("CLEAN-002: PATCH /settings/global/bulk, the ranges of the two cleanup settings")
    async with httpx.AsyncClient() as client:
        await get_admin_session(client)
        originals = originals_of(await listed(client))
        try:
            accepted = await patch(client, **{MAX_MB: EDGES[MAX_MB], MAX_DAYS: EDGES[MAX_DAYS]})
            assert accepted.status_code == 200, f"the upper edges are accepted: {accepted.status_code} {accepted.text[:300]}"
            read_back = originals_of(await listed(client))
            assert read_back == {MAX_MB: str(EDGES[MAX_MB]), MAX_DAYS: str(EDGES[MAX_DAYS])}, f"the values read back: {read_back}"

            zero = await patch(client, **{MAX_MB: 0, MAX_DAYS: 0})
            assert zero.status_code == 200, f"0 (off) is accepted on a self-hosted instance: {zero.status_code} {zero.text[:300]}"

            refused = {
                "max_mb one past the edge": {MAX_MB: EDGES[MAX_MB] + 1},
                "max_days one past the edge": {MAX_DAYS: EDGES[MAX_DAYS] + 1},
                "max_mb negative": {MAX_MB: -1},
                "max_days negative": {MAX_DAYS: -1},
                "max_mb not an integer": {MAX_MB: "ten"},
                "max_days not an integer": {MAX_DAYS: "1.5"},
            }
            for label, values in refused.items():
                response = await patch(client, **values)
                (key,) = values
                assert response.status_code == 422, f"{label}: 422, not {response.status_code} {response.text[:200]}"
                assert key in str(response.json().get("detail")), f"{label}: the detail names the key {key}: {response.text[:300]}"
            before = originals_of(await listed(client))
            mixed = await patch(client, **{MAX_MB: 5, MAX_DAYS: EDGES[MAX_DAYS] + 1})
            assert mixed.status_code == 422, f"one refused item refuses the bulk: {mixed.status_code} {mixed.text[:200]}"
            assert originals_of(await listed(client)) == before, "all or nothing: the accepted item beside the refused one is not saved"
        finally:
            await restore(client, originals)
        assert originals_of(await listed(client)) == originals, "the original values are back"
    print_success("edges accepted, past them refused with 422, all or nothing")
