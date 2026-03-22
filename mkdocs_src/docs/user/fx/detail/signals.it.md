# 📈 Segnali

Il pannello Segnali ti permette di sovrapporre **indicatori tecnici** sul grafico FX. Questi vengono calcolati in tempo reale dai dati del tasso di cambio e aiutano a identificare trend, variazioni di momentum e schemi di volatilità.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Pannello Segnali FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Indicatori Disponibili

### 📉 [EMA — Media Mobile Esponenziale](../../../financial-theory/technical-indicators.md#ema)

Traccia il **trend** attenuando il rumore dei prezzi giornalieri, assegnando più peso ai valori recenti. Quando una EMA a periodo breve incrocia al rialzo una EMA a periodo lungo ("golden cross"), segnala momentum ascendente.

- ⚡ **EMA Veloce**: Periodo breve (es. 12 giorni) — reagisce rapidamente ai cambiamenti di prezzo
- 🐢 **EMA Lenta**: Periodo lungo (es. 26 giorni) — più regolare, mostra il trend sottostante

### 📊 [MACD — Convergenza/Divergenza delle Medie Mobili](../../../financial-theory/technical-indicators.md#macd)

Misura il **momentum** calcolando la differenza tra due EMA. Un MACD positivo significa che la EMA veloce è sopra quella lenta (rialzista), negativo significa il contrario (ribassista).

- 📈 **Linea MACD**: Differenza tra EMA veloce e lenta
- 〰️ **Linea di Segnale**: EMA della stessa linea MACD (momentum smorzato)
- 📊 **Istogramma**: Differenza visiva tra le linee MACD e di Segnale

### 💪 [RSI — Relative Strength Index](../../../financial-theory/technical-indicators.md#rsi)

Un **oscillatore** (0–100) che misura la velocità e l'entità delle variazioni di prezzo. Valori sopra 70 suggeriscono condizioni di ipercomprato, sotto 30 di ipervenduto.

### 📏 [Bollinger Bands](../../../financial-theory/technical-indicators.md#bollinger-bands)

Una **fascia di volatilità** attorno al prezzo. Le bande si allargano durante i periodi volatili e si contraggono in quelli calmi.

- 〰️ **Banda Centrale**: Media Mobile Semplice (SMA)
- 🔺 **Banda Superiore**: SMA + 2 deviazioni standard
- 🔻 **Banda Inferiore**: SMA − 2 deviazioni standard

---

## 🛠️ Come Utilizzare

1. Fai clic sul pulsante di attivazione **Segnali** (📈) nella barra degli strumenti del grafico
2. Il pannello segnali si apre sotto il grafico
3. Attiva/disattiva ogni indicatore **indipendentemente**
4. I segnali sono visualizzati come sovrapposizioni direttamente sul grafico
5. I parametri di ogni indicatore possono essere modificati in [Impostazioni Grafico](../chart-settings.md)

---

## 📚 Approfondimento: Teoria Finanziaria

Per un trattamento matematico completo di ogni indicatore — includendo formule, equivalenti nell'elaborazione del segnale e interpretazione pratica:

:material-book-open-variant: **[Indicatori Tecnici — Teoria Finanziaria](../../../financial-theory/technical-indicators.md)**

Questa pagina di riferimento copre:

- 🔢 Le **formule matematiche** dietro ogni indicatore
- 🎛️ Equivalenti nell'**elaborazione del segnale** (EMA = filtro IIR, SMA = filtro FIR, ecc.)
- ⚡ L'intuizione **"veloce vs lento"** in termini di frequenze di taglio dei filtri
- 📈 **Esempi pratici** di identificazione degli incroci e trend

## 📝 Note del Traduttore
