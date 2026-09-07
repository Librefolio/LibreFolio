---
title: "Assert on identity, never on rendered text"
category: concept
date: 2026-09-01
tags: [testing, frontend, i18n, vitest, playwright, false-green, assertions]
related:
  - problems/i18n-key-assertion-false-green
  - concepts/e2e-data-testid-rule
  - concepts/characterisation-test-latch
related_features: [F-067, F-008]
---

# Concept: assert on identity, never on rendered text

> Written 2026-09-01. The principle was already fully demonstrated by
> [[problems/i18n-key-assertion-false-green]], whose frontmatter pointed at a
> `assert-on-identity-not-prose` page that had never been written. This is that page.
> It states the rule; the problem page is the proof.

## Definition

A test must assert on something the **code** decides — a `data-*` attribute, an
i18n key, an enum value, a status code — and never on the string a user reads.

Rendered text is a **product of three inputs**: the code, the catalogue, and the
active locale. An assertion on rendered text is an assertion on all three at once,
so it cannot tell you which one changed. That is not a strict test; it is an
ambiguous one.

> The assertion should fail when the behaviour changes, and only then. Rendered
> text changes for reasons that are not behaviour.

## The trap that makes this non-obvious

The rule has a disguise that looks exactly like the rule being followed:

```ts
// looks like it asserts on a KEY. asserts on rendered TEXT.
expect(errorText()).toBe('brokers.sharing.loadFailedBlocking');
```

`errorText()` reads the DOM, so it returns whatever `$_()` produced. The suite loads
the real catalogue, so `$_()` really does translate. The assertion passed for one
reason and one reason only: **the key did not exist yet**, and `svelte-i18n` echoes
a missing key back as its own text. Two facts cancelled out and produced a green.

The failure ordering is the worst available: **green while the feature is
untranslated, red the moment someone translates it** — a commit that touches no
component and no test. Five `BrokerSharingPanel` tests failed exactly that way, and
the blame landed on the translator for a defect written weeks earlier.

## The two correct forms

**1 — the component publishes its own identity.** Preferred, because it makes the
assertion independent of the catalogue entirely:

```svelte
<div data-testid="broker-sharing-panel" data-error-key={errorKey ?? undefined}>
```

```ts
expect(panel()).toHaveAttribute('data-error-key', 'brokers.sharing.loadFailedBlocking');
```

This is the precedent set by `BrokerSharingPanel.svelte` (L379), which publishes
`data-error-key` alongside `data-access-state` and `aria-invalid`. Seven assertions
across five tests were converted to it.

**2 — compare against the catalogue, never against a hand-written literal.**
Acceptable when the message has no identity in the code:

```ts
import en from '$lib/i18n/en.json';
expect(errorText()).toBe(en.brokers.sharing.loadFailedBlocking);
```

The literal is then never typed by a human, and the test stays true in all four
languages. `imageCrop.test.ts` uses this form.

## What is *not* an acceptable form

```ts
expect(errorText()).toBe('Could not load current sharing settings');  // English prose
expect(page.getByText('Salva')).toBeVisible();                        // locale-dependent
```

Both break on a copy edit, and the second breaks on a locale change. See
[[concepts/e2e-data-testid-rule]] for the Playwright-side statement of the same rule.

## How to find violations

Any assertion comparing rendered text — `toBe`, `toContainText`, `textContent`,
`getByText` — against a string that looks like a dotted lowercase path. Then:

- **key exists in `en.json`** → the test is asserting on English prose right now;
- **key does not exist** → the test is a time bomb, green until translated.

Both are defects; only the second one is invisible.

## Why it recurs

Nothing in the code *looks* wrong. The literal in the test genuinely is the key.
Seeing the bug requires knowing simultaneously that `setupI18n()` loads real
messages **and** that the fallback echoes the key. Neither fact is visible at the
assertion. This is why the rule has to be stated as a rule rather than left to
inspection.

Characterisation tests are the most exposed, because they outlive ordinary tests
and therefore have the most time to be overtaken by a translation —
see [[concepts/characterisation-test-latch]].

## Source files

| Role | Path |
|------|------|
| Identity precedent — `data-error-key` | `frontend/src/lib/components/brokers/BrokerSharingPanel.svelte` (L379) |
| Converted assertions | `frontend/src/lib/components/brokers/BrokerSharingPanel.test.ts` |
| Catalogue-comparison precedent | `frontend/src/lib/utils/files/imageCrop.test.ts` |
| English catalogue | `frontend/src/lib/i18n/en.json` |
| Rule as stated for the test author | `.github/agents/test-author.agent.md` — rule 5 |
| Playwright-side rule | `LibreFolio_devWiki/wiki/concepts/e2e-data-testid-rule.md` |
