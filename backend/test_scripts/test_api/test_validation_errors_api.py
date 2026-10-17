"""Validation errors: FastAPI's 422 never sends the request's input back (A-35, accounts lot A7b-2, decision D2).

FastAPI's default handler puts ``input`` in every error of its 422: a field that breaks its constraint comes back with
its value, and a **missing** field with the whole body it was missing from — password and tokens included. The
contract: ``backend/app/api/validation_errors.py`` gives ``install_validation_error_handler(app)``, called once in
``backend/app/main.py``; it registers a handler for ``RequestValidationError`` that answers as FastAPI's default does
(``{"detail": [...]}``, status 422) with the key ``input`` removed from every error. ``loc``, ``msg``, ``type`` and
``ctx`` stay — the rule of ``_NoInputEchoRoute`` (``api/v1/plugin_settings.py``), for the whole app. The OpenAPI schema
does not change: FastAPI's ``ValidationError`` keeps ``input`` as an optional property.

1. **In process** (no server, no database): a tiny app of two routes — a body with a username and a password of at
   least 64 characters, a query with a token of at most 16 — with and without the install. With it, a too-short
   password, a missing username, two errors in one body, a query parameter and a body that is not JSON are each
   answered with FastAPI's own 422 minus ``input``, the secret nowhere; a request that validates and the route's own
   coded 422 are answered as before. Red until A7b-2: the module does not exist yet; it is imported inside the tests,
   so the rest of the file is collected all the same. Without the install (guard), FastAPI sends the input back.
2. **On the lane's server**, through the whole app: for every route with a secret in its body — login, register,
   change-password, password-reset, setup, tokens/inspect, profile, and workstream E's email/verification/resend — the
   secret field itself invalid, and another field missing beside it, with unique markers as the secrets: 422,
   ``detail`` a non-empty list refusing the request for the reason the case names, every error with ``loc``, ``msg``
   and ``type``, nothing but ``ctx`` besides, no ``input``; no marker anywhere in the answer. Red until A7b-2.
   ``DELETE /auth/users/me`` has no body, so nothing to send back; ``PUT /auth/profile`` has no required field, so a
   body that is not an object stands in for the missing field (its one error also carries the whole body).
3. **Guards**, green today and after: a plain 422 keeps ``loc``, ``msg``, ``type`` and ``ctx`` exactly as before (what
   the frontend reads); the OpenAPI schema keeps FastAPI's ``ValidationError``.

Isolation: write-scoped, parallel-safe. The in-process part touches nothing shared. On the lane every request but the
sign-ins is malformed and refused by FastAPI before any handler runs: it writes nothing and spends no rate limit. The two
routes that need a session get it from an account the test registers and signs in, deleted at teardown, after a red
too; every username a request carries is named before the request, so a registration a red would let through is
deleted as well. No global setting, no shared account, nobody else's password is touched.
"""

import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Annotated, Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.api.v1 import auth as auth_api
from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.db.session import get_async_engine
from backend.app.schemas.auth import AdminSetupRequest, AuthRegisterRequest, PasswordResetRequest, TokenInspectRequest
from backend.app.schemas.email import EmailVerificationResendRequest
from backend.app.services.accounts import user_service
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}{API_V1_PREFIX}"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME

#: What every error of the 422 keeps; ``ctx`` may stand beside them when the constraint has one; ``input`` never.
KEPT = frozenset({"loc", "msg", "type"})


def _marker(prefix: str) -> str:
    """A secret no response may hold: unique across workers and runs."""
    return f"{prefix}{uuid.uuid4().hex}"


# =============================================================================
# 1. IN PROCESS: A TINY APP, WITH AND WITHOUT THE INSTALL
# =============================================================================

#: The tiny app's password rule: a marker (36 characters) is too short, padded with _long_enough it is long enough.
_MIN_PASSWORD = 64
#: The tiny app's query rule: a marker is too long for it.
_MAX_QUERY_TOKEN = 16
#: The username the tiny route refuses with a coded 422 of its own, an HTTPException as the app's coded refusals are.
_REFUSED = "refused"
_CODED_REFUSAL = {"error_code": "SIGN_IN_REFUSED", "message": "Refused by the route itself"}


class _SignIn(BaseModel):
    """The body of the tiny app's ``POST /sign-in``: a username, and a password of at least ``_MIN_PASSWORD`` characters."""

    username: str
    password: str = Field(..., min_length=_MIN_PASSWORD)


def _long_enough(marker: str) -> str:
    """``marker`` padded to a password the tiny app accepts."""
    return marker + "-" * _MIN_PASSWORD


def _tiny_app(install: Callable[[FastAPI], None] | None = None) -> FastAPI:
    """``POST /sign-in`` (a ``_SignIn`` body) and ``GET /lookup`` (a short ``token`` query), with ``install`` applied first if given."""
    app = FastAPI()
    if install is not None:
        install(app)

    @app.post("/sign-in")
    async def sign_in(body: _SignIn) -> dict[str, str]:
        if body.username == _REFUSED:
            raise HTTPException(status_code=422, detail=_CODED_REFUSAL)
        return {"username": body.username}

    @app.get("/lookup")
    async def lookup(token: Annotated[str, Query(max_length=_MAX_QUERY_TOKEN)]) -> dict[str, int]:
        return {"length": len(token)}

    return app


def _the_install() -> Callable[[FastAPI], None]:
    """``install_validation_error_handler``, imported when a test needs it: before A7b-2 its module does not exist, and
    the rest of this file must still be collected."""
    try:
        from backend.app.api.validation_errors import install_validation_error_handler  # noqa: PLC0415 — red until A7b-2: the module's absence must fail these tests, not the file's collection
    except ImportError as error:
        pytest.fail(f"backend/app/api/validation_errors.py must give install_validation_error_handler(app) (A-35, decision D2): {error}")
    return install_validation_error_handler


async def _send(app: FastAPI, method: str, path: str, **request: Any) -> httpx.Response:
    """One request to ``app`` in process, through httpx's ASGI transport: no server, no database."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        return await client.request(method, path, **request)


def _assert_fastapis_answer_without_input(answered: httpx.Response, default: httpx.Response) -> None:
    """``answered`` is ``default`` — FastAPI's own 422 to the same request — with ``input`` removed from every error, and nothing else changed."""
    assert (answered.status_code, answered.headers.get("content-type")) == (default.status_code, default.headers.get("content-type")), f"{answered.status_code} {answered.headers.get('content-type')}"
    expected = {"detail": [{key: value for key, value in error.items() if key != "input"} for error in default.json()["detail"]]}
    assert answered.json() == expected, f"FastAPI's own 422 with input removed, nothing else changed: expected {expected}, got {answered.json()}"


# red until A7b-2: backend.app.api.validation_errors does not exist yet
@pytest.mark.asyncio
async def test_a_too_short_password_is_refused_without_its_input():
    """A password under the route's ``min_length``: 422, one error — ``string_too_short`` at ``body.password``, its
    ``msg``, ``ctx.min_length`` — without ``input``; the password nowhere in the answer, which is FastAPI's own with
    ``input`` removed and nothing else changed."""
    print_section("A-35 in process: a too-short password")
    install = _the_install()
    password = _marker("lfpw")
    request = {"json": {"username": "alice", "password": password}}

    default = await _send(_tiny_app(), "POST", "/sign-in", **request)
    answered = await _send(_tiny_app(install), "POST", "/sign-in", **request)

    assert answered.status_code == 422, answered.text
    (error,) = answered.json()["detail"]
    assert (error["type"], error["loc"], error.get("ctx")) == ("string_too_short", ["body", "password"], {"min_length": _MIN_PASSWORD}), error
    assert isinstance(error.get("msg"), str) and error["msg"], f"the error must keep its msg: {error}"
    assert "input" not in error, f"the error must not carry the input: {error}"
    assert password not in answered.text, f"the 422 sends the password back: {answered.text}"
    _assert_fastapis_answer_without_input(answered, default)
    print_success("422 with loc, msg, type and ctx; no input, no password")


# red until A7b-2: backend.app.api.validation_errors does not exist yet
@pytest.mark.asyncio
async def test_a_missing_username_does_not_send_the_body_back():
    """No username beside a valid password — FastAPI's ``missing`` error carries the whole body as its ``input``: 422,
    one error, ``missing`` at ``body.username``, made of ``loc``, ``msg`` and ``type`` only; the password nowhere."""
    print_section("A-35 in process: a missing username")
    install = _the_install()
    marker = _marker("lfpw")
    request = {"json": {"password": _long_enough(marker)}}

    default = await _send(_tiny_app(), "POST", "/sign-in", **request)
    answered = await _send(_tiny_app(install), "POST", "/sign-in", **request)

    assert answered.status_code == 422, answered.text
    (error,) = answered.json()["detail"]
    assert (error["type"], error["loc"]) == ("missing", ["body", "username"]), error
    assert set(error) == KEPT, f"loc, msg and type, nothing else — no input: {error}"
    assert marker not in answered.text, f"the 422 sends the body back, password included: {answered.text}"
    _assert_fastapis_answer_without_input(answered, default)
    print_success("422 with loc, msg and type; the body stays home")


#: Malformed requests to the tiny app beyond one body field, each carrying ``secret``: FastAPI's own 422 gives every
#: error an ``input`` — the secret itself in the first two, ``{}`` for a body that is not JSON.
_EVERY_ERROR: dict[str, Callable[[str], tuple[str, str, dict[str, Any]]]] = {
    "two-errors-in-one-body": lambda secret: ("POST", "/sign-in", {"json": {"username": [secret], "password": secret}}),
    "a-query-parameter": lambda secret: ("GET", "/lookup", {"params": {"token": secret}}),
    "a-body-that-is-not-json": lambda secret: ("POST", "/sign-in", {"content": f'{{"username": "alice", "password": "{secret}"'.encode(), "headers": {"content-type": "application/json"}}),
}


# red until A7b-2: backend.app.api.validation_errors does not exist yet
@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(_EVERY_ERROR))
async def test_every_error_loses_its_input_wherever_it_is(case: str):
    """Every error of the 422 loses ``input``, wherever FastAPI found it — several in one body, in the query, a body it
    could not parse — and the answer is FastAPI's own otherwise; the secret is nowhere."""
    print_section(f"A-35 in process: {case}")
    install = _the_install()
    secret = _marker("lfsecret")
    method, path, request = _EVERY_ERROR[case](secret)

    default = await _send(_tiny_app(), method, path, **request)
    answered = await _send(_tiny_app(install), method, path, **request)

    assert default.status_code == 422 and all("input" in error for error in default.json()["detail"]), f"Precondition: FastAPI's own 422 gives every error an input: {default.text}"
    assert answered.status_code == 422, answered.text
    detail = answered.json()["detail"]
    assert detail and not [error for error in detail if "input" in error], f"no error may carry its input: {detail}"
    assert secret not in answered.text, f"the 422 sends the secret back: {answered.text}"
    _assert_fastapis_answer_without_input(answered, default)
    print_success(f"{len(detail)} error(s), none with its input")


# red until A7b-2: backend.app.api.validation_errors does not exist yet
@pytest.mark.asyncio
async def test_the_install_changes_nothing_but_fastapis_422():
    """A request that validates is answered 200 as before; the route's own 422 — an HTTPException with a detail of its
    own, as the app's coded refusals are — passes untouched: the handler is for FastAPI's validation errors only."""
    print_section("A-35 in process: nothing else changes")
    install = _the_install()
    password = _long_enough(_marker("lfpw"))

    accepted = await _send(_tiny_app(install), "POST", "/sign-in", json={"username": "alice", "password": password})
    coded = await _send(_tiny_app(install), "POST", "/sign-in", json={"username": _REFUSED, "password": password})
    coded_by_default = await _send(_tiny_app(), "POST", "/sign-in", json={"username": _REFUSED, "password": password})

    assert (accepted.status_code, accepted.json()) == (200, {"username": "alice"}), accepted.text
    assert (coded.status_code, coded.json()) == (coded_by_default.status_code, coded_by_default.json()) == (422, {"detail": _CODED_REFUSAL}), coded.text
    print_success("200 as before; the route's own 422 untouched")


# guard: green today and after A7b-2
@pytest.mark.asyncio
async def test_without_the_install_fastapi_sends_the_input_back():
    """The premise: the same tiny app without the install answers FastAPI's default 422, whose errors carry ``input`` —
    the too-short password itself, and for the missing username the whole body."""
    print_section("A-35 guard: FastAPI's default 422 echoes the input")
    password = _marker("lfpw")
    long_enough = _long_enough(password)

    too_short = await _send(_tiny_app(), "POST", "/sign-in", json={"username": "alice", "password": password})
    missing = await _send(_tiny_app(), "POST", "/sign-in", json={"password": long_enough})

    assert (too_short.status_code, missing.status_code) == (422, 422), f"{too_short.text} {missing.text}"
    assert [error.get("input") for error in too_short.json()["detail"]] == [password], too_short.text
    assert [error.get("input") for error in missing.json()["detail"]] == [{"password": long_enough}], missing.text
    assert password in too_short.text and password in missing.text
    print_success("without the install, the input comes back")


# =============================================================================
# 2. ON THE LANE'S SERVER: EVERY ROUTE WITH A SECRET IN ITS BODY
# =============================================================================


@pytest.fixture(scope="module")
def test_server():
    """The lane's server (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


def _lane_engine() -> AsyncEngine:
    """The lane's test database, the one its server serves: this module deletes its own accounts there only."""
    is_test_db, database_url = verify_test_database()
    assert is_test_db, f"Refusing to touch a database that is not the lane's test database: {database_url}"
    return get_async_engine()


@dataclass
class _Lane:
    """The accounts one test names on the lane: named before any request that carries them, deleted at teardown."""

    usernames: list[str] = field(default_factory=list)

    def new_username(self, prefix: str = "a35") -> str:
        username = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self.usernames.append(username)
        return username

    async def call(self, method: str, path: str, *, json: Any = None, cookie: str | None = None) -> httpx.Response:
        """One request from a client of its own: no cookie jar, the session sent explicitly."""
        headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
        async with httpx.AsyncClient() as client:
            return await client.request(method, f"{API_BASE}{path}", json=json, headers=headers, timeout=TIMEOUT)

    async def signed_in(self) -> str:
        """An account of this test, registered on the lane and signed in: its session token. Its own password is never sent malformed."""
        username = self.new_username("a35_session")
        password = f"Echo-Guard-2026-{uuid.uuid4().hex[:8]}"
        registered = await self.call("POST", "/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password})
        assert registered.status_code == 201, f"Setup: registering {username} failed; the lane's registration must be open: {registered.status_code} {registered.text}"
        login = await self.call("POST", "/auth/login", json={"username": username, "password": password})
        cookie = login.cookies.get(COOKIE)
        assert login.status_code == 200 and cookie, f"Setup: signing in as {username} failed: {login.status_code} {login.text}"
        return cookie


async def _delete_accounts(usernames: list[str]) -> list[str]:
    """Delete those of these accounts the lane holds, each in a session of its own, through user_service.delete_user; what failed."""
    errors: list[str] = []
    for username in usernames:
        async with AsyncSession(_lane_engine()) as session:
            try:
                user = await user_service.get_user_by_username(session, username)
                if user is not None:
                    await user_service.delete_user(session, user.id)
            except Exception as exc:  # every account gets its attempt; the failures are reported together
                errors.append(f"{username}: {exc!r}")
    return errors


@pytest_asyncio.fixture
async def lane(test_server) -> AsyncIterator[_Lane]:
    """The accounts a test names go at teardown, after a red too."""
    named = _Lane()
    try:
        yield named
    finally:
        errors = await _delete_accounts(named.usernames)
        assert not errors, f"Teardown: could not delete this test's accounts: {errors}"


@dataclass(frozen=True)
class _Secrets:
    """What one malformed request may carry: three secrets, each a unique marker, and a username of this test's own."""

    username: str
    password: str = field(default_factory=lambda: _marker("lfpw"))
    new_password: str = field(default_factory=lambda: _marker("lfnewpw"))
    token: str = field(default_factory=lambda: _marker("lftoken"))

    @property
    def email(self) -> str:
        return f"{self.username}@example.com"

    def named(self) -> dict[str, str]:
        """The secrets by name: none may come back."""
        return {"password": self.password, "new password": self.new_password, "token": self.token}


@dataclass(frozen=True)
class _Case:
    """A malformed request to one route — ``name``, ``method``, ``path``, its ``body`` built from the secrets — and the
    one error FastAPI refuses it with, ``(type, loc)``; ``session`` when the route needs a signed-in account."""

    name: str
    method: str
    path: str
    body: Callable[[_Secrets], Any]
    error: tuple[str, tuple[str, ...]]
    session: bool = False


def _at(error_type: str, *path: str) -> tuple[str, tuple[str, ...]]:
    """An error as FastAPI reports one in a body: its ``type``, and its ``loc`` — ``body``, then the field."""
    return error_type, ("body", *path)


def _past(marker: str, model: type[BaseModel], name: str) -> str:
    """``marker`` padded past the ``max_length`` that ``model`` declares for its field ``name``."""
    limits = [rule.max_length for rule in model.model_fields[name].metadata if getattr(rule, "max_length", None) is not None]
    assert limits, f"Precondition: {model.__name__}.{name} declares no max_length, so no value of it is too long"
    return marker + "x" * limits[0]


def _link_cases(name: str, path: str, model: type[BaseModel]) -> list[_Case]:
    """A link's spend (the reset link, the setup link): ``token`` and ``new_password``, each invalid and each missing beside the other."""
    return [
        _Case(f"{name}-token-too-long", "POST", path, lambda s: {"token": _past(s.token, model, "token"), "new_password": s.new_password}, _at("string_too_long", "token")),
        _Case(f"{name}-new-password-no-string", "POST", path, lambda s: {"token": s.token, "new_password": [s.new_password]}, _at("string_type", "new_password")),
        _Case(f"{name}-token-missing", "POST", path, lambda s: {"new_password": s.new_password}, _at("missing", "token")),
        _Case(f"{name}-new-password-missing", "POST", path, lambda s: {"token": s.token}, _at("missing", "new_password")),
    ]


#: Each route with a secret in its body: the secret itself invalid (too long where the schema has a max_length, no
#: string where it has none), and another field missing while the secret is there.
_CASES: list[_Case] = [
    # POST /auth/login: the password
    _Case("login-password-no-string", "POST", "/auth/login", lambda s: {"username": s.username, "password": [s.password]}, _at("string_type", "password")),
    _Case("login-username-missing", "POST", "/auth/login", lambda s: {"password": s.password}, _at("missing", "username")),
    # POST /auth/register: the password and the invitation's token
    _Case("register-password-no-string", "POST", "/auth/register", lambda s: {"username": s.username, "email": s.email, "password": [s.password]}, _at("string_type", "password")),
    _Case("register-invite-token-too-long", "POST", "/auth/register", lambda s: {"username": s.username, "email": s.email, "password": s.password, "invite_token": _past(s.token, AuthRegisterRequest, "invite_token")}, _at("string_too_long", "invite_token")),
    _Case("register-username-missing", "POST", "/auth/register", lambda s: {"email": s.email, "password": s.password, "invite_token": s.token}, _at("missing", "username")),
    # POST /auth/change-password, signed in: the current and the new password
    _Case("change-password-current-no-string", "POST", "/auth/change-password", lambda s: {"current_password": [s.password], "new_password": s.new_password}, _at("string_type", "current_password"), session=True),
    _Case("change-password-new-missing", "POST", "/auth/change-password", lambda s: {"current_password": s.password}, _at("missing", "new_password"), session=True),
    _Case("change-password-current-missing", "POST", "/auth/change-password", lambda s: {"new_password": s.new_password}, _at("missing", "current_password"), session=True),
    # POST /auth/password-reset and POST /auth/setup: the link's token and the new password
    *_link_cases("password-reset", "/auth/password-reset", PasswordResetRequest),
    *_link_cases("setup", "/auth/setup", AdminSetupRequest),
    # POST /auth/tokens/inspect: the token
    _Case("tokens-inspect-token-too-long", "POST", "/auth/tokens/inspect", lambda s: {"token": _past(s.token, TokenInspectRequest, "token"), "purpose": "invite"}, _at("string_too_long", "token")),
    _Case("tokens-inspect-purpose-missing", "POST", "/auth/tokens/inspect", lambda s: {"token": s.token}, _at("missing", "purpose")),
    # PUT /auth/profile, signed in: the current password. No field is required, so none can be missing: a body that is
    # not an object stands in, its one error carrying the whole body just the same.
    _Case("profile-current-password-no-string", "PUT", "/auth/profile", lambda s: {"email": s.email, "current_password": [s.password]}, _at("string_type", "current_password"), session=True),
    _Case("profile-body-no-object", "PUT", "/auth/profile", lambda s: [{"email": s.email, "current_password": s.password}], _at("model_attributes_type"), session=True),
    # POST /email/verification/resend, workstream E's: the password. Here as the proof that the rule is the whole app's,
    # not the auth router's.
    _Case("resend-password-too-long", "POST", "/email/verification/resend", lambda s: {"username": s.username, "password": _past(s.password, EmailVerificationResendRequest, "password")}, _at("string_too_long", "password")),
    _Case("resend-username-missing", "POST", "/email/verification/resend", lambda s: {"password": s.password}, _at("missing", "username")),
]


def _assert_refused_for_the_case(response: httpx.Response, case: _Case) -> None:
    """FastAPI's 422 — ``{"detail": [...]}`` and nothing else — refusing the request for the one reason ``case`` names."""
    request = f"{case.method} {case.path} ({case.name})"
    assert response.status_code == 422, f"{request}: expected FastAPI's 422, got {response.status_code} {response.text[:300]}"
    body = response.json()
    assert isinstance(body, dict) and set(body) == {"detail"}, f"{request}: the 422 must be {{'detail': [...]}} and nothing else: {response.text[:300]}"
    detail = body["detail"]
    assert isinstance(detail, list) and detail, f"{request}: detail must be a non-empty list of errors: {detail!r}"
    found = [(error.get("type"), tuple(error.get("loc", ()))) for error in detail]
    assert found == [case.error], f"Precondition, {request}: the request must be refused for the reason the case names, {case.error}; got {found}"


def _echoes(response: httpx.Response, secrets: _Secrets) -> list[str]:
    """What of the request the 422 sends back: errors that keep an ``input`` or lose ``loc``, ``msg`` or ``type``, and the secrets in its text."""
    detail = response.json()["detail"]
    problems = [f"an error keeps its input: {error}" for error in detail if "input" in error]
    problems += [f"an error must keep loc, msg and type, and add nothing but ctx: {sorted(error)}" for error in detail if not KEPT <= set(error) - {"input"} <= KEPT | {"ctx"}]
    problems += [f"the response sends the {name} back" for name, value in secrets.named().items() if value in response.text]
    return problems


# red until A7b-2: the routes answer FastAPI's default 422, input included
@pytest.mark.asyncio
@pytest.mark.parametrize("case", [pytest.param(case, id=case.name) for case in _CASES])
async def test_a_422_never_sends_a_secret_back(lane: _Lane, case: _Case):
    """A malformed request to a route with a secret in its body, the secrets unique markers: FastAPI's 422 for the
    reason the case names, every error with ``loc``, ``msg`` and ``type`` (``ctx`` at most besides) and no ``input``,
    and no marker anywhere in the answer. The routes that need a session get one of an account of this test."""
    print_section(f"A-35 on the lane: {case.method} {case.path}, {case.name}")
    secrets = _Secrets(lane.new_username())
    cookie = await lane.signed_in() if case.session else None

    response = await lane.call(case.method, case.path, json=case.body(secrets), cookie=cookie)

    _assert_refused_for_the_case(response, case)
    problems = _echoes(response, secrets)
    assert not problems, f"{case.method} {case.path} ({case.name}):\n- " + "\n- ".join(problems)
    print_success(f"422 refusing {case.error}, without input, no secret back")


# =============================================================================
# 3. GUARDS: THE SHAPE OF THE 422 AND THE OPENAPI SCHEMA
# =============================================================================

#: FastAPI's answer to a sign-in with an empty username and no password, ``input`` aside: what the frontend reads
#: (``loc`` and ``msg``, by ``type``), and ``ctx`` where the constraint gives one.
_PLAIN_ERRORS = [
    {"type": "string_too_short", "loc": ["body", "username"], "msg": "String should have at least 1 character", "ctx": {"min_length": 1}},
    {"type": "missing", "loc": ["body", "password"], "msg": "Field required"},
]


# guard: green today and after A7b-2
@pytest.mark.asyncio
async def test_a_422_still_lists_loc_msg_and_type_as_before(lane: _Lane):
    """The frontend reads ``loc`` and ``msg`` of a 422 (the registration card, the save errors): the fix takes ``input``
    away and nothing else. A plain sign-in on the lane's server, with an empty username and no password: FastAPI's two
    errors, in order, each with its ``loc``, ``msg`` and ``type``, and ``ctx`` where its constraint gives one."""
    print_section("A-35 guard: loc, msg and type as before")
    response = await lane.call("POST", "/auth/login", json={"username": ""})

    assert response.status_code == 422, response.text
    body = response.json()
    assert set(body) == {"detail"}, response.text
    kept = [{key: error[key] for key in ("type", "loc", "msg", "ctx") if key in error} for error in body["detail"]]
    assert kept == _PLAIN_ERRORS, f"loc, msg, type and ctx must stay as FastAPI gives them: {kept}"
    print_success("422 with loc, msg, type and ctx as before")


# guard: green today and after A7b-2
@pytest.mark.asyncio
async def test_the_openapi_schema_keeps_fastapis_validation_error(lane: _Lane):
    """The fix changes the answers, not the schema the API client is generated from: FastAPI's ``ValidationError``
    keeps ``loc``, ``msg`` and ``type`` required and ``input`` and ``ctx`` optional, ``HTTPValidationError`` is a list of
    them, and it is still the 422 of a route with a body (``POST /auth/login``)."""
    print_section("A-35 guard: the OpenAPI schema of the 422")
    response = await lane.call("GET", "/openapi.json")

    assert response.status_code == 200, f"{response.status_code} {response.text[:300]}"
    openapi = response.json()
    schemas = openapi["components"]["schemas"]
    error = schemas["ValidationError"]
    assert (sorted(error["properties"]), error["required"]) == (["ctx", "input", "loc", "msg", "type"], ["loc", "msg", "type"]), error
    assert schemas["HTTPValidationError"]["properties"]["detail"]["items"] == {"$ref": "#/components/schemas/ValidationError"}, schemas["HTTPValidationError"]
    login_422 = openapi["paths"][f"{API_V1_PREFIX}/auth/login"]["post"]["responses"]["422"]
    assert login_422["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/HTTPValidationError"}, login_422
    print_success("ValidationError keeps input and ctx optional; a route's 422 is HTTPValidationError")
