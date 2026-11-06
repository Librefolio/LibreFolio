// @vitest-environment jsdom
/**
 * FoldPanel — component test (Vitest + jsdom).
 *
 * A native `<details>` that starts closed. It publishes `data-open` and keeps its body mounted while closed, so what was
 * typed in it survives a fold (K-2, K-3).
 */
import {afterEach, describe, expect, it} from 'vitest';
import {createRawSnippet} from 'svelte';
import {cleanup, fireEvent, render, screen} from '$test/component';
import FoldPanel from './FoldPanel.svelte';

afterEach(cleanup);

const children = createRawSnippet(() => ({render: () => '<input data-testid="inside" />'}));

const panel = () => screen.getByTestId('fold') as HTMLDetailsElement;

describe('FoldPanel', () => {
    it('starts closed, and says so', () => {
        render(FoldPanel, {title: 'Advanced', testId: 'fold', children});

        expect(panel().open).toBe(false);
        expect(panel()).toHaveAttribute('data-open', 'false');
        expect(screen.getByTestId('fold-toggle')).toHaveTextContent('Advanced');
    });

    it('opens and closes from its title line, and data-open follows', async () => {
        render(FoldPanel, {title: 'Advanced', testId: 'fold', children});

        await fireEvent.click(screen.getByTestId('fold-toggle'));
        // jsdom does not toggle a <details> on a click: it is toggled as a browser does, through the attribute.
        panel().open = true;
        await fireEvent(panel(), new Event('toggle'));
        expect(panel()).toHaveAttribute('data-open', 'true');

        panel().open = false;
        await fireEvent(panel(), new Event('toggle'));
        expect(panel()).toHaveAttribute('data-open', 'false');
    });

    it('can start open, and keeps its body in the page while closed', () => {
        render(FoldPanel, {title: 'Advanced', testId: 'fold', children, open: true});
        expect(panel().open).toBe(true);
        cleanup();

        render(FoldPanel, {title: 'Advanced', testId: 'fold', children});
        expect(screen.getByTestId('inside'), 'the body stays mounted: a typed value survives a fold').toBeInTheDocument();
    });
});
