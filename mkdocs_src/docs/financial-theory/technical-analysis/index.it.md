# 📊 Analisi Tecnica

L'analisi tecnica studia i **pattern di prezzo e le dinamiche di mercato** per identificare trend, momentum e volatilità. A differenza dell'analisi fondamentale (che valuta il valore intrinseco di un'azienda), l'analisi tecnica si concentra esclusivamente sui dati storici di prezzo e volume.

---

## 📖 Contenuti

### 📉 [Indicatori](indicators/index.md)

Indicatori overlay che estraggono informazioni su trend, momentum o volatilità dai dati di prezzo. LibreFolio implementa quattro indicatori principali, ciascuno spiegato sia da una prospettiva **finanziaria** che di **elaborazione dei segnali**:

- **[EMA](indicators/ema.md)** — Media Mobile Esponenziale (tracciamento del trend)
- **[MACD](indicators/macd.md)** — Moving Average Convergence Divergence (momentum)
- **[RSI](indicators/rsi.md)** — Indice di Forza Relativa (ipercomprato/ipervenduto)
- **[Bande di Bollinger](indicators/bollinger-bands.md)** — Involucro di volatilità adattivo

### 🎯 [Benchmark Sintetici](synthetic-benchmarks/index.md)

Curve di riferimento matematiche sovrapposte ai grafici per il confronto. A differenza degli indicatori (calcolati *dai* dati di mercato), i benchmark sono generati esclusivamente a partire da parametri:

- **[Crescita Lineare](synthetic-benchmarks/linear.md)** — Modello a interesse semplice
- **[Crescita Composta](synthetic-benchmarks/compound.md)** — Modello a interesse composto
- **[Onda Sinusoidale](synthetic-benchmarks/sine-wave.md)** — Riferimento ciclico per la stagionalità

---

## ⚡ L'intuizione "Veloce" vs "Lenta"

In finanza, *veloce* e *lento* si riferiscono alla **costante di tempo** ($\tau$) del filtro sottostante.

| Proprietà | Veloce ($N$ piccolo) | Lento ($N$ grande) |
|---|---|---|
| Frequenza di taglio $f_c$ | Più alta | Più bassa |
| Reiezione del rumore | Scarsa — lascia passare le alte frequenze | Buona — forte smorzamento |
| Ritardo di fase | Piccolo — reagisce rapidamente | Grande — ritardo significativo |
| $N$ tipico | 9, 12, 14 | 26, 50, 200 |

---

## 🔗 Sezioni Correlate

- 🏦 **[Strumenti](../instruments/index.md)** — Gli asset che questi indicatori analizzano
- 📐 **[Fondamentali](../fundamentals/index.md)** — Rendimenti, convenzioni di conteggio dei giorni
- 📈 **[Teoria di Portafoglio](../portfolio-theory/index.md)** — Metriche di rischio e allocazione
