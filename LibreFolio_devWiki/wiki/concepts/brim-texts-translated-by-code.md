---
title: "BRIM texts are translated by code: plugin names and descriptions, notices, evidence captions, refusals"
category: concept
tags: [brim, i18n, frontend, plugins, notices, translations, workstream-s]
related:
  - decisions/import-wizard-default-plugin-check
  - decisions/scalable-two-accounts-two-plugins
  - decisions/plugin-folders-and-split-i18n
  - decisions/i18n-key-rationalization
  - sources/phase00-brim-scalable-2026-10
---

# Concept: BRIM texts are translated by code

## Definition

A BRIM plugin speaks English: its name, its description, its notices, the caption of a notice's evidence rows, its
reason for refusing a file. The frontend shows each in the user's language through a key built from a stable code, and
falls back to the plugin's English text when the key is missing.

## Where It Applies

| Text | Key | Since |
|------|-----|-------|
| Plugin name and description | `brimPlugins.<code>.name`, `brimPlugins.<code>.description` — every plugin, 33 today, brands identical in every language | plan 37, step 12b (`2046b7419`, 2026-10-10) |
| Notices | `importWizard.brimNotice.<code>` (`resolveBrimNotice.ts`) | before plan 37; Scalable added twelve codes |
| Evidence captions | `importWizard.brimEvidence.<code>`; an empty caption in the plugin means «use the interface's» | step 12b |
| Refusal reasons | `importWizard.parseRefusal.<code>` (`resolveParseRefusalMessage`) | step 10, with [[decisions/import-wizard-default-plugin-check]]; the Generic CSV's and DEGIRO's codes, five of them shared by any plugin, since release 1.3 (workstream W, lot K2a) |

- `utils/brim/pluginText.ts`, on `translateOr`, serves the plugin select, the report-set card, the About tab and the
  import wizard. Brands get a key too, because svelte-i18n warns in the console for every missing key.
- DEGIRO's rule — notices in the language of the file — gives nothing for Scalable, whose files are always English:
  the interface language wins.
- Guards: `TestPluginTextCatalogues` (every registered plugin has a name and a description in the four catalogues, the
  English identical to the plugin, no orphan code), `TestWhatTheWizardWords` (Scalable's notice and caption keys),
  `utils gate-i18n-usage`.

## What changes next

Backlog C-39 split the catalogues by namespace after 1.2, starting with `brimPlugins`. Workstream U's planned split
goes further: seventeen subsystem catalogues plus a `base`, and each plugin's translations in its own folder —
[[decisions/plugin-folders-and-split-i18n]].

## Source files

| Role | Path |
|------|------|
| Plugin names and descriptions | `frontend/src/lib/utils/brim/pluginText.ts` |
| Notices and evidence captions | `frontend/src/lib/features/transactions/resolveBrimNotice.ts` |
| Refusals | `frontend/src/lib/features/transactions/import/defaultPluginCheck.ts` |
| The catalogue | `frontend/src/lib/i18n/base/en.json` |
| `TestPluginTextCatalogues` | `backend/test_scripts/test_external/test_brim_providers.py` |
| `TestWhatTheWizardWords` | `backend/test_scripts/test_external/test_brim_scalable.py` |
