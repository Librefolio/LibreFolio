<!--
  FilesTable - Wrapper component using the generic DataTable for files
  
  This component wraps DataTable with file-specific column definitions
  and actions. It supports both static uploads and BRIM reports.
-->
<script lang="ts">
	import { t } from '$lib/i18n';
	import { DataTable, type ColumnDef, type RowAction, type BulkAction } from '$lib/components/table';
	import {
		Download,
		Trash2,
		FileText,
		Image,
		File as FileIcon,
		FileSpreadsheet,
		FileJson,
		FileCode,
		FileArchive,
		FileVideo,
		FileAudio,
		FileType
	} from 'lucide-svelte';

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
		// Multi-user fields
		uploaded_by_user_id?: number;
		target_broker_id?: number;
	}

	interface BrokerInfo {
		id: number;
		name: string;
	}

	type FileData = UploadedFile | BrimFile;

	interface Props {
		files: FileData[];
		type: 'static' | 'brim';
		onDelete: (id: string) => void;
		onDeleteMultiple?: (ids: string[]) => void;
		/** Broker map for BRIM files - key: broker_id, value: broker info */
		brokers?: Map<number, BrokerInfo>;
		/** Whether to show broker column (default: true for brim) */
		showBrokerColumn?: boolean;
	}

	let { files, type, onDelete, onDeleteMultiple, brokers, showBrokerColumn = true }: Props = $props();

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
		const filename = getFileName(file).toLowerCase();
		const ext = filename.split('.').pop() || '';

		if (type === 'static') {
			const f = file as UploadedFile;
			const contentType = f.content_type || '';

			// Images (png, jpg, jpeg, gif, webp, svg, bmp, ico)
			if (contentType.startsWith('image/') ||
				['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico', 'tiff'].includes(ext)) {
				return Image;
			}

			// Videos
			if (contentType.startsWith('video/') ||
				['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'].includes(ext)) {
				return FileVideo;
			}

			// Audio
			if (contentType.startsWith('audio/') ||
				['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma'].includes(ext)) {
				return FileAudio;
			}

			// Spreadsheets (csv, xlsx, xls, ods)
			if (contentType.includes('spreadsheet') || contentType.includes('csv') ||
				['csv', 'xlsx', 'xls', 'ods', 'numbers'].includes(ext)) {
				return FileSpreadsheet;
			}

			// JSON
			if (contentType.includes('json') || ext === 'json') {
				return FileJson;
			}

			// Code files
			if (['js', 'ts', 'jsx', 'tsx', 'py', 'java', 'c', 'cpp', 'h', 'cs', 'go', 'rs',
				 'rb', 'php', 'swift', 'kt', 'scala', 'html', 'css', 'scss', 'less', 'vue', 'svelte'].includes(ext)) {
				return FileCode;
			}

			// Archives
			if (contentType.includes('zip') || contentType.includes('tar') || contentType.includes('archive') ||
				['zip', 'tar', 'gz', 'rar', '7z', 'bz2', 'xz', 'tgz'].includes(ext)) {
				return FileArchive;
			}

			// PDF
			if (contentType.includes('pdf') || ext === 'pdf') {
				return FileType;  // FileType looks like a document with lines
			}

			// Text/Documents
			if (contentType.includes('text') ||
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

	function getBrokerName(file: FileData): string {
		if (type !== 'brim') return '';
		const brimFile = file as BrimFile;
		if (!brimFile.target_broker_id || !brokers) return '-';
		const broker = brokers.get(brimFile.target_broker_id);
		return broker?.name || `Broker #${brimFile.target_broker_id}`;
	}

	// Generate a consistent color based on broker id for visual distinction
	// Uses HSL color space starting from green (120°) and rotating through hues
	function getBrokerColor(brokerId: number): { bg: string; text: string; darkBg: string; darkText: string } {
		// Golden ratio for better distribution
		const goldenRatio = 0.618033988749895;
		// Start at green hue (120°), rotate through spectrum
		const hue = ((brokerId * goldenRatio) % 1) * 360;
		// Keep saturation and lightness in pleasant ranges
		const saturation = 35 + (brokerId % 5) * 5; // 35-55%
		const lightness = 92; // Light background
		const textLightness = 30; // Dark text

		return {
			bg: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
			text: `hsl(${hue}, ${saturation + 10}%, ${textLightness}%)`,
			darkBg: `hsl(${hue}, ${saturation - 10}%, 20%)`,
			darkText: `hsl(${hue}, ${saturation}%, 75%)`,
		};
	}

	function getBrokerBadgeStyle(file: FileData): string | undefined {
		if (type !== 'brim') return undefined;
		const brimFile = file as BrimFile;
		if (!brimFile.target_broker_id) return undefined;
		const colors = getBrokerColor(brimFile.target_broker_id);
		return `--broker-bg: ${colors.bg}; --broker-text: ${colors.text}; --broker-dark-bg: ${colors.darkBg}; --broker-dark-text: ${colors.darkText};`;
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
			// Add broker column for BRIM files
			if (showBrokerColumn && brokers && brokers.size > 0) {
				cols.push({
					id: 'broker',
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
