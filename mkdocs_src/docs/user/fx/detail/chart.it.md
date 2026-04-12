# 📉 Grafico Interattivo

Il cuore della pagina Dettagli Coppia: un grafico completo **basato su ECharts** che consente di visualizzare lo storico dei tassi di cambio grazie a potenti strumenti interattivi.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Grafico Dettagli FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Modalità di Visualizzazione

Passa da una modalità di visualizzazione all'altra utilizzando la barra degli strumenti:

- 📈 **Assoluta** — Mostra i valori grezzi del tasso di cambio (es. 1 EUR = 1.0845 USD). Ideale per vedere i livelli effettivi del tasso.
- 📊 **Percentuale (%)** — Mostra la variazione percentuale rispetto al primo punto dati visibile. Ideale per confrontare i movimenti relativi e sovrapporre più segnali.

Passando alla modalità %, tutti i segnali sovrapposti vengono ricalcolati come percentuali rispetto ai rispettivi punti di partenza.

---

## 🔍 Navigazione e Zoom

| Azione | Desktop | Mobile |
|--------|---------|--------|
| **Sposta vista** | Clic + trascina | Touch + trascina |
| **Zoom in** | Rotella mouse su | Pinch out |
| **Zoom out** | Rotella mouse giù | Pinch in |
| **Reset zoom** | Doppio clic | Doppio tocco |

Puoi anche utilizzare i **preset dell'intervallo temporale** (1W, 1M, 3M, 6M, 1Y, 2Y) o selezionare un intervallo di date **Personalizzato** per saltare rapidamente a periodi specifici.

!!! info "Disponibilità dei dati"

    Se l'intervallo temporale selezionato supera i dati disponibili, LibreFolio visualizza tutto ciò che è disponibile. Usa **Sync** per provare a recuperare dati più vecchi dal provider — ma tieni presente che alcuni provider hanno una copertura storica limitata.

---

## 💬 Suggerimento

Passa il mouse su qualsiasi punto del grafico per vedere:

- 📅 La **data**
- 💱 Il **tasso di cambio** con precisione completa
- 📊 La **variazione percentuale** rispetto al punto dati precedente

---

## 🧰 Barra degli Strumenti

La barra degli strumenti del grafico fornisce un accesso rapido a:

- 📊 **Interruttore modalità visualizzazione** — Assoluta / Percentuale
- ⏱️ **Intervallo temporale** — 1W, 1M, 3M, 6M, 1Y, 2Y, Personalizzato
- 📈 **[Segnali](signals.md)** — Attiva/disattiva la sovrapposizione degli indicatori tecnici
- 📏 **[Misure](measures.md)** — Strumento di misurazione punto-punto
- ✏️ **[Editor Dati](data-editor.md)** — Modifica i singoli punti dati
- ⚙️ **[Impostazioni Grafico](../chart-settings.md)** — Personalizzazione visiva

---

## 🔗 Correlati

- ⚙️ **[Impostazioni Grafico](../chart-settings.md)** — Personalizza colori, larghezza linea, riempimento area, griglia
- 📈 **[Segnali](signals.md)** — Sovrapponi indicatori tecnici sul grafico
