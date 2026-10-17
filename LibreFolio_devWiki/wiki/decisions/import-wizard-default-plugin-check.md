---
title: "Import wizard: a file its broker's default plugin cannot read is flagged, with the plugin's own reason"
category: decision
status: resolved
date: 2026-10-09
updated: 2026-10-10
tags: [brim, import-wizard, plugins, frontend, backend, api, i18n, workstream-s, release-1.2]
related:
  - decisions/scalable-two-accounts-two-plugins
  - concepts/brim-texts-translated-by-code
  - problems/brim-compatible-plugins-frozen-at-upload
  - decisions/brim-report-sets
  - entities/import-wizard-modal
  - features/F-049
  - sources/phase00-brim-scalable-2026-10
---

# Decision: the import wizard checks each file against its broker's default plugin

## Context

When a broker's default plugin could not read an uploaded file, the wizard **silently** picked the first compatible
plugin (`pickBestPlugin`): a Scalable overnight-account file dropped on the broker would have been read by the right
plugin into the wrong broker. A plugin's reason for refusing a file (`cannot_parse_reason`, an English sentence)
reached only the 400 of a parse: no API exposed it earlier.

## Decision

The developer, 2026-10-09: «Avanti così: base `cannot_parse_reason`, più codice per le traduzioni ed endpoint al
caricamento» ("go ahead: based on `cannot_parse_reason`, plus a code for the translations and an endpoint at upload").
DEGIRO's order list (accept the file and warn) would never trigger the check, and Danske's 422 `set_required` concerns
only report sets.

- **Contract**: an optional `cannot_parse_detail(file_path) -> Optional[BRIMRefusal]` on `BRIMProvider` — `code`,
  `message` (the English sentence), `context`. By default it wraps `cannot_parse_reason` with no code, so the existing
  plugins did not change; it never raises.
- **Endpoint**: `GET /api/v1/brokers/import/files/{file_id}/plugin-check?plugin_code=…` → `BRIMPluginCheck`
  (`plugin_code`, `can_parse`, `refusal`), run off the event loop, with the access of the other broker files; an
  unknown plugin or file is a 404. `check_file_with_plugin()` retries on the new path when a concurrent parse moved the
  file.
- **The wizard**: after the uploads of step 1, `reviewDefaultPluginMismatches` opens `ImportBrokerMismatchModal` once
  per file whose broker's default plugin is not among the file's `compatible_plugins`. It shows the plugin's reason,
  translated by its code, and the brokers whose default plugin reads the file. **Move** re-uploads the file to the
  chosen broker with the same `batch_id`, then deletes the original; **Keep here** is the old behaviour (closing the
  modal means the same); **Remove** deletes the upload. `findDefaultPluginMismatch` (`defaultPluginCheck.ts`) is pure.
- **For every broker**, not only Scalable. Two exemptions came from the test author's reading:
  - a file read by a **report-set** plugin is never questioned — a Danske Bank member on a broker with the generic CSV
    as default would otherwise break the report-set flow ([[decisions/brim-report-sets]]);
  - **fallback plugins** (`detection_priority` below 50) are offered as a destination only when no dedicated plugin
    reads the file, and the destinations follow the order of `compatible_plugins`.
- «Continue» stays disabled, with a spinner, while step 1 goes on — upload, this check and the report-set check
  (`step1Continuing`, reset in a `finally`).

## Consequences

- After the developer's test, the modal shows the assigned broker with its icon and «cannot read it», «Notes from the
  plugin», and the destinations as cards, with radio buttons when there is more than one (`2046b7419`, 2026-10-10).
- Tests: `TestPluginSaysWhyWithACode` (the contract, for every plugin and sample), the endpoint's
  `TestPluginCheckEndpoint` (RS-PC01…07), Vitest `defaultPluginCheck.test.ts` and `ImportBrokerMismatchModal.test.ts`,
  E2E `tx-import-broker-mismatch.spec.ts` (M1–M4).
- The `compatible_plugins` it compares are the upload's detection — see
  [[problems/brim-compatible-plugins-frozen-at-upload]] for when that list was stale.
- If a move fails, an error message stays and the file remains in the original broker.
- The check reads the wizard's broker list. Until plan 44 (train 48) a quick «Next» could run it on an empty list;
  step 1 now waits for every broker load — [[problems/import-wizard-next-before-brokers-loaded]].

## Links

- [[decisions/scalable-two-accounts-two-plugins]] — the case that asked for it
- [[concepts/brim-texts-translated-by-code]] — `importWizard.parseRefusal.<code>`
- [[entities/import-wizard-modal]], [[features/F-049]]

## Source files

| Role | Path |
|------|------|
| `cannot_parse_detail`, `check_file_with_plugin` | `backend/app/services/brim/brim_provider.py` |
| `BRIMRefusal`, `BRIMPluginCheck` | `backend/app/schemas/brim.py` |
| The `plugin-check` endpoint | `backend/app/api/v1/brokers.py` |
| `findDefaultPluginMismatch`, `resolveParseRefusalMessage` | `frontend/src/lib/features/transactions/import/defaultPluginCheck.ts` |
| The modal | `frontend/src/lib/features/transactions/import/ImportBrokerMismatchModal.svelte` |
| `reviewDefaultPluginMismatches`, `step1Continuing` | `frontend/src/lib/features/transactions/import/ImportWizardModal.svelte` |
| Contract tests | `backend/test_scripts/test_external/test_brim_providers.py` |
| E2E | `frontend/e2e/transactions/tx-import-broker-mismatch.spec.ts` |
| BRIM guide, «Saying why with a code» | `mkdocs_src/docs/developer/architecture/patterns/brim_plugin_guide.md` |
