# 💰 Schede KPI

Le tre schede in cima alla Dashboard rispondono a colpo d'occhio a tre domande: **quanto ho guadagnato in questo periodo**, **quanto bene ha lavorato il mio denaro** e **quanto vale il mio portafoglio**. Seguono l'intervallo temporale e il filtro broker in cima alla pagina, e la pagina di un broker mostra le stesse schede solo per quel broker. L'icona **?** nell'angolo di una scheda apre la sua sezione qui sotto.

- 📉 **[Scheda 1 — P&L periodo](#card-1-period-pl)** — il denaro che i tuoi investimenti hanno prodotto nel periodo
- 📈 **[Scheda 2 — Rendimenti](#card-2-returns)** — i tuoi rendimenti in percentuale, e cosa ha fatto il tuo timing
- 💰 **[Scheda 3 — Patrimonio netto](#card-3-net-worth)** — quello che possiedi, e il tuo guadagno dall'inizio

!!! note "I broker condivisi contano per la tua quota"

    La Dashboard somma i broker che **possedi** con una quota superiore allo 0%, ciascuno in proporzione a quella quota: un proprietario al 50% vede metà del valore e del P&L del broker. I broker in cui sei editor o visualizzatore non sono conteggiati qui; la loro pagina li mostra, con i loro importi completi. Vedi [Condivisione dei broker](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Panoramica delle schede KPI">
</div>

---

## 📉 Scheda 1 — P&L periodo {: #card-1-period-pl }

Quanto denaro hanno prodotto i tuoi investimenti nel periodo selezionato? La scheda **P&L periodo** risponde, escludendo il denaro che hai spostato dentro o fuori tu stesso.

<div class="kpi-card-crop-container card-period-pnl">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda P&L periodo">
</div>

**Metriche mostrate**

- **P&L periodo** — il numero grande: $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Net flows}$, dove i flussi netti sono il capitale che hai spostato dentro o fuori → [P&L periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **La riga sotto di esso** — per esempio `+91,31 € (+16,36%)`: di quanto si è mosso il tuo P&L totale da ieri (pannello sottostante)
- **Variazione latente** — come si è mossa, nel periodo, la plusvalenza o minusvalenza latente delle tue posizioni, incluso l'effetto del tasso di cambio → [Valore contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Vendite** — la plusvalenza o minusvalenza realizzata delle vendite del periodo, rispetto al prezzo medio di carico (PMC) delle unità vendute → [prezzo medio di carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Dividendi e interessi** — dividendi, cedole e interessi P2P ricevuti → [Dividendo e interesse](../../financial-theory/instruments/transaction-types/dividend-interest.md)
- **Commissioni e imposte** — commissioni e imposte registrate come transazioni; passa il cursore sulla riga per vedere la ripartizione → [Commissione e imposta](../../financial-theory/instruments/transaction-types/fee.md)

**Come leggerla**

- **Verde è un guadagno, rosso una perdita** — e un deposito o un prelievo non è né l'uno né l'altra.
- **Le quattro righe spiegano il numero grande.** Ciò che non riescono a vedere, come asset che si spostano tra due tuoi broker nel primo o nell'ultimo giorno, finisce nel **Residuo Altro / di riconciliazione** della [vista Performance](positions.md#performance).
- **La barra più lunga** è la riga che ha mosso di più il tuo risultato.

??? info "📏 La riga sotto il numero grande — come viene calcolata"

    È la variazione del tuo P&L totale — il tuo guadagno o la tua perdita dall'inizio — da ieri a oggi, dove *oggi* è la data finale del periodo. La percentuale la confronta con il P&L totale di ieri, preso senza il suo segno:

    $$
    \Delta = \text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}} \qquad \text{percentage} = \frac{\Delta}{\left|\text{Total P}\&\text{L}_{\text{yesterday}}\right|} \times 100
    $$

    - **Il segno e il colore seguono la variazione**, anche quando il P&L totale è una perdita: da `-558,10 €` a `-466,79 €`, la riga mostra `+91,31 € (+16,36%)` — la tua perdita si è ridotta del 16,36%.
    - **Richiede due giorni di storico**; la percentuale è omessa quando il P&L totale di ieri è esattamente zero, e un giorno senza variazioni mostra `0,00%`.

### 💱 Variazione latente per valuta {: #unrealized-change-by-currency }

Passa il cursore su **Variazione latente** per suddividerla per la valuta in cui sono quotati i tuoi asset — qui con l'euro come valuta di visualizzazione:

| Riga | Cosa mostra |
|-----|---------------|
| 📈 **Asset in USD** | Cosa hanno fatto i tuoi asset in dollari *in dollari* — la loro variazione di prezzo — contati al tasso di cambio del giorno |
| 💱 **Tasso USD → EUR** | Cosa ha fatto il tasso di cambio su quanto hai pagato per acquistarli |
| ❔ **USD, non suddiviso** | Solo quando, nel primo o nell'ultimo giorno, alcuni di quegli asset non avevano prezzo, né tasso, o avevano un valore di acquisto incompleto: la loro variazione, in un unico blocco |

C'è una riga 📈 per ogni valuta, euro incluso, e una riga 💱 per ogni valuta diversa dalla tua valuta di visualizzazione; insieme, le righe sommano **esattamente** alla Variazione latente.

??? example "Un ETF statunitense su una dashboard in euro"

    Durante il periodo hai acquistato 10 unità per 400 €, quando valevano 500 USD. Alla fine del periodo valgono 550 USD, e 1 USD = 0,75 €. Il tooltip mostra:

    - 📈 **Asset in USD**: (550 − 500) × 0,75 = **+37,50 €** — il tuo ETF ha guadagnato il 10% in dollari;
    - 💱 **Tasso USD → EUR**: 500 × 0,75 − 400 = **−25,00 €** — il dollaro ha perso valore rispetto all'euro;
    - insieme, la **Variazione latente**: 550 × 0,75 − 400 = **+12,50 €**.

🔗 **Teoria**: [Variazione latente per valuta](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#unrealized-change-by-currency) — le formule dietro ogni riga

---

## 📈 Scheda 2 — Rendimenti {: #card-2-returns }

Quanto bene ha lavorato il tuo denaro, qualunque sia la dimensione del tuo portafoglio? La scheda **Rendimenti** risponde in percentuale, e il suo numero grande ti dice se il tuo timing ha aiutato.

<div class="kpi-card-crop-container card-returns">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda Rendimenti">
</div>

**Metriche mostrate**

- **Effetto timing** — il numero grande, in punti percentuali (pp): $\text{MWRR}_{\text{cumulative}} - \text{TWRR}$ → [Effetto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)
- **La percentuale sotto di esso** — per esempio `+0,35%`: la variazione odierna del tuo P&L totale, rispetto al patrimonio netto di ieri (pannello sottostante)
- **ROI** — il guadagno del periodo rispetto al capitale investito → [ROI semplice](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)
- **TWRR** — come si sono comportate le tue scelte di asset, indipendentemente dal timing dei tuoi depositi → [TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)
- **MWRR cumulativo** e **MWRR annualizzato** — il tuo rendimento personale, incluso il timing dei depositi, sul periodo e come tasso annuo → [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)

**Come leggerla**

- **Timing favorevole** (verde): tendevi a depositare prima che i prezzi salissero. **Timing sfavorevole** (rosso): tendevi a depositare sui massimi. Vicino allo zero si legge **Timing neutro**, e più forte è il colore, maggiore è l'effetto.
- **Il TWRR giudica la strategia, il MWRR il tuo risultato personale** — come per un gestore di fondi e un investitore.
- **Le quattro righe coprono l'intero periodo**; la piccola percentuale copre solo oggi.
- **`—` significa nessun valore**: un rendimento che LibreFolio non può calcolare per il periodo mostra `—` al posto di un numero. L'effetto timing richiede sia il TWRR sia il MWRR: quando ne manca uno, mostra un `—` grigio, senza etichetta di timing.

??? info "📏 La percentuale sotto l'effetto timing — come viene calcolata"

    La stessa variazione del tuo P&L totale della [Scheda 1](#card-1-period-pl), divisa per il patrimonio netto di ieri preso senza il suo segno:

    $$
    \text{percentage} = \frac{\text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}}}{\left|\text{Net Worth}_{\text{yesterday}}\right|} \times 100
    $$

    Il suo segno e il suo colore seguono la variazione, come nella Scheda 1. Richiede due giorni di storico ed è nascosta quando il patrimonio netto di ieri era esattamente zero.

---

## 💰 Scheda 3 — Patrimonio netto {: #card-3-net-worth }

Quanto vale il tuo portafoglio alla fine del periodo, e quanto ha guadagnato da quando hai iniziato? La scheda **Patrimonio netto** risponde, liquidità inclusa.

<div class="kpi-card-crop-container card-net-worth">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda Patrimonio netto">
</div>

**Metriche mostrate**

- **Patrimonio netto** — il numero grande: titoli al valore di mercato, più liquidità, più tutto ciò che è in transito tra i tuoi broker → [NAV / Patrimonio netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **La riga sotto di esso** — per esempio `+12.450,30 (+24,85%)`: il tuo **P&L totale** dall'inizio e, tra parentesi, il tuo **ROI dall'inizio** → [Capitale versato e P&L totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)
- **Valore di mercato** — quanto valgono, ai prezzi di mercato, gli asset che detieni → [NAV / Patrimonio netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **Valore di acquisto** — quanto ti sono costate le posizioni che detieni ancora, ogni acquisto al tasso di cambio della propria data → [Valore contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Liquidità** — la liquidità presso i tuoi broker; passa il cursore per separare il capitale versato dai rendimenti che hai ottenuto → [Pool di liquidità](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)
- **Capitale versato (Periodo)** — depositi meno prelievi nel periodo, verde a destra e rosso a sinistra; passa il cursore per vedere i totali → [Capitale versato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

$$
\text{Total P}\&\text{L} = \text{Net Worth} - \text{Capital put in since the start}
$$

Quel capitale è ogni deposito meno ogni prelievo, più il valore di acquisto dei titoli che hai conferito senza liquidità, come una posizione di apertura; il ROI tra parentesi divide per esso il P&L totale.

**Come leggerla**

- **Data finale o periodo?** Il numero grande e le prime tre righe sono valori alla data finale; il Capitale versato (Periodo) conta solo i movimenti tra inizio e fine.
- **Il piccolo caret** su una barra indica il suo valore all'inizio del periodo (passa il cursore); il Valore di mercato diventa rosso quando termina al di sotto di esso.
- **Il Patrimonio netto include la liquidità**, a differenza del "valore dei titoli" di un estratto conto bancario.
- **Il P&L totale non è una variazione giornaliera**: per il polso di oggi, vedi le piccole righe nelle schede 1 e 2.

---

## 🔗 Correlati

- 🔍 **[Posizioni e analisi](positions.md)** — gli stessi risultati, posizione per posizione
- 📊 **[Grafici](charts.md)** — la vista **P&L** del grafico di crescita segue il tuo P&L totale nel tempo
- 📐 **[Panoramica delle metriche di performance](../../financial-theory/technical-analysis/performance-metrics/index.md)** — ogni metrica di queste schede, con la sua formula
- 🛠️ **[Dettagli tecnici](../../developer/frontend/pages/index.md#dashboard)** — per gli sviluppatori: da dove provengono i numeri delle schede

---

*[⬅️ Torna alla panoramica della Dashboard](index.md)*
