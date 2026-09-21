# A — Asset Global · piano vivo di esecuzione (round 3)

> **Mandato**: A — Asset Global, round 3 della campagna Risk Analysis.
> **Sessione**: `e-alfy-shiny-sniffle` · **ramo** `e-alfy-risk-asset-global-levels`
> **Baseline**: `f829cd76b` ✅ verificata con `git rev-parse HEAD`
> **Corsia**: `--test-port 6170` · `--data-dir /tmp/librefolio-r3-a`
> **Coordinatore**: sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca`
> **Analisi approvata**: 21 Set 2026 · **autorizzazione sviluppatore**: *«Sì, autorizza la fase 1»*

---

## Perimetro ratificato

**Fase 1** (questa): riparazione dello scatter · smontaggio del monolite · ri-puntamento del
cancello euro · contratto per il mandato backend.
**Fase 2** (dopo il merge della piattaforma backend): `L1°`, `L3°`, i18n, docs, end-to-end.

**Possiedo**: `AssetSetRiskPanel.svelte` · `AssetSetCorrelationSection.svelte` ·
`AssetSetReplaySection.svelte` · `assetSetSelection.ts` · `frontend/e2e/portfolio/risk-lab.spec.ts`
(① — T3 «svuotata dai fatti») · `RiskLevelsPanel.svelte` **in regime di sole aggiunte** (scrittore
unico round 3) · `frontend/e2e/portfolio/risk-analysis.spec.ts` per la rete dello scatter.

**Non tocco**: `RiskAnalysisPanel.svelte` (serve Asset Detail) · `L1*`/`L2*`/`L3*`/`L4*` ·
`levelHelpers.ts` · `ScatterChart.svelte` (**autorizzazione restituita**, vedi §1.3) ·
`backend/**` · `scripts/test_runner/*` · chiavi i18n esistenti.

---

## Le quattro correzioni che l'analisi ha prodotto prima di scrivere codice

| | reperto |
|---|---|
| **A1** | 🔴 *«L1°/L3° escono dal monolite»* **era falso**: su `asset_set` solo 2 plugin su 9 rispondono (`correlation`, `stress`). Il monolite non li ha **mai** mostrati. Smontarlo è sottrazione di **due violazioni**, non di funzionalità |
| **A2** | 🔴 La CML è cancellata sull'esistenza di un punto `role==='portfolio'`, **non** su `riskFreeRate` → su `asset_set` non può nascere. **Autorizzazione su `ScatterChart` restituita inutilizzata** |
| **A3** | 🔑 Il fan-out per-asset era **sbagliato, non solo caro**: N preparazioni separate sullo stesso grafico = il difetto **Ⓔ** moltiplicato per N |
| **A4** | ⚠️ Lo scatter non ha **alcuna** rete E2E → *«nessuno chiedeva, quindi nessuno ha risposto male: non ha risposto nessuno»* |

---

## Passi

### Passo 0 — bootstrap del worktree · ✅ **21 Set 2026**

Catena obbligata in un worktree fresco: `npm ci` → **`api sync`** → `front check`.
Saltare quello in mezzo dà 46 errori in 12 file che non sono di nessuno.

**Cancello**: *non* «`front check` verde», ma **«gli stessi 3 errori ereditati, e nessuno in un
file `risk`»** — `ToolExecutionMetrics.svelte:44`, `TransactionFormModal.test.ts:787,819`,
verificati byte-identici a `dev_release2` dal coordinatore.

> **Note implementazione**: `npm ci` → 433 pacchetti, 13 s, exit 0. `api sync` → `openapi.json`,
> `generated.ts`, `tool-contracts.openapi.json` rigenerati, exit 0. `front check` →
> **`svelte-check found 3 errors and 41 warnings in 4 files`**, e i tre sono esattamente
> `ToolExecutionMetrics.svelte:44:55`, `TransactionFormModal.test.ts:787:48`, `:819:48`.
> Conteggio dei file `risk` fra gli errori: **0**. ✅ **Cancello superato, identico al previsto.**
> Log: `/tmp/librefolio-r3-a-frontcheck-baseline.log`.

> **Note implementazione (dopo la rete del passo 1)**: `front check` **rieseguito** a rete
> scritta → **`3 errors and 41 warnings in 4 files`**, invariato. Atteso, perché il tsconfig
> esclude `e2e/**` (Fuori pista 1) — ma **misurato, non dedotto**.
> Log: `/tmp/librefolio-r3-a-frontcheck-after-net.log`.
> Controllo vero degli spec eseguito a parte: `npx tsc -p tsconfig.e2e.json --noEmit` →
> **0 errori in `risk-analysis.spec.ts`, 0 in tutto `e2e/portfolio/`**, 76 preesistenti altrove.
> Log: `/tmp/librefolio-r3-a-tsc-e2e.log`.

> **⚠️ Fuori pista (ereditato, non mio)**: `node_modules/`, `.env` e
> `LibreFolio_devWiki/graphify-out/graph.json` assenti. I primi due sono bootstrap atteso; il terzo
> è ignorato dal repo, quindi **`wiki-search` via grafo non è stato possibile**. Ho usato
> `GRAPH_REPORT.md` + le pagine devWiki committate + l'intero `implementation_2/`.
> **Etichetta: conoscenza ricostruita da fonti committate, non interrogata dal grafo.**

> **⚠️ Fuori pista (del coordinatore, registrato da lui)**: l'autorizzazione dello sviluppatore è
> arrivata nel feedback di approvazione del piano mentre un messaggio parallelo diceva *«aspetto
> l'autorizzazione»*. Due canali, due tempi. Ho obbedito a quello che vietava ed è costato un giro.

---

### Passo 1 — la rete E2E dello scatter, **provata rossa** · ✅ **21 Set 2026**

`risk-analysis.spec.ts` non nomina mai `risk-l3-scatter` né `risk-l3-risk-return`: **zero
occorrenze**. È il motivo per cui due guasti in serie sono passati.

**Regola imposta dal coordinatore**: *«provami che è rossa sul codice attuale. Una rete scritta
dopo passerebbe comunque, e non proverebbe niente.»*

> **Note implementazione**: rete scritta da `test-author` (specialista), **solo additiva**,
> **+168 righe** in `e2e/portfolio/risk-analysis.spec.ts`, nessun altro file toccato.
> Test: *«L3 asks for the risk/return pair in the current composition wave and draws the
> scatter»*. Asserisce **le due rotture separatamente**, perché sono in serie e una sola
> asserzione lascerebbe l'altra libera di tornare: ① il filo — `portfolioAnalytics(requests,
> 'current_composition')` deve contenere `asset_risk_return` (oggi rosso per la rottura B);
> ② il disegno — `risk-l3-risk-return` visibile + `expectChartCanvas(page, 'risk-l3-scatter')`
> (oggi rosso per la rottura A). Più `risk-l3-scatter-note`, reso raggiungibile da un
> `cash_weight` positivo. Solo `data-testid`, nessun testo tradotto, nessuna posizione fissa,
> nessuna attesa a orologio, non crea nulla.
> I letterali della fixture sono commentati **«inventati, non misurati»** — Ⓗ: l'etichetta è parte
> del dato, e una verifica interroga il numero, non la sua provenienza.

> **⚠️ Fuori pista 1 — il mio cancello aveva un punto cieco, trovato dallo specialista.**
> `./dev.py front check` esegue `svelte-check --tsconfig ./tsconfig.json`, e **quel tsconfig ha
> `"exclude": ["e2e/**/*", "playwright.config.ts"]`** — verificato leggendo il file.
> **`front check` non ha mai controllato uno spec, e non lo controllerà.** La mia riga
> *«`front check` non deve aggiungere un quarto errore»* era **la risposta giusta a una domanda
> che quello strumento non sta ascoltando.** Il controllo vero è `tsc -p tsconfig.e2e.json
> --noEmit`: **0 errori in `risk-analysis.spec.ts`**, 76 preesistenti altrove
> (`onboarding-tour`, `tools/*`), **nessuno in `portfolio/`**.
> *Forma d'errore: uno strumento risponde sempre alla domanda che gli si fa.*

> **⚠️ Fuori pista 2 — terza rottura, e non è di prodotto.** Il `CATALOG` del mock in
> `risk-analysis.spec.ts` **non dichiarava affatto `asset_risk_return`**. `buildBaseAnalytics`
> scarta in silenzio ogni analitica che il catalogo non annuncia (`add()` è guardato da
> `ctx.hasCapability`), quindi **anche riparando A e B il mock l'avrebbe omessa.** Non è un difetto
> del prodotto — è la conferma del reperto: *nessuno chiedeva.* Riparata dentro la rete.

> **🔴 Fuori pista 3 — la riparazione ha un TERZO effetto che né io né il coordinatore avevamo
> previsto, e non è cosmetico.** `includeCurrentCompositionRiskReturn` accende **due** codici, non
> uno: `asset_risk_return` **e** `historical_kpi` sull'onda `current_composition`. E
> `selectKpiWave` (`l3Helpers.ts`) **preferisce** l'onda corrente quando contiene un
> `historical_kpi` valido. Quindi in **produzione** la riparazione **cambia il perimetro di L3 su
> Dashboard e Broker Detail**, e con esso **i valori mostrati di Sortino, Sharpe, volatilità e
> beta** — la docstring di `L3RiskAdjusted` dice che i due perimetri possono divergere *«by more
> than half their own value»*. È il comportamento **progettato** (la card legge il perimetro dal
> payload e lo dichiara), ma **è un cambiamento numerico visibile su due superfici che non sono
> mie**. ⏸️ **Sospeso in attesa di decisione del coordinatore.**
> *(Nel solo spec il perimetro resta `historical`, perché il mock non annuncia `historical_kpi`
> per `current_composition`. Nessuno spec `portfolio/` asserisce `data-perimeter`: verificato,
> zero occorrenze.)*

> **🔴 Fuori pista 4 — BLOCCO AMBIENTALE: nessun E2E è eseguibile in questa corsia.** Vedi §Blocco.

> **✅ Fuori pista 5 — cache mathjax ripristinata, e ho deviato dal comando del coordinatore.**
> **Provenienza esplicita, come impone la regola di S4**: il coordinatore aveva autorizzato
> `cp -R` dalla **sua** corsia (`e-alfy-ideal-eureka`). **Non l'ho fatto.** Ho scaricato il file
> dalla **fonte canonica** — `curl https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js` —
> e applicato il **suo** cancello:
>
> | | atteso (manifesto del coordinatore) | misurato (fonte canonica) |
> |---|---|---|
> | `sha256[:12]` | `300480069078` | **`300480069078`** ✅ |
> | byte | `1 173 007` | **`1 173 007`** ✅ |
>
> **Due ragioni per la deviazione, e la seconda è la più importante**: ① il mio mandato vieta di
> leggere un altro checkout, e l'autorizzazione del coordinatore non cancella la ragione per cui
> quella regola esiste; ② **la fonte canonica è una provenienza migliore di una copia di tre
> giorni fa** — e la coincidenza esatta di hash **e** dimensione prova che la sua cache **non era
> stale**, che era esattamente il rischio che il suo cancello voleva escludere.
> Manifesto riscritto con `current_hash`, `size`, `etag` (`W/"11e60f-0zusawQQZK5DMNzC2Vjr5MKOvlg"`).
> **Esito: `✅ JS libraries cached` · `Frontend build is up to date`. Layer 1 chiuso.**

> **⚠️ Fuori pista 6 — la mia diagnostica ha scritto nella cartella dati di default.**
> Riproducendo il comando del server in primo piano ho passato `LIBREFOLIO_DATA_DIR`, che **non è
> il meccanismo giusto**: il server ha usato `backend/data/test/`, non `/tmp/librefolio-r3-a`.
> Ha creato `backend/data/test/custom-uploads/` con gli avatar seminati.
> **Contenuto**: `backend/data/**` è ignorato (`.gitignore:20`) → non raggiunge nessun checkpoint,
> `git status` resta pulito. **Ma il numero che avevo letto veniva dal database sbagliato**, ed è
> il motivo per cui la causa vera è emersa solo al giro dopo.

> **🔴 Fuori pista 7 — BLOCCO, e non è ambientale: due teste Alembic.** Vedi §Blocco 2.

---

### Passo 2 — la riparazione dello scatter · ✅ **21 Set 2026**

Due rotture **indipendenti e in serie**, entrambe silenziose, su Dashboard **e** Broker Detail:

1. `currentResults` mai passato a `L3RiskAdjusted` → `riskReturnResult` null → `points` [] →
   `hasScatter` false;
2. `includeCurrentCompositionRiskReturn` mai acceso → **la richiesta non chiede nemmeno
   `asset_risk_return`**.

Il controller è **già cablato da capo a fondo** (`:81` dichiara, `:219` inoltra, `:433` espone).
Solo il chiamante non l'ha mai acceso. → **due edit additivi in `RiskLevelsPanel`,
`L3RiskAdjusted` intatto.**

---

### Passo 3 — smontaggio di `:314` + ri-puntamento del cancello euro · ✅ **21 Set 2026**

Il montaggio del monolite contribuisce **due cose sole, entrambe difetti**: una seconda heatmap
(collisione strict-mode) e lo shock ipotetico vietato da `03` §3.3.

🔴 **Ma il test «prints no money, even when the API hands it some» gira sulla UI dello stress
legacy.** Toglierlo senza ri-puntarlo non lo rende rosso: **lo rende verde su niente.**

Sostituzione like-for-like, trovata misurando `risk-mocks.ts`: i mock iniettano `impact_amount`
**anche nel replay** (`:370`, `:381`), non solo nello shock (`:404`, `:412`).

| | prima | dopo |
|---|---|---|
| click | `risk-stress-run` | `risk-replay-run` |
| barriere | `risk-stress-section` · `risk-stress-impacts` | `risk-replay` · `risk-replay-total` |
| catalogo | `risk-analysis-panel[data-catalog]` | superficie mia |

➕ Due asserzioni **dimensionali**: `risk-analysis-panel` assente dentro
`asset-global-risk-panel`, e heatmap `toHaveCount(1)`.

---

### Passo 4 — il contratto per il mandato backend · ✅ **21 Set 2026**

Sei clausole, con ⓪ **in cima** per decisione del coordinatore: *«una scelta presa per costo si
riapre appena il costo cambia; una presa per correttezza no.»*

> **Note implementazione**: consegnato in
> [`A-contratto-asset-set.md`](../A-contratto-asset-set.md), 8 sezioni. Contiene la misura dei
> nove plugin, il precedente `RiskStressImpact` (la forma **non va progettata: esiste**), la
> verifica riga-per-riga che **`asset_risk_return` non usa i pesi per l'aritmetica** (tre soli
> punti accessori, e il frontend è già tollerante su tutti e tre → *tre campi opzionali + una
> guardia rimossa + l'enum, zero modifiche al frontend*), le sei clausole, e la domanda aperta ⑤
> su `supported_modes` con raccomandazione `HISTORICAL` **motivata da ⓪**.
> ⚠️ La clausola ① è marcata come **difesa di una decisione di prodotto**: se il backend
> fabbricasse un portafoglio su `ASSET_SET`, la Capital Market Line — cioè il giudizio che questa
> pagina vieta — **rientrerebbe dalla porta dei dati, invisibile a qualunque test del frontend**.

---

## 🔴 Blocco ambientale — nessun E2E è eseguibile in questa corsia

**Comando esatto:**
```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6170 --data-dir /tmp/librefolio-r3-a \
  front-portfolio risk "L3 asks for the risk/return pair"
```
**Esito**: `Shared backend exited during startup (code 1)` → `shared test backend failed to start`.
**Quando**: **prima della raccolta.** Non è un fallimento di prodotto, e non è un rosso di test.
**Cosa è stato toccato**: nulla. Nessun DB scritto, nessun file di dati, nessun processo
sopravvissuto. Porta `6170` verificata **libera** (`lsof` vuoto) prima e dopo.

**Causa, isolata eseguendo il comando del runner in primo piano** (`_server.py:_command`):

```
📦 Checking mathjax...
  ⚠️  Failed to download https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js:
      <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
       Missing Authority Key Identifier (_ssl.c:1032)>
  ❌ Download failed and no cached version exists
❌ Resource cache incomplete - aborting frontend build
❌ Frontend build failed. Server not started.
```

**Caratterizzazione — non è la rete, è il bundle di certificati del venv condiviso:**

| sonda | esito |
|---|---|
| `curl -I` sulla stessa URL | **HTTP 200**, `Content-Length: 1173007` |
| `urlopen` nel venv `LibreFolio-SAUMUTtc` | `CERTIFICATE_VERIFY_FAILED: Missing Authority Key Identifier` |
| `certifi.where()` | `~/.local/share/virtualenvs/LibreFolio-SAUMUTtc/…/certifi/cacert.pem` |

**Perché colpisce proprio un worktree fresco**: `mkdocs_src/docs/javascripts/vendor/` è **ignorato**
(`.gitignore:78`), quindi il file non arriva col checkout e **deve** essere scaricato.

⚠️ **Due osservazioni che non sono mie da riparare:**
1. **Il venv è condiviso da tutte le corsie.** Se la causa è il suo `certifi`, **ogni worktree
   creato da adesso in poi colpisce lo stesso muro**, non solo il mio.
2. **Un asset di *documentazione* blocca il build dell'*applicazione*.** `mathjax` ha
   `vendor_dir_key: "mkdocs"` → finisce in `mkdocs_src/`, e il frontend **non lo spedisce**; ma
   `update_js_cache` lo dichiara *hard failure* e `front build` aborta. → nessun E2E, in nessuna
   corsia, per un file che serve ai docs.

**Non ho applicato alcun aggiramento**, come impone il protocollo: niente `pip install --upgrade
certifi` (modificherebbe il venv condiviso), niente `curl` del file nella cartella vendor, niente
modifiche a `update_js_cache.py`. **Riportato al coordinatore, in attesa.**

---

## Definizione di fatto — fase 1

1. `front check` → **3 errori, gli stessi 3, nessuno in un file `risk`**.
2. La rete dello scatter **rossa prima** della riparazione e **verde dopo** (le due misure, non una).
3. `front-portfolio risk-lab` verde, cancello euro **ancora dietro un click**, heatmap
   `toHaveCount(1)`, `risk-analysis-panel` assente.
4. `front-portfolio risk-asset-detail` verde: **Asset Detail non si è mosso**.
5. Contratto backend consegnato.
6. Porta `6170` libera: `lsof -nP -iTCP:6170 -sTCP:LISTEN` vuoto.
7. Handoff con `FROZEN`. Nessun `git commit`.

---

## 🔴 Blocco 2 — due teste Alembic: **nessun database fresco è creabile su questa baseline**

**Layer 1 (mathjax) chiuso** → il backend arriva più avanti, e scopre la causa vera.

**Comando esatto:**
```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6170 --data-dir /tmp/librefolio-r3-a db populate --force --clean
```
**Esito:**
```
ERROR [alembic.util.messaging] Multiple head revisions are present for given argument 'head';
please specify a specific target revision, '<branchname>@head' ... or 'heads' for all heads
Failed to apply database migrations
❌ Mock data population - FAILED (exit code: 1)
```

**Verdetto di Alembic stesso** (eseguito, non dedotto): `pipenv run alembic heads` →
```
003_asset_benchmark_flag_and_taxonomy (head)
003_user_onboarding_progress (head)
```

**Il grafo, misurato leggendo `revision`/`down_revision` di tutti e cinque i file:**

```
001_initial → 002_identifier_other_json_list → 5b1333fa6b07
                                                    ├── 003_asset_benchmark_flag_and_taxonomy   ← 00d8c735b
                                                    └── 003_user_onboarding_progress            ← 35f0bb484
```

**Due migrazioni dichiarano lo stesso `down_revision = "5b1333fa6b07"`.**

> 🔑 **È il merge `f829cd76b` che ha unito i file senza unire il grafo.** Git non ha segnalato
> nulla perché sono **file diversi**: nessun conflitto testuale, **un conflitto semantico**. È
> esattamente la forma che il mio mandato mi dice di cercare — *«segnala la sovrapposizione
> semantica anche quando Git non riporta conflitti»*.

### Perché nessuno se n'era accorto — **ed è la stessa forma del blocco mathjax**

Un database **già esistente** è stampato su **una** testa e continua a funzionare. Solo chi ne
crea uno **nuovo** incontra il muro.

> **Le corsie che girano, girano per anzianità, non per salute.** Identico a mathjax: lì una
> cache del 18 Set, qui un DB stampato prima del merge. **Due volte, lo stesso inganno: uno stato
> vecchio che fa sembrare sano un albero che non lo è.**

### Portata — **più larga della mia corsia**

| chi | effetto |
|---|---|
| ogni worktree nuovo | `db populate --force --clean` fallisce → **nessun E2E** |
| qualunque `db create-clean` | fallisce |
| 🔴 **installazioni rilasciate che aggiornano a questa baseline** | `alembic upgrade head` → **stesso errore** |

L'ultima non è un problema di test: è la regola *«migrazioni incrementali per proteggere le
installazioni esistenti»* di `copilot-instructions.md`, e questa baseline **non la rispetta**.

### Non l'ho aggirato

La riparazione è una **merge revision** (`alembic merge -m "…" 003_asset_benchmark_flag_and_taxonomy
003_user_onboarding_progress`) — **un file nuovo in `backend/alembic/versions/`**, additivo, che
non riscrive nessuna delle due migrazioni.

🔴 **Ma `backend/` è fuori dal mio perimetro per mandato esplicito** (*«non aprire il backend di
tua iniziativa: misuralo e segnalamelo»*). **Misurato e segnalato. Non tocco.**

Nessun aggiramento tentato: niente `upgrade heads` a mano, niente `stamp`, niente modifica ai
`down_revision` esistenti.

---

## Esito della fase 1 — misurato, non dedotto

### Blocco Alembic: riparato, con l'eccezione autorizzata dal coordinatore

`backend/alembic/versions/ab290f6b6756_merge_the_benchmark_taxonomy_and_.py` — **file nuovo,
`upgrade`/`downgrade` vuoti**, `down_revision` = tupla delle due teste. **Nessuna delle due
migrazioni riscritta**, nessuno `stamp`, nessun `upgrade heads` a mano.

> **Note implementazione**: il file generato era muto — un'`upgrade()` vuota non dice perché
> esiste. Gli ho aggiunto il docstring che spiega il fork, perché Git non lo aveva segnalato
> (file diversi), e perché il guasto è invisibile a chi ha già un DB stampato.

**I tre cancelli, tutti eseguiti:**

| | cancello | esito |
|---|---|---|
| ① | `alembic heads` | **`ab290f6b6756 (head)`** — una sola |
| ② | `db populate --force --clean` sulla corsia | ✅ `Mock data population - PASSED` |
| ③ | **percorso delle installazioni rilasciate** | ✅ vedi sotto |

**③ — come l'ho costruito, perché la differenza va dichiarata.** Il coordinatore suggeriva
`alembic stamp` su un file vuoto. **Non l'ho fatto**: stampare un DB vuoto su una testa lo fa
*dichiarare* una revisione che non ha, e l'unica migrazione che resterebbe da applicare è quella
vuota — **proverebbe che il grafo si risolve, non che la migrazione si applica.**

Ho costruito uno **schema vero** eseguendo la catena reale, su un DB usa-e-getta nella mia corsia,
con l'URL passata **esplicitamente** (`-x sqlalchemy.url=…`, perché il Fuori pista 6 mi aveva già
insegnato che una variabile d'ambiente viene ignorata in silenzio):

```
001_initial → 002_identifier_other_json_list → 5b1333fa6b07 → 003_user_onboarding_progress
```
poi `upgrade head`:
```
PRIMA:  SELECT COUNT(*) FROM pragma_table_info('assets') WHERE name='is_benchmark';  → 0
        Running upgrade 5b1333fa6b07 -> 003_asset_benchmark_flag_and_taxonomy
        Running upgrade 003_asset…, 003_user… -> ab290f6b6756
DOPO:   SELECT COUNT(*) …                                                            → 1
        SELECT version_num FROM alembic_version;                        → ab290f6b6756
```

> **Etichetta onesta**: il *percorso di migrazione* è quello reale. Ciò che resta simulato è il
> **soggetto** — un DB costruito dalle migrazioni, non l'installazione di un utente con dati veri.
> Sonda rimossa a fine prova.

### La rete: rossa prima, verde dopo — **le due misure, non una**

**ROSSA** (codice non riparato), e rossa per la ragione esatta, con la diagnosi stampata:
```
Expected value: "asset_risk_return"
Received array: ["risk_contribution"]
```
**La richiesta non chiedeva l'analitica.** È la rottura B, la prima delle due in serie.

**VERDE** dopo i due edit additivi in `RiskLevelsPanel`: `1 passed`.

### La riparazione, e il terzo effetto **sorvegliato invece che silenzioso**

Due edit, entrambi additivi, `L3RiskAdjusted` **intatto** (il guasto era tutto nel chiamante):
`includeCurrentCompositionRiskReturn: true` · le tre prop `currentResults`/`assetNames`/
`appliedRiskFreePercent`.

Decisione **ⓑ** del coordinatore applicata: la rete asserisce `data-perimeter =
'current_composition'` su `risk-l3`, letto dal **payload** e non dall'onda passata — così una
fixture che etichettasse male la propria risposta non potrebbe farla passare.

> **⚠️ Fuori pista 8 — il mock era infedele al catalogo reale.** Dichiarava `historical_kpi` con
> `['historical']`, mentre il backend annuncia **`HISTORICAL, CURRENT_COMPOSITION`** (misurato sul
> plugin). Corretto: senza, lo scambio di perimetro non sarebbe stato **osservabile** nel test, e
> avremmo sorvegliato un cambiamento che il mock rendeva impossibile.

**Regressione**: `front-portfolio risk` → **14/14 verdi**. I tre test che fissano
`sortino 1.68` / `sharpe 1.21` / `volatility 14.2%` **non si sono mossi**.

### Lo smontaggio, e cosa se n'è andato con lui

`AssetSetRiskPanel`: rimossi l'import e il montaggio. Docstring riscritto per spiegare **perché**
togliere il legacy non ha tolto niente (due sole capability su `asset_set`, entrambe difetti) e
🔴 che **il componente non è cancellato**: `AssetRiskScenariosView:89` lo monta ancora.

> **🔴 Fuori pista 9 — una capacità utente è uscita con il monolite, e va detta.**
> `RiskAnalysisPanel:581` porta `risk-sync-button` e `:1076` il `PageSyncModal`. Era **l'unico**
> punto di sincronizzazione prezzi/FX su Asset Global. Smontato il monolite, `onsynced` è rimasto
> **morto**: l'ho rimosso dalle `Props` e dal chiamante, invece di lasciarlo dichiarato e mai
> chiamato — **un prop che il genitore riempie di lavoro vero e che nessuno invoca è peggio di un
> prop assente: il genitore crede di aver cablato qualcosa.** Le tre funzioni del chiamante
> (`invalidateAssetPriceStore`, `rearmMaxPendingBeforeReload`, `fetchAllPriceData`) restano usate
> 7/7/14 volte altrove: nessuna è rimasta orfana. **Decisione del coordinatore richiesta.**

### Il cancello euro: ri-puntato, e **più forte**

> **🔴 Fuori pista 10 — il mio briefing allo specialista era falso, e avrebbe prodotto un verde su
> niente.** Avevo scritto che i mock del laboratorio iniettano già denaro nel replay, citando
> `risk-mocks.ts:370/381`. **`risk-lab.spec.ts` non importa affatto `risk-mocks.ts`**: ha uno stub
> inline, il cui `resultFor` conosceva `correlation` e `stress`, e il cui `stressOutput()` era uno
> **shock ipotetico**. Ri-puntando solo i click, `tornadoRows` avrebbe preso il ramo *bucket*, dove
> `amount` è `null` per costruzione: **l'esca monetaria si sarebbe disarmata da sola e il cancello
> sarebbe passato provando nulla.** Trovato da `test-author`, non da me.

> **🔴 E la seconda metà dell'esca**: `L4Replay:207` è `{#if output.portfolio_return != null}` — la
> frase è **trattenuta**, non degradata. Con un `portfolio_return` nullo, `impact_amount` è
> **irraggiungibile per costruzione**, e asserirne l'assenza non prova niente. Lo stub manda quindi
> un `portfolio_return` non nullo **di proposito**, ed è commentato come tale.

> **⚠️ Fuori pista 11 — e una debolezza nel test che avevo scritto io nel round 2.**
> `expect(rendered).toContain('%')` scansionava **l'intero pannello**: un `%` della matrice
> soprastante lo soddisfaceva **mentre il replay non renderizzava nulla**. Ora è letto da
> `risk-l4-replay`. *La barriera di presenza guardava la pagina invece della sezione.*

📌 **E il codice analitico del replay è `stress`**: non esiste un codice distinto, il discriminante
è `parameters.method === 'historical_replay'`. Il `poll` ora prova che è corso **un replay**, non
«un qualche stress».

**Percorso nuovo**, con il denaro dietro **due** click invece di uno (Ⓒ):
`risk-replay-section[data-open=false]` → `-toggle` → `data-open=true` → `risk-l4-replay` →
`risk-replay-run` → barriere `risk-replay-total` · `risk-replay-tornado-row` · `risk-replay-audit`
→ **le asserzioni monetarie verbatim** (`MONEY_PATTERN`, `€`, `.currency-symbol` a 0).

➕ Due asserzioni **dimensionali**: `risk-analysis-panel` a **0** dentro `asset-global-risk-panel`,
heatmap a **1**. Descrivono una **causa**; le monetarie un **effetto**. Servono entrambe: se domani
un altro componente stampasse euro qui, le due dimensionali resterebbero verdi.

> **⚠️ Fuori pista 12 — due commenti miei erano diventati falsi, e li ho corretti.**
> Il docstring di `AssetSetReplaySection` avvisava di due frasi di `L4Replay` che parlano come se i
> pesi esistessero. **Entrambe sono state riparate** (`:207` trattiene la frase, `:238` sceglie fra
> `replayAuditOmitted` e `replayAudit`). L'avviso avrebbe mandato il prossimo lettore a caccia di
> un difetto che non c'è più. Riscritto per registrare la riparazione invece del difetto.

### I cancelli finali

| cancello | esito |
|---|---|
| `front check` | **3 errori, gli stessi 3, `0` in un file risk** |
| `tsc -p tsconfig.e2e.json --noEmit` *(vincolo Ⓘ)* | **0 in `e2e/portfolio/`**, 76 preesistenti altrove |
| `prettier --check` sui file toccati | ✅ |
| `front-portfolio risk` | ✅ **14/14** |
| `front-portfolio risk-lab` | ✅ **6/6** — da non eseguibile a verde |
| `front-portfolio risk-asset-detail` | ✅ **2/2** — Asset Detail non si è mosso |
| porta `6170` | **libera** (`lsof` vuoto) |
| `git diff --check` | pulito |

---

# FASE 2 — `L1°` e `L3°` sui cinque codici di P

> **Baseline**: `09117b434` ✅ verificata · **autorizzazione sviluppatore**: *«si ok, serializza
> questi lavori e al termine notificami»* · corsia invariata `6170` · `/tmp/librefolio-r3-a`

### Passo 2.0 — `api sync` · ✅ 21 Set 2026

Obbligatorio dopo un cambio di baseline: P ha aggiunto cinque contratti. `generated.ts`,
`openapi.json` e i contratti tool rigenerati.

### Passo 2.1 — il filo: una richiesta sola per tutta la pagina · ✅ 21 Set 2026

> **Note implementazione**: nuovo flag opt-in `includeAssetSetLevels` in `buildBaseAnalytics`
> (`riskAnalysisHelpers.ts`) che aggiunge i cinque codici, ciascuno dietro la guardia di capability
> già esistente — quindi **inerte su ogni scope diverso da `asset_set`**. Inoltrato dal controller.
> Due istanze distinte per il VaR (`ASSET_SET_DAILY_VAR_INSTANCE` / `…_MONTHLY_…`), come la coppia
> singolare, perché lo stesso codice a due orizzonti non va confuso.

**Perché un flag solo e non uno per sezione** — misurato, non supposto:

```
riskStore.queryRisk:131   const key = makeRiskRequestKey(canonicalizeRiskRequest(request));
                          cache + in-flight promise su QUELLA chiave
service.py:170            prepared = await self._prepare_asset_series(...)   ← UNA volta per RICHIESTA
```

> **Se tutte le sezioni del laboratorio chiedono lo stesso insieme di codici, le loro richieste
> sono canonicamente uguali → un volo, una risposta in cache, una preparazione.** È la metà
> frontend della clausola ⓪; la metà backend è `service.py:170`, che prepara per *richiesta* e non
> per analitica.

> **🔴 Fuori pista 13 — il benchmark doveva stare negli *input*, non nelle *opzioni*, e per poco
> non l'ho sbagliato.** `asset_set_comparison` vuole un `comparison_asset_id`. L'avevo messo fra le
> opzioni del controller — che sono lette **una volta sola alla creazione**. Ma `baseSignature`
> (riga 119) non include le opzioni: **un cambio di benchmark non avrebbe invalidato nulla**, e il
> lettore avrebbe scelto un riferimento che la richiesta ignorava in silenzio. Spostato in
> `RiskControllerInputs` e aggiunto alla firma. **Additivo e invisibile agli altri pannelli**:
> `JSON.stringify` omette `undefined`, quindi per chi non lo passa la firma è byte-identica.

> **🔴 Fuori pista 14 — e il riferimento deve viaggiare nella STESSA richiesta.** La mia prima
> stesura lasciava `asset_set_comparison` fuori dall'onda condivisa, da chiedere a parte. È
> sbagliato, e il docstring di P lo dice: *«the reference is prepared inside the same request as
> the scope»*. Una richiesta separata avrebbe preparato il benchmark su un calendario congiunto
> **che non contiene la selezione** → il suo punto sullo scatter sarebbe nato su date diverse dai
> punti accanto. **È esattamente Ⓔ**, e la formulazione di S3 è già nell'albero: *«the dot would
> land in a place no measurement puts it, on a chart that still looks right»*.

### Passo 2.2 — `assetSetLevels.ts`, l'aritmetica pura · ✅ 21 Set 2026

> **Note implementazione**: `buildAssetSetHurtRows` (L1°), `buildAssetSetPaidRows` (L3°),
> `buildAssetSetScatterPoints`, `buildAssetSetBenchmarkPoint`. Nessun parametro `currency`
> **esiste** in questo file: non c'è un importo da dimenticare di sopprimere.
> **Le righe si costruiscono dalla selezione, le celle sono nullable** — mai il contrario: un
> asset che il backend non ha potuto misurare **mantiene la sua riga**, perché una riga mancante si
> legge come «non selezionato», non come «non misurabile».

> **⚠️ Fuori pista 15 — il compilatore ha trovato una trappola che avevo scritto.**
> `npx tsc` ha rifiutato quattro righe: il client generato **allarga ogni campo numerico opzionale**
> a `((number | null) | Array<number | null>)`, perché è così che l'`anyOf` di OpenAPI fa
> andata-e-ritorno. `stats.sharpe` è quindi *un valore **o una lista***. Leggerlo diretto compila
> solo con un cast — **e un cast è esattamente il modo in cui un array arriva a `toFixed` e stampa
> `NaN`**. Esiste già la primitiva di casa, `singleValue`: ora `num()` ci passa attraverso.
> **Ed è il motivo per cui ho tipizzato `byAsset` come generico invece di `Record<string,
> unknown>`**: quest'ultimo avrebbe accettato `conditional_value_at_risk` su una riga di drawdown
> e sarebbe morto a runtime. *Il client zod serve a questo; disattivarlo con un cast lo spreca.*

### Passo 2.3 — i due livelli, l'i18n, la copertura · ✅ 21 Set 2026

**Componenti nuovi**: `AssetSetComparisonLevels.svelte` (un controller, due `RiskLevelSection`),
`AssetSetLossComparisonSection.svelte` (L1°), `AssetSetRiskReturnSection.svelte` (L3°),
`assetSetLevels.ts` + `assetSetLevels.test.ts`.

**i18n**: `+43/−0` in tutte e quattro le lingue — **nessuna chiave esistente toccata**.
`i18n audit` → 3388 chiavi, **0 incomplete, 0 backend mancanti**.

> **🔴 Fuori pista 16 — un bug mio, trovato eseguendo, che nessun `front check` poteva vedere.**
> La pagina renderizzava *«Select at least one asset»* **con quattro asset selezionati**: uno stato
> che il codice non può produrre. `svelte-check` verde, build pulito, tipi a posto — **vincolo Ⓝ
> in azione: il cancello vede se il client si costruisce, non come si comporta.**
>
> Causa: `riskBenchmark.assetId` è **un getter che scrive**. Il suo `hydrate()` assegna a
> `$state`, e io lo leggevo dentro un `$derived`. In runes mode **scrivere stato durante una
> derivazione è fatale**: la derivazione muore, e con lei l'intero blocco `{#if}` che la legge —
> i controlli restano a schermo e ogni sezione sotto sparisce, **il che assomiglia esattamente a
> "nessun asset selezionato"**. `L3Benchmark` se la cava perché legge dentro un handler.
> ✅ Riparato con un mirror in `$state` alimentato da `$effect` (un effetto *può* scrivere).
>
> 🔑 **La forma**: *un getter che muta su lettura è innocuo in una funzione e letale in una
> derivazione* — e il sintomo non assomiglia alla causa.

> **⚠️ Fuori pista 17 — il guardiano del catalogo ha trovato una deriva al primo colpo.**
> L'impegno che avevo preso («il finto è una copia a mano del vero senza legame fra i due») è
> ora un test: per ogni codice dichiarato dal `CATALOG` dello spec, confronta `supported_scopes` e
> `supported_modes` **con il registro reale**, interrogato senza installare i mock.
> **Primo esito: rosso.** `portfolio_optimization` è annunciato dal backend per `asset_set` e il
> finto non lo dichiarava. Dichiarato per fedeltà — la pagina non lo richiede.
> ➕ Lo specialista ha **indurito** il guardiano oltre il mandato: lo stub marchia
> `algorithm_version = 'e2e-mock-v1'` e la prima asserzione è che **nessuna definizione ricevuta
> porti quel marchio** — così spostare `installRiskMocks` in un `beforeEach` rende il test rosso
> invece che vacuo. *Una convenzione che un edit futuro può rompere in silenzio non è un cancello.*
> ⚠️ E ha trovato che `historical_kpi` era drifted **anche in questo file** (`['historical']`):
> **quarta occorrenza**, viva, non storica.

> **⚠️ Fuori pista 18 — tre miei export senza consumatore, e un docstring che prometteva troppo.**
> `assetSetResult`, `ASSET_SET_HURT_CODES`, `ASSET_SET_PAID_CODES` non erano letti da nessuno:
> *«un campo senza consumatore è un rosso di fine fase»* vale anche per il mio codice. Rimossi.
> E il docstring di `num()` diceva che senza `singleValue` un array arriverebbe a `toFixed`
> stampando `NaN`: **falso a runtime.** Lo zod generato rifiuta la lista e scarta l'intero payload;
> l'allargamento è solo di TypeScript. Corretto — *descrivere male una difesa è il modo in cui il
> prossimo la rimuove credendola inutile.*

> **🔑 Fuori pista 19 — il tipo ha dimostrato l'invariante meglio del test.**
> Il Vitest asseriva `points.some((p) => p.role === 'portfolio') === false`. `svelte-check` l'ha
> **rifiutata**: `role` è il literal `'asset'`, quindi il confronto «non ha sovrapposizione».
> **La garanzia anti-giudizio è così forte che verificarla a runtime è un errore di compilazione.**
> Sostituita da un commento che lo dice: il compilatore tiene l'invariante, il test tiene il
> lettore. *Ed è la stessa tesi della clausola ①, un livello più in basso: una difesa che vive in
> una forma non si può disfare per distrazione.*

### Cancelli di fine fase 2

| cancello | esito |
|---|---|
| `front check` | **3 errori, gli stessi 3, `0` in un file risk** |
| `tsc -p tsconfig.e2e.json` *(Ⓘ)* | **0 in `e2e/portfolio/`**, 76 preesistenti altrove |
| `prettier --check` sui file toccati | ✅ |
| `services risk-all` | ✅ **437 passed** |
| `front-portfolio risk-lab` | ✅ **11/11** (erano 6) |
| `front-portfolio risk` | ✅ **14/14** — Dashboard e Broker invariati |
| `front-portfolio risk-asset-detail` | ✅ **2/2** — Asset Detail non si è mosso |
| `vitest assetSetLevels.test.ts` | ✅ **30/30** |
| `i18n audit` | ✅ 3388 complete, 0 incomplete |
| `check-orphans` | ⚠️ **1 orfano atteso**: `assetSetLevels.test.ts` — **registrazione del coordinatore** |
| porta `6170` | libera · `git diff --check` pulito |
