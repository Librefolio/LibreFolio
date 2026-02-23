# Piano Aggiornato: Image Crop Modal System

**Data**: 18 Febbraio 2026  
**Ultimo Aggiornamento**: 20 Febbraio 2026 (ore 19:00)  
**Status**: 🟢 COMPLETATO — Tutte le feature implementate, test E2E da scrivere  
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
- ✅ **2-column CSS Grid layout** — sinistra: preset/output/scale, destra: ratio/info
- ✅ **Output size editabile** — input width/height interdipendenti con aspect ratio
- ✅ **Scale factor sempre visibile** — range 0.01-1.00, ricalcola output automaticamente
- ✅ **Quality sulla riga filename** — spinner solo per JPEG/WebP, step ±10%
- ✅ **Preview ellisse** — Eye toggle su SINISTRA, auto-on per avatar/icon
- ✅ **Flip nell'overlay** — accanto a zoom/rotate/reset, con separatore
- ✅ **Aspect ratio nel panel** — colonna destra, solo per custom preset
- ✅ **Rimossa sezione Input/Selection** — assorbita nel bottom panel
- ✅ **Preset senza dimensioni** — solo "Avatar", "Icon", "Custom"
- ✅ **Preset chiama cropper.selectAspect()** — selezione cambia aspect ratio
- ✅ **Live update output** — `on:input` anziché `on:change`
- ✅ **Titolo generico Icon** — "Upload Icon" riusabile per qualsiasi contesto
- ✅ **0 errori, 0 warnings** — svelte-check pulito

### UI Polish Round 3 ✅ (20 Feb 2026 ore 12:30)
- ✅ **Ellipse overlay fix**: box-shadow 9999px per coprire l'area fuori il cerchio nella selezione
- ✅ **Maniglie visibili con ellisse**: le handle rimangono operative sopra l'overlay circolare
- ✅ **Eye toggle in alto a sinistra**: spostato da bottom-left a top-left
- ✅ **Bottom panel swap colonne**: LEFT = preset + aspect ratio, RIGHT = input/selection + output/scale
- ✅ **Scale input più largo**: 56px per migliore usabilità
- ✅ **Reset all funzionante**: `resetAll()` esportato da ImageCropper, rimosso dall'overlay (solo header)
- ✅ **Drag fuori modale**: mousedown tracking per prevenire false close durante trascinamento
- ✅ **CSS cleanup**: rimossi stili inutilizzati (.overlay-btn.reset)
- ✅ **TODO riorganizzati**: `TODO_FUTURI.md` pulito, `TODO_Completati.md` creato, appunti utente documentati

### UI Polish Round 4 ✅ (20 Feb 2026 ore 13:10)
- ✅ **Colonne swap corretto**: LEFT = info+output+scale, RIGHT = preset+aspect ratio
- ✅ **Scale allineato con Y di output**: spacer 52px allineato con secondo dim-input
- ✅ **Ellipse fix completo**: JS-based overlay (div reale posizionato sopra la selezione), non più CSS :has()
- ✅ **Auto-resetAll al primo edit**: `needsInit` flag per allineare selezione/size all'apertura modale
- ✅ **Drag fuori modale fix v2**: traccia `mouseDownTarget` per distinguere drag da click backdrop
- ✅ **resetAll esportato**: funzione accessibile da ImageEditModal via `cropper?.resetAll?.()`
- ✅ **Reset rimosso da overlay**: solo nel header modale

### Feature 6: AssetPickerModal ✅ COMPLETATA (20 Feb 2026)
- ✅ **AssetPickerModal creato** — modale con 3 tab: Existing, URL, Upload
- ✅ **Tab Existing**: griglia/lista con search, view toggle, selezione singola, doppio click conferma
- ✅ **Tab URL**: input con validazione, preview immagine con LazyImage, cerchio overlay
- ✅ **Tab Upload**: trigger file input hidden, dispatch 'upload' event per genitore
- ✅ **Integrato in BrokerForm**: click icona → AssetPickerModal → URL o ImageEditModal
- ✅ **Integrato in ProfileTab**: click avatar → AssetPickerModal → URL o ImageEditModal
- ✅ **Traduzioni i18n**: selectAsset, existingFiles, fromUrl, uploadNew, imageUrl, useSelected, selectIcon, selectAvatar, urlHint
- ✅ **A11y compliant**: tabindex=-1, label for/id, 0 errori 0 warnings

### UI Polish Round 5 ✅ (20 Feb 2026 ore 18:00)
- ✅ **Ellipse overlay contenuta**: `overflow: hidden` su `.crop-wrapper` per evitare che box-shadow 9999px copra la modale
- ✅ **Zoom logic corretta**: + prima riduce selezione poi zooma sfondo, - prima ingrandisce selezione poi dezooma sfondo
- ✅ **Clamping selezione migliorato**: usa bounds canvas e vincoli più stretti per prevenire overflow
- ✅ **BrokerForm icon clickable**: click sull'icona apre AssetPickerModal (rimosso campo URL visibile)
- ✅ **AssetPickerModal initialUrl prop**: pre-popola il campo URL con il valore corrente
- ✅ **AssetPickerModal circularPreview prop**: overlay cerchio nella preview URL per avatar/icon
- ✅ **URL preview auto-dimensionata**: max-height 250px, width 100%, centrata
- ✅ **URL hint text**: "Enter a remote URL or a local path from Files"
- ✅ **URL mostrata sotto icona in BrokerForm**: testo troncato con tooltip

### UI Polish Round 6 ✅ (20 Feb 2026 ore 19:00)
- ✅ **Fix `__upload__` contamination**: upload non più dispatcha `select` con URL `__upload__`
- ✅ **Cancel upload → reopen picker**: cancellando ImageEditModal riapre AssetPickerModal
- ✅ **Tab iniziale intelligente**: se c'è initialUrl → tab URL, altrimenti → tab Existing
- ✅ **Reset URL corretto**: urlInput resettato correttamente on open (non on close)
- ✅ **Filter `__upload__` in parents**: BrokerForm e ProfileTab filtrano `__upload__` dal select handler
- ✅ **ResetAll con margine**: free mode usa 95% coverage (margine sottile visibile)
- ✅ **Active clamping durante drag**: `pointerdown`/`pointerup` + `requestAnimationFrame` loop per enforcement continuo
- ✅ **Threshold clamping stretto**: 0.1px di threshold per prevenire micro-leak
- ✅ **Rimozione duplicato**: rimossa vecchia `handleAvatarModalCancel` duplicata in ProfileTab
- ✅ **0 errori, 0 warnings** — svelte-check + build puliti

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

**Requisito**: Bottom panel compatto a 2 colonne con tutte le info di output editabili.

**Layout finale implementato**:
```
[filename_______________] [.png ▼] [−90%+]    ← quality solo per JPEG/WebP
╔═══════════════════════════╦══════════════════════════════╗
║ LEFT COLUMN               ║ RIGHT COLUMN                 ║
║ Preset: [Avatar] [Icon]   ║ Ratio: [1:1] [16:9] ... Free║ ← solo custom
║        [Custom]            ║                              ║
║ Output: [200] × [200] px 🔒║ Input:  1920 × 1080 px      ║
║ Scale:  ×[0.25]           ║ Selection: 800 × 800 px     ║
╚═══════════════════════════╩══════════════════════════════╝
```

**Cambiamenti chiave (20 Feb 2026 - fix round 2)**:
- ✅ Rimossa sezione "Input/Selection" standalone — assorbita nel panel destro
- ✅ Aspect ratio DENTRO il bottom panel (colonna destra), non fuori
- ✅ 2 colonne CSS Grid — sinistra: preset/output/scale, destra: ratio/info
- ✅ Quality sulla stessa riga del filename (non nel panel)
- ✅ Scale SEMPRE visibile (non solo quando output diverso da selection)
- ✅ Output aggiornamento LIVE con `on:input` anziché `on:change`
- ✅ Ellisse toggle a SINISTRA dell'immagine (opposto ai controlli)
- ✅ Preset senza dimensioni nel label (solo "Avatar", "Icon", "Custom")
- ✅ Preset cambia aspect ratio del cropper (`cropper.selectAspect()`)
- ✅ Titolo broker-icon generico → "Upload Icon" (riusabile per asset, forex, etc.)
- ✅ Rimosso `showAspectSelector` prop dal ImageCropper (gestito da ImageEditModal)
- ✅ `selectAspect()` e `getCurrentAspect()` esportate da ImageCropper
- ✅ Responsive: 1 colonna su mobile (<520px)

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

### Fase 5: Grid View Improvements + User Filter ✅ COMPLETATA (parziale)

> ⚠️ **Spostata prima di Asset Picker** perché Feature 6 (Asset Picker → Existing) dipende dal componente StaticFileBrowser che richiede le migliorie alla grid.

21. ✅ Grid card layout 3 righe: titolo, metadati, azioni (aligned right)
22. ✅ Aggiunto "Copy Link" alle azioni nella grid (con feedback ✓ verde)
23. ✅ Cestino rosso consistente in grid e tabella (rosso di default, non solo hover)
24. ✅ Search per nome in grid mode (input con icona lente + clear)
25. ⏳ Filtro utente: **DEFERRED** — richiede endpoint `/api/v1/users` backend (non esiste)
    - L'UploadedFile ha `uploaded_by_user_id` ma non c'è modo di risolverlo in username
    - Da implementare quando si aggiunge un'API admin user list (vedi TODO_FUTURI.md)
26. ✅ Riutilizzato pattern clipboard da FilesTable per copyFileLink
27. N/A Filtro frontend-only — deferred con punto 25

### Fase 6: Asset Picker Modal ✅ COMPLETATA

28. ✅ Creato `AssetPickerModal.svelte` con 3 tab (URL / Existing / Upload)
29. ✅ Tab URL: input + preview LazyImage + cerchio overlay + initialUrl + hint
30. ✅ Tab Existing: griglia/lista con search, view toggle, selezione singola
31. ✅ Tab Upload: apre ImageEditModal, cancel riapre picker
32. ✅ Integrato in Avatar (ProfileTab) e BrokerIcon (BrokerForm)
33. ✅ BrokerForm: icon clickable, rimosso campo URL visibile
34. ✅ Tab iniziale intelligente: initialUrl → URL, altrimenti → Existing
35. ✅ Fix `__upload__` contamination nel flusso upload/cancel

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

> **Prerequisiti test**: Utente autenticato, DB popolato con `./dev.py test db populate --force`
> **File di test**: Creare cartella `frontend/e2e/fixtures/` con immagini e file di test

#### Suite 1: Files Page — Image Upload Flow (7 test)

```typescript
test.describe('Files Page - Image Upload', () => {
    // A1: Upload singola immagine apre ImageEditModal
    test('uploading image file opens ImageEditModal', async ({ page }) => {
        // Navigate to /files, Static tab
        // Drag-and-drop or select a .jpg file
        // Assert: ImageEditModal visible (data-testid="image-edit-modal")
        // Assert: Crop area present (crop-container element)
        // Assert: Filename input pre-filled with file name
    });

    // A2: Crop e conferma upload
    test('crop and upload saves file correctly', async ({ page }) => {
        // Open ImageEditModal with image
        // Click "Crop" button (uploadOnComplete=false mode)
        // Assert: Modal closes
        // Assert: File appears in pending list with edit indicator
        // Click "Upload" to upload all pending files
        // Assert: File appears in files table
    });

    // A3: Cancel crop non carica file
    test('canceling crop does not add file', async ({ page }) => {
        // Open ImageEditModal via image upload
        // Click Cancel or X
        // Assert: Modal closes
        // Assert: No file in pending list
    });

    // A4: Upload file non-immagine skip crop modal
    test('non-image file uploads directly without crop modal', async ({ page }) => {
        // Upload a .pdf file
        // Assert: ImageEditModal NOT shown
        // Assert: File appears in pending list directly
    });

    // A5: Edit button apre ImageEditModal per file immagine
    test('edit button on pending image re-opens ImageEditModal', async ({ page }) => {
        // Upload image, crop, close modal
        // Assert: Edit (pencil) icon visible on image file row
        // Click pencil icon
        // Assert: ImageEditModal re-opens with previous settings
    });

    // A6: Restore button annulla modifiche
    test('restore button reverts file to original', async ({ page }) => {
        // Upload and edit an image
        // Assert: Restore (refresh) icon visible
        // Click restore
        // Assert: File reverts to original name/content
        // Assert: Edit indicator disappears
    });

    // A7: FileEditModal per file non-immagine
    test('edit button on non-image file opens FileEditModal', async ({ page }) => {
        // Upload a .txt file
        // Click pencil icon
        // Assert: FileEditModal opens (not ImageEditModal)
        // Change filename
        // Click confirm
        // Assert: File shows new name in pending list
    });
});
```

#### Suite 2: ImageEditModal Features (10 test)

```typescript
test.describe('ImageEditModal - Controls & Settings', () => {
    // B1: Zoom buttons funzionano
    test('zoom in/out buttons change selection size', async ({ page }) => {
        // Open ImageEditModal
        // Read initial selection dimensions
        // Click zoom in (+) button
        // Assert: Selection dimensions decrease (crop tighter)
        // Click zoom out (-) button
        // Assert: Selection dimensions increase (crop wider)
    });

    // B2: Rotation buttons
    test('rotation buttons rotate image', async ({ page }) => {
        // Open ImageEditModal
        // Click rotate right button
        // Assert: Image visually rotated (transform matrix changed)
        // Click rotate left button
        // Assert: Image rotated back
    });

    // B3: Flip H/V buttons
    test('flip buttons mirror image', async ({ page }) => {
        // Open ImageEditModal
        // Click flip horizontal
        // Assert: Flip H button has 'active' class
        // Click flip vertical
        // Assert: Flip V button has 'active' class
    });

    // B4: Preset selection changes aspect ratio
    test('selecting preset changes crop aspect ratio', async ({ page }) => {
        // Open ImageEditModal with custom preset
        // Click "Avatar" preset
        // Assert: Aspect ratio becomes 1:1
        // Assert: Ellipse preview auto-enabled
        // Click "Custom" preset
        // Assert: Aspect ratio buttons visible
    });

    // B5: Aspect ratio buttons (custom mode)
    test('aspect ratio buttons in custom mode work', async ({ page }) => {
        // Open with custom preset
        // Click "16:9"
        // Assert: Selection width/height ratio ≈ 16:9
        // Click "Free"
        // Assert: Selection is freely resizable
    });

    // B6: Output size editabile
    test('output width/height are editable and interdependent', async ({ page }) => {
        // Open ImageEditModal
        // Set output width to 100
        // Assert: Output height auto-calculated based on aspect ratio
        // Assert: Scale factor updated
    });

    // B7: Scale factor editabile
    test('scale factor adjusts output dimensions', async ({ page }) => {
        // Open ImageEditModal
        // Change scale to 0.50
        // Assert: Output width/height = selection * 0.5
    });

    // B8: Format e Quality
    test('format selector and quality spinner work', async ({ page }) => {
        // Open ImageEditModal
        // Change format to .jpg
        // Assert: Quality spinner appears
        // Click + quality button
        // Assert: Quality increases by 10%
    });

    // B9: Filename editabile
    test('filename can be changed', async ({ page }) => {
        // Open ImageEditModal
        // Clear filename input, type new name
        // Click Crop
        // Assert: Resulting file has new name
    });

    // B10: Reset All
    test('reset all restores original state', async ({ page }) => {
        // Open ImageEditModal
        // Zoom in, rotate, change preset
        // Click Reset All (refresh icon in header)
        // Assert: Image back to original state
        // Assert: Selection centered on image with slight margin
    });
});
```

#### Suite 3: ImageEditModal — Confirmation & Edge Cases (4 test)

```typescript
test.describe('ImageEditModal - Confirmation & Edge Cases', () => {
    // C1: Chiusura con modifiche mostra conferma
    test('closing with changes shows confirmation dialog', async ({ page }) => {
        // Open ImageEditModal
        // Make a change (rotate, zoom, etc.)
        // Click X or backdrop
        // Assert: Confirmation dialog visible (orange warning)
        // Click "Cancel" in dialog
        // Assert: Modal still open
        // Click "Discard" in dialog
        // Assert: Modal closes
    });

    // C2: Chiusura senza modifiche non mostra conferma
    test('closing without changes closes immediately', async ({ page }) => {
        // Open ImageEditModal
        // Wait for init (resetAll auto)
        // Click X or press Escape
        // Assert: Modal closes without confirmation
    });

    // C3: Ellipse preview toggle
    test('eye toggle shows/hides ellipse preview', async ({ page }) => {
        // Open ImageEditModal
        // Assert: Eye toggle visible in top-left
        // Click eye toggle
        // Assert: Ellipse overlay visible/hidden
    });

    // C4: Selection non esce dal canvas
    test('selection stays within canvas bounds', async ({ page }) => {
        // Open ImageEditModal
        // Try to drag selection to edge
        // Assert: Selection stays within canvas boundaries
    });
});
```

#### Suite 4: AssetPickerModal (8 test)

```typescript
test.describe('AssetPickerModal', () => {
    // D1: Apertura da BrokerForm
    test('clicking broker icon opens AssetPickerModal', async ({ page }) => {
        // Navigate to /brokers, click Add Broker
        // Click on the icon area
        // Assert: AssetPickerModal visible
        // Assert: Title is "Select Icon"
    });

    // D2: Tab URL con initialUrl
    test('URL tab pre-populated when broker has icon', async ({ page }) => {
        // Edit a broker that has an icon_url
        // Click icon
        // Assert: AssetPickerModal opens on URL tab
        // Assert: URL input contains existing icon URL
        // Assert: Preview image visible
    });

    // D3: Tab Existing mostra file immagini
    test('existing tab shows uploaded image files', async ({ page }) => {
        // Upload an image file first
        // Open AssetPickerModal (existing tab)
        // Assert: Uploaded image visible in grid
        // Assert: Search input functional
    });

    // D4: Selezione file da existing
    test('selecting existing file sets icon URL', async ({ page }) => {
        // Open AssetPickerModal, existing tab
        // Click on a file
        // Assert: File selected (highlighted)
        // Click "Use Selected"
        // Assert: Modal closes
        // Assert: Icon URL updated
    });

    // D5: URL manuale funziona
    test('entering URL manually sets icon', async ({ page }) => {
        // Open AssetPickerModal, URL tab
        // Type a valid URL
        // Assert: Preview visible
        // Click "Use Selected"
        // Assert: Icon URL set to entered URL
    });

    // D6: Upload → ImageEditModal → cancel → torna al picker
    test('canceling upload returns to AssetPickerModal', async ({ page }) => {
        // Open AssetPickerModal
        // Click Upload tab, select image
        // Assert: ImageEditModal opens
        // Cancel ImageEditModal
        // Assert: AssetPickerModal re-opens
    });

    // D7: Upload → ImageEditModal → confirm → chiude tutto
    test('completing upload sets URL and closes both modals', async ({ page }) => {
        // Open AssetPickerModal
        // Upload and crop image
        // Assert: Both modals close
        // Assert: Icon URL set to uploaded file URL
    });

    // D8: Cerchio overlay in URL tab (avatar/icon)
    test('circular preview overlay visible for avatar/icon context', async ({ page }) => {
        // Open AssetPickerModal with circularPreview=true (from avatar)
        // Enter a valid URL
        // Assert: Circular overlay visible on preview
    });
});
```

#### Suite 5: Avatar Management (6 test)

```typescript
test.describe('Avatar - Profile Settings', () => {
    // E1: Click avatar apre AssetPickerModal
    test('clicking avatar opens AssetPickerModal', async ({ page }) => {
        // Navigate to /settings, Profile tab
        // Unlock edit mode (click pencil)
        // Hover avatar, click camera overlay
        // Assert: AssetPickerModal opens with "Select Avatar" title
    });

    // E2: Upload avatar tramite crop
    test('uploading and cropping avatar saves it', async ({ page }) => {
        // Open AssetPickerModal from avatar
        // Upload new image → crop → confirm
        // Assert: Avatar visible in Profile section
        // Assert: Avatar visible in sidebar
    });

    // E3: Avatar da URL
    test('setting avatar from URL saves it', async ({ page }) => {
        // Open AssetPickerModal, URL tab
        // Enter a valid image URL
        // Confirm
        // Assert: Avatar updated
    });

    // E4: Rimuovi avatar
    test('removing avatar shows default icon', async ({ page }) => {
        // With avatar set, click "Remove" link
        // Assert: Confirmation dialog
        // Confirm removal
        // Assert: Default User icon shown
        // Assert: Sidebar shows default icon
    });

    // E5: Avatar persiste dopo logout/login
    test('avatar persists after re-login', async ({ page }) => {
        // Set avatar
        // Logout
        // Login
        // Assert: Avatar still visible in sidebar
    });

    // E6: Avatar con preset 1:1
    test('avatar crop uses 1:1 aspect ratio', async ({ page }) => {
        // Upload avatar via AssetPickerModal
        // Assert: ImageEditModal has "Avatar" preset selected
        // Assert: Aspect ratio locked to 1:1
        // Assert: Ellipse preview auto-enabled
    });
});
```

#### Suite 6: Dark Mode (3 test)

```typescript
test.describe('Dark Mode - Image Crop Components', () => {
    // F1: ImageEditModal dark styling
    test('ImageEditModal has correct dark mode colors', async ({ page }) => {
        // Enable dark mode
        // Open ImageEditModal
        // Assert: Modal background dark (#1f2937)
        // Assert: Text is light colored
        // Assert: Crop handles are white
    });

    // F2: AssetPickerModal dark styling
    test('AssetPickerModal dark mode', async ({ page }) => {
        // Enable dark mode
        // Open AssetPickerModal
        // Assert: Dark background
        // Assert: Tabs have correct active color (green)
    });

    // F3: FileEditModal dark styling
    test('FileEditModal dark mode', async ({ page }) => {
        // Enable dark mode
        // Open FileEditModal for a non-image file
        // Assert: Dark background, light text
    });
});
```

#### Suite 7: Grid View Files Page (4 test)

```typescript
test.describe('Files Page - Grid View', () => {
    // G1: Grid card layout 3 righe
    test('grid cards show title, metadata, actions', async ({ page }) => {
        // Navigate to /files, switch to grid view
        // Assert: Each card has 3 rows: title, metadata, actions
        // Assert: Actions include download, copy link, delete
    });

    // G2: Search funziona in grid
    test('search filters files in grid view', async ({ page }) => {
        // Upload multiple files
        // Switch to grid view
        // Type in search box
        // Assert: Only matching files shown
    });

    // G3: Copy link in grid
    test('copy link button in grid copies URL', async ({ page }) => {
        // Click copy link on a grid card
        // Assert: Clipboard contains file URL
        // Assert: Brief checkmark feedback shown
    });

    // G4: Delete in grid rosso
    test('delete button in grid is red styled', async ({ page }) => {
        // Assert: Delete icon in grid has red color
    });
});
```

### Totale: ~42 test E2E da creare

### data-testid da aggiungere

| Componente | data-testid | Scopo |
|------------|-------------|-------|
| `ImageEditModal` backdrop | `image-edit-modal` | Identificare modal aperto |
| `ImageEditModal` confirm btn | `image-edit-confirm` | Click per confermare |
| `ImageEditModal` cancel btn | `image-edit-cancel` | Click per annullare |
| `ImageEditModal` reset btn | `image-edit-reset` | Click per reset all |
| `ImageEditModal` filename input | `image-edit-filename` | Editing nome file |
| `ImageEditModal` eye toggle | `image-edit-ellipse-toggle` | Toggle preview ellipse |
| `ImageCropper` container | `image-cropper` | Verificare presenza cropper |
| `ImageCropper` zoom in btn | `cropper-zoom-in` | Zoom in |
| `ImageCropper` zoom out btn | `cropper-zoom-out` | Zoom out |
| `ImageCropper` rotate left btn | `cropper-rotate-left` | Rotate -15° |
| `ImageCropper` rotate right btn | `cropper-rotate-right` | Rotate +15° |
| `ImageCropper` flip h btn | `cropper-flip-h` | Flip horizontal |
| `ImageCropper` flip v btn | `cropper-flip-v` | Flip vertical |
| `FileEditModal` backdrop | `file-edit-modal` | Identificare modal aperto |
| `FileEditModal` confirm btn | `file-edit-confirm` | Click per confermare |
| `AssetPickerModal` backdrop | `asset-picker-modal` | Identificare modal aperto |
| `AssetPickerModal` url tab | `asset-picker-url-tab` | Tab URL |
| `AssetPickerModal` existing tab | `asset-picker-existing-tab` | Tab Existing |
| `AssetPickerModal` upload tab | `asset-picker-upload-tab` | Tab Upload |
| `AssetPickerModal` confirm btn | `asset-picker-confirm` | Use Selected |
| `AssetPickerModal` search input | `asset-picker-search` | Search nel existing |
| `BrokerForm` icon trigger | `broker-icon-trigger` | Click per aprire picker |
| `ProfileTab` avatar area | `profile-avatar` | Area cliccabile avatar |
| `ProfileTab` avatar remove | `avatar-remove-btn` | Rimuovi avatar |
| `Sidebar` user avatar | `sidebar-user-avatar` | Verificare presenza avatar |
| `FileUploader` edit btn | `file-edit-btn` | Trigger edit file |
| `FileUploader` restore btn | `file-restore-btn` | Trigger restore file |

---

## ✅ Success Criteria

- [x] Utente può caricare immagine e vedere crop area interattiva
- [x] Utente può zoom/pan per posizionare crop
- [x] Preview mostra risultato finale in tempo reale (tramite crop area)
- [x] Da Files: upload immagine apre editor, poi upload
- [x] Da Broker: click icona apre AssetPicker → URL/Existing/Upload → ImageEditModal
- [x] Da Settings: click avatar apre AssetPicker → URL/Existing/Upload → ImageEditModal
- [x] Avatar visibile in header/sidebar dopo salvataggio
- [x] Dark mode funziona (già implementato nei componenti)
- [x] Mobile-friendly (touch gestures - cropperjs v2 supporta)
- [x] Ellipse preview per avatar/icon (auto-enable)
- [x] Output size, scale, quality editabili
- [x] FileEditModal per rename file non-immagine
- [x] Grid view con 3 righe, copy link, search
- [x] Cancel upload → riapre AssetPickerModal
- [x] initialUrl pre-popola campo URL
- [x] Selezione contenuta nei bounds del canvas
- [ ] 42 test E2E da implementare (pianificati sopra)

---

## 🔗 Note Backend

La preview immagini esiste già nel backend:

- Endpoint: `GET /api/v1/uploads/files/{file_id}?img_preview=200x200`
- Supporta resize on-the-fly con dimensioni specificate
- Usabile per mostrare thumbnail delle immagini esistenti
