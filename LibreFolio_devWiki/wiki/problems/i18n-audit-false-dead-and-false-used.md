---
title: "The i18n audit called 118 live keys dead and absolved 481 dead-or-alive ones"
category: problem
status: resolved
date: 2026-10-07
tags: [frontend, backend, i18n, tooling, audit, false-positive, gates]
related: [problems/svelte-i18n-formatter-cache-ignores-locale, decisions/i18n-key-rationalization, problems/i18n-key-assertion-false-green]
---

# Problem: the i18n usage audit was wrong in both directions

## Symptom

On 2026-10-06 `./dev.py i18n audit` listed 250 «likely unused» keys. A key-by-key check found
**118 of them alive** — rendered through wrappers, props, backend dictionaries and relative helpers.
At the same time the whole `risk.*` namespace (481 keys) could never be reported, and keys named only
by tests counted as used.

## Root causes

1. **Tests were evidence.** The scan read `*.test.ts`, `__tests__/` and `__mocks__/`: 774 strings and
   19 prefixes (the bare roots `common` and `onboarding` among them) existed only there.
2. **Only four callee names.** A key was a reference only inside `t(`, `$t(`, `_(` or `$_(`; real
   code also uses `translateOr($_, 'k', …)`, `label('k', …)`, `translate('k')`, `tr('k', …)` and
   props such as `afterCopyKey: 'k'`.
3. **Half of the backend.** Only `…_i18n_key="literal"` assignments were read: a dictionary of keys
   (`lots_analysis_service.py`, `_message_key_for_issue`) and an f-string family
   (`ai_export/analyses/catalog.py`, `f"aiExport.additionalData.reason.{reason}"`) were invisible,
   and the producer vocabulary was lowercase snake_case only (no `NO_DATA`, no `deeperTechnical`, no
   `"Health Care"` → `HealthCare`).
4. **A family names its members in its own file**, and nobody read them: `text('compute.title')` over
   `` `${KEY}.${key}` ``, a `titleKey:` list read as `` `importWizard.${step.titleKey}` ``, a map
   read as `` `chartSettings.${EVENT_BADGE_KEY[t] ?? 'badgePoints'}` ``.
5. **A union of one.** `RiskResultFrame.svelte` narrowed `prefix: 'errors' | 'warnings'` to
   `prefix: 'errors'`; the union expander wanted two members, so the bare root `risk` came back and
   absolved the namespace — the regression the typed-union rule had been written to stop.
6. **Paired backticks.** A template nested in another template's interpolation
   (`CorrelationHeatmap.svelte`) was never seen; those families survived only through legacy prefixes,
   which counted as proof of use.

## Fix (Release 2, workstream O)

`scripts/i18n_usage.py` now: walks product sources only; counts any whole-key literal anywhere
(frontend and backend); expands single-literal parameter types; harvests backend f-string families
and a vocabulary of any case; reads the members a building file names (narrow families only for
plain quoted words); records `` `${key}Full` `` suffixes; parses nested templates; demotes legacy
prefixes from «used» to «not verified»; and reports backend families with no catalogue key (👻,
today `tools.allocation.constraints.` from `pac_allocator/evaluator.py`). 77 new cases in the gate,
each rule proven in both halves.

Result on the same tree: **180 dead** instead of 250, none of them alive; the tool also caught two
keys the manual review had wrongly kept (`aiExport.additionalData.reason.{fifoDetail,performanceContext}`,
no producer since `c9f840680`). Remaining limit: the backend vocabulary is shared by all families, so
a common word can still make a dead key look used (`…planner.result.sections.assets`).

### Second pass on the release tip (same day, `d07412899`)

With the dashboard (N) and risk (A13) work merged, 78 live keys still read «not verified», and a
component nobody imported (`planner/shared/AgeLabel.svelte`) still proved its five keys «used».
Five more rules, each again proven in both halves (94 new gate cases, 195 in all):

- **One import hop.** A narrow family also reads the words of the modules its file imports directly:
  `CorrelationHeatmap.svelte` builds `risk.assetSet.band.${band}`, the bands are a union in the
  imported `correlationHelpers.ts`. Two hops, an unimported neighbour or a wide family read nothing.
- **Unreferenced sources.** Reachability from the SvelteKit entries (route files under `routes/`, the
  root hooks, the service worker) through static and dynamic imports. The report lists under 📦 the
  keys only unreachable files keep alive; informational, it changes no verdict.
- **Generated clients are no sources.** `lib/api/generated.ts` exists only after `api sync`, so a verdict
  resting on it flipped on a fresh clone; it is no import witness either.
- **Codes in other spellings.** `"3m"` is a code, and `IN_TRANSIT` witnesses `in_transit`.
- **Shapes.** `assets.providerParams.${code}.${kind}.${field.key}` keeps its shape: one-segment slots,
  a union slot restricted to its members, every slot named by the file, its imports or the producer.

Result: **0 dead, 3 not verified**, all live: `chartSettings.params.{amplitude,histogramScale}`, whose
member sits two imports away, and `transactions.fields.cash_code`, built from the validation path
`cash.code` of a Pydantic field the vocabulary cannot see. A fourth, `onboarding.settings.groups.contextual`,
was dead in fact — its group was replaced in `580bd504f` — and only a per-key check could tell: the tool
rightly refuses to call an unnamed member of a narrow family dead. It was removed with the batch.
`AgeLabel.svelte` went with its keys; `onboardingTourSurfaces.svelte.ts` and `stores/core/EditBuffer.ts`
are unreferenced too, but read no key (knip backlog).

## Lesson

An audit that only ever answers «used» on partial evidence is not conservative, it is blind: the
three verdicts (used / not verified / dead) only work if «used» needs proof and «not verified» is
where every unproven-but-plausible key lands. The converse holds too: a «not verified» list that
shrinks to a handful is worth a per-key check, because that is where a dead member of a live family
hides.

## Source files

| Role | Path |
|------|------|
| Evidence engine | `scripts/i18n_usage.py` |
| CLI and report | `frontend/scripts/i18n-audit.py` |
| Gate (PURE) | `backend/test_scripts/test_utilities/test_i18n_usage_gate.py` |
| Skill (rules for contributors) | `.github/skills/devpy-tools/devpy-i18n/SKILL.md` |
| Plan (§5, Appendix A) | `LibreFolio_developer_journal/Release_2/phases/29_i18nAudit/plan-phase00I18nAudit.prompt.md` |
