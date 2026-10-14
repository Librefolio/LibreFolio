# Round 6 — PAC/Rebalancer UI Blueprint

> **ARCHIVIO:** record di approvazione UI consolidato nella specifica target
> unica
> [`../plan-phase00PacRebalancerTargetDesign.prompt.md`](../plan-phase00PacRebalancerTargetDesign.prompt.md).

**Stato:** ✅ COMPLETATO — configurazione UI approvata dal developer; design-only,
nessuna implementazione production/test.

> **Correzione semantica 2026-09-16:** estetica e wizard approvati restano
> invariati. Entrambi i Tool mostrano primario globale fixed-L2 e variante
> margine BUY-only; nel PAC le card riordinano tier operativi, nel Rebalancer
> scelgono il dominio SELL. `L2_fixed/U` sono score normativi;
> percentuali/D∞/D1 sono diagnostici. Ogni incumbent è Decimal-validato e lo
> status floating non viene promosso a proof esatta.

← Previous:
[Round 5 — PAC/Rebalancer operational planner](plan-phase00Step2Round5-PacRebalancerOperationalPlanner.prompt.md)

→ Follow-up:
[Round 7 — PAC/Rebalancer operational migration](plan-phase00Step2Round7-PacRebalancerOperationalMigration.prompt.md)

**Artifact UX approvato, ora promosso nella suite target:**
[PAC/Rebalancer UI completa](../plan-phase00PacRebalancerUiTarget.prompt.md).

**Design prodotto normativo:**
[PAC/Rebalancer end-to-end design](pac-rebalancer-end-to-end-design.md).

## 1. Mandato e confine

Round 6 ha trasformato il flusso operativo Round 5 in una specifica visuale
desktop/mobile verificabile prima dello sviluppo. Ha coperto entrambi i Tool:

- PAC: liquidità selezionata → Asset target → ordini eseguibili;
- Rebalancer: portafoglio corrente → target → BUY e SELL opzionali.

Il round non ha modificato backend, frontend, test, API, DB, i18n, MkDocs,
dipendenze o runtime. Le ASCII sono design approvato, non prova di consegna.

## 2. Flusso input approvato

Wizard incrementale a nove step:

1. scenario e Tool;
2. liquidità e fonti;
3. Broker operativi;
4. Asset/holding;
5. routing Asset×Broker;
6. target;
7. FX;
8. strategia;
9. review snapshot e compute unico.

Avanti/indietro conserva il draft. Una modifica upstream che invalida dati downstream
apre un modal con impatto esatto e richiede conferma prima della cancellazione.
Nessun binding live o risposta vecchia può sovrascrivere input modificati.

## 3. Decisioni UI congelate

- Step liquidità separato da configurazione Broker operativo.
- Fonte da conto esistente selezionabile parzialmente; fonte nuova/manuale esplicita.
- Broker operativo esistente o manuale.
- Selezione Asset/Broker tramite componenti di dominio e modali esistenti.
- `order_instruction_kind` enum:
  - `whole_quantity`;
  - `monetary_amount`.
- `order_amount_step` solo per `monetary_amount`; nessun `quantity_step`.
- Fee BUY/SELL indipendenti, ciascuna con fisso, percentuale, minimo e massimo.
- Target in step dedicato; nessuna pseudo-preview economica frontend.
- Compute atomico una sola volta dopo review completa.
- Risultati base e ottimizzati separati e confrontabili.
- Piano operativo unico, foldable: Funding → FX → Broker → ordini.
- Nomi Asset con icona; tabelle basate su `DataTable` e
  `ColumnVisibilityToggle`.
- Matrice mini-bar per Asset.
- Tipo/Settore: rail verticali Prima→Target→Dopo con nastri rastremati.
- Geografia: mappe sincronizzate Prima/Dopo + delta, senza archi inventati.
- Mobile usa stesso modello dati con card/accordion; nessun contratto parallelo.

## 4. Componenti da riusare o generalizzare

Riuso obbligatorio:

- `CompactCashCell.svelte`;
- `ExactDecimalInput.svelte`;
- `AssetSelect.svelte`;
- `BrokerSearchSelect.svelte`;
- `AssetModal.svelte`;
- `BrokerModal.svelte`;
- `AssetIcon.svelte`;
- `BrokerIcon.svelte`;
- `CurrencySearchSelect.svelte`;
- `SingleDatePicker.svelte`;
- `ConfirmModal.svelte`;
- `DataTable.svelte`;
- `ColumnVisibilityToggle.svelte`;
- `GeographyMap.svelte`;
- lifecycle/theme ECharts;
- `KpiCard.svelte`.

Round 7 estrae la logica quantità esatta di `TransactionFormModal.svelte` in un
componente shared `ExactQuantityInput.svelte`, preservando il valore autorevole come
stringa e il comportamento osservabile di Add Transaction.

## 5. Progressione completata

- [x] Step 1 — shell desktop/mobile e navigazione — 2026-09-15
  > **Nota implementazione**: definite stepper, summary rail, progress mobile,
  > CTA e persistenza draft; Review A approvata.

- [x] Step 2 — fonti, Broker, Asset, routing, target, FX, strategia e review —
  2026-09-15
  > **Nota implementazione**: applicati split liquidità/Broker, fonti manuali,
  > enum ordine, component reuse e compute atomico; Review B approvata.

- [x] Step 3 — risultati PAC/Rebalancer — 2026-09-15
  > **Nota implementazione**: definite gerarchia KPI/grafici/tabelle, soluzioni
  > base/ottimizzata e piano operativo foldable; Review C approvata.

- [x] Step 4 — responsive, stati e casi limite — 2026-09-15
  > **Nota implementazione**: allineati desktop/mobile, invalid/needs-input,
  > no-op/infeasible/limited/busy/stale e privacy/provenance; Review D approvata.

- [x] Step 5 — approvazione estetica finale — 2026-09-15
  > **Nota implementazione**: developer ha approvato l'intera configurazione UI,
  > inclusi Sankey/ribbon verticali e componenti shared.

## 6. Evidenza e limiti

Evidenza valida: review conversazionale developer e artifact ASCII completo.
Nessun test/build/lint/server/DB/API sync è stato eseguito o richiesto per questo round.
L'approvazione estetica non autorizza implementazione.

SHA-256 live del Blueprint approvato:
`88b7665fc8c1ee98001a751e74207a4acbdd6ce015a8f2609042d82ab720b26d`.

## 7. Definition of done

- [x] Flusso input completo per entrambi i Tool.
- [x] Desktop, tablet e mobile coperti.
- [x] Navigazione reversibile e invalidazione distruttiva esplicita.
- [x] Grafici, DataTable, dettagli e piano operativo definiti.
- [x] Componenti shared esistenti inventariati.
- [x] Review A/B/C/D/finale approvate.
- [x] Follow-up implementativo Round 7 separato.
