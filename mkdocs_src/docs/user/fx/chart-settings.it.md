# ⚙️ Impostazioni Grafico

LibreFolio fornisce una modale delle **Impostazioni del Grafico** per personalizzare l'aspetto e il comportamento dei grafici FX. Queste impostazioni si applicano sia ai mini-grafici nella [pagina FX List](index.md) che al grafico completo nella [pagina Pair Detail](detail/index.md).

---

## 🔓 Accesso alle Impostazioni Grafico

È possibile aprire la modale delle Impostazioni del Grafico da:

- 📋 La **pagina FX List** — tramite il pulsante delle impostazioni (⚙️) nella barra degli strumenti
- 📊 La **pagina Pair Detail** — tramite il pulsante delle impostazioni del grafico

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Modale Impostazioni Grafico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Impostazioni Disponibili

### 🎨 Aspetto

| Impostazione | Descrizione |
|-------------|-------------|
| **Colore Linea** | Colore primario per la linea del grafico |
| **Spessore Linea** | Spessore della linea del grafico (px) |
| **Riempimento Area** | Abilita/disabilita il riempimento a gradiente sotto la linea |
| **Linee della Griglia** | Mostra/nasconde le linee della griglia orizzontali e verticali |

### 🖱️ Suggerimento e Interazione

| Impostazione | Descrizione |
|-------------|-------------|
| **Formato Suggerimento** | Numero di cifre decimali mostrate nei suggerimenti |
| **Mirino** | Abilita/disabilita il mirino (crosshair) al passaggio del mouse |
| **Zoom** | Impostazioni per lo zoom tramite rotella del mouse e pinch zoom |

### 📈 Overlay di Segnali

Quando si utilizza il grafico della pagina di dettaglio, è possibile configurare quali **indicatori tecnici** devono essere visualizzati come overlay:

#### 🧮 Segnali Calcolati

Questi sono computati a partire dai dati della coppia stessa:

- 📉 **EMA** (Exponential Moving Average)
- 📊 **MACD** (Moving Average Convergence Divergence)
- 💪 **RSI** (Relative Strength Index)
- 📏 **Bollinger Bands**

Ogni segnale può essere gestito tramite l'interruttore indipendentemente dal [pannello Signals](detail/signals.md).

#### 🔍 Segnali Comparativi e Benchmark

È inoltre possibile sovrapporre **confronti con benchmark** per vedere come una coppia si comporta rispetto a un riferimento:

- 📐 **Benchmark Sintetici** — Panieri personalizzati o tassi di riferimento calcolati
- ↔️ **Overlay Cross-pair** — Confronta EUR/USD rispetto a GBP/USD sullo stesso grafico

Per le basi matematiche, consultare [Indicatori Tecnici](../../financial-theory/technical-analysis/indicators/index.md) e [Benchmark Sintetici](../../financial-theory/technical-analysis/synthetic-benchmarks/index.md).

---

## 💾 Persistenza

Le impostazioni del grafico sono memorizzate localmente nel `localStorage` del browser e si applicano a tutte le coppie di valute. Vengono mantenute tra le sessioni — anche dopo aver chiuso e riaperto il browser — e andranno perse solo se si svuota la cache/storage del browser o se lo storage scade (dipende dal browser, tipicamente da mesi ad anni).
