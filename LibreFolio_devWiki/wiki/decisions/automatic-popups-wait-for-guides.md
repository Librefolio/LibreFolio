---
title: "Automatic popups wait for guides and modals; a popup the user asked for opens at once"
category: decision
status: resolved
date: 2026-09-11
updated: 2026-09-24
tags: [frontend, onboarding, popups, donation, update-check, modals, layout, release-1.2, workstream-j]
related:
  - features/F-105
  - features/F-104
  - features/F-004
  - sources/phase00-onboarding-2026-09
---

# Decision: unrequested popups take the lane only when nothing else is on screen

## Context

Two prompts appear without the user asking: the **donation** prompt, decided by the backend at sign-in
(`record_login_and_maybe_show_popup()` in `backend/app/services/donation_popup_service.py`), and the
**update-available** modal. Opened over a running guide, either would cover the coachmark's target or steal the
user's first minutes.

## Decision

`DeferredAppPopups.svelte`, mounted by the `(app)` layout since `8a8e686f0` (2026-09-11; the main plan's step 9,
«popup priority»), owns the unrequested popups:

- while a guide is active, or any modal is open (`document.body.dataset.modalScrollLockCount > 0`), **none is shown**;
- when both are gone, the next one is shown: **donation first, then update**;
- a popup already on screen stays until dismissed.

The order is workstream J's own choice; the review dossier (§2.8) records it as «onboarding beats everything, donation
beats update», a choice nobody had specified. The dossier also describes the prompts as «suppressed entirely, not
queued-and-shown-after»; the component it reviewed (`580bd504f`) already showed them once the guide and the modals
were gone, as today — a due prompt stays due in its store.

## The exception: what the user asked for (Round 8, Q2)

The usage review of 2026-09-22 (R3) found that a manual **check for updates** from the changelog showed a newer
release only after the changelog closed: the lane held it back like an unrequested popup. Q2, approved with the Round 8
plan: a requested result opens **at once, above** the changelog — `updateAvailable.show(release, {requested: true})`,
with `DeferredAppPopups` skipping the wait for that one (`64d78e244`, 2026-09-24). Developer, point 11 of the review of
2026-09-24: «ora funziona». R4 («no "you are up to date"») did not reproduce once the version string was fixed.

## Consequences

- A donation prompt due at sign-in waits behind Welcome, the intro tour and any guide; it is not lost.
- `DonationPopupModal.svelte` has no close button and ignores the backdrop and Esc; only its two actions dismiss it,
  and its share button opens the dialog of [[features/F-104]] above it.
- Tests: `DeferredAppPopups.test.ts` holds automatic prompts while showing a requested one.

## Source files

| Role | Path |
|------|------|
| Popup lane | `frontend/src/lib/features/onboarding/components/DeferredAppPopups.svelte` |
| Popup lane test | `frontend/src/lib/features/onboarding/components/DeferredAppPopups.test.ts` |
| Requested flag | `frontend/src/lib/features/update-check/updateCheckStore.svelte.ts` |
| Donation state | `frontend/src/lib/stores/app/donationPopupStore.svelte.ts` |
| Donation decision at sign-in | `backend/app/services/accounts/donation_popup_service.py` |
| Layout mount | `frontend/src/routes/(app)/+layout.svelte` |
| Developer doc | `mkdocs_src/docs/developer/frontend/onboarding.md` |
