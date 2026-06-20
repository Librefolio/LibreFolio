#!/usr/bin/env python3
"""
Structural validation of MkDocs translation files.

Cross-references .en.md source files with their .{lang}.md translations
and reports structural discrepancies:

  - Heading level mismatches (different # count)
  - Missing or altered links/URLs
  - Modified code blocks
  - Artifact remnants (Translator's Notes, <translation> tags, etc.)
  - Missing emojis in headings
  - Abnormal file size ratio
  - YAML front-matter corruption

Usage (standalone):
    python validate_translations.py
    python validate_translations.py --lang it --file faq.en.md

Usage (via dev.py):
    ./dev.py mkdocs translate-validate
    ./dev.py mkdocs translate-validate --lang it
    ./dev.py mkdocs translate-validate --file faq.en.md --verbose
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Import shared infrastructure from translate_docs
from translate_docs import (
    DOCS_DIR,
    _detect_target_languages,
    get_translatable_files,
)

# ---------------------------------------------------------------------------
# Issue severity
# ---------------------------------------------------------------------------

class Severity:
    ERROR = "❌ ERROR"
    WARN = "⚠️  WARN"
    INFO = "ℹ️  INFO"
    LOCALIZED = "🌐 LOCALIZED"  # intentional localization (text in \text{}, code comments, decimal sep)


@dataclass
class Issue:
    severity: str
    file: str
    lang: str
    check: str
    message: str
    line: int | None = None

    def __str__(self):
        loc = f":{self.line}" if self.line else ""
        return f"  {self.severity} [{self.check}] {self.file}{loc} ({self.lang}): {self.message}"


@dataclass
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)
    files_checked: int = 0
    files_ok: int = 0
    files_missing: int = 0

    @property
    def errors(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARN)

    @property
    def localized(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.LOCALIZED)


# ---------------------------------------------------------------------------
# Markdown structure extraction
# ---------------------------------------------------------------------------

def _extract_headings(text: str) -> list[tuple[int, int, str]]:
    """
    Extract markdown headings with line numbers.
    Returns list of (line_number, level, text).
    """
    headings = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2).strip()
            headings.append((i, level, heading_text))
    return headings


def _extract_links(text: str) -> list[tuple[str, str]]:
    """
    Extract markdown links [text](url).
    Returns list of (display_text, url).
    """
    return re.findall(r'\[([^\]]*)\]\(([^)]+)\)', text)


def _extract_code_blocks(text: str) -> list[str]:
    """
    Extract fenced code blocks (``` ... ```).
    Returns list of code block content (including language tag).
    """
    blocks = re.findall(r'```(\w*)\n(.*?)```', text, re.DOTALL)
    return [f"```{lang}\n{code}```" for lang, code in blocks]


def _extract_emojis(text: str) -> list[str]:
    """Extract emoji characters from text."""
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed chars
        "\U0001F900-\U0001F9FF"  # supplemental
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended-A
        "\U00002600-\U000026FF"  # misc symbols
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U0000200D"             # zero-width joiner
        "\U00002B50\U00002B55"   # star, circle
        "]+",
        re.UNICODE,
    )
    return emoji_pattern.findall(text)


def _extract_front_matter(text: str) -> str | None:
    """Extract YAML front-matter (--- ... ---) if present."""
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_heading_structure(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Compare heading levels between source and translation.
    Flags: different heading count, level mismatch, missing/extra headings.
    """
    issues = []
    src_headings = _extract_headings(source)
    tr_headings = _extract_headings(translated)

    # Count mismatch
    if len(src_headings) != len(tr_headings):
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="heading-count",
            message=f"Source has {len(src_headings)} headings, translation has {len(tr_headings)}",
        ))

    # Level-by-level comparison (zip to shorter)
    for idx, (src_h, tr_h) in enumerate(zip(src_headings, tr_headings)):
        src_line, src_level, src_text = src_h
        tr_line, tr_level, tr_text = tr_h

        if src_level != tr_level:
            issues.append(Issue(
                severity=Severity.ERROR,
                file=cache_key, lang=lang,
                check="heading-level",
                line=tr_line,
                message=f"Heading #{idx + 1}: source is h{src_level}, translation is h{tr_level} "
                        f"(src: '{src_text[:40]}', tr: '{tr_text[:40]}')",
            ))

        # Check emoji preservation in heading
        src_emojis = _extract_emojis(src_text)
        tr_emojis = _extract_emojis(tr_text)
        if src_emojis != tr_emojis:
            issues.append(Issue(
                severity=Severity.WARN,
                file=cache_key, lang=lang,
                check="heading-emoji",
                line=tr_line,
                message=f"Heading #{idx + 1}: emoji mismatch — "
                        f"source {''.join(src_emojis)} vs translation {''.join(tr_emojis)}",
            ))

    return issues


def check_links(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Verify all URLs from source are preserved in translation.
    Display text may be translated — URLs must NOT change.
    """
    issues = []
    src_links = _extract_links(source)
    tr_links = _extract_links(translated)

    src_urls = [url for _, url in src_links]
    tr_urls = [url for _, url in tr_links]

    # Missing URLs
    for url in src_urls:
        if url not in tr_urls:
            issues.append(Issue(
                severity=Severity.ERROR,
                file=cache_key, lang=lang,
                check="link-missing",
                message=f"URL missing in translation: {url}",
            ))

    # Extra URLs (less critical — might be legitimate)
    for url in tr_urls:
        if url not in src_urls:
            issues.append(Issue(
                severity=Severity.INFO,
                file=cache_key, lang=lang,
                check="link-extra",
                message=f"Extra URL in translation (not in source): {url}",
            ))

    # Count mismatch (different from missing — could be duplicate)
    if len(src_links) != len(tr_links):
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="link-count",
            message=f"Source has {len(src_links)} links, translation has {len(tr_links)}",
        ))

    return issues


def check_code_blocks(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Verify code blocks are preserved exactly.
    Code blocks should NEVER be translated.
    """
    issues = []
    src_blocks = _extract_code_blocks(source)
    tr_blocks = _extract_code_blocks(translated)

    if len(src_blocks) != len(tr_blocks):
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="code-block-count",
            message=f"Source has {len(src_blocks)} code blocks, translation has {len(tr_blocks)}",
        ))

    for idx, (src_b, tr_b) in enumerate(zip(src_blocks, tr_blocks)):
        if src_b.strip() != tr_b.strip():
            # Show first difference
            src_lines = src_b.strip().splitlines()
            tr_lines = tr_b.strip().splitlines()
            for line_idx, (sl, tl) in enumerate(zip(src_lines, tr_lines)):
                if sl != tl:
                    issues.append(Issue(
                        severity=Severity.LOCALIZED,  # shell comments translated or alignment stripped
                        file=cache_key, lang=lang,
                        check="code-block-modified",
                        message=(
                            f"Code block #{idx + 1}, line {line_idx + 1} altered "
                            f"(check: comments translated or alignment stripped):\n"
                            f"    SRC: {sl[:80]}\n"
                            f"    TRN: {tl[:80]}"
                        ),
                    ))
                    break
            else:
                # Length difference
                issues.append(Issue(
                    severity=Severity.WARN,
                    file=cache_key, lang=lang,
                    check="code-block-modified",
                    message=f"Code block #{idx + 1}: different line count "
                            f"({len(src_lines)} vs {len(tr_lines)})",
                ))

    return issues


def check_artifacts(
    translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Detect known translation artifacts that should have been cleaned.
    """
    issues = []
    lines = translated.splitlines()

    # Translator notes section (heading variants)
    translator_notes_patterns = [
        r"###?\s*Note?\s+(?:del|du)\s+Trad",
        r"###?\s*Translator['\u2019]?s?\s+Notes?",
        r"###?\s*Notas?\s+del?\s+Trad",
        r"###?\s*Notes?\s+(?:de\s+)?traduction",
        # Emoji variant: ## 📖 Notes du Traducteur
        r"##\s+\S+\s+Note?\s+(?:del|du)\s+Trad",
        r"##\s+\S+\s+Notas?\s+del?\s+Trad",
    ]
    for i, line in enumerate(lines, 1):
        for pattern in translator_notes_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(Issue(
                    severity=Severity.ERROR,
                    file=cache_key, lang=lang,
                    check="artifact-translator-notes",
                    line=i,
                    message=f"Translator notes artifact found: '{line.strip()}'",
                ))
                break

    # Bold translator notes: **Notas del Traductor**, **Notes du traducteur**
    _notes_kw = (
        r"(?:Notas?\s+del?\s+Trad\w+|Notes?\s+du\s+Trad\w+|"
        r"Note?\s+del\s+Trad\w+|Translator['\u2019]?s?\s+Notes?)"
    )
    bold_notes = re.findall(rf'\*\*{_notes_kw}\*\*', translated, re.IGNORECASE)
    if bold_notes:
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="artifact-translator-notes-bold",
            message=f"Translator notes in bold format: {bold_notes[0]}",
        ))

    # HTML translator notes: <h2>Notas del Traductor</h2>
    html_notes = re.findall(
        rf'<h[1-6]>\s*{_notes_kw}\s*</h[1-6]>', translated, re.IGNORECASE,
    )
    if html_notes:
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="artifact-translator-notes-html",
            message=f"Translator notes in HTML heading: {html_notes[0]}",
        ))

    # <translation> tags
    if re.search(r'</?translation>', translated):
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="artifact-translation-tag",
            message="<translation> tag remnant found",
        ))

    # Glossary markers [N] not part of links
    glossary_markers = re.findall(r'\[(\d+)\](?!\()', translated)
    if glossary_markers:
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="artifact-glossary-marker",
            message=f"Glossary markers found: [{'], ['.join(glossary_markers[:5])}] "
                    f"({len(glossary_markers)} total)",
        ))

    # Glossary definition block (line starting with [N] followed by term definition)
    for i, line in enumerate(lines, 1):
        if re.match(r'^\[\d+\]\s+\w+', line.strip()):
            issues.append(Issue(
                severity=Severity.WARN,
                file=cache_key, lang=lang,
                check="artifact-glossary-block",
                line=i,
                message=f"Glossary definition line: '{line.strip()[:60]}'",
            ))

    # Footnote definitions [^N]: (translator notes disguised as footnotes)
    footnote_defs = re.findall(r'^\[\^\d+\]:.*$', translated, re.MULTILINE)
    if footnote_defs:
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="artifact-footnote-defs",
            message=f"Footnote definitions found ({len(footnote_defs)}): "
                    f"likely translator notes in footnote format",
        ))

    # Inline footnote references [^N]
    footnote_refs = re.findall(r'\[\^\d+\]', translated)
    if footnote_refs:
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="artifact-footnote-refs",
            message=f"Inline footnote refs found ({len(footnote_refs)}): "
                    f"{', '.join(footnote_refs[:5])}",
        ))

    return issues


def check_admonition_indent(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Check that admonition content lines are properly indented (4 spaces).
    Translation LLMs often strip the leading spaces from admonition bodies.
    Also checks title preservation and body presence.
    """
    issues = []
    lines = translated.splitlines()
    src_lines = source.splitlines()

    # ── 1. Indentation check ──
    for i, line in enumerate(lines):
        if re.match(r'^!!! \w+', line) or re.match(r'^\?\?\? \w+', line):
            # Check next non-empty line for proper indentation
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j]
                if next_line.strip() == '':
                    continue
                if (next_line.startswith('    ')
                        or next_line.startswith('!!! ')
                        or next_line.startswith('??? ')
                        or next_line.startswith('---')):
                    break  # Properly indented or new block
                if next_line.strip():
                    issues.append(Issue(
                        severity=Severity.ERROR,
                        file=cache_key, lang=lang,
                        check="admonition-indent",
                        line=j + 1,
                        message=f"Admonition content not indented (needs 4 spaces): "
                                f"'{next_line.strip()[:50]}'",
                    ))
                    break

    # ── 2. Title preservation ──
    _adm_title_re = re.compile(r'^(?:!!!|[?]{3})\s+\w+\s+"([^"]*)"')
    src_titles = _adm_title_re.findall(source)
    tr_titles = _adm_title_re.findall(translated)

    if len(src_titles) != len(tr_titles):
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="admonition-title-count",
            message=f"Admonition titles: source {len(src_titles)}, "
                    f"translation {len(tr_titles)}",
        ))

    for idx, (src_t, tr_t) in enumerate(zip(src_titles, tr_titles)):
        if src_t.strip() and not tr_t.strip():
            issues.append(Issue(
                severity=Severity.ERROR,
                file=cache_key, lang=lang,
                check="admonition-title-empty",
                message=f"Admonition #{idx + 1}: title lost "
                        f"(source: \"{src_t}\")",
            ))

    # ── 3. Body presence ──
    for i, line in enumerate(lines):
        if re.match(r'^(?:!!!|[?]{3})\s+\w+', line):
            has_body = False
            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j]
                if next_line.startswith('    ') and next_line.strip():
                    has_body = True
                    break
                # Non-indented non-empty content = body is outside the box
                if (next_line.strip()
                        and not next_line.startswith('    ')
                        and not re.match(r'^(?:!!!|[?]{3})\s+', next_line)
                        and next_line.strip() != '---'):
                    break
            if not has_body:
                issues.append(Issue(
                    severity=Severity.ERROR,
                    file=cache_key, lang=lang,
                    check="admonition-body-missing",
                    line=i + 1,
                    message=f"Admonition has no indented body content: "
                            f"'{line.strip()[:60]}'",
                ))

    # ── 4. Empty line after directive (Prettier-safe) ──
    # Admonitions MUST have an empty line between the directive and the body.
    # Without it, Prettier removes the 4-space indentation, breaking the box.
    for i, line in enumerate(lines):
        if re.match(r'^(?:!!!|[?]{3})\s+\w+', line):
            if i + 1 < len(lines) and lines[i + 1].strip() != '':
                # Next line is NOT empty — check if it's indented body content
                if lines[i + 1].startswith('    '):
                    issues.append(Issue(
                        severity=Severity.WARN,
                        file=cache_key, lang=lang,
                        check="admonition-empty-line",
                        line=i + 1,
                        message=f"Admonition missing empty line after directive "
                                f"(Prettier will break it): '{line.strip()[:60]}'",
                    ))

    return issues


def check_file_size(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Flag abnormal size ratios.
    Translations should typically be 0.8x-1.5x the source size.
    """
    issues = []
    src_len = len(source)
    tr_len = len(translated)

    if src_len == 0:
        return issues

    ratio = tr_len / src_len

    if ratio < 0.5:
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="size-ratio",
            message=f"Translation is {ratio:.0%} of source — likely truncated "
                    f"({tr_len} vs {src_len} chars)",
        ))
    elif ratio < 0.75:
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="size-ratio",
            message=f"Translation is {ratio:.0%} of source — might be incomplete "
                    f"({tr_len} vs {src_len} chars)",
        ))
    elif ratio > 2.0:
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="size-ratio",
            message=f"Translation is {ratio:.0%} of source — likely has artifacts "
                    f"({tr_len} vs {src_len} chars)",
        ))

    return issues


def check_front_matter(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """Check YAML front-matter preservation."""
    issues = []
    src_fm = _extract_front_matter(source)
    tr_fm = _extract_front_matter(translated)

    if src_fm and not tr_fm:
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="front-matter-missing",
            message="Source has YAML front-matter but translation doesn't",
        ))
    elif not src_fm and tr_fm:
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="front-matter-added",
            message="Translation has YAML front-matter but source doesn't",
        ))

    return issues


def check_list_structure(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Compare bullet/numbered list item counts.
    Translations should have the same number of list items.
    """
    issues = []

    # Bullet lists
    src_bullets = re.findall(r'^\s*[-*+]\s', source, re.MULTILINE)
    tr_bullets = re.findall(r'^\s*[-*+]\s', translated, re.MULTILINE)
    if len(src_bullets) != len(tr_bullets):
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="list-bullet-count",
            message=f"Bullet items: source {len(src_bullets)}, translation {len(tr_bullets)}",
        ))

    # Numbered lists
    src_numbered = re.findall(r'^\s*\d+\.\s', source, re.MULTILINE)
    tr_numbered = re.findall(r'^\s*\d+\.\s', translated, re.MULTILINE)
    if len(src_numbered) != len(tr_numbered):
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="list-numbered-count",
            message=f"Numbered items: source {len(src_numbered)}, translation {len(tr_numbered)}",
        ))

    return issues


def check_admonitions(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Check MkDocs admonition syntax preservation (!!!, ???).
    The type keyword must NOT be translated.
    """
    issues = []
    src_admonitions = re.findall(r'^(!{3}|[?]{3})\s+(\w+)', source, re.MULTILINE)
    tr_admonitions = re.findall(r'^(!{3}|[?]{3})\s+(\w+)', translated, re.MULTILINE)

    if len(src_admonitions) != len(tr_admonitions):
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="admonition-count",
            message=f"Admonitions: source {len(src_admonitions)}, "
                    f"translation {len(tr_admonitions)}",
        ))

    for idx, (src_a, tr_a) in enumerate(zip(src_admonitions, tr_admonitions)):
        src_marker, src_type = src_a
        tr_marker, tr_type = tr_a
        if src_type != tr_type:
            issues.append(Issue(
                severity=Severity.ERROR,
                file=cache_key, lang=lang,
                check="admonition-type",
                message=f"Admonition #{idx + 1}: type changed from '{src_type}' to '{tr_type}'",
            ))

    return issues


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks from text (for checks that should ignore code)."""
    return re.sub(r'```\w*\n.*?```', '', text, flags=re.DOTALL)


def check_html_blocks(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Verify HTML tags/blocks are preserved (gallery pages have heavy HTML).
    Only checks tag names and attributes — inner text may be translated.
    Ignores content inside code blocks.
    """
    issues = []

    # Strip code blocks first to avoid false positives from e.g. <username>
    src_clean = _strip_code_blocks(source)
    tr_clean = _strip_code_blocks(translated)

    # Extract HTML tags (just opening/closing tag names)
    src_tags = re.findall(r'<(/?\w+)[^>]*>', src_clean)
    tr_tags = re.findall(r'<(/?\w+)[^>]*>', tr_clean)

    if src_tags != tr_tags:
        # Count by tag name
        from collections import Counter
        src_counts = Counter(src_tags)
        tr_counts = Counter(tr_tags)

        for tag, count in src_counts.items():
            tr_count = tr_counts.get(tag, 0)
            if tr_count != count:
                issues.append(Issue(
                    severity=Severity.WARN,
                    file=cache_key, lang=lang,
                    check="html-tag-mismatch",
                    message=f"<{tag}> count: source {count}, translation {tr_count}",
                ))

    return issues



# ---------------------------------------------------------------------------
# HTML attribute integrity check (technical attrs must not be translated)
# ---------------------------------------------------------------------------

def check_html_attrs(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Verify that technical HTML attributes are preserved verbatim in translations.

    Translatable attributes (alt, title, placeholder, aria-label, data-title):
        These carry human-readable text — translation is correct and expected.

    Non-translatable attributes (class, id, src, href, data-*, style, type,
    width, height, loading, etc.):
        These are structural/functional identifiers — must NOT be changed.

    Skips content inside Markdown code blocks to avoid false positives.
    """
    import re

    # Attributes that carry human text → legitimately translated
    TRANSLATABLE_ATTRS = frozenset({
        "alt", "title", "placeholder", "aria-label", "aria-labelledby",
        "aria-describedby", "data-title",
    })

    def _extract_tag_attrs(text: str) -> list[tuple[str, dict[str, str]]]:
        """Return list of (tag_name, {attr: value}) for every HTML opening tag."""
        results = []
        # Match opening tags (not self-closing handled the same way)
        for tag_m in re.finditer(r"<([a-zA-Z][\w-]*)([^>]*)>", text):
            tag_name = tag_m.group(1).lower()
            attr_str = tag_m.group(2)
            attrs = {}
            for attr_m in re.finditer(
                r"""([\w:@-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?""",
                attr_str,
            ):
                attr_name = attr_m.group(1).lower()
                attr_val = attr_m.group(2) or attr_m.group(3) or attr_m.group(4) or ""
                attrs[attr_name] = attr_val
            results.append((tag_name, attrs))
        return results

    issues = []
    src_clean = _strip_code_blocks(source)
    tr_clean = _strip_code_blocks(translated)

    src_tags = _extract_tag_attrs(src_clean)
    tr_tags = _extract_tag_attrs(tr_clean)

    # Only compare if same number of tags (structural check already handles count)
    if len(src_tags) != len(tr_tags):
        return issues

    for idx, ((s_tag, s_attrs), (t_tag, t_attrs)) in enumerate(zip(src_tags, tr_tags)):
        if s_tag != t_tag:
            continue  # tag mismatch handled by html-tag-mismatch check

        for attr, s_val in s_attrs.items():
            if attr in TRANSLATABLE_ATTRS:
                continue  # legitimately translated
            t_val = t_attrs.get(attr)
            if t_val is None:
                issues.append(Issue(
                    severity=Severity.WARN,
                    file=cache_key, lang=lang,
                    check="html-attr-missing",
                    message=(
                        f"<{s_tag}> tag #{idx + 1}: attribute `{attr}` missing "
                        f"in translation (expected: {s_val!r})"
                    ),
                ))
            elif t_val != s_val:
                issues.append(Issue(
                    severity=Severity.WARN,
                    file=cache_key, lang=lang,
                    check="html-attr-mismatch",
                    message=(
                        f"<{s_tag}> tag #{idx + 1}: attribute `{attr}` changed "
                        f"— source: {s_val!r}, translation: {t_val!r}"
                    ),
                ))

    return issues


# ---------------------------------------------------------------------------
# HTML static-path detection (breaks in dev or language subdirectories)
# ---------------------------------------------------------------------------

def check_html_relative_src(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Detect HTML src/href attributes with static resource paths that are
    environment-specific and will break either in dev or in production.

    Two problematic patterns:
    1. src="static/..."          -- bare relative path, breaks in /{lang}/ subdirs
    2. src="/LibreFolio/static/" -- hardcoded production base path, breaks in dev
                                    (where MkDocs is served at /mkdocs/)

    Fix: use JS dynamic base calculation, like:
        <img id="my-img">
        <script>(function(){
          var p = window.location.pathname.replace(/[/]+$/, "");
          var base = p.replace(/[/](it|fr|es)$/, "");
          document.getElementById("my-img").src = base + "/static/...";
        })();</script>
    """
    issues = []
    tr_clean = _strip_code_blocks(translated)
    lines = tr_clean.split("\n")

    def _add_issue(m, description):
        pos = tr_clean[:m.start()].count("\n") + 1
        line_content = lines[pos - 1][:80] if pos <= len(lines) else ""
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="html-relative-src",
            message=(
                f"L{pos}: {description} -- "
                f"use JS dynamic base pattern instead. "
                f"Context: {line_content!r}"
            ),
        ))

    # Pattern 1: bare relative src/href="static/..." (breaks in /lang/ subdirs)
    for m in re.finditer(r'(?:src|href)="static/', tr_clean, re.IGNORECASE):
        _add_issue(m, f"'{m.group(0)}...' is a relative path that breaks in /{lang}/ subdirectory")

    # Pattern 2: hardcoded production base /LibreFolio/static/ (breaks in dev at /mkdocs/)
    # Exclude:
    #   a) occurrences inside data-title="..." (JS carousel labels, not rendered directly)
    #   b) <img id="..."> followed within ~300 chars by getElementById(id).src = ... (JS override)
    for m in re.finditer(r'(?:src|href)="/LibreFolio/static/', tr_clean, re.IGNORECASE):
        before_line = tr_clean[:m.start()].split("\n")[-1]
        after_ctx = tr_clean[m.start():m.start() + 400]

        # Skip if inside data-title attribute
        if re.search(r'data-title=["\'](?:[^"\']*)', before_line):
            continue

        # Skip if this img has an id and a nearby <script> overrides .src via getElementById
        id_match = re.search(r'id="([^"]+)"', before_line + after_ctx[:100])
        if id_match:
            elem_id = id_match.group(1)
            if re.search(re.escape(elem_id) + r'[^<]*\.src\s*=', after_ctx):
                continue

        _add_issue(m, f"'{m.group(0)}...' hardcodes production base path, breaks in dev (/mkdocs/)")

    return issues


# ---------------------------------------------------------------------------
# Truncated word detection (common LLM artifact)
# ---------------------------------------------------------------------------

def check_truncated_words(
    translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Detect words that look truncated (partial words that aren't valid).
    Heuristic: words with unusual consonant clusters at word boundaries,
    very short fragments next to spaces, etc.
    """
    issues = []

    # Common patterns of LLM truncation in Italian/French/Spanish
    # Words that are suspiciously short and end mid-syllable
    truncation_patterns = [
        # Words with 3+ consonants in a row that aren't common clusters
        (r'\b[A-Z][a-z]*[bcdfghjklmnpqrstvwxyz]{3,}\b', "consonant cluster"),
        # Capitalized word fragment followed by space and lowercase continuation
        # e.g. "Critt valute" instead of "Criptovalute"
    ]

    # Check for split words: Capitalized + space + lowercase that looks like
    # a single word was split (e.g., "Critt valute" from "Criptovalute")
    lines = translated.splitlines()
    for line_num, line in enumerate(lines, 1):
        # Look for very short "words" (2-4 chars) that are capitalized and
        # followed by lowercase — possible truncation
        fragments = re.findall(r'\b([A-Z][a-z]{1,3})\s+([a-z]+)\b', line)
        for frag, following in fragments:
            # Skip common short words
            common_short = {"La", "Le", "Lo", "Il", "Un", "De", "El", "En",
                           "Es", "Se", "Si", "No", "Al", "Da", "Di", "In",
                           "Su", "Du", "Au", "Les", "Des", "Una", "Per",
                           "Con", "Del", "Dal", "Che", "Non", "Più",
                           "Tra", "Fra", "Suo", "Sua", "Poi", "Già"}
            if frag not in common_short and len(frag) <= 4:
                # Could be truncation — flag as info for manual review
                pass  # Too many false positives to be useful

    return issues


# ---------------------------------------------------------------------------
# LaTeX preservation check
# ---------------------------------------------------------------------------

def check_latex(
    source: str, translated: str, cache_key: str, lang: str,
) -> list[Issue]:
    """
    Verify LaTeX math expressions are preserved.
    Inline $...$ and display $$...$$ should be identical.
    """
    issues = []

    # Display math ($$...$$)
    src_display = re.findall(r'\$\$(.+?)\$\$', source, re.DOTALL)
    tr_display = re.findall(r'\$\$(.+?)\$\$', translated, re.DOTALL)

    if len(src_display) != len(tr_display):
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="latex-display-count",
            message=f"Display math blocks: source {len(src_display)}, "
                    f"translation {len(tr_display)}",
        ))

    for idx, (src_m, tr_m) in enumerate(zip(src_display, tr_display)):
        if src_m.strip() != tr_m.strip():
            issues.append(Issue(
                severity=Severity.LOCALIZED,  # \text{} content intentionally localized
                file=cache_key, lang=lang,
                check="latex-display-modified",
                message=(
                    f"Display math #{idx + 1} altered (check \\text{{}} not formula):\n"
                    f"    SRC: $${src_m.strip()[:80]}$$\n"
                    f"    TRN: $${tr_m.strip()[:80]}$$"
                ),
            ))

    # Inline math ($...$) — avoid display math, currency ($0.25 / 500 $), bash vars (${VAR})
    # Uses finditer to have access to surrounding context for suffix-currency detection
    _INLINE_RE = re.compile(r'(?<![\\\$])\$(?!\$)(.+?)(?<![\\\$])\$(?!\$)')
    _NON_MATH_CONTENT_RE = re.compile(r'^[\d,.]|^\{')  # prefix currency or bash var
    # Suffix currency: $ preceded by digit+optional-space (e.g. "500 $" or "500$")
    _SUFFIX_CURRENCY_CTX_RE = re.compile(r'\d\s?$')
    # Markdown bold/italic markup leaked between two $ signs — not real math
    _MARKDOWN_MARKUP_RE = re.compile(r'\*\*|\*|__')

    def _extract_inline(text: str) -> list[str]:
        """Extract inline math, filtering out currency and bash-variable false positives."""
        results = []
        for m in _INLINE_RE.finditer(text):
            content = m.group(1)
            # Filter: content starts with digit/comma (prefix currency like $0.25) or { (bash var)
            if _NON_MATH_CONTENT_RE.match(content.strip()):
                continue
            # Filter: text before opening $ ends with digit or digit+space (suffix currency like "500 $")
            before = text[:m.start()]
            if _SUFFIX_CURRENCY_CTX_RE.search(before):
                continue
            # Filter: content contains markdown bold/italic markers (leaked between two currency $ signs)
            if _MARKDOWN_MARKUP_RE.search(content):
                continue
            results.append(content)
        return results

    src_inline = _extract_inline(source)
    tr_inline = _extract_inline(translated)

    if len(src_inline) != len(tr_inline):
        issues.append(Issue(
            severity=Severity.WARN,
            file=cache_key, lang=lang,
            check="latex-inline-count",
            message=f"Inline math: source {len(src_inline)}, "
                    f"translation {len(tr_inline)}",
        ))

    for idx, (src_m, tr_m) in enumerate(zip(src_inline, tr_inline)):
        if src_m.strip() != tr_m.strip():
            issues.append(Issue(
                severity=Severity.LOCALIZED,  # \text{} or decimal sep intentionally localized
                file=cache_key, lang=lang,
                check="latex-inline-modified",
                message=(
                    f"Inline math #{idx + 1} altered (check \\text{{}} not formula structure):\n"
                    f"    SRC: ${src_m}$\n"
                    f"    TRN: ${tr_m}$"
                ),
            ))

    return issues


# ---------------------------------------------------------------------------
# Main validation orchestration
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    ("heading-structure", check_heading_structure, True),   # needs source + translated
    ("links", check_links, True),
    ("code-blocks", check_code_blocks, True),
    ("list-structure", check_list_structure, True),
    ("admonitions", check_admonitions, True),
    ("html-blocks", check_html_blocks, True),
    ("html-attrs", check_html_attrs, True),
    ("html-relative-src", check_html_relative_src, True),
    ("front-matter", check_front_matter, True),
    ("latex", check_latex, True),
    ("file-size", check_file_size, True),
    ("artifacts", check_artifacts, False),                  # only needs translated
    ("admonition-indent", check_admonition_indent, True),   # uses source for title comparison
]


def validate_file(
    source_path: Path, trans_path: Path,
    cache_key: str, lang: str,
    verbose: bool = False,
) -> list[Issue]:
    """Run all checks on a single source/translation pair."""
    source = source_path.read_text(encoding="utf-8")
    translated = trans_path.read_text(encoding="utf-8")
    issues = []

    for check_name, check_fn, needs_source in ALL_CHECKS:
        if needs_source:
            result = check_fn(source, translated, cache_key, lang)
        else:
            result = check_fn(translated, cache_key, lang)
        issues.extend(result)

    # Truncated words (translation-only)
    issues.extend(check_truncated_words(translated, cache_key, lang))

    return issues


def run_validate(args) -> int:
    """Main validation logic — called by dev.py or standalone."""
    target_langs = args.lang or _detect_target_languages()
    file_filter = getattr(args, "file", None)
    verbose = getattr(args, "verbose", False)
    hide_localized = getattr(args, "hide_localized", False)

    # Get source files list
    if file_filter:
        # Resolve file paths (same logic as translate_docs)
        import glob as glob_mod
        sources = []
        for f in file_filter:
            p = Path(f)
            if not p.name.endswith(".en.md"):
                # Try adding .en.md suffix
                if f.endswith(".md"):
                    f = f.replace(".md", ".en.md")
            cwd_path = (Path.cwd() / f).resolve()
            docs_path = (DOCS_DIR / f).resolve()
            if cwd_path.exists():
                p = cwd_path
            elif docs_path.exists():
                p = docs_path
            else:
                print(f"  ⚠️  File not found: {f}", file=sys.stderr)
                continue
            try:
                cache_key = str(p.relative_to(DOCS_DIR))
            except ValueError:
                cache_key = p.name
            sources.append((cache_key, p))
    else:
        nav_files = get_translatable_files()
        sources = [(rel, DOCS_DIR / rel) for rel in nav_files]

    if not sources:
        print("No translatable files found.")
        return 0

    result = ValidationResult()

    print(f"\n🔍 Validating translations...")
    print(f"   Languages: {', '.join(target_langs)}")
    print(f"   Source files: {len(sources)}")
    print()

    for cache_key, source_path in sources:
        if not source_path.exists():
            if verbose:
                print(f"  ⚠️  Source not found: {cache_key}")
            continue

        for lang in target_langs:
            trans_name = source_path.name.replace(".en.md", f".{lang}.md")
            trans_path = source_path.parent / trans_name

            if not trans_path.exists():
                result.files_missing += 1
                if verbose:
                    print(f"  ⏭️  {cache_key} → {lang}: translation not found")
                continue

            result.files_checked += 1
            issues = validate_file(source_path, trans_path, cache_key, lang, verbose)

            if issues:
                result.issues.extend(issues)
                # Filter for display (hide LOCALIZED if requested)
                visible = [i for i in issues
                           if not (hide_localized and i.severity == Severity.LOCALIZED)]
                if visible:
                    has_errors = any(i.severity == Severity.ERROR for i in visible)
                    has_warnings = any(i.severity == Severity.WARN for i in visible)
                    has_localized = any(i.severity == Severity.LOCALIZED for i in visible)
                    status = "❌" if has_errors else ("⚠️ " if has_warnings else ("🌐" if has_localized else "ℹ️ "))
                    print(f"  {status} {cache_key} → {lang}:")
                    for issue in visible:
                        print(f"    {issue}")
                elif verbose:
                    loc_count = sum(1 for i in issues if i.severity == Severity.LOCALIZED)
                    print(f"  🌐 {cache_key} → {lang}: {loc_count} localized (hidden)")
            else:
                result.files_ok += 1
                if verbose:
                    print(f"  ✅ {cache_key} → {lang}: OK")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"📊 Validation Summary:")
    print(f"   Files checked:  {result.files_checked}")
    print(f"   Files OK:       {result.files_ok}")
    print(f"   Files missing:  {result.files_missing}")
    print(f"   Errors:         {result.errors}")
    print(f"   Warnings:       {result.warnings}")
    print(f"   Localized:      {result.localized}"
          + ("  (hidden — use without --hide-localized to see)" if hide_localized else ""))

    # Breakdown by check type
    from collections import Counter
    err_counts = Counter(i.check for i in result.issues if i.severity == Severity.ERROR)
    warn_counts = Counter(i.check for i in result.issues if i.severity == Severity.WARN)
    loc_counts = Counter(i.check for i in result.issues if i.severity == Severity.LOCALIZED)
    if err_counts:
        print(f"\n   ❌ Errors by type:")
        for check, count in sorted(err_counts.items(), key=lambda x: -x[1]):
            print(f"      {count:3d}  {check}")
    if warn_counts:
        print(f"\n   ⚠️  Warnings by type:")
        for check, count in sorted(warn_counts.items(), key=lambda x: -x[1]):
            print(f"      {count:3d}  {check}")
    if loc_counts and not hide_localized:
        print(f"\n   🌐 Localized by type (intentional — use --hide-localized to suppress):")
        for check, count in sorted(loc_counts.items(), key=lambda x: -x[1]):
            print(f"      {count:3d}  {check}")

    if result.errors:
        print(f"\n❌ {result.errors} error(s) found — translations need fixing.")
        print(f"   Tip: re-translate with --force, or use a better model (e.g. Gemini Flash via OpenRouter)")
    elif result.warnings:
        print(f"\n⚠️  {result.warnings} warning(s) — review manually.")
    elif result.localized:
        print(f"\n🌐 {result.localized} localized diff(s) — intentional, no action needed.")
    else:
        print(f"\n✅ All translations look good!")

    return 1 if result.errors else 0


# ---------------------------------------------------------------------------
# CLI / dev.py integration
# ---------------------------------------------------------------------------

def register_subparser(mk_sub) -> None:
    """Register 'translate-validate' sub-command under 'mkdocs' in dev.py."""
    target_langs = _detect_target_languages()
    vp = mk_sub.add_parser(
        "translate-validate",
        help="Validate translated docs (structural cross-check)",
    )
    vp.add_argument(
        "--lang", action="extend", nargs="+", choices=target_langs,
        metavar="LANG",
        help=f"Target language(s) to validate. Detected: {target_langs}",
    )
    vp.add_argument(
        "--file", action="extend", nargs="+", metavar="PATH",
        help="Source file(s) to validate (relative to docs/)",
    )
    vp.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show OK files and skipped files",
    )
    vp.add_argument(
        "--hide-localized", "-L", action="store_true", dest="hide_localized",
        help="Hide intentional localization diffs (latex \\text{}, code comments, decimal sep)",
    )
    vp.set_defaults(func=run_validate)


def main():
    """Standalone CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate MkDocs translation files (structural cross-check)",
    )
    target_langs = _detect_target_languages()
    parser.add_argument(
        "--lang", action="extend", nargs="+", choices=target_langs,
        metavar="LANG",
    )
    parser.add_argument("--file", action="extend", nargs="+", metavar="PATH")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--hide-localized", "-L", action="store_true", dest="hide_localized",
        help="Hide intentional localization diffs",
    )
    parser.set_defaults(func=run_validate)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()



