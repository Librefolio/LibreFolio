"""
BRIM API: the personal ``date_order`` of the generic CSV plugin, end to end (CP12, W5-8).

The user's own order of day and month (``PATCH /settings/plugins/bulk``, family ``brim``) reaches the parse
(``POST /brokers/import/files/{id}/parse``), and a change of it makes the cached parse stale
(``GET /brokers/import/files`` and ``GET /brokers/import/files/{id}``: ``parse_is_stale``), without the API ever showing the
fingerprint the stale rule compares.

- DO-A01: the plugin's card is in the catalogue of the plugin settings, for a member: ``date_order``, a select on ``day_first``.
- DO-B01: a file parsed over the defaults is not stale; the upload response, the file info and the listing carry no
  ``parsed_settings_fingerprint``.
- DO-C01: the user picks ``month_first``: the file is stale (info and listing); parsing again gives the month-first date and
  the file is current; clearing the choice makes it stale again (the record says month first); the choice is cleared at the end.

Each test logs in a user of its own, creates its broker and its file, and writes only that user's own setting: it goes with
the user. The unit is scoped (own user, own rows).

Reference: backend/app/services/brim/brim_file_settings.py, brim_parse_pool.py, brim_provider.py (save_parse_result),
backend/app/services/brim_providers/broker_generic_csv/plugin.py (date_order)
"""

from __future__ import annotations

import io
import json
import uuid
from datetime import date

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_api.test_brim_api import create_test_broker, create_test_user
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
PLUGIN = "broker_generic_csv"
FIELD = "date_order"
FINGERPRINT_KEY = "parsed_settings_fingerprint"

#: 03/01/2025 is 3 January day first and 1 March month first; the ISO row never moves.
AMBIGUOUS_CSV = b"date,type,quantity,amount,currency,asset,description\n03/01/2025,DEPOSIT,0,500.00,EUR,,ambiguous\n2025-02-03,DEPOSIT,0,100.00,EUR,,iso\n"


@pytest.fixture(scope="module")
def test_server():
    """The lane's server (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _upload(client: httpx.AsyncClient, broker_id: int) -> tuple[str, dict]:
    """The file id of an upload of the ambiguous CSV, and the upload response."""
    files = {"file": (f"date_order_{uuid.uuid4().hex[:8]}.csv", io.BytesIO(AMBIGUOUS_CSV), "text/csv")}
    response = await client.post(f"{API_BASE}/brokers/import/upload", files=files, data={"broker_id": broker_id}, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    return response.json()["file_id"], response.json()


async def _parse(client: httpx.AsyncClient, file_id: str, broker_id: int) -> dict[str, date]:
    """Parse the file and answer the date of each transaction by its description."""
    response = await client.post(f"{API_BASE}/brokers/import/files/{file_id}/parse", json={"plugin_code": PLUGIN, "broker_id": broker_id}, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    return {tx["description"]: date.fromisoformat(tx["date"]) for tx in response.json()["transactions"]}


async def _file(client: httpx.AsyncClient, file_id: str) -> dict:
    response = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    return response.json()


async def _listed(client: httpx.AsyncClient, broker_id: int, file_id: str) -> dict:
    """The listing item of the file, found by its id (the listing is filtered on the broker the test created)."""
    response = await client.get(f"{API_BASE}/brokers/import/files", params={"broker_ids": broker_id}, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    matching = [item for item in response.json() if item["file_id"] == file_id]
    assert len(matching) == 1, f"file {file_id} not found in the listing of broker {broker_id}"
    return matching[0]


async def _set_order(client: httpx.AsyncClient, value: str | None) -> httpx.Response:
    """The user's own ``date_order``: ``value`` saved, or the saved value cleared when ``None``."""
    item = {"family": "brim", "plugin_code": PLUGIN, "field_key": FIELD, "scope": "user"} | ({"value": value} if value is not None else {"clear": True})
    return await client.patch(f"{API_BASE}/settings/plugins/bulk", json={"items": [item]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_the_catalogue_offers_the_date_order_to_a_member(test_server):
    """DO-A01: the plugin's card: one personal select, on its default."""
    print_section("DO-A01: the catalogue lists date_order")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)

        response = await client.get(f"{API_BASE}/settings/plugins", params={"family": "brim", "plugin_code": PLUGIN}, timeout=TIMEOUT)

        assert response.status_code == 200, response.text
        entries = [plugin for plugin in response.json()["plugins"] if plugin["plugin_code"] == PLUGIN]
        assert len(entries) == 1, f"{PLUGIN} is not in the catalogue of the brim family"
        fields = {declared["key"]: declared for declared in entries[0]["fields"]}
        assert FIELD in fields, sorted(fields)
        assert (fields[FIELD]["scope"], fields[FIELD]["value"], fields[FIELD]["is_set"]) == ("user", "day_first", False)
        print_success("date_order: a personal select on day_first")


@pytest.mark.asyncio
async def test_a_file_parsed_over_the_defaults_is_current_and_shows_no_fingerprint(test_server):
    """DO-B01: not stale, and the fingerprint is stored but never served."""
    print_section("DO-B01: parsed over the defaults")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        broker_id = await create_test_broker(client)
        file_id, uploaded = await _upload(client, broker_id)

        dates = await _parse(client, file_id, broker_id)

        assert dates["ambiguous"] == date(2025, 1, 3), "the default is day first, as the plugin always read"
        info = await _file(client, file_id)
        item = await _listed(client, broker_id, file_id)
        assert (info["parse_is_stale"], item["parse_is_stale"]) == (False, False)
        for body in (uploaded, info, item):
            assert FINGERPRINT_KEY not in body, f"the API serves {FINGERPRINT_KEY}"
        assert FINGERPRINT_KEY not in json.dumps(info) and info["last_parse_result"] is not None
        print_success("current, no fingerprint in the API")


@pytest.mark.asyncio
async def test_a_changed_personal_value_makes_the_parse_stale_until_the_file_is_parsed_again(test_server):
    """DO-C01: day first (default) -> month first chosen -> stale -> parse -> month-first date, current -> cleared -> stale."""
    print_section("DO-C01: choose month first, the file goes stale, parse again")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        broker_id = await create_test_broker(client)
        file_id, _ = await _upload(client, broker_id)
        try:
            first = await _parse(client, file_id, broker_id)
            assert first["ambiguous"] == date(2025, 1, 3)
            assert (await _file(client, file_id))["parse_is_stale"] is False, "barrier: current before the user chooses"

            chosen = await _set_order(client, "month_first")
            assert chosen.status_code == 200, f"the user's own date_order was refused: {chosen.status_code} {chosen.text}"
            assert (await _file(client, file_id))["parse_is_stale"] is True
            assert (await _listed(client, broker_id, file_id))["parse_is_stale"] is True

            second = await _parse(client, file_id, broker_id)
            assert second["ambiguous"] == date(2025, 3, 1), "the parse reads the user's month-first order"
            assert second["iso"] == first["iso"] == date(2025, 2, 3), "an ISO date does not depend on the order"
            assert (await _file(client, file_id))["parse_is_stale"] is False
            assert (await _listed(client, broker_id, file_id))["parse_is_stale"] is False

            cleared = await _set_order(client, None)
            assert cleared.status_code == 200, cleared.text
            assert (await _file(client, file_id))["parse_is_stale"] is True, "back on the default, the stored parse was drawn month first"
            assert (await _parse(client, file_id, broker_id))["ambiguous"] == date(2025, 1, 3)
            assert (await _file(client, file_id))["parse_is_stale"] is False
            print_success("stale on a change, current after a new parse, fingerprint never served")
        finally:
            await _set_order(client, None)  # the user is a temporary one; the setting goes with it, cleared anyway
