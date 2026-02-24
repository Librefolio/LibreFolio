# DataTable Component

The `DataTable` is a powerful, generic table component built with Svelte 5 Runes. It provides a rich set of features similar to Excel or advanced data grids.

## Features

- **Sorting**: Click column headers to sort ASC/DESC.
- **Filtering**: Excel-style column filters (Text, Number, Date, Enum, Size).
- **Pagination**: Client-side pagination with configurable page sizes.
- **Selection**: Row selection with checkboxes and "Select All" on page.
- **Column Management**: Show/hide columns, reorder via drag-and-drop (in toolbar), and resize columns.
- **Persistence**: User preferences (column order, visibility, widths, page size) are automatically saved to `localStorage`.
- **Actions**: Support for per-row actions and bulk actions on selected rows.
- **Sticky Columns**: Selection and Action columns are sticky.

## Usage

```svelte
<script lang="ts">
  import { DataTable } from '$lib/components/table';
  import type { ColumnDef, RowAction } from '$lib/components/table/types';
  import { Pencil, Trash2 } from 'lucide-svelte';

  // Define your data type
  type User = { id: string; name: string; role: string; };

  // Define columns
  const columns: ColumnDef<User>[] = [
    {
      id: 'name',
      header: 'Name',
      // Simple text cell
      cell: (row) => row.name,
      sortable: true,
      filterable: true,
      type: 'text'
    },
    {
      id: 'role',
      header: 'Role',
      // Badge cell
      cell: (row) => ({
        type: 'badge',
        text: row.role,
        variant: row.role === 'admin' ? 'success' : 'default'
      }),
      type: 'enum',
      enumOptions: ['admin', 'user']
    }
  ];

  // Define row actions
  const rowActions: RowAction<User>[] = [
    {
      id: 'edit',
      icon: Pencil,
      label: 'Edit',
      onClick: (row) => console.log('Edit', row)
    },
    {
      id: 'delete',
      icon: Trash2,
      label: 'Delete',
      variant: 'danger',
      requireConfirm: true,
      onClick: (row) => console.log('Delete', row)
    }
  ];
</script>

<DataTable
  data={users}
  columns={columns}
  rowActions={rowActions}
  getRowId={(row) => row.id}
  storageKey="users-table"
/>
```

## Props

| Prop                  | Type                 | Default      | Description                              |
|:----------------------|:---------------------|:-------------|:-----------------------------------------|
| `data`                | `T[]`                | **Required** | Array of data objects.                   |
| `columns`             | `ColumnDef<T>[]`     | **Required** | Column definitions.                      |
| `getRowId`            | `(row: T) => string` | **Required** | Function to get unique ID for a row.     |
| `storageKey`          | `string`             | **Required** | Unique key for localStorage persistence. |
| `enableSelection`     | `boolean`            | `true`       | Enable row selection checkboxes.         |
| `selectionMode`       | `'multi' \| 'single'`| `'multi'`    | Multi-select or single-select rows.      |
| `enableActions`       | `boolean`            | `true`       | Enable row actions column.               |
| `enableSorting`       | `boolean`            | `true`       | Enable column sorting.                   |
| `enableColumnFilters` | `boolean`            | `true`       | Enable column filters.                   |
| `enablePagination`    | `boolean`            | `true`       | Enable pagination.                       |
| `defaultPageSize`     | `number`             | `10`         | Initial page size.                       |
| `rowActions`          | `RowAction<T>[]`     | `[]`         | Actions available for each row.          |
| `bulkActions`         | `BulkAction<T>[]`    | `[]`         | Actions available for selected rows.     |
| `onRowClick`          | `(row: T) => void`   | `undefined`  | Callback when a row is clicked.          |
| `onRowDoubleClick`    | `(row: T) => void`   | `undefined`  | Callback when a row is double-clicked.   |

## Column Definition (`ColumnDef<T>`)

| Field         | Type                                               | Description                                       |
|:--------------|:---------------------------------------------------|:--------------------------------------------------|
| `id`          | `string`                                           | Unique identifier for the column.                 |
| `header`      | `string \| () => string`                           | Column header text.                               |
| `cell`        | `(row: T) => CellContent`                          | Function returning cell content.                  |
| `type`        | `'text' \| 'number' \| 'date' \| 'enum' \| 'size'` | Data type for filtering.                          |
| `sortable`    | `boolean`                                          | Enable sorting for this column (default: true).   |
| `filterable`  | `boolean`                                          | Enable filtering for this column (default: true). |
| `width`       | `number`                                           | Initial width in pixels.                          |
| `enumOptions` | `string[]`                                         | Options for 'enum' filter type.                   |

## Cell Content Types

The `cell` function can return a simple string/number or a structured object:

- **Text**: `string` or `number`
- **Icon + Text**: `{ type: 'icon-text', icon: Component, text: string }`
- **Image + Text**: `{ type: 'image-text', src: string, text: string, fallbackIcon?: Component, size?: number }` (thumbnail with fallback, centered in 32×32 box)
- **Badge**: `{ type: 'badge', text: string, variant: 'success'|'warning'|'error'|'info'|'default' }`
- **Date**: `{ type: 'date', value: Date, format: 'date'|'datetime'|'relative' }`
- **Size**: `{ type: 'size', bytes: number }` (Auto-formats to KB/MB/GB, i18n-aware)
- **Link**: `{ type: 'link', text: string, href: string, external: boolean }`
- **Custom**: `{ type: 'custom', component: Component, props: object }`

## State Management (Internal)

The component uses Svelte 5 Runes for internal state:

- `$state` for sorting, pagination, filters, and selection.
- `$derived` for calculating filtered/sorted/paginated data efficiently.
- `$effect` for syncing state with `localStorage`.
