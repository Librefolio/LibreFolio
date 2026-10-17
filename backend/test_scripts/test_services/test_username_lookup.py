"""A-21a, rule 3: ``get_user_by_username_or_email`` finds an address first, then a legacy username; without an @, a username only (release 1.3, workstream A, lot A-21a; workstream E's review, point c).

Until A-21a the lookup is one statement, ``username = :identifier OR lower(email) = lower(:identifier)``, and its
``.first()``. SQLite answers it with a MULTI-INDEX OR — ``ix_users_username`` first, then ``ux_users_email_lower`` —, so
when account A is named with account B's address, the identifier B's address finds A, in whatever order the two rows
were written: the squatter (workstream E's review, MEDIUM 8/10). The sign-in, «forgot password» and the verification
resend all look an identifier up through it. The contract pinned here, at the service:

- An identifier WITH an ``@`` is an address first: the account whose email is the identifier, A–Z case aside
  (``lower(email)``, decision P18). Only when no account has that address, the account whose username is exactly the
  identifier — a legacy username, written before A-21a refused the ``@`` (rule 1) —, compared as written.
- An identifier WITHOUT an ``@`` is a username only, compared exactly: no A–Z folding (lot A-21b may change that) and
  never an address — not even a legacy one without an ``@``: ``./dev.py user create`` stores the address it is given
  unchecked (``scripts/user_cli.py`` ``cmd_create_user``), so such rows exist.

The scenes, as E's review asks: B owns ``bob.<tag>@example.com``; A, a legacy account, is named with that address as B
writes it, or in another A–Z case; the two rows are written in both orders. B's address typed exactly as A's name is
written — B's address in its own case, or in another A–Z case — finds B (red today); typed in a form that is not A's name
it finds B today already (GUARD). A legacy name with an ``@`` that is nobody's address is still found by its exact
string, and only by it (GUARD: rule 3's fallback). Rules 1 and 2 — no new name with an ``@``, no address that is a name —
are ``test_username_rules.py``; the sign-in over HTTP is ``test_api/test_username_rules_api.py``.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` (so with the indexes of the
``User`` model, ``ux_users_email_lower`` included: the plan production runs), opened as production opens its own
(aiosqlite, NullPool, the PRAGMA listener of ``backend.app.db.session``), disposed at teardown; ``get_async_engine`` is a
tripwire. The accounts are rows with a marker hash, each lookup runs in a session of its own, and every name and address
carries a random tag of its own. Nothing here signs in.

Red until A-21a, each test on its own: ULOOK-001 (the squatter is found, not B) and ULOOK-005 (an identifier without an
``@`` finds the account whose address it is). ULOOK-002, 003 and 004 are GUARDS, green today and to stay green.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import User
from backend.app.services.accounts import user_service
from backend.test_scripts.test_utils import print_section, print_success

#: What makes an identifier an address first (rule 3).
AT = "@"
#: What the accounts written as rows hold for a hash: nobody signs in with them here.
MARKER_HASH = "$argon2id$username-lookup-marker"
SQUATTER_FIRST, OWNER_FIRST = "squatter-first", "owner-first"
#: The order the two rows of a scene are written in: the lookup must not depend on it.
ORDERS = [pytest.param(SQUATTER_FIRST, id=SQUATTER_FIRST), pytest.param(OWNER_FIRST, id=OWNER_FIRST)]


# =============================================================================
# NAMES AND ADDRESSES
# =============================================================================


def _tag() -> str:
    """Twelve random hex characters: time alone is not unique across workers."""
    return uuid.uuid4().hex[:12]


def _ascii_fold(text: str) -> str:
    """The fold of decision P18, written out: A–Z to a–z, every other character as it is."""
    return "".join(chr(ord(character) + 32) if "A" <= character <= "Z" else character for character in text)


def _as_written(text: str) -> str:
    return text


def _upper(text: str) -> str:
    return text.upper()


def _capitalized(address: str) -> str:
    local, _, domain = address.partition("@")
    return f"{local.capitalize()}@{domain.capitalize()}"


def _alternating(text: str) -> str:
    return "".join(character.upper() if position % 2 else character for position, character in enumerate(text))


Form = Callable[[str], str]

#: How the squatter's legacy name writes B's address: as B writes it, or in another A–Z case.
SQUATTER_FORMS = [
    pytest.param(_as_written, id="name-as-B-writes-it"),
    pytest.param(_upper, id="name-in-UPPER"),
    pytest.param(_capitalized, id="name-Capitalized"),
]
#: (how the squatter's name writes B's address, how B types it): never the same string, always the same address but for A–Z.
OTHER_FORMS = [
    pytest.param(_as_written, _upper, id="name-as-B-writes-it-typed-in-UPPER"),
    pytest.param(_upper, _as_written, id="name-in-UPPER-typed-as-B-writes-it"),
    pytest.param(_capitalized, _alternating, id="name-Capitalized-typed-aLtErNaTiNg"),
]


# =============================================================================
# FIXTURES
# =============================================================================


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's private one")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` of the session module raises: nothing here may open the lane's database."""
    monkeypatch.setattr(db_session, "get_async_engine", _lane_database_tripwire)


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema and its indexes (``create_all``); disposed at teardown."""
    private = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'username-lookup.db'}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield private
    finally:
        await private.dispose()


# =============================================================================
# HELPERS — the accounts as rows, and the lookup as its callers run it
# =============================================================================


async def _add_account(engine: AsyncEngine, *, username: str, email: str) -> int:
    """An account written as a row and committed in a session of its own — as an install before A-21a may hold it. Its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=MARKER_HASH)
        session.add(user)
        await session.commit()
        return user.id


async def _look_up(engine: AsyncEngine, identifier: str) -> Optional[int]:
    """The id of the account ``get_user_by_username_or_email(session, identifier)`` answers in a fresh session, or None."""
    async with AsyncSession(engine) as session:
        found = await user_service.get_user_by_username_or_email(session, identifier)
        return None if found is None else found.id


@dataclass(frozen=True)
class Squat:
    """B, who owns an address, and A, a legacy account named with that address in some A–Z case."""

    owner: int
    owner_email: str
    squatter: int
    squatter_name: str


async def _squat(engine: AsyncEngine, form: Form, order: str) -> Squat:
    """The scene of E's review: B owns ``bob.<tag>@example.com``; A is named with it as ``form`` writes it, A's own address elsewhere; the rows written in ``order``."""
    tag = _tag()
    owner_email = f"bob.{tag}@example.com"
    squatter_name = form(owner_email)
    assert AT in squatter_name and _ascii_fold(squatter_name) == _ascii_fold(owner_email), f"test bug: {squatter_name!r} is not B's address but for A–Z"
    owner = {"username": f"bob_{tag}", "email": owner_email}
    squatter = {"username": squatter_name, "email": f"alice.{tag}@example.org"}
    written = (squatter, owner) if order == SQUATTER_FIRST else (owner, squatter)
    ids = [await _add_account(engine, **account) for account in written]
    squatter_id, owner_id = ids if order == SQUATTER_FIRST else ids[::-1]
    return Squat(owner=owner_id, owner_email=owner_email, squatter=squatter_id, squatter_name=squatter_name)


# =============================================================================
# WITH AN @ — THE ADDRESS FIRST
# =============================================================================


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize("form", SQUATTER_FORMS)
async def test_an_address_finds_its_owner_before_a_legacy_name_written_like_it(engine: AsyncEngine, form: Form, order: str) -> None:
    """ULOOK-001 — rule 3, red until A-21a (today the squatter A is found: the username's index answers first, in either order of the rows): B owns ``bob.<tag>@example.com``; A, a legacy account, is named with that address — as B writes it, in UPPER, Capitalized —; the rows written squatter first or owner first. The identifier exactly as A's name is written — B's address in its own case, or in another A–Z case — finds B: an identifier with an ``@`` is an address first."""
    print_section("ULOOK-001: B's address, typed as A's legacy name is written, finds B")
    scene = await _squat(engine, form, order)

    found = await _look_up(engine, scene.squatter_name)

    assert found == scene.owner, f"red until A-21a: {scene.squatter_name!r} is the address of B (#{scene.owner}, A–Z case aside) and the legacy name of A (#{scene.squatter}): an identifier with an @ is an address first — found #{found}"
    print_success(f"{scene.squatter_name!r} finds B, not the squatter")


# GUARD — green today, must stay green
@pytest.mark.asyncio
@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize(("form", "typed_form"), OTHER_FORMS)
async def test_an_address_typed_unlike_the_legacy_name_finds_its_owner(engine: AsyncEngine, form: Form, typed_form: Form, order: str) -> None:
    """ULOOK-002 — rule 3, GUARD (green today, where only the address matches; red if A-21a stops folding the address, or lets a name match in another A–Z case): the scene of ULOOK-001; B's address typed in another A–Z case than A's name writes it finds B."""
    scene = await _squat(engine, form, order)
    typed = typed_form(scene.owner_email)
    assert typed != scene.squatter_name and _ascii_fold(typed) == _ascii_fold(scene.owner_email), f"test bug: {typed!r} must be B's address but for A–Z, and not A's name as written"

    assert await _look_up(engine, typed) == scene.owner, f"{typed!r} is B's address but for A–Z, and nobody's name as written: it must find B"


# GUARD — green today, must stay green
@pytest.mark.asyncio
@pytest.mark.parametrize("form", [pytest.param(_as_written, id="name-in-lower-case"), pytest.param(_capitalized, id="name-Capitalized")])
async def test_a_legacy_name_with_an_at_that_is_nobodys_address_is_found_by_its_exact_string(engine: AsyncEngine, form: Form) -> None:
    """ULOOK-003 — rule 3's fallback, GUARD (green today; red if A-21a drops the legacy names, or folds them): L, a legacy account named ``legacy.<tag>@example.net`` — nobody's address —, in lower case or Capitalized. Its exact name finds L: no account has that address, so the username answers, compared as written. The name in UPPER finds nobody: the fallback is exact."""
    name = form(f"legacy.{_tag()}@example.net")
    legacy = await _add_account(engine, username=name, email=f"own.{_tag()}@example.org")

    assert await _look_up(engine, name) == legacy, f"{name!r} is nobody's address and L's legacy name: L must be found by it"
    assert await _look_up(engine, name.upper()) is None, f"{name.upper()!r} is L's name in another A–Z case and nobody's address: the fallback is exact, it must find nobody"


# =============================================================================
# WITHOUT AN @ — A USERNAME ONLY, AS WRITTEN
# =============================================================================


# GUARD — green today, must stay green
@pytest.mark.asyncio
async def test_without_an_at_a_username_is_compared_exactly(engine: AsyncEngine) -> None:
    """ULOOK-004 — rule 3, GUARD (green today; red if A-21a folds usernames — A-21b's to decide): ``carol_<tag>`` is found by its exact name; ``CAROL_<TAG>`` and ``Carol_<tag>`` find nobody."""
    name = f"carol_{_tag()}"
    carol = await _add_account(engine, username=name, email=f"carol.{_tag()}@example.com")

    assert await _look_up(engine, name) == carol, f"{name!r} is Carol's username: it must find her"
    assert {typed: await _look_up(engine, typed) for typed in (name.upper(), name.capitalize())} == {name.upper(): None, name.capitalize(): None}, "without an @ the username is compared as written: another A–Z case finds nobody"


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("typed_form", [pytest.param(_as_written, id="typed-as-stored"), pytest.param(_upper, id="typed-in-UPPER")])
async def test_without_an_at_an_identifier_never_finds_an_address(engine: AsyncEngine, typed_form: Form) -> None:
    """ULOOK-005 — rule 3, red until A-21a (today the address half answers: X is found): X, a legacy account whose address has no ``@`` — ``mailbox<tag>``, stored unchecked by ``user create`` —, and no account named so. ``mailbox<tag>``, as stored or in UPPER, finds nobody: an identifier without an ``@`` is a username only. Barrier: X is found by its username."""
    tag = _tag()
    mailbox = f"mailbox{tag}"
    username = f"x_{tag}"
    x = await _add_account(engine, username=username, email=mailbox)
    assert await _look_up(engine, username) == x, "barrier: X is found by its username, so a None below is about the address"

    typed = typed_form(mailbox)
    found = await _look_up(engine, typed)

    assert found is None, f"red until A-21a: {typed!r} has no @ and is nobody's username: it must find nobody, not the account whose address it is (#{found})"
