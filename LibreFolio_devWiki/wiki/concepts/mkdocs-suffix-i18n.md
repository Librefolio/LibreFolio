---
title: "MkDocs Suffix-based i18n Strategy"
category: concept
tags: [mkdocs, i18n, documentation, aphra]
related_features: [F-069, F-070]
---

# Concept: MkDocs Suffix-based i18n Strategy

## Definition

LibreFolio uses the `mkdocs-static-i18n` plugin's **suffix strategy** to organize multilingual documentation: each page exists as separate files with language suffixes (`index.en.md`, `index.it.md`, `index.fr.md`, `index.es.md`). This differs from the folder strategy (where each language gets its own directory tree) and enables clean, flat repository structure with explicit language files.

## Why This Approach

1. **Explicit file tracking**: `git diff` shows exactly which language file changed
2. **Flat directory structure**: no nested `en/`, `it/`, `fr/`, `es/` directories — easier navigation
3. **Translation pipeline compatibility**: Aphra expects `.XX.md` suffix format for target files
4. **Source file clarity**: `.en.md` is always the source of truth, translations are derived
5. **mkdocs-static-i18n native support**: plugin designed for this pattern, handles nav generation automatically

## Configuration

In `mkdocs_src/mkdocs.yml`:

```yaml
plugins:
  - i18n:
      docs_structure: suffix  # NOT folder
      languages:
        - locale: en
          default: true
          name: English
        - locale: it
          name: Italiano
        - locale: fr
          name: Français
        - locale: es
          name: Español
```

## Scope

| Section | Translated? | Files |
|---------|:-----------:|-------|
| User Manual | ✅ | 17 × 4 languages |
| Admin Manual | ✅ | 6 × 4 languages |
| Financial Theory | ✅ | 7 × 4 languages |
| Gallery | ✅ | 3 × 4 languages |
| Root (Home, FAQ, Credits) | ✅ | 3 × 4 languages |
| **Developer Manual** | ❌ | ~45 files (EN-only) |
| POC UX | ❌ | 1 file (EN-only) |

**Total**: ~36 source files → ~108 translated files (3 target languages).

## Developer Pages Excluded

`EN_ONLY_SECTIONS` in `translate_docs.py` skips:
- `developer/` — technical audience, EN standard
- `POC_UX/` — historical artifact

Rationale: developer audience expects English technical docs, translation overhead not justified.

## Where It Applies

- **Build**: `./dev.py mkdocs build` — mkdocs-static-i18n generates 4 language versions of the site
- **Serve**: `./dev.py mkdocs serve` — preview all languages at `http://localhost:6042/XX/` (EN, IT, FR, ES)
- **Translation**: `./dev.py mkdocs translate` — Aphra reads `.en.md`, writes `.it.md`/`.fr.md`/`.es.md`
- **Validation**: `./dev.py mkdocs translate-diff` — structural diff ensures EN and translations match

## Relation to Aphra Pipeline

The suffix strategy is **required** for Aphra integration:
1. Aphra reads `source.en.md`
2. For each target language (`it`, `fr`, `es`):
   - Step 3 (Translate) writes initial `source.it.md`
   - Step 5 (Refine) overwrites `source.it.md` with final version
3. `_clean_translation()` step 9 normalizes internal links (`.it.md` → `.md`) so mkdocs-static-i18n can resolve them

## Conventions

- **Source file**: always `.en.md` — never modify `.it.md`/`.fr.md`/`.es.md` by hand
- **Link normalization**: translated files use `.md` (not `.it.md`) — plugin handles resolution
- **Cache tracking**: `.translate-hashes.json` stores MD5 of `.en.md` + all `.XX.md` — skip re-translation if unchanged

## Anchors in links from the app (2026-09-24)

A link from the app to the docs is served in the reader's language, so its anchor must exist in **every** language.
`dev.py mkdocs check-links` checks exactly that, and fails with "anchor … resolves in English but is missing in: it, fr,
es — the translated heading produces a different slug".

Two ways to hit it:
- **A translated heading**: the slug comes from the heading text, which differs per language. Give the heading an
  explicit id (`## Title {: #my-id }`) in the English source, and make sure the translations keep it.
- **An English page rewritten and not translated yet**: the section does not exist in the other languages at all.
  On 24/09 the risk-metrics index had the four-questions sections (`#how-much-can-it-hurt`,
  `#am-i-paid-for-the-risk`) in English only: it had been rewritten on 18/09 (`b35a8581e`) and not translated. The
  lab's L1/L3 icons point at the page root until the translation lands.

`MKDOCS_ANCHOR_EXCEPTIONS` may only shrink: it is not the place to park a new anchor. Check an anchor in all four
`.XX.md` files before handing it to anyone; the coordinator's own map missed it by looking at English only.

## Source files

| Role | Path |
|------|------|
| mkdocs config | `mkdocs_src/mkdocs.yml` |
| Translation script | `mkdocs_src/aphra-pipeline/translate_docs.py` |
| Source KB file | `LibreFolio_developer_journal/knowledge_base/03_documentation.md` |
| Developer doc | `mkdocs_src/docs/developer/docs/translation-pipeline.md` |
| Cross-boundary link check, `MKDOCS_ANCHOR_EXCEPTIONS` | `dev.py` |
| i18n plugin docs | [mkdocs-static-i18n GitHub](https://github.com/ultrabug/mkdocs-static-i18n) |
