// @vitest-environment jsdom
import {afterEach, describe, expect, it} from 'vitest';
import {isOutsideClick} from '../clickOutside';

/** Mount some markup under a fresh, document-attached host and return it. */
function connected(html: string): HTMLElement {
    const host = document.createElement('div');
    host.innerHTML = html;
    document.body.appendChild(host);
    return host;
}

afterEach(() => {
    document.body.innerHTML = '';
});

describe('isOutsideClick', () => {
    it('treats a detached target as NOT an outside click (the promoted isConnected guard)', () => {
        // Only SingleDatePicker and DateRangePicker carried this guard; it is now
        // every caller's. A nested SimpleSelect/CurrencySearchSelect removes the
        // clicked <option> on mousedown, so by click-time the target is detached
        // and every contains/closest reads "outside" — closing the very surface
        // the user is operating. A detached target must therefore never close,
        // even when the predicate says it is not inside.
        const detached = document.createElement('button'); // never appended
        expect(detached.isConnected).toBe(false);
        expect(isOutsideClick(detached, () => false)).toBe(false);
    });

    it('returns false when the target is null', () => {
        expect(isOutsideClick(null, () => false)).toBe(false);
    });

    it('returns false when the target is not an Element (e.g. the document)', () => {
        // Guards against `(target as HTMLElement).closest(...)` throwing on a
        // non-element target, which the original hand-written copies risked.
        expect(isOutsideClick(document, () => false)).toBe(false);
    });

    it('is an outside click when connected and the predicate says not-inside', () => {
        const host = connected('<button id="x">x</button>');
        const btn = host.querySelector('#x') as HTMLElement;
        expect(isOutsideClick(btn, () => false)).toBe(true);
    });

    it('is not an outside click when the predicate says inside', () => {
        const host = connected('<button id="x">x</button>');
        const btn = host.querySelector('#x') as HTMLElement;
        expect(isOutsideClick(btn, () => true)).toBe(false);
    });

    it('supports a contains-based predicate — the five menu/dropdown copies', () => {
        const host = connected('<div class="menu"><button id="in">in</button></div><button id="out">out</button>');
        const menu = host.querySelector('.menu') as HTMLElement;
        const inside = host.querySelector('#in') as HTMLElement;
        const outside = host.querySelector('#out') as HTMLElement;
        const pred = (el: Element) => menu.contains(el);
        expect(isOutsideClick(inside, pred)).toBe(false);
        expect(isOutsideClick(outside, pred)).toBe(true);
    });

    it('supports a closest-based predicate — the four portalled date/autocomplete copies', () => {
        const host = connected('<div class="sdp-popover"><span id="opt">opt</span></div><span id="elsewhere">e</span>');
        const opt = host.querySelector('#opt') as HTMLElement;
        const elsewhere = host.querySelector('#elsewhere') as HTMLElement;
        const pred = (el: Element) => !!el.closest('.sdp-popover') || !!el.closest('.sdp-trigger');
        expect(isOutsideClick(opt, pred)).toBe(false);
        expect(isOutsideClick(elsewhere, pred)).toBe(true);
    });

    it('supports a two-surface predicate — Tooltip (trigger OR tooltip body)', () => {
        const host = connected('<button id="trig">t</button><div id="tip"><a id="link">l</a></div><span id="far">f</span>');
        const trigger = host.querySelector('#trig') as HTMLElement;
        const tip = host.querySelector('#tip') as HTMLElement;
        const link = host.querySelector('#link') as HTMLElement;
        const far = host.querySelector('#far') as HTMLElement;
        const pred = (el: Element) => !trigger || trigger.contains(el) || (tip?.contains(el) ?? false);
        expect(isOutsideClick(trigger, pred)).toBe(false); // on the trigger
        expect(isOutsideClick(link, pred)).toBe(false); // inside the tooltip body
        expect(isOutsideClick(far, pred)).toBe(true);
    });

    it('treats a missing ref as inside — the `!ref || ref.contains` pattern keeps the menu open until bound', () => {
        // Preserves the original `if (ref && !ref.contains(t))` semantics of the
        // contains-based copies: no ref yet (listener fired before bind:this) ⇒
        // do not close; ref bound and target genuinely outside ⇒ close.
        const menuHost = connected('<div class="menu">m</div>');
        const menu = menuHost.querySelector('.menu') as HTMLElement;
        const outsideHost = connected('<button id="x">x</button>');
        const outside = outsideHost.querySelector('#x') as HTMLElement;

        let ref: HTMLElement | null = null;
        const pred = (el: Element) => !ref || ref.contains(el);

        expect(isOutsideClick(outside, pred)).toBe(false);
        ref = menu;
        expect(isOutsideClick(outside, pred)).toBe(true);
    });
});
