# 💰 Schede KPI

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*

Le tre schede KPI nella parte superiore della dashboard forniscono una rapida diagnosi del tuo portafoglio. Tutti i valori rispettano l'**intervallo di tempo e l'ambito del broker** selezionati nella parte superiore della pagina.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Panoramica Schede KPI">
</div>

---

## 📉 Scheda 1 — P&L del Periodo {: #card-1-period-pl }

<div class="kpi-card-crop-container card-period-pnl">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda P&L del Periodo">
</div>

La scheda **P&L del Periodo** mostra quanto denaro il tuo portafoglio ha effettivamente *guadagnato* nella finestra selezionata — dopo aver rimosso l'effetto dei tuoi depositi e prelievi personali.

Il valore principale viene calcolato utilizzando la seguente formula:

\[\text{P&L del Periodo} = \text{NAV}_{\text{fine}} - \text{NAV}_{\text{inizio}} - \text{Flussi Netti}_{\text{periodo}}\]

Un numero positivo significa che hai guadagnato denaro dall'attività di investimento. Un numero negativo significa che hai perso denaro al netto dei movimenti di capitale.

### The numero sotto il valore principale

Subito sotto il valore del P&L del Periodo, una riga più piccola mostra qualcosa come `+45.20 (+3.10%)`.

- L'importo è la variazione **giorno per giorno** (oggi rispetto a ieri) del tuo **P&L Totale** — il tuo guadagno/perdita accumulato da sempre, non solo del periodo selezionato.
- La percentuale lo esprime come quota del P&L del Periodo di **ieri** — ti dice quanto il movimento di oggi ha "pesato" sul risultato del periodo che stai visualizzando.

\[\text{Variazione giornaliera} = \text{P&L Totale}_{\text{oggi}} - \text{P&L Totale}_{\text{ieri}}\]

Questa riga appare solo quando la cronologia ha almeno due punti giornalieri.

### The righe di dettaglio

| Riga | Cosa misura |
|-----|-------------|
| **Variazione non realizzata** | Quanto è cambiata la [plusvalenza/perdita non realizzata](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) delle tue posizioni aperte durante il periodo |
| **Vendite** | Utile o perdita realizzata dalle posizioni chiuse durante il periodo (prezzo di vendita − costo medio) |
| **Dividendi e interessi** | Reddito da cassa da dividendi, cedole obbligazionarie e interessi P2P |
| **Commissioni e tasse** | Commissioni e tasse registrate come transazioni |

!!! tip "Controllo identità"

    Tutte e quattro le righe sommate danno il valore principale del P&L del Periodo (± piccoli residui dall'arrotondamento FX).

🔗 **Teoria**: [P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md) · [Valore Contabile / PMC](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)

---

## 📈 Scheda 2 — Rendimenti {: #card-2-returns }

<div class="kpi-card-crop-container card-returns">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda Rendimenti">
</div>

La scheda **Rendimenti** mostra metriche di *tasso di rendimento* — percentuali che ti permettono di confrontare le prestazioni indipendentemente dalla dimensione del portafoglio.

### Timing Tempistica

L'**Effetto Tempistica** nella parte superiore della scheda misura se le tue decisioni di deposito/prelievo hanno *aggiunto* o *sottratto* valore rispetto a una strategia passiva di buy-and-hold:

\[\text{Effetto Tempistica} = \text{MWRR}_{\text{cumulativo}} - \text{TWRR}_{\text{cumulativo}}\]

- **Favorevole (positivo)** ✅: hai avuto la tendenza a depositare quando i prezzi erano bassi, aumentando il tuo rendimento personale al di sopra di quanto guadagnato dai soli asset.
- **Sfavorevole (negativo)** ❌: hai avuto la tendenza a depositare ai picchi o hai perso i ribassi, abbassando il tuo rendimento al di sotto della pura performance degli asset.

### The numero sotto l'Effetto Tempistica

Sotto l'Effetto Tempistica vedrai una piccola percentuale (es. `+0.35%`) — è la variazione del tuo **P&L Totale** da **ieri a oggi**, espressa come quota del patrimonio netto di ieri:

\[\text{%Variazione giornaliera} = \frac{\text{P&L Totale}_{\text{oggi}} - \text{P&L Totale}_{\text{ieri}}}{\text{Patrimonio Netto}_{\text{ieri}}} \times 100\]

È una stima approssimativa del rendimento di **oggi** — un rapido controllo del polso. Non è il ROI, TWRR o MWRR mostrati nelle righe sottostanti, che rimangono ancorati all'intero periodo selezionato.

### The quattro metriche di rendimento

| Metrica | Domanda a cui risponde |
|---------|------------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Quanto ho guadagnato rispetto al mio capitale investito netto? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Come si sono comportate le mie scelte di asset, indipendentemente da quando ho depositato? |
| **[MWRR cumulativo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Qual è il rendimento ponderato per il denaro cumulativo per i miei flussi di cassa effettivi? |
| **[MWRR annualizzato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | A quale tasso composto annuo è cresciuto effettivamente il mio capitale? |

!!! note "TWRR vs. MWRR"

    - **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** misura la **strategia degli asset** — come viene valutato un gestore di fondi.
    - **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** misura **il tuo risultato personale** — inclusa la tempistica dei tuoi depositi.
    - Il divario tra loro è l'[Effetto Tempistica](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md).

---

## 💰 Scheda 3 — Patrimonio Netto {: #card-3-net-worth }

<div class="kpi-card-crop-container card-net-worth">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Scheda Patrimonio Netto">
</div>

La scheda **Patrimonio Netto** mostra il valore assoluto del tuo portafoglio alla fine del periodo selezionato.

!!! note "Il Patrimonio Netto include la liquidità"
    La cifra è **titoli al valore di mercato + saldo liquido** (+ eventuale valore in transito tra broker). Poiché include la liquidità, **non è confrontabile** con il "controvalore titoli" di un estratto conto bancario, che esclude la cassa — la liquidità della banca è riportata separatamente.

### The numero sotto il Patrimonio Netto

Sotto il valore del Patrimonio Netto troverai il tuo **P&L Totale**, con la sua variazione percentuale tra parentesi — es. `+12.450,30 (+0,35%)`.

- L'importo è il tuo **P&L Totale** — l'utile o la perdita accumulati dall'inizio, nell'intera cronologia di questo ambito (non solo il periodo corrente).
- La percentuale tra parentesi esprime la variazione **giorno per giorno** (oggi rispetto a ieri) di questo P&L Totale, come quota del **P&L Totale di ieri**.

\[\text{P&L Totale} = \text{Patrimonio Netto} - \text{Capitale Netto Investito dall'Inizio}\]

Nota: "Capitale Netto Investito dall'Inizio" qui è la somma di **tutti** i depositi meno **tutti** i prelievi da quando hai iniziato a utilizzare questo ambito — una cifra diversa e più grande rispetto alla riga "Capitale Depositato" sottostante, che conta solo i movimenti all'interno del periodo selezionato.

🔗 **Teoria**: [Capitale Depositato, P&L Totale e Pool di Liquidità](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

### What significano le righe

| Riga | Definizione |
|------|-------------|
| **[Valore di Mercato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Prezzo di mercato corrente × quantità per tutti gli asset detenuti |
| **[Valore Contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)** | Quanto hai pagato per le tue posizioni aperte (costo medio × q.tà) |
| **Cassa** | Saldo liquido detenuto nei conti del broker |
| **[Capitale Depositato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Capitale esterno netto conferito a questo ambito |

### The barra del Capitale Depositato

La barra orizzontale sotto le righe visualizza:

- 🟢 **Totale depositato** — tutti i depositi nel periodo
- 🔴 **Totale prelevato** — tutti i prelievi nel periodo

Il numero principale mostra il saldo netto (depositato − prelevato).

!!! info "Puntuale vs. periodo"

    Valore di Mercato, Valore Contabile e Cassa sono **istantanee** alla data di fine — sono indipendenti dalla data di inizio.
    Il Capitale Depositato è **scoped al periodo** — conta i depositi e i prelievi tra l'inizio e la fine dell'intervallo selezionato.

---

## 🔗 Correlati

- 💼 **[NAV / Patrimonio Netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 📚 **[Valore Contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- 📊 **[P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- 💸 **[Capitale Depositato e P&L Totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)**
- ⏱️ **[Effetto Tempistica](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
