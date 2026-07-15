# Studio — Quantizzazione dinamica daily→weekly→monthly nei grafici a 2 assi

> Studio di fattibilità, **non un piano implementativo**. Nessuna riga di codice toccata per questo tema.
> Nasce da una richiesta di potenziamento futuro sui grafici a 2 assi (tempo × valore) della Dashboard e del
> Broker Detail, in continuità con il redesign di Milestone 3.

## Problema

Alcuni grafici (crescita del portafoglio, storico allocazione per settore/tipo/geografia, prezzi asset)
possono coprire l'intera vita del portafoglio — potenzialmente **10-20+ anni di dati giornalieri** (~2500-7300
punti). Il backend restituisce sempre la risoluzione nativa richiesta (giornaliera) senza essere toccato: il
problema è **puramente di visualizzazione**. Quando l'utente è zoomato su un intervallo molto ampio:

1. Il rendering rallenta (migliaia di punti/candele da disegnare).
2. I pixel del monitor non bastano: più punti finiscono nella stessa colonna di pixel, il dettaglio
   giornaliero diventa visivamente inutile.

**Obiettivo**: quando il periodo attualmente visibile (in base allo zoom/dataZoom) supera una soglia (es. 600
giorni), passare automaticamente a una vista aggregata settimanale; se si supera un'ulteriore soglia, a
mensile. Il backend continua a inviare sempre i dati giornalieri grezzi; l'aggregazione avviene lato client,
dinamicamente, in base allo zoom corrente.

## Verdetto di fattibilità

**Fattibile lato client. Nessuna feature "automagica" nativa in ECharts — va costruita a mano**, ma è un
pattern standard e ben documentato nel settore charting finanziario (lo stesso approccio usato da TradingView,
Highcharts Stock, ecc.: si ascolta l'evento `dataZoom`, si calcola la risoluzione necessaria, si
ri-aggregano/ri-richiedono i dati, si aggiorna il grafico con `setOption`).

ECharts fornisce il gancio giusto (evento `dataZoom`, già presente e usato oggi solo per un effetto
collaterale minore — vedi sotto) ma **non** una feature di re-aggregazione calendariale automatica.
`series.sampling: 'lttb'` è **già usato oggi** (solo su serie `line`, es. overlay dei segnali in
`chartCoreHelpers.ts`) — ma è un downsampling *visivo* (algoritmo Largest-Triangle-Three-Buckets, preserva la
"forma" della curva), non un'aggregazione OHLC calendariale. È complementare alla feature richiesta, non un
sostituto.

## Modello dati attuale (rilevante per la fattibilità)

Tutte le serie usano un tipo comune, `LineDataPoint`:

```ts
interface LineDataPoint {
    date: string;
    value: number;
    open?: number | null;
    high?: number | null;
    low?: number | null;
    close?: number | null;
    volume?: number | null;
    // + alcuni campi FX/staleness non rilevanti qui
}
```

OHLCV sono **reali se il provider li fornisce**, altrimenti **sintetizzati** in
`CandlestickChart.svelte` (righe 264-274): `open = chiusura del giorno precedente`,
`high/low = max/min(open, close)`. L'aggregazione settimanale/mensile lavorerebbe su questi stessi dati
giornalieri (reali o sintetizzati) — le regole OHLC standard (vedi sotto) si applicano naturalmente in
entrambi i casi.

**Scoperta chiave sui segnali overlay**: le classi in `frontend/src/lib/charts/signals/*.ts` (EMA, RSI,
MACD, Bollinger, ecc.) sono **già agnostiche alla spaziatura temporale** — `computePoints(baseData)` itera
per indice di array, non per giorni di calendario effettivi (il parametro "period" espresso in giorni è solo
un'etichetta UI: la matematica è "N campioni consecutivi", si veda `EmaSignal.ts`). Questo significa che
ri-eseguire un segnale su dati già aggregati **non richiederebbe alcuna modifica al codice di calcolo** — ma
cambierebbe la *semantica* dell'indicatore (EMA(14) su dati settimanali diventa una EMA a 14 settimane, non
più 14 giorni). **Deciso** (vedi sezione "Segnali overlay" sotto): i segnali vanno calcolati SEMPRE sulla
serie giornaliera completa, per non falsare i risultati — è il solo downsample dell'OUTPUT che segue le
regole di aggregazione.

## Componenti coinvolti

| Componente | Ruolo attuale | Impatto se implementato |
|---|---|---|
| **NUOVO** `timeSeriesAggregation.ts` (proposto) | — | Utility pura condivisa: bucketing per settimana ISO / mese di calendario, regole OHLCV, regola "valore rappresentativo" per le linee. Da creare per evitare 3 implementazioni duplicate. |
| `chartCoreHelpers.ts` | Assi Y, `buildDataZoom()`, costruttore serie overlay — condiviso da `PriceChartFull` + `CandlestickChart` | Aggiungere logica di risoluzione corrente + formattazione tick asse X per settimana/mese |
| `lineChartHelpers.ts` | `buildMainSeries()` — usato da `PriceChartFull` (vista linea); contiene l'algoritmo di segmentazione colore verde/rosso per baseline (vedi sezione dedicata sotto) | Deve costruire la serie da dati (eventualmente) aggregati — l'algoritmo di segmentazione è generico e funziona invariato su qualunque risoluzione |
| `PriceChartFull.svelte` | Orchestratore prezzi asset (linea/candela), gestisce dataZoom/eventi/measure | Nuovo stato `resolution: 'daily' \| 'weekly' \| 'monthly'`; listener sull'evento `dataZoom` → calcolo giorni visibili → ri-aggregazione dati + segnali prima di `setOption` |
| `CandlestickChart.svelte` | Rendering candele + volume (2 grid già sincronizzati sullo stesso dataZoom) | Stessa logica di risoluzione (ricevuta dal parent o calcolata autonomamente); aggregazione volume = somma |
| `ChartSignal.ts` + sottoclassi (Ema/Rsi/Macd/Bollinger/comparison) | `computePoints()` già indipendente dalla spaziatura | **Nessuna modifica alla matematica** — calcolo sempre sulla serie giornaliera piena (deciso); serve solo una funzione di downsample dell'OUTPUT per-tipo (vedi sotto) |
| `GrowthChart.svelte` | Grafico crescita NAV — implementazione indipendente (non condivide `chartCoreHelpers`) | Proprio listener `dataZoom` + proprio aggregatore per ~5 serie linea (NAV, capital baseline, ecc.) |
| `AllocationHistoryChart.svelte` | Storico allocazione % stacked — implementazione indipendente | Proprio listener `dataZoom` + aggregazione percentuali stacked (media o fine-periodo, vedi sotto) |
| `echartsTooltipHelpers.ts` | Tooltip condiviso | Il formatter potrebbe dover indicare "settimana del..." invece di una data esatta |
| Event markers (dividendi/interessi/split in `PriceChartFull`) | Scatter su data esatta | Da riallineare al bucket contenente, se il periodo è aggregato |
| Measure mode (click-to-measure) | Click su punto esatto | Precisione ridotta al bucket (settimana/mese) invece del giorno esatto quando aggregato — comportamento accettabile ma da segnalare all'utente |
| i18n | — | Nuova label/badge tipo "Vista: Settimanale" consigliata (vedi rischi) |

`LineChart.svelte` e `PriceChartCompact.svelte` sono usati solo per preview compatte/anteprima nel settings
modal, **senza** `dataZoom` — non gestiscono range temporali ampi, quindi **non applicabili**.

## Regole di aggregazione proposte

- **Candela (OHLCV)**: open = primo valore del bucket, close = ultimo, high/low = max/min su tutto il bucket,
  volume = somma. Regola ovvia, già confermata.
- **Linea (prezzo/NAV/ecc.)** — 2 opzioni, nessuna decisione presa:
  - *Fine periodo* (valore dell'ultimo giorno del bucket): coerente con il "close" della candela (stesso
    identico valore passando da vista linea a candela), nessuna distorsione/lag. Non riflette la volatilità
    infra-periodo.
  - *Media del periodo*: smussa il rumore, ma introduce lag percepito ed è incoerente con la candela (chi
    passa da linea a candela vedrebbe un valore diverso a parità di data).
  - **Raccomandazione**: fine-periodo, per coerenza tra le 2 viste dello stesso `PriceChartFull`.
- **Allocazione % stacked (`AllocationHistoryChart`)**: stessa scelta fine-periodo vs media; qui l'urgenza di
  coerenza con una candela non esiste (non c'è vista candela per l'allocazione), quindi la media potrebbe
  avere più senso (meno sensibile a un singolo giorno anomalo) — da decidere quando si pianificherà
  l'implementazione.
- **`staleDays`** (campo ausiliario che pilota la sfumatura di opacità per dati non aggiornati, usato dalla
  colorazione — vedi sezione sotto): serve una regola di bucketing dedicata, non solo OHLCV. Coerentemente
  con "fine periodo" per il valore principale, si propone di usare lo `staleDays` **dell'ultimo giorno del
  bucket** (stesso giorno che determina il valore mostrato) — alternativa più conservativa: il MAX
  `staleDays` nel bucket, se si preferisce segnalare il caso peggiore anche quando l'ultimo giorno è fresco.

## Colorazione baseline (verde/rosso) e segmentazione — impatto dell'aggregazione

Solo la **vista linea del grafico prezzi** (`PriceChartFull.svelte` + `LineChart.svelte`, tramite
`lineChartHelpers.ts::buildMainSeries()`) ha questa logica — `GrowthChart`/`AllocationHistoryChart` usano
serie a colore fisso, non sono coinvolti.

**Come funziona oggi** (indipendentemente dall'aggregazione): l'algoritmo NON usa il `visualMap` nativo di
ECharts, è custom. Per ogni punto calcola un colore (verde se `value >= baseline`, rosso altrimenti) e
un'opacità (in base allo staleness). Poi raggruppa i punti consecutivi con lo stesso (colore, opacità) in
"segmenti" (`Segment[]`), e crea **una serie ECharts per segmento** (non 1 o 2 serie fisse — tante quante
sono le transizioni di colore/opacità), con un punto di sovrapposizione tra segmenti adiacenti per mantenere
la linea visivamente continua (logica di "bridge" direzionale: indietro alle transizioni di colore, avanti
alle transizioni di sola opacità).

**Impatto dell'aggregazione**: l'algoritmo è generico — lavora su un array `values`/`staleDays` qualsiasi,
senza assunzioni sulla spaziatura temporale. Aggregare a settimanale/mensile **non richiede modifiche al
codice della funzione**: basta passarle gli array già aggregati. Due conseguenze da tenere presenti:

1. **Il colore di ogni bucket eredita la stessa scelta "fine-periodo vs media"** del valore mostrato (vedi
   sopra) — se un asset scende sotto baseline lunedì-giovedì e recupera venerdì, un bucket settimanale
   "fine-periodo" mostrerebbe l'intera settimana in verde, mascherando il calo infra-periodo. Con "media"
   invece il colore rifletterebbe l'andamento medio del periodo. Non è una scelta indipendente: è lo stesso
   fork già aperto per il valore della linea, applicato anche al colore.
2. **Effetto collaterale positivo**: aggregare RIDUCE il numero di attraversamenti della baseline (dati più
   lisci, meno rumore giorno-per-giorno) e quindi il numero di segmenti/serie ECharts generate quando
   zoomati fuori — un beneficio di performance ulteriore, non richiesto esplicitamente ma coerente con
   l'obiettivo della feature.

**Nota indipendente (comportamento preesistente, non introdotto da questa feature)**: oggi
`buildMainSeries()` riceve sempre l'array COMPLETO del periodo caricato (non solo la finestra visibile), sia
in giornaliero che aggregato — quindi il numero di segmenti/serie è già proporzionale agli attraversamenti
di baseline sull'INTERO storico, non solo sulla vista corrente. Non è un problema introdotto
dall'aggregazione (che anzi lo allevia), ma un dettaglio architetturale preesistente da tenere a mente se in
futuro si notassero rallentamenti con asset molto volatili su storici lunghi.

## Buffering/finestra dati durante il pan a risoluzione giornaliera

**Non serve un buffer manuale.** Verificato: ECharts con `dataZoom` di tipo `'inside'` e
`filterMode: 'filter'` (già l'impostazione corrente in `buildDataZoom()`) **filtra internamente** — cioè
renderizza e processa SOLO i punti nella finestra di zoom corrente, non l'array intero, indipendentemente da
quanti punti siano caricati in `series.data`. Non è necessario implementare manualmente un meccanismo di
"finestra scorrevole" (buffer ±10% con aggiunta/rimozione su evento di pan): ECharts lo fa già internamente
per il rendering, ed è pensato per reggere bene fino a decine/centinaia di migliaia di punti — il nostro
caso peggiore (~7300 punti, 20 anni giornalieri) è ben al di sotto di quella soglia.

Dove il volume dati PESA comunque (indipendentemente dal pan) sono i ricalcoli lato JS che facciamo noi, non
ECharts:
- Il calcolo dei segnali (sempre su serie giornaliera piena, per decisione presa sopra).
- La costruzione dei segmenti colore in `buildMainSeries()` (nota architetturale sopra).
- Il controllo soglia-risoluzione ad ogni evento `dataZoom`.

Questi girano però solo quando i dati/parametri cambiano o quando si attraversa una soglia di risoluzione
(con debounce, vedi sopra) — **non ad ogni tick di pan** (il pan/zoom via dataZoom `'inside'` è gestito da
ECharts internamente via trasformazione del canvas, senza bisogno di richiamare `setOption`). Con ~7300
punti al massimo, un singolo passaggio O(N) è comunque nell'ordine dei millisecondi, non un collo di
bottiglia reale.

**Se in futuro il profiling mostrasse un problema reale** (es. dataset più grandi di quanto previsto), la
mitigazione più semplice non sarebbe un buffer che si aggiorna ad ogni pan, ma limitare la slice passata a
`setOption` a "finestra visibile × 3" ricalcolata solo al cambio di livello di risoluzione (non ad ogni
tick) — molto più semplice di un buffer incrementale live, con la maggior parte del beneficio.

## Segnali overlay — DECISO: calcolo su serie giornaliera, poi downsample dell'output

Per non falsare i risultati, i segnali si calcolano **sempre sulla serie giornaliera completa** (mai su
dati già aggregati) — corrisponde a quello che nello studio originale era descritto come "Approccio B".
Solo la serie di OUTPUT già calcolata viene poi ridotta con le stesse regole di bucketing usate per il
grafico principale, per allinearsi visivamente. Regola di downsampling proposta per tipo:

| Tipo di segnale | Esempio | Regola di downsample dell'output |
|---|---|---|
| Linea singola (valore continuo) | EMA, Linear, Compound, Sine, FX Pair, Asset Comparison | Fine-periodo (stesso criterio del prezzo, per coerenza visiva) |
| Oscillatore singola linea | RSI | Fine-periodo |
| Composito multi-linea | MACD (linea MACD + linea segnale + istogramma) | Le 2 linee: fine-periodo. L'istogramma (differenza MACD−segnale): fine-periodo anch'esso, per restare coerente con le 2 linee da cui deriva (evitare di sommare un istogramma già calcolato come differenza, che perderebbe di significato) |
| Banda di confidenza | Bollinger (upper/middle/lower) | `upper` = max del bucket, `lower` = min del bucket (inviluppo che contiene l'intera banda del periodo), `middle` = fine-periodo |

Nessuna modifica al codice di calcolo dei segnali stessi — serve solo una nuova utility di downsample
dell'output (idealmente parte dello stesso `timeSeriesAggregation.ts` proposto sopra, riutilizzata sia per
le serie principali sia per gli output dei segnali), applicata dopo `computePoints()`/`render()`.

Le label (`getLabel()`, es. "EMA(14)") restano invariate e continuano a essere corrette dato che
l'indicatore è sempre calcolato a 14 giorni reali — nessun aggiornamento di label/tooltip necessario per la
risoluzione (a differenza di quanto ipotizzato nella prima stesura di questo studio, quando l'Approccio A
era ancora sul tavolo).

## Soglie e meccanica di attivazione

- L'evento `dataZoom` (già presente, oggi usato solo per `updateArrowRotations` in `PriceChartFull.svelte`)
  è il gancio naturale: da `start`/`end` (percentuali dello zoom) + span totale in giorni si ricavano i
  giorni effettivamente visibili.
- **Soglia fissa** (es. 600gg → settimanale, un'ulteriore soglia proporzionale → mensile), come proposto:
  semplice da implementare e testare.
- **Alternativa più robusta**: soglia adattiva basata sulla larghezza reale del grafico in pixel (giorni
  visibili ÷ larghezza-px), così un monitor 4K e un laptop piccolo si comportano diversamente — più corretta
  ma più complessa. Si consiglia di partire dalla soglia fissa e rivalutare in base al riscontro reale.
- **Debounce necessario**: l'evento `dataZoom` di tipo `'inside'` genera moltissimi eventi durante un
  drag/scroll continuo — ricalcolare l'aggregazione e chiamare `setOption` ad ogni tick sarebbe
  costoso/scattoso. Serve un debounce (~150-250ms dopo che lo zoom si stabilizza) prima di ricalcolare.

## Decisioni prese finora

- ✅ **Segnali overlay**: calcolo sempre sulla serie giornaliera piena, mai su dati aggregati (per non
  falsare i risultati) — solo l'output già calcolato viene downsample-ato con le regole per-tipo sopra.
- ✅ **Buffering/finestra durante il pan**: non necessario — ECharts filtra già nativamente via
  `dataZoom filterMode:'filter'`, i volumi dati di questa app (~7300 punti max) sono ben entro il range
  gestito senza bisogno di windowing manuale.

## Punti ancora aperti

- **Linea/NAV/allocazione: fine-periodo vs media** per il valore rappresentativo di ogni bucket (si
  ripercuote anche sul colore verde/rosso della vista linea prezzi, vedi sopra) — raccomandazione
  provvisoria: fine-periodo per il prezzo (coerenza con la candela), media possibile per l'allocazione %
  (nessun vincolo di coerenza con una vista candela).
- Soglia fissa vs adattiva-ai-pixel per il cambio di risoluzione (raccomandazione: iniziare con soglia
  fissa).

## Rischi

1. **Coerenza toggle linea↔candela**: `PriceChartFull` permette di cambiare vista mantenendo lo stesso zoom
   — la risoluzione corrente va condivisa tra i due rendering, non ricalcolata in modo indipendente
   (altrimenti si rischia un disallineamento visivo cambiando vista).
2. **Nessuna indicazione visiva della risoluzione attuale** rischia di confondere l'utente (una "candela" che
   sembra un giorno ma è in realtà una settimana aggregata). Si raccomanda (non richiesto esplicitamente, ma
   fortemente consigliato) un piccolo badge "Vista: Settimanale/Mensile" quando non si è in giornaliero.
3. Le grid volume + prezzo in `CandlestickChart` sono già sincronizzate sullo stesso dataZoom (nessun nuovo
   lavoro di sync lì), ma vanno aggregate in modo coerente (stesso bucket per entrambe le serie).
4. I marker eventi (dividendi/split) andrebbero riallineati al bucket quando la vista è aggregata.
5. La modalità misura (click-to-measure) avrebbe precisione ridotta al bucket quando aggregato — accettabile,
   ma da comunicare all'utente.
6. `buildMainSeries()` costruisce oggi i segmenti-colore sull'intero storico caricato, non sulla sola
   finestra visibile — comportamento preesistente (non introdotto da questa feature, anzi alleviato
   dall'aggregazione), da tenere presente per eventuali ottimizzazioni future indipendenti.

## Prossimo passo

Nessuna implementazione in questo studio, come richiesto. Il passo naturale successivo, se si vuole
procedere, è un piano implementativo dedicato che risolva il punto ancora aperto (fine-periodo vs media per
linea/allocazione) e poi affronti l'implementazione componente per componente, nell'ordine suggerito dalla
tabella sopra (prima l'utility di aggregazione condivisa, poi `PriceChartFull`/`CandlestickChart`, poi
`GrowthChart`/`AllocationHistoryChart`).



---------------

````md
---

# Integrazione raffinata — Semantic zoom adattivo daily → weekly → monthly

## Obiettivo dell’integrazione

Questa integrazione raffina lo studio precedente introducendo alcune decisioni architetturali aggiuntive:

- scelta della risoluzione basata sulla densità reale dei punti rispetto ai pixel disponibili;
- hysteresis anch’essa basata sulla densità punti/pixel;
- aggregazioni calcolate lazy e conservate nello store/cache;
- switch di risoluzione senza animazione;
- gestione bucket-aware di eventi, tooltip e measure mode;
- regola definitiva per i segnali overlay;
- badge sintetico di aggregazione mostrato solo quando la vista non è giornaliera.

La feature va interpretata come uno **semantic zoom temporale**, non come un semplice downsampling visuale.

Il dato daily resta sempre la sorgente canonica. Le viste weekly/monthly sono viste derivate generate lato client per rappresentare meglio intervalli temporali ampi.

---

## 1. Sorgente canonica e aggregazioni derivate

Il backend continua a fornire dati giornalieri.

La struttura concettuale diventa:

```text
Backend daily data
        ↓
Store dati originali daily
        ↓
Aggregazioni client-side lazy:
  - daily: sempre disponibile
  - weekly: calcolata solo quando serve
  - monthly: calcolata solo quando serve
        ↓
Serie visualizzata da ECharts
````

Le aggregazioni settimanali e mensili non sostituiscono mai i dati originali.

Il daily rimane sempre:

* sorgente di verità;
* base per invalidare le cache;
* base per il calcolo dei segnali;
* base per i valori precisi usati nel measure mode quando l’utente inserisce manualmente date specifiche.

***

## 2. Calcolo lazy + cache nello store

> **Aggiornato dopo `impl_plan_chart_resolution_00_foundation.md`**: "store" qui va inteso in senso lato
> (dove viene conservato il risultato), non come nuovo store globale singleton. Il documento fondativo ha
> chiuso questo punto con una scelta più semplice: **memoizzazione locale al componente**, keyed by
> `resolution`, invalidata per identità del riferimento dell'array dati in ingresso — non un nuovo store
> condiviso cross-componente. Il principio "calcola lazy, riusa finché valido" sotto resta corretto, cambia
> solo DOVE vive la cache (locale al componente, non un registry globale come `assetPriceStoreRegistry.ts`).

Non è necessario pre-calcolare sempre tutte le risoluzioni all’apertura del grafico.

La strategia preferita è:

```text
Calcolare una risoluzione solo quando serve per la prima volta.
Salvarla nello store/cache (locale al componente — vedi nota sopra).
Riutilizzarla finché la sorgente daily resta valida.
```

Esempio:

```text
Apertura grafico su 10 anni.
La densità punti/px suggerisce monthly.
→ Calcolo monthly.
→ Salvo monthly in cache.
→ Renderizzo direttamente monthly.

L’utente zooma su 8 mesi.
La densità suggerisce weekly.
→ Se weekly non è in cache, la calcolo.
→ Salvo weekly.
→ Sostituisco la serie visualizzata con weekly.

L’utente torna a 10 anni.
→ monthly è già in cache.
→ riuso monthly senza ricalcolo.
```

### Invalidazione della cache

Le cache aggregate vanno invalidate solo quando viene invalidata la sorgente daily o quando cambiano parametri che rendono obsolete le serie derivate.

Esempi di invalidazione:

* cambio asset;
* cambio broker;
* cambio periodo caricato;
* refresh prezzi;
* cambio valuta;
* modifica delle transazioni/dati sorgente;
* cambio dataset/versione dati;
* cambio configurazioni che alterano la serie originale.

Non invalidano la cache:

* pan;
* zoom;
* resize, salvo la necessità di scegliere un’altra risoluzione;
* cambio dataZoom dentro la stessa risoluzione;
* switch verso una risoluzione già calcolata.

***

## 3. Risoluzione iniziale al primo rendering

All’apertura del grafico non bisogna renderizzare daily e poi sostituire immediatamente con weekly/monthly.

Il flusso corretto è:

```text
1. Ricezione dati daily.
2. Misura della larghezza effettiva del plot.
3. Lettura del periodo iniziale visibile/selezionato.
4. Calcolo della densità daily.
5. Scelta della risoluzione iniziale.
6. Calcolo lazy dell’aggregazione, se non daily.
7. Primo rendering direttamente nella risoluzione scelta.
```

L’eventuale animazione iniziale del grafico deve avvenire **solo sulla serie già corretta**.

Esempio:

```text
Periodo iniziale: 10 anni
Risoluzione scelta: monthly

Corretto:
  render iniziale monthly

Da evitare:
  render daily
  immediato switch monthly
```

Questo evita effetto popup o cambio visivo immediato dopo il caricamento.

***

## 4. Switch di risoluzione senza animazione

Quando durante zoom/pan/resize si passa da una risoluzione all’altra, lo switch deve essere netto.

Regola:

```text
Lo switch daily ↔ weekly ↔ monthly sostituisce la serie visualizzata senza animazione di transizione.
```

Quindi:

* nessun morphing tra le serie;
* nessuna animazione tra daily e weekly/monthly;
* nessun effetto rimbalzo;
* nessun popup visivo;
* la nuova serie compare direttamente.

Il cambio di risoluzione è una modifica del livello semantico della vista, non una transizione narrativa da animare.

***

## 5. Scelta della risoluzione basata su punti/pixel

La risoluzione non deve dipendere solo dal numero di giorni visibili, ma dalla densità reale dei punti rispetto alla larghezza disponibile.

La metrica principale è:

```text
density = numero bucket visibili / larghezza plot in pixel
```

Dove i bucket dipendono dalla risoluzione candidata:

```text
daily   → giorni/punti daily visibili
weekly  → settimane visibili
monthly → mesi visibili
```

Esempio:

```text
Plot desktop: 1200 px
Periodo: 900 giorni

daily density = 900 / 1200 = 0,75 punti/px
→ daily può essere ancora accettabile

Plot mobile/card stretta: 400 px
Periodo: 900 giorni

daily density = 900 / 400 = 2,25 punti/px
→ daily troppo denso
→ passaggio a weekly
```

Questa logica rende il comportamento adattivo su:

* monitor grandi;
* laptop;
* mobile;
* card strette;
* layout responsive;
* resize del contenitore.

***

## 6. Hysteresis basata su punti/pixel

Anche l’hysteresis deve lavorare sulla stessa metrica della soglia, quindi sulla densità bucket/px.

Non si usano soglie fisse del tipo:

```text
daily → weekly sopra N giorni
weekly → daily sotto M giorni
```

ma soglie di densità:

```text
daily → weekly se daily density supera una soglia alta
weekly → daily se daily density scende sotto una soglia bassa
```

Esempio concettuale:

```text
soglia alta = 1,30 bucket/px
soglia bassa = 0,80 bucket/px
```

Applicazione:

```text
daily → weekly
  se daily density > 1,30

weekly → daily
  se daily density < 0,80

weekly → monthly
  se weekly density > 1,30

monthly → weekly
  se weekly density < 0,80
```

La soglia alta e quella bassa devono essere separate per evitare oscillazioni vicino al confine.

Senza hysteresis:

```text
daily ↔ weekly può oscillare continuamente durante piccoli zoom/pan/resize.
```

Con hysteresis:

```text
il cambio avviene solo quando la nuova risoluzione è chiaramente più adatta.
```

***

## 7. Debounce sugli eventi dataZoom

L’evento `dataZoom` può essere generato molte volte durante interazioni continue.

Serve quindi debounce, indicativamente:

```text
150–250 ms
```

Il flusso desiderato è:

```text
Durante pan/zoom:
  ECharts gestisce la vista corrente.

Dopo stabilizzazione:
  calcolo range visibile;
  calcolo density;
  applico hysteresis;
  se serve cambio risoluzione;
  altrimenti non faccio nulla.
```

Non bisogna ricalcolare aggregazioni o chiamare `setOption` a ogni tick dello zoom.

***

## 8. Range logico e range renderizzato

Va distinta la finestra logica richiesta dall’utente dai punti effettivamente disegnati.

Esempio:

```text
visibleStartDate = 2026-01-05
visibleEndDate   = 2026-09-20
resolution        = monthly
```

La finestra logica parte dal 5 gennaio.

La vista monthly però disegnerà i bucket che intersecano quel range:

```text
gennaio 2026 → rappresentato dal 31 gennaio
...
settembre 2026 → rappresentato dal 30 settembre o dall’ultimo dato disponibile nel mese
```

Quindi:

```text
range logico:
  2026-01-05 → 2026-09-20

range renderizzato:
  bucket gennaio → bucket settembre
```

Questa distinzione è fondamentale per:

* dataZoom;
* switch tra risoluzioni;
* measure mode;
* tooltip;
* marker eventi.

***

## 9. Preservazione del range con date assolute

Quando cambia risoluzione, non bisogna preservare il range usando solo percentuali `start/end`, perché il numero di punti cambia.

La finestra va preservata con date assolute:

```text
visibleStartDate
visibleEndDate
```

In fase di rendering, queste date vengono mappate sulla risoluzione target.

Esempio:

```text
visibleStartDate = 2026-01-05

daily:
  primo punto visibile = 2026-01-05

weekly:
  primo bucket = settimana che contiene 2026-01-05

monthly:
  primo bucket = gennaio 2026
  punto rappresentativo = 2026-01-31
```

Quando si torna da monthly a weekly o daily, non bisogna partire dalla data rappresentativa del bucket monthly, ma dalla finestra logica conservata.

Quindi:

```text
la vista usa i bucket;
lo stato logico conserva le date reali.
```

***

## 10. Funzione concettuale date → bucket

Serve una funzione condivisa di mapping:

```text
mapDateToBucket(date, resolution)
```

Responsabilità:

```text
dato un giorno reale, determinare il bucket daily/weekly/monthly che lo contiene.
```

Esempi:

```text
mapDateToBucket(2026-01-05, monthly)
→ bucket gennaio 2026
→ bucketStart = 2026-01-01
→ bucketEnd   = 2026-01-31
→ representativeDate = 2026-01-31

mapDateToBucket(2026-01-05, weekly)
→ settimana ISO contenente 2026-01-05
→ bucketStart = lunedì della settimana
→ bucketEnd   = domenica della settimana o ultimo dato disponibile
```

Questa funzione deve essere usata in modo coerente da:

* dataZoom;
* event markers;
* measure mode;
* tooltip;
* badge/debug;
* riallineamento visuale nello switch di risoluzione.

***

## 11. Regole di aggregazione principali

### 11.1 Linee prezzo, NAV e serie cumulative

Decisione definitiva:

```text
value = valore all’end-date del bucket
```

Ovvero il valore dell’ultimo giorno disponibile dentro il bucket.

Questa regola vale per:

* prezzo asset in vista linea;
* NAV;
* capitale versato;
* valore portafoglio;
* P\&L cumulato;
* baseline;
* GrowthChart;
* serie derivate;
* AllocationHistoryChart.

Esempio monthly:

```text
Gennaio 2026:
  value = valore al 31 gennaio,
          o ultimo valore disponibile nel mese.
```

Motivazione:

* coerenza con il close della candela;
* nessun lag da media;
* interpretazione finanziaria chiara;
* tooltip semplice;
* coerenza tra grafici diversi.

***

### 11.2 Candlestick OHLCV

Regola standard:

```text
open   = primo valore disponibile nel bucket
high   = massimo valore/high nel bucket
low    = minimo valore/low nel bucket
close  = ultimo valore disponibile nel bucket
volume = somma dei volumi nel bucket
```

Se i dati OHLC sono sintetizzati a partire dalle chiusure giornaliere, l’aggregazione lavora sugli stessi dati sintetizzati.

***

### 11.3 AllocationHistoryChart

Anche l’allocazione stacked usa la regola fine-periodo.

Quindi un punto/barra mensile significa:

```text
allocazione a fine mese
```

non:

```text
allocazione media durante il mese
```

La media del periodo potrebbe essere una futura vista analitica separata, ma non fa parte di questa feature.

***

### 11.4 Staleness

Per `staleDays` si usa il valore dell’end-date del bucket.

```text
value     = valore al 31 gennaio
staleDays = staleDays del 31 gennaio
```

Non si usa il massimo staleDays del bucket, perché il valore mostrato è quello finale, non il caso peggiore interno al periodo.

***

### 11.5 Colorazione baseline verde/rosso

La colorazione eredita la stessa semantica del valore mostrato.

```text
colore bucket = colore calcolato sul valore di fine bucket
```

Esempio:

```text
asset sotto baseline lunedì-giovedì
asset sopra baseline venerdì

weekly close sopra baseline
→ bucket settimanale verde
```

Questo può nascondere oscillazioni intra-bucket, ma è coerente con il fatto che la vista weekly/monthly rappresenta il close del periodo.

***

## 12. Metadata di bucket

Ogni punto aggregato dovrebbe includere metadata espliciti.

Struttura concettuale:

```ts
{
  date: string; // data rappresentativa, normalmente bucketEnd
  value: number;

  bucketStart: string;
  bucketEnd: string;
  bucketResolution: 'daily' | 'weekly' | 'monthly';
  sourcePointCount: number;
}
```

Per OHLCV:

```ts
{
  date: string;

  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;

  bucketStart: string;
  bucketEnd: string;
  bucketResolution: 'daily' | 'weekly' | 'monthly';
  sourcePointCount: number;
}
```

I metadata servono per:

* tooltip bucket-aware;
* marker eventi aggregati;
* measure mode;
* mapping date → bucket;
* debug;
* gestione range logico/renderizzato;
* badge di aggregazione.

***

## 13. Event markers

### 13.1 Vista daily

In giornaliero il comportamento resta quello attuale.

```text
marker x = data reale evento
marker y = prezzo/valore in quel giorno
tooltip = evento specifico
```

Esempio:

```text
2026-01-12
Dividendo 12,40 €
marker y = prezzo del 2026-01-12
```

***

### 13.2 Vista weekly/monthly

In vista aggregata, gli eventi vengono raggruppati nel bucket che li contiene.

Se uno o più eventi cadono nello stesso bucket:

```text
marker x = representativeDate del bucket
marker y = valore aggregato del bucket
tooltip = lista concatenata degli eventi reali contenuti nel bucket
```

Esempio:

```text
Bucket gennaio 2026
representativeDate = 2026-01-31
value = close/value del bucket

Eventi reali:
- 2026-01-05 — dividendo 8,20 €
- 2026-01-12 — dividendo 12,40 €
- 2026-01-21 — split 2:1

Marker:
x = 2026-01-31
y = valore aggregato di gennaio
```

Tooltip:

```text
Gennaio 2026
Valore al 31/01/2026: 123,45 €

Eventi nel periodo:
- 05/01/2026 — Dividendo: 8,20 €
- 12/01/2026 — Dividendo: 12,40 €
- 21/01/2026 — Split 2:1
```

La data reale dell’evento non viene persa.  
Viene solo rappresentata graficamente sul bucket aggregato.

Se in futuro un bucket contiene molti eventi, si potrà valutare una compattazione tipo:

```text
mostra primi N eventi + “altri X eventi”
```

ma per questa fase è sufficiente prevedere la concatenazione completa nel tooltip.

***

## 14. Tooltip bucket-aware

Il tooltip deve cambiare in base alla risoluzione.

### Daily

```text
12/01/2026
Prezzo: 123,45 €
```

### Weekly

```text
Settimana 12/01/2026 – 18/01/2026
Valore al 18/01/2026: 123,45 €
```

### Monthly

```text
Gennaio 2026
Valore al 31/01/2026: 123,45 €
```

Per marker aggregati:

```text
Eventi nel periodo:
- data reale evento 1
- data reale evento 2
- data reale evento 3
```

Il tooltip deve rendere chiaro che il punto settimanale/mensile rappresenta un bucket, non una singola giornata ordinaria.

***

## 15. Measure mode

Il measure mode deve distinguere modello dati e rendering.

### Modello dati

Il modello della misura conserva sempre date reali.

Esempio:

```text
startDate = 2026-01-05
endDate   = 2026-09-17
```

La tabella misura deve calcolare i valori coerenti con quelle date reali.

Se l’utente inserisce manualmente una data specifica nella tabella, il dato mostrato deve riferirsi a quella data, non automaticamente all’end-date del bucket.

***

### Rendering sul grafico

In vista aggregata, però, i marker visuali della misura vengono disegnati sul bucket che contiene le date reali.

Esempio monthly:

```text
startDate = 2026-01-05
→ marker grafico sul bucket gennaio

endDate = 2026-09-17
→ marker grafico sul bucket settembre
```

Quindi:

```text
measure data model = date reali
measure rendering = bucket coerenti con la risoluzione corrente
```

Il click diretto su un punto aggregato imposta invece come data selezionata la data rappresentativa del bucket, normalmente l’end-date.

Esempio:

```text
click su gennaio 2026 in monthly
→ selectedDate = 2026-01-31
```

Questo è coerente perché il punto rappresenta il valore di fine gennaio.

***

## 16. Segnali overlay

Decisione definitiva:

```text
I segnali vengono calcolati sempre sulla serie daily completa.
In vista weekly/monthly viene downsampled solo l’output del segnale.
```

Non si calcolano EMA/MACD/RSI sull’aggregato, perché cambierebbe la semantica finanziaria.

Esempio:

```text
EMA(14) su daily = EMA a 14 giorni/campioni daily.
EMA(14) su weekly = diventerebbe EMA a 14 settimane.
EMA(14) su monthly = diventerebbe EMA a 14 mesi.
```

Per evitare questa ambiguità, il calcolo resta daily.

In vista aggregata si mostra uno snapshot del segnale coerente con il bucket visualizzato.

***

### 16.1 EMA / RSI / MACD / segnali linea

Regola:

```text
valore segnale aggregato = valore daily del segnale all’end-date del bucket
```

Esempi:

```text
EMA monthly gennaio = EMA daily al 31 gennaio
RSI monthly gennaio = RSI daily al 31 gennaio
MACD monthly gennaio = MACD daily al 31 gennaio
```

Per MACD:

```text
MACD line    = valore daily all’end-date
Signal line  = valore daily all’end-date
Histogram    = valore daily all’end-date
```

Questa regola mantiene:

* semantica daily;
* label invariate;
* coerenza con il close price del bucket;
* confronto stabile tra zoom diversi.

***

### 16.2 Bollinger Bands

Per Bollinger Bands si adotta una regola diversa, perché la banda rappresenta un intervallo e può beneficiare di una rappresentazione dell’escursione intra-bucket.

Decisione:

```text
Bollinger in vista aggregata usa una envelope aggregation.
```

Regola:

```text
upper  = massimo valore daily della upper band nel bucket
middle = valore daily della middle band all’end-date del bucket
lower  = minimo valore daily della lower band nel bucket
```

Esempio monthly:

```text
Gennaio 2026:
  upper  = max upper band tra 1 e 31 gennaio
  middle = middle band al 31 gennaio
  lower  = min lower band tra 1 e 31 gennaio
```

Questa scelta non rappresenta la Bollinger Band puntuale di fine periodo, ma un inviluppo visuale del bucket.

Va quindi documentata come:

```text
In vista settimanale/mensile, le Bollinger Bands mostrano l’inviluppo del periodo:
upper massimo del bucket, lower minimo del bucket, middle a fine periodo.
```

Motivazione:

* più informativa a zoom ampio;
* mostra meglio l’ampiezza potenziale della banda nel periodo;
* evita di perdere del tutto l’escursione intra-settimanale/mensile;
* mantiene comunque la middle coerente con l’end-date.

***

## 17. LTTB / sampling ECharts

L’eventuale sampling già presente in ECharts resta invariato.

Non fa parte della logica di questa feature.

Differenza concettuale:

```text
Aggregazione calendariale:
  crea punti settimanali/mensili semanticamente interpretabili.

Sampling visuale:
  riduce punti per preservare la forma visuale,
  ma non crea bucket finanziari.
```

Questa feature si occupa dei primi due livelli:

```text
1. scelta della risoluzione temporale;
2. costruzione della serie daily/weekly/monthly;
3. eventuale sampling ECharts preesistente lasciato invariato.
```

Se i punti diventano meno grazie all’aggregazione, il sampling avrà semplicemente meno lavoro o impatto marginale.

***

## 18. Badge di aggregazione

Quando la vista è diversa da daily, va mostrato un piccolo badge in alto a sinistra del grafico.

Regola:

```text
daily   → nessun badge
weekly  → badge “Settimanale”
monthly → badge “Mensile”
```

Il testo deve essere sintetico.

Non usare label lunghe tipo:

```text
Vista: Settimanale
Aggregazione: Mensile
```

ma solo:

```text
Settimanale
Mensile
```

Posizione raccomandata:

```text
alto a sinistra del plot/grafico
```

Il badge serve a evitare ambiguità, soprattutto nei grafici candlestick, dove una candela aggregata potrebbe essere scambiata per una candela giornaliera.

***

## 19. Flusso completo all’apertura

```text
1. Il componente riceve i dati daily dal backend/store.
2. Misura la larghezza effettiva del plot.
3. Determina il range iniziale visibile.
4. Calcola la densità daily sul range iniziale.
5. Applica la logica di selezione risoluzione.
6. Determina risoluzione iniziale:
     - daily
     - weekly
     - monthly
7. Se daily:
     usa dati originali.
8. Se weekly/monthly:
     verifica cache store.
     se non presente, calcola aggregazione.
9. Calcola/recupera segnali:
     - segnali calcolati su daily;
     - output downsampled secondo risoluzione scelta.
10. Aggrega/rimappa event marker.
11. Prepara tooltip e metadata bucket-aware.
12. Renderizza ECharts direttamente nella risoluzione scelta.
13. Mostra badge solo se weekly/monthly.
```

***

## 20. Flusso completo durante zoom/pan/resize

```text
1. L’utente interagisce con zoom, pan o resize.
2. ECharts aggiorna temporaneamente la vista.
3. Il componente riceve eventi dataZoom/resize.
4. Applica debounce.
5. Calcola visibleStartDate e visibleEndDate logici.
6. Misura widthPx corrente.
7. Calcola density della risoluzione corrente e delle candidate.
8. Applica hysteresis.
9. Se la risoluzione target è uguale alla corrente:
     non fare nulla.
10. Se la risoluzione target cambia:
     recupera aggregazione da cache, oppure calcolala lazy.
     rimappa range logico sui bucket target.
     rigenera serie principali.
     rigenera/downsample segnali.
     aggrega event marker per bucket.
     riallinea eventuali marker measure.
     aggiorna tooltip/badge.
     chiama setOption senza animazione di switch.
```

***

## 21. Componenti coinvolti

### Nuova utility condivisa

Proposta:

```text
timeSeriesAggregation.ts
```

Responsabilità concettuali:

* creazione bucket daily/weekly/monthly;
* mapping date → bucket;
* aggregazione linee a fine-periodo;
* aggregazione OHLCV;
* aggregazione staleness;
* aggregazione/downsample segnali;
* envelope aggregation Bollinger;
* aggregazione eventi per bucket;
* metadata bucket;
* helper per range logico vs range renderizzato.

***

### Store/cache

Lo store attuale va potenziato per conservare le viste derivate.

Concettualmente:

```text
sourceDailyData
sourceVersion

aggregations:
  daily
  weekly
  monthly

signals:
  dailyComputedOutput
  weeklyDownsampledOutput
  monthlyDownsampledOutput

events:
  dailyEvents
  weeklyBucketedEvents
  monthlyBucketedEvents
```

La cache è valida finché resta valida la sorgente daily da cui deriva.

***

### PriceChartFull

Responsabilità:

* orchestrare la risoluzione corrente;
* misurare width plot;
* ascoltare dataZoom;
* applicare debounce;
* applicare hysteresis;
* condividere la stessa risoluzione tra linea e candela;
* evitare animazioni nello switch;
* mostrare badge sintetico;
* gestire marker eventi aggregati;
* gestire measure mode bucket-aware.

***

### CandlestickChart

Responsabilità:

* ricevere dati già nella risoluzione corretta;
* renderizzare OHLCV;
* gestire volume aggregato coerente;
* non ricalcolare autonomamente una risoluzione diversa dal parent.

La risoluzione deve essere condivisa con `PriceChartFull`, così il toggle linea ↔ candela non produce disallineamenti.

***

### GrowthChart

Responsabilità:

* usare la stessa logica di risoluzione;
* aggregare le serie a fine-periodo;
* tooltip bucket-aware;
* badge se weekly/monthly.

***

### AllocationHistoryChart

Responsabilità:

* usare aggregazione fine-periodo;
* rappresentare allocazione a fine bucket;
* tooltip bucket-aware;
* badge se weekly/monthly.

***

### Tooltip helpers

Da rendere bucket-aware.

Devono supportare:

```text
daily:
  data singola

weekly:
  range settimana + valore end-date

monthly:
  mese + valore end-date

event marker aggregato:
  lista eventi reali contenuti nel bucket
```

***

### Measure mode

Da rendere bucket-aware separando:

```text
date reali usate per calcolo/tabella
bucket usati per rendering grafico
```

***

## 22. Decisioni consolidate

```text
- Backend invariato.
- Daily resta sorgente canonica.
- Weekly/monthly sono viste derivate client-side.
- Aggregazioni calcolate lazy.
- Aggregazioni salvate in store/cache.
- Cache invalidata solo quando cambia la sorgente daily o parametri invalidanti.
- Risoluzione iniziale scelta prima del primo rendering.
- Switch risoluzione senza animazione.
- Soglia basata su bucket/px.
- Hysteresis basata su bucket/px.
- Debounce obbligatorio sugli eventi dataZoom.
- Range logico preservato tramite date assolute.
- Range renderizzato derivato dai bucket che intersecano il range logico.
- Linee prezzo/NAV/Growth/serie derivate aggregate a fine-periodo.
- AllocationHistoryChart aggregato a fine-periodo.
- Candlestick OHLCV con regole standard.
- Staleness preso dall’end-date del bucket.
- Colorazione baseline basata sul valore end-date.
- Event marker aggregati per bucket.
- Tooltip eventi aggregati con date reali concatenate.
- Measure mode con date reali nel modello e bucket per rendering.
- Segnali calcolati sempre daily.
- EMA/RSI/MACD/linee segnale downsampled a end-date.
- Bollinger Bands aggregate come envelope:
    upper max bucket,
    lower min bucket,
    middle end-date.
- LTTB/sampling ECharts lasciato invariato.
- Badge mostrato solo se non daily:
    “Settimanale”
    “Mensile”
```

***

## 23. Punti ancora aperti

> **Aggiornato dopo i 7 piani implementativi derivati** (`chart_resolution/`): la maggior parte dei punti
> sotto sono stati chiusi con una decisione concreta nei documenti implementativi. Restano segnalati anche
> quelli chiusi, con riferimento a dove, per tracciabilità — non rimuoverli renderebbe difficile capire
> quali fossero le alternative scartate.

```text
- Valori numerici precisi delle soglie density alta/bassa.
  → CHIUSO: 1.30 (alta) / 0.80 (bassa) bucket/px — impl_plan_chart_resolution_00_foundation.md §7.2.
- Se density deve basarsi sui giorni calendario o sui punti effettivamente disponibili.
  → CHIUSO: sui bucket ottenuti raggruppando le date effettivamente visibili con mapDateToBucket(), non su
    un'approssimazione a giorni di calendario — impl_plan_chart_resolution_00_foundation.md §7.2.
- Se considerare la larghezza del plot intero o solo della grid interna effettiva.
  → CHIUSO: chartInstance.getWidth() (plot intero, non grid interna) — impl_plan_chart_resolution_00_foundation.md.
- Strategia visuale per marker aggregati con molti eventi.
  → ANCORA APERTO: impl_plan_chart_resolution_01_price_candlestick.md concatena tutti gli eventi reali nel
    tooltip del bucket senza un cap; nessun documento propone ancora una strategia di compattazione.
- Numero massimo di eventi da mostrare nel tooltip prima di compattare.
  → ANCORA APERTO, collegato al punto precedente.
- Posizionamento esatto del badge rispetto a titolo, legenda e toolbox.
  → CHIUSO: impl_plan_chart_resolution_05_badge_i18n.md fissa `top-2 left-28` per PriceChartFull (accanto
    al toggle chart-type esistente) e `top-2 left-2` per GrowthChart/AllocationHistoryChart.
- Se in futuro offrire una modalità alternativa “media periodo” per AllocationHistoryChart.
  → Confermato fuori scope per questa fase (fine-periodo unica regola) — resta un'idea per una vista
    analitica futura separata, non un punto bloccante.
- Se in futuro offrire Bollinger snapshot end-date come alternativa all’envelope.
  → Confermato fuori scope per questa fase (solo envelope) — resta un'idea futura, non un punto bloccante.
```

***

## 24. Sintesi finale

La feature introduce uno **zoom semantico temporale adattivo**.

Il frontend mantiene i dati daily come verità canonica, ma sceglie dinamicamente se visualizzare daily, weekly o monthly in base alla densità reale dei bucket rispetto ai pixel disponibili.

Le aggregazioni sono:

* client-side;
* lazy;
* cached nello store;
* invalidate solo quando cambia la sorgente;
* coerenti tra linea, candela, eventi, tooltip e measure mode.

Lo switch di risoluzione è netto e non animato.

La semantica generale è:

```text
daily:
  valore puntuale del giorno

weekly:
  valore di fine settimana / bucket settimanale

monthly:
  valore di fine mese / bucket mensile
```

Per i segnali:

```text
calcolo sempre daily;
visualizzazione aggregata tramite downsample dell’output.
```

Per Bollinger:

```text
vista aggregata come inviluppo del periodo:
upper massimo,
lower minimo,
middle end-date.
```

Il badge sintetico:

```text
Settimanale
Mensile
```

viene mostrato solo quando la vista non è giornaliera, così l’utente capisce immediatamente il livello temporale rappresentato senza appesantire l’interfaccia.

---

## Piani implementativi derivati

Questo studio (fattibilità + raffinamento) è stato tradotto in 7 piani implementativi (gap-analysis
stato-attuale → gap → risoluzione), un file per componente/workstream, in
[`chart_resolution/`](./chart_resolution/), scritti in parallelo da una flotta di agenti — nessuna riga di
codice sorgente è stata toccata finora, solo documentazione:

1. [`impl_plan_chart_resolution_00_foundation.md`](./impl_plan_chart_resolution_00_foundation.md)
   — nuova utility condivisa `timeSeriesAggregation.ts` (documento fondativo).
2. [`impl_plan_chart_resolution_01_price_candlestick.md`](./impl_plan_chart_resolution_01_price_candlestick.md)
   — `PriceChartFull` + `CandlestickChart`.
3. [`impl_plan_chart_resolution_02_growth_chart.md`](./impl_plan_chart_resolution_02_growth_chart.md) —
   `GrowthChart`.
4. [`impl_plan_chart_resolution_03_allocation_history.md`](./impl_plan_chart_resolution_03_allocation_history.md)
   — `AllocationHistoryChart`.
5. [`impl_plan_chart_resolution_04_signals_overlay.md`](./impl_plan_chart_resolution_04_signals_overlay.md)
   — downsample segnali overlay (9 tipi).
6. [`impl_plan_chart_resolution_05_badge_i18n.md`](./impl_plan_chart_resolution_05_badge_i18n.md) —
   componente `ResolutionBadge` + i18n.
7. [`impl_plan_chart_resolution_06_compact_cards.md`](./impl_plan_chart_resolution_06_compact_cards.md)
   — `PriceChartCompact`/`LineChart` (ramo compact) nelle card `AssetCard`/`FxCard` (`/assets`, `/fx`); caso
   statico senza `dataZoom`, niente isteresi né badge pill.

Vedi anche [`README.md`](../README.md) della cartella per la tabella riassuntiva di stato.


