# Handoff C → D — primo plugin PAC reale

> ⚠️ **Contratto superato — 2026-09-24 (workstream D, round 5).** I §1–§7 qui sotto
> descrivono il pilot P1 `pac_allocator` `1.0.0` / `operation="analyze"`, **rimosso il
> 2026-09-21** in `b82e59ffa` per decisione del developer («togli p1 e poi lavora su v2»).
> Il contratto vivo è `1.0.0` / `operation="plan"` ed è descritto nella **§0**, misurata sul
> codice. Il testo storico resta com'era, perché documenta come C e D si erano accordati; non
> va più usato come istruzione. Correzione chiesta dall'analisi statica del round 5
> (`09_feedbackJobs/09_reperti_analisi_statica_20260922.md` §9.5). Il developer ha confermato
> che era il documento a essere rimasto indietro, non il codice.
>
> **Stesso numero, contratto diverso.** Il planner è nato come `2.0.0` e il 2026-10-02 (round 14
> di D) il developer lo ha riportato a `1.0.0`, perché nessuna delle due versioni è mai stata
> rilasciata. Il `1.0.0` di oggi è il planner `plan`; il `1.0.0` dei §1–§7 è il pilot `analyze`,
> che non esiste più nel codice.

**Data:** 2026-09-10
**Stato C:** base completa e validata · nessun plugin/renderer PAC incluso
**Dipendenza D:** modelli/core P1 reali e UI P1 approvata

Questo documento definisce il raccordo esatto. D non copia il worker, il registry,
il client o gli schemi Tool; aggiunge il proprio dominio nei punti di estensione C.

## 0. Contratto effettivo al `111b0bbd0` (misurato il 2026-10-02)

Ogni riga cita il file e la riga da cui è stata letta. Se il codice cambia, prevale il
codice: questa sezione è una fotografia, non una specifica. La fotografia precedente era al
`f1047f766` (2026-09-24), con la versione `2.0.0`.

### 0.1 Backend

| Voce | Valore | Fonte |
|---|---|---|
| Plugin | `PacAllocatorTool(ToolPlugin)` con **una** `ToolService` in `services` | `backend/app/services/tool_plugins/pac_allocator.py:130-157` |
| Versioni | `contract_version = "1.0.0"`, `implementation_version = "1.0.0"` | `pac_allocator.py:132-133` |
| Codice tool | `tool_code="pac_allocator"`, `category="allocation"`, `icon_key="calculator"` | `pac_allocator.py:137,142-143` |
| Descrizione | chiavi `tools.pacAllocator.name` / `tools.pacAllocator.description`; fallback EN a `:138-139` | `pac_allocator.py:138-141` |
| UI | `ToolUIDescriptor(kind="custom", component_key="pac-allocator", version="1.0.0")` | `pac_allocator.py:144-148` |
| Documentazione | `path="user/tools/pac-allocator/"`, `version="1.0.0"` | `pac_allocator.py:149-152` |
| Operazione | una sola: `plan` — `pure`, `deterministic`, `deduplication="none"` | `pac_allocator.py:81-97` |
| Limiti di byte | parametri `262_144` (la piattaforma applica il minimo col proprio tetto di `131_072`), risultato `512 * 1024` | `pac_allocator.py:65,87-88` |
| Timeout (ms) | queue `5_000` · engine `30_000` · job `45_000` · soft `44_000` · cleanup `5_000` · request `59_000` · client `65_000` | `pac_allocator.py:89-95` |
| Riserva post-engine | `2_000` ms, passata a `context.claim_engine_window(...)` | `pac_allocator.py:79,186` |
| Tipi wire | `input_type=PacPlannerRequest`, `output_type=PacPlannerResult` | `pac_allocator.py:154-155` |
| Firma `compute` | `compute(self, tool_code: str, parameters: BaseModel, context: ToolExecutionContext) -> PacPlannerResult`; il dispatch è su `tool_code` e `operation`, mai sulla forma dei parametri; se non corrispondono, solleva `ToolExecutionError("invalid_parameters")` | `pac_allocator.py:159-199`; base `backend/app/services/tools/base.py:103` |
| Motore | `plan_pac_allocation(request, *, checkpoint=None, solver_time_budget_seconds=None) -> PacPlannerResult`. Non solleva su un esito di pianificazione | `backend/app/services/pac_allocator/planner.py:124-128` |
| Package | `backend/app/services/pac_allocator/__init__.py` non riesporta niente (`__all__ = []`, `:20`); importarlo non deve caricare `pyscipopt` (`:16`) | `__init__.py:16,20` |
| Richiesta | `PacPlannerRequest` (`operation: Literal["plan"]` obbligatorio, senza default) | `backend/app/schemas/pac_allocator.py:617,648` |
| Risultato | unione discriminata su `result_state`, sette stati: `needs_input`, `invalid`, `unsupported`, `ready_no_op`, `ready_incumbent`, `ready_infeasible`, `ready_no_incumbent` | schema `:2346-2357,2410-2434,2506-2517` |
| Adapter per i test | `PAC_PLAN_INPUT_ADAPTER`, `PAC_PLAN_OUTPUT_ADAPTER` | schema `:2533-2534` |

Il Rebalancer **non** ha un servizio registrato: i suoi tipi esistono nello schema
(`RebalancerPlannerRequest`/`Result`), ma il plugin non li espone (`pac_allocator.py:10-14`).

### 0.2 Codegen

- `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync`
  (oppure `--tools-only`, `dev.py:2439-2447`). Estrae lo schema in-process e non apre porte.
- I cinque file generati sono **ignorati da git** (`frontend/src/lib/api/.gitignore:1-3`,
  `frontend/.gitignore:12-13`). Non arrivano col merge, quindi vanno rigenerati dopo ogni salto
  di baseline, prima di `front check`.
- La mappa espone `toolContractMap.pac_allocator["1.0.0"]` con `componentKey: "pac-allocator"`,
  `uiVersion: "1.0.0"` e `operations: ["plan"]`. Il 2026-10-02, con il client rigenerato al
  `111b0bbd0`, il fingerprint misurato è `schemaFingerprint: "bd84ef14…"` e la generazione
  `bb77549b…`.
- **`uiContractVersion` non esiste più**: il campo è `uiVersion`, una stringa uguale alla
  `version` del `ToolUIDescriptor`.

### 0.3 Renderer

- Props: `ToolHostPropsV1<'pac_allocator', '1.0.0'>` = `{descriptor, accountGeneration}`
  (`frontend/src/lib/features/tools/registry.ts:20-23`).
- Registrazione, nell'array compilato (`registry.ts:240-246`):

  ```ts
  defineToolRenderer('pac_allocator', '1.0.0', {componentKey: 'pac-allocator', uiVersion: '1.0.0', load: () => import('./pac-allocator/planner/PacPlannerTool.svelte')})
  ```

  Firma e opzioni in `registry.ts:25-29,126`. `componentKey` e `uiVersion` devono coincidere
  con la mappa generata (`registry.ts:162`).
- `resolveToolRenderer` restituisce `ready` (`registry.ts:235,249-251`), e il test lo fissa
  (`registry.test.ts:135`). Se il renderer sparisce, il tool torna allo stato
  `renderer_missing` (`registry.ts:234`) che il developer aveva visto nel round 5.
- Esecuzione: `runTool('pac_allocator', '1.0.0', {descriptor, correlationId, parameters, signal})`
  (`frontend/src/lib/features/tools/client.ts:36-41,300`). `parameters` è
  `ToolInput<'pac_allocator','1.0.0'>` e il risultato è
  `ToolItemResult<'pac_allocator','1.0.0'>` (`client.ts:50-52`).
- Restano valide le regole di §4 su `accountGeneration`, revisione della bozza, sequenza
  della richiesta, metriche fuori dal risultato finanziario e ruoli C/D.

### 0.4 Selector reali

```text
schemas  pac-planner                                   scripts/test_runner/_backend_schemas.py:156-163
schemas  tools                                         _backend_schemas.py:165-172
services pac-planner-{core,evaluator,oracle,policies,  _backend_services.py:906-977
          solver,proof,wire-numbers,report,service}
services portfolio-allocation-source                   _backend_services.py:1040-1047
services tools-registry | tools-lifecycle              _backend_services.py:1130-1145
utils    tools-wire                                    _backend_utils.py:306-313
api      tools                                         _backend_api.py:687
api      pac-planner-tool                              _backend_api.py:688
front-utility core-unit       (client, registry, allocationSource, decimal, format)   _frontend_utility.py:114-118,509-517
front-utility component-unit  (ToolsHub, ToolHost, StateNotice, ResultCell)          _frontend_utility.py:254-257,518-526
front-utility document-title  (E2E: /tools e /tools/<primo codice del catalogo>)      _frontend_utility.py:555
test check-orphans                                     scripts/test_runner/_cli.py:466,510
```

`schemas pac-analyze`, `services pac-analyze`, `api pac-tool` e `pac-planner-capacity`
**non esistono**. Il test API end-to-end del planner (catalogo → compute → risultato
validato) è `api pac-planner-tool`.

### 0.5 Lane (dal round 5)

La lane `6153` della §6 è superata. Oggi valgono:

- suite `--test-port 6151 --data-dir /tmp/librefolio-r2-d`, solo `dev.py test`;
- copia di prod `6161` + `/tmp/librefolio-r2-d-prodcopy`, per server e review.

### 0.6 Definition of done del renderer del planner (sostituisce §7)

- Il catalogo contiene un solo `pac_allocator/1.0.0` sano. La mappa generata e il catalogo
  hanno lo stesso fingerprint e lo stesso `uiVersion`.
- `resolveToolRenderer` restituisce `ready` e la card non mostra più `renderer_missing`.
- La UI manuale funziona senza Asset/Broker nel DB e non calcola valori economici nel browser.
  Le copie passano da `POST /portfolio/allocation-source`.
- Una risposta obsoleta, o di un account precedente, non sostituisce la bozza.
- I sette stati del risultato hanno una vista. Ogni importo patrimoniale passa dai formatter
  privacy (`utils/currency/currencyFormat.ts`).
- Il runbook del developer è completato sulla copia di prod. Piano:
  `13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md`.

## 1. Simboli backend D richiesti

> ⚠️ **Superato → §0.1.** P1 `analyze`, rimosso il 2026-09-21 (`b82e59ffa`).

File di dominio D:

```text
backend/app/schemas/pac_allocator.py
backend/app/services/pac_allocator/__init__.py
backend/app/services/pac_allocator/{models,normalize,evaluator,report,numeric}.py
```

Simboli pubblici:

```python
PacAnalyzeInput
PacAnalyzeOutput
PAC_ANALYZE_INPUT_ADAPTER
PAC_ANALYZE_OUTPUT_ADAPTER

analyze_initial_state(
    request: PacAnalyzeInput,
    *,
    checkpoint: Callable[[], None] | None = None,
) -> PacAnalyzeOutput
```

Vincoli:

- `operation: Literal["analyze"]` obbligatorio, senza default.
- `PacAnalyzeOutput` e' l'unione discriminata P1-r3 per availability.
- Tutti i modelli annidati extra-forbid; niente TypedDict/dataclass/open dict.
- Nessun computed field o alias validation/serialization divergente nell'output wire.
- Interi nel dominio JSON safe; numeri finanziari esatti come stringhe decimali.
- Il core non importa Tool, clock, DB, provider o principal. Chiama soltanto il
  callback no-arg `checkpoint` a confini di lavoro limitati.

Gli adapter pubblici restano utili ai test D. Il registry C ricostruisce i propri
TypeAdapter dai tipi reali e ne deriva fingerprint e schema.

## 2. Thin plugin D

> ⚠️ **Superato → §0.1.** Oggi il plugin dichiara `services = (ToolService(...),)`, versione `1.0.0` (il planner, non il pilot di questa sezione), operazione `plan`, e `compute(tool_code, parameters, context)`.

File:

```text
backend/app/services/tool_plugins/pac_allocator.py
```

Contratto esatto:

```python
from backend.app.schemas.pac_allocator import PacAnalyzeInput, PacAnalyzeOutput
from backend.app.schemas.tools import (
    ToolDocumentation,
    ToolOperationPolicy,
    ToolUIDescriptor,
)
from backend.app.services.pac_allocator import analyze_initial_state
from backend.app.services.provider_registry import register_plugin
from backend.app.services.tools.base import ToolExecutionContext, ToolPlugin
from backend.app.services.tools.registry import ToolPluginRegistry


@register_plugin(ToolPluginRegistry)
class PacAllocatorTool(ToolPlugin[PacAnalyzeInput, PacAnalyzeOutput]):
    tool_code = "pac_allocator"
    contract_version = "1.0.0"
    implementation_version = "1.0.0"

    name = "PAC allocator"
    description = "Analyze the exact initial allocation state."
    name_i18n_key = "tools.pacAllocator.name"
    description_i18n_key = "tools.pacAllocator.description"
    category = "allocation"
    icon_key = "calculator"

    ui = ToolUIDescriptor(
        kind="custom",
        component_key="pac-allocator",
        version="1.0.0",
    )
    documentation = ToolDocumentation(
        path="user/tools/pac-allocator/",
        version="1.0.0",
    )
    operations = (
        ToolOperationPolicy(
            operation="analyze",
            pure=True,
            deterministic=True,
            deduplication="none",
            max_parameter_bytes=131_072,
            max_result_bytes=262_144,
            queue_timeout_ms=5_000,
            job_timeout_ms=5_000,
            soft_timeout_ms=4_000,
        ),
    )

    input_type = PacAnalyzeInput
    output_type = PacAnalyzeOutput

    def compute(
        self,
        parameters: PacAnalyzeInput,
        context: ToolExecutionContext,
    ) -> PacAnalyzeOutput:
        return analyze_initial_state(
            parameters,
            checkpoint=context.checkpoint,
        )
```

Non aggiungere solve finche' il relativo contratto non e' congelato/versionato.
Niente costruttore parametrico, self-test/import compute, DB copy o scenario personale.

## 3. Codegen e descriptor atteso

> ⚠️ **Superato → §0.2.** `uiContractVersion` è diventato `uiVersion: "1.0.0"`; la mappa è `toolContractMap.pac_allocator["1.0.0"]` con `operations: ["plan"]`.

Dopo l'aggiunta del thin plugin:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py api sync --tools-only
```

Output generati/ignorati:

```text
frontend/src/lib/api/tool-contracts.openapi.json
frontend/src/lib/api/generated-tools.ts
frontend/src/lib/api/tool-contract-map.generated.ts
```

La mappa deve contenere:

```ts
toolContractMap.pac_allocator["1.0.0"]
```

con:

```text
toolCode             pac_allocator
contractVersion      1.0.0
schemaFingerprint    uguale al catalogo runtime
componentKey         pac-allocator
uiContractVersion    1
operations           ["analyze"]
input/output          codec reali P1
```

`implementation_version` non e' statico nella mappa frontend: viene letto e
pinnato dal descriptor runtime. Un cambio schema/operazioni richiede aggiornamento
contratto/fingerprint e nuova generazione.

## 4. Renderer D

> ⚠️ **Superato → §0.3** per versioni e registrazione. Le regole sui controlli (`accountGeneration`, bozza, sequenza, metriche) e sui ruoli C/D restano valide.

File raccomandato:

```text
frontend/src/lib/features/tools/pac-allocator/PacAllocatorTool.svelte
frontend/src/lib/features/tools/pac-allocator/PacAllocatorTool.test.ts
```

Props:

```ts
import type {ToolHostPropsV1} from '$lib/features/tools/registry';

let {
    descriptor,
    accountGeneration,
}: ToolHostPropsV1<'pac_allocator', '1.0.0'> = $props();
```

Registrazione compilata in:

```text
frontend/src/lib/features/tools/registry.ts
```

```ts
defineToolRenderer('pac_allocator', '1.0.0', {
    componentKey: 'pac-allocator',
    uiContractVersion: 1,
    load: () => import('./pac-allocator/PacAllocatorTool.svelte'),
})
```

Nessun path/URL/modulo server. Il renderer invoca:

```ts
runTool('pac_allocator', '1.0.0', {
    descriptor,
    correlationId,
    parameters,
    signal,
})
```

`parameters` e `result` derivano da `ToolInput`/`ToolOutput`, non da interfacce
finanziarie scritte a mano. Prima di applicare un risultato D controlla:

- `accountGeneration`;
- revisione draft;
- sequenza richiesta;
- identita' componente/contratto.

Le metriche sono `reply.metrics` e `reply.batch.metrics`, visualizzabili con
`ToolExecutionMetrics.svelte`; non entrano nel risultato finanziario.

Il componente D possiede input, facts/issues, exact/formatted view e stale state.
C possiede host, errori trasporto/protocollo e compatibilita'. Nessun generatore
schema-driven sostituisce la UI P1.

## 5. Documentazione e i18n D

> ⚠️ **Parzialmente superato.** Pagina e chiavi `name`/`description` restano quelle indicate. Le chiavi `tools.pacAllocator.*` del P1 sono ancora nei cataloghi: il loro ritiro è pianificato a fine round 5 e nessuna chiave si cancella senza decisione.

Pagina:

```text
mkdocs_src/docs/user/tools/pac-allocator/index.en.md
```

La traduzione parte solo su richiesta esplicita. `DocsLink` costruisce il link
dalla lingua frontend; non codificare `/mkdocs/en/`.

Chiavi UI minime:

```text
tools.pacAllocator.name
tools.pacAllocator.description
```

Le altre chiavi appartengono all'ASCII P1 approvato D e vanno aggiunte con
`dev.py i18n`, mai editando contemporaneamente i quattro JSON.

## 6. Selector test

> ⚠️ **Superato → §0.4 e §0.5.** La lane `6153` e i selector `pac-analyze`/`pac-tool` non esistono più.

Lane dopo merge C→D:

```text
--test-port 6153 --data-dir /tmp/librefolio-r2-d
```

Selector gia' esistenti D/C:

```text
schemas pac-analyze
services pac-analyze
schemas tools
services tools-registry
services tools-lifecycle
utils tools-wire
api tools
front-utility core-unit client
test check-orphans
```

Integrazioni D da registrare:

```text
api pac-tool
front-utility component-unit pac-allocator
```

`api pac-tool` usa il witness sintetico P1 attraverso catalogo → compute → processo
→ evaluator → output validato; verifica fingerprint/versioni/correlation e risultato,
senza DB/provider o dati personali.

`PacAllocatorTool.test.ts` va aggiunto all'elenco `component-unit`; il describe
contiene `pac-allocator`, cosi' il selector mirato resta stabile.

Gate finali D:

```text
api sync --tools-only
front check
front format --check
front build
mkdocs build
mkdocs check-links
```

Test nuovi/riparati passano da `test-author`; docs da `docs-writer`.

## 7. Definition of done del pilot D

> ⚠️ **Superato → §0.6.**

- Catalogo contiene un solo `pac_allocator/1.0.0` sano.
- Generated map e catalogo hanno lo stesso fingerprint/UI ABI.
- Compute reale produce esattamente un risultato per item, in ordine.
- P1 invalid/needs_input resta successo piattaforma tipizzato.
- Timeout/crash/cleanup restano errori piattaforma.
- UI manuale funziona senza Asset/Broker DB e non calcola valori nel browser.
- Risposte obsolete/account precedente non sostituiscono la bozza.
- Runbook developer desktop/mobile/errori completato dopo build integrata.

C non include questo pilot: il suo stato completo e' **base pronta per D**.
