// @vitest-environment jsdom
/**
 * FixFlaggedStep — component test (Vitest + jsdom).
 *
 * Subject: the F11 report-an-issue note. The wizard's fix step asks the user to
 * repair rows the broker plugin could not read; when the plugin itself is at
 * fault, the user needs a visible path to report it, so the step renders a
 * warning InfoBanner with a link to open a GitHub issue. The contract under
 * test: the banner is the *warning* variant, the link lives inside it, points
 * at the repo's new-issue page, and opens in a new tab with noopener.
 *
 * The step's interactive row editing (pickers, split editors, type select) is
 * out of scope here — those controls mount inside expanded rows, and the rows
 * below stay collapsed.
 *
 * Nothing here asserts translated text: the banner copy comes from the
 * four-language catalogue; the anchors are `info-banner-warning` (the
 * InfoBanner variant contract) and `fix-step-report-issue-link`.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {render, screen, setupI18n, waitFor} from '$test/component';
import FixFlaggedStep from './FixFlaggedStep.svelte';

/** One flagged row with an unreadable-quantity blocker, left pending. */
function flaggedRow(index: number) {
    return {
        index,
        tx: {type: 'BUY', date: '2026-01-10', asset_id: null, quantity: null, cash: {code: 'EUR', amount: '-100'}},
        todos: [{field: 'quantity', severity: 'blocker' as const, reasonCode: 'missing_quantity', message: 'NEEDLE-QUANTITY-UNREADABLE'}],
        decision: null,
    };
}

function mountStep(rows: ReturnType<typeof flaggedRow>[]) {
    return render(FixFlaggedStep, {
        rows,
        analysisAssets: [],
        expanded: new Set<number>(),
        ontoggle: vi.fn(),
        onapply: vi.fn(),
        onaccept: vi.fn(),
        onacceptall: vi.fn(),
        oncreateasset: vi.fn(),
        onreset: vi.fn(),
        onresetall: vi.fn(),
        onreopen: vi.fn(),
    });
}

beforeAll(async () => {
    await setupI18n();
});

describe('FixFlaggedStep — report-issue note (F11)', () => {
    it('renders a warning banner containing the GitHub new-issue link when rows are present', async () => {
        mountStep([flaggedRow(0), flaggedRow(1)]);

        // Barrier: the step rendered its rows before the banner is read.
        await waitFor(() => expect(screen.getByTestId('fix-step-rows')).toBeInTheDocument());

        const banner = screen.getByTestId('info-banner-warning');
        const link = screen.getByTestId('fix-step-report-issue-link');
        expect(banner.contains(link)).toBe(true);
        expect(link).toHaveAttribute('href', 'https://github.com/Librefolio/LibreFolio/issues/new');
        expect(link).toHaveAttribute('target', '_blank');
        expect(link.getAttribute('rel')).toContain('noopener');
    });

    it('keeps the note visible in the nothing-flagged state too', async () => {
        // The hint is about the *step*, not about the rows: an all-clean import
        // can still be the sign of a plugin that read nothing at all.
        mountStep([]);

        await waitFor(() => expect(screen.getByTestId('fix-step-empty')).toBeInTheDocument());

        expect(screen.getByTestId('info-banner-warning')).toBeInTheDocument();
        expect(screen.getByTestId('fix-step-report-issue-link')).toBeInTheDocument();
    });
});
