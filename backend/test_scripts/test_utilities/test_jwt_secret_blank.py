r"""A blank ``JWT_SECRET`` never becomes the key that signs session cookies (``backend/app/services/accounts/auth_service.py``).

The signing key is read once, when the module is imported, from the ``JWT_SECRET`` environment variable
(``configured_jwt_secret``, ``backend/app/config/platform.py``):

* a value made only of whitespace (``"   "``, ``"\t \n"``, ``" "``) counts as unset: the module signs with
  a random key of at least 64 URL-safe characters, new in every process, never with the blank value; a
  token signed with the blank value (HS256, ``sub``, ``iat``, ``exp`` in the future) is refused by
  ``decode_jwt_token`` (``None``). ``docker run --env-file`` hands a line ``JWT_SECRET=   `` to the
  process exactly as it is written;
* any other value is the key exactly as it is written, surrounding spaces included, so the sessions of
  an installation that already has a secret survive the upgrade: a token signed with that exact value
  decodes to its user id (``SessionClaims.user_id``);
* an unset or empty ``JWT_SECRET`` gives a random key too.

Because the key is computed at import, every case imports the module in a fresh interpreter, run in
``tmp_path``, whose environment is this one's without ``JWT_SECRET`` and ``JWT_SECRET_FILE`` (read when
``JWT_SECRET`` is blank, so a developer's file cannot leak into a case), plus the case's value. The child
reports the key it got (``_JWT_SECRET``) and the user id ``decode_jwt_token`` read from a token signed with
the case's value; each refusal is first proven not vacuous, the child checking that the token is valid under
the key it was signed with. No DB, no server, no network.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

USER_ID = 4242

#: Values made only of whitespace: each counts as unset.
BLANK_SECRETS = {"spaces": "   ", "tab-space-newline": "\t \n", "one-space": " "}

#: Values with something besides whitespace: each is the key exactly as written.
REAL_SECRET = "c0ffee-5e55i0n-k3y-0f-an-1n5tallat10n-that-already-had-0ne-set-up"
NON_BLANK_SECRETS = {"plain": REAL_SECRET, "surrounded-by-spaces": f"  {REAL_SECRET}  "}

#: No value at all: the module has always drawn a random key for these.
UNSET_SECRETS = {"unset": None, "empty": ""}

#: What ``secrets.token_urlsafe`` produces.
URL_SAFE = re.compile(r"[A-Za-z0-9_-]+")

RESULT_MARKER = "JWT-SECRET-PROBE "

#: Where the key may come from (``env_secret("JWT_SECRET")``): none is inherited by a probe.
JWT_SECRET_SOURCES = ("JWT_SECRET", "JWT_SECRET_FILE")

#: Runs in the child. argv[1] is the JSON pair [key the token is signed with or null, user id].
PROBE = """
import json, sys, warnings
from datetime import UTC, datetime, timedelta

warnings.simplefilter("ignore")  # PyJWT warns about short HMAC keys, and the blank ones are short on purpose

import jwt

from backend.app.services.accounts import auth_service

signing_key, user_id = json.loads(sys.argv[1])
result = {"key": auth_service._JWT_SECRET, "token_valid_under_its_key": None, "decoded": None}
if signing_key is not None:
    now = datetime.now(UTC)
    token = jwt.encode({"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=1)}, signing_key, algorithm="HS256")
    result["token_valid_under_its_key"] = jwt.decode(token, signing_key, algorithms=["HS256"])["sub"] == str(user_id)
    claims = auth_service.decode_jwt_token(token)
    result["decoded"] = None if claims is None else claims.user_id
print("RESULT_MARKER" + json.dumps(result))
""".replace("RESULT_MARKER", RESULT_MARKER)


@dataclass(frozen=True)
class Probe:
    """What one fresh interpreter saw."""

    key: str  # auth_service._JWT_SECRET
    token_valid_under_its_key: bool | None  # the token is well formed; None when no token was signed
    decoded: int | None  # decode_jwt_token(token).user_id; None when refused


ProbeRunner = Callable[..., Probe]


@pytest.fixture(scope="module")
def probe(tmp_path_factory: pytest.TempPathFactory) -> ProbeRunner:
    """Import ``auth_service`` in a fresh interpreter with ``JWT_SECRET=env_value`` (``None``: unset).

    When ``signing_key`` is given, a token for ``USER_ID`` signed with it is handed to
    ``decode_jwt_token``. Results are kept per arguments; ``process`` asks for another interpreter.
    """
    workdir = tmp_path_factory.mktemp("jwt-secret-probe")
    results: dict[tuple[str | None, str | None, int], Probe] = {}

    def run(env_value: str | None, signing_key: str | None, process: int = 0) -> Probe:
        case = (env_value, signing_key, process)
        if case not in results:
            env = {name: value for name, value in os.environ.items() if name not in JWT_SECRET_SOURCES}
            if env_value is not None:
                env["JWT_SECRET"] = env_value
            env["PYTHONPATH"] = os.pathsep.join(part for part in (str(REPO_ROOT), os.environ.get("PYTHONPATH")) if part)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            done = subprocess.run(
                [sys.executable, "-c", PROBE, json.dumps([signing_key, USER_ID])],
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            assert done.returncode == 0, f"the probe failed with JWT_SECRET={env_value!r}:\n{done.stderr}"
            lines = [line for line in done.stdout.splitlines() if line.startswith(RESULT_MARKER)]
            assert len(lines) == 1, f"the probe printed no result with JWT_SECRET={env_value!r}:\n{done.stdout}"
            results[case] = Probe(**json.loads(lines[0].removeprefix(RESULT_MARKER)))
        return results[case]

    return run


def _assert_random_key(key: str, env_value: str | None) -> None:
    assert key != env_value, f"JWT_SECRET={env_value!r} became the signing key"
    assert len(key) >= 64, f"with JWT_SECRET={env_value!r} the signing key is {len(key)} characters long"
    assert URL_SAFE.fullmatch(key), f"with JWT_SECRET={env_value!r} the signing key is not URL-safe: {key!r}"


# ---------------------------------------------------------------------------
# A blank JWT_SECRET counts as unset
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("blank", BLANK_SECRETS.values(), ids=list(BLANK_SECRETS))
def test_a_blank_secret_is_replaced_by_a_random_key(probe: ProbeRunner, blank: str) -> None:
    _assert_random_key(probe(blank, blank).key, blank)


@pytest.mark.parametrize("blank", BLANK_SECRETS.values(), ids=list(BLANK_SECRETS))
def test_a_token_signed_with_a_blank_secret_is_refused(probe: ProbeRunner, blank: str) -> None:
    result = probe(blank, blank)
    # The token is well formed and in date: only the key can refuse it.
    assert result.token_valid_under_its_key is True

    assert result.decoded is None, f"with JWT_SECRET={blank!r}, a token signed with {blank!r} was accepted as user {result.decoded}"


@pytest.mark.parametrize("value", [*BLANK_SECRETS.values(), *UNSET_SECRETS.values()], ids=[*BLANK_SECRETS, *UNSET_SECRETS])
def test_the_random_key_is_new_in_every_process(probe: ProbeRunner, value: str | None) -> None:
    # PyJWT refuses an empty HMAC key, so no token is signed for an unset or empty value.
    signing_key = value or None
    first, second = probe(value, signing_key, process=0), probe(value, signing_key, process=1)

    assert first.key != second.key, f"with JWT_SECRET={value!r} two processes signed with the same key {first.key!r}"


# ---------------------------------------------------------------------------
# Guards: a real secret is kept as written, an unset one is still random
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("secret", NON_BLANK_SECRETS.values(), ids=list(NON_BLANK_SECRETS))
def test_a_non_blank_secret_is_the_key_exactly_as_written(probe: ProbeRunner, secret: str) -> None:
    result = probe(secret, secret)

    assert result.key == secret, f"JWT_SECRET={secret!r} became the signing key {result.key!r}"
    assert result.token_valid_under_its_key is True
    assert result.decoded == USER_ID, f"a token signed with JWT_SECRET={secret!r} itself was refused"


@pytest.mark.parametrize("value", UNSET_SECRETS.values(), ids=list(UNSET_SECRETS))
def test_an_unset_or_empty_secret_gives_a_random_key(probe: ProbeRunner, value: str | None) -> None:
    _assert_random_key(probe(value, None).key, value)
