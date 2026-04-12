# ⚙️ Impostazioni Grafico

LibreFolio fornisce una **finestra modale Impostazioni Grafico** per personalizzare l'aspetto e il comportamento dei grafici FX. Queste impostazioni si applicano sia ai mini-grafici nella [Pagina Lista FX](index.md) che al grafico completo nella [Pagina Dettaglio Coppia](detail/index.md).

---

## 🔓 Accedere alle Impostazioni Grafico

Puoi aprire la finestra modale Impostazioni Grafico da:

- 📋 La **Pagina Lista FX** — tramite il pulsante delle impostazioni (⚙️) nella barra degli strumenti
- 📊 La **Pagina Dettaglio Coppia** — tramite il pulsante delle impostazioni del grafico

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Finestra modale Impostazioni Grafico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Impostazioni Disponibili

### 🎨 Aspetto

| Impostazione | Descrizione |
|--------------|-------------|
| **Colore della linea** | Colore principale per la linea del grafico |
| **Spessore della linea** | Spessore della linea del grafico (px) |
| **Riempimento dell'area** | Attiva/disattiva il riempimento graduale sotto la linea |
| **Linee della griglia** | Mostra/nascondi le linee orizzontali e verticali della griglia |

### 🖱️ Descrizione comando e Interazione

| Impostazione | Descrizione |
|--------------|-------------|
| **Formato descrizione comando** | Numero di decimali mostrati nella descrizione comando |
| **Mirino** | Attiva/disattiva il mirino al passaggio del mouse |
| **Zoom** | Impostazioni di zoom con rotellina del mouse e movimento di pizzico |

### 📈 Sovrapposizione Segnali

Quando si utilizza il grafico della pagina dettaglio, è possibile configurare quali **indicatori tecnici** visualizzare come sovrapposizioni:

#### 🧮 Segnali Calcolati

Questi sono calcolati dai dati della stessa coppia:

- 📉 **EMA** (Media Mobile Esponenziale)
- 📊 **MACD** (Moving Average Convergence Divergence)
- 💪 **RSI** (Relative Strength Index)
- 📏 **Bollinger Bands**

Ogni segnale può essere attivato/disattivato indipendentemente dal [pannello Segnali](detail/signals.md).

#### 🔍 Confronti e Benchmark

Puoi anche sovrapporre **confronti con benchmark** per vedere come una coppia performa rispetto a un riferimento:

- 📐 **Benchmark Sintetici** — Cestini personalizzati o tassi di riferimento calcolati
- ↔️ **Confronti tra coppie valutarie** — Confronta EUR/USD con GBP/USD sullo stesso grafico

Per le basi matematiche, vedere [Indicatori Tecnici](../../financial-theory/technical-analysis/indicators/index.md) e [Benchmark Sintetici](../../financial-theory/technical-analysis/synthetic-benchmarks/index.md).

---

## 💾 Persistenza

Le impostazioni del grafico vengono salvate nel `localStorage` del browser e si applicano a tutte le coppie di valute. Sopravvivono tra le sessioni — anche dopo aver chiuso e riaperto il browser — e verranno perse solo se si cancella la cache/storage del browser o se lo storage scade (dipende dal browser, tipicamente mesi o anni).
