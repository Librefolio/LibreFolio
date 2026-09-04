# 📉 Indicatori Tecnici

LibreFolio espone **17 indicatori tecnici calcolati dal backend**, raggruppati per la proprietà di mercato che misurano. Gli stessi contratti matematici alimentano i grafici degli Asset, i grafici FX compatibili, le annotazioni e i futuri consumatori analitici.

!!! info "I campi prezzo contano"

    Non tutti gli indicatori possono funzionare su tutte le serie. Gli indicatori basati solo sul Close funzionano su Asset
    e tassi FX; gli indicatori che richiedono High, Low o Volume sono solo per Asset e si segnalano
    come non disponibili in assenza di questi campi.

---

## 📈 Trend

Gli indicatori di Trend attenuano il prezzo o misurano se un movimento direzionale è consolidato.

| Indicatore | Domanda Principale | Dati | Dettagli |
|---|---|---|---|
| **EMA** | Dov'è il trend ponderato recente? | Close | [📖](ema.md) |
| **SMA** | Qual è il prezzo medio a pari peso? | Close | [📖](sma.md) |
| **KAMA** | Come dovrebbe adattarsi l'attenuazione al rumore? | Close | [📖](kama.md) |
| **ADX** | Quanto è forte il trend? | High, Low, Close | [📖](adx.md) |
| **Aroon** | Quanto recentemente si sono verificati nuovi estremi? | High, Low | [📖](aroon.md) |

➡️ [Panoramica del gruppo Trend](trend.md)

---

## ⚡ Momentum

Gli indicatori di Momentum misurano velocità, pressione direzionale e accelerazione.

| Indicatore | Domanda Principale | Dati | Dettagli |
|---|---|---|---|
| **RSI** | Dominano i compratori o i venditori? | Close | [📖](rsi.md) |
| **MACD** | L'impulso del trend sta accelerando? | Close | [📖](macd.md) |
| **ROC** | Quanto velocemente è cambiato il prezzo? | Close | [📖](roc.md) |
| **Stochastic RSI** | Dove si trova l'RSI all'interno del suo range recente? | Close | [📖](stochastic-rsi.md) |
| **PPO** | Qual è l'impulso della media mobile in termini percentuali? | Close | [📖](ppo.md) |
| **CCI** | Quanto è distante il prezzo dalla sua media statistica recente? | High, Low, Close | [📖](cci.md) |

➡️ [Panoramica del gruppo Momentum](momentum.md)

---

## 🌊 Volatilità

Gli indicatori di Volatilità misurano il range, la dispersione e l'ampiezza del canale piuttosto che la direzione.

| Indicatore | Domanda Principale | Dati | Dettagli |
|---|---|---|---|
| **Bande di Bollinger** | Quanto è ampio l'involucro statistico del prezzo? | Close | [📖](bollinger-bands.md) |
| **ATR** | Quanto è ampio il tipico true range? | High, Low, Close | [📖](atr.md) |
| **NATR** | Quanto è ampia la volatilità rispetto al prezzo? | High, Low, Close | [📖](natr.md) |
| **Canali di Donchian** | Quali sono il massimo più alto e il minimo più basso del periodo? | High, Low | [📖](donchian-channels.md) |

➡️ [Panoramica del gruppo Volatilità](volatility.md)

---

## 📊 Volume

Gli indicatori di Volume combinano la direzione del prezzo con l'attività di trading.

| Indicatore | Domanda Principale | Dati | Dettagli |
|---|---|---|---|
| **OBV** | Il volume firmato sta accumulando o distribuendo? | Close, Volume | [📖](obv.md) |
| **MFI** | Il flusso di denaro è una pressione di acquisto o di vendita? | High, Low, Close, Volume | [📖](mfi.md) |

➡️ [Panoramica del gruppo Volume](volume.md)

---

## 🔗 Correlati

- 🎯 **[Benchmark Sintetici](../synthetic-benchmarks/index.md)** — Curve di riferimento matematiche
- 📈 **[Grafico Interattivo](../../../user/assets/detail/chart.md)** — Dove vengono visualizzati gli indicatori
- 📊 **[Segnali](../../../user/assets/detail/signals.md)** — Come configurare le sovrapposizioni in LibreFolio
