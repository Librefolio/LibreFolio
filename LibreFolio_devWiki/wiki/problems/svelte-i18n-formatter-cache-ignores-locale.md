---
title: "svelte-i18n caches ICU formatters by text, not by locale"
category: problem
status: resolved
date: 2026-10-07
tags: [frontend, i18n, svelte-i18n, icu, plural, cache, locale]
related: [problems/i18n-audit-false-dead-and-false-used, decisions/i18n-key-rationalization]
---

# Problem: an ICU message identical in two catalogues gets one locale's rules

## Symptom

After an in-place language switch (Header language selector, Preferences, the Welcome page, or the
login that applies the user's saved language), a plural message that is **byte-identical** in two
catalogues keeps the plural rules and the number format of whichever locale compiled it first:

| Message (EN = FR) | Wrong in FR after EN compiled it | Wrong in EN after FR compiled it |
|---|---|---|
| `{n, plural, one {# position} other {# positions}}` | `0 positions` (FR expects `one`), `1,000` | `0 position`, `1 000` |

Three keys had the shape on 2026-10-06: `importWizard.reportSet.gapFix.{positions,corrections}` and
`tools.pacAllocator.planner.review.sources`, all EN = FR.

## Root cause

`svelte-i18n@4.0.1` — the locked version and the latest published — memoizes the formatter factory
with a one-argument memo:

```js
// node_modules/svelte-i18n/dist/runtime.js:383-392 and :496
const monadicMemoize = (fn) => { /* cacheKey = JSON.stringify(arg) */ };
const getMessageFormatter = monadicMemoize((message, locale = getCurrentLocale()) => new IntlMessageFormat(message, locale, …));
```

The memo forwards only `message`, so the cache key is the text alone and `locale` is always the
current locale **at the first compilation**. The page never reloads on a language switch, so the
cached formatter survives for the whole session.

Only locale-sensitive ICU is affected — `plural`, `selectordinal`, `number`, `date`, `time` and the
`#` inside a plural. A plain text or a `{name}` argument renders the same everywhere.

## Fix

- **Data**: a locale-sensitive message must never be identical in two catalogues. The three FR texts
  got a CLDR `many` branch, identical to `other`: the text now differs from EN, and no rendering
  changes.
- **Gate**: `frontend/src/lib/i18n/catalogIcuLocale.test.ts` reads the four real catalogues and fails
  on any locale-sensitive ICU text shared by two locales, listing key and locales. A characterization
  latch in the same file pins the library behaviour (`getMessageFormatter(m, 'en')` and then
  `(m, 'fr')` return the same instance): when an upgrade fixes the cache, the latch turns red, which
  is the signal to revisit the gate.

## How to recognize it elsewhere

A test that formats the same ICU text in two locales in one file inherits the first locale's
rules. Read selections through formatters built with an explicit locale (the runtime's own
`IntlMessageFormat` class), as `planner/result/text.test.ts` does.

## Source files

| Role | Path |
|------|------|
| Locale switching, in place | `frontend/src/lib/stores/app/language.ts` |
| i18n initialisation | `frontend/src/lib/i18n/index.ts` |
| Catalogue gate and latch | `frontend/src/lib/i18n/catalogIcuLocale.test.ts` |
| Explicit-locale selection precedent | `frontend/src/lib/features/tools/pac-allocator/planner/result/text.test.ts` |
| Plan (§4) | `LibreFolio_developer_journal/Release_2/phases/29_i18nAudit/plan-phase00I18nAudit.prompt.md` |
