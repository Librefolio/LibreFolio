---
title: "An i18n-key assertion is green only until the key is translated"
category: problem
status: resolved
date: 2026-08-31
tags: [frontend, testing, i18n, vitest, false-green]
related_concepts: [concepts/assert-on-identity-not-prose]
related: [concepts/characterisation-test-latch, sources/settings-lane-and-sixteen-defects]
---

# Problem: a test that asserts on `$_()` output looks like it asserts on a key

## Symptom

Five `BrokerSharingPanel` tests, green for the whole life of the lane that wrote
them, all turned red **in the same commit that added their translations** — a
commit that touched no component and no test:

```
AssertionError: expected 'Could not load current sharing settin…'
             to be 'brokers.sharing.loadFailedBlocking'
```

Nothing had broken. The tests had never worked.

## Root cause

The assertions read like they check an i18n **key**:

```ts
expect(errorText()).toBe('brokers.sharing.loadFailedBlocking');
```

But `errorText()` reads the rendered DOM, i.e. whatever `$_()` returned. The
suite calls `setupI18n()`, which loads the real catalogue, so `$_()` **does
translate**.

The assertion passed for one reason only: **the key did not exist yet**, and
`svelte-i18n` falls back to echoing the key when a message is missing. So the
string on screen happened to equal the string in the test.

That makes it a violation of the "never assert on translated text" rule wearing
the disguise of the rule's own remedy. And its failure mode is the worst
possible ordering: the test is green while the feature is untranslated, and goes
red the moment someone completes the translation — blaming the translator for a
defect written weeks earlier.

## Why it is easy to write

Nothing in the code looks wrong. The literal in the test *is* the key. It takes
knowing that `setupI18n()` loads real messages **and** that the fallback echoes
the key to see that the two facts cancel out.

## Fix

Assert on **identity**, not on prose. The component now publishes the key it is
rendering:

```svelte
<div data-testid="broker-sharing-panel" data-error-key={errorKey}>
```

```ts
expect(panel()).toHaveAttribute('data-error-key', 'brokers.sharing.loadFailedBlocking');
```

Seven assertions across five tests were converted this way.

The alternative, acceptable when the message has no identity in the code, is to
import the catalogue and compare against it — `import en from '$lib/i18n/en.json'`
then `en.brokers.sharing.loadFailedBlocking`. The literal is then never written
by hand, and the test stays true in all four languages. `imageCrop.test.ts` uses
this form.

## How to detect it elsewhere

Any assertion comparing rendered text — `toBe`, `toContainText`, `textContent`
— against a string that looks like a dotted i18n path. Grep for `'` followed by
a dotted lowercase path inside an `expect`. If the key exists in `en.json`, the
test is already asserting on English prose; if it does not, the test is a
time bomb.

## Source files

| Role | Path |
|------|------|
| Component publishing the key | `frontend/src/lib/components/brokers/BrokerSharingPanel.svelte` |
| Converted assertions | `frontend/src/lib/components/brokers/BrokerSharingPanel.test.ts` |
| Catalogue-comparison precedent | `frontend/src/lib/utils/files/imageCrop.test.ts` |
| Rule it violates | `.github/agents/test-author.agent.md` — rule 5 |

## See also

- [[concepts/assert-on-identity-not-prose]] — the rule this page is the proof of.
  (The frontmatter pointed at it from 2026-08-31; the page was written 2026-09-01.)
- [[concepts/e2e-data-testid-rule]] — the same rule stated for Playwright.
- [[concepts/characterisation-test-latch]] — characterisation tests live longer
  than ordinary ones, so they are the most exposed to this failure mode.
- [[sources/settings-lane-and-sixteen-defects]] — the lane that produced it.
