"""``instance_backup/secure.py``: the rules of an archive's password, and the instance key a secure archive may carry
(release 1.3, workstream B, lot B4: decisions 38 and 39, P12).

Under test: ``backend/app/services/platform/instance_backup/secure.py``, new in B4, built on A's
``services/accounts/password_policy.py`` (the rules, with the ``rules=`` and ``rules_with_minimum_length`` that B4 adds
to it) and on H's ``services/platform/instance_key.py`` (``instance_key_status``). The frozen contract,
``b4-test-brief.md`` §2:

(a) ``ARCHIVE_PASSWORD_MIN_LENGTH`` is 12 and ``ARCHIVE_PASSWORD_MAX_LENGTH`` 1024.
(b) ``archive_password_rules()`` is ``rules_with_minimum_length(12)``: A's rules in A's order, ``min_length`` at least
    12, every other rule as A has it. Never a copy taken once: when A raises its own minimum above 12 (14 here, with
    ``PASSWORD_RULES`` replaced), the archive follows.
(c) ``archive_password_problems(password)`` is ``failed_rules(password, rules=archive_password_rules())``: the codes of
    the rules missed, in the rules' order. Eleven characters meeting every class miss ``min_length`` alone, twelve meet
    them all; eight, enough for an account, are not enough for an archive; the length counts characters, as A counts it.
(d) ``exportable_instance_key()``, the key a secure archive carries (decision 39: only the key LibreFolio generated): the
    text of ``secrets/instance.key`` in the data directory, without its trailing line break (read with
    ``config.read_secret_file``), when ``instance_key_status()`` finds a generated key without a problem; that text is
    the very key this instance derives its keys from. ``None`` when the environment configures the key
    (``LIBREFOLIO_INSTANCE_KEY`` or ``LIBREFOLIO_INSTANCE_KEY_FILE``, usable or not, even beside a usable generated key
    file), when there is no key yet, and when the generated key file is unusable (too short, empty, blank). It never
    raises in those cases, and it never writes: no key file is generated, none is replaced.

Each case of (d) first checks, with ``instance_key_status()``, that the setup is the state it names: a case whose key is
not where the test thinks would prove nothing.

Pure: the data directory is a folder of ``tmp_path`` that does not exist until a test makes it (``LIBREFOLIO_TEST_MODE=1``
and ``LIBREFOLIO_TEST_DATA_DIR``, as ``test_instance_key.py`` sets them); the key variables are set or removed, and
``PASSWORD_RULES`` replaced, with ``monkeypatch``: no database, no server, no network, nothing written in the
repository or in the lane's data directory.

Red until B4: ``instance_backup/secure.py`` does not exist yet, so the import at the top fails at collection, for every
test of the module.
"""

from __future__ import annotations

import dataclasses
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from backend.app.services.accounts import password_policy
from backend.app.services.platform import instance_key
from backend.app.services.platform.instance_backup import secure
from backend.app.services.platform.instance_key import INSTANCE_KEY_FILE, INSTANCE_KEY_MIN_LENGTH, derive_key_from, instance_key_path, instance_key_status
from backend.test_scripts.test_utils import print_section, print_success

KEY_VARIABLE = "LIBREFOLIO_INSTANCE_KEY"
KEY_FILE_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_FILE"

#: The archive's bounds (P12): at least 12 characters, at most 1024 (the API's ``max_length``).
ARCHIVE_MINIMUM = 12
ARCHIVE_MAXIMUM = 1024
#: A minimum A might one day raise its own to, above the archive's.
RAISED_POLICY_MINIMUM = 14
#: The codes of A's rules, in A's order (``test_password_policy.py`` pins them).
RULE_CODES = ["min_length", "uppercase", "lowercase", "digit", "special"]

#: A key as LibreFolio generates it: 43 base64url characters (32 random bytes), well over the 32 a key needs.
GENERATED_KEY = "b4GeneratedInstanceKey_0123456789-abcdefghi"
#: A key the environment configures, with a length a key accepts.
CONFIGURED_KEY = "b4-configured-instance-key-0123456789abcdef"
#: A purpose of the instance's derived keys: the subkey of the plugin settings' secrets, which a restore re-encrypts.
PURPOSE = "plugins.settings.v1"

#: Four characters, one per class (Lu, Ll, Nd, a symbol), nine UTF-8 bytes.
UNICODE_QUARTET = "".join(unicodedata.lookup(name) for name in ("LATIN CAPITAL LETTER E WITH ACUTE", "LATIN SMALL LETTER E WITH ACUTE", "ARABIC-INDIC DIGIT THREE", "EURO SIGN"))


def meeting_every_class(length: int) -> str:
    """``length`` characters, at least four, meeting every class: ``Aa1!``, then lowercase letters."""
    return "Aa1!" + "a" * (length - 4)


#: (password, the codes ``archive_password_problems`` answers for it).
PROBLEM_CASES = [
    pytest.param(meeting_every_class(11), ["min_length"], id="eleven-characters-meeting-every-class"),
    pytest.param(meeting_every_class(12), [], id="twelve-characters-meeting-every-class"),
    pytest.param("Aa!" + "a" * 9, ["digit"], id="twelve-characters-without-a-digit"),
    pytest.param("Abcdef1!", ["min_length"], id="eight-characters-enough-for-an-account-not-for-an-archive"),
    pytest.param("abc", ["min_length", "uppercase", "digit", "special"], id="several-missed-in-the-rules-order"),
    pytest.param("", RULE_CODES, id="the-empty-password-misses-every-rule"),
    pytest.param("Correct-Horse-Battery-9", [], id="a-passphrase"),
    pytest.param(UNICODE_QUARTET * 3, [], id="twelve-unicode-characters-twenty-seven-utf8-bytes"),
    pytest.param((UNICODE_QUARTET * 3)[:11], ["min_length"], id="eleven-unicode-characters"),
]

#: Generated key files a key cannot come from: the file is there, its content is not a key.
UNUSABLE_KEY_FILES = [
    pytest.param(b"0123456789\n", id="ten-characters"),
    pytest.param(b"k" * (INSTANCE_KEY_MIN_LENGTH - 1) + b"\n", id="one-character-short"),
    pytest.param(b"", id="empty"),
    pytest.param(b" " * 40 + b"\n", id="blank"),
]


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The data directory of this test, with no configured key: the generated key file lives in it.

    It does not exist yet: whatever the code under test creates there is visible.
    """
    for variable in (KEY_VARIABLE, KEY_FILE_VARIABLE, "LIBREFOLIO_DATA_DIR"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    data = (tmp_path / "data").resolve()
    assert instance_key_path() == data / INSTANCE_KEY_FILE, f"the key file must live in the data directory of this test, not at {instance_key_path()}"
    return data


def write_key_file(data: Path, content: bytes) -> Path:
    """A key file as LibreFolio leaves it: ``secrets/instance.key`` with mode ``0600``, in a folder ``0700``."""
    key_file = data / INSTANCE_KEY_FILE
    key_file.parent.mkdir(mode=0o700, parents=True)
    key_file.parent.chmod(0o700)
    key_file.write_bytes(content)
    key_file.chmod(0o600)
    return key_file


def snapshot(directory: Path) -> dict[str, bytes | None]:
    """Every entry under ``directory``, a folder as ``None`` and a file as its bytes; ``{}`` when it does not exist."""
    if not directory.exists():
        return {}
    return {path.relative_to(directory).as_posix(): None if path.is_dir() else path.read_bytes() for path in sorted(directory.rglob("*"))}


def rule_pairs(rules: Any) -> Any:
    """``(code, value)`` of each rule; anything but a sequence of ``PasswordRule`` as it is, so that the comparison fails and shows it."""
    if not isinstance(rules, (list, tuple)) or not all(isinstance(rule, password_policy.PasswordRule) for rule in rules):
        return rules
    return [(rule.code, rule.value) for rule in rules]


def configure_the_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(KEY_VARIABLE, CONFIGURED_KEY)


def configure_a_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mounted = tmp_path / "mounted-instance-key"
    mounted.write_text(CONFIGURED_KEY + "\n", encoding="ascii")
    monkeypatch.setenv(KEY_FILE_VARIABLE, str(mounted))


def configure_a_short_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(KEY_VARIABLE, "too-short-configured-key")


def configure_a_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(KEY_FILE_VARIABLE, str(tmp_path / "missing-instance-key"))


#: (how the environment configures the key, whether that key is usable).
CONFIGURED_KEYS = [
    pytest.param(configure_the_variable, True, id="LIBREFOLIO_INSTANCE_KEY"),
    pytest.param(configure_a_file, True, id="LIBREFOLIO_INSTANCE_KEY_FILE"),
    pytest.param(configure_a_short_variable, False, id="LIBREFOLIO_INSTANCE_KEY-too-short"),
    pytest.param(configure_a_missing_file, False, id="LIBREFOLIO_INSTANCE_KEY_FILE-missing"),
]


# =============================================================================
# (a)-(c) The rules of an archive's password
# =============================================================================


def test_an_archive_password_has_12_to_1024_characters():
    """(a) P12: at least 12 characters; at most 1024, the ``max_length`` of the API's password fields."""
    bounds = (secure.ARCHIVE_PASSWORD_MIN_LENGTH, secure.ARCHIVE_PASSWORD_MAX_LENGTH)
    assert bounds == (ARCHIVE_MINIMUM, ARCHIVE_MAXIMUM), f"the archive password's bounds must be (12, 1024): got {bounds}"


def test_the_archive_rules_are_the_policys_with_a_minimum_of_12():
    """(b) ``archive_password_rules()`` is ``rules_with_minimum_length(12)``: A's rules in A's order, ``min_length`` at
    ``max(A's, 12)`` (12 while A's is 8), the other rules as A has them."""
    print_section("B4: the rules of an archive's password")
    expected = [(rule.code, max(rule.value, ARCHIVE_MINIMUM) if rule.code == "min_length" else rule.value) for rule in password_policy.PASSWORD_RULES]

    rules = secure.archive_password_rules()

    assert rule_pairs(rules) == expected, f"A's rules with min_length at least 12: expected {expected}, got {rules!r}"
    assert rules == password_policy.rules_with_minimum_length(ARCHIVE_MINIMUM), f"archive_password_rules() must be rules_with_minimum_length(12), {password_policy.rules_with_minimum_length(ARCHIVE_MINIMUM)!r}: got {rules!r}"
    print_success(f"archive_password_rules() = {rule_pairs(rules)}")


def test_the_archive_rules_follow_a_policy_minimum_raised_above_12(monkeypatch: pytest.MonkeyPatch):
    """(b) Never a copy: with A's minimum raised to 14 (``PASSWORD_RULES`` replaced after the import), the archive asks for
    14 too; 13 characters meeting every class miss ``min_length``, 14 meet every rule."""
    raised = tuple(dataclasses.replace(rule, value=RAISED_POLICY_MINIMUM) if rule.code == "min_length" else rule for rule in password_policy.PASSWORD_RULES)
    monkeypatch.setattr(password_policy, "PASSWORD_RULES", raised)
    expected = [(code, RAISED_POLICY_MINIMUM if code == "min_length" else None) for code in RULE_CODES]
    thirteen, fourteen = meeting_every_class(13), meeting_every_class(14)

    rules = secure.archive_password_rules()

    assert rule_pairs(rules) == expected, f"A's minimum raised to 14: the archive must follow, expected {expected}, got {rules!r}"
    assert secure.archive_password_problems(thirteen) == ["min_length"], f"{thirteen!r}, 13 characters against A's 14: got {secure.archive_password_problems(thirteen)}"
    assert secure.archive_password_problems(fourteen) == [], f"{fourteen!r}, 14 characters meeting every class: got {secure.archive_password_problems(fourteen)}"


@pytest.mark.parametrize(("password", "missed"), PROBLEM_CASES)
def test_the_problems_of_an_archive_password(password: str, missed: list[str]):
    """(c) ``archive_password_problems(password)``: the codes of the archive's rules the password misses, in the rules'
    order; the same answer as ``failed_rules(password, rules=archive_password_rules())``."""
    found = secure.archive_password_problems(password)

    assert found == missed, f"archive_password_problems({password!r}), {len(password)} characters: expected {missed}, got {found!r}"
    composed = password_policy.failed_rules(password, rules=secure.archive_password_rules())
    assert found == composed, f"archive_password_problems must be failed_rules(password, rules=archive_password_rules()), {composed}: got {found}"


# =============================================================================
# (d) The instance key a secure archive carries
# =============================================================================


@pytest.mark.parametrize("ending", [pytest.param(b"\n", id="ending-with-a-line-break"), pytest.param(b"", id="without-a-line-break")])
def test_a_generated_key_is_exported_as_its_text(data_dir: Path, ending: bytes):
    """(d) A usable generated key (``secrets/instance.key``, ``0600`` in a ``0700`` folder): exactly its text, the
    trailing line break not part of it; the data directory left as it was."""
    print_section("B4: the generated instance key, exported")
    assert len(GENERATED_KEY) >= INSTANCE_KEY_MIN_LENGTH, f"test bug: the sample key has {len(GENERATED_KEY)} characters, a key needs {INSTANCE_KEY_MIN_LENGTH}"
    write_key_file(data_dir, GENERATED_KEY.encode("ascii") + ending)
    status = instance_key_status()
    assert (status.source, status.problem, status.loose_modes) == ("generated", None, {}), f"precondition: a usable generated key, private to its owner: {status}"
    before = snapshot(data_dir)

    exported = secure.exportable_instance_key()

    assert exported == GENERATED_KEY, f"the generated key's text, without its line break: expected {GENERATED_KEY!r}, got {exported!r}"
    assert snapshot(data_dir) == before, f"exporting the key must write nothing: the data directory is now {sorted(snapshot(data_dir))}"
    print_success("the generated key's text, and nothing written")


def test_the_exported_key_is_the_one_this_instance_derives_its_keys_from(data_dir: Path):
    """(d) The key H generates at its first use is the one exported: the key file's text without its line break, from
    which ``derive_key_from`` gives the very subkey this instance derives, so a restore can re-encrypt with it."""
    derived = instance_key.derive_key(PURPOSE)
    key_file = data_dir / INSTANCE_KEY_FILE
    assert key_file.is_file(), f"precondition: the first derivation generates {key_file}: {sorted(snapshot(data_dir))}"

    exported = secure.exportable_instance_key()

    assert exported == key_file.read_text(encoding="ascii").rstrip("\n"), f"the text of {key_file} without its line break: got {exported!r}"
    assert derive_key_from(exported, PURPOSE) == derived, f"the exported key must be the one this instance derives {PURPOSE} from"


@pytest.mark.parametrize(("configure", "usable"), CONFIGURED_KEYS)
def test_a_configured_key_is_never_exported(data_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, configure: Callable[[pytest.MonkeyPatch, Path], None], usable: bool):
    """(d) Decision 39: a key the environment configures (``LIBREFOLIO_INSTANCE_KEY``, ``LIBREFOLIO_INSTANCE_KEY_FILE``,
    usable or not) is never exported, even beside a usable generated key file, which the instance then does not use:
    ``None``, never an exception, the data directory left as it was."""
    write_key_file(data_dir, GENERATED_KEY.encode("ascii") + b"\n")
    configure(monkeypatch, tmp_path)
    status = instance_key_status()
    assert (status.source, status.problem is None) == ("configured", usable), f"precondition: a configured key, {'usable' if usable else 'unusable'}: {status}"
    before = snapshot(data_dir)

    exported = secure.exportable_instance_key()

    assert exported is None, f"a configured key is never exported, nor the generated one beside it: got {exported!r}"
    assert snapshot(data_dir) == before, f"the data directory must stay as it was: it is now {sorted(snapshot(data_dir))}"


def test_without_a_key_nothing_is_exported_and_no_key_file_is_created(data_dir: Path):
    """(d) No key yet (the instance never derived one): ``None``, and the key file is still not there afterwards; nothing
    is created in the data directory."""
    data_dir.mkdir(parents=True)
    status = instance_key_status()
    assert status.source == "not_created", f"precondition: no key yet: {status}"

    exported = secure.exportable_instance_key()

    assert exported is None, f"no key yet: nothing to export, got {exported!r}"
    assert not (data_dir / INSTANCE_KEY_FILE).exists(), f"exporting must never generate the key file: {data_dir / INSTANCE_KEY_FILE} exists"
    assert snapshot(data_dir) == {}, f"nothing may be created in the data directory: {sorted(snapshot(data_dir))}"


@pytest.mark.parametrize("content", UNUSABLE_KEY_FILES)
def test_an_unusable_generated_key_is_never_exported_nor_replaced(data_dir: Path, content: bytes):
    """(d) A generated key file that cannot give a key (10 characters, 31, empty, blank): ``None``, never an exception;
    the file is left as it is, never replaced by a new key."""
    write_key_file(data_dir, content)
    status = instance_key_status()
    assert status.source == "generated" and status.problem is not None, f"precondition: a generated key file that cannot be used: {status}"
    before = snapshot(data_dir)

    exported = secure.exportable_instance_key()

    assert exported is None, f"an unusable key file ({len(content)} bytes) is never exported: got {exported!r}"
    assert snapshot(data_dir) == before, f"the unusable key file must be left as it is: the data directory is now {snapshot(data_dir)}"
