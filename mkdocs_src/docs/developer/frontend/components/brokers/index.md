# 🏦 Broker Components

Components in `lib/components/brokers/` that power the broker management UI.

## 📖 Overview

```mermaid
graph LR
    Cards["🃏 <b>Cards</b><br/><small>BrokerCard<br/>CashBalanceCard</small>"]
    Forms["📝 <b>Forms</b><br/><small>BrokerForm<br/>BrokerIcon</small>"]
    Modals["🪟 <b>Modals</b><br/><small>BrokerModal · SharingModal<br/>ImportFiles · Delete · Cash</small>"]

    Modals -->|wraps| Forms
    Cards -->|uses| Forms

    style Cards fill:#e3f2fd,stroke:#1565c0
    style Forms fill:#e8f5e9,stroke:#2e7d32
    style Modals fill:#fff3e0,stroke:#e65100
```

Each sub-section has its own detailed composition diagram. See the pages below.

## 📑 Sub-sections

| Section | Components | Description |
|---------|-----------|-------------|
| **[Cards](cards.md)** | BrokerCard, CashBalanceCard | Display components for broker list and detail |
| **[Forms](forms.md)** | BrokerForm, BrokerIcon | Create/edit form and smart icon with fallback |
| **[Modals](modals.md)** | BrokerModal, BrokerSharingModal, BrokerImportFilesModal, DeleteBrokerDialog, CashTransactionModal | All broker-related modal dialogs |

All modals extend [ModalBase](../ui-base/modals.md) from the UI Base components.
