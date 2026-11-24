"""
MkDocs hook: rewrite relative hreflang alternate URLs to absolute.

The i18n plugin gives Material the other languages' addresses and MkDocs' ``url`` filter makes each of them relative to
the PAGE that holds it (``../it/user/`` on ``user/``); the home pages' links start with ``/`` (``/LibreFolio/it/``).
Google requires absolute URLs for hreflang to work correctly. This hook rewrites them at build time: a relative one is
resolved from the address of its page (``site_url`` + ``page.url``), so the site's path (``/LibreFolio/``) is kept. Resolved
from ``site_url`` alone, ``../it/user/`` led to ``https://host/it/user/``, outside the site (lane 84, DW-2).
"""

import re
from urllib.parse import urljoin

_ALTERNATE_LINK = re.compile(
    r'<link\b([^>]*\brel="alternate"[^>]*\bhreflang="[^"]*"[^>]*)/?>',
    re.IGNORECASE,
)
_HREF_ATTR = re.compile(r'\bhref="([^"]*)"')


def _fix_hreflang(html: str, page, config) -> str:
    site_url = config.get("site_url", "")
    if not site_url:
        return html
    page_address = urljoin(site_url, getattr(page, "url", "") or "")

    def fix_link(m: re.Match) -> str:
        attrs = m.group(1)
        href_m = _HREF_ATTR.search(attrs)
        if not href_m:
            return m.group(0)
        href = href_m.group(1)
        if href.startswith("http://") or href.startswith("https://"):
            return m.group(0)
        abs_href = urljoin(page_address, href)
        new_attrs = attrs.replace(f'href="{href}"', f'href="{abs_href}"')
        return f"<link{new_attrs}>"

    return _ALTERNATE_LINK.sub(fix_link, html)


def on_page_content(html: str, page, config, files) -> str:
    return _fix_hreflang(html, page, config)


def on_post_page(output: str, page, config) -> str:
    return _fix_hreflang(output, page, config)
