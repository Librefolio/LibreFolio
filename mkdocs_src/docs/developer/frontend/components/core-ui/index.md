# 🧱 Core UI Components

Generic, reusable components in `lib/components/ui/` that serve as building blocks for all composite components.

## 🗺️ Dependency Map

```mermaid
graph TD
    subgraph "Modals"
        MB["ModalBase"] --> CM["ConfirmModal"]
        MB --> DIM["DataImportModal"]
    end

    subgraph "Pickers"
        CAL["CalendarMonth"] --> SDP["SingleDatePicker"]
        CAL --> DRP["DateRangePicker"]
    end

    subgraph "Datapoint Editor"
        DIM --> CSE["CsvEditor"]
        DE["DataEditor"] --> SDP
    end

    MB -.->|used by| BM["Broker Modals"]
    MB -.->|used by| IE["ImageEditModal"]
    CM -.->|used by| DEL["Delete Dialogs"]
    DRP -.->|used by| CT["Chart Toolbar"]
    DE -.->|used by| FX["FX Data Editor"]

    style MB fill:#f3e5f5,stroke:#7b1fa2
    style CM fill:#f3e5f5,stroke:#7b1fa2
    style CAL fill:#e3f2fd,stroke:#1565c0
    style SDP fill:#e3f2fd,stroke:#1565c0
    style DRP fill:#e3f2fd,stroke:#1565c0
    style DE fill:#e8f5e9,stroke:#2e7d32
    style DIM fill:#e8f5e9,stroke:#2e7d32
    style CSE fill:#e8f5e9,stroke:#2e7d32
```

## 📑 Sub-sections

| Section | Components | Description |
|---------|-----------|-------------|
| **[Modals](modals.md)** | ModalBase, ConfirmModal | Foundation for all modal dialogs |
| **[Feedback](feedback.md)** | ToastContainer, InfoBanner, LoadingSpinner, Tooltip | Notifications and user feedback |
| **[Pickers](datePickers.md)** | CalendarMonth, SingleDatePicker, DateRangePicker | Date selection components |
| **[Atoms](atoms.md)** | ThemeToggle, DocsLink, AnimatedBackground, OrderableList, PasswordInput, PasswordStrength | Small standalone UI primitives |
| **[Datapoint Editor](data-editor.md)** | DataEditor, CsvEditor, DataImportModal | Inline editing and CSV import for financial datapoints |
