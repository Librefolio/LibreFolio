"""translate-validate reads what a page renders: the checks of R2 batches 11-12 (M, R2 B13).

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
  when it exists (mkdocs-static-i18n falls back to EN), with the slugs Python-Markdown's toc gives;
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

PURE: strings in memory and docs trees under ``tmp_path``. An autouse fixture points
``validate_translations.DOCS_DIR`` at an empty tree under ``tmp_path`` in every test, so no check resolves a link
against ``mkdocs_src/docs``; the repository's docs and ``.translate-hashes.json`` are never opened (the Aphra pipeline
may be rewriting them while this runs). Python-Markdown, installed with MkDocs, renders the slug fixture once to prove
its expected anchors are the ones a build gives. No DB, no server, no network, no writes outside ``tmp_path``.
"""

import importlib
import re
import textwrap
from pathlib import Path
from types import ModuleType

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
        """Check and severity only: how the message spells a number without its separators is not pinned here."""
        vt = validate_translations
        issues = vt.check_inline_code("A fee of `1,000.50` EUR.\n", "Una commissione di `1.500,00` EUR.\n", CACHE_KEY, LANG)
        assert _kinds(issues) == [("inline-code-missing", vt.Severity.WARN)]

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

# A translated glossary: the anchors Python-Markdown's toc renders (TestFixtures proves it) and near misses it does not.
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


# ---------------------------------------------------------------------------
# Fixture self-check
# ---------------------------------------------------------------------------


def _rendered_ids(text: str) -> set[str]:
    """The ids Python-Markdown gives the page with the site's toc, attr_list and md_in_html (fenced_code for the fence)."""
    html = markdown.Markdown(extensions=["toc", "attr_list", "md_in_html", "fenced_code"]).convert(text)
    return set(re.findall(r'\bid="([^"]+)"', html))


class TestFixtures:
    def test_the_expected_anchors_are_the_ones_python_markdown_renders(self):
        """Not a product contract: an expected anchor the build would not give, or a near miss it would, would let the anchor tests pass for the wrong reason."""
        rendered = _rendered_ids(SLUG_PAGE)
        assert rendered == set(SLUG_ANCHORS)
        assert rendered.isdisjoint(NEAR_MISSES)
