# ⚙️ Broker Configuration & AI Export

The **Info** tab houses metadata configuration, safety controls, the scoped AI Export tool, and the sharing configuration panel.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Broker Info and Sharing View">
</div>

---

## ⚙️ Metadata & Settings

The left column of the Info tab displays key properties and validation rules for this broker:

- **Broker Status**: Shows whether the account is currently `Active`. Inactive brokers are hidden from list drop-downs but their historical values are preserved in charts.
- **Dates**: Renders when the account was opened and when it was created in LibreFolio.
- **Base Currency**: The base currency of the account (all transactions and valuations are internally converted using historical FX rates to this currency for local reporting).
- **Allow Cash Overdraft**: A toggle to bypass negative balance errors. When disabled, LibreFolio blocks transactions (like purchases or withdrawals) that would result in a negative cash balance.
- **Allow Short Positions**: A toggle to authorize negative asset quantities. When disabled, selling more than your current open position size is blocked.

---

## 🧠 Scoped AI Export

At the top right of the broker toolbar, **AI Export** (:material-brain:) opens
four dedicated Broker tasks—not filtered Portfolio prompts:

- **Broker Review**
- **Broker Cost Efficiency**
- **Broker Concentration Context**
- **FIFO Lot Review**

The backend snapshot is limited to the selected broker and can include its cash,
holdings, activity, performance, costs, concentration, and FIFO lots according
to the selected task. Server-side access checks prevent exporting a broker the
current user cannot access. LibreFolio only copies the result to the clipboard;
review sensitive financial data before sharing it. See
[Broker AI Export](../ai-export/broker.md) or the
[AI Export overview](../ai-export/index.md).

---

## 🤝 Access Sharing Panel

The right column of the Info tab houses the inline **Broker Sharing** manager. Here you can:

- Invite other users by their email or username.
- Define their role permission (Owner, Editor, Viewer).
- Configure ownership percentages.

For a detailed explanation of sharing rules, roles, and percentage logic, please refer to the dedicated **[Broker Sharing](sharing.md)** page.
