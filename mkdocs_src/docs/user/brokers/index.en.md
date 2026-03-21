# 🏦 Brokers

A **Broker** in LibreFolio represents a brokerage account — the place where your investments live (e.g., Interactive Brokers, Degiro, a bank account).

All transactions, reports, and import data are tied to a broker. You need at least one broker to start tracking your portfolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Creating a Broker

1. Navigate to the **Brokers** page from the sidebar
2. Click **"New Broker"**
3. Fill in the details: name, base currency, and optionally an icon
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Broker Edit Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. The broker appears in your list, ready to receive transactions and reports
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Edit Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
---

## 🔧 What Can You Do With a Broker?

| Feature | Description | Status |
|---------|-------------|--------|
| **View details** | Name, currency, creation date, icon | ✅ Available |
| **Upload reports** | CSV/Excel files from your real broker | ✅ Available |
| **Share access** | Invite other users with role-based permissions | ✅ Available |
| **Import transactions** | Automatic parsing of uploaded reports via BRIM | 🔜 Coming soon |
| **View transactions** | List, filter, and manage imported trades | 🔜 Coming soon |

!!! note "Work in Progress"
    The broker detail page and transaction management UI are under active development. Currently you can create brokers, upload reports, and share access. Full transaction import and visualization will be added in upcoming phases.

---

## 📑 In This Section

- 🤝 **[Broker Sharing](sharing.md)** — How to share access with other users (family, advisors, accountants)
