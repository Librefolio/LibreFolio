# 📊 Dashboard

La Dashboard è il **centro di comando del tuo portafoglio** — una schermata unica che ti mostra il valore del portafoglio, le sue performance e come sono allocati i tuoi capitali.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista Principale (Assoluto)" alt="Dashboard — Modalità Assoluta">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista Principale (Percentuale)" alt="Dashboard — Modalità Percentuale">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocazione" alt="Dashboard — Allocazione">
</div>

## 🗂️ Layout a Schede

L'interfaccia della Dashboard è organizzata in tre schede principali, che ti permettono di passare tra diversi livelli di dettaglio:

1. **Panoramica** (predefinita): Metriche chiave, saldi di liquidità e grafici del tuo portafoglio.
2. **[Posizioni e Analisi](positions.md)**: Posizioni aperte, pesi e analisi dettagliata dei lotti fiscali (FIFO).
3. **Transazioni**: Elenco delle operazioni recenti con un visualizzatore di dettagli in sola lettura.

---

## 📈 Scheda Panoramica

La scheda Panoramica è la pagina di destinazione predefinita. È strutturata nelle seguenti sezioni:

| Sezione | Descrizione |
|---------|-------------|
| **[Schede KPI](kpi-cards.md)** | Riepilogo del Patrimonio Netto, P&L di periodo e metriche di rendimento. |
| **Saldi di Liquidità** | Saldi liquidi raggruppati per valuta nell'ambito del broker attivo. |
| **[Grafico di Crescita](charts.md#portfolio-growth-chart)** | Grafico ad aree impilate che mostra il costo degli asset, la liquidità e i rendimenti nel tempo. |
| **[Pannello di Allocazione](charts.md#allocation-panel)** | Grafici a ciambella e storici impilati raggruppati per Tipo, Settore e Geografia. |

### 🪙 Saldi di Liquidità

Direttamente sotto le schede KPI, il pannello **Saldi di Liquidità** mostra la tua liquidità totale aggregata per valuta. Ad esempio, se detieni USD presso il broker A ed EUR presso il broker B, entrambi i saldi verranno visualizzati fianco a fianco.

Quando applichi un filtro per broker, i saldi di liquidità si aggiornano automaticamente per riflettere solo la liquidità detenuta presso i broker selezionati.

---

## 🎛️ Intervallo di Date, Filtri ed Esportazione AI

Nella parte superiore destra della dashboard, hai diversi controlli per personalizzare la visualizzazione:

- **Intervallo temporale** — predefiniti da 1 settimana a Tutto il periodo (MAX), o un intervallo personalizzato tramite il selettore di date.
- **Filtro broker** — filtra tutte le metriche per uno o più broker specifici.
- **Valuta di destinazione** — converte dinamicamente tutti gli asset e i saldi di liquidità in un'unica valuta selezionata per una visione aggregata.
- **Esportazione AI** (:material-brain:) — apre un'esportazione negli appunti.
  Scegli **Fotografia dati** per copiare solo dati fattuali, oppure un **task di
  analisi** che include automaticamente istruzioni e contratto di risposta, poi
  seleziona il **livello di dettaglio** (Compatto, Standard o Completo).
  L'istantanea del backend segue filtro broker attivo, intervallo di date e
  valuta di destinazione; LibreFolio non contatta servizi AI. Consulta la
  [Esportazione AI Portafoglio](../ai-export/portfolio.md) o la [guida Esportazione AI](../ai-export/index.md).

!!! tip "L'ambito è importante"

    Quando filtri per un singolo broker, i trasferimenti di liquidità *verso altri broker* diventano flussi esterni per quell'ambito. Ciò influisce sui calcoli del [Capitale Depositato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) e del [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

!!! note "La condivisione influenza questi numeri"

    La dashboard aggrega solo i broker **a cui hai accesso**, e ogni importo proveniente da un broker di cui sei co-proprietario è **ridimensionato in base alla tua quota di proprietà**: un Proprietario con una quota del 50% vede conteggiata nei totali la metà del valore, del reddito e del P&L di quel broker (una quota dello 0% è valida e non contribuisce). Editor e Visualizzatori — che per regola hanno sempre una quota dello 0% — vedono invece gli importi **completi** del broker. Vedi [Condivisione del Broker](../brokers/sharing.md) per i dettagli.

---

## 🌡️ Banner di Qualità dei Dati

Se mancano prezzi o tassi di cambio alla data di fine, appare un banner nella parte superiore che spiega quali asset non hanno potuto essere valutati.
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="data-quality-banner" alt="Banner di qualità dei dati della dashboard con link per asset">
</div>
 Gli asset senza un fornitore di prezzo (inseriti manualmente, come i progetti di crowdfunding immobiliare) sono permanentemente valutati al costo di acquisto — questo è intenzionale e non genera un avviso.

---

## 🔗 In questa sezione

- 💰 **[Schede KPI](kpi-cards.md)** — Spiegazione di Patrimonio Netto, P&L di periodo e Rendimenti
- 📊 **[Grafici](charts.md)** — Spiegazione del Grafico di Crescita e del Pannello di Allocazione
- 🔍 **[Posizioni e Analisi](positions.md)** — Posizioni aperte, viste tabella vs. mappa e analisi dettagliata dei lotti fiscali FIFO.


## 🔗 Teoria correlata

- **[NAV / Patrimonio Netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valore Contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[P&L di Periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capitale Depositato e P&L Totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Panoramica delle Metriche di Performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
