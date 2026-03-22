# 📉 Grafico interattivo

Il cuore della pagina dei dettagli della coppia — un grafico **ECharts-powered** completo di tutte le funzionalità che permette di visualizzare la storia del tasso di cambio con potenti strumenti interattivi.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="FX Detail Chart" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Modalità di visualizzazione

Alterna tra due modalità tramite la barra degli strumenti:

- 📈 **Assoluto** — Mostra il valore del tasso di cambio grezzo (es. 1 EUR = 1,0845 USD). Ideale per vedere i livelli effettivi del tasso.
- 📊 **Percentuale (%)** — Mostra la variazione percentuale dal primo punto dati visibile. Ideale per confrontare i movimenti relativi e sovrapporre più segnali.

Passando alla modalità %, anche tutti i segnali overlay vengono ricalcolati come percentuali dal rispettivo punto di partenza.

---

## 🔍 Navigazione & zoom

| Action | Desktop | Mobile |
|--------|---------|--------|
| **Pan** | Clicca + trascina | Tocca + trascina |
| **Zoom in** | Rotella del mouse verso l’alto | Allargamento con due dita |
| **Zoom out** | Rotella del mouse verso il basso | Stringimento con due dita |
| **Reset zoom** | Doppio clic | Doppio tocco |

Puoi anche utilizzare i **preset temporali** (1S, 1M, 3M, 6M, 1A, 2A) o selezionare un intervallo **Personalizzato** per passare rapidamente a periodi specifici.

!!! info "Disponibilità dei dati"
    Se l'intervallo selezionato supera i dati disponibili, LibreFolio mostra quello che c'è. Usa **Sincronizza** per provare a scaricare dati più vecchi dal provider — ma nota che alcuni provider hanno una copertura storica limitata.

---

## 💬 Tooltip

Passa il puntatore su qualsiasi punto del grafico per vedere:

- 📅 La **data**
- 💱 Il **tasso di cambio** con piena precisione
- 📊 La **variazione percentuale** rispetto al punto dati precedente

---

## 🧰 Barra degli strumenti

La barra degli strumenti del grafico offre un rapido accesso a:

- 📊 **Modalità di visualizzazione** — Assoluto / Percentuale
- ⏱️ **Intervallo di tempo** — 1S, 1M, 3M, 6M, 1A, 2A, Personalizzato
- 📈 **[Segnali](signals.md)** — Attiva/disattiva sovrapposizioni di indicatori tecnici
- 📏 **[Misure](measures.md)** — Strumento di misurazione click‑to‑click
- ✏️ **[Editor dati](data-editor.md)** — Modifica i singoli punti dati
- ⚙️ **[Impostazioni grafico](../chart-settings.md)** — Personalizzazione visiva

---

## 🔗 Correlati

- ⚙️ **[Impostazioni grafico](../chart-settings.md)** — Personalizza colori, spessore linea, riempimento area, griglia.
- 📈 **[Segnali](signals.md)** — Sovrapponi indicatori tecnici al grafico.
