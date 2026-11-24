"""shared_nav: the menu is written once per language, not in every page (lane 84-D).

Material writes the whole navigation tree into each page (217 KB of 258 KB). ``mkdocs_src/hooks/shared_nav.py`` keeps in each page
what Material itself draws for a *pruned* navigation (the groups of the branch the page is in; every other group one link to its
first page) and writes the whole menu of the language once, ``javascripts/nav/nav.<language>.<hash>.js``, which
``javascripts/nav-enhance.js`` reads while the page is parsed to put the groups back. Pinned here:

* ``find_nav``: the span of the primary ``<nav>``, its nested ``<nav>`` elements included;
* ``prune_menu`` follows Material's rule: a group that is neither active nor a section becomes
  ``<li class="md-nav__item md-nav__item--pruned md-nav__item--nested">`` with one link, to its FIRST page, holding the group's
  label; the active branch and the sections stay whole; a group the shared menu does not hold stays whole;
* ``build_master``: every link of the shared menu is a path from the site's root, the pages at the top level are not in it;
* ``shrink_page``: the menu is pruned, the marks the script reads (``data-lf-nav``, ``data-lf-root``) and the script tag are in,
  a page with no menu or nothing to prune is returned as it was;
* ``script_for``: the menu first, then the code that reads it; the name carries the hash of the whole file (the file is cached immutable);
* ROUND TRIP, the property that matters: putting the groups back (what the script does, here done in Python with the same keys)
  gives, for every page, the DOM the page had before, links compared as paths from the root, whitespace collapsed; on a
  synthetic site and on a copy of real pages;
* ``apply`` writes one script per language and shrinks every page of the language but ``404.html``; ``on_post_build`` runs for
  ``build`` and ``gh-deploy`` only, once; ``mkdocs.yml`` lists the hook.

PURE: trees under ``tmp_path``, the hook loaded by path, lxml. Reads ``mkdocs_src/mkdocs.yml``, ``docs/javascripts/nav-enhance.js``
and, when it exists, a few pages of ``mkdocs_src/site/`` (read only). No DB, no server, no network.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import posixpath
import re
import shutil
from pathlib import Path
from types import ModuleType

import pytest
from lxml import html as lxml_html

from backend.app.services.platform.static_site import is_content_hashed_doc_file

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MKDOCS_SRC = PROJECT_ROOT / "mkdocs_src"
HOOK_ENTRY = "hooks/shared_nav.py"
HOOK = MKDOCS_SRC / HOOK_ENTRY
ENHANCER = MKDOCS_SRC / "docs" / "javascripts" / "nav-enhance.js"
SITE = MKDOCS_SRC / "site"

needs_built_site = pytest.mark.skipif(not (SITE / "user" / "getting-started" / "index.html").exists(), reason="the docs are not built here: run ./dev.py mkdocs build")


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("shared_nav_under_test", HOOK)
    assert spec is not None and spec.loader is not None, f"cannot load {HOOK}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# A page shaped like Material's: tabs (level 1), sections (level 2 under the active tab), groups (level 3), leaves
# ---------------------------------------------------------------------------

#: The site: tab → [section/group → [pages]]. ``Home`` is a page at the top level.
TREE = {
    "user": {"fx": ["rates", "pairs"], "assets": {"detail": ["chart", "signals"], "create": ["new"]}},
    "admin": {"backup": ["moving", "sealed"], "cli": ["tools"]},
}


def _leaf(url: str, base: str, title: str, active: bool = False) -> str:
    cls = "md-nav__item md-nav__item--active" if active else "md-nav__item"
    link = "md-nav__link md-nav__link--active" if active else "md-nav__link"
    return f'<li class="{cls}">\n<a href="{posixpath.relpath(url or ".", base or ".")}/" class="{link}">\n<span class="md-ellipsis">{title}</span>\n</a>\n</li>\n'


def _group(path: str, title: str, inner: str, classes: str, checked: bool, expanded: bool) -> str:
    toggle = "md-nav__toggle md-toggle" + ("" if checked else " md-toggle--indeterminate")
    return (
        f'<li class="{classes} md-nav__item--nested">\n'
        f'<input class="{toggle}" type="checkbox" id="{path}"{" checked" if checked else ""}>\n'
        f'<label class="md-nav__link" for="{path}" id="{path}_label" tabindex="0">\n<span class="md-ellipsis">{title}</span>\n<span class="md-nav__icon md-icon"></span>\n</label>\n'
        f'<nav class="md-nav" data-md-level="1" aria-labelledby="{path}_label" aria-expanded="{"true" if expanded else "false"}">\n'
        f'<ul class="md-nav__list" data-md-scrollfix>\n{inner}</ul>\n</nav>\n</li>\n'
    )


def material_menu(page: str) -> str:
    """The primary menu of ``page`` (a URL path from the root, ``user/assets/detail/chart``) as Material writes it."""
    base = page  # the page's own folder (the site's root for the home page)
    items = [_leaf("", base, "Home", active=page == "")]
    for ti, (tab, sections) in enumerate(TREE.items(), start=1):
        tab_active = page.startswith(tab + "/")
        sections_html = ""
        for si, (section, content) in enumerate(sections.items(), start=1):
            section_active = page.startswith(f"{tab}/{section}/")
            if isinstance(content, dict):
                groups_html = ""
                for gi, (group, pages) in enumerate(content.items(), start=1):
                    group_active = page.startswith(f"{tab}/{section}/{group}/")
                    leaves = "".join(_leaf(f"{tab}/{section}/{group}/{p}", base, p.title(), active=page == f"{tab}/{section}/{group}/{p}") for p in pages)
                    groups_html += _group(f"__nav_{ti}_{si}_{gi}", group.title(), leaves, "md-nav__item" + (" md-nav__item--active" if group_active else ""), group_active, group_active)
                inner = groups_html
            else:
                inner = "".join(_leaf(f"{tab}/{section}/{p}", base, p.title(), active=page == f"{tab}/{section}/{p}") for p in content)
            classes = "md-nav__item" + (" md-nav__item--active" if section_active else "") + (" md-nav__item--section" if tab_active else "")
            sections_html += _group(f"__nav_{ti}_{si}", section.title(), inner, classes, section_active, section_active)
        classes = "md-nav__item" + (" md-nav__item--active" if tab_active else "") + (" md-nav__item--section" if tab_active else "")
        items += _group(f"__nav_{ti}", tab.title(), sections_html, classes, tab_active, tab_active)
    return (
        '<nav class="md-nav md-nav--primary md-nav--lifted" aria-label="Navigation" data-md-level="0">\n'
        '<label class="md-nav__title" for="__drawer"><a href="x" class="md-nav__button md-logo"><img src="../static/logo.png" alt="logo"></a>Site</label>\n'
        f'<ul class="md-nav__list" data-md-scrollfix>\n{"".join(items)}</ul>\n</nav>'
    )


def page_html(page: str, language_folder: str = "") -> str:
    return f'<!doctype html><html><body><div class="md-sidebar md-sidebar--primary"><div class="md-sidebar__inner">{material_menu(page)}</div></div><main><p>{page}</p></main></body></html>\n'


def all_pages() -> list[str]:
    pages = [""]
    for tab, sections in TREE.items():
        for section, content in sections.items():
            for group, group_pages in content.items() if isinstance(content, dict) else [(None, content)]:
                pages += [f"{tab}/{section}/{group + '/' if group else ''}{p}" for p in group_pages]
    return pages


# ---------------------------------------------------------------------------
# What the script does, in Python, with the same keys: the round trip
# ---------------------------------------------------------------------------


def _norm(element):
    return (
        element.tag,
        tuple(sorted(element.attrib.items())),
        re.sub(r"\s+", " ", element.text or "").strip(),
        tuple(_norm(child) for child in element),
        re.sub(r"\s+", " ", element.tail or "").strip(),
    )


def expand(hook: ModuleType, shrunk_nav, master: str, page_dir_url: str):
    """Put the groups back in a pruned menu: the script's algorithm."""
    root = shrunk_nav.get("data-lf-root") or ""
    groups: dict = {}
    for item in lxml_html.fragment_fromstring(master).iter("li"):
        if "md-nav__item--nested" in hook._classes(item):
            groups.setdefault((hook.depth_of(item), hook.first_page(item)), item)
    for stub in [li for li in shrunk_nav.iter("li") if "md-nav__item--pruned" in hook._classes(li)]:
        group = groups.get((hook.depth_of(stub), hook.to_root_relative(hook.first_page(stub), page_dir_url)))
        if group is None:
            continue
        clone = copy.deepcopy(group)
        for link in clone.xpath(".//a[@href]"):
            link.set("href", root + link.get("href"))
        clone.tail = stub.tail
        stub.getparent().replace(stub, clone)
    return shrunk_nav


def comparable(hook: ModuleType, nav, page_dir_url: str):
    """The menu as the browser reads it: the marks of the hook dropped, every link a path from the root."""
    nav = copy.deepcopy(nav)
    for mark in ("data-lf-nav", "data-lf-root"):
        nav.attrib.pop(mark, None)
    for link in nav.xpath(".//a[@href]"):
        link.set("href", hook.to_root_relative(link.get("href"), page_dir_url))
    return _norm(nav)


def round_trip_ok(hook: ModuleType, original: str, shrunk: str, master: str, page_dir_url: str) -> bool:
    before = lxml_html.fragment_fromstring(original[slice(*hook.find_nav(original))])
    after = expand(hook, lxml_html.fragment_fromstring(shrunk[slice(*hook.find_nav(shrunk))]), master, page_dir_url)
    return comparable(hook, before, page_dir_url) == comparable(hook, after, page_dir_url)


def master_of(hook: ModuleType) -> str:
    master = hook.build_master(page_html(""), "")
    assert master is not None
    return master


# ---------------------------------------------------------------------------
# find_nav / prune / master / shrink
# ---------------------------------------------------------------------------


class TestFindNav:
    def test_the_span_holds_the_nested_navs(self, hook):
        page = page_html("user/fx/rates")
        start, end = hook.find_nav(page)

        assert page[start:end].startswith('<nav class="md-nav md-nav--primary') and page[start:end].endswith("</nav>")
        assert page[start:end].count("<nav") == page[start:end].count("</nav>") > 3

    def test_a_page_without_a_menu_has_none(self, hook):
        assert hook.find_nav("<html><body><nav class='md-tabs'>x</nav></body></html>") is None


class TestPrune:
    def test_the_active_branch_stays_and_the_rest_is_one_link_to_its_first_page(self, hook):
        page = "user/assets/detail/chart"
        nav = lxml_html.fragment_fromstring(material_menu(page))
        known = hook.master_keys(master_of(hook))

        count = hook.prune_menu(nav, "user/assets/detail/chart/", known)

        assert count > 0
        pruned = {hook.first_page(li): li for li in nav.iter("li") if "md-nav__item--pruned" in hook._classes(li)}
        # the other tab: pruned, the link goes to its first page
        admin = next(li for li in pruned.values() if "Admin" in li.text_content())
        assert admin.xpath("./a")[0].get("href") == "../../../../admin/backup/moving/"
        assert hook._classes(admin) == ["md-nav__item", "md-nav__item--pruned", "md-nav__item--nested"]
        assert len(admin) == 1 and admin[0].tag == "a" and admin[0].get("class") == "md-nav__link"
        assert admin[0].xpath("./span[@class='md-ellipsis']")[0].text == "Admin" and admin[0].xpath("./span[contains(@class,'md-icon')]")
        # the branch of the page is whole: the user tab, its sections (assets, fx stays a section), the active group
        assert nav.xpath("//li[contains(@class,'md-nav__item--active') and contains(@class,'md-nav__item--nested')]//input[@checked]")
        assert nav.xpath("//a[contains(@class,'md-nav__link--active')]")
        # a section of the active tab is never pruned, even when it is not the page's own
        assert any("Fx" in li.text_content() and "md-nav__item--pruned" not in hook._classes(li) for li in nav.xpath("//li[contains(@class,'md-nav__item--section')]"))

    def test_a_group_the_shared_menu_does_not_hold_stays_whole(self, hook):
        nav = lxml_html.fragment_fromstring(material_menu("user/fx/rates"))

        count = hook.prune_menu(nav, "user/fx/rates/", set())

        assert count == 0 and not nav.xpath("//li[contains(@class,'md-nav__item--pruned')]")

    def test_a_group_of_a_shape_the_hook_does_not_know_stays_whole(self, hook):
        group = lxml_html.fragment_fromstring('<li class="md-nav__item md-nav__item--nested"><a href="x/">no label</a></li>')

        assert hook.prune_item(group) is False and group.xpath("./a")


class TestMaster:
    def test_every_link_is_a_path_from_the_root_and_the_top_pages_are_left_out(self, hook):
        master = master_of(hook)

        links = re.findall(r'href="([^"]*)"', master)
        assert links and all(not link.startswith(("../", "./", "/")) for link in links)
        assert "user/fx/rates/" in links and "admin/cli/tools/" in links
        fragment = lxml_html.fragment_fromstring(master)
        assert all("md-nav__item--nested" in hook._classes(li) for li in fragment.xpath("./li"))  # no Home

    def test_it_is_built_from_a_page_in_a_folder_too(self, hook):
        master = hook.build_master(page_html(""), "it/")

        assert master is not None
        links = re.findall(r'href="([^"]*)"', master)
        assert links and all(link.startswith("it/") for link in links)  # the folder of the language is part of the path


class TestShrink:
    def test_the_menu_is_pruned_and_marked_and_the_script_is_added(self, hook):
        page = page_html("user/fx/rates")
        known = hook.master_keys(master_of(hook))

        shrunk, count = hook.shrink_page(page, "user/fx/rates/", "en", "javascripts/nav/nav.en.abc.js", known)

        assert count > 0 and len(shrunk) < len(page)
        assert 'data-lf-nav="en"' in shrunk and 'data-lf-root="../../../"' in shrunk
        assert shrunk.count('<script src="../../../javascripts/nav/nav.en.abc.js"></script>') == 1
        # the script comes right after the menu: it reads its previous sibling
        assert re.search(r"</nav><script src=", shrunk)

    def test_a_page_without_a_menu_or_with_nothing_to_prune_is_returned_as_it_was(self, hook):
        plain = "<html><body><p>x</p></body></html>"
        assert hook.shrink_page(plain, "x/", "en", "s.js", set()) == (plain, 0)
        page = page_html("user/fx/rates")
        assert hook.shrink_page(page, "user/fx/rates/", "en", "s.js", set()) == (page, 0)


class TestScript:
    def test_the_menu_comes_first_and_the_name_carries_the_hash_of_the_whole_file(self, hook):
        name, content = hook.script_for("it", "<ul>menu è</ul>", "(function(){/* code */})();\n")
        other, _ = hook.script_for("it", "<ul>other</ul>", "x")

        assert re.fullmatch(r"javascripts/nav/nav\.it\.[0-9a-f]{10}\.js", name) and name != other
        assert content.index("window.LF_NAV") < content.index("/* code */")
        assert json.dumps("<ul>menu è</ul>", ensure_ascii=False) in content  # accents are kept, not escaped
        # The file is cached for a year under its name (static_site.py): the name follows the menu AND the code, so a change
        # of the enhancer alone, with the same menu, is a new name and never a stale copy
        assert hook.script_for("it", "<ul>menu è</ul>", "y")[0] != name
        assert hook.script_for("it", "<ul>menu è</ul>", "(function(){/* code */})();\n")[0] == name  # same content, same name
        assert hook.script_for("fr", "<ul>menu è</ul>", "(function(){/* code */})();\n")[0] != name

    def test_the_name_is_one_the_backend_sends_cached_for_a_year(self, hook):
        for language in hook.LANGUAGES:
            assert is_content_hashed_doc_file(hook.script_for(language, "<ul>menu</ul>", "code")[0])


# ---------------------------------------------------------------------------
# The round trip, on a site
# ---------------------------------------------------------------------------


def write_site(site: Path, language: str = "") -> None:
    folder = site / language if language else site
    for page in all_pages():
        target = folder / page / "index.html" if page else folder / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html(page), encoding="utf-8")
    (site / "404.html").write_text(page_html("user/fx/rates"), encoding="utf-8")


class TestRoundTrip:
    def test_every_page_of_the_site_has_the_menu_it_had(self, hook, tmp_path):
        write_site(tmp_path)
        originals = {p: p.read_text(encoding="utf-8") for p in hook.pages_of(tmp_path, "en")}

        totals = hook.apply(tmp_path, ENHANCER.read_text(encoding="utf-8"), ("en",))

        assert totals["scripts"] == 1 and totals["pages"] == len(originals)
        script = next((tmp_path / "javascripts" / "nav").glob("nav.en.*.js")).read_text(encoding="utf-8")
        master = json.loads(re.match(r'\(window\.LF_NAV = window\.LF_NAV \|\| \{\}\)\["en"\] = (".*?");\n', script, re.DOTALL).group(1))
        for page, original in originals.items():
            relative = page.parent.relative_to(tmp_path).as_posix()
            folder = "" if relative == "." else relative + "/"
            assert round_trip_ok(hook, original, page.read_text(encoding="utf-8"), master, folder), f"the menu of {folder or 'the home page'} is not the one it had"
        assert sum(len(text.encode()) for text in originals.values()) > 1.5 * sum(p.stat().st_size for p in originals)  # and the pages are smaller

    def test_404_is_left_alone_and_the_other_languages_do_not_touch_each_other(self, hook, tmp_path):
        write_site(tmp_path)
        write_site(tmp_path, "it")
        not_found = (tmp_path / "404.html").read_text(encoding="utf-8")

        totals = hook.apply(tmp_path, "/* e */", ("en", "it"))

        assert totals["scripts"] == 2 and (tmp_path / "404.html").read_text(encoding="utf-8") == not_found
        assert 'data-lf-nav="it"' in (tmp_path / "it" / "user" / "fx" / "rates" / "index.html").read_text(encoding="utf-8")
        assert 'data-lf-nav="en"' in (tmp_path / "user" / "fx" / "rates" / "index.html").read_text(encoding="utf-8")
        assert len(list((tmp_path / "javascripts" / "nav").glob("*.js"))) == 2

    def test_a_language_without_a_home_page_is_skipped(self, hook, tmp_path):
        write_site(tmp_path)

        assert hook.apply(tmp_path, "/* e */", ("de",)) == {"pages": 0, "groups": 0, "scripts": 0}


class TestEvents:
    def test_it_runs_for_build_and_deploy_only_and_once(self, hook, tmp_path):
        write_site(tmp_path)
        (tmp_path / "docs" / "javascripts").mkdir(parents=True)
        (tmp_path / "docs" / "javascripts" / "nav-enhance.js").write_text("/* e */", encoding="utf-8")
        probe = tmp_path / "user" / "fx" / "rates" / "index.html"
        original = probe.read_text(encoding="utf-8")

        class Plugin:
            building = False

        class Config(dict):
            plugins = {"i18n": Plugin()}

        config = Config(site_dir=str(tmp_path), docs_dir=str(tmp_path / "docs"))

        hook.on_startup("serve", False)
        hook.on_post_build(config)
        assert probe.read_text(encoding="utf-8") == original

        hook.on_startup("build", False)
        config.plugins["i18n"].building = True
        hook.on_post_build(config)
        assert probe.read_text(encoding="utf-8") == original

        config.plugins["i18n"].building = False
        hook.on_post_build(config)
        assert 'data-lf-nav="en"' in probe.read_text(encoding="utf-8")

    def test_the_hook_is_registered_after_the_english_only_hook(self):
        hooks = re.search(r"^hooks:\n((?:[ \t]+-[^\n]*\n)+)", (MKDOCS_SRC / "mkdocs.yml").read_text(encoding="utf-8"), flags=re.MULTILINE)

        assert hooks is not None and f"- {HOOK_ENTRY}" in hooks.group(1)

    def test_the_script_the_pages_load_is_in_the_sources(self):
        code = ENHANCER.read_text(encoding="utf-8")

        assert "li.md-nav__item--pruned" in code and "window.LF_NAV" in code and "data-lf-root" in code


@needs_built_site
class TestBuiltSite:
    """The same round trip on a copy of real pages (the site as it is built, before or after the hook ran: the hook is
    idempotent on a page it already shrank)."""

    PAGES = ("index.html", "user/getting-started/index.html", "developer/dev_workflow/index.html", "admin/cli_tools/index.html", "financial-theory/fundamentals/day-count/index.html")

    def test_real_pages_keep_their_menu(self, hook, tmp_path):
        site = tmp_path / "site"
        for page in self.PAGES:
            (site / page).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(SITE / page, site / page)
        originals = {page: (site / page).read_text(encoding="utf-8") for page in self.PAGES}
        if any("data-lf-nav" in text for text in originals.values()):
            pytest.skip("the site was built with the hook already in: its pages are shrunk, there is no original to compare with")

        hook.apply(site, ENHANCER.read_text(encoding="utf-8"), ("en",))

        script = next((site / "javascripts" / "nav").glob("nav.en.*.js")).read_text(encoding="utf-8")
        master = json.loads(re.match(r'\(window\.LF_NAV = window\.LF_NAV \|\| \{\}\)\["en"\] = (".*?");\n', script, re.DOTALL).group(1))
        for page in self.PAGES:
            shrunk = (site / page).read_text(encoding="utf-8")
            folder = posixpath.dirname(page) + "/" if "/" in page else ""
            assert len(shrunk) < 0.5 * len(originals[page]), f"{page} is not much smaller"
            assert round_trip_ok(hook, originals[page], shrunk, master, folder), f"the menu of {page} is not the one it had"
