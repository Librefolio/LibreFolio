# 📄 Generic CSV

The **Generic CSV** provider is a flexible fallback for brokers that are not directly supported. It allows manual column mapping so you can import from any CSV-based export.

## When to Use

- Your broker is not in the supported list.
- A supported broker changed its export format and the plugin hasn't been updated yet.
- You have a custom spreadsheet you want to import.

## How It Works

1. Upload your CSV file.
2. LibreFolio shows the raw columns detected.
3. Map each column to the corresponding LibreFolio field (date, type, asset, quantity, price, amount, currency, fee).
4. Preview the parsed rows and confirm import.

!!! tip "Add a native plugin"

    If you use a broker frequently, consider contributing a native plugin. See the [Developer Manual → BRIM Plugin Guide](../../../developer/backend/brim/generic_csv.md) for instructions.

## 🔗 Developer Reference

→ [Generic CSV Provider — Implementation Details](../../../developer/backend/brim/generic_csv.md)
