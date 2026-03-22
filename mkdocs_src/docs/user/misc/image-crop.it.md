# ✂️ Strumento di Ritaglio Immagini

LibreFolio include un potente strumento di editing interattivo delle immagini che ti permette di ritagliare, ruotare e ridimensionare le immagini prima di caricarle.

---

## 🎯 Quando appare?

Il modale di ritaglio si apre automaticamente ogni volta che carichi un file immagine in LibreFolio:

- 📂 **Pagina File** → caricando qualsiasi immagine (JPEG, PNG, WebP, GIF)
- 👤 **Impostazioni profilo** → cambiando il tuo avatar
- 🏦 **Impostazioni broker** → cambiando l'icona di un broker

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Modale di Modifica Immagine" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📐 Configurazioni predefinite

Lo strumento offre configurazioni predefinite per i casi d'uso comuni:

| Configurazione | Dimensioni | Proporzioni | Caso d'uso |
|----------------|------------|-------------|------------|
| **Avatar** | 200 × 200 px | 1:1 (quadrato) | Foto profilo |
| **Icona Broker** | 64 × 64 px | 1:1 (quadrato) | Loghi broker |
| **Personalizzata** | Libere | Libere | Qualsiasi dimensione e rapporto |

La configurazione predefinita imposta automaticamente il vincolo delle proporzioni e la dimensione di output.

---

## 🎛️ Controlli

### ✂️ Area di Ritaglio

- 📏 **Trascina gli angoli** per ridimensionare l'area di ritaglio
- ↔️ **Trascina all'interno** per spostarla
- 🔒 L'area di ritaglio è **vincolata ai bordi dell'immagine** — non puoi selezionare al di fuori dell'immagine

### 🔍 Zoom

- 🖱️ **Rotellina del mouse** o **pinch** (su dispositivi touch) per zoomare avanti/indietro
- ➕ **Pulsanti zoom** (+/−) per un controllo preciso
- 🎯 Lo zoom si centra sulla selezione di ritaglio

### 🔄 Rotazione

- 🔄 **Pulsanti di rotazione** (↺/↻) ruotano a passi di 15°
- 📍 La rotazione avviene rispetto al centro della selezione

### 🪞 Ribaltamento

- ↔️ **Ribalta Orizzontalmente** (↔) — specchia l'immagine sinistra-destra
- ↕️ **Ribalta Verticalmente** (↕) — specchia l'immagine alto-basso

---

## ⚙️ Impostazioni di Esportazione

Prima di confermare, puoi regolare:

- 🎨 **Formato di esportazione**: PNG (senza perdita, con trasparenza), JPEG (più piccolo, senza trasparenza), WebP (moderno, compressione migliore)
- 📊 **Qualità** (solo JPEG/WebP): Cursore dal 10% al 100% — qualità più bassa = file più piccolo
- 📐 **Dimensione del file risultante**: Larghezza e altezza in pixel (collegata alla configurazione predefinita, ma modificabile)

!!! tip "Anteprima Ellisse"
    Per le configurazioni **Avatar** e **Icona Broker**, viene mostrata una **sovrapposizione ellittica** circolare sull'area di ritaglio. Questo ti aiuta a vedere un'anteprima di come l'immagine apparirà in una cornice circolare (es. avatar utente nella barra di navigazione).

---

## 🔄 Flusso di lavoro

1. **Carica o trascina** un file immagine
2. Il modale di ritaglio si apre con la configurazione predefinita appropriata
3. **Regola** l'area di ritaglio, lo zoom, la rotazione secondo necessità
4. **Controlla l'anteprima** del risultato
5. Clicca **Carica** per confermare — l'immagine ritagliata viene salvata sul server
6. Clicca **Annulla** o chiudi il modale per scartare le modifiche

!!! info "File non immagine"
    Se carichi un file non immagine (PDF, CSV, ecc.), il modale di ritaglio viene saltato. Al suo posto appare una semplice finestra di dialogo per la ridenominazione.
