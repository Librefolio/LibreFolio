"""translate-validate reads what a page renders: the checks of R2 batches 11-14 (M, R2 B13-B14).

Batches 11 and 12 changed ``mkdocs_src/aphra-pipeline/validate_translations.py`` and the structural diff of
``translate_docs.py``, and nothing covered the changes. Pinned here through the check functions
(``check_x(source, translated, cache_key, lang) -> list[Issue]``), ``_structural_diff`` and ``validate_file``:

* ``_strip_code_blocks`` is fence-aware (``code_blocks.code_line_mask``): backtick and tilde fences, at any
  indentation (list items, admonitions), with any info string or title. The former regex needed the language word
  to end the line. ``_strip_code`` removes the inline code spans as well;
* the HTML checks (``html-tag-mismatch``, ``html-attr-missing``, ``html-attr-mismatch``) read only what
  ``_strip_code`` leaves. Inline code such as ``EUR<USD`` was parsed as a ``<usd>`` tag whose "attributes" were the
  words of the following lines (201 warnings on user/fx/detail/data-editor). A real tag is still compared, and its
  text attributes (``alt``, ``title``, ``data-title``) may be translated;
* ``text-untranslated`` (WARN): an ``alt``, ``title``, ``aria-label`` or ``data-title`` value, or a Markdown image
  alt, of three words or more, copied verbatim from the source;
* ``inline-code-missing`` (WARN): every inline code span of the source is in the translation, as many times, digit
  grouping aside;
* ``anchor-missing`` (ERROR): a ``page.md#anchor`` link lands on an anchor of the page it opens, the translated page
  when it exists (mkdocs-static-i18n falls back to EN). Since batch 13 a page's anchors are the ids its MkDocs render
  records, not slugs made by hand (below);
* ``_structural_diff`` counts blank-line-separated blocks for ``LINE_COUNT``, not lines: a paragraph the translation
  keeps on one line while the EN wraps it at 80 columns is not dropped content.

Red phase, against the pipeline at 01c6f1ae4 (before batch 11), staged outside the worktree and imported first:
64 red, 7 green.

* red on behaviour (17): ``_strip_code_blocks`` leaves the code of a titled, a tilde, a "``` python" and a 4-backtick
  fence in the text, and an indentation-only line for a fence in a list item; inline code read as HTML (both
  fixtures); every LINE_COUNT case but two (lines, not blocks); ``validate_file`` (the ``<usd>`` false alarm, no
  new check);
* red on a missing function (47): everything reaching ``_strip_code``, ``check_untranslated_text_attrs``,
  ``check_inline_code`` or ``check_link_anchors``;
* green, and they must stay green (7): a changed technical attribute of a real tag (3 cases), translated text
  attributes, the two LINE_COUNT cases a count of lines leaves quiet as well (40 blocks, ±6), the fixture
  self-check.

Batch 13 made ``anchor-missing`` read the page's render. ``page_anchors.render_anchors`` runs MkDocs' ``Page.render``
with the site's configuration (``mkdocs_src/mkdocs.yml``) and returns ``Page.present_anchor_ids``, the set
``mkdocs build --strict`` checks a fragment against; ``file_anchors`` does it for a page on disk, once per version of
the file. The hand-made slugs it replaced offered the text slug of a heading with an explicit id (the build gives only
the id), numbered duplicates without counting explicit ids, read ``{#x}`` and ``id="x"`` written in inline code as
anchors and missed ``<a name="y">``, took a YAML comment of the front matter for a heading and an attr_list lookalike
in a YAML value for an id, slugged an emoji shortcode as text, and lost the first heading of a page starting with a
byte-order mark. ``render_anchors`` drops that mark, as MkDocs reads pages as utf-8-sig: ``validate_file`` reads a
translation as utf-8, so the in-page links of one starting with a mark were checked against a render that had lost
its first heading and rendered its front matter. ``inline-code-missing`` now names a span as the source writes it
(``1,000.50``, not the key ``100050`` it is compared on). Pinned through ``check_link_anchors`` (target pages and
in-page links), ``check_inline_code`` and ``page_anchors`` itself (a byte-order mark is not content; a file is
rendered again once it changes, and only then).

Red phase of batch 13, against the pipeline at f4a42bf4a (HEAD), staged outside the worktree and imported first, with
``page_anchors``, which HEAD lacks, taken from the worktree: 12 red, 84 green.

* red, on behaviour (12): every anchor case of ``TestLinkAnchorsReadTheRender`` (an explicit id in its three
  spellings, duplicates, inline code and raw HTML, emoji, front matter, in-page links, the byte-order mark of a target
  page and of the translation itself) and both spellings of a changed number;
* green (84): the 70 tests of batches 11-12 (the 71 less the bare Python-Markdown fixture self-check, replaced), which
  hold on both pipelines; the fixture guard (9), ``render_anchors`` (2) and ``file_anchors`` (3), which run
  ``page_anchors`` alone and have no HEAD counterpart.

The mark was first dropped only from files (``file_anchors`` reads utf-8-sig). Against a copy of ``page_anchors.py``
whose ``render_anchors`` keeps it, the three tests of a translation's own mark are red: the in-page link to its first
heading and ``render_anchors`` with the mark before a heading or before front matter.

Batch 14 added ``html-asset-depth`` (ERROR). A translated page is built one folder deeper than its English page
(``site/<lang>/...``), and the language folders hold only pages; MkDocs rewrites Markdown paths, not raw-HTML ones. A
raw-HTML relative path of a file (``src``, a ``srcset`` candidate, ``poster``, an ``href`` to a file that is not a
page) copied unchanged from the English therefore points where the file is not: 21 images shipped broken that way.
``check_html_asset_depth`` reports each URL of the translation identical to one of the English's, at the
translation's own line, with the path that reaches the same file from the translated page: pages are built with
directory URLs, so a path that climbs to the site root needs one more ``../`` and one that does not needs the way back
down. A changed path is left to the check ``./dev.py mkdocs build`` runs on the built site. Code, fenced or inline,
and HTML comments are not HTML; a comment keeps its lines. Batch 14 also made ``check_latex`` read inline math as
pymdownx.arithmatex does (smart dollar: no space after the opening ``$`` nor before the closing one, no unescaped
``$`` nor line break inside). The rule it replaced took a digit before a ``$`` for a price, and dropped the formula of
«on day 3 $A$'s line» from the English while the translation, worded otherwise, kept it: a false
``latex-inline-count`` on deposited-capital in it, fr and es. Red phase, against the pipeline at c0d933abf (HEAD),
staged outside the worktree and imported first: 24 red, 106 green.

* red on a missing function (18): every case of ``TestHtmlAssetDepth``;
* red on behaviour (6): ``validate_file``, which reported no error for the copy; the day-3 formula, counted in the
  translation only; a formula the translation breaks with a space, not reported; a formula after a price, not read;
  ``$ x$`` and ``$x $``, read as formulas;
* green (106): the tests of batches 11-13, unchanged, and the ten readings of inline math HEAD already got right
  (prices after their numbers, escaped dollars, display math, the prefix-price, shell-variable and markup filters).

Against the first version of batch 14 (the current file with one change reverted), the path that reaches the file is
red on the three paths that do not climb to the root, comments on the test that has them, and the old price rule on
the day-3 formula.

Batch 25 brought the CHANGELOG in: ``CHANGELOG.<lang>.md`` beside ``CHANGELOG.md`` (``changelog.py``;
``validate_changelog`` here, ``_diff_changelog`` in ``translate_docs.py``), checked chapter by chapter against the
English. Every chapter line must be an English one, once, in the English order; each chapter present goes through the
page checks (``validate_text``), and its pieces must be done in the cache for the current English. What a finding
weighs is the release policy's (``changelog.released``): every chapter but the newest is released, the newest once its
tag ``v<version>`` (or ``<version>``, as the release workflow's tag guard allows) exists or is the CI run's ref
(``GITHUB_REF``). A released chapter that is missing, stale or wrong is an error; the open chapter's findings are
information. ``translate-diff`` counts the released chapters' anomalies and absences and only prints the open
chapter's. Pinned through ``changelog.released`` (stubbed, then the real lookup: ``GITHUB_REF``, and a throwaway git
repository created in ``tmp_path`` with the tag under test), ``validate_changelog``, ``run_validate`` and ``run_diff``,
both commands with arguments parsed by their real parsers. Written against the new code, not red first; no test is
red now. One was red on it and named a defect, fixed since: ``test_an_empty_newest_chapter_leaves_the_chapter_below_it_released``
(``_diff_changelog`` applied the policy to the chapters that have a piece, so a newest chapter with nothing in it yet
handed its open status down to the released chapter below it, which ``translate-validate`` counted).

PURE: strings in memory and docs trees under ``tmp_path``. An autouse fixture points
``validate_translations.DOCS_DIR`` at an empty tree under ``tmp_path`` in every test, so no check resolves a link
against ``mkdocs_src/docs``; the repository's docs and ``.translate-hashes.json`` are never opened (the Aphra pipeline
may be rewriting them while this runs). The CHANGELOG tests put ``CHANGELOG.md``, its translations and the cache under
``tmp_path`` (``_changelog_source`` of both modules, ``translate_docs.HASH_FILE``, which the validator's
``_load_hashes`` reads, ``translate_docs.DOCS_DIR``; ``changelog.SOURCE`` at a folder that does not exist), and stub
the tag lookup; the tests of the real lookup run git in ``tmp_path`` alone (``GIT_CEILING_DIRECTORIES``, no global or
system configuration, a local identity), reading tags, or creating a throwaway repository there: never the project's.
The repository's ``CHANGELOG*.md`` are never opened. ``page_anchors`` loads the
site's configuration, ``mkdocs_src/mkdocs.yml``, once per process; no page of ``mkdocs_src/docs`` is read.
``TestFixtures`` renders every anchor fixture with it, to prove the expected anchors are the ones a build gives. No DB,
no server, no network, no writes outside ``tmp_path``.
"""

import argparse
import dataclasses
import hashlib
import importlib
import json
import os
import posixpath
import re
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit

import markdown
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_DIR = PROJECT_ROOT / "mkdocs_src" / "aphra-pipeline"
CACHE_KEY = "user/guide.en.md"  # the page under validation, relative to DOCS_DIR
LANG = "it"


# ---------------------------------------------------------------------------
# Pipeline modules, imported by bare name as dev.py loads them. They are reached only through fixtures and test
# bodies, so a function an older pipeline lacks fails the tests that call it, never the collection.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pipeline_on_path():
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(PIPELINE_DIR))
        yield PIPELINE_DIR


@pytest.fixture(scope="module")
def validate_translations(pipeline_on_path) -> ModuleType:
    module = importlib.import_module("validate_translations")
    assert hasattr(module, "ALL_CHECKS") and hasattr(module, "validate_file"), f"not the pipeline script: {module.__file__}"
    return module


@pytest.fixture(scope="module")
def translate_docs(pipeline_on_path) -> ModuleType:
    module = importlib.import_module("translate_docs")
    assert hasattr(module, "_structural_diff"), f"not the pipeline script: {module.__file__}"
    return module


@pytest.fixture(scope="module")
def page_anchors(pipeline_on_path) -> ModuleType:
    module = importlib.import_module("page_anchors")
    assert hasattr(module, "render_anchors") and hasattr(module, "file_anchors"), f"not the pipeline module: {module.__file__}"
    return module


@pytest.fixture(autouse=True)
def docs(validate_translations, tmp_path, monkeypatch) -> Path:
    """An empty docs tree under tmp_path, as DOCS_DIR: no check ever resolves a link against mkdocs_src/docs."""
    root = (tmp_path / "docs").resolve()
    (root / "user").mkdir(parents=True)
    monkeypatch.setattr(validate_translations, "DOCS_DIR", root)
    return root


def _write(docs: Path, rel: str, text: str) -> Path:
    path = docs / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _kinds(issues) -> list[tuple[str, str]]:
    """(check, severity) of each issue, in order: what the tests compare, rather than whole messages."""
    return [(issue.check, issue.severity) for issue in issues]


# ---------------------------------------------------------------------------
# _strip_code_blocks / _strip_code
# ---------------------------------------------------------------------------


class TestStripCode:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param('Intro\n\n```yaml title="compose.yml"\nservices: {}\n```\n\nOutro', "Intro\n\n\nOutro", id="backtick-fence-with-info-string-and-title"),
            pytest.param("Intro\n\n~~~text\nplain body\n~~~\n\nOutro", "Intro\n\n\nOutro", id="tilde-fence"),
            pytest.param("1. Start it:\n\n    ```bash\n    docker compose up -d\n    ```\n\n2. Open the app", "1. Start it:\n\n\n2. Open the app", id="indented-in-a-list-item"),
            pytest.param('!!! note "Heads up"\n\n    ``` python\n    print("hi")\n    ```\n\nAfter', '!!! note "Heads up"\n\n\nAfter', id="indented-in-an-admonition-info-after-a-space"),
            pytest.param("Intro\n\n````markdown\n```python\nx = 1\n```\n````\n\nOutro", "Intro\n\n\nOutro", id="longer-fence-holding-a-shorter-one"),
        ],
    )
    def test_strip_code_blocks_removes_every_fenced_block_and_keeps_the_prose(self, validate_translations, text, expected):
        assert validate_translations._strip_code_blocks(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("Run `ls -la` now.", "Run  now.", id="single-backticks"),
            pytest.param("Type ``a `quoted` word`` here.", "Type  here.", id="double-backticks-around-a-backtick"),
            pytest.param("Quote `EUR<USD` as `<username>` does.", "Quote  as  does.", id="two-spans-on-one-line"),
            pytest.param("Intro `x`.\n\n~~~bash\necho `pwd`\n~~~\n\nOutro", "Intro .\n\n\nOutro", id="inline-and-fenced"),
            pytest.param("Press ` to open the console.", "Press ` to open the console.", id="a-lone-backtick-is-prose"),
        ],
    )
    def test_strip_code_removes_inline_spans_too_and_keeps_the_prose(self, validate_translations, text, expected):
        assert validate_translations._strip_code(text) == expected


# ---------------------------------------------------------------------------
# HTML checks: rendered HTML only
# ---------------------------------------------------------------------------

# Inline code that looks like a tag, kept verbatim by the translation. Read as HTML, `<USD` ran to the next `>` and
# took the words in between as attributes.
EUR_USD_EN = textwrap.dedent("""\
    Quote a pair as `EUR<USD` when the euro is the weaker currency of the two.

    <img class="chart" src="../static/fx.png" alt="Chart of the EUR/USD rate">
    """)
EUR_USD_IT = textwrap.dedent("""\
    Quota una coppia come `EUR<USD` quando l'euro è la valuta più debole delle due.

    <img class="chart" src="../static/fx.png" alt="Grafico del cambio EUR/USD">
    """)
# The translation moves the spans: read as HTML, `<USD` then swallowed the `<username>` that follows it.
USERNAME_EN = "Log in as `<username>`, then open the `EUR<USD` chart.\n"
USERNAME_IT = "Apri il grafico `EUR<USD` dopo aver effettuato l'accesso come `<username>`.\n"

# A real tag after inline code: stripping the code must leave it to the comparison.
IMG_TEXTS = ("The import wizard on its first step", "Import wizard overview", "Step one of the import")
IMG_EN = textwrap.dedent("""\
    The wizard quotes pairs as `EUR<USD`.

    <img class="shot" src="../static/wizard.png" data-name="wizard" alt="The import wizard on its first step" title="Import wizard overview" data-title="Step one of the import">
    """)
IMG_IT = IMG_EN.replace("The wizard quotes pairs as", "La procedura quota le coppie come").replace(IMG_TEXTS[0], "La procedura di importazione al primo passo").replace(IMG_TEXTS[1], "Panoramica della procedura").replace(IMG_TEXTS[2], "Primo passo dell'importazione")


class TestHtmlChecksReadRenderedHtml:
    @pytest.mark.parametrize(
        ("source", "translated"),
        [
            pytest.param(EUR_USD_EN, EUR_USD_IT, id="eur-usd-span-before-a-real-img"),
            pytest.param(USERNAME_EN, USERNAME_IT, id="username-span-moved-by-the-translation"),
        ],
    )
    def test_inline_code_that_looks_like_a_tag_is_not_html(self, validate_translations, source, translated):
        vt = validate_translations
        issues = vt.check_html_blocks(source, translated, CACHE_KEY, LANG) + vt.check_html_attrs(source, translated, CACHE_KEY, LANG)
        assert [str(issue) for issue in issues] == []

    def test_translated_alt_title_and_data_title_are_not_reported(self, validate_translations):
        vt = validate_translations
        assert [text for text in IMG_TEXTS if text in IMG_IT] == [], "barrier: the fixture translates every text attribute"
        assert vt.check_html_blocks(IMG_EN, IMG_IT, CACHE_KEY, LANG) == []
        assert vt.check_html_attrs(IMG_EN, IMG_IT, CACHE_KEY, LANG) == []

    @pytest.mark.parametrize(
        ("old", "new", "check", "attribute"),
        [
            pytest.param('class="shot"', 'class="foto"', "html-attr-mismatch", "class", id="class-changed"),
            pytest.param('src="../static/wizard.png"', 'src="../static/procedura.png"', "html-attr-mismatch", "src", id="src-changed"),
            pytest.param(' data-name="wizard"', "", "html-attr-missing", "data-name", id="data-name-dropped"),
        ],
    )
    def test_a_changed_technical_attribute_of_a_real_tag_is_still_reported(self, validate_translations, old, new, check, attribute):
        vt = validate_translations
        translated = IMG_IT.replace(old, new)
        assert translated != IMG_IT, "barrier: the edit applies"
        issues = vt.check_html_attrs(IMG_EN, translated, CACHE_KEY, LANG)
        assert _kinds(issues) == [(check, vt.Severity.WARN)]
        assert f"`{attribute}`" in issues[0].message


# ---------------------------------------------------------------------------
# check_untranslated_text_attrs (text-untranslated)
# ---------------------------------------------------------------------------

EN_TEXT = "Bulk workspace with a cloned row"
IT_TEXT = "Area di lavoro massiva con una riga clonata"
TEXT_SLOTS = [
    pytest.param('<img src="bulk.png" alt="{}">', id="img-alt"),
    pytest.param('<a href="import.md" title="{}">Import</a>', id="title"),
    pytest.param('<button aria-label="{}">x</button>', id="aria-label"),
    pytest.param('<img src="bulk.png" data-title="{}">', id="data-title-caption"),
    pytest.param("![{}](bulk.png)", id="markdown-image-alt"),
]


def _page_with(slot: str, value: str, prose: str) -> str:
    return f"{prose}\n\n{slot.format(value)}\n"


def _untranslated(vt, page: str) -> list:
    """The check on a translation identical to its source."""
    return vt.check_untranslated_text_attrs(page, page, CACHE_KEY, LANG)


class TestUntranslatedTextAttrs:
    @pytest.mark.parametrize("slot", TEXT_SLOTS)
    def test_a_value_copied_from_the_source_is_a_warning(self, validate_translations, slot):
        vt = validate_translations
        issues = vt.check_untranslated_text_attrs(_page_with(slot, EN_TEXT, "Intro."), _page_with(slot, EN_TEXT, "Introduzione."), CACHE_KEY, LANG)
        assert _kinds(issues) == [("text-untranslated", vt.Severity.WARN)]
        assert EN_TEXT in issues[0].message

    @pytest.mark.parametrize("slot", TEXT_SLOTS)
    def test_a_translated_value_passes(self, validate_translations, slot):
        vt = validate_translations
        assert vt.check_untranslated_text_attrs(_page_with(slot, EN_TEXT, "Intro."), _page_with(slot, IT_TEXT, "Introduzione."), CACHE_KEY, LANG) == []

    @pytest.mark.parametrize(
        ("value", "reported"),
        [
            pytest.param("Import wizard", False, id="two-words-pass"),
            pytest.param("Import wizard opened", True, id="three-words-warn"),
            pytest.param("Buy Me a Coffee", False, id="allowed-brand-name-passes"),
        ],
    )
    def test_only_values_of_three_words_or_more_count(self, validate_translations, value, reported):
        vt = validate_translations
        issues = _untranslated(vt, f'<img src="x.png" alt="{value}">\n')
        assert _kinds(issues) == ([("text-untranslated", vt.Severity.WARN)] if reported else [])

    @pytest.mark.parametrize("attribute", ["foo-title", "xtitle"])
    def test_a_longer_attribute_name_ending_in_title_is_not_read(self, validate_translations, attribute):
        vt = validate_translations
        assert _kinds(_untranslated(vt, f'<span title="{EN_TEXT}"></span>\n')) == [("text-untranslated", vt.Severity.WARN)], "barrier: the value itself is reported"
        assert _untranslated(vt, f'<span {attribute}="{EN_TEXT}"></span>\n') == []

    def test_single_quoted_values_are_not_read_current_behaviour(self, validate_translations):
        """Documents the current scope, not a requirement: only double-quoted values are read, so a value copied in
        single quotes goes unreported. Extending the check to them turns this test red on purpose."""
        vt = validate_translations
        assert _kinds(_untranslated(vt, f'<img src="x.png" alt="{EN_TEXT}">\n')) == [("text-untranslated", vt.Severity.WARN)], "barrier: the value itself is reported"
        assert _untranslated(vt, f"<img src='x.png' alt='{EN_TEXT}'>\n") == []

    def test_values_inside_code_are_ignored(self, validate_translations):
        vt = validate_translations
        img, link = f'<img src="x.png" alt="{EN_TEXT}">', '<a href="import.md" title="Open the import wizard">Import</a>'
        assert len(_untranslated(vt, f"{img}\n\n{link}\n")) == 2, "barrier: both values are reported outside code"
        assert _untranslated(vt, f"Write `{img}` in the page.\n\n```html\n{link}\n```\n") == []


# ---------------------------------------------------------------------------
# check_html_asset_depth (html-asset-depth)
# ---------------------------------------------------------------------------

# CACHE_KEY, user/guide.md, is built as site/user/guide/, its translation as site/it/user/guide/: the English climbs two
# folders to static/, the translation three. MkDocs rewrites Markdown paths, not raw HTML ones.
EN_IMG = '<img src="../../static/a.png" alt="Chart">'
IT_IMG_COPIED = '<img src="../../static/a.png" alt="Grafico">'
IT_IMG_SHIFTED = '<img src="../../../static/a.png" alt="Grafico">'


def _asset_depth(vt, source: str, translated: str) -> list:
    return vt.check_html_asset_depth(source, translated, CACHE_KEY, LANG)


def _flagged_urls(issues) -> list[str]:
    """The URL each html-asset-depth message names as the English path."""
    return [re.match(r"L\d+: `([^`]+)` is the English path", issue.message).group(1) for issue in issues]


class TestHtmlAssetDepth:
    def test_a_path_copied_from_the_english_is_an_error_naming_its_line_and_the_fix(self, validate_translations):
        vt = validate_translations
        source = f"# Guide\n\n{EN_IMG}\n"
        translated = f"# Guida\n\nUn paragrafo che l'inglese non ha.\n\n{IT_IMG_COPIED}\n"
        issues = _asset_depth(vt, source, translated)
        assert _kinds(issues) == [("html-asset-depth", vt.Severity.ERROR)]
        assert issues[0].message.startswith("L5: `../../static/a.png` "), issues[0].message  # the translation's line, not the source's (L3)
        assert "`../../../static/a.png`" in issues[0].message, issues[0].message

    @pytest.mark.parametrize(
        "translated",
        [
            pytest.param(IT_IMG_SHIFTED, id="one-folder-deeper"),
            pytest.param('<img src="../../../static/b.png" alt="Grafico">', id="a-url-only-the-translation-has"),
            pytest.param('<img src="../static/a.png" alt="Grafico">', id="changed-otherwise"),
        ],
    )
    def test_a_changed_path_is_left_to_the_build_check(self, validate_translations, translated):
        assert _asset_depth(validate_translations, f"{EN_IMG}\n", f"{translated}\n") == []

    def test_page_links_and_urls_that_are_not_relative_files_are_not_compared(self, validate_translations):
        vt = validate_translations
        page = "\n".join(
            [
                '<a href="scalable/">Scalable</a> <a href="../x.md">X</a> <a href="p.html">P</a> <a href="p.htm">P</a>',
                '<img src="https://example.com/a.png"> <img src="//cdn.example.com/a.png"> <img src="/static/a.png">',
                '<a href="#top">Top</a> <img src="data:image/png;base64,iVBORw0KGgo=">',
            ]
        )
        assert _kinds(_asset_depth(vt, f"{page}\n{EN_IMG}\n", f"{page}\n{IT_IMG_COPIED}\n")) == [("html-asset-depth", vt.Severity.ERROR)], "barrier: a file path copied on the same page is reported"
        assert _asset_depth(vt, f"{page}\n", f"{page}\n") == []

    @pytest.mark.parametrize(
        ("source", "translated", "flagged"),
        [
            pytest.param('<img srcset="../../static/a.png 1x, ../../static/b.png 2x">', '<img srcset="../../../static/a.png 1x, ../../static/b.png 2x">', ["../../static/b.png"], id="srcset-the-copied-candidate"),
            pytest.param('<video src="../../static/v.mp4" poster="../../static/p.jpg"></video>', '<video src="../../../static/v.mp4" poster="../../static/p.jpg"></video>', ["../../static/p.jpg"], id="poster"),
            pytest.param('<a href="../../static/report.pdf">PDF</a>', '<a href="../../static/report.pdf">PDF</a>', ["../../static/report.pdf"], id="a-link-to-a-file"),
            pytest.param('<img data-src="../../static/a.png">', '<img data-src="../../static/a.png">', [], id="data-src-is-not-src"),
        ],
    )
    def test_each_file_url_attribute_is_compared(self, validate_translations, source, translated, flagged):
        assert _flagged_urls(_asset_depth(validate_translations, f"{source}\n", f"{translated}\n")) == flagged

    def test_code_is_not_html(self, validate_translations):
        vt = validate_translations
        assert _kinds(_asset_depth(vt, f"{EN_IMG}\n", f"{IT_IMG_COPIED}\n")) == [("html-asset-depth", vt.Severity.ERROR)], "barrier: outside code the copy is reported"
        translated = f"Scrivi `{IT_IMG_COPIED}` nella pagina.\n\n```html\n{IT_IMG_COPIED}\n```\n\n1. In un elenco:\n\n    ~~~html\n    {IT_IMG_COPIED}\n    ~~~\n"
        assert _asset_depth(vt, f"{EN_IMG}\n", translated) == []

    def test_an_image_in_a_heading_line_is_html(self, validate_translations):
        vt = validate_translations
        issues = _asset_depth(vt, '# <img src="../../static/a.png" alt=""> Title\n', '# <img src="../../static/a.png" alt=""> Titolo\n')
        assert _kinds(issues) == [("html-asset-depth", vt.Severity.ERROR)]
        assert issues[0].message.startswith("L1: "), issues[0].message

    def test_the_line_number_counts_the_lines_of_a_fenced_block_before_it(self, validate_translations):
        translated = f"# Guida\n\n```bash\necho uno\necho due\n```\n\n{IT_IMG_COPIED}\n"
        line = translated.split("\n").index(IT_IMG_COPIED) + 1
        assert line == 8, "barrier: the tag is on the eighth line of the translation"
        issues = _asset_depth(validate_translations, f"{EN_IMG}\n", translated)
        assert [issue.message.split(":", 1)[0] for issue in issues] == ["L8"]

    @pytest.mark.parametrize(
        ("cache_key", "lang", "built", "url", "fix"),
        [
            pytest.param("user/x/index.en.md", "it", "user/x", "../../static/a.png", "../../../static/a.png", id="up-to-the-root-one-more-up"),
            pytest.param("user/x/index.en.md", "it", "user/x", "../img.png", "../../../user/img.png", id="into-its-section-back-down-from-the-root"),
            pytest.param("user/x/page.en.md", "es", "user/x/page", "shot.png?v=2#top", "../../../../user/x/page/shot.png?v=2#top", id="a-page-not-an-index-query-and-fragment-kept"),
            pytest.param("faq.en.md", "fr", "faq", "../static/a.png", "../../static/a.png", id="a-top-level-page"),
            pytest.param("user/v1.2.en.md", "it", "user/v1.2", "shot.png", "../../../user/v1.2/shot.png", id="a-page-whose-name-holds-a-dot"),
        ],
    )
    def test_the_fix_reaches_from_the_translated_page_the_file_the_english_reaches(self, validate_translations, cache_key, lang, built, url, fix):
        """Pages are built with directory URLs (x/index.md into x/, x/page.md into x/page/), a translation under <lang>/."""
        path = urlsplit(url).path
        assert posixpath.normpath(posixpath.join(built, path)) == posixpath.normpath(posixpath.join(lang, built, urlsplit(fix).path)), "barrier: from the translated page, the fix lands on the English URL's file"
        issues = validate_translations.check_html_asset_depth(f'<img src="{url}">\n', f'<img src="{url}">\n', cache_key, lang)
        assert [issue.message.rsplit("so it needs ", 1)[-1] for issue in issues] == [f"`{fix}`"]

    def test_an_html_comment_is_not_html_and_keeps_its_lines(self, validate_translations):
        translated = f"# Guida\n\n<!-- {IT_IMG_COPIED} -->\n\n<!--\nPrima versione:\n{IT_IMG_COPIED}\n-->\n\n{IT_IMG_COPIED}\n"
        assert translated.split("\n")[9] == IT_IMG_COPIED, "barrier: the tag outside the comments is on line 10"
        issues = _asset_depth(validate_translations, f"{EN_IMG}\n", translated)
        assert [issue.message.split(":", 1)[0] for issue in issues] == ["L10"]


# ---------------------------------------------------------------------------
# check_latex: inline math as pymdownx.arithmatex reads it (latex-inline-count)
# ---------------------------------------------------------------------------


def _latex_inline(vt, source: str, translated: str) -> list:
    return [issue for issue in vt.check_latex(source, translated, CACHE_KEY, LANG) if issue.check.startswith("latex-inline")]


def _inline_formulas(vt, text: str) -> list[str]:
    """The inline formulas check_latex reads in ``text``, in order. Compared with a page without math it reports their
    count; compared with a page holding as many formulas of its own, each pair as modified, the text's first."""
    counted = [issue.message for issue in _latex_inline(vt, text, "") if issue.check == "latex-inline-count"]
    count = int(re.fullmatch(r"Inline math: source (\d+), translation 0", counted[0]).group(1)) if counted else 0
    probe = " ".join(f"$\\omega_{{{9000 + n}}}$" for n in range(count))
    modified = [issue.message for issue in _latex_inline(vt, text, probe) if issue.check == "latex-inline-modified"]
    assert len(modified) == count, f"barrier: each formula pairs with one of the probe: {modified}"
    return [re.search(r"SRC: \$(.*)\$\n", message).group(1) for message in modified]


class TestInlineMath:
    """Smart dollar, the site's arithmatex default: the opening ``$`` is not followed by a space, the closing one not
    preceded by one, and a formula holds no unescaped ``$`` nor a line break."""

    def test_a_formula_after_a_number_counts_in_the_source_too(self, validate_translations):
        """deposited-capital: the former rule took a digit before the ``$`` for a price («500 $») and dropped the
        English formula, which the translation, worded otherwise, kept: a false latex-inline-count in it, fr and es."""
        source = "The chart starts on day 3 $A$'s line, then follows the deposits.\n"
        translated = "Il grafico parte il giorno 3, la linea di $A$, poi segue i depositi.\n"
        assert _latex_inline(validate_translations, source, translated) == []

    def test_a_formula_the_translation_breaks_with_a_space_is_reported(self, validate_translations):
        vt = validate_translations
        issues = _latex_inline(vt, "The weight $w$ of each asset.\n", "Il peso $ w$ di ogni titolo.\n")
        assert [(issue.check, issue.severity, issue.message) for issue in issues] == [("latex-inline-count", vt.Severity.WARN, "Inline math: source 1, translation 0")]

    @pytest.mark.parametrize(
        ("text", "formulas"),
        [
            pytest.param("Il rendimento $r$ e il peso $\\beta_1$.", ["r", "\\beta_1"], id="two-formulas"),
            pytest.param("costa 500 $ al mese", [], id="a-price-after-its-number"),
            pytest.param("entre 0,25 $ et 1,50 $ par jour", [], id="two-prices-after-their-numbers"),
            pytest.param("costa 500 $ e poi $x$", ["x"], id="a-price-then-a-formula"),
            pytest.param("il valore $ x$ e basta", [], id="a-space-after-the-opening-dollar"),
            pytest.param("il valore $x $ e basta", [], id="a-space-before-the-closing-dollar"),
            pytest.param("costs \\$5 and \\$6", [], id="escaped-dollars"),
            pytest.param("the share $a\\$b$ of it", ["a\\$b"], id="an-escaped-dollar-inside-a-formula"),
            pytest.param("the share $a\nb$ of it", [], id="no-line-break-inside"),
            pytest.param("$$x + y$$", [], id="display-math-is-not-inline"),
            pytest.param("between $0.25-$0.50 a day", [], id="prices-before-their-numbers"),
            pytest.param("PATH=${HOME}/bin:${PATH}", [], id="shell-variables"),
            pytest.param("Use **$var** in bash and **$other** in zsh", [], id="markup-between-two-dollars"),
        ],
    )
    def test_inline_math_is_read_as_arithmatex_reads_it(self, validate_translations, text, formulas):
        assert _inline_formulas(validate_translations, text) == formulas


# ---------------------------------------------------------------------------
# check_inline_code (inline-code-missing)
# ---------------------------------------------------------------------------


class TestInlineCode:
    def test_spans_kept_verbatim_pass_and_spans_only_the_translation_has_are_allowed(self, validate_translations):
        vt = validate_translations
        source = "Set `total_return` and `period`, then run `./dev.py mkdocs build`.\n"
        translated = "Imposta `total_return` e `period`, poi esegui `./dev.py mkdocs build` (anche con `--strict`).\n"
        assert vt.check_inline_code(source, translated, CACHE_KEY, LANG) == []

    def test_a_translated_identifier_is_reported(self, validate_translations):
        vt = validate_translations
        source = "Set `total_return` and `period` before you start.\n"
        translated = "Imposta `rendimento_totale` e `period` prima di iniziare.\n"
        issues = vt.check_inline_code(source, translated, CACHE_KEY, LANG)
        assert _kinds(issues) == [("inline-code-missing", vt.Severity.WARN)]
        assert "`total_return`" in issues[0].message

    @pytest.mark.parametrize(
        ("translated", "shown"),
        [
            pytest.param("Usa `asset_id` qui e anche lì.\n", None, id="twice-in-en-once-in-translation"),
            pytest.param("Usa l'identificativo qui e anche lì.\n", "×2", id="twice-in-en-never-in-translation"),
        ],
    )
    def test_occurrences_are_counted_and_a_span_is_reported_once(self, validate_translations, translated, shown):
        vt = validate_translations
        issues = vt.check_inline_code("Use `asset_id` here and `asset_id` there.\n", translated, CACHE_KEY, LANG)
        assert _kinds(issues) == [("inline-code-missing", vt.Severity.WARN)]
        message = issues[0].message
        assert "`asset_id`" in message
        assert (shown in message) if shown else ("×" not in message), message

    @pytest.mark.parametrize(
        ("en", "localized"),
        [
            pytest.param("1,000.50", "1.000,50", id="grouping-and-decimal-swapped"),
            pytest.param("1,234,567.89", "1.234.567,89", id="several-groups"),
            pytest.param("12,345", "12\u00a0345", id="nbsp-grouping"),
            pytest.param("12,345", "12\u202f345", id="narrow-nbsp-grouping"),
            pytest.param("12,345", "12 345", id="space-grouping"),
        ],
    )
    def test_digit_grouping_may_be_localized(self, validate_translations, en, localized):
        vt = validate_translations
        assert vt.check_inline_code(f"A fee of `{en}` EUR.\n", f"Una commissione di `{localized}` EUR.\n", CACHE_KEY, LANG) == []

    def test_a_changed_number_is_still_reported(self, validate_translations):
        """Check and severity only: the spelling the message gives is the next test's."""
        vt = validate_translations
        issues = vt.check_inline_code("A fee of `1,000.50` EUR.\n", "Una commissione di `1.500,00` EUR.\n", CACHE_KEY, LANG)
        assert _kinds(issues) == [("inline-code-missing", vt.Severity.WARN)]

    @pytest.mark.parametrize(
        ("source", "translated", "shown"),
        [
            pytest.param("A fee of `1,000.50` EUR.\n", "Una commissione di `1.500,00` EUR.\n", "`1,000.50`", id="grouping-and-decimal"),
            pytest.param("Up to `12,345` rows, `12,345` at most.\n", "Fino a `12 346` righe.\n", "`12,345` ×2", id="twice-in-en"),
        ],
    )
    def test_a_changed_number_is_named_as_the_source_writes_it(self, validate_translations, source, translated, shown):
        """Not as the key it is compared on, digit grouping removed (``100050``): the translator searches the source for it."""
        vt = validate_translations
        issues = vt.check_inline_code(source, translated, CACHE_KEY, LANG)
        assert _kinds(issues) == [("inline-code-missing", vt.Severity.WARN)]
        assert shown in issues[0].message, issues[0].message

    def test_spans_inside_fenced_code_are_ignored(self, validate_translations):
        vt = validate_translations
        line_en, line_it = "Run `make build` first.", "Esegui prima `make compila`."
        assert _kinds(vt.check_inline_code(f"{line_en}\n", f"{line_it}\n", CACHE_KEY, LANG)) == [("inline-code-missing", vt.Severity.WARN)], "barrier: outside a fence the change is reported"
        source = f"Build it:\n\n```text\n{line_en}\n```\n"
        translated = f"Compilalo:\n\n```text\n{line_it}\n```\n"
        assert vt.check_inline_code(source, translated, CACHE_KEY, LANG) == []


# ---------------------------------------------------------------------------
# check_link_anchors (anchor-missing), on a docs tree under tmp_path
# ---------------------------------------------------------------------------

TARGET_EN = "# Target\n\n## English heading\n"
TARGET_IT = "# Obiettivo\n\n## Titolo {: #x }\n\n## Intestazione italiana\n"
FALLBACK_EN = "# English only\n\n## Fallback heading\n"
SECTION_EN = "# Section\n\n## Section heading\n"

# A translated glossary: the anchors the site's render gives it (TestFixtures proves it) and near misses it does not.
SLUG_PAGE = textwrap.dedent("""\
    # Glossario

    ## Café crème à la carte

    ## What's new? (v2.0)

    ## Prix & coûts — détails

    ## `total_return` spiegato

    ## Vedi [la guida](guide.md) prima

    ## **Grassetto** e *corsivo*

    ## Résumé

    ## Résumé

    ## Résumé

    ```bash
    # not-a-heading
    ```

    <div id="fees-box" markdown>

    Commissioni.

    </div>
    """)
SLUG_ANCHORS = (
    "glossario",
    "cafe-creme-a-la-carte",  # accents stripped
    "whats-new-v20",  # punctuation removed
    "prix-couts-details",
    "total_return-spiegato",  # code text kept, underscore included
    "vedi-la-guida-prima",  # link text kept
    "grassetto-e-corsivo",  # emphasis markers dropped
    "resume",
    "resume_1",  # duplicates numbered
    "resume_2",
    "fees-box",  # an HTML id
)
# What a translator might write instead: accents or the dot kept, a fourth duplicate, a dash for the underscore, a
# capital, a prefix of the HTML id, and the text of a `# comment` inside a fence, which is no heading.
NEAR_MISSES = ("café-crème-à-la-carte", "whats-new-v2.0", "résumé", "resume_3", "total-return-spiegato", "Glossario", "fees", "not-a-heading")

# Batch 13: pages whose anchors the hand-made slugs got wrong. Each case gives the anchors the site's render records
# (TestFixtures proves it) and the near misses the slugs offered instead.
CODE_AND_HTML_PAGE = textwrap.dedent("""\
    # Pagina

    Scrivi `## Titolo {: #scritto }` per fissare l'ancora, oppure `id="attributo"` in un tag.

    <div id="riquadro" markdown>

    Testo nel riquadro.

    </div>

    Un <a name="segnalibro"></a>segnalibro nel testo.
    """)
EMOJI_PAGE = "# Supporto\n\n## :coffee: Buy Me a Coffee\n"
FRONT_MATTER_PAGE = textwrap.dedent("""\
    ---
    title: Glossario
    # Revisione: traduzione 2026
    description: "Le voci del glossario {#fm-id}"
    ---

    # Glossario

    ## Voci
    """)
RENDER_CASES = [
    # attr_list's three spellings, all used in the docs: the heading gets the id, and its text slug is no anchor.
    *(pytest.param(f"# Pagina\n\n## Titolo tradotto {syntax}\n", ("pagina", "en-id"), ("titolo-tradotto",), id=f"explicit-id-only-{name}") for name, syntax in (("colon", "{: #en-id }"), ("spaced", "{ #en-id }"), ("compact", "{#en-id}"))),
    # The toc numbers a duplicate after the ids already given, explicit ones included: "Foo" comes second.
    pytest.param("# Pagina\n\n## Bar {: #foo }\n\n## Foo\n", ("pagina", "foo", "foo_1"), ("bar",), id="duplicates-numbered-after-explicit-ids"),
    # Written in inline code, `{: #x }` and `id="x"` are text; a raw HTML id and <a name> are anchors.
    pytest.param(CODE_AND_HTML_PAGE, ("pagina", "riquadro", "segnalibro"), ("scritto", "attributo"), id="ids-in-inline-code-no-raw-html-ids-yes"),
    # pymdownx.emoji (site config) renders the shortcode as an icon: it is not part of the heading's text.
    pytest.param(EMOJI_PAGE, ("supporto", "buy-me-a-coffee"), ("coffee-buy-me-a-coffee",), id="emoji-shortcode-rendered-by-the-site"),
    # Split off before rendering: a YAML comment is no heading, a value that looks like attr_list no id.
    pytest.param(FRONT_MATTER_PAGE, ("glossario", "voci"), ("revisione-traduzione-2026", "fm-id"), id="front-matter-not-rendered"),
]


@pytest.fixture
def tree(docs) -> Path:
    """Pages linked from user/guide: target (EN and IT), fallback (EN only), section/ (an EN index)."""
    _write(docs, "user/target.en.md", TARGET_EN)
    _write(docs, "user/target.it.md", TARGET_IT)
    _write(docs, "user/fallback.en.md", FALLBACK_EN)
    _write(docs, "user/section/index.en.md", SECTION_EN)
    return docs


def _links(*urls: str) -> str:
    return "\n\n".join(f"See [link {n}]({url})." for n, url in enumerate(urls, 1)) + "\n"


class TestLinkAnchors:
    @pytest.mark.parametrize(
        ("lang", "url"),
        [
            pytest.param("it", "target.md#x", id="explicit-id-of-the-translated-target"),
            pytest.param("it", "target.md#intestazione-italiana", id="heading-slug-of-the-translated-target"),
            pytest.param("it", "fallback.md#fallback-heading", id="no-translated-target-falls-back-to-en"),
            pytest.param("fr", "target.md#english-heading", id="no-fr-target-falls-back-to-en-not-to-it"),
            pytest.param("it", "section/#section-heading", id="directory-link-opens-its-index"),
            pytest.param("it", "../user/target.md#x", id="relative-path-up-and-back"),
        ],
    )
    def test_a_link_to_an_anchor_of_the_page_it_opens_passes(self, validate_translations, tree, lang, url):
        assert validate_translations.check_link_anchors(_links(url), _links(url), CACHE_KEY, lang) == []

    @pytest.mark.parametrize(
        ("lang", "url", "opened"),
        [
            pytest.param("it", "target.md#english-heading", "user/target.it.md", id="translated-target-lacks-the-en-slug"),
            pytest.param("it", "fallback.md#missing", "user/fallback.en.md", id="en-fallback-lacks-the-anchor"),
            pytest.param("fr", "target.md#x", "user/target.en.md", id="fr-falls-back-to-en-which-lacks-the-it-id"),
            pytest.param("it", "section/#missing", "user/section/index.en.md", id="directory-index-lacks-the-anchor"),
        ],
    )
    def test_a_link_to_a_missing_anchor_is_an_error_naming_the_page_it_opens(self, validate_translations, tree, lang, url, opened):
        vt = validate_translations
        issues = vt.check_link_anchors(_links(url), _links(url), CACHE_KEY, lang)
        assert _kinds(issues) == [("anchor-missing", vt.Severity.ERROR)]
        assert opened in issues[0].message and url in issues[0].message, issues[0].message

    def test_an_in_page_anchor_is_checked_against_the_translated_page_itself(self, validate_translations):
        vt = validate_translations
        source = "## Advanced configuration\n\nSee [below](#advanced-configuration).\n"
        translated = "## Configurazione avanzata\n\nVedi [sotto](#configurazione-avanzata) e [l'originale](#advanced-configuration).\n"
        issues = vt.check_link_anchors(source, translated, CACHE_KEY, LANG)
        assert _kinds(issues) == [("anchor-missing", vt.Severity.ERROR)]
        assert "#advanced-configuration" in issues[0].message and "this page" in issues[0].message, issues[0].message

    def test_heading_slugs_and_html_ids_are_the_anchors_python_markdown_renders(self, validate_translations, docs):
        vt = validate_translations
        _write(docs, "user/glossary.it.md", SLUG_PAGE)
        assert vt.check_link_anchors("", _links(*(f"glossary.md#{anchor}" for anchor in SLUG_ANCHORS)), CACHE_KEY, LANG) == []
        issues = vt.check_link_anchors("", _links(*(f"glossary.md#{anchor}" for anchor in NEAR_MISSES)), CACHE_KEY, LANG)
        assert _kinds(issues) == [("anchor-missing", vt.Severity.ERROR)] * len(NEAR_MISSES)
        assert [anchor for anchor in NEAR_MISSES if not any(f"glossary.md#{anchor})" in issue.message for issue in issues)] == []

    def test_links_it_must_not_resolve_are_ignored(self, validate_translations, tree):
        vt = validate_translations
        assert _kinds(vt.check_link_anchors("", _links("target.md#nope"), CACHE_KEY, LANG)) == [("anchor-missing", vt.Severity.ERROR)], "barrier: the page these links point at lacks #nope"
        translated = textwrap.dedent("""\
            [web](https://example.com/target.md#nope), [mail](mailto:team@example.com#nope),
            [image](target.png#nope), [page](target.html#nope).

            Inline: `[code](target.md#nope)`.

            ```markdown
            [fenced](target.md#nope)
            ```

            ~~~
            [tilde](target.md#nope)
            ~~~

            1. In a list:

                ```text
                [indented](target.md#nope)
                ```
            """)
        assert vt.check_link_anchors("", translated, CACHE_KEY, LANG) == []

    def test_the_same_broken_link_twice_is_reported_once(self, validate_translations, tree):
        vt = validate_translations
        issues = vt.check_link_anchors("", _links("target.md#nope", "target.md#nope", "target.md#also-missing"), CACHE_KEY, LANG)
        assert _kinds(issues) == [("anchor-missing", vt.Severity.ERROR)] * 2
        assert [sum(url in issue.message for issue in issues) for url in ("target.md#nope", "target.md#also-missing")] == [1, 1]


class TestLinkAnchorsReadTheRender:
    """Batch 13: a page's anchors are the ids its MkDocs render records, ``mkdocs build``'s own set."""

    @pytest.mark.parametrize(("page", "anchors", "near_misses"), RENDER_CASES)
    def test_a_target_offers_the_anchors_of_its_render_and_no_other(self, validate_translations, docs, page, anchors, near_misses):
        vt = validate_translations
        _write(docs, "user/target.it.md", page)
        assert vt.check_link_anchors("", _links(*(f"target.md#{anchor}" for anchor in anchors)), CACHE_KEY, LANG) == []
        issues = vt.check_link_anchors("", _links(*(f"target.md#{anchor}" for anchor in near_misses)), CACHE_KEY, LANG)
        assert _kinds(issues) == [("anchor-missing", vt.Severity.ERROR)] * len(near_misses)
        assert [anchor for anchor in near_misses if not any(f"target.md#{anchor})" in issue.message for issue in issues)] == []

    def test_an_in_page_link_lands_on_an_anchor_of_the_translated_pages_render(self, validate_translations):
        vt = validate_translations
        translated = textwrap.dedent("""\
            ## Configurazione avanzata {: #advanced-configuration }

            ## Bar {: #foo }

            ## Foo

            Vedi [la configurazione](#advanced-configuration) e [Foo](#foo_1), non [il titolo](#configurazione-avanzata) né [Bar](#bar).
            """)
        issues = vt.check_link_anchors("", translated, CACHE_KEY, LANG)
        assert _kinds(issues) == [("anchor-missing", vt.Severity.ERROR)] * 2
        reported = {anchor for anchor in ("configurazione-avanzata", "bar") for issue in issues if f"(link #{anchor})" in issue.message and "this page" in issue.message}
        assert reported == {"configurazione-avanzata", "bar"}, [str(issue) for issue in issues]

    def test_a_byte_order_mark_does_not_change_a_files_anchors(self, validate_translations, docs):
        vt = validate_translations
        page = "# Titolo\n\n## Sezione\n"
        _write(docs, "user/plain.it.md", page)
        bom = docs / "user" / "bom.it.md"
        bom.write_text(page, encoding="utf-8-sig")
        assert bom.read_bytes().startswith(b"\xef\xbb\xbf"), "barrier: the file starts with a UTF-8 byte-order mark"
        assert _kinds(vt.check_link_anchors("", _links("bom.md#nope"), CACHE_KEY, LANG)) == [("anchor-missing", vt.Severity.ERROR)], "barrier: the page is read"
        assert vt.check_link_anchors("", _links(*(f"{name}.md#{anchor}" for name in ("plain", "bom") for anchor in ("titolo", "sezione"))), CACHE_KEY, LANG) == []

    def test_a_byte_order_mark_does_not_change_the_translations_own_anchors(self, validate_translations):
        """validate_file reads a translation as utf-8, so its byte-order mark reaches the check; MkDocs reads pages as utf-8-sig."""
        vt = validate_translations
        assert _kinds(vt.check_link_anchors("", "\ufeff# Titolo\n\nVedi [giù](#nope).\n", CACHE_KEY, LANG)) == [("anchor-missing", vt.Severity.ERROR)], "barrier: the page's in-page links are checked"
        assert vt.check_link_anchors("", "\ufeff# Titolo\n\nVedi [su](#titolo).\n", CACHE_KEY, LANG) == []


# ---------------------------------------------------------------------------
# page_anchors: what a render offers, one render per version of a file
# ---------------------------------------------------------------------------


class TestRenderAnchors:
    @pytest.mark.parametrize(
        ("page", "anchors"),
        [
            pytest.param("# Titolo\n", {"titolo"}, id="heading-first"),
            pytest.param(FRONT_MATTER_PAGE, {"glossario", "voci"}, id="front-matter-first"),
        ],
    )
    def test_a_byte_order_mark_is_not_content(self, page_anchors, page, anchors):
        """MkDocs reads a page as utf-8-sig: a leading mark hides neither the first heading nor the front matter, which
        would then be rendered (its YAML lines turned into headings)."""
        assert page_anchors.render_anchors("\ufeff" + page) == page_anchors.render_anchors(page) == anchors


class TestFileAnchors:
    def test_each_version_of_a_file_is_rendered_once(self, page_anchors, docs, monkeypatch):
        real_render, renders = page_anchors.render_anchors, []

        def counting_render(source: str) -> frozenset[str]:
            renders.append(source)
            return real_render(source)

        monkeypatch.setattr(page_anchors, "render_anchors", counting_render)
        path = _write(docs, "user/page.it.md", "# Alfa\n")
        assert page_anchors.file_anchors(path) == {"alfa"}
        assert page_anchors.file_anchors(docs / "user" / ".." / "user" / "page.it.md") == {"alfa"}, "the same file, spelled differently"
        assert renders == ["# Alfa\n"]

    @pytest.mark.parametrize(
        ("edit", "anchor", "same_mtime"),
        [
            pytest.param("# Beta\n", "beta", False, id="same-size-later-mtime"),
            pytest.param("# Gamma\n", "gamma", True, id="other-size-same-mtime"),
        ],
    )
    def test_a_changed_file_is_rendered_again(self, page_anchors, docs, edit, anchor, same_mtime):
        """A version is the file's size and mtime: an edit saved within the same mtime tick is told by its size."""
        path = _write(docs, "user/page.it.md", "# Alfa\n")
        before = path.stat()
        assert page_anchors.file_anchors(path) == {"alfa"}
        path.write_text(edit, encoding="utf-8")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns if same_mtime else before.st_mtime_ns + 1_000_000_000))
        after = path.stat()
        assert (after.st_size == before.st_size, after.st_mtime_ns == before.st_mtime_ns) == (not same_mtime, same_mtime), "barrier: only the intended half of the version changed"
        assert page_anchors.file_anchors(path) == {anchor}


# ---------------------------------------------------------------------------
# _structural_diff: LINE_COUNT on blocks
# ---------------------------------------------------------------------------

EN_SENTENCE = "The import wizard reads the broker file, matches every row to an asset and shows what it will create before anything is saved."
IT_SENTENCE = "La procedura guidata legge il file del broker, abbina ogni riga a un titolo e mostra cosa creerà prima di salvare qualsiasi cosa."
_LINE_COUNT = re.compile(r"LINE_COUNT: source=(\d+) blocks \(\d+ lines\), translated=(\d+) blocks \(\d+ lines\) \(Δ([+-]\d+) blocks")


def _wrapped_page(paragraphs: int) -> str:
    """An EN page as the docs are written: a heading, then paragraphs wrapped at 80 columns."""
    return "# Import\n\n" + "\n\n".join(textwrap.fill(f"{EN_SENTENCE} {EN_SENTENCE}", width=80) for _ in range(paragraphs)) + "\n"


def _one_line_page(paragraphs: int) -> str:
    """A translation as the pipeline often writes it: a heading, then one line per paragraph."""
    return "# Importazione\n\n" + "\n\n".join(f"{IT_SENTENCE} {IT_SENTENCE}" for _ in range(paragraphs)) + "\n"


def _numbered(blocks: int, word: str) -> str:
    """``blocks`` one-line paragraphs, blank-line separated."""
    return "\n\n".join(f"{word} {n} of the page." for n in range(1, blocks + 1)) + "\n"


def _line_count(report: str) -> tuple[int, ...] | None:
    """(source blocks, translated blocks, delta) of the LINE_COUNT issue; None when the report has none."""
    if "LINE_COUNT" not in report:
        return None
    match = _LINE_COUNT.search(report)
    assert match, f"LINE_COUNT issue without the block counts:\n{report}"
    return tuple(int(group) for group in match.groups())


class TestStructuralDiffLineCount:
    def test_a_paragraph_kept_on_one_line_is_not_dropped_content(self, translate_docs):
        source, translated = _wrapped_page(8), _one_line_page(8)
        source_lines, translated_lines = len(source.split("\n")), len(translated.split("\n"))
        assert source_lines >= 2 * translated_lines, "barrier: the EN wraps every paragraph over several lines"
        assert abs(translated_lines - source_lines) > max(3, source_lines * 0.15), "barrier: a comparison of lines would report it"
        assert _line_count(translate_docs._structural_diff(source, translated)) is None

    def test_a_translation_missing_half_its_blocks_is_reported(self, translate_docs):
        assert _line_count(translate_docs._structural_diff(_wrapped_page(20), _one_line_page(10))) == (21, 11, -10)

    @pytest.mark.parametrize(
        ("blocks", "delta", "reported"),
        [
            pytest.param(10, -3, False, id="10-blocks-3-fewer-at-the-floor-of-3"),
            pytest.param(10, -4, True, id="10-blocks-4-fewer-beyond-the-floor"),
            pytest.param(10, +3, False, id="10-blocks-3-more-at-the-floor-of-3"),
            pytest.param(10, +4, True, id="10-blocks-4-more-beyond-the-floor"),
            pytest.param(40, -6, False, id="40-blocks-6-fewer-at-15-percent"),
            pytest.param(40, -7, True, id="40-blocks-7-fewer-beyond-15-percent"),
            pytest.param(40, +6, False, id="40-blocks-6-more-at-15-percent"),
            pytest.param(40, +7, True, id="40-blocks-7-more-beyond-15-percent"),
        ],
    )
    def test_line_count_fires_only_beyond_max_3_or_15_percent_of_the_source_blocks(self, translate_docs, blocks, delta, reported):
        report = translate_docs._structural_diff(_numbered(blocks, "Paragraph"), _numbered(blocks + delta, "Paragrafo"))
        assert _line_count(report) == ((blocks, blocks + delta, delta) if reported else None)


# ---------------------------------------------------------------------------
# validate_file: one EN/IT pair end to end
# ---------------------------------------------------------------------------

GUIDE_EN = textwrap.dedent("""\
    # Guide

    Set `total_return` and `period` before you start, and quote pairs as `EUR<USD`.

    See [the configuration](other.md#configuration) and [the details](other.md#details).

    <img class="shot" src="../static/guide.png" alt="The import wizard on its first step">

    ![Portfolio value over the last year](../static/value.png)
    """)
# Three defects: a translated identifier, an alt text left in English, a link to an anchor the IT target lacks.
GUIDE_IT = textwrap.dedent("""\
    # Guida

    Imposta `rendimento_totale` e `period` prima di iniziare, e quota le coppie come `EUR<USD`.

    Vedi [la configurazione](other.md#configuration) e [i dettagli](other.md#details).

    <img class="shot" src="../static/guide.png" alt="The import wizard on its first step">

    ![Valore del portafoglio nell'ultimo anno](../static/value.png)
    """)
GUIDE_IT_FIXED = GUIDE_IT.replace("`rendimento_totale`", "`total_return`").replace('alt="The import wizard on its first step"', 'alt="La procedura di importazione al primo passo"')
OTHER_EN = "# Other\n\n## Configuration\n\n## Details\n"
OTHER_IT = "# Altro\n\n## Configurazione {: #configuration }\n\n## Dettagli\n"
OTHER_IT_FIXED = OTHER_IT.replace("## Dettagli", "## Dettagli {: #details }")
CHECKS_UNDER_TEST = frozenset({"anchor-missing", "inline-code-missing", "text-untranslated", "html-tag-mismatch", "html-attr-missing", "html-attr-mismatch"})


def _validate(vt, docs: Path, guide_it: str, other_it: str) -> list:
    """validate_file on user/guide (EN, IT), the IT linking user/other (EN, IT); only the issues of the checks under test."""
    source = _write(docs, "user/guide.en.md", GUIDE_EN)
    translation = _write(docs, "user/guide.it.md", guide_it)
    _write(docs, "user/other.en.md", OTHER_EN)
    _write(docs, "user/other.it.md", other_it)
    return [issue for issue in vt.validate_file(source, translation, CACHE_KEY, LANG) if issue.check in CHECKS_UNDER_TEST]


class TestValidateFile:
    def test_a_translated_page_gets_the_new_checks(self, validate_translations, docs):
        vt = validate_translations
        issues = _validate(vt, docs, GUIDE_IT, OTHER_IT)
        assert sorted(_kinds(issues)) == sorted([("anchor-missing", vt.Severity.ERROR), ("inline-code-missing", vt.Severity.WARN), ("text-untranslated", vt.Severity.WARN)]), [str(issue) for issue in issues]
        assert {(issue.file, issue.lang) for issue in issues} == {(CACHE_KEY, LANG)}
        by_check = {issue.check: issue.message for issue in issues}
        assert "user/other.it.md" in by_check["anchor-missing"] and "other.md#details" in by_check["anchor-missing"]
        assert "`total_return`" in by_check["inline-code-missing"]
        assert "The import wizard on its first step" in by_check["text-untranslated"]

    def test_the_fixed_page_passes_them(self, validate_translations, docs):
        assert GUIDE_IT_FIXED != GUIDE_IT and OTHER_IT_FIXED != OTHER_IT, "barrier: the fixes apply"
        assert [str(issue) for issue in _validate(validate_translations, docs, GUIDE_IT_FIXED, OTHER_IT_FIXED)] == []

    def test_a_raw_html_path_copied_from_the_english_fails_the_validation(self, validate_translations, docs):
        """html-asset-depth is in ALL_CHECKS: the copy is an error of the page. HEAD's validator reported none."""
        vt = validate_translations
        source = _write(docs, "user/guide.en.md", f"# Guide\n\n{EN_IMG}\n")
        translation = _write(docs, "user/guide.it.md", f"# Guida\n\n{IT_IMG_COPIED}\n")
        issues = vt.validate_file(source, translation, CACHE_KEY, LANG)
        errors = [(issue.check, issue.severity) for issue in issues if issue.severity == vt.Severity.ERROR and "../../static/a.png" in issue.message]
        assert errors == [("html-asset-depth", vt.Severity.ERROR)], [str(issue) for issue in issues]


# ---------------------------------------------------------------------------
# Fixture self-check
# ---------------------------------------------------------------------------


def _bare_ids(text: str) -> set[str]:
    """The ids bare Python-Markdown gives a page, toc and attr_list only: the site's render without its other extensions."""
    html = markdown.Markdown(extensions=["toc", "attr_list"]).convert(text)
    return set(re.findall(r'\bid="([^"]+)"', html))


class TestFixtures:
    """Not a product contract: an expected anchor the build would not give, or a near miss it would, would let the
    anchor tests pass for the wrong reason. The oracle is ``page_anchors.render_anchors``, which gave the ids a real
    ``mkdocs build`` records on all 946 pages (R2 B13 parity probe, 13,992 ids).
    It does not involve the validator: against HEAD's, these stay green while the anchor tests turn red."""

    @pytest.mark.parametrize(("page", "anchors", "near_misses"), [pytest.param(SLUG_PAGE, SLUG_ANCHORS, NEAR_MISSES, id="glossary"), *RENDER_CASES])
    def test_the_expected_anchors_are_the_ones_the_site_renders(self, page_anchors, page, anchors, near_misses):
        rendered = page_anchors.render_anchors(page)
        assert rendered == set(anchors)
        assert rendered.isdisjoint(near_misses)

    def test_the_emoji_case_needs_the_sites_extensions(self):
        """Only the site's render gives ``buy-me-a-coffee`` (above): without pymdownx.emoji the shortcode is text, and
        its slug is the near miss. A validator rendering without the site's configuration fails the emoji case."""
        assert _bare_ids(EMOJI_PAGE) == {"supporto", "coffee-buy-me-a-coffee"}


# ---------------------------------------------------------------------------
# The CHANGELOG (R2 B25): released chapters, translate-validate, translate-diff
# ---------------------------------------------------------------------------
# Newest chapter first: [3.1.0] is open, longer than CL_THRESHOLD and so cut into four pieces; the preamble, [3.0.1] and
# [3.0.0] are one piece each. The fake translation tags each prose line with its language and keeps every heading,
# chapter line, rule and link: it passes every page check (TestValidateChangelog's first test proves it).

CL_LANGS = ("it", "fr", "es")
CL_THRESHOLD = 300  # changelog.PIECE_THRESHOLD in these tests, instead of writing 30,000 characters
CL_RULE = "---"
CL_ROADMAP = "[roadmap](https://example.org/roadmap)"
CL_GUIDE = "[import guide](https://example.org/import)"
CL_OPEN_BULLET = "- A Tools catalogue with isolated computations and read-only diagnostics."
CL_PATCH_BULLET = "- Exchange rates older than a week are fetched again on the next sync."
CL_PREAMBLE = "# Changelog\n\nAll notable changes to LibreFolio are documented in this file."
CL_OPEN = "\n\n".join(
    (
        "## [3.1.0] - 2026-11-30",
        f"**Preparing v3.1.0.** These changes are in preparation and not released yet: see the {CL_ROADMAP}.",
        f"### ✨ Added\n\n- A support popup in the About page, with links to the project pages.\n{CL_OPEN_BULLET}",
        "### 🐛 Fixed",
        "#### 🔒 Security\n\n- Session cookies are rotated after every password change.",
        "#### 📚 Documentation\n\n- The installation guide describes the Docker volumes again.",
    )
)
CL_PATCH = "\n\n".join(("## [3.0.1] - 2026-07-21", "### 🐛 Fixed", f"- The import wizard keeps the broker selected after a page reload, as the {CL_GUIDE} says.\n{CL_PATCH_BULLET}"))
CL_FIRST = "\n\n".join(("## [3.0.0] - 2026-07-20", "First public release.", "### ✨ Added", "- Portfolio dashboard, broker report imports and exchange rates."))
CL_NEXT = "## [3.2.0] - 2027-01-15"  # a chapter just opened: nothing in it yet
CL_INVENTED = "## [2.9.9] - 2026-01-01\n\nA chapter the English does not have."
CL_EARLIER = "2020-01-01T00:00:00+00:00"
# translate-diff's marks: ❌ counted missing, ⚠️ counted anomalies, ℹ️ information only (the open chapter)
MISSING_MARK, ANOMALY_MARK, INFO_MARK = "\u274c", "\u26a0\ufe0f", "\u2139\ufe0f"
OPEN_MISSING_NOTE = "not translated yet: open chapter, information only"


def _cl_text(*blocks: str) -> str:
    """A CHANGELOG as the repository writes it: the preamble, then the chapters newest first, a rule between two units."""
    return f"\n\n{CL_RULE}\n\n".join(blocks) + "\n"


def _cl_translated(english: str, lang: str) -> str:
    """The fake translation of a CHANGELOG: each prose line tagged with the language; every heading (the chapter lines
    with them), rule, link and blank line as in the English."""
    return "\n".join(line if not line or line.startswith("#") or line == CL_RULE else f"{line} ({lang})" for line in english.split("\n"))


CL_EN = _cl_text(CL_PREAMBLE, CL_OPEN, CL_PATCH, CL_FIRST)


def _findings(vt: ModuleType, issues) -> dict[str, list[tuple[str, str]]]:
    """(check, severity name) of each issue, by the unit it is about: ``CHANGELOG.md#<name>``, or ``CHANGELOG.md``."""
    names = {getattr(vt.Severity, name): name for name in ("ERROR", "WARN", "INFO", "LOCALIZED")}
    found: dict[str, list[tuple[str, str]]] = {}
    for issue in issues:
        found.setdefault(issue.file, []).append((issue.check, names[issue.severity]))
    return {unit: sorted(kinds) for unit, kinds in found.items()}


# translate-validate prints each issue as "<mark> <SEVERITY> [<check>] <file>[:<line>] (<lang>): <message>".
_PRINTED_ISSUE = re.compile(r"(?P<severity>ERROR|WARN|INFO|LOCALIZED) \[(?P<check>[^\]]+)\] (?P<file>\S+?)(?::\d+)? \((?P<lang>[a-z]+)\): ")
_FILES_CHECKED = re.compile(r"Files checked:\s+(?P<n>\d+)")
# translate-diff prints a chapter as "  <mark>  CHANGELOG.md#<name> → <lang>  (<note>)", the note absent when clean.
_DIFF_CHAPTER = re.compile(r"^  (?P<mark>\S+)\s+CHANGELOG\.md#(?P<unit>\S+) → (?P<lang>[a-z]+)(?:  \((?P<note>.*)\))?$", re.MULTILINE)
_DIFF_MISSING = re.compile(r"Missing translations: (?P<n>\d+)")
_DIFF_WITH_ISSUES = re.compile(r"With issues: (?P<n>\d+)")


def _printed_issues(out: str) -> set[tuple[str, str, str, str]]:
    """(severity, check, file, lang) of each issue translate-validate printed."""
    return {(m["severity"], m["check"], m["file"], m["lang"]) for m in _PRINTED_ISSUE.finditer(out)}


def _diff_report(out: str) -> dict:
    """What translate-diff printed about the CHANGELOG: each chapter's mark and note by (chapter, lang), and its counts."""
    missing, with_issues = _DIFF_MISSING.search(out), _DIFF_WITH_ISSUES.search(out)
    return {
        "chapters": {(m["unit"], m["lang"]): (m["mark"], m["note"]) for m in _DIFF_CHAPTER.finditer(out)},
        "missing": int(missing["n"]) if missing else 0,
        "with issues": int(with_issues["n"]) if with_issues else 0,
    }


@dataclasses.dataclass
class ChangelogTree:
    """``CHANGELOG.md`` under ``tmp_path``, its translations beside it and the cache, where both commands read them."""

    vt: ModuleType
    td: ModuleType
    cl: ModuleType
    source: Path
    hash_file: Path
    capsys: pytest.CaptureFixture
    real_tag_exists: Callable[[str, Path], bool]
    tagged: set[str] = dataclasses.field(default_factory=set)  # the versions whose tag the stub says exists
    asked: list[tuple[str, Path]] = dataclasses.field(default_factory=list)  # the lookups the stub answered

    def write(self, text: str, lang: str = "en") -> None:
        path = self.source if lang == "en" else self.source.with_name(f"CHANGELOG.{lang}.md")
        path.write_bytes(text.encode("utf-8"))

    def read(self, lang: str) -> str:
        return self.source.with_name(f"CHANGELOG.{lang}.md").read_bytes().decode("utf-8")

    def translate_all(self, english: str = CL_EN) -> None:
        """Every language's fake translation of ``english``, which may lack chapters of the current English."""
        for lang in CL_LANGS:
            self.write(_cl_translated(english, lang), lang)

    def units(self) -> list:
        return self.cl.read_english(self.source)

    def released(self) -> set[str]:
        return self.cl.released(self.units(), self.source)

    def done(self, english: str = CL_EN) -> dict:
        """The cache as runs that translated ``english`` into every language left it: each piece done, at its position."""
        return {
            piece.key: {
                "md5": hashlib.md5(piece.text.encode("utf-8")).hexdigest(),
                "langs_done": list(CL_LANGS),
                "last_translated": CL_EARLIER,
                "langs": {lang: {"translated_at": CL_EARLIER, "index": index} for lang in CL_LANGS},
            }
            for unit in self.cl.english(english)
            for index, piece in enumerate(unit.pieces)
        }

    def save_cache(self, hashes: dict) -> None:
        self.hash_file.write_text(json.dumps(hashes, indent=2), encoding="utf-8")

    def validate(self, lang: str, hashes: dict) -> list:
        """``validate_changelog`` for ``lang``, with the current English and the release policy."""
        units = self.units()
        return self.vt.validate_changelog(lang, units, self.cl.released(units, self.source), hashes, self.source)

    def run_validate(self, *argv: str) -> tuple[int, str]:
        """``translate-validate ARGV``, registered and parsed as dev.py does."""
        parser = argparse.ArgumentParser()
        self.vt.register_subparser(parser.add_subparsers(dest="command"))
        args = parser.parse_args(["translate-validate", *argv])
        self.capsys.readouterr()
        rc = args.func(args)
        return rc, self.capsys.readouterr().out

    def run_diff(self, *argv: str) -> tuple[int, str]:
        """``translate-diff ARGV``, parsed by the real parser."""
        parser = argparse.ArgumentParser()
        self.td._add_diff_arguments(parser)
        args = parser.parse_args(list(argv))
        self.capsys.readouterr()
        rc = self.td.run_diff(args)
        return rc, self.capsys.readouterr().out


@pytest.fixture
def changelog_tree(validate_translations, translate_docs, docs, tmp_path, monkeypatch, capsys) -> ChangelogTree:
    """``CL_EN`` under ``tmp_path``, translated into no language yet, an empty cache, no tag: what both commands read,
    and no tag lookup but the stub's."""
    vt, td = validate_translations, translate_docs
    cl = vt.cl
    assert cl is td.cl, "barrier: validate_translations and translate_docs share one changelog module"
    root = tmp_path.resolve()
    tree = ChangelogTree(vt, td, cl, root / "CHANGELOG.md", root / ".translate-hashes.json", capsys, cl._tag_exists)

    def tag_exists(version: str, repo: Path) -> bool:
        tree.asked.append((version, repo))
        return version in tree.tagged

    monkeypatch.setattr(cl, "PIECE_THRESHOLD", CL_THRESHOLD)
    monkeypatch.setattr(cl, "SOURCE", root / "not-the-repository" / "CHANGELOG.md")  # changelog.py's default, for a call that forgets its source
    monkeypatch.setattr(cl, "_tag_exists", tag_exists)
    monkeypatch.setattr(td, "HASH_FILE", tree.hash_file)  # read by translate_docs._load_hashes, which validate_translations imported
    monkeypatch.setattr(td, "DOCS_DIR", docs)
    for module in (vt, td):
        monkeypatch.setattr(module, "_changelog_source", lambda: tree.source)
        monkeypatch.setattr(module, "_detect_target_languages", lambda: list(CL_LANGS))
        monkeypatch.setattr(module, "get_translatable_files", lambda: [])
    tree.write(CL_EN)
    assert vt._load_hashes() == {}, "barrier: the validator reads the cache under tmp_path, not the repository's"
    assert [unit.name for unit in tree.units() if unit.split] == ["3.1.0"], "barrier: the threshold cuts the open chapter alone"
    return tree


def _hermetic_git(monkeypatch, tree: ChangelogTree) -> None:
    """Git as the real tag lookup will see it, kept to ``tmp_path``: no repository above it, no user or system
    configuration, no CI ref."""
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GITHUB_REF"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tree.source.parent.parent))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setattr(tree.cl, "_tag_exists", tree.real_tag_exists)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """``git ARGS`` in ``repo``, a throwaway repository under ``tmp_path``: a local identity, no signing, no hooks."""
    config = ("user.name=LibreFolio tests", "user.email=tests@example.org", "commit.gpgsign=false", "tag.gpgsign=false", f"core.hooksPath={os.devnull}")
    return subprocess.run(["git", "-C", str(repo), *(arg for item in config for arg in ("-c", item)), *args], capture_output=True, text=True, check=True)


class TestChangelogReleasePolicy:
    def test_every_chapter_but_the_newest_is_released(self, changelog_tree):
        tree = changelog_tree
        assert tree.released() == {"preamble", "3.0.1", "3.0.0"}
        assert tree.asked == [("3.1.0", tree.source.parent)], "the tag looked for is the newest chapter's, in the CHANGELOG's repository"

    def test_the_newest_chapter_is_released_once_its_tag_exists(self, changelog_tree):
        tree = changelog_tree
        tree.tagged.add("3.1.0")
        assert tree.released() == {"preamble", "3.1.0", "3.0.1", "3.0.0"}

    @pytest.mark.parametrize(
        ("ref", "released"),
        [
            pytest.param("refs/tags/v3.1.0", True, id="the-newest-chapters-tag"),
            pytest.param("refs/tags/3.1.0", True, id="the-newest-chapters-tag-without-v"),
            pytest.param("refs/tags/v3.1.0-rc.1", False, id="a-release-candidates-tag"),
            pytest.param("refs/tags/v3.0.1", False, id="an-older-chapters-tag"),
            pytest.param("refs/heads/dev", False, id="a-branch"),
            pytest.param(None, False, id="no-ci-ref"),
        ],
    )
    def test_the_ref_of_the_ci_run_releases_the_newest_chapter(self, changelog_tree, monkeypatch, ref, released):
        """The real lookup. The CHANGELOG under ``tmp_path`` is in no repository (git may not climb above it), so only
        ``GITHUB_REF`` can release the newest chapter: its own tag, with or without the ``v`` the release workflow's tag
        guard allows, never a release candidate's, an older chapter's or a branch."""
        tree = changelog_tree
        _hermetic_git(monkeypatch, tree)
        if ref is not None:
            monkeypatch.setenv("GITHUB_REF", ref)
        assert tree.released() == {"preamble", "3.0.1", "3.0.0"} | ({"3.1.0"} if released else set())

    @pytest.mark.parametrize(
        ("tag", "released"),
        [
            pytest.param("v3.1.0", True, id="the-newest-chapters-tag"),
            pytest.param("3.1.0", True, id="the-newest-chapters-tag-without-v"),
            pytest.param("v3.1.0-rc.1", False, id="a-release-candidates-tag"),
            pytest.param("v3.0.1", False, id="an-older-chapters-tag"),
        ],
    )
    def test_a_tag_in_the_changelogs_repository_releases_the_newest_chapter(self, changelog_tree, monkeypatch, tag, released):
        """The real lookup in a real repository: a throwaway one, created in ``tmp_path`` around the CHANGELOG (never the
        project's), holding one empty commit and the tag under test; no CI ref."""
        tree = changelog_tree
        _hermetic_git(monkeypatch, tree)
        repo = tree.source.parent
        _git(repo, "init", "-q")
        assert Path(_git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve() == repo.resolve(), "barrier: the commands below reach the throwaway repository"
        _git(repo, "commit", "-q", "--allow-empty", "-m", "A throwaway commit to tag")
        _git(repo, "tag", tag)
        assert tree.released() == {"preamble", "3.0.1", "3.0.0"} | ({"3.1.0"} if released else set())


class TestValidateChangelog:
    def test_a_complete_translation_done_for_the_current_english_has_no_finding(self, changelog_tree):
        """The fake translation passes every page check and the cache knows it done: what the other tests find, their
        edits cause."""
        tree = changelog_tree
        tree.translate_all()
        hashes = tree.done()
        assert {lang: [str(issue) for issue in tree.validate(lang, hashes)] for lang in CL_LANGS} == {lang: [] for lang in CL_LANGS}

    @pytest.mark.parametrize(
        ("chapters", "tagged", "expected"),
        [
            pytest.param(None, False, {"preamble": "ERROR", "3.1.0": "INFO", "3.0.1": "ERROR", "3.0.0": "ERROR"}, id="no-translated-file"),
            pytest.param(None, True, {"preamble": "ERROR", "3.1.0": "ERROR", "3.0.1": "ERROR", "3.0.0": "ERROR"}, id="no-translated-file-newest-tagged"),
            pytest.param((CL_PREAMBLE, CL_FIRST), False, {"3.1.0": "INFO", "3.0.1": "ERROR"}, id="two-chapters-missing"),
            pytest.param((CL_PREAMBLE, CL_FIRST), True, {"3.1.0": "ERROR", "3.0.1": "ERROR"}, id="two-chapters-missing-newest-tagged"),
        ],
    )
    def test_a_missing_translation_is_an_error_when_released_and_information_when_open(self, changelog_tree, chapters, tagged, expected):
        tree = changelog_tree
        if chapters is not None:
            tree.write(_cl_translated(_cl_text(*chapters), LANG), LANG)
        if tagged:
            tree.tagged.add("3.1.0")
        issues = tree.validate(LANG, tree.done())
        assert _findings(tree.vt, issues) == {f"CHANGELOG.md#{name}": [("changelog-missing", severity)] for name, severity in expected.items()}
        assert [issue.message for issue in issues if issue.severity == tree.vt.Severity.INFO and not issue.message.endswith(" (open chapter)")] == []

    @pytest.mark.parametrize(
        ("chapter", "tagged", "severity"),
        [
            pytest.param("3.0.1", False, "ERROR", id="released"),
            pytest.param("3.1.0", False, "INFO", id="open"),
            pytest.param("3.1.0", True, "ERROR", id="newest-tagged"),
        ],
    )
    def test_a_chapter_line_unlike_the_english_one_is_an_error_when_released_and_information_when_open(self, changelog_tree, chapter, tagged, severity):
        """The app finds a chapter by its line: a translated date (``21/07/2026``) loses the chapter."""
        tree = changelog_tree
        line = next(line for line in CL_EN.split("\n") if line.startswith(f"## [{chapter}] - "))
        year, month, day = line.rsplit(" - ", 1)[1].split("-")
        tree.translate_all()
        text = tree.read(LANG)
        assert text.count(line) == 1, "barrier: the translation opens the chapter with the English line"
        tree.write(text.replace(line, f"## [{chapter}] - {day}/{month}/{year}"), LANG)
        if tagged:
            tree.tagged.add("3.1.0")
        assert _findings(tree.vt, tree.validate(LANG, tree.done())) == {f"CHANGELOG.md#{chapter}": [("changelog-chapter", severity)]}

    @pytest.mark.parametrize(
        ("chapters", "expected"),
        [
            pytest.param((CL_PREAMBLE, CL_OPEN, CL_PATCH, CL_INVENTED, CL_FIRST), {"CHANGELOG.md#2.9.9": [("changelog-chapter", "ERROR")]}, id="a-chapter-the-english-lacks"),
            pytest.param((CL_PREAMBLE, CL_OPEN, CL_FIRST, CL_PATCH), {"CHANGELOG.md": [("changelog-chapter", "ERROR")]}, id="two-released-chapters-swapped"),
            pytest.param((CL_PREAMBLE, CL_PATCH, CL_FIRST, CL_OPEN), {"CHANGELOG.md": [("changelog-chapter", "ERROR")]}, id="the-open-chapter-moved-last"),
            pytest.param((CL_PREAMBLE, CL_OPEN, CL_PATCH, CL_FIRST, CL_FIRST), {"CHANGELOG.md#3.0.0": [("changelog-chapter", "ERROR")]}, id="a-chapter-written-twice"),
        ],
    )
    def test_an_unknown_chapter_the_wrong_order_and_a_repeated_chapter_are_errors(self, changelog_tree, chapters, expected):
        """Whatever the release: the app lists the chapters it finds, in the file's order."""
        tree = changelog_tree
        tree.write(_cl_translated(_cl_text(*chapters), LANG), LANG)
        assert _findings(tree.vt, tree.validate(LANG, tree.done())) == expected

    @pytest.mark.parametrize(
        ("old", "new", "tagged", "chapter", "pieces", "severity"),
        [
            pytest.param("after a page reload", "after a browser reload", False, "3.0.1", "3.0.1", "ERROR", id="released"),
            pytest.param("the Docker volumes", "the Docker volumes and networks", False, "3.1.0", "3.1.0/fixed/documentation", "INFO", id="open"),
            pytest.param("the Docker volumes", "the Docker volumes and networks", True, "3.1.0", "3.1.0/fixed/documentation", "ERROR", id="newest-tagged"),
        ],
    )
    def test_a_chapter_changed_since_its_translation_is_stale(self, changelog_tree, old, new, tagged, chapter, pieces, severity):
        """The English is edited after the translation; the cache still records the pieces done for the old text."""
        tree = changelog_tree
        tree.translate_all()
        hashes = tree.done()
        assert CL_EN.count(old) == 1, "barrier: the edit touches one piece"
        tree.write(CL_EN.replace(old, new))
        if tagged:
            tree.tagged.add("3.1.0")
        issues = tree.validate(LANG, hashes)
        assert _findings(tree.vt, issues) == {f"CHANGELOG.md#{chapter}": [("changelog-stale", severity)]}
        assert [issue.message for issue in issues] == [f"1 piece(s) changed since their translation: {pieces}" + (" (open chapter)" if severity == "INFO" else "")]

    @pytest.mark.parametrize(
        ("link", "chapter", "tagged", "severities"),
        [
            pytest.param(CL_GUIDE, "3.0.1", False, ("WARN", "ERROR"), id="released"),
            pytest.param(CL_ROADMAP, "3.1.0", False, ("INFO", "INFO"), id="open"),
            pytest.param(CL_ROADMAP, "3.1.0", True, ("WARN", "ERROR"), id="newest-tagged"),
        ],
    )
    def test_each_chapter_goes_through_the_page_checks(self, changelog_tree, link, chapter, tagged, severities):
        """A translated chapter that drops a link: the page checks report it, weighed by the release."""
        tree = changelog_tree
        tree.translate_all()
        text = tree.read(LANG)
        assert text.count(link) == 1, "barrier: the translation keeps the link once"
        tree.write(text.replace(link, link[1:].split("]")[0]), LANG)
        if tagged:
            tree.tagged.add("3.1.0")
        assert _findings(tree.vt, tree.validate(LANG, tree.done())) == {f"CHANGELOG.md#{chapter}": [("link-count", severities[0]), ("link-missing", severities[1])]}


class TestRunValidateChangelog:
    @pytest.mark.parametrize(
        ("argv", "rc", "checked", "page_reported"),
        [
            pytest.param(("--file", "CHANGELOG.md"), 0, 3, False, id="file-changelog-alone"),
            pytest.param((), 1, 4, True, id="no-file-the-pages-and-the-changelog"),
        ],
    )
    def test_the_changelog_is_validated_with_its_file_or_with_every_page(self, changelog_tree, docs, monkeypatch, argv, rc, checked, page_reported):
        """A page whose Italian drops a link (an error) and a CHANGELOG whose open chapter is not translated yet
        (information, in each language). ``--file CHANGELOG.md`` checks the three CHANGELOG translations and no page."""
        tree = changelog_tree
        _write(docs, CACHE_KEY, "# Guide\n\nSee the [manual](https://example.org/manual) first.\n")
        _write(docs, "user/guide.it.md", "# Guida\n\nLeggi prima il manuale.\n")
        monkeypatch.setattr(tree.vt, "get_translatable_files", lambda: [CACHE_KEY])
        tree.translate_all(_cl_text(CL_PREAMBLE, CL_PATCH, CL_FIRST))
        tree.save_cache(tree.done())
        result, out = tree.run_validate(*argv)
        printed = _printed_issues(out)
        assert (result, int(_FILES_CHECKED.search(out)["n"])) == (rc, checked)
        assert {issue for issue in printed if issue[2].startswith("CHANGELOG.md")} == {("INFO", "changelog-missing", "CHANGELOG.md#3.1.0", lang) for lang in CL_LANGS}
        assert any(issue[2] == CACHE_KEY for issue in printed) is page_reported

    @pytest.mark.parametrize(
        ("chapters", "tagged", "rc"),
        [
            pytest.param((CL_PREAMBLE, CL_PATCH, CL_FIRST), False, 0, id="open-chapter-missing-exit-0"),
            pytest.param((CL_PREAMBLE, CL_PATCH, CL_FIRST), True, 1, id="newest-chapter-tagged-and-missing-exit-1"),
            pytest.param((CL_PREAMBLE, CL_OPEN, CL_FIRST), False, 1, id="released-chapter-missing-exit-1"),
        ],
    )
    def test_the_exit_code_counts_the_released_chapters_alone(self, changelog_tree, chapters, tagged, rc):
        """What CI reads: the open chapter's findings never fail the step, until its tag exists."""
        tree = changelog_tree
        tree.translate_all(_cl_text(*chapters))
        tree.save_cache(tree.done())
        if tagged:
            tree.tagged.add("3.1.0")
        assert tree.run_validate("--file", "CHANGELOG.md")[0] == rc


def _without_the_open_chapter(text: str, lang: str) -> str:
    return _cl_translated(_cl_text(CL_PREAMBLE, CL_PATCH, CL_FIRST), lang)


def _italian_without_3_0_1(text: str, lang: str) -> str:
    return _cl_translated(_cl_text(CL_PREAMBLE, CL_OPEN, CL_FIRST), lang) if lang == LANG else text


def _italian_drops(bullet: str) -> Callable[[str, str], str]:
    """The Italian translation loses ``bullet``: one structural anomaly (a list item fewer) in its chapter."""
    return lambda text, lang: text.replace(f"\n{bullet} ({lang})", "", 1) if lang == LANG else text


class TestTranslateDiffChangelog:
    @pytest.mark.parametrize(
        ("edit", "tagged", "chapters", "rc", "missing", "with_issues"),
        [
            pytest.param(_without_the_open_chapter, False, {("3.1.0", lang): (INFO_MARK, OPEN_MISSING_NOTE) for lang in CL_LANGS}, 0, 0, 0, id="open-chapter-missing"),
            pytest.param(_without_the_open_chapter, True, {("3.1.0", lang): (MISSING_MARK, "missing translation") for lang in CL_LANGS}, 1, 3, 0, id="open-chapter-missing-newest-tagged"),
            pytest.param(_italian_without_3_0_1, False, {("3.0.1", LANG): (MISSING_MARK, "missing translation")}, 1, 1, 0, id="released-chapter-missing"),
            pytest.param(_italian_drops(CL_PATCH_BULLET), False, {("3.0.1", LANG): (ANOMALY_MARK, "1 issue")}, 1, 0, 1, id="released-chapter-anomaly"),
            pytest.param(_italian_drops(CL_OPEN_BULLET), False, {("3.1.0", LANG): (INFO_MARK, "1 issue: open chapter, information only")}, 0, 0, 0, id="open-chapter-anomaly"),
            pytest.param(_italian_drops(CL_OPEN_BULLET), True, {("3.1.0", LANG): (ANOMALY_MARK, "1 issue")}, 1, 0, 1, id="open-chapter-anomaly-newest-tagged"),
        ],
    )
    def test_the_released_chapters_count_and_the_open_one_is_only_printed(self, changelog_tree, edit, tagged, chapters, rc, missing, with_issues):
        """``translate-diff --issues-only`` (as CI runs it): a released chapter's absence or anomaly counts and fails the
        command; the open chapter's are printed as information, until its tag exists."""
        tree = changelog_tree
        for lang in CL_LANGS:
            tree.write(edit(_cl_translated(CL_EN, lang), lang), lang)
        if tagged:
            tree.tagged.add("3.1.0")
        result, out = tree.run_diff("--issues-only", "--file", "CHANGELOG.md")
        assert (result, _diff_report(out)) == (rc, {"chapters": chapters, "missing": missing, "with issues": with_issues})

    @pytest.mark.parametrize("argv", [pytest.param((), id="no-file"), pytest.param(("--file", "CHANGELOG.md"), id="file-changelog")])
    def test_translate_diff_takes_the_changelog_with_no_file_and_with_file_changelog(self, changelog_tree, argv):
        tree = changelog_tree
        for lang in CL_LANGS:
            tree.write(_italian_without_3_0_1(_cl_translated(CL_EN, lang), lang), lang)
        result, out = tree.run_diff("--issues-only", *argv)
        assert (result, _diff_report(out)["chapters"]) == (1, {("3.0.1", LANG): (MISSING_MARK, "missing translation")})

    def test_an_empty_newest_chapter_leaves_the_chapter_below_it_released(self, changelog_tree):
        """[3.2.0] was just opened, with nothing in it yet, and [3.1.0] below it is not translated. The newest chapter is
        [3.2.0], so [3.1.0] is released and its absence counts: for translate-diff as for translate-validate."""
        tree = changelog_tree
        english = _cl_text(CL_PREAMBLE, CL_NEXT, CL_OPEN, CL_PATCH, CL_FIRST)
        tree.write(english)
        tree.translate_all(_cl_text(CL_PREAMBLE, CL_PATCH, CL_FIRST))
        tree.save_cache(tree.done(english))
        assert "3.1.0" in tree.released(), "barrier: below the newest chapter, [3.1.0] is released"
        assert tree.run_validate("--file", "CHANGELOG.md")[0] == 1, "barrier: translate-validate counts [3.1.0] missing"
        result, out = tree.run_diff("--issues-only", "--file", "CHANGELOG.md")
        assert (result, _diff_report(out)) == (1, {"chapters": {("3.1.0", lang): (MISSING_MARK, "missing translation") for lang in CL_LANGS}, "missing": 3, "with issues": 0})
