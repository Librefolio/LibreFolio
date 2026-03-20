# 📋 Case Study: The Generic CSV Provider

The **Generic CSV Provider** (`broker_generic_csv`) is the fallback import plugin for BRIM. It is designed to be highly flexible and serves as an excellent case study for
understanding the BRIM plugin architecture.

Its primary goal is to parse simple CSV files even if they don't come from a specifically supported broker.

## Key Features

- **Header Auto-Detection**: It doesn't rely on fixed column names. Instead, it maintains a dictionary of possible header names for each standard field (e.g., `date` can be "
  Date", "data", "Trade Date", etc.).
- **Flexible Date Parsing**: It attempts to parse dates using a list of common formats (e.g., `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`).
- **Flexible Number Parsing**: It can handle both US (`1,234.56`) and European (`1.234,56`) number formats.
- **Transaction Type Mapping**: It maps common keywords (e.g., "buy", "acquisto", "compra") to the standard `TransactionType` enum.
- **Low Priority**: It has a `detection_priority` of `0`, ensuring that more specific, high-confidence plugins are always tried first.

## Column Mapping Reference

When creating a CSV file for import (or a new plugin), these are the standard columns that LibreFolio expects. The Generic CSV provider tries to map input columns to these
concepts.

| Standard Column   | Description                                 | Expected Content                                                                                                    |
|:------------------|:--------------------------------------------|:--------------------------------------------------------------------------------------------------------------------|
| **`date`**        | **Required**. The date of the transaction.  | A valid date string (e.g., `2023-12-31`, `31/12/2023`).                                                             |
| **`type`**        | **Required**. The type of operation.        | One of: `BUY`, `SELL`, `DIVIDEND`, `INTEREST`, `DEPOSIT`, `WITHDRAWAL`, `FEE`, `TAX`.                               |
| **`quantity`**    | The number of units involved.               | A number. Positive for BUY/DEPOSIT, usually negative for SELL/WITHDRAWAL (though the plugin may auto-adjust signs). |
| **`amount`**      | The total cash value of the transaction.    | A number representing the net impact on cash balance.                                                               |
| **`currency`**    | The currency of the `amount`.               | ISO 4217 code (e.g., `EUR`, `USD`). Defaults to `EUR` if missing.                                                   |
| **`asset`**       | The identifier of the financial instrument. | Ticker symbol (e.g., `AAPL`), ISIN (e.g., `US0378331005`), or name. Required for BUY/SELL/DIVIDEND.                 |
| **`description`** | Optional notes.                             | Any text string.                                                                                                    |

## How it Works: A Deeper Look

### 1. Column Detection (`_detect_columns`)

When the `parse()` method is called, the first step is to map the CSV's header row to LibreFolio's standard fields.

```python
# A simplified view of the mapping dictionary
HEADER_MAPPINGS = {
    "date": ["date", "data", "settlement_date", ...],
    "type": ["type", "tipo", "operation", ...],
    "asset": ["asset", "symbol", "ticker", "isin", ...],
    # ... and so on
}

def _detect_columns(self, fieldnames: List[str]) -> Dict[str, str]:
    column_map = {}
    for csv_col in fieldnames:
        csv_col_lower = csv_col.lower().strip()
        for std_name, variations in HEADER_MAPPINGS.items():
            if csv_col_lower in variations:
                column_map[std_name] = csv_col
                break
    return column_map
```

This creates a `column_map` like `{'date': 'Data operazione', 'type': 'Tipo operazione'}` which is then used to read data from each row.

### 2. Row Parsing (`_parse_row`)

For each row in the CSV, the `_parse_row` method is called.

1. **Extract Values**: It uses the `column_map` to get the raw string values for date, type, quantity, etc.
2. **Parse Date**: It calls `parse_date()`, which tries multiple `strptime` formats until one succeeds.
3. **Parse Type**: It looks up the lowercase type string in the `TYPE_MAPPINGS` dictionary.
4. **Parse Numbers**: It uses `parse_decimal()` to handle different decimal and thousands separators.
5. **Handle Assets**:
    - It extracts the asset identifier (e.g., "AAPL", "US0378331005").
    - It calls `_classify_asset_identifier()` to make a best guess on whether the identifier is a symbol, ISIN, or name.
    - It assigns a consistent **fake asset ID** for each unique asset identifier found in the file. This allows the user to map all "AAPL" transactions to the correct asset in one
      go during the review step.

### 3. The "Gold Standard" Example

The Generic CSV Provider is the perfect starting point for creating a new, specific broker plugin. You can copy its structure and then:

1. Increase the `detection_priority` to `100`.
2. Add a `can_parse()` method to reliably detect your specific broker's file format.
3. Customize the `HEADER_MAPPINGS` and `TYPE_MAPPINGS` to match your broker's specific terminology.
4. Refine the parsing logic to handle any quirks of your broker's CSV format.
