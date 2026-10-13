---
title: "A destructuring default of {accepted: true} read a missing event detail as the user's consent"
category: problem
status: resolved
date: 2026-09-24
tags: [frontend, events, defaults, consent, sync, svelte, static-analysis, latent]
related:
  - features/F-033
  - sources/phase00-feedback-jobs-2026-09
---

# Problem: an omission that meant «yes»

## Symptom

Latent, found by the static analysis of 2026-09-22 (folder 09, §2.5): any future call to the asset page's
`handlePageSyncComplete()` without an argument would have been read as acceptance, and would have re-run the
calendar-return computation in silence.

## Root Cause

The handler destructured `{accepted}` with the default `{accepted: true}`. The event travels from `PageSyncModal`
through the risk panel and its view to the page, and it worked only because every link passed the detail along; a
comment guarded that contract, nothing guarded the default if the contract broke.

## Solution

`ff9038487` («fix(assets): read missing sync detail as cancel»): the default is now `{accepted: false}` — an omission
means cancel.

## Prevention

A default must be the safe answer: never let a missing value stand for the user's consent.

## Source files

| Role | Path |
|------|------|
| The handler | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| The modal that emits the detail | `frontend/src/lib/components/ui/modals/PageSyncModal.svelte` |
| Journal (§2.5) | `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/09_reperti_analisi_statica_20260922.md` |
