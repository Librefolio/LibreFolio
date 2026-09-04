# 16 — Feature perse nei redesign: caccia sistematica al pattern

> Ambito: intero `frontend/` (componenti, e2e, i18n, store, routing) + superficie API in `backend/app/api/v1/` letta in sola lettura come termine di paragone. Nessun file di codice è stato modificato per produrre questo report: analisi statica, grep mirati, lettura diretta dei componenti e archeologia con `git log`/`git show`.
> Gravità massima: 🔴

## Sintesi

Il punto di partenza di questa caccia sono due casi già confermati, con una forma identica: **una capability sparisce durante un refactor o un redesign, nessun test si accorge di nulla, e nessuno annota se la sparizione è voluta**. Il compito era verificare se si tratta di un incidente isolato (due bug sfortunati) o di un pattern strutturale del progetto.

La risposta, dopo aver setacciato sistematicamente quattro assi (test container-vs-content, archeologia dei redesign via git, superficie UI orfana, trappole di reattività identiche al bug originale), è che **non è un incidente isolato**. Ho trovato due componenti chart con lo *stesso identico difetto di codice* del bug del semi-donut, ancora presenti e non corretti nel branch; un secondo caso concreto di capability persa in un redesign (scorciatoia di cassa nella pagina broker, sparita nello stesso commit che ha eliminato il suo componente); e un'asserzione di test talmente vuota da essere quasi comica — letteralmente non può fallire, qualunque cosa succeda all'applicazione. Sul fronte della superficie orfana (i18n, endpoint API, store, routing) l'esito è invece prevalentemente pulito, con una sola eccezione minore già ben documentata da un altro commit.

La lezione di fondo, che ripropongo nella sezione finale, è sempre la stessa dei due casi originali: **il problema non è mai il refactor in sé, è la mancanza di un'asserzione che guardi il contenuto invece del contenitore, e la mancanza di una riga nel commit message che dica "ho rimosso X".**

## Metriche

| Asse | Ambito setacciato | Reperti utili | Reperti scartati (falsi positivi) |
|---|---|---|---|
| 1 — Test container-vs-content | 100+ file in `frontend/e2e/**` | 7 (2 🔴, 4 🟡, 1 🟢) | — |
| 2 — Capability perse nei redesign | ~15 commit di refactor/redesign di grande diff, cronologia `.svelte` cancellati | 2 confermati con evidenza forte, 1 ipotesi debole | 2 (endpoint "spariti" che in realtà sono stati sostituiti, non perduti) |
| 3 — Superficie orfana | 2328 chiavi i18n foglia in `en.json`, 110 alias API generati, store in `frontend/src/lib/stores/`, `Sidebar.svelte` | 1 minore (22 chiavi i18n orfane, già spiegate da un commit documentato) + 1 endpoint mai collegato | 169 chiavi `risk.*` (falso positivo: uso dinamico `` $t(`risk...${x}`) ``), 1 endpoint duplicato non perso |
| 4 — Trappole di reattività identiche | 16 componenti chart in `frontend/src/lib/components/charts/` | 2 componenti con la stessa identica forma del bug originale | — |

## Le due istanze confermate (richiamo)

Prima di passare ai nuovi reperti, riassumo le due istanze che hanno innescato questa caccia, perché sono il metro di paragone per tutto il resto.

**Istanza 1 — il grafico a semi-ciambella.** `SemiDonutChart.svelte`, usato dal pannello di condivisione broker, aveva un `$effect` (Svelte 5, runes) che leggeva l'array `data` solo dentro un controllo di verità: `if (chartContainer && data)`. Un array è sempre "vero" anche se vuoto o non cambiato di riferimento in modo tracciabile: l'effetto non si riagganciava mai davvero al contenuto, e non si ri-eseguiva quando il genitore (in legacy mode, `export let`/`$:`) riassegnava i dati. Il grafico spariva silenziosamente. **Verificato**: nell'albero di lavoro attuale (diff non committato) il componente è **già stato corretto** — il nuovo codice legge `data.map(...)` in modo sincrono dentro l'effetto (per forzare un aggancio reale al contenuto), aggiunge un contatore `renderGeneration` incrementato a ogni esecuzione dell'effetto, e verifica `generation !== renderGeneration || instance.isDisposed()` dopo ogni `await` prima di toccare l'istanza del grafico. Questo pattern corretto è il metro di paragone che uso in tutto l'Asse 4.

Nessuno se n'era accorto perché il test e2e (`broker-sharing.spec.ts`, prima dell'intervento di un altro agente della flotta) asseriva solo `getByTestId('ownership-chart-section')).toBeVisible()` — un contenitore che resta visibile anche a grafico completamente vuoto, perché contiene anche una sovrapposizione testuale. **Il test verificava il contenitore, non il contenuto.** Oggi lo stesso file usa un helper `expectOwnershipChartCanvas()` (righe 56-74) che verifica che esista un `<canvas>` con dimensioni non nulle: è il pattern di riferimento che cito ripetutamente nell'Asse 1.

**Istanza 2 — il ticker dei prezzi live.** `LiveTicker.svelte` mostrava una striscia di badge con prezzi live, con polling ogni 30 secondi. I suoi punti di utilizzo documentati erano la Dashboard e `AssetPriceSummary`. Ho verificato con `git show 6c009e6b^:.../dashboard/+page.svelte` che `<LiveTicker />` era presente nella Dashboard **prima** del commit `6c009e6b` ("feat(dashboard): add Dashboard Home page + portfolio ROI series...") e **assente dopo**; il messaggio del commit non menziona mai la rimozione. Oggi `dashboard/+page.svelte` non contiene più alcun riferimento al ticker. L'utente se n'è accorto solo quando abbiamo proposto di eliminare il componente ormai orfano — se lo ricordava ancora in uso. **Una capability visibile all'utente è sparita dentro un redesign, senza che nessun test fallisse e senza traccia della decisione.**

La nota metodologica cruciale di questi due casi: l'istanza 2 è stata individuabile solo perché il componente stesso è sopravvissuto come orfano (uno scanner di codice morto lo avrebbe trovato). I casi in cui il refactor elimina *sia* il componente *sia* il suo punto di chiamata nello stesso commit non lasciano alcun orfano: si trovano solo con l'archeologia di git, non con un semplice grep. Questo è esattamente il caso che ho trovato nell'Asse 2 (vedi B1 più sotto).

---

## Asse 1 — Test che verificano il contenitore, non il contenuto

Ho setacciato `frontend/e2e/**` cercando asserzioni che passerebbero anche a fronte di una feature completamente rotta: `toBeVisible()` su un wrapper che resta visibile a contenuto vuoto, test di grafico che non verificano mai un `<canvas>` con pixel reali, test di tabella/lista che verificano solo la shell e mai che il conteggio righe sia > 0.

### 🔴 A1 — Asserzione tautologica in `brokers.spec.ts`

**File**: `frontend/e2e/brokers/brokers.spec.ts:61`
**Evidenza**: `await expect(brokerCards).toHaveCount(await brokerCards.count());`

Questa riga confronta il conteggio delle card broker con **se stesso**, calcolato nello stesso istante. Non importa se ci sono 0 broker, 3 broker o se la lista è completamente rotta: l'asserzione è sempre vera per costruzione. È l'esempio più netto di "test container-non-content" trovato in questa caccia — non verifica nemmeno un contenitore, verifica un numero contro se stesso. Probabile refuso di refactor (qualcuno intendeva confrontare con un valore atteso fisso, o con il conteggio ottenuto da una risposta API mockata, e ha finito per riusare la stessa variabile). **Severità**: massima per questo asse — il test dà una falsa sensazione di copertura a costo zero di manutenzione, ma non protegge assolutamente nulla.

### 🔴 A2 — Grafici "visibili" mai verificati nel contenuto: pagina dettaglio asset

**File**: `frontend/e2e/assets/asset-detail.spec.ts:36-39`
**Evidenza**: il test "detail page shows header and chart" verifica solo che il testid del contenitore del grafico prezzi (`PriceChartFull`/`LineChart`) sia visibile. Non c'è alcuna verifica che esista un `<canvas>`, che abbia dimensioni non nulle, o che contenga tracciati. Esattamente la stessa forma del bug del semi-donut: un contenitore che sopravvive anche se ECharts non ha mai renderizzato nulla dentro. Questo è il grafico più visibile dell'intera applicazione (prima cosa che un utente vede aprendo un asset), quindi la severità è alta nonostante non ci sia (per ora) evidenza che sia effettivamente rotto — il punto è che il test non lo scoprirebbe se lo fosse.

### 🟡 A3 — Suite dettaglio broker: molti test, stessa lacuna ripetuta

**File**: `frontend/e2e/brokers/brokers-detail.spec.ts` (test di `LotWacPriceChart`, `LotGanttChart`, `LotComparisonChart`, circa righe 297-449)
**Evidenza**: la suite è estesa e a prima vista sembra accurata — il test del `lot-comparison-echart` verifica il grafico in **quattro stati diversi di toggle** (vista per lotto/per asset, ecc.), dando l'impressione di una copertura granulare. Ma ognuna delle quattro asserzioni è un `toBeVisible()` sul contenitore, mai un controllo sul canvas o sul suo contenuto. È un caso interessante perché il volume di test crea un falso senso di robustezza: quattro asserzioni ripetute sullo stesso difetto non sono quattro volte più sicure di una sola.

### 🟡 A4 — Pagina dettaglio FX: verifica parziale, migliore ma non sufficiente

**File**: `frontend/e2e/fx/fx-detail.spec.ts` (circa righe 44-51)
**Evidenza**: qui il test è un gradino sopra i precedenti — verifica che l'elemento `<canvas>` stesso sia visibile (non solo il contenitore esterno), il che esclude il caso "il componente non è mai montato". Non verifica però che il canvas abbia contenuto renderizzato (dimensioni non nulle, pixel non tutti trasparenti), quindi non intercetterebbe un `$effect` che monta il canvas ma non ci disegna mai sopra — la stessa famiglia di bug del semi-donut, solo in un punto leggermente più a valle della catena di rendering.

### 🟡 A5 — `asset-data-editor.spec.ts`: canvas usato come gate di sincronizzazione, non come asserzione

**File**: `frontend/e2e/assets/asset-data-editor.spec.ts:37-43`
**Evidenza**: `await page.waitForSelector('canvas')` non è scope-ato a un contenitore specifico e viene usato per aspettare che *qualche* canvas compaia nella pagina prima di procedere, non come verifica esplicita che il grafico giusto abbia renderizzato correttamente. Funziona da sincronizzazione, non da protezione — se un canvas sbagliato (o vuoto) comparisse per primo, il test proseguirebbe comunque.

### 🟡 A6 — Suite di analisi rischio: stessa forma, severità minore

**File**: `frontend/e2e/*risk*` (grafici di confronto, simulazione, correlation heatmap)
**Evidenza**: stessa forma container-only delle voci precedenti. Severità più bassa perché la sezione rischio è più recente e meno centrale nel percorso utente principale rispetto a dettaglio asset/FX/broker.

### 🟢 A7 — `asset-list.spec.ts`: parzialmente protetto

**Evidenza**: qui esiste già un'asserzione ragionevole (conteggio card > 0 OPPURE tabella visibile), quindi la lista non è scoperta come le voci precedenti — la segnalo solo perché la condizione "OR" è più debole di un controllo diretto sul conteggio righe in entrambe le modalità di visualizzazione (card/tabella), ma non è un problema urgente.

**Riferimento positivo**: `frontend/e2e/brokers/broker-sharing.spec.ts:56-74`, funzione `expectOwnershipChartCanvas()`. Verifica sia l'esistenza del `<canvas>` sia le sue dimensioni (`boundingBox()` con altezza/larghezza non nulle). È l'unico test della suite che avrebbe effettivamente intercettato il bug del semi-donut, ed è il modello che propongo di generalizzare nella sezione finale.

---

## Asse 2 — Capability sparite durante i redesign

Ho incrociato `git log --diff-filter=D --name-only` sui file `.svelte` cancellati, `git log -S'<NomeComponente'` per isolare il commit che ha rimosso l'ultimo punto di chiamata di un componente, e lettura diretta dei messaggi di commit dei grandi redesign noti (`6c009e6b` dashboard, `095d5299`/`0a551f1c` riscrittura pagina FX, `1a734008`/`29898623` transazioni) più altri individuati per dimensione del diff.

### 🔴 B1 — La scorciatoia di cassa nella pagina broker, eliminata insieme al suo componente

**Commit**: `c14117bb` — "feat(brokers): redesign broker overview UI (Milestone 3, Fase 1)"
**Evidenza**: `git show --name-status c14117bb` mostra `D` (delete) per **entrambi** `CashBalanceCard.svelte` (174 righe) e `CashTransactionModal.svelte` (68 righe), **nello stesso commit** che ha riscritto `brokers/[id]/+page.svelte` — cioè anche il loro unico punto di chiamata è sparito nella stessa modifica. Questo è esattamente il caso "più difficile" descritto nella consegna: non rimane alcun file orfano da trovare con uno scanner di codice morto, perché componente e chiamante sono spariti insieme. L'unico modo per trovarlo era la cronologia git.

**Cosa rappresentava**: un pulsante rapido nella pagina dettaglio broker per registrare un DEPOSITO o un PRELIEVO di liquidità direttamente dal contesto del broker, senza uscire dalla pagina.

**Verifica della severità reale**: ho controllato se la capability sottostante (creare transazioni DEPOSIT/WITHDRAWAL) sia sparita del tutto o solo la scorciatoia contestuale. È sparita solo la scorciatoia: la pagina generica Transazioni permette ancora di creare questi movimenti tramite il modale generico. Quindi non si tratta di una capability persa nella sostanza, ma di una **comodità contestuale persa senza traccia** — l'utente doveva prima poterlo fare in due click dalla pagina del broker, ora deve navigare alla pagina Transazioni e (presumibilmente) filtrare/selezionare il broker giusto. Il messaggio del commit descrive un redesign dell'overview broker ma non menziona da nessuna parte la rimozione di questa funzionalità.

**Cosa servirebbe per confermare**: verificare con l'app in esecuzione se un utente reale nota la mancanza (analogamente a come si è scoperto il caso del LiveTicker), e se la user experience di creare un deposito/prelievo dal contesto broker sia effettivamente peggiorata in modo significativo o solo marginale.

### 🟡 B2 — Pannello "transazioni recenti" della dashboard, ipotesi più debole

**Commit**: `6f9330ae` (individuato durante l'analisi dei grandi diff dashboard)
**Evidenza**: indicazioni di una vista compatta "transazioni recenti" presente in una versione precedente della dashboard e non più presente identica nella versione attuale. A differenza di B1, qui **non ho una conferma di prima mano altrettanto solida quanto per CashTransactionModal** — l'evidenza proviene dall'analisi delegata e non l'ho riverificata riga per riga con lo stesso rigore. Il pannello equivalente potrebbe essere stato spostato/rinominato invece che eliminato (nella dashboard attuale esistono più tab/sezioni che potrebbero coprire lo stesso ruolo). Riporto questo reperto con fiducia più bassa, da trattare come pista da verificare piuttosto che conclusione.

### Il contro-esempio positivo: come si documenta un redesign correttamente

**Commit**: `54a15b42` — "feat(ai-export)!: publish focused V3 catalog" (il punto esclamativo nel tipo di commit segnala esplicitamente una breaking change, e il messaggio contiene un footer `BREAKING CHANGE:`). Questo commit ha consolidato una ventina di dataset granulari dell'AI Export in 8 dataset "pubblici" curati (vedi anche Asse 3, e il report `13_ai_export.md` per il dettaglio completo — l'AI Export è fuori dal perimetro del mio approfondimento). Lo cito qui non come reperto negativo ma come **modello di comportamento corretto**: il commit dichiara esplicitamente che sta rompendo qualcosa, anche se non elenca ogni singolo ID rimosso. È l'opposto esatto di `6c009e6b` e `c14117bb`, che riscrivono un'area intera senza mai dire "questo pezzo prima c'era e ora non c'è più".

### Casi controllati e scartati (non sono capability perse)

Durante l'archeologia ho anche isolato due endpoint backend che *sembravano* spariti dal frontend, e ho verificato che non lo sono realmente — li riporto qui perché la distinzione è importante per non gonfiare la lista con falsi allarmi (dettagli completi nell'Asse 3): `promote_transfer` non ha chiamanti diretti ma la funzionalità che rappresenta passa oggi per un endpoint generico diverso; non è stata rimossa, è stata sostituita da un percorso più generale nello stesso periodo.

---

## Asse 3 — Superficie UI orfana (i18n, API, store, routing)

### i18n: sostanzialmente pulito, con un'unica eccezione minore e già spiegata

Ho confrontato le **2328 chiavi foglia** presenti in `en.json` con il loro utilizzo letterale in `frontend/src` e `frontend/e2e`, includendo entrambe le sintassi di chiamata usate nel codice (`$_('chiave')` e `$t('chiave')` — un grep che ne controlla solo una produce falsi positivi, come mi è capitato inizialmente).

Due cluster sono emersi come apparenti orfani e sono stati entrambi verificati a fondo:

- **`risk.*` (169 chiavi): falso positivo.** Tutte referenziate tramite costruzione dinamica della chiave, `` $t(`risk.warnings.${code}`) `` e simili, per stringhe pilotate da codici enum lato backend (avvisi, errori, indicatori di qualità dell'analisi rischio). Nessuna di queste 169 chiavi è realmente orfana; sono tutte raggiungibili a runtime, semplicemente non tramite un letterale grep-abile. Lo segnalo come nota metodologica: uno scanner naive di chiavi i18n orfane produrrebbe qui un allarme rumoroso e completamente falso.
- **`aiExport.dataset.{broker,asset,fx}.*` (22 ID orfani su 28 totali, 6 ancora usati): reperto reale ma minore, già spiegato.** Il catalogo pubblico attuale (`frontend/src/lib/features/ai-export/catalog/shared.ts`, `AI_EXPORT_PUBLIC_CATALOG_CONFIG`) referenzia solo 8 dataset curati; i restanti 22 ID (ciascuno con coppia `.display`/`.description`, quindi 44 chiavi foglia) sono rimasti tradotti in tutte e quattro le lingue ma non più referenziati da nessun componente, a seguito del commit `54a15b42` descritto sopra nell'Asse 2. È debito di pulizia minore (chiavi da rimuovere da tutti i file `*.json` delle 4 lingue), non una capability nascosta: il redesign è documentato, non silenzioso. Non è quindi lo stesso pattern degli altri reperti di questo report, ma lo cito per completezza numerica dato che l'angolo i18n era indicato come il più promettente.

Al netto di questi due cluster spiegati, non ho trovato altri gruppi di chiavi tradotte in tutte e quattro le lingue (EN/IT/FR/ES) e prive di qualunque chiamante — il segnale "qualcuno ha tradotto deliberatamente una stringa in 4 lingue per una feature ora irraggiungibile" **non si è materializzato altrove**. Asse i18n dichiarato pulito oltre quanto sopra.

### Endpoint API senza chiamante frontend

- **`suggest_events`** (`POST /api/v1/transactions/events/suggest`, `backend/app/api/v1/transactions.py:257-258`): **zero riferimenti** in componenti, store o test frontend, fin dalla sua introduzione nel commit `c3faae19`. A differenza dei reperti dell'Asse 2, questo non è "costruito e poi rimosso" — è "costruito e mai collegato" fin dal principio. È lo stesso tipo di caso già documentato per il calcolo WAC multi-broker nel report `02`/`12` (`portfolio_service.py:347`): funzionalità backend pronta, mai esposta in UI. Non rientra strettamente nel pattern "sparito durante un redesign" che sto cacciando, ma lo segnalo perché è comunque superficie orfana rilevante trovata sullo stesso asse.
- **`promote_transfer`** (`POST /api/v1/transactions/transfers/promote`, `backend/app/api/v1/transactions.py:301-302`): nessun chiamante diretto per alias — ma **non è una capability persa**. Ho tracciato `frontend/src/lib/stores/portfolio/portfolioMutation.ts:26` e confermato che `onPromoteMergeConfirm` in `transactions/+page.svelte` realizza la stessa azione (promuovere una coppia di transazioni a trasferimento) passando per l'endpoint generico batch `/api/v1/transactions/commit` con un payload `{promotes: [...]}`. L'endpoint dedicato è duplicato/superato, non abbandonato: la UI ha semplicemente scelto la via generica invece di quella specifica nello stesso periodo di sviluppo. Lo cito esplicitamente come "quasi-reperto" scartato, per la stessa ragione metodologica dei falsi positivi i18n: distinguere una sostituzione voluta da una perdita silenziosa è il cuore di questa caccia.
- Endpoint di backup/amministrazione/upload verificati e considerati **legittimamente** privi di una controparte UI diretta (operazioni CLI/manutenzione, non user-facing) — non li elenco singolarmente perché non sono reperti, sono rumore di fondo atteso.

### Store: puliti

Nessuna funzione esportata da uno store di `frontend/src/lib/stores/` risulta priva di consumatori con un profilo sospetto — le uniche funzioni non chiamate da alcun componente sono helper interni di reset/compatibilità legacy, coerenti con manutenzione ordinaria e non con una capability rimossa.

### Routing/navigazione: pulito

Tutte le route verificate contro `Sidebar.svelte` risultano raggiungibili da un punto di navigazione. Nessuna pagina "orfana" (route definita ma non linkata) trovata.

---

## Asse 4 — Trappole di reattività della stessa classe del bug del semi-donut

Il bug originale ha una forma meccanica precisa: un `$effect` (runes mode) che legge una prop array/oggetto **solo dentro un controllo di verità**, senza mai leggerne il contenuto in modo sincrono all'interno del corpo dell'effetto — quindi senza mai agganciare davvero una dipendenza tracciata sul contenuto, con il rendering effettivo delegato a una funzione richiamata in modo asincrono. Ho cercato la stessa identica forma negli altri 15 componenti chart di `frontend/src/lib/components/charts/`.

### 🟡 C1 — `AllocationPieChart.svelte:95-101` e `GeographyMap.svelte:112-118`: stessa forma di codice, stessa classe di rischio

**Evidenza diretta**: entrambi i componenti hanno un `$effect` con la stessa identica struttura del bug originale pre-correzione:

```
if (chartContainer && data) {
    tick().then(() => {
        setupResizeObserver();
        renderChart();
    });
}
```

`data` viene letto solo nel controllo di verità; `renderChart()` non riceve `data` come parametro ma rilegge la variabile del componente al momento della sua esecuzione, dopo il salto asincrono di `tick()`. È, riga per riga, la stessa forma che era presente in `SemiDonutChart.svelte` prima della correzione ora nell'albero di lavoro. Nessuno dei due componenti ha il contatore `renderGeneration` né un controllo `isDisposed()` introdotti dalla correzione di riferimento.

**Una precisazione onesta che modera la severità**: ho verificato i punti di chiamata reali di questi due componenti — `AllocationPanel.svelte` (dashboard) e `assets/[id]/+page.svelte`. **Entrambi i genitori sono già in modalità runes pura** (`let {...} = $props()`, nessun `$:`/`export let` residuo) — a differenza del caso originale, dove il genitore (`BrokerSharingPanel`) era in legacy mode e il confine legacy→runes è stato indicato come l'elemento scatenante. Questo significa che la condizione specifica che ha fatto emergere il bug originale — un genitore legacy che riassegna l'array e un ponte runes che non lo propaga correttamente — **non è oggi presente per nessuno dei due punti di chiamata verificati** di `AllocationPieChart`/`GeographyMap`. Non posso quindi affermare con la stessa certezza dell'istanza 1 che questi due componenti stiano attualmente fallendo in produzione: la forma di codice è oggettivamente fragile e identica a un difetto già dimostrato altrove nello stesso codebase, ma il suo innesco specifico potrebbe non verificarsi con gli attuali genitori runes-to-runes.

Ho anche verificato che `renderChart()` in `AllocationPieChart.svelte` non contiene `await` al suo interno (è sincrona), quindi il secondo tipo di trappola (vedi C2 sotto) non si applica qui.

**Perché lo segnalo comunque come reperto a sé, e non lo scarto**: primo, è codice strutturalmente meno robusto del pattern corretto disponibile nello stesso repository, e potrebbe rompersi silenziosamente se in futuro uno di questi due componenti venisse agganciato a un genitore legacy (come già successo una volta con `SemiDonutChart`) — cosa più che plausibile dato che sia `AllocationPanel` sia la pagina asset sono aree soggette a redesign frequenti. Secondo, non posso escludere con analisi statica scenari più sottili di mutazione in-place di un array senza cambio di riferimento. **Cosa servirebbe per confermare**: eseguire l'app e osservare se i grafici di allocazione (torta settori/tipologia, mappa geografica) si aggiornano correttamente cambiando rapidamente broker/valuta di visualizzazione sul pannello Allocazione della dashboard o sulla pagina dettaglio asset — la stessa tecnica di riproduzione che ha rivelato il bug originale.

### 🟢 C2 — `setOption` dopo un `await`: pulito al di fuori del caso già corretto

Ho verificato gli altri componenti chart per la seconda classe di trappola (chiamare `setOption` dopo un salto asincrono, senza controllare se l'istanza del grafico sia stata smontata o sostituita nel frattempo). Al di fuori del caso `SemiDonutChart` (già corretto con il contatore di generazione), non ho trovato altre istanze in cui questo pattern sia effettivamente presente con un `await` reale e dati esterni nel mezzo — la maggior parte dei componenti chart o non ha logica asincrona nel percorso di rendering, o (come `AllocationPieChart`) usa solo `tick()` senza ulteriori attese a valle. Asse dichiarato pulito su questo punto specifico.

### 🟢 C3 — Nessun altro confine legacy/runes rischioso individuato

Ho cercato altri punti in cui un componente runes-mode riceve prop da un genitore ancora in legacy mode (`export let`/`$:`), che è il confine dove il bug originale ha effettivamente vissuto. Il confine `BrokerSharingPanel` (legacy) → `SemiDonutChart` (runes) resta l'unico caso confermato in cui questa combinazione coesisteva *con* la forma di codice difettosa. Non ho trovato altri confini misti abbinati alla stessa forma di effetto rischiosa — il che è positivo, ma vale la pena ripetere la verifica quando altri componenti legacy verranno migrati a runes nelle prossime fasi, perché è proprio nel momento della migrazione parziale che questo tipo di confine si crea.

---

## Interventi raccomandati (priorità)

| # | Reperto | Asse | Severità | Sforzo stimato di verifica/fix | Tipo |
|---|---|---|---|---|---|
| 1 | Asserzione tautologica `brokers.spec.ts:61` | 1 | 🔴 | Banale (una riga) | Bug di test, correzione immediata |
| 2 | `AllocationPieChart.svelte` / `GeographyMap.svelte`: stessa forma del bug del semi-donut | 4 | 🟡→🔴 se confermato a runtime | Medio (applicare lo stesso pattern di `SemiDonutChart` corretto) | Hardening difensivo, verificare a runtime prima di classificare 🔴 |
| 3 | `CashTransactionModal`/`CashBalanceCard` eliminati con il loro punto di chiamata (`c14117bb`) | 2 | 🟡 | Basso (decisione di prodotto: reintrodurre la scorciatoia o confermare che è voluto) | Decisione di prodotto da registrare, non necessariamente un bug |
| 4 | Test dettaglio asset/FX/broker: nessuna verifica di contenuto del canvas | 1 | 🟡 | Medio (generalizzare `expectOwnershipChartCanvas`) | Hardening dei test |
| 5 | 22 chiavi i18n orfane in `aiExport.dataset.*` | 3 | 🟢 | Basso (pulizia file di traduzione) | Debito minore, già spiegato |
| 6 | `suggest_events` mai collegato al frontend | 3 | 🟢 | Da decidere in sede di prodotto | Costruito e mai esposto, non "perso" |
| 7 | Pannello transazioni recenti dashboard (`6f9330ae`) | 2 | 🟢 (ipotesi debole) | Verifica manuale necessaria | Da confermare, fiducia bassa |

## Stato di remediation

> Aggiornato dal coordinatore dopo la consegna del report. Ogni riga della tabella
> precedente è stata triagiata; qui sotto l'esito.

| # | Stato | Dettaglio |
|---|---|---|
| 1 | ✅ **Corretto** | `brokers.spec.ts` — l'asserzione tautologica è stata sostituita con un controllo reale: il test filtra le card sul nome univoco (`Test Broker ${Date.now()}`) generato dal test stesso e verifica `toHaveCount(1)`. Ora fallisce davvero se la creazione del broker non va a buon fine, ed è indipendente dai broker già presenti. |
| 2 | ✅ **Corretto (hardening difensivo)** | `AllocationPieChart.svelte` e `GeographyMap.svelte` — la guardia `if (chartContainer && data)` è stata sostituita con una lettura sincrona del *contenuto* dentro l'`$effect`, così che l'effetto dipenda davvero dai dati. **Nota tecnica importante**: i due componenti non hanno lo stesso tipo di `data` — `AllocationPieChart` riceve `AllocationEntry[]` (array, letto con `data.map((slice) => ({...slice}))`, identico a `SemiDonutChart`), mentre `GeographyMap` riceve `Record<string, number>` (oggetto, letto con `for (const key of Object.keys(data)) void data[key]`). Applicare meccanicamente il pattern dell'array anche al secondo lo avrebbe rotto: `.map` non esiste su un `Record`. Non è stata introdotta la macchina `renderGeneration` di `SemiDonutChart`, perché K3 ha dichiarato onestamente che l'attivazione a runtime non è confermata e i genitori attuali sono già in runes mode puro: la correzione del tracking è atomica e a rischio nullo, la guardia di generazione sarebbe stata un intervento più invasivo su un difetto non riprodotto. Verifica: `./dev.py front check` 0 errori/0 warning, vitest 45 file / 415 test verdi, Prettier conforme. |
| 4 | ⏳ **Delegato** | La parte relativa a `asset-detail.spec.ts` (voce A2, il grafico più visibile dell'app) è stata assegnata allo stream K1, che stava già modificando quel file — un edit concorrente lo avrebbe corrotto. K1 deve replicare il pattern di `expectOwnershipChartCanvas()` con un helper locale, e fermarsi con uno STOP se il canvas risultasse davvero a dimensione zero (sarebbe una seconda regressione reale). Le voci A3–A6 (broker detail, FX, risk) restano aperte. |
| 3, 5, 6, 7 | 📋 **Aperto, non è debito tecnico** | Sono decisioni di prodotto o verifiche che richiedono l'app in esecuzione, non correzioni meccaniche: vanno discusse, non eseguite d'ufficio. |

## Come evitare che il pattern si ripeta

Dai quattro assi emerge una ricetta di prevenzione a due componenti, la stessa che era implicita già nei due casi originali:

**Sul lato test**: un test che verifica un grafico deve sempre affermare qualcosa sul *contenuto renderizzato*, non sulla presenza del contenitore. Il modello minimo, già esistente in questo stesso repository, è `expectOwnershipChartCanvas()` in `broker-sharing.spec.ts`: verificare che esista un `<canvas>` e che il suo `boundingBox()` abbia altezza e larghezza non nulle. Lo stesso principio si generalizza a tabelle/liste: l'asserzione utile non è "il contenitore della tabella è visibile", è "il numero di righe è maggiore di zero" (o, se lo zero è uno stato legittimo, "il messaggio di stato vuoto è visibile in alternativa alle righe"). Varrebbe la pena, come intervento strutturale più ampio, promuovere un helper condiviso equivalente a `expectOwnershipChartCanvas` per tutti i test grafico dell'e2e suite, invece di lasciarlo come pattern isolato in un solo file.

**Sul lato commit/redesign**: quando un redesign o una riscrittura elimina un componente, un pulsante, una card o una sezione, il messaggio di commit dovrebbe dirlo esplicitamente — anche una singola riga "Removed: cash quick-action from broker detail (superseded by generic transactions page)" sarebbe bastata a rendere `c14117bb` un caso documentato invece che silenzioso. Il commit `54a15b42` (V3 catalog dell'AI Export) è l'esempio, imperfetto ma reale, di come si fa: dichiara esplicitamente nel tipo di commit (`!`) e nel footer che sta rompendo qualcosa, anche se non elenca ogni singolo ID rimosso. La differenza tra un redesign "pulito" e uno che nasconde una perdita silenziosa non è la qualità del codice prodotto — in entrambi i casi confermati (`6c009e6b`, `c14117bb`) il codice nuovo è buono — è semplicemente se qualcuno ha scritto una riga in più nel messaggio di commit.

Nessuno dei due accorgimenti richiede nuovi strumenti: richiedono solo disciplina al momento in cui si scrive il test o si finalizza il commit. È lo stesso motivo per cui i due bug originali sono sopravvissuti così a lungo: non mancavano gli strumenti per trovarli, mancava l'abitudine di chiedersi "questa asserzione fallirebbe davvero se la feature si rompesse?" e "sto per cancellare qualcosa che l'utente notava?".
