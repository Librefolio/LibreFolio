# ✂️ Strumento di ritaglio immagine

Inquadra, ruota e ridimensiona un'immagine prima che LibreFolio la salvi.

---

## 🎯 Quando appare?

- 👤 **Immagine del profilo** — in **[Profilo](../settings/profile.md)** o nella pagina di benvenuto: nel
  selettore di immagini, scegli **Carica** e seleziona un'immagine.
- 🏦 **Icona broker** e 📈 **icona asset** — lo stesso selettore, dal modulo broker o asset.
- 📂 **Pagina File** — aggiungi immagini alla lista di caricamento, poi fai clic sul pulsante ✏️ **Modifica** di un'immagine.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Modale modifica immagine" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ✂️ Inquadra l'immagine

- 📏 **Trascina** un angolo o un lato dell'area di ritaglio per ridimensionarla, l'interno per spostarla, l'esterno
  per spostare l'immagine. L'area di ritaglio rimane sempre all'interno dell'immagine.
- 🔍 **Zoom** con la rotellina del mouse o **+ / −** — l'area di ritaglio si stringe (o si allarga) prima, poi
  l'immagine si ingrandisce o si riduce — o esegui un pinch su touch screen.
- 🔄 **Ruota** di 15° alla volta con **↺ / ↻**, e 🪞 **capovolgi** con ↔ / ↕.
- 👁️ Il pulsante con l'icona dell'occhio a sinistra attiva/disattiva un'**anteprima rotonda**: come appare l'immagine in un cerchio, come
  il tuo avatar nella barra laterale.
- 🔁 **Reimposta tutto** (in alto a destra) annulla il ritaglio, lo zoom, la rotazione e il capovolgimento.

---

## 📐 Preimpostazioni

| Preimpostazione | Dimensioni di output | Forma |
|--------|------|-------------|
| **Avatar** | 200 × 200 px | Quadrata, anteprima rotonda attiva |
| **Icona** | 64 × 64 px | Quadrata, anteprima rotonda attiva |
| **Personalizzata** | Come l'area di ritaglio | Libera, o un rapporto a tua scelta: 1:1, 16:9, 4:3, 3:4 |

Le immagini del profilo si aprono con **Avatar**, le icone broker con **Icona** e le immagini della pagina File con
**Personalizzata**; le icone asset vengono ritagliate quadrate a 256 × 256 px. Puoi cambiare preimpostazione in qualsiasi momento.

---

## ⚙️ Impostazioni di output

- 🎨 **Formato** — `.png` (senza perdita, mantiene la trasparenza), `.jpg` (più piccolo, senza trasparenza) o
  `.webp` (migliore compressione), accanto al nome del file, che puoi anche cambiare. Un'immagine `.jpg` o `.webp`
  mantiene il suo formato; qualsiasi altro inizia come `.png`.
- 📊 **Qualità** (solo `.jpg` e `.webp`) — **−** / **+** a passi del 10%, dal 10% al 100%: una qualità
  inferiore significa un file più piccolo.
- 📐 **Output** — larghezza × altezza in pixel, impostate dalla preimpostazione ma modificabili. Le due restano
  proporzionate all'area di ritaglio, e non puoi impostarle più grandi di essa; **Scala** le imposta entrambe
  contemporaneamente.

---

## ✅ Conferma o annulla

- **Ritaglia e carica** salva l'immagine e la utilizza. Nella pagina File, **Ritaglia** la mette invece nella lista
  di caricamento (**Ripristina originale** ↺ riporta l'originale), e **Carica** invia la lista.
- **Annulla** o **✕** chiude lo strumento — dopo aver chiesto conferma, se hai modifiche non salvate
  (**Scarta e chiudi**). Dal selettore di immagini, torni al selettore.

??? info "📄 File che non sono immagini — nella pagina File"

    Un PDF, un CSV o qualsiasi altro file che non sia un'immagine non ha un passaggio di ritaglio: il suo pulsante ✏️ apre invece una semplice
    finestra di dialogo **Rinomina**.

---

## 🔗 Correlati

- 🛠️ **[Componenti di caricamento file e media](../../developer/frontend/components/core-ui/file-upload.md)** — Come è costruito lo strumento (per sviluppatori)
