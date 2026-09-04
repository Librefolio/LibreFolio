# 📈 Grafico Interattivo

Il grafico dei prezzi è l'elemento centrale della pagina di dettaglio dell'asset, fornendo una cronologia visiva del prezzo dell'asset nel tempo.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Grafico Prezzi Asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Barra dei Filtri

La barra dei filtri sopra il grafico fornisce i controlli per personalizzare la visualizzazione:

### 📅 Intervallo di Date

Seleziona una finestra temporale per i dati del grafico:

- **Preset**: 1W, 1M, 3M, 6M, 1Y, 2Y, YTD, MAX — quando la barra ha spazio libero, compaiono **preset di riempimento** extra per occuparlo (3Y, 5Y, 10Y e WTD, MTD, QTD)
- **Personalizzato**: scegli una data di inizio e di fine utilizzando il selettore del calendario

### 💱 Selettore di Valuta

Visualizza i prezzi in:

- La **valuta nativa** dell'asset (ad es. USD per Apple)
- La **valuta base del tuo portafoglio** (ad es. EUR) — convertita automaticamente utilizzando i tassi di cambio

### 📊 Interruttore Assoluto / Percentuale

- **Assoluto**: mostra i valori effettivi del prezzo
- **Percentuale** (%): mostra la variazione percentuale rispetto al primo punto dati nell'intervallo selezionato

### 📅 Indicatori di Evento

Dividendi, split, pagamenti di interessi e altri [eventi dell'asset](events.md) appaiono come indicatori colorati sul grafico:

- 💰 **Dividendo** — distribuzione di contanti
- 💵 **Interesse** — pagamento di interessi
- 📊 **Split** — frazionamento azionario
- 📝 **Rettifica del prezzo** — svalutazione o re-rating
- 🏁 **Regolamento alla scadenza** — l'asset ha raggiunto la scadenza

Passa il mouse su un indicatore per vedere i dettagli dell'evento (data, tipo, valore).

---

## 🎨 Estetica

Clicca sul pulsante **Impostazioni** (⚙️) per mostrare/nascondere il pannello aspetto inline (riempimento dell'area, colori della baseline, linee della griglia, gradiente stale, scala dell'asse Y). Le stesse impostazioni — più i segnali di overlay — possono essere modificate per tutti i grafici degli asset in una volta dalla modale **Impostazioni Grafico** sulla [pagina della lista Asset](../index.md), che mostra un'anteprima live durante la modifica; vedi [Impostazioni Grafico](../../fx/chart-settings.md) per come funzionano la modale e la sua anteprima (l'ambito Asset è indipendente da FX).

---

## 🔗 Correlati

- 📊 **[Segnali](signals.md)** — Sovrapponi indicatori tecnici
- 📐 **[Misure](measures.md)** — Misura le differenze di prezzo
- 📅 **[Eventi](events.md)** — Comprendi gli indicatori di evento
