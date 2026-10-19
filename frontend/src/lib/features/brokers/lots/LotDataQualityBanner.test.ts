// @vitest-environment jsdom
/**
 * LotDataQualityBanner — every orphan pool with its own amount and its own date (workstream Y, J-53).
 *
 * The contract. The banner of the lots panel folds the data-quality issues behind a header (`lot-data-quality-toggle`,
 * `aria-expanded`) that counts categories and, unfolded, draws one block per code (`lot-data-quality-issue-{code}`),
 * with the lots it names as chips (`lot-data-quality-chip-{lotId}`). The engine sends `ASSET_INCOME_NO_ELIGIBLE_LOTS`
 * once per orphan pool, with no lot (`lot_id: null`) and the pool's own `economic_type`, `as_of_date`, `target_amount`
 * and `target_currency`. Until J-53 a block wrote the message of its code's FIRST issue only: with two pools the user
 * read one amount and one date, and the other pool's income, left unallocated as well, was nowhere on screen. The cure
 * (`buildIssueGroups` → `IssueGroup.messages`; its rules are pinned in `lotDataQualityHelpers.test.ts`, block J-53):
 * inside each block, one `lot-data-quality-message` per line — one per distinct lot-less issue, with its own params,
 * and one for the lot-bearing issues of the code, the first one's, with the chips under the block as before. The
 * blocks and the header's counts stay per code.
 *
 * The harness. As in LotCustodyModal.test.ts and LotAnalysisFailedNotice.test.ts: the banner runs with real i18n, the
 * real helpers and no module mocked. The issues are built as the client receives them (`DataQualityIssue`): every
 * engine issue carries `transaction_id`, `lot_id`, `broker_id` and `related_transaction_id`, null when it has none,
 * then its own params, amounts as decimal strings. The visible lots are the `lotDates` prop, as the panel passes it.
 *
 * Expectations. A pool's amount and day are read from its params and looked for in the messages as sent: the catalogue
 * sentence takes them as plain `{argument}`s, which svelte-i18n's formatter (intl-messageformat) writes as
 * `String(value)`, with no locale formatting — checked by a control, in this runtime. The header is compared with the
 * catalogue's own sentence for a count, through the i18n the harness boots: never a frozen string.
 *
 * Absence. «No chip in the pools' block» follows a presence barrier in the same mount: the sibling block draws its chip.
 *
 * Red, before the cure: no block draws a `lot-data-quality-message`, and the income block writes its first pool only —
 * the first test fails on the June pool's amount, the third on the lot block's missing message. The second and the
 * fourth are controls: green before the cure, and they must stay green after it.
 *
 * Round 3 of the designer (the last block; lot R3-a of workstream T, 17/10): each severity in its own state, through
 * `DATA_QUALITY_TONE` — an error in danger, a warning in warning, an info in info; until then an error shared the
 * warning tint. The banner publishes `data-tone`, the tone of its worst group (`groupedSeverity`), and each block its
 * `data-severity` and the `data-tone` of that severity. The block reads those attributes, never a colour class (design
 * system, rule 10), and writes the expected tones out (`TONE_OF`) instead of reading them back from the table. The
 * error is `FIFO_SOURCE_QUANTITY_MISSING` as the engine sends it, `fails_analysis` included: in the panel a FAILED
 * analysis hands it to `LotAnalysisFailedNotice` (J-12), but here the banner is mounted alone and draws what it is
 * given. The engine sends no info today; the banner draws one all the same, so the info borrows
 * `TRANSFER_SHARE_MISMATCH`, an info of the portfolio report: the banner reads a severity, never a code. Red before
 * R3-a: the banner published no `data-tone`, its blocks no `data-severity` and no `data-tone`.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {_} from '$lib/i18n';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
import LotDataQualityBanner from './LotDataQualityBanner.svelte';

const INCOME = 'ASSET_INCOME_NO_ELIGIBLE_LOTS';
const FALLBACK = 'REFERENCE_PRICE_FALLBACK';

const BROKER_ID = 61;

/** The visible lot: 501, opened on 10 January 2024 by an adjustment on a day without a quote. */
const LOT_ID = 501;
const LOT_DATES = new Map<number, string>([[LOT_ID, '2024-01-10']]);

/** An orphan income pool, by what the user must read of it: its amount and its day. */
interface Pool {
    transactionId: number;
    amount: string;
    day: string;
}

/** 12.50 EUR of dividends on 15 March, 30.75 EUR on 20 June: two pools, and no lot eligible for either. */
const MARCH: Pool = {transactionId: 7101, amount: '12.50', day: '2024-03-15'};
const JUNE: Pool = {transactionId: 7102, amount: '30.75', day: '2024-06-20'};
const POOLS: readonly Pool[] = [MARCH, JUNE];

/** A pool's issue as `_build_data_quality_report` serialises it: a warning, with no lot and no related row. */
function orphanIncome(pool: Pool): DataQualityIssue {
    return {
        domain: 'PORTFOLIO',
        code: INCOME,
        severity: 'warning',
        message_i18n_key: 'dataQuality.assetIncomeNoEligibleLots',
        message_params: {transaction_id: pool.transactionId, lot_id: null, broker_id: BROKER_ID, related_transaction_id: null, economic_type: 'DIVIDEND', as_of_date: pool.day, target_amount: pool.amount, target_currency: 'EUR'},
    };
}

/** The lot issue, `REFERENCE_PRICE_FALLBACK`: the engine names the lot by its opening row. */
const LOT_ISSUE: DataQualityIssue = {domain: 'PORTFOLIO', code: FALLBACK, severity: 'warning', message_i18n_key: 'dataQuality.referencePriceFallback', message_params: {transaction_id: LOT_ID, lot_id: LOT_ID, broker_id: BROKER_ID, related_transaction_id: null, reference_price: '101.25'}};

/** The banner's issues in the engine's order: the lot issue during the replay, then the pools by day. */
const ISSUES: DataQualityIssue[] = [LOT_ISSUE, ...POOLS.map(orphanIncome)];

/** Mount the banner on `issues`, ISSUES unless given, with the visible lot; it mounts folded. */
function mount(issues: DataQualityIssue[] = ISSUES): {banner: HTMLElement; toggle: HTMLElement} {
    render(LotDataQualityBanner, {issues, lotDates: LOT_DATES});
    const banner = screen.getByTestId('lot-data-quality-banner');
    return {banner, toggle: within(banner).getByTestId('lot-data-quality-toggle')};
}

/** Unfold the banner: it mounts folded, so the toggle is checked folded, clicked once, and checked unfolded. */
async function unfold(toggle: HTMLElement): Promise<void> {
    expect(toggle, 'mounted folded').toHaveAttribute('aria-expanded', 'false');
    await fireEvent.click(toggle);
    expect(toggle, 'unfolded').toHaveAttribute('aria-expanded', 'true');
}

/** Mount the banner on ISSUES and unfold it. */
async function mountUnfolded(): Promise<HTMLElement> {
    const {banner, toggle} = mount();
    await unfold(toggle);
    return banner;
}

/** The block of `code`. */
function blockOf(banner: HTMLElement, code: string): HTMLElement {
    return within(banner).getByTestId(`lot-data-quality-issue-${code}`);
}

/** The messages a block draws, in document order. */
function messagesIn(block: HTMLElement): HTMLElement[] {
    return within(block).queryAllByTestId('lot-data-quality-message');
}

/** The text an element shows, each run of whitespace read as one space. */
function shown(element: HTMLElement): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
});

describe('LotDataQualityBanner — every orphan pool with its own amount and its own date (J-53)', () => {
    // Red before the cure: the block writes the March pool only, so the June amount is nowhere.
    it('draws one message per orphan pool in the income block, each with its own amount and its own day', async () => {
        // Control: the catalogue writes a pool's amount and day as sent. Were they formatted for a locale, «the message
        // shows its amount» would look for a text the banner never writes.
        for (const pool of POOLS) {
            const sentence = get(_)('dataQuality.assetIncomeNoEligibleLots', {values: orphanIncome(pool).message_params});
            expect(sentence, `control: the catalogue writes ${pool.amount} as sent`).toContain(pool.amount);
            expect(sentence, `control: the catalogue writes ${pool.day} as sent`).toContain(pool.day);
        }

        const block = blockOf(await mountUnfolded(), INCOME);

        // The defect as the user meets it: the block names one pool and hides the other.
        for (const pool of POOLS) {
            expect(shown(block), `the block names the pool of ${pool.day} by its amount`).toContain(pool.amount);
        }
        const messages = messagesIn(block);
        expect(messages, 'one message per pool').toHaveLength(2);
        for (const pool of POOLS) {
            const carrying = messages.filter((message) => shown(message).includes(pool.amount));
            expect(carrying, `one message carries ${pool.amount}`).toHaveLength(1);
            const text = shown(carrying[0]);
            expect(text, `the message of ${pool.amount} carries its own day`).toContain(pool.day);
            for (const other of POOLS.filter((candidate) => candidate !== pool)) {
                expect(text, `the message of ${pool.amount}: nothing of the other pool’s amount`).not.toContain(other.amount);
                expect(text, `the message of ${pool.amount}: nothing of the other pool’s day`).not.toContain(other.day);
            }
        }
    });

    // Control, green before and after the cure: the lines live inside the blocks, still one block per code.
    it('control: draws one block per code — the two pools share one, the lot issue has its own', async () => {
        const banner = await mountUnfolded();

        const blocks = within(banner)
            .queryAllByTestId(/^lot-data-quality-issue-/)
            .map((block) => block.getAttribute('data-testid'));

        expect(blocks.sort()).toEqual([`lot-data-quality-issue-${INCOME}`, `lot-data-quality-issue-${FALLBACK}`].sort());
    });

    // Red before the cure: the lot block writes its sentence, but in no `lot-data-quality-message`.
    it('keeps one message and the lot’s chip in the lot issue’s block, and draws no chip in the pools’ block', async () => {
        const banner = await mountUnfolded();
        const lotBlock = blockOf(banner, FALLBACK);

        // Presence barrier for the absence below: the sibling block draws the lot's chip, a button.
        expect(within(lotBlock).getByTestId(`lot-data-quality-chip-${LOT_ID}`).tagName, 'the lot’s chip').toBe('BUTTON');
        expect(within(blockOf(banner, INCOME)).queryAllByTestId(/^lot-data-quality-chip-/), 'the pools name no lot: no chip').toEqual([]);

        const messages = messagesIn(lotBlock);
        expect(messages, 'one message for the lot issue').toHaveLength(1);
        expect(shown(messages[0]), 'barrier: the message is written').not.toBe('');
        expect(shown(messages[0]), 'barrier: the catalogue resolved its key').not.toBe(LOT_ISSUE.message_i18n_key);
    });

    // Control, green before and after the cure: the header counts categories — two codes — not issues nor lines.
    it('control: the header counts two warning categories, folded and unfolded, not three issues', async () => {
        const twoCategories = get(_)('dataQuality.headerWarnings', {values: {warnings: 2}});
        const threeIssues = get(_)('dataQuality.headerWarnings', {values: {warnings: 3}});
        expect(twoCategories, 'control: the catalogue tells two from three').not.toBe(threeIssues);

        const {toggle} = mount();
        expect(shown(toggle), 'folded').toBe(twoCategories);

        await unfold(toggle);
        expect(shown(toggle), 'unfolded, every line drawn').toBe(twoCategories);
    });
});

// =====================================================================================================================
// Round 3 of the designer (17/10, lot R3-a): the banner in the tone of its worst group, each group in its own

/** The state the designer gives each severity (round 3): written out, never read back from `DATA_QUALITY_TONE`. */
const TONE_OF: Record<DataQualityIssue['severity'], string> = {error: 'danger', warning: 'warning', info: 'info'};

/** A sale 4 units beyond what the broker held on 2 May, as the engine sends it: an error with no lot, failing the replay (J-12). */
const SHORTFALL: DataQualityIssue = {
    domain: 'PORTFOLIO',
    code: 'FIFO_SOURCE_QUANTITY_MISSING',
    severity: 'error',
    message_i18n_key: 'dataQuality.fifoSourceQuantityMissing',
    message_params: {transaction_id: 7201, lot_id: null, broker_id: BROKER_ID, related_transaction_id: null, missing_quantity: '4', transaction_date: '2024-05-02', fails_analysis: true},
};

/** An info: the engine sends none today, so it borrows TRANSFER_SHARE_MISMATCH, an info of the portfolio report. */
const SHARE_NOTE: DataQualityIssue = {domain: 'PORTFOLIO', code: 'TRANSFER_SHARE_MISMATCH', severity: 'info', message_i18n_key: 'dataQuality.transferShareMismatch', message_params: {count: 1}};

/** The tone of the whole banner for each mix of groups. The error comes last, so the tone cannot come from the first issue. */
const TONE_CASES: Array<{name: string; issues: DataQualityIssue[]; tone: string}> = [
    {name: 'an error, a warning and an info', issues: [LOT_ISSUE, SHARE_NOTE, SHORTFALL], tone: 'danger'},
    {name: 'warnings only, the J-53 issues', issues: ISSUES, tone: 'warning'},
    {name: 'an info only', issues: [SHARE_NOTE], tone: 'info'},
];

describe('LotDataQualityBanner — the banner in the tone of its worst group, each group in its own (round 3)', () => {
    it.each(TONE_CASES)('$name: the banner is $tone, and each group carries its own severity and the tone of it', async ({issues, tone}) => {
        const {banner, toggle} = mount(issues);
        expect(banner, 'folded: the tone of the worst group').toHaveAttribute('data-tone', tone);

        await unfold(toggle);
        expect(banner, 'unfolded: still the tone of the worst group').toHaveAttribute('data-tone', tone);

        // One block per code, each read on its own: the issues of a code share its severity.
        const severities = new Map<string, DataQualityIssue['severity']>(issues.map((issue) => [issue.code, issue.severity]));
        const blocks = within(banner)
            .queryAllByTestId(/^lot-data-quality-issue-/)
            .map((block) => block.getAttribute('data-testid'));
        expect(blocks.sort(), 'one block per code, none left out of the reading below').toEqual([...severities.keys()].map((code) => `lot-data-quality-issue-${code}`).sort());
        for (const [code, severity] of severities) {
            const block = blockOf(banner, code);
            expect(block, `${code}: its own severity`).toHaveAttribute('data-severity', severity);
            expect(block, `${code}: the tone of its severity, ${TONE_OF[severity]}`).toHaveAttribute('data-tone', TONE_OF[severity]);
        }
    });
});
