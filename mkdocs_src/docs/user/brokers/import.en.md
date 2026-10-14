# 📥 Broker Transactions

The **Transactions** tab of a broker lists all its transactions, newest first. It always shows the broker's whole history: the date range in the toolbar does not filter it.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Broker Transactions Tab">
</div>

Above the list you find **Uploaded Reports**, **View in Transactions** and the column picker. Owners and Editors also get **Import** and **Add Transaction**.

---

## ➕ Add a transaction

1. Click **Add Transaction**. The transaction workspace opens on a **New transaction** form, with this broker already selected.
2. Pick the **Type** and fill in the required fields — see [Transaction Form](../transactions/form.md).
3. Click **Apply** to place the row in the workspace, then **Save All** to write it.

Nothing is saved before **Save All**: until then you can add more rows, change them or cancel (see [The bulk workspace](../transactions/index.md#bulk-workspace)).

---

## 🔎 Open, edit or delete transactions

- **Double-click** a row to open it read-only.
- To edit, clone or delete rows, click **View in Transactions**: the [Transactions](../transactions/index.md) page opens, filtered on this broker and on the column filters you set here.

---

## 🧙 Import a statement

**Import** opens the workspace together with the **Import Wizard** (BRIM, the Broker Report Import Module). The wizard reads the files exported by your broker, lets you check every row, and hands the result to the workspace: nothing is written until **Save All**.

- 📥 **[Import from Broker](../transactions/import/index.md)** — supported brokers and formats.
- 🧙 **[How to Import Transactions](../transactions/import/how-to.md)** — the wizard, step by step.

The same wizard opens from **Import** on the [Transactions](../transactions/index.md) page.

??? tip "🧩 Your broker is not supported yet — what you can do"

    - **Request a plugin**: open a [plugin request](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml) on GitHub and attach an anonymised sample of the broker's export.
    - **Write a plugin**: the [BRIM Plugin Guide](../../developer/architecture/patterns/brim_plugin_guide.md) explains the plugin contract, and [Contribute](../../community/contribute.md) the workflow.
    - If imported rows keep looking wrong, the wizard's **Corrections** step links to GitHub so you can report a possible importer bug.

---

## 🗂️ Uploaded reports

**Uploaded Reports** opens the report files stored for this broker:

- **Upload** CSV or Excel files: they are assigned to this broker and listed in the wizard's **Select Files** step. Files you upload together form one set — this is how banks that split an account across several exports, such as Danske Bank, are imported.
- **Preview** or **Delete** a file. Deleting a report never deletes the transactions imported from it.
- Check each file's **Status** and **Report set** badges — see [Report sets](../files/index.md#report-sets).
- **Manage all files** opens the [Files & Uploads](../files/index.md#broker-reports) page, filtered on this broker.

Uploading and deleting reports needs Owner or Editor access to the broker.
