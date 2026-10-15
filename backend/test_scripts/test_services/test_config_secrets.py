"""
Secrets given as ``NAME`` or as ``NAME_FILE`` (workstream H, platform, checkpoint CP3).

Under test: the «Secrets» section of ``backend/app/config/__init__.py`` (``env_secret``, ``env_secret_origin``,
``read_secret_file``, ``secrets_set_twice``, ``INSTANCE_TRUST_SECRETS``) and the accessors built on it in
``backend/app/config/platform.py``: ``configured_jwt_secret``, ``configured_instance_key`` and their ``*_origin``.

Docker and Kubernetes hand a secret to a container as a mounted file, which ``docker inspect`` and
``/proc/<pid>/environ`` do not show. So every secret of LibreFolio is read from ``NAME`` or, when ``NAME`` is unset, from
the file named by ``NAME_FILE``. The contract:

(a) Precedence. A ``NAME`` that is not blank is the secret exactly as written, spaces included, and wins over
    ``NAME_FILE``, which is then not even opened. An empty or blank ``NAME`` counts as unset and falls through to the
    file, so a stray space never becomes a key; an empty or blank ``NAME_FILE`` is no file.
(b) The file. The secret is its text without a leading UTF-8 byte order mark and without its trailing line breaks: only
    the BOM at the very start and the ``\\r`` and ``\\n`` at the very end are dropped, so what an editor or an ``echo``
    adds never becomes part of the key while every other character stays. A relative path starts from the project
    folder, never from the working directory; ``~`` is the home folder.
(c) The errors. A file that cannot give its secret (missing, a directory, unreadable, larger than 64 KiB, not UTF-8,
    empty or blank) raises ``SecretFileError`` naming the variable and the path, never the content: the message reaches
    the startup log, so a secret in it would be a leak.
(d) The origin. ``env_secret_origin`` names where ``env_secret`` takes the secret from, for messages: ``NAME``, or
    ``NAME_FILE (<resolved path>)``, or ``None``. It never opens the file and never holds the value.
(e) ``secrets_set_twice`` lists, sorted, the secrets of LibreFolio (``JWT_SECRET`` and any ``LIBREFOLIO_*``) set both
    ways, for the configuration audit; the pairs of other software (``SSL_CERT_FILE``) and empty or blank values are no
    concern.
(f) The accessors of the platform section follow (a)-(d) for their own variables.
(g) ``INSTANCE_TRUST_SECRETS`` lists the secrets a test lane never inherits, since a test lane signs sessions and derives
    keys with secrets of its own, never with the instance's: the session signing key and the instance key, both forms.

Pure: no database, no server, no network. Every variable the code reads is set or removed through ``monkeypatch``, every
file lives in ``tmp_path``, and nothing is written in the repository.
"""

from __future__ import annotations

import os
import traceback
from collections.abc import Callable
from pathlib import Path

import pytest

import backend.app.config as config
from backend.app.config import (
    INSTANCE_TRUST_SECRETS,
    SECRET_FILE_MAX_BYTES,
    SECRET_FILE_SUFFIX,
    SecretFileError,
    env_secret,
    env_secret_origin,
    read_secret_file,
    secrets_set_twice,
)
from backend.app.config.platform import configured_instance_key, configured_instance_key_origin, configured_jwt_secret, configured_jwt_secret_origin
from backend.test_scripts.test_utils import print_section, print_success

#: A secret no application code reads: the generic behaviour of ``env_secret`` is tested on it.
PROBE = "LIBREFOLIO_PROBE_SECRET"
PROBE_FILE = PROBE + SECRET_FILE_SUFFIX

#: Recognisable secret content: an error message or a traceback that leaks the secret would show it.
CANARY = "c4nary-S3CRET-must-never-reach-a-message"

#: Markers of the parametrized cases that need a file built in ``tmp_path``.
VALID_FILE = "<a readable secret file>"
MISSING_FILE = "<a path where no file exists>"
DIRECTORY = "<a directory instead of a file>"

#: Markers of the origin ``env_secret_origin`` must name: the variable itself, or the file variable with its path.
BY_NAME = "<NAME>"
BY_FILE = "<NAME_FILE (path)>"

UTF8_BOM = b"\xef\xbb\xbf"


def _is_secret_file_variable(variable: str) -> bool:
    """The ``NAME_FILE`` variables ``secrets_set_twice`` looks at: those of ``JWT_SECRET`` and of ``LIBREFOLIO_*``."""
    return variable.endswith(SECRET_FILE_SUFFIX) and (variable == "JWT_SECRET_FILE" or variable.startswith("LIBREFOLIO_"))


@pytest.fixture(autouse=True)
def no_secret_in_the_environment(monkeypatch):
    """Every test starts with no secret set either way, whatever the shell or the test runner exported."""
    for variable in [name for name in os.environ if _is_secret_file_variable(name)]:
        monkeypatch.delenv(variable)
    for variable in ("JWT_SECRET", "LIBREFOLIO_INSTANCE_KEY", PROBE):
        monkeypatch.delenv(variable, raising=False)


def _set_variable(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    """``None`` unsets ``name``; any string, the empty one included, sets it."""
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _secret_file(tmp_path: Path, content: bytes, name: str = "secret") -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


# =============================================================================
# (a) Precedence, (d) the origin
# =============================================================================


@pytest.mark.parametrize(
    ("name_value", "file_value", "expected", "origin"),
    [
        pytest.param(None, None, None, None, id="neither-set"),
        pytest.param("", None, None, None, id="empty-name-is-unset"),
        pytest.param("   ", None, None, None, id="blank-name-is-unset"),
        pytest.param(" \t\n ", None, None, None, id="whitespace-name-is-unset"),
        pytest.param(None, "", None, None, id="empty-file-variable-is-no-file"),
        pytest.param(None, "   ", None, None, id="blank-file-variable-is-no-file"),
        pytest.param("", "", None, None, id="both-empty"),
        pytest.param("  ", "  ", None, None, id="both-blank"),
        pytest.param("from-the-variable", None, "from-the-variable", BY_NAME, id="name-only"),
        pytest.param("  spaced out  ", None, "  spaced out  ", BY_NAME, id="name-kept-as-written-spaces-included"),
        pytest.param("from-the-variable", VALID_FILE, "from-the-variable", BY_NAME, id="name-wins-over-the-file"),
        pytest.param("from-the-variable", MISSING_FILE, "from-the-variable", BY_NAME, id="name-wins-the-file-is-not-opened"),
        pytest.param("", VALID_FILE, "from-the-file", BY_FILE, id="empty-name-falls-through-to-the-file"),
        pytest.param("   ", VALID_FILE, "from-the-file", BY_FILE, id="blank-name-falls-through-to-the-file"),
        pytest.param(None, VALID_FILE, "from-the-file", BY_FILE, id="file-only"),
    ],
)
def test_env_secret_takes_the_variable_first_then_the_file(monkeypatch, tmp_path, name_value, file_value, expected, origin):
    """(a)(d) A NAME that is not blank wins and the file is not opened; an empty or blank NAME falls through to NAME_FILE; an
    empty or blank NAME_FILE is none. ``env_secret_origin`` names the source ``env_secret`` reads, never the value."""
    if file_value == VALID_FILE:
        file_value = str(_secret_file(tmp_path, b"from-the-file\n"))
    elif file_value == MISSING_FILE:
        file_value = str(tmp_path / "no-such-secret")
    _set_variable(monkeypatch, PROBE, name_value)
    _set_variable(monkeypatch, PROBE_FILE, file_value)

    secret, named = env_secret(PROBE), env_secret_origin(PROBE)

    assert secret == expected, f"{PROBE}={name_value!r} and {PROBE_FILE}={file_value!r} must give {expected!r}, env_secret gave {secret!r}"
    expected_origin = {None: None, BY_NAME: PROBE, BY_FILE: f"{PROBE_FILE} ({file_value})"}[origin]
    assert named == expected_origin, f"{PROBE}={name_value!r} and {PROBE_FILE}={file_value!r}: env_secret_origin must be {expected_origin!r}, not {named!r}"
    print_success(f"{PROBE}={name_value!r}, {PROBE_FILE}={file_value!r}: {secret!r} from {named!r}")


# =============================================================================
# (b) The file
# =============================================================================


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        pytest.param(b"s3cret", "s3cret", id="no-line-break"),
        pytest.param(b"s3cret\n", "s3cret", id="trailing-lf-dropped"),
        pytest.param(b"s3cret\r\n", "s3cret", id="trailing-crlf-dropped"),
        pytest.param(b"s3cret\n\r\n\n", "s3cret", id="several-trailing-line-breaks-dropped"),
        pytest.param(UTF8_BOM + b"my-secret\r\n", "my-secret", id="leading-utf8-bom-dropped"),
        pytest.param(b"my-" + UTF8_BOM + b"secret\n", "my-\ufeffsecret", id="inner-bom-kept"),
        pytest.param(b"  s3cret  \n", "  s3cret  ", id="spaces-kept"),
        pytest.param(b"\ts3cret\t\n", "\ts3cret\t", id="tabs-kept"),
        pytest.param(b"\ns3cret\n", "\ns3cret", id="leading-line-break-kept"),
        pytest.param(b"line one\nline two\n", "line one\nline two", id="inner-line-break-kept"),
        pytest.param(b"s3cret\n ", "s3cret\n ", id="line-break-followed-by-a-space-kept"),
        pytest.param("pässwörd-ключ\n".encode(), "pässwörd-ключ", id="utf8-text"),
    ],
)
def test_the_secret_is_the_file_text_without_a_leading_bom_and_its_trailing_line_breaks(monkeypatch, tmp_path, content, expected):
    """(b) Only a BOM at the very start and the CR and LF at the very end are dropped: every other character is part of the secret."""
    monkeypatch.setenv(PROBE_FILE, str(_secret_file(tmp_path, content)))

    secret = env_secret(PROBE)

    assert secret == expected, f"a secret file holding {content!r} must give {expected!r}, env_secret gave {secret!r}"
    print_success(f"{content!r} → {secret!r}")


def test_a_secret_file_may_hold_64_KiB_and_not_one_byte_more(monkeypatch, tmp_path):
    """(b)(c) The limit counts the bytes of the file, before the trailing line breaks are dropped."""
    print_section("Secrets: the 64 KiB limit")
    assert SECRET_FILE_MAX_BYTES == 64 * 1024, f"the limit of a secret file is 64 KiB, not {SECRET_FILE_MAX_BYTES} bytes"
    largest = b"k" * SECRET_FILE_MAX_BYTES
    monkeypatch.setenv(PROBE_FILE, str(_secret_file(tmp_path, largest)))
    assert env_secret(PROBE) == largest.decode(), f"a secret file of exactly {SECRET_FILE_MAX_BYTES} bytes must be accepted whole"

    monkeypatch.setenv(PROBE_FILE, str(_secret_file(tmp_path, largest + b"\n", name="one-byte-more")))
    with pytest.raises(SecretFileError, match=f"is larger than {SECRET_FILE_MAX_BYTES} bytes"):
        env_secret(PROBE)
    print_success(f"{SECRET_FILE_MAX_BYTES} bytes accepted, {SECRET_FILE_MAX_BYTES + 1} refused even when the extra byte is a line break")


def test_a_relative_secret_path_starts_from_the_project_folder(monkeypatch, tmp_path):
    """(b)(d) A relative NAME_FILE is resolved from the project folder: the working directory of the server does not matter."""
    print_section("Secrets: a relative NAME_FILE")
    project, working_directory = tmp_path / "project", tmp_path / "working-directory"
    relative = Path("run") / "secrets" / "probe"
    for root, content in ((project, b"from-the-project-folder\n"), (working_directory, b"from-the-working-directory\n")):
        (root / relative).parent.mkdir(parents=True)
        (root / relative).write_bytes(content)
    monkeypatch.setattr(config, "PROJECT_ROOT", project)
    monkeypatch.chdir(working_directory)

    monkeypatch.setenv(PROBE_FILE, relative.as_posix())
    secret = env_secret(PROBE)
    assert secret == "from-the-project-folder", f"{PROBE_FILE}={relative.as_posix()} must be read from the project folder, env_secret gave {secret!r}"
    assert env_secret_origin(PROBE) == f"{PROBE_FILE} ({project / relative})", f"the origin must name the path the file was read from: {env_secret_origin(PROBE)!r}"

    missing = Path("run") / "secrets" / "missing"
    monkeypatch.setenv(PROBE_FILE, missing.as_posix())
    with pytest.raises(SecretFileError) as raised:
        env_secret(PROBE)
    assert str(raised.value) == f"{PROBE_FILE}: {project / missing} does not exist", f"the error must name the path where the file was looked for: {raised.value}"
    print_success(f"{relative.as_posix()} read from the project folder; a missing one named as {project / missing}")


def test_a_secret_path_may_start_from_the_home_folder(monkeypatch, tmp_path):
    """(b)(d) ``~`` in NAME_FILE is the home folder of the user running the server."""
    home = tmp_path / "home"
    (home / ".secrets").mkdir(parents=True)
    (home / ".secrets" / "probe").write_bytes(b"from-the-home-folder\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # what expanduser reads on Windows
    monkeypatch.setenv(PROBE_FILE, "~/.secrets/probe")

    secret = env_secret(PROBE)

    assert secret == "from-the-home-folder", f"{PROBE_FILE}=~/.secrets/probe must be read from the home folder, env_secret gave {secret!r}"
    assert env_secret_origin(PROBE) == f"{PROBE_FILE} ({home / '.secrets' / 'probe'})", f"the origin must name the expanded path: {env_secret_origin(PROBE)!r}"
    print_success("~/.secrets/probe read from the home folder")


# =============================================================================
# (c) The errors
# =============================================================================


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        pytest.param(MISSING_FILE, "does not exist", id="missing"),
        pytest.param(DIRECTORY, "cannot be read (", id="a-directory"),
        pytest.param(b"", "is empty or blank", id="empty"),
        pytest.param(b"\r\n\n", "is empty or blank", id="line-breaks-only"),
        pytest.param(b"   \n", "is empty or blank", id="spaces-only"),
        pytest.param(b"\t\n", "is empty or blank", id="tab-only"),
        pytest.param(b"\n   ", "is empty or blank", id="line-break-and-spaces"),
        pytest.param(UTF8_BOM + b"\n", "is empty or blank", id="bom-only"),
        pytest.param(CANARY.encode() + b"\xff\xfe", "is not UTF-8 text", id="not-utf8"),
        pytest.param((CANARY * (SECRET_FILE_MAX_BYTES // len(CANARY) + 1)).encode()[: SECRET_FILE_MAX_BYTES + 1], f"is larger than {SECRET_FILE_MAX_BYTES} bytes", id="larger-than-64-KiB"),
    ],
)
def test_a_file_that_cannot_give_its_secret_names_the_variable_and_the_path_never_the_content(monkeypatch, tmp_path, content, problem):
    """(c)(d) SecretFileError says which variable, which path and what is wrong, and shows no content; the origin is still named."""
    path = tmp_path / "secret"
    if content == DIRECTORY:
        path.mkdir()
    elif content != MISSING_FILE:
        path.write_bytes(content)
    monkeypatch.setenv(PROBE_FILE, str(path))

    with pytest.raises(SecretFileError) as raised:
        env_secret(PROBE)
    message = str(raised.value)
    assert message.startswith(f"{PROBE_FILE}: {path} "), f"the message must start with the variable and the path: {message!r}"
    assert problem in message, f"the message must say what is wrong ({problem!r}): {message!r}"
    rendered = "".join(traceback.format_exception(raised.value))
    assert CANARY not in rendered, f"the error or its traceback shows the content of the secret file:\n{rendered[:2000]}"
    assert env_secret_origin(PROBE) == f"{PROBE_FILE} ({path})", f"the origin of a file that cannot be read is named all the same, without opening it: {env_secret_origin(PROBE)!r}"

    with pytest.raises(SecretFileError) as direct:
        read_secret_file(path, "the label of the source")
    assert str(direct.value).startswith(f"the label of the source: {path} "), f"read_secret_file must name its source with the label it is given: {direct.value}"
    print_success(f"{problem}: {message}")


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="needs POSIX permissions, which root bypasses")
def test_an_unreadable_secret_file_names_the_variable_and_the_path_never_the_content(monkeypatch, tmp_path):
    """(c) A file the server may not read: ``cannot be read`` with the reason the system gives."""
    path = _secret_file(tmp_path, CANARY.encode())
    monkeypatch.setenv(PROBE_FILE, str(path))
    path.chmod(0)
    try:
        with pytest.raises(SecretFileError) as raised:
            env_secret(PROBE)
    finally:
        path.chmod(0o600)
    message = str(raised.value)
    assert message.startswith(f"{PROBE_FILE}: {path} cannot be read ("), f"an unreadable file must be reported as such, with its variable and path: {message!r}"
    assert CANARY not in message, f"the message shows the content of the secret file: {message!r}"
    print_success(message)


# =============================================================================
# (e) Secrets set twice
# =============================================================================


@pytest.mark.parametrize(
    ("variables", "expected"),
    [
        pytest.param({}, [], id="nothing-set"),
        pytest.param({"JWT_SECRET": "x"}, [], id="name-only"),
        pytest.param({"JWT_SECRET_FILE": "/run/secrets/jwt"}, [], id="file-only"),
        pytest.param({"JWT_SECRET": "x", "JWT_SECRET_FILE": "/run/secrets/jwt"}, ["JWT_SECRET"], id="jwt-secret-both-ways"),
        pytest.param({"JWT_SECRET": "", "JWT_SECRET_FILE": "/run/secrets/jwt"}, [], id="empty-name-is-not-set"),
        pytest.param({"JWT_SECRET": "   ", "JWT_SECRET_FILE": "/run/secrets/jwt"}, [], id="blank-name-is-not-set"),
        pytest.param({"JWT_SECRET": "x", "JWT_SECRET_FILE": ""}, [], id="empty-file-variable-is-not-set"),
        pytest.param({"JWT_SECRET": "x", "JWT_SECRET_FILE": "   "}, [], id="blank-file-variable-is-not-set"),
        pytest.param(
            {"LIBREFOLIO_INSTANCE_KEY": "k", "LIBREFOLIO_INSTANCE_KEY_FILE": "/run/secrets/key", "JWT_SECRET": "x", "JWT_SECRET_FILE": "/run/secrets/jwt"},
            ["JWT_SECRET", "LIBREFOLIO_INSTANCE_KEY"],
            id="sorted",
        ),
        pytest.param({"LIBREFOLIO_FUTURE_TOKEN": "t", "LIBREFOLIO_FUTURE_TOKEN_FILE": "/run/secrets/token"}, ["LIBREFOLIO_FUTURE_TOKEN"], id="any-librefolio-secret-without-a-list"),
        pytest.param({"SSL_CERT": "c", "SSL_CERT_FILE": "/etc/ssl/cert.pem", "MYSQL_PASSWORD": "p", "MYSQL_PASSWORD_FILE": "/run/secrets/db"}, [], id="other-software-ignored"),
        pytest.param({"JWT_SECRET": "x", "JWT_SECRET_FILE": "/no/such/file"}, ["JWT_SECRET"], id="the-file-is-not-opened"),
    ],
)
def test_secrets_set_twice_lists_the_librefolio_secrets_set_both_ways(monkeypatch, variables, expected):
    """(e) NAME and NAME_FILE neither empty nor blank, NAME being JWT_SECRET or LIBREFOLIO_*: listed sorted; nothing else."""
    for name, value in variables.items():
        monkeypatch.setenv(name, value)

    found = secrets_set_twice()

    assert found == expected, f"with {variables} secrets_set_twice() must be {expected}, not {found}"
    print_success(f"{sorted(variables)} → {found}")


# =============================================================================
# (f) The accessors of the platform section
# =============================================================================

ACCESSORS = [
    pytest.param(configured_jwt_secret, configured_jwt_secret_origin, "JWT_SECRET", id="configured_jwt_secret"),
    pytest.param(configured_instance_key, configured_instance_key_origin, "LIBREFOLIO_INSTANCE_KEY", id="configured_instance_key"),
]


@pytest.mark.parametrize(("accessor", "origin", "variable"), ACCESSORS)
def test_an_accessor_reads_its_variable_or_else_its_file(monkeypatch, tmp_path, accessor: Callable[[], str | None], origin: Callable[[], str | None], variable):
    """(f) None without either, a blank variable included; the file's text without its line break; the variable, when not blank, over the file."""
    print_section(f"Secrets: {accessor.__name__}")
    assert (accessor(), origin()) == (None, None), f"{accessor.__name__}() and {origin.__name__}() must be None when neither {variable} nor {variable}_FILE is set"
    monkeypatch.setenv(variable, "   ")
    assert (accessor(), origin()) == (None, None), f"a blank {variable} must count as unset for {accessor.__name__}() and {origin.__name__}()"

    mounted = _secret_file(tmp_path, b"from-a-mounted-secret\n")
    monkeypatch.setenv(variable + SECRET_FILE_SUFFIX, str(mounted))
    assert accessor() == "from-a-mounted-secret", f"{accessor.__name__}() must read {variable}_FILE when {variable} is blank"
    assert origin() == f"{variable}_FILE ({mounted})", f"{origin.__name__}() must name {variable}_FILE and its path: {origin()!r}"

    monkeypatch.setenv(variable, "from-the-variable")
    assert (accessor(), origin()) == ("from-the-variable", variable), f"{accessor.__name__}() must prefer {variable} to {variable}_FILE, and {origin.__name__}() say so"
    print_success(f"{accessor.__name__}: None, then {variable}_FILE, then {variable} over it; {origin.__name__} follows")


@pytest.mark.parametrize(("accessor", "origin", "variable"), ACCESSORS)
def test_an_accessor_raises_on_a_file_that_cannot_give_its_secret(monkeypatch, tmp_path, accessor: Callable[[], str | None], origin: Callable[[], str | None], variable):
    """(f) A broken NAME_FILE is an error naming that variable, never a silent None; its origin is named without opening it."""
    missing = tmp_path / "missing"
    monkeypatch.setenv(variable + SECRET_FILE_SUFFIX, str(missing))

    with pytest.raises(SecretFileError) as raised:
        accessor()

    assert str(raised.value) == f"{variable}_FILE: {missing} does not exist", f"{accessor.__name__}() must name {variable}_FILE and the path: {raised.value}"
    assert origin() == f"{variable}_FILE ({missing})", f"{origin.__name__}() must name the file the secret should come from: {origin()!r}"
    print_success(f"{accessor.__name__}: {raised.value}")


# =============================================================================
# (g) The secrets a test lane never inherits
# =============================================================================


def test_the_secrets_a_test_lane_never_inherits_are_the_signing_key_and_the_instance_key_in_both_forms():
    """(g) A test lane signs sessions and derives keys with secrets of its own, never with the instance's: both forms of each."""
    names = set(INSTANCE_TRUST_SECRETS)
    assert len(names) == len(INSTANCE_TRUST_SECRETS), f"INSTANCE_TRUST_SECRETS lists a name twice: {INSTANCE_TRUST_SECRETS}"
    assert {"JWT_SECRET", "LIBREFOLIO_INSTANCE_KEY"} <= names, f"INSTANCE_TRUST_SECRETS must list the session signing key and the instance key: {INSTANCE_TRUST_SECRETS}"
    pairs = {name: name.removesuffix(SECRET_FILE_SUFFIX) if name.endswith(SECRET_FILE_SUFFIX) else name + SECRET_FILE_SUFFIX for name in names}
    unpaired = sorted(name for name, other in pairs.items() if other not in names)
    assert not unpaired, f"INSTANCE_TRUST_SECRETS must list each secret as NAME and as NAME_FILE, or the other form still reaches a test lane: {unpaired} lack their pair"
    print_success(f"{sorted(names)}")
