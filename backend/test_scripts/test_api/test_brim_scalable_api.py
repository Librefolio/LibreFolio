"""
BRIM API — the two Scalable Capital plugins, end to end (plan 37, §9 and §12).

Scalable has two accounts and LibreFolio gives each its own broker: the broker account, read by ``broker_scalable``,
and the overnight account, read by ``broker_scalable_deposit``. A transfer between the two shows up in both exports —
same day, opposite amounts — and the bulk editor merges each pair into a CASH_TRANSFER.

- SC-A01: each sample into its own broker, its cash rows saved; promote-suggest pairs each internal transfer with its
  other side and with nothing else; the pairs merged as the bulk editor merges them; both samples imported again:
  every saved row is a likely duplicate, each transfer of its merged leg. Red while ``detect_tx_duplicates`` compared
  rows of the same type only: the merged transfers came back as new, and the cash doubled.
- SC-B01: both samples into one broker: nothing to merge (a cash transfer needs two brokers, a conversion two
  currencies), and the broker's cash is the sum of the two files.

Only the rows without an instrument are saved, so no asset needs resolving. What the plugins read, row by row, is
tested in test_external/test_brim_scalable.py. Each test logs in a user of its own, creates its brokers and files, and
deletes them.

Reference: backend/app/services/brim_provider.py (detect_tx_duplicates), backend/app/services/brim_providers/_scalable.py,
backend/app/services/transaction_service.py (promote_suggest_bulk)
"""

import io
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, NamedTuple, Set, Tuple

import httpx
import pytest

from backend.app.config import PROJECT_ROOT, get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"

# The rows the tests save: cash movements without an instrument.
CASH_TYPES = {"DEPOSIT", "WITHDRAWAL", "INTEREST", "TAX", "FEE"}
SCALABLE_TAGS = ["import", "scalable"]
# The window of the bulk editor's merge suggestions by default (TransactionBulkModal, maxDeltaDays).
SUGGEST_TOLERANCE_DAYS = 3


class _Transfer(NamedTuple):
    """An internal transfer as a plugin parses it."""

    tx_type: str
    day: str
    amount: Decimal
    description: str


class _Sample(NamedTuple):
    """A sample export, the plugin that reads it, and the internal transfers it holds."""

    path: Path
    plugin_code: str
    transfers: Tuple[_Transfer, ...]


BROKER_TRANSFER_OUT = _Transfer("WITHDRAWAL", "2026-04-02", Decimal("-1000"), "Interner Übertrag · id SYNTHC0000000000000005")
BROKER_TRANSFER_IN = _Transfer("DEPOSIT", "2026-06-01", Decimal("300"), "Interner Übertrag · id SYNTHC0000000000000010")
OVERNIGHT_TRANSFER_IN = _Transfer("DEPOSIT", "2026-04-02", Decimal("1000"), "Interner Übertrag · id synthD0000000000000003")
OVERNIGHT_TRANSFER_OUT = _Transfer("WITHDRAWAL", "2026-06-01", Decimal("-300"), "Interner Übertrag · id synthD0000000000000006")
# Each transfer of the broker account and its other side in the overnight account: same day, opposite amount.
TRANSFER_PAIRS = [(BROKER_TRANSFER_OUT, OVERNIGHT_TRANSFER_IN), (BROKER_TRANSFER_IN, OVERNIGHT_TRANSFER_OUT)]

BROKER_FILE = _Sample(SAMPLE_DIR / "scalable-broker-export.csv", "broker_scalable", (BROKER_TRANSFER_OUT, BROKER_TRANSFER_IN))
OVERNIGHT_FILE = _Sample(SAMPLE_DIR / "scalable-deposit-export.csv", "broker_scalable_deposit", (OVERNIGHT_TRANSFER_IN, OVERNIGHT_TRANSFER_OUT))


# ============================================================================
# FIXTURES AND HELPERS
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """The lane's backend: the runner's shared server, or one started for this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _log_in_new_user(client: httpx.AsyncClient) -> None:
    """Register a user of this test alone and log it in: the brokers it creates are the only ones it can see."""
    username = f"brim_scalable_{uuid.uuid4().hex[:12]}"
    password = "testpass123"
    response = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password}, timeout=TIMEOUT)
    assert response.status_code == 201, f"Register failed: {response.text}"
    response = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    assert response.status_code == 200, f"Login failed: {response.text}"


async def _create_broker(client: httpx.AsyncClient, label: str, broker_ids: List[int]) -> int:
    """A broker of the logged-in user, uniquely named; its id goes into ``broker_ids`` for the cleanup."""
    response = await client.post(f"{API_BASE}/brokers", json=[{"name": f"Scalable {label} {uuid.uuid4().hex[:10]}", "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    result = response.json()["results"][0]
    assert result["success"], response.text
    broker_ids.append(result["broker_id"])
    return result["broker_id"]


async def _cleanup(client: httpx.AsyncClient, file_ids: List[str], broker_ids: List[int]) -> None:
    """Whoever writes cleans up: the files first, then the brokers (``force``: their transactions go with them)."""
    for file_id in file_ids:
        response = await client.delete(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
        assert response.status_code in (200, 404), f"{file_id}: {response.status_code} {response.text}"
    if broker_ids:
        response = await client.delete(f"{API_BASE}/brokers", params={"ids": broker_ids, "force": True}, timeout=TIMEOUT)
        assert response.status_code == 200 and response.json().get("success_count") == len(broker_ids), response.text


async def _upload_and_parse(client: httpx.AsyncClient, broker_id: int, sample: _Sample, file_ids: List[str]) -> dict:
    """``POST /upload`` of one sample to ``broker_id``, then ``POST /parse`` with its plugin; the file id goes into ``file_ids``."""
    files = {"file": (sample.path.name, io.BytesIO(sample.path.read_bytes()), "text/csv")}
    upload = await client.post(f"{API_BASE}/brokers/import/upload", files=files, data={"broker_id": broker_id}, timeout=TIMEOUT)
    assert upload.status_code == 200, upload.text
    file_id = upload.json()["file_id"]
    file_ids.append(file_id)
    compatible = upload.json()["compatible_plugins"]
    assert sample.plugin_code in compatible, f"the test backend does not read {sample.path.name} with {sample.plugin_code}: compatible {compatible}"
    parsed = await client.post(f"{API_BASE}/brokers/import/files/{file_id}/parse", json={"plugin_code": sample.plugin_code, "broker_id": broker_id}, timeout=TIMEOUT)
    assert parsed.status_code == 200, parsed.text
    return parsed.json()


def _amount(tx: dict) -> Decimal:
    return Decimal(tx["cash"]["amount"])


def _cash_rows(transactions: list) -> Dict[str, Tuple[int, dict]]:
    """``{description: (index in the parse, row)}`` of the rows the tests save: cash movements without an instrument.

    The description identifies the row: the plugins write each transaction's id into it.
    """
    rows = [(index, tx) for index, tx in enumerate(transactions) if tx["type"] in CASH_TYPES and tx.get("asset_id") is None]
    by_description = {tx["description"]: (index, tx) for index, tx in rows}
    assert len(by_description) == len(rows), f"two cash rows share a description: {[tx['description'] for _, tx in rows]}"
    return by_description


def _match_facts(candidate: dict) -> List[tuple]:
    """``(existing id, its type, its description, level)`` of every saved row a parsed row was matched with."""
    return [(match["existing_tx_id"], match["tx_type"], match["tx_description"], match["match_level"]) for match in candidate["tx_existing_matches"]]


def _verdicts(report: dict) -> Dict[int, Tuple[str, List[tuple]]]:
    """``{row index: (category, matches)}`` for every row of a parse's duplicate report: the whole verdict, in one comparable value."""
    verdicts: Dict[int, Tuple[str, List[tuple]]] = {index: ("unique", []) for index in report["tx_unique_indices"]}
    verdicts.update({candidate["tx_row_index"]: ("possible", _match_facts(candidate)) for candidate in report["tx_possible_duplicates"]})
    verdicts.update({candidate["tx_row_index"]: ("likely", _match_facts(candidate)) for candidate in report["tx_likely_duplicates"]})
    return verdicts


async def _validate_and_commit(client: httpx.AsyncClient, body: dict) -> dict:
    """``body`` through ``/transactions/validate`` without a single issue, then ``/transactions/commit``, as the editor submits it."""
    validated = await client.post(f"{API_BASE}/transactions/validate", json=body, timeout=TIMEOUT)
    assert validated.status_code == 200, validated.text
    assert validated.json()["issues"] == [], f"the batch does not validate: {validated.json()['issues']}"
    committed = await client.post(f"{API_BASE}/transactions/commit", json=body, timeout=TIMEOUT)
    assert committed.status_code == 200, committed.text
    assert committed.json()["committed"] is True, committed.text
    return committed.json()


def _new_cash_rows(parsed: dict, sample: _Sample, broker_id: int) -> Dict[str, Tuple[int, dict]]:
    """The cash rows of a parse that finds nothing of its file in the broker, and whose internal transfers are among
    them as ``sample`` describes them: the presence barrier of every later step."""
    verdicts = _verdicts(parsed["duplicates"])
    assert verdicts == {index: ("unique", []) for index in range(len(parsed["transactions"]))}, f"{sample.path.name}: rows taken for ones already saved on broker {broker_id}: {verdicts}"
    cash = _cash_rows(parsed["transactions"])
    expected = {t.description: (t.tx_type, t.day, t.amount, sorted(SCALABLE_TAGS)) for t in sample.transfers}
    found = {description: (row["type"], row["date"], _amount(row), sorted(row["tags"])) for description, (_, row) in cash.items() if description in expected}
    assert found == expected, f"{sample.path.name}: the internal transfers are not among the cash rows as expected; cash rows: {sorted(cash)}"
    return cash


async def _save_cash_rows(client: httpx.AsyncClient, cash: Dict[str, Tuple[int, dict]]) -> Dict[str, int]:
    """Save the cash rows of a parse as parsed; returns their ids by description."""
    descriptions = list(cash)
    result = await _validate_and_commit(client, {"creates": [cash[description][1] for description in descriptions]})
    ids = {item["index"]: item["ids"][0] for item in result["results"] if item["operation"] == "create"}
    assert sorted(ids) == list(range(len(descriptions))), result["results"]
    return {description: ids[index] for index, description in enumerate(descriptions)}


async def _import_cash_rows(client: httpx.AsyncClient, broker_id: int, sample: _Sample, file_ids: List[str]) -> Tuple[Dict[str, int], Decimal]:
    """One sample uploaded to ``broker_id`` and parsed, its cash rows saved as parsed (see ``_new_cash_rows``).

    Returns the saved ids by description, and the sum of the saved cash.
    """
    parsed = await _upload_and_parse(client, broker_id, sample, file_ids)
    cash = _new_cash_rows(parsed, sample, broker_id)
    saved_ids = await _save_cash_rows(client, cash)
    return saved_ids, sum((_amount(row) for _, row in cash.values()), Decimal("0"))


async def _read(client: httpx.AsyncClient, ids: List[int]) -> Dict[int, dict]:
    """The saved transactions ``ids``, by id; every one of them must be found."""
    response = await client.get(f"{API_BASE}/transactions", params={"ids": ids}, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    found = {item["id"]: item for item in response.json()}
    assert set(found) == set(ids), f"saved transactions not found: {sorted(set(ids) - set(found))}"
    return found


async def _suggest(client: httpx.AsyncClient, item: dict) -> Set[int]:
    """The ids ``POST /transactions/promote-suggest`` proposes for one input, asked alone."""
    response = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": SUGGEST_TOLERANCE_DAYS}, json=[item], timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert str(item["id"]) in results, f"no answer for input {item['id']}: {results}"
    return {candidate["id"] for candidate in results[str(item["id"])]}


async def _suggested_partners(client: httpx.AsyncClient, saved: Dict[int, dict]) -> Dict[int, Set[int]]:
    """``{id: ids promote-suggest proposes for it}`` for saved rows, each asked in a request of its own.

    The endpoint leaves the id of every input out of the candidates of every input (no self-match), so saved rows
    asked together could never be proposed to one another: the bulk editor pairs the rows it holds by itself.
    """
    partners = {}
    for tx_id, tx in saved.items():
        partners[tx_id] = await _suggest(client, {"id": tx_id, "type": tx["type"], "broker_id": tx["broker_id"], "date": tx["date"], "currency": tx["cash"]["code"], "amount": tx["cash"]["amount"]})
    return partners


async def _merge(client: httpx.AsyncClient, pairs: List[Tuple[int, int]], saved: Dict[int, dict]) -> Dict[int, str]:
    """Promote each saved ``(id_a, id_b)`` as the bulk editor merges a pair: both texts, one per line, and the shared tags.

    Read back, both legs of each pair are a CASH_TRANSFER pointing at the other, with the joined text, the tags and
    their own amount. Returns the joined text of each leg.
    """
    joined: Dict[int, str] = {}
    for id_a, id_b in pairs:
        joined[id_a] = joined[id_b] = "\n".join((saved[id_a]["description"], saved[id_b]["description"]))
    promotes = [{"id_a": id_a, "id_b": id_b, "resolved_fields": {"description": joined[id_a], "tags": SCALABLE_TAGS}} for id_a, id_b in pairs]
    result = await _validate_and_commit(client, {"promotes": promotes})
    assert sorted(tuple(item["ids"]) for item in result["results"] if item["operation"] == "promote") == sorted(pairs), result["results"]

    other = dict(pairs) | {id_b: id_a for id_a, id_b in pairs}
    legs = await _read(client, list(other))
    actual = {tx_id: (tx["type"], tx["related_transaction_id"], tx["description"], sorted(tx["tags"]), _amount(tx)) for tx_id, tx in legs.items()}
    expected = {tx_id: ("CASH_TRANSFER", other[tx_id], joined[tx_id], sorted(SCALABLE_TAGS), _amount(saved[tx_id])) for tx_id in other}
    assert actual == expected, "each leg must be a CASH_TRANSFER pointing at the other, with the joined text, the tags and its own amount"
    return joined


def _assert_saved_rows_are_likely_duplicates(parsed: dict, saved_ids: Dict[str, int], joined: Dict[int, str]) -> None:
    """A sample parsed again on its broker: each cash row a likely duplicate of exactly the row it was saved as, the
    transfers of their merged CASH_TRANSFER leg (with the joined text); every row never saved still new."""
    cash = _cash_rows(parsed["transactions"])
    assert set(cash) == set(saved_ids), f"the second parse brings other cash rows than the first: {sorted(set(cash) ^ set(saved_ids))}"
    expected: Dict[int, Tuple[str, List[tuple]]] = {}
    for description, (index, tx) in cash.items():
        tx_id = saved_ids[description]
        saved_as = ("CASH_TRANSFER", joined[tx_id]) if tx_id in joined else (tx["type"], description)
        expected[index] = ("likely", [(tx_id, *saved_as, "likely")])
    expected.update({index: ("unique", []) for index in range(len(parsed["transactions"])) if index not in expected})
    assert _verdicts(parsed["duplicates"]) == expected


async def _cash_balances(client: httpx.AsyncClient, broker_id: int) -> Dict[str, Decimal]:
    """``{currency: balance}`` of a broker, from ``GET /brokers/{id}/summary``."""
    response = await client.get(f"{API_BASE}/brokers/{broker_id}/summary", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    return {item["code"]: Decimal(item["amount"]) for item in response.json()["cash_balances"]}


# ============================================================================
# THE TWO ACCOUNTS THROUGH THE API
# ============================================================================


class TestScalableAccounts:
    """The broker account and the overnight account, in two brokers (SC-A01) and in one (SC-B01)."""

    @pytest.mark.asyncio
    async def test_transfers_merged_across_the_two_brokers_come_back_as_duplicates(self, test_server):
        """SC-A01: two brokers, one per account; the internal transfers suggested, merged, then exported again.

        Each sample goes into its own broker (``broker_scalable`` and ``broker_scalable_deposit``) and its cash rows
        are saved. promote-suggest proposes, for each of the four transfers, its other side and nothing else: −1000 /
        +1000 on 2026-04-02, +300 / −300 on 2026-06-01. Merged as the bulk editor merges them, both legs become a
        CASH_TRANSFER with both texts. Both samples parsed again on their brokers — an export "since the last one"
        re-delivers the last day — every saved row is a LIKELY duplicate of exactly itself, the transfers of their
        merged leg, and the rows never saved are still new.
        """
        print_section("SC-A01: Scalable in two brokers, transfers merged, then imported again")
        async with httpx.AsyncClient() as client:
            await _log_in_new_user(client)
            file_ids: List[str] = []
            broker_ids: List[int] = []
            try:
                broker = await _create_broker(client, "broker account", broker_ids)
                overnight = await _create_broker(client, "overnight account", broker_ids)
                saved_broker, _ = await _import_cash_rows(client, broker, BROKER_FILE, file_ids)
                saved_overnight, _ = await _import_cash_rows(client, overnight, OVERNIGHT_FILE, file_ids)

                pairs = [(saved_broker[out.description], saved_overnight[other_side.description]) for out, other_side in TRANSFER_PAIRS]
                transfers = await _read(client, [tx_id for pair in pairs for tx_id in pair])
                expected_partners = {id_a: {id_b} for id_a, id_b in pairs} | {id_b: {id_a} for id_a, id_b in pairs}
                assert await _suggested_partners(client, transfers) == expected_partners, "promote-suggest must pair each internal transfer with its other side, and with nothing else"

                joined = await _merge(client, pairs, transfers)

                again = await _upload_and_parse(client, broker, BROKER_FILE, file_ids)
                _assert_saved_rows_are_likely_duplicates(again, saved_broker, joined)
                again = await _upload_and_parse(client, overnight, OVERNIGHT_FILE, file_ids)
                _assert_saved_rows_are_likely_duplicates(again, saved_overnight, joined)
                print_success("✓ merged transfers suggested, merged, and recognised when exported again")
            finally:
                await _cleanup(client, file_ids, broker_ids)

    @pytest.mark.asyncio
    async def test_both_accounts_in_one_broker_merge_nothing_and_add_up(self, test_server):
        """SC-B01: both samples into one broker: no pair proposed, no error, the cash is the sum of the two files.

        The overnight file goes in after the broker file's cash rows are saved, and nothing in it is taken for one of
        them (its +1000 transfer is not the −1000 already there). promote-suggest proposes nothing for the four
        transfers: a cash transfer needs two brokers, a conversion two currencies. Presence barrier: asked from
        another broker, the same endpoint does propose the −1000 of this one. The summary's cash is the sum of every
        saved row of both files, and the broker holds exactly those rows.
        """
        print_section("SC-B01: Scalable broker and overnight account in one broker")
        async with httpx.AsyncClient() as client:
            await _log_in_new_user(client)
            file_ids: List[str] = []
            broker_ids: List[int] = []
            try:
                both = await _create_broker(client, "both accounts", broker_ids)
                elsewhere = await _create_broker(client, "elsewhere", broker_ids)  # holds nothing: it only asks promote-suggest from another broker
                saved_broker, cash_broker = await _import_cash_rows(client, both, BROKER_FILE, file_ids)
                saved_overnight, cash_overnight = await _import_cash_rows(client, both, OVERNIGHT_FILE, file_ids)
                saved = saved_broker | saved_overnight
                assert len(saved) == len(saved_broker) + len(saved_overnight), "the two files share a description"

                transfers = await _read(client, [saved[row.description] for pair in TRANSFER_PAIRS for row in pair])
                assert {tx["broker_id"] for tx in transfers.values()} == {both}
                assert await _suggested_partners(client, transfers) == {tx_id: set() for tx_id in transfers}, "no pair can be merged inside one broker"
                from_elsewhere = {"id": -1, "type": "DEPOSIT", "broker_id": elsewhere, "date": BROKER_TRANSFER_OUT.day, "currency": "EUR", "amount": str(-BROKER_TRANSFER_OUT.amount)}
                assert await _suggest(client, from_elsewhere) == {saved[BROKER_TRANSFER_OUT.description]}, "presence barrier: from another broker, the −1000 transfer must be proposed"

                listed = await client.get(f"{API_BASE}/transactions", params={"broker_id": both}, timeout=TIMEOUT)
                assert listed.status_code == 200, listed.text
                assert {item["id"] for item in listed.json()} == set(saved.values())
                assert await _cash_balances(client, both) == {"EUR": cash_broker + cash_overnight}
                print_success("✓ one broker: nothing to merge, the cash adds up")
            finally:
                await _cleanup(client, file_ids, broker_ids)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
