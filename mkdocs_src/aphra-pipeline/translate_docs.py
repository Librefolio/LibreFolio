#!/usr/bin/env python3
"""
Aphra Translation Pipeline for MkDocs Documentation.

Translates .en.md documentation files into target languages using Aphra
(LLM-based translation agent with Google Gemini via OpenRouter BYOK).

Lives in mkdocs_src/aphra-pipeline/ and integrates with dev.py via
register_subparser().

Usage (standalone):
    python translate_docs.py --lang it fr --dry-run
    python translate_docs.py --file faq.en.md --lang it

Usage (via dev.py):
    ./dev.py mkdocs translate --lang it fr
    ./dev.py mkdocs translate --force
    ./dev.py mkdocs translate --dry-run
"""

import argparse
import glob
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path constants (resolved relative to this script's location)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent  # mkdocs_src/aphra-pipeline/
MKDOCS_SRC = SCRIPT_DIR.parent  # mkdocs_src/
DOCS_DIR = MKDOCS_SRC / "docs"  # mkdocs_src/docs/
MKDOCS_YML = MKDOCS_SRC / "mkdocs.yml"  # mkdocs_src/mkdocs.yml
PROJECT_ROOT = MKDOCS_SRC.parent  # LibreFolio/
FRONTEND_I18N = PROJECT_ROOT / "frontend" / "src" / "lib" / "i18n" / "index.ts"

ENV_FILE = SCRIPT_DIR / ".env"
CONFIG_TOML = SCRIPT_DIR / "config.toml"
HASH_FILE = SCRIPT_DIR / ".translate-hashes.json"

# Source language (documentation is written in English)
SOURCE_LANG = "en"

# Fallback target languages if frontend detection fails
FALLBACK_TARGETS = ["it", "fr", "es"]

# EN-only nav sections (not translated)
EN_ONLY_SECTIONS = {"Developer Manual", "POC UX"}

# Aphra model configuration (overridable per-role via .env)
DEFAULT_APHRA_MODEL = "google/gemini-2.5-flash"

# Default Ollama base URL (OpenAI-compatible API)
DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"


# ---------------------------------------------------------------------------
# Language detection from frontend
# ---------------------------------------------------------------------------

def _detect_target_languages() -> list[str]:
    """
    Parse frontend/src/lib/i18n/index.ts to extract SUPPORTED_LOCALES,
    then exclude the source language ('en').

    Returns e.g. ['it', 'fr', 'es'].
    """
    try:
        content = FRONTEND_I18N.read_text(encoding="utf-8")
        match = re.search(r"SUPPORTED_LOCALES\s*=\s*\[([^\]]+)\]", content)
        if match:
            raw = match.group(1)
            locales = re.findall(r"['\"](\w+)['\"]", raw)
            targets = [l for l in locales if l != SOURCE_LANG]
            if targets:
                return targets
    except Exception:
        pass
    return FALLBACK_TARGETS


# ---------------------------------------------------------------------------
# Nav parsing — extract translatable file paths from mkdocs.yml
# ---------------------------------------------------------------------------

def _extract_nav_paths(nav_items: list, skip_sections: set[str]) -> list[str]:
    """
    Recursively walk the nav structure and collect file paths.
    Skips entire sections whose top-level label is in skip_sections.

    Nav uses plain .md references (e.g. faq.md); we convert to .en.md
    because on disk the source files use the i18n suffix (faq.en.md).
    """
    paths = []
    for item in nav_items:
        if isinstance(item, str):
            # Bare path (no label)
            if item.endswith(".md"):
                paths.append(item.replace(".md", ".en.md"))
        elif isinstance(item, dict):
            for label, value in item.items():
                if label in skip_sections:
                    continue
                if isinstance(value, str):
                    if value.endswith(".md"):
                        paths.append(value.replace(".md", ".en.md"))
                elif isinstance(value, list):
                    paths.extend(_extract_nav_paths(value, skip_sections))
    return paths


def get_translatable_files() -> list[str]:
    """
    Parse mkdocs.yml nav and return list of .en.md file paths
    (relative to docs/).
    """
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is required. Install with: pipenv install pyyaml", file=sys.stderr)
        sys.exit(1)

    # Use a loader that ignores !!python/name: tags (used by mkdocs material)
    class _SafeIgnoreLoader(yaml.SafeLoader):
        pass

    _SafeIgnoreLoader.add_multi_constructor(
        "tag:yaml.org,2002:python/",
        lambda loader, suffix, node: None,
        )

    with open(MKDOCS_YML, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=_SafeIgnoreLoader)

    nav = config.get("nav", [])
    return _extract_nav_paths(nav, EN_ONLY_SECTIONS)


# ---------------------------------------------------------------------------
# Hash cache for incremental translation
# ---------------------------------------------------------------------------

def _load_hashes() -> dict:
    """Load translation hash cache, migrating old format if needed.

    Old format:  {"file": {"md5": ..., "langs_done": [...], "last_translated": ...}}
    New format adds: {"file": {..., "analysis": ..., "analysis_model": ..., "langs": {"it": {...}}}}

    Migration is automatic and non-destructive (old fields are preserved).
    """
    if HASH_FILE.exists():
        try:
            data = json.loads(HASH_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        # Auto-migrate: ensure every entry has a "langs" dict
        migrated = False
        for key, entry in data.items():
            if isinstance(entry, dict) and "langs" not in entry:
                entry["langs"] = {}
                # Populate from langs_done if present (migration from old format)
                for lang in entry.get("langs_done", []):
                    entry["langs"][lang] = {
                        "translated_at": entry.get("last_translated", ""),
                        "models": {},
                        "critique": "",
                        "structural_diff": "",
                        "structural_issues": 0,
                        "elapsed_s": 0,
                        "migrated_from_v1": True,
                    }
                migrated = True
        if migrated:
            _save_hashes(data)
        return data
    return {}


def _save_hashes(hashes: dict) -> None:
    """Save translation hash cache."""
    HASH_FILE.write_text(json.dumps(hashes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _file_md5(filepath: Path) -> str:
    """Compute MD5 hash of a file."""
    return hashlib.md5(filepath.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Aphra config.toml generation
# ---------------------------------------------------------------------------

def _is_local_mode() -> bool:
    """Check if using a local LLM backend (Ollama, llama.cpp, etc.)."""
    base_url = _load_env_var("APHRA_BASE_URL", "")
    return base_url != "" and "openrouter.ai" not in base_url


def _get_base_url() -> str | None:
    """Get custom base URL for LLM API (None = default OpenRouter)."""
    url = _load_env_var("APHRA_BASE_URL", "")
    return url if url else None


def _load_api_key() -> str:
    """Load API key from .env file.

    In local mode (APHRA_BASE_URL set to non-OpenRouter), a dummy key
    is returned since Ollama/llama.cpp don't require authentication.
    """
    if _is_local_mode():
        return _load_env_var("OPENROUTER_API_KEY", "ollama-local")

    if not ENV_FILE.exists():
        print(f"ERROR: {ENV_FILE} not found. Copy from .env.example and add your key.", file=sys.stderr)
        sys.exit(1)

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "OPENROUTER_API_KEY":
            return value.strip().strip('"').strip("'")

    print("ERROR: OPENROUTER_API_KEY not found in .env", file=sys.stderr)
    sys.exit(1)


def _load_env_var(name: str, default: str = "") -> str:
    """Load a variable from .env file."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == name:
                val = value.strip().strip('"').strip("'")
                if val:
                    return val
    return default


def _load_models() -> dict:
    """
    Load per-role Aphra model names from .env.

    Roles (4 steps in the workflow):
      - analyzer:  Step 1 Analyze (reasoning — identify key terms)
      - writer:    Step 3 Translate + Step 5 Refine (generation)
      - critiquer: Step 4 Critique (reasoning — compare original vs translation)
      - searcher:  Step 2 Search (web lookup, usually skipped)

    Hierarchy:
      APHRA_ANALYZER  → defaults to APHRA_WRITER → APHRA_MODEL → DEFAULT
      APHRA_WRITER    → defaults to APHRA_MODEL → DEFAULT
      APHRA_CRITIQUER → defaults to APHRA_ANALYZER (reasoning model)
      APHRA_SEARCHER  → defaults to APHRA_MODEL → DEFAULT

    Returns dict with keys: analyzer, writer, searcher, critiquer.
    """
    shared = _load_env_var("APHRA_MODEL", DEFAULT_APHRA_MODEL)
    writer = _load_env_var("APHRA_WRITER", shared)
    analyzer = _load_env_var("APHRA_ANALYZER", writer)
    return {
        "analyzer": analyzer,
        "writer": writer,
        "searcher": _load_env_var("APHRA_SEARCHER", shared),
        "critiquer": _load_env_var("APHRA_CRITIQUER", analyzer),
    }


def _generate_config_toml(api_key: str, models: dict) -> None:
    """Generate temporary config.toml for Aphra.

    Format expected by Aphra (see config.example.toml):
      [openrouter]    → api_key
      [short_article] → writer, searcher, critiquer  (model per role)
    """
    config_content = f"""[openrouter]
api_key = "{api_key}"

[short_article]
writer = "{models['writer']}"
searcher = "{models['searcher']}"
critiquer = "{models['critiquer']}"
"""
    CONFIG_TOML.write_text(config_content, encoding="utf-8")


def _cleanup_config_toml() -> None:
    """Remove temporary config.toml."""
    if CONFIG_TOML.exists():
        CONFIG_TOML.unlink()


# ---------------------------------------------------------------------------
# Post-processing — clean Aphra translation artifacts
# ---------------------------------------------------------------------------

def _clean_translation(text: str) -> str:
    """
    Strip Aphra artifacts from translated text:

    1. <translation> / </translation> wrapper tags
    2. "Translator's Notes" / "Note del Traduttore" trailing section
    3. Glossary definitions block at the end ([N] term: definition...)
    4. Inline glossary markers [N] (preserves markdown links [text](url))
    """
    # 1. Strip <translation> / </translation> tags (Aphra wraps output in these)
    text = re.sub(r'</?translation>', '', text)

    # 2. Remove "Translator's Notes" trailing section (any language variant)
    #    Matches: ---\n### Note del Traduttore, ### Translator's Notes,
    #    ### Notes du Traducteur, ### Notas del Traductor, etc.
    #    Also matches without the --- separator.
    _NOTES_KW = (
        r"(?:Note?\s+(?:del|du)\s+Trad\w+|Translator['\u2019]?s?\s+Notes?"
        r"|Notas?\s+del?\s+Trad\w+)"
    )
    translator_notes_patterns = [
        # With --- separator (most common)
        rf"\n---\s*\n+\s*###?\s*{_NOTES_KW}.*",
        # Without --- separator
        rf"\n###?\s*{_NOTES_KW}.*",
        # Emoji between ## and text: ## 📖 Notes du Traducteur
        rf"\n---\s*\n+\s*##\s+\S+\s+{_NOTES_KW}.*",
        rf"\n##\s+\S+\s+{_NOTES_KW}.*",
        # Bold variant: **Notas del Traductor**, **Notes du traducteur**
        rf"\n---\s*\n+\*\*{_NOTES_KW}\*\*.*",
        rf"\n\*\*{_NOTES_KW}\*\*.*",
        # HTML variant: <h2>Notas del Traductor</h2>
        rf"\n<hr\s*/?\s*>\s*\n*<h[1-6]>\s*{_NOTES_KW}\s*</h[1-6]>.*",
        rf"\n<h[1-6]>\s*{_NOTES_KW}\s*</h[1-6]>.*",
    ]
    for pattern in translator_notes_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)

    # 3. Remove glossary block at the end
    #    Scan backwards: remove lines that are blank or start with [N]
    lines = text.split('\n')
    while lines:
        stripped = lines[-1].strip()
        if stripped == '' or re.match(r'^\[\d+\]', stripped):
            lines.pop()
        else:
            break
    text = '\n'.join(lines)

    # 4. Remove inline [N] markers — but NOT markdown links [text](url)
    #    [N] followed by ( is a markdown link → keep. Everything else → strip.
    text = re.sub(r'\[(\d+)\](?!\()', '', text)

    # 5. Remove footnote definitions [^N]: ... (LLM translator notes disguised as footnotes)
    #    These are NOT standard markdown footnotes from the source — the EN source has none.
    #    They appear only in translations as "Translator Notes" in footnote format.
    text = re.sub(r'^\[\^\d+\]:.*$', '', text, flags=re.MULTILINE)

    # 6. Remove inline footnote references [^N] (not markdown links)
    text = re.sub(r'\[\^\d+\]', '', text)

    # 7. Clean up double/triple spaces left by removed markers
    text = re.sub(r'  +', ' ', text)

    # 8. Collapse 3+ consecutive blank lines to 2 (left by removed footnotes)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Ensure file ends with single newline
    text = text.rstrip() + '\n'

    return text


# ---------------------------------------------------------------------------
# Structural diff — objective comparison between source and translation
# ---------------------------------------------------------------------------

def _extract_md_structure(text: str) -> dict:
    """
    Extract structural elements from a markdown document.

    Returns a dict with counts and lists of structural elements.
    """
    lines = text.split('\n')

    # ── Headings ──
    headings = []
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            headings.append({"level": len(m.group(1)), "text": m.group(2).strip()})

    # ── Code blocks (fenced) ──
    code_blocks = re.findall(r'^```(\w*)', text, re.MULTILINE)

    # ── Links [text](url) — exclude images ![alt](url) ──
    links = re.findall(r'(?<!!)\[([^\]]*)\]\(([^)]+)\)', text)

    # ── Images ![alt](url) ──
    images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', text)

    # ── Admonitions (MkDocs Material: !!! or ???) ──
    admonitions = re.findall(r'^(!!!|\?\?\?)\s+(\w+)', text, re.MULTILINE)

    # ── Horizontal rules ──
    hr_count = len(re.findall(r'^\s*---\s*$', text, re.MULTILINE))

    # ── Lists ──
    bullets = re.findall(r'^\s*[-*+]\s', text, re.MULTILINE)
    numbered = re.findall(r'^\s*\d+\.\s', text, re.MULTILINE)

    # ── Tables (pipe-delimited rows) ──
    table_rows = re.findall(r'^\s*\|.+\|\s*$', text, re.MULTILINE)

    # ── Bold markers ──
    bold_count = len(re.findall(r'\*\*[^*]+\*\*', text))

    # ── URLs used in links (for URL preservation check) ──
    link_urls = [url for _, url in links]
    image_urls = [url for _, url in images]

    return {
        "headings": headings,
        "code_blocks": code_blocks,
        "links": links,
        "link_urls": link_urls,
        "images": images,
        "image_urls": image_urls,
        "admonitions": admonitions,
        "hr_count": hr_count,
        "bullet_count": len(bullets),
        "numbered_count": len(numbered),
        "table_row_count": len(table_rows),
        "bold_count": bold_count,
        "line_count": len(lines),
    }


def _structural_diff(source_text: str, translated_text: str) -> str:
    """
    Compare markdown structure between source (EN) and translated text.

    Returns a factual report of structural anomalies that the critic model
    can use for objective evaluation. Returns empty string if no issues found.
    """
    src = _extract_md_structure(source_text)
    trn = _extract_md_structure(translated_text)

    issues: list[str] = []
    info: list[str] = []

    # ── 1. Headings: count per level ──
    src_levels = {}
    trn_levels = {}
    for h in src["headings"]:
        src_levels[h["level"]] = src_levels.get(h["level"], 0) + 1
    for h in trn["headings"]:
        trn_levels[h["level"]] = trn_levels.get(h["level"], 0) + 1

    all_levels = sorted(set(list(src_levels.keys()) + list(trn_levels.keys())))
    for lvl in all_levels:
        s = src_levels.get(lvl, 0)
        t = trn_levels.get(lvl, 0)
        if s != t:
            tag = "#" * lvl
            issues.append(f"HEADING_COUNT: '{tag}' headings — source={s}, translated={t} (Δ{t - s:+d})")

    # ── 2. Heading order / nesting ──
    src_outline_levels = [h["level"] for h in src["headings"]]
    trn_outline_levels = [h["level"] for h in trn["headings"]]
    if src_outline_levels != trn_outline_levels:
        issues.append(
            f"HEADING_STRUCTURE: heading level sequence differs.\n"
            f"  Source:     {src_outline_levels}\n"
            f"  Translated: {trn_outline_levels}"
        )

    # ── 3. Code blocks ──
    if len(src["code_blocks"]) != len(trn["code_blocks"]):
        issues.append(
            f"CODE_BLOCKS: source={len(src['code_blocks'])}, "
            f"translated={len(trn['code_blocks'])} "
            f"(Δ{len(trn['code_blocks']) - len(src['code_blocks']):+d})"
        )
    elif src["code_blocks"] != trn["code_blocks"]:
        issues.append(
            f"CODE_BLOCK_LANGS: language tags differ.\n"
            f"  Source:     {src['code_blocks']}\n"
            f"  Translated: {trn['code_blocks']}"
        )

    # ── 4. Link URLs preservation ──
    src_urls = sorted(src["link_urls"])
    trn_urls = sorted(trn["link_urls"])
    if src_urls != trn_urls:
        missing = set(src_urls) - set(trn_urls)
        added = set(trn_urls) - set(src_urls)
        parts = ["LINK_URLS: URL set differs."]
        if missing:
            parts.append(f"  Missing in translation: {sorted(missing)}")
        if added:
            parts.append(f"  Added in translation:   {sorted(added)}")
        issues.append("\n".join(parts))

    # ── 5. Link count ──
    if len(src["links"]) != len(trn["links"]):
        issues.append(
            f"LINK_COUNT: source={len(src['links'])}, "
            f"translated={len(trn['links'])} "
            f"(Δ{len(trn['links']) - len(src['links']):+d})"
        )

    # ── 6. Images ──
    if len(src["images"]) != len(trn["images"]):
        issues.append(
            f"IMAGE_COUNT: source={len(src['images'])}, "
            f"translated={len(trn['images'])} "
            f"(Δ{len(trn['images']) - len(src['images']):+d})"
        )
    src_img_urls = sorted(src["image_urls"])
    trn_img_urls = sorted(trn["image_urls"])
    if src_img_urls != trn_img_urls:
        issues.append(
            f"IMAGE_URLS: image URL set differs.\n"
            f"  Source:     {src_img_urls}\n"
            f"  Translated: {trn_img_urls}"
        )

    # ── 7. Admonitions (MkDocs Material) ──
    if len(src["admonitions"]) != len(trn["admonitions"]):
        issues.append(
            f"ADMONITIONS: source={len(src['admonitions'])}, "
            f"translated={len(trn['admonitions'])} "
            f"(Δ{len(trn['admonitions']) - len(src['admonitions']):+d})"
        )

    # ── 7b. Admonition empty line (Prettier-safe) ──
    # Each !!!/??? directive MUST be followed by an empty line before the
    # indented body.  Without it, Prettier strips the 4-space indent.
    _adm_re = re.compile(r'^(?:!!!|[?]{3})\s+\w+')
    tr_lines = translated_text.splitlines()
    bad_adm_lines = []
    for i, line in enumerate(tr_lines):
        if _adm_re.match(line):
            if i + 1 < len(tr_lines) and tr_lines[i + 1].strip() != '':
                if tr_lines[i + 1].startswith('    '):
                    bad_adm_lines.append(i + 1)
    if bad_adm_lines:
        issues.append(
            f"ADMONITION_EMPTY_LINE: {len(bad_adm_lines)} admonition(s) missing "
            f"empty line after directive (lines {bad_adm_lines}). "
            f"Add a blank line between the !!! directive and the indented body — "
            f"without it Prettier will strip the indentation and break the box."
        )

    # ── 8. Horizontal rules ──
    if src["hr_count"] != trn["hr_count"]:
        issues.append(
            f"HORIZONTAL_RULES: source={src['hr_count']}, "
            f"translated={trn['hr_count']} "
            f"(Δ{trn['hr_count'] - src['hr_count']:+d})"
        )

    # ── 9. Lists ──
    if src["bullet_count"] != trn["bullet_count"]:
        issues.append(
            f"BULLET_LIST: source={src['bullet_count']}, "
            f"translated={trn['bullet_count']} "
            f"(Δ{trn['bullet_count'] - src['bullet_count']:+d})"
        )
    if src["numbered_count"] != trn["numbered_count"]:
        issues.append(
            f"NUMBERED_LIST: source={src['numbered_count']}, "
            f"translated={trn['numbered_count']} "
            f"(Δ{trn['numbered_count'] - src['numbered_count']:+d})"
        )

    # ── 10. Tables ──
    if src["table_row_count"] != trn["table_row_count"]:
        issues.append(
            f"TABLE_ROWS: source={src['table_row_count']}, "
            f"translated={trn['table_row_count']} "
            f"(Δ{trn['table_row_count'] - src['table_row_count']:+d})"
        )

    # ── 11. Bold markers ──
    if src["bold_count"] != trn["bold_count"]:
        issues.append(
            f"BOLD_MARKERS: source={src['bold_count']}, "
            f"translated={trn['bold_count']} "
            f"(Δ{trn['bold_count'] - src['bold_count']:+d})"
        )

    # ── 12. Line count delta (info, not necessarily an issue) ──
    delta_lines = trn["line_count"] - src["line_count"]
    if abs(delta_lines) > max(3, src["line_count"] * 0.15):
        issues.append(
            f"LINE_COUNT: source={src['line_count']}, "
            f"translated={trn['line_count']} "
            f"(Δ{delta_lines:+d}, >{15}% difference)"
        )

    # ── 13. Source heading outline (for critic reference) ──
    info.append("SOURCE_OUTLINE (for reference):")
    for h in src["headings"]:
        indent = "  " * (h["level"] - 1)
        info.append(f"  {indent}{'#' * h['level']} {h['text']}")

    # ── Build report ──
    if not issues:
        return ""

    report_parts = [
        "## STRUCTURAL DIFF REPORT (source vs translation)",
        "",
        f"Issues found: {len(issues)}",
        "",
    ]
    for i, issue in enumerate(issues, 1):
        report_parts.append(f"{i}. {issue}")
    report_parts.append("")
    report_parts.extend(info)

    return "\n".join(report_parts)


def _structural_diff_report(source_path: Path, translated_path: Path) -> str:
    """
    Run structural diff between a source file and its translation.

    Convenience wrapper that reads files and returns the diff report.
    """
    source_text = source_path.read_text(encoding="utf-8")
    translated_text = translated_path.read_text(encoding="utf-8")
    return _structural_diff(source_text, translated_text)

def _estimate_tokens(char_count: int) -> dict:
    """
    Estimate token usage for a single file translation (4-step workflow).

    Rough model (OpenRouter / tiktoken averages):
      - 1 token ≈ 4 chars (English source)
      - Each step sends system prompt (~500 tok) + source + accumulated context
      - Step 1 Analyze:   in ≈ src,            out ≈ src*0.3
      - Step 3 Translate: in ≈ src*1.5,         out ≈ src
      - Step 4 Critique:  in ≈ src*2.5,         out ≈ src*0.5
      - Step 5 Refine:    in ≈ src*3.5,         out ≈ src
      - Total input  ≈ src * 8.5 + prompts(~2000)
      - Total output ≈ src * 2.8
    """
    src_tokens = max(char_count // 4, 1)
    prompt_overhead = 2000  # system prompts across 4 calls
    input_tokens = int(src_tokens * 8.5) + prompt_overhead
    output_tokens = int(src_tokens * 2.8)
    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens,
    }


def _format_tokens(total: int) -> str:
    """Format token count with K suffix."""
    if total >= 1000:
        return f"~{total / 1000:.1f}K tok"
    return f"~{total} tok"


# ---------------------------------------------------------------------------
# Translation logic — shared-analysis architecture
# ---------------------------------------------------------------------------

# Language name mapping for Aphra prompts
LANG_NAMES = {"it": "Italian", "fr": "French", "es": "Spanish"}

# Step timeouts (seconds) — configurable via .env
DEFAULT_STEP_TIMEOUT = 900  # 15 min — generous for large files on slow local models

# Rate limit retry defaults
DEFAULT_RATE_LIMIT_RETRIES = 5
DEFAULT_RATE_LIMIT_PAUSE = 90  # seconds between retries


class RateLimitError(Exception):
    """Raised when the LLM API returns HTTP 429 and all retries are exhausted."""
    pass


class AuthError(Exception):
    """Raised when the LLM API returns HTTP 401 (key disabled/invalid)."""
    pass


# ---------------------------------------------------------------------------
# Time formatting helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return current local time as HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def _format_elapsed(seconds: float) -> str:
    """Format elapsed time as human-readable string.

    Only shows units that are non-zero:
      42        → '42s'
      135       → '2m 15s'
      3723      → '1h 2m 3s'
    """
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _get_step_timeout() -> int:
    """Get per-step timeout in seconds from .env or default."""
    val = _load_env_var("APHRA_STEP_TIMEOUT", str(DEFAULT_STEP_TIMEOUT))
    try:
        return int(val)
    except ValueError:
        return DEFAULT_STEP_TIMEOUT


def _strip_think_blocks(text: str) -> str:
    """
    Strip <think>...</think> blocks from thinking-model output.

    Reasoning-distilled models (Qwen3.5-*-Reasoning, DeepSeek-R1, etc.)
    wrap their chain-of-thought in <think> blocks BEFORE the actual response.
    Aphra's XML parser does str.find() which can match tags inside <think>
    blocks or miss the real tags entirely.
    """
    if not text:
        return text
    # Remove all <think>...</think> blocks (greedy, may span many lines)
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()


def _apply_client_timeout(model_client) -> None:
    """
    Set HTTP-level timeout on the OpenAI client.

    This is the REAL timeout — when it fires, the HTTP connection is closed
    and Ollama actually stops generating. Unlike a threading timeout which
    just abandons the thread while the request keeps running.

    Uses httpx.Timeout with:
      - connect: 10s — fast fail if Ollama is not running
      - total: APHRA_STEP_TIMEOUT — per-request generation timeout
    """
    timeout_s = _get_step_timeout()
    try:
        import httpx
        model_client.client.timeout = httpx.Timeout(
            float(timeout_s),
            connect=10.0,
        )
    except ImportError:
        # httpx not available — fallback to simple float timeout
        model_client.client.timeout = float(timeout_s)


def _is_rate_limit_error(e: Exception) -> bool:
    """Check if an exception is a rate limit (HTTP 429) error."""
    err_type = type(e).__name__.lower()
    err_str = str(e).lower()
    return any(term in err_str or term in err_type
               for term in ('ratelimit', 'rate_limit', '429', 'rate limit', 'too many requests'))


def _call_step(func, *args, step_name: str, rate_limit_retries: int = DEFAULT_RATE_LIMIT_RETRIES, **kwargs):
    """
    Call an Aphra workflow step with proper error handling.

    Relies on the HTTP-level timeout set on the OpenAI client
    (_apply_client_timeout). When timeout fires, the connection is closed
    and Ollama stops generating.

    Rate limit (429) handling:
      - Pauses for APHRA_RATE_LIMIT_PAUSE seconds (default 90)
      - Retries up to rate_limit_retries times (default 5)
      - Shows countdown during pause
      - If all retries exhausted → raises RateLimitError

    Other errors:
      - Timeout → raises TimeoutError
      - Connection refused → raises ConnectionError
    """
    pause_s = int(_load_env_var("APHRA_RATE_LIMIT_PAUSE", str(DEFAULT_RATE_LIMIT_PAUSE)))

    for attempt in range(rate_limit_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # ── Auth error (401) — API key disabled/invalid, abort immediately ──
            err_str_raw = str(e)
            err_str = err_str_raw.lower()
            err_type = type(e).__name__

            if '401' in err_str or 'unauthorized' in err_str or 'user not found' in err_str or 'authenticationerror' in err_type.lower():
                raise AuthError(
                    f"{step_name}: API key invalid or disabled (HTTP 401).\n"
                    f"       OpenRouter sometimes disables keys (especially with free models).\n"
                    f"       To fix:\n"
                    f"         1. Go to https://openrouter.ai/workspaces/default/keys\n"
                    f"         2. Find your key — if disabled, click the 3 dots → Enable\n"
                    f"         3. Re-run the same command (progress is saved in cache)"
                ) from e

            # ── Rate limit (429) — pause and retry ──
            if _is_rate_limit_error(e):
                if attempt < rate_limit_retries:
                    remaining = rate_limit_retries - attempt
                    print(f"\n       🛑 Rate limit (429). "
                          f"Pausing {pause_s}s, then retry ({remaining} attempts left)...",
                          flush=True)
                    # Countdown display
                    for sec in range(pause_s, 0, -30):
                        time.sleep(min(30, sec))
                        if sec > 30:
                            print(f"          ⏳ {sec - 30}s...", flush=True)
                    print(f"       🔄 [{_now()}] Retry {step_name}...", end="", flush=True)
                    continue
                else:
                    raise RateLimitError(
                        f"{step_name}: rate limit hit (HTTP 429) after {rate_limit_retries} retries.\n"
                        f"       Progress is saved in cache — completed translations won't be redone.\n"
                        f"       Re-run the same command when the rate limit resets."
                    ) from e

            err_type = type(e).__name__
            err_str = str(e).lower()

            # ── Timeout (HTTP-level — connection was actually closed) ──
            if 'timeout' in err_type.lower() or 'timeout' in err_str or 'timed out' in err_str:
                timeout_s = _get_step_timeout()
                raise TimeoutError(
                    f"{step_name} timed out after {timeout_s}s. "
                    f"The request was cancelled and the model stopped. "
                    f"Set APHRA_STEP_TIMEOUT in .env to increase (current: {timeout_s}s)."
                ) from e

            # ── Connection refused (Ollama not running) ──
            if any(term in err_str for term in ('connect', 'refused', 'unreachable', 'no route')):
                base_url = _get_base_url() or DEFAULT_OLLAMA_URL
                ollama_url = base_url.replace("/v1", "")
                raise ConnectionError(
                    f"{step_name}: cannot connect to LLM backend at {base_url}.\n"
                    f"       Is Ollama running? Start it with:\n"
                    f"         ollama serve\n"
                    f"       Then verify with: curl {ollama_url}/api/tags"
                ) from e

            # ── Other errors — re-raise as-is ──
            raise


def _robust_refine(workflow, context, source_text: str, *,
                   translation: str, glossary: str, critique: str,
                   max_retries: int = 2) -> str:
    """
    Step 5 Refine with retry and fallback parsing.

    Problems this solves:
    1. Model doesn't output <improved_translation> tags → retry
    2. Model wraps output in <think> blocks → stripped by patched call_model
    3. Transient model failures → retry up to max_retries

    Returns translated text, or empty string on total failure.
    """
    for attempt in range(max_retries + 1):
        try:
            raw_output = _call_step(
                workflow.refine, context, source_text,
                translation=translation, glossary=glossary, critique=critique,
                step_name="Refine",
            )
        except TimeoutError as e:
            print(f"\n       ⏱️  {e}", file=sys.stderr)
            if attempt < max_retries:
                print(f"       🔄 Retry {attempt + 1}/{max_retries}...", flush=True)
                continue
            return ""
        except (ConnectionError, RateLimitError, AuthError):
            raise  # Propagate up — pipeline will abort
        except Exception as e:
            print(f"\n       ❌ Refine error: {e}", file=sys.stderr)
            if attempt < max_retries:
                print(f"       🔄 Retry {attempt + 1}/{max_retries}...", flush=True)
                continue
            return ""

        # If workflow.refine() returned non-empty, it already parsed OK
        if raw_output:
            return raw_output

        # Aphra's refine() calls parse_translation() internally, which returns ""
        # on parse failure. We can't access the raw LLM output from here.
        # Log and retry — next attempt the model may produce valid XML.
        if attempt < max_retries:
            print(f"\n       ⚠️  Refine returned empty (parse failure), retry {attempt + 1}/{max_retries}...",
                  end="", flush=True)
            continue

    return ""


def _create_model_client(api_key: str, models: dict):
    """Create an Aphra LLMModelClient, patching base_url for local backends.

    Also:
    - Sets HTTP-level timeout (so Ollama actually stops on timeout)
    - Wraps call_model() to strip <think> blocks from reasoning models
    """
    from aphra.core.llm_client import LLMModelClient

    _generate_config_toml(api_key, models)
    model_client = LLMModelClient(str(CONFIG_TOML))

    custom_base_url = _get_base_url()
    if custom_base_url:
        model_client.client.base_url = custom_base_url

    # Set HTTP-level timeout — closes connection on timeout, stopping Ollama
    _apply_client_timeout(model_client)

    # Wrap call_model to strip <think> blocks from output
    original_call = model_client.call_model

    def _patched_call(*args, **kwargs):
        result = original_call(*args, **kwargs)
        if result and '<think>' in result:
            result = _strip_think_blocks(result)
        return result

    model_client.call_model = _patched_call

    return model_client


def _analyze_source(source_text: str, model_client, models: dict):
    """
    Step 1 — Analyze: identify key terms, entities, expressions.

    This step is language-INDEPENDENT (it analyzes the English source)
    so its result can be shared across all target languages.

    Returns (workflow, workflow_config, analysis_text) or raises on error.
    """
    from aphra.core.context import TranslationContext
    from aphra.core.registry import get_suitable_workflow

    workflow = get_suitable_workflow(source_text)
    if workflow is None:
        raise ValueError("No suitable Aphra workflow for this content")

    workflow_config = workflow.load_config(global_config_path=str(CONFIG_TOML))

    # Use analyzer model (reasoning) for analysis step
    workflow_config['writer'] = models['analyzer']

    context = TranslationContext(
        model_client=model_client,
        source_language="English",
        target_language="multilingual",
        log_calls=False,
    )
    context.set_workflow_config(workflow_config)

    analysis = _call_step(workflow.analyze, context, source_text, step_name="Analyze")
    return workflow, workflow_config, analysis


def _translate_one_lang(
    source_text: str, source_path: Path, target_lang: str,
    workflow, workflow_config: dict, model_client, models: dict,
    analysis: str,
) -> dict:
    """
    Steps 2-5 for ONE target language: Search → Translate → Critique → Refine.

    Uses writer model (generation) for Translate+Refine and
    critiquer model (reasoning) for Critique.

    Returns dict with translation artifacts:
        output_path:      Path | None — output file (None on failure)
        critique:         str — Step 4 critic output
        structural_diff:  str — Step 3.5 structural diff report
        structural_issues: int — number of structural anomalies found
        models:           dict — {"writer": ..., "critiquer": ...} used
    """
    from aphra.core.context import TranslationContext

    output_name = source_path.name.replace(".en.md", f".{target_lang}.md")
    output_path = source_path.parent / output_name
    target_name = LANG_NAMES.get(target_lang, target_lang)

    # Track which models were actually used
    used_models = {
        "writer": models["writer"],
        "critiquer": models["critiquer"],
    }

    # Initialize result dict (returned on both success and failure)
    result = {
        "output_path": None,
        "critique": "",
        "structural_diff": "",
        "structural_issues": 0,
        "models": used_models,
    }

    context = TranslationContext(
        model_client=model_client,
        source_language="English",
        target_language=target_name,
        log_calls=False,
    )
    context.set_workflow_config(workflow_config)

    web_search = _load_env_var("APHRA_WEB_SEARCH", "false").lower() in ("true", "1", "yes")

    # Step 2: Search (optional)
    if web_search:
        t1 = time.time()
        print(f"       [2/5] 🔍 Search    ... ", end="", flush=True)
        glossary = workflow.search(context, analysis)
        print(f"({time.time() - t1:.0f}s)", flush=True)
    else:
        glossary = ""
        print(f"       [2/5] 🔍 Search    ... skipped", flush=True)

    # Step 3: Translate (writer model — generation)
    workflow_config['writer'] = models['writer']
    t2 = time.time()
    print(f"       [3/5] 🌐 Translate ... ", end="", flush=True)
    try:
        translation = _call_step(
            workflow.translate, context, source_text,
            step_name="Translate",
        )
    except (RateLimitError, AuthError):
        raise  # Propagate up — pipeline will abort
    except (TimeoutError, ConnectionError) as e:
        print(f"\n       ⏱️  {e}", file=sys.stderr)
        return result
    print(f"({time.time() - t2:.0f}s)", flush=True)

    if not translation:
        print(f"       ⚠️  Translate returned empty", file=sys.stderr)
        return result

    # Step 3.5: Structural diff (fast, no LLM — objective comparison)
    struct_diff = _structural_diff(source_text, translation)
    struct_issues = 0
    if struct_diff:
        # Prepend structural analysis to glossary so the critic sees it
        glossary_with_diff = (
            f"{struct_diff}\n\n---\n\n{glossary}" if glossary
            else struct_diff
        )
        struct_issues = sum(1 for line in struct_diff.splitlines()
                            if re.match(r'^\d+\.', line.strip()))
        print(f"       [3.5]  📐 StructDiff ... {struct_issues} issue{'s' if struct_issues != 1 else ''}", flush=True)
    else:
        glossary_with_diff = glossary
        print(f"       [3.5]  📐 StructDiff ... clean ✓", flush=True)

    # Step 4: Critique (critiquer model — reasoning)
    t3 = time.time()
    print(f"       [4/5] 🔎 Critique  ... ", end="", flush=True)
    try:
        critique = _call_step(
            workflow.critique, context, source_text, translation, glossary_with_diff,
            step_name="Critique",
        )
    except (RateLimitError, AuthError):
        raise  # Propagate up — pipeline will abort
    except TimeoutError as e:
        print(f"\n       ⏱️  {e}", file=sys.stderr)
        # Critique timeout → skip critique, refine with what we have
        critique = "(Critique timed out — refining without critique feedback)"
        print(f"       ⚠️  Continuing without critique...", flush=True)
    except ConnectionError as e:
        print(f"\n       ❌ {e}", file=sys.stderr)
        return result
    print(f"({time.time() - t3:.0f}s)", flush=True)

    # Step 5: Refine (writer model — generation, with retry + timeout)
    t4 = time.time()
    print(f"       [5/5] ✨ Refine    ... ", end="", flush=True)
    translated = _robust_refine(
        workflow, context, source_text,
        translation=translation, glossary=glossary, critique=critique,
    )
    print(f"({time.time() - t4:.0f}s)", flush=True)

    # Update result with collected artifacts
    result["critique"] = critique or ""
    result["structural_diff"] = struct_diff or ""
    result["structural_issues"] = struct_issues

    if translated:
        translated = _clean_translation(translated)
        output_path.write_text(translated, encoding="utf-8")
        result["output_path"] = output_path
    else:
        print(f"  ⚠️  Empty translation for {source_path.name} → {target_lang}", file=sys.stderr)

    return result


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_translate(args) -> int:
    """Main translation logic."""
    global DEFAULT_RATE_LIMIT_RETRIES  # noqa: PLW0603
    target_langs = args.lang or _detect_target_languages()
    force = getattr(args, "force", False)
    dry_run = getattr(args, "dry_run", False)
    file_filter = getattr(args, "file", None)

    # Apply CLI overrides
    cli_retries = getattr(args, "rate_limit_retries", None)
    if cli_retries is not None:
        DEFAULT_RATE_LIMIT_RETRIES = cli_retries

    # Build list of (cache_key, source_path) tuples
    # - From nav: cache_key is relative to docs/, source_path = DOCS_DIR / rel
    # - From --file: resolve path from CWD or absolute, save next to source
    if file_filter:
        sources = []
        # Expand glob patterns and collect resolved paths
        resolved_paths: list[Path] = []
        for f in file_filter:
            # Try glob expansion in CWD first, then in docs/
            cwd_matches = sorted(glob.glob(f, recursive=True))
            docs_matches = sorted(glob.glob(str(DOCS_DIR / f), recursive=True))
            if cwd_matches:
                resolved_paths.extend(Path(m).resolve() for m in cwd_matches)
            elif docs_matches:
                resolved_paths.extend(Path(m).resolve() for m in docs_matches)
            elif '*' in f or '?' in f or '[' in f:
                # Glob pattern that matched nothing
                print(f"  ⚠️  No files matching glob: {f}", file=sys.stderr)
                print(f"       (searched CWD: {Path.cwd() / f})", file=sys.stderr)
                print(f"       (searched docs: {DOCS_DIR / f})", file=sys.stderr)
            else:
                # Not a glob — try as literal path
                p = Path(f)
                if p.is_absolute():
                    p = p.resolve()
                else:
                    cwd_path = (Path.cwd() / p).resolve()
                    docs_path = (DOCS_DIR / p).resolve()
                    if cwd_path.exists():
                        p = cwd_path
                    elif docs_path.exists():
                        p = docs_path
                    else:
                        print(f"  ⚠️  File not found: {f}", file=sys.stderr)
                        print(f"       (searched: {cwd_path})", file=sys.stderr)
                        print(f"       (searched: {docs_path})", file=sys.stderr)
                        continue
                if not p.exists():
                    print(f"  ⚠️  File not found: {p}", file=sys.stderr)
                    continue
                resolved_paths.append(p)

        # Deduplicate and filter to .en.md files only
        seen: set[Path] = set()
        for p in resolved_paths:
            if p in seen:
                continue
            seen.add(p)
            if not p.name.endswith('.en.md'):
                continue  # skip non-source files silently
            # Cache key: relative to docs/ when possible, otherwise filename
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

    # Load hash cache
    hashes = _load_hashes()

    # Build translation plan
    plan = []  # list of (cache_key, source_path, target_lang)
    for cache_key, source_path in sources:
        if not source_path.exists():
            print(f"  ⚠️  Source not found: {cache_key}", file=sys.stderr)
            continue

        current_md5 = _file_md5(source_path)
        cached = hashes.get(cache_key, {})
        cached_md5 = cached.get("md5", "")
        cached_langs = set(cached.get("langs_done", []))

        for lang in target_langs:
            if not force and current_md5 == cached_md5 and lang in cached_langs:
                continue  # Skip — unchanged and already translated
            plan.append((cache_key, source_path, lang))

    if not plan:
        print("✅ All files are up-to-date. Nothing to translate.")
        return 0

    # Show plan
    print(f"\n📋 Translation Plan: {len(plan)} file(s) × language(s)")
    print(f"   Target languages: {', '.join(target_langs)}")
    print(f"   Source files: {len(sources)}")
    print(f"   Cache: {HASH_FILE}")
    print()

    for cache_key, source_path, lang in plan:
        est = _estimate_tokens(source_path.stat().st_size)
        print(f"  • {cache_key} → {lang}  ({_format_tokens(est['total'])})")

    if dry_run:
        # Total token estimate
        total_est = {"input": 0, "output": 0, "total": 0}
        for _, source_path, _ in plan:
            est = _estimate_tokens(source_path.stat().st_size)
            total_est["input"] += est["input"]
            total_est["output"] += est["output"]
            total_est["total"] += est["total"]

        print(f"\n📊 Estimated tokens: {_format_tokens(total_est['total'])} "
              f"(in: {_format_tokens(total_est['input'])}, out: {_format_tokens(total_est['output'])})")
        print(f"🔍 Dry run — no files translated.")
        return 0

    # Load API key and models
    api_key = _load_api_key()
    models = _load_models()

    print(f"\n🚀 [{_now()}] Starting translation...")
    local = _is_local_mode()
    base_url = _get_base_url()
    backend_label = f"🏠 Local ({base_url})" if local else "☁️  OpenRouter"
    print(f"   Backend: {backend_label}")
    unique_models = set(models.values())
    if len(unique_models) == 1:
        print(f"   Model: {models['writer']}")
    else:
        print(f"   Analyzer:  {models['analyzer']}  (analyze + critique)")
        print(f"   Writer:    {models['writer']}  (translate + refine)")
        if models['searcher'] not in (models['writer'], models['analyzer']):
            print(f"   Searcher:  {models['searcher']}")
    web_search = _load_env_var("APHRA_WEB_SEARCH", "false").lower() in ("true", "1", "yes")
    print(f"   Web search: {'ON' if web_search else 'OFF (skipped)'}")
    timeout_s = _get_step_timeout()
    print(f"   Step timeout: {_format_elapsed(timeout_s)}")
    print(f"   Rate limit: {DEFAULT_RATE_LIMIT_RETRIES} retries, {DEFAULT_RATE_LIMIT_PAUSE}s pause")
    print(f"   Cache: {HASH_FILE}")
    print()

    # ── Group plan by source file for shared analysis ──
    from collections import OrderedDict
    file_groups: OrderedDict[tuple[str, Path], list[str]] = OrderedDict()
    for cache_key, source_path, lang in plan:
        key = (cache_key, source_path)
        if key not in file_groups:
            file_groups[key] = []
        file_groups[key].append(lang)

    success_count = 0
    fail_count = 0
    total_tokens_est = 0
    translation_idx = 0
    t_total = time.time()

    try:
        model_client = _create_model_client(api_key, models)

        for file_idx, ((cache_key, source_path), langs) in enumerate(file_groups.items(), 1):
            source_text = source_path.read_text(encoding="utf-8")
            langs_label = ", ".join(langs)
            print(f"  📄 [{_now()}] [{file_idx}/{len(file_groups)}] {cache_key} → {langs_label}")

            # ── Step 1: Analyze ONCE (shared across all target languages) ──
            t0 = time.time()
            print(f"     [1/5] 📝 Analyze   ... ", end="", flush=True)
            try:
                workflow, workflow_config, analysis = _analyze_source(
                    source_text, model_client, models,
                )
                analysis_elapsed = time.time() - t0
                print(f"({_format_elapsed(analysis_elapsed)}) [{models['analyzer'].split('/')[-1]}]", flush=True)
            except ConnectionError as e:
                print(f"\n     ❌ {e}", file=sys.stderr)
                fail_count += sum(len(v) for v in file_groups.values())  # all remaining
                break  # Ollama is down — stop everything
            except (RateLimitError, AuthError) as e:
                print(f"\n     🛑 {e}", file=sys.stderr)
                fail_count += sum(len(v) for v in file_groups.values())
                break  # Rate limit or auth error — stop, re-run later
            except Exception as e:
                print(f"\n     ❌ Analyze failed: {e}", file=sys.stderr)
                fail_count += len(langs)
                continue

            # Save analysis in hash cache (shared across languages)
            current_md5 = _file_md5(source_path)
            if cache_key not in hashes:
                hashes[cache_key] = {"md5": current_md5, "langs_done": [], "last_translated": ""}
            hashes[cache_key]["md5"] = current_md5
            # Serialize analysis: it's a list of dicts from Aphra's parse_analysis()
            try:
                analysis_serialized = json.dumps(analysis, ensure_ascii=False) if not isinstance(analysis, str) else analysis
            except (TypeError, ValueError):
                analysis_serialized = str(analysis)
            hashes[cache_key]["analysis"] = analysis_serialized
            hashes[cache_key]["analysis_model"] = models["analyzer"]
            if "langs" not in hashes[cache_key]:
                hashes[cache_key]["langs"] = {}
            _save_hashes(hashes)

            # ── Steps 2-5: per language ──
            rate_limited = False
            for lang in langs:
                translation_idx += 1
                target_label = LANG_NAMES.get(lang, lang)
                print(f"\n     🌐 [{_now()}] [{translation_idx}/{len(plan)}] → {target_label} ({lang})")
                start = time.time()

                try:
                    result = _translate_one_lang(
                        source_text=source_text,
                        source_path=source_path,
                        target_lang=lang,
                        workflow=workflow,
                        workflow_config=workflow_config,
                        model_client=model_client,
                        models=models,
                        analysis=analysis,
                    )
                except (RateLimitError, AuthError) as e:
                    print(f"\n     🛑 {e}", file=sys.stderr)
                    result = {"output_path": None}
                    rate_limited = True
                    fail_count += 1
                    break  # Stop this file's languages
                except Exception as e:
                    result = {"output_path": None}
                    print(f"\n     ❌ Error: {e}", file=sys.stderr)

                output_path = result.get("output_path")

                if output_path:
                    elapsed = time.time() - start
                    est = _estimate_tokens(source_path.stat().st_size)
                    total_tokens_est += est["total"]
                    print(f"     ✅ [{_now()}] Done ({_format_elapsed(elapsed)}, {_format_tokens(est['total'])}) → {output_path}")
                    success_count += 1

                    # Update hash cache — backward-compat fields
                    current_md5 = _file_md5(source_path)
                    hashes[cache_key]["md5"] = current_md5
                    if lang not in hashes[cache_key].get("langs_done", []):
                        hashes[cache_key].setdefault("langs_done", []).append(lang)
                    hashes[cache_key]["last_translated"] = datetime.now(timezone.utc).isoformat()

                    # Save per-language artifacts
                    if "langs" not in hashes[cache_key]:
                        hashes[cache_key]["langs"] = {}
                    hashes[cache_key]["langs"][lang] = {
                        "translated_at": datetime.now(timezone.utc).isoformat(),
                        "models": result.get("models", {}),
                        "critique": result.get("critique", ""),
                        "structural_diff": result.get("structural_diff", ""),
                        "structural_issues": result.get("structural_issues", 0),
                        "elapsed_s": round(elapsed, 1),
                    }
                    _save_hashes(hashes)
                else:
                    fail_count += 1
                    print("     ❌ Failed")

                    # Save failure info too (useful for debugging)
                    if "langs" not in hashes[cache_key]:
                        hashes[cache_key]["langs"] = {}
                    hashes[cache_key]["langs"][lang] = {
                        "translated_at": datetime.now(timezone.utc).isoformat(),
                        "models": result.get("models", {}),
                        "critique": result.get("critique", ""),
                        "structural_diff": result.get("structural_diff", ""),
                        "structural_issues": result.get("structural_issues", 0),
                        "failed": True,
                    }
                    _save_hashes(hashes)

            if rate_limited:
                break  # Stop all files — rate limit hit

    finally:
        _cleanup_config_toml()

    # Summary
    total_elapsed = time.time() - t_total

    print(f"\n{'=' * 50}")
    print(f"✅ Translated: {success_count}  |  ❌ Failed: {fail_count}  |  Total: {len(plan)}")
    print(f"⏱️  Total time: {_format_elapsed(total_elapsed)}")
    print(f"📊 Estimated tokens: {_format_tokens(total_tokens_est)}")
    if fail_count:
        print(f"⚠️  Re-run to retry failed translations.")
    print()

    return 1 if fail_count else 0


# ---------------------------------------------------------------------------
# Check / diagnostics
# ---------------------------------------------------------------------------

def run_check(args) -> int:
    """
    Verify that the translation pipeline is correctly set up.

    Checks:
      1. Aphra importable (dev dependency installed)
      2. .env file exists with OPENROUTER_API_KEY
      3. Target languages detected from frontend
      4. Translatable files detected from mkdocs.yml nav
      5. Quick API connectivity test (OpenRouter /models endpoint)
    """
    ok = True
    local = _is_local_mode()
    base_url = _get_base_url()

    # ── 1. Aphra import ──
    print("1️⃣  Aphra module ...", end=" ", flush=True)
    try:
        from aphra import translate as _  # noqa: F401
        print("✅ importabile")
    except ImportError:
        print("❌ NON trovato")
        print("   ➜  Installa con: pipenv install --dev 'git+https://github.com/DavidLMS/aphra.git#egg=aphra'")
        ok = False

    # ── 2. Backend + API key ──
    if local:
        print(f"2️⃣  Backend ...", end=" ", flush=True)
        print(f"✅ 🏠 Locale ({base_url})")
    else:
        print("2️⃣  .env + API key ...", end=" ", flush=True)
        if not ENV_FILE.exists():
            print(f"❌ {ENV_FILE} non trovato")
            print(f"   ➜  Copia da .env.example e aggiungi la tua chiave OpenRouter")
            ok = False
        else:
            try:
                api_key = _load_api_key()
                masked = api_key[:12] + "..." + api_key[-4:]
                print(f"✅ trovata ({masked})")
            except SystemExit:
                print("❌ OPENROUTER_API_KEY non trovata nel file .env")
                ok = False

    # ── 3. Models ──
    print("3️⃣  Modelli LLM ...", end=" ", flush=True)
    models = _load_models()
    if len(set(models.values())) == 1:
        # All roles use the same model
        m = models['writer']
        src = "(default)" if m == DEFAULT_APHRA_MODEL else "(da .env)"
        print(f"✅ {m} {src}")
    else:
        print("✅ (per-ruolo)")
        for role, m in models.items():
            src = "(default)" if m == DEFAULT_APHRA_MODEL else "(da .env)"
            print(f"     {role:10s} → {m} {src}")

    # ── 4. Web search ──
    print("4️⃣  Web search ...", end=" ", flush=True)
    web_search = _load_env_var("APHRA_WEB_SEARCH", "false").lower() in ("true", "1", "yes")
    if web_search:
        print("🟡 ATTIVO (Step 2 Search con costi aggiuntivi)")
    else:
        print("✅ disattivato (step 2 Search → skipped)")

    # ── 5. Target languages ──
    print("5️⃣  Lingue target ...", end=" ", flush=True)
    langs = _detect_target_languages()
    print(f"✅ {langs}")

    # ── 6. Translatable files ──
    print("6️⃣  File traducibili ...", end=" ", flush=True)
    try:
        files = get_translatable_files()
        print(f"✅ {len(files)} file trovati")
        for f in files:
            print(f"     • {f}")
    except Exception as e:
        print(f"❌ errore: {e}")
        ok = False

    # ── 7. Hash cache ──
    print("7️⃣  Cache traduzioni ...", end=" ", flush=True)
    hashes = _load_hashes()
    if hashes:
        done = sum(1 for v in hashes.values() if v.get("langs_done"))
        print(f"✅ {done}/{len(hashes)} file con traduzioni cached")
    else:
        print("ℹ️  vuota (prima esecuzione)")

    # ── 8. API connectivity ──
    if local:
        print("8️⃣  Ollama server ...", end=" ", flush=True)
        try:
            import urllib.request
            import urllib.error
            # Ollama health check (strip /v1 to get base Ollama URL)
            ollama_url = base_url.replace("/v1", "") if base_url else DEFAULT_OLLAMA_URL.replace("/v1", "")
            req = urllib.request.Request(f"{ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    import json as _json
                    data = _json.loads(resp.read())
                    model_names = [m.get("name", "?") for m in data.get("models", [])]
                    print(f"✅ connesso — {len(model_names)} modelli disponibili")
                    # Check if configured model is available
                    configured = models['writer']
                    found = any(configured in n or n.startswith(configured.split(":")[0]) for n in model_names)
                    if not found:
                        print(f"     ⚠️  Modello '{configured}' non trovato in Ollama")
                        print(f"     Modelli disponibili: {', '.join(model_names[:5])}")
                else:
                    print(f"⚠️  status {resp.status}")
        except Exception as e:
            print(f"❌ Ollama non raggiungibile: {e}")
            print(f"   ➜  Avvia Ollama con: ollama serve")
            ok = False
    else:
        print("8️⃣  OpenRouter API ...", end=" ", flush=True)
        if ok:  # only if we have an API key
            try:
                import urllib.request
                import urllib.error
                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        print("✅ connessione OK")
                    else:
                        print(f"⚠️  status {resp.status}")
            except urllib.error.HTTPError as e:
                print(f"❌ HTTP {e.code} — chiave non valida?")
                ok = False
            except Exception as e:
                print(f"⚠️  errore di rete: {e}")
        else:
            print("⏭️  saltato (fix errori precedenti)")

    # ── Summary ──
    print()
    if ok:
        print("✅ Pipeline pronta! Puoi lanciare:")
        print("   ./dev.py mkdocs translate --dry-run")
    else:
        print("❌ Ci sono problemi da risolvere (vedi sopra)")

    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Structural diff — standalone command
# ---------------------------------------------------------------------------

def run_diff(args) -> int:
    """
    Run structural diff between EN source files and their translations.

    Compares markdown structure (headings, code blocks, links, lists, etc.)
    and reports anomalies. No LLM required — pure text analysis.
    """
    target_langs = args.lang or _detect_target_languages()
    file_filter = getattr(args, "file", None)
    verbose = getattr(args, "verbose", False)

    # Build list of source files (reuse same logic as run_translate)
    if file_filter:
        sources = []
        resolved_paths: list[Path] = []
        for f in file_filter:
            cwd_matches = sorted(glob.glob(f, recursive=True))
            docs_matches = sorted(glob.glob(str(DOCS_DIR / f), recursive=True))
            if cwd_matches:
                resolved_paths.extend(Path(m).resolve() for m in cwd_matches)
            elif docs_matches:
                resolved_paths.extend(Path(m).resolve() for m in docs_matches)
            else:
                p = Path(f)
                if not p.is_absolute():
                    cwd_path = (Path.cwd() / p).resolve()
                    docs_path = (DOCS_DIR / p).resolve()
                    p = cwd_path if cwd_path.exists() else docs_path
                if p.exists():
                    resolved_paths.append(p.resolve())
                else:
                    print(f"  ⚠️  File not found: {f}", file=sys.stderr)

        seen: set[Path] = set()
        for p in resolved_paths:
            if p in seen:
                continue
            seen.add(p)
            if not p.name.endswith('.en.md'):
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
        print("No source files found.")
        return 0

    total_issues = 0
    files_checked = 0
    files_with_issues = 0

    print(f"\n📐 Structural Diff: {len(sources)} source file(s) × {len(target_langs)} language(s)")
    print(f"   Languages: {', '.join(target_langs)}\n")

    for cache_key, source_path in sources:
        if not source_path.exists():
            continue

        for lang in target_langs:
            translated_name = source_path.name.replace(".en.md", f".{lang}.md")
            translated_path = source_path.parent / translated_name

            if not translated_path.exists():
                if verbose:
                    print(f"  ⏭️  {cache_key} → {lang}: translation not found")
                continue

            files_checked += 1
            report = _structural_diff_report(source_path, translated_path)

            if report:
                files_with_issues += 1
                issue_count = sum(1 for line in report.splitlines()
                                  if re.match(r'^\d+\.', line.strip()))
                total_issues += issue_count
                print(f"  ⚠️  {cache_key} → {lang}  ({issue_count} issue{'s' if issue_count != 1 else ''})")
                if verbose:
                    for line in report.splitlines():
                        print(f"       {line}")
                    print()
            else:
                print(f"  ✅ {cache_key} → {lang}")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"📊 Files checked: {files_checked}")
    print(f"✅ Clean: {files_checked - files_with_issues}")
    print(f"⚠️  With issues: {files_with_issues}  ({total_issues} total anomalies)")
    if files_with_issues and not verbose:
        print(f"\n💡 Run with --verbose to see detailed reports.")
    print()

    return 1 if files_with_issues else 0


# ---------------------------------------------------------------------------
# Inspect — view saved artifacts from hash cache
# ---------------------------------------------------------------------------

def run_inspect(args) -> int:
    """
    Inspect saved translation artifacts (analysis, critique, structural diff).

    Shows what was saved for each file and language, including:
    - Analysis output (shared across languages)
    - Critique text per language
    - Structural diff per language
    - Models used and timing
    """
    hashes = _load_hashes()
    if not hashes:
        print("ℹ️  No translation cache found. Run 'translate' first.")
        return 0

    file_filter = getattr(args, "file", None)
    lang_filter = getattr(args, "lang", None)
    show_critique = getattr(args, "critique", False)
    show_analysis = getattr(args, "analysis", False)
    show_diff = getattr(args, "diff", False)
    show_all = not (show_critique or show_analysis or show_diff)

    print(f"\n🔍 Translation Artifacts Inspector")
    print(f"   Cache: {HASH_FILE}")
    print(f"   Entries: {len(hashes)}\n")

    for cache_key, entry in hashes.items():
        # Filter by file if specified
        if file_filter:
            if not any(f in cache_key for f in file_filter):
                continue

        md5 = entry.get("md5", "?")[:8]
        langs_done = entry.get("langs_done", [])
        last = entry.get("last_translated", "?")
        if last and last != "?":
            last = last[:19]  # trim to datetime without microseconds

        print(f"  📄 {cache_key}")
        print(f"     md5: {md5}...  |  langs: {', '.join(langs_done)}  |  last: {last}")

        # Analysis
        analysis_text = entry.get("analysis", "")
        analysis_model = entry.get("analysis_model", "")
        if analysis_text:
            # Truncate for display unless --analysis flag
            if show_all or show_analysis:
                preview = analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text
                print(f"     📝 Analysis ({analysis_model}): {preview}")
        else:
            print(f"     📝 Analysis: not saved (pre-v2 translation)")

        # Per-language details
        langs_data = entry.get("langs", {})
        for lang, lang_info in langs_data.items():
            if lang_filter and lang not in lang_filter:
                continue

            at = lang_info.get("translated_at", "?")[:19]
            models = lang_info.get("models", {})
            elapsed = lang_info.get("elapsed_s", 0)
            failed = lang_info.get("failed", False)
            struct_issues = lang_info.get("structural_issues", 0)
            migrated = lang_info.get("migrated_from_v1", False)

            status = "❌ FAILED" if failed else "✅"
            model_label = models.get("writer", "?").split("/")[-1] if models else "?"
            print(f"\n     🌐 {lang} {status}  ({at}, {elapsed:.0f}s, model: {model_label})")

            if migrated:
                print(f"        ℹ️  Migrated from v1 cache — no artifacts saved")
                continue

            # Structural diff
            if show_all or show_diff:
                diff_text = lang_info.get("structural_diff", "")
                if diff_text:
                    print(f"        📐 Structural issues: {struct_issues}")
                    for line in diff_text.splitlines()[:10]:
                        print(f"           {line}")
                    if len(diff_text.splitlines()) > 10:
                        print(f"           ... ({len(diff_text.splitlines()) - 10} more lines)")
                else:
                    print(f"        📐 Structural diff: clean ✓")

            # Critique
            if show_all or show_critique:
                critique = lang_info.get("critique", "")
                if critique:
                    preview = critique[:300] + "..." if len(critique) > 300 else critique
                    # Indent critique text
                    lines = preview.splitlines()
                    print(f"        🔎 Critique:")
                    for line in lines[:8]:
                        print(f"           {line}")
                    if len(lines) > 8:
                        print(f"           ... ({len(critique)} chars total)")
                else:
                    print(f"        🔎 Critique: not saved")

        print()

    return 0


# ---------------------------------------------------------------------------
# CLI / dev.py integration
# ---------------------------------------------------------------------------

def _add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add translate-specific arguments to a parser."""
    target_langs = _detect_target_languages()

    parser.add_argument("--lang", action="extend", nargs="+", choices=target_langs, metavar="LANG", help=f"Target language(s). Detected from frontend: {target_langs}", )
    parser.add_argument("--file", action="extend", nargs="+", metavar="PATH", help="File(s) or glob pattern(s) to translate (e.g. faq.en.md, user/*.en.md, 'user/**/*.en.md')", )
    parser.add_argument("--force", action="store_true", help="Re-translate all files (ignore MD5 cache)", )
    parser.add_argument("--dry-run", action="store_true", help="Show plan without translating", )
    parser.add_argument("--rate-limit-retries", type=int, default=DEFAULT_RATE_LIMIT_RETRIES, metavar="N", help=f"Max retries on rate limit (429), with {DEFAULT_RATE_LIMIT_PAUSE}s pause between (default: {DEFAULT_RATE_LIMIT_RETRIES})", )


def _add_diff_arguments(parser: argparse.ArgumentParser) -> None:
    """Add translate-diff-specific arguments to a parser."""
    target_langs = _detect_target_languages()

    parser.add_argument("--lang", action="extend", nargs="+", choices=target_langs, metavar="LANG", help=f"Target language(s). Detected from frontend: {target_langs}", )
    parser.add_argument("--file", action="extend", nargs="+", metavar="PATH", help="File(s) or glob pattern(s) to check (e.g. faq.en.md, 'user/**/*.en.md')", )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed structural diff reports", )


def _add_inspect_arguments(parser: argparse.ArgumentParser) -> None:
    """Add translate-inspect-specific arguments to a parser."""
    target_langs = _detect_target_languages()

    parser.add_argument("--lang", action="extend", nargs="+", choices=target_langs, metavar="LANG", help=f"Filter by language(s)", )
    parser.add_argument("--file", action="extend", nargs="+", metavar="PATH", help="Filter by file name (substring match)", )
    parser.add_argument("--critique", action="store_true", help="Show only critique artifacts", )
    parser.add_argument("--analysis", action="store_true", help="Show only analysis artifacts", )
    parser.add_argument("--diff", action="store_true", help="Show only structural diff artifacts", )


def register_subparser(mk_sub) -> None:
    """Register sub-commands under 'mkdocs' in dev.py."""
    # translate
    mk_p = mk_sub.add_parser("translate", help="Translate docs via Aphra (LLM agent)")
    _add_arguments(mk_p)
    mk_p.set_defaults(func=run_translate)

    # translate-check
    chk_p = mk_sub.add_parser("translate-check", help="Check translation pipeline setup")
    chk_p.set_defaults(func=run_check)

    # translate-diff
    diff_p = mk_sub.add_parser("translate-diff", help="Structural diff: compare EN vs translated files")
    _add_diff_arguments(diff_p)
    diff_p.set_defaults(func=run_diff)

    # translate-inspect
    ins_p = mk_sub.add_parser("translate-inspect", help="Inspect saved translation artifacts (analysis, critique, diff)")
    _add_inspect_arguments(ins_p)
    ins_p.set_defaults(func=run_inspect)


def main():
    """Standalone CLI entry point."""
    parser = argparse.ArgumentParser(description="Translate MkDocs documentation using Aphra (LLM agent)", )
    sub = parser.add_subparsers(dest="command")

    # translate (default)
    tr_p = sub.add_parser("translate", help="Run translation")
    _add_arguments(tr_p)
    tr_p.set_defaults(func=run_translate)

    # check
    chk_p = sub.add_parser("check", help="Check pipeline setup")
    chk_p.set_defaults(func=run_check)

    # diff
    diff_p = sub.add_parser("diff", help="Structural diff: compare EN vs translated files")
    _add_diff_arguments(diff_p)
    diff_p.set_defaults(func=run_diff)

    # inspect
    ins_p = sub.add_parser("inspect", help="Inspect saved translation artifacts")
    _add_inspect_arguments(ins_p)
    ins_p.set_defaults(func=run_inspect)

    args = parser.parse_args()
    if hasattr(args, "func"):
        sys.exit(args.func(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
