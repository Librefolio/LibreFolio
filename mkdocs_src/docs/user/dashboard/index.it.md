# 📊 Dashboard

La Dashboard è il **centro di comando del tuo portafoglio** — una singola schermata che ti mostra il valore del tuo portafoglio, come sta performando e come sono allocati i tuoi soldi.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista Principale (Assoluto)" alt="Dashboard — Modalità Assoluta">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista Principale (Percentuale)" alt="Dashboard — Modalità Percentuale">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocazione" alt="Dashboard — Allocazione">
</div>

---

## 🗂️ Layout

| Sezione | Posizione | Contenuto |
|---------|-----------|-----------|
| **[Schede KPI](kpi-cards.md)** | Riga superiore | [Patrimonio Netto](kpi-cards.md#card-1--net-worth) · [P&L del Periodo](kpi-cards.md#card-2--period-pl) · [Rendimenti](kpi-cards.md#card-3--returns) |
| **[Grafico di Crescita](charts.md#portfolio-growth-chart)** | Centro sinistra | Area stacked assoluta + serie dei rendimenti percentuali |
| **[Pannello di Allocazione](charts.md#allocation-panel)** | Centro destra + fondo | Tipo / Settore / Area Geografica — attuale e storico |

---

## 🎛️ Date Range & Filtro Broker

Nella parte superiore della dashboard puoi selezionare:

- **Intervallo temporale** — predefiniti da 1 settimana a Sempre (All-Time), o un intervallo personalizzato tramite il selettore di date
- **Filtro Broker** — mostra tutti i broker o concentrati su uno o più
- **Valuta obiettivo** — converte tutti i valori in una singola valuta

!!! tip "L'ambito conta"

    Quando applichi un filtro a un singolo broker, i trasferimenti di liquidità *verso altri broker* diventano flussi esterni per tale ambito. Questo influenza i calcoli del [Capitale Depositato](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) e del [P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md).

---

## 🌡️ Banner Qualità dei Dati

Se mancano prezzi o tassi di cambio (FX) alla data finale, appare un banner in alto che spiega quali asset non è stato possibile valutare. Gli asset privi di un provider di prezzi (inseriti manualmente, come i progetti di crowdfunding immobiliare) sono valutati in modo permanente al costo di acquisto — questo è intenzionale e non genera un avvertimento.

---

## 🔗 In questa sezione

- 💰 **[Schede KPI](kpi-cards.md)** — Spiegazione di Patrimonio Netto, P&L del Periodo e Rendimenti
- 📊 **[Grafici](charts.md)** — Spiegazione del Grafico di Crescita e del Pannello di Allocazione

## 🔗 Teoria correlata

- **[NAV / Patrimonio Netto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- **[Valore Contabile](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- **[P&L del Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- **[Capitale Depositato & P&L Totale](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- **[Panoramica delle Metriche di Performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
