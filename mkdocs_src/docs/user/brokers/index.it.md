# 🏦 Broker

Un **Broker** in LibreFolio rappresenta un conto di intermediazione — il luogo dove risiedono i tuoi investimenti (es. Interactive Brokers, Degiro, un conto bancario).

Tutte le transazioni, i report e i dati importati sono collegati a un broker. È necessario almeno un broker per iniziare a monitorare il tuo portafoglio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Elenco Broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Creazione di un Broker

1. Vai alla pagina **Broker** dalla barra laterale
2. Clicca su **"Nuovo Broker"**
3. Compila i dettagli: nome, valuta di base e, opzionalmente, un'icona
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Modulo di modifica Broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

4. Il broker appare nell'elenco, pronto a ricevere transazioni e report
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Dettaglio Broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

---

## 🗂️ Layout dei Dettagli del Broker

Una volta selezionato un broker dall'elenco, l'interfaccia è suddivisa in quattro schede principali:

1. **Panoramica**: Visualizzazione del patrimonio netto, metriche di rendimento, storico della crescita e grafici di allocazione limitati esclusivamente a questo conto broker (vedi **[Panoramica Dashboard](../dashboard/index.md)**).
2. **Posizioni**: Elenco delle posizioni aperte, pesi degli asset e metriche di performance all'interno di questo broker, con accesso al pannello in linea di Analisi Lotti FIFO (vedi **[Posizioni Dashboard](../dashboard/positions.md)**).
3. **Transazioni**: Il registro di tutte le attività finanziarie, incluse voci manuali, importazioni di estratti conto e cronologie (vedi **[Importazione Transazioni](import.md)**).
4. **Info**: Metadati del broker, configurazioni di scoperto di cassa/vendita allo scoperto, Esportazione AI e controlli di condivisione in linea (vedi **[Configurazione & Info](info.md)**).

---

## 📈 Scheda Panoramica

La scheda **Panoramica** funge da dashboard locale per il broker selezionato. Contiene gli stessi elementi della **[Panoramica Dashboard](../dashboard/index.md)** principale ma limitata esclusivamente a questo conto broker:

- **Schede KPI Locali**: Patrimonio Netto, Profitti e Perdite di Periodo e Rendimenti specifici di questo broker. (Vedi **[Schede KPI Dashboard](../dashboard/kpi-cards.md)** per i dettagli di calcolo).
- **Pannello Saldi di Cassa**: Liquidità disponibile in questo conto broker, suddivisa per valuta.
- **Grafico di Crescita**: Storico della crescita del valore di questo conto (vedi **[Grafico di Crescita del Portafoglio](../dashboard/charts.md#portfolio-growth-chart)**).
- **Pannello di Allocazione**: Composizione del portafoglio (per Tipo, Settore e Geografia) per le posizioni detenute presso questo specifico broker (vedi **[Pannello di Allocazione](../dashboard/charts.md#allocation-panel)**).

---

## 🔍 Scheda Posizioni

La scheda **Posizioni** elenca tutti gli asset attivi attualmente detenuti presso questo broker. È identica nella funzionalità alla vista principale **[Posizioni Dashboard](../dashboard/positions.md)**, ma limitata solo a questo broker:

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Posizioni (Tabella)" alt="Vista Tabella Posizioni Broker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Posizioni (Mappa / Treemap)" alt="Vista Mappa Posizioni Broker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Performance (Tabella)" alt="Vista Tabella Performance Broker">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Performance (Mappa / Grafico)" alt="Vista Mappa Performance Broker">
</div>

- **Alternanze e Layout**: Puoi alternare tra metriche di **Posizioni** (quantità, valori, pesi) e **Performance** (Plusvalenze/Minusvalenze non realizzate, ROI %) e scegliere tra un layout a **Tabella** o **Mappa** (treemap).
- **Analisi FIFO**: Clicca su qualsiasi riga o carta di asset per espandere il pannello in linea di **Analisi Lotti FIFO** sotto l'elenco. (Vedi **[Analisi Lotti FIFO](../dashboard/positions.md#fifo-lots-analysis)** per le regole di corrispondenza dettagliate).

---

## 📑 In Questa Sezione

- 📥 **[Importazione Transazioni (BRIM)](import.md)** — Come registrare manualmente le transazioni, eseguire la procedura guidata di importazione BRIM CSV/Excel e visualizzare i log di importazione.
- ⚙️ **[Configurazione & Info](info.md)** — Impostazioni dei metadati (scoperti, vendite allo scoperto), generatore di prompt per Esportazione AI con ambito limitato e pannello di condivisione del broker in linea.
- 🤝 **[Condivisione del Broker](sharing.md)** — Guida dettagliata sui permessi dei ruoli (Proprietario, Editor, Visualizzatore) e sulle impostazioni di percentuale degli asset.
