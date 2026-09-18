# Step 5 — shell frontend, PAC/Rebalancer e review umana

**Stato:** PENDING CONTRACT, SOURCE COPY AND GENERATED CLIENT.
**Dipende da:** Step 1 contract, Step 4 copy, ExactQuantityInput, integrazione client.
**Hard gate:** nessun E2E completo prima dell'approvazione umana.

← Master: [piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Precedente: [copie dominio](plan-phase00Step4PacRebalancerDomainCopies.prompt.md)

## 1. Scopo

Implementare le ASCII approvate nel
[piano UI target](../plan-phase00PacRebalancerUiTarget.prompt.md) come due Tool
distinti sopra una shell condivisa, senza calcoli economici frontend.

Prima si costruisce una candidate UI con fixture e test meccanici; poi il
developer la prova. Gli E2E formalizzano soltanto il comportamento approvato.

## 2. Ownership

```text
frontend/src/lib/features/tools/pac-allocator/planner/**
frontend/src/lib/features/tools/pac-allocator/pac/**
frontend/src/lib/features/tools/pac-allocator/rebalancer/**
frontend/src/lib/features/tools/pac-allocator/PacAllocatorTool.svelte
frontend/src/lib/features/tools/pac-allocator/PortfolioRebalancerTool.svelte
frontend/src/lib/utils/transactions/txPayloadHelpers.ts
frontend/src/lib/components/ui/input/ExactDecimalInput.svelte
frontend/src/lib/components/ui/input/ExactQuantityInput.svelte
frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte
```

Per Slice W3 `fleet-exact-input` possiede esclusivamente i quattro path
shared-input/transaction elencati sopra; non possiede ancora planner, wrapper
PAC/Rebalancer o registry.

Shared writer separati:

- `frontend/src/lib/features/tools/registry.ts`;
- generated API client;
- i18n catalogues;
- E2E runner.

PAC owner non modifica Rebalancer files e viceversa. La shell ha un solo owner.

## 3. Riuso obbligatorio

Prima di creare componenti:

1. inventariare form controls, DataTable, dialog, alert, tabs, chart e mappe;
2. riusare theme/tokens/accessibility esistenti;
3. confrontare il comportamento richiesto con `ExactDecimalInput`;
4. estendere quel componente oppure estrarre `ExactQuantityInput`, ma
   mantenere un solo parser/editor esatto condiviso;
5. migrare la Transaction modal allo shared component scelto;
6. eseguire regressione mirata;
7. creare nuovo componente soltanto quando l'estensione non può preservare il
   contratto esistente.

Nessuna copia locale di parsing numerico, formatting o lifecycle già condiviso.

### 3.1 Decisioni exact input congelate — 2026-09-16

- Estrarre `ExactQuantityInput.svelte` come wrapper semantico di
  `ExactDecimalInput`; le modifiche al low-level restano additive e il callback
  raw preesistente resta byte-compatible.
- Correggere `txPayloadHelpers.ts` senza `Number`/`parseFloat` sulle quantità:
  helper exactness condiviso, non logica PAC-specifica.
- Transaction quantity: massimo 12 cifre intere + 6 frazionarie, coerente con
  DB `Numeric(18,6)`; nessuna migrazione DB.
- PAC/Rebalancer possono configurare 12+12 senza cambiare il budget
  persistibile delle transazioni.
- Hold acceleration resta disponibile. Tempo/cadenza/moltiplicatori usano
  interi ordinari; applicazione step, bounds, segno e valore risultante usano
  soltanto BigInt/string fixed-point.
- `BulkModal` deve restare compatibile; ogni drift payload/comportamento è stop.
- Test `ExactDecimalInput`, `ExactQuantityInput`, `TransactionFormModal` e
  `txPayloadHelpers` sono esclusivamente `test-author`; runner resta a
  `D-main/integration`.

> **Note implementazione**: analisi Fleet `fleet-exact-input`
> (`b2f1f620-f091-4d89-8a52-44936b65934b`) accettata. Writer W3 autorizzabile
> solo su questi path; P1 PAC/Rebalancer restano invariati in questa slice.

> **Note implementazione — exact input 2026-09-16**: writer W3 ha completato
> la slice production quattro-file; test-author ha aggiunto `158` casi
> parametrizzati (`239` totali nei quattro file). `D-main` ha registrato il
> solo path prima mancante,
> `frontend/src/lib/components/ui/input/ExactQuantityInput.test.ts`, nel
> selector `front-utility component-unit`.

> **⚠️ Fuori pista — runtime 2026-09-16**: il primo focused run
> `front-utility component-unit ExactDecimalInput ExactQuantityInput
> TransactionFormModal` ha prodotto `101 passed / 1 failed / 1852 skipped`.
> Il caso view-mode ha dispatchato input/ArrowDown sul textbox disabled e il
> DOM value è mutato da `999999999999.123456` a `1`, senza chiamate payload.
> Sono emessi inoltre warning Svelte `state_referenced_locally` sui prop
> `required`, budget cifre e `resetKey` di `ExactQuantityInput`. Nessun
> backend/DB coinvolto. Red e warning restituiti allo stesso production owner;
> niente E2E/format/check finché il focused selector non torna verde.

> **Note implementazione — rerun 2026-09-16**: il fix controllato
> `disabled || readonly` e la sincronizzazione reattiva sono verdi:
> `102 passed / 1852 skipped`, senza nuovi warning dai due exact input.

> **⚠️ Fuori pista — tx-unit 2026-09-16**: il successivo selector
> `front-transaction tx-unit txPayloadHelpers` ha prodotto
> `362 passed / 4 failed`. Per `required_qty_pos` in modalità `auto`, quantità
> zero, negative o non-finite-decimal rimuovono correttamente
> `cost_basis_mode` ma lasciano erroneamente `cost_basis_override` nel payload.
> Il red deterministico è tornato a production owner e test-author; E2E e gate
> statici restano sospesi.

> **Note implementazione — helper 2026-09-16**: create/update ora applicano lo
> stesso gate exact-sign/metadata; l'update `auto` ammesso conserva anche il
> sentinel valuta `{code, amount: "0"}`. Il selector completo è verde:
> `366 passed`.

> **⚠️ Fuori pista — E2E/static 2026-09-16**: `transactions-modals` non ha
> raggiunto alcuna assertion dei modal: tutti i `19/19` casi sono caduti nel
> `beforeEach`, perché `/` rendeva la pagina Svelte `500 Internal Error` e
> `login-page` non esisteva. Triage: **environment**, cascata pre-auth, non
> difetto exact-input. Il successivo `front check` ha isolato quattro errori
> esterni alla slice: tre nel client ignored rigenerato dalle union W2 ancora
> non congelate e uno in `ToolExecutionMetrics.svelte` sul passaggio da metriche
> numeriche a resource metrics annidate. Nessun errore/warning exact-input.
> Prettier è verde sui file production; resta un solo format delta nel test
> `txPayloadHelpers.test.ts`, restituito a test-author.

> **⚠️ Fuori pista — probe diagnostico 2026-09-16**: un avvio isolato
> `dev.py server --test` per riprodurre il `500` ha attivato automaticamente
> export/codegen perché le API concorrenti erano più nuove del build. Arrestato
> durante `svelte-check`, prima dell'avvio server: nessun path tracked aggiunto,
> ma gli artifact API ignored ora rappresentano il contract W0/W2 incompleto.
> Porta `6153` libera. Nessun rerun E2E finché G3/codegen e frontend platform
> non sono integrati o il coordinator fornisce una baseline isolabile.

> **⚠️ Fuori pista — review scoped 2026-09-16**: la review read-only del
> checkpoint ha bloccato il freeze con due finding HIGH e uno MEDIUM:
> `draftToTxFields()` perdeva il discriminator manuale necessario a conservare
> l'override; `diffDualItem()` eliminava `cost_basis_mode` negli update paired,
> separandolo dal sentinel valuta; utility Tailwind `!border-*` neutralizzavano
> il colore sign/invalid dei tre exact input. Fix production/test autorizzati
> sugli stessi owner; checkpoint selettivo sospeso fino a nuovo focused gate e
> review.

> **Note implementazione — W3 final freeze 2026-09-16**: applicato il delta
> minimo autorevole: intent manual/auto preservato dal modal, metadata
> cost-basis paired atomici senza ampliare `PATCHABLE_FIELDS`, rimossi soltanto
> i border neutral `!important`; regressioni standalone/paired/border/T12
> aggiunte. Prettier mirato e `git diff --check` verdi; porta `6153` libera.
> Evidenza runtime preservata: `68/68` casi exact indipendenti e `343/343`
> tx-unit collezionati verdi. I `37` casi modal/component e `26`
> `promoteHelpers`, più E2E desktop/mobile e `front check`, restano
> **non validabili** finché il client ignored non viene rigenerato dal singolo
> API sync canonico dopo freeze W0 + backend platform. Il `500` pre-auth e le
> 42 suite non collezionate sono environment evidence, non product red.

> **⚠️ Fuori pista — discriminator crash 2026-09-18**: il singolo API sync
> canonico atteso ha esposto un difetto genuino, non ambientale: 9 schemi
> `PortfolioPlannerSource*` (Path/Param, W2) avevano solo `"const"` senza
> `"enum"` nello schema OpenAPI del campo `kind`, per assenza del pattern
> `Field(json_schema_extra={"enum": [...]})` già usato altrove (AiExport). Da
> qui `openapi-zod-client` degradava `kind` a `z.string()` invece di
> `z.literal(...)`, e `z.discriminatedUnion` lanciava un crash runtime su ogni
> import del client rigenerato — 42/72 file component-unit non caricavano
> (inclusi i 3 target W3). Root cause isolata via diff diretto dello schema
> JSON, non da ipotesi. Fix autorizzato e applicato: stesso pattern
> `json_schema_extra` sui 9 campi in `portfolio.py`; nessuna modifica a
> FX/funding/W1/W2/registrazione Tool v2. Static gate (`ruff`/`black`/
> `py_compile`/`diff-check`/introspezione JSON-schema diretta) verdi; nessun
> marker xfail/skip pregresso trovato. Dopo l'API sync coordinator: fix
> confermato via import Node diretto del client rigenerato (nessun crash,
> `z.literal('root')` emesso).

> **Note implementazione — gate rerun post-fix 2026-09-18**: `front-utility
> component-unit` sul catalogo curato di 72 file: `70/72` caricano (da `30/72`
> pre-fix), `1922/1957` test individuali verdi; i 3 file target W3
> (`TransactionFormModal.test.ts`/`ExactDecimalInput.test.ts`/
> `ExactQuantityInput.test.ts`) caricano e passano puliti. `front-transaction
> tx-unit`: `369/369`. `front-transaction transactions-modals` E2E: `19/19`
> desktop (nessuna variante mobile registrata per questo selettore — il runner
> non espone un parametro `project`, resta il default `"desktop"`). `front
> build`: verde. Review a fresco dei 4 diff W3 di produzione
> (`txPayloadHelpers.ts`, `ExactDecimalInput.svelte`, nuovo
> `ExactQuantityInput.svelte`, `TransactionFormModal.svelte`): coerenti, nessun
> difetto — sostituzione sistematica di `Number()`/`parseFloat()` con
> aritmetica BigInt/stringa su tutti i percorsi quantità, wiring prop coerente
> sulle 3 istanze form, fix genuino sul cost-basis-mode (in precedenza
> `buildUpdateDiff` azzerava sempre `cost_basis_override` in modalità auto,
> perdendo un valore manuale precedente).

> **⚠️ Fuori pista — 2 difetti scoperti, non del W3 2026-09-18**: il rerun ha
> smascherato due difetti indipendenti, entrambi mascherati fino ad ora dal
> crash discriminator, nessuno causato da questa slice:
> (1) `PacAllocatorTool.test.ts`/`PortfolioRebalancerTool.test.ts` (Tool
> platform, non W3) ora caricano ma falliscono `ToolClientError:
> invalid_catalog` — la fixture mock del catalogo (helper `policy()` +
> `operations.map()` inline) precede l'estensione resource-budget e manca di 7
> campi ora required (`cleanup_timeout_ms`/`client_timeout_ms`/
> `engine_timeout_ms`/`memory_limit_bytes`/`request_timeout_ms` per-operation,
> `engine_timeout_ms`/`memory_limit_bytes` per-policy), introdotti dal commit
> pregresso `4a38b9061`. Root-caused via `.safeParse()` diretto sullo schema
> Zod. **Triage coordinator: non toccare, fixture debt per futuro test-author
> Tool-platform, routing separato.**
> (2) `front check` mostrava ancora gli stessi 3 errori (righe spostate) — non
> lo stesso bug: il valore runtime `kind: z.literal('root')` era già corretto,
> ma la dichiarazione restava `const X: z.ZodType<X> = z.object(...)`,
> annotazione che nasconde a TypeScript la forma ZodObject concreta richiesta
> da `z.discriminatedUnion`. Causa: `frontend/scripts/
> fix-openapi-discriminators.mjs` esiste già per questo scopo, ma la sua
> allow-list `discriminatedSchemas` (40 nomi) non includeva i 9 nuovi schemi
> Path/Param. **Autorizzato e applicato**: aggiunti i 9 nomi allo stesso array,
> stesso pattern degli altri 40; verificato che `requiredLiteralDiscriminators`
> (secondo array, per suffissi `.optional().default(...)`) non serve per questi
> 9 — `kind` è già literal puro senza suffisso. Statico verde (`node --check`,
> `prettier --check`, `git diff --check`, 9 inserimenti/1 file). In attesa
> del rerun API sync coordinator prima di ri-eseguire `front check`.

## 4. Shell a nove step

```text
1 Scenario
2 Liquidità
3 Broker
4 Asset / holding
5 Routing
6 Target
7 FX
8 Strategia
9 Review
```

Ogni step:

- modifica soltanto il draft;
- mostra validazione locale di forma;
- conserva errori backend tipizzati;
- espone copy action contestuali;
- dichiara dipendenze downstream;
- non calcola fee, FX, quantità finali o obiettivi.

Il submit crea snapshot immutabile. Il risultato è read-only.

## 5. Draft dependency graph

Esempi:

```text
valuation_currency
  -> prices -> FX -> target preview -> result stale

brokers
  -> cash -> routes -> fee/tax -> result stale

assets/holdings
  -> routes -> target -> strategy -> result stale

order_instruction
  -> min/cap/step -> strategy -> result stale
```

Cambio distruttivo:

1. mostra sezioni invalidate;
2. richiede conferma;
3. elimina soltanto derivati dipendenti;
4. incrementa `draft_revision`;
5. annulla request incompatibili;
6. non sovrascrive input indipendenti.

## 6. Lifecycle

Stato minimo:

```text
account_generation
component_instance_id
draft_revision
request_sequence
review_snapshot_id
active_abort_controller
result_snapshot_id
```

Una response copy/compute viene applicata soltanto se:

- account invariato;
- componente ancora montato;
- sequence corrente;
- draft/review snapshot atteso;
- sezione target ancora compatibile.

Gestire:

- doppio click;
- navigazione indietro;
- unmount;
- account switch;
- cancel;
- late success;
- late error;
- retry;
- result stale dopo edit.

Nessun binding live fra dominio e draft.

## 7. Input

`ExactQuantityInput`:

- sorgente autorevole stringa;
- virgola e punto locale;
- trailing zero preservati;
- step arrow;
- blur normalization non distruttiva;
- min/max/sign;
- disabled/readonly;
- testid;
- accessibilità;
- nessun round a `number`.

La stessa sessione può includere:

- Asset whole;
- Asset monetary;
- holding frazionarie;
- cap/minimi in unità diverse ma esplicite;
- più Broker e valute.

## 8. PAC e Rebalancer

PAC:

- scenario iniziale zero;
- funding/contributi;
- BUY-only;
- `proportional` e `min_fragmentation`;
- target e risultato focalizzati sul nuovo capitale.

Rebalancer:

- holding iniziali e distribuzione corrente;
- `invest_only`;
- `invest_and_sell`;
- disclosure SELL, PMC/tax e baseline;
- grafici Prima/Target/Dopo.

Sono route/wrapper distinti. Policy/mode non vengono nascosti in un selettore di
prodotto unico.

## 9. Risultato

Componenti condivisi alimentati dal DTO:

- status/proof banner;
- selector Primario/Variante margine;
- KPI `F_ref`, `F_final`, `U`, costi, cash e riserve;
- Asset allocation chart;
- Type/Sector ribbons;
- Geography map;
- Asset DataTable;
- piano operativo Funding → FX → Broker;
- Broker orders;
- native cash ledger;
- solution compare;
- diagnostics/provenance/issues.

Desktop usa tabelle complete; mobile proietta le stesse righe in card. Nessun
dato viene eliminato sul mobile.

Il frontend può:

- selezionare;
- filtrare;
- ordinare;
- formattare;
- nascondere per privacy.

Non può:

- applicare delta;
- calcolare finali;
- convertire FX;
- aggregare denaro;
- ricostruire ledger/fee/tax;
- decidere proof o fattibilità.

## 10. Stati

Tutte le viste approvate:

- pristine/manual;
- copy preview;
- dirty conflict;
- invalid;
- needs_input;
- unsupported;
- busy/cancel;
- error;
- stale;
- no_op;
- incumbent proven;
- incumbent gap/not proven;
- no incumbent;
- infeasible proven.

Status, issue e label restano leggibili in privacy mode. Valori, quantità,
percentuali e grafici vengono oscurati coerentemente.

## 11. Test prima della review umana

Consentiti:

- unit del draft reducer/state machine;
- unit `ExactQuantityInput`;
- component test dei nove step;
- component test copy/stale/cancel;
- schema fixture rendering;
- accessibilità meccanica;
- type-check;
- build;
- smoke tecnico minimo.

Non consentiti come gate:

- E2E completi della UX;
- screenshot personali;
- test che congelano testo tradotto;
- assunzioni CSS/class;
- il vecchio E2E P1 come acceptance della UI nuova.

## 12. Runbook review umana

Ambiente:

- lane `6153`;
- `/tmp/librefolio-r2-d`;
- fixture sintetica;
- nessun portafoglio personale.
- lane riservata per l'intera sessione; tutti gli altri workstream sospendono i
  comandi runtime fino a shutdown e prova porta libera.

PAC desktop/mobile:

1. manuale completo;
2. ogni copy indipendente;
3. whole + monetary;
4. multi-currency/FX;
5. due policy;
6. primary/deployment compare;
7. invalid/needs_input/unsupported/no_op/limit.

Rebalancer desktop/mobile:

1. multi-custody;
2. distribuzione corrente come base target;
3. invest-only;
4. invest-and-sell;
5. fee/tax/SELL explanation;
6. before/target/after;
7. primary/deployment compare;
8. stale/account/cancel.

Per entrambi:

- back/forward e conferme;
- tastiera/focus;
- contrasto/dark;
- tabelle/grafici;
- privacy;
- copy provenance.

Verdetto separato:

```text
PAC: APPROVED | CHANGES REQUIRED
Rebalancer: APPROVED | CHANGES REQUIRED
```

## 13. Sequenza

- [ ] 1. Inventariare componenti e fissare ownership.
- [ ] 2. Decidere extend-vs-extract e migrare un solo exact input condiviso.
- [ ] 3. Implementare shell e draft graph.
- [ ] 4. Implementare lifecycle copy/compute.
- [ ] 5. Implementare result primitives da fixture.
- [ ] 6. Implementare PAC wrapper e flusso.
- [ ] 7. Implementare Rebalancer wrapper e flusso.
- [ ] 8. Eseguire unit/component/type/build.
- [ ] 9. Preparare ambiente review.
- [ ] 10. Eseguire review PAC e registrare verdetto.
- [ ] 11. Eseguire review Rebalancer e registrare verdetto.
- [ ] 12. Correggere e ripetere superfici respinte.
- [ ] 13. Congelare doppio `APPROVED`.

## 14. Stop conditions

- DTO non congelato;
- UI richiede un calcolo non presente nel backend;
- source copy non è auth-safe;
- una risposta vecchia può mutare il draft;
- mobile omette fatti;
- componenti condivisi vengono duplicati;
- si propone E2E completo prima della review;
- developer richiede cambi a matematica/constraint.

## 15. Definition of Done

- nove step conformi alle ASCII;
- PAC/Rebalancer distinti;
- mixed instruction editabile esattamente;
- copy manuale/esplicita/stale-safe;
- risultato esclusivamente backend-authored;
- desktop/mobile/a11y/privacy verificati;
- unit/component/type/build verdi;
- PAC `APPROVED`;
- Rebalancer `APPROVED`;
- E2E gate aperto;
- CP7 pronto e porta libera.

→ Step 6: [Integrazione, test e docs](plan-phase00Step6PacRebalancerIntegrationTestsDocs.prompt.md)
