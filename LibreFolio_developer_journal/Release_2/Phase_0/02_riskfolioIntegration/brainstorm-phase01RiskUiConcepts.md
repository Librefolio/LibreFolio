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
│  RISK SNAPSHOT                                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐    │
│  │ VOLAT.    │ │ MAX DD    │ │ SHARPE    │ │ VaR 95% 1M│ │ DIVERSIF. │    │
│  │  14.2%    │ │ -23.1%    │ │  0.87     │ │ -€2,410   │ │  ●●●○○ 3/5 │    │
│  │ ▁▂▃▅▇ ann.│ │ ▔▔▁▁▂ und.│ │ ▂▃▃▄▅ roll│ │  ~4.4% NAV│ │ corr med. │    │
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

- **Fa notare:** una fotografia unica "quanto è rischioso il mio portafoglio *ora*",
  con la stessa lente temporale che l'utente usa già per le performance.
- **Dove:** Dashboard (`dashboard/main.png` → aggiungere 4ª tab). Stesso pattern
  replicato in **Broker Detail** (`brokers/detail.png`), scoped al broker.
- 💰💰 ⭐⭐⭐⭐⭐ — è il contenitore che dà casa a tutti gli altri concept.

---

## Concept B — Asset Detail: 2ª tab chart "Projections / Risk"

Nell'Asset Detail il blocco grafico oggi ha il toggle linea/candela in alto a
sinistra (`assets/detail-signals-macd.png`). Aggiungiamo un **2° tab** al blocco
chart, come già previsto per il "Rendimento Rolling" in roadmap.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ┌ Price ┐ ┌ Projections ┐  ◀ nuova tab                        ⚙ ✎ 📏    │
│  └───────┘ └─────────────┘                                                 │
│                                                                            │
│   Monte Carlo — 10,000 paths · GBM · horizon 5y                           │
│   €90k ┤                                          ..········  P95         │
│        │                                 ....·····▓▓▓▓▓▓▓▓▓▓             │
│   €60k ┤                        ...·····▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  P50 (median)  │
│        │              ...··▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                  │
│   €30k ┤ ●───────●▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░  P5              │
│        │   storico    ┊ oggi                                              │
│    €0k ┼───────────────┼──────────────────────────────────────           │
│        2023           2026                 2028              2031          │
│                                                                            │
│   ┌ P(target €50k) ┐ ┌ Expected CAGR ┐ ┌ Worst 5% terminal ┐             │
│   │      68%       │ │     +7.1%      │ │      €21,300      │             │
│   └────────────────┘ └────────────────┘ └────────────────────┘           │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Fa notare:** il **ventaglio di futuri plausibili** invece di una singola
  previsione illusoria; la probabilità di raggiungere un obiettivo; il "sequence
  risk". Il P5 comunica il downside in modo viscerale.
- **Dove:** Asset Detail, blocco chart (scope asset o composizione mirata).
- **Riuso:** il cono P5/P50/P95 riusa il rendering a bande di **Bollinger**.
- 💰💰 ⭐⭐⭐⭐ — molto ingaggiante; attenzione ai disclaimer.

---

## Concept C — Rolling risk come SEGNALI (zero UI nuova)

Queste metriche vivono **dentro il grafico segnali esistente** come nuovi plugin
`category: "risk"`. L'utente le attiva dal pannello Signals già presente.

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
  - *Rolling Sharpe*: se il rendimento recente **valeva il rischio** o era fortuna.
- **Dove:** pannello Signals di Asset Detail (`assets/detail-signals.png`) e FX.
- 💰 ⭐⭐⭐⭐ — **il quick win**: riuso totale, solo plugin backend + `category`.

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
│   BND   │ ▁▁▁▁ │ ▁▁▁▁ │ ░░░░ │ ▁▁▁▁ │ ▒▒▒▒ │ ████ │          │
│                                                                │
│  ⚠ AAPL·MSFT·VWCE fortemente correlati (>0.6): concentrazione  │
│     nascosta dietro 3 ticker diversi. GLD/BND = veri diversif. │
└────────────────────────────────────────────────────────────────┘
```

- **Fa notare:** la **diversificazione reale vs illusoria**. "Hai 6 titoli ma 3 si
  muovono insieme → in pratica una sola scommessa". Rende visibile il rischio di
  concentrazione che i numeri di allocazione (donut in `dashboard/main.png`)
  nascondono.
- **Dove:** Risk tab Dashboard e Broker Detail (correlazione *interna* al broker).
- 💰💰 ⭐⭐⭐⭐⭐ — nuovo widget heatmap, ma insight fortissimo e memorabile.

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

- **Fa notare:** il rischio in **euro concreti e in emozioni** ("tolleri -€19k?"),
  non in percentuali astratte. Testa la tolleranza *prima* che accada davvero.
- **Dove:** Risk tab Dashboard/Broker.
- 💰💰 ⭐⭐⭐⭐ — costo = curare il dataset degli scenari (shock per asset class).

---

## Concept F — Risk Contribution Map (riuso della treemap esistente)

La treemap Positions (`dashboard/positions-performance-map.png`) oggi dimensiona
per valore. Aggiungiamo un toggle **"Risk contribution"**: dimensione/colore =
contributo marginale al rischio di portafoglio (MCTR).

```
┌───────────────────────────────────────────────────────────────┐
│ HOLDINGS MAP     view: [ Value ] [ Performance ] [▶ Risk ◀ ]   │
│                                                               │
│ ┌───────────────────────────┐ ┌─────────────┐ ┌───────────┐  │
│ │                           │ │             │ │           │  │
│ │        BTC                │ │   AAPL      │ │  MSFT     │  │
│ │   38% del RISCHIO         │ │  16% risk   │ │ 12% risk  │  │
│ │   (ma 22% del valore) ⚠   │ │             │ │           │  │
│ │                           │ ├─────────────┤ ├───────────┤  │
│ │                           │ │ VWCE 9%     │ │ GLD 3%    │  │
│ └───────────────────────────┘ └─────────────┘ └───────────┘  │
│                                                               │
│  ⚠ BTC pesa il 22% del valore ma il 38% del rischio totale.   │
└───────────────────────────────────────────────────────────────┘
```

- **Fa notare:** che **il rischio non è dove pensi**. La posizione più grande per
  valore spesso NON è quella che guida il rischio — e viceversa un piccolo asset
  volatile può dominare. Scollega "peso" da "rischio".
- **Dove:** riuso del componente treemap in Dashboard e Broker (terzo toggle
  accanto a Value/Performance già esistenti).
- 💰 ⭐⭐⭐⭐ — riuso di un componente esistente + un calcolo (MCTR) backend.

---

## Concept G — Efficient Frontier (avanzato / opzionale)

Scatter rischio-rendimento con la frontiera. **Solo qui** entra Riskfolio-Lib.

```
┌──────────────────────────────────────────────────────────────┐
│ EFFICIENT FRONTIER          [Advanced ⚠]   window:[3Y ▾]      │
│  return                                                       │
│  12% ┤                                   ╭───── frontiera     │
│      │                          ╭───────╯                     │
│   9% ┤                  ╭──────╯   ★ ottimo (max Sharpe)      │
│      │            ╭────╯                                       │
│   6% ┤     ◉ TU ─╯   ← sei sotto la frontiera:               │
│      │    (stesso rendimento, meno rischio possibile)         │
│   3% ┤ ╭─╯                                                    │
│      ┼──────┬──────┬──────┬──────┬──────► volatilità          │
│      8%    12%    16%    20%    24%                            │
│                                                               │
│  Potresti ottenere il tuo +6% con volatilità 12% invece di 17%│
└──────────────────────────────────────────────────────────────┘
```

- **Fa notare:** se stai prendendo **rischio non compensato** — "stesso rendimento
  atteso con meno volatilità è possibile". Il punto "TU" sotto la curva è un
  messaggio potentissimo.
- **⚠ Cautela:** soggetta a estimation error; mai imperativa; disclaimer obbligato.
  Collassata di default sotto un accordion "Advanced".
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
  tab. "Il tuo -1.17% è arrivato con che rischio?" — contestualizza il rendimento.
- **Dove:** striscia KPI Dashboard.
- 💰 ⭐⭐⭐ — economicissimo, buon "gancio" verso la Risk tab completa.

---

## Sintesi: priorità consigliata

| Concept | Archetipo | Riuso | 💰 | ⭐ | Ordine |
|---------|-----------|-------|----|----|--------|
| **C** Rolling risk = segnali | T | totale (SignalPlugin) | 💰 | ⭐⭐⭐⭐ | **1°** |
| **H** Risk KPI card | S | striscia KPI | 💰 | ⭐⭐⭐ | **2°** |
| **A** Risk tab (contenitore) | — | pattern tab Dashboard | 💰💰 | ⭐⭐⭐⭐⭐ | **3°** |
| **D** Correlation matrix | M | nuovo widget | 💰💰 | ⭐⭐⭐⭐⭐ | **4°** |
| **F** Risk contribution map | (treemap) | componente esistente | 💰 | ⭐⭐⭐⭐ | **5°** |
| **B** Monte Carlo cono | C/D | band-rendering Bollinger | 💰💰 | ⭐⭐⭐⭐ | **6°** |
| **E** Stress test | S | card | 💰💰 | ⭐⭐⭐⭐ | **7°** |
| **G** Efficient frontier | F | Riskfolio-Lib | 💰💰💰 | ⭐⭐⭐ | **opz.** |

Il filo conduttore: **massimizzare il riuso** (concept C, F, H, e il cono di B
riusano infrastruttura esistente) e introdurre widget nuovi solo dove l'insight lo
giustifica (D correlazione, B/E proiezioni).

→ Razionale architetturale: [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md)
