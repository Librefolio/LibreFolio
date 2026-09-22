# F2 — Primitive e il contratto che le fa trovare

> **Fase 1 · fondamenta.** Gira insieme a F1 e a nient'altro.
> **Sessione**: D `e-alfy-risk-primitives-cards` (riuso)
> **Baseline**: `2ec19b8f0` — **verificala prima di leggere oltre**
> **Corsia**: `--test-port 6152` · `--data-dir /tmp/librefolio-r2-f2`

---

## 1. La ragione per cui questo mandato esiste, e non è quella che sembra

Hai costruito `RiskMetricCard`: **131 righe di componente, 187 di test, un'intestazione che
spiega ogni decisione con la misura che l'ha prodotta.** È fatta bene.

```bash
$ grep -rl RiskMetricCard frontend/src/lib --include=*.svelte | grep -v 'ui/display/'
$          # nessun risultato
```

**Zero consumatori.** E il pannello che avrebbe dovuto usarla rende una `<ul>` con
`<li class="flex justify-between">` che a schermo largo spinge etichetta e numeri ai due bordi
opposti — esattamente il difetto che la tua card risolve con `@container`.

> ## 🔑 Il difetto non è nella card: **è in dove sta il contratto**
>
> L'intestazione di `RiskMetricCard.svelte` contiene già tutto ciò che serve per adottarla —
> perché `@container` e non i breakpoint, perché la doppia etichetta, quale metà della garanzia
> anti-salto è a carico del chiamante.
>
> **Ma sta dentro il file che nessuno ha aperto.** Un contratto va dove lo si legge *prima* di
> aver bisogno del file, non dentro il file di cui non si sa ancora di aver bisogno.

⚠️ **Correzione a un'assunzione del coordinatore, fatta prima di scriverti**: il piano diceva
*«rendere la card adottabile»*. **Ho letto le props: è già adottabile.** `label`,
`technicalName`, `value`, `numericValue` + `formatValue`, `caption`, `sentiment`, `docsPath`,
`loading`, `testId`, e gli snippet `submetrics` e `sparkline`. **Non manca niente.** Lo scopo
di questo mandato non è ripararla — **è renderla trovabile e disporla.**

---

## 2. I tre deliverable, in ordine di importanza

### 2.1 🔴 `PRIMITIVE.md` — il deliverable che conta

Una pagina, alla radice di `implementation_2/`, che **ogni mandato di superficie deve leggere
prima di scrivere una riga**. Deve rispondere a quattro domande, e basta:

```
Cosa esiste già            per ogni primitiva: nome, percorso, a cosa serve in una riga
Come si monta una card     l'esempio minimo, e cosa passare DURANTE il loading
Come si monta un grafico   quale seriesType per quale forma di dato
Cosa NON si costruisce     l'elenco esplicito delle cose che esistono e vanno riusate
```

**L'inventario verificato dal coordinatore** (rifallo, non fidarti):

| primitiva | percorso | note |
|---|---|---|
| `RiskMetricCard` | `ui/display/` | `@container`, doppia etichetta, slot `submetrics` e `sparkline` |
| `KpiMetricBar` | `ui/display/` | barra etichettata; **clampa i non-finiti a 0** |
| `KpiDivergingFlowBar` | `ui/display/` | barra divergente |
| `LineChart` | `components/charts/` | ⚠️ **solo serie storiche, asse categoriale sulle date.** `seriesType` vive su `RenderedSignal`, non è una prop: `line` · `area` · `bar` · `band`. **Nessuno scatter a X numerica** |
| `CorrelationHeatmap` | `components/risk/` | costruita da F |
| `Tooltip` | `ui/feedback/` | **ha già il riposizionamento** verso lo spazio disponibile |
| `SingleDatePicker` | `ui/date/` | 389 righe, giunzione digitato/calendario |
| `DocsLink` | `components/ui/` | ⚠️ **il percorso deve esistere**: nel round 1 sei link puntavano a `user/analysis/`, che non esiste |
| `formatPercent` | `utils/core/` | ⚠️ usa `toFixed`: **niente `toFixed` nuovi nelle superfici** |
| `currencyFormat` | `utils/currency/` | ⚠️ legge il locale del **browser**, non quello dell'app → `TODO_FUTURI` |

### 2.2 Esporre `seriesType: 'scatter'` in `LineChart`

**L'unico vuoto vero.** Oggi `LineChart:399` usa `type: 'scatter'` **internamente**, per la
sovrapposizione delle modifiche pendenti, e non è raggiungibile da un chiamante.

Serve a **S3**, per lo scatter rischio-rendimento — l'unica delle sette rappresentazioni del
design con un costo backend non marginale, e quindi quella che meno può permettersi di trovare
anche il frontend da costruire.

### 2.3 La disposizione delle card

`KpiSection:231` usa `grid grid-cols-1 md:grid-cols-3`. **Cinque superfici dovranno disporre
delle card, e se ognuna sceglie la propria griglia divergono.**

Decidi tu la forma — un componente, una classe documentata, o una riga in `PRIMITIVE.md` —
**ma decidila una volta**. È esattamente la deriva che la tua intestazione denunciava:
*«la vecchia griglia saltava `1 → sm:2 → xl:5` senza nulla in mezzo»*.

---

## 3. Perimetro

**Possiedi:**
```
frontend/src/lib/components/ui/display/*          le tre primitive e i loro test
frontend/src/lib/components/charts/LineChart.svelte    solo per esporre scatter
implementation_2/PRIMITIVE.md                     nuovo
```

**Non toccare — sono di altri mandati:**
```
🔴 frontend/src/lib/components/risk/levels/L1*.svelte    → S1 (E)
🔴 frontend/src/lib/components/risk/levels/L2*.svelte    → S2
🔴 frontend/src/lib/components/risk/levels/L3*.svelte    → S3
🔴 frontend/src/lib/components/risk/levels/l4/*          → S4
🔴 frontend/src/lib/components/risk/AssetSetRiskPanel.svelte → S5
🔴 levelHelpers.ts e RiskLevelsPanel.svelte              → scrittore unico: E
🔴 i18n/*.json                                           → ciascuno nel proprio namespace
```

> ⚠️ **Questo vincolo ha una conseguenza che devi accettare**: **non puoi dimostrare che la
> card è adottabile montandola in un livello**, perché i livelli sono di altri. La prova che
> `PRIMITIVE.md` funziona **sarà S1 che adotta la card senza farti domande**. Se S1 deve
> chiedere, il documento non era abbastanza.
>
> 📌 Puoi invece dimostrarlo in un **test** o in un esempio dentro `PRIMITIVE.md`: quello è
> tuo, e vale come prova che il montaggio compila e rende.

**Corsia**: `--test-port 6152`, `--data-dir /tmp/librefolio-r2-f2`. Il coordinatore tiene un
server di review su **6150** con la cartella dati predefinita: non usarla.

---

## 4. Primo deliverable: **analisi, non codice**

1. **Verifica l'inventario di §2.1**: ogni riga è vera? Ne manca qualcuna? Il coordinatore l'ha
   costruito con `grep` e `ls`, che trovano ciò che si chiama come ci si aspetta.
2. `LineChart`: esporre `scatter` è una riga o tocca l'asse, la legenda, il tooltip? **Misura.**
3. La griglia: componente o classe documentata? **Argomenta la scelta**, non solo il risultato.
4. Cosa mettere in `PRIMITIVE.md` che **non** sia già nell'intestazione della card — e cosa
   spostare fuori da lì perché sia trovabile.
5. I passi, con la verifica di ciascuno.

⚠️ **Non scrivere codice prima che l'analisi sia rivista.**

---

## 5. Due avvertimenti che vengono dal round 1

> **Non fidarti di questo documento.** Ne ho già corretto un'assunzione mentre lo scrivevo —
> il piano diceva *«rendere la card adottabile»* e la card era già adottabile. **Le altre
> misure qui dentro possono avere lo stesso difetto.** Se divergono, dillo subito.

> **Aggiorna il piano dopo ogni passo.** Nel round 1 i file `*-esecuzione.md` sono risultati
> **gli unici otto file su dieci alberi a esistere solo sul disco**, fuori da ogni oggetto git —
> perché il piano si aggiorna *dopo* il passo, e nessun checkpoint automatico lo contiene mai.

---

## 6. Come si misura la riuscita di F2

**Non dal codice che scrivi.** Da questo, fra due mandati:

```
S1 adotta RiskMetricCard senza chiedere nulla a F2.
S3 monta lo scatter senza costruire un grafico nuovo.
Nessuna superficie introduce un toFixed, un date picker o un popover nuovo.
```

**È l'unico mandato del round 2 il cui risultato si vede nel lavoro di qualcun altro.**
