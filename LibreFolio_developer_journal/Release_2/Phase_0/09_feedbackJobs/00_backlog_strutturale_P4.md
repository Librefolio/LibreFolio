# Backlog strutturale — i task P4 dell'audit 08

**Creato**: 2026-09-07 · **Origine**: `08_newCleanAndDocumentation_audit` (archiviato in
`Release_2/phases/`) · **Natura**: lavoro strutturale rimandato — NON bug, NON urgente,
ma debito che cresce col tempo. Da pescare al prossimo round di sviluppo.

Queste 8 aree ereditano il debito dell'audit di pulizia (02/09). La verifica del 07/09 ha
distinto i refactor ancora aperti dagli alias e dalle voci S6 già risolte nella tornata P0–P3.
I marker `TODO(P2-refactor)` erano 26 al 03/09 e sono **25** alla baseline `a9138140`:
`grep -rn "TODO(P2-refactor)" backend/ scripts/`. Non sono 25 task autonomi approvati.

> ⚠️ I report citati sotto sono **archiviati** in `../../phases/08_newCleanAndDocumentation_audit/`
> (li descrivono con l'evidenza del 02/09; le righe possono essere scivolate da allora).

| # | Task | Perché / cosa comporta | Dimensione | Descritto in |
|---|------|------------------------|-----------|--------------|
| P4-1 | **Scissione di `asset_source.py`** (5 106 righe al 07/09; erano 5 162 al 02/09) in moduli per responsabilità | Separare provider management, prezzi, metadata, CRUD e ricerca; "bulk ops" da solo non è un confine utile | L | [03 §T8](../../phases/08_newCleanAndDocumentation_audit/03_services_pricing_fx.md) · [14 #6.13](../../phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md) |
| P4-2 | **Scomposizione di `transaction_service.execute_batch`** (C901 = 115, 637 righe) in stage ordinati con contesto esplicito | Il dispatch non può rendere indipendenti split/update/create/promote/link; il commit resta al chiamante | XL | [02 §T8](../../phases/08_newCleanAndDocumentation_audit/02_services_core.md) · [11 #7](../../phases/08_newCleanAndDocumentation_audit/11_crosscutting.md) |
| P4-3 | **Estrazione mirata BRIM**, partendo da `broker_credit_agricole._parse_account_movements` (C901 storico 71; oggi 692 righe, nove closure) | Helper comuni già presenti; i 35 siti C901 non sono tutti parser annidati equivalenti. Prima fasi locali, poi riuso dimostrato | L | [04 §T2](../../phases/08_newCleanAndDocumentation_audit/04_providers.md) · [17 #4](../../phases/08_newCleanAndDocumentation_audit/17_stabilizzazione.md) |
| P4-4 | **`get_history_value` di Yahoo Finance** (complessità 31, invariata da un mese) | Il provider più usato e più instabile; i retry/fallback annidati sono il punto caldo | M | [04 §T4](../../phases/08_newCleanAndDocumentation_audit/04_providers.md) |
| P4-5 | **Migrazione Svelte 5 Runes** di `BrokerSharingPanel.svelte` (24 `$:`), `PreferencesTab.svelte` (9), `GlobalSettingsTab.svelte` (10) | 43 statement legacy; preservare binding, salvataggi, reset, permessi e caricamenti | M | [11 #6](../../phases/08_newCleanAndDocumentation_audit/11_crosscutting.md) · [10 §G3](../../phases/08_newCleanAndDocumentation_audit/10_frontend_charts.md) |
| P4-6 | **Matrice dichiarativa per `validate_status_matrix`** (`schemas/signals.py:1050`, C901 32) | Tabella di presenza/assenza più predicati semantici; conservare sottomatrice FAILED e invarianti trasversali | M | [05 §T4](../../phases/08_newCleanAndDocumentation_audit/05_signals_risk.md) |
| P4-7 | **Ciclo di vita dei cache store frontend** (`removeAssetPriceStore` mai chiamato, registry non completamente collegati al reset sessione) | Confine account già presente; pool limitato a 8 worker. Misurare entry, punti, intervalli e riferimenti prima di scegliere budget/rilascio | L | [08 §T2](../../phases/08_newCleanAndDocumentation_audit/08_frontend_state_api.md) · [14 #9](../../phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md) |
| P4-8 | **Coda S6 riconciliata**: aperte 6.2/6.4/6.11; 6.7/6.8 alias di P4-6/P4-2; 6.3/6.12 già risolte; 6.14 solo entro P4-3; **TRY003 congelata** | Il report 14 non incorpora tutte le chiusure P2: fa fede la verifica corrente sotto | varie | [14 #23/#26](../../phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md) |

## Come leggerlo

- **P4-1/2/3** sono i refactor ampi (L/XL), senza dipendenza hard fra loro.
  Migliorano la testabilità; non sono prerequisiti per qualunque test di errore.
- **P4-4/5/6** sono medi (M); **P4-7** è L includendo misura, policy e lifecycle completo.
- **P4-8** è la coda: si spunta quando si tocca l'area.
- I 26 marker storici sono nel piano P1 archiviato; i **25 attuali** e il loro rapporto
  con lo scope approvato sono nell'appendice A di [06_piano_sprint.md](06_piano_sprint.md).
  Il marker scomparso era `compute_wac_iterative_multi_broker`, rimosso in `2572b240`.

## Analisi 2026-09-07

Baseline `a9138140`; superfici, rischi e DoD in [06_piano_sprint.md](06_piano_sprint.md).
La pubblicazione iniziale non avviava refactor. Successivamente il dev ha approvato
il solo Gruppo B r2 (SP04-SP05), in esecuzione dal 2026-09-07 nel
[piano dedicato](../11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md).
Le spunte di presa in carico sotto non attestano il completamento dell'implementazione.

| Task | Nota di analisi | Sprint |
|---|---|---|
| P4-1 | 🟡 In implementazione su K/SP08: facciata compatibile + moduli per responsabilità; non ricreare AssetMetadataService. | SP08 |
| P4-2 | ✅ Integrato con L/SP16: `execute_batch` ridotto a orchestratore esplicito, contesto typed + stage ordinati, contratto/atomicità invariati. [Piano](../23_transactionBatchRefactor/plan-phase00TransactionBatchRefactor.prompt.md). | SP16 |
| P4-3 | ✅ Integrato e developer-accepted con G; caratterizzazione CA, helper maturity CA/Intesa ed eToro FEE. [Piano](../18_brimTargeted/plan-phase00BrimTargeted.prompt.md). | SP09 |
| P4-4 | 🟡 In implementazione su K/SP08: refactor locale Yahoo prima della scissione manager. | SP08 |
| P4-5 | ✅ Integrato con B/SP05 (`514582a47`). [Piano](../11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md). | SP05 |
| P4-6 | ✅ Integrato con B/SP04 (`514582a47`), incluso alias S6 6.7. [Piano](../11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md). | SP04 |
| P4-7 | Parziale, L: misura/ownership prima di eviction e rilascio. | SP10 |
| P4-8 | Coda deduplicata nella tabella seguente. | Per voce |

| Residuo | Esito 2026-09-07 |
|---|---|
| 6.2 | ✅ Integrato in B/SP04. `is_chain` e `providers_used` restano output-only; membership configurata distinta dal percorso e dalla provenance. |
| 6.3 | ✅ Chiuso per rimozione dei quattro aggregate; [audit 02](../../phases/08_newCleanAndDocumentation_audit/02_services_core.md), nessun helper da ripristinare. |
| 6.4 | 🟡 In implementazione su K/SP08: estrazione PREPARE/FETCH/PERSIST dopo il move meccanico. |
| 6.7 | ✅ Integrato come alias P4-6 nello stesso piano B; nessuna seconda implementazione. |
| 6.8 | ✅ Chiuso come alias P4-2 nello stesso refactor L/SP16; nessuna seconda implementazione. |
| 6.11 | ✅ Integrato in B/SP04: 17 guardie Python in memoria, nessuna bonifica DB. |
| 6.12 | ✅ Risolto P2-9: registry unico, servizi separati per scelta; [piano P2](../../phases/08_newCleanAndDocumentation_audit/plan-phase00P2ProductDecisions.prompt.md). |
| 6.14 | Nessuna campagna autonoma; limiti incorporati in P4-3. |
| TRY003 | Congelato: TRY non nel select; nessuna attivazione implicita. |

## Coordinamento — confronto successivo 2026-09-07

La sezione 11 di [06_piano_sprint.md](06_piano_sprint.md) distingue dipendenze hard,
corsie indipendenti e file/risorse da serializzare. P4-4/5/6, S6 6.2/6.11, BRIM e
contratti Tool non formano una catena obbligatoria. Scissione asset_source e refresh
restano sotto un owner; test/backend/DB e rigenerazioni condivise hanno una sola coda.

P4-5 conserva la UI: niente redesign implicito durante la migrazione. Se un refactor
introduce nuove viste o modifiche visive importanti, prima servono ASCII approvati dal dev
e dopo walkthrough operativo e feedback, come G-UX-DESIGN/G-UX-REVIEW del piano.

> **Presa in carico 2026-09-07**: soltanto Gruppo B autorizzato a implementare r2.
> Avanzamento per-step e accettazione nel piano 11; runtime/test/build/API sync e writer
> condivisi riservati al suo integratore, una suite alla volta. A/C/D restano in planning.
> Nessuna correzione persistente di produzione, migrazione, staging, commit o push.

> **Aggiornamento 2026-09-08**: B00-B09 completati nel piano 11; B10 resta
> `awaiting_dev_review`, rinviato dal dev alla propria disponibilità. La chiusura
> complessiva non è attestata dalle spunte di presa in carico. Server TEST B fermato
> e coda runtime restituita; nessun avvio automatico di A/C/D.
