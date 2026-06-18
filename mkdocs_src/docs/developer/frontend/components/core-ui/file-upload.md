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
- **Image files** → automatic ImageEditModal opening
- **Non-image files** → FileEditModal for rename
- Edit (✏️) and Restore (↩️) buttons per file
- Preview for images via backend thumbnail API

### ✂️ ImageCropper (`ui/media/ImageCropper.svelte`)

cropperjs v2 based image cropper (Web Components):

- Free crop with L-shaped corner handles
- Zoom via buttons, mouse wheel, or pinch
- Rotation (15° steps) relative to selection center
- Flip horizontal/vertical
- Aspect ratio presets (free, 1:1, 4:3, 16:9)
- Selection clamped to canvas bounds
- Middle-mouse-button drag for background translation

### 🖼️ ImageEditModal (`ui/media/ImageEditModal.svelte`)

Full image editing modal (extends ModalBase):

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Image Edit Modal" style="width: 100%; display: block;">
</div>

- Presets: Avatar (200×200), Icon (64×64), Custom (free)
- Output size with editable width/height + auto scale
- Format selection (PNG, JPEG, WebP)
- Quality control for lossy formats (10-100%)
- Ellipse preview overlay (for avatar/icon circular display)
- Confirmation dialog on close with unsaved changes
- Reset all button to restore original state

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

## Backend Support

- **Image preview API**: `GET /api/v1/uploads/file/{id}?img_preview=WxH`
- **Preview cache**: Size-based (`PREVIEW_CACHE_MAX_MB` in `.env`, default 50MB), TTL 1h, invalidated on delete
- **No-op for small images**: If requested size ≥ original, serves file directly without processing
- **Seed avatars**: 30 default avatar PNGs copied to `custom-uploads/` on first startup via `seed_default_avatars()`
- **Upload utility**: Centralized `uploadFile()` in `utils/upload.ts` — single FormData creation point
- **Size formatting**: Centralized i18n-aware `formatBytes()` in `utils/upload.ts`

## Validation

- File type checking against `accept` prop
- File size checking against global `max_file_upload_mb` setting
- Client-side only (server validates again)
