---
title: "Playwright 1.61 aborts every image whose URL ends in `/favicon.ico` once a route is registered: the gallery lost the broker and provider logos"
category: problem
status: resolved
date: 2026-10-08
tags: [frontend, testing, playwright, e2e, gallery, screenshots, routes, favicon, broker-icons, workstream-m]
related:
  - decisions/gallery-is-a-release-gate-with-real-data
  - problems/playwright-probes-ignore-timeout
  - problems/broker-icon-race-condition
  - features/F-074
  - sources/phase00-release-images-and-gallery-2026-10
---

# Problem: the logos that only the gallery could not load

## Symptom

In the 1.2 gallery the brokers' logos, most import plugins' icons and the FED and SNB provider icons drew their
fallback, while the published 1.1 gallery, shot with no route installed, shows them.

## Root Cause

Playwright 1.61 takes any request whose URL ends in `/favicon.ico` for the page's own favicon (playwright-core,
`coreBundle.js`: `_isFavicon`). Once a route is registered — on the page or on its context, whatever it matches — it
aborts that request before a single handler runs (`requestStarted`).

The gallery's outer `beforeEach` registers routes on every page, for the temporary data and the offline guard
([[decisions/gallery-is-a-release-gate-with-real-data]]). And those icons are `/favicon.ico` URLs: `BrokerIcon`, for
one, falls back to the broker portal's origin plus `/favicon.ico` (`brokerIconChain.svelte.ts`, `brokerHelpers.ts`).
Every one of those `<img>` failed.

## Solution

`keepFaviconImagesLoading` (`73680c052`, 2026-10-08), an init script installed before the first navigation, writes
those URLs with a query, `…/favicon.ico?lf-gallery`: Playwright no longer takes them for the favicon, and every host
involved answers with the same bytes. It rewrites only the URL written into an image — the `src` property,
`setAttribute('src', …)` and `src` attributes in HTML set through `innerHTML` — so each logo is the same live image
from the same host, and no product code changes. A URL that does not end in `/favicon.ico` (BOE's
`favicon.svg?ver=…`) is left alone.

`expectFaviconImagesLoading` checks at the end of each test that the script is still in force.

## Prevention

- When a Playwright route is installed for an unrelated reason, an image ending in `/favicon.ico` will not load in
  that test: compare a shot with the published gallery, or with the same page in a browser, before blaming the app.
- The same version hides another trap, probes that do not wait for their timeout
  ([[problems/playwright-probes-ignore-timeout]]).
- This is not the broker icon race of the app, which is a product defect seen outside the tests
  ([[problems/broker-icon-race-condition]]).

## Source files

| Role | Path |
|------|------|
| `keepFaviconImagesLoading`, `expectFaviconImagesLoading` | `frontend/e2e/fixtures/galleryReportSets.ts` |
| Gallery spec (outer `beforeEach`) | `frontend/e2e/gallery.spec.ts` |
| The favicon fallback of a broker logo | `frontend/src/lib/utils/broker/brokerIconChain.svelte.ts` |
| Portal origin helpers | `frontend/src/lib/utils/broker/brokerHelpers.ts` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseGallery.prompt.md` |
