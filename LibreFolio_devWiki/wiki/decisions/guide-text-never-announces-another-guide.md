---
title: "A tour or guide step describes its own section; it never announces that another guide will start — enforced by a copy gate"
category: decision
status: resolved
date: 2026-09-24
updated: 2026-09-25
tags: [frontend, onboarding, i18n, copy, testing, gate, release-1.2, workstream-j]
related:
  - features/F-105
  - decisions/onboarding-guide-observes-never-acts
  - sources/phase00-onboarding-2026-09
---

# Decision: guide texts never announce another guide

## Context

The usage review of 2026-09-22 found the intro tour telling Transactions users that Import «has a guide of its own»
(R19). Round 8 removed that sentence (`64d78e244`), but at the developer's live review of 2026-09-24 (point 12) the
Brokers stop still read «Una breve guida si avvia quando scegli Aggiungi broker». The developer asked for the
principle to hold **for every text, without having to remember it**. The skill `onboarding-guide` keeps the count:
«"a short guide starts when you choose Add…" is what the developer asked to remove, twice».

## Decision

Written in Round 8, step 8 (C7): *a tour or guide text describes its section; it does not announce that another guide
will start.*

- **The fix** (`208296923`, 2026-09-25): five violations, all the same shape — a second sentence announcing a guide —
  in `onboarding.tour.steps.brokersNav.description` and in the **Add** step of the four page guides (Transactions,
  Brokers, FX, Assets). The first sentence was kept, in four languages; no key was removed.
- **Kept on purpose**: `tour.steps.settingsNav` («…permettono di ripetere qualsiasi guida…» describes what the Settings
  section does) and the first sentence of `transactionsPageGuide.steps.add` («modulo guidato» describes the form).
- **The gate**: `frontend/src/lib/features/onboarding/guideCopy.test.ts` scans every step text of the overlay host, in
  all four languages, for the words that name a guide or a tour. It was red first, on 23 violations (the five keys ×
  four languages, plus `transactionsPageGuide.steps.import.description` in en/fr/es, where «guides» was a verb). A text
  that describes rather than announces goes into its `REGISTRY`, with a reason.
- **The rule for authors** is the third ground rule of the developer doc and is in the skill `onboarding-guide`.

## Consequences

- The `steps` table of `OnboardingOverlayHost.svelte` keeps `titleKey` and `descriptionKey` as string literals,
  because the gate reads them from the source.
- The dead keys of the old tour, which still named the Import guide, went later with the i18n audit (`08b885d43`,
  2026-10-07).

## Source files

| Role | Path |
|------|------|
| Copy gate | `frontend/src/lib/features/onboarding/guideCopy.test.ts` |
| Step table (literal keys) | `frontend/src/lib/features/onboarding/components/OnboardingOverlayHost.svelte` |
| Catalogue | `frontend/src/lib/i18n/base/en.json` |
| Authoring rules | `.github/skills/onboarding-tools/onboarding-guide/SKILL.md` |
| Developer doc | `mkdocs_src/docs/developer/frontend/onboarding.md` |
