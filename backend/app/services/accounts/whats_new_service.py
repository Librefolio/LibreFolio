"""What's new since the user's last version (C-54): the release whose changelog each account saw last.

The backend says whether there is anything new for a user, and from which release (``pending_for``, the
``user.whats_new`` of the login and ``/auth/me``); the app holds the changelog and picks its chapters
(``frontend/src/lib/features/changelog/whatsNew.ts``). ``users.last_seen_version`` holds a base release ``X.Y.Z``:
written when the account is created (a new account has nothing to catch up on) and when the user closes the modal
(``mark_seen``). ``NULL`` is an account from before the feature: it sees the running release's chapter, once.

``LIBREFOLIO_DISABLE_WHATS_NEW`` (a hidden switch, as the donation popup's, decision D-A7) turns it off: ``dev.py
server --test`` sets it on every test lane, whose accounts were created before the feature.
"""

import re
from dataclasses import dataclass
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import config
from backend.app.config.accounts import whats_new_disabled as _whats_new_disabled
from backend.app.db.models import User

logger = structlog.get_logger(__name__)

#: A version string down to its base release: ``v1.2.1``, ``1.3``, ``1.3.0-rc1``, ``v1.2.1-2106-gcd52e25fc-dirty`` (``git
#: describe``). Major and minor are required, so a bare commit hash (``--always`` without a tag) is not a release.
_RELEASE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class WhatsNew:
    """Something new for a user: the chapters after ``since`` up to ``release``; ``since`` None for an account from
    before the feature, which sees the ``release`` chapter only."""

    since: Optional[str]
    release: str


def release_of(version: Optional[str]) -> Optional[str]:
    """The base release ``X.Y.Z`` of an app version, or None when the string names no release."""
    if not version:
        return None
    match = _RELEASE.match(version.strip())
    if match is None:
        return None
    major, minor, patch = match.groups()
    release = (int(major), int(minor), int(patch or 0))
    # `get_git_version()` reports a checkout with no tag as `v0.0.0-g<hash>`: that is no release, or the accounts created
    # there would see the whole changelog at the first real one
    if release == (0, 0, 0):
        return None
    return "{}.{}.{}".format(*release)


def current_release() -> Optional[str]:
    """The release the app runs: the base of ``config.get_version()``, read at each call; None when it names none."""
    return release_of(config.get_version())


def whats_new_disabled() -> bool:
    """``LIBREFOLIO_DISABLE_WHATS_NEW``: ``1``, ``true`` or ``yes``, in any case, turns the «What's new» modal off."""
    return _whats_new_disabled()


def _key(release: str) -> tuple[int, int, int]:
    major, minor, patch = (int(part) for part in release.split("."))
    return major, minor, patch


def pending_for(user: User) -> Optional[WhatsNew]:
    """What is new for ``user`` since the release it saw last, or None: switched off, the running release unknown, or
    nothing newer than what it saw (a downgrade included)."""
    if whats_new_disabled():
        return None
    release = current_release()
    if release is None:
        return None
    seen = release_of(user.last_seen_version)
    if seen is not None and _key(seen) >= _key(release):
        return None
    return WhatsNew(since=seen, release=release)


async def mark_seen(session: AsyncSession, user: User) -> Optional[str]:
    """The user closed the modal: the running release becomes the last one it saw (never a version from the client).

    Commits when it changes something; idempotent. Returns the release written, or None when the running one is
    unknown (nothing written).
    """
    release = current_release()
    if release is None:
        return None
    if user.last_seen_version != release:
        user_id = user.id
        user.last_seen_version = release
        session.add(user)
        await session.commit()
        logger.info("What's new seen", user_id=user_id, release=release)
    return release
