---
title: "Each plugin a folder with its own translations; the i18n catalogues split by subsystem (U-1 to U-5 delivered; plan 45 closed)"
category: decision
status: accepted
date: 2026-10-12
updated: 2026-10-12
tags: [backend, frontend, architecture, plugins, providers, i18n, translations, build, docker, workstream-u, release-1.2]
related:
  - decisions/provider-registry-decision
  - decisions/signal-backend-plugin-architecture
  - decisions/i18n-key-rationalization
  - decisions/financial-math-one-home
  - decisions/utils-leaf-functions-only
  - features/F-008
---

# Decision: plugins as folders, translations split by subsystem

> **Update (step D of the historian, 2026-10-12, at `145502a39`): U-1 is in the code.** `2eed3d26c` («one folder per
> plugin», merged in train 61, `bd8ee8e4d`) moved the 84 first-party plugins with `git mv` (82 renames at 100 %, 2 at
> 99 %) to `<family>/<name>/plugin.py`, each beside an `__init__.py` that is only its docstring — «the code is in
> ``plugin.py``, which the registry loads; this package re-exports nothing». Discovery loads `plugin.py` as
> `<namespace>.<name>.plugin` (`PLUGIN_MODULE_NAME` in `provider_registry.py`); the family helpers (`_brim_io.py`,
> `_brim_output.py`, `_scalable.py`, `signal_plugins/base.py`) stay at the family root, and
> `test_plugin_layout_gate.py` guards the layout, the imports and the strings. **The translations are still planned**:
> U-2 (a catalogue built from sources) and U-3 (one catalogue per subsystem and plugin) are later steps of plan 45, and
> `frontend/src/lib/i18n/` still holds one catalogue per language.

*Update 2026-10-17 (CP-10b):* the signal contract left the family root for `services/signals/base.py`, the signals
runtime package. A family root now keeps only `__init__.py` and its `_*.py` helpers, and the layout gate no longer
allows a `base.py` there.

> **Update (train 71, 2026-10-12, at `c57acf510`): U-2 is in the code — the catalogue is built from its sources.**
> `1b31f9057` («feat(i18n): build the catalogue from its sources»):
>
> - **Generated, never edited.** The catalogue the app loads, `frontend/src/lib/i18n/<lang>.json`, is generated and
>   ignored by git, with its stamp `.generated`. Its sources are `frontend/src/lib/i18n/base/<lang>.json` (the four
>   catalogues of before, moved by a pure rename in the same commit so that other workstreams' edits followed it at
>   merge), a folder per subsystem whose `prefixes.txt` lists the key prefixes it owns, and an `i18n/` folder beside
>   a plugin's `plugin.py`. A key belongs to the plugin that defines it, otherwise to the subsystem with the longest
>   declared prefix, otherwise to `base`; a key defined twice is an error. Today only `base/` exists: the subsystem
>   and plugin folders are U-3's.
> - **The builder**, `scripts/i18n_catalog.py` (stdlib only, so the npm hooks can run the system `python3`), fills a
>   missing language from English with a warning (D-4). `check` is strict, and `check --against <rev>` proves the
>   merged catalogue equal to the one at a revision: the generated files matched the old ones byte for byte.
>   `dev.py i18n where <key>` names the source that holds, or would hold, a key.
> - **Read-only and stamped.** The generated files are written read-only (0444), and `.generated` keeps their
>   sha256. A build that finds a generated file matching neither what it writes nor what the last build wrote stops:
>   «generated file(s) edited by hand; move the change to its source (`dev.py i18n where <key>`), then build again»
>   (`--force` overrides it).
> - **Who builds it.** The npm pre-hooks (`predev`, `prebuild`, `precheck`…) and Vitest's `globalSetup`, through
>   `frontend/scripts/i18n-catalog-build.mjs`; `dev.py` calls the library itself (`front build`, `front check`, knip,
>   `i18n build`). A missing generated file makes the frontend build stale, because the E2E fixtures read it.
> - **The gate**: `utils gate-i18n-catalog` (`test_i18n_catalog_gate.py`, pure) proves every rule both ways on
>   synthetic trees, then checks the repository's own sources and ignore rule.
> - **Found on the way** (plan 45, §10): the new staleness check met a `CatalogError` in a test project without i18n
>   sources, and the staleness function's `except Exception` turned it into «no build needed». Now
>   `generated_catalogs()` returns nothing where there is no `base/`. The three reds came from the full backend run,
>   not from the targeted gates, which ran on the real tree.
> - **Still open**: U-3, the split itself; and U-B6 (low, after 1.2) — a hand edit of a source reaches `npm run dev`
>   only after `dev.py i18n build` or `npm run i18n:build`; the cure is a Vite plugin that watches the sources.
>   On the merge that carried U into the target, Git stalled once on a lock —
>   [[problems/git-merge-stash-failed-on-locked-index]].
> - *Train 72*: I's batch 48, written against the old catalogue paths, reached `base/` at the merge — the pure rename
>   did its job ([[sources/phase00-ui-polish-2026-10]]).

> **Update (train 74, 2026-10-12, at `bcd502912`): U-3 is in the code — the catalogue is split.** `f2a394a0f`
> («refactor(i18n): catalogue per subsystem and plugin»):
>
> - **Three kinds of source, as decided.** `base/` keeps 288 generic keys; 17 subsystem folders, each with its
>   `prefixes.txt` (aiExport, app, assets, auth, brokers, charts, dashboard, dataQuality, files, fx, importWizard,
>   onboarding, pacAllocator, risk, settings, tools, transactions), hold 3 844; the `i18n/` folders of 71 plugins
>   hold 219. The merged catalogue is identical in the four languages, keys and values (`check --strict --against`).
> - **Two choices, the coordinator's (D-U3-1, D-U3-2, 2026-10-12)**: the 22 `risk.warnings.*` stay in the `risk`
>   subsystem, the single vocabulary of the warnings; the 9 `risk.analytics.*` that the interface uses by name stay in
>   the plugins' fragments, as planned.
> - **A second gate**, `utils gate-plugin-i18n-ownership` (`test_plugin_i18n_ownership_gate.py`), reads the real
>   registries and proves four rules: every key of a fragment lies in its plugin's space (R1); every key a plugin
>   declares in its exclusive space lives in its fragment (R2); no fragment holds another plugin's key (R3); every
>   catalogue key under an exclusive space lives in that plugin's fragment (R4).
> - **`dev.py i18n where` and `add`** pick the source that owns a key: with the split, `base/<lang>.json` is the
>   generic vocabulary, no longer «the» catalogue.
> - **Still to come**: U-4, the documentation (after T's CP3, which writes M-18's rule in the same page), and U-5,
>   the final gates and the handoff.

> **Update (train 78, 2026-10-13, at `1c710c7a8`): U-4 is in — the documentation.** `c120086d2` rewrote the developer
> pages and the plugin skills around the plugin folders and the translation sources; `bb3772324` gave
> `developer/frontend/i18n.md` the catalogue's sources, `where`, `add` and the two gates. Backlog: U-B7 — without
> `--into`, `dev.py i18n add` puts a new plugin key in the subsystem that declares its prefix, silently, and only the
> ownership gate notices; the guides say to pass `--into`. U-B5's devWiki part was done in step D (below). U-5, the
> final gates and the handoff, remains.
>
> *Train 79*: the first keys added after U-3 — eight, with `dev.py i18n add` for T-EN — went by their prefix to the
> `charts` and `assets` subsystems (`f31bd6cfd`).

> **Update (train 80, 2026-10-13, at `cea8a478d`): U-5 is in, and plan 45 is closed** (`6a3b87d1c`). Its four
> findings (§10):
>
> - a staleness probe whose `except Exception` turned an error into «no build needed» — «Found on the way», above;
> - `all-backend` timing out at startup after a production build, while the server rebuilt in debug under load —
>   [[problems/shared-server-rebuilt-the-frontend-past-its-startup-timeout]];
> - a bash script edited while it ran — [[problems/editing-a-running-bash-script-corrupts-its-run]];
> - moving a tracked file when a generated file takes its path: first `git rm --cached` of the old path, then the pure
>   rename — the order U-2's checkpoint used for the four catalogues.
>
> Backlog: U-B5 is closed (its devWiki part was step D); U-B2 — the subsystems' sources beside their code — waits for
> after 1.2.

> **Planned, not in the code.** Decided on 2026-10-12; at `e7d698c4d` (train 56) nothing of it is implemented and
> workstream U's plan (45) is not in the target yet. The decisions are quoted from the coordinator's diary, which is
> not in the repository, as the coordinator relayed them.

## Context

The request comes from the developer's server checklist, item 28: every plugin a folder with its own translations,
merged at build time like a `generate.ts`, because a plugin is installed with a new Docker image — «non è un sistema
a hot-plugin, solo una modularizzazione estrema» ("it is not a hot-plug system, only an extreme modularization").

Until U-1, every plugin family was a package of flat modules under `backend/app/services/` (`asset_source_providers/`,
`fx_providers/`, `brim_providers/`, `signal_plugins/`, `risk_plugins/`, `tool_plugins/`), registered by auto-discovery
([[decisions/provider-registry-decision]], [[decisions/signal-backend-plugin-architecture]]; the Tool family is
[[features/F-106]]). Until U-2 the frontend had one
catalogue per language, `frontend/src/lib/i18n/{en,it,fr,es}.json` (5 653 lines in English).

## Options Considered (D-1, the plugin layout)

U's first analysis put two layouts on the table:

1. **A** — the code in `<plugin>/__init__.py`. No import to rewrite, because the module's path does not change; for U
   the code would *live* in the package, so nothing would be re-exported.
2. **B** — the code in `<plugin>/<plugin>.py`: about 85 changes to imports and `patch()` targets in 32 files.

The developer answered «proposta A con la specifica che dentro __init__.py ci sia qualcosa che fa chiamare il file
giusto nella fase di registrazione…» ("proposal A, with the proviso that something inside `__init__.py` makes the
registration call the right file…"), doubting A as it stood: «Non sono sicuro sia filosoficamente corretto mettere
dentro __init__.py il codice dei plugin, o sbaglio?» ("I am not sure it is philosophically right to put the plugins'
code in `__init__.py` — am I wrong?"). His idea, then, was an `__init__.py` that leads to the right file, not the code
inside `__init__.py`.

The coordinator explained the trap: if `__init__.py` imports the contents of the real file, a test's `patch()` on the
package path changes the package's copy of a name, which the code never reads, and the test passes without testing
anything — the same mute patch for which T-1 rejected shims at the old paths ([[decisions/financial-math-one-home]]).
The developer then left the choice to the coordinator: «dimmi tu, onestamente se è meglio la mia soluzione o quella
che proponeva U nell'ottica che nel tempo questi plugin potrebbero crescere o essere importati "dinamicamente"
aggiungendo cartelle di linking al docker compose» ("tell me honestly whether mine or U's is better, given that these
plugins may grow over time or be imported "dynamically" by linking folders in the docker compose").

## Decision

- **D-1, the layout** (the coordinator, on the developer's delegation): the clean version of the developer's idea.
  Every plugin is a folder whose `__init__.py` holds only a docstring and re-exports nothing; the code is in
  `<plugin>/plugin.py`, a fixed name, loaded by convention. Measured against the developer's criterion:
  - **growth**: the helpers sit beside `plugin.py`, and the entry file never moves again;
  - **docker-compose mounts**: the rule "the folder contains `plugin.py`" does not depend on the folder's name;
  - hence preferred to B, whose entry file is named after its folder.

  The cost: U then counted 112 changes in 32 files, among them 27 imports of the module through its package.
- **Why folders**: item 28 of the developer's checklist (see Context) — every plugin a folder with its own
  translations. Growth and mounts are the criterion the layout was chosen by, not the reason for the folders.
  **The limit**: a plugin mounted at runtime has no translations in the frontend, because they are merged at build.
- **The scope of the i18n split** (the developer): «Farei sin da subito una differenziazione spinta, oltre che nei
  plugin, anche nella traduzione "base" io creerei vari file, uno per ogni sotto sistema importante, lasciando il base
  attuale solo le cose common o comunque le chiavi generaliste/generiche, mentre creerei una cartella per ogni sotto
  sistema così che sia anche più facile raggruppare i le key con i testi che spiegano gli errrori nel file del sotto
  sistema. L'obiettivo è splittare il più possibile ora che ci sono pochi agenti al lavoro e quindi è facile fare le
  modifiche e i test» ("split hard from the start: one file per important subsystem, the base keeping only the
  common, generic keys, and a folder per subsystem, so that keys and the texts explaining its errors sit together …
  split as much as possible now, while few agents are at work and changes and tests are easy").
  - **D-A**: «La mappa così com'è» — the proposed map as it is: **17 central subsystems plus a `base`**.
  - **D-B**: «le traduzioni di sistemi core in frontend è il punto corretto, mentre per i plugin e il resto le metterei
    nelle cartelle dei plugin come detto» — core-system translations stay in the frontend; each plugin's translations
    live in its folder.
- **D-4, the merged file**: generated and ignored by git. «Al build si ripiega sull'inglese con un avviso; l'audit del
  repo resta severo e fallisce se un plugin nostro non ha tutte e 4 le lingue» ("at build time, fall back to English
  with a warning; the repository audit stays strict and fails if one of our plugins lacks any of the 4 languages").
- **D-C**: «Sì, procedi: nessuna rinomina di chiavi, tag verso il 19–20/10» — go ahead, no key renamed; the release
  tag around 19–20 October.

## Consequences

- No i18n key changes name (D-C): the rules of [[decisions/i18n-key-rationalization]] carry over unchanged.
- A plugin mounted at runtime has no translations in the frontend until the image is rebuilt: an accepted limit,
  consistent with "not a hot-plug system".
- When U lands, about 84 citations of plugin paths in 47 wiki pages will need realigning, as after T-1 — assigned to
  the historian when the lot enters the target. *Done in step D (2026-10-12, at `145502a39`): 112 citations in 54
  pages moved to `<name>/plugin.py`; 8 left as written, because they are history (five in the log, a quoted old
  import, a past-tense account, a dated residual).*
- U-2 moved the four catalogues to `base/`: the wiki's citations of `frontend/src/lib/i18n/<lang>.json` were realigned
  at the train-71 ingest (28 in 13 pages, plus 5 written as `{en,it,fr,es}`). Imports such as
  `$lib/i18n/en.json` stay: they name the generated file, which the tests do import. *Since U-3* `base/` holds only
  the generic keys: a page that cites it for a subsystem's keys names where they were; `dev.py i18n where <key>` names
  where they are.

## Links

- [[decisions/provider-registry-decision]], [[decisions/signal-backend-plugin-architecture]] — the plugin families and
  their registration today
- [[decisions/financial-math-one-home]] — the mute-patch lesson behind the empty `__init__.py`
- [[decisions/utils-leaf-functions-only]] — the same day's other layering decision
- [[decisions/i18n-key-rationalization]] — the key rules that D-C keeps

## Source files

| Role | Path |
|------|------|
| Asset providers (one folder per plugin since U-1) | `backend/app/services/asset_source_providers/` |
| FX providers today | `backend/app/services/fx_providers/` |
| BRIM providers today | `backend/app/services/brim_providers/` |
| Signal plugins today | `backend/app/services/signal_plugins/` |
| Risk plugins today | `backend/app/services/risk_plugins/` |
| Tool plugins today | `backend/app/services/tool_plugins/` |
| Discovery (`PLUGIN_MODULE_NAME`) | `backend/app/services/provider_registry.py` |
| Layout gate (U-1) | `backend/test_scripts/test_utilities/test_plugin_layout_gate.py` |
| Plan 45 of U | `LibreFolio_developer_journal/Release_2/Phase_0/45_pluginModules/plan-phase00PluginModules.prompt.md` |
| The generic vocabulary (`base`, U-2; 288 keys since U-3) | `frontend/src/lib/i18n/base/en.json` |
| A subsystem's declared prefixes (U-3) | `frontend/src/lib/i18n/risk/prefixes.txt` |
| A plugin's fragment (U-3) | `backend/app/services/risk_plugins/asset_risk_return/i18n/en.json` |
| The ownership gate `utils gate-plugin-i18n-ownership` | `backend/test_scripts/test_utilities/test_plugin_i18n_ownership_gate.py` |
| The builder (`build`, `check`, `where`) | `scripts/i18n_catalog.py` |
| The npm and Vitest hook | `frontend/scripts/i18n-catalog-build.mjs` |
| The generated files, ignored | `frontend/.gitignore` |
| The gate `utils gate-i18n-catalog` | `backend/test_scripts/test_utilities/test_i18n_catalog_gate.py` |
| Backlog U-B6 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| The i18n loader | `frontend/src/lib/i18n/index.ts` |
