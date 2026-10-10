---
title: "A premise gate keyed by content: fail when the set of sites changes, not when a line moves"
category: concept
tags: [testing, gates, method, privacy, i18n, false-positive, anti-regression]
related: [decisions/privacy-mask-at-the-formatter, concepts/span-as-a-detector, concepts/characterisation-test-latch, problems/i18n-audit-false-dead-and-false-used, concepts/echarts-chart-gotchas, decisions/html-escape-at-the-source]
---

# Concept: gate the premise, key it by content

## Definition

Some rules are only sound while a set is known. Privacy masking works because every amount of money is rendered
through a small set of formatters; the rule "a site is safe if it comes out of one of them" breaks silently the day
someone writes a new formatter. A **premise gate** does not test behaviour: it scans the source for the observable
forms of the thing (money rendering) and fails when a site appears that is not in its registry. Registering a site
is a human decision, recorded once.

Two design rules make it survive:

1. **Key by content, not by line.** An unrelated edit above a site shifts its line; a line-keyed registry goes red
   for reasons that have nothing to do with the rule, people learn to update it without reading it, and then it
   protects nothing.
2. **Do not judge intent.** A gate that decides whether a new site is safe will be wrong in an annoying direction
   and get switched off. It only says "this is new".

It must also say what it cannot see. The privacy gate states its completeness limits in its header ("Completeness,
stated honestly"): it does not see ECharts axis formatters, which only behaviour tests cover (backlog I-05).

## Where it applies

- `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` — the money-rendering sites (Release 2, U2).
- The same idea, applied to data instead of call sites: the tooltip-HTML gate checks the **catalogues** — every
  translation must render as itself — instead of escaping ~109 interpolation sites
  (`frontend/src/htmlInterpolation.gate.test.ts`).
- The two XSS gates of 2026-09-30: the interpolation gate (sources: user text in hand-built HTML must pass
  through `escapeHtml`) and `frontend/src/htmlSink.gate.test.ts` (every `{@html}` is `sanitizeHtml(…)` or a
  reviewed entry keyed by content) — [[decisions/html-escape-at-the-source]].
- Related failure it avoids: a gate that cries wolf ([[concepts/span-as-a-detector]]).

## Source files

| Role | Path |
|------|------|
| Money-site premise gate | `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` |
| Catalogue HTML gate | `frontend/src/htmlInterpolation.gate.test.ts` |
| The rule it protects | `frontend/src/lib/utils/privacy/maskable.ts` |
