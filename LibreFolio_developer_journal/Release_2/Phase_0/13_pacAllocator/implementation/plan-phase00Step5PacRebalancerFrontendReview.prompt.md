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
frontend/src/lib/components/ui/input/ExactDecimalInput.svelte
frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte
```

Un eventuale
`frontend/src/lib/components/ui/input/ExactQuantityInput.svelte` entra
nell'ownership soltanto se l'audit dimostra che estendere `ExactDecimalInput`
romperebbe il contratto esistente.

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
