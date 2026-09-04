# 📉 Indicatori Tecnici

LibreFolio espone **22 indicatori tecnici calcolati dal backend**, raggruppati per la proprietà di mercato che misurano. Gli stessi contratti matematici alimentano i grafici degli Asset, i grafici FX compatibili, le annotazioni e i consumatori analitici come AI Export.

!!! info "I campi dei prezzi sono importanti"

    Non tutti gli indicatori possono essere applicati a ogni serie. **9 dei 22**
    sono indicatori basati solo sulla chiusura e funzionano sia sugli Asset sia
    sui tassi di cambio (EMA, SMA, KAMA, MACD, RSI, ROC, PPO, RSI stocastico, Bande di
    Bollinger). Gli indicatori che richiedono massimi, minimi o volume sono
    disponibili solo per gli Asset e si dichiarano non disponibili quando questi
    campi non esistono. La famiglia **Rischio** è anch'essa disponibile solo per
    gli Asset: le letture di rischio rolling non vengono prodotte per le coppie FX.

---

## 📈 Tendenza

Gli indicatori di tendenza livellano il prezzo o misurano se un movimento direzionale è consolidato.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **EMA** | Dove si colloca la tendenza ponderata recente? | Chiusura | [📖](ema.md) |
| **SMA** | Qual è il prezzo medio con pesi uguali? | Chiusura | [📖](sma.md) |
| **KAMA** | Come dovrebbe adattarsi il livellamento al rumore? | Chiusura | [📖](kama.md) |
| **ADX** | Quanto è forte la tendenza? | Massimo, Minimo, Chiusura | [📖](adx.md) |
| **Aroon** | Quanto di recente si sono verificati nuovi estremi? | Massimo, Minimo | [📖](aroon.md) |

➡️ [Panoramica del gruppo Tendenza](trend.md)

---

## ⚡ Momentum

Gli indicatori di momentum misurano velocità, pressione direzionale e accelerazione.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **RSI** | Stanno dominando gli acquirenti o i venditori? | Chiusura | [📖](rsi.md) |
| **MACD** | Il momentum della tendenza sta accelerando? | Chiusura | [📖](macd.md) |
| **ROC** | Quanto velocemente è cambiato il prezzo? | Chiusura | [📖](roc.md) |
| **RSI stocastico** | Dove si trova l'RSI all'interno del suo range recente? | Chiusura | [📖](stochastic-rsi.md) |
| **PPO** | Qual è il momentum delle medie mobili in termini percentuali? | Chiusura | [📖](ppo.md) |
| **CCI** | Quanto dista il prezzo dalla sua media statistica recente? | Massimo, Minimo, Chiusura | [📖](cci.md) |

➡️ [Panoramica del gruppo Momentum](momentum.md)

---

## 🌊 Volatilità

Gli indicatori di volatilità misurano il range, la dispersione e l'ampiezza del canale, piuttosto che la direzione.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **Bande di Bollinger** | Quanto è ampio l'inviluppo statistico del prezzo? | Chiusura | [📖](bollinger-bands.md) |
| **ATR** | Quanto è ampio il tipico range reale? | Massimo, Minimo, Chiusura | [📖](atr.md) |
| **NATR** | Quanto è ampia la volatilità rispetto al prezzo? | Massimo, Minimo, Chiusura | [📖](natr.md) |
| **Canali di Donchian** | Quali sono il massimo dei massimi e il minimo dei minimi del periodo? | Massimo, Minimo | [📖](donchian-channels.md) |

➡️ [Panoramica del gruppo Volatilità](volatility.md)

---

## 📊 Volume

Gli indicatori di volume combinano la direzione del prezzo con l'attività di negoziazione.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **OBV** | Il volume con segno sta accumulando o distribuendo? | Chiusura, Volume | [📖](obv.md) |
| **MFI** | Il flusso di denaro rappresenta una pressione di acquisto o di vendita? | Massimo, Minimo, Chiusura, Volume | [📖](mfi.md) |

➡️ [Panoramica del gruppo Volume](volume.md)

---

## ⚠️ Rischio

Gli indicatori di rischio trasformano la serie dei prezzi stessa in una lettura di rischio rolling. Sono **disponibili solo per gli Asset** — le coppie FX non producono queste letture.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **Drawdown sott'acqua** | Di quanto il prezzo è al di sotto del massimo progressivo? | Chiusura | [📖](../risk-metrics/max-drawdown.md) |
| **Rendimento rolling** | A quanto ammonta il rendimento composto dell'ultima finestra? | Chiusura | [📖](../../fundamentals/returns.md) |
| **Volatilità rolling** | Quanto sono dispersi i rendimenti recenti? | Chiusura | [📖](../risk-metrics/volatility.md) |
| **Rapporto di Sharpe rolling** | Il rendimento in eccesso compensa il rischio corso? | Chiusura | [📖](../risk-metrics/sharpe-ratio.md) |
| **Beta rolling** | Quanto è sensibile l'asset a un asset di confronto? | Chiusura + asset di confronto | — |

➡️ [Panoramica delle metriche di rischio](../risk-metrics/index.md)

---

## 🔗 Correlati

- 🎯 **[Benchmark sintetici](../synthetic-benchmarks/index.md)** — Curve di riferimento matematiche
- 📈 **[Grafico interattivo](../../../user/assets/detail/chart.md)** — Dove vengono visualizzati gli indicatori
- 📊 **[Segnali](../../../user/assets/detail/signals.md)** — Come configurare le sovrapposizioni in LibreFolio
