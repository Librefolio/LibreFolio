---
title: "A slow language switch tore the whole app down, and Welcome lost the chosen language"
category: problem
status: resolved
date: 2026-10-07
tags: [frontend, i18n, svelte-i18n, onboarding, e2e, under-load]
related: [problems/svelte-i18n-formatter-cache-ignores-locale, problems/i18n-audit-false-dead-and-false-used]
---

# Problem: a slow language switch tore the whole app down

## Symptom

In a full coverage run under heavy load, `e2e/auth.spec.ts` «3a» went red: after completing Welcome
with Italian chosen, the page stayed `<html lang="en" data-i18n-ready="true">`. On an idle machine the
test passed. A real user on a remote instance would see the same: pick a language in Welcome, the app
blanks out, comes back in English, and completing Welcome saves English.

## Root cause

Three behaviours, each reasonable alone:

1. **svelte-i18n 4** (`runtime.js:319-338`): `locale.set(x)` on a dictionary not yet loaded sets the
   locale only once it has loaded, and raises `isLoading` if that takes more than `loadingDelay`
   (200 ms).
2. **Both layouts** (`routes/+layout.svelte`, `routes/(app)/+layout.svelte`) replaced the whole app with a
   placeholder while `$i18nLoading` — meant for the first dictionary, but it fired on every later
   switch too, destroying and rebuilding every page.
3. **The Welcome preview** (`welcome/+page.svelte`, `previewLanguage`) only calls `locale.set`, by design:
   Skip must restore the saved language. On the rebuild, `(app)/+layout.svelte` re-ran `initI18n()` and
   `currentLanguage.init()`, which read `localStorage['librefolio-locale']` (still the old language), and
   Welcome re-hydrated its draft from the saved settings.

The ~250 KB Italian catalogue arrives within 200 ms on an idle localhost, so only load (or a real
network) exposed it. A comment in the root layout even claimed that `locale` flips at once.

## Fix (Release 2, workstream O)

Both layouts latch `i18nBooted` the first time `$i18nLoading` is false and show the placeholder only
before that. Later loads keep the app mounted; `data-i18n-ready` still reports them. The regression E2E
«3c» holds the Italian chunk at the network until `data-i18n-ready="false"` is on screen (no clock),
then asserts the same Welcome form node, `lang="it"` and a completion that posts `it`; a unit case in
`layout.gate.test.ts` proves the `(app)` layout keeps its page node through a later load.

## Lesson

A gate on a *loading* flag must say which load it waits for. «Show a splash until i18n is ready» became
«tear the app down whenever any dictionary is in flight», and the cost (rebuilt pages, lost drafts) only
appeared when the network or the machine was slow. To reproduce a load-only red, hold the resource at the
network and wait on the state it causes; never rewrite a gzip-served chunk body in `route.fulfill`.

## Source files

| Role | Path |
|------|------|
| Root layout (first-dictionary latch, `data-i18n-ready`) | `frontend/src/routes/+layout.svelte` |
| App layout (same latch) | `frontend/src/routes/(app)/+layout.svelte` |
| Welcome preview | `frontend/src/routes/(app)/welcome/+page.svelte` |
| Language store (`init` reads localStorage) | `frontend/src/lib/stores/app/language.ts` |
| Regression E2E («3c») | `frontend/e2e/auth.spec.ts` |
| Layout unit gate | `frontend/src/routes/(app)/layout.gate.test.ts` |
| Plan (S16 triage, S17 fix) | `LibreFolio_developer_journal/Release_2/phases/29_i18nAudit/plan-phase00I18nAudit.prompt.md` |
