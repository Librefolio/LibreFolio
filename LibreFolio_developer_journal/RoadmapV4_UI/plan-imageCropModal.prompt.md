# Piano Aggiornato: Image Crop Modal System

**Data**: 18 Febbraio 2026  
**Ultimo Aggiornamento**: 19 Febbraio 2026  
**Status**: 🔧 FIX IN CORSO (feedback utente ricevuto)  
**Dipende da**: UI Fixes + Settings Stores completati ✅

---

## 🐛 Bug & Fix da Test Manuali (19 Feb 2026)

### Bug Critici

| ID | Descrizione | Priorità | Status |
|----|-------------|----------|--------|
| BUG-IC1 | Files Page: modal crop NON si apre dopo drag, serve pulsante edit accanto al file | Alta | 🔧 |
| BUG-IC2 | Avatar: dopo cancel, secondo click non apre crop (input file non resettato) | Alta | 🔧 |
| BUG-IC3 | Dashboard: avatar non aggiornato dopo modifica (solo sidebar e profile) | Media | 🔧 |
| BUG-IC4 | Rotazione: salva con trasparenza ai bordi invece di crop dopo rotate | Media | 🔧 |
| BUG-IC5 | Rimuovi avatar: nessuna conferma "sei sicuro?" | Bassa | 🔧 |

### UX Improvements Richiesti

| ID | Descrizione | Priorità | Status |
|----|-------------|----------|--------|
| UX-IC1 | Preset: rimuovere "Original", tenere Avatar(200), Icon(64), Custom | Alta | 🔧 |
| UX-IC2 | Custom: permettere aspect ratio libero con maniglie trascinabili | Alta | ⏳ (difficile) |
| UX-IC3 | Box info: tabella 2 righe (originale → scala → output editabile) | Alta | 🔧 |
| UX-IC4 | Zoom: minimo 1x, max = pixel asse più corto | Media | 🔧 |
| UX-IC5 | Rotazione: mostrare preview CSS ruotato (non solo al save) | Media | 🔧 |
| UX-IC6 | Reset separati: uno per zoom, uno per rotation (oltre al globale) | Bassa | 🔧 |
| UX-IC7 | Asset picker: modale intermedia con URL esterno O file esistenti O upload | Alta | ⏳ |
| UX-IC8 | Settings burger: link diretto a Preferences invece di generico Settings | Bassa | 🔧 |

### Note Tecniche

- **UX-IC2 (Free aspect)**: svelte-easy-crop NON supporta maniglie trascinabili.
  - **Decisione**: Migrare a **cropperjs** che supporta:
    - Free crop con maniglie trascinabili
    - Rotazione live preview
    - Flip
    - Zoom
    - API più matura e feature-complete

---

## 🔄 MIGRAZIONE A CROPPERJS v2 ✅ COMPLETATA (19 Feb 2026)

### Motivazione

`svelte-easy-crop` ha limitazioni significative:
- ❌ No maniglie trascinabili per free crop
- ❌ No rotazione live preview (solo al save)
- ❌ No prop `rotation` diretta

`cropperjs v2` offre:
- ✅ Free crop con resize handles
- ✅ Rotazione live con preview
- ✅ Flip orizzontale/verticale
- ✅ Zoom con limiti configurabili
- ✅ API Web Components moderna
- ✅ Touch-friendly
- ✅ CSS built-in (no external stylesheet)

### Cambiamenti Effettuati

1. **Disinstallato** `svelte-easy-crop`
2. **Installato** `cropperjs@^2.1.0`
3. **Riscritto** `ImageCropper.svelte` per API v2:
   - Usa `new Cropper(imageSrc, {container: element})`
   - Metodi: `getCropperImage().$rotate()`, `$scale()`, `$zoom()`
   - Metodi: `getCropperSelection().$toCanvas()`, `aspectRatio`
   - CSS integrato nei Web Components
4. **Aggiornato** `imageCrop.ts`:
   - `getCroppedImageFromCropper()` usa `selection.$toCanvas()`
   - Rimosso vecchio `getCroppedImage()` con canvas manuale
5. **Rimosso** preset `original` (solo avatar, broker-icon, custom)

### API Cropperjs v2 - Riferimento

```typescript
// Inizializzazione
const cropper = new Cropper(imageSrc, {container: element});

// Ottenere componenti
const image = cropper.getCropperImage();      // CropperImage
const selection = cropper.getCropperSelection(); // CropperSelection  
const canvas = cropper.getCropperCanvas();    // CropperCanvas

// Trasformazioni immagine (relative)
image.$rotate(15);           // Ruota di 15 gradi
image.$scale(-1, 1);         // Flip H
image.$zoom(1.5);            // Zoom 50%
image.$center('contain');    // Centra immagine

// Selection properties
selection.aspectRatio = 1;   // 1:1 (NaN = free)
selection.movable = true;
selection.resizable = true;  // Abilita maniglie!

// Ottenere canvas croppato
const croppedCanvas = await selection.$toCanvas({width: 200, height: 200});
```

---

## 📝 NUOVE FEATURE RICHIESTE (19 Feb 2026)

### Feature 1: Pulsante Edit nella Lista File (Files Page)

**Requisito**: Dopo drag&drop file immagine, nella lista pending appare un pulsante edit (matita) accanto alla dimensione. Cliccandolo si apre ImageEditModal.

**Comportamento**:
1. Utente trascina file immagini in upload area
2. File appaiono nella lista con: `[nome] [size] [✏️ edit]`
3. Click su edit → apre ImageEditModal per quel file
4. Le configurazioni (crop, rotate, zoom, output size) vengono salvate in un oggetto `ImageEditConfig`
5. Se utente clicca di nuovo edit, riparte dalla config salvata
6. Click su "Carica" → applica tutte le config e fa upload

**Struttura ImageEditConfig**:
```typescript
interface ImageEditConfig {
  // Crop area (from cropper.getData())
  cropX: number;
  cropY: number;
  cropWidth: number;
  cropHeight: number;
  
  // Transform
  rotation: number;  // degrees
  scaleX: number;    // 1 or -1 (flip H)
  scaleY: number;    // 1 or -1 (flip V)
  
  // Output
  outputWidth: number | null;
  outputHeight: number | null;
  outputFormat: 'png' | 'jpeg' | 'webp';
  outputQuality: number;
  
  // File name
  outputFileName: string;
}
```

### Feature 2: Nome File Editabile

**Requisito**: Nella modale edit, l'utente può modificare il nome di salvataggio.

**UI**:
```
┌─────────────────────────────────────────────────┐
│ File name: [photo_vacanze.png        ]  [.png ▼]│
└─────────────────────────────────────────────────┘
```

- Input text con nome base (senza estensione)
- Dropdown per formato output (cambia anche estensione)
- Default: nome file originale

### Feature 3: Asset Picker Modal (per Avatar, Broker Icon, etc.)

**Requisito**: Modale intermedia che permette di:
1. Inserire URL esterno
2. Selezionare da file esistenti sul server
3. Uploadare nuovo file (→ apre ImageEditModal)

**Flusso**:
```
User clicks "Change Avatar"
       ↓
┌─────────────────────────────────────────────────┐
│  Select Image                           [X]     │
├─────────────────────────────────────────────────┤
│ ○ URL:  [https://example.com/avatar.png    ]   │
│ ○ Existing: [grid of existing images]          │
│ ○ Upload new: [Select file...]                 │
├─────────────────────────────────────────────────┤
│                    [Cancel] [Use Selected]      │
└─────────────────────────────────────────────────┘
```

**Comportamento**:
- Se URL → ritorna `{ type: 'url', url: '...' }`
- Se Existing → ritorna `{ type: 'existing', url: '...' }`
- Se Upload → apre ImageEditModal, poi ritorna `{ type: 'upload', url: '...', config: ImageEditConfig }`

Il chiamante (Avatar, BrokerIcon) riceve sempre un URL finale.

### Feature 4: Output Size Editabile con Scala

**Requisito**: Box info mostra dimensioni con fattore di scala e output editabile.

**UI**:
```
┌───────────────────────────────────────────────────────────┐
│ Original: 1920 × 1080 px                                  │
│ Selection: 800 × 800 px  → ×0.25 → Output: [200] × [200]  │
└───────────────────────────────────────────────────────────┘
```

- Output width/height sono input editabili
- Quando si modifica uno, l'altro si ricalcola mantenendo aspect ratio (se locked)
- Fattore scala = output / selection
- Preset (Avatar, Icon) forzano i valori output

---

## 🔧 Piano Fix Aggiornato (Ordine Implementazione)

### Fase 1: Migrazione cropperjs (PRIORITÀ MASSIMA)

1. Disinstallare svelte-easy-crop, installare cropperjs
2. Riscrivere `ImageCropper.svelte` con cropperjs
3. Aggiornare `getCroppedImage` per usare cropper API
4. Aggiornare `ImageEditModal.svelte` per nuovi controlli
5. Test: rotazione live, free crop con maniglie, flip

### Fase 2: Edit nella Lista File

6. Modificare lista file pending in Files page
7. Aggiungere pulsante edit (matita) per immagini
8. Creare tipo `ImageEditConfig`
9. Salvare config per file, riapplicare su re-edit
10. Applicare config durante upload

### Fase 3: Nome File Editabile

11. Aggiungere input nome file in ImageEditModal
12. Dropdown formato output (png/jpeg/webp)
13. Rinominare file durante upload

### Fase 4: Output Size Editabile

14. Nuova UI tabella dimensioni con scale factor
15. Input editabili per output width/height
16. Ricalcolo automatico con aspect ratio lock

### Fase 5: Asset Picker Modal

17. Creare `AssetPickerModal.svelte`
18. Tab URL esterno
19. Tab file esistenti (fetch da API /uploads)
20. Tab upload nuovo (integra ImageEditModal)
21. Integrare in Avatar, BrokerIcon

### Fase 6: Bug Fix Rimanenti

22. BUG-IC2: Reset input file (già fixato)
23. BUG-IC3: Avatar in Dashboard
24. BUG-IC5: Conferma rimozione avatar
25. UX-IC8: Link Settings → Preferences

---

## 🎯 Obiettivo Rivisto

Creare un **sistema modale unificato** per upload e editing di immagini, con:

- Crop interattivo (svelte-easy-crop)
- Preset configurabili per caso d'uso
- Integrazione con endpoint upload esistente
- Ritorno URL risorsa al chiamante

---

## 📋 Step di Implementazione

### Step 1: Setup & Componenti Base ✅ COMPLETATO (18 Feb 2026)

1. ✅ `npm install svelte-easy-crop` nel frontend
2. ✅ Creare `utils/imageCrop.ts` con presets e utility `getCroppedImage()`
3. ✅ Creare `ImageCropper.svelte` - componente crop puro
4. ✅ Creare `ImageEditModal.svelte` - modale wrapper
5. ✅ Aggiungere traduzioni i18n

**File creati:**

- `frontend/src/lib/utils/imageCrop.ts`
- `frontend/src/lib/components/ui/media/ImageCropper.svelte`
- `frontend/src/lib/components/ui/media/ImageEditModal.svelte`

### Step 2: Integrazione Files Page ✅ COMPLETATO (18 Feb 2026)

1. ✅ Import ImageEditModal in files/+page.svelte
2. ✅ Aggiunto stato per image edit modal
3. ✅ Aggiunto componente ImageEditModal con eventi

**Nota**: L'integrazione è preparata ma la logica di intercettazione immagini
sarà aggiunta nello Step 2.5 per completare il flusso.

### Step 2.5: Completare Logica Intercettazione Immagini ✅ COMPLETATO (18 Feb 2026)

1. ✅ Modificata `handleUpload` per rilevare immagini con `isImageFile()`
2. ✅ Upload diretto per file non-immagine, apertura ImageEditModal per immagini
3. ✅ Gestione coda di immagini multiple con `pendingImageFiles`
4. ✅ Handler `handleImageEditComplete` e `handleImageEditCancel` implementati

### Step 3: Integrazione Broker Icon ✅ COMPLETATO (18 Feb 2026)

1. ✅ Modificato `BrokerForm.svelte` - click su bottone upload apre modale
2. ✅ Preset `broker-icon` (64x64, 1:1) già configurato in `imageCrop.ts`
3. ✅ Su complete → riceve URL e lo imposta in `iconUrl`
4. ✅ ImageEditModal aggiunto al template con eventi corretti

### Step 4: Avatar Utente ✅ COMPLETATO (18 Feb 2026)

1. ✅ Backend: `avatar_url` già presente in UserSettings model + schema + migrazione
2. ✅ API client già sincronizzato con campo avatar_url
3. ✅ Modificato `PreferencesTab.svelte` - sezione avatar con preview e upload
4. ✅ Click su avatar → `ImageEditModal` con preset `avatar` (200x200)
5. ✅ Su complete → salva URL in user settings

**Nota**: Avatar visibile in sidebar sarà implementato nello Step 5 (Polish)

### Step 5: Polish & Testing ✅ COMPLETATO (18 Feb 2026)

1. ✅ Dark mode styling (già implementato nei componenti)
2. ✅ Avatar visibile in Sidebar con link a Settings
3. ✅ Mobile/touch testing (svelte-easy-crop supporta touch gestures nativamente)
4. [ ] E2E tests (opzionale - da fare in sessione separata)

---

## 🔍 Gap Analysis vs Piano Originale

| Aspetto | Piano Originale | Stato Attuale | Azione |
|---------|-----------------|---------------|--------|
| Crop interattivo | Pianificato | ✅ Implementato | Done |
| ImageUploader | Esistente con resize | ✅ Nuovo ImageEditModal | Done |
| FileUploader | Non menzionato | ✅ Integrazione preparata | Step 2.5 |
| Avatar utente | Menzionato | ❌ Campo non esiste nel DB | Step 4 |
| Broker icon | Menzionato | ✅ `icon_url` esiste | Step 3 |
| Modale wrapper | Non dettagliato | ✅ Creato | Done |

---

## 📂 File Creati/Modificati

### Nuovi File Frontend ✅

| File | Descrizione | Status |
|------|-------------|--------|
| `ui/media/ImageEditModal.svelte` | Modale wrapper con upload | ✅ |
| `ui/media/ImageCropper.svelte` | Componente crop (svelte-easy-crop) | ✅ |
| `utils/imageCrop.ts` | Utility: getCroppedImage, presets | ✅ |

### Modifiche Frontend

| File | Modifica | Status |
|------|----------|--------|
| `ui/media/index.ts` | Export nuovi componenti | ✅ |
| `files/+page.svelte` | Import e stato ImageEditModal | ✅ |
| `brokers/BrokerForm.svelte` | Integrazione icon picker | 📋 |
| `settings/tabs/PreferencesTab.svelte` | Sezione Avatar | 📋 |

### Modifiche Backend (Step 4)

| File | Modifica | Status |
|------|----------|--------|
| `db/models.py` | `avatar_url` in UserSettings | 📋 |
| `schemas/settings.py` | `avatar_url` in schemas | 📋 |
| `alembic/versions/001_initial.py` | Colonna avatar_url | 📋 |

---

## 🎨 Preset Configurations ✅

```typescript
export const IMAGE_PRESETS = {
  avatar: { aspectRatio: 1, outputWidth: 200, outputHeight: 200, ... },
  'broker-icon': { aspectRatio: 1, outputWidth: 64, outputHeight: 64, ... },
  custom: { aspectRatio: 0, outputWidth: null, ... }
};
```

---

## 📊 Stima Tempo Aggiornata

| Step | Tempo | Status |
|------|-------|--------|
| Step 1: Setup & Componenti | 1 giorno | ✅ COMPLETATO |
| Step 2: Files Page | 0.5 giorni | ✅ COMPLETATO |
| Step 2.5: Logica intercettazione | 0.25 giorni | ✅ COMPLETATO |
| Step 3: Broker Icon | 0.5 giorni | ✅ COMPLETATO |
| Step 4: Avatar Utente | 1 giorno | ✅ COMPLETATO |
| Step 5: Polish | 0.5 giorni | ✅ COMPLETATO |
| **Totale** | **~3.75 giorni** | ✅ |

---

## 🧪 Test E2E Automatici (Playwright)

### File da creare: `frontend/e2e/image-crop.spec.ts`

#### Suite: Files Page Image Upload

```typescript
// A1: Upload singola immagine apre ImageEditModal
test('uploading image opens ImageEditModal', async ({ page }) => {
  // Navigate to files page
  // Click upload, select image file
  // Assert ImageEditModal is visible
  // Assert crop area is present
});

// A3: Conferma upload salva file
test('confirming crop uploads image', async ({ page }) => {
  // Open ImageEditModal with image
  // Click confirm/upload button
  // Assert modal closes
  // Assert new file appears in list
});

// A4: Cancel chiude senza upload
test('canceling crop does not upload', async ({ page }) => {
  // Open ImageEditModal
  // Click cancel or X
  // Assert modal closes
  // Assert no new file in list
});

// A6: Non-image file uploads directly
test('non-image file uploads without crop modal', async ({ page }) => {
  // Upload a PDF
  // Assert ImageEditModal NOT shown
  // Assert file uploaded directly
});
```

#### Suite: Broker Icon Upload

```typescript
// B1: Upload icona apre modal con aspect ratio 1:1
test('broker icon upload opens modal with 1:1 ratio', async ({ page }) => {
  // Open broker create modal
  // Click icon upload button
  // Select image
  // Assert ImageEditModal visible
  // Assert aspect ratio selector hidden (preset broker-icon)
});

// B2: Conferma icona imposta URL
test('confirming icon sets icon_url field', async ({ page }) => {
  // Upload and confirm icon
  // Assert icon_url input has value
  // Assert icon preview shows image
});
```

#### Suite: Avatar Upload

```typescript
// C1: Upload avatar apre modal con preset avatar
test('avatar upload opens modal with 200x200 preset', async ({ page }) => {
  // Navigate to settings
  // Hover avatar, click change
  // Select image
  // Assert ImageEditModal visible with avatar preset
});

// C2: Avatar visibile dopo salvataggio
test('avatar appears in settings after upload', async ({ page }) => {
  // Upload avatar
  // Assert avatar image visible in profile section
});

// C3: Avatar in sidebar
test('avatar appears in sidebar after upload', async ({ page }) => {
  // Upload avatar
  // Assert sidebar shows user avatar
});

// C4: Remove avatar
test('removing avatar shows default icon', async ({ page }) => {
  // With avatar set, click remove
  // Assert avatar removed, default User icon shown
});
```

#### Suite: Dark Mode

```typescript
// D1: Modal styling in dark mode
test('ImageEditModal has correct dark mode styling', async ({ page }) => {
  // Enable dark mode
  // Open ImageEditModal
  // Assert dark background colors
  // Assert text is light colored
});
```

### data-testid da aggiungere

| Componente | data-testid | Scopo |
|------------|-------------|-------|
| `ImageEditModal` backdrop | `image-edit-modal` | Identificare modal aperto |
| `ImageEditModal` confirm btn | `image-edit-confirm` | Click per confermare |
| `ImageEditModal` cancel btn | `image-edit-cancel` | Click per annullare |
| `ImageCropper` container | `image-cropper` | Verificare presenza cropper |
| `ImageCropper` zoom slider | `image-cropper-zoom` | Interazione zoom |
| `BrokerForm` icon upload btn | `broker-icon-upload` | Trigger upload icona |
| `PreferencesTab` avatar area | `avatar-upload-area` | Area cliccabile avatar |
| `PreferencesTab` avatar remove | `avatar-remove-btn` | Rimuovi avatar |
| `Sidebar` user avatar | `sidebar-user-avatar` | Verificare presenza avatar |

---

## ✅ Success Criteria

- [x] Utente può caricare immagine e vedere crop area interattiva
- [x] Utente può zoom/pan per posizionare crop
- [x] Preview mostra risultato finale in tempo reale (tramite crop area)
- [x] Da Files: upload immagine apre editor, poi upload
- [x] Da Broker: click icona apre editor con preset 64x64, ritorna URL
- [x] Da Settings: sezione avatar con editor preset 200x200, salva in DB
- [x] Avatar visibile in header/sidebar dopo salvataggio
- [x] Dark mode funziona (già implementato nei componenti)
- [x] Mobile-friendly (touch gestures - svelte-easy-crop supporta)

---

## 🔗 Note Backend

La preview immagini esiste già nel backend:

- Endpoint: `GET /api/v1/uploads/files/{file_id}?img_preview=200x200`
- Supporta resize on-the-fly con dimensioni specificate
- Usabile per mostrare thumbnail delle immagini esistenti
