# 🔍 Pagina Dettaglio Asset

Clicca su qualsiasi asset dalla [Lista Asset](../index.md) per aprire la sua pagina di dettaglio. Qui puoi visualizzare, analizzare e gestire i dati dei prezzi per quello specifico asset.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Pagina Dettaglio Asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La pagina di dettaglio è organizzata in diverse funzionalità, ognuna accessibile dalla barra degli strumenti:

---

## 🧭 Funzionalità

### 📈 [Grafico Interattivo](chart.md)

La vista principale: un grafico completo basato su ECharts con zoom, pan, filtraggio dell'intervallo di date e conversione di valuta. I marcatori di evento (dividendi, split, interessi) sono sovrapposti direttamente sulla linea del prezzo.

### 📊 [Segnali](signals.md)

Sovrapponi indicatori tecnici (EMA, MACD, RSI, Bollinger Bands, Confronto Asset) al grafico. Ogni segnale è calcolato in tempo reale dai dati dei prezzi e può essere gestito tramite un interruttore indipendente.

### 📐 [Misure](measures.md)

Strumento di misurazione click-to-click. Seleziona due punti sul grafico per vedere il delta, la variazione percentuale e il rendimento annualizzato tra di essi.

### 🗂️ [Classificazione](classification.md)

Grafico a torta dei settori, mappa geografica mondiale e ripartizione per paese — quando i dati di classificazione sono configurati per l'asset.

### ✏️ [Editor Dati](data-editor.md)

Visualizza, aggiungi, modifica o elimina singoli punti dati dei prezzi direttamente sul grafico.

### 📅 [Eventi](events.md)

Eventi a livello di asset (dividendi, interessi, split, aggiustamenti di prezzo) mostrati come marcatori sul grafico.

---

## 🔧 Intestazione e Controlli

- **← Pulsante Indietro**: torna alla lista asset (o alla pagina precedente)
- **Info Asset**: nome, badge del tipo, valuta, prezzo attuale
- **Modifica** (✏️): apre la finestra modale di modifica per modificare le proprietà dell'asset
- **Sincronizza** (🔄): recupera gli ultimi dati dei prezzi dal provider
- **Aggiorna** (↻): ricarica i dati dal database

---

## 🔗 Correlati

- ➕ **[Crea e Modifica](../create-edit.md)** — Creazione e configurazione degli asset
- 📋 **[Panoramica Asset](../index.md)** — Torna alla pagina della lista asset
