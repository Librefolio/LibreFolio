# Handoff C → D — primo plugin PAC reale

**Data:** 2026-09-10
**Stato C:** base completa e validata · nessun plugin/renderer PAC incluso
**Dipendenza D:** modelli/core P1 reali e UI P1 approvata

Questo documento definisce il raccordo esatto. D non copia il worker, il registry,
il client o gli schemi Tool; aggiunge il proprio dominio nei punti di estensione C.

## 1. Simboli backend D richiesti

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
        ui_contract_version=1,
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

- Catalogo contiene un solo `pac_allocator/1.0.0` sano.
- Generated map e catalogo hanno lo stesso fingerprint/UI ABI.
- Compute reale produce esattamente un risultato per item, in ordine.
- P1 invalid/needs_input resta successo piattaforma tipizzato.
- Timeout/crash/cleanup restano errori piattaforma.
- UI manuale funziona senza Asset/Broker DB e non calcola valori nel browser.
- Risposte obsolete/account precedente non sostituiscono la bozza.
- Runbook developer desktop/mobile/errori completato dopo build integrata.

C non include questo pilot: il suo stato completo e' **base pronta per D**.
