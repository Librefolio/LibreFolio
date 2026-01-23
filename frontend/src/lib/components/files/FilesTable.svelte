<!--
  FilesTable - Wrapper component using the generic DataTable for files
  
  This component wraps DataTable with file-specific column definitions
  and actions. It supports both static uploads and BRIM reports.
-->
<script lang="ts">
	import { t } from '$lib/i18n';
	import { DataTable, type ColumnDef, type RowAction, type BulkAction } from '$lib/components/table';
	import { Download, Trash2, FileText, Image, File as FileIcon, FileSpreadsheet } from 'lucide-svelte';

	// Types
	interface UploadedFile {
		id: string;
		original_name: string;
		stored_name: string;
		content_type: string;
		size_bytes: number;
		uploaded_at: string;
		url: string;
	}

	interface BrimFile {
		file_id: string;
		filename: string;
		status: string;
		uploaded_at: string;
		size_bytes?: number;
	}

	type FileData = UploadedFile | BrimFile;

	interface Props {
		files: FileData[];
		type: 'static' | 'brim';
		onDelete: (id: string) => void;
		onDeleteMultiple?: (ids: string[]) => void;
	}

	let { files, type, onDelete, onDeleteMultiple }: Props = $props();

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

	function getFileIcon(file: FileData) {
		if (type === 'static') {
			const f = file as UploadedFile;
			if (f.content_type?.startsWith('image/')) return Image;
			if (f.content_type?.includes('csv') || f.original_name?.endsWith('.csv')) return FileSpreadsheet;
			if (f.content_type?.includes('text') || f.content_type?.includes('json')) return FileText;
		} else {
			const f = file as BrimFile;
			const ext = f.filename.split('.').pop()?.toLowerCase();
			if (ext === 'csv') return FileSpreadsheet;
			if (ext === 'json' || ext === 'txt') return FileText;
		}
		return FileIcon;
	}

	function translateStatus(status: string): string {
		const key = `fileStatus.${status}`;
		const translated = $t(key);
		return translated !== key ? translated : status.charAt(0).toUpperCase() + status.slice(1);
	}

	function getBadgeVariant(status: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
		switch (status) {
			case 'parsed': return 'success';
			case 'uploaded': return 'info';
			case 'processing': return 'warning';
			case 'failed': return 'error';
			default: return 'default';
		}
	}

	// Column definitions
	function getColumns(): ColumnDef<FileData>[] {
		const cols: ColumnDef<FileData>[] = [
			{
				id: 'filename',
				header: () => $t('uploads.fileName'),
				cell: (row) => ({
					type: 'icon-text',
					icon: getFileIcon(row),
					text: getFileName(row),
				}),
				type: 'text',
				width: 250,
				getValue: (row) => getFileName(row),
			},
		];

		if (type === 'brim') {
			cols.push({
				id: 'status',
				header: () => $t('uploads.status'),
				cell: (row) => ({
					type: 'badge',
					text: translateStatus((row as BrimFile).status),
					variant: getBadgeVariant((row as BrimFile).status),
				}),
				type: 'enum',
				enumOptions: [
					{ value: 'uploaded', label: translateStatus('uploaded') },
					{ value: 'processing', label: translateStatus('processing') },
					{ value: 'parsed', label: translateStatus('parsed') },
					{ value: 'failed', label: translateStatus('failed') },
				],
				width: 100,
				getValue: (row) => (row as BrimFile).status,
			});
		}

		cols.push(
			{
				id: 'size',
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

	// Row actions
	function getRowActions(): RowAction<FileData>[] {
		return [
			{
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
			},
			{
				id: 'delete',
				icon: Trash2,
				label: () => $t('common.delete'),
				onClick: (file) => onDelete(getFileId(file)),
				variant: 'danger',
				requireConfirm: true,
				confirmMessage: () => $t('uploads.deleteConfirmSingle'),
			},
		];
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

<DataTable
	data={files}
	{columns}
	getRowId={getFileId}
	getRowDisplayName={getFileName}
	storageKey="filesTable_{type}"
	{rowActions}
	{bulkActions}
	emptyMessage={$t('uploads.noFiles')}
/>
