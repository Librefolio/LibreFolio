# 📊 Grafici

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*

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

### Modalità Abs — valori assoluti

Il grafico utilizza un **design ad area impilata + linee sovrapposte**:

| Elemento | Colore | Significato |
|---------|-------|-------------|
| Area — **Costo degli Asset** | Blu | Base di costo di tutte le posizioni aperte (costo medio × quantità) |
| Area — **Rendimenti** | Smeraldo | Rendimenti del portafoglio sotto forma di liquidità disponibile (interessi, plusvalenze realizzate non ancora reinvestite) |
| Area — **Capitale** | Grigio-verde | Depositi non impiegati sotto forma di contante |
| Linea — **[NAV](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Verde scuro continuo | Valore totale del portafoglio ai prezzi correnti di mercato |
| Linea — **[Capitale Depositato](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Grigio tratteggiato | Capitale esterno netto conferito nel tempo |

**Il divario tra la linea del NAV e la linea del Capitale Depositato = P&L Totale** — tutti i guadagni mai generati, inclusi utili non realizzati, plusvalenze realizzate, interessi e dividendi, meno commissioni e imposte.

#### Dettaglio del suggerimento

Quando passi il mouse sul grafico, il suggerimento mostra:

- **NAV** — valore totale del portafoglio a quella data
- **Capitale Depositato** — capitale netto che hai conferito fino a quella data
- **P&L Totale** — la differenza (NAV − Capitale Depositato)
- **Costo degli Asset** / **Rendimenti** / **Capitale** — le tre componenti di cassa

!!! tip "Leggere i portafogli basati sul reddito (P2P, obbligazioni)"

    Per portafogli come il P2P lending in cui gli asset sono valutati al prezzo di acquisto (nessun prezzo di mercato in tempo reale), NAV ≈ Costo degli Asset. Il divario tra NAV e Capitale Depositato potrebbe non essere visibile come gap nel grafico, ma il **P&L Totale** nel suggerimento mostra il valore corretto.

    Quando reinvesti tutti i rendimenti in nuovi asset, l'area dei Rendimenti rimane vicina allo zero e il reddito guadagnato finisce incorporato nell'area del Costo degli Asset. Questo è matematicamente corretto: la tua base di costo è cresciuta perché hai reinvestito i profitti.

🔗 **Teoria**: [Capitale Depositato e P&L Totale](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) · [Scomposizione della Cassa](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md#three-pool-cash-model)

### Modalità % — tasso di rendimento

Tutte le serie partono da 0% all'inizio del periodo selezionato e mostrano come ciascuna metrica di rendimento è evoluta:

| Serie | Cosa mostra |
|--------|--------------|
| **[MWRR cumulativo](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Il tuo rendimento personale ponderato per il denaro, inclusa la tempistica dei depositi |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Rendimento puro della strategia sugli asset, ignorando quando hai depositato |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Rendimento lordo sul capitale netto investito |

Il divario tra MWRR e TWRR è l'[Effetto di Tempistica](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

!!! note "MWRR non disponibile"

    Se appare un banner sulla **Qualità dei Dati** che indica che il MWRR è inaffidabile, la serie MWRR viene nascosta dal grafico %. Il problema si verifica tipicamente quando il periodo ha flussi di cassa molto grandi rispetto alla dimensione iniziale del portafoglio, causando l'instabilità del risolutore matematico. ROI e TWRR vengono sempre mostrati.

---

## 🥧 Pannello di Allocazione {: #allocation-panel }

Il pannello di allocazione mostra come il tuo portafoglio è distribuito al momento attuale e come si è evoluto storicamente.

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

### Tre dimensioni

| Dimensione | Cosa mostra |
|-----------|--------------|
| **Tipo** | ETF, Azioni, Obbligazioni, Crypto, Immobiliare, Liquidità (contante) |
| **Settore** | Settore industriale: 💻 Tecnologia, 🏦 Finanziario, 💊 Sanità, ecc. |
| **Geografia** | Paese o regione della quotazione primaria di ciascun asset |

### Schede Ora vs. Storico

- **Ora** — Grafico a ciambella dell'allocazione corrente alla `date_to`. Passa il mouse su una fetta per vedere la percentuale esatta e il valore assoluto.
- **Storico** — Grafico ad area impilata al 100% che mostra come l'allocazione è cambiata nel tempo. Utile per visualizzare il ribilanciamento del portafoglio tra mesi o anni.

### Contante come Liquidità

Il **Contante** (il saldo del tuo broker) appare sempre come la fetta **Liquidità** sia nella vista Tipo che in quella Settore. Nella mappa geografica, il contante non è assegnato a nessun paese e non appare.

!!! info "Ambito del broker"

    Quando filtri per broker specifici, l'allocazione mostra solo gli asset e il contante all'interno di tali broker.

---

## 🔗 Correlati

- 💰 **[Schede KPI](kpi-cards.md)** — Patrimonio Netto, P&L del Periodo, Rendimenti
- 💼 **[NAV / Patrimonio Netto](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 💸 **[Capitale Depositato e P&L Totale](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** · **[Effetto di Tempistica](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
