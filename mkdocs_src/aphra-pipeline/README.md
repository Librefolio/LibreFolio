# 🌐 Aphra Translation Pipeline

Automated translation of LibreFolio MkDocs documentation into multiple languages using [Aphra](https://github.com/DavidLMS/aphra) (LLM-based translation agent) with Google Gemini via OpenRouter BYOK.

## Overview

This pipeline translates `.en.md` source files into `it`, `fr`, `es` using Aphra. The translated files (`*.it.md`, `*.fr.md`, `*.es.md`) are picked up by `mkdocs-static-i18n` (suffix strategy) to build a multilingual documentation site.

**What gets translated:**
- User Manual, Admin Manual, Financial Theory, Gallery, FAQ, Home, Credits
- ~35 source files → ~105 translated files (3 target languages)

**What stays EN-only:**
- Developer Manual (~45 files) — technical reference, not user-facing
- POC UX — temporary proof-of-concept, will be removed

## Prerequisites

1. **Aphra** installed as dev dependency: `pipenv install --dev git+https://github.com/DavidLMS/aphra.git#egg=aphra`
2. **`.env`** file with OpenRouter API key (copy from `.env.example`)
3. **Python + Pipenv** environment from LibreFolio root

## Usage

```bash
# Translate all (skips unchanged files via MD5 cache)
./dev.py mkdocs translate

# Translate specific languages
./dev.py mkdocs translate --lang it fr

# Force re-translation (ignores MD5 cache)
./dev.py mkdocs translate --force

# Translate specific files
./dev.py mkdocs translate --file user/getting-started.en.md faq.en.md --lang it

# Dry run (shows what would be translated)
./dev.py mkdocs translate --dry-run
```

Both flag styles work:
- `--lang it fr es` (space-separated)
- `--lang it --lang fr --lang es` (repeated flags)

### Check pipeline setup

```bash
./dev.py mkdocs translate-check
```

Verifies: Aphra installed, API key valid, models configured, files detected, OpenRouter connectivity.

## 🔄 How Aphra Translates (Workflow)

Aphra uses a multi-step **agentic workflow** where an LLM acts in different roles. Each role can use a different model.

### Default: 4-step workflow (web search OFF)

| Step | Role | What it does |
|------|------|-------------|
| **1. Analyze** | Writer | Reads the source text, identifies key terms, cultural references, and technical jargon that may be tricky to translate |
| **2. Translate** | Writer | Produces an initial full translation preserving structure and style |
| **3. Critique** | Critiquer | Compares original vs translation, flags errors, suggests improvements |
| **4. Refine** | Writer | Produces the final translation incorporating the critic's feedback |

### Optional: 5-step workflow (web search ON)

When `APHRA_WEB_SEARCH=true`, a **Search** step is added between Analyze and Translate:

| Step | Role | What it does |
|------|------|-------------|
| **2. Search** | Searcher | For each term found in Step 1, queries the web via OpenRouter's `:online` plugin for real-time context, definitions, and usage examples |

### Why web search is OFF by default

- **Cost**: OpenRouter charges **$4 per 1000 web search results**, on top of model costs. Each term from Step 1 triggers a separate search query.
- **Speed**: Search adds 30-120 seconds per file depending on term count.
- **Not needed for technical docs**: LibreFolio documentation uses well-known terms (Docker, ETF, API, ISIN…) that don't benefit from web lookup.
- **Model compatibility**: The `:online` suffix appended to model names may conflict with `:free` model suffixes (`model:free:online` is invalid).

> **When to enable**: Only if translating content with obscure cultural references, idiomatic expressions, or rapidly-evolving terminology that needs real-time verification.

### LLM Roles & Model Configuration

Aphra's 3 roles can each use a different model, configured via `.env`:

```env
# Shared model for all roles (convenient shortcut)
APHRA_MODEL=google/gemini-2.5-flash

# Per-role overrides (uncomment to specialize)
# APHRA_WRITER=google/gemini-2.5-flash      # Steps: analyze, translate, refine
# APHRA_SEARCHER=google/gemini-2.5-flash     # Step: search (only if web search ON)
# APHRA_CRITIQUER=google/gemini-2.5-flash    # Step: critique
```

**Priority**: `APHRA_WRITER` > `APHRA_MODEL` > hardcoded default (`google/gemini-2.5-flash`)

> **⚠️ Aphra's built-in defaults** (in `aphra/workflows/short_article/config/default.toml`) are `anthropic/claude-sonnet-4` (writer + critiquer) and `perplexity/sonar` (searcher) — both paid models. Our wrapper **overrides these** with the models from `.env`, so you're always in control of costs.

### Web Search Toggle

```env
# OFF (default) — 4 steps, no web cost, faster
APHRA_WEB_SEARCH=false

# ON — 5 steps, adds web search cost + latency
APHRA_WEB_SEARCH=true
```

### Caching Note

The translation pipeline caches **source file MD5 hashes** (`.translate-hashes.json`) to skip unchanged files between runs. This is per-file granularity — if a source `.en.md` hasn't changed, all its translations are skipped.

Aphra's web search results (Step 2, when enabled) are **not cached** between runs. In theory, since the search glossary is shared context (same terms appear across files in the same section), caching and reusing it could save significant API calls. However, for our use case with web search disabled, this optimization is unnecessary. If needed in the future, the glossary could be serialized per-section and reused across files.

## 🔑 API Key Setup (BYOK: OpenRouter + Google Gemini)

This pipeline uses Google Gemini models via OpenRouter's **BYOK (Bring Your Own Key)** feature. This routes API calls directly through Google's servers using your own credentials, minimizing costs.

### Step 1 — Get a Google Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click **"Get API key"** in the navigation menu
4. Create a new key in a new or existing project — copy it

### Step 2 — Create an OpenRouter Account

1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Sign up or log in

### Step 3 — Add Google Key to OpenRouter (BYOK)

1. In the OpenRouter dashboard, go to **Keys** → **Integrations / BYOK**
2. Find the **Google** provider
3. Paste the Google Gemini API key from Step 1
4. Save the configuration

### Step 4 — Generate an OpenRouter API Key

1. Still on OpenRouter, go to **Keys**
2. Click **"Create Key"**
3. Name it (e.g., "MkDocs Translation Pipeline")
4. Copy the generated key (starts with `sk-or-v1-`)

### Step 5 — Configure Local `.env`

```bash
cp .env.example .env
# Edit .env and paste the OpenRouter key from Step 4
```

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

## Architecture

```
mkdocs_src/aphra-pipeline/
├── .env                    # API key + model config (gitignored)
├── .env.example            # Template for contributors
├── .gitignore              # Ignores .env, config.toml, cache
├── README.md               # This file
└── translate_docs.py       # Orchestration script (integrated with dev.py)
```

The script:
1. Reads translatable file paths from `mkdocs.yml` nav (excludes Developer/POC sections)
2. Detects target languages from `frontend/src/lib/i18n/index.ts` → `SUPPORTED_LOCALES`
3. Computes MD5 hash per source file — skips unchanged files
4. Generates temporary `config.toml` with model names + API key (Aphra format)
5. Calls Aphra workflow step-by-step (bypasses `aphra.translate()` to correctly pass config path and control web search)
6. Shows per-step progress with timing (Analyze → Translate → Critique → Refine)
7. Saves output as `*.{lang}.md` alongside the source
8. Cleans up `config.toml` (even on error)

Translation cache stored in `.translate-hashes.json` (gitignored).
