"""Tests for cross-boundary documentation link discovery (``scripts/docs_links.py``) and dev.py's anchor verdict.

The gate this module serves used to declare its own blindness in a comment —
*"a dynamic `path={expr}` has no quotes and is skipped by construction"* — and
the declaration was not quite true: the expressions it skipped resolved to
static maps and constants sitting in the same file. It was skipped by choice.

Two properties are worth more than the rest, and both are asymmetries:

* **A known constant must be resolved, not deleted.** The naive repair — scan
  the map literals and strip ``${…}`` — turns ``${DOCS}/max-drawdown/`` into
  ``max-drawdown``, a plausible path that does not exist, and reports a healthy
  link as broken. A gate that stops being blind by starting to lie is worse than
  the blindness: people learn to ignore it.

* **A guess may confirm a link and never condemn one.** When an interpolation
  *cannot* be resolved, dropping it is a guess. If the guess lands on a real
  page, the link is fine; if it does not, that says something about the guess,
  not about the link — so the verdict is "unverifiable", never "broken".

dev.py's verdict on an anchor (R2 B13). ``_mkdocs_check_anchor`` checks a link's anchor in English, then in every
language the page is translated into. It judged them against slugs dev.py made itself, which offered the text slug
of a heading with an explicit ``{: #id }`` (the build gives that heading its id only) and kept accents (``Détails``
gave ``détails``, the build ``details``). A page's anchors are now the ids of its own MkDocs render,
``page_anchors.file_anchors``, the function translate-validate uses. That needs MkDocs, which dev.py does not: without
it, dev.py still builds its whole CLI, and ``mkdocs check-links`` says what it needs and exits 1 before checking
anything.

dev.py is never imported here: its import changes directory and ``sys.path``, in a pytest process other units share.
These cases run it in child interpreters. Red phase, against the dev.py of f4a42bf4a (HEAD), run from a copy of the
tree: 5 red, 3 green.

* red (5): fr named among the languages lacking ``#details``, which its heading «Détails» gives; the text slug of a
  heading with an explicit id, accepted in English on a translated page and on an English-only one;
  ``_mkdocs_page_anchors``, which HEAD lacks; ``check-links`` without MkDocs, which ran instead of saying what it needs;
* green (3): an anchor every language offers, kept by the translations as an explicit id (two cases); dev.py building
  its CLI without MkDocs, which HEAD did too.

dev.py's check of the built site (R2 B14). A translated page is built one folder deeper than its English page
(``site/<lang>/...``), and the language folders hold only pages. MkDocs rewrites the paths of Markdown images and
links, not those of raw HTML, so a raw-HTML path copied unchanged from the English points under ``site/<lang>/``,
where the file is not. The check run after ``mkdocs build`` looked only at ``static/icons`` and printed a warning:
21 such images shipped broken. ``_check_asset_paths_in_built_site`` resolves every relative URL of a file
(``<img>``/``<source>`` ``src``/``srcset``, ``<video>`` ``src``/``poster``, ``<audio>`` ``src``, ``<a href>`` to a
file) from its page's folder as a browser does, inside the site, HTML comments left out, and ``cmd_mkdocs_build``
exits 1 when one is broken. The cases build a site under ``tmp_path``; ``cmd_mkdocs_build`` runs in a child with
``mkdocs build``, ``copy_docs_assets`` and the admonition check stubbed and ``PROJECT_ROOT`` pointing at a tree under
``tmp_path``. Red phase, against the dev.py of c0d933abf (HEAD), run from a copy of the tree: 22 red, 1 green.

* red on a missing function (20): every case of ``_check_asset_paths_in_built_site``;
* red on behaviour (1): a broken image that is not an icon, with which HEAD's build returned 0;
* red on output, its exit status right (1): a site whose URLs resolve, which HEAD's check did not count;
* green (1): a failed MkDocs build keeps its exit code, and the check does not run.

Against the first version of batch 14, which read the tags inside HTML comments, the comment case is red.

PURE: every fixture is built under ``tmp_path``. The discovery tests read no repo files; the dev.py children read
code and ``mkdocs_src/mkdocs.yml``, the site configuration ``page_anchors`` renders with, never the docs nor the
built site: the build cases build their own.
"""

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from scripts.docs_links import (
    Link,
    collect_backend,
    collect_frontend,
    deduplicate,
    find_page,
    resolve,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
#: Started in child interpreters, never imported here: its import changes directory and ``sys.path``.
DEV_PY = PROJECT_ROOT / "dev.py"
#: Seconds. A child loads dev.py and the site's MkDocs configuration; a loaded parallel run takes longer, a hang still ends.
CHILD_TIMEOUT = 120
ANSI = re.compile(r"\x1b\[[0-9;]*m")
#: Where the links of the anchor cases come from, as check-links names an origin.
ORIGIN = "frontend/src/lib/components/settings/SettingsPanel.svelte:42"

#: A child's script: dev.py loaded as a module (its ``main()`` does not run), the Aphra pipeline put on ``sys.path`` as
#: ``main()`` does before any mkdocs command, then the calls of argv[2], ``[[name, [arguments]], ...]``, answered with one
#: JSON list. ``page_anchors.<name>`` is the shared module's function, any other name dev.py's; an argument
#: ``{"path": p}`` is passed as ``Path(p)``; a set comes back as a sorted list.
CALL_DEV = textwrap.dedent("""\
    import importlib, json, runpy, sys
    from pathlib import Path

    dev = runpy.run_path(sys.argv[1], run_name="dev_under_test")
    sys.path.insert(0, str(dev["PROJECT_ROOT"] / "mkdocs_src" / "aphra-pipeline"))

    def function(name):
        module, _, attribute = name.rpartition(".")
        return getattr(importlib.import_module(module), attribute) if module else dev[attribute]

    def argument(value):
        return Path(value["path"]) if isinstance(value, dict) else value

    def result(value):
        return sorted(value) if isinstance(value, (set, frozenset)) else value

    print(json.dumps([result(function(name)(*map(argument, args))) for name, args in json.loads(sys.argv[2])]))
    """)

#: A child's script for a host without MkDocs: importing ``mkdocs`` (or any ``mkdocs.*``) raises ImportError, then
#: dev.py (argv[1]) runs as ``python dev.py <the remaining arguments>`` would.
DEV_WITHOUT_MKDOCS = textwrap.dedent("""\
    import runpy, sys

    sys.modules["mkdocs"] = None
    sys.argv = sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name="__main__")
    """)

#: A child's script: dev.py loaded as a module, ``PROJECT_ROOT`` pointed at argv[2] (a tree holding ``mkdocs_src/site``),
#: the build's other steps stubbed (``mkdocs build`` exits with argv[3]), then ``cmd_mkdocs_build``. Its output comes
#: first, then one JSON line: what it returned and the commands ``run_pipenv`` was given.
BUILD_DEV = textwrap.dedent("""\
    import importlib.util, json, sys
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("dev_under_test", sys.argv[1])
    dev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dev)
    dev.PROJECT_ROOT = Path(sys.argv[2])
    builds = []
    dev.run_pipenv = lambda args, **kwargs: builds.append(args) or int(sys.argv[3])
    dev.copy_docs_assets = lambda: None
    dev._check_admonition_empty_lines = lambda: None
    returned = dev.cmd_mkdocs_build(None)
    print(json.dumps({"returned": returned, "builds": builds}))
    """)


@pytest.fixture
def docs_root(tmp_path):
    """A miniature mkdocs tree with one real page per shape."""
    root = tmp_path / "docs"
    for rel in (
        "financial-theory/metrics/max-drawdown/index.en.md",
        "financial-theory/metrics/value-at-risk.en.md",
        "user/tools/rebalancer/index.en.md",
    ):
        page = root / rel
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("# Title\n", encoding="utf-8")
    return root


class TestResolve:
    def test_a_known_constant_is_substituted_not_deleted(self):
        consts = {"DOCS": "financial-theory/metrics"}
        assert resolve("${DOCS}/max-drawdown/", consts) == (
            "financial-theory/metrics/max-drawdown",
            True,
        )

    def test_deleting_the_constant_would_have_produced_a_different_path(self, docs_root):
        # The measured trap, kept as an executable statement: the old resolver
        # returned "max-drawdown", which resolves to nothing.
        assert find_page(docs_root, "max-drawdown") is None
        resolved, _ = resolve("${DOCS}/max-drawdown/", {"DOCS": "financial-theory/metrics"})
        assert find_page(docs_root, resolved) is not None

    def test_an_unknown_interpolation_yields_a_speculative_path(self):
        # `/mkdocs/${prefix}user/...` — prefix is a language segment that is
        # empty for English, so dropping it is right *and* unproven.
        assert resolve("${prefix}user/tools/rebalancer/") == ("user/tools/rebalancer", False)

    def test_the_svelte_interpolation_dialect_is_understood_too(self):
        # Markup uses `{X}`, not `${X}`; a resolver that knows only one dialect
        # is blind on half the call sites.
        assert resolve("{DOCS}/max-drawdown/", {"DOCS": "financial-theory/metrics"}) == (
            "financial-theory/metrics/max-drawdown",
            True,
        )

    @pytest.mark.parametrize("raw", ["${lang", "", "/", "https://example.org/x", ":path"])
    def test_values_with_nothing_checkable_are_refused(self, raw):
        assert resolve(raw) is None


class TestFindPage:
    @pytest.mark.parametrize(
        "path",
        [
            "financial-theory/metrics/max-drawdown/",
            "financial-theory/metrics/max-drawdown",
            "financial-theory/metrics/value-at-risk",
            "financial-theory/metrics/max-drawdown/#an-anchor",
        ],
    )
    def test_directory_and_file_spellings_both_resolve(self, docs_root, path):
        assert find_page(docs_root, path) is not None

    def test_a_missing_page_is_reported_as_missing(self, docs_root):
        assert find_page(docs_root, "financial-theory/metrics/sortino") is None


class TestFrontendDiscovery:
    SOURCE = """
    <script lang="ts">
        const DOCS = 'financial-theory/metrics';
        const DOC_PATHS: Record<string, string> = {
            day: `${DOCS}/max-drawdown/`,
            worst: `${DOCS}/value-at-risk/`,
        };
    </script>
    <RiskMetricCard docsPath={DOC_PATHS[row.id]} />
    <DocsLink path="user/tools/rebalancer/" />
    <DocsLink path={runtimeOnly} />
    """

    @pytest.fixture
    def found(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "Panel.svelte").write_text(self.SOURCE, encoding="utf-8")
        return collect_frontend(src)

    def test_the_map_behind_a_dynamic_prop_is_read(self, found):
        paths = {link.path for link in found.links}
        assert "financial-theory/metrics/max-drawdown" in paths
        assert "financial-theory/metrics/value-at-risk" in paths

    def test_the_map_values_keep_their_constant_prefix(self, found):
        # The regression this guards: a stripped `${DOCS}` leaves a bare leaf.
        assert not any(link.path in {"max-drawdown", "value-at-risk"} for link in found.links)

    def test_plain_literals_still_work(self, found):
        assert "user/tools/rebalancer" in {link.path for link in found.links}

    def test_a_genuinely_dynamic_prop_is_declared_not_swallowed(self, found):
        # It used to vanish from the output, and an empty error list read as a pass.
        assert found.unverified, "an unresolvable reference must be reported"

    @pytest.mark.parametrize("name", ["Thing.test.ts", "Thing.spec.ts", "generated.ts"])
    def test_fixtures_and_generated_artefacts_are_ignored(self, tmp_path, name):
        # generated.ts is git-ignored, so reading it would make this gate's
        # output depend on whether a code generator happened to have run.
        src = tmp_path / "src"
        src.mkdir()
        (src / name).write_text("const p = 'user/ghost/page';\ndocsPath: 'user/ghost'\n")
        found = collect_frontend(src)
        assert found.links == []
        assert found.unverified == []

    def test_a_route_placeholder_is_not_reported_at_all(self, tmp_path):
        # `/mkdocs/:path` is a URL pattern, not a link. Listing it as
        # "unverifiable" would be noise in the one section meant to be read.
        src = tmp_path / "src"
        src.mkdir()
        (src / "Router.ts").write_text("const route = '/mkdocs/:path';\n")
        found = collect_frontend(src)
        assert found.links == []
        assert found.unverified == []


class TestBackendDiscovery:
    """Plugin families must be found by glob, not by a hand-written list."""

    @pytest.fixture
    def services(self, tmp_path):
        root = tmp_path / "services"
        for pkg, body in {
            "signal_plugins/adx.py": 'docs_path = "financial-theory/indicators/adx/"\n',
            "brim_providers/degiro.py": 'docs_path = "user/transactions/import/degiro/"\n',
            "tool_plugins/pac.py": 'ToolDocumentation(path="user/tools/pac-allocator/")\n',
            "fx_providers/ecb.py": 'DOCS = "/mkdocs/user/fx/providers/ecb/"\n',
            "not_a_plugin_dir/x.py": 'docs_path = "user/should/not/be/scanned/"\n',
        }.items():
            path = root / pkg
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return root

    @pytest.mark.parametrize(
        "expected",
        [
            "financial-theory/indicators/adx",
            "user/transactions/import/degiro",
            "user/tools/pac-allocator",
            "user/fx/providers/ecb",
        ],
    )
    def test_every_plugin_family_is_covered(self, services, expected):
        # The two directories the gate used to name by hand left signal_plugins,
        # tool_plugins and brim_providers unchecked — fifty pages between them.
        assert expected in {link.path for link in collect_backend(services).links}

    def test_unrelated_packages_are_not_scanned(self, services):
        paths = {link.path for link in collect_backend(services).links}
        assert "user/should/not/be/scanned" not in paths

    def test_a_missing_services_directory_is_not_an_error(self, tmp_path):
        assert collect_backend(tmp_path / "absent").links == []


class TestDeduplicate:
    def test_keeps_one_entry_per_path_with_its_first_origin(self):
        links = [Link("a/b", "one.py"), Link("a/b", "two.py"), Link("c/d", "three.py")]
        unique = deduplicate(links)
        assert [(link.path, link.origin) for link in unique] == [
            ("a/b", "one.py"),
            ("c/d", "three.py"),
        ]


def call_dev(*calls: tuple) -> list:
    """Each ``(name, *arguments)`` run in one child interpreter that loaded ``DEV_PY``: their results, in order."""
    payload = [[name, [{"path": str(arg)} if isinstance(arg, Path) else arg for arg in args]] for name, *args in calls]
    child = subprocess.run([sys.executable, "-c", CALL_DEV, str(DEV_PY), json.dumps(payload)], stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=CHILD_TIMEOUT, check=False)
    status, stdout, stderr = child.returncode, child.stdout, child.stderr
    assert status == 0, f"the child exited {status}:\n{stdout}\n{stderr}"
    return json.loads(stdout.strip().splitlines()[-1])


def run_dev_without_mkdocs(*argv: str) -> tuple[int, str]:
    """``python dev.py <argv>`` where MkDocs cannot be imported: the exit status and the output, stderr included, uncoloured."""
    child = subprocess.run([sys.executable, "-c", DEV_WITHOUT_MKDOCS, str(DEV_PY), *argv], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=CHILD_TIMEOUT, check=False)
    return child.returncode, ANSI.sub("", child.stdout)


#: One page in four languages, its headings written as the docs write them: the EN heading's slug kept by every
#: translation as an explicit id (general-settings), an EN explicit id kept as it is (fifo-lots), a heading each language
#: translates without an id (Details).
SETTINGS_PAGES = {
    "en": "# Settings\n\n## General settings\n\n## Details\n\n## Lot matching {: #fifo-lots }\n",
    "it": "# Impostazioni\n\n## Impostazioni generali {: #general-settings }\n\n## Dettagli\n\n## Abbinamento dei lotti {: #fifo-lots }\n",
    "fr": "# Paramètres\n\n## Paramètres généraux {: #general-settings }\n\n## Détails\n\n## Appariement des lots {: #fifo-lots }\n",
    "es": "# Ajustes\n\n## Ajustes generales {: #general-settings }\n\n## Detalles\n\n## Emparejamiento de lotes {: #fifo-lots }\n",
}
#: A page with no translation: mkdocs-static-i18n serves its English body, anchors included, in every language.
LOTS_PAGE = "# Lots\n\n## Lot matching {: #fifo-lots }\n"


@pytest.fixture
def anchor_docs(tmp_path):
    """user/settings in four languages, developer/lots in English only."""
    root = tmp_path / "docs"
    pages = {f"user/settings.{lang}.md": text for lang, text in SETTINGS_PAGES.items()} | {"developer/lots.en.md": LOTS_PAGE}
    for rel, text in pages.items():
        page = root / rel
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(text, encoding="utf-8")
    return root


def verdicts(docs, page: str, *anchors: str) -> list:
    """dev.py's verdict on a link to ``page#anchor``, ``page`` an EN file under ``docs``, per anchor: None when it resolves."""
    link = page.removesuffix(".en.md")
    return call_dev(*(("_mkdocs_check_anchor", docs / page, anchor, f"{link}/#{anchor}", ORIGIN, docs) for anchor in anchors))


def missing_in(verdict: str | None) -> list[str]:
    """The languages a verdict names as lacking the anchor."""
    match = re.search(r"missing in: ([a-z]{2}(?:, [a-z]{2})*)", verdict or "")
    assert match, f"not a verdict naming the languages that lack an anchor: {verdict!r}"
    return match.group(1).split(", ")


class TestAnchorVerdict:
    """An anchor is checked against each language's MkDocs render: what the build checks a link against."""

    @pytest.mark.parametrize(
        "anchor",
        [
            pytest.param("general-settings", id="en-slug-kept-by-the-translations-as-an-explicit-id"),
            pytest.param("fifo-lots", id="en-explicit-id-kept-by-the-translations"),
        ],
    )
    def test_an_anchor_every_language_offers_resolves(self, anchor_docs, anchor):
        assert verdicts(anchor_docs, "user/settings.en.md", anchor) == [None]

    def test_the_languages_lacking_an_anchor_are_named(self, anchor_docs):
        # fr's «Détails» renders as #details: a slug drops accents, so only it and es lack it.
        (verdict,) = verdicts(anchor_docs, "user/settings.en.md", "details")
        assert missing_in(verdict) == ["it", "es"]

    @pytest.mark.parametrize("page", ["user/settings.en.md", "developer/lots.en.md"], ids=["translated-page", "english-only-page"])
    def test_the_text_slug_of_a_heading_with_an_explicit_id_is_no_anchor(self, anchor_docs, page):
        # The build gives «Lot matching {: #fifo-lots }» its id only: #lot-matching lands nowhere, already in English.
        (verdict,) = verdicts(anchor_docs, page, "lot-matching")
        assert "File exists but anchor #lot-matching not found" in (verdict or ""), verdict

    def test_a_pages_anchors_are_the_shared_render(self, anchor_docs):
        # The translated slugs of the headings with an id (impostazioni-generali, abbinamento-dei-lotti) are not anchors.
        page = anchor_docs / "user" / "settings.it.md"
        from_dev, shared = call_dev(("_mkdocs_page_anchors", page), ("page_anchors.file_anchors", page))
        assert from_dev == shared == ["dettagli", "fifo-lots", "general-settings", "impostazioni"]


class TestDevPyWithoutMkDocs:
    """MkDocs belongs to the docs toolchain, not to dev.py: only check-links needs it, and it says so."""

    def test_dev_py_builds_its_whole_cli(self):
        assert (DEV_PY.parent / "mkdocs_src" / "aphra-pipeline" / "validate_translations.py").is_file(), "barrier: building the parser imports translate-validate's module, and with it page_anchors"
        status, output = run_dev_without_mkdocs("--help")
        assert (status, "Traceback" in output) == (0, False), output
        assert "check-links" in output, output

    def test_check_links_says_it_needs_mkdocs_and_exits_1(self):
        status, output = run_dev_without_mkdocs("mkdocs", "check-links")
        assert (status, "check-links needs MkDocs" in output, "Traceback" in output) == (1, True, False), output
        # Before checking anything: no verdict is printed for a link whose anchors it cannot read.
        assert "Checking cross-boundary links" not in output, output


#: Files of the fake built site, under static/ at its root as the docs' images are. ``archive.v1`` is a folder with
#: an index.html, ``archive.v2`` (made by the fixture) one without.
SITE_FILES = ("static/a.png", "static/a b.png", "static/a&b.png", "static/report.pdf", "static/clip.mp4", "static/poster.jpg", "static/sound.mp3", "static/archive.v1/index.html")
EN_PAGE = "user/x/index.html"  # the English page user/x.md, one folder below the root
IT_PAGE = "it/user/x/index.html"  # its Italian build, one folder deeper; a language folder holds only pages
EN_DEPTH = "../../static/"  # from EN_PAGE to static/: the path the English writes
IT_DEPTH = "../../../static/"  # from IT_PAGE to static/: one more '../'


def build_site(root: Path) -> Path:
    """A built site at ``root`` holding SITE_FILES and no page yet."""
    for rel in SITE_FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x00")
    (root / "static" / "archive.v2").mkdir()
    return root


@pytest.fixture
def site(tmp_path) -> Path:
    return build_site(tmp_path / "site")


@pytest.fixture
def project(tmp_path) -> Path:
    """A project root whose ``mkdocs_src/site`` is a built site, as ``cmd_mkdocs_build`` finds it."""
    build_site(tmp_path / "project" / "mkdocs_src" / "site")
    return tmp_path / "project"


def write_page(site: Path, page: str, markup: str) -> None:
    path = site / page
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"<!doctype html>\n<html><body>\n{markup}\n</body></html>\n", encoding="utf-8")


def broken_assets(site: Path) -> list:
    """``_check_asset_paths_in_built_site(site)``: the broken URLs as [page, tag, attribute, url]."""
    (broken,) = call_dev(("_check_asset_paths_in_built_site", site))
    return broken


def build_docs(root: Path, mkdocs_exit: int) -> tuple[int, list, str]:
    """``cmd_mkdocs_build`` on the site under ``root``, ``mkdocs build`` stubbed to exit with ``mkdocs_exit``: what it
    returned, the commands it gave ``run_pipenv`` and its output, uncoloured."""
    child = subprocess.run([sys.executable, "-c", BUILD_DEV, str(DEV_PY), str(root), str(mkdocs_exit)], stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=CHILD_TIMEOUT, check=False)
    status, stdout, stderr = child.returncode, ANSI.sub("", child.stdout), child.stderr
    assert status == 0, f"the child exited {status}:\n{stdout}\n{stderr}"
    *output, reply = stdout.strip().splitlines()
    returned = json.loads(reply)
    return returned["returned"], returned["builds"], "\n".join(output)


class TestBuiltSiteAssets:
    """Every relative URL of a file in the built site resolves from its page's folder, inside the site."""

    def test_the_english_path_breaks_one_folder_deeper(self, site):
        write_page(site, EN_PAGE, f'<img src="{EN_DEPTH}a.png">')
        write_page(site, IT_PAGE, f'<img src="{EN_DEPTH}a.png">\n<img src="{IT_DEPTH}a.png">')
        assert broken_assets(site) == [[IT_PAGE, "img", "src", f"{EN_DEPTH}a.png"]]

    @pytest.mark.parametrize(
        ("markup", "reported"),
        [
            pytest.param('<img srcset="{it}a.png 1x, {en}a.png 2x">', [("img", "srcset", "a.png")], id="img-srcset-the-broken-candidate"),
            pytest.param('<picture><source srcset="{en}a.png"><img src="{it}a.png"></picture>', [("source", "srcset", "a.png")], id="source-srcset"),
            pytest.param('<video><source src="{en}clip.mp4" type="video/mp4"><source src="{it}clip.mp4"></video>', [("source", "src", "clip.mp4")], id="source-src"),
            pytest.param('<video src="{en}clip.mp4" poster="{it}poster.jpg"></video>', [("video", "src", "clip.mp4")], id="video-src"),
            pytest.param('<video src="{it}clip.mp4" poster="{en}poster.jpg"></video>', [("video", "poster", "poster.jpg")], id="video-poster"),
            pytest.param('<audio src="{en}sound.mp3"></audio> <audio src="{it}sound.mp3"></audio>', [("audio", "src", "sound.mp3")], id="audio-src"),
            pytest.param('<a href="{en}report.pdf">PDF</a> <a href="{it}report.pdf">PDF</a>', [("a", "href", "report.pdf")], id="a-href-to-a-file"),
        ],
    )
    def test_every_file_url_of_a_page_is_checked(self, site, markup, reported):
        # In the Italian page, the English depth breaks and one more '../' resolves: only the first is reported.
        write_page(site, IT_PAGE, markup.format(en=EN_DEPTH, it=IT_DEPTH))
        assert broken_assets(site) == [[IT_PAGE, tag, attr, f"{EN_DEPTH}{name}"] for tag, attr, name in reported]

    def test_a_link_to_a_page_or_a_folder_is_not_checked(self, site):
        pages = '<a href="../other/">Other</a> <a href="../../user/">User</a> <a href="page.html">Page</a> <a href="page.htm">Page</a>'
        write_page(site, IT_PAGE, f'{pages}\n<a href="{EN_DEPTH}report.pdf">PDF</a>')
        assert broken_assets(site) == [[IT_PAGE, "a", "href", f"{EN_DEPTH}report.pdf"]]

    @pytest.mark.parametrize(
        ("written", "reported"),
        [
            pytest.param("a.png?v=2#top", "a.png?v=2#top", id="query-and-fragment-dropped"),
            pytest.param("a%20b.png", "a%20b.png", id="percent-encoding-decoded"),
            pytest.param("a&amp;b.png", "a&b.png", id="html-entity-unescaped"),
        ],
    )
    def test_a_url_is_resolved_as_a_browser_reads_it(self, site, written, reported):
        # One folder deeper the file is found (static/a.png, static/a b.png, static/a&b.png); at the English depth the
        # URL is reported, as the page holds it but for its entities.
        write_page(site, IT_PAGE, f'<img src="{IT_DEPTH}{written}">\n<img src="{EN_DEPTH}{written}">')
        assert broken_assets(site) == [[IT_PAGE, "img", "src", f"{EN_DEPTH}{reported}"]]

    @pytest.mark.parametrize(
        "markup",
        [
            pytest.param("<img alt='A' src='{url}'>", id="single-quotes"),
            pytest.param('<IMG ALT="A" SRC="{url}">', id="upper-case-tag-and-attribute"),
            pytest.param('<img\n  class="shot"\n  src="{url}">', id="attributes-over-several-lines"),
        ],
    )
    def test_any_spelling_of_the_tag_is_read(self, site, markup):
        write_page(site, IT_PAGE, markup.format(url=f"{EN_DEPTH}a.png"))
        assert broken_assets(site) == [[IT_PAGE, "img", "src", f"{EN_DEPTH}a.png"]]

    def test_urls_that_are_not_relative_paths_of_a_file_are_ignored(self, site):
        ignored = [
            f'<img data-src="{EN_DEPTH}a.png">',
            '<img src="https://example.com/a.png">',
            '<img src="//cdn.example.com/a.png">',
            '<img src="/static/a.png">',
            '<img src="#x">',
            '<img src="data:image/png;base64,iVBORw0KGgo=">',
            '<img src="">',
        ]
        write_page(site, IT_PAGE, "\n".join([*ignored, f'<img src="{EN_DEPTH}a.png">']))
        assert broken_assets(site) == [[IT_PAGE, "img", "src", f"{EN_DEPTH}a.png"]], "only the last image, which is read"

    def test_a_path_out_of_the_site_is_broken_even_if_the_file_exists(self, site):
        outside, url = site.parent / "outside.png", "../../../outside.png"
        outside.write_bytes(b"\x00")
        write_page(site, EN_PAGE, f'<img src="{url}">')
        assert (site / EN_PAGE).parent.joinpath(url).resolve() == outside.resolve(), "barrier: the URL lands on an existing file"
        assert broken_assets(site) == [[EN_PAGE, "img", "src", url]]

    def test_a_folder_resolves_when_it_holds_an_index_html(self, site):
        # A name that looks like a file can be a folder, served by its index.html.
        write_page(site, EN_PAGE, f'<a href="{EN_DEPTH}archive.v1">v1</a> <a href="{EN_DEPTH}archive.v2">v2</a>')
        assert broken_assets(site) == [[EN_PAGE, "a", "href", f"{EN_DEPTH}archive.v2"]]

    def test_an_html_comment_is_not_read(self, site):
        # A commented-out image is no image, on one line or over several: the same tag outside a comment is reported.
        tag, other_page = f'<img src="{EN_DEPTH}a.png">', "it/user/y/index.html"
        write_page(site, IT_PAGE, f"<!-- {tag} -->\n<!--\nFirst version:\n{tag}\n-->")
        write_page(site, other_page, tag)
        assert broken_assets(site) == [[other_page, "img", "src", f"{EN_DEPTH}a.png"]]

    def test_a_site_not_built_has_nothing_to_check(self, tmp_path):
        assert broken_assets(tmp_path / "site") == []


class TestMkdocsBuild:
    """``dev.py mkdocs build`` fails on a broken asset URL of its site; a failed MkDocs build keeps its own exit code."""

    def test_a_broken_asset_url_fails_the_build(self, project):
        site = project / "mkdocs_src" / "site"
        write_page(site, EN_PAGE, f'<img src="{EN_DEPTH}a.png">')
        write_page(site, IT_PAGE, f'<img src="{EN_DEPTH}a.png">')  # an image, not an icon: HEAD's check looked at static/icons only
        returned, builds, output = build_docs(project, mkdocs_exit=0)
        assert len(builds) == 1, "barrier: mkdocs build ran, stubbed"
        assert returned == 1, output
        assert "1 broken asset URL(s)" in output and IT_PAGE in output and f"{EN_DEPTH}a.png" in output, output
        assert "one more '../'" in output and "html-asset-depth" in output, output

    def test_a_site_whose_urls_resolve_builds(self, project):
        site = project / "mkdocs_src" / "site"
        write_page(site, EN_PAGE, f'<img src="{EN_DEPTH}a.png">')
        write_page(site, IT_PAGE, f'<img src="{IT_DEPTH}a.png">')
        returned, builds, output = build_docs(project, mkdocs_exit=0)
        assert (len(builds), returned) == (1, 0), output
        assert "All 2 relative asset URL(s) in the built site resolve" in output, output

    def test_a_failed_mkdocs_build_keeps_its_exit_code_and_skips_the_check(self, project):
        write_page(project / "mkdocs_src" / "site", IT_PAGE, f'<img src="{EN_DEPTH}a.png">')
        returned, builds, output = build_docs(project, mkdocs_exit=2)
        assert (len(builds), returned) == (1, 2), output
        assert "asset URL" not in output, output
