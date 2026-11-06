/**
 * The space limit, as a screen says it (release 1.3, lot C8).
 *
 * The backend refuses what would take the data past the space limit (`storage_limit` of the instance) with a 507 whose
 * `detail` holds a stable code and the numbers: an uploaded file, a broker report (also a combined one) and a backup
 * started by hand. A restore that would pass it is a blocker of its check (`backup.restore.blocker.storage_limit`). The
 * words are the interface's own, in its language, from the numbers: this file turns a refusal into them, once, for every
 * screen (`extractErrorMessage` and `uploadFile` call it).
 *
 * The message says what to do: raise the total space to at least `required`, which the limit would have to hold (or, when
 * the hosting provider fixes the limit, ask whoever hosts the instance to), and free up space; when the disk itself lacks
 * room for it, how much more the disk needs free.
 */

import {get} from 'svelte/store';
import {_} from '$lib/i18n';
import {formatBytes} from './upload';

/** The code of every refusal of the space limit. */
export const STORAGE_LIMIT_CODE = 'storage_limit_exceeded';

const BYTES_PER_MB = 1024 * 1024;

/** The numbers of a refusal: what the screens word their message from. */
export interface StorageLimitNumbers {
    /** The limit that would allow the action, in whole megabytes. */
    requiredMb: number;
    /** The room the disk lacks to hold it, in bytes; 0 when it has enough. */
    diskMissingBytes: number;
    /** The limit is fixed by whoever hosts the instance: the administrator cannot raise it. */
    limitLocked: boolean;
}

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

function isRecord(value: unknown): value is Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function whole(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
}

/** The numbers of a refusal's `detail` (an axios error's `response.data.detail`); `null` when it is none. */
export function storageLimitNumbersOf(detail: unknown): StorageLimitNumbers | null {
    if (!isRecord(detail) || detail.code !== STORAGE_LIMIT_CODE) return null;
    const requiredMb = whole(detail.required_mb);
    if (requiredMb === null) return null;
    return {requiredMb, diskMissingBytes: whole(detail.disk_missing_bytes) ?? 0, limitLocked: detail.limit_locked === true};
}

/** The numbers of a failed request, when it was refused by the space limit. */
export function storageLimitNumbersOfError(error: unknown): StorageLimitNumbers | null {
    return storageLimitNumbersOf((error as {response?: {data?: {detail?: unknown}}} | null | undefined)?.response?.data?.detail);
}

/** The message of a refusal, in the interface's language: what to raise (or whom to ask) and how much room to free. */
export function storageLimitMessage(numbers: StorageLimitNumbers, translate: Translate = get(_) as Translate): string {
    const bytes = (value: number) => formatBytes(value, (key) => translate(key));
    const values = {required: bytes(numbers.requiredMb * BYTES_PER_MB), missing: bytes(numbers.diskMissingBytes)};
    const sentence = translate(numbers.limitLocked ? 'storage.limit.exceeded.locked' : 'storage.limit.exceeded.raise', {values});
    return numbers.diskMissingBytes > 0 ? `${sentence} ${translate('storage.limit.exceeded.disk', {values})}` : sentence;
}

/** The message of a failed request when the space limit refused it; `null` for any other failure. */
export function storageLimitMessageOfError(error: unknown, translate?: Translate): string | null {
    const numbers = storageLimitNumbersOfError(error);
    return numbers === null ? null : storageLimitMessage(numbers, translate);
}
