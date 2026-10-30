"""
The hosting panel's figures route, ``GET /api/v1/panel/metrics`` (LibreFolio 1.3, lot CL-M1, SECURITY): the credential
and the refusals as the app answers them. The figures themselves (every measure, each failing alone, the job-log windows,
the files, the privacy of the JSON) are in ``test_services/test_panel_metrics_service.py``; the route's place in the
document (tag, scheme, documented answers) is in ``test_hosting_panel_routes.py`` (HPR-002..HPR-011).

Under test: ``backend/app/api/v1/panel.py`` (``get_panel_metrics``) and ``panel_access(PanelScope.METRICS)``
(``services/platform/hosting_panel/access.py``) as the route meets it. The contract:

- Scope ``metrics``: a SIGNED TICKET ONLY, like ``backup:restore``: no token of any scope opens it. Without
  ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` the route answers 404 ``Not Found`` (whatever the request carries, the status, backup
  and wake tokens included) and logs nothing, counts nothing.
- 401 ``panel_metrics_unauthorized`` (with ``WWW-Authenticate: Bearer``, counted for the address) for: no credential, a
  static token of any scope, a credential that is not a ticket, a ticket whose signature does not verify, a ticket in the
  query string or in another scheme. A ticket whose signature is the panel's but that is refused keeps its own
  ``panel_ticket_*`` code and is NEVER counted: another scope's ticket (``panel_ticket_wrong_scope``), a replayed one
  (``panel_ticket_replayed``), an expired, not yet valid, wrong-audience or malformed one. The route's ticket opens nothing
  else (the other scopes answer it ``panel_ticket_wrong_scope``), and a refusal for another scope does not burn its
  ``jti``.
- 429 ``panel_too_many_attempts`` when the address sent ``PANEL_ATTEMPT_LIMIT`` refused credentials in the window, the
  limiter shared with every panel scope, even to a valid ticket (whose ``jti`` the 429 does not record). 503
  ``panel_metrics_unavailable`` for ticket settings that cannot be used.
- It is in ``ALLOWED_WHEN_BLOCKED`` and ``ALLOWED_WHEN_AWAITING_RESTORE`` (hence ``ALLOWED_WHEN_RESTORE_INTERRUPTED``): on
  a blocked instance, in the awaiting-restore mode and with an interrupted restore, a valid ticket answers 200 and a call
  without one follows the same refusals as outside the state, never a 423.
- One line per call, ``Hosting panel request``, scope ``metrics``, never the ticket; and a call is never user activity.
- A measure that fails is ``null`` in a 200 (never a 500, never its message in the answer).

How. The app of ``backend/app/main.py`` runs in this process through ``httpx.ASGITransport`` from a public peer
(``203.0.113.62``), as ``test_panel_restore_api.py`` does, and its keys, tickets and constants are that file's (one
ticket helper, not two). The database is an in-memory one the test owns entirely (``dependency_overrides``), the data
directory ``tmp_path/data`` with a database file, uploads and a job log, ``shutil.disk_usage`` stood in for, the attempts
limiter and the activity record the test's own. No server, no lane database, no network.

Red today: ``PanelScope.METRICS`` and ``get_panel_metrics`` do not exist: the path answers the plain 404 of a route that
does not exist, which the presence barrier of each case turns into a red naming the route.
"""

from __future__ import annotations

import asyncio
import importlib
import secrets
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from structlog.contextvars import merge_contextvars
from structlog.testing import capture_logs

from backend.app.api.v1 import instance_block
from backend.app.config import API_V1_PREFIX, is_test_mode
from backend.app.db.base import SQLModel
from backend.app.db.session import get_session_generator
from backend.app.services.platform import client_address as client_address_module
from backend.app.services.platform import restore_guard
from backend.app.services.platform.hosting_panel import access as access_module
from backend.app.services.platform.hosting_panel import ticket_registry
from backend.app.services.platform.instance_key import instance_key_path
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_api import test_panel_restore_api as restore_api
from backend.test_scripts.test_services import test_panel_metrics_service as service_cases
from backend.test_scripts.test_utils import print_section, print_success

METRICS = f"{API_V1_PREFIX}/panel/metrics"
SCOPE = "metrics"
ROUTE_NAME = "get_panel_metrics"
UNAUTHORIZED_CODE = "panel_metrics_unauthorized"
UNAVAILABLE_CODE = "panel_metrics_unavailable"
TOO_MANY_CODE = restore_api.TOO_MANY_CODE
WRONG_SCOPE_CODE = restore_api.WRONG_SCOPE_CODE
REPLAYED_CODE = restore_api.REPLAYED_CODE
OFF_ANSWER = (404, {"detail": "Not Found"})
ATTEMPT_LIMIT = restore_api.ATTEMPT_LIMIT
ANSWER_KEYS = service_cases.ANSWER_KEYS
TIMEOUT = 60.0

PANEL_ENVIRONMENT = restore_api.PANEL_ENVIRONMENT
KEYS_VARIABLE = restore_api.KEYS_VARIABLE
PUBLIC_URL_VARIABLE = restore_api.PUBLIC_URL_VARIABLE
STATUS_TOKEN_VARIABLE = restore_api.STATUS_TOKEN_VARIABLE
BACKUP_TOKEN_VARIABLE = restore_api.BACKUP_TOKEN_VARIABLE
WAKE_TOKEN_VARIABLE = restore_api.WAKE_TOKEN_VARIABLE
AWAIT_VARIABLE = restore_api.AWAIT_VARIABLE
BLOCKED_VARIABLE = restore_api.BLOCKED_VARIABLE
DELETION_DATE_VARIABLE = restore_api.DELETION_DATE_VARIABLE

#: The states of the instance in which the panel must still read its figures.
STATES = {
    "blocked": {BLOCKED_VARIABLE: "1"},
    "awaiting-restore": {AWAIT_VARIABLE: "1"},
    "blocked-and-awaiting-restore": {BLOCKED_VARIABLE: "1", AWAIT_VARIABLE: "1"},
}
STATE_CASES = [pytest.param(name, id=name) for name in STATES]


# =============================================================================
# The app in process, the world, the panel of a test
# =============================================================================


@pytest.fixture(scope="module")
def app() -> FastAPI:
    assert is_test_mode(), "Precondition: test mode, so the app in process never reaches the production data directory"
    from backend.app.main import app as main_app  # noqa: PLC0415 — the server's own app, imported by the fixture that needs it

    return main_app


@dataclass
class Instance:
    """What a test works with: the app, the data directory, the database session, the attempts limiter, the activity record
    and the monkeypatch to change the environment."""

    app: FastAPI
    root: Path
    session: AsyncSession
    limiter: SlidingWindowLimiter
    activity: activity_module.Activity
    monkeypatch: pytest.MonkeyPatch
    disk: service_cases.FakeDisk = field(default_factory=service_cases.FakeDisk)
    status_token: str = ""
    backup_token: str = ""
    wake_token: str = ""

    @property
    def key(self) -> str | None:
        return client_address_module.client_rate_key(restore_api.PEER[0])

    def counted(self) -> int:
        return self.limiter.count(self.key)

    def switch(self, state: str) -> None:
        for variable, value in STATES[state].items():
            self.monkeypatch.setenv(variable, value)

    def new_limiter(self) -> SlidingWindowLimiter:
        self.limiter = SlidingWindowLimiter(restore_api.ATTEMPT_LIMIT, restore_api.ATTEMPT_WINDOW_SECONDS, clock=restore_api._frozen_clock)
        self.monkeypatch.setattr(access_module, "PANEL_ATTEMPTS", self.limiter)
        return self.limiter


@pytest_asyncio.fixture
async def instance(app: FastAPI, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncIterator[Instance]:
    """The real app for this test: the panel's keys and public address set (the scope is on), the three static tokens set
    too (they must open nothing here), no switch; the data directory with its files and job log; an in-memory database
    with the world of the service cases; the disk, the limiter and the activity record the test's own."""
    for name in (*PANEL_ENVIRONMENT, AWAIT_VARIABLE, BLOCKED_VARIABLE, DELETION_DATE_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    root = service_cases.use_data_dir(monkeypatch, tmp_path)
    service_cases.write_data_files(root)
    service_cases.write_job_log(root, service_cases.happy_entries(datetime.now(UTC)))
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, restore_api.PUBLIC_URL)
    monkeypatch.setenv(KEYS_VARIABLE, restore_api.KEY.entry)
    tokens = {"status_token": (STATUS_TOKEN_VARIABLE, restore_api.a_token()), "backup_token": (BACKUP_TOKEN_VARIABLE, restore_api.a_token()), "wake_token": (WAKE_TOKEN_VARIABLE, restore_api.a_token())}
    for variable, value in tokens.values():
        monkeypatch.setenv(variable, value)
    activity = activity_module.Activity()
    monkeypatch.setattr(activity_module, "ACTIVITY", activity)
    limiter = SlidingWindowLimiter(restore_api.ATTEMPT_LIMIT, restore_api.ATTEMPT_WINDOW_SECONDS, clock=restore_api._frozen_clock)
    monkeypatch.setattr(access_module, "PANEL_ATTEMPTS", limiter)
    monkeypatch.setattr(client_address_module, "_configured_header", lambda: None)
    disk = service_cases.FakeDisk()
    monkeypatch.setattr(service_cases.shutil, "disk_usage", disk)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    with restore_api.client_address_state_kept():
        try:
            async with engine.begin() as connection:
                await connection.run_sync(SQLModel.metadata.create_all)
            async with AsyncSession(engine, expire_on_commit=False) as session:
                await service_cases.seed_world(session)
                monkeypatch.setitem(app.dependency_overrides, get_session_generator, lambda: session)
                yield Instance(app, root, session, limiter, activity, monkeypatch, disk, **{name: value for name, (_, value) in tokens.items()})
        finally:
            await engine.dispose()


async def send(m: Instance, method: str, path: str, *, authorization: str | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
    """One request to the app in process, from the public peer; ``authorization`` is the whole header value."""
    sent = dict(headers or {})
    if authorization is not None:
        sent["Authorization"] = authorization
    transport = httpx.ASGITransport(app=m.app, raise_app_exceptions=False, client=restore_api.PEER)
    async with asyncio.timeout(TIMEOUT), httpx.AsyncClient(transport=transport, base_url=restore_api.BASE_URL) as client:
        return await client.request(method, path, headers=sent)


async def ask(m: Instance, *, authorization: str | None = None, path: str = METRICS, method: str = "GET", headers: dict[str, str] | None = None) -> tuple[httpx.Response, list[dict[str, Any]]]:
    """A request inside a log capture: the response and the lines it wrote."""
    with capture_logs(processors=[merge_contextvars]) as events:
        response = await send(m, method, path, authorization=authorization, headers=headers)
    return response, events


def bearer(token: str) -> str:
    return f"Bearer {token}"


def a_ticket(scope: str = SCOPE, **times: int) -> restore_api.Ticket:
    return restore_api.ticket(scope, **times)


def code_of(response: httpx.Response) -> tuple[int, Any]:
    """The status, and the code of the ``detail`` (the body whole when it has none)."""
    try:
        body = response.json()
    except ValueError:
        return response.status_code, response.text[:300]
    detail = body.get("detail") if isinstance(body, dict) else None
    return response.status_code, detail.get("code") if isinstance(detail, dict) else body


def panel_lines(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("event") == access_module.REQUEST_LINE]


def the_route() -> Any:
    """``get_panel_metrics`` of CL-M1."""
    module = importlib.import_module("backend.app.api.v1.panel")
    found = getattr(module, ROUTE_NAME, None)
    if found is None:
        pytest.fail(f"CL-M1: backend.app.api.v1.panel gives no {ROUTE_NAME}")
    return found


def the_scope() -> Any:
    found = getattr(access_module.PanelScope, "METRICS", None)
    if found is None:
        pytest.fail("CL-M1: PanelScope has no METRICS")
    assert found.value == SCOPE, f"PanelScope.METRICS is {SCOPE!r}: {found.value!r}"
    return found


# =============================================================================
# PM-001..002: off without the panel's keys
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("presented", ["nothing", "status-token", "backup-token", "wake-token", "a-ticket"])
async def test_without_the_panels_keys_the_route_is_a_404_that_logs_and_counts_nothing(instance, presented):
    """PM-001: no ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` and the three static tokens set (their scopes are on): the metrics route
    answers ``404 {"detail": "Not Found"}`` whatever the request carries, a static token included (no token opens it),
    writes no ``Hosting panel request`` line and counts nothing for the address."""
    print_section("PM-001: off without the keys")
    the_route()
    the_scope()
    instance.monkeypatch.delenv(KEYS_VARIABLE)
    credentials = {"nothing": None, "status-token": bearer(instance.status_token), "backup-token": bearer(instance.backup_token), "wake-token": bearer(instance.wake_token), "a-ticket": bearer(a_ticket().value)}

    response, events = await ask(instance, authorization=credentials[presented])

    assert (response.status_code, response.json()) == OFF_ANSWER, f"off without the keys, whatever it carries: {response.status_code} {response.text}"
    assert panel_lines(events) == [], f"a scope that is off writes no line: {panel_lines(events)}"
    assert instance.counted() == 0, "and counts nothing for the address"
    print_success(f"off: 404 with {presented}")


# =============================================================================
# PM-010..012: what proves nothing is a 401 of the scope, counted
# =============================================================================


def tampered(value: str) -> str:
    """The ticket with the end of its signature changed: the panel's header and claims, a signature that does not verify."""
    return value[:-3] + ("AAA" if not value.endswith("AAA") else "BBB")


UNPROVEN = [
    pytest.param("no-credential", id="no-credential"),
    pytest.param("status-token", id="status-token"),
    pytest.param("backup-token", id="backup-token"),
    pytest.param("wake-token", id="wake-token"),
    pytest.param("garbage", id="not-a-ticket"),
    pytest.param("tampered-signature", id="tampered-signature"),
    pytest.param("basic-scheme", id="basic-scheme"),
    pytest.param("ticket-in-the-query", id="ticket-in-the-query"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", UNPROVEN)
async def test_what_proves_nothing_gets_the_scopes_own_401_and_is_counted(instance, case):
    """PM-010: with the keys on, no credential, the status, backup or wake token (no token opens this scope), a string that
    is no ticket, a ticket with a bad signature, a ``Basic`` header and a valid ticket in the query string alone each get
    ``401 panel_metrics_unauthorized`` with ``WWW-Authenticate: Bearer`` and a message, count once for the address, write
    one ``refused`` line of scope ``metrics``, and show nothing they carried. Barrier: the status token does open the
    status route, so the tokens of this test are real."""
    valid = a_ticket()
    path = METRICS
    authorization: str | None
    if case == "no-credential":
        authorization = None
    elif case == "garbage":
        authorization = bearer("this-is-not-a-ticket")
    elif case == "tampered-signature":
        authorization = bearer(tampered(valid.value))
    elif case == "basic-scheme":
        authorization = f"Basic {valid.value}"
    elif case == "ticket-in-the-query":
        authorization, path = None, f"{METRICS}?ticket={valid.value}&token={valid.value}"
    else:
        authorization = bearer({"status-token": instance.status_token, "backup-token": instance.backup_token, "wake-token": instance.wake_token}[case])
    barrier = await send(instance, "GET", f"{API_V1_PREFIX}/panel/status", authorization=bearer(instance.status_token))
    assert barrier.status_code == 200, f"Barrier: the status token opens the status route: {barrier.status_code} {barrier.text}"
    the_scope()

    response, events = await ask(instance, authorization=authorization, path=path)

    status, code = code_of(response)
    assert (status, code) == (401, UNAUTHORIZED_CODE), f"{case}: the scope's own 401: {response.status_code} {response.text}"
    detail = response.json()["detail"]
    assert isinstance(detail.get("message"), str) and detail["message"], f"a message beside the code: {detail}"
    assert response.headers.get_list("www-authenticate") == ["Bearer"], f"a bearer challenge: {response.headers}"
    assert instance.counted() == 1, f"a credential that proves nothing is counted once: {instance.counted()}"
    lines = panel_lines(events)
    assert len(lines) == 1 and (lines[0].get("scope"), lines[0].get("outcome")) == (SCOPE, "refused"), f"one refused line of scope metrics: {lines}"
    shown = repr(events) + response.text + repr(dict(response.headers))
    carried = [secret for secret in (instance.status_token, instance.backup_token, instance.wake_token, valid.value, valid.jti) if secret in shown]
    assert carried == [], f"the answer or a line shows what the request carried: {len(carried)} of it"


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong", ["status", "backup", "wake", "backup:restore", "metrics:read"])
async def test_a_ticket_of_another_scope_is_wrong_scope_and_not_counted(instance, wrong):
    """PM-011: a validly signed ticket for ANOTHER scope (``status``, ``backup``, ``wake``, ``backup:restore``, a near name)
    is ``401 panel_ticket_wrong_scope``, never counted (it comes from whoever holds the key), one refused line, and the
    next valid ticket of scope ``metrics`` opens the route: the refusal closed nothing."""
    the_scope()
    foreign = a_ticket(wrong)

    response, events = await ask(instance, authorization=bearer(foreign.value))

    assert code_of(response) == (401, WRONG_SCOPE_CODE), f"scope {wrong!r}: {response.status_code} {response.text}"
    assert instance.counted() == 0, "a signed refusal is never counted"
    assert [line.get("outcome") for line in panel_lines(events)] == ["refused"], f"one refused line: {panel_lines(events)}"
    opened = await send(instance, "GET", METRICS, authorization=bearer(a_ticket().value))
    assert opened.status_code == 200, f"a valid ticket of scope metrics then opens the route: {opened.status_code} {opened.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        pytest.param("GET", f"{API_V1_PREFIX}/panel/status", id="status"),
        pytest.param("GET", f"{API_V1_PREFIX}/backup/panel/restore/status", id="restore-status"),
        pytest.param("POST", f"{API_V1_PREFIX}/backup/panel/jobs", id="backup-start"),
        pytest.param("GET", f"{API_V1_PREFIX}/backup/panel/jobs/nojob", id="backup-poll"),
        pytest.param("POST", f"{API_V1_PREFIX}/system/wake-sync", id="wake-sync"),
    ],
)
async def test_the_metrics_ticket_opens_no_other_scope_and_a_refusal_there_keeps_its_jti(instance, method, path):
    """PM-012: the route's ticket is useful for the figures alone: every other panel route answers it ``401
    panel_ticket_wrong_scope`` (not counted), and that refusal does not record its ``jti``: the same ticket then opens
    the metrics route once."""
    the_scope()
    ticket = a_ticket()

    elsewhere = await send(instance, method, path, authorization=bearer(ticket.value))

    assert code_of(elsewhere) == (401, WRONG_SCOPE_CODE), f"{method} {path} with a metrics ticket: {elsewhere.status_code} {elsewhere.text}"
    assert instance.counted() == 0, "not counted"
    here = await send(instance, "GET", METRICS, authorization=bearer(ticket.value))
    assert here.status_code == 200, f"the refusal elsewhere left the jti unused, the same ticket opens the figures: {here.status_code} {here.text}"


# =============================================================================
# PM-020..024: the ticket, once
# =============================================================================


@pytest.mark.asyncio
async def test_a_valid_ticket_opens_the_route_once_and_a_replay_is_refused_uncounted(instance):
    """PM-020: a ticket of scope ``metrics`` answers 200 with the 15 keys; the same ticket again is ``401
    panel_ticket_replayed`` (never counted); a new ticket opens it again."""
    print_section("PM-020: one ticket, one call")
    ticket = a_ticket()
    the_scope()

    first = await send(instance, "GET", METRICS, authorization=bearer(ticket.value))
    replay, events = await ask(instance, authorization=bearer(ticket.value))
    fresh = await send(instance, "GET", METRICS, authorization=bearer(a_ticket().value))

    assert first.status_code == 200 and set(first.json()) == ANSWER_KEYS, f"a valid ticket: 200 with exactly the 15 keys: {first.status_code} {first.text}"
    assert code_of(replay) == (401, REPLAYED_CODE), f"the same ticket twice: {replay.status_code} {replay.text}"
    assert replay.headers.get_list("www-authenticate") == ["Bearer"], "a bearer challenge"
    assert [line.get("outcome") for line in panel_lines(events)] == ["refused"], f"one refused line: {panel_lines(events)}"
    assert instance.counted() == 0, "a replay is never counted"
    assert fresh.status_code == 200, f"a new ticket opens it again: {fresh.status_code} {fresh.text}"
    print_success("200 once, replay refused, a new ticket 200")


@pytest.mark.asyncio
@pytest.mark.parametrize("refusal", ["expired", "not-yet-valid", "wrong-audience", "too-long-lived"])
async def test_a_signed_ticket_that_is_refused_has_its_own_code_and_is_not_counted(instance, refusal):
    """PM-021: expired (``panel_ticket_expired``), issued in the future (``panel_ticket_not_yet_valid`` with ``Retry-After:
    5``), for another instance (``panel_ticket_wrong_audience``), or living over 300 s (``panel_ticket_invalid``): each its
    own 401 with a bearer challenge, never counted, never a 200."""
    the_scope()
    now = int(time.time())
    expected = {"expired": "panel_ticket_expired", "not-yet-valid": "panel_ticket_not_yet_valid", "wrong-audience": "panel_ticket_wrong_audience", "too-long-lived": "panel_ticket_invalid"}[refusal]
    if refusal == "expired":
        ticket = a_ticket(iat=now - 1000)
    elif refusal == "not-yet-valid":
        ticket = a_ticket(iat=now + 3600, exp=now + 3600 + 240)
    elif refusal == "too-long-lived":
        ticket = a_ticket(iat=now - 5, exp=now + 3000)
    else:
        ticket = a_ticket()
        instance.monkeypatch.setenv(PUBLIC_URL_VARIABLE, "https://another-instance.example.com")

    response, events = await ask(instance, authorization=bearer(ticket.value))

    assert code_of(response) == (401, expected), f"{refusal}: {response.status_code} {response.text}"
    assert response.headers.get_list("www-authenticate") == ["Bearer"]
    if refusal == "not-yet-valid":
        assert response.headers.get("retry-after") == "5", f"a clock behind is told to retry: {dict(response.headers)}"
    assert instance.counted() == 0, f"{refusal}: a signed refusal is never counted"
    assert ticket.value not in repr(events) + response.text, "the ticket is not shown"


@pytest.mark.asyncio
@pytest.mark.parametrize("setting", ["unusable-keys", "no-public-address"])
async def test_ticket_settings_that_cannot_be_used_are_the_scopes_503_and_show_nothing(instance, setting):
    """PM-022: keys that do not parse, or keys without a usable ``LIBREFOLIO_PUBLIC_URL`` (no audience), answer ``503
    panel_metrics_unavailable``, not counted; the variable's value is shown nowhere, and no figure is."""
    the_scope()
    garbage = "kid-without-a-key"
    if setting == "unusable-keys":
        instance.monkeypatch.setenv(KEYS_VARIABLE, garbage)
    else:
        instance.monkeypatch.delenv(PUBLIC_URL_VARIABLE)

    response, events = await ask(instance, authorization=bearer(a_ticket().value))

    assert code_of(response) == (503, UNAVAILABLE_CODE), f"{setting}: {response.status_code} {response.text}"
    assert instance.counted() == 0, "an unusable setting is not a refused credential"
    assert garbage not in response.text + repr(panel_lines(events)), "the value of the setting is not shown"


@pytest.mark.asyncio
@pytest.mark.parametrize("kid", ["h62-key-rotated-away", "k" * 200])
async def test_a_ticket_signed_with_a_key_the_instance_does_not_hold_is_unknown_key_and_counted(instance, kid):
    """PM-023: a ticket whose ``kid`` is not among ``LIBREFOLIO_PANEL_PUBLIC_KEYS`` (a rotation half done; a hostile 200
    character ``kid``) is ``401 panel_ticket_unknown_key`` with a bearer challenge, unlike every other ``panel_ticket_*``
    COUNTED once for the address (it proves nothing: anyone can sign with a key of their own), one refused line whose ``kid``
    is cut to 64 characters, and the ticket is not shown. Barrier: the same claims signed with the held key open the route."""
    the_scope()
    stranger = restore_api.signing_key("h62-stranger", "a key the instance never held")
    now = int(time.time())
    claims = {"aud": restore_api.AUDIENCE, "scope": SCOPE, "iat": now - 5, "exp": now + 235, "jti": secrets.token_urlsafe(16)}
    foreign = jwt.encode(claims, stranger.private, algorithm="EdDSA", headers={"typ": restore_api.TICKET_TYP, "kid": kid})
    held = await send(instance, "GET", METRICS, authorization=bearer(a_ticket().value))
    assert held.status_code == 200, f"Barrier: a ticket of the held key opens the route: {held.status_code} {held.text}"
    assert instance.counted() == 0, "Barrier: nothing counted yet"

    response, events = await ask(instance, authorization=bearer(foreign))

    assert code_of(response) == (401, "panel_ticket_unknown_key"), f"a key the instance does not hold: {response.status_code} {response.text}"
    assert response.headers.get_list("www-authenticate") == ["Bearer"], f"a bearer challenge: {dict(response.headers)}"
    assert instance.counted() == 1, f"an unknown key proves nothing: it is counted once, as a refused credential: {instance.counted()}"
    lines = panel_lines(events)
    assert len(lines) == 1 and (lines[0].get("scope"), lines[0].get("outcome"), lines[0].get("reason")) == (SCOPE, "refused", "panel_ticket_unknown_key"), f"one refused line, reason unknown key: {lines}"
    assert len(str(lines[0].get("kid") or "")) <= 64, f"the kid is the caller's text, cut to 64 characters: {lines[0].get('kid')!r}"
    assert foreign not in repr(events) + response.text, "the ticket is not shown"


@pytest.mark.asyncio
async def test_a_registry_of_used_tickets_that_fails_is_the_scopes_503_and_no_figure(instance):
    """PM-024: ``ticket_registry.record`` raising ``TicketRegistryError`` (the file of used tickets is out of reach) for a
    ticket that verifies: ``503 panel_metrics_unavailable``, not counted, one ``unavailable`` line with reason ``registry``, no
    figure and no message of the failure in the answer."""
    the_scope()

    def unreachable(*_args: Any, **_kwargs: Any) -> bool:
        raise ticket_registry.TicketRegistryError("clm1canary-the-registry-of-the-test-is-out-of-reach")

    instance.monkeypatch.setattr(ticket_registry, "record", unreachable)
    ticket = a_ticket()

    response, events = await ask(instance, authorization=bearer(ticket.value))

    assert code_of(response) == (503, UNAVAILABLE_CODE), f"a registry that fails: {response.status_code} {response.text}"
    assert instance.counted() == 0, "an unusable registry is not a refused credential"
    lines = panel_lines(events)
    assert len(lines) == 1 and (lines[0].get("outcome"), lines[0].get("reason")) == ("unavailable", "registry"), f"one unavailable line, reason registry: {lines}"
    assert not (set(response.json()) & ANSWER_KEYS) and "clm1canary" not in response.text, f"no figure and no message of the failure: {response.text}"
    assert ticket.value not in repr(events) + response.text, "the ticket is not shown"


# =============================================================================
# PM-030..032: the shared limiter
# =============================================================================


@pytest.mark.asyncio
async def test_the_limiter_is_shared_with_the_other_scopes_and_closes_the_address_even_to_a_valid_ticket(instance):
    """PM-030: refused credentials count for the address across every panel scope: half sent to the status route, half to
    this one, reach ``PANEL_ATTEMPT_LIMIT``; then a VALID ticket gets ``429 panel_too_many_attempts`` with ``Retry-After``
    and its ``jti`` is not recorded: with the window open again the same ticket opens the route."""
    print_section("PM-030: the shared limiter")
    the_scope()
    ticket = a_ticket()
    for index in range(ATTEMPT_LIMIT):
        if index % 2:
            refused = await send(instance, "GET", METRICS, authorization=bearer(instance.status_token))
            assert code_of(refused) == (401, UNAUTHORIZED_CODE), f"refusal {index}: {refused.status_code} {refused.text}"
        else:
            refused = await send(instance, "GET", f"{API_V1_PREFIX}/panel/status", authorization=bearer("not-the-status-token"))
            assert code_of(refused) == (401, "panel_status_unauthorized"), f"refusal {index}: {refused.status_code} {refused.text}"
    assert instance.counted() == ATTEMPT_LIMIT, f"Barrier: the limit is reached by refusals of two scopes: {instance.counted()}"

    closed, events = await ask(instance, authorization=bearer(ticket.value))

    assert code_of(closed) == (429, TOO_MANY_CODE), f"a valid ticket from a closed address: {closed.status_code} {closed.text}"
    assert int(closed.headers.get("retry-after", "0")) >= 1, f"Retry-After: {dict(closed.headers)}"
    assert [line.get("outcome") for line in panel_lines(events)] == ["limited"], f"one limited line: {panel_lines(events)}"
    instance.new_limiter()
    reopened = await send(instance, "GET", METRICS, authorization=bearer(ticket.value))
    assert reopened.status_code == 200, f"the 429 did not use the ticket's jti: {reopened.status_code} {reopened.text}"


@pytest.mark.asyncio
async def test_signed_refusals_never_close_the_address(instance):
    """PM-031: more than the limit of signed refusals (wrong scope, expired, replayed) from one address leave the limiter
    at zero and a valid ticket still opens the route: a panel with a bad clock or a mix-up locks nobody out."""
    the_scope()
    spent = a_ticket()
    assert (await send(instance, "GET", METRICS, authorization=bearer(spent.value))).status_code == 200, "Barrier: the ticket works once"
    for index in range(ATTEMPT_LIMIT + 5):
        ticket = (a_ticket("status"), a_ticket(iat=int(time.time()) - 1000), spent)[index % 3]
        refused = await send(instance, "GET", METRICS, authorization=bearer(ticket.value))
        assert refused.status_code == 401 and code_of(refused)[1] != UNAUTHORIZED_CODE, f"refusal {index} is a signed one: {refused.status_code} {refused.text}"

    assert instance.counted() == 0, f"no signed refusal was counted: {instance.counted()}"
    opened = await send(instance, "GET", METRICS, authorization=bearer(a_ticket().value))
    assert opened.status_code == 200, f"a valid ticket still opens the route: {opened.status_code} {opened.text}"


# =============================================================================
# PM-040..044: the answer and its line
# =============================================================================


@pytest.mark.asyncio
async def test_the_answer_is_the_figures_of_the_instance_and_names_neither_who_nor_where(instance):
    """PM-040: 200, exactly the 15 keys, the figures of the instance the test made (counts, providers, files, jobs), the
    constant nulls, and nothing that names who or where: no canary name or email, no path of the data directory, no ticket,
    no static token, in the body or the headers."""
    the_scope()
    ticket = a_ticket()

    response = await send(instance, "GET", METRICS, authorization=bearer(ticket.value))

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    body = response.json()
    assert set(body) == ANSWER_KEYS, f"exactly the 15 keys: {sorted(set(body) ^ ANSWER_KEYS)}"
    figures = {name: body[name] for name in ("brokers_count", "transactions_count", "assets_count", "plugins_enabled", "database_mb", "uploads_mb", "price_refresh_errors_24h", "jobs_failed_24h", "market_data_credits_used", "market_data_credits_limit")}
    expected = {
        "brokers_count": service_cases.BROKERS,
        "transactions_count": service_cases.TRANSACTIONS,
        "assets_count": service_cases.ASSETS,
        "plugins_enabled": service_cases.PROVIDERS,
        "database_mb": service_cases.DATABASE_MB,
        "uploads_mb": service_cases.UPLOADS_MB,
        "price_refresh_errors_24h": service_cases.HAPPY_ERRORS,
        "jobs_failed_24h": service_cases.HAPPY_FAILED,
        "market_data_credits_used": None,
        "market_data_credits_limit": None,
    }
    assert figures == expected, f"the instance's figures:\n  expected {expected}\n  got      {figures}"
    assert response.headers.get("content-type", "").startswith("application/json")
    shown = response.text + repr(dict(response.headers))
    leaked = [word for word in (service_cases.CANARY, service_cases.USER_EMAIL, str(instance.root), str(instance.root.parent), ticket.value, ticket.jti, instance.status_token, instance.backup_token, instance.wake_token) if word in shown]
    assert leaked == [], f"the answer shows {len(leaked)} thing(s) it should not: {[word[:20] for word in leaked]}"
    assert all(set(item) == {"check_id", "severity"} for item in body["config_warnings"]), f"config_warnings items have exactly two keys: {body['config_warnings']}"


@pytest.mark.asyncio
async def test_the_accepted_call_writes_the_one_line_of_the_scope_and_never_the_ticket(instance):
    """PM-041: one ``Hosting panel request`` line: scope ``metrics``, ``GET``, the path without a query, outcome
    ``accepted``, credential ``ticket``, the ``kid`` and ``jti``; never the ticket, its signature or the header."""
    the_scope()
    ticket = a_ticket()

    response, events = await ask(instance, authorization=bearer(ticket.value), path=f"{METRICS}?canary=clm1query")

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    lines = panel_lines(events)
    assert len(lines) == 1, f"one line: {lines}"
    line = lines[0]
    assert (line.get("scope"), line.get("method"), line.get("path"), line.get("outcome"), line.get("credential"), line.get("kid"), line.get("jti")) == (SCOPE, "GET", METRICS, "accepted", "ticket", ticket.kid, ticket.jti), f"the line: {line}"
    shown = repr(events)
    assert ticket.value not in shown and ticket.value.split(".")[-1] not in shown and "clm1query" not in shown and "Authorization" not in shown, "never the ticket, its signature, the query or the header"


@pytest.mark.asyncio
async def test_a_call_is_never_user_activity(instance):
    """PM-042: a figures call (accepted or refused) leaves the activity record as it found it: no user request, nothing
    in flight afterwards, so the panel's polling never keeps a machine awake. Barrier: an ordinary API request does set
    the user's last request."""
    the_scope()
    assert instance.activity.last_user_request_at is None, "Precondition: a fresh record"

    accepted = await send(instance, "GET", METRICS, authorization=bearer(a_ticket().value))
    refused = await send(instance, "GET", METRICS)

    assert (accepted.status_code, refused.status_code) == (200, 401), f"{accepted.status_code} / {refused.status_code}"
    assert instance.activity.last_user_request_at is None and instance.activity.in_flight == 0, "the panel's call is not a visit"
    await send(instance, "GET", f"{API_V1_PREFIX}/auth/me")
    assert instance.activity.last_user_request_at is not None, "Barrier: an ordinary request is a visit, so the record does watch"


# =============================================================================
# PM-050..052: a measure that fails is a null in a 200
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("name", service_cases.SEAM_CASES)
async def test_a_measure_that_raises_is_a_null_in_a_200_never_a_500_and_never_its_message(instance, name):
    """PM-050: each measure of the service raising in turn: the route still answers 200 with 15 keys, the keys of that
    measure are null, and the text of the exception is not in the answer."""
    the_scope()
    metrics = importlib.import_module(service_cases.METRICS_MODULE)
    assert hasattr(metrics, name), f"CL-M1: metrics.{name} exists"
    instance.monkeypatch.setattr(metrics, name, service_cases.raising(name))

    with capture_logs():
        response = await send(instance, "GET", METRICS, authorization=bearer(a_ticket().value))

    assert response.status_code == 200, f"{name} raised: {response.status_code} {response.text}"
    body = response.json()
    assert set(body) == ANSWER_KEYS and [key for key in service_cases.SEAMS[name] if body[key] is not None] == [], f"the keys of {name} are null, all 15 present: {body}"
    assert f"boom-{name}" not in response.text and "Traceback" not in response.text, "the message of the failure stays in the log"


# =============================================================================
# PM-060..064: a blocked instance, the mode, an interrupted restore
# =============================================================================


@pytest.mark.asyncio
async def test_the_route_is_in_the_three_allowed_sets():
    """PM-060: ``get_panel_metrics`` is in ``ALLOWED_WHEN_BLOCKED`` and in ``ALLOWED_WHEN_AWAITING_RESTORE``, and
    ``ALLOWED_WHEN_RESTORE_INTERRUPTED`` is still that same object (so it is allowed there too)."""
    route = the_route()

    assert route in instance_block.ALLOWED_WHEN_BLOCKED, "allowed on a blocked instance"
    assert route in instance_block.ALLOWED_WHEN_AWAITING_RESTORE, "allowed while the instance awaits its restore"
    assert instance_block.ALLOWED_WHEN_RESTORE_INTERRUPTED is instance_block.ALLOWED_WHEN_AWAITING_RESTORE, "the interrupted set is the awaiting set"
    assert route in instance_block.ALLOWED_WHEN_RESTORE_INTERRUPTED, "allowed with an interrupted restore"


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [*STATE_CASES, pytest.param("restore-interrupted", id="restore-interrupted")])
async def test_in_every_state_a_valid_ticket_opens_the_figures_and_anyone_else_gets_the_refusals_of_every_day(instance, state):
    """PM-061: blocked, awaiting the restore, both, and with an interrupted restore: a valid ticket answers 200 with the 15
    keys; a replay, no credential, a static token and a ticket of another scope get ``panel_ticket_replayed``,
    ``panel_metrics_unauthorized`` (twice) and ``panel_ticket_wrong_scope``, exactly the answers of the normal state, never a
    423; without the keys the route is the 404 of every day. Barrier: the state is on."""
    print_section(f"PM-061: {state}")
    the_scope()
    if state == "restore-interrupted":
        instance.monkeypatch.setattr(restore_guard, "_interrupted", True)
        assert restore_guard.restore_interrupted(), "Barrier: the restore is interrupted"
    else:
        instance.switch(state)
        assert (instance_block.instance_blocked(), instance_block.awaiting_restore()) == (BLOCKED_VARIABLE in STATES[state], AWAIT_VARIABLE in STATES[state]), "Barrier: the state is on"
    spent = a_ticket()

    opened = await send(instance, "GET", METRICS, authorization=bearer(spent.value))
    answers = {
        "replay": code_of(await send(instance, "GET", METRICS, authorization=bearer(spent.value))),
        "nothing": code_of(await send(instance, "GET", METRICS)),
        "status-token": code_of(await send(instance, "GET", METRICS, authorization=bearer(instance.status_token))),
        "other-scope": code_of(await send(instance, "GET", METRICS, authorization=bearer(a_ticket("status").value))),
    }
    instance.monkeypatch.delenv(KEYS_VARIABLE)
    off = await send(instance, "GET", METRICS, authorization=bearer(a_ticket().value))

    assert opened.status_code == 200 and set(opened.json()) == ANSWER_KEYS, f"{state}: a valid ticket opens the figures: {opened.status_code} {opened.text}"
    expected = {"replay": (401, REPLAYED_CODE), "nothing": (401, UNAUTHORIZED_CODE), "status-token": (401, UNAUTHORIZED_CODE), "other-scope": (401, WRONG_SCOPE_CODE)}
    assert answers == expected, f"{state}: the refusals are those of the normal state, never a 423:\n  expected {expected}\n  got      {answers}"
    assert (off.status_code, off.json()) == OFF_ANSWER, f"{state}: without the keys, the 404 of a path that does not exist: {off.status_code} {off.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["normal", *STATE_CASES, pytest.param("restore-interrupted", id="restore-interrupted")])
async def test_a_metrics_call_never_creates_the_instance_key_file(instance, state):
    """PM-062 (the route is read-only): an instance with a stored plugin secret, no key from the environment and no
    ``secrets/instance.key`` (the state in which counting the unreadable secrets generated the key): a valid ticket answers
    200 and the key file, with its folder, is still not there, in the normal state, blocked, awaiting the restore, both, and
    with an interrupted restore."""
    print_section(f"PM-062: no key file made, {state}")
    the_scope()
    if state == "restore-interrupted":
        instance.monkeypatch.setattr(restore_guard, "_interrupted", True)
        assert restore_guard.restore_interrupted(), "Barrier: the restore is interrupted"
    elif state != "normal":
        instance.switch(state)
        assert (instance_block.instance_blocked(), instance_block.awaiting_restore()) == (BLOCKED_VARIABLE in STATES[state], AWAIT_VARIABLE in STATES[state]), "Barrier: the state is on"
    instance.session.add(service_cases.stored_secret())
    await instance.session.commit()
    path = instance_key_path()
    assert path.parent.parent == instance.root, f"Barrier: the key file belongs to this test's data directory: {path}"
    assert not path.exists() and not path.parent.exists(), "Barrier: no key file (nor its folder) before the call"

    response = await send(instance, "GET", METRICS, authorization=bearer(a_ticket().value))

    assert response.status_code == 200 and set(response.json()) == ANSWER_KEYS, f"{state}: the figures are answered: {response.status_code} {response.text}"
    assert not path.exists(), f"{state}: the metrics call generated the instance key file {path}"
    assert not path.parent.exists(), f"{state}: the metrics call created the folder of the key file {path.parent}"
