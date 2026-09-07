# 15 — Esecuzione S1–S3

> **Report di cronaca, non di audit.** I report 01–13 documentano *cosa hanno trovato* gli
> audit di codice e mkdocs. Il report [14](14_backlog_per_complessita.md) riordina quei
> reperti *per complessità e rischio*. Questo report racconta cosa è successo quando, il
> 2026-08-05, la banda S1–S3 di quella classificazione è stata **eseguita**: 32 interventi
> chiusi in un solo ciclo, le correzioni che l'esecuzione ha imposto ai reperti stessi
> dell'audit, e le lezioni trasversali che ha lasciato in eredità.

---

## Sintesi

Le tre lezioni trasversali, non l'elenco degli interventi, sono il contenuto che vale la
pena portarsi via da questo ciclo. Non sono tre aneddoti isolati: sono emerse da voci del
backlog scritte da persone diverse, in momenti diversi, e si sono rivelate essere **la
stessa forma di problema** vista da tre angolazioni indipendenti.

1. **Le misure di codice morto dipendono dall'ordine in cui si eseguono i passi.** Un
   barrel morto (un `index.ts` che si limita a ri-esportare) tiene artificialmente in vita
   i simboli che ri-esporta. Qualunque elenco di orfani calcolato *prima* di aver rimosso
   i barrel morti non è attendibile — ed è esattamente per questo che la voce 3.7 è
   passata da 8 (dichiarati dall'audit) a 12 (effettivamente esportati, una volta
   rimossi i barrel) a 9 (il numero vero, misurato *dopo* con knip rieseguito da capo).
2. **Un test che verifica un contenitore invece del contenuto passa anche quando la
   funzionalità è rotta.** Si è ripresentato **due volte, indipendentemente**: nella voce
   2.5 (una guardia di test troppo larga che non poteva mai fallire) e nella regressione
   del grafico a mezza ciambella (un'asserzione E2E su un `<div>` involucro che restava
   visibile intorno a un grafico vuoto). Due istanze indipendenti della stessa forma di
   difetto non sono una coincidenza: sono un pattern.
3. **Una capacità può sparire dentro un redesign senza che nulla se ne accorga.** La
   striscia `LiveTicker` in dashboard è stata rimossa nel commit `6c009e6b` senza che
   alcun test fallisse e senza che alcun messaggio di commit registrasse la decisione. È
   riemersa solo perché il componente è sopravvissuto come orfano e l'utente lo ha
   riconosciuto. Il report [16 — Feature perse nei redesign](16_feature_perse_nei_redesign.md)
   indaga quanto questo fenomeno sia diffuso nel resto del progetto.

Le tre lezioni sono sviluppate per intero, con le prove, nell'ultima sezione di questo
report. Tutto il resto documenta il lavoro che ci ha portato a scriverle.

### I numeri

| Voce | Valore |
|---|---:|
| Interventi chiusi in questo ciclo | **32** |
| — dal backlog di codice trasversale ([14](14_backlog_per_complessita.md): 25 in banda S1–S3 + 2 fuori banda) | 27 |
| — dal Blocco 1 dell'audit mkdocs, netti e non sovrapposti al backlog di codice | 4 |
| — regressione segnalata dall'utente durante il ciclo | 1 |
| Agenti paralleli impegnati, più la passata di chiusura | 9 + 1 |
| Reperto rivelatosi nullo durante l'esecuzione | 1 (`1.2`) |
| Voci lasciate aperte deliberatamente o per lavorazione parallela concorrente | 4 (`1.5`, `2.2`, `3.8`, `3.9`) |
| Scoperte non anticipate da alcun report | 2 (`FxProviderConfig.svelte`, `LiveTicker.svelte`) |
| Correzioni di gravità o attribuzione imposte ai reperti dell'audit | 5 |

---

## Come è stato partizionato il lavoro

Il meccanismo che ha reso sicura l'esecuzione in parallelo non è stato un coordinamento in
tempo reale fra gli agenti: è stata la **proprietà disgiunta dei file**. 9 agenti paralleli
hanno ricevuto ciascuno un sottoinsieme di voci che non toccava file in comune con nessun
altro agente assegnatario, così che due agenti non potessero mai proporre due modifiche
incompatibili sullo stesso file nello stesso momento. Una decima passata di chiusura ha poi
verificato l'insieme — coerenza fra le voci chiuse, esecuzione delle voci trasversali non
assegnabili a un solo agente (la correzione di licenza tocca sia `pyproject.toml` sia
`frontend/package.json`, ad esempio), e la raccolta delle evidenze di verifica riportate
più sotto.

Le voci chiuse sono state **32**, non le 30 della banda S1–S3 di [14](14_backlog_per_complessita.md):
**27** vengono dal backlog di codice trasversale — le 25 chiuse dentro la banda assegnata
più le 2 chiuse fuori banda come effetto collaterale (`4.5`, `5.6`, vedi più sotto) — **4**
vengono dal Blocco 1 della tassonomia dell'audit mkdocs
([`08-functionality-gap-taxonomy.md`](mkdocsAudit/08-functionality-gap-taxonomy.md): `05 A3`,
`05 B1`, `03 F2`, `03 F3`), e **1** è la regressione del grafico a mezza ciambella,
segnalata dall'utente durante il ciclo stesso e chiusa nello stesso giro.

> La quinta voce del Blocco 1 mkdocs marcata come implementata, `05 A1`, **non è un
> intervento aggiuntivo**: è lo stesso difetto già censito come voce `2.4` del backlog di
> codice (`api/v1/auth.py:189` — l'interruttore "Allow new user registration" esposto in
> UI e mai controllato da `register()`). Due audit indipendenti, uno documentale e uno di
> codice, sono convergenti sulla stessa riga; contarla due volte avrebbe gonfiato
> artificialmente il totale.

---

## Backend

Le correzioni di quest'area erano tutte tracciate: nessuna ha richiesto una decisione di
prodotto, solo la verifica che il sostituto esistesse davvero.

- **`main.py:253`** — il task di pre-warm dei provider, creato con `asyncio.create_task()`
  e mai assegnato a una variabile, poteva essere raccolto dal garbage collector a metà
  esecuzione. Ora viene aggiunto a un insieme a livello di modulo, `_background_tasks`,
  con una callback `add_done_callback(_background_tasks.discard)` che lo rimuove alla
  conclusione — il pattern raccomandato per i task *fire-and-forget* di `asyncio`.
- **`uploads.py:377`** — l'unica violazione della *Async I/O Rule* del progetto: un
  `open()` sincrono dentro un handler `async def`, che bloccava l'intero event loop per
  la durata della lettura del file. Avvolto in `await asyncio.to_thread(...)`.
- **11 `S110`** (`try`/`except`/`pass` silenziosi) in `system.py` (×3), `utils/version.py`
  (×2), `yahoo_finance.py` (×2), `asset_source.py` (×2), `provider_registry.py` e
  `uploads.py` — tutti convertiti in eccezioni loggate. `S110` in `backend/app/` è ora
  **0**, verificato con `ruff check --select S110`.

  > I due `S110` di `utils/version.py` stanno entrambi in poche righe (lettura della
  > versione da file e da `git describe`, con fallback silenzioso se nessuna delle due
  > fonti è disponibile): sono il caso in cui il silenzio era più difendibile, ma anche
  > quello in cui un log di debug costa nulla e spiega perché la versione mostrata è
  > quella di fallback.

- **Il blocco pre-engine di `portfolio_service.py`** — l'audit aveva stimato ~156 righe
  su 6 simboli; la rimozione reale è stata più ampia perché copriva anche i test:
  **−130 righe** di codice sorgente e **−176 righe di test**, 306 in totale. Ogni simbolo
  è stato tracciato uno per uno nel proprio sostituto dentro
  `PortfolioCalculationEngine.build_history()` prima di essere rimosso.
- **Sette rimozioni con assorbimento citato individualmente**: `get_optional_user`
  (nessun endpoint a visibilità mista lo richiedeva), `get_session_ttl_sync` /
  `get_session_ttl` (sostituite da `global_settings_service.get_session_ttl_hours`),
  `valuation_price` / `valuation_price_ccy` (alias di compatibilità rimasti senza
  chiamanti), `signed_quantity_by_broker` (idem), `unique_computation_count` (era
  letteralmente `len(self.computations)` — il campo è pubblico e vivo, non serviva un
  metodo dedicato per leggerlo), `transitive_dependencies` (una DFS topologica che vive
  40 righe sotto `_detect_cycles`, una DFS viva sullo stesso identico grafo: due visite
  dello stesso grafo, una usata e una no) e `summary_position_count`.

### La licenza — il primo intervento non è tecnico

Quattro righe di metadati in `pyproject.toml` dichiaravano `MIT` su un progetto `AGPL-3.0`,
insieme a una versione (`0.6.x`), un vincolo Python (`>=3.11`) e una maturità (`Alpha`)
tutti disallineati dallo stato reale del progetto. Corretti in `AGPL-3.0` / `1.1.0` /
`>=3.13` / `Beta`.

> **Il primo tentativo ha introdotto un errore secondario, corretto nello stesso ciclo.**
> La prima scrittura del classifier Trove ha usato una stringa che **non esiste**
> nell'elenco ufficiale PyPI: `...v3 or later`. L'elenco ammette solo `License :: OSI
> Approved :: GNU Affero General Public License v3` oppure `... v3 or later (AGPLv3+)` —
> due varianti distinte, non intercambiabili a piacere. Corretto in `...v3`, **senza**
> "or later": è quanto dichiarano già `LICENSE`, `README.md:193` e le quattro pagine
> `credits-legal.*.md` in tutte le lingue pubblicate. Un secondo controllo dopo la
> correzione ha confermato che il classifier ora scritto in `pyproject.toml` corrisponde
> esattamente a quella stringa.

`frontend/package.json` dichiarava la stessa versione superata (`0.6.x`) ed è stato
allineato a `1.1.0` nello stesso passaggio, perché è il secondo punto del repository in
cui la versione del progetto è dichiarata in metadati letti da strumenti automatici.

---

## Frontend

- **13 barrel morti** rimossi, sostituiti da import diretti: i **12** che il report 09
  elencava già (11 sotto `components/` più `src/lib/index.ts`) più
  `tanstack-table/index.ts`, che nell'elenco non c'era.
- **`src/lib/tanstack-table/`** rimossa insieme alla dipendenza `@tanstack/table-core`:
  assorbita dall'implementazione tabelle propria del progetto sotto `components/ui/`.
- **`HoldingsPanel.svelte`** → assorbito da `PositionsPanel.svelte`, che espone la stessa
  vista "Holdings / Table" più altre tre viste.
- **`BrokerImportFiles.svelte`** → assorbito da `BrokerImportFilesModal.svelte`.
- **`e2e/fixtures/db-helpers.ts`** rimosso, orfano.
- **9 bandiere `isXLoaded` / `isXLoading`** morte rimosse (il numero vero, non le 8
  dichiarate — vedi la prima lezione). Fra le nove, `isLoggedIn` non era nemmeno una
  bandiera di caricamento ma un predicato di autenticazione finito nell'elenco per
  somiglianza di nome: rimovibile perché `isAuthenticated = derived(auth, $auth.user !==
  null)` (`stores/app/auth.ts:225`) codifica già la stessa cosa, usata in
  `routes/(app)/+layout.svelte:97,112`. `isCurrenciesLoaded` è invece viva — usata da
  `currencyGraphStore.ts` — ed è stata **tenuta**. Bonus nella stessa rimozione:
  `getConfiguredCurrencies` in `fxRoutesStore.ts`, superata da
  `getConfiguredCurrencySet()` / `getConfiguredPairSlugs()`, che sono ciò che i
  consumatori reali usano.
- **Gli helper di staleness dell'AI Export** superati da `PreparationContext` e dalla
  funzione `isPreparationContextCurrent()` in `AiExportMenu.svelte`, che incapsulano lo
  stesso controllo in un unico punto invece di tre helper sparsi.
- **6 dipendenze npm inutilizzate** rimosse. `katex` è stata **tenuta** — è usata da
  `inlineMath.ts` e `FilePreviewModal.svelte` — mentre `@types/katex` è stata rimossa
  perché katex v2 include già i propri tipi. `package-lock.json` resta da rigenerare.

---

## Le due scoperte che nessun report conteneva

Sono emerse solo perché la rimozione dei 12 barrel morti ha smesso di tenerle
artificialmente in vita nel grafo delle dipendenze — la stessa causa della prima lezione
trasversale, qui applicata a due decisioni di prodotto invece che a un conteggio.

**`FxProviderConfig.svelte`** (314 righe) era il pannello inline con la vista d'insieme
delle rotte FX e le relative priorità. L'audit lo aveva classificato come orfano da
discutere: o era una regressione, o la capacità era stata spostata altrove senza lasciare
traccia verificabile. **L'utente ha rivisto personalmente il caso e confermato la
rimozione**: la capacità si è spostata in `FxPairAddModal` in `editMode` (invocato da
`fx/[pair]/+page.svelte:985` e montato a `:1320`, con il commento nel file stesso che lo
documenta già alla riga 11 — *"Provider Config: via modal (not inline panel)"*) →
`ui/select/FxProviderSelect.svelte`. Il sostituto è un **superset stretto** del
componente rimosso: mantiene il riordino per priorità via drag-and-drop
(`OrderableList`) e le rotte dirette/a catena, e aggiunge pathfinding DFS fino a
profondità 4 (`currencyGraph.ts`, `findAllPaths(..., maxDepth = 4)`), ricerca full-text e
una barra informativa sui provider. Nessuna capacità è andata perduta — l'interfaccia si
è spostata da un pannello inline a un modale, ed è per questo che l'utente se lo
ricordava diversamente.

**`LiveTicker.svelte`** (233 righe) erano le etichette di prezzo live con polling ogni
30 secondi. La sua capacità sopravvive nelle pagine asset (`assets/+page.svelte:355`,
`assets/[id]/+page.svelte:954,1300` — stesso intervallo, stesso `livePriceService.ts`) e
`AssetPriceSummary.svelte` oggi mostra più informazioni del vecchio badge. **Ma la
striscia in dashboard è stata genuinamente perduta** — vedi la terza lezione
trasversale più sotto per la ricostruzione completa. L'utente ha rivisto il caso e ha
scelto di **non ripristinarla**, chiedendo invece un miglioramento correlato sulla pagina
di dettaglio asset.

---

## La regressione: il grafico a mezza ciambella

Segnalata dall'utente durante il ciclo stesso, nel pannello di condivisione broker: il
grafico a mezza ciambella (`SemiDonutChart.svelte`) a volte non si disegnava affatto,
lasciando visibile solo l'involucro vuoto attorno a sé.

**Causa radice**: `SemiDonutChart.svelte` è in modalità runes e il suo `$effect` era
condizionato su `if (chartContainer && data)`. Un array è sempre truthy in JavaScript, per
cui quella condizione non registrava mai una dipendenza reale sul *contenuto* dell'array —
solo sulla sua esistenza. Quando il genitore, ancora in modalità legacy, riassegnava le
fette del grafico, l'effetto non si riattivava mai, perché per Svelte l'array era "lo
stesso" di prima.

**Il fix** prende un'istantanea reale (`data.map((slice) => ({...slice}))`) prima di
usarla nel corpo dell'effetto, così che la dipendenza sia genuinamente tracciata sui
valori e non sull'identità del contenitore. Nello stesso intervento sono state
irrobustite due race condition latenti, scoperte verificando il fix:

- una **guardia di generazione di rendering** (`renderGeneration`), incrementata a ogni
  nuovo giro dell'effetto, in modo che un caricamento asincrono di un avatar circolare
  superato da un rendering successivo non possa più chiamare `setOption` su un'istanza
  ECharts ormai sostituita o disposta;
- un'attesa di un contenitore a dimensione non nulla prima di `echarts.init`, così da non
  inizializzare mai il grafico in un `<div>` ancora a larghezza zero durante il primo
  render.

Il test E2E (`frontend/e2e/brokers/broker-sharing.spec.ts`) non asseriva più sul `<div>`
involucro — che restava visibile a prescindere dal contenuto del grafico, esattamente il
difetto della seconda lezione trasversale — ma sul `<canvas>` di ECharts stesso, con
dimensioni CSS e bitmap non nulle verificate via `boundingBox()` ed `evaluate()`, sui tre
percorsi in cui il pannello viene montato: inline nella scheda "Info" del dettaglio
broker, dentro `BrokerSharingModal`, e in dark mode.

---

## Escluso da questo ciclo, deliberatamente

- **`1.5`** — mettere `TRY003` in `ignore` in `pyproject.toml` è condizionale
  all'adozione della regola `TRY` in ruff, e quella decisione non è stata presa in questo
  ciclo. I 515 `TRY003` dell'AI Export sono messaggi diagnostici dentro eccezioni già
  tipizzate: adottare `TRY` senza questa esclusione cancellerebbe 515 messaggi utili in
  un colpo solo.
- **`2.2`** — la chiamata `get_global_setting(self.db, "base_currency", "EUR")` in
  `portfolio_engine.py:1947` (spostata da `:1960` per effetto delle rimozioni di `3.2` e
  `2.7` nello stesso file). L'utente ha chiesto di discuterla a parte, e a ragione: la
  riga contiene **tre difetti distinti**, non uno solo.
  1. La firma reale è `get_global_setting(key: str, session: AsyncSession)` — due
     parametri, in quest'ordine — mentre la chiamata passa `self.db` al posto di `key`,
     `"base_currency"` al posto di `session`, e un terzo argomento posizionale in più
     (`"EUR"`) che la funzione non accetta affatto: un `TypeError` garantito ogni volta
     che il ramo di fallback viene raggiunto.
  2. È il registro sbagliato: la funzione da usare per leggere un'impostazione con un
     valore di default è `get_setting_value(session, key, default)`, che vive in
     `global_settings_service.py:30` — un modulo diverso da quello effettivamente
     importato.
  3. È la chiave sbagliata: fra i global settings esiste `"default_currency"`
     (`schemas/settings.py:131`), non `"base_currency"`. `base_currency` è invece una
     colonna **per-utente** (`db/models.py:343`). Anche corretti i primi due problemi,
     la valuta base configurata a livello globale resterebbe silenziosamente ignorata a
     favore del fallback `"EUR"` hardcoded.

  > **`5.2` è la stessa riga di `2.2`.** Il backlog di [14](14_backlog_per_complessita.md)
  > la elenca due volte sotto tier di complessità diversi — come bug puntuale in S2 e
  > come decisione di semantica di prodotto in S5 — perché è entrambe le cose insieme:
  > un difetto meccanico che non si può correggere senza prima scegliere quale delle due
  > chiavi/semantiche è quella voluta.

- **`3.9`** — `git rm fifo_utils.py`, l'unica rimozione a rischio medio dell'intero
  backlog nonostante sia l'azione più atomica possibile: un errore qui non produce
  un'eccezione, produce un **costo di carico sbagliato** in un portafoglio reale.
  Bloccata su `4.2` (verifica dei casi limite FIFO sull'engine), non ancora eseguita.
- **`3.8`** — rimuovere i test orfani insieme al codice che coprono è in lavorazione in
  un ciclo parallelo concorrente a questo, non confermata chiusa da questa esecuzione.

---

## Ancora fuori dalla banda S0–S3

Il resto del Blocco 1 dell'audit mkdocs e le voci S4–S6 del backlog di codice restano
aperte, fuori dallo scopo di questo ciclo:

| Voce | Descrizione | Tier |
|---|---|:---:|
| `02 F6` | eToro importa XLSX | S4 |
| `01 R-11` | Preferenza Date Format | S4 |
| `02 F4` | Quota percentuale assegnabile anche a Editor | S5 |
| `03 F4` | Tre task AI Export FX documentati, il catalogo reale ne contiene due | S5 |
| `06A R-03` | Policy costo zero per ADJUSTMENT senza override | S5 |
| `02 F3` | Generic CSV — transazioni composte (`TRANSFER`, `FX_CONVERSION`, `CASH_TRANSFER`) | S6 |
| `06B B1` | `compoundingFrequency` sul benchmark composto | S6 |
| `06C F1` | Split K/R di `CASH_TRANSFER` | S6 |

Resta anche una correzione solo editoriale, non di remediation, per il prossimo batch
documentale: `cli_tools.en.md:24-25` descrive ancora `--workers` con il comportamento
manuale precedente, e va allineato ora che il comportamento CPU-based di `05 B1` è stato
implementato.

---

## Evidenze di verifica

| Comando / controllo | Esito |
|---|---|
| `./dev.py lint` | 36 errori (35 `PLC0415` + 1 `B905`) — baseline invariata rispetto all'apertura dell'audit |
| `ruff check --select S110 backend/app/` | **0** |
| `./dev.py test services all` | 60/60 |
| `./dev.py front check` | 0 errori, 0 warning |
| `npx vitest run` | 45 file, 415 test |
| `./dev.py test front-user broker-sharing` | 15/15 |
| `./dev.py test front-fx fx-csv-import` | 21/21 |
| knip, file frontend inutilizzati | da 20 a 1 |
| knip, dipendenze npm inutilizzate | da 6 a 0 |

---

## Nota sull'ambiente, per chi ripete questa esecuzione

Due problemi hanno costato tempo di debug reale durante questo ciclo, entrambi con lo
stesso sintomo fuorviante — un `no such table` che non ha nulla a che fare con lo schema:

- Un server di test backend rimasto attivo sulla porta `6041` fa rifiutare
  `db create-clean`; dopo il rifiuto, ogni test backend fallisce con un fuorviante `no
  such table`, che sembra un problema di migrazione ma è solo un database che non è mai
  stato ricreato. Rimedio: usare `TEST_PORT=6059` per non collidere con il residuo.
- Eseguire Playwright in concorrenza con la suite backend API ricrea il database di test
  sotto ai piedi della suite backend in corso, producendo la stessa firma di fallimento
  fuorviante.

---

## Le tre lezioni trasversali

### 1 — Le misure di codice morto sono dipendenti dall'ordine di esecuzione

I barrel morti — file `index.ts` che si limitano a ri-esportare simboli di una cartella —
tengono artificialmente in vita ciò che ri-esportano agli occhi di uno strumento di
analisi statica: finché il barrel esiste, importare (anche solo teoricamente, anche se
nessun altro file lo fa davvero) *attraverso* di esso rende il simbolo "raggiungibile", e
uno strumento come knip non lo segnala come orfano.

Questo è esattamente ciò che è successo alla voce `3.7`: il rilievo originale dell'audit
dichiarava 8 bandiere `isXLoaded` / `isXLoading` morte. Una volta rimossi i barrel
(voce `3.1`) e rieseguito knip **da capo**, l'elenco reale delle bandiere esportate era
di 12, non 8 — la prima misura era stata fatta mentre i barrel morti ne nascondevano
alcune dietro un falso "in uso". Solo una seconda misura, eseguita *dopo* la rimozione
strutturale, ha prodotto il numero vero: **9** bandiere davvero orfane.

**La regola operativa**: dopo qualunque rimozione strutturale che tocchi il grafo delle
dipendenze (barrel, moduli di re-export, alias), l'elenco degli orfani va **ricalcolato
da zero** — mai riusato quello calcolato prima. Un numero di codice morto calcolato prima
di una rimozione strutturale non è una stima prudente per difetto: è un numero che
descrive un grafo delle dipendenze che non esiste più.

### 2 — Un test sul contenitore, non sul contenuto, non protegge nulla

Questa lezione si è manifestata **due volte, in modo indipendente**, in due parti
diverse del ciclo:

- **Voce `2.5`**: la guardia `'"fast"'` in `test_signal_plugins_close_only.py:107`
  controllava una condizione troppo ampia — non poteva mai fallire, a prescindere da cosa
  facesse davvero il plugin sotto test. Era l'unico test rosso del progetto, ma non per
  un difetto del codice: per un test che, restringendo la guardia a `params_schema`, ha
  smesso di dare un falso negativo.
- **La regressione del grafico a mezza ciambella**: l'asserzione E2E originale verificava
  la visibilità di un `<div>` involucro attorno al grafico — un elemento che resta nel
  DOM e resta visibile **a prescindere** dal fatto che ECharts abbia effettivamente
  disegnato qualcosa al suo interno. Il grafico poteva restare vuoto per intere sessioni
  di test senza che nulla se ne accorgesse.

In entrambi i casi la forma del difetto è identica: **l'asserzione verifica che
"l'involucro esiste", non che "il contenuto atteso è dentro l'involucro"**. Un contenitore
esiste sempre, appena viene montato; il contenuto che dovrebbe esserci dentro è la parte
che può davvero rompersi, ed è l'unica che vale la pena verificare. Due istanze
indipendenti — un test unitario di backend e un test E2E di frontend, su due
sottosistemi che non condividono codice — non sono una coincidenza: sono la prova che
questa è una **forma di difetto ricorrente**, non un incidente isolato. Vale la pena
cercarla anche altrove nella suite, non solo dove si è già manifestata.

### 3 — Una capacità può sparire dentro un redesign senza che nulla se ne accorga

`LiveTicker.svelte` era un componente reale, introdotto deliberatamente (commit
`2c448cd2`, *"feat: LiveTicker component + Yahoo Finance current-price optimization"*) e
montato nella pagina Dashboard. Il commit `6c009e6b`, *"feat(dashboard): add Dashboard
Home page + portfolio ROI series"*, ha riscritto la pagina Dashboard introducendo
`KpiCard`, `GrowthChart`, `RecentTransactionsPanel` e `portfolioStore` — e nello stesso
diff ha rimosso sia l'import sia il montaggio di `<LiveTicker />`. Il messaggio di quel
commit descrive in dettaglio ogni componente **aggiunto**; non menziona in alcun modo
la rimozione della striscia prezzi live.

Nessun test è entrato in rosso: non esisteva (e tuttora non esiste) un test che
verificasse la presenza della striscia prezzi in dashboard, quindi la sua sparizione non
aveva alcun modo strumentale di essere rilevata. L'unico segnale rimasto è stato il
componente stesso, che è sopravvissuto sul filesystem come file orfano — tre commenti al
suo interno lo descrivevano ancora come montato in Dashboard — finché l'audit di codice
morto non lo ha segnalato e l'utente, leggendo il reperto, lo ha riconosciuto come una
capacità che ricordava di aver avuto e non vedeva più.

**Questo è il punto**: la rete di sicurezza che ha permesso di *notare* la perdita non è
stata scritta per quello. È stato un sottoprodotto casuale di un audit di codice morto
fatto per un motivo completamente diverso (trovare astrazioni non referenziate, non
regressioni di prodotto). Se il commit `6c009e6b` avesse anche cancellato il file
`LiveTicker.svelte` invece di lasciarlo come orfano sul filesystem — o se questo audit
non fosse mai stato fatto — la perdita sarebbe rimasta invisibile a tempo indeterminato.
Quante altre capacità sono uscite allo stesso modo da un redesign, senza lasciarsi dietro
nemmeno un file orfano da notare, è la domanda a cui risponde
[16 — Feature perse nei redesign](16_feature_perse_nei_redesign.md).

---

*Report 15 di 16 — cronaca dell'esecuzione S1–S3. Torna a [`INDEX.md`](INDEX.md) ·
prosegue in [16 — Feature perse nei redesign](16_feature_perse_nei_redesign.md).*
