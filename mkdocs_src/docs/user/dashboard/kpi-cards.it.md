# 💰 Schede KPI

*[⬅️ Torna alla Panoramica Dashboard](index.md)*

Le tre schede KPI nella parte superiore della dashboard forniscono una rapida diagnosi del tuo portafoglio. Tutti i valori rispettano l'**intervallo temporale e l'ambito del broker** selezionati in alto nella pagina.

---

## 💰 Scheda 1 — Net Worth

La scheda **Net Worth** mostra il valore assoluto del tuo portafoglio alla fine del periodo selezionato.

### Significato delle righe

| Riga | Definizione |
|-----|-----------|
| **[Market Value](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Prezzo di mercato attuale × quantità per tutti gli asset detenuti |
| **[Book Value](../../financial-theory/technical-analysis/performance-metrics/book-value.md)** | Quanto hai pagato per le tue posizioni aperte (costo medio × qty) |
| **Cash** | Saldo liquido detenuto nei conti del broker |
| **[Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Contributo netto di capitale esterno in questo ambito |

### La barra del Deposited Capital

La barra orizzontale sotto le righe visualizza:

- 🟢 **Total deposited** — tutti i depositi nel periodo
- 🔴 **Total withdrawn** — tutti i prelievi nel periodo

Il valore principale mostra il saldo netto (depositati − prelevati).

!!! info "Istantanea vs periodo"

    Market Value, Book Value e Cash sono **istantanee** alla data di fine — sono indipendenti dalla data di inizio.
    Deposited Capital è **relativo al periodo** — conteggia i depositi e i prelievi tra l'inizio e la fine dell'intervallo selezionato.

---

## 📉 Scheda 2 — Period P&L

La scheda **Period P&L** mostra quanto denaro il tuo portafoglio ha effettivamente *guadagnato* nella finestra selezionata — dopo aver rimosso l'effetto dei tuoi depositi e prelievi.

Il valore principale utilizza la formula:

> **NAV fine** − **NAV inizio** − **Flussi Esterni Netti nel periodo**

Un numero positivo significa che hai guadagnato denaro dall'attività di investimento. Un numero negativo significa che hai perso denaro al netto dei movimenti di capitale.

### Le righe di dettaglio

| Riga | Cosa misura |
|-----|-----------------|
| **Unrealized change** | Di quanto è variato il [guadagno/perdita non realizzato](../../financial-theory/technical-analysis/performance-metrics/book-value.md) delle tue posizioni aperte durante il periodo |
| **Sales** | Guadagno o perdita realizzato dalle posizioni chiuse durante il periodo (prezzo di vendita − costo medio) |
| **Dividends & interest** | Reddito in contanti da dividendi, cedole obbligazionarie e interessi P2P |
| **Fees & taxes** | Commissioni e tasse registrate come transazioni |

!!! tip "Verifica di identità"

    Tutte e quattro le righe sommate corrispondono al valore principale del Period P&L (± piccoli residui dovuti all'arrotondamento FX).

🔗 **Teoria**: [Period P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md) · [Book Value / PMC](../../financial-theory/technical-analysis/performance-metrics/book-value.md)

---

## 📈 Scheda 3 — Returns

La scheda **Returns** mostra metriche di *tasso di rendimento* — percentuali che ti permettono di confrontare le performance indipendentemente dalla dimensione del portafoglio.

### Timing Effect

Il **Timing Effect** nella parte superiore della scheda misura se le tue decisioni di deposito/prelievo hanno *aggiunto* o *sottratto* valore rispetto a una strategia passiva di buy-and-hold.

> **Timing Effect** = MWRR cumulativo − TWRR cumulativo

- **Favorevole (positivo)** ✅: hai tendenzialmente depositato quando i prezzi erano bassi, aumentando il tuo rendimento personale oltre a quanto guadagnato dai soli asset.
- **Sfavorevole (negativo)** ❌: hai tendenzialmente depositato ai picchi o hai mancato i minimi, trascinando il tuo rendimento al di sotto della pura performance degli asset.

### Le quattro metriche di rendimento

| Metrica | Domanda a cui risponde |
|--------|---------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Quanto ho guadagnato rispetto al mio capitale netto investito? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Come hanno performato le mie scelte di asset, indipendentemente da quando ho depositato? |
| **[MWRR cumulative](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Qual è il rendimento cumulativo ponderato per il capitale (MWRR) per i miei flussi di cassa effettivi? |
| **[MWRR annualized](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | A quale tasso composto annuo è effettivamente cresciuto il mio capitale? |

!!! note "TWRR vs. MWRR"

    - **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** misura la **strategia degli asset** — lo stesso modo in cui viene valutato un gestore di fondi.
    - **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** misura il **tuo risultato personale** — incluso il timing dei tuoi depositi.
    - Il divario tra i due è il [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

---

## 🔗 Correlati

- 💼 **[NAV / Net Worth](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 📚 **[Book Value](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- 📊 **[Period P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- 💸 **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)**
- ⏱️ **[Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
