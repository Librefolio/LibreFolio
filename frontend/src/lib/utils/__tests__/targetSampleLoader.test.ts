/**
 * targetSampleLoader.ts (Z-29d reduced): the settings preview of a sampled card draws a comparison the user has just
 * picked, before saving. The page reads that target sampled like the card once, outside the render: the loader runs each
 * read once per key (card, target, range, max_points), never synchronously (the preview asks from inside a `$derived`,
 * where Svelte refuses state writes), and does not try a key again after it failed.
 *
 * Red first: the module does not exist.
 */
import {describe, expect, it, vi} from 'vitest';

import {TargetSampleLoader, targetSampleKey} from '../targetSampleLoader';

const KEY = {cardId: 7, targetId: 9, start: '2025-01-01', end: '2026-06-30', maxPoints: 377};

/** Every microtask already queued has run. */
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('targetSampleKey', () => {
    it('names a read by card, target, range and max_points', () => {
        expect(targetSampleKey(KEY)).toBe('7|9|2025-01-01|2026-06-30|377');
        expect(targetSampleKey({...KEY, maxPoints: 380})).not.toBe(targetSampleKey(KEY));
    });
});

describe('TargetSampleLoader', () => {
    it('runs a read after the call returns, never inside it', async () => {
        const read = vi.fn(async () => undefined);
        const loader = new TargetSampleLoader(read);

        loader.want(KEY);

        expect(read, 'not inside the call: the preview asks from a $derived').not.toHaveBeenCalled();
        await settle();
        expect(read).toHaveBeenCalledTimes(1);
        expect(read).toHaveBeenCalledWith(KEY);
    });

    it('runs one read per key, however often the preview asks', async () => {
        const read = vi.fn(async () => undefined);
        const loader = new TargetSampleLoader(read);

        loader.want(KEY);
        loader.want(KEY);
        await settle();
        loader.want(KEY);
        await settle();

        expect(read).toHaveBeenCalledTimes(1);
    });

    it('runs a read for another target, range or width', async () => {
        const read = vi.fn(async () => undefined);
        const loader = new TargetSampleLoader(read);

        loader.want(KEY);
        loader.want({...KEY, targetId: 10});
        loader.want({...KEY, end: '2026-07-31'});
        loader.want({...KEY, maxPoints: 200});
        await settle();

        expect(read).toHaveBeenCalledTimes(4);
    });

    it('does not try a key again after its read failed, and says the failure to the caller once', async () => {
        const failure = new Error('boom');
        const read = vi.fn(async () => {
            throw failure;
        });
        const failed = vi.fn();
        const loader = new TargetSampleLoader(read, failed);

        loader.want(KEY);
        await settle();
        loader.want(KEY);
        await settle();

        expect(read).toHaveBeenCalledTimes(1);
        expect(failed).toHaveBeenCalledTimes(1);
        expect(failed).toHaveBeenCalledWith(KEY, failure);
    });

    it('forgets every key on reset, so the next ask reads again', async () => {
        const read = vi.fn(async () => undefined);
        const loader = new TargetSampleLoader(read);

        loader.want(KEY);
        await settle();
        loader.reset();
        loader.want(KEY);
        await settle();

        expect(read).toHaveBeenCalledTimes(2);
    });
});
