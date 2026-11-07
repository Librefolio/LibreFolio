"""A Mermaid node with its own fill must say its text colour too (E9C).

Material draws a diagram's text in the theme's colour: light in the dark theme. A node whose ``style`` or ``classDef`` sets
a ``fill`` and no ``color`` is therefore a pale box with white text in the dark theme, and cannot be read. The documentation
had 127 such lines in 24 pages and four languages. This gate keeps them out: every ``style`` or ``classDef`` line of every
Mermaid block of every page that sets ``fill:`` also sets ``color:``.

A ``color:`` in the source is not enough (E9D): Mermaid writes it on the label's ``<div>`` and ``<span>``, and the text is a
``<p>`` that Material's theme CSS colours with the theme's label colour (``.nodeLabel p``): light in the dark theme. So the
early script must append a rule that makes the ``<p>`` inherit the colour of its ``<span>``. What the browser finally computes
was read from the built site in a browser, in the dark theme (see the lot's hand-over note); this file pins the pieces.

PURE: reads the Markdown and script sources only. No DB, no server, no network, no writes.
"""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[3] / "mkdocs_src" / "docs"
MERMAID = re.compile(r"```mermaid[ \t]*\n(.*?)```", re.S)
STYLE_LINE = re.compile(r"^\s*(?:style|classDef)\s")


EARLY = Path(__file__).resolve().parents[3] / "mkdocs_src" / "docs" / "javascripts" / "mermaid-early.js"


def fill_without_colour(root: Path = DOCS) -> list[str]:
    offenders = []
    for page in sorted(root.rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        for block in MERMAID.findall(text):
            for line in block.splitlines():
                if STYLE_LINE.match(line) and "fill:" in line and "color:" not in line:
                    offenders.append(f"{page.relative_to(root)}: {line.strip()}")
    return offenders


def test_no_mermaid_node_sets_a_fill_without_its_text_colour():
    assert fill_without_colour() == []


def test_the_gate_sees_a_line_without_a_colour(tmp_path):
    page = tmp_path / "page.md"
    page.write_text("```mermaid\nflowchart TD\n    A --> B\n    style B fill:#d4edda,stroke:#28a745\n```\n", encoding="utf-8")

    assert fill_without_colour(tmp_path) == ["page.md: style B fill:#d4edda,stroke:#28a745"]


def test_the_gate_accepts_a_colour_and_a_class_with_both(tmp_path):
    page = tmp_path / "page.md"
    page.write_text("```mermaid\nflowchart TD\n    style B fill:#d4edda,color:#1b1b1b\n    classDef ok fill:#fff,color:#000\n```\n", encoding="utf-8")

    assert fill_without_colour(tmp_path) == []


def _early_code() -> str:
    text = EARLY.read_text(encoding="utf-8")
    return re.sub(r"(?<!:)//[^\n]*|/\*.*?\*/", "", text, flags=re.S)


def test_the_text_of_a_node_takes_the_colour_its_label_was_given():
    code = _early_code()
    rule = re.search(r"""NODE_TEXT_CSS\s*=\s*["']([^"']+)["']""", code)
    assert rule, "mermaid-early.js defines the rule that lets a node's <p> inherit the colour of its label"
    assert re.search(r"\.nodeLabel p[^{]*\{[^}]*color:\s*inherit", rule.group(1)), "the <p> inside .nodeLabel inherits: Material colours it with the theme's label colour"
    assert re.search(r"\.cluster-label p[^{]*\{[^}]*color:\s*inherit", rule.group(1)), "the same for the label of a subgraph"


def test_the_rule_is_appended_after_materials_theme_css():
    code = _early_code()
    # Same specificity as Material's `.nodeLabel p` rule: the later one wins, so it is appended, never put first.
    assert re.search(r"themeCSS\s*=\s*\(\s*merged\.themeCSS\s*\|\|\s*[\"']{2}\s*\)\s*\+\s*NODE_TEXT_CSS", code)
    assert "mermaid.initialize" in code and "initialize(merged)" in code
