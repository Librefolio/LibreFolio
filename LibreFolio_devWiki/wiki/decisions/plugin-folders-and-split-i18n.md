---
title: "Each plugin a folder with its own translations; the i18n catalogues split by subsystem (planned, workstream U)"
category: decision
status: accepted
date: 2026-10-12
tags: [backend, frontend, architecture, plugins, providers, i18n, translations, build, docker, workstream-u, release-1.2]
related:
  - decisions/provider-registry-decision
  - decisions/signal-backend-plugin-architecture
  - decisions/i18n-key-rationalization
  - decisions/financial-math-one-home
  - decisions/utils-leaf-functions-only
---

# Decision: plugins as folders, translations split by subsystem

> **Planned, not in the code.** Decided on 2026-10-12; at `e7d698c4d` (train 56) nothing of it is implemented and
> workstream U's plan (45) is not in the target yet. The decisions are quoted from the coordinator's diary, which is
> not in the repository, as the coordinator relayed them.

## Context

The request comes from the developer's server checklist, item 28: every plugin a folder with its own translations,
merged at build time like a `generate.ts`, because a plugin is installed with a new Docker image — «non è un sistema
a hot-plugin, solo una modularizzazione estrema» ("it is not a hot-plug system, only an extreme modularization").

Today every plugin family is a package of flat modules under `backend/app/services/` (`asset_source_providers/`,
`fx_providers/`, `brim_providers/`, `signal_plugins/`, `risk_plugins/`, `tool_plugins/`), registered by auto-discovery
([[decisions/provider-registry-decision]], [[decisions/signal-backend-plugin-architecture]]). The frontend has one
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
  the historian when the lot enters the target.

## Links

- [[decisions/provider-registry-decision]], [[decisions/signal-backend-plugin-architecture]] — the plugin families and
  their registration today
- [[decisions/financial-math-one-home]] — the mute-patch lesson behind the empty `__init__.py`
- [[decisions/utils-leaf-functions-only]] — the same day's other layering decision
- [[decisions/i18n-key-rationalization]] — the key rules that D-C keeps

## Source files

| Role | Path |
|------|------|
| Asset providers today (flat modules) | `backend/app/services/asset_source_providers/` |
| FX providers today | `backend/app/services/fx_providers/` |
| BRIM providers today | `backend/app/services/brim_providers/` |
| Signal plugins today | `backend/app/services/signal_plugins/` |
| Risk plugins today | `backend/app/services/risk_plugins/` |
| Tool plugins today | `backend/app/services/tool_plugins/` |
| The catalogue today, one per language | `frontend/src/lib/i18n/en.json` |
| The i18n loader | `frontend/src/lib/i18n/index.ts` |
