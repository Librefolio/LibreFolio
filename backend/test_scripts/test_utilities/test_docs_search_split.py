"""search_language_split: one search index per language, written after the docs build (DOC-2, route B, lot of workstream H).

Material downloads ONE ``search/search_index.json`` for every language of the site (10 MB, the English, Italian, French and
Spanish pages together), so a visitor searching in Italian sees the Italian, English, French and Spanish page of the same
topic side by side. Route B (analysis ``H-DOC2-analisi.md``) splits it after the build and lets a small script pick the
file of the page's language before Material fetches it. This file pins the build half:
``mkdocs_src/hooks/search_language_split.py`` and what it leaves in ``site/``.

Pinned here:

* ``language_of(location)``: the language of one entry of the index, by the FIRST path segment of its ``location``: exactly
  ``it`` / ``fr`` / ``es`` (alone, or followed by ``/`` or ``#``) is that language, anything else is ``en``, the default
  language (the pages that exist only in English, ``developer/api/``, included: the i18n plugin's fallback copies them under
  ``/it/`` but never puts them in the index). A segment that merely STARTS like a language (``italiano/``, ``item/``,
  ``frontend/``, ``espresso/``) is English; so is a language segment that is not the first one (``developer/it/``);
* ``split_index(index, languages)``, pure: one index per language, the same ``config`` in all of them, and every ``doc`` of
  the full index in exactly ONE of them, unchanged: none lost, none duplicated, none changed. The input is not modified. The
  ``languages`` argument limits the keys that come out;
* the same properties on the real index built in ``mkdocs_src/site/`` (when there is one): counts add up, a language file
  holds only its prefix, the Italian pages are not in ``en``;
* ``on_post_build(config)``: reads ``<site_dir>/search/search_index.json`` and writes ``search_index.<lang>.json`` beside it
  for ``en``, ``it``, ``fr``, ``es``: valid UTF-8 JSON (non-ASCII text intact), each equal to ``split_index``'s answer,
  nothing else written, the full index byte for byte as it was. A missing index (a build without the search plugin, a
  ``mkdocs serve``) logs a warning and does nothing: it never raises;
* what the build leaves in ``site/`` (when the docs are built, with this hook): the four files exist and agree with the full
  index, every built page's ``<html lang>`` is one of the four languages, and each language's home page loads
  ``javascripts/search-language.js`` in the head, BEFORE Material's bundle, which is what lets the script wrap ``fetch``
  before Material calls it;
* the registration: ``mkdocs.yml`` lists the hook under ``hooks:`` and does NOT list the script in ``extra_javascript`` (that
  puts it after the bundle); ``overrides/main.html`` loads it in the ``extrahead`` block.

Red phase. The hook and the script are new, with no HEAD version: the file runs against a tree where they do not exist yet.
The tests that read the BUILT site (``TestBuiltSite``) are red until ``./dev.py mkdocs build`` is run on the new source; they
are skipped, with a reason, only when there is no built index at all (a checkout that never built the docs).

PURE: dictionaries and files under ``tmp_path``, the hook loaded by path. Reads ``mkdocs_src/mkdocs.yml``,
``mkdocs_src/overrides/main.html`` and, when it exists, ``mkdocs_src/site/`` (read only). No DB, no server, no network, no
writes outside ``tmp_path``.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import logging
import re
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from mkdocs.config.defaults import MkDocsConfig

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MKDOCS_SRC = PROJECT_ROOT / "mkdocs_src"
MKDOCS_YML = MKDOCS_SRC / "mkdocs.yml"
MAIN_HTML = MKDOCS_SRC / "overrides" / "main.html"
HOOK_ENTRY = "hooks/search_language_split.py"  # as mkdocs.yml lists it: relative to the configuration file
HOOK = MKDOCS_SRC / HOOK_ENTRY
SITE = MKDOCS_SRC / "site"
FULL_INDEX = SITE / "search" / "search_index.json"

LANGUAGES = ["en", "it", "fr", "es"]  # the i18n plugin's languages in mkdocs.yml, en the default
PREFIXED = ["it", "fr", "es"]  # the languages whose pages live under a folder of their own name

NO_BUILD = "the docs are not built here (no mkdocs_src/site/search/search_index.json): run ./dev.py mkdocs build"
needs_built_index = pytest.mark.skipif(not FULL_INDEX.exists(), reason=NO_BUILD)


# ---------------------------------------------------------------------------
# The hook, loaded by path as MkDocs loads it. Reached through a fixture only, so a function the hook lacks fails the tests
# that call it, never the collection.
# ---------------------------------------------------------------------------


def _load_hook(name: str) -> ModuleType:
    """The hook file as a module of its own, by path (what ``config_options.Hooks._load_hook`` does)."""
    spec = importlib.util.spec_from_file_location(name, HOOK)
    assert spec is not None and spec.loader is not None, f"cannot load {HOOK} as a module"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    assert HOOK.is_file(), f"the hook is not there yet: {HOOK}"
    module = _load_hook("search_language_split_under_test")
    for name in ("language_of", "split_index", "on_post_build"):
        assert callable(getattr(module, name, None)), f"the hook has no {name}(): {HOOK}"
    return module


def _doc(location: str, title: str = "T", text: str = "body") -> dict:
    """One entry of the index, shaped as MkDocs' search plugin writes it (``location``, ``title``, ``text``)."""
    return {"location": location, "title": title, "text": text}


# The config of the real index (what ``static-i18n`` makes of ``search.lang``): the same object travels into every file.
CONFIG = {
    "lang": ["en", "it", "fr", "es"],
    "separator": r"[\s\-]+",
    "pipeline": ["stopWordFilter"],
    "fields": {"title": {"boost": 1000.0}, "text": {"boost": 1.0}, "tags": {"boost": 1000000.0}},
}

# One entry per language and a few of each kind, every location distinct so a doc is told by its location.
SYNTHETIC_DOCS = [
    _doc("", "Home"),
    _doc("#lf-fit-title", "Home fit"),
    _doc("admin/backup_restore/", "Backup"),
    _doc("admin/backup_restore/#restore", "Restore"),
    _doc("developer/api/", "API (English only)"),
    _doc("it/", "Home it"),
    _doc("it/#intro", "Intro it"),
    _doc("it/admin/backup_restore/", "Backup it"),
    _doc("it/admin/backup_restore/#ripristino", "Ripristino è ò à"),
    _doc("fr/", "Accueil"),
    _doc("fr/admin/backup_restore/", "Sauvegarde « é »"),
    _doc("fr/admin/backup_restore/#restauration", "Restauration"),
    _doc("es/", "Inicio"),
    _doc("es/admin/backup_restore/", "Copia de seguridad ñ"),
    _doc("es/admin/backup_restore/#restaurar", "Restaurar ¿?"),
    # Names that only LOOK like a language: English.
    _doc("italiano/x/", "italiano"),
    _doc("item/", "item"),
    _doc("frontend/", "frontend"),
    _doc("espresso/", "espresso"),
    _doc("it-x/", "it-x"),
    _doc("developer/it/x/", "language not first"),
    _doc("user/fr/", "language not first, fr"),
]


def _index(docs: list[dict] | None = None) -> dict:
    return {"config": copy.deepcopy(CONFIG), "docs": copy.deepcopy(SYNTHETIC_DOCS if docs is None else docs)}


def _locations(docs: list[dict]) -> list[str]:
    return [d["location"] for d in docs]


# ---------------------------------------------------------------------------
# language_of
# ---------------------------------------------------------------------------


class TestLanguageOf:
    @pytest.mark.parametrize(
        ("location", "expected"),
        [
            # Italian, French, Spanish: the first segment is exactly the language, alone, or followed by / or #.
            ("it/", "it"),
            ("it/x/", "it"),
            ("it/#a", "it"),
            ("it/admin/backup_restore/#ripristino", "it"),
            ("it", "it"),
            ("it#a", "it"),
            ("fr/", "fr"),
            ("fr/user/dashboard/", "fr"),
            ("fr/#a", "fr"),
            ("fr", "fr"),
            ("es/", "es"),
            ("es/financial-theory/#a", "es"),
            ("es#a", "es"),
            ("es", "es"),
        ],
    )
    def test_a_language_folder_is_that_language(self, hook, location, expected):
        assert hook.language_of(location) == expected

    @pytest.mark.parametrize(
        "location",
        [
            "",  # the home page of the default language
            "#a",  # a section of it
            "#lf-fit-title",
            "developer/api/",  # a page that exists in English only
            "admin/backup_restore/",
            "admin/backup_restore/#restore",
            "user/",
            # a name that only starts like a language
            "italiano/",
            "italiano/x/",
            "item/",
            "item/x/#a",
            "frontend/",
            "french/",
            "francese/x/",
            "espresso/",
            "espanol/x/",
            "it-x/",
            "it_x/",
            # a language that is not the first segment
            "developer/it/x/",
            "user/fr/",
            "x/es/",
            # other folders: not a language of this site
            "de/x/",
            "en/x/",
        ],
    )
    def test_everything_else_is_english(self, hook, location):
        assert hook.language_of(location) == "en"

    def test_the_answer_is_always_one_of_the_languages(self, hook):
        for doc in SYNTHETIC_DOCS:
            assert hook.language_of(doc["location"]) in LANGUAGES, doc["location"]

    def test_the_languages_of_the_site(self, hook):
        assert list(hook.LANGUAGES) == LANGUAGES, "the four languages of mkdocs.yml, the default first"


# ---------------------------------------------------------------------------
# split_index
# ---------------------------------------------------------------------------


class TestSplitIndex:
    def test_one_index_per_language_each_with_config_and_docs(self, hook):
        out = hook.split_index(_index())
        assert set(out) == set(LANGUAGES)
        for lang, part in out.items():
            assert set(part) == {"config", "docs"}, lang
            assert isinstance(part["docs"], list), lang

    def test_the_config_is_the_same_in_every_language_and_as_the_full_index(self, hook):
        out = hook.split_index(_index())
        for lang, part in out.items():
            assert part["config"] == CONFIG, f"{lang}: the config travels unchanged (the worker needs every language's pipeline)"

    def test_every_doc_is_in_exactly_one_language(self, hook):
        out = hook.split_index(_index())
        everything = [loc for part in out.values() for loc in _locations(part["docs"])]
        assert sorted(everything) == sorted(_locations(SYNTHETIC_DOCS)), "none lost, none duplicated"
        assert len(everything) == len(set(everything)), "no location in two files"

    def test_each_language_holds_only_its_own_prefix(self, hook):
        out = hook.split_index(_index())
        for lang in PREFIXED:
            assert _locations(out[lang]["docs"]), f"the synthetic index has {lang} docs"
            for loc in _locations(out[lang]["docs"]):
                assert loc == lang or loc.startswith((f"{lang}/", f"{lang}#")), f"{loc!r} is not {lang}"
        for loc in _locations(out["en"]["docs"]):
            first = re.split(r"[/#]", loc, maxsplit=1)[0]
            assert first not in PREFIXED, f"{loc!r} is not English"

    def test_the_split_by_location(self, hook):
        out = hook.split_index(_index())
        assert sorted(_locations(out["it"]["docs"])) == sorted(["it/", "it/#intro", "it/admin/backup_restore/", "it/admin/backup_restore/#ripristino"])
        assert sorted(_locations(out["fr"]["docs"])) == sorted(["fr/", "fr/admin/backup_restore/", "fr/admin/backup_restore/#restauration"])
        assert sorted(_locations(out["es"]["docs"])) == sorted(["es/", "es/admin/backup_restore/", "es/admin/backup_restore/#restaurar"])
        english = {
            "",
            "#lf-fit-title",
            "admin/backup_restore/",
            "admin/backup_restore/#restore",
            "developer/api/",
            "italiano/x/",
            "item/",
            "frontend/",
            "espresso/",
            "it-x/",
            "developer/it/x/",
            "user/fr/",
        }
        assert set(_locations(out["en"]["docs"])) == english

    def test_a_page_that_exists_only_in_english_is_only_in_english(self, hook):
        out = hook.split_index(_index())
        for lang in PREFIXED:
            assert "developer/api/" not in _locations(out[lang]["docs"]), lang
        assert "developer/api/" in _locations(out["en"]["docs"])

    def test_the_docs_are_unchanged(self, hook):
        out = hook.split_index(_index())
        by_location = {d["location"]: d for d in SYNTHETIC_DOCS}
        for part in out.values():
            for doc in part["docs"]:
                assert doc == by_location[doc["location"]], "title and text travel as they are, non-ASCII included"

    def test_the_input_is_not_modified(self, hook):
        index = _index()
        before = copy.deepcopy(index)
        hook.split_index(index)
        assert index == before

    def test_an_empty_index_gives_four_empty_languages(self, hook):
        out = hook.split_index(_index([]))
        assert set(out) == set(LANGUAGES)
        for lang, part in out.items():
            assert part["docs"] == [], lang
            assert part["config"] == CONFIG, lang

    def test_a_language_without_docs_is_still_there_empty(self, hook):
        only_english = [d for d in SYNTHETIC_DOCS if hook.language_of(d["location"]) == "en"]
        out = hook.split_index(_index(only_english))
        assert set(out) == set(LANGUAGES)
        assert out["it"]["docs"] == [] and out["fr"]["docs"] == [] and out["es"]["docs"] == []
        assert len(out["en"]["docs"]) == len(only_english)

    def test_the_languages_argument_limits_the_files(self, hook):
        docs = [d for d in SYNTHETIC_DOCS if hook.language_of(d["location"]) in ("en", "it")]
        out = hook.split_index(_index(docs), languages=["en", "it"])
        assert set(out) == {"en", "it"}
        assert sorted(_locations(out["it"]["docs"])) == sorted(loc for loc in _locations(docs) if loc.startswith("it/"))

    @needs_built_index
    def test_the_real_index_counts_add_up_and_each_file_holds_its_prefix(self, hook):
        full = json.loads(FULL_INDEX.read_text(encoding="utf-8"))
        out = hook.split_index(full)
        assert set(out) == set(LANGUAGES)

        total = sum(len(part["docs"]) for part in out.values())
        assert total == len(full["docs"]), "the four files together hold every doc of the full index: none lost, none duplicated"
        for lang, part in out.items():
            assert part["config"] == full["config"], lang
            assert part["docs"], f"the real site has {lang} pages"

        everything = [(d["location"], d["title"], d["text"]) for part in out.values() for d in part["docs"]]
        assert sorted(everything) == sorted((d["location"], d["title"], d["text"]) for d in full["docs"]), "the same docs, repartitioned"

        for lang in PREFIXED:
            for doc in out[lang]["docs"]:
                loc = doc["location"]
                assert loc == lang or loc.startswith((f"{lang}/", f"{lang}#")), f"{loc!r} is in the {lang} file"
        for doc in out["en"]["docs"]:
            first = re.split(r"[/#]", doc["location"], maxsplit=1)[0]
            assert first not in PREFIXED, f"{doc['location']!r} is in the English file"

    @needs_built_index
    def test_the_real_italian_pages_are_not_in_english(self, hook):
        full = json.loads(FULL_INDEX.read_text(encoding="utf-8"))
        italian_in_full = {d["location"] for d in full["docs"] if d["location"].startswith("it/")}
        assert italian_in_full, "precondition: the built index holds Italian pages"
        out = hook.split_index(full)
        english = set(_locations(out["en"]["docs"]))
        assert not (italian_in_full & english), "an it/ doc in the English file is what this route removes"
        assert italian_in_full == set(_locations(out["it"]["docs"]))


# ---------------------------------------------------------------------------
# on_post_build
# ---------------------------------------------------------------------------


def _config_for(site_dir: Path) -> MkDocsConfig:
    """A real MkDocs configuration, holding the only value the hook needs: where the site was built."""
    config = MkDocsConfig()
    config.site_dir = str(site_dir)
    return config


def _write_full_index(site_dir: Path, index: dict) -> Path:
    path = site_dir / "search" / "search_index.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return path


class TestOnPostBuild:
    def test_writes_one_file_per_language_beside_the_full_index(self, hook, tmp_path):
        site = tmp_path / "site"
        _write_full_index(site, _index())
        hook.on_post_build(config=_config_for(site))
        for lang in LANGUAGES:
            assert (site / "search" / f"search_index.{lang}.json").is_file(), lang

    def test_each_file_is_valid_utf8_json_equal_to_the_split(self, hook, tmp_path):
        site = tmp_path / "site"
        _write_full_index(site, _index())
        hook.on_post_build(config=_config_for(site))
        expected = hook.split_index(_index())
        for lang in LANGUAGES:
            raw = (site / "search" / f"search_index.{lang}.json").read_bytes()
            assert json.loads(raw.decode("utf-8")) == expected[lang], lang

    def test_the_files_hold_exactly_the_docs_of_their_language(self, hook, tmp_path):
        """Not through split_index: the file of a language, read back, holds the locations of its prefix and every doc once."""
        site = tmp_path / "site"
        _write_full_index(site, _index())
        hook.on_post_build(config=_config_for(site))
        seen: list[str] = []
        for lang in LANGUAGES:
            part = json.loads((site / "search" / f"search_index.{lang}.json").read_text(encoding="utf-8"))
            assert part["config"] == CONFIG, lang
            for doc in part["docs"]:
                seen.append(doc["location"])
                if lang in PREFIXED:
                    assert doc["location"] == lang or doc["location"].startswith((f"{lang}/", f"{lang}#")), (lang, doc["location"])
                else:
                    assert re.split(r"[/#]", doc["location"], maxsplit=1)[0] not in PREFIXED, doc["location"]
        assert sorted(seen) == sorted(_locations(SYNTHETIC_DOCS))

    def test_non_ascii_text_survives(self, hook, tmp_path):
        site = tmp_path / "site"
        _write_full_index(site, _index())
        hook.on_post_build(config=_config_for(site))
        italian = json.loads((site / "search" / "search_index.it.json").read_text(encoding="utf-8"))
        assert "Ripristino è ò à" in [d["title"] for d in italian["docs"]]
        french = json.loads((site / "search" / "search_index.fr.json").read_text(encoding="utf-8"))
        assert "Sauvegarde « é »" in [d["title"] for d in french["docs"]]

    def test_the_full_index_stays_byte_for_byte(self, hook, tmp_path):
        site = tmp_path / "site"
        full = _write_full_index(site, _index())
        before = full.read_bytes()
        hook.on_post_build(config=_config_for(site))
        assert full.read_bytes() == before

    def test_it_writes_nothing_else(self, hook, tmp_path):
        site = tmp_path / "site"
        _write_full_index(site, _index())
        hook.on_post_build(config=_config_for(site))
        assert sorted(p.name for p in (site / "search").iterdir()) == sorted(["search_index.json", *(f"search_index.{lang}.json" for lang in LANGUAGES)])
        assert [p.name for p in site.iterdir()] == ["search"], "nothing outside the search folder"

    def test_a_second_build_over_the_first_gives_the_same_files(self, hook, tmp_path):
        site = tmp_path / "site"
        _write_full_index(site, _index())
        hook.on_post_build(config=_config_for(site))
        first = {lang: (site / "search" / f"search_index.{lang}.json").read_bytes() for lang in LANGUAGES}
        hook.on_post_build(config=_config_for(site))
        second = {lang: (site / "search" / f"search_index.{lang}.json").read_bytes() for lang in LANGUAGES}
        assert first == second

    def test_a_missing_index_warns_and_writes_nothing(self, hook, tmp_path, caplog):
        site = tmp_path / "site"
        (site / "search").mkdir(parents=True)  # the folder is there, the index is not: the search plugin ran off
        with caplog.at_level(logging.WARNING):
            hook.on_post_build(config=_config_for(site))  # must not raise
        assert any(record.levelno >= logging.WARNING for record in caplog.records), "the hook says it found no index"
        assert [p.name for p in (site / "search").iterdir()] == [], "and writes none of the four files"

    def test_a_site_without_a_search_folder_does_not_raise(self, hook, tmp_path, caplog):
        site = tmp_path / "site"
        site.mkdir()
        with caplog.at_level(logging.WARNING):
            hook.on_post_build(config=_config_for(site))
        assert any(record.levelno >= logging.WARNING for record in caplog.records)
        assert list(site.iterdir()) == []

    def test_a_site_dir_that_does_not_exist_does_not_raise(self, hook, tmp_path):
        hook.on_post_build(config=_config_for(tmp_path / "never-built"))
        assert not (tmp_path / "never-built").exists(), "the hook creates no site"


# ---------------------------------------------------------------------------
# The registration
# ---------------------------------------------------------------------------


class _MkDocsYmlLoader(yaml.SafeLoader):
    """``mkdocs.yml`` holds ``!!python/name:`` and ``!ENV`` tags: read as plain data, never executed."""


_MkDocsYmlLoader.add_multi_constructor("", lambda loader, suffix, node: None)


def _mkdocs_yml() -> dict:
    return yaml.load(MKDOCS_YML.read_text(encoding="utf-8"), Loader=_MkDocsYmlLoader)  # noqa: S506 - a loader that builds nothing


class TestRegistration:
    def test_mkdocs_yml_lists_the_hook(self):
        assert HOOK_ENTRY in _mkdocs_yml()["hooks"]

    def test_the_hook_file_is_there(self):
        assert HOOK.is_file(), f"mkdocs.yml lists a hook that does not exist: {HOOK}"

    def test_the_script_is_not_an_extra_javascript(self):
        """``extra_javascript`` lands AFTER Material's bundle at the end of the body: too late to wrap the ``fetch`` it calls."""
        scripts = [str(s) for s in _mkdocs_yml().get("extra_javascript") or []]
        assert not [s for s in scripts if "search-language" in s], scripts

    def test_main_html_loads_the_script_in_the_head_block(self):
        text = MAIN_HTML.read_text(encoding="utf-8")
        block = re.search(r"{%\s*block\s+extrahead\s*%}(.*?){%\s*endblock\s*%}", text, re.S)
        assert block, "overrides/main.html has an extrahead block"
        assert re.search(r"""<script\s+src=["']{{\s*['"]javascripts/search-language\.js['"]\s*\|\s*url\s*}}["']\s*>\s*</script>""", block.group(1)), "a classic script tag, MkDocs' url filter, no defer or async or type=module"
        assert not re.search(r"<script[^>]*search-language[^>]*\b(defer|async|type=)", block.group(1)), "it must run before the bundle: neither deferred nor a module"

    def test_the_script_source_is_there(self):
        assert (MKDOCS_SRC / "docs" / "javascripts" / "search-language.js").is_file()


# ---------------------------------------------------------------------------
# The built site
# ---------------------------------------------------------------------------

_HTML_LANG = re.compile(r"""<html\b[^>]*\blang=["']([^"']*)["']""", re.I)
_SCRIPT_SRC = re.compile(r"""<script\b[^>]*\bsrc=["']([^"']+)["']""", re.I)
_MKDOCS_PAGE = re.compile(r"""<meta\s+name=["']generator["']\s+content=["']mkdocs-""", re.I)

# Each language's home page in the built site, and the path from it to the site's root (where ``javascripts/`` is).
HOME_PAGES = [("en", "index.html", ""), ("it", "it/index.html", "../"), ("fr", "fr/index.html", "../"), ("es", "es/index.html", "../")]


@needs_built_index
class TestBuiltSite:
    @pytest.mark.parametrize("lang", LANGUAGES)
    def test_the_language_file_exists_beside_the_full_index(self, lang):
        path = SITE / "search" / f"search_index.{lang}.json"
        assert path.is_file(), f"{path} is not in the built site: ./dev.py mkdocs build (the hook writes it after the build)"

    def test_the_files_agree_with_the_full_index(self, hook):
        full = json.loads(FULL_INDEX.read_text(encoding="utf-8"))
        total = 0
        for lang in LANGUAGES:
            path = SITE / "search" / f"search_index.{lang}.json"
            assert path.is_file(), f"{path} is not in the built site: ./dev.py mkdocs build"
            part = json.loads(path.read_text(encoding="utf-8"))
            assert part["config"] == full["config"], lang
            assert part["docs"], lang
            for doc in part["docs"]:
                assert hook.language_of(doc["location"]) == lang, (lang, doc["location"])
            total += len(part["docs"])
        assert total == len(full["docs"]), "the four files hold every doc of the full index, once"

    def test_the_italian_file_is_much_smaller_than_the_full_index(self):
        """The point of the route: a reader in Italian downloads a fraction of the 10 MB index. A factor of 3 is far below the measured 7."""
        italian = SITE / "search" / "search_index.it.json"
        assert italian.is_file(), f"{italian} is not in the built site: ./dev.py mkdocs build"
        assert italian.stat().st_size * 3 < FULL_INDEX.stat().st_size

    def test_every_built_page_says_a_language_the_files_cover(self):
        pages = [p for p in SITE.rglob("*.html") if _MKDOCS_PAGE.search(p.read_text(encoding="utf-8", errors="ignore")[:6000])]
        assert pages, "precondition: the built site has pages"
        bad: dict[str, str | None] = {}
        for page in pages:
            match = _HTML_LANG.search(page.read_text(encoding="utf-8", errors="ignore")[:6000])
            lang = match.group(1) if match else None
            if lang not in LANGUAGES:
                bad[str(page.relative_to(SITE))] = lang
        assert not bad, f"pages whose <html lang> is not one of {LANGUAGES} (the script would pick the English index for them): {dict(list(bad.items())[:10])}"

    @pytest.mark.parametrize(("lang", "page", "to_root"), HOME_PAGES)
    def test_the_home_page_loads_the_script_before_materials_bundle(self, lang, page, to_root):
        html = (SITE / page).read_text(encoding="utf-8")
        match = _HTML_LANG.search(html)
        assert match and match.group(1) == lang, f"precondition: {page} says lang={lang}"
        sources = _SCRIPT_SRC.findall(html)
        ours = [i for i, src in enumerate(sources) if src.endswith("javascripts/search-language.js") and "assets/" not in src]
        bundle = [i for i, src in enumerate(sources) if re.search(r"assets/javascripts/bundle\.[^/]*\.js$", src)]
        assert ours, f"{page} does not load javascripts/search-language.js: ./dev.py mkdocs build after the override is in"
        assert bundle, f"precondition: {page} loads Material's bundle"
        assert sources[ours[0]] == f"{to_root}javascripts/search-language.js", "relative to the page, to the site's root"
        assert ours[0] < bundle[0], "the script comes first: Material fetches the index when the bundle runs"
        head_end = html.index("</head>")
        assert html.index(sources[ours[0]]) < head_end, "and in the head, not at the end of the body"

    def test_the_script_is_copied_into_the_site(self):
        assert (SITE / "javascripts" / "search-language.js").is_file(), "mkdocs copies docs/javascripts/ to the site: ./dev.py mkdocs build"
