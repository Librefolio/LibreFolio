---
title: "The translation clean-up flattened the indentation of code blocks: one regex on the whole document broke the translated Docker compose"
category: problem
status: resolved
date: 2026-10-06
tags: [docs, i18n, translation, aphra, pipeline, code-blocks, yaml, validator, workstream-m]
related:
  - features/F-070
  - problems/stamps-hide-stale-translations
  - problems/raw-html-paths-in-translations
  - decisions/docs-anchors-from-the-render
  - sources/phase00-release-images-and-gallery-2026-10
---

# Problem: translated code blocks lost their indentation

## Symptom

While adding the Tailscale watchdog to the admin guide (plan of the release images, step 6), M found the Italian,
French and Spanish versions of the Docker compose examples flattened: in `admin/docker_advanced`, block 22, a YAML
file indented at 0, 2, 4, 6 and 8 spaces came out at 0 and 1 — a compose file Docker cannot read. M fixed that block
by hand, and the coordinator asked for the cause («passo 8»).

## Root Cause

`_clean_translation()` in `mkdocs_src/aphra-pipeline/translate_docs.py`, step 7, ran
`re.sub(r'  +', ' ', text)` on the **whole** translated document, code blocks included, right before the only write of
the translation. Nothing masked the code.

The checks were blind to it:

- the pipeline's structural diff compared only the number and the language tags of the code blocks;
- `validate_translations.py` compared blocks by position and filed every difference as LOCALIZED, «comments translated
  or alignment stripped».

The damage spread over two lists: **A**, pages the next alignment would translate again (9 pairs, 51 blocks), and
**B**, pages it would not (54 pairs in 18 pages — 17 indicators and `price-resolution` — Mermaid only).

## Solution

`5fa0cf12a` (2026-10-06, «fix(aphra): keep code indentation in translations»):

- **B, the clean-up spares code.** Step 7 becomes `_collapse_inner_spaces()`: runs of spaces between two words
  collapse, only on lines outside code; leading indentation and trailing hard breaks are never touched.
- **C, the translation gets the source indentation back.** `_finalize_translation()` runs the clean-up, then
  `restore_code_indent()` puts the English leading whitespace back on each paired code block.
- **A new module, standard library only**, `mkdocs_src/aphra-pipeline/code_blocks.py` (`pair_blocks`,
  `restore_code_indent`, `code_indent_issues`). On that day `dev.py` imported the translation commands inside
  `except ImportError: pass`, so a third-party import there would have made them vanish in silence. (Since
  `5dca6e2cf`, 2026-10-08, `dev.py` checks with `_has()` that the docs sources are there instead, and a broken import
  in a full checkout fails loudly — [[problems/devpy-unusable-in-docker-image]].)
- **A new ERROR in the validator**, `code-block-indent`.
- **80 tests**, written red first: `test_translation_code_blocks.py`, with fixtures modelled on the real pages
  (an annotated compose file, list steps, Mermaid tabs, ASCII art).

The developer on the repair: «si mi torna, allora di ad M di correggere lo script. riguardo al correggere le pagine
già convertite sono in dubbio visto che tra poco dobbiamo rifare il grande allineamento, che ne pensi? magari solo per
le pagine che comunque sono fuori dallo scope?». So only list **B** was repaired at once, by script (342 lines, whitespace
only); list A was left to the alignment. The repair is invisible to the translation cache, which keys a page on the
English file's md5.

`translate-validate` counted 606 errors before, 711 with the new check on the old pages (+105 `code-block-indent`),
657 after the B repair (+51, all in list A, until the alignment).

## Prevention

- Text normalisation in the pipeline must mask code before it runs; `code-block-indent` is now an ERROR, and
  `translate-validate` gates every run of `release.yml` except on `dev`.
- A fix made to translated files only, leaving the English file alone, never reaches the cache: the cache decides from
  the English md5 alone, the same root as [[problems/stamps-hide-stale-translations]].

## Source files

| Role | Path |
|------|------|
| Code-block pairing and indentation | `mkdocs_src/aphra-pipeline/code_blocks.py` |
| `_collapse_inner_spaces`, `_finalize_translation` | `mkdocs_src/aphra-pipeline/translate_docs.py` |
| `code-block-indent` check | `mkdocs_src/aphra-pipeline/validate_translations.py` |
| Tests | `backend/test_scripts/test_utilities/test_translation_code_blocks.py` |
| Developer page | `mkdocs_src/docs/developer/docs/translation-pipeline.md` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslatedCodeIndent.prompt.md` |
