# DataTable Component

*Status: Draft - Component implemented, documentation in progress*

## Overview

`DataTable` is a powerful, generic table component with Excel-like features:

- **Sorting** - Click column headers to sort ASC/DESC
- **Filtering** - Per-column filters (text, enum, number, size, date)
- **Pagination** - Sticky bottom balloon with page size selection
- **Selection** - Row selection with bulk actions
- **Column Management** - Show/hide and reorder columns
- **Column Resize** - Drag to resize columns
- **Persistence** - Settings saved to localStorage

## Files

```
frontend/src/lib/components/table/
├── index.ts              # Exports
├── types.ts              # TypeScript interfaces
├── DataTable.svelte      # Main component (~940 lines)
├── DataTablePagination.svelte
├── DataTableToolbar.svelte
├── DataTableColumnFilter.svelte
└── ConfirmModal.svelte
```

## Basic Usage

```svelte
<script lang="ts">
  import { DataTable, type ColumnDef } from '$lib/components/table';
  
  const columns: ColumnDef<MyData>[] = [
    {
      id: 'name',
      header: () => 'Name',
      cell: (row) => ({ type: 'text', text: row.name }),
      type: 'text',
    },
    // ...more columns
  ];
  
  const rowActions = [
    { id: 'edit', icon: Pencil, label: 'Edit', onClick: (row) => editRow(row) },
    { id: 'delete', icon: Trash2, label: 'Delete', onClick: (row) => deleteRow(row), danger: true },
  ];
</script>

<DataTable
  data={myData}
  columns={columns}
  rowActions={rowActions}
  getRowId={(row) => row.id}
/>
```

## Column Types

| Type | Filter UI | Description |
|------|-----------|-------------|
| `text` | Text input with match mode | For strings |
| `enum` | Checkbox list | For status/category fields |
| `number` | Min/Max inputs | For numeric values |
| `size` | Logarithmic slider | For file sizes (bytes) |
| `date` | Date range picker | For timestamps |

## Cell Renderers

*(To be documented)*

- `text` - Plain text
- `icon-text` - Icon + text
- `badge` - Status badge with color variants
- `size` - Formatted file size
- `date` - Formatted date/datetime
- `custom` - Custom Svelte component

## Props Reference

*(To be documented)*

## Events

*(To be documented)*

## Styling

*(To be documented)*
