---
title: "A Tool's contract is its Pydantic models and its UI a compiled renderer: generated codecs, four version identities, no generic form"
category: decision
status: resolved
date: 2026-09-08
updated: 2026-09-25
tags: [backend, frontend, tools, pydantic, json-schema, codegen, zod, versioning, renderer, registry, release-1.2, workstream-c]
related:
  - features/F-106
  - decisions/tool-calculation-without-authority
  - decisions/tool-item-runs-in-owned-process
  - decisions/provider-registry-decision
  - sources/phase00-tool-platform-2026-09
---

# Decision: one source for the contract, a compiled renderer for the UI

## Context

A Tool is called by a frontend that must render its inputs and results, and the backend must reject anything the
contract does not allow — for nested financial models, in two languages. Two lists written by hand, one in Python and
one in TypeScript, drift; a generic form generated from a schema shows numbers without their meaning.

## Decision

- **Pydantic is the only source.** The models and their `TypeAdapter`s validate and publish the schemas; there is no
  `jsonschema` dependency and no handwritten JSON Schema or TypeScript transport type (the developer's decision,
  plan §1). Every nested model forbids extra fields; every input root requires an `operation` literal **without a
  default**; the operation values must match the declared policies exactly.
- **The fingerprint is generated**, never declared: SHA-256 over the canonical JSON of the input schema (validation
  mode), the output schema (serialization mode) and the sorted operation names.
- **Four identities, kept apart**: `contract_version` and `implementation_version` (package-wide), the schema
  fingerprint, and `ui.version` (a SemVer string owned by each service). Every compute item pins the first three; a
  stale pin returns a per-item `version_mismatch` before any worker starts, and the child checks them again.
- **Generated codecs**: `schema_export.py` writes a build-only OpenAPI 3.1 document with `paths: {}`;
  `frontend/scripts/generate-tools-client.mjs` turns it into strict Zod codecs and a literal contract map keyed by
  service code and contract version. The generated files are git-ignored and rebuilt by `./dev.py api sync`. The
  dossier's reason against a generic schema dictionary: it «avrebbe perso letterali richiesti, union discriminate e
  `extra=forbid` annidato».
- **A compiled renderer per service.** `registry.ts` accepts only source-owned literal imports
  (`defineToolRenderer`); a server descriptor never becomes a module URL. A missing or mismatching registration
  leaves the Tool unavailable with a reason (`renderer_missing`, `schema_mismatch`, …) — never a fallback to a generic
  financial form (the developer's decision, plan §1).
- **Transactional discovery, «perdono tutti».** When two plugins claim the same code, every claimant is quarantined
  (`duplicate_code`): «se due plugin rivendicano lo stesso nome, nessuno dei due è quello che l'utente crede»
  (dossier §1). A failed import leaves no partial registration, healthy siblings stay published, and registration
  closes after publication.
- **Validation is a gate, not a rewrite**: the client validates one plain snapshot and sends those same bytes.

## Options Considered

| Option | Outcome |
|--------|---------|
| Handwritten JSON Schema or TypeScript types | Rejected: a second contract to keep in step |
| A generic schema dictionary as the codec source | Rejected: loses required literals, discriminated unions and nested `extra=forbid` |
| A generic generated financial form when no renderer exists | Rejected: the Tool stays unavailable instead |
| First-wins on a duplicate code, as on the provider registries | Rejected: every claimant is quarantined |
| A demo plugin to show the platform «complete» | Rejected: the renderer registry shipped empty; «il primo consumatore doveva essere vero» |

## Consequences

- A Tool cannot run until the frontend bundle holds a compatible compiled renderer: the PAC planner's arrived on
  2026-09-25 (`0210f9848`), and `registry.ts` holds that one registration today.
- Any change to a model changes the fingerprint, so a released contract must move its version with it. The PAC
  contract has kept `1.0.0` because it has never been released: its fingerprint moved with the compaction
  (2026-10-05), with the FX fix (2026-10-09, `4f061103…` → `a999932e…`) and with the schema texts of the rounding fix
  the same day. The reasoning is the one of [[decisions/ai-export-version-bump-once-per-release]]: a version counts
  from the last release, not from each change.
- The registry pattern of the data providers ([[decisions/provider-registry-decision]]) is reused for discovery, but
  without its first-wins rule and without its retry on a constructor `TypeError`.

## Source files

| Role | Path |
|------|------|
| Schema profile and fingerprint | `backend/app/services/tools/schema.py` |
| Build-only manifest | `backend/app/services/tools/schema_export.py` |
| Transactional registry | `backend/app/services/tools/registry.py` |
| Codec generator | `frontend/scripts/generate-tools-client.mjs` |
| Compatibility check | `frontend/src/lib/features/tools/contracts.ts` |
| Compiled renderer registry | `frontend/src/lib/features/tools/registry.ts` |
| Registry and schema tests | `backend/test_scripts/test_services/test_tools_registry.py`, `backend/test_scripts/test_schemas/test_tools_schemas.py` |
| Developer doc («JSON and generation boundary») | `mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md` |
| Review dossier (§1) | `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/dossier-piattaforma-tool.md` |
