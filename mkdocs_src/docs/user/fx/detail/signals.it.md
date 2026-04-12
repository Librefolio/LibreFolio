# 📈 Segnali

Il pannello Segnali consente di sovrapporre **indicatori tecnici** al grafico FX. Questi vengono calcolati in tempo reale a partire dai dati del tasso di cambio e aiutano a identificare trend, cambiamenti di momentum e pattern di volatilità.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Pannello Segnali FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicatori Disponibili

### 📉 [EMA — Media Mobile Esponenziale](../../../financial-theory/technical-analysis/indicators/ema.md)

Riduce il rumore dei tassi giornalieri per rivelare il **trend sottostante**. Nel FX, un'EMA che incrocia al rialzo la linea del tasso suggerisce spesso un indebolimento della valuta base (o un rafforzamento della valuta quotata). Periodo configurabile: più breve = più reattivo, più lungo = più fluido.

### 📊 [MACD — Convergenza/Divergenza della Media Mobile](../../../financial-theory/technical-analysis/indicators/macd.md)

Misura il **momentum** calcolando la differenza tra un EMA veloce e uno lento. Un MACD positivo indica che l'EMA veloce è sopra l'EMA lento (bullish), un valore negativo indica l'opposto (bearish). Utile nel FX per rilevare inversioni di trend e cambiamenti di momentum.

- 📈 **Linea MACD**: Differenza tra EMA veloce e lento
- 〰️ **Linea di Segnale**: EMA della linea MACD stessa (momentum levigato)
- 📊 **Istogramma**: Differenza visiva tra le linee MACD e di Segnale

### 💪 [RSI — Indice di Forza Relativa](../../../financial-theory/technical-analysis/indicators/rsi.md)

Un **oscillatore** (0–100) che misura la velocità e l'entità delle variazioni di prezzo. Nel FX, valori superiori a 70 possono suggerire che la coppia di valute sia ipercomprata, valori inferiori a 30 suggeriscono che sia ipervenduta. Utile per individuare potenziali inversioni.

### 📏 [Bande di Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

Un **inviluppo di volatilità** attorno al prezzo. Le bande si allargano durante i periodi volatili e si restringono durante i periodi di calma. Nel FX, un tasso che tocca la banda superiore può segnalare condizioni di ipercomprato, mentre il tocco della banda inferiore può segnalare condizioni di ipervenduto.

- 〰️ **Banda Centrale**: Media Mobile Semplice (SMA)
- 🔺 **Banda Superiore**: SMA + 2 deviazioni standard
- 🔻 **Banda Inferiore**: SMA − 2 deviazioni standard

---

## 🛠️ Come Usarlo

1. Clicca sull'interruttore **Segnali** (📈) nella barra degli strumenti del grafico
2. Il pannello dei segnali si apre sotto il grafico
3. Aggiungi indicatori dai menu a tendina categorizzati (Indicatori Tecnici, Confronto Dati, Benchmark Sintetici)
4. I parametri di ogni indicatore possono essere regolati inline
5. I segnali vengono renderizzati come overlay direttamente sul grafico

---

## 📚 Approfondimento: Teoria Finanziaria

Per un trattamento matematico completo di ogni indicatore — incluse formule, equivalenti di elaborazione dei segnali e interpretazione pratica:

:material-book-open-variant: **[Indicatori Tecnici — Teoria Finanziaria](../../../financial-theory/technical-analysis/indicators/index.md)**

Questa pagina di riferimento copre:

- 🔢 Le **formule matematiche** dietro ogni indicatore
- 🎛️ Gli equivalenti di **elaborazione dei segnali** (EMA = filtro IIR, SMA = filtro FIR, ecc.)
- ⚡ L'intuizione **"veloce vs lento"** in termini di frequenze di taglio dei filtri
- 📈 **Esempi pratici** di rilevamento di crossover e identificazione del trend
