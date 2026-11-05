# 📊 Segnali

I segnali sono linee tracciate sopra il grafico dei prezzi: **indicatori tecnici** che LibreFolio calcola dai prezzi memorizzati, **un altro asset o una coppia di valute** con cui confrontarsi, e **curve di riferimento** come una crescita costante. Usali per leggere a colpo d'occhio trend, momentum, volatilità e rischio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Pannello dei segnali dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Aggiungere un segnale

1. Apri il pannello **Segnali** sopra il grafico.
2. Scegli un segnale da uno dei suoi tre menu: **Indicatori tecnici**, **Confronto dati** o **Benchmark sintetici**. Nel menu degli indicatori, digita per cercare per nome, descrizione o dati utilizzati da un indicatore.
3. Imposta i suoi parametri sulla scheda che appare; il grafico si aggiorna.
4. Trascina una scheda dalla sua maniglia (frecce su un telefono) per cambiarne l'ordine, oppure rimuovila con 🗑️.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Ricerca raggruppata degli indicatori nel pannello dei segnali dell'asset">
</div>

Ogni linea di una scheda, e ogni zona di indicatori come l'RSI, ha il proprio colore e stile di linea. I tuoi segnali vengono ricordati per questo asset, in questo browser.

---

## 📉 Indicatori tecnici {: #technical-indicators }

**22 indicatori**, raggruppati in base a ciò che misurano. Ogni nome rimanda alla sua pagina teorica; il **?** su una scheda apre la stessa pagina.

### 📈 Trend

- [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) — media semplice dei prezzi di chiusura
- [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) — media che attribuisce maggior peso ai prezzi recenti
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

- [Bande di Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) — una banda attorno a una media mobile che si allarga con la volatilità
- [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) — volatilità in unità di prezzo
- [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) — volatilità in percentuale del prezzo
- [Canali di Donchian](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) — il massimo più alto e il minimo più basso del periodo

### 📊 Volume

- [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) — pressione del volume dietro i movimenti di prezzo
- [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) — momentum ponderato per il volume

### ⚠️ Rischio

- [Drawdown sotto il picco](../../../financial-theory/technical-analysis/risk-metrics/current-drawdown.md) — quanto il prezzo è al di sotto del suo picco progressivo ([storia completa](#drawdown-full-history))
- [Rendimento mobile](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar) — rendimento del solo prezzo rispetto alla chiusura di un numero scelto di giorni di calendario precedenti, la stessa misura della modalità [Rendimento mobile](chart.md#rolling-return) del grafico
- [Volatilità mobile](../../../financial-theory/technical-analysis/risk-metrics/volatility.md) — volatilità annualizzata su una finestra mobile
- [Indice di Sharpe mobile](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md) — rendimento in eccesso per unità di volatilità su una finestra mobile
- [Beta mobile](../../../financial-theory/technical-analysis/risk-metrics/beta-active-return.md) — quanto fortemente l'asset segue un asset di confronto che scegli

I periodi contano le **sedute**, ossia i giorni in cui l'asset è stato quotato: una SMA 200 copre 200 sedute, circa 290 giorni di calendario ([perché](../../../financial-theory/technical-analysis/indicators/index.md)). La **Finestra** di Volatilità mobile, Indice di Sharpe mobile e Beta mobile conta le **osservazioni**: un rendimento per ogni giorno in cui l'asset è stato quotato — per Beta mobile, per ogni giorno in cui è stato quotato almeno uno dei due asset, con l'altro conteggiato al suo ultimo prezzo. La **Finestra** di Rendimento mobile conta i **giorni di calendario**, come nella modalità [Rendimento mobile](chart.md#rolling-return) del grafico.

!!! info "Non tutti gli indicatori possono funzionare su ogni asset"

    ADX, Aroon, ATR, NATR, CCI, Canali di Donchian e MFI richiedono i prezzi **massimi** e **minimi**; OBV e MFI richiedono il **volume**. Senza di essi, la scheda ti indica quali dati mancano.

### 📉 Drawdown sull'intera storia {: #drawdown-full-history }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Scheda del segnale Drawdown con l'interruttore della storia completa">
</div>

La scheda **Drawdown sotto il picco** ha una casella di controllo **Storia completa**, attiva per impostazione predefinita: il calo è misurato dal prezzo più alto dell'intera storia dell'asset, anche molti anni prima delle date visualizzate. Deselezionala per una vista più rapida, misurata dal prezzo più alto nell'intervallo visualizzato.

---

## 💱 Confronto con un asset o una coppia di valute {: #data-comparison }

Il menu **Confronto dati** aggiunge:

- **Confronto asset** — un altro asset sullo stesso grafico, come un'azione rispetto al suo ETF sull'indice. Nella vista **%** entrambe le linee partono da 0 %. L'asset si sceglie nello stesso pannello usato per il confronto di rischio: una casella di ricerca, filtri **Tipo** e **Valuta**, i benchmark elencati per primi, un clic per scegliere. L'asset del grafico stesso è visualizzato in grigio; uno già usato da un altro confronto porta un segno di avviso ma può comunque essere scelto.
- **Coppia FX** — il tasso di una delle tue coppie di valute.

Con **Tutto** selezionato, il grafico parte dalla serie più vecchia. Se l'asset confrontato ha prezzi dal 1985 e l'asset del grafico stesso dal 2010, il grafico viene disegnato dal 1985, la linea dell'asset del grafico stesso resta vuota fino al 2010, e la data **Da** mostra 1985. Nella vista **%** ogni linea parte da 0 % sul proprio primo prezzo. Se l'asset confrontato inizia dopo quello del grafico stesso, il grafico resta com'era e la linea di confronto parte dal proprio primo giorno. Gli altri segnali (indicatori e benchmark sintetici) seguono i giorni dell'asset del grafico stesso, quindi sono vuoti prima del suo primo giorno.

**Sync** (🔄) su una scheda Confronto asset scarica i prezzi di quell'asset per le date del grafico, insieme ai tassi di cambio che li convertono, per le coppie esistenti. Quando la coppia manca, un ⚠️ color ambra sulla scheda la crea; quando mancano i suoi tassi, un 🔄 color ambra li sincronizza.

In modalità [Rendimento mobile](chart.md#rolling-return) resta solo il Confronto asset: ogni asset confrontato diventa un rendimento mobile, con la stessa finestra e la stessa valuta. Gli altri segnali sono nascosti, non eliminati, e ricompaiono in modalità **Prezzi**.

---

## 📐 Benchmark sintetici

Curve di riferimento tracciate dai soli parametri, senza alcun dato di mercato:

- [Crescita lineare](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md) — $y(t) = y_0\,(1 + r\,t)$
- [Crescita composta](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) — $y(t) = y_0\,(1 + r)^t$
- [Onda sinusoidale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md) — $y(t) = A \sin(2\pi t / T) + y_0$

---

## 🩺 Leggere una scheda di segnale

- Un **indicatore di caricamento** gira mentre il segnale viene calcolato.
- **📈 N** è il numero di punti di prezzo caricati.
- Un **ℹ** grigio — calcolato, con una piccola avvertenza: una breve interruzione o un periodo di inizializzazione quasi completo. Passa il mouse sull'icona per i dettagli.
- Un **⚠** color ambra — calcolato, con un'avvertenza che merita un'occhiata: interruzioni più ampie, un periodo di inizializzazione incompleto, o dati che iniziano dopo la prima data visualizzata. Anche la scheda diventa color ambra.
- Un **⚠** rosso — non calcolato: un campo di prezzo mancante, uno storico troppo breve per i parametri, nessun dato, o un errore di calcolo. La scheda diventa rossa.

??? note "🧩 Storico dei prezzi frammentato — quando un segnale è parziale"

    ADX, Aroon, ATR, NATR, CCI, Canali di Donchian, MFI e OBV possono funzionare su uno storico frammentato: usano il tratto più recente senza interruzioni che sia abbastanza lungo, e il tooltip indica quel tratto e quanti punti sono stati esclusi. Gli altri indicatori richiedono uno storico senza interruzioni e spiegano perché non possono funzionare anziché tracciare una linea fuorviante. Un fine settimana o una festività di mercato non è un'interruzione.

---

## 🔗 Correlati

- 📚 **[Indicatori tecnici](../../../financial-theory/technical-analysis/indicators/index.md)** — La formula di ogni indicatore e come leggerlo
- ⚠️ **[Metriche di rischio](../../../financial-theory/technical-analysis/risk-metrics/index.md)** — Le metriche alla base dei segnali di rischio
- 🧠 **[AI Export dell'asset](../../ai-export/asset.md)** — Indicatori tecnici calcolati dallo stesso backend, esportati per un assistente AI
- 🛠️ **[Guida ai plugin dei segnali](../../../developer/architecture/patterns/signal_plugin_guide.md)** — Per gli sviluppatori: come gli indicatori vengono calcolati, verificati e aggiunti
