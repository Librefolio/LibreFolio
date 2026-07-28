# Step 6 — Risk Frontend Reconciliation & Functional Completion

**Stato**: 📋 PIANO RICONCILIATO — non implementare in questa esecuzione

**Data audit**: 28 Luglio 2026

← Step precedente:
[`plan-phase01Step5SimulationScaleOptimization.prompt.md`](./plan-phase01Step5SimulationScaleOptimization.prompt.md)

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

→ Gate finale: GF nel master implementativo.

## 1. Obiettivo

Chiudere G6 partendo dalla UI Risk **già materializzata**, senza riscriverla e senza
spostare matematica nel frontend.

Il lavoro futuro deve:

1. ricertificare le capability esistenti contro il contratto backend canonico;
2. correggere il placement Asset Detail;
3. eliminare fallback tecnici visibili come `#assetId`;
4. rendere espliciti i metadata MC/QMC;
5. aggiungere una UI funzionale minima per P13 `portfolio_optimization`;
6. completare mock E2E e smoke reali contro backend;
7. fermarsi prima di polish, gallery e design finale.

## 2. Non-obiettivi

- nessuna formula finanziaria nel frontend;
- nessun nuovo motore, endpoint o migrazione DB;
- nessun redesign visuale;
- nessuna ottimizzazione CSS o filling editoriale;
- nessuna snapshot visuale/gallery come gate;
- nessun selector Risk-specific se esiste già un controllo condiviso;
- nessuna normalizzazione arbitraria dei PCTR negativi;
- nessun fallback locale che mascheri capability/backend error.

## 3. Inventario reale al 28 Luglio 2026

Il vecchio piano descriveva G6 come non iniziato. L'audit del codice mostra invece:

| Superficie | Stato reale | Evidenza |
|---|---|---|
| client OpenAPI | ✅ generato e sincronizzato | `frontend/src/lib/api/generated.ts` |
| store Risk | ✅ presente | `frontend/src/lib/stores/risk.ts` |
| panel condiviso | ✅ presente | `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte` |
| heatmap correlazione | ✅ presente | `frontend/src/lib/components/risk/RiskCorrelationHeatmap.svelte` |
| Dashboard Risk | ✅ montato | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Broker Risk | ✅ montato | `frontend/src/routes/(app)/brokers/[id]/+page.svelte` |
| Asset Global correlation | ✅ montato in tab dedicata | `frontend/src/routes/(app)/assets/+page.svelte` |
| Asset Detail | ⚠️ panel presente, placement non conforme | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| rolling comparison selector | ✅ controllo condiviso già corretto | `frontend/src/lib/components/signals/SignalAssetParamControl.svelte` |
| simulation MC/QMC | ✅ funzionale | `RiskAnalysisPanel.svelte` |
| campi sequence canonici | ✅ compatibilità minima già corretta | `random_seed` / `sobol_start_index` |
| sync/quality | ✅ presenti | `PageSyncModal` + renderer qualità |
| UI P13 optimization | ❌ assente | nessun renderer/controllo |
| E2E mock Risk | ✅ 5 test desktop verdi | `frontend/e2e/portfolio/risk-analysis.spec.ts` |
| smoke E2E con backend reale | ❌ assente | nessun test Risk non-mocked dedicato |

## 4. Decisioni vincolanti

1. **Backend calcola, frontend presenta.**
2. Svelte 5 runes soltanto; nessun `$:` legacy.
3. Selectors e test usano `data-testid`, mai classi/testo localizzato.
4. `PageSyncModal` resta l'unico flusso sync prezzi/FX.
5. Catalogo e capability backend governano controlli e renderer disponibili.
6. `SignalAssetParamControl` resta il selector condiviso per comparison asset.
7. PCTR signed è corretto: contributi negativi rappresentano diversificazione.
8. MC usa `random_seed`; QMC usa `sobol_start_index`; mai un campo UI generico
   `seed`.
9. P13 è una **analisi descrittiva**, non una raccomandazione compra/vendi.
10. UI P13 minima: controlli, submit, stati, tabelle e metadata; design finale fuori
    scope.
11. Nessuna compatibility alias nuova nel frontend: il client usa solo il contratto
    canonico.
12. Il backend G0-G5 è baseline chiusa: una richiesta UI che richiede nuova
    matematica riapre il piano, non viene implementata localmente.

## 5. Sequenza di consegna

```text
G6.0 inventario/contratto
    ↓
G6.1 ricertifica capability esistenti
    ↓
G6.2 placement Asset Detail
    ↓
G6.3 label asset e metadata sequence
    ↓
G6.4 UI P13 minima
    ↓
G6.5 mock E2E + smoke backend reali
    ↓
G6.6 check/build/i18n/API sync idempotente
    ↓
GF
```

## 6. Task implementativi

### 6.0 — Congelare baseline e capability matrix

**Stato**: ✅ DOCUMENTATO DALL'AUDIT — ricertificare all'avvio G6.

**Obiettivo**: evitare di ricreare store, renderer o wiring già presenti.

**Gap**: il piano precedente non distingueva materiale esistente da lavoro mancante.

**File**:

- `frontend/src/lib/stores/risk.ts`
- `frontend/src/lib/components/risk/`
- quattro route Risk
- `frontend/e2e/portfolio/risk-analysis.spec.ts`

**Contratto/schema**: nessun cambio; leggere catalogo e discriminated union generati.

**Frontend**:

- mappare analytic id → scope → output kind → route;
- segnare capability già completa, parziale o assente;
- non creare componenti duplicati.

**Dipendenze**: G5 chiuso, API client sincronizzato.

**Test**: eseguire il test Risk E2E esistente come baseline.

**Migrazione**: nessuna.

**Criterio uscita**: matrice aggiornata nel piano prima della prima modifica G6.

**Rischio/fallback**: se catalogo e client divergono, fermarsi e correggere il
contratto/API sync; non hardcodare capability nel frontend.

### 6.1 — Ricertificare store, request key e stati

**Stato**: ⏳ DA ESEGUIRE IN G6.

**Obiettivo**: provare che lo store esistente gestisca il contratto completo senza
stato stale o collisioni tra scope/parametri.

**Gap**:

- store presente ma non auditato end-to-end dopo G5;
- nuovi campi simulation canonici devono partecipare alla request identity;
- output optimization non è ancora consumato.

**File**:

- `frontend/src/lib/stores/risk.ts`
- eventuali test store esistenti o nuovi test mirati.

**Contratto/schema**:

- request key include scope, asset/broker ids, date, currency, mode, analytic id e
  params canonici;
- nessun alias `sampling`, `paths`, `seed`;
- errori per analytic restano isolati.

**Service**: nessun cambio backend previsto.

**Frontend**:

- preservare loading/error/data per richiesta;
- invalidare su cambio sessione e mutazioni già previste;
- non duplicare la cache content-keyed backend.

**Test**:

- due request identiche deduplicate;
- parametri MC/QMC diversi non collidono;
- portfolio/broker/asset_set non collidono;
- errore di un analytic non cancella gli altri.

**Migrazione**: nessuna.

**Criterio uscita**: test store verdi e nessun cast `any`/schema locale duplicato.

**Rischio/fallback**: se il key builder non è riusabile, estrarre un helper typed;
non serializzare oggetti UI instabili.

### 6.2 — Spostare Asset Detail in “Risk & Scenarios”

**Stato**: ⏳ DA ESEGUIRE IN G6.

**Obiettivo**: conformare il placement approvato senza cambiare contenuto o design.

**Gap**: il panel Risk è montato dopo il blocco tecnico, non in una tab dedicata.

**File**:

- `frontend/src/routes/(app)/assets/[id]/+page.svelte`
- componenti tab già usati nella route;
- i18n EN/IT/FR/ES.

**Contratto/schema/service**: nessun cambio.

**Frontend**:

- aggiungere tab `Risk & Scenarios`;
- spostare, non duplicare, il panel esistente;
- mantenere lazy loading coerente con le altre tab;
- preservare comparison selector condiviso;
- nessun calcolo finanziario locale.

**Dipendenze**: 6.1.

**Test funzionali**:

- tab visibile;
- apertura tab monta il panel;
- cambio comparison asset produce payload corretto;
- stato unavailable/partial resta renderizzato.

**Migrazione**: nessuna.

**Criterio uscita**: una sola istanza del panel e nessun fetch Risk prima che serva,
se il pattern route corrente è lazy.

**Rischio/fallback**: se la route non supporta lazy tab senza refactor ampio,
preservare il fetch corrente ma correggere prima il placement; ottimizzare in un
task separato.

### 6.3 — Eliminare fallback `#assetId`

**Stato**: ⏳ DA ESEGUIRE IN G6.

**Obiettivo**: mostrare nomi/ticker reali in heatmap, PCTR, pesi e comparison.

**Gap**: alcuni renderer cadono su stringhe tecniche `#123`.

**File**:

- `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte`
- `frontend/src/lib/components/risk/RiskCorrelationHeatmap.svelte`
- store asset/helper label già esistenti.

**Contratto/schema/service**: nessun cambio API; usare gli id restituiti come chiave.

**Frontend**:

- caricare/riusare la mappa asset canonica;
- label primaria secondo convenzione esistente nome/ticker;
- se un asset è realmente irrisolvibile, mostrare una label localizzata
  “Asset non disponibile”, non l'id tecnico;
- id ammesso solo in attributi diagnostici/test, non nel testo utente.

**Dipendenze**: 6.1.

**Test**:

- label risolta per tutti gli asset fixture;
- asset mancante usa fallback localizzato;
- nessun testo visibile matcha `#\d+`.

**Migrazione**: nessuna.

**Criterio uscita**: nessun fallback tecnico nelle quattro route.

**Rischio/fallback**: non aggiungere fetch N+1; se la mappa non è caricata, usare il
bulk store esistente.

### 6.4 — Rendere espliciti i metadata MC/QMC

**Stato**: ⏳ DA ESEGUIRE IN G6; request controls già corretti.

**Obiettivo**: evitare che l'utente interpreti offset Sobol come random seed.

**Gap**:

- controlli request distinti già presenti;
- metadata/result devono mostrare la stessa semantica in modo verificabile.

**File**:

- `RiskAnalysisPanel.svelte`
- i18n EN/IT/FR/ES
- E2E Risk.

**Contratto/schema**:

- MC: `sampling_method=mc`, `path_count`, `random_seed`;
- QMC: `sampling_method=qmc`, `path_count`, `sobol_start_index`;
- il campo non applicabile è assente/null.

**Frontend**:

- label e help distinti;
- output metadata mostra solo il controllo applicabile;
- QMC spiega “indice iniziale sequenza Sobol”, non scrambling;
- nessun input generico `seed`.

**Dipendenze**: contratto G5 canonico.

**Test**:

- payload MC non contiene `sobol_start_index`;
- payload QMC non contiene `random_seed`;
- metadata renderizzato corrisponde alla request;
- switch metodo non conserva il campo incompatibile.

**Migrazione**: nessuna.

**Criterio uscita**: contratto UI/API univoco e testato.

**Rischio/fallback**: se il client generato non riflette i campi, rieseguire
`./dev.py api sync`; non aggiungere tipi manuali.

### 6.5 — Aggiungere UI P13 funzionale minima

**Stato**: ⏳ DA ESEGUIRE IN G6.

**Obiettivo**: rendere utilizzabile `portfolio_optimization` senza introdurre un
design definitivo.

**Gap**: analytic backend completo, nessun controllo o renderer frontend.

**Placement**:

| Route | Scope |
|---|---|
| Dashboard Risk | `portfolio` |
| Broker Risk | `broker` |
| Asset Global Risk | `asset_set` |
| Asset Detail | non disponibile: un solo asset non soddisfa P13 |

**File**:

- `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte`
- eventuale nuovo componente mirato sotto `frontend/src/lib/components/risk/`
- store Risk;
- route solo se il panel non riceve già lo scope;
- i18n EN/IT/FR/ES;
- E2E Risk.

**Contratto/schema**:

- analytic id `portfolio_optimization`;
- strategy `min_risk | max_sharpe | risk_parity`;
- covariance estimator `historical | ledoit_wolf | oas`;
- `risk_free_annual_rate` solo per max-Sharpe;
- `min_weight`, `max_weight`;
- `include_frontier`, `frontier_points`;
- `include_sensitivity`;
- solver soltanto da opzioni allowlisted pubblicate dal contratto/catalogo.

**Frontend**:

- controlli typed con default backend;
- submit esplicito per evitare job costosi ad ogni keystroke;
- loading, queue/backpressure, timeout, invalid params e unavailable distinti;
- tabella pesi ordinata;
- metriche return/volatility/Sharpe;
- contributi marginal/absolute/percentage;
- constraint summary e solver/status;
- frontiera e sensitivity solo se richieste;
- wording descrittivo: mai “compra”, “vendi”, “portafoglio consigliato”.

**Service**: nessuna matematica o post-processing finanziario. Il frontend può solo
ordinare/presentare i valori già prodotti.

**Dipendenze**: 6.1 e 6.3.

**Test funzionali**:

- capability gating per scope;
- tre strategie inviano payload corretto;
- risk-free compare solo con max-Sharpe;
- bound invalidi mostrano errore backend;
- frontier/sensitivity sono opzionali;
- pesi e contributi renderizzati con asset label;
- P13 non appare in Asset Detail;
- testo non contiene recommendation wording.

**Migrazione**: nessuna.

**Criterio uscita**: P13 eseguibile nei tre scope, output completo e nessuna formula
duplicata.

**Rischio/fallback**: se un renderer frontier richiede design non approvato, usare
una tabella funzionale dei punti; non bloccare G6 su un grafico finale.

### 6.6 — Ricertificare sync, qualità e capability gating

**Stato**: ⏳ DA ESEGUIRE IN G6.

**Obiettivo**: garantire che dati incompleti non producano una UI success-shaped.

**Gap**: componenti presenti, ma non ricertificati su tutti gli output dopo G5.

**File**:

- panel/quality renderer;
- `PageSyncModal`;
- route Risk;
- E2E.

**Contratto/schema**:

- `DataQualityReport` descrive sorgente;
- `RiskResultMetadata` descrive esecuzione;
- `partial`, `unavailable`, warnings ed excluded assets restano distinti.

**Frontend**:

- CTA sync apre `PageSyncModal`;
- dopo sync, refetch/invalidation usa pattern esistente;
- capability assente non mostra controlli morti;
- errore di un analytic non nasconde risultati validi degli altri.

**Test**:

- missing price/FX;
- partial con excluded asset;
- unavailable per storia insufficiente;
- sync modal open/close/refresh;
- bulk con un errore e un risultato valido.

**Migrazione**: nessuna.

**Criterio uscita**: nessuno stato degradato è mostrato come successo pieno.

**Rischio/fallback**: non inventare warning frontend; mostrare codici/messaggi
backend tramite mapping i18n esistente.

### 6.7 — Test funzionali mocked

**Stato**: ⏳ ESTENDERE SU BASE ESISTENTE.

**Obiettivo**: coprire comportamento, non estetica.

**File**:

- `frontend/e2e/portfolio/risk-analysis.spec.ts`
- eventuali fixture/helper E2E condivisi.

**Copertura minima**:

1. quattro placement route;
2. Asset Detail tab;
3. heatmap e label asset;
4. KPI/PCTR/stress/comparison/VaR;
5. MC e QMC con payload canonico;
6. optimization tre strategie;
7. frontier/sensitivity optional;
8. quality/sync/error isolation;
9. capability gating.

**Selectors**: solo `data-testid`.

**Test**: desktop funzionale; mobile solo se necessario per accessibilità funzionale,
non per polish.

**Migrazione**: nessuna.

**Criterio uscita**: suite deterministica, nessuna assertion su testo localizzato o
classi CSS.

**Rischio/fallback**: non ampliare un singolo test monolitico; separare scenari per
failure diagnosis.

### 6.8 — Smoke reali contro backend

**Stato**: ⏳ MANCANTE.

**Obiettivo**: provare wiring OpenAPI/store/backend senza route interception.

**Setup**:

- DB test popolato tramite `./dev.py test db populate --force`;
- server test via `./dev.py`;
- utenti E2E esistenti;
- nessun mock `/api/v1/risk/*`.

**Smoke minimi**:

1. Dashboard/Broker: caricare catalogo + almeno un analytic storico reale;
2. simulation oppure optimization: inviare un job piccolo e osservare output reale.

**File**:

- nuovo spec Risk real-backend oppure suite smoke esistente appropriata;
- nessun helper che bypassi l'API pubblica.

**Contratto/schema/service**: usare solo client/endpoint reali.

**Test**:

- auth;
- request/response validation;
- rendering output;
- worker spawn;
- errore esplicito se fixture dati insufficiente.

**Migrazione**: nessuna.

**Criterio uscita**: almeno due smoke verdi senza interception Risk.

**Rischio/fallback**: se la fixture non ha storico sufficiente, correggere il
popolamento test o scegliere asset fixture valido; non trasformare lo smoke in mock.

### 6.9 — Validazione G6 e GF

**Stato**: ⏳ DA ESEGUIRE DOPO 6.0-6.8.

**Comandi**:

```bash
./dev.py api sync
./dev.py api sync
./dev.py front format --check
./dev.py front check
./dev.py front build
./dev.py i18n audit
./dev.py test e2e --project chromium --grep "Risk Analysis"
```

Usare il comando E2E reale definito dal test runner per gli smoke non-mocked.

**Criteri**:

- secondo API sync senza diff;
- zero errori/warning Svelte;
- build verde;
- i18n EN/IT/FR/ES completa;
- mock E2E e smoke reali verdi;
- nessuna migrazione;
- nessuna modifica matematica frontend;
- Docker finale verde se il bundle cambia.

## 7. Gate G6

- [ ] baseline/capability matrix ricertificata;
- [ ] store e request identity testati;
- [ ] Asset Detail in tab `Risk & Scenarios`;
- [ ] nessun fallback visibile `#assetId`;
- [ ] metadata MC/QMC canonici e distinti;
- [ ] P13 funzionale nei tre scope;
- [ ] quality/sync/error isolation ricertificati;
- [ ] mock E2E estesi;
- [ ] almeno due smoke real-backend;
- [ ] API sync idempotente;
- [ ] format/check/build/i18n verdi;
- [ ] nessun design/polish fuori scope.

## 8. Stop condition

G6 si ferma e richiede una nuova decisione se:

- la UI richiede una nuova formula o aggregazione finanziaria;
- serve cambiare il contratto backend G0-G5;
- P13 richiede un recommendation layer;
- il design definitivo diventa prerequisito del renderer funzionale;
- emerge una migrazione DB.

## 9. Progress rule

Dopo **ogni** task:

1. segnare stato e data;
2. aggiungere `> **Note implementazione**: ...`;
3. aggiungere `> **⚠️ Fuori pista**: ...` per deviazioni;
4. aggiornare il master;
5. non iniziare il task successivo prima di aver registrato l'esito.

## 10. Stato corrente

Questo documento è solo il piano riconciliato richiesto dall'audit. Nessuna attività
6.1-6.9 è stata implementata in questa esecuzione. Le sole modifiche frontend
effettuate durante la remediation G5 sono quelle strettamente necessarie a mantenere
compatibilità con il contratto simulation canonico e i relativi test.
