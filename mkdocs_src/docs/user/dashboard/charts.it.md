# 📊 Grafici

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*

La sezione dei grafici si trova sotto le schede KPI e fornisce una **vista storica e strutturale** del tuo portafoglio nell'intervallo di tempo selezionato.

---

## 📈 Grafico di Crescita del Portafoglio

Il grafico di crescita mostra come il valore del tuo portafoglio si è evoluto nel periodo selezionato. Usa l'interruttore **Abs / %** nell'angolo in alto a destra per passare tra le due visualizzazioni.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Modalità Assoluta" alt="Grafico di Crescita — Modalità Assoluta">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Modalità Percentuale" alt="Grafico di Crescita — Modalità Percentuale">
</div>

### Modalità ABS — valori assoluti

Il grafico utilizza un design a **aree sovrapposte + linee di overlay**:

| Elemento | Colore | Significato |
|---------|-------|---------|
| Area — **Costo asset** | Blu | Base di costo di tutte le posizioni aperte (costo medio × quantità) |
| Area — **Rendimenti** | Smeraldo | Rendimenti del portafoglio detenuti come liquidità (interessi, guadagni realizzati non ancora reinvestiti) |
| Area — **Capitale** | Grigio-verde | Depositi non investiti detenuti in contanti |
| Linea — **[NAV](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Verde scuro continua | Valore totale del portafoglio ai prezzi di mercato attuali |
| Linea — **[Capitale Depositato](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Grigio tratteggiata | Capitale esterno netto versato nel tempo |

**Il divario tra la linea NAV e la linea del Capitale Depositato = P&L Totale** — tutti i guadagni mai generati, inclusi i guadagni non realizzati, i guadagni realizzati, gli interessi e i dividendi, meno commissioni e tasse.

#### Dettaglio del suggerimento

Passando il mouse sopra il grafico, il suggerimento mostra:

- **NAV** — valore totale del portafoglio in quella data
- **Capitale Depositato** — capitale netto versato fino a quella data
- **P&L Totale** — la differenza (NAV − Capitale Depositato)
- **Costo asset** / **Rendimenti** / **Capitale** — le tre componenti di liquidità

!!! tip "Leggere portafogli basati sul reddito (P2P, obbligazioni)"

    Per portafogli come il P2P lending, dove gli asset sono valutati al loro prezzo di acquisto (senza prezzo di mercato in tempo reale), NAV ≈ Costo asset. Il divario tra NAV e Capitale Depositato potrebbe non essere visibile come un distacco grafico, ma il suggerimento **P&L Totale** mostra il valore corretto.

    Quando reinvesti tutti i rendimenti in nuovi asset, l'area Rendimenti rimane vicina allo zero e il reddito guadagnato finisce per essere incorporato nell'area Costo asset. Questo è matematicamente corretto: la tua base di costo è cresciuta perché hai reinvestito il profitto.

🔗 **Teoria**: [Capitale Depositato & P&L Totale](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) · [Decomposizione della Liquidità](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md#modello-di-liquidita-a-tre-pool)

### Modalità % — tasso di rendimento

Tutte le serie partono dallo 0% all'inizio del periodo selezionato e mostrano come si è evoluta ogni metrica di rendimento:

| Serie | Cosa mostra |
|--------|--------------|
| **[MWRR cumulativo](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Il tuo rendimento personale ponderato per il capitale, inclusa la tempistica dei depositi |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Rendimento puro della strategia degli asset, ignorando quando hai effettuato i depositi |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Rendimento grezzo sul capitale netto investito |

Il divario tra MWRR e TWRR è l'[Effetto Timing](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

!!! note "MWRR non disponibile"

    Se appare un **banner di Qualità dei Dati** che indica che l'MWRR non è affidabile, la serie MWRR viene nascosta dal grafico %. Il problema si verifica tipicamente quando il periodo presenta flussi di cassa molto grandi rispetto alla dimensione iniziale del portafoglio, rendendo instabile il risolutore matematico. ROI e TWRR sono sempre mostrati.

---

## 🥧 Pannello di Allocazione

Il pannello di allocazione mostra come il tuo portafoglio è distribuito al momento attuale e come si è evoluto storicamente.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="allocation-type-now" data-title="Per Tipo (Attuale)" alt="Allocazione per Tipo — Attuale">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-sector-now" data-title="Per Settore (Attuale)" alt="Allocazione per Settore — Attuale">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-geo-now" data-title="Per Geografia (Attuale)" alt="Allocazione per Geografia — Attuale">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-history" data-title="Per Tipo (Storico)" alt="Storico Allocazione per Tipo">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-sector-history" data-title="Per Settore (Storico)" alt="Storico Allocazione per Settore">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-geo-history" data-title="Per Geografia (Storico)" alt="Storico Allocazione per Geografia">
</div>

### Tre dimensioni

| Dimensione | Cosa mostra |
|-----------|--------------|
| **Tipo** | ETF, Azioni, Obbligazioni, Crypto, Immobiliare, Liquidità (cash) |
| **Settore** | Settore industriale: 💻 Tecnologia, 🏦 Settore Finanziario, 💊 Sanità, ecc. |
| **Geografia** | Paese o regione del listing principale di ogni asset |

### Schede Attuale vs Cronologia

- **Attuale** — Grafico a ciambella dell'allocazione corrente alla data `date_to`. Passa il mouse su qualsiasi fetta per vedere la percentuale esatta e il valore assoluto.
- **Cronologia** — Grafico ad area sovrapposta al 100% che mostra come l'allocazione è cambiata nel tempo. Utile per visualizzare il ribilanciamento del portafoglio attraverso mesi o anni.

### Cash come Liquidità

Il **Cash** (il tuo saldo presso il broker) appare sempre come la fetta **Liquidità** sia nella vista per Tipo che in quella per Settore. Nella mappa Geografica, il cash non è assegnato a nessun paese e non appare.

!!! info "Ambito del Broker"

    Quando filtri per broker specifici, l'allocazione mostra solo gli asset e la liquidità all'interno di quei broker.

---

## 🔗 Correlati

- 💰 **[Schede KPI](kpi-cards.md)** — Net Worth, P&L del Periodo, Rendimenti
- 💼 **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 💸 **[Capitale Depositato & P&L Totale](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** · **[Effetto Timing](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
