---
title: "Docs link anchors are read from the page's MkDocs render"
category: decision
status: resolved
date: 2026-10-11
tags: [docs, i18n, mkdocs, translation, aphra, anchors, check-links, translate-validate]
related:
  - concepts/mkdocs-suffix-i18n
  - problems/stamps-hide-stale-translations
  - problems/raw-html-paths-in-translations
  - decisions/fr-typography-at-build-time
  - sources/phase00-translation-round12-2026-10
---

# Decision: docs link anchors are read from the page's MkDocs render

> Written by workstream M as a note for the devWiki on 2026-10-11, filed by the historian on 2026-10-12 with its paths
> and commits checked at `5d0585595`.

## Context

Two checks verify that a link `page.md#anchor` lands on an anchor of the page it opens, in English and in every
translation: `translate-validate`'s `anchor-missing` (`mkdocs_src/aphra-pipeline/validate_translations.py`) and
`./dev.py mkdocs check-links` (frontend/backend links into the docs). Both computed a page's anchors with
hand-written code: heading slugs re-implementing Python-Markdown's slugify, plus `{: #id }` and `id="…"` found by
regex. `mkdocs build --strict` (`validation: anchors: warn`) is the real arbiter, but it stops at the first language
with a warning, so it surfaces broken links one language at a time.

A corpus probe (batch 13, 944 pages) compared the hand-made anchors with a render using the site's own extensions:
the validator **accepted 1179 ids the build does not have** (335 pages) and **missed 109 it has** (73 pages). The
divergences:

- a heading with an explicit `{: #id }` has **only** that id; its text slug is not an anchor;
- the `_1`, `_2` numbering of repeated slugs also counts the explicit ids;
- an `id="…"` or `{: #… }` written in inline code is not an anchor, while a raw-HTML `id` or `<a name>` is (MkDocs
  collects them from the source, a full tag in inline code included);
- the site's extensions change ids: e.g. an emoji shortcode in a heading;
- the front matter is not rendered; a leading byte-order mark is dropped (MkDocs reads pages as utf-8-sig).

No link was broken that day, so nothing was red: the checks were simply not measuring what the build measures.

## Options Considered

1. **Fix the hand-made slugs** — cheap, but it chases MkDocs, Python-Markdown and every extension of `mkdocs.yml`;
   the next extension silently breaks it again.
2. **Read the ids from the page's own MkDocs render** — exactly the set the build checks, ~6 s for the whole corpus.
3. **Leave anchors to the strict build** — one language per run, and `check-links` covers links from the app, which
   the build never sees.

## Decision

Option 2. `mkdocs_src/aphra-pipeline/page_anchors.py`: `render_anchors(source)` renders a Markdown source through
MkDocs' own `Page.render` with the site configuration (`load_config(mkdocs_src/mkdocs.yml)`, loaded once) and returns
`Page.present_anchor_ids`, the set `mkdocs build --strict` checks a link against. `file_anchors(path)` renders each
version of a file once (cache on path, mtime, size). Both callers use it; MkDocs is imported only inside the
functions, so `dev.py` still builds its whole command line where MkDocs is not installed (the Docker image), and
`check-links` then exits 1 saying it needs MkDocs.

Proof of exactness: a real build with `Page.render` wrapped to record each page's ids gave **the same ids on all 946
pages** (13,992 ids). `check-links` gave the same 95 valid links before and after.

## Consequences

- An anchor check never re-implements slugify: if a page renders an id, links may use it; if not, they may not.
- Shared explicit ids (`{: #name }` on the heading in all four languages) stay the way to link across languages:
  a translated heading's text slug differs per language, and once it has an explicit id its slug is gone.
- The checks cost a render per page (~6 s per corpus run); `translate-validate` takes ~7 s.
- Tests: `./dev.py test utils translation-validator` (`page_anchors.py` included) and `utils gate-docs-links`
  (dev.py's verdict per language, dev.py without MkDocs).

## Links

- [[concepts/mkdocs-suffix-i18n]] — the suffix structure and its anchors
- [[problems/stamps-hide-stale-translations]] — the same round's other blind spot of the checks
- Commits: `3d86cc732` "fix(i18n): anchors from the page's MkDocs render" and `5b8e647db` "fix(dev): check-links
  reads rendered anchors"; batch 13, merged as `3a2e14514` (train 33)
- Source: [[sources/phase00-translation-round12-2026-10]]

## Source files

| Role | Path |
|------|------|
| `render_anchors`, `file_anchors` | `mkdocs_src/aphra-pipeline/page_anchors.py` |
| `anchor-missing` | `mkdocs_src/aphra-pipeline/validate_translations.py` |
| `check-links` (`cmd_mkdocs_check_links`) | `dev.py` |
| Site configuration the render loads | `mkdocs_src/mkdocs.yml` |
| Validator tests | `backend/test_scripts/test_utilities/test_translation_validator.py` |
| Link gate tests | `backend/test_scripts/test_utilities/test_docs_links_gate.py` |
| Journal (steps 5.7 and 5.8) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
