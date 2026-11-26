// @vitest-environment jsdom
/**
 * LinkBadge — a link drawn as a badge: an anchor with `href`, a button otherwise, the same look in both.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet} from 'svelte';
import {cleanup, fireEvent, render, screen} from '$test/component';
import LinkBadge from './LinkBadge.svelte';

afterEach(cleanup);

const children = createRawSnippet(() => ({render: () => '<span>Go</span>'}));
const badge = () => screen.getByTestId('badge');

describe('LinkBadge', () => {
    it('is an anchor to its href, with its content', () => {
        render(LinkBadge, {href: '/transactions?asset=1', testId: 'badge', children});
        expect(badge().tagName).toBe('A');
        expect(badge()).toHaveAttribute('href', '/transactions?asset=1');
        expect(badge()).not.toHaveAttribute('type');
        expect(badge()).toHaveTextContent('Go');
    });

    it('without an href is a plain button that calls onclick', async () => {
        const onclick = vi.fn();
        render(LinkBadge, {onclick, testId: 'badge', children});
        expect(badge().tagName).toBe('BUTTON');
        expect(badge()).toHaveAttribute('type', 'button');
        expect(badge()).not.toHaveAttribute('href');
        await fireEvent.click(badge());
        expect(onclick).toHaveBeenCalledTimes(1);
    });

    it('looks the same in both, with the focus ring', () => {
        const link = render(LinkBadge, {href: '/x', testId: 'badge', children});
        const classes = badge().className;
        link.unmount();
        render(LinkBadge, {testId: 'badge', children});
        expect(badge().className).toBe(classes);
        expect(badge()).toHaveClass('border-lf-focus', 'text-lf-link', 'focus-visible:outline-lf-focus');
    });
});
