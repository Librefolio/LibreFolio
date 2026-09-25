---
title: "Asset Global shows no money, and the guard must be a net rather than a grep"
category: decision
status: accepted
date: 2026-09-05
updated: 2026-09-23
tags: [frontend, risk, asset-set, ux, testing, invariant, weights, correlation, privacy]
related:
  - problems/asset-set-scope-has-no-primary-series
  - problems/front-check-does-not-check-what-you-think
  - concepts/characterisation-test-latch
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

## Later development — measured 2026-09-23

*"The frontend has **no guard at all**"* was true on 2026-09-05. It no longer is. On
`f1047f766`:

| guard | where | since | nature (09 §3.11) |
|---|---|---|---|
| `formatScopedCurrencyAmount` returns `—` for every scope that is not `portfolio`; the legacy `RiskAnalysisPanel.formatAmount` goes through it | `riskAnalysisHelpers.ts` | `bf34f3a0a`, 18/09 | money that exists and is silenced |
| `AssetSetReplaySection` passes `showMoney={false}` to `L4Replay`, whose two money sites sit behind `!showMoney \|\| …` | `AssetSetReplaySection.svelte` | `6b8c69bfc`, 21/09 | money that exists and is silenced |
| the L1°/L3° helpers take no currency parameter at all — nothing there computes, returns or accepts an amount | `assetSetLevels.ts` | `032b86959`, 21/09 | money that does not exist |

*"The first is safe as long as a flag holds; the second has no flag to drop."*

- **The blast-radius question above was answered in the shared formatter**: `—` on `asset` as
  well as `asset_set`. The asset-detail Risk tab mounts `RiskAnalysisPanel` with
  `scope.kind: 'asset'`, so it shows no euro either; the docstring cites D107 — *"an invented
  euro reads exactly like a measured one."*
- The legacy panel no longer mounts on Asset Global (`daa03c0f2`, 21/09).
- **The net still stubs money in** — `risk-lab.spec.ts` › *"prints no money, even when the API
  hands it some"*, now aimed at the historical replay — and it is **no longer red**: `risk-lab`
  ran 11/11 green on `f1047f766` with the spec untouched (F-1, 23/09).

### New, 23/09 — under global privacy the net is blind

09 §1.6/§9.2 (22/09) concluded that under privacy only the *value* assertion goes blind,
because the mask of `currencyFormat.ts` covers the number and leaves symbol, flag and code
outside. That holds for `currencyFormat.ts` — **not on the laboratory's path**. `L4Replay`
formats with the risk formatter, `formatCurrencyAmount` in `riskAnalysisHelpers.ts`, which
under privacy returns `•••` **in place of the whole string**. Executed by F on 23/09:
`npx vitest run src/lib/components/risk/riskAnalysisHelpers.test.ts -t "with global privacy on"`
→ 1 file passed, 7 tests, `.toBe(PRIVACY_PLACEHOLDER)`.

| assertion | privacy off | privacy on, today |
|---|---|---|
| `MONEY_PATTERN` — the value | ✅ | ❌ blind |
| `'€'` — the channel | ✅ | ❌ blind: the whole string is `•••` |
| `.currency-symbol` count 0 | ⚠️ never guarded this formatter: only the HTML formatters of `currencyFormat.ts` emit that class | ❌ |

A scope-violating euro printed through `L4Replay` with privacy on would pass all three.

- **Pinned off.** The money test now switches privacy off through the header control,
  `privacy-toggle`, and asserts its public state `aria-pressed="false"` — never through the
  storage key. On 23/09 this is in F's working tree, uncommitted, with its before/after run
  still to do (F-1b).
- **The privacy-on variant waits for workstream J**, who repairs the formatter: privacy should
  hide the number, not the currency. The coordinator classified today's behaviour a defect on
  23/09; the unit test pins it as *"a deliberate asymmetry, pinned rather than judged"*, so J's
  repair will turn that test red — which is what a pin is for
  ([[concepts/characterisation-test-latch]]). The variant must assert on the rendered output
  (`not.toContain('•••')`, and `'€'` if J keeps the currency) and must not reuse J's `SAFE_CALL`
  (09 §3.12).
- **Latent inconsistency in assertion 3**: `.currency-symbol` has a second source,
  `formatCurrencyCodeHtml` — a currency code with no amount, which this decision explicitly
  allows. Left for the closure of `risk-lab` (F-6).

### 24–25/09 — the redesigned selection card keeps the rule

The F-3b redesign added three surfaces, and none carries an amount:
- the "+" picker's rows show a name, a type and a currency code;
- the holdings command ("All mine" / one broker) reads only `summary.holdings[].asset_id` from the light report;
- the chips show a name and, for an asset Risk's engine rules out, the engine's reason.

The net — *prints no money, even when the API hands it some* — passes on the realigned spec (F-6, 16/16), which now
stubs the eligibility engine and waits for every chip's verdict before asserting
([[decisions/lab-eligibility-from-risk-engine]]).

## Source files

| Role | Path |
|------|------|
| The panel under the rule — mounts the three sections | `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte` |
| Rendered the money unguarded on 2026-09-05; since `bf34f3a0a` through `formatScopedCurrencyAmount` | `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte` |
| Em dash for absent amounts; `formatScopedCurrencyAmount` (scope guard); `formatCurrencyAmount` (whole-string privacy mask) | `frontend/src/lib/components/risk/riskAnalysisHelpers.ts` |
| Pins the mask — `with global privacy on` | `frontend/src/lib/components/risk/riskAnalysisHelpers.test.ts` |
| Passes `showMoney={false}` | `frontend/src/lib/components/risk/AssetSetReplaySection.svelte` |
| Money sites behind `!showMoney`; formats with the risk formatter | `frontend/src/lib/components/risk/levels/l4/L4Replay.svelte` |
| L1°/L3° arithmetic with no currency parameter | `frontend/src/lib/components/risk/assetSetLevels.ts` |
| Asset-detail Risk tab — `RiskAnalysisPanel` on `scope.kind: 'asset'` | `frontend/src/lib/components/risk/AssetRiskScenariosView.svelte` |
| Masks the number, keeps the currency; the only emitters of `.currency-symbol` | `frontend/src/lib/utils/currency/currencyFormat.ts` |
| `privacy-toggle`, `aria-pressed` | `frontend/src/lib/components/ui/PrivacyToggle.svelte` |
| The net — *prints no money, even when the API hands it some*; `pinPrivacyOff` | `frontend/e2e/portfolio/risk-lab.spec.ts` |
| Empty values / null scope value for an asset set **and for a single asset** | `backend/app/services/risk/service.py` |
| Returns no amount without weights | `backend/app/services/risk_plugins/stress.py` |
| F's plan — §1 (09 §1.6/§9.2), §3.1, F-1, F-1b | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/F-laboratorio-postmerge.md` |
| The 22/09 sheet — §1.6, §3.11, §3.12, §9.2 | `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/09_reperti_analisi_statica_20260922.md` |
