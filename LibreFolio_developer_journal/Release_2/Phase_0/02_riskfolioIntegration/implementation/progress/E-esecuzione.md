# E — Esecuzione: i quattro livelli su Dashboard e Broker Detail

**Mandato**: [`../E-frontend-quattro-livelli.md`](../E-frontend-quattro-livelli.md) (sola lettura)
**Worktree**: `e-alfy-vigilant-adventure` · **Baseline**: `cc33120ebfbc61efe4c6178218ff8d64dd4adf47`
**Lane**: porta `6244` · data dir `backend/data/test-risk-e`
**Autorizzato**: 18 Set 2026 dal coordinatore sotto delega permanente del developer.

---

## Verdetti ricevuti prima di cominciare

| # | Questione | Verdetto |
|---|---|---|
| 1 | Quattro consumatori di `RiskAnalysisPanel` | **E1 approvato**: controller headless + due composizioni |
| 2 | Gate dei `DocsLink` | **Il gate vede i `DocsLink`**: lo scope 1c di `dev.py` esiste nel worktree di I, non nella mia baseline. I 18 slug faranno salire il contatore. Baseline 24 |
| 3 | L3, Sharpe o Sortino | **Entrambi**: Sortino primario, Sharpe secondario, mai come «voto». Vince `05` §9.1 sulla DoD del brief |
| 4 | Scatter rischio-rendimento §7.5 | **Fuori dalla v1**: nessun contratto produce vol/rendimento per singolo asset |
| 5 | Facciata `primitives.ts` | **Approvata** |

> ⚠️ **Tre volte in un giorno la mia baseline era vecchia** (contratti, D85-D92, riparazione di
> `dev.py`). Causa unica: il coordinatore non può committare. Regola operativa che ne deriva:
> **una verifica sul codice resta il metodo giusto, ma il suo esito va datato**. Se una cosa
> non c'è, la domanda giusta è «non c'è, o non è ancora arrivata qui?».

### Vincoli aggiuntivi del coordinatore

- `AssetRiskScenariosView.svelte` (Asset Detail, parcheggiato) e `AssetSetRiskPanel.svelte`
  (di **F**) si toccano **solo** per puntare al pannello ridotto, **a resa invariata**.
- Il controller headless è **anche** la mitigazione del trabocchetto
  `discard-the-answer-not-the-question`: spezzare in quattro pannelli moltiplicherebbe per
  quattro le occasioni di reintrodurlo.
- `resultFor` dovrà servire anche `drawdown`: aggiungere l'analytic senza aggiornare il mock
  **non fa fallire i test** — il pannello mostra «non disponibile» e la rete lo accetta.

---

## K9 — contratto verso F, ricevuto e corretto in corso d'opera

`allowedStressMethods?: RiskStressMethod[]`, additiva, default «tutti» → resa invariata per
Dashboard, Broker Detail e Asset Detail. Vive nel **pannello ridotto al solo markup**.

**Quello che il contratto non diceva, e che ho misurato**: il replay storico non è gated
solo su `supportsStress`. Ha un **secondo cancello interno**:

| Riga | Cosa |
|---:|---|
| `:927` | `{#if supportsStress}` apre |
| `:928-1066` | shock ipotetico |
| **`:1068`** | **`{#if scope.kind === 'asset'}`** |
| `:1069-1161` | replay storico, tutto dentro |
| `:653` | `if (scope.kind !== 'asset') return;` in `runReplay()` |

Quindi oggi, per `asset_set`, il pannello mostra **lo shock e non il replay** — l'inverso di
ciò che serve a F. `allowedStressMethods` da sola le avrebbe dato **una sezione vuota**.
K9 corretto dal coordinatore: *separare i due metodi **e** allargare il replay a `asset_set`*.

**Approvato**: per `asset_set` il replay si rende **senza i controlli proxy/esclusione**
(`proxyAssets: []`, `excludedAssetIds: []`). `buildHistoricalReplayParameters` prende già
array, quindi **non si tocca**. Condizione vincolante del coordinatore: **l'audit del replay
va mostrato**, non taciuto — senza i controlli è il sistema a scegliere al posto dell'utente,
quindi deve dichiarare cosa ha scelto.

**Le KpiCard in valuta sono tre, non due** (`:997`, `:1016` nello shock, `:1128` nel replay).
Le prime due spariscono da sole con lo shock. Resta una rimozione vera. E si **toglie la
resa**, non si nasconde il trattino: nascondere lascerebbe in piedi la falla latente il
giorno in cui `service.py` popolasse `asset_values`.

---

## K1 — consegnato da A, verificato in OpenAPI

`return_bins` + `var_bin_edge` su `RiskVarCvarOutput`; `underwater_series` su
`RiskDrawdownOutput`. Additivi, non `required`.

- **`var_bin_edge == -value_at_risk`, esattamente.** `value_at_risk` è una magnitudine
  positiva; i bin vivono in spazio di rendimento con segno. È il ponte fra le due convenzioni.
- Bin contigui, ordinati, larghezze uniformi, ancoraggio esatto → l'area rossa è **un numero
  intero di barre**. Nessun sort lato client.
- **La coda non è il 5% tondo**: misurata 37/750 = 4,93 %. Non asserirlo.
- Serie che ha solo guadagnato → `value_at_risk == 0.0`, taglio fuori dai dati, **banda rossa
  vuota**: non è un bug.
- `underwater_series` allineata 1:1 con `dates`, `drawdown <= 0`. Nessuno sfasamento.
- `drawdown_summary` → **1.1.0**, così «serie piatta» si distingue da «server che precede il
  campo».

⚠️ **Non ancora innestabile qui**: il mio backend è alla baseline e non ha quei campi.
Disegno lasciando il posto, e quando arrivano aggiorno **anche `resultFor`**.

---

## Passi

### ✅ Passo 0 — Aprire il piano vivo — *18 Set 2026*

> **Note implementazione**: creato questo file. Recepiti i cinque verdetti. Baseline
> riconfermata `cc33120eb`, albero pulito prima di cominciare.

---

### ✅ Passo 2 — Controller headless `riskPanelController.svelte.ts` — *18 Set 2026*

*(Il passo 1, divisione degli spec, è di D e arriverà come innesto: non lo eseguo.)*

**Rete di sicurezza scelta**: finché la divisione di D non arriva, il file unico
`e2e/portfolio/risk-analysis.spec.ts` (817 righe, 6 test) copre **tutti e quattro** i
consumatori — Dashboard, Broker, Asset Global e Asset Detail. È la miglior prova di non
regressione disponibile durante l'estrazione, migliore di quella che avrò dopo la divisione.

> **Note implementazione**: creati
> `frontend/src/lib/stores/risk/riskPanelController.svelte.ts` (~400 righe),
> `frontend/src/lib/stores/risk/riskPanelController.test.ts` (10 test),
> `frontend/src/__tests__/runes.svelte.ts` (nuovo, additivo) e il selettore
> `front-portfolio risk-controller-unit` in `scripts/test_runner/_frontend_portfolio.py`
> (aggiunta additiva; la lista `all` è derivata dal registro, quindi si aggiorna da sé).
>
> Il seme del controller è `applyBaseSignature`, che **registra chi era in volo prima di
> azzerare** e poi rilancia esattamente quelli. `registerLauncher` è la presa a cui ogni
> composizione attacca il proprio rilancio: chi non registra nulla, nulla si vede
> rilanciare — che è quello che serve a un L4 chiuso.

#### Evidenza, comandi esatti

| Comando | Esito |
|---|---|
| `git rev-parse HEAD` | `cc33120eb…`, albero pulito |
| `dev.py api sync` | client rigenerato (`generated.ts` è gitignored e **mancava**) |
| `dev.py front check` | **0 errori**, 41 avvisi in 2 file (preesistenti, `GlobalSettingsTab`) |
| `dev.py test --test-port 6244 --data-dir backend/data/test-risk-e front-portfolio risk-controller-unit` | **10 passed** |

#### Tre prove per costruzione, perché «verde» non è evidenza

1. **Il gate vede davvero il mio file.** Iniettato di proposito
   `const __gateProbe: number = "not a number"` → `svelte-check found 1 error … in 3 files`,
   citando `riskPanelController.svelte.ts:416`. Ripristinato. Un «0 errori» da un gate cieco
   non vale niente, e in questa campagna ne abbiamo già trovato uno.
2. **Il test prende il difetto se torna.** Rimossa la riga
   `for (const analysis of rerun) void launchers.get(analysis)?.();` → **1 failed, 9 passed**,
   con `expected "vi.fn()" to be called 2 times, but got 1 times`. Ripristinata. Il test
   fallisce *per la ragione giusta*, non per un effetto collaterale.
3. **La guardia jsdom non è decorativa.** Tolta la prima riga
   `// @vitest-environment jsdom` → tutti e 10 rossi, con il messaggio esplicito di
   `assertEffectsRun()`. Ripristinata.

> **⚠️ Fuori pista — il ritrovamento che vale oltre questo mandato.**
> Sotto vitest le rune in un `.svelte.ts` funzionano **solo** con
> `// @vitest-environment jsdom`. In ambiente `node` — il default di `vitest.config.ts`
> per i ~190 test esistenti — il file **compila bene** (il transform emette
> `$.derived(...)`: verificato aprendo un server Vite e stampando il modulo trasformato),
> ma a runtime `$state` reagisce, **`$derived` resta stantio** ed **`$effect` non parte mai**.
>
> Misurato su un file usa-e-getta poi cancellato: `node` → `p.n` 1 ✅, `p.doubled` **0** ❌,
> effetti **mai**; `jsdom` → 2 test su 2 verdi.
>
> **Perché è grave**: un'asserzione *negativa* — «l'effetto non è ripartito», «la
> fisarmonica riaperta non rifà la fetch» — in `node` **passa a vuoto**. È lo stesso
> difetto del mock stantio in un terzo vestito: non una forma vecchia, un **ambiente**
> vecchio. E riguarda proprio le asserzioni che difendono il controller.
>
> Probabile causa dello shim `Object.defineProperty(globalThis, '$state', …)` in testa a
> `riskStore.test.ts`: qualcuno ha aggirato il sintomo senza trovarne la causa.
>
> Si risolve con **una riga di commento nel proprio test**: `vitest.config.ts` non si tocca.
> Riportato al coordinatore, che lo diffonde a D, F e G.

> **⚠️ Fuori pista — `generated.ts` mancava.** È gitignored, quindi un worktree fresco non
> ce l'ha e *qualunque* gate frontend sarebbe fallito. Risolto con `api sync` (che esporta
> lo schema importando l'app: nessun server, nessuna porta, compatibile con la lane).
> **Ma il client così generato non contiene K1**: il mio backend è alla baseline e
> `grep -rn "return_bins\|var_bin_edge\|underwater_series" backend/app/schemas/risk.py`
> non trova nulla. Il lavoro di A è nel worktree di A. Disegno lasciando il posto.

---

### ✅ Passo 3 — Ricablare il pannello legacy sul controller — *18 Set 2026*

**Strategia scelta**: sostituire solo le *scritture*; ogni *lettura* conserva il vecchio
identificatore attraverso un alias `$derived` di sola lettura. Così le ~700 righe di markup e
tutte le derivazioni a valle restano **byte per byte identiche**, e la rete E2E misura
l'estrazione e nient'altro.

> **Note implementazione**: `RiskAnalysisPanel.svelte` **1 271 → 1 068 righe**.
> Rimossi: il blocco di stato del controller, i due `$effect` (firma e refresh), `loadBase`,
> `runSingle`, il corpo delle quattro esecuzioni su richiesta, `handleSynced`, il wrapper
> morto `buildBaseAnalytics`, e sei import ormai inutili.
> Aggiunti al controller `resetAnalysis()` e l'opzione `scenarioCatalogLoaded`, perché
> l'originale rialimentava gli editor degli scenari nel `finally` del catalogo.

#### Evidenza, comandi esatti

| Comando | Esito |
|---|---|
| `dev.py front check` (dopo lo script di ricablaggio) | 2 errori — `RiskMode`/`RiskQueryRequest` orfani nel wrapper morto |
| `dev.py front check` (wrapper rimosso) | **0 errori**, 42 avvisi — uno **nuovo** e vero |
| `dev.py front check` (dopo la correzione) | **0 errori, 41 avvisi in 2 file** = esattamente la baseline |
| `… front-portfolio risk` (pannello ricablato, 1º tentativo) | **6 failed** |
| `… front-portfolio risk` (pannello originale ripristinato) | **6 passed** ← baseline stabilita |
| `… front-portfolio risk` (dopo la correzione) | **6 passed** in 13,8 s |
| `… front-portfolio risk-controller-unit` | **11 passed** |
| `lsof -nP -iTCP:6244 -sTCP:LISTEN` | libera |

> **⚠️ Fuori pista — il ricablaggio ha rotto tutti e sei i test, e la diagnosi non somigliava
> alla causa.**
>
> Sintomo: `dashboard-risk-tab` **non trovato**, `broker-risk-tab` non trovato,
> `asset-detail-risk-panel` non visibile. Cioè spariva **la pagina**, non il pannello — e io
> avevo toccato solo il pannello.
>
> **Prima mossa, prima di qualunque ipotesi**: ripristinare il file originale e rimisurare.
> 6 verdi. Quindi la regressione era mia, e la rete funzionava. Senza quel passaggio avrei
> potuto passare ore a sospettare il database, la lane o il build.
>
> **Causa**: la factory leggeva `inputs()` **subito**, dentro
> `let lastRefreshVersion = untrack(() => inputs().refreshVersion)`. Ma la factory gira mentre
> lo `<script>` del componente ospite sta ancora eseguendo, e la closure legge
> `appliedRiskFreePercent`, che in `RiskAnalysisPanel` è dichiarata **più in basso**. In
> Svelte 5 uno `$state` compila in un `let`, quindi è **temporal dead zone**: `ReferenceError`.
> E un `ReferenceError` durante l'inizializzazione di un componente non si vede come «pannello
> rotto», ma come **pagina che non si monta**.
>
> **Correzione scelta**: non spostare la creazione del controller sotto le dichiarazioni —
> sarebbe stata una toppa che lascia la trappola armata per il prossimo chiamante. Il
> controller ora **non tocca i suoi input finché non parte il primo effetto**
> (`lastRefreshVersion: number | null = null`, seminato dall'effetto stesso). Un controller
> che esplode a seconda dell'ordine di dichiarazione di chi lo usa è un difetto del
> controller, non del chiamante.
>
> Aggiunto il test che l'avrebbe preso: *«does not touch its inputs while the host script is
> still running»*, che conta le letture della closure durante la costruzione e pretende **0**.
> Verificato per mutazione: rimettendo la lettura eager → **1 failed, 10 passed**.

> **⚠️ Fuori pista — due PNG non miei.** `git status` mostra come non tracciati
> `mkdocs_src/docs/static/icons/asset-types/commodity.png` e `real-estate.png`. Non li ho
> creati e non li tocco. Segnalati al coordinatore, **non messi in stage**.

### ⏳ Passo 4 — `RiskLevelsPanel`, contenitore e mappa dei livelli

### ⏳ Passo 5 — L1 «Quanto può fare male?»

### ⏳ Passo 6 — L2 «Sono diversificato come credo?»

### ⏳ Passo 7 — L3 «Sto venendo pagato per questo rischio?»

### ⏳ Passo 8 — L4 «Cosa succede se…?», chiuso di default

### ⏳ Passo 9 — Rimozioni (TE, IR, `sobol_start_index`, barre a mano)

### ⏳ Passo 10 — Innesti K1, K3, K4, K6, K7, K8

### ⏳ Passo 11 — Gate finali e porta libera

---

## Passi 4–7 — il contenitore unico e i quattro livelli ✅ 2026-09-18

> **Nota implementazione**: nati `components/risk/levels/`: `RiskLevelsPanel.svelte` (118),
> `RiskLevelSection.svelte` (84), `L1HowMuchItHurts.svelte` (124), `L2Diversification.svelte` (103),
> `L3RiskAdjusted.svelte` (84), `L4WhatIf.svelte` (60), `levelHelpers.ts` (243),
> `levelHelpers.test.ts` (185). **Nessun file supera le 600 righe**; il massimo è 243.
> Dashboard e Broker Detail montano **lo stesso** `RiskLevelsPanel`, con la sola differenza di `scope`.

### Comandi e esiti

| Comando | Esito |
|---|---|
| `dev.py front check` | **0 errori, 41 avvisi in 2 file** = baseline esatta |
| `… front-utility core-unit buildBaseAnalytics` | **12 passed** (8 preesistenti + 4 nuovi) |
| `… front-portfolio risk-levels-unit` | **28 passed** |
| `… front-portfolio risk` | **6 passed** in 13,5 s |

### ⚠️ Fuori pista 1 — l'analytic si chiama `drawdown_summary`, non `drawdown`

Il mio controller cercava `resultByCode(historicalResults, 'drawdown')`. Il plugin è
`drawdown_summary` (`analytic_code = "drawdown_summary"`, scope `ASSET` + `PORTFOLIO`,
modo `HISTORICAL`, versione 1.0.0 alla mia baseline). Con il codice sbagliato L1 non
avrebbe trovato nulla **e nessun test sarebbe stato rosso**: avrebbe solo mostrato
«non disponibile». Corretto.

### ⚠️ Fuori pista 2 — la rete di Asset Detail mi ha preso a distanza, e aveva ragione

`risk-analysis.spec.ts:819` asserisce un **Set esatto** di analytic code per lo scope
asset. Aggiungere `drawdown_summary` a `buildBaseAnalytics` — helper condiviso da tutti
gli scope — **cambiava ciò che Asset Detail mette sul filo**, senza che nessuno toccasse
Asset Detail. Adattare quell'asserzione era vietato, e giustamente: è l'unica prova che
la superficie parcheggiata è rimasta ferma.

**Correzione**: `includeDrawdownSummary` **opt-in per call site**, mai default — è la
lezione già in wiki (`shared-component-option-changed-globally.md`). Solo la
composizione a livelli lo accende.

**Prova per costruzione** — rimesso il default e rieseguito:
- unit: **2 failed** (`expected [...] to not include 'drawdown_summary'`);
- E2E: **1 failed, 5 passed**, test 6, diff `+ "drawdown_summary"`.
Ripristinato → **6 passed**.

### ⚠️ Fuori pista 3 — `front-utility core-unit <filtro>` dà PASSED con zero test

Primo tentativo: `… core-unit riskAnalysisHelpers` → `Test Files 80 skipped`,
`Tests 1947 skipped`, `tests 0ms`, **`✅ PASSED`**. `-t` è un pattern sul **nome del
test**, non sul file: un filtro sbagliato esce 0 e rassicura. Il filtro giusto è il nome
del `describe` (`buildBaseAnalytics` → 12 passed).

### ⚠️ Fuori pista 4 — `numberRecord` scarta tutto ciò che non è numero

Lo avevo usato per leggere l'output: avrebbe **silenziosamente** azzerato `items` (array)
e `current_peak_date` (stringa). Sostituito con un `record()` locale che non scarta nulla.

### Decisioni prese, e da cosa discendono

1. **`historical_var` a 21 giorni è una seconda richiesta, non un √21.** `05` §9.1 e il
   mandato §5 dicono che *nulla in L1 è stimato*. Il backend compone finestre reali
   sovrapposte (`horizon_compounded_returns`), quindi la riga «mese storto» è un fatto
   osservato. Costa una richiesta in più: `includeMonthlyVar`, anch'esso opt-in.
   Serve `resultByInstance`: due risultati condividono l'`analytic_code`, e
   `resultByCode` avrebbe etichettato una perdita mensile come giornaliera.
2. **Gli euro di L1 non vengono da nessun analytic.** Verificato: solo `stress` porta un
   `impact_amount`. Quindi `scopeValue` è una **prop** delle due pagine; quando manca, la
   colonna denaro **non compare**. Un euro inventato si legge come un euro misurato.
3. **CVaR principale, VaR secondario** (D4), e il VaR sparisce quando coincide col CVaR.
4. **Una riga assente non è una riga a zero**: un analytic fallito viene omesso.
5. **L4 chiuso, catalogo scenari al primo `onfirstopen`** — riaprire un accordion non è
   un cambio di domanda (`risk-g6-application-contracts.md`).
6. **Banner beta solo sul gradino simulazione**, non sulla sezione: un avviso ovunque non
   si legge da nessuna parte, e marchierebbe anche il replay, che è solo ciò che è successo.

### Ancora da fare

- L4: i tre gradini sono ordinati e intitolati, ma gli **editor** (preset shock a un clic,
  replay con audit, cono) sono ancora nel pannello legacy. Passo 8.
- Innesto dei due montaggi in Dashboard e Broker Detail (le pagine montano ancora il legacy).
- Passi 9-11: rimozioni, innesti K1/K3/K4/K8, cancelli finali.

---

## Passo 8b — anticipo di K4 da C: ordinamento della fetta ✅ 2026-09-18

> **Note implementazione**: C aggiungerà `asset_ids` a `PortfolioRiskScope` e ha chiesto a
> E di ordinarlo in `canonicalizeScope`. Fatto, ma **non come proposto**.

### ⚠️ Fuori pista 1 — lo snippet proposto lasciava scoperto proprio il caso Dashboard

Lo snippet del coordinatore presupponeva un `next` mutato in sequenza. Il codice reale
(`riskRequest.ts:79-86`) usa **return anticipati**, e il ramo portfolio era
**subordinato a `broker_ids`**. Mettere `asset_ids` lì dentro avrebbe lasciato non
canonicalizzato ogni scope `{kind:'portfolio', asset_ids:[…]}` privo di `broker_ids` —
**cioè esattamente ciò che monta la Dashboard** (`dashboard/+page.svelte:752`), mentre
Broker Detail i `broker_ids` li passa.

I due restringimenti ora sono **indipendenti**.

**Provato per mutazione**, non dichiarato: implementando lo snippet alla lettera,
`risk-unit` → `1 failed` (`expected [9,3] to deeply equal [3,9]`) e
`risk-controller-unit` → `2 failed`, di cui
`expected "vi.fn()" to be called 1 times, but got 2 times` — cioè la fetta riordinata che
riemette l'analisi. Ripristinato: 16 e 13 verdi.

### ⚠️ Fuori pista 2 — `baseSignature` usava lo scope grezzo

`riskPanelController.svelte.ts:91` serializzava `inputs.scope` tale e quale, mentre la
richiesta lo canonicalizzava (`riskRequest.ts:104`). Con `asset_ids` **dentro** lo scope,
l'ordine dell'array sarebbe diventato un innesco di invalidazione: la Dashboard costruisce
la lista da `[...new Set(holdings.map(…))]`, quindi l'ordine segue quello delle posizioni, e
un ricaricamento in ordine diverso avrebbe azzerato le quattro analisi on-demand.

Era `discard-the-answer-not-the-question` che rientrava dallo scope invece che dalle date.
La firma ora canonicalizza. **È il motivo per cui il controller esiste.**

### 🔴 Fuori pista 3 — il danno non è «una cache che raddoppia»: è un numero sbagliato

Scrivendo il test negativo (due fette diverse → due chiavi diverse) è **fallito**:
le due chiavi erano **identiche**.

Causa: `canonicalizeRiskRequest` termina con `schemas.RiskQueryRequest.parse(normalized)`
(`riskRequest.ts:122`), e **Zod scarta le chiavi sconosciute**. Finché `asset_ids` non
arriva nel client generato, il campo viene **tolto in silenzio** — non solo dalla chiave di
cache, ma **dal corpo della richiesta che va sul filo**, perché `buildRiskQueryRequest`
restituisce l'oggetto già validato.

> Quindi una UI che offrisse la fetta prima della rigenerazione del client mostrerebbe
> **i numeri del portafoglio intero sotto un'intestazione affettata**. Non una cache
> doppia: un numero sbagliato, servito con sicurezza.

Asimmetria da tenere a mente: **la firma vede la fetta, la richiesta no.** Il controller
rifarebbe correttamente la domanda al cambio di fetta, e manderebbe una richiesta non
affettata.

Registrato come **rilevatore dell'innesto**: il test asserisce oggi la collisione, con il
commento che dice cosa farne. **Diventa rosso il giorno in cui il campo atterra**, ed è
quello il momento di asserire l'invariante vera e togliere i cast.

### Superfici toccate

| File | Cosa |
|---|---|
| `riskRequest.ts` | `canonicalizeScope` **esportata**, rami indipendenti, lettura strutturale di `asset_ids` |
| `riskPanelController.svelte.ts` | `baseSignature` canonicalizza lo scope |
| `riskStore.test.ts` | +3 test (2 diretti su `canonicalizeScope`, 1 rilevatore del confine Zod) |
| `riskPanelController.test.ts` | +2 test (riordino non reinvia; identità della firma) |

### Evidenza

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** (baseline esatta) |
| `front-portfolio risk-unit` | **16 passed** (erano 13) |
| `front-portfolio risk-controller-unit` | **13 passed** (erano 11) |
| `front-portfolio risk` | **6 passed**, 19.6 s — rete di Asset Detail intatta |

### Aperto: `RiskReturnBasis` non può portare la dichiarazione K4

L'enum ha **esattamente due** valori, `PRICE_ONLY` e `TWRR` (`risk.py:41-43`). Un backtest
sulla composizione corrente non è né l'uno né l'altro. Se una corsa `HISTORICAL` affettata
continua a dichiarare `TWRR`, il frontend può solo **inferire** l'avviso da «la fetta è
attiva» — indovinare lato client una decisione presa lato server.

Serve un **terzo valore**. Chiesto a C tramite il coordinatore. Blocca solo l'avviso.

Nota: `return_basis` vive su `RiskResultMetadata` (`:461`), quindi su *ogni* risultato —
è il posto giusto, e `riskMetadata()` già lo legge.

### K6: due dei sei campi esistono già

`RiskSimulationOutput` ha già `drift_estimator` e `covariance_estimator`. Mancano davvero
`regime`, `regime_declared_days`, `regime_applied_days`, `block_length_days`,
`bootstrap_seed`. Due assunzioni si possono già rendere senza aspettare H.

---

## Passo 8c — K8 da N: la disciplina del segno e la coppia di L2 ✅ 2026-09-18

> **Note implementazione**: gli otto campi nuovi **non sono nella mia baseline** (verificato
> uno per uno: zero occorrenze in `schemas/risk.py`). Ho quindi costruito **la disciplina**
> che li reggerà, lasciando il posto ai campi. Tutto ciò che segue è già attivo sui campi
> che esistono oggi.

### Le quattro affermazioni di N, verificate

| Affermazione | Esito |
|---|---|
| `RiskKpiOutput.max_drawdown` è `le=0` | ✅ `:644` |
| `RiskVarCvarOutput.value_at_risk` è `ge=0` | ✅ `:823` |
| `cash_weight` assorbe gli asset esclusi | ✅ `service.py:631` — `max(0.0, 1.0 - sum(usable_weights.values()))`: è **il residuo**, quindi ci finisce dentro ogni titolo senza serie usabile |
| `risk.params.confidenceLevel` già nelle quattro lingue | ✅ EN/IT/FR/ES |

### ⚠️ Fuori pista 4 — avevo già il difetto che N descrive, in forma silenziosa

`buildHurtRows` normalizzava la profondità del drawdown con `Math.abs(depth)`. Sembra
equivalente a gestire il segno: non lo è. **`Math.abs` non legge una convenzione, la
scarta** — quindi un valore che *contraddice il proprio contratto* (un `le=0` che arriva
positivo) sarebbe stato reso come una perdita perfettamente plausibile.

Il server non può emetterlo, perché Pydantic applica il vincolo. **Una fixture sì**, e non
è validata da nessuno. È la stessa famiglia del mock stantio.

Introdotto `lossMagnitude(value, 'negative' | 'positive')`: la convenzione è **dichiarata
per campo, mai annusata dal valore**, e una contraddizione si legge come **assente** — che
L1 sa già rendere — invece che come un numero indistinguibile da uno vero.

**Provato per mutazione**: rimettendo `Math.abs`, `risk-levels-unit` → **3 failed**, fra cui
`expected 0.0385 to be null` e `expected [ 'day' ] to not include 'day'`. Ripristinato: 39 verdi.

### 🔒 L2: la coppia NEA + DR non è una raccomandazione, è un tipo

`buildConcentration` restituisce **entrambi i numeri o `null`**. Un chiamante non *può*
rendere il NEA da solo per distrazione.

Il motivo è quello misurato da N: dieci titoli equipesati danno NEA **10,00** con ρ 0, 0,5
o 0,95, mentre il DR fa **3,15 → 1,35 → 1,02**. Il NEA da solo **si complimenta con una
scommessa sola che indossa dieci nomi** — l'illusione esatta che L2 esiste per rompere.

**Provato per mutazione**: facendo restituire il NEA con DR mancante, → **2 failed**
(`expected { effectiveNumberOfAssets: 10, …(1) } to be null`). Ripristinato.

### 🔴 Fuori pista 5 — un'etichetta falsa già a schermo, non mia ma sulla mia superficie

`RiskAnalysisPanel.svelte:657` rende `risk.metrics.cashWeight` = **«Cash weight»**. Dato il
residuo verificato sopra, quell'etichetta è **falsa** su qualunque portafoglio con un
titolo non prezzabile: il lettore prende un **buco del modello** per una **scelta di
allocazione**.

Corretto il **valore** in tutte e quattro le lingue (chiave invariata, nessuna rimozione):

| | prima | dopo |
|---|---|---|
| EN | Cash weight | **Cash and uncovered** |
| IT | Peso liquidità | **Liquidità e non coperto** |
| FR | Poids des liquidités | **Liquidités et non couvert** |
| ES | Peso del efectivo | **Efectivo y no cubierto** |

Aggiunto `uncoveredWeight()` perché L2 legga lo stesso numero senza ripetere la bugia.

### `MDD` non è un campo nuovo

Preso atto: `max_drawdown` **è** `MDD_Rel`, verificato da N per costruzione. Uso quello;
nessuna richiesta di campo aggiuntivo da parte mia.

### Evidenza

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** |
| `front-portfolio risk-levels-unit` | **39 passed** (erano 28) |
| `front-portfolio risk` | **6 passed**, 13.3 s |

### Resta aperto

- I sei campi L1 e i due L2 si renderanno all'innesto: `lossMagnitude` li aspetta con la
  convenzione già dichiarata (`worst_realization`, `drawdown_at_risk`,
  `conditional_drawdown_at_risk` → `negative`; `ulcer_index` **non è una perdita**, è un
  indice `ge=0`, e non passa da `lossMagnitude`).
- `drawdown_confidence_level` riuserà `risk.params.confidenceLevel`: nessuna chiave nuova.

---

## Passo 8d — K3 da B: il benchmark condiviso di L3 ✅ 2026-09-18

### Verifiche

| Affermazione | Esito |
|---|---|
| `optionFilter.ts` toglie un titolo orfano da solo | ✅ verificato alla lettera: `kept.filter((o, i) => !o.header \|\| (kept[i+1] !== undefined && !kept[i+1].header))` |
| `AssetSelect` accetta `sections`/`restLabel` | ❌ **non nella mia baseline** (worktree di B) — atteso |
| `AssetInfo.is_benchmark` normalizzato in `assetStore.ts` | 🔴 **il campo non esiste da nessuna parte nel repo** |

### 🔴 Fuori pista 6 — `is_benchmark` non è una normalizzazione, è una catena

Cercato in backend (`app/`), nel client generato e in tutto `frontend/src`: **zero
occorrenze**. `AssetInfo` (`assetStore.ts:42-62`) non ha il campo.

Quindi il `match: (a) => a.is_benchmark === true` non dipende da una normalizzazione di B,
ma da una **catena**: colonna DB → migrazione → schema → `api sync` → normalizzazione. È
una dipendenza molto più lunga di quanto il relay lasciasse intendere, e va saputo prima di
pianificarci sopra il sezionamento del picker.

### La nota di coerenza è una domanda di persistenza, e ha una risposta

Oggi il benchmark è `comparisonAssetId = $state<number | undefined>(undefined)`
(`RiskAnalysisPanel.svelte:76`): **stato di componente**. Dashboard e Broker Detail montano
lo **stesso** componente, ma sono **due istanze**: due valori indipendenti, che si azzerano
a ogni mount.

Perciò la coerenza chiesta da D10 non si ottiene montando lo stesso componente — si ottiene
**togliendo la scelta dal componente**. Creato `riskBenchmarkStore.svelte.ts`: stato a
livello di modulo, quindi **una sola scelta per ogni scope**, con le tre discipline prese da
`chartSettingsStore` (guardia `browser`, chiave per utente, reset di sessione).

### ⚠️ Fuori pista 7 — la mutazione ha trovato un difetto **nel mio test**

Prima stesura: `// @vitest-environment jsdom` + `localStorage` reale. Fallita:
`Cannot read properties of undefined (reading 'clear')`. La casa non usa jsdom per questo —
`chartSettingsStore.test.ts` gira in `node` con `vi.mock('$app/environment', () => ({browser: true}))`
e un `localStorage` finto su `Map`. Il mock condiviso di `$app/environment` riporta
`browser: false`, quindi **senza quell'override ogni percorso di persistenza è un no-op**.

Poi, mutando la guardia sui valori corrotti, il test **è rimasto verde**. Causa: seminavo il
valore e ri-transitavo **sullo stesso utente**, quindi `hydratedKey === key` e lo store non
rileggeva mai. **Passava senza mai consultare la guardia.**

> Un test che non può fallire non è una rete: è un ornamento che somiglia a una rete.

Corretto seminando la chiave **prima** che l'account diventi corrente, e aggiunto il
controcanto positivo (un `42` valido dev'essere accettato, altrimenti «rifiuta tutto»
passerebbe lo stesso).

**Provato per mutazione, due volte**:
- chiave senza utente + guardia rimossa → `2 failed` (`expected 42 to be null`, cioè l'account successivo **ereditava** la scelta del precedente);
- solo guardia rimossa, **dopo** la correzione del test → `1 failed` (`expected +0 to be null`). Prima della correzione: **0 failed**.

### Evidenza

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** |
| `front-portfolio risk-benchmark-unit` (nuovo selettore) | **8 passed** |

### Resta aperto

- Il **sezionamento** del picker (prop `sections` di B) aspetta sia la prop sia il campo
  `is_benchmark`: il negozio del benchmark non ne dipende ed è già in piedi.
- Il picker in L3 si monta col passo 8 (editor), leggendo `riskBenchmark`.

---

## Passo 8a — L4, gradino 3: la provenienza della simulazione (K6) ✅ 2026-09-18

### 🔴 Fuori pista 8 — due «⚠️» del brief erano già fatte, e la terza era peggio del previsto

Controllati sul codice i due avvertimenti del brief su L4:

| Avvertimento del brief | Realtà |
|---|---|
| «oggi si chiede all'utente di riempire i bucket uno per uno» | ❌ **falso**: il preset esiste (`SimpleSelect` a `:733`, testid `risk-stress-preset`), se ne applica uno all'apertura (`global_risk_off`, `:393`) e i bucket sono già filtrati ai soli presenti + modificati (`stressVisibleBuckets :182`, con casella «mostra tutti» a `:765`). **Delta reale**: il dettaglio per bucket è sempre visibile, non «su richiesta». Molto più piccolo di quanto il brief lasci intendere. |
| «l'audit del replay va mostrato, non nascosto» | ❌ **già mostrato**, senza piegature, a `:927-948` (`risk-replay-audit`, conteggi proxy/esclusi, tre politiche, elenchi). **Delta: zero** — va solo portato nella nuova composizione. |

### 🔴 Il difetto vero era il terzo gradino, e nessuno lo aveva descritto

La simulazione rende `terminal_mean_return`, `terminal_volatility`, `probability_of_loss`,
il cono — e poi una riga chiamata **«assumptions»**:

> `risk.simulation.assumptions`: «{paths} paths over {days} days; current buy-and-hold
> composition, **without costs, cash flows, inflation or rebalancing**.»

I due numeri sono interpolati: sono **gli unici due che l'utente ha digitato lui**. Tutto
ciò che segue il punto e virgola è **scritto a mano nei quattro cataloghi**. E i campi che
lo direbbero davvero — `costs_included`, `cash_flows_included`, `inflation_included`,
`rebalanced`, `aggregation_policy`, `drift_estimator`, `covariance_estimator`,
`process`, `sampling_method` — **non vengono letti da nessuna parte** (verificato: gli
unici `simulationOutput.*` a schermo sono `:1039-1058`).

> La frase è vera **per coincidenza**. Il giorno in cui una corsa mettesse `rebalanced: true`,
> la UI continuerebbe a negarlo, in quattro lingue, senza un test che se ne accorga.
> **Un'assunzione scritta a mano non è una dichiarazione: è una congettura che per ora
> indovina.** Ed è peggio del silenzio, perché l'etichetta dice «assumptions» e il lettore
> crede di essere stato informato.

Quindi K6 non aggiunge campi a una provenienza esistente: **è la prima provenienza**.

### Cosa ho fatto

`levels/simulationProvenance.ts` (137 righe) + `SimulationProvenance.svelte` (89 righe).
Legge ogni campo **dal payload**, e in **entrambe le direzioni**: un effetto dichiarato
incluso è elencato fra gli inclusi, uno dichiarato escluso fra gli esclusi, e uno **di cui
il payload non parla non compare da nessuna parte** — perché un cono che non ha mai detto
se applica i costi non ha detto che non li applica.

Campi K6 (`regime`, `regime_declared_days`, `regime_applied_days`, `block_length_days`,
`bootstrap_seed`) letti già ora, tutti opzionali: **assenti, la resa è identica a oggi**.
Il regime si rende **solo insieme alla durata dichiarata** — un nome di regime da solo
ricostruirebbe esattamente l'ambiguità che il validatore di H esiste per vietare.
`drift_estimator` e `covariance_estimator` **esistono già** e non erano resi.

Esportati `record`/`finite`/`okOutput` da `levelHelpers` invece di riscriverli.

### Provato per mutazione (3 rossi mirati)

| Mutazione | Rosso |
|---|---|
| `stated === true/false` → `if (stated) … else …` | `expected ['costs','cashFlows',…(2)] to deeply equal ['cashFlows','inflation']` (assente letto come escluso) |
| idem | `expected ['costs','rebalancing'] to deeply equal []` — **la stringa `'false'` è veritiera**: letta larga, la frase si ribalta nel suo contrario |
| guardia regime → solo `regime !== null` | `expected { Object (key, value, …) } to be null` |

### Evidenza

| Comando | Esito |
|---|---|
| `front-portfolio risk-levels-unit` | **51 passed** (2 file; era 39) |
| `i18n audit` | **2815 chiavi, 2815 complete, 0 incomplete** |
| `front check` | **0 errori, 41 avvisi in 2 file** |

Chiavi nuove: `risk.levels.l4.provenance.*` in EN/IT/FR/ES. I valori enum ignoti
degradano al valore grezzo (`{default: value}`): un regime che il catalogo non conosce
non deve apparire come una chiave puntata, che somiglierebbe a un errore della pagina.

---

## Passo 8b — Il montaggio: una sola composizione su due pagine ✅ 2026-09-18

Dashboard (`(app)/dashboard/+page.svelte`) e Broker Detail (`(app)/brokers/[id]/+page.svelte`)
montano ora **lo stesso** `RiskLevelsPanel`, con le stesse prop e **un solo `scope` diverso**.
È la tesi centrale del mandato, ed è ora verificabile leggendo dieci righe in due file.

### 🔴 Fuori pista 9 — il valore dello scope non è il valore che la pagina ha in mano

L1 vuole mettere i soldi accanto alle percentuali. La Dashboard ha `summary`, quindi
sembrava ovvio passarne il patrimonio netto. **Non lo è**: `summary` viene da
`fetchReport(activeBrokerIds, …)` (`:378`), quindi **segue il filtro broker**, mentre lo
scope del rischio è `{kind:'portfolio'}` senza filtro — e il sottotitolo lo dichiara
(`risk.dashboardFullPortfolio`).

> Con un filtro attivo avrei stampato **i soldi di un broker accanto al rischio di tutti**.
> Non un errore visibile: un numero plausibile, sotto un titolo che dice un'altra cosa.

Quindi `scopeValue={brokerFilterActive || !summary ? null : …}`: l'importo **sparisce
esattamente quando mentirebbe**. Su Broker Detail `portfolioSummary` nasce da
`fetchReport([data.brokerId], …)` (`:262`), cioè **dallo stesso scope**, e si passa sempre.

### L'intestazione non poteva sparire: è stata estratta

I tre test rossi non dicevano «i test sono vecchi», dicevano **«la composizione è
incompleta»**: il pannello legacy porta in testa `RiskBetaBanner`, i pulsanti
`risk-sync-button` e `risk-refresh-button`, `risk-load-error`, il `DataQualityBanner` e
il `PageSyncModal` — funzioni vere, non decorazione. Estratte in
`levels/RiskPanelHeader.svelte` (115 righe) invece che copiate: *«queste quotazioni sono
vecchie di tre giorni ed ecco il pulsante»* è la stessa frase su ogni superficie di
rischio, e due copie di una frase sola sono il modo in cui due pagine cominciano a non
essere più d'accordo.

`RiskLevelsPanel` resta a **134 righe**. Nessun file del mandato supera le 600.

### 🔴🔴 Fuori pista 10 — il difetto peggiore l'ho scritto io, e i miei test lo confermavano

Delegato a `test-author` il ripristino dei tre test di portafoglio. Ha trovato un **bug di
prodotto mio**, non un problema di test:

`buildDivergenceRows` faceva `const contribution = percentage / 100;`.
Il backend (`services/risk/metrics.py:487`) calcola
`percentage = component / portfolio_volatility`, e `sum(component) = portfolio_volatility`
per decomposizione di Eulero: **è una frazione che somma a 1,0**, non un valore su cento.
Il pannello legacy infatti la rende con `formatPercent(row.percentage, true)` (`:667`),
cioè da frazione.

Effetto a schermo: una posizione che pesa il 60% e produce il 65% del rischio veniva resa
come **0,7% di contributo, con divergenza −59,4pp**. Ogni posizione appariva come
**riduttrice** di rischio, ogni barra puntava dalla parte sbagliata, e `leadDivergence`
(soglia +0,05) **non poteva più scattare**: la frase di sintesi di L2 non sarebbe mai
comparsa. Cioè il livello che esiste per smascherare la concentrazione avrebbe
rassicurato tutti.

> **E i miei 51 test unitari erano verdi.** Perché le *fixture* le avevo scritte io, con
> la stessa premessa sbagliata: valori 0-100 invece che frazioni. Un test scritto dalla
> stessa mano che ha scritto il difetto ne eredita il presupposto — e nessun vincolo di
> schema lo avrebbe fermato, perché `percentage_contribution` è solo
> `Optional[FiniteFloat]`, senza `le`/`ge`.
>
> È la ragione per cui questo difetto è stato trovato da un **E2E contro il payload reale**
> e non da uno unit test: l'E2E non poteva condividere la mia premessa.

Verificato da me su tre fonti indipendenti prima di accettare la correzione: la matematica
del backend, i test backend (`test_risk_api.py:454` asserisce somma 1,0) e la resa del
pannello spedito. Fixture riscalate a frazioni: **tutte le attese sono rimaste identiche**,
il che è la prova che codificavano lo stesso errore.

### 🔴 Fuori pista 11 — la divisione degli spec di D non è nella mia baseline

Il kickoff descriveva quattro file (`risk-mocks.ts`, `risk-analysis.spec.ts`,
`risk-lab.spec.ts`, `risk-asset-detail.spec.ts`) con proprietà distinte, e uno
«di nessuno» da non toccare. In questo worktree `ls frontend/e2e/portfolio/ | grep risk`
restituisce **un solo file**: `risk-analysis.spec.ts`. I quattro vivono nel worktree di D.

Conseguenza pratica: la rete che doveva dimostrare l'immobilità di Asset Detail **non
esisteva qui**, quindi è stata surrogata fissando i tre test d'asset **per checksum**
(3765/3765, 1282/1282, 6177/6177 caratteri, estratti da `git show HEAD:…`): sono passati
**senza essere stati toccati**.

### Evidenza (tutti i cancelli)

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** (identico alla baseline) |
| `front-portfolio risk-unit` | **16 passed** |
| `front-portfolio risk-controller-unit` | **13 passed** |
| `front-portfolio risk-levels-unit` | **51 passed** |
| `front-portfolio risk-benchmark-unit` | **8 passed** |
| `front-portfolio risk` (E2E) | **6 passed**, 13,1 s |
| `lsof -nP -iTCP:6244 -sTCP:LISTEN` | libera |

Mutazioni provate su `RiskPanelHeader`: testid del sync → `element(s) not found` su
`toBeEnabled`; `{#if subtitle || internalSubset}` → `{#if subtitle}` → `risk-scope-label`
invisibile sul broker. Ripristinate, di nuovo 6 passed.

### Debito aperto, dichiarato e non nascosto

1. **L4 è un guscio**: `<L4WhatIf />` è montato senza i tre snippet. Il caricamento pigro
   del catalogo scenari **funziona ed è provato** (una sola chiamata, alla prima apertura).
   Manca il contenuto: replay, shock, simulazione.
2. **I risultati `partial` spariscono**: `okOutput()` pretende `status === 'ok'`, quindi un
   contributo parziale svuota L2 invece di mostrare ciò che c'è.
3. **`warnings` non è reso da nessun livello**.
4. **L'indisponibilità per analitica è muta**: L1 omette il gradino invece di dire che la
   misura è fallita. L'omissione è meglio di uno zero, ma non è una comunicazione.
5. **`correlation` è richiesta per lo scope portafoglio e non resa**: un giro O(n²) sprecato.
6. **`HurtRow.secondaryLoss` è calcolato e mai reso.**
7. **Suggerimento**: `risk-scope-label` avrebbe bisogno di un `data-scope-label`
   leggibile a macchina, oggi il test deve leggere testo tradotto.

---

## Passo 8c — il parziale e la dichiarazione del degrado ✅ 2026-01-16

Chiusi i debiti **2** e **4**, che erano lo stesso difetto visto da due lati: il pannello
decideva cosa *non* dire.

**Debito 2 — `okOutput` rifiutava `partial`.** `service.py:736` restituisce `PARTIAL` per
qualunque avvertimento degradante, esclusione di contesto o qualità dati non OK: è lo
**stato ordinario** di un portafoglio con un titolo non prezzabile, non un caso esotico.
Pretendere `'ok'` svuotava **tutti e quattro** i livelli — e svuotava L2 esattamente nel
caso per cui L2 esiste, visto che `cash_weight` assorbe proprio quegli asset. Ora
`okOutput` accetta `'ok' | 'partial'` e continua a rifiutare `unavailable`/`failed`, che
per contratto non portano `output`.

**Debito 4 — l'indisponibilità era muta.** Aggiunto `degradedResults()` e la prop `health`
su `RiskLevelSection`: ogni livello dichiara le misure che non sono tornate intere, con il
loro stato. Il motivo non è la cortesia: **l'omissione non è comunicazione**. Un livello che
salta il gradino che non ha saputo calcolare mostra una lista più corta, e una lista più
corta è indistinguibile da un portafoglio che ha meno da dire. Solo uno dei due vale la
pena di riprovarlo.

> **Note implementazione**: `risk.states.{partial,unavailable,failed}` e
> `risk.analytics.{camelCase}.name` esistevano già in quattro lingue → **zero chiavi nuove**.
> I codici arrivano `snake_case` e il catalogo li tiene `camelCase`: conversione nel frame,
> con `{default: code}` perché un codice ignoto si legga com'è invece di stampare la chiave.

### 🔴 Fuori pista 12 — due difetti *nel mio stesso* codice appena scritto

La prima stesura di `l1Health` filtrava «tutto lo storico tranne `risk_comparison`».
Sembrava prudente. Era **una falsa accusa**:

- `correlation` viaggia nella stessa ondata storica (`riskPanelController:321`) ed è resa
  **da nessun livello** (debito 5). Il mock E2E la restituisce `partial` *sempre*
  (`low_pair_coverage`), quindi L1 avrebbe dichiarato in permanenza un guasto che il
  lettore non può vedere, non può verificare e non può correggere.
  → Il filtro ora è per **codice esplicito** (`historical_var`, `drawdown_summary`,
  `historical_kpi`), non per sottrazione.

- Peggio: `{#each health as entry (entry.code)}`. `analytic_code` **non è un'identità**.
  L1 chiede `historical_var` **due volte**, a un giorno e a un mese, distinte solo da
  `instance_id`. Due chiavi uguali in un `{#each}` keyed sono un **errore di runtime** di
  Svelte 5 — e sarebbero collise **esattamente quando entrambi gli orizzonti falliscono**,
  cioè nel caso per cui la dichiarazione esiste. Ora la chiave è `instance_id`.
  In più «Historical VaR: non disponibile» stampato due volte non dice *quale*: la voce
  porta ora una `label` opzionale, e L1 passa `risk.levels.l1.rows.{day,month}` — chiavi
  già tradotte, così la riga nomina **il gradino che manca** invece dell'analitica.

### Evidenza — mutazioni provate, non «verde»

| Mutazione | Esito |
|---|---|
| `degradedResults` deduplica per `analytic_code` | **1 failed** — `expected [ 'base-historical-historical_var' ] to deeply equal [ …(2) ]` |
| `labels[id] ?? Object.values(labels)[0]` (etichetta che tracima) | **1 failed** — `expected 'risk.levels.l1.rows.month' to be undefined` |

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** (identico alla baseline) |
| `front-portfolio risk-levels-unit` | **57 passed** (erano 51) |
| `front-portfolio risk` (E2E) | **6 passed**, 13,3 s |

### Debito che resta aperto dopo 8c

- **3** — `warnings` non è reso da nessun livello (lo **stato** ora sì, il *motivo* no).
- **5** — `correlation` richiesta e mai resa: ora non è più *mal attribuita*, ma resta un
  giro O(n²) sprecato per lo scope portafoglio.
- **6** — `HurtRow.secondaryLoss` calcolato e mai reso.
- **NUOVO 8** — la riga `{testId}-health` **è resa ma non asserita da nessun test**: l'E2E
  passa identico con e senza. Sarà chiesta a `test-author` insieme alle asserzioni di L4,
  per non spendere due passaggi di lane. Finché non c'è, il verde su quella riga è **vuoto**.

---

## Passo 8d — L4 innestato: i tre gradini rendono davvero ✅ 2026-01-23

> **Note implementazione**: i quattro componenti scritti nel passo 8 erano *scritti*, non
> *verificati*: mai type-checked, mai montati, con chiavi i18n inesistenti. Questo passo li
> chiude. `RiskLevelsPanel` passa i tre gradini come **snippet** a `L4WhatIf`, che li ordina
> per distanza dal dato (replay → shock → simulazione, l'avviso beta solo sull'ultimo).
> Il pannello resta a **163 righe**; il file più grande del mandato è il controller a **452**.

### Quattro scoperte, tutte contro qualcosa che avevo scritto io

**1. Le chiavi i18n della simulazione esistevano già, e non dove le cercavo.**
Stavo per aggiungere `risk.simulation.{horizonDays,paths,sampling,randomSeed}` in quattro
lingue. Il pannello legacy (`:966-1013`) le legge da **`risk.params.*`**, già tradotte.
Quattro chiavi nuove in quattro lingue sarebbero state **sedici stringhe doppione** — e,
peggio, due nomi diversi a schermo per lo stesso controllo fra vecchio e nuovo pannello.
Aggiunte solo le dieci chiavi davvero nuove: **2825 totali, 0 incomplete**.

**2. `error` non ha la forma che il mio codice assumeva.**
`generated.ts:7662` tipizza il campo `RiskError | Array<RiskError | null>`, mentre il
validatore Zod (`:14415`) ammette **solo** l'oggetto singolo e il backend dichiara
`Optional[RiskError]` (`schemas/risk.py:1045`). Il ramo array è quindi **irraggiungibile
oggi** — ma i miei test passavano solo perché le *mie* fixture usavano la forma singola:
è di nuovo il difetto della mano sola. Un cast avrebbe spento il compilatore lasciando la
bugia in piedi. C'è invece `firstError()`, che normalizza entrambe le forme in una riga.

**3. 🔴 Cinque avvisi `svelte-check` erano un bug di reattività, non rumore.**
`front check` è passato da 41 avvisi in 2 file a **46 in 5**. I cinque nuovi dicevano
*«This reference only captures the initial value»*. Non è cosmesi:

- `let start = $state(dateStart)` **congela** la finestra del replay al primo valore. Il
  lettore poteva **restringere il periodo nell'intestazione** e poi lanciare un replay sul
  periodo **vecchio**, con le date vecchie a schermo e nessun indizio che avessero smesso di
  essere quelle del pannello. Ora `startOverride ?? dateStart`: la finestra **segue** il
  pannello finché qualcuno non la sovrascrive, e il box resta editabile.
- `controller.registerLauncher(...)` a livello di modulo registra sul controller **iniziale**.
  Nel pannello legacy `controller` è una `const` locale, quindi non avvisava; nei miei è una
  **prop**. Avvolto in `$effect`, si ri-registra se l'identità cambia (`launchers.set` è
  idempotente, `riskPanelController.svelte.ts:281`).

Dopo le correzioni: **0 errori, 41 avvisi in 2 file** — di nuovo esattamente la baseline.
Gli avvisi non sono stati zittiti: sono **spariti perché la causa è stata tolta**.

**4. Il mock E2E serve `stress` in entrambi i metodi, ma mai un blocco.**
`resultFor` (`:378-470`) risponde al replay con `status: 'ok'` sempre. Quindi il ramo
`replayBlocker` — il pezzo di L4 che porta più giudizio — **non è esercitato da nessun
test E2E**, e non lo sarebbe nemmeno aprendo il livello. Va chiesto a `test-author`
come opzione **additiva** del mock.

### Evidenza — mutazioni provate, non «verde»

| Mutazione | Esito |
|---|---|
| `tornadoRows` ordina per `Math.abs` (l'ordinamento che lo schizzo §7.6 suggerirebbe) | **1 failed** — `expected [ 'UP', 'DOWN' ] to deeply equal [ 'DOWN', 'UP' ]` |
| `replayBlocker` accetta **qualunque** codice d'errore | **1 failed** — `expected { assetId: 42, …(2) } to be null` |

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** (baseline esatta) |
| `front-portfolio risk-levels-unit` | **73 passed** (3 file) |
| `front-portfolio risk` (E2E) | **6 passed**, 13,1 s |
| `i18n audit` | **2825 chiavi, 0 incomplete** |

### ⚠️ Il verde di questo passo è in parte vuoto, e va detto

L'E2E passa **identico a prima**, perché il livello 4 è **richiuso**: i sei test non lo
aprono mai. Quindi *«6 passed»* non dice nulla sui tre gradini appena innestati — né che
rendano, né che non esplodano al mount. È esattamente la forma di rassicurazione contro cui
questo mandato si è già scottato due volte. La copertura vera è delegata a `test-author`
nel passo 8e; **fino ad allora L4 è verificato solo dai 16 test di `scenarioHelpers`**,
cioè dalla logica, non dal rendering.

> **⚠️ Fuori pista 13**: avrei aggiunto sedici stringhe doppione se non avessi letto il
> pannello legacy prima di scrivere le chiavi. La regola «le chiavi esistenti prima delle
> chiavi nuove» ha appena pagato per la seconda volta in questo mandato.
>
> **⚠️ Fuori pista 14**: ho quasi trattato cinque avvisi `svelte-check` come rumore da
> baseline. Erano **due bug distinti**, uno dei quali (la finestra congelata) avrebbe
> prodotto un replay su un periodo diverso da quello mostrato — un numero sbagliato
> presentato come giusto, la categoria peggiore. **Un avviso nuovo in un file nuovo non è
> mai rumore: è l'unica cosa che il gate ha da dire su codice che nessun test tocca ancora.**

---

## Passo 8e — L4 finalmente *provato*, non solo montato ✅ 2026-01-23

> **Note implementazione**: delegato a `test-author` con la lane in esclusiva. Due test
> nuovi (7 e 8) e le asserzioni sulla riga di degrado infilate nei due test **non pinnati**.
> E2E da **6 a 8 passed**. I tre test pinnati (3, 5, 6) verificati **byte-identici per
> SHA-256 del corpo**, non a occhio.

### Cosa copre adesso il verde che prima non copriva

| Prima | Adesso |
|---|---|
| L4 mai aperto → i tre gradini mai renderizzati da nessun test | livello 4 espanso; ordine `observed → assumed → modelled` asserito via `data-distance`; avviso beta **solo** sul gradino modellato |
| catalogo scenari: una sola chiamata asserita, ma mai la **non**-richiesta | chiuso e riaperto: resta **1**, e la barriera è la pastiglia che riappare — quindi «ancora 1» significa *ricordato*, non *non ancora arrivato* |
| `replayBlocker`: 16 test di logica pura, zero rendering | il blocco **nomina** la partecipazione, offre il ramo azionabile (`data-proxy-at-fault="false"`), e l'esclusione **viaggia davvero**: richieste catturate `[[], [2]]` |
| `{testId}-health` reso e asserito da nulla | `data-count="2"` con entrambi gli orizzonti caduti, e **0** quando non cade niente |

### Evidenza — le due mutazioni che `test-author` ha guardato fallire

| Mutazione (sul **prodotto**, non sul test) | Esito |
|---|---|
| `degradedResults` deduplica per `analytic_code` — **il bug storico del passo 8c** | `Expected "2" · Received "1"`, con il DOM che stampa *una* voce di prosa perfettamente plausibile e il mese **sparito in silenzio** |
| `excluded_assets: []` in `buildHistoricalReplayParameters` — la UI ricorda, il filo no | `Expected [[], [2]] · Received [[]]` — **una sola richiesta**: il retry era identico al primo, quindi la cache di `queryRisk` se l'è mangiato e al server **non è arrivato nulla** |

> La seconda mutazione è più istruttiva della prima: il difetto non sarebbe apparso come un
> numero sbagliato ma come **un pulsante che non fa niente**, e il pannello avrebbe
> continuato a mostrare l'errore precedente — cioè avrebbe *sembrato* che il backend
> insistesse. Senza l'asserzione sulle richieste catturate, nessun test l'avrebbe visto.

### Quattro correzioni che `test-author` ha portato indietro

**1. §C non era fattibile senza toccare il prodotto.** La riga di degrado rende tutte le
voci in **un solo `<p>`** separate da `·`: «due voci, non una» non aveva **nessun segnale
nel DOM**, era leggibile solo dalla prosa tradotta — che non si asserisce. Aggiunto
`data-count={health.length}`, un attributo, zero markup, zero comportamento, nella
convenzione già usata qui (`risk-replay-audit` pubblica `data-proxy-count`).
*Resta vero che `data-count` non dice **quale** orizzonte manca: per quello servirebbero
nodi indirizzabili per voce. Annotato come debito, non fatto adesso.*

**2. I percorsi delle pagine nel mio piano erano stalli**: sono
`routes/(app)/dashboard/+page.svelte` e `routes/(app)/brokers/[id]/+page.svelte`.

**3. Le pastiglie shock non hanno il suffisso `-<id>`**: condividono un `data-testid` e si
distinguono per `data-preset-id`. Ancorate così.

**4. 🔴 La scelta dell'asset da bloccare era una trappola.** `matrixAssetIds[0] = 1` è la
riga per cui lo stub riporta un impatto: escludere **quella** avrebbe dato un totale
`0,00%` **indistinguibile da un replay che non ha fatto niente**. Bloccato l'asset **2**.
Un fixture distratto qui sarebbe stato verde dicendo il falso.

### Formattazione — il gate che nessuno stava guardando

`test-author` non poteva eseguire `front format --check` (una sola forma di comando in
lane). L'ho eseguito io: **7 file fuori formato, tutti miei**, nessuno suo — la sua
imitazione a mano della config ha retto. Riformattati **solo i sette file miei**, mai
l'albero, per non toccare file di altri mandati. Poi tutti i gate rieseguiti **dopo** la
riformattazione, perché formattare tocca file veri.

### Evidenza finale del passo

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** (baseline esatta) |
| `front format --check` | **All matched files use Prettier code style!** |
| `front-portfolio risk-unit` | 16 passed |
| `front-portfolio risk-controller-unit` | 13 passed |
| `front-portfolio risk-levels-unit` | **73 passed** (3 file) |
| `front-portfolio risk-benchmark-unit` | 8 passed |
| `front-portfolio risk` (E2E) | **8 passed**, 16,6 s |

Nessun file sorgente del mandato supera le **448** righe (il controller). Soglia 600 mai
avvicinata; `RiskLevelsPanel` è a **163**.

> **⚠️ Fuori pista 15**: `front format --check` non era nel mio giro di gate. Sette file
> fuori formato aspettavano da **otto passi**, e `front check` — verde tutto il tempo — non
> ne sa niente. È lo stesso genere di buco del gate di documentazione che un mandato
> fratello ha trovato: **un gate verde dice solo ciò che quel gate guarda**, e io avevo
> smesso di chiedermi cosa non guardasse.

---

## Passo 9 — Le rimozioni: tre su quattro sono **già fatte**, e farle davvero sarebbe una violazione ✅ 2026-01-23

> **Note implementazione**: nessuna riga rimossa, e **è il risultato giusto**. §6 del mandato
> elenca quattro sparizioni. Una era già stata ritirata dal coordinatore (D91). Le altre tre
> vivono **tutte e sole** in `RiskAnalysisPanel.svelte` — e quel file, dopo il passo 2, non
> è più montato da nessuna delle mie due pagine.

### La verifica che cambia la risposta

```
$ grep -rn "RiskAnalysisPanel" frontend/src --include=*.svelte
AssetRiskScenariosView.svelte:89   → routes/(app)/assets/[id]/+page.svelte   (Asset Detail)
AssetSetRiskPanel.svelte:167       → routes/(app)/assets/+page.svelte        (Risk Lab)
```

E §8 del mio stesso mandato dice, di entrambe:

> **Fuori**: `(app)/assets/+page.svelte` (mandato **F**) […]
> ⚠️ **Asset Detail è fuori** (**D8**, **D47**): si riapre dopo il rilascio, così eredita una
> grammatica già decisa.

**§6 e §8 si contraddicono.** §6 è stato scritto quando il pannello legacy serviva *anche*
Dashboard e Broker Detail; dal passo 2 non è più così, e la contraddizione è nata lì.

### Le quattro voci, una per una

| §6 dice che sparisce | Dov'è davvero | Verdetto |
|---|---|---|
| Tracking error e information ratio | `RiskAnalysisPanel:710-711`, **unico posto nel frontend** (`grep` su tutto `src/` + `e2e/`) | **già assente** dai quattro livelli: `RiskLevelsPanel` non li ha mai avuti. Toglierli dal legacy cambierebbe Asset Detail |
| Controllo `sobol_start_index` | `RiskAnalysisPanel:1013` | **già assente**: `L4Simulation:86` passa la costante `SOBOL_START_INDEX = 0`, nessun controllo a schermo |
| Barre divergenti scritte a mano | `RiskAnalysisPanel:659-670` (§6 dice `:854-870` — **numeri stalli**, il pannello si è accorciato di 203 righe al passo 2) | **già assente**: L2 disegna le sue, con `data-sign` e scala condivisa. E il rimpiazzo (`KpiDivergingFlowBar` esteso da D) **non è nella mia baseline** |
| Formattatore valuta doppione | `riskAnalysisHelpers.ts:130` | **ritirato dal coordinatore** (D91): non era un doppione |

> 🔑 **La rimozione era il fine, non il mezzo.** Il fine di D5 — non mostrare a un investitore
> privato l'aderenza a un mandato che non ha — è **raggiunto per costruzione** sulle mie due
> pagine: quei numeri non esistono nel componente nuovo. Cancellarli anche dal pannello
> legacy non aggiungerebbe niente allo scopo e **spenderebbe l'immobilità di Asset Detail**,
> che è precisamente la proprietà che i tre test pinnati esistono per dimostrare.

**Decisione**: non tocco `RiskAnalysisPanel.svelte`. Segnalato al coordinatore come
contraddizione del piano, non risolta di mia iniziativa: se il coordinatore decide che le
rimozioni valgono anche fuori scope, è una riga di richiesta e mezz'ora di lavoro — ma è
**una decisione sua**, perché consuma una garanzia data a un altro mandato.

> **⚠️ Fuori pista 16**: stavo per cancellare due `KpiCard` in due minuti. Il `grep` che ho
> fatto *prima* — «chi monta ancora questo pannello?» — è l'unica ragione per cui non l'ho
> fatto. **Una rimozione è irreversibile per chi legge la diff dopo**: cancellare è l'unica
> modifica che non lascia traccia di cosa c'era.

---

## Passo 9b — `k4-basis` sbloccato e chiuso ✅ 2026-01-23

Il coordinatore ha letto il valore nell'albero di C: `current_composition_backtest`,
impostato in un solo punto (`service.py:656`), nessun consumatore toccato.

**Confronto su stringa letterale, mai sul membro d'enum**: `RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST`
non esiste in questo albero, quindi importarlo **non compila**. Il filo ha sempre portato una
stringa. Così il confronto è **corretto oggi** (non combacia mai, l'avviso non compare, nulla
cambia) e **corretto dopo** l'integrazione, senza che nessuno debba tornarci.

Nessun cast è servito: `metadata` è letto via `record()` come `Record<string, unknown>`.

### Dove vive la dichiarazione, e perché non dentro L1

`backtestDeclared(results)` legge **tutta l'onda storica**, e l'avviso sta **sopra i quattro
livelli**, non dentro uno. Il `return_basis` è una proprietà della **serie** che ogni
analitica storica ha consumato: annunciarlo dentro L1 lascerebbe lo **Sharpe di L3** a
leggersi come se venisse da ciò che è successo davvero. La distinzione è la sostanza di K4:

> **TWRR** dice *com'è andata*. La ricomposizione pesata dice *come sarebbe andata la
> composizione di oggi*. **È un backtest, non un resoconto.**

### 🔴 Una conseguenza di K4 che nessuno aveva segnalato

`RiskResultFrame.svelte:108` rende **una chiave i18n dinamica**:

```svelte
{$t(`risk.returnBasis.${metadata.return_basis}`)}
```

Esistevano solo `price_only` e `twrr`. Quando C integra, quel frame avrebbe stampato a
schermo la **stringa grezza** `risk.returnBasis.current_composition_backtest`. Aggiunta la
chiave in quattro lingue: costa quattro stringhe, il namespace `risk` è mio (§8), ed è
additiva. *I miei livelli non usano `RiskResultFrame`, quindi il difetto sarebbe caduto su
Asset Detail e Risk Lab — pagine che non sono mie e che non avrebbero saputo perché.*

### Evidenza — mutazioni

| Mutazione | Esito |
|---|---|
| confronto sfocato (`.toLowerCase().includes('backtest')`) invece del letterale | **1 failed** — `expected true to be false` |
| ispeziona solo `results[0]` invece di tutta l'onda | **1 failed** — `expected false to be true` |

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** |
| `front format --check` | **All matched files use Prettier code style!** |
| `front-portfolio risk-levels-unit` | **78 passed** (erano 73) |
| `front-portfolio risk` (E2E) | **8 passed**, 16,6 s |
| `i18n audit` | **2827 chiavi, 0 incomplete**, unused invariato a 122 |

`RiskLevelsPanel` è a **182 righe**.

---

## Passo 10 — K3, il benchmark persistente di L3 ✅ 2026-09-01

> **Note implementazione**: creato `L3Benchmark.svelte`, montato in `RiskLevelsPanel`,
> chiave `risk.levels.l3.benchmark` in quattro lingue. La scelta vive nello store
> condiviso `riskBenchmarkStore`, **non** nel componente: è l'unica forma in cui
> Dashboard e Broker Detail possono restare confrontabili (**D10**). Estratto
> `comparedAssetId()` in `levelHelpers.ts` per renderlo verificabile fuori dal DOM.
>
> Lasciato il posto a **K3/B**: `sections` e `restLabel` sono additive e di default
> riproducono il comportamento di oggi, quindi la chiamata le acquisisce senza
> cambiare ciò che fa ora.

### ⚠️ Fuori pista 17 — un test che passava per il motivo sbagliato

La prima mutazione su `comparedAssetId` (leggere `output` ignorando `status`) è
**sopravvissuta**. Non perché il codice fosse indifferente, ma perché la mia fixture
legava `status: 'unavailable'` a `output: null`: leggere l'output direttamente dava
comunque `null`. **Il caso non distingueva i due comportamenti.**

Il caso portante è un risultato **fallito che porta ancora l'output vecchio** — ed è
reale: `okOutput` controlla lo stato *dopo* aver visto che l'output c'è, e quel secondo
controllo esiste proprio perché può esserci. Fixture riscritta con l'output **sempre
popolato**, due casi nuovi (`unavailable`, `failed`). Rieseguita la stessa mutazione:
`expected 7 to be null`.

> Una mutazione sopravvissuta non dice «il codice è ridondante». Dice **«il test non
> guarda dove credi»**.

### 🔴 Fuori pista 18 — il benchmark persistito non si calcolava mai a freddo

Segnalato da `test-author` misurando il filo: Broker Detail mostrava
`data-benchmark-id="9"` e **non mandava nessuna `comparison`**. Confermato sul codice:
`runSingle` (`:229`) ha `if (!hasRiskCapability(...)) return null` — **una guardia che
ritorna null in silenzio**. Il mio `$effect` lanciava nello stesso tick in cui leggeva
lo store, con `controller.catalog` ancora `null`, e `launched` era già scattato: nessun
ritentativo, mai.

A schermo: **il nome del benchmark sopra un trattino**. La persistenza faceva metà del
proprio lavoro e non lo diceva.

Corretto leggendo `controller.catalogState` **dentro** l'effetto — non per il valore, per
la *dipendenza*: così l'effetto rigira quando il catalogo atterra.

### 🔴 Fuori pista 19 — una scelta permanente trattata come una domanda estemporanea

`applyBaseSignature` → `discardOnDemand()` annulla ogni risultato on-demand e rilancia
**solo quelli in volo** (filtra su `isLoading`). Per uno stress chiuso è la policy
giusta, ed è **fissata da un test** (`does not re-issue an analysis that was not
running`). Ma un benchmark non è una domanda fatta una volta: è un **impostazione** che
il lettore si aspetta continui a valere.

E non è il caso limite ipotizzato (`dateFrom` che si assesta tardi su Broker Detail):
`applyBaseSignature` gira da un `$effect` su `inputs()` (`:342`), quindi **qualunque
cambio di periodo o di scope** ci passa. Restringi il periodo con un benchmark attivo e
il confronto spariva.

**Non ho toccato la policy del controller**: è corretta e pinnata. Aggiunto
`baseEpoch`, contatore reattivo **puramente additivo**, e `L3Benchmark` chiave il
proprio latch sull'epoca invece che su un booleano. Un booleano sbaglia in entrambe le
direzioni: non ri-armare mai lascia il nome sopra il trattino; ri-armare su «non c'è
risultato» **gira all'infinito** la prima volta che la risposta torna legittimamente
vuota. L'epoca chiede *una volta per movimento del terreno*.

### Evidenza — mutazioni

| Mutazione | Esito |
|---|---|
| `comparedAssetId` legge `output` ignorando `status` | **1 failed** — `expected 7 to be null` |
| `baseEpoch` non viene mai incrementato | **1 failed** — `expected 0 to be greater than 0` |
| `L3Benchmark` senza la guardia sul catalogo (codice pre-fix) | **1 failed** — `Expected: "9" / Received: ""` |

---

## Passo 10b — 🔴 Gli innesti K8/K1 sono impossibili oggi, e K4 non può accendersi

> **Note implementazione**: nessun codice scritto. Il criterio d'innesto del
> coordinatore — «costruisci dove entrambi i rami sono esercitabili oggi» — si è
> rivelato **strutturalmente insoddisfacibile** per ogni contratto che cambia la forma
> del payload. Misurato, non dedotto.

Il client è `validate: 'response'` (`zodios-client.ts:170`): **le risposte passano da
Zod**. Da lì escono due comportamenti opposti.

**Un campo nuovo viene cancellato in silenzio.** `RiskKpiOutput` (`:14230`) e
`RiskContributionOutput` (`:14249`) sono `z.object({...})` **senza `.passthrough()`** —
e il generatore ne emette 90 altrove, quindi *può*, semplicemente lì non l'ha fatto.
Passando allo schema reale i campi di N:

```
in:  … worst_realization: -0.0385, ulcer_index: 0.04
out: [ 'kind', 'max_drawdown', 'max_drawdown_duration_days', 'volatility' ]
```

**Una fixture E2E con i campi nuovi non esercita il ramo «presente»: lo esercita come
assente, e passa.** È il mock stantio del README `contracts/`, prodotto però dal client
invece che dal mock — quindi nessuno che aggiorni `resultFor` se ne accorgerebbe.

**Un valore di enum nuovo, invece, non viene cancellato: rifiuta tutta la risposta.**
`RiskReturnBasis = z.enum(['price_only', 'twrr'])` (`:11349`), e `return_basis` è
**obbligatorio** dentro `RiskResultMetadata` (`:11407`) e dentro `RiskDrawdownOutput`
(`:14388`). Su una risposta completa **e valida**:

| Risposta | `safeParse` |
|---|---|
| `return_basis: 'twrr'` | **OK** |
| `return_basis: 'current_composition_backtest'` | **FAIL** |

Il baseline passa, quindi il confronto significa qualcosa: **un solo valore di enum fa
fallire l'intera `RiskQueryResponse`** → `queryRisk` lancia → l'errore va in cache →
Dashboard, Broker Detail, Asset Detail e Risk Lab vanno **tutte** in stato di errore.

> Non è un campo che manca. È il pannello che si spegne — su quattro pagine, di cui due
> non sono mie.

### ⚠️ Fuori pista 20 — il mio innesto K4 poggiava su un presupposto falso, mio

Avevo accettato K4 scrivendo che «il filo porta una stringa semplice, nessun cast
serve». **Era falso: il filo è validato.** `backtestDeclared()` resta corretto e i suoi
test restano veri, ma il ramo **non può accendersi** finché `generated.ts` non conosce
il valore. Non è da rifare: è **in attesa di `api sync`**, esattamente come K8 e K1.

`api sync` rigenera `generated.ts`, che è **un file solo** e serve ad A, C, H e N
insieme. Chi lo lancia e prima di quale merge è una **decisione di campagna**: segnalata
al coordinatore, non presa da me. L'ordine però è vincolato — `api sync` deve atterrare
**prima** del backend di C, non dopo.

---

## Passo 11 — `warnings`: il *perché* accanto al *che cosa* ✅ 2026-09-18

> **Note implementazione**: autorizzato dal coordinatore come **unico innesto che il
> criterio corretto ammette oggi** — e per una ragione precisa: `warnings` è un campo
> **vecchio**, già presente in `RiskAnalyticResult` nello schema generato. Quindi Zod non
> lo cancella e una fixture che lo porta esercita davvero il ramo «presente». K1, K8 e
> il ramo di K4 restano in attesa **perché sono nuovi**; questo si può fare **perché è
> vecchio**.
>
> Aggiunto `resultReasons()` in `levelHelpers.ts`, la prop `reasons` su
> `RiskLevelSection`, e le tre derivazioni in `RiskLevelsPanel` — dalle **stesse fette**
> da cui nasce l'health corrispondente.

Fino a qui i livelli dicevano *che* una misura era incompleta e mai *perché*. I quattro
livelli esistono per rispondere a «posso fidarmi di questo numero?»: uno stato senza
causa lascia la domanda aperta **dichiarando di averla chiusa**.

### Due decisioni, ciascuna con la propria mutazione

**Niente viene filtrato su `degrades_result`.** Quel flag decide lo *stato*, che è già a
schermo, e non è sinonimo di «vale la pena leggerlo»: l'unico punto dell'albero che lo
mette a `false` (`stress.py:341`) segnala che i metadati di settore mancavano e l'asset
è stato trattato come «Other al 100%». **Il numero non è degradato — il significato di
uno shock settoriale calcolato così sì.** Filtrarlo nasconderebbe proprio la frase che
spiega la forma sullo schermo.

**Niente viene tradotto.** Sono stringhe del backend. Mapparle su chiavi i18n costruite
a runtime è esattamente il difetto trovato in `RiskResultFrame:108`. Verbatim, o nulla.

### ⚠️ Fuori pista 21 — `partial` non implica «c'è un warning»

`service.py:736`: una wave diventa `PARTIAL` per **quattro** cause — un warning che
degrada, `context_exclusions`, `computation.excluded_assets`, o `data_quality` non OK.
**Solo la prima è un warning.** Quindi filtrare su `degrades_result` e non mostrare
nulla quando l'insieme è vuoto avrebbe riprodotto il difetto proprio nei casi
probabilmente più frequenti. Un `partial` senza warning è **ordinario**, non un bug:
inventare una causa sarebbe peggio che non mostrarne.

### 🔴 Fuori pista 22 — l'E2E era verde su una UI che non raggiungeva mai

Dopo l'implementazione la suite diceva **10 passed**, e non significava niente: l'unico
warning del mock è attaccato a `correlation` (`:286`), e **nessun livello rende la
correlazione**. La funzione nuova non veniva mai eseguita.

> È la stessa famiglia del mock stantio, nella variante peggiore: non una fixture
> vecchia, ma **nessuna fixture** — e un verde che non copre nulla ha esattamente lo
> stesso aspetto di un verde che copre tutto.

Delegato a `test-author` con il vincolo di rendere l'opzione **opt-in**, così le fixture
esistenti restano byte-identiche. Ha trovato una trappola che la mia consegna non
prevedeva: **`resultFor` scrive `warnings` due volte** — in `base` e di nuovo nel ramo
`correlation`, che *sostituisce* l'array. Un'iniezione fatta in `base`, come suggeriva
la mia analogia con `replayBlockedAssetId`, sarebbe stata **accettata e scartata in
silenzio** per un analytic. Risolto applicandola al confine, in `installRiskMocks`.

Ha anche aggiunto **una seconda mutazione di propria iniziativa**, perché la prima si
fermava alla barriera di presenza e non arrivava mai alla pretesa sul conteggio.

### Evidenza — mutazioni

| Mutazione | Esito |
|---|---|
| `resultReasons` filtra su `degrades_result === false` | **1 failed** — `expected [] to deeply equal [ 'Treated as Other at 100%.' ]` |
| deduplica per `code` invece che per frase | **1 failed** — `expected [ {…} ] to have a length of 2 but got 1` |
| `RiskLevelsPanel` smette di passare `reasons` a L1 | **1 failed** — `getByTestId('risk-level-1-reasons') … element(s) not found` |
| `occurrences` non viene mai incrementato | **1 failed** — `Expected: "2" · Received: "1"` |

---

## Gate finali — 2026-09-18 · **FROZEN**

| Comando | Esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** — baseline esatta |
| `front format --check` | **All matched files use Prettier code style!** |
| `front-portfolio risk-unit` | **16 passed** |
| `front-portfolio risk-controller-unit` | **14 passed** |
| `front-portfolio risk-levels-unit` | **89 passed** (3 file) |
| `front-portfolio risk-benchmark-unit` | **8 passed** |
| `front-portfolio risk` (E2E) | **11 passed**, 21,5 s |
| `i18n audit` | **2828 chiavi, 0 incomplete**, unused invariato a 122 |
| `test check-orphans` | 78 spec E2E + 202 unit, tutti registrati e raggiungibili |
| `git diff --check` | pulito |
| `lsof -nP -iTCP:6244 -sTCP:LISTEN` | **exit 1** — nessun listener |

### Il vincolo numero uno del mandato

| File | Righe |
|---|---|
| `levelHelpers.ts` | 494 |
| `riskPanelController.svelte.ts` | 467 |
| `levelHelpers.test.ts` | 448 |
| **`RiskLevelsPanel.svelte`** | **206** |
| ogni componente L1-L4 | ≤ 208 |

**Nessun file supera 600.** E `RiskLevelsPanel` è **uno**: Dashboard e Broker Detail
montano lo stesso componente, distinti solo dallo scope. Il monolite da 1 271 righe non
è stato sostituito da un secondo monolite.

### Cosa resta in attesa, e perché non è un rimando di comodo

**K1, K8 e il ramo di K4** non sono innestabili oggi: Zod cancella i campi nuovi e
rifiuta i valori di enum nuovi, quindi nessuna fixture può esercitarne il ramo
«presente». Innestarli adesso significherebbe scrivere codice morto che **rassicura chi
legge il diff**. Atterreranno con `api sync` nell'albero che avrà il backend.

**K5** (primitive promosse da D) e **K7** (slug di documentazione da I) non mi sono mai
arrivati, in nessuna forma: il file `contracts/` del coordinatore contiene solo il
proprio README, e la sua tabella dà ⏳ anche ai contratti che ho già ricevuto per relay.
Non ho costruito contro una forma che non ho visto.

---

## Post-FROZEN — verifica della decisione «array vuoti» (2026-09-18)

Il coordinatore conferma dopo il congelamento: *«`proxyAssets: []`, `excludedAssetIds: []`,
con l'audit del backend mostrato — senza i controlli il sistema sceglie al posto
dell'utente, quindi deve dichiarare cosa ha scelto.»*

Ho verificato la decisione contro il codice **prima** di confermare che la rispetto.
**Non la rispetto alla lettera, e la lettera non è implementabile.**

### Tre fatti

1. **`RiskScenarioMissingHistoryPolicy` ha esattamente un valore**
   (`schemas/risk_scenarios.py:39-40`): `MANUAL_PROXY_OR_EXCLUDE`. **Non esiste una
   politica automatica.** Il sistema non può scegliere al posto dell'utente: non gli è
   stata data la facoltà.
2. **Senza scelte il backend non sceglie: rifiuta.** `risk_plugins/stress.py:452-466`
   itera sugli asset dello scope e al **primo** privo di serie utilizzabile solleva
   `RiskUnavailableError(INSUFFICIENT_HISTORY)` — messaggio letterale *«requires a manual
   proxy or explicit exclusion»*. Non degrada la risposta: **la nega per intero**.
3. **L'audit è uno specchio della richiesta, non una dichiarazione del sistema.**
   `risk/service.py:513`: `excluded_asset_ids = tuple(getattr(plan.params,
   "excluded_assets", ()))`. Il backend non aggiunge mai esclusioni proprie. Con gli array
   vuoti per sempre, l'audit direbbe stabilmente **«0 proxy, 0 esclusi, 0,0%»**: una frase
   vera, che non informa di nulla, appesa a un replay che non è mai partito.

### Cosa ho consegnato, e perché è la lettura giusta della decisione

- `proxyAssets: []` — **sempre**, nessun controllo di proxy. ✅ rispettata.
- `excludedAssetIds: []` — **alla prima richiesta**, che è la richiesta di cui parla la
  decisione. ✅ rispettata.
- L'audit del backend è reso (`risk-replay-audit`, con `proxy_count`, `excluded_count`,
  `excluded_weight_total`). ✅ rispettata. Il peso totale è l'unico dato che il client non
  potrebbe calcolarsi: lì l'audit guadagna il suo posto.
- In più: quando il backend **rifiuta**, il lettore può escludere quel singolo titolo e
  ritentare. È l'unica uscita che la politica unica del backend consente.

> Tenere `excludedAssetIds` vuoto **per sempre** significherebbe che su un portafoglio con
> un solo titolo non prezzabile il replay **non parte mai** — non degradato, assente, con
> un avviso ambra e nessuna via d'uscita. E il difetto avrebbe la forma che questa campagna
> ha già incontrato quattro volte: **una dichiarazione che non dichiara niente.**

Le esclusioni sono accumulate (`stress.py` rifiuta **un asset per volta**: tre titoli
illeggibili richiedono tre risposte), **visibili** come pastiglie e **reversibili**, e
azzerate quando cambia il periodo — perché una domanda nuova non può ereditare le risposte
della precedente.

**Nessuna modifica al codice**: la consegna era già conforme. Questa nota esiste perché la
decisione verrà propagata a F, e la sua motivazione — «il sistema sceglie» — è invertita
rispetto a ciò che il backend fa.

---

## Post-FROZEN — verifica di tre consegne (K5 p2, emendamento K8, `coverage`)

Il coordinatore chiede di segnalare **prima** di rifare. Verificate una per una: **nessuna
obbliga a cambiare L1/L2/L3.**

### 1. K5 parte 2 — non è nel mio albero

`ls frontend/src/lib/components/ui/display/` → `BrokerBadge`, `CompactCashCell`,
`CompactCashCell.test.ts`. `KpiMetricBar` e `KpiDivergingFlowBar` sono ancora in
`components/dashboard/`, `RiskMetricCard.svelte` **non esiste**. Stesso schema di K1, K3,
K6, K8: consegnato nel worktree del fratello, invisibile nel mio. **Adozione
post-integrazione.**

**La guardia `NaN` non mi tocca, ma per un motivo migliore di «non capita».** Le mie righe
sono filtrate **alla costruzione**: `buildDivergenceRows` scarta la riga se `finite()`
rifiuta `asset_id`, `weight` o `percentage_contribution`; `tornadoRows` fa lo stesso con
`toNumber()`, che controlla `Number.isFinite` **su entrambi i rami**, numero e stringa.
Nessun `NaN` può raggiungere una larghezza.

> ⚠️ E se ci arrivasse, il mio danno sarebbe **peggiore** di quello della dashboard: le due
> scale sono `Math.max(0.01, ...rows.map(...))` (`L2Diversification:36`) e
> `Math.max(...rows.map(...), Number.EPSILON)` (`TornadoChart:33`). **`Math.max` con un solo
> `NaN` nello spread restituisce `NaN`** → la scala si avvelena → **tutte** le barre del
> pannello conservano la larghezza precedente, non una. Filtrare al costruttore è il posto
> più forte della guardia alla barra: la barra difende sé stessa, il costruttore difende
> ogni consumatore.

**Non-salto**: oggi L2 e L3 hanno scheletri propri che occupano **le stesse celle di griglia**
del contenuto (`h-8` in L2, `h-16` in L3), quindi il salto non si presenta per un'altra
strada. La regola «fornire `caption`/`sparkline`/`submetrics` anche in `loading`» diventa
vincolante **quando** adotterò `RiskMetricCard`.

### 2. Emendamento K8 — NEA non è reso da nessuna parte

`buildConcentration` esiste ed è testata, ma **nessun `.svelte` la consuma** e il blocco i18n
`risk.levels.l2` non ha chiavi per NEA/DR. Il vincolo «mai da solo» è già **nel tipo**:
`Concentration` è un unico valore nullable con entrambi i campi, quindi un chiamante **non
può** renderne uno per sbaglio.

> ⚠️ Ma la mia stessa documentazione contiene la parola che l'emendamento dichiara falsa:
> *«Correlation-blind **count** of equally weighted equivalents»* (`levelHelpers.ts:433`).
> **Un conteggio non può superare il totale**, e con la cassa al denominatore supera:
> 11,44 su 2 posizioni. Chi cablerà il renderer leggerà quel commento.
> **Proposta al coordinatore** (non eseguita, sono `FROZEN`): correggere il commento a
> «indice di concentrazione» e aggiungere il requisito del peso di cassa accanto.

### 3. `coverage` — non lo rendo, ma è **vivo oggi dove la distorsione è massima**

`RiskResultMetadata.coverage` non compare in L1/L2/L3. L'unico `coverage` dei livelli è
`classification_coverage` in `L4Shock:148`, campo **diverso** (copertura di classificazione
settoriale) e mostrato **solo quando `< 1`**: mette in guardia, non rassicura.

🔴 **Ma**: `RiskResultFrame:99-100` rende `metadata.coverage`, e il suo **unico** consumatore
è il pannello legacy — la cui cornice KPI (`RiskAnalysisPanel:631`) avvolge **Sharpe**
(`:636`) e **Sortino** (`:637`). Il legacy serve gli scope `asset` e `asset_set`: **Asset
Detail (parcheggiato D8/D47) e il laboratorio di F** — cioè **il ramo titolo, quello a
distorsione massima**. Comportamento **preesistente**, preservato byte per byte di proposito.
L'avvertimento va instradato lì, non a me.

**Conseguenza per L3 — verificata assente.** `buildRiskAdjusted` prende `sortino`, `sharpe`,
`volatility` da `historical_kpi` (il portafoglio) e `beta` dal confronto: **non esiste una
card con il rapporto del benchmark**. Il solo numero relazionale è il beta, rapporto di
co-momenti in cui **un fattore di annualizzazione comune si cancella**. Non ho misurato
l'allineamento delle serie: affermo solo la cancellazione.

**La versione fra pagine non morde oggi**: il report TWRR **filtra per broker** (scoperta di
C su K4), quindi Dashboard e Broker Detail prendono **entrambe** il ramo TWRR, esatto.
Morderà quando atterrerà la fetta `asset_ids` di C — **lo stesso innesco della dichiarazione
di backtest che ho già scritto**. Una superficie, due avvisi.

### 4. Corroborazione meccanica della misura di A (non richiesta, ma nomina la riga)

`daily_risk_free_rate` (`metrics.py:140-144`) è `expm1(log1p(rate)/365)`: **il 365 è fisso e
non dipende da `annualization_factor`**. `annualized_sharpe:157` e `annualized_sortino:173`
lo sottraggono a ogni osservazione di una serie che, sul ramo titolo, ha ~252 punti l'anno:
si deducono **252 unità di rf invece di 365**. Sotto-deduzione → `excess_mean` gonfiato.

Tre conseguenze che coincidono con ciò che A ha misurato senza che io abbia visto i suoi
numeri: **proporzionale a rf** (quindi *esattamente* zero a rf = 0), **crescente con rf**
(2% → 5%), e **peggiore sul Sortino**, perché lo stesso errore al numeratore è diviso per una
`downside_deviation` più piccola della volatilità. Sul ramo TWRR la serie è giornaliera di
calendario, il 365 è corretto, e il delta sparisce.

> La misura di A dice **quanto**; questa dice **quale riga**. Sono complementari, e la
> seconda è falsificabile: se la cura tocca `√f` invece di `daily_risk_free_rate`,
> il delta a rf = 0 **non** resterebbe zero.

**Nessuna modifica al codice.** Unico file toccato: questo piano.

---

## Post-FROZEN — correzione K6 della didascalia, `format`, e `api sync`

### 1. La stringa da correggere **non esiste nel mio albero**, e non per fortuna

`grep "35" frontend/src/lib/i18n/en.json` → **zero**. In più:

- `risk.levels.l4.provenance.values` **non contiene alcuna etichetta di regime**: solo
  `gbm`, `mc`, `qmc`, `historical_log_mle`, `sample_log_returns`,
  `current_buy_and_hold`. Nessun nome di regime è mai stato scritto qui.
- `regimeValue` è **«{regime}, declared over {days} days»**: dichiara un'**ipotesi
  dichiarata**, non promette un risultato. È già la forma che la correzione impone.
- `valueLabel()` ha un fallback documentato `{default: value}`: un regime sconosciuto
  rende **il token del backend**, non una didascalia inventata da me.
- Le didascalie dei preset vengono dal **catalogo backend**
  (`equity_crash.yml`: *«Editable asset-class shocks centered on listed equity
  exposure»*). Il `-0.35` lì dentro è un **bucket shock predefinito**, cioè un **input
  modificabile**, non una promessa.
- La mia riga di risultato è `shockTotal`: *«This scenario would move the scope by
  {percent} {amount}»* — **riporta** il numero calcolato, non lo anticipa.

> ⚠️ **Ma la correzione individua una trappola che il mio fallback lascia aperta.** Il
> giorno in cui qualcuno aggiunge `provenance.values.crisis = "un calo del 35 %"`,
> reintroduce esattamente il difetto che H ha appena chiuso — e **nulla diventa rosso**,
> perché è la semplice aggiunta di una stringa.
>
> **Regola da registrare**: un'etichetta di regime nomina la **trasformazione**, mai
> l'**esito**. «moltiplica per 0,65», non «cala del 35 %».

### 2. `format` — il mio albero è pulito, verificato non assunto

`git diff --stat` → **13 file, tutti miei**. Nessun `schemas/*`, nessun file estraneo.
I quattro cataloghi i18n cambiano di **92 righe esatte ciascuno**: l'uguaglianza dei
quattro conteggi è essa stessa la prova che nessuna lingua è andata alla deriva.

### 3. 🔴 `api sync` nella mia lane **non rigenererebbe nulla di K6**

`grep "RiskSimulationRegime\|regime_declared_days\|bootstrap_seed"` su **il mio**
`backend/app/schemas/risk.py` → **zero occorrenze**. Presenti solo `drift_estimator` e
`covariance_estimator` (`:859-860`); assente anche `block_length_days`.

> `api sync` legge **la mia** OpenAPI, non quella di H. Girerebbe, uscirebbe verde e
> produrrebbe **zero tipi nuovi** — un successo apparente, che è la famiglia di difetto
> che questa campagna continua a incontrare. Identico a K1.

**Conseguenza onesta sullo stato di K6 da parte mia**: `SimulationProvenance` è
**costruita, testata unitariamente e cieca sul filo**. Zod cancella i campi assenti dallo
schema, quindi finché `api sync` non gira in un albero che **contiene il backend di H**,
il componente rende le voci che ha e **omette in silenzio** regime, seme e lunghezza del
blocco. I miei test passano perché costruiscono l'output direttamente, **scavalcando il
filo**.

> **Non contare K6 come reso** finché qualcuno non ha eseguito `api sync` **dopo** aver
> fuso H. Da parte mia: costruito, provato, **spento**.

---

## Post-FROZEN — due richieste di contratto a K1, finché la firma è ancora aperta

Il coordinatore avvisa che la firma di K1 **non è più a costo zero** (`historical_var`
2.0.0, `drawdown_summary` 1.1.0) e chiede di domandare **ora**. Verificato prima di
chiedere: `RiskDrawdownOutput` della **mia** baseline è già ricco — `current_drawdown`,
`current_peak_date`, `maximum_drawdown` con picco/valle/recupero, `remaining_to_peak_ratio`,
`available_start`, `available_end`, `n_observations`, `coverage`, `calculation_basis`,
`return_basis`.

**Domanda 1 — `underwater_series` porta una data per punto?**
`n_observations` e `available_start`/`available_end` esistono già, ma **non bastano**: le
osservazioni sono **giorni di borsa**, non di calendario. Con ~750 punti su ~1 095 giorni,
interpolare uniformemente fra inizio e fine **sbaglia ogni punto interno** — corretti solo
il primo e l'ultimo. Senza una data per punto il client deve **inventare** un fatto che il
server conosce: stessa famiglia della base di rendimento K4, che ho rifiutato di inferire.

**Domanda 2 — `var_bin_edge` è un indice o un valore?**
Se è un valore, marcare la barra del VaR obbliga a un confronto fra float sugli estremi dei
bin. Un indice è **non ambiguo**; un valore richiede una tolleranza, e una tolleranza
sbagliata evidenzia la barra sbagliata **senza fallire**.

### Una buona notizia sul costo, per costruzione e non per fortuna

`underwater_series` viaggia dentro l'output di `drawdown_summary`, che ho reso **opt-in**
(`includeDrawdownSummary`) per una ragione **diversa** — il difetto a distanza che faceva
chiedere l'analitica ad Asset Detail. Quindi i ~1 100 punti **sono già dietro un cancello**:
Asset Detail e il laboratorio di F non li pagheranno mai. La decisione presa per proteggere
una superficie parcheggiata contiene anche il costo di una serie non campionata.

### `drawdown` mai positivo — coincide con ciò che ho già scritto

Il validatore della mia baseline ha il ramo `no_drawdown`: `maximum_drawdown == 0` **e
nessuna data d'episodio**. `buildCurrentDrawdown` restituisce già `null` quando
`current_drawdown` è 0, ed è pinnato a `levelHelpers.test.ts:102`. Nessun caso «sopra il
livello dell'acqua» da gestire: **il contratto lo rende impossibile**, non improbabile.


---

# Innesto K9 — la guardia sugli importi (2026-09-18)

**Richiesta**: guardia `scope.kind === 'portfolio'` su **due** `formatAmount` (`:997`, `:1016`
nella numerazione di F).

## ⚠️ I siti sono TRE, non due

I numeri di F vengono dalla baseline; nel mio file riscritto sono `:794` e `:813`. Ma
`grep -n formatAmount` ne trova **un terzo**:

| riga | contesto | citato da F |
|---:|---|---|
| 794 | `stressOutput?.impact_amount` (KPI) | ✅ |
| 813 | `impact.impact_amount` (tabella) | ✅ |
| **925** | **`replayOutput?.impact_amount` (KPI del replay)** | ❌ **no** |

Stesso `formatAmount`, stessa cecità allo scope. Coprire due su tre avrebbe fatto **passare
lo spec di F lasciando la regola bucata**: peggio del rosso, perché trasforma una domanda
aperta in una risposta falsa.

## La correzione: una guardia, non tre

La guardia sta **dentro** `formatAmount` → `formatScopedCurrencyAmount`
(`riskAnalysisHelpers.ts:149-167`). Un solo punto, immune al quarto sito — che è
esattamente il modo in cui questo difetto è arrivato a tre.
Ritorna `'—'`, **la stessa stringa** che `formatCurrencyAmount` già rende su `null`:
per questo non muove un pixel oggi.

## Prova per mutazione

| | comando | esito |
|---|---|---|
| con guardia | `front-utility core-unit` | **1951 passed** (baseline 1947 + 4) |
| **senza** guardia | idem | **`2 failed`** — `expected '$1,234.50' to be '—'` |
| ripristinata | idem | **1951 passed** |

Il quarto test (`null` su scope portfolio → `—`) esiste per l'**altra** direzione: una
guardia che azzerasse *ogni* scope passerebbe i primi due e svuoterebbe gli importi della
dashboard il giorno in cui il backend li calcola.

> **⚠️ Fuori pista — ho eseguito il selettore sbagliato.** Prima corsa su `risk-unit`:
> **16 passed**, identico al conteggio *precedente* ai miei quattro test. `risk-unit` è il
> **riskStore**; `riskAnalysisHelpers.test.ts` è registrato sotto **`front-utility core-unit`**
> (`_frontend_utility.py:68`). Il banner diceva `PASSED` e non misurava nulla di mio.
> È la regola «guarda il conteggio, non il banner» applicata a me stesso: il conteggio
> **non si è mosso** ed è l'unica cosa che l'ha rivelato.

## Cancelli

`front check` **0 errori / 41 avvisi in 2 file** (baseline esatta) · `front format --check`
pulito · `front-portfolio risk` **11 passed** · 13 file modificati (invariato) · 6244 libera.

---

# Correzione K6 §9 — e un difetto MIO che la correzione fa emergere (2026-09-18)

## Verificato nella mia baseline

| Affermazione | Esito |
|---|---|
| l'errore non è 422 ma `200 OK` + `unavailable` | ✅ `service.py:143-150`, `continue` — **presente nella mia baseline**, non in un altro albero |
| `INVALID_PARAMETERS` nell'enum | ✅ `schemas/risk.py:99` |
| `process`/`regime` senza `x-control-order` → non sono controlli utente | ✅ e **non ho alcun selettore**: zero occorrenze di `block_bootstrap`/`process` nei livelli |
| un renderer che assumesse contiguità degli ordini | ✅ **non è mio**: unico consumatore `charts/signals/schemaMapper.ts:107`, che usa l'ordine come **chiave di ordinamento** con fallback `?? sourceIndex` — le posizioni 1 e 2 vacanti non lo toccano |
| `drift_estimator`/`covariance_estimator` già presenti | ✅ già rilevato da me al §4 dell'innesto precedente |

**Quindi il 422 non mi riguarda**: non scrivo il selettore, e lo schema dice che non devo.

## 🔴 Ma la frase di H è vera nel mio codice, e per cause che NON richiedono il selettore

> «Un rosso sarebbe stato più gentile di un vuoto.»

`okOutput` (`levelHelpers.ts:44-48`) ritorna `null` per ogni stato diverso da `ok`/`partial`.
E i tre gradini di L4 rendono **solo** su `output`:

| gradino | riga | su `unavailable` |
|---|---|---|
| `L4Simulation` | `:129` `{#if output}` | **vuoto assoluto** |
| `L4Shock` | `:138` `{#if output}` | **vuoto assoluto** |
| `L4Replay` | `:161` `{#if blocker}` | messaggio **solo** per `insufficient_history`/`invalid_parameters` **con `details.asset_id`**; ogni altra causa → vuoto |

E la sezione L4 (`RiskLevelsPanel:192`) è **l'unica delle quattro senza `health` né `reasons`**:
L1, L2, L3 li passano (`:176 :180 :184`), L4 no.

> **Il difetto è raggiungibile oggi**, senza alcun selettore: worker occupato, timeout,
> storia insufficiente. Il lettore preme «esegui», il caricamento finisce, e **non compare
> nulla** — né risultato né causa.

**La mia stessa motivazione conteneva l'errore.** Il docstring di `replayBlocker` dice:
*«un timeout o un worker occupato non sono domande a cui il lettore può rispondere, e
offrirgli un bottone "risolvi" sarebbe una bugia su chi ha il controllo.»* Vero sul
**bottone** — ma ho fatto discendere da «nessuna azione» anche «nessun messaggio».
**Un timeout non è una domanda, ma è pur sempre qualcosa che va detto.**

## Correzione proposta (≈3 righe, nessuna chiave i18n nuova)

```svelte
let l4Health  = $derived(degradedResults([controller.replayResult, controller.shockResult, controller.simulationResult]));
let l4Reasons = $derived(resultReasons([controller.replayResult, controller.shockResult, controller.simulationResult]));
<RiskLevelSection level={4} … health={l4Health} reasons={l4Reasons}>
```

`degradedResults` è già null-safe (provato a `levelHelpers.test.ts:294`, che passa `null`
nell'array), quindi prima che il lettore chieda qualcosa L4 resta muto — corretto: non c'è
nulla da riferire. `risk.states.*` esiste già (`RiskLevelSection:109`). Nessun bottone
aggiunto: si nomina il gradino e il suo stato, senza promettere un rimedio.

⚠️ **Non implementato**: sono `FROZEN` e questo non era nella richiesta. In attesa del
coordinatore, **con la nota che una prova credibile richiede un mock che risponda
`unavailable`** — oggi nessuno lo fa, quindi il cablaggio da solo passerebbe verde senza
essere misurato.

---

# L4 · disclosure dello stato + commento NEA — AUTORIZZATO ed ESEGUITO (2026-09-18)

## Cosa è cambiato

| File | Cosa |
|---|---|
| `levels/RiskLevelsPanel.svelte` | `l4Results` / `l4Health` / `l4Reasons`, passati alla sezione 4 |
| `e2e/portfolio/risk-analysis.spec.ts` | opzione **additiva** `unavailableSimulation` + 1 test nuovo |
| `levels/levelHelpers.ts` | commento NEA: da «count» a **indice di concentrazione** |

**Nessuna chiave i18n nuova** (2828 invariate): `risk.states.*` esisteva già.
**Nessun bottone**: si nomina il gradino e il suo stato, senza promettere un rimedio.

## ⚠️ Verifica preventiva che poteva far fallire tutto in silenzio

`risk.states.${entry.status}` è **anch'essa una chiave composta a runtime**. Se
`unavailable` fosse mancata, il cablaggio nuovo avrebbe stampato **la chiave grezza**,
in quattro lingue, senza che alcun cancello lo rilevasse — lo stesso difetto D150 che il
coordinatore mi segnalava per `returnBasis`, riprodotto **dalla correzione stessa**.

Controllato prima di scrivere: `partial`, `unavailable`, `failed` presenti in **en/it/fr/es**.
`ok` **manca ed è corretto**: `degradedResults` emette solo i tre stati degradati.

> E `risk.returnBasis.current_composition_backtest` **c'era già in tutte e quattro le
> lingue** — l'avevo aggiunta durante l'innesto K4, perché avevo già identificato
> `RiskResultFrame:108` come chiave dinamica. L'adempimento era assolto prima di essere
> richiesto. Idem i due estimatori K6: `simulationProvenance.ts:101-102`.

## Prova per mutazione — la spesa che il coordinatore ha autorizzato

| | comando | esito |
|---|---|---|
| cablato | `front-portfolio risk` | **12 passed** |
| **scablato** (`health`/`reasons` rimossi) | idem | **`1 failed, 11 passed`** — `expect(locator).toBeVisible() failed` su `risk-level-4-health`, riga 1469 |
| ripristinato | idem | **12 passed** |

Il rosso cade **solo** sul test nuovo: la fixture è opt-in e gli altri 11 non si muovono —
additività dimostrata dallo stesso rosso che dimostra il cablaggio.

## Cancelli

`front check` **0 errori / 41 avvisi in 2 file** · `front format --check` pulito ·
`risk-levels-unit` **89 passed** · `front-portfolio risk` **12 passed** ·
`check-orphans` 78 / 202 / 206 tutti raggiungibili · i18n **2828** per lingua.

---

# Verifica del giro C — tutto già consegnato (2026-09-18, nessun codice scritto)

| Richiesta | Stato nel mio albero |
|---|---|
| §3(b) quattro traduzioni `returnBasis` | ✅ **già presenti**, dall'innesto K4 (`*.json:2976`) |
| §3(a) `api sync` | ❌ **non eseguibile**: `RiskReturnBasis` nel mio backend ha **due** valori (`schemas/risk.py:42-43`) |
| §4 `Cash and uncovered` | ✅ **già consegnato** in quattro lingue (`cashWeight`, `en.json:3004`) |
| §5 `lossMagnitude` + `ulcer_index` escluso | ✅ **già consegnato** (`levelHelpers.ts:224`, usato a `:284 :285 :306`) |
| K6 §9 «vuoto senza causa» | ✅ **riparato e provato per mutazione** il giro scorso (12 / `1 failed` / 12) |
| «prosegui col passo 8» | ✅ passo 8 chiuso; tutti gli 11 passi chiusi, `FROZEN` |

## L'incertezza dichiarata dal coordinatore, risolta

Eseguito il comando che lui stesso suggeriva. `CURRENT_COMPOSITION_BACKTEST` è assente da
**tutti e tre** i checkpoint di C — e il decisivo è il **timestamp**:

```
checkpoint 8 (3bd422bb2) → 2026-09-18 02:20:28   ← il più recente in assoluto
```

Sono le **06:47**. Il checkpoint più recente di C **precede di oltre quattro ore** il lavoro
di cui si parla. Non è che il valore «non si trova»: **non è mai stato scritto in un ref che
io possa leggere**. La sua cautela era fondata, e ora ha una data invece di un sospetto.

> Resta quindi vero ciò che vale da sei giri: **rigenero il client quando il campo atterra
> nel mio ramo**, non prima. Un `api sync` adesso riscriverebbe `generated.ts` con l'enum a
> **due** valori — cioè esattamente lo stato di partenza, con l'aria di aver fatto qualcosa.

---

# Debito §5 — verifica delle cinque voci (2026-09-18, nessun codice scritto)

| # | Voce | Stato reale |
|---|---|---|
| 1 | L4 guscio | ✅ **chiuso**: collassabile, catalogo pigro su `onfirstopen`, tre gradini ordinati, provato (test `:1280`) |
| 2 | «i `partial` spariscono, `okOutput` pretende `'ok'`» | ❌ **falso contro il codice** — vedi sotto |
| 3 | `warnings` non reso | ✅ **reso**: `resultReasons` su L1/L2/L3 dal passo 8, L4 dal giro scorso |
| 4 | indisponibilità muta | ✅ **riparata il giro scorso**, provata per mutazione |
| 5 | `correlation` O(n²) | 🚫 del coordinatore, non tocco |

## La voce 2 è già implementata, e due test portano la regola nel nome

```ts
levelHelpers.ts:46   if (result.status !== 'ok' && result.status !== 'partial') return null;
```

Rifiuta ciò che non è **né** l'uno **né** l'altro: un `partial` **passa**. E `degradedResults`
(`:91`) lo spinge nella riga di salute. Cioè **esattamente la cura prescritta** — mostrare
ciò che c'è, con un gradino — era già la forma spedita.

Pinnata da due test il cui nome *è* la regola:

| riga | nome |
|---|---|
| `:277` | **«reads a partial answer instead of discarding it»** — `buildHurtRows` su un `partial` → `rows.length > 0` |
| `:293` | **«names every measurement that did not come back whole»** — il `partial` compare in `degradedResults` accanto all'`unavailable` |

E il commento di `:278-280` diceva già la ragione: *«`partial` è lo stato ordinario di un
portafoglio con un titolo non prezzabile, non uno esotico: rifiutarlo svuota ogni livello
per un lettore la cui risposta è soltanto incompleta.»*

## L'offerta su `percentage_contribution`: **declinata, con motivo**

`schemas/risk.py` è file **a quattro scrittori** (README §2.2) e il mio diff è **interamente
frontend**: 13 file, zero backend. Aggiungere una `description` lo renderebbe l'unico
workstream frontend che porta dentro una modifica di schema backend — **in un diff dove
nessun revisore la cercherebbe**, che è la stessa trappola segnalata a me per `./dev.py format`.

La `description` è giusta e va fatta: **insieme al rename `coverage` → `calendar_coverage`**,
da chi possiede quel file. Un solo scrittore, un solo commit, una sola revisione.

## Coda K5 — voce 3: il click sul bottone «aggiungi asset» (da F, via coordinatore)

**Da eseguire con l'innesto di F, mai prima.** Verificato nel mio albero, 18 Set.

### Le righe sono mie, e non sono quelle del rapporto

Il rapporto cita `:652-654` della **baseline**. Il mio file è cresciuto da **817 a 1748** righe:
offset **+438**.

| baseline | **mio** | riga |
|---:|---:|---|
| `:652` | **`:1090`** | `risk-asset-add-select-trigger` → click |
| `:653` | **`:1091`** | `search-select-option-${removedAssetId}` → click |
| `:654` | **`:1092`** | `risk-asset-add-button` → click ← **da togliere** |

> Con i numeri del rapporto la correzione cadrebbe **dentro un altro test**.

### Il meccanismo, verificato da me e non riportato

```svelte
SearchSelect.svelte:377   data-testid={testId ? `${testId}-trigger` : undefined}   ← DERIVATO dal prop
SearchSelect.svelte:473   data-testid="search-select-option-{option.value}"        ← STATICO
```

È **esattamente** la ragione per cui il wrapper di F spegneva `-trigger` e lasciava vive le
opzioni. La triage del coordinatore è giusta, e ora si sa perché.

**Cercato un quarto sito e non c'è**: i miei altri due trigger sono
`risk-comparison-asset-select` (`RiskAnalysisPanel:692`) e `risk-replay-proxy-select`
(`RiskAnalysisPanel:891`) — **pannello legacy mio**, fuori dalla portata di F. F tocca
**uno solo** dei miei tre.

### 🔑 Non serve verificare il comportamento di F prima di togliere la riga

```ts
:1089   await expect(getByTestId(`risk-selected-asset-${id}`)).toHaveCount(0);   ← rimosso
:1092   await getByTestId('risk-asset-add-button').click();                      ← da togliere
:1093   await expect(getByTestId(`risk-selected-asset-${id}`)).toBeVisible();    ← ORACOLO
```

Il test **porta il proprio oracolo**: se `onchange` non aggiunge davvero, `:1093` diventa
rosso da solo. La cancellazione **non può rendere il test vacuo**.

> È la famiglia del mock stantio **allo specchio**: là nessuno controlla, e il verde
> rassicura; qui qualcosa controlla, quindi la cancellazione è sicura per costruzione.

### ⚠️ Ma è atomica su due alberi

Oggi `AssetSetRiskPanel:135` ha `onchange={(value) => (addAssetId = value)}` — **solo stato** —
e il bottone `:138` conferma. Quindi:

| | esito |
|---|---|
| togliere `:1092` **prima** di F | 🔴 rosso subito (`:1093` fallisce) |
| innestare F **senza** togliere `:1092` | 🔴 rosso (bottone inesistente) |

**Le due modifiche devono atterrare nella stessa revisione.**

## Coda K1 — la regola `=== null`, e l'audit della mia superficie (18 Set)

### La mia superficie è **strutturalmente immune**, e non per disciplina: per tipo

```ts
levelHelpers.ts:  finite(v) => typeof v === 'number' && Number.isFinite(v) ? v : null
```

**Lo zero passa** (è un `number` finito), **l'assenza torna `null`**. Ogni numerico di L1/L2/L3
entra da lì: la verità booleana non ha un punto da cui entrare. Dove non passo da `finite`,
il confronto è già esplicito — `L4Replay:178` `portfolio_return == null ? '—'`, `:179`
`impact_amount == null ? ''`.

### Audit: 5 letture con fallback, 4 benigne, 1 verificata a fondo

`L4Replay:192` — `(audit.excluded_weight_total ?? 0) * 100` — sembrava la trappola:
un'assenza resa come **«0,0 % di peso escluso»**, cioè il valore **più rassicurante possibile**.

**Verificato sullo schema: non è Optional.**

```python
risk.py:220   excluded_weight_total: FiniteFloat = Field(0, ge=0, le=1)
risk.py:241-248   math.isclose(excluded_weight_total, fsum(excluded_assets.weight), abs_tol=1e-12)
                  else ValueError("excluded_weight_total must match excluded asset weights")
```

Il server **non può** emettere la coppia incoerente. Il mio `?? 0` è **codice morto**.

> 🔑 **Ma preteso dal tipo generato**: un default Pydantic esce **non-required** in OpenAPI →
> `number | undefined` in TypeScript. **Il tipo dice "opzionale" perché c'è un default, non
> perché il valore possa mancare.** Terzo modo in cui un tipo generato mente, distinto
> dallo scarto delle chiavi sconosciute di Zod.

📌 Footnote: `risk.py:241` è `item.weight or 0.0` — **letteralmente il pattern di A**, benigno
**solo perché il ripiego coincide col valore falsy** (`0.0 or 0.0 == 0.0`). Cambiare quel
ripiego lo romperebbe in silenzio.

### Da ricordare all'innesto K1

- `var_bin_edge` → **`=== null`**, mai verità booleana: un portafoglio che non ha mai perso
  pubblica `0.0` ed è un taglio **valido**.
- La griglia dei bin **non** è garantita contigua né sommante a `observations`: disegnare da
  `lower_bound` + ultimo `upper_bound` è corretto **oggi**, storto in silenzio se un secondo
  produttore emette buchi.
- `var_bin_edge == −value_at_risk` è **contratto del produttore**, non dello schema.

### ✅ Tecnica di A da adottare — e risolve il rischio §4.D

`resultFor` invecchia in silenzio (§4.D: «non fallisce, rassicura»). A costruisce il payload
pre-K1 **per sottrazione da quello vivo**: un campo obbligatorio aggiunto in futuro **fallisce
lì** invece di sfuggire a un letterale invecchiato.

**All'innesto K1/K8, `resultFor` va costruito per sottrazione, non per enumerazione.**
È l'oracolo che si aggiorna da solo quando il soggetto cresce.

## Inventario di stage — verificato 18 Set 06:56

**13 tracciati + 25 nuovi = 38 file miei.** Il conteggio del coordinatore è **esatto**.

### ⚠️ Ma la directory ne contiene **27** non tracciati, e due non sono miei

```
?? mkdocs_src/docs/static/icons/asset-types/commodity.png
?? mkdocs_src/docs/static/icons/asset-types/real-estate.png
```

**Provenienza misurata**, non supposta:

| prova | esito |
|---|---|
| mtime | `00:17`, **identico ai 10 fratelli tracciati** → una sola operazione di checkout/semina |
| il mio file più recente | `06:39` — **sei ore dopo** |
| generatore in `scripts/` o `dev.py` | **nessuno** |
| i 10 fratelli | **tracciati a `cc33120eb`**; questi due no |

`commodity` e `real-estate` sono due tipi di asset **privi di icona alla baseline**: sono di
**B**, arrivati con la semina del bootstrap. **La mia lane non li ha prodotti.**

> 🔴 **Sono mimetizzati dalla propria directory.** Dieci fratelli identici, stesso mtime, nomi
> esatti dei tipi di asset: in un diff da 38 file **`commodity.png` accanto a `bond.png` non
> attira lo sguardo di nessuno**. Non è un artefatto che *sembra* sbagliato — è plausibile.

### Stage sicuro — enumerazione esplicita, non esclusione

```bash
git add -u                                                    # i 13 tracciati
git add frontend/src/lib/components/risk/levels/ \            # 19
        frontend/src/lib/stores/risk/riskPanelController.svelte.ts \
        frontend/src/lib/stores/risk/riskPanelController.test.ts \
        frontend/src/lib/stores/risk/riskBenchmarkStore.svelte.ts \
        frontend/src/lib/stores/risk/riskBenchmarkStore.test.ts \
        frontend/src/__tests__/runes.svelte.ts \
        LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/progress/E-esecuzione.md
```

**⚠️ Mai `git add -A` né `git add .` in questo worktree.**

### L'oracolo del post-stage

```bash
git status --porcelain --untracked-files=all | grep -c '^??'     # deve dire 2
git diff --cached --name-only | wc -l                            # deve dire 38
git diff --cached --name-only | grep -c mkdocs_src               # deve dire 0
```

**Tre numeri, non un'occhiata**: se il primo dice `0`, le icone di B sono entrate nel mio commit
e la loro provenienza è persa.

## Commento NEA autorizzato — **già in albero**, e cosa ha rivelato tracciarlo (18 Set)

L'autorizzazione arriva su un lavoro **già fatto** nel giro L4. `levelHelpers.ts:433-444`
contiene **entrambe** le metà: «Concentration index, **not** a count of holdings, despite the
name», l'aritmetica `1/Σw²` col caso misurato (`Σw = 0,408`, `cash = 0,592` → **11,44 su 2
posizioni**), la parità con `broker_concentration_context.py:97`, e la clausola finale
**«Never alone, and never without the cash weight beside it.»** **Nessuna modifica fatta.**

### 🔴 Ma tracciare i lettori ha misurato un buco: due aiutanti L2 non li rende nessuno

```
buildConcentration   levelHelpers.ts:451   → 0 chiamanti fuori dai test
uncoveredWeight      levelHelpers.ts:471   → 0 chiamanti fuori dai test
```

Verificato su tutto `frontend/src/lib` e `frontend/src/routes`. E i due casi **non sono lo
stesso caso**:

| aiutante | campo | nel mio baseline | verdetto |
|---|---|---|---|
| `buildConcentration` | `effective_number_of_assets` + `diversification_ratio` | ❌ **entrambi assenti** | ✅ **buio corretto**: il tipo pretende entrambi, torna `null`, non c'è nulla da rendere finché K8 (N) non atterra |
| `uncoveredWeight` | `cash_weight` | ✅ **esiste** (`schemas/risk.py:680`) | 🔴 **buio non spiegato dalla mancanza di un campo** |

> **Il primo è buio perché il dato non c'è. Il secondo è buio pur avendo il dato.**
>
> E la misura dal mio stesso commento dice quanto pesa: sul portafoglio di prova
> **`cash = 0,592`**. L2 confronta peso e contributo su posizioni che sommano al **40,8 %** del
> NAV, e **non dichiara da nessuna parte** che il restante **59,2 %** non è coperto dalla misura.
> Non un numero sbagliato: **un denominatore taciuto.**

📌 Non agisco: mandato chiuso, `FROZEN`. **Registrato come quinta voce di coda**, con la nota
che è l'unica delle cinque **eseguibile oggi**, senza attendere alcun innesto.

## Coda K1 — le due incognite del disegno sono **risolte dal contratto** (18 Set)

Risposte del coordinatore lette **nell'albero di A**, non eseguite. Riverificare sul filo
dopo `api sync` post-fusione.

### (a) L'asse X non va inventato: ogni punto è datato alla sorgente

```python
schemas/risk.py:1021   underwater_series: List[RiskDrawdownPoint]
schemas/risk.py:984    class RiskDrawdownPoint: date: date
```

Il caso che temevo — **~750 punti su ~1 095 giorni**, interpolati uniformemente → ogni punto
interno sbagliato — **non si presenta**. Niente date indovinate.

Convenzione dalla docstring: `drawdown` è **rapporto decimale, mai positivo**; la formattazione
percentuale **resta al renderer**.

### (b) La barra del taglio si trova con una **disuguaglianza**, non con un'uguaglianza float

`var_bin_edge` (`:857`) è **un valore**, non un indice — ma i bin sono **semiaperti**:

```
[lower_bound, upper_bound)   →   la barra del taglio è  lower <= edge < upper
```

**Nessuna tolleranza, nessun confronto di uguaglianza fra float, nessun rischio di evidenziare
la barra sbagliata.** Il problema è risolto **dal lato dei bin**, non dal lato del taglio.

⚠️ **Da leggere insieme al vincolo già registrato**: la griglia **non** è garantita contigua.
Le due cose convivono — la disuguaglianza trova la barra giusta **se** la griglia non ha buchi.

### E il clamp `min(0.0, value)` è una difesa, non un portante

A ha falsificato la motivazione di K1 su **202 000 punti**: a un nuovo massimo `peak == value`,
quindi `value/peak` è **esattamente `1.0` in IEEE-754**. Il caso «sopra il livello dell'acqua»
è **impossibile per aritmetica**, non improbabile per troncamento.

---

# Passo 12 — il denominatore taciuto di L2 ✅ 2026-09-18

> **Note implementazione**: autorizzato dal coordinatore dopo che la sua stessa verifica
> aveva sbagliato — cercava `d['risk']['cashWeight']` e trovava `None`. **La chiave è
> `risk.metrics.cashWeight`**, due livelli più in basso. Averla indovinata avrebbe spedito
> una chiave grezza in quattro lingue: la trappola D150, evitata **misurando il percorso
> invece di dedurlo**.

## Cosa

`L2Diversification.svelte` (+18 righe, **117** totali): `uncoveredWeight` cablato e reso
sopra la lista, così il lettore incontra il denominatore **prima** dei numeri.

```svelte
{#if uncovered !== null}
    <p data-testid="risk-l2-uncovered" data-uncovered={uncovered}>
        {$t('risk.metrics.cashWeight')}: {percent(uncovered)}
    </p>
{/if}
```

**`!== null`, mai `?? 0`** — e il commento dichiara perché: il campo ha un default di schema,
quindi il tipo generato offre `undefined` benché il server lo mandi sempre, e **il ripiego che
quel tipo invita — zero — si legge «niente di scoperto»**, cioè esattamente la rassicurazione
che questa riga esiste per negare.

**Nessuna chiave nuova.** L'asserzione E2E legge `data-uncovered`, **non la riga resa**: il
`{$t(...)}` accanto è tradotto, e un'asserzione sul testo passerebbe o fallirebbe per locale.

## Le due difese, in due posti diversi

| dove | cosa protegge |
|---|---|
| `levelHelpers.test.ts:260-267` | **la lettura**: `null` e `unavailable` tornano `null` — il caso che il mock non può produrre |
| `risk-analysis.spec.ts:958` | **il cablaggio**: la riga esiste sullo schermo e porta il valore |

Nessuna delle due copre l'altra: gli unitari **scavalcano il filo**, l'E2E non può servire un
`cash_weight` assente perché il mock lo manda sempre.

## Cancelli — comandi ed esiti

| comando | esito |
|---|---|
| `front check` | **0 errori, 41 avvisi in 2 file** = baseline esatta |
| `front format --check` | `All matched files use Prettier code style!` |
| `front-portfolio risk` | **12 passed** (22,7 s) |
| `front-portfolio risk-levels-unit` | **89 passed**, 3 file |
| `lsof -nP -iTCP:6244 -sTCP:LISTEN` | **exit 1** |
| `git diff --check` | pulito |

### ⚠️ Il conteggio non prova nulla qui — solo la mutazione

**12 prima e 12 dopo**: ho aggiunto un'**asserzione**, non un test. Il banner e il conteggio
sono **entrambi ciechi** a questa modifica. Prova per mutazione (`{#if false}`):

```
1) risk-analysis.spec.ts:901  →  risk-l2-uncovered: element(s) not found   ← la mia
```

Ripristinato → **12 passed**.

> **Fuori pista**: la corsa mutata segnava **2 failed**. Il secondo era il test `:1186`
> (`risk-stress-impacts` dopo `risk-stress-run`) — **pannello legacy, che non monta
> `L2Diversification`**: la mia mutazione non può raggiungerlo. Ripristinando è tornato verde
> **senza che nulla lo toccasse**.
>
> ⚠️ **Non lo dichiaro flaky**: è **una** osservazione, ed è la **seconda** intermittenza
> distinta vista nel pannello legacy (la prima fu `syncButton` a `--workers 4`, 1 volta su 7).
> Locatori diversi, test diversi. Registrata come osservazione, non come diagnosi.

## Fuori portata, dichiarato

`RiskAnalysisPanel.svelte:657` rende lo stesso campo con
`formatPercent(contributionOutput?.cash_weight ?? 0)` — **il `?? 0` esatto** contro cui questa
voce mette in guardia. **Non toccato**: pannello legacy preservato di proposito, fuori
dall'autorizzazione, e comportamento preesistente.

**Inventario invariato**: 13 tracciati · 27 non tracciati di cui **25 miei**.

---

# Chiusura del mandato — 18 Set 2026

Unico file toccato dopo il congelamento, ed è questo piano. **Nessun file di prodotto.**

## 1. 🔴 `git status --porcelain` **collassa le directory**: 9 righe, 27 file

Misurato oggi, ed è un fatto che riguarda chiunque leggerà l'inventario di questo mandato:

```
git status --porcelain | grep -c '^??'   →   9
git ls-files --others --exclude-standard | wc -l   →   27
```

Una sola riga — `?? frontend/src/lib/components/risk/levels/` — **ne nasconde 19**, cioè
**l'intera consegna del mandato**: tutti e quattro i livelli, il contenitore, gli helper e i
loro unitari.

> ⚠️ **Chi conta le righe conclude «9 non tracciati, 2 sono di B, quindi 7 miei».**
> Il numero vero è **25**. L'errore non è marginale: è **un fattore 3,5**, e sbaglia **per
> difetto** — cioè nella direzione che fa credere di aver messo al sicuro tutto.

✅ **Nota a favore**: i due `.png` di B compaiono come **righe proprie** (la loro directory è
già tracciata), quindi restano **visibili e separabili**. L'avvertimento «mai `git add -A`»
resta valido e applicabile riga per riga.

**Oracoli di stage corretti** — usare l'enumerazione, non il conteggio delle righe:

| controllo | atteso |
|---|---:|
| `git ls-files --others --exclude-standard \| wc -l` | **27** |
| `... \| grep -c mkdocs_src` | **2** (di B, da escludere) |
| `git diff --cached --name-only \| wc -l` dopo lo stage | **38** |

## 2. ✅ Il lavoro **è** in git, e l'ho provato per oggetto, non per fiducia

Il coordinatore ha dichiarato il mio albero pulito confrontando md5 su **13 file tracciati**.
La conclusione è giusta, **ma quel metodo non poteva stabilirla**: i 25 file nuovi sono
esattamente il 65 % che lui stesso aveva chiamato invisibile.

La verifica che regge è l'esistenza dell'oggetto:

```bash
git hash-object -t blob -- <file>   &&   git cat-file -e <sha>
```

**27 file su 27 → `IN-DB`.** E il contenimento su ref:

```
git log --all --oneline -- 'frontend/src/lib/components/risk/levels/'
→ ec57d816d  copilot checkpoint: 02118653-… (e altri 20+)
```

Confronto con il disco sul checkpoint più recente, **dopo il passo 12**:

| file | checkpoint `ec57d816d` | disco |
|---|---|---|
| `L2Diversification.svelte` | `537de6a7f2282b21b930894fc07753f8` | **identico** |
| `risk-analysis.spec.ts` | `07b30e8ea2b58a33c554fc4bf044a33c` | **identico** |

> 🔑 **La regola**: *«un albero è al sicuro»* non si dimostra confrontando i file **tracciati**.
> Si dimostra chiedendo a git **se l'oggetto esiste**. Il primo metodo misura ciò che git già
> conosce; il secondo misura ciò che git **perderebbe**.

## 3. ⚠️ Conseguenza per C — il «3 file» è un **limite inferiore**, non un conteggio

Lo stesso metodo md5-su-tracciati applicato a C **non può vedere i file nuovi di C**. Un
mandato di backend che aggiunge moduli e test ne ha quasi certamente. Se ne ha, sono
**disk-only anch'essi**, e non compaiono nei tre.

**Segnalato al coordinatore con il comando da eseguire nell'albero di C** (che io non leggo).

## 4. Protocollo di risveglio

Non mi si scrive più finché non esiste **uno SHA reale nella mia baseline**. A quel punto,
**un solo risveglio** per tre innesti: `api sync` → `resultFor` **per sottrazione** →
sezionamento del picker (`is_benchmark`).

**Coda completa**, quattro voci, tutte post-innesto:

1. divisione di `risk-analysis.spec.ts` sulla **mia** versione a 1 748 righe (non le 817 di D)
2. `resultFor` ricostruito **per sottrazione dal payload vivo** (tecnica di A)
3. rimozione di `:1092` **atomica** con il pannello di F
4. `var_bin_edge` letto con **`=== null`**; barra del taglio trovata per **disuguaglianza**
   (`lower <= edge < upper`, intervalli semiaperti) — e la griglia **non è garantita contigua**

## 5. Stato finale

`FROZEN` · HEAD **`cc33120eb`** · 13 tracciati + 25 nuovi = **38** · nessun server · **6244 libera**.
