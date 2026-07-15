# 📊 Dashboard

La Dashboard è il **centro di comando del tuo portafoglio** — una singola schermata che ti mostra il valore del tuo portafoglio, la sua performance e come è allocato il tuo denaro.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista principale (Assoluto)" alt="Dashboard — Modalità Assoluto">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista principale (Percentuale)" alt="Dashboard — Modalità Percentuale">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocazione" alt="Dashboard — Allocazione">
</div>

## 🗂️ Layout a schede

L'interfaccia della Dashboard è organizzata in tre schede principali, che ti permettono di passare tra diversi livelli di dettaglio:

1. **Panoramica** (predefinita): Metriche chiave, saldi di cassa e grafici del tuo portafoglio.
2. **[Posizioni e Analisi](positions.md)**: Partecipazioni aperte, pesi e analisi dettagliata dei lotti fiscali (FIFO).
3. **Transazioni**: Elenco delle operazioni recenti con un visualizzatore di dettaglio in sola lettura.

---

## 📈 Scheda Panoramica

La scheda Panoramica è la pagina di destinazione predefinita. È strutturata nelle seguenti sezioni:

| Sezione | Descrizione |
|---------|-------------|
| **[Schede KPI](kpi-cards.md)** | Riepilogo del Patrimonio Netto, P&L di Periodo e metriche del tasso di rendimento. |
| **Saldi di Cassa** | Saldi liquidi raggruppati per valuta nell'ambito del broker attivo. |
| **[Grafico di Crescita](charts.md#portfolio-growth-chart)** | Grafico ad area impilata che mostra il costo degli asset, la liquidità e i rendimenti nel tempo. |
| **[Pannello di Allocazione](charts.md#allocation-panel)** | Grafici a ciambella e storici impilati raggruppati per Tipo, Settore e Area Geografica. |

### 🪙 Saldi di Cassa

Subito sotto le schede KPI, il pannello **Saldi di Cassa** mostra la tua liquidità totale aggregata per valuta. Ad esempio, se possiedi USD nel broker A e EUR nel broker B, entrambi i saldi verranno visualizzati affiancati.

Quando applichi un filtro per broker, i saldi di cassa si aggiornano automaticamente per riflettere solo la liquidità detenuta presso i broker selezionati.

---

## 🎛️ Intervallo di Date, Filtri ed Esportazione AI

Nella parte superiore destra della dashboard, hai diversi controlli per personalizzare la tua visualizzazione:

- **Intervallo di tempo** — preset da 1 settimana a Da sempre (MAX), o un intervallo personalizzato tramite il selettore di date.
- **Filtro broker** — filtra tutte le metriche per uno o più broker specifici.
- **Valuta di destinazione** — converte dinamicamente tutti gli asset e i saldi di cassa in un'unica valuta selezionata per una visione aggregata.
- **Esportazione AI** (:material-brain:) — Clicca questo pulsante per copiare un riepilogo testuale dello stato attuale del tuo portafoglio negli appunti, ottimizzato per l'incollaggio in LLM (es. Gemini). Puoi scegliere tra:
 - **Esportazione Completa**: Include tutti i valori KPI, le posizioni, i pesi e le allocazioni.
 - **Solo Dati**: Una rappresentazione compatta in JSON/testo delle tue partecipazioni e dei saldi.

!!! tip "Il contesto è importante"

    Quando applichi un filtro per un singolo broker, i trasferimenti di liquidità *verso altri broker* diventano flussi esterni per quel contesto. Questo influisce sul [Capitale Depositato](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) e sul [P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md).

---

## 🌡️ Banner di Qualità dei Dati

Se mancano prezzi o tassi di cambio alla data di fine, appare un banner nella parte superiore che spiega quali asset non hanno potuto essere valutati. Gli asset senza un fornitore di prezzi (inseriti manualmente, come progetti di crowdfunding immobiliare) sono valutati permanentemente al costo di acquisto — questo è intenzionale e non genera un avviso.

---

## 🔗 In questa sezione

- 💰 **[Schede KPI](kpi-cards.md)** — Spiegazione di Patrimonio Netto, P&L di Periodo e Rendimenti
- 📊 **[Grafici](charts.md)** — Spiegazione del Grafico di Crescita e del Pannello di Allocazione
- 🔍 **[Posizioni e Analisi](positions.md)** — Posizioni aperte, vista tabella vs. mappa, e analisi dettagliata dei lotti fiscali FIFO.

## 🔗 Teoria correlata

- **[NAV / Patrimonio Netto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- **[Valore Contabile](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- **[P&L di Periodo](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- **[Capitale Depositato e P&L Totale](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- **[Panoramica delle Metriche di Performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
