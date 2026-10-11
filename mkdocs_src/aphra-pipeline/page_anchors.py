"""The anchors a MkDocs page offers: the ids its own render produces, as ``mkdocs build`` records them.

``mkdocs build --strict`` checks a link's fragment against the target page's ``Page.present_anchor_ids``
(MkDocs 1.6): every ``id`` (and ``<a name>``) of the rendered element tree, plus those of the page's raw
HTML. Hand-made heading slugs drifted from that set — a heading with an explicit ``{: #id }`` only has
its id, duplicates are numbered after explicit ids too, emoji shortcodes and inline code render — so
this module renders the page instead, through MkDocs' own ``Page.render``, with the site's Markdown
extensions read from ``mkdocs_src/mkdocs.yml``.

Used by ``translate-validate`` (anchor-missing) and ``dev.py mkdocs check-links``. Needs MkDocs and the
site's extensions installed (the docs toolchain); callers import it only when they run.
"""

from __future__ import annotations

import functools
import logging
from contextlib import contextmanager
from pathlib import Path

MKDOCS_YML = Path(__file__).resolve().parents[1] / "mkdocs.yml"


@contextmanager
def _quiet_mkdocs():
    """Silence MkDocs while a page renders alone: with no other page to resolve them against, every
    relative link would be logged as unresolved — link checking is the callers' job, not the render's."""
    logger = logging.getLogger("mkdocs")
    previous = logger.level
    logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        logger.setLevel(previous)


@functools.lru_cache(maxsize=1)
def _site():
    """The site's configuration, as ``mkdocs build`` loads it, and an empty file set: loaded once."""
    from mkdocs.config import load_config  # noqa: PLC0415 — MkDocs only when a page renders
    from mkdocs.structure.files import Files  # noqa: PLC0415 — MkDocs only when a page renders

    with _quiet_mkdocs():
        config = load_config(config_file=str(MKDOCS_YML))
    return config, Files([])


def render_anchors(source: str) -> frozenset[str]:
    """The anchor ids MkDocs records for a page whose file holds ``source``.

    As MkDocs reads a page (utf-8-sig, ``Page.read_source``), a leading byte-order mark is dropped and YAML front
    matter is split off before rendering; plugins' page events are not run (the i18n plugin's only translates
    untitled admonition headings, which carry no id).
    """
    from mkdocs.structure.files import File  # noqa: PLC0415 — MkDocs only when a page renders
    from mkdocs.structure.pages import Page  # noqa: PLC0415 — MkDocs only when a page renders
    from mkdocs.utils import meta  # noqa: PLC0415 — MkDocs only when a page renders

    config, files = _site()
    page = Page(None, File("page.md", config["docs_dir"], config["site_dir"], config["use_directory_urls"]), config)
    page.markdown, page.meta = meta.get_data(source.removeprefix("\ufeff"))
    with _quiet_mkdocs():
        page.render(config, files)
    return frozenset(page.present_anchor_ids or ())


@functools.cache
def _file_anchors(path: str, mtime_ns: int, size: int) -> frozenset[str]:
    # utf-8-sig, as MkDocs reads a page (File.content_string): a byte-order mark is not content.
    return render_anchors(Path(path).read_text(encoding="utf-8-sig"))


def file_anchors(path: Path | str) -> frozenset[str]:
    """``render_anchors`` of a page on disk; each version of a file is rendered once per process."""
    resolved = Path(path).resolve()
    stat = resolved.stat()
    return _file_anchors(str(resolved), stat.st_mtime_ns, stat.st_size)
