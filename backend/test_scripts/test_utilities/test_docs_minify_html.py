"""minify_html: the pages of the built site lose Material's indentation and blank lines, and nothing else (lane 84-C).

Material's templates write a third of every HTML file as indentation and blank lines (387 MB of HTML, 242 MB without them).
``mkdocs_src/hooks/minify_html.py`` rewrites the built pages so that a run of whitespace that holds a newline becomes one
newline. This file pins what that must never change:

* ``minify(page)``: the same page for the browser. Whitespace is kept as content inside ``<pre>``, ``<code>``, ``<kbd>``,
  ``<textarea>``, ``<script>`` and ``<style>`` (Material sets ``white-space: pre-wrap`` on the first three), and inside a tag,
  attribute values included, a ``>`` in a quoted value not ending the tag; between two inline elements a separator is left,
  so they never touch. It is idempotent;
* on a page shaped like Material's: the DOM before and after is the same tree, the same text outside the protected elements
  once whitespace is collapsed as a browser collapses it, the protected text byte for byte;
* ``minify_site(dir)``: every ``*.html`` under it, in place, the other files untouched, a file that is not UTF-8 left alone,
  the sizes it reports true;
* ``on_post_build(config)``: acts for ``build`` and ``gh-deploy``, not for ``serve``, and not inside the nested build the
  i18n plugin runs per language (the site is whole only at the end);
* the real site built in ``mkdocs_src/site/`` (when there is one): a sample of its pages, from every language and every
  section, is the same DOM after ``minify`` and keeps no indented line in its text (true of a site built before and after the hook ran);
* the registration: ``mkdocs.yml`` lists the hook under ``hooks:``.

PURE: strings and files under ``tmp_path``, the hook loaded by path. Reads ``mkdocs_src/mkdocs.yml`` and, when it exists,
``mkdocs_src/site/`` (read only). No DB, no server, no network, no writes outside ``tmp_path``.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest
from lxml import html as lxml_html

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MKDOCS_SRC = PROJECT_ROOT / "mkdocs_src"
HOOK_ENTRY = "hooks/minify_html.py"
HOOK = MKDOCS_SRC / HOOK_ENTRY
SITE = MKDOCS_SRC / "site"

needs_built_site = pytest.mark.skipif(not (SITE / "index.html").exists(), reason="the docs are not built here (no mkdocs_src/site/index.html): run ./dev.py mkdocs build")


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("minify_html_under_test", HOOK)
    assert spec is not None and spec.loader is not None, f"cannot load {HOOK}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalised(element, protected: frozenset, inside: bool = False):
    """The tree as a browser sees it: tag, attributes, text with whitespace runs collapsed unless a protected element holds it."""
    tag = element.tag if isinstance(element.tag, str) else "#"
    here = inside or tag in protected

    def collapse(text, keep):
        return "" if text is None else (text if keep else re.sub(r"\s+", " ", text))

    return (
        tag,
        tuple(sorted(element.attrib.items())),
        collapse(element.text, here) if tag != "#" else element.text,
        tuple(normalised(child, protected, here) for child in element),
        collapse(element.tail, inside),
    )


def same_dom(hook: ModuleType, before: str, after: str) -> bool:
    protected = frozenset(hook.PROTECTED_ELEMENTS)
    return normalised(lxml_html.fromstring(before.encode()), protected) == normalised(lxml_html.fromstring(after.encode()), protected)


# ---------------------------------------------------------------------------
# minify()
# ---------------------------------------------------------------------------


class TestMinify:
    def test_indentation_and_blank_lines_go(self, hook):
        page = "<ul>\n\n      <li>\n        <a href='x'>\n          One\n        </a>\n      </li>\n\n    </ul>\n"

        assert hook.minify(page) == "<ul>\n<li>\n<a href='x'>\nOne\n</a>\n</li>\n</ul>\n"

    def test_a_separator_is_left_between_inline_elements(self, hook):
        out = hook.minify("<p><b>a</b>\n      <i>b</i></p>")

        assert out == "<p><b>a</b>\n<i>b</i></p>"  # still whitespace between them: the words do not join

    def test_whitespace_without_a_newline_is_content_and_stays(self, hook):
        assert hook.minify("<p>a   b <b>c</b>  d</p>") == "<p>a   b <b>c</b>  d</p>"

    @pytest.mark.parametrize("element", ["pre", "code", "kbd", "textarea", "script", "style"])
    def test_protected_elements_are_untouched(self, hook, element):
        inner = "  line one\n\n      line two\n    "
        page = f"<div>\n   <{element} class='x'>{inner}</{element}>\n   </div>"

        assert hook.minify(page) == f"<div>\n<{element} class='x'>{inner}</{element}>\n</div>"

    def test_a_pre_keeps_the_markup_of_its_highlighting(self, hook):
        pre = '<pre><span></span><code>  <span class="k">def</span> f():\n\n      return 1\n</code></pre>'

        assert hook.minify(f"<div>\n   {pre}\n</div>") == f"<div>\n{pre}\n</div>"

    def test_the_element_name_must_match_whole(self, hook):
        """``<preview>`` and ``<codex>`` are not ``<pre>`` and ``<code>``: their whitespace is minified."""
        assert hook.minify("<codex>\n   a\n</codex>") == "<codex>\na\n</codex>"

    def test_the_protected_tag_is_matched_in_any_case(self, hook):
        page = "<PRE>\n   keep\n\n   me\n</PRE>"

        assert hook.minify(page) == page

    def test_the_inside_of_a_tag_is_untouched(self, hook):
        page = '<a title="two\n      lines" data-x=\'a\n    b\' href="x">\n   t\n</a>'

        assert hook.minify(page) == '<a title="two\n      lines" data-x=\'a\n    b\' href="x">\nt\n</a>'

    def test_a_greater_than_in_an_attribute_does_not_end_the_tag(self, hook):
        page = '<a title="a > b\n      c" href="x">\n   t\n</a>\n   <p>\n   z\n   </p>'

        assert hook.minify(page) == '<a title="a > b\n      c" href="x">\nt\n</a>\n<p>\nz\n</p>'

    def test_a_lone_less_than_is_text(self, hook):
        assert hook.minify("<p>\n  1 < 2\n</p>") == "<p>\n1 < 2\n</p>"

    def test_it_is_idempotent(self, hook):
        page = "<div>\n   <pre>  a\n\n b</pre>\n\n   <p>x\n    y</p>\n</div>\n\n"

        once = hook.minify(page)

        assert hook.minify(once) == once


MATERIAL_LIKE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>
      A page
    </title>
    <style>
      :root { --a: 1; }

      .x { color: red; }
    </style>
    <script id="__config" type="application/json">{"base": "..",
      "features": ["navigation.tabs"]}</script>
  </head>
  <body>
    <nav class="md-nav">
      <ul class="md-nav__list">

        <li class="md-nav__item">
          <a href="../x/" class="md-nav__link">
            <span class="md-ellipsis">
              One
            </span>
          </a>
        </li>
      </ul>
    </nav>
    <article>
      <h1>Title <b>bold</b>
        and <i>italic</i></h1>
      <p>Use <code>a   b</code> and <kbd>Ctrl  +  C</kbd>.</p>
      <div class="highlight"><pre><span></span><code>one
  two

three
</code></pre></div>
      <table>
        <tr>
          <td>cell</td>
          <td>
            <code>x  y</code>
          </td>
        </tr>
      </table>
      <div class="arithmatex">\\[
        a   +   b
      \\]</div>
      <textarea>
   keep
</textarea>
    </article>
    <script>
      document.querySelectorAll("a").forEach(function (a) {
        console.log(a);
      });
    </script>
  </body>
</html>
"""


class TestDom:
    def test_a_page_shaped_like_materials_is_the_same_dom(self, hook):
        out = hook.minify(MATERIAL_LIKE)

        assert same_dom(hook, MATERIAL_LIKE, out)
        assert len(out) < len(MATERIAL_LIKE) * 0.85

    def test_the_protected_text_is_kept_byte_for_byte(self, hook):
        out = hook.minify(MATERIAL_LIKE)

        for fragment in ("<code>one\n  two\n\nthree\n</code>", "<code>a   b</code>", "<kbd>Ctrl  +  C</kbd>", "<textarea>\n   keep\n</textarea>", "      :root { --a: 1; }\n\n      .x { color: red; }\n"):
            assert fragment in out

    def test_the_check_would_catch_a_change(self, hook):
        """The comparison is not vacuous: joining two words, or squeezing a ``<pre>``, makes the DOMs differ."""
        assert not same_dom(hook, "<p><b>a</b> <i>b</i></p>", "<p><b>a</b><i>b</i></p>")
        assert not same_dom(hook, "<pre>a\n\nb</pre>", "<pre>a\nb</pre>")


# ---------------------------------------------------------------------------
# minify_site() and the hook's events
# ---------------------------------------------------------------------------


class TestSite:
    def test_every_html_is_minified_in_place_and_the_rest_is_left(self, hook, tmp_path):
        (tmp_path / "a").mkdir()
        page = "<div>\n      <p>x</p>\n\n</div>\n"
        (tmp_path / "index.html").write_text(page, encoding="utf-8")
        (tmp_path / "a" / "deep.html").write_text(page, encoding="utf-8")
        (tmp_path / "app.js").write_text("a\n\n  b", encoding="utf-8")
        (tmp_path / "data.json").write_text('{\n  "a": 1\n}', encoding="utf-8")

        files, before, after = hook.minify_site(tmp_path)

        assert files == 2 and before == 2 * len(page.encode()) and after == 2 * len(b"<div>\n<p>x</p>\n</div>\n")
        assert (tmp_path / "a" / "deep.html").read_text(encoding="utf-8") == "<div>\n<p>x</p>\n</div>\n"
        assert (tmp_path / "app.js").read_text(encoding="utf-8") == "a\n\n  b"
        assert (tmp_path / "data.json").read_text(encoding="utf-8") == '{\n  "a": 1\n}'

    def test_a_page_that_is_not_utf8_is_left_alone(self, hook, tmp_path, caplog):
        raw = b"<p>\n   caf\xe9\n</p>"
        (tmp_path / "latin.html").write_bytes(raw)

        files, _, _ = hook.minify_site(tmp_path)

        assert files == 0 and (tmp_path / "latin.html").read_bytes() == raw

    def test_the_site_is_minified_only_once_and_never_for_serve(self, hook, tmp_path, monkeypatch):
        page = "<div>\n      <p>x</p>\n</div>\n"
        target = tmp_path / "index.html"

        class Plugin:
            building = False

        class Config(dict):
            plugins = {"i18n": Plugin()}

        config = Config(site_dir=str(tmp_path))

        # serve: nothing is written
        target.write_text(page, encoding="utf-8")
        hook.on_startup("serve", False)
        hook.on_post_build(config)
        assert target.read_text(encoding="utf-8") == page

        # inside the nested language build: nothing is written
        hook.on_startup("build", False)
        config.plugins["i18n"].building = True
        hook.on_post_build(config)
        assert target.read_text(encoding="utf-8") == page

        # the outer build, and gh-deploy: minified
        config.plugins["i18n"].building = False
        hook.on_post_build(config)
        assert target.read_text(encoding="utf-8") == "<div>\n<p>x</p>\n</div>\n"
        target.write_text(page, encoding="utf-8")
        hook.on_startup("gh-deploy", False)
        hook.on_post_build(config)
        assert target.read_text(encoding="utf-8") == "<div>\n<p>x</p>\n</div>\n"

    def test_the_hook_is_registered(self):
        hooks = re.search(r"^hooks:\n((?:[ \t]+-[^\n]*\n)+)", (MKDOCS_SRC / "mkdocs.yml").read_text(encoding="utf-8"), flags=re.MULTILINE)

        assert hooks is not None and f"- {HOOK_ENTRY}" in hooks.group(1)


# ---------------------------------------------------------------------------
# the real site
# ---------------------------------------------------------------------------


@needs_built_site
class TestBuiltSite:
    @staticmethod
    def sample() -> list[Path]:
        """Pages of every language and every section: the first two of each folder, the home pages, the 404."""
        pages: list[Path] = [SITE / "index.html", SITE / "404.html"]
        for language in ("", "it", "fr", "es"):
            base = SITE / language if language else SITE
            for section in ("user", "admin", "financial-theory", "developer", "gallery", "community"):
                pages += sorted((base / section).glob("**/index.html"))[:2]
        return [page for page in pages if page.is_file()]

    def test_a_sample_of_every_language_and_section_is_the_same_dom(self, hook):
        pages = self.sample()
        assert len(pages) >= 20, f"the sample holds only {len(pages)} pages"
        for page in pages:
            before = page.read_text(encoding="utf-8")
            after = hook.minify(before)
            assert same_dom(hook, before, after), f"{page.relative_to(SITE)} is not the same DOM after minify"
            assert hook.minify(after) == after

    def test_no_indentation_is_left_in_the_text_after_minify(self, hook):
        """Whatever the state of the built site (before or after the hook ran), ``minify`` leaves no indented line in the
        text between the tags: the proof that the rule reaches Material's output."""
        for page in self.sample():
            out = hook.minify(page.read_text(encoding="utf-8"))
            last, chunks = 0, []
            for protected in hook._PROTECTED.finditer(out):  # the text between the protected elements, chunk by chunk
                chunks.append(out[last : protected.start()])
                last = protected.end()
            chunks.append(out[last:])
            for chunk in chunks:
                for text in hook._TAG_RE.split(chunk):  # one text node at a time: a space after a tag is not an indent
                    assert not re.search(r"\n[ \t]", text), f"{page.relative_to(SITE)} keeps indented lines after minify"
