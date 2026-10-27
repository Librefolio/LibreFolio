"""
MkDocs hook: split the search index by language (lot DOC-2).

MkDocs builds ONE index, ``search/search_index.json``, for every language of the site: a visitor reading Italian downloads
the English, French and Spanish pages too (10 MB), and finds the four versions of a page together. After the build this
hook writes one file per language next to it, ``search/search_index.<lang>.json``, with only the pages written in that
language. ``javascripts/search-language.js`` makes the page ask Material for its own language's file, and a checkbox in the
search dialog asks for the full index instead («search the other languages too»).

A page belongs to the language its address starts with: ``it/``, ``fr/``, ``es/``; every other address is English (the
default language has no prefix). A page that exists only in English has no copy in the other languages' index, so a
reader of Italian finds it only with the checkbox on. The full ``search_index.json`` is left as it is.
"""

import json
import logging
from pathlib import Path

from mkdocs.plugins import event_priority

log = logging.getLogger("mkdocs.hooks.search_language_split")

#: The languages of the site, the default one first: the files written are ``search_index.<lang>.json``.
LANGUAGES = ("en", "it", "fr", "es")
DEFAULT_LANGUAGE = "en"

INDEX_NAME = "search_index.json"


def language_of(location: str, languages: tuple[str, ...] = LANGUAGES) -> str:
    """The language a search entry is written in: its address's first segment when that is a language of the site (``it/``,
    ``it/x/``, ``it/#a`` or ``it``), English otherwise (``developer/api/``, ``#a``, an empty address, ``item/``)."""
    first = location.split("#", 1)[0].split("/", 1)[0]
    return first if first in languages and first != DEFAULT_LANGUAGE else DEFAULT_LANGUAGE


def split_index(index: dict, languages: tuple[str, ...] = LANGUAGES) -> dict[str, dict]:
    """One index per language from the full one: the same ``config``, only the ``docs`` written in that language. Every
    entry of the full index is in exactly one of them."""
    docs: dict[str, list] = {language: [] for language in languages}
    for doc in index.get("docs", []):
        docs[language_of(doc.get("location", ""), languages)].append(doc)
    return {language: {**index, "docs": entries} for language, entries in docs.items()}


def _inside_language_build(config) -> bool:
    """Whether this is one of the builds ``mkdocs-static-i18n`` runs for the non-default languages, from inside its own
    ``on_post_build``: their index is merged into the main one afterwards, and the main one is what is split."""
    try:
        plugin = config.plugins.get("i18n")
    except (AttributeError, TypeError):
        return False
    return bool(getattr(plugin, "building", False))


@event_priority(-100)  # after the search plugin, and the i18n plugin's merge of every language's entries
def on_post_build(config) -> None:
    if _inside_language_build(config):
        return
    folder = Path(config["site_dir"]) / "search"
    full = folder / INDEX_NAME
    if not full.is_file():
        log.warning("No %s in %s: the search index is not split by language", INDEX_NAME, folder)
        return
    try:
        index = json.loads(full.read_text(encoding="utf-8"))
        parts = split_index(index)
    except (OSError, ValueError, AttributeError) as exc:
        log.warning("The search index could not be split by language: %s", exc)
        return
    for language, part in parts.items():
        (folder / f"search_index.{language}.json").write_text(json.dumps(part, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("Search index split by language: %s", ", ".join(f"{language} {len(part['docs'])}" for language, part in parts.items()))
