# Guida Rapida — Toolbar Responsive (PageToolbar + DateRangePicker)

> ⚠️ **Round 11/11.1/11.2**: la tabella soglie, i comandi console che citano `actionsColumn`/
> `.actionsStacked`, la nota border-box, e l'intera sezione "🗺️ Layout atteso per fascia" più in
> fondo a questo documento sono SUPERATI — vedi **`GUIDA-TOOLBAR-RESPONSIVE-v2.md`** per il modello
> corretto e aggiornato (fascia `'mobile'` rinominata/formalizzata in `oneColumn`; le Azioni si
> spostano SOTTO già a `oneColumn`; a `stackFilters` le Azioni sono una colonna verticale 4×1 CON
> etichetta, non 2×2; soglie confrontate in content-box, non border-box). Il resto di questo
> documento (algoritmo badge jolly, `effectiveMaxWidth`, gotcha "verify+shed", checklist
> estensione) resta valido e NON è duplicato in v2.

**File principali**:
- `frontend/src/lib/utils/layout/responsiveLayout.svelte.ts` — soglie di layout + registro debug
- `frontend/src/lib/components/ui/toolbar/PageToolbar.svelte` — shell toolbar (tutte e 6 le pagine)
- `frontend/src/lib/components/ui/date/DateRangePicker.svelte` — date picker + badge "jolly" auto-fit

---

## 🎯 Panoramica del sistema

Il layout responsive della toolbar (dashboard, broker-detail, assets, forex — 6 pagine in
totale) usa un `ResizeObserver` sul contenitore reale per decidere come disporre filtri/azioni,
**senza breakpoint CSS fissi** — i confini sono numeri in pixel, configurabili per pagina e
**tarabili live da console del browser**, senza rebuild.

**Vocabolario unico**: soglia e `layoutMode` risultante usano ESATTAMENTE lo stesso nome (dal
Round 10.2 — prima erano due vocabolari diversi da tenere a mente, es. soglia `oneRow` → modalità
`'wide'`; fonte di confusione costante, ora eliminata). Dal Round 11 anche l'ultima eccezione è
sparita: la fascia che qui sotto veniva chiamata `'mobile'` (senza soglia propria) è stata
rinominata/formalizzata in `oneColumn`, con soglia dedicata — **vedi `GUIDA-TOOLBAR-RESPONSIVE-v2.md`
per la tabella e il comportamento aggiornati**, la riga sotto è mantenuta solo per contesto storico.

| Larghezza reale del contenitore | `layoutMode` risultante |
|---|---|
| ≥ `oneRow` | `'oneRow'` |
| tra `denseRow` e `oneRow` | `'denseRow'` |
| tra `stackFilters` e `denseRow` | `'stackFilters'` |
| tra `oneColumn` e `stackFilters` | `'oneColumn'` (vedi v2 — Round 10 la chiamava `'mobile'`, senza soglia propria) |
| < `oneColumn` | `'iconOnly'` |

> ⚠️ **SUPERATO (Round 11.1)** — questo box descriveva il tentativo border-box del Round 10.3, poi
> **invertito di nuovo a content-box** dopo misurazione diretta dell'utente (border-box era la
> direzione sbagliata: si debugga leggendo l'INTERNO, non il rendering completo col padding). Le
> soglie confrontano di nuovo `contentRect.width` (content-box, ESCLUDE il `p-4` = 32px di padding
> orizzontale della barra) — vedi `GUIDA-TOOLBAR-RESPONSIVE-v2.md` per lo stato corrente. Testo
> originale del Round 10.3 mantenuto sotto solo per contesto storico:
>
> ~~La larghezza confrontata con le soglie è quella BORDER-BOX — la stessa che vedi passando il
> mouse su un elemento in devtools, o leggendo `getBoundingClientRect().width`/`offsetWidth`.~~

Il `DateRangePicker` (in modalità `align="start"`, usata da tutte e 6 le pagine) aggiunge un
secondo livello: badge "jolly" (3Y/5Y/10Y/MTD/QTD/WTD) che appaiono automaticamente solo se c'è
spazio libero da riempire, misurati via JS in tempo reale (non con soglie CSS fisse) — anche la
loro `max-width` massima è tarabile live (due valori separati, uno per 1-riga e uno per 2-righe —
vedi sotto). La scelta 1-riga/2-righe del picker NON è autonoma (misura del contenuto) — è una
decisione guidata da soglia (`oneRow`, tramite `layoutMode`), per dare pieno controllo su tutta la
riga, come richiesto esplicitamente dall'utente.

---

## 🔧 Le soglie di `PageToolbar`/pagina

> ⚠️ Tabella superata da Round 11 — `actionsColumn` non esiste più nel codice, sostituita da
> `oneColumn` (fascia di primo livello, non più sotto-fascia opzionale). Vedi
> `GUIDA-TOOLBAR-RESPONSIVE-v2.md` per la tabella corrente. Righe mantenute qui per contesto storico.

| Soglia | Cosa cambia a questo confine |
|---|---|
| `oneRow` | **DateRangePicker: 1 riga sola** (badge jolly a misura reale). Sotto: **sempre 2 righe interne** — decisione diretta di questa soglia (via `layoutMode`), non una misura autonoma del contenuto. Al confine, i badge jolly totali mostrati AUMENTANO (2 righe = più spazio totale), poi tornano a diminuire via via che ci si restringe ulteriormente verso `denseRow` |
| `denseRow` | Nessun cambio di struttura in `PageToolbar` (Centro ancora affiancato al picker, Azioni ancora 2×2) — alcune pagine (es. assets lista) usano questo confine per riorganizzare il PROPRIO contenuto "Centro" |
| `stackFilters` | Il Centro si sposta SOTTO il DateRangePicker (i due si impilano in colonna, distribuzione "giustificata" — allineata a sinistra, mai centrata, larghezza allineata al picker via `effectiveMaxWidth`, vedi sotto). Azioni restano 2×2 con etichetta, AFFIANCATE alla colonna Picker+Centro (non sotto) |
| ~~`actionsColumn` (opzionale)~~ | **Superata (Round 11)** — era pensata come sotto-fascia dentro `'mobile'` (Azioni 4×1 verticale ma ancora affiancate). Sostituita da `oneColumn`: vedi v2 |
| `iconOnly` | **Tutto impilato, incluse le Azioni** (in v1; da Round 11 le Azioni si impilano già a `oneColumn` — vedi v2) — Azioni diventano riga di sole icone (nessuna etichetta) — il fallback più stretto, per quando anche 2×2-con-etichetta non ci sta più |
| `labelHide` | *(asse indipendente)* Sotto questa larghezza le etichette testuali dei bottoni azione scompaiono (di solito = `iconOnly`, stesso valore, così le icone-sole compaiono ESATTAMENTE insieme alla scomparsa delle etichette) |

### Dove sono definite (una chiamata per pagina)

Tutte e 6 le pagine usano `<PageToolbar thresholds={{...}}>` (stesso componente condiviso — un
fix fatto in `PageToolbar.svelte` si propaga automaticamente a tutte, non serve più replicarlo
pagina per pagina).

| Pagina | File | Nome registro console | Valori attuali |
|---|---|---|---|
| Dashboard | `routes/(app)/dashboard/+page.svelte` | `dashboard` | `oneRow:1000 denseRow:810 stackFilters:430 oneColumn:365 iconOnly:330 labelHide:330` |
| Broker Detail | `routes/(app)/brokers/[id]/+page.svelte` | `brokerDetail` | `oneRow:1000 denseRow:800 stackFilters:560 oneColumn:470 iconOnly:330 labelHide:330` |
| Assets (lista) | `routes/(app)/assets/+page.svelte` | `assetsList` | `oneRow:1340 denseRow:1060 stackFilters:500 oneColumn:410 iconOnly:330 labelHide:330` |
| Assets (dettaglio) | `routes/(app)/assets/[id]/+page.svelte` | `assetDetail` | `oneRow:1090 denseRow:870 stackFilters:570 oneColumn:445 iconOnly:330 labelHide:330` |
| Forex (lista) | `routes/(app)/fx/+page.svelte` | `fxList` | `oneRow:1120 denseRow:760 stackFilters:520 oneColumn:420 iconOnly:330 labelHide:330` |
| Forex (dettaglio) | `routes/(app)/fx/[pair]/+page.svelte` | `fxDetail` | `oneRow:790 denseRow:620 stackFilters:520 oneColumn:420 iconOnly:330 labelHide:330` |

> ⚠️ I valori di `oneColumn` sopra sono gli stessi numeri usati per `actionsColumn` in v1 (stime
> iniziali, mai tarate live) — usa il flusso di taratura sotto per trovare il valore giusto pagina
> per pagina. `labelHide`/`iconOnly` sono a **330** ovunque come default di partenza (Round 10.2) —
> anche questi ancora da rifinire pagina per pagina.

---

## 🎈 I badge "jolly" del `DateRangePicker`

Oltre ai 6 preset fissi (1W/1M/3M/6M/1Y/2Y) e al gruppo finale fisso (YTD/Tutti/Personalizzato),
esistono **2 pool opzionali**, mostrate solo se c'è spazio:

- **Pool "durate"** (`durationFillPresets`): 3Y, 5Y, 10Y — estende la progressione anni
- **Pool "periodi"** (`periodFillPresets`): MTD, QTD, WTD — periodi "da inizio X a oggi"

L'algoritmo (`measureAndFill()` in `DateRangePicker.svelte`) misura le larghezze REALI (badge
nascosti `absolute invisible` sempre renderizzati per la misura) e decide:

1. **Quante righe** (1 o 2): NON è una misura del contenuto — è la prop `layoutMode` (passata
   dalla pagina, proveniente da `PageToolbar`) a deciderlo direttamente: `layoutMode === 'oneRow'`
   (cioè larghezza ≥ soglia `oneRow`) → 1 riga; qualsiasi altro valore di `layoutMode`
   (`'denseRow'`, `'stackFilters'`, `'oneColumn'`, `'iconOnly'`) → SEMPRE 2 righe. Una pagina che non
   passa `layoutMode` ottiene il default 1-riga (comportamento pre-Round-10).
2. **Quanti badge jolly** in ciascuna riga: QUESTO resta a misura reale (continuo, non a
   soglia) — se 1 riga sola, i badge fissi + quanti jolly ci stanno, presi ALTERNANDO dalle
   2 pool (budget condiviso); se 2 righe, ognuna pesca SOLO dalla propria pool nel proprio
   spazio residuo (riga 1 = durate, riga 2 = periodi).

> 💡 Perché questo cambio: l'utente ha richiesto esplicitamente che la scelta 1-vs-2-righe sia
> controllata dalla soglia `oneRow`, non decisa autonomamente dal componente in base al
> contenuto — "abbiamo le soglie apposta per avere controllo su tutta la riga". Al confine
> `oneRow`, passando da 1 a 2 righe, la capacità totale aumenta (2 righe hanno più spazio
> complessivo di 1), quindi il numero di badge jolly mostrati SALE in quel momento, per poi
> tornare a scendere via via che ci si restringe ulteriormente verso `denseRow`.

### `maxWidth`/`maxWidthTwoRow` — quanto può crescere il DateRangePicker

Due prop separate, una per modalità riga (Round 10.1 — un unico valore condiviso rendeva il
layout a 2 righe sproporzionato: ogni riga molto più larga del contenuto che porta, con grandi
vuoti lasciati da `justify-between`):

| Prop | Si applica quando | Default |
|---|---|---|
| `maxWidth` | `isSingleRow` è vero (`layoutMode === 'oneRow'`, 1 riga) | **740px** (tarato dall'utente — prima era 672px, la classe fissa Tailwind `max-w-2xl`) |
| `maxWidthTwoRow` | `isSingleRow` è falso (`layoutMode` è tutto il resto, 2 righe) | **390px** (tarato dall'utente) |

Il tetto massimo di larghezza che il picker può occupare quando condivide la riga con altri
filtri (valuta, filtro broker, ecc.). Sotto il cofano diventa uno `style="max-width: {}px"`
inline (necessario per essere veramente dinamico — le classi Tailwind sono fisse a build-time);
il valore effettivo (`effectiveMaxWidth`) sceglie automaticamente tra le due prop in base a
`isSingleRow`, quindi passa da uno all'altro da solo attraversando la soglia `oneRow` — nessun
wiring aggiuntivo richiesto.

### `effectiveMaxWidth` (bindable) — allineare il Centro alla larghezza REALE del picker

Quando `filtersStacked` è vero (Centro impilato SOTTO il picker), il Centro deve avere la STESSA
larghezza del picker (non quella del contenitore/colonna esterna, che resta più largo per non
lasciare un vuoto enorme rispetto alle Azioni — vedi `stackFilters` sotto). Il picker espone il
proprio `effectiveMaxWidth` corrente come prop **bindable**:

```svelte
<DateRangePicker ... bind:effectiveMaxWidth={pickerMaxWidth} />
<div class="{filtersStacked ? 'w-full' : ''}" style={filtersStacked && pickerMaxWidth ? `max-width: ${pickerMaxWidth}px` : ''}>
    <!-- contenuto Centro -->
</div>
```

`pickerMaxWidth` si aggiorna live insieme a `pickerConfig.maxWidthTwoRow` (anche da console,
senza resize) — il Centro resta sempre pixel-allineato al picker durante il tuning. Pattern
usato da dashboard, broker-detail, forex lista (Round 10.3 — bug: prima il Centro usava solo
`w-full`, che lo stendeva alla larghezza dell'intera colonna esterna — più larga del picker
stesso — creando un bordo destro disallineato).

### ⚠️ Gotcha noto — perché esiste ancora il "verify+shed"

L'algoritmo di misura usa larghezze REALI (non stime), ma un margine piccolo (badge nascosto di
misura vs badge reale, o il gap CSS che non corrisponde esattamente al valore hardcoded) può
farlo sbagliare **per un solo badge** a certe larghezze — SOLO sul CONTEGGIO dei jolly (dal
Round 10 la scelta 1-vs-2-righe non può più sbagliare, è fissata da `oneRow`). Se questo
succede, il CSS nativo (`flex-wrap`) spacca la riga interessata in 2 SENZA che il JS se ne
accorga — e siccome il contenitore misurato cambia solo di ALTEZZA (non di larghezza) quando
questo avviene, il calcolo sbagliato **si ripete identico per sempre**, anche a resize
successivi: un "punto fisso sbagliato" che resta bloccato finché non si ricarica la pagina.

Per questo esiste una verifica DOPO il render (`verifyNoWrap()`, con `tick()`): controlla se i
badge di ogni riga condividono davvero la stessa coordinata Y — se non la condividono, TOGLIE un
badge jolly e riverifica (fino a 6 tentativi, il massimo di jolly possibili). Gira ad OGNI
ricalcolo, non solo al primo, quindi corregge anche un eventuale errore futuro invece di lasciarlo
bloccato.

**Se noti ancora un wrap indesiderato**: prima di sospettare un bug nuovo, controlla in console
(`window.__lfLayouts.<nome>.pickerConfig.maxWidth`) se stai testando con un `maxWidth` molto
stretto e pochi badge fissi (caso limite: se anche 0 badge jolly non entrano, la verifica non ha
più nulla da togliere e accetta il wrap come ultima spiaggia — succede solo con `maxWidth`
irragionevolmente piccolo).

---

## 💻 Comandi Console — Test Live (F12 → Console)

Tutte le pagine registrano la propria istanza su `window.__lfLayouts.<nome>` — **sempre
disponibile**, anche sulla build di produzione locale, non serve alcun flag debug.

```js
// Elenco pagine disponibili (dipende da quale pagina hai aperto)
window.__lfLayouts

// Vedi le soglie attuali di una pagina
window.__lfLayouts.dashboard.thresholds
// { oneRow: 1000, denseRow: 810, stackFilters: 430, oneColumn: 365, iconOnly: 330, labelHide: 330 }

// Cambia una soglia — ricalcola SUBITO, nessun resize richiesto
window.__lfLayouts.dashboard.thresholds.iconOnly = 300

// Taratura della soglia "oneColumn" (Round 11 — dove le Azioni si spostano sotto Picker+Centro)
window.__lfLayouts.dashboard.thresholds.oneColumn = 380

// Leggi la modalità corrente risultante
window.__lfLayouts.dashboard.layoutMode
// 'oneRow' | 'denseRow' | 'stackFilters' | 'oneColumn' | 'iconOnly'

// Cambia la max-width del DateRangePicker — una per modalità riga, entrambe live, nessun resize
window.__lfLayouts.dashboard.pickerConfig.maxWidth = 740        // usata quando è a 1 riga (oneRow)
window.__lfLayouts.dashboard.pickerConfig.maxWidthTwoRow = 390  // usata quando è a 2 righe (tutto il resto)

// 🩺 Diagnostica rapida: correla larghezza REALE content-box (Round 11.1 — quella confrontata
// con le soglie; getBoundingClientRect() è border-box, quindi sottraiamo il padding) con la
// modalità risultante e le soglie stesse, IN UN COLPO SOLO — utile per capire perché una soglia
// "non sembra scattare" (di solito: non si è ancora restretto abbastanza, non un bug)
(() => {
    const l = window.__lfLayouts.dashboard;
    const bar = document.querySelector('[data-testid="dashboard-filter-bar"]');
    const cs = bar && getComputedStyle(bar);
    const contentWidth = bar && cs ? bar.getBoundingClientRect().width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) : undefined;
    console.table({realWidthContentBox: contentWidth, layoutMode: l.layoutMode, ...l.thresholds});
})()
```

> ℹ️ `.actionsStacked`/`thresholds.actionsColumn` (v1, sotto-fascia "azioni a colonna 4×1") non
> esistono più — vedi `GUIDA-TOOLBAR-RESPONSIVE-v2.md` per il modello Round 11 (`oneColumn`).

Nomi disponibili: `dashboard`, `brokerDetail`, `assetsList`, `assetDetail`, `fxList`, `fxDetail`
(cambia sia il nome nel registro sia il `data-testid` del selettore nello snippet diagnostico
sopra — vedi tabella soglie per il `data-testid`/`filterRowTestId` di ciascuna pagina).

Nomi disponibili: `dashboard`, `brokerDetail`, `assetsList`, `assetDetail`, `fxList`, `fxDetail`.

### Flusso di taratura consigliato

1. Apri la pagina che vuoi tarare, F12 → Console.
2. Ridimensiona la finestra fino al punto in cui il comportamento ti sembra sbagliato.
3. Leggi `window.__lfLayouts.<nome>.thresholds` per vedere i valori attuali.
4. Modifica il campo che sospetti (es. `iconOnly`) e osserva il cambiamento immediato.
5. Quando sei soddisfatto, riporta il valore trovato: aggiorna la riga corrispondente nel codice
   (vedi tabella sopra per il file esatto).

---

## 📁 Estendere il sistema a una nuova pagina — checklist

Per una NUOVA pagina che vuole lo stesso pattern (breakpoint responsive + badge jolly nel
DateRangePicker):

1. Usa `<PageToolbar thresholds={{oneRow, denseRow, stackFilters, oneColumn, iconOnly,
   labelHide}} layoutDebugName="nomeUnivoco">` (tutte e 5 le soglie sono obbligatorie, Round 11 —
   vedi `GUIDA-TOOLBAR-RESPONSIVE-v2.md`) — le zone `filters`/`summary` ricevono
   `{layoutMode, isStacked, filtersStacked}`, `actions` riceve
   `{layoutMode, showActionLabels, stretchActions}`. Usa questi flag semantici,
   MAI `layoutMode === 'oneColumn'` direttamente (la semantica di ogni livello può cambiare in
   futuro, solo `PageToolbar` dovrebbe doversi aggiornare) — in particolare usa `filtersStacked`
   (non `isStacked`) per qualsiasi stile "il mio contenuto Centro deve diventare full-width/
   giustificato quando il Picker si impila" (`isStacked` è vero nelle due fasce più strette,
   `oneColumn` e `iconOnly`, dove impilano TUTTO incluse le Azioni — vedi v2 per il dettaglio).
2. **DateRangePicker**: passa `align="start"` + `layoutMode={layoutMode}` (dallo stesso snippet
   `filters`/`summary` — OBBLIGATORIO: senza questa prop il picker resta sempre a 1 riga,
   ignorando le soglie della pagina) + lo stesso `debugName="nomeUnivoco"` usato al punto 1 (così
   soglie e `maxWidth` finiscono sulla stessa voce del registro console). Se il Centro deve
   allinearsi in larghezza al picker quando `filtersStacked` (vedi sezione `effectiveMaxWidth`
   sopra), fai anche `bind:effectiveMaxWidth={miaVariabileLocale}` sul picker e applicalo come
   `max-width` inline sul div Centro. Se la pagina ha bisogno di leggere `layoutMode` ANCHE fuori
   dalle snippet (es. un testo che cambia in base al layout, non solo dentro filters/actions),
   usa `bind:layoutMode={miaVariabile}` su `<PageToolbar>` E passa quella stessa variabile al
   picker (vedi `assets/[id]/+page.svelte` o `fx/[pair]/+page.svelte` per un esempio — entrambe
   fanno `layoutMode={pageLayoutMode}`).
3. Se la pagina ha altri elementi da affiancare al DateRangePicker nella zona `filters` (valuta,
   filtro broker, ricerca, ecc.), dagli **`shrink-0`** — MAI lasciarli con lo shrink di default:
   solo il DateRangePicker deve restringersi/perdere badge quando lo spazio si stringe, gli altri
   elementi restano alla loro dimensione naturale (bug reale trovato e corretto in Round 9 — il
   gruppo valuta/broker andava a capo invece di lasciar restringere il picker).

---

## 📌 Storico (per contesto)

Questo sistema è stato costruito in modo iterativo (round di bugfix guidati da feedback visivo)
su dashboard/broker-detail (Round 1-6), poi esteso ad assets/forex (Round 6-7), poi rifinito con
soglia `compact` ovunque + tuning live da console (Round 7) + max-width dinamica e fix del wrap
prematuro (Round 8) + migrazione REALE di assets/forex a `<PageToolbar>` condiviso (prima
replicavano solo le stesse classi CSS a mano) + fix wrap gruppo valuta/broker + floor WTD
6gg invece di 14gg (Round 9) + righe del DateRangePicker rese threshold-driven invece che
autonome, nuova soglia `actionsColumn` per la sotto-fascia bottoni-a-colonna, rinomina di tutte
le soglie con nomi più parlanti (Round 10) + `maxWidthTwoRow` separato da `maxWidth` per
correggere l'estetica del layout a 2 righe, sproporzionata con un unico valore condiviso
(Round 10.1) + rinomina dei VALORI `layoutMode` per combaciare 1:1 coi nomi soglia (vocabolario
unico), split `isStacked`/`filtersStacked` per far restare le Azioni affiancate al Picker+Centro
fino a `iconOnly`, `labelHide`/`iconOnly` a 330 di default ovunque (Round 10.2) + fix
border-box/content-box del `ResizeObserver` (le soglie ora combaciano esattamente con le
larghezze lette in devtools) + `effectiveMaxWidth` bindable per allineare il Centro al Picker in
pixel quando impilati (Round 10.3) + rinomina/formalizzazione della fascia `'mobile'` in
`'oneColumn'` con soglia propria (sostituisce `actionsColumn`), `isStacked` (Azioni sotto
Picker+Centro) spostato dalla soglia `iconOnly` alla soglia `oneColumn` — le Azioni restano un
2×2 con etichetta a `oneColumn`, perdono l'etichetta e diventano riga icone solo a `iconOnly`
(Round 11 — v1 documentava la direzione sbagliata del comportamento atteso in questa fascia, vedi
v2) + `ResizeObserver` invertito di nuovo a content-box (Round 11.1 — misurazione diretta
dell'utente ha mostrato che il fix border-box del Round 10.3 andava nella direzione sbagliata:
si debugga leggendo l'interno del contenitore, non il rendering completo col padding — vedi v2).
Non esiste un unico "piano madre" per questo lavoro — la
cronologia completa con diagnosi round-per-round è nella sessione dell'agente che lo ha
implementato, non riportata qui per brevità. Questa guida documenta lo **stato attuale**, non la
storia.

---

## 🗺️ Layout atteso per fascia (alto livello)

> ⚠️ **Superata da Round 11** — questa sezione descrive il modello PRE-Round-11 (fascia `'mobile'`
> senza soglia propria, Azioni affiancate fino a `iconOnly`). Vedi **`GUIDA-TOOLBAR-RESPONSIVE-v2.md`**
> per il modello corrente e corretto. Mantenuta qui solo per contesto storico/diff.

Tutte le topbar condividono la stessa struttura concettuale a 3-4 zone:

- **DateRangePicker** (sempre a sinistra, `align="start"`)
- **Centro** — contenuto specifico per pagina, varia:

  | Pagina | Cosa c'è nel "Centro" |
  |---|---|
  | Dashboard | Valuta + filtro broker |
  | Broker Detail | Valuta |
  | Assets lista | Ricerca + Attivo/Inattivo + Tipo + Valuta + Reset (un mini blocco 2×2 a sua volta) |
  | Assets dettaglio | `AssetPriceSummary` (prezzo + delta) — zona `summary` |
  | Forex lista | Coppia valute (2 select) + Reset |
  | Forex dettaglio | `FxPriceSummary` (tasso + delta) — zona `summary` |

- **Azioni** (sempre AFFIANCATE al blocco Picker+Centro quando `layoutMode` è `'oneRow'`/
  `'denseRow'`/`'stackFilters'`/`'mobile'`; SOTTO tutto il resto solo quando è `'iconOnly'`)
- **Tab** (solo dashboard e broker-detail — riga a parte, sotto tutto il resto)

> ✅ Il DateRangePicker NON decide da solo se stare su 1 o 2 righe interne — è la soglia `oneRow`
> a deciderlo direttamente (`layoutMode === 'oneRow'` → 1 riga, qualsiasi altro valore → sempre
> 2 righe). Il conteggio badge jolly PER riga resta a misura reale (continuo) — cambia solo CHI
> decide 1-vs-2-righe, non il riempimento fine.
>
> ✅ **Round 10.2**: Picker+Centro (`filtersStacked`) e Azioni (`isStacked`) hanno soglie di stack
> DIVERSE — Picker+Centro si impilano già da `stackFilters` in poi, ma le Azioni restano
> AFFIANCATE a quella colonna fino a `iconOnly` incluso (unica fascia in cui TUTTO, Azioni
> comprese, si impila). Prima di questo fix le Azioni scendevano sotto un'intera fascia troppo
> presto (già in "mobile"), bug segnalato dall'utente e corretto.

### ONE ROW (`layoutMode === 'oneRow'`, sopra la soglia `oneRow`) — tutto affiancato, 1 riga, badge jolly al completo

```
[ DateRangePicker (1 riga, jolly al completo) │ Centro ]  ───────────  [ 2×2 con etichetta ]
                                                                        [ Tab Tab Tab ]  (con etichetta — solo dashboard/broker)
```

- Riga unica: `[DateRangePicker] [Centro]` a sinistra, Azioni a destra (`justify-between`).
- Azioni: griglia 2×2 CON etichetta testuale.
- Tab (se presenti): riga sotto, CON etichetta.

### DENSE ROW (`layoutMode === 'denseRow'`, tra `denseRow` e `oneRow`) — stessa struttura, 2 righe

```
[ DateRangePicker (2 righe interne) │ Centro ]  ───────────  [ 2×2 con etichetta ]
                                                               [ Tab Tab Tab ]  (con etichetta)
```

- Stessa struttura esterna di `oneRow` (Centro ancora affiancato, Azioni ancora 2×2) — nessun
  cambio di layout in `PageToolbar`, solo il picker che ha 2 righe invece di 1.
- Il picker passa a 2 righe interne ESATTAMENTE al confine `oneRow` (non gradualmente) — con più
  spazio disponibile (2 righe) il numero di badge jolly totali mostrati AUMENTA rispetto a
  subito prima del confine, poi torna a diminuire (misura reale, continua) via via che ci si
  restringe verso `denseRow`.
- Centro (valuta/ricerca/...) NON si restringe mai (`shrink-0`) — è il picker che cede spazio.
- Alcune pagine (es. assets lista) usano il confine `denseRow` per riorganizzare il PROPRIO
  contenuto "Centro" (es. il blocco ricerca+filtri passa da inline a un blocco 2 righe interno),
  pur restando il Centro affiancato al picker (non sotto) per tutta la fascia `denseRow`.

### STACK FILTERS (`layoutMode === 'stackFilters'`, tra `stackFilters` e `denseRow`) — Picker+Centro impilati, azioni 2×2 ANCORA affiancate

```
[ DateRangePicker (2 righe) ]               [ Azione1 (con etichetta) ]
[ Centro                    ]               [ Azione2 (con etichetta) ]
                                            [ Azione3 (con etichetta) ]
                                            [ Azione4 (con etichetta) ]
                          [ Tab Tab Tab ]  (con etichetta)
```

- DateRangePicker e Centro si impilano in colonna (uno sopra l'altro), distribuzione
  "giustificata" (allineata a sinistra, mai centrata, larghezza del Centro allineata pixel-perfect
  al picker via `effectiveMaxWidth`, vedi sezione dedicata sopra) — ma questa colonna resta
  AFFIANCATA alle Azioni (non sotto) — `justify-between` ancora attivo sulla riga esterna.
- Azioni: restano griglia 2×2 con etichetta.


### oneColumn
[ DateRangePicker (2 righe) ]
[ Centro                    ]
[ 2×2 con etichetta ]


### iconOnly
[ DateRangePicker (2 righe) ]
[ Centro                    ]
       🔧  ⚙  ↻  …          (solo icone, riga centrata, va a capo se serve)
       🏠  📊  💰           (tab solo icone, se presenti)
