# 🌐 Aphra Translation Pipeline

Automated translation of LibreFolio MkDocs documentation into multiple languages using [Aphra](https://github.com/DavidLMS/aphra) — an LLM-based agentic translation workflow. Supports both **cloud** (OpenRouter) and **local** (Ollama) LLM backends.

> 📖 **Full documentation**: See the [Translation Pipeline](../docs/developer/docs/translation-pipeline.md) page in the Developer Manual for architecture details, Mermaid workflow diagrams, and how we customized Aphra.

## Quick Start

```bash
# 1. Copy and configure .env
cp .env.example .env
# Edit .env — set APHRA_BASE_URL for local (Ollama) or OPENROUTER_API_KEY for cloud

# 2. Verify setup
./dev.py mkdocs translate-check

# 3. Translate
./dev.py mkdocs translate --file faq.en.md --lang it                    # single file
./dev.py mkdocs translate --file 'user/**/*.en.md' --lang it fr es      # glob
./dev.py mkdocs translate                                                # all files
./dev.py mkdocs translate --dry-run                                      # preview + token estimate
```

## Local Mode (Ollama)

```bash
brew install ollama
ollama pull kwangsuklee/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF  # analyzer (reasoning)
ollama pull kwangsuklee/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-GGUF   # writer (generation)
```

```env
APHRA_BASE_URL=http://localhost:11434/v1
APHRA_ANALYZER=kwangsuklee/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF
APHRA_MODEL=kwangsuklee/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-GGUF
```

## Cloud Mode (OpenRouter)

See `.env.example` for BYOK setup with Google Gemini.

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
APHRA_MODEL=google/gemini-2.5-flash
```
