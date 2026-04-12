# 📉 Indicatori Tecnici

LibreFolio fornisce quattro indicatori tecnici come overlay sul grafico. Ogni indicatore è spiegato da due prospettive complementari: l'interpretazione **finanziaria** che i trader utilizzano quotidianamente e l'equivalente di **elaborazione dei segnali** che gli ingegneri riconosceranno istantaneamente.

!!! info "Perché due prospettive?"

    I mercati finanziari **non** sono sistemi LTI (Linear Time-Invariant) stazionari:
    sono rumorosi, caotici e il loro contenuto spettrale cambia nel tempo. Tuttavia, gli
    strumenti matematici che applichiamo per estrarre trend, momentum o volatilità
    sono *esattamente* gli stessi filtri a tempo discreto insegnati in qualsiasi corso
    di elaborazione dei segnali.

---

## 📋 Panoramica Indicatori

| Indicatore | Cosa Misura | Uso Principale | Dettagli |
|-----------|-----------------|---------|---------|
| **EMA** | Direzione del trend | Rilevamento della Golden/Death Cross | [📖](ema.md) |
| **MACD** | Momentum / accelerazione del trend | Crossover rialzisti/ribassisti | [📖](macd.md) |
| **RSI** | Ipercomprato / ipervenduto | Setup di mean-reversion | [📖](rsi.md) |
| **Bollinger Bands** | Inviluppo di volatilità | Squeeze → rilevamento breakout | [📖](bollinger-bands.md) |

---

## 🔗 Correlati

- 🎯 **[Benchmark Sintetici](../synthetic-benchmarks/index.md)** — Curve di riferimento matematiche
- 📈 **[Grafico Interattivo](../../../user/assets/detail/chart.md)** — Dove vengono visualizzati gli indicatori
- 📊 **[Segnali](../../../user/assets/detail/signals.md)** — Come configurare gli overlay in LibreFolio
