# 📊 Segnali

Il pannello Segnali consente di sovrapporre **indicatori tecnici** al grafico dei prezzi. Questi vengono calcolati in tempo reale a partire dai dati di prezzo dell'asset e aiutano a identificare tendenze, cambiamenti di momentum e pattern di volatilità.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-signals" alt="Pannello Segnali Asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicatori Disponibili

### 📉 [EMA — Media Mobile Esponenziale](../../../financial-theory/technical-analysis/indicators/ema.md)

Riduce il rumore dei prezzi giornalieri per rivelare il **trend sottostante**. Un'EMA che incrocia al rialzo la linea del prezzo spesso segnala un trend ribassista. Periodo configurabile: più breve = più reattivo, più lungo = più fluido.

### 📊 [MACD — Moving Average Convergence Divergence](../../../financial-theory/technical-analysis/indicators/macd.md)

Misura il **momentum** calcolando la differenza tra un'EMA veloce e una lenta. Utile per rilevare inversioni di tendenza e cambiamenti di momentum.

- 📈 **Linea MACD**: Differenza tra EMA veloce e lenta
- 〰️ **Linea di Segnale**: EMA della linea MACD stessa (momentum levigato)
- 📊 **Istogramma**: Differenza visiva tra le linee MACD e di Segnale

### 💪 [RSI — Relative Strength Index](../../../financial-theory/technical-analysis/indicators/rsi.md)

Un **oscillatore** (0–100) che misura la velocità e l'entità delle variazioni di prezzo. Valori superiori a 70 possono suggerire che l'asset sia ipercomprato, valori inferiori a 30 suggeriscono che sia ipervenduto.

### 📏 [Bande di Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

Un **inviluppo di volatilità** attorno al prezzo. Le bande si allargano durante i periodi volatili e si restringono durante i periodi di calma.

- 〰️ **Banda Centrale**: Media Mobile Semplice (SMA)
- 🔺 **Banda Superiore**: SMA + 2 deviazioni standard
- 🔻 **Banda Inferiore**: SMA − 2 deviazioni standard

### 🔀 Confronto Asset

Confronta la performance dell'asset corrente con **un altro asset**. Il prezzo dell'asset di confronto viene sovrapposto al grafico, normalizzato sulla stessa scala. Utile per l'analisi della performance relativa (ad esempio, confrontare un'azione con il suo benchmark).

---

## 🛠️ Come Utilizzare

1. Clicca sull'interruttore **Segnali** (📈) nella barra degli strumenti
2. Il pannello dei segnali si apre sotto la barra degli strumenti
3. Aggiungi indicatori dai menu a tendina categorizzati
4. I parametri di ogni indicatore possono essere regolati inline
5. I segnali vengono renderizzati come sovrapposizioni direttamente sul grafico

---

## 📚 Approfondimento: Teoria Finanziaria

Per un trattamento matematico completo di ogni indicatore — incluse formule, equivalenti di elaborazione dei segnali e interpretazione pratica:

:material-book-open-variant: **[Indicatori Tecnici — Teoria Finanziaria](../../../financial-theory/technical-analysis/indicators/index.md)**

Questa pagina di riferimento copre:

- 🔢 Le **formule matematiche** dietro ogni indicatore
- 🎛️ Equivalenti di **elaborazione dei segnali** (EMA = filtro IIR, SMA = filtro FIR, ecc.)
- ⚡ L'intuizione **"veloce vs lento"** in termini di frequenze di taglio dei filtri
- 📈 **Esempi pratici** di rilevamento di crossover e identificazione del trend
