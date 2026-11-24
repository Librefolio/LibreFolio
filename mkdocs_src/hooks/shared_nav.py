"""
MkDocs hook: the menu is written once per language, not in every page (lane 84-D).

Material writes the whole navigation tree into each page: 217 KB of a 258 KB page, 83% of the 387 MB of HTML, the same 393
links 1566 times. After the build this hook keeps in each page only what Material itself draws when a page is **pruned**
(``navigation.prune``): the top-level tabs and the groups of the branch the page is in, every other group as one link to its
first page. The full tree of each language goes to one file, ``javascripts/nav/nav.<language>.<hash>.js``, which a small
script reads while the page is parsed, before Material's bundle starts: it puts back, in place of each link left by the
pruning, the group it stands for. The DOM that Material finds is the one it always found. The file is named after the hash of its content, so the backend
sends it cached for a year (``backend/app/services/platform/static_site.py``) and a visitor downloads it once per release.

Why this shape and not a menu drawn from scratch by a script: Material writes the state of the page into the menu (which
group is open, which item is current, the table of contents of the page inside it). Here Material still writes it, in the
markup that stays; the shared file holds only groups that are **not** active, whose markup does not depend on the page. Without
JavaScript the page keeps a menu of real links (the tabs, the section of the page, a link to the first page of every other
group), which is what a crawler or a text browser reads.

The rule for what stays is Material's (``partials/nav-item.html``): a group that is neither active nor a section is replaced
by ``<li class="md-nav__item md-nav__item--pruned md-nav__item--nested"><a href="first page" class="md-nav__link">label</a></li>``.
The replacement keys are the depth of the group and its first page, relative to the site's root, so a link means the same in
every page.

It runs for ``mkdocs build`` and ``gh-deploy``, once, after the other hooks (``developer_english_only.py`` first) and before the
minifier.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import posixpath
import re
from pathlib import Path
from urllib.parse import urlsplit

from lxml import html as lxml_html
from mkdocs.plugins import event_priority

log = logging.getLogger("mkdocs.hooks.shared_nav")

#: The languages whose pages share their menu: the default one has no folder, the others have their own.
LANGUAGES = ("en", "it", "fr", "es")
DEFAULT_LANGUAGE = "en"
OTHER_LANGUAGES = tuple(language for language in LANGUAGES if language != DEFAULT_LANGUAGE)

NAV_FOLDER = "javascripts/nav"
ENHANCER = "javascripts/nav-enhance.js"

_NAV_OPEN = re.compile(r'<nav class="md-nav md-nav--primary[^"]*"[^>]*>')
_NAV_TAG = re.compile(r"<nav\b|</nav\s*>")
_NEWLINE_RUN = re.compile(r"\s*\n\s*")

_command = "build"


# ---------------------------------------------------------------------------
# The menu inside a page
# ---------------------------------------------------------------------------


def find_nav(page: str) -> tuple[int, int] | None:
    """The span of the page's primary ``<nav>`` element, its nested ``<nav>`` included, or ``None`` when there is none."""
    opening = _NAV_OPEN.search(page)
    if opening is None:
        return None
    depth = 0
    for tag in _NAV_TAG.finditer(page, opening.start()):
        depth += 1 if tag.group(0).startswith("<nav") else -1
        if depth == 0:
            return opening.start(), tag.end()
    return None


def _classes(element) -> list[str]:
    return (element.get("class") or "").split()


def _nested_items(container) -> list:
    """The groups directly inside ``container`` (a ``<ul>`` of the menu), in order."""
    return [item for item in container.xpath("./li") if "md-nav__item--nested" in _classes(item)]


def depth_of(item) -> int:
    """How many groups hold this group, itself included: 1 for a tab."""
    return 1 + sum(1 for ancestor in item.iterancestors("li") if "md-nav__item--nested" in _classes(ancestor))


def first_page(item) -> str:
    """The ``href`` of the first page of a group, in document order (the groups themselves hold labels, not links)."""
    links = item.xpath(".//a[@href]")
    return links[0].get("href") if links else ""


def is_pruned_by_material(item) -> bool:
    """Whether Material prunes this group: neither active (a page of its own is open) nor a section (always shown)."""
    classes = _classes(item)
    return "md-nav__item--active" not in classes and "md-nav__item--section" not in classes


def prune_item(item) -> bool:
    """Replace what is inside a group by Material's pruned form: one link to its first page, with the group's label.
    Returns whether the group was replaced."""
    label = item.xpath("./label[contains(concat(' ', normalize-space(@class), ' '), ' md-nav__link ')]")
    target = first_page(item)
    if not label or not target:
        return False  # a shape this hook does not know: leave the group whole
    classes = _classes(item)
    link = lxml_html.Element("a", href=target, **{"class": "md-nav__link"})
    link.text = label[0].text
    for child in label[0]:
        link.append(copy.deepcopy(child))
    for child in list(item):
        item.remove(child)
    item.text = "\n"
    item.append(link)
    link.tail = "\n"
    item.set("class", " ".join(c for c in classes if c != "md-nav__item--nested") + " md-nav__item--pruned md-nav__item--nested")
    return True


def group_key(item, page_dir_url: str) -> tuple[int, str]:
    """What the script finds a group by: its depth and the path of its first page from the site's root."""
    return depth_of(item), to_root_relative(first_page(item), page_dir_url)


def prune_menu(nav, page_dir_url: str, known: set[tuple[int, str]]) -> int:
    """Prune every group of the menu that Material prunes, outermost first, and that the shared menu holds (``known``: the
    keys of its groups): a group the script could not put back stays whole. Returns how many groups were replaced."""
    count = 0
    pending = list(_nested_items(nav.xpath("./ul")[0])) if nav.xpath("./ul") else []
    while pending:
        item = pending.pop()
        if is_pruned_by_material(item) and group_key(item, page_dir_url) in known:
            count += prune_item(item)
        else:
            for inner in item.xpath("./nav/ul"):
                pending.extend(_nested_items(inner))
    return count


def root_prefix(page_dir_url: str) -> str:
    """The path from a page to the site's root: ``../../`` for ``user/x/``."""
    parts = [p for p in page_dir_url.split("/") if p]
    return "../" * len(parts)


def to_root_relative(href: str, page_dir_url: str) -> str:
    """A link of a page as a path from the site's root, which does not depend on the page that holds it."""
    if not href or href.startswith(("#", "/", "http:", "https:", "mailto:", "tel:", "data:", "javascript:")):
        return href
    parts = urlsplit(href)
    resolved = posixpath.normpath(posixpath.join(page_dir_url, parts.path)) if parts.path else page_dir_url.rstrip("/")
    resolved = "" if resolved == "." else resolved
    if parts.path.endswith("/") and resolved and not resolved.endswith("/"):
        resolved += "/"
    return resolved + (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")


def build_master(home_page: str, home_dir_url: str) -> str | None:
    """The menu of a language, whole, from its home page: every group, in its state when no page of it is open, with every
    link as a path from the site's root. ``None`` when the page has no menu."""
    span = find_nav(home_page)
    if span is None:
        return None
    nav = lxml_html.fragment_fromstring(home_page[span[0] : span[1]])
    lists = nav.xpath("./ul")
    if not lists:
        return None
    lists[0].tail = None
    for leaf in [li for li in lists[0].xpath("./li") if "md-nav__item--nested" not in _classes(li)]:
        lists[0].remove(leaf)  # the pages at the top level hold no group: nothing of them is ever put back
    for link in lists[0].xpath(".//a[@href]"):
        link.set("href", to_root_relative(link.get("href"), home_dir_url))
    markup = lxml_html.tostring(lists[0], encoding="unicode", method="html")
    return _NEWLINE_RUN.sub("\n", markup)


def master_keys(master: str) -> set[tuple[int, str]]:
    """The keys of the groups in a language's shared menu (its links are already paths from the site's root)."""
    fragment = lxml_html.fragment_fromstring(master)
    return {(depth_of(item), first_page(item)) for item in fragment.iter("li") if "md-nav__item--nested" in _classes(item)}


def shrink_page(page: str, page_dir_url: str, language: str, script_url: str, known: set[tuple[int, str]]) -> tuple[str, int]:
    """The page with its menu pruned, the marks the script reads and the script itself. Returns the page and the number of
    groups pruned; a page with no menu is returned as it is."""
    span = find_nav(page)
    if span is None:
        return page, 0
    nav = lxml_html.fragment_fromstring(page[span[0] : span[1]])
    count = prune_menu(nav, page_dir_url, known)
    if not count:
        return page, 0
    nav.set("data-lf-nav", language)
    nav.set("data-lf-root", root_prefix(page_dir_url))
    markup = lxml_html.tostring(nav, encoding="unicode", method="html")
    return page[: span[0]] + markup + f'<script src="{root_prefix(page_dir_url)}{script_url}"></script>' + page[span[1] :], count


# ---------------------------------------------------------------------------
# The site
# ---------------------------------------------------------------------------


def pages_of(site_dir: Path, language: str) -> list[Path]:
    """The built HTML of a language: its folder, or for the default language everything outside the other languages' folders."""
    if language != DEFAULT_LANGUAGE:
        return sorted((site_dir / language).rglob("*.html")) if (site_dir / language).is_dir() else []
    return sorted(p for p in site_dir.rglob("*.html") if p.relative_to(site_dir).parts[0] not in OTHER_LANGUAGES and p.name != "404.html")


def home_of(site_dir: Path, language: str) -> Path:
    return site_dir / "index.html" if language == DEFAULT_LANGUAGE else site_dir / language / "index.html"


def script_for(language: str, master: str, enhancer: str) -> tuple[str, str]:
    """``(file name, content)`` of the script of a language: the menu and the enhancer, named after the hash of the whole file.

    The backend caches the file for a year under its name (``static_site.is_content_hashed_doc_file``): the hash covers the
    code as well as the menu, so a change of either is another name and no browser keeps a stale copy."""
    # The menu first, then the code that reads it: the code runs as soon as the file is parsed.
    content = f"(window.LF_NAV = window.LF_NAV || {{}})[{json.dumps(language)}] = {json.dumps(master, ensure_ascii=False)};\n{enhancer.rstrip()}\n"
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
    return f"{NAV_FOLDER}/nav.{language}.{digest}.js", content


def apply(site_dir: Path, enhancer: str, languages: tuple[str, ...] = LANGUAGES) -> dict[str, int]:
    """Prune the menu of every page of the given languages and write each language's script. Returns the counts for the log."""
    totals = {"pages": 0, "groups": 0, "scripts": 0}
    for language in languages:
        home = home_of(site_dir, language)
        if not home.is_file():
            continue
        master = build_master(home.read_text(encoding="utf-8"), home.parent.relative_to(site_dir).as_posix() + "/" if home.parent != site_dir else "")
        if master is None:
            log.warning("No menu in %s: the pages of %s keep theirs", home, language)
            continue
        name, content = script_for(language, master, enhancer)
        known = master_keys(master)
        (site_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (site_dir / name).write_text(content, encoding="utf-8")
        totals["scripts"] += 1
        for page in pages_of(site_dir, language):
            relative = page.parent.relative_to(site_dir).as_posix()
            page_dir_url = "" if relative == "." else relative + "/"
            original = page.read_text(encoding="utf-8")
            updated, groups = shrink_page(original, page_dir_url, language, name, known)
            if groups:
                page.write_text(updated, encoding="utf-8")
                totals["pages"] += 1
                totals["groups"] += groups
    return totals


def _inside_language_build(config) -> bool:
    try:
        plugin = config.plugins.get("i18n")
    except (AttributeError, TypeError):
        return False
    return bool(getattr(plugin, "building", False))


def on_startup(command, dirty) -> None:
    global _command
    _command = command


@event_priority(-170)  # after developer_english_only (-150): its links already lead to the English pages; before the minifier (-200)
def on_post_build(config) -> None:
    if _command == "serve" or _inside_language_build(config):
        return
    site_dir = Path(config["site_dir"])
    enhancer = (Path(config["docs_dir"]) / ENHANCER).read_text(encoding="utf-8")
    counts = apply(site_dir, enhancer)
    if counts["pages"]:
        log.info("Menu shared: %d pages pruned (%d groups), %d script(s)", counts["pages"], counts["groups"], counts["scripts"])
