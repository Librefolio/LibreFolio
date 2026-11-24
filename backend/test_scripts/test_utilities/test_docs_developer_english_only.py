"""developer_english_only: the developer manual is built once, in English (lane 84-E).

``mkdocs-static-i18n`` copies each of the 142 pages of ``docs/developer/`` (English only, by design) into ``it/``, ``fr/``
and ``es/`` as the fallback of a missing translation: 113 MB of the same text under three more canonical addresses.
``mkdocs_src/hooks/developer_english_only.py`` replaces the copies after the build. Pinned here:

* which pages are copies: those under ``<lang>/developer/`` that no ``<name>.<lang>.md`` translates (``index.<lang>.md`` is the
  section's home); a translated page stays a real page;
* ``redirect_page``: the page that stands in for a copy goes to the English page (``meta refresh`` and a script that keeps the
  query and the ``#anchor``), is ``noindex``, names the English page as canonical, keeps the title, escapes it;
* ``apply`` on a built site: every copy becomes that page, the links of the other pages of the language lead straight to the
  English page (relative links from any depth, fragments and queries kept, ``index.html`` forms too; external links, other
  sections and translated pages untouched), the English pages' head stops naming the copies as ``hreflang`` alternates, and
  ``sitemap.xml`` and its ``.gz`` stop listing them and the alternates that named them; a site with no copies is left as it
  is, and a second run changes nothing;
* ``on_post_build``: runs for ``build`` and ``gh-deploy``, not for ``serve`` and not inside the nested per-language build;
* a sample of the real built site (when there is one): the same, on its pages;
* the registration: ``mkdocs.yml`` lists the hook.

PURE: trees under ``tmp_path``, the hook loaded by path. Reads ``mkdocs_src/mkdocs.yml`` and, when it exists, a few pages of
``mkdocs_src/site/`` (read only). No DB, no server, no network, no writes outside ``tmp_path``.
"""

from __future__ import annotations

import gzip
import importlib.util
import re
import shutil
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MKDOCS_SRC = PROJECT_ROOT / "mkdocs_src"
HOOK_ENTRY = "hooks/developer_english_only.py"
HOOK = MKDOCS_SRC / HOOK_ENTRY
SITE = MKDOCS_SRC / "site"
SITE_URL = "https://example.org/LibreFolio/"

needs_built_site = pytest.mark.skipif(not (SITE / "developer" / "architecture" / "overview" / "index.html").exists(), reason="the docs are not built here: run ./dev.py mkdocs build")


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("developer_english_only_under_test", HOOK)
    assert spec is not None and spec.loader is not None, f"cannot load {HOOK}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def english_page(url: str, title: str = "API") -> str:
    """An English developer page, with the alternates the i18n plugin writes in its head (some without the site's folder)."""
    return (
        f'<!doctype html><html lang="en"><head><title>{title} - LibreFolio</title>\n'
        f'<link rel="canonical" href="{SITE_URL}{url}">\n'
        f'<link rel="alternate" href="{SITE_URL}{url}" hreflang="en">\n'
        f'<link rel="alternate" href="https://example.org/it/{url}" hreflang="it">\n'
        f'<link rel="alternate" href="{SITE_URL}fr/{url}" hreflang="fr">\n'
        f'<link rel="alternate" hreflang="es" href="{SITE_URL}es/{url}">\n'
        "</head><body><p>Manual</p></body></html>\n"
    )


SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
    <url>
        <loc>https://example.org/LibreFolio/user/x/</loc>
        <xhtml:link rel="alternate" hreflang="en" href="https://example.org/LibreFolio/user/x/"/>
        <xhtml:link rel="alternate" hreflang="it" href="https://example.org/LibreFolio/it/user/x/"/>
    </url>
    <url>
        <loc>https://example.org/LibreFolio/developer/api/</loc>
        <xhtml:link rel="alternate" hreflang="en" href="https://example.org/LibreFolio/developer/api/"/>
        <xhtml:link rel="alternate" hreflang="it" href="https://example.org/LibreFolio/it/developer/api/"/>
        <xhtml:link rel="alternate" hreflang="fr" href="https://example.org/LibreFolio/fr/developer/api/"/>
    </url>
    <url>
        <loc>https://example.org/LibreFolio/it/developer/api/</loc>
    </url>
    <url>
        <loc>https://example.org/LibreFolio/it/developer/translated/</loc>
    </url>
</urlset>
"""


@pytest.fixture
def tree(tmp_path) -> tuple[Path, Path]:
    """A small built site and its sources: ``developer/api`` and ``developer`` are English only, ``developer/translated`` has an
    Italian source."""
    docs, site = tmp_path / "docs", tmp_path / "site"
    for source in ("developer/index.md", "developer/api.md", "developer/translated.md", "developer/translated.it.md", "user/x.md"):
        write(docs / source, "# page\n")
    for lang in ("", "it/", "fr/", "es/"):
        for url in ("developer/", "developer/api/", "developer/translated/"):
            if lang == "" or lang == "it/" or url != "developer/translated/":
                write(site / f"{lang}{url}index.html", english_page(url, f"Page of {lang}{url}") if lang == "" else f'<html><head><title>Copy of {lang}{url}</title></head><body><a href="../x/">x</a></body></html>')
    write(
        site / "it" / "user" / "x" / "index.html",
        '<html><body><a href="../../developer/api/">api</a> <a href="../../developer/api/#section">anchor</a> <a href="../../developer/">home</a> <a href="../../developer/api/index.html">index</a> <a href="../../developer/api/?q=1#z">query</a> <a href="../../developer/translated/">translated</a> <a href="../y/">other</a> <a href="https://example.org/it/developer/api/">external</a> <a href="#top">top</a></body></html>',
    )
    write(site / "fr" / "user" / "x" / "index.html", '<html><body><a href="../../developer/api/">api</a></body></html>')
    write(site / "user" / "x" / "index.html", '<html><body><a href="../../developer/api/">api</a></body></html>')
    write(site / "sitemap.xml", SITEMAP)
    (site / "sitemap.xml.gz").write_bytes(gzip.compress(SITEMAP.encode()))
    return docs, site


class TestWhichPagesAreCopies:
    def test_the_translated_pages_are_found_by_their_source(self, hook, tree):
        docs, _ = tree

        assert hook.translated_urls(docs, "it") == {"developer/translated/"}
        write(docs / "developer" / "index.it.md", "# home\n")
        assert hook.translated_urls(docs, "it") == {"developer/translated/", "developer/"}
        assert hook.translated_urls(docs, "fr") == set()

    def test_a_copy_is_a_page_of_the_language_without_a_translation(self, hook, tree):
        docs, site = tree

        copies = [hook.page_url(site, page) for page in hook.fallback_copies(site, docs, "it")]

        assert set(copies) == {"it/developer/", "it/developer/api/"} and len(copies) == 2  # `translated` has an Italian source: it stays
        assert {hook.page_url(site, p) for p in hook.fallback_copies(site, docs, "fr")} == {"fr/developer/", "fr/developer/api/"}
        assert hook.fallback_copies(site, docs, "de") == []


class TestRedirectPage:
    def test_it_goes_to_the_english_page_and_keeps_the_anchor(self, hook):
        page = hook.redirect_page("it", "Overview & more <b>", "../../../developer/api/", "https://example.org/LibreFolio/developer/api/")

        assert '<meta http-equiv="refresh" content="0; url=../../../developer/api/">' in page
        assert 'location.replace("../../../developer/api/" + location.search + location.hash)' in page
        assert '<meta name="robots" content="noindex">' in page
        assert '<link rel="canonical" href="https://example.org/LibreFolio/developer/api/">' in page
        assert "<title>Overview &amp; more &lt;b&gt;</title>" in page
        assert '<a href="../../../developer/api/">open this page in English</a>' in page
        assert len(page) < 800

    def test_a_page_without_title_or_canonical_is_still_a_redirect(self, hook):
        page = hook.redirect_page("fr", "", "../developer/", "")

        assert "<title>LibreFolio</title>" in page and "canonical" not in page and "refresh" in page


class TestApply:
    def test_every_copy_becomes_a_redirect_to_its_english_page(self, hook, tree):
        docs, site = tree

        counts = hook.apply(site, docs, SITE_URL)

        assert counts["stubs"] == 6  # it, fr and es: home and api (`translated` has an Italian source: it stays)
        stub = (site / "it" / "developer" / "api" / "index.html").read_text(encoding="utf-8")
        assert "url=../../../developer/api/" in stub and "Copy of it/developer/api/" in stub
        assert 'canonical" href="https://example.org/LibreFolio/developer/api/"' in stub
        assert "url=../../developer/" in (site / "it" / "developer" / "index.html").read_text(encoding="utf-8")
        # the translated page is still its own page
        assert "refresh" not in (site / "it" / "developer" / "translated" / "index.html").read_text(encoding="utf-8")
        # the English pages are untouched but for their head
        assert "<p>Manual</p>" in (site / "developer" / "api" / "index.html").read_text(encoding="utf-8")

    def test_the_links_of_the_other_pages_lead_to_the_english_pages(self, hook, tree):
        docs, site = tree

        hook.apply(site, docs, SITE_URL)

        page = (site / "it" / "user" / "x" / "index.html").read_text(encoding="utf-8")
        assert page.count('href="../../../developer/api/"') == 2  # plain and the `index.html` form
        assert 'href="../../../developer/api/#section"' in page
        assert 'href="../../../developer/"' in page
        assert 'href="../../../developer/api/?q=1#z"' in page
        # untouched: a translated page, another section, an external address, an anchor
        assert 'href="../../developer/translated/"' in page
        assert 'href="../y/"' in page and 'href="https://example.org/it/developer/api/"' in page and 'href="#top"' in page
        assert 'href="../../../developer/api/"' in (site / "fr" / "user" / "x" / "index.html").read_text(encoding="utf-8")
        # the English pages are not rewritten
        assert 'href="../../developer/api/"' in (site / "user" / "x" / "index.html").read_text(encoding="utf-8")

    def test_the_english_head_stops_naming_the_copies(self, hook, tree):
        docs, site = tree

        hook.apply(site, docs, SITE_URL)

        head = (site / "developer" / "api" / "index.html").read_text(encoding="utf-8")
        assert 'hreflang="en"' in head and 'rel="canonical"' in head
        assert not re.search(r'hreflang="(it|fr|es)"', head)  # all three copies were replaced

    def test_the_sitemap_and_its_gz_stop_listing_the_copies(self, hook, tree):
        docs, site = tree

        hook.apply(site, docs, SITE_URL)

        text = (site / "sitemap.xml").read_text(encoding="utf-8")
        assert "/it/developer/api/" not in text and "/fr/developer/api/" not in text
        assert "/it/developer/translated/" in text  # a translated page is listed
        assert "https://example.org/LibreFolio/it/user/x/" in text  # other alternates stay
        assert text.count("<url>") == 3 and text.count("</url>") == 3
        assert gzip.decompress((site / "sitemap.xml.gz").read_bytes()).decode() == text

    def test_a_second_run_changes_nothing(self, hook, tree):
        docs, site = tree
        hook.apply(site, docs, SITE_URL)
        before = {p: p.read_bytes() for p in site.rglob("*") if p.is_file()}

        hook.apply(site, docs, SITE_URL)

        assert {p: p.read_bytes() for p in site.rglob("*") if p.is_file()} == before

    def test_a_site_without_copies_is_left_alone(self, hook, tmp_path):
        write(tmp_path / "docs" / "user" / "x.md", "# x\n")
        write(tmp_path / "site" / "index.html", "<html></html>")

        assert hook.apply(tmp_path / "site", tmp_path / "docs", SITE_URL) == {"stubs": 0, "pages": 0}
        assert (tmp_path / "site" / "index.html").read_text(encoding="utf-8") == "<html></html>"


class TestEvents:
    def test_it_runs_for_build_and_deploy_only_and_once(self, hook, tree, monkeypatch):
        docs, site = tree

        class Plugin:
            building = False

        class Config(dict):
            plugins = {"i18n": Plugin()}

        config = Config(site_dir=str(site), docs_dir=str(docs), site_url=SITE_URL)
        probe = site / "it" / "developer" / "api" / "index.html"
        original = probe.read_text(encoding="utf-8")

        hook.on_startup("serve", False)
        hook.on_post_build(config)
        assert probe.read_text(encoding="utf-8") == original

        hook.on_startup("build", False)
        config.plugins["i18n"].building = True
        hook.on_post_build(config)
        assert probe.read_text(encoding="utf-8") == original

        config.plugins["i18n"].building = False
        hook.on_post_build(config)
        assert "refresh" in probe.read_text(encoding="utf-8")

        probe.write_text(original, encoding="utf-8")
        hook.on_startup("gh-deploy", False)
        hook.on_post_build(config)
        assert "refresh" in probe.read_text(encoding="utf-8")

    def test_the_hook_is_registered(self):
        hooks = re.search(r"^hooks:\n((?:[ \t]+-[^\n]*\n)+)", (MKDOCS_SRC / "mkdocs.yml").read_text(encoding="utf-8"), flags=re.MULTILINE)

        assert hooks is not None and f"- {HOOK_ENTRY}" in hooks.group(1)


@needs_built_site
class TestBuiltSite:
    """The same, on pages of the real site, copied into ``tmp_path``."""

    def test_a_copy_of_the_real_site(self, hook, tmp_path):
        site = tmp_path / "site"
        for folder in ("developer/architecture/overview", "it/developer/architecture/overview", "fr/developer/architecture/overview", "es/developer/architecture/overview", "it/user/getting-started"):
            if (SITE / folder).is_dir():
                shutil.copytree(SITE / folder, site / folder)
        shutil.copy(SITE / "sitemap.xml", site / "sitemap.xml")

        counts = hook.apply(site, MKDOCS_SRC / "docs", "https://librefolio.github.io/LibreFolio/")

        assert counts["stubs"] == 3
        stub = (site / "it" / "developer" / "architecture" / "overview" / "index.html").read_text(encoding="utf-8")
        assert "url=../../../../developer/architecture/overview/" in stub and len(stub) < 900
        english = (site / "developer" / "architecture" / "overview" / "index.html").read_text(encoding="utf-8")
        assert not re.search(r'<link[^>]*hreflang="(?:it|fr|es)"', english)  # the three alternates named copies that no longer exist
        sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")  # only the three copies of the sample were replaced
        assert all(f"/{language}/developer/architecture/overview/" not in sitemap for language in ("it", "fr", "es"))
        italian_page = (site / "it" / "user" / "getting-started" / "index.html").read_text(encoding="utf-8")
        assert "/it/developer/" not in italian_page and "../../../developer/" in italian_page
