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
import {SETTINGS_FIELD_PARAM, settingsTabHref} from '$lib/features/settings/settingsPaths';

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
    /** How far past the limit the action would take the data, in bytes: what a user who cannot raise it has to free. */
    excessBytes: number;
}

/** Who reads the message: an administrator raises the limit (Settings › Administration › Global Settings), a member frees space or asks one. */
export type StorageLimitViewer = 'admin' | 'member';

/**
 * Where an administrator raises the limit: the Global Settings tab, the row of the limit in view and highlighted (lot B10).
 * Files › Advanced keeps the same field, beside the space bar.
 */
export const STORAGE_LIMIT_SETTINGS_HREF = settingsTabHref('admin', {[SETTINGS_FIELD_PARAM]: 'storage_limit_mb'});

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
    const requiredBytes = whole(detail.required_bytes);
    const limitMb = whole(detail.limit_mb);
    const excessBytes = requiredBytes !== null && limitMb !== null ? Math.max(0, requiredBytes - limitMb * BYTES_PER_MB) : 0;
    return {requiredMb, diskMissingBytes: whole(detail.disk_missing_bytes) ?? 0, limitLocked: detail.limit_locked === true, excessBytes};
}

/**
 * The numbers of a failed request, when it was refused by the space limit: the axios error itself, or the error that wraps it
 * as its `cause` (`uploadFile` throws one, so that `message` is the sentence).
 */
export function storageLimitNumbersOfError(error: unknown): StorageLimitNumbers | null {
    const own = storageLimitNumbersOf((error as {response?: {data?: {detail?: unknown}}} | null | undefined)?.response?.data?.detail);
    if (own !== null) return own;
    const cause = (error as {cause?: unknown} | null | undefined)?.cause;
    return cause !== undefined && cause !== error ? storageLimitNumbersOf((cause as {response?: {data?: {detail?: unknown}}} | null)?.response?.data?.detail) : null;
}

/**
 * The message of a refusal, in the interface's language. An administrator: the limit to raise (or, when the hosting provider
 * fixes it, whom to ask) and how much room the disk lacks. A member, who cannot raise it: how much to free, or to ask an
 * administrator; a limit the provider fixes reads the same for everyone.
 */
export function storageLimitMessage(numbers: StorageLimitNumbers, translate: Translate = get(_) as Translate, viewer: StorageLimitViewer = 'admin'): string {
    const bytes = (value: number) => formatBytes(value, (key) => translate(key));
    const values = {required: bytes(numbers.requiredMb * BYTES_PER_MB), missing: bytes(numbers.diskMissingBytes), free: bytes(numbers.excessBytes)};
    if (viewer === 'member') return translate(numbers.limitLocked ? 'storage.limit.exceeded.locked' : 'storage.limit.exceeded.member', {values});
    const sentence = translate(numbers.limitLocked ? 'storage.limit.exceeded.locked' : 'storage.limit.exceeded.raise', {values});
    return numbers.diskMissingBytes > 0 ? `${sentence} ${translate('storage.limit.exceeded.disk', {values})}` : sentence;
}

/** The message of a failed request when the space limit refused it; `null` for any other failure. */
export function storageLimitMessageOfError(error: unknown, translate?: Translate, viewer?: StorageLimitViewer): string | null {
    const numbers = storageLimitNumbersOfError(error);
    return numbers === null ? null : storageLimitMessage(numbers, translate, viewer);
}
