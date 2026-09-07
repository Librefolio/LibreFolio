// @vitest-environment jsdom
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {createResizeWatcher} from '../resizeWatcher';

/**
 * jsdom has no layout engine and therefore no `ResizeObserver`. The double below
 * records what was observed and disconnected, which is exactly the contract these
 * tests are about — not whether a resize actually fires, which is the browser's
 * job and is covered by the E2E suite.
 */
class FakeResizeObserver {
    static instances: FakeResizeObserver[] = [];
    observed: Element[] = [];
    disconnected = false;
    constructor(public cb: (entries?: ResizeObserverEntry[]) => void) {
        FakeResizeObserver.instances.push(this);
    }
    observe(el: Element) {
        this.observed.push(el);
    }
    disconnect() {
        this.disconnected = true;
    }
}

beforeAll(() => {
    vi.stubGlobal('ResizeObserver', FakeResizeObserver);
});

function el(id: string): Element {
    const node = document.createElement('div');
    node.id = id;
    return node;
}

describe('createResizeWatcher', () => {
    it('observes the element it is given', () => {
        FakeResizeObserver.instances = [];
        const w = createResizeWatcher(() => {});
        const a = el('a');
        w.observe(a);
        expect(FakeResizeObserver.instances).toHaveLength(1);
        expect(FakeResizeObserver.instances[0].observed).toEqual([a]);
    });

    it('does nothing when there is no element yet', () => {
        // Components call this from an effect that may run before the node is bound.
        FakeResizeObserver.instances = [];
        const w = createResizeWatcher(() => {});
        w.observe(null);
        w.observe(undefined);
        expect(FakeResizeObserver.instances).toHaveLength(0);
    });

    it('does not observe the same element twice', () => {
        FakeResizeObserver.instances = [];
        const w = createResizeWatcher(() => {});
        const a = el('a');
        w.observe(a);
        w.observe(a);
        w.observe(a);
        expect(FakeResizeObserver.instances).toHaveLength(1);
    });

    it('re-points at a new element, releasing the old one', () => {
        // The defect this module exists for: seven of the eight copies checked only
        // "do I have an observer?", so after Svelte replaced the node they kept
        // watching a detached one and the chart stopped resizing — with nothing to
        // show for it.
        FakeResizeObserver.instances = [];
        const w = createResizeWatcher(() => {});
        const a = el('a');
        const b = el('b');
        w.observe(a);
        w.observe(b);

        expect(FakeResizeObserver.instances).toHaveLength(2);
        expect(FakeResizeObserver.instances[0].disconnected).toBe(true);
        expect(FakeResizeObserver.instances[1].observed).toEqual([b]);
        expect(FakeResizeObserver.instances[1].disconnected).toBe(false);
    });

    it('forwards resize notifications to the caller', () => {
        FakeResizeObserver.instances = [];
        const onResize = vi.fn();
        const w = createResizeWatcher(onResize);
        w.observe(el('a'));

        FakeResizeObserver.instances[0].cb();
        FakeResizeObserver.instances[0].cb();
        expect(onResize).toHaveBeenCalledTimes(2);
    });

    it('forwards the first ResizeObserverEntry to the caller', () => {
        // LotComparisonChart is the one caller that reads the entry: it thresholds
        // sub-pixel jitter off `entry.contentRect` and resizes ECharts to that exact
        // box. If the watcher stopped forwarding the entry, that chart would silently
        // fall back to re-measuring — the divergence this argument exists for.
        FakeResizeObserver.instances = [];
        const onResize = vi.fn();
        const w = createResizeWatcher(onResize);
        w.observe(el('a'));

        const entryA = {contentRect: {width: 640, height: 480}} as unknown as ResizeObserverEntry;
        const entryB = {contentRect: {width: 100, height: 100}} as unknown as ResizeObserverEntry;
        FakeResizeObserver.instances[0].cb([entryA, entryB]);
        expect(onResize).toHaveBeenCalledWith(entryA);
    });

    it('tolerates a notification carrying no entries', () => {
        // Real ResizeObservers always deliver a non-empty array, but the `?.` guard
        // keeps a zero-argument caller (every other component) and any hand-driven
        // double from throwing on `entries[0]`.
        FakeResizeObserver.instances = [];
        const onResize = vi.fn();
        const w = createResizeWatcher(onResize);
        w.observe(el('a'));

        expect(() => FakeResizeObserver.instances[0].cb()).not.toThrow();
        expect(onResize).toHaveBeenCalledWith(undefined);
    });

    it('releases the observer on disconnect', () => {
        FakeResizeObserver.instances = [];
        const w = createResizeWatcher(() => {});
        w.observe(el('a'));
        w.disconnect();
        expect(FakeResizeObserver.instances[0].disconnected).toBe(true);
    });

    it('observes again after a disconnect', () => {
        // A component that is destroyed and re-created must start watching again;
        // forgetting to clear `observed` on disconnect would make the second
        // observe() a no-op when the same node comes back.
        FakeResizeObserver.instances = [];
        const w = createResizeWatcher(() => {});
        const a = el('a');
        w.observe(a);
        w.disconnect();
        w.observe(a);
        expect(FakeResizeObserver.instances).toHaveLength(2);
        expect(FakeResizeObserver.instances[1].observed).toEqual([a]);
    });

    it('survives a disconnect that was never preceded by an observe', () => {
        const w = createResizeWatcher(() => {});
        expect(() => w.disconnect()).not.toThrow();
    });
});
