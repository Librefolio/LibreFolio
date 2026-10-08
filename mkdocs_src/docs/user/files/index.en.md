# 📁 Files & Uploads

The **Files** page keeps everything uploaded to LibreFolio, in two tabs:

- **Static Resources** — avatars, broker icons and other images or documents, visible to every user;
- **Broker Reports** — the statement files you import transactions from, visible only to the people with access to their broker.

---

## 🖼️ Static resources

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Here you find the users' **avatars**, the brokers' **icons** and any **image or document** shared by users. Everyone with a LibreFolio account can see them.

- Switch between **list** and **grid** view: the grid previews images.
- In the list, right-click a file for **Preview**, **Copy Link**, **Download** or **Delete**. You can delete only the files you uploaded; an administrator can delete any.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⬆️ Upload a file

1. Click **Upload**, then drop files on the area or click it to browse.
2. Before uploading, you can click ✏️ **Edit** on an image to crop it with the [Image Crop tool](../misc/image-crop.md), then confirm with **Crop**; on any other file, ✏️ **Rename** changes its name. **Restore original** puts a file back as you picked it.
3. Click **Upload**.

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="File Upload Drop Zone" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Broker Reports {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Broker Reports Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

These are the statements exported by your brokers, waiting to be imported or already imported. You see the reports of every broker you can access, as Owner, Editor or Viewer.

The **Status** column tells you where each file stands:

- **Uploaded** — stored, not analysed yet;
- **Parsed** — the Import Wizard read it successfully;
- **Failed** — the analysis failed; the file stays here so you can check it or report it.

### 📤 Upload a broker report

1. On **Broker Reports**, click **Upload** and pick CSV or Excel files.
2. In **Assign Brokers**, choose the broker of each file, or one for all with **Assign all to**. **Create new** adds a broker on the spot; if you can edit only one broker, it is already chosen.
3. Click **Upload**. The files are stored, but **nothing is imported yet**.

To import them, open the [Import Wizard](../transactions/import/index.md) (**Transactions** → **Import**): its **Select Files** step lists the reports you have uploaded.

The broker you choose only decides which account receives the transactions. The importer recognises the file format by itself, and one import plugin can read the exports of several brokers.

### ⚙️ Manage reports

Right-click a report for **Preview**, **Download** or **Delete**, or tick several to delete them together. Deleting a report never deletes the transactions already imported from it.

### 🧩 Report sets {: #report-sets }

Some banks split one account across several exports: [Danske Bank](../transactions/import/danske-bank.md), for example, needs a securities export and a cash statement. The exports of such a bank that you upload **together** form a **report set**, and LibreFolio imports them as one, through a **combined file** it builds from them. The **Report set** column tells you where each file stands (the same column appears in a broker's **Uploaded Reports**):

| Badge | Meaning |
|:--|:--|
| **Set of ‹date›** | The file belongs to the set uploaded on that date, together with the other exports of the set. |
| **Incomplete** | The set still lacks a required export: hover the badge to see which one. Add it from the set's card in the Import Wizard, with **Upload the missing file**. |
| **Combined** | The file LibreFolio built from the exports of a set — the one the import actually reads. Hover the badge to see the files it was built from, and which of them have been deleted since. |
| **Used in a combined file** | This export went into a combined file of its set. |
| **To re-combine** | The importer has changed since the combined file was built: analysing the set again rebuilds it. |

You can preview, download and delete these files like any other report. Deleting one export of a set leaves its combined file in place, but to import the set again you first need to upload that export into it again.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-report-sets" alt="Broker Reports tab with Danske Bank files, their Report set badges and the Uploaded by filter open" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👤 Who uploaded each file {: #uploaded-by }

Both tabs show who uploaded each file in the **Uploaded by** column, with the person's avatar and name:

- click the column header to sort by uploader;
- open its filter to keep only the files of one or more people: tick them in the list, or search them by name;
- a file whose uploader was not recorded shows *Uploader not recorded*.

The filter also applies to the grid view of **Static Resources**. It is saved in the page address, so a bookmark or a shared link opens with the same filter.

---

## 🔒 Access and limits

- 🌐 **Static resources** — every signed-in user can see them.
- 🔐 **Broker reports** — only the users with access to the broker can see them; uploading and deleting need Owner or Editor access.
- 📏 **Size** — up to the limit the administrator sets in [Global Settings](../../admin/settings.md): 10 MB unless changed.
- 🚫 **File types** — programs and scripts (such as `.exe`, `.sh` or `.py` files) are refused as static resources; broker reports must be CSV or Excel files.

Where the files live on the server is described in [Filesystem Structure](../../admin/filesystem.md).
