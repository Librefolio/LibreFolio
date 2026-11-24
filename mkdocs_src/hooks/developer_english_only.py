"""
MkDocs hook: the developer manual exists once, in English (lane 84-E).

The manual for developers (``docs/developer/``) is English only, by design. ``mkdocs-static-i18n`` still copies each of its
142 pages into ``it/``, ``fr/`` and ``es/`` as the fallback of a missing translation: 113 MB of HTML that say the same
thing, three more canonical addresses for the same text, and a menu in every language that points at them. After the
build, for each non-default language, this hook:

1. **replaces each fallback copy with a redirect page** of about half a kilobyte (``<meta http-equiv="refresh">``, a
   ``location.replace`` that keeps the ``#anchor``, a ``noindex`` and the English page as ``canonical``): an old address, a
   bookmark or an external link to ``/it/developer/...`` still works, and ends on the English page. A page is a fallback copy
   when no ``<name>.<lang>.md`` translates it: the day someone translates one, it stays a real page;
2. **points every link of the other pages at the English page directly**: the menu and the text of the Italian, French and
   Spanish pages link ``/developer/...`` instead of ``/<lang>/developer/...``, so nobody goes through the redirect;
3. **removes the copies from ``sitemap.xml`` (and its ``.gz``)** and the ``hreflang`` alternates that named them, in the
   sitemap and in the head of the English pages: a search engine is not told that three translations exist.

The language selector (``javascripts/site-lang-selector.js``) already shows a page of ``/developer/`` as English, read only,
and leaves the visitor's language untouched, so it keeps working: from an English-only page there is nothing to switch to,
and the next page of the visitor's language opens in that language.

It runs for ``mkdocs build`` and ``gh-deploy``, once, on the final site, before the minifier (``minify_html.py``).
"""

from __future__ import annotations

import gzip
import html
import json
import logging
import posixpath
import re
from pathlib import Path
from urllib.parse import urlsplit

from mkdocs.plugins import event_priority

log = logging.getLogger("mkdocs.hooks.developer_english_only")

#: The non-default languages of the site and the section that is English only.
LANGUAGES = ("it", "fr", "es")
SECTION = "developer"

_command = "build"

_TITLE = re.compile(r"<title>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_HREF = re.compile(r'(\bhref=")([^"]*)(")')
_LINK_TAG = re.compile(r"<link\b[^>]*>[ \t]*\n?", re.IGNORECASE)
_ATTRIBUTE = {name: re.compile(rf'\b{name}="([^"]*)"', re.IGNORECASE) for name in ("rel", "hreflang", "href")}
_SITEMAP_URL = re.compile(r"[ \t]*<url>.*?</url>[ \t]*\n?", re.DOTALL)
_SITEMAP_ALTERNATE = re.compile(r'[ \t]*<xhtml:link\b[^>]*\bhreflang="(?P<lang>[^"]*)"[^>]*\bhref="(?P<href>[^"]*)"[^>]*/>[ \t]*\n?')


def translated_urls(docs_dir: Path, language: str) -> set[str]:
    """The URL paths (``developer/api/``) of the developer pages that DO have a ``<name>.<language>.md`` source."""
    urls: set[str] = set()
    for source in (docs_dir / SECTION).rglob(f"*.{language}.md"):
        relative = source.relative_to(docs_dir).as_posix()[: -len(f".{language}.md")]
        urls.add(relative[: -len("index")] if relative.endswith("/index") or relative == "index" else relative + "/")
    return urls


def page_url(site_dir: Path, page: Path) -> str:
    """The directory URL of a built page, relative to the site root: ``it/developer/api/`` for ``it/developer/api/index.html``."""
    folder = page.parent.relative_to(site_dir).as_posix()
    return "" if folder == "." else folder + "/"


def fallback_copies(site_dir: Path, docs_dir: Path, language: str) -> list[Path]:
    """The built pages of ``<language>/developer/`` that no translation backs: the ones to replace."""
    translated = translated_urls(docs_dir, language)
    base = site_dir / language / SECTION
    if not base.is_dir():
        return []
    prefix = f"{language}/"
    return [page for page in sorted(base.rglob("index.html")) if page_url(site_dir, page)[len(prefix) :] not in translated]


def english_url(language: str, url: str) -> str:
    """``it/developer/api/`` → ``developer/api/``."""
    return url[len(language) + 1 :]


def redirect_page(language: str, title: str, target: str, canonical: str) -> str:
    """The page that stands in for a fallback copy. ``target`` is relative to the page, ``canonical`` absolute (or empty)."""
    shown = html.escape(title or "LibreFolio")
    link = html.escape(target, quote=True)
    canonical_tag = f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">\n' if canonical else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{shown}</title>\n"
        '<meta name="robots" content="noindex">\n'
        f"{canonical_tag}"
        f'<meta http-equiv="refresh" content="0; url={link}">\n'
        f"<script>location.replace({json.dumps(target)} + location.search + location.hash)</script>\n"
        "</head>\n<body>\n"
        f'<p>The developer manual is English only: <a href="{link}">open this page in English</a>.</p>\n'
        "</body>\n</html>\n"
    )


def retarget_links(page_html: str, page_dir_url: str, language: str, replaced: set[str]) -> str:
    """The same page with every ``href`` that leads to a replaced copy leading to the English page instead.

    ``page_dir_url`` is the page's own directory URL (``it/user/x/``): the relative links are read from there.
    """

    def retarget(match: re.Match) -> str:
        href = match.group(2)
        if not href or href.startswith(("#", "/", "http:", "https:", "mailto:", "tel:", "data:", "javascript:")):
            return match.group(0)
        parts = urlsplit(href)
        resolved = posixpath.normpath(posixpath.join(page_dir_url, parts.path)) if parts.path else page_dir_url.rstrip("/")
        if resolved.endswith("/index.html"):
            resolved = resolved[: -len("index.html")].rstrip("/")
        if resolved + "/" not in replaced:
            return match.group(0)
        target = english_url(language, resolved + "/")
        relative = posixpath.relpath(target.rstrip("/") or ".", page_dir_url.rstrip("/") or ".") + "/"
        suffix = (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")
        return f"{match.group(1)}{relative}{suffix}{match.group(3)}"

    return _HREF.sub(retarget, page_html)


def drop_alternates(page_html: str, replaced_by_language: dict[str, set[str]], site_path: str) -> str:
    """Remove from the head the ``rel="alternate" hreflang`` links that name a replaced copy."""

    def drop(match: re.Match) -> str:
        tag = match.group(0)
        values = {name: (pattern.search(tag).group(1) if pattern.search(tag) else "") for name, pattern in _ATTRIBUTE.items()}
        if values["rel"].lower() != "alternate" or not values["hreflang"]:
            return tag
        return "" if _names_copy(values["href"], values["hreflang"], replaced_by_language, site_path) else tag

    return _LINK_TAG.sub(drop, page_html)


def _names_copy(href: str, language: str, urls_by_language: dict[str, set[str]], site_path: str) -> bool:
    """Whether ``href`` (absolute or root-relative) is the address of a replaced copy of ``language``."""
    path = urlsplit(href).path
    for candidate in (path, path[len(site_path) :] if site_path and path.startswith(site_path) else path):
        candidate = candidate.lstrip("/")
        if candidate in urls_by_language.get(language, ()):
            return True
    return False


def fix_sitemap(text: str, urls_by_language: dict[str, set[str]], site_path: str) -> str:
    """The sitemap without the replaced copies, and without the alternates that named them."""

    def fix_url(match: re.Match) -> str:
        block = match.group(0)
        loc = re.search(r"<loc>(.*?)</loc>", block)
        if loc and any(_names_copy(loc.group(1), language, urls_by_language, site_path) for language in urls_by_language):
            return ""
        return _SITEMAP_ALTERNATE.sub(lambda alt: "" if _names_copy(alt.group("href"), alt.group("lang"), urls_by_language, site_path) else alt.group(0), block)

    return _SITEMAP_URL.sub(fix_url, text)


def _relink_pages(site_dir: Path, replaced_by_language: dict[str, set[str]]) -> int:
    """Point the links of every page of a non-default language (the copies themselves excepted) at the English pages."""
    count = 0
    for language, replaced in replaced_by_language.items():
        base = site_dir / language
        for page in sorted(base.rglob("*.html")) if base.is_dir() else []:
            folder = page.parent.relative_to(site_dir).as_posix() + "/"
            if page.name == "index.html" and folder in replaced:
                continue
            original = page.read_text(encoding="utf-8")
            updated = retarget_links(original, folder, language, replaced)
            if updated != original:
                page.write_text(updated, encoding="utf-8")
                count += 1
    return count


def _write_redirects(site_dir: Path, replaced_by_language: dict[str, set[str]], site_url: str) -> int:
    """Overwrite each fallback copy with its redirect page."""
    count = 0
    for language, replaced in replaced_by_language.items():
        for url in sorted(replaced):
            page = site_dir / url / "index.html"
            title = _TITLE.search(page.read_text(encoding="utf-8"))
            target_url = english_url(language, url)
            relative = posixpath.relpath(target_url.rstrip("/") or ".", url.rstrip("/")) + "/"
            canonical = f"{site_url.rstrip('/')}/{target_url}" if site_url else ""
            page.write_text(redirect_page(language, html.unescape(title.group(1).strip()) if title else "", relative, canonical), encoding="utf-8")
            count += 1
    return count


def _clean_metadata(site_dir: Path, replaced_by_language: dict[str, set[str]], site_path: str) -> None:
    """The head of the English pages and the sitemap stop naming the copies."""
    for page in sorted((site_dir / SECTION).rglob("index.html")):
        original = page.read_text(encoding="utf-8")
        updated = drop_alternates(original, replaced_by_language, site_path)
        if updated != original:
            page.write_text(updated, encoding="utf-8")
    sitemap = site_dir / "sitemap.xml"
    if sitemap.is_file():
        sitemap.write_text(fix_sitemap(sitemap.read_text(encoding="utf-8"), replaced_by_language, site_path), encoding="utf-8")
        if (site_dir / "sitemap.xml.gz").is_file():
            (site_dir / "sitemap.xml.gz").write_bytes(gzip.compress(sitemap.read_bytes(), mtime=0))


def apply(site_dir: Path, docs_dir: Path, site_url: str = "") -> dict[str, int]:
    """Do the three things of the module's docstring on the built site. Returns the counts, for the log."""
    replaced_by_language = {language: {page_url(site_dir, page) for page in fallback_copies(site_dir, docs_dir, language)} for language in LANGUAGES}
    if not any(replaced_by_language.values()):
        return {"stubs": 0, "pages": 0}
    # The links first: the copies are skipped, then overwritten.
    pages = _relink_pages(site_dir, replaced_by_language)
    stubs = _write_redirects(site_dir, replaced_by_language, site_url)
    _clean_metadata(site_dir, replaced_by_language, urlsplit(site_url).path.rstrip("/"))
    return {"stubs": stubs, "pages": pages}


def _inside_language_build(config) -> bool:
    try:
        plugin = config.plugins.get("i18n")
    except (AttributeError, TypeError):
        return False
    return bool(getattr(plugin, "building", False))


def on_startup(command, dirty) -> None:
    global _command
    _command = command


@event_priority(-150)  # after the search split (-100), before the minifier (-200)
def on_post_build(config) -> None:
    if _command == "serve" or _inside_language_build(config):
        return
    counts = apply(Path(config["site_dir"]), Path(config["docs_dir"]), config.get("site_url") or "")
    if counts["stubs"]:
        log.info("Developer manual kept in English only: %d copies replaced by redirects, %d pages relinked", counts["stubs"], counts["pages"])
