# Piano — fase 00, 54: le quote e lo YoC della fixture della galleria (I-M30)

> **Stato**: ✅ **Checkpoint pronto** (2026-10-13), poi FROZEN. Tre stadi, verdi uno per uno: la fixture col suo
> Vitest (C1), lo script col suo pytest e la voce del runner (C2), questo piano col backlog (C3). Il manifest è nel §6,
> la privacy nel §5.
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), lotto **I-M30**, strada **(b)**, il ricalcolo
>   deterministico. Il developer è via per la notte e ha delegato al coordinatore. **Origine**: M, negli scatti della
>   galleria la storia dell'allocazione (stack al 100 %) non arriva in cima, in Tipo, Settore e Geografia.
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Base **`24a960283`** (treno 97); worktree pulito, porta
>   6157 libera.
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta, **1 worker**.
>   R fa la run finale con coverage sulla 6176: sonde brevi, niente suite lunghe. Mai le porte 6040, 6041 e 6176, mai
>   `--force`, mai la galleria, mai `mkdocs serve`.
> - **Tocca**: `scripts/normalize_dashboard_fixture.py`; `frontend/e2e/dashboard-report.json` (solo le righe `value`
>   delle quote e dello YoC, più `price_change_1d` dal §1.7); `frontend/src/lib/api/dashboardReportFixture.test.ts`
>   e il nuovo `backend/test_scripts/test_utilities/test_normalize_dashboard_fixture.py` (test-author);
>   `scripts/test_runner/_backend_utils.py` (la voce del runner, la scrivo io); `BACKLOG_POST_1.2.md` (sezione I);
>   questo piano.
> - **Non tocca**: la devWiki (ha un solo scrittore, W: le proposte vanno al coordinatore); il CHANGELOG (l'app non è
>   mai stata toccata); la galleria e gli scatti (M); le istruzioni condivise che descrivono lo script
>   (`frontend-testing.instructions.md:355-359`, `test-author.agent.md:256-260`, `devpy-mkdocs/SKILL.md:57-60`): dopo
>   la cura dicono il vero.
> - **Privacy**: nessun numero reale (patrimonio, importi, fattore di scala, somme per giorno) in questo piano, nei log
>   o nei messaggi. Le misure stampano solo conteggi, percorsi, date e sì/no.

## 0. Autorizzazione (2026-10-13)

Il coordinatore: «Analisi chiarissima. Il developer è via per la notte e mi ha delegato il lavoro, quindi decido io
quello che si può decidere senza di lui. **Via al lotto I-M30, strada (b), il ricalcolo deterministico.** La domanda
sulla storia di git resta al developer, domattina.

**Cartella `Phase_0/54_galleryFixtureShares/`**; il 52 e il 53 sono presi. Base: la tua worktree, a `24a960283`.

1. **Prima i rossi**, via test-author:
   - il Vitest in `dashboardReportFixture.test.ts` (somma 100 per giorno e per dimensione; YoC = gross/WAC);
   - il pytest nuovo per lo script. **La voce in `_backend_utils.py` la scrivi tu**: nessun altro tocca quel file
     adesso.
2. **La cura**:
   - eccezioni per percorso nello script, con invarianti che falliscono forte;
   - la fixture ricalcolata, toccando solo le righe `value` di allocazione e di YoC.
3. **Privacy, da allargare prima del checkpoint, solo misura**: dopo la cura, il fattore si ricava ancora per altre
   vie? Per esempio quantità non scalate per prezzi pubblici, contro valori scalati, o qualunque coppia di campi
   scalato e non scalato. Scrivi solo il sì o il no e il campo; nessun numero.
4. **I consumatori della fixture**: elenca chi legge `e2e/dashboard-report.json` oltre alla galleria. Se ci sono spec
   della suite normale, falli girare (la 6157, un comando alla volta). R è a metà della run finale sulla 6176, che non
   li rivede.
5. **La nota sulla liquidità negativa** (quote oltre 100, taglio a `max: 100`): voce bassa nella sezione I del
   backlog, dopo la 1.2.
6. Il checkpoint, FROZEN. Poi M rifà gli scatti `allocation-*` e le Posizioni con lo YoC.

**Niente numeri reali** nel piano, nei log o nei messaggi.»

## 1. Analisi (dal rapporto del 13/10, in sintesi)

### 1.1 La causa

- `SCALE_NAME_RE` (`scripts/normalize_dashboard_fixture.py:61-65`) contiene `value`. Lo script lo applica al **nome
  della chiave**, quindi scala come denaro anche due numeri che denaro non sono:
  - `AllocationItem.value`, la quota in percento (`backend/app/schemas/portfolio.py:79`, «Percentage share (0-100)»);
  - `YieldOnCostResult.value`, la frazione dello YoC (`:317`, «0.04 means 4%»).
- **L'effetto**: ogni lista di quote somma al fattore × 100, non a 100. Lo stack di `AllocationHistoryChart`
  (`max: 100`, `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:802`) disegna onestamente la cima
  lì. Lo YoC disponibile vale il fattore × il vero.
- **Le famiglie toccate**: `summary.allocation_by_{type,sector,geography}[*].value`,
  `allocation_history.{type,sector,geography}[*].components[*].value`, `summary.holdings[*].yield_on_cost.value`. Le
  altre famiglie scalate sono denaro o prezzi unitari, ed è giusto così (`/tmp/libreFolio_i_m30_paths.log`, solo
  nomi).

### 1.2 Un difetto della fixture, non dell'app

- L'API dal vivo sulla 6157 (dati sintetici della corsia): ogni lista somma a 100 entro l'arrotondamento.
- La torta (`AllocationPanel.svelte:60-67`) e il tooltip leggono le stesse liste della fixture: nella galleria sono
  sbagliati allo stesso modo.
- Nessuna serie nascosta, nessuna categoria esclusa, nessun componente negativo nella fixture.

### 1.3 La provenienza

- Lo script (`17adbe0f4`) e la prima fixture normalizzata (`3e33372c6`) sono antenati di `v1.1.0`
  (`git merge-base --is-ancestor`): la galleria della 1.1 era già sbagliata.
- L'app non è mai stata toccata: **niente riga nel CHANGELOG**.

### 1.4 Le formule della cura

- **Le quote** (`backend/app/services/financial_math/portfolio/derived_views.py:231-243` e `:245-268`): per ogni
  lista `total = sum(amounts) or Decimal("1")` e `value = (amt / total * 100).quantize(Decimal("0.01"))`. Il contesto
  Decimal è quello di default (28 cifre, `ROUND_HALF_EVEN`): in `backend/app` nessuno lo cambia. L'`amount` di ogni
  voce è lo stesso `amt`, non arrotondato; nella fixture è scalato dello stesso fattore in tutta la lista, quindi il
  rapporto non cambia.
- **Lo YoC** (`backend/app/services/financial_math/yield_on_cost.py:700`): `value = gross_income_per_unit /
  converted_wac`. Lo stesso `converted_wac` diventa `holdings[*].wac_per_unit` (`portfolio_service.py:816`). Nella
  fixture `provenance.gross_income_per_unit.amount` e `wac_per_unit` sono scalati tutti e due: il rapporto è quello
  vero.
- **I formati**: le quote come l'API, stringhe a 2 decimali; lo YoC `available` come `Decimal` in notazione fissa;
  `no_income` (zero) e `unavailable` (`null`) restano come sono.
- **L'esattezza**: la sonda del 13/10 (`/tmp/libreFolio_i_m30_repair_exactness.log`) dà un rapporto fra quota
  scalata e quota ricalcolata costante su tutte le voci non nulle, con dispersione relativa dell'ordine di 1e-27.
  Quindi il ricalcolo ridà esattamente le quote che il backend aveva prodotto, prima che lo script le scalasse.

### 1.5 La regola 12

- La regola 12 (`.github/agents/test-author.agent.md:242`) vieta di aggiustare a mano una fixture catturata che non
  torna più con lo schema.
- Qui lo schema torna. Il difetto l'ha fatto lo script, e la cura (b) rifà con le formule del backend solo le righe
  derivate, partendo dagli importi già nella fixture: nessun dato inventato.
- La strada (b) è approvata dal coordinatore, su delega del developer (§0).

### 1.6 I consumatori della fixture

- `frontend/e2e/gallery.spec.ts:754`: la galleria di M; non la lancio.
- `frontend/src/lib/api/dashboardReportFixture.test.ts`: il Vitest di guardia, in `front-utility core-unit`.
- Lo script stesso, anche come `dev.py mkdocs normalize-dashboard-fixture` (`dev.py:922-926`, `:2606-2611`).
- Nessun'altra spec della suite normale legge la fixture.

### 1.7 Una terza famiglia: `price_change_1d` (13/10, dopo l'approvazione)

> **⚠️ Fuori pista**: rileggendo le 32 famiglie scalate (`/tmp/libreFolio_i_m30_paths.log`) contro lo schema e il
> servizio, `summary.holdings[*].price_change_1d` non è denaro: è una frazione, `(cur − prev) / prev` quantizzata a 4
> decimali (`portfolio_service.py:839`). Lo script la scala perché la chiave contiene `price`. Nell'analisi del 13/10
> l'avevo messa fra i prezzi unitari.
>
> - Nella fixture: 8 posizioni su 10. Nessun componente la legge (in `frontend/src` solo `generated.ts`): nessuno
>   scatto cambia.
> - **È una via di privacy**: con `gain_loss_change_1d_percent`, non scalato, dà il fattore. La relazione
>   `|pc × 100| ≈ |gl1d %|` (tolleranza 0,0101) tiene per 8 su 8 col valore ricalcolato, per 0 su 8 così com'è.
> - **Il ricalcolo è esatto**: diviso per il fattore, ricavato dentro lo script dalle quote e mai stampato, torna un
>   valore a 4 decimali per 8 su 8 (`/tmp/libreFolio_i_m30_pc1d_probe.log`, solo conteggi e sì/no).
> - **Decisione chiesta al coordinatore** (13/10): includerla nel lotto (eccezione, invariante, 8 righe in più nella
>   fixture), oppure solo l'eccezione e una voce nel backlog.
> - **Decisione** (coordinatore, 13/10): «**Includila**: l'eccezione di percorso per `holdings[*].price_change_1d`,
>   l'invariante solo sulle posizioni `MARKET_PRICE` con entrambi i campi, e le 8 righe ricalcolate. Chiude una via di
>   privacy e lascia la fixture coerente con lo script; la voce di backlog non serve.»

## 2. Il disegno della cura

### 2.1 Lo script

- **Eccezioni per percorso**: `NOT_MONEY_PATH_RE`, confrontata col percorso scritto con `[*]` al posto degli indici,
  prima di `SCALE_NAME_RE`:
  - `allocation_by_<dimensione>[*].value`;
  - `allocation_history.<dimensione>[*].components[*].value`;
  - `yield_on_cost.value`;
  - `holdings[*].price_change_1d` (§1.7).
- **Gli invarianti**, in `_verify`, dopo la trasformazione:
  - ogni lista di quote non vuota, con importi a somma diversa da zero, somma a 100 entro `0,005 × n` (l'errore
    massimo dell'arrotondamento a 0,01 su `n` voci). Le liste del riepilogo e quelle della storia, ogni dimensione;
  - ogni YoC `available` vale `gross_income_per_unit / wac_per_unit`, con una tolleranza relativa;
  - per ogni posizione `MARKET_PRICE` con `price_change_1d` e `gain_loss_change_1d_percent`:
    `||pc × 100| − |gl1d %|| ≤ 0,0101` (i due arrotondamenti, a 4 e a 2 decimali, valgono 0,005 ciascuno);
  - **i messaggi non portano valori**: la famiglia del percorso e il numero di liste o di posizioni che sbagliano,
    mai una somma, una quota, un rapporto o uno YoC.
- **La docstring** dice il vero: quote e frazioni hanno nomi da denaro e sono escluse per percorso.

### 2.2 La fixture

- Uno script in `/tmp` ricalcola con le formule del §1.4 e riscrive il file come lo script
  (`json.dumps(…, indent=2, ensure_ascii=False) + "\n"`).
- Prove: `git diff --numstat` e un controllo riga per riga, solo righe `"value": …` e `"price_change_1d": …`
  cambiate; il rapporto fra il vecchio e il nuovo è costante su tutte le voci non nulle, sugli YoC e sulle
  `price_change_1d` (stampato solo come sì/no).

## 3. Passi

### Passo 0 — Base e piano ✅ 2026-10-13

> **Note implementazione**: HEAD `24a9602830282390f7b8831a1550ac61312989d4`, 0 file sporchi, porta 6157 libera. Le
> cartelle 43-53 esistono, la 54 era libera. Letti lo script, il Vitest di guardia, il runner, `dev.py`, lo schema, le
> formule.

### Passo 1 — La voce del runner ✅ 2026-10-13

> **Note implementazione**: in `scripts/test_runner/_backend_utils.py` la funzione
> `utils_normalize_dashboard_fixture` (dopo `utils_docs_fr_typography`) e la voce `utils normalize-dashboard-fixture`
> in `populate_registry`, `isolation="pure"`, prima di `all`. Il file del test lo scrive test-author al passo 2.

### Passo 2 — I rossi (test-author) ✅ 2026-10-13

> **Note implementazione**: test-author ha scritto `backend/test_scripts/test_utilities/test_normalize_dashboard_fixture.py`
> (nuovo, 29 casi su report sintetici in `tmp_path`, più la fixture committata copiata e letta solo attraverso lo
> script, con l'output deviato in un buffer) e ha esteso `frontend/src/lib/api/dashboardReportFixture.test.ts` (un
> secondo `describe`: le tre relazioni sulla fixture e tre controlli negativi, ognuno prima riscritto perché la
> relazione tenga, poi rotto su una voce sola; l'intestazione aggiornata). Il primo blocco e i suoi 5 test sono
> invariati.
>
> - **pytest**, `utils normalize-dashboard-fixture`: 12 rossi su 29, tutti sul comportamento che manca: il report al
>   doppio del target (quote, YoC e `price_change_1d` scalati), `_walk` che elenca le quattro famiglie, il rifiuto
>   delle quote per famiglia, i due casi fuori tolleranza per lista del riepilogo e per giorno della storia, lo YoC
>   fuori tolleranza (due casi), `price_change_1d` fuori tolleranza (tre casi). Verdi: le tolleranze accettate, le
>   liste vuote o a valore zero, gli YoC non `available`, le posizioni non `MARKET_PRICE` o coi campi nulli, la fixture
>   committata (verde ora; rossa dopo il passo 3, verde dopo il 4).
> - **Vitest**, `front-utility core-unit`: 3 rossi su 4195, le tre relazioni sulla fixture committata; verdi i
>   controlli negativi e il resto della suite.
> - **Comandi**: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157
>   --data-dir /tmp/librefolio-r2-i-charts utils normalize-dashboard-fixture` e, con
>   `LIBREFOLIO_TEST_STARTUP_TIMEOUT=900` e `--workers 1`, `front-utility core-unit`. Log
>   `/tmp/libreFolio_i_m30_red_pytest.log`, `/tmp/libreFolio_i_m30_red_vitest.log`.
> - **Privacy dei log**: `/tmp/libreFolio_i_m30_leakcheck.py` confronta i token decimali dei log con le foglie numeriche
>   della fixture e stampa solo conteggi: 0 corrispondenze. ruff, black e prettier puliti.

> **⚠️ Fuori pista**: ho ritoccato io il testo del rimedio nel Vitest (l'intestazione e il passo 2 di
> `NOT_MONEY_SCALED`). «Ripara la fixture con lo script» non era vero: lo script non rimette a posto quote già scalate.
> Ora dice: una cattura nuova normalizzata con lo script corretto, oppure, su approvazione, il ricalcolo del piano 54.
> Prettier pulito.

### Passo 3 — La cura dello script ✅ 2026-10-13

> **Note implementazione**: `scripts/normalize_dashboard_fixture.py`.
> - `NOT_MONEY_PATH_RE` (le quattro famiglie del §2.1) e `LIST_INDEX_RE`; in `_walk` il percorso, con gli indici
>   scritti `[*]`, si confronta dopo `NEVER_SCALE_RE` e prima di `SCALE_NAME_RE`.
> - Tre controlli nuovi in `_verify`, dopo quelli di prima: `_share_errors` (con `_allocation_lists` e
>   `_share_verdict`, divisi per la complessità di ruff), `_yield_on_cost_errors`, `_price_change_errors`. Ogni riga
>   `❌` porta la famiglia e un conteggio, mai una cifra; le tolleranze sono costanti con nome, non stampate.
> - Barriere di presenza contro la deriva dello schema, coerenti con `schemas/portfolio.py`: un riepilogo senza
>   `allocation_by_*`, un giorno della storia senza `components`, una posizione senza `yield_on_cost`, uno YoC
>   `available` senza valore, lordo o `wac_per_unit` non nullo. Ognuna dà una riga `❌ … schema changed?` senza valori.
>   La relazione di `price_change_1d` vale per costruzione: le due gambe usano la stessa quantità e
>   `compute_holding_value` non arrotonda (`portfolio_service.py:839-853`).
> - La docstring dice le eccezioni per percorso e i tre controlli. ruff e black puliti.
> - **pytest**: 28 su 29 verdi. Rosso solo `test_the_committed_fixture_passes_its_dry_run_and_is_not_written`, come
>   previsto: la fixture di HEAD cade su 8 righe `❌`, cioè le 6 famiglie di quote, lo YoC e `price_change_1d`. Log
>   `/tmp/libreFolio_i_m30_s3_pytest.log`, controllo delle fughe pulito.

> **⚠️ Fuori pista**: il controllo delle fughe ha segnalato un token, cioè la durata di pytest («in #.##s»), uguale per
> caso a una foglia della fixture. Ora il controllo esclude le durate (`s`, `ms`); rilanciato su tutti i log: pulito.

### Passo 4 — Il ricalcolo della fixture ✅ 2026-10-13

> **Note implementazione**: `/tmp/libreFolio_i_m30_repair.py --with-price-change-1d` (fuori dal repo), prima a secco e
> poi in scrittura, con le formule del §1.4 nel contesto `Decimal` del backend (prec 28, `ROUND_HALF_EVEN`).
> `price_change_1d` torna sui 4 decimali dividendo per il rapporto vecchio/nuovo della prima quota non nulla.
> - **Cambiati**: 43 quote del riepilogo, 16265 della storia, 2 YoC `available`, 8 `price_change_1d`.
>   `git diff --numstat`: 16318 righe tolte e 16318 aggiunte, una per valore.
> - **Prove, solo sì/no e conteggi** (`/tmp/libreFolio_i_m30_diffcheck.py`, log `_diffcheck.log`):
>   - le righe cambiate sono solo `"value"` e `"price_change_1d"`, ognuna con la sua gemella (stessa chiave, rientro e
>     virgola);
>   - le foglie della fixture hanno gli stessi percorsi;
>   - le 16318 foglie diverse stanno tutte nelle quattro famiglie di `NOT_MONEY_PATH_RE`;
>   - la serializzazione si rilegge identica al byte.
> - Il rapporto vecchio/nuovo è costante per famiglia (quote, YoC, `price_change_1d`), le quote nulle restano nulle, e
>   ogni `price_change_1d` torna esatta sui 4 decimali.
> - **Il disegno a parte** (`/tmp/libreFolio_i_m30_families.py`, log `_families.log`, solo nomi e conteggi): sulla
>   fixture di HEAD, lo script corretto scala 79 famiglie, tutte di denaro, e ne salta per percorso 8, esattamente le
>   quattro forme volute. Le 79 sono le 32 famiglie scalate per nome del §1.7, meno le 8 escluse, più le 55 degli
>   oggetti valuta (`{code, amount}`), che il log del §1.7 contava a parte.

### Passo 5 — I verdi ✅ 2026-10-13

> **Note implementazione**: corsia 6157, un comando alla volta.
> - **pytest** `utils normalize-dashboard-fixture`: **29/29** (log `_green_pytest.log`).
> - **Vitest** `front-utility core-unit`, 1 worker: **128 file, 4195/4195** (log `_green_vitest.log`).
> - **Lo script sulla fixture curata**: `dev.py mkdocs normalize-dashboard-fixture --dry-run` passa, con 0 righe ❌, e
>   la fixture resta com'era (`numstat` identico prima e dopo).
> - **Lo script su una copia della fixture di HEAD in /tmp**: rifiuta con exit 1 e **8 righe ❌** (6 famiglie di quote,
>   YoC, `price_change_1d`; contate, non stampate). La copia resta intatta ed è poi cancellata.
> - **I log**: il controllo delle fughe passa su tutti i 22 log del lotto, contro le foglie della fixture di HEAD e di
>   quella curata.
>
> **⚠️ Fuori pista**: dopo la cura il controllo ha segnalato 5 gettoni nel log pytest, 1 in quello Vitest e 2 nel log del
> server dell'analisi. Il controllo li ha mostrati solo con le cifre mascherate: erano versioni di strumenti (Python,
> pytest, i plugin, Vitest) e `HTTP/1.1`.
> - La coincidenza è nuova: la fixture curata ha oltre 16 mila quote a due decimali, quindi i numeri corti ora vi
>   trovano un gemello.
> - L'espressione del controllo ora salta i pezzi di versioni puntate e le versioni di protocollo, e prende ancora un
>   decimale a fine frase. Sette casi sintetici lo provano; poi tutti i log sono stati ricontrollati.

### Passo 6 — La misura della privacy ✅ 2026-10-13

> **Note implementazione**: sulla fixture curata, `/tmp/libreFolio_i_m30_privacy.py` (log `_privacy.log`) e
> `/tmp/libreFolio_i_m30_unscaled.py` (log `_unscaled.log`). Il fattore vero lo ricavano dentro, dal blob di HEAD, e
> lo usano solo per confrontare: non è mai stampato. Escono solo sì/no, famiglie e conteggi; i log passano il controllo
> delle fughe. Le risposte sono nel §5.
>
> **⚠️ Fuori pista**: la via C, preparata nell'analisi, aveva due difetti, corretti prima di girarla.
> - La prova del «multiplo intero» era nel verso sbagliato: con gli originali in centesimi, l'unità ricostruita vale
>   il fattore per il MCD dei centesimi, quindi va divisa per il fattore, non il contrario.
> - Guardava solo gli `.amount`: ora prende ogni famiglia scalata, anche quelle a numero semplice, più la loro unione,
>   col migliore di 5 riferimenti presi fra i valori più piccoli.
> - Tre controlli sintetici lo provano: griglia dei centesimi → esatto; griglia di 5 unità → multiplo intero;
>   rumore ad alta precisione → no.
>
> **⚠️ Fuori pista**: **la via C dice sì, ed è esatta**. La pubblicazione, in sola lettura sui riferimenti remoti
> locali (ultimo fetch); il repository è pubblico:
> - la fixture di HEAD prima della cura, cioè la ricattura `c80508be8` del 7/10, è su `origin/dev` e
>   `origin/dev_release2`;
> - `origin/main` e il tag `v1.1.0` hanno la cattura precedente, quella di `3e33372c6` ritoccata in `16fb90c90`, con
>   un altro fattore. Lo stesso `_scale` la rende esposta alle stesse vie per costruzione, ma non l'ho misurata;
> - questo lotto non crea le vie A, B e C e non le chiude: gli importi non cambiano (Passo 4).
>
> La misura era il mandato: non ho cambiato nulla, e le proposte sono nel §5 per il developer.

### Passo 7 — I consumatori ✅ 2026-10-13

> **Note implementazione**: ricontrollati sulla base, cercando `dashboard-report` in tutto il repository (fuori da
> `node_modules`). Nel codice la fixture ha quattro lettori:
> - `frontend/e2e/gallery.spec.ts:754`, la galleria di M: non la lancio. M rifà gli scatti `allocation-*` e le
>   Posizioni con lo YoC; `price_change_1d` non lo legge nessun componente (§1.7);
> - `frontend/src/lib/api/dashboardReportFixture.test.ts:70`, il Vitest di guardia in `front-utility core-unit`:
>   verde (Passo 5);
> - lo script, `scripts/normalize_dashboard_fixture.py:328`, anche come `dev.py mkdocs normalize-dashboard-fixture`
>   (`dev.py:2607`): la prova a secco è verde (Passo 5);
> - il pytest nuovo, `test_normalize_dashboard_fixture.py:52` e `:449-450`, su una copia in `tmp_path`: 29/29 (Passo 5).
>
> Nessun'altra spec della suite normale e nessun componente dell'app la legge, quindi non c'è altro da far girare. Le
> altre occorrenze sono documentazione: il journal, la devWiki e le tre istruzioni condivise del §0. Dopo la cura
> queste dicono il vero: ogni cifra di denaro è scalata, e quantità, percentuali e id restano invariati.

### Passo 8 — Il backlog ✅ 2026-10-13

> **Note implementazione**: voce **54-1** nella sezione I di `BACKLOG_POST_1.2.md`, dopo la 49-1. Liquidità negativa
> in Tipo e Settore (`daily_state.py:715-717`), totale con segno (`derived_views.py:231-243`), lo stack di ECharts
> (`samesign`, `dataStack.js:103`, `:132`) e il taglio a `max: 100` (`AllocationHistoryChart.svelte:703`, `:802`),
> i filtri di tooltip, famiglie e torta. Righe ricontrollate sulla base. L'indice per fonte lo riconcilia il
> coordinatore: non l'ho toccato.

### Passo 9 — La pulizia dei log in /tmp ✅ 2026-10-13

> **Note implementazione**: tutto fuori dal repository. Stampati solo conteggi.
> - **Cancellati sul posto** (`/tmp/libreFolio_i_m30_redact.py`, log `_redact.log`): ogni token decimale diventa
>   `<redacted>`, mentre versioni, date e conteggi restano.
>   - `_fixture_scan.log`: 217 decimali, cioè le quote, gli importi e le somme per giorno della fixture di HEAD;
>   - `_v110_check.log`: 9, le somme della fixture del tag;
>   - `_yoc_check.log`: 2, i rapporti dello YoC;
>   - `_scaled_keys.log`: 18 esempi «e.g.»;
>   - `_green_dry.log`: 2, il patrimonio e il rapporto stampati dalla prova a secco. Sono l'obiettivo pubblico, non
>     cifre reali, ma li ho tolti lo stesso.
>   - `analysis.md`, il rapporto dell'analisi: 13 sostituzioni su 10 righe (approssimazioni, intervalli, una frazione).
>     Fra i numeri con la forma di una quota restano solo le somme della corsia di test, che sono dati sintetici, e un
>     conteggio di righe.
> - **Le copie della fixture**: 81 `dashboard-report.json` nelle 3 cartelle di base che pytest conserva, 27 per
>   ciascuna (log `_tmpclean.log`). Ho toccato solo le cartelle che portano il nome delle 11 funzioni del mio modulo:
>   la radice di pytest è condivisa con le altre corsie. Ho cancellato anche `_live_report.json`, il report della
>   corsia di test, che non è più usato. In `/tmp` non resta nessuna copia.
> - **Il controllo delle fughe** su tutto l'insieme, 36 file (ogni `/tmp/libreFolio_i_m30_*.log`, i `.txt` e
>   `analysis.md`): pulito (log `_leak_s9.log`).
>
> **⚠️ Fuori pista**: il controllo delle fughe trova solo le foglie della fixture copiate tali e quali. I numeri
> derivati, come somme e rapporti, gli sfuggono.
> - Per questo ho aggiunto `/tmp/libreFolio_i_m30_derivedscan.py`, che mostra con le cifre mascherate ogni decimale o
>   intero lungo dei log. Fuori dai file cancellati restano solo letterali sintetici dei test, conteggi, versioni,
>   durate e codici di uscita.
> - Il controllo rilanciato ha trovato due coincidenze in `analysis.md`: la citazione della docstring «0.04 means 4%»,
>   già contata come sintetica, e la versione «1.1» nel testo, che ora è scritta `v1.1.0`.
> - La prova a secco della pulizia contava 108 copie, ma il collegamento `pytest-current` puntava a una delle tre
>   cartelle e la contava due volte: le copie vere erano 81, tutte cancellate.

### Passo 10 — Checkpoint ✅ 2026-10-13

> **Note implementazione**: il pacchetto del §6 è pronto, fatto da `/tmp/libreFolio_i_m30_bundle.sh` (log
> `_bundle.log`), in sola lettura sul repository.
> - **Gli stadi**: 3 stadi su 7 percorsi, ognuno in un solo stadio. Il blob di ogni stadio è quello del worktree, e il
>   delta del worktree (i modificati più i nuovi) coincide coi 7 percorsi del manifest.
> - **I messaggi**: l'oggetto entro 50 caratteri, in forma Conventional Commits; la seconda riga vuota; solo ASCII,
>   righe entro 72, nessuno spazio in coda e nessun numero dei dati.
> - **I verdi sui blob finali**, rilanciati prima del pacchetto: pytest `utils normalize-dashboard-fixture` 29/29 e
>   Vitest `front-utility core-unit` 128 file, 4195/4195 (log `_final_pytest.log`, `_final_vitest.log`).
> - **La privacy**: la scansione di percorsi, email e chiavi sulle righe aggiunte, sui file nuovi e sui messaggi non
>   trova niente. Il controllo delle fughe su messaggi, manifest e prove è pulito (`_leak_bundle.log`), e così
>   `proseclass` sul piano e sulle righe nuove del backlog.
> - **Il target** `a3e3298df` (treno 98) è 8 commit avanti, con HEAD come base comune. Dei 7 percorsi cambia solo il
>   backlog, in un'altra sezione: la fusione a tre vie, simulata in /tmp con `git merge-file`, è pulita.
>   `frontend/e2e/gallery.spec.ts` cambia nel target, ma nessuna riga tocca la fixture o l'allocazione.
> - **Lo stato finale**: `git diff --check` pulito, niente in stage, porta 6157 libera.
>
> **⚠️ Fuori pista**: alla prima corsa il controllo delle fughe ha segnalato il mio helper `proseclass.py`: l'insieme
> dei nomi di rilascio, scritto con letterali decimali, coincideva con due foglie della fixture. Erano nomi, non dati;
> l'ho riscritto senza letterali decimali, e la seconda corsa è pulita.

## 4. Selettori, prove e definizione di fatto

> Corsia 6157 (`--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`), un comando alla volta, col prefisso
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; per il Vitest anche
> `LIBREFOLIO_TEST_STARTUP_TIMEOUT=900` e `--workers 1`. I log sono `/tmp/libreFolio_i_m30_<nome>.log`, copiati nel
> pacchetto del §6.

| Controllo | Esito | Log |
|---|---|---|
| pytest `utils normalize-dashboard-fixture` | 12/29 rossi → 28/29 dopo lo script (rosso solo il test della fixture committata, per disegno) → **29/29** | `red_pytest`, `s3_pytest`, `green_pytest`, `final_pytest` |
| Vitest `front-utility core-unit` | 3 rossi su 4195 → **128 file, 4195/4195** | `red_vitest`, `green_vitest`, `final_vitest` |
| `dev.py mkdocs normalize-dashboard-fixture --dry-run`: lo script curato sulla fixture curata | 0 ❌, fixture invariata | `green_dry` |
| lo script curato su una copia in /tmp della fixture di HEAD | exit 1, 8 ❌ | `head_refusal` |
| lo script di HEAD, a secco, sulla fixture curata (lo stadio C1 del §6) | exit 0, 0 ❌, fixture invariata | `stage_c1_headscript` |
| ruff e black sui 3 file Python, prettier sul Vitest | puliti | `lint_s10` |
| il controllo delle fughe e la scansione dei derivati, su log e helper | puliti | `leak_s9`, `leak_s10`, `derivedscan_s10`, `leak_bundle` |
| i decimali di questo piano uguali a una foglia della fixture | tutti strutturali, 0 non classificati | `proseclass` |

- **Prettier e la fixture**: `prettier --check` segnala `frontend/e2e/dashboard-report.json`, ma è preesistente. La
  fixture di HEAD dà lo stesso scarto (24 righe), il file è fuori da `npm run format` (che prende `src/**` ed
  `e2e/**/*.ts`) e lo script la scrive con `json.dumps(…, indent=2)`, come prima.
- **I gemelli del piano**: la fixture curata ha oltre 16 mila quote a due decimali, quindi quasi ogni decimale corto vi
  trova un gemello. Nel piano sono solo numeri di sezione (nei titoli e nei rimandi), nomi di rilascio, il letterale
  `Decimal` del §1.4 e l'esempio della docstring dello YoC, citato due volte.
  `/tmp/libreFolio_i_m30_proseclass.py` li classifica e fallisce su ogni altro token, che mostrerebbe con le cifre
  mascherate.
- **Non girati**: la galleria (di M); altre spec della suite normale, perché nessuna legge la fixture (Passo 7); le
  suite lunghe, perché R è sulla 6176.

**Definizione di fatto**

- [x] Le quattro famiglie non si scalano mai, e gli invarianti falliscono forte: la famiglia e un conteggio, mai un
  valore (Passo 3).
- [x] Nella fixture cambiano solo le righe derivate, e gli importi restano quelli catturati (Passo 4).
- [x] I rossi prima dei verdi, via test-author (Passi 2 e 5).
- [x] La privacy misurata (§5) e i log puliti (Passo 9, §6).
- [x] La voce 54-1 nel backlog (Passo 8).
- [x] Niente riga nel CHANGELOG, e le istruzioni condivise dicono ancora il vero (Passo 7).
- [x] Ogni stadio verde da solo; `git diff --check` pulito, niente in stage, porta 6157 libera (§6, Passo 10).

## 5. La privacy: il fattore si ricava ancora? (misura, nessun numero)

> Misurata sulla fixture curata al Passo 6 (log `privacy`, `unscaled`, `yoc_status`): solo sì o no, il campo e dei
> conteggi, come chiede il mandato.

| Via | Risposta | Il campo, o il perché |
|---|---|---|
| S, le quote | **no**, curata | `summary.allocation_by_*[*].value`, `allocation_history.*[*].components[*].value`: ogni lista somma a 100 |
| Y, lo YoC | **no**, curata | `summary.holdings[*].yield_on_cost.value`: i 2 `available` valgono lordo/WAC; i 4 `no_income` valgono zero e i 4 `unavailable` sono `null`, quindi la scala non li toccava |
| G, la variazione di un giorno | **no**, curata | `summary.holdings[*].price_change_1d`: 8 su 8 sulla griglia a 4 decimali e coerenti con `gain_loss_change_1d_percent` |
| D, una coppia scalato e non scalato dentro la fixture | **no** | 41 famiglie numeriche non scalate su 120 (quote, frazioni, tassi, conteggi, id, `quantity`). Ogni relazione con un campo scalato è omogenea: percentuali e quote sono rapporti di importi scalati, e `quantity × current_price = current_value` vale col fattore e senza. Nessun decimale nei testi |
| A, le quotazioni pubbliche | **sì**, per costruzione | `summary.holdings[*].current_price`, `wac_per_unit`, `valuation_*_unit_price`, contro la quotazione pubblica del giorno `metadata.computed_date_to`; 7 posizioni su 10 hanno un ticker |
| B, la quantità non scalata | **sì**, per costruzione | `summary.holdings[*].quantity` per la quotazione pubblica, contro `current_value` |
| C, la precisione, senza dati esterni | **sì, esatta** | `_scale` moltiplica a 28 cifre senza arrotondare: un importo nato sui centesimi ci torna, diviso per il fattore. Le famiglie esatte sono sotto; molte altre lo sono a meno di un multiplo intero dell'unità della griglia |
| E, l'output dello script | **sì**, solo in locale | `scripts/normalize_dashboard_fixture.py:316` (sotto) |
| F, la storia e gli scatti | **sì** | i blob di prima della cura, pubblici (Passo 6); gli scatti sul sito e nelle immagini del rilascio (sotto) |

- **Le famiglie esatte della via C**: `broker_pnl_history[*].points[*].total_pnl`, `cost_history.points[*].cost`,
  `deposit_history.points[*].deposit`; `history[*]`: `capital_baseline`, `cash_value`;
  `positions_contribution.positions[*]`: `period_fees_taxes`, `period_pnl`, `period_realized_gain_loss`,
  `period_unrealized_delta`, `start_value`; `summary.allocation_by_type[*].amount`; `summary.by_broker[*]`:
  `gain_loss`, `net_worth`; `summary.holdings[*]`: `current_price`, `gain_loss`, `gain_loss_change_1d`,
  `valuation_effective_unit_price`, `valuation_reference_unit_price`.
- **La via E, riga per riga**:
  - `:316` stampa `net_worth: {current} → {TARGET} (ratio …); scaled N fields`. Su una cattura grezza mostra il
    patrimonio vero e il fattore, nel terminale di chi normalizza.
  - `:172`, `:180` e `:182` c'erano già in HEAD (`:142`, `:150`, `:152`). Le ultime due stampano il rapporto
    `value / (quantity × price)`, che con la scala non cambia. La prima stampa il patrimonio dopo la scala, cioè
    l'obiettivo; sarebbe quello grezzo solo se fallisse la scala del patrimonio stesso, e sempre in locale.
  - `:158` porta solo il nome dell'asset. Le righe nuove (`:240`, `:243`, `:269`, `:271`, `:293`) portano la famiglia
    e un conteggio.
- **La via F, la pubblicazione** (riferimenti remoti locali, ultimo fetch; il repository è pubblico):
  - la fixture di prima della cura è su `origin/dev` e `origin/dev_release2`; `origin/main` e `v1.1.0` hanno la
    cattura precedente, con un altro fattore (Passo 6);
  - gli scatti non sono nel repository (`.gitignore:79`). `release.yml` li genera (`:223`, `mkdocs gallery`), le
    immagini del rilascio li includono (`:218-219`) e il sito li pubblica (`mkdocs deploy`, `:389-391`), solo da main
    o da un rilascio stabile;
  - `origin/gh-pages` (punta `8704c1f46`, 2026-09-07) ha 48 `allocation-*history*.png`, quindi da una cattura
    precedente alla ricattura del 7/10. La cima dello stack vi dà una stima a occhio del fattore di quella cattura.
- **La fixture curata non aggiunge niente**: le quote e lo YoC veri si ricavano già dagli importi scalati, perché il
  fattore si semplifica, e `price_change_1d` da `gain_loss_change_1d_percent`, che non è scalato. Prima della cura,
  invece, erano proprio le somme delle quote a mostrare il fattore: a occhio negli scatti, per somma nel file.
- **Le proposte, che decide il developer**:
  - **C**: arrotondare ai centesimi gli importi scalati. Toglie l'esattezza, non la stima.
  - **A e B**: la cattura di un portafoglio sintetico chiude tutte le vie. Scalare le quantità invece dei prezzi
    chiude A e B, ma la C resta, anche sulle quantità, se non si arrotondano.
  - **E**: stampare solo il numero dei campi scalati e l'obiettivo.
  - **F**: la riscrittura della storia, già una domanda per il developer.

## 6. Il checkpoint: tre stadi e il pacchetto

> Il pacchetto è nello stato di sessione, in `files/fixtureshares_commit_bundle/`: `MANIFEST.txt`, i 3 messaggi in
> `messages/`, le cartelle `stage_C1` … `stage_C3` (i file di ogni stadio più `BLOBS.txt`) ed `evidence/` (i log e gli
> helper `/tmp/libreFolio_i_m30_*`). Ogni file passa per un solo stadio, quindi il blob di ogni stadio è quello del
> worktree e non servono istantanee.

| Stadio | Oggetto | File | Perché è verde da solo |
|---|---|---|---|
| C1 | `fix(gallery): recompute fixture shares and yields` | `frontend/e2e/dashboard-report.json`, `frontend/src/lib/api/dashboardReportFixture.test.ts` | il Vitest passa sulla fixture curata; lo script di HEAD, a secco, la accetta e non la riscrive |
| C2 | `fix(gallery): never scale fixture shares` | `scripts/normalize_dashboard_fixture.py`, `backend/test_scripts/test_utilities/test_normalize_dashboard_fixture.py` (nuovo), `scripts/test_runner/_backend_utils.py` | pytest 29/29 |
| C3 | `docs(journal): plan 54, gallery fixture shares` | questo piano (nuovo), `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | solo journal |

- **L'ordine**: la fixture prima dello script. Al contrario, fra i due stadi lo script curato rifiuterebbe la fixture
  di HEAD (8 ❌), e il suo pytest sarebbe rosso.
- **Dopo il checkpoint**: M rifà gli scatti `allocation-*` e le Posizioni con lo YoC. Nessuna riga nel CHANGELOG.
- **Le proposte per la wiki**, da girare a W, che ne è l'unico scrittore:
  1. in `LibreFolio_devWiki/wiki/concepts/ci-release-pipeline.md` («Gallery fixture for the dashboard shots»,
     `:128-133`), un punto: le eccezioni per percorso e gli invarianti dello script, e lo stack della galleria che
     non arrivava in cima;
  2. una pagina problema: la scala per nome della chiave ha preso quote, YoC e `price_change_1d`; una scala uniforme
     a piena precisione lascia rapporti esatti (via C), quindi la cura vera è arrotondare o catturare un portafoglio
     sintetico; un controllo delle fughe sulle foglie letterali non vede i numeri derivati, e dopo la cura i decimali
     corti coincidono con le quote, quindi conviene mascherare. Nella decisione
     `wiki/decisions/gallery-is-a-release-gate-with-real-data.md` un rimando alla pagina;
  3. una voce nel log.
