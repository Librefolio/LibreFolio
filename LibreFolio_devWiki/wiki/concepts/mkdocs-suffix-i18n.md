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

## Source files

| Role | Path |
|------|------|
| mkdocs config | `mkdocs_src/mkdocs.yml` |
| Translation script | `mkdocs_src/aphra-pipeline/translate_docs.py` |
| Source KB file | `LibreFolio_developer_journal/knowledge_base/03_documentation.md` |
| Developer doc | `mkdocs_src/docs/developer/docs/translation-pipeline.md` |
| i18n plugin docs | [mkdocs-static-i18n GitHub](https://github.com/ultrabug/mkdocs-static-i18n) |
