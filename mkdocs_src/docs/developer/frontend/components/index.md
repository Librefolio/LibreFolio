# Frontend Components

This section documents the reusable UI components in LibreFolio.

## Component Categories

### Table Components (`lib/components/table/`)

- [DataTable](data-table.md) - Generic data table with advanced features
- DataTablePagination - Sticky pagination balloon
- DataTableToolbar - Bulk actions, column visibility, reorder
- DataTableColumnFilter - Excel-style column filters
- ConfirmModal - Confirmation dialog for destructive actions

### Authentication (`lib/components/auth/`)

- [Auth Components](auth.md) - Login, Register, Forgot Password modals
- PasswordStrengthMeter - zxcvbn-based password strength indicator
- AnimatedBackground - Animated waves background for login page

### Settings (`lib/components/settings/`)

- [Settings Components](settings.md) - User preferences and global settings
- SettingsLayout - Two-column layout with sidebar categories
- PreferencesTab - User preference fields
- GlobalSettingsTab - Admin-only global settings
- ProfileTab - User profile management

### UI Components (`lib/components/ui/`)

- [File Upload](file-upload.md) - Multi-file uploader with validation
- LazyImage - Image with lazy loading and fallback
- FuzzySelect - Searchable dropdown with fuzzy matching
- Toggle - On/off toggle switch

### Broker Components (`lib/components/brokers/`)

- BrokerCard - Broker display card with icon
- BrokerForm - Create/edit broker form
- BrokerIcon - Smart icon with fallback chain

## Component Guidelines

*(To be documented)*

- Props patterns with Svelte 5 runes
- Event handling with `onclick` instead of `on:click`
- Styling with Tailwind CSS
- Dark mode support
- Accessibility considerations
