// @vitest-environment jsdom
/**
 * DataQualityBanner — each severity in its own state (the designer's round 3, §2; lot R3-a of workstream T, 17/10).
 *
 * Until round 3 an error and a warning shared the warning tint (`STATUS_TONES.dataQuality.attention`), and only the
 * icon told them apart. The designer asked for «errori veri in danger»: since R3-a an error is drawn in danger, a
 * warning in warning and an info in info, through `DATA_QUALITY_TONE` (`$lib/theme/toneClasses`); which conditions are
 * errors stays the backend's call, condition by condition. The banner publishes the tone it draws, `data-tone`, beside
 * the severity it draws it for, `data-severity`:
 *   - grouped (the Dashboard, the risk panels): the container `data-quality-banner` takes the tone of its worst issue;
 *     unfolded, each row `data-quality-issue-{code}` keeps its own severity and the tone of it, so a warning row inside
 *     a banner holding an error keeps its warning icon and chips;
 *   - flat (the asset and FX detail pages): each banner `data-quality-issue-{code}` carries its severity and its tone.
 *
 * The contract under test:
 *   - DQT-01: `DATA_QUALITY_TONE` maps error → danger, warning → warning, info → info;
 *   - DQT-02 (grouped): an error, a warning and an info → the container is danger, folded and unfolded; unfolded, each
 *     row keeps its `data-severity` and takes the tone of its own: danger, warning, info;
 *   - DQT-03 (grouped): a warning and an info, no error → warning; an info only → info; each row still in its own tone;
 *   - DQT-04 (flat): each banner carries its `data-severity` and the matching `data-tone`.
 *
 * The fixtures. Three issues with their real code, key and severity — MISSING_PRICE, an error of the portfolio report;
 * STALE_PRICE, a warning of it; RANGE_BEFORE_FIRST_DATA, the info the asset page adds — put together so that every
 * severity is drawn beside the others in one mount: the banner reads an issue's severity, never its code. Wherever
 * there are several, the worst issue is passed last, so the container's tone cannot come from the first by accident.
 *
 * What it reads: the state the banner publishes, `data-tone`, `data-severity` and `aria-expanded`, never a colour class
 * (design system, rule 10): a tone's classes live in `STATUS_TONES` and change whenever the colours do. The expected
 * tones are written out here (`TONE_OF`), not read back from `DATA_QUALITY_TONE`. No translated text is read.
 *
 * Red before R3-a: `DATA_QUALITY_TONE` did not exist, so the file did not collect; the banner published no `data-tone`,
 * and its flat banners no `data-severity` either.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {DATA_QUALITY_TONE} from '$lib/theme/toneClasses';
import type {DataQualityIssue} from './DataQualityBanner.svelte';
import DataQualityBanner from './DataQualityBanner.svelte';

/** The state the designer gives each severity (round 3): written out, never read back from `DATA_QUALITY_TONE`. */
const TONE_OF: Record<DataQualityIssue['severity'], string> = {error: 'danger', warning: 'warning', info: 'info'};

// --- Fixtures: the issues as their sources send them -----------------------------------------------------------------

/** Two assets with no market price, as the portfolio report sends them: an error, with a way to each asset. */
const MISSING_PRICE: DataQualityIssue = {
    domain: 'portfolio',
    code: 'MISSING_PRICE',
    severity: 'error',
    message_i18n_key: 'dataQuality.missingPrice',
    message_params: {count: 2},
    count: 2,
    affected_asset_ids: [301, 302],
    affected_asset_names: ['Delisted fund', 'Unlisted bond'],
    affected_fx_pairs: [],
    cta_action: 'navigate_asset',
    cta_target: '301',
    group_key: 'missing_price',
};

/** One asset with an outdated price, as the portfolio report sends it: a warning, with its sync. */
const STALE_PRICE: DataQualityIssue = {
    domain: 'portfolio',
    code: 'STALE_PRICE',
    severity: 'warning',
    message_i18n_key: 'dataQuality.stalePrice',
    message_params: {count: 1},
    count: 1,
    affected_asset_ids: [303],
    affected_asset_names: ['Quiet stock'],
    affected_fx_pairs: [],
    cta_action: 'sync_asset_prices',
    cta_target: '303',
    group_key: 'stale_price',
};

/** The range starts before the first price, as the asset page says it: an info, with no action. */
const RANGE_NOTE: DataQualityIssue = {domain: 'asset', code: 'RANGE_BEFORE_FIRST_DATA', severity: 'info', message_i18n_key: 'dataQuality.rangeBeforeData', message_params: {date: '2025-03-03'}};

/** One issue of each severity, the error last. */
const ONE_OF_EACH: DataQualityIssue[] = [STALE_PRICE, RANGE_NOTE, MISSING_PRICE];

// --- Helpers ---------------------------------------------------------------------------------------------------------

/** Mount the grouped banner on `issues` and return its container, which mounts folded. */
function mountGrouped(issues: DataQualityIssue[]): HTMLElement {
    render(DataQualityBanner, {issues, mode: 'grouped'});
    return screen.getByTestId('data-quality-banner');
}

/** Unfold the grouped banner: it mounts folded, so the toggle is checked folded, clicked once, and checked unfolded. */
async function unfold(banner: HTMLElement): Promise<void> {
    const toggle = within(banner).getByTestId('data-quality-toggle');
    expect(toggle, 'mounted folded').toHaveAttribute('aria-expanded', 'false');
    await fireEvent.click(toggle);
    expect(toggle, 'unfolded').toHaveAttribute('aria-expanded', 'true');
}

/** In `scope`, one row (grouped) or one banner (flat) per issue, each with its own severity and the tone of that severity. */
function expectEachInItsOwnTone(scope: HTMLElement, issues: DataQualityIssue[]): void {
    const drawn = within(scope)
        .getAllByTestId(/^data-quality-issue-/)
        .map((element) => element.getAttribute('data-testid'));
    expect(drawn.sort(), 'one per issue, none left out of the reading below').toEqual(issues.map((issue) => `data-quality-issue-${issue.code}`).sort());
    for (const issue of issues) {
        const element = within(scope).getByTestId(`data-quality-issue-${issue.code}`);
        expect(element, `${issue.code}: its own severity`).toHaveAttribute('data-severity', issue.severity);
        expect(element, `${issue.code}: the tone of its severity, ${TONE_OF[issue.severity]}`).toHaveAttribute('data-tone', TONE_OF[issue.severity]);
    }
}

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('DataQualityBanner — each severity in its own state (round 3)', () => {
    it('DQT-01: DATA_QUALITY_TONE draws an error in danger, a warning in warning, an info in info', () => {
        expect(DATA_QUALITY_TONE).toEqual(TONE_OF);
    });

    it('DQT-02: grouped, an error beside a warning and an info: the container is danger, and each row keeps the tone of its own severity', async () => {
        const banner = mountGrouped(ONE_OF_EACH);
        expect(banner, 'folded: the tone of the worst issue, the error').toHaveAttribute('data-tone', 'danger');

        await unfold(banner);
        expect(banner, 'unfolded: still the tone of the worst issue').toHaveAttribute('data-tone', 'danger');
        expectEachInItsOwnTone(banner, ONE_OF_EACH);
    });

    it.each([
        {name: 'a warning and an info, no error', issues: [RANGE_NOTE, STALE_PRICE], tone: 'warning'},
        {name: 'an info only', issues: [RANGE_NOTE], tone: 'info'},
    ])('DQT-03: grouped, $name: the container is $tone, and each row keeps the tone of its own severity', async ({issues, tone}) => {
        const banner = mountGrouped(issues);
        expect(banner, 'folded: the tone of the worst issue').toHaveAttribute('data-tone', tone);

        await unfold(banner);
        expect(banner, 'unfolded: still the tone of the worst issue').toHaveAttribute('data-tone', tone);
        expectEachInItsOwnTone(banner, issues);
    });

    it('DQT-04: flat, one banner per issue: each carries its own severity and the tone of that severity', () => {
        render(DataQualityBanner, {issues: ONE_OF_EACH, mode: 'flat'});

        expectEachInItsOwnTone(document.body, ONE_OF_EACH);
        // Asked once the flat banners are proven drawn, above: in this mode no container groups them.
        expect(screen.queryByTestId('data-quality-banner'), 'flat: no grouped container').toBeNull();
    });
});
