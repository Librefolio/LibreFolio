// @vitest-environment jsdom
/**
 * The harness's `toBeDisabled` / `toBeEnabled` (project 85, BTN-0): redefined in `component.ts`, after jest-dom, so that
 * an element's own `aria-disabled="true"` counts as disabled, as in Playwright.
 *
 * The standard button keeps three kinds of «off» reachable (a reason, an icon that is off, busy) with `aria-disabled`
 * instead of the native attribute. With jest-dom's matchers alone, `toBeEnabled()` and `not.toBeDisabled()` would pass
 * in silence on a button the user cannot use. Native `disabled` and a plain button keep jest-dom's meaning; an
 * ancestor's `aria-disabled` does not count.
 */
import {describe, expect, it} from 'vitest';
import '$test/component';

function element(html: string): HTMLElement {
    const host = document.createElement('div');
    host.innerHTML = html;
    document.body.appendChild(host);
    return host.firstElementChild as HTMLElement;
}

describe('toBeDisabled / toBeEnabled in the component harness', () => {
    it('aria-disabled="true": disabled, not enabled', () => {
        const button = element('<button type="button" aria-disabled="true">Go</button>');
        expect(button).toBeDisabled();
        expect(() => expect(button).toBeEnabled()).toThrow();
        expect(() => expect(button).not.toBeDisabled()).toThrow();
        expect(button).not.toBeEnabled();
    });

    it('native disabled: unchanged', () => {
        const button = element('<button type="button" disabled>Go</button>');
        expect(button).toBeDisabled();
        expect(button).not.toBeEnabled();
        expect(() => expect(button).toBeEnabled()).toThrow();
    });

    it('a plain button: enabled', () => {
        const button = element('<button type="button">Go</button>');
        expect(button).toBeEnabled();
        expect(button).not.toBeDisabled();
        expect(() => expect(button).toBeDisabled()).toThrow();
    });

    it('aria-disabled="false" and an ancestor’s aria-disabled do not count', () => {
        expect(element('<button type="button" aria-disabled="false">Go</button>')).toBeEnabled();
        const inner = element('<div aria-disabled="true"><button type="button">Go</button></div>').querySelector('button');
        expect(inner).toBeEnabled();
    });
});
