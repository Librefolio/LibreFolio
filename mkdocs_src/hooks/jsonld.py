"""
MkDocs hook: inject JSON-LD structured data for Google rich results.

Injects three schema types:
- WebSite + SearchAction  (homepage only) → Google Sitelinks Searchbox
- SoftwareApplication     (homepage only) → rich card with category/price
- BreadcrumbList          (all inner pages) → breadcrumb trail in SERP
"""

import json


_SITE_URL = "https://librefolio.github.io/LibreFolio/"
_REPO_URL = "https://github.com/Librefolio/LibreFolio"
_SEARCH_URL = f"{_SITE_URL}search/?q="


def _inject(html: str, data: dict) -> str:
    block = (
        '<script type="application/ld+json">\n'
        + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n</script>"
    )
    return html.replace("</head>", f"{block}\n</head>", 1)


def _website_schema() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "LibreFolio",
        "url": _SITE_URL,
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{_SEARCH_URL}{{search_term_string}}",
            },
            "query-input": "required name=search_term_string",
        },
    }


def _software_schema() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "LibreFolio",
        "url": _SITE_URL,
        "downloadUrl": f"{_REPO_URL}/releases",
        "codeRepository": _REPO_URL,
        "applicationCategory": "FinanceApplication",
        "operatingSystem": "Linux, macOS, Windows",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD",
        },
        "description": (
            "Free, self-hosted, open-source financial portfolio tracker. "
            "Tracks stocks, ETFs, crypto and bonds with multi-currency support, "
            "technical analysis (EMA, MACD, RSI, Bollinger) and broker import."
        ),
        "license": "https://opensource.org/licenses/AGPL-3.0",
    }


def _breadcrumb_schema(page) -> dict | None:
    """Build BreadcrumbList: Home → [sections with index] → current page."""
    crumbs = []

    # Walk parent chain bottom-up, collect sections that have an index page
    ancestors = []
    node = getattr(page, "parent", None)
    while node is not None:
        ancestors.append(node)
        node = getattr(node, "parent", None)
    ancestors.reverse()

    position = 1
    items = [
        {
            "@type": "ListItem",
            "position": position,
            "name": "Home",
            "item": _SITE_URL,
        }
    ]
    position += 1

    for section in ancestors:
        title = getattr(section, "title", None)
        if not title:
            continue
        # Sections may have an index child page
        index_child = None
        for child in getattr(section, "children", []):
            if getattr(child, "is_index", False):
                index_child = child
                break
        if index_child and getattr(index_child, "url", None):
            url = _SITE_URL.rstrip("/") + "/" + index_child.url.lstrip("/")
            items.append({"@type": "ListItem", "position": position, "name": title, "item": url})
            position += 1

    # Current page
    page_url = getattr(page, "url", None)
    page_title = getattr(page, "title", None)
    if page_url and page_title and not getattr(page, "is_homepage", False):
        url = _SITE_URL.rstrip("/") + "/" + page_url.lstrip("/")
        items.append({"@type": "ListItem", "position": position, "name": page_title, "item": url})

    if len(items) < 2:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }


def on_post_page(output: str, page, config) -> str:
    is_home = getattr(page, "is_homepage", False) or page.url in ("", "/", "./", "index.html")

    if is_home:
        output = _inject(output, _website_schema())
        output = _inject(output, _software_schema())
    else:
        bc = _breadcrumb_schema(page)
        if bc:
            output = _inject(output, bc)

    return output
