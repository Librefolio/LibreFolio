# Piano: Advanced Image Crop Component

**Data**: 20 Gennaio 2026  
**Ultimo Aggiornamento**: 20 Febbraio 2026  
**Status**: 🔄 IN CORSO (Debug & Refinement)

---

## 📊 Stato Attuale

### ✅ Implementato

| Componente | File | Descrizione |
|------------|------|-------------|
| ImageCropper | `frontend/src/lib/components/ui/media/ImageCropper.svelte` | Crop con zoom, rotation slider, flip H/V, aspect ratio |
| ImageEditModal | `frontend/src/lib/components/ui/media/ImageEditModal.svelte` | Modale wrapper per ImageCropper con preset (avatar, broker-icon, original, custom) |
| imageCrop utils | `frontend/src/lib/utils/imageCrop.ts` | Funzioni `getCroppedImage`, `blobToFile`, preset definitions |
| Avatar in ProfileTab | `frontend/src/lib/components/settings/tabs/ProfileTab.svelte` | Avatar editabile in modalità edit, click per upload |
| i18n keys | `frontend/src/lib/i18n/locales/*.ts` | Traduzioni per uploads.* (zoom, rotation, flip, inputSize, etc.) |

### 🔄 In Corso

- **Debug rotazione**: Rotazione funziona solo nel processing finale, non live preview (limitazione svelte-easy-crop)
- **Test manuali**: In attesa di feedback utente
- **Unified UX**: ImageEditModal usa stesso componente ovunque con preset diversi

### ⏳ Da Implementare

- [ ] Preview output dimension (mostrare compression ratio)
- [ ] Selezione da risorse statiche esistenti prima di upload
- [ ] Test automatici Playwright
- [ ] Custom output width input quando preset="custom"

---

## 🔧 Limitazioni Tecniche Note

1. **svelte-easy-crop non supporta**:
   - Prop `rotation` direttamente (la rotazione viene applicata solo al momento del crop finale)
   - Aspect ratio 0 ("free") → usa 4:3 come fallback con nota
   
2. **Rotazione**:
   - Slider da -180° a +180°
   - Pulsanti ±15° per incrementi discreti
   - Indicatore visivo quando rotation ≠ 0 ("Rotation will be applied on save")
   - La rotazione viene applicata in `getCroppedImage()` via canvas

3. **Zoom**:
   - Range: 0.5x a 10x (molto aggressivo)
   - Step: 0.1 via slider, 0.5 via pulsanti

---

## 🎯 Obiettivo

Creare un componente avanzato per crop/resize immagini, riutilizzabile in:

- Avatar upload (1:1 square)
- Icon upload (1:1 square, dimensioni diverse)
- Future cover images (16:9, custom ratios)
- Broker icons, asset logos, etc.

---

## 🔍 Problema Attuale

`ImageUploader.svelte` attuale:

- ✅ Resize semplice (mantiene aspect ratio)
- ✅ 3 preset: original, avatar (200x200), icon (50x50)
- ❌ NO crop/selection area (utente non può scegliere quale parte dell'immagine usare)
- ❌ NO aspect ratio forzato (se immagine è 16:9, avatar diventa rettangolare)
- ❌ NO preview in tempo reale del crop

**Scenario problema**:

```
Utente carica foto 1920x1080 (16:9)
→ Vuole avatar 200x200 (1:1)
→ Sistema attuale: Ridimensiona a 200x112 (mantiene 16:9) ❌
→ Desiderato: Utente seleziona area 1:1, sistema crop e ridimensiona ✅
```

---

## 📚 Librerie Valutate

### Opzione 1: cropperjs (+ svelte-cropperjs) ⭐ RACCOMANDATO

- **Pro**:
    - Feature-complete (crop, rotate, zoom, flip)
    - Ottimizzata, usata da milioni
    - Aspect ratio forzato
    - Touch-friendly (mobile)
    - Preview multipli
- **Contro**:
    - Bundle size ~50KB minified
    - Non nativa Svelte (serve wrapper)
- **Link**: https://github.com/fengyuanchen/cropperjs
- **Svelte wrapper**: https://github.com/ValentinH/svelte-easy-crop

### Opzione 2: svelte-easy-crop ⭐ ALTERNATIVA

- **Pro**:
    - Leggera (~15KB)
    - Nativa Svelte
    - API semplice
    - Good DX
- **Contro**:
    - Meno features di cropperjs
    - Community più piccola
- **Link**: https://github.com/ValentinH/svelte-easy-crop

### Opzione 3: Custom Canvas Implementation

- **Pro**: Zero dipendenze
- **Contro**: 3-5 giorni sviluppo, complesso per touch, no rotate/flip
- **Verdict**: ❌ Non giustificato

---

## 🎨 Design Proposto

### Layout Component

```
┌──────────────────────────────────────────────────────┐
│  Upload Image for Avatar                     [X]     │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌────────────────────────────────────────────┐     │
│  │                                             │     │
│  │         ╔═══════════════╗                  │     │
│  │         ║               ║  ← Crop area     │     │
│  │         ║   Selected    ║     (draggable)  │     │
│  │         ║     Area      ║                  │     │
│  │         ╚═══════════════╝                  │     │
│  │                                             │     │
│  └────────────────────────────────────────────┘     │
│                                                       │
│  Aspect Ratio: [●] 1:1  [ ] 16:9  [ ] Free          │
│                                                       │
│  Zoom: [────●────────] 1.5x                          │
│  Rotate: [────────●──] 45°                           │
│                                                       │
│  Preview:  ┌─────┐  ┌──────┐                        │
│            │ 50  │  │ 200  │                        │
│            └─────┘  └──────┘                        │
│                                                       │
│            [Cancel]  [Crop & Upload]                 │
└──────────────────────────────────────────────────────┘
```

### Features

1. **Crop Area Selection**
    - Draggable rectangle con handles
    - Aspect ratio lock (1:1, 16:9, 4:3, free)
    - Visual feedback (dimmed area outside)

2. **Zoom & Pan**
    - Slider per zoom (0.5x - 3x)
    - Drag per pan image sotto crop area

3. **Rotate & Flip** (opzionali)
    - Rotate slider (-180° to +180°)
    - Flip horizontal/vertical buttons

4. **Preview**
    - Multiple preview sizes (50x50, 200x200)
    - Update in real-time durante crop/zoom

5. **Export**
    - Output finale nel formato richiesto
    - Quality control (85% default)
    - Format selection (PNG, JPEG, WebP)

---

## 🏗️ Architettura Componenti

### 1. `ImageCropper.svelte` - Main Component

```typescript
interface ImageCropperProps {
  // Input
  file?: File;                    // Initial file
  aspectRatios?: AspectRatio[];   // Available ratios
  defaultRatio?: AspectRatio;     // Default selection
  minZoom?: number;               // Min zoom (default 0.5)
  maxZoom?: number;               // Max zoom (default 3)
  
  // Features toggles
  allowRotate?: boolean;          // Enable rotation (default true)
  allowFlip?: boolean;            // Enable flip (default true)
  showPreview?: boolean;          // Show preview boxes (default true)
  previewSizes?: number[];        // Preview dimensions (default [50, 200])
  
  // Output
  outputFormat?: 'png' | 'jpeg' | 'webp';  // Default 'png'
  outputQuality?: number;         // 0-100 (default 85)
  
  // Events
  onCrop: (file: File) => void;
  onCancel: () => void;
}

type AspectRatio = '1:1' | '16:9' | '4:3' | '3:2' | 'free';
```

### 2. `AspectRatioSelector.svelte` - Ratio Buttons

```svelte
<script>
  export let ratios: AspectRatio[];
  export let selected: AspectRatio;
</script>

<div class="ratio-selector">
  {#each ratios as ratio}
    <button class:active={selected === ratio}>
      {ratio}
    </button>
  {/each}
</div>
```

### 3. `CropPreview.svelte` - Preview Box

```svelte
<script>
  export let size: number;      // 50, 200, etc.
  export let croppedImage: string;  // Base64 or blob URL
</script>

<div class="preview-box" style="width: {size}px; height: {size}px">
  <img src={croppedImage} alt="Preview {size}px" />
  <span class="preview-label">{size}×{size}</span>
</div>
```

---

## 🔧 Implementazione con svelte-easy-crop

### Setup

```bash
npm install svelte-easy-crop
```

### Esempio Base

```svelte
<script lang="ts">
  import Cropper from 'svelte-easy-crop';
  import { createEventDispatcher } from 'svelte';
  
  const dispatch = createEventDispatcher();
  
  export let imageFile: File;
  
  let imageSrc: string;
  let crop = { x: 0, y: 0 };
  let zoom = 1;
  let aspect = 1; // 1:1
  let croppedAreaPixels = null;
  
  // Load image
  $: if (imageFile) {
    imageSrc = URL.createObjectURL(imageFile);
  }
  
  function onCropComplete(e) {
    croppedAreaPixels = e.detail.croppedAreaPixels;
  }
  
  async function handleCrop() {
    const croppedBlob = await getCroppedImg(imageSrc, croppedAreaPixels);
    const file = new File([croppedBlob], imageFile.name, { type: 'image/png' });
    dispatch('crop', { file });
  }
  
  async function getCroppedImg(imageSrc, pixelCrop) {
    const image = await createImage(imageSrc);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = pixelCrop.width;
    canvas.height = pixelCrop.height;
    
    ctx.drawImage(
      image,
      pixelCrop.x,
      pixelCrop.y,
      pixelCrop.width,
      pixelCrop.height,
      0,
      0,
      pixelCrop.width,
      pixelCrop.height
    );
    
    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), 'image/png');
    });
  }
  
  function createImage(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.addEventListener('load', () => resolve(img));
      img.addEventListener('error', error => reject(error));
      img.src = url;
    });
  }
</script>

<div class="crop-container">
  <Cropper
    image={imageSrc}
    bind:crop
    bind:zoom
    {aspect}
    on:cropcomplete={onCropComplete}
  />
</div>

<div class="controls">
  <label>
    Zoom:
    <input type="range" min={1} max={3} step={0.1} bind:value={zoom} />
  </label>
  
  <div class="aspect-ratios">
    <button on:click={() => aspect = 1}>1:1</button>
    <button on:click={() => aspect = 16/9}>16:9</button>
    <button on:click={() => aspect = 0}>Free</button>
  </div>
  
  <button on:click={handleCrop}>Crop</button>
</div>

<style>
  .crop-container {
    position: relative;
    width: 100%;
    height: 400px;
  }
</style>
```

---

## 📋 Piano Implementazione

### Fase 1: Setup Base (0.5 giorni)

1. [ ] Installare `svelte-easy-crop`
2. [ ] Creare `ImageCropper.svelte` con features base
3. [ ] Testare con immagini diverse (portrait, landscape, square)
4. [ ] Implementare aspect ratio selector

### Fase 2: Features Avanzate (1 giorno)

1. [ ] Aggiungere zoom slider
2. [ ] Aggiungere rotate slider (opzionale)
3. [ ] Implementare preview boxes real-time
4. [ ] Gestire orientamento EXIF per foto da mobile

### Fase 3: Integrazione (0.5 giorni)

1. [ ] Sostituire `ImageUploader` in Settings → Profile (avatar)
2. [ ] Integrare in BrokerForm (icon)
3. [ ] Integrare in Files page (upload con crop)
4. [ ] Aggiungere traduzioni i18n

### Fase 4: Polish (0.5 giorni)

1. [ ] Dark mode styling
2. [ ] Mobile/touch optimization
3. [ ] Loading states durante crop
4. [ ] Error handling (file troppo grande, formato non supportato)
5. [ ] Accessibility (keyboard navigation)

---

## 🧪 Test Playwright Pianificati

### Test da Aggiungere in `frontend/e2e/files/image-crop.spec.ts`

```typescript
// Test Suite: Image Crop Modal

describe('ImageEditModal', () => {
  // A. Files Page Upload
  test('opens modal when uploading image file', async () => {
    // Upload image in /files, verify modal opens
  });
  
  test('preset selector changes output dimensions', async () => {
    // Select avatar preset → output shows 200×200
    // Select icon preset → output shows 64×64
  });
  
  test('zoom slider works', async () => {
    // Move slider, verify zoom value updates
  });
  
  test('rotation slider shows indicator', async () => {
    // Move rotation slider, verify "Rotation applied on save" banner
  });
  
  test('flip buttons toggle state', async () => {
    // Click flip H, verify button active state
    // Click flip V, verify button active state
  });
  
  test('reset button clears all transforms', async () => {
    // Apply zoom/rotation/flip
    // Click reset, verify all back to default
  });
  
  test('cancel closes modal without upload', async () => {
    // Open modal, click cancel, verify no file uploaded
  });
  
  test('crop and upload saves file', async () => {
    // Crop image, click upload, verify file in list
  });
  
  test('non-image files skip crop modal', async () => {
    // Upload PDF, verify direct upload without modal
  });
});

describe('Avatar Upload', () => {
  test('avatar visible in profile tab', async () => {
    // Go to /settings, verify avatar section
  });
  
  test('avatar upload in edit mode', async () => {
    // Enable edit, click avatar, verify modal opens
  });
  
  test('avatar hidden upload when locked', async () => {
    // When not in edit mode, no upload overlay
  });
  
  test('remove avatar works', async () => {
    // Set avatar, then remove, verify placeholder
  });
});

describe('Broker Icon Upload', () => {
  test('icon upload opens modal with broker-icon preset', async () => {
    // Create broker, upload icon, verify 64×64 preset
  });
  
  test('icon preview shows in form', async () => {
    // After upload, icon preview visible
  });
});

describe('Dark Mode', () => {
  test('modal renders correctly in dark mode', async () => {
    // Enable dark mode, open modal, screenshot compare
  });
});

describe('Mobile/Touch', () => {
  test('modal responsive on mobile viewport', async () => {
    // Set mobile viewport, open modal, verify usable
  });
});
```

### File Test da Creare

| File | Descrizione |
|------|-------------|
| `frontend/e2e/files/image-crop.spec.ts` | Test completi ImageEditModal |
| `frontend/e2e/settings/avatar.spec.ts` | Test avatar in ProfileTab |
| `frontend/e2e/brokers/broker-icon.spec.ts` | Test icona broker |

---

### Colors (LibreFolio Design)

```css
--crop-overlay: rgba(0, 0, 0, 0.5);
--crop-border: #1a4031;
--crop-handle: #1a4031;
--crop-grid: rgba(255, 255, 255, 0.3);
```

### Dark Mode

```css
html.dark {
  --crop-overlay: rgba(0, 0, 0, 0.7);
  --crop-border: #4ade80;
  --crop-handle: #4ade80;
}
```

---

## 📂 File da Creare

| File                                               | Descrizione                             |
|----------------------------------------------------|-----------------------------------------|
| `src/lib/components/ui/ImageCropper.svelte`        | Main component con crop logic           |
| `src/lib/components/ui/AspectRatioSelector.svelte` | Ratio buttons                           |
| `src/lib/components/ui/CropPreview.svelte`         | Preview boxes                           |
| `src/lib/utils/imageCrop.ts`                       | Utility functions (getCroppedImg, etc.) |

---

## 🧪 Test Cases

1. **Aspect Ratios**:
    - ✅ 1:1 produce immagine perfettamente quadrata
    - ✅ 16:9 produce corretto ratio
    - ✅ Free permette qualsiasi shape

2. **Zoom & Pan**:
    - ✅ Zoom mantiene crop area centrata
    - ✅ Pan funziona anche con zoom >1
    - ✅ Non si può pan fuori dai bounds

3. **Quality**:
    - ✅ Output a 200px è nitido
    - ✅ Output a 50px è riconoscibile
    - ✅ File size ragionevole (<50KB per avatar)

4. **Edge Cases**:
    - ✅ Immagine molto piccola (es. 100x100)
    - ✅ Immagine enorme (es. 5000x5000)
    - ✅ Immagine con orientamento EXIF rotato

---

## ⚠️ Note Importanti

1. **EXIF Orientation**: Foto da mobile spesso hanno metadata EXIF con rotation. Usare libreria come `exif-js` o gestire server-side.

2. **Performance**: Per immagini >5MB, considerare resize preliminare prima di mostrare in cropper (max 2000px lato più lungo).

3. **Memory**: Rilasciare sempre blob URLs con `URL.revokeObjectURL()` dopo uso.

4. **Browser Support**: Canvas API e FileReader sono supportati da tutti i browser moderni. IE11 richiede polyfill.

---

## 📊 Stima Tempo

- **Ottimistico**: 2 giorni
- **Realistico**: 3 giorni
- **Con imprevisti**: 4 giorni

---

## 🎯 Success Criteria

✅ Utente può caricare immagine e vedere crop area  
✅ Utente può selezionare aspect ratio (1:1, 16:9, free)  
✅ Utente può zoom/pan per posizionare crop  
✅ Preview mostra risultato finale in tempo reale  
✅ Output file è corretto (dimensioni, ratio, quality)  
✅ Component è riutilizzabile (avatar, icon, cover, etc.)  
✅ Dark mode funziona  
✅ Mobile-friendly (touch gestures)

---

**Attendo approvazione per procedere con implementazione.**
