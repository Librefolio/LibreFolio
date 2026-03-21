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
├── .env                    # API key (gitignored)
├── .env.example            # Template for contributors
├── .gitignore              # Ignores .env, config.toml, cache
├── README.md               # This file
└── translate_docs.py       # Orchestration script (integrated with dev.py)
```

The script:
1. Reads translatable file paths from `mkdocs.yml` nav (excludes Developer/POC sections)
2. Detects target languages from `frontend/src/lib/i18n/index.ts` → `SUPPORTED_LOCALES`
3. Computes MD5 hash per source file — skips unchanged files
4. Generates temporary `config.toml` with Gemini model + API key
5. Invokes Aphra per file × language
6. Saves output as `*.{lang}.md` alongside the source
7. Cleans up `config.toml` (even on error)

Translation cache stored in `.translate-hashes.json` (gitignored).

