# 🪟 Modals

The modal system in LibreFolio. Every modal extends `ModalBase`.

```mermaid
graph TD
    MB["ModalBase<br/><small>Backdrop · Escape · Focus trap<br/>z-index · Scroll lock · Animation</small>"]
    MB --> CM["ConfirmModal<br/><small>Destructive action dialog</small>"]

    MB -.->|used by| BM["BrokerModal"]
    MB -.->|used by| BSM["BrokerSharingModal"]
    MB -.->|used by| BIM["BrokerImportFilesModal"]
    MB -.->|used by| IEM["ImageEditModal"]
    MB -.->|used by| CSM["ChartSettingsModal"]
    MB -.->|used by| DIM["DataImportModal"]
    CM -.->|used by| DBD["DeleteBrokerDialog"]

    style MB fill:#f3e5f5,stroke:#7b1fa2
    style CM fill:#f3e5f5,stroke:#7b1fa2
```

---

## 🏗️ ModalBase

The **foundation for all modals** in LibreFolio.

- **Backdrop** with configurable opacity and click-outside-to-close
- **Escape** key to close
- **Focus trap** — Tab cycles within modal content
- **Configurable z-index** — Supports stacked modals (e.g., ImageEditModal over AssetPickerModal)
- **Scroll lock** — Prevents body scroll when modal is open
- **Animation** — Fade-in/out transition

**Props**: `isOpen`, `onClose`, `zIndex` (default: 50), `closeOnBackdrop` (default: true), `maxWidth`.

---

## ⚠️ ConfirmModal

A confirmation dialog for **destructive actions**. Extends `ModalBase`.

- Displays a warning message with customizable title and body
- **Confirm** and **Cancel** buttons with configurable labels
- Confirm button styled as danger (red) by default
- Optional loading state on confirm button

**Used by**: [DeleteBrokerDialog](../brokers/modals.md), file deletion, data editor row deletion.

