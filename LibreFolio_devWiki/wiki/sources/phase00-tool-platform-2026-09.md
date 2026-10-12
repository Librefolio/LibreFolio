---
title: "Phase 0 / 16 — the atomic Tool platform (workstream C), with the capacity round of workstream D"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/plan-phase00ToolPlatform.prompt.md
tags: [phase0, release2, workstream-c, workstream-d, tools, plugins, multiprocessing, codegen, capacity]
related:
  - features/F-106
  - decisions/tool-calculation-without-authority
  - decisions/tool-item-runs-in-owned-process
  - decisions/tool-contract-from-pydantic-compiled-renderer
---

# Source: Phase 0 / 16 — the Tool platform

## Summary

Folder 16 holds four files (about 96 KB); a fifth source, the capacity round, lives in the PAC folder because
workstream D wrote it. Together they tell how the platform of [[features/F-106]] was built by workstream C in three
days, frozen, then reshaped by its first real consumer before reaching `dev_release2`.

| File | Dates | What it adds |
|------|-------|--------------|
| `16_toolPlatform/plan-phase00ToolPlatform.prompt.md` | 2026-09-08 → 10-10 | The developer's decisions (§1), steps 1–6, the initial policy (§3, superseded), the merge with the runtime lanes (§4) and the hardening (§4.1); «Cosa resta aperto»: nothing of C |
| `16_toolPlatform/manifest-integrazione-C.md` | 2026-09-10 → 10-09 | Inventory of the checkpoint (55 files), the generated files that must never be committed, the conflict of the merge `bb0cdc334`, the gates |
| `16_toolPlatform/dossier-piattaforma-tool.md` | 2026-09-11 | A standalone review by the platform's session, written at `8e7259ecc` for the developer and for the next plugin author: decisions, refusals with reasons, the ABI, traps, risks |
| `16_toolPlatform/handoff-pac-D.md` | 2026-09-10 → 10-05 | The hand-off to the PAC workstream: §1–§7 the P1 pilot (superseded on 2026-09-24), §0 the live contract of the PAC planner, maintained by D |
| `13_pacAllocator/implementation/plan-phase00Step1Round1-ToolPlatformCapacity.prompt.md` | 2026-09-16 | The capacity round: per-operation budgets, the engine window, per-job memory (`4a38b9061`) |

## Key Takeaways

- **The platform never merged on its own.** It went into the PAC branch (`570beb386`) and reached `dev_release2`
  inside the PAC merge `3913fe217` on 2026-09-19. The dossier checked it (`git rev-list --left-right --count` →
  `82 0`) and warned that the code under review «non è quello che ho congelato io»: after the freeze the plugin ABI
  went from `ToolPlugin[InputT, OutputT]`, one Tool per class, to a package of one to sixteen `ToolService`s with
  `compute(tool_code, parameters, context)`, and `resources.py` arrived (891 insertions, 271 deletions on 15 files).
- **The developer's decisions** (plan §1) are the boundary of every page created here: three authenticated
  endpoints; diagnostics for every active user; Pydantic as the only schema source; a process per item even for
  identical inputs; plugin children only inside the job's cleanup domain; compiled custom UI with no generic
  fallback; documentation through `DocsLink` in the current language; metrics apart from the financial result,
  `null` when not observed — [[decisions/tool-calculation-without-authority]],
  [[decisions/tool-item-runs-in-owned-process]], [[decisions/tool-contract-from-pydantic-compiled-renderer]].
- **A designer and an implementer.** C wrote the capacity report (30/44/45/5/59/65 s, 1 GiB per job, cgroup v2 where
  delegated) at the coordinator's request; D implemented it «quasi alla lettera» on the developer's decision of
  2026-09-16, which replaced a fixed scenario cap with a growth curve and an anti-abuse envelope. The dossier then
  reviewed, as a reader, an envelope its author had designed but not written.
- **The first pilot was thrown away.** The hand-off described P1 `analyze`: two services (PAC and Rebalancer) on
  one plugin, 5 s budgets. P1 was removed on 2026-09-21 (`b82e59ffa`) on the developer's instruction «togli p1 e poi
  lavora su v2»; since 2026-09-24 every historical section carries «⚠️ Superato → §0.x», and §0 states the planner's
  live contract: «Se il codice cambia, prevale il codice».
- **The dossier's risks, checked today** (`8abce8e87`): the user page no longer publishes the old budgets (§5.5,
  fixed); the memory mode is still invisible in the UI (§5.1) and the client still waits the platform's timeout
  rather than the operation's (§5.4); `claim_engine_window()` still fails at once on the default operation budgets
  (§5.3) — recorded in [[features/F-106]].
- **Detours worth keeping** (plan §4): a `pipenv run` without the standard virtualenv name created an empty worktree
  environment and stopped on `argcomplete` — the trap the project instructions now warn about (pass the
  standard virtualenv name); and `info api` read the lazy `_IncludedRouter` markers and listed 9 routes instead of 121,
  so the utility now enumerates `app.openapi()`.
- **The generated files are never committed** (manifest; hand-off §0: «I cinque file generati sono ignorati da
  git»): the build-only manifest `tool-contracts.openapi.json`, `generated-tools.ts` and
  `tool-contract-map.generated.ts` are listed in `frontend/src/lib/api/.gitignore`, so they are regenerated after
  every baseline jump.

## Still open

- The folder stays in `Phase_0/` until `13_pacAllocator` is archived, because D maintains the planner's live
  contract in the hand-off's §0 and links to it from the PAC folder more than twenty times (plan header, 2026-10-09).
- The user pages, English only at the time, exist today in four languages.

## Wiki Pages Updated

Created: [[features/F-106]]; [[decisions/tool-calculation-without-authority]],
[[decisions/tool-item-runs-in-owned-process]], [[decisions/tool-contract-from-pydantic-compiled-renderer]].

Updated: [[features/registry]], [[domains/infrastructure]], [[features/F-059]], [[features/F-105]],
[[decisions/provider-registry-decision]], [[decisions/plugin-folders-and-split-i18n]],
[[concepts/backend-only-calculations]].

## Source files

| Role | Path |
|------|------|
| Platform plan | `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/plan-phase00ToolPlatform.prompt.md` |
| Review dossier | `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/dossier-piattaforma-tool.md` |
| Integration manifest | `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/manifest-integrazione-C.md` |
| Hand-off to D (§0 live contract) | `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/handoff-pac-D.md` |
| Capacity round | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step1Round1-ToolPlatformCapacity.prompt.md` |
| Executor | `backend/app/services/tools/executor.py` |
| Developer doc | `mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md` |
