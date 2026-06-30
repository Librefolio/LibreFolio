# 📁 Files & Uploads

The **Files** page (`/files`) is your central hub for managing all uploaded content in LibreFolio. It has two distinct sections with different visibility rules.

---

## 📂 Two Tabs, Two Purposes

### 📁 Static Resources

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Static resources are **visible to all users** in the system. This is where you'll find:

- 🖼️ User **avatars** and profile pictures
- 🏷️ Broker **icons** and logos
- 📄 Any **shared documents** or images uploaded by users

These files live in the `custom-uploads/` directory on the server.

**Context Menu**: Right-click any file row (in list view) to access quick actions (Preview, Rename, Delete).

You can switch between **list view** and **grid view** for a visual preview of image files:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Broker Reports

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Broker Reports Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Broker reports have **restricted visibility** — you can only see reports for brokers you have access to (as Owner, Editor, or Viewer). These files include:

- 📋 CSV or Excel **transaction exports** from your broker
- ✅ **Parsed results** from the automatic import system (BRIM)
- ❌ Files that **failed parsing** (kept for debugging)

**Context Menu**: Right-click any report row to access quick actions (Preview, Rename, Delete).

---

## ⬆️ Uploading Files

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

## 📤 Managing Broker Reports

If you want to import transactions or manage existing statements:

1. Go to the **Broker Reports** tab.
2. Upload the CSV or Excel file exported from your broker (Degiro, Interactive Brokers, eToro, Directa SIM, etc.).
3. Choose which **broker to associate** the file with — this determines which broker account receives the imported transactions.
4. The system automatically detects the format and runs the guided **[Import Wizard](../transactions/import/index.md)**.

### ⚙️ Actions on Existing Reports

Right-click any report in the table to open its context menu:
- 🔄 **Reprocess**: Reruns the import parser on the statement. This is useful after an import plugin update or if you accidentally deleted some transactions and want to restore them.
- 📥 **Download**: Download the original raw file.
- 🗑️ **Delete**: Remove the statement and its associated transactions from the ledger.

!!! info "Association vs. Parsing"

    The broker you choose when uploading is for **association** only — it determines which broker account receives the imported transactions. The format detection and parsing happen in a separate step and are **independent** of the broker: the same BRIM plugin can work for multiple brokers if they export in the same format.

---

## 🔒 Security

- 🌐 **Static files** are accessible to anyone with a LibreFolio account
- 🔐 **Broker reports** respect the broker's access control — only users with access to that broker can view its reports
- 🚫 **Executable files** (`.exe`, `.sh`, `.py`, etc.) are blocked for security
- 🔍 File **MIME type** is validated server-side to prevent masquerading (e.g., renaming a `.exe` to `.jpg`)
