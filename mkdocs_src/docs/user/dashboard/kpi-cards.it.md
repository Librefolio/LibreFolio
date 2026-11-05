# 💰 Schede KPI

Le tre schede in cima alla Dashboard rispondono a colpo d'occhio a tre domande: **quanto ho guadagnato in questo periodo**, **quanto bene hanno lavorato i miei soldi** e **quanto vale il mio portafoglio**. Seguono l'intervallo temporale e il filtro broker in cima alla pagina, e la pagina di un broker mostra le stesse schede solo per quel broker. L'icona **?** nell'angolo di una scheda apre la sezione corrispondente qui sotto.

- 📉 **[Scheda 1 — P&L periodo](#card-1-period-pl)** — il denaro che i tuoi investimenti hanno prodotto nel periodo
- 📈 **[Scheda 2 — Rendimenti](#card-2-returns)** — i tuoi rendimenti in percentuale, e l'effetto che il tuo timing ha avuto su di essi
- 💰 **[Scheda 3 — Patrimonio netto](#card-3-net-worth)** — ciò che possiedi, e il guadagno accumulato dall'inizio

!!! note "I broker condivisi contano per la tua quota"

    La Dashboard somma i broker che **possiedi** con una quota superiore allo 0%, ciascuno in proporzione a quella quota: un proprietario al 50% vede metà del valore e del P&L del broker. I broker in cui sei editor o visualizzatore non sono conteggiati qui; la loro pagina li mostra, con gli importi completi. Vedi [Condivisione broker](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Panoramica delle schede KPI">
</div>

---

## 📉 Scheda 1 — P&L periodo {: #card-1-period-pl }

Quanto denaro hanno prodotto i tuoi investimenti nel periodo selezionato? La scheda **P&L periodo** risponde, escludendo il denaro che hai spostato in entrata o in uscita tu stesso.

<div class="kpi-card-crop-container card-period-pnl">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda P&L periodo">
</div>

**Metriche mostrate**

- **P&L periodo** — il numero grande: $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Net flows}$, dove i flussi netti sono il capitale che hai spostato in entrata o in uscita → [P&L periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **La riga sotto** — per esempio `+91.31 € (+16.36%)`: di quanto è cambiato il tuo P&L totale da ieri (pannello sottostante)
- **Variazione non realizzata** — come si è mossa nel periodo la plusvalenza o minusvalenza non realizzata delle tue posizioni, effetto cambio incluso → [P&L periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Vendite** — la plusvalenza o minusvalenza realizzata delle vendite del periodo, rispetto al costo medio delle unità vendute. Una rettifica che rimuove unità non ha valore: qui conta come una vendita a zero, una perdita pari a quanto sono costate quelle unità (vedi [Rettifiche in uscita](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)) → [Prezzo medio di carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Dividendi e interessi** — dividendi, cedole e interessi P2P ricevuti → [Dividendi e interessi](../../financial-theory/instruments/transaction-types/dividend-interest.md)
- **Commissioni e imposte** — commissioni e imposte registrate come transazioni; passa il mouse sulla riga per vedere la suddivisione → [Commissioni e imposte](../../financial-theory/instruments/transaction-types/fee.md)

**Come leggerla**

- **Il verde è un guadagno, il rosso una perdita** — e un deposito o un prelievo non rappresenta né l'uno né l'altro.
- **Le quattro righe spiegano il numero grande.** Ciò che non riescono a vedere confluisce nella [vista Periodo](positions.md#performance): l'effetto dei tassi di cambio sulla liquidità che detieni in un'altra valuta compare lì come **Effetto cambio sulla liquidità**, una riga per ogni broker la cui liquidità è stata mossa dai tassi. Quando consideri solo alcuni dei tuoi broker, i titoli trasferiti da o verso un broker fuori dalla tua selezione sono conteggiati al loro valore di mercato del giorno: il guadagno maturato presso l'altro broker compare come **Trasferimenti a valore di mercato**, una riga per ogni broker coinvolto ([come funziona](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#transfers-at-market-value)). Il resto — ad esempio asset che si spostano tra due dei tuoi broker il primo o l'ultimo giorno — è l'**Altro / residuo di riconciliazione**.
- **La barra più lunga** è la riga che ha inciso di più sul tuo risultato.

??? info "📏 La riga sotto il numero grande — come si calcola"

    È la variazione del tuo P&L totale — il guadagno o la perdita dall'inizio — da ieri a oggi, dove *oggi* è la data di fine del periodo. La percentuale lo confronta con il P&L totale di ieri, preso senza il suo segno:

    $$
    \Delta = \text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}} \qquad \text{percentage} = \frac{\Delta}{\left|\text{Total P}\&\text{L}_{\text{yesterday}}\right|} \times 100
    $$

    - **Segno e colore seguono la variazione**, anche quando il P&L totale è una perdita: da `-558.10 €` a `-466.79 €`, la riga mostra `+91.31 € (+16.36%)` — la tua perdita si è ridotta del 16.36%.
    - **Manca solo quando il periodo termina nel primo giorno del tuo portafoglio**, poiché non c'è un giorno precedente con cui confrontare; la percentuale viene omessa quando il P&L totale di ieri è esattamente zero, e un giorno senza variazioni mostra `0.00%`. Di lunedì la riga copre l'intero fine settimana, poiché un giorno senza mercato mantiene i prezzi dell'ultimo giorno di contrattazione.

### 💱 Variazione non realizzata per valuta {: #unrealized-change-by-currency }

Passa il mouse su **Variazione non realizzata** per suddividerla per la valuta in cui sono espressi i tuoi asset — qui con l'euro come valuta di visualizzazione:

| Riga | Cosa mostra |
|-----|---------------|
| 📈 **Asset in USD** | Cosa hanno fatto *in dollari* i tuoi asset in dollari — la loro variazione di prezzo — valutati al tasso di cambio del giorno |
| 💱 **Tasso USD → EUR** | Cosa ha fatto il tasso di cambio rispetto a quanto li hai pagati |
| ❔ **USD, non suddiviso** | Solo quando, il primo o l'ultimo giorno, alcuni di quegli asset non avevano un tasso o un valore di acquisto incompleto: la loro variazione, in un unico blocco |

C'è una riga 📈 per ogni valuta, euro incluso, e una riga 💱 per ogni valuta diversa dalla tua valuta di visualizzazione; insieme, le righe sommano **esattamente** alla Variazione non realizzata. In un giorno in cui un asset è valorizzato al costo che hai sostenuto, perché non ha alcun prezzo, non ha plusvalenze o minusvalenze non realizzate e non aggiunge nulla a nessuna riga.

??? example "Un ETF statunitense su una dashboard in euro"

    Durante il periodo hai acquistato 10 unità per 400 €, quando valevano 500 USD. Alla fine del periodo valgono 550 USD e 1 USD = 0,75 €. Il tooltip mostra:

    - 📈 **Asset in USD**: (550 − 500) × 0,75 = **+37,50 €** — il tuo ETF ha guadagnato il 10% in dollari;
    - 💱 **Tasso USD → EUR**: 500 × 0,75 − 400 = **−25,00 €** — il dollaro ha perso valore rispetto all'euro;
    - insieme, la **Variazione non realizzata**: 550 × 0,75 − 400 = **+12,50 €**.

🔗 **Teoria**: [Variazione non realizzata per valuta](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#unrealized-change-by-currency) — le formule dietro ogni riga

---

## 📈 Scheda 2 — Rendimenti {: #card-2-returns }

Quanto bene hanno lavorato i tuoi soldi, indipendentemente dalla dimensione del portafoglio? La scheda **Rendimenti** risponde in percentuale, e il suo numero grande ti dice se il tuo timing è stato d'aiuto.

<div class="kpi-card-crop-container card-returns">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda Rendimenti">
</div>

**Metriche mostrate**

- **Effetto timing** — il numero grande, in punti percentuali (pp): $\text{MWRR}_{\text{cumulative}} - \text{TWRR}$ → [Effetto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)
- **La percentuale sotto** — per esempio `+0.35%`: la variazione odierna del tuo P&L totale, rispetto al patrimonio netto di ieri (pannello sottostante)
- **ROI** — il guadagno del periodo rispetto al capitale investito: quanto valeva il portafoglio all'inizio del periodo, più i depositi e meno i prelievi effettuati da allora. Quando l'intervallo inizia prima della tua prima transazione, anche il tuo primo deposito conta come capitale, quindi il ROI è identico a quello dell'intera storia → [ROI semplice](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md#dashboard-period-roi)
- **TWRR** — come si sono comportate le tue scelte di asset, indipendentemente dal timing dei tuoi depositi → [TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)
- **MWRR cumulato** e **MWRR annualizzato** — il tuo rendimento personale, timing dei depositi incluso, sull'intero periodo e come tasso annuo → [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)

**Come leggerla**

- **Timing favorevole** (verde): tendevi a depositare prima che i prezzi salissero. **Timing sfavorevole** (rosso): tendevi a depositare sui massimi. Vicino allo zero si legge **Timing neutro**, né verde né rosso.
- **Il TWRR giudica la strategia, il MWRR il tuo risultato personale** — come per un gestore di fondi e un investitore.
- **Le quattro righe coprono l'intero periodo**; la piccola percentuale riguarda solo oggi.
- **`—` significa nessun valore**: un rendimento che LibreFolio non può calcolare per il periodo mostra `—` invece di un numero. TWRR e MWRR mostrano `—` quando il tuo portafoglio vale zero o meno alla fine del periodo, ad esempio dopo che hai venduto tutto e prelevato la liquidità ([Quando non viene mostrato il TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr), [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)). L'effetto timing richiede sia TWRR sia MWRR: quando ne manca uno, mostra un `—` grigio, senza etichetta di timing. Il ROI non è mai `—`: senza capitale investito nel periodo mostra `0.00%`.

??? info "📏 La percentuale sotto l'effetto timing — come si calcola"

    La stessa variazione del tuo P&L totale della [Scheda 1](#card-1-period-pl), divisa per il patrimonio netto di ieri preso senza il suo segno:

    $$
    \text{percentage} = \frac{\text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}}}{\left|\text{Net Worth}_{\text{yesterday}}\right|} \times 100
    $$

    Il suo segno e il suo colore seguono la variazione, come nella Scheda 1. Manca quando il periodo termina nel primo giorno del tuo portafoglio ed è nascosta quando il patrimonio netto di ieri era esattamente zero.

---

## 💰 Scheda 3 — Patrimonio netto {: #card-3-net-worth }

Quanto vale il tuo portafoglio alla fine del periodo, e quanto ha guadagnato da quando hai iniziato? A questa domanda risponde la scheda **Patrimonio netto**, liquidità inclusa.

<div class="kpi-card-crop-container card-net-worth">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda Patrimonio netto">
</div>

**Metriche mostrate**

- **Patrimonio netto** — il numero grande: titoli al valore di mercato, più la liquidità, più tutto ciò che è in transito tra i tuoi broker → [NAV / Patrimonio netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **La riga sotto** — per esempio `+12,450.30 (+24.85%)`: il tuo **P&L totale** dall'inizio e, tra parentesi, il tuo **ROI dall'inizio** → [Capitale versato e P&L totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)
- **Valore di mercato** — quanto valgono ai prezzi di mercato gli asset che detieni → [NAV / Patrimonio netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **Valore di acquisto** — quanto ti sono costate le posizioni che detieni ancora, ogni acquisto al tasso di cambio della rispettiva data → [Valore contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Liquidità** — la liquidità presso i tuoi broker; passa il mouse sopra per separare il capitale versato dai rendimenti ottenuti → [Pool di liquidità](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)
- **Capitale versato (periodo)** — depositi meno prelievi nel periodo, verde a destra e rosso a sinistra; passa il mouse sopra per i totali → [Capitale versato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

$$
\text{Total P}\&\text{L} = \text{Net Worth} - \text{Capital put in since the start}
$$

Quel capitale è ogni deposito meno ogni prelievo, più il valore di acquisto dei titoli che hai introdotto senza liquidità, come una posizione di apertura; il ROI tra parentesi divide il P&L totale per quel capitale.

**Come leggerla**

- **Data di fine o periodo?** Il numero grande e le prime tre righe sono valori alla data di fine; il capitale versato (periodo) conta solo i movimenti tra inizio e fine.
- **Il piccolo indicatore sulla barra** indica il suo valore all'inizio del periodo (passa il mouse sopra); il valore di mercato diventa rosso quando il suo valore finale è inferiore a quello iniziale.
- **Il patrimonio netto include la liquidità**, a differenza del "valore titoli" di un estratto conto bancario.
- **Il P&L totale non è una variazione giornaliera**: per la situazione odierna, vedi le righe piccole nella Scheda 1 e nella Scheda 2.

---

## 🔗 Correlati

- 🔍 **[Posizioni e analisi](positions.md)** — gli stessi risultati, posizione per posizione
- 📊 **[Grafici](charts.md)** — la vista **P&L** del grafico Crescita segue il tuo P&L totale nel tempo
- 📐 **[Panoramica delle metriche di performance](../../financial-theory/technical-analysis/performance-metrics/index.md)** — ogni metrica di queste schede, con la sua formula
- 🛠️ **[Dettagli tecnici](../../developer/frontend/pages/index.md#dashboard)** — per gli sviluppatori: da dove provengono i numeri delle schede

---

*[⬅️ Torna alla panoramica della Dashboard](index.md)*
