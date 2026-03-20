# 🧩 Frontend Components

This section documents the reusable UI components in LibreFolio, organized by functional area.

## Component Library

| Category | Components | Details |
|----------|-----------|---------|
| **[UI Base](ui-base.md)** | ModalBase, ConfirmModal, Tooltip, ToastContainer, DateRangePicker, DataEditor, and more | Generic building blocks used by all composite components |
| **[DataTable](data-table.md)** | DataTable, Pagination, Toolbar, ColumnFilter, ModalBase, ConfirmModal | Advanced data grid with sorting, filtering, column management |
| **[Authentication](auth.md)** | LoginCard, RegisterCard, ForgotPasswordCard, PasswordStrengthMeter | Card-style auth forms with validation |
| **[Settings](settings.md)** | SettingsLayout, PreferencesTab, ProfileTab, GlobalSettingsTab, AboutTab | Two-column settings with categories |
| **[File Upload & Media](file-upload.md)** | FileUploader, ImageCropper, ImageEditModal, FileEditModal, AssetPickerModal, LazyImage | Upload, crop, edit, and pick media files |
| **[Select & Dropdowns](select.md)** | BaseDropdown, SimpleSelect, SearchSelect, CurrencySearchSelect, FxProviderSelect, BrokerSearchSelect | Keyboard-navigable dropdowns with search |
| **[Brokers](brokers/index.md)** | BrokerCard, BrokerForm, BrokerIcon, BrokerModal, BrokerSharingModal, CashBalanceCard | Broker CRUD, sharing, cash management |

## Component Guidelines

- **ModalBase**: ALL modals extend `ModalBase.svelte` with configurable z-index
- **Svelte 5 Runes**: Use `$state`, `$derived`, `$effect`, `$props`
- **Event handling**: Use `onclick` instead of `on:click` (Svelte 5 syntax)
- **Styling**: Tailwind CSS utilities + dark mode with `dark:` prefix
- **Accessibility**: Keyboard navigation, ARIA labels, focus management
- **i18n**: All user-facing text via `$t('key')` translation function
