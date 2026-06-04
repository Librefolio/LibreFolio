import type {BrimFile, FileData, FilePreviewType, UploadedFile} from '$lib/types';

const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.tif', '.ico']);
const MARKDOWN_EXTENSIONS = new Set(['.md', '.markdown', '.mdown']);
const TABLE_EXTENSIONS = new Set(['.csv', '.xlsx', '.xls']);
const PDF_EXTENSIONS = new Set(['.pdf']);
const TEXT_EXTENSIONS = new Set(['.txt', '.log', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.html', '.htm', '.css', '.sql', '.csv']);
const TEXT_MIME_TYPES = new Set(['application/json', 'application/xml', 'application/x-yaml', 'application/yaml']);

export function getPreviewTypeForUploadedFile(file: UploadedFile): FilePreviewType | null {
    return detectPreviewType(file.original_name, file.mime_type);
}

export function getPreviewTypeForBrimFile(file: BrimFile): FilePreviewType | null {
    return detectPreviewType(file.filename);
}

export function canPreviewFileData(file: FileData, type: 'static' | 'brim'): boolean {
    return type === 'static' ? getPreviewTypeForUploadedFile(file as UploadedFile) !== null : getPreviewTypeForBrimFile(file as BrimFile) !== null;
}

export function detectPreviewType(filename: string, mimeType?: string | null): FilePreviewType | null {
    const ext = getExtension(filename);
    const normalizedMime = normalizeMimeType(mimeType);

    if (normalizedMime.startsWith('image/') || IMAGE_EXTENSIONS.has(ext)) {
        return 'image';
    }
    if (normalizedMime === 'application/pdf' || PDF_EXTENSIONS.has(ext)) {
        return 'pdf';
    }
    if (MARKDOWN_EXTENSIONS.has(ext)) {
        return 'markdown';
    }
    if (TABLE_EXTENSIONS.has(ext) || normalizedMime === 'text/csv' || normalizedMime === 'application/vnd.ms-excel') {
        return 'table';
    }
    if (normalizedMime.startsWith('text/') || TEXT_MIME_TYPES.has(normalizedMime) || TEXT_EXTENSIONS.has(ext)) {
        return 'text';
    }
    return null;
}

function getExtension(filename: string): string {
    const index = filename.lastIndexOf('.');
    return index >= 0 ? filename.slice(index).toLowerCase() : '';
}

function normalizeMimeType(mimeType?: string | null): string {
    return (mimeType ?? '').split(';')[0].trim().toLowerCase();
}
