# 💰 Carte KPI

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*

Le tre carte KPI nella parte superiore della dashboard forniscono una rapida diagnosi del tuo portafoglio. Tutti i valori rispettano l'**intervallo di tempo e l'ambito del broker** selezionati nella parte superiore della pagina.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Panoramica Carte KPI">
</div>

---

## 📉 Carta 1 — P&L del Periodo {: #card-1-period-pl }

<div class="kpi-card-crop-container card-period-pnl">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carta P&L del Periodo">
</div>

La carta **P&L del Periodo** mostra quanto denaro il tuo portafoglio ha effettivamente *guadagnato* nella finestra selezionata — dopo aver rimosso l'effetto dei tuoi depositi e prelievi.

Il numero principale è calcolato utilizzando la seguente formula:

\[\text{P&L del Periodo} = \text{NAV}_{\text{fine}} - \text{NAV}_{\text{inizio}} - \text{Flussi Netti}_{\text{periodo}}\]

Un numero positivo significa che hai guadagnato denaro dall'attività di investimento. Un numero negativo significa che hai perso denaro al netto dei movimenti di capitale.

### Le righe di dettaglio

| Riga | Cosa misura |
|-----|-------------|
| **Variazione non realizzata** | Quanto è cambiato l'[utile/perdita non realizzato](../../financial-theory/technical-analysis/performance-metrics/book-value.md) delle tue posizioni aperte durante il periodo |
| **Vendite** | Utile o perdita realizzata dalle posizioni chiuse durante il periodo (prezzo di vendita − costo medio) |
| **Dividendi e interessi** | Reddito da contanti da dividendi, cedole obbligazionarie e interessi P2P |
| **Commissioni e imposte** | Commissioni e imposte registrate come transazioni |

!!! tip "Verifica di identità"

    Tutte e quattro le righe sommate danno il numero principale del P&L del Periodo (± piccoli residui dovuti all'arrotondamento FX).

🔗 **Teoria**: [P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md) · [Valore Contabile / PMC](../../financial-theory/technical-analysis/performance-metrics/book-value.md)

---

## 📈 Carta 2 — Rendimenti {: #card-2-returns }

<div class="kpi-card-crop-container card-returns">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carta Rendimenti">
</div>

La carta **Rendimenti** mostra metriche di *tasso di rendimento* — percentuali che ti permettono di confrontare la performance indipendentemente dalla dimensione del portafoglio.

### Effetto Tempismo

L'**Effetto Tempismo** nella parte superiore della carta misura se le tue decisioni di deposito/prelievo hanno *aggiunto* o *sottratto* valore rispetto a una strategia passiva di acquisto e mantenimento:

\[\text{Effetto Tempismo} = \text{MWRR}_{\text{cumulativo}} - \text{TWRR}_{\text{cumulativo}}\]

- **Favorevole (positivo)** ✅: hai avuto la tendenza a depositare quando i prezzi erano bassi, aumentando il tuo rendimento personale al di sopra di quanto guadagnato dai soli asset.
- **Sfavorevole (negativo)** ❌: hai avuto la tendenza a depositare ai massimi o hai perso i minimi, abbassando il tuo rendimento al di sotto della pura performance degli asset.

### Le quattro metriche di rendimento

| Metrica | Domanda a cui risponde |
|---------|------------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Quanto ho guadagnato rispetto al mio capitale netto investito? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Come si sono comportate le mie scelte di asset, indipendentemente da quando ho depositato? |
| **[MWRR cumulativo](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Qual è il rendimento cumulativo ponderato per il denaro dei miei flussi di cassa effettivi? |
| **[MWRR annualizzato](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | A quale tasso composto annuo è effettivamente cresciuto il mio capitale? |

!!! note "TWRR vs. MWRR"

    - **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** misura la **strategia degli asset** — allo stesso modo in cui viene valutato un gestore di fondi.
    - **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** misura **il tuo risultato personale** — includendo la tempistica dei tuoi depositi.
    - Il divario tra loro è l'[Effetto Tempismo](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

---

## 💰 Carta 3 — Patrimonio Netto {: #card-3-net-worth }

<div class="kpi-card-crop-container card-net-worth">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carta Patrimonio Netto">
</div>

La carta **Patrimonio Netto** mostra il valore assoluto del tuo portafoglio alla fine del periodo selezionato.

### Cosa significano le righe

| Riga | Definizione |
|------|------------|
| **[Valore di Mercato](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Prezzo corrente di mercato × quantità per tutti gli asset detenuti |
| **[Valore Contabile](../../financial-theory/technical-analysis/performance-metrics/book-value.md)** | Quanto hai pagato per le tue posizioni aperte (costo medio × q.tà) |
| **Contanti** | Saldo liquido detenuto nei conti del broker |
| **[Capitale Depositato](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Capitale netto esterno conferito in questo ambito |

### La barra del Capitale Depositato

La barra orizzontale sotto le righe visualizza:

- 🟢 **Totale depositato** — tutti i depositi nel periodo
- 🔴 **Totale prelevato** — tutti i prelievi nel periodo

Il numero principale mostra il saldo netto (depositato − prelevato).

!!! info "Istantanea vs. periodo"

    Valore di Mercato, Valore Contabile e Contanti sono **istantanee** alla data di fine — sono indipendenti dalla data di inizio.
    Il Capitale Depositato è **relativo al periodo** — conta i depositi e i prelievi tra l'inizio e la fine dell'intervallo selezionato.

---

## 🔗 Correlati

- 💼 **[NAV / Patrimonio Netto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 📚 **[Valore Contabile](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- 📊 **[P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- 💸 **[Capitale Depositato e P&L Totale](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)**
- ⏱️ **[Effetto Tempismo](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
