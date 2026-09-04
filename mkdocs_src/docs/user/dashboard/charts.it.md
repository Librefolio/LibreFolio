# 📊 Grafici

La sezione dei grafici si trova sotto le schede KPI e fornisce una **visione storica e strutturale** del tuo portafoglio nell'intervallo di tempo selezionato.

---

## 📈 Grafico della Crescita del Portafoglio {: #portfolio-growth-chart }

Il grafico della crescita mostra come il valore del tuo portafoglio è evoluto nel periodo selezionato. Usa l'interruttore **Ass / %** nell'angolo in alto a destra per passare da una vista all'altra.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Modalità Assoluta" alt="Grafico della Crescita — Modalità Assoluta">
 <img class="gallery-img" data-category="dashboard" data-name="main" alt="Grafico della Crescita — Modalità Assoluta">
 </div>
 <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Modalità Percentuale" alt="Grafico della Crescita — Modalità Percentuale">
 <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Grafico della Crescita — Modalità Percentuale">
 </div>
</div>

### ABS ASS — valori assoluti

Il grafico utilizza un design **ad area impilata + linee sovrapposte**:

| Elemento | Colore | Significato |
|---------|-------|-------------|
| Area — **Costo degli Asset** | Blu | Base di costo di tutte le posizioni aperte (costo medio × quantità) |
| Area — **Rendimenti** | Smeraldo | Rendimenti del portafoglio come liquidità disponibile (interessi, plusvalenze realizzate non ancora reinvestite) |
| Area — **Capitale** | Grigio-verde | Depositi non impiegati in contanti |
| Linea — **[NAV](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Verde scuro continua | Valore totale del portafoglio ai prezzi correnti di mercato |
| Linea — **[Capitale Depositato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Grigia tratteggiata | Capitale esterno netto conferito nel tempo |

**La differenza tra la linea NAV e la linea Capitale Depositato = P&L Totale** — tutti i profitti mai generati, incluse plusvalenze non realizzate, plusvalenze realizzate, interessi e dividendi, meno commissioni e imposte.

#### Tooltip del suggerimento

Quando passi il mouse sul grafico, il suggerimento mostra:

- **NAV** — valore totale del portafoglio a quella data
- **Capitale Depositato** — capitale netto che hai conferito fino a quella data
- **P&L Totale** — la differenza (NAV − Capitale Depositato)
- **Costo degli Asset** / **Rendimenti** / **Capitale** — le tre componenti di cassa

!!! tip "Leggere portafogli basati sul reddito (P2P, obbligazioni)"

    Per portafogli come il P2P lending dove gli asset sono valutati al prezzo di acquisto (nessun prezzo di mercato in tempo reale), NAV ≈ Costo degli Asset. La differenza tra NAV e Capitale Depositato potrebbe non essere visibile come divario nel grafico — ma il suggerimento **P&L Totale** mostra il valore corretto.

    Quando reinvesti tutti i rendimenti in nuovi asset, l'area Rendimenti rimane vicina allo zero e il reddito guadagnato finisce incorporato nell'area Costo degli Asset. Questo è matematicamente corretto: la tua base di costo è cresciuta perché hai reinvestito i profitti.

🔗 **Teoria**: [Capitale Depositato & P&L Totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Scomposizione della Cassa](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### Modalità % — tasso di rendimento

Tutte le serie iniziano allo 0% all'inizio del periodo selezionato e mostrano come ogni metrica di rendimento è evoluta:

| Serie | Cosa mostra |
|--------|--------------|
| **[MWRR cumulativo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Il tuo rendimento personale ponderato per il denaro, inclusa la tempistica dei depositi |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rendimento puro della strategia sugli asset, ignorando quando hai depositato |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rendimento lordo sul capitale netto investito |

La differenza tra MWRR e TWRR è l'[Effetto Tempistica](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md).

!!! note "MWRR non disponibile"

    Se appare un banner di **Qualità dei Dati** che segnala che MWRR è inaffidabile, la serie MWRR viene nascosta dal grafico %. Il problema si verifica tipicamente quando il periodo ha flussi di cassa molto ampi rispetto alla dimensione iniziale del portafoglio, causando instabilità nel risolutore matematico. ROI e TWRR vengono sempre mostrati.

---

## 🥧 Pannello di Allocazione {: #allocation-panel }

Il pannello di allocazione mostra come il tuo portafoglio è distribuito nel momento corrente e come si è evoluto storicamente.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Per Tipo (Corrente)" alt="Allocazione per Tipo — Corrente">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Allocazione per Tipo — Corrente">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per Settore (Corrente)" alt="Allocazione per Settore — Corrente">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Allocazione per Settore — Corrente">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per Geografia (Corrente)" alt="Allocazione per Geografia — Corrente">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Allocazione per Geografia — Corrente">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per Tipo (Storico)" alt="Storico Allocazione per Tipo">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Storico Allocazione per Tipo">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per Settore (Storico)" alt="Storico Allocazione per Settore">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Storico Allocazione per Settore">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per Geografia (Storico)" alt="Storico Allocazione per Geografia">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Storico Allocazione per Geografia">
 </div>
</div>

### Three dimensioni

| Dimensione | Cosa mostra |
|-----------|-------------|
| **Tipo** | ETF, Azione, Obbligazione, Crypto, Immobiliare, Liquidità (contanti) |
| **Settore** | Settore industriale: 💻 Tecnologia, 🏦 Finanziario, 💊 Sanità, ecc. |
| **Geografia** | Paese o regione della quotazione principale di ogni asset |

### Now Ora vs. Storico

- **Ora** — Grafico a ciambella dell'allocazione corrente a `date_to`. Passa il mouse su una fetta per vedere la percentuale esatta e il valore assoluto.
- **Storico** — Grafico ad area impilata al 100% che mostra come l'allocazione è cambiata nel tempo. Utile per visualizzare il ribilanciamento del portafoglio tra mesi o anni.

### Cash come Liquidità

**I contanti** (il saldo del tuo broker) appaiono sempre come la fetta **Liquidità** sia nella vista Tipo che Settore. Nella mappa geografica, i contanti non sono assegnati a nessun paese e non appaiono.

!!! info "Ambito del broker"

    Quando filtri per broker specifici, l'allocazione mostra solo gli asset e i contanti all'interno di quei broker.

---

## 🔗 Correlati

- 💰 **[Schede KPI](kpi-cards.md)** — Patrimonio Netto, P&L del Periodo, Rendimenti
- 💼 **[NAV / Patrimonio Netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capitale Depositato & P&L Totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Effetto Tempistica](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**

---

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*
