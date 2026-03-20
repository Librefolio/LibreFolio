# 🏦 Broker Components

This section documents the components in `lib/components/brokers/` that power the broker management UI.

---

## BrokerCard

Displays a broker as a card in the broker list page.

- Shows **BrokerIcon**, name, base currency, and description
- **Cash balance** display with multi-currency breakdown
- Quick action buttons: Edit (✏️), Delete (🗑️), Navigate to detail
- Role badge for shared brokers: 👑 Owner, ✏️ Editor, 👁️ Viewer

**Used in**: `/brokers` list page — one card per broker.

---

## BrokerForm

The create/edit form for a broker.

- Fields: name, description, base currency (`CurrencySearchSelect`), portal URL
- Icon selection via `ImagePickerWrapper` (upload, URL, or pick from existing)
- Default import plugin selection via `ImportPluginSelect`
- `allow_cash_overdraft` toggle
- Validation: name required, currency required

**Used in**: `BrokerModal` — wrapped in a modal for create/edit flows.

---

## BrokerIcon

A smart icon component with a **4-step fallback chain**:

1. **`icon_url`** — Custom uploaded icon (if user set one)
2. **`portal_url` favicon** — Automatically fetched via Google Favicon API
3. **`default_import_plugin` icon** — Icon from the broker's BRIM plugin (loaded from API)
4. **`Briefcase`** — Default Lucide icon as last resort

Supports three sizes: `sm` (24px), `md` (32px), `lg` (48px).

**Used in**: `BrokerCard`, `BrokerSearchSelect`, broker detail page header.

---

## BrokerModal

Modal wrapper for creating or editing a broker. Extends `ModalBase`.

- Wraps `BrokerForm` with save/cancel actions
- Create mode: calls `POST /brokers`
- Edit mode: calls `PATCH /brokers/{id}`, pre-fills form with existing data
- Shows `InfoBanner` for validation errors

**Used in**: `/brokers` page — triggered by "New Broker" button or Edit action.

---

## BrokerImportFilesModal

Modal for importing broker report files via the BRIM system.

- **Plugin selection** via `ImportPluginSelect` — choose the parser for this broker's CSV/Excel format
- **File upload** with drag & drop via `FileUploader`
- Preview of uploaded files with status indicators
- Triggers BRIM parsing pipeline on submit

**Used in**: Broker detail page — "Import Files" action.

---

## BrokerSharingModal

Modal for managing broker sharing with RBAC.

- **User search** via `SearchSelect` — find users to share with
- **Role assignment**: Owner, Editor, Viewer
- **Share percentage** — ownership percentage for portfolio aggregation (e.g., 50% for joint accounts)
- User list with inline role editing and removal
- Displays current access list with role badges

**Used in**: Broker detail page — "Share" action.

---

## DeleteBrokerDialog

A `ConfirmModal` for broker deletion.

- Shows broker name and warns about data loss
- Requires explicit confirmation
- Calls `DELETE /brokers` on confirm

**Used in**: `BrokerCard` — Delete action.

---

## CashBalanceCard

Displays the cash balance for a broker, broken down by currency.

- Shows total balance with multi-currency rows
- Color coding: green for positive, red for negative (overdraft)
- Links to cash transaction history

**Used in**: Broker detail page sidebar.

---

## CashTransactionModal

Modal for recording cash operations (deposits and withdrawals).

- Transaction type: Deposit or Withdrawal
- Amount and currency fields
- Date picker
- Optional notes

**Used in**: Broker detail page — "Add Cash" action.

