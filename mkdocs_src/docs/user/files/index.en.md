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

**Context Menu**: Right-click any file row (in list view) to access quick actions (Preview, Copy Link, Download, Delete).

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

**Context Menu**: Right-click any report row to access quick actions (Preview, Download, Delete).

#### 🧩 Report sets {: #report-sets }

Some banks split one account across several exports: [Danske Bank](../transactions/import/danske-bank.md), for example, needs a securities export and a cash statement. The exports of such a bank that you upload **together** form a **report set**, and LibreFolio imports them as one, through a **combined file** it builds from them. The **Report set** column tells you where each file stands (the same column appears in a broker's **Uploaded Reports**):

| Badge | Meaning |
|:--|:--|
| **Set of ‹date›** | The file belongs to the set uploaded on that date, together with the other exports of the set. |
| **Incomplete** | The set still lacks a required export: hover the badge to see which one. Add it from the set's card in the Import Wizard, with **Upload the missing file**. |
| **Combined** | The file LibreFolio built from the exports of a set — the one the import actually reads. Hover the badge to see the files it was built from, and which of them have been deleted since. |
| **Used in a combined file** | This export went into a combined file of its set. |
| **To re-combine** | The combined file was built by an older version of the importer: analysing the set again rebuilds it. |

You can preview, download and delete these files like any other report. Deleting one export of a set leaves its combined file in place, but to import the set again you first need to upload that export into it again.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-report-sets" alt="Broker Reports tab with Danske Bank files, their Report set badges and the Uploaded by filter open" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👤 Who uploaded each file {: #uploaded-by }

In both tabs, the table shows who uploaded each file in its **Uploaded by** column, with the user's avatar and name. Click the column header to sort by uploader, or open its filter to keep only the files of one or more people: tick them in the list — each with avatar and name — or search them by name. A file whose uploader was not recorded shows *Uploader not recorded*.

The filter also applies when you switch the **Static Resources** tab to grid view, and it is still there when you switch back to the list. It is written in the page address too (`?uploader=…`), so a bookmarked or shared link opens with the same filter.

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
3. Choose which **broker to associate** the file with — this determines which broker account will receive the imported transactions.
4. The file is stored and appears in the reports list. **No import runs yet**: to actually parse it and import the transactions, open the **[Import Wizard](../transactions/import/index.md)** (Transactions → **Import**) — its *Select Files* step lists the reports you already uploaded, so you can pick one instead of uploading it again.

### ⚙️ Actions on Existing Reports

Right-click any report in the table to open its context menu:
- 👁️ **Preview**: Inspect the file content without leaving the page.
- 📥 **Download**: Download the original raw file.
- 🗑️ **Delete**: Remove the file and its metadata. Transactions already imported from it **stay in the ledger** — deleting a report never deletes transactions.

!!! info "Association vs. Parsing"

    The broker you choose when uploading is for **association** only — it determines which broker account receives the imported transactions. The format detection and parsing happen in a separate step and are **independent** of the broker: the same BRIM plugin can work for multiple brokers if they export in the same format.

---

## 🔒 Security

- 🌐 **Static files** are accessible to anyone with a LibreFolio account
- 🔐 **Broker reports** respect the broker's access control — only users with access to that broker can view its reports
- 🚫 **Executable files** (`.exe`, `.sh`, `.py`, etc.) are blocked for security
- 🔍 File **MIME type** is validated server-side to prevent masquerading (e.g., renaming a `.exe` to `.jpg`)
