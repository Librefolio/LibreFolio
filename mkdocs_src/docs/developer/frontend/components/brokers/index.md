# 🏦 Broker Components

Components in `lib/components/brokers/` that power the broker management UI.

## Component Composition

```mermaid
graph TD
    subgraph Cards
        BC["BrokerCard<br/><small>Broker display + actions</small>"]
        CBC["CashBalanceCard<br/><small>Multi-currency balance</small>"]
    end

    subgraph Forms
        BF["BrokerForm<br/><small>Create/edit fields</small>"]
        BI["BrokerIcon<br/><small>4-step fallback chain</small>"]
    end

    subgraph Modals
        BM["BrokerModal<br/><small>Create/edit wrapper</small>"]
        BSM["BrokerSharingModal<br/><small>RBAC sharing</small>"]
        BIM["BrokerImportFilesModal<br/><small>BRIM file import</small>"]
        DBD["DeleteBrokerDialog<br/><small>Confirm deletion</small>"]
        CTM["CashTransactionModal<br/><small>Deposit/withdrawal</small>"]
    end

    BM --> BF
    BF --> BI
    BF --> CSS["CurrencySearchSelect"]
    BC --> BI
    BSM --> SrS["SearchSelect (users)"]
    BIM --> IPS["ImportPluginSelect"]
    BIM --> FU["FileUploader"]
    DBD --> CM["ConfirmModal"]
    BM --> MB["ModalBase"]
    BSM --> MB
    BIM --> MB
    CTM --> MB

    style Cards fill:#e3f2fd,stroke:#1565c0
    style Forms fill:#e8f5e9,stroke:#2e7d32
    style Modals fill:#fff3e0,stroke:#e65100
```

## Sub-sections

| Section | Components | Description |
|---------|-----------|-------------|
| **[Cards](cards.md)** | BrokerCard, CashBalanceCard | Display components for broker list and detail |
| **[Forms](forms.md)** | BrokerForm, BrokerIcon | Create/edit form and smart icon with fallback |
| **[Modals](modals.md)** | BrokerModal, BrokerSharingModal, BrokerImportFilesModal, DeleteBrokerDialog, CashTransactionModal | All broker-related modal dialogs |

All modals extend [ModalBase](../ui-base.md#modalbase) from the UI Base components.

