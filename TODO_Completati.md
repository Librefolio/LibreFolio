# TODO COMPLETATI

Questo file documenta i TODO che sono stati completati durante lo sviluppo di LibreFolio.

---

## 🖼️ File Uploader Image Preview ✅

**Data aggiunta**: 23 Gennaio 2026  
**Data completamento**: 19 Febbraio 2026  
**Status**: ✅ COMPLETATO

### Contesto
Il FileUploader supporta upload multiplo di qualsiasi tipo di file. Per le immagini era necessario:
- Anteprima dell'immagine con crop prima dell'upload
- Resize/crop tramite ImageEditModal (cropperjs v2)
- Pulsante Edit (matita) nella lista file pending per le immagini
- Pulsante Restore per annullare le modifiche

### Implementazione
- Migrato a **cropperjs v2** (Web Components) per crop interattivo con maniglie
- Creato **ImageEditModal** con preset (Avatar 200×200, Icon 64×64, Custom)
- Creato **FileEditModal** per rinominare file non-immagine
- Creato **ImageCropper** con zoom unificato, rotazione, flip, preview ellisse
- Integrato in files page con pulsanti edit/restore nella lista pending
- Output size editabile con scale factor e quality control

### File coinvolti
- `frontend/src/lib/components/ui/media/ImageCropper.svelte`
- `frontend/src/lib/components/ui/media/ImageEditModal.svelte`
- `frontend/src/lib/components/ui/media/FileEditModal.svelte`
- `frontend/src/lib/components/ui/media/FileUploader.svelte`
- `frontend/src/lib/utils/imageCrop.ts`

---

## 🖼️ Image Crop Component ✅

**Data aggiunta**: 22 Gennaio 2026  
**Data completamento**: 20 Febbraio 2026  
**Status**: ✅ COMPLETATO

### Contesto
Implementare crop avanzato per avatar e icone broker.

### Implementazione
Implementato con cropperjs v2 (non svelte-easy-crop come inizialmente pianificato).
Vedi `LibreFolio_developer_journal/RoadmapV4_UI/plan-imageCropModal.prompt.md` per dettagli completi.

---

