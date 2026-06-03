"""
MkDocs hook: rewrite relative hreflang alternate URLs to absolute.

The mkdocs-material i18n plugin generates relative hrefs in <link rel="alternate">
tags (e.g. href="/LibreFolio/es/"). Google requires absolute URLs for hreflang
to work correctly. This hook rewrites them using site_url at build time.
"""

import re
from urllib.parse import urljoin


_ALTERNATE_LINK = re.compile(
    r'<link\b([^>]*\brel="alternate"[^>]*\bhreflang="[^"]*"[^>]*)/?>', 
    re.IGNORECASE,
)
_HREF_ATTR = re.compile(r'\bhref="([^"]*)"')


def _fix_hreflang(html: str, config) -> str:
    site_url = config.get("site_url", "")
    if not site_url:
        return html

    def fix_link(m: re.Match) -> str:
        attrs = m.group(1)
        href_m = _HREF_ATTR.search(attrs)
        if not href_m:
            return m.group(0)
        href = href_m.group(1)
        if href.startswith("http://") or href.startswith("https://"):
            return m.group(0)
        abs_href = urljoin(site_url, href)
        new_attrs = attrs.replace(f'href="{href}"', f'href="{abs_href}"')
        return f"<link{new_attrs}>"

    return _ALTERNATE_LINK.sub(fix_link, html)


def on_page_content(html: str, page, config, files) -> str:
    return _fix_hreflang(html, config)


def on_post_page(output: str, page, config) -> str:
    return _fix_hreflang(output, config)
