# 📊 Segnali

Il pannello dei segnali ti consente di sovrapporre **indicatori tecnici**, **serie di confronto** e **curve di benchmark** sul grafico dei prezzi. Gli indicatori vengono calcolati lato server dalla **piattaforma di plugin per segnali** del backend di LibreFolio a partire dalla cronologia dei prezzi memorizzata per l'asset — il browser si limita a visualizzare i risultati, quindi il grafico, la diagnostica e gli snapshot dell'AI Export vedono tutti gli stessi numeri.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Pannello dei segnali dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 Segnali disponibili

I segnali sono organizzati in **tre categorie**, ciascuna con il proprio menu a tendina nella parte superiore del pannello.

### 📉 Indicatori tecnici — 22 plugin backend

I grafici degli asset possono eseguire **22 plugin di indicatori**, raggruppati in base alla proprietà di mercato che misurano. La matematica di ciascun indicatore è trattata nella sezione Teoria Finanziaria — segui i link qui sotto oppure fai clic sull'icona 📖 su qualsiasi scheda del segnale per passare direttamente alla relativa pagina di teoria.

| Famiglia | Indicatori |
|---|---|
| 📈 **Trend** (5) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) · [ADX](../../../financial-theory/technical-analysis/indicators/adx.md) · [Aroon](../../../financial-theory/technical-analysis/indicators/aroon.md) |
| ⚡ **Momentum** (6) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [RSI Stocastico](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) · [CCI](../../../financial-theory/technical-analysis/indicators/cci.md) |
| 🌊 **Volatilità** (4) | [Bande di Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) · [ATR](../../../financial-theory/technical-analysis/indicators/atr.md) · [NATR](../../../financial-theory/technical-analysis/indicators/natr.md) · [Canali di Donchian](../../../financial-theory/technical-analysis/indicators/donchian-channels.md) |
| 📊 **Volume** (2) | [OBV](../../../financial-theory/technical-analysis/indicators/obv.md) · [MFI](../../../financial-theory/technical-analysis/indicators/mfi.md) |
| ⚠️ **Rischio** (5) | Drawdown Sott'acqua · Rendimento Rolling · Volatilità Rolling · Sharpe Ratio Rolling · Beta Rolling |

Per i concetti della famiglia Rischio, consulta le pagine di teoria delle [Metriche di Rischio](../../../financial-theory/technical-analysis/risk-metrics/index.md) ([Max Drawdown](../../../financial-theory/technical-analysis/risk-metrics/max-drawdown.md), [Volatilità](../../../financial-theory/technical-analysis/risk-metrics/volatility.md), [Sharpe Ratio](../../../financial-theory/technical-analysis/risk-metrics/sharpe-ratio.md)).

!!! info "Non tutti gli indicatori possono essere eseguiti su ogni asset"

    Gli indicatori che richiedono prezzi **massimi/minimi** (ADX, Aroon, ATR, NATR, CCI, Donchian
    Channels) o **volume** (OBV, MFI) diventano disponibili solo quando la cronologia dei prezzi
    include questi campi — la scheda del segnale indica quale campo manca.
    **Beta Rolling** richiede inoltre di scegliere un asset di confronto.

### 💱 Confronto dati

Sovrapposizioni calcolate dal browser che normalizzano un'altra serie sullo stesso grafico:

- ↔️ **Confronto Asset** — sovrappone la performance di un altro asset, normalizzata sulla stessa scala (ad es. un titolo azionario rispetto al suo indice di riferimento)
- 💱 **Coppia FX** — sovrappone il tasso di cambio di una coppia di valute configurata

### 📐 Benchmark sintetici

**Curve di riferimento matematiche** calcolate dal browser e generate esclusivamente da parametri — nessun dato di mercato richiesto: [Crescita Lineare](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Crescita Composita](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) e [Onda Sinusoidale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🔍 Trovare un indicatore

Il menu a tendina degli indicatori è un **albero comprimibile raggruppato per famiglia** (trend, momentum, volatilità, volume, rischio), con una casella di ricerca nella parte superiore:

- ⌨️ Digita per filtrare tra tutte le famiglie — la ricerca trova corrispondenze in nomi, descrizioni e persino nei campi dati utilizzati da un indicatore
- 📁 Ogni famiglia mostra un badge con il conteggio e si espande/comprime in modo indipendente
- 🖱️ Supporto completo da tastiera: le frecce spostano la selezione, `→`/`←` espandono e comprimono una famiglia, `Enter` seleziona

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals-tree" alt="Ricerca raggruppata degli indicatori nel pannello dei segnali dell'asset">
</div>

---

## 🎛️ Schede dei segnali

Ogni segnale aggiunto diventa una scheda che mostra:

- 📖 Un'**icona della documentazione** che collega alla pagina di Teoria Finanziaria dell'indicatore
- 🎚️ **Parametri in linea** (numeri, menu a tendina, caselle di spunta) — alcuni suggerimenti contengono formule LaTeX renderizzate con KaTeX
- 🏷️ Un **badge dati** con il numero di punti di prezzo (📈) caricati
- 🗑️ Pulsante di rimozione; trascina le schede per riordinare le sovrapposizioni

### ⏳ Mentre il backend calcola

Un piccolo **spinner** appare su ogni scheda mentre la richiesta al backend è in corso. Lo stato transitorio è voluto: le schede non mostrano mai un errore rosso "nessun dato" solo perché la risposta non è ancora arrivata.

### 🩺 Diagnostica per segnale

Dopo il caricamento, un'icona colorata riporta l'esito del calcolo — passa il mouse sopra per la spiegazione completa:

- ℹ️ **Avviso** (grigio) / ⚠️ **Attenzione** (ambra) — il segnale è stato calcolato ma con riserve: lacune nei dati, un warm-up incompleto o un intervallo che inizia prima dei tuoi dati
- 🔴 **Errore** (rosso) — il segnale non può essere calcolato: campi OHLCV mancanti, cronologia insufficiente per i parametri scelti o un errore di calcolo

---

## 🧩 Dati incompleti: segmenti parziali

Gli indicatori che tollerano le lacune (ADX, Aroon, ATR, NATR, CCI, Donchian, MFI, OBV) non falliscono su una cronologia dei prezzi frammentaria: il backend seleziona il **segmento contiguo completo** più recente, calcola l'indicatore su di esso e riporta il risultato come *parziale* — il suggerimento indica quale segmento è stato utilizzato e quanti punti sono stati esclusi. Tutti gli altri indicatori richiedono dati senza lacune e spiegano perché non possono essere eseguiti invece di tracciare una linea fuorviante.

---

## 📉 Drawdown: interruttore della cronologia completa

La scheda **Drawdown Sott'acqua** include una casella di spunta **Cronologia completa** (attiva per impostazione predefinita): il calo viene misurato rispetto al picco corrente dell'*intera* cronologia disponibile, quindi ritagliato sulla finestra visibile — un picco di anni fa conta ancora. Disattivala per una visualizzazione più rapida e relativa alla finestra. Gli snapshot dell'AI Export usano sempre il comportamento a cronologia completa, indipendentemente da questa impostazione del grafico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals-drawdown" alt="Scheda del segnale Drawdown con l'interruttore della cronologia completa">
</div>

---

## 🛠️ Come utilizzare

1. Fai clic sull'interruttore **Segnali** (📈) nella barra degli strumenti
2. Il pannello dei segnali si apre sotto la barra degli strumenti
3. Aggiungi segnali dai tre menu a tendina delle categorie (**Indicatori tecnici**, **Confronto dati**, **Benchmark sintetici**)
4. Regola i parametri di ciascun segnale direttamente sulla sua scheda
5. I segnali vengono visualizzati come sovrapposizioni direttamente sul grafico

---

## 🧠 AI Export

Il pulsante **AI Export** (:material-brain:) nella barra degli strumenti della pagina offre due attività per gli asset:

- **Revisione Posizione**
- **Analisi di Mercato dell'Asset**

Il backend costruisce lo snapshot a partire da identità e valutazione dell'asset, cronologia dei prezzi normalizzata, contesto della posizione di portafoglio e risultati tecnici del servizio segnali condiviso. Il browser non ricalcola gli indicatori. Le attività compaiono solo quando sono applicabili all'asset e ai dati disponibili — ad esempio, la Revisione Posizione richiede una posizione aperta. Vedi [Asset AI Export](../../ai-export/asset.md) o la [panoramica AI Export](../../ai-export/index.md).

---

## 📚 Approfondimento: Teoria Finanziaria

Per un trattamento matematico completo di ciascun indicatore — incluse le formule, le equivalenze nell'elaborazione del segnale e l'interpretazione pratica:

:material-book-open-variant: **[Indicatori Tecnici — Teoria Finanziaria](../../../financial-theory/technical-analysis/indicators/index.md)**

Questa pagina di riferimento copre:

- 🔢 Le **formule matematiche** alla base di ciascun indicatore
- 🎛️ Equivalenze nell'**elaborazione del segnale** (EMA = filtro IIR, SMA = filtro FIR, ecc.)
- ⚡ L'intuizione **"veloce vs lento"** in termini di frequenze di taglio del filtro
- 📈 **Esempi pratici** di rilevamento dei crossover e identificazione dei trend
