# R5 — Risk: fix post-merge e apertura della review puntuale

**Workstream**: Risk (coordinamento del sottosistema di rischio)
**Worktree**: `e-alfy-ideal-eureka` · branch `e-alfy-risk-management-replan`
**Baseline**: `f1047f766` (`dev_release2`, 23/09/2026)
**Approvato dal developer**: 23/09/2026, dopo una revisione del coordinator Release 2
**Fonti**: [`09_feedbackJobs/08_review_visiva_20260922.md`](../../09_feedbackJobs/08_review_visiva_20260922.md) ·
[`09_feedbackJobs/09_reperti_analisi_statica_20260922.md`](../../09_feedbackJobs/09_reperti_analisi_statica_20260922.md)

> Piano vivo: si aggiorna **dopo ogni passo**, con data, *Note implementazione* e *Fuori
> pista*. L'avanzamento è in fondo, in [§ Avanzamento](#avanzamento).

---

**Baseline verificata** `f1047f766` · albero pulito · catena Alembic
`001 → 002 → 003_scheduler_timezone → 004_release_1_2_0_schema`.
Tutti gli 8 worktree a `f1047f766`, puliti, **avanti 0** → conflitti previsti **per
perimetro dichiarato**, non su diff in volo.

## Lane e dati

| | porta | data-dir | uso |
|---|---|---|---|
| **copia di prod** | `6162` | `/tmp/librefolio-r2-risk-prodcopy` | server, verifiche, review |
| **suite** | `6152` | `/tmp/librefolio-r2-risk` | **solo** `dev.py test …` |

Mai un `dev.py test` sulla copia. Nessuna nuova migrazione Alembic.

**Copia di prod — dalla snapshot**, non dal main checkout (che l'agente dei figli vieta):

```bash
SNAP=/tmp/librefolio-r2-prod-snapshot
COPIA=/tmp/librefolio-r2-risk-prodcopy
test -f "$SNAP/sqlite/app.db" \
  && test ! -e "$SNAP/.librefolio-production-data" \
  && { [ ! -e "$COPIA" ] || mv "$COPIA" "$COPIA.prev-$(date +%Y%m%d-%H%M%S)"; } \
  && cp -R "$SNAP" "$COPIA" \
  && chmod -R u+w "$COPIA" \
  && sqlite3 "$COPIA/sqlite/app.db" "SELECT version_num FROM alembic_version" \
  || echo "❌ copia NON eseguita (snapshot assente o marcata): fermati e dimmelo"
```

Deve stampare `004_release_1_2_0_schema`. Il `chmod` serve: la snapshot è `a-w`. **Se la
snapshot manca (reboot), la chiedo al coordinator** — non la ricostruisco.

**Credenziali**: fornite dal developer (messaggio del coordinator, 23/09), non trascritte in file versionati. Se il login
fallisce, **prima il list, poi il reset, solo sulla mia copia** (`dev.py user` non ha
`--data-dir` e senza `--test-db` mira al prod del checkout):

```bash
LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-risk-prodcopy PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py user --test-db list
LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-risk-prodcopy PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py user --test-db reset alfy '<password del developer>'
```

Due tempi: **① fix post-merge → FROZEN → ② mi fermo** e apro con il developer la review
componente-per-componente (estetica + matematica).

---

## Tempo ① — fix post-merge

### ① 🔴 Stress uniforme: 8 tipi su 17 ricevono 0.0 in silenzio (classe D70)

Trovato da K, verificato dal coordinator, **rimisurato da me**:

```
RiskAnalysisPanel.svelte:115   stressAssetClasses = ['STOCK','ETF','BOND','CRYPTO','FUND','CROWDFUND','HOLD','INDEX','OTHER']
AssetType (models.py)          17 valori
mancanti                       COMMODITY · REAL_ESTATE · ETF_STOCK · ETF_BOND · ETF_COMMODITY
                               ETF_REAL_ESTATE · ETF_CRYPTO · ETF_MONETARY
```

È esattamente il caso che il gate backend descrive — *«no error is raised, the number is
simply wrong»* (`test_risk_scenario_catalog.py:303`) — **un piano più su, dove il gate non
arriva**.

**Dove si esercita, misurato** (perché cambia cosa va provato):

| sito | cosa fa | raggiungibile oggi? |
|---|---|---|
| `:472` | shock uniforme `stressPercent` sulla lista, per scope **≠ `asset`** | ⚠️ **no, per caso**: l'unico consumatore rimasto (`AssetRiskScenariosView:90`, Asset Detail) passa `scope.kind: 'asset'` → ramo `:469`. Il ramo è vivo nel codice e **ritorna a sbagliare il giorno in cui qualcuno rimonta il pannello su un portafoglio** |
| `:173` | aggiunge la lista all'editor dei secchi `asset_class` | ✅ **sì**: su Asset Detail, prima di scegliere un preset, gli 8 tipi mancanti **non compaiono nell'editor** |
| `L4Shock` (Dashboard/Broker) | secchi presi dal **catalogo** (`scenarioHelpers.ts:106-115`) | ✅ **sicuro per costruzione**: il catalogo è legato all'enum dal gate backend bidirezionale |

**Rimedio**: la lista **si deriva dall'enum**, non si riscrive: `ASSET_TYPES`
(`assetTypes.ts:17`, `= schemas.AssetType.options`, file di K — **consumo, non scrivo**).

**Test** — comportamentale, non tautologico (un test *«la lista è `ASSET_TYPES`»* passerebbe
sempre, anche su un'altra lista scritta a mano):
- costruire i parametri dello shock uniforme per uno scope `portfolio` e asserire che **ogni
  valore di `schemas.AssetType.options`** riceve `stressPercent / 100`;
- **controllo positivo**: la stessa asserzione applicata alla lista a mano **fallisce** e nomina
  gli 8 tipi — è la riga che rende leggibile il verde;
- l'editor `asset_class` elenca **tutti** i tipi dell'enum.

⚠️ Per renderlo testabile, la costruzione dei parametri esce dal componente in un helper puro
**nuovo** (non in `riskAnalysisHelpers.ts`, che J sta riparando — vedi ⑦).

### ② R12 🟠 La torta «per tipo» mostra un livello invece di due

**Diagnosi statica (da confermare sulla copia di prod prima di scrivere):**

| fatto | dove |
|---|---|
| il backend accumula il tipo **grezzo** | `portfolio_engine.py:1685` `by_type[asset_type] += mv` |
| il roll-up esiste nel frontend ed è corretto | `assetTypes.ts:158` `primaryAssetType('ETF_STOCK') = 'STOCK'` |
| la torta lo applica, in `mode='type'` | `AllocationPieChart.svelte:194-197` → `buildAllocationHierarchy` |
| è **D71**: un anello, il sottotipo come sfumatura | `allocationHierarchy.ts:1-49` |

🔑 **Il buco è nel disegno D71:**

```
allocationHierarchy.test.ts:414   'never shades a singleton group'
AllocationPieChart.svelte:361     riga «↳ <genitore> <totale>%» solo se groupSize > 1
```

Un **ETF azionario senza azioni dirette** è un gruppo di **uno**: colore puro, nessun genitore
visibile — **indistinguibile da una categoria indipendente**. G aveva misurato il **massimo**
di un gruppo, non il **minimo informativo**.

**Rimedio: D72**, ciambella a due anelli — **tipo base dentro**, membri fuori.

✅ **Decisione del developer (23/09)**: anello esterno **solo dove una famiglia ha sottotipi**;
le altre fette **piene su un solo livello** → per una famiglia senza sottotipi, l'arco esterno
ha lo stesso colore del base, senza bordo, etichetta, legenda né tooltip propri: si legge come
**un pezzo solo** a tutto spessore.

🔴 **Gruppi di N membri, non di due.** Se il developer sceglie
`primaryAssetType(CROWDFUND_REAL_ESTATE) = REAL_ESTATE` (raccomandazione di K, coerente con
D61), **Immobiliare diventa un gruppo a tre**. La ciambella non presume il numero dei membri;
le sfumature dell'anello esterno vanno generate per N, non come «puro + uno».

**Due relazioni, due funzioni** — non si confondono:

| relazione | funzione | chi la usa |
|---|---|---|
| **roll-up**: in quale tipo base confluisce | `primaryAssetType` | **la torta (mia)** |
| **contenitore**: quale icona porta | `assetTypeFamily()` / `ASSET_TYPE_FAMILIES` (esposte da K) | le icone composite (K) |

K **tiene invariata** la firma di `getAssetTypeIconUrl(type): string` (usata a
`AllocationPieChart:238, :354`); se gli serve una seconda icona aggiunge una funzione.

**Passi**
1. **Riprodurre sulla copia di prod**: dump di `allocation_by_type` + screenshot. Se il caso
   non è il singoletto, **rivedo la diagnosi prima di scrivere**.
2. **Implementare in `AllocationPieChart.svelte`**, solo `mode === 'type'`:
   - due serie `pie` sullo stesso centro;
   - 🔴 trappola di G: il percorso veloce (`:208-212`, `sameTypeSet`) scrive **una** serie →
     aggiornarle entrambe, con un test che lo pinna;
   - importi solo via `formatCurrencyAmountPlain` (canale mascherato di J) → **nessuna modifica
     al registro privacy**;
   - costruzione degli anelli come **funzione nuova e additiva**: l'output di
     `buildAllocationHierarchy` **non cambia**, lo consuma `AllocationHistoryChart` (di I);
   - **`AllocationPanel.svelte` non si tocca** (memoria di vista R21, di I);
   - `sector` e Asset Detail (`assets/[id]:3453`) invariati e pinnati.
3. **Test list al developer**: sottotipo **da solo** · famiglia completa · **famiglia a tre**
   (`REAL_ESTATE` + `ETF_REAL_ESTATE` + un terzo membro fittizio: il test non deve dipendere
   da R17) · famiglia senza sottotipi = un pezzo solo · `Liquidity` · `ETF` generico ·
   `ETF_MONETARY` · **somma degli archi interni = esterni** · ordine · palette corta · percorso
   veloce · snapshot di `sector`. ⚠️ Nessun E2E può asserire un anello su canvas: la prova
   visiva è del developer.

### ③ Registro — ciò che vive solo nei messaggi

- **D62** (`04-decisioni-e-questioni-aperte.md:74`), **annotare senza riscrivere**: *corretta
  al passo 10 di B → decisione (d), sezioni su `SimpleSelect`; riaperta dalla review del 22/09
  (R15); owner **K***. ➕ e un fatto che nessuno aveva notato: **F27 è citata e mai scritta** —
  vedi ⑧.
- **D71/D72**: la premessa di G misurava il massimo, non il singoletto; D72 attivata da R12;
  i gruppi possono crescere a N con R17.
- **`REGISTRO.md`**: voci che **rimandano** a `09_…md` invece di ricopiarlo, più ciò che lì non
  c'è: diagnosi R12, stress a lista scritta a mano, collisione R17↔catalogo, F27 fantasma.
- **`_comune.md`**: corsie `6162`/`6152`, snapshot come fonte della copia, credenziali e ordine
  `list → reset`, `api sync` **in-process**, catena `004`.

### ④ §1.7 — il nostro cancello i18n condanna 4 chiavi vive

`scripts/i18n_usage.py` non riduce `$derived(cond ? 'a' : 'b')` (`RiskBetaBanner.svelte:31`)
→ `risk.betaBanner.*` fra le morte. Rimedio: estrarre **entrambi i rami** di un prefisso
condizionale letterale. Controlli: **positivo** (le 4 escono) · **negativo** (`panelTitle`
resta morta) · **invariante** (le 31 di `SimulationProvenance` restano vive) · diff degli
**elenchi**, non dei totali.

### ⑤ §2.6 — deriva dei commenti

`L4Replay:47`, `L4Shock:46` citano `formatScopedCurrencyAmount:163` (ora `:177`) → citare il
**simbolo**. Non si sovrappone alle righe di J (`riskAnalysisHelpers.ts:155-161`).

### ⑥ Test del filtro broker: esce da `risk-analysis.spec.ts`

`risk-analysis.spec.ts:1335` *«asset global maps broker holdings and supports remove/add»* è
comportamento di **Asset Global**, che vive nel mio spec → passa a `risk-lab.spec.ts`.
**F lo aggiunge, io lo rimuovo, nello stesso lotto; l'ordine lo coordina il coordinator** —
così non esiste una finestra in cui nessuno spec lo copre. `:1397` (tab broker su Broker
Detail) **resta mio**. `risk` scende da 14 a 13; aggiorno la `desc=` del catalogo del runner
solo per sottrazione.

---

## Confini decisi dal coordinator

| voce | owner | io |
|---|---|---|
| pin privacy su `risk-lab.spec.ts:1356` | **F** | non tocco il file |
| `risk.assetSet.panelTitle` orfano | **F**, a fine round (l'ha introdotta F, `f2ad97dd4`) | — |
| sync FX su Asset Global mai ri-alloggiato (R2-128, `REGISTRO.md:360`) | **F**, proprietario del guscio | — |
| `CorrelationHeatmap` | **F** (la monta anche `L2Diversification`) | **non la modifico** |
| gli 11 testid di `risk-lab` composti dai miei componenti — 10 da `RiskLevelSection`, 1 da `TornadoChart` (`{testId}-…`) — più 3 radici il cui valore sceglie chi li monta (`risk-asset-set-loss`, `risk-asset-set-paid`, `risk-replay-section`) | — | **non li rinomino senza avvisare** (corretto il 24/09: erano scritti «12», misurato per testid esatto sulla prop davvero passata) |
| `riskAnalysisHelpers.ts:155-161` + `…test.ts:387` — `formatCurrencyAmount` che sotto privacy perde la valuta | **J** | **non tocco quelle righe** |
| emoji mancanti in `AllocationHistoryChart` | **I** | — |
| le due righe di `CROWDFUND_REAL_ESTATE` in `equity_crash.yml` e `global_risk_off.yml` | **K**, nello stesso commit dell'enum | **non tocco quei due YAML finché R17 non è integrato** |

### ⑦ La conseguenza del fix di J sulla mia review

Oggi `formatCurrencyAmount` sotto privacy rende `•••` **senza valuta**; per il developer è un
errore (*«la privacy nasconde il numero, non la valuta»*). Dopo J, `L1` renderà
`−••• € 🇪🇺 EUR`. → **La review di L1/L4 sul denaro va fatta dopo il fix di J**, o giudicheremo
un'uscita che sta per cambiare.

---

## Previsione dei conflitti

| con | superficie | tipo | mitigazione |
|---|---|---|---|
| **K** | `ASSET_TYPES`, `primaryAssetType`, `getAssetTypeIconUrl` | semantico | consumo, non scrivo; firma dell'icona garantita da K |
| **K** 🔴 | R17 → gruppo `REAL_ESTATE` a 3 membri | semantico | D72 per N membri, test col terzo membro fittizio |
| **K** | R17 → gate enum↔`bucket_shocks` | ordine | K scrive le due righe YAML nel suo commit; io fuori da quei file |
| **I** | `allocationHierarchy.ts`, `AllocationPanel.svelte` | testuale/semantico | solo aggiunte nel modulo; pannello intoccato |
| **J** | `riskAnalysisHelpers.ts:155-161` | testuale | righe sue; il mio helper dello stress va in un file nuovo |
| **F** | `risk-lab.spec.ts`, `CorrelationHeatmap`, testid di `RiskLevelSection` | testuale + ordine | test del filtro broker in lotto coordinato; nessuna modifica alla heatmap |
| **A** | cataloghi i18n | testuale | nessuna mia chiave in `risk.assetSet.*` |
| **D** | — | — | — |
| condivisi | cataloghi i18n, catalogo del runner | additivo | elencati nell'handoff; `CHANGELOG.md` non lo tocco, propongo le voci |

---

## ⑧ Da mandare al coordinator

- **Parere su R17** (decide il developer): la **famiglia** di roll-up e il **secchio di stress**
  rispondono a domande diverse e possono non coincidere. Il gate è chiavato su `AssetType`, non
  sul primario. Quindi `primaryAssetType → REAL_ESTATE` (K) è compatibile con uno shock **da
  CROWDFUND** (`−0.10 / −0.10`): il crowdfunding immobiliare è **prestito illiquido non marcato
  a mercato** — in uno shock di mercato il suo prezzo non si muove come quello di un REIT
  quotato; il suo rischio è il **default**, che arriva in ritardo. Applicargli il `−0.20` di
  `REAL_ESTATE` sovrastima la perdita di breve e ne nasconde la natura. È un giudizio, non una
  misura: lo dichiaro come tale.
- **Risposta a K su F27**: **F27 non esiste.** B la cita al passo 10 (*«vedi F27»*) ma la
  numerazione salta da F26 a F28: è un rimando a un testo mai scritto. L'unico contenuto
  rintracciabile è quello del passo 10 — i **tre assi** (contenuto dell'opzione, prefisso dei
  testid, modello dati) — più il ragionamento che lo circonda: (d) contro (b) per non
  **duplicare la meccanica di tendina** (il rischio di D73), F28 (`SelectOption.header` e la
  regola di `optionFilter.ts:39-40`) e F29 (`SimpleSelect` rende già le intestazioni, la
  pastiglia composita di D52 gira immutata). **Chi rivaluta R15 non deve cercare un quarto
  asse in F27: non c'è un F27 in cui cercarlo.**

---

## Tempo ② — review puntuale col developer (dopo il FROZEN di ①)

Sulla copia di prod **rinfrescata**, un componente alla volta. Per ciascuno una scheda: *a quale
domanda risponde · formula e plugin · dove confrontarla con numeri che conosci · limiti noti ·
cosa sarebbe un difetto · chi possiede il fix*.

**Prima di tutto — R12, il fix di questo round che solo i tuoi occhi possono chiudere**

Un anello su canvas non si asserisce in un E2E: i test legano la costruzione, non l'aspetto.

| # | cosa guardare | perché è una scelta, non un fatto |
|---|---|---|
| R12a | niente spazio di 1° fra le fette in modalità anelli | `padAngle` toglie un grado per arco e i due anelli hanno archi diversi: con lo spazio scivolerebbero |
| R12b | legenda non cliccabile in modalità anelli | spegnere una voce toglierebbe un arco da un anello solo — cambio di comportamento |
| R12c | famiglia piccola (3,5 %): si vede **una** icona sola | `hideOverlap` toglie quella della banda interna |
| R12d | tooltip: membro `3.52%`, famiglia `Azione 3.5%` | due arrotondamenti diversi sulla stessa riga |
| R12e | 8 dei tuoi 15 asset sono `ETF` generico | **dato, non codice**: più ne classifichi, più il secondo anello racconta |

**Dashboard (i tuoi dati, in €)**

| # | componente | matematica da verificare | owner del fix |
|---|---|---|---|
| 0 | `RiskPanelHeader` | periodo, perimetro, banner qualità del dato | Risk |
| 1a | L1 · giornata storta / mese storto | VaR e CVaR storici 1g e 21g: segno, confidenza, scala mensile | Risk · denaro: **J** |
| 1b | L1 · peggior discesa e drawdown corrente | max drawdown su TWRR, durata, recupero; € = valore × frazione | Risk · denaro: **J** |
| 1c | L1 · `UnderwaterChart` + Ulcer · `ReturnHistogram` | coerenza con le card | Risk |
| 2a | L2 · card di diversificazione | asset effettivi, correlazione media | Risk |
| 2b | L2 · contributo al rischio | peso vs PCTR, somma 100 % | Risk |
| 2c | L2 · `CorrelationHeatmap` + coppie | finestra congiunta, ordinamento | **F** |
| 3a | L3 · `L3Benchmark` | benchmark persistente, uguale su ogni pagina | Risk |
| 3b | L3 · Sortino / Sharpe / σ / β | annualizzazione aritmetica, risk-free, perimetro dichiarato | Risk |
| 3c | L3 · `ScatterChart` | punti, portafoglio, Capital Market Line | Risk |
| 4a | L4 · `L4Replay` + tornado | copertura, proxy, trattamento dei buchi | Risk · denaro: **J** |
| 4b | L4 · `L4Shock` | propagazione per `asset_class` | Risk · denaro: **J** |
| 4c | L4 · `L4Simulation` + provenienza + incertezza della deriva | 🔴 il difetto finestra/orizzonte, i due avvisi | Risk |

**Broker Detail** — stesso componente: solo verifica di scope.
**Asset Global (in %)** — selezione · correlazione · confronto perdite · rischio/rendimento ·
replay: i numeri si guardano insieme, i fix sono di **A/F**.
**Asset Detail** — parcheggiata in beta: fuori, salvo tua richiesta (ma il fix dello stress ①
la tocca: lo verifichi lì).

---

## Dopo l'approvazione

1. Scrivo il piano nel journal: `02_riskfolioIntegration/implementation_2/R5-post-merge-e-review.md`.
2. Mando al coordinator le due voci di ⑧.
3. Eseguo ① → ⑥, aggiornando il piano **dopo ogni passo** (data, *Note implementazione*,
   *Fuori pista*).
4. Handoff `FROZEN`: file condivisi toccati, voci di CHANGELOG proposte, porte `6162`/`6152`
   provate libere.
5. **Mi fermo** e apro il tempo ② con te.

---

## Avanzamento

| passo | stato |
|---|---|
| 0 · piano nel journal | ✅ 23/09/2026 |
| ⑧ · parere R17 e risposta F27 al coordinator | ✅ 23/09/2026 |
| ① · stress derivato dall'enum | ✅ 23/09/2026 · registrato nel runner (`risk-request-unit`: 2 file, 26 test) |
| ② · R12 — riproduzione sulla copia di prod | ✅ 23/09/2026 |
| ② · R12 — ciambella a due anelli | ✅ 23/09/2026 · 18 test, mutante (a) rosso sul caso R12 |
| ③ · registro (D62, D71/D72, REGISTRO, _comune) | ✅ 23/09/2026 |
| ④ · cancello i18n sul prefisso condizionale | ✅ 23/09/2026 · 17 → 24 test, HEAD rosso su 6 dei 7 nuovi |
| ⑤ · deriva dei commenti | ✅ 23/09/2026 |
| ⑥ · test del filtro broker fuori da `risk-analysis` | ✅ 24/09/2026 · 13 passed nella `6152` |
| handoff `FROZEN` del tempo ① | ✅ 23/09/2026 · checkpoint `de55b5346` + `551edffdc` (⑥) |
| tempo ② · review col developer | 🔵 aperta il 24/09/2026 · R12 in discussione |

### Passo 0 — il piano nel journal · ✅ 23/09/2026

> **Note implementazione**: materializzato dalla v2 del piano di sessione, approvata dal
> developer dopo la revisione del coordinator. La v1 (rimandata) non entra nel journal: la sua
> sostanza è tutta nella v2, e le cinque voci aggiunte sono segnate come tali nel testo.

### Passo ⑧ — parere R17 e risposta F27 · ✅ 23/09/2026

> **Note implementazione**: mandati al coordinator **prima** del codice, perché R17 decide dati
> che K sta per scrivere. **F27**: citata a `B-esecuzione.md:271`, mai scritta (la numerazione
> salta F26 → F28; nessun altro file del journal o del devWiki la nomina). Consegnato il
> contenuto rintracciabile: i tre assi, (d) contro (b) per non rifare D73, F28, F29.
> **R17**: proposta di shock come `CROWDFUND` (−0.10/−0.10) indipendentemente dal roll-up in
> `REAL_ESTATE`, con il limite dichiarato (sottostima il credito in una crisi immobiliare
> prolungata, che quegli scenari non modellano). Decide il developer.

### Passo ① — stress derivato dall'enum · ✅ 23/09/2026

> **Note implementazione**: `riskRequest.ts` espone `STRESS_ASSET_CLASSES =
> schemas.AssetType.options` e `uniformAssetClassShocks(fraction)`; `RiskAnalysisPanel.svelte`
> li usa a `:173` (editor dei secchi) e nel ramo dello shock uniforme. Verificato prima che il
> backend accetti ogni `AssetType` come secchio (`stress.py:150`, `AssetType(bucket)`): allargare
> la lista non rompe lo shock. Test scritto da `test-author`:
> `frontend/src/lib/risk/stressBuckets.test.ts`, **5 test**; `vitest` 2 path ⇒ `Test Files 2
> passed (2)`, `Tests 26 passed (26)`. Cinque mutanti, tutti col rosso nel posto giusto: A (lista
> a mano rimessa) · B (enum letto vuoto) · C (**arriva `CROWDFUND_REAL_ESTATE`**: tutto verde) ·
> D (il controllo degli estranei non può segnalarne uno) · E (il prodotto spedisce un secchio
> estraneo). `front check`: gli stessi 3 errori ereditati, zero in file risk.
>
> **⚠️ Fuori pista — `schemas.AssetType.options` invece di `ASSET_TYPES`**: stesso valore
> (`assetTypes.ts:17` è un alias), ma una dipendenza in meno da un file che K sta riscrivendo.
>
> **⚠️ Fuori pista — il ramo `:472` oggi non si esegue**: l'unico consumatore rimasto
> (`AssetRiskScenariosView:90`) passa `scope.kind: 'asset'`, quindi lo shock uniforme su un
> portafoglio è codice vivo ma non raggiunto. Riparato lo stesso: tornerebbe a sbagliare il giorno
> in cui qualcuno rimonta il pannello su un portafoglio. Il difetto **visibile** oggi era `:173`,
> che nascondeva 8 tipi dall'editor.
>
> **⚠️ Fuori pista — il controllo positivo fissava la taglia dell'enum**: nella prima stesura il
> test asseriva che la vecchia lista mancasse **esattamente** 8 tipi. R17 aggiunge un tipo → il
> test sarebbe diventato rosso **sul ramo di K** con il prodotto sano. Rilassato a *sovrainsieme*,
> con la ragione scritta nel test: *un tipo nuovo non deve far diventare rosso un controllo*.
>
> **⚠️ Fuori pista — il controllo degli estranei non aveva mai detto no**: `test-author` l'ha
> segnalato da sé; il mutante D ha provato che era vero (con il controllo spento, **nessun** altro
> test diventava rosso). Aggiunto il controllo positivo sugli estranei.

### Passo ② — R12, riproduzione · ✅ 23/09/2026

> **Note implementazione**: copia di prod dalla snapshot (`004`, nessun marcatore), server
> `6162`, DB verificato dal log (`/private/tmp/librefolio-r2-risk-prodcopy/sqlite/app.db`), login
> `alfy`. Asset del developer: `ETF 8 · CROWDFUND 4 · ETF_STOCK 1 · ETF_BOND 1 · BOND 1`.
> Payload reale di `allocation_by_type`:
> `ETF 49.79 · CROWDFUND 30.55 · BOND 16.13 · ETF_STOCK 3.53 · Liquidity 0.01`.
> **Diagnosi confermata**: `ETF_STOCK` è l'unico membro della famiglia Azioni → singoletto →
> colore puro, nessun «↳». E `ETF_BOND` non compare: nessuna posizione aperta, quindi anche
> Obbligazioni è un singoletto. Screenshot prima/dopo in `session-state/files/r12-*.png`.
>
> 📌 **Un dato per la review, non un difetto**: 8 asset su 15 sono `ETF` generico, il residuo
> «contenuto misto». Se sono ETF azionari o obbligazionari, riclassificarli li porterebbe nelle
> famiglie giuste. È una scelta sui dati del developer, non sul codice.

### Passo ② — R12, ciambella a due anelli · 🔵 codice ✅ 23/09/2026

> **Note implementazione**: costruttore puro nuovo `charts/allocationRings.ts` (additivo:
> `allocationHierarchy.ts`, condiviso con I, **non è stato toccato**). `AllocationPieChart.svelte`
> in `mode='type'`: se nessuna famiglia ha sottotipi disegna **l'anello di sempre, invariato**;
> altrimenti tre serie. Misurato sulla copia di prod:
>
> ```
> archi base vs somma dei membri   Δ 0.0000° su tutte e cinque le famiglie
> tooltip dell'arco esterno        «ETF azionario: 3.52% · ≈ X € EUR · ↳ Azione 3.5%»
> transizione nella stessa istanza anelli → uno → anelli: 3 → 1 → 3 serie, nessuna orfana
> errori di pagina                 nessuno
> front check                      gli stessi 3 ereditati, zero nei file toccati
> ```
>
> **⚠️ Fuori pista — tre serie, non due**: due anelli contigui disegnano sempre una **cucitura
> bianca** fra loro, e la decisione del developer è che le famiglie senza sottotipi restino
> *piene su un solo livello*. Quindi l'anello base è **a tutto spessore**, l'anello dei membri gli
> si **sovrappone** sulla banda esterna (trasparente dove la famiglia non è divisa), e una terza
> serie muta porta l'icona del tipo base sulla banda interna, dove la sovrapposizione non la copre.
>
> **⚠️ Fuori pista — `padAngle: 0` in modalità anelli**: il padding sottrae un grado **per ogni
> arco**, e i due anelli non hanno lo stesso numero di archi: con il padding scivolerebbero.
> Conseguenza visiva da giudicare in review: niente spazio di 1° fra le fette, solo il bordo.
>
> **⚠️ Fuori pista — legenda non selezionabile in modalità anelli**: spegnere una voce toglierebbe
> un arco da un anello e non dall'altro, rompendo l'unica ragione per cui combaciano. È un cambio
> di comportamento, da confermare in review.
>
> **⚠️ Fuori pista — `setOption` fonde le serie per indice**: tornando da tre serie a una, le due
> vecchie resterebbero a schermo. `replaceMerge: ['series']` **solo** quando il layout cambia; ogni
> altra ricostruzione fonde come prima.
>
> **⚠️ Fuori pista — il filtro broker ha una semantica che non conoscevo**: da «tutti», un clic
> **seleziona solo quel broker** invece di toglierlo. La prima sonda ha quindi scelto il broker che
> ha ancora l'ETF azionario, e sembrava che la transizione fallisse. Non era il codice: era la mia
> sonda.
>
> **⚠️ Fuori pista — il percorso veloce non è stato esercitato dal vivo**: il grafico «adesso» è
> alla data finale, e i preset di periodo spostano solo l'inizio → i valori non cambierebbero e la
> sonda passerebbe provando nulla. Il percorso veloce è quindi legato da un **contratto sul
> sorgente** nel test, col suo controllo positivo.
>
> 🟡 **Per la review estetica**: su una famiglia di 3,5 % `hideOverlap` lascia visibile **una sola**
> icona (quella dell'ETF, sull'anello esterno); l'icona «Azione» della banda interna non ci sta.

### Passo ③ — registro · ✅ 23/09/2026

> **Note implementazione**: `04-decisioni-e-questioni-aperte.md` — **D62** annotata senza
> riscriverla (corretta al passo 10 di B → decisione (d) su `SimpleSelect`; riaperta dalla review
> del 22/09 come R15; owner **K**; F27 citata e mai scritta), **D72** annotata (attivata da R12:
> la premessa di G misurava il gruppo più grande, non il singoletto), e un rimando sotto il
> paragrafo «Vince il terzo», che altrimenti un lettore prenderebbe per lo stato attuale.
> `REGISTRO.md` — **R2-153…R2-157**, che *rimandano* a `09_…md` invece di ricopiarlo:
> R2-153 il rimando stesso · R2-154 la diagnosi di R12 · R2-155 lo stress a lista scritta a mano ·
> R2-156 F27 fantasma · R2-157 R17 contro il gate enum↔secchi. `_comune.md` — sezione del round 5:
> Ⓢ corsie `6162`/`6152` e copia dallo snapshot · Ⓣ catena Alembic `004` e divieto di `005` ·
> Ⓤ `api sync` in-process · Ⓥ tabella dei proprietari.
>
> **⚠️ Fuori pista — la tabella di avanzamento era rimasta a ⏳**: il passo ③ è stato eseguito
> prima del ④, ma la riga e questa sezione sono state scritte solo al ⑤. È esattamente la regola
> «dopo ogni passo» non rispettata: recuperato qui, senza cambiare le date.

### Passo ④ — cancello i18n sul prefisso condizionale · 🔵 codice ✅ · misura ✅ 23/09/2026

> **Note implementazione**: `scripts/i18n_usage.py` — `_CONDITIONAL_DECL` riconosce
> `const|let NOME = [$derived(] cond ? 'a' : 'b'` con **entrambi** i rami letterali;
> `_resolvable_names` produce la tabella dei nomi del file, ora `dict[str, list[str]]` (un `const`
> dà un valore, un condizionale letterale due), e `_expand` espande il template su tutti. La causa
> non era «il template comincia con `${`»: `SimulationProvenance` ha la stessa forma con
> `const NS` e le sue 31 chiavi erano già vive. Era il **condizionale**.
>
> ```
> diff degli ELENCHI (non dei totali)   morte 422 → 418
>   escono esattamente                  risk.betaBanner.{title,description}
>                                       risk.betaBanner.simulation.{title,description}
> non verificate                        41 → 41, elenco identico
> negativo  risk.assetSet.panelTitle    resta morta (orfano vero, di F)
> invariante l4.provenance.*            0 fra le morte, prima e dopo
> ruff                                  pulito
> test del cancello                     17 passed (invariati: usano solo l'API pubblica)
> ```
>
> **⚠️ Fuori pista — `black --check` fallisce anche su HEAD**: il file aveva già 30 righe che black
> riformatterebbe. Non l'ho riformattato (sarebbe riscrivere righe altrui, Ⓟ); ho solo portato le
> **mie** righe allo stile del file (espressione su una riga), e misurato: HEAD 30 righe · mio 30
> righe → nessun debito aggiunto.
>
> 🔵 test-author aggiunge a `test_i18n_usage_gate.py` i casi del condizionale (entrambi i rami ·
> negativo sullo stesso namespace · `const` oltre a `let $derived` · ramo non letterale non
> indovinato · regressione del `const` singolo), con due mutanti.

### Passo ⑤ — deriva dei commenti · ✅ 23/09/2026

> **Note implementazione**: `L4Replay.svelte:47` e `L4Shock.svelte:46` ora citano
> `formatScopedCurrencyAmount` per **simbolo**, senza `:163`. Nessun'altra citazione per numero
> di riga di `riskAnalysisHelpers.ts` sotto `src/lib`.
>
> **⚠️ Fuori pista — prima di togliere il numero ho controllato la frase**: il commento afferma che
> il predicato è *lo stesso* di `formatScopedCurrencyAmount`. Togliere solo la riga avrebbe
> lasciato un'affermazione con l'aria di essere stata verificata. Regge: `scopeKind !==
> 'portfolio'` nel file di J, `scopeKind === 'portfolio'` nei due consumatori.

### Passo ⑥ — test del filtro broker · ✅ 24/09/2026

> **Ordine confermato dal coordinator (23/09)**: ① F aggiunge il test in `risk-lab.spec.ts`, lo fa
> girare verde nella sua lane di suite e manda al coordinator il **nome esatto**; ② il coordinator
> mi dà il via, **non prima**; ③ rimuovo `risk-analysis.spec.ts:1335`, faccio girare `risk` nella
> `6152` (14 → 13) e aggiorno la `desc=` del catalogo solo per sottrazione. `:1397` resta mio.
> **Integrazione**: il ramo di F con il test entra nel target *non dopo* il mio — lo tiene il
> coordinator.
>
> ~~Misurato in sola lettura: nel worktree di F `risk-lab.spec.ts` **non** contiene ancora il test.~~
> **Falso, e la misura non provava nulla**: vedi il Fuori pista sotto.
>
> **Note implementazione**: via del coordinator il 24/09 alle 09:31, dopo il commit del checkpoint
> (`a5f6776aa` … `de55b5346`) e con la condizione di F soddisfatta — il suo test
> *«broker preset: loads exactly that broker's holdings and lets no amount through, its empty option
> keeps the selection, and a chip removed by hand comes back through the picker»*
> (`risk-lab.spec.ts:2478`) verde nella sua lane, 16/16. Il suo test contiene il mio: stessi controlli
> su pannello, banner, heatmap, rimozione e ritorno di un chip; sul filtro broker verifica **esattamente**
> le posizioni di quel broker, dove il mio chiedeva almeno una. Rimosso **per titolo**, non per numero
> di riga, con uno script che rifiuta di scrivere se un'ancora non è unica.
>
> ```
> risk-analysis.spec.ts    −96 righe, 0 aggiunte: il test (62) + i due helper locali che usava solo
>                          lui (brokerWithHoldings, selectedAssetIds: 34, non esportati)
> test nello spec          14 → 13 (più il describe) · :1397, tab broker su Broker Detail, resta
> desc= del runner         invariata: «Portfolio-level risk on Dashboard and Broker Detail» non cita
>                          Asset Global, non c'è niente da sottrarre
> tsc -p tsconfig.e2e      4 errori, identici su HEAD, nessuno in e2e/portfolio
> prettier                 pulito
> suite risk, lane 6152    13 passed (26.5s), exit 0 · 6152 libera prima e dopo · il log conferma
>                          porta 6152 e dati /private/tmp/librefolio-r2-risk, nessuna traccia di 6041
> ```
>
> **⚠️ Fuori pista — la misura del 23/09 cercava il nome vecchio**: alle 16:1x ho cercato
> `broker holdings` nello spec di F e ho ottenuto zero, ma F ha scritto il test con un titolo nuovo
> (*«that broker's holdings»*, con l'apostrofo, fra virgolette doppie). Zero su una ricerca per il nome
> sbagliato non dice che il test manca: dice che la sonda non poteva trovarlo. Me ne sono accorto
> leggendo i test nuovi dello spec invece di rifare la stessa ricerca, e l'ho corretto col coordinator
> alle 17:00. Quando il test sia arrivato non lo so.
>
> **⚠️ Fuori pista — i due helper**: il perimetro di ⑥ era «il test e nient'altro». Ho rimosso anche
> `brokerWithHoldings` e `selectedAssetIds` perché, tolto il test, restavano codice morto creato dalla
> mia modifica, nello stesso file. Non ho toccato le copie **esportate** con gli stessi nomi in
> `risk-mocks.ts` (modulo condiviso, `70a11dfc7`): oggi non le importa nessuno, ma non è il mio passo.

### Catalogo del runner e orfani — 23/09/2026

> **Note implementazione**: `_frontend_portfolio.py`, solo aggiunta — `stressBuckets.test.ts`
> nel comando di `risk-request-unit` e in coda a `desc=`/`tests=`. Via runner, nella lane di suite:
> `Test Files 2 passed (2) · Tests 26 passed (26)`. `allocationRings.test.ts` si registra in
> `allocation-unit` quando esiste.
>
> **⚠️ Fuori pista — `check-orphans` ne trova 6, e 5 non sono miei**: prima della registrazione
> `src/**/*.test.ts` aveva 6 orfani; uno era `stressBuckets.test.ts`. Gli altri cinque vengono da due
> commit di privacy del 22/09 — `b66e93003` (`privacyStore`, `privacyStoreSsr`, `currencyFormat`,
> `maskable`) e `9a6dd2015` (`moneyRenderSites`) — quindi dal perimetro di **J**. Non li registro:
> segnalati al coordinator. Il più istruttivo è l'ultimo: **il cancello dei punti di resa non
> registrati non è registrato**. Verificato prima di scriverlo — `check-orphans` guarda solo i
> percorsi espliciti, e una cartella li includerebbe: nessuna azione del runner cita i cinque file
> né le loro cartelle, e nessun workflow CI lancia vitest. Girano **solo** con un
> `npm run test:unit` fatto a mano.

### Passo ② — R12, i test · ✅ 23/09/2026

> **Note implementazione**: test-author ha scritto `charts/__tests__/allocationRings.test.ts`
> (644 righe, 18 test): sottotipo solitario sul **payload vero** del developer, famiglie divise e
> non divise, «Liquidità» come famiglia a sé, invariante di allineamento, quando disegnare due
> anelli, tavolozza corta, e un **contratto sul sorgente** del percorso veloce col suo controllo
> positivo. Il blocco R12 comincia con una **barriera**: sotto D71 da solo `ETF_STOCK` è un
> gruppo di uno, profondità 0, colore di tavolozza — cioè l'ingresso riproduce il difetto prima
> che il test ne misuri la cura. La cura è asserita in tre modi: colore diverso da quello della
> famiglia · ΔL ≥ 15 sulla stessa tinta (Δh ≤ 1) · esattamente `shadeForDepth(famiglia, 1)`.
>
> ```
> vitest (da frontend/)       allocationRings + allocationHierarchy   Test Files 2 · Tests 57
> runner allocation-unit      colors + allocationHierarchy + allocationRings   Test Files 3 · Tests 86
> mutante (a), rifatto da me  ombra per POSIZIONE nella famiglia invece che per rango
>                             → 2 falliti / 16 su 18: il test R12, su entrambe le tavolozze
> mutante (b), del test-author   percorso veloce `series: [{data}]`, riformattato a 40 colonne
>                             → rosso solo il controllo sul sorgente vero
> ```
>
> Il contratto sul sorgente regge la riformattazione di prettier: provato dal test-author a 300,
> 120, 80 e 40 colonne.

### Passo ④ — i test del cancello · ✅ 23/09/2026

> **Note implementazione**: test-author ha aggiunto a `test_i18n_usage_gate.py` la classe
> `TestConditionalPrefix` (+72 −0, 7 test): entrambi i rami sono prova · una chiave sotto nessun
> ramo resta morta (con barriera) · anche con `const` in un `.ts` · un ramo non letterale **non**
> viene indovinato (con controllo: la coppia letterale nello stesso file si risolve) · il `const`
> singolo regge il cambio di tipo in `list`. La `desc=` del cancello in `_backend_utils.py` ora
> nomina la forma nuova (inserzione, niente riordino).
>
> ```
> test del cancello           17 → 24 passed · via runner (utils gate-i18n-usage) 24 passed
> sorgente di HEAD, rifatto da me in /tmp   6 dei 7 nuovi ROSSI; verde solo il `const` singolo,
>                                           che HEAD già sapeva risolvere — giusto così
> sorgente attuale, stessa copia            25 passed (24 + il guardiano del modulo caricato)
> ```
>
> 🟡 **Limite noto, non corretto**: `_CONDITIONAL_DECL` riconosce anche
> `const msg = $_(cond ? 'a' : 'b')` e registra `msg` come prefisso, benché contenga testo tradotto.
> Pesa solo se un template di chiave comincia con `${msg}`: **oggi nessuno** — lo prova il diff
> degli elenchi del passo ④, dove si muovono solo le quattro chiavi del banner. È un errore che
> tenderebbe al verde, quindi lo scrivo qui invece di lasciarlo alla memoria.
>
> **⚠️ Fuori pista — il mio guardiano era rosso, e aveva torto lui**: nella copia in `/tmp` avevo
> aggiunto un test che verifica di aver caricato il modulo mutante, e falliva in **entrambe** le
> corse. Causa: su macOS `/tmp` è un link a `/private/tmp`, e `__file__` riporta il percorso
> risolto. Il modulo caricato era la copia. Prima di credere ai sei rossi ho letto il messaggio
> del guardiano, non quello dei test; poi l'ho corretto con `realpath` e rifatto le due corse.
> Una sonda che sbaglia verso il rosso si denuncia da sola.
>
> **⚠️ Fuori pista — e una che sbagliava verso il verde**: per sapere se i 19 errori ruff sui file
> del runner fossero miei ho filtrato l'uscita per codice, su HEAD e sul mio: **«nessuno» da
> entrambi i lati**. Il filtro non combaciava col formato di ruff. L'ho visto solo perché
> contraddiceva il «Found 19 errors» di pochi secondi prima. Rifatto con `--output-format concise`:
> 18 `E701` + 1 `PLC0415`, **identici su HEAD** — ereditati. È la forma della regola di ieri: una
> misura che dà l'atteso chiude la pratica, e va creduta la contraddizione, non la sonda.

### Cancelli finali del tempo ① — 23/09/2026

> ```
> front check           3 errori, gli stessi ereditati (TransactionFormModal.test.ts:787,819 ·
>                       ToolExecutionMetrics.svelte:44); zero errori e zero warning nei miei file
> prettier --check      i 7 file frontend toccati: puliti. AllocationPieChart era pulito su HEAD e
>                       il debito era mio (1 espressione, 8 righe): riformattato solo quello
> ruff                  i18n_usage.py, test del cancello, _backend_utils.py: puliti.
>                       _frontend_portfolio.py: 19 ereditati, identici su HEAD
> black                 nessun debito aggiunto: HEAD e mio con le stesse righe da riformattare
>                       (i18n_usage 30 · test del cancello 12 · _frontend_portfolio 121 · _backend_utils 0)
> check-orphans         6 → 5; i cinque rimasti sono di J (privacy), segnalati al coordinator
> front build           bundle 16:31:26, più recente dell'ultimo sorgente toccato (16:17:54)
> ```

### Handoff `FROZEN` del tempo ① — 23/09/2026, ⑥ escluso

> **Stato**: HEAD `f1047f766`, 16 percorsi sporchi (12 modificati, 4 nuovi), tutti nel
> checkpoint; sei commit proposti in `/tmp/libreFolio_commits/` con l'ordine e i percorsi esatti
> in `ORDER.md` — l'unione dei percorsi coincide con `git status` (16 = 16). Nessun hook di
> pre-commit attivo. `dev_release2` è a `55bf7d163` (+1 commit su `09_feedbackJobs/`, nessun file
> in comune): nessun aggiornamento di baseline necessario.
>
> **File condivisi toccati**: `scripts/test_runner/_frontend_portfolio.py` (due registrazioni, solo
> aggiunta) · `scripts/test_runner/_backend_utils.py` (una frase inserita nella `desc=` del
> cancello). Cataloghi i18n **non toccati**, `CHANGELOG.md` **non toccato**.
>
> **Runtime**: server `6162` spento (PID 58936 terminato), `6162` e `6152` libere, nessun processo
> sulla copia. Copia **rinfrescata** dalla snapshot (`004`, niente marcatore, `app.db`
> byte-identico); quella su cui ho lavorato è in `.prev-20260923-163327`. Bundle ricostruito dopo
> l'ultimo sorgente. Al via del tempo ② basta accendere il server: i dati sono i suoi.
>
> **Voci di CHANGELOG proposte** (le scrive il coordinator), `### 🐛 Fixed`:
> - *Allocation by type* — ETF subtypes (e.g. an equity ETF) are drawn on a second ring, inside
>   the base type they hold, instead of looking like a separate category. Families without
>   subtypes stay whole on one ring.
> - *Asset Detail · stress test (beta)* — the per-type shock editor offers every asset type (it
>   listed 9 of 17), so ETF subtypes and crowdfunding can be shocked too.
>
> Non da CHANGELOG: il cancello i18n, i commenti, il runner.
>
> **Resta aperto**: ⑥ (via del coordinator dopo F) · i 5 test di privacy non registrati (di J) ·
> il tempo ②.

---

## Fuori pista rimasti fuori dal checkpoint del tempo ① — 23–24/09/2026

Il journal era dentro il checkpoint e quindi `FROZEN`: questi li porto qui all'apertura del tempo ②.

> **⚠️ Credenziali in file versionati** (23/09): avevo trascritto utente e password del developer in
> `_comune.md` e in questo piano, copiandole dal piano di sessione. Il coordinator ha bloccato il
> checkpoint; sostituite con «fornite dal developer, non trascritte in file versionati» e un segnaposto
> nel `reset`; `grep` sui 16 percorsi → zero. Segnalati due fatti fuori perimetro: i ref di checkpoint
> dell'app (solo locali, 0 sul remote) e una stringa quasi identica già pubblica su `origin/main` dal
> 31/07 → rimedio del developer: cambiare la password.
>
> **⚠️ F2 e C2 generalizzati oltre la misura** (23/09): avevo scritto al coordinator che valevano anche
> per A/F. A ha misurato il contrario: su `asset_set` l'asset senza prezzi è escluso, non convertito in
> liquidità, e la simulazione non è offerta. Avevo esteso a un perimetro la conclusione letta nel ramo
> dei perimetri pesati.
>
> **⚠️ La premessa della griglia presa dalla doc** (23/09): avevo scritto che, col BOND dentro, la
> griglia congiunta fosse di giorni di borsa, fidandomi di `observed-annualization.en.md:94-95`
> («intersected»). Il codice fa l'**unione** delle date fresche (`series_preparation.py:236-289`) e
> justETF scrive i weekend come righe fresche → f ≈ 365. C2 è sceso a 🟡 latente; C3 è diventato
> «3 settimane ovunque sui tuoi dati», tranne il BOND da solo (misura del coordinator).
>
> **⚠️ Un fatto vero altrove scritto come vero qui** (24/09): il messaggio del commit 7 diceva
> «risk-lab.spec.ts now owns…», falso a quel commit nel mio ramo (il test di F è sul ramo di F). Il
> coordinator ha corretto corpo e oggetto; la mia proposta di oggetto («…risk-lab covers») ripeteva lo
> stesso errore. Regola tenuta: in un messaggio di commit, ogni affermazione su un altro file o ramo
> va nel corpo con la sua condizione, mai nell'oggetto.

---

## Tempo ② — review col developer · 🔵 aperta il 24/09/2026

Schede: [`R5-tempo2-schede.md`](R5-tempo2-schede.md). Server di review sulla copia di prod, `6162`,
copia byte-identica alla snapshot al momento dell'avvio.

### R12 — la ciambella a due anelli · ❌ bocciata così com'è, decisione aperta

> **Esito della review (24/09, due screenshot del developer)**: *«è ancora una torta unica e c'è solo
> un'icona per quell'asset e anzi, in base a dove tocco nel tooltip mi si apre o azione o etf, direi
> che non è quello che volevo»*.
>
> **Diagnosi** — i due anelli ci sono, ma tre scelte mie nascondono proprio il secondo livello:
> 1. **nessuno stacco fra gli anelli** (anello base a tutto spessore + sovrapposizione sulla banda
>    esterna, scelto per evitare la «cucitura bianca»): da fuori è una fetta sola;
> 2. **l'icona del membro copre la banda esterna** sulla fetta piccola (3,5 %): si legge una fetta
>    «Azione» con sopra l'icona di un ETF;
> 3. **il tooltip cambia con la banda** (interna = famiglia, esterna = sottotipo), ma le bande non si
>    vedono, quindi sembra casuale.
>
> Confermato anche R12d dal suo screenshot: `ETF azionario: 3.48%` accanto a `↳ Azione 3.5%`, due
> arrotondamenti della stessa quantità (la famiglia è fatta solo di quel membro).
>
> **Decisione aperta, prima di toccare il codice**: *quale famiglia per l'ETF azionario?*
> **A — per contenuto** (dentro «Azione»: è ciò che è implementato, dal principio del modello e dalla
> nota del coordinator «non a ETF») oppure **B — per veicolo** («ETF» famiglia, dentro i sottotipi,
> come l'albero del selettore di K). Mockup delle due, sui suoi numeri, con **anelli staccati**, anello
> esterno più sottile e **didascalie invece delle icone** sul sottile: nel piano di sessione,
> `files/r12-proposte-A-B.png` (+ `.html`), non versionati.
>
> **⚠️ Fuori pista — i numeri si muovono sulla copia**: ieri il tooltip leggeva `3.52% · ≈ X €`,
> oggi `3.48% · ≈ X €` sulla copia rinfrescata. Lo scheduler dei prezzi gira anche sul server di
> review e la torta è alla data finale. Spiega anche lo scarto `3.53`/`3.52` di ieri fra payload e
> tooltip: letture in momenti diversi, non un difetto di arrotondamento.
>
> **Decisione del developer (24/09, 10:29)**: *«la proposta B è quello che mi aspettavo»* → **per veicolo**.
>
> **Note implementazione (24/09)** — la torta di B, in codice:
> - `charts/allocationFamily.ts` (nuovo): la famiglia è il veicolo, `isEtfSubtype(t) ? 'ETF' : t`. Consuma
>   l'elenco di **K** (`ETF_SUBTYPES`/`isEtfSubtype`, già esportati, nessuna modifica nel ramo di K):
>   nessuna seconda mappa. `primaryAssetType` (contratto K2, per contenuto) **non** è toccato.
> - `charts/allocationRings.ts`: docstring riallineata; nuova funzione pura `buildAllocationRingData`, che
>   fissa le regole su cui legenda e tooltip si appoggiano: **ogni arco porta il nome della famiglia**
>   (un clic in legenda nasconde la famiglia su entrambi gli anelli), la **didascalia** dice che cosa è
>   l'arco (il membro generico diventa «ETF generico», nuova chiave `dashboard.allocationGeneric` nelle 4
>   lingue via `dev.py i18n`), **un solo arrotondamento** per membro e famiglia.
> - `AllocationPieChart.svelte`: due serie invece di tre; anelli **staccati** (interno 25–45 %, esterno
>   49–55 % sulla stessa estensione di prima), esterno con didascalie fuori e linee guida, bordo bianco al
>   posto di `padAngle`, icone di famiglia solo su fette ≥ 5 % (`minShowLabelAngle: 18`), legenda di nuovo
>   cliccabile, tooltip col genitore a due decimali.
>
> ```
> sui dati del developer (copia di prod, 6162)
>   interno   ETF 53.05 · Crowdfunding 30.77 · Obbligazione 16.18 · Liquidità 0.01
>   esterno   ETF generico 49.56 + ETF azionario 3.49 = 53.05, riempitivi senza tooltip
>   tooltip   «ETF azionario: 3.49% · ≈ X € · ↳ ETF 53.05%»
>   legenda   clic su «ETF» → spariscono insieme l'arco interno e i due esterni; anelli allineati
>   errori di pagina: nessuno · front check: gli stessi 3 ereditati, zero nei miei file · prettier pulito
> test      85/86: rosso solo il contratto sul sorgente del percorso veloce, che cercava tre id (ora due)
> ```
>
> **⚠️ Fuori pista — un'icona di troppo**: alla prima prova l'icona della Liquidità (0,01 %) veniva
> disegnata a cavallo delle fette vicine. Soglia del 5 % presa dal mockup approvato.
>
> **In attesa**: approvazione della **lista dei test** da parte del developer, poi test-author.
> **Da comunicare al coordinator**: il grafico storico di I raggruppa ancora per contenuto; il futuro
> `CROWDFUND_REAL_ESTATE` di K avrà bisogno di un genitore-veicolo esposto da K.
>
> **Review del developer sul risultato (24/09, 10:45)**: *«mi piace tutto quello che hai fatto»* — tutto
> **approvato, lista dei test compresa**, con una richiesta: nel tooltip dell'ETF azionario c'era solo
> l'icona ETF, *«mi aspettavo le 2 icone come le abbiamo descritte, o almeno le 2 affiancate»*.
>
> **Note implementazione — l'icona doppia nel tooltip**: la descrizione è quella di R16 (*«la seconda
> icona piccola, leggermente sovrapposta alla principale»*), passata a **K**, che non l'ha ancora
> realizzata; il mio piano fissava già che K **non** cambia `getAssetTypeIconUrl()` e che la seconda icona
> arriva con una funzione nuova. Per non far aspettare il developer e senza una seconda mappa, la compongo
> da due export **già esistenti** di K: `getAssetTypeIconUrl()` (veicolo) + `primaryAssetType()` (contenuto
> → sua icona). Funzione pura `allocationTypeIcons()` in `charts/allocationFamily.ts`: `ETF_STOCK` → icona
> ETF + icona azione; quando il contenuto ripeterebbe l'icona principale (`ETF`, `ETF_MONETARY`, i tipi
> base) una sola. Resa come R16: la principale 14 px, quella del contenuto 10 px in basso a destra,
> leggermente sovrapposta, con un alone nel colore di sfondo del tooltip (chiaro e scuro). Verificata con
> uno zoom sullo screenshot della copia: etichetta ETF + edificio col $.
> **Quando R16 consegnerà l'icona composita di K, il tooltip dovrà consumare quella.**
>
> **Coordinamento (24/09)**: K conferma `assetTypeFamily()` nel suo ramo (sottotipi ETF → `ETF`,
> `CROWDFUND_REAL_ESTATE` → `CROWDFUND`, stabile per il round). All'integrazione `allocationFamily` diventa
> `assetTypeFamily(type)`: una riga. La normalizzazione è la stessa (maiuscolo, vuoto → `OTHER`), quindi
> `'Liquidity'` → `'LIQUIDITY'` prima e dopo; l'unico `===` su chiavi di famiglia confronta due uscite del
> resolver. Caso `'Liquidity'` esplicito nei test, come chiesto dal coordinator.
>
> 🔵 **test-author** scrive i test della lista approvata (+ icone del tooltip, + `'Liquidity'`).
>
> **Test (24/09)** — test-author sulla lista approvata (+ `'Liquidity'` esplicito, + icone del tooltip):
>
> ```
> allocationRings.test.ts aggiornato · allocationFamily.test.ts nuovo · solo questi due file toccati
> vitest (da frontend/): rings + family + hierarchy + colors      Test Files 4 · Tests 114
> runner allocation-unit, lane 6152 (libera prima e dopo)         Test Files 4 · Tests 114
> mutanti del test-author   a nome proprio sugli archi esterni 8/34 · b didascalia generica 1/34 ·
>                           c totale a un decimale 1/34 · d raggruppamento per contenuto 5/46 ·
>                           e icona di contenuto sempre presente 4/12 — tutti rossi
> mutante (a) rifatto da me, indipendente dal suo harness: 8 falliti / 26 su 34, esattamente i test della legenda
> check-orphans             5, gli stessi di J; allocationFamily.test.ts registrato in allocation-unit
> ```
>
> Fuori lista, tenuti: il controllo che lo stub del veicolo coincida con `allocationFamily`, il vecchio
> test «ombra per rango» (il dato del developer ha un ETF generico, senza il test l'affermazione
> resterebbe scoperta), un secondo test d'arrotondamento. Da proporre: un test che `amount` sia la somma
> degli importi dei membri (il tooltip ci conta). Quando `CROWDFUND_REAL_ESTATE` entrerà nell'enum (R17
> di K), due test diventeranno rossi **apposta**: è il segnale per passare ad `assetTypeFamily`.
>
> **⚠️ Fuori pista — il server di review è morto da solo**: alle 11:11 l'ultima riga (lo scheduler dei
> prezzi), poi nessun messaggio di chiusura. Processo terminato di colpo, causa non scritta nel log: non
> la indovino. Riavviato sulla stessa copia (i dati del developer + i prezzi di oggi scritti dallo
> scheduler); all'avvio `dev.py server` ha ricostruito il frontend perché i due file di test erano più
> recenti del bundle. Verificata di nuovo la torta: due serie, tooltip corretti, nessun errore.
