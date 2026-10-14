---
title: "A fixture that skipped on an unexpected status hid an API test for ten months"
category: problem
status: resolved
date: 2026-10-01
first_seen: 2025-11-21
resolved: 2026-10-01
tags: [testing, pytest, fixtures, api, false-green, method]
related: [concepts/span-as-a-detector, concepts/characterisation-test-latch, problems/testid-grep-false-negative, sources/phase00-taxonomy-select-2026-10]
---

# Problem: "1 skipped" was a broken fixture

## What happened

`test_delete_linked_without_pair` (`backend/test_scripts/test_api/test_transactions_api.py`) — the API contract
for deleting one leg of a linked pair — never ran. Its fixture `test_asset_id`:

1. called `GET /assets` without `asset_ids`, a required parameter → **422**;
2. fell back to `POST /assets`, declared `status_code=201` since `0d8ad8ad9` (2025-11-21), but checked `== 200`;
3. and on that mismatch called `pytest.skip("Could not create test asset")`.

The suite reported `22 passed, 1 skipped` for ten months. The test body would not have worked either: it ignored the
fixture's value and repeated the same get-or-create (same 422, a POST with an object instead of a list), used a
non-unique broker name and never checked its setup commits.

## Fix (`3cdee7efa`, 2026-10-01, workstream K step 14)

The fixture creates its **own** asset (unique name, asserts 201 and `success`) and deletes it at teardown — assets
are global rows, so a fixture never borrows one; `DELETE /assets` refuses an asset with transactions, so the test
deletes its own transactions (both legs and the ADJUSTMENT) in a `finally`. After: `23 passed`; the product
contract held (`committed` false, `pairDeleteIncomplete` with `id`/`partnerId`).

## Lesson

- **A setup failure is a failure.** `pytest.skip` in a fixture or setup path turns "my test cannot run" into a
  harmless-looking `s`. Skip only for a declared environmental reason (no network, a provider without that
  capability), never because the code under test answered something unexpected.
- **Read the skip reasons**, not the count: a skip whose reason names the system under test ("could not create",
  "endpoint not implemented") is a test that may never have run.
- The same shape is still latent elsewhere (2026-10-09, read-only check): `test_settings_api.py` skips five checks
  when `PUT /settings/user` or `POST /settings/global/initialize` answers 404 ("endpoint not implemented"). Both
  endpoints exist, so the checks run today — but a renamed route would turn them into skips, not failures.

## Source files

| Role | Path |
|------|------|
| Fixture and test, fixed | `backend/test_scripts/test_api/test_transactions_api.py` |
| `POST /assets` (201), `DELETE /assets` | `backend/app/api/v1/assets.py` |
| Latent skips on 404 | `backend/test_scripts/test_api/test_settings_api.py` |
| Plan (step 14, item 3) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep14TooltipTeardownFixture.prompt.md` |
