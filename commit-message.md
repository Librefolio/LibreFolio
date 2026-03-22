```
feat(i18n): pipeline resilience, artifacts cache, scroll/theme sync

Translation pipeline improvements:
- Structural diff (translate-diff): 13-check markdown structure comparison
  between EN source and translations. Injected as context into Step 4
  (Critique) for objective quality evaluation.
- Artifacts cache v2: analysis, critique, structural diff, models used,
  and timing saved per-file per-language in .translate-hashes.json.
  Auto-migration from v1. New `translate-inspect` command to browse.
- Rate limit retry: on HTTP 429, pauses 90s and retries up to 5 times
  (configurable via --rate-limit-retries). Aborts cleanly on exhaustion
  with progress saved.
- Auth error handling: detects HTTP 401 (key disabled/invalid), aborts
  immediately with actionable message pointing to OpenRouter keys page.
- HTTP-level timeout: replaces threading approach — actually closes the
  connection and stops Ollama/OpenRouter on timeout (default 15 min).
- Think-block stripping: monkey-patches Aphra's call_model() to remove
  <think>...</think> blocks from reasoning-distilled models before
  XML parsing.
- Refine retry: _robust_refine() retries up to 2x on parse failure
  (<improved_translation> tag not found).
- Connection error detection: clear "ollama serve" suggestion when
  backend is unreachable.
- Timestamps: HH:MM:SS on each file/language start+finish, elapsed
  shown as h/m/s (adaptive units).

MkDocs UX improvements:
- Scroll preservation: saves scroll position % in sessionStorage before
  language switch, restores after page load.
- Theme sync (app-sync.js): reads librefolio-theme from localStorage
  (shared origin with SvelteKit app) and applies matching MkDocs Material
  palette on page load. Also syncs librefolio-locale → gallery-lang so
  MkDocs language selector picks up the app's language.
- Locale-aware docs links: DocsLink.svelte and HelpMenu.svelte read
  librefolio-locale (not gallery-lang) and open docs in the user's
  selected language (e.g., /mkdocs/fr/faq/).

Bug fixes:
- validate_translations.py: fix UnboundLocalError on DOCS_DIR caused by
  redundant conditional import shadowing module-level import.
- DocsLink/HelpMenu: read librefolio-locale (SvelteKit key) instead of
  gallery-lang (MkDocs key) for correct language when opening docs.
```
