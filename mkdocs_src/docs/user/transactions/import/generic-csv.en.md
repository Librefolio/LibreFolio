# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> Generic CSV

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
