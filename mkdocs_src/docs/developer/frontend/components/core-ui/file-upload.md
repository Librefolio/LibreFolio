# 📤 File Upload & Media Components

*Status: Implemented and documented (Feb 2026)*

## 📖 Overview

Comprehensive file upload system with image editing, asset picking, and multi-file support.

<div class="lf-screenshot-carousel" data-carousel="file-upload-main" data-carousel-interval="3000" data-show-titles="true">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="files" data-name="static-tab" data-title="Static Files Tab">
    <img class="gallery-img lf-screenshot-carousel-item" data-category="files" data-name="static-grid" data-title="Static Files Grid View">
</div>

## 🧱 Components

### ⬆️ FileUploader (`ui/media/FileUploader.svelte`)

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="File Uploader" style="width: 100%; display: block;">
</div>

Multi-file uploader with:

- Drag & drop support
- Click to browse
- File type & size validation
- **Edit (✏️) per pending file** — on an image the button is titled **Edit**: it dispatches
  `editImage` and the host opens ImageEditModal. On any other file it is titled **Rename**: it
  dispatches `editFile` and the host opens FileEditModal. The edited file replaces the pending one
  (`replaceFile()`). Nothing opens on its own: on **Upload** the host receives the pending files
  as they are (the Files page's `pendingImageFiles` queue in `routes/(app)/files/+page.svelte` is
  never filled)
- **Restore original** (↩️) on every edited file, cropped or renamed (`editedIndices`), **Remove**
  on every file
- Preview for images via backend thumbnail API

Hosts:

- **Files page, Static Resources** — `on:upload` sends each file through `uploadFile()`.
- **Files page, Broker Reports** (`accept=".csv,.xlsx,.xls"`) — the selection opens the
  **Assign Brokers** dialog: one broker per file or **Assign all to**, pre-filled when the user can
  edit exactly one broker (Viewer brokers are left out), and **Upload (n)** enabled only once every
  file has a broker. All the files of one confirmation share a `batch_id` (`generateUUID()`), so
  they form one report set.
- **[BrokerImportFilesModal](../features/brokers/modals.md#brokerimportfilesmodal)** — the
  report files of one broker.

### ✂️ ImageCropper (`ui/media/ImageCropper.svelte`)

cropperjs v2 based image cropper (Web Components):

- Free crop with L-shaped corner handles
- **Zoom** (overlay buttons and mouse wheel) works on the selection first: zoom-in shrinks it by
  10% until it covers 50% of the image (`MIN_SELECTION_COVERAGE`), then zooms the image by 0.1;
  zoom-out enlarges it by 10% up to 90% (`MAX_SELECTION_COVERAGE`), then zooms the image out
- Rotation (15° steps, **−15°** / **+15°**) relative to selection center
- Flip horizontal/vertical
- Aspect ratio given by the host (`aspectRatio`; `0` or `NaN` = free); the ratio buttons live in
  ImageEditModal
- Selection clamped to canvas bounds
- Middle-mouse-button drag for background translation

### 🖼️ ImageEditModal (`ui/media/ImageEditModal.svelte`)

Full image editing modal (extends ModalBase):

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Image Edit Modal" style="width: 100%; display: block;">
</div>

It opens only when a host asks: the ✏️ **Edit** button of FileUploader (Files page), or the
upload path of ImagePickerWrapper (below) — never by itself when a file is picked.

- **Confirm button** — **Crop & Upload** when `uploadOnComplete` is `true` (the default, used by
  ImagePickerWrapper); **Crop** when it is `false`, as on the Files page after ✏️, where the cropped
  file goes back to the pending list
- **Presets** (`IMAGE_PRESETS` in `lib/utils/files/imageCrop.ts`): buttons **Avatar** (200×200),
  **Icon** (`broker-icon`, 64×64) and **Custom** (free size), shown while `allowPresetChange`
  (default `true`). The `asset-icon` preset (256×256) has no button: only a host can set it
- **Round preview** — a toggle for the ellipse overlay, on by default for Avatar and Icon
- **Ratio** buttons **1:1**, **16:9**, **4:3**, **3:4** and **Free**, shown only with Custom
- **Output** — width and height are capped at the selection and keep its ratio; **Scale** goes from
  0.01 to 1
- **Format** — `.png`, `.jpg` or `.webp`, defaulting to the source file's type. **Quality** (JPEG
  and WebP only) moves with −/+ in 10-point steps from 10 to 100, default 90
- **Reset All** (header) puts zoom, rotation and flip back and re-centres the selection
  (`resetAll()`)
- **Closing with changes** asks *Discard changes?* — **Discard & Close**

### 📄 FileEditModal (`ui/media/FileEditModal.svelte`)

Simple file rename modal (extends ModalBase):

- Rename file before upload
- Used for PDFs, CSVs, and other non-image files
- Also available for BRIM import files

### 🔎 AssetPickerModal (`ui/media/AssetPickerModal.svelte`)

3-tab asset picker modal (extends ModalBase):

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="media" data-name="asset-picker-modal" alt="Asset Picker Modal" style="width: 100%; display: block;">
</div>

- **Existing**: Browse uploaded files with DataTable or FileGrid
- **URL**: Enter a URL with live preview and circular overlay
- **Upload**: Upload + crop a new image

Used for: broker icons, user avatars, and any image URL field.

### 📸 ImagePickerWrapper (`ui/media/ImagePickerWrapper.svelte`)

*(This component is an invisible logic wrapper and has no UI of its own)*
Wraps the full AssetPicker → ImageEdit flow:

- Opens AssetPickerModal
- If upload selected → opens ImageEditModal
- Returns final URL to parent

### 📁 FileGrid (`files/FileGrid.svelte`)

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; display: block;">
</div>

Shared grid view component used in both `/files` page and AssetPickerModal.

## 📂 Files

```
frontend/src/lib/components/
├── files/
│   └── FileGrid.svelte
└── ui/media/
    ├── AssetPickerModal.svelte
    ├── FileEditModal.svelte
    ├── FileUploader.svelte
    ├── ImageCropper.svelte
    ├── ImageEditModal.svelte
    ├── ImagePickerWrapper.svelte
    ├── ImageUploader.svelte
    ├── LazyImage.svelte
    └── index.ts
```

## 🖥️ Backend Support

- **Image preview API**: `GET /api/v1/uploads/file/{id}?img_preview=WxH`
- **Preview cache**: Size-based (`PREVIEW_CACHE_MAX_MB` in `.env`, default 50MB), TTL 1h, invalidated on delete
- **No-op for small images**: If requested size ≥ original, serves file directly without processing
- **Seed avatars**: 30 default avatar PNGs copied to `custom-uploads/` on first startup via `seed_default_avatars()`
- **Upload utility**: Centralized `uploadFile()` in `utils/upload.ts` — single FormData creation point
- **Size formatting**: Centralized i18n-aware `formatBytes()` in `utils/upload.ts`

## ✅ Validation

Client side (`FileUploader`):

- File type checking against `accept` prop
- File size checking against global `max_file_upload_mb` setting

Server side:

- **Size** — `get_max_upload_mb()` (`max_file_upload_mb`, default 10) is enforced on both
  `POST /uploads` and `POST /brokers/import/upload`: `413` above the limit.
- **Static files** (`validate_upload_security()` in `services/static_uploads.py`) — the extension
  must not be in `BLOCKED_EXTENSIONS` (`.exe`, `.dll`, `.sh`, `.py`, `.js`, `.jar`, …); when
  `python-magic` (libmagic) loads, the content's detected type must not be in
  `BLOCKED_MIME_TYPES`, otherwise the type is guessed from the extension (`mimetypes`). A
  declared type that differs from the detected one is only logged. A refused file returns `400`.
- **Static delete** — only the uploader or a superuser (`403` *Cannot delete files uploaded by
  other users*); the UI shows the action to everyone.
- **Broker reports** — EDITOR or OWNER on the target broker (`403`), an empty file is refused
  (`400`), `batch_id` must be a UUID (`422`). There is no server-side extension check: only the
  uploader's `accept` limits them to CSV and Excel.
