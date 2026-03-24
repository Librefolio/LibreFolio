<!--
  FilesTable - Wrapper component using the generic DataTable for files
  
  This component wraps DataTable with file-specific column definitions
  and actions. It supports both static uploads and BRIM reports.

  URL Filter Support:
  - Pass initialFilters to set filters from URL params
  - Use onFiltersChange to sync filter changes back to URL
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import {type BulkAction, type ColumnDef, DataTable, type FilterValue, type RowAction} from '$lib/components/table';
    import {Download, File as FileIcon, FileArchive, FileAudio, FileCode, FileJson, FileSpreadsheet, FileText, FileType, FileVideo, Image as ImageIcon, Link, Trash2} from 'lucide-svelte';
    import type {BrimFile, BrokerInfo, FileData, UploadedFile} from '$lib/types';
    import {safeNumber} from '$lib/types';

    interface Props {
        files: FileData[];
        type: 'static' | 'brim';
        onDelete: (id: string) => void;
        onDeleteMultiple?: (ids: string[]) => void;
        /** Broker map for BRIM files - key: broker_id, value: broker info */
        brokers?: Map<number, BrokerInfo>;
        /** Whether to show broker column (default: true for brim) */
        showBrokerColumn?: boolean;
        /** Initial filters from URL params */
        initialFilters?: Record<string, FilterValue>;
        /** Called when filters change (for URL sync) */
        onFiltersChange?: (filters: Record<string, FilterValue>) => void;
        /** Called when row selection changes (exposes selected IDs to parent) */
        onSelectionChange?: (selectedIds: string[]) => void;
    }

    let {files, type, onDelete, onDeleteMultiple, brokers, showBrokerColumn = true, initialFilters, onFiltersChange, onSelectionChange}: Props = $props();

    // Internal DataTable reference (for external column visibility control)
    let dataTableRef: DataTable<FileData> | undefined = $state(undefined);

    /** Expose the internal DataTable ref for ColumnVisibilityToggle */
    export function getTableRef() { return dataTableRef; }

    /** Clear all selected rows */
    export function clearSelection() { dataTableRef?.clearSelection(); }

    // Helper functions
    function getFileName(file: FileData): string {
        return type === 'static' ? (file as UploadedFile).original_name : (file as BrimFile).filename;
    }

    function getFileId(file: FileData): string {
        return type === 'static' ? (file as UploadedFile).id : (file as BrimFile).file_id;
    }

    function getDownloadUrl(file: FileData): string {
        if (type === 'static') {
            return `${(file as UploadedFile).url}?download=true`;
        }
        return `/api/v1/brokers/import/files/${(file as BrimFile).file_id}/download`;
    }

    function getFileSize(file: FileData): number {
        return type === 'static' ? (file as UploadedFile).size_bytes : ((file as BrimFile).size_bytes || 0);
    }

    function isImageFile(file: FileData): boolean {
        if (type !== 'static') return false;
        const f = file as UploadedFile;
        return f.mime_type?.startsWith('image/') ?? false;
    }

    function getPreviewUrl(file: FileData): string {
        const f = file as UploadedFile;
        return `${f.url}?img_preview=48x48`;
    }

    function getFileIcon(file: FileData) {
        const filename = getFileName(file).toLowerCase();
        const ext = filename.split('.').pop() || '';

        if (type === 'static') {
            const f = file as UploadedFile;
            const mimeType = f.mime_type || '';

            // Images (png, jpg, jpeg, gif, webp, svg, bmp, ico)
            if (mimeType.startsWith('image/') ||
                ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico', 'tiff'].includes(ext)) {
                return Image;
            }

            // Videos
            if (mimeType.startsWith('video/') ||
                ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'].includes(ext)) {
                return FileVideo;
            }

            // Audio
            if (mimeType.startsWith('audio/') ||
                ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma'].includes(ext)) {
                return FileAudio;
            }

            // Spreadsheets (csv, xlsx, xls, ods)
            if (mimeType.includes('spreadsheet') || mimeType.includes('csv') ||
                ['csv', 'xlsx', 'xls', 'ods', 'numbers'].includes(ext)) {
                return FileSpreadsheet;
            }

            // JSON
            if (mimeType.includes('json') || ext === 'json') {
                return FileJson;
            }

            // Code files
            if (['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'c', 'cpp', 'h', 'cs', 'go', 'rs',
                'rb', 'php', 'swift', 'kt', 'scala', 'html', 'css', 'scss', 'less', 'vue', 'svelte'].includes(ext)) {
                return FileCode;
            }

            // Archives
            if (mimeType.includes('zip') || mimeType.includes('tar') || mimeType.includes('archive') ||
                ['zip', 'tar', 'gz', 'rar', '7z', 'bz2', 'xz', 'tgz'].includes(ext)) {
                return FileArchive;
            }

            // PDF
            if (mimeType.includes('pdf') || ext === 'pdf') {
                return FileType;  // FileType looks like a document with lines
            }

            // Text/Documents
            if (mimeType.includes('text') ||
                ['txt', 'md', 'rtf', 'doc', 'docx', 'odt', 'pages'].includes(ext)) {
                return FileText;
            }
        } else {
            // BRIM files - mainly spreadsheets
            if (['csv', 'xlsx', 'xls', 'ods'].includes(ext)) return FileSpreadsheet;
            if (ext === 'json') return FileJson;
            if (ext === 'txt') return FileText;
        }

        return FileIcon;
    }

    function translateStatus(status: string): string {
        // 'error' is a common concept, use common.error
        if (status === 'error') return $t('common.error');
        const key = `fileStatus.${status}`;
        const translated = $t(key);
        return translated !== key ? translated : status.charAt(0).toUpperCase() + status.slice(1);
    }

    function getBadgeVariant(status: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
        switch (status) {
            case 'parsed':
                return 'success';
            case 'uploaded':
                return 'info';
            case 'failed':
                return 'error';
            default:
                return 'default';
        }
    }

    function getBrokerName(file: FileData): string {
        if (type !== 'brim') return '';
        const brimFile = file as BrimFile;
        const brokerId = safeNumber(brimFile.target_broker_id);
        if (!brokerId || !brokers) return '-';
        const broker = brokers.get(brokerId);
        // If broker not in map, it belongs to another user (shown to superuser)
        return broker?.name || `#${brokerId} (${$t('uploads.otherUser') || 'other user'})`;
    }

    // Generate a consistent color based on broker id for visual distinction
    // Uses shared golden-ratio color utility
    import {getIndexColor} from '$lib/utils/colors';

    function getBrokerColor(brokerId: number): { bg: string; text: string; darkBg: string; darkText: string } {
        return getIndexColor(brokerId, 120);
    }

    function getBrokerBadgeStyle(file: FileData): string | undefined {
        if (type !== 'brim') return undefined;
        const brimFile = file as BrimFile;
        const brokerId = safeNumber(brimFile.target_broker_id);
        if (!brokerId) return undefined;
        const colors = getBrokerColor(brokerId);
        return `--broker-bg: ${colors.bg}; --broker-text: ${colors.text}; --broker-dark-bg: ${colors.darkBg}; --broker-dark-text: ${colors.darkText};`;
    }

    // Column definitions
    function getColumns(): ColumnDef<FileData>[] {
        const cols: ColumnDef<FileData>[] = [
            {
                id: 'filename',
                urlKey: 'filename',
                header: () => $t('uploads.fileName'),
                cell: (row) => {
                    if (isImageFile(row)) {
                        return {
                            type: 'image',
                            src: getPreviewUrl(row),
                            alt: getFileName(row),
                            text: getFileName(row),
                            fallbackIcon: ImageIcon,
                            size: 32,
                        };
                    }
                    return {
                        type: 'icon-text',
                        icon: getFileIcon(row),
                        text: getFileName(row),
                    };
                },
                type: 'text',
                width: 250,
                getValue: (row) => getFileName(row),
            },
        ];

        if (type === 'brim') {
            // Add broker column for BRIM files when user has multiple brokers
            // Bug 4 fix: Show column based on broker count, not just existence
            if (showBrokerColumn && brokers && brokers.size > 1) {
                cols.push({
                    id: 'broker',
                    urlKey: 'broker',
                    header: () => $t('uploads.broker') || 'Broker',
                    cell: (row) => {
                        const name = getBrokerName(row);
                        if (name === '-') return '-';
                        // Return styled badge for broker
                        return {
                            type: 'badge' as const,
                            text: name,
                            variant: 'default' as const,
                            customStyle: getBrokerBadgeStyle(row),
                        };
                    },
                    type: 'enum',
                    enumOptions: Array.from(brokers.values()).map(b => ({
                        value: String(b.id),
                        label: b.name,
                    })),
                    width: 140,
                    getValue: (row) => String((row as BrimFile).target_broker_id || ''),
                });
            }

            cols.push({
                id: 'status',
                urlKey: 'status',
                header: () => $t('uploads.status'),
                cell: (row) => ({
                    type: 'badge',
                    text: translateStatus((row as BrimFile).status),
                    variant: getBadgeVariant((row as BrimFile).status),
                }),
                type: 'enum',
                enumOptions: [
                    {value: 'uploaded', label: translateStatus('uploaded')},
                    {value: 'parsed', label: translateStatus('parsed')},
                    {value: 'failed', label: translateStatus('failed')},
                ],
                width: 100,
                getValue: (row) => (row as BrimFile).status,
            });
        }

        cols.push(
            {
                id: 'size',
                urlKey: 'size',
                header: () => $t('uploads.fileSize'),
                cell: (row) => ({
                    type: 'size',
                    bytes: getFileSize(row),
                }),
                type: 'size',
                width: 100,
                getValue: (row) => getFileSize(row),
            },
            {
                id: 'date',
                urlKey: 'date',
                header: () => $t('uploads.uploadDate'),
                cell: (row) => ({
                    type: 'date',
                    value: row.uploaded_at,
                    format: 'datetime',
                }),
                type: 'date',
                width: 160,
                getValue: (row) => row.uploaded_at,
            }
        );

        return cols;
    }


    // Helper to copy to clipboard with fallback
    async function copyToClipboard(text: string): Promise<boolean> {
        // Try modern clipboard API first
        if (navigator.clipboard && window.isSecureContext) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (err) {
                console.warn('Clipboard API failed:', err);
            }
        }

        // Fallback for HTTP or older browsers
        try {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            textArea.style.top = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            const success = document.execCommand('copy');
            document.body.removeChild(textArea);
            return success;
        } catch (err) {
            console.error('Fallback copy failed:', err);
            return false;
        }
    }

    // Row actions
    function getRowActions(): RowAction<FileData>[] {
        const actions: RowAction<FileData>[] = [];

        // Copy Link action (only for static files)
        if (type === 'static') {
            actions.push({
                id: 'copyLink',
                icon: Link,
                label: () => $t('uploads.copyLink') || 'Copy Link',
                onClick: async (file) => {
                    const staticFile = file as UploadedFile;
                    const url = staticFile.url;
                    const success = await copyToClipboard(url);
                    if (success) {
                        toasts.success($t('common.copied') || 'Copied!');
                    } else {
                        toasts.error('Copy failed');
                    }
                },
            });
        }

        // Download action
        actions.push({
            id: 'download',
            icon: Download,
            label: () => $t('uploads.download'),
            onClick: (file) => {
                const link = document.createElement('a');
                link.href = getDownloadUrl(file);
                link.download = getFileName(file);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            },
        });

        // Delete action
        actions.push({
            id: 'delete',
            icon: Trash2,
            label: () => $t('common.delete'),
            onClick: (file) => onDelete(getFileId(file)),
            variant: 'danger',
            requireConfirm: true,
            confirmMessage: () => $t('uploads.deleteConfirm'),
        });

        return actions;
    }

    // Bulk actions
    function getBulkActions(): BulkAction<FileData>[] {
        return [
            {
                id: 'download',
                icon: Download,
                label: () => $t('uploads.download'),
                onClick: (selectedFiles) => {
                    selectedFiles.forEach((file, index) => {
                        setTimeout(() => {
                            const link = document.createElement('a');
                            link.href = getDownloadUrl(file);
                            link.download = getFileName(file);
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                        }, index * 200);
                    });
                },
            },
            {
                id: 'delete',
                icon: Trash2,
                label: () => $t('common.delete'),
                onClick: (selectedFiles) => {
                    if (onDeleteMultiple) {
                        onDeleteMultiple(selectedFiles.map(f => getFileId(f)));
                    } else {
                        selectedFiles.forEach(file => onDelete(getFileId(file)));
                    }
                },
                variant: 'danger',
                requireConfirm: true,
                confirmMessage: (count) => `${$t('uploads.deleteConfirmMultiple')} (${count})`,
            },
        ];
    }

    // Reactive columns (to get translations updated)
    let columns = $derived(getColumns());
    let rowActions = $derived(getRowActions());
    let bulkActions = $derived(getBulkActions());
</script>

<div data-testid="files-table-{type}">
    <DataTable
            bind:this={dataTableRef}
            {bulkActions}
            {columns}
            data={files}
            emptyMessage={$t('uploads.noFiles')}
            getRowDisplayName={getFileName}
            getRowId={getFileId}
            {initialFilters}
            {onFiltersChange}
            onSelectionChange={onSelectionChange}
            {rowActions}
            storageKey="filesTable_{type}"
            tableLayout="auto"
    />
</div>

