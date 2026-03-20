# 🃏 Broker Cards

Display components for the broker list and detail pages.

---

## BrokerCard

Displays a broker as a card in the `/brokers` list page.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List with Cards" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### Features

- **BrokerIcon** + name, base currency, and description
- **Cash balance** display with multi-currency breakdown
- **Role badge** for shared brokers:
    - 👑 **Owner** — Full control
    - ✏️ **Editor** — Can modify
    - 👁️ **Viewer** — Read-only
- **Quick actions**: Edit (✏️), Delete (🗑️), Navigate to detail page

### Key Props

| Prop | Type | Description |
|------|------|-------------|
| `broker` | `BrokerRead` | Broker data object |
| `role` | `UserRole` | Current user's role for this broker |
| `cashBalances` | `CashBalance[]` | Multi-currency balance data |

**Events**: `edit`, `delete` — dispatched with broker ID.

---

## CashBalanceCard

Displays the cash balance for a broker, broken down by currency.

### Features

- **Total balance** with multi-currency row breakdown
- **Color coding**: green for positive balances, red for negative (overdraft)
- **Currency flags** via emoji for each currency row
- Links to cash transaction history

### Key Props

| Prop | Type | Description |
|------|------|-------------|
| `balances` | `CashBalance[]` | Array of `{ currency, amount }` |
| `baseCurrency` | `string` | Broker's base currency for total |

**Used in**: Broker detail page sidebar.

