/**
 * The space bar of the Files page (lot FB-29): the bytes the backend measured, turned into the widths of a bar.
 *
 * The backend measures and sums (`GET /backup/instance/storage`); this only divides a part by the whole, which is all a
 * bar needs. Three modes:
 *   - `limit`: the administrator (or the hosting provider) set a limit; the bar is that limit and LibreFolio's parts fill it;
 *   - `volume`: no limit and the disk is known; the bar is the disk — LibreFolio's parts, then the other files of the
 *     disk, then the free space;
 *   - `data`: no limit and no disk; the bar is LibreFolio's own folder, split in its parts.
 */
import type {InstanceStorage} from '$lib/features/backup/backupApi';

export type StorageMode = 'limit' | 'volume' | 'data';
export type StorageSegmentId = 'database' | 'uploads' | 'brokerReports' | 'backups' | 'dataOther' | 'disk';

export interface StorageSegment {
    id: StorageSegmentId;
    bytes: number;
    /** Share of the bar, 0–100, rounded to two decimals. */
    percent: number;
}

export interface StorageBarModel {
    mode: StorageMode;
    /** What the whole bar stands for, in bytes. */
    totalBytes: number;
    segments: StorageSegment[];
    usedBytes: number;
    freeBytes: number;
    freePercent: number;
    /** The limit is set and the data folder is larger than it. */
    overLimit: boolean;
}

const BYTES_PER_MB = 1024 * 1024;

function share(bytes: number, total: number): number {
    return total > 0 ? Math.round((bytes / total) * 10000) / 100 : 0;
}

export function storageBarModel(usage: InstanceStorage): StorageBarModel {
    const limitMb = usage.limit_mb ?? 0;
    const volumeTotal = usage.volume_total_bytes ?? 0;
    const mode: StorageMode = limitMb > 0 ? 'limit' : volumeTotal > 0 ? 'volume' : 'data';
    const totalBytes = mode === 'limit' ? limitMb * BYTES_PER_MB : mode === 'volume' ? volumeTotal : usage.data_bytes;

    const parts: Array<{id: StorageSegmentId; bytes: number}> = [
        {id: 'database', bytes: usage.database_bytes},
        {id: 'uploads', bytes: usage.uploads_bytes},
        {id: 'brokerReports', bytes: usage.broker_reports_bytes},
        {id: 'backups', bytes: usage.backups_bytes},
        {id: 'dataOther', bytes: usage.other_bytes},
    ];
    if (mode === 'volume') parts.push({id: 'disk', bytes: Math.max(0, (usage.volume_used_bytes ?? 0) - usage.data_bytes)});

    // The percentages never add up to more than the bar: when they would, the last segment gives way.
    const segments: StorageSegment[] = [];
    let taken = 0;
    for (const part of parts) {
        if (part.bytes <= 0) continue;
        const percent = Math.max(0, Math.min(share(part.bytes, totalBytes), Math.round((100 - taken) * 100) / 100));
        taken = Math.round((taken + percent) * 100) / 100;
        if (percent > 0) segments.push({id: part.id, bytes: part.bytes, percent});
    }

    const usedBytes = segments.reduce((sum, segment) => sum + segment.bytes, 0);
    const freeBytes = mode === 'volume' ? (usage.volume_free_bytes ?? 0) : mode === 'limit' ? Math.max(0, totalBytes - usedBytes) : 0;
    return {mode, totalBytes, segments, usedBytes, freeBytes, freePercent: share(freeBytes, totalBytes), overLimit: mode === 'limit' && usage.data_bytes > totalBytes};
}
