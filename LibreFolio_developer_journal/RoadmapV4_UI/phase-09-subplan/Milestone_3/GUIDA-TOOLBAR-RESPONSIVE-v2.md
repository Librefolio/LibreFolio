# Guida Rapida v2 — Toolbar Responsive: soglie, comandi, layout per fascia

> Questa v2 **corregge e sostituisce** il modello di layout-per-fascia descritto in
> `GUIDA-TOOLBAR-RESPONSIVE.md` (v1) — in particolare la fascia che v1 chiamava `'mobile'` (senza
> soglia propria) è stata **rinominata e formalizzata come `oneColumn`**, con soglia dedicata, e il
> comportamento delle Azioni in quella fascia è cambiato (vedi sotto). Per tutto ciò che v2 NON
> ripete — algoritmo badge "jolly", `effectiveMaxWidth`, gotcha "verify+shed", checklist per
> estendere il sistema a una nuova pagina — v1 resta valido, vedi i rimandi in fondo.

**File principali** (invariati): `responsiveLayout.svelte.ts` (soglie + `layoutMode`),
`PageToolbar.svelte` (shell, tutte e 6 le pagine), `DateRangePicker.svelte` (date picker + badge
jolly).

---

## 🎯 Le 5 fasce (`layoutMode`)

> ⚠️ **Round 11.1**: la larghezza confrontata con le soglie è **CONTENT-BOX** (l'interno del
> contenitore, esclude il `p-4` = 32px di padding orizzontale della barra) — non border-box.
> Round 10.3 aveva provato border-box (per combaciare con `getBoundingClientRect()`/devtools), ma
> misurazione diretta dell'utente ha confermato che era la direzione sbagliata: si legge/tara
> "l'interno", non il rendering completo col padding. Se leggi la larghezza da devtools
> (`getBoundingClientRect().width`, border-box) **sottrai 32px** per ottenere il numero da
> confrontare con le soglie — o meglio, usa lo snippet diagnostico sotto, che fa già la sottrazione.

Regola unica, sempre la stessa: appena la larghezza **content-box** (l'interno, senza il padding
della barra) scende sotto la soglia della fascia corrente, si passa alla fascia immediatamente più
stretta. Ogni fascia ha ORA una soglia dedicata con lo stesso nome — nessuna eccezione, nessun caso
implicito:

```
larghezza ≥ oneRow        → 'oneRow'
oneRow > larghezza ≥ denseRow      → 'denseRow'
denseRow > larghezza ≥ stackFilters → 'stackFilters'
stackFilters > larghezza ≥ oneColumn → 'oneColumn'
larghezza < oneColumn      → 'iconOnly'
```

> ⚠️ **Round 11.2**: Round 11 (sotto) aveva sbagliato la forma delle Azioni in `stackFilters` —
> il testo diceva "2×2" ma lo SKETCH originale dell'utente mostrava 4 righe singole (4×1
> verticale). Corretto: `stackFilters` ora mostra le Azioni come colonna verticale 4×1 CON
> etichetta (non 2×2) — vedi tabella e sezione dedicata sotto.

| Fascia | `filtersStacked` | `isStacked` | Picker + Centro | Azioni |
|---|---|---|---|---|
| `oneRow` | no | no | affiancati, Picker 1 riga | affiancate, 2×2 con etichetta |
| `denseRow` | no | no | affiancati, Picker 2 righe | affiancate, 2×2 con etichetta |
| `stackFilters` | **sì** | no | impilati, giustificati | **ancora affiancate**, ma **colonna 4×1** con etichetta |
| `oneColumn` | sì | **sì** | impilati, giustificati (identico a `stackFilters`) | **sotto**, torna 2×2 con etichetta |
| `iconOnly` | sì | sì | impilati, a tutta larghezza | sotto, riga centrata SOLE ICONE |

Il cambio chiave rispetto a v1: `isStacked` (tutta la barra, Azioni comprese, si impila in
colonna) ora scatta già a `oneColumn`, non solo a `iconOnly`. In `stackFilters` le Azioni restano
BESIDE (accanto) alla colonna Picker+Centro, ma cambiano FORMA rispetto a `oneRow`/`denseRow`: da
griglia 2×2 a colonna verticale 4×1 (sempre con etichetta) — `actionsStacked` in
`PageToolbar.svelte` governa questa forma, vero SOLO in `stackFilters`. A `oneColumn` le Azioni
tornano una griglia 2×2 (con etichetta), ma spostata SOTTO. Solo a `iconOnly` perdono ANCHE
l'etichetta e passano a riga centrata a-capo di sole icone.

`filtersStacked` (Picker+Centro impilati) copre `stackFilters` + `oneColumn` + `iconOnly` — non è
cambiata rispetto a v1, continua a essere l'unico flag che le pagine devono leggere per il proprio
contenuto "Centro" (mai `isStacked`, riservato al posizionamento delle Azioni).

---

## 🔧 Le soglie — tabella e valori per pagina

| Soglia | Cosa cambia a questo confine |
|---|---|
| `oneRow` | DateRangePicker: 1 riga sola (badge jolly a misura reale). Sotto: sempre 2 righe interne |
| `denseRow` | Nessun cambio di struttura in `PageToolbar` — solo alcune pagine riorganizzano il proprio "Centro" |
| `stackFilters` | Centro si sposta SOTTO il DateRangePicker (colonna giustificata, larghezza allineata al picker via `effectiveMaxWidth`). Azioni restano AFFIANCATE alla colonna, ma cambiano forma: da griglia 2×2 a colonna verticale 4×1, sempre con etichetta |
| `oneColumn` | **Nuova soglia (Round 11)** — le Azioni si spostano SOTTO Picker+Centro (tutta la barra è ora una colonna) e tornano una griglia 2×2 con etichetta |
| `iconOnly` | Le Azioni (e i Tab, se presenti) perdono l'etichetta e passano a riga centrata di sole icone (va a capo se serve) — il fallback più stretto |
| `labelHide` | *(asse indipendente)* Sotto questa larghezza le etichette testuali dei bottoni azione scompaiono — di solito = `iconOnly`, stesso valore |

> ⚠️ `actionsColumn` (v1) come CAMPO/soglia separata non esiste più — la colonna 4×1 non è più una
> sotto-fascia opzionale dentro un'altra fascia, è il comportamento SEMPRE attivo di `stackFilters`
> stessa (nessuna soglia dedicata da tarare per questo: scatta/finisce esattamente insieme a
> `stackFilters`).

### Valori attuali per pagina

| Pagina | `oneRow` | `denseRow` | `stackFilters` | `oneColumn` | `iconOnly` | `labelHide` |
|---|---|---|---|---|---|---|
| Dashboard (`dashboard`) | 1000 | 810 | 430 | 365 | 330 | 330 |
| Broker Detail (`brokerDetail`) | 1000 | 800 | 560 | 470 | 330 | 330 |
| Assets lista (`assetsList`) | 1340 | 1060 | 500 | 410 | 330 | 330 |
| Assets dettaglio (`assetDetail`) | 1090 | 870 | 570 | 445 | 330 | 330 |
| Forex lista (`fxList`) | 1120 | 760 | 520 | 420 | 330 | 330 |
| Forex dettaglio (`fxDetail`) | 790 | 620 | 520 | 420 | 330 | 330 |

> ⚠️ Segnalato dall'utente (dashboard a 460, assets a 414/460): a `stackFilters` la colonna
> Picker+Centro (contenuto quasi fisso, non si riduce) PIÙ la colonna Azioni possono non stare
> nello spazio disponibile se `stackFilters` è tarato troppo basso rispetto al contenuto reale
> della pagina — causa overflow/clipping. Le soglie sopra sono ancora quelle ereditate da
> `actionsColumn` (mai tarate live) — vanno verificate/alzate pagina per pagina col flusso di
> taratura sotto.

---

## 💻 Comandi Console — Test Live (F12 → Console)

Stesso registro `window.__lfLayouts.<nome>` di v1, campi aggiornati (`actionsColumn` → `oneColumn`,
niente più `.actionsStacked` — vedi nota sotto):

```js
// Vedi le soglie attuali di una pagina
window.__lfLayouts.dashboard.thresholds
// { oneRow: 1000, denseRow: 810, stackFilters: 430, oneColumn: 365, iconOnly: 330, labelHide: 330 }

// Cambia una soglia — ricalcola SUBITO, nessun resize richiesto
window.__lfLayouts.dashboard.thresholds.oneColumn = 380

// Leggi la modalità corrente risultante
window.__lfLayouts.dashboard.layoutMode
// 'oneRow' | 'denseRow' | 'stackFilters' | 'oneColumn' | 'iconOnly'

// isStacked/filtersStacked NON sono esposti direttamente (sono calcolati dentro PageToolbar,
// non fanno parte del layout registrato) — deducili da layoutMode:
//   isStacked      = layoutMode === 'oneColumn' || layoutMode === 'iconOnly'
//   filtersStacked = layoutMode === 'stackFilters' || isStacked

// Cambia la max-width del DateRangePicker — una per modalità riga, entrambe live, nessun resize
window.__lfLayouts.dashboard.pickerConfig.maxWidth = 740        // usata quando è a 1 riga (oneRow)
window.__lfLayouts.dashboard.pickerConfig.maxWidthTwoRow = 390  // usata quando è a 2 righe (tutto il resto)

// 🩺 Diagnostica rapida: correla larghezza REALE content-box (quella confrontata con le soglie —
// getBoundingClientRect() è border-box, quindi qui sottraiamo il padding orizzontale calcolato)
// con la modalità risultante e le soglie stesse, IN UN COLPO SOLO — utile per capire perché una
// soglia "non sembra scattare"
(() => {
    const l = window.__lfLayouts.dashboard;
    const bar = document.querySelector('[data-testid="dashboard-filter-bar"]');
    const cs = bar && getComputedStyle(bar);
    const contentWidth = bar && cs ? bar.getBoundingClientRect().width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) : undefined;
    console.table({realWidthContentBox: contentWidth, layoutMode: l.layoutMode, ...l.thresholds});
})()
```

Nomi disponibili: `dashboard`, `brokerDetail`, `assetsList`, `assetDetail`, `fxList`, `fxDetail`
(cambia anche il `data-testid` nello snippet diagnostico — vedi tabella soglie sopra per il nome
registro di ciascuna pagina, e v1 per il `data-testid`/`filterRowTestId` esatto).

### Flusso di taratura consigliato

1. Apri la pagina da tarare, F12 → Console.
2. Ridimensiona la finestra fino al punto in cui il comportamento ti sembra sbagliato.
3. Leggi `window.__lfLayouts.<nome>.thresholds` per i valori attuali.
4. Modifica il campo sospetto (es. `oneColumn`) e osserva il cambiamento immediato.
5. Quando sei soddisfatto, riporta il valore trovato nel file `+page.svelte` corrispondente
   (chiamata `<PageToolbar thresholds={{...}}>`).

---

## 🗺️ Layout atteso per fascia (versione corretta)

Tutte le topbar condividono la stessa struttura concettuale: **DateRangePicker** (sempre a
sinistra, `align="start"`) + **Centro** (contenuto per-pagina: valuta/broker/ricerca/price-summary/
pair-info) + **Azioni** (bottoni) + **Tab** (solo dashboard e broker-detail).

### ONE ROW (`layoutMode === 'oneRow'`, ≥ soglia `oneRow`)

```
[ DateRangePicker (1 riga, jolly al completo) │ Centro ]  ───────────  [ 2×2 con etichetta ]
                                                                        [ Tab Tab Tab ]  (con etichetta — solo dashboard/broker)
```

Riga unica, tutto affiancato (`justify-between`). Azioni: griglia 2×2 CON etichetta. Tab (se
presenti): riga sotto, CON etichetta.

### DENSE ROW (`layoutMode === 'denseRow'`, tra `denseRow` e `oneRow`)

```
[ DateRangePicker (2 righe interne) │ Centro ]  ───────────  [ 2×2 con etichetta ]
                                                               [ Tab Tab Tab ]  (con etichetta)
```

Stessa struttura esterna di `oneRow` — solo il Picker passa a 2 righe interne (i badge jolly
totali aumentano al confine, poi tornano a scendere restringendo verso `denseRow`). Centro non si
restringe mai (`shrink-0`).

### STACK FILTERS (`layoutMode === 'stackFilters'`, tra `stackFilters` e `denseRow`)

```
[ DateRangePicker (2 righe) ]               [ Azione1 (con etichetta) ]
[ Centro                    ]               [ Azione2 (con etichetta) ]
                                            [ Azione3 (con etichetta) ]
                                            [ Azione4 (con etichetta) ]
                          [ Tab Tab Tab ]  (con etichetta)
```

Picker+Centro si impilano in colonna, distribuzione "giustificata" (allineata a sinistra, mai
centrata, larghezza del Centro allineata pixel-perfect al Picker via `effectiveMaxWidth`) — ma
questa colonna resta **AFFIANCATA** alle Azioni (`justify-between` ancora attivo sulla riga
esterna). Azioni: **colonna verticale 4×1 CON etichetta** (non griglia 2×2 — vedi Round 11.2:
il testo di v2 diceva erroneamente "2×2", ma questo ASCII, fedele all'originale dell'utente, ha
sempre mostrato 4 righe singole; `actionsStacked` in `PageToolbar.svelte` è vero SOLO qui).

### ONE COLUMN (`layoutMode === 'oneColumn'`, tra `oneColumn` e `stackFilters`) — 🆕 corretta

```
[ DateRangePicker (2 righe) ]
[ Centro                    ]
[ Azione1 (con etichetta) ] [ Azione2 (con etichetta) ]
[ Azione3 (con etichetta) ] [ Azione4 (con etichetta) ]
[ Tab Tab Tab ]  (con etichetta — solo dashboard/broker)
```

Tutta la barra diventa UNA colonna: Picker, Centro, Azioni, Tab — ognuno sotto il precedente,
a piena larghezza. Rispetto a `stackFilters`:

- Picker+Centro: **nessun cambiamento visivo** — stessa colonna giustificata/allineata a
  sinistra, stesso `effectiveMaxWidth`.
- Azioni: **si spostano da accanto a sotto E tornano una griglia 2×2** (`actionsStacked` torna
  falso qui) — due cambi contemporanei rispetto a `stackFilters`: posizione (sotto, non accanto)
  E forma (griglia 2×2, non più colonna 4×1).
- Tab (se presenti): restano orizzontali, con etichetta, sotto le Azioni.

Questa è la fascia che v1 chiamava `'mobile'` (senza soglia propria) — v2 la promuove a fascia di
primo piano con nome e soglia dedicati, perché lo spostamento delle Azioni è una decisione di
layout a sé, non un dettaglio secondario.

### ICON ONLY (`layoutMode === 'iconOnly'`, < soglia `oneColumn`)

```
[ DateRangePicker (2 righe) ]
[ Centro                    ]
       🔧  ⚙  ↻  …          (solo icone, riga centrata, va a capo se serve)
       🏠  📊  💰           (tab solo icone, se presenti)
```

Stessa colonna unica di `oneColumn`, ma Azioni e Tab perdono l'etichetta testuale e passano da
griglia 2×2 a riga centrata di sole icone (va a capo se lo spazio non basta per tutte in riga). Il
fallback più stretto, per quando anche un 2×2-con-etichetta non ci sta più.

---

## 📌 Cosa resta valido in v1 (non ripetuto qui)

- Algoritmo badge "jolly" del `DateRangePicker` (pool durate/periodi, `measureAndFill()`).
- `maxWidth`/`maxWidthTwoRow`/`effectiveMaxWidth` (meccanismo bindable per allineare il Centro al
  Picker in pixel quando `filtersStacked`).
- Il gotcha "verify+shed" (perché esiste una verifica post-render sul wrap dei badge).
- La checklist per estendere il sistema a una nuova pagina.

> ⚠️ Il capitolo di v1 sul fix border-box/content-box del `ResizeObserver` è invece SUPERATO
> (Round 11.1 lo ha invertito di nuovo a content-box, vedi banner in cima a questa v2) — non è
> "ciò che resta valido", è parte di ciò che questa v2 corregge.

Solo la tabella soglie, i comandi console che citano `actionsColumn` come SOGLIA (il concetto
`actionsStacked` come FLAG booleano invece esiste ancora, solo agganciato a `stackFilters` invece
che a una soglia dedicata), la nota border-box, e l'intera sezione "Layout atteso per fascia" di
v1 sono superati da questa v2.
