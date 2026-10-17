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

- **Files page, Static Resources** — `on:upload` sends each file through
  `uploadFile(file, undefined, 'personal')`: a file uploaded there is personal (see
  [Scope of uploaded files](#scope-flow)).
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
- **Scope** — the `scope` prop (default `common`) goes to `uploadFile()` on **Crop & Upload**.
  ImagePickerWrapper keeps the default, so an image uploaded through a picker is common; the Files
  page passes `personal`, though with `uploadOnComplete` false the modal uploads nothing itself
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
- `scope` (default none: the backend's rule decides) goes to `uploadFile()` when
  `uploadOnComplete` is `true`. The Files page passes `personal`. With `uploadOnComplete` false —
  the Files page after ✏️, BrokerImportFilesModal — nothing is uploaded: the renamed file goes back
  to the pending list

### 🔎 AssetPickerModal (`ui/media/AssetPickerModal.svelte`)

3-tab asset picker modal (extends ModalBase):

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="media" data-name="asset-picker-modal" alt="Asset Picker Modal" style="width: 100%; display: block;">
</div>

- **Existing**: Browse uploaded files with DataTable or FileGrid: the common files and the user's
  own personal ones, even for an administrator, whose `GET /uploads` lists every file. The list
  loads once per opening (`existingLoaded`). Confirming a personal file shares it first
  (D36-1, [below](#scope-flow))
- **URL**: Enter a URL with live preview and circular overlay
- **Upload**: dispatches `upload` with the picked image; the host (ImagePickerWrapper) opens
  ImageEditModal, which uploads it common

Used for: broker icons, user avatars, and any image URL field.

### 📸 ImagePickerWrapper (`ui/media/ImagePickerWrapper.svelte`)

*(This component is an invisible logic wrapper and has no UI of its own)*
Wraps the full AssetPicker → ImageEdit flow:

- Opens AssetPickerModal
- If upload selected → opens ImageEditModal, with its default scope `common`
- Returns final URL to parent

### 📁 FileGrid (`files/FileGrid.svelte`) {: #filegrid }

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; display: block;">
</div>

Shared grid view component used in both `/files` page and AssetPickerModal.

- `mode="browse"` with `showActions` (the Files page): each card offers Download, Preview (when the
  file has one), Copy Link, the **scope switch** and Delete. The switch (`file-grid-scope-<id>`,
  with `data-scope`) needs the `onscopechange` prop and a file whose `can_delete` is not `false`;
  it calls `onscopechange({file, scope})` with the opposite scope: the lock icon of a common file
  asks for `personal`, the users icon of a personal one for `common`. Delete
  (`file-grid-delete-<id>`, `ondelete({id})`) shows on the same `can_delete` condition. The cards
  carry no scope badge: the list view shows it
- `mode="select"` (AssetPickerModal, `showActions={false}`): single selection, no actions

### 📋 FilesTable (`files/FilesTable.svelte`) {: #filestable }

The DataTable of the Files page, both tabs, and of a broker's
[Uploaded Reports](../features/brokers/modals.md#brokerimportfilesmodal): `type="static"` or
`type="brim"`. The **Report set** badges of `type="brim"` are in
[Badges in FilesTable](../features/import-wizard.md#report-set-badges).

- **Visibility** column (`scope`, `type="static"` only): a badge, `info` for a common file
  (**Shared**) and `default` for a personal one (**Personal**), with an enum filter on the two
  values, URL key `scope`
- **Row actions** `share` and `makePersonal` (`type="static"`, only with the `onScopeChange` prop):
  `share` on a personal file calls `onScopeChange(file, 'common')`, `makePersonal` on a common one
  `onScopeChange(file, 'personal')`; both only when the file's `can_delete` is not `false`
- **Delete** row action: hidden when the row's `can_delete` is `false`, on both types
  (`UploadFileInfo.can_delete`; `can_delete` of the `GET /brokers/import/files` items). The bulk
  delete belongs to the host's `SelectionBar`: the Files page leaves those files out
  ([below](#scope-flow)), BrokerImportFilesModal sends them and the server refuses them with `403`

## 🔐 Scope of uploaded files {: #scope-flow }

Every static upload is `common` (every signed-in user sees it) or `personal` (its uploader and the
admins): developer decision 36. The backend rule, older files included, is in
[Uploaded Files: Common and Personal](../../../architecture/security.md#upload-scope); the frontend
chooses the scope of what it uploads, and lets the user change it.

**Client** — `frontend/src/lib/utils/files/upload.ts`, with the type `UploadScope` (`UploadedFile['scope']`:
`'common' | 'personal'`) in `frontend/src/lib/types/files.ts`:

- `uploadFile(file, description?, scope?)` — `POST /api/v1/uploads`, returns the file's URL. The
  multipart field `scope` is sent only when given; without it, the backend's rule decides (images
  common, the rest personal)
- `setUploadScope(fileId, scope)` — `PATCH /api/v1/uploads/{id}` with `{scope}`, returns the
  `UploadedFile` as the backend now describes it. Only the uploader and the admins may: anyone else
  gets `403` or `404`

**Who uploads with which scope:**

| Upload | `scope` sent |
|---|---|
| Files page, Static Resources (`handleUpload` in `routes/(app)/files/+page.svelte`) | `personal` |
| An image picker: ImagePickerWrapper → ImageEditModal with its default `scope` (ProfileTab and WelcomePage avatars, BrokerForm icon, AssetModal icon) | `common` |
| ImageEditModal and FileEditModal on the Files page | `personal`, though after ✏️ they upload nothing (`uploadOnComplete` false) |
| FileEditModal at its default `scope` (BrokerImportFilesModal, which uploads nothing through it) | none: the backend's rule |

**Files page** (`routes/(app)/files/+page.svelte`):

- FilesTable's `onScopeChange` and FileGrid's `onscopechange` both go to
  `requestScopeChange(file, scope)`. `common` is applied at once; `personal` first opens a warning
  `ConfirmModal` (`files-scope-confirm`), since the other users lose the file, also where it serves
  as an icon or a photo. `applyScopeChange()` calls `setUploadScope()` and puts the returned file in
  place of the row
- the `scope` URL filter (`urlFilterColumns`) also filters the grid view (`staticGridColumns`)
- the bulk delete (`handleBulkDeleteFiles`, both tabs) deletes only the selected files whose
  `can_delete` is not `false` (`deletableSelection()`); the others stay, reported by
  `file.delete.skipped` with a warning toast

**Image picker** (AssetPickerModal). What a picker returns is shown to other users, so a personal
image picked there becomes common, with a notice (D36-1):

- the **Existing** tab keeps the common files and the user's own: `scope === 'common'`, or
  `uploaded_by_user_id` equal to the id of `currentUser` (`lib/stores/app/auth`)
- confirming a personal file, necessarily the user's own, first calls
  `setUploadScope(id, 'common')`, and dispatches `select` only once that succeeds, with
  `file.scope.shared-on-pick` and an info toast. On failure: `file.scope.change.failed` with an
  error toast, no `select`, and the picker stays open. **Use Selected** is disabled meanwhile
  (`confirming`)
- a common file is handed back at once, its scope untouched

**App events** — through `notify()` (`lib/stores/app/notify.svelte.ts`), kept in
`window.__lf.events` for the E2E; the toast is a field of the same call:

| Event | Emitted by | `detail` | Toast |
|---|---|---|---|
| `file.scope.changed` | Files page | `{fileId, scope}` | success: `uploads.scope.nowShared` or `uploads.scope.nowPersonal` |
| `file.scope.change.failed` | Files page; AssetPickerModal | `{fileId, scope, reason}`; `{fileId, scope: 'common'}` | error: `uploads.scope.changeFailed` |
| `file.scope.shared-on-pick` | AssetPickerModal | `{fileId}` | info: `uploads.scope.sharedOnPick` |
| `file.delete.skipped` | Files page, bulk delete | `{count, isBrim}` | warning: `uploads.deleteSkipped` |

The page's other file events (`file.uploaded`, `file.upload.failed`, `file.deleted`,
`file.deleted.bulk`, `file.delete.failed`) carry no toast. The texts are the `uploads.scope.*` keys
of `frontend/src/lib/i18n/files/<lang>.json`.

## 📂 Files

```
frontend/src/lib/components/
├── files/
│   ├── FileGrid.svelte
│   └── FilesTable.svelte
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

- **Image preview API**: `GET /api/v1/uploads/file/{id}?img_preview=WxH`, answered with `Cache-Control: private, max-age=3600`
- **Preview cache**: Size-based (`PREVIEW_CACHE_MAX_MB` in `.env`, default 50MB), TTL 1h, invalidated on delete
- **No-op for small images**: If requested size ≥ original, serves file directly without processing
- **Scope**: every upload is `common` (every signed-in user sees it) or `personal` (its uploader and the admins).
  `POST /api/v1/uploads` takes an optional multipart field `scope`; without it, a file whose validated type (below) is
  `image/*` is stored common and any other file personal. `PATCH /api/v1/uploads/{id}` with `{"scope": "common"}` or
  `{"scope": "personal"}` changes it, for the uploader or an admin. Every `UploadFileInfo` carries `scope` and
  `can_delete`: whether the requesting user may delete the file and change its scope. The full rule, older files
  included: [Uploaded Files: Common and Personal](../../../architecture/security.md#upload-scope)
- **Seed avatars**: 30 default avatar PNGs copied to `custom-uploads/` on first startup via `seed_default_avatars()`,
  with uploader `0` (the system): they are common
- **Off the event loop**: the handlers of uploaded files (`api/v1/uploads.py`) run the service's synchronous disk work
  (`save_upload`, `list_uploads`, `get_upload_info`, `get_upload_path`, `set_upload_scope`, `delete_upload`) through
  `asyncio.to_thread`
- **Upload utility**: `uploadFile()` in `frontend/src/lib/utils/files/upload.ts` — single FormData creation point;
  `setUploadScope()` sits beside it (see [Scope of uploaded files](#scope-flow))
- **Size formatting**: Centralized i18n-aware `formatBytes()` in the same `frontend/src/lib/utils/files/upload.ts`

## ✅ Validation

Client side (`FileUploader`):

- File type checking against `accept` prop
- File size checking against global `max_file_upload_mb` setting

Server side:

- **Size** — `get_max_upload_mb()` (`max_file_upload_mb`, default 10) is enforced on both
  `POST /uploads` and `POST /brokers/import/upload`: `413` above the limit.
- **Static files** (`validate_upload_security()` in `services/files/static_uploads.py`) — the extension
  must not be in `BLOCKED_EXTENSIONS` (`.exe`, `.dll`, `.sh`, `.py`, `.js`, `.jar`, …); when
  `python-magic` (libmagic) loads, the content's detected type must not be in
  `BLOCKED_MIME_TYPES`, otherwise the type is guessed from the extension (`mimetypes`). A
  declared type that differs from the detected one is only logged. A refused file returns `400`.
- **Static delete and scope change** — `DELETE` and `PATCH /uploads/{id}` belong to the uploader or a superuser.
  Another user gets `403` on a common file (*Cannot delete files uploaded by other users*, *Cannot change files
  uploaded by other users*) and, on a personal one, the `404` of a file that does not exist. The UI offers delete and
  the scope switch only on a file whose `can_delete` is not `false` ([FilesTable](#filestable),
  [FileGrid](#filegrid)).
- **Broker reports** — EDITOR or OWNER on the target broker (`403`), an empty file is refused
  (`400`), `batch_id` must be a UUID (`422`). There is no server-side extension check: only the
  uploader's `accept` limits them to CSV and Excel.

The two families differ deliberately: someone else's personal static file answers `404`, so its existence is not
revealed, while the broker report routes answer `403` to a user without access to the file's broker.
