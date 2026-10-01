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
| R12d | tooltip: membro a due decimali, famiglia a uno (`a,bc%` accanto a `Azione a,b%`) | due arrotondamenti diversi sulla stessa riga |
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
| handoff `FROZEN` del tempo ① | ✅ 23/09/2026 · checkpoint `393a3d118` + `7d6c9a60c` (⑥) |
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
> `ETF <quota> · CROWDFUND <quota> · BOND <quota> · ETF_STOCK <quota> · Liquidity <quota>`.
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
> tooltip dell'arco esterno        «ETF azionario: <quota>% · ≈ X € EUR · ↳ Azione <quota>%» (membro a due decimali, famiglia a uno)
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
> (`a5f6776aa` … `393a3d118`) e con la condizione di F soddisfatta — il suo test
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
> Confermato anche R12d dal suo screenshot: il membro a due decimali accanto a `↳ Azione` a uno, due
> arrotondamenti della stessa quantità (la famiglia è fatta solo di quel membro).
>
> **Decisione aperta, prima di toccare il codice**: *quale famiglia per l'ETF azionario?*
> **A — per contenuto** (dentro «Azione»: è ciò che è implementato, dal principio del modello e dalla
> nota del coordinator «non a ETF») oppure **B — per veicolo** («ETF» famiglia, dentro i sottotipi,
> come l'albero del selettore di K). Mockup delle due, sui suoi numeri, con **anelli staccati**, anello
> esterno più sottile e **didascalie invece delle icone** sul sottile: nel piano di sessione,
> `files/r12-proposte-A-B.png` (+ `.html`), non versionati.
>
> **⚠️ Fuori pista — i numeri si muovono sulla copia**: ieri il tooltip leggeva `<quota> · ≈ X €`,
> oggi `<quota'> · ≈ Y €` sulla copia rinfrescata. Lo scheduler dei prezzi gira anche sul server di
> review e la torta è alla data finale. Spiega anche lo scarto di un centesimo di punto di ieri fra payload e
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
>   interno   ETF <quota> · Crowdfunding <quota> · Obbligazione <quota> · Liquidità <quota>
>   esterno   ETF generico <quota> + ETF azionario <quota> = la quota interna dell'ETF, riempitivi senza tooltip
>   tooltip   «ETF azionario: <quota>% · ≈ X € · ↳ ETF <quota>%», stessa precisione
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

### R12 — dopo il checkpoint `0a22b2ab3` → `8afe5b31c` → `3a90c6dcc` (24/09)

> **Note implementazione — l'icona del tooltip si adatta alla composita di K**: con la D-K2 di K,
> `getAssetTypeIconUrl('ETF_STOCK')` restituirà una **composita statica** (ETF con l'azione già
> sovrapposta); sovrapporci di nuovo il contenuto lo mostrerebbe due volte (reperto del coordinator).
> Regola in `allocationTypeIcons`: se l'icona del tipo è diversa da quella del suo contenitore
> (`allocationFamily`) è già la composita → nessuna sovrapposizione; altrimenti si sovrappone il contenuto.
> Oggi il comportamento è identico (46/46 test invariati); dopo K niente doppio contenuto, senza
> modifiche all'integrazione. ⚠️ Dipende dallo scambio `allocationFamily` → `assetTypeFamily`: senza, un
> futuro `CROWDFUND_REAL_ESTATE` avrebbe per contenitore se stesso. I due punti stanno insieme nella lista
> d'integrazione del coordinator.
>
> **Coordinamento**: l'icona del manuale in `RiskLevelSection` la scrive **F** (prop facoltativa); io la
> collego ai miei punti di chiamata dopo aver fuso il ramo di F. Se il developer approva la frase unica
> al posto di «Parziale», toccherò il blocco di stato di `RiskLevelSection` solo dopo F.
>
> **Da proporre al developer**: un test che simula la composita di K (`vi.mock` di `getAssetTypeIconUrl`)
> e verifica che il tooltip mostri solo quella; mutante: senza il confronto col contenitore → rosso.

### Dati personali nei file versionati — 24/09/2026

> **⚠️ Fuori pista — pesi e importi reali del developer nel journal**: nelle note di R12 e nelle schede
> del tempo ② avevo trascritto le quote reali del suo portafoglio per tipo e alcuni importi in euro letti
> dalla copia di prod; nel test della torta le fixture riproducevano le stesse quote. Insieme permettevano
> di risalire al patrimonio. Trovato dal coordinator dopo il checkpoint `3a90c6dcc` (il controllo del
> tempo ① cercava la password, non i valori finanziari). La regola dell'agente di lane lo vietava già
> («financial values … identifying user data»).
>
> **Decisione del developer**: dalla storia locale si tolgono **solo gli importi in euro** (6 righe, in
> `393a3d118` e `3a90c6dcc` — prima della riscrittura `de55b5346` e `cdf89f1b3`; la riscrittura la prepara il coordinator su un clone in `/tmp`, la lancia il
> developer); le **percentuali possono restare**. Nel working tree ho comunque messo segnaposto
> (`<quota>`, `≈ X €`) su pesi e importi — innocui, e riscritte le osservazioni che se ne servivano
> (per R12d: «membro a due decimali, famiglia a uno») — e test-author ha rifatto le fixture di
> `allocationRings.test.ts` con valori **sintetici** della stessa forma (4 file · 114 test; il mutante
> del totale a un decimale ora fa rosso su entrambi i test d'arrotondamento). L'importo rimasto nel test
> è sintetico (`value * 1000`, un portafoglio fittizio da centomila).
> **Regola tenuta**: i valori veri del developer stanno solo nella chat e nei file di sessione, mai nei
> file versionati; nei file si scrivono segnaposto o grandezze relative senza valore.
>
> **Da segnalare, non mio**: `REGISTRO.md:235` (R2-03, `da303e211`, 18/09) contiene un importo, già su
> `origin`: lo porta il coordinator al developer.
>
> **⚠️ Fuori pista — `npx --no-install` non protegge**: l'avevo passato a test-author come cautela; il
> coordinator ha verificato che interroga comunque il registry. Da ora solo `node_modules/.bin/…` o
> `npm run`. I miei `npx prettier/vitest/tsc` di oggi usavano binari locali: nessun download mio.

### R12 — il test dell'icona composita (punto 5 del developer) · ✅ 24/09/2026

> **Note implementazione**: test-author ha aggiunto a `allocationFamily.test.ts` un blocco che simula le
> icone composite di K (D-K2): `getAssetTypeIconUrl('ETF_STOCK')` restituisce una composita, tutto il
> resto è il codice vero di K. Asserisce che la composita si mostra **da sola** (mai il contenuto due
> volte) e, nello stesso mondo simulato, che un sottotipo ancora sull'icona del contenitore
> (`ETF_BOND`) tiene la sovrapposizione e che `STOCK` resta un'icona sola.
>
> ```
> vitest, 4 file (rings + family + hierarchy + colors)      Test Files 4 · Tests 116
> mutante (f) — via il ritorno anticipato «già composita»   rosso solo il test D-K2 (1/14), rifatto da me
> mutante (e) — contenuto sempre presente                   5/14
> ```
>
> **⚠️ Fuori pista — una corsa nel mock, trovata da test-author**: la prima versione importava i due moduli
> con `Promise.all`; con il blocco eseguito per primo il test vedeva le icone simulate e
> `allocationFamily.ts` quelle vere. I mock manuali di vitest non reggono import concorrenti (lo dice il suo
> sorgente). Rimedio: il blocco ha un caricatore che importa in sequenza, e una barriera verifica che
> `allocationFamily.ts` veda davvero la composita. Provato anche col blocco spostato in testa, 4 volte.

### Riscrittura della storia locale — 24/09/2026

> Checkpoint `580fa8053` → `3c1589943` → `03c1f52e7` (icona composita, fixture sintetiche, journal senza
> cifre), poi la riscrittura preparata dal coordinator e lanciata dal developer: via i 6 importi in euro
> dai commit da `393a3d118` in poi (`a5f6776aa..8757c7e3a` invariati). Verificato da me dopo: HEAD
> `03c1f52e7`, albero pulito, `refs/original` assente, **0** occorrenze delle stringhe nella storia del ramo.
>
> | prima | dopo |
> |---|---|
> | `de55b5346` | `393a3d118` |
> | `551edffdc` | `7d6c9a60c` |
> | `5135efffc` | `0a22b2ab3` |
> | `086af5172` | `8afe5b31c` |
> | `cdf89f1b3` | `3a90c6dcc` |
>
> **⚠️ Fuori pista — avevo previsto conflitti che non ci sono stati**: avevo avvisato il coordinator che
> rigiocando i commit ripuliti ci sarebbero stati conflitti col commit dei segnaposto. La riscrittura usa
> `filter-branch --tree-filter`, che trasforma l'albero di ogni commit da solo senza rigiocare diff; e il
> commit 13 aveva già i segnaposto, quindi la punta nuova è identica alla vecchia. Avevo ragionato come
> per un rebase.

---

## Tempo ② — piano del checkpoint backend (approvato dal developer il 24/09)

Decisioni del developer: nessun periodo nell'intestazione (è quello della barra in alto) · avvisi in i18n
con nomi e parametri dal backend · una sola notifica di parzialità in cima, con «parziale» ridefinito sulla
soglia di progetto · requisiti minimi di ammissibilità per periodo · «i miei asset» = quantità > 0 ·
replay che esclude da sé gli asset che non coprono la finestra della crisi. Divisione confermata dal
coordinator: servizio, benchmark, replay e campi della lista asset = Risk; selettore e pagina di Asset
Global = F. Il backend va in un checkpoint suo, prima del frontend.

| # | passo | file | stato |
|---|---|---|---|
| B1 | un modulo per le soglie: `STALE_PRICE_THRESHOLD_DAYS = 7`, `TRANSACTION_IMPLIED_GRACE_DAYS = 14`, `RISK_MIN_OBSERVATIONS = 20`; motore del portafoglio e analisi di rischio li leggono da lì | `services/data_quality_thresholds.py` (nuovo), `portfolio_engine.py`, `portfolio_service.py`, i dieci plugin a 20, `price_store.py` (il commento citi il simbolo) | ✅ 24/09 · test ✅ |
| B2 | «parziale» ridefinito: un punto riportato degrada solo oltre i 7 giorni, e la baseline non conta mai | `series_preparation.py` | ✅ 24/09 · test ✅ |
| B3 | avvisi con chiave i18n e parametri (nomi degli asset, giorni) | `schemas/risk.py` (`RiskWarning`), `risk/service.py`, `risk_plugins/stress.py`, cataloghi i18n | ✅ 24/09 · test ✅ |
| B4 | replay: esclusione automatica di chi non copre la finestra (nessun prezzo, parte oltre 7 gg dopo l'inizio, finisce oltre 7 gg prima della fine, cambio mancante); motivo nell'audit | `risk/eligibility.py` (nuovo, regole pure), `risk/service.py`, `risk_plugins/stress.py`, `schemas/risk.py` | ✅ 24/09 · test ✅ |
| B5 | ammissibilità per periodo: non ammesso (nessun prezzo, cambio mancante, < 20 quotazioni) · ammesso con avviso (parte tardi, ultimo prezzo > 7 gg) | `risk/eligibility.py`, `api/v1/risk.py`, `schemas/risk.py` | ✅ 24/09 · test ✅ |
| B6 | lista asset: «posseduto ora da me» e «posseduto ora da altri» (quantità > 0) | `schemas/assets.py`, `asset_sources/crud.py` | ✅ 24/09 · test ✅ |
| B7 | test (test-author), registrazione nel runner, `api sync`, journal | 8 file di test (3 nuovi), `_backend_services.py`, `_backend_api.py` | ✅ 24/09 |
| B8 | motivi del replay che non dicono il falso: all'inizio «prima quotazione dopo l'inizio» ≠ «nessun prezzo nei 7 giorni prima» (buco o NAV mensile); alla fine un motivo neutro | `schemas/risk.py`, `risk/eligibility.py`, `risk_plugins/stress.py`, cataloghi i18n | ✅ 24/09 · test ✅ |

**Test previsti** (lista da mostrare al developer): 7 gg riportati non degradano, 8 sì · la baseline
riportata mai · portafoglio, rischio e ammissibilità leggono le stesse costanti · gli avvisi portano chiave e
parametri · ammissibilità ai bordi (19/20 quotazioni, 7/8 giorni) e per ogni motivo · replay: ogni motivo
di esclusione, tolleranza dei 7 giorni, esclusione manuale ancora valida, tutto escluso → non parte, peso
escluso come liquidità sul portafoglio e omesso su Asset Global, e **la finestra comune non viene più
accorciata** da chi parte tardi · lista asset: posizione chiusa → non «mio», posizione altrui aperta →
«di altri».

> **⚠️ Fuori pista — un difetto nascosto del replay, trovato leggendo il codice**: il replay prepara una
> serie *congiunta* per tutti gli asset; se uno comincia a quotare a metà crisi, la baseline comune si
> sposta alla sua prima data e **il replay di tutti gli altri copre solo la seconda metà della crisi**,
> senza dirlo (resta solo l'avviso generico `short_history`). L'esclusione automatica di B4 lo chiude per
> costruzione.

### Checkpoint backend B1–B6 — note implementazione · 24/09/2026

> - **B1**: `services/data_quality_thresholds.py` con le tre soglie; `portfolio_engine.py` importa la soglia
>   dei prezzi vecchi, `portfolio_service.py` il periodo di grazia; i dieci plugin a 20 e il default di
>   `CorrelationParams` leggono `RISK_MIN_OBSERVATIONS`; il commento di `price_store.py` cita
>   `PortfolioCalculationEngine._compute_price_fingerprint()` invece di una riga sbagliata dalla nascita.
> - **B2**: in `series_preparation.py` un punto riportato conta solo oltre i 7 giorni, prezzo e cambio
>   separatamente, e la baseline mai. Il contatore pubblicato cambia quindi significato («riportato oltre
>   la soglia»): lo leggono anche i segnali, che vedranno meno punti riportati — voluto, è la stessa regola.
> - **B3**: `RiskWarning` ha `message_i18n_key` e `message_params`; i 19 punti che costruiscono un avviso
>   scrivono la chiave per intero (l'audit i18n legge le chiavi del backend dalle assegnazioni letterali);
>   un avviso per motivo di esclusione e uno per causa di degrado; i nomi degli asset li aggiunge il
>   servizio con una sola query per risposta. **32 chiavi** in `risk.warnings.*`, nella convenzione già
>   usata dal namespace (`<codice>[_<variante>]`, 7 riusate), 4 lingue via `dev.py i18n`, tutte provate
>   con `intl-messageformat` e i loro parametri. Corrette le due frasi «alcune coppie» della correlazione.
> - **B4**: `risk/eligibility.py` (regole pure + un caricatore: una query aggregata e una prova di cambio
>   per valuta); esclusione automatica nel replay prima della serie congiunta; motivo nell'audit; un
>   proxy inutilizzabile resta un errore dei parametri; niente da riprodurre → errore, non più «0 %».
> - **B5**: `POST /api/v1/risk/eligibility`.
> - **B6**: `held_by_me` / `held_by_others` sulla lista asset (somma delle quantità per broker e asset,
>   la stessa lettura dei saldi del broker).
> - `api sync`: i file generati sono ignorati da git.
>
> **Misurato sulla copia di prod** (valori nella chat, non qui):
>
> ```
> L1, L2                    parziali solo per i crowdfunding senza prezzi, ora nominati; i weekend del
>                           BTP non degradano più nulla
> replay Covid 2020         parte (prima si bloccava): 3 esclusi in automatico, tutti no_prices_in_window
> replay 2008               parte: 8 esclusi — tutti gli ETF nati dopo il 2009 — con <quota> alta del
>                           portafoglio come liquidità: il risultato dice poco, il pannello deve dirlo
> replay 2022               parte: 3 esclusi
> ammissibilità 12 mesi     11 ammessi, i 4 crowdfunding non ammessi (no_prices)
> ```
>
> **Test**: `services risk-all` 450 ✓ / 4 ✗ — tutti attesi: fissavano il comportamento vecchio (un riporto
> di 1–2 giorni contato come degrado, il replay che si blocca) o costruivano il servizio su un DB finto che
> le chiamate nuove ora toccano. `schemas risk` 26 ✓, `schemas assets` 70 ✓, `api assets-crud` 32 ✓,
> `api risk` 11 ✓. test-author ripara i 4 e scrive i test nuovi (T1–T10).
>
> **⚠️ Fuori pista — tre rossi di `api risk` che non erano del codice**: il run precedente di `services`
> cancella il DB della corsia di suite, e i test API vogliono il portafoglio finto. Con `test db populate
> --force` nella mia data-dir di suite: 11 ✓. Stesso artefatto d'invocazione già visto nei round precedenti.
>
> **⚠️ Fuori pista — le chiavi i18n rinominate a metà**: le avevo scritte in camelCase; il namespace
> `risk.warnings` aveva già 7 chiavi col nome del codice, usate da `RiskResultFrame`. Rinominate tutte in
> snake_case e riusate le 7 esistenti, invece di duplicarle.

### B7 — i test del backend · ✅ 24/09/2026

> **Note implementazione**: test-author ha riparato i 4 test che fissavano il comportamento vecchio
> (uno rinominato, perché il nome diceva il contrario di quello che ora verifica) e scritto T1–T10: tre
> file nuovi (`test_data_quality_thresholds.py`, `test_risk_warnings_i18n.py`, `test_risk_eligibility.py`)
> e cinque estesi, registrati in `RISK_SERVICE_TEST_PATHS` e nelle descrizioni del runner. I due
> scanner di sorgente (soglie, chiavi i18n) hanno ciascuno un autotest del rilevatore. 18 mutanti, su
> copie caricate con un hook di import: tutti presi da almeno un test mirato; i sorgenti veri hanno lo
> stesso SHA-256 prima e dopo.
>
> **Verifica mia, nella corsia di suite 6152**: `services risk-all` 551 ✓ · `signal-service` 50 ✓ ·
> `asset-signals` 20 ✓ · `portfolio-engine` 42 ✓ · `roi-fifo-utils` 507 ✓ · `schemas risk` 26 ✓ ·
> `schemas assets` 70 ✓ · `db populate --force` ✓ · `api risk` 13 ✓ · `api assets-crud` 34 ✓ ·
> `check-orphans`: backend tutto registrato; i 5 orfani frontend sono i file privacy di `b66e93003`,
> non nostri. Ruff pulito; black segnalava due righe vuote mie in `schemas/risk.py`, sistemate.
> Scansione dei valori reali e delle password sui file toccati: nulla.
>
> **⚠️ Fuori pista — un motivo che poteva dire il falso**: test-author ha notato che un asset quotato da
> anni ma con un buco a cavallo dell'inizio della crisi (un fondo con NAV mensile) finiva escluso come
> «ha iniziato a quotare dopo l'inizio», che per lui è falso; e alla fine, per un asset che ha ancora
> prezzi oggi, «ha smesso di quotare» è quasi sempre un buco. Sui dati del developer non succede (prova
> in sola lettura su una copia del DB: gli esclusi sono tutti nati *dopo* la finestra, o senza prezzi) →
> passo B8.

### B8 — motivi del replay che non dicono il falso · ✅ 24/09/2026

Il developer ha chiesto prima se l'esclusione fosse giusta. Risposta, con le controindicazioni della sua
idea di spostare le date di confine:

- **Sì, è giusta.** Il replay somma i movimenti di ogni asset *sullo stesso intervallo*; il pezzo di
  finestra di un asset nato a metà crisi è un altro scenario (Covid 19/02→23/03/2020: S&P 500 −34 %,
  dal 16/03 solo −6 %). La quota esclusa conta come liquidità ferma: il numero dice quanto perde la
  parte misurata, non stima il tutto.
- **Accorciare** al periodo comune è coerente ma cambia scenario: le crisi del catalogo vanno dal massimo
  al minimo, quindi ogni finestra più corta lì dentro mostra una caduta più piccola → ottimista. Spesso
  il periodo comune non esiste; si sposta a ogni acquisto; era il vecchio comportamento, solo silenzioso.
- **Allargare** non aiuta chi non esisteva; per un buco al bordo la cura è accettare, per quell'asset
  solo, un prezzo più vecchio quando è il suo ritmo di quotazione (idea per dopo).
- La cura vera per gli asset giovani è il **sostituto** (già nel backend, UI assente, già in `TODO_FUTURI`).

Frase scelta (opzione A): all'inizio due motivi, alla fine uno neutro; «finestra del replay» al posto di
«crisi», perché il replay gira anche sul periodo personalizzato.

> **Note implementazione**: `RiskHistoricalReplayExclusionReason` guadagna `stale_at_window_start`, e
> `ends_before_window_end` diventa `stale_at_window_end` (mai rilasciato: il nome ora dice quello che i
> dati sanno). In `replay_coverage`, senza un prezzo nei 7 giorni prima dell'inizio, un asset quotato
> già prima della finestra è `stale_at_window_start`; solo una quotazione nuova ha la tolleranza dopo
> l'inizio. Gli avvisi dei due motivi «stale» portano `days` dal modulo delle soglie. Le 6 frasi del
> replay riscritte nelle 4 lingue via `dev.py i18n` (`ends_early` rimossa, due aggiunte): niente accordo
> di numero, così valgono per uno o per molti; 33 chiavi del backend × 4 lingue provate con
> `intl-messageformat`; audit i18n: 0 chiavi del backend mancanti.
>
> **Test** (test-author, secondo giro): T5 a 17 casi (buco al bordo esatto → coperto, NAV mensile →
> «stale» all'inizio e non «nato dopo», quotazione nuova esattamente a 7 giorni → coperta, a 8 → esclusa,
> cambio mancante prima del buco); T6 con cinque motivi automatici più quello manuale, in ordine di enum e
> con `days` solo sui due «stale»; un caso su righe vere (buco a cavallo dell'inizio → `stale_at_window_start`
> accanto a un `starts_after_window_start`, che fissa `first_quote` = prima quotazione di sempre);
> `stress.py` nella mappa dei consumatori delle soglie. Mutanti M13–M17 tutti presi (etichetta sbagliata al
> buco, `days` tolto all'inizio e alla fine, un buco «salvato» da una quotazione dopo l'inizio, tolleranza
> della quotazione nuova resa stretta, caricatore che legge la prima quotazione nella finestra).

### Decisioni del developer per il giro frontend · 24/09/2026

- **Avviso forte nel replay** quando l'escluso supera **metà** del portafoglio: «il risultato descrive
  solo il N % del tuo portafoglio». La soglia va nel modulo delle soglie.
- **Pulsante «adatta al periodo comune (dal X al Y)»** in due posti:
  - in alto, nella zona dove si scelgono gli asset (Asset Global): cambia il periodo della barra in alto;
    compare solo se il periodo scelto crea un problema a qualche asset. La zona è di F: chi mette il
    pulsante lo decide il coordinator; il calcolo è mio, nel backend;
  - nel replay: cambia solo le date del replay; compare solo se qualcuno è escluso per i bordi; nelle
    crisi del catalogo con la nota «è solo una parte della crisi: la perdita misurata tende a essere più
    piccola».
- **Replay con il `DateRangePicker`** della barra in alto al posto dei due `SingleDatePicker`, senza i
  pulsanti rapidi riferiti a oggi; se le date di una crisi cambiano, lo dice accanto al nome.
- **Piano frontend e lista dei test approvati** (avvisi tradotti, un solo avviso di parzialità in cima,
  replay senza blocco, benchmark filtrato, test delle palette, E2E aggiornati).

> **⚠️ Fuori pista — due messaggi al developer in inglese**: il riepilogo del backend e l'analisi del
> replay gli sono arrivati in inglese, e ha dovuto chiedere di rifarli. Regola: con il developer sempre
> in italiano, anche nei messaggi lunghi.
>
> **⚠️ Fuori pista — una chiave viva che l'audit crede morta**: `dashboard.allocationGeneric` (R12-B) è
> chiamata come `tr('dashboard.allocationGeneric', …)`, con `tr` alias di `$t`; l'audit riconosce `$t(`,
> `$_(`, `t(` e `_(`, non `tr(`, e una chiave a due segmenti sfugge anche alla rete generica. Una pulizia
> futura la cancellerebbe e la ciambella mostrerebbe la chiave grezza. Da correggere nel giro frontend
> (chiamata diretta a `$t(`), oppure estendendo l'audit, con il via del coordinator.

## Tempo ② — piano dopo il checkpoint backend (approvato dal developer il 24/09)

Ordine: checkpoint backend B1–B8 → **checkpoint C** (backend: periodo comune e avviso forte) →
frontend F1–F8 → checkpoint frontend. Il calcolo resta nel backend (regola di progetto): il frontend
mostra, non decide.

| # | passo | file | stato |
|---|---|---|---|
| C1 | periodo comune per l'analisi: sugli asset scelti, la finestra del periodo corrente dove tutti hanno prezzi (dall'ultima prima quotazione alla prima ultima), proposta solo se cambia qualcosa e se basta a tutti (≥ 20 quotazioni); con gli asset che la limitano; «nessun periodo comune» quando non esiste | `risk/eligibility.py`, `schemas/risk.py`, `api/v1/risk.py` | ✅ 24/09 · test ✅ |
| C2 | periodo comune nel replay: dentro la finestra, per gli esclusi a causa dei bordi; verificato con una seconda lettura dei fatti prima di proporlo; nell'audit | `risk/eligibility.py` (prima quotazione nella finestra), `risk/service.py`, `risk_plugins/stress.py`, `schemas/risk.py` | ✅ 24/09 · test ✅ |
| C3 | avviso forte quando l'escluso supera metà portafoglio: `historical_replay_mostly_excluded` con la quota coperta; soglia `REPLAY_EXCLUDED_WEIGHT_WARNING_SHARE = 0.5` nel modulo delle soglie | `data_quality_thresholds.py`, `risk_plugins/stress.py`, cataloghi i18n | ✅ 24/09 · test ✅ |
| C4 | test (test-author), runner, `api sync`, journal | 6 file di test (nessuno nuovo, runner invariato) | ✅ 24/09 |
| F1 | avvisi tradotti: chiave e parametri del backend; se manca la traduzione, il testo originale — mai una chiave grezza | `levels/warningSentence.ts` (nuovo), `levels/levelHelpers.ts`, `RiskResultFrame.svelte`, `levels/RiskLevelsPanel.svelte` | ✅ 24/09 |
| F2 | un solo avviso di parzialità in cima al pannello, ogni causa una volta; sotto i livelli solo gli errori | `levels/RiskLevelsPanel.svelte` (non `RiskLevelSection`, che è di F) | ✅ 25/09 (con la parte non-replay di F7) |
| F3 | replay: via il blocco «escludi e riprova»; esclusi per motivo con nomi e peso; avviso forte (C3); «niente da simulare»; `DateRangePicker` senza pulsanti rapidi; pulsante del periodo comune (C2), con la nota «solo una parte della crisi» nelle crisi del catalogo | `levels/l4/L4Replay.svelte`, `levels/l4/scenarioHelpers.ts` | ⏳ **dopo F → Risk** (decisione del developer, 25/09) |
| F4 | benchmark: non ammissibili grigi con il motivo, con avviso selezionabili e segnalati; cambia col periodo — **dopo la fusione F → Risk**, con le chiavi `risk.eligibility.*` di F (proposta al coordinator) | `levels/L3Benchmark.svelte` | ⏳ |
| F5 | test delle palette che leggono i colori dai grafici veri; puntatori per contenuto, non per riga | test di `AllocationPieChart` / `AllocationHistoryChart` (solo lettura dei `.svelte`) | ✅ 25/09 |
| F6 | `dashboard.allocationGeneric` chiamata con `$t(`, così l'audit la vede | `AllocationPieChart.svelte` | ✅ 24/09 · anticipato nel checkpoint B |
| F7 | E2E: riscritto quello del replay bloccato; aggiornati quelli che si aspettavano «Parziale» sotto i livelli | `frontend/e2e/portfolio/risk-analysis.spec.ts` | ⏳ prima di F → Risk solo la parte non-replay; il replay dopo |
| F8 | screenshot per il developer: icona composita (D-K2), avviso unico, replay, benchmark | — | ⏳ per le parti pronte; il replay dopo F → Risk |
| F9 | `runGuarded`: una risposta arrivata e scartata (il `null` di `queryRisk`) non diventa più «nessun risultato» muto — richiesta una volta sotto la nuova generazione, poi uno stato «scartata» per analisi, mostrato dalla sezione; test deterministici sul controller, **scritti da test-author e rossi prima della cura**, sui tre casi (`null` poi risposta → risposta; `null` due volte → scartata; generazione superata → nessuna nuova richiesta); la frase nel mio namespace `risk.*`, non in `risk.eligibility.*` (**obbligatorio**: il polling della Correlazione resta, decisione D11 del developer; confermato dal coordinator) | `stores/risk/riskPanelController.svelte.ts`, sezioni L4 | ✅ 25/09 |

Pulsante del periodo comune in alto (zona asset di Asset Global): la zona è di F; chi lo mette (F con il
mio endpoint, oppure io dopo l'integrazione di F) lo decide il coordinator. All'integrazione, inoltre:
collegare `docsPath`/`docsLabel` di F nella Dashboard, togliere `height` da `L2Diversification`,
sostituire `allocationFamily` con `assetTypeFamily` di K.

### Incarico nuovo — l'icona della documentazione su tutti i pannelli · ⏳ (deciso dal developer il 24/09, 13:1x)

Parole del developer, riportate dal coordinator: *«l'icona, solo lei, allineata a destra … in tutti i
pannelli di tutte le pagine, con annessa pagina di documentazione (specifica o in comune) che la
documenta»*. Non si comincia adesso.

- **Forma** (fissata con F): solo l'icona del libro (`DocsLink`, cioè `Tooltip.svelte`) sul bordo destro
  dell'intestazione; il tooltip spiega il pannello in poche frasi, il click apre la sua pagina di doc. Il
  pezzo generico c'è già: `docsPath` / `docsLabel` in `RiskLevelSection`; `check-links` valida ogni
  `docsPath` scritto per intero.
- **Sequenza**: F finisce la riprogettazione del laboratorio con il developer e mette l'icona sui pannelli
  del laboratorio → il developer fonde il ramo di F nel mio → da lì proseguo io: review e rifinitura dei
  componenti successivi, e l'icona su tutti i pannelli di tutte le pagine.
- **Dopo la fusione** sono l'owner d'integrazione del ramo combinato F + Risk (il vincolo «F entra prima di
  Risk» si soddisfa da sé). Le parti di F nella divisione del tempo ② (selettore che consuma
  l'ammissibilità, «i miei asset» = quantità > 0, declassamento nei pannelli) restano di F solo se il mio
  backend arriva prima del suo checkpoint finale; altrimenti passano a me con la fusione. → **Il
  checkpoint backend B va chiuso presto**; il pulsante del periodo comune in alto dipende da C, quindi con
  ogni probabilità sarà mio dopo la fusione.

| # | passo | stato |
|---|---|---|
| Doc0 | fusione di F nel mio ramo (la fa il developer): verifica dei genitori, conflitti risolti in modo additivo, cancelli di entrambe le parti sul combinato | ⏳ |
| Doc1 | **analisi prima del codice**: inventario dei pannelli pagina per pagina e, per ciascuno, la sua pagina di doc — esistente o da scrivere con `docs-writer`, solo EN; le pagine di altri owner del round (Dashboard di I e J, Broker di J, Asset di K, PAC di D) le mette in sequenza il coordinator | ⏳ |
| Doc2 | l'icona su tutti i pannelli, dopo l'approvazione dell'analisi | ⏳ |
| Doc3 | pagine di doc mancanti (`docs-writer`), `mkdocs build` e `check-links` | ⏳ |

### F6 — la chiave che l'audit credeva morta · ✅ 24/09/2026 (anticipato nel checkpoint B)

> **Note implementazione**: il coordinator ha dato la cura minima a me, subito, e ha messo in backlog quella
> generale (la regex di `i18n-audit.py:99`), perché cambierebbe la base «likely unused» su cui misurano
> altre corsie. `AllocationPieChart.svelte` chiama `$t('dashboard.allocationGeneric', …)` invece di
> `tr(…)`, con una riga di commento sul perché. Audit: la chiave non è più tra le inutilizzate (419 → 418).
> Verifica: `vitest` dei grafici 181 ✓, prettier pulito, `svelte-check` nulla sul componente (i suoi 3
> errori sono in `TransactionFormModal.test.ts`, non toccato da noi).

### Checkpoint backend B1–B8 + F6 — handoff `FROZEN` · 24/09/2026

Base `03c1f52e7`, 39 percorsi, 7 commit (script con i controlli di HEAD, stage vuoto, percorsi esatti e
impronta del contenuto): lista asset (3) → backend del rischio (21) → i18n (4) → test (7) → runner (2)
→ chiave dell'audit (1) → journal (1).

> **Verifica finale, corsia 6152**: `services risk-all` 560 ✓ · `signal-service` 50 ✓ · `asset-signals`
> 20 ✓ · `portfolio-engine` 42 ✓ · `roi-fifo-utils` 507 ✓ · `schemas risk` 26 ✓ · `schemas assets` 70 ✓ ·
> `db populate --force` ✓ · `api risk` 13 ✓ · `api assets-crud` 34 ✓ · `check-orphans`: backend tutto
> registrato (i 5 orfani frontend sono di `b66e93003`) · ruff e black puliti sui 33 file Python · `vitest`
> dei grafici 181 ✓ · audit i18n: 0 chiavi del backend mancanti · `api sync` rifatto (file ignorati da
> git) · nessun importo reale e nessuna password nei file e nei messaggi.
>
> **File condivisi toccati**: catalogo del runner (3 percorsi aggiunti a `RISK_SERVICE_TEST_PATHS`, due
> descrizioni estese in coda), cataloghi i18n (26 chiavi nuove e 2 riscritte, tutte in `risk.warnings.*`),
> `schemas/assets.py` + `crud.py` (due campi nuovi, li consuma F), `portfolio_engine.py` /
> `portfolio_service.py` (solo l'import delle costanti).
>
> **Effetti per l'integrazione**: chi fonde rigenera il client (`api sync`); le pagine di teoria di F e la
> pagina utente di A che dicono «i riportati rendono parziale» diventano inesatte (ora solo oltre 7
> giorni); i segnali vedono meno punti riportati (stessa regola); A e F vedranno meno «parziale» sui dati
> veri.
>
> **Voci di CHANGELOG proposte** (non scritte: il file lo tiene chi rilascia), in `### 🧪 Beta`:
> «Le analisi di rischio non segnano più come parziali i risultati per i weekend e le festività: un prezzo
> riportato conta solo dopo 7 giorni, la stessa soglia del banner dei prezzi vecchi» · «Il replay storico
> parte anche quando alcuni asset non esistevano durante la crisi: li esclude da sé e dice quali e
> perché». Le altre (avvisi tradotti, ammissibilità nei selettori) quando arriva il frontend.

### Checkpoint backend B — committato · 24/09/2026

> `b20f926fb` → `a766a9d5d` → `708187d8f` → `81499e0a8` → `c4135c1d1` → `a983808ad` → `14c334d85`, su
> `03c1f52e7`: 3 + 21 + 4 + 7 + 2 + 1 + 1 = 39 file, albero pulito, letti e verificati da me.

### C1–C3 — periodo comune e avviso forte · 🔵 codice ✅ 24/09/2026

> **Note implementazione**:
> - `PriceWindowFacts` guadagna la prima quotazione nella finestra e la prima e l'ultima di sempre; il
>   caricatore resta una query sola, senza più il filtro sulla fine della finestra (i campi di prima si
>   ottengono con `CASE`).
> - Tre regole pure in `risk/eligibility.py`: `common_quoted_range` (dall'ultima prima quotazione alla
>   prima ultima, sugli asset quotati), `suggested_analysis_range` (il periodo tagliato sul comune, oppure
>   il comune stesso se non si toccano), `suggested_replay_range` (dentro la finestra, solo per gli esclusi
>   a causa dei bordi).
> - Nel servizio ogni proposta passa una **seconda lettura dei fatti**: per l'analisi, ogni asset quotato
>   deve essere ammesso senza avvisi nel periodo proposto; per il replay, chi è coperto resta coperto e chi
>   è recuperato lo diventa. Nessuna proposta se l'unico problema è un asset senza nessuna quotazione.
> - `RiskEligibilityResponse` porta `common_range` e `suggested_range`; l'audit del replay
>   `suggested_range` e `suggested_range_recovers`, con un secondo validatore (ordinati, insieme, solo
>   esclusi automatici). Il validatore dell'audit è diviso in due per restare sotto la complessità di ruff.
> - Avviso `historical_replay_mostly_excluded` quando l'escluso supera metà del portafoglio
>   (`REPLAY_EXCLUDED_WEIGHT_WARNING_SHARE = 0.5`), con la quota coperta in parametro; frase nelle 4
>   lingue con la percentuale nel formato della lingua.
>
> **Misurato su una copia del DB della copia di prod** (in sola lettura, poi cancellata; nomi e valori nella
> chat):
>
> ```
> BTP + 3 ETF, 5 anni        il BTP parte tardi → proposto il periodo dalla sua prima quotazione a oggi
> 3 ETF, 1 anno              nessun problema, nessuna proposta
> BTP + ETF, 2018–2020       il BTP non esiste ancora → proposto il periodo comune (spostamento)
> replay Covid, 2022         3 esclusi, poco meno di metà del peso: nessun avviso forte
> replay 2008                8 esclusi, circa nove decimi del peso → avviso forte
> replay 2023–2025 (libero)  il BTP parte dentro la finestra → proposto il pezzo che lo recupera, verificato
> ```
>
> **Test**: `services risk-all` 558 ✓ / 2 ✗, entrambi attesi (i fatti hanno tre campi nuovi; un replay
> con più di metà escluso ora ha l'avviso forte). test-author li ripara e scrive i test di C.
>
> **⚠️ Fuori pista — il mio script di misura mandava un parametro che il replay non conosce**
> (`scenario_id`): la validazione rifiuta i campi in più, e tutte e quattro le finestre tornavano
> `invalid_parameters`. Tolto il campo, le misure sopra. Il frontend non lo manda.

> **⚠️ Fuori pista — un ramo morto nella proposta del replay, trovato da test-author prima di scrivere i
> test**: per un asset con un buco prima dell'inizio (o un NAV mensile) la proposta partiva dalla sua prima
> quotazione nella finestra; lì il suo ultimo prezzo *prima* dell'inizio è ancora quello vecchio, quindi la
> seconda lettura lo escludeva di nuovo e buttava la proposta intera. Sicuro (mai una promessa falsa), ma
> muto. Letto il codice della serie: il replay parte dall'ultimo giorno completo **prima** del primo giorno
> (`series_preparation.py:243-248`, caricato da inizio − 1). → la proposta parte **il giorno dopo** la prima
> quotazione, per il buco *e* per la quotazione nuova: così quel prezzo fresco fa da partenza, e la baseline
> non cade dentro la finestra (niente `short_history`). Stessa regola per la proposta dell'analisi.

> **Note implementazione — decisioni di C dopo lo stop** (24/09):
> - analisi: candidati in ordine — il periodo tagliato sul comune, poi il periodo comune stesso (per un
>   periodo che lo manca o lo tocca troppo poco); si tiene il primo che la seconda lettura conferma; nessuna
>   proposta se il periodo sta già dentro il comune (il guaio è un buco, nessuno spostamento lo risolve);
>   proposta solo per `no_prices`, `starts_late`, `stale_at_end` di un asset quotato;
> - motivo nuovo `no_price_history` (mai quotato), distinto da `no_prices` (nessun prezzo nel periodo, ma
>   altrove sì): solo il secondo si ripara cambiando periodo. Stesso principio di B8: il motivo non deve
>   suggerire il rimedio sbagliato;
> - replay senza più nulla da riprodurre: la proposta viaggia nei dettagli dell'errore (il caso dell'asset
>   singolo, dove serve di più);
> - soglia di polvere unica: `QUANTITY_DUST_THRESHOLD` passa nel modulo delle soglie; il portafoglio la
>   importa (valore invariato), i flag «posseduto ora» la usano al posto di 1e-9, così «posseduto ora» e
>   «holding a oggi» coincidono anche con i residui dei rimborsi.
>
> **Misurato su una copia del DB** (sola lettura, poi cancellata): proposta dell'analisi dal giorno dopo la
> prima quotazione del BTP; periodo disgiunto → spostato sul comune; replay libero 2023–2025 → proposta
> verificata, e il replay del periodo proposto **riporta dentro il BTP** senza avvisi di storia corta (restano
> fuori solo i crowdfunding mai quotati); il solo BTP → «non disponibile» con la proposta nell'errore; i
> crowdfunding → `no_price_history`.
>
> **Coordinamento**: la decisione del developer porta il mio backend `14c334d85` nel ramo di F subito (lo
> fonde il developer); C e F1–F9 restano nel mio ramo. Risposto a F sul contratto di `14c334d85` (forma,
> motivi, «nessun prezzo» = nel periodo, 500 per chiamata, `held_by_*` = oggi e non `dateEnd`); proposto al
> coordinator che `risk.eligibility.*` sia di F, primo consumatore. Il polling della Correlazione resta
> (D11) → la cura di `runGuarded` diventa obbligatoria: F9.
>
> **Risposta di F** (24/09, 16:0x): usa il contratto di `14c334d85` così com'è ed è `FROZEN` fino alla fusione
> Risk → F. Crea lui `risk.eligibility.reasons.<codice>` (con i testi proposti, `min_quotes` e `stale_days`
> come parametri) e prepara già `no_price_history`; lookup con ripiego generico, codici sconosciuti
> tollerati, test su `data-*`. Il developer ha deciso: **nessun segnaposto** per «adatta al periodo comune»
> nel ramo di F — posizione e collegamento miei dopo la fusione F → Risk. «Tutti i miei» resta «posseduti
> l'ultimo giorno del periodo» (`dateEnd`), con un'etichetta distinta da «posseduto ora»; **`held_by_me` /
> `held_by_others` per ora non li usa** → da riprendere all'integrazione (il declassamento «posseduto in
> passato» li userebbe; senza consumatori restano campi senza lettore). Chiamata unica per il catalogo,
> debounce, risposte superate scartate; `ineligible` in sola lettura e fuori da «Seleziona tutti» e
> «Inverti», `warning` selezionabile con l'avviso.

### Storia condivisa e contratto dopo `14c334d85` · 24/09/2026

Decisione del developer, comunicata dal coordinator: F ha committato il suo checkpoint 2 (`b97360b32`) e il
developer fonde `14c334d85` nel ramo di F (fusione simulata dal coordinator: pulita, `backend/` identico a
`14c334d85`, cataloghi i18n unione esatta di 3455 chiavi). La direzione finale resta **F → Risk**, con me
owner d'integrazione del ramo combinato.

- **`14c334d85` e tutti i suoi antenati sono storia condivisa: mai riscriverli.**
- Quello che committo dopo (C, F1–F9) arriva nel codice di F solo con F → Risk, salvo una seconda fusione
  Risk → F decisa dal developer.
- I miei file restano miei anche nel ramo di F: F li consuma, non li modifica. Unica eccezione concordata:
  l'area del titolo di `RiskLevelSection`, che non tocco prima di F → Risk.
- `risk.eligibility.*` è di F fino a F → Risk (le 5 chiavi di `14c334d85`, 4 lingue, dai miei testi EN/IT);
  dopo passa a me, e F4 lo riusa. **`no_price_history` ha un solo scrittore**: chi per primo ha nello stesso
  ramo il valore dell'enum e la mappatura di F — oggi io, a F → Risk. Il coordinator chiede a F una
  mappatura esaustiva sul tipo generato, così `front check` segnala la chiave mancante invece di una chiave
  grezza a schermo. Le frasi del replay (`risk.warnings.historical_replay_excluded_*`) restano mie: nessun
  riuso fra i due namespace.
- `portfolio_service.py`: I ha una correzione di una riga approvata a `:2404` (`needs_engine`, S10); le mie
  modifiche restano a `:77` e `:438`.

**Cambiamenti di contratto dopo `14c334d85`** — da adattare nel codice di F a F → Risk (lista viva):

| # | cambiamento | dove | effetto su F |
|---|---|---|---|
| K1 | motivo nuovo `no_price_history` (mai quotato), prima in `RiskEligibilityReason` | `schemas/risk.py`, `risk/eligibility.py` | la mappatura dei motivi guadagna un codice; chiave i18n scritta da me a F → Risk |
| K2 | `common_range` e `suggested_range` sulla risposta di `/risk/eligibility` | `schemas/risk.py`, `risk/service.py` | campi opzionali nuovi; il pulsante in Asset Global lo collego io |
| K3 | `suggested_range` e `suggested_range_recovers` nell'audit del replay | `schemas/risk.py`, `risk_plugins/stress.py` | nessuno (lo legge il mio `L4Replay`) |
| K4 | dettagli dell'errore del replay senza nulla da riprodurre: `suggested_range`, `suggested_range_recovers` | `risk_plugins/stress.py` | nessuno (idem) |
| K5 | avviso nuovo `historical_replay_mostly_excluded` (+ chiave i18n) | `risk_plugins/stress.py`, cataloghi | nessuno, se F mostra gli avvisi con la chiave del backend |
| K6 | `held_by_me` / `held_by_others`: soglia di polvere del portafoglio (0,00001) invece di 1e-9 | `asset_sources/crud.py`, `data_quality_thresholds.py` | nessuno oggi (F non li usa); il coordinator lo avvisa |
| K7 | (frontend, F9) risposta scartata: nuova richiesta una volta, poi `controller.discarded[analisi]`; `discardedErrorCodes(...)` e `ANSWER_DISCARDED_CODE`; frase `risk.errors.answer_discarded` | `riskPanelController.svelte.ts`, `levels/RiskLevelsPanel.svelte`, cataloghi | **`AssetSetReplaySection` di F** (la pagina del polling D11) monta `L4Replay` con un controller suo e passa al suo `RiskLevelSection` nessun `errorCodes`: senza, un replay scartato due volte lì sparisce ancora → a F → Risk aggiungo `errorCodes={discardedErrorCodes(controller.discarded, ['replay'])}` |
| K8 | (frontend, F1) `resultReasons(results, translate?)` e `warningSentence(...)`: le frasi dalla chiave e dai parametri del backend; senza traduttore l'uscita resta identica | `levels/levelHelpers.ts`, `RiskResultFrame.svelte` | le sezioni di Asset Global di F (`AssetSetCorrelationSection`, `AssetSetReplaySection`, `AssetSetComparisonLevels`) chiamano con un argomento: a F → Risk passo loro `$t`; e la doc delle prop `reasons` di `RiskLevelSection` (che F ha modificato: non la tocco prima) dice ancora «verbatim» → da riscrivere lì |
| K9 | (frontend, F2) `analyticNameKey(code)` in `levels/partialNotice.ts` duplica la funzione locale `analyticName` di `RiskLevelSection` | `levels/partialNotice.ts` | a F → Risk, `RiskLevelSection` (di F) può adottarla, così le due regole non divergono |
| K10 | (F, V5-A) la `CorrelationHeatmap` di F ignora la prop `height` | `levels/L2Diversification.svelte:342` passa ancora `height="360px"` | a F → Risk la tolgo |
| K11 | (F) la matrice riprogettata ordina per similarità, nome, tipo, settore, area; tipo, settore e area servono le mappe dal chiamante | la L2 della Dashboard non le passa → solo «similarità» e «nome» | lo decide chi prende il blocco Dashboard (A) con il developer; nella tabella dei proprietari |

### C — i test del checkpoint · ✅ 24/09/2026

> **Note implementazione**: test-author ha riparato i due rossi attesi e scritto i test di C1–C3 (regole pure
> ai bordi, servizio con una spia che conta le letture, round trip sul DB per una quotazione nuova *e* per un
> buco, con un controllo che mostra gli avvisi se si parte sulla prima quotazione stessa, dettagli dell'errore,
> validatore dell'audit, avviso forte, `no_price_history`, soglia di polvere nella lista asset, costanti).
> `services risk-all` 633 ✓ · `api risk` 14 ✓ · `api assets-crud` 35 ✓. 14 mutanti nuovi (M18–M31), tutti
> presi.
>
> **⚠️ Fuori pista — la proposta dell'analisi non scattava per una quotazione nuova con poche quotazioni**
> (domanda di test-author): con meno di 20 quotazioni nel periodo il motivo bloccante `too_few_quotes`
> nasconde gli avvisi, quindi `starts_late` non compariva e il mio innesco, letto dai motivi, taceva — proprio
> nel caso in cui la proposta serve di più. Non era una decisione nuova: la regola approvata dice «inizia
> tardi». → l'innesco ora si legge dai **fatti** (`period_limits_coverage`: quotato ma non nel periodo, parte
> oltre 7 giorni dopo l'inizio, si ferma oltre 7 giorni prima della fine), non dai motivi; i motivi nella
> risposta restano quelli di `14c334d85`. test-author aggiunge i casi.

> **Chiusura dei test di C** (test-author, ultimi due giri): l'innesco dai fatti ha 11 casi puri (ognuno
> dichiara anche cosa riporta `analysis_eligibility`, così la distanza fra fatti e motivi si vede nel test),
> e il caso di servizio in due forme: 11 quotazioni nel periodo → il periodo tagliato fallisce e il comune
> arriva dopo **due** letture in più; quotazione nuova il giorno prima della fine → il comune in **una**.
> Mutanti M32–M34 presi. Poi un rosso che i suoi run non vedevano, in `schemas risk` (non era nella lista
> che gli avevo dato: mia la svista): il test che fissa il JSON dell'audit ora ha i due campi nuovi, e un test
> fratello porta un audit con proposta attraverso JSON e ritorno; i 7 casi del validatore della proposta sono
> stati **spostati** nel file degli schemi, non copiati.

### Checkpoint C — handoff `FROZEN` · 24/09/2026

Base `14c334d85`, 19 percorsi, 4 commit (script con i controlli di HEAD, stage vuoto, percorsi esatti e
impronta del contenuto): backend (8) → i18n (4) → test (6) → journal (1).

> **Verifica finale, corsia 6152**: `services risk-all` 639 ✓ · `signal-service` 50 ✓ · `asset-signals`
> 20 ✓ · `portfolio-engine` 42 ✓ · `roi-fifo-utils` 507 ✓ · `schemas risk` 34 ✓ · `schemas assets` 70 ✓ ·
> `db populate --force` ✓ · `api risk` 14 ✓ · `api assets-crud` 35 ✓ · `check-orphans`: backend tutto
> registrato (i 5 orfani frontend sono di `b66e93003`) · ruff e black puliti sui 14 file Python · 34 chiavi
> del backend × 4 lingue formattate · audit i18n: 0 mancanti, parità 3431 chiavi · `api sync` rifatto (file
> ignorati) · nessun importo reale, nessuna password.
>
> **File condivisi toccati**: cataloghi i18n (1 chiave nuova in `risk.warnings`); `portfolio_service.py`
> (solo `:77` e `:439-440`, valore della soglia invariato; I tocca `:2404`); `data_quality_thresholds.py` (due
> costanti nuove). Cambiamenti di contratto dopo `14c334d85`: K1–K6 nella tabella sopra.

### Checkpoint C — committato · 24/09/2026

> `3ba802b42` → `fbb4773d2` → `d7d6fb293` → `96931b7f4`, su `14c334d85`: 8 + 4 + 6 + 1 = 19 file, albero
> pulito, letti e verificati da me. Da qui anche questi sono storia condivisa: mai riscriverli.

## Tempo ② — giro frontend · 🔵 aperto il 24/09/2026

Ordine concordato col coordinator: **F1 per primo**, in un commit suo, con i test **rossi prima della cura**;
poi F9, F2, F3, F5, F7, F8; F4 dopo F → Risk.

### F1 — avvisi tradotti con i loro parametri · ✅ 24/09/2026

> **Note implementazione**: F non ha toccato `levelHelpers.ts`, `RiskResultFrame.svelte` e
> `RiskLevelsPanel.svelte` (controllato sul suo ramo); le sezioni di Asset Global che chiamano
> `resultReasons` sono sue → il traduttore è un secondo argomento opzionale, e senza di esso l'uscita resta
> identica (K8). test-author nuovo, dedicato al frontend, scrive i test contro il contratto e si ferma sul
> rosso; poi la cura, poi il verde e i mutanti.
>
> **Il coordinator sulla regressione** (verifica di C): meccanismo confermato (le tre chiavi non esistevano a
> `f1047f766`; `translatedCode` chiama `$t` senza valori). Portata: oltre al mio, solo il ramo di F contiene
> `14c334d85` — K, I, J, A, D e `dev_release2` no → a K non va detto niente; F lo avvisa lui. **Cancello
> d'integrazione**: il ramo combinato F/Risk non entra in `dev_release2` senza F1. Due aggiunte ai test,
> girate a test-author: coprire anche `historical_replay_mostly_excluded` (argomento ICU numerico), e la
> proprietà generale — per ogni chiave `risk.warnings.*` con argomenti ICU, il testo mostrato non contiene mai
> una graffa né la chiave, e con parametri vuoti ricade sul `message` del backend.

> **Rosso prima della cura** (test-author): `levelHelpers.test.ts` esteso e `RiskResultFrame.test.ts` nuovo, con un
> aiuto condiviso (`src/__tests__/riskWarningCatalogue.ts`) che ricava dal catalogo **ogni** chiave
> `risk.warnings.*` con argomenti ICU (24 oggi) e costruisce i valori dall'AST della frase. Sul codice di
> prima: 38 rossi in `risk-levels-unit` (la funzione non esiste ancora; il traduttore ignorato) e 8 in
> `risk-frame-component` (il testo ICU grezzo, con le graffe; la frase generica al posto di quella vera),
> tutti per il motivo giusto; verdi la guardia di regressione senza traduttore e il ramo degli errori.
>
> **Cura**: `warningSentence` in un modulo suo (`levels/warningSentence.ts`, perché `levelHelpers.ts` dichiara
> di essere al limite di dimensione — stesso precedente di `levelMetadata.ts`), riesportato da `levelHelpers`;
> chiave e parametri del backend, ripiego sul `message` inglese se la chiave manca o se la formattazione
> fallisce (una graffa rimasta) — mai una chiave, mai un segnaposto. `resultReasons(results, translate?)` la usa
> (senza traduttore: uscita identica); `RiskResultFrame` mostra così gli avvisi (gli errori restano sui codici);
> `RiskLevelsPanel` passa `$t` alle quattro chiamate. Prova locale dei due file: 125 ✓; `svelte-check`: nulla
> sui file toccati (restano i 3 errori già noti altrove); prettier pulito.

> **Verde e mutanti** (test-author): `risk-levels-unit` 228 ✓ · `risk-frame-component` 13 ✓ ·
> `risk-levels-component` 9 ✓ · `risk-controller-unit` 16 ✓ · `risk-unit` 17 ✓. Otto mutanti più uno in
> aggiunta, applicati sul posto con copia di riserva, ripristino e controllo SHA-256 a ogni passo: tutti presi.
> Uno era sopravvissuto («liste non unite»): il backend unisce già i nomi, quindi nessun test mandava una lista
> → aggiunti due test (una lista si legge come la stringa già unita; un valore che non è uno scalare resta
> fuori invece di stamparsi come `[object Object]`). Su suo suggerimento `translatedCode` accetta ora solo
> `'errors'`: nessuno può più riaprire la strada che mostrava le graffe.
>
> **Verifica mia, corsia 6152**: le cinque categorie sopra più `allocation-unit` 116 ✓; `check-orphans`:
> `RiskResultFrame.test.ts` registrato, restano i 5 orfani di privacy già noti; prettier pulito sui 7 file;
> `svelte-check` nulla sui file toccati (restano i 3 errori già noti altrove); il file del runner ha lo stesso
> debito di ruff e black di `HEAD` (19 e da riformattare), nessuno nuovo; nessun importo reale, nessuna password.

### F1 — committato · 24/09/2026

> `4b563f225` → `8bac06955` → `0a86af69b` → `0fb96a163`, su `96931b7f4`: 4 + 3 + 1 + 1 = 9 file, albero
> pulito, letti da me. Storia condivisa da qui: mai riscriverla.

### ⏸ Pausa chiesta dal developer · 24/09/2026, 18:3x

Stato esatto alla pausa (nessun comando in corso, nessuno specialista al lavoro, 6152 e 6162 libere — il
server della copia di prod è stato spento):

- **F9 non è cominciato.** Analisi fatta: `runSingle` trasforma il `null` di `queryRisk` (risposta arrivata e
  scartata) in «nessun risultato», e replay, stress e simulazione spariscono in silenzio; `loadBase` ha già la
  cura (una nuova richiesta, poi `loadDiscarded`). Cura prevista: stesso schema per ogni analisi a richiesta —
  distinguere «scartata» da «non supportata», richiedere una volta sotto la nuova generazione, poi uno stato
  «scartata» per analisi, mostrato dalla sezione con una frase nel namespace `risk.*`. **Primo passo alla
  ripresa**: brief a test-author per i test rossi prima della cura, sui tre casi (`null` poi risposta →
  risposta; `null` due volte → scartata; generazione superata → nessuna nuova richiesta), sul modello di
  `riskPanelController.test.ts`.
- **Da fare dopo**: F2 (un solo avviso di parzialità in cima), F5 (palette dai grafici veri), F7 (E2E), F8
  (screenshot); F4 dopo F → Risk; l'icona della doc su tutti i pannelli dopo F → Risk.
- **Replay rinviato dal developer al prossimo sprint** (messaggio del coordinator): F3 va in backlog insieme ai
  tre difetti trovati nella review di F in `L4Replay.svelte` — le date non usano `DateRangePicker`; una data di
  inizio preistorica (1019-06-10) non dà né un avviso né un restringimento (verificarlo prima con C, che il ramo
  di F non ha); il menu dei preset (`SimpleSelect`, `:155`) si apre in basso anche in fondo alla pagina (se la
  causa è nel `SimpleSelect` condiviso, prima il coordinator). Da confermare alla ripresa se il rinvio copre
  tutto F3, e quindi anche la parte replay di F7.
- **Ancore dell'icona della doc** (correzione del coordinator): finché l'indice `risk-metrics` non è tradotto,
  L1–L3 → `financial-theory/technical-analysis/risk-metrics/` senza ancora; un pannello con una sola analisi →
  la sua pagina (il replay → `…/risk-metrics/historical-replay/`); gli altri → l'indice. Le ancore
  (`#how-much-can-it-hurt`, `#am-i-diversified`, `#am-i-paid-for-the-risk`, `#what-if`) solo dopo la traduzione.
- **Messaggi arrivati fuori ordine**: «F1 committato, vai con F9» mi è arrivato *dopo* la pausa, che viaggiava
  con priorità; ho seguito la pausa, la più prudente, e aspetto il coordinator prima di cominciare F9.

### ▶ Ripresa · 25/09/2026, 09:1x

> Il Mac si è riavviato durante la pausa (08:58): `/tmp` cancellato, quindi le mie dir di corsia non ci sono
> più (il runner ricrea quella di test) e la copia di prod va rifatta dalla snapshot solo se serve la review;
> il coordinator ha ripristinato `/tmp/libreFolio_commits`. 6152 e 6162 libere, HEAD `0fb96a163`.
>
> **Risposta del developer sul replay**: le correzioni del replay vengono **dopo F → Risk**, e allora decido io
> chi le fa — tutto F3, la parte replay di F7 e i tre difetti della review di F. **Prima di F → Risk**: F9 →
> F2 → F5 → F7 senza il replay → F8 per le parti pronte; F4 resta dopo la fusione.

### F9 — le risposte scartate non spariscono più · ✅ 25/09/2026

> **Rosso prima della cura** (test-author nuovo: quello di ieri non esiste più dopo il riavvio): 37 test nuovi in
> `riskPanelController.test.ts`, tutti rossi per il motivo giusto sul codice di `0fb96a163` (il primo `null`
> memorizzato come «nessun risultato», nessuna nuova richiesta, il getter e la funzione che mancano, la chiave
> che manca); i 16 esistenti verdi. Più un aiuto `recordReads` in `src/__tests__/runes.svelte.ts`, per provare
> che `discarded` è reattivo (solo un `$effect` può dirlo). Ha provato il contratto su una copia in `/tmp` e sei
> cure sbagliate: tutte prese.
>
> **Cura**: `runSingle` distingue tre esiti (risposta, analisi non supportata, risposta scartata); `runGuarded`
> richiede una volta finché la sua generazione è quella corrente, poi — solo se lo è ancora — memorizza il
> risultato e alza `discarded[analisi]` se è stata scartata di nuovo; i flag si azzerano con una nuova esecuzione,
> con `resetAnalysis` e quando cambia la domanda. `RiskLevelsPanel` mostra il codice `answer_discarded` sotto L3
> (confronto) e sotto L4 (stress, replay, simulazione), con la frase nuova `risk.errors.answer_discarded` (4
> lingue via `dev.py i18n`, senza graffe: `translateErrorCode` la chiama senza valori). Prova locale: 53 ✓;
> `svelte-check` nulla sui file toccati.
>
> **Da sapere** (dal rapporto di test-author): il polling di D11 è `POST /assets/prices/current`, che conta come
> modifica del portafoglio → `invalidateRisk()` → le risposte in volo tornano `null` senza spostare le
> generazioni: finisce proprio nel ramo della nuova richiesta. Anche Asset Detail (pagina ferma) fa lo stesso
> polling e usa lo stesso controller: guadagna la nuova richiesta ma nessuna frase (il pannello vecchio non la
> mostra) → rifaccio il suo E2E. Un'analisi che dura ~30 s o più su una pagina col polling viene scartata
> entrambe le volte: il flag lo rende visibile, non lo cura. Un solo codice per livello: L4 non dice quale dei
> tre passi ha perso la risposta (accettato: il rimedio è lo stesso).
>
> **Verde, E2E e mutanti** (test-author): `risk-controller-unit` 53 ✓ · `risk-levels-unit` 228 ✓ ·
> `risk-frame-component` 13 ✓ · `risk-levels-component` 9 ✓ · `risk-unit` 17 ✓ · E2E `risk-asset-detail` 2 ✓ e
> `risk` 13 ✓ (verificato che il bundle servito conteneva la cura). 14 mutanti presi; **uno sopravvissuto**: il
> collegamento nel pannello (confronto sotto L3, gli altri tre sotto L4), che nessun test vede — nessun test
> vitest monta `RiskLevelsPanel` e nessun E2E provoca uno scarto. → estratta la mappa
> `LEVEL_ON_DEMAND_ANALYSES` accanto a `discardedErrorCodes` (ogni analisi in un solo livello), letta dal
> pannello; test-author aggiunge il test della mappa (disgiunta, unione = tutte le analisi). Resta scoperto solo
> lo scambio di `.l3`/`.l4` nel pannello: accettato, i nomi sono espliciti. Nota di UX: L4 chiusa nasconde la
> frase finché non la si apre (le analisi a richiesta si lanciano da dentro L4, quindi capita solo chiudendola
> mentre un'analisi è in volo).

>
> **Chiusura** (test-author): il test della mappa (nessuna analisi in due livelli né in nessuno, il confronto
> sotto L3, i tre passi sotto L4) prende entrambi i mutanti del collegamento; `risk-controller-unit` 54 ✓,
> `risk-levels-unit` 228 ✓, E2E `risk` 13 ✓ ricostruito dai sorgenti ripristinati. **Verifica mia, corsia 6152**:
> `risk-controller-unit` 54 ✓ · `risk-levels-unit` 228 ✓ · `risk-frame-component` 13 ✓ ·
> `risk-levels-component` 9 ✓ · `risk-unit` 17 ✓ · `check-orphans`: solo i 5 orfani di privacy già noti ·
> prettier pulito sugli 8 file · `svelte-check` nulla sui file toccati · audit i18n: 3432 chiavi, 0 incomplete,
> `risk.errors.answer_discarded` non figura fra le inutilizzate (`risk.errors` è un prefisso dinamico) · nessun
> importo reale, nessuna password.

### F9 — committato · 25/09/2026

> `b02f49727` → `48a14ed0a` → `9e9c19c8f` → `296a50ae9`, su `0fb96a163`: 2 + 4 + 2 + 1 = 9 file, albero pulito,
> letti da me. Storia condivisa da qui.

### F2 — un solo avviso in cima (L1–L3) · ✅ 25/09/2026

> **Note implementazione**: il design (preparato durante il `FROZEN` di F9) mette in cima, sotto l'avviso del
> backtest, un riquadro unico con le misure parziali di L1–L3 (per istanza: i due VaR restano distinti) e le loro
> ragioni, una volta per frase e contate una volta per istanza (`historical_kpi` alimenta L1 e L3); sotto i livelli
> restano solo gli errori, col nome dell'analisi. Due titoli: «Alcuni risultati sono parziali» se qualcosa lo è,
> altrimenti «Da sapere su questi risultati» (una nota su un risultato completo resta da leggere). L4 invariato:
> lo mostro al developer sugli screenshot. `RiskLevelSection` (di F) non si tocca: cambia solo cosa gli passa il
> pannello. Il test E2E che fissava le ragioni sotto ogni livello va riscritto: la regola nuova la chiede il
> developer (decisione del 24/09, punto 3).

> **Rosso prima della cura** (test-author): `partialNotice.test.ts` e `RiskPartialNotice.test.ts` nuovi (modulo e
> componente mancanti), l'E2E riscritto — ora «a partial measurement and every warning are disclosed once, in one
> notice above the levels» — rosso sulla prima asserzione dell'avviso dopo le barriere, e l'aggiunta al test
> «per-analytic unavailable state remains isolated» rossa sulla parte dell'avviso; gli altri test verdi.
> Registrati nel runner in coda alle voci esistenti. L'E2E controlla anche che l'avviso venga *prima* di L1.
>
> **Cura**: `levels/partialNotice.ts` (`uniqueByInstance`, `partialNotice`, `levelErrorHealth`,
> `analyticNameKey`), `levels/RiskPartialNotice.svelte`, e in `RiskLevelsPanel` l'avviso calcolato dalle stesse
> fette dei livelli e messo per primo; L1–L3 ricevono solo la salute degli errori e nessuna ragione; L4 invariato.
> Due chiavi nuove (`risk.levels.notice.partialTitle`, `.notesTitle`), 4 lingue via `dev.py i18n`. Prova locale:
> 22 ✓; `svelte-check` nulla sui file toccati.
>
> **⚠️ Fuori pista — una lacuna di L3 che precede F2** (trovata da test-author): la scheda di L3 preferisce il
> `historical_kpi` della **composizione attuale** (`selectKpiWave`) e il grafico usa `asset_risk_return` della
> stessa onda, ma né la vecchia salute di L3 né il nuovo avviso li leggono: un risultato parziale lì non viene
> detto da nessuna parte. Le istanze hanno id distinti (`base-current_composition-…`), quindi la cura è facile, ma
> richiede un'etichetta nuova a schermo per distinguere i due «Indicatori storici» → **F2b**, da decidere col
> developer sugli screenshot. Altre note: una frase su un risultato *non disponibile* finirebbe in cima mentre il
> suo stato resta sotto il livello (nessuna fixture lo produce oggi); `analyticNameKey` duplica la funzione di
> `RiskLevelSection` → K9.

> **Verde e mutanti** (test-author): `risk-levels-unit` 240 ✓ · `risk-levels-component` 19 ✓ ·
> `risk-frame-component` 13 ✓ · `risk-controller-unit` 54 ✓ · E2E `risk` 13 ✓ (bundle servito controllato:
> l'avviso c'è, le ragioni per livello no) · E2E `risk-asset-detail` 2 ✓. Dieci mutanti, tutti presi dal test
> pensato per ciascuno — i tre del pannello solo dall'E2E, che è l'unico a montarlo (ricostruito dal pannello
> mutato a ogni giro, poi dai sorgenti ripristinati). Il titolo ora ha un suo `data-testid`, e il test del
> componente lo confronta per uguaglianza esatta.
>
> **Verifica mia, corsia 6152**: le cinque categorie unit/componenti sopra più `risk-unit` 17 ✓ ed E2E `risk`
> 13 ✓ · `check-orphans`: i due test nuovi registrati, restano i 5 orfani di privacy · prettier pulito sui 10
> file · `svelte-check` nulla sui file toccati · audit i18n: 3434 chiavi, 0 incomplete, le due chiavi nuove non
> figurano fra le inutilizzate · il runner cambia solo per aggiunte (ruff 19 come `HEAD`) · nessun importo reale,
> nessuna password.

### F2 — committato · 25/09/2026

> `af39db8a9` → `ae37dcffe` → `17b5cbefd` → `3b4e1e356` → `3cd4524cf`, su `296a50ae9`: 3 + 4 + 3 + 1 + 1 = 12 file,
> albero pulito, letti da me. Storia condivisa da qui.
>
> **Per la pianificazione** (coordinator): J è integrato in `dev_release2` (`2bbaa8db2`). Dopo F → Risk il mio
> ramo resterà sulla vecchia base: prima dell'ingresso finale di F+Risk servirà una fusione `dev_release2` → Risk,
> che porta nel mio ramo il lavoro di privacy di J. La pianifichiamo insieme dopo F → Risk.

### F5 — le palette si leggono dai grafici veri · ✅ 25/09/2026

> **Note implementazione**: il reperto di I (24/09, approvato dal developer: «sì se testabile») — tre file di test
> (`colors.test.ts`, `allocationHierarchy.test.ts`, `allocationRings.test.ts`) dichiarano di misurare le palette
> «reali» ma ne controllano una copia, con puntatori per numero di riga ormai sbagliati. La cura è solo nei test:
> un aiuto condiviso legge `const PALETTE_*` dal `.svelte` **per nome**, e le copie spariscono. La palette storica
> sta nel file di I: il test la legge soltanto. La prova che serve: una palette rotta nel componente lascia verdi i
> test di oggi e rende rossi quelli nuovi.

> **Fatto** (test-author): un aiuto nuovo `src/__tests__/sourcePalettes.ts` legge `const <nome> = [...]` dal
> sorgente per nome e si ferma con un errore chiaro (costante assente, dichiarata due volte, non letterale, vuota,
> una voce che non è `'#rrggbb'`), con 18 test sui suoi casi d'errore, su stringhe in linea; i tre file di test
> leggono le palette dai due componenti invece delle copie, con i puntatori per contenuto e i guardiani (14 colori
> distinti, chiara e scura della stessa lunghezza). Due commenti che *affermavano* che un colore sta nella palette
> sono diventati precondizioni controllate. `allocation-unit`: 116 → 149 ✓.
>
> **La prova** (tre mutanti sul posto, sorgenti ripristinati identici): una palette con due colori uguali, una
> palette scura con un colore in meno, una costante rinominata → **verdi** sui test di prima (il difetto), **rossi**
> su quelli nuovi, l'ultimo col messaggio dell'aiuto. Il primo lo vedono solo i guardiani: nessun test di logica
> si accorge di due colori uguali.
>
> **Verifica mia**: `allocation-unit` 149 ✓, `risk-levels-unit` 240 ✓, `check-orphans` (il test nuovo è
> registrato, restano i 5 orfani di privacy), prettier pulito, `svelte-check` nulla sui file toccati, i due
> componenti identici a `HEAD`, il runner cambia solo per aggiunte (ruff 19 come `HEAD`), nessun importo reale,
> nessuna password. `PALETTE_SLOTS = 14` è un fissaggio voluto: far crescere una palette vorrà dire cambiare una
> riga nell'aiuto.

### F5 — committato · 25/09/2026

> `4dc04dd18` → `d1f607416` → `4807d2b7d`, su `3cd4524cf`: 5 + 1 + 1 = 7 file, albero pulito, letti da me.

### F8 — screenshot sulla copia di prod, domande rimandate · 25/09/2026

> **Note implementazione**: copia rifatta dalla snapshot delle 09:15 con la procedura (schema 004, impronta del DB
> uguale a quella del coordinator, nessun marcatore), server di review sulla 6162 legato a `127.0.0.1` e senza
> scheduler; la password del developer non era salvata da nessuna parte, quindi è stata resettata **solo sulla
> copia** a una temporanea, in un file in `/tmp` leggibile solo dal proprietario. Tre screenshot (nella cartella di
> sessione, non versionati: contengono i suoi dati): l'avviso unico in cima, L3 («sulla composizione attuale»), L4
> dopo un replay del Covid. Sui suoi dati l'avviso nomina **tutte e sei** le misure, perché i due crowdfunding senza
> prezzi rendono parziale ogni risultato.
>
> **⚠️ Fuori pista — uno screenshot sbagliato**: il primo ritaglio di L4 è venuto sull'area sbagliata; dopo lo
> scorrimento le coordinate dell'elemento sono relative alla finestra, non alla pagina. Rifatto con lo screenshot
> dell'elemento.
>
> **Decisione del developer**: le domande (L4, F2b) sono **rimandate** — «sono tutte, in qualche modo, sbagliate, ma
> bisogna entrarci nel dettaglio». Il rischio in Dashboard e in Asset richiede un lavoro puntuale sulla UI: pensa di
> dare un blocco ad A e uno a F, ognuno a lavorare con lui sulla grafica, e a me il coordinamento delle basi e la
> divisione del lavoro. Proposta di baseline (al developer e al coordinator): checkpoint di F → F → Risk (integro io,
> K1–K9) → `dev_release2` → Risk (J) → Risk → A e Risk → F; poi la divisione, con un proprietario unico per ogni
> superficie condivisa.

## Giro UI rischio — coordinamento di A + F + Risk · 🔵 aperto il 25/09/2026

> **Ordine rivisto dal developer** (25/09, 12:0x): prima di riprendere lo sviluppo Risk, F e A tirano dentro il
> `dev_release2` corrente, così nessuno si allontana troppo; quindi `dev_release2` → Risk viene **prima** di F → Risk.

Decisione del developer, confermata dal coordinator: **A** lavora con il developer sul rischio in **Dashboard**, a
partire da un miglioramento grafico; **F** sul **laboratorio** di Asset Global; **io** coordino — baseline, divisione
dei file, proprietario unico di ogni superficie condivisa della famiglia (`RiskLevelSection`, chiavi `risk.*` e
`risk.assetSet.*`, `levelHelpers`, `riskPanelController`, `L4Replay`, `AssetSet*`), integrazione di A e F nel mio ramo
e validazione del combinato. Al coordinator restano `dev_release2`, l'ingresso finale, il percorso dei checkpoint (A e
F li mandano a me per il contenuto; io li inoltro) e le superfici fuori famiglia (grafici di I, primitive di privacy di
J, tassonomia e select di K, Asset Detail fuori dal pannello rischio, strumenti di D, runner, i18n fuori `risk.*`,
CHANGELOG, client generato). Commit e fusioni li fa solo il developer.

| passo | cosa | stato |
|---|---|---|
| G0 | **A**: validazione di `f45f0fb4d` (fusione `dev_release2` → A), `dev_release2` avanza in fast-forward su A, commit di CHANGELOG del coordinator → la baseline di tutti: `dev_release2` con J e A | ✅ 25/09 (`dev_release2` = `f45f0fb4d`; segue il commit di CHANGELOG del coordinator) |
| G1 | **`dev_release2` → Risk** (simulazione e script del coordinator; conflitti additivi, solo risoluzioni) e validazione del combinato nella 6152, **con la privacy accesa e spenta** sulle quattro superfici con importi (schede di L1, importi del replay, tornado di L4, cifre di Asset Global): ciò che passa per le primitive di J segue la modalità da sé, ciò che formatta il denaro a mano no, e il cancello `moneyRenderSites.test.ts` vede solo le righe con un simbolo di valuta | ✅ 28/09 — fusione `81f762d11`; validazione verde dopo la riparazione del pin di `risk.errors`; privacy accesa e spenta ✅ |
| G2 | **F**: checkpoint dei 31 file, poi `dev_release2` → F allo stesso modo | ✅ 28/09 — `dev_release2` → F fatto da F (`5010fe815`), checkpoint di F committato |
| G3 | **F → Risk**, con tutti e due sulla stessa base: restano solo i conflitti fra me e F | ✅ 28/09 — `d471e0b5b` (genitori `b9ee8d7be` + `533a18787`), 5 conflitti additivi risolti da me |
| G4 | commit mio con gli adattamenti K1–K9 al codice di F | 🔵 codice ✅, test ✅ 28/09 — in consegna al coordinator come checkpoint |
| G5 | validazione del ramo combinato | ✅ 28/09 — validazione del combinato (vedi sotto) |
| G6 | A e F avanzano in fast-forward alla punta di Risk | ⏳ |
| G7 | tabella dei proprietari, confermata col developer, al coordinator; poi il via del developer | ⏳ |

> **Reperti di A per dopo la baseline** (sovrapposizioni semantiche, che Git non vede): con la regola nuova del
> «parziale» (7 giorni) la regola 3 della sua pagina utente e una riga della guida D3 non valgono più; con
> l'esclusione automatica del replay il paragrafo sul replay di `correlation.en.md` è falso; la pagina cita la frase
> inglese del backend, ora tradotta. Le pagine sono sue: le corregge lui. Il docstring di `AssetSetComparisonLevels`
> e il montaggio dei suoi livelli in `AssetSetRiskPanel` li verifica dopo la fusione.

> **Principio del developer per tutte le corsie** (25/09, via coordinator): il prodotto, per ora, va bene così; i
> test devono provare il prodotto di oggi, non i passaggi intermedi; un test vecchio che prova un comportamento che non
> c'è più se ne va, e così il codice rimasto senza chiamanti, dentro il perimetro della corsia e con il suo test di
> regressione dove serve — prima di togliere, attribuire con `test-triage`, per non scambiare un test vecchio per un
> difetto; le domande al developer, in italiano.
>
> **Cosa ricade sotto il principio, nel mio perimetro** (da fare nel lavoro sul replay, dopo F → Risk): dal backend C
> il replay non si blocca più su un asset senza storia — lo esclude da sé — quindi in `L4Replay` il ramo «escludi e
> riprova» (`replayBlocker`, `replayNeedsChoice`) resta senza un chiamante reale (resta raggiungibile solo un sostituto
> inutilizzabile, e i sostituti non hanno UI), e l'E2E «a blocked replay names the holding and the exclusion travels on
> retry» prova un comportamento che il prodotto non ha più (regge solo perché usa un mock). Vanno via insieme, con
> `test-triage` prima.

> **Checkpoint 3 di F — contenuto rivisto da me** (25/09): 31 percorsi in 8 gruppi disgiunti che coprono l'albero,
> messaggi puliti, cataloghi allineati (3463 chiavi; +11 in `risk.*`, −3 in `risk.assetSet.*` che nessuno usa fuori
> dai file di F — l'unico uso dinamico, `risk.assetSet.ordering.${mode}`, nella heatmap di F non ha più `original`).
> Su `RiskLevelSection` F resta dentro l'eccezione dell'intestazione (icona accanto al toggle, mai dentro); sul file
> di A solo i due `docsPath`. Fuori famiglia, al coordinator: tre frasi `assets.panels.*Hint`, la pagina della lista
> asset e il suo E2E, i file del runner, la voce di CHANGELOG. Inoltrato con il mio OK. Due voci nuove per
> l'integrazione: K10 e K11.

> **Prima di G1**: il mio albero deve essere pulito per la fusione, quindi le note del journal da F5 in poi (F8, il
> giro UI, il principio del developer, K10–K11) vanno in un commit solo, prima della simulazione del coordinator. La
> voce di CHANGELOG proposta da F è arrivata a me: la inoltro con l'handoff combinato a fine giro.

### ⚠️ Fuori pista — il commit del journal fatto dal coordinator, e il segnaposto mancante · 25/09/2026

> Per provare a secco i controlli di `ORDER-r5-41.sh` il coordinator taglia lo script sul segnaposto `# NN ·` prima
> del primo commit; quello script non l'aveva (gli altri sì), così la «copia dei soli controlli» era lo script intero
> e ha creato `3625be46c`. Contenuto identico a quello congelato (impronta verificata da me); il developer lo ha tenuto.
> **Regola da ora**: ogni script ha `# NN ·` prima di ogni blocco di commit, anche se è uno solo, e una guardia
> `GUARDS_ONLY=1` che si ferma dopo i controlli; il coordinator taglia al primo `git … add` e rifiuta se ne resta uno.

### G1 — `dev_release2` → Risk · 🔵 25/09/2026

> **Fusione** `81f762d11` fatta dal developer con lo script del coordinator: pulita, albero identico alla simulazione
> (`385b9ed7`), dentro J (privacy) e A (i suoi 4 commit). `api sync` rifatto (solo file ignorati).
>
> **Validazione nella 6152**: front-portfolio `risk-controller-unit` 54 · `risk-levels-unit` 240 ·
> `risk-frame-component` 13 · `risk-levels-component` 19 · `risk-unit` 17 · `risk-request-unit` 26 ·
> `risk-benchmark-unit` 8 · `allocation-unit` 149 · E2E `risk` 13 e `risk-asset-detail` 2 · `services risk-all` 639 ·
> `api risk` 14 · audit i18n 3441 chiavi, 0 incomplete · `front check` al solito pavimento.
>
> **⚠️ Fuori pista — un rosso mio, di F9, trovato solo adesso**: `schemas risk`
> (`test_risk_error_catalogues_agree_across_languages`) fissa «catalogo `risk.errors.*` = `RiskErrorCode` + il solo
> ripiego `unknown`», e F9 ha aggiunto `risk.errors.answer_discarded`, un codice che emette solo il frontend. La
> verifica di F9 non aveva `schemas risk`, e nemmeno il brief che avevo dato a test-author. Riparazione approvata dal
> coordinator: la relazione diventa «`RiskErrorCode` + i codici del frontend, nominati» (`unknown`,
> `answer_discarded`), in un commit a parte sopra la fusione; la frase resta in `risk.errors`. **Lezione**: una
> chiave nuova sotto un namespace che il backend fissa (`risk.errors`, `risk.warnings`) va verificata anche coi test
> di schema del backend, non solo coi test del frontend.
>
> **Altro rosso, non mio**: `check-orphans` segnala 2 test di A (`e0364c535`) non registrati già nel target; il
> coordinator li ha registrati su `dev_release2` (commit al developer): fino alla prossima sincronizzazione sono
> orfani noti della mia base.

### ⏸ Pausa (25/09, 13:0x) e ripresa (28/09, 10:3x)

> Il developer ha spento la macchina a metà della riparazione di `schemas risk`; alla ripresa (`/tmp` cancellato dal
> riavvio) l'albero aveva solo i due file attesi, e il test di schema conteneva la riparazione finita, senza mutanti
> (`frontend/` e `backend/app` identici a `HEAD`): `schemas risk` 34 ✓. Un test-author nuovo la prova con i mutanti.
>
> **Riparazione del pin** (test-author, prima della pausa): «catalogo `risk.errors` = `RiskErrorCode` + i codici del
> frontend», con i codici del frontend nominati — `unknown` (il ripiego di `translateErrorCode`) e
> `ANSWER_DISCARDED_CODE`, letto **per nome** dal sorgente TS di `riskPanelController`, con errori chiari se la costante
> manca, è dichiarata due volte o non è un letterale — e un controllo che i due insiemi siano disgiunti.

### G1 — privacy accesa e spenta sulla revisione combinata · ✅ 28/09/2026

> Copia rifatta dalla snapshot, 6162 con `--rebuild`, password resettata solo sulla copia. Sulle superfici con
> importi del pannello rischio: schede di L1 3 importi → 0 (`−€•••`), totale del replay 1 → 0, tornado di L4 9 → 0,
> pannello intero 13 → 0; le percentuali restano visibili, com'è giusto. Asset Global: nessun importo anche a privacy
> spenta, coerente con la regola «la pagina non mostra denaro» (controllo debole: non verifica quale tab fosse aperta;
> la prova vera è nell'E2E di F). Nota estetica, non di privacy, già prima della fusione: il totale del replay scrive
> la percentuale con il meno tipografico e l'importo con il trattino (`−X,XX% -€…`) → per il blocco Dashboard di A.
>
> **Da A** (sola lettura, `merge-tree`): `ea30d5ccf` (i due test di A registrati) non è né nel mio ramo né in quello di
> F; `dev_release2` → Risk oggi è pulito; con F esce un solo conflitto additivo, nel catalogo del runner
> (`_frontend_utility.py`, lista `front_utility_unit`), qualunque sia l'ordine: si tengono tutte e tre le righe. La
> base di A resta un fast-forward.

> **La riparazione del pin, provata** (test-author, 28/09): il pin vecchio sui cataloghi di oggi è rosso con
> `answer_discarded` come unica chiave in più; 14 mutanti, tutti presi dal test, con il messaggio giusto per ciascuno —
> la chiave tolta da un catalogo o da tutti, una chiave estranea, la costante rinominata, dichiarata due volte, resa un
> modello o un'espressione, il valore cambiato senza aggiornare i cataloghi, l'insieme del frontend senza `unknown`, e
> un codice del backend con lo stesso nome di uno del frontend (preso **solo** dal controllo di disgiunzione).
> Nessun sopravvissuto, test invariato. `schemas risk` 34 ✓ · `services risk-all` 639 ✓ · `risk-controller-unit` 54 ✓ ·
> ruff e black puliti; i cinque file mutati tornati identici a `HEAD`. Restano fuori dal contratto del lettore (e li
> copre già il test vitest, che fissa il valore della costante) un'ombra `let`, un'ombra di parametro e una
> dichiarazione vecchia lasciata in un commento a blocco.

### G1bis — `dev_release2` (`ea30d5ccf`) → Risk · ✅ 28/09/2026

> Checkpoint del pin e del journal (`5053bf16e` → `3d3ac7c85`), poi la fusione `b9ee8d7be` (i due test di A registrati):
> pulita, albero uguale alla simulazione del coordinator; `check-orphans` pulito (260 test unit, 83 spec).

### G3 — F → Risk · ✅ 28/09/2026

> **Fusione** aperta dal developer con lo script del coordinator: esattamente 5 conflitti, tutti additivi — i 4
> cataloghi e il catalogo del runner. **Risoluzione mia**, con una procedura guardata (HEAD, MERGE_HEAD, insieme dei
> conflitti, e gli stadi `:2:`/`:3:` uguali ai blob dei due genitori, prima di toccare qualcosa):
> - cataloghi: fusione a tre vie **per chiave**, nell'ordine d'inserimento (i cataloghi non sono ordinati), le chiavi
>   nuove di F dopo il loro vicino precedente; calcolata da **entrambe** le basi di fusione (`e6187d6ab`, `14c334d85`)
>   con risultato identico: 3474 chiavi per lingua, 0 conflitti di chiave, 4 chiavi rimosse da F e non più usate;
> - runner: le due righe aggiunte da me e da F, tenute entrambe.
> In stage solo i 5 file; il coordinator ha verificato l'albero per conto suo (identico alla sua unione).
> **Commit fatto dal developer** dal terminale agganciato alla mia sessione (nessun agente ha committato).
>
> **Validazione del combinato nella 6152**: unit rischio (8 categorie) 526 · `core-unit` 2651 · `component-unit` 2033 ·
> `services risk-all` 639 · `schemas` 34 + 70 · `api risk` 14 · `api assets-crud` 35 · `check-orphans` 0 · audit i18n
> 3474/0 · E2E `risk` 13, `risk-lab` 18, `risk-asset-detail` 2, `asset-list` 28 (dopo `front build --debug`). **Un
> rosso previsto**: `front check` segnava `no_price_history` nella mappa esaustiva di F (`eligibility.ts`) — il cancello
> che il coordinator aveva chiesto a F per K1.

### G4 — K1–K11, gli adattamenti al codice di F · ✅ 28/09/2026

> **Test prima della cura** (test-author): rossi per il motivo giusto, e verdi su copie usa-e-getta con le cure.
> - **K1**: la mappa dei motivi di F dice anche `no_price_history`, con la frase nelle 4 lingue; il test legge i motivi
>   dall'enum generato, così un codice nuovo del motore lo fa diventare rosso. `front check` torna ai soliti 3 errori.
> - **K7**: la sezione replay del laboratorio mostra la risposta scartata due volte (il polling della pagina la rende
>   ordinaria), come fa la L4 della Dashboard.
> - **K8**: le sezioni del laboratorio traducono gli avvisi con chiave e parametri del backend, come la Dashboard; un
>   controllo sui sorgenti (col parser di Svelte) impedisce che una sezione nuova torni all'inglese.
> - **K9**: `RiskLevelSection` usa la stessa regola del nome dell'analisi dell'avviso unico (`analyticNameKey`), e la
>   doc delle sue prop non dice più «verbatim». **K10**: via la prop `height` che la heatmap ignorava, con il suo ultimo
>   chiamante (la L2 della Dashboard).
> - K2–K6: nessun adattamento (campi opzionali, o superfici che F non monta). **K11**: una decisione, non codice → nella
>   tabella dei proprietari, per A e il developer.
>
> **Verde e mutanti**: `core-unit` 2664 · `component-unit` 2040 · `risk-levels-unit` 240 · `risk-levels-component` 19 ·
> `risk-frame-component` 13 · `risk-controller-unit` 54 · E2E `risk-lab` 18 e `risk` 13. Undici mutanti: dieci presi
> subito; il sopravvissuto (la sezione che aggira la regola del nome) prende un test di `RiskLevelSection` nuovo, che
> fissa il nome che un livello dà a una misura fallita.
>
> **Per dopo** (dal rapporto di test-author): la sezione replay del laboratorio non mostra i codici d'errore che la L4
> della Dashboard mostra (`resultErrorCodes`) — un cambiamento di comportamento, quindi nel blocco replay, mio; la
> sezione dei livelli di confronto non legge `loadDiscarded` — per F nel giro UI; i mock dell'E2E del laboratorio hanno
> solo `message`, senza `message_i18n_key` (il backend ora le manda) — per F.

### G4 — committato; `dev_release2` con K → Risk · ✅ 28/09/2026

> K1–K11: `a04be75df` → `2e2894742` → `41605d669` → `65a622915` (6 + 6 + 5 + 1 file). Poi la fusione
> `dd85b9317` (`dev_release2` con J, A e K), fatta dal developer con lo script del coordinator: albero come la
> simulazione. **Validazione** nella 6152: unit rischio e `core-unit` 2779 / `component-unit` 2120 (con i test
> `TreeSelect`/`AssetTypeSelect` di K), `services risk-all` 639, `schemas` 34 + 70, `api assets-crud` 35, `api risk`
> 14, `check-orphans` 0, audit i18n 3482/0, `front check` a 3, E2E `risk` 13 · `risk-lab` 18 · `risk-asset-detail` 2 ·
> `asset-list` 28 (con le icone composte di K).
>
> **⚠️ Fuori pista — `api risk` al primo giro, infrastruttura**: la fusione aveva reso vecchia `frontend/build`, e
> l'avvio del backend di test l'ha ricostruita oltre i 120 s del runner. Lezione: dopo una fusione che tocca il
> frontend, `front build --debug` **prima della prima suite che avvia un backend**, non solo prima degli E2E.

### Le voci di K sulla torta · ✅ 28/09/2026

> **Perché**: le icone composte di K sono arrivate davvero (ogni sottotipo ha la sua: ETF con l'azione, ETF con
> l'obbligazione, …, e il tipo nuovo «crowdfunding immobiliare»). Il mio `allocationFamily` metteva gli ETF sotto ETF
> con una regola sua, e lasciava il crowdfunding immobiliare come famiglia a sé: il suo tooltip avrebbe mostrato il
> contenuto due volte (la composta di K più la mia sovrapposizione). Tre test fissavano il mondo prima di K.
>
> **Cura**: la torta prende le famiglie da `assetTypeFamily` di K (il crowdfunding immobiliare va sotto Crowdfunding,
> con il secondo anello come gli ETF); il tooltip mostra **una** icona, quella del tipo — la composta di K per un
> sottotipo; la sovrapposizione e `allocationFamily.ts` se ne vanno (dopo K non poteva più scattare per nessun tipo,
> e la sua regola di famiglia era il difetto). Riscritti i commenti di `allocationRings.ts` e di `allocationHierarchy.ts`
> («quanti membri può avere un gruppo»).
>
> **Test** (test-author, prima della cura): una torta montata in jsdom (`AllocationPieChart.test.ts`) controlla le
> famiglie sui due anelli, la didascalia del membro generico, la legenda e l'icona unica del tooltip, leggendo il
> formattatore vero; i test di anelli e gerarchia usano le funzioni vere di K invece di copie a mano. **15 test tolti**:
> quelli delle due funzioni cancellate, quelli della sovrapposizione prima di K e l'intero gruppo che simulava le
> composite (un mondo a metà che non è mai stato rilasciato). Tre mutanti, tutti presi. `allocation-unit` 142 ✓,
> `risk-levels-unit` 240 ✓, E2E `dashboard`: 10 ✓ e 5 rossi, tutti fra quelli noti del target (GrowthChart di I).
>
> **⚠️ Fuori pista — un difetto più vecchio, trovato dal test nuovo**: per veicolo la famiglia ETF può avere 7 membri
> (l'ETF generico e i suoi sei sottotipi), e la sfumatura, che si muove sulla luminosità in una sola direzione, arriva
> a nero o bianco puro dopo 2–4 passi: gli ultimi sottotipi prendono lo stesso colore, senza tinta (14 posizioni su 14
> delle due palette della torta). Non è di K: è latente da R12-B (24/09). Sui dati del developer non si vede (la sua
> famiglia ETF ha 2 membri), ma con i sottotipi di K una famiglia di 5 o più è normale. Nessun passo lo risolve: serve
> un'altra regola. **Decisione del coordinator**: fuori da questo checkpoint (il test dei 7 membri salvato nei file di
> sessione, da riportare rosso per primo con la cura), voce del giro UI da decidere col developer, con i gruppi fino a
> 3 identici (il grafico storico di I non deve cambiare) — e **cancello per l'ingresso in `dev_release2`**. Il test dei
> 3 membri per contenuto (immobiliare puro, ETF immobiliare, crowdfunding immobiliare) passa oggi e resta.
>
> **Un rosso del target, fuori famiglia**: `front-asset asset-unit` ha 12 rossi in `chartCoreHelpers.test.ts`, tutti
> test che rispecchiano il sorgente del GrowthChart di I; né il test né il grafico sono cambiati dall'inizio del giro, e
> nessuno dei file che legge è fra quelli di questo checkpoint → al coordinator.

## Giro UI rischio — il passaggio visivo del developer · 29/09/2026

Base comune `ffe41c5ba` (A e F in fast-forward); tabella dei proprietari approvata dal developer, con la regola per i
19 componenti che Dashboard e laboratorio hanno in comune: **un proprietario per componente, qualunque pagina lo monti**.
Modello di lavoro: il developer scrive direttamente ad A e a F; io coordino e smisto ciò che tocca pezzi in comune o file
altrui. Passaggio visivo sulla 6162 (copia della snapshot, revisione combinata). Osservazioni, smistate:

| # | dove | osservazione | a chi |
|---|---|---|---|
| V1 | Dashboard, rischio, in cima | l'avviso unico raggruppato piace, ma l'estetica va rifatta | A (`RiskPartialNotice`) |
| V2 | L1 | l'istogramma dei rendimenti giornalieri non ha infobox su nessuna barra (c'è solo il `title` del browser) | A (`l1/ReturnHistogram`) |
| V3 | L1 | le schede vanno bene nei contenuti, non nell'estetica | A (`ui/display/RiskMetricCard`, `RiskCardGrid`: li usano solo L1–L3) |
| V4 | L2 | la matrice ordina solo per somiglianza e nome: servono anche tipo, settore e area (K11 deciso: sì) | F estrae il caricamento condiviso delle mappe, poi A lo collega |
| V5 | L2, sopra la matrice | schede e barre usano ancora `title` invece di solo `Tooltip.svelte`; la lunghezza delle parole (testi troncati) e le barre CSS non vanno bene — da riparlarne quando ci si arriva | A (schede); le barre `ui/display/KpiDivergingFlowBar` sono anche nel pannello KPI principale della Dashboard, fuori famiglia → decisione del coordinator |
| V6 | Dashboard, rischio | servono le stesse icone del manuale del laboratorio, nella stessa posizione, con i link verificati | A (`RiskLevelsPanel` → `docsPath`) |
| V7 | Asset Global, Correlazione | tutto ok | — |
| V8 | Dashboard, torta dell'allocazione | fatta bene | — |

> **V5, precisazione del developer (via coordinator)**: pensava che le barre peso/rischio di L2 fossero un'implementazione
> a sé; saputo che sono lo stesso componente del pannello KPI principale della Dashboard (`ui/display/KpiDivergingFlowBar`),
> ha **ritirato** quelle osservazioni: il componente va rivisto più avanti, con chi avrà il pannello KPI (backlog del
> coordinator). In questo giro nessuno lo tocca. Le schede di L2 (`RiskMetricCard`/`RiskCardGrid`, di A) restano da
> verificare con il developer nella disamina con A, insieme alla V3.

### «Parziale» dove il numero ha perso qualcosa · ✅ backend fatto (29/09/2026)

> **Il reperto** (A, misurato sulla sua copia, che è la snapshot del developer): sulla Dashboard del developer **tutti**
> i risultati del rischio erano «parziali», per **una sola causa** — due crowdfunding senza fonte di prezzo, esclusi
> dalle serie per asset (`missing_price`). Il servizio marca parziale ogni risultato della richiesta quando c'è
> un'esclusione. Ma nella modalità storica del portafoglio la serie principale è il TWRR, che quei due asset li contiene
> già (valutati all'ultimo prezzo di transazione): i numeri di L1 non avevano perso niente. E nella composizione attuale
> il loro peso finiva nella «liquidità», senza nulla che lo distinguesse dalla liquidità vera.
>
> **Decisioni del developer**:
> - ① «parziale» solo dove il numero ha davvero perso qualcosa: `historical_kpi`, `historical_var`, `drawdown_summary` e
>   `comparison`, quando leggono solo il TWRR, non ereditano le esclusioni della richiesta e si giudicano sulla qualità
>   dei dati del portafoglio (generalizza un caso speciale che copriva solo i primi due); correlazione e misure della
>   composizione attuale le tengono;
> - ② gli asset senza prezzo di mercato chiamati col loro nome, separati dalla liquidità, senza cambiare i numeri:
>   `excluded_weight` in aggiunta, sottoinsieme di `cash_weight` (che resta il residuo a rendimento zero) — non con la
>   liquidità vera negativa: vedi il primo Fuori pista qui sotto;
> - (b), su richiesta di A (è un calcolo, quindi nel backend): un motivo `no_price_source` (nessuna fonte configurata:
>   permanente) distinto da `missing_price` (fonte che non ha dato prezzi: occasionale), perché l'avviso di A usi un
>   tono informativo per le cause permanenti e ambra per quelle occasionali (decisione del developer).
>
> Test prima (test-author), poi il codice; A adatta l'avviso, L2 e L3 nei suoi file dopo il mio checkpoint.

> **Il contratto, come l'hanno affinato i test** (test-author, due giri; rosso prima: **37 rossi** — 29 in
> `services risk-all`, 8 in `schemas risk` — più 14 verdi da tenere, fra cui la barriera di presenza nella stessa
> richiesta: la correlazione continua a portare l'esclusione):
> - ① non un booleano ma un enum interno, `RiskSeriesInputs` (`services/risk/base.py`): `PRIMARY` (KPI, VaR, drawdown),
>   `PRIMARY_AND_BENCHMARK` (confronto), `SCOPE_ASSETS` (tutte le altre, il default). Sul TWRR i primi due non ereditano
>   le esclusioni, né l'avviso `assets_excluded`, né `zero_risk_residual_includes_in_transit` (descrive il residuo della
>   composizione, che il TWRR non usa), né `metadata.excluded_assets`. Qualità dei dati: `PRIMARY` → quella del
>   portafoglio; `PRIMARY_AND_BENCHMARK` → quella unita (il benchmark si prepara sul calendario congiunto del perimetro:
>   un suo prezzo riportato oltre la soglia o una data persa lo rendono ancora parziale) **meno** le voci
>   `unusable_assets` degli asset esclusi dal perimetro, che in quel calendario non sono mai entrati — tranne la voce del
>   benchmark stesso quando è un asset posseduto ed escluso: il confronto è allora non disponibile, e la sua qualità dei
>   dati dice perché.
> - La regola segue la **base** (TWRR), non più la modalità: su una fetta (Q-C1, niente TWRR) KPI e VaR passano alla
>   qualità dei dati delle serie per asset da cui sono ricostruiti. Prima prendevano quella del portafoglio e nascondevano
>   l'asset perso: correzione voluta, fissata da un test.
> - ② `excluded_weight` nel contesto e in `RiskContributionOutput`/`RiskReturnOutput` = Σ pesi degli asset del
>   perimetro rimasti senza serie; `cash_weight` invariato; perimetri senza pesi (asset, insieme di asset) → 0 nel
>   contesto, campo assente nei loro payload. I numeri non si muovono: valori d'oro presi su `ffe41c5ba` (tolleranza
>   relativa 1e-12) e identici a quelli dello stesso patrimonio tenuto in liquidità.
> - (b) `no_price_source` = **nessuna** riga in `asset_provider_assignments` **e nessuna** riga in `price_history`: mai
>   prezzato. Una fonte che non ha dato niente, o prezzi manuali fuori dal periodo, restano `missing_price` («fuori» vuol
>   dire dopo: i prezzi di prima vengono riportati avanti e l'asset non è escluso). Una sola istruzione per richiesta
>   (`NOT EXISTS` su tutte e due le tabelle), emessa solo se almeno un'esclusione è `missing_price`. Chiave
>   `risk.warnings.assets_excluded_no_price_source` nelle 4 lingue, scritta per esteso nel ramo (l'audit legge i letterali).
>
> **Note implementazione** (29/09): `base.py` (enum, ClassVar, `excluded_weight` nel contesto), i quattro plugin che
> leggono il TWRR dichiarano la serie, `risk_contribution`/`asset_risk_return` passano `excluded_weight`,
> `schemas/risk.py` (campo con `ge=0`, nessun vincolo verso `cash_weight`), `service.py` (`_reads_the_twrr_alone`,
> `_COMPOSITION_WARNING_CODES`, `_data_quality` senza più il caso speciale codificato per nome, `_scope_exclusions` pura,
> `_never_priced_asset_ids`, ramo letterale dell'avviso), chiave i18n via `dev.py i18n add`. `algorithm_version` in su
> di una minore dove il payload guadagna `excluded_weight` (`risk_contribution` 1.1.0 → 1.2.0, `asset_risk_return`
> 1.0.0 → 1.1.0), come per i due campi aggiunti prima (`drawdown_summary` 1.1.0, `risk_contribution` 1.1.0): un
> `excluded_weight` a zero si distingue così da un server che il campo non lo conosce. Doc (docs-writer, sola EN: le due
> pagine non hanno traduzioni): `data-quality.en.md` — quali risultati portano un'esclusione (e perché gli stress no),
> i motivi con `no_price_source`, il peso escluso, su quale report si giudica ciascun risultato, la **soglia dei 7 giorni**
> definita una volta (i punti riportati la contano: debito del 24/09, mio) e un limite nuovo, «un asset valutato dalle
> sue transazioni sta fermo»; `correlation.en.md` — il motivo dell'asset senza prezzi e la soglia. Verifica nella 6152:
> `services risk-all` **682** · `schemas risk` **43** · `api risk` 14 (dopo `front build --debug` e `db populate --force`)
> · `services ai-export` 922 · `front check` al solito pavimento di 3 · i18n 3483/0 mancanti · `check-orphans` pulito ·
> ruff e black puliti sui 15 file Python. **Mutanti**: 20 su 20 presi (test-author), più un test nuovo scritto apposta
> per M9 (il benchmark posseduto ed escluso tiene la sua voce); due equivalenti dichiarati (il controllo del motivo dentro
> `_scope_exclusions`, perché l'insieme dei mai prezzati contiene solo esclusioni `missing_price`; la guardia su
> `portfolio_data_quality`, mai `None` su un perimetro di portafoglio). I 9 file di produzione ripristinati identici
> (SHA-256). Il salto di versione è venuto dopo i mutanti, anche lui col rosso prima (test-author: il pin di
> `asset_risk_return` e la versione nei metadati dei due risultati, 2 rossi → verdi); dopo, di nuovo `services risk-all`
> 682 · `schemas risk` 43 · `api risk` 14 · `mkdocs build` (strict) e `check-links` verdi.
>
> **⚠️ Fuori pista**:
> - `api risk` rilanciato subito dopo `services risk-all`: 3 rossi su 14, «utente di prova assente». Infrastruttura, non
>   prodotto: le suite `services` ricreano il DB pulito della corsia, quindi prima di `api risk` va rifatto
>   `db populate --force`. Rifatto → 14.
> - Il mio primo contratto aveva un validatore `excluded_weight ≤ cash_weight` e diceva «sottoinsieme». Falso con la
>   liquidità vera negativa (pesi 0,8 e 0,4, il secondo escluso → residuo 0,2, escluso 0,4), e comunque irraggiungibile
>   dal servizio: la liquidità negativa accende `composition_error`, che ferma `risk_contribution` e `asset_risk_return`
>   prima del payload. L'ha trovato test-author; validatore tolto, i due pesi dichiarati come sono.
> - «Qualità dei dati unita, come oggi» per il confronto contraddiceva «un'esclusione da sola non lo rende parziale»:
>   l'esclusione sta proprio in `unusable_assets`, che basta a rendere `partial` la qualità dei dati. Trovato da
>   test-author; regola corretta come sopra.
> - Il ClassVar booleano `reads_scope_asset_series` del primo contratto non bastava: il confronto ha una terza condizione,
>   il benchmark. → l'enum.
> - **Il mio brief al docs-writer conteneva due affermazioni false**, scritte senza guardare il codice: lo stress fra i
>   risultati che ereditano le esclusioni (il replay prepara le sue serie con `excluded_assets=()`, lo shock ipotetico le
>   toglie), e «prezzi vecchi nella storia del portafoglio → KPI, VaR e drawdown parziali» (il report del portafoglio non
>   registra l'età dei prezzi: vedi il primo reperto qui sotto). Durante i mutanti gli avevo vietato di leggere il backend;
>   dopo, leggendolo, le ha trovate e corrette da sé. Stessa forma delle altre volte: descrivere prima di guardare.
>
> **Effetto fuori famiglia** (→ coordinator): AI Export (`ai_export/components/drawdown_context.py`) chiama
> `drawdown_summary` sul portafoglio e sul broker. Ora riporta `ok` dove prima riportava `partial` per un'esclusione
> soltanto, e fra i suoi `warnings` non ci sono più `assets_excluded` né il residuo in transito. `services ai-export`
> resta verde (922: i suoi test usano un servizio finto).
>
> **Reperti fuori perimetro** (trovati dal docs-writer, verificati da me):
> - **Il report del portafoglio non porta mai `stale_prices`**: `build_data_quality_report` ha il parametro
>   `stale_prices_dto`, ma nessuna delle due chiamate in `portfolio_service.py` (`:1250`, `:2624`) lo passa. Il motore
>   calcola `stale_price_asset_ids` punto per punto con la soglia dei 7 giorni (`portfolio_engine.py` ~1101–1130), ma non
>   arriva al report: l'avviso `STALE_PRICE` del banner della Dashboard (`dataQuality.stalePrice`) non può scattare. Fuori
>   famiglia → coordinator. Se lo si ripara, KPI, VaR e drawdown sul TWRR diventeranno `carried_forward` quando la storia
>   del portafoglio usa prezzi vecchi (giusto), e la frase di `data-quality.en.md` «quel report registra ciò che non si è
>   potuto valutare, non quanto è vecchia una valutazione» andrà cambiata insieme.
> - **`user/assets/correlation.en.md:154`** (la guida del laboratorio; scritta da A in `b67b8ba79`, superficie di F, sola
>   EN) dice che basta un giorno di prezzo riportato per marcare **Parziale** e cita la nota inglese: falso dalla soglia
>   dei 7 giorni del 24/09 (mia), e la nota ora è la frase tradotta dei prezzi vecchi → a F.
>
> **Limiti noti, non fissati**: un'esclusione `missing_fx` lascia la sua coppia in `unresolved_fx_pairs`, che non si può
> ricondurre a un asset, quindi il confronto sul TWRR resta parziale per lei (di norma lo stesso cambio mancante rende
> parziale anche il report del portafoglio, e con lui KPI, VaR e drawdown: non fissato da un test). Un prezzo vecchio
> (oltre 7 giorni) di un **asset posseduto** sul calendario congiunto rende parziale il confronto sul TWRR anche se i
> numeri del benchmark non ne dipendono: il conteggio dei punti riportati è aggregato (`carried_forward_price_points` è
> un intero), e togliere quelli degli asset posseduti richiederebbe un conteggio per asset che `DataQualityReport` (del
> portafoglio) non ha. Nella qualità dei dati
> del risultato, un asset `no_price_source` resta `missing_price` in `unusable_assets` (l'enum `DataQualityExclusionReason`
> è del portafoglio): il motivo da leggere è in `metadata.excluded_assets` e nel `details.reason` dell'avviso.
> `asset_risk_return` riporta l'errore di composizione della liquidità negativa come `insufficient_history`:
> comportamento esistente, fuorviante → backlog.
>
> **Poi A**, nei suoi file e dopo il checkpoint (e dopo `api sync`, perché il client generato non è versionato): l'avviso
> (tono informativo per `no_price_source`, ambra per il resto), la scheda «non misurato» di L2 e la nota sotto lo
> scatter di L3, su `excluded_weight` invece che su `cash_weight`.

### Commit, fusione di `dev_release2` e le primitive per l'avviso di A · 29/09/2026 (sera)

> **Commit del «parziale»** (developer, 22:26), verificati: `56b0c36bd` (i18n, 4 file) · `20eff079e` (backend, test e
> runner, 15) · `a8fdf9f1d` (doc, 2) · `7840fa7df` (journal, 1); messaggi identici a quelli proposti, albero pulito. A in
> avanzamento semplice a `7840fa7df` (22:31); F resta dov'è (lavoro del giro non ancora committato).
>
> **`dev_release2` → Risk = `25b8a5766`** (22:47; genitori `7840fa7df` + `5068b706c`): i seguiti di K (font delle
> bandiere, selezione delle transazioni, titolo della scheda), il CHANGELOG, due voci di journal. Un solo conflitto,
> `LibreFolio_devWiki/log.md`: tutte e due le parti avevano aggiunto in coda (le due voci di F del 23 e del 25/09 da qui,
> quella di K del 29/09 da là). Risolto aggiungendo, in ordine di data, con uno script guardato (additività controllata
> nei due versi, 97 + 2 + 1 = 100 intestazioni, blob `7f546cc3`); messo in stage solo quel file; albero `991c4d8b`,
> identico alla prova del coordinator. Validazione nella 6152: `front check` al pavimento di 3 · i18n 3483/0 ·
> `check-orphans` pulito · `front build --debug` · unit `risk-unit` 17, `risk-request-unit` 26, `risk-benchmark-unit` 8,
> `risk-controller-unit` 54, `risk-levels-component` 22, `risk-frame-component` 13, `risk-levels-unit` 241,
> `allocation-unit` 142, `core-unit` 2784, `component-unit` 2120 · `services risk-all` 682 · E2E `risk` 13, `risk-lab` 18,
> `risk-asset-detail` 2, `asset-list` 28, `document-title` 22.
>
> **Decisione del developer sull'avviso in cima** (via A): gli asset esclusi diventano **badge per asset** (icona e nome
> barrato, come nel laboratorio) con una frase breve per causa, scritta da A nelle sue chiavi; la frase completa del
> backend resta il ripiego quando la causa manca. Il badge è **un solo componente**: F estrae il chip del laboratorio in
> `risk/AssetChip.svelte`, suo come la heatmap (varianti `default | warning | excluded`, `help`, `testId`, snippet finale,
> `data-*`, `data-variant`), nel suo checkpoint; A lo monta dopo F → Risk → A. Regola del coordinator: A non modifica
> `L2Diversification.svelte` finché questo checkpoint non è nel suo ramo.
>
> **Questo checkpoint** — le primitive chieste da A, nei miei file:
> - `ResultReason.reason` e `ResultReason.assetIds` (`levelHelpers.ts`, letti in `warningSentence.ts`): la causa da
>   `details.reason`; gli asset come il backend li legge per nominarli nella frase (`_warning_asset_ids`: `asset_ids`,
>   altrimenti un solo `asset_id`), tutto o niente sugli interi. Una frase fusa li tiene solo finché tutti gli avvisi
>   dietro di lei concordano, e non li riprende più: il ripiego non tradotto dice ogni esclusione con le stesse parole, e
>   una causa permanente letta su uno potrebbe essere occasionale su un altro.
> - `uncoveredWeight()` → `{total, unpriced, cash}`: `total` è `cash_weight` e `unpriced` è `excluded_weight`, tutti e
>   due così come sono pubblicati (mai una somma delle parti, nessun tetto); `cash` è la differenza, che sotto `1e-9` vale
>   zero — la tolleranza che il servizio del rischio usa già sui pesi (`service.py`, controlli della leva e del residuo in
>   transito). Si legge da qualunque uscita della composizione attuale che pubblica i due pesi, senza guardare `kind`:
>   `risk_contribution` (L2) e, su richiesta di A, anche `asset_risk_return` (L3). A passa L3 a questa funzione e toglie
>   i suoi due gemelli (`uncoveredShares()`, `cashWeight()`) nel suo checkpoint.
> - `L2Diversification.svelte:87` → `?.total ?? null`, con l'OK di A: la scheda di L2 non cambia; la didascalia la
>   riscrive A.
>
> **Note implementazione**: test prima (test-author, 18 rossi su `25b8a5766`, provati su un'implementazione usa e getta e
> 21 varianti sbagliate fuori dal worktree), poi il codice. Verde nella 6152: i due file 144 · `risk-levels-unit` 258 ·
> `risk-levels-component` 22 · `risk-frame-component` 13 · `risk-controller-unit` 54 · `core-unit` 2784 ·
> `component-unit` 2120 · `front check` al pavimento di 3 · prettier pulito · E2E `risk` 13 (`data-uncovered` sempre
> 0.05) e `risk-lab` 18. **Mutanti** sul codice vero: 15 su 16 presi (M15 dall'E2E `risk`: `data-uncovered` «0» invece
> di «0.05»). **M16 sopravvive** (`?? 0` al posto di `?? null` in `L2Diversification.svelte:87`): non è equivalente —
> con il contributo assente, non disponibile o fallito la scheda comparirebbe con uno 0 % falso — ma è un buco di test
> del componente di A che c'era già (nessun test fissa l'assenza della scheda) → il test jsdom lo scrive A nel suo
> checkpoint. Quattro mie decisioni sopravvivevano perché nessun test le fissava (`reason` ripulito, `null` che ripiega
> su `asset_id`, insiemi con doppioni, nessun tetto a `unpriced`) → fissate, ciascuna con il suo mutante preso. Poi le
> aggiunte di A, di nuovo col rosso prima (3 rossi sulla tolleranza, un controllo che non mangi la liquidità vera, un test
> che fissa la lettura di `asset_risk_return`): i due file 153. **Ultima passata** sul codice nuovo: M17 (niente
> tolleranza), M18 (tolleranza da `1e-2`, mangia la liquidità vera), M19 (tolleranza anche sul totale) e il controllo su
> `kind` presi; M20 (`<=` al posto di `<`) equivalente sui valori fissati e M21 (tolleranza anche su `unpriced`) **non**
> equivalente — un asset «polvere» senza prezzo sparirebbe dalla scheda mentre l'avviso ne mostra il badge → fissati
> tutti e due (il limite è stretto come nel controllo del residuo in transito del backend), ciascuno col suo mutante
> preso. Finale: i due file **155** · `risk-levels-unit` **269** · `risk-levels-component` 22 · `front check` al
> pavimento di 3 · prettier pulito · i 3 file di produzione identici alla loro impronta dopo ogni mutante.
>
> **⚠️ Fuori pista**:
> - Il mio esempio per «`total` non è una somma» (0,3 e 0,1) non distingueva niente: `0,1 + (0,3 − 0,1)` torna
>   esattamente 0,3 in virgola mobile. test-author ha scelto 0,45 e 0,1, con una guardia che lo verifica.
> - Nel contratto avevo scritto «`asset_ids` presente ma non valido → nessun ripiego su `asset_id`», senza dire cosa fa
>   un `null`: deciso come il backend, `null` vale assente e si passa ad `asset_id`.
> - Il mio «a zero se lo supererebbe» toglieva solo il rumore negativo. A l'ha misurato: il backend pubblica i due pesi da
>   due somme separate, e senza liquidità vera la loro differenza vale zero o un'unità dell'ultima cifra da una parte o
>   dall'altra — positiva in circa un caso su quattro su portafogli simulati — e bastava per scrivere «0 % in liquidità».
>   Sistemato con la tolleranza del backend, non con una soglia nuova del frontend.
>
> **Limiti noti**: il client generato dà a `excluded_weight` il valore 0 quando manca (`default(0)` di Zod), quindi un
> campo assente si leggerebbe «tutta liquidità»; non succede, perché backend e frontend escono nella stessa immagine e il
> backend lo manda sempre (a distinguere resta `algorithm_version`). Gli avvisi di dati vecchi o mancanti portano
> `asset_ids` ma la causa in `details.cause`: avranno i badge e non `reason`, quindi l'ambra. Il «tutto o niente» sugli
> id è più severo del backend, che scarta i valori non interi e tiene gli altri: oggi il backend non ne manda mai.

### Il laboratorio di F in Risk, il nodo del calendario e le guide dei segnali · 30/09/2026

> **Commit delle primitive per A** (developer, 10:01), verificati: `91e91346c` (5 file) · `d618e80ed` (journal); A avanzato
> a `d618e80ed` con i suoi 9 file non committati intatti. 6162 spenta: serviva `ffe41c5ba`.
>
> **Checkpoint 4 di F → Risk.** Il developer l'ha approvato dopo la review sulla 6164. Letto da me prima del commit, in
> sola lettura: le due superfici fuori famiglia (la callback `onfitperiod` di `assets/+page.svelte`, le 4 righe del
> runner) sono esattamente le eccezioni concesse; i cataloghi hanno solo le 3 chiavi `risk.assetSet.fitPeriod.*`;
> `AssetChip.svelte` rispetta l'interfaccia approvata; la modifica della heatmap non cambia niente sulla L2 di A; l'ordine
> dei commit regge (`check-orphans` rosso da C1 a C6, accettato dal coordinator: i test si registrano in C7). Fusione
> prevista pulita con `merge-tree` su un clone usa e getta, poi confermata sui commit veri. Commit di F (10:18):
> `d613d443d` … `506d17f18`. **Fusione `881941e44`** (10:20; genitori `d618e80ed` + `506d17f18`, albero `f81095c3` come
> previsto; script con `--no-commit` e controllo dell'albero prima del commit). Validazione nella 6152: `front check` al
> pavimento di 3 · i18n 3486/0 · `check-orphans` pulito · unit `risk-levels-unit` 269, `allocation-unit` 142,
> `core-unit` 2843, `component-unit` 2161 · E2E `risk` 13 (la heatmap sulla L2), `risk-lab` 22 (il chip nel
> laboratorio), `risk-asset-detail` 2, `asset-list` 28. F avanzato sulla punta (10:36), poi la sua guida sotto la regola
> dei 7 giorni (`73ba9f08e`, `b26ca6e29`): i cinque motivi del replay che descrive coincidono con `replay_coverage`.
>
> **Il nodo del calendario** (da F, sulla sua L1°; il motore è mio). Le righe del weekend che justETF salva (il venerdì
> ripetuto) sono trattate come quotazioni fresche, quindi entrano nel calendario come osservazioni a rendimento zero.
> **Non è nuovo e non è solo del laboratorio**: il TWRR del portafoglio ha un punto per ogni giorno di calendario, quindi
> la «giornata storta» della Dashboard è da sempre per giorno di calendario e il suo «mese storto» (21 osservazioni) copre
> circa 3 settimane. Stima teorica: VaR giornaliero sottostimato di circa il 10 %, mensile di circa il 16 %. Non
> cambiano volatilità, Sharpe e Sortino (la frequenza osservata compensa), drawdown, replay, shock, correlazione,
> rendimenti. La simulazione ha l'errore opposto: sui dati solo feriali «365 giorni» sono 365 sedute.
>
> **Decisioni del developer** (30/09, mattina):
> - «sì, approvo tutto il piano»: (1) una riga di **sabato o domenica — o di un festivo di borsa —** che ripete
>   *esattamente* l'ultima chiusura è un riporto, non una quotazione (niente «uguale al giorno prima → ignora» su tutti i
>   giorni: toglierebbe i giorni feriali piatti veri); (2) il TWRR si legge solo nei giorni con almeno una quotazione
>   vera, concatenando gli altri; (3) gli orizzonti in giorni di calendario («mese» = 30 giorni), convertiti in
>   osservazioni con la frequenza osservata, simulazione compresa; **prima i numeri prima/dopo sui suoi dati, poi il
>   codice**.
> - **I festivi**: dai calendari di QuantLib, come **unione** delle borse principali («ci serve solo per sapere se
>   potenzialmente è un giorno di festa»); la regola resta la ripetizione esatta, quindi un festivo di troppo costa al più
>   un giorno piatto vero. **La tabella si genera a ogni avvio, in un processo separato** (scelta del developer, dopo la
>   spiegazione del perché il server web non importa QuantLib: i worker nascono in modalità `spawn` e reimportano tutto,
>   quindi un import nel padre non risparmierebbe memoria ai worker e terrebbe circa 170 MB sempre occupati).
> - Il coordinator: la regola del riporto è **un solo helper condiviso**, che userà anche `signal_series_preparation.py`
>   (anche gli indicatori tecnici contano oggi le righe del weekend come osservazioni).
>
> **Le guide dei segnali di rischio** (punto 8 dell'analisi di K, riassegnato a me dal developer): `docs_path` su
> `RISK_DRAWDOWN` (`current-drawdown/`), `RISK_ROLLING_RETURN` e `ASSET_CALENDAR_ROLLING_RETURN` (`fundamentals/returns/`),
> `RISK_ROLLING_VOLATILITY` (`volatility/`), `RISK_ROLLING_SHARPE` (`sharpe-ratio/`), `RISK_ROLLING_BETA`
> (`beta-active-return/`). Test prima (test-author): `docs_path` obbligatorio per **tutti** i segnali registrati,
> nascosti compresi, con forma fissata (relativo, barra finale, minuscole: su macOS un maiuscolo passerebbe in locale e
> darebbe 404 sul sito), pagina `.en.md` esistente e tabella dei sei valori; rosso sui sei codici, poi verde.
> Verifica: `services signal-plugin-matrix` 65 · `signal-registry` 65 · `signal-contracts` 10 · `api signal-catalogs` 4 ·
> `check-links` 88 validi (erano 83: i 5 percorsi nuovi sono visti dal gate).
>
> **⚠️ Fuori pista**: `ASSET_CALENDAR_ROLLING_RETURN` è nascosto dal catalogo (`catalog_visible = False`): il suo
> `docs_path` non fa comparire nessun pulsante, perché la pagina dell'asset disegna quella serie senza `DocsLink` →
> decisione dell'interfaccia, di I (segnalata al coordinator).

### Il calendario di borsa nel motore — giro 1: riporti, festivi e TWRR · 🔵 30/09/2026

> **Numeri prima del codice** (copia di prod, sola lettura, script e cifre solo in `/tmp`): sull'anno, il VaR
> giornaliero della Dashboard sale di circa un terzo e quello mensile di circa un quarto; nel laboratorio il VaR
> giornaliero sale del 5–20 % e la volatilità non si muove (la frequenza osservata compensa); un insieme di soli ETF
> passa da f ≈ 360 a f ≈ 256, quindi i «365 giorni» della simulazione diventerebbero 1,43 anni di sedute senza la
> conversione del giro 2. Il developer: «Procedi con l'implementazione, test prima».
>
> **Confini concessi dal coordinator**: l'aggancio in `main.py` (avvio come il prewarm dei provider, rilascio allo
> spegnimento accanto a `shutdown_quant_worker_pools()`, senza mai aspettare la costruzione); lato segnali
> `signal_series_preparation.py`, nel passo dopo, con l'RSI 14 misurato prima e dopo.
>
> **Test prima** (test-author): 55 rossi su cinque file (`test_market_calendar.py` nuovo, registrato in
> `RISK_SERVICE_TEST_PATHS`; `test_series_preparation.py`, `test_risk_eligibility.py`, `test_risk_service.py`). Tre sue
> scelte accettate: il punto base del TWRR resta sempre; l'uguaglianza è numerica (`101.50 == 101.5`); il confronto è
> sulla chiusura **nativa**.
>
> **Note implementazione**
> - `backend/app/services/market_calendar.py` (nuovo): la regola in un helper solo, `is_market_closed_repeat(day, close,
>   previous_close, holidays)`: sabato, domenica o festivo dell'unione, e chiusura *identica* alla riga precedente. La
>   tabella dei festivi (`build_market_holidays`) è l'unione dei giorni feriali di chiusura di TARGET, Borsa Italiana,
>   Xetra, Euronext Paris, LSE, SIX e NYSE fra il 1970 e il 2100, e QuantLib si importa **solo** dentro quella funzione.
>   `ensure_market_holidays()` la costruisce una volta in un processo `spawn` a sé (demone, 120 s al massimo, chiuso
>   alla fine); chi aspetta passa da `asyncio.shield`, quindi l'annullamento di una richiesta non annulla la
>   costruzione. Se fallisce: tabella vuota (resta la regola del weekend) e un nuovo tentativo dopo 10 minuti.
>   `start_market_holiday_prewarm()` all'avvio, `shutdown_market_holidays()` allo spegnimento (termina il processo e
>   annulla il task, senza aspettare).
> - `series_preparation.py`: `_mark_market_closed_carries()` segna i riporti come valori riportati in avanti (con la
>   data della chiusura vera), quindi non entrano nel calendario congiunto; `quote_dates` per asset in
>   `PreparedAssetSeries`; `prepare_asset_series_set(..., market_holidays=frozenset())`.
> - `risk/eligibility.py`: le 20 quotazioni si contano con la stessa regola (finestra `LAG` in SQL).
> - `risk/service.py`: la tabella si aspetta una volta per `execute`, per `asset_eligibility` e per il replay; il TWRR
>   si legge solo nei giorni in cui almeno un titolo posseduto ha una quotazione vera (`_held_quote_dates`), gli altri
>   giorni si concatenano nel successivo, e la copertura si misura su quei giorni.
> - Verde: `services risk-all` 737; i due rossi rimasti erano previsti (una fixture che finiva di sabato, un pin degli
>   argomenti del loader del replay) e li riallinea test-author.
>
> **⚠️ Fuori pista**: in QuantLib 1.43 `ql.Switzerland()` non ha l'enum del mercato (`.SIX` non esiste): il calendario
> svizzero è quello e basta. E Xetra è aperta il 31/12/2025, ma nell'unione quel giorno resta festivo per gli altri: è
> la conseguenza voluta dell'unione, che costa al più un giorno piatto vero.

### Il calendario di borsa nel motore — giro 2: gli orizzonti in giorni di calendario · ✅ 30/09/2026

> **Test prima** (test-author): 34 rossi sul contratto (VaR 16 + 2 Vitest, simulazione 23 fra motore e plugin, meno le
> guardie già verdi), 9 sulle mie decisioni, 8 sul cambio di nome. Riallineati senza indebolirli: i 6 test di schema
> che costruiscono `RiskVarCvarOutput`, la relazione dell'oracolo (ora passa da `horizon_observations`) e il dizionario
> esatto del rifiuto del blocco. La copia congelata del resampler che il test-author aveva scritto come oracolo è
> diventata valori catturati sul codice intatto (`10b0b0d48`), con `rel=1e-12`: i test provano il prodotto di oggi.
>
> **Mie decisioni sulle ambiguità del test-author**: una sola conversione, `calendar_days_to_observations` in
> `risk/metrics.py` (modulo puro, lo importa anche il worker `spawn`); la lunghezza del blocco si confronta con la
> storia in osservazioni, sia nel plugin (`INVALID_PARAMETERS`, dettaglio nuovo `block_length_observations`) sia nel
> validatore del motore; il budget delle risorse resta in giorni di calendario (per eccesso); `steps_per_year` è
> rifiutato da GBM e deve essere > 0; l'ordine dei rifiuti di `historical_var` resta quello (prima la serie, poi f);
> la mappatura a scala (un giorno senza passo ripete il precedente: niente borsa, niente movimento).
>
> **Note implementazione**
> - `metrics.py`: `calendar_days_to_observations(giorni, f) = max(1, round(giorni × f / 365))`. I parametri di
>   `horizon_compounded_returns`, `historical_var_cvar` e `estimate_drift_uncertainty` si chiamano ora
>   `horizon_observations`: ricevono osservazioni, e il vecchio nome `horizon_days` è quello che aveva nascosto C2 e C3.
> - `historical_var` 3.0.0 e `asset_set_var` 2.0.0: `horizon_days` in giorni di calendario, composti su `n` osservazioni
>   con la frequenza osservata; campo obbligatorio nuovo `horizon_observations` nelle due uscite; il controllo della
>   storia insufficiente conta le finestre (`N − n + 1`) e i dettagli portano giorni e osservazioni.
> - Simulazione 4.0.0: `SimulationEngineRequest.steps_per_year` (solo bootstrap; assente = 365, cioè il motore di
>   prima, identico al byte). Il resampler converte orizzonte, regimi e blocco in passi; la deriva della crisi è per
>   anno di passi; i percorsi tornano ai giorni di calendario (giorno d → passo ⌊d × passi / giorni⌋), quindi la banda
>   ha sempre `horizon_days + 1` punti e il frontend non cambia; la dichiarazione resta in giorni di calendario. Il
>   plugin passa la f osservata; l'incertezza della deriva si compone su `n` osservazioni, per GBM e bootstrap.
> - Frontend: `MONTHLY_VAR_HORIZON_DAYS` 21 → 30; `api sync` (il client generato è ignorato da git).
> - Fixture di A e F, con il loro OK una tantum: `risk-analysis.spec.ts` (A: la copia della costante e il mock),
>   `risk-lab.spec.ts`, `AssetSetComparisonLevels.test.ts`, `AssetSetLossComparisonSection.test.ts`,
>   `assetSetLevels.test.ts` (F); `risk-mocks.ts` è mio.
>
> **Verifica** (6152, un comando per volta): `services risk-all` 789 · `schemas risk` 47 · `series-preparation` 22 ·
> `asset-signals` 20 · `signal-plugins-core` 46 · `signal-plugin-matrix` 65 · `signal-service` 50 · `signal-runtime` 6 ·
> `ai-export` 922 · `api risk` 14 (dopo `db populate --force`) · `check-orphans` pulito · `front check` al pavimento
> di 3 · `risk-levels-unit` 269 · `core-unit` 2845 · `component-unit` 2161 · Vitest della cartella del rischio 796 · E2E
> `risk` 13, `risk-lab` 22, `risk-asset-detail` 2 (dopo `front build --debug`).
>
> **Misura sulla copia di prod, con il codice vero** (cifre solo in `/tmp` e in chat): coincide col prototipo del
> mattino. Il TWRR di un anno ha 255 osservazioni con f = 255,7 e il mese di 30 giorni vale 21 osservazioni; l'insieme
> degli asset quotati ha f = 256; la simulazione di 365 giorni fa 256 passi e pubblica 366 punti.
>
> **⚠️ Fuori pista**
> - Avevo scritto a F che `assetSetLevels.test.ts` non rompeva nessun cancello: falso. Il suo `assetSetLevels.ts` legge
>   le uscite con Zod, e un tipo largo (`Record<string, unknown>`) nasconde il campo mancante a svelte-check ma non a
>   runtime: 6 rossi. Un campo obbligatorio nuovo rompe ogni fixture che passa dal parser, non solo quelli tipizzati:
>   si cercano le chiamate al parser, non i tipi. Corretto con un secondo OK di F.
> - Nel brief avevo scritto 50 × 252 / 365 → 34: è 34,52, quindi 35. L'ha preso il test-author.
> - Il bootstrap a blocchi non ha una pagina di teoria nel manuale: debito di prima, lasciato alla ripresa della
>   simulazione che il developer ha rimandato.

### `comparison` — una regressione del giro 1, trovata dal docs-writer · ✅ 30/09/2026

> **Il difetto**: il confronto con un benchmark accoppiava per data i ritorni del primario e quelli del benchmark. Dal
> giro 1 il TWRR del portafoglio ha ritorni solo nei giorni di osservazione, mentre il benchmark resta sul calendario
> congiunto, che contiene anche i giorni quotati solo da lui (un benchmark cripto nel weekend, un ETF americano in un
> festivo europeo): lì il suo ritorno cadeva, e il successivo veniva accoppiato a un ritorno del TWRR su un intervallo
> più lungo. Prima del giro 1 non poteva succedere, perché il TWRR aveva ogni giorno di calendario. L'ha trovato il
> docs-writer leggendo `comparison.py` per scrivere la frase giusta nel manuale.
>
> **La cura** (`comparison` 1.1.0, test prima): le due serie si compongono fra le date che condividono. Fino alla prima
> coppia, una data del primario senza ritorno del benchmark cade e l'intervallo riparte da lì (un benchmark che parte
> tardi si aggancia dall'ultima data che non poteva rispondere); dopo, quella data non è un confine: l'intervallo va
> avanti dall'ultima data condivisa e alla successiva si compongono entrambe le serie. Un solo ritorno per lato si
> prende così com'è, quindi su un calendario comune (un asset, la composizione attuale) il risultato è identico al byte.
>
> **⚠️ Fuori pista**: la mia prima versione faceva ripartire l'intervallo da ogni data scartata, e non era esatta quando
> il benchmark non ha ritorni dentro l'intervallo scartato (il suo ritorno successivo parte da prima). Di nuovo il
> docs-writer, descrivendo la regola, ha trovato il caso; il contratto è passato a «fra le date condivise», con un
> test rosso prima e il vecchio caso di metà finestra riscritto.
>
> **Mutanti** (test-author, su produzione, impronte dei 14 file controllate prima e dopo ciascuno): 46 sui giri 1 e 2,
> 43 presi dai test esistenti; i 3 sopravvissuti sono ora presi da 2 test nuovi e 1 stretto — il confronto sulla
> chiusura nativa e non su quella convertita (una quotazione in dollari che ripete la chiusura mentre il cambio si
> muove), il punto base del TWRR in un festivo della borsa posseduta, lo spegnimento che deve fermare il processo nel
> momento in cui ritorna. Poi 10 su `comparison` nel contratto finale, tutti presi.
>
> **Verifica finale** (6152): `services risk-all` 799 · `schemas risk` 47 · `api risk` 14 (dopo un nuovo
> `db populate --force`: il DB della corsia era stato ricreato dalle esecuzioni intermedie) · `check-orphans` pulito ·
> ruff, black, prettier e `git diff --check` puliti · `mkdocs build` rigoroso senza avvisi e `check-links` 88 validi
> (docs-writer). Il frontend non è cambiato dopo gli E2E e la cartella Vitest del rischio (796).
>
> **Manuale** (docs-writer, solo EN, pagine senza traduzioni): `value-at-risk` (T = N − n + 1 con n dall'orizzonte in
> giorni di calendario; i numeri dell'esempio a h = 10 ricalcolati; il riquadro che diceva il conteggio dei metadati
> «già al netto dell'orizzonte» era falso), `observed-annualization` (i giorni di osservazione del portafoglio; la
> copertura; il calendario congiunto è un'unione, non un'intersezione), `data-quality` (la sezione nuova «Stored
> Carries»), `historical-replay` (il replay prepara le sue serie, non «le stesse»), `benchmark-selection` (la coppia fra
> le date condivise).
>
> **Restano** (non in questo checkpoint): il passo dei segnali (`signal_series_preparation.py`, concesso, con l'RSI 14
> prima e dopo; `price_query.py` riceve oggi solo la regola del weekend, i festivi lì sono fuori famiglia); la frase
> di `historical-replay.en.md:59` («refuses to run and asks for a decision»), falsa da prima, va al blocco replay; la
> guida di F (`user/assets/correlation.en.md:99` e la regola 2 di `:153`) va riallineata da F; il bootstrap a blocchi
> non ha una pagina di teoria.

### F in Risk, la guida di F e gli indicatori tecnici sui giorni di quotazione · ✅ 30/09/2026 (pomeriggio) – 01/10/2026

> **Commit** (developer), verificati dal coordinator: il checkpoint del calendario `1996b84e4` … `95051fa8a`; la
> fusione F → Risk `3c46c8e60` (genitori `95051fa8a` + `1b62abd2e`, albero `25235c91`), aperta con `--no-commit`,
> adattati da me i due fixture nuovi di F (`SORT_DAILY_VAR`/`SORT_MONTHLY_VAR`: `horizon_observations`, il mese a 30
> giorni, con l'OK di F) e validata prima del commit (`risk-lab` 26, `asset-list` 28, unit e `front check` al
> pavimento); F in fast-forward. Poi la guida di F dopo il calendario (`31cff1e5e`, `3eff35036`).
>
> **Il passo dei segnali era più grande del previsto.** La query dei prezzi (`_build_backward_filled_series`) dà agli
> indicatori tecnici un punto per ogni giorno di calendario, riempiendo weekend e festivi con l'ultima barra, e i
> plugin calcolano su tutti: su **ogni** asset, non solo su quelli di justETF. La regola dei riporti da sola avrebbe
> cambiato solo i conteggi della copertura, non un valore. Misurato sugli asset del developer (ultimo anno, cifre
> solo in `/tmp`): RSI 14 si sposta in media di 2,5–3 punti (fino a 7–10) e resta fuori da 30–70 molto più spesso
> (54 giorni contro 32); SMA 200 copre 199 giorni di calendario (circa 140 sedute) e il suo livello cambia fino al 9 %;
> la larghezza delle bande di Bollinger cambia in media del 18 %; l'istogramma del MACD cambia segno in un giorno su
> sette circa; l'ATR (una sola fonte con OHLC) del 6 % in media; l'EMA 20 poco (sotto l'1 % in media).
>
> **Decisione del developer**: «Sui giorni di quotazione, come la definizione standard: SMA 200 = 200 sedute». Il
> coordinator me la assegna, sul mio ramo, con le superfici concesse (`price_query.py`: marcatura dei riporti
> nell'ingresso dei segnali, l'attesa della tabella dei festivi, i festivi ai segnali di rischio, il moltiplicatore
> del riscaldamento; `api/v1/fx.py`: solo il moltiplicatore; `technical_shared.py`: il moltiplicatore FX e le versioni
> dei componenti) e un vincolo (`backend/app/services/fx.py` resta fuori: c'è la PR #28 di un contributore).
>
> **Il piano**, approvato dal developer («Sì, procedi con il piano, test prima»):
> 1. un giorno di quotazione è un punto senza `backward_fill_info`; i riporti salvati diventano riempiti alla fonte;
> 2. la copertura resta di calendario (il frontend non cambia: i grafici allineano per data e le linee scavalcano il
>    weekend);
> 3. il servizio dei segnali passa al plugin solo i giorni di quotazione dei punti scelti, per i plugin con
>    `computes_on_quote_days` (vero per i 17 indicatori tecnici; falso per `calendar_rolling_return`, che ha finestre
>    di calendario per definizione, e per i 5 segnali di rischio, già sulle serie preparate);
> 4. il riscaldamento carica punti × 2 giorni di calendario;
> 5. versioni: i 17 plugin a 2.0.0, i 5 segnali di rischio minori, i componenti tecnici dell'AI Export da 1 a 2;
> 6. il manuale (EN): i periodi in sedute.
> Nessun test di altri rami fissa valori assoluti degli indicatori; nel mio blocco si riallineano alcuni test
> dell'AI Export e del servizio dei segnali.
>
> | passo | stato |
> |---|---|
> | test rossi (test-author) | ✅ 44 test, 32 rossi per il motivo giusto, provati contro una simulazione del contratto |
> | implementazione, versioni | ✅ |
> | mutanti | ✅ 14 presi; i 2 sopravvissuti (Q-3, Q-9a) presi da 2 test nuovi, più un test diretto per Q-1 |
> | prove dell'AI Export, numeri prima/dopo col codice vero | ✅ |
> | manuale (docs-writer) | ✅ 21 pagine EN (gli indicatori, `indicators/index`, `ai_export_sampling.md`); ha trovato le due regressioni UI qui sotto |
> | UI: i periodi in sedute (unità e suggerimenti) | ✅ 30/09 |
> | UI: le bande di Bollinger e Donchian sul weekend | ✅ 30/09 — riempite fra due punti; concessione rivista dal coordinator |
> | checkpoint | ✅ committato il 30/09: `9d410e4de` · `840bdbc0d` · `6f455dee6` · `d800882b2` (67 percorsi, verificati dal coordinator) |
>
> **Mie decisioni sulle ambiguità del test-author**: un giorno di quotazione è un **prezzo** genuino (`days_back == 0`),
> anche se il cambio è riportato, come per il motore e per l'AI Export: altrimenti le ultime sedute sparirebbero
> quando la sincronizzazione dei cambi è in ritardo; `calendar_rolling_return` passa a 1.4.0 (valori e date uguali,
> ma sui riporti salvati ora dichiara il riporto); un intervallo visibile di soli weekend è non disponibile.
>
> **Note implementazione**
> - `signal_plugins/base.py`: `computes_on_quote_days` (vero di default; falso su `calendar_rolling_return` e sui 5
>   segnali di rischio, già sul calendario delle serie preparate). I 17 indicatori a 2.0.0; i 5 segnali di rischio
>   minori; `calendar_rolling_return` 1.4.0.
> - `signal_series_preparation.py`: `is_quote_day`, `quote_day_points`, `SESSION_WARMUP_DAY_MULTIPLIER = 2`.
> - `signal_service.py`: il piano separa i punti di riscaldamento in sedute, calendario e serie preparate
>   (`max_history_days_before_visible`: sedute × 2 giorni di calendario); dopo la selezione il plugin riceve solo le
>   sedute; la copertura resta di calendario.
> - `price_query.py`: la stessa `mark_market_closed_carries` del motore (resa pubblica in `series_preparation.py`)
>   sull'ingresso dei segnali; la tabella dei festivi attesa una volta per chiamata, solo se ci sono segnali, e passata
>   anche ai segnali di rischio; il riscaldamento in giorni di calendario. `api/v1/fx.py` e
>   `technical_shared._fx_warmup_days`: lo stesso riscaldamento.
> - Test di altri riallineati senza indebolirli: le due fixture FX con un solo cambio salvato (ora più giorni pubblicati),
>   il caso del seme per intervallo con abbastanza sedute, le docstring dello scenario dell'AI Export (le copie
>   dell'ancora sono riporti, non sedute) con i controlli di presenza che hanno mostrato che la metà FX confrontava
>   due insiemi vuoti.
>
> **Il codice vero sui dati del developer** (copia di prod, cifre solo in `/tmp`): RSI 14 e SMA 200 coincidono al
> centesimo col prototipo su tutti gli 11 asset quotati, nessun punto di weekend, circa 250 punti l'anno, versioni
> 2.0.0; il BTP è «parziale» per SMA 200, a ragione (storia breve).
>
> **Le prove dell'AI Export** (skill `ai-export-probe-tuning`, prove mirate, alfy, 1Y, Standard; la sorgente è la
> snapshot in sola lettura, l'uscita in `/tmp`, la porta 6162; il «prima» da un'esportazione di `3c46c8e60` in
> `/tmp`): asset `asset.market_history` prompt +0,4 %, stessi dataset e componenti, stesse righe di storia, eventi
> esportati 116 → 106; portafoglio `portfolio.asset_history` +1,8 %, 5 indicatori da OK a parziale (le storie brevi,
> ora che il riscaldamento conta sedute), eventi rilevati −17 % (meno incroci prodotti dai weekend piatti). Sorgente
> invariata, controllo dei segreti superato, prompt uguali fra UI e prova. FX non provabile sui dati del developer
> (nessuna esposizione in valuta): coperto dai test.
>
> **⚠️ Fuori pista — le versioni dei componenti dell'AI Export**: nel piano le avevo portate da 1 a 2. La prova vera ha
> fallito i controlli del prompt pubblico: il renderer del frontend (`snapshotDataRenderer.ts:1438`) scrive in forma
> compatta solo i componenti alla versione 1, e per gli altri ricade sullo YAML grezzo, con gli identificativi. Né la
> logica dei componenti né la forma dei loro dati cambiano, cambiano solo i valori degli indicatori a monte, che hanno
> le loro versioni (2.0.0): versioni dei componenti riportate a 1, i pin tolti. Una regola scritta sul quando cambiare
> la versione di un componente non c'è; questo è il caso che la motiva.

#### Le due regressioni UI di (a), trovate dal docs-writer · ✅ 30/09/2026 (sera)

> Rilette le pagine, il docs-writer ha visto ciò che il backend non poteva mostrare: i campi del periodo dicono
> ancora «giorni», e il riempimento delle bande si spezza a ogni weekend (i punti ora sono solo sulle sedute, l'asse
> delle date resta di calendario). Il coordinator concede le due superfici: `lineChartHelpers.ts` (di I) e le chiavi
> i18n, più una riga nella lista Vitest `core-unit`.
>
> **Note implementazione — i periodi in sedute** (test rossi del test-author prima: 17 in
> `test_signal_plugin_matrix.py`, un pin per plugin di unità e suggerimento, più la presenza delle chiavi nei quattro
> cataloghi):
> - i 16 indicatori con un periodo dichiarano `"x-suffix": "sessions"`; i 12 sul suggerimento comune passano a
>   `chartSettings.tooltips.sessionPeriod`; EMA, MACD, PPO e StochRSI tengono le loro chiavi. `calendar_rolling_return`,
>   i 4 segnali di rischio a finestra e i 3 plugin di rischio con orizzonte restano in «giorni», che per loro sono veri;
> - i18n con `dev.py i18n`: `signals.units.sessions` e `chartSettings.tooltips.sessionPeriod` nuove, riscritte
>   `emaPeriod`, `fastPeriod`, `slowPeriod` e `signalPeriod`; `chartSettings.tooltips.period` resta com'è (il benchmark
>   Sine del frontend conta giorni veri). In francese lo spazio indivisibile prima dei due punti, che c'era, resta.
>
> **⚠️ Fuori pista — `connectNulls` non ripara la banda, la rompe.** Il rimedio concesso era mettere `connectNulls`
> anche sulle due serie impilate della banda (la base invisibile e il delta). Prima di chiudere l'ho disegnato davvero,
> con ECharts 6.0.0 in un browser, le stesse tre serie di `buildBandSeries`: dove la base di una serie impilata è
> nulla, ECharts prende come fondo l'origine dell'asse (`getStackedOnPoint`), e `connectNulls` salta solo i punti di
> sopra: il bordo inferiore precipita all'asse a ogni weekend. Nessuna opzione di ECharts lo evita. Tolto; il file è
> tornato com'era. La proposta al coordinator: riempire, solo nella base e nel delta, i giorni strettamente fra due
> punti con la retta fra i vicini (ciò che `connectNulls` disegna per una linea); prima del primo punto e dopo
> l'ultimo resta il vuoto; la linea di mezzo non cambia, e i tooltip saltano già le due serie di servizio, quindi un
> valore riempito non si vede mai. Cambia un test di I (una data mancante in mezzo non è più nulla nella base).
> Disegno di prova: tre pannelli, prima, `connectNulls`, riempimento (solo in `/tmp` e fra i file della sessione).
>
> **Note implementazione — le bande** (concessione rivista dal coordinator: l'aiuto in `lineChartHelpers.ts` e un solo
> test di I, riscritto al contratto nuovo; test rossi del test-author prima, 6):
> - `bridgeBetweenPoints`, locale: le posizioni dell'asse strettamente fra due punti prendono la retta fra i vicini;
>   prima del primo e dopo l'ultimo restano come sono. Solo sulla base invisibile e sul delta impilato; nessun
>   `connectNulls` su di loro; la linea di mezzo non cambia;
> - il test di I (`'maps a date absent from the signal to null across all three series'`) ora dice ciò che prova: la
>   data assente in mezzo è riempita nella banda, per posizione sull'asse, e resta vuota nella linea di mezzo;
> - il file nuovo è `lineChartHelpers.sessionGaps.test.ts` (un `lineChartHelpers.test.ts` c'era già, sotto
>   `__tests__/`), in `core-unit`: il weekend, un lunedì festivo, i vuoti ai due capi, il delta con la sua pendenza,
>   nessun nullo dentro il riempimento;
> - 7 mutanti (niente riempimento della base o del delta, riempimento in testa o in coda, riempimento della linea di
>   mezzo, `connectNulls` sulla base, pendenza sfasata): presi tutti;
> - il disegno col `buildBandSeries` vero, HEAD contro l'albero di lavoro (esbuild e un browser): HEAD si spezza a ogni
>   weekend e sul festivo, l'albero di lavoro è continuo, i capi vuoti.
>
> **Verifica finale del blocco** (6152, un comando alla volta): matrice dei plugin 92; registro 65, contratti 10,
> plugin 46 + 62 + 75 + 40, servizio 64, annotazioni 25, runtime 6; API cataloghi 4, anteprima 5, validazione 2;
> `core-unit` 2854; `component-unit` 2194; `front check` al pavimento di 3 (4 file non miei); i18n 3493 chiavi, nessuna
> mancante; orfani ✅; link ✅; ruff, black, `diff --check` puliti; nessun segreto. E2E `fx-detail` 17/17,
> `asset-detail` 27/28 (il `:486` noto, la fixture scaduta il 17/09, riparata nel ramo di I).
>
> **⚠️ Fuori pista — un rosso che c'era già**: `asset-unit` dà 12 rossi in `chartCoreHelpers.test.ts`, i test che
> rileggono il sorgente di `GrowthChart.svelte`. Gli stessi 12 su HEAD e su `dev_release2` (esportati in `/tmp`): il
> grafico è cambiato con `e7773a143` e i test no. Non è (a); il ramo di I li ritira (`2e4c8589f`).

### `dev_release2` → Risk dopo (a): il passo 13 di K e le scelte di L · ✅ 01/10/2026

> **Commit** (developer, script del coordinator): `cf09df7f6`, genitori `d800882b2` + `8f18416df`, albero
> `918eb1626cbb…`. Fusione aperta con `--no-commit` dallo script del coordinator, che si fermava se i conflitti non erano
> esattamente i due previsti.
>
> **I due conflitti, risolti in anticipo su una simulazione** (`git merge-tree`, nessuna scrittura nell'albero) e
> applicati da uno script che controllava che i file in conflitto fossero byte per byte quelli simulati:
> - `AllocationPieChart.svelte`: il mio importo preso dalla voce del grafico e il mio `iconHtml`, più gli escape di K
>   (`escapeHtml` sull'importo e sull'URL dell'icona, che ora si chiama `iconUrl` come vuole la regola del cancello).
>   Prendere il lato di K così com'era non compilava: usava un `iconUrl` che il mio lato non definiva più. Risultato
>   contro il mio: esattamente le 4 modifiche di K.
> - `assets/+page.svelte`: il blocco dei filtri, che F ha avvolto in `{#if activeTab !== 'correlation'}` reindentandolo
>   e K ha ricalibrato (`filterWidthClass`). Git chiudeva i segni a metà, e il testo dopo `>>>>>>>` era la copia di F con
>   le classi vecchie: scegliere un lato era sbagliato in tutti e due i casi. Ricostruito con una fusione a tre del solo
>   blocco, con la versione di F senza rientro e senza l'`{#if}`, poi rimesso l'avvolgimento. Prova a spazi ignorati:
>   il risultato contro F è esattamente le 13 righe di K, contro K esattamente le 135 di F.
>
> **Verifica del combinato** (6152, un comando alla volta): `front build --debug` ✅; `front check` al pavimento di 3;
> `core-unit` 2887 (con i cancelli anti-XSS di K); `component-unit` 2263; `allocation-unit` 142 (con
> `AllocationPieChart.test.ts`); orfani ✅; i18n 3494 chiavi, nessuna mancante; E2E `risk` 13, `risk-lab` 26,
> `risk-asset-detail` 2, `asset-list` 28, `toolbar-width-sweep` 15, `asset-name-xss` 2, `stale-price-banner` 1;
> backend `risk-all` 800, matrice dei plugin 92, `signal-service` 64, `ai-export` 925, `roi-fifo-utils` 518,
> `brim-provider-base` 34, `portfolio-engine` 42 (i due file del portafoglio si erano fusi da soli dai due lati). Rossi
> di altri invariati: `asset-unit` 12 in `chartCoreHelpers.test.ts`, gli stessi nomi di prima.
>
> **A e F**: niente avanzamento veloce, perché il loro lavoro in corso tocca file che la punta cambia. Al prossimo
> checkpoint ciascuno fonde la punta. Simulazioni sull'albero esatto, con la vera base di fusione (per F `3c46c8e60`, non
> la sua punta: è due commit di documentazione avanti): A 0 conflitti; F uno solo, in `TODO_FUTURI.md`, che il
> coordinator ha preso per sé (il file ha un solo scrittore): la voce di F è passata su `dev_release2`, e F la toglie dal
> suo checkpoint.

### Il benchmark condiviso: anche gli asset posseduti, e il selettore mai vuoto · ✅ 01/10/2026 (la mia parte)

> **Origine**: F aggiunge al laboratorio un selettore del benchmark, su richiesta del developer («non è accettabile che
> debba andare in dashboard, modificare il selettore e poi tornare qui»), e mi chiede se il laboratorio debba escludere
> anche gli asset posseduti, come fa la Dashboard.
>
> **Il difetto che c'era già**: la Dashboard e il Broker escludono dalla lista gli asset del proprio perimetro, ma il
> benchmark è uno solo. Il Broker esclude solo i suoi, quindi un benchmark scelto lì può essere posseduto in un altro
> broker; la Dashboard allora lo toglie dalla lista (`AssetSelect` filtra le opzioni, `SearchSelect` cerca il valore solo
> fra quelle) e mostra il segnaposto, mentre `run()` confronta proprio contro di lui.
>
> **Decisione del developer**, testuale: «credo che matematicamente può avere senso usare come benckmark un asset
> posseduto, quello che non capisco è quando dici che il selettore resta vuoto. Vorrei che ovunque serve scegliere un
> benchmark ci sia un selettore che permette di farlo e che al momento del caricamento della pagina, esso mostri il
> benchmark attuale, vuoto non deve mai essere, eccetto quando non c'è nessun asset impostato». E per la pagina
> dell'asset: «Sì, usa il benchmark condiviso: all'apertura mostra quello attuale, e cambiarlo lì lo cambia ovunque».
>
> **La regola**: si esclude solo ciò che si misura (l'asset sulla sua pagina, gli asset selezionati nel laboratorio); il
> selettore mostra sempre la scelta corrente, anche quando lì non si può usare, e lo dice; un id salvato che non
> corrisponde più a nessun asset vale come «non impostato». Il motivo finanziario: un portafoglio contiene quasi sempre
> qualcosa del suo riferimento, e «i satelliti mi fanno guadagnare o perdere rispetto al solo nucleo?» è la domanda più
> utile per chi investe così. Il backend lo gestisce già (il benchmark posseduto ed escluso dà un confronto non
> disponibile, con la qualità dei dati che dice perché).
>
> | chi | cosa | stato |
> |---|---|---|
> | A | `RiskLevelsPanel`: niente esclusione degli asset posseduti; l'id morto | ⏳ test rossi prima |
> | F | il selettore nel laboratorio, sopra L1° e L3° (decide il developer); la scelta corrente sempre visibile | ⏳ giro 4 |
> | io | la primitiva, e la scheda Rischio della pagina dell'asset che legge e scrive il benchmark condiviso | ✅ 01/10 |
>
> **Una primitiva, non tre filtri.** La regola vive in `components/risk/BenchmarkSelect.svelte` con
> `resolveRiskBenchmark()` nello store (miei); A la monta in `L3Benchmark` con `measuredAssetIds={[]}`, F nel
> laboratorio sopra L1° e L3° (variante B scelta dal developer), io sulla pagina dell'asset. Il ⚠ è il disegno di F
> approvato dal developer; il testo generico è mio (`risk.benchmark.measuredHere`), il laboratorio passa il suo con
> `measuredHint`. Due concessioni del coordinator per il runner (il test jsdom in `risk-levels-component`, l'E2E nuovo
> `risk-benchmark-shared`).
>
> **⚠️ Fuori pista — l'id morto non si cancella.** Il primo contratto cancellava dallo store un id senza asset. Il
> test-author di A ha trovato due ragioni per non farlo: `entityStore.ensureLoaded()` si risolve anche quando il
> caricamento fallisce («Fail silently»), quindi un asset sparito e una lista non caricata non si distinguono e si
> perderebbe una scelta valida; e `assets.id` è `INTEGER PRIMARY KEY` senza AUTOINCREMENT, quindi SQLite riusa l'id
> dell'ultimo asset cancellato e un id salvato può tornare vivo su un altro asset. La primitiva espone ora lo stato
> della risoluzione (`none`, `pending`, `set`, `unknown`, anche come `data-benchmark-state`): `unknown` vuol dire
> segnaposto e nessuna richiesta, senza toccare la memoria. Il riuso degli id riguarda ogni riferimento ad asset
> salvato nel client: passato al coordinator come limite del backend.
>
> **Note implementazione** (test rossi prima, test-author, tre giri: 4 + 23, poi gli attributi e il ⚠ di F, poi lo
> stato della risoluzione; la sessione è caduta alle 14:28 durante la mia verifica dei rossi, ripresa alle 15:42 dai
> file):
> - `riskBenchmarkStore.svelte.ts`: `resolveRiskBenchmark()` → `{state: 'none' | 'set' | 'unknown', assetId}`; niente
>   salvato → `none` senza caricare la lista; altrimenti attende `ensureAssetsLoaded()` e conferma con `getAssetInfo`;
>   un caricamento fallito dà `unknown` senza rigettare; **non scrive mai** lo store.
> - `BenchmarkSelect.svelte`: lo stato è sincrono al montaggio (`pending` se c'è un id salvato, altrimenti `none`), poi
>   la risoluzione (valore prima dello stato); una scelta del lettore scrive lo store, poi stato e valore, poi
>   `onchange`, e la risoluzione tardiva non la sovrascrive; il filtro toglie solo ciò che la pagina misura, mai la
>   scelta corrente; benchmark per primi; la radice `${testid}-control` pubblica `data-benchmark-id`,
>   `data-benchmark-state`, `data-measured`; il ⚠ è il disegno di F (`role="img"`, `tabindex="0"`, `aria-label`, dentro
>   il `Tooltip` con `interactiveChild`, perché il suo involucro normale è un `role="button"`), testo generico
>   `risk.benchmark.measuredHere` o `measuredHint` della pagina. Il prop si chiama `state`, la variabile locale
>   `benchmarkState`: un nome `state` oscura la runa `$state`.
> - `RiskAnalysisPanel.svelte` (pagina dell'asset): `BenchmarkSelect` al posto di `SignalAssetParamControl` per il
>   confronto, stesso testid; `comparisonUsable` esclude l'asset stesso, e il pulsante resta il solo avvio.
> - Runner (due concessioni del coordinator): il test jsdom in `risk-levels-component`, l'E2E nuovo
>   `risk-benchmark-shared`; la `desc` corretta al contratto finale (il primo giro diceva ancora «is cleared»).
>
> **Verifica** (6152, un comando alla volta): store 13 · `BenchmarkSelect` 38 (`risk-levels-component` 74) ·
> `core-unit` 2887 · `component-unit` 2263 · `front check` al pavimento di 3/41 (nessun avviso nuovo) · i18n 3495 chiavi,
> nessuna mancante · orfani ✅ · E2E `risk-benchmark-shared` 4/4 (i quattro rossi), la rete senza proprietario
> `risk-asset-detail` 2/2 (con la memoria vuota la pagina è identica), `risk` 13, `risk-lab` 26. **Mutanti**: 18 su 18
> presi (5 sullo store: cancella l'id sconosciuto, non attende la lista, rigetta sul fallimento, carica senza id, legge
> il fallimento come `set`; 13 sulla primitiva: mai `pending`, niente guardia della corsa, scelta corrente filtrata,
> `onchange` o valore prima dello store, ⚠ mai mostrato, suggerimento della pagina ignorato, niente sezioni, ⚠ non
> focalizzabile, stato non pubblicato o non scritto, valore dallo store invece che dalla risoluzione, scelta che non
> arriva allo store); file ripristinati identici (SHA-256).

### I piccoli debiti di documentazione, e un difetto di (a) che la guida ha fatto emergere · ✅ 01/10/2026 (sera)

> **Commit della famiglia nel pomeriggio**: A `2b9362618` (avviso con la causa prima, residuo onesto di L3); il mio
> checkpoint del benchmark `07f6bb01d` · `8a2cc16dd`; Risk ← F `a7f1dbea4` (validato: `core-unit` 2896,
> `component-unit` 2356, E2E `risk-lab` 31, `risk` 13, `risk-benchmark-shared` 4, `risk-asset-detail` 2, `asset-list`
> 28); la punta in A `738ddc064`, con il solo conflitto atteso sulle due righe del runner, risolto in modo additivo e
> controllato byte per byte contro la mia risoluzione calcolata a parole.
>
> **Scelta del developer**: dopo F → Risk, prima i piccoli debiti di documentazione, poi il blocco replay o l'idoneità
> del benchmark.
>
> **Note implementazione**
> - **La guida dei plugin dei segnali** (docs-writer, solo EN: le pagine per sviluppatori non hanno traduzioni):
>   `computes_on_quote_days` nel contratto, il filtro delle sedute nell'esecuzione (la copertura resta di calendario),
>   il riscaldamento separato per sedute e giorni (`SESSION_WARMUP_DAY_MULTIPLIER = 2`), `sessions` contro `days` nei
>   metadati dei parametri, la regola della versione. Ha corretto anche sette punti già sbagliati prima (la categoria
>   `risk`, l'esempio completo che la registrazione avrebbe rifiutato, i campi semantici obbligatori, il tipo `area`,
>   un nome di costante dei test superato). Build severa e link verdi.
> - **⚠️ Fuori pista — un difetto di (a), trovato dal docs-writer leggendo il codice**: l'avviso di copertura parziale
>   (`build_signal_availability_warnings`) contava come «esclusi» tutti i punti di calendario fuori da quelli scelti, e
>   dal 30/09 quelli scelti sono le sole sedute: i giorni riportati dentro il segmento finivano fra gli esclusi, e il
>   numero sul grafico (`signalProblem.ts:226` → `chartSignalsHelpers.ts:86`) era gonfiato. Rosso prima (test-author):
>   15 esclusi contro 11, e i bordi del segmento dati come prima e ultima seduta invece che come estremi di calendario;
>   un plugin gemello con `computes_on_quote_days = False` fa da metro. Cura: l'avviso riceve la selezione della
>   copertura, prima del filtro delle sedute. Mutanti: tornare alle sedute, togliere il filtro: presi entrambi.
>   Consumatori di `excluded_points`: solo l'avviso del grafico; l'AI Export legge degli avvisi solo codice e
>   messaggio, e solo nel contesto del drawdown, che non usa le sedute: niente prova dell'AI Export.
> - **Il pin «nessun id mentre è `pending`»** in `BenchmarkSelect.test.ts` (reperto di A): i due mutanti di A sulle sue
>   guardie `state === 'set'` sopravvivevano solo perché la primitiva non pubblica un id non confermato, cosa che il
>   contratto non fissava. Ora la fissa (39 test); il mutante che pubblica l'id salvato al montaggio muore anche nel
>   caso di un id che la lista poi conferma, che prima nessun test copriva.
>
> **Verifica** (6152): `signal-service` 65 · matrice 92 · `asset-signals` 30 · plugin OHLC 75 e core 46 ·
> `risk-levels-component` 75 · orfani ✅ · ruff e black puliti · `diff --check` pulito.
>
> **Restano**: la nota sul cancello della documentazione (`scripts/docs_links.py` riconosce `docsPath:` anche nei
> commenti: falsi link rotti), passata al coordinator, a cui appartiene lo strumento; il limite delle sfumature della
> torta (famiglie di 5–7 membri), da decidere col developer, cancello per `dev_release2`; poi il blocco replay (F3) o
> l'idoneità del benchmark (F4).
