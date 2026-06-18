# 🧩 Frontend Components

This section documents the reusable UI components in LibreFolio, organized by functional area.

## 📚 Component Categories

The library is split into two architectural layers: **Core UI** (generic atoms and molecules) and **Features** (domain-specific components).

### Core UI
| Component | Details |
|-----------|---------|
| **[Atoms & Modals](core-ui/index.md)** | `ModalBase`, `ConfirmModal`, `Tooltip`, `ToastContainer`, `DateRangePicker`, `DataEditor`, `Button`, etc. Generic building blocks. |
| **[DataTable](core-ui/data-table.md)** | Advanced data grid with sorting, filtering, and column management. |
| **[File Upload & Media](core-ui/file-upload.md)** | `FileUploader`, `ImageCropper`, `ImageEditModal`, `AssetPickerModal`, `LazyImage`. |
| **[Select & Dropdowns](core-ui/select.md)** | `BaseDropdown`, `SimpleSelect`, `SearchSelect` with keyboard navigation. |

### Features (Domain)
| Component | Details |
|-----------|---------|
| **[Transaction Form](features/transaction-form.md)** | Complex modal for creating/editing transactions with reactive auto-calculation and live WAC preview. |
| **[Brokers](features/brokers/index.md)** | `BrokerCard`, `BrokerForm`, `BrokerModal`, `CashBalanceCard`, and Broker Sharing. |
| **[Settings](features/settings.md)** | `SettingsLayout`, `PreferencesTab`, `GlobalSettingsTab`. |
| **[Authentication](features/auth.md)** | `LoginCard`, `RegisterCard`, `ForgotPasswordCard`. |
| **[Live Ticker](features/live-ticker.md)** | Real-time asset price badges with polling and dynamic colors. |

## 📏 Component Guidelines

- **ModalBase**: ALL modals extend `ModalBase.svelte` with configurable z-index
- **Svelte 5 Runes**: Use `$state`, `$derived`, `$effect`, `$props`
- **Event handling**: Use `onclick` instead of `on:click` (Svelte 5 syntax)
- **Styling**: Tailwind CSS utilities + dark mode with `dark:` prefix
- **Accessibility**: Keyboard navigation, ARIA labels, focus management
- **i18n**: All user-facing text via `$t('key')` translation function
