# 🏦 Broker Components

Components in `lib/components/brokers/` that power the broker management UI.

## 📖 Overview

```mermaid
graph LR
    Cards["🃏 <b>Cards</b><br/><small>BrokerCard<br/>BrokerDiscoveryCard</small>"]
    Forms["📝 <b>Forms</b><br/><small>BrokerForm<br/>BrokerIcon</small>"]
    Modals["🪟 <b>Modals</b><br/><small>BrokerModal · SharingModal · SharingPanel<br/>ImportFiles · Delete</small>"]
    Lots["🔬 <b>Lots</b><br/><small>lots/ · LotsAnalysisPanel</small>"]

    Modals -->|wraps| Forms
    Cards -->|uses| Forms

    style Cards fill:#e3f2fd,stroke:#1565c0
    style Forms fill:#e8f5e9,stroke:#2e7d32
    style Modals fill:#fff3e0,stroke:#e65100
    style Lots fill:#f3e5f5,stroke:#7b1fa2
```

Each sub-section has its own detailed composition diagram. See the pages below.

## 📑 Sub-sections

| Section | Components | Description |
|---------|-----------|-------------|
| **[Cards](cards.md)** | BrokerCard, BrokerDiscoveryCard | The cards of the `/brokers` list page |
| **[Forms](forms.md)** | BrokerForm, BrokerIcon | Create/edit form and smart icon with fallback |
| **[Modals](modals.md)** | BrokerModal, BrokerSharingModal, BrokerSharingPanel, BrokerImportFilesModal, DeleteBrokerDialog | The broker dialogs, and the sharing panel that the Info tab embeds |
| **[Lots Analysis](../lots-analysis.md)** | `lots/` (LotsAnalysisPanel, UnifiedLotsTable, …) | The FIFO lots panel of the Positions views |

The dialogs are built on [ModalBase](../../core-ui/modals.md) from the UI Base components.
BrokerSharingPanel is a plain panel — wrapped by BrokerSharingModal, or embedded in the broker's
Info tab — whose add-user and edit-user dialogs are ModalBase too.
