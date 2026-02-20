# Piano Aggiornato: Image Crop Modal System

**Data**: 18 Febbraio 2026  
**Ultimo Aggiornamento**: 20 Febbraio 2026 (ore 10:45)  
**Status**: 🟢 COMPLETATO - Core feature + FileEditModal  
**Dipende da**: UI Fixes + Settings Stores completati ✅

---

## ✅ Stato Attuale (20 Feb 2026)

### Core Features - COMPLETATE ✅
- ✅ Migrazione a cropperjs v2 (Web Components)
- ✅ Free crop con maniglie trascinabili (L-shaped white corners)
- ✅ Rotazione rispetto al centro selezione (trasla-ruota-trasla)
- ✅ Zoom pulsanti funzionanti
- ✅ Flip H/V funzionanti
- ✅ Aspect ratio change centrato con diagonale preservata
- ✅ CSS maniglie: linee bianche agli angoli, niente punti blu
- ✅ Dark mode: maniglie bianche, no verde
- ✅ Traduzioni complete (crop, discardChanges, etc.)
- ✅ **Overlay scuro fix**: CSS Variables (`--theme-color`) su `cropper-canvas`
- ✅ **Drag immagine fuori selezione**: handle "select" → "move"

### FileUploader - COMPLETATO ✅
- ✅ **Pulsante Edit immagini** - icona matita per immagini → apre ImageEditModal
- ✅ **Pulsante Edit file** - icona matita per non-immagini → apre FileEditModal
- ✅ **Pulsante Restore** - annulla modifiche (prima della matita)
- ✅ **File editati evidenziati** - bordo blu e sfondo leggero
- ✅ **replaceFile()** - sostituisce file croppati/rinominati con reattività corretta
- ✅ **uploadOnComplete prop** - ImageEditModal può croppare senza uploadare

### ImageEditModal - COMPLETATO ✅
- ✅ **Testo pulsante dinamico** - "Crop" o "Crop & Upload"
- ✅ **Controlli in overlay** - zoom/rotation/reset nel riquadro a destra
- ✅ **Reset singolo** - solo 1 reset nell'overlay
- ✅ **Conferma chiusura** - dialogo arancione se ci sono modifiche non salvate
- ✅ Rimosso preset "Original" (solo avatar, broker-icon, custom)

### FileEditModal - COMPLETATO ✅ (20 Feb 2026)
- ✅ **Modale per file non-immagine** - rename file prima dell'upload
- ✅ **Input nome file + estensione** - estensione mostrata come badge non editabile
- ✅ **Info file** - mostra size e type del file originale
- ✅ **Stessa API di ImageEditModal** - events complete/cancel/error
- ✅ **Conferma chiusura** - dialogo arancione se ci sono modifiche
- ✅ **uploadOnComplete prop** - può rinominare senza uploadare
- ✅ **Integrato in files page** - FileUploader dispatcha editFile, files page gestisce
- ✅ **Traduzioni i18n** - uploads.editFile, uploads.rename, uploads.renameAndUpload

### Bug Fix: Freeze selezione oltre bordo ✅ (20 Feb 2026)
- ✅ **Sostituito** `queueMicrotask` con `requestAnimationFrame` per guard release
- ✅ **Aggiunto** `clampDepth` counter come safety valve (max 2)
- ✅ **Usato** `cropperSelection.$change()` atomico anziché proprietà singole
- ✅ **Threshold** 0.5px per evitare micro-clamping inutile

### Bottom Panel Redesign + Output Size ✅ (20 Feb 2026)
- ✅ **Output size editabile** — input width/height interdipendenti con aspect ratio
- ✅ **Scale factor editabile** — range 0.01-1.00, ricalcola output automaticamente
- ✅ **Quality spinner** — solo per JPEG/WebP, step ±10%, range 10-100%
- ✅ **Preview ellisse** — Eye toggle, auto-on per avatar/icon, auto-off per custom
- ✅ **Flip spostato nell'overlay** — accanto a zoom/rotate/reset, con separatore
- ✅ **Bottom panel compatto** — preset → output/scale → aspect ratio (se custom) → quality
- ✅ **Filename in cima** — coerente in ImageEditModal e FileEditModal
- ✅ **Format selector** — .png/.jpg/.webp integrato nell'area filename

### Note Tecniche
- **CSS Variables per Shadow DOM**: `--theme-color` e `--cropper-backdrop-color` ereditati
- **Reattività Svelte**: Usare espressioni inline nel template, non funzioni
- **Rotazione pivot**: Tecnica trasla-ruota-trasla per ruotare rispetto al centro selezione
- **Anti-freeze**: `isClamping` + `clampDepth` + `$change()` atomico + `requestAnimationFrame`

---

## 🐛 Bug Risolti

| ID | Descrizione | Status |
|----|-------------|--------|
| BUG-IC1 | Files Page: serve pulsante edit accanto al file per aprire crop | ✅ |
| BUG-IC2 | Avatar: dopo cancel, secondo click non apre crop | ✅ Fix: reset input via ref |
| BUG-IC3 | Dashboard: avatar non aggiornato dopo modifica | ✅ Fix: aggiorna userSettings store + avatar in dashboard |
| BUG-IC5 | Rimuovi avatar: nessuna conferma "sei sicuro?" | ✅ Fix: modale conferma |
| BUG-IC6 | FREEZE: selezione oltre bordo canvas causa infinite loop | ✅ Fix: $change() atomico + clampDepth + requestAnimationFrame |

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

### Feature 1: Pulsante Edit nella Lista File (Files Page) ✅ COMPLETATA

**Requisito**: Dopo drag&drop file immagine, nella lista pending appare un pulsante edit (matita) accanto alla dimensione. Cliccandolo si apre ImageEditModal.

**Implementato**:
- ✅ Pulsante matita (Pencil) per file immagine
- ✅ Pulsante restore (RefreshCw) per file editati - PRIMA della matita
- ✅ File editati evidenziati con bordo blu
- ✅ Ordine: `[icona] [nome] [🔄 restore?] [✏️ edit] [size] [✕ remove]`
- ✅ Click edit → apre ImageEditModal con `uploadOnComplete=false`
- ✅ Crop salva nel file pending, non fa upload
- ✅ Click "Carica" → upload diretto dei file (già croppati se editati)

### Feature 2: Nome File Editabile ✅ COMPLETATA

**Requisito**: Nella modale edit, l'utente può modificare il nome di salvataggio.

**Implementato**:
- ✅ Input per nome file (senza estensione)
- ✅ Dropdown per formato output (png/jpg/webp)
- ✅ Nome estratto automaticamente dal file originale
- ✅ Formato rilevato dal tipo MIME del file
- ✅ Nome e formato usati durante save/upload

### Feature 2.5: Sistema Zoom Unificato ✅ COMPLETATA

**Requisito**: Zoom con rotellina prima modifica selezione, poi immagine.

**Implementato**:
- ✅ Zoom IN: prima ingrandisce selezione, quando QUALUNQUE asse ≥90% → zooma immagine
- ✅ Zoom OUT: prima rimpicciolisce selezione, quando QUALUNQUE asse ≤50% → dezooma immagine
- ✅ Rotellina mouse intercettata con `on:wheel={handleWheel}`
- ✅ Soglie basate su percentuale per asse (non pixel assoluti)
- ✅ Selezione sempre clampata dentro canvas bounds
- ✅ `scaleSelection()` rispetta bounds = intersezione canvas ∩ image
- ✅ Maniglie sempre visibili

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
│ ○ URL:  [https://example.com/avatar.png    ]    │
│ ○ Existing: [grid of existing images]           │
│ ○ Upload new: [Select file...]                  │
├─────────────────────────────────────────────────┤
│                    [Cancel] [Use Selected]      │
└─────────────────────────────────────────────────┘
```

**Comportamento**:
- Se URL → ritorna `{ type: 'url', url: '...' }`
- Se Existing → ritorna `{ type: 'existing', url: '...' }`
- Se Upload → apre ImageEditModal, poi ritorna `{ type: 'upload', url: '...', config: ImageEditConfig }`

Il chiamante (Avatar, BrokerIcon) riceve sempre un URL finale.

### Feature 4: Output Size Editabile con Scala ✅ IMPLEMENTATA (20 Feb 2026)

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

**Redesign bottom panel (ImageEditModal)**:
La parte bassa della modale (sotto il cropper) deve essere ripensata per una UX più compatta e user-friendly.
Attualmente ci sono vari blocchi separati (info, output, preset) che occupano troppo spazio verticale.

Proposta layout bottom panel:
```
┌─────────────────────────────────────────────────────────────────┐
│ FILE NAME                                                       │
│ [filename________________] [.png ▼]                             │
├─────────────────────────────────────────────────────────────────┤
│ DIMENSIONS              │ OUTPUT PRESET                         │
│ Input:  1920 × 1080 px  │ [Avatar(200)] [Icon(64)] [Custom]    │
│ Select:  800 ×  800 px  │                                      │
│ Output: [200] × [200] 🔒│ FORMAT & QUALITY                     │
│ Scale:  ×0.25           │ [PNG] [JPG] [WEBP]  Quality: [90%]   │
├─────────────────────────────────────────────────────────────────┤
│ ASPECT RATIO (solo se custom)                                   │
│ [1:1] [16:9] [4:3] [3:4] [Free]                                │
├─────────────────────────────────────────────────────────────────┤
│ FLIP                                                            │
│ [↔ H] [↕ V]                                                    │
└─────────────────────────────────────────────────────────────────┘
```

- Il filename editor rimane in cima alla modale (prima del cropper) ✅ già fatto
- Le dimensioni sono in una griglia compatta 2 colonne
- Output width/height sono input inline editabili con lock aspect ratio
- Il fattore di scala si calcola automaticamente: output/selection
- Preset selector e format/quality sulla destra della stessa riga
- Aspect ratio e flip rimangono in basso, compatti
- Su mobile tutto diventa 1 colonna

### Feature 5: Miglioramenti Grid View Files Page

**Requisito**: La grid view nella Files Page ha diverse inconsistenze con la table view:

**Bug/Mancanze da correggere**:

1. **Azioni mancanti**: La grid card non ha "Copy Link", la table sì
2. **Design azioni**: Il cestino non è rosso in grid (è `danger` ma manca l'effetto visivo senza hover)
3. **Layout card**: Attualmente sono 2 righe (nome+meta, azioni). Devono essere 3 righe:
   - **Riga 1 - Titolo**: nome file (troncato con ellipsis)
   - **Riga 2 - Metadati**: size • data • user (se multi-utente)
   - **Riga 3 - Azioni**: allineate a destra, stesse della tabella (download, copy link, delete)
4. **Search in grid mode**: Campo di ricerca per nome file sopra la griglia
5. **Filtro utente**: Se ci sono più utenti registrati, mostrare colonna utente e filtro dropdown
   - In table: nuova colonna "Uploaded by" (come la colonna Broker in BRIM)
   - In grid: filtro dropdown accanto al search
   - Filtro solo frontend (nessuna restrizione backend per utente)

**File coinvolti**:
- `frontend/src/routes/(app)/files/+page.svelte` — grid view template + filtri
- `frontend/src/lib/components/files/FilesTable.svelte` — aggiungere colonna user se multi-utente
- Backend: l'API `/api/v1/uploads` già restituisce `user_id` nei metadati
- Necessario: endpoint per lista utenti o estrazione utenti unici dai file

**Riutilizzo codice esistente**:
- Riutilizzare lo stesso pattern filtri di `FilesTable` (tipo colonna enum, `urlFilters`)
- Riutilizzare `BrokerSearchSelect` come pattern per UserFilter dropdown

### Feature 6: Asset Picker Modal - Existing Files Browser

**Requisito**: Quando nell'Asset Picker Modal (Feature 3) si sceglie "Existing", deve aprirsi una modale che mostra fondamentalmente il tab Static di files/, con:

1. **Switch tabella/griglia** — come in files page
2. **Ricerca per nome** — campo search, filtro client-side
3. **Preview immagini in griglia** — LazyImage con img_preview
4. **Click per selezionare** — ritorna URL del file selezionato

**Implementazione**:
- Creare `StaticFileBrowser.svelte` componente riutilizzabile
- Usato sia dentro AssetPickerModal che potenzialmente in altri contesti
- Accetta prop `filterMimeTypes?: string[]` per filtrare solo immagini (o solo CSV, etc.)
- Emette evento `select: { file: UploadedFile }` quando un file viene selezionato
- Include sia la modalità griglia (con LazyImage) che la modalità tabella (con DataTable)

**UI**:
```
┌──────────────────────────────────────────────────────────────┐
│  Select existing file                                   [X]  │
├──────────────────────────────────────────────────────────────┤
│ 🔍 [Search by name...            ]  [User ▼]  [☰] [⊞]     │
├──────────────────────────────────────────────────────────────┤
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐             │
│  │ img │  │ img │  │ img │  │ img │  │ img │              │
│  │ 📸  │  │ 📸  │  │ 📸  │  │ 📸  │  │ 📸  │              │
│  │name │  │name │  │name │  │name │  │name │              │
│  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘             │
│                                                              │
│  ┌─────┐  ┌─────┐  ┌─────┐                                 │
│  │ img │  │ img │  │ img │                                  │
│  │ 📸  │  │ 📸  │  │ 📸  │                                  │
│  │name │  │name │  │name │                                  │
│  └─────┘  └─────┘  └─────┘                                 │
├──────────────────────────────────────────────────────────────┤
│                               [Cancel]  [Use Selected]      │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Piano Fix Aggiornato (Ordine Implementazione)

### Fase 1: Migrazione cropperjs ✅ COMPLETATA
### Fase 2: Edit nella Lista File ✅ COMPLETATA  
### Fase 3: Nome File Editabile + FileEditModal ✅ COMPLETATA
### Fase 2.5: Zoom Unificato ✅ COMPLETATA
### Bug Fix: Freeze selezione ✅ COMPLETATA

### Fase 4: Output Size Editabile + Bottom Panel Redesign ✅ COMPLETATA

14. ✅ Riprogettato bottom panel di ImageEditModal con layout compatto
15. ✅ Input editabili per output width/height (interdiendenti con aspect ratio)
16. ✅ Icona Lock per indicare che aspect ratio è bloccato
17. ✅ Scale factor calcolato e editabile (0.01-1.00)
18. ✅ Preset forzano output (Avatar 200px, Icon 64px), custom permette editing
19. ✅ Format selector in filename area + quality spinner (solo JPEG/WebP)
20. ✅ Preview ellisse (Eye toggle) — auto-on per avatar/icon, auto-off per custom
21. ✅ Flip spostato nell'overlay immagine (accanto zoom/rotate)
22. ✅ Responsive: 1 colonna su mobile

### Fase 5: Grid View Improvements + User Filter 📋

21. Grid card layout 3 righe: titolo, metadati, azioni
22. Aggiungere "Copy Link" alle azioni nella grid
23. Cestino rosso consistente in grid e tabella
24. Search per nome in grid mode (input sopra la griglia)
25. Filtro utente: colonna in tabella + dropdown in grid (se multi-utente)
26. Riutilizzare pattern filtri da FilesTable/urlFilters
27. Filtro frontend-only (nessuna restrizione backend)

### Fase 6: Asset Picker Modal 📋

28. Creare `AssetPickerModal.svelte` con 3 tab (URL / Existing / Upload)
29. Tab URL: input + preview LazyImage
30. Tab Existing: Creare `StaticFileBrowser.svelte` (griglia/tabella, search, filtri)
31. Tab Upload: apre ImageEditModal, ritorna URL
32. Integrare in Avatar (ProfileTab) e BrokerIcon (BrokerForm)

### Fase 7: Bug Fix Rimanenti ✅ COMPLETATA

33. ✅ BUG-IC2: Reset input file
34. ✅ BUG-IC3: Avatar in Dashboard
35. ✅ BUG-IC5: Conferma rimozione avatar
36. ✅ BUG-IC6: Freeze selezione oltre bordo

---

## 🎯 Obiettivo Rivisto

Creare un **sistema modale unificato** per upload e editing di file, con:

- Crop interattivo (cropperjs v2 Web Components)
- Preset configurabili per caso d'uso (avatar, icon, custom)
- Rename per qualsiasi tipo di file (FileEditModal)
- Asset Picker per selezionare da URL/file esistenti/upload nuovo
- Output Size editabile con scale factor
- Grid view migliorata con filtri utente e search
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
