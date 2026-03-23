# ✏️ Data Editor & CSV Import

The Data Editor lets you **view, add, edit, and delete** individual exchange rate data points. For bulk loading, it includes a built-in **CSV Import** tool.

---

## 📝 Data Editor

Click the **Edit** button (✏️) in the chart toolbar to open the data editor panel:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="FX Data Editor" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👀 Viewing Data

The editor shows a scrollable table of all data points for this currency pair, sorted by date (newest first):

- 📅 **Date** — The observation date
- 💱 **Rate** — The exchange rate value
- 🏛️ **Source** — Where the data came from (provider name, CSV import, or manual)

### ➕ Adding a Data Point

1. Click **"Add"** at the top of the editor
2. Select the **date** from the date picker
3. Enter the **rate** value
4. Click **Save** — the point is immediately added and the chart updates

### ✏️ Editing a Data Point

1. Click the **pencil icon** next to any row
2. Modify the rate value
3. Click **Save** to confirm

### 🗑️ Deleting a Data Point

1. Click the **trash icon** next to any row
2. Confirm the deletion

!!! warning "Synced data overwrites manual edits"

    If you manually edit or add a data point for a date that is later covered by a sync, the provider's value will **overwrite** your manual edit — the provider is always treated as the authoritative source. For pairs where you want full manual control, use the MANUAL provider (no automatic data source) — see [Provider Config](provider.md).

---

## 📥 CSV Import

For bulk loading historical rate data, use the CSV Import tool.

### 🔓 How to Access

1. Open the Data Editor (pencil icon ✏️)
2. Click **"Import CSV"** to open the import modal

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="CSV Import Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

### 📄 CSV File Format

The CSV file must have **exactly 2 columns** with a **header row** that specifies the direction:

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

### 📏 Rules

| Rule | Details |
|------|---------|
| **Separator** | Semicolon (`;`) |
| **Date format** | `YYYY-MM-DD` |
| **Rate values** | Positive decimal numbers |
| **Header** | Required — must contain the direction (e.g., `EUR>USD`) |
| **Direction arrow** | Use `>` or `<` (both are supported) |

### ↔️ Direction in the Header

The header tells LibreFolio which direction the rates are expressed in:

- ➡️ `date;EUR>USD` means: **1 EUR = X USD** (rates are EUR→USD)
- ⬅️ `date;USD>EUR` means: **1 USD = X EUR** (rates are USD→EUR)

If you're on the EUR/USD page and your CSV has `USD>EUR` rates, LibreFolio will automatically invert the values.

---

### 🔀 Direction & Swap

The import modal shows a **direction bar** indicating how your data will be interpreted:

- ➡️ **Left currency** → **Right currency**: the rate tells you how much of the right currency you get for 1 unit of the left currency
- 🔄 Use the **swap button (⇄)** to flip the direction if your data is in the opposite format

The header in your CSV determines the direction automatically. If the header says `EUR>USD`, the modal sets the direction to EUR→USD.

---

### 📋 Examples

#### ✅ Minimal Valid File

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
```

#### ✅ Inverted Direction

```csv
date;USD>EUR
2024-01-02;0.9053
2024-01-03;0.9106
```

This is equivalent to the first example — LibreFolio inverts `0.9053` to `1/0.9053 ≈ 1.1045`.

#### ❌ Invalid File

```csv
date;GBP>JPY
2024-01-02;188.45
```

This will fail if you're on the EUR/USD page — the header currencies must match the page's pair.

---

### ⚠️ Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| **"Header currencies don't match"** | Header has currencies not on this page | Check the pair and fix the header |
| **"Missing or invalid header"** | No header row, or wrong format | Add a header like `date;EUR>USD` |
| **"Duplicate dates"** | Same date appears multiple times | Remove duplicates |
| **"Invalid rate"** | Non-numeric or negative value | Ensure all rates are positive numbers |
| **"Invalid date format"** | Date not in `YYYY-MM-DD` format | Fix date formatting |

---

### 🔀 Merge Behavior

When importing via CSV or adding points manually in the editor:

- Changes are first applied to the **local client cache** (visible immediately in the chart)
- Changes are **not persisted** to the database until you click **Save**
- 🔄 **Existing data points** in the database will be **overwritten** with the imported values upon save
- 🆕 **New dates** are added
- ✅ **Dates not in the import** are left untouched

This allows you to selectively update specific date ranges without affecting the rest of your data.

!!! tip "Best for MANUAL pairs"

    The data editor is most useful for pairs configured with the MANUAL provider (no automatic data source). For provider-backed pairs, manual edits will be overwritten on the next sync.

