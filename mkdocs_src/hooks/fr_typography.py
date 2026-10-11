"""
MkDocs hook: French typography on the French pages, applied to the rendered HTML only.

French keeps a sign or a unit together with the word before it: a non-breaking space stands before the colon, the
semicolon, the question and exclamation marks and the percent sign, inside « », and between the groups of a number.
The translations, and every run of the pipeline that writes them, use plain spaces, so a line could break before a
colon or inside « 28 398 € ». This hook turns those plain spaces into non-breaking ones in the pages whose source is
French (``*.fr.md``), at build time: the sources never change.

It only replaces whitespace that is already there; it never inserts a space. It reads text only: tags and their
attributes (URLs, alt and title texts) pass through byte for byte, and so do comments and the content of ``code``,
``pre``, ``kbd``, ``samp``, ``var``, ``svg``, ``math``, of the raw-text elements (``script``, ``style``,
``textarea``…) and of any element of class ``arithmatex`` (formulas). The theme renders two more French texts outside
the page content, and they get the same treatment: the titles of the page's table of contents (``page.toc``), and the
French navigation labels (``nav_translations``), which also title the pages in the tabs, the header and the browser
tab.
"""

from __future__ import annotations

import re

try:
    from mkdocs.plugins import event_priority
except ImportError:  # the functions below stay importable without MkDocs
    event_priority = lambda priority: lambda f: f  # noqa: E731

NBSP = "\u00a0"  # before the colon, inside « »
NNBSP = "\u202f"  # before ; ? ! %, a currency symbol after a number, between thousand groups

_SPACE = r"[ \t\r\n]+"
# A sign that closes a phrase is followed by a space, the end of the text, closing punctuation, or an entity.
_AFTER_SIGN = r"(?=[\s)\]}»”\"'.,;:?!…&]|$)"

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(_SPACE + r"(?=:" + _AFTER_SIGN + ")"), NBSP),
    (re.compile(_SPACE + r"(?=[;?!]" + _AFTER_SIGN + ")"), NNBSP),
    (re.compile(_SPACE + r"(?=%)"), NNBSP),  # also «<strong>50</strong> %»: the number may end the previous run
    (re.compile(r"(?<=\d)" + _SPACE + r"(?=[€$£¥])"), NNBSP),
    (re.compile(r"(?<=«)" + _SPACE), NBSP),
    (re.compile(_SPACE + r"(?=»)"), NBSP),
]
_THOUSANDS = re.compile(r"(?<![\w.,#&])\d{1,3}(?: \d{3})+(?![\w]|[.,]\d{3})")

# Tags with quoted attribute values (a value may hold a ">"), comments, doctype and processing instructions.
_TOKEN = re.compile(
    "|".join(
        (
            r"<!--.*?-->",
            r"<!\[CDATA\[.*?\]\]>",
            r"<![A-Za-z][^>]*>",
            r"<\?.*?\?>",
            r"</?[A-Za-z][\w:.-]*(?:\s+(?:[^\s\"'>/=]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'=<>`]+))?|/))*\s*/?>",
        )
    ),
    re.S,
)
_TAG_NAME = re.compile(r"</?([A-Za-z][\w:.-]*)")
_CLASS = re.compile(r"""\sclass\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""", re.I)

_SKIPPED = frozenset({"code", "pre", "kbd", "samp", "var", "svg", "math"})
# Their content is not HTML: skipped up to the end tag.
_RAW_TEXT = frozenset({"script", "style", "textarea", "iframe", "noembed", "noframes", "xmp"})


def typeset(text: str) -> str:
    """French spacing in a run of text (no tags): plain whitespace before the signs becomes non-breaking."""
    for pattern, space in _RULES:
        text = pattern.sub(space, text)
    return _THOUSANDS.sub(lambda m: m.group(0).replace(" ", NNBSP), text)


def _is_formula(tag: str) -> bool:
    m = _CLASS.search(tag)
    return bool(m) and "arithmatex" in (m.group(1) or m.group(2) or m.group(3) or "").split()


def typeset_html(html: str) -> str:
    """Apply ``typeset`` to the text of an HTML fragment, leaving tags, attributes and skipped elements untouched."""
    out: list[str] = []
    pos = 0
    skip_name: str | None = None
    skip_depth = 0
    while (m := _TOKEN.search(html, pos)) is not None:  # from pos: a raw-text element's content is never tokenized
        text = html[pos : m.start()]
        out.append(text if skip_name else typeset(text))
        token = m.group(0)
        pos = m.end()
        out.append(token)
        name_m = _TAG_NAME.match(token)
        if not name_m:
            continue  # comment, doctype, CDATA, processing instruction
        name = name_m.group(1).lower()
        closing = token.startswith("</")
        self_closing = token.endswith("/>")
        if skip_name:
            if name == skip_name and not self_closing:
                skip_depth += -1 if closing else 1
                if skip_depth == 0:
                    skip_name = None
            continue
        if closing or self_closing:
            continue
        if name in _RAW_TEXT:
            end = re.compile(rf"</{name}\s*>", re.I).search(html, pos)
            stop = end.end() if end else len(html)
            out.append(html[pos:stop])
            pos = stop
        elif name in _SKIPPED or _is_formula(token):
            skip_name, skip_depth = name, 1
    tail = html[pos:]
    out.append(tail if skip_name else typeset(tail))
    return "".join(out)


def _typeset_toc(items) -> None:
    for item in items:
        item.title = typeset(item.title)
        _typeset_toc(item.children)


def on_page_content(html: str, page, config, files) -> str:
    if getattr(page.file, "locale", None) != "fr":
        return html
    _typeset_toc(getattr(page, "toc", None) or [])
    return typeset_html(html)


def _typeset_nav(items, french: set[str]) -> None:
    for item in items:
        if getattr(item, "title", None) in french:
            item.title = typeset(item.title)
        _typeset_nav(getattr(item, "children", None) or [], french)


@event_priority(-110)  # after mkdocs-static-i18n (-100) has put the French labels in
def on_nav(nav, config, files):
    i18n = config.plugins.get("i18n")
    if getattr(i18n, "current_language", None) != "fr":
        return nav
    french = set((i18n.current_language_config.nav_translations or {}).values())
    _typeset_nav(nav.items, french)
    return nav
