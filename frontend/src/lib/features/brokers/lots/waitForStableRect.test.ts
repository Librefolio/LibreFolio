// @vitest-environment jsdom
/**
 * waitForStableRect — a rectangle with no height is not a settled one (the scroll to the lots panel).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {waitForStableRect} from './waitForStableRect';

let frames: FrameRequestCallback[] = [];
beforeEach(() => {
    frames = [];
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => frames.push(cb));
});
afterEach(() => vi.unstubAllGlobals());

/** An element whose rectangle is read from `heights`, one per frame (the last one repeats). */
function elementWithHeights(heights: number[]): HTMLElement {
    let read = 0;
    const el = document.createElement('div');
    el.getBoundingClientRect = () => ({top: 10, left: 0, width: 300, height: heights[Math.min(read++, heights.length - 1)]}) as DOMRect;
    return el;
}

/** Runs frames until the promise settles or `limit` frames pass; returns how many ran. */
async function run(promise: Promise<void>, limit: number): Promise<{frames: number; settled: boolean}> {
    let settled = false;
    void promise.then(() => (settled = true));
    let n = 0;
    while (!settled && n < limit && frames.length > 0) {
        frames.shift()!(0);
        n++;
        await Promise.resolve();
    }
    return {frames: n, settled};
}

describe('waitForStableRect', () => {
    it('does not count a 0-high rectangle seen for several frames as stable', async () => {
        const result = await run(waitForStableRect(elementWithHeights([0, 0, 0, 0, 0, 0, 120])), 6);
        expect(result.settled).toBe(false);
    });

    it('settles after the element has opened and then held still for two frames', async () => {
        const result = await run(waitForStableRect(elementWithHeights([0, 0, 40, 120, 120, 120, 120])), 20);
        expect(result.settled).toBe(true);
        expect(result.frames).toBe(6);
    });

    it('still ends for an element that never opens, at maxFrames', async () => {
        const result = await run(waitForStableRect(elementWithHeights([0]), 10), 50);
        expect(result.settled).toBe(true);
        expect(result.frames).toBe(10);
    });
});
