# 📁 Files & Uploads

The **Files** page (`/files`) is your central hub for managing all uploaded content in LibreFolio. It has two distinct sections with different visibility rules.

---

## Two Tabs, Two Purposes

### 📁 Static Resources

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Static resources are **visible to all users** in the system. This is where you'll find:

- User **avatars** and profile pictures
- Broker **icons** and logos
- Any **shared documents** or images uploaded by users

These files live in the `custom-uploads/` directory on the server.

You can switch between **list view** and **grid view** for a visual preview of image files:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Broker Reports

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Broker Reports Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Broker reports have **restricted visibility** — you can only see reports for brokers you have access to (as Owner, Editor, or Viewer). These files include:

- CSV or Excel **transaction exports** from your broker
- **Parsed results** from the automatic import system (BRIM)
- Files that **failed parsing** (kept for debugging)

---

## Uploading Files

To upload a file:

1. Click the **upload area** or **drag & drop** files directly
2. For **image files**, the [Image Crop tool](../misc/image-crop.md) opens automatically, letting you resize and crop before uploading
3. For **non-image files** (CSV, PDF, etc.), you can rename the file before confirming

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="File Upload Drop Zone" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "File Size Limit"
    The maximum upload size is configured by the system administrator in [Global Settings](../../admin/settings.md). The default is typically 10 MB.

---

## Uploading Broker Reports

If you want to import transactions from your broker:

1. Go to the **Broker Reports** tab
2. Upload the CSV or Excel file exported from your broker (Degiro, Interactive Brokers, eToro, Directa, etc.)
3. The system will attempt to **automatically detect** the broker format and parse the transactions

!!! note "Work in Progress"
    The full broker report import UI (BRIM) is under active development. Currently, you can upload reports and trigger parsing, but the guided import wizard is not yet available.

---

## Security

- **Static files** are accessible to anyone with a LibreFolio account
- **Broker reports** respect the broker's access control — only users with access to that broker can view its reports
- **Executable files** (`.exe`, `.sh`, `.py`, etc.) are blocked for security
- File **MIME type** is validated server-side to prevent masquerading (e.g., renaming a `.exe` to `.jpg`)

