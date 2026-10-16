"""
Users Admin API — release 1.3, workstream A, lot A5a (plan phase01Accounts, A5.1, contract point 5, the administrator's part).

An administrator manages the accounts from the API. Every route below sits behind ``require_admin`` in
``api/v1/users.py``, its static routes declared before ``{user_id}``:

1. ``GET /users/invites`` → ``{items: [{id, grants_admin, email, created_at, expires_at, created_by_user_id}], usage:
   {used, max_users, billing_url}}``: the live invitations only (neither consumed, nor revoked, nor expired), whoever
   issued them. ``used`` counts the active accounts plus the live invitations; ``max_users`` is ``LIBREFOLIO_MAX_USERS``
   (null without a limit, 0 when the variable is not valid: a bad limit closes); ``billing_url`` is
   ``LIBREFOLIO_BILLING_URL``, null when unset.
2. ``POST /users/invites`` ``{grants_admin=false, email?}`` → 201 ``{invite, token, path, url}``: ``invite`` as listed,
   ``token`` the plaintext shown once, ``path`` its page with the token in the URL fragment (``/invite#token=…``: a
   browser never sends a fragment, so the token stays out of the access log and of proxy logs), ``url`` the public URL
   plus the path, null
   without ``LIBREFOLIO_PUBLIC_URL``. An invitation lives 7 days and only its hash is stored. 409 ``USER_LIMIT_REACHED``
   with ``limit``, ``used`` and ``billing_url`` when ``used >= max_users`` (the caller is an administrator: the counts and
   the subscription link are for them); 409 ``REGISTRATION_DISABLED`` while registration is ``disabled``, by the row or
   by ``LIBREFOLIO_REGISTRATION``. A refusal issues nothing.
3. ``DELETE /users/invites/{invite_id}`` → 204, and the invitation opens nothing any more; 404 when the id is not a live
   invitation: revoked, consumed, expired, never issued, or a token of another purpose (which stays as it was).
4. ``GET /users`` → ``{items: [{id, username, email, is_active, is_superuser, created_at, protected}], usage}``: every
   account, active or not; no hash, no secret. ``protected`` is added by lot A6a (point 12).
5. ``PATCH /users/{user_id}`` ``{is_active?, is_superuser?}`` → 200 with the account as ``GET /users`` lists it; 404; 409
   ``LAST_ADMIN`` to deactivate or demote the last active administrator; 409 ``USER_LIMIT_REACHED`` (with the counts) to
   reactivate an account over the limit, which blocks nothing else. Deactivation and demotion end the account's sessions
   (A4b); activation and promotion end none, and a reactivation does not bring the old sessions back.
6. ``POST /users/{user_id}/password-reset-link`` → 201 ``{token, path, url, expires_at}``, ``path`` being
   ``/reset-password#token=…``, 30 minutes, after revoking the account's other live reset links (another account's
   stay); the link works once with ``POST /auth/password-reset``. 404.
7. ``POST /users/{user_id}/sessions/revoke`` → 204: every session of that account ends, no other one; 404.
8. ``POST /users/{user_id}/onboarding/reset`` ``{flow?}`` → 204: every flow, steps included, or only the one named, back
   to ``pending``, as the account itself reads it from ``GET /settings/onboarding`` (21-5); an unknown flow is a 422 that
   resets nothing; 404.
9. Every action writes a structured log event, and no log carries a token. The plaintext (hence neither the path nor the
   URL) appears in no structlog event and no stdlib record, whatever the logger. Its hash appears in no structlog event
   and in no record of the application's loggers. The third-party loggers that ``configure_logging`` silences to WARNING
   (``aiosqlite``, ``sqlalchemy.engine``, …) are excluded: they log every statement with its parameters, the stored
   hash included, so a running server never emits those records.

Lot A6a (plan phase01Accounts §A6.1) adds:

10. ``GET /users/{user_id}/deletion-preview`` → 200 ``{user_id, username, brokers_deleted: [{id, name, transactions}],
    brokers_left: [{id, name, role}], transfers_unpaired}``, both lists by broker id, ``role`` the UserRole value: what
    deleting the account would take, by the rule ``delete_user`` applies (``BrokerService.leave_broker``); it writes
    nothing. 404 for an account that does not exist.
11. ``DELETE /users/{user_id}`` → 204 with no body: the account is gone, its sessions answer 401, its brokers follow the
    preview — those of ``brokers_deleted`` gone with their transactions, those of ``brokers_left`` still there without
    its access, the transfer half it leaves alone unlinked. 404 for an account that does not exist; 409
    ``SELF_DELETION`` for the caller's own id (one's own account is deleted from the profile); 409 ``DEMOTE_FIRST`` for
    an administrator, active or not; 409 ``ACCOUNT_PROTECTED`` from the hook; a technical failure → 500 «nothing was
    deleted», and nothing is. One structured event, «Account deleted by an administrator», with ``user_id``,
    ``username``, ``admin_id``, ``brokers_deleted`` and ``files_removed``; no session token and no password in any log.
12. The hook of lot A7, ``user_service.account_protection(user) -> Optional[str]``, a plain function: ``PATCH`` refuses
    to deactivate or demote an account it gives a reason for, ``DELETE`` refuses to delete it, both 409
    ``ACCOUNT_PROTECTED``, changing nothing; ``GET /users`` and ``PATCH`` answer ``protected: bool`` (a reason exists).
    Today it protects nobody: every account of the lane is ``protected: false``.

Lot A7b (plan phase01Accounts, «A7b — Analisi e contratto», contract C5, its backend part) adds:

13. ``pending_setup: bool`` on every account ``GET /users`` lists and ``PATCH /users/{user_id}`` answers, false by
    default in ``AdminUserRead``. True exactly for an account waiting for its F02 setup, by the notion of
    ``registration_service.pending_admin_filter()`` — the one ``user_usage`` counts (A7a, C4) and ``pending_admin``
    reads (BOOT-016, ``test_admin_bootstrap.py``): inactive, with at least one ``admin_setup`` token and none of them
    consumed; those tokens live, expired or revoked alike, the account an administrator or not. False for every other
    account: an active one, its setup link live or spent; an inactive one whose setup link was spent (deactivated after
    its setup); an inactive one without a setup link, with no token or with a token of another purpose; one waiting for
    its email verification, for which ``holds_place`` stays workstream E's own flag — false, in turn, for the pending
    administrator. The ``PATCH`` answer carries the flag of the account as it returns it, the one ``GET /users`` lists
    right after. Nothing else changes in either answer: an account is exactly its nine fields, ``usage`` counts as before.
14. ``PATCH /users/{user_id}`` refuses to activate that account (decision of the coordinator, 16/10): a body with
    ``is_active: true`` — alone, or with ``is_superuser`` either way — is 409 ``PENDING_SETUP``, ``detail: {error_code,
    message}``, and changes nothing, all or nothing: its password is a secret nobody knows, and the way in is a setup
    link. Its link live or expired, alike. Every other inactive account is activated as before, and a ``PATCH`` that
    leaves the pending administrator waiting still answers 200.

Coded refusals are read from ``detail.error_code``, the shape ``POST /auth/login`` gives ``ACCOUNT_DISABLED`` and
``test_registration_api.py`` reads; the administrator's ``USER_LIMIT_REACHED`` carries ``limit``, ``used`` and
``billing_url`` in the same ``detail``.

Where each case runs, and why. The lane is shared: its registration mode is one row on which every unit's
registrations depend, the ``LIBREFOLIO_*`` variables are read by the lane's server (another process), and «the last
active administrator» depends on every account of the lane's database. So:

- **on the lane's server** run only the cases that hold whatever the neighbours do. Each test registers its own accounts
  (its administrator promoted through ``user_service``, never a shared E2E user), acts only on them and on the tokens
  they hold or issue, finds every row by id, and never counts the lane: ``used`` is only bounded below by the test's own
  active accounts. Deactivating or demoting one of its accounts is deterministic there, because the caller is an active
  administrator who is never the target. The lane must be ``open``, as every unit that registers its users needs it;
  nothing here writes a setting. Teardown deletes the test's tokens (by id, issuer, consumer and marker e-mail), then its
  accounts, after a red too;
- **in-process**, on a private SQLite file under ``tmp_path``, run the cases that need a mode, a limit, a public or
  billing URL, «the last administrator», an expired token or exact counts: the real routers of auth, users and settings,
  mounted as ``api/v1/router.py`` mounts them, in an app of this test whose ``get_session_generator`` opens sessions on
  that file. The variables are set with ``monkeypatch`` in this process only. Two assumptions follow: the endpoints take
  their session from ``get_session_generator``, as every handler does, and the accessors of ``config/accounts.py`` read
  the environment at each call.

A6a's cases follow the same split. On the lane: the deletion and its preview on accounts and brokers the case writes
(brokers and transactions straight into the lane's database, recorded once committed and deleted at teardown by id),
the refusals that hold whatever the neighbours do (``SELF_DELETION``, ``DEMOTE_FIRST``), and «nobody is protected
today». In-process: the hook (``user_service.account_protection``, replaced with ``monkeypatch``), the log, the technical
failure. Their private database is not built by ``create_all`` but taken to head by the real migrations — in a child
process, once for the module, then copied per test —: the models do not declare the ``ON DELETE CASCADE`` that
``broker_user_access`` has in ``001_initial``, and a deletion relies on it. The BRIM report directory moves under
``tmp_path`` there, because private broker ids start at 1 like the lane's, and ``delete_files_for_brokers`` is replaced
by a spy. Assumed: the routes reach the hook as ``user_service.account_protection`` and the report cleanup as
``brim_provider.delete_files_for_brokers`` or a name ``user_service`` imported, the two names the spy replaces.

A7b's cases run in-process only, on the private instance of ``create_all``. A pending administrator is an inactive
superuser that ``pending_admin``, ``issue_setup_link`` and ``user_usage`` read: in the lane's database every concurrent
unit would see it, and a run killed mid-test would leave it behind (the reason ``test_admin_setup_api.py`` gives). There
the bootstrap itself makes it — ``run_admin_bootstrap`` on the instance still empty, the configuration handed to the
service with a token the test holds, so that ``POST /auth/setup`` can spend it; run the link's lifetime and a minute
ago when the case wants that link expired —, and every other state of a setup link is a row and tokens of the token
service, an expired link issued the same way, never waited for. Its cleanup is the private file's. On the lane, the
field is read by UADM-003, UADM-007 and UADM-008: false on every account they own.

The unit is therefore write-scoped (the ``api`` category's default), with no ``exclusive_because``. bcrypt runs at its
lowest cost in this process (``auth_service.BCRYPT_ROUNDS = 4``, as in ``test_registration_api.py``); the lane's server
keeps its own.

Red until A5a: the routes do not exist. Red until A6a: the two routes UADM-001 now also covers, UADM-040 to UADM-043,
UADM-050 to UADM-054, and the ``protected`` field UADM-003, UADM-007, UADM-008 and UADM-028 now expect on every account.
Red until A7b: UADM-060 to UADM-065, on the missing ``pending_setup`` and the missing refusal; and UADM-003, UADM-007,
UADM-008 and UADM-028 again, whose accounts must now be exactly nine fields. UADM-066 and UADM-067 are the guards of
UADM-065, green today: what the refusal must not reach.
"""

import ast
import contextlib
import inspect
import logging
import re
import sqlite3
import textwrap
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
import structlog
from fastapi import FastAPI
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app import logging_config
from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import settings as settings_api
from backend.app.api.v1 import users as users_api
from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.config.accounts import AdminBootstrapConfig
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, Broker, BrokerUserAccess, GlobalSetting, OnboardingFlow, Transaction, TransactionType, User, UserOnboardingProgress, UserRole
from backend.app.db.session import get_async_engine, get_session_generator
from backend.app.schemas.brokers import BRDeleteItem
from backend.app.schemas.users import AdminUserRead
from backend.app.services.accounts import auth_service, registration_service, user_service
from backend.app.services.accounts.bootstrap_admin_service import BootstrapAction, run_admin_bootstrap
from backend.app.services.accounts.onboarding_service import ONBOARDING_FLOW_STEPS, ONBOARDING_FLOW_VERSIONS
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus, consume_token, hash_token, inspect_token, issue_token, revoke_tokens
from backend.app.services.brim import brim_provider
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_db.test_autoincrement_schema import _alembic_upgrade_head
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME

INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
ADMIN_SETUP = AccountTokenPurpose.ADMIN_SETUP
EMAIL_VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION

REGISTRATION_VARIABLE = "LIBREFOLIO_REGISTRATION"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
BILLING_URL_VARIABLE = "LIBREFOLIO_BILLING_URL"
ACCOUNTS_VARIABLES = (REGISTRATION_VARIABLE, MAX_USERS_VARIABLE, PUBLIC_URL_VARIABLE, BILLING_URL_VARIABLE)
MODE_KEY = "registration_mode"

#: Set with a trailing slash on purpose: a link is the URL without it, then the path.
PUBLIC_URL = "https://librefolio.example.test/base/"
PUBLIC_ORIGIN = "https://librefolio.example.test/base"
BILLING_LINK = "https://billing.example.test/plans/family"

USER_ITEM_KEYS = frozenset({"id", "username", "email", "is_active", "is_superuser", "created_at", "protected", "holds_place", "pending_setup"})
INVITE_ITEM_KEYS = frozenset({"id", "grants_admin", "email", "created_at", "expires_at", "created_by_user_id"})
USAGE_KEYS = frozenset({"used", "max_users", "billing_url"})
ISSUED_INVITE_KEYS = frozenset({"invite", "token", "path", "url"})
RESET_LINK_KEYS = frozenset({"token", "path", "url", "expires_at"})
#: secrets.token_urlsafe(32): 43 URL-safe characters.
TOKEN_SHAPE = re.compile(r"[A-Za-z0-9_-]{43}")
#: The page of each kind of link; the token follows in the fragment, ``#token=…``.
LINK_PAGES = {INVITE: "/invite", PASSWORD_RESET: "/reset-password"}
#: GET /auth/me's answer to a cookie whose session was ended.
SESSION_EXPIRED = (401, {"detail": "Session expired or invalid"})

PRIVATE_PASSWORD = "Users-Admin-Api-2026"
NEW_PASSWORD = "Reset-By-Link-2026"
THIRD_PASSWORD = "Reset-Again-2026"
#: Far above any id a private database of a few rows reaches.
NEVER_ISSUED_ID = 987_654_321
CANARY = "canary: the capture sees the events of the admin endpoints' logger"

STEP_FLOWS = {flow.value: tuple(steps) for flow, steps in ONBOARDING_FLOW_STEPS.items()}

# Lot A6a: the deletion of an account by an administrator, and the hook of lot A7.
#: The one event an administrator's deletion logs, word for word, and the fields it carries.
ADMIN_DELETION_EVENT = "Account deleted by an administrator"
ADMIN_DELETION_FIELDS = ("user_id", "username", "admin_id", "brokers_deleted", "files_removed")
#: What the in-process stand-in of the hook answers for an account it protects.
PROTECTION_REASON = "the paying administrator of this managed instance"
#: What the spy of delete_files_for_brokers answers: a count no real call on an empty directory could give.
FILES_REMOVED = 2
TRANSACTION_DATE = date(2026, 1, 5)
NOTHING_WAS_DELETED = "nothing was deleted"

# Lot A7b: the pending administrator in the Users tab (contract C5).
#: The F02 administrator the configuration of a private instance names (LIBREFOLIO_ADMIN_USERNAME, LIBREFOLIO_ADMIN_EMAIL), handed to the bootstrap.
F02_USERNAME = "f02_admin"
F02_EMAIL = "f02-admin@example.com"
#: The password the pending administrator chooses through its setup link: it meets the rules (decision 37).
SETUP_PASSWORD = "Setup-Admin-Pass-2026"


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the lane cases only (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# SHARED HELPERS
# ============================================================================


@dataclass(frozen=True)
class _Account:
    """An account one test created."""

    user_id: int
    username: str
    email: str
    password: str


@dataclass(frozen=True)
class _Signed:
    """An account with the session cookie of one device."""

    account: _Account
    cookie: str


def _expect(violations: list[str], ok: bool, message: str) -> None:
    """Record a broken expectation instead of stopping at the first one: the red lists them all."""
    if not ok:
        violations.append(message)


def _verdict(violations: list[str]) -> str:
    return "\n- " + "\n- ".join(violations)


def _detail(response: httpx.Response) -> dict[str, Any]:
    """``detail`` of a coded refusal as a mapping; {} when the body carries none."""
    try:
        body = response.json()
    except ValueError:
        return {}
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail if isinstance(detail, dict) else {}


def _refusal(response: httpx.Response) -> tuple[int, Optional[str]]:
    """(status, ``detail.error_code``): (201, None) for a success."""
    return response.status_code, _detail(response).get("error_code")


def _counts(response: httpx.Response) -> dict[str, Any]:
    """What the administrator's ``USER_LIMIT_REACHED`` says, read from ``detail``: the code, the limit, the seats used, the billing link."""
    detail = _detail(response)
    return {key: detail.get(key) for key in ("error_code", "limit", "used", "billing_url")}


def _answer(response: httpx.Response) -> tuple[int, Any]:
    """The status and the JSON body (the text when it is not JSON)."""
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


def _session_cookie(response: httpx.Response) -> Optional[str]:
    """The value of the response's ``session`` Set-Cookie, parsed by name; None when there is none."""
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == COOKIE and value:
            return value
    return None


def _instant(text: Any) -> Optional[datetime]:
    """An API timestamp as an aware UTC datetime (a naive one is UTC); None when it is not a timestamp."""
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _comparable(item: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """An item with its timestamps as instants: two serialisations of the same moment compare equal."""
    if item is None:
        return None
    return {key: _instant(value) if key.endswith("_at") else value for key, value in item.items()}


def _user_item_violations(item: Any, account: _Account, *, active: bool, superuser: bool, protected: bool = False, holds_place: bool = False, pending_setup: bool = False) -> list[str]:
    """What is wrong with an account as GET /users lists it, and PATCH answers it: exactly its nine fields, with these values.

    ``protected`` is False unless the test replaced the hook: today the hook protects nobody (lot A6a).
    ``holds_place`` is workstream E's flag, true only for an inactive account whose live verification link holds its place (``api email-verification-hooks``, EVH-006…012); false unless the case wrote such a link (UADM-060).
    ``pending_setup`` is lot A7b's flag (C5), true only for the account waiting for its F02 setup (UADM-060 to UADM-064); false unless the case made one.
    """
    if not isinstance(item, dict) or set(item) != USER_ITEM_KEYS:
        return [f"{account.username}: an account must be exactly {sorted(USER_ITEM_KEYS)}, no hash and no secret: {item}"]
    expected = {"id": account.user_id, "username": account.username, "email": account.email, "is_active": active, "is_superuser": superuser, "protected": protected, "holds_place": holds_place, "pending_setup": pending_setup}
    found = {key: item[key] for key in expected}
    violations = [] if found == expected else [f"{account.username}: expected {expected}, got {found}"]
    _expect(violations, _instant(item["created_at"]) is not None, f"{account.username}: created_at is not a timestamp: {item['created_at']!r}")
    return violations


def _link_path_violations(path: Any, purpose: AccountTokenPurpose, token: str) -> list[str]:
    """What is wrong with a link's ``path``: the purpose's page, no query, and the token alone in the URL fragment (``#token=…``).

    The fragment because a browser never sends it: the token stays out of the access log and of every proxy's log.
    """
    if not isinstance(path, str):
        return [f"path: a string expected, got {path!r}"]
    parts = urlparse(path)
    found = {"page": (parts.scheme, parts.netloc, parts.path), "query": parts.query, "fragment": parse_qs(parts.fragment)}
    expected = {"page": ("", "", LINK_PAGES[purpose]), "query": "", "fragment": {"token": [token]}}
    return [] if found == expected else [f"path: expected {LINK_PAGES[purpose]}#token=<the token>, nothing in the query; got {path!r}, read as {found}"]


def _issued_invite_violations(issued: Any, *, grants_admin: bool, email: Optional[str], created_by: int) -> list[str]:
    """What is wrong with the 201 of POST /users/invites: its keys, the token, its path, the invitation and its seven days."""
    if not isinstance(issued, dict) or set(issued) != ISSUED_INVITE_KEYS:
        return [f"the 201 body must be exactly {sorted(ISSUED_INVITE_KEYS)}: {issued}"]
    token, invite = str(issued["token"]), issued["invite"]
    violations: list[str] = []
    _expect(violations, TOKEN_SHAPE.fullmatch(token) is not None, f"token: 43 URL-safe characters expected, got {token!r}")
    violations += _link_path_violations(issued["path"], INVITE, token)
    if not isinstance(invite, dict) or set(invite) != INVITE_ITEM_KEYS:
        return [*violations, f"invite: exactly {sorted(INVITE_ITEM_KEYS)} expected, got {invite}"]
    found = (invite["grants_admin"], invite["email"], invite["created_by_user_id"])
    _expect(violations, found == (grants_admin, email, created_by), f"invite: (grants_admin, email, created_by_user_id) must be {(grants_admin, email, created_by)}, got {found}")
    created, expires = _instant(invite["created_at"]), _instant(invite["expires_at"])
    lives = None if created is None or expires is None else expires - created
    _expect(violations, lives == DEFAULT_TTL[INVITE], f"invite: an invitation lives {DEFAULT_TTL[INVITE]} from its creation, this one {lives}: {invite}")
    return violations


def _reset_link_violations(link: Any) -> list[str]:
    """What is wrong with the 201 of POST /users/{id}/password-reset-link: its keys, the token, its path, its expiry."""
    if not isinstance(link, dict) or set(link) != RESET_LINK_KEYS:
        return [f"the 201 body must be exactly {sorted(RESET_LINK_KEYS)}: {link}"]
    token = str(link["token"])
    violations: list[str] = []
    _expect(violations, TOKEN_SHAPE.fullmatch(token) is not None, f"token: 43 URL-safe characters expected, got {token!r}")
    violations += _link_path_violations(link["path"], PASSWORD_RESET, token)
    _expect(violations, _instant(link["expires_at"]) is not None, f"expires_at is not a timestamp: {link['expires_at']!r}")
    return violations


def _url_violations(body: dict[str, Any], public_origin: Optional[str]) -> list[str]:
    """``url`` is the public URL (its trailing slash dropped) plus ``path``, the token still in the fragment; or null without a public URL."""
    expected = None if public_origin is None else f"{public_origin}{body.get('path')}"
    if body.get("url") != expected:
        return [f"url: expected {expected!r}, got {body.get('url')!r} (path {body.get('path')!r})"]
    url_parts = urlparse(expected) if expected else None
    in_the_fragment = url_parts is None or (url_parts.query == "" and parse_qs(url_parts.fragment) == {"token": [str(body.get("token"))]})
    return [] if in_the_fragment else [f"url: the token must travel in the fragment, not in the query: {expected!r}"]


def _onboarding_reading(body: Any) -> dict[str, tuple[str, dict[str, str]]]:
    """GET /settings/onboarding as {flow: (status, {step: status})}, steps empty for a flow without them."""
    return {item["flow"]: (item["status"], {step["step_id"]: step["status"] for step in item.get("steps") or []}) for item in body["flows"]}


def _pending(flow: str) -> tuple[str, dict[str, str]]:
    """A flow as a never-touched account reads it: pending, and every step of it pending."""
    return "pending", dict.fromkeys(STEP_FLOWS.get(flow, ()), "pending")


# ============================================================================
# THE LANE: ITS SERVER AND ITS DATABASE
# ============================================================================


def _lane_engine() -> AsyncEngine:
    """The lane's test database, the one its server serves: the lane cases read and delete their own rows there, nowhere else."""
    is_test_db, database_url = verify_test_database()
    assert is_test_db, f"Refusing to touch a database that is not the lane's test database: {database_url}"
    return get_async_engine()


@dataclass
class _LaneRows:
    """What a lane case wrote: accounts by name (even one a red let through), tokens by id, the marker e-mails of invitations, brokers by id (recorded once committed)."""

    usernames: list[str] = field(default_factory=list)
    token_ids: list[int] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    broker_ids: list[int] = field(default_factory=list)

    def new_username(self, prefix: str) -> str:
        username = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self.usernames.append(username)
        return username

    def new_email(self, prefix: str) -> str:
        email = f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"
        self.emails.append(email)
        return email


async def _delete_lane_brokers(engine: AsyncEngine, broker_ids: list[int]) -> list[str]:
    """Delete the case's brokers still there, with their transactions, whoever holds them now (no access check); what failed.

    Only ids recorded after their commit reach here: brokers have AUTOINCREMENT, so such an id was never anyone else's.
    """
    if not broker_ids:
        return []
    async with AsyncSession(engine) as session:
        try:
            surviving = sorted((await session.execute(select(Broker.id).where(Broker.id.in_(broker_ids)))).scalars().all())
            response = await BrokerService(session).delete_bulk([BRDeleteItem(id=broker_id, force=True) for broker_id in surviving], user_id=0, as_user_id="all")
            await session.commit()
        except Exception as exc:  # the accounts still get their attempt; every failure is reported together
            return [f"brokers {broker_ids}: {exc!r}"]
    return [f"broker {result.id}: {result.message}" for result in response.results if not result.success]


async def _delete_lane_rows(rows: _LaneRows) -> list[str]:
    """Delete the case's tokens (by id, issued or consumed by its accounts, or to its marker e-mails), then its brokers, then its accounts; what failed."""
    errors: list[str] = []
    engine = _lane_engine()
    async with AsyncSession(engine) as session:
        user_ids = list((await session.execute(select(User.id).where(User.username.in_(rows.usernames)))).scalars().all())
        mine = or_(AccountToken.id.in_(rows.token_ids), AccountToken.email.in_(rows.emails), AccountToken.created_by_user_id.in_(user_ids), AccountToken.consumed_by_user_id.in_(user_ids))
        try:
            await session.execute(delete(AccountToken).where(mine))
            await session.commit()
        except Exception as exc:  # the accounts still get their attempt; every failure is reported together
            errors.append(f"tokens: {exc!r}")
    errors += await _delete_lane_brokers(engine, rows.broker_ids)
    for user_id in user_ids:
        async with AsyncSession(engine) as session:
            try:
                await user_service.delete_user(session, user_id)
            except Exception as exc:
                errors.append(f"user {user_id}: {exc!r}")
    return errors


@pytest_asyncio.fixture
async def lane(test_server) -> AsyncIterator[_LaneRows]:
    """The lane's server, in its own mode (open); what the case writes there is deleted at teardown, after a red too."""
    rows = _LaneRows()
    try:
        yield rows
    finally:
        errors = await _delete_lane_rows(rows)
        assert not errors, f"Teardown: could not delete what this test wrote in the lane: {errors}"


async def _live(method: str, path: str, *, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request to the lane's server from a client of its own: no cookie jar, the session (if any) sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    async with httpx.AsyncClient() as client:
        return await client.request(method, f"{API_BASE}{path}", json=json, headers=headers, timeout=TIMEOUT)


async def _live_register(lane: _LaneRows, prefix: str) -> _Account:
    """A regular account of this case, registered over HTTP in the lane's own mode, which must be open."""
    username = lane.new_username(prefix)
    email, password = f"{username}@example.com", f"Initial-{uuid.uuid4().hex[:12]}1"
    response = await _live("POST", "/auth/register", json={"username": username, "email": email, "password": password})
    assert response.status_code == 201, f"Setup: registering {username} on the lane failed; its mode must be open, as every unit registering its own users needs it: {response.status_code} {response.text}"
    user = response.json()["user"]
    assert user["is_superuser"] is False, f"Precondition: {username} registered as the lane's first account, hence its administrator: the api setup (db populate) did not run on this lane"
    return _Account(user_id=user["id"], username=username, email=email, password=password)


async def _live_login(account: _Account, password: Optional[str] = None) -> httpx.Response:
    """POST /auth/login from a client of its own: a new device."""
    return await _live("POST", "/auth/login", json={"username": account.username, "password": password or account.password})


async def _live_sign_in(account: _Account, password: Optional[str] = None) -> str:
    """A new device of ``account``: a login, and the session cookie it sets."""
    response = await _live_login(account, password)
    cookie = _session_cookie(response)
    assert response.status_code == 200 and cookie, f"Login as {account.username} failed: {response.status_code} {response.text}"
    return cookie


async def _live_member(lane: _LaneRows, prefix: str) -> _Signed:
    """A regular account of this case, signed in on one device."""
    account = await _live_register(lane, prefix)
    return _Signed(account, await _live_sign_in(account))


async def _lane_set(username: str, *, admin: Optional[bool] = None, active: Optional[bool] = None) -> None:
    """Promote, demote, activate or deactivate one of this case's accounts through user_service, in the lane's database."""
    async with AsyncSession(_lane_engine()) as session:
        if admin is not None:
            done, error = await user_service.set_user_admin(session, username, admin)
            assert done, f"Setup: set_user_admin({username!r}, {admin}) failed: {error}"
        if active is not None:
            done, error = await user_service.set_user_active(session, username, active)
            assert done, f"Setup: set_user_active({username!r}, {active}) failed: {error}"


async def _live_admin(lane: _LaneRows) -> _Signed:
    """An administrator of this case: registered, promoted through user_service, then signed in."""
    account = await _live_register(lane, "uadm_admin")
    await _lane_set(account.username, admin=True)
    cookie = await _live_sign_in(account)
    status, body = await _live_me(cookie)
    assert status == 200 and body["user"]["is_superuser"] is True, f"Setup: {account.username} must be signed in as an administrator: {status} {body}"
    return _Signed(account, cookie)


async def _live_me(cookie: str) -> tuple[int, Any]:
    """GET /auth/me with this session cookie only."""
    return _answer(await _live("GET", "/auth/me", cookie=cookie))


async def _live_me_id(cookie: str) -> Optional[int]:
    """The id of the account this cookie is a session of; None when GET /auth/me refuses it."""
    status, body = await _live_me(cookie)
    return body["user"]["id"] if status == 200 else None


async def _listed(cookie: str, path: str, item_id: int) -> Optional[dict[str, Any]]:
    """The item of id ``item_id`` in GET ``path`` (/users or /users/invites) as this administrator sees it, found by id; None when absent."""
    response = await _live("GET", path, cookie=cookie)
    assert response.status_code == 200, f"GET {path} as an administrator: expected 200, got {response.status_code} {response.text}"
    return next((item for item in response.json()["items"] if item.get("id") == item_id), None)


async def _live_register_with(lane: _LaneRows, prefix: str, invite_token: str) -> tuple[str, httpx.Response]:
    """POST /auth/register with ``invite_token``, for a new username of this case."""
    username = lane.new_username(prefix)
    body = {"username": username, "email": f"{username}@example.com", "password": f"Invited-{uuid.uuid4().hex[:12]}1", "invite_token": invite_token}
    return username, await _live("POST", "/auth/register", json=body)


async def _live_reset_password(token: str, new_password: str) -> httpx.Response:
    """POST /auth/password-reset, anonymous: whoever holds the link."""
    return await _live("POST", "/auth/password-reset", json={"token": token, "new_password": new_password})


async def _admin_reset_link(admin: _Signed, user_id: int) -> str:
    """A reset link for ``user_id``, issued by ``admin`` through the API: its token."""
    response = await _live("POST", f"/users/{user_id}/password-reset-link", cookie=admin.cookie)
    assert response.status_code == 201, f"POST /users/{user_id}/password-reset-link: expected 201, got {response.status_code} {response.text}"
    return response.json()["token"]


async def _live_onboarding(cookie: str) -> dict[str, tuple[str, dict[str, str]]]:
    """The account's own onboarding, read from GET /settings/onboarding with its session."""
    response = await _live("GET", "/settings/onboarding", cookie=cookie)
    assert response.status_code == 200, f"GET /settings/onboarding: {response.status_code} {response.text}"
    return _onboarding_reading(response.json())


async def _live_onboarding_move(cookie: str, flow: OnboardingFlow, action: str, step: Optional[str] = None) -> None:
    """Complete or skip a flow, or one of its steps, as the account itself does from the app."""
    path = f"/settings/onboarding/{flow.value}/{action}" if step is None else f"/settings/onboarding/{flow.value}/steps/{step}/{action}"
    response = await _live("POST", path, cookie=cookie, json={"expected_version": ONBOARDING_FLOW_VERSIONS[flow]})
    assert response.status_code == 200, f"Setup: POST {path}: {response.status_code} {response.text}"


async def _lane_user(user_id: int) -> tuple[bool, bool, int]:
    """(is_active, is_superuser, session_version) of one of this case's accounts, read fresh from the lane's database."""
    async with AsyncSession(_lane_engine()) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == user_id))).one()
    return bool(row[0]), bool(row[1]), int(row[2])


async def _lane_user_id(username: str) -> Optional[int]:
    async with AsyncSession(_lane_engine()) as session:
        return (await session.execute(select(User.id).where(User.username == username))).scalar_one_or_none()


async def _lane_issue(lane: _LaneRows, purpose: AccountTokenPurpose, **arguments: Any) -> IssuedToken:
    """A token issued by token_service directly in the lane's database, committed, and recorded for the teardown."""
    async with AsyncSession(_lane_engine(), expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    lane.token_ids.append(issued.record.id)
    return issued


async def _lane_consume(token: str, purpose: AccountTokenPurpose, consumed_by_user_id: int) -> None:
    async with AsyncSession(_lane_engine()) as session:
        record = await consume_token(session, token, purpose, consumed_by_user_id=consumed_by_user_id)
        await session.commit()
    assert record is not None, "Setup: the token must be consumed"


async def _lane_token_of(token: str) -> Optional[AccountToken]:
    """The lane's row of a plaintext token, found by its hash as stored."""
    async with AsyncSession(_lane_engine(), expire_on_commit=False) as session:
        return (await session.execute(select(AccountToken).where(AccountToken.token_hash == hash_token(token)))).scalars().first()


async def _lane_token_state(token_id: int) -> tuple[Any, Any, Any]:
    """(purpose, consumed_at, revoked_at) of one of this case's tokens."""
    async with AsyncSession(_lane_engine()) as session:
        row = (await session.execute(select(AccountToken.purpose, AccountToken.consumed_at, AccountToken.revoked_at).where(AccountToken.id == token_id))).one()
    return row[0], row[1], row[2]


async def _lane_reset_links(user_id: int) -> int:
    """How many reset links this case's account has ever had: it owns them all."""
    async with AsyncSession(_lane_engine()) as session:
        statement = select(func.count()).select_from(AccountToken).where(AccountToken.user_id == user_id, AccountToken.purpose == PASSWORD_RESET.value)
        return int((await session.execute(statement)).scalar_one())


# ============================================================================
# LANE: ONLY AN ADMINISTRATOR, AND A REFUSED CALL CHANGES NOTHING
# ============================================================================


@dataclass(frozen=True)
class _Scene:
    """An administrator, an ordinary account (the refused caller), a target account signed in with intro_tour completed, a live invitation, and an e-mail no invitation carries yet."""

    admin: _Signed
    member: _Signed
    target: _Signed
    invite_id: int
    marker_email: str


async def _scene(lane: _LaneRows) -> _Scene:
    admin = await _live_admin(lane)
    member = await _live_member(lane, "uadm_member")
    target = await _live_member(lane, "uadm_target")
    await _live_onboarding_move(target.cookie, OnboardingFlow.INTRO_TOUR, "complete")
    invite = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
    return _Scene(admin=admin, member=member, target=target, invite_id=invite.record.id, marker_email=lane.new_email("uadm_marker"))


async def _footprint(scene: _Scene) -> dict[str, Any]:
    """Everything an admin route could change in the scene, read fresh from the lane's database; the target None once it is gone."""
    target_id = scene.target.account.user_id
    async with AsyncSession(_lane_engine()) as session:
        target = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == target_id))).one_or_none()
        invite = (await session.execute(select(AccountToken.consumed_at, AccountToken.revoked_at).where(AccountToken.id == scene.invite_id))).one()
        marker = (await session.execute(select(func.count()).select_from(AccountToken).where(AccountToken.email == scene.marker_email))).scalar_one()
        tour = (await session.execute(select(UserOnboardingProgress.status).where(UserOnboardingProgress.user_id == target_id, UserOnboardingProgress.flow == OnboardingFlow.INTRO_TOUR.value))).scalar_one_or_none()
    return {
        "the target (is_active, is_superuser, session_version)": None if target is None else tuple(target),
        "the scene's invitation (consumed_at, revoked_at)": tuple(invite),
        "invitations to the marker e-mail": marker,
        "reset links of the target": await _lane_reset_links(target_id),
        "the target's intro_tour": tour,
    }


@dataclass(frozen=True)
class _Route:
    """An admin route as the matrix calls it, with the status an administrator gets."""

    method: str
    path: Callable[[_Scene], str]
    body: Callable[[_Scene], Any]
    success: int


def _on_target(suffix: str) -> Callable[[_Scene], str]:
    return lambda scene: f"/users/{scene.target.account.user_id}{suffix}"


def _no_body(scene: _Scene) -> None:
    return None


ADMIN_ROUTES = [
    pytest.param(_Route("GET", lambda scene: "/users/invites", _no_body, 200), id="list-invites"),
    pytest.param(_Route("POST", lambda scene: "/users/invites", lambda scene: {"grants_admin": True, "email": scene.marker_email}, 201), id="create-invite"),
    pytest.param(_Route("DELETE", lambda scene: f"/users/invites/{scene.invite_id}", _no_body, 204), id="revoke-invite"),
    pytest.param(_Route("GET", lambda scene: "/users", _no_body, 200), id="list-users"),
    pytest.param(_Route("PATCH", _on_target(""), lambda scene: {"is_active": False}, 200), id="deactivate-user"),
    pytest.param(_Route("POST", _on_target("/password-reset-link"), _no_body, 201), id="reset-link"),
    pytest.param(_Route("POST", _on_target("/sessions/revoke"), _no_body, 204), id="revoke-sessions"),
    pytest.param(_Route("POST", _on_target("/onboarding/reset"), lambda scene: {}, 204), id="reset-onboarding"),
    # Lot A6a. In every case the administrator's call comes last: after the 204 the target is gone, and nothing reads the scene again.
    pytest.param(_Route("GET", _on_target("/deletion-preview"), _no_body, 200), id="deletion-preview"),
    pytest.param(_Route("DELETE", _on_target(""), _no_body, 204), id="delete-user"),
]


class TestOnlyAnAdministrator:
    """Every admin route on the lane's server: anonymous 401, an ordinary account 403, neither changes anything; the administrator gets through."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    async def test_anonymous_401_ordinary_403_nothing_changes_and_the_administrator_gets_through(self, lane: _LaneRows, route: _Route) -> None:
        """UADM-001: no session → 401, an ordinary account's session → 403, and after each the scene is as it was (the target's state and sessions, the invitation, no invitation issued, no reset link, the onboarding); then the administrator gets the route's success status.

        Each call acts on what a wrongly open route would visibly change: the deactivation of the target, an invitation to a
        marker e-mail, the revocation of a live invitation, the target's sessions, reset links and completed intro_tour, and
        (lot A6a) the target itself, which a wrongly open DELETE would remove. The preview of its deletion changes nothing
        whoever calls it: there only the status codes speak.
        """
        scene = await _scene(lane)
        path, body = route.path(scene), route.body(scene)
        print_section(f"UADM-001: {route.method} {path} is for administrators only")
        before = await _footprint(scene)

        anonymous = await _live(route.method, path, json=body)
        after_anonymous = await _footprint(scene)
        ordinary = await _live(route.method, path, cookie=scene.member.cookie, json=body)
        after_ordinary = await _footprint(scene)
        admin = await _live(route.method, path, cookie=scene.admin.cookie, json=body)

        violations: list[str] = []
        _expect(violations, anonymous.status_code == 401, f"anonymous: expected 401, got {anonymous.status_code} {anonymous.text}")
        _expect(violations, after_anonymous == before, f"the anonymous call changed the lane: {before} → {after_anonymous}")
        _expect(violations, ordinary.status_code == 403, f"an ordinary account: expected 403, got {ordinary.status_code} {ordinary.text}")
        _expect(violations, after_ordinary == before, f"the ordinary account's call changed the lane: {before} → {after_ordinary}")
        _expect(violations, admin.status_code == route.success, f"the administrator: expected {route.success}, got {admin.status_code} {admin.text}")
        assert not violations, f"{route.method} {path} must be an administrator's route only:{_verdict(violations)}"
        print_success(f"{route.method} {path}: 401, 403, nothing changed, then {route.success} for the administrator")

    @pytest.mark.asyncio
    async def test_an_ordinary_account_cannot_make_itself_an_administrator_nor_mint_its_own_reset_link(self, lane: _LaneRows) -> None:
        """UADM-002: an ordinary account aiming the routes at itself — PATCH {is_superuser: true}, POST its own reset link — gets 403 for both, and is still an ordinary account with no reset link."""
        print_section("UADM-002: no route makes an ordinary account an administrator of itself")
        member = await _live_member(lane, "uadm_climber")
        user_id = member.account.user_id
        before = await _lane_user(user_id)

        promote = await _live("PATCH", f"/users/{user_id}", cookie=member.cookie, json={"is_superuser": True})
        link = await _live("POST", f"/users/{user_id}/password-reset-link", cookie=member.cookie)

        violations: list[str] = []
        _expect(violations, promote.status_code == 403, f"PATCH /users/{{self}} {{is_superuser: true}}: expected 403, got {promote.status_code} {promote.text}")
        _expect(violations, link.status_code == 403, f"POST /users/{{self}}/password-reset-link: expected 403, got {link.status_code} {link.text}")
        _expect(violations, await _lane_user(user_id) == before, f"the account changed: {before} → {await _lane_user(user_id)}")
        _expect(violations, await _lane_reset_links(user_id) == 0, "a reset link was issued to the account that asked for it")
        assert not violations, f"An ordinary account must not reach the admin routes, not even about itself:{_verdict(violations)}"
        print_success("403 twice, still an ordinary account, no reset link")


# ============================================================================
# LANE: THE ACCOUNTS AND THE INVITATIONS
# ============================================================================


class TestAccountsListOnTheLane:
    @pytest.mark.asyncio
    async def test_lists_this_cases_accounts_with_their_flags_and_the_usage(self, lane: _LaneRows) -> None:
        """UADM-003: GET /users → {items, usage}; this case's four accounts are there, found by id — the caller, an ordinary account, a second administrator, an inactive account — each exactly {id, username, email, is_active, is_superuser, created_at, protected} with the right flags, protected false (A6a: the hook protects nobody today); usage is {used, max_users, billing_url}, and used counts at least this case's three active accounts."""
        print_section("UADM-003: GET /users")
        admin = await _live_admin(lane)
        member = await _live_register(lane, "uadm_listed")
        second_admin = await _live_register(lane, "uadm_listed_admin")
        inactive = await _live_register(lane, "uadm_listed_off")
        await _lane_set(second_admin.username, admin=True)
        await _lane_set(inactive.username, active=False)

        response = await _live("GET", "/users", cookie=admin.cookie)

        assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
        body = response.json()
        assert isinstance(body, dict) and set(body) == {"items", "usage"}, f"GET /users must answer exactly {{items, usage}}: {body}"
        items = {item.get("id"): item for item in body["items"]}
        violations: list[str] = []
        for account, active, superuser in ((admin.account, True, True), (member, True, False), (second_admin, True, True), (inactive, False, False)):
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser)
        usage = body["usage"]
        _expect(violations, isinstance(usage, dict) and set(usage) == USAGE_KEYS, f"usage must be exactly {sorted(USAGE_KEYS)}: {usage}")
        _expect(violations, isinstance(usage, dict) and isinstance(usage.get("used"), int) and usage["used"] >= 3, f"usage.used counts the active accounts, this case's three at least: {usage}")
        assert not violations, f"GET /users broke its contract:{_verdict(violations)}"
        print_success("four accounts of this case listed with their flags, usage present")


class TestInvitationsOnTheLane:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("grants_admin", "with_email"), [pytest.param(False, False, id="user-invitation"), pytest.param(True, True, id="admin-invitation-with-email")])
    async def test_an_invitation_is_listed_opens_one_account_in_its_role_then_is_gone(self, lane: _LaneRows, grants_admin: bool, with_email: bool) -> None:
        """UADM-004: POST /users/invites → 201 {invite, token, path, url}; GET /users/invites lists exactly that invitation; its token registers one account through POST /auth/register, in the invitation's role; then the invitation is no longer listed, its row is consumed by that account, and the same token registers nobody else (400 INVITE_INVALID)."""
        print_section(f"UADM-004: the life of an invitation, grants_admin={grants_admin}")
        admin = await _live_admin(lane)
        email = lane.new_email("uadm_invitee") if with_email else None
        request = {"grants_admin": grants_admin, **({"email": email} if email else {})}

        created = await _live("POST", "/users/invites", cookie=admin.cookie, json=request)

        assert created.status_code == 201, f"POST /users/invites: expected 201, got {created.status_code} {created.text}"
        issued = created.json()
        violations = _issued_invite_violations(issued, grants_admin=grants_admin, email=email, created_by=admin.account.user_id)
        assert not violations, f"POST /users/invites answered a 201 that breaks its contract:{_verdict(violations)}"
        token, invite = issued["token"], issued["invite"]
        lane.token_ids.append(invite["id"])
        _expect(violations, issued["url"] is None or issued["url"].endswith(issued["path"]), f"url must be null or end with the path: {issued}")
        listed = await _listed(admin.cookie, "/users/invites", invite["id"])
        _expect(violations, _comparable(listed) == _comparable(invite), f"GET /users/invites must list the invitation as it was created: listed {listed}, created {invite}")
        row = await _lane_token_of(token)
        _expect(violations, row is not None and row.id == invite["id"] and row.purpose == INVITE.value and row.consumed_at is None, f"the token must be the stored hash of the live invitation {invite['id']}: {row}")
        assert not violations, f"the new invitation is not what was asked:{_verdict(violations)}"

        _, registered = await _live_register_with(lane, "uadm_invited", token)

        assert registered.status_code == 201, f"POST /auth/register with the invitation: expected 201, got {registered.status_code} {registered.text}"
        user = registered.json()["user"]
        _expect(violations, user["is_superuser"] is grants_admin, f"the account must take the invitation's role, is_superuser={grants_admin}: {user}")
        _expect(violations, await _listed(admin.cookie, "/users/invites", invite["id"]) is None, "a consumed invitation must no longer be listed")
        row = await _lane_token_of(token)
        _expect(violations, row is not None and row.consumed_by_user_id == user["id"], f"the invitation must be consumed by the account it opened: {row}")
        again_username, again = await _live_register_with(lane, "uadm_invited_again", token)
        _expect(violations, _refusal(again) == (400, "INVITE_INVALID"), f"a consumed invitation must register nobody else: {again.status_code} {again.text}")
        _expect(violations, await _lane_user_id(again_username) is None, f"{again_username} was created with a consumed invitation")
        assert not violations, f"An invitation must open one account, in its role, once:{_verdict(violations)}"
        print_success(f"listed, opened {user['username']} (is_superuser={grants_admin}), then gone and spent")

    @pytest.mark.asyncio
    async def test_a_revoked_invitation_is_gone_and_opens_nothing(self, lane: _LaneRows) -> None:
        """UADM-005: DELETE /users/invites/{id} → 204 with no body; the invitation is no longer listed and its row is revoked; a second DELETE → 404; its token → 400 INVITE_INVALID at POST /auth/register, and no account."""
        print_section("UADM-005: a revoked invitation")
        admin = await _live_admin(lane)
        created = await _live("POST", "/users/invites", cookie=admin.cookie, json={"grants_admin": False})
        assert created.status_code == 201, f"POST /users/invites: expected 201, got {created.status_code} {created.text}"
        invite_id, token = created.json()["invite"]["id"], created.json()["token"]
        lane.token_ids.append(invite_id)

        revoked = await _live("DELETE", f"/users/invites/{invite_id}", cookie=admin.cookie)
        again = await _live("DELETE", f"/users/invites/{invite_id}", cookie=admin.cookie)
        username, registered = await _live_register_with(lane, "uadm_revoked_invitee", token)

        violations: list[str] = []
        _expect(violations, (revoked.status_code, revoked.content) == (204, b""), f"DELETE: expected 204 with no body, got {revoked.status_code} {revoked.text}")
        _expect(violations, await _listed(admin.cookie, "/users/invites", invite_id) is None, "a revoked invitation must no longer be listed")
        purpose, consumed_at, revoked_at = await _lane_token_state(invite_id)
        _expect(violations, revoked_at is not None and consumed_at is None, f"the row must be revoked, not consumed: consumed_at={consumed_at}, revoked_at={revoked_at}")
        _expect(violations, again.status_code == 404, f"a second DELETE: expected 404, got {again.status_code} {again.text}")
        _expect(violations, _refusal(registered) == (400, "INVITE_INVALID"), f"a revoked invitation must register nobody: {registered.status_code} {registered.text}")
        _expect(violations, await _lane_user_id(username) is None, f"{username} was created with a revoked invitation")
        assert not violations, f"A revoked invitation must be gone:{_verdict(violations)}"
        print_success("204, unlisted, 404 the second time, its token opens nothing")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["consumed-invitation", "live-reset-link"])
    async def test_what_is_not_a_live_invitation_cannot_be_revoked_and_stays_as_it_was(self, lane: _LaneRows, kind: str) -> None:
        """UADM-006: DELETE /users/invites/{id} of a consumed invitation, or of the id of a live password-reset link → 404, and the row is untouched: the reset link stays live.

        Presence barrier first: a live invitation of this case is revoked with 204. A route that does not exist answers 404 too.
        """
        print_section(f"UADM-006: DELETE /users/invites/{{id}} of a {kind}")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_holder")
        barrier = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
        revoked = await _live("DELETE", f"/users/invites/{barrier.record.id}", cookie=admin.cookie)
        assert revoked.status_code == 204, f"Presence barrier: DELETE of a live invitation of this case must answer 204, or the 404 below proves nothing: {revoked.status_code} {revoked.text}"
        if kind == "live-reset-link":
            issued = await _lane_issue(lane, PASSWORD_RESET, user_id=holder.user_id)
        else:
            issued = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
            await _lane_consume(issued.token, INVITE, holder.user_id)
        before = await _lane_token_state(issued.record.id)

        response = await _live("DELETE", f"/users/invites/{issued.record.id}", cookie=admin.cookie)

        assert response.status_code == 404, f"only a live invitation can be revoked: expected 404 for a {kind}, got {response.status_code} {response.text}"
        assert await _lane_token_state(issued.record.id) == before, f"the {kind} changed: {before} → {await _lane_token_state(issued.record.id)}"
        print_success(f"{kind}: 404, untouched")


# ============================================================================
# LANE: STATE AND ROLE OF AN ACCOUNT
# ============================================================================


UNKNOWN_ACCOUNT_ROUTES = [
    pytest.param("PATCH", "", {"is_active": False}, 200, id="patch"),
    pytest.param("POST", "/password-reset-link", None, 201, id="reset-link"),
    pytest.param("POST", "/sessions/revoke", None, 204, id="revoke-sessions"),
    pytest.param("POST", "/onboarding/reset", {}, 204, id="reset-onboarding"),
]


class TestAccountStateOnTheLane:
    """PATCH /users/{id} on this case's own accounts. The caller is an active administrator and never the target, so the last-administrator guard never applies here, whatever the lane holds."""

    @pytest.mark.asyncio
    async def test_deactivation_ends_the_sessions_and_reactivation_does_not_bring_them_back(self, lane: _LaneRows) -> None:
        """UADM-007: PATCH {is_active: false} → 200 with the account; its cookie is refused (401), its password gets 403 ACCOUNT_DISABLED, its session version rose by one. PATCH {is_active: true} → 200; the old cookie stays refused (401 «Session expired or invalid»), the version does not move, a new login works."""
        print_section("UADM-007: deactivate, then reactivate")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_paused")
        account, user_id = member.account, member.account.user_id
        _, _, version = await _lane_user(user_id)

        off = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_active": False})
        assert off.status_code == 200, f"PATCH {{is_active: false}}: expected 200, got {off.status_code} {off.text}"
        violations = _user_item_violations(off.json(), account, active=False, superuser=False)
        old_cookie_while_off = await _live_me(member.cookie)
        login_while_off = await _live_login(account)
        state_while_off = await _lane_user(user_id)
        on = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_active": True})

        _expect(violations, old_cookie_while_off[0] == 401, f"a deactivated account's cookie must be refused: GET /auth/me {old_cookie_while_off}")
        _expect(violations, _refusal(login_while_off) == (403, "ACCOUNT_DISABLED"), f"the right password of a deactivated account: expected 403 ACCOUNT_DISABLED, got {login_while_off.status_code} {login_while_off.text}")
        _expect(violations, state_while_off == (False, False, version + 1), f"deactivation must end the sessions, version + 1: {state_while_off}, version before {version}")
        assert on.status_code == 200, f"PATCH {{is_active: true}}: expected 200, got {on.status_code} {on.text}" + (" — the lane's server runs with LIBREFOLIO_MAX_USERS, which no unit may set" if _refusal(on) == (409, "USER_LIMIT_REACHED") else "")
        violations += _user_item_violations(on.json(), account, active=True, superuser=False)
        _expect(violations, await _live_me(member.cookie) == SESSION_EXPIRED, f"reactivation must not bring the old session back: GET /auth/me {await _live_me(member.cookie)}")
        _expect(violations, await _lane_user(user_id) == (True, False, version + 1), f"reactivation must not move the version: {await _lane_user(user_id)}")
        _expect(violations, await _live_me_id(await _live_sign_in(account)) == user_id, "a new login after the reactivation must work")
        assert not violations, f"Deactivation and reactivation broke their contract:{_verdict(violations)}"
        print_success("deactivated: sessions ended, login refused; reactivated: old cookie still refused, new login works")

    @pytest.mark.asyncio
    async def test_promotion_keeps_the_session_and_demotion_ends_it(self, lane: _LaneRows) -> None:
        """UADM-008: PATCH {is_superuser: true} → 200; the same cookie now reaches GET /users, the version unchanged. PATCH {is_superuser: false} → 200; that cookie is refused (401 «Session expired or invalid»), the version rose by one, and a new login gets 403 from GET /users."""
        print_section("UADM-008: promote, then demote")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_promoted")
        account, user_id = member.account, member.account.user_id
        _, _, version = await _lane_user(user_id)
        before = await _live("GET", "/users", cookie=member.cookie)

        up = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_superuser": True})
        assert up.status_code == 200, f"PATCH {{is_superuser: true}}: expected 200, got {up.status_code} {up.text}"
        violations = _user_item_violations(up.json(), account, active=True, superuser=True)
        promoted = await _live("GET", "/users", cookie=member.cookie)
        state_promoted = await _lane_user(user_id)
        down = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_superuser": False})

        _expect(violations, before.status_code == 403, f"Precondition: an ordinary account gets 403 from GET /users, got {before.status_code}")
        _expect(violations, promoted.status_code == 200, f"promotion ends no session: the same cookie must now reach GET /users, got {promoted.status_code} {promoted.text}")
        _expect(violations, state_promoted == (True, True, version), f"promotion must not move the version: {state_promoted}, before {version}")
        assert down.status_code == 200, f"PATCH {{is_superuser: false}}: expected 200, got {down.status_code} {down.text}"
        violations += _user_item_violations(down.json(), account, active=True, superuser=False)
        _expect(violations, await _live_me(member.cookie) == SESSION_EXPIRED, f"demotion must end the sessions: GET /auth/me {await _live_me(member.cookie)}")
        _expect(violations, await _lane_user(user_id) == (True, False, version + 1), f"demotion: version + 1: {await _lane_user(user_id)}")
        fresh = await _live_sign_in(account)
        _expect(violations, (await _live("GET", "/users", cookie=fresh)).status_code == 403, "after the demotion a new login must be an ordinary account again (403 from GET /users)")
        assert not violations, f"Promotion and demotion broke their contract:{_verdict(violations)}"
        print_success("promoted: same session, admin routes open; demoted: session ended, routes closed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("method", "suffix", "body", "success"), UNKNOWN_ACCOUNT_ROUTES)
    async def test_an_account_that_does_not_exist_is_404(self, lane: _LaneRows, method: str, suffix: str, body: Any, success: int) -> None:
        """UADM-009: the id of an account this case created and deleted (ids of users are never reused: AUTOINCREMENT) → 404.

        Presence barrier first: the same call on an existing account of this case gets the route's success status. A route
        that does not exist answers 404 too.
        """
        print_section(f"UADM-009: {method} /users/{{gone}}{suffix}")
        admin = await _live_admin(lane)
        present = await _live_register(lane, "uadm_present")
        barrier = await _live(method, f"/users/{present.user_id}{suffix}", cookie=admin.cookie, json=body)
        assert barrier.status_code == success, f"Presence barrier: {method} /users/{{id}}{suffix} on an existing account must answer {success}, or the 404 below proves nothing: {barrier.status_code} {barrier.text}"
        gone = await _live_register(lane, "uadm_gone")
        async with AsyncSession(_lane_engine()) as session:
            assert await user_service.delete_user(session, gone.user_id) is not None, f"Setup: {gone.username} must be deleted"

        response = await _live(method, f"/users/{gone.user_id}{suffix}", cookie=admin.cookie, json=body)

        assert response.status_code == 404, f"{method} /users/{gone.user_id}{suffix} of a deleted account: expected 404, got {response.status_code} {response.text}"
        print_success("404")


# ============================================================================
# LANE: RESET LINKS, SESSIONS, ONBOARDING
# ============================================================================


class TestResetLinksOnTheLane:
    @pytest.mark.asyncio
    async def test_a_reset_link_works_once(self, lane: _LaneRows) -> None:
        """UADM-010: POST /users/{id}/password-reset-link → 201 {token, path, url, expires_at}, the stored hash of a reset link of that account; POST /auth/password-reset with it → 200, the new password signs in and the old one no longer does; the same link again → 400 TOKEN_INVALID, and the password stays."""
        print_section("UADM-010: a reset link, once")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_forgetful")

        created = await _live("POST", f"/users/{holder.user_id}/password-reset-link", cookie=admin.cookie)

        assert created.status_code == 201, f"POST /users/{{id}}/password-reset-link: expected 201, got {created.status_code} {created.text}"
        link = created.json()
        violations = _reset_link_violations(link)
        assert not violations, f"the 201 breaks its contract:{_verdict(violations)}"
        _expect(violations, link["url"] is None or link["url"].endswith(link["path"]), f"url must be null or end with the path: {link}")
        row = await _lane_token_of(link["token"])
        _expect(violations, row is not None and (row.purpose, row.user_id, row.consumed_at, row.revoked_at) == (PASSWORD_RESET.value, holder.user_id, None, None), f"the token must be the stored hash of a live reset link of {holder.username}: {row}")
        used = await _live_reset_password(link["token"], NEW_PASSWORD)
        _expect(violations, used.status_code == 200, f"POST /auth/password-reset: expected 200, got {used.status_code} {used.text}")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "the new password must sign in")
        _expect(violations, (await _live_login(holder)).status_code == 401, "the old password must no longer sign in")
        reused = await _live_reset_password(link["token"], THIRD_PASSWORD)
        _expect(violations, _refusal(reused) == (400, "TOKEN_INVALID"), f"a used link: expected 400 TOKEN_INVALID, got {reused.status_code} {reused.text}")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "a refused second use must leave the password as it was")
        assert not violations, f"A reset link must work once:{_verdict(violations)}"
        print_success("201, used once, refused the second time")

    @pytest.mark.asyncio
    async def test_a_new_link_revokes_the_accounts_earlier_links_and_only_those(self, lane: _LaneRows) -> None:
        """UADM-011: a link for a bystander, then two for the holder: the holder's first is revoked (400 TOKEN_INVALID, the password unchanged), the second works; the bystander's link was not revoked and works."""
        print_section("UADM-011: a new link revokes the account's earlier ones, only those")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_reset_holder")
        bystander = await _live_register(lane, "uadm_reset_bystander")
        theirs = await _admin_reset_link(admin, bystander.user_id)
        first = await _admin_reset_link(admin, holder.user_id)
        second = await _admin_reset_link(admin, holder.user_id)

        violations: list[str] = []
        first_row, their_row = await _lane_token_of(first), await _lane_token_of(theirs)
        _expect(violations, first_row is not None and first_row.revoked_at is not None, f"the holder's earlier link must be revoked by the new one: {first_row}")
        _expect(violations, their_row is not None and their_row.revoked_at is None, f"another account's link must not be revoked: {their_row}")
        used_first = await _live_reset_password(first, NEW_PASSWORD)
        _expect(violations, _refusal(used_first) == (400, "TOKEN_INVALID"), f"the revoked link: expected 400 TOKEN_INVALID, got {used_first.status_code} {used_first.text}")
        _expect(violations, (await _live_login(holder)).status_code == 200, "a refused link must leave the password as it was")
        _expect(violations, (await _live_reset_password(second, NEW_PASSWORD)).status_code == 200, "the newest link must work")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "the newest link must set the password")
        _expect(violations, (await _live_reset_password(theirs, NEW_PASSWORD)).status_code == 200, "the bystander's link must still work")
        _expect(violations, (await _live_login(bystander, NEW_PASSWORD)).status_code == 200, "the bystander's link must set the bystander's password")
        assert not violations, f"Only the newest link of an account may work, and only that account's are revoked:{_verdict(violations)}"
        print_success("earlier link revoked, newest works, the bystander's untouched")


class TestSessionsAndOnboardingOnTheLane:
    @pytest.mark.asyncio
    async def test_sessions_revoke_ends_every_session_of_the_account_and_no_other(self, lane: _LaneRows) -> None:
        """UADM-012: POST /users/{id}/sessions/revoke → 204 with no body; both devices of the account get 401 «Session expired or invalid», its version rose by one, it stays active and can sign in again; another account's session and version do not move."""
        print_section("UADM-012: sessions revoke")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_signed_out")
        bystander = await _live_member(lane, "uadm_signed_in")
        device_a, device_b = await _live_sign_in(holder), await _live_sign_in(holder)
        holder_before, bystander_before = await _lane_user(holder.user_id), await _lane_user(bystander.account.user_id)

        response = await _live("POST", f"/users/{holder.user_id}/sessions/revoke", cookie=admin.cookie)

        violations: list[str] = []
        _expect(violations, (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}")
        for label, cookie in (("device A", device_a), ("device B", device_b)):
            _expect(violations, await _live_me(cookie) == SESSION_EXPIRED, f"{label} of the account must be refused with {SESSION_EXPIRED}: {await _live_me(cookie)}")
        _expect(violations, await _lane_user(holder.user_id) == (holder_before[0], holder_before[1], holder_before[2] + 1), f"the account's version must rise by one, nothing else: {holder_before} → {await _lane_user(holder.user_id)}")
        _expect(violations, await _live_me_id(bystander.cookie) == bystander.account.user_id, "another account's session must not notice")
        _expect(violations, await _lane_user(bystander.account.user_id) == bystander_before, "another account's version must not move")
        _expect(violations, await _live_me_id(await _live_sign_in(holder)) == holder.user_id, "the account must be able to sign in again")
        assert not violations, f"POST /users/{{id}}/sessions/revoke broke its contract:{_verdict(violations)}"
        print_success("204: both devices out, the bystander in, a new login works")

    @pytest.mark.asyncio
    async def test_onboarding_reset_puts_every_flow_and_step_back_to_pending(self, lane: _LaneRows) -> None:
        """UADM-013: an account completed intro_tour and import_guide (with its steps), skipped fx_guide and one step of transaction_bulk_guide; POST /users/{id}/onboarding/reset {} → 204, and the account, signing in again, reads every flow and every step pending."""
        print_section("UADM-013: onboarding reset, every flow")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_onboarded")
        bulk_step = STEP_FLOWS[OnboardingFlow.TRANSACTION_BULK_GUIDE.value][0]
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.FX_GUIDE, "skip")
        await _live_onboarding_move(member.cookie, OnboardingFlow.IMPORT_GUIDE, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.TRANSACTION_BULK_GUIDE, "skip", step=bulk_step)
        before = await _live_onboarding(member.cookie)
        assert before[OnboardingFlow.INTRO_TOUR.value][0] == "completed" and before[OnboardingFlow.FX_GUIDE.value][0] == "skipped", f"Precondition: {before}"
        assert before[OnboardingFlow.IMPORT_GUIDE.value][1] and set(before[OnboardingFlow.IMPORT_GUIDE.value][1].values()) == {"completed"}, f"Precondition: {before}"
        assert before[OnboardingFlow.TRANSACTION_BULK_GUIDE.value][1][bulk_step] == "skipped", f"Precondition: {before}"

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={})

        assert (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}"
        after = await _live_onboarding(await _live_sign_in(member.account))
        expected = {flow.value: _pending(flow.value) for flow in ONBOARDING_FLOW_VERSIONS}
        assert after == expected, f"every flow and step must be back to pending: {after}"
        print_success("every flow and every step pending")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("flow", [OnboardingFlow.INTRO_TOUR.value, OnboardingFlow.IMPORT_GUIDE.value])
    async def test_onboarding_reset_of_one_flow_leaves_the_others_as_they_were(self, lane: _LaneRows, flow: str) -> None:
        """UADM-014: intro_tour and import_guide completed, fx_guide skipped; {flow} → 204, that flow (with its steps, when it has any) back to pending, every other flow as it was."""
        print_section(f"UADM-014: onboarding reset of {flow}")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_one_flow")
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.IMPORT_GUIDE, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.FX_GUIDE, "skip")
        before = await _live_onboarding(member.cookie)
        assert before[flow][0] == "completed", f"Precondition: {flow} completed: {before}"

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={"flow": flow})

        assert (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}"
        after = await _live_onboarding(await _live_sign_in(member.account))
        assert after == {**before, flow: _pending(flow)}, f"only {flow} must be back to pending: before {before}, after {after}"
        print_success(f"{flow} pending, the others untouched")

    @pytest.mark.asyncio
    async def test_onboarding_reset_of_an_unknown_flow_is_refused_and_resets_nothing(self, lane: _LaneRows) -> None:
        """UADM-015: {flow: "no_such_flow"} → 422, and the account's onboarding is as it was."""
        print_section("UADM-015: onboarding reset of an unknown flow")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_unknown_flow")
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        before = await _live_onboarding(member.cookie)

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={"flow": "no_such_flow"})

        assert response.status_code == 422, f"an unknown flow: expected 422, got {response.status_code} {response.text}"
        assert await _live_onboarding(await _live_sign_in(member.account)) == before, "a refused reset must reset nothing"
        print_success("422, nothing reset")


# ============================================================================
# LANE: DELETING AN ACCOUNT, AND WHAT IT WOULD TAKE (lot A6a)
# ============================================================================


def _deposit(broker_id: int) -> Transaction:
    return Transaction(broker_id=broker_id, type=TransactionType.DEPOSIT, date=TRANSACTION_DATE, amount=Decimal("100"), currency="EUR")


def _cash_leg(broker_id: int, amount: str) -> Transaction:
    return Transaction(broker_id=broker_id, type=TransactionType.CASH_TRANSFER, date=TRANSACTION_DATE, amount=Decimal(amount), currency="EUR")


def _grant(user_id: int, broker_id: int, role: UserRole) -> BrokerUserAccess:
    return BrokerUserAccess(user_id=user_id, broker_id=broker_id, role=role, share_percentage=Decimal("0"))


@dataclass(frozen=True)
class _DeletionScene:
    """An administrator, the target (signed in), its partner, and four brokers this case wrote in the lane's database.

    - ``sole``: the target its only OWNER; two DEPOSITs and the outgoing leg of a cash transfer to ``co_owned`` → deleted;
    - ``last_owner``: the target OWNER, the partner EDITOR, so the target is its last owner; a DEPOSIT → deleted;
    - ``co_owned``: the target and the partner both OWNER; the incoming leg → left, the target an OWNER there;
    - ``viewed``: the partner OWNER, the target VIEWER → left, the target a VIEWER there.

    The incoming leg is the one transfer half the deletion leaves alone.
    """

    admin: _Signed
    target: _Signed
    partner: _Account
    brokers: dict[str, int]
    names: dict[int, str]
    transactions: dict[int, int]

    @property
    def deleted(self) -> list[int]:
        return sorted(self.brokers[key] for key in ("sole", "last_owner"))

    @property
    def left(self) -> dict[int, str]:
        """The brokers left, with the target's role there as the API spells it."""
        return {self.brokers["co_owned"]: UserRole.OWNER.value, self.brokers["viewed"]: UserRole.VIEWER.value}

    def preview(self) -> dict[str, Any]:
        """What GET /users/{target}/deletion-preview must answer, exactly: both lists by broker id."""
        return {
            "user_id": self.target.account.user_id,
            "username": self.target.account.username,
            "brokers_deleted": [{"id": broker_id, "name": self.names[broker_id], "transactions": self.transactions[broker_id]} for broker_id in self.deleted],
            "brokers_left": [{"id": broker_id, "name": self.names[broker_id], "role": role} for broker_id, role in sorted(self.left.items())],
            "transfers_unpaired": 1,
        }


@dataclass(frozen=True)
class _LaneHoldings:
    """What the lane holds of the target and of this case's four brokers, read fresh: every read scoped to them."""

    target: bool
    brokers: frozenset[int]
    grants: frozenset[tuple[int, int, str]]
    transactions: frozenset[tuple[int, int, Optional[int]]]


async def _deletion_scene(lane: _LaneRows) -> _DeletionScene:
    """Register the administrator, the target and the partner; write the four brokers with their grants and transactions; record the brokers once committed."""
    admin = await _live_admin(lane)
    target = await _live_member(lane, "uadm_leaver")
    partner = await _live_register(lane, "uadm_partner")
    t, p = target.account.user_id, partner.user_id
    marker = uuid.uuid4().hex[:12]
    async with AsyncSession(_lane_engine(), expire_on_commit=False) as session:
        rows = {key: Broker(name=f"UADM {key} {marker}") for key in ("sole", "last_owner", "co_owned", "viewed")}
        session.add_all(rows.values())
        await session.flush()
        b = {key: broker.id for key, broker in rows.items()}
        grants = ((t, "sole", UserRole.OWNER), (t, "last_owner", UserRole.OWNER), (p, "last_owner", UserRole.EDITOR), (t, "co_owned", UserRole.OWNER), (p, "co_owned", UserRole.OWNER), (p, "viewed", UserRole.OWNER), (t, "viewed", UserRole.VIEWER))
        session.add_all([_grant(user_id, b[key], role) for user_id, key, role in grants])
        outgoing, incoming = _cash_leg(b["sole"], "-25"), _cash_leg(b["co_owned"], "25")
        session.add_all([_deposit(b["sole"]), _deposit(b["sole"]), _deposit(b["last_owner"]), outgoing, incoming])
        await session.flush()
        outgoing.related_transaction_id, incoming.related_transaction_id = incoming.id, outgoing.id
        await session.commit()
    # Recorded only now: an id flushed then rolled back could be handed to a neighbour, and the teardown deletes by id.
    lane.broker_ids.extend(b.values())
    counts = {b["sole"]: 3, b["last_owner"]: 1, b["co_owned"]: 1, b["viewed"]: 0}
    return _DeletionScene(admin=admin, target=target, partner=partner, brokers=b, names={broker.id: broker.name for broker in rows.values()}, transactions=counts)


async def _lane_holdings(scene: _DeletionScene) -> _LaneHoldings:
    broker_ids = list(scene.brokers.values())
    async with AsyncSession(_lane_engine()) as session:
        target = await session.scalar(select(User.id).where(User.id == scene.target.account.user_id))
        brokers = (await session.execute(select(Broker.id).where(Broker.id.in_(broker_ids)))).scalars().all()
        grants = (await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role).where(BrokerUserAccess.broker_id.in_(broker_ids)))).all()
        transactions = (await session.execute(select(Transaction.id, Transaction.broker_id, Transaction.related_transaction_id).where(Transaction.broker_id.in_(broker_ids)))).all()
    return _LaneHoldings(
        target=target is not None,
        brokers=frozenset(brokers),
        grants=frozenset((broker_id, user_id, UserRole(role).value) for broker_id, user_id, role in grants),
        transactions=frozenset((tx_id, broker_id, related) for tx_id, broker_id, related in transactions),
    )


def _after_deleting(before: _LaneHoldings, scene: _DeletionScene) -> _LaneHoldings:
    """What deleting the target must leave: the deleted brokers gone with their grants and transactions, the target and its grants gone, the half left alone unlinked; nothing else."""
    deleted, target_id = set(scene.deleted), scene.target.account.user_id
    gone = {tx_id for tx_id, broker_id, _ in before.transactions if broker_id in deleted}
    return _LaneHoldings(
        target=False,
        brokers=before.brokers - deleted,
        grants=frozenset(grant for grant in before.grants if grant[0] not in deleted and grant[1] != target_id),
        transactions=frozenset((tx_id, broker_id, None if related in gone else related) for tx_id, broker_id, related in before.transactions if broker_id not in deleted),
    )


async def _lane_account(user_id: int) -> Optional[tuple[bool, bool, int]]:
    """(is_active, is_superuser, session_version) of one of this case's accounts, read fresh; None once it is gone."""
    async with AsyncSession(_lane_engine()) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == user_id))).one_or_none()
    return None if row is None else (bool(row[0]), bool(row[1]), int(row[2]))


class TestAccountDeletionOnTheLane:
    """GET /users/{id}/deletion-preview and DELETE /users/{id} on this case's own accounts and brokers. The caller is an active administrator, never the target unless the case says so."""

    @pytest.mark.asyncio
    async def test_the_preview_says_what_would_go_and_what_would_stay_and_writes_nothing(self, lane: _LaneRows) -> None:
        """UADM-040: GET /users/{target}/deletion-preview → 200, exactly {user_id, username, brokers_deleted: [sole (3 transactions), last_owner (1)], brokers_left: [co_owned OWNER, viewed VIEWER], transfers_unpaired: 1}, both lists by id; the target, the four brokers, their grants and transactions are as before, and the target's session still works."""
        print_section("UADM-040: the preview of a deletion")
        scene = await _deletion_scene(lane)
        target_id = scene.target.account.user_id
        before = await _lane_holdings(scene)

        response = await _live("GET", f"/users/{target_id}/deletion-preview", cookie=scene.admin.cookie)

        after = await _lane_holdings(scene)
        violations: list[str] = []
        _expect(violations, _answer(response) == (200, scene.preview()), f"expected 200 with exactly {scene.preview()}, got {_answer(response)}")
        _expect(violations, after == before, f"the preview must write nothing: before {before}, after {after}")
        _expect(violations, await _live_me_id(scene.target.cookie) == target_id, "the preview must end no session of the target")
        assert not violations, f"GET /users/{{id}}/deletion-preview broke its contract:{_verdict(violations)}"
        print_success("two brokers would go, two would stay, one transfer half left alone; nothing written")

    @pytest.mark.asyncio
    async def test_the_deletion_takes_what_the_preview_said_and_ends_the_sessions(self, lane: _LaneRows) -> None:
        """UADM-041: after a preview (200, the presence barrier of the 404s below), DELETE /users/{target} → 204 with no body; the target and its grants are gone, sole and last_owner are gone with their transactions and grants, co_owned and viewed stay with the partner's grants, the incoming leg stays unlinked — exactly what the preview said, nothing else; the target's session answers 401; the preview and a second DELETE of it → 404; the administrator's session does not notice."""
        print_section("UADM-041: DELETE /users/{id}")
        scene = await _deletion_scene(lane)
        target_id, cookie = scene.target.account.user_id, scene.admin.cookie
        preview = await _live("GET", f"/users/{target_id}/deletion-preview", cookie=cookie)
        assert preview.status_code == 200, f"Presence barrier: the preview of an existing account must answer 200, or the 404 below proves nothing: {preview.status_code} {preview.text}"
        assert await _live_me_id(scene.target.cookie) == target_id, "Presence barrier: the target's session must work before the deletion"
        before = await _lane_holdings(scene)

        response = await _live("DELETE", f"/users/{target_id}", cookie=cookie)

        after = await _lane_holdings(scene)
        previewed = preview.json()
        previewed_deleted = {item.get("id") for item in previewed.get("brokers_deleted", [])}
        previewed_left = {item.get("id") for item in previewed.get("brokers_left", [])}
        violations: list[str] = []
        _expect(violations, (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}")
        _expect(violations, previewed == scene.preview(), f"the preview: expected {scene.preview()}, got {previewed}")
        _expect(violations, not after.brokers & previewed_deleted and previewed_left <= after.brokers, f"the brokers must follow the preview: deleted {sorted(previewed_deleted)}, left {sorted(previewed_left)}, still there {sorted(after.brokers)}")
        _expect(violations, after == _after_deleting(before, scene), f"the deletion must take the target, its grants and the brokers it was the last owner of, unlinking the half left alone, and nothing else: expected {_after_deleting(before, scene)}, found {after}")
        _expect(violations, (await _live_me(scene.target.cookie))[0] == 401, f"the deleted account's session must answer 401: {await _live_me(scene.target.cookie)}")
        _expect(violations, (await _live("GET", f"/users/{target_id}/deletion-preview", cookie=cookie)).status_code == 404, "the preview of a deleted account must answer 404")
        _expect(violations, (await _live("DELETE", f"/users/{target_id}", cookie=cookie)).status_code == 404, "deleting a deleted account must answer 404")
        _expect(violations, await _live_me_id(scene.admin.cookie) == scene.admin.account.user_id, "the administrator's session must not notice")
        assert not violations, f"DELETE /users/{{id}} broke its contract:{_verdict(violations)}"
        print_success("204: the account and the two brokers it was the last owner of gone, the other two left, the session 401, then 404")

    @pytest.mark.asyncio
    async def test_an_administrator_deletes_neither_itself_nor_another_administrator(self, lane: _LaneRows) -> None:
        """UADM-042: DELETE of the caller's own id → 409 SELF_DELETION (one's own account is deleted from the profile); of an active administrator, and of an inactive one → 409 DEMOTE_FIRST; each of the three is as it was, version included, and the caller is still signed in as an administrator.

        Presence barrier first: an ordinary account of this case is deleted with 204, so the route exists and refuses
        only these. Deterministic on the lane: the caller is an active administrator, and the others are this case's.
        """
        print_section("UADM-042: SELF_DELETION and DEMOTE_FIRST")
        admin = await _live_admin(lane)
        ordinary = await _live_register(lane, "uadm_deletable")
        active_admin = await _live_register(lane, "uadm_other_admin")
        dormant_admin = await _live_register(lane, "uadm_dormant_admin")
        await _lane_set(active_admin.username, admin=True)
        await _lane_set(dormant_admin.username, admin=True)
        await _lane_set(dormant_admin.username, active=False)
        barrier = await _live("DELETE", f"/users/{ordinary.user_id}", cookie=admin.cookie)
        assert barrier.status_code == 204, f"Presence barrier: DELETE of an ordinary account of this case must answer 204, or the 409s below prove nothing: {barrier.status_code} {barrier.text}"
        accounts = {"the caller": admin.account.user_id, "an active administrator": active_admin.user_id, "an inactive administrator": dormant_admin.user_id}
        before = {label: await _lane_account(user_id) for label, user_id in accounts.items()}

        answers = {label: _refusal(await _live("DELETE", f"/users/{user_id}", cookie=admin.cookie)) for label, user_id in accounts.items()}

        after = {label: await _lane_account(user_id) for label, user_id in accounts.items()}
        expected = {"the caller": (409, "SELF_DELETION"), "an active administrator": (409, "DEMOTE_FIRST"), "an inactive administrator": (409, "DEMOTE_FIRST")}
        violations: list[str] = []
        _expect(violations, answers == expected, f"expected {expected}, got {answers}")
        _expect(violations, after == before, f"a refused deletion must change nothing, the version included: before {before}, after {after}")
        _expect(violations, (await _live("GET", "/users", cookie=admin.cookie)).status_code == 200, "the caller must still be signed in as an administrator")
        assert not violations, f"An administrator must delete neither itself nor another administrator:{_verdict(violations)}"
        print_success("409 SELF_DELETION, 409 DEMOTE_FIRST twice, nothing changed")

    @pytest.mark.asyncio
    async def test_every_account_of_the_lane_is_listed_unprotected_today(self, lane: _LaneRows) -> None:
        """UADM-043: GET /users → every account carries ``protected: false``: today the hook of lot A7 protects nobody, whatever the neighbours registered. Presence barrier: this case's two accounts are listed."""
        print_section("UADM-043: nobody is protected today")
        admin = await _live_admin(lane)
        member = await _live_register(lane, "uadm_unprotected")

        response = await _live("GET", "/users", cookie=admin.cookie)

        assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
        items = response.json()["items"]
        assert {admin.account.user_id, member.user_id} <= {item.get("id") for item in items}, "Presence barrier: this case's two accounts must be listed"
        flagged = [(item.get("username"), item.get("protected", "<missing>")) for item in items if item.get("protected") is not False]
        assert flagged == [], f"every account must be listed with protected false today: {flagged}"
        print_success(f"{len(items)} accounts, none protected")


# ============================================================================
# THE PRIVATE INSTANCE: THE REAL ROUTERS ON A DATABASE OF THIS TEST
# ============================================================================


@dataclass(frozen=True)
class _Private:
    """An instance of one test: the routers of auth, users and settings, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _private_app(engine: AsyncEngine) -> FastAPI:
    """The real routers, mounted under the API prefix as ``api/v1/router.py`` mounts them; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    for router in (auth_api.router, users_api.router, settings_api.router):
        app.include_router(router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@pytest_asyncio.fixture
async def private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with; no accounts variable; bcrypt at cost 4. Disposed at teardown."""
    for name in ACCOUNTS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'instance.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_private_app(engine))
    finally:
        await engine.dispose()


async def _call(private: _Private, method: str, path: str, *, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request to the private instance, from a client of its own: no cookie jar, the session (if any) sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=private.app), base_url="http://test", timeout=TIMEOUT) as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", json=json, headers=headers)


async def _add_user(private: _Private, username: str, *, admin: bool = False, active: bool = True) -> _Account:
    """An account written as a row, with a real bcrypt hash of PRIVATE_PASSWORD (cost 4), so that it can sign in."""
    email = f"{username}@example.com"
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(PRIVATE_PASSWORD), is_active=active, is_superuser=admin)
        session.add(user)
        await session.commit()
    return _Account(user_id=user.id, username=username, email=email, password=PRIVATE_PASSWORD)


async def _sign_in(private: _Private, account: _Account) -> str:
    """A session of ``account`` on the private instance, through its POST /auth/login."""
    response = await _call(private, "POST", "/auth/login", json={"username": account.username, "password": account.password})
    cookie = _session_cookie(response)
    assert response.status_code == 200 and cookie, f"Setup: {account.username} could not sign in to the private instance: {response.status_code} {response.text}"
    return cookie


async def _admin(private: _Private, username: str = "root") -> tuple[_Account, str]:
    """An active administrator of the private instance, signed in."""
    account = await _add_user(private, username, admin=True)
    return account, await _sign_in(private, account)


async def _private_user(private: _Private, user_id: int) -> tuple[bool, bool, int]:
    """(is_active, is_superuser, session_version) of an account, read fresh."""
    async with AsyncSession(private.engine) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == user_id))).one()
    return bool(row[0]), bool(row[1]), int(row[2])


async def _private_issue(private: _Private, purpose: AccountTokenPurpose = INVITE, **arguments: Any) -> IssuedToken:
    """A token issued by token_service directly, committed."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _private_consume(private: _Private, token: str, consumed_by_user_id: int) -> None:
    async with AsyncSession(private.engine) as session:
        record = await consume_token(session, token, INVITE, consumed_by_user_id=consumed_by_user_id)
        await session.commit()
    assert record is not None, "Setup: the invitation must be consumed"


async def _private_tokens(private: _Private) -> list[AccountToken]:
    """Every token row of the private instance: this test owns them all."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        return list((await session.execute(select(AccountToken).order_by(AccountToken.id))).scalars().all())


async def _private_token_columns(private: _Private) -> list[dict[str, Any]]:
    """Every token row of the private instance as its raw column values, read from the table without the model: what the database holds."""
    async with AsyncSession(private.engine) as session:
        return [dict(row) for row in (await session.execute(select(AccountToken.__table__))).mappings().all()]


async def _invitation_count(private: _Private) -> int:
    return sum(1 for row in await _private_tokens(private) if row.purpose == INVITE.value)


async def _set_mode_row(private: _Private, mode: str) -> None:
    """The ``registration_mode`` row says ``mode``: the seeded row updated, or created when missing."""
    async with AsyncSession(private.engine) as session:
        row = await session.get(GlobalSetting, MODE_KEY)
        if row is None:
            row = GlobalSetting(key=MODE_KEY, value=mode, value_type="string", updated_at=utcnow())
        row.value = mode
        session.add(row)
        await session.commit()


# ============================================================================
# IN-PROCESS: THE LAST ACTIVE ADMINISTRATOR
# ============================================================================


class TestLastActiveAdministrator:
    """«The last active administrator» depends on every account of the instance: a real state only on a private one."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("change", [pytest.param({"is_active": False}, id="deactivate"), pytest.param({"is_superuser": False}, id="demote")])
    async def test_the_last_active_administrator_is_neither_deactivated_nor_demoted(self, private: _Private, change: dict[str, bool]) -> None:
        """UADM-020: root is the only active administrator (another administrator exists, inactive: it does not count); PATCH /users/{root} with the change → 409 LAST_ADMIN; root is as it was, version included, and its session still works."""
        print_section(f"UADM-020: {change} on the last active administrator")
        root, cookie = await _admin(private)
        dormant = await _add_user(private, "dormant", admin=True, active=False)
        await _add_user(private, "member")
        before = await _private_user(private, root.user_id)

        response = await _call(private, "PATCH", f"/users/{root.user_id}", cookie=cookie, json=change)

        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "LAST_ADMIN"), f"expected 409 LAST_ADMIN, got {response.status_code} {response.text}")
        _expect(violations, await _private_user(private, root.user_id) == before, f"a refused change must change nothing, the version included: {before} → {await _private_user(private, root.user_id)}")
        _expect(violations, (await _call(private, "GET", "/users", cookie=cookie)).status_code == 200, "a refused change must end no session: root must still be signed in as an administrator")
        _expect(violations, await _private_user(private, dormant.user_id) == (False, True, 0), "the inactive administrator must be untouched")
        assert not violations, f"The last active administrator must stay:{_verdict(violations)}"
        print_success("409 LAST_ADMIN, nothing changed")

    @pytest.mark.asyncio
    async def test_the_guard_follows_the_active_administrators(self, private: _Private) -> None:
        """UADM-021: root is the only active administrator. Demoting the inactive administrator → 200 (it removes no active one); promoting the member → 200; deactivating root → 200, the member remains; the member, now the last active administrator, demoting itself → 409 LAST_ADMIN."""
        print_section("UADM-021: the guard counts the active administrators")
        root, cookie = await _admin(private)
        dormant = await _add_user(private, "dormant", admin=True, active=False)
        member = await _add_user(private, "member")

        steps = {
            "demote the inactive administrator": (await _call(private, "PATCH", f"/users/{dormant.user_id}", cookie=cookie, json={"is_superuser": False})).status_code,
            "promote the member": (await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})).status_code,
            "deactivate root while the member is an active administrator": (await _call(private, "PATCH", f"/users/{root.user_id}", cookie=cookie, json={"is_active": False})).status_code,
        }
        last = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=await _sign_in(private, member), json={"is_superuser": False})

        flags = {name: (await _private_user(private, account.user_id))[:2] for name, account in (("root", root), ("dormant", dormant), ("member", member))}
        violations: list[str] = []
        _expect(violations, steps == dict.fromkeys(steps, 200), f"each step must be allowed: {steps}")
        _expect(violations, _refusal(last) == (409, "LAST_ADMIN"), f"the member is now the last active administrator: expected 409 LAST_ADMIN, got {last.status_code} {last.text}")
        _expect(violations, flags == {"root": (False, True), "dormant": (False, False), "member": (True, True)}, f"(is_active, is_superuser) afterwards: {flags}")
        assert not violations, f"The guard must count the active administrators, and only them:{_verdict(violations)}"
        print_success("allowed while another active administrator remains, refused for the last one")


# ============================================================================
# IN-PROCESS: THE USER LIMIT AND THE REGISTRATION MODE
# ============================================================================


REACTIVATION_CASES = [
    pytest.param("2", 0, True, id="at-the-limit"),
    pytest.param("3", 1, True, id="an-invitation-holds-the-last-seat"),
    pytest.param("3", 0, False, id="a-seat-left"),
]

INVITATION_LIMIT_CASES = [
    pytest.param("2", 0, BILLING_LINK, (409, 2, 2), id="at-the-limit"),
    pytest.param("1", 0, BILLING_LINK, (409, 1, 2), id="over-the-limit"),
    pytest.param("3", 1, None, (409, 3, 3), id="invitations-hold-the-seats"),
    pytest.param("not-a-number", 0, None, (409, 0, 2), id="an-invalid-limit-closes"),
    pytest.param("3", 0, BILLING_LINK, (201, None, None), id="a-seat-left"),
]

MODE_CASES = [
    pytest.param("open", "row", 201, id="open-by-the-row"),
    pytest.param("invite", "row", 201, id="invite-by-the-row"),
    pytest.param("disabled", "row", 409, id="disabled-by-the-row"),
    pytest.param("open", "variable", 201, id="open-by-the-variable"),
    pytest.param("invite", "variable", 201, id="invite-by-the-variable"),
    pytest.param("disabled", "variable", 409, id="disabled-by-the-variable"),
]


class TestUserLimitAndRegistrationMode:
    """LIBREFOLIO_MAX_USERS, LIBREFOLIO_BILLING_URL, LIBREFOLIO_REGISTRATION and the registration_mode row, on a private instance. Every instance has root (an active administrator) and a member (active): two seats used; an inactive account takes none."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("max_users", "live_invitations", "refused"), REACTIVATION_CASES)
    async def test_a_reactivation_over_the_limit_is_refused_with_the_counts(self, private: _Private, monkeypatch: pytest.MonkeyPatch, max_users: str, live_invitations: int, refused: bool) -> None:
        """UADM-022: PATCH {is_active: true} of an inactive account with no seat left (the live invitations hold seats) → 409 USER_LIMIT_REACHED with limit, used and billing_url, and the account stays inactive; with a seat left → 200, active."""
        print_section(f"UADM-022: reactivation, LIBREFOLIO_MAX_USERS={max_users}, {live_invitations} live invitation(s)")
        root, cookie = await _admin(private)
        await _add_user(private, "member")
        dormant = await _add_user(private, "dormant", active=False)
        for _ in range(live_invitations):
            await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, max_users)
        monkeypatch.setenv(BILLING_URL_VARIABLE, BILLING_LINK)

        response = await _call(private, "PATCH", f"/users/{dormant.user_id}", cookie=cookie, json={"is_active": True})

        is_active = (await _private_user(private, dormant.user_id))[0]
        if refused:
            expected = {"error_code": "USER_LIMIT_REACHED", "limit": int(max_users), "used": 2 + live_invitations, "billing_url": BILLING_LINK}
            assert (response.status_code, _counts(response)) == (409, expected), f"expected 409 with {expected}, got {response.status_code} {response.text}"
            assert is_active is False, "a refused reactivation must leave the account inactive"
        else:
            assert (response.status_code, is_active) == (200, True), f"with a seat left the reactivation goes through: {response.status_code} {response.text}, is_active={is_active}"
        print_success(f"{response.status_code}")

    @pytest.mark.asyncio
    async def test_the_limit_blocks_neither_a_promotion_nor_a_deactivation(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-023: two seats used, LIBREFOLIO_MAX_USERS=1 (over the limit): promoting the member → 200, then deactivating it → 200."""
        print_section("UADM-023: over the limit, promotion and deactivation still go through")
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        monkeypatch.setenv(MAX_USERS_VARIABLE, "1")

        promote = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})
        deactivate = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_active": False})

        assert (promote.status_code, deactivate.status_code) == (200, 200), f"the limit blocks invitations, open registration and reactivations only: promote {promote.status_code} {promote.text}, deactivate {deactivate.status_code} {deactivate.text}"
        assert (await _private_user(private, member.user_id))[:2] == (False, True), "the member must end up an inactive administrator"
        print_success("200, 200")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("max_users", "live_invitations", "billing", "outcome"), INVITATION_LIMIT_CASES)
    async def test_an_invitation_at_the_limit_is_refused_with_the_counts_and_the_billing_link(self, private: _Private, monkeypatch: pytest.MonkeyPatch, max_users: str, live_invitations: int, billing: Optional[str], outcome: tuple[int, Optional[int], Optional[int]]) -> None:
        """UADM-024: POST /users/invites with no seat left (an invalid LIBREFOLIO_MAX_USERS closes: limit 0) → 409 USER_LIMIT_REACHED with limit, used and billing_url (null without LIBREFOLIO_BILLING_URL), and no invitation issued; with a seat left → 201."""
        print_section(f"UADM-024: an invitation, LIBREFOLIO_MAX_USERS={max_users}, {live_invitations} live invitation(s)")
        root, cookie = await _admin(private)
        await _add_user(private, "member")
        await _add_user(private, "dormant", active=False)
        for _ in range(live_invitations):
            await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, max_users)
        if billing:
            monkeypatch.setenv(BILLING_URL_VARIABLE, billing)
        before = await _invitation_count(private)

        response = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": False})

        status, limit, used = outcome
        issued = await _invitation_count(private) - before
        if status == 201:
            assert (response.status_code, issued) == (201, 1), f"with a seat left the invitation is issued: {response.status_code} {response.text}, {issued} issued"
            return
        expected = {"error_code": "USER_LIMIT_REACHED", "limit": limit, "used": used, "billing_url": billing}
        assert (response.status_code, _counts(response)) == (409, expected), f"expected 409 with {expected}, got {response.status_code} {response.text}"
        assert issued == 0, f"a refused invitation must issue nothing: {issued} issued"
        print_success(f"409 with {expected}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("mode", "source", "status"), MODE_CASES)
    async def test_an_invitation_is_refused_while_registration_is_disabled(self, private: _Private, monkeypatch: pytest.MonkeyPatch, mode: str, source: str, status: int) -> None:
        """UADM-025: registration disabled — by the row, or by LIBREFOLIO_REGISTRATION over a row that says open — → POST /users/invites 409 REGISTRATION_DISABLED and nothing issued; open or invite (the variable over a disabled row too) → 201."""
        print_section(f"UADM-025: an invitation while registration is {mode}, by the {source}")
        _, cookie = await _admin(private)
        if source == "row":
            await _set_mode_row(private, mode)
        else:
            await _set_mode_row(private, "open" if mode == "disabled" else "disabled")
            monkeypatch.setenv(REGISTRATION_VARIABLE, mode)
        before = await _invitation_count(private)

        response = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": True})

        expected = (201, None) if status == 201 else (409, "REGISTRATION_DISABLED")
        assert _refusal(response) == expected, f"registration {mode} by the {source}: expected {expected}, got {response.status_code} {response.text}"
        assert await _invitation_count(private) - before == (1 if status == 201 else 0), "a refused invitation must issue nothing, an accepted one exactly one"
        print_success(f"{expected}")


# ============================================================================
# IN-PROCESS: LINKS, LIFETIMES, WHAT IS LISTED AND COUNTED
# ============================================================================


class TestLinksAndInvitationsInProcess:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("public_url", [pytest.param(None, id="without-a-public-url"), pytest.param(PUBLIC_URL, id="with-a-public-url")])
    async def test_links_carry_the_public_url_when_it_is_set(self, private: _Private, monkeypatch: pytest.MonkeyPatch, public_url: Optional[str]) -> None:
        """UADM-026: the 201 of an invitation and of a reset link: ``path`` is the page with the token, ``url`` is LIBREFOLIO_PUBLIC_URL without its trailing slash plus the path, or null without the variable."""
        print_section(f"UADM-026: links, LIBREFOLIO_PUBLIC_URL={public_url}")
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        if public_url:
            monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)

        invitation = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        link = await _call(private, "POST", f"/users/{member.user_id}/password-reset-link", cookie=cookie)

        assert (invitation.status_code, link.status_code) == (201, 201), f"invitation {invitation.status_code} {invitation.text}; reset link {link.status_code} {link.text}"
        origin = PUBLIC_ORIGIN if public_url else None
        violations: list[str] = []
        for label, body, purpose in (("invitation", invitation.json(), INVITE), ("reset link", link.json(), PASSWORD_RESET)):
            violations += [f"{label}: {problem}" for problem in _link_path_violations(body.get("path"), purpose, str(body.get("token")))]
            violations += [f"{label}: {problem}" for problem in _url_violations(body, origin)]
        assert not violations, f"The links must follow LIBREFOLIO_PUBLIC_URL:{_verdict(violations)}"
        print_success(f"url {'built on the public URL' if public_url else 'null'}")

    @pytest.mark.asyncio
    async def test_an_invitation_lives_seven_days_a_reset_link_thirty_minutes_and_only_hashes_are_stored(self, private: _Private) -> None:
        """UADM-027: the invitation is created now and lives 7 days, as asked (admin role, e-mail, its issuer); the reset link expires 30 minutes after it was asked for; each row holds the token's SHA-256, of its purpose and owner, and no column of any token row holds a plaintext."""
        print_section("UADM-027: lifetimes and hashes")
        root, cookie = await _admin(private)
        member = await _add_user(private, "member")

        started = utcnow()
        invitation = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": True, "email": "guest@example.com"})
        link = await _call(private, "POST", f"/users/{member.user_id}/password-reset-link", cookie=cookie)
        finished = utcnow()

        assert (invitation.status_code, link.status_code) == (201, 201), f"invitation {invitation.status_code} {invitation.text}; reset link {link.status_code} {link.text}"
        issued, reset = invitation.json(), link.json()
        violations = _issued_invite_violations(issued, grants_admin=True, email="guest@example.com", created_by=root.user_id) + _reset_link_violations(reset)
        assert not violations, f"the 201 bodies break their contract:{_verdict(violations)}"
        created, expires = _instant(issued["invite"]["created_at"]), _instant(reset["expires_at"])
        ttl = DEFAULT_TTL[PASSWORD_RESET]
        _expect(violations, created is not None and started <= created <= finished, f"the invitation must be created now, between {started} and {finished}: {created}")
        _expect(violations, expires is not None and started + ttl <= expires <= finished + ttl, f"the reset link must expire {ttl} after it was asked for, between {started + ttl} and {finished + ttl}: {expires}")
        rows = {row.token_hash: row for row in await _private_tokens(private)}
        invite_row, reset_row = rows.get(hash_token(issued["token"])), rows.get(hash_token(reset["token"]))
        _expect(violations, invite_row is not None and (invite_row.id, invite_row.purpose, invite_row.user_id) == (issued["invite"]["id"], INVITE.value, None), f"the invitation's row must hold its hash: {invite_row}")
        _expect(violations, reset_row is not None and (reset_row.purpose, reset_row.user_id) == (PASSWORD_RESET.value, member.user_id), f"the reset link's row must hold its hash, for the member: {reset_row}")
        stored = [f"{row['id']}.{column}" for row in await _private_token_columns(private) for column, value in row.items() if any(secret in str(value) for secret in (issued["token"], reset["token"]))]
        _expect(violations, stored == [], f"a plaintext token is stored in {stored}")
        assert not violations, f"Lifetimes and storage broke their contract:{_verdict(violations)}"
        print_success("7 days, 30 minutes, hashes only")

    @pytest.mark.asyncio
    async def test_only_live_invitations_are_listed_and_counted_and_every_account_is_listed(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-028: two administrators, a member, an inactive account; invitations live (one from the API, one by the other administrator), revoked, consumed and expired, and a reset link. GET /users/invites lists exactly the two live ones; GET /users exactly the four accounts with their flags; both say usage {used: 3 active + 2 live = 5, max_users: 10, billing_url}; without the variables {used: 5, max_users: null, billing_url: null}."""
        print_section("UADM-028: what is listed and what is counted")
        root, cookie = await _admin(private)
        other = await _add_user(private, "other_admin", admin=True)
        member = await _add_user(private, "member")
        dormant = await _add_user(private, "dormant", active=False)
        live = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        revoked = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        assert (live.status_code, revoked.status_code) == (201, 201), f"Setup: {live.status_code} {live.text}; {revoked.status_code} {revoked.text}"
        assert (await _call(private, "DELETE", f"/users/invites/{revoked.json()['invite']['id']}", cookie=cookie)).status_code == 204, "Setup: revoke"
        live_by_other = await _private_issue(private, INVITE, created_by_user_id=other.user_id)
        consumed = await _private_issue(private, INVITE, created_by_user_id=other.user_id)
        await _private_consume(private, consumed.token, member.user_id)
        await _private_issue(private, INVITE, created_by_user_id=other.user_id, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(minutes=1))
        await _private_issue(private, PASSWORD_RESET, user_id=member.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, "10")
        monkeypatch.setenv(BILLING_URL_VARIABLE, BILLING_LINK)

        invitations = await _call(private, "GET", "/users/invites", cookie=cookie)
        accounts = await _call(private, "GET", "/users", cookie=cookie)
        monkeypatch.delenv(MAX_USERS_VARIABLE)
        monkeypatch.delenv(BILLING_URL_VARIABLE)
        unlimited = await _call(private, "GET", "/users/invites", cookie=cookie)

        assert (invitations.status_code, accounts.status_code, unlimited.status_code) == (200, 200, 200), f"{invitations.text}; {accounts.text}; {unlimited.text}"
        usage = {"used": 5, "max_users": 10, "billing_url": BILLING_LINK}
        violations: list[str] = []
        listed = sorted(item["id"] for item in invitations.json()["items"])
        _expect(violations, listed == sorted([live.json()["invite"]["id"], live_by_other.record.id]), f"GET /users/invites must list the two live invitations only, whoever issued them: {listed}")
        _expect(violations, invitations.json()["usage"] == usage, f"GET /users/invites usage: expected {usage}, got {invitations.json()['usage']}")
        items = {item["id"]: item for item in accounts.json()["items"]}
        _expect(violations, sorted(items) == sorted(account.user_id for account in (root, other, member, dormant)), f"GET /users must list every account, active or not: {sorted(items)}")
        for account, active, superuser in ((root, True, True), (other, True, True), (member, True, False), (dormant, False, False)):
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser)
        _expect(violations, accounts.json()["usage"] == usage, f"GET /users usage: expected {usage}, got {accounts.json()['usage']}")
        _expect(violations, unlimited.json()["usage"] == {"used": 5, "max_users": None, "billing_url": None}, f"without the variables: {unlimited.json()['usage']}")
        assert not violations, f"Listing and usage broke their contract:{_verdict(violations)}"
        print_success("two live invitations listed, four accounts, used 5")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["expired", "never-issued"])
    async def test_an_expired_or_never_issued_invitation_cannot_be_revoked(self, private: _Private, kind: str) -> None:
        """UADM-029: DELETE /users/invites/{id} of an expired invitation, or of an id never issued → 404, and nothing else is revoked.

        Presence barrier first: a live invitation is revoked with 204. A route that does not exist answers 404 too.
        """
        print_section(f"UADM-029: DELETE an {kind} invitation")
        root, cookie = await _admin(private)
        live = await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        barrier = await _call(private, "DELETE", f"/users/invites/{live.record.id}", cookie=cookie)
        assert barrier.status_code == 204, f"Presence barrier: DELETE of a live invitation must answer 204, or the 404 below proves nothing: {barrier.status_code} {barrier.text}"
        invite_id = NEVER_ISSUED_ID
        if kind == "expired":
            invite_id = (await _private_issue(private, INVITE, created_by_user_id=root.user_id, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(minutes=1))).record.id
        revoked_before = {row.id for row in await _private_tokens(private) if row.revoked_at is not None}

        response = await _call(private, "DELETE", f"/users/invites/{invite_id}", cookie=cookie)

        assert response.status_code == 404, f"an {kind} invitation is not live: expected 404, got {response.status_code} {response.text}"
        assert {row.id for row in await _private_tokens(private) if row.revoked_at is not None} == revoked_before, "a refused revocation must revoke nothing"
        print_success("404")


# ============================================================================
# IN-PROCESS: STRUCTURED LOGS, AND NO TOKEN IN THEM
# ============================================================================


#: The SQL loggers: they print every statement with its parameters, the stored token_hash included.
SQL_LOGGERS = frozenset({"aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool"})


def _warning_target(node: ast.AST) -> Optional[ast.expr]:
    """The argument of ``logging.getLogger(<argument>).setLevel(logging.WARNING)`` when ``node`` is that call; None otherwise."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "setLevel" and node.args):
        return None
    level, getter = node.args[0], node.func.value
    if not (isinstance(level, ast.Attribute) and level.attr == "WARNING" and isinstance(getter, ast.Call) and getter.args):
        return None
    return getter.args[0] if isinstance(getter.func, ast.Attribute) and getter.func.attr == "getLogger" else None


def _silenced_by_the_app() -> frozenset[str]:
    """The third-party loggers that ``configure_logging`` (``backend/app/logging_config.py``) sets to WARNING, read from its source so that this list cannot drift from it.

    Two forms: ``logging.getLogger("name").setLevel(logging.WARNING)``, and the same call on the variable of a ``for``
    loop over a literal tuple of names.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(logging_config.configure_logging)))
    loops = {node.target.id: [item.value for item in node.iter.elts if isinstance(item, ast.Constant)] for node in ast.walk(tree) if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and isinstance(node.iter, (ast.Tuple, ast.List))}
    names: set[str] = set()
    for node in ast.walk(tree):
        target = _warning_target(node)
        if isinstance(target, ast.Constant) and isinstance(target.value, str):
            names.add(target.value)
        elif isinstance(target, ast.Name):
            names.update(str(name) for name in loops.get(target.id, ()))
    return frozenset(names)


def _is_silenced(logger_name: str, silenced: frozenset[str]) -> bool:
    """Whether a logger is one of ``silenced`` or a child of one: a child inherits the WARNING level."""
    return any(logger_name == name or logger_name.startswith(f"{name}.") for name in silenced)


def _carries(record: logging.LogRecord, secrets: list[str]) -> bool:
    """Whether a stdlib record shows one of ``secrets``, in its message or anywhere among its attributes."""
    shown = record.getMessage() + repr(vars(record))
    return any(secret in shown for secret in secrets)


class TestStructuredLogs:
    @pytest.mark.asyncio
    async def test_every_admin_action_writes_a_structured_event_and_no_log_carries_a_token(self, private: _Private, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """UADM-030: each admin action — an invitation issued and revoked, two reset links, deactivation, reactivation, promotion, demotion, sessions revoked, onboarding reset (all, then one flow) — emits at least one structlog event with a field besides its message. No structlog event and no stdlib record carries a token's plaintext (hence neither its path nor its URL), whatever the logger. No structlog event, and no record of the application's own loggers, carries its hash.

        The hash is the value of the ``token_hash`` column, so the SQL loggers print it among the parameters of the INSERT.
        ``configure_logging`` silences them to WARNING (``backend/app/logging_config.py``), so a running server never emits
        those records: caplog sees them only because it lowers the level. Their names are read from that function's source
        (``_silenced_by_the_app``), and a record of one of them or of a child is left out of the hash check only.

        Barriers first: a canary through the users module's logger name reaches both captures, or a capture that sees
        nothing would pass for endpoints that log nothing.
        """
        print_section("UADM-030: structured logs without tokens")
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        monkeypatch.setattr(logging.getLogger(users_api.__name__), "disabled", False)
        caplog.set_level(logging.DEBUG)
        caplog.set_level(logging.DEBUG, logger=users_api.__name__)
        actions: dict[str, list[dict[str, Any]]] = {}
        bodies: list[Any] = []

        with capture_logs() as events:
            structlog.get_logger(users_api.__name__).info(CANARY)
            logging.getLogger(users_api.__name__).info(CANARY)

            async def act(label: str, method: str, path: str, body: Any = None, status: int = 200) -> Any:
                start = len(events)
                response = await _call(private, method, path, cookie=cookie, json=body)
                assert response.status_code == status, f"{label}: expected {status}, got {response.status_code} {response.text}"
                actions[label] = list(events[start:])
                bodies.append(response.json() if response.content else None)
                return bodies[-1]

            invitation = await act("issue an invitation", "POST", "/users/invites", {"grants_admin": True, "email": "guest@example.com"}, 201)
            await act("revoke the invitation", "DELETE", f"/users/invites/{invitation['invite']['id']}", None, 204)
            first = await act("issue a reset link", "POST", f"/users/{member.user_id}/password-reset-link", None, 201)
            second = await act("issue another reset link", "POST", f"/users/{member.user_id}/password-reset-link", None, 201)
            await act("deactivate", "PATCH", f"/users/{member.user_id}", {"is_active": False})
            await act("reactivate", "PATCH", f"/users/{member.user_id}", {"is_active": True})
            await act("promote", "PATCH", f"/users/{member.user_id}", {"is_superuser": True})
            await act("demote", "PATCH", f"/users/{member.user_id}", {"is_superuser": False})
            await act("revoke the sessions", "POST", f"/users/{member.user_id}/sessions/revoke", None, 204)
            await act("reset the onboarding", "POST", f"/users/{member.user_id}/onboarding/reset", {}, 204)
            await act("reset one flow", "POST", f"/users/{member.user_id}/onboarding/reset", {"flow": OnboardingFlow.INTRO_TOUR.value}, 204)
            reads = [await _call(private, "GET", path, cookie=cookie) for path in ("/users/invites", "/users")]

        assert any(event.get("event") == CANARY for event in events), "barrier: structlog events of the users module's logger do not reach capture_logs"
        assert any(record.getMessage() == CANARY for record in caplog.records), "barrier: stdlib records of the users module's logger do not reach caplog"
        assert [read.status_code for read in reads] == [200, 200], f"the reads inside the capture: {[read.text for read in reads]}"
        silenced = _silenced_by_the_app()
        assert SQL_LOGGERS <= silenced, f"premise: configure_logging silences the SQL loggers {sorted(SQL_LOGGERS)} to WARNING, as read from its source: {sorted(silenced)}"
        silent = [label for label, captured in actions.items() if not any(set(event) - {"event", "log_level"} for event in captured)]
        tokens = [invitation["token"], first["token"], second["token"]]
        hashes = [hash_token(token) for token in tokens]
        plaintext_events = [event for event in events if any(token in repr(event) for token in tokens)]
        plaintext_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if _carries(record, tokens)]
        hash_events = [event for event in events if any(digest in repr(event) for digest in hashes)]
        hash_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if not _is_silenced(record.name, silenced) and _carries(record, hashes)]
        violations: list[str] = []
        _expect(violations, silent == [], f"these actions wrote no structured event: {silent}")
        _expect(violations, plaintext_events == [], f"structlog events carrying a plaintext token: {plaintext_events}")
        _expect(violations, plaintext_records == [], f"stdlib records carrying a plaintext token, whatever the logger: {plaintext_records}")
        _expect(violations, hash_events == [], f"structlog events carrying a token's hash: {hash_events}")
        _expect(violations, hash_records == [], f"records of the application's loggers carrying a token's hash: {hash_records}")
        assert not violations, f"Every admin action logs, and no log carries a token:{_verdict(violations)}"
        print_success(f"{len(actions)} actions logged; {len(events)} events and {len(caplog.records)} records without a plaintext, no hash outside {sorted(SQL_LOGGERS)}")


# ============================================================================
# IN-PROCESS, ON THE MIGRATED SCHEMA: THE HOOK OF LOT A7, THE LOG, A FAILURE (lot A6a)
# ============================================================================


@pytest.fixture(scope="module")
def head_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to head by the real migrations, in a child process, once for the module. Read-only: each test works on a copy."""
    data_dir = tmp_path_factory.mktemp("users-admin-head") / "data"
    db = data_dir / "sqlite" / "app.db"
    _alembic_upgrade_head(db, data_dir)
    return db


@pytest_asyncio.fixture
async def private_head(head_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """A private instance with the schema production has — a copy of the migrated template — and the default settings; no accounts variable; bcrypt at cost 4. Disposed at teardown.

    The BRIM report directory moves under tmp_path: private broker ids start at 1 like the lane's, and the cleanup of a
    deleted private broker would otherwise remove a neighbour's reports.
    """
    for name in ACCOUNTS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    reports = tmp_path / "broker_reports"
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: reports)
    database = tmp_path / "instance.db"
    with contextlib.closing(sqlite3.connect(head_template)) as source, contextlib.closing(sqlite3.connect(database)) as copy:
        source.backup(copy)
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}", poolclass=NullPool)
    try:
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_private_app(engine))
    finally:
        await engine.dispose()


def _protect(monkeypatch: pytest.MonkeyPatch, *user_ids: int) -> None:
    """Replace the hook of lot A7, a plain function: a reason for the accounts ``user_ids``, None for every other one.

    ``raising=False``: before A6a the hook does not exist, and the red is then the route's answer, not this setup.
    """
    protected = frozenset(user_ids)

    def account_protection(user: User) -> Optional[str]:
        return PROTECTION_REASON if user.id in protected else None

    monkeypatch.setattr(user_service, "account_protection", account_protection, raising=False)


def _spy_on_report_cleanup(monkeypatch: pytest.MonkeyPatch) -> list[list[int]]:
    """Replace delete_files_for_brokers, under both names a caller may reach, by a spy answering FILES_REMOVED; the broker ids of each call."""
    calls: list[list[int]] = []

    def delete_files_for_brokers(broker_ids: Any) -> int:
        calls.append([int(broker_id) for broker_id in broker_ids])
        return FILES_REMOVED

    monkeypatch.setattr(brim_provider, "delete_files_for_brokers", delete_files_for_brokers)
    monkeypatch.setattr(user_service, "delete_files_for_brokers", delete_files_for_brokers, raising=False)
    return calls


async def _private_broker(private: _Private, name: str, grants: list[tuple[int, UserRole]], *, deposits: int = 0) -> int:
    """A broker of the private instance with these grants and DEPOSITs, committed; its id."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        broker = Broker(name=name)
        session.add(broker)
        await session.flush()
        session.add_all([_grant(user_id, broker.id, role) for user_id, role in grants])
        session.add_all([_deposit(broker.id) for _ in range(deposits)])
        await session.commit()
    return broker.id


async def _private_holdings(private: _Private) -> dict[str, Any]:
    """Every account (flags and session version), broker, grant and transaction of the private instance: the test owns them all."""
    async with AsyncSession(private.engine) as session:
        accounts = (await session.execute(select(User.username, User.is_active, User.is_superuser, User.session_version))).all()
        brokers = (await session.execute(select(Broker.id, Broker.name))).all()
        grants = (await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.user_id, BrokerUserAccess.role))).all()
        transactions = (await session.execute(select(Transaction.id, Transaction.broker_id, Transaction.related_transaction_id))).all()
    return {
        "accounts": sorted(tuple(row) for row in accounts),
        "brokers": sorted(tuple(row) for row in brokers),
        "grants": sorted((broker_id, user_id, UserRole(role).value) for broker_id, user_id, role in grants),
        "transactions": sorted(tuple(row) for row in transactions),
    }


def _logged(event: dict[str, Any]) -> dict[str, Any]:
    """The fields of an administrator's deletion an event carries, a sequence read as a list."""
    return {key: list(value) if isinstance(value, (list, tuple)) else value for key, value in event.items() if key in ADMIN_DELETION_FIELDS}


async def _failing_delete_bulk(self: BrokerService, *args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("injected technical failure while deleting a broker")


class TestAccountProtectionInProcess:
    """The hook of lot A7, replaced in this process: a reason for one account. root, the caller, is an active administrator the hook never protects."""

    @pytest.mark.asyncio
    async def test_a_protected_account_is_neither_deactivated_nor_demoted(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-050: boss, an active administrator the hook protects: PATCH {is_active: false} and PATCH {is_superuser: false} → 409 ACCOUNT_PROTECTED, and boss is as it was, version included.

        Barrier: the same two calls on peer, an administrator the hook does not protect, → 200. root stays an active
        administrator throughout, so LAST_ADMIN never applies: only the hook can refuse.
        """
        print_section("UADM-050: PATCH on a protected account")
        _, cookie = await _admin(private_head)
        boss = await _add_user(private_head, "boss", admin=True)
        peer = await _add_user(private_head, "peer", admin=True)
        _protect(monkeypatch, boss.user_id)
        before = await _private_user(private_head, boss.user_id)

        deactivate = await _call(private_head, "PATCH", f"/users/{boss.user_id}", cookie=cookie, json={"is_active": False})
        demote = await _call(private_head, "PATCH", f"/users/{boss.user_id}", cookie=cookie, json={"is_superuser": False})
        after = await _private_user(private_head, boss.user_id)
        peer_demoted = await _call(private_head, "PATCH", f"/users/{peer.user_id}", cookie=cookie, json={"is_superuser": False})
        peer_deactivated = await _call(private_head, "PATCH", f"/users/{peer.user_id}", cookie=cookie, json={"is_active": False})

        violations: list[str] = []
        _expect(violations, _refusal(deactivate) == (409, "ACCOUNT_PROTECTED"), f"deactivating a protected account: expected 409 ACCOUNT_PROTECTED, got {deactivate.status_code} {deactivate.text}")
        _expect(violations, _refusal(demote) == (409, "ACCOUNT_PROTECTED"), f"demoting a protected account: expected 409 ACCOUNT_PROTECTED, got {demote.status_code} {demote.text}")
        _expect(violations, after == before, f"a refused change must change nothing, the version included: {before} → {after}")
        _expect(violations, (peer_demoted.status_code, peer_deactivated.status_code) == (200, 200), f"Barrier: the same changes on an administrator the hook does not protect go through: {peer_demoted.status_code} {peer_demoted.text}; {peer_deactivated.status_code} {peer_deactivated.text}")
        _expect(violations, (await _private_user(private_head, peer.user_id))[:2] == (False, False), "the unprotected administrator must end up inactive and demoted")
        assert not violations, f"The hook must stop the deactivation and the demotion of the account it protects:{_verdict(violations)}"
        print_success("409 ACCOUNT_PROTECTED twice, the protected account untouched; the unprotected one changed")

    @pytest.mark.asyncio
    async def test_a_protected_account_is_not_deleted(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-051: patron, an ordinary account the hook protects and the only OWNER of a broker with a DEPOSIT: DELETE → 409 ACCOUNT_PROTECTED; every account, broker, grant and transaction as before, and no report file touched. Barrier: DELETE of other, an ordinary account the hook does not protect, → 204, gone."""
        print_section("UADM-051: DELETE of a protected account")
        _, cookie = await _admin(private_head)
        patron = await _add_user(private_head, "patron")
        other = await _add_user(private_head, "other")
        await _private_broker(private_head, "Patron's broker", [(patron.user_id, UserRole.OWNER)], deposits=1)
        _protect(monkeypatch, patron.user_id)
        calls = _spy_on_report_cleanup(monkeypatch)
        before = await _private_holdings(private_head)

        refused = await _call(private_head, "DELETE", f"/users/{patron.user_id}", cookie=cookie)
        after = await _private_holdings(private_head)
        calls_after_refusal = list(calls)
        allowed = await _call(private_head, "DELETE", f"/users/{other.user_id}", cookie=cookie)
        usernames = [row[0] for row in (await _private_holdings(private_head))["accounts"]]

        violations: list[str] = []
        _expect(violations, _refusal(refused) == (409, "ACCOUNT_PROTECTED"), f"deleting a protected account: expected 409 ACCOUNT_PROTECTED, got {refused.status_code} {refused.text}")
        _expect(violations, after == before, f"a refused deletion must change nothing: before {before}, after {after}")
        _expect(violations, calls_after_refusal == [], f"a refused deletion must touch no report file: {calls_after_refusal}")
        _expect(violations, allowed.status_code == 204 and other.username not in usernames, f"Barrier: an account the hook does not protect is deleted: {allowed.status_code} {allowed.text}, accounts now {usernames}")
        assert not violations, f"The hook must stop the deletion of the account it protects:{_verdict(violations)}"
        print_success("409 ACCOUNT_PROTECTED, everything in place; the unprotected account deleted")

    @pytest.mark.asyncio
    async def test_protected_says_whether_the_hook_gives_a_reason(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-052: the hook protects boss: GET /users lists root, boss and member with exactly their eight fields, ``protected`` true for boss alone; PATCH promoting member answers it with ``protected`` false."""
        print_section("UADM-052: the protected field")
        root, cookie = await _admin(private_head)
        boss = await _add_user(private_head, "boss", admin=True)
        member = await _add_user(private_head, "member")
        _protect(monkeypatch, boss.user_id)

        listed = await _call(private_head, "GET", "/users", cookie=cookie)
        promoted = await _call(private_head, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})

        assert (listed.status_code, promoted.status_code) == (200, 200), f"GET /users {listed.status_code} {listed.text}; PATCH {promoted.status_code} {promoted.text}"
        items = {item.get("id"): item for item in listed.json()["items"]}
        violations = _user_item_violations(items.get(root.user_id), root, active=True, superuser=True)
        violations += _user_item_violations(items.get(boss.user_id), boss, active=True, superuser=True, protected=True)
        violations += _user_item_violations(items.get(member.user_id), member, active=True, superuser=False)
        violations += [f"PATCH: {problem}" for problem in _user_item_violations(promoted.json(), member, active=True, superuser=True)]
        assert not violations, f"protected must say whether the hook gives a reason:{_verdict(violations)}"
        print_success("protected true for the account the hook protects, false for the others")


class TestAccountDeletionInProcess:
    """DELETE /users/{id} on a private instance with the production schema: what only this process can see — its log, an injected failure."""

    @pytest.mark.asyncio
    async def test_the_deletion_logs_one_structured_event_and_no_token_nor_password(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """UADM-053: root deletes leaver, the only OWNER of one broker and a co-OWNER of another with partner: 204; exactly one structlog event «Account deleted by an administrator» with user_id, username, admin_id, brokers_deleted [leaver's own broker] and files_removed (what the report cleanup answered); the cleanup ran once, for that broker; no structlog event and no stdlib record, whatever the logger, carries a session token (root's or leaver's) or the password; leaver and its own broker are gone, the shared broker stays.

        Barriers first, as UADM-030: a canary through the users module's logger name reaches both captures.
        """
        print_section("UADM-053: the administrator's deletion, in the log")
        root, root_cookie = await _admin(private_head)
        leaver = await _add_user(private_head, "leaver")
        partner = await _add_user(private_head, "partner")
        leaver_cookie = await _sign_in(private_head, leaver)
        sole = await _private_broker(private_head, "Leaver's broker", [(leaver.user_id, UserRole.OWNER)], deposits=1)
        shared = await _private_broker(private_head, "Shared broker", [(leaver.user_id, UserRole.OWNER), (partner.user_id, UserRole.OWNER)], deposits=1)
        calls = _spy_on_report_cleanup(monkeypatch)
        monkeypatch.setattr(logging.getLogger(users_api.__name__), "disabled", False)
        caplog.set_level(logging.DEBUG)
        caplog.set_level(logging.DEBUG, logger=users_api.__name__)

        with capture_logs() as events:
            structlog.get_logger(users_api.__name__).info(CANARY)
            logging.getLogger(users_api.__name__).info(CANARY)
            response = await _call(private_head, "DELETE", f"/users/{leaver.user_id}", cookie=root_cookie)

        assert any(event.get("event") == CANARY for event in events), "barrier: structlog events of the users module's logger do not reach capture_logs"
        assert any(record.getMessage() == CANARY for record in caplog.records), "barrier: stdlib records of the users module's logger do not reach caplog"
        holdings = await _private_holdings(private_head)
        deletions = [_logged(event) for event in events if event.get("event") == ADMIN_DELETION_EVENT]
        expected = {"user_id": leaver.user_id, "username": leaver.username, "admin_id": root.user_id, "brokers_deleted": [sole], "files_removed": FILES_REMOVED}
        secrets = [root_cookie, leaver_cookie, PRIVATE_PASSWORD]
        secret_events = [event for event in events if any(secret in repr(event) for secret in secrets)]
        secret_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if _carries(record, secrets)]
        violations: list[str] = []
        _expect(violations, (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}")
        _expect(violations, deletions == [expected], f"exactly one «{ADMIN_DELETION_EVENT}» event with {expected}: {deletions}")
        _expect(violations, calls == [[sole]], f"the report files of the deleted broker must be removed once: {calls}")
        _expect(violations, secret_events == [], f"structlog events carrying a session token or the password: {secret_events}")
        _expect(violations, secret_records == [], f"stdlib records carrying a session token or the password: {secret_records}")
        _expect(violations, leaver.username not in [row[0] for row in holdings["accounts"]] and [row[0] for row in holdings["brokers"]] == [shared], f"leaver and its own broker must be gone, the shared broker left: {holdings}")
        assert not violations, f"The administrator's deletion must log one event, without secrets:{_verdict(violations)}"
        print_success("one structured event with the five fields, no token, no password")

    @pytest.mark.asyncio
    async def test_a_technical_failure_answers_500_and_deletes_nothing(self, private_head: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-054: BrokerService.delete_bulk raises when the deletion reaches leaver's own broker — the shared broker, of a lower id, is already left inside the transaction: DELETE → 500 «nothing was deleted», as for one's own account; every account, broker, grant and transaction as before, and no report file touched."""
        print_section("UADM-054: a technical failure deletes nothing")
        _, cookie = await _admin(private_head)
        leaver = await _add_user(private_head, "leaver")
        partner = await _add_user(private_head, "partner")
        await _private_broker(private_head, "Shared broker", [(leaver.user_id, UserRole.OWNER), (partner.user_id, UserRole.OWNER)], deposits=1)
        await _private_broker(private_head, "Leaver's broker", [(leaver.user_id, UserRole.OWNER)], deposits=1)
        calls = _spy_on_report_cleanup(monkeypatch)
        monkeypatch.setattr(BrokerService, "delete_bulk", _failing_delete_bulk)
        before = await _private_holdings(private_head)

        response = await _call(private_head, "DELETE", f"/users/{leaver.user_id}", cookie=cookie)

        after = await _private_holdings(private_head)
        status, body = _answer(response)
        violations: list[str] = []
        _expect(violations, status == 500 and NOTHING_WAS_DELETED in str(body), f"expected 500 saying «{NOTHING_WAS_DELETED}», got {status} {body}")
        _expect(violations, after == before, f"a failed deletion must change nothing: before {before}, after {after}")
        _expect(violations, calls == [], f"a failed deletion must touch no report file: {calls}")
        assert not violations, f"A technical failure must delete nothing:{_verdict(violations)}"
        print_success("500, nothing deleted, no file touched")


# ============================================================================
# IN-PROCESS: THE PENDING ADMINISTRATOR IN THE USERS TAB (lot A7b, C5)
# ============================================================================


#: What a token in each state of ``_private_link`` reads as, once the scene is built.
LINK_STATUSES = {"live": TokenStatus.VALID, "expired": TokenStatus.EXPIRED, "revoked": TokenStatus.REVOKED, "consumed": TokenStatus.CONSUMED}


@dataclass(frozen=True)
class _PendingAdmin:
    """The F02 administrator the bootstrap made on a private instance, and the token of its setup link (live, unless the case asked for it expired)."""

    account: _Account
    token: str


async def _bootstrap_pending_admin(private: _Private, *, expired: bool = False) -> _PendingAdmin:
    """The pending administrator F02 makes: ``run_admin_bootstrap`` on the still empty private instance, for F02_USERNAME and F02_EMAIL, the token of its setup link given by the configuration so that the test holds the link; committed by the service. ``expired``: the bootstrap ran the link's lifetime and a minute ago, so the link has expired — never waited for — and the account waits all the same.

    Run it first: the bootstrap creates its administrator on an instance without accounts only. It ends on what it
    promises — ``CREATED``, the account an inactive superuser, the token an ``admin_setup`` link of that account, live or
    expired as asked. ``account.password`` is the one its setup would choose, SETUP_PASSWORD; until then nobody knows it.
    """
    token = token_urlsafe(32)
    moment = utcnow() - DEFAULT_TTL[ADMIN_SETUP] - timedelta(minutes=1) if expired else utcnow()
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        result = await run_admin_bootstrap(session, AdminBootstrapConfig(email=F02_EMAIL, username=F02_USERNAME, token=token), now=moment)
    assert result.action == BootstrapAction.CREATED and result.user_id is not None, f"Setup: on an empty instance the bootstrap creates the pending administrator: {result!r}"
    async with AsyncSession(private.engine) as session:
        link = await inspect_token(session, token, ADMIN_SETUP)
    owner = link.record.user_id if link.record is not None else None
    expected = TokenStatus.EXPIRED if expired else TokenStatus.VALID
    assert (link.status, owner) == (expected, result.user_id), f"Setup: the configuration's token must be a setup link of the new account {result.user_id}, {expected.value}: {link.status.value}, owner {owner}"
    flags = (await _private_user(private, result.user_id))[:2]
    assert flags == (False, True), f"Setup: the pending administrator is an inactive superuser: (is_active, is_superuser) {flags}"
    return _PendingAdmin(account=_Account(user_id=result.user_id, username=F02_USERNAME, email=F02_EMAIL, password=SETUP_PASSWORD), token=token)


async def _private_link(private: _Private, user_id: int, purpose: AccountTokenPurpose, state: str) -> None:
    """A token of ``purpose`` for the account, through the token service: ``live`` (issued now), ``expired`` (issued its lifetime and a minute ago, never waited for), ``revoked``, or ``consumed`` by the account itself, as its setup or a reset spends it.

    It ends on what it promises: the token reads as that state (LINK_STATUSES).
    """
    issued_at = utcnow() - DEFAULT_TTL[purpose] - timedelta(minutes=1) if state == "expired" else utcnow()
    issued = await _private_issue(private, purpose, user_id=user_id, now=issued_at)
    async with AsyncSession(private.engine) as session:
        if state == "revoked":
            await revoke_tokens(session, token_id=issued.record.id)
        elif state == "consumed":
            await consume_token(session, issued.token, purpose, consumed_by_user_id=user_id)
        await session.commit()
        status = (await inspect_token(session, issued.token, purpose)).status
    assert status == LINK_STATUSES[state], f"Setup: a {state} {purpose.value} token must read {LINK_STATUSES[state].value}, it reads {status.value}"


async def _pending_admin_ids(private: _Private) -> set[int]:
    """The accounts ``registration_service.pending_admin_filter()`` selects in the private database: A7a's notion of the account waiting for its setup, the one C5 reuses."""
    async with AsyncSession(private.engine) as session:
        return set((await session.execute(select(User.id).where(*registration_service.pending_admin_filter()))).scalars().all())


async def _private_listed(private: _Private, cookie: str) -> dict[int, dict[str, Any]]:
    """GET /users as this administrator: the listed accounts by id, after a 200."""
    response = await _call(private, "GET", "/users", cookie=cookie)
    assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
    return {item["id"]: item for item in response.json()["items"]}


async def _private_view(private: _Private, cookie: str, user_id: int) -> tuple[Optional[dict[str, Any]], Any]:
    """GET /users as this administrator: the account's item, found by id (None when absent), and the usage."""
    response = await _call(private, "GET", "/users", cookie=cookie)
    assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
    body = response.json()
    return next((item for item in body["items"] if item.get("id") == user_id), None), body.get("usage")


async def _private_snapshot(private: _Private) -> dict[str, list[dict[str, Any]]]:
    """Every row of ``users`` and ``account_tokens`` in the private database, as raw column values read from the tables: what a refused PATCH may not change. The test owns them all."""
    async with AsyncSession(private.engine) as session:
        users = (await session.execute(select(User.__table__).order_by(User.__table__.c.id))).mappings().all()
        tokens = (await session.execute(select(AccountToken.__table__).order_by(AccountToken.__table__.c.id))).mappings().all()
    return {"users": [dict(row) for row in users], "account_tokens": [dict(row) for row in tokens]}


def _snapshot_changes(before: dict[str, list[dict[str, Any]]], after: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """The rows of each table that are not the same before and after, as ``{table: {"before": […], "after": […]}}``; empty when nothing changed."""
    changes: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for table in sorted(before.keys() | after.keys()):
        gone = [row for row in before.get(table, []) if row not in after.get(table, [])]
        new = [row for row in after.get(table, []) if row not in before.get(table, [])]
        if gone or new:
            changes[table] = {"before": gone, "after": new}
    return changes


@dataclass(frozen=True)
class _SetupScene:
    """An account of the private instance: whether it is active and an administrator, its tokens as ``(purpose, state)`` in the order they are issued (``_private_link``), and the ``pending_setup`` C5 expects for it."""

    active: bool
    superuser: bool
    tokens: tuple[tuple[AccountTokenPurpose, str], ...]
    pending_setup: bool


#: The scenes of BOOT-016 (``pending_admin``, ``test_admin_bootstrap.py``) as accounts of the Users tab, and three more:
#: a re-armed link (what ``./dev.py user setup-link`` leaves), an account no longer an administrator, and an inactive
#: administrator without a setup link — with no token, or with a reset link.
PENDING_SETUP_SCENES = [
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "live"),), pending_setup=True), id="inactive-with-a-live-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "expired"),), pending_setup=True), id="inactive-with-an-expired-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "revoked"),), pending_setup=True), id="inactive-with-a-revoked-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "revoked"), (ADMIN_SETUP, "live")), pending_setup=True), id="inactive-re-armed"),
    pytest.param(_SetupScene(active=False, superuser=False, tokens=((ADMIN_SETUP, "live"),), pending_setup=True), id="inactive-not-an-administrator-with-a-live-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"),), pending_setup=False), id="inactive-with-a-consumed-setup-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"), (ADMIN_SETUP, "live")), pending_setup=False), id="inactive-with-a-consumed-and-a-live-setup-link"),
    pytest.param(_SetupScene(active=True, superuser=True, tokens=((ADMIN_SETUP, "live"),), pending_setup=False), id="active-with-a-live-setup-link"),
    pytest.param(_SetupScene(active=True, superuser=True, tokens=((ADMIN_SETUP, "consumed"), (ADMIN_SETUP, "revoked")), pending_setup=False), id="active-after-its-setup"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((PASSWORD_RESET, "live"),), pending_setup=False), id="inactive-administrator-with-a-reset-link-only"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=(), pending_setup=False), id="inactive-administrator-without-any-link"),
]

#: What an administrator may do to the pending administrator that leaves it waiting for its setup, with whether it is an administrator afterwards.
PENDING_ADMIN_CHANGES = [
    pytest.param({"is_superuser": False}, False, id="demoted"),
    pytest.param({"is_active": False}, True, id="deactivated-while-already-inactive"),
]

#: The detail of the refusal to activate the pending administrator carries exactly these keys (UADM-065); the wording of its message is not pinned.
PENDING_SETUP_KEYS = frozenset({"error_code", "message"})

#: PATCH bodies that would activate the pending administrator: refused whole, whatever else they ask.
ACTIVATIONS = [
    pytest.param({"is_active": True}, id="activate"),
    pytest.param({"is_active": True, "is_superuser": True}, id="activate-as-an-administrator"),
    pytest.param({"is_active": True, "is_superuser": False}, id="activate-and-demote"),
]

#: The pending administrator's setup link, live or expired: the account waits all the same (pending_admin_filter()).
PENDING_LINKS = [pytest.param(False, id="its-link-live"), pytest.param(True, id="its-link-expired")]

#: Inactive accounts that do not wait for a setup: an ordinary member, an administrator without any link, and an
#: administrator whose setup link was spent — deactivated after its setup, its password known.
NOT_PENDING_INACTIVE = [
    pytest.param(_SetupScene(active=False, superuser=False, tokens=(), pending_setup=False), id="a-member-without-any-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=(), pending_setup=False), id="an-administrator-without-any-link"),
    pytest.param(_SetupScene(active=False, superuser=True, tokens=((ADMIN_SETUP, "consumed"),), pending_setup=False), id="an-administrator-whose-setup-link-was-spent"),
]


class TestThePendingAdministratorInTheUsersTab:
    """Lot A7b, C5: the Users tab tells the account waiting for its F02 setup from a deactivated one, and the PATCH refuses to activate it. In-process only: a pending administrator never enters the lane's database."""

    @pytest.mark.asyncio
    async def test_the_pending_administrator_is_listed_pending_setup_and_nobody_else(self, private: _Private) -> None:
        """UADM-060: the bootstrap made the pending administrator; root (the caller), a member, a deactivated account and an account waiting for its email verification (a live verification link, written directly) are there too. GET /users → pending_setup true for the pending administrator only, false for every other account; holds_place true for the waiting account only — false for the pending administrator, whose place another rule counts —; each account exactly its nine fields; usage as before: used 4 (root, the member, the waiting account, the pending administrator), no limit, no billing link."""
        print_section("UADM-060: GET /users with the pending administrator")
        pending = await _bootstrap_pending_admin(private)
        root, cookie = await _admin(private)
        member = await _add_user(private, "member")
        dormant = await _add_user(private, "dormant", active=False)
        waiting = await _add_user(private, "waiting", active=False)
        await _private_link(private, waiting.user_id, EMAIL_VERIFICATION, "live")

        response = await _call(private, "GET", "/users", cookie=cookie)

        assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
        body = response.json()
        items = {item["id"]: item for item in body["items"]}
        # (account, is_active, is_superuser, holds_place, pending_setup)
        expected = [(pending.account, False, True, False, True), (root, True, True, False, False), (member, True, False, False, False), (dormant, False, False, False, False), (waiting, False, False, True, False)]
        flags = {item.get("username"): item.get("pending_setup", "<missing>") for item in body["items"]}
        violations: list[str] = []
        _expect(violations, sorted(items) == sorted(row[0].user_id for row in expected), f"GET /users must list every account of the instance: {sorted(items)}")
        _expect(violations, flags == {F02_USERNAME: True, "root": False, "member": False, "dormant": False, "waiting": False}, f"pending_setup must be true for the pending administrator only: {flags}")
        for account, active, superuser, holds_place, pending_setup in expected:
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser, holds_place=holds_place, pending_setup=pending_setup)
        _expect(violations, body["usage"] == {"used": 4, "max_users": None, "billing_url": None}, f"usage must count as before — root, the member, the waiting account and the pending administrator: {body['usage']}")
        assert not violations, f"GET /users must tell the pending administrator apart, and only it:{_verdict(violations)}"
        print_success("pending_setup true for the pending administrator only; holds_place its own flag; usage unchanged")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scene", PENDING_SETUP_SCENES)
    async def test_pending_setup_is_the_notion_of_pending_admin_filter(self, private: _Private, scene: _SetupScene) -> None:
        """UADM-061: an account in one state of its setup links, beside root, the caller. GET /users → its pending_setup is true exactly when it is inactive with an admin_setup token and none of them consumed — live, expired or revoked alike, an administrator or not —: the notion of registration_service.pending_admin_filter(), which user_usage counts. Root's is false; both are exactly their nine fields.

        Premise first: the filter selects the account exactly when the scene says it waits. If it no longer does, A7a's
        notion has moved, and this expectation moves with it, not the flag.
        """
        print_section(f"UADM-061: pending_setup of an account active={scene.active}, administrator={scene.superuser}, tokens {[(purpose.value, state) for purpose, state in scene.tokens]}")
        root, cookie = await _admin(private)
        subject = await _add_user(private, "subject", admin=scene.superuser, active=scene.active)
        for purpose, state in scene.tokens:
            await _private_link(private, subject.user_id, purpose, state)
        selected = subject.user_id in await _pending_admin_ids(private)
        assert selected is scene.pending_setup, f"premise: pending_admin_filter() selects this account: {selected}; C5 expects pending_setup {scene.pending_setup} because it is the same notion — if the filter moved, this expectation moves with it"

        items = await _private_listed(private, cookie)

        violations = _user_item_violations(items.get(subject.user_id), subject, active=scene.active, superuser=scene.superuser, pending_setup=scene.pending_setup)
        violations += _user_item_violations(items.get(root.user_id), root, active=True, superuser=True)
        assert not violations, f"pending_setup must be the notion of pending_admin_filter():{_verdict(violations)}"
        print_success(f"pending_setup {scene.pending_setup}, as the filter says; root false")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("change", "superuser_after"), PENDING_ADMIN_CHANGES)
    async def test_the_patch_answer_carries_pending_setup_as_the_list_does(self, private: _Private, change: dict[str, bool], superuser_after: bool) -> None:
        """UADM-062: PATCH /users/{the pending administrator} with a change that leaves it waiting for its setup — a demotion, or {is_active: false} on the account already inactive — → 200, the account exactly its nine fields, still inactive, pending_setup true. The answer replaces its row in the Users tab: it is the item GET /users lists right after.

        Premise: after the change the filter still selects the account. The flag is the one of the account the PATCH
        returns, as ``holds_place`` is.
        """
        print_section(f"UADM-062: PATCH {change} on the pending administrator")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)

        response = await _call(private, "PATCH", f"/users/{pending.account.user_id}", cookie=cookie, json=change)

        assert response.status_code == 200, f"PATCH {change} on the pending administrator: expected 200, got {response.status_code} {response.text}"
        assert pending.account.user_id in await _pending_admin_ids(private), f"premise: after {change} the account still waits for its setup"
        listed = (await _private_listed(private, cookie)).get(pending.account.user_id)
        answer = response.json()
        violations = _user_item_violations(answer, pending.account, active=False, superuser=superuser_after, pending_setup=True)
        _expect(violations, _comparable(answer) == _comparable(listed), f"the answer must be the account as GET /users lists it right after: answered {answer}, listed {listed}")
        assert not violations, f"The PATCH answer must carry pending_setup as the list does:{_verdict(violations)}"
        print_success("200, pending_setup true, as the list says")

    @pytest.mark.asyncio
    async def test_once_set_up_the_administrator_is_pending_no_more_even_deactivated(self, private: _Private) -> None:
        """UADM-063: the pending administrator, listed with pending_setup true, spends its setup link through POST /auth/setup (200): GET /users then lists it active, pending_setup false. Deactivated afterwards by root — PATCH {is_active: false} → 200 —, it is an ordinary inactive account, whose password is known: the answer, and the list after it, say pending_setup false.

        Premise: once its link was spent, the filter no longer selects the account.
        """
        print_section("UADM-063: set up, then deactivated — pending no more")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        before = (await _private_listed(private, cookie)).get(user_id)

        setup = await _call(private, "POST", "/auth/setup", json={"token": pending.token, "new_password": SETUP_PASSWORD})
        assert setup.status_code == 200, f"Setup: POST /auth/setup with the live link: expected 200, got {setup.status_code} {setup.text}"
        set_up = (await _private_listed(private, cookie)).get(user_id)
        off = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json={"is_active": False})
        assert off.status_code == 200, f"PATCH {{is_active: false}} after the setup: expected 200, got {off.status_code} {off.text}"
        listed_off = (await _private_listed(private, cookie)).get(user_id)

        assert user_id not in await _pending_admin_ids(private), "premise: once its link was spent, pending_admin_filter() no longer selects the account"
        answer = off.json()
        violations = _user_item_violations(before, pending.account, active=False, superuser=True, pending_setup=True)
        violations += _user_item_violations(set_up, pending.account, active=True, superuser=True)
        violations += _user_item_violations(answer, pending.account, active=False, superuser=True)
        _expect(violations, _comparable(answer) == _comparable(listed_off), f"the answer must be the account as GET /users lists it right after: answered {answer}, listed {listed_off}")
        assert not violations, f"An administrator set up is pending no more, even deactivated:{_verdict(violations)}"
        print_success("pending before its setup; not after it, nor after a deactivation")

    def test_admin_user_read_declares_pending_setup_false_by_default(self) -> None:
        """UADM-064: AdminUserRead declares ``pending_setup: bool``, false by default — an AdminUserRead built without it is not pending —, and nothing else changes: its fields are exactly the nine an account is listed with."""
        print_section("UADM-064: AdminUserRead.pending_setup")
        declared = AdminUserRead.model_fields.get("pending_setup")
        assert declared is not None, f"AdminUserRead must declare pending_setup (lot A7b, C5); it declares {sorted(AdminUserRead.model_fields)}"
        built = AdminUserRead(id=1, username="built", email="built@example.com", is_active=False, is_superuser=True, created_at=utcnow(), protected=False)

        violations: list[str] = []
        _expect(violations, declared.annotation is bool, f"pending_setup must be a bool: {declared.annotation!r}")
        _expect(violations, not declared.is_required() and declared.default is False, f"pending_setup must default to false: required {declared.is_required()}, default {declared.default!r}")
        _expect(violations, built.pending_setup is False, f"an account built without it must not be pending: {built.pending_setup!r}")
        _expect(violations, set(AdminUserRead.model_fields) == USER_ITEM_KEYS, f"AdminUserRead must be exactly {sorted(USER_ITEM_KEYS)}: {sorted(AdminUserRead.model_fields)}")
        assert not violations, f"AdminUserRead.pending_setup broke its contract:{_verdict(violations)}"
        print_success("a bool, false by default, nine fields")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("expired", PENDING_LINKS)
    @pytest.mark.parametrize("change", ACTIVATIONS)
    async def test_activating_the_pending_administrator_is_refused_and_changes_nothing(self, private: _Private, change: dict[str, bool], expired: bool) -> None:
        """UADM-065: PATCH /users/{the pending administrator} with a body that activates it — {is_active: true}, alone or with is_superuser true or false — → 409, detail exactly {error_code: PENDING_SETUP, message}, the message a sentence whose wording is not pinned. All or nothing, as the route's other refusals: nothing changes — the account still inactive and an administrator, its session version and password hash as they were (every row of users and account_tokens as it was); its setup link neither consumed nor revoked; its row in GET /users and the usage identical. Its link live or expired: it waits all the same (pending_admin_filter()), its password a secret nobody knows; the way in is a setup link, not an activation.

        Premise: the filter selects the account. No LIBREFOLIO_MAX_USERS in this process: the limit cannot refuse first.
        """
        print_section(f"UADM-065: PATCH {change} on the pending administrator, its link {'expired' if expired else 'live'}")
        pending = await _bootstrap_pending_admin(private, expired=expired)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id
        assert user_id in await _pending_admin_ids(private), "premise: pending_admin_filter() selects the pending administrator"
        listed_before, usage_before = await _private_view(private, cookie, user_id)
        assert listed_before is not None, "Presence barrier: GET /users must list the pending administrator, or «its row identical» below proves nothing"
        before = await _private_snapshot(private)

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=change)

        after = await _private_snapshot(private)
        listed_after, usage_after = await _private_view(private, cookie, user_id)
        detail = _detail(response)
        account = next(row for row in after["users"] if row["id"] == user_id)
        links = [(row["id"], row["consumed_at"], row["revoked_at"]) for row in after["account_tokens"] if row["user_id"] == user_id and row["purpose"] == ADMIN_SETUP]
        changes = _snapshot_changes(before, after)
        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "PENDING_SETUP"), f"expected 409 PENDING_SETUP, got {response.status_code} {response.text}")
        _expect(violations, set(detail) == PENDING_SETUP_KEYS and isinstance(detail.get("message"), str) and detail["message"].strip() != "", f"detail must be exactly {sorted(PENDING_SETUP_KEYS)}, the message a sentence: {detail}")
        _expect(violations, not account["is_active"], f"the pending administrator must still be inactive: is_active {account['is_active']!r}")
        _expect(violations, links != [] and all(consumed is None and revoked is None for _, consumed, revoked in links), f"its setup link must be neither consumed nor revoked: (id, consumed_at, revoked_at) {links}")
        _expect(violations, changes == {}, f"a refused PATCH must change nothing, all or nothing — rows that changed: {changes}")
        _expect(violations, (_comparable(listed_after), usage_after) == (_comparable(listed_before), usage_before), f"its row in GET /users and the usage must be identical: before {listed_before} {usage_before}, after {listed_after} {usage_after}")
        assert not violations, f"Activating the pending administrator must be refused, and change nothing:{_verdict(violations)}"
        print_success("409 PENDING_SETUP, nothing changed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scene", NOT_PENDING_INACTIVE)
    async def test_an_inactive_account_that_does_not_wait_for_its_setup_is_still_activated(self, private: _Private, scene: _SetupScene) -> None:
        """UADM-066, guard of UADM-065 (green today): the pending administrator waits on the instance, and PATCH {is_active: true} on another inactive account, which does not wait for its setup — an ordinary member, an administrator without any link, an administrator whose setup link was spent (deactivated after its setup) — → 200, active in the answer and in the database, an administrator or not as before. The refusal is the pending administrator's alone: not the instance's while one waits, not every inactive administrator's, not every account that ever had a setup link.

        Premise: the filter selects the pending administrator, and only it.
        """
        print_section(f"UADM-066: PATCH {{is_active: true}} on an inactive account that does not wait, administrator={scene.superuser}, tokens {[(purpose.value, state) for purpose, state in scene.tokens]}")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        subject = await _add_user(private, "subject", admin=scene.superuser, active=False)
        for purpose, state in scene.tokens:
            await _private_link(private, subject.user_id, purpose, state)
        assert await _pending_admin_ids(private) == {pending.account.user_id}, "premise: pending_admin_filter() selects the pending administrator, and only it"

        response = await _call(private, "PATCH", f"/users/{subject.user_id}", cookie=cookie, json={"is_active": True})

        assert response.status_code == 200, f"PATCH {{is_active: true}} on an inactive account that does not wait for its setup: expected 200, got {response.status_code} {response.text}"
        answer = response.json()
        state = (await _private_user(private, subject.user_id))[:2]
        violations: list[str] = []
        _expect(violations, (answer.get("is_active"), answer.get("is_superuser")) == (True, scene.superuser), f"the answer must be the account active, is_superuser {scene.superuser}: {answer}")
        _expect(violations, state == (True, scene.superuser), f"the account must be active in the database, is_superuser {scene.superuser}: (is_active, is_superuser) {state}")
        assert not violations, f"An inactive account that does not wait for its setup must still be activated:{_verdict(violations)}"
        print_success("200, active")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("change", "superuser_after"), PENDING_ADMIN_CHANGES)
    async def test_a_patch_that_leaves_the_pending_administrator_waiting_still_answers_200(self, private: _Private, change: dict[str, bool], superuser_after: bool) -> None:
        """UADM-067, guard of UADM-065 (green today): UADM-062's PATCHes on the pending administrator — a demotion, {is_active: false} on the account already inactive — still answer 200: only an activation is refused, not every change to the pending administrator, nor every body that names is_active. The answer and the database say inactive, an administrator or not as asked, and the account still waits: the filter selects it. Its pending_setup is UADM-062's to read (red until A7b): here only the status and the two states."""
        print_section(f"UADM-067: PATCH {change} on the pending administrator still answers 200")
        pending = await _bootstrap_pending_admin(private)
        _, cookie = await _admin(private)
        user_id = pending.account.user_id

        response = await _call(private, "PATCH", f"/users/{user_id}", cookie=cookie, json=change)

        assert response.status_code == 200, f"PATCH {change} leaves the pending administrator waiting: expected 200, got {response.status_code} {response.text}"
        answer = response.json()
        state = (await _private_user(private, user_id))[:2]
        violations: list[str] = []
        _expect(violations, (answer.get("is_active"), answer.get("is_superuser")) == (False, superuser_after), f"the answer must be the account inactive, is_superuser {superuser_after}: {answer}")
        _expect(violations, state == (False, superuser_after), f"in the database: (is_active, is_superuser) {state}, expected {(False, superuser_after)}")
        _expect(violations, user_id in await _pending_admin_ids(private), "the account must still wait for its setup: pending_admin_filter() no longer selects it")
        assert not violations, f"A PATCH that leaves the pending administrator waiting must still go through:{_verdict(violations)}"
        print_success("200, still waiting")
