# Guida Rapida — Toolbar Responsive (PageToolbar + DateRangePicker)

**File principali**:
- `frontend/src/lib/utils/layout/responsiveLayout.svelte.ts` — soglie di layout + registro debug
- `frontend/src/lib/components/ui/toolbar/PageToolbar.svelte` — shell toolbar (dashboard, broker-detail)
- `frontend/src/lib/components/ui/date/DateRangePicker.svelte` — date picker + badge "jolly" auto-fit

---

## 🎯 Panoramica del sistema

Il layout responsive della toolbar (dashboard, broker-detail, assets, forex — 6 pagine in
totale) usa un `ResizeObserver` sul contenitore reale per decidere come disporre filtri/azioni,
**senza breakpoint CSS fissi** — i confini sono numeri in pixel, configurabili per pagina e
**tarabili live da console del browser**, senza rebuild.

### ⚠️ Due vocabolari — da tenere a mente per capire il resto della guida

| Cosa | Dove vive | Nomi |
|---|---|---|
| **Soglie** (input, una per pagina) | prop `thresholds={{...}}` di `<PageToolbar>` | `oneRow`, `denseRow`, `stackFilters`, `actionsColumn` *(opzionale)*, `iconOnly`, `labelHide` |
| **`layoutMode`** (output calcolato, letto nel codice) | valore restituito da `createResponsiveLayout()` — es. `layoutMode === 'wide'` | `'wide'`, `'tablet'`, `'tablet-s'`, `'mobile'`, `'compact'` |

Le **soglie** sono state rinominate (Round 10) per essere descrittive di cosa succede a quel
confine. Il valore **`layoutMode`** risultante, invece, usato in tutti i confronti nel codice
(`layoutMode === 'wide'` ecc.), mantiene i nomi storici — cambiarli avrebbe richiesto toccare
ogni confronto sparso nei 6 file pagina per nessun beneficio pratico. Mappa tra i due:

| Larghezza reale del contenitore | `layoutMode` risultante |
|---|---|
| ≥ `oneRow` | `'wide'` |
| tra `denseRow` e `oneRow` | `'tablet'` |
| tra `stackFilters` e `denseRow` | `'tablet-s'` |
| tra `iconOnly` e `stackFilters` | `'mobile'` (con sotto-fascia opzionale `actionsColumn`, vedi sotto) |
| < `iconOnly` | `'compact'` |

Il `DateRangePicker` (in modalità `align="start"`, usata da tutte e 6 le pagine) aggiunge un
secondo livello: badge "jolly" (3Y/5Y/10Y/MTD/QTD/WTD) che appaiono automaticamente solo se c'è
spazio libero da riempire, misurati via JS in tempo reale (non con soglie CSS fisse) — anche la
loro `max-width` massima è tarabile live (due valori separati, uno per 1-riga e uno per 2-righe —
vedi sotto). **Dal Round 10**, la scelta 1-riga/2-righe del picker NON è più autonoma (misura del
contenuto) — è diventata anch'essa una decisione guidata da soglia (`oneRow`, tramite
`layoutMode`), per dare pieno controllo su tutta la riga, come richiesto esplicitamente
dall'utente.

---

## 🔧 Le soglie di `PageToolbar`/pagina

| Soglia | `layoutMode` che introduce | Cosa cambia a questo confine |
|---|---|---|
| `oneRow` | `'wide'` (sopra) | **DateRangePicker: 1 riga sola** (badge jolly a misura reale). Sotto: **sempre 2 righe interne** — decisione diretta di questa soglia (via `layoutMode`), non più una misura autonoma del contenuto. Al confine, i badge jolly totali mostrati AUMENTANO (2 righe = più spazio totale), poi tornano a diminuire via via che ci si restringe ulteriormente verso `denseRow` |
| `denseRow` | `'tablet'` | Nessun cambio di struttura in `PageToolbar` (Centro ancora affiancato al picker, Azioni ancora 2×2) — alcune pagine (es. assets lista) usano questo confine per riorganizzare il PROPRIO contenuto "Centro" |
| `stackFilters` | `'tablet-s'` | Il Centro si sposta SOTTO il DateRangePicker (i due si impilano in colonna, distribuzione "giustificata" — allineata a sinistra, mai centrata). Azioni restano 2×2 con etichetta |
| `actionsColumn` *(opzionale)* | sotto-fascia dentro `'mobile'` | Sopra questo valore (ma sotto `stackFilters`): Azioni diventano colonna verticale 4×1 con etichetta. Sotto questo valore (ma sopra `iconOnly`): Azioni tornano a griglia 2×2. Omettila per avere sempre 2×2 fino a `iconOnly` (comportamento pre-Round-10) |
| `iconOnly` | `'compact'` (sotto) | **Tutto impilato**, Azioni diventano riga di sole icone (nessuna etichetta) — il fallback più stretto, per quando anche 2×2-con-etichetta non ci sta più |
| `labelHide` | *(asse indipendente)* | Sotto questa larghezza le etichette testuali dei bottoni azione scompaiono (di solito = `iconOnly`, stesso valore, così le icone-sole compaiono ESATTAMENTE insieme alla scomparsa delle etichette) |

### Dove sono definite (una chiamata per pagina)

Tutte e 6 le pagine usano `<PageToolbar thresholds={{...}}>` (stesso componente condiviso — un
fix fatto in `PageToolbar.svelte` si propaga automaticamente a tutte, non serve più replicarlo
pagina per pagina).

| Pagina | File | Nome registro console | Valori attuali |
|---|---|---|---|
| Dashboard | `routes/(app)/dashboard/+page.svelte` | `dashboard` | `oneRow:1000 denseRow:810 stackFilters:430 actionsColumn:365 iconOnly:300 labelHide:320` |
| Broker Detail | `routes/(app)/brokers/[id]/+page.svelte` | `brokerDetail` | `oneRow:1000 denseRow:800 stackFilters:560 actionsColumn:470 iconOnly:380 labelHide:380` |
| Assets (lista) | `routes/(app)/assets/+page.svelte` | `assetsList` | `oneRow:1340 denseRow:1060 stackFilters:500 actionsColumn:410 iconOnly:320 labelHide:320` |
| Assets (dettaglio) | `routes/(app)/assets/[id]/+page.svelte` | `assetDetail` | `oneRow:1090 denseRow:870 stackFilters:570 actionsColumn:445 iconOnly:320 labelHide:320` |
| Forex (lista) | `routes/(app)/fx/+page.svelte` | `fxList` | `oneRow:1120 denseRow:760 stackFilters:520 actionsColumn:420 iconOnly:320 labelHide:320` |
| Forex (dettaglio) | `routes/(app)/fx/[pair]/+page.svelte` | `fxDetail` | `oneRow:790 denseRow:620 stackFilters:520 actionsColumn:420 iconOnly:320 labelHide:320` |

> ⚠️ I valori di `actionsColumn` sopra sono STIME iniziali (a metà circa tra `stackFilters` e
> `iconOnly`), non ancora tarati live come gli altri — usa il flusso di taratura sotto per
> trovare il valore giusto pagina per pagina.

---

## 🎈 I badge "jolly" del `DateRangePicker`

Oltre ai 6 preset fissi (1W/1M/3M/6M/1Y/2Y) e al gruppo finale fisso (YTD/Tutti/Personalizzato),
esistono **2 pool opzionali**, mostrate solo se c'è spazio:

- **Pool "durate"** (`durationFillPresets`): 3Y, 5Y, 10Y — estende la progressione anni
- **Pool "periodi"** (`periodFillPresets`): MTD, QTD, WTD — periodi "da inizio X a oggi"

L'algoritmo (`measureAndFill()` in `DateRangePicker.svelte`) misura le larghezze REALI (badge
nascosti `absolute invisible` sempre renderizzati per la misura) e decide:

1. **Quante righe** (1 o 2): **dal Round 10, NON è più una misura del contenuto** — è la prop
   `layoutMode` (passata dalla pagina, proveniente da `PageToolbar`) a deciderlo direttamente:
   `layoutMode === 'wide'` (cioè larghezza ≥ soglia `oneRow`) → 1 riga; qualsiasi altro valore di
   `layoutMode` (`'tablet'`, `'tablet-s'`, `'mobile'`, `'compact'`) → SEMPRE 2 righe. Una pagina
   che non passa `layoutMode` ottiene il default 1-riga (comportamento pre-Round-10).
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
| `maxWidth` | `isSingleRow` è vero (`layoutMode === 'wide'`, 1 riga) | **740px** (tarato dall'utente — prima era 672px, la classe fissa Tailwind `max-w-2xl`) |
| `maxWidthTwoRow` | `isSingleRow` è falso (`layoutMode` è tutto il resto, 2 righe) | **390px** (tarato dall'utente) |

Il tetto massimo di larghezza che il picker può occupare quando condivide la riga con altri
filtri (valuta, filtro broker, ecc.). Sotto il cofano diventa uno `style="max-width: {}px"`
inline (necessario per essere veramente dinamico — le classi Tailwind sono fisse a build-time);
il valore effettivo (`effectiveMaxWidth`) sceglie automaticamente tra le due prop in base a
`isSingleRow`, quindi passa da uno all'altro da solo attraversando la soglia `oneRow` — nessun
wiring aggiuntivo richiesto.

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
// { oneRow: 1000, denseRow: 810, stackFilters: 430, actionsColumn: 365, iconOnly: 300, labelHide: 320 }

// Cambia una soglia — ricalcola SUBITO, nessun resize richiesto
window.__lfLayouts.dashboard.thresholds.iconOnly = 300

// Prova/rimuovi la sotto-fascia "azioni a colonna" (opzionale)
window.__lfLayouts.dashboard.thresholds.actionsColumn = 380
window.__lfLayouts.dashboard.thresholds.actionsColumn = undefined  // torna sempre 2×2 fino a iconOnly

// Leggi la modalità corrente risultante
window.__lfLayouts.dashboard.layoutMode
// 'wide' | 'tablet' | 'tablet-s' | 'mobile' | 'compact'

// Leggi se le Azioni sono attualmente in colonna (vero solo nella sotto-fascia actionsColumn)
window.__lfLayouts.dashboard.actionsStacked

// Cambia la max-width del DateRangePicker — una per modalità riga, entrambe live, nessun resize
window.__lfLayouts.dashboard.pickerConfig.maxWidth = 740        // usata quando è a 1 riga (wide)
window.__lfLayouts.dashboard.pickerConfig.maxWidthTwoRow = 390  // usata quando è a 2 righe (tutto il resto)
```

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

1. Usa `<PageToolbar thresholds={{oneRow, denseRow, stackFilters, actionsColumn, iconOnly,
   labelHide}} layoutDebugName="nomeUnivoco">` (`actionsColumn` è opzionale) — le zone
   `filters`/`summary` ricevono `{layoutMode, isStacked}`, `actions` riceve `{layoutMode,
   showActionLabels, stretchActions, actionsStacked}`. Usa questi flag semantici, MAI
   `layoutMode === 'mobile'` direttamente (la semantica di ogni livello può cambiare in futuro,
   solo `PageToolbar` dovrebbe doversi aggiornare).
2. **DateRangePicker**: passa `align="start"` + `layoutMode={layoutMode}` (dallo stesso snippet
   `filters`/`summary` — OBBLIGATORIO dal Round 10: senza questa prop il picker resta sempre a
   1 riga, ignorando le soglie della pagina) + lo stesso `debugName="nomeUnivoco"` usato al
   punto 1 (così soglie e `maxWidth` finiscono sulla stessa voce del registro console). Se la
   pagina ha bisogno di leggere `layoutMode` ANCHE fuori dalle snippet (es. un testo che cambia
   in base al layout, non solo dentro filters/actions), usa `bind:layoutMode={miaVariabile}` su
   `<PageToolbar>` E passa quella stessa variabile al picker (vedi `assets/[id]/+page.svelte` o
   `fx/[pair]/+page.svelte` per un esempio — entrambe fanno `layoutMode={pageLayoutMode}`).
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
(Round 10.1). Non esiste un unico "piano madre" per questo lavoro — la cronologia completa con
diagnosi round-per-round è nella sessione dell'agente che lo ha implementato, non riportata qui
per brevità. Questa guida documenta lo **stato attuale**, non la storia.

---

## 🗺️ Layout atteso per fascia (alto livello)

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

- **Azioni** (sempre a destra quando `layoutMode` è `'wide'`/`'tablet'`/`'tablet-s'`, sotto tutto il resto quando è `'mobile'`/`'compact'`)
- **Tab** (solo dashboard e broker-detail — riga a parte, sotto tutto il resto)

> ✅ **Dal Round 10**: il DateRangePicker NON decide più da solo se stare su 1 o 2 righe interne
> — è la soglia `oneRow` a deciderlo direttamente (`layoutMode === 'wide'` → 1 riga, qualsiasi
> altro valore → sempre 2 righe). Il conteggio badge jolly PER riga resta a misura reale
> (continuo) — cambia solo CHI decide 1-vs-2-righe, non il riempimento fine.

### WIDE (`layoutMode === 'wide'`, sopra `oneRow`) — tutto affiancato, 1 riga, badge jolly al completo

```
[ DateRangePicker (1 riga, jolly al completo) │ Centro ]  ───────────  [ 2×2 con etichetta ]
                                                                        [ Tab Tab Tab ]  (con etichetta — solo dashboard/broker)
```

- Riga unica: `[DateRangePicker] [Centro]` a sinistra, Azioni a destra (`justify-between`).
- Azioni: griglia 2×2 CON etichetta testuale.
- Tab (se presenti): riga sotto, CON etichetta.

### TABLET (`layoutMode === 'tablet'`, tra `denseRow` e `oneRow`) — stessa struttura, 2 righe

```
[ DateRangePicker (2 righe interne) │ Centro ]  ───────────  [ 2×2 con etichetta ]
                                                               [ Tab Tab Tab ]  (con etichetta)
```

- Stessa struttura esterna di `wide` (Centro ancora affiancato, Azioni ancora 2×2) — nessun
  cambio di layout in `PageToolbar`, solo il picker che ha 2 righe invece di 1.
- Il picker passa a 2 righe interne ESATTAMENTE al confine `oneRow` (non gradualmente) — con più
  spazio disponibile (2 righe) il numero di badge jolly totali mostrati AUMENTA rispetto a
  subito prima del confine, poi torna a diminuire (misura reale, continua) via via che ci si
  restringe verso `denseRow`.
- Centro (valuta/ricerca/...) NON si restringe mai (`shrink-0`) — è il picker che cede spazio.
- Alcune pagine (es. assets lista) usano il confine `denseRow` per riorganizzare il PROPRIO
  contenuto "Centro" (es. il blocco ricerca+filtri passa da inline a un blocco 2 righe interno),
  pur restando il Centro affiancato al picker (non sotto) per tutta la fascia `tablet`.

### TABLET-S (`layoutMode === 'tablet-s'`, tra `stackFilters` e `denseRow`) — filtri impilati, azioni 2×2

```
[ DateRangePicker (2 righe) ]               [ Azione1 (con etichetta) ]
[ Centro                    ]               [ Azione2 (con etichetta) ]
                          [ Tab Tab Tab ]  (con etichetta)
```

- DateRangePicker e Centro si impilano in colonna (uno sopra l'altro), distribuzione
  "giustificata" (allineata a sinistra, mai centrata) — ma questa colonna resta AFFIANCATA alle
  Azioni (non sotto) — `justify-between` ancora attivo sulla riga esterna.
- Azioni: restano griglia 2×2 con etichetta (CORREZIONE Round 10 — qui NON diventano colonna).

### MOBILE (`layoutMode === 'mobile'`, tra `iconOnly` e `stackFilters`) — tutto impilato, 2 sotto-casi per le Azioni

```
[ DateRangePicker (2 righe) ]
[ Centro                    ]
[ Azione1 (con etichetta) ] [ Azione2 (con etichetta) ]     ← 2×2, sotto-fascia "bassa" di mobile
[ Azione3 (con etichetta) ] [ Azione4 (con etichetta) ]        (o l'UNICA struttura se actionsColumn non è definito)
[ Tab Tab Tab ]  (ancora con etichetta)
```
```
[ DateRangePicker (2 righe) ]           [ Azione1 (con etichetta) ]   ← colonna 4×1, sotto-fascia
[ Centro                    ]           [ Azione2 (con etichetta) ]      "alta" di mobile (sopra
                                        [ Azione3 (con etichetta) ]      actionsColumn, se definito)
                                        [ Azione4 (con etichetta) ]
                      [ Tab Tab Tab ]  (con etichetta)
```

- TUTTO impilato in un'unica colonna esterna (Picker+Centro, poi Azioni, poi Tab) — cambia da
  `tablet-s` perché ORA anche le Azioni si spostano SOTTO (non più affiancate).
- Se la soglia opzionale `actionsColumn` è definita, "mobile" si divide in 2 sotto-casi:
  sopra quel valore (ma sotto `stackFilters`) le Azioni sono colonna 4×1 (secondo diagramma
  sopra); sotto quel valore (ma sopra `iconOnly`) tornano a griglia 2×2 (primo diagramma) — un
  "ritorno" deliberato, non un errore: una colonna 4×1 usa più altezza verticale di una griglia
  2×2, quindi vicino a `stackFilters` (subito dopo essersi impilati) può avere senso dare più
  respiro orizzontale con la colonna, mentre a larghezze "mobile" più tipiche la griglia 2×2
  torna più efficiente in altezza.
- Se `actionsColumn` NON è definito, tutta la fascia "mobile" usa solo il primo diagramma
  (griglia 2×2) — comportamento pre-Round-10.
- L'etichetta sparisce solo sotto `labelHide` (di solito = `iconOnly`), MAI dentro "mobile".

### COMPACT (`layoutMode === 'compact'`, sotto `iconOnly`) — fallback più stretto, solo icone

```
[ DateRangePicker (2 righe) ]
[ Centro                    ]
       🔧  ⚙  ↻  …          (solo icone, riga centrata, va a capo se serve)
       🏠  📊  💰           (tab solo icone, se presenti)
```

- Stessa struttura impilata di `mobile`, ma le Azioni perdono l'etichetta e diventano una riga di
  sole icone, centrata (non più griglia/colonna) — l'ultimo fallback, pensato per finestre molto
  strette dove anche 2×2-con-etichetta non ci sta più.
- I Tab (se presenti) perdono anche loro l'etichetta.
