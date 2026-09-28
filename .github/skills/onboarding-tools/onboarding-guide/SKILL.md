---
name: onboarding-guide
description: "Use this skill when creating, extending, or reviewing a LibreFolio onboarding guide — the intro tour, a page, modal or detail guide, or a step-managed guide such as Import or Bulk. Explains the high-level spirit of a guide and its mandatory rules, and points to the developer docs and reference code for up-to-date technical details."
---

# 🧭 Onboarding Guide Skill

> High-level, durable guide to what an **onboarding guide** must do and the spirit it must
> follow. For exact, up-to-date names and behaviour, read the developer docs and the code (see
> [Where to find the technical details](#-where-to-find-the-technical-details)).

## 🎯 What a guide is

A guide is a short sequence of coachmarks that **points at real controls on a real page** and
explains them. It starts in context — when its page, modal or detail view opens — or, for the
intro tour, right after Welcome. The server keeps its versioned status per user (pending,
completed, skipped), and the user can replay it from Settings.

It is **not** a wizard, **not** an automation and **not** a place to write data: the user does
the work with the page's own controls, and the guide follows.

## 🧭 The spirit — mandatory rules

1. **The guide observes; it never acts on the page.** It may scroll a target into view (and the
   intro tour requests its own route and sidebar), but it never clicks, switches a tab, fills a
   field or saves for the user. Finishing a guide and saving work are two independent user
   actions.
2. **Anchor only an element that is actually rendered for that step.** A registered anchor that
   is hidden — a 0×0 box, `visibility:hidden` — counts as absent: the step waits and then stalls
   with *Continue anyway*. When a view hides a region (a tab, a collapsed panel), unmount it or
   leave the anchor off; never hide a registered anchor.
3. **No text announces another guide.** A tour or guide text describes its section or control; it
   never says that a guide will start ("a short guide starts when you choose Add…" is what the
   developer asked to remove, twice). Saying that Settings can replay the guides describes
   Settings, and is fine. A catalog gate test enforces this: add a justified exception to its
   registry, never silence it.
4. **Everything goes through the standard guide controller.** Start, advance, finish, skip,
   suspend and replay only through the shared guide API, and never read or write the guide's
   stored state yourself. That is what gives every guide, for free: persistence, pause and resume
   when the user leaves the page, stall handling, and the **cross-tab close** (a guide that ends in
   one tab closes in the others). A guide that bypasses the controller loses all of them.
5. **State is saved per account, in this browser.** Guide positions and armed replays are keyed by
   account; they survive a closed tab, a browser restart, and logging out and back in on the same
   browser (developer decision, 2026-09-24). They are never shared across accounts, browsers or
   devices.
6. **Changed content means a new version.** Bump the flow's version so users who finished it see
   the new content. A brand-new flow starts pending for every existing user as well: keeping it
   from them is an explicit developer decision, not a default.

## 🛠️ Rough shape of the work

1. Register the flow on both sides: the backend flow registry (version, and the step list for a
   step-managed flow) and the frontend flow list and guide catalog.
2. Describe each step in the overlay host: anchor, texts, host route, allowed modal depth,
   pointer and highlight.
3. Bind the anchors on the real controls; start the guide when its page or modal is ready; when a
   modal closes, let a linear guide restart from its first step.
4. Add the flow to its group in the Settings replay list — the groups are listed by hand — with a
   label.
5. Write every text in four languages through `dev.py i18n`.
6. Cover it: unit tests for catalog or controller changes, and an E2E that walks every step on
   desktop and mobile with a disposable account. Update the E2E specs that list the flows by hand.
7. Update the user flow table and, when a rule changes, the developer docs.

## 📚 Where to find the technical details

This skill is intentionally **high-level and durable**. For the current contract, read:

- **Developer docs** — `mkdocs_src/docs/developer/frontend/components/features/import-wizard.md`
  (import guide wiring, *Anchor presence and stalls*, the browser-stored replay),
  `…/features/settings.md` (the Settings replay section), `…/features/auth.md` (Welcome and the
  intro tour).
- **User docs** — `mkdocs_src/docs/user/settings/preferences.en.md` (*Onboarding and guides*).
- **Reference code** — `frontend/src/lib/features/onboarding/` (guide controller, catalog,
  anchors), `frontend/src/lib/stores/app/onboarding.svelte.ts` (progress and stored replays),
  `frontend/src/lib/components/onboarding/` (overlay host, coachmark, Settings replay section),
  `backend/app/services/onboarding_service.py` (flow registry and versions).
- **Reference tests** — `frontend/e2e/onboarding-guides.spec.ts` with
  `frontend/e2e/fixtures/onboarding-accounts.ts`, and `frontend/e2e/onboarding-tour.spec.ts`.
- **History and decisions** — `LibreFolio_developer_journal/Release_2/Phase_0/21_onboarding/`.

Do not rely on this page for names or signatures — they change; the code and the developer docs
are kept current.
