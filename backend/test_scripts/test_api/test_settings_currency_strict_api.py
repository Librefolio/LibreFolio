"""
Strict base currency through the API, and a 422 that names the ISO code — lot E-19a (workstream E), items 2 and 3.

E-19a, as the release coordinator decided on 17/10, makes the user's base currency strict and its refusal helpful:

- ``PUT /api/v1/settings/user`` (``UserSettingsUpdate``) and the welcome flow's completion
  (``POST /api/v1/settings/onboarding/welcome/complete`` with ``welcome_settings``, ``OnboardingWelcomeSettings``) take
  ``base_currency`` with the ``iso_currency_code`` rule of E-18: an ISO 4217 alphabetic code, stored upper-cased. Today
  both take any three characters as given (``978``, ``XYZ``, ``eur``).
- A refusal names the code to write instead: ``978`` → ``… the ISO 4217 alphabetic code is EUR``. The E-18 write paths
  get the same text: ``POST /api/v1/fx/currencies/rate`` with a base of ``840`` → ``… is USD``.
- A refused request writes nothing.

Isolation (the API runs against the lane's shared database and backend, beside other tests):

- every test runs as a user of its own, registered with a unique name for that test only and deleted at teardown
  (``own_session``), so ``e2e_test_user`` and ``e2e_test_admin`` are never touched;
- the FX test posts a rate for a pair and a random day of 1901-1940 that no other test writes, reads the rates of that
  day and pair only, and deletes whatever it finds there afterwards.

"RED" tests (marked ``# red until E-19a``) fail before E-19a: the settings accept and store the lenient code, and the
FX refusal names no code. The "GUARD (green today)" test passes before and after: a valid ISO code is still accepted.
"""

import re
import secrets
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any, Optional

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.config import get_settings
from backend.app.db.models import FxRate
from backend.app.db.session import get_async_engine
from backend.app.services.accounts import user_service
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
PASSWORD = "TestPass123!"

#: The generic example of a refusal without a suggestion: a refusal "names EUR" when it names it outside this example.
GENERIC_EXAMPLE = "such as EUR or USD"


@pytest.fixture(scope="module")
def test_server():
    """Start, or attach to, the lane's test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# =============================================================================
# A USER OF THIS TEST'S OWN
# =============================================================================


async def _delete_user(username: str) -> None:
    """Delete an account this file registered, through the service layer, with what goes with it."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await user_service.get_user_by_username(session, username)
        if user is not None:
            await user_service.delete_user(session, user.id)


@pytest_asyncio.fixture
async def own_session(test_server) -> AsyncIterator[dict[str, str]]:
    """A Cookie header with the session of a regular user registered for this test only, deleted at teardown.

    The session travels explicitly on each request, never through a cookie jar.
    """
    username = f"scs_{uuid.uuid4().hex[:12]}"
    credentials = {"username": username, "password": PASSWORD}
    try:
        async with httpx.AsyncClient() as client:
            registered = await client.post(f"{API_BASE}/auth/register", json={**credentials, "email": f"{username}@test.com"}, timeout=TIMEOUT)
            assert registered.status_code == 201, f"Setup: registering {username} failed: {registered.status_code} {registered.text}"
            assert registered.json()["user"]["is_superuser"] is False, f"Barrier: {username} must be a regular user: {registered.text}"
            login = await client.post(f"{API_BASE}/auth/login", json=credentials, timeout=TIMEOUT)
        token = login.cookies.get(SESSION_COOKIE_NAME)
        assert login.status_code == 200 and token, f"Setup: signing in as {username} failed: {login.status_code} {login.text}"
        cookie = {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}
        me = await _call("GET", "/auth/me", cookie)
        assert me.status_code == 200 and me.json()["user"]["username"] == username, f"Barrier: the session must be {username}'s: {me.status_code} {me.text}"
        yield cookie
    finally:
        await _delete_user(username)


async def _call(method: str, path: str, cookie: dict[str, str], json: Any = None) -> httpx.Response:
    """One request with exactly ``cookie`` as its session, from a client with an empty cookie jar."""
    async with httpx.AsyncClient() as client:
        return await client.request(method, f"{API_BASE}{path}", headers=cookie, json=json, timeout=TIMEOUT)


async def _settings(cookie: dict[str, str]) -> dict[str, Any]:
    response = await _call("GET", "/settings/user", cookie)
    assert response.status_code == 200, f"GET /settings/user: {response.status_code} {response.text}"
    return response.json()


async def _put_base_currency(cookie: dict[str, str], value: Any) -> httpx.Response:
    return await _call("PUT", "/settings/user", cookie, {"base_currency": value})


async def _set_known_currency(cookie: dict[str, str], code: str = "CHF") -> None:
    """Positive control: a valid ISO code is accepted and stored, so a refusal after it is about the code alone, and the
    previous value is known."""
    response = await _put_base_currency(cookie, code)
    assert response.status_code == 200 and response.json()["base_currency"] == code, f"positive control: PUT {code!r} → {response.status_code} {response.text}"
    assert (await _settings(cookie))["base_currency"] == code


def _messages_at(response: httpx.Response, field: str) -> list[str]:
    """The ``msg`` of each 422 error whose ``loc`` ends with ``field`` (the request's input is never echoed, A-35)."""
    detail = response.json().get("detail")
    errors = detail if isinstance(detail, list) else []
    return [str(error.get("msg", "")) for error in errors if isinstance(error, dict) and list(error.get("loc", []))[-1:] == [field]]


def _names_as_suggestion(message: str, code: str) -> bool:
    """``code`` appears in ``message`` as a code of its own, outside the generic example ``such as EUR or USD``."""
    return re.search(rf"(?<![A-Z]){code}(?![A-Z])", message.replace(GENERIC_EXAMPLE, "")) is not None


def _red_if_accepted(response: httpx.Response, what: str) -> None:
    if response.status_code == 200:
        pytest.fail(f"red until E-19a: {what} is accepted (200): {response.text}", pytrace=False)


# =============================================================================
# 1. PUT /settings/user
# =============================================================================


@pytest.mark.asyncio
async def test_put_numeric_code_is_refused_naming_eur(test_server, own_session):  # red until E-19a
    """SCS-API-01 — RED: ``PUT /settings/user`` with ``{"base_currency": "978"}`` → 422 whose error on ``base_currency``
    names ``ISO 4217`` and ``EUR``; ``GET`` still shows the previous value (CHF)."""
    print_section("SCS-API-01: PUT /settings/user base_currency '978' → 422 naming EUR")
    await _set_known_currency(own_session)

    response = await _put_base_currency(own_session, "978")

    _red_if_accepted(response, "the base currency '978'")
    assert response.status_code == 422, f"{response.status_code} {response.text}"
    messages = _messages_at(response, "base_currency")
    assert messages, f"a 422 on base_currency expected: {response.text}"
    assert any("ISO 4217" in message and _names_as_suggestion(message, "EUR") for message in messages), f"the error must name ISO 4217 and EUR, the code to write: {messages}"
    assert (await _settings(own_session))["base_currency"] == "CHF", "a refused PUT writes nothing"
    print_success("✓ '978' refused, EUR named, nothing written")


@pytest.mark.asyncio
async def test_put_lower_case_code_is_stored_upper_case(test_server, own_session):  # red until E-19a
    """SCS-API-02 — RED: ``PUT /settings/user`` with ``{"base_currency": "eur"}`` → 200, and ``GET`` returns ``EUR``."""
    print_section("SCS-API-02: PUT /settings/user base_currency 'eur' → stored 'EUR'")
    await _set_known_currency(own_session)

    response = await _put_base_currency(own_session, "eur")

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    stored = (await _settings(own_session))["base_currency"]
    if stored != "EUR":
        pytest.fail(f"red until E-19a: 'eur' is stored as {stored!r}, not 'EUR'", pytrace=False)
    assert response.json()["base_currency"] == "EUR", f"the PUT answers what it stored: {response.text}"
    print_success("✓ 'eur' stored as 'EUR'")


@pytest.mark.asyncio
async def test_put_unknown_code_is_refused(test_server, own_session):  # red until E-19a
    """SCS-API-03 — RED: ``PUT /settings/user`` with ``{"base_currency": "XYZ"}`` → 422 on ``base_currency``; ``GET`` still shows CHF."""
    print_section("SCS-API-03: PUT /settings/user base_currency 'XYZ' → 422")
    await _set_known_currency(own_session)

    response = await _put_base_currency(own_session, "XYZ")

    _red_if_accepted(response, "the base currency 'XYZ'")
    assert response.status_code == 422 and _messages_at(response, "base_currency"), f"{response.status_code} {response.text}"
    assert (await _settings(own_session))["base_currency"] == "CHF", "a refused PUT writes nothing"
    print_success("✓ 'XYZ' refused, nothing written")


# =============================================================================
# 2. The welcome flow's completion
# =============================================================================


async def _welcome(cookie: dict[str, str]) -> dict[str, Any]:
    response = await _call("GET", "/settings/onboarding", cookie)
    assert response.status_code == 200, f"GET /settings/onboarding: {response.status_code} {response.text}"
    flows = {item["flow"]: item for item in response.json()["flows"]}
    return flows["welcome"]


async def _complete_welcome(cookie: dict[str, str], version: int, language: str, base_currency: Any) -> httpx.Response:
    payload = {"expected_version": version, "welcome_settings": {"language": language, "base_currency": base_currency, "avatar_url": None}}
    return await _call("POST", "/settings/onboarding/welcome/complete", cookie, payload)


@pytest.mark.asyncio
async def test_welcome_completion_refuses_numeric_code_and_commits_nothing(test_server, own_session):  # red until E-19a
    """SCS-API-04 — RED: completing the welcome flow with ``welcome_settings.base_currency`` ``978`` → 422 naming ``EUR``,
    and nothing is committed: the flow stays pending, the settings (language included) stay as they were.

    Then the positive control: the same request with ``CHF`` completes the flow (200) and stores both preferences, so
    the 422 was about the code alone.
    """
    print_section("SCS-API-04: welcome completion with base_currency '978' → 422, nothing committed")
    before = await _settings(own_session)
    welcome = await _welcome(own_session)
    assert welcome["status"] == "pending", f"precondition: a new user's welcome flow is pending: {welcome}"
    language = "it" if before["language"] == "fr" else "fr"

    response = await _complete_welcome(own_session, welcome["current_version"], language, "978")

    _red_if_accepted(response, "completing the welcome flow with the base currency '978'")
    assert response.status_code == 422, f"{response.status_code} {response.text}"
    messages = _messages_at(response, "base_currency")
    assert any("ISO 4217" in message and _names_as_suggestion(message, "EUR") for message in messages), f"the error must name ISO 4217 and EUR: {response.text}"
    assert (await _welcome(own_session))["status"] == "pending", "a refused completion completes nothing"
    assert await _settings(own_session) == before, "a refused completion stores no preference"

    control = await _complete_welcome(own_session, welcome["current_version"], language, "CHF")
    assert control.status_code == 200, f"positive control: the same completion with 'CHF' must succeed: {control.status_code} {control.text}"
    after = await _settings(own_session)
    assert (after["language"], after["base_currency"]) == (language, "CHF")
    print_success("✓ '978' refused with nothing committed; 'CHF' completes")


# =============================================================================
# 3. An E-18 write path names the code too: POST /fx/currencies/rate
# =============================================================================


def _unused_day() -> date:
    """A random day of 1901-1940: no other test writes a rate there, so whatever this test finds there is its own."""
    return date(1901, 1, 1) + timedelta(days=secrets.randbelow(40 * 365))


async def _rates_of(day: date, codes: frozenset[str]) -> list[tuple[str, str]]:
    """The stored rates of ``day`` between two of ``codes``, as ``(base, quote)``."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(FxRate.base, FxRate.quote).where(FxRate.date == day, FxRate.base.in_(codes), FxRate.quote.in_(codes)))).all()
    return [(base, quote) for base, quote in rows]


async def _delete_rates_of(day: date, codes: frozenset[str]) -> None:
    """Whoever writes, cleans up: the rates of this test's own day and pair, if a regression wrote any."""
    async with AsyncSession(get_async_engine()) as session:
        await session.execute(delete(FxRate).where(FxRate.date == day, FxRate.base.in_(codes), FxRate.quote.in_(codes)))
        await session.commit()


@pytest.mark.asyncio
async def test_fx_rate_with_numeric_base_is_refused_naming_usd(test_server, own_session):  # red until E-19a
    """SCS-API-05 — RED: ``POST /fx/currencies/rate`` with a rate whose base is ``840`` (USD's numeric code) → 422 whose
    error on ``base`` contains ``is USD``; no rate is written for the day and pair (840 or USD, against ISK)."""
    print_section("SCS-API-05: POST /fx/currencies/rate base '840' → 422 naming USD")
    day = _unused_day()
    codes = frozenset({"840", "USD", "ISK"})
    before: Optional[list[tuple[str, str]]] = None
    try:
        before = await _rates_of(day, codes)
        assert before == [], f"precondition: no rate on {day} for {sorted(codes)}: {before}"

        response = await _call("POST", "/fx/currencies/rate", own_session, [{"date": day.isoformat(), "base": "840", "quote": "ISK", "rate": "138.5"}])

        assert response.status_code == 422, f"E-18 refuses '840' already: {response.status_code} {response.text}"
        messages = _messages_at(response, "base")
        assert messages and all("ISO 4217" in message for message in messages), f"a 422 on base naming ISO 4217 expected: {response.text}"
        if not any("is USD" in message for message in messages):
            pytest.fail(f"red until E-19a: the refusal of '840' must say 'is USD': {messages}", pytrace=False)
        assert await _rates_of(day, codes) == [], "a refused rate is not written"
        print_success("✓ '840' refused naming USD, nothing written")
    finally:
        if before == []:
            await _delete_rates_of(day, codes)


# =============================================================================
# 4. A valid ISO code is still accepted
# =============================================================================


@pytest.mark.asyncio
async def test_put_valid_iso_code_is_accepted(test_server, own_session):
    """SCS-API-06 — GUARD (green today): ``PUT /settings/user`` with a valid ISO code (``JPY``) → 200, and ``GET`` returns it."""
    print_section("SCS-API-06: PUT /settings/user base_currency 'JPY' → 200")
    response = await _put_base_currency(own_session, "JPY")
    assert response.status_code == 200 and response.json()["base_currency"] == "JPY", f"{response.status_code} {response.text}"
    assert (await _settings(own_session))["base_currency"] == "JPY"
    print_success("✓ 'JPY' accepted")
