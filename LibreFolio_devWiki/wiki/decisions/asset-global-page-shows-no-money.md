---
title: "Asset Global shows no money, and the guard must be a net rather than a grep"
category: decision
status: accepted
date: 2026-09-05
tags: [frontend, risk, asset-set, ux, testing, invariant, weights, correlation]
related:
  - problems/asset-set-scope-has-no-primary-series
  - problems/front-check-does-not-check-what-you-think
---

# Decision: Asset Global shows no money — and how that is actually guarded

## Context

Two surfaces run the same risk analyses over different subjects:

- the **portfolio** surface, where holdings carry weights, so an analysis can answer
  *"what happens to me"* — in euros;
- the **Asset Global** page, a laboratory over an arbitrary set of instruments with no
  weights, which can only answer *"how do these behave"* — in percentages.

Stated as a rule:

> **With weights → euros → "me". Without weights → percentages → "these".**

## Decision

On the Asset Global page **no amount of money representing a position, an exposure, or
a portfolio impact is ever rendered**, in any panel.

Two things are explicitly *not* forbidden, because forbidding them would be wrong:

- the **currency code** as a label or badge (`EUR`) — naming a currency is not
  quoting a position;
- a **unit list price** elsewhere on the page, which is a property of the instrument,
  not of anyone's holding.

The rule is about *whose* money is implied, not about the glyph.

## The part that is easy to get wrong

The obvious guard — load the page, assert no `€` appears — is **worthless here**, and
worth understanding why.

Today the euro on this page is **absent, not prevented**. For an asset-set scope the
service builds empty per-asset values and a null scope value; the stress plugin
consequently returns `None` for every amount; the frontend renders an em dash. So a
test asserting "no euro on screen" passes *because the backend sent no numbers*.

And the frontend has **no guard at all** — this was verified, not assumed, and it is
the opposite of what the plan assumed. `RiskAnalysisPanel.svelte` renders
`formatAmount(stressOutput?.impact_amount)` on a KPI card and
`formatAmount(impact.impact_amount)` in every impact row, and `formatAmount` reaches
`Intl.NumberFormat({style: 'currency'})`. **Nothing consults `scope.kind`.** Feed the
page an `impact_amount` and it prints a euro amount in two places.

So the rule is not held up by an invariant. It is held up by the fact that *today*
nobody computes those numbers. The day anyone gives an asset set implicit weights —
equal weighting is the most natural thing in the world to add — the euros appear by
themselves, on the one page whose entire thesis is that it has none.

**The guard must therefore be a test that stubs the money in.** It feeds the page an
`impact_amount` that the backend does not currently produce and asserts that no
currency-formatted amount is rendered. Written against the code as it stands, that
test is **red**, and the red is the point: it is the first thing in the codebase that
states the rule in a form capable of failing.

Assertions target the *formatted* forms — the `€` glyph, the `currency-symbol` span
emitted by the currency formatter, and the stubbed magnitude with thousands separators
in both `1,234.56` and `1.234,67` conventions — never the bare currency code.

## Blast radius, if you go to fix it

`AssetRiskScope` is built the same way — empty values, null scope value — so the same
unguarded renderer also serves the **asset-detail Risk tab**. A `scope.kind` guard is
therefore not a one-line change to one page; it is a contract decision across two
surfaces, and it needs to answer what the asset-detail tab should show.

## Consequences

- The rule is falsifiable, which is the only sense in which it is enforced.
- It also explains a cancelled deliverable: without weights there is no aggregate, so
  the set has neither a euro nor a drawdown. See
  [[problems/asset-set-scope-has-no-primary-series]].
- A plain `grep` for `€` over the source is *not* an acceptable substitute and will
  produce a false positive anyway, since the legitimate unit-price formatter appears
  on the same page.

## Source files

| Role | Path |
|------|------|
| The panel under the rule | `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte` |
| **Renders the money unguarded** — no `scope.kind` check | `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte` |
| Renders the em dash for absent amounts | `frontend/src/lib/components/risk/riskAnalysisHelpers.ts` |
| Empty values / null scope value for an asset set **and for a single asset** | `backend/app/services/risk/service.py` |
| Returns no amount without weights | `backend/app/services/risk_plugins/stress.py` |
