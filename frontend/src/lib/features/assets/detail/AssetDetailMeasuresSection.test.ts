// @vitest-environment jsdom
/**
 * AssetDetailMeasuresSection — component test (Vitest + jsdom), FE5c.
 *
 * The foldable frame of the asset page's measures. The page keeps the state and the measure panels; the frame
 * publishes the chart mode in `data-mode`, asks to fold or unfold with `ontoggle` — on a click, and on Enter
 * or Space, since its header is a `role="button"` — and to add a measure with `onaddmeasure`. «Add measure»
 * sits inside the header, so its click must not also fold the section: it stops the click's propagation. The
 * children, the page's measure panels, always render: the page keeps their instances. Labels are translated,
 * so nothing reads them.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {createRawSnippet} from 'svelte';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import AssetDetailMeasuresSection from './AssetDetailMeasuresSection.svelte';

/** The page's measure panels, as a stand-in the test owns. */
const measurePanels = createRawSnippet(() => ({render: () => '<div data-testid="probe-measure-panels">measures</div>'}));

/** The section in the price view, folded, with something to measure, and a spy for each callback. */
function renderSection(overrides: {mode?: string; open?: boolean; canAddMeasure?: boolean} = {}) {
    const ontoggle = vi.fn();
    const onaddmeasure = vi.fn();
    const view = render(AssetDetailMeasuresSection, {props: {mode: 'price', open: false, measureModeActive: false, canAddMeasure: true, ontoggle, onaddmeasure, children: measurePanels, ...overrides}});
    return {rerender: view.rerender, ontoggle, onaddmeasure};
}

describe('AssetDetailMeasuresSection: publishes the mode, asks to fold on a click, Enter or Space, and adds a measure without folding', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('publishes the chart mode it is given as data-mode', async () => {
        const {rerender} = renderSection({mode: 'price'});
        expect(screen.getByTestId('asset-detail-measures-section')).toHaveAttribute('data-mode', 'price');

        await rerender({mode: 'calendar-return'});

        expect(screen.getByTestId('asset-detail-measures-section')).toHaveAttribute('data-mode', 'calendar-return');
    });

    it('calls ontoggle on a click of its header', async () => {
        const {ontoggle, onaddmeasure} = renderSection();

        await fireEvent.click(screen.getByTestId('asset-detail-measures-toggle'));

        expect(ontoggle).toHaveBeenCalledTimes(1);
        expect(onaddmeasure).not.toHaveBeenCalled();
    });

    it.each(['Enter', ' '])('calls ontoggle on the %j key, and cancels the key’s default action', async (key) => {
        const {ontoggle} = renderSection();

        const notCancelled = await fireEvent.keyDown(screen.getByTestId('asset-detail-measures-toggle'), {key});

        expect(ontoggle).toHaveBeenCalledTimes(1);
        expect(notCancelled).toBe(false);
    });

    it('ignores any other key', async () => {
        const {ontoggle} = renderSection();
        const toggle = screen.getByTestId('asset-detail-measures-toggle');

        expect(await fireEvent.keyDown(toggle, {key: 'Escape'})).toBe(true);
        expect(await fireEvent.keyDown(toggle, {key: 'a'})).toBe(true);
        expect(ontoggle).not.toHaveBeenCalled();
    });

    it('disables «Add measure» while there is nothing to measure', () => {
        renderSection({canAddMeasure: false});

        expect(screen.getByTestId('asset-detail-add-measure-btn')).toBeDisabled();
    });

    it('calls onaddmeasure, and not ontoggle, on a click of «Add measure» inside the header', async () => {
        const {ontoggle, onaddmeasure} = renderSection({canAddMeasure: true});
        // Inside the header: without the stopped propagation, its click would reach the header's handler too.
        const addMeasure = within(screen.getByTestId('asset-detail-measures-toggle')).getByTestId('asset-detail-add-measure-btn');
        expect(addMeasure).toBeEnabled();

        await fireEvent.click(addMeasure);

        expect(onaddmeasure).toHaveBeenCalledTimes(1);
        expect(ontoggle).not.toHaveBeenCalled();
    });

    it('opens the measures page from the docs icon on the header’s right edge, without folding the section (RN-13, B1)', async () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null);
        const {ontoggle} = renderSection();
        const icon = screen.queryByTestId('asset-detail-measures-docs');
        expect(icon, 'the measures header has no docs icon').not.toBeNull();
        // Beside the toggle, never inside it: inside a role="button" header its click and its Enter would fold the section.
        expect(screen.getByTestId('asset-detail-measures-toggle').contains(icon)).toBe(false);

        await fireEvent.click(icon as HTMLElement);
        expect(await fireEvent.keyDown(icon as HTMLElement, {key: 'Enter'})).toBe(true);

        expect(open).toHaveBeenCalledWith('/mkdocs/user/assets/detail/measures/', '_blank', 'noopener');
        expect(ontoggle).not.toHaveBeenCalled();
        open.mockRestore();
    });

    it.each([false, true])('renders its children with open %s', (open) => {
        renderSection({open});

        expect(within(screen.getByTestId('asset-detail-measures-section')).getByTestId('probe-measure-panels')).toBeInTheDocument();
    });
});
