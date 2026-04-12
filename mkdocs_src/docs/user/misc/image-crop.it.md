# ✂️ Strumento di Ritaglio Immagini

LibreFolio include un potente strumento di editing interattivo per immagini che consente di ritagliare, ruotare e ridimensionare le immagini prima di caricarle.

---

## 🎯 Quando Appare?

La finestra modale di ritaglio immagini si apre automaticamente ogni volta che carichi un file immagine in LibreFolio:

- 📂 **Pagina File** → caricamento di qualsiasi immagine (JPEG, PNG, WebP, GIF)
- 👤 **Impostazioni profilo** → modifica del proprio avatar
- 🏦 **Impostazioni Broker** → modifica dell'icona di un broker

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Modale di editing immagine" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📐 Preset

Lo strumento offre dei preset per i casi d'uso più comuni:

| Preset | Dimensione | Rapporto d'Aspetto | Caso d'Uso |
|--------|------|-------------|----------|
| **Avatar** | 200 × 200 px | 1:1 (quadrato) | Foto profilo utente |
| **Icona Broker** | 64 × 64 px | 1:1 (quadrato) | Loghi dei broker |
| **Personalizzato** | Libero | Libero | Qualsiasi dimensione e rapporto |

Il preset imposta automaticamente il vincolo del rapporto d'aspetto e la dimensione di output.

---

## 🎛️ Controlli

### ✂️ Area di Ritaglio

- 📏 **Trascina gli angoli** per ridimensionare l'area di ritaglio
- ↔️ **Trascina all'interno** dell'area per spostarla
- 🔒 L'area di ritaglio è **vincolata ai bordi dell'immagine** — non è possibile selezionare aree esterne all'immagine

### 🔍 Zoom

- 🖱️ **Rotella del mouse** o **pinch** (su dispositivi touch) per ingrandire/ridurre
- ➕ **Pulsanti Zoom** (+/−) per un controllo preciso
- 🎯 Lo zoom si centra sulla selezione del ritaglio

### 🔄 Rotazione

- 🔄 **Pulsanti di rotazione** (↺/↻) ruotano l'immagine a incrementi di 15°
- 📍 La rotazione avviene rispetto al centro della selezione

### 🪞 Rifletti

- ↔️ **Specchia orizzontalmente** (↔) — specchia l'immagine da sinistra a destra
- ↕️ **Specchia verticalmente** (↕) — specchia l'immagine dall'alto verso il basso

---

## ⚙️ Impostazioni di Output

Prima di confermare, puoi regolare:

- 🎨 **Formato di output**: PNG (senza perdita, trasparenza), JPEG (più piccolo, senza trasparenza), WebP (moderno, miglior compressione)
- 📊 **Qualità** (solo JPEG/WebP): Slider dal 10% al 100% — qualità inferiore = file più piccolo
- 📐 **Dimensione di output**: Larghezza e altezza in pixel (collegate al preset, ma modificabili)

!!! tip "Anteprima Ellisse"

    Per i preset avatar e icona, un **overlay a ellisse** circolare viene mostrato sull'area di ritaglio. Questo ti aiuta a vedere in anteprima come apparirà l'immagine in una cornice circolare (ad es. gli avatar utente nella barra di navigazione).

---

## 🔄 Workflow

1. **Carica o trascina** un file immagine
2. La modale di ritaglio si apre con il preset appropriato
3. **Regola** l'area di ritaglio, lo zoom e la rotazione secondo necessità
4. **Visualizza l'anteprima** del risultato in tempo reale
5. Clicca su **Carica** per confermare — l'immagine ritagliata viene salvata sul server
6. Clicca su **Annulla** o chiudi la modale per scartare le modifiche

!!! info "File non immagine"

    Se carichi un file che non è un'immagine (PDF, CSV, ecc.), la modale di ritaglio viene saltata. Al suo posto, appare un semplice dialogo di rinomina.
