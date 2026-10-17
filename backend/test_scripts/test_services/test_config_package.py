"""
Guard of the configuration package (workstream H, platform, checkpoint CP2a).

Package under guard: ``backend/app/config/`` — the base (constants, data directories, test mode, ``Settings``) in
``__init__.py``, and one section module per owner (``platform.py``, ``accounts.py``, ...) holding that owner's variables.

The project rule, in one line: every environment variable of the application is read inside ``backend/app/config/``; a
module elsewhere calls an accessor of the package instead of reading ``os.environ``. Eight checks:

(a) The detector. A source READS the environment wherever it evaluates ``os.environ`` (or ``os.environb``) for anything
    but an item assignment or deletion — a subscript, ``.get``, ``.copy``, ``.items``, ``.keys``, ``.values``, ``in``,
    ``dict(...)``, iteration, unpacking, passing the mapping on, aliasing it; wherever it calls or references
    ``os.getenv`` (or ``os.getenvb``); and wherever it imports one of them from ``os`` (``from os import environ``,
    ``from os import getenv``, ``from os import *``), every use of the imported name counting as well. ``os`` is any
    name an import binds to the module: ``import os``, ``import os as alias``, ``import os.path``. The only WRITES are
    ``os.environ["X"] = "1"`` and ``del os.environ["X"]``: they read nothing and the rule allows them anywhere
    (``services/risk/quant/spawn_worker.py`` pins the native thread pools that way). An augmented assignment,
    ``setdefault`` or ``pop`` reads the item before writing it, so it counts as a read.
(b) The guard. No module under ``backend/app/`` outside ``config/`` reads the environment, except the files declared in
    ``ENVIRONMENT_READ_EXCEPTIONS``: keyed by basename, so an entry survives its module moving between packages, with
    the reason as value. The exceptions are a ratchet: an entry whose file no longer reads, or no longer exists, fails
    until it is removed. None is declared at the moment: the last one, ``web_link_finder.py``, left when its reads moved
    into ``config/plugins.py``; the mechanism stays for the next debt.
(c) The accessors that replaced the reads keep the exact semantics of the call sites they replaced, quirks included:
    any non-empty ``LIBREFOLIO_NO_SCHEDULER`` disables the scheduler, ``0`` and ``false`` too. One semantic changed on
    purpose since: an empty or blank ``JWT_SECRET`` is no secret; any other value is the secret as written, spaces
    included. The link finder's accessors in ``config/plugins.py`` keep the reads of ``web_link_finder.py``:
    ``LIBREFOLIO_WEB_LINK_FINDER_ENABLED`` unset is on and set but empty is off; the engine is stripped and lowercased, a
    blank one being the empty string; region and backend are stripped and fall back to their default when blank; the
    timeout and the maximum are what ``float()`` and ``int()`` read, the caller's default when unset, blank or refused
    (``5.0`` is no integer) — and, changed on purpose since (X-R6), when below 1, or for the timeout not finite:
    ``0``, a negative value, ``nan`` and ``inf`` give the default, ``1`` is kept. The API key is stripped and, as every secret now, may come from
    ``LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE``. ``LF_APP_VERSION``, read since through ``frozen_app_version()``, is the
    version as set, stripped, and ``None`` when unset or blank. The variables of the instance block (CP6) are new, so
    their semantics are the ones decided for them: ``LIBREFOLIO_BLOCKED`` unset or blank is not blocked, ``1``, ``true``,
    ``yes``, ``on`` block and ``0``, ``false``, ``no``, ``off`` do not, in any case and stripped, any other value raising
    ``ValueError``; ``LIBREFOLIO_DELETION_DATE`` unset or blank is no date, an ISO date (stripped) is that ``date``, any
    other value raising ``ValueError``.
(d) ``PROJECT_ROOT``, now computed from one directory deeper, is still the repository root.
(e) One rule for the address variables (CP13-1): ``env_url(name)`` reads ``name`` from the process environment, stripped;
    unset, empty or blank is ``None``; otherwise the value must start with ``http://`` or ``https://``, in any case, and
    loses one trailing slash, one only (``https://a.example//`` keeps one), nothing else changed; any other value raises
    ``ValueError`` naming the variable and quoting the value — unless it holds an ``@`` (h). The scheme is not enough (N48):
    a host must follow it — a name, an IPv4 or an IPv6 address, with a port or not —, and no whitespace may stand inside
    the address, in the host or the path. ``support_url()`` (``config/platform.py``) reads an http(s)
    ``LIBREFOLIO_SUPPORT_URL`` by that rule, and takes a ``mailto:`` address besides (g); ``public_url()`` and
    ``billing_url()`` (``config/accounts.py``) are pinned in ``test_registration_service.py``, ``mailto:`` refused.
(f) ``support_link()`` (``services/platform/instance_links.py``), what ``GET /system/instance`` publishes as
    ``support_url``, never raises: the address, or ``None`` when it is unset or invalid, and the asset search then offers
    a new GitHub issue on a self-hosted instance, no report link on a managed one (N61). An invalid address is logged
    once per process (``_report_invalid``, ``functools.cache``): one error event, ``Invalid instance link``, whose
    ``problem`` names the variable and quotes the value — never its user info (h) — and whose ``consequence`` says what
    it costs. A missing or a valid address logs nothing.
(g) One more form, for the support address alone (CP13/P20, the rule of workstream H): ``LIBREFOLIO_SUPPORT_URL`` may
    also be ``mailto:`` and one email address, so an instance can send its users to a mailbox. The value is stripped
    first, as ``env_url`` does; the scheme, in any case, comes back as ``mailto:``; the address must be one pydantic's
    ``EmailStr`` accepts, without a DNS lookup, and comes back as ``EmailStr`` normalizes it: the local part as written,
    the domain lowercased and in Unicode — a punycode domain (``xn--``) is given back decoded. Refused, as a
    ``ValueError`` naming the variable — so ``support_link()`` publishes no link and logs the one error of (f) —: an
    empty address; ``?``, ``#``, ``%``, ``,``, ``;`` or ``/`` in it, a trailing ``/`` included (never removed, as
    ``env_url`` removes it from an http(s) address); whitespace inside the value once stripped; the "pretty" forms
    ``Name <a@b.c>`` and ``<a@b.c>``, and quotes; an address ``EmailStr`` refuses (no ``@``, no dot in the domain, a
    special-use domain such as ``.test`` or ``.local``, an invalid one); and every scheme but ``http``, ``https`` and
    ``mailto``, ``mailto`` without its colon included. ``EmailStr`` alone lets several of those through — ``?``, ``#``,
    ``%`` and ``/`` are legal in a local part, where a mail client reads headers, a fragment or an escape, and where
    ``mailto://help@…``, written by analogy with ``https://``, would mail ``//help``; it strips the whitespace around
    the address and unwraps the pretty forms —, so each has a case of its own. ``env_url`` is not widened: it is the
    rule of ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BILLING_URL`` too, and still refuses a ``mailto:`` value, even
    read from ``LIBREFOLIO_SUPPORT_URL``.
(h) No user info in an address (X-R35, from workstream E's security review «R13-SEC2»). An ``@`` in the authority of
    the value, ``urlsplit(value).netloc``, is user info: a user name and a password, a user name alone, a password
    alone, or nothing at all before the ``@``. ``env_url`` refuses it — the scheme in any case, with a port or a path
    too — as a ``ValueError`` naming the variable, whose message holds neither the user name nor the password: the
    address would otherwise be published as it is, the support address on the anonymous ``GET /system/instance``, and
    its error would write the credentials into the operator's log. Nor does ``env_url`` quote any invalid value holding
    an ``@`` anywhere, whichever rule refuses it — another scheme or none, no ``//`` after it, whitespace inside, no
    host, a bracket ``urlsplit`` cannot read, the ``mailto:`` form —: without an authority to read, an ``@`` may still
    stand for user info. A value without ``@`` keeps the message of (e). ``support_url()`` refuses user info in its
    http(s) branch; a ``mailto:`` address holds an ``@`` but no authority, so it is no user info and keeps (g), quoted
    in its errors as there: public, and plain. ``support_link()`` publishes no link and logs the one error of (f), and
    no captured record holds the user name or the password. An ``@`` outside the authority — in the path, the query or
    the fragment — is no user info: the address is taken unchanged. ``public_url()``, ``billing_url()`` and the links
    built on them are pinned in ``test_registration_service.py``. Red until X-R35 lands, for the user-info cases; the
    ``@`` outside the authority and the ``mailto:`` address are controls, green before and after.

What the detector does not see: a read made on the module's behalf (``os.path.expanduser``, a library honouring
``HTTPS_PROXY``) and ``os`` reached dynamically (``importlib``, ``sys.modules``). The rule is about the variables the
application reads itself, and those are written ``os.environ`` and ``os.getenv``.

Pure: the sources are parsed with ``ast``, never imported, and the accessors run against variables set through
``monkeypatch`` (the one secret file in ``tmp_path``) — no database, no server, no network, no file written in the
repository. The guard asserts an absence, so the detector first proves it sees a presence: it flags every read shape of a
synthetic source and nothing allowed, and the scan must reach known modules, find the writes of ``spawn_worker.py``
without calling them reads, and find the reads of the config package itself (an empty parametrization would be skipped,
never red). The ratchet, with no entry to check today, proves on synthetic modules that it flags an entry excusing
nothing; it is one test over the whole dictionary, so an empty one passes instead of adding a skip. The log of
``support_link`` is read with ``structlog.testing.capture_logs``, behind a barrier: a canary logged through the module's
own logger must reach the capture, or "nothing was logged" would prove nothing. The cache of ``_report_invalid`` is
emptied before and after each of those tests, so "once per process" starts over in each. Not tested here: that
``env_url`` never reads ``.env`` — it takes no path, and no case of this file loads a dotenv file.
"""

from __future__ import annotations

import ast
import contextlib
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlsplit

import pytest
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT, SecretFileError, env_url
from backend.app.config.accounts import donation_popup_disabled
from backend.app.config.platform import configured_jwt_secret, frozen_app_version, instance_blocked, instance_deletion_date, owning_test_lane_id, scheduler_disabled, support_url
from backend.app.config.plugins import (
    web_link_finder_api_key,
    web_link_finder_ddgs_backend,
    web_link_finder_ddgs_region,
    web_link_finder_enabled,
    web_link_finder_engine,
    web_link_finder_max_results,
    web_link_finder_timeout,
)
from backend.app.services.platform import instance_links
from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "backend" / "app"
CONFIG_ROOT = APP_ROOT / "config"

# (a) The members of ``os`` that expose the environment: the mappings (str and bytes) and their getters.
ENVIRONMENT_MAPPINGS = frozenset({"environ", "environb"})
ENVIRONMENT_GETTERS = frozenset({"getenv", "getenvb"})
ENVIRONMENT_MEMBERS = ENVIRONMENT_MAPPINGS | ENVIRONMENT_GETTERS

# (b) Files still allowed to read the environment, by basename (robust to the module moving between packages), with the
# reason. Each entry is a debt: the ratchet fails as soon as its file stops reading, so the entry leaves with the move
# that pays it. Empty since the reads of web_link_finder.py moved into config/plugins.py.
ENVIRONMENT_READ_EXCEPTIONS: dict[str, str] = {}

# Presence barrier: modules the scan must reach, relative to backend/app/. The writer sets environment variables for
# its spawned children and reads none.
KNOWN_MODULES = ("main.py", "api/v1/system/health.py", "services/risk/quant/spawn_worker.py")
ENVIRONMENT_WRITER = "services/risk/quant/spawn_worker.py"

# One parametrized case per file, so a failure names the file.
SCANNED_MODULES = sorted(path.relative_to(APP_ROOT).as_posix() for path in APP_ROOT.rglob("*.py") if CONFIG_ROOT not in path.parents)
CONFIG_MODULES = sorted(path.relative_to(APP_ROOT).as_posix() for path in CONFIG_ROOT.rglob("*.py"))


# =============================================================================
# Detector
# =============================================================================


class EnvironmentAccesses(NamedTuple):
    """Where a source touches the process environment: sorted ``(line, source line)`` pairs."""

    reads: list[tuple[int, str]]
    writes: list[tuple[int, str]]


def _names_bound_to_os(tree: ast.Module) -> set[str]:
    """Every name an ``import`` binds to the ``os`` module: ``import os``, ``import os as alias``, ``import os.path`` (it binds ``os``)."""
    return {alias.asname or "os" for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names if alias.name == "os" or (alias.name.startswith("os.") and alias.asname is None)}


def _environment_imports(tree: ast.Module) -> list[ast.ImportFrom]:
    """The ``from os import ...`` statements that bind an environment member, a star import included: each one is a read."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "os" and any(alias.name == "*" or alias.name in ENVIRONMENT_MEMBERS for alias in node.names)]


def _names_bound_to_environment(tree: ast.Module) -> dict[str, str]:
    """Every name a ``from os import`` binds to an environment member, mapped to the member: ``from os import environ as env`` → ``{"env": "environ"}``."""
    names: dict[str, str] = {}
    for node in _environment_imports(tree):
        for alias in node.names:
            if alias.name == "*":
                names.update({member: member for member in ENVIRONMENT_MEMBERS})
            elif alias.name in ENVIRONMENT_MEMBERS:
                names[alias.asname or alias.name] = alias.name
    return names


def _environment_member(node: ast.AST, modules: set[str], names: dict[str, str]) -> str | None:
    """The environment member of ``os`` that ``node`` evaluates, if any: ``os.environ`` → ``"environ"``; ``getenv`` bound by ``from os import getenv`` → ``"getenv"``."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in modules and node.attr in ENVIRONMENT_MEMBERS:
        return node.attr
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        return names.get(node.id)
    return None


def _is_item_write(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    """``node`` is the mapping of an item assignment or deletion — ``os.environ["X"] = "1"``, ``del os.environ["X"]`` — the two uses that read nothing.

    An augmented assignment (``os.environ["X"] += ":more"``) stores into the item too, but reads it first.
    """
    item = parents.get(node)
    if not isinstance(item, ast.Subscript) or item.value is not node:
        return False
    return isinstance(item.ctx, ast.Del) or (isinstance(item.ctx, ast.Store) and not isinstance(parents.get(item), ast.AugAssign))


def _environment_accesses(source: str) -> EnvironmentAccesses:
    """Every read and write of the process environment in ``source``, as defined in (a) of the module docstring.

    ``ast.walk`` visits every node, so a function-level import or a read inside a nested function counts like a
    top-level one. ``source`` comes from ``read_text``, whose universal newlines leave only ``\\n``: its lines are the
    lines the parser numbers.
    """
    tree = ast.parse(source)
    lines = source.split("\n")
    modules = _names_bound_to_os(tree)
    names = _names_bound_to_environment(tree)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    reads = [(node.lineno, lines[node.lineno - 1].strip()) for node in _environment_imports(tree)]
    writes: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        member = _environment_member(node, modules, names)
        if member is None:
            continue
        access = (node.lineno, lines[node.lineno - 1].strip())
        if member in ENVIRONMENT_MAPPINGS and _is_item_write(node, parents):
            writes.append(access)
        else:
            reads.append(access)
    return EnvironmentAccesses(sorted(reads), sorted(writes))


def _accesses_of(module: str) -> EnvironmentAccesses:
    """The environment accesses of ``backend/app/<module>``."""
    return _environment_accesses((APP_ROOT / module).read_text(encoding="utf-8"))


# =============================================================================
# The detector sees what it looks for
# =============================================================================

# Every shape (a) must flag as a read: (source, lines of its reads). None of them may count as a write.
_READ_SHAPES = (
    ('import os\nvalue = os.environ["X"]\n', [2]),
    ('import os\nvalue = os.environ.get("X")\n', [2]),
    ('import os\nvalue = os.environ.get("X", "fallback")\n', [2]),
    ('import os\nvalue = os.getenv("X")\n', [2]),
    ("import os\nsnapshot = os.environ.copy()\n", [2]),
    ("import os\npairs = os.environ.items()\n", [2]),
    ("import os\nnames = os.environ.keys()\n", [2]),
    ("import os\nvalues = os.environ.values()\n", [2]),
    ('import os\npresent = "X" in os.environ\n', [2]),
    ('import os\nabsent = "X" not in os.environ\n', [2]),
    ("import os\nsnapshot = dict(os.environ)\n", [2]),
    ("import os\nfor name in os.environ:\n    print(name)\n", [2]),
    ("import os\nnames = [name for name in os.environ]\n", [2]),
    ('import os\nmerged = {**os.environ, "X": "1"}\n', [2]),
    ("import os\nenvironment = os.environ\n", [2]),
    ('import os\nimport subprocess\n\nsubprocess.run(["true"], env=os.environ, check=False)\n', [4]),
    ("import os\nread = os.getenv\n", [2]),
    ('import os\nlookup = {}\nlookup[os.environ["X"]] = 1\n', [3]),
    ('import os\nos.environ["X"] += ":more"\n', [2]),
    ('import os\nvalue = os.environ.setdefault("X", "1")\n', [2]),
    ('import os\nvalue = os.environ.pop("X", None)\n', [2]),
    ('import os\nraw = os.environb[b"X"]\n', [2]),
    ('import os\nraw = os.getenvb(b"X")\n', [2]),
    ('import os.path\nvalue = os.environ.get("X")\n', [2]),
    ('import os as operating_system\nvalue = operating_system.environ["X"]\n', [2]),
    ('import os as operating_system\nvalue = operating_system.getenv("X")\n', [2]),
    ("from os import environ\n", [1]),
    ('from os import environ\nvalue = environ.get("X")\n', [1, 2]),
    ('from os import environ as env\nvalue = env["X"]\n', [1, 2]),
    ('from os import getenv\nvalue = getenv("X")\n', [1, 2]),
    ('from os import getenv as read\nvalue = read("X")\n', [1, 2]),
    ('from os import *\nvalue = getenv("X")\n', [1, 2]),
    ('def load():\n    import os\n\n    return os.environ.get("X")\n', [4]),
    ('import os\n\n\ndef load():\n    return os.environ["A"] or os.getenv("B")\n', [5, 5]),
)

# What (a) lets through: (source, lines of the writes it must see in it). None of them may count as a read.
_ALLOWED_SHAPES = (
    ('import os\nos.environ["X"] = "1"\n', [2]),
    ('import os\ndel os.environ["X"]\n', [2]),
    ('import os\nos.environ["A"], os.environ["B"] = "1", "2"\n', [2, 2]),
    ('import os as operating_system\noperating_system.environ["X"] = "1"\n', [2]),
    ('import os\nos.environb[b"X"] = b"1"\n', [2]),
    ('import os\npath = os.path.join("a")\n', []),
    ("import os\n", []),
    ("import os\npid = os.getpid()\n", []),
    ("from os import getpid, path\n", []),
    ('environ = {"X": "1"}\nvalue = environ.get("X")\n', []),  # a name is the environment only when an import from os binds it
    ('def getenv(name):\n    return name\n\n\nvalue = getenv("X")\n', []),
)


def test_the_detector_flags_every_read_shape_and_lets_writes_through():
    print_section("Config package: the environment-read detector")
    for source, lines in _READ_SHAPES:
        accesses = _environment_accesses(source)
        assert ([line for line, _ in accesses.reads], accesses.writes) == (lines, []), source
    for source, lines in _ALLOWED_SHAPES:
        accesses = _environment_accesses(source)
        assert (accesses.reads, [line for line, _ in accesses.writes]) == ([], lines), source
    assert _environment_accesses('import os\n\nsecret = os.environ.get("JWT_SECRET") or None\n') == EnvironmentAccesses(reads=[(3, 'secret = os.environ.get("JWT_SECRET") or None')], writes=[])
    print_success(f"{len(_READ_SHAPES)} read shapes flagged, {len(_ALLOWED_SHAPES)} allowed ones left alone, writes seen as writes")


def test_the_scan_reaches_the_application_and_tells_writes_from_reads():
    print_section("Config package: the scan reaches the application")
    assert (CONFIG_ROOT / "__init__.py").is_file(), f"{CONFIG_ROOT} is not the config package: the repository root derived from this file is wrong"
    missing = sorted(set(KNOWN_MODULES) - set(SCANNED_MODULES))
    assert not missing, f"the scan of {APP_ROOT} outside config/ missed known modules: {missing}"

    writer = _accesses_of(ENVIRONMENT_WRITER)
    assert writer.writes, f"{ENVIRONMENT_WRITER} pins the native thread pools by writing os.environ, yet the detector saw no write there"
    assert writer.reads == [], f"{ENVIRONMENT_WRITER} only writes the environment, yet the detector saw reads there: {writer.reads}"

    config_reads = [f"{module}:{line}" for module in CONFIG_MODULES for line, _ in _accesses_of(module).reads]
    assert config_reads, f"the detector found no read in {CONFIG_ROOT}, the one place the environment is read: it cannot see a real read"
    print_success(f"{len(SCANNED_MODULES)} modules scanned outside config/; {len(writer.writes)} writes and no read in {ENVIRONMENT_WRITER}; {len(config_reads)} reads inside config/")


# =============================================================================
# The rule
# =============================================================================


@pytest.mark.parametrize("module", SCANNED_MODULES)
def test_a_module_outside_the_config_package_reads_no_environment_variable(module):
    """(b) A module outside backend/app/config/ calls an accessor of the package; it never reads the environment itself."""
    reads = _accesses_of(module).reads
    reason = ENVIRONMENT_READ_EXCEPTIONS.get(Path(module).name)
    if reason is not None:
        print_success(f"backend/app/{module}: {len(reads)} read(s) excused by a declared exception — {reason}")
        return
    offenders = [f"backend/app/{module}:{line} {text}" for line, text in reads]
    assert not offenders, "every environment variable of the application is read inside backend/app/config/: add an accessor to the config section of the variable's owner and call it here:\n" + "\n".join(offenders)
    print_success(f"backend/app/{module}: no environment read")


def _stale_exceptions(exceptions: dict[str, str], modules: list[str], reads_of: Callable[[str], list[tuple[int, str]]]) -> list[str]:
    """The entries of ``exceptions`` that excuse nothing any more: no file of that basename is left, or none still reads."""
    stale = []
    for basename, reason in sorted(exceptions.items()):
        matching = [module for module in modules if Path(module).name == basename]
        if not matching:
            stale.append(f"{basename}: no such file is left under backend/app/ outside config/ ({reason})")
        elif not any(reads_of(module) for module in matching):
            stale.append(f"{basename}: {', '.join(matching)} no longer read the environment ({reason})")
    return stale


def test_every_declared_exception_still_has_reads_to_excuse():
    """(b) An exception is a debt: it goes as soon as its file stops reading the environment. None declared, none owed."""
    stale = _stale_exceptions(ENVIRONMENT_READ_EXCEPTIONS, SCANNED_MODULES, lambda module: _accesses_of(module).reads)
    assert not stale, "remove these entries from ENVIRONMENT_READ_EXCEPTIONS so the rule covers their files again:\n" + "\n".join(stale)
    print_success(f"{len(ENVIRONMENT_READ_EXCEPTIONS)} exception(s) declared, each still excusing reads" if ENVIRONMENT_READ_EXCEPTIONS else "no exception declared: every module outside config/ is under the rule")


def test_the_ratchet_flags_an_exception_that_excuses_nothing():
    """(b) Presence barrier of the ratchet: through the real detector, it keeps a file that still reads and flags a file
    that no longer does and one that is gone."""
    sources = {
        "services/a/still_reads.py": 'import os\n\nvalue = os.environ.get("X")\n',
        "services/b/paid_off.py": "from backend.app.config.plugins import web_link_finder_enabled\n\nvalue = web_link_finder_enabled()\n",
    }
    exceptions = {"still_reads.py": "a debt", "paid_off.py": "a paid debt", "moved_away.py": "a file that is gone"}

    stale = _stale_exceptions(exceptions, sorted(sources), lambda module: _environment_accesses(sources[module]).reads)

    assert [entry.split(":", 1)[0] for entry in stale] == ["moved_away.py", "paid_off.py"], f"the ratchet must flag the file that is gone and the one that no longer reads, and only them: {stale}"
    print_success(f"{len(stale)} stale entries flagged, the one still excusing reads kept")


# =============================================================================
# The section accessors keep the semantics of the call sites they replaced
# =============================================================================


def _set_variable(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    """``None`` unsets ``name``; any string, the empty one included, sets it."""
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, False, id="unset"),
        pytest.param("", False, id="empty"),
        pytest.param("1", True, id="1"),
        pytest.param("true", True, id="true"),
        pytest.param("0", True, id="0-disables-too"),
        pytest.param("false", True, id="false-disables-too"),
        pytest.param(" ", True, id="blank-disables-too"),
    ],
)
def test_scheduler_disabled_by_any_non_empty_value(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_NO_SCHEDULER``: any non-empty value keeps the scheduler off, ``0`` and ``false`` included (kept on purpose)."""
    _set_variable(monkeypatch, "LIBREFOLIO_NO_SCHEDULER", value)
    assert scheduler_disabled() is expected
    print_success(f"LIBREFOLIO_NO_SCHEDULER={value!r}: scheduler_disabled() is {expected}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", None, id="empty-is-none"),
        pytest.param("  ", None, id="blank-is-none"),
        pytest.param(" \t\n", None, id="any-whitespace-is-none"),
        pytest.param(" padded ", " padded ", id="never-stripped"),
        pytest.param("s3cret-signing-key", "s3cret-signing-key", id="set"),
    ],
)
def test_configured_jwt_secret_treats_an_empty_or_blank_value_as_none(monkeypatch, value, expected):
    """(c) ``JWT_SECRET``: unset, empty or blank is no secret; anything else is the secret as written, spaces included."""
    monkeypatch.delenv("JWT_SECRET_FILE", raising=False)  # its file would stand in for an unset or empty JWT_SECRET
    _set_variable(monkeypatch, "JWT_SECRET", value)
    assert configured_jwt_secret() == expected
    print_success(f"JWT_SECRET={value!r}: configured_jwt_secret() == {expected!r}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", "", id="empty-returned-as-is"),
        pytest.param("lane-0123456789abcdef", "lane-0123456789abcdef", id="set"),
    ],
)
def test_owning_test_lane_id_is_the_variable_as_set(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_TEST_LANE_ID``: the value as the environment holds it, ``None`` when unset."""
    _set_variable(monkeypatch, "LIBREFOLIO_TEST_LANE_ID", value)
    assert owning_test_lane_id() == expected
    print_success(f"LIBREFOLIO_TEST_LANE_ID={value!r}: owning_test_lane_id() == {expected!r}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset"),
        pytest.param("", None, id="empty-is-none"),
        pytest.param("   ", None, id="blank-is-none"),
        pytest.param(" v1.2.3 ", "v1.2.3", id="stripped"),
    ],
)
def test_frozen_app_version_is_the_variable_stripped_and_none_when_blank(monkeypatch, value, expected):
    """(c) ``LF_APP_VERSION``: the version as set, stripped; ``None`` when unset, empty or blank."""
    _set_variable(monkeypatch, "LF_APP_VERSION", value)
    assert frozen_app_version() == expected
    print_success(f"LF_APP_VERSION={value!r}: frozen_app_version() == {expected!r}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, False, id="unset-is-not-blocked"),
        pytest.param("", False, id="empty-is-not-blocked"),
        pytest.param(" \t ", False, id="blank-is-not-blocked"),
        pytest.param("1", True, id="1"),
        pytest.param("true", True, id="true"),
        pytest.param("yes", True, id="yes"),
        pytest.param("on", True, id="on"),
        pytest.param("TRUE", True, id="TRUE-any-case"),
        pytest.param("Yes", True, id="Yes-any-case"),
        pytest.param(" On ", True, id="On-stripped"),
        pytest.param("0", False, id="0"),
        pytest.param("false", False, id="false"),
        pytest.param("no", False, id="no"),
        pytest.param("off", False, id="off"),
        pytest.param("FALSE", False, id="FALSE-any-case"),
        pytest.param(" Off\n", False, id="Off-stripped"),
    ],
)
def test_instance_blocked_by_1_true_yes_or_on_and_not_by_0_false_no_or_off(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_BLOCKED``: unset or blank is not blocked; the four words of each side in any case, stripped."""
    _set_variable(monkeypatch, "LIBREFOLIO_BLOCKED", value)
    assert instance_blocked() is expected
    print_success(f"LIBREFOLIO_BLOCKED={value!r}: instance_blocked() is {expected}")


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("2", id="2"),
        pytest.param("-1", id="minus-1"),
        pytest.param("y", id="y"),
        pytest.param("n", id="n"),
        pytest.param("enabled", id="enabled"),
        pytest.param("blocked", id="blocked"),
        pytest.param("true false", id="two-words"),
        pytest.param("1.0", id="1.0"),
    ],
)
def test_instance_blocked_raises_on_any_other_value(monkeypatch, value):
    """(c) ``LIBREFOLIO_BLOCKED``: a value outside the eight words is an error naming the variable, never a guess either way."""
    _set_variable(monkeypatch, "LIBREFOLIO_BLOCKED", value)
    with pytest.raises(ValueError, match="LIBREFOLIO_BLOCKED") as raised:
        instance_blocked()
    print_success(f"LIBREFOLIO_BLOCKED={value!r}: {raised.value}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset-is-no-date"),
        pytest.param("", None, id="empty-is-no-date"),
        pytest.param("   ", None, id="blank-is-no-date"),
        pytest.param("2026-11-14", date(2026, 11, 14), id="iso-date"),
        pytest.param(" 2026-11-14\n", date(2026, 11, 14), id="iso-date-stripped"),
        pytest.param("2028-02-29", date(2028, 2, 29), id="leap-day"),
    ],
)
def test_instance_deletion_date_is_an_iso_date_or_none(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_DELETION_DATE``: an ISO date, stripped, is that ``date``; unset or blank is no date."""
    _set_variable(monkeypatch, "LIBREFOLIO_DELETION_DATE", value)
    deletion_date = instance_deletion_date()
    assert (deletion_date, type(deletion_date)) == (expected, type(expected)), f"LIBREFOLIO_DELETION_DATE={value!r} must give {expected!r}, instance_deletion_date gave {deletion_date!r}"
    print_success(f"LIBREFOLIO_DELETION_DATE={value!r}: instance_deletion_date() == {deletion_date!r}")


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("14/11/2026", id="day-first"),
        pytest.param("11/14/2026", id="month-first"),
        pytest.param("2026-13-01", id="no-month-13"),
        pytest.param("2026-02-30", id="no-february-30"),
        pytest.param("2026-11-14T00:00:00", id="a-datetime"),
        pytest.param("tomorrow", id="a-word"),
        pytest.param("0", id="0"),
    ],
)
def test_instance_deletion_date_raises_on_anything_but_an_iso_date(monkeypatch, value):
    """(c) ``LIBREFOLIO_DELETION_DATE``: any other value is an error naming the variable and quoting the value."""
    _set_variable(monkeypatch, "LIBREFOLIO_DELETION_DATE", value)
    with pytest.raises(ValueError, match="LIBREFOLIO_DELETION_DATE") as raised:
        instance_deletion_date()
    assert repr(value) in str(raised.value), f"the error must quote the value it refused, {value!r}: {raised.value}"
    print_success(f"LIBREFOLIO_DELETION_DATE={value!r}: {raised.value}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, False, id="unset"),
        pytest.param("", False, id="empty"),
        pytest.param("1", True, id="1"),
        pytest.param("true", True, id="true"),
        pytest.param("yes", True, id="yes"),
        pytest.param("TRUE", True, id="TRUE-any-case"),
        pytest.param("Yes", True, id="Yes-any-case"),
        pytest.param("0", False, id="0"),
        pytest.param("false", False, id="false"),
        pytest.param("on", False, id="on-is-not-accepted"),
        pytest.param(" 1", False, id="never-stripped"),
    ],
)
def test_donation_popup_disabled_by_1_true_or_yes_in_any_case(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_DISABLE_DONATION_POPUP``: ``1``, ``true`` or ``yes`` in any case turns the popup off; nothing else does."""
    _set_variable(monkeypatch, "LIBREFOLIO_DISABLE_DONATION_POPUP", value)
    assert donation_popup_disabled() is expected
    print_success(f"LIBREFOLIO_DISABLE_DONATION_POPUP={value!r}: donation_popup_disabled() is {expected}")


# The link finder's variables, read in config/plugins.py since they left services/assets/web_link_finder.py.
LINK_FINDER = "LIBREFOLIO_WEB_LINK_FINDER_"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, True, id="unset-is-on"),
        pytest.param("", False, id="set-but-empty-is-off"),
        pytest.param("  ", False, id="blank-is-off"),
        pytest.param("1", True, id="1"),
        pytest.param("true", True, id="true"),
        pytest.param("YES", True, id="YES-any-case"),
        pytest.param(" On ", True, id="On-spaces-around"),
        pytest.param("0", False, id="0"),
        pytest.param("false", False, id="false"),
        pytest.param("off", False, id="off"),
        pytest.param("2", False, id="2-is-off"),
    ],
)
def test_web_link_finder_enabled_by_1_true_yes_or_on(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_WEB_LINK_FINDER_ENABLED``: unset is on, set but empty is off; ``1``, ``true``, ``yes``, ``on`` in any case, spaces around."""
    _set_variable(monkeypatch, LINK_FINDER + "ENABLED", value)
    assert web_link_finder_enabled() is expected
    print_success(f"{LINK_FINDER}ENABLED={value!r}: web_link_finder_enabled() is {expected}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, "ddgs", id="unset-is-ddgs"),
        pytest.param("", "", id="empty-is-empty"),
        pytest.param("   ", "", id="blank-is-empty"),
        pytest.param(" APIKEY ", "apikey", id="stripped-and-lowercased"),
        pytest.param("SearXNG", "searxng", id="lowercased"),
    ],
)
def test_web_link_finder_engine_is_stripped_and_lowercased(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_WEB_LINK_FINDER_ENGINE``: ``ddgs`` when unset; otherwise stripped and lowercased, blank giving the empty string."""
    _set_variable(monkeypatch, LINK_FINDER + "ENGINE", value)
    assert web_link_finder_engine() == expected
    print_success(f"{LINK_FINDER}ENGINE={value!r}: web_link_finder_engine() == {expected!r}")


@pytest.mark.parametrize(
    ("accessor", "variable", "default"),
    [
        pytest.param(web_link_finder_ddgs_region, LINK_FINDER + "DDGS_REGION", "wt-wt", id="region"),
        pytest.param(web_link_finder_ddgs_backend, LINK_FINDER + "DDGS_BACKEND", "auto", id="backend"),
    ],
)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset-is-the-default"),
        pytest.param("", None, id="empty-is-the-default"),
        pytest.param("   ", None, id="blank-is-the-default"),
        pytest.param(" it-it ", "it-it", id="stripped"),
        pytest.param("Google,Bing", "Google,Bing", id="case-kept"),
    ],
)
def test_web_link_finder_ddgs_option_is_stripped_or_its_default(monkeypatch, accessor: Callable[[], str], variable, default, value, expected):
    """(c) ``…_DDGS_REGION`` (``wt-wt``) and ``…_DDGS_BACKEND`` (``auto``): stripped, case kept, the default when unset or blank."""
    _set_variable(monkeypatch, variable, value)
    expected = default if expected is None else expected
    assert accessor() == expected
    print_success(f"{variable}={value!r}: {accessor.__name__}() == {expected!r}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, 7.5, id="unset-is-the-default"),
        pytest.param("", 7.5, id="empty-is-the-default"),
        pytest.param("  ", 7.5, id="blank-is-the-default"),
        pytest.param("2.5", 2.5, id="2.5"),
        pytest.param(" 3 ", 3.0, id="spaces-around-and-a-float"),
        pytest.param("1", 1.0, id="1-the-smallest-kept"),
        pytest.param("0.5", 7.5, id="below-1-is-the-default"),
        pytest.param("0", 7.5, id="0-is-the-default"),
        pytest.param("-1", 7.5, id="negative-is-the-default"),
        pytest.param("1e1", 10.0, id="exponent"),
        pytest.param("nan", 7.5, id="nan-is-the-default"),
        pytest.param("inf", 7.5, id="inf-is-the-default"),
        pytest.param("six", 7.5, id="not-a-number-is-the-default"),
    ],
)
def test_web_link_finder_timeout_is_what_float_reads_when_finite_and_at_least_1(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT``: ``float()`` of the stripped value when finite and at least 1 (X-R6: a timeout under a second meant none); the caller's default when unset, blank, refused, below 1 or not finite."""
    _set_variable(monkeypatch, LINK_FINDER + "TIMEOUT", value)
    timeout = web_link_finder_timeout(7.5)
    # repr() tells nan from nan as == cannot, and 3.0 from 3
    assert repr(timeout) == repr(expected), f"{LINK_FINDER}TIMEOUT={value!r} must give {expected!r}, web_link_finder_timeout gave {timeout!r}"
    print_success(f"{LINK_FINDER}TIMEOUT={value!r}: web_link_finder_timeout(7.5) == {timeout!r}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, 9, id="unset-is-the-default"),
        pytest.param("", 9, id="empty-is-the-default"),
        pytest.param("3", 3, id="3"),
        pytest.param(" 7 ", 7, id="spaces-around"),
        pytest.param("1", 1, id="1-the-smallest-kept"),
        pytest.param("0", 9, id="0-is-the-default"),
        pytest.param("-2", 9, id="negative-is-the-default"),
        pytest.param("5.0", 9, id="5.0-is-no-integer"),
        pytest.param("five", 9, id="not-a-number-is-the-default"),
    ],
)
def test_web_link_finder_max_results_is_what_int_reads_when_at_least_1(monkeypatch, value, expected):
    """(c) ``LIBREFOLIO_WEB_LINK_FINDER_MAX``: ``int()`` of the stripped value when at least 1 (X-R6: ``0`` returned one URL all the same); the caller's default when unset, blank, refused or below 1."""
    _set_variable(monkeypatch, LINK_FINDER + "MAX", value)
    maximum = web_link_finder_max_results(9)
    assert (maximum, type(maximum)) == (expected, int), f"{LINK_FINDER}MAX={value!r} must give {expected!r}, web_link_finder_max_results gave {maximum!r}"
    print_success(f"{LINK_FINDER}MAX={value!r}: web_link_finder_max_results(9) == {maximum!r}")


@pytest.mark.parametrize(
    ("key", "key_file", "expected"),
    [
        pytest.param(None, None, "", id="neither-set-is-empty"),
        pytest.param("", None, "", id="empty-is-empty"),
        pytest.param("   ", None, "", id="blank-is-empty"),
        pytest.param(" k3y ", None, "k3y", id="stripped"),
        pytest.param(None, "   ", "", id="blank-file-variable-is-no-file"),
        pytest.param(None, "<key file>", "from-the-file", id="from-the-file-stripped"),
        pytest.param("   ", "<key file>", "from-the-file", id="blank-key-falls-to-the-file"),
        pytest.param("from-the-variable", "<key file>", "from-the-variable", id="key-wins-over-the-file"),
    ],
)
def test_web_link_finder_api_key_from_the_variable_or_its_file_stripped(monkeypatch, tmp_path, key, key_file, expected):
    """(c) ``LIBREFOLIO_WEB_LINK_FINDER_API_KEY``, or else ``…_API_KEY_FILE`` as every secret; stripped, the empty string when neither."""
    if key_file == "<key file>":
        key_file = str(tmp_path / "web-link-finder-api-key")
        Path(key_file).write_text("  from-the-file \n", encoding="utf-8")
    _set_variable(monkeypatch, LINK_FINDER + "API_KEY", key)
    _set_variable(monkeypatch, LINK_FINDER + "API_KEY_FILE", key_file)
    assert web_link_finder_api_key() == expected
    print_success(f"{LINK_FINDER}API_KEY={key!r}, {LINK_FINDER}API_KEY_FILE={key_file!r}: {expected!r}")


def test_web_link_finder_api_key_raises_on_a_file_that_cannot_give_it(monkeypatch, tmp_path):
    """(c) A ``…_API_KEY_FILE`` that cannot give the key is an error naming the variable and the path, never a silent empty key."""
    missing = tmp_path / "missing-api-key"
    monkeypatch.delenv(LINK_FINDER + "API_KEY", raising=False)
    monkeypatch.setenv(LINK_FINDER + "API_KEY_FILE", str(missing))
    with pytest.raises(SecretFileError) as raised:
        web_link_finder_api_key()
    assert str(raised.value) == f"{LINK_FINDER}API_KEY_FILE: {missing} does not exist", f"the error must name {LINK_FINDER}API_KEY_FILE and the path: {raised.value}"
    print_success(f"{raised.value}")


# =============================================================================
# The base moved one directory deeper
# =============================================================================


def test_project_root_is_the_repository_root():
    """(d) config.py became config/__init__.py, so PROJECT_ROOT climbs one more directory to stay the repository root."""
    print_section("Config package: PROJECT_ROOT")
    assert (PROJECT_ROOT / "backend" / "app" / "config" / "__init__.py").is_file(), f"{PROJECT_ROOT} holds no backend/app/config/__init__.py"
    assert (PROJECT_ROOT / "dev.py").is_file(), f"{PROJECT_ROOT} holds no dev.py: it is not the repository root"
    assert PROJECT_ROOT.resolve() == REPO_ROOT, f"backend.app.config was imported from {PROJECT_ROOT}, not from the checkout of this test ({REPO_ROOT})"
    print_success(f"PROJECT_ROOT = {PROJECT_ROOT}")


# =============================================================================
# One rule for the address variables: env_url, and support_url built on it
# =============================================================================

#: A variable no application code reads: the generic rule of ``env_url`` is tested on it.
URL_PROBE = "LIBREFOLIO_PROBE_URL"
#: Where the users of the instance ask for help (CP13): read by ``support_url()``, published by ``support_link()``.
SUPPORT_URL_VARIABLE = "LIBREFOLIO_SUPPORT_URL"
#: The user name and the password of the user-info cases (h), distinctive enough that either one found in a message or
#: a log record can only be the value leaking.
USER_INFO_NAME = "alice"
USER_INFO_PASSWORD = "s3cr3t-pw"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset-is-none"),
        pytest.param("", None, id="empty-is-none"),
        pytest.param("   ", None, id="blank-is-none"),
        pytest.param(" \t\n", None, id="any-whitespace-is-none"),
        pytest.param("https://a.example", "https://a.example", id="https"),
        pytest.param("http://192.168.1.20:6040", "http://192.168.1.20:6040", id="http-with-a-port"),
        pytest.param("  https://a.example \n", "https://a.example", id="stripped"),
        pytest.param("HTTPS://A.EXAMPLE/Help", "HTTPS://A.EXAMPLE/Help", id="upper-case-scheme-accepted-and-case-kept"),
        pytest.param("Http://a.example", "Http://a.example", id="mixed-case-scheme-accepted"),
        pytest.param("https://a.example/", "https://a.example", id="trailing-slash-removed"),
        pytest.param("https://a.example/help/", "https://a.example/help", id="trailing-slash-of-a-path-removed"),
        pytest.param("https://a.example//", "https://a.example/", id="one-slash-removed-only"),
        pytest.param(" https://a.example/ \n", "https://a.example", id="stripped-before-the-slash-is-removed"),
        pytest.param("http://192.168.1.20:6040/", "http://192.168.1.20:6040", id="ipv4-with-a-port-trailing-slash-removed"),
        pytest.param("https://[::1]:6040", "https://[::1]:6040", id="ipv6-with-a-port-unchanged"),
        pytest.param("https://help.example/path?x=1", "https://help.example/path?x=1", id="query-unchanged"),
        pytest.param("HTTPS://Help.Example/", "HTTPS://Help.Example", id="mixed-case-host-kept-trailing-slash-removed"),
    ],
)
def test_env_url_is_the_address_stripped_and_without_one_trailing_slash(monkeypatch, value, expected):
    """(e) ``env_url(name)``: ``None`` when unset, empty or blank; otherwise the value stripped, ``http://`` or ``https://`` in any case, one trailing slash removed — one only —, nothing else changed.

    The host is a name, an IPv4 or an IPv6 address, with a port or not; the case of the scheme and of the host, the path
    and the query stay as written. Controls of N48: every case here stays valid once a host is required.
    """
    _set_variable(monkeypatch, URL_PROBE, value)
    address = env_url(URL_PROBE)
    assert address == expected, f"{URL_PROBE}={value!r} must give {expected!r}, env_url gave {address!r}"
    print_success(f"{URL_PROBE}={value!r}: env_url() == {address!r}")


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("a.example", id="no-scheme"),
        pytest.param("a.example/help/", id="no-scheme-with-a-path"),
        pytest.param("ftp://a.example", id="ftp"),
        pytest.param(" FTP://a.example/ ", id="ftp-any-case-stripped"),
        pytest.param("//a.example", id="scheme-relative"),
        pytest.param("https:/a.example", id="one-slash-after-the-scheme"),
        pytest.param("javascript:alert(1)", id="javascript"),
    ],
)
def test_env_url_raises_on_anything_but_an_http_or_https_address(monkeypatch, value):
    """(e) Any other value is an error naming the variable and quoting the value, when it holds no ``@`` — one that does is never quoted (h), its ``mailto:`` row there —: it would become a link the instance hands out, so it is never guessed."""
    monkeypatch.setenv(URL_PROBE, value)
    with pytest.raises(ValueError, match=URL_PROBE) as raised:
        env_url(URL_PROBE)
    assert value.strip() in str(raised.value), f"the error must quote the value it refused, {value.strip()!r}: {raised.value}"
    print_success(f"{URL_PROBE}={value!r}: {raised.value}")


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("https://", id="https-alone"),
        pytest.param("http://", id="http-alone"),
        pytest.param("https:///path", id="empty-host"),
        pytest.param("https://:443", id="port-without-a-host"),
        pytest.param("https://help .example", id="space-in-the-host"),
        pytest.param("https://help.example/a b", id="space-in-the-path"),
        pytest.param("https://help.example/a\tb", id="tab-in-the-path"),
    ],
)
def test_env_url_raises_on_an_address_without_a_host_or_with_whitespace_inside(monkeypatch, value):
    """(e) N48: the scheme is not enough. Without a host — the scheme alone, an empty host, a port without a host —, or with whitespace inside, the address is an error naming the variable and quoting the value.

    Either way the link the instance hands out would lead nowhere, or not where it says.
    """
    monkeypatch.setenv(URL_PROBE, value)
    with pytest.raises(ValueError, match=URL_PROBE) as raised:
        env_url(URL_PROBE)
    # Quoted as repr() quotes it, as the message does today: a tab must show as \t in the log line, not as a blank
    assert repr(value) in str(raised.value), f"the error must quote the value it refused, as repr() does, {value!r}: {raised.value}"
    print_success(f"{URL_PROBE}={value!r}: {raised.value}")


def _user_info_in(text: str) -> list[str]:
    """The parts of the user info of the cases (h) that ``text`` holds, in any case: anything but ``[]`` is the value leaking."""
    return [part for part in (USER_INFO_NAME, USER_INFO_PASSWORD) if part.casefold() in text.casefold()]


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("https://alice:s3cr3t-pw@help.example.org", id="user-name-and-password"),
        pytest.param("https://alice@help.example.org", id="user-name-alone"),
        pytest.param("https://:s3cr3t-pw@help.example.org", id="password-alone"),
        pytest.param("https://@help.example.org", id="nothing-before-the-at-sign"),
        pytest.param("https://:@help.example.org", id="empty-user-name-and-password"),
        pytest.param("HTTPS://alice:s3cr3t-pw@help.example.org", id="upper-case-scheme"),
        pytest.param("Http://alice:s3cr3t-pw@help.example.org", id="mixed-case-scheme"),
        pytest.param("https://alice:s3cr3t-pw@help.example.org:8443", id="with-a-port"),
        pytest.param("https://alice:s3cr3t-pw@help.example.org/support/", id="with-a-path"),
        pytest.param("http://alice:s3cr3t-pw@192.168.1.20:6040", id="ipv4-with-a-port"),
        pytest.param("https://alice:s3cr3t-pw@[::1]:6040", id="ipv6-with-a-port"),
        pytest.param("  https://alice:s3cr3t-pw@help.example.org/ \n", id="stripped"),
        pytest.param("https://alice:s3cr3t-pw@help.example.org@evil.example", id="two-at-signs-the-host-after-the-last"),
    ],
)
def test_env_url_refuses_user_info_in_the_authority_and_never_quotes_it(monkeypatch, value):
    """(h) X-R35: an ``@`` in the authority is user info — even with nothing before it —, refused as an error naming the variable whatever the case of the scheme, with a port or a path too; the message holds neither the user name nor the password.

    Accepted, the address would be published as it is — the support address on the anonymous ``GET /system/instance``,
    ``LIBREFOLIO_PUBLIC_URL`` in every link built on it —; quoted, its error would write the credentials into the
    operator's log. Red today: ``env_url`` takes every one of them.
    """
    assert "@" in urlsplit(value.strip()).netloc, f"precondition: {value!r} must hold user info by the rule's own definition, an @ in urlsplit(value).netloc"
    monkeypatch.setenv(URL_PROBE, value)
    with pytest.raises(ValueError, match=URL_PROBE) as raised:
        env_url(URL_PROBE)
    assert _user_info_in(str(raised.value)) == [], f"the error must name {URL_PROBE} without quoting its user info, neither {USER_INFO_NAME!r} nor {USER_INFO_PASSWORD!r}: {raised.value}"
    print_success(f"{URL_PROBE}: refused without its user info — {raised.value}")


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("ftp://alice:s3cr3t-pw@help.example.org", id="ftp"),
        pytest.param("//alice:s3cr3t-pw@help.example.org", id="scheme-relative"),
        pytest.param("https://alice:s3cr3t-pw@help.example.org/my help", id="space-in-the-path"),
        pytest.param("https://alice:s3cr3t-pw@", id="no-host"),
        pytest.param("alice:s3cr3t-pw@help.example.org", id="no-double-slash-the-user-name-read-as-the-scheme"),
        pytest.param("https:alice:s3cr3t-pw@help.example.org", id="no-double-slash-after-the-scheme"),
        pytest.param("https://alice:s3cr3t-pw@[::1", id="unclosed-ipv6-bracket-urlsplit-raises"),
        pytest.param("mailto:alice:s3cr3t-pw@help.example.org", id="mailto-read-by-env-url"),
    ],
)
def test_env_url_never_quotes_user_info_even_when_another_rule_refuses_the_address(monkeypatch, value):
    """(h) X-R35: an invalid value holding an ``@`` anywhere is an error naming the variable, never quoting the value, whichever rule refuses it: the message holds neither the user name nor the password.

    The rule that speaks first may be another one of (e) — a scheme other than http(s), or none, no ``//`` after it,
    whitespace inside, no host, a bracket ``urlsplit`` cannot read —: without an authority to read, an ``@`` may still
    stand for user info, so the value stays out of what reaches the operator's log. ``env_url`` refuses a ``mailto:``
    value too, unquoted: only ``support_url()`` takes that form, and quotes its address there (g), public and plain.
    Red today: these are refused already, the message quoting the whole value.
    """
    assert "@" in value and _user_info_in(value) == [USER_INFO_NAME, USER_INFO_PASSWORD], f"precondition: {value!r} must hold an @, and both parts of the user info whose absence from the message is checked"
    monkeypatch.setenv(URL_PROBE, value)
    with pytest.raises(ValueError, match=URL_PROBE) as raised:
        env_url(URL_PROBE)
    assert _user_info_in(str(raised.value)) == [], f"the error must name {URL_PROBE} without quoting its user info, neither {USER_INFO_NAME!r} nor {USER_INFO_PASSWORD!r}: {raised.value}"
    print_success(f"{URL_PROBE}: refused without its user info — {raised.value}")


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("https://help.example.org/team@x", id="in-the-path"),
        pytest.param("https://help.example.org/?to=a@b.org", id="in-the-query"),
        pytest.param("https://help.example.org?to=a@b.org", id="in-a-query-right-after-the-host"),
        pytest.param("https://help.example.org/faq#ask@desk", id="in-the-fragment"),
    ],
)
def test_env_url_takes_an_at_sign_outside_the_authority_unchanged_it_is_no_user_info(monkeypatch, value):
    """(h) X-R35, control: the authority ends at the first ``/``, ``?`` or ``#``, so an ``@`` in the path, the query or the fragment is no user info, and the address is taken unchanged, as (e) takes any other. Green before X-R35 and after: a fix refusing every ``@`` would turn it red."""
    assert "@" not in urlsplit(value).netloc, f"precondition: the @ of {value!r} must stand outside the authority, urlsplit(value).netloc"
    monkeypatch.setenv(URL_PROBE, value)
    address = env_url(URL_PROBE)
    assert address == value, f"{URL_PROBE}={value!r}: an @ outside the authority is no user info, env_url must give the address unchanged, gave {address!r}"
    print_success(f"{URL_PROBE}={value!r}: env_url() == {address!r}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset-is-none"),
        pytest.param("", None, id="empty-is-none"),
        pytest.param(" \t ", None, id="blank-is-none"),
        pytest.param(" https://help.example.com/support/ ", "https://help.example.com/support", id="stripped-without-its-trailing-slash"),
        pytest.param("HTTP://help.example.com", "HTTP://help.example.com", id="http-any-case"),
    ],
)
def test_support_url_is_librefolio_support_url_by_the_rule_of_env_url(monkeypatch, value, expected):
    """(e) ``LIBREFOLIO_SUPPORT_URL``: the address the users of the instance ask for help at, by the rule of ``env_url``; ``None`` when unset or blank."""
    _set_variable(monkeypatch, SUPPORT_URL_VARIABLE, value)
    address = support_url()
    assert address == expected, f"{SUPPORT_URL_VARIABLE}={value!r} must give {expected!r}, support_url gave {address!r}"
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: support_url() == {address!r}")


@pytest.mark.parametrize("value", [pytest.param("help.example.com", id="no-scheme"), pytest.param("ftp://help.example.com", id="ftp")])
def test_support_url_raises_naming_librefolio_support_url(monkeypatch, value):
    """(e) An address that is neither http(s) nor ``mailto:`` (g) is an error naming ``LIBREFOLIO_SUPPORT_URL``: the accessor never guesses, and ``support_link()`` decides what it costs."""
    monkeypatch.setenv(SUPPORT_URL_VARIABLE, value)
    with pytest.raises(ValueError, match=SUPPORT_URL_VARIABLE) as raised:
        support_url()
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: {raised.value}")


@pytest.mark.parametrize("value", [pytest.param("https://alice:s3cr3t-pw@help.example.org/support", id="user-name-and-password")])
def test_support_url_refuses_user_info_in_an_http_address_and_never_quotes_it(monkeypatch, value):
    """(h) X-R35: an http(s) ``LIBREFOLIO_SUPPORT_URL`` follows the rule of ``env_url``, so user info in its authority is an error naming the variable, whose message holds neither the user name nor the password. Red today: ``support_url()`` gives the address back, credentials included."""
    monkeypatch.setenv(SUPPORT_URL_VARIABLE, value)
    with pytest.raises(ValueError, match=SUPPORT_URL_VARIABLE) as raised:
        support_url()
    assert _user_info_in(str(raised.value)) == [], f"the error must name {SUPPORT_URL_VARIABLE} without quoting its user info, neither {USER_INFO_NAME!r} nor {USER_INFO_PASSWORD!r}: {raised.value}"
    print_success(f"{SUPPORT_URL_VARIABLE}: refused without its user info — {raised.value}")


@pytest.mark.parametrize(("value", "expected"), [pytest.param("mailto:alice@help.example.org", "mailto:alice@help.example.org", id="mailto")])
def test_support_url_still_takes_a_mailto_address_its_at_sign_is_no_user_info(monkeypatch, value, expected):
    """(h) X-R35, control: a ``mailto:`` address holds an ``@`` but no authority, so it is no user info and keeps the rule of (g). Green before X-R35 and after."""
    assert "@" not in urlsplit(value).netloc, f"precondition: {value!r} must have no authority to hold user info in, urlsplit(value).netloc"
    monkeypatch.setenv(SUPPORT_URL_VARIABLE, value)
    address = support_url()
    assert address == expected, f"{SUPPORT_URL_VARIABLE}={value!r}: a mailto: address is no user info, support_url must give {expected!r}, gave {address!r}"
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: support_url() == {address!r}")


# =============================================================================
# The support address may also be mailto: and one email address (CP13/P20)
# =============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("mailto:help@example.org", "mailto:help@example.org", id="mailto"),
        pytest.param("MAILTO:help@example.org", "mailto:help@example.org", id="upper-case-scheme-saved-lowercase"),
        pytest.param("MailTo:help@example.org", "mailto:help@example.org", id="mixed-case-scheme-saved-lowercase"),
        pytest.param("mailto:Help@Example.ORG", "mailto:Help@example.org", id="domain-lowercased-local-part-kept"),
        pytest.param("  mailto:help@example.org  ", "mailto:help@example.org", id="stripped"),
        pytest.param(" \tMAILTO:Help@Example.ORG\n", "mailto:Help@example.org", id="stripped-then-scheme-and-domain-lowercased"),
        pytest.param("mailto:support@help.example.co.uk", "mailto:support@help.example.co.uk", id="subdomain"),
        pytest.param("mailto:support+librefolio@example.org", "mailto:support+librefolio@example.org", id="plus-tag-in-the-local-part-kept"),
        pytest.param("mailto:info@Bücher.DE", "mailto:info@bücher.de", id="internationalized-domain-lowercased"),
        pytest.param("mailto:info@xn--bcher-kva.de", "mailto:info@bücher.de", id="punycode-domain-given-back-in-unicode"),
    ],
)
def test_support_url_accepts_mailto_and_one_address_as_email_str_normalizes_it(monkeypatch, value, expected):
    """(g) ``LIBREFOLIO_SUPPORT_URL`` may be ``mailto:`` and one email address: the value stripped, the scheme saved as ``mailto:`` whatever its case, the address as pydantic's ``EmailStr`` normalizes it.

    ``EmailStr`` keeps the local part as written and gives the domain back lowercased and in Unicode: a punycode domain
    comes back decoded, ``xn--bcher-kva.de`` as ``bücher.de``.
    """
    _set_variable(monkeypatch, SUPPORT_URL_VARIABLE, value)
    address = support_url()
    assert address == expected, f"{SUPPORT_URL_VARIABLE}={value!r} must give {expected!r}, support_url gave {address!r}"
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: support_url() == {address!r}")


@pytest.mark.parametrize(
    "value",
    [
        # An empty address
        pytest.param("mailto:", id="empty-mailto"),
        pytest.param(" MailTo:  ", id="empty-mailto-once-stripped"),
        # ? # % , ; — EmailStr alone takes the first three in a local part, where a mail client reads headers, a fragment, an escape
        pytest.param("mailto:help?cc=boss@example.org", id="question-mark-a-header-in-the-local-part"),
        pytest.param("mailto:help@example.org?subject=Help", id="question-mark-a-subject-query"),
        pytest.param("mailto:help#desk@example.org", id="hash-in-the-local-part"),
        pytest.param("mailto:help@example.org#top", id="hash-a-fragment"),
        pytest.param("mailto:he%6Cp@example.org", id="percent-escape-in-the-local-part"),
        pytest.param("mailto:help%40example.org", id="percent-escaped-at-sign"),
        pytest.param("mailto:help@example.org,sales@example.org", id="comma-two-addresses"),
        pytest.param("mailto:help@example.org;sales@example.org", id="semicolon-two-addresses"),
        # / anywhere in the address — EmailStr alone takes it in a local part, so mailto:// written by analogy with https:// would mail "//help"; a trailing one is never removed, as env_url removes it from an http(s) address
        pytest.param("mailto://help@example.org", id="double-slash-after-the-colon"),
        pytest.param("mailto:help/desk@example.org", id="slash-in-the-local-part"),
        pytest.param("mailto:help@example.org/", id="trailing-slash-never-removed"),
        # Whitespace inside the value once stripped — EmailStr alone strips it around the address
        pytest.param("mailto: help@example.org", id="space-after-the-colon"),
        pytest.param("mailto:\thelp@example.org", id="tab-after-the-colon"),
        pytest.param("mailto:\nhelp@example.org", id="line-break-after-the-colon"),
        pytest.param("mailto:\u00a0help@example.org", id="no-break-space-after-the-colon"),
        pytest.param("mailto:help desk@example.org", id="space-in-the-local-part"),
        # The pretty forms and quotes — EmailStr alone unwraps the address out of the first four
        pytest.param("mailto:Help Desk <help@example.org>", id="pretty-name-and-angle-brackets"),
        pytest.param("mailto:<help@example.org>", id="angle-brackets"),
        pytest.param("mailto:Help<help@example.org>", id="pretty-name-without-a-space"),
        pytest.param('mailto:"Help"<help@example.org>', id="quoted-pretty-name"),
        pytest.param('mailto:"help"@example.org', id="quoted-local-part"),
        # An address EmailStr refuses
        pytest.param("mailto:help", id="no-at-sign"),
        pytest.param("mailto:@example.org", id="no-local-part"),
        pytest.param("mailto:help@", id="no-domain"),
        pytest.param("mailto:a@localhost", id="domain-without-a-dot"),
        pytest.param("mailto:help@example.test", id="special-use-domain-test"),
        pytest.param("mailto:help@printer.local", id="special-use-domain-local"),
        pytest.param("mailto:help@-example.org", id="invalid-domain"),
        pytest.param("mailto:help@[192.0.2.1]", id="ip-literal-domain"),
        # Every scheme but http, https and mailto
        pytest.param("javascript:alert(1)", id="javascript"),
        pytest.param("JavaScript:alert(1)", id="javascript-any-case"),
        pytest.param("data:text/html,x", id="data"),
        pytest.param("ftp://example.org", id="ftp"),
        pytest.param("file:///etc/passwd", id="file"),
        pytest.param("mailto", id="mailto-alone-without-its-colon"),
        pytest.param("mailtohelp@example.org", id="mailto-without-its-colon"),
    ],
)
def test_support_url_refuses_anything_but_mailto_and_one_plain_address_naming_librefolio_support_url(monkeypatch, value):
    """(g) Any other ``mailto:`` value, and any scheme but ``http``, ``https`` and ``mailto``, is an error naming ``LIBREFOLIO_SUPPORT_URL``: the accessor never guesses, and ``support_link()`` decides what it costs.

    One address, written plainly: never empty, without ``? # % , ; /``, without whitespace inside, never a pretty form
    or quoted, and one ``EmailStr`` accepts. The cases ``EmailStr`` would let through on its own are the ones this table
    exists for.
    """
    monkeypatch.setenv(SUPPORT_URL_VARIABLE, value)
    with pytest.raises(ValueError, match=SUPPORT_URL_VARIABLE) as raised:
        support_url()
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: {raised.value}")


@pytest.mark.parametrize("value", [pytest.param("mailto:help@example.org", id="mailto"), pytest.param("MAILTO:help@example.org", id="mailto-any-case")])
def test_env_url_still_refuses_mailto_even_read_from_librefolio_support_url(monkeypatch, value):
    """(g) The ``mailto:`` form belongs to ``support_url()`` alone: ``env_url``, the rule of ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BILLING_URL`` too, still refuses it — even from the very variable ``support_url()`` reads."""
    monkeypatch.setenv(SUPPORT_URL_VARIABLE, value)
    with pytest.raises(ValueError, match=SUPPORT_URL_VARIABLE) as raised:
        env_url(SUPPORT_URL_VARIABLE)
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: env_url() still refuses it — {raised.value}")


# =============================================================================
# The support address the instance publishes: support_link
# =============================================================================

#: The one event an invalid instance link logs (``services/platform/instance_links.py``).
INVALID_INSTANCE_LINK = "Invalid instance link"
LINK_LOG_CANARY = "canary: the capture reaches the logger of the instance links"


@pytest.fixture
def fresh_link_reports() -> Iterator[None]:
    """The cache of ``_report_invalid`` empty before and after the test: "once per process" starts over, and no test inherits what another reported."""
    instance_links._report_invalid.cache_clear()
    yield
    instance_links._report_invalid.cache_clear()


@contextlib.contextmanager
def _captured_link_log() -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged through the module's own logger must be among them.

    Without it, a capture that misses the module's events would pass every "nothing was logged" and count no error where
    one was logged.
    """
    with capture_logs() as events:
        instance_links.logger.debug(LINK_LOG_CANARY)
        yield events
    assert any(event.get("event") == LINK_LOG_CANARY for event in events), f"barrier: the events of the instance links' logger do not reach capture_logs, so what this test reads of the log proves nothing: {events}"


def _error_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The error-level events among those captured: what an operator's log shows as a problem."""
    return [event for event in events if event.get("log_level") in ("error", "critical")]


@pytest.mark.usefixtures("fresh_link_reports")
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset-is-no-link"),
        pytest.param("  ", None, id="blank-is-no-link"),
        pytest.param(" https://help.example.com/support/ ", "https://help.example.com/support", id="valid-is-the-address"),
    ],
)
def test_support_link_is_the_support_address_and_logs_nothing(monkeypatch, value, expected):
    """(f) ``support_link()``: the address of ``LIBREFOLIO_SUPPORT_URL``, ``None`` without one — the asset search then offers a new GitHub issue on a self-hosted instance, no report link on a managed one (N61) —; neither is a problem: nothing is logged."""
    _set_variable(monkeypatch, SUPPORT_URL_VARIABLE, value)
    with _captured_link_log() as events:
        link = instance_links.support_link()
    assert link == expected, f"{SUPPORT_URL_VARIABLE}={value!r}: support_link() must give {expected!r}, gave {link!r}"
    assert _error_events(events) == [], f"a missing or a valid {SUPPORT_URL_VARIABLE} is no problem to report: {_error_events(events)}"
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: support_link() == {link!r}, nothing logged")


@pytest.mark.usefixtures("fresh_link_reports")
@pytest.mark.parametrize("value", [pytest.param("help.example.com", id="no-scheme"), pytest.param("ftp://help.example.com", id="ftp")])
def test_an_invalid_support_address_is_no_link_and_one_error_however_often_it_is_read(monkeypatch, value):
    """(f) An invalid ``LIBREFOLIO_SUPPORT_URL`` never raises out of ``support_link()``: no link at every reading, so the asset search behaves as without a support address (N61).

    And one error for the whole process, ``Invalid instance link``, whose ``problem`` names the variable and quotes the
    value and whose ``consequence`` says what it costs.
    """
    monkeypatch.setenv(SUPPORT_URL_VARIABLE, value)
    with _captured_link_log() as events:
        links = [instance_links.support_link(), instance_links.support_link()]
    errors = _error_events(events)
    assert links == [None, None], f"{SUPPORT_URL_VARIABLE}={value!r}: every reading must give no link, got {links}"
    reported = [(error.get("event"), error.get("consequence")) for error in errors]
    assert reported == [(INVALID_INSTANCE_LINK, instance_links._DEFAULT_SUPPORT)], f"two readings of an invalid {SUPPORT_URL_VARIABLE} must log exactly one error, {INVALID_INSTANCE_LINK!r}, saying what it costs: {errors}"
    problem = str(errors[0].get("problem"))
    assert SUPPORT_URL_VARIABLE in problem and value in problem, f"the problem must name {SUPPORT_URL_VARIABLE} and quote the value it refused, {value!r}: {problem!r}"
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: no link twice, one error — {problem}")


@pytest.mark.usefixtures("fresh_link_reports")
@pytest.mark.parametrize("value", [pytest.param("https://alice:s3cr3t-pw@help.example.org/support", id="user-name-and-password")])
def test_a_support_address_with_user_info_is_no_link_and_no_log_record_holds_it(monkeypatch, value):
    """(h) X-R35: ``LIBREFOLIO_SUPPORT_URL`` with user info is invalid like any other (f): ``support_link()`` gives no link at every reading, so the anonymous ``GET /system/instance`` never carries the credentials, and logs one error for the whole process, naming the variable.

    No captured record holds the user name or the password; the one error, and the canary of the capture, are the
    presence barriers that give that absence its meaning. Red today: ``support_link()`` publishes the address,
    credentials included, and logs nothing.
    """
    monkeypatch.setenv(SUPPORT_URL_VARIABLE, value)
    with _captured_link_log() as events:
        links = [instance_links.support_link(), instance_links.support_link()]
    errors = _error_events(events)
    assert links == [None, None], f"{SUPPORT_URL_VARIABLE} with user info: every reading must publish no link, got {links}"
    reported = [(error.get("event"), error.get("consequence")) for error in errors]
    assert reported == [(INVALID_INSTANCE_LINK, instance_links._DEFAULT_SUPPORT)], f"two readings of {SUPPORT_URL_VARIABLE} with user info must log exactly one error, {INVALID_INSTANCE_LINK!r}, saying what it costs: {errors}"
    problem = str(errors[0].get("problem"))
    assert SUPPORT_URL_VARIABLE in problem, f"the problem must name {SUPPORT_URL_VARIABLE}: {problem!r}"
    leaking = [event for event in events if _user_info_in(repr(event))]
    assert leaking == [], f"no log record may hold the user name {USER_INFO_NAME!r} or the password {USER_INFO_PASSWORD!r}: {leaking}"
    print_success(f"{SUPPORT_URL_VARIABLE} with user info: no link twice, one error without the credentials — {problem}")


@pytest.mark.usefixtures("fresh_link_reports")
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("mailto:help@example.org", "mailto:help@example.org", id="mailto-is-the-address"),
        pytest.param(" MailTo:Help@Example.ORG ", "mailto:Help@example.org", id="mailto-stripped-and-normalized"),
    ],
)
def test_support_link_publishes_a_mailto_address_and_logs_nothing(monkeypatch, value, expected):
    """(g) ``support_link()`` publishes a ``mailto:`` support address as ``support_url()`` normalizes it, for ``GET /system/instance``: a valid address is no problem, nothing is logged."""
    _set_variable(monkeypatch, SUPPORT_URL_VARIABLE, value)
    with _captured_link_log() as events:
        link = instance_links.support_link()
    assert link == expected, f"{SUPPORT_URL_VARIABLE}={value!r}: support_link() must publish {expected!r}, gave {link!r}; errors logged: {_error_events(events)}"
    assert _error_events(events) == [], f"a valid mailto: {SUPPORT_URL_VARIABLE} is no problem to report: {_error_events(events)}"
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: support_link() == {link!r}, nothing logged")


@pytest.mark.usefixtures("fresh_link_reports")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("mailto:", id="empty-mailto"),
        pytest.param("mailto:help?cc=boss@example.org", id="question-mark-a-header"),
        pytest.param("mailto: help@example.org", id="space-after-the-colon"),
        pytest.param("mailto:Help Desk <help@example.org>", id="pretty-form"),
        pytest.param("mailto:a@localhost", id="an-address-email-str-refuses"),
        pytest.param("JavaScript:alert(1)", id="javascript"),
    ],
)
def test_an_invalid_mailto_support_address_is_no_link_and_one_error_however_often_it_is_read(monkeypatch, value):
    """(g) A ``mailto:`` value the rule refuses, or a foreign scheme, never reaches the published link: ``support_link()`` gives no link at every reading, so the asset search behaves as without a support address (N61).

    And, as for any invalid address (f), one error for the whole process, ``Invalid instance link``, whose ``problem``
    names the variable and quotes the value and whose ``consequence`` says what it costs.
    """
    monkeypatch.setenv(SUPPORT_URL_VARIABLE, value)
    with _captured_link_log() as events:
        links = [instance_links.support_link(), instance_links.support_link()]
    errors = _error_events(events)
    assert links == [None, None], f"{SUPPORT_URL_VARIABLE}={value!r}: every reading must give no link, got {links}"
    reported = [(error.get("event"), error.get("consequence")) for error in errors]
    assert reported == [(INVALID_INSTANCE_LINK, instance_links._DEFAULT_SUPPORT)], f"two readings of an invalid {SUPPORT_URL_VARIABLE} must log exactly one error, {INVALID_INSTANCE_LINK!r}, saying what it costs: {errors}"
    problem = str(errors[0].get("problem"))
    assert SUPPORT_URL_VARIABLE in problem and value in problem, f"the problem must name {SUPPORT_URL_VARIABLE} and quote the value it refused, {value!r}: {problem!r}"
    print_success(f"{SUPPORT_URL_VARIABLE}={value!r}: no link twice, one error — {problem}")
