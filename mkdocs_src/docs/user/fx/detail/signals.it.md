# 📈 Segnali

Il pannello Segnali ti permette di sovrapporre **indicatori tecnici** sul grafico FX. Questi vengono calcolati in tempo reale dai dati del tasso di cambio e aiutano a identificare trend, variazioni di momentum e schemi di volatilità.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Pannello Segnali FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicatori Disponibili

### 📉 [EMA — Media Mobile Esponenziale](../../../financial-theory/technical-analysis/indicators/ema.md)

Attenua il rumore dei tassi giornalieri per rivelare il **trend sottostante**. Nel FX, una EMA che incrocia al rialzo la linea del tasso spesso suggerisce un indebolimento della valuta base (o un rafforzamento della valuta quotata). Periodo configurabile: più breve = più reattiva, più lungo = più regolare.

### 📊 [MACD — Convergenza/Divergenza delle Medie Mobili](../../../financial-theory/technical-analysis/indicators/macd.md)

Misura il **momentum** calcolando la differenza tra una EMA veloce e una lenta. Un MACD positivo significa che la EMA veloce è sopra quella lenta (rialzista), negativo significa il contrario (ribassista). Utile nel FX per rilevare inversioni di trend e cambiamenti di momentum.

- 📈 **Linea MACD**: Differenza tra EMA veloce e lenta
- 〰️ **Linea di Segnale**: EMA della stessa linea MACD (momentum smorzato)
- 📊 **Istogramma**: Differenza visiva tra le linee MACD e di Segnale

### 💪 [RSI — Relative Strength Index](../../../financial-theory/technical-analysis/indicators/rsi.md)

Un **oscillatore** (0–100) che misura la velocità e l'entità delle variazioni di prezzo. Valori sopra 70 suggeriscono condizioni di ipercomprato, sotto 30 di ipervenduto.

### 📏 [Bollinger Bands](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md)

Una **fascia di volatilità** attorno al prezzo. Le bande si allargano durante i periodi volatili e si contraggono in quelli calmi.

- 〰️ **Banda Centrale**: Media Mobile Semplice (SMA)
- 🔺 **Banda Superiore**: SMA + 2 deviazioni standard
- 🔻 **Banda Inferiore**: SMA − 2 deviazioni standard

---

## 🛠️ Come Utilizzare

1. Fai clic sul pulsante di attivazione **Segnali** (📈) nella barra degli strumenti del grafico
2. Il pannello segnali si apre sotto il grafico
3. Aggiungi indicatori dai menu a discesa categorizzati (Indicatori Tecnici, Confronto Dati, Benchmark Sintetici)
4. I parametri di ogni indicatore possono essere regolati direttamente inline
5. I segnali sono visualizzati come sovrapposizioni direttamente sul grafico

---

## 📚 Approfondimento: Teoria Finanziaria

Per un trattamento matematico completo di ogni indicatore — includendo formule, equivalenti nell'elaborazione del segnale e interpretazione pratica:

:material-book-open-variant: **[Indicatori Tecnici — Teoria Finanziaria](../../../financial-theory/technical-analysis/indicators/index.md)**

Questa pagina di riferimento copre:

- 🔢 Le **formule matematiche** dietro ogni indicatore
- 🎛️ Equivalenti nell'**elaborazione del segnale** (EMA = filtro IIR, SMA = filtro FIR, ecc.)
- ⚡ L'intuizione **"veloce vs lento"** in termini di frequenze di taglio dei filtri
- 📈 **Esempi pratici** di identificazione degli incroci e trend
