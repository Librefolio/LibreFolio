# 💸 Transactions

Transactions represent every financial activity within your portfolio. Every purchase, sale, dividend, fee, asset transfer, and cash movement is recorded here to keep your portfolio statistics, performance, and tax records up to date.

Each broker account in LibreFolio has its own dedicated transaction log, showing all movements in reverse chronological order.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Transaction List">
</div>

---

## 🚀 Getting Started

Managing your transactions is straightforward:

* 📝 **Manual Entry & Editing**: Open the interactive **[Transaction Form](form.md)** to manually add, edit, or adjust individual operations.
* 📥 **Super-Easy Broker Import**: You don't need to type everything by hand! LibreFolio allows you to upload CSV or XLSX exports from your broker and automatically map and import them in seconds. Learn more in the **[Import from Broker](import/index.md)** guide.

---

## 🛠️ Page Features

Here is a summary of the operations and tools available directly within the transaction page:

| Feature | Description | Reference |
|---------|-------------|-----------|
| **Add & Edit** | Click **Add Transaction** to open the form, or click any existing row to edit its details. | [Transaction Form](form.md) |
| **Broker Import** | Click **Import** to upload a broker statement and import your history automatically. | [Import from Broker](import/index.md) |
| **Sorting & Filtering** | Click any column header to sort the list. Use the search bar to filter by asset name, type, or notes. | |
| **Deleting & Bulk Actions** | Right-click any row to open the Context Menu for quick actions. Deleting a single row and checking multiple rows for bulk deletion both open the same **bulk workspace**, where rows are staged for deletion before you confirm; a linked partner (FX trade or transfer leg) is automatically staged together with the row you picked. | |

Duplicating works the same way: **Clone** from the context menu stages a copy in the bulk workspace — keeping the **original date** (cloning is how a misclassified historical row gets corrected, so the date must survive) — where you adjust and save it.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Bulk workspace with a cloned transaction row">
</div>

| **Composite & Promotion** | Link single operations (like two cash legs) into a **Composite Transaction** via **Promotion** to enable advanced tracking and portfolio analytics, or split a composite transaction back into single operations. | [Transaction Form](form.md#composite-transactions) |

---

## 🔗 Related

* 📝 **[Transaction Form](form.md)** — Fields, validation, and type-specific options
* 📥 **[Import from Broker](import/index.md)** — BRIM import workflow
* 📖 **[Transaction Types](../../financial-theory/instruments/transaction-types/index.md)** — Financial theory behind each type
