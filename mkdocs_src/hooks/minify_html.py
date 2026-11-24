"""
MkDocs hook: the pages of the built site lose the indentation Material's templates write (lane 84-C).

Material's Jinja templates leave a third of every HTML file as indentation and blank lines (387 MB of HTML in the four
languages, 242 MB without them). After the build this hook rewrites each ``*.html`` of the site so that every run
of whitespace that contains a newline, between the tags and inside the text, becomes a single newline. A browser renders
the same page: a run of whitespace is one space wherever the layout collapses it, and the newline is kept so that two
inline elements never touch.

What is never touched, because there whitespace is content:

* ``<pre>``, ``<code>`` and ``<kbd>`` (Material sets ``white-space: pre-wrap`` on all three), ``<textarea>``;
* ``<script>`` and ``<style>`` (JSON configuration, inline code);
* the inside of a tag, attribute values included (``alt``, ``title``, ``data-*``, an SVG ``d``).

No dependency: the rule is a small tokeniser on the stdlib, which a test checks against the DOM of every page of a build
(same tree, same text outside the protected elements). It is idempotent. It runs for ``mkdocs build`` and ``gh-deploy``
(the published site and the Docker image both come from a build), not for ``mkdocs serve``, where it would only slow the
reload down. The i18n plugin runs a nested build per language: the hook acts once, on the final site.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from mkdocs.plugins import event_priority

log = logging.getLogger("mkdocs.hooks.minify_html")

#: Elements whose whitespace is content (and ``script``/``style``, whose text is not markup at all).
PROTECTED_ELEMENTS = ("pre", "code", "kbd", "textarea", "script", "style")

# A tag: ``>`` inside a quoted attribute value does not end it.
_TAG = r"""<(?:[^>"']|"[^"]*"|'[^']*')*>"""
_PROTECTED = re.compile(r"<(" + "|".join(PROTECTED_ELEMENTS) + r")\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>.*?</\1\s*>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(_TAG)
_TOKEN = re.compile(r"(" + _TAG + r")|([^<]+)|(<)")
_NEWLINE_RUN = re.compile(r"\s*\n\s*")

#: The command MkDocs runs (``build``, ``gh-deploy``, ``serve``), set by ``on_startup``.
_command = "build"


def _minify_unprotected(chunk: str) -> str:
    """The text between the protected elements: tags stay as they are, a whitespace run with a newline becomes one."""

    def token(match: re.Match) -> str:
        if match.group(2) is not None:
            return _NEWLINE_RUN.sub("\n", match.group(2))
        return match.group(0)

    return _TOKEN.sub(token, chunk)


def minify(page: str) -> str:
    """The page with its indentation and blank lines removed; see the module's docstring for what is kept."""
    out: list[str] = []
    last = 0
    for match in _PROTECTED.finditer(page):
        out.append(_minify_unprotected(page[last : match.start()]))
        out.append(match.group(0))
        last = match.end()
    out.append(_minify_unprotected(page[last:]))
    return "".join(out)


def minify_site(site_dir: Path) -> tuple[int, int, int]:
    """Minify every ``*.html`` under ``site_dir`` in place. Returns ``(files, bytes before, bytes after)``."""
    files = before = after = 0
    for path in sorted(site_dir.rglob("*.html")):
        original = path.read_bytes()
        try:
            text = original.decode("utf-8")
        except UnicodeDecodeError:
            log.warning("%s is not UTF-8: left as it is", path)
            continue
        minified = minify(text).encode("utf-8")
        files += 1
        before += len(original)
        if len(minified) < len(original):
            path.write_bytes(minified)
            after += len(minified)
        else:
            after += len(original)
    return files, before, after


def _inside_language_build(config) -> bool:
    """Whether this is one of the builds ``mkdocs-static-i18n`` runs for the non-default languages, from inside its own
    ``on_post_build``: the site is whole only when the outer build ends."""
    try:
        plugin = config.plugins.get("i18n")
    except (AttributeError, TypeError):
        return False
    return bool(getattr(plugin, "building", False))


def on_startup(command, dirty) -> None:
    global _command
    _command = command


@event_priority(-200)  # after every other hook and plugin of the build, the search split included
def on_post_build(config) -> None:
    if _command == "serve" or _inside_language_build(config):
        return
    files, before, after = minify_site(Path(config["site_dir"]))
    if files:
        log.info("HTML minified: %d files, %.1f MB -> %.1f MB (-%.0f%%)", files, before / 1048576, after / 1048576, 100 * (1 - after / before) if before else 0)
