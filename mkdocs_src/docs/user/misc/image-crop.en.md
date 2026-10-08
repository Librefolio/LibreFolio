# ✂️ Image Crop Tool

Frame, rotate and resize a picture before LibreFolio stores it.

---

## 🎯 When Does It Appear?

- 👤 **Profile picture** — in **[Profile](../settings/profile.md)** or on the Welcome page: in the
  image picker, choose **Upload** and pick an image.
- 🏦 **Broker icon** and 📈 **asset icon** — the same picker, from the broker or the asset form.
- 📂 **Files page** — add images to the upload list, then click the ✏️ **Edit** button of an image.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Image Edit Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ✂️ Frame the Picture

- 📏 **Drag** a corner or a side of the crop area to resize it, its inside to move it, the outside
  to move the picture. The crop area always stays inside the picture.
- 🔍 **Zoom** with the mouse wheel or **+ / −** — the crop area tightens (or widens) first, then the
  picture zooms — or pinch on a touch screen.
- 🔄 **Rotate** 15° at a time with **↺ / ↻**, and 🪞 **flip** with ↔ / ↕.
- 👁️ The eye button on the left toggles a **round preview**: how the picture looks in a circle, like
  your avatar in the sidebar.
- 🔁 **Reset All** (top right) undoes the crop, zoom, rotation and flip.

---

## 📐 Presets

| Preset | Output size | Shape |
|--------|------|-------------|
| **Avatar** | 200 × 200 px | Square, round preview on |
| **Icon** | 64 × 64 px | Square, round preview on |
| **Custom** | Same as the crop area | Free, or a ratio of your choice: 1:1, 16:9, 4:3, 3:4 |

Profile pictures open with **Avatar**, broker icons with **Icon** and Files-page images with
**Custom**; asset icons are cut square at 256 × 256 px. You can switch preset at any time.

---

## ⚙️ Output Settings

- 🎨 **Format** — `.png` (lossless, keeps transparency), `.jpg` (smaller, no transparency) or
  `.webp` (best compression), next to the file name, which you can also change. A `.jpg` or `.webp`
  picture keeps its format; anything else starts as `.png`.
- 📊 **Quality** (`.jpg` and `.webp` only) — **−** / **+** in steps of 10%, from 10% to 100%: lower
  quality means a smaller file.
- 📐 **Output** — width × height in pixels, set by the preset but editable. The two stay in
  proportion with the crop area, and you can't set them larger than it; **Scale** sets both at
  once.

---

## ✅ Confirm or Cancel

- **Crop & Upload** saves the picture and uses it. On the Files page, **Crop** puts it in the upload
  list instead (**Restore original** ↺ brings the original back), and **Upload** sends the list.
- **Cancel** or **✕** closes the tool — after asking, if you have unsaved changes
  (**Discard & Close**). From the image picker, you go back to the picker.

??? info "📄 Non-image files — on the Files page"

    A PDF, a CSV or any other non-image file has no crop step: its ✏️ button opens a simple
    **Rename** dialog instead.

---

## 🔗 Related

- 🛠️ **[File Upload & Media Components](../../developer/frontend/components/core-ui/file-upload.md)** — How the tool is built (for developers)
