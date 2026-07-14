# Guida Toolbar Responsive — soglie, comandi, layout per fascia

> **⚠️ Questa guida è ORA AUTOSUFFICIENTE** — la precedente `GUIDA-TOOLBAR-RESPONSIVE.md` (v1) è
> stata **eliminata** (Round 14). Tutti i contenuti di v1 ancora validi (algoritmo badge "jolly",
> mecanismo `maxWidth`/`maxWidthTwoRow`/`effectiveMaxWidth`, gotcha "verify+shed", checklist per
> estendere il sistema a una nuova pagina) sono stati **portati qui dentro** (vedi le sezioni
> dedicate più sotto) — questo file non rimanda più a nessun altro documento.
>
> **Storia in breve** (per contesto, non serve leggerla per usare la guida): il modello originale
> (v1) chiamava la fascia più stretta `'mobile'` senza soglia propria — **Round 11** l'ha
> rinominata/formalizzata come `oneColumn` con soglia dedicata; **Round 12** ha rimosso la fascia
> ancora più stretta `'iconOnly'` e introdotto l'auto-shrink lineare delle etichette (si
> rimpiccioliscono invece di scomparire di scatto) + il "Centro giustificato" su tutte le pagine;
> **Round 13** ha splittato `labelHide` in `labelHideActions`/`labelHideTabs`, aggiunto
> `noExtraLabel` e promosso `justify-around` a standard universale; **Round 13.1** ha corretto 2
> bug (etichetta+selettore devono condividere un wrapper; introdotto poi ricorretto l'invariante
> `maxWidthTwoRow`); **Round 14** (questo) ha corretto le soglie finali di tutte le pagine, un bug
> di allineamento del Centro, il clipping di un dropdown, l'header responsive di 2 pagine, tuning
> cosmetico, e reso questa guida autosufficiente.

**File principali**: `responsiveLayout.svelte.ts` (soglie + `layoutMode`), `PageToolbar.svelte`
(shell, tutte e 6 le pagine), `DateRangePicker.svelte` (date picker + badge jolly), `labelShrink.ts`
(meccanismo condiviso di auto-shrink lineare delle etichette), `dropdownPosition.ts` (🆕 Round 14
— meccanismo condiviso "fixed position, escape overflow-hidden" per dropdown hand-rolled).

---

## 🎯 Le 4 fasce (`layoutMode`)

> ⚠️ **Round 11.1**: la larghezza confrontata con le soglie è **CONTENT-BOX** (l'interno del
> contenitore, esclude il `p-4` = 32px di padding orizzontale della barra) — non border-box.
> Round 10.3 aveva provato border-box (per combaciare con `getBoundingClientRect()`/devtools), ma
> misurazione diretta dell'utente ha confermato che era la direzione sbagliata: si legge/tara
> "l'interno", non il rendering completo col padding. Se leggi la larghezza da devtools
> (`getBoundingClientRect().width`, border-box) **sottrai 32px** per ottenere il numero da
> confrontare con le soglie — o meglio, usa lo snippet diagnostico sotto, che fa già la sottrazione.

Regola unica, sempre la stessa: appena la larghezza **content-box** (l'interno, senza il padding
della barra) scende sotto la soglia della fascia corrente, si passa alla fascia immediatamente più
stretta. Ogni fascia ha una soglia dedicata con lo stesso nome — nessuna eccezione, nessun caso
implicito. **Round 12**: la fascia `'iconOnly'` (la più stretta di tutte, che faceva scomparire le
etichette) è stata rimossa — `oneColumn` è ora la fascia più stretta:

```
larghezza ≥ oneRow        → 'oneRow'
oneRow > larghezza ≥ denseRow      → 'denseRow'
denseRow > larghezza ≥ stackFilters → 'stackFilters'
larghezza < stackFilters   → 'oneColumn'
```

> ⚠️ **Round 11.2**: in `stackFilters` le Azioni sono una colonna verticale **4×1 CON etichetta**
> (non 2×2) — vedi tabella e sezione dedicata sotto.

| Fascia | `filtersStacked` | `isStacked` | Picker + Centro | Azioni |
|---|---|---|---|---|
| `oneRow` | no | no | affiancati, Picker 1 riga | affiancate, 2×2 con etichetta |
| `denseRow` | no | no | affiancati, Picker 2 righe | affiancate, 2×2 con etichetta |
| `stackFilters` | **sì** | no | impilati, giustificati | **ancora affiancate**, ma **colonna 4×1** con etichetta |
| `oneColumn` | sì | **sì** | impilati, giustificati (identico a `stackFilters`) | **sotto**, torna 2×2 con etichetta |

Il cambio chiave rispetto a v1: `isStacked` (tutta la barra, Azioni comprese, si impila in
colonna) scatta a `oneColumn` — ORA la fascia più stretta di tutte (Round 12 ha eliminato
`iconOnly`, che prima veniva dopo). In `stackFilters` le Azioni restano BESIDE (accanto) alla
colonna Picker+Centro, ma cambiano FORMA rispetto a `oneRow`/`denseRow`: da griglia 2×2 a colonna
verticale 4×1 (sempre con etichetta) — `actionsStacked` in `PageToolbar.svelte` governa questa
forma, vero SOLO in `stackFilters`. A `oneColumn` le Azioni tornano una griglia 2×2 (con
etichetta), ma spostata SOTTO — **le etichette non scompaiono mai per effetto della fascia**: se
un'etichetta (Azione o Tab) non ci sta più in orizzontale, si rimpicciolisce (vedi sezione
"Auto-shrink lineare" sotto) prima di eventualmente sparire tramite `labelHideActions`/
`labelHideTabs` (**Round 13**: due soglie separate, non più una sola — vedi sezione dedicata).

`filtersStacked` (Picker+Centro impilati) copre `stackFilters` + `oneColumn` — non è cambiata
nella sostanza rispetto a v1 (era già così), continua a essere l'unico flag che le pagine devono
leggere per il proprio contenuto "Centro" (mai `isStacked`, riservato al posizionamento delle
Azioni).

---

## 🔧 Le soglie — tabella e valori per pagina

| Soglia | Cosa cambia a questo confine |
|---|---|
| `oneRow` | DateRangePicker: 1 riga sola (badge jolly a misura reale). Sotto: sempre 2 righe interne |
| `denseRow` | Nessun cambio di struttura in `PageToolbar` — solo alcune pagine riorganizzano il proprio "Centro" |
| `stackFilters` | Centro si sposta SOTTO il DateRangePicker (colonna giustificata, larghezza allineata al picker via `effectiveMaxWidth` — Round 12: applicato ORA su tutte e 6 le pagine, vedi sezione dedicata). Azioni restano AFFIANCATE alla colonna, ma cambiano forma: da griglia 2×2 a colonna verticale 4×1, sempre con etichetta |
| `oneColumn` | ⚠️ **Round 12.1 — attualmente INERTE, vedi nota sotto**. Concettualmente: le Azioni si spostano SOTTO Picker+Centro (tutta la barra è ora una colonna) e tornano una griglia 2×2 con etichetta — la fascia più stretta di tutte (Round 12 ha rimosso `iconOnly`, che stava sotto) |
| `labelHideActions` | 🆕 **Round 13** *(asse indipendente)* Sotto questa larghezza le etichette testuali dei bottoni AZIONE scompaiono DEL TUTTO — prima di arrivare qui, si rimpiccioliscono (vedi "Auto-shrink lineare"), non scompaiono di scatto |
| `labelHideTabs` | 🆕 **Round 13** *(asse indipendente, separato da `labelHideActions`)* Stesso comportamento di sopra, ma per le etichette dei TAB — prima erano governate dalla STESSA soglia dei bottoni Azione (`labelHide`, unica), ora sono indipendenti perché i due gruppi hanno geometrie/contenuti diversi e non sempre serve nasconderli allo stesso punto |
| `noExtraLabel` | 🆕 **Round 13** *(soglia OPZIONALE, solo dashboard per ora)* Sotto questa larghezza nasconde SOLO l'etichetta decorativa "Valuta:" davanti al selettore valuta — il selettore stesso resta sempre visibile. Vedi sezione dedicata sotto |

> ⚠️ `actionsColumn`/`iconOnly` (v1/Round 10-11) come CAMPI/soglie separati non esistono più. La
> colonna 4×1 non è una sotto-fascia opzionale: è il comportamento SEMPRE attivo di `stackFilters`
> stessa. La sparizione delle etichette non è più legata a NESSUNA soglia di layout: è governata
> solo da `labelHideActions`/`labelHideTabs`, dopo che l'auto-shrink lineare (Round 12) ha già
> fatto il possibile.

> ⚠️ **Round 12.1 — `oneColumn` come NUMERO è oggi inerte**: confermato tarando le soglie a mano —
> attraversarlo non produce nessun cambiamento visibile. Motivo: `oneColumn` è la fascia più
> stretta (Round 12 ha rimosso `iconOnly`, che le stava sotto), quindi la derivazione di
> `layoutMode` cade in `'oneColumn'` incondizionatamente appena si scende sotto `stackFilters`,
> senza mai confrontare il valore di questo campo. Il campo/soglia resta comunque (nel codice e
> nella tabella sotto) — non è stato rimosso — riservato per un'eventuale sotto-fascia futura
> ancora più stretta, che potrebbe reintrodurre un confine reale a questo numero.

### Valori attuali per pagina

| Pagina | `oneRow` | `denseRow` | `stackFilters` | `oneColumn` | `labelHideActions` | `labelHideTabs` | `noExtraLabel` | `maxWidthTwoRow` |
|---|---|---|---|---|---|---|---|---|
| Dashboard (`dashboard`) | 1000 | 810 | 430 | 390 | 210 | 370 | 410 | 390 *(default)* |
| Broker Detail (`brokerDetail`) | 1000 | 800 | 470 | 430 | 270 | 370 | — | 470 |
| Assets lista (`assetsList`) | 1340 | 850 | 440 | 400 | 250 | 370 | — | 410 |
| Assets dettaglio (`assetDetail`) | 1215 | 780 | 400 | 360 | 230 | 370 | — | 445 |
| Forex lista (`fxList`) | 1120 | 930 | 440 | 400 | 260 | 370 | — | 420 |
| Forex dettaglio (`fxDetail`) | 870 | 650 | 400 | 360 | 230 | 370 | — | 420 |

> 🆕 **Round 13**: `labelHideActions`/`labelHideTabs` sono i valori TARATI dall'utente
> (presumibilmente su dashboard, che ha sia Tab sia molte Azioni) — applicati come default di
> partenza uniformi su tutte e 6 le pagine, stesso flusso già seguito per ogni altra soglia in
> questa guida: si tarano poi singolarmente se serve. `noExtraLabel` è presente SOLO su dashboard
> (broker-detail ha lo stesso pattern "Valuta:" ma resta fuori scope per ora — vedi sezione
> dedicata). **Round 13.1**: dashboard ri-tarato dall'utente (`labelHideActions` 250→210,
> `noExtraLabel` 300→410) e persistito nel codice. **Round 14**: tutte le soglie ri-tarate
> dall'utente dopo test approfonditi su ogni pagina — vedi la sezione "Round 14" più sotto per il
> dettaglio riga-per-riga (cosa è cambiato e perché).

> 🆕 **Round 14 — `oneColumn` = `stackFilters − 40` per convenzione**: dato che `oneColumn` è
> inerte (vedi nota sotto), l'utente ha stabilito una regola pratica per NON doverlo pensare
> pagina per pagina: il suo valore è semplicemente `stackFilters - 40` ovunque — un margine
> "di sicurezza" riservato per un'eventuale sotto-fascia futura, non un numero da tarare a mano.
> Se in futuro cambi `stackFilters` di una pagina, ricalcola `oneColumn` con questa stessa
> formula (a meno che l'utente non chieda esplicitamente qualcos'altro).

> 📝 **Nota concettuale su `maxWidthTwoRow` (nessuna azione richiesta)**: `maxWidthTwoRow` (prop
> del `DateRangePicker`, default **390**) è il cap di larghezza del Picker (e per riflesso del
> "Centro", tramite `effectiveMaxWidth`) quando NON in `oneRow`. Il vero confine LIVE tra
> `stackFilters` e `oneColumn` è `stackFilters` stesso (non `oneColumn`, inerte) — quindi SE UN
> GIORNO si volesse un invariante "il Picker/Centro non restano più stretti dello spazio
> realmente disponibile", andrebbe legato a `stackFilters`, non a `oneColumn` (una versione
> precedente di questa nota, Round 13.1, lo legava erroneamente a `oneColumn`). **Per ora
> `maxWidthTwoRow` NON viene toccato automaticamente per nessuna pagina** — l'utente lo cambia
> solo quando lo chiede esplicitamente (vedi tabella sopra per i valori attuali).

> ⚠️ Segnalato dall'utente (dashboard a 460, assets a 414/460, PRIMA del Round 12): a
> `stackFilters` la colonna Picker+Centro PIÙ la colonna Azioni possono non stare nello spazio
> disponibile se `stackFilters` è tarato troppo basso rispetto al contenuto reale della pagina —
> causa overflow/clipping. Il Round 12 dovrebbe aver alleviato parte del problema (Azioni ora 4×1,
> più stretto di un 2×2; Centro ora capped a `pickerMaxWidth`≈390px anche su assets/asset-detail/
> fx-detail, che prima potevano eccedere) — ma i valori sopra restano quelli ereditati, mai
> ri-tarati live dopo questi fix. Ri-verifica col flusso di taratura sotto.

---

## 🔡 Auto-shrink lineare delle etichette — 🆕 Round 12

Alcune lingue rendono la stessa etichetta molto più lunga di altre (es. FR "Vue d'ensemble" vs IT
"Panoramica") — nasconderla del tutto appena non ci sta più (comportamento pre-Round-12) è uno
spreco. Da questo round, **sia le etichette dei Tab sia quelle delle Azioni** si RIMPICCIOLISCONO
prima di eventualmente scomparire (`labelHideActions`/`labelHideTabs` — 🆕 **Round 13**: due
soglie SEPARATE, non più una sola `labelHide` condivisa, vedi sezione dedicata sotto — restano
l'unico fallback finale, e restano soglie per-pagina interamente sotto il tuo controllo).

**Dove**: `frontend/src/lib/utils/layout/labelShrink.ts` — modulo condiviso, framework-agnostic
(nessuna rune Svelte al suo interno), usato da:
- `TabBar.svelte` — nuova prop opt-in `shrinkLabelsToFit` (default `false`, per non toccare
  `settings`/`files` che usano `TabBar` direttamente). `PageToolbar.svelte` la attiva SEMPRE sulla
  propria riga Tab (dashboard/broker-detail oggi, qualunque pagina futura con Tab la eredita
  gratis) — "globale", nessun toggle per pagina.
- `PageToolbar.svelte`, zona Azioni — **nessuna modifica alle 6 pagine**: gli span-etichetta
  vengono letti GENERICAMENTE dal DOM (`button > span`, la convenzione già seguita ovunque:
  `{#if showActionLabels}<span>{...}</span>{/if}` come figlio diretto del bottone) — si attiva
  automaticamente in tutte le pagine con Azioni, cioè tutte e 6.

**Come funziona** (scala LINEARE, non passi discreti fissi):
1. Per ogni etichetta visibile, un clone effimero fuori schermo (creato/distrutto al volo via JS
   — non un clone statico nel template come i badge del `DateRangePicker`, qui il set di
   etichette è dinamico/arbitrario) misura la larghezza NATURALE (mai troncata) al font originale.
2. Lo spazio DISPONIBILE per quell'etichetta è calcolato dalla geometria REALE e STABILE del
   bottone/tab (larghezza del bottone meno icona/gap/padding) — MAI dalla larghezza attuale
   dell'etichetta stessa (che potrebbe già essere ridotta o già andata a capo), così il
   meccanismo funziona correttamente sia per rimpicciolire SIA per tornare alla dimensione
   normale (es. tornando a una lingua più corta, o allargando la finestra).
3. Scala = `min(1, disponibile / naturale)` per ogni etichetta; il gruppo (tutti i Tab insieme,
   o tutte le Azioni insieme) usa il valore PEGGIORE (più piccolo) tra i suoi membri — un rapporto
   continuo misurato, non una scelta tra pochi livelli fissi — clampato a un **floor** di
   leggibilità (default **0.75**, cioè non scende sotto il 75% del font normale).
4. Applicata in **px assoluti** (mai `em`, che sarebbe relativo al genitore e romperebbe le classi
   Tailwind `text-*` già presenti sull'etichetta).
5. Piccola verifica bounded-retry post-applicazione (max 3 tentativi) per il margine di misura
   (subpixel/gap letto in modo leggermente impreciso) — se il wrap persiste anche al floor, si
   accetta: resta comunque leggibile, `labelHideActions`/`labelHideTabs` (se/quando l'utente le
   raggiunge) sono l'unico modo in cui l'etichetta sparisce davvero.
6. Ricalcolo su `ResizeObserver` del contenitore (coglie sia i resize di larghezza sia i cambi di
   ALTEZZA dovuti al wrap stesso — stesso principio già usato da `verifyNoWrap` del
   `DateRangePicker`); per i Tab, anche un effect esplicito sul testo delle etichette (cambio
   lingua) come ulteriore garanzia.

---

## ✂️ Split `labelHide` + nuova `noExtraLabel` — 🆕 Round 13

**Prima**: una SOLA soglia `labelHide` pilotava SIA le etichette dei Tab SIA quelle delle Azioni —
un solo numero per due gruppi con geometria/contenuto diversi. Testando a mano, l'utente ha
trovato due valori BUONI diversi (Tab: **370**, Azioni: **250**) — impossibile esprimerli con un
solo campo.

**Ora**: `LayoutThresholds.labelHide` è sparito, sostituito da 2 campi obbligatori indipendenti:

| Campo | Pilota | Derivato esposto |
|---|---|---|
| `labelHideActions` | Solo le etichette dei bottoni Azione | `showActionLabels` |
| `labelHideTabs` | Solo le etichette dei Tab | `showTabLabels` |

`PageToolbar.svelte` passa `showActionLabels` alla propria zona Azioni (`{#if showActionLabels}`,
invariato) e **ora** `showTabLabels` (non più `showActionLabels`) alla propria `<TabBar
showLabels={...}>` — prima dello split, la Zona Tab riusava per errore lo stesso segnale delle
Azioni, il che rendeva impossibile tarare i due gruppi in modo indipendente.

### 🆕 `noExtraLabel` — soglia opzionale, solo dashboard per ora

Sotto una certa larghezza, l'etichetta decorativa **"Valuta:"** davanti al selettore valuta di
dashboard (il testo di prefisso, NON il selettore stesso — quello resta sempre visibile) inizia a
creare problemi di spazio. Non è la stessa cosa di `labelHideActions`/`labelHideTabs` (che
nascondono etichette DI BOTTONI/TAB) — è un'etichetta EXTRA, decorativa, indipendente da qualunque
Azione/Tab — quindi ha una soglia propria:

- **Campo**: `noExtraLabel?: number` in `LayoutThresholds` — **opzionale** (solo dashboard lo
  imposta oggi; le altre 5 pagine non lo passano, zero impatto per loro).
- **Derivato**: `showExtraLabels = thresholds.noExtraLabel == null || width >= thresholds.noExtraLabel`
  — default `true` (etichetta sempre visibile) quando il campo non è impostato.
- **Esposto**: `PageToolbar.svelte` passa `showExtraLabels` come nuovo parametro dello snippet
  `filters` (accanto a `layoutMode`/`isStacked`/`filtersStacked`).
- **Uso** (`dashboard/+page.svelte`, `noExtraLabel: 300`): `{#if showExtraLabels}<span>{$_('common.currency')}:</span>{/if}` — solo il testo "Valuta:" è condizionale, il `<CurrencySearchSelect>` resta
  sempre visibile.
- **Decisione architetturale** (confermata via `ask_user`): flag/soglia INDIPENDENTE, NON un nuovo
  valore di `LayoutMode` — attraversare questa soglia non causa nessun reflow strutturale, cambia
  solo la visibilità di QUESTA specifica etichetta.
- **Broker-detail ha lo stesso pattern "Valuta:"** ma non è stato toccato in questo round (fuori
  scope esplicito, "gli altri staremo a vedere") — resta un'estensione naturale futura: basta
  aggiungere `noExtraLabel: N` alle sue soglie e lo stesso `{#if showExtraLabels}` nel suo snippet
  `filters`.

---

## 📐 "Centro giustificato" — ora su tutte e 6 le pagine — 🆕 Round 12

Segnalato dall'utente: la regola "giustificata" (Centro allineato a sinistra, mai centrato,
larghezza allineata pixel-perfetta al Picker via `effectiveMaxWidth`/`pickerMaxWidth`) era
applicata SOLO su dashboard/brokerDetail/fxList — assetsList/assetDetail/fxDetail restavano
centrati e senza cap di larghezza. Estesa a tutte e 6:

- `assets/+page.svelte`: nuovo state `pickerMaxWidth` (init 390) +
  `bind:effectiveMaxWidth={pickerMaxWidth}` sul proprio `DateRangePicker`; blocco Centro
  (ricerca+filtri) da `items-center` a `items-start w-full` + cap di larghezza quando
  `filtersStacked`.
- `assets/[id]/+page.svelte` + `AssetPriceSummary.svelte`: stessa aggiunta di stato/bind nella
  pagina; nuove prop `filtersStacked`/`maxWidth` sul componente, che ora usa
  `items-start`/`justify-between` (invece di `items-center`/`justify-center`) + cap quando
  `filtersStacked` (⚠️ `justify-between` qui è quello introdotto in Round 12 — **Round 13** lo
  sostituisce con `justify-around`, vedi sezione subito sotto).
- `fx/[pair]/+page.svelte` + `FxPriceSummary.svelte`: stessa modifica, simmetrica.

Nessun'altra pagina era mancante (dashboard/brokerDetail/fxList erano già corrette).

---

## ⚖️ `justify-around` come standard universale — 🆕 Round 13

**Segnalazione utente**: quando una riga "Centro" capped (~390px) contiene solo 2 elementi piccoli
(es. FX: tasso "5.2340" + delta "+4.05%"), `justify-between` li spinge ai 2 estremi lasciando un
vuoto enorme ed esteticamente sbagliato in mezzo. Richiesta: distribuire lo spazio libero come
**1/4 inizio — 2/4 centro — 1/4 fine**, "stessa logica per tutte le righe" — poi ESTESA (dopo un
primo giro di piano più conservativo, respinto) a: **`justify-around` deve diventare lo standard
UNICO per ogni riga "Centro" capped/`filtersStacked`, sostituendo sia `justify-between` sia
`justify-center` ovunque, indipendentemente dal numero di elementi**.

### La matematica — perché `justify-around` è ESATTAMENTE 1/4:2/4:1/4 per 2 elementi

Per una riga flex con ESATTAMENTE 2 figli, `justify-around` (`justify-content: space-around`) dà a
ciascun figlio uno spazio EGUALE su entrambi i lati. Se l'unità di spazio libero per lato è `x`:
- margine iniziale (bordo sinistro → 1° elemento): `x`
- margine centrale (tra i 2 elementi): SOMMA di 2 margini adiacenti = `x + x = 2x`
- margine finale (2° elemento → bordo destro): `x`

Totale spazio libero = `x + 2x + x = 4x` → proporzioni esatte: inizio `x/4x = 1/4`, centro
`2x/4x = 2/4`, fine `x/4x = 1/4`. **Combacia esattamente** con la richiesta — nessuna classe CSS
custom necessaria, basta usare la classe Tailwind nativa `justify-around`.

Per **1 solo elemento**, `justify-around` produce lo STESSO risultato visivo di `justify-center`
(margine uguale sui 2 lati = elemento centrato) — il cambio lì è di CONVENZIONE/uniformità (stessa
classe ovunque), non di resa visiva. Per **N>2** elementi, distribuisce uno spazio uguale ATTORNO a
ciascun elemento (non solo tra le coppie adiacenti come `justify-between`, che lascia gli estremi
"attaccati" al bordo) — generalizzazione naturale della stessa logica 1/4:2/4:1/4.

### File toccati (tutti e 6)

| File | Riga | Prima | Dopo |
|---|---|---|---|
| `dashboard/+page.svelte` | Centro (valuta+filtro broker, 2 elementi) | `justify-between` | `justify-around` |
| `brokers/[id]/+page.svelte` | Centro (selettore valuta, 1 elemento) | `justify-center` | `justify-around` |
| `assets/+page.svelte` | riga1 (search+toggle) e riga2 (tipo+valuta+reset) — **prima NESSUNA delle 2 aveva `w-full`/`justify-*`** | *(nessuna classe)* | `w-full justify-around` |
| `AssetPriceSummary.svelte` | riga1 (prezzo+delta, 2 elementi) | `justify-between` | `justify-around` |
| `AssetPriceSummary.svelte` | riga2 (valuta "Converti in", 1 elemento SOLO — prima NESSUNA classe) | *(nessuna classe)* | `justify-around w-full` |
| `FxPriceSummary.svelte` | unica riga (tasso+delta, 2 elementi) | `justify-between` | `justify-around` |
| `fx/+page.svelte` | Centro (2 select valuta + reset, 3 elementi) | `justify-center` | `justify-around` |

> ⚠️ **Il bug "2 div invece di 4" segnalato su assets lista NON era quello che sembrava**: il
> wrapper ESTERNO (Round 12: `items-start w-full` + cap) era già corretto — ma le 2 righe INTERNE
> (search+toggle / tipo+valuta+reset) non avevano MAI avuto `w-full`/`justify-*` fin dall'inizio,
> quindi lo spazio libero del cap (~390px) non veniva mai distribuito al LORO interno (nessun
> effetto da nessuna classe `justify-*`, con o senza spazio da distribuire). La causa reale non era
> il numero di `<div>`, era la mancanza di `w-full` su quei 2 div — la stessa identica dinamica di
> `AssetPriceSummary.svelte`'s riga2 (valuta "Converti in", che l'utente si aspettava centrata
> perché sola sulla riga, ma restava a sinistra per lo stesso identico motivo).

---

## 🩹 Bugfix Round 13.1 — label + controllo devono condividere UN div

**Segnalazione utente**: su broker-detail, `justify-around` era applicato correttamente alla riga,
ma l'etichetta "Valuta:" e il selettore valuta finivano SEPARATI ai 2 estremi (grande vuoto in
mezzo) invece di restare visivamente uniti come un solo blocco "Valuta: [selettore]".

**Causa**: `justify-around` distribuisce spazio tra i figli DIRETTI del contenitore flex. Se
etichetta e selettore sono 2 elementi FRATELLI diretti (non un unico wrapper), vengono trattati
come 2 unità INDIPENDENTI da spaziare — esattamente la stessa dinamica di 2 controlli
genuinamente distinti (es. la coppia valuta+broker di dashboard), ma qui i 2 "figli" sono in
realtà UN SOLO controllo logico (etichetta + il suo select), che deve restare un blocco unico.

**Fix**: avvolgere etichetta + selettore in un wrapper `<div class="flex items-center gap-1.5">`
condiviso, così il contenitore `justify-around` esterno vede UN SOLO figlio per quel controllo (si
comporta come `justify-center` per N=1 — l'intero blocco resta unito e centrato). Corretto in:

- `brokers/[id]/+page.svelte` — riga Centro (etichetta "Valuta:" + `CurrencySearchSelect`).
- `AssetPriceSummary.svelte` — riga2 (etichetta "Converti in" + `CurrencySearchSelect`); l'icona
  opzionale di link al pair FX resta un fratello SEPARATO (azione supplementare distinta, non
  parte del controllo di selezione valuta in sé — quando l'icona non c'è, un solo figlio, centrato
  come sopra; quando c'è, 2 figli: blocco-etichetta+selettore E icona, spaziati 1/4:2/4:1/4).

**Dove NON serviva alcun fix** (verificato per esclusione, stesso pattern controllato su tutti i
file `justify-around`): `dashboard/+page.svelte` (già corretto — l'etichetta valuta era già nel suo
wrapper); `assets/+page.svelte` righe 1-2 (nessuna etichetta separata da un controllo — sono
SEMPRE gruppi di controlli genuinamente distinti tra loro); `fx/+page.svelte` (2 select + reset,
nessuna etichetta testuale separata); `FxPriceSummary.svelte`/riga1 di `AssetPriceSummary.svelte`
(tasso/prezzo+delta, nessuna etichetta separata dal suo valore).

**Regola generale da tenere a mente per il futuro**: prima di aggiungere `justify-around` (o
qualunque `justify-*`) a una riga, chiediti "quanti CONTROLLI LOGICI distinti ci sono, non quanti
elementi DOM?" — un'etichetta + il suo input/select è SEMPRE un solo controllo logico e deve
condividere un wrapper, anche se sono 2 tag HTML.

---

## 🩹 Bugfix Round 13.1 — invariante `maxWidthTwoRow` ≥ `oneColumn`

Vedi tabella soglie sopra per il dettaglio completo (nuova colonna `maxWidthTwoRow`) — riassunto:
`maxWidthTwoRow` (default 390) è il cap di larghezza del Picker/Centro fuori da `oneRow`; se più
stretto della soglia `oneColumn` della pagina, il layout non riempie lo spazio realmente
disponibile una volta entrati in `oneColumn`. Le 5 pagine con `oneColumn > 390` ora passano un
`maxWidthTwoRow` esplicito pari alla propria soglia `oneColumn` — dashboard (`oneColumn: 365`)
resta sul default (già conforme). **Se in futuro alzi una soglia `oneColumn` oltre il
`maxWidthTwoRow` attuale, ricordati di alzare anche quest'ultimo — non è automatico.**

---

## 🔎 Diagnosi Round 13.1 — "layoutMode è `oneColumn` ma `thresholds.oneColumn` è più stretto della larghezza reale": NON è un bug

**Segnalazione utente** (broker-detail): `layoutMode` risultava `'oneColumn'`, `thresholds.oneColumn`
era 390 (live-tarato), ma il contenitore reale misurava 429px in Chrome DevTools — 429 > 390,
eppure la fascia era `'oneColumn'`. `stackFilters` invece rispondeva bene alla propria soglia.

**Spiegazione (rileggi la nota Round 12.1 sopra)**: `thresholds.oneColumn` è **INERTE** — non
viene MAI confrontato nella derivazione di `layoutMode` (vedi `responsiveLayout.svelte.ts`,
righe ~104-115). L'UNICO confronto che conta per cadere in `'oneColumn'` è
`larghezza < thresholds.stackFilters`: sotto quella soglia si è SEMPRE e SOLO `'oneColumn'`,
qualunque sia il valore (o il live-tuning) di `thresholds.oneColumn`.

Nel caso segnalato: 429px in DevTools è quasi certamente **border-box** (Tailwind applica
`box-sizing: border-box` di default) — il valore CONTENT-BOX confrontato con le soglie è
429 − 32px (`p-4`) ≈ **397px**. Il codice di broker-detail ha `stackFilters: 560` → 397 < 560 →
`'oneColumn'` è ESATTAMENTE il risultato atteso, non vicino a nessun confine ambiguo. Anche
l'altezza riportata (214px, molto alta) conferma: `'oneColumn'` impila TUTTO in colonna
(Picker 2 righe + Centro + Azioni 2×2 + Tab), quindi un box stretto E alto è coerente con quella
fascia, non un sintomo di stato "sbagliato".

**Che fare se si vuole restare in `'stackFilters'` fino a una larghezza più stretta**: abbassa il
valore di **`stackFilters`** stesso — MAI `oneColumn`, che non ha alcun effetto. Nessuna modifica
al codice è stata fatta PER QUESTA DIAGNOSI (comportamento intenzionale, confermato e documentato
dall'utente stesso in Round 12.1); questa sezione esiste solo per chiarire il meccanismo la
prossima volta che il dubbio si ripresenta.

> ✅ **Round 14 — seguito pratico**: l'utente ha poi confermato empiricamente (live-tuning in
> console) che abbassare `stackFilters` a **470** (da 560) dava il comportamento desiderato su
> broker-detail — esattamente l'azione descritta sopra ("abbassa `stackFilters`"). Il valore 470
> è stato persistito nel codice (vedi tabella soglie in cima). L'esempio numerico sopra (560,
> 397px) resta la cronaca di COME si è arrivati alla diagnosi — il valore live in codice oggi è
> diverso (470), l'importante è il MECCANISMO (solo `stackFilters` conta), non il numero storico.

---

### Dove sono definite (una chiamata per pagina)

Tutte e 6 le pagine usano `<PageToolbar thresholds={{...}}>` (stesso componente condiviso — un
fix fatto in `PageToolbar.svelte` si propaga automaticamente a tutte, non serve replicarlo
pagina per pagina).

| Pagina | File | Nome registro console | `filterRowTestId` |
|---|---|---|---|
| Dashboard | `routes/(app)/dashboard/+page.svelte` | `dashboard` | `dashboard-filter-bar` |
| Broker Detail | `routes/(app)/brokers/[id]/+page.svelte` | `brokerDetail` | `broker-overview-controls` |
| Assets (lista) | `routes/(app)/assets/+page.svelte` | `assetsList` | `assets-filter-bar` |
| Assets (dettaglio) | `routes/(app)/assets/[id]/+page.svelte` | `assetDetail` | `asset-detail-filter-bar` |
| Forex (lista) | `routes/(app)/fx/+page.svelte` | `fxList` | `fx-filter-bar` |
| Forex (dettaglio) | `routes/(app)/fx/[pair]/+page.svelte` | `fxDetail` | `fx-detail-filter-bar` |

(vedi la tabella "Valori attuali per pagina" sopra per le soglie di ciascuna)

---

## 💻 Comandi Console — Test Live (F12 → Console)

Tutte le pagine registrano la propria istanza su `window.__lfLayouts.<nome>` — **sempre
disponibile**, anche sulla build di produzione locale, non serve alcun flag debug. Campi:
`labelHideActions`/`labelHideTabs` (Round 13, sostituiscono la vecchia `labelHide` singola),
`noExtraLabel` (opzionale). Non esistono più `iconOnly`/`actionsColumn`/`labelHide` (singola):

```js
// Vedi le soglie attuali di una pagina
window.__lfLayouts.dashboard.thresholds
// { oneRow: 1000, denseRow: 810, stackFilters: 430, oneColumn: 390, noExtraLabel: 410, labelHideActions: 210, labelHideTabs: 370 }

// Cambia una soglia — ricalcola SUBITO, nessun resize richiesto (`oneColumn` è l'eccezione:
// attualmente inerte, vedi nota sopra — usa `stackFilters` o le altre per un effetto visibile)
window.__lfLayouts.dashboard.thresholds.stackFilters = 480

// Round 13: le 2 soglie label sono indipendenti — tara Tab e Azioni separatamente
window.__lfLayouts.dashboard.thresholds.labelHideTabs = 380     // solo Tab
window.__lfLayouts.dashboard.thresholds.labelHideActions = 260  // solo bottoni Azione

// Round 13: noExtraLabel esiste solo dove il campo è impostato (oggi solo dashboard)
window.__lfLayouts.dashboard.thresholds.noExtraLabel = 320

// Leggi la modalità corrente risultante
window.__lfLayouts.dashboard.layoutMode
// 'oneRow' | 'denseRow' | 'stackFilters' | 'oneColumn'   (Round 12: 'iconOnly' rimossa)

// isStacked/filtersStacked/showActionLabels/showTabLabels/showExtraLabels NON sono esposti
// direttamente (sono calcolati dentro PageToolbar, non fanno parte del layout registrato) —
// deducili da layoutMode + thresholds:
//   isStacked      = layoutMode === 'oneColumn'
//   filtersStacked = layoutMode === 'stackFilters' || isStacked
//   showActionLabels = <larghezza reale> >= thresholds.labelHideActions
//   showTabLabels    = <larghezza reale> >= thresholds.labelHideTabs
//   showExtraLabels  = thresholds.noExtraLabel == null || <larghezza reale> >= thresholds.noExtraLabel

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
(cambia anche il `data-testid` nello snippet diagnostico — vedi la tabella "Dove sono definite"
sopra per il `filterRowTestId` esatto di ciascuna pagina).

### Flusso di taratura consigliato

1. Apri la pagina da tarare, F12 → Console.
2. Ridimensiona la finestra fino al punto in cui il comportamento ti sembra sbagliato.
3. Leggi `window.__lfLayouts.<nome>.thresholds` per i valori attuali.
4. Modifica il campo sospetto (es. `stackFilters`) e osserva il cambiamento immediato —
   `oneColumn` è l'eccezione: oggi non produce nessun effetto, vedi nota sopra.
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
centrata, larghezza del Centro allineata pixel-perfetto al Picker via `effectiveMaxWidth` — Round
12: ora su TUTTE e 6 le pagine, vedi sezione dedicata) — ma questa colonna resta **AFFIANCATA**
alle Azioni (`justify-between` ancora attivo sulla riga esterna). Azioni: **colonna verticale 4×1
CON etichetta** (non griglia 2×2 — `actionsStacked` in `PageToolbar.svelte` è vero SOLO qui).

### ONE COLUMN (`layoutMode === 'oneColumn'`, < soglia `stackFilters`) — fascia più stretta

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

Questa è la fascia che si chiamava `'mobile'` nel modello originale (senza soglia propria) — è
stata promossa a fascia di primo piano con nome e soglia dedicati (Round 11), perché lo
spostamento delle Azioni è una decisione di layout a sé, non un dettaglio secondario. **Round
12**: è ORA la fascia più stretta di tutte — non esiste più una fascia `iconOnly` sotto di essa.
Se un'etichetta (Azione o Tab) non ci sta più a questa larghezza, si rimpicciolisce (vedi
"Auto-shrink lineare" sopra) prima di eventualmente scomparire tramite
`labelHideActions`/`labelHideTabs` (due soglie separate) — non scompare mai "a scatto" per il
solo fatto di essere in `oneColumn`.

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
   (`'denseRow'`, `'stackFilters'`, `'oneColumn'`) → SEMPRE 2 righe. Una pagina che non passa
   `layoutMode` ottiene il default 1-riga.
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

Due prop separate, una per modalità riga (un unico valore condiviso rendeva il layout a 2 righe
sproporzionato: ogni riga molto più larga del contenuto che porta, con grandi vuoti lasciati da
`justify-between`):

| Prop | Si applica quando | Default |
|---|---|---|
| `maxWidth` | `isSingleRow` è vero (`layoutMode === 'oneRow'`, 1 riga) | **740px** (tarato dall'utente — prima era 672px, la classe fissa Tailwind `max-w-2xl`) |
| `maxWidthTwoRow` | `isSingleRow` è falso (`layoutMode` è tutto il resto, 2 righe) | **390px** (tarato dall'utente — vedi tabella soglie in cima per gli override espliciti per pagina) |

Il tetto massimo di larghezza che il picker può occupare quando condivide la riga con altri
filtri (valuta, filtro broker, ecc.). Sotto il cofano diventa uno `style="max-width: {}px"`
inline (necessario per essere veramente dinamico — le classi Tailwind sono fisse a build-time);
il valore effettivo (`effectiveMaxWidth`) sceglie automaticamente tra le due prop in base a
`isSingleRow`, quindi passa da uno all'altro da solo attraversando la soglia `oneRow` — nessun
wiring aggiuntivo richiesto.

**Round 14**: `DateRangePicker.svelte`, quando `align="start"`, applica GIÀ da solo
`grow`+`self-stretch`+`style="max-width:{effectiveMaxWidth}px"` sulla propria root — si
autolimita correttamente senza bisogno di alcun wrapper esterno. **Non avvolgerlo in un
ulteriore `<div class="flex flex-1 ...">` senza il suo stesso cap di larghezza** — un wrapper
così si espande oltre il contenuto reale del picker (che resta capped internamente), lasciando
uno spazio invisibile che spinge qualsiasi fratello successivo (es. il Centro) più a destra di
quanto dovrebbe (bug trovato/corretto in Round 14 su 4 pagine). Se serve un wrapper solo per
attaccarci un `data-testid` (senza alcun effetto di layout), usa `class="contents"` — esce dal
box model, l'attributo resta comunque interrogabile da Playwright.

### `effectiveMaxWidth` (bindable) — allineare il Centro alla larghezza REALE del picker

Quando `filtersStacked` è vero (Centro impilato SOTTO il picker), il Centro deve avere la STESSA
larghezza del picker (non quella del contenitore/colonna esterna, che resta più largo per non
lasciare un vuoto enorme rispetto alle Azioni — vedi `stackFilters` sopra). Il picker espone il
proprio `effectiveMaxWidth` corrente come prop **bindable**:

```svelte
<DateRangePicker ... bind:effectiveMaxWidth={pickerMaxWidth} />
<div class="{filtersStacked ? 'w-full' : ''}" style={filtersStacked && pickerMaxWidth ? `max-width: ${pickerMaxWidth}px` : ''}>
    <!-- contenuto Centro -->
</div>
```

`pickerMaxWidth` si aggiorna live insieme a `pickerConfig.maxWidthTwoRow` (anche da console,
senza resize) — il Centro resta sempre pixel-allineato al picker durante il tuning. Pattern usato
da tutte e 6 le pagine (bug storico: prima il Centro usava solo `w-full`, che lo stendeva alla
larghezza dell'intera colonna esterna — più larga del picker stesso — creando un bordo destro
disallineato).

### ⚠️ Gotcha noto — perché esiste ancora il "verify+shed"

L'algoritmo di misura usa larghezze REALI (non stime), ma un margine piccolo (badge nascosto di
misura vs badge reale, o il gap CSS che non corrisponde esattamente al valore hardcoded) può
farlo sbagliare **per un solo badge** a certe larghezze — SOLO sul CONTEGGIO dei jolly (la scelta
1-vs-2-righe non può sbagliare, è fissata da `oneRow`). Se questo succede, il CSS nativo
(`flex-wrap`) spacca la riga interessata in 2 SENZA che il JS se ne accorga — e siccome il
contenitore misurato cambia solo di ALTEZZA (non di larghezza) quando questo avviene, il calcolo
sbagliato **si ripete identico per sempre**, anche a resize successivi: un "punto fisso sbagliato"
che resta bloccato finché non si ricarica la pagina.

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

## 📁 Estendere il sistema a una nuova pagina — checklist

Per una NUOVA pagina che vuole lo stesso pattern (breakpoint responsive + badge jolly nel
DateRangePicker):

1. Usa `<PageToolbar thresholds={{oneRow, denseRow, stackFilters, oneColumn, labelHideActions,
   labelHideTabs}} layoutDebugName="nomeUnivoco">` (tutte e 6 le soglie sono obbligatorie;
   opzionale: `noExtraLabel` se la pagina ha un'etichetta decorativa da nascondere
   indipendentemente — vedi sezione dedicata) — la zona `filters` riceve `{layoutMode, isStacked,
   filtersStacked, showExtraLabels}`, `summary` riceve `{layoutMode, isStacked, filtersStacked}`,
   `actions` riceve `{layoutMode, showActionLabels, actionsStacked}`. Usa questi flag semantici,
   MAI `layoutMode === 'oneColumn'` direttamente (la semantica di ogni livello può cambiare in
   futuro, solo `PageToolbar` dovrebbe doversi aggiornare) — in particolare usa `filtersStacked`
   (non `isStacked`) per qualsiasi stile "il mio contenuto Centro deve diventare full-width/
   giustificato quando il Picker si impila" (`isStacked` è vero SOLO nella fascia più stretta,
   `oneColumn`, dove impila TUTTO incluse le Azioni). Per `oneColumn`, applica la convenzione
   `oneColumn = stackFilters - 40` (Round 14 — riservato/inerte, vedi note sopra).
2. **DateRangePicker**: passa `align="start"` + `layoutMode={layoutMode}` (dallo stesso snippet
   `filters`/`summary` — OBBLIGATORIO: senza questa prop il picker resta sempre a 1 riga,
   ignorando le soglie della pagina) + lo stesso `debugName="nomeUnivoco"` usato al punto 1 (così
   soglie e `maxWidth` finiscono sulla stessa voce del registro console). NON avvolgerlo in un
   `<div class="flex flex-1 ...">` senza cap (vedi nota Round 14 sopra) — se serve solo un
   `data-testid`, usa `class="contents"`. Se il Centro deve allinearsi in larghezza al picker
   quando `filtersStacked` (vedi sezione `effectiveMaxWidth` sopra), fai anche
   `bind:effectiveMaxWidth={miaVariabileLocale}` sul picker e applicalo come `max-width` inline
   sul div Centro. Se la pagina ha bisogno di leggere `layoutMode` ANCHE fuori dalle snippet (es.
   un testo che cambia in base al layout, non solo dentro filters/actions), usa
   `bind:layoutMode={miaVariabile}` su `<PageToolbar>` E passa quella stessa variabile al picker
   (vedi `assets/[id]/+page.svelte` o `fx/[pair]/+page.svelte` per un esempio — entrambe fanno
   `layoutMode={pageLayoutMode}`).
3. Se la pagina ha altri elementi da affiancare al DateRangePicker nella zona `filters` (valuta,
   filtro broker, ricerca, ecc.), dagli **`shrink-0`** — MAI lasciarli con lo shrink di default:
   solo il DateRangePicker deve restringersi/perdere badge quando lo spazio si stringe, gli altri
   elementi restano alla loro dimensione naturale (bug reale trovato e corretto in passato — il
   gruppo valuta/broker andava a capo invece di lasciar restringere il picker).
4. Ogni riga "Centro" con più di un elemento capped/`filtersStacked` deve usare `justify-around`
   (mai `justify-between`/`justify-center`) — è lo standard universale (vedi sezione dedicata).
   **Se una riga contiene un'etichetta + il suo controllo** (es. "Valuta: [selettore]"),
   avvolgili in UN wrapper condiviso — sono un solo controllo logico, non 2 elementi da spaziare
   separatamente (bug trovato/corretto più volte, vedi sezione "bugfix label-div").

---

## 🆕 Round 14 — soglie finali, 4 bugfix, tuning cosmetico

Dopo un giro di test approfondito su tutte e 6 le pagine, l'utente ha fornito le soglie finali
(vedi tabella in cima) e segnalato 4 problemi distinti, tutti risolti:

### Bug 1 — Centro allineato a destra invece che a sinistra (denseRow)

**Causa**: `DateRangePicker.svelte` si autolimita già (vedi sezione `maxWidth`/`maxWidthTwoRow`
sopra) — ma 4 pagine (assetsList, assetDetail, fxList, fxDetail) lo avvolgevano in un
`<div class="flex flex-1 self-stretch min-w-0">` **senza alcun cap proprio**. Questo wrapper si
espandeva (flex-1, illimitato) ben oltre il contenuto reale del picker (limitato internamente),
lasciando uno spazio invisibile PRIMA del Centro (un fratello successivo nella stessa riga flex)
— il Centro finiva quindi spinto verso destra (verso le Azioni) invece di restare adiacente al
picker. Dashboard/brokerDetail non avevano questo wrapper extra (chiamano `<DateRangePicker>`
nudo) e infatti non avevano il bug. Più visibile in `denseRow` che in `oneRow` perché in `oneRow`
il meccanismo "jolly badge fill" del picker consuma attivamente più spazio (il gap si nota meno).

**Fix**: wrapper cambiato da `flex flex-1 self-stretch min-w-0` a `contents` (Tailwind
`display:contents` — il div esce dal box model, il suo unico figlio `<DateRangePicker>` diventa
figlio flex DIRETTO della riga, ereditando il proprio auto-limite corretto; `data-testid` resta
comunque interrogabile perché è solo un attributo DOM, non influenzato da `display:contents`).

### Bug 2 — pannello "Tutti i tipi" (assetsList) tagliato/clippato

**Causa**: `PageToolbar.svelte` ha `overflow-hidden` sulla card esterna. Il pannello "Tutti i
tipi" di assetsList è hand-rolled con `position: absolute` (dentro `filters`, quindi dentro la
card `overflow-hidden`) → viene tagliato ogni volta che vorrebbe overfloware i bordi della card.
`CurrencySearchSelect` (usato per i filtri valuta) usa GIÀ `position: fixed` + `z-index: 9999`
con coordinate calcolate da `getBoundingClientRect()` — non ha questo problema.

**Fix**: estratta l'utility `getFixedDropdownPosition()`/`clamp()` (prima locale a
`dashboard/+page.svelte`, che la usava già per i propri dropdown broker-filter/AI-export) in un
nuovo file condiviso `frontend/src/lib/utils/layout/dropdownPosition.ts`; dashboard refactorizzato
per importarla (nessun cambio di comportamento); stesso meccanismo applicato al pannello "Tutti i
tipi" — passa da `absolute z-50` a `fixed` con coordinate calcolate e ricalcolate su resize/scroll
mentre è aperto, mai più tagliato da un antenato `overflow-hidden`.

> ⚠️ **Nota per il futuro**: lo stesso `overflow-hidden` di `PageToolbar` potrebbe in teoria
> tagliare ALTRI dropdown hand-rolled con `position:absolute` altrove nell'app, se ce ne sono —
> nessun altro trovato nello scope del Round 14, ma è un pattern da tenere a mente.

### Bug 3 — header titolo+bottoni si comprimono invece di impilarsi

**Causa (v1)**: `fx/+page.svelte` e `assets/+page.svelte` usavano `class="flex items-center
justify-between"` per l'header (titolo a sinistra, ViewModeToggle+bottone Aggiungi a destra) —
MAI impilato, quindi sotto spazio scarso titolo e bottoni si comprimevano a vicenda.
`brokers/+page.svelte` aveva GIÀ un pattern che impilava, ma con lo stesso difetto scoperto poi
al Round 14.1 (vedi sotto).

**Fix (v1, Round 14)**: applicato lo stesso pattern di `brokers/+page.svelte` a entrambe le
pagine: `class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"`.

> ⚠️ **Round 14.1 — bug nel fix stesso**: `lg:` è una breakpoint VIEWPORT (1024px, media query) —
> sotto quella larghezza IMPILA SEMPRE, indipendentemente da quanto spazio ha REALMENTE
> l'header (che potrebbe benissimo starci su una riga anche a 900px di viewport). L'utente ha
> segnalato "i bottoni sono sempre nella seconda riga" su fx list — l'opposto di "impila solo se
> lo spazio non basta". **Fix corretto**: sostituito `flex-col gap-4 lg:flex-row lg:items-start
> lg:justify-between` con **`flex flex-wrap items-start justify-between gap-4`** — nessuna
> breakpoint fissa, il wrap CSS nativo scatta solo quando il contenuto (titolo + bottoni) non ci
> sta davvero nella larghezza REALE del contenitore, esattamente come richiesto. Il gruppo
> bottoni interno perde il suo `lg:justify-end` (diventa `justify-end` incondizionato — ininfluente
> quando il gruppo sta sulla riga del titolo, via `justify-between` del contenitore esterno).
> Corretto su **tutte e 3** le pagine con questo pattern: `fx/+page.svelte`, `assets/+page.svelte`
> E `brokers/+page.svelte` (l'originale copiato — stesso bug latente, non segnalato ma
> identico). Dashboard non ha questo pattern (titolo `sr-only`, invisibile) — non applicabile.
> broker-detail non ha un header titolo+bottoni simile — non applicabile.

### Bug 4 — componenti fxList si restringono troppo lasciando spazio vuoto

**Causa**: i 2 filtri valuta di fxList erano fissi (`w-28 sm:w-40`) anche da stackati/capped —
quindi lo spazio libero nel cap finiva come GAP vuoto (via `justify-around`) invece di allargare
i componenti stessi.

**Fix**: quando `filtersStacked`, entrambi i wrapper diventano `flex-1 min-w-0` (si dividono
equamente lo spazio disponibile, crescono invece di lasciare vuoti); restano `w-28 sm:w-40` fissi
altrove (oneRow/denseRow, non segnalato come problema lì).

### Tuning cosmetico (valori di partenza, verificati/tarati visivamente dall'utente)

- assetsList — ricerca asset: `min-w-[160px]` aggiunto (era senza floor, poteva schiacciarsi
  troppo sotto la larghezza naturale `w-44`/176px).
- assetsList — bottone "Tutti i tipi": `min-w-0` + testo avvolto in `<span class="truncate">` —
  ora si restringe con ellissi invece di forzare l'overflow della riga.
- assetsList — filtro valuta: `w-36 min-w-[96px]` (poteva restringersi solo fino al suo
  min-content naturale, spesso già piccolo, ora ha un floor esplicito).
- assetDetail — "Converti in" (`AssetPriceSummary.svelte`): `w-28 sm:w-32` → `w-32 sm:w-36`.

### `oneColumn = stackFilters − 40` — convenzione stabilita in questo Round

Vedi nota dedicata nella sezione soglie sopra — dato che `oneColumn` è inerte, l'utente ha
stabilito questa formula come default per non doverlo pensare pagina per pagina.

**Nessuna modifica a `maxWidthTwoRow`** in questo Round (richiesta esplicita dell'utente — resta
quello attuale ovunque, si cambia solo su richiesta esplicita futura). Vedi comunque la nota
concettuale nella sezione soglie sopra (l'invariante, se mai riconsiderato, andrebbe legato a
`stackFilters`, non a `oneColumn`).
