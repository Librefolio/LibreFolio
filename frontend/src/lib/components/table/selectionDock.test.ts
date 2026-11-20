// @vitest-environment jsdom
/**
 * The watcher of the selection panel (plan 77, SEL-A, Q-SEL-13): the top of a table is watched against the element that
 * really scrolls it — a dialog's body, a section, or the page (null: the viewport) — and the dock takes the actions only
 * while that top is out of view. Without IntersectionObserver (an old browser, a test without the stub) the top counts as
 * in view: the actions stay at the top, where they are always reachable.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {scrollRootOf, watchInView} from './selectionDock';

afterEach(() => {
    vi.unstubAllGlobals();
    document.body.innerHTML = '';
});

function nest(styles: Array<Partial<CSSStyleDeclaration>>): HTMLElement {
    let parent: HTMLElement = document.body;
    for (const style of styles) {
        const el = document.createElement('div');
        Object.assign(el.style, style);
        parent.appendChild(el);
        parent = el;
    }
    return parent;
}

describe('scrollRootOf', () => {
    it('is the nearest ancestor that scrolls vertically', () => {
        const target = nest([{overflowY: 'auto'}, {overflowY: 'scroll'}, {}, {}]);
        expect(scrollRootOf(target)).toBe(target.parentElement!.parentElement);
    });

    it('ignores an ancestor that only clips or scrolls sideways', () => {
        const target = nest([{overflowY: 'auto'}, {overflowY: 'hidden'}, {overflowX: 'auto'}, {}]);
        expect(scrollRootOf(target)).toBe(target.parentElement!.parentElement!.parentElement);
    });

    it('is null (the viewport) when no ancestor scrolls', () => {
        expect(scrollRootOf(nest([{}, {}]))).toBeNull();
    });
});

describe('watchInView', () => {
    it('observes the target against its scroll root and reports each change', () => {
        const seen: Array<{root: Element | Document | null | undefined}> = [];
        let callback: IntersectionObserverCallback = () => {};
        const disconnect = vi.fn();
        vi.stubGlobal(
            'IntersectionObserver',
            class {
                constructor(cb: IntersectionObserverCallback, options?: IntersectionObserverInit) {
                    callback = cb;
                    seen.push({root: options?.root});
                }
                observe() {}
                disconnect = disconnect;
            },
        );
        const target = nest([{overflowY: 'auto'}, {}]);
        const onChange = vi.fn();
        const stop = watchInView(target, onChange);
        expect(seen[0].root).toBe(target.parentElement);
        callback([{isIntersecting: false} as IntersectionObserverEntry], {} as IntersectionObserver);
        expect(onChange).toHaveBeenLastCalledWith(false);
        callback([{isIntersecting: true} as IntersectionObserverEntry], {} as IntersectionObserver);
        expect(onChange).toHaveBeenLastCalledWith(true);
        stop();
        expect(disconnect).toHaveBeenCalled();
    });

    it('without IntersectionObserver the top counts as in view', () => {
        vi.stubGlobal('IntersectionObserver', undefined);
        const onChange = vi.fn();
        const stop = watchInView(nest([{}]), onChange);
        expect(onChange).toHaveBeenCalledWith(true);
        stop();
    });
});
