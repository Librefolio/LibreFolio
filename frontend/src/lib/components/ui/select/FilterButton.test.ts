// @vitest-environment jsdom
/**
 * FilterButton — component test (Vitest + jsdom).
 *
 * The button that opens a filter, shared by CheckMenu and the allocation tab: neutral with no choice on, the info tint
 * and a round count when some are, `aria-expanded` for the popup it opens.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {Filter} from 'lucide-svelte';
import {cleanup, fireEvent, render, screen} from '$test/component';
import FilterButton from './FilterButton.svelte';

afterEach(cleanup);

const button = () => screen.getByTestId('fb');

describe('FilterButton', () => {
    it('is neutral with no choice on: no badge, no info tint', () => {
        render(FilterButton, {label: 'Filters', icon: Filter, testId: 'fb'});

        expect(button()).toHaveAttribute('type', 'button');
        expect(button()).toHaveTextContent('Filters');
        expect(button()).toHaveClass('border-lf-subtle');
        expect(button()).not.toHaveClass('bg-lf-info-soft');
        expect(button().querySelector('.rounded-full'), 'no count badge').toBeNull();
    });

    it('takes the info tint and shows the count when choices are on', () => {
        render(FilterButton, {label: 'Filters', icon: Filter, count: 3, testId: 'fb'});

        expect(button()).toHaveClass('bg-lf-info-soft', 'border-lf-info-line', 'text-lf-info-on-soft');
        expect(button()).toHaveTextContent('3');
    });

    it('publishes aria-expanded, and turns the chevron when open', () => {
        const {unmount} = render(FilterButton, {label: 'Filters', icon: Filter, testId: 'fb'});
        expect(button()).toHaveAttribute('aria-expanded', 'false');
        unmount();

        render(FilterButton, {label: 'Filters', icon: Filter, expanded: true, testId: 'fb'});
        expect(button()).toHaveAttribute('aria-expanded', 'true');
        expect(button().querySelector('svg.rotate-180'), 'the chevron is turned').not.toBeNull();
    });

    it('can drop the chevron', () => {
        render(FilterButton, {label: 'Filters', icon: Filter, chevron: false, testId: 'fb'});
        // Only the icon is left.
        expect(button().querySelectorAll('svg')).toHaveLength(1);
    });

    it('calls onclick and passes the other attributes to the button', async () => {
        const onclick = vi.fn();
        render(FilterButton, {label: 'Filters', icon: Filter, onclick, testId: 'fb', 'aria-controls': 'panel-1'} as never);

        await fireEvent.click(button());

        expect(onclick).toHaveBeenCalledTimes(1);
        expect(button()).toHaveAttribute('aria-controls', 'panel-1');
    });
});
