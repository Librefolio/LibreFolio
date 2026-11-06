/**
 * storageLimit.ts — a refusal of the space limit, as a screen says it (release 1.3, lot C8).
 *
 * The backend answers 507 with `detail: {code: 'storage_limit_exceeded', required_mb, disk_missing_bytes, limit_locked, …}`.
 * Here: the numbers are read from a `detail` (and from an axios-like error) only when the code is that one and the numbers
 * are usable; the message is built from them in the translator's language, with the limit to raise (or whom to ask, when the
 * hosting provider fixes it) and, only when the disk lacks room, how much more it needs free.
 *
 * `translate` is a stub that echoes the key it is asked for with its values, so the sentence asserted is the key and the
 * numbers the function passed, never a phrase from a catalogue.
 */
import {describe, expect, it} from 'vitest';
import {STORAGE_LIMIT_CODE, storageLimitMessage, storageLimitMessageOfError, storageLimitNumbersOf, storageLimitNumbersOfError} from './storageLimit';

const translate = (key: string, options?: {values?: Record<string, string | number>}): string =>
    options?.values
        ? `${key}(${Object.entries(options.values)
              .map(([name, value]) => `${name}=${value}`)
              .join(',')})`
        : `[[${key}]]`;

const detail = (extra: Record<string, unknown> = {}) => ({code: STORAGE_LIMIT_CODE, message: 'The space limit would be passed', limit_mb: 100, used_bytes: 1, required_bytes: 1, required_mb: 120, disk_missing_bytes: 0, limit_locked: false, ...extra});
const refused = (extra: Record<string, unknown> = {}) => ({isAxiosError: true, response: {status: 507, data: {detail: detail(extra)}}});

describe('storageLimitNumbersOf — only a refusal of the space limit with usable numbers', () => {
    it('reads the numbers of a refusal', () => {
        expect(storageLimitNumbersOf(detail({required_mb: 120, disk_missing_bytes: 5, limit_locked: true}))).toEqual({requiredMb: 120, diskMissingBytes: 5, limitLocked: true});
    });

    it.each([
        ['another code', {...detail(), code: 'backup_no_space'}],
        ['no required_mb', {...detail(), required_mb: undefined}],
        ['a required_mb that is not a number', {...detail(), required_mb: '120'}],
        ['a negative required_mb', {...detail(), required_mb: -1}],
        ['a string', 'The space limit would be passed'],
        ['null', null],
        ['an array', [detail()]],
    ])('is no refusal: %s', (_case, value) => {
        expect(storageLimitNumbersOf(value)).toBeNull();
    });

    it('a missing disk_missing_bytes is 0, a missing limit_locked is false', () => {
        expect(storageLimitNumbersOf({code: STORAGE_LIMIT_CODE, required_mb: 7})).toEqual({requiredMb: 7, diskMissingBytes: 0, limitLocked: false});
    });

    it('reads an error the way axios carries it, and nothing else', () => {
        expect(storageLimitNumbersOfError(refused({required_mb: 9}))?.requiredMb).toBe(9);
        expect(storageLimitNumbersOfError(new Error('boom'))).toBeNull();
        expect(storageLimitNumbersOfError(null)).toBeNull();
        expect(storageLimitNumbersOfError({response: {status: 500, data: {detail: {code: 'backup_failed'}}}})).toBeNull();
    });
});

describe('storageLimitMessage — what to raise, whom to ask, how much room to free', () => {
    it('an administrator who can raise the limit: the sentence of the raise, the limit written as a size', () => {
        expect(storageLimitMessage({requiredMb: 120, diskMissingBytes: 0, limitLocked: false}, translate)).toBe('storage.limit.exceeded.raise(required=120.0 [[common.megabytes]],missing=0 [[common.bytes]])');
    });

    it('a limit fixed by the hosting provider: the sentence that asks whoever hosts it, never «raise it here»', () => {
        const message = storageLimitMessage({requiredMb: 120, diskMissingBytes: 0, limitLocked: true}, translate);
        expect(message.startsWith('storage.limit.exceeded.locked(')).toBe(true);
        expect(message).not.toContain('exceeded.raise');
    });

    it('the room the disk lacks is added only when it lacks some', () => {
        const without = storageLimitMessage({requiredMb: 120, diskMissingBytes: 0, limitLocked: false}, translate);
        const withDisk = storageLimitMessage({requiredMb: 120, diskMissingBytes: 5 * 1024 * 1024, limitLocked: false}, translate);
        expect(without).not.toContain('exceeded.disk');
        expect(withDisk.startsWith(without.replace('missing=0 [[common.bytes]]', 'missing=5.0 [[common.megabytes]]'))).toBe(true);
        expect(withDisk).toContain('storage.limit.exceeded.disk(required=120.0 [[common.megabytes]],missing=5.0 [[common.megabytes]])');
    });

    it('of an error: the message of a refusal, null for any other failure', () => {
        expect(storageLimitMessageOfError(refused(), translate)).toContain('storage.limit.exceeded.raise');
        expect(storageLimitMessageOfError(new Error('boom'), translate)).toBeNull();
    });
});
