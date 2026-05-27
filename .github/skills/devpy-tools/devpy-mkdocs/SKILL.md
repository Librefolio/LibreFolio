---
name: devpy-mkdocs
description: "Use this skill when the user needs to build, serve, or deploy MkDocs documentation, generate gallery screenshots, translate documentation, validate translations, or check cross-boundary links."
---

# MkDocs Documentation Commands

## Build & Serve

```bash
./dev.py mkdocs build                  # Build docs (strict mode, checks admonitions)
./dev.py mkdocs serve                  # Dev server on port 6042
./dev.py mkdocs clean                  # Remove build artifacts
./dev.py mkdocs deploy                 # Deploy to GitHub Pages
./dev.py mkdocs check-links           # Validate cross-boundary links (frontend/backend → docs)
```

## Gallery Screenshots

Generate automatic screenshots for documentation (light/dark × desktop/mobile × 4 languages):

```bash
./dev.py mkdocs gallery                          # Full gallery generation
./dev.py mkdocs gallery -l                       # List available test names
./dev.py mkdocs gallery -f "assets"              # Filter by name
./dev.py mkdocs gallery --desktop-only           # Only desktop viewport
./dev.py mkdocs gallery --mobile-only            # Only mobile viewport
./dev.py mkdocs gallery --no-populate            # Skip DB population (faster re-runs)
./dev.py mkdocs gallery -w 8                     # Custom worker count
./dev.py mkdocs gallery --force                  # Kill zombie processes on test port
./dev.py mkdocs gallery --headed                 # Visible browser (debugging)
./dev.py mkdocs gallery --test-port 8099         # Custom port
```

### Gallery Pipeline
1. Populates test DB with deterministic data (`--with-static --with-reports`)
2. Ensures E2E test users exist
3. Starts test server on port 6041
4. Runs `gallery.spec.ts` via Playwright (desktop + mobile projects)
5. Screenshots saved to `mkdocs_src/docs/gallery/`

### On Failure
When tests fail, the output shows which tests failed and provides retry commands:
```
Failed tests:
  ✗ Files › static resources grid view - all languages and themes

💡 Retry failed tests with:
   ./dev.py mkdocs gallery --no-populate -f "static resources grid view"
```

## Translation Pipeline

```bash
./dev.py mkdocs translate                        # Translate all docs (EN → IT, FR, ES)
./dev.py mkdocs translate --file "user/*.md"     # Only specific files
./dev.py mkdocs translate --lang it,fr           # Only specific languages
./dev.py mkdocs translate --dry-run              # Preview without writing
./dev.py mkdocs translate --force                # Force re-translate (ignore cache)

./dev.py mkdocs translate-check                  # Verify Aphra pipeline setup
./dev.py mkdocs translate-validate               # Offline structural validation
./dev.py mkdocs translate-validate --lang it     # Validate single language
./dev.py mkdocs translate-diff                   # Structural diff EN vs translations
./dev.py mkdocs translate-diff --issues-only     # Only show problems
./dev.py mkdocs translate-inspect                # Inspect translation cache artifacts
```

### Translation Architecture
- Strategy: `mkdocs-static-i18n` with suffix (`index.en.md`, `index.it.md`)
- LLM: Aphra workflow (Analyze → Translate → Critique → Refine)
- EN-only sections: `Developer Manual`, `POC UX`
- Cache: `.translate-hashes.json` (MD5-based skip)

## Documentation Style Rules

- **Admonitions**: ALWAYS insert empty line between `!!!`/`???` and body (Prettier-safe)
- **Emoji in headings**: H1-H3 always have 1 emoji
- **Diagrams**: Mermaid inline (no PNG)
- **Language**: Write in English (translations via pipeline)

See `.github/instructions/mkdocs.instructions.md` for full style guide.

