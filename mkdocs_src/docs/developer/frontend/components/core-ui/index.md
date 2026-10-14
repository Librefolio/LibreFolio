# 🧱 Core UI Components

Generic, reusable components — in `lib/components/ui/`, plus the DataTable in `lib/components/table/` — that serve as building blocks for all composite components.

## 🗺️ Dependency Map

```mermaid
graph TD
    subgraph "Modals"
        MB["ModalBase"] --> CM["ConfirmModal"]
        MB --> SMB["SyncModalBase"]
        SMB --> PSM["PageSyncModal"]
        MB --> DIM["DataImportModal"]
    end

    subgraph "Pickers"
        CAL["CalendarMonth"] --> SDP["SingleDatePicker"]
        CAL --> DRP["DateRangePicker"]
        DRP --> CDB["CompactDurationBadge"]
    end

    subgraph "Toolbar"
        PT["PageToolbar"] --> TB["TabBar"]
        PT -.->|filters snippet| DRP
    end

    subgraph "Datapoint Editor"
        DIM --> CSE["CsvEditor"]
        DE["DataEditor"] --> SDP
    end

    MB -.->|used by| BM["Broker Modals"]
    MB -.->|used by| IE["ImageEditModal"]
    CM -.->|used by| DEL["Confirm & discard dialogs"]
    DRP -.->|used by| DTF["DataTable date filter"]
    DE -.->|used by| FX["FX & asset data editors"]
    PT -.->|used by| PAGES["Dashboard · Broker Detail · Assets · FX"]

    style MB fill:#f3e5f5,stroke:#7b1fa2
    style CM fill:#f3e5f5,stroke:#7b1fa2
    style SMB fill:#f3e5f5,stroke:#7b1fa2
    style PSM fill:#f3e5f5,stroke:#7b1fa2
    style CAL fill:#e3f2fd,stroke:#1565c0
    style SDP fill:#e3f2fd,stroke:#1565c0
    style DRP fill:#e3f2fd,stroke:#1565c0
    style CDB fill:#e3f2fd,stroke:#1565c0
    style DE fill:#e8f5e9,stroke:#2e7d32
    style DIM fill:#e8f5e9,stroke:#2e7d32
    style CSE fill:#e8f5e9,stroke:#2e7d32
    style PT fill:#fff3e0,stroke:#e65100
    style TB fill:#fff3e0,stroke:#e65100
```

`PageToolbar` does not import the date picker: the page renders a `DateRangePicker` inside the
toolbar's `filters` snippet.

## 📑 Sub-sections

| Section | Components | Description |
|---------|-----------|-------------|
| **[Modals](modals.md)** | ModalBase, ConfirmModal, SyncModalBase, PageSyncModal | Foundation for all modal dialogs, confirmations and provider syncs |
| **[Feedback](feedback.md)** | ToastContainer, InfoBanner, DataQualityBanner, LoadingSpinner, Tooltip | Notifications and user feedback |
| **[Pickers](datePickers.md)** | CalendarMonth, SingleDatePicker, DateRangePicker | Date selection components |
| **[Toolbar & Responsive Layout](toolbar.md)** | PageToolbar, TabBar, `responsiveLayout.svelte.ts` | Container-width-driven responsive page toolbar shell |
| **[Atoms](atoms.md)** | ThemeToggle, PrivacyToggle, DocsLink, AnimatedBackground, OrderableList, PasswordInput, PasswordStrength, ExactDecimalInput, ExactQuantityInput, CompactDurationBadge, display blocks (KpiMetricBar, KpiDivergingFlowBar, RiskMetricCard, RiskCardGrid, CurrencyAmount, …) | Small standalone UI primitives, inputs and display blocks |
| **[Datapoint Editor](data-editor.md)** | DataEditor, CsvEditor, DataImportModal | Inline editing and CSV import for financial datapoints |
| **[DataTable](data-table.md)** | DataTable, DataTablePagination, ColumnVisibilityToggle | Sortable, filterable, paginated data grid |
| **[File Upload & Media](file-upload.md)** | FileUploader, ImageCropper, ImageEditModal, AssetPickerModal, LazyImage | Uploads and image handling |
| **[Select & Dropdowns](select.md)** | SimpleSelect, SearchSelect, TreeSelect, AssetTypeSelect, AssetPickerPanel, SelectPopover, CheckMenu, … | Selects; a typed search ranks [name matches first](select.md#ranking-the-matches) |
