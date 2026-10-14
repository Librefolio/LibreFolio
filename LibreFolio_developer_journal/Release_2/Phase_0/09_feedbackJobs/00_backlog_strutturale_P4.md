# Backlog strutturale — i task P4 dell'audit 08

**Creato**: 2026-09-07 · **Origine**: `08_newCleanAndDocumentation_audit` (archiviato in
`Release_2/phases/`) · **Natura**: lavoro strutturale rimandato — NON bug, NON urgente,
ma debito che cresce col tempo. Da pescare al prossimo round di sviluppo.

Queste 8 aree ereditano il debito dell'audit di pulizia (02/09). La verifica del 07/09 ha
distinto i refactor ancora aperti dagli alias e dalle voci S6 già risolte nella tornata P0–P3.
I marker `TODO(P2-refactor)` erano 26 al 03/09 e sono **25** alla baseline `a9138140`:
`grep -rn "TODO(P2-refactor)" backend/ scripts/`. Non sono 25 task autonomi approvati.
Al 2026-10-09 sono **21**, con la stessa `grep` (verifica Q del 2026-10-09, base `3cceb4f90`).

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
| P4-8 | **Coda S6 riconciliata**: 6.2/6.3/6.4/6.7/6.8/6.11/6.12 chiuse; 6.14 limitata al refactor G già consegnato; **TRY003 congelata** | Il report 14 non incorpora tutte le chiusure successive: fa fede la verifica corrente sotto | varie | [14 #23/#26](../../phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md) |

> **Stato al 2026-10-09** (verifica Q del 2026-10-09, base `3cceb4f90`): P4-1…P4-6 sono nel target; P4-8 è come sopra. **P4-7 resta aperto**: `frontend/src/lib/stores/assetPriceStoreRegistry.ts:30` è una `Map` senza limite né eviction, `removeAssetPriceStore` (`:64`) non viene chiamata da nessun altro file, e niente la aggancia al reset di sessione.

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
[piano dedicato](../../phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md).
Le spunte di presa in carico sotto non attestano il completamento dell'implementazione.

| Task | Nota di analisi | Sprint |
|---|---|---|
| P4-1 | ✅ Integrato con K/SP08: `asset_source.py` è una facciata compatibile; implementazione canonica separata per responsabilità. [Piano](../../phases/22_assetPricingRefactor/plan-phase00AssetPricingRefactor.prompt.md). | SP08 |
| P4-2 | ✅ Integrato con L/SP16: `execute_batch` ridotto a orchestratore esplicito, contesto typed + stage ordinati, contratto/atomicità invariati. [Piano](../../phases/23_transactionBatchRefactor/plan-phase00TransactionBatchRefactor.prompt.md). | SP16 |
| P4-3 | ✅ Integrato e developer-accepted con G; caratterizzazione CA, helper maturity CA/Intesa ed eToro FEE. [Piano](../../phases/18_brimTargeted/plan-phase00BrimTargeted.prompt.md). | SP09 |
| P4-4 | ✅ Integrato con K/SP08: acquisizione, mapping prezzi ed eventi Yahoo separati con contratto invariato. [Piano](../../phases/22_assetPricingRefactor/plan-phase00AssetPricingRefactor.prompt.md). | SP08 |
| P4-5 | ✅ Integrato con B/SP05 (`514582a47`). [Piano](../../phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md). | SP05 |
| P4-6 | ✅ Integrato con B/SP04 (`514582a47`), incluso alias S6 6.7. [Piano](../../phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md). | SP04 |
| P4-7 | Parziale, L: misura/ownership prima di eviction e rilascio. | SP10 |
| P4-8 | Coda deduplicata nella tabella seguente. | Per voce |

| Residuo | Esito 2026-09-07 |
|---|---|
| 6.2 | ✅ Integrato in B/SP04. `is_chain` e `providers_used` restano output-only; membership configurata distinta dal percorso e dalla provenance. |
| 6.3 | ✅ Chiuso per rimozione dei quattro aggregate; [audit 02](../../phases/08_newCleanAndDocumentation_audit/02_services_core.md), nessun helper da ripristinare. |
| 6.4 | ✅ Integrato con K/SP08: refresh esplicito PREPARE/FETCH/PERSIST, sessioni e risultati parziali invariati. |
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

## Debito nuovo registrato 2026-09-22 — round D / I / Risk / J

Baseline `0a1d98eaf` (`dev_release2`), dopo l'integrazione dei quattro workstream.
Tre voci **misurate**, non stimate: ciascuna riporta il comando che la riproduce.

| # | Task | Perché / cosa comporta | Dimensione |
|---|------|------------------------|-----------|
| P4-9 | **Conversione dei test specchio** di `frontend/src/lib/components/charts/chartCoreHelpers.test.ts` da lettura del testo sorgente a esecuzione delle funzioni (DBT-D di I) | Un test che legge il sorgente si rompe a ogni cambio di sola grafia e non prova il comportamento: la stessa proprietà si fissa **eseguendo** la funzione. Il file è verde; da convertire restano i 7 specchi ri-pinnati da `2e4c8589f`, che leggono ancora il sorgente (35 `readFileSync` nel file) | M |
| P4-10 | **Sei siti di Risk** che rendono denaro fuori dal canale di mascheratura: 3 `not-money`, 3 che delegano a una funzione mascherata | Non registrabili nel gate per ragioni strutturali (sotto); vanno decisi come classe, non uno per uno | S |
| P4-11 | **Copertura del gate privacy**: aggancia 1 degli 8 **consumatori** di `fmtCurrency` in `GrowthChart.svelte` | Lo scanner esige **due** token nello stesso template literal (uno valuta, uno numerico): quattro righe che rendono denaro cadono lì. L'unico consumatore visto sopravvive per i nomi delle variabili accanto, e un rename porta il gate al rosso sbagliato | M |

> **Stato al 2026-10-09** (verifica Q del 2026-10-09, base `3cceb4f90`; P4-9 e P4-11 precisati con le note di I):
> - **P4-11 è chiuso**: `804bc9903` (24/09) maschera `fmtCurrency` alla sua definizione, oggi a `GrowthChart.svelte:2156`, con `maskFormattedNumber`. Il gate custodisce quel confine (`moneyRenderSites.test.ts:193-196`), la lista `residual` è vuota (`:281`) e `GrowthChart.test.ts:1080` fissa il comportamento. Lo stesso commit maschera il secondo grafico, `PerformanceChart.svelte` (`shortMoney` `:166`, `axisTickAmount` `:183`). Le righe dell'analisi qui sotto sono del 22/09.
> - **P4-9 resta aperto, come conversione** (DBT-D di I, [piano 20 §6.0.11](../../phases/20_performanceCharts/plan-phase00PerformanceCharts.prompt.md)): `2e4c8589f` (28/09) ha chiuso i rossi e il file è verde (145/145 alla misura di I). Restano i 7 specchi ri-pinnati, che leggono ancora il sorgente; nel file le letture con `readFileSync` sono 35.
> - **P4-10 è da riverificare** dopo il Round 2 della privacy: `riskAnalysisHelpers.ts` risulta `masked` in `moneyRenderSites.test.ts`.

### P4-9 — la conversione, e le due trappole già pagate

**Cosa resta** (09/10). I rossi non ci sono più: `2e4c8589f` (28/09) ha cancellato per
nome, uno alla volta, gli specchi di comportamenti rimossi, e ha ri-pinnato i 7 che
fissavano proprietà ancora vere, ciascuno con un commento sul cambio di prodotto che
l'aveva rotto. Resta la sostanza, DBT-D di I: quei 7 specchi leggono ancora il testo
sorgente, quindi si romperanno al prossimo cambio di sola grafia. Convertirli vuol dire
fissare la stessa proprietà **eseguendo** la funzione.

Le due trappole valgono anche per la conversione.

**Non cancellare in automatico.** Un passaggio a conteggio di parentesi ha tagliato oltre
il confine di un `it()` e vitest è passato a *«no tests»*: i rossi nominati sono diventati
162 test spariti in silenzio. Si converte o si cancella una voce alla volta, a mano,
verificando il conteggio dopo ciascuna.

**Non usare `.skip`.** Criterio del developer del 22/09: *«non mi importa di chi è la
causa, basta che non si nasconda… l'importante è che i rossi non diventino silenziosi»*.
Uno `.skip` è un rosso che smette di chiedere.

```
cd frontend && node_modules/.bin/vitest run src/lib/components/charts/chartCoreHelpers.test.ts
atteso: tutto verde, con lo stesso numero di test prima e dopo ogni conversione
```

> **Storico.** Al 22/09 i rossi nominati erano 12: 5 residui di comportamenti rimossi su
> richiesta e 7 proprietà ancora vere in helper rinominati o rimodellati. I nomi sono nel
> corpo del commit `22b82e3fb`, e il comando dava 12 rossi su 162 test. Il rinvio l'aveva
> deciso il developer con la sua causa: *«è imperativo riallineare la baseline, tanto i
> test bisognerà rigirarli tutti»*. Un debito senza causa si eredita; con causa si
> ri-discute. Al 28/09 i rossi erano 11 su 159 test, e `2e4c8589f` ha portato il file a
> 144 test, tutti verdi.

> 🔗 **P4-9 e P4-11 condividono un meccanismo, non solo un'area.** In entrambi i casi la
> riparazione che il rosso *suggerisce* è quella che distrugge la copertura: là cancellare
> i test residui, qui cancellare la voce di registro. Vanno letti insieme, o il secondo
> sembra risolvibile allentando una regex.

### P4-10 — perché non bastava registrarli

Il registro di `moneyRenderSites.test.ts` è **indicizzato sul contenuto ma popolato dallo
scanner**: `stale = REGISTRY.filter((s) => !found.has(key(s)))`. Una voce che lo scanner
non produce è stantia nell'istante in cui la si scrive — provato con una sonda temporanea,
**due rossi insieme** (il controllo del marcio e il controllo positivo).

Serve a impedire che un sito **noto** cambi in silenzio, non a ricordarne uno invisibile.
I sei sono dichiarati nel [piano di J](../../phases/24_privacyGlobal/plan-phase00PrivacyGlobalRound1-MaskingCore.prompt.md);
`formatScopedCurrencyAmount` è entrata invece in `SAFE_CALL`, che è il posto dove una
promessa si può verificare.

⚠️ **`SAFE_CALL` non è la scorciatoia.** Una voce lì è una promessa, e ha un prezzo:
la funzione dev'essere un export fissato da un test che si romperebbe togliendo la
mascheratura. E va **ancorata** con `\b`: un prefisso nudo assolve ogni nome più lungo
che comincia uguale, creando un permesso che non si può revocare cancellando la riga che
sembra concederlo.

### P4-11 — perché un rosso piccolo è il segnale peggiore

> Righe del 22/09, quando il file ne aveva 2 246. Oggi ne ha 2 583, e `fmtCurrency` è a
> `:2156`, mascherata alla definizione: vedi lo stato al 2026-10-09 sopra.

La dimensione del rosso misura quanto il gate **vede**, non quanto il file **espone**, e
le due quantità divergono esattamente dove il file è peggiore. `GrowthChart.svelte`
(2 246 righe dopo il merge) definisce `fmtCurrency` a `:1834` e la consuma **8** volte;
il gate ne aggancia **1**. Le sette invisibili non sono una classe sola — replicando la
logica dello scanner riga per riga:

| righe | perché il gate non le vede |
|---|---|
| `:1893` `:1896` | `fmtCurrency(...)` è **argomento di chiamata**, fuori da ogni template literal |
| `:1895` | il literal c'è, ma il denaro è fuori: dentro c'è solo `${eurLabels.nav}` |
| `:1915` `:1927` `:1943` `:1958` | 🔴 il literal **contiene** il token valuta, ed è scartato dalla **regola di co-occorrenza** |

Lo scanner esige **due** token distinti nello stesso literal: uno che somigli a valuta
(`/currency|symbol/i`) **e un altro** che somigli a un numero. È un filtro anti-falsi-positivi
sensato — senza, un nome di classe CSS farebbe scattare il gate — ma su queste quattro righe
gli unici altri token sono `color`, `label`, `signColor`, e il denaro esce lo stesso.

🔑 **L'unico consumatore visto sopravvive per i nomi delle variabili accanto.** `:1899`
passa perché `pnlColor` e `totalPnlVal` contengono `pnl` e `total`. Rinominando quella
variabile in `tpVal` gli hit del file passano da 2 a 1 — misurato replicando `scan()`:

```
PRIMA  [{line: 1834, form: B}, {line: 1899, form: B}]
DOPO   [{line: 1834, form: B}]
```

🔴 **E il gate non tace: diventa rosso. Che è peggio.** La voce registrata per `:1899`
smette di essere prodotta, quindi il test di marcio spara. Ma **nomina il colpevole
sbagliato** — punta alla voce di registro, non alla perdita di visibilità — e delle due
riparazioni ovvie:

| azione | esito |
|---|---|
| aggiornare lo snippet al testo nuovo | **ancora rosso**: quel testo non è più un hit |
| **cancellare la voce** | **verde**, consumatori visti a 0, nessuna traccia |

**L'unica risoluzione che il gate accetta è quella dannosa.** Chi segue il rosso in buona
fede arriva alla cancellazione perché è l'unica cosa che funziona. Per questo P4-11 non si
ripara allentando la regex: la soglia si sposterebbe e il meccanismo resterebbe.

> ⚠️ Il file produce **2** hit, non 1: `:1834`, la definizione, è essa stessa un hit ed è la
> prima voce del registro. «1 su 8» parla dei **consumatori** e va detto con quel sostantivo,
> o il prossimo lettore troverà due numeri veri che non tornano.

Le opzioni sono due, e vanno decise insieme: allentare la co-occorrenza accettando i falsi
positivi che ne derivano, oppure mascherare `fmtCurrency` **alla definizione** — una riga
sola a `:1834`, che coprirebbe tutti e otto i siti indipendentemente da come il gate li vede.
Dopo la misura sopra non è la migliore delle due: **è l'unica che sopravvive a un rename.**
È già registrata come `residual` nel gate.

### Contromisure di misura adottate nel round

- **N path in ⇒ `Test Files` deve dire N.** `vitest` con un path inesistente *da solo*
  esce con codice 1; **in compagnia di un path valido esegue quello e riporta verde**,
  senza una riga sui mancanti. Una suite può rimpicciolirsi in silenzio.
- **`git check-ignore -v`**, non la lettura del `.gitignore` ovvio: i file generati del
  frontend sono ignorati da **due** file diversi, e chi ne legge uno ne trova un terzo.
- **`git merge-tree --write-tree` + confronto blob** dice quali file una mano ha toccato
  in un merge. È cieco sui path in conflitto (il blob contiene i marker): lì si estraggono
  i due lati dal blob e si verifica che ogni **simbolo** sopravviva — non ogni riga, perché
  una risoluzione additiva *deve* fondere le righe.
