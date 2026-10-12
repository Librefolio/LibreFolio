---
title: "French typography applied at build time, not in the sources"
category: decision
status: accepted
date: 2026-10-11
tags: [docs, i18n, mkdocs, mkdocs-static-i18n, mkdocs-material, french, typography, hooks, build]
related:
  - concepts/mkdocs-suffix-i18n
  - problems/raw-html-paths-in-translations
  - decisions/docs-anchors-from-the-render
  - problems/stamps-hide-stale-translations
  - sources/phase00-translation-round12-2026-10
---

# Decision: French typography applied at build time, not in the sources

> Written by workstream M as a note for the devWiki on 2026-10-11, filed by the historian on 2026-10-12 with its paths
> and commits checked at `5d0585595`.

## Context

French typography keeps a sign with the word before it: a no-break space goes before `:`, a narrow no-break space
before `; ? !` and `%`, a no-break space inside `« »`, a narrow one between the digit groups of a number. The French
pages had a plain, breakable space in 3,630 places on 207 pages (batch 14 audit) and U+00A0 nowhere, and every
run of the translation pipeline writes plain spaces, so fixing the sources would not stay fixed.

## Options Considered

1. **(a)** normalize the sources, plus a validator check and a pipeline step;
2. **(b)** a build hook that applies French typography to the HTML of the French pages;
3. **(c)** keep the plain space.

**Developer's decision (2026-10-11): (b), in release 1.2** (backlog M-4). Decimals inside formulas keep the dot
(post-1.2 backlog M-5).

## Decision — what the hook does

- `mkdocs_src/hooks/fr_typography.py`, listed under `hooks:` in `mkdocs.yml`.
- It only **replaces** whitespace already standing before a sign; it never inserts one. `: ; ? !` count only when
  followed by whitespace, the end of the text, closing punctuation or an entity: a `?page=2` or a `:x` that starts
  a word after a space stays as written. `%` takes any whitespace before it (`<strong>50</strong> %`), a currency
  sign only after a digit.
- It reads text only. Tags and attributes pass through byte for byte, comments are skipped, and so is the content of
  `code`, `pre`, `kbd`, `samp`, `var`, `svg`, `math`, any element of class `arithmatex` (formulas), and the raw-text
  elements `script`, `style`, `textarea`, `iframe`, `noembed`, `noframes` and `xmp`, up to their end tag.
- Three places, French build only:
  - `on_page_content`, for pages whose **source** is French;
  - `page.toc` titles, because Material renders the sidebar TOC from `page.toc`, not from the content;
  - `on_nav` at priority −110, for the values of the French `nav_translations`: sidebar, tabs, header, `<title>`.

## Non-obvious facts learned on the way

- **mkdocs-static-i18n, `page.file.locale`** is the language of the source file. An English fallback page in the
  French build has `locale == "en"` and `locale_alternate_of == "fr"`, so the hook leaves English text alone.
- **mkdocs-static-i18n translates the nav in its own `on_nav` at priority −100.** A hook that needs the translated
  titles must run later, so at a lower priority (−110). It reads the current language from
  `config.plugins["i18n"].current_language`.
- **MkDocs 1.6: `del config.plugins[name]` does not unregister the plugin's event handlers.** To build the same site
  without a hook, remove its handlers from `config.plugins.events[event]`, matching `handler.__module__`. A first
  proof compared two builds that both ran the hook.
- **Tokenizer bug: a `<!--` inside raw text.** A tokenizer that precomputes `re.finditer` over the page and skips
  raw text by position resumed on a match the skip had jumped over: a `<!--` inside `script`, `style` or `textarea`
  swallowed the real tags after it. The fix searches each next token from the current position. The test-author's
  suite found it.

## Consequences — proof with two real builds, with and without the hook

- Every en, it and es file is byte-identical. Only `search/search_index.json` differs, because it holds the French
  text.
- In all 322 French pages, the two versions differ only in whitespace. Start tags (attributes included) and the
  content of code, pre, kbd, script, style and formulas are identical, compared with `html.parser`, independently of
  the hook's own tokenizer.
- Plain whitespace before `: ; ? ! %` in the French text drops from 6,580 to **0** in pages from a French source. 28
  remain in the English text of English fallback pages, by design.
- Delivered in batch 15 (`a965956ab`, "feat(docs): French typography at build time"), built on train 37 and merged
  with train 38 (`9245ffb6f`).

## Links

- [[concepts/mkdocs-suffix-i18n]] — the translated pages the hook works on
- [[problems/raw-html-paths-in-translations]] — the other build-time rule for translated pages
- Source: [[sources/phase00-translation-round12-2026-10]]

## Source files

| Role | Path |
|------|------|
| `typeset`, `typeset_html`, `on_page_content`, `on_nav` | `mkdocs_src/hooks/fr_typography.py` |
| The `hooks:` entry | `mkdocs_src/mkdocs.yml` |
| 191 tests (`./dev.py test utils docs-fr-typography`) | `backend/test_scripts/test_utilities/test_docs_fr_typography.py` |
| The runner action | `scripts/test_runner/_backend_utils.py` |
| Section «French Typography» | `mkdocs_src/docs/developer/docs/translation-pipeline.md` |
| Journal (part B, batch 15) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
