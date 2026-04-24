---
title: "Knowledge Base: Documentation (MkDocs)"
category: source
source_type: knowledge_base
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/knowledge_base/03_documentation.md
tags: [mkdocs, documentation, i18n, aphra, gallery, translation]
related_features: [F-069, F-070, F-074]
---

# Source: Knowledge Base 03 — Documentation (MkDocs)

## Summary

Comprehensive guide to LibreFolio's MkDocs documentation system covering: directory structure (~90 files in 4 languages), gallery image loader auto-resolution, build validation, translation pipeline architecture (Aphra v2 with shared analysis step), 10-step `_clean_translation()` post-processing, 13-dimension structural diff, and style conventions (3 tone registers, mandatory emoji in H1-H3, admonition blank line rule for Prettier safety).

## Key insights extracted

- **MkDocs suffix i18n strategy** (`index.en.md`, `index.it.md`) → [[concepts/mkdocs-suffix-i18n]] created
- **Aphra translation pipeline** (4 phases: Analyze→Translate→Critique→Refine) → [[features/F-070]] enriched
- **Gallery screenshot automation** (E2E tests + deterministic DB state) → [[features/F-074]] enriched
- **Multi-language documentation** (90 source files × 4 languages, developer = EN-only) → [[features/F-069]] enriched
- **Admonition blank line rule** (Prettier-safe syntax for MkDocs admonitions) → documented in [[features/F-069]]
- **Gallery image loader** (auto-resolves paths via `basePath` detection, must update `knownSegments` for new top-level sections) → documented in [[features/F-074]]

## Wiki pages updated

- [[features/F-069]] — MkDocs Multi-Language Documentation — added source files, structure breakdown, admonition rule
- [[features/F-070]] — Aphra LLM Translation Pipeline — added v2 architecture, shared analysis, 10-step cleaning, structural diff
- [[features/F-074]] — E2E Test Gallery — added prerequisites, output directory, deterministic DB state
- [[concepts/mkdocs-suffix-i18n]] — created new concept page for suffix-based i18n strategy

## Source files

| Role | Path |
|------|------|
| Source KB file | `LibreFolio_developer_journal/knowledge_base/03_documentation.md` |
| MkDocs config | `mkdocs_src/mkdocs.yml` |
| Translation pipeline | `mkdocs_src/aphra-pipeline/translate_docs.py` |
| Validation script | `mkdocs_src/aphra-pipeline/validate_translations.py` |
| Gallery loader JS | `mkdocs_src/docs/javascripts/gallery-img-loader.js` |
| Developer docs | `mkdocs_src/docs/developer/docs/translation-pipeline.md` |
