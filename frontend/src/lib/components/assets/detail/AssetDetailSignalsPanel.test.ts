// @vitest-environment jsdom
/**
 * AssetDetailSignalsPanel — component test (Vitest + jsdom), FE5c.
 *
 * The foldable frame of the asset page's signals. Folded, it renders neither its panel nor the section the
 * page puts inside it (its children); its toggle unfolds it. The page keeps `open` with a binding — it reads
 * it, and opens the panel itself to configure a signal — so the binding is followed both ways, through a host
 * that binds it as the page does (`$test/harness/AssetDetailSignalsPanelHarness.svelte`).
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {createRawSnippet} from 'svelte';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import Host from '$test/harness/AssetDetailSignalsPanelHarness.svelte';
import AssetDetailSignalsPanel from './AssetDetailSignalsPanel.svelte';

/** The page's signals section, as a stand-in the test owns. */
const signalsSection = createRawSnippet(() => ({render: () => '<div data-testid="probe-signals-section">signals</div>'}));

function expectUnfolded(): void {
    expect(screen.getByTestId('asset-detail-signals-toggle')).toHaveAttribute('aria-expanded', 'true');
    expect(within(screen.getByTestId('asset-detail-signals-panel')).getByTestId('probe-signals-section')).toBeInTheDocument();
}

function expectFolded(): void {
    expect(screen.getByTestId('asset-detail-signals-toggle')).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByTestId('asset-detail-signals-panel')).toBeNull();
    expect(screen.queryByTestId('probe-signals-section')).toBeNull();
}

describe('AssetDetailSignalsPanel: folded, no panel and no children; its toggle unfolds it; open is bound both ways', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('renders neither its panel nor its children while folded', () => {
        render(AssetDetailSignalsPanel, {props: {open: false, children: signalsSection}});

        expectFolded();
    });

    it('renders its children inside its panel while unfolded', () => {
        render(AssetDetailSignalsPanel, {props: {open: true, children: signalsSection}});

        expectUnfolded();
    });

    it('unfolds on a click of its toggle, and folds on the next one', async () => {
        render(AssetDetailSignalsPanel, {props: {open: false, children: signalsSection}});

        await fireEvent.click(screen.getByTestId('asset-detail-signals-toggle'));
        expectUnfolded();

        await fireEvent.click(screen.getByTestId('asset-detail-signals-toggle'));
        expectFolded();
    });

    it('binds open: the host sees its toggle, and the panel follows the host', async () => {
        render(Host);
        expect(screen.getByTestId('probe-signals-open')).toHaveTextContent('false');

        await fireEvent.click(screen.getByTestId('asset-detail-signals-toggle'));
        expect(screen.getByTestId('probe-signals-open')).toHaveTextContent('true');
        expectUnfolded();

        await fireEvent.click(screen.getByTestId('probe-signals-host-toggle'));
        expect(screen.getByTestId('probe-signals-open')).toHaveTextContent('false');
        expectFolded();

        await fireEvent.click(screen.getByTestId('probe-signals-host-toggle'));
        expect(screen.getByTestId('probe-signals-open')).toHaveTextContent('true');
        expectUnfolded();
    });
});
