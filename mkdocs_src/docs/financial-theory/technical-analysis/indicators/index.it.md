# 📉 Indicatori Tecnici

LibreFolio espone **22 indicatori tecnici calcolati lato backend**, raggruppati per la proprietà di mercato che misurano. Gli stessi contratti matematici alimentano i grafici degli asset, i grafici FX compatibili, le annotazioni e i consumatori analitici come AI Export.

Gli indicatori contano le **sedute**, non i giorni di calendario: una seduta è un giorno in cui la serie ha una quotazione propria — un prezzo per un asset, un tasso di cambio pubblicato per una coppia FX. Un giorno che la serie riempie con l'ultimo valore noto — un fine settimana, una festività di mercato, qualsiasi giorno senza quotazione — non è una seduta, e non lo è nemmeno un prezzo memorizzato con data in un fine settimana o in una festività di mercato che ripete soltanto la chiusura precedente (un [carry memorizzato](../risk-metrics/data-quality.md#stored-carries)). Anche i periodi, il warm-up e la storia minima si contano in sedute, quindi la SMA 200 calcola la media delle ultime 200 sedute, circa 290 giorni di calendario. Il grafico mantiene le proprie date di calendario: un indicatore ha valori solo nelle sedute e la sua linea collega i giorni di chiusura intermedi. La famiglia Rischio calcola le proprie finestre in modo diverso. Volatilità rolling, Indice di Sharpe rolling e Beta rolling contano le **osservazioni di rendimento** della serie di rendimenti preparata per l'asset: un rendimento per seduta, misurato rispetto alla seduta precedente — per Beta rolling, per ciascuna data del [calendario congiunto](../risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs) dei due asset — quindi una finestra di $w$ considera $w$ rendimenti ricavati da $w + 1$ prezzi. **Rendimento rolling** conta i **giorni di calendario**: confronta ogni data con la chiusura risolta esattamente $N$ giorni di calendario prima ([Rendimento rolling](../../fundamentals/returns.md#rolling-return-calendar)), lo stesso calcolo della [modalità Rendimento rolling](../../../user/assets/detail/chart.md#primary-modes) del grafico.

!!! info "I campi di prezzo sono importanti"

    Non tutti gli indicatori possono essere eseguiti su ogni serie. **9 dei 22** sono
    indicatori basati solo sulla chiusura e funzionano sia sugli asset sia sui tassi di cambio (EMA, SMA, KAMA, MACD, RSI,
    ROC, PPO, Stochastic RSI, Bollinger Bands). Gli indicatori che richiedono i campi high, low o
    volume sono disponibili solo per gli asset e si dichiarano non disponibili quando quei campi
    non esistono. Anche la famiglia **Rischio** è disponibile solo per gli asset: le letture di rischio rolling non
    vengono prodotte per le coppie FX.

---

## 📈 Trend

Gli indicatori di trend smussano il prezzo o misurano se un movimento direzionale è stabilito.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **EMA** | Dove si trova il trend ponderato recente? | Close | [📖](ema.md) |
| **SMA** | Qual è il prezzo medio a pesi uguali? | Close | [📖](sma.md) |
| **KAMA** | Come dovrebbe adattarsi lo smoothing al rumore? | Close | [📖](kama.md) |
| **ADX** | Quanto è forte il trend? | High, Low, Close | [📖](adx.md) |
| **Aroon** | Quanto di recente si sono verificati nuovi estremi? | High, Low | [📖](aroon.md) |

➡️ [Panoramica del gruppo Trend](trend.md)

---

## ⚡ Momentum

Gli indicatori di momentum misurano velocità, pressione direzionale e accelerazione.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **RSI** | Stanno dominando i compratori o i venditori? | Close | [📖](rsi.md) |
| **MACD** | Il momentum del trend sta accelerando? | Close | [📖](macd.md) |
| **ROC** | Quanto velocemente è cambiato il prezzo? | Close | [📖](roc.md) |
| **Stochastic RSI** | Dove si trova l'RSI all'interno del suo intervallo recente? | Close | [📖](stochastic-rsi.md) |
| **PPO** | Qual è il momentum della media mobile in termini percentuali? | Close | [📖](ppo.md) |
| **CCI** | Quanto è lontano il prezzo dalla sua media statistica recente? | High, Low, Close | [📖](cci.md) |

➡️ [Panoramica del gruppo Momentum](momentum.md)

---

## 🌊 Volatilità

Gli indicatori di volatilità misurano intervallo, dispersione e ampiezza del canale anziché la direzione.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **Bollinger Bands** | Quanto è ampio l'involucro statistico del prezzo? | Close | [📖](bollinger-bands.md) |
| **ATR** | Quanto è ampio il true range tipico? | High, Low, Close | [📖](atr.md) |
| **NATR** | Quanto è ampia la volatilità rispetto al prezzo? | High, Low, Close | [📖](natr.md) |
| **Donchian Channels** | Quali sono il massimo più alto e il minimo più basso del periodo? | High, Low | [📖](donchian-channels.md) |

➡️ [Panoramica del gruppo Volatilità](volatility.md)

---

## 📊 Volume

Gli indicatori di volume combinano la direzione del prezzo con l'attività di negoziazione.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **OBV** | Il volume con segno si sta accumulando o distribuendo? | Close, Volume | [📖](obv.md) |
| **MFI** | Il money flow è pressione di acquisto o di vendita? | High, Low, Close, Volume | [📖](mfi.md) |

➡️ [Panoramica del gruppo Volume](volume.md)

---

## ⚠️ Rischio

Gli indicatori di rischio trasformano la serie di prezzi stessa in una lettura di rischio rolling. Sono **solo per gli asset** — le coppie FX non li producono.

| Indicatore | Domanda principale | Dati | Dettagli |
|---|---|---|---|
| **Drawdown sotto il picco** | Quanto dista il prezzo dal picco progressivo? | Close | [📖](../risk-metrics/current-drawdown.md) |
| **Rendimento rolling** | Quanto si è mosso il prezzo negli ultimi $N$ giorni di calendario? | Close | [📖](../../fundamentals/returns.md#rolling-return) |
| **Volatilità rolling** | Quanto sono dispersi i rendimenti recenti? | Close | [📖](../risk-metrics/volatility.md) |
| **Indice di Sharpe rolling** | Il rendimento in eccesso sta ripagando il proprio rischio? | Close | [📖](../risk-metrics/sharpe-ratio.md) |
| **Beta rolling** | Quanto è sensibile l'asset a un asset di confronto? | Close + asset di confronto | [📖](../risk-metrics/beta-active-return.md) |

➡️ [Panoramica delle metriche di rischio](../risk-metrics/index.md)

---

## 🔗 Correlati

- 🎯 **[Benchmark sintetici](../synthetic-benchmarks/index.md)** — Curve di riferimento matematiche
- 📈 **[Grafico interattivo](../../../user/assets/detail/chart.md)** — Dove vengono visualizzati gli indicatori
- 📊 **[Segnali](../../../user/assets/detail/signals.md)** — Come configurare gli overlay in LibreFolio
