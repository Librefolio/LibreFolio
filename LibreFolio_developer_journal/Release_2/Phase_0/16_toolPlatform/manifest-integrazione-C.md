# Manifest checkpoint C — Piattaforma Tool

**Data:** 2026-09-10
**Stato:** ready per commit manuale · non integrato · non archiviato
**Piano:** [plan-phase00ToolPlatform.prompt.md](plan-phase00ToolPlatform.prompt.md)

## 1. Fotografia esatta del delta

Worktree C:

- HEAD/base: `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`
- Target runtime successivo: `916f12bddf3eb9b8e834e4b9033eb52ce4bde25a`
- Commit nel range C: nessuno
- File modificati tracciati: **14**
- File nuovi non tracciati: **41**
- Totale file del checkpoint applicativo: **55**

I due file journal di questa cartella vengono aggiunti dal checkpoint di chiusura e
portano il totale finale del commit proposto a **57 file**.

### File tracciati modificati (14)

```text
backend/app/api/v1/router.py
backend/app/main.py
backend/app/schemas/__init__.py
backend/app/services/__init__.py
backend/app/services/provider_registry.py
backend/app/utils/financial/__init__.py
dev.py
frontend/package.json
frontend/src/lib/components/layout/Sidebar.svelte
scripts/cli_base.py
scripts/list_api_endpoints.py
scripts/test_runner/_backend_schemas.py
scripts/test_runner/_backend_services.py
scripts/test_runner/_backend_utils.py
```

### File nuovi applicativi/documentali (41)

```text
.github/skills/tool-plugin/SKILL.md
backend/app/api/v1/tools.py
backend/app/schemas/tools.py
backend/app/services/tool_plugins/__init__.py
backend/app/services/tools/__init__.py
backend/app/services/tools/base.py
backend/app/services/tools/catalog.py
backend/app/services/tools/executor.py
backend/app/services/tools/process_tree.py
backend/app/services/tools/registry.py
backend/app/services/tools/schema.py
backend/app/services/tools/schema_export.py
backend/app/services/tools/wire.py
backend/app/services/tools/worker.py
backend/test_scripts/test_schemas/test_tools_schemas.py
backend/test_scripts/test_services/_tools_executor_fixtures.py
backend/test_scripts/test_services/test_tools_executor.py
backend/test_scripts/test_services/test_tools_registry.py
backend/test_scripts/test_utilities/test_tools_wire.py
frontend/scripts/generate-tools-client.mjs
frontend/scripts/tools-codec-ast.mjs
frontend/scripts/tools-fix-main-discriminators.mjs
frontend/scripts/tools-generation-io.mjs
frontend/scripts/tools-record-runtime.hbs
frontend/scripts/tools-schema-document.mjs
frontend/scripts/tools-schemas.hbs
frontend/src/lib/api/.gitignore
frontend/src/lib/features/tools/ToolAboutPanel.svelte
frontend/src/lib/features/tools/ToolDiagnosticsPanel.svelte
frontend/src/lib/features/tools/ToolHost.svelte
frontend/src/lib/features/tools/ToolsHub.svelte
frontend/src/lib/features/tools/client.ts
frontend/src/lib/features/tools/components/ToolExecutionMetrics.svelte
frontend/src/lib/features/tools/contracts.ts
frontend/src/lib/features/tools/presentation.ts
frontend/src/lib/features/tools/registry.ts
frontend/src/routes/(app)/tools/+page.svelte
frontend/src/routes/(app)/tools/[tool_code]/+page.svelte
mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md
mkdocs_src/docs/user/tools/index.en.md
scripts/export_tool_contracts.py
```

### File journal aggiunti dal checkpoint (2)

```text
LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/plan-phase00ToolPlatform.prompt.md
LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/manifest-integrazione-C.md
```

## 2. File generati/temporanei da NON includere

| Path / gruppo | Stato | Trattamento |
|---------------|-------|-------------|
| `.testLog/` | Presente e ignorato; contiene log DTO | Escludere dal commit |
| `frontend/src/lib/api/tool-contracts.openapi.json` | Assente; ignorato dalla nuova `.gitignore` locale | Generare dopo merge/VIA, non committare |
| `frontend/src/lib/api/generated-tools.ts` | Assente; ignorato | Generare, non committare |
| `frontend/src/lib/api/tool-contract-map.generated.ts` | Assente; ignorato | Generare, non committare |
| `.tools-codegen.lock`, `*.pending`, `*.previous` | Assenti | Artefatti transitori, mai committare |
| `tool-ui-i18n.json` | Artifact sessione esterno al repo | Input per writer i18n, non fonte runtime |
| `tool-test-registration.patch` | Artifact sessione esterno al repo | Solo proposta lifecycle esclusiva, non committare |
| `/tmp/libreFolio_c_*` | Log/fingerprint fuori repo | Evidenza locale, non committare |
| `__pycache__`, `.pyc`, cache tool | Ignorati | Escludere |

`frontend/src/lib/api/.gitignore` e' invece un file sorgente voluto: rende espliciti
i tre output Tool non committabili.

## 3. Evidenze disponibili

| Evidenza | Esito |
|----------|-------|
| Ruff/Black file-scoped backend C | Pass sui blocchi eseguiti |
| Ruff/Black tre initializer lazy | Pass |
| Ruff Python codegen nuovi file | Pass;42 rilievi `dev.py` dimostrati preesistenti |
| `schemas tools --workers 1` | **214 passed in0.17s**, exit0 |
| Fingerprint readset test | Identico pre/post |
| DB C test/prod | Assenti pre/post |

Non eseguiti: registry/wire/lifecycle, API, codegen, type-check, Vitest/build/E2E,
MkDocs build/check-links, PAC integrato.

## 4. Conflitti con `dev_release2/916f12bd`

Overlap Git esatto: **3 file**.

### `dev.py`

**Target runtime:** importa/configura runtime per-lane, aggiunge `--data-dir`, propaga
test mode e sposta la verifica porta dopo build.
**C:** estende `api schema/client/sync` con contratti Tool e `--tools-only`.

Risoluzione semantica:

- mantenere integralmente configurazione runtime, data-dir e porta fail-closed;
- mantenere i tre comandi API Tool e il percorso tools-only senza import app;
- non ripristinare il vecchio flusso server o il vecchio export solo legacy;
- nessun `--force` nelle future invocazioni C.

### `scripts/cli_base.py`

**Target runtime:** introduce dotenv controllato, validazione porta/data-dir,
`configure_test_runtime`, `configure_server_runtime` e lane ID.
**C:** amplia gli output generati e la freshness con sorgenti Tool dinamici.

Risoluzione semantica:

- prendere tutte le primitive runtime dal target;
- riapplicare `_BUILD_GENERATED_SOURCES` con i tre output Tool;
- conservare `_tool_contract_sources()` e relativo controllo mtime;
- non far caricare `.env` nel percorso tools-only isolato.

### `scripts/test_runner/_backend_utils.py`

**Target runtime:** registra `container-registry` e `runtime-isolation`.
**C:** registra `tools-wire`.

Risoluzione semantica:

- conservare tutte e tre le funzioni/action;
- mantenere selector distinti e `isolation="pure"`;
- non spostare registry/lifecycle nella categoria utils per evitare il setup services;
- verificare `utils all` soltanto nella lane isolata dopo merge.

## 5. Conflitti semantici successivi, non nel commit runtime

- **Pacchetto E:** `AboutTab.svelte` e i quattro JSON i18n. Applicare il pannello Tool
  sul details Plugin diagnostics definitivo, preservando SupportActions,
  SocialShareModal e currentVersion backend. Importare le102 chiavi via writer/CLI.
- **D/PAC:** i tre initializer lazy sono condivisi; evitare una seconda copia del delta.
  Integrare modelli/core/thin plugin/renderer reali, non fixture o formule duplicate.
- **Backlog 05/06:** `916f12bd` contiene versioni piu' recenti. Dopo merge aggiungere
  il link a questo piano su quelle versioni, non sovrascriverle con la base C.
- **Generated API:** target/E possono avere altri contratti. Eseguire un solo
  `api sync` integrato nella lane C, non scegliere generated output di un lato.

## 6. Messaggio commit proposto

```text
feat(tools): add atomic Tool foundation

Run each item in an owned process tree and derive client codecs from
Pydantic contracts so plugins remain reusable without ambient authority.
```

Nessun commit, staging o mutazione della storia e' stato eseguito dall'agente.
