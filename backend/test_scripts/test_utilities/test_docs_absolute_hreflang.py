"""
The ``hreflang`` alternates of the documentation's pages are absolute and keep the site's path (lane 84, DW-2).

Under test: ``mkdocs_src/hooks/absolute_hreflang.py``. Material writes ``<link rel="alternate" href=… hreflang=…>`` from
``extra.alternate``, whose links ``mkdocs-static-i18n`` fills with the other languages' addresses; MkDocs' ``url`` filter
makes each of them relative to the page that holds it (``../it/user/`` on ``user/``). Google wants them absolute. The hook
used to resolve them against ``site_url``: ``urljoin("https://host/LibreFolio/", "../it/user/")`` is
``https://host/it/user/``, an address of a site that is not there, and the English alternate of every page led to the
home. Pinned here:

* a relative alternate is resolved from the page that holds it, and the site's path (``/LibreFolio/``) is kept, from the home,
  a page and a page two folders deep, in every language;
* an alternate that is already absolute, or starts with ``/`` (the home pages), stays what it is;
* the order of the attributes does not matter, and only ``rel="alternate" hreflang`` links are touched (the canonical and the
  RSS links are not);
* without a ``site_url`` the page is not touched; the hook is idempotent;
* on a site that is built here, every alternate of every page leads to a page of the site (its ``index.html`` exists) in the
  language it names, and the English developer pages name no translation (skipped when the docs are not built; a site built
  BEFORE the fix is red here, by design: it needs a ``mkdocs build`` made after the patch).

PURE: strings, the hook loaded by path; the built-site check only reads.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MKDOCS_SRC = PROJECT_ROOT / "mkdocs_src"
HOOK = MKDOCS_SRC / "hooks" / "absolute_hreflang.py"
SITE = MKDOCS_SRC / "site"
SITE_URL = "https://librefolio.github.io/LibreFolio/"

needs_built_site = pytest.mark.skipif(not (SITE / "user" / "getting-started" / "index.html").exists(), reason="the docs are not built here: run ./dev.py mkdocs build")


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("absolute_hreflang_under_test", HOOK)
    assert spec is not None and spec.loader is not None, f"cannot load {HOOK}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def head(*alternates: tuple[str, str]) -> str:
    """The head of a page as Material writes it: the canonical, then one alternate per language."""
    lines = [f'<link rel="canonical" href="{SITE_URL}user/">']
    lines += [f'<link rel="alternate" href="{href}" hreflang="{lang}">' for lang, href in alternates]
    lines.append('<link rel="alternate" type="application/rss+xml" title="RSS" href="feed_rss_created.xml">')
    return "\n".join(lines)


def alternates_of(page: str) -> dict[str, str]:
    return {m.group(2): m.group(1) for m in re.finditer(r'<link rel="alternate" href="([^"]*)" hreflang="([^"]*)">', page)}


def run(hook: ModuleType, page_html: str, page_url: str, site_url: str = SITE_URL) -> str:
    return hook.on_post_page(page_html, SimpleNamespace(url=page_url), {"site_url": site_url})


class TestResolution:
    @pytest.mark.parametrize(
        ("page_url", "relative"),
        [
            ("user/", {"en": "./", "it": "../it/user/", "fr": "../fr/user/", "es": "../es/user/"}),
            ("user/fx/rates/", {"en": "./", "it": "../../../it/user/fx/rates/", "fr": "../../../fr/user/fx/rates/", "es": "../../../es/user/fx/rates/"}),
            ("it/user/fx/", {"en": "../../../user/fx/", "it": "./", "fr": "../../../fr/user/fx/", "es": "../../../es/user/fx/"}),
        ],
        ids=["page", "nested-page", "italian-page"],
    )
    def test_a_relative_alternate_is_resolved_from_its_page_and_keeps_the_site_path(self, hook, page_url, relative):
        page = head(*relative.items())

        fixed = alternates_of(run(hook, page, page_url))

        base = page_url.removeprefix("it/") if page_url.startswith("it/") else page_url
        expected = {"en": f"{SITE_URL}{base}", "it": f"{SITE_URL}it/{base}", "fr": f"{SITE_URL}fr/{base}", "es": f"{SITE_URL}es/{base}"}
        assert fixed == expected

    def test_an_alternate_that_starts_with_a_slash_or_is_absolute_is_not_changed(self, hook):
        page = head(("en", "/LibreFolio/"), ("it", "/LibreFolio/it/"), ("fr", "https://elsewhere.example/fr/"))

        assert alternates_of(run(hook, page, "")) == {"en": "https://librefolio.github.io/LibreFolio/", "it": "https://librefolio.github.io/LibreFolio/it/", "fr": "https://elsewhere.example/fr/"}

    def test_a_site_without_a_path_resolves_from_its_root(self, hook):
        page = head(("it", "../it/user/"))

        assert alternates_of(run(hook, page, "user/", site_url="https://docs.example.org/")) == {"it": "https://docs.example.org/it/user/"}

    def test_the_other_links_and_the_rest_of_the_page_are_not_touched(self, hook):
        page = head(("it", "../it/user/")) + '\n<body><a href="../it/user/">text</a></body>'

        fixed = run(hook, page, "user/")

        assert f'<link rel="canonical" href="{SITE_URL}user/">' in fixed
        assert 'href="feed_rss_created.xml"' in fixed
        assert '<a href="../it/user/">text</a>' in fixed

    def test_the_order_of_the_attributes_does_not_matter(self, hook):
        page = '<link href="../it/user/" rel="alternate" hreflang="it">'

        assert run(hook, page, "user/") == f'<link href="{SITE_URL}it/user/" rel="alternate" hreflang="it">'

    def test_without_a_site_url_the_page_is_left_as_it_is_and_the_hook_is_idempotent(self, hook):
        page = head(("it", "../it/user/"))

        assert run(hook, page, "user/", site_url="") == page
        once = run(hook, page, "user/")
        assert run(hook, once, "user/") == once


@needs_built_site
def test_every_alternate_of_the_built_site_leads_to_a_page_of_the_site_in_its_language():
    """Needs a ``mkdocs build`` made after the hook's fix: a site built before it is red here, by design (its alternates are the defect)."""
    wrong: list[str] = []
    developer_translations: list[str] = []
    for path in sorted(SITE.rglob("*.html")):
        if path.name == "404.html":
            continue
        relative = path.relative_to(SITE).as_posix()
        for match in re.finditer(r'<link\b[^>]*\brel="alternate"[^>]*\bhreflang="([^"]*)"[^>]*>', path.read_text(encoding="utf-8")):
            language = match.group(1)
            href = re.search(r'\bhref="([^"]*)"', match.group(0))
            address = href.group(1) if href else ""
            if not address.startswith(SITE_URL):
                wrong.append(f"{relative}: {address} (outside the site address)")
                continue
            target = address[len(SITE_URL) :]
            folder = target.split("/")[0]
            if (folder if folder in ("it", "fr", "es") else "en") != language:
                wrong.append(f"{relative}: hreflang={language} leads to {address} (another language's folder)")
            elif not (SITE / target / "index.html").is_file():
                wrong.append(f"{relative}: {address} is not a page of the site")
            if relative.startswith("developer/") and language != "en":
                developer_translations.append(f"{relative}: {address}")
    shown = wrong[:5] + ([f"… and {len(wrong) - 5} more"] if len(wrong) > 5 else [])
    assert not wrong, "an alternate leads astray:\n" + "\n".join(shown)
    assert not developer_translations, "an English developer page names a translation that does not exist:\n" + "\n".join(developer_translations[:5])
