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

    Hierarchy (per role):
      1. APHRA_WRITER / APHRA_SEARCHER / APHRA_CRITIQUER  (role-specific)
      2. APHRA_MODEL  (shared fallback)
      3. DEFAULT_APHRA_MODEL  (hardcoded)

    Returns dict with keys: writer, searcher, critiquer.
    """
    shared = _load_env_var("APHRA_MODEL", DEFAULT_APHRA_MODEL)
    return {
        "writer": _load_env_var("APHRA_WRITER", shared),
        "searcher": _load_env_var("APHRA_SEARCHER", shared),
        "critiquer": _load_env_var("APHRA_CRITIQUER", shared),
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
    2. Glossary definitions block at the end ([N] term: definition...)
    3. Inline glossary markers [N] (preserves markdown links [text](url))
    """
    # 1. Strip <translation> / </translation> tags (Aphra wraps output in these)
    text = re.sub(r'</?translation>', '', text)

    # 2. Remove glossary block at the end
    #    Scan backwards: remove lines that are blank or start with [N]
    lines = text.split('\n')
    while lines:
        stripped = lines[-1].strip()
        if stripped == '' or re.match(r'^\[\d+\]', stripped):
            lines.pop()
        else:
            break
    text = '\n'.join(lines)

    # 3. Remove inline [N] markers — but NOT markdown links [text](url)
    #    [N] followed by ( is a markdown link → keep. Everything else → strip.
    text = re.sub(r'\[(\d+)\](?!\()', '', text)

    # 4. Clean up double/triple spaces left by removed markers
    text = re.sub(r'  +', ' ', text)

    # Ensure file ends with single newline
    text = text.rstrip() + '\n'

    return text


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

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
# Translation logic
# ---------------------------------------------------------------------------

def _translate_file(source_path: Path, target_lang: str, api_key: str, models: dict) -> Path | None:
    """
    Translate a single .en.md file to target language using Aphra.

    We bypass aphra.translate() to correctly pass our config.toml path
    to BOTH the LLMModelClient (API key) AND the workflow's load_config
    (model names). Without this, Aphra loads default models from its
    internal config/default.toml (Claude Sonnet 4 + Perplexity Sonar).

    Returns the output Path on success, None on failure.
    """
    from aphra.core.llm_client import LLMModelClient
    from aphra.core.context import TranslationContext
    from aphra.core.registry import get_suitable_workflow

    # Read source text
    source_text = source_path.read_text(encoding="utf-8")

    # Build output path: foo.en.md → foo.{lang}.md
    output_name = source_path.name.replace(".en.md", f".{target_lang}.md")
    output_path = source_path.parent / output_name

    # Language name mapping for Aphra
    lang_names = {"it": "Italian", "fr": "French", "es": "Spanish"}
    target_name = lang_names.get(target_lang, target_lang)

    config_path = str(CONFIG_TOML)

    try:
        # Ensure config.toml exists
        _generate_config_toml(api_key, models)

        # Create model client with our config (reads [openrouter] api_key)
        model_client = LLMModelClient(config_path)

        # Create translation context
        context = TranslationContext(
            model_client=model_client,
            source_language="English",
            target_language=target_name,
            log_calls=False,
            )

        # Find suitable workflow for this content
        workflow = get_suitable_workflow(source_text)
        if workflow is None:
            print(f"\n  ⚠️  No suitable workflow for {source_path.name}", file=sys.stderr)
            return None

        # ── KEY FIX: pass OUR config path so [short_article] models are read ──
        workflow_config = workflow.load_config(global_config_path=config_path)
        context.set_workflow_config(workflow_config)

        # Check if web search is enabled (default: disabled — saves cost & time)
        web_search = _load_env_var("APHRA_WEB_SEARCH", "false").lower() in ("true", "1", "yes")

        t0 = time.time()

        # Step 1: Analyze — identify key terms, expressions, entities
        print(f"\n     [1/5] 📝 Analyze   ... ", end="", flush=True)
        analysis = workflow.analyze(context, source_text)
        print(f"({time.time() - t0:.0f}s)", flush=True)

        # Step 2: Search (optional) — web-search context for each term
        if web_search:
            t1 = time.time()
            print(f"     [2/5] 🔍 Search    ... ", end="", flush=True)
            glossary = workflow.search(context, analysis)
            print(f"({time.time() - t1:.0f}s)", flush=True)
        else:
            glossary = ""  # skip web search — not needed for technical docs
            print(f"     [2/5] 🔍 Search    ... skipped", flush=True)

        # Step 3: Translate — initial full translation
        t2 = time.time()
        print(f"     [3/5] 🌐 Translate ... ", end="", flush=True)
        translation = workflow.translate(context, source_text)
        print(f"({time.time() - t2:.0f}s)", flush=True)

        # Step 4: Critique — compare original vs translation, suggest fixes
        t3 = time.time()
        print(f"     [4/5] 🔎 Critique  ... ", end="", flush=True)
        critique = workflow.critique(context, source_text, translation, glossary)
        print(f"({time.time() - t3:.0f}s)", flush=True)

        # Step 5: Refine — final translation incorporating critique
        t4 = time.time()
        print(f"     [5/5] ✨ Refine    ... ", end="", flush=True)
        translated = workflow.refine(context, source_text,
                                     translation=translation,
                                     glossary=glossary,
                                     critique=critique)
        print(f"({time.time() - t4:.0f}s)", flush=True)

        if translated:
            translated = _clean_translation(translated)
            output_path.write_text(translated, encoding="utf-8")
            return output_path
        else:
            print(f"  ⚠️  Empty translation for {source_path.name} → {target_lang}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"\n  ❌ Error translating {source_path.name} → {target_lang}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_translate(args) -> int:
    """Main translation logic."""
    target_langs = args.lang or _detect_target_languages()
    force = getattr(args, "force", False)
    dry_run = getattr(args, "dry_run", False)
    file_filter = getattr(args, "file", None)

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

    print(f"\n🚀 Starting translation...")
    if len(set(models.values())) == 1:
        print(f"   Model: {models['writer']}")
    else:
        print(f"   Writer:    {models['writer']}")
        print(f"   Searcher:  {models['searcher']}")
        print(f"   Critiquer: {models['critiquer']}")
    web_search = _load_env_var("APHRA_WEB_SEARCH", "false").lower() in ("true", "1", "yes")
    print(f"   Web search: {'ON' if web_search else 'OFF (skipped)'}")
    print()

    success_count = 0
    fail_count = 0
    total_tokens_est = 0
    t_total = time.time()

    try:
        _generate_config_toml(api_key, models)

        for i, (cache_key, source_path, lang) in enumerate(plan, 1):
            print(f"  [{i}/{len(plan)}] {cache_key} → {lang}", flush=True)
            start = time.time()

            output_path = _translate_file(source_path, lang, api_key, models)
            if output_path:
                elapsed = time.time() - start
                est = _estimate_tokens(source_path.stat().st_size)
                total_tokens_est += est["total"]
                print(f"     ✅ Done ({elapsed:.0f}s, {_format_tokens(est['total'])}) → {output_path}")
                success_count += 1

                # Update hash cache
                current_md5 = _file_md5(source_path)
                if cache_key not in hashes:
                    hashes[cache_key] = {"md5": current_md5, "langs_done": [], "last_translated": ""}
                hashes[cache_key]["md5"] = current_md5
                if lang not in hashes[cache_key]["langs_done"]:
                    hashes[cache_key]["langs_done"].append(lang)
                hashes[cache_key]["last_translated"] = datetime.now(timezone.utc).isoformat()

                # Save after each successful translation
                _save_hashes(hashes)
            else:
                fail_count += 1
                print("❌")

    finally:
        _cleanup_config_toml()

    # Summary
    total_elapsed = time.time() - t_total
    mins, secs = divmod(int(total_elapsed), 60)
    time_str = f"{mins}m {secs}s" if mins else f"{secs}s"

    print(f"\n{'=' * 50}")
    print(f"✅ Translated: {success_count}  |  ❌ Failed: {fail_count}  |  Total: {len(plan)}")
    print(f"⏱️  Total time: {time_str}")
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

    # ── 1. Aphra import ──
    print("1️⃣  Aphra module ...", end=" ", flush=True)
    try:
        from aphra import translate as _  # noqa: F401
        print("✅ importabile")
    except ImportError:
        print("❌ NON trovato")
        print("   ➜  Installa con: pipenv install --dev 'git+https://github.com/DavidLMS/aphra.git#egg=aphra'")
        ok = False

    # ── 2. .env + API key ──
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
# CLI / dev.py integration
# ---------------------------------------------------------------------------

def _add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add translate-specific arguments to a parser."""
    target_langs = _detect_target_languages()

    parser.add_argument("--lang", action="extend", nargs="+", choices=target_langs, metavar="LANG", help=f"Target language(s). Detected from frontend: {target_langs}", )
    parser.add_argument("--file", action="extend", nargs="+", metavar="PATH", help="File(s) or glob pattern(s) to translate (e.g. faq.en.md, user/*.en.md, 'user/**/*.en.md')", )
    parser.add_argument("--force", action="store_true", help="Re-translate all files (ignore MD5 cache)", )
    parser.add_argument("--dry-run", action="store_true", help="Show plan without translating", )


def register_subparser(mk_sub) -> None:
    """Register sub-commands under 'mkdocs' in dev.py."""
    # translate
    mk_p = mk_sub.add_parser("translate", help="Translate docs via Aphra (LLM agent)")
    _add_arguments(mk_p)
    mk_p.set_defaults(func=run_translate)

    # translate-check
    chk_p = mk_sub.add_parser("translate-check", help="Check translation pipeline setup")
    chk_p.set_defaults(func=run_check)


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

    args = parser.parse_args()
    if hasattr(args, "func"):
        sys.exit(args.func(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
