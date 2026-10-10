# 📊 Segnali

I segnali sono linee disegnate sopra il grafico dei prezzi: **indicatori tecnici** che LibreFolio calcola dai prezzi memorizzati, **un altro asset o una coppia FX** con cui confrontarsi, e **curve di riferimento** come una crescita costante. Usali per leggere a colpo d'occhio trend, momentum, volatilità e rischio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Pannello dei segnali dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Aggiungere un segnale

1. Apri il pannello **Segnali** sopra il grafico.
2. Scegli un segnale da uno dei suoi tre menu: **Indicatori tecnici**, **Confronto dati** o **Benchmark sintetici**. Nel menu degli indicatori, digita per cercare per nome, descrizione o per i dati usati da un indicatore.
3. Imposta i suoi parametri sulla scheda che appare; il grafico si aggiorna.
4. Trascina una scheda dalla sua maniglia (frecce su un telefono) per cambiarne l'ordine, oppure rimuovila con 🗑️.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Ricerca degli indicatori per gruppo nel pannello dei segnali dell'asset">
</div>

Ogni linea di una scheda, e ogni zona di indicatori come RSI, ha il proprio colore e stile di linea. I tuoi segnali vengono ricordati per questo asset, in questo browser.

---

## 📉 Indicatori tecnici {: #technical-indicators }

**22 indicatori**, raggruppati in base a ciò che misurano. Ogni nome rimanda alla sua pagina teorica; il **?** su una scheda apre la stessa pagina.

### 📈 Trend

- [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) — media semplice dei prezzi di chiusura
- [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) — media che pesa maggiormente i prezzi recenti
- [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) — media che si adatta al rumore di mercato
- [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) — forza del trend, con +DI e −DI per la sua direzione
- [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) — quanto sono recenti gli ultimi massimi e minimi

### ⚡ Momentum

- [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) — pressione di acquisto e vendita, con zone di ipercomprato e ipervenduto
- [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) — momentum tra due medie mobili, con una linea di segnale e un istogramma
- [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) — lo stesso momentum, in percentuale
- [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) — velocità della variazione del prezzo
- [Stochastic RSI](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) — dove si colloca l'RSI all'interno del suo intervallo recente
- [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) — distanza dal prezzo medio

### 🌊 Volatilità

- [Bollinger Bands](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) — una banda attorno a una media mobile che si allarga con la volatilità
- [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) — volatilità in unità di prezzo
- [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) — volatilità in percentuale del prezzo
- [Donchian Channels](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) — il massimo più alto e il minimo più basso del periodo

### 📊 Volume

- [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) — pressione del volume dietro i movimenti di prezzo
- [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) — momentum ponderato per il volume

### ⚠️ Rischio

- [Drawdown sotto il picco](../../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md) — quanto il prezzo è sotto il suo massimo progressivo ([cronologia completa](#drawdown-full-history))
- [Rolling Return](../../../financial-theory/fundamentals/returns.md#rolling-return-sessions) — rendimento solo-prezzo su una finestra mobile
- [Volatilità rolling](../../../financial-theory/technical-analysis/risk-metrics/volatility.md) — volatilità annualizzata su una finestra mobile
- [Indice di Sharpe rolling](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md) — rendimento in eccesso per unità di volatilità su una finestra mobile
- [Beta rolling](../../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md) — quanto fortemente l'asset segue un asset di confronto che scegli

I periodi sono contati in **sedute**, i giorni in cui l'asset è stato quotato: una SMA 200 copre 200 sedute, circa 290 giorni di calendario ([perché](../../../financial-theory/technical-analysis/indicators/index.md)). La **Finestra** dei quattro segnali di rischio rolling conta anch'essa i giorni con una quotazione; per il Beta rolling, i giorni in cui entrambi gli asset sono stati quotati.

!!! info "Non tutti gli indicatori possono funzionare su ogni asset"

    ADX, Aroon, ATR, NATR, CCI, Donchian Channels e MFI richiedono i prezzi **high** e **low**; OBV e MFI richiedono il **volume**. In loro assenza, la scheda ti indica quali dati mancano.

### 📉 Drawdown sull'intera cronologia {: #drawdown-full-history }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Scheda del segnale Drawdown con l'interruttore Storia completa">
</div>

La scheda **Drawdown sotto il picco** ha una casella di controllo **Cronologia completa**, attiva per impostazione predefinita: il calo è misurato dal massimo progressivo dell'intera cronologia dell'asset, anche anni prima delle date sullo schermo. Deselezionala per una vista più rapida, misurata dal massimo progressivo all'interno delle date sullo schermo.

---

## 💱 Confronta con un asset o una coppia FX {: #data-comparison }

Il menu **Confronto dati** aggiunge:

- **Confronto asset** — un altro asset sullo stesso grafico, come un'azione rispetto al suo ETF di indice. Nella vista **%** entrambe le linee partono da 0 %.
- **Coppia FX** — il tasso di una delle tue coppie FX.

**Sincronizza** (🔄) su una scheda di Confronto asset scarica i prezzi di quell'asset per le date del grafico, insieme ai tassi di cambio che lo convertono, per le coppie esistenti. Quando la coppia manca, un ⚠️ ambra sulla scheda la crea; quando mancano i suoi tassi, un 🔄 ambra li sincronizza.

Nella modalità [Rolling Return](chart.md#rolling-return) rimane solo Confronto asset: ogni asset confrontato diventa un rendimento rolling, con la stessa finestra mobile e la stessa valuta. Gli altri segnali vengono nascosti, non eliminati, e ricompaiono nella modalità **Prezzi**.

---

## 📐 Benchmark sintetici

Curve di riferimento disegnate solo dai loro parametri, senza dati di mercato:

- [Crescita lineare](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md) — $y(t) = y_0\,(1 + r\,t)$
- [Crescita composta](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) — $y(t) = y_0\,(1 + r)^t$
- [Onda sinusoidale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md) — $y(t) = A \sin(2\pi t / T) + y_0$

---

## 🩺 Leggere una scheda di segnale

- Uno **spinner** gira mentre il segnale viene calcolato.
- **📈 N** è il numero di punti di prezzo caricati.
- Un **ℹ** grigio — calcolato, con una piccola avvertenza: un breve gap o un warm-up quasi completo. Passa il mouse sull'icona per i dettagli.
- Un **⚠** ambra — calcolato, con un'avvertenza che vale la pena controllare: gap più grandi, un warm-up incompleto o dati che iniziano dopo la prima data sullo schermo. Anche la scheda diventa ambra.
- Un **⚠** rosso — non calcolato: un campo di prezzo mancante, cronologia troppo breve per i parametri, nessun dato o un errore di calcolo. La scheda diventa rossa.

??? note "🧩 Cronologia dei prezzi discontinua — quando un segnale è parziale"

    ADX, Aroon, ATR, NATR, CCI, Donchian Channels, MFI e OBV possono funzionare su una cronologia discontinua: usano il tratto più recente senza gap che sia sufficientemente lungo, e il tooltip indica quel tratto e quanti punti sono stati esclusi. Gli altri indicatori richiedono una cronologia senza gap e spiegano perché non possono funzionare invece di tracciare una linea fuorviante. Un fine settimana o una festività di mercato non è un gap.

---

## 🔗 Correlati

- 📚 **[Indicatori tecnici](../../../financial-theory/technical-analysis/indicators/index.md)** — La formula di ogni indicatore e come leggerla
- ⚠️ **[Metriche di rischio](../../../financial-theory/technical-analysis/risk-metrics/index.md)** — Le metriche dietro i segnali di rischio
- 🧠 **[AI Export dell'asset](../../ai-export/asset.md)** — Indicatori tecnici calcolati dallo stesso backend, esportati per un assistente AI
- 🛠️ **[Guida ai plugin dei segnali](../../../developer/architecture/patterns/signal_plugin_guide.md)** — Per sviluppatori: come vengono calcolati, verificati e aggiunti gli indicatori
