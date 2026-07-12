# Guida Rapida — Toolbar Responsive (PageToolbar + DateRangePicker)

**File principali**:
- `frontend/src/lib/utils/layout/responsiveLayout.svelte.ts` — soglie di layout + registro debug
- `frontend/src/lib/components/ui/toolbar/PageToolbar.svelte` — shell toolbar (dashboard, broker-detail)
- `frontend/src/lib/components/ui/date/DateRangePicker.svelte` — date picker + badge "jolly" auto-fit

---

## 🎯 Panoramica del sistema

Il layout responsive della toolbar (dashboard, broker-detail, assets, forex — 6 pagine in
totale) usa un `ResizeObserver` sul contenitore reale per decidere come disporre filtri/azioni
a 5 livelli di larghezza (`wide`→`tablet`→`tablet-s`→`mobile`→`compact`), **senza breakpoint CSS
fissi** — le soglie sono numeri in pixel, configurabili per pagina e **tarabili live da console
del browser**, senza rebuild.

Il `DateRangePicker` (in modalità `align="start"`, usata da tutte e 6 le pagine) aggiunge un
secondo livello: badge "jolly" (3Y/5Y/10Y/MTD/QTD/WTD) che appaiono automaticamente solo se c'è
spazio libero da riempire, misurati via JS in tempo reale (non con soglie CSS fisse) — anche la
loro `max-width` massima è tarabile live.

---

## 🔧 Le 5 soglie di `PageToolbar`/pagina

| Soglia | Significato |
|---|---|
| `wide` | Sopra questa larghezza (px, larghezza REALE del contenitore, misurata da `ResizeObserver` — non il viewport) → tutto in riga, azioni 2×2 con etichetta |
| `tablet` | Sotto `wide`, sopra questa → ancora riga ma più compatta |
| `tabletS` | Sotto `tablet`, sopra questa → filtri impilati in colonna, azioni ancora 2×2 con etichetta |
| `compact` | Sotto questa → **tutto impilato**, azioni diventano riga di sole icone (nessuna etichetta). È il fallback più stretto, aggiunto apposta perché prima "mobile" saltava direttamente alle icone-sole — ora "mobile" (tra `tabletS` e `compact`) mostra ancora 2×2-con-etichetta |
| `labelHide` | Sotto questa larghezza le etichette testuali dei bottoni azione scompaiono (di solito = `compact`, stesso valore, così le icone-sole compaiono ESATTAMENTE insieme alla scomparsa delle etichette) |

### Dove sono definite (una chiamata per pagina)

| Pagina | File | Nome registro console | Valori attuali |
|---|---|---|---|
| Dashboard | `routes/(app)/dashboard/+page.svelte` (`<PageToolbar thresholds={{...}}>`) | `dashboard` | `wide:900 tablet:660 tabletS:480 compact:340 labelHide:340` |
| Broker Detail | `routes/(app)/brokers/[id]/+page.svelte` (`<PageToolbar thresholds={{...}}>`) | `brokerDetail` | `wide:1000 tablet:800 tabletS:560 compact:380 labelHide:380` |
| Assets (lista) | `routes/(app)/assets/+page.svelte` (`createResponsiveLayout({...})`) | `assetsList` | `wide:1340 tablet:1060 tabletS:500 compact:320 labelHide:320` |
| Assets (dettaglio) | `routes/(app)/assets/[id]/+page.svelte` | `assetDetail` | `wide:1090 tablet:870 tabletS:570 compact:320 labelHide:320` |
| Forex (lista) | `routes/(app)/fx/+page.svelte` | `fxList` | `wide:1120 tablet:760 tabletS:520 compact:320 labelHide:320` |
| Forex (dettaglio) | `routes/(app)/fx/[pair]/+page.svelte` | `fxDetail` | `wide:790 tablet:620 tabletS:520 compact:320 labelHide:320` |

**Dashboard/Broker-detail** passano le soglie come prop `thresholds` a `<PageToolbar>` (che usa
internamente `createResponsiveLayout`). **Assets/Forex** chiamano `createResponsiveLayout(...)`
direttamente nel proprio `<script>` (non usano `PageToolbar` — hanno un layout filtri/azioni
scritto a mano, ma condividono lo stesso helper sotto il cofano).

---

## 🎈 I badge "jolly" del `DateRangePicker`

Oltre ai 6 preset fissi (1W/1M/3M/6M/1Y/2Y) e al gruppo finale fisso (YTD/Tutti/Personalizzato),
esistono **2 pool opzionali**, mostrate solo se c'è spazio:

- **Pool "durate"** (`durationFillPresets`): 3Y, 5Y, 10Y — estende la progressione anni
- **Pool "periodi"** (`periodFillPresets`): MTD, QTD, WTD — periodi "da inizio X a oggi"

L'algoritmo (`measureAndFill()` in `DateRangePicker.svelte`) misura le larghezze REALI (badge
nascosti `absolute invisible` sempre renderizzati per la misura) e decide:
1. **Se tutto entra su una riga**: i badge fissi + quanti jolly ci stanno, presi ALTERNANDO dalle
   2 pool (budget condiviso) — mai un numero fisso, sempre "quanti servono a riempire lo spazio".
2. **Se non entra**: 2 righe separate, ognuna pesca SOLO dalla propria pool nel proprio spazio
   residuo (riga 1 = durate, riga 2 = periodi).

### `maxWidth` — quanto può crescere il DateRangePicker

Prop `maxWidth` (default **672px**, prima era la classe fissa Tailwind `max-w-2xl`) — il tetto
massimo di larghezza che il picker può occupare quando condivide la riga con altri filtri
(valuta, filtro broker, ecc.). Sotto il cofano diventa uno `style="max-width: {}px"` inline
(necessario per essere veramente dinamico — le classi Tailwind sono fisse a build-time).

### ⚠️ Gotcha noto — perché esiste il "verify+shed"

L'algoritmo di misura usa larghezze REALI (non stime), ma un margine piccolo (badge nascosto di
misura vs badge reale, o il gap CSS che non corrisponde esattamente al valore hardcoded) può
farlo sbagliare **per un solo badge** a certe larghezze. Se questo succede, il CSS nativo
(`flex-wrap`) spacca la riga in 2 SENZA che il JS se ne accorga — e siccome il contenitore
misurato cambia solo di ALTEZZA (non di larghezza) quando questo avviene, il calcolo sbagliato **si
ripete identico per sempre**, anche a resize successivi: un "punto fisso sbagliato" che resta
bloccato finché non si ricarica la pagina.

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
// { wide: 900, tablet: 660, tabletS: 480, compact: 340, labelHide: 340 }

// Cambia una soglia — ricalcola SUBITO, nessun resize richiesto
window.__lfLayouts.dashboard.thresholds.compact = 300

// Leggi la modalità corrente risultante
window.__lfLayouts.dashboard.layoutMode
// 'wide' | 'tablet' | 'tablet-s' | 'mobile' | 'compact'

// Cambia la max-width del DateRangePicker — anche questo live, nessun resize
window.__lfLayouts.dashboard.pickerConfig.maxWidth = 900
```

Nomi disponibili: `dashboard`, `brokerDetail`, `assetsList`, `assetDetail`, `fxList`, `fxDetail`.

### Flusso di taratura consigliato

1. Apri la pagina che vuoi tarare, F12 → Console.
2. Ridimensiona la finestra fino al punto in cui il comportamento ti sembra sbagliato.
3. Leggi `window.__lfLayouts.<nome>.thresholds` per vedere i valori attuali.
4. Modifica il campo che sospetti (es. `compact`) e osserva il cambiamento immediato.
5. Quando sei soddisfatto, riporta il valore trovato: aggiorna la riga corrispondente nel codice
   (vedi tabella sopra per il file esatto).

---

## 📁 Estendere il sistema a una nuova pagina — checklist

Per una NUOVA pagina che vuole lo stesso pattern (breakpoint responsive + badge jolly nel
DateRangePicker):

1. **Se usi `PageToolbar`**: passa `thresholds={{wide, tablet, tabletS, compact, labelHide}}` +
   `layoutDebugName="nomeUnivoco"`. Le zone `filters`/`actions` ricevono `{layoutMode, isStacked}`
   / `{layoutMode, showActionLabels, stretchActions}` — usa questi flag semantici, MAI
   `layoutMode === 'mobile'` direttamente (la semantica di ogni livello può cambiare in futuro,
   solo `PageToolbar` dovrebbe doversi aggiornare).
2. **Se NON usi `PageToolbar`** (layout filtri/azioni scritto a mano, come assets/fx): chiama
   `createResponsiveLayout({wide, tablet, tabletS, compact, labelHide})` +
   `registerLayoutDebug('nomeUnivoco', layout)` nello `<script>`. Deriva SEMPRE un
   `isStacked = layoutMode === 'mobile' || layoutMode === 'compact'` locale — non confrontare
   `layoutMode` isolatamente nella zona filtri, altrimenti il nuovo stato `compact` cade nel ramo
   sbagliato (bug reale trovato e corretto proprio in questo modo per le 4 pagine assets/fx).
3. **Zona azioni**: `layoutMode === 'compact' ? 'flex-row justify-center flex-wrap' :
   layoutMode === 'tablet-s' ? 'flex-col ...' : 'grid grid-cols-2 ...'` — "mobile" cade nel ramo
   grid (2×2 con etichetta), MAI nel ramo icone-sole.
4. **DateRangePicker**: passa `align="start"` + lo stesso `debugName="nomeUnivoco"` usato al
   punto 1/2 (così soglie e `maxWidth` finiscono sulla stessa voce del registro console). Il
   wrapper attorno al picker deve avere `self-stretch` (oltre a `flex-1` se condivide una riga)
   — senza, il picker non usa mai più della sua larghezza intrinseca e l'algoritmo di misura
   lavora su una larghezza sbagliata (bug reale, Round 6).

---

## 📌 Storico (per contesto)

Questo sistema è stato costruito in modo iterativo (round di bugfix guidati da feedback visivo)
su dashboard/broker-detail (Round 1-6), poi esteso ad assets/forex (Round 6-7), poi rifinito con
soglia `compact` ovunque + tuning live da console (Round 7) + max-width dinamica e fix del wrap
prematuro (Round 8, questo). Non esiste un unico "piano madre" per questo lavoro — la cronologia
completa con diagnosi round-per-round è nella sessione dell'agente che lo ha implementato, non
riportata qui per brevità. Questa guida documenta lo **stato attuale**, non la storia.
