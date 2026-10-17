---
title: "An onboarding guide observes and never acts: no clicks, writes or demo data; the Import guide hands off to Bulk and Save All stays the user's"
category: decision
status: resolved
date: 2026-09-10
updated: 2026-09-25
tags: [frontend, onboarding, coachmark, import-wizard, bulk-editor, replay, ux, release-1.2, workstream-j]
related:
  - features/F-105
  - entities/import-wizard-modal
  - decisions/onboarding-positions-in-browser-per-account
  - decisions/guide-text-never-announces-another-guide
  - sources/phase00-onboarding-2026-09
---

# Decision: the guide observes; it never acts

## Context

The brief of 2026-09-10 asked for «a contextual import guide following the **real** conditional wizard steps through
Bulk/Save All, **without automatic writes**» and «no demo financial data». A guide that clicked, filled or saved for
the user would also mean that a broken guide could corrupt a portfolio.

## Decision

The first ground rule of `developer/frontend/onboarding.md`:

- A guide may **scroll its target into view**; the intro tour moves to `/dashboard` and opens the sidebar for its
  stops. Nothing else: **nothing clicks, fills or saves** for the user.
- When a step advances on a click of its target, the click still reaches the control; the coachmark only listens
  (`handleTargetActivate` in `OnboardingOverlayHost.svelte`).
- The `guideAnchor` action registers nodes and does nothing else (`guideAnchors.test.ts`).
- **The Import guide is wiring, not scripting.** The wizard reports its own step (`startImportAt()`, then `setStep()`)
  and renders anchors; it never imports guide content. `handOffToEditor()` passes the rows to the bulk editor, which
  arms `import.bulk` and highlights only **Save All**. **Finish guide** completes the guide step; it never presses
  Save All — finishing the guide and saving the batch are two independent user actions.
- **A replay writes no onboarding status.** Its Finish and X only update or delete the stored position.

## History

- **Round 1** (2026-09-11) removed Pause, demo data and automatic writes, and opened the create modals of Broker, FX and
  Asset as non-writing previews (`tourPreview`). A detour of the same round: Finish and Skip ignored `active.mode`, so a
  replay could flip a flow between `completed` and `skipped`; since then a replay never touches the server status.
- **Round 2** (2026-09-11): on the developer's feedback, the Add guides start on a **real click** on Add, not from a
  preview. The preview handlers survive in `onboardingTourSurfaces.svelte.ts`; per the developer doc no component
  registers one and no step requests one.
- **Round 4**: the Import guide follows the wizard's real milestones instead of a scripted sequence.

## The one constraint: the shell is `inert` during the intro tour

During `intro_tour` the layout sets `inert` on the app shell (`data-guide-inert="true"` in
`routes/(app)/+layout.svelte`), so the page behind the tour cannot be operated; X stays live. Round 1 added it after
keyboard access still reached the controls under the tour. The review dossier (§2.9) names the cost: the tour «feels
modal», a trade made for geometry stability. Contextual guides never make the page inert; a nested dialog only hides
the coachmark (`allowedModalDepth`).

## Consequences

- Welcome **Skip** saves no setting (the user keeps the administrator's defaults); a Welcome **replay** saves its
  choices through `PUT /api/v1/settings/user` and leaves the onboarding status alone.
- A guide that loses its target cannot «help» by acting: it waits, then stalls with **Continue anyway**
  ([[problems/guide-anchor-never-resolves]]).
- Page authors keep the rule through the skill `onboarding-guide` («a guide observes and never acts on the page»).

## Source files

| Role | Path |
|------|------|
| Step table and target listening | `frontend/src/lib/features/onboarding/components/OnboardingOverlayHost.svelte` |
| Anchor action | `frontend/src/lib/features/onboarding/guideAnchors.svelte.ts` |
| Anchor action test | `frontend/src/lib/features/onboarding/guideAnchors.test.ts` |
| Wizard wiring | `frontend/src/lib/features/transactions/import/ImportWizardModal.svelte` |
| Bulk hand-off | `frontend/src/lib/features/transactions/bulk/TransactionBulkModal.svelte` |
| Inert shell | `frontend/src/routes/(app)/+layout.svelte` |
| Unwired previews | `frontend/src/lib/features/onboarding/onboardingTourSurfaces.svelte.ts` |
| Authoring rules | `.github/skills/onboarding-tools/onboarding-guide/SKILL.md` |
| Import guide wiring doc | `mkdocs_src/docs/developer/frontend/components/features/import-wizard.md` |
