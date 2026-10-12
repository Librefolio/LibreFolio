"""
Gate of the frontend translation catalogue (workstream U, step U-2): ``scripts/i18n_catalog.py``.

The catalogue the app loads, ``frontend/src/lib/i18n/<lang>.json``, is generated and ignored by git. Its sources are
``frontend/src/lib/i18n/base/`` (the generic vocabulary), one folder per subsystem holding the key prefixes it claims in
``prefixes.txt``, and the ``i18n/`` folder of each plugin, ``backend/app/services/<family>/<plugin>/i18n/`` in the
``*_providers`` and ``*_plugins`` families. Each rule is proven in both halves, what it accepts and what it refuses, on
synthetic trees under ``tmp_path``:

1. Ownership. A key belongs to the plugin whose ``i18n/`` holds it, otherwise to the subsystem with the longest declared
   prefix (whole segments; ``#`` starts a comment), otherwise to ``base``.
2. Defects. A key in two sources, a string in one source and a branch in another (or the same one, whatever sorts
   between them), a key outside the folder its prefix names, a prefix declared by two subsystems or twice by one, a
   subsystem without prefixes, a source without English, a key English does not have, a value that is not a string
   (``null`` included), unreadable JSON and a language ``base`` does not have are errors, for ``merge``, ``build`` and
   ``check`` alike, all reported at once.
3. Fallback. A translation missing from a language is filled from English with a warning when building
   (``strict=False``), and is an error when checking (``strict=True``). Without ``fill`` (``load_catalog(...,
   fallback=False)``) a language holds only the translations its sources have, which is what a test checking
   "translated in every language" must read.
4. Order and format. Each source keeps its own key order, in each language: ``base``, then the subsystems by name,
   then the plugins by path. The text is ``json.dumps(nested, ensure_ascii=False, indent=2)`` and a newline, so a
   single source comes back byte for byte.
5. ``build``. Writes a language only when its text changes, read-only (0444), beside the ``.generated`` stamp (sha256
   per language); refuses, writing nothing, a generated file edited by hand (neither the new text nor the stamped one)
   unless forced; a second run writes nothing.
6. Where a new key goes. ``route``: when every key under the key's deepest existing ancestor belongs to one plugin and
   the ancestor lies within that plugin's own branch (``plugin_namespace``), that plugin; when they belong only to
   plugins otherwise, a refusal naming them and asking for ``--into``; else the longest prefix, else ``base``.
   ``set_key(into=...)`` takes ``base``, a subsystem, or exactly ``<family>/<plugin>`` in a family discovery reads,
   with its ``plugin.py``; ``where`` names the file.
7. Edits. ``move``, ``split`` (rerunnable), ``remove_key`` and ``set_key`` keep the merged catalogue valid, and
   unchanged where they only rearrange it; they rewrite only the files they touch, refuse whole when the result would
   be invalid, and delete the files of a plugin source they empty.
8. Revisions, on a throwaway git repository. ``catalogs_at`` reads the legacy layout (one tracked file per language)
   and the tracked sources alike, without fallback, and refuses a revision that is not a commit; ``check(against=...)``
   compares the working sources, without fallback, with a revision; ``absorb`` merges three ways, per key and per
   language, what a branch changed on the legacy layout: applied where only it changed, already there where both
   agree, a conflict where both changed differently (all reported and nothing written, unless ``prefer`` settles them),
   a new key where ``route`` says, removals first, and nothing at all on any problem. A key one side removed while the
   other gave one of its translations a new text is one conflict about the whole key, settled in every language; a
   ``null`` is a value, never a missing key, and no value but a string reaches a source.

Then the repository itself: its sources merge strictly, the four ``base`` catalogues hold the same keys, every source
is in the generator's format, ``load_catalog`` reads this checkout without a build and without fallback, git ignores
the generated files and none of their sources, and the index never tracks the generated files beside the sources. Each
of those checks first proves on a synthetic tree that it can fail.

PURE: synthetic trees and git repositories under ``tmp_path``; the repository is only read, and asked about with
``git check-ignore``. No database, no server, no network, no application import.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import os
import stat
import subprocess
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts import i18n_catalog as catalog
from scripts.i18n_catalog import CatalogError

REPO_ROOT = Path(__file__).resolve().parents[3]
UI_LANGUAGES = ("en", "it", "fr", "es")

# The layout, spelled out: these paths are the contract with the app's loader and with the plugin folders.
I18N = "frontend/src/lib/i18n"
SERVICES = "backend/app/services"
BASE_DIR = f"{I18N}/base"
RISK_DIR = f"{I18N}/risk"
CHARTS_DIR = f"{I18N}/riskcharts"
STRESS_DIR = f"{SERVICES}/probe_plugins/stress/i18n"
VAR_DIR = f"{SERVICES}/probe_plugins/var/i18n"
ACME_DIR = f"{SERVICES}/probe_providers/acme/i18n"
FRESH_DIR = f"{SERVICES}/probe_plugins/fresh/i18n"
STAMP = f"{I18N}/.generated"

# A modification time long past (2001): what a call writes is what no longer carries it.
AGED_NS = 10**18

# =============================================================================
# The synthetic catalogue
# =============================================================================

# base; the subsystem risk, and riskcharts whose prefix lies inside risk's; three plugins, two of them under the same
# ancestor and inside risk's prefix, one outside any prefix.
BASE = {
    "en": {"common": {"ok": "OK", "cancel": "Cancel"}, "app": {"title": "Folio — “yours”"}},
    "it": {"common": {"ok": "OK", "cancel": "Annulla"}, "app": {"title": "Folio — «tuo»"}},
}
RISK_PREFIXES = "# The risk subsystem: analyses and their errors.\n\nrisk   # every risk.* key nobody more specific claims\n#hidden\n"
RISK = {
    "en": {"risk": {"title": "Risk", "errors": {"flat": "Flat series"}}},
    "it": {"risk": {"title": "Rischio", "errors": {"flat": "Serie piatta"}}},
}
CHARTS = {
    "en": {"risk": {"charts": {"legend": "Legend"}}},
    "it": {"risk": {"charts": {"legend": "Legenda"}}},
}
STRESS = {
    "en": {"risk": {"analytics": {"stress": {"title": "Stress test", "shock": "Shock of {pct}%"}}}},
    "it": {"risk": {"analytics": {"stress": {"title": "Prova di stress", "shock": "Shock del {pct}%"}}}},
}
VAR = {
    "en": {"risk": {"analytics": {"var": {"title": "Value at risk"}}}},
    "it": {"risk": {"analytics": {"var": {"title": "Valore a rischio"}}}},
}
ACME = {
    "en": {"brimPlugins": {"acme": {"name": "Acme Bank"}}},
    "it": {"brimPlugins": {"acme": {"name": "Banca Acme"}}},
}
OWNERS = {
    "common.ok": "base",
    "common.cancel": "base",
    "app.title": "base",
    "risk.title": "risk",
    "risk.errors.flat": "risk",
    "risk.charts.legend": "riskcharts",
    "risk.analytics.stress.title": "probe_plugins/stress",
    "risk.analytics.stress.shock": "probe_plugins/stress",
    "risk.analytics.var.title": "probe_plugins/var",
    "brimPlugins.acme.name": "probe_providers/acme",
}
SOURCES = ["base", "risk", "riskcharts", "probe_plugins/stress", "probe_plugins/var", "probe_providers/acme"]


def dumps(nested: dict) -> str:
    """The generator's format, written out here rather than borrowed from the library: rule 4 is what it states."""
    return json.dumps(nested, ensure_ascii=False, indent=2) + "\n"


def write(root: Path, relative: str, text: str) -> Path:
    """Write a file as a person would: a generated catalogue is read-only, so its mode is lifted first."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o644)
    path.write_text(text, encoding="utf-8")
    return path


def read(root: Path, relative: str) -> OrderedDict:
    return json.loads((root / relative).read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def write_catalogs(root: Path, folder: str, catalogs: dict[str, dict]) -> None:
    for language, nested in catalogs.items():
        write(root, f"{folder}/{language}.json", dumps(nested))


def make_subsystem(root: Path, name: str, prefixes: str | None, catalogs: dict[str, dict] | None = None) -> None:
    """A subsystem folder: its ``prefixes.txt`` when given, and its catalogues when given."""
    (root / I18N / name).mkdir(parents=True, exist_ok=True)
    if prefixes is not None:
        write(root, f"{I18N}/{name}/prefixes.txt", prefixes)
    write_catalogs(root, f"{I18N}/{name}", catalogs or {})


def make_plugin(root: Path, name: str, catalogs: dict[str, dict] | None = None) -> None:
    """A plugin folder as U-1 left them, ``__init__.py`` and ``plugin.py``, with its ``i18n/`` when given catalogues."""
    write(root, f"{SERVICES}/{name}/__init__.py", '"""A synthetic plugin."""\n')
    write(root, f"{SERVICES}/{name}/plugin.py", "")
    write_catalogs(root, f"{SERVICES}/{name}/i18n", catalogs or {})


def healthy_tree(root: Path) -> Path:
    write_catalogs(root, BASE_DIR, BASE)
    make_subsystem(root, "risk", RISK_PREFIXES, RISK)
    make_subsystem(root, "riskcharts", "risk.charts\n", CHARTS)
    make_plugin(root, "probe_plugins/stress", STRESS)
    make_plugin(root, "probe_plugins/var", VAR)
    make_plugin(root, "probe_providers/acme", ACME)
    return root


def put(root: Path, folder: str, key: str, values: dict[str, object]) -> None:
    """Set ``key`` in some languages of one source folder, by hand: the library's own setter is under test."""
    for language, value in values.items():
        relative = f"{folder}/{language}.json"
        nested = read(root, relative) if (root / relative).exists() else OrderedDict()
        *parents, leaf = key.split(".")
        node = nested
        for part in parents:
            node = node.setdefault(part, OrderedDict())
        node[leaf] = value
        write(root, relative, dumps(nested))


def drop(root: Path, folder: str, key: str, languages: tuple[str, ...]) -> None:
    """Remove the string ``key`` from some languages of one source folder, by hand, with the branches it empties."""
    for language in languages:
        relative = f"{folder}/{language}.json"
        nested = read(root, relative)
        *parents, leaf = key.split(".")
        trail = []
        node = nested
        for part in parents:
            trail.append((node, part))
            node = node[part]
        del node[leaf]
        for parent, part in reversed(trail):
            if parent[part]:
                break
            del parent[part]
        write(root, relative, dumps(nested))


def merged(root: Path, strict: bool = False) -> catalog.Merged:
    langs, sources = catalog.load(root)
    return catalog.merge(langs, sources, strict=strict, root=root)


def problems_of(root: Path, strict: bool = False) -> list[str]:
    """Every problem that loading and merging ``root``'s sources finds; empty when the catalogue is sound."""
    try:
        merged(root, strict)
    except CatalogError as exc:
        return exc.problems
    return []


def flat(root: Path, strict: bool = False) -> dict[str, dict[str, object]]:
    """The merged catalogue of every language, flat: what must not change when the sources are only rearranged."""
    return {language: dict(catalog.flatten(nested)) for language, nested in merged(root, strict).catalogs.items()}


def owners(root: Path) -> dict[str, str]:
    return {key: source.name for key, source in merged(root).owners.items()}


def _files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file() and ".git" not in path.relative_to(root).parts]


def age(root: Path) -> set[str]:
    """Move every file's modification time far into the past and return the files: what a call writes is what moves."""
    for path in _files(root):
        os.utime(path, ns=(AGED_NS, AGED_NS))
    return {path.relative_to(root).as_posix() for path in _files(root)}


def changes(root: Path, before: set[str]) -> tuple[set[str], set[str]]:
    """``(written, deleted)`` since ``age``: the files created or rewritten, and the ones that disappeared."""
    now = {path.relative_to(root).as_posix(): path for path in _files(root)}
    return {relative for relative, path in now.items() if path.stat().st_mtime_ns != AGED_NS}, before - set(now)


def mode(root: Path, relative: str) -> int:
    return stat.S_IMODE((root / relative).stat().st_mode)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generated(root: Path, language: str) -> str:
    return (root / I18N / f"{language}.json").read_text(encoding="utf-8")


def test_the_layout_is_the_one_the_app_and_the_plugins_use():
    assert catalog.I18N_RELATIVE.as_posix() == I18N
    assert catalog.SERVICES_RELATIVE.as_posix() == SERVICES
    assert (catalog.BASE_NAME, catalog.PREFIXES_FILE, catalog.STAMP_NAME, catalog.SOURCE_LANGUAGE) == ("base", "prefixes.txt", ".generated", "en")


# =============================================================================
# 1. Ownership
# =============================================================================


def test_every_key_belongs_to_the_owner_the_rule_names(tmp_path):
    """Plugins own what they hold, inside a subsystem's prefix too; risk.charts goes to the longer prefix; base keeps
    the rest. Every source is found, and the merge is clean even when strict."""
    root = healthy_tree(tmp_path)

    result = merged(root, strict=True)

    assert {key: source.name for key, source in result.owners.items()} == OWNERS
    assert result.warnings == []
    assert [source.name for source in catalog.load(root)[1]] == SOURCES


@pytest.mark.parametrize(
    ("folder", "key", "problem"),
    [
        pytest.param(STRESS_DIR, "risk.analytics.stress.note", None, id="a-plugin-holds-a-key-inside-a-subsystem-prefix"),
        pytest.param(BASE_DIR, "risk.analytics.stress.note", "risk.analytics.stress.note: is in 'base', but its prefix belongs to 'risk'", id="the-same-key-in-base-is-misplaced"),
        pytest.param(CHARTS_DIR, "risk.charts.axis", None, id="the-longest-prefix-holds-its-key"),
        pytest.param(RISK_DIR, "risk.charts.axis", "risk.charts.axis: is in 'risk', but its prefix belongs to 'riskcharts'", id="the-shorter-prefix-does-not"),
        pytest.param(CHARTS_DIR, "risk.title2", "risk.title2: is in 'riskcharts', but its prefix belongs to 'risk'", id="the-longer-prefix-claims-only-its-own"),
        pytest.param(BASE_DIR, "riskier.note", None, id="a-prefix-claims-whole-segments"),
        pytest.param(RISK_DIR, "riskier.note", "riskier.note: is in 'risk', but its prefix belongs to 'base'", id="riskier-is-not-under-risk"),
        pytest.param(RISK_DIR, "common.close", "common.close: is in 'risk', but its prefix belongs to 'base'", id="no-prefix-means-base"),
    ],
)
def test_a_key_sits_in_the_folder_the_rule_names(tmp_path, folder, key, problem):
    root = healthy_tree(tmp_path)

    put(root, folder, key, {"en": "x", "it": "x"})

    assert problems_of(root) == ([problem] if problem else [])


def test_a_commented_prefix_claims_nothing(tmp_path):
    root = healthy_tree(tmp_path)
    put(root, BASE_DIR, "hidden.note", {"en": "x", "it": "x"})

    assert catalog.read_prefixes(root / RISK_DIR / "prefixes.txt") == ("risk",)
    assert problems_of(root) == []

    write(root, f"{RISK_DIR}/prefixes.txt", RISK_PREFIXES.replace("#hidden", "hidden"))

    assert problems_of(root) == ["hidden.note: is in 'base', but its prefix belongs to 'risk'"]


# =============================================================================
# 2. Defects: errors, even when building, all reported at once
# =============================================================================


def _key_in_two_sources(root: Path) -> None:
    put(root, RISK_DIR, "risk.analytics.var.title", {"en": "VaR", "it": "VaR"})


def _misplaced(root: Path) -> None:
    put(root, BASE_DIR, "risk.errors.nan", {"en": "Not a number", "it": "Non è un numero"})


def _prefix_declared_twice(root: Path) -> None:
    write(root, f"{CHARTS_DIR}/prefixes.txt", "risk.charts\nrisk\n")


def _prefix_repeated_in_one_subsystem(root: Path) -> None:
    write(root, f"{RISK_DIR}/prefixes.txt", RISK_PREFIXES + "risk   # once more\n")


def _subsystem_without_prefixes_file(root: Path) -> None:
    make_subsystem(root, "orphan", None, {"en": {"orphan": {"x": "X"}}, "it": {"orphan": {"x": "X"}}})


def _subsystem_with_only_comments(root: Path) -> None:
    make_subsystem(root, "orphan", "# to be declared\n\n", {"en": {"orphan": {"x": "X"}}, "it": {"orphan": {"x": "X"}}})


def _subsystem_without_english(root: Path) -> None:
    (root / CHARTS_DIR / "en.json").unlink()


def _plugin_without_english(root: Path) -> None:
    (root / STRESS_DIR / "en.json").unlink()


def _key_english_does_not_have(root: Path) -> None:
    put(root, BASE_DIR, "common.extra", {"it": "In più"})


def _unreadable_json(root: Path) -> None:
    write(root, f"{BASE_DIR}/it.json", '{"common": ')


def _language_base_does_not_have(root: Path) -> None:
    write_catalogs(root, STRESS_DIR, {"de": STRESS["en"]})


def _base_without_english(root: Path) -> None:
    (root / BASE_DIR / "en.json").unlink()


def _null_translation(root: Path) -> None:
    put(root, BASE_DIR, "common.ok", {"it": None})


def _number_in_english(root: Path) -> None:
    put(root, ACME_DIR, "brimPlugins.acme.name", {"en": 42})


def _boolean_translation(root: Path) -> None:
    put(root, RISK_DIR, "risk.title", {"it": True})


def _list_translation(root: Path) -> None:
    put(root, VAR_DIR, "risk.analytics.var.title", {"it": ["Valore", "a rischio"]})


DEFECTS = [
    pytest.param(_key_in_two_sources, "risk.analytics.var.title: defined in both 'risk' and 'probe_plugins/var'", id="a-key-in-two-sources"),
    pytest.param(_misplaced, "risk.errors.nan: is in 'base', but its prefix belongs to 'risk'", id="a-key-outside-its-prefix-folder"),
    pytest.param(_prefix_declared_twice, "prefix 'risk' is declared by both 'risk' and 'riskcharts'", id="a-prefix-declared-by-two-subsystems"),
    pytest.param(_prefix_repeated_in_one_subsystem, "prefix 'risk' is declared twice in 'risk'", id="a-prefix-repeated-in-one-subsystem"),
    pytest.param(_subsystem_without_prefixes_file, "frontend/src/lib/i18n/orphan: declares no prefix (prefixes.txt missing or empty)", id="a-subsystem-without-prefixes-txt"),
    pytest.param(_subsystem_with_only_comments, "frontend/src/lib/i18n/orphan: declares no prefix (prefixes.txt missing or empty)", id="a-subsystem-whose-prefixes-are-all-comments"),
    pytest.param(_subsystem_without_english, "frontend/src/lib/i18n/riskcharts/en.json is missing: English is mandatory", id="a-subsystem-without-english"),
    pytest.param(_plugin_without_english, "backend/app/services/probe_plugins/stress/i18n/en.json is missing: English is mandatory", id="a-plugin-without-english"),
    pytest.param(_key_english_does_not_have, "frontend/src/lib/i18n/base/it.json: 1 key(s) English does not have, e.g. common.extra", id="a-key-english-does-not-have"),
    pytest.param(_unreadable_json, "frontend/src/lib/i18n/base/it.json: unreadable JSON (", id="unreadable-json"),
    pytest.param(_language_base_does_not_have, "backend/app/services/probe_plugins/stress/i18n/de.json: 'de' is not one of base's languages ['en', 'it']", id="a-language-base-does-not-have"),
    pytest.param(_base_without_english, "frontend/src/lib/i18n/base/en.json is missing", id="base-without-english"),
    pytest.param(_null_translation, "frontend/src/lib/i18n/base/it.json: 1 value(s) not a string, e.g. common.ok", id="a-null"),
    pytest.param(_number_in_english, "backend/app/services/probe_providers/acme/i18n/en.json: 1 value(s) not a string, e.g. brimPlugins.acme.name", id="a-number"),
    pytest.param(_boolean_translation, "frontend/src/lib/i18n/risk/it.json: 1 value(s) not a string, e.g. risk.title", id="a-boolean"),
    pytest.param(_list_translation, "backend/app/services/probe_plugins/var/i18n/it.json: 1 value(s) not a string, e.g. risk.analytics.var.title", id="a-list"),
]


@pytest.mark.parametrize(("defect", "problem"), DEFECTS)
def test_each_defect_is_refused_by_merge_build_and_check(tmp_path, capsys, defect, problem):
    """The healthy half is the tree before ``defect``: ``test_every_key_belongs_to_the_owner_the_rule_names``."""
    root = healthy_tree(tmp_path)
    defect(root)

    found = problems_of(root, strict=False)

    assert any(problem in line for line in found), f"expected {problem!r} among {found}"
    before = age(root)
    assert catalog.build(root=root, quiet=True) == 1
    assert changes(root, before) == (set(), set())
    assert problem in capsys.readouterr().err
    assert catalog.check(root=root, strict=False) == 1
    assert problem in capsys.readouterr().err


def test_a_null_is_a_value_not_a_missing_translation(tmp_path):
    """Read as missing, a ``null`` would be filled from English when building and reported as missing when strict."""
    root = healthy_tree(tmp_path)
    _null_translation(root)

    assert problems_of(root, strict=True) == ["frontend/src/lib/i18n/base/it.json: 1 value(s) not a string, e.g. common.ok"]


def test_every_merge_problem_is_reported_at_once(tmp_path):
    root = healthy_tree(tmp_path)
    for defect in (_key_in_two_sources, _misplaced, _prefix_declared_twice, _subsystem_without_prefixes_file, _plugin_without_english, _key_english_does_not_have):
        defect(root)
    drop(root, BASE_DIR, "common.cancel", ("it",))

    found = problems_of(root, strict=True)

    expected = [
        "risk.analytics.var.title: defined in both 'risk' and 'probe_plugins/var'",
        "risk.errors.nan: is in 'base', but its prefix belongs to 'risk'",
        "prefix 'risk' is declared by both 'risk' and 'riskcharts'",
        "frontend/src/lib/i18n/orphan: declares no prefix (prefixes.txt missing or empty)",
        "backend/app/services/probe_plugins/stress/i18n/en.json is missing: English is mandatory",
        "frontend/src/lib/i18n/base/it.json: 1 key(s) English does not have, e.g. common.extra",
        "frontend/src/lib/i18n/base/it.json: 1 key(s) missing, e.g. common.cancel",
    ]
    assert [problem for problem in expected if problem not in found] == [], found


def test_every_reading_problem_is_reported_at_once(tmp_path):
    root = healthy_tree(tmp_path)
    _unreadable_json(root)
    _language_base_does_not_have(root)

    found = problems_of(root)

    expected = ["frontend/src/lib/i18n/base/it.json: unreadable JSON (", "backend/app/services/probe_plugins/stress/i18n/de.json: 'de' is not one of base's languages ['en', 'it']"]
    assert [problem for problem in expected if not any(problem in line for line in found)] == [], found


def _plugin_branch_under_a_base_string(root: Path) -> None:
    put(root, ACME_DIR, "common.ok.short", {"en": "x", "it": "x"})


def _plugin_string_over_a_base_branch(root: Path) -> None:
    put(root, ACME_DIR, "app", {"en": "x", "it": "x"})


def _a_key_sorting_between_the_string_and_its_branch(root: Path) -> None:
    assert sorted(["common.ok.short", "common.ok-x", "common.ok"]) == ["common.ok", "common.ok-x", "common.ok.short"], "premise: '-' sorts before '.'"
    put(root, BASE_DIR, "common.ok-x", {"en": "x", "it": "x"})
    _plugin_branch_under_a_base_string(root)


def _a_dotted_name_in_the_same_source(root: Path) -> None:
    for language in ("en", "it"):
        nested = read(root, f"{BASE_DIR}/{language}.json")
        nested["common"]["ok.short"] = "x"
        write(root, f"{BASE_DIR}/{language}.json", dumps(nested))


@pytest.mark.parametrize(
    ("clash", "problem"),
    [
        pytest.param(_plugin_branch_under_a_base_string, "common.ok: a string in 'base' and a branch in 'probe_providers/acme' (common.ok.short)", id="the-string-in-base"),
        pytest.param(_plugin_string_over_a_base_branch, "app: a string in 'probe_providers/acme' and a branch in 'base' (app.title)", id="the-branch-in-base"),
        pytest.param(_a_key_sorting_between_the_string_and_its_branch, "common.ok: a string in 'base' and a branch in 'probe_providers/acme' (common.ok.short)", id="a-key-sorting-between-them"),
        pytest.param(_a_dotted_name_in_the_same_source, "common.ok: a string in 'base' and a branch in 'base' (common.ok.short)", id="in-the-same-source"),
    ],
)
def test_a_string_against_a_branch_is_reported_with_the_other_problems(tmp_path, clash, problem):
    """A key whose parent, or whose children, another source holds (or the same one, through a dotted JSON name). The
    clash is reported as the others are and together with them, whatever sorts between the string and its branch; the
    merge never stops at it."""
    root = healthy_tree(tmp_path)
    clash(root)
    _misplaced(root)

    found = problems_of(root)

    assert problem in found and "risk.errors.nan: is in 'base', but its prefix belongs to 'risk'" in found, found
    before = age(root)
    assert catalog.build(root=root, quiet=True) == 1
    assert changes(root, before) == (set(), set())


# =============================================================================
# 3. A missing translation: English and a warning when building, an error when strict
# =============================================================================


def test_a_missing_translation_is_filled_from_english_with_a_warning_when_building(tmp_path):
    root = healthy_tree(tmp_path)
    drop(root, BASE_DIR, "common.cancel", ("it",))

    result = merged(root, strict=False)

    assert catalog.flatten(result.catalogs["it"])["common.cancel"] == "Cancel"
    assert result.warnings == ["frontend/src/lib/i18n/base/it.json: 1 key(s) missing, e.g. common.cancel (English used)"]


def test_a_missing_translation_is_an_error_when_strict(tmp_path):
    root = healthy_tree(tmp_path)
    drop(root, BASE_DIR, "common.cancel", ("it",))

    assert problems_of(root, strict=True) == ["frontend/src/lib/i18n/base/it.json: 1 key(s) missing, e.g. common.cancel"]


def test_a_plugin_without_a_language_is_filled_whole_when_building_and_refused_when_strict(tmp_path):
    """D-4: the build falls back on English with a warning; the audit fails when one of our plugins lacks a language."""
    root = healthy_tree(tmp_path)
    (root / VAR_DIR / "it.json").unlink()

    lenient = merged(root, strict=False)

    assert catalog.flatten(lenient.catalogs["it"])["risk.analytics.var.title"] == "Value at risk"
    assert lenient.warnings == ["backend/app/services/probe_plugins/var/i18n/it.json: 1 key(s) missing, e.g. risk.analytics.var.title (English used)"]
    assert problems_of(root, strict=True) == ["backend/app/services/probe_plugins/var/i18n/it.json: 1 key(s) missing, e.g. risk.analytics.var.title"]


def test_build_fills_and_check_refuses_by_default(tmp_path, capsys):
    root = healthy_tree(tmp_path)
    drop(root, BASE_DIR, "common.cancel", ("it",))
    missing = "frontend/src/lib/i18n/base/it.json: 1 key(s) missing, e.g. common.cancel"

    assert catalog.check(root=root) == 1
    assert missing in capsys.readouterr().err
    assert catalog.check(root=root, strict=False) == 0
    assert f"{missing} (English used)" in capsys.readouterr().err, "a lenient check warns as the build does"
    assert catalog.build(root=root, strict=True, quiet=True) == 1
    assert not (root / I18N / "it.json").exists()
    assert catalog.build(root=root, quiet=True) == 0
    assert catalog.flatten(read(root, f"{I18N}/it.json"))["common.cancel"] == "Cancel"
    assert f"{missing} (English used)" in capsys.readouterr().err


def test_without_fill_a_language_holds_only_the_translations_its_sources_have(tmp_path):
    root = healthy_tree(tmp_path)
    drop(root, BASE_DIR, "common.cancel", ("it",))
    (root / VAR_DIR / "it.json").unlink()
    langs, sources = catalog.load(root)

    bare = catalog.merge(langs, sources, root=root, fill=False)

    italian = catalog.flatten(bare.catalogs["it"])
    assert ("common.cancel" in italian, "risk.analytics.var.title" in italian, italian["common.ok"]) == (False, False, "OK")
    assert set(catalog.flatten(bare.catalogs["en"])) == set(OWNERS)
    assert bare.warnings == [], "nothing filled, nothing to warn about"
    with pytest.raises(CatalogError) as caught:
        catalog.merge(langs, sources, root=root, fill=False, strict=True)
    assert caught.value.problems == [
        "frontend/src/lib/i18n/base/it.json: 1 key(s) missing, e.g. common.cancel",
        "backend/app/services/probe_plugins/var/i18n/it.json: 1 key(s) missing, e.g. risk.analytics.var.title",
    ]


@pytest.mark.parametrize(
    ("fallback", "cancel", "var_title"),
    [
        pytest.param(True, "Cancel", "Value at risk", id="with-fallback-what-the-build-ships"),
        pytest.param(False, None, None, id="without-fallback-what-the-sources-hold"),
    ],
)
def test_load_catalog_falls_back_on_english_only_when_asked(tmp_path, fallback, cancel, var_title):
    root = healthy_tree(tmp_path)
    drop(root, BASE_DIR, "common.cancel", ("it",))
    (root / VAR_DIR / "it.json").unlink()

    italian = catalog.flatten(catalog.load_catalog("it", root=root, fallback=fallback))

    assert (italian.get("common.cancel"), italian.get("risk.analytics.var.title"), italian["common.ok"]) == (cancel, var_title, "OK")
    assert catalog.load_catalog("en", root=root, fallback=fallback) == catalog.load_catalog("en", root=root), "English is whole either way"


# =============================================================================
# 4. Merge order and byte format
# =============================================================================

# One source, non-ASCII text, keys out of alphabetical order, and an Italian file whose order is not English's.
ONE_SOURCE = {
    "en": {"zeta": {"z": "Last letter, first key"}, "alpha": {"quote": "He said “hi” — and left / stayed", "emoji": "📈 up", "escaped": 'a "quoted" \\ backslash'}},
    "it": {"alpha": {"emoji": "📈 su", "escaped": 'una \\ barra e "virgolette"', "quote": "Ha detto «ciao» — e se n’è andato / rimasto"}, "zeta": {"z": "Ultima lettera, prima chiave"}},
}


def test_a_single_source_comes_back_byte_for_byte(tmp_path):
    root = tmp_path
    write_catalogs(root, BASE_DIR, ONE_SOURCE)
    assert list(ONE_SOURCE["it"]) != list(ONE_SOURCE["en"]), "premise: each language keeps its own order"

    assert catalog.build(root=root, quiet=True) == 0

    for language in ONE_SOURCE:
        source = (root / BASE_DIR / f"{language}.json").read_bytes()
        assert (root / I18N / f"{language}.json").read_bytes() == source
        assert dumps(catalog.load_catalog(language, root=root)).encode("utf-8") == source


def test_sources_merge_base_then_subsystems_by_name_then_plugins_by_path(tmp_path):
    """Each source in its own order and language; a key whose branch exists already joins it."""
    root = tmp_path
    write_catalogs(root, BASE_DIR, {"en": {"zeta": "Z", "alpha": {"b": "B"}}, "it": {"alpha": {"b": "Bi"}, "zeta": "Zi"}})
    make_subsystem(root, "b_sub", "bsub\n", {"en": {"bsub": {"k": "b"}}, "it": {"bsub": {"k": "bi"}}})
    make_subsystem(root, "a_sub", "asub\n", {"en": {"asub": {"k": "a"}}, "it": {"asub": {"k": "ai"}}})
    make_plugin(root, "zz_providers/aa", {"en": {"p2": "P2", "alpha": {"c": "C"}}, "it": {"p2": "P2i", "alpha": {"c": "Ci"}}})
    make_plugin(root, "aa_plugins/zz", {"en": {"p1": "P1"}, "it": {"p1": "P1i"}})

    assert catalog.build(root=root, quiet=True) == 0

    assert generated(root, "en") == dumps({"zeta": "Z", "alpha": {"b": "B", "c": "C"}, "asub": {"k": "a"}, "bsub": {"k": "b"}, "p1": "P1", "p2": "P2"})
    assert generated(root, "it") == dumps({"alpha": {"b": "Bi", "c": "Ci"}, "zeta": "Zi", "asub": {"k": "ai"}, "bsub": {"k": "bi"}, "p1": "P1i", "p2": "P2i"})


# =============================================================================
# 5. build: only what changed, read-only, stamped, refuses a hand edit
# =============================================================================


def test_build_writes_every_language_read_only_beside_its_sha256_stamp(tmp_path):
    root = healthy_tree(tmp_path)

    assert catalog.build(root=root, quiet=True) == 0

    result = merged(root)
    texts = {language: generated(root, language) for language in ("en", "it")}
    assert texts == {language: dumps(result.catalogs[language]) for language in ("en", "it")}
    assert {language: mode(root, f"{I18N}/{language}.json") for language in texts} == {"en": 0o444, "it": 0o444}
    assert (root / STAMP).read_text(encoding="utf-8") == json.dumps({language: sha256(text) for language, text in texts.items()}, indent=2, sort_keys=True) + "\n"
    assert sorted(path.name for path in (root / I18N).iterdir() if path.is_file()) == [".generated", "en.json", "it.json"]
    assert catalog.generated_catalogs(root) == [root / I18N / "en.json", root / I18N / "it.json"], "the files build writes, by its own account"
    assert [source.name for source in catalog.load(root)[1]] == SOURCES, "a generated file is never read back as a source"


@pytest.mark.parametrize("base_languages", [pytest.param((), id="no-base-folder"), pytest.param(("it", "fr"), id="base-without-english")])
def test_generated_catalogs_are_none_without_an_english_base(tmp_path, base_languages):
    """No ``base/en.json``, nothing to build from: no generated file is expected, and asking never raises. The staleness
    probe of ``scripts/cli_base.py`` asks it on any tree, a catalogue or not."""
    for language in base_languages:
        write(tmp_path, f"{BASE_DIR}/{language}.json", "{}\n")

    assert catalog.generated_catalogs(tmp_path) == []


def test_generated_catalogs_follow_the_languages_of_base_english_first(tmp_path):
    """One file per language of ``base``: en, it, fr, es, then any other by name."""
    for language in ("pt", "es", "fr", "it", "en", "de"):
        write(tmp_path, f"{BASE_DIR}/{language}.json", "{}\n")

    assert catalog.generated_catalogs(tmp_path) == [tmp_path / I18N / f"{language}.json" for language in ("en", "it", "fr", "es", "de", "pt")]


def test_build_is_idempotent_and_rewrites_only_the_language_that_changed(tmp_path, capsys):
    root = healthy_tree(tmp_path)
    assert catalog.build(root=root) == 0
    stamp = json.loads((root / STAMP).read_text(encoding="utf-8"))

    before = age(root)
    assert catalog.build(root=root) == 0
    assert changes(root, before) == (set(), set())
    assert "up to date" in capsys.readouterr().out

    put(root, BASE_DIR, "common.cancel", {"it": "Chiudi"})
    before = age(root)
    assert catalog.build(root=root) == 0
    assert changes(root, before) == ({f"{I18N}/it.json", STAMP}, set())
    assert "rewrote it" in capsys.readouterr().out
    restamped = json.loads((root / STAMP).read_text(encoding="utf-8"))
    assert (restamped["en"], restamped["it"]) == (stamp["en"], sha256(generated(root, "it")))
    assert restamped["it"] != stamp["it"]


def test_build_refuses_a_hand_edited_catalogue_and_writes_nothing_unless_forced(tmp_path, capsys):
    root = healthy_tree(tmp_path)
    assert catalog.build(root=root, quiet=True) == 0
    put(root, BASE_DIR, "common.retry", {"en": "Retry", "it": "Riprova"})  # the sources move on, en.json is stale...
    write(root, f"{I18N}/it.json", generated(root, "it").replace("Annulla", "Annulla!"))  # ...and someone edits it.json

    before = age(root)
    assert catalog.build(root=root, quiet=True) == 1
    assert changes(root, before) == (set(), set()), "not even the stale en.json may be written"
    refusal = capsys.readouterr().err
    assert "frontend/src/lib/i18n/it.json" in refusal and "dev.py i18n where" in refusal

    assert catalog.build(root=root, force=True, quiet=True) == 0
    result = merged(root)
    texts = {language: generated(root, language) for language in ("en", "it")}
    assert texts == {language: dumps(result.catalogs[language]) for language in ("en", "it")}
    assert {language: mode(root, f"{I18N}/{language}.json") for language in texts} == {"en": 0o444, "it": 0o444}
    assert json.loads((root / STAMP).read_text(encoding="utf-8")) == {language: sha256(text) for language, text in texts.items()}


def test_build_takes_a_generated_file_that_already_holds_the_new_text(tmp_path):
    """Neither the stamped text nor a hand edit: the new text itself is not refused, and is not written twice."""
    root = healthy_tree(tmp_path)
    assert catalog.build(root=root, quiet=True) == 0
    put(root, BASE_DIR, "common.retry", {"en": "Retry", "it": "Riprova"})
    write(root, f"{I18N}/it.json", dumps(merged(root).catalogs["it"]))

    before = age(root)
    assert catalog.build(root=root, quiet=True) == 0
    assert changes(root, before) == ({f"{I18N}/en.json", STAMP}, set())


def test_build_without_a_stamp_takes_the_file_it_finds_as_its_own(tmp_path):
    """The first build of a checkout: no stamp, so no evidence of a hand edit; the file found is replaced."""
    root = healthy_tree(tmp_path)
    write(root, f"{I18N}/en.json", '{"legacy": "a catalogue no build wrote"}\n')

    assert catalog.build(root=root, quiet=True) == 0

    assert generated(root, "en") == dumps(merged(root).catalogs["en"])


# =============================================================================
# 6. Where a new key goes: route, where, set_key
# =============================================================================


@pytest.mark.parametrize(
    ("key", "owner"),
    [
        pytest.param("risk.analytics.stress.note", "probe_plugins/stress", id="the-plugin-whose-branch-holds-the-ancestor"),
        pytest.param("brimPlugins.acme.description", "probe_providers/acme", id="a-plugin-outside-any-prefix"),
        pytest.param("risk.errors.nan", "risk", id="an-ancestor-a-subsystem-holds-then-the-prefix"),
        pytest.param("risk.charts.axis", "riskcharts", id="the-longest-prefix"),
        pytest.param("risk.brandnew.title", "risk", id="an-ancestor-shared-by-subsystems-and-plugins-then-the-prefix"),
        pytest.param("common.close", "base", id="an-ancestor-in-base"),
        pytest.param("newspace.key", "base", id="no-ancestor-no-prefix"),
        pytest.param("toplevel", "base", id="a-top-level-key"),
    ],
)
def test_route_names_where_a_new_key_goes(tmp_path, key, owner):
    root = healthy_tree(tmp_path)
    langs, sources = catalog.load(root)

    assert catalog.route(key, sources, catalog.merge(langs, sources, root=root).owners).name == owner


def refused(key: str, ancestor: str, plugins: str) -> str:
    """How ``route`` refuses a key only a plugin could own."""
    return f"{key}: the keys under '{ancestor}' belong to plugins ({plugins}); name the target with --into <family>/<plugin>"


@pytest.mark.parametrize(
    ("key", "problem"),
    [
        pytest.param("brimPlugins.newbroker.name", refused("brimPlugins.newbroker.name", "brimPlugins", "probe_providers/acme"), id="one-plugin-whose-branch-lies-deeper-than-the-ancestor"),
        pytest.param("risk.analytics.newone.title", refused("risk.analytics.newone.title", "risk.analytics", "probe_plugins/stress, probe_plugins/var"), id="several-plugins-under-the-ancestor"),
    ],
)
def test_route_where_and_set_key_refuse_a_key_only_a_plugin_could_own(tmp_path, key, problem):
    """A new plugin, or a new field beside several plugins: no guess is safe. ``where`` and ``set_key`` without
    ``--into`` refuse alike, and nothing is written."""
    root = healthy_tree(tmp_path)
    langs, sources = catalog.load(root)
    owners_now = catalog.merge(langs, sources, root=root).owners
    before = age(root)

    with pytest.raises(CatalogError) as routed:
        catalog.route(key, sources, owners_now)
    with pytest.raises(CatalogError) as located:
        catalog.where(key, root=root)
    with pytest.raises(CatalogError) as added:
        catalog.set_key(key, {"en": "New", "it": "Nuovo"}, root=root)

    assert routed.value.problems == located.value.problems == added.value.problems == [problem]
    assert changes(root, before) == (set(), set())


@pytest.mark.parametrize(
    ("english", "namespace"),
    [
        pytest.param(STRESS["en"], "risk.analytics.stress", id="one-branch"),
        pytest.param({"x": {"a": {"b": "1", "c": {"d": "2"}}}}, "x.a", id="the-common-part-of-parents-at-different-depths"),
        pytest.param({"brimPlugins": {"acme": {"name": "A"}}, "importWizard": {"brimNotice": {"acme_x": "X"}}}, None, id="two-branches"),
        pytest.param({"p1": "P1", "p2": "P2"}, None, id="top-level-keys-only"),
        pytest.param(None, None, id="no-english"),
    ],
)
def test_plugin_namespace_is_the_branch_its_keys_share(english, namespace):
    source = catalog.Source("plugin", "probe_plugins/x", Path("unused"), catalogs={"en": english} if english is not None else {})

    assert catalog.plugin_namespace(source) == namespace


# The shapes of the real catalogue, as the coordinator's rehearsal on it met them, on a synthetic tree.
REAL_SHAPES = {
    "brim_providers/broker_degiro": {"brimPlugins": {"broker_degiro": {"name": "DEGIRO"}}},
    "brim_providers/broker_directa": {"brimPlugins": {"broker_directa": {"name": "Directa", "description": "Directa SIM"}}},
    "brim_providers/broker_fineco": {"brimPlugins": {"broker_fineco": {"name": "Fineco"}}},
    "brim_providers/broker_scalable": {"brimPlugins": {"broker_scalable": {"name": "Scalable Capital"}}},
    "signal_plugins/ema": {"signals": {"ema": {"name": "EMA", "description": "Exponential moving average"}}},
    "asset_source_providers/borsa_italiana": {"assets": {"providerParams": {"borsa_italiana": {"isin": "ISIN"}}}},
    "risk_plugins/stress": {"risk": {"analytics": {"stress": {"name": "Stress test"}}}},
    "risk_plugins/var": {"risk": {"analytics": {"var": {"name": "Value at risk"}}}},
}


@pytest.mark.parametrize(
    ("key", "outcome"),
    [
        pytest.param("brimPlugins.broker_directa.extra", "brim_providers/broker_directa", id="a-new-field-of-a-broker"),
        pytest.param("signals.ema.extra", "signal_plugins/ema", id="a-new-field-of-a-signal"),
        pytest.param("brimPlugins.newbroker.name", refused("brimPlugins.newbroker.name", "brimPlugins", "brim_providers/broker_degiro, brim_providers/broker_directa, brim_providers/broker_fineco, …"), id="a-new-broker-three-names-then-an-ellipsis"),
        pytest.param("assets.providerParams.newprovider.foo", refused("assets.providerParams.newprovider.foo", "assets.providerParams", "asset_source_providers/borsa_italiana"), id="a-new-provider-beside-the-only-one"),
        pytest.param("risk.analytics.newone.name", refused("risk.analytics.newone.name", "risk.analytics", "risk_plugins/stress, risk_plugins/var"), id="a-new-analytic"),
        pytest.param("assets.newThing", "assets", id="a-new-key-of-the-assets-subsystem"),
        pytest.param("brandNew.key", "base", id="a-new-namespace"),
    ],
)
def test_route_on_the_shapes_of_the_real_catalogue(tmp_path, key, outcome):
    """``outcome`` is the owner ``route`` names, or its refusal."""
    root = tmp_path
    write_catalogs(root, BASE_DIR, {language: {"common": {"ok": "OK"}} for language in ("en", "it")})
    make_subsystem(root, "assets", "assets\n", {language: {"assets": {"title": "Assets"}} for language in ("en", "it")})
    make_subsystem(root, "signals", "signals\n", {language: {"signals": {"units": {"days": "days"}}} for language in ("en", "it")})
    make_subsystem(root, "risk", "risk\n", {language: {"risk": {"title": "Risk"}} for language in ("en", "it")})
    for name, nested in REAL_SHAPES.items():
        make_plugin(root, name, {"en": nested, "it": nested})
    langs, sources = catalog.load(root)
    owners_now = catalog.merge(langs, sources, root=root, strict=True).owners

    try:
        found = catalog.route(key, sources, owners_now).name
    except CatalogError as exc:
        found = "; ".join(exc.problems)

    assert found == outcome


@pytest.mark.parametrize(
    ("key", "answer"),
    [
        pytest.param("risk.title", "frontend/src/lib/i18n/risk/en.json (exists)", id="an-existing-key"),
        pytest.param("risk.analytics", "branch of 3 key(s) in: probe_plugins/stress, probe_plugins/var", id="a-branch"),
        pytest.param("risk.analytics.stress.note", "backend/app/services/probe_plugins/stress/i18n/en.json (new key)", id="a-new-key-for-a-plugin"),
        pytest.param("newspace.key", "frontend/src/lib/i18n/base/en.json (new key)", id="a-new-key-for-base"),
    ],
)
def test_where_names_the_file_that_holds_or_would_hold_a_key(tmp_path, key, answer):
    assert catalog.where(key, root=healthy_tree(tmp_path)) == answer


def test_set_key_writes_a_new_key_where_route_says_and_nowhere_else(tmp_path):
    root = healthy_tree(tmp_path)
    before = age(root)

    target = catalog.set_key("risk.analytics.stress.note", {"en": "Note", "it": "Nota"}, root=root)

    assert target.name == "probe_plugins/stress"
    assert changes(root, before) == ({f"{STRESS_DIR}/en.json", f"{STRESS_DIR}/it.json"}, set())
    assert owners(root)["risk.analytics.stress.note"] == "probe_plugins/stress"
    assert flat(root, strict=True)["it"]["risk.analytics.stress.note"] == "Nota"


@pytest.mark.parametrize(
    ("into", "key", "folder"),
    [
        pytest.param("base", "common.close", BASE_DIR, id="base"),
        pytest.param("riskcharts", "risk.charts.axis", CHARTS_DIR, id="a-subsystem"),
        pytest.param("probe_plugins/stress", "risk.analytics.stress.note", STRESS_DIR, id="a-plugin"),
        pytest.param("backend/app/services/probe_plugins/stress", "risk.analytics.stress.note", STRESS_DIR, id="a-plugin-by-its-path"),
        pytest.param("backend/app/services/probe_plugins/stress/i18n/", "risk.analytics.stress.note", STRESS_DIR, id="a-plugin-by-its-i18n-path"),
        pytest.param("probe_plugins/fresh", "risk.analytics.fresh.title", FRESH_DIR, id="a-plugin-without-translations-yet"),
        pytest.param("brim_providers/broker_x/i18n", "brimPlugins.broker_x.name", f"{SERVICES}/brim_providers/broker_x/i18n", id="a-new-plugin-by-its-i18n-folder"),
    ],
)
def test_set_key_into_names_base_a_subsystem_or_a_plugin(tmp_path, into, key, folder):
    root = healthy_tree(tmp_path)
    make_plugin(root, "probe_plugins/fresh")
    make_plugin(root, "brim_providers/broker_x")
    before = age(root)

    target = catalog.set_key(key, {"en": "New", "it": "Nuovo"}, into=into, root=root)

    assert target.folder == root / folder
    assert changes(root, before) == ({f"{folder}/en.json", f"{folder}/it.json"}, set())
    assert owners(root)[key] == target.name
    assert problems_of(root, strict=True) == []


def test_set_key_updates_an_existing_key_in_its_owner_only(tmp_path):
    root = healthy_tree(tmp_path)
    before = age(root)

    target = catalog.set_key("risk.analytics.var.title", {"it": "VaR"}, create=False, root=root)

    assert target.name == "probe_plugins/var"
    assert changes(root, before) == ({f"{VAR_DIR}/it.json"}, set())
    values = flat(root, strict=True)
    assert (values["en"]["risk.analytics.var.title"], values["it"]["risk.analytics.var.title"]) == ("Value at risk", "VaR")


@pytest.mark.parametrize(
    ("key", "values", "into", "create", "problem"),
    [
        pytest.param("common.ok", {"en": "Okay"}, None, True, "common.ok: already exists in 'base'", id="adding-a-key-that-exists"),
        pytest.param("risk.analytics.var.subtitle", {"en": "Sub"}, None, False, "risk.analytics.var.subtitle: does not exist", id="updating-a-key-that-does-not"),
        pytest.param("common.close", {"de": "Schließen"}, None, True, "common.close: unknown language 'de'", id="a-language-base-does-not-have"),
        pytest.param("risk.errors.nan", {"en": "NaN", "it": "NaN"}, "base", True, "risk.errors.nan: is in 'base', but its prefix belongs to 'risk'", id="into-a-folder-its-prefix-forbids"),
        pytest.param("common.close", {"en": "Close"}, "nosuch", True, "--into nosuch: no subsystem 'nosuch' (create frontend/src/lib/i18n/nosuch/prefixes.txt first)", id="into-an-unknown-subsystem"),
        pytest.param("risk.analytics.ghost.title", {"en": "Ghost"}, "probe_plugins/ghost", True, "--into probe_plugins/ghost: backend/app/services/probe_plugins/ghost is not a plugin folder (no plugin.py)", id="into-a-folder-without-plugin-py"),
    ],
)
def test_set_key_refuses_whole_and_writes_nothing(tmp_path, key, values, into, create, problem):
    root = healthy_tree(tmp_path)
    write(root, f"{SERVICES}/probe_plugins/ghost/__init__.py", '"""A package without plugin.py: not a plugin."""\n')
    before = age(root)

    with pytest.raises(CatalogError) as caught:
        catalog.set_key(key, values, into=into, root=root, create=create)

    assert problem in caught.value.problems
    assert changes(root, before) == (set(), set())


SHAPE = "a plugin target is <family>/<plugin>, the family one of *_providers, *_plugins"


@pytest.mark.parametrize(
    ("into", "problem"),
    [
        pytest.param("risk/odd", f"--into risk/odd: {SHAPE}", id="a-family-discovery-does-not-read"),
        pytest.param("probe_plugins/stress/nested", f"--into probe_plugins/stress/nested: {SHAPE}", id="a-folder-below-a-plugin"),
        pytest.param("brim_providers/_brim_io", f"--into brim_providers/_brim_io: {SHAPE}", id="a-private-helper"),
        pytest.param("brim_providers/.cache", f"--into brim_providers/.cache: {SHAPE}", id="a-hidden-folder"),
        pytest.param("foo/bar", f"--into foo/bar: {SHAPE}", id="no-plugin-family"),
        pytest.param("brim_providers/static", "--into brim_providers/static: backend/app/services/brim_providers/static is not a plugin folder (no plugin.py)", id="a-data-folder"),
        pytest.param("brim_providers/nope", "--into brim_providers/nope: backend/app/services/brim_providers/nope is not a plugin folder (no plugin.py)", id="a-folder-that-does-not-exist"),
    ],
)
def test_set_key_and_move_take_a_plugin_target_only_where_discovery_reads(tmp_path, into, problem):
    """Discovery reads ``<*_providers|*_plugins>/<plugin>/i18n`` only: anything else would take keys no catalogue reads.
    The first five folders hold a ``plugin.py``, so their shape alone refuses them."""
    root = healthy_tree(tmp_path)
    for folder in ("risk/odd", "probe_plugins/stress/nested", "brim_providers/_brim_io", "brim_providers/.cache", "foo/bar"):
        write(root, f"{SERVICES}/{folder}/plugin.py", "")
    write(root, f"{SERVICES}/brim_providers/static/sample.csv", "date,amount\n")
    before = age(root)

    with pytest.raises(CatalogError) as added:
        catalog.set_key("zz.fresh", {"en": "Fresh", "it": "Fresco"}, into=into, root=root)
    with pytest.raises(CatalogError) as moved:
        catalog.move("risk.analytics.var", into, root=root)

    assert added.value.problems == moved.value.problems == [problem]
    assert changes(root, before) == (set(), set())


# =============================================================================
# 7. Edits that keep the catalogue: move, split, remove_key
# =============================================================================


@pytest.mark.parametrize(
    ("prefix", "into", "count", "written", "deleted"),
    [
        pytest.param("risk.analytics.var", "probe_plugins/stress", 1, {f"{STRESS_DIR}/en.json", f"{STRESS_DIR}/it.json"}, {f"{VAR_DIR}/en.json", f"{VAR_DIR}/it.json"}, id="plugin-to-plugin-emptying-the-first"),
        pytest.param("common", "probe_plugins/fresh", 2, {f"{BASE_DIR}/en.json", f"{BASE_DIR}/it.json", f"{FRESH_DIR}/en.json", f"{FRESH_DIR}/it.json"}, set(), id="base-to-a-plugin-without-translations-yet"),
        pytest.param("brimPlugins", "base", 1, {f"{BASE_DIR}/en.json", f"{BASE_DIR}/it.json"}, {f"{ACME_DIR}/en.json", f"{ACME_DIR}/it.json"}, id="plugin-to-base-emptying-it"),
    ],
)
def test_move_carries_a_subtree_in_every_language_and_keeps_the_catalogue(tmp_path, prefix, into, count, written, deleted):
    root = healthy_tree(tmp_path)
    make_plugin(root, "probe_plugins/fresh")
    expected = flat(root)
    before = age(root)

    assert catalog.move(prefix, into, root=root) == count

    assert changes(root, before) == (written, deleted)
    assert flat(root, strict=True) == expected
    moved = {owner for key, owner in owners(root).items() if key == prefix or key.startswith(prefix + ".")}
    assert moved == {into}
    for relative in deleted:
        i18n_folder = (root / relative).parent
        assert not i18n_folder.exists() and (i18n_folder.parent / "plugin.py").is_file(), f"an emptied plugin source loses its i18n/ folder, never its plugin: {i18n_folder}"


def test_move_puts_keys_where_a_newly_declared_prefix_says(tmp_path):
    root = healthy_tree(tmp_path)
    expected = flat(root)
    make_subsystem(root, "commons", "common\n")
    assert "common.ok: is in 'base', but its prefix belongs to 'commons'" in problems_of(root), "premise: the new prefix leaves base's keys misplaced"

    assert catalog.move("common", "commons", root=root) == 2

    assert flat(root, strict=True) == expected
    assert read(root, f"{I18N}/commons/it.json") == {"common": {"ok": "OK", "cancel": "Annulla"}}
    assert read(root, f"{BASE_DIR}/it.json") == {"app": {"title": "Folio — «tuo»"}}


@pytest.mark.parametrize(
    ("prefix", "into", "problem"),
    [
        pytest.param("risk.errors", "base", "risk.errors.flat: is in 'base', but its prefix belongs to 'risk'", id="into-a-folder-the-prefix-forbids"),
        pytest.param("nothing.here", "base", "no key under 'nothing.here' outside base", id="nothing-to-move"),
        pytest.param("risk.analytics.var", "probe_plugins/ghost", "--into probe_plugins/ghost: backend/app/services/probe_plugins/ghost is not a plugin folder (no plugin.py)", id="into-a-folder-without-plugin-py"),
    ],
)
def test_move_refuses_whole_and_writes_nothing(tmp_path, prefix, into, problem):
    root = healthy_tree(tmp_path)
    before = age(root)

    with pytest.raises(CatalogError) as caught:
        catalog.move(prefix, into, root=root)

    assert problem in caught.value.problems
    assert changes(root, before) == (set(), set())


# U-2's starting point: the whole catalogue in base.
MONOLITH = {
    "en": {"common": {"ok": "OK", "cancel": "Cancel"}, "app": {"title": "Folio — “yours”"}, "risk": {"title": "Risk", "errors": {"flat": "Flat series"}, "charts": {"legend": "Legend"}}},
    "it": {"common": {"ok": "OK", "cancel": "Annulla"}, "app": {"title": "Folio — «tuo»"}, "risk": {"title": "Rischio", "errors": {"flat": "Serie piatta"}, "charts": {"legend": "Legenda"}}},
}


def test_split_puts_every_key_where_the_prefixes_say_and_can_run_again(tmp_path):
    root = tmp_path
    write_catalogs(root, BASE_DIR, MONOLITH)
    make_subsystem(root, "risk", "risk\n")
    make_subsystem(root, "riskcharts", "risk.charts\n")
    make_plugin(root, "probe_plugins/stress", STRESS)  # split never touches a plugin
    expected = {language: {**catalog.flatten(MONOLITH[language]), **catalog.flatten(STRESS[language])} for language in MONOLITH}
    assert "risk.title: is in 'base', but its prefix belongs to 'risk'" in problems_of(root), "premise: the subsystems are declared and still empty"

    before = age(root)
    assert catalog.split(root=root) == {"risk": 2, "riskcharts": 1}
    assert changes(root, before) == ({f"{folder}/{language}.json" for folder in (BASE_DIR, RISK_DIR, CHARTS_DIR) for language in ("en", "it")}, set())
    assert flat(root, strict=True) == expected
    assert read(root, f"{BASE_DIR}/it.json") == {"common": {"ok": "OK", "cancel": "Annulla"}, "app": {"title": "Folio — «tuo»"}}
    assert read(root, f"{RISK_DIR}/en.json") == {"risk": {"title": "Risk", "errors": {"flat": "Flat series"}}}
    assert read(root, f"{CHARTS_DIR}/it.json") == {"risk": {"charts": {"legend": "Legenda"}}}

    before = age(root)
    assert catalog.split(root=root) == {}
    assert changes(root, before) == (set(), set())

    make_subsystem(root, "riskerrors", "risk.errors\n")  # a longer prefix appears: its keys leave risk
    before = age(root)
    assert catalog.split(root=root) == {"riskerrors": 1}
    assert changes(root, before) == ({f"{folder}/{language}.json" for folder in (RISK_DIR, f"{I18N}/riskerrors") for language in ("en", "it")}, set())
    assert flat(root, strict=True) == expected


@pytest.mark.parametrize(
    ("key", "touched", "written", "deleted"),
    [
        pytest.param("common.cancel", ["base"], {f"{BASE_DIR}/en.json", f"{BASE_DIR}/it.json"}, set(), id="a-key"),
        pytest.param("risk.errors", ["risk"], {f"{RISK_DIR}/en.json", f"{RISK_DIR}/it.json"}, set(), id="a-branch"),
        pytest.param("risk.analytics", ["probe_plugins/stress", "probe_plugins/var"], set(), {f"{folder}/{language}.json" for folder in (STRESS_DIR, VAR_DIR) for language in ("en", "it")}, id="a-branch-across-the-plugins-it-empties"),
    ],
)
def test_remove_key_removes_a_key_or_a_branch_from_every_source_and_language(tmp_path, key, touched, written, deleted):
    root = healthy_tree(tmp_path)
    before = age(root)

    assert catalog.remove_key(key, root=root) == touched

    assert changes(root, before) == (written, deleted)
    remaining = flat(root, strict=True)
    assert [k for language in remaining for k in remaining[language] if k == key or k.startswith(key + ".")] == []


def test_remove_key_prunes_the_branches_it_empties_and_refuses_a_key_that_is_nowhere(tmp_path):
    root = healthy_tree(tmp_path)

    assert catalog.remove_key("risk.errors.flat", root=root) == ["risk"]
    assert read(root, f"{RISK_DIR}/en.json") == {"risk": {"title": "Risk"}}

    before = age(root)
    with pytest.raises(CatalogError) as caught:
        catalog.remove_key("nothing.here", root=root)
    assert caught.value.problems == ["nothing.here: not found"]
    assert changes(root, before) == (set(), set())


# =============================================================================
# 8. Revisions: catalogs_at, check --against, absorb
# =============================================================================

# The legacy layout: one tracked catalogue per language, frontend/src/lib/i18n/<lang>.json.
LEGACY = {
    "en": {"app": {"title": "App"}, "common": {"ok": "OK", "cancel": "Cancel"}, "risk": {"title": "Risk", "analytics": {"stress": {"title": "Stress"}}}, "old": {"gone": "Gone"}},
    "it": {"app": {"title": "App"}, "common": {"ok": "Va bene", "cancel": "Annulla"}, "risk": {"title": "Rischio", "analytics": {"stress": {"title": "Stress"}}}, "old": {"gone": "Andato"}},
}
# A branch that changed it on the legacy layout: 4 keys added, 4 keys changed in 5 places (app.title in both
# languages, risk.title in English, common.ok and old.gone in Italian), common.cancel removed.
THEIRS = {
    "en": {"app": {"title": "Application"}, "common": {"ok": "OK", "retry": "Retry"}, "risk": {"title": "Risk!", "analytics": {"stress": {"title": "Stress", "subtitle": "Sub"}}, "newkey": "New"}, "old": {"gone": "Gone"}, "brandnew": {"key": "Brand new"}},
    "it": {"app": {"title": "Applicazione"}, "common": {"ok": "Ok", "retry": "Riprova"}, "risk": {"title": "Rischio", "analytics": {"stress": {"title": "Stress", "subtitle": "Sotto"}}, "newkey": "Nuovo"}, "old": {"gone": "Sparito"}, "brandnew": {"key": "Nuovissimo"}},
}
ADDED = ("common.retry", "risk.analytics.stress.subtitle", "risk.newkey", "brandnew.key")
# A branch that adds a key route can place (common.retry) and one it cannot: risk.analytics.var.title, beside the stress
# plugin alone, whose branch lies deeper than risk.analytics.
UNROUTABLE = {
    "en": {"app": {"title": "App"}, "common": {"ok": "OK", "cancel": "Cancel", "retry": "Retry"}, "risk": {"title": "Risk", "analytics": {"stress": {"title": "Stress"}, "var": {"title": "Value at risk"}}}, "old": {"gone": "Gone"}},
    "it": {"app": {"title": "App"}, "common": {"ok": "Va bene", "cancel": "Annulla", "retry": "Riprova"}, "risk": {"title": "Rischio", "analytics": {"stress": {"title": "Stress"}, "var": {"title": "Valore a rischio"}}}, "old": {"gone": "Andato"}},
}
# A branch that turns the string common.ok into a branch: only a removal made first leaves room for it.
RESHAPED = {
    "en": {"app": {"title": "App"}, "common": {"ok": {"short": "OK", "long": "Okay"}, "cancel": "Cancel"}, "risk": {"title": "Risk", "analytics": {"stress": {"title": "Stress"}}}, "old": {"gone": "Gone"}},
    "it": {"app": {"title": "App"}, "common": {"ok": {"short": "OK", "long": "Va bene"}, "cancel": "Annulla"}, "risk": {"title": "Rischio", "analytics": {"stress": {"title": "Stress"}}}, "old": {"gone": "Andato"}},
}
# A branch whose JSON names a key "ok.short" beside the string common.ok: a branch under a string.
DOTTED = {language: {**catalogs, "common": {**catalogs["common"], "ok.short": "x"}} for language, catalogs in LEGACY.items()}
# In legacy(): the key is not there.
DROPPED = object()


def legacy(*edits: tuple[str, str, object]) -> dict[str, dict]:
    """LEGACY with ``(language, key, value)`` edits, ``DROPPED`` taking the key out."""
    catalogs = copy.deepcopy(LEGACY)
    for language, key, value in edits:
        *parents, leaf = key.split(".")
        node = catalogs[language]
        for part in parents:
            node = node[part]
        if value is DROPPED:
            del node[leaf]
        else:
            node[leaf] = value
    return catalogs


# HEAD: LEGACY's catalogue as sources, split into base, the risk subsystem and the stress plugin.
OURS_BASE = {
    "en": {"app": {"title": "App"}, "common": {"ok": "OK", "cancel": "Cancel"}, "old": {"gone": "Gone"}},
    "it": {"app": {"title": "App"}, "common": {"ok": "Va bene", "cancel": "Annulla"}, "old": {"gone": "Andato"}},
}
OURS_RISK = {"en": {"risk": {"title": "Risk"}}, "it": {"risk": {"title": "Rischio"}}}
OURS_STRESS = {"en": {"risk": {"analytics": {"stress": {"title": "Stress"}}}}, "it": {"risk": {"analytics": {"stress": {"title": "Stress"}}}}}
SOURCE_FILES = {f"{folder}/{language}.json" for folder in (BASE_DIR, RISK_DIR, STRESS_DIR) for language in ("en", "it")}
CONFLICT = "conflict (base/ours/theirs differ; settle with --prefer ours|theirs)"

# What an enclosing process (a git hook, an editor) or the user's own configuration would bring into a throwaway
# repository: another repository's location, and settings such as signing, hooks, excludes and line ends.
GIT_LOCATION_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR")


@pytest.fixture
def hermetic_git(monkeypatch):
    """Git, for the tests and for the library alike, sees only the repository it is pointed at and its own config."""
    for name in GIT_LOCATION_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo: Path, *args: str) -> str:
    """Git in a throwaway repository; the settings repeat ``hermetic_git`` for a git older than ``GIT_CONFIG_GLOBAL``."""
    settings = ("user.email=t@t", "user.name=t", "commit.gpgsign=false", "core.autocrlf=false", f"core.excludesFile={os.devnull}", f"core.hooksPath={repo / '.no-hooks'}")
    command = ["git", "-C", str(repo)] + [part for setting in settings for part in ("-c", setting)] + list(args)
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def legacy_branch(repo: Path, base: str, name: str, catalogs: dict[str, dict]) -> str:
    """Commit ``catalogs`` on the legacy layout in a branch from ``base``; the sources are checked out again after."""
    git(repo, "checkout", "-q", "-b", name, base)
    write_catalogs(repo, I18N, catalogs)
    git(repo, "commit", "-q", "-a", "-m", name)
    rev = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "sources")
    return rev


@dataclass(frozen=True)
class History:
    """``base`` (the legacy layout) and ``theirs``, a branch from it; HEAD, the branch ``sources`` checked out and clean,
    holds ``base``'s catalogue as sources."""

    repo: Path
    base: str
    theirs: str

    def branch(self, name: str, catalogs: dict[str, dict]) -> str:
        """Another legacy branch from ``base``: call it before touching the working tree."""
        return legacy_branch(self.repo, self.base, name, catalogs)


@pytest.fixture
def history(tmp_path, hermetic_git) -> History:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    write_catalogs(repo, I18N, LEGACY)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "legacy")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "sources")
    git(repo, "rm", "-q", f"{I18N}/en.json", f"{I18N}/it.json")
    write_catalogs(repo, BASE_DIR, OURS_BASE)
    make_subsystem(repo, "risk", "risk\n", OURS_RISK)
    make_plugin(repo, "probe_plugins/stress", OURS_STRESS)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "sources")
    return History(repo, base, legacy_branch(repo, base, "theirs", THEIRS))


def test_catalogs_at_reads_the_legacy_layout_and_the_tracked_sources_alike(history):
    legacy = {language: dict(catalog.flatten(nested)) for language, nested in LEGACY.items()}

    assert catalog.catalogs_at(history.base, root=history.repo) == legacy
    assert catalog.catalogs_at("HEAD", root=history.repo) == legacy
    put(history.repo, BASE_DIR, "common.ok", {"it": "Bene"})
    assert catalog.catalogs_at("HEAD", root=history.repo) == legacy, "a revision is what is tracked, never the working tree"
    assert catalog.compare(catalog.catalogs_at(history.base, root=history.repo), catalog.catalogs_at(history.theirs, root=history.repo)) == [
        "en: 1 missing, 4 extra, 2 changed; e.g. missing common.cancel; e.g. extra common.retry; e.g. changed app.title",
        "it: 1 missing, 4 extra, 3 changed; e.g. missing common.cancel; e.g. extra common.retry; e.g. changed app.title",
    ]


def test_catalogs_at_holds_what_a_revision_has_without_fallback(history):
    drop(history.repo, BASE_DIR, "common.cancel", ("it",))
    git(history.repo, "commit", "-q", "-a", "-m", "no Italian common.cancel")

    at_head = catalog.catalogs_at("HEAD", root=history.repo)

    assert ("common.cancel" in at_head["en"], "common.cancel" in at_head["it"]) == (True, False)


@pytest.mark.parametrize("rev", [pytest.param("nope", id="no-such-name"), pytest.param("HEAD^{tree}", id="an-object-that-is-not-a-commit")])
def test_a_revision_that_is_not_a_commit_is_a_problem_never_a_traceback(history, capsys, monkeypatch, rev):
    problem = f"{rev}: not a commit of this repository"
    before = age(history.repo)

    with pytest.raises(CatalogError) as read_at:
        catalog.catalogs_at(rev, root=history.repo)
    with pytest.raises(CatalogError) as absorbed_from:
        catalog.absorb(rev, history.theirs, root=history.repo)
    with pytest.raises(CatalogError) as absorbed_into:
        catalog.absorb(history.base, rev, root=history.repo)

    assert read_at.value.problems == absorbed_from.value.problems == absorbed_into.value.problems == [problem]
    assert changes(history.repo, before) == (set(), set())
    assert catalog.check(root=history.repo, against=rev) == 1
    assert problem in capsys.readouterr().err
    # main() works on the checkout it ships in: point its check at the throwaway repository.
    monkeypatch.setattr(catalog, "check", functools.partial(catalog.check, root=history.repo))
    assert catalog.main(["check", "--against", rev]) == 1
    assert problem in capsys.readouterr().err


def test_check_against_a_revision_compares_the_working_sources_without_fallback(history, capsys):
    repo = history.repo
    assert catalog.check(root=repo, against=history.base) == 0
    assert catalog.check(root=repo, against=history.theirs) == 1

    put(repo, BASE_DIR, "common.ok", {"it": "Bene"})
    assert catalog.check(root=repo, against=history.base) == 1
    changed = "it: 0 missing, 0 extra, 1 changed; e.g. changed common.ok"
    assert catalog.compare(catalog.catalogs_at(history.base, root=repo), flat(repo)) == [changed]
    assert changed in capsys.readouterr().err

    put(repo, BASE_DIR, "common.ok", {"it": "Va bene"})
    drop(repo, BASE_DIR, "common.cancel", ("it",))
    missing = "frontend/src/lib/i18n/base/it.json: 1 key(s) missing, e.g. common.cancel"
    assert catalog.check(root=repo, strict=False, against=history.base) == 1, "the English fallback must not hide a missing translation"
    lenient = capsys.readouterr().err
    assert f"{missing} (English used)" in lenient and "it: 1 missing, 0 extra, 0 changed; e.g. missing common.cancel" in lenient
    assert catalog.check(root=repo, strict=True, against=history.base) == 1
    assert missing in capsys.readouterr().err


def test_absorb_replays_what_a_legacy_branch_changed_and_a_second_run_finds_it_there(history):
    """Counts are keys: app.title, changed in two languages, counts once; an added key counts once, decided on English."""
    before = age(history.repo)

    assert catalog.absorb(history.base, history.theirs, root=history.repo) == {"added": 4, "changed": 4, "removed": 1, "already": 0, "conflicts": 0}

    assert changes(history.repo, before) == (SOURCE_FILES, set())
    assert catalog.compare(catalog.catalogs_at(history.theirs, root=history.repo), flat(history.repo, strict=True)) == []
    assert {key: owner for key, owner in owners(history.repo).items() if key in ADDED} == {
        "common.retry": "base",
        "risk.analytics.stress.subtitle": "probe_plugins/stress",
        "risk.newkey": "risk",
        "brandnew.key": "base",
    }
    assert (read(history.repo, f"{BASE_DIR}/en.json")["common"], read(history.repo, f"{BASE_DIR}/it.json")["common"]) == ({"ok": "OK", "retry": "Retry"}, {"ok": "Ok", "retry": "Riprova"})

    before = age(history.repo)
    assert catalog.absorb(history.base, history.theirs, root=history.repo) == {"added": 0, "changed": 0, "removed": 0, "already": 9, "conflicts": 0}
    assert changes(history.repo, before) == (set(), set())


def test_absorb_counts_what_ours_already_has_and_changes_only_the_rest(history):
    """Ours already holds risk.newkey, in the stress plugin where route would not put it (it stays there), and the English
    app.title; its Italian is still to change, so app.title counts once, as changed."""
    put(history.repo, STRESS_DIR, "risk.newkey", {"en": "New", "it": "Nuovo"})
    put(history.repo, BASE_DIR, "app.title", {"en": "Application"})

    assert catalog.absorb(history.base, history.theirs, root=history.repo) == {"added": 3, "changed": 4, "removed": 1, "already": 1, "conflicts": 0}

    assert owners(history.repo)["risk.newkey"] == "probe_plugins/stress"
    assert catalog.compare(catalog.catalogs_at(history.theirs, root=history.repo), flat(history.repo, strict=True)) == []


def test_absorb_reads_ours_without_fallback(history):
    """Ours has no Italian common.cancel, which theirs removes: absent on both sides, so already done; read with the
    English fallback, ours would hold "Cancel" there and make a conflict out of nothing."""
    drop(history.repo, BASE_DIR, "common.cancel", ("it",))

    assert catalog.absorb(history.base, history.theirs, root=history.repo) == {"added": 4, "changed": 4, "removed": 1, "already": 0, "conflicts": 0}

    assert catalog.compare(catalog.catalogs_at(history.theirs, root=history.repo), flat(history.repo, strict=True)) == []


def _ours_disagrees(history: History) -> None:
    """Ours added risk.newkey with other words than theirs, and changed the Italian common.ok another way."""
    put(history.repo, STRESS_DIR, "risk.newkey", {"en": "Fresh", "it": "Fresco"})
    put(history.repo, BASE_DIR, "common.ok", {"it": "Bene"})


def test_absorb_reports_every_conflict_and_writes_nothing(history):
    _ours_disagrees(history)
    before = age(history.repo)

    with pytest.raises(CatalogError) as caught:
        catalog.absorb(history.base, history.theirs, root=history.repo)

    assert caught.value.problems == [
        f'{CONFLICT}: en risk.newkey: base (absent), ours "Fresh", theirs "New"',
        f'{CONFLICT}: it common.ok: base "Va bene", ours "Bene", theirs "Ok"',
        f'{CONFLICT}: it risk.newkey: base (absent), ours "Fresco", theirs "Nuovo"',
    ]
    assert changes(history.repo, before) == (set(), set())


@pytest.mark.parametrize(
    ("prefer", "counts", "kept"),
    [
        pytest.param("ours", {"added": 3, "changed": 3, "removed": 1, "already": 0, "conflicts": 3}, {"en": {"risk.newkey": "Fresh"}, "it": {"common.ok": "Bene", "risk.newkey": "Fresco"}}, id="ours"),
        pytest.param("theirs", {"added": 3, "changed": 5, "removed": 1, "already": 0, "conflicts": 3}, {"en": {}, "it": {}}, id="theirs"),
    ],
)
def test_absorb_prefer_settles_every_conflict_one_way(history, prefer, counts, kept):
    _ours_disagrees(history)

    assert catalog.absorb(history.base, history.theirs, root=history.repo, prefer=prefer) == counts

    assert flat(history.repo, strict=True) == {language: {**catalog.flatten(THEIRS[language]), **kept[language]} for language in THEIRS}
    assert owners(history.repo)["risk.newkey"] == "probe_plugins/stress"


def test_absorb_refuses_a_preference_it_does_not_know(history):
    before = age(history.repo)

    with pytest.raises(CatalogError) as caught:
        catalog.absorb(history.base, history.theirs, root=history.repo, prefer="both")

    assert caught.value.problems == ["--prefer both: expected 'ours' or 'theirs'"]
    assert changes(history.repo, before) == (set(), set())


def _ours_removed_old_gone(history: History) -> None:
    drop(history.repo, BASE_DIR, "old.gone", ("en", "it"))


def _ours_changed_the_italian_cancel(history: History) -> None:
    put(history.repo, BASE_DIR, "common.cancel", {"it": "Chiudi"})


def test_absorb_treats_a_change_to_a_key_ours_removed_as_one_conflict_about_the_whole_key(history):
    _ours_removed_old_gone(history)
    before = age(history.repo)

    with pytest.raises(CatalogError) as caught:
        catalog.absorb(history.base, history.theirs, root=history.repo)

    assert caught.value.problems == [f'{CONFLICT}: old.gone: removed by ours, while theirs changed it: it "Andato" → "Sparito"']
    assert changes(history.repo, before) == (set(), set())


@pytest.mark.parametrize(
    ("ours", "prefer", "key", "kept", "counts"),
    [
        pytest.param(_ours_removed_old_gone, "ours", "old.gone", None, {"added": 4, "changed": 3, "removed": 1, "already": 0, "conflicts": 1}, id="ours-removed-what-theirs-changed-prefer-ours"),
        pytest.param(_ours_removed_old_gone, "theirs", "old.gone", {"en": "Gone", "it": "Sparito"}, {"added": 5, "changed": 3, "removed": 1, "already": 0, "conflicts": 1}, id="ours-removed-what-theirs-changed-prefer-theirs"),
        pytest.param(_ours_changed_the_italian_cancel, "ours", "common.cancel", {"en": "Cancel", "it": "Chiudi"}, {"added": 4, "changed": 4, "removed": 0, "already": 0, "conflicts": 1}, id="theirs-removed-what-ours-changed-prefer-ours"),
        pytest.param(_ours_changed_the_italian_cancel, "theirs", "common.cancel", None, {"added": 4, "changed": 4, "removed": 1, "already": 0, "conflicts": 1}, id="theirs-removed-what-ours-changed-prefer-theirs"),
    ],
)
def test_absorb_prefer_settles_a_removal_conflict_for_the_whole_key(history, ours, prefer, key, kept, counts):
    """One side removed a key, the other changed one of its translations: whether the key exists is decided by its
    English, so ``prefer`` settles the whole key, in every language, as the preferred side has it (``kept`` None: no
    key). A key brought back counts as added, a key removed as removed, the conflict once."""
    ours(history)

    assert catalog.absorb(history.base, history.theirs, root=history.repo, prefer=prefer) == counts

    values = flat(history.repo, strict=True)
    assert {language: values[language].get(key) for language in ("en", "it")} == (kept or {"en": None, "it": None})


def test_absorb_finds_no_conflict_when_theirs_only_dropped_a_translation_of_a_key_ours_removed(history):
    dropped = history.branch("dropped", legacy(("it", "old.gone", DROPPED)))
    _ours_removed_old_gone(history)
    before = age(history.repo)

    assert catalog.absorb(history.base, dropped, root=history.repo) == {"added": 0, "changed": 0, "removed": 0, "already": 1, "conflicts": 0}

    assert changes(history.repo, before) == (set(), set())
    assert "old.gone" not in flat(history.repo)["en"]


def test_absorb_names_every_language_theirs_changed_in_a_key_ours_removed_and_counts_one_conflict(history):
    both = history.branch("both", legacy(("en", "old.gone", "Gone!"), ("it", "old.gone", "Sparito")))
    _ours_removed_old_gone(history)
    before = age(history.repo)

    with pytest.raises(CatalogError) as caught:
        catalog.absorb(history.base, both, root=history.repo)

    assert caught.value.problems == [f'{CONFLICT}: old.gone: removed by ours, while theirs changed it: en "Gone" → "Gone!", it "Andato" → "Sparito"']
    assert changes(history.repo, before) == (set(), set())
    assert catalog.absorb(history.base, both, root=history.repo, prefer="ours") == {"added": 0, "changed": 0, "removed": 0, "already": 0, "conflicts": 1}
    assert changes(history.repo, before) == (set(), set()), "ours is what the sources already hold"


def test_absorb_counts_a_translation_base_did_not_have_as_a_change_to_a_key_ours_removed(history):
    lacking = history.branch("lacking", legacy(("it", "old.gone", DROPPED)))
    _ours_removed_old_gone(history)
    before = age(history.repo)

    with pytest.raises(CatalogError) as caught:
        catalog.absorb(lacking, history.theirs, root=history.repo)

    assert caught.value.problems == [f'{CONFLICT}: old.gone: removed by ours, while theirs changed it: it (absent) → "Sparito"']
    assert changes(history.repo, before) == (set(), set())


def test_absorb_prefer_theirs_brings_a_key_ours_removed_back_with_exactly_their_languages(history):
    lacking = history.branch("lacking", legacy(("it", "old.gone", DROPPED)))
    english_only = history.branch("english-only", legacy(("en", "old.gone", "Gone!"), ("it", "old.gone", DROPPED)))
    _ours_removed_old_gone(history)

    assert catalog.absorb(lacking, english_only, root=history.repo, prefer="theirs") == {"added": 1, "changed": 0, "removed": 0, "already": 0, "conflicts": 1}

    held = {language: catalog.flatten(catalog.load_catalog(language, root=history.repo, fallback=False)).get("old.gone") for language in ("en", "it")}
    assert held == {"en": "Gone!", "it": None}


def test_absorb_writes_nothing_when_a_new_key_has_no_safe_home(history):
    """The branch adds common.retry, which route places, and risk.analytics.var.title, which it cannot: all or nothing.
    The refusal is reported once, with what to do."""
    unroutable = history.branch("unroutable", UNROUTABLE)
    before = age(history.repo)

    with pytest.raises(CatalogError) as caught:
        catalog.absorb(history.base, unroutable, root=history.repo)

    hint = " (absorb cannot choose: add it first with `dev.py i18n add risk.analytics.var.title --into ...` and its values, then absorb again)"
    assert caught.value.problems == [refused("risk.analytics.var.title", "risk.analytics", "probe_plugins/stress") + hint]
    assert changes(history.repo, before) == (set(), set())


def test_absorb_reports_a_branch_under_a_string_in_each_language(history):
    dotted = history.branch("dotted", DOTTED)
    before = age(history.repo)

    with pytest.raises(CatalogError) as caught:
        catalog.absorb(history.base, dotted, root=history.repo)

    assert caught.value.problems == [f"{language} common.ok.short: 'ok' is a string and cannot hold children" for language in ("en", "it")]
    assert changes(history.repo, before) == (set(), set())


def test_absorb_removes_before_it_adds_so_a_string_can_become_a_branch(history):
    reshaped = history.branch("reshaped", RESHAPED)

    assert catalog.absorb(history.base, reshaped, root=history.repo) == {"added": 2, "changed": 0, "removed": 1, "already": 0, "conflicts": 0}

    assert catalog.compare(catalog.catalogs_at(reshaped, root=history.repo), flat(history.repo, strict=True)) == []
    assert read(history.repo, f"{BASE_DIR}/en.json")["common"] == {"cancel": "Cancel", "ok": {"short": "OK", "long": "Okay"}}


def test_absorb_takes_a_null_for_a_value_and_the_final_merge_refuses_it(history):
    """Taken for an absent value, the Italian null would remove the translation and the absorb would pass, lenient."""
    nulled = history.branch("nulled", legacy(("it", "common.ok", None)))
    before = age(history.repo)

    at_nulled = catalog.catalogs_at(nulled, root=history.repo)
    assert ("common.ok" in at_nulled["it"], at_nulled["it"].get("common.ok")) == (True, None)
    with pytest.raises(CatalogError) as caught:
        catalog.absorb(history.base, nulled, root=history.repo)

    assert caught.value.problems == ["frontend/src/lib/i18n/base/it.json: 1 value(s) not a string, e.g. common.ok"]
    assert changes(history.repo, before) == (set(), set())


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        pytest.param(None, "null", id="null-is-a-value-not-absent"),
        pytest.param(42, "42", id="a-number"),
        pytest.param(list(range(30)), "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16...", id="a-long-list-cut-to-57-characters"),
    ],
)
def test_a_conflict_shows_any_value(history, value, shown):
    odd = history.branch("odd", legacy(("it", "common.ok", value)))
    put(history.repo, BASE_DIR, "common.ok", {"it": "Bene"})
    before = age(history.repo)

    with pytest.raises(CatalogError) as caught:
        catalog.absorb(history.base, odd, root=history.repo)

    assert caught.value.problems == [f'{CONFLICT}: it common.ok: base "Va bene", ours "Bene", theirs {shown}']
    assert changes(history.repo, before) == (set(), set())


# =============================================================================
# The repository
# =============================================================================


def base_key_problems(root: Path) -> list[str]:
    """The four ``base`` catalogues are there, and each holds exactly English's keys."""
    found = sorted(path.stem for path in (root / BASE_DIR).glob("*.json"))
    if found != sorted(UI_LANGUAGES):
        return [f"{BASE_DIR}: languages {found}, expected {sorted(UI_LANGUAGES)}"]
    keys = {language: set(catalog.flatten(read(root, f"{BASE_DIR}/{language}.json"))) for language in UI_LANGUAGES}
    problems = []
    for language in UI_LANGUAGES[1:]:
        missing, extra = sorted(keys["en"] - keys[language]), sorted(keys[language] - keys["en"])
        if missing or extra:
            problems.append(f"{BASE_DIR}/{language}.json: lacks {missing[:5]}, has beyond English {extra[:5]}")
    return problems


def source_files(root: Path) -> list[str]:
    """Every catalogue source that loading reads, relative to ``root``."""
    _langs, sources = catalog.load(root)
    return sorted(catalog.display_path(source.file(language), root) for source in sources for language in source.catalogs)


def format_problems(root: Path) -> list[str]:
    """The sources not in the generator's own format: the first tool that touches one rewrites it whole."""
    problems = []
    for relative in source_files(root):
        text = (root / relative).read_text(encoding="utf-8")
        if text != dumps(json.loads(text, object_pairs_hook=OrderedDict)):
            problems.append(f"{relative}: not in the generator's format")
    return problems


GENERATED = (*(f"{I18N}/{language}.json" for language in UI_LANGUAGES), STAMP)
I18N_SOURCE_SAMPLES = (f"{BASE_DIR}/en.json", f"{I18N}/subsystem/prefixes.txt", f"{I18N}/subsystem/it.json")
PLUGIN_SOURCE_SAMPLES = (f"{SERVICES}/brim_providers/broker_x/i18n/en.json", f"{SERVICES}/signal_plugins/x/i18n/es.json")


def ignored(repo: Path, relative: str) -> bool:
    """Whether the repository's ignore rules match ``relative``, whatever the index holds (the rule, not the state of a
    commit). A personal excludes file is not the repository's: it is left out."""
    result = subprocess.run(["git", "-C", str(repo), "-c", f"core.excludesFile={os.devnull}", "check-ignore", "--no-index", "-q", relative], capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        raise AssertionError(f"git check-ignore {relative}: {result.stderr.strip()}")
    return result.returncode == 0


def ignore_problems(repo: Path) -> list[str]:
    problems = [f"{relative}: generated, but git does not ignore it" for relative in GENERATED if not ignored(repo, relative)]
    return problems + [f"{relative}: a source, but git ignores it" for relative in I18N_SOURCE_SAMPLES + PLUGIN_SOURCE_SAMPLES if ignored(repo, relative)]


def tracked(repo: Path, relative: str) -> bool:
    """Whether the index holds ``relative``: what the next commit will hold."""
    result = subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch", "--", relative], capture_output=True, text=True, check=False)
    return result.returncode == 0


def layout_problems(repo: Path) -> list[str]:
    """The index holds the legacy catalogues or the sources, never both. An ignore rule does not untrack a file, and
    ``catalogs_at`` reads the legacy catalogues of a commit that tracks them, whatever sources it also holds."""
    if not tracked(repo, f"{BASE_DIR}/en.json"):
        return []
    return [f"{relative}: tracked beside the sources; it is generated, untrack it (git rm --cached)" for relative in GENERATED if tracked(repo, relative)]


def test_the_repository_sources_merge_strictly():
    """What ``dev.py i18n check --strict`` and the audit demand. Its failing half is
    ``test_a_missing_translation_is_an_error_when_strict`` and ``test_each_defect_is_refused_by_merge_build_and_check``."""
    problems = problems_of(REPO_ROOT, strict=True)

    assert problems == [], f"{len(problems)} problem(s) in the catalogue's sources:\n" + "\n".join(f"  {problem}" for problem in problems)


def test_the_four_base_catalogues_hold_the_same_keys():
    assert base_key_problems(REPO_ROOT) == []


@pytest.mark.parametrize(
    ("edit", "problems"),
    [
        pytest.param(None, [], id="four-languages-with-the-same-keys"),
        pytest.param(lambda root: drop(root, BASE_DIR, "common.cancel", ("it",)), ["frontend/src/lib/i18n/base/it.json: lacks ['common.cancel'], has beyond English []"], id="a-key-missing"),
        pytest.param(lambda root: put(root, BASE_DIR, "common.extra", {"fr": "En plus"}), ["frontend/src/lib/i18n/base/fr.json: lacks [], has beyond English ['common.extra']"], id="a-key-english-does-not-have"),
        pytest.param(lambda root: (root / BASE_DIR / "es.json").unlink(), ["frontend/src/lib/i18n/base: languages ['en', 'fr', 'it'], expected ['en', 'es', 'fr', 'it']"], id="a-language-missing"),
        pytest.param(lambda root: write(root, f"{BASE_DIR}/de.json", "{}\n"), ["frontend/src/lib/i18n/base: languages ['de', 'en', 'es', 'fr', 'it'], expected ['en', 'es', 'fr', 'it']"], id="a-fifth-language"),
    ],
)
def test_the_base_key_check_fails_when_a_language_drifts(tmp_path, edit, problems):
    write_catalogs(tmp_path, BASE_DIR, {language: {"common": {"ok": "OK", "cancel": f"Cancel ({language})"}} for language in UI_LANGUAGES})
    if edit:
        edit(tmp_path)

    assert base_key_problems(tmp_path) == problems


def test_every_repository_source_is_in_the_generator_format():
    """``save()`` writes this format: a source in any other is rewritten whole by the first ``set``/``move``/``split``."""
    assert f"{BASE_DIR}/en.json" in source_files(REPO_ROOT), "presence barrier: the sources were not found"
    assert format_problems(REPO_ROOT) == []


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        pytest.param(dumps(BASE["it"]), True, id="the-generator-format"),
        pytest.param(json.dumps(BASE["it"], ensure_ascii=False, indent=4) + "\n", False, id="four-spaces"),
        pytest.param(json.dumps(BASE["it"], indent=2) + "\n", False, id="non-ascii-escaped"),
        pytest.param(json.dumps(BASE["it"], ensure_ascii=False, indent=2), False, id="no-final-newline"),
    ],
)
def test_the_format_check_fails_on_a_source_the_tools_would_rewrite(tmp_path, text, canonical):
    root = healthy_tree(tmp_path)
    write(root, f"{BASE_DIR}/it.json", text)

    assert format_problems(root) == ([] if canonical else ["frontend/src/lib/i18n/base/it.json: not in the generator's format"])


def test_load_catalog_reads_this_checkout_without_a_build():
    """What the backend tests that read the catalogue rely on: the default root is this checkout, and every language
    comes from the sources, whether or not a build has generated ``frontend/src/lib/i18n/<lang>.json``. Without
    fallback (how those tests read it) each language holds every key by itself."""
    assert catalog.ROOT == REPO_ROOT

    keys = {(language, fallback): set(catalog.flatten(catalog.load_catalog(language, fallback=fallback))) for language in UI_LANGUAGES for fallback in (True, False)}

    english = keys["en", True]
    assert english, "presence barrier: English has no key"
    assert {pair: found == english for pair, found in keys.items()} == dict.fromkeys(keys, True)


def test_load_catalog_merges_the_sources_in_memory_and_writes_nothing(tmp_path):
    root = healthy_tree(tmp_path)
    write(root, f"{I18N}/it.json", '{"stale": "a generated file is never read back"}\n')
    before = age(root)

    for language in ("en", "it"):
        assert catalog.load_catalog(language, root=root) == merged(root).catalogs[language]

    assert changes(root, before) == (set(), set())


def test_load_catalog_raises_rather_than_returning_an_empty_catalogue(tmp_path):
    root = healthy_tree(tmp_path)

    with pytest.raises(KeyError):
        catalog.load_catalog("de", root=root)
    (root / BASE_DIR / "en.json").unlink()
    with pytest.raises(CatalogError):
        catalog.load_catalog("it", root=root)


def test_git_ignores_the_generated_catalogues_and_none_of_their_sources(hermetic_git):
    assert ignore_problems(REPO_ROOT) == []


@pytest.mark.parametrize(
    ("rules", "problems"),
    [
        pytest.param({}, [f"{relative}: generated, but git does not ignore it" for relative in GENERATED], id="nothing-ignored"),
        pytest.param({"frontend/.gitignore": "/src/lib/i18n/*.json\n/src/lib/i18n/.generated\n"}, [], id="the-generated-files-only"),
        pytest.param({"frontend/.gitignore": "/src/lib/i18n/\n"}, [f"{relative}: a source, but git ignores it" for relative in I18N_SOURCE_SAMPLES], id="the-whole-folder"),
        pytest.param({".gitignore": "i18n/\n"}, [f"{relative}: a source, but git ignores it" for relative in I18N_SOURCE_SAMPLES + PLUGIN_SOURCE_SAMPLES], id="every-i18n-folder"),
    ],
)
def test_the_ignore_check_fails_when_git_ignores_too_little_or_too_much(tmp_path, hermetic_git, rules, problems):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    for relative, text in rules.items():
        write(repo, relative, text)

    assert ignore_problems(repo) == problems


def test_the_index_never_holds_the_generated_catalogues_beside_their_sources(hermetic_git):
    """Checked on the index, so a commit that stages the sources without untracking the old catalogues is caught before
    it is made. Its failing half is the next test."""
    assert layout_problems(REPO_ROOT) == []


@pytest.mark.parametrize(
    ("staged", "problems"),
    [
        pytest.param((f"{I18N}/en.json", f"{I18N}/it.json"), [], id="the-legacy-layout"),
        pytest.param((f"{BASE_DIR}/en.json", f"{BASE_DIR}/it.json"), [], id="the-sources"),
        pytest.param((f"{I18N}/en.json", f"{I18N}/it.json", f"{BASE_DIR}/en.json", f"{BASE_DIR}/it.json"), [f"{I18N}/{language}.json: tracked beside the sources; it is generated, untrack it (git rm --cached)" for language in ("en", "it")], id="both"),
    ],
)
def test_the_layout_check_fails_when_the_index_holds_both_layouts(tmp_path, hermetic_git, staged, problems):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    for relative in staged:
        write(repo, relative, "{}\n")
    git(repo, "add", "--", *staged)

    assert layout_problems(repo) == problems
