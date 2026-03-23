# ✂️ Image Crop Tool

LibreFolio includes a powerful interactive image editing tool that lets you crop, rotate, and resize images before uploading them.

---

## 🎯 When Does It Appear?

The Image Crop modal opens automatically whenever you upload an image file in LibreFolio:

- 📂 **Files page** → uploading any image (JPEG, PNG, WebP, GIF)
- 👤 **Profile settings** → changing your avatar
- 🏦 **Broker settings** → changing a broker icon

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Image Edit Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📐 Presets

The tool offers presets for common use cases:

| Preset | Size | Aspect Ratio | Use Case |
|--------|------|-------------|----------|
| **Avatar** | 200 × 200 px | 1:1 (square) | User profile pictures |
| **Broker Icon** | 64 × 64 px | 1:1 (square) | Broker logos |
| **Custom** | Free | Free | Any size and ratio |

The preset automatically sets the aspect ratio constraint and output size.

---

## 🎛️ Controls

### ✂️ Crop Area

- 📏 **Drag the corners** to resize the crop area
- ↔️ **Drag inside** the area to move it
- 🔒 The crop area is **clamped to the image bounds** — you can't select outside the image

### 🔍 Zoom

- 🖱️ **Mouse wheel** or **pinch** (on touch devices) to zoom in/out
- ➕ **Zoom buttons** (+/−) for precise control
- 🎯 Zooming centers on the crop selection

### 🔄 Rotation

- 🔄 **Rotate buttons** (↺/↻) rotate in 15° steps
- 📍 Rotation happens relative to the selection center

### 🪞 Flip

- ↔️ **Flip Horizontal** (↔) — mirrors the image left-right
- ↕️ **Flip Vertical** (↕) — mirrors the image top-bottom

---

## ⚙️ Output Settings

Before confirming, you can adjust:

- 🎨 **Output format**: PNG (lossless, transparency), JPEG (smaller, no transparency), WebP (modern, best compression)
- 📊 **Quality** (JPEG/WebP only): Slider from 10% to 100% — lower quality = smaller file
- 📐 **Output size**: Width and height in pixels (linked to the preset, but editable)

!!! tip "Ellipse Preview"

    For avatar and icon presets, a circular **ellipse overlay** is shown on the crop area. This helps you preview how the image will look in a circular frame (e.g., user avatars in the navigation bar).

---

## 🔄 Workflow

1. **Upload or drag** an image file
2. The crop modal opens with the appropriate preset
3. **Adjust** the crop area, zoom, rotation as needed
4. **Preview** the result in real-time
5. Click **Upload** to confirm — the cropped image is saved to the server
6. Click **Cancel** or close the modal to discard changes

!!! info "Non-image files"

    If you upload a non-image file (PDF, CSV, etc.), the crop modal is skipped. Instead, a simple rename dialog appears.
