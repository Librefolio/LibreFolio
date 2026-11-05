// @vitest-environment jsdom
/**
 * LinkedStackedBar — component test (Vitest + jsdom).
 *
 * The bar and legend shared by the Files page's space bar and the planner's timing bar (K-2). Props in, DOM out:
 * a segment per entry with its width, a legend row per entry with the dot and the caller's content, the optional
 * label that makes the bar an image, and the link between the two halves (`data-active`, published on both).
 */
import {afterEach, describe, expect, it} from 'vitest';
import {createRawSnippet} from 'svelte';
import {cleanup, fireEvent, render, screen} from '$test/component';
import LinkedStackedBar from './LinkedStackedBar.svelte';
import type {LinkedSegment} from './linkedStackedBar';

afterEach(cleanup);

const SEGMENTS: LinkedSegment[] = [
    {id: 'a', percent: 60, fill: 'bg-lf-brand', attrs: {'data-bytes': 600}},
    {id: 'b', percent: 40, fill: 'bg-lf-info'},
];

const row = createRawSnippet((segment: () => LinkedSegment) => ({render: () => `<span data-testid="row-text">${segment().id}</span>`}));

function mount(props: Record<string, unknown> = {}) {
    return render(LinkedStackedBar, {
        segments: SEGMENTS,
        barClass: 'flex h-3',
        legendClass: 'grid',
        testIds: {bar: 'bar', segment: (id: string) => `seg-${id}`, legend: 'legend', item: (id: string) => `item-${id}`},
        row,
        ...props,
    });
}

describe('LinkedStackedBar — the drawing', () => {
    it("draws a segment per entry with its width and its extra attributes, and a legend row per entry with the caller's content", () => {
        mount();

        expect(screen.getByTestId('seg-a')).toHaveStyle({width: '60%'});
        expect(screen.getByTestId('seg-a')).toHaveAttribute('data-bytes', '600');
        expect(screen.getByTestId('seg-b')).toHaveStyle({width: '40%'});
        expect(screen.getByTestId('item-a')).toHaveTextContent('a');
        expect(screen.getByTestId('item-b')).toHaveTextContent('b');
    });

    it('is an image with a label when given one, decoration otherwise', () => {
        mount({barLabel: 'summary'});
        expect(screen.getByTestId('bar')).toHaveAttribute('role', 'img');
        expect(screen.getByTestId('bar')).toHaveAttribute('aria-label', 'summary');
        cleanup();

        mount();
        expect(screen.getByTestId('bar')).toHaveAttribute('aria-hidden', 'true');
    });

    it('a minimum width keeps a thin segment visible', () => {
        mount({minSegmentPx: 3});

        expect(screen.getByTestId('seg-a').getAttribute('style')).toContain('min-width: 3px');
    });
});

describe('LinkedStackedBar — the link between the bar and the legend', () => {
    const states = (id: string) => [screen.getByTestId(`seg-${id}`).getAttribute('data-active'), screen.getByTestId(`item-${id}`).getAttribute('data-active')];

    it('a segment under the pointer lights its row, and the other way round', async () => {
        mount();
        expect(states('a')).toEqual(['false', 'false']);

        await fireEvent.pointerEnter(screen.getByTestId('seg-a'));
        expect(states('a')).toEqual(['true', 'true']);
        expect(states('b')).toEqual(['false', 'false']);
        await fireEvent.pointerLeave(screen.getByTestId('seg-a'));
        expect(states('a')).toEqual(['false', 'false']);

        await fireEvent.pointerEnter(screen.getByTestId('item-b'));
        expect(states('b')).toEqual(['true', 'true']);
    });

    it('focus inside a row counts as pointing at it', async () => {
        mount();

        await fireEvent.focusIn(screen.getByTestId('item-a'));
        expect(states('a')).toEqual(['true', 'true']);
        await fireEvent.focusOut(screen.getByTestId('item-a'));
        expect(states('a')).toEqual(['false', 'false']);
    });

    it('a segment that disappears while pointed leaves nothing lit', async () => {
        const {rerender} = mount();
        await fireEvent.pointerEnter(screen.getByTestId('seg-b'));
        expect(states('b')).toEqual(['true', 'true']);

        await rerender({segments: [SEGMENTS[0]]});
        expect(screen.queryByTestId('seg-b')).toBeNull();
        expect(states('a')).toEqual(['false', 'false']);
    });
});
