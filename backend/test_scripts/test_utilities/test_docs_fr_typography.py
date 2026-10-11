"""fr_typography: French typography on the French pages, set by an MkDocs hook at build time (R2 B15, M).

``mkdocs_src/hooks/fr_typography.py`` turns the plain whitespace the French pages already have before a sign into the
non-breaking space French typography asks for, in the rendered HTML only, so a line never breaks before a colon or
inside « 28 398 € ». The sources never change. Pinned here:

* ``typeset(text)``, on a run of text: plain whitespace (``[ \\t\\r\\n]+``, of any length) before ``:`` becomes U+00A0;
  before ``;`` ``?`` ``!``, before ``%`` (whatever precedes the whitespace, so ``<strong>50</strong> %`` too) and before
  ``€ $ £ ¥`` after a digit of the same run, U+202F; after ``«`` and before ``»``, U+00A0; between thousand groups (1 to
  3 digits, then groups of exactly 3), U+202F. A ``:`` ``;`` ``?`` or ``!`` counts only when followed by whitespace, the
  end of the text, closing punctuation or ``&`` (an entity). Nothing is inserted (``Next: Select``, ``16:9``,
  ``«sans»``), ``&nbsp;`` is left alone, a year is not joined to the number after it, and a decimal tail and a second
  grouping style are left alone;
* ``typeset_html(html)`` applies it to the text between tags only. Tags with their attributes (a quoted value holding a
  ``>`` included), comments and the doctype pass through byte for byte; the content of ``code``, ``pre``, ``kbd``,
  ``samp``, ``var``, ``svg``, ``math`` and of any element of class ``arithmatex`` is skipped, nested elements of the
  same name counted; the raw-text elements (``script``, ``style``, ``textarea``, ``iframe``, ``noembed``, ``noframes``,
  ``xmp``) are skipped up to their end tag, their content not being HTML: a ``<p>`` or a ``<!--`` in it opens nothing;
  a self-closing tag opens nothing. On fragments shaped like the site's render it is idempotent, changes whitespace
  only, and leaves the markup, as ``html.parser`` reads it, identical;
* ``on_page_content`` acts only on a page whose ``file.locale`` is ``fr``: its HTML, and the titles of ``page.toc``
  with their children. mkdocs-static-i18n sets ``file.locale`` to the language of the source file, so the English
  fallback of the French build is ``en``, and so is a page without suffix: pinned on files made by the plugin's own
  ``suffix.create_i18n_file``;
* ``on_nav``, in the French build only, typesets the navigation labels that are French (the values of the French
  ``nav_translations``) at any depth, which also title the pages in the tabs, the header and the browser tab. A title
  that is not one (the Developer Manual, shown in English) and an identity label (``Yahoo Finance``) stay as they are,
  an item without a title is skipped, any other build and a site without the i18n plugin are left alone. Its priority
  is below the plugin's ``on_nav`` (−100), which puts the labels in: dispatched through the site's real configuration,
  the plugin's labels come out typeset;
* the registration: ``mkdocs_src/mkdocs.yml`` lists the hook under ``hooks:``, and MkDocs, loading it, registers both
  events of this file;
* a French page rendered with the site's Markdown configuration (MkDocs' ``Page.render``, not a build) comes out with
  its prose typeset, and its code, formulas, diagram, icon and attributes as the render made them.

Red phase. The hook is new, with no HEAD version: the file ran against copies of it under /tmp, each in a tree holding a
copy of this file (so that ``PROJECT_ROOT`` is the tree) and the site's own configuration, docs and other hooks.

* The hook as first written was red on the raw-text cases holding ``<!--`` (3 of the 181 tests then): its token search
  (``finditer``) went on inside a ``script``, ``style`` or ``textarea`` already copied, found there a comment running to
  the next ``-->`` of the page, skipped it as inside the element and resumed after its end, so the tags in between had
  their attributes typeset and their text was not. The hook now restarts the search where the element ends
  (``_TOKEN.search(html, pos)``); its first loop is mutant m36 below.
* Two decisions of the same batch, each red against the rule it replaced: ``%`` after any whitespace (the former
  ``(?<=\\S)``, mutant m34, is red on ``<strong>50</strong> %`` and on a run starting with `` %``), and ``iframe``,
  ``noembed``, ``noframes`` and ``xmp`` read as raw text (left out, mutant m35, red on their content).
* 36 one-defect mutants of the hook, each red on the tests of its defect: U+00A0 for ``; ? !``, U+202F after ``«``; a
  sign followed by a letter, or not by ``&``; one whitespace character, no newline; ``%`` only after a digit or only
  after a non-space, a currency after any non-space; a year joined, a second grouping style joined; attributes typeset,
  a quoted ``>`` ending the tag, comments read as text, tag names or the class attribute read case-sensitively, the
  token search resumed inside raw text; ``code`` or ``arithmatex`` not skipped, nesting not counted, a self-closing tag
  opening a region or counting as nesting; raw text not skipped, skipped to the end of the document, read as HTML with
  nesting counted, or without ``iframe``, ``noembed``, ``noframes`` and ``xmp``; ``on_page_content`` for every locale,
  without the TOC or its children, or returning the HTML as it came; ``on_nav`` for every build, for every title,
  without children, or at a priority of 0 or −100 (the plugin's own); the hook left out of ``mkdocs.yml``.

PURE: strings in memory. Loads the hook by path and reads ``mkdocs_src/mkdocs.yml`` (the hook's registration, and the
site configuration a page is rendered and a navigation dispatched with: no plugin event runs but ``on_nav``, on a
navigation built here). No build, no DB, no server, no network, no writes.
"""

from __future__ import annotations

import importlib.util
import logging
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import yaml
from mkdocs.config import load_config
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import PluginCollection
from mkdocs.structure.files import File, Files
from mkdocs.structure.nav import Link, Navigation, Section
from mkdocs.structure.pages import Page
from mkdocs.structure.toc import AnchorLink, TableOfContents
from mkdocs_static_i18n import suffix as i18n_suffix
from mkdocs_static_i18n.plugin import I18n

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MKDOCS_YML = PROJECT_ROOT / "mkdocs_src" / "mkdocs.yml"
HOOK_ENTRY = "hooks/fr_typography.py"  # as mkdocs.yml lists it: relative to the configuration file
HOOK = PROJECT_ROOT / "mkdocs_src" / HOOK_ENTRY

NBSP = "\u00a0"  # before the colon, inside « »
NNBSP = "\u202f"  # before ; ? ! %, a currency symbol after a number, between thousand groups

LANGUAGES = ["en", "it", "fr", "es"]  # the i18n plugin's languages in mkdocs.yml, en the default


# ---------------------------------------------------------------------------
# The hook, loaded by path as MkDocs loads it. Reached through a fixture only, so a function the hook lacks fails the
# tests that call it, never the collection.
# ---------------------------------------------------------------------------


def _load_hook(name: str) -> ModuleType:
    """The hook file as a module of its own, by path (what ``config_options.Hooks._load_hook`` does)."""
    spec = importlib.util.spec_from_file_location(name, HOOK)
    assert spec is not None and spec.loader is not None, f"cannot load {HOOK} as a module"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    module = _load_hook("fr_typography_under_test")
    assert callable(getattr(module, "typeset", None)), f"not the typography hook: {HOOK}"
    return module


@contextmanager
def _quiet_mkdocs() -> Iterator[None]:
    """MkDocs logs what a lone page or a hand-built navigation lacks (links to resolve, a homepage): not under test."""
    logger = logging.getLogger("mkdocs")
    previous = logger.level
    logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        logger.setLevel(previous)


@pytest.fixture(scope="module")
def site_config() -> MkDocsConfig:
    """The site's configuration as ``mkdocs build`` loads it, plugins and hooks included. Loaded once; the tests run
    no event of it but ``on_nav``, on navigations they build, and restore what they change in it."""
    with _quiet_mkdocs():
        return load_config(config_file=str(MKDOCS_YML))


def _titles(items) -> list[str | None]:
    """Every title of a table of contents or a navigation, depth first."""
    titles: list[str | None] = []
    for item in items:
        titles.append(item.title)
        titles.extend(_titles(getattr(item, "children", None) or []))
    return titles


# ---------------------------------------------------------------------------
# typeset: the rules, each with the exact code point
# ---------------------------------------------------------------------------


class TestTypesetRules:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("Remarque : texte", f"Remarque{NBSP}: texte", id="a-space"),
            pytest.param("Remarque   : texte", f"Remarque{NBSP}: texte", id="several-spaces"),
            pytest.param("Remarque\n: texte", f"Remarque{NBSP}: texte", id="a-newline"),
            pytest.param("Remarque \t\r\n : texte", f"Remarque{NBSP}: texte", id="mixed-whitespace"),
            pytest.param("Texte :", f"Texte{NBSP}:", id="at-the-end-of-the-text"),
            pytest.param(" : le texte", f"{NBSP}: le texte", id="at-the-start-of-the-text"),
        ],
    )
    def test_whitespace_before_a_colon_becomes_a_no_break_space(self, hook, text, expected):
        assert hook.typeset(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("Prix ; quantité", f"Prix{NNBSP}; quantité", id="semicolon"),
            pytest.param("Vraiment ?", f"Vraiment{NNBSP}?", id="question-mark"),
            pytest.param("Attention !", f"Attention{NNBSP}!", id="exclamation-mark"),
            pytest.param("Vraiment ?!", f"Vraiment{NNBSP}?!", id="question-then-exclamation-mark"),
            pytest.param("Quoi ? ! ;", f"Quoi{NNBSP}?{NNBSP}!{NNBSP};", id="one-after-the-other"),
            pytest.param("Vraiment  \n ?", f"Vraiment{NNBSP}?", id="spaces-and-a-newline"),
            pytest.param(" ? suite", f"{NNBSP}? suite", id="at-the-start-of-the-text"),
        ],
    )
    def test_whitespace_before_a_semicolon_question_or_exclamation_mark_becomes_a_narrow_no_break_space(self, hook, text, expected):
        assert hook.typeset(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("50 %", f"50{NNBSP}%", id="after-a-number"),
            pytest.param("un taux de 12,5 % par an", f"un taux de 12,5{NNBSP}% par an", id="after-a-decimal"),
            pytest.param("cent %", f"cent{NNBSP}%", id="after-a-word"),
            pytest.param("50\n  %", f"50{NNBSP}%", id="a-newline-and-spaces"),
            pytest.param(" % des parts", f"{NNBSP}% des parts", id="at-the-start-of-the-text"),
        ],
    )
    def test_whitespace_before_a_percent_sign_becomes_a_narrow_no_break_space(self, hook, text, expected):
        """Whatever stands before the whitespace: a text run may start there, the number ending the run before it."""
        assert hook.typeset(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("10 €", f"10{NNBSP}€", id="euro"),
            pytest.param("10 $", f"10{NNBSP}$", id="dollar"),
            pytest.param("10 £", f"10{NNBSP}£", id="pound"),
            pytest.param("10 ¥", f"10{NNBSP}¥", id="yen"),
            pytest.param("1 234,56  $", f"1{NNBSP}234,56{NNBSP}$", id="after-a-decimal-several-spaces"),
        ],
    )
    def test_whitespace_before_a_currency_symbol_after_a_digit_becomes_a_narrow_no_break_space(self, hook, text, expected):
        assert hook.typeset(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("« Bonjour »", f"«{NBSP}Bonjour{NBSP}»", id="a-space"),
            pytest.param("«   Bonjour   »", f"«{NBSP}Bonjour{NBSP}»", id="several-spaces"),
            pytest.param("«\nBonjour\n»", f"«{NBSP}Bonjour{NBSP}»", id="a-newline"),
        ],
    )
    def test_whitespace_inside_guillemets_becomes_a_no_break_space(self, hook, text, expected):
        assert hook.typeset(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("28 398", f"28{NNBSP}398", id="two-groups"),
            pytest.param("1 000 000", f"1{NNBSP}000{NNBSP}000", id="three-groups"),
            pytest.param("999 999 lignes", f"999{NNBSP}999 lignes", id="three-digit-head"),
            pytest.param("de 10 000 à 20 000", f"de 10{NNBSP}000 à 20{NNBSP}000", id="two-numbers"),
            pytest.param("vaut 28 398 €", f"vaut 28{NNBSP}398{NNBSP}€", id="before-a-currency"),
            pytest.param("(-1 000)", f"(-1{NNBSP}000)", id="signed-in-brackets"),
        ],
    )
    def test_the_space_between_thousand_groups_becomes_a_narrow_no_break_space(self, hook, text, expected):
        assert hook.typeset(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("(vraiment ?)", f"(vraiment{NNBSP}?)", id="closing-bracket"),
            pytest.param("[sic !]", f"[sic{NNBSP}!]", id="closing-square-bracket"),
            pytest.param("« Quoi ?»", f"«{NBSP}Quoi{NNBSP}?»", id="closing-guillemet"),
            pytest.param("“Vraiment ?”", f"“Vraiment{NNBSP}?”", id="closing-curly-quote"),
            pytest.param('"Non !"', f'"Non{NNBSP}!"', id="straight-double-quote"),
            pytest.param("'Oui ?'", f"'Oui{NNBSP}?'", id="straight-single-quote"),
            pytest.param("Quoi ?, dit-il", f"Quoi{NNBSP}?, dit-il", id="comma"),
            pytest.param("Ah !…", f"Ah{NNBSP}!…", id="ellipsis"),
            pytest.param("Quoi ?&nbsp;Oui", f"Quoi{NNBSP}?&nbsp;Oui", id="named-entity"),
            pytest.param("Prix :&#160;10", f"Prix{NBSP}:&#160;10", id="numeric-entity"),
        ],
    )
    def test_a_sign_followed_by_closing_punctuation_or_an_entity_counts(self, hook, text, expected):
        assert hook.typeset(text) == expected


# ---------------------------------------------------------------------------
# typeset: what it leaves alone
# ---------------------------------------------------------------------------


class TestTypesetLeavesAlone:
    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("Next: Select", id="english-colon"),
            pytest.param("16:9", id="ratio"),
            pytest.param("https://example.org/a:b", id="url"),
            pytest.param("«sans»", id="guillemets"),
            pytest.param("Quoi? Attention! a;b", id="question-exclamation-semicolon"),
            pytest.param("50% et 10€", id="percent-and-currency"),
            pytest.param("28398 lignes", id="number"),
        ],
    )
    def test_no_space_is_inserted(self, hook, text):
        assert hook.typeset(text) == text

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("a :b", id="colon-before-a-letter"),
            pytest.param("ratio 16 :9", id="colon-before-a-digit"),
            pytest.param("le paramètre ?lang=fr", id="question-mark-before-a-letter"),
            pytest.param("color: red !important", id="exclamation-mark-before-a-letter"),
            pytest.param("x ;y", id="semicolon-before-a-letter"),
        ],
    )
    def test_a_sign_followed_by_anything_else_is_not_a_sign(self, hook, text):
        assert hook.typeset(text) == text

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("Remarque&nbsp;: texte", id="nbsp-entity-before-a-colon"),
            pytest.param("Quoi&#8239;? «&nbsp;x&nbsp;»", id="entities-before-and-inside"),
            pytest.param(f"Remarque{NBSP}: Quoi{NNBSP}? «{NBSP}x{NBSP}» 28{NNBSP}398", id="already-non-breaking"),
            pytest.param("Remarque\u2009: texte", id="a-thin-space-is-not-plain-whitespace"),
        ],
    )
    def test_entities_and_spaces_that_are_not_plain_whitespace_are_left_alone(self, hook, text):
        assert hook.typeset(text) == text

    def test_a_percent_sign_inside_a_url_is_left_alone(self, hook):
        text = "Voir https://example.org/r%C3%A9sum%C3%A9?q=50%25&x=1 pour 50 %"
        assert hook.typeset(text) == f"Voir https://example.org/r%C3%A9sum%C3%A9?q=50%25&x=1 pour 50{NNBSP}%"

    def test_a_currency_symbol_not_after_a_digit_is_left_alone(self, hook):
        assert hook.typeset("en € ou en $, 10 €") == f"en € ou en $, 10{NNBSP}€"

    def test_a_year_is_not_joined_to_the_number_after_it(self, hook):
        assert hook.typeset("en 2024 120 000 lignes") == f"en 2024 120{NNBSP}000 lignes"

    def test_a_decimal_tail_is_left_alone(self, hook):
        assert hook.typeset("1 000,50") == f"1{NNBSP}000,50"

    def test_a_second_grouping_style_is_left_alone(self, hook):
        assert hook.typeset("1 000.500") == "1 000.500"

    def test_english_text_in_code_is_left_alone(self, hook):
        html = '<p>Lancez <code>echo "Total : 50 %" ; ls ? 1 000 €</code> puis validez :</p>'
        assert hook.typeset_html(html) == f'<p>Lancez <code>echo "Total : 50 %" ; ls ? 1 000 €</code> puis validez{NBSP}:</p>'


# ---------------------------------------------------------------------------
# typeset_html: text between tags only
# ---------------------------------------------------------------------------

# Typeset when processed, so a test fails when the content of a skipped element is typeset.
INSIDE = "a : b ; c ? d ! 50 % 10 € « e » 1 000"


class TestTypesetHtml:
    @pytest.mark.parametrize(
        ("html", "expected"),
        [
            pytest.param(
                '<a href="https://example.org/aide?x=1&amp;y=2#a:b" title="Aide : page ?">l\'aide :</a>',
                f'<a href="https://example.org/aide?x=1&amp;y=2#a:b" title="Aide : page ?">l\'aide{NBSP}:</a>',
                id="link-href-and-title",
            ),
            pytest.param(
                '<img alt="Graphique : 28 398 € ; « x »" src="g.png" title="Titre : 50 %"> Légende : ici',
                f'<img alt="Graphique : 28 398 € ; « x »" src="g.png" title="Titre : 50 %"> Légende{NBSP}: ici',
                id="image-alt-and-title",
            ),
            pytest.param(
                "<span data-title='<img src=\"x\"> A : b'>Texte :</span>",
                f"<span data-title='<img src=\"x\"> A : b'>Texte{NBSP}:</span>",
                id="quoted-value-holding-a-tag",
            ),
            pytest.param(
                '<abbr title="Taux annuel : 3 %">TAEG</abbr> : 3 %',
                f'<abbr title="Taux annuel : 3 %">TAEG</abbr>{NBSP}: 3{NNBSP}%',
                id="abbr-title",
            ),
            pytest.param(
                '<a\n  href="#etape-1"\n  title="Étape 1 : « choisir » ?">Étape 1 : choisir</a>',
                f'<a\n  href="#etape-1"\n  title="Étape 1 : « choisir » ?">Étape 1{NBSP}: choisir</a>',
                id="attributes-on-several-lines",
            ),
            pytest.param(
                "<td align=right title=Total>1 000 €</td>",
                f"<td align=right title=Total>1{NNBSP}000{NNBSP}€</td>",
                id="unquoted-values",
            ),
        ],
    )
    def test_tags_and_their_attributes_pass_through_byte_for_byte(self, hook, html, expected):
        assert hook.typeset_html(html) == expected

    @pytest.mark.parametrize(
        ("start", "end"),
        [
            pytest.param("<code>", "</code>", id="code"),
            pytest.param("<pre>", "</pre>", id="pre"),
            pytest.param("<kbd>", "</kbd>", id="kbd"),
            pytest.param("<samp>", "</samp>", id="samp"),
            pytest.param("<var>", "</var>", id="var"),
            pytest.param('<svg viewBox="0 0 24 24">', "</svg>", id="svg"),
            pytest.param("<math>", "</math>", id="math"),
            pytest.param('<span class="arithmatex">', "</span>", id="arithmatex-span"),
            pytest.param('<div class="arithmatex">', "</div>", id="arithmatex-div"),
            pytest.param("<span class='md-math arithmatex'>", "</span>", id="arithmatex-among-other-classes"),
            pytest.param("<span class=arithmatex>", "</span>", id="arithmatex-unquoted"),
            pytest.param("<script>", "</script>", id="script"),
            pytest.param('<style media="screen">', "</style>", id="style"),
            pytest.param("<textarea>", "</textarea>", id="textarea"),
            pytest.param('<iframe src="https://example.org/">', "</iframe>", id="iframe"),
            pytest.param("<noembed>", "</noembed>", id="noembed"),
            pytest.param("<noframes>", "</noframes>", id="noframes"),
            pytest.param("<xmp>", "</xmp>", id="xmp"),
        ],
    )
    def test_the_content_of_a_skipped_element_is_left_alone(self, hook, start, end):
        html = f"<p>Avant : {start}{INSIDE}{end} après !</p>"
        assert hook.typeset_html(html) == f"<p>Avant{NBSP}: {start}{INSIDE}{end} après{NNBSP}!</p>"

    @pytest.mark.parametrize(
        ("html", "expected"),
        [
            pytest.param(
                '<pre><code>x : 1\n<span class="k">if</span> a ? b : c ;</code> y : 2</pre> Fin :',
                f'<pre><code>x : 1\n<span class="k">if</span> a ? b : c ;</code> y : 2</pre> Fin{NBSP}:',
                id="code-inside-pre",
            ),
            pytest.param(
                '<span class="arithmatex"><span class="MathJax">x : y</span> ; z ?</span> Texte :',
                f'<span class="arithmatex"><span class="MathJax">x : y</span> ; z ?</span> Texte{NBSP}:',
                id="span-inside-an-arithmatex-span",
            ),
            pytest.param(
                r'<div class="arithmatex"><div>\[a : b\]</div> c : d</div> Texte :',
                rf'<div class="arithmatex"><div>\[a : b\]</div> c : d</div> Texte{NBSP}:',
                id="div-inside-an-arithmatex-div",
            ),
            pytest.param(
                "<code><code>a : b</code> c : d</code> e : f",
                f"<code><code>a : b</code> c : d</code> e{NBSP}: f",
                id="code-inside-code",
            ),
            pytest.param(
                r'<span class="arithmatex">\(a\)<span/> : b</span> Texte :',
                rf'<span class="arithmatex">\(a\)<span/> : b</span> Texte{NBSP}:',
                id="a-self-closing-tag-of-the-same-name-is-not-nesting",
            ),
        ],
    )
    def test_nested_elements_of_the_same_name_are_counted(self, hook, html, expected):
        assert hook.typeset_html(html) == expected

    def test_code_inside_a_link_is_skipped_and_the_rest_of_the_link_text_typeset(self, hook):
        html = '<a href="#x" title="Voir : x">Voir <code>a : b</code> : ici !</a>'
        assert hook.typeset_html(html) == f'<a href="#x" title="Voir : x">Voir <code>a : b</code>{NBSP}: ici{NNBSP}!</a>'

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param('<script>if (a < b && c > d) { s = "</p><p>Texte : x ?"; }</script>', id="script"),
            pytest.param('<style>a > b { content: "</p> : ?"; } p:hover { c: d }</style>', id="style"),
            pytest.param("<textarea>a < b : c </p> ? <p>d ! </textarea>", id="textarea"),
            pytest.param('<script>s = "<script>";</script>', id="script-holding-a-script-start-tag"),
            pytest.param('<SCRIPT type="module">a : b</SCRIPT >', id="uppercase-end-tag-with-a-space"),
            pytest.param('<script>var open = "<!--";</script>', id="script-holding-a-comment-opener"),
            pytest.param('<style>p::before { content: "<!--"; }</style>', id="style-holding-a-comment-opener"),
            pytest.param("<textarea>a <!-- b</textarea>", id="textarea-holding-a-comment-opener"),
            pytest.param("<xmp><p>Exemple : <b>gras</b> <!-- pas un commentaire</p></xmp>", id="xmp-holding-a-paragraph-a-colon-and-a-comment-opener"),
            pytest.param('<iframe src="https://example.org/"><p>Repli : voir <!-- la page</p></iframe>', id="iframe-holding-a-paragraph-a-colon-and-a-comment-opener"),
        ],
    )
    def test_raw_text_is_skipped_up_to_its_end_tag_and_is_not_read_as_html(self, hook, raw):
        """What follows the element is read as usual, its comment included: nothing inside the element opened one."""
        html = f'{raw}<p title="Note : a">Après :</p><!-- fin : x -->'
        assert hook.typeset_html(html) == f'{raw}<p title="Note : a">Après{NBSP}:</p><!-- fin : x -->'

    @pytest.mark.parametrize(
        "markup",
        [
            pytest.param("<!-- Remarque : x ? -->", id="comment"),
            pytest.param("<!--\n  Section vidéo : supprimée ; « temporairement »\n-->", id="comment-on-several-lines"),
            pytest.param("<!-- <code> -->", id="comment-holding-a-tag"),
            pytest.param("<!DOCTYPE html>", id="doctype"),
            pytest.param("<![CDATA[ a : b ? ]]>", id="cdata"),
            pytest.param('<?xml version="1.0" ? ?>', id="processing-instruction"),
        ],
    )
    def test_comments_and_declarations_pass_through_and_open_nothing(self, hook, markup):
        assert hook.typeset_html(f"{markup}<p>Texte :</p>") == f"{markup}<p>Texte{NBSP}:</p>"

    @pytest.mark.parametrize(
        "tag",
        [
            pytest.param("<code/>", id="code"),
            pytest.param('<svg class="icon" viewBox="0 0 24 24"/>', id="svg"),
            pytest.param('<span class="arithmatex" />', id="arithmatex"),
            pytest.param("<br/>", id="br"),
            pytest.param('<img src="a.png" alt="A : b" />', id="img"),
        ],
    )
    def test_a_self_closing_tag_opens_nothing(self, hook, tag):
        assert hook.typeset_html(f"{tag} Texte : suite") == f"{tag} Texte{NBSP}: suite"

    def test_text_before_between_and_after_skipped_elements_is_typeset(self, hook):
        html = "Avant : <code>a : b</code> entre : <kbd>Ctrl</kbd> + <kbd>S</kbd> : après !"
        assert hook.typeset_html(html) == f"Avant{NBSP}: <code>a : b</code> entre{NBSP}: <kbd>Ctrl</kbd> + <kbd>S</kbd>{NBSP}: après{NNBSP}!"

    @pytest.mark.parametrize(
        ("html", "expected"),
        [
            pytest.param("<CODE>a : b</CODE> Texte :", f"<CODE>a : b</CODE> Texte{NBSP}:", id="code"),
            pytest.param("<Pre>a : b</PRE> Texte :", f"<Pre>a : b</PRE> Texte{NBSP}:", id="pre-in-mixed-case"),
            pytest.param(r'<SPAN CLASS="arithmatex">\(a : b\)</SPAN> Texte :', rf'<SPAN CLASS="arithmatex">\(a : b\)</SPAN> Texte{NBSP}:', id="arithmatex"),
            pytest.param("<TEXTAREA>a : b</TEXTAREA> Texte :", f"<TEXTAREA>a : b</TEXTAREA> Texte{NBSP}:", id="textarea"),
            pytest.param("<P>Texte : <B>gras</B> !</P>", f"<P>Texte{NBSP}: <B>gras</B>{NNBSP}!</P>", id="ordinary-tags"),
        ],
    )
    def test_tag_names_are_read_in_any_case(self, hook, html, expected):
        assert hook.typeset_html(html) == expected

    @pytest.mark.parametrize(
        ("html", "expected"),
        [
            pytest.param("<p><strong>Remarque</strong> : le texte</p>", f"<p><strong>Remarque</strong>{NBSP}: le texte</p>", id="after-an-inline-element"),
            pytest.param("<p>Texte :</p>", f"<p>Texte{NBSP}:</p>", id="before-an-end-tag"),
            pytest.param(
                '<h2 id="etape-1">Étape 1 :<a class="headerlink" href="#etape-1" title="Permanent link">&para;</a></h2>',
                f'<h2 id="etape-1">Étape 1{NBSP}:<a class="headerlink" href="#etape-1" title="Permanent link">&para;</a></h2>',
                id="before-the-headerlink",
            ),
            pytest.param("<p>Vraiment ?!<br>Oui</p>", f"<p>Vraiment{NNBSP}?!<br>Oui</p>", id="before-a-line-break"),
            pytest.param("<p><strong>50</strong> % des parts</p>", f"<p><strong>50</strong>{NNBSP}% des parts</p>", id="percent-after-an-inline-element"),
        ],
    )
    def test_a_sign_at_either_end_of_a_text_run_counts(self, hook, html, expected):
        assert hook.typeset_html(html) == expected

    def test_a_currency_symbol_needs_its_digit_in_the_same_text_run(self, hook):
        """Unlike ``%``: the digit before a currency symbol (what keeps ``en €`` alone) is looked for in its own run."""
        assert hook.typeset_html("<p><strong>28 398</strong> € au total</p>") == f"<p><strong>28{NNBSP}398</strong> € au total</p>"


# ---------------------------------------------------------------------------
# typeset_html: invariants, on fragments shaped like the site's render
# ---------------------------------------------------------------------------


class _Markup(HTMLParser):
    """The markup of a fragment, in order, as the standard library's HTML parser reads it: start tags as written
    (attributes included), end tags, comments, declarations and processing instructions. Text is left out."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.items: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs) -> None:
        self.items.append(("start", self.get_starttag_text() or ""))

    def handle_startendtag(self, tag, attrs) -> None:
        self.items.append(("start-end", self.get_starttag_text() or ""))

    def handle_endtag(self, tag) -> None:
        self.items.append(("end", tag))

    def handle_comment(self, data) -> None:
        self.items.append(("comment", data))

    def handle_decl(self, decl) -> None:
        self.items.append(("declaration", decl))

    def handle_pi(self, data) -> None:
        self.items.append(("processing-instruction", data))

    def unknown_decl(self, data) -> None:
        self.items.append(("declaration", data))


def _markup(fragment: str) -> list[tuple[str, str]]:
    parser = _Markup()
    parser.feed(fragment)
    parser.close()
    return parser.items


_ANY_SPACE = re.compile(r"[\s\u00a0\u202f]+")


def _assert_invariants(hook: ModuleType, fragment: str) -> None:
    once = hook.typeset_html(fragment)
    assert once != fragment, "nothing to typeset: the invariants would hold for a function that does nothing"
    assert hook.typeset_html(once) == once, "not idempotent"
    assert _ANY_SPACE.sub(" ", once) == _ANY_SPACE.sub(" ", fragment), "something other than whitespace changed"
    assert set(once) - set(fragment) <= {NBSP, NNBSP}, "a character other than U+00A0 and U+202F was written"
    assert _markup(once) == _markup(fragment), "the markup changed"


SAMPLES = [
    pytest.param(
        '<h1 id="guide-premiers-pas">Guide : premiers pas<a class="headerlink" href="#guide-premiers-pas" title="Permanent link">&para;</a></h1>',
        id="heading-with-headerlink",
    ),
    pytest.param("<p>Le portefeuille vaut 28 398 € ; il a gagné 12,5 % en 2024 120 000 fois ? Vraiment !</p>", id="every-sign"),
    pytest.param("<p>Cliquez sur « Enregistrer » puis tapez <code>ls -la : x ; y ?</code> dans le terminal :</p>", id="inline-code"),
    pytest.param(
        '<div class="highlight"><pre><span></span><code><a id="__codelineno-0-1" name="__codelineno-0-1" href="#__codelineno-0-1"></a>'
        '<span class="nb">print</span><span class="p">(</span><span class="s2">"Total : 50 %"</span><span class="p">)</span>'
        '  <span class="c1"># vraiment ?</span>\n</code></pre></div>\n<p>Résultat : 50 %</p>',
        id="highlighted-block",
    ),
    pytest.param('<pre class="mermaid"><code>sequenceDiagram\n    Alice-&gt;&gt;Bob : Bonjour !</code></pre>\n<p>Le diagramme : ci-dessus.</p>', id="mermaid"),
    pytest.param(
        '<p>Le ratio vaut <span class="arithmatex">\\(a : b\\)</span> sur 1 000 000 lignes ; voir :</p>\n<div class="arithmatex">\\[\nx : y ; z ? 1 000\n\\]</div>',
        id="formulas",
    ),
    pytest.param(
        '<div class="admonition note">\n<p class="admonition-title">Remarque : important</p>\n<p>Le taux est de 3,5 % ; voir '
        '<a href="https://example.org/aide?x=1" title="Aide : page">l\'aide</a> <span class="twemoji"><svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 24 24"><path d="M21 7 9 19l-5.5-5.5 1.41-1.41L9 16.17 19.59 5.59z"/></svg></span> !</p>\n</div>',
        id="admonition-link-icon",
    ),
    pytest.param(
        '<table>\n<thead>\n<tr>\n<th>Colonne : A</th>\n<th style="text-align: right;">Valeur ?</th>\n</tr>\n</thead>\n<tbody>\n<tr>\n<td>Prix</td>\n<td style="text-align: right;">1 234,56 $</td>\n</tr>\n</tbody>\n</table>',
        id="table",
    ),
    pytest.param('<p><img alt="Graphique : 28 398 €" src="https://example.org/g.png" title="Titre : image" /> Légende : le graphique</p>', id="image"),
    pytest.param('<details class="tip">\n<summary>Astuce : replier</summary>\n<p>Contenu replié !</p>\n</details>', id="details"),
    pytest.param(
        '<div class="tabbed-set tabbed-alternate" data-tabs="1:1"><input checked="checked" id="__tabbed_1_1" name="__tabbed_1" type="radio" />'
        '<div class="tabbed-labels"><label for="__tabbed_1_1">Onglet : un</label></div>\n<div class="tabbed-content">\n<div class="tabbed-block">\n'
        "<p>Premier onglet ?</p>\n</div>\n</div>\n</div>",
        id="tabbed",
    ),
    pytest.param(
        "<p data-title='<img src=\"x\"> A : b'>Texte brut : ici</p>\n<!-- commentaire : à garder -->\n<p><kbd>Ctrl</kbd> + <kbd>S</kbd> : enregistrer</p>",
        id="raw-html-attribute-comment-kbd",
    ),
    pytest.param(
        '<script>if (a < b && c > d) { s = "</p><p>Texte : x ?"; }</script>\n<style>p::before { content: "a : b ?"; } a > b { c: d }</style>\n<textarea>a < b : c </p> ?</textarea>\n<p>Après : la suite !</p>',
        id="raw-text",
    ),
    pytest.param("<p><strong>Remarque</strong> : le texte <em>important</em> ! <code>a : b</code> ; « <var>x</var> » vaut <samp>1 000 %</samp> ?</p>", id="inline-elements"),
    pytest.param("<P>Texte : <CODE>a : b</CODE> fin !</P>", id="uppercase"),
    pytest.param("<!DOCTYPE html>\n<p>Prix :&nbsp;10 € ; « déjà&nbsp;» ?</p>", id="doctype-and-entities"),
    pytest.param("<ul>\n<li>Étape 1 : ouvrir</li>\n<li>Étape 2 : valider ?</li>\n</ul>\n<p>Texte\n:\nsur trois lignes ; avec   des   espaces !</p>", id="list-and-wrapped-text"),
    pytest.param(
        '<p><iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/x" title="Vidéo : démo" allowfullscreen></iframe></p>\n<p>La vidéo ci-dessus : 3 minutes !</p>',
        id="iframe-embed",
    ),
]


class TestInvariants:
    @pytest.mark.parametrize("fragment", SAMPLES)
    def test_idempotent_whitespace_only_and_markup_unchanged(self, hook, fragment):
        _assert_invariants(hook, fragment)


# ---------------------------------------------------------------------------
# on_page_content: French pages only, with their table of contents
# ---------------------------------------------------------------------------

_I18N_CONFIG = SimpleNamespace(docs_dir="/docs", site_dir="/site", use_directory_urls=True)


def _i18n_file(src: str, build: str) -> File:
    """The file mkdocs-static-i18n hands MkDocs for ``src`` in the build of ``build`` (docs_structure: suffix)."""
    return i18n_suffix.create_i18n_file(File(src, "/docs", "/site", True), build, "en", LANGUAGES, _I18N_CONFIG)


class TestI18nLocale:
    """What the hook reads, as the plugin writes it: ``file.locale`` is the language of the source file."""

    @pytest.mark.parametrize(
        ("src", "build", "locale", "alternate_of"),
        [
            pytest.param("user/guide.fr.md", "fr", "fr", "fr", id="french-page-of-the-french-build"),
            pytest.param("user/guide.en.md", "fr", "en", "fr", id="english-fallback-of-the-french-build"),
            pytest.param("user/guide.md", "fr", "en", "fr", id="page-without-suffix-in-the-french-build"),
            pytest.param("user/guide.it.md", "it", "it", "it", id="italian"),
            pytest.param("user/guide.es.md", "es", "es", "es", id="spanish"),
        ],
    )
    def test_file_locale_is_the_language_of_the_source_file(self, src, build, locale, alternate_of):
        file = _i18n_file(src, build)
        assert (file.locale, file.locale_alternate_of) == (locale, alternate_of)


PAGE_HTML = '<h1 id="guide">Guide : premiers pas</h1>\n<p>Le portefeuille vaut 28 398 € ; <code>a : b</code> « vraiment » ?</p>'
PAGE_HTML_FR = f'<h1 id="guide">Guide{NBSP}: premiers pas</h1>\n<p>Le portefeuille vaut 28{NNBSP}398{NNBSP}€{NNBSP}; <code>a : b</code> «{NBSP}vraiment{NBSP}»{NNBSP}?</p>'
TOC_TITLES = ["Guide : premiers pas", "Étape 1 : choisir", "Détails : « tout » ?", "Prix &amp; frais : 28 398 €"]
TOC_TITLES_FR = [f"Guide{NBSP}: premiers pas", f"Étape 1{NBSP}: choisir", f"Détails{NBSP}: «{NBSP}tout{NBSP}»{NNBSP}?", f"Prix &amp; frais{NBSP}: 28{NNBSP}398{NNBSP}€"]


def _page(file: File) -> Page:
    """A rendered page of ``file`` as the hook receives it: its table of contents nests a child and a grandchild."""
    grandchild = AnchorLink(TOC_TITLES[2], "details", 3)
    child = AnchorLink(TOC_TITLES[1], "etape-1", 2)
    child.children.append(grandchild)
    top = AnchorLink(TOC_TITLES[0], "guide", 1)
    top.children.append(child)
    page = Page(None, file, {})
    page.toc = TableOfContents([top, AnchorLink(TOC_TITLES[3], "prix", 1)])
    return page


class TestOnPageContent:
    def test_a_french_page_gets_its_html_and_its_toc_typeset(self, hook):
        page = _page(_i18n_file("user/guide.fr.md", "fr"))
        assert hook.on_page_content(PAGE_HTML, page=page, config=SimpleNamespace(), files=Files([])) == PAGE_HTML_FR
        assert _titles(page.toc) == TOC_TITLES_FR

    @pytest.mark.parametrize(
        ("src", "build"),
        [
            pytest.param("user/guide.en.md", "fr", id="english-fallback-of-the-french-build"),
            pytest.param("user/guide.md", "fr", id="page-without-suffix-in-the-french-build"),
            pytest.param("user/guide.it.md", "it", id="italian"),
            pytest.param("user/guide.es.md", "es", id="spanish"),
            pytest.param("user/guide.en.md", "en", id="english"),
        ],
    )
    def test_any_other_page_is_left_alone(self, hook, src, build):
        page = _page(_i18n_file(src, build))
        assert hook.on_page_content(PAGE_HTML, page=page, config=SimpleNamespace(), files=Files([])) == PAGE_HTML
        assert _titles(page.toc) == TOC_TITLES

    def test_a_file_without_locale_is_left_alone(self, hook):
        page = _page(File("user/guide.md", "/docs", "/site", True))
        assert not hasattr(page.file, "locale")
        assert hook.on_page_content(PAGE_HTML, page=page, config=SimpleNamespace(), files=Files([])) == PAGE_HTML
        assert _titles(page.toc) == TOC_TITLES

    def test_a_french_page_with_an_empty_toc_gets_its_html_typeset(self, hook):
        page = _page(_i18n_file("user/guide.fr.md", "fr"))
        page.toc = TableOfContents([])
        assert hook.on_page_content(PAGE_HTML, page=page, config=SimpleNamespace(), files=Files([])) == PAGE_HTML_FR

    def test_mkdocs_dispatches_the_event_to_the_hook(self, hook):
        plugins = PluginCollection()
        plugins[HOOK_ENTRY] = hook  # what MkDocs does with each module of `hooks:`
        page = _page(_i18n_file("user/guide.fr.md", "fr"))
        assert plugins.on_page_content(PAGE_HTML, page=page, config=SimpleNamespace(), files=Files([])) == PAGE_HTML_FR
        assert _titles(page.toc) == TOC_TITLES_FR


# ---------------------------------------------------------------------------
# on_nav: the French labels of the French build
# ---------------------------------------------------------------------------

FRENCH_LABELS = {  # English label → French label, shaped like the French nav_translations of mkdocs.yml
    "🧩 Am I Diversified?": "🧩 Suis-je Diversifié ?",
    "📉 How Much Can It Hurt?": "📉 Jusqu'où Peut-on Perdre ?",
    "Settings": "Réglages : avancés",
    "Quotes": "« Citations »",
    "Prices": "Prix : 28 398 €",
    "Yahoo Finance": "Yahoo Finance",  # an identity label: a French label too, with nothing to typeset
}


def _section(title: str, *children: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(title=title, children=list(children))


def _leaf(title: str | None) -> SimpleNamespace:
    """A page or a link: a title, and no children attribute at all."""
    return SimpleNamespace(title=title)


def _stub_nav() -> tuple[SimpleNamespace, dict[str, SimpleNamespace]]:
    """A navigation as on_nav reads it (``items``, each with a ``title`` and, for a section, ``children``), as
    mkdocs-static-i18n leaves it in the French build; and its items by name. First an entry with no title yet (a page
    without a label, before it is read), then French labels three deep, an identity label, and the Developer Manual,
    shown in English: none of its titles is a French label, though typeset would change one."""
    item = {
        "untitled": _leaf(None),
        "hurt": _leaf("📉 Jusqu'où Peut-on Perdre ?"),
        "quotes": _leaf("« Citations »"),
        "prices": _leaf("Prix : 28 398 €"),
        "yahoo": _leaf("Yahoo Finance"),
        "benchmarks": _leaf("Benchmarks on 10 000 rows"),
    }
    item["settings"] = _section("Réglages : avancés", item["quotes"], item["prices"])
    item["diversified"] = _section("🧩 Suis-je Diversifié ?", item["hurt"], item["settings"])
    item["developer"] = _section("Developer Manual", item["benchmarks"])
    return SimpleNamespace(items=[item["untitled"], item["diversified"], item["yahoo"], item["developer"]]), item


STUB_TITLES = [None, "🧩 Suis-je Diversifié ?", "📉 Jusqu'où Peut-on Perdre ?", "Réglages : avancés", "« Citations »", "Prix : 28 398 €", "Yahoo Finance", "Developer Manual", "Benchmarks on 10 000 rows"]


def _nav_config(language: str | None, translations: dict[str, str] | None) -> SimpleNamespace:
    """What on_nav reads of MkDocs' configuration: the i18n plugin, the language it builds, that language's labels."""
    i18n = SimpleNamespace(current_language=language, current_language_config=SimpleNamespace(nav_translations=translations))
    return SimpleNamespace(plugins={"i18n": i18n})


def _french_build(hook: ModuleType, nav):
    return hook.on_nav(nav, config=_nav_config("fr", FRENCH_LABELS), files=Files([]))


class TestOnNav:
    def test_a_french_label_is_typeset_on_a_section_and_on_its_nested_items(self, hook):
        nav, item = _stub_nav()
        _french_build(hook, nav)
        assert item["diversified"].title == f"🧩 Suis-je Diversifié{NNBSP}?"
        assert item["hurt"].title == f"📉 Jusqu'où Peut-on Perdre{NNBSP}?"
        assert item["settings"].title == f"Réglages{NBSP}: avancés"
        assert item["quotes"].title == f"«{NBSP}Citations{NBSP}»"
        assert item["prices"].title == f"Prix{NBSP}: 28{NNBSP}398{NNBSP}€"

    def test_a_title_that_is_not_a_french_label_is_left_alone(self, hook):
        """The Developer Manual is shown in English in the French build: no title of it is among the French labels."""
        nav, item = _stub_nav()
        assert hook.typeset(item["benchmarks"].title) != item["benchmarks"].title, "typeset leaves it alone anyway: pick another title"
        _french_build(hook, nav)
        assert (item["developer"].title, item["benchmarks"].title) == ("Developer Manual", "Benchmarks on 10 000 rows")

    def test_an_identity_label_is_left_as_it_is(self, hook):
        nav, item = _stub_nav()
        _french_build(hook, nav)
        assert item["yahoo"].title == "Yahoo Finance"

    def test_an_item_without_a_title_is_skipped_and_the_walk_goes_on(self, hook):
        nav, item = _stub_nav()
        _french_build(hook, nav)
        assert item["untitled"].title is None
        assert item["diversified"].title == f"🧩 Suis-je Diversifié{NNBSP}?"

    def test_it_returns_the_navigation_it_was_given(self, hook):
        nav, _ = _stub_nav()
        assert _french_build(hook, nav) is nav

    @pytest.mark.parametrize("language", ["en", "it", "es", None])
    def test_any_other_build_is_left_alone(self, hook, language):
        nav, _ = _stub_nav()
        assert hook.on_nav(nav, config=_nav_config(language, FRENCH_LABELS), files=Files([])) is nav
        assert _titles(nav.items) == STUB_TITLES

    def test_without_the_i18n_plugin_the_navigation_is_left_alone(self, hook):
        nav, _ = _stub_nav()
        assert hook.on_nav(nav, config=SimpleNamespace(plugins={}), files=Files([])) is nav
        assert _titles(nav.items) == STUB_TITLES

    def test_a_french_build_without_nav_translations_is_left_alone(self, hook):
        nav, _ = _stub_nav()
        assert hook.on_nav(nav, config=_nav_config("fr", None), files=Files([])) is nav
        assert _titles(nav.items) == STUB_TITLES

    def test_mkdocs_navigation_classes_are_read_the_same_way(self, hook):
        """Section, Page and Link, as MkDocs builds the navigation (a page and a link have ``children = None``)."""
        page = Page("📉 Jusqu'où Peut-on Perdre ?", File("user/risk.md", "/docs", "/site", True), {})
        diversified = Section("🧩 Suis-je Diversifié ?", [page, Link("« Citations »", "https://example.org/quotes")])
        developer = Section("Developer Manual", [Link("Benchmarks on 10 000 rows", "https://example.org/benchmarks")])
        nav = Navigation([diversified, Link("Yahoo Finance", "https://example.org/yahoo"), developer], [page])
        assert _french_build(hook, nav) is nav
        assert _titles(nav.items) == [
            f"🧩 Suis-je Diversifié{NNBSP}?",
            f"📉 Jusqu'où Peut-on Perdre{NNBSP}?",
            f"«{NBSP}Citations{NBSP}»",
            "Yahoo Finance",
            "Developer Manual",
            "Benchmarks on 10 000 rows",
        ]

    def test_it_runs_after_the_i18n_plugin_has_put_the_french_labels_in(self, hook):
        """MkDocs runs the handlers of an event by decreasing priority (0 when undecorated): the hook's ``on_nav`` must
        come below mkdocs-static-i18n's (−100), the one that sets the labels."""
        assert getattr(hook.on_nav, "mkdocs_priority", 0) < getattr(I18n.on_nav, "mkdocs_priority", 0)


# ---------------------------------------------------------------------------
# The hook in the site's configuration
# ---------------------------------------------------------------------------


class _MkDocsYmlLoader(yaml.SafeLoader):
    """Reads mkdocs.yml without importing what its ``!!python/name:`` tags name."""


_MkDocsYmlLoader.add_multi_constructor("tag:yaml.org,2002:python/", lambda loader, suffix, node: None)

PROBE = "FR typography probe"  # an English navigation label the tests give a translation, in memory
PROBE_LABEL = "Sonde : « vraiment » ?"
# A French label of the site that ends with a spaced question mark and holds nothing else to typeset.
_SPACED_QUESTION = re.compile(r"[^\s\d:;?!%«»]+(?: [^\s\d:;?!%«»]+)* \?")


def _dispatch_nav(site_config: MkDocsConfig, labels: list[str]) -> Navigation:
    """A navigation of English labels (a section, then a page per label) through every ``on_nav`` of the site."""
    pages = [Page(label, File(f"user/nav-{i}.md", site_config["docs_dir"], site_config["site_dir"], True), site_config) for i, label in enumerate(labels[1:])]
    nav = Navigation([Section(labels[0], list(pages))], pages)
    with _quiet_mkdocs():
        return site_config.plugins.on_nav(nav, config=site_config, files=Files([]))


class TestHookInTheSiteConfiguration:
    def test_mkdocs_yml_lists_the_hook(self):
        config = yaml.load(MKDOCS_YML.read_text(encoding="utf-8"), Loader=_MkDocsYmlLoader)
        assert HOOK_ENTRY in config["hooks"], f"{HOOK_ENTRY} is not under hooks: in {MKDOCS_YML}"
        assert (MKDOCS_YML.parent / HOOK_ENTRY).resolve() == HOOK.resolve()

    def test_mkdocs_registers_both_events_of_the_hook(self, site_config):
        module = site_config.plugins[HOOK_ENTRY]
        assert Path(module.__file__).samefile(HOOK)
        assert module.on_page_content in site_config.plugins.events["page_content"]
        assert module.on_nav in site_config.plugins.events["nav"]

    def test_the_nav_event_runs_after_the_i18n_plugin_has_put_the_labels_in(self, site_config):
        nav_events = site_config.plugins.events["nav"]
        assert nav_events.index(site_config.plugins[HOOK_ENTRY].on_nav) > nav_events.index(site_config.plugins["i18n"].on_nav)

    def test_the_french_build_typesets_the_labels_the_plugin_puts_in(self, site_config, monkeypatch):
        i18n = site_config.plugins["i18n"]
        monkeypatch.setattr(i18n, "current_language", "fr")
        language = i18n.current_language_config
        monkeypatch.setitem(language, "nav_translations", {**language.nav_translations, PROBE: PROBE_LABEL})
        site = {english: french for english, french in language.nav_translations.items() if _SPACED_QUESTION.fullmatch(french)}
        nav = _dispatch_nav(site_config, [PROBE, *site])
        assert _titles(nav.items) == [f"Sonde{NBSP}: «{NBSP}vraiment{NBSP}»{NNBSP}?", *(french[:-2] + NNBSP + "?" for french in site.values())]

    @pytest.mark.parametrize("build", ["en", "it", "es"])
    def test_other_builds_keep_the_labels_the_plugin_puts_in(self, site_config, monkeypatch, build):
        i18n = site_config.plugins["i18n"]
        monkeypatch.setattr(i18n, "current_language", build)
        language = i18n.current_language_config
        monkeypatch.setitem(language, "nav_translations", {**(language.nav_translations or {}), PROBE: PROBE_LABEL})
        nav = _dispatch_nav(site_config, [PROBE])
        assert _titles(nav.items) == [PROBE_LABEL]


# ---------------------------------------------------------------------------
# A French page rendered with the site's Markdown configuration
# ---------------------------------------------------------------------------

FRENCH_PAGE = """\
# Guide : premiers pas

Le portefeuille vaut 28 398 € ; il a gagné 12,5 % en 2024 120 000 fois ? Vraiment !

## Étape 1 : choisir le broker

Cliquez sur « Enregistrer » puis tapez `ls -la : x ; y ?` dans le terminal.
Le ratio vaut $a : b$ sur 1 000 000 lignes.

$$
x : y ; z ? 1 000
$$

### Sous-titre : détails & co

```python
print("Total : 50 %")  # vraiment ?
```

```mermaid
sequenceDiagram
    Alice->>Bob : Bonjour !
```

!!! note "Remarque : important"

    Le taux est de 3,5 % ; voir [l'aide](https://example.org/aide?x=1 "Aide : page") :material-check:.

![Graphique : 28 398 €](https://example.org/g.png "Titre : image")
"""

# Pieces of the render the hook must leave as they are: (what, pattern on the render).
UNTOUCHED = [
    ("inline code", r"<code>ls -la : x ; y \?</code>"),
    ("inline formula", r'<span class="arithmatex">.*?</span>'),
    ("display formula", r'<div class="arithmatex">.*?</div>'),
    ("highlighted code block", r'<div class="highlight">.*?</div>'),
    ("mermaid diagram", r'<pre class="mermaid">.*?</pre>'),
    ("icon", r"<svg .*?</svg>"),
    ("image", r"<img [^>]*>"),
    ("link", r'<a href="https://example.org/aide[^>]*>'),
]


@pytest.fixture
def rendered(site_config) -> Page:
    """FRENCH_PAGE as the French build hands it to the hook: rendered by MkDocs with the site's Markdown extensions
    (``page.content``, ``page.toc``), its file made by mkdocs-static-i18n."""
    file = File("guide.fr.md", site_config["docs_dir"], site_config["site_dir"], site_config["use_directory_urls"])
    page = Page(None, i18n_suffix.create_i18n_file(file, "fr", "en", LANGUAGES, site_config), site_config)
    page.markdown = FRENCH_PAGE
    with _quiet_mkdocs():
        page.render(site_config, Files([]))
    return page


class TestRenderedFrenchPage:
    def test_the_prose_is_typeset(self, hook, rendered):
        out = hook.on_page_content(rendered.content, page=rendered, config=SimpleNamespace(), files=Files([]))
        for text in [
            f">Guide{NBSP}: premiers pas<",
            f"vaut 28{NNBSP}398{NNBSP}€{NNBSP}; il a gagné 12,5{NNBSP}% en 2024 120{NNBSP}000 fois{NNBSP}? Vraiment{NNBSP}!",
            f">Étape 1{NBSP}: choisir le broker<",
            f"«{NBSP}Enregistrer{NBSP}»",
            f"sur 1{NNBSP}000{NNBSP}000 lignes.",
            f">Sous-titre{NBSP}: détails &amp; co<",
            f">Remarque{NBSP}: important<",
            f"Le taux est de 3,5{NNBSP}%{NNBSP}; voir",
        ]:
            assert text in out, f"{text!r} is not in the typeset page:\n{out}"

    @pytest.mark.parametrize(("what", "pattern"), UNTOUCHED, ids=[what for what, _ in UNTOUCHED])
    def test_code_formulas_diagram_icon_and_attributes_are_as_rendered(self, hook, rendered, what, pattern):
        piece = re.search(pattern, rendered.content, re.S)
        assert piece, f"the render has no {what} ({pattern}): the page or the Markdown extensions changed\n{rendered.content}"
        out = hook.on_page_content(rendered.content, page=rendered, config=SimpleNamespace(), files=Files([]))
        assert piece.group(0) in out, f"the {what} changed: {piece.group(0)!r}"

    def test_the_toc_titles_are_typeset_at_every_level(self, hook, rendered):
        (top,) = rendered.toc
        (child,) = top.children
        (grandchild,) = child.children
        assert [top.title, child.title, grandchild.title] == ["Guide : premiers pas", "Étape 1 : choisir le broker", "Sous-titre : détails &amp; co"]
        hook.on_page_content(rendered.content, page=rendered, config=SimpleNamespace(), files=Files([]))
        assert [top.title, child.title, grandchild.title] == [f"Guide{NBSP}: premiers pas", f"Étape 1{NBSP}: choisir le broker", f"Sous-titre{NBSP}: détails &amp; co"]

    def test_the_render_keeps_the_invariants(self, hook, rendered):
        _assert_invariants(hook, rendered.content)


# ---------------------------------------------------------------------------
# Without MkDocs
# ---------------------------------------------------------------------------


def test_the_hook_loads_and_typesets_without_mkdocs(monkeypatch):
    monkeypatch.setitem(sys.modules, "mkdocs.plugins", None)  # `from mkdocs.plugins import ...` now raises ImportError
    module = _load_hook("fr_typography_without_mkdocs")
    assert module.typeset("Vraiment ?") == f"Vraiment{NNBSP}?"
    assert module.typeset_html("<p>Texte : <code>a : b</code></p>") == f"<p>Texte{NBSP}: <code>a : b</code></p>"
