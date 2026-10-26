/**
 * instanceBlockState — recognising the refusal of an interrupted restore (workstream H, lot B-33, the start's part).
 *
 * When the state of a restore (`.restore/restore.json`) cannot be read the backend serves no data: every route but a
 * few answers `423 {"detail": {"code": "instance_restore_interrupted", "message": ...}}` to anyone. The API client's
 * response interceptor recognises it with `isInstanceRestoreInterruptedError(status, data)` of this rune-free module,
 * beside `isInstanceBlockedError` and `isInstanceAwaitingRestoreError`, and forces a reload of the instance config.
 *
 * The contract under test:
 *   - `isInstanceRestoreInterruptedError(status, data)` is true only for status 423 with
 *     `data.detail.code === 'instance_restore_interrupted'`: another status, another code (the block's, the awaiting
 *     mode's), a code outside `detail`, a `detail` that is not an object, or no body at all is not that refusal;
 *   - the three recognisers do not overlap: the interrupted body is neither a block nor the awaiting mode.
 *
 * H5-3: the refusal carries no reason. `restore_interrupted_reason` (`restore_state` | `owner_assignment`) is read from
 * `GET /system/instance` only; the 423 is recognised by its code alone, the same for both reasons, so the predicate's
 * answer does not change with any reason-like field a body might carry. (Green on arrival: a pin of what stays.)
 *
 * Node environment: a pure function, nothing to render. The helper is read off the module namespace, so while it does
 * not exist each case fails on its own premise («a function») instead of the whole file failing to import.
 *
 * Red until B-33: `instanceBlockState.ts` has no `isInstanceRestoreInterruptedError`.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {describe, expect, it} from 'vitest';
import * as state from './instanceBlockState';

type Recogniser = (status: number | undefined, data: unknown) => boolean;

const INTERRUPTED_BODY = {detail: {code: 'instance_restore_interrupted', message: 'The state of the restore cannot be read'}};

/** The helper of the contract, or a failure that names it. */
function recogniser(): Recogniser {
    const candidate = (state as Record<string, unknown>).isInstanceRestoreInterruptedError;
    expect(typeof candidate, 'premise: instanceBlockState exports isInstanceRestoreInterruptedError, a function').toBe('function');
    return candidate as Recogniser;
}

describe('isInstanceRestoreInterruptedError', () => {
    it('recognises a 423 whose detail.code is instance_restore_interrupted', () => {
        expect(recogniser()(423, INTERRUPTED_BODY)).toBe(true);
    });

    it('recognises it without a message too: the code alone decides', () => {
        expect(recogniser()(423, {detail: {code: 'instance_restore_interrupted'}})).toBe(true);
    });

    it.each([
        ['a 403 with the same body', 403, INTERRUPTED_BODY],
        ['a 500 with the same body', 500, INTERRUPTED_BODY],
        ['no status', undefined, INTERRUPTED_BODY],
        ['a 423 instance_blocked', 423, {detail: {code: 'instance_blocked'}}],
        ['a 423 instance_awaiting_restore', 423, {detail: {code: 'instance_awaiting_restore'}}],
        ['a 423 with another code', 423, {detail: {code: 'locked'}}],
        ['a 423 with the code outside detail', 423, {code: 'instance_restore_interrupted'}],
        ['a 423 whose detail is a string', 423, {detail: 'instance_restore_interrupted'}],
        ['a 423 whose detail is null', 423, {detail: null}],
        ['a 423 with a null body', 423, null],
        ['a 423 without a body', 423, undefined],
        ['a 423 whose body is a string', 423, 'instance_restore_interrupted'],
    ])('is false for %s', (_case, status, data) => {
        expect(recogniser()(status, data)).toBe(false);
    });
});

describe('the three recognisers do not overlap', () => {
    it('the interrupted body is neither the block nor the awaiting mode', () => {
        expect(recogniser()(423, INTERRUPTED_BODY), 'Barrier: it is the interrupted refusal').toBe(true);

        expect(state.isInstanceBlockedError(423, INTERRUPTED_BODY), 'not a block').toBe(false);
        expect(state.isInstanceAwaitingRestoreError(423, INTERRUPTED_BODY), 'not the awaiting mode').toBe(false);
    });

    it.each([
        ['the block', {detail: {code: 'instance_blocked'}}],
        ['the awaiting mode', {detail: {code: 'instance_awaiting_restore'}}],
    ])('the body of %s is not an interrupted restore', (_case, body) => {
        expect(recogniser()(423, body)).toBe(false);
    });
});

describe('isInstanceRestoreInterruptedError — H5-3, the code decides, never the reason', () => {
    it.each([
        ['no reason', {detail: {code: 'instance_restore_interrupted'}}],
        ['restore_state beside the code (detail)', {detail: {code: 'instance_restore_interrupted', restore_interrupted_reason: 'restore_state'}}],
        ['owner_assignment beside the code (detail)', {detail: {code: 'instance_restore_interrupted', restore_interrupted_reason: 'owner_assignment'}}],
        ['owner_assignment at the body root', {restore_interrupted_reason: 'owner_assignment', detail: {code: 'instance_restore_interrupted'}}],
        ['a null reason', {detail: {code: 'instance_restore_interrupted', restore_interrupted_reason: null}}],
    ])('is true for a 423 with the code and %s: the same answer for both reasons', (_case, body) => {
        expect(recogniser()(423, body)).toBe(true);
    });

    it.each([
        ['restore_state', 'restore_state'],
        ['owner_assignment', 'owner_assignment'],
    ])('is false for a reason %s without the code: a reason is not a refusal', (_case, reason) => {
        expect(recogniser()(423, {detail: {code: 'locked', restore_interrupted_reason: reason}})).toBe(false);
        expect(recogniser()(423, {restore_interrupted_reason: reason})).toBe(false);
    });

    it('takes the status and the body only: nothing else to read a reason from', () => {
        expect(recogniser().length, 'the refusal predicate receives (status, data), no reason argument').toBe(2);
    });
});
