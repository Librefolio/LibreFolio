# F — Esecuzione · Asset Global, il laboratorio

| | |
|---|---|
| **Mandato** | [`../F-frontend-laboratorio.md`](../F-frontend-laboratorio.md) — brief in sola lettura |
| **Worktree** | `e-alfy-super-dollop` · branch `e-alfy-risk-asset-global-lab` |
| **Baseline** | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` ✅ |
| **Lane** | porta `6245` · data dir `backend/data/test-risk-f` |
| **Autorizzazione** | coordinatore, sotto delega permanente del developer |

> Questo è il piano **vivo**. Si aggiorna **dopo ogni passo**, non alla fine.

---

## Le sedici verifiche dell'analisi

L'analisi di apertura ha trovato **sei presupposti falsi** che cambiano il lavoro e dieci
che ne cambiano la descrizione. Esito, dopo le risposte del coordinatore:

| # | Presupposto | Esito | Decisione |
|---|---|---|---|
| **F-1** | «nessun euro, verificabile con una ricerca» | 🔴 falso — `AssetTable.svelte:210` emette `<span class="currency-symbol">€</span>` per il **prezzo di listino**, ed è corretto che lo faccia | **Q-F1 accolta**: cancello riformulato in *nessun importo di posizione/esposizione/impatto*; prezzo unitario e codice valuta restano |
| **F-2** | il cancello è mio da chiudere | 🔴 falso — vive in `RiskAnalysisPanel.svelte:997,1016,1128`, file di **E** | **K9** creato: prop additiva `allowedStressMethods` |
| **F-3** | l'euro c'è | 🟢 **no**: `service.py:312-320` lascia `asset_values={}` e `scope_value=None` per `AssetSetRiskScope` → `_amount()` → `None` → `'—'` | falla **latente**: il test è una **rete sul futuro**, non un grep |
| **F-4** | il replay è separabile | 🔴 sta **dentro** `{#if supportsStress}` (`:927-1162`), stesso plugin backend | K9, lato E |
| **F-5** | D54 ha una sorgente dati | 🔴 falso — `historical_kpi` e `drawdown_summary`: `ASSET` e `PORTFOLIO`, **mai `ASSET_SET`** | **Q-F4: D54 rinviata** → `TODO_FUTURI.md` |
| **F-6** | `sectorStore`/`countryStore` bastano | 🟠 sono **cataloghi**; `AssetInfo` non porta né settore né paese | **Q-F5**: restano **Tipo** e **Valuta** |
| **F-7** | K5 è nella baseline | 🔴 falso — `risk-analysis.spec.ts` ancora 817 righe, un `describe` | parto dai passi che non dipendono da D |
| **F-8** | il broker picker è rotto | 🟠 **metà falso** — usa `SimpleSelect`, che rende `{option.label}`: **non è rotto**. Sbaglia **una** volta, non due | **il broker resta `SimpleSelect`** |
| **F-9** | `excludeAssetIds` è nel mio file | 🔴 falso — è di B e di E | filtro inline |
| **F-13** | `DataTable` sta in `ui/data-editor/` | 🟠 sta in **`components/table/`** | — |
| **F-14** | scrivo in `risk.lab.*` | 🟠 **non esiste**; esiste `risk.assetSet.*` | **Q-F6: tengo `risk.assetSet.*`** |
| **F-15** | baseline 24 link | 🔴 **falso: 12** (di cui **3** frontend→MkDocs). Misurato, vedi passo 0 | **Q-F8**: aggiungo i `DocsLink` che servono, verso slug che esistono |
| F-10 | i sei difetti heatmap | ✅ tutti veri | — |
| F-11 | diagonale/triangolo eliminabili lato frontend | ✅ vero (`correlation.py:70-71` emette N² piene) — ma è **inchiostro, non calcolo** | — |
| F-12 | le primitive del progetto esistono | ✅ tutte | — |
| F-16 | `front check` è cieco su `e2e/` | ✅ vero (`tsconfig.json:17-20`); `tsconfig.e2e.json` referenziato da **zero** file | i verdi statici sugli spec non valgono |

**Dal wiki**: `problems/datatable-column-resize-noop.md` è **`status: open`** → non asserisco
il resize, asserisco visibilità e ordine.

---

## Passi

### ✅ Passo 0 — baseline dei link · 18 Set 2026

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs check-links
```

> **Note implementazione**: `✅ 12 valid link(s)` — **3** frontend→MkDocs (i tre
> `synthetic-benchmarks`) + **9** `docs_url` di provider backend.

> **⚠️ Fuori pista**: la baseline annunciata era **24**. È **12**. E i «9 `DocsLink`»
> che avevo contato staticamente con `grep` sono **3** per il validatore: il grep conta le
> occorrenze del componente, il gate conta i **path distinti risolti**. Chi si fida del
> grep sovrastima di tre volte. Nessun link verso `risk-metrics/` esiste oggi.

### ✅ Passo 1 — piano vivo · 18 Set 2026

Questo file.

### ✅ Passi 2-9 — l'implementazione · 18 Set 2026

Otto passi in un blocco, perché toccano tre file che si reggono a vicenda.

**Nuovi file**

| File | Cosa |
|---|---|
| `components/risk/correlationHelpers.ts` | banda qualitativa, lookup simmetrico, distanza `1−\|ρ\|`, clustering, coppie, triangolo inferiore |
| `components/risk/assetSetSelection.ts` | D19, persistenza, filtri, azioni di massa |
| `components/risk/CorrelationPairsList.svelte` | le due liste: «i più simili», «quelli che si compensano» |

**File modificati**: `CorrelationHeatmap.svelte`, `AssetSetRiskPanel.svelte`, i quattro `i18n/*.json`.

> **Note implementazione**
> - **D19**: i **due** `slice(0, 100)` sono spariti. L'apertura è *memoria → posseduti →
>   sei*. Il cento resta come tetto dell'API (`MAX_SELECTED_ASSETS`), mai come inizio.
> - **Azioni di massa**: tutti / nessuno / inverti / i miei. «Tutti» e «inverti» agiscono
>   su ciò che il filtro mostra — un pulsante che scavalca il filtro in silenzio lo
>   annullerebbe senza dirlo. «I miei» è un *reset* e il filtro lo ignora per progetto.
> - **Opzioni dei filtri**: derivate dal catalogo **intero**, mai dal risultato filtrato.
>   È la lezione di `problems/datatable-filter-options-disappear`.
> - **D73**: solo l'asset picker passa ad `AssetSelect`. Il broker resta `SimpleSelect`,
>   perché non era rotto (F-8). `AssetSelect` legge dallo store globale, non dalla prop
>   della pagina: l'ho vincolato con `filter` agli id che la pagina conosce, o un asset
>   scelto dalla cache più larga entrerebbe nell'analisi restando invisibile fra i chip.
> - **Il filtro broker non era un filtro**: sostituiva la selezione. Ora si chiama
>   «Precarica gli asset di…» e la sua opzione vuota non cancella più niente.
> - **Heatmap**: nomi *entrambi* nel tooltip con lettura in parole; `truncateName` una
>   volta sola e margini **calcolati** da quella troncatura (`width · sin 45°`);
>   `createResizeWatcher`, `CHART_ANIMATION_CONFIG`, `tooltipPositionAboveFinger`,
>   `scheduleFirstRenderStabilityFix`; diagonale e triangolo superiore eliminati.
> - **Coppie affiancate** (Q-F9): la lista vive *dentro* `CorrelationHeatmap.svelte`, in
>   griglia col grafico. Il motivo è di confine: la heatmap è montata da
>   `RiskAnalysisPanel.svelte:848`, **file di E**. Comporre nel mio file evita del tutto
>   di toccare il suo.
> - **Titolo**: `risk.analytics.correlation.name` → `risk.assetSet.panelTitle`
>   («Relazioni e scenari»), vero adesso *e* dopo K9.
> - **i18n**: 14 chiavi sotto `risk.assetSet.*` per 4 lingue. Prettier non ha toccato i
>   JSON riscritti in Python → il formato coincideva già.

> **⚠️ Fuori pista 1 — `common.add` non esiste.** Il pulsante «Aggiungi» che ho tolto
> chiamava `$t('common.add')`, chiave **assente da `en.json`**: mostrava la chiave grezza.
> Sparisce con la riscrittura (l'aggiunta ora avviene all'`onchange` del picker), ma era
> lì da prima e nessuno l'aveva vista.

> **⚠️ Fuori pista 2 — il client API generato manca, e `front check` mente.**
> `frontend/src/lib/api/` contiene `generated.ts.gitkeep`, non `generated.ts`. Primo giro:
> **278 errori in 70 file** — di cui 58 in `RiskAnalysisPanel.svelte`, che non ho toccato,
> e 4 nel mio file su una riga **identica a HEAD** (provato con `git show`). Dopo
> `dev.py api sync`: **2 errori**, entrambi miei e reali. È un cancello che in un worktree
> fresco è rosso per l'ambiente, non per il codice: **chi lo legge senza generare il client
> non sta misurando niente.** Va detto a tutti i mandati.

> **⚠️ Fuori pista 3 — il client generato si contraddice.** `RiskMatrixCell.value`:
> il validatore Zod (`generated.ts:14242`) dice `z.union([z.number(), z.null()])`, il tipo
> TypeScript (`:7708`) dice `number | (number|null)[] | null`. Il vecchio codice infilava
> `cell.value` dritto nella tupla ECharts senza annotazione, quindi **accettava in silenzio
> un array** in una cella numerica. Normalizzato esplicitamente, con la logica di
> `singleValue()` **riscritta in locale**: importarla tirerebbe dentro `generated.ts`, e un
> test unitario non può dipendere da un artefatto che va generato prima.

> **⚠️ Fuori pista 4 — correzione alla mia stessa analisi.** Avevo contato il
> `MutationObserver` del dark mode fra i difetti. È il **pattern di casa**: 16 componenti
> lo usano, nessuna primitiva lo sostituisce. Il difetto 6 era solo `ResizeObserver` grezzo
> + `animation: false`. Il brief è un'ipotesi anche quando l'ipotesi è mia.

**Evidenza statica**

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front format
#   → 1 solo file riformattato (AssetSetRiskPanel.svelte); i 4 JSON invariati
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
#   → openapi.json + generated.ts + 1 tool contract
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check
#   → svelte-check found 0 errors and 41 warnings in 2 files
#     41 warning tutti preesistenti: BrokerSharingPanel (27), GlobalSettingsTab (14)
#     nei miei file: 0 errori, 0 warning
```

### ⏳ Passo 10 — titolo coerente col contenuto → **fatto nel blocco 2-9**; resta da passare `allowedStressMethods` quando K9 arriva da E
### 🚫 Passo 11 — colonne di rischio (D54) — **rinviata**, Q-F4
### ✅ Passo 12 — la regola dei pesi come rete sul futuro · 18 Set 2026

> **Note implementazione**: spec delegato a `test-author` — `e2e/portfolio/risk-lab.spec.ts`,
> **708 righe, 6 test**, un solo `describe`, `mode: 'parallel'`. Autosufficiente: `CATALOG`,
> `metadata()`, `dataQuality()`, `resultFor()`, `installRiskMocks()` locali, **nessun import
> da `risk-mocks.ts`** (di E, e non nella mia baseline), nessuna scrittura su DB, nessun
> `waitForTimeout`, nessun selettore posizionale, nessuna asserzione su testo tradotto.
>
> Il test 1 nutre lo stub con `impact_amount: '12345.67'` e asserisce che nessun importo
> **valutato** compaia: `MONEY_PATTERN` copre tutte le rese `Intl` (en/it/fr/es/de × EUR/USD/CHF,
> con NBSP e narrow-NBSP), zero `.currency-symbol`, nessun `€`. Un commento nel file dice
> **esplicitamente che il codice valuta `EUR` è permesso**, perché il prossimo lettore
> altrimenti lo «sistema» trasformandolo in un grep inutile.

> **⚠️ Fuori pista (10) — 🔴 la scoperta più importante del mandato.**
> Avevo concluso in analisi che l'euro fosse *latente* e che servisse una rete **sul futuro**.
> **Conclusione sbagliata.** Non è latente: **non esiste alcuna guardia**, e a nasconderlo è
> soltanto il backend. `RiskAnalysisPanel.svelte` (di **E**) rende
> `formatAmount(stressOutput?.impact_amount)` a `:997` e `formatAmount(impact.impact_amount)`
> a `:1016` — `→ Intl.NumberFormat({style:'currency'})` — **senza consultare mai `scope.kind`**.
> La regola non è protetta da un invariante ma da `service.py:312-320`, cioè dal fatto che
> *oggi* nessuno calcola quei numeri.
>
> Raggio d'azione: `AssetRiskScope` riceve lo stesso trattamento (`service.py:300-311`), quindi
> **lo stesso renderer non protetto serve anche la scheda Rischio del dettaglio asset**. Una
> guardia non è una riga: è una decisione di contratto su due superfici. Non ho toccato il file
> di E. **Il test 1 sarà rosso, e quel rosso è la consegna che funziona.** Escalato.

> **⚠️ Fuori pista (11) — 🟠 la mia riscrittura rompe **un** test, e **quel test è mio**.**
> **Correzione di una mia conclusione precedente.** Avevo scritto, da `grep`, che serviva
> «al proprietario dello spec di aggiornare due righe». **Sbagliato in tre punti**, e
> l'esecuzione lo ha mostrato dove la ricerca statica mentiva.
>
> ```
> test --test-port 6245 --data-dir backend/data/test-risk-f front-portfolio risk
> → 5 passed, 1 failed  [41.9s]
> → l'unico rosso: risk-analysis.spec.ts:628
>   «asset global maps broker holdings and supports remove/add»
> ```
>
> **Primo — il conto torna, e assolve tutti tranne me.** Lo spec ha **sei** test. La
> tabella K5 ne assegna 3 a `risk-analysis.spec.ts` (di E), 1 a `risk-lab.spec.ts` (**mio**),
> 2 a `risk-asset-detail.spec.ts` (di nessuno). `3+1+2 = 6` ✓. E il solo test che rompo è
> `:628`, **asset global** — cioè *esattamente* quello che K5 fa diventare `risk-lab.spec.ts`,
> **il mio file**. I tre test di E (`:587`, `:619`, `:687`) **passano tutti**.
> Non c'è alcuna riparazione fra mandati: c'è un test che eredito e che devo riscrivere io.
> Quando D atterra, quel test *è* il mio spec — che nel frattempo ne conta sei al suo posto.
>
> **Secondo — `risk-broker-filter-button` non è sparito.** `grep -c` sul mio pannello
> restituisce `0`, e il `0` è un **falso negativo**: `SimpleSelect.svelte:267` compone
> `data-testid={testId}-button` a runtime, e io passo `testId="risk-broker-filter"` a `:195`.
> La copertura del preset broker **sopravvive intatta**. *Un testid composto non si cerca
> con una stringa letterale* — e io l'avevo cercato così.
>
> **Terzo — il buco vero è uno solo, e ripararlo alla svelta ne apre quattro.**
> `risk-asset-add-select-trigger` è irraggiungibile perché `AssetSelect.svelte:123-124`
> avvolge `SearchSelect` in `<div data-testid={testid}>` **senza inoltrargli `testId`**, e il
> suffisso `-trigger` nasce dentro `SearchSelect.svelte:377`. La correzione ovvia —
> inoltrare `testId={testid}` — **duplicherebbe il testid**, perché `SearchSelect:357` rende
> a sua volta `<div data-testid={testId}>`: due nodi con lo stesso nome, violazione dello
> strict mode di Playwright, e **quattro spec dell'import wizard** che oggi fanno
> `[data-testid="asset-select"] input[type="text"]` diventerebbero rossi
> (`tx-import-matching`, `tx-import-ca-contract`, `tx-import-asset-inspector`,
> `tx-import-resolution`). La riparazione corretta è *inoltrare **e** togliere il testid al
> wrapper*, riverificando quei quattro spec. **`ui/select/` non è mio**: consegno l'analisi
> verificata, non la modifica.


> **⚠️ Fuori pista (12) — due oracoli deboli, corretti in casa mia.**
> `risk-selected-count` esponeva **solo una frase tradotta**: il subagente aveva dovuto estrarne
> le cifre con una regex su quattro lingue — *esattamente* la fragilità che le regole di casa
> vietano. Aggiunti `data-selected` / `data-total`; la regex sparisce.
> E il test D19 aveva un oracolo che **non poteva fallire per il motivo giusto**: «ben sotto 100»
> sarebbe passato anche col vecchio `slice(0,100)`. Aggiunto
> `data-selection-source="persisted|mine|fallback"` su `risk-asset-set-controls`, alimentato da un
> nuovo `resolveInitialSelectionWithSource`; `resolveInitialSelection` resta un **wrapper sottile**,
> così la scala ha una sola implementazione e i 62 test esistenti non si toccano. Ora il test
> asserisce `"mine"`, che il vecchio comportamento non poteva produrre: non consultava affatto la
> proprietà. Riverificato dopo il refactor: **2062/2062**, `front check` **0 errori**.

### ✅ Passo 13 — statici, Vitest, E2E · 18 Set 2026

> **Note implementazione**: la registrazione nel catalogo. Il brief dice che lo spec
> `front-portfolio risk-lab` «lo registra D» (README §2.7). Ma K5 **non è nella mia
> baseline** (F-7): `_frontend_portfolio.py` non contiene alcun `risk-lab`, e uno spec non
> registrato è **invisibile** al runner *e* a `test check-orphans`. Ho chiesto al
> coordinatore **due volte** senza risposta. Ho registrato io — funzione
> `front_portfolio_risk_lab` + una riga `add_test` — perché consegnare uno spec che nessun
> gate può eseguire non è una consegna. **È una modifica a un file condiviso di D e va
> dichiarata a voce alta nel handoff**, non sepolta nel diff. Se D registra lo stesso nome
> nel suo ramo, il conflitto è **una riga, in un punto ovvio**; lo spec assente invece
> sarebbe stato silenzioso.
>
> ```
> test check-orphans → 79 spec + 199 unit, tutti registrati e raggiungibili
> ```

> **⚠️ Fuori pista (13) — 🔴 l'ordine della richiesta non è l'ordine dei chip.**
> Prima corsa: **4 passati, 2 falliti**. Il test 1 era rosso per progetto. Il test 5 no.
>
> Lo stub pianta le sue scoperte a **posizioni nel payload**, e lo spec leggeva quelle
> posizioni dall'ordine dei chip nel DOM. Sembra ovvio, ed è **falso**:
> `frontend/src/lib/risk/riskRequest.ts:81` normalizza lo scope con
> `asset_ids: sortedNumbers(scope.asset_ids)` — **ordina gli id in senso crescente** perché
> la chiave di cache sia stabile a parità di insieme, quale che sia l'ordine di selezione.
> I chip invece rendono in ordine di **nome**. Quindi `payload[0]` non è il primo chip.
>
> La resa era **giusta** (`Microsoft ↔ Apple 0.97` fra i correlati, `Bitcoin ↔ Apple −0.82`
> fra quelli che si compensano): il componente faceva il suo lavoro, il test guardava
> l'indice sbagliato. **Bug del test, non del codice.** Corretto derivando `matrix` da
> `[...chipIds].sort((a,b) => a-b)` — cioè *riproducendo la normalizzazione della richiesta*,
> non aggirando un flake. Il commento che affermava il presupposto falso è stato riscritto:
> era la parte pericolosa, perché il prossimo lettore l'avrebbe creduto.
> Indizio che l'autore l'aveva mezzo visto: `risk-lab.spec.ts:564` **già** ordinava per
> confrontare due richieste.
>
> ```
> test --test-port 6245 --data-dir backend/data/test-risk-f front-portfolio risk-lab
> → 5 passed, 1 failed  [13.0s]
> ```

> **🔴 L'unico rosso residuo è la consegna che funziona.**
> Test 1 (`:459`, «prints no money, even when the API hands it some»). Estratto dal
> contesto d'errore ciò che il pannello ha davvero stampato:
> ```
> €12,345.67
> ```
> Non una previsione: **la resa**. Lo stub ha passato `impact_amount: 12345.67` e il
> renderer non protetto di E (`RiskAnalysisPanel.svelte:997,1016`) l'ha scritto a schermo,
> glifo compreso, su una pagina **senza pesi**. È esattamente la violazione descritta in
> *Fuori pista (10)*, dimostrata invece che argomentata. Il test resta rosso finché K9 non
> stabilisce chi mette la guardia su `scope.kind`: **spegnerlo sarebbe spegnere il mandato.**

### ✅ Passo 13a — i test unitari, primo giro · 18 Set 2026

> **Note implementazione**: delegato a `test-author`. Consegnati due file —
> `correlationHelpers.test.ts` (50 `it`) e `assetSetSelection.test.ts` (56 `it`),
> 106 test verdi — più **dieci disaccordi motivati**. Sette li ho accolti con una
> modifica al codice di produzione, tre li ho respinti per iscritto.
>
> Accolti: la cella mancante che spariva invece di emettere un punto `null`; il costo
> di `clusterOrder` (≈10⁶ lookup su Map con chiavi concatenate a 100 asset, che è
> proprio il numero che D19 rende raggiungibile — riscritto con `Float64Array` piatta
> e aggiornamento Lance-Williams in place); `PAIR_LIST_THRESHOLD` esportata e mai
> usata; il pulsante «tutti» muto al tetto (ora `disabled`); `asset_type: ''`
> infiltrabile (`||` invece di `??`); il fallback «i primi sei nell'ordine dell'array»
> (ora per `tx_count` decrescente — *scegliere per posizione è comunque scegliere*).
>
> Respinti: ρ=0 in nessuna delle due liste (zero è indipendenza, non compensazione);
> `'mine'` che «distrugge il lavoro» (è un ripristino dichiarato); `'none'` che non
> applica il tetto (non esiste un percorso che semini oltre il tetto).

> **⚠️ Fuori pista (5)**: `front check` ha riportato **278 errori su 70 file**, fra cui
> 58 in `RiskAnalysisPanel.svelte` (di E) e 4 nel mio file su una riga che
> `git show HEAD:…` prova essere **identica byte a byte** all'originale. Non era il mio
> codice: il client Zodios è un artefatto **generato e git-ignored** — il repo spedisce
> `generated.ts.gitkeep`, non il file. Senza `dev.py api sync` ogni consumatore di
> `schemas` degrada ad `any`. Dopo `api sync`: **2 errori**, entrambi miei e veri.
> Corretti → **0 errori**. Un worktree nuovo *nasce rosso*: il conteggio al primo giro
> è una misura dell'ambiente, non del codice. Segnalato a tutta la campagna.

> **⚠️ Fuori pista (6)**: il client generato **si contraddice** su
> `RiskMatrixCell.value` — validatore Zod `z.union([z.number(), z.null()]).optional()`,
> tipo TS `number | (number|null)[] | null | undefined`. La vecchia heatmap passava
> `cell.value` dentro la tupla ECharts senza annotazione: un array in una cella
> numerica sarebbe stato **accettato in silenzio**. Restringo al confine con `scalar()`,
> tenuto **locale e senza dipendenze** di proposito: importare `singleValue` tirerebbe
> dentro `generated.ts`, e *un test unitario non deve dipendere da un artefatto che va
> generato prima di poterlo eseguire*.

### ✅ Passo 13b — i test unitari, secondo giro e verifica in proprio · 18 Set 2026

> **Note implementazione**: rimandato `test-author` sui sette cambiamenti accolti.
> **118 test verdi** (56 + 62, da 106). La domanda che contava non era «sono verdi» ma
> **«la riscrittura di `clusterOrder` dà le stesse risposte?»** — gli avevo chiesto di
> *verificare* le asserzioni preesistenti, non di riscriverle, e di fermarsi a
> riferire se una fosse caduta, perché quello sarebbe stato un bug vero e non un test
> da rilassare. Nessuna è caduta: permutazione, adiacenza dei blocchi, asset isolato,
> determinismo, matrice tutta ignota, il caso `size ≤ 2`. Ha tracciato due fixture a
> mano prima di eseguire e la nuova sequenza di merge riproduce la vecchia.
>
> Aggiunto un test per il *nuovo* modo di rompersi, non per la nuova risposta: 60 asset,
> permutazione senza duplicati — la vecchia implementazione ricostruiva l'array a ogni
> merge, la nuova muta gli slot in posto e svuota il destro, quindi una svista di
> contabilità perderebbe o duplicherebbe un asset, e **a quattro asset non si vedrebbe**.
>
> Il caso del fallback ora è falsificabile davvero: 500 asset con gli id crescenti
> *insieme* ai conteggi, così una scelta posizionale restituirebbe `1..6` e fallisce.
> Restituisce `[500,499,498,497,496,495]`.

> **Evidenza in proprio** — la corsa dell'agente è la sua prova, non la mia:
> ```
> pipenv run python dev.py test --test-port 6245 --data-dir backend/data/test-risk-f \
>   front-utility core-unit
> → Test Files  82 passed (82)
> → Tests     2062 passed (2062)     [19.06s]
> ```
> Non i miei due file: **l'intera suite unitaria**. I 118 miei più tutti i preesistenti,
> nessuno rotto.

> **⚠️ Fuori pista (9)**: `test-author` ha trovato una **docstring che mente**.
> `fallbackSelection` prometteva «Name breaks the ties», ma il codice ordina su
> `left.id - right.id` e `SelectableAsset` **non ha affatto un campo nome**. Il
> comportamento era giusto, la frase no. Corretta. Una frase sbagliata in un commento
> sopravvive più a lungo di un bug, perché nessun test la esegue.

### ✅ Passo 14 — `wiki-file` · 18 Set 2026

> **Note implementazione**: `wiki-search` in fase di analisi non aveva trovato
> **nessuna** pagina su Asset Global, correlazione o heatmap. Depositate quattro pagine
> in `LibreFolio_devWiki/wiki/`, più le righe in `index.md` e in `log.md`:
>
> | Pagina | Cosa conserva |
> |---|---|
> | `decisions/asset-global-page-shows-no-money` | la regola dei pesi **e** il motivo per cui il suo test ovvio è vuoto |
> | `problems/front-check-does-not-check-what-you-think` | i due punti ciechi del gate, in direzioni opposte |
> | `problems/generated-client-widens-nullable-scalar` | validatore e tipo che dicono cose diverse |
> | `problems/asset-set-scope-has-no-primary-series` | perché D54 non ha una fonte dati, non un flag mancante |
>
> `python3 check_source_paths.py`: **61 percorsi rotti preesistenti** (92 occorrenze su
> 2087 citati, 56 pagine) — **zero nelle mie quattro**. Verificato con grep sul log.

> **⚠️ Fuori pista (7)**: due dei percorsi che stavo per citare erano **sbagliati a
> memoria** (`frontend/src/lib/risk/riskAnalysisHelpers.ts` invece di
> `.../components/risk/`, e uno `scripts/dev_commands/frontend.py` inesistente).
> Li ha intercettati il controllo *prima* della scrittura. È esattamente il difetto per
> cui quel controllo esiste: *un percorso ricordato non è un percorso che esiste*.

> **⚠️ Fuori pista (8)**: `graphify --update` **non eseguito**. `.graphify_python` è un
> artefatto ignorato e assente nel worktree, e il comando della skill punta al
> **checkout principale**, che non devo leggere. Le quattro pagine sono depositate e
> leggibili, ma **non ancora interrogabili dal grafo**: va rigenerato dal coordinatore
> o dallo sviluppatore. Segnalato, non aggirato.

### ✅ Passo 14b — due pagine in più, nate dai rossi · 18 Set 2026

> **Note implementazione**: i due fallimenti E2E avevano in comune una cosa — **la causa
> era l'osservatore, non il codice**. Meritano di sopravvivere, perché entrambi mi hanno
> ingannato e il secondo mi ha fatto scrivere un'escalation sbagliata.
>
> | Pagina | Cosa conserva |
> |---|---|
> | `problems/risk-request-sorts-asset-ids` | l'ordine del payload è per id crescente, quello dei chip per nome: uno stub posizionale legge l'asset sbagliato |
> | `problems/testid-grep-false-negative` | `${testId}-button` si compone a runtime: un `grep` a zero **non** significa selettore rimosso — e `AssetSelect` nasconde l'errore inverso |
>
> `python3 check_source_paths.py` → **59 rotti preesistenti, zero nelle mie sei pagine**.
> Il conteggio è sceso da 61 a 59 perché due percorsi citati dalle mie pagine di ieri —
> fra cui `risk-lab.spec.ts` — **nel frattempo esistono**. Il controllo misura il mondo reale.

### ✅ Passo 15 — `FROZEN` · 18 Set 2026

> **⚠️ Fuori pista (14) — il formattatore aveva ancora qualcosa da dire.**
> `front format` ha **riscritto due file miei** (`AssetSetRiskPanel.svelte`,
> `assetSetSelection.ts`): l'ultima modifica — l'aggiunta di `data-selection-source` — era
> rimasta fuori formato, perché avevo eseguito `front check` e i test *dopo* quell'edit ma
> **non** `front format`. Un verde su tre gate non copre il quarto.
> Riverificato dopo la riscrittura invece di darla per cosmetica:
> `front check` → **0 errori, 41 warning** (2 file preesistenti, non miei);
> `front-utility core-unit` → **82 file, 2062/2062**.

> **Artefatti non miei nell'albero**: `mkdocs_src/docs/static/icons/asset-types/commodity.png`
> e `real-estate.png` risultano *untracked*. Portano lo stesso timestamp (`Sep 18 00:20`)
> dei dodici fratelli **tracciati** nella stessa cartella: sono materializzazione del
> worktree, non lavoro mio. **Non li metto in stage**, li dichiaro.

### ✅ Passo 16 — verifiche su richiesta del coordinatore · 18 Set 2026 (nessuna modifica)

> **Rune sotto vitest (avviso di E)** — **non mi tocca**, verificato invece che assunto:
> 0 rune nei due moduli e nei due file di test, nessun `.svelte.ts`, ed **entrambi i test
> dichiarano già `@vitest-environment node` esplicitamente**. La persistenza non legge un
> globale: `readPersistedSelection`/`writePersistedSelection` **ricevono lo storage come
> parametro** e i test iniettano `fakeStorage()` / `refusingStorage()`. Non è fortuna, è la
> scelta del passo 2 — *la reattività è rimasta nel `.svelte`, il testabile è uscito puro*.
> L'unico `$effect` (semina della selezione) **non ha Vitest**: lo copre `risk-lab.spec.ts`
> test 2 in un **browser vero**. ⚠️ Vale *oggi*: un futuro `.svelte.ts` con rune riaprirebbe
> la trappola.

> **⚠️ Fuori pista (15) — K9: avevo torto io, e il campo sbagliato era suo.**
> Avevo ipotizzato che `:997`/`:1016` stessero in un blocco risultati **condiviso** col
> replay, e che le rimozioni restassero tre. **Falso**: `runReplay()` scrive `replayResult`,
> non `stressResult`, quindi `{#if stressResult || stressLoading}` (`:993`) è solo dello
> shock. *Una* rimozione, come diceva il coordinatore.
>
> Ma i campi che K9 nomina — `bucket_audit`, `metadata_fallback` — sono l'audit **dello
> shock**: vivono a `:1027-:1048` dentro `risk-stress-audit`, cioè **dentro il blocco che si
> sta togliendo**; dopo `:1068` non esistono. Il replay ha un audit **proprio e già
> costruito**: `risk-replay-audit` (`:1131`) con `missing-history-policy` (`:1134`),
> `composition-policy` (`:1138`), `proxy-series-usage` (`:1142`), il proxy **asset per
> asset** (`:1147`) e gli esclusi (`:1152`). La condizione del coordinatore è quindi **già
> soddisfatta strutturalmente**, e `:1147` è proprio la garanzia invocata: dichiara i proxy
> che *il backend* ha scelto. Segnalato: se il campo sbagliato resta nel contratto, E
> costruisce markup morto o duplica un audit che esiste.

> **Conseguenza sul mio test 1 — diventerà un rosso bugiardo.** Guida
> `risk-stress-controls` → `risk-stress-run` e mette le barriere di presenza su
> `risk-stress-section`/`risk-stress-impacts`. Dopo K9 quei testid spariscono per
> `asset_set`: il test fallirebbe **alla barriera**, non sull'asserzione del denaro, e
> sembrerebbe che la falla sia ancora aperta. **Retarget proposto**: `risk-replay-run`,
> barriera su **`risk-replay-audit`**, poi l'assenza di importi — così *la barriera e la
> condizione del coordinatore diventano la stessa asserzione*, e l'audit smette di essere
> una raccomandazione per diventare un gate. In attesa della sua scelta fra retarget
> speculativo (rosso fino all'atterraggio di E) e retarget dopo K9. **Raccomandato: dopo.**

### ✅ Passo 17 — K3 da B, verificato · 18 Set 2026 (nessuna modifica)

> **Note implementazione**: `AssetSelect` guadagna `sections` / `restLabel`, retrocompatibili.
> Tre delle quattro implicazioni relayate erano **già chiuse dal mio lato**:
>
> | Claim del relay | Verifica |
> |---|---|
> | «migra ad `AssetSelect`» | **già fatto al passo 4** — `:201`, con `filter`. È *questa* migrazione che ha rotto `risk-asset-add-select-trigger` (Fuori pista 11). Di K3 resta solo `sections` |
> | «se i tuoi test sullo stress usavano `equity_crash`…» | **irraggiungibile**: lo spec intercetta `risk/catalog` (`:306`), `risk/scenario-catalog` (`:310`) **e** `risk/query` (`:314`); gli unit sono funzioni pure. `grep equity_crash` → nulla |
> | `ALL_ASSET_TYPES:231` corretto da B | **non ho mai aperto `+page.svelte`** |
> | `AssetTable.typeBadgeHtml`/`enumOptions` | **non ho mai aperto `AssetTable.svelte`** — con D54 rinviata è sparita l'unica ragione |
>
> Sovrapposizione di file fra me e B: **zero**, provata da `git status`, non prevista.

> **⚠️ Fuori pista (16) — la mia isolazione ha un prezzo, e lo dichiaro invece di incassarlo.**
> Stubbare tutte e tre le rotte mi rende immune alla ricalibrazione di `equity_crash.yml` —
> ma per la stessa ragione **il mio spec non avrebbe mai scoperto** i quattro buchi che B ha
> chiuso (`BOND`, `CRYPTO`, `CROWDFUND`, `HOLD` shockati a zero in silenzio), e non scoprirà
> la prossima regressione di taratura: da me resterebbe **verde**. La mia rete copre la
> **resa**, non la **calibrazione**. Quella copertura deve avere un altro proprietario.

> **Decisione rimandata al coordinatore**: `sections` (sezione «i miei» su `tx_count_own > 0`,
> *lo stesso predicato del fallback D19*, così picker e selezione iniziale raccontano la
> stessa storia) ora oppure insieme al retarget di test 1 dopo K9. **Raccomandato: insieme** —
> il retarget riaprirà comunque il file e la scala di gate, e accorparli dimezza le finestre
> in cui il mio ramo si muove sotto l'integrazione. Resto `FROZEN`.

### ✅ Passo 18 — D100 applicato a me stesso · 18 Set 2026 (nessuna modifica)

> **⚠️ Fuori pista (17) — 🔴 due delle mie sei reti E2E non discriminano.**
> Lo standard di prova D100 chiede di rompere una rete e citare il rosso. Congelato non
> posso eseguire la rottura, ma ho fatto il passo che la precede: **rileggere le asserzioni
> chiedendomi cosa *non* le farebbe fallire**. Due non reggono.
>
> | # | Test | Discrimina? |
> |---|---|---|
> | 1 | nessun denaro | ✅ **rosso vero**: `€12,345.67` — una cattura reale, più forte di una rottura iniettata |
> | 2 | selezione iniziale | ✅ `data-selection-source="mine"` **irraggiungibile** dal vecchio `slice(0,100)` |
> | 3 | azioni di massa | ✅ conteggi esatti dopo ogni azione: un no-op fallisce |
> | 4 | filtri | 🟡 **metà inerte** |
> | 5 | coppie della matrice | ✅ **rosso vero**: fallita sull'indice sbagliato, verde con la correzione |
> | 6 | riordino | 🔴 **inerte sul cablaggio** |
>
> **Test 6** asserisce l'inversione di `aria-pressed`, la sopravvivenza delle due scoperte e
> il ridisegno del canvas — **mai che l'ordine sia cambiato** (il commento lo ammette:
> *«Nothing here asserts a visual sequence»*). Se `clusterOrder` restituisse l'**identità**,
> o il toggle fosse cablato a una variabile che nessuno legge, **resta verde**. Gli unit
> provano l'algoritmo, **niente prova il cablaggio**: unit verdi perché la matematica è
> giusta, E2E verde perché il bottone si preme, e il difetto passa in mezzo.
> *Correzione proposta*: `CorrelationHeatmap` espone solo `data-testid` (`:221`); aggiungere
> **`data-asset-order`** e asserire che cambi fra i due modi restando una permutazione dello
> stesso insieme. ⚠️ **Cautela**: lo stub va costruito perché il clustering permuti
> *dimostrabilmente*, o si sostituisce una rete inerte con una instabile.
>
> **Test 4** prova **bene** il bug del wiki (`:643-644` i conteggi delle opzioni non calano,
> `:645-646` la pastiglia resta cliccabile), ma `:634` è `toBeLessThanOrEqual`: **con un
> filtro morto** `candidates == unfiltered` e passano tutte e tre le asserzioni. Il non
> stretto ha una ragione onesta (un `<` sarebbe instabile con un solo tipo a DB), ma la
> narrowing non è provata. *Correzione*: l'invariante vero — *dopo il filtro per T, **ogni**
> candidato è di tipo T* — sotto guardia `typeOptions > 1`.

> **TDZ nei `.svelte.ts` (avviso di E)** — non mi tocca, **con prova positiva**: nessun
> `.svelte.ts`, nessuna factory, nessuna closure che legga una dichiarazione più in basso.
> E non è un grep: **5 test su 6 montano la pagina**. Un `ReferenceError` in init le avrebbe
> spente tutte e sei con «`dashboard-risk-tab` non trovato». Il mio unico rosso stampa un
> importo: la pagina c'è.

> **Coda di riapertura proposta**: (1) `data-asset-order` + permutazione, (2) invariante di
> tipo nel test 4 — **subito, nella stessa revisione delle reti che correggono**; (3)
> `sections` di K3 e (4) retarget di test 1 su `risk-replay-audit` — nel giro post-K9.
> In attesa dello scongelamento. Se l'integrazione è già partita, **due reti restano
> dichiaratamente inerti**: meglio scritto che scoperto dopo.

---

## Passo 19 — verifica del relay K5 (primitive, `coverage`, `NaN%`, `tee|head`) · 2026-09-01

**Note implementazione**: giro di **sole letture**, `FROZEN` mantenuto. Nessuna modifica a
codice, test, server o Git. Quattro affermazioni del coordinatore verificate sul codice,
più il numero di `check-links` che mi era stato richiesto due volte.

| # | Affermazione relayata | Esito verificato |
|---|---|---|
| 1 | «Le primitive esistono in `ui/display/`: **puoi adottarle ora**» | 🔴 **falso nel mio albero** — vedi *Fuori pista 18* |
| 2 | «Non presentare `coverage` come qualità dei dati» | 🟢 **non mi tocca**, ma per una ragione che andava provata |
| 3 | «`width: NaN%` conserva la larghezza precedente» | 🟢 non raggiunge i miei file |
| 4 | «`tee \| head` tronca il log al 54 %» | 🟢 ho usato `tail`: log **integro**, e conferma indipendente della misura |

> **⚠️ Fuori pista 18 — 🔴 le primitive di K5 non sono nella mia baseline. È F-7, la terza volta.**
> `find frontend/src -name "RiskMetricCard.svelte"` → **nessun risultato**. E le altre due
> **non si sono spostate**: `dashboard/KpiMetricBar.svelte`, `dashboard/KpiDivergingFlowBar.svelte`.
> `ui/display/` contiene solo `BrokerBadge.svelte`, `CompactCashCell.svelte`, `CompactCashCell.test.ts`.
> La tabella «Prima → Adesso» del relay descrive **il worktree di D**. Adottarle ora avrebbe
> importato un file inesistente e **rotto `front build`** — l'unico gate oggi pulito.
> *Causa sistemica*, identica alle due volte precedenti (K5, poi `implementation/contracts/`):
> **un contratto si relaya, il codice si integra.** Senza lo SHA che lo porta non ho modo di
> distinguere «esiste» da «esiste altrove».
> *Rimedio proposto al coordinatore*: allegare al relay lo **SHA del commit**, così verifico
> con `git cat-file -e <sha>:<path>` invece che con `ls`.

> **Il `coverage` del mio tooltip non è quello dell'avvertimento — e sono due campi omonimi.**
> `CorrelationHeatmap.svelte:177` legge `params.data`, cioè la **cella**:
> `RiskMatrixCell.coverage` (`schemas/risk.py:656`) = frazione della finestra in cui
> **entrambi** gli asset avevano dati. L'avvertimento riguarda
> `RiskResultMetadata.coverage` (`:451`), il cui denominatore differisce da
> `annualization_factor` (`:450`). Per una cella di correlazione quella copertura è **il
> segnale giusto**, e soprattutto **in una correlazione non esiste annualizzazione** — è
> adimensionale — quindi la distorsione descritta non può nascere.
> ⚠️ *Ma il rischio intercettato è reale oltre il mio caso*: **due campi `coverage` diversi
> nello stesso file, a duecento righe di distanza, con denominatori diversi**. È esattamente
> ciò che ha prodotto l'avvertimento sbagliato, e stavo per commettere lo stesso errore
> leggendolo. Un precedente per il rename esiste già: `calendar_coverage` (`:400`).

> **`NaN%`**: zero percentuali CSS in `CorrelationHeatmap`, `CorrelationPairsList`,
> `AssetSetRiskPanel`. La geometria della heatmap è di ECharts; la lista coppie non ha barre.
> Lezione presa comunque: *un denominatore nullo non dà errore, dà il numero di prima.*

> **Il mio log di `front format` è completo** — usavo `| tee log | tail -12`, non `head`.
> Misurato: **768 righe · 96 voci `e2e/` · 763 voci-file**, combaciante con la corsa corretta
> di D (768 file, 98 in `e2e/`). Quindi «Prettier ha riscritto esattamente 2 file» poggia su
> un log integro, e la misura del 54 % perso con `head` ha ora **una conferma da una corsa
> indipendente**.

> **`check-links` = 12** (rinviato al coordinatore, terza richiesta). Dal log del passo 0:
> `✅ 12 valid link(s)`. La baseline «24» di I è **il doppio del reale**: se il suo cancello
> è «24 e ogni link deve far salire il numero», **parte rosso**. Io ho aggiunto **zero**
> `DocsLink`: lo slug `correlation` non esiste in tutto l'albero docs.

**Stato**: `FROZEN`. HEAD invariato a `cc33120e`, niente in stage.
**Coda di riapertura** (invariata, più una): (1) `data-asset-order` + permutazione;
(2) invariante di tipo nel test 4; (3) `sections` di K3; (4) retarget di test 1 su
`risk-replay-audit`; **(5) adozione delle primitive — solo quando saranno nel mio ramo.**

---

## Passo 20 — le due reti inerti, riparate e **rotte apposta** (D100) · 2026-09-18

**Autorizzazione**: «Prosegui» del coordinatore. ⚠️ Il messaggio nominava lavoro **già
consegnato** (Vitest sugli helper, rete della regola dei pesi, E2E in 6245): era una
risposta a un giro vecchio. Ho quindi proseguito sulla **coda dichiarata**, cioè le due
reti che al passo 18 avevo dichiarato **non discriminanti** — entrambe su superfici mie.

### Cosa è cambiato

| File | Modifica |
|---|---|
| `CorrelationHeatmap.svelte` | `data-asset-order={order.join(',')}` sul contenitore: pubblica **l'array da cui il grafico è costruito** |
| `risk-lab.spec.ts` | gemello piantato a **indice 3** invece di 1; `MINIMUM_SELECTION`, `REDUNDANT_INDEX`, `OFFSETTING_INDEX`; helper `adjacentInOrder`; test 5 ritarghettato; **test 6 riscritto**; **test 4** con l'invariante di partizione |
| `correlationHelpers.test.ts` | nuovo test che **fissa la premessa** dell'E2E (2062 → 2063) |

> **⚠️ Fuori pista 19 — 🔴 il test 6 non poteva discriminare, e adesso è **misurato**, non dedotto.**
> Al passo 18 l'avevo dichiarato inerte «al cablaggio». Prima di correggerlo ho verificato
> *perché*, con una sonda eseguita: lo stub piantava il gemello a **indice 1**, cioè
> **già adiacente** al suo partner. Misura:
> ```
> redundantAt=1 → [101,102,103,104,105,106,107,108] identity=true
> redundantAt=5 → [101,106,103,102,104,105,107,108] identity=false adj=true
> ```
> Con lo stub vecchio `clusterOrder` restituiva **l'ordine di input**: `similarity` e
> `original` erano **lo stesso array**. Quindi non solo il test non asseriva il riordino —
> **asserirlo sarebbe stato un rosso falso**. La cautela del passo 18 era fondata.
> *Correzione*: gemello a indice 3, `MINIMUM_SELECTION = 4`. Verificato per **ogni** taglia
> raggiungibile (N = 4…8): `identity=false`, `adj=true` sempre. La selezione iniziale non è
> fissa (`ensureSelectionAtLeast` è un *pavimento*, e D19 può seminarne di più), quindi la
> posizione piantata doveva esistere per ogni N — non per uno.

> **⚠️ Fuori pista 20 — 🔴 il test 4 era inerte *e il suo commento rivendicava rigore*.**
> `candidates` non è un oracolo indipendente: `chooseTypeFilter` lo **legge dal contatore
> stesso** che l'asserzione poi controlla. Con un filtro morto ogni tipo restituisce
> l'insieme pieno → `candidates === unfiltered` → passano sia il `toBeLessThanOrEqual` sia
> il successivo `data-total === candidates`, che un commento definiva «*Exact, and retried*».
> **Un commento che rivendica una precisione che il codice non ha è peggio del codice.**
> *Correzione*: l'invariante di **partizione**. Un asset ha esattamente un tipo e le
> pastiglie derivano dall'insieme intero → i filtri di tipo applicati uno per volta devono
> **sommare all'insieme non filtrato**. Un filtro morto somma `options × unfiltered`.
> Nessun dato per-asset richiesto, solo conteggi.

> **⚠️ Fuori pista 21 — `tsconfig.e2e.json` non è inutilizzato: è **già rosso**.**
> `npx tsc -p tsconfig.e2e.json --noEmit` → **48 errori**, tutti preesistenti:
> `e2e/tools/pac-allocator.spec.ts` (33), `features/tools/contracts.ts` (14),
> `types/files.ts` (1). **Zero nel mio spec.** Quindi il buco F-16 non è «nessun gate lo
> usa»: è che **accenderlo oggi costa 48 riparazioni altrui**. Ed è anche l'unica prova
> di tipo che il mio spec riscritto potesse avere: `front check` esclude `e2e/**`.

### 🔬 D100 — ogni rete rotta una volta, rosso citato

| Rete | Rotta come | Rosso ottenuto |
|---|---|---|
| Unit sulla premessa | gemello rimesso a indice 1 | `AssertionError: size 4 must cluster the twins: expected false to be true` |
| **Test 6** | `order` cablato a `[...output.asset_ids]` (toggle collegato a nulla) | `Error: similarity must not simply echo the payload order` (`:791`) |
| **Test 4** | filtro per tipo reso no-op in `applyFilters` | `Error: type filters must partition the candidates, not each return everything` (`:679`) |

Entrambe le rotture E2E **passavano verdi con le reti vecchie**. Rotture rimosse e assenza
verificata (`grep "BREAK"` → nessun residuo).

### Evidenza — comandi esatti

| Comando | Esito |
|---|---|
| `front-utility core-unit "E2E stub topology"` | 1 passed |
| `front format` | riscritto **solo** `CorrelationHeatmap.svelte` |
| `front check` | **0 errori**, 41 warning in 2 file (preesistenti) |
| `npx tsc -p tsconfig.e2e.json --noEmit` | 48 errori, **0 miei** |
| `front-portfolio risk-lab` | **5 passed, 1 failed** — il rosso è il test 1 (denaro), **per progetto** fino a K9 |
| `front-utility core-unit` | **2063/2063**, 82 file |

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.
**Coda residua**: `sections` di K3; retarget del test 1 su `risk-replay-audit` dopo K9;
adozione delle primitive **quando saranno nel mio ramo**.

---

## Passo 21 — debito `DocsLink` registrato · l'astensione travestita, misurata · 2026-09-18

### 📌 Debito di documentazione — **mio, post-integrazione**

| | |
|---|---|
| **Cosa** | `DocsLink` dalla heatmap di correlazione |
| **Slug** | `financial-theory/technical-analysis/risk-metrics/correlation/` — **esiste**, nel worktree di I |
| **Proprietario** | **F** |
| **Quando** | dopo l'integrazione di I, **mai prima** |
| **Perché non ora** | nella baseline `cc33120eb` lo slug **non risolve**: il link farebbe **scendere** il conteggio di `check-links` invece di alzarlo, cioè romperebbe il cancello che K7 esiste per far salire |

> Il coordinatore ha verificato: I ha costruito **21 pagine** (`correlation`, `concentration`,
> `risk-contribution`, `data-quality`, `observed-annualization`, `historical-replay`,
> `hypothetical-shock`, `simulation-modes`, `worst-realization`, i sei della famiglia
> drawdown…). Nella mia baseline ce ne sono **cinque**. Il mio contributo zero è
> **deliberato**, non una dimenticanza. *Un debito che vive in una sola testa è un debito
> perso*: per questo sta qui e non solo in un messaggio.

E per memoria: **`check-links` = 12 nel mio mondo, 24 nel mondo di I.** Il numero sbagliato
stava in un contratto che non dichiarava il proprio mondo. Regola che ne esce:
**un numero in un contratto deve dichiarare il mondo in cui è stato misurato.**

> **⚠️ Fuori pista 22 — 🔴 un filtro che non combacia riporta VERDE, e `exit=0`.**
> Avviso di E, verificato **nella mia lane** invece che accettato. Un solo carattere di
> refuso (`"E2E stub topologyy"`):
> ```
>  Test Files  82 skipped (82)
>       Tests  2063 skipped (2063)
>    Duration  13.06s (… tests 0ms …)
> ✅ Core store Vitest unit tests - PASSED        exit=0
> ```
> **Più insidioso di come è stato descritto**: la riga `Tests` non contiene **nessun token
> `passed`** — quindi il discriminante non è «0 passed», è **l'assenza del conteggio**. Chi
> cerca `grep PASSED` legge un verde; chi cerca `grep -E "passed|failed"` non trova nulla
> sulla riga che conta e può ripiegare sul banner. E `exit=0` rende cieco anche lo scripting
> sullo stato d'uscita.
> **Discriminante affidabile**: `tests 0ms`, oppure pretendere `Tests N passed` con N ≥ 1.
>
> ✅ **Audit delle mie cinque corse filtrate**: nessuna è un'astensione.
> `probe3` 1 failed · `unit_premise` **1 passed, tests 48ms** · `break1` 1 failed ·
> `break2` 1 failed · `break3` 1 failed. E le tre rotture hanno prodotto **il testo
> esatto delle mie asserzioni nuove** (`must cluster the twins`, `must not simply echo
> the payload order`, `must partition the candidates`): un filtro a vuoto non può
> fabbricare un messaggio su misura. I verdi autorevoli restano comunque i due **non
> filtrati**: `2063/2063` e la suite E2E completa.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 22 — registrazioni nel runner: additività **verificata**, non dichiarata · 2026-09-18

Il coordinatore ha autorizzato la riga in `_frontend_portfolio.py` con tre condizioni
(solo additiva · citata parola per parola · fermarsi se serve toccare altro) e ha
approvato retroattivamente `_frontend_utility.py` come «additivo della stessa forma».
**Ho misurato invece di confermare.** Le due cose non hanno la stessa forma.

| File | `git diff --numstat` | Verdetto |
|---|---|---|
| `_frontend_portfolio.py` | **10 aggiunte, 0 rimozioni** | ✅ **puramente additivo**, le tre condizioni sono soddisfatte alla lettera |
| `_frontend_utility.py` | **3 aggiunte, 1 rimozione** | 🟠 due aggiunte pure **+ una riga esistente modificata** |

La riga modificata è il `desc=` della voce `core-unit`. Verificato carattere per carattere:

```
vecchio desc: 1517 caratteri — conservato VERBATIM come prefisso
nuovo  desc: 1877 caratteri — 360 aggiunti in coda
resto della riga: identico
```

Quindi è **semanticamente additivo** (nulla rimosso, nessun testo altrui toccato) ma
**testualmente una modifica**. E la regola appena generalizzata dal coordinatore —
*«restano da chiedere: riordini, **modifiche a voci esistenti**, cambi di struttura»* —
**escluderebbe proprio ciò che ho fatto**.

> **⚠️ Fuori pista 23 — 🔴 il `desc=` di `core-unit` è una riga sola che ogni mandato deve allungare.**
> ~1 900 caratteri su **una riga fisica**. Chiunque aggiunga un test unitario al catalogo
> deve estenderla. G ed E lo faranno. Git vedrà **tre modifiche alla stessa riga** →
> **conflitto testuale garantito**, risolvibile solo rileggendo prosa a mano.
> Non è un rischio: è una certezza aritmetica, e arriva **dopo** che il coordinatore avrà
> detto a G ed E «registrate senza chiedere».
> *Proposta*: dichiarare l'**estensione in coda di un `desc=`** una forma additiva
> riconosciuta, con regola di risoluzione meccanica — **si tengono entrambe le clausole
> aggiunte, nell'ordine di arrivo**. Così il conflitto resta, ma smette di essere un
> giudizio e diventa un'unione.

### La riga registrata, parola per parola

```python
    add_test(cat, "risk-lab", front_portfolio_risk_lab, name="Asset Global Risk Lab Tests", desc="Asset-set laboratory: the no-money rule asserted by stubbing money in, D19 opening selection by branch rather than by size, bulk actions against filtered candidates, filters that keep their own option clickable, correlation pairs keyed by asset id and matrix ordering", tests="portfolio/risk-lab.spec.ts")
```

più la funzione `front_portfolio_risk_lab` (`:83-90`), che termina con:

```python
    return _run_playwright("portfolio/risk-lab.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)
```

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 23 — verifica dei relay di B · 2026-09-18

### 🔴 Fuori pista 24 — `api sync` è il comando che **non può** attraversare i worktree

Il coordinatore relaya da B: *«`generated.ts`: da 6 a 11 occorrenze di `is_benchmark`.
**Rifai `api sync`** o non vedrai il parametro»*. Misurato:

```
grep -rn "is_benchmark" backend/app --include=*.py   →  0
grep -c  "is_benchmark" frontend/src/lib/api/generated.ts  →  0   (client risincronizzato alle 02:26)
```

**Zero nel backend, zero nel client appena generato.** `api sync` legge l'OpenAPI del
backend **locale**: rigenerarlo mille volte non produrrà mai un campo che il mio backend
non dichiara. L'istruzione è **insoddisfacibile nel mio mondo**, non perché sia sbagliata
ma perché descrive il mondo di B.

> È **F-7 per la quarta volta** — e stavolta il rimedio che avevo proposto (allegare la
> SHA al relay) **non basterebbe**: `generated.ts` è **gitignorato e generato**. Non
> esiste SHA che lo contenga. Può comparire solo dopo che il **codice backend** di B è nel
> mio ramo. Per gli artefatti generati la frase giusta non è «rifai `api sync`» ma
> **«questo comparirà dopo l'integrazione, non prima»**.

### ✅ `asset-list.spec.ts` — non ho alcuna posta in quel file

B manda i confini di merge (righe 1-691 intatte, B occupa 692-825, appendere a 825).
**Non mi serve**: quel file non è fra i miei dieci. D54 è stata rinviata → niente colonne
di rischio; la rete sulla regola dei pesi è finita in `risk-lab.spec.ts`, non lì.
→ **Lo slot d'integrazione per F su `asset-list.spec.ts` si può chiudere.**

### ✅ Verifica positiva **per** B, che nessuno aveva chiesto

`asset-list.spec.ts:362` e `:368` asseriscono su `asset-global-risk-panel`. Il mio
riscritto **conserva quel testid** → **la riscrittura del mio pannello non rompe lo spec di
B**. Verificato, non supposto.

### ✅ F30 confermato, e sono immune in **entrambe** le direzioni

`AssetSelect.svelte:123` rende `data-testid={testid}` su un **div wrapper**; `:124` passa a
`SearchSelect` **senza** `testid`. B ha ragione: `{testId}-trigger` sparisce.
Il mio spec (`:430`) prende **il wrapper**, non il trigger → funziona **prima e dopo** la
correzione di B. **Non implemento nulla.**

### ✅ E lo spec di E ha bisogno di due righe, non di una riscrittura

| Riga di `risk-analysis.spec.ts` | Sorte sotto il mio riscritto |
|---|---|
| `:652` `risk-asset-add-select-trigger` | 🔴 **rotta** — già instradata a E |
| `:654` `risk-asset-add-button` | 🔴 **rotta** — già instradata a E |
| `:633` `asset-global-risk-panel` | ✅ **sopravvive** |

### ✅ «6 test non eseguiti»: cinque esecuzioni, con durate vere

`front-portfolio risk-lab` in `6245`: `4 passed/2 failed` (prima della correzione
dell'ordinamento) → poi **`5 passed, 1 failed`** in **quattro** corse successive, durate
13,0s · 13,6s · 18,0s · 41,9s. Nessuna è un'astensione: **nessun `0ms`, nessuno `skipped`**.
Lo spec è **812 righe**, non 708 — la differenza sono le riparazioni D100 di test 4 e 6.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 24 — la trappola della ritrattazione: **non è dietro di me, è davanti** · 2026-09-18

Il coordinatore avvisa che ho «due `test-author` in volo» e che scrivere sotto un agente
aperto produce una **ritrattazione falsa** (caso di I: l'agente si accusa di un bug che non
aveva, perché il mondo era cambiato sotto di lui).

### Misurato: nessun agente è in volo

```
💤 lab-helper-tests  (59b88302…)  idle  5984s ≈ 100 min
💤 risk-lab-e2e      (bd18b864…)  idle  4983s ≈  83 min
```

### La trappola **non si è verificata all'indietro** — lo provano i timestamp

| Agente | inattivo da | mia scrittura successiva | scarto |
|---|---|---|---|
| `lab-helper-tests` | ~00:58 | `correlationHelpers.test.ts` **02:22:17** | +84 min |
| `risk-lab-e2e` | ~01:14 | `risk-lab.spec.ts` **02:17:22** | +63 min |

Ogni mia scrittura è **posteriore** alla chiusura del turno. Nessun agente ha misurato un
mondo che stavo cambiando.

### 🔴 Fuori pista 25 — ma la trappola è **carica**, e con precisione

Ho modificato **i deliverable di entrambi** mentre erano inattivi:

| Agente | come l'ha lasciato | com'è adesso |
|---|---|---|
| `risk-lab-e2e` | `risk-lab.spec.ts` **708 righe** | **812** (+104), **test 4 e 6 riscritti da me** |
| `lab-helper-tests` | 7 `describe` | **8** — `clusterOrder — the E2E stub topology` (`:616`) è mio; 57 `it` |
| — | — | e `CorrelationHeatmap.svelte` (**02:24:05**) ha un `data-asset-order` che l'agente E2E **non ha mai visto** |

> **Se svegliassi `risk-lab-e2e` senza annunciare il delta, sarebbe il caso di I alla
> lettera** — e con una conclusione peggiore: troverebbe **proprio i due test che aveva
> scritto** riscritti, e concluderebbe *«il mio lavoro era sbagliato»*.
> **Non era sbagliato: era inerte** — passava senza poter fallire. Sono due difetti
> diversi, e la ritrattazione archivierebbe la lezione sbagliata.

**Precondizione che adotto**: ogni futuro `write_agent` a uno dei due **apre con il delta** —
righe, test riscritti, attributi di prodotto aggiunti — nello stesso messaggio.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 25 — 🔴 conflitto previsto con la correzione F30 di B · 2026-09-18

### La struttura, misurata

```
AssetSelect.svelte:183    <div data-testid={testid}>          ← wrapper
SearchSelect.svelte:357   <div … data-testid={testId}>        ← container
SearchSelect.svelte:374       role="combobox"                 ← DISCENDENTE del container
```

Il `role="combobox"` è **dentro** il div che porta il testid, non è quel div.

### Perché mi riguarda: il mio helper interroga per **discendenza**

`risk-lab.spec.ts:428-436` (`ensureSelectionAtLeast`, usato da **due** test, `:720` e `:759`):

```ts
const picker = page.getByTestId('risk-asset-add-select');
await picker.locator('[role="combobox"]').click();
```

| Se B fa… | DOM | esito del mio helper |
|---|---|---|
| **inoltra e basta** (parziale) | testid su wrapper **e** su container, annidati | `getByTestId` → **2 elementi**; il combobox è discendente di entrambi → **2 match** → 🔴 **strict-mode violation** su `.click()` |
| **inoltra e toglie l'id al wrapper** (corretto) | testid solo sul container | 1 elemento → ✅ **il mio spec sopravvive** |

> **Il mio spec è il caso che distingue le due riparazioni.** Con la correzione completa
> non me ne accorgo nemmeno; con quella parziale perdo due test — e non per un difetto mio.

### 🔴 E non sono nel cancello di B

Il cancello dichiarato è `tx-import-*`, che esercita il testid **di default** (`asset-select`).
Ma il prop `testid` ha **quattro valori** su 5 punti di chiamata:

| valore | punto di chiamata | consumatori e2e |
|---|---|---|
| `asset-select` (default) | `ImportWizardModal:4324` | i 5 enumerati |
| `tx-form-asset` | `TransactionFormModal:1513,:1886` | (gli spec usano `tx-form-asset-wrap`, testid **diverso** → non toccati) |
| `asset-merge-target-select` | `AssetMergeModal:259` | `assets/asset-merge.spec.ts` |
| **`risk-asset-add-select`** | `AssetSetRiskPanel:201` (mio) | **`portfolio/risk-lab.spec.ts`** |

**Le due vie custom — `asset-merge` e la mia — non sono in `tx-import-*`.** Chi fa la
modifica non esercita il percorso che la distingue.

**Richiesta**: il cancello di B includa `front-portfolio risk-lab` e lo spec di merge,
oppure rieseguo io `risk-lab` dopo l'integrazione.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 26 — autorizzazione per 1 e 2: **erano già consegnate** · 2026-09-18

Il coordinatore scongela per i punti 1 e 2 (riparazione delle due reti inerti). **Entrambe
erano già in albero** dal giro precedente, con i rossi citati. Verificato sul file, non a
memoria: test 4 a `:656` con l'invariante di partizione a `:679`, test 6 a `:756` con
l'asserzione chiave a `:792`.

### 🟠 Fuori pista 26 — l'asserzione che il coordinatore descrive **non è quella che ho scritto**, e la sua non è misurabile

Il coordinatore descrive per il test 4 un'invariante di **omogeneità**:
*«dopo aver filtrato per il tipo T, ogni candidato è di tipo T»*.
Io ho implementato un'invariante di **partizione**: `Σ|filtro(T_i)| = |non filtrato|`.

**L'omogeneità non è esprimibile nel mio DOM.** Misurato:

| superficie | cosa espone |
|---|---|
| `AssetSetRiskPanel:242` | `risk-filter-type-{type}` — è la **pastiglia**, non un candidato |
| `AssetSetRiskPanel:271` | `risk-selected-asset-{id}` — solo l'**id**, nessun tipo |
| contatore | `data-selected` / `data-total` — **un numero** |

**I candidati non sono elementi enumerabili: sono un conteggio.** Per asserire l'omogeneità
dovrei rendere l'intero insieme candidato nel DOM — cioè **cambiare il prodotto per il
test**.

E la partizione è **più forte in una direzione**: un filtro *corretto ma lesivo* (restituisce
solo T, ma ne perde qualcuno) **passa** l'omogeneità e **fallisce** la partizione.

### I tre rossi, verbatim

```
[unit]  AssertionError: size 4 must cluster the twins: expected false to be true
        Tests  1 failed | 2062 skipped (2063)                         100ms

[e2e 6] ✘ risk-lab.spec.ts:756 … the ordering toggle reorders the matrix and loses no finding (2.0s)
        Error: similarity must not simply echo the payload order

[e2e 4] ✘ risk-lab.spec.ts:656 … a filter keeps its own option clickable and clears back (2.3s)
        Error: type filters must partition the candidates, not each return everything
```

Durate **100ms · 2,0s · 2,3s**: nessuna è un'astensione.

### La cautela che l'autorizzazione poneva era già onorata

*«la matrice dello stub deve permutare dimostrabilmente, altrimenti sostituisci una rete
inerte con una rete instabile»*. È esattamente ciò che avevo misurato **prima** di riscrivere:
col gemello all'indice 1 `clusterOrder` restituiva **l'identità**, quindi l'asserzione ovvia
sarebbe stata un **falso rosso**. Gemello spostato all'indice 3 e **premessa fissata da un
test unitario permanente per ogni N=4…8** (2062 → **2063**).

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 27 — la regola dello SHA **eseguita**, e il suo confine · 2026-09-18

Il coordinatore adotta la mia regola e manda il primo SHA: `1a537f9cb` (checkpoint di D).
**L'ho eseguita**, perché una regola che il destinatario non può eseguire vale quanto il
relay che sostituisce.

```
git cat-file -t 1a537f9cb                                → commit          ✅
…:ui/display/RiskMetricCard.svelte                       → ✅ presente
…:ui/display/KpiMetricBar.svelte                         → ✅ presente
…:ui/display/KpiDivergingFlowBar.svelte                  → ✅ presente
git for-each-ref refs/copilot/checkpoints/ | wc -l        → 1232
```

**Funziona perché i worktree condividono un solo object store.** La regola non è una
convenzione documentale: è **un comando che il destinatario può eseguire**. Chiude F-7
strutturalmente — per la prima volta in quattro relay posso rispondere «esiste, e qui».

### ✅ E il confine, provato: la classe che **nessuno** SHA può portare

```
1a537f9cb:frontend/src/lib/api/generated.ts   → ❌ non nell'albero
1a537f9cb:frontend/src/lib/api/openapi.json   → ❌ non nell'albero
```

**Gli artefatti generati e gitignorati non stanno in nessun commit.** Per loro la frase
giusta resta **«comparirà dopo l'integrazione»**: né un file né uno SHA possono provarli.

✅ Conferma indipendente: `git grep -c is_benchmark 1a537f9cb -- backend/app` → **0**.
Cioè il campo non esiste **nemmeno nell'albero di D** — la mia misura di Passo 23 vale ora
da **due** punti d'osservazione, non solo dal mio.

### 🔴 Fuori pista 27 — i `coverage` non sono tre omonimi: **è lo stesso nome per tre denominatori E un nome diverso per la stessa cosa**

| riga | modello | vicini di campo | denominatore implicato |
|---|---|---|---|
| `:451` | `RiskResultMetadata` | `n_observations`, `calendar_days`, `annualization_factor` | copertura di calendario di **una** serie |
| `:656` | `RiskMatrixCell` | `row_asset_id`, `column_asset_id`, `observations` | sovrapposizione **di coppia** |
| `:967` | `RiskDrawdownOutput` | `available_start`, `available_end`, `n_observations` | copertura della finestra **disponibile** |

E il precedente non è «un precedente»: **è lo stesso blocco, già disambiguato**.

```
:398 calendar_days            :449 n_observations
:399 annualization_factor     :450 calendar_days
:400 calendar_coverage   ←→   :451 annualization_factor
:401 fresh_quote_coverage     :452 coverage            ← stesso vicinato, nome generico
```

> **Il file contiene già il nome corretto per il campo ambiguo, cinquanta righe più su,
> applicato allo stesso vicinato.** Il rename di `:451` → `calendar_coverage` non è una
> decisione di design: è una **riparazione di coerenza interna**.

⚠️ *Onestà epistemica*: è evidenza **strutturale** (vicinato identico), non lettura del
calcolo. Chi esegue il rename confermi sul servizio che popola il campo.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 28 — `1 674` misura la **riga**, non il `desc=` · 2026-09-18

Il coordinatore registra in `STATO.md` §15: *«Il `desc=` di `core-unit` nella baseline:
**1 674 caratteri**»*. Misurato:

| | baseline | attuale |
|---|---:|---:|
| contenuto della stringa `desc=` | **1 517** | **1 877** |
| **riga fisica intera** | **1 672** | **2 032** |
| riga + newline | 1 673 | 2 033 |

**1 674 non coincide con nessuna delle quattro**, ma dista 1-2 dalla **riga intera**: è la
riga, non il campo. Il numero è **giusto di grandezza e attribuito al referente sbagliato**.

> È la **stessa classe** già trovata due volte oggi: i tre `coverage` (stesso nome, tre
> denominatori) e `check-links` 12 vs 24 (stesso numero, due mondi). Qui: **numero giusto,
> oggetto misurato diverso da quello dichiarato.**
> Chi domani leggesse «il `desc` è 1 674» e lo misurasse troverebbe **1 517**, e cercherebbe
> una modifica che non è mai avvenuta.

✅ E una prova meccanica che arriva gratis dalle stesse cifre: **la riga è cresciuta
esattamente dei 360 caratteri di cui è cresciuto il `desc`** (1672→2032, 1517→1877).
Quindi **nulla fuori dal `desc` è cambiato** — più forte del confronto fra stringhe che
avevo fatto prima.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 29 — la divisibilità di A: **immune oggi, carica domani** · 2026-09-18

Relay di A (misurato 02:4x, 7 200 prove): il VaR si sposta **esattamente quando
`(1 − confidenza) × osservazioni` è un intero**, e allora si sposta del 100 %, mai a metà.
Il coordinatore chiede se le mie fixture usano lunghezze tonde.

### ✅ Parte 1 — non può raggiungermi **oggi**, e per struttura

`risk-lab.spec.ts:118`, il mio stub del catalogo:

```js
definition('historical_var', 'var_cvar', ['asset', 'portfolio'], …)
```

**`asset_set` non è fra gli scope.** Lo stub dichiara VaR non supportato per il mio scope —
coerente con F-5, dove avevo misurato che `historical_var` non accetta `ASSET_SET`.
**Nessun numero di VaR viene mai calcolato né asserito nel mio spec.**

### ⚠️ Fuori pista 28 — ma la mia fixture è **esattamente** nel caso che si muove

`risk-lab.spec.ts:159` e `:243` → **`observations = 60`**.

| confidenza | `(1 − c) × 60` | |
|---|---:|---|
| 0,95 | **3,0** | 🔴 intero |
| 0,90 | **6,0** | 🔴 intero |
| 0,99 | 0,6 | ✅ |

**60 è divisibile per 10 e per 20**: è precisamente il numero «pulito» che A descrive.
Quindi la mia fixture è **già armata per una funzionalità che non esiste ancora**: se un
giorno `historical_var` accettasse `ASSET_SET` — che era l'opzione (a) di **Q-F4** — le
asserzioni sul VaR nascerebbero **sul filo**, e si sposterebbero del 100 % fra rami senza
che nulla di visibile cambi nel test.

**Rimedio, un carattere**, da applicare **insieme** a quella estensione e non prima:
`observations = 61` → 3,05 · 6,1 · 0,61, **nessun intero** per le tre confidenze comuni.

> Non lo applico adesso: cambierebbe anche `annualization_factor` (`:169`, derivato da
> `observations`) per rincorrere una funzionalità che non c'è. **Va legato alla condizione
> che lo attiva**, come il debito del `DocsLink`.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage.

---

## Passo 30 — verifica del riepilogo del coordinatore · 2026-09-18

Il coordinatore manda lo stato che ha di me e chiede di correggere le righe sbagliate.
Misurato riga per riga. Due correzioni, una delle quali è **un buco nella mia evidenza**.

| riga sua | esito |
|---|---|
| `FROZEN` | ✅ |
| **812 righe di spec** | ✅ esatte (`wc -l`) |
| **5 esecuzioni** | 🔴 **sbagliata** → vedi Fuori pista 29 |
| `5 passed / 1 failed`, rosso = test 1 | ✅ **e attuale** → `e2e4` 02:28:16 posteriore a ogni mtime di prodotto |
| test 4 e 6 riparati e falsificati | ✅ |
| coda (`sections`, retarget, primitive, `DocsLink`) | ✅ |

### ⚠️ Fuori pista 29 — **due spec diversi con la stessa riga di risultato**

Corse **del mio** spec: `e2e` 01:45 (4p/2f) · `e2e2` 01:49 (5p/1f) · `e2e3` 02:21 (5p/1f) ·
`e2e4` 02:28 (5p/1f) = **4 complete**, più `break2` 02:23 e `break3` 02:25 filtrate = **6
invocazioni**.

La «quinta corsa completa» del conteggio è **`e2e_risk` 01:50**, che è
**`risk-analysis.spec.ts`** — non mia. Entrambi gli spec hanno **6 test** ed entrambi
danno **`5 passed / 1 failed`**.

> 🔑 **La riga di risultato non nomina lo spec.** Due file diversi producono un banner
> identico. Un conteggio tenuto *per esito* è infondibile: il nome del file è **nel log**,
> **non nel banner**.

Quarto costume della famiglia: stesso nome/denominatori diversi (`coverage`) · stesso
numero/mondi diversi (`check-links` 12 vs 24) · giusta grandezza/referente sbagliato
(`1674`) · **stessa riga di esito/spec diversi**.

### 🔴 Fuori pista 30 — avevo dichiarato `FROZEN` con un cancello statico **stantio di 5 minuti**

| gate | ultima corsa | copre l'albero finale? |
|---|---|:---:|
| e2e | `e2e4` **02:28:16** | ✅ |
| unit | `unit4` **02:28:42** | ✅ |
| format | `format4` **02:29:36** | ✅ |
| **check** | `check7` **02:18:54** | 🔴 **no** |

Ma `correlationHelpers.test.ts` è **02:22:17** e `CorrelationHeatmap.svelte` è **02:24:05**
— entrambi sotto `src/`, **entrambi nel raggio di `svelte-check`**, entrambi **invisibili**
all'ultimo `check`.

**È il fuori pista 14 al rovescio**: quella volta il gate stantio era `format`, e me n'ero
accorto per caso. *«Un verde su tre gate non copre il quarto»* — e stavolta il quarto era
l'unico scoperto.

**Chiuso con un comando** (`front check`, 02:4x → `/tmp/libreFolio_F_check8.log`):

```
svelte-check found 0 errors and 41 warnings in 2 files
```

**Identico a `check7`**, e i due file con warning sono `BrokerSharingPanel.svelte` e
`GlobalSettingsTab.svelte` — deprecazioni `on:click` preesistenti, **nessuno dei due è
mio** (`grep -c` sui miei file: **0**).

> **`api sync` non serviva, e posso dire perché**: `git diff --stat` mostra **zero file
> backend** nel mio delta → l'OpenAPI non è cambiato dalle 01:06, quindi `generated.ts` è
> corrente. La regola *«`api sync` prima di ogni `front check`»* è giusta come default, ma
> quando il diff non ha superficie backend è **una scrittura a vuoto**: dire perché la si
> salta è meglio che eseguirla per riflesso.

### ✅ La scelta di B non è una scelta: è forzata dalla disponibilità

```
cc33120e:frontend/e2e/assets/asset-merge.spec.ts:137  getByTestId('asset-merge-target-select')   ✅ nella baseline
cc33120e:frontend/e2e/portfolio/risk-lab.spec.ts      fatal: exists on disk, but not in cc33120e  🔴 solo mio
```

- **`front-asset asset-merge` → B può e deve**: è nella sua baseline, usa `getByTestId` su
  un testid **custom** — cioè esattamente la forma che il fix parziale spezza in
  strict mode. **Il cancello che ha già disponibile è quello che discrimina.**
- **`front-portfolio risk-lab` → solo io, post-integrazione**: il file **non esiste nel suo
  albero**, e nemmeno la sua registrazione. F-7 visto dall'altro lato.

Non è «l'una o l'altra»: **`asset-merge` rileva il difetto, `risk-lab` prova che la mia
superficie sopravvive.** Due domande diverse, due proprietari diversi.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage, `6245` libera, quattro gate su
quattro sull'albero finale.

---

## Passo 31 — «il lavoro di tutti esiste solo nei worktree»: metà vero · 2026-09-18 02:5x

Il coordinatore misura **il ramo di N** fermo a `cc33120eb` e ne inferisce che *nessuno
degli undici mandati ha committato* e che *il lavoro di tutti esiste solo nei worktree*.

### ✅ Prima metà — confermata, ma **misurata invece che inferita**

```
git branch -v --format='%(objectname:short)  %(refname:short)'
```

**Undici rami su `cc33120eb`**, e sono esattamente i nostri: `risk-management-replan`
(coordinatore) · `risk-oracle-math-migration` (A) · `risk-taxonomy-benchmark` (B) ·
`risk-c-portfolio-slicing` (C) · `risk-primitives-cards` (D) · `vigilant-adventure` (E) ·
`risk-asset-global-lab` (**io**) · `risk-g-allocation-colors` (G) · `h-monte-carlo` (H) ·
`risk-analysis-documentation` (I) · `risk-n-backend-acquisizioni` (N).

> La conclusione regge, ma veniva da **un ramo**. I worktree **condividono i ref**: gli
> undici si leggono in un comando. **Inferire da uno vale finché non costa niente
> misurarli tutti.**

### 🔴 Fuori pista 31 — seconda metà **falsa**, e la falsità ha una conseguenza pratica

```
1 238 ref sotto refs/copilot/checkpoints/     ← 1 232 venti minuti fa: cresce mentre guardo
  385 scritti oggi (09-17 / 09-18)
   27 sessioni distinte, 14 attive oggi
```

La mia sessione `17e18859-…` ha checkpoint alle **02:46, 02:47, 02:49, 02:54** (seq 19-22).
E la prova che chiude la questione:

```
git cat-file -e ee08426f5:frontend/e2e/portfolio/risk-lab.spec.ts   → ✅ esiste, 812 righe
git cat-file -e cc33120e:frontend/e2e/portfolio/risk-lab.spec.ts    → fatal: exists on disk, but not in cc33120e
```

**Lo stesso file, nello stesso momento**: assente dal ramo, **presente nell'object store**.

> ## 🔑 **Il lavoro non è nei worktree: è nell'object store. I *rami* sono fermi, i *commit* no.**

### 📌 La conseguenza: il confine della regola dello SHA non è quello che credevo

Avevo dato la regola pensando che uno SHA esistesse **quando una sessione aveva
checkpointato**. Invece **ogni sessione checkpointa in continuazione** — 385 oggi. Quindi:

| | leggibile con uno SHA? |
|---|:---:|
| codice tracciato, non committato su ramo | ✅ **sempre** |
| artefatto **ignorato** (`generated.ts`, `openapi.json`) | 🔴 **mai, da nessun albero** |

**Il confine non è «committato vs non committato»: è «tracciato vs ignorato».** La metà
ignorata l'avevo già trovata a `1a537f9cb`; questa chiude l'altra.

**Ricaduta operativa**: la lettura diretta del worktree di N — fatta stamattina dal
coordinatore *«dichiarando fonte, momento e stato non committato»* perché credeva non
esistesse uno SHA — **era evitabile**. Il meccanismo è universale e dimostrato sulla mia
sessione; il coordinatore ha l'ID di sessione di N e lo trova in un comando
(`git for-each-ref refs/copilot/checkpoints/ | grep <prefisso> | tail -1`, scoperta di B).
⚠️ Non ho **misurato** i checkpoint di N: non conosco il suo ID. Provo il meccanismo, non
il caso singolo.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage, `6245` libera.

---

## Passo 32 — 🔴 il rosso `asset global` **l'ho causato io**, e la cura sta arrivando da B · 2026-09-18 03:2x

La correzione del coordinatore sull'indirizzo `:201` («è tuo, non di B») è giusta, e
tirandone il filo si arriva a una **correzione di una mia affermazione ripetuta due volte**.

### La catena, misurata

```
BASELINE  AssetSetRiskPanel:135  <SearchSelect … testId="risk-asset-add-select">   ← DIRETTO
          → SearchSelect accende tutti e cinque gli id, compreso :377 `${testId}-trigger`

IL MIO    AssetSetRiskPanel:201  <AssetSelect  … testid="risk-asset-add-select">   ← D73
          → AssetSelect baseline :123 mette l'id su un <div> wrapper
          → :124 <SearchSelect> SENZA testId  →  `-trigger` SPENTO
```

E il rosso lo dice con parole sue (`/tmp/libreFolio_F_e2e_risk.log`):

```
✘ risk-analysis.spec.ts:628 … asset global maps broker holdings and supports remove/add (30.1s)
    - waiting for getByTestId('risk-asset-add-select-trigger')
```

**30,1 s = timeout, non asserzione.** Il locatore non risolve nulla.

> 🔑 Avevo riportato due volte quel rosso come *«il test che eredito con K5»*. **Il test lo
> eredito; il guasto l'ho causato io con D73.** *La proprietà del file non è la proprietà
> della causa.*

### ⚠️ Fuori pista 32 — **uno spec nato dopo la perdita non può accorgersene**

Nel mio `risk-lab.spec.ts` raggiungo il trigger con `.locator('[role="combobox"]')`.
**L'ho scritto perché l'id semantico era già spento — da me, un'ora prima.** Ho inventato
un selettore strutturale per rimpiazzare uno semantico **che non ho mai visto vivo**.

> **Una migrazione a un wrapper "migliore" può spegnere in silenzio la superficie di test
> di ciò che avvolge.** Non è una misura stantia: è **una superficie la cui affordance è
> stata distrutta prima che nascesse il test che l'avrebbe usata.** Lo spec non può
> rimpiangere ciò che non ha mai visto.

### 📌 Previsione falsificabile — **deliberatamente parziale**

Dopo l'integrazione di F30 (B, `590f32ae6`: inoltro **e** rimozione):

| riga | cosa | dopo B |
|---|---|:---:|
| `:652` | `risk-asset-add-select-trigger` | ✅ **guarisce** |
| `:653` | `search-select-option-{id}` — prefisso **statico** a `SearchSelect:473`, non derivato da `testId` | ✅ sempre esistito |
| `:654` | `risk-asset-add-button` | 🔴 **resta rosso** |

`risk-asset-add-button` era alla **baseline `:138`**; la mia riscrittura l'ha **rimosso**
(aggiunta in un passo solo: `onchange={addAsset}` a `:201`). `grep` sul prodotto: **assente**.
Unico utente: `risk-analysis.spec.ts:654`.

> ## 🔴 **Il rosso si SPOSTA, non si spegne.** Chi rieseguirà `front-portfolio risk` dopo
> l'integrazione vedrà ancora `asset global` rosso e potrà concludere che F30 **non ha
> funzionato**. Ha funzionato: il rosso è avanzato di due righe.

La riparazione di `:654` non è di B ed è una **decisione di prodotto mia** (un passo invece
di due) → appartiene alla riassegnazione K5 di quel test, cioè a **E**.

✅ E il corollario del coordinatore è giusto: dopo l'integrazione
`getByTestId('risk-asset-add-select-trigger')` sostituisce `.locator('[role="combobox"]')`
in `ensureSelectionAtLeast` (`:428-436`) — **e ora so perché torna disponibile**.

**Stato**: `FROZEN`. HEAD `cc33120e`, niente in stage, `6245` libera.
