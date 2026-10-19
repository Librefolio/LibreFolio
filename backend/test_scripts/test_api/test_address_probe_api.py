"""
Address Probe API — release 1.3, workstream A, lot A6a (plan phase01Accounts, A6.1 «Verifica dell'indirizzo», D-A3).

When an administrator edits the server address in the Invite dialog, the browser checks that THIS instance answers at
that address: it asks its own instance for a nonce, then sends the nonce to the edited address; only the instance that
issued it answers ``match``. The nonce is signed with a key derived from the instance key and stored nowhere
(``services/accounts/address_probe.py``, pinned by ``test_services/test_address_probe.py``). Two routes:

1. ``POST /users/address-probe``, administrators only (``require_admin``): 200 with exactly ``{nonce, expires_at}`` —
   ``nonce`` 75 base64url characters; ``expires_at`` a timestamp with an explicit UTC offset, 120 s after the issue, the
   very instant the nonce carries —; 401 without a valid session, 403 for a regular user. Every call, a new nonce.
2. ``GET /auth/address-probe?nonce=…``, public: 200 with the body exactly ``{"match": <bool>}``, the header
   ``Access-Control-Allow-Origin: *`` (set by the route itself, once) and ``Cache-Control: no-store`` on every answer,
   true or false: a page on another origin reads a «no» only with the header too. ``match`` is true for a nonce of this
   instance not yet expired, as many times as it is asked; false for anything else — altered, another instance's,
   expired, empty, garbage, oversized (still 200, never 422). A session cookie, valid or not, changes nothing.
3. H-19, in process: when the instance key cannot be used, ``POST /users/address-probe`` answers 503 and issues
   nothing. ``derive_key`` raises ``InstanceKeyError`` then: at runtime, once a generated ``secrets/instance.key`` goes
   bad or loses its permissions (a configured key that cannot be used already stops the start). The body is exactly
   ``{"detail": {"error_code": "INSTANCE_KEY_UNAVAILABLE", "message": <the message below>}, "request_id": <the answer's
   X-Request-Id>}`` (H-60: a 5xx carries its request's id; the route raises ``from None``, so no ``error_type``), with
   the message «The instance key cannot be used: see the configuration checks» — no nonce and no ``expires_at``
   anywhere —, and the module logger of ``users.py`` writes one warning, «Address probe: the instance key cannot be
   used, no nonce issued», with the administrator's ``admin_id``, neither the reason nor exception info. The
   server-error handler writes no line of its own (H-60): that warning, written inside the ``except``, already reported
   the failure. Red until H-19: the route let the error out, a plain 500 with its traceback in the server log (in
   process, the error itself reaches the test); red until H-60: no ``X-Request-Id`` on the answer, no ``request_id`` in
   its body. The public check already tolerates that state: 200 ``{"match": false}`` with both headers, even for a
   nonce this instance issued. Both cases replace the probe module's ``derive_key`` with ``monkeypatch`` for the test
   only: no key file is touched, and the lane's server is not asked meanwhile.

The cross-origin promise is checked where it can break: on the lane's server, which runs the whole middleware stack of
``main.py``, its global ``CORSMiddleware`` included (``allow_credentials=True``, no allowed origin). A GET carrying
``Origin: https://elsewhere.example`` must still get ``Access-Control-Allow-Origin: *``.

Where each case runs, and why:

- **On the lane's server**: the routes as a browser meets them. The sessions are the fixture users of
  ``populate_mock_data.py`` (the api setup runs ``db populate``), ``e2e_test_admin`` and ``e2e_test_user``, signed in
  once for the module; their roles are checked, never changed. Every request comes from an empty client and carries at
  most one cookie, explicitly.
- **Minted in this process**: a test lane configures no instance key (``configure_test_runtime`` removes them), so this
  process and the lane's server derive from the same generated ``<data dir>/secrets/instance.key``. A nonce issued here
  with ``issue_probe_nonce`` under that key is accepted by the lane's server — the nonce is stateless, any process of the
  instance verifies it: that is the control —; issued ten minutes ago, or under another instance's key, it is refused.
- **In process**: «another instance» with the routes of both sides. The app of ``main.py`` runs through
  ``httpx.ASGITransport`` (its lifespan does not run) on the lane's database, signing its own session cookies, and
  ``LIBREFOLIO_INSTANCE_KEY`` is switched between the issue and the check with ``monkeypatch``.

A key is set in this process only for a ``with`` block that never asks the lane's server: without a shared backend,
``_TestingServerManager`` runs that server in this very process, on this environment.

Write-scoped, the ``api`` category's default: no setting, no global row, nothing stored for a nonce. The only write is
the one of a login (``record_login_and_maybe_show_popup``: the login counters of ``e2e_test_admin`` and
``e2e_test_user``), which no unit asserts on. Nothing to clean up.

Red until A6a: ``POST /users/address-probe`` falls on the path of ``PATCH /users/{user_id}`` (405);
``GET /auth/address-probe`` on the SPA catch-all of ``main.py`` (404, HTML, no CORS header); the tests that mint nonces
in this process do not find ``backend.app.services.accounts.address_probe`` (``ModuleNotFoundError``).
"""

import base64
import contextlib
import importlib
import logging
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import ModuleType
from typing import Any, Optional
from uuid import uuid4

import httpx
import pytest
import structlog
from fastapi import FastAPI
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import users as users_api
from backend.app.config import API_V1_PREFIX, get_settings, is_test_mode
from backend.app.services.platform.instance_key import InstanceKeyError
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME

ISSUE_PATH = "/users/address-probe"
PROBE_PATH = "/auth/address-probe"
#: Imported only by the tests that mint nonces in this process: until A6a only they fail on it, the others on their route.
PROBE_MODULE = "backend.app.services.accounts.address_probe"

#: The fixture users of populate_mock_data.py: signed in, never changed.
E2E_ADMIN = ("e2e_test_admin", "E2eAdminPass123!")
E2E_USER = ("e2e_test_user", "E2eTestPass123!")

TTL_SECONDS = 120
RANDOM_BYTES = 16
EXPIRY_BYTES = 8
RAW_LENGTH = 56
NONCE_SHAPE = re.compile(r"[A-Za-z0-9_-]{75}")
FOREIGN_ORIGIN = "https://elsewhere.example"
#: How long before the check the expired nonce is issued: expired eight minutes ago, far from any clock jitter.
EXPIRED_AGO_SECONDS = 600

KEY_VARIABLE = "LIBREFOLIO_INSTANCE_KEY"
KEY_FILE_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_FILE"
#: Two instance keys of this test, at least 32 characters (instance_key.py); the lane's own key is generated, random.
KEY_A = "address-probe-api-instance-key-A-0123456789"
KEY_B = "address-probe-api-instance-key-B-0123456789"


# =============================================================================
# The nonce, the answers
# =============================================================================


def _b64(raw: bytes) -> str:
    """base64url without padding, as a nonce is written."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    """The bytes of a base64url text without padding."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _with_bit_flipped(nonce: str, byte_index: int) -> str:
    """The nonce with the lowest bit of one of its 56 bytes flipped, spelled canonically: a well-formed forgery."""
    raw = bytearray(_unb64(nonce))
    raw[byte_index] ^= 0x01
    return _b64(bytes(raw))


def _expiry_of(nonce: str) -> int:
    """The expiry a nonce carries: whole unix seconds, the 8 bytes big-endian after the 16 random ones."""
    raw = _unb64(nonce)
    assert len(raw) == RAW_LENGTH, f"a nonce holds {RAW_LENGTH} bytes, not {len(raw)}: {nonce!r}"
    return int.from_bytes(raw[RANDOM_BYTES : RANDOM_BYTES + EXPIRY_BYTES], "big")


def _answer(response: httpx.Response) -> tuple[int, Any]:
    """What a client is told: the status code and the JSON body (the text when it is not JSON)."""
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


def _utc_instant(text: Any) -> Optional[datetime]:
    """An API timestamp with an explicit UTC offset (``Z`` or ``+00:00``) as an aware datetime; None for anything else,
    a naive timestamp included: a browser would read it in its own time zone."""
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.utcoffset() == timedelta(0) else None


def _cache_directives(response: httpx.Response) -> set[str]:
    """The directives of the response's Cache-Control, lower-cased."""
    return {directive.strip().lower() for directive in response.headers.get("cache-control", "").split(",") if directive.strip()}


def _probe_violations(response: httpx.Response, expected: bool) -> list[str]:
    """Why a probe answer is not 200 ``{"match": expected}`` with ``Access-Control-Allow-Origin: *`` (once) and
    ``Cache-Control: no-store``: empty when it is."""
    violations: list[str] = []
    status, body = _answer(response)
    if status != 200:
        violations.append(f"status {status}")
    if not (isinstance(body, dict) and body == {"match": expected} and isinstance(body["match"], bool)):
        violations.append(f"body {body!r}")
    origins = response.headers.get_list("access-control-allow-origin")
    if origins != ["*"]:
        violations.append(f"Access-Control-Allow-Origin {origins!r}")
    if "no-store" not in _cache_directives(response):
        violations.append(f"Cache-Control {response.headers.get('cache-control')!r}")
    return violations


def _assert_probe(response: httpx.Response, expected: bool, case: str) -> None:
    """The whole answer of the probe, not only its verdict: status, exact body, the CORS header, the cache header."""
    violations = _probe_violations(response, expected)
    assert not violations, f"GET {PROBE_PATH}, {case}: expected 200 {{'match': {expected}}} with Access-Control-Allow-Origin: * (once) and Cache-Control: no-store; wrong: {'; '.join(violations)}"


def _issued(response: httpx.Response, where: str) -> str:
    """The nonce of the administrator's route, its answer checked first: 200 with exactly {nonce, expires_at}."""
    status, body = _answer(response)
    assert status == 200, f"POST {ISSUE_PATH} as an administrator ({where}) must issue a nonce: {status} {body!r}"
    assert isinstance(body, dict) and set(body) == {"nonce", "expires_at"}, f"POST {ISSUE_PATH} ({where}) answers {{nonce, expires_at}} and nothing else: {body!r}"
    nonce = body["nonce"]
    assert isinstance(nonce, str) and NONCE_SHAPE.fullmatch(nonce), f"the nonce ({where}) is 75 base64url characters without padding: {nonce!r}"
    return nonce


# =============================================================================
# Sessions
# =============================================================================


def _cookie_header(value: str) -> dict[str, str]:
    """A Cookie header carrying this session cookie, and nothing else."""
    return {"Cookie": f"{COOKIE}={value}"}


def _forged_session() -> dict[str, str]:
    """A session cookie no server ever issued."""
    return _cookie_header(f"forged-{uuid4().hex}")


def _session_cookie(response: httpx.Response) -> Optional[str]:
    """The value the response's Set-Cookie gives the session cookie, found by name; None when it sets none."""
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == COOKIE and value:
            return value
    return None


def _session_of(login: httpx.Response, username: str, *, superuser: bool) -> dict[str, str]:
    """The Cookie header of the session a login of a fixture user opened, its role checked first: this test changes none."""
    status, body = _answer(login)
    assert status == 200, f"Setup: signing in as {username} failed: {status} {body!r} — the api setup (db populate) creates the fixture users"
    user = body.get("user") if isinstance(body, dict) else None
    assert isinstance(user, dict) and user.get("is_superuser") is superuser, f"Precondition: {username} must {'' if superuser else 'not '}be an administrator, as db populate makes it; this test never changes a role: {body!r}"
    value = _session_cookie(login)
    assert value, f"Setup: the login of {username} set no {COOKIE} cookie: {login.headers.get_list('set-cookie')}"
    return _cookie_header(value)


def _sign_in_on_lane(credentials: tuple[str, str], *, superuser: bool) -> dict[str, str]:
    """A fixture user signed in on the lane's server: the Cookie header of its session."""
    username, password = credentials
    login = httpx.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    return _session_of(login, username, superuser=superuser)


@dataclass(frozen=True)
class LaneSessions:
    """The Cookie headers of the fixture administrator and of the fixture regular user, on the lane's server."""

    admin: dict[str, str]
    user: dict[str, str]


# =============================================================================
# The lane's server, the app in process, the instance key of this process
# =============================================================================


@pytest.fixture(scope="module")
def test_server():
    """The lane's server: the runner's shared backend, or one started in this process (_TestingServerManager)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest.fixture(scope="module")
def lane_sessions(test_server) -> LaneSessions:
    """``e2e_test_admin`` and ``e2e_test_user`` signed in on the lane's server, once for the module."""
    return LaneSessions(admin=_sign_in_on_lane(E2E_ADMIN, superuser=True), user=_sign_in_on_lane(E2E_USER, superuser=False))


async def _lane(method: str, path: str, *, headers: Optional[dict[str, str]] = None, params: Optional[dict[str, str]] = None) -> httpx.Response:
    """``method`` ``/api/v1<path>`` on the lane's server, from an empty client: only ``headers`` decide what is sent."""
    async with httpx.AsyncClient() as client:
        return await client.request(method, f"{API_BASE}{path}", headers=headers or {}, params=params, timeout=TIMEOUT)


async def _probe_on_lane(nonce: str, headers: Optional[dict[str, str]] = None) -> httpx.Response:
    """GET /auth/address-probe?nonce=… on the lane's server."""
    return await _lane("GET", PROBE_PATH, headers=headers, params={"nonce": nonce})


async def _issue_on_lane(admin: dict[str, str]) -> str:
    """A nonce from the administrator's route of the lane's server."""
    return _issued(await _lane("POST", ISSUE_PATH, headers=admin), "the lane's server")


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """The app the lane's server runs, in this process, on the lane's database: test mode, or nothing runs."""
    assert is_test_mode(), "Precondition: test mode, so that the app in process reads the lane's database and derives from the lane's data directory"
    from backend.app.main import app as main_app  # noqa: PLC0415 — the server's own app, imported only by the fixture that needs it

    return main_app


async def _in_process(app: FastAPI, method: str, path: str, *, headers: Optional[dict[str, str]] = None, params: Optional[dict[str, str]] = None, json: Any = None) -> httpx.Response:
    """``method`` ``/api/v1<path>`` on the app in process, from a client of its own: a session travels only in ``headers``."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://librefolio.test") as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", headers=headers or {}, params=params, json=json, timeout=TIMEOUT)


async def _probe_in_process(app: FastAPI, nonce: str) -> httpx.Response:
    """GET /auth/address-probe?nonce=… on the app in process."""
    return await _in_process(app, "GET", PROBE_PATH, params={"nonce": nonce})


@contextlib.contextmanager
def _instance_key(monkeypatch: pytest.MonkeyPatch, key: Optional[str]) -> Iterator[None]:
    """In this process, for the block only: the instance key ``key``, or the lane's own for None (none configured: the
    generated key file of the lane's data directory). Never ask the lane's server inside the block."""
    with monkeypatch.context() as patched:
        patched.delenv(KEY_FILE_VARIABLE, raising=False)
        if key is None:
            patched.delenv(KEY_VARIABLE, raising=False)
        else:
            patched.setenv(KEY_VARIABLE, key)
        yield


def _address_probe() -> ModuleType:
    """The module under test, imported here and not at the top: until A6a only the tests that mint nonces fail on it."""
    return importlib.import_module(PROBE_MODULE)


def _mint(monkeypatch: pytest.MonkeyPatch, *, key: Optional[str], now: Optional[float] = None) -> str:
    """A nonce issued in this process by issue_probe_nonce: under ``key``, or under the lane's own key for None."""
    assert is_test_mode(), "Precondition: test mode, so that this process derives from the lane's data directory, never from the production one"
    probe = _address_probe()
    with _instance_key(monkeypatch, key):
        nonce, _ = probe.issue_probe_nonce(now=now)
    return nonce


# =============================================================================
# 1. POST /users/address-probe — the administrator's nonce
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("forged", [False, True], ids=["no-cookie", "forged-session-cookie"])
async def test_issue_refuses_a_caller_without_a_valid_session(test_server, forged):
    """AP-API-01: without a valid session, 401 and no nonce."""
    print_section(f"AP-API-01: POST {ISSUE_PATH} without a valid session")
    status, body = _answer(await _lane("POST", ISSUE_PATH, headers=_forged_session() if forged else None))
    assert status == 401, f"POST {ISSUE_PATH} without a valid session must answer 401: {status} {body!r}"
    print_success(f"{status} {body!r}")


@pytest.mark.asyncio
async def test_issue_refuses_a_regular_user(lane_sessions):
    """AP-API-02: a signed-in regular user gets 403: the nonce is for administrators."""
    print_section(f"AP-API-02: POST {ISSUE_PATH} as a regular user")
    status, body = _answer(await _lane("POST", ISSUE_PATH, headers=lane_sessions.user))
    assert status == 403, f"POST {ISSUE_PATH} as {E2E_USER[0]}, a regular user, must answer 403: {status} {body!r}"
    print_success(f"{status} {body!r}")


@pytest.mark.asyncio
async def test_issue_gives_the_administrator_a_new_nonce_and_its_expiry(lane_sessions):
    """AP-API-03: 200 with exactly {nonce, expires_at}: 75 base64url characters, and an explicit-UTC timestamp 120 s after
    the issue, the instant the nonce itself carries. Every call, a new nonce."""
    print_section(f"AP-API-03: POST {ISSUE_PATH} as the administrator")
    before = time.time()
    response = await _lane("POST", ISSUE_PATH, headers=lane_sessions.admin)
    after = time.time()
    nonce = _issued(response, "the lane's server")
    raw_expires_at = response.json()["expires_at"]
    expires_at = _utc_instant(raw_expires_at)
    assert expires_at is not None, f"expires_at must be a timestamp with an explicit UTC offset (Z or +00:00): {raw_expires_at!r}"
    assert before + TTL_SECONDS - 1 < expires_at.timestamp() < after + TTL_SECONDS + 1, f"issued between {before:.3f} and {after:.3f}: expires_at must be {TTL_SECONDS} s later, not {expires_at.isoformat()}"
    expiry = _expiry_of(nonce)
    assert abs(expires_at.timestamp() - expiry) < 1, f"expires_at ({expires_at.isoformat()}) must be the expiry the nonce carries ({expiry}), to the second"
    again = await _issue_on_lane(lane_sessions.admin)
    assert again != nonce, "every call issues a new nonce"
    print_success(f"{nonce[:12]}… expires at {raw_expires_at}")


# =============================================================================
# 2. GET /auth/address-probe — the public check, on the lane's server
# =============================================================================


@pytest.mark.asyncio
async def test_probe_matches_a_nonce_the_administrator_was_issued(lane_sessions):
    """AP-API-04: anyone, without a session, gets ``{"match": true}`` for a nonce of this instance — twice: nothing is
    consumed, the check is stateless (and the shared backend's workers may answer the issue and the check apart)."""
    print_section(f"AP-API-04: GET {PROBE_PATH} with an issued nonce")
    nonce = await _issue_on_lane(lane_sessions.admin)
    _assert_probe(await _probe_on_lane(nonce), True, "a nonce the administrator's route just issued, asked without a session")
    _assert_probe(await _probe_on_lane(nonce), True, "the same nonce asked again")
    print_success("match: true, twice, with both headers")


#: Texts no instance issued: each is asked anonymously and must get the whole «no», headers included.
NOT_ISSUED = [
    pytest.param("", id="empty"),
    pytest.param("not-a-nonce", id="garbage"),
    pytest.param("A" * 75, id="nonce-shape-zero-bytes"),
    pytest.param(_b64(bytes(range(RAW_LENGTH))), id="nonce-shape-arbitrary-bytes"),
    pytest.param("\u00e9" * 75, id="non-ascii"),
    pytest.param("A" * 257, id="257-characters"),
    pytest.param("A" * 4096, id="4096-characters"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", NOT_ISSUED)
async def test_probe_answers_anyone_no_for_what_no_instance_issued(test_server, text):
    """AP-API-05: public, and 200 ``{"match": false}`` with both headers; an oversized text is no exception (still 200,
    never 422). The positive half is AP-API-04: a route that always said no fails there."""
    print_section(f"AP-API-05: GET {PROBE_PATH} with {len(text)} characters no instance issued")
    _assert_probe(await _probe_on_lane(text), False, f"{len(text)} characters no instance issued, asked without a session")
    print_success("match: false, with both headers")


#: Alterations of a nonce the lane issued. The bit flips keep a well-formed nonce, and the one in the expiry keeps it in
#: the future (its lowest bit: one second either way), so that only the MAC can refuse them.
ALTERATIONS = [
    pytest.param(lambda nonce: _with_bit_flipped(nonce, 0), id="bit-flipped-in-the-random-part"),
    pytest.param(lambda nonce: _with_bit_flipped(nonce, RANDOM_BYTES + EXPIRY_BYTES - 1), id="bit-flipped-in-the-expiry"),
    pytest.param(lambda nonce: _with_bit_flipped(nonce, RAW_LENGTH - 1), id="bit-flipped-in-the-mac"),
    pytest.param(lambda nonce: nonce[:-1], id="truncated"),
    pytest.param(lambda nonce: nonce + "A", id="extended"),
    pytest.param(lambda nonce: nonce + "=", id="padding-added"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("alter", ALTERATIONS)
async def test_probe_answers_no_to_an_altered_nonce(lane_sessions, alter: Callable[[str], str]):
    """AP-API-06: an altered nonce is a forgery: ``{"match": false}``, while the original still matches."""
    print_section(f"AP-API-06: GET {PROBE_PATH} with an altered nonce")
    nonce = await _issue_on_lane(lane_sessions.admin)
    altered = alter(nonce)
    assert altered != nonce, "Barrier: the alteration changes the nonce"
    _assert_probe(await _probe_on_lane(nonce), True, "Barrier: the original nonce")
    _assert_probe(await _probe_on_lane(altered), False, f"the nonce altered: {altered!r}")
    print_success("the original matches, the altered one does not")


@pytest.mark.asyncio
@pytest.mark.parametrize("session", ["no-cookie", "administrator", "regular-user", "forged-cookie"])
async def test_probe_answers_the_same_whatever_the_session_cookie(lane_sessions, session):
    """AP-API-07: the check is public and reads no session: a valid one, a forged one or none, the same answers."""
    print_section(f"AP-API-07: GET {PROBE_PATH} with {session}")
    cookie = {"no-cookie": None, "administrator": lane_sessions.admin, "regular-user": lane_sessions.user, "forged-cookie": _forged_session()}[session]
    nonce = await _issue_on_lane(lane_sessions.admin)
    _assert_probe(await _probe_on_lane(nonce, cookie), True, f"an issued nonce, with {session}")
    _assert_probe(await _probe_on_lane(_with_bit_flipped(nonce, RAW_LENGTH - 1), cookie), False, f"an altered nonce, with {session}")
    print_success(f"{session}: match true for the nonce, false for its forgery")


@pytest.mark.asyncio
async def test_probe_answer_is_readable_from_another_origin(lane_sessions):
    """AP-API-08: the browser checks the edited address from the app's own origin, so the check is cross-origin. On the
    lane's server, through the global CORSMiddleware (credentials allowed, no origin allowed), a GET from
    https://elsewhere.example still gets ``Access-Control-Allow-Origin: *``, on a «no» as on a «yes». The «no» comes
    first: it needs no nonce, so this red is the header's own."""
    print_section(f"AP-API-08: GET {PROBE_PATH} from {FOREIGN_ORIGIN}")
    origin = {"Origin": FOREIGN_ORIGIN}
    _assert_probe(await _probe_on_lane("", origin), False, f"an empty nonce, Origin: {FOREIGN_ORIGIN}")
    nonce = await _issue_on_lane(lane_sessions.admin)
    _assert_probe(await _probe_on_lane(nonce, origin), True, f"an issued nonce, Origin: {FOREIGN_ORIGIN}")
    _assert_probe(await _probe_on_lane(_with_bit_flipped(nonce, RAW_LENGTH - 1), origin), False, f"an altered nonce, Origin: {FOREIGN_ORIGIN}")
    print_success("Access-Control-Allow-Origin: * survives the CORSMiddleware, on yes and on no")


# =============================================================================
# 3. Nonces minted in this process, checked by the lane's server
# =============================================================================


@pytest.mark.asyncio
async def test_the_lane_answers_no_to_its_own_nonce_once_expired(test_server, monkeypatch):
    """AP-API-09: under the lane's own key, a nonce minted now matches (the control: stateless, any process of the
    instance verifies it); minted ten minutes ago, it has expired: ``{"match": false}``."""
    print_section("AP-API-09: an expired nonce of the lane's own key")
    fresh = _mint(monkeypatch, key=None)
    expired = _mint(monkeypatch, key=None, now=time.time() - EXPIRED_AGO_SECONDS)
    _assert_probe(await _probe_on_lane(fresh), True, "Control: minted now in this process, under the lane's own key (none is configured in a test lane: this process and the lane's server derive from the same <data dir>/secrets/instance.key)")
    _assert_probe(await _probe_on_lane(expired), False, f"minted {EXPIRED_AGO_SECONDS} s ago under the lane's own key: expired")
    print_success("fresh: match; expired: no match")


@pytest.mark.asyncio
async def test_the_lane_answers_no_to_a_nonce_of_another_instance(test_server, monkeypatch):
    """AP-API-10: a nonce minted under another instance key is refused by the lane's server; one under the lane's own
    key, the control, matches."""
    print_section("AP-API-10: a nonce of another instance, on the lane's server")
    own = _mint(monkeypatch, key=None)
    foreign = _mint(monkeypatch, key=KEY_B)
    _assert_probe(await _probe_on_lane(own), True, "Control: minted in this process under the lane's own key (the same generated key file as the lane's server)")
    _assert_probe(await _probe_on_lane(foreign), False, "minted under another instance's key (LIBREFOLIO_INSTANCE_KEY set in this process, for the issue only)")
    print_success("own key: match; another instance's key: no match")


# =============================================================================
# 4. Another instance, both routes, in process
# =============================================================================


@pytest.mark.asyncio
async def test_another_instance_answers_no_in_process(app, monkeypatch):
    """AP-API-11: the same app with its instance key switched is another instance. A nonce from the administrator's
    route under key A is refused under key B and matches under A again; the same the other way round."""
    print_section("AP-API-11: another instance, in process, both routes")
    login = await _in_process(app, "POST", "/auth/login", json={"username": E2E_ADMIN[0], "password": E2E_ADMIN[1]})
    admin = _session_of(login, E2E_ADMIN[0], superuser=True)
    with _instance_key(monkeypatch, KEY_A):
        nonce_a = _issued(await _in_process(app, "POST", ISSUE_PATH, headers=admin), "in process, instance A")
    with _instance_key(monkeypatch, KEY_B):
        _assert_probe(await _probe_in_process(app, nonce_a), False, "in process, instance B asked a nonce of instance A")
        nonce_b = _issued(await _in_process(app, "POST", ISSUE_PATH, headers=admin), "in process, instance B")
        _assert_probe(await _probe_in_process(app, nonce_b), True, "in process, instance B asked its own nonce")
    with _instance_key(monkeypatch, KEY_A):
        _assert_probe(await _probe_in_process(app, nonce_a), True, "in process, instance A asked its own nonce again: the «no» came from the key, from nothing else")
        _assert_probe(await _probe_in_process(app, nonce_b), False, "in process, instance A asked a nonce of instance B")
    print_success("each instance matches its own nonces only")


# =============================================================================
# 5. An instance key that cannot be used (H-19), in process
# =============================================================================

#: H-19: the whole ``detail`` of the administrator's route when the instance key cannot be used, and its one warning.
UNAVAILABLE_DETAIL = {"error_code": "INSTANCE_KEY_UNAVAILABLE", "message": "The instance key cannot be used: see the configuration checks"}
UNAVAILABLE_WARNING = "Address probe: the instance key cannot be used, no nonce issued"
#: Logged through the module logger of users.py first, inside the capture: a capture that sees nothing proves nothing.
LOG_CANARY = "AP-API-12 canary: the module logger of users.py reaches the capture"
#: The reason the stand-in of derive_key gives, worded as H's errors word an unreadable key file. The answer and the
#: warning are pinned exactly, so neither can carry it.
UNUSABLE_KEY_REASON = "/srv/librefolio-ap-api-12/secrets/instance.key: the instance key cannot be reached (Permission denied), raised by this test"
#: H-60: the request id every answer of the app carries in X-Request-Id, secrets.token_hex(8); and the lines of the
#: server-error handler and of the unhandled-error fallback, none of which a failure the route already logged gets.
REQUEST_ID_SHAPE = re.compile(r"[0-9a-f]{16}")
SERVER_ERROR_LINES = ("Request failed", "Request answered a server error", "Unhandled error")


@contextlib.contextmanager
def _writes_warnings(logger_name: str) -> Iterator[None]:
    """For the block, the stdlib logger ``logger_name`` writes warnings, whatever the lane's LOG_LEVEL: H-60's logging
    wrapper marks the failure a warning reports only when its logger writes warnings. Its level restored after."""
    stdlib_logger = logging.getLogger(logger_name)
    before = stdlib_logger.level
    stdlib_logger.setLevel(min(stdlib_logger.getEffectiveLevel(), logging.WARNING))
    try:
        yield
    finally:
        stdlib_logger.setLevel(before)


def _make_the_instance_key_unusable(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Until the test ends, in this process: the probe module's ``derive_key`` raises ``InstanceKeyError``, as the real
    one does once a generated ``secrets/instance.key`` goes bad or loses its permissions. No key file is touched. Never
    ask the lane's server meanwhile: without a shared backend, it runs in this very process. Returns the purposes the
    stand-in is asked for, so that a test can prove the key was asked."""
    asked: list[str] = []

    def unusable(purpose: str, length: int = 32) -> bytes:
        asked.append(purpose)
        raise InstanceKeyError(UNUSABLE_KEY_REASON)

    monkeypatch.setattr(_address_probe(), "derive_key", unusable)
    return asked


async def _admin_in_process(app: FastAPI) -> tuple[dict[str, str], int]:
    """``e2e_test_admin`` signed in on the app in process: the Cookie header of its session, and its id."""
    login = await _in_process(app, "POST", "/auth/login", json={"username": E2E_ADMIN[0], "password": E2E_ADMIN[1]})
    admin = _session_of(login, E2E_ADMIN[0], superuser=True)
    admin_id = login.json()["user"].get("id")
    assert isinstance(admin_id, int), f"Setup: the login of {E2E_ADMIN[0]} must answer its id: {login.json()!r}"
    return admin, admin_id


@pytest.mark.asyncio
async def test_issue_answers_503_when_the_instance_key_cannot_be_used(app, monkeypatch):
    """AP-API-12 (H-19, H-60), in process: ``derive_key`` raising ``InstanceKeyError``, the administrator's route answers
    503 with the body exactly ``{"detail": UNAVAILABLE_DETAIL, "request_id": <the answer's X-Request-Id>}`` — no nonce,
    no expires_at, and no ``error_type``: the route raises ``from None``, so no cause is visible (H-60) — and the module
    logger of users.py writes exactly one warning, «Address probe: the instance key cannot be used, no nonce issued»,
    with the administrator's ``admin_id`` and nothing else: no reason, no exception info. Nothing at error level, and no
    line of the server-error handler (H-60): the warning, written inside the ``except``, already reported the failure —
    the users.py logger writes warnings for the request, whatever the lane's LOG_LEVEL, as that report needs.

    The traceback in a server log is uvicorn's, written when an exception leaves the app. In process, ``_in_process``
    (httpx's default ``raise_app_exceptions``) raises that exception in the test instead: red until H-19, turned into
    a failure that says so. Barriers first: the same call with the key usable issues a nonce (the session and the route
    work, so a 503 can only come from the key); a canary through the module logger of users.py reaches the capture."""
    print_section(f"AP-API-12: POST {ISSUE_PATH} when the instance key cannot be used")
    admin, admin_id = await _admin_in_process(app)
    with _instance_key(monkeypatch, KEY_A):
        _issued(await _in_process(app, "POST", ISSUE_PATH, headers=admin), "in process, Barrier: the same call with the instance key usable")
        asked = _make_the_instance_key_unusable(monkeypatch)
        with capture_logs(processors=[structlog.stdlib.add_logger_name]) as events, _writes_warnings(users_api.__name__):
            users_api.logger.info(LOG_CANARY)
            try:
                response = await _in_process(app, "POST", ISSUE_PATH, headers=admin)
            except InstanceKeyError as escaped:
                pytest.fail(f"POST {ISSUE_PATH}, the instance key unusable: {type(escaped).__name__} left the app ({escaped}) — a client gets a plain 500 and the server logs its traceback; expected 503 with detail {UNAVAILABLE_DETAIL!r}")
    assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the module logger of users.py does not reach capture_logs, so what this test reads of the log proves nothing: {events!r}"
    assert asked, "Precondition: the route asked the probe's derive_key for its key, so the answer comes from a key that cannot be used"
    request_id = response.headers.get("x-request-id")
    assert isinstance(request_id, str) and REQUEST_ID_SHAPE.fullmatch(request_id), f"H-60: every answer of the app carries its request id in X-Request-Id, 16 lowercase hex characters: {request_id!r}"
    status, body = _answer(response)
    expected_body = {"detail": UNAVAILABLE_DETAIL, "request_id": request_id}
    assert (status, body) == (503, expected_body), f"POST {ISSUE_PATH} as an administrator, the instance key unusable: expected 503 with the body exactly {expected_body!r} — no nonce, no expires_at, no error_type (raised from None) —, got {status} {body!r}"
    expected = {"event": UNAVAILABLE_WARNING, "admin_id": admin_id, "logger": users_api.__name__, "log_level": "warning"}
    logged = [event for event in events if event.get("event") == UNAVAILABLE_WARNING]
    assert logged == [expected], f"exactly one warning {expected!r}: the administrator's id, neither the reason nor exception info; logged: {logged!r}"
    loud = [event for event in events if event.get("log_level") in ("error", "critical") or event.get("exc_info") or event.get("stack_info")]
    assert loud == [], f"nothing at error level, no exception info, no stack while the route answers: {loud!r}"
    handler_lines = [event for event in events if event.get("event") in SERVER_ERROR_LINES]
    assert handler_lines == [], f"H-60: the route's warning already reported the failure, so the server-error handler writes no line of its own: {handler_lines!r}"
    print_success(f"503 {UNAVAILABLE_DETAIL['error_code']} with its request_id, one warning with admin_id {admin_id}, no line of the handler")


@pytest.mark.asyncio
async def test_probe_answers_no_when_the_instance_key_cannot_be_used(app, monkeypatch):
    """AP-API-13 (H-19), in process: the public check already tolerates a key that cannot be used — 200
    ``{"match": false}`` with both headers, never an error — even for a nonce this instance issued. The control: the
    same nonce, the key usable, matches."""
    print_section(f"AP-API-13: GET {PROBE_PATH} when the instance key cannot be used")
    nonce = _mint(monkeypatch, key=KEY_A)
    with _instance_key(monkeypatch, KEY_A):
        _assert_probe(await _probe_in_process(app, nonce), True, "Control: in process, instance A asked its own nonce, the key usable")
        asked = _make_the_instance_key_unusable(monkeypatch)
        response = await _probe_in_process(app, nonce)
    assert asked, "Precondition: the check asked the probe's derive_key for its key: the nonce reached the signature check"
    _assert_probe(response, False, "in process, instance A asked its own nonce, the instance key unusable")
    print_success("match: true with the key usable, false without it, with both headers")
