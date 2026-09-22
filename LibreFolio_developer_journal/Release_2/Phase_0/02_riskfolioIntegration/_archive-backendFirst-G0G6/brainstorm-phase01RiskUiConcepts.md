# Brainstorming — Concept UI per la Risk Analysis (con ASCII art)

> Modalità brainstorming/fantasiosa. Ogni concept ha: mockup ASCII, **cosa fa
> notare all'utente**, dove va, costo/valore. Le proporzioni ASCII sono
> indicative — servono a farsi un'idea, non sono pixel-perfect.
>
> Riferimenti reali negli screenshot `mkdocs_src/docs/gallery/desktop/en/light/`.

Legenda costo/valore: 💰 = costo impl. · ⭐ = valore percepito utente.

---

## Concept A — "Risk tab" nella Dashboard (il contenitore madre)

Nuova tab **Risk** accanto a Overview / Positions / Transactions. Eredita i filtri
in alto (periodo, valuta, broker) → gratis diventano finestra di stima e scope.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1W 1M 3M 6M [2Y] 5Y  All  Custom   Currency [EUR ▾]  [All brokers ▾] ⟳    │
├────────────┬────────────┬──────────────┬───────────────────────────────────┤
│  Overview  │ Positions  │ Transactions │            ▛ Risk ▟  ◀ nuova      │
├────────────┴────────────┴──────────────┴───────────────────────────────────┤
│                                                                            │
│  RISK SNAPSHOT   ·  modalità: Storico reale · finestra 2Y · EUR · copertura 97%│
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐    │
│  │ VOLAT.  ⓘ │ │ MAX DD  ⓘ │ │ SHARPE  ⓘ │ │ VaR 95% 1M│ │ CORR MEDIA│    │
│  │  14.2%    │ │ -23.1%    │ │  0.87     │ │ -€2,410 ⓘ │ │  0.42  ⓘ  │    │
│  │ ann.√A obs│ │ 41gg sotto│ │ rf=0 dich.│ │ hist.sim. │ │ n=642 cop.│    │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘    │
│                                                                            │
│  ┌─────────────────────────────┐  ┌────────────────────────────────────┐  │
│  │ CORRELATION MATRIX          │  │ MONTE CARLO — 10y projection       │  │
│  │  (Concept D)                │  │  (Concept B / cono)                │  │
│  └─────────────────────────────┘  └────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ STRESS TEST scenarios (Concept E)                                    │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Fa notare:** una fotografia unica "quanto è stato rischioso il portafoglio nel
  periodo osservato", con la stessa lente temporale usata per le performance.
- **Dove:** Dashboard (`dashboard/main.png` → aggiungere 4ª tab). Stesso pattern
  replicato in **Broker Detail** (`brokers/detail.png`), scoped al broker (con
  etichetta "rischio interno al broker", non rischio complessivo).
- **Guardrail:** ogni card porta finestra/valuta/copertura e un'icona ⓘ verso la
  nota metodologica. **Nessun punteggio sintetico** basso/medio/alto o "3/5": si
  mostrano KPI espliciti e scomponibili (review §16). "Corr media" è la media
  delle correlazioni a coppie osservate, con `n` e copertura, non un voto.
- **Nota annualizzazione (review-3 §2.1):** `ann.√A` = annualizzazione con **fattore
  osservato** `A = oss.incluse × 365 / giorni-calendario`, non un `√365` fisso.
- 💰💰 ⭐⭐⭐⭐⭐ — è il contenitore che dà casa a tutti gli altri concept.

---

## Concept B — Asset Detail: 2ª tab chart "Risk & Scenarios"

Nell'Asset Detail il blocco grafico oggi ha il toggle linea/candela in alto a
sinistra (`assets/detail-signals-macd.png`). Aggiungiamo un **2° tab** al blocco
chart, come già previsto per il "Rendimento Rolling" in roadmap. Il nome
**"Risk & Scenarios"** è preferito a "Projections", troppo assertivo per output
simulati (review §12).

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ┌ Price ┐ ┌ Risk & Scenarios ┐  ◀ nuova tab                   ⚙ ✎ 📏    │
│  └───────┘ └──────────────────┘                                           │
│                                                                            │
│   Monte Carlo — SIMULATO (non previsione) · GBM · 10.000 path · seed 12345 │
│   drift & σ stimati su 2Y storico · orizzonte 5y · costi/flussi: nessuno    │
│   €90k ┤                                          ..········  P95         │
│        │                                 ....·····▓▓▓▓▓▓▓▓▓▓             │
│   €60k ┤                        ...·····▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  P50 (mediana) │
│        │              ...··▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                  │
│   €30k ┤ ●───────●▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░  P5              │
│        │   storico    ┊ oggi                                              │
│    €0k ┼───────────────┼──────────────────────────────────────           │
│        2023           2026                 2028              2031          │
│                                                                            │
│   ┌ % path ≥ €50k ⓘ ┐ ┌ CAGR mediano  ┐ ┌ P5 valore terminale ┐         │
│   │  68% (simulato) │ │  +7.1% (sim.)  │ │      €21,300         │         │
│   └─────────────────┘ └────────────────┘ └──────────────────────┘        │
│   ⚠ % simulata sotto il modello GBM, non probabilità oggettiva del futuro. │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Fa notare:** il **ventaglio di esiti simulati** sotto un modello dichiarato,
  invece di una singola previsione illusoria; il P5 comunica il downside; la
  sensibilità alle ipotesi. Tutto etichettato "simulato".
- **Dove:** Asset Detail, blocco chart (scope asset o composizione mirata).
- **Riuso:** il cono P5/P50/P95 riusa il rendering a bande di **Bollinger**.
- **Guardrail (review §12):** modello/processo/drift/σ/seed/costi/ribilanciamento
  visibili; percentili non certezze; la "% path ≥ target" è quota **simulata**,
  non probabilità del futuro; prevedere scenari prudente/storico/ottimistico e
  sensitivity. Priorità **bassa** (dopo drawdown/correlazione/contributo/stress).
- 💰💰 ⭐⭐⭐ — ingaggiante ma massimo rischio di falsa precisione.

---

## Concept C — Rolling risk sul RENDERER dei segnali (riuso del renderer, non del dominio)

Queste metriche riusano il **renderer** del grafico segnali (`backendRenderer.ts`,
`LineChart`). **Pivot review-4:** le metriche rolling **asset-scoped** entrano nel
**`SignalPlugin`** esistente con piccole estensioni — non passano da `RiskAnalytic`.
Drawdown, rolling vol e rolling return sono price-only (fattibili subito); lo Sharpe
aggiunge solo un **param** risk-free; il beta richiede uno **slot serie secondaria**
(unica vera estensione di contratto). Solo lo scope portafoglio/multi-asset resta
`RiskAnalytic` (vedi analisi §4).

```
   Prezzo + segnali (asse primario)              Drawdown underwater (asse sec.)
   ┌──────────────────────────────┐              ┌──────────────────────────────┐
   │        ╱╲      ╱╲╱╲           │    0% ───────┤▔▔▔╲    ╱▔▔▔▔╲      ╱▔▔▔▔     │
   │   ╱╲  ╱  ╲╱╲ ╱    ╲  ╱╲       │              │    ╲  ╱      ╲    ╱          │
   │  ╱  ╲╱      ╲       ╲╱  ╲     │  -10% ───────┤     ╲╱        ╲  ╱           │
   │ ╱                        ╲    │              │                ╲╱  ← -18%    │
   └──────────────────────────────┘  -20% ───────┴──────────────────────────────┘

   Rolling Volatility 30d           Rolling Sharpe 90d
   ┌──────────────────────────────┐ ┌──────────────────────────────┐
   │ high ┤    ╱╲          ╱╲      │ │ +2 ┤        ╱▔▔╲              │
   │      ┤   ╱  ╲___     ╱  ╲     │ │  0 ┼───╲___╱────╲___╱▔╲──────│
   │ low  ┤__╱      ╲____╱    ╲__  │ │ -1 ┤ ╲_╱            ╲_╱       │
   └──────────────────────────────┘ └──────────────────────────────┘
```

- **Fa notare:**
  - *Drawdown underwater*: quanto è stata profonda e **quanto è durata** la
    peggiore discesa (tempo di recupero).
  - *Rolling volatility*: i **cambi di regime** — quando l'asset è diventato più
    nervoso.
  - *Rolling Sharpe*: come si è mosso nel tempo il rapporto tra rendimento
    eccedente storico e variabilità (rf dichiarato) — **non** "fortuna vs bravura".
- **Dove:** pannello Signals / renderer condiviso di Asset Detail
  (`assets/detail-signals.png`) e FX.
- 💰 ⭐⭐⭐⭐ — **quick win**: riuso del renderer. Le rolling asset-scoped entrano nei
  `SignalPlugin` (estensione minore `SignalCategory`; Sharpe = param; beta = slot
  serie secondaria). Solo il rischio di portafoglio/multi-asset → `RiskAnalytic`.

---

## Concept D — Correlation Matrix (l'"aha moment" della diversificazione)

Heatmap NxN degli asset (o dei broker, o per categoria). Colore = correlazione.

```
┌────────────────────────────────────────────────────────────────┐
│ CORRELATION MATRIX   scope:[Portfolio ▾]  window:[1Y ▾]  by:[Asset ▾]│
│                                                                │
│           AAPL   MSFT   BTC    VWCE   GLD    BND               │
│   AAPL  │ ████ │ ▓▓▓▓ │ ▒▒▒▒ │ ▓▓▓▓ │ ░░░░ │ ▁▁▁▁ │  █ 1.0   │
│   MSFT  │ ▓▓▓▓ │ ████ │ ▒▒▒▒ │ ▓▓▓▓ │ ░░░░ │ ▁▁▁▁ │  ▓ 0.6   │
│   BTC   │ ▒▒▒▒ │ ▒▒▒▒ │ ████ │ ▒▒▒▒ │ ░░░░ │ ░░░░ │  ▒ 0.3   │
│   VWCE  │ ▓▓▓▓ │ ▓▓▓▓ │ ▒▒▒▒ │ ████ │ ░░░░ │ ▁▁▁▁ │  ░ 0.0   │
│   GLD   │ ░░░░ │ ░░░░ │ ░░░░ │ ░░░░ │ ████ │ ▒▒▒▒ │  ▁ <0    │
│   BND   │ ▁▁▁▁ │ ▁▁▁▁ │ ░░░░ │ ▁▁▁▁ │ ▒▒▒▒ │ ████ │  ▨ n<20  │
│   valuta: EUR (post-conversione) · intersezione date · n=642 · cop. 95%   │
│                                                                │
│  Nel periodo osservato AAPL·MSFT·VWCE si sono mossi insieme    │
│  (corr >0.6): possibile concentrazione dietro 3 ticker diversi.│
└────────────────────────────────────────────────────────────────┘
```

- **Fa notare:** quanto, **nel campione osservato**, gli asset si sono mossi
  insieme — utile per leggere la diversificazione oltre i pesi del donut
  (`dashboard/main.png`). Descrive l'osservazione, **non** afferma verità
  strutturali («una sola scommessa»): la correlazione è instabile e campionaria.
- **Regole dati (contratto §5):** correlazione calcolata **dopo** conversione in
  valuta; intersezione delle date; celle con `n<min` grigie (▨); `n`/copertura
  sempre esposti; possibile correlazione **rolling** per mostrarne l'instabilità.
- **Dove:** Risk tab Dashboard e Broker Detail (correlazione *interna* al broker,
  etichettata come parziale).
- 💰💰 ⭐⭐⭐⭐⭐ — nuovo widget heatmap; dipende da `AssetReturnSeries` (§ analisi).

> **Nota (review-4):** i blocchi **D-bis** e **D-ter** qui sotto **non** sono nuovi
> concept numerati: sono **varianti di scope** dello stesso Concept D (un solo
> contratto correlazione riusato). I concept restano **9** (A–I).

### D-bis — Asset Global: casa primaria della correlazione (tab `Assets | Correlation`)

Correlazione come **2ª tab** di Asset Global. Riusa `PageToolbar`+`TabBar` (Asset
Global oggi non ha tab → piccola estensione). Il **filtro broker** costruisce solo
l'**insieme** di asset (nessun peso); l'utente può **aggiungere asset a mano**.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1W 1M 3M 6M [1Y] 5Y All   Currency [EUR ▾]           [+ Aggiungi asset]   │
├──────────────┬───────────────────────────────────────────────────────────┤
│    Assets    │           ▛ Correlation ▟  ◀ nuova tab                     │
├──────────────┴───────────────────────────────────────────────────────────┤
│  Set di asset:  [Tutti ▾] [Broker: Directa ▾]  ← costruisce solo il SET   │
│  chip:  (AAPL ✕)(MSFT ✕)(BTC ✕)(VWCE ✕)(GLD ✕)(BND ✕)   ⟵ aggiunta manuale│
│                                                                            │
│           AAPL   MSFT   BTC    VWCE   GLD    BND               █ 1.0       │
│   AAPL  │ ████ │ ▓▓▓▓ │ ▒▒▒▒ │ ▓▓▓▓ │ ░░░░ │ ▁▁▁▁ │           ▓ 0.6       │
│   MSFT  │ ▓▓▓▓ │ ████ │ ▒▒▒▒ │ ▓▓▓▓ │ ░░░░ │ ▁▁▁▁ │           ▒ 0.3       │
│   BTC   │ ▒▒▒▒ │ ▒▒▒▒ │ ████ │ ▒▒▒▒ │ ░░░░ │ ░░░░ │           ░ 0.0       │
│   …                                                            ▨ n<20      │
│  valuta EUR (post-conv.) · intersezione date · n=642 · cop.95% · SET=6     │
│  ⚠ il broker filtra solo QUALI asset entrano: nessun peso/quantità usato.  │
└──────────────────────────────────────────────────────────────────────────┘
```

### D-ter — Asset Detail: correlazione centrata sull'asset corrente

Nell'Asset Detail la correlazione è **asset-centrica**: una lista «questo asset vs
gli altri», non una matrice NxN. Stesso contratto backend, output a lista.

```
┌──────────────────────────────────────────────────────────────┐
│ CORRELAZIONE — AAPL vs …    window:[1Y ▾]  EUR  n=642 cop.95% │
│   MSFT   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓  0.71   (si muovono spesso insieme)   │
│   VWCE   ▓▓▓▓▓▓▓▓▓▓▓▓    0.64                                 │
│   BTC    ▒▒▒▒▒▒          0.29                                 │
│   GLD    ░░              0.04                                 │
│   BND    ▁               -0.08  (tende a compensare)          │
│   ⓘ osservato nel periodo · non è una verità strutturale     │
└──────────────────────────────────────────────────────────────┘
```

---

## Concept E — Stress Test: "e se tornasse il 2008?"

Card di scenari storici applicati alla composizione **attuale**, in € reali.

```
┌──────────────────────────────────────────────────────────────────────┐
│ STRESS TEST — impatto sul portafoglio attuale (NAV €54,293)          │
│                                                                      │
│ ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐│
│ │ 📉 Lehman 2008     │ │ 🦠 COVID Mar-2020  │ │ 📈 Rates +200bps   ││
│ │                    │ │                    │ │                    ││
│ │  -€19,050          │ │  -€11,720          │ │  -€3,180           ││
│ │  ▼ -35.1% NAV      │ │  ▼ -21.6% NAV      │ │  ▼ -5.9% NAV       ││
│ │  recovery ~18mesi  │ │  recovery ~5mesi   │ │  bond -8% eq flat  ││
│ │  ███████████░░░░░  │ │  ███████░░░░░░░░░  │ │  ██░░░░░░░░░░░░░░░  ││
│ └────────────────────┘ └────────────────────┘ └────────────────────┘│
│                                                                      │
│  Peggior scenario: Lehman 2008 → tolleri una perdita di €19k?        │
└──────────────────────────────────────────────────────────────────────┘
```

- **Fa notare:** il rischio in **euro concreti** ("tolleri -€19k?"), non in
  percentuali astratte. Testa la tolleranza *prima* che accada.
- **Tre famiglie (contratto §6.10):** *historical replay* (periodo storico reale
  applicato alla composizione), *hypothetical shock* (shock a categorie), *factor
  shock* (azionario/tassi/spread/FX/inflazione). Ogni scenario **mostra le proprie
  assunzioni**: «tassi +200bps → bond −8%» è un **input dello scenario**, non una
  legge finanziaria universale.
- **Scope € (review-4):** questo è lo **stress economico di portafoglio** →
  **Dashboard/Broker**, dove esistono pesi/valorizzazione (`mode` dichiarato). La
  **stessa definizione di scenario** è riusata con output diverso per scope (E-bis).
- 💰💰 ⭐⭐⭐⭐ — trasparente e auditabile; costo = curare il dataset degli scenari.
  Più comprensibile del Monte Carlo → precede R8 in roadmap.

### E-bis — Stress percentuale multi-asset (Asset Global / Asset Detail)

Stessa definizione di scenario, ma **senza pesi**: dove non c'è composizione (Asset
Global, Asset Detail) l'impatto è **percentuale**, di confronto — non in €.

```
┌──────────────────────────────────────────────────────────────┐
│ STRESS % — scenario: [📉 Lehman 2008 ▾]   (nessun peso: %)    │
│   BTC     ▼ -58%   ████████████████████                      │
│   AAPL    ▼ -41%   ██████████████                            │
│   VWCE    ▼ -37%   ████████████                              │
│   MSFT    ▼ -33%   ███████████                               │
│   GLD     ▲  +6%          ██  (bene rifugio nello scenario)  │
│   BND     ▼  -8%   ██▏                                        │
│   ⓘ stesso scenario del Concept E · qui % per confronto asset │
└──────────────────────────────────────────────────────────────┘
```

- **Fa notare:** *quali asset* soffrirebbero di più in % nello **stesso** scenario,
  senza mescolare i pesi — utile in Asset Global/Detail dove non c'è portafoglio.
- **Riuso:** stessa definizione di scenario di Concept E; barre → primitive `DB`.
- 💰 ⭐⭐⭐ — variante di scope (non un concept nuovo).

---

## Concept F — Risk Contribution (grafico a barre divergente riusabile)

> **Revisione (review-2 §5):** la **treemap è scartata** come visualizzazione
> primaria del contributo al rischio. Il PCTR **può essere negativo** (asset che
> diversifica) e un'area negativa non ha rappresentazione naturale in una treemap
> (l'`ExposureTreemap` dimensiona per `current_value`, sempre ≥ 0). Si usa un
> **grafico a barre divergente** con asse a zero, coerente con quello già usato da
> LibreFolio per le performance.

Contributo al rischio come **barre orizzontali divergenti**: diversificazione a
sinistra dello zero, contributo positivo a destra. Definizioni formali
MCTR/CCTR/PCTR nel contratto §6.7.

```
┌────────────────────────────────────────────────────────────────┐
│ RISK CONTRIBUTION      base: σ_p · finestra 1Y · EUR · PCTR     │
│                                                                │
│  Diversificazione ◀────────────── 0 ──────────────▶ Contributo │
│                                    │                           │
│  Oro (GLD)              ███◀       │                    −2%    │
│  MSFT                              │████████            12%    │
│  AAPL                              │██████████          16%    │
│  ETF World (VWCE)                  │███████████████     22%    │
│  BTC                               │████████████████████ 38%   │
│                                    │                           │
│  ▸ ordina per: [PCTR ▾]   ▸ mostra: [◍ peso valore vs PCTR]    │
│  Σ PCTR = 100% (norm.) · cash/vol-nulla = 0% · GLD<0 = copre   │
│  ⚠ BTC: 22% del valore ma 38% del rischio (PCTR) nel periodo.  │
└────────────────────────────────────────────────────────────────┘
```

- **Fa notare:** che **il rischio non è dove pensi**. La barra più lunga a destra
  spesso NON è la posizione più grande per valore; un piccolo asset volatile può
  dominare. Le barre a **sinistra dello zero** rendono visibile la
  **diversificazione** (contributi negativi), impossibile da mostrare in treemap.
- **Semantica (contratto §6.7):** «X% del rischio» = **PCTR** su base volatilità
  `σ_p`, dichiarata. Casi limite gestiti: cash/vol-nulla → 0%; contributi
  **negativi** mostrati a sinistra, non troncati; somma normalizzata a 100%; asset
  con storia insufficiente esclusi (elencati); tooltip metodologico con finestra,
  valuta, copertura, base di rischio.
- **Riuso frontend (evidenza codice):** LibreFolio ha **già** un grafico a barre
  divergente — `PerformanceChart.svelte` («Diverging stacked horizontal bar
  chart», asse a zero via `markLine{xAxis:0}`, colori sign-based). Inoltre il
  renderer dei segnali `backendRenderer.renderBackendSignalResult` supporta **già**
  serie di tipo `bar` (`buildBarSeries` in `lineChartHelpers.ts`). Riuso minimo
  sensato: la **primitive di barra divergente** (asse a zero + colori pos/neg), con
  un **adapter** per il dominio PCTR — **non** riusare `PerformanceChart` così com'è
  (è stacked-multi-componente, specifico delle performance). Vedi analisi §6.
- **Dove:** Risk tab (Dashboard e Broker), accanto a "peso economico".
- 💰 ⭐⭐⭐⭐ — riuso primitive + calcolo; dipende da `AssetReturnSeries` + pesi.
  **Alto valore informativo → precede il Monte Carlo** (review §9).

---

## Concept G — Efficient Frontier (avanzato / opzionale)

Scatter rischio-rendimento con la frontiera. **Solo qui** entra Riskfolio-Lib.

```
┌──────────────────────────────────────────────────────────────┐
│ EFFICIENT FRONTIER          [Advanced ⚠]   window:[3Y ▾]      │
│  return (stimato)                                            │
│  12% ┤                                   ╭───── frontiera     │
│      │                          ╭───────╯      (stimata)      │
│   9% ┤                  ╭──────╯   ★ max Sharpe stimato       │
│      │            ╭────╯             nel campione             │
│   6% ┤     ◉ TU ─╯                                            │
│      │                                                        │
│   3% ┤ ╭─╯                                                    │
│      ┼──────┬──────┬──────┬──────┬──────► volatilità (stim.)  │
│      8%    12%    16%    20%    24%                            │
│                                                               │
│  Nel modello stimato sulla finestra selezionata esiste una    │
│  combinazione con rendimento atteso simile e volatilità       │
│  stimata inferiore. Dipende da campione, stime e vincoli.     │
└──────────────────────────────────────────────────────────────┘
```

- **Fa notare:** che, **nel modello stimato sulla finestra selezionata**, potrebbe
  esistere una combinazione con rendimento atteso simile e **volatilità stimata
  inferiore**. Nessuna affermazione di ottimalità certa.
- **⚠ Cautela (review-2 §10):** niente wording assertivo («ottimo», «potresti
  ottenere lo stesso rendimento con meno rischio»). Il risultato dipende da
  **campione · finestra · stima dei rendimenti · matrice di covarianza · vincoli ·
  modello · estimation error**. Mai imperativa; disclaimer obbligato; collassata di
  default sotto un accordion "Advanced".
- **Dove:** in fondo alla Risk tab.
- 💰💰💰 ⭐⭐⭐ — introduce Riskfolio-Lib + cvxpy; valore alto ma per utenti evoluti.

---

## Concept H — Risk KPI card nella striscia superiore della Dashboard

Micro-intervento: una 4ª card accanto a Net Worth / Gain·Loss / Weighted ROI
(`dashboard/allocation-charts.png`), sempre visibile senza entrare in una tab.

```
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐
│ NET WORTH     │ │ GAIN / LOSS   │ │ WEIGHTED ROI  │ │ RISK          ◀ new│
│ EUR 54,293    │ │ -EUR 641      │ │ -1.17%        │ │ Vol 14.2% ▁▂▃▅▇   │
│ Cash 29,407   │ │ (-0.01%)      │ │ TWRR -3.68%   │ │ MaxDD -23% Shp .87│
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────────┘
```

- **Fa notare:** tiene il rischio **sempre nel campo visivo**, non nascosto in una
  tab. "Il tuo -1.17% è arrivato con che variabilità?" — contestualizza il
  rendimento (che qui è già TWRR, neutro rispetto ai flussi).
- **Dove:** striscia KPI Dashboard.
- 💰 ⭐⭐⭐ — economico, buon "gancio" verso la Risk tab completa.

---

## Concept I — Confronta con: risk-free sintetico vs asset reale (review-2 §8)

Una **UI unica di confronto** con selezione della modalità, ma con **metriche e
spiegazioni semanticamente distinte**. Il backend tiene contratti separati
(`RiskFreeReference` vs `ComparisonBenchmark`), **mai** un unico campo ambiguo.

```
┌──────────────────────────────────────────────────────────────┐
│ CONFRONTA CON:                                               │
│  (●) Baseline risk-free sintetica                            │
│      Tasso annuo: [ 0,00 % ]   Valuta: EUR                   │
│      → crescita giornaliera deterministica, varianza NULLA   │
│  ( ) Asset reale                                             │
│      Cerca asset / indice / obbligazione / FX: [ AssetSearch▾]│
│──────────────────────────────────────────────────────────────│
│  ▸ se RISK-FREE  → Sharpe, rendimento eccedente              │
│  ▸ se ASSET      → active return, tracking error, IR,         │
│                    correlazione, beta, drawdown comparato     │
│                                                              │
│  serie giornaliera · stessa valuta target · intersezione ·   │
│  n=612 · copertura 96% · return_basis: price_only ⚠ cedole   │
└──────────────────────────────────────────────────────────────┘
```

Interpretazione guidata dal **tipo** di asset (cambia la spiegazione, non il
renderer):

```
BTP / obbligazione → "vs questa alternativa obbligazionaria" (NON risk-free;
                      price-only ⚠ cedole escluse → confronto incompleto)
ETF World / S&P500 → "vs questa alternativa azionaria / benchmark di mercato"
                      (distingui mandato vs semplice alternativa)
Coppia FX          → fattore/esposizione valutaria: "Valore in EUR di 1 USD"
                      (direzione esplicita; NON risk-free, NON benchmark default)
```

- **Fa notare:** la differenza tra «crescere più di un deposito a rendimento fisso»
  (risk-free) e «battere/seguire un'alternativa reale» (benchmark). Evita il
  fraintendimento più comune: trattare un ETF o un BTP come se fosse "privo di
  rischio".
- **Formule (contratto §6.11):** `A_t = R_p − R_b`, `TE = σ(A_t)`,
  `IR = E[A_t]/σ(A_t)`, `β = Cov(R_p,R_b)/Var(R_b)`; risk-free giornaliero
  `r_{f,daily} = (1+r_{f,annual})^(1/365)−1`.
- **Riuso frontend (evidenza codice):** l'asset picker esiste
  (`AssetSearchAutocomplete.svelte`) e un confronto asset-vs-asset esiste già come
  segnale (`AssetComparisonSignal.ts`, param `assetId`; dropdown "Comparison" in
  `ChartSignalsSection.svelte`). La baseline risk-free sintetica è **nuova**
  (deterministica, varianza nulla) → contratto `RiskFreeReference`.
- **Dove:** Risk tab (contenitore condiviso) + Asset Detail.
- 💰💰 ⭐⭐⭐⭐ — riuso ricerca/confronto esistenti; il valore è nella **distinzione
  semantica**, non nel grafico.

---

## Information architecture della Risk tab (review §17)

La Risk tab **non** deve essere un accumulo di grafici ordinati per archetipo
tecnico (S/T/D/C/M/F sono utili al *rendering*, non alla comprensione). Deve
rispondere progressivamente a domande concrete dell'utente:

```
1. Quanto è stato instabile?            → Rolling volatility (C)
2. Qual è stata la perdita peggiore
   e quanto è durata?                   → Drawdown underwater (C)
3. Dove è concentrato il rischio?       → Risk contribution PCTR, barre (F)
4. Quanto è reale la diversificazione?  → Correlation matrix (D)
5. Rispetto a un'alternativa/risk-free? → Confronto risk-free vs asset (I)
6. Cosa accadrebbe sotto scenari
   espliciti?                           → Stress test (E)
7. (solo dopo) quali futuri sono
   simulabili sotto un modello?         → Monte Carlo (B)
```

L'ordine visivo della tab segue queste domande (storico e osservabile prima,
simulato dopo), non la complessità matematica. Il **confronto** (I) distingue
sempre risk-free sintetico da benchmark reale.

### Elemento trasversale — Banner qualità dati (§qualità dati, non un concept numerato)

Non è un concept a sé: è **infrastruttura riusabile** che compare in cima a qualunque
scheda quando la copertura prezzi non è uniforme (contratto §2.3). I concept numerati
restano **9** (A–I).

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⚠ Dati di prezzo incompleti                                                │
│                                                                            │
│ Alcuni asset non hanno una quotazione per tutti i giorni del periodo       │
│ selezionato. Per i punti mancanti è stato usato l'ultimo prezzo            │
│ disponibile. Le metriche potrebbero essere meno attendibili.               │
│                                                                            │
│    [ Mostra dettagli ]              [ ⟳ Sincronizza prezzi ]               │
└──────────────────────────────────────────────────────────────────────────┘

Dettaglio (espanso):
┌────────┬───────────────────────┬────────────────────┬────────────┬──────────────┐
│ Asset  │ Giorni senza nuovo pr.│ Punti con ult.prezzo│ Ultima quot│ Motivo       │
├────────┼───────────────────────┼────────────────────┼────────────┼──────────────┤
│ BTC    │ 3                     │ 3                  │ 2026-07-24 │ —            │
│ XYZ    │ tutti nel periodo     │ 0                  │ —          │ escluso: 0 pr│
└────────┴───────────────────────┴────────────────────┴────────────┴──────────────┘
```

- **Fa notare:** che il numero mostrato poggia su dati **parzialmente carried-forward**
  (warning ordinario) o su un campione **ridotto** perché un asset è stato escluso
  (warning grave, risultato parziale) — trasparenza sulla qualità della sorgente.
  La qualità considera **anche l'FX** carried-forward, non solo i prezzi (contratto §4).
- **Confine (review-4):** il pulsante **apre la modale di sync comune** già esistente
  (`PageSyncModal`, che gestisce **prezzi + FX** insieme) con gli asset e le coppie FX
  incomplete **preselezionati**; l'utente **avvia esplicitamente**. Al termine la
  pagina invalida le cache e ricalcola (pattern attuale). Il Risk Engine **non**
  scarica prezzi né corregge il DB (contratto §2.3). **Nessun** banner quando un
  giorno è escluso perché nessun asset ha una nuova quotazione (esclusione normale).

```
[ ⟳ Sincronizza dati ]  ──▶  MODALE COMUNE (PageSyncModal, riusata)
┌───────────────────────────────────────────────────────────┐
│  Sincronizza dati        periodo: 2024-01-02 → 2026-07-25  │
│  ┌───────────────────────────────────────────────────────┐│
│  │ ▣ Prezzi asset (preselezionati: BTC, XYZ)             ││
│  │ ▣ Tassi FX (preselezionati: USD→EUR)                  ││
│  └───────────────────────────────────────────────────────┘│
│  ⓘ avvio manuale · nessun auto-sync                        │
│                         [ Annulla ]   [ ▶ Avvia sync ]     │
└───────────────────────────────────────────────────────────┘
   dopo onsynced → invalidazione cache pagina → ricalcolo metriche
```

- 💰 ⭐⭐⭐⭐ — primitive singola riusata ovunque; alto valore di fiducia.

---

## Sintesi: priorità consigliata (allineata alla roadmap R0–R9 dell'analisi)

| Concept | Archetipo | Riuso | Dipende da | 💰 | ⭐ | Ordine |
|---------|-----------|-------|-----------|----|----|--------|
| **C** Rolling vol / drawdown | T | renderer segnali | contratto | 💰 | ⭐⭐⭐⭐ | **1°** (R2) |
| **H** Risk KPI card | S | striscia KPI | contratto | 💰 | ⭐⭐⭐ | **2°** (R3) |
| **A** Risk tab (contenitore) | — | pattern tab Dashboard | — | 💰💰 | ⭐⭐⭐⭐⭐ | **3°** |
| **D** Correlation matrix | M | nuovo widget | `AssetReturnSeries` | 💰💰 | ⭐⭐⭐⭐⭐ | **4°** (R4) |
| **F** Risk contribution PCTR | **barre divergenti** | primitive barra (`PerformanceChart`/`buildBarSeries`) | `AssetReturnSeries`+pesi | 💰 | ⭐⭐⭐⭐ | **5°** (R5) |
| **I** Confronto risk-free/asset | S/T | `AssetSearchAutocomplete`+`AssetComparisonSignal` | `AssetReturnSeries` | 💰💰 | ⭐⭐⭐⭐ | **6°** (R7) |
| **E** Stress test | S | card | scenari+contratto | 💰💰 | ⭐⭐⭐⭐ | **7°** (R6) |
| **B** Monte Carlo cono | C/D | band-rendering Bollinger | contratto+seed | 💰💰 | ⭐⭐⭐ | **8°** (R8) |
| **G** Efficient frontier | F | Riskfolio-Lib | tutto sopra | 💰💰💰 | ⭐⭐⭐ | **opz.** (R9) |

> ⚠️ Rispetto alla prima stesura: **il contributo al rischio (F) usa un grafico a
> barre divergente, non la treemap** (review-2 §5); **risk contribution (F) e
> stress test (E) precedono il Monte Carlo (B)** per valore informativo e
> auditabilità (review §9, §13). Aggiunto il **confronto (I)** con distinzione
> risk-free/benchmark (review-2 §8).

Il filo conduttore: **massimizzare il riuso** (C, F, H, I e il cono di B riusano
infrastruttura esistente), consumare le **serie canoniche** del motore, e
introdurre widget nuovi solo dove l'insight lo giustifica (D correlazione).

→ Fondamenta matematiche: [`contract-phase01RiskMetricsMathematical.md`](./contract-phase01RiskMetricsMathematical.md)
→ Razionale architetturale: [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md)
→ Revisione punto-per-punto: [`review-risk-analysis-feedback.md`](./review-risk-analysis-feedback.md)
