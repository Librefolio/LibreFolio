# Analisi Duplicazione Codice - Frontend Media Components

**Data**: 23 Febbraio 2026
**Ultimo Aggiornamento**: 23 Febbraio 2026 (Round 3 — post dedup)
**Analisi su**: `frontend/src/lib/components/ui/media/`, modals correlate, `files/+page.svelte`

---

## 📊 Inventario Componenti Analizzati

| File | Righe | Ruolo |
|------|-------|-------|
| `ImageCropper.svelte` | ~1020 | Core crop engine (cropperjs v2 wrapper) |
| `ImageEditModal.svelte` | ~749 | Modal wrapper per crop immagini |
| `FileEditModal.svelte` | ~584 | Modal wrapper per rename file non-immagine |
| `AssetPickerModal.svelte` | ~573 | Modal picker (URL/Existing/Upload) |
| `FileUploader.svelte` | ~583 | Drag & drop file upload con pending list |
| `ImageUploader.svelte` | ~300 | **LEGACY** — vecchio uploader immagini (non più usato attivamente) |
| `LazyImage.svelte` | ~132 | Lazy loading immagini con placeholder |
| `files/+page.svelte` | ~1634 | Pagina Files con upload integration |
| `BrokerImportFilesModal.svelte` | ~483 | Modal import file BRIM |
| `BrokerForm.svelte` | ~560 | Form broker con icon picker |
| `ProfileTab.svelte` | ~807 | Tab profilo con avatar picker |
| `imageCrop.ts` | ~211 | Utility presets + getCroppedImageFromCropper() |

---

## 🔴 Duplicazione ALTA (stessi pattern implementati 3+ volte)

### 1. Pattern "Modal con Conferma Chiusura"

**Implementato in**: `ImageEditModal`, `FileEditModal`, `BrokerImportFilesModal`, `files/+page.svelte` (2 modali inline)

**Codice duplicato** (~70 righe × 5 implementazioni = ~350 righe):
```
- showCloseConfirm state variable
- requestClose() → if hasChanges → show confirm
- confirmClose() → hide confirm → close
- cancelClose() → hide confirm
- handleBackdropClick()
- handleKeydown(Escape)
- Confirm dialog HTML (⚠️ icon, message, Cancel/Discard buttons)
- Confirm dialog CSS (backdrop, dialog, header, actions, btn-warning)
```

**Proposta**: Creare un **`ModalBase.svelte`** che gestisca:
- Backdrop con click-to-close
- Escape key handling
- Close confirmation dialog (opzionale, attivato da prop `hasChanges`)
- Header con titolo + azioni destra (slot)
- Body (slot)
- Footer (slot)
- Animazione apertura/chiusura

**Risparmio stimato**: ~250 righe + consistenza garantita

---

### 2. Pattern "Upload File al Backend"

**Implementato in**: `ImageEditModal.handleUpload()`, `FileEditModal.handleConfirm()`, `files/+page.svelte` (uploadFilesNow + handleDirectUpload), `BrokerImportFilesModal`

**Codice duplicato** (~20 righe × 4-5 implementazioni = ~100 righe):
```typescript
const formData = new FormData();
formData.append('file', file);
const response = await axiosInstance.post('/api/v1/uploads', formData);
const uploadedUrl = response.data.file?.url || response.data.url;
if (!uploadedUrl) throw new Error('No URL in upload response');
```

**Proposta**: Creare utility **`uploadFile(file: File): Promise<UploadedFile>`** in `utils/uploadApi.ts` che centralizzi:
- Costruzione FormData
- POST request
- Estrazione URL da risposta
- Error handling

**Risparmio stimato**: ~60 righe + single point of failure/change

---

### 3. Pattern "CSS Stili Modal"

**Implementato in**: `ImageEditModal`, `FileEditModal`, `AssetPickerModal`, `BrokerImportFilesModal`, `files/+page.svelte`

**CSS duplicato** (~80 righe × 5 = ~400 righe):
```css
.modal-backdrop { position: fixed; inset: 0; z-index: 50; ... }
.modal-content { background: white; border-radius: 1rem; ... }
:global(.dark) .modal-content { background: #1f2937; ... }
.modal-header { display: flex; align-items: center; justify-content: space-between; ... }
.modal-footer { display: flex; justify-content: flex-end; ... }
.btn { display: inline-flex; align-items: center; ... }
.btn-primary { background: #1a4031; color: white; }
.btn-secondary { background: #e5e7eb; ... }
```

**Proposta**: Se `ModalBase.svelte` viene creato, tutto il CSS modale va lì. In alternativa, creare un file CSS condiviso `styles/modal.css` importato dai vari componenti.

**Risparmio stimato**: ~300 righe CSS

---

### 4. Pattern "formatBytes / formatSize"

**Implementato in**: `AssetPickerModal.formatBytes()`, `FileEditModal.formatSize()`, `FilesTable` (nel DataTable formatter), `files/+page.svelte`

**Codice duplicato**: Stessa funzione con nomi diversi (~5 righe × 4 = ~20 righe)

**Proposta**: Già esiste logica simile altrove. Consolidare in **`utils/format.ts`** con:
```typescript
export function formatBytes(bytes: number): string { ... }
```

**Risparmio stimato**: minimo in righe (~15), alto in consistenza

---

## 🟡 Duplicazione MEDIA (pattern simili ma con differenze significative)

### 5. ImageEditModal vs FileEditModal

**Sono modali con la stessa struttura**, ma:
- `ImageEditModal` ha il cropper, bottom panel, ellipse, zoom/rotate
- `FileEditModal` ha solo rename + metadata display

**Ciò che condividono**:
- Props: `open`, `file`, `uploadOnComplete`
- Events: `complete`, `cancel`, `error`
- Logica: `requestClose`, `confirmClose`, `cancelClose`, backdrop click, escape
- CSS: header, footer, buttons, confirm dialog (~200 righe)
- Upload flow: FormData + POST

**Proposta alternativa a ModalBase**: Creare `FileEditModal` come caso semplificato che **usa ImageEditModal** con un prop `mode: 'image' | 'file'` dove in mode `file` non mostra il cropper ma solo filename + metadata. 

**Pro**: Un solo componente  
**Contro**: ImageEditModal è già 749 righe, aggiungere condizionali lo complicherebbe

**Raccomandazione**: Meglio il **`ModalBase.svelte`** approach — mantiene separazione responsabilità.

---

### 6. AssetPickerModal — List View vs FilesTable

**Problema**: Il tab "Existing" nella `AssetPickerModal` ha una lista/griglia custom con HTML+CSS inline, mentre `FilesTable.svelte` wrappa `DataTable` con tutte le funzionalità (sort, filter, pagination).

**Differenze**:
- AssetPickerModal list è **selezione singola** (click per selezionare, doppio click conferma)
- FilesTable è **multi-azione** (delete, download, copy link, bulk actions)
- AssetPickerModal non ha bisogno di pagination/sort

**Proposta**: Non unificare forzatamente — il caso d'uso è abbastanza diverso. Però si potrebbe:
1. Estrarre una **`FileGrid.svelte`** riutilizzabile per la vista griglia con:
   - Props: files, selectedId, onSelect, onDoubleClick
   - Slot per azioni card
2. Usarla sia in `AssetPickerModal` che in `files/+page.svelte` (grid mode)

---

### 7. Profile Avatar Upload vs Broker Icon Upload (BrokerForm + ProfileTab)

**Sono quasi identici**:
```
1. showAssetPicker = true → AssetPickerModal
2. handleAssetPickerSelect → set URL
3. handleAssetPickerUpload → show ImageEditModal
4. handleImageEditComplete → set URL + upload
5. handleImageEditCancel → reopen picker
```

**Codice duplicato**: ~80 righe di handler identici in entrambi i componenti.

**Proposta**: Creare un **custom hook / action** `useImagePicker(options)` che restituisce:
```typescript
const { showPicker, showEditor, handlers, currentUrl } = useImagePicker({
    preset: 'avatar',
    initialUrl: existingUrl,
    onComplete: (url) => saveAvatar(url),
});
```

**Ma attenzione**: in Svelte 4 non ci sono composables come in Vue/React. Si potrebbe:
- Creare un **`ImagePickerWrapper.svelte`** componente che incapsula tutto il flusso
- Props: preset, initialUrl, circularPreview
- Events: change (new URL), remove
- Internamente gestisce AssetPickerModal + ImageEditModal + conferma

**Risparmio stimato**: ~120 righe + meno bug nei flussi paralleli

---

## 🟢 Duplicazione BASSA (accettabile)

### 8. `isImageFile()` — usata in pochi posti, importata da `imageCrop.ts` ✅
### 9. `LazyImage` — usata ovunque, componente singolo ✅
### 10. `DataTable` pattern — riutilizzato via composizione ✅

---

## 📋 Priorità Refactoring

| # | Intervento | Risparmio | Complessità | Priorità | Status |
|---|-----------|-----------|-------------|----------|--------|
| 1 | **ModalBase.svelte** | ~550 righe | Media | 🔴 Alta | 🔲 TODO |
| 2 | **uploadFile() utility** | ~60 righe | Bassa | 🔴 Alta | ✅ FATTO (`utils/upload.ts`) |
| 3 | **formatBytes() centralizzato** | ~15 righe | Minima | 🟡 Media | ✅ FATTO (`utils/upload.ts`) |
| 4 | **ImagePickerWrapper.svelte** | ~120 righe | Media | 🟡 Media | 🔲 TODO |
| 5 | **FileGrid.svelte** estratto | ~80 righe | Media | 🟢 Bassa | 🔲 TODO |
| 6 | **DataTable single-select mode** | n/a (new feature) | Media | 🔴 Alta | ✅ FATTO |
| 7 | **DataTable ImageCell type** | n/a (new feature) | Bassa | 🔴 Alta | ✅ FATTO |
| 8 | **DataTable in AssetPicker** | ~100 righe | Media | 🔴 Alta | 🔲 TODO |
| 9 | **Preview img_preview cache backend** | n/a (perf) | Bassa | 🔴 Alta | ✅ FATTO (PreviewCache class, size-based) |
| 10 | **img_preview everywhere** | ~5 righe | Minima | 🟡 Media | ✅ FATTO |
| 11 | **svelte:component deprecation** | ~1 riga | Minima | 🟡 Media | ✅ FATTO |
| 12 | **FilesTable image alignment** | ~5 righe CSS | Minima | 🟡 Media | ✅ FATTO (cell-icon-box) |
| 13 | **AssetPicker URL ellipse** | ~15 righe CSS | Bassa | 🟡 Media | ✅ FATTO (box-shadow overlay) |

### Feedback Utente (23 Feb 2026)
- **DataTable**: evolverla per supportare `selectionMode: 'single'` (click riga = seleziona, no checkbox) ✅
- **ImageCell**: aggiungere tipo cella con preview thumbnail + fallback icona ✅
- **AssetPicker**: usare DataTable con single-select per la lista file (TODO)
- **Griglia AssetPicker vs Files**: devono usare lo stesso componente base (TODO — FileGrid.svelte)
- **Preview ovunque**: usare `?img_preview=` per risparmiare banda ✅
- **Cache backend**: size-based 50MB (parametrico da .env PREVIEW_CACHE_MAX_MB), TTL 1h ✅
- **svelte:component deprecation**: sostituito con componente dinamico Svelte 5 ✅
- **FilesTable alignment**: immagini/icone centrate, nomi allineati a sinistra in colonna (cell-icon-box) ✅
- **AssetPicker URL ellipse**: full image con box-shadow overlay ✅
- **Backend img_preview >= original**: serve file direttamente senza processamento ✅
- **BRIM file rename**: aggiunto FileEditModal al BrokerImportFilesModal e al BRIM uploader in files/ ✅

---

## 🔭 Ulteriori Ottimizzazioni Identificate (Round 3)

### Duplicazione ALTA — da affrontare prima di Phase 5

| Pattern | Occorrenze | Note |
|---------|-----------|------|
| **Modal backdrop CSS** | 6 componenti (ConfirmModal, BrokerModal, BrokerImportFilesModal, FileEditModal, ImageEditModal, files/+page.svelte) | Stessi stili `.modal-backdrop` + `.modal-content` copiati |
| **handleKeydown (Escape)** | 8+ componenti | Pattern identico `if (event.key === 'Escape')` |
| **Backdrop click handler** | 6 componenti | `event.target === event.currentTarget → close()` |
| **fade/scale transitions** | 6 componenti | `transition:fade={{ duration: 150 }}` + `transition:scale={{ duration: 200, start: 0.95 }}` |

→ Tutto risolvibile con **ModalBase.svelte** (task #1, ~550 righe risparmiate)

### Duplicazione MEDIA — nice to have

| Pattern | Occorrenze | Note |
|---------|-----------|------|
| **formatBytes i18n** | 3 (DataTable, DataTableColumnFilter, files/+page) | Usa `$t()` store — serviva funzione che accetta translator come parametro |
| **Error banner pattern** | 4+ componenti | `{#if error}<div class="error-banner">...` |
| **Loading spinner** | 4+ componenti | Pattern `{#if loading}<div class="loading">...` |

---

## 🏁 Raccomandazione

Il prossimo passo di refactoring più impattante è **ModalBase.svelte**, che eliminerebbe ~550 righe di codice duplicato e standardizzerebbe il comportamento di tutte le modali (Escape, backdrop click, transitions, dark mode). Questo va fatto **prima di Phase 5** (FX Management) perché ogni nuova pagina avrà le sue modali.

**Ordine suggerito**:
1. ✅ ~~Creare `uploadFile()` utility~~ — FATTO in `utils/upload.ts`
2. Creare `ModalBase.svelte` (impatta tutte le modali future)
3. Usare DataTable nel tab Existing di AssetPickerModal
4. Questi possono essere fatti come sub-plan dedicato tra Phase 4 e Phase 5

