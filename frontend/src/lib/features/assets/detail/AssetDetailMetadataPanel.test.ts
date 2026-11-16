// @vitest-environment jsdom
/**
 * AssetDetailMetadataPanel — component test (Vitest + jsdom), RN-13 (B1).
 *
 * The foldable «Metadata & Classification» panel of the asset page. Its header is a `<button>` that folds and unfolds
 * it; the docs icon sits beside that button, on the header's right edge, never inside it (a button inside a button
 * is invalid HTML, and its click would fold the panel). The click opens the classification page, nothing else.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import AssetDetailMetadataPanel from './AssetDetailMetadataPanel.svelte';

/** The panel folded, with nothing to show inside: the header is the subject. */
function renderPanel() {
    return render(AssetDetailMetadataPanel, {
        props: {
            open: false,
            shortDescription: null,
            providerExternalUrl: null,
            classificationLoaded: false,
            sectorDistribution: null,
            geographicDistribution: null,
            identifiersList: [],
            providerAssignment: null,
            providerIconUrl: null,
            assignmentProviderName: '',
            onedit: vi.fn(),
        },
    });
}

describe('AssetDetailMetadataPanel: the docs icon beside the fold toggle (RN-13, B1)', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('unfolds on a click of its header', async () => {
        renderPanel();
        expect(screen.queryByTestId('asset-detail-metadata-panel')).toBeNull();

        await fireEvent.click(screen.getByTestId('asset-detail-metadata-toggle'));

        expect(screen.getByTestId('asset-detail-metadata-panel')).toBeInTheDocument();
    });

    it('opens the classification page from the icon, outside the toggle, without unfolding the panel', async () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null);
        renderPanel();
        const icon = screen.queryByTestId('asset-detail-metadata-docs');
        expect(icon, 'the metadata header has no docs icon').not.toBeNull();
        expect(screen.getByTestId('asset-detail-metadata-toggle').contains(icon)).toBe(false);

        await fireEvent.click(icon as HTMLElement);

        expect(open).toHaveBeenCalledWith('/mkdocs/user/assets/detail/classification/', '_blank', 'noopener');
        expect(screen.queryByTestId('asset-detail-metadata-panel')).toBeNull();
        open.mockRestore();
    });
});
