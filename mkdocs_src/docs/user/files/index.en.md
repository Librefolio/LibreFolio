# 📁 Files & Uploads

The **Files** page keeps everything uploaded to LibreFolio, in two tabs:

- **Static Resources** — avatars, broker icons and other images or documents, each one **shared** with every user or **personal** to whoever uploaded it;
- **Broker Reports** — the statement files you import transactions from, visible only to the people with access to their broker.

---

## 🖼️ Static resources

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Here you find the users' **avatars**, the brokers' **icons** and the **images and documents** uploaded by users: the shared ones, which everyone with a LibreFolio account can see, and your personal ones, which only you and the administrators can see (see [Shared or personal](#visibility)).

- Switch between **list** and **grid** view: the grid previews images.
- In the list, right-click a file for **Preview**, **Copy Link**, **Download** or **Delete**. You can delete only the files you uploaded, so **Delete** appears only on them; an administrator can delete any. Tick several files to delete them together: the files of other users stay in place, and a notice tells you so.
- **Preview** shows a PDF in a read-only viewer: you can read it, search it and copy its text, but not edit, annotate or print it; to keep the file, use **Download**. A password-protected PDF asks for its password, which stays in your browser: it is never sent to the server or saved, and it is gone once the preview closes.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⬆️ Upload a file

1. Click **Upload**, then drop files on the area or click it to browse.
2. Before uploading, you can click ✏️ **Edit** on an image to crop it with the [Image Crop tool](../misc/image-crop.md), then confirm with **Crop**; on any other file, ✏️ **Rename** changes its name. **Restore original** puts a file back as you picked it.
3. Click **Upload**. The files are **personal**: only you and the administrators see them, until you [share them](#visibility).

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="File Upload Drop Zone" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👥 Shared or personal {: #visibility }

Every static resource is **Shared** or **Personal**, as its badge in the **Visibility** column of the list shows:

- **Shared** — every signed-in user can see it;
- **Personal** — only the person who uploaded it and the administrators can see it. The other users do not find it in their list, and cannot open, preview or download it.

A file you upload is:

- **personal** when you upload it from this page;
- **shared** when you upload it from an image picker (your profile picture, in **Profile** or on the Welcome page; a broker icon; an asset icon), because the other users see the picture where you use it.

Files uploaded with an older version of LibreFolio are shared if they are images, personal otherwise.

You can change the visibility of the files you uploaded; an administrator, of any file:

- in the list, right-click the file: a personal file offers **Share with everyone**, a shared one **Make personal**;
- in the grid, use the same switch on the file's card: 👥 shares it, 🔒 makes it personal.

Sharing is immediate. **Make personal** asks you to confirm first: the other users lose the file, also where it shows as an icon or a photo.

The **Visibility** filter, in the column header, keeps only the shared or only the personal files. Like the [Uploaded by](#uploaded-by) filter, it also applies to the grid view and is saved in the page address.

An image picker's **Existing** tab lists the shared images and your own personal ones, even for an administrator. Picking one of your personal images there makes it shared, and a notice tells you so: the other users can then see it where you used it.

---

## 📊 Broker Reports {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Broker Reports Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

These are the statements exported by your brokers, waiting to be imported or already imported. You see the reports of every broker you can access, as Owner, Editor or Viewer. The reports an older version of LibreFolio stored without a broker appear only here: to the administrators, and to the person who uploaded them when LibreFolio recorded who did.

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

Right-click a report for **Preview**, **Download** or **Delete**, or tick several to delete them together. **Delete** appears only on the reports you may delete, and deleting several leaves the others in place, with a notice. Deleting a report never deletes the transactions already imported from it.

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

- 🌐 **Static resources** — every signed-in user can see the shared ones; a personal file, only the person who uploaded it and the administrators (see [Shared or personal](#visibility)). Deleting a file and changing its visibility belong to whoever uploaded it, and to an administrator.
- 🔐 **Broker reports** — only the users with access to the broker can see them; uploading and deleting need Owner or Editor access. An administrator can see and delete every report.
- 📏 **Size** — up to the limit the administrator sets in [Global Settings](../../admin/settings.md): 10 MB unless changed.
- 🚫 **File types** — programs and scripts (such as `.exe`, `.sh` or `.py` files) are refused as static resources; broker reports must be CSV or Excel files.

Where the files live on the server is described in [Filesystem Structure](../../admin/filesystem.md).
