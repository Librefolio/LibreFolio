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
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path constants (resolved relative to this script's location)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent              # mkdocs_src/aphra-pipeline/
MKDOCS_SRC = SCRIPT_DIR.parent                            # mkdocs_src/
DOCS_DIR = MKDOCS_SRC / "docs"                            # mkdocs_src/docs/
MKDOCS_YML = MKDOCS_SRC / "mkdocs.yml"                    # mkdocs_src/mkdocs.yml
PROJECT_ROOT = MKDOCS_SRC.parent                          # LibreFolio/
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

# Aphra model configuration
APHRA_MODEL = "google/gemini-2.5-flash"


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
    Recursively walk the nav structure and collect file paths (.en.md).
    Skips entire sections whose top-level label is in skip_sections.
    """
    paths = []
    for item in nav_items:
        if isinstance(item, str):
            # Bare path (no label)
            if item.endswith(".en.md"):
                paths.append(item)
        elif isinstance(item, dict):
            for label, value in item.items():
                if label in skip_sections:
                    continue
                if isinstance(value, str):
                    if value.endswith(".en.md"):
                        paths.append(value)
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
    """Load translation hash cache."""
    if HASH_FILE.exists():
        try:
            return json.loads(HASH_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
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

def _load_api_key() -> str:
    """Load OPENROUTER_API_KEY from .env file."""
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


def _generate_config_toml(api_key: str) -> None:
    """Generate temporary config.toml for Aphra."""
    config_content = f"""[llm]
api_key = "{api_key}"
base_url = "https://openrouter.ai/api/v1"

[llm.writer]
model = "{APHRA_MODEL}"
temperature = 0.3

[llm.searcher]
model = "{APHRA_MODEL}"
temperature = 0.1

[llm.critiquer]
model = "{APHRA_MODEL}"
temperature = 0.2
"""
    CONFIG_TOML.write_text(config_content, encoding="utf-8")


def _cleanup_config_toml() -> None:
    """Remove temporary config.toml."""
    if CONFIG_TOML.exists():
        CONFIG_TOML.unlink()


# ---------------------------------------------------------------------------
# Translation logic
# ---------------------------------------------------------------------------

def _translate_file(source_path: Path, target_lang: str, api_key: str) -> bool:
    """
    Translate a single .en.md file to target language using Aphra.
    Returns True on success, False on failure.
    """
    from aphra import translate as aphra_translate

    # Read source text
    source_text = source_path.read_text(encoding="utf-8")

    # Build output path: foo.en.md → foo.{lang}.md
    output_name = source_path.name.replace(".en.md", f".{target_lang}.md")
    output_path = source_path.parent / output_name

    # Language name mapping for Aphra
    lang_names = {"it": "Italian", "fr": "French", "es": "Spanish"}
    target_name = lang_names.get(target_lang, target_lang)

    try:
        # Ensure config.toml exists
        _generate_config_toml(api_key)

        # Call Aphra translate
        translated = aphra_translate(
            source_language="English",
            target_language=target_name,
            text=source_text,
            config_file=str(CONFIG_TOML),
            log_calls=False,
        )

        if translated:
            output_path.write_text(translated, encoding="utf-8")
            return True
        else:
            print(f"  ⚠️  Empty translation result for {source_path.name} → {target_lang}", file=sys.stderr)
            return False

    except Exception as e:
        print(f"  ❌ Error translating {source_path.name} → {target_lang}: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_translate(args) -> int:
    """Main translation logic."""
    target_langs = args.lang or _detect_target_languages()
    force = getattr(args, "force", False)
    dry_run = getattr(args, "dry_run", False)
    file_filter = getattr(args, "file", None)

    # Get translatable files
    if file_filter:
        all_files = file_filter
    else:
        all_files = get_translatable_files()

    if not all_files:
        print("No translatable files found.")
        return 0

    # Load hash cache
    hashes = _load_hashes()

    # Build translation plan
    plan = []  # list of (rel_path, source_path, target_lang)
    for rel_path in all_files:
        source_path = DOCS_DIR / rel_path
        if not source_path.exists():
            print(f"  ⚠️  Source not found: {rel_path}", file=sys.stderr)
            continue

        current_md5 = _file_md5(source_path)
        cached = hashes.get(rel_path, {})
        cached_md5 = cached.get("md5", "")
        cached_langs = set(cached.get("langs_done", []))

        for lang in target_langs:
            if not force and current_md5 == cached_md5 and lang in cached_langs:
                continue  # Skip — unchanged and already translated
            plan.append((rel_path, source_path, lang))

    if not plan:
        print("✅ All files are up-to-date. Nothing to translate.")
        return 0

    # Show plan
    print(f"\n📋 Translation Plan: {len(plan)} file(s) × language(s)")
    print(f"   Target languages: {', '.join(target_langs)}")
    print(f"   Source files: {len(all_files)}")
    print()

    for rel_path, _, lang in plan:
        print(f"  • {rel_path} → {lang}")

    if dry_run:
        print(f"\n🔍 Dry run — no files translated.")
        return 0

    # Load API key and generate config
    api_key = _load_api_key()

    print(f"\n🚀 Starting translation...\n")

    success_count = 0
    fail_count = 0

    try:
        _generate_config_toml(api_key)

        for i, (rel_path, source_path, lang) in enumerate(plan, 1):
            print(f"  [{i}/{len(plan)}] {rel_path} → {lang} ... ", end="", flush=True)
            start = time.time()

            if _translate_file(source_path, lang, api_key):
                elapsed = time.time() - start
                print(f"✅ ({elapsed:.1f}s)")
                success_count += 1

                # Update hash cache
                current_md5 = _file_md5(source_path)
                if rel_path not in hashes:
                    hashes[rel_path] = {"md5": current_md5, "langs_done": [], "last_translated": ""}
                hashes[rel_path]["md5"] = current_md5
                if lang not in hashes[rel_path]["langs_done"]:
                    hashes[rel_path]["langs_done"].append(lang)
                hashes[rel_path]["last_translated"] = datetime.now(timezone.utc).isoformat()

                # Save after each successful translation
                _save_hashes(hashes)
            else:
                fail_count += 1
                print("❌")

    finally:
        _cleanup_config_toml()

    # Summary
    print(f"\n{'='*50}")
    print(f"✅ Translated: {success_count}  |  ❌ Failed: {fail_count}  |  Total: {len(plan)}")
    if fail_count:
        print(f"⚠️  Re-run to retry failed translations.")
    print()

    return 1 if fail_count else 0


# ---------------------------------------------------------------------------
# CLI / dev.py integration
# ---------------------------------------------------------------------------

def _add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add translate-specific arguments to a parser."""
    target_langs = _detect_target_languages()

    parser.add_argument(
        "--lang", action="extend", nargs="+", choices=target_langs, metavar="LANG",
        help=f"Target language(s). Detected from frontend: {target_langs}",
    )
    parser.add_argument(
        "--file", action="extend", nargs="+", metavar="PATH",
        help="File(s) to translate (relative to docs/)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-translate all files (ignore MD5 cache)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show plan without translating",
    )


def register_subparser(mk_sub) -> None:
    """Register as sub-command under 'mkdocs' in dev.py."""
    mk_p = mk_sub.add_parser("translate", help="Translate docs via Aphra (LLM agent)")
    _add_arguments(mk_p)
    mk_p.set_defaults(func=run_translate)


def main():
    """Standalone CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Translate MkDocs documentation using Aphra (LLM agent)",
    )
    _add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run_translate(args))


if __name__ == "__main__":
    main()


