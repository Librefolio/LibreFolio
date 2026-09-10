# Manifest checkpoint C — Piattaforma Tool

**Data:** 2026-09-10
**Stato:** base C completa · merge `bb0cdc33` · checkpoint finale staged · handoff D pronto
**Piano:** [plan-phase00ToolPlatform.prompt.md](plan-phase00ToolPlatform.prompt.md)

## 1. Fotografia esatta del checkpoint `1656aff6` pre-merge

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
| `frontend/src/lib/api/tool-contracts.openapi.json` | Generato e ignorato · SHA256 `1e12276a590dbc92dfbf07ed541874b851e27379693d677a467babd9ef3e34c5` | Non committare |
| `frontend/src/lib/api/generated-tools.ts` | Generato e ignorato · SHA256 `839aabc4a6a92b1dd510d09b4308b6e65a82ce3ae9b3121397b76b2d18e6882d` | Non committare |
| `frontend/src/lib/api/tool-contract-map.generated.ts` | Generato e ignorato · SHA256 `49dc1bbf739581e3e5d1f865140e991d5f82cbb59790e16a65fbdd3d6106e60c` | Non committare |
| `.tools-codegen.lock`, `*.pending`, `*.previous` | Assenti | Artefatti transitori, mai committare |
| `tool-ui-i18n.json` | Artifact sessione esterno al repo, applicato via CLI | Storico handoff, non fonte runtime |
| `tool-test-registration.patch` | Artifact sessione esterno al repo, applicato | Storico handoff, non committare |
| `/tmp/libreFolio_c_*` | Log/fingerprint fuori repo | Evidenza locale, non committare |
| `__pycache__`, `.pyc`, cache tool | Ignorati | Escludere |

`frontend/src/lib/api/.gitignore` e' invece un file sorgente voluto: rende espliciti
i tre output Tool non committabili.

## 3. Evidenze disponibili al checkpoint pre-merge

| Evidenza | Esito |
|----------|-------|
| Ruff/Black file-scoped backend C | Pass sui blocchi eseguiti |
| Ruff/Black tre initializer lazy | Pass |
| Ruff Python codegen nuovi file | Pass;42 rilievi `dev.py` dimostrati preesistenti |
| `schemas tools --workers 1` | **214 passed in0.17s**, exit0 |
| Fingerprint readset test | Identico pre/post |
| DB C test/prod | Assenti pre/post |

Le evidenze post-merge sostitutive sono nella sezione6.

## 4. Conflitti con `dev_release2/916f12bd`

Overlap Git esatto: **3 file**.

**Esito:** merge committato dal developer in
`bb0cdc3348971d118cc12d7e5a4a5e7f6f7ccfe7`.
Unico conflitto testuale in `_backend_utils.py`, risolto additivamente.
`dev.py` e `cli_base.py` sono auto-merge verificati semanticamente.
Checkpoint post-merge finale:21 path staged, nessun `UU`, untracked o modifica
unstaged. L'agente non crea il commit finale.

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

Gate mirati confermano `runtime-isolation`133/134, `container-registry`30 e
`tools-wire`190/196 durante i giri successivi; l'ultimo stato e' riportato sotto.

## 5. Integrazioni semantiche applicate dopo il merge

- Mount `ToolAboutPanel` nel details Plugin diagnostics E, senza rimuovere
  SupportActions, SocialShareModal o currentVersion backend.
-102 chiavi Tool aggiunte con `dev.py i18n add`; audit completo2668/2668 x4.
- Nav MkDocs user/developer aggiunta; build e check-links verdi.
- Lifecycle registrato come action esclusiva; orfani tutti risolti.
- `list_api_endpoints.py` usa OpenAPI materializzato:121 endpoint, inclusi i3 Tool.
- Boundary hardening dopo due review: frame deadline-aware, PGID fail-closed,
  output round-trip/alias, nested strict types, schema frontend-compatible,
  safe integers e snapshot client immutabile.

## 6. Evidenze post-merge

| Gate | Ultimo esito |
|------|--------------|
| Ruff `dev.py lint` | pass |
| Runtime isolation |134 passed |
| Container registry |30 passed |
| Tool schema |214 passed |
| Tool wire |196 passed |
| Tool registry |82 passed |
| Tool lifecycle |63 passed |
| Tool API |5 passed |
| System API |24 passed |
| Orphan/reachability | pass |
| i18n |2668/2668 EN/IT/FR/ES |
| MkDocs build / links | pass /12 |
| OpenAPI listing |121 endpoint,3 Tool |
| API sync completo / Tool-only | pass / pass;0 plugin base |
| Svelte check |0 errori,0 warning |
| Vitest client Tool |17 passed |
| Frontend build | pass |
| Prettier check | pass |

### Ambiente ripristinato

- Un solo `npm --prefix frontend ci` dal lock:433 pacchetti, manifest/lock invariati.
- Audit npm ha riportato20 advisory del lock corrente; nessun `npm audit fix`
  o aggiornamento dipendenze eseguito.
- Cache MathJax popolata localmente dallo stesso URL configurato tramite `curl`
  con TLS di sistema verificato; file/manifest sono cache ignorata.

### Limiti residui

- Nessun plugin/renderer PAC reale integrato.
- Output generati restano ignorati e non vanno committati.
- Le pagine localizzate Tool esistono nel sito tramite fallback EN; traduzioni
  MkDocs native IT/FR/ES richiedono una richiesta esplicita separata.

> **⚠️ Detour ambiente**: un primo `pipenv run` senza custom venv ha creato il
> virtualenv vuoto del worktree e si e' fermato prima dei test. L'ambiente e'
> rimasto intatto; i run validi usano `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`.

Due review read-only boundary completate. I residui trovati sono stati corretti
su frame deadline, PGID, output aliases/shape, schema supportato, interi safe e
snapshot client. Le regressioni backend sono verdi; client/AST resta da eseguire
dopo la generazione dei codec.
Il contratto D e' in [handoff-pac-D.md](handoff-pac-D.md).

## 7. Conflitti semantici ancora aperti

- **D/PAC:** i tre initializer lazy sono condivisi; evitare una seconda copia del delta.
  Integrare modelli/core/thin plugin/renderer reali, non fixture o formule duplicate.
- **Generated API:** target/E possono avere altri contratti. Eseguire un solo
  `api sync` integrato nella lane C, non scegliere generated output di un lato.

## 8. Commit

```text
feat(tools): add atomic Tool foundation

Run each item in an owned process tree and derive client codecs from
Pydantic contracts so plugins remain reusable without ambient authority.
```

Checkpoint C iniziale: `1656aff6937f08935a902726884fdda4102f46ec`.
Merge runtime: `bb0cdc3348971d118cc12d7e5a4a5e7f6f7ccfe7`.

Checkpoint finale proposto:

```text
fix(tools): harden merged platform

Validate process, schema, wire, and client boundaries after runtime
isolation, then wire diagnostics, docs, translations, and API tests.
```

Il commit finale resta manuale; l'agente non lo crea.
