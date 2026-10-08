# ✏️ Data Editor & CSV Import

The Data Editor lets you add, change and delete a pair's stored rates one by one, or load many at
once from a CSV file. Nothing is saved until you click **Save**.

---

## 📝 Open the editor

Click ✏️ (**Edit Rates**) on the chart. The editor opens below the chart, and the other panels fold
away while you edit.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="FX Data Editor" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

It lists the rates of the selected period with their **Date**, **Rate** and **Status** (**Original**,
**Edited**, **Deleted** or **New**).

- A date marked ⚠️ and a number of days has no rate of its own (a weekend or a bank holiday) and
  repeats the previous one. The ⚠️ switch at the top hides these days.
- Double-click a point on the chart (long-press on mobile) to jump to its date in the editor.

---

## ✍️ Change rates

### ➕ Add a rate

Click **Add Row**: a row appears on the day after the last one, never later than today. Change its
date with the date picker if needed, then type the rate.

### ✏️ Edit a rate

Click a rate and type the new value.

### 🗑️ Delete rates

Click 🗑️ on a row, or select rows and click the bin at the top. **Undo** brings a row back until you
save.

### 💾 Save your changes

Your changes show on the chart as a purple **Preview** line. **Save (N)** writes them all;
**Cancel** drops them. A rate must be greater than zero: a zero, negative or empty one is skipped.

!!! warning "Synced data overwrites manual edits"

    A later sync of the same dates replaces your values with the provider's. For full manual
    control, use a pair without a provider — see [Provider Config](provider.md).

---

## 📥 CSV import

### 🔓 Open the import window

1. In the editor, click **Import CSV**.
2. In **Import CSV Data**, drop a `.csv` or `.txt` file, or paste the text into the box.
3. Check the direction at the top, then click **Import (N)**.

The rows join the editor: review them, then click **Save**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="CSV Import Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📄 File format

Two columns, with a header row that sets the direction:

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

| Rule | Details |
|------|---------|
| **Separator** | Semicolon (`;`) |
| **Header** | `date` and the direction, e.g. `EUR>USD` |
| **Dates** | `YYYY-MM-DD` |
| **Rates** | Positive numbers; `.` or `,` as decimal mark, optional `_` for thousands (`1_000.50`) |

### ↔️ Direction

- `EUR>USD` means **1 EUR = X USD**; `EUR<USD` is the other way round, **1 USD = X EUR**.
- The header must name this pair's two currencies, in either order.
- The bar at the top shows how the rates are read (*Rates interpreted as: 1 EUR = X USD*); ⇄ flips
  it and rewrites the header.
- A file in the opposite direction to the page is inverted for you: each rate $r$ becomes $1/r$.

??? example "📋 Examples — the same rates written in both directions"

    ```csv
    date;EUR>USD
    2024-01-02;1.1045
    2024-01-03;1.0982
    ```

    ```csv
    date;USD>EUR
    2024-01-02;0.9053
    2024-01-03;0.9106
    ```

    On the EUR/USD page both files give the same rates: `0.9053` becomes $1/0.9053 \approx 1.1046$.

### ⚠️ Common errors

The import window marks each wrong line; only the valid lines are imported.

| Message | Cause | Fix |
|---------|-------|-----|
| **Header currencies don't match** | Other currencies in the header, e.g. `GBP>JPY` on the EUR/USD page | Use this pair's currencies |
| **Expected header** or **Missing required columns** | No header row, or a column is missing | Start with a line such as `date;EUR>USD` |
| **Invalid date format** | The date is not `YYYY-MM-DD` | Fix the date |
| **Invalid number** | The rate is not a number | Fix the value |
| **Duplicate date** | The same date appears twice | Keep one line per date |

??? info "🔀 How imported rows merge — when the editor already has some of the dates"

    - A date already in the editor takes the imported rate (**Edited**); a new date is added
      (**New**). Dates missing from the file stay as they are.
    - Dates outside the selected period are saved too, replacing any rate stored on those days;
      after saving, the period widens to show them.
