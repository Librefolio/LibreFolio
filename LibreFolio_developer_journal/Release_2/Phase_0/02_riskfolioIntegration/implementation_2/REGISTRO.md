# Registro di coordinamento — Round 2

> **Scrittore unico: il coordinatore.** Nessun mandato scrive in questo file.
> Aggiornato a ogni cambio di stato, non a fine fase.

---

## 1. Stato dei mandati

**Baseline comune**: `2ec19b8f0` · **piano e briefing**: `466fdb724`

| | mandato | sessione | corsia | stato | dal |
|---|---|---|---|---|---|
| **F1** | Dati di prova | N `miniature-train` | `6151` · `/tmp/librefolio-r2-f1` | 🔵 **analisi** — piano approvato da terzi, zero file scritti | 18 Set 13:30 |
| **F2** | Primitive e contratto | D `solid-engine` | `6152` · `/tmp/librefolio-r2-f2` | 🟢 **CONSEGNATO · `FROZEN`** — `PRIMITIVE.md` 243 righe · `RiskCardGrid` +7 test · `ScatterChart` + helper +23 test | 18 Set 15:00 |
| **S1** | L1 — Quanto può fare male | E `vigilant-adventure` | `6153` · `/tmp/librefolio-r2-s1` | ⏸️ attende fase 1 | — |
| **S2** | L2 — Sono diversificato | *(nuova)* | `6154` · `/tmp/librefolio-r2-s2` | ⏸️ non creata | — |
| **S3** | L3 — Sono pagato per il rischio | *(nuova)* | `6155` · `/tmp/librefolio-r2-s3` | ⏸️ non creata | — |
| **S4** | L4 — Cosa succede se | H `friendly-bassoon` | `6156` · `/tmp/librefolio-r2-s4` | ⏸️ attende fase 1 | — |
| **S5** | Asset Global | F `super-dollop` | `6157` · `/tmp/librefolio-r2-s5` | ⏸️ attende fase 1 | — |
| **T1** | Avvisi come segnali | *(nuova)* | `6158` | ⏸️ attende fase 2 | — |
| **T2** | Link doc + cancello | I `shiny-broccoli` | `6159` | ⏸️ attende fase 2 · **vedi R2-08 e R2-09** | — |
| **T3** | Ricombinazione spec | `test-author` | `6160` | ⏸️ attende fase 2 | — |
| — | consulente matematica | A `improved-meme` | *nessuna* | 💬 a chiamata | — |
| — | da archiviare | B, C, G | — | 📦 in attesa | — |

**Coordinatore**: porta **6150**, cartella dati **predefinita**.
⚠️ **Nessun mandato deve usare la cartella dati predefinita**: la riscriverebbe.

### ⚠️ Il server di review si avvia **a richiesta**, e va riseminato ogni volta

Scritto qui dopo essermi corretto: avevo dichiarato il server «attivo» e **una riga dopo la
misura diceva `HTTP 000`**. Il processo era terminato senza errori nel log.

**Ma tenerlo acceso non sarebbe stato giusto comunque**, e la ragione è più interessante
dell'errore:

> **F1 riscrive `populate_mock_data.py`.** Nel momento in cui F1 consegna, il mio DB di
> review — seminato col popolatore vecchio — **è obsoleto**. Un server acceso da prima
> mostrerebbe lo stato che F1 ha appena superato, **e sembrerebbe che non abbia funzionato.**

✅ **Procedura di verifica, da rieseguire a ogni chiusura di mandato:**

```bash
# 1. riseminare con il popolatore CORRENTE, non con quello di ieri
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6150 db populate --force --clean

# 2. ricostruire il frontend (il server lo fa da solo, ma dopo api sync serve esplicito)
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build

# 3. avviare
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server \
  --test --port 6150 --no-scheduler --no-reload
```

📌 **E un promemoria dal round 1**: le corse di test consumano il DB di review. Dopo
`dev.py test api all` gli utenti `e2e_test_*` **non esistono più** — c'era persino un
`wipe_user_…` fra i residui. **Riseminare non è pignoleria: è l'unico modo per guardare
ciò che si crede di guardare.**

---

## 2. Scrittori unici delle superfici condivise

**Nominati prima di avviare.** Nel round 1 questa tabella non esisteva, e il catalogo del
runner ha conflittato **tre volte su quattro merge** — una risoluzione stava per cancellare
in silenzio il lavoro di D.

| superficie | scrittore unico | gli altri |
|---|---|---|
| `risk/levels/RiskLevelsPanel.svelte` | **E** (S1) | chiedono a E |
| `risk/levels/levelHelpers.ts` | **E** (S1) | chiedono a E |
| `frontend/src/lib/i18n/*.json` | ciascuno **solo** nel proprio namespace `risk.levels.lN.*` | il coordinatore verifica l'unione |
| `scripts/test_runner/_frontend_portfolio.py` | **T3** `test-author` | nessun altro |
| `frontend/e2e/portfolio/*.spec.ts` | **T3** `test-author` | nessun altro |
| `backend/app/schemas/risk.py` | **F1** in fase 1, poi **il coordinatore** | additivo, mai sostitutivo |
| `implementation_2/PRIMITIVE.md` | **F2** (D) | lo leggono tutti, non lo scrive nessun altro |

---

## 3. Registro dei campi del contratto → chi li rende

**Un campo senza consumatore è un rosso di fine fase**, non una scoperta di sei mesi dopo.
Stato al 18 Set 2026, misurato su `components/risk/levels/`.

| campo | oggi | destinatario | rappresentazione |
|---|---:|---|---|
| `underwater_series` | 🔴 0 | **S1** | 7.1 underwater chart |
| `return_bins` | 🔴 0 | **S1** | 7.2 istogramma VaR |
| `var_bin_edge` | 🔴 0 | **S1** | 7.2 — barra del taglio |
| `worst_realization` | 🔴 0 | **S1** | riga sotto «giornata storta» (W0) |
| `drawdown_at_risk` | 🔴 0 | **S1** | riga sotto «peggior discesa» (W0) |
| `conditional_drawdown_at_risk` | 🔴 0 | **S1** | riga sotto DaR (W0) |
| `ulcer_index` | 🔴 0 | **S1** | didascalia dell'underwater chart (W0) |
| `primary_drawdown` | 🔴 0 | **da decidere** | il design lo segnalava già scartato |
| `tracking_error` | ⚪ 0 | **nessuno** | ✅ tagliato di proposito |
| `information_ratio` | ⚪ 0 | **nessuno** | ✅ tagliato di proposito |
| `effective_number_of_assets` | ✅ 6 | S2 | — |
| `diversification_ratio` | ✅ 6 | S2 | — |
| `cash_weight` | ✅ 4 | S2 | — |
| `percentile_bands` | ✅ | S4 | 7.7 cono — già reso |

⚠️ **`var_bin_edge` va letto con `=== null`, mai con `?? 0`**: uno zero è un taglio legittimo,
e il ripiego lo renderebbe indistinguibile dall'assenza.

---

## 4. Registro delle primitive — «questo esiste già»

Un mandato che vuole creare un componente **lo chiede al coordinatore**, che risponde con il
nome di quello esistente o autorizza.

| serve | esiste | non costruire |
|---|---|---|
| card per una metrica | `ui/display/RiskMetricCard` | una card nuova |
| barra etichettata | `ui/display/KpiMetricBar` | — |
| barra divergente | `ui/display/KpiDivergingFlowBar` | — |
| grafico su **serie storiche** (linea, area, barre, banda) | `charts/LineChart` — asse **categoriale sulle date** | un wrapper ECharts nuovo |
| scatter a **X numerica** (vol/rendimento) | ⏳ **F2 lo COSTRUISCE** — `LineChart` non può farlo | un grafico nuovo dopo F2 |
| heatmap | `risk/CorrelationHeatmap` | — |
| popover riposizionabile | `ui/feedback/Tooltip` | un popover nuovo |
| selettore di data | `ui/date/SingleDatePicker` | un input nativo |
| percentuale formattata | `utils/core/formatPercent` | 🔴 **nessun `toFixed` nuovo** |
| link alla documentazione | `components/ui/DocsLink` | ⚠️ **il percorso deve esistere** |

---

## 5. Definizione di finito

```
Round 1:  finito = il mio codice è scritto e i test passano
Round 2:  finito = IL COORDINATORE LO VEDE sull'app in esecuzione,
                   in italiano, con il link che porta a una pagina che esiste
```

**Nessun mandato chiude senza che io abbia guardato la sua superficie nel browser.**
È la verifica che ha trovato tutti e tre i delta della review, e nel round 1 l'ho fatta
**dopo** l'integrazione invece che **prima di ogni chiusura**.

---

## 6. Diario delle decisioni del round 2

| | data | decisione |
|---|---|---|
| **R2-01** | 18 Set | **W0**: le quattro misure senza verdetto vanno **tutte in L1**, ciascuna come **seconda riga** di una esistente. L'Ulcer index come **didascalia dell'underwater chart**, perché da solo è un numero senza unità |
| **R2-02** | 18 Set | **E prende L1, non L3.** Lo scatter di L3 richiede backend nuovo e va a un mandato full-stack: spezzarlo fra due persone è l'errore del round 1 |
| **R2-03** | 18 Set | **Separatore decimale → `TODO_FUTURI`.** L'helper esiste ma legge il locale del **browser**: adottarlo propagherebbe un secondo difetto. **Divergenza riprodotta dal vivo**: app in inglese, browser `it-IT` → `−175,91 €` sotto interfaccia inglese |
| **R2-04** | 18 Set | 🔴 **Correzione a un mio piano**: `RiskMetricCard` era **già adottabile** — props complete. F2 non la ripara: la rende **trovabile**. Detto a D nel briefing |
| **R2-05** | 18 Set | I worktree **non si fanno avanzare mentre l'agente lavora**: F1 e F2 hanno il briefing inline, il file arriva al prossimo aggiornamento di baseline |
| **R2-12** | 🔴 18 Set | **Violazione mia: ho approvato il piano di F2 dopo aver detto allo sviluppatore che non l'avrei fatto.** Un messaggio prima: *«la prima autorizzazione a scrivere codice è tua, non mia»*. Poi ho chiuso il messaggio a D con *«✅ Piano approvato»*. ✅ **Riconosciuta e riportata subito, non scoperta dopo.** Lo sviluppatore ha **tenuto il lavoro** (era nel perimetro e verificato) **e delegato l'approvazione dei piani al coordinatore** da qui in avanti. 📌 **La regola sopravvissuta non è "il coordinatore non approva" ma "il coordinatore dichiara subito quando ha ecceduto"** — la prima era una promessa, la seconda è una procedura |
| **R2-13** | 🔴🔴 18 Set | **`generated.ts` è ignorato da git, quindi NON viaggia col merge: sei worktree su otto avevano un client stantio o assente** | Trovato perché **D ha diagnosticato un difetto inesistente** misurando nel proprio albero. \| albero \| stato \| \|---\|---\| \| `ideal-eureka`, `miniature-train` \| ✅ 19107 righe \| \| `solid-engine`, `vigilant-adventure`, `super-dollop`, `improved-meme` \| 🔴 18887 — **stantio** \| \| `friendly-bassoon`, `shiny-broccoli` \| 🔴 **assente** \| 🔑 **È un difetto del mio impianto**: ho allineato gli alberi con un fast-forward, ma `api sync` non viaggia col merge perché **il suo prodotto è nel `.gitignore`**. ⚠️ **In fase 2 partono cinque superfici insieme: ognuna avrebbe incontrato rossi fantasma e li avrebbe diagnosticati come propri**, esattamente come è successo a D. ✅ **Riparato: `api sync` eseguito in tutti e otto → 19107 righe ovunque.** 📌 **Vincolo permanente: `api sync` va rieseguito in OGNI worktree dopo OGNI aggiornamento di baseline.** Un fast-forward pulito non basta |
| **R2-14** | 18 Set | ⚠️ **L'escalation di D era giusta la prima volta ed eccessiva la seconda, e la differenza è dove ha misurato** | **Primo messaggio**: *«2 test rossi, lo spec non conosce `is_benchmark`»* → ✅ **vero, verificato dal coordinatore nel proprio albero fresco**: `+ "is_benchmark": false`, 15 chiavi contro 14 attese. **Secondo messaggio**: riqualificato come *«perdita di dati in una feature rilasciata»* — Zod scarta il campo, `=== true` lo rende un `false` deciso, il PATCH lo riscrive. 🔴 **La catena è corretta anello per anello, ma il primo anello richiede un client stantio.** Nel client fresco `is_benchmark` è `.optional().default(false)`: **Zod lo riempie, non lo lascia `undefined`**. E non può arrivare in produzione: `dev.py:563` rigenera **sempre** prima del build **e annulla il build se fallisce**; il Dockerfile copia il frontend già costruito. ✅ **Riparazione applicata: due righe `is_benchmark: false` subito dopo `active: true`**, che è esattamente dove il prodotto le manda (`AssetModal:1341`, `:1479`, incondizionate come `active`). **23 passed**, `front check` **0 errori**. 📌 **D temeva che questa riparazione "cementasse" il difetto: non lo fa**, perché col client fresco il valore inviato è quello vero, non uno fabbricato |
| **R2-07** | 18 Set | 🔴🔴 **`LineChart` NON può fare lo scatter di §7.5, e io avevo scritto il contrario in due modi opposti.** Trovato da **D**, riverificato dal coordinatore: `xAxis:{type:'category',data:dates}` **senza prop** per cambiarlo (`grep xAxisType` → 0); `seriesType` **non è una prop** di `LineChart` ma vive su `RenderedSignal:226`, il sistema di overlay su serie storiche; lo scatter interno a `:399` fa `dates.indexOf(d.date)` — **è inchiodato all'asse delle date**. §7.5 vuole X=volatilità e Y=rendimento, **entrambi numerici continui**. ✅ **Autorizzato a D: `ScatterChart.svelte` + `scatterChartHelpers.ts`**, perimetro allargato. Il contratto delle props viene da **`05` §7.5**, non da un'ipotesi. 🔑 **I miei due errori erano opposti**: `00-proposta:72` prometteva uno scatter **inesistente**, il briefing F2 e il REGISTRO dimenticavano `'area'` che **esiste**. Due documenti scritti a un'ora di distanza, **e nessun cancello poteva vederli: un inventario in prosa non è eseguibile** |
| **R2-08** | 18 Set | 🔴 **Il cancello `check-links` è cieco su 3 dei 6 link rotti, e lo dichiara da sé.** `dev.py:1238`: *«A dynamic `path={expr}` has no quotes and is skipped by construction.»* `L3RiskAdjusted:51,59,74` usa `path="…"` → visti. `L1HowMuchItHurts:78` usa `path={DOC_PATHS[row.id]}` → **invisibili**, benché i valori della mappa siano **stringhe statiche, quindi controllabili**. ⚠️ **Vincolo per T2**: non partire credendo che passare il cancello significhi qualcosa |
| **R2-09** | 18 Set | ⚠️ **I sei link sono sbagliati DUE volte**: percorso inesistente **e** forma. `use_directory_urls` non è dichiarato in `mkdocs.yml` → default `true` → **URL a directory**. La forma funzionante nel resto dell'app è `user/dashboard/kpi-cards/#card-1-period-pl`, non `user/analysis/risk.md#sortino`. 🔴 **E le pagine vere sono UNA PER METRICA**, non ancore di un `risk.md`: chi ripara puntando a `user/analysis/risk/` **sbaglia una seconda volta**. Vincolo per T2 |
| **R2-10** | 18 Set | ✅ **`RiskCardGrid` come componente, non come convenzione documentata.** L'argomento è di D e non è estetico: **20 dichiarazioni di griglia, 12 varianti distinte** in `components/risk/`, e il salto `1 → sm:2 → xl:5` che l'intestazione della card denuncia **è ancora a `RiskAnalysisPanel:632`**. *«Una stringa documentata è copia-incolla — il meccanismo esatto con cui sono nate quelle venti.»* **Venti dichiarazioni sono la prova che la convenzione documentata ha già fallito.** E `auto-fit` toglie la causa: la card si dimensiona da sé con `@container` |
| **R2-11** | 18 Set | ✅ **K5 marcato storico.** Descrive **uno spostamento avvenuto**, non **come si monta**. La fonte per l'uso è `PRIMITIVE.md`. Ragione data da D: *«due documenti che descrivono le stesse primitive divergono, ed è il difetto che PRIMITIVE.md esiste per chiudere»* |
| **R2-06** | 18 Set | 🔴 **Il server di review si avvia a richiesta, mai tenuto acceso.** Avevo scritto «attivo» e la misura una riga dopo diceva `HTTP 000`. Ma la ragione vera non è l'errore: **F1 riscrive il popolatore**, quindi un server acceso da prima mostrerebbe lo stato che F1 ha appena superato — **e sembrerebbe che non abbia funzionato** |
