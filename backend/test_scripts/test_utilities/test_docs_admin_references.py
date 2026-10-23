"""docs_admin_references: every address of the admin guide that the app and the repository carry still reaches a page and an
anchor, and every anchor the long pages had before they were split is still reachable (DOC-1, lot of workstream H).

DOC-1 split the long English admin pages by section (``configuration`` into four, ``email`` into three, ``service_exposure``,
``sleep_wake`` and ``connection_checks`` into two each; pass 2 will do ``hosting_providers``, ``backup_restore`` and
``cli_tools``). The address of the guide is data the app spells in code (``checkGuides.json``, ``cspNotice.ts``, a ``DocsLink``,
the README), and a split moves anchors from one page to another without any compiler noticing. Three halves:

(a) **The references scan.** Every ``admin/<page>/#<anchor>`` and ``admin/<page>/`` of the NON-test sources of
    ``frontend/src`` (``.ts``, ``.svelte``, ``.json``), ``backend/app``, ``scripts``, ``dev.py`` and the README of the repository
    root, written bare, with a leading ``/mkdocs/`` (and a language folder) or as the public ``…/LibreFolio/admin/<page>/`` URL:
    ``mkdocs_src/docs/admin/<page>.en.md`` exists and, with an anchor, defines it. A page defines an anchor when it writes
    ``{: #anchor }`` exactly once, or when the anchor is the automatic slug of one of its headings
    (``markdown.extensions.toc.slugify``, separator ``-``); code fences count for nothing. The reader is shown honest on
    a synthetic sample (an invented page and an invented anchor are both reported, a repeated anchor, a heading in a code
    fence and a link are not taken for definitions) and against MkDocs' own render of every admin page (an anchor the reader
    defines is an id of the render: a reader that accepts everything fails there). A control: the scan finds at least 20
    references, those of ``checkGuides.json`` among them.
(b) **The anchors that moved.** ``backend/test_scripts/fixtures/docs_admin/old_anchors.json`` lists every anchor the five
    old pages had before the split. Each is still defined by its page, or ``MOVED_ANCHORS[page][anchor]`` of
    ``mkdocs_src/docs/javascripts/moved-anchors.js`` names a page that exists and defines it; no entry for an anchor the old
    page still defines; no entry for an anchor the old page never had; no entry that points back at its own page. The map is read from
    the script's text, the object literal between ``var MOVED_ANCHORS = `` and the ``;`` that ends it. The check is shown refusing a
    lost anchor, a stale entry, an entry to a page that does not define the anchor and one to a missing page.
(c) **The built site** (``TestBuiltSite``). Each reference with an anchor has ``id="<anchor>"`` in
    ``mkdocs_src/site/admin/<page>/index.html``; every English admin page exists in the built site; the built
    ``javascripts/moved-anchors.js`` is the source's and an admin page loads it. Skipped, with a reason, only when
    ``mkdocs_src/site/admin/`` does not exist. The site is a build of a past tree: until ``./dev.py mkdocs build`` runs on the
    split, these are red, and say which page and anchor the old build lacks.

PURE: reads files (the sources above, ``mkdocs_src/docs/admin/``, ``mkdocs_src/mkdocs.yml``, the fixture, and read only the
built ``mkdocs_src/site/``) and renders pages in memory with MkDocs; synthetic samples live under ``tmp_path``. No DB, no
server, no network, no writes outside ``tmp_path``.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pytest
from markdown.extensions.toc import slugify

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MKDOCS_SRC = PROJECT_ROOT / "mkdocs_src"
ADMIN_DOCS = MKDOCS_SRC / "docs" / "admin"
MKDOCS_YML = MKDOCS_SRC / "mkdocs.yml"
MOVED_JS = MKDOCS_SRC / "docs" / "javascripts" / "moved-anchors.js"
FIXTURE = PROJECT_ROOT / "backend" / "test_scripts" / "fixtures" / "docs_admin" / "old_anchors.json"
SITE = MKDOCS_SRC / "site"
SITE_ADMIN = SITE / "admin"
CHECK_GUIDES = PROJECT_ROOT / "frontend" / "src" / "lib" / "features" / "instance" / "checkGuides.json"
PAGE_ANCHORS_DIR = MKDOCS_SRC / "aphra-pipeline"

#: The pages DOC-1 pass 1 added; every one must exist in the source and in the built site.
NEW_PAGES = [
    "configuration_secrets",
    "configuration_security",
    "configuration_accounts",
    "email_flows",
    "email_troubleshooting",
    "service_exposure_funnel",
    "wake_sync",
    "connection_proxy",
]

# ---------------------------------------------------------------------------
# The reader of a page: which anchors it defines.
# ---------------------------------------------------------------------------

FENCE = re.compile(r"^\s*(```+|~~~+)")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
ATTR_LIST = re.compile(r"\s*\{:\s*([^}]*)\}\s*$")
INLINE_CODE = re.compile(r"`[^`]*`")
EXPLICIT_ID = re.compile(r"\{:[^}]*?#([A-Za-z0-9_-]+)[^}]*\}")


def _outside_fences(text: str) -> list[str]:
    """The lines of a Markdown text that are not inside a fenced code block (the fence lines themselves included in none)."""
    kept: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        marker = FENCE.match(line)
        if fence is None and marker:
            fence = marker.group(1)[0]
            continue
        if fence is not None:
            if marker and marker.group(1)[0] == fence:
                fence = None
            continue
        kept.append(line)
    return kept


def _plain_heading(text: str) -> str:
    """The text of a heading as it reads once rendered: links, code marks and emphasis reduced to their words."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r":[a-z0-9_-]+(?:-[a-z0-9_]+)*:", "", text)  # an emoji shortcode renders an icon, no text
    return re.sub(r"[`*]", "", text).strip()


@dataclass(frozen=True)
class PageAnchors:
    """What one page defines: explicit ids with their counts, and the automatic slugs of the headings that kept theirs."""

    explicit: dict[str, int]
    slugs: frozenset[str]

    def defines(self, anchor: str) -> bool:
        return self.explicit.get(anchor, 0) == 1 or (anchor in self.slugs and anchor not in self.explicit)

    def repeated(self) -> list[str]:
        return sorted(anchor for anchor, count in self.explicit.items() if count > 1)

    def all_defined(self) -> frozenset[str]:
        return frozenset(anchor for anchor in {*self.explicit, *self.slugs} if self.defines(anchor))


def read_page_anchors(markdown: str) -> PageAnchors:
    """The anchors a Markdown page defines, from its text, code fences left out."""
    explicit: dict[str, int] = {}
    slugs: set[str] = set()
    for line in _outside_fences(markdown):
        for found in EXPLICIT_ID.finditer(INLINE_CODE.sub("", line)):
            explicit[found.group(1)] = explicit.get(found.group(1), 0) + 1
        heading = HEADING.match(line)
        if not heading:
            continue
        body = heading.group(2)
        attr = ATTR_LIST.search(body)
        if attr and re.search(r"#[A-Za-z0-9_-]+", attr.group(1)):
            continue  # an explicit id replaces the heading's own
        if attr:
            body = body[: attr.start()]
        slug = slugify(_plain_heading(body), "-")
        if slug:
            slugs.add(slug)
    return PageAnchors(explicit, frozenset(slugs))


class DocsReader:
    """The English admin pages of a docs folder: ``<root>/<page>.en.md``, read once."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[str, PageAnchors | None] = {}

    def page_file(self, page: str) -> Path:
        return self.root / f"{page}.en.md"

    def page(self, page: str) -> PageAnchors | None:
        if page not in self._cache:
            file = self.page_file(page)
            self._cache[page] = read_page_anchors(file.read_text(encoding="utf-8-sig")) if file.is_file() else None
        return self._cache[page]

    def pages(self) -> list[str]:
        return sorted(file.name.removesuffix(".en.md") for file in self.root.glob("*.en.md"))


REAL = DocsReader(ADMIN_DOCS)

# ---------------------------------------------------------------------------
# The references scan.
# ---------------------------------------------------------------------------

#: A token that holds ``admin/<page>/`` with an optional ``#anchor``; ``pre`` is whatever of the token comes before it.
REFERENCE = re.compile(r"(?P<pre>[A-Za-z0-9_.:/%~-]*?)admin/(?P<page>[a-z0-9_]+)/(?:#(?P<anchor>[A-Za-z0-9_-]+))?")
#: What may stand before ``admin/``: nothing, ``/``, the ``/mkdocs/`` mount, the public ``…/LibreFolio/`` base, a language folder.
PREFIX = re.compile(r"^(?:https?://[A-Za-z0-9.-]+(?::\d+)?)?/?(?:LibreFolio/)?(?:mkdocs/)?(?:(?:it|fr|es)/)?$")

TEST_NAMES = (".test.ts", ".spec.ts", ".d.ts")
SKIPPED_DIRS = {"node_modules", "__pycache__", "__tests__", ".svelte-kit", "build"}
FRONTEND_SUFFIXES = {".ts", ".svelte", ".json"}
OTHER_SUFFIXES = {".py", ".md", ".json", ".sh", ".yml", ".yaml", ".html", ".txt", ".js", ".toml"}


@dataclass(frozen=True)
class Reference:
    source: str
    line: int
    page: str
    anchor: str | None

    def label(self) -> str:
        return f"{self.source}:{self.line} admin/{self.page}/" + (f"#{self.anchor}" if self.anchor else "")


def scan_text(text: str, source: str) -> list[Reference]:
    """Every reference to an admin page in a text."""
    found: list[Reference] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in REFERENCE.finditer(line):
            if PREFIX.match(match.group("pre")):
                found.append(Reference(source, number, match.group("page"), match.group("anchor")))
    return found


def _is_source(path: Path, suffixes: set[str]) -> bool:
    name = path.name
    if path.suffix not in suffixes or name == "generated.ts" or name.endswith(TEST_NAMES):
        return False
    if name.startswith("test_") and path.suffix == ".py":
        return False
    return not any(part in SKIPPED_DIRS for part in path.parts)


def _files(root: Path, suffixes: set[str]) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and _is_source(path.relative_to(root), suffixes):
            yield path


def scan_repository() -> list[Reference]:
    """Every reference in the non-test sources of the repository (the list in the module's docstring)."""
    roots: list[tuple[Path, set[str]]] = [
        (PROJECT_ROOT / "frontend" / "src", FRONTEND_SUFFIXES),
        (PROJECT_ROOT / "backend" / "app", OTHER_SUFFIXES),
        (PROJECT_ROOT / "scripts", OTHER_SUFFIXES),
        (PROJECT_ROOT / "dev.py", OTHER_SUFFIXES),
        *((readme, OTHER_SUFFIXES) for readme in sorted(PROJECT_ROOT.glob("README*.md"))),
    ]
    references: list[Reference] = []
    for root, suffixes in roots:
        for path in _files(root, suffixes):
            references.extend(scan_text(path.read_text(encoding="utf-8", errors="replace"), path.relative_to(PROJECT_ROOT).as_posix()))
    return references


def reference_problems(references: Iterable[Reference], reader: DocsReader) -> list[str]:
    """What is wrong with the references: a page that does not exist, an anchor its page does not define exactly once."""
    problems: list[str] = []
    for ref in references:
        page = reader.page(ref.page)
        if page is None:
            problems.append(f"{ref.label()}: no page {reader.page_file(ref.page).name}")
        elif ref.anchor is not None and not page.defines(ref.anchor):
            if page.explicit.get(ref.anchor, 0) > 1:
                problems.append(f"{ref.label()}: {ref.page}.en.md writes {{: #{ref.anchor} }} {page.explicit[ref.anchor]} times")
            else:
                problems.append(f"{ref.label()}: {ref.page}.en.md defines no anchor {ref.anchor}")
    return problems


REFERENCES = scan_repository()
ANCHORED = sorted({(ref.page, ref.anchor) for ref in REFERENCES if ref.anchor})


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


SAMPLE_PAGE = """# Sample page

## Real Heading {: #explicit-one }

Text with a [link](#invented-link-target) and `{: #in-code }`.

### Plain Heading Here

```markdown
## Heading In A Fence {: #fenced-id }
### Fenced Heading
```

#### Twice {: #twice }

Paragraph.
{: #twice }

## Heading with `code` and a [link](x.md)
"""


@pytest.fixture
def sample_docs(tmp_path: Path) -> DocsReader:
    _write(tmp_path / "docs" / "real.en.md", SAMPLE_PAGE)
    _write(tmp_path / "docs" / "other.en.md", "# Other\n\n## Second {: #other-second }\n")
    return DocsReader(tmp_path / "docs")


# ---------------------------------------------------------------------------
# (a) The references scan
# ---------------------------------------------------------------------------


class TestScanner:
    """The scanner and the reader of a page, shown on text whose answer is known."""

    @pytest.mark.parametrize(
        ("text", "page", "anchor"),
        [
            ("'admin/configuration_security/#csp'", "configuration_security", "csp"),
            ("`/mkdocs/admin/email/`", "email", None),
            ("href=/mkdocs/it/admin/settings/#open-registration-warning", "settings", "open-registration-warning"),
            ("(https://librefolio.github.io/LibreFolio/admin/host_installation/)", "host_installation", None),
            ("https://example.org/admin/docker_advanced/#a-b", "docker_advanced", "a-b"),
            ("`/mkdocs/${lang}/admin/users/#x`", "users", "x"),  # a template hole before the path: the literal tail is still an address (InstanceRestoreInterruptedPage)
        ],
    )
    def test_forms_of_an_address(self, text: str, page: str | None, anchor: str | None) -> None:
        found = scan_text(text, "x")
        if page is None:
            assert found == []
        else:
            assert [(ref.page, ref.anchor) for ref in found] == [(page, anchor)]

    @pytest.mark.parametrize(
        "text",
        [
            "mkdocs_src/docs/admin/configuration.en.md",  # a source file, no folder URL
            "see docs/admin/configuration/ in the tree",  # a path inside the repository, not an address
            "admin/configuration#csp",  # not a folder URL
            "/api/v1/admin/users/#x",  # an API route under another prefix
            "admin/${page}/#csp",  # a computed page
        ],
    )
    def test_not_an_address(self, text: str) -> None:
        assert scan_text(text, "x") == []

    def test_reader_on_a_sample(self, sample_docs: DocsReader) -> None:
        page = sample_docs.page("real")
        assert page is not None
        assert page.defines("explicit-one")
        assert page.defines("plain-heading-here")
        assert page.defines("sample-page")
        assert page.defines("heading-with-code-and-a-link")
        assert not page.defines("real-heading"), "a heading with an explicit id has only that id"
        assert not page.defines("invented-link-target"), "a link to an anchor is not its definition"
        assert not page.defines("in-code"), "an attribute written inside inline code is not a definition"
        assert not page.defines("fenced-id") and not page.defines("fenced-heading"), "a code fence defines nothing"
        assert not page.defines("twice"), "an id written twice is not defined once"
        assert page.repeated() == ["twice"]

    def test_invented_page_and_anchor_are_both_reported(self, sample_docs: DocsReader) -> None:
        sources = """
const a = 'admin/real/#plain-heading-here';
const b = `/mkdocs/admin/real/#explicit-one`;
const c = 'admin/real/';
const d = 'admin/real/#invented-anchor-xyz';
const e = '/mkdocs/admin/invented_page_xyz/#sample-page';
const f = 'admin/other/#other-second';
const g = 'admin/real/#twice';
"""
        problems = reference_problems(scan_text(sources, "synthetic.ts"), sample_docs)
        assert len(problems) == 3, problems
        assert "no anchor invented-anchor-xyz" in problems[0]
        assert "no page invented_page_xyz.en.md" in problems[1]
        assert "writes {: #twice } 2 times" in problems[2]
        assert reference_problems(scan_text("admin/real/#explicit-one admin/other/", "x"), sample_docs) == []

    def test_a_scanner_that_finds_nothing_fails_the_control(self) -> None:
        # The control of the repository scan below, shown to bite: an empty scan is below the floor.
        assert len(scan_text("nothing to see here", "x")) < 20


class TestRepositoryReferences:
    """(a) What the repository's non-test sources say about the admin guide."""

    def test_the_scan_finds_the_references(self) -> None:
        assert len(REFERENCES) >= 20, f"the scan found {len(REFERENCES)} references; the repository has more than that"
        guides = json.loads(CHECK_GUIDES.read_text(encoding="utf-8"))
        wanted = {guide for half in guides.values() for guide in half.values()}
        scanned = {f"admin/{ref.page}/#{ref.anchor}" for ref in REFERENCES if ref.source.endswith("checkGuides.json")}
        assert wanted, "checkGuides.json holds guides"
        assert wanted <= scanned, f"the scan missed guides of checkGuides.json: {sorted(wanted - scanned)}"
        assert any(ref.source.startswith("README") and ref.anchor is None for ref in REFERENCES), "the README's public URLs are found"

    def test_every_reference_reaches_a_page_and_an_anchor(self) -> None:
        problems = reference_problems(REFERENCES, REAL)
        assert problems == [], "references to the admin guide that reach nothing:\n" + "\n".join(problems)

    def test_the_reader_agrees_with_mkdocs_own_render(self) -> None:
        """An anchor the reader defines is an id of MkDocs' render of that page: a reader that accepts everything fails here."""
        pytest.importorskip("mkdocs")
        sys.path.insert(0, str(PAGE_ANCHORS_DIR))
        try:
            from page_anchors import file_anchors  # noqa: PLC0415 — needs MkDocs and the aphra-pipeline folder on sys.path
        finally:
            sys.path.remove(str(PAGE_ANCHORS_DIR))
        disagreements: list[str] = []
        for name in REAL.pages():
            page = REAL.page(name)
            assert page is not None
            rendered = file_anchors(REAL.page_file(name))
            extra = sorted(page.all_defined() - rendered)
            if extra:
                disagreements.append(f"{name}: defined by the reader, not in the render: {extra}")
        assert disagreements == [], "\n".join(disagreements)
        assert len(REAL.pages()) >= 14 + len(NEW_PAGES), "barrier: the admin pages (the old ones and the new) were all rendered"

    def test_new_pages_exist(self) -> None:
        assert [page for page in NEW_PAGES if REAL.page(page) is None] == []

    def test_every_admin_page_is_in_the_navigation(self) -> None:
        nav = MKDOCS_YML.read_text(encoding="utf-8")
        assert [page for page in REAL.pages() if f"admin/{page}.md" not in nav] == [], "an admin page the navigation does not list"


# ---------------------------------------------------------------------------
# (b) The anchors that moved
# ---------------------------------------------------------------------------


def read_moved_anchors(script: str) -> dict[str, dict[str, str]]:
    """``MOVED_ANCHORS`` from the script's text: the object literal after ``var MOVED_ANCHORS = ``, up to the ``;`` that ends it."""
    marker = "var MOVED_ANCHORS = "
    start = script.index(marker) + len(marker)
    value, end = json.JSONDecoder().raw_decode(script, start)
    assert script[end:].lstrip().startswith(";"), "the object literal ends with a ';'"
    assert isinstance(value, dict)
    return value


def _moved_problem(page: str, anchor: str, target: str | None, reader: DocsReader) -> str | None:
    """What is wrong with the map's answer for an anchor the page no longer defines, or None when it is right."""
    if target is None:
        return f"{page}#{anchor}: lost, the page does not define it and the map does not move it"
    if target == page:
        return f"{page}#{anchor}: moved to its own page"
    there = reader.page(target)
    if there is None:
        return f"{page}#{anchor}: moved to {target}, which does not exist"
    if not there.defines(anchor):
        return f"{page}#{anchor}: moved to {target}, which does not define it exactly once"
    return None


def anchor_problems(old: dict[str, list[str]], moved: dict[str, dict[str, str]], reader: DocsReader) -> list[str]:
    """What the split lost: an old anchor neither kept nor moved, and every entry of the map that is stale or wrong."""
    problems: list[str] = []
    for page, anchors in sorted(old.items()):
        here = reader.page(page)
        if here is None:
            problems.append(f"{page}: the page of the fixture does not exist any more")
            continue
        entries = moved.get(page, {})
        for anchor in anchors:
            if not here.defines(anchor):
                problem = _moved_problem(page, anchor, entries.get(anchor), reader)
            elif anchor in entries:
                problem = f"{page}#{anchor}: the page still defines it, and the map moves it to {entries[anchor]}"
            else:
                problem = None
            if problem:
                problems.append(problem)
        problems.extend(f"{page}#{anchor}: in the map, but the old page never had it" for anchor in sorted(set(entries) - set(anchors)))
    problems.extend(f"{page}: in the map, but not among the pages of the fixture" for page in sorted(set(moved) - set(old)))
    return problems


FIXTURE_PAGES: dict[str, list[str]] = json.loads(FIXTURE.read_text(encoding="utf-8"))["pages"]


class TestMovedAnchors:
    """(b) The map of the anchors that moved, against the fixture and the pages."""

    def test_the_map_is_read_from_the_script(self) -> None:
        moved = read_moved_anchors(MOVED_JS.read_text(encoding="utf-8"))
        assert sum(len(entries) for entries in moved.values()) >= 20, "the script moves anchors of the five split pages"
        assert set(moved) <= set(FIXTURE_PAGES)
        assert all(isinstance(target, str) for entries in moved.values() for target in entries.values())

    def test_the_fixture_is_the_five_old_pages(self) -> None:
        assert sorted(FIXTURE_PAGES) == ["configuration", "connection_checks", "email", "service_exposure", "sleep_wake"]
        assert all(anchors == sorted(anchors) and len(anchors) == len(set(anchors)) for anchors in FIXTURE_PAGES.values())
        assert sum(len(anchors) for anchors in FIXTURE_PAGES.values()) >= 100, "the fixture lists the old anchors, not a sample"

    def test_no_anchor_is_lost_and_no_entry_is_stale(self) -> None:
        moved = read_moved_anchors(MOVED_JS.read_text(encoding="utf-8"))
        problems = anchor_problems(FIXTURE_PAGES, moved, REAL)
        assert problems == [], "the split lost or mis-moved anchors:\n" + "\n".join(problems)

    def test_the_check_refuses_each_defect(self, tmp_path: Path) -> None:
        _write(tmp_path / "old.en.md", "# Old\n\n## Kept {: #kept }\n\n## Stale {: #stale }\n")
        _write(tmp_path / "new.en.md", "# New\n\n## Arrived {: #arrived }\n\n## Dup {: #dup }\n\nx {: #dup }\n")
        reader = DocsReader(tmp_path)
        old = {"old": ["arrived", "dup", "gone", "kept", "lost", "stale", "to-missing", "wrong"]}

        clean = {"old": {"arrived": "new"}}
        base = anchor_problems({"old": ["arrived", "kept"]}, clean, reader)
        assert base == [], "control: a kept anchor and a moved one pass"

        moved = {"old": {"arrived": "new", "dup": "new", "gone": "nowhere", "stale": "new", "to-missing": "nowhere", "wrong": "new", "extra": "new"}, "ghost": {"a": "new"}}
        problems = anchor_problems(old, moved, reader)
        text = "\n".join(problems)
        assert "old#lost: lost" in text, "an anchor neither kept nor moved"
        assert "old#stale: the page still defines it" in text, "an entry for an anchor the page still has"
        assert "old#gone: moved to nowhere, which does not exist" in text, "an entry to a missing page"
        assert "old#wrong: moved to new, which does not define it" in text, "an entry to a page without the anchor"
        assert "old#dup: moved to new, which does not define it exactly once" in text, "an anchor written twice on the target"
        assert "old#extra: in the map, but the old page never had it" in text, "an entry the old page never needed"
        assert "ghost: in the map, but not among the pages" in text, "a page that is not in the fixture"
        assert "old#arrived" not in text and "old#kept" not in text, "the good ones are not reported"

    def test_the_script_is_registered(self) -> None:
        config = MKDOCS_YML.read_text(encoding="utf-8")
        assert re.search(r"extra_javascript:(?:\n(?:[ \t]+.*)?)*?\n[ \t]+- javascripts/moved-anchors\.js\b", config), "mkdocs.yml loads the script in extra_javascript"
        assert MOVED_JS.is_file()


# ---------------------------------------------------------------------------
# (c) The built site
# ---------------------------------------------------------------------------

NO_BUILD = "the docs are not built here (no mkdocs_src/site/admin/): run ./dev.py mkdocs build"
needs_built_site = pytest.mark.skipif(not SITE_ADMIN.is_dir(), reason=NO_BUILD)


def built_page_file(page: str) -> Path:
    """Where MkDocs builds ``admin/<page>.en.md``: ``admin/<page>/index.html``; the page named ``index`` is its folder's own, ``admin/index.html``."""
    return SITE_ADMIN / "index.html" if page == "index" else SITE_ADMIN / page / "index.html"


def built_ids(page: str) -> set[str] | None:
    """The ``id`` attributes of a built page, or None when the page is not built."""
    file = built_page_file(page)
    if not file.is_file():
        return None
    return set(re.findall(r'\bid="([^"]+)"', file.read_text(encoding="utf-8")))


@needs_built_site
class TestBuiltSite:
    """(c) The built site carries every address of (a), every page, and the script of (b).

    The site is a build of a past tree: red until ``./dev.py mkdocs build`` runs on the split.
    """

    @pytest.mark.parametrize(("page", "anchor"), ANCHORED, ids=[f"{page}#{anchor}" for page, anchor in ANCHORED])
    def test_the_built_page_has_the_anchor(self, page: str, anchor: str) -> None:
        ids = built_ids(page)
        assert ids is not None, f"{built_page_file(page).relative_to(SITE)} does not exist: the site was built before the page did"
        assert anchor in ids, f'{built_page_file(page).relative_to(SITE)} has no id="{anchor}"'

    def test_the_references_were_found_to_check(self) -> None:
        assert len(ANCHORED) >= 15, "barrier: the parametrized cases above are the anchored references of (a)"

    def test_every_admin_page_is_built(self) -> None:
        missing = [page for page in REAL.pages() if not built_page_file(page).is_file()]
        assert missing == [], f"English admin pages without a built page: {missing}"
        assert set(NEW_PAGES) <= set(REAL.pages()), "barrier: the new pages are in the source, so the built ones are asked for"

    def test_the_built_script_is_the_sources_and_a_page_loads_it(self) -> None:
        built = SITE / "javascripts" / "moved-anchors.js"
        assert built.is_file(), "site/javascripts/moved-anchors.js is not copied: the site was built before the script was registered"
        assert built.read_bytes() == MOVED_JS.read_bytes(), "the built script differs from the source"
        loaders = [page for page in ("configuration", "connection_checks", "email") if built_page_file(page).is_file() and "javascripts/moved-anchors.js" in built_page_file(page).read_text(encoding="utf-8")]
        assert loaders, "no built admin page loads javascripts/moved-anchors.js"
