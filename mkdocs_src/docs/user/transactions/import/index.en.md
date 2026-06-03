# 📥 Import from Broker (BRIM)

**BRIM** (Broker Report Import Module) lets you import transactions directly from your broker's export files — no manual entry needed. Upload a CSV report and LibreFolio parses, maps, and imports all transactions in one flow.

---

## 🚀 How to Import

1. Export a transaction report from your broker (usually a CSV file — check your broker's help center).
2. In LibreFolio, navigate to your **Broker** page.
3. Click the **Import** button (:material-file-upload:) in the broker header.
4. The **Import Modal** opens.
5. **Drag & drop** or click to select your file.
6. LibreFolio **auto-detects** the broker format and shows a **preview** of parsed transactions.
7. Review the preview — check that dates, amounts, and asset names look correct.
8. Click **Import** to commit all transactions.

!!! tip "You can also use the Files section"

    The **[Files](../../files/index.md)** section (BRIM tab) lets you manage uploaded broker reports centrally, re-import them, or delete them.

---

## 🏦 Supported Brokers

| Broker | Page |
|--------|------|
| Interactive Brokers (IBKR) | [→](ibkr.md) |
| Degiro | [→](degiro.md) |
| eToro | [→](etoro.md) |
| Directa SIM | [→](directa.md) |
| Charles Schwab | [→](schwab.md) |
| Revolut | [→](revolut.md) |
| Coinbase | [→](coinbase.md) |
| Freetrade | [→](freetrade.md) |
| Finpension | [→](finpension.md) |
| Trading212 | [→](trading212.md) |
| Generic CSV | [→](generic-csv.md) |

!!! note "All providers are in Beta"

    Import plugins are community-maintained and improve over time. If a specific report format has quirks, the **[Generic CSV](generic-csv.md)** provider allows manual column mapping as a fallback.

---

## 🗂️ Asset Mapping

During the preview step, LibreFolio attempts to **auto-match** each asset name from your report to an asset already in your library.

- ✅ **Matched** — will be imported against the existing asset.
- ⚠️ **Unmatched** — select or create the target asset before importing.
- ❌ **Error** — the row could not be parsed.

---

## ♻️ Duplicate Detection

BRIM checks for **duplicate transactions** based on date, type, asset, quantity, and amount. Duplicate rows are flagged in the preview — you can choose to skip or force-import them.

---

## 🔗 Related

- 📋 **[Transaction Table](../index.md)** — View and manage imported transactions
- 🗂️ **[Files](../../files/index.md)** — Manage uploaded broker report files
- 🏦 **[Brokers](../../brokers/index.md)** — Set up your broker accounts first
