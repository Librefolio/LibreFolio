// @vitest-environment jsdom
/**
 * DataQualityBanner, grouped mode — the button that fixes sits ABOVE what it fixes (workstream T; the developer's
 * decision of 19/10/2026: «if you click here, this is what you fix»).
 *
 * Until then each category of the grouped banner (the Dashboard, the risk panels) drew its message row — severity icon,
 * sentence, FX pairs inline — and UNDER it its action: one aggregate button `data-quality-cta-{code}`, or one chip per
 * asset for `navigate_asset`. The user read the problem first and met the button after it; and `add_fx_pair` and
 * `navigate_fx`, which act on ONE pair at a time (the add dialog opens on one pair, the link goes to one pair), offered
 * a single button for all the pairs of their category.
 *
 * The contract under test, grouped mode only. Every category keeps its container `data-quality-issue-{code}` and takes
 * one of four shapes:
 *   1. one button fixes all of it — `sync_fx_pair`, `sync_asset_prices`, and the per-item actions when they have no item:
 *      the button `data-quality-cta-{code}` FIRST; after it, outside it, a block `data-quality-fixes-{code}` holding the
 *      message row `data-quality-message-{code}` and, when there are items, the items line
 *      `data-quality-fixes-items-{code}`: at most three pairs (flag, code, arrow, flag, code) or three asset names
 *      (comma-separated), then «+N». The button keeps its busy state (`disabled` while `busyCode` is its code);
 *   2. one chip per asset — `navigate_asset` with ids: the message row, then `data-quality-nav-assets-{code}` >
 *      `data-quality-nav-asset-{id}`, each calling `onaction('navigate_asset', String(id), issue)` (unchanged);
 *   3. one chip per pair — `add_fx_pair` and `navigate_fx` with pairs: the message row, without the pairs, then
 *      `data-quality-fx-pairs-{code}` > one `<button>` per pair `data-quality-fx-pair-{slug}`, named «{the action's
 *      label}: BASE/QUOTE», each calling `onaction(action, slug, issue)`; no `data-quality-cta-{code}`;
 *   4. no action: the message row alone.
 * Flat mode (the asset and FX pages) is unchanged: one banner per issue, one aggregate button.
 *
 * The tests:
 *   - DQL-01 (both one-button actions) and DQL-02 (the three per-item actions, given no item): the button precedes the
 *     message and every item, outside the block that holds them; the items line shows the first three and «+N», never
 *     the fourth, and lists each pair once; the click still acts on the whole category, with the backend's target;
 *   - DQL-03: the moved button keeps its busy state — disabled while its code is busy, only its own — and its place;
 *   - DQL-04 (both per-pair actions): one button per pair and none for all of them, each after the message; the k-th
 *     acts on the k-th pair — never null, never the backend's target, never always the first;
 *   - DQL-05 (control): the per-asset chips, after the message, each opening its own asset;
 *   - DQL-06: every category in one banner — each in its shape inside its own container, every button and every
 *     sentence of the banner in exactly one category, an aggregate button only where one button fixes all of it, and
 *     none between a category's message and its items;
 *   - DQL-07 (control): flat, the per-pair actions still draw one aggregate button, and no chip.
 *
 * The fixtures are the issues as `backend/app/services/financial_math/portfolio/data_quality.py` serialises them: the
 * slugs with their two codes sorted (`normalize_fx_pair_slug`), listed sorted; the target of the sync and of the manual
 * pairs is their first pair, the add has none. Two categories share the code MISSING_FX_RATES (the synced and the
 * manual pairs), so their containers share a `data-testid`: a category is found by the sentence it writes, never by its
 * index. DQL-02's issues are those fixtures with their items emptied: the backend sends none such today, the contract
 * still gives them their one button.
 *
 * What it reads: `data-testid`s; document order (`compareDocumentPosition`), which is the subject of the change; the
 * buttons a category holds, compared as sorted lists since their order is not; the arguments of `onaction`. The sentence
 * and the action labels are resolved through the i18n the banner uses (`get(_)`), never written out, and no colour
 * class is read (design system, rule 10).
 *
 * Red before the change: DQL-01, DQL-02, DQL-03 and DQL-06 on «the button comes before the message of what it fixes» —
 * it followed it; DQL-04 on the buttons of the category, one aggregate `data-quality-cta-{code}` where one chip per pair
 * is due. DQL-05 and DQL-07 are controls: green before the change, and they must stay green after it.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {_} from '$lib/i18n';
import type {DataQualityIssue} from './DataQualityBanner.svelte';
import DataQualityBanner from './DataQualityBanner.svelte';

/** The banner's `onaction`: the action, its target, the issue. */
type OnAction = (action: string, target: string | null, issue: DataQualityIssue) => void;

/** The four shapes a category of the grouped banner takes. */
type Shape = 'one button' | 'one chip per asset' | 'one chip per pair' | 'no action';

/** What a category draws, once located: the element writing its sentence, and its items (its items line, or its chips). */
interface Drawn {
    message: Element;
    items: Element[];
}

// --- Fixtures: the issues as the backend serialises them ------------------------------------------------------------

/** Two pairs served by a provider, rates missing on nine days: one sync fetches both; the first pair is the target. */
const SYNC_FX: DataQualityIssue = {
    domain: 'portfolio',
    code: 'MISSING_FX_RATES',
    severity: 'warning',
    message_i18n_key: 'dataQuality.missingFxRates',
    message_params: {count: 2, date_from: '2026-03-02', date_to: '2026-03-13', dates_count: 9},
    count: 2,
    affected_asset_ids: [],
    affected_asset_names: [],
    affected_fx_pairs: ['EUR-USD', 'GBP-JPY'],
    cta_action: 'sync_fx_pair',
    cta_target: 'EUR-USD',
    group_key: 'missing_fx_rates',
};

/** Four assets with outdated prices: one sync refreshes all four; the first asset is the target. */
const STALE: DataQualityIssue = {
    domain: 'portfolio',
    code: 'STALE_PRICE',
    severity: 'warning',
    message_i18n_key: 'dataQuality.stalePrice',
    message_params: {count: 4},
    count: 4,
    affected_asset_ids: [201, 202, 203, 204],
    affected_asset_names: ['Acme Corp', 'Borealis Fund', 'Cobalt ETF', 'Delta Bond'],
    affected_fx_pairs: [],
    cta_action: 'sync_asset_prices',
    cta_target: '201',
    group_key: 'stale_price',
};

/** Two pairs with no route: the add dialog opens on one pair at a time, so the backend names no target. */
const ADD_FX: DataQualityIssue = {
    domain: 'portfolio',
    code: 'MISSING_FX_MARKET',
    severity: 'warning',
    message_i18n_key: 'dataQuality.missingFx',
    message_params: {count: 2},
    count: 2,
    affected_asset_ids: [],
    affected_asset_names: [],
    affected_fx_pairs: ['CHF-SEK', 'NOK-USD'],
    cta_action: 'add_fx_pair',
    cta_target: null,
    group_key: 'missing_fx',
};

/** Two manual pairs with missing rates: their page opens one pair at a time; the first pair is the target. */
const MANUAL_FX: DataQualityIssue = {
    domain: 'portfolio',
    code: 'MISSING_FX_RATES',
    severity: 'warning',
    message_i18n_key: 'dataQuality.missingFxRatesManual',
    message_params: {count: 2},
    count: 2,
    affected_asset_ids: [],
    affected_asset_names: [],
    affected_fx_pairs: ['AUD-NZD', 'CAD-HKD'],
    cta_action: 'navigate_fx',
    cta_target: 'AUD-NZD',
    group_key: 'missing_fx_rates_manual',
};

/** Two assets with no market price: an error, with a way to each asset; the first asset is the target. */
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

/** One asset with a split of an invalid ratio: the banner has nothing to do about it, the user fixes the split in the asset's events. */
const INVALID_SPLIT: DataQualityIssue = {
    domain: 'portfolio',
    code: 'INVALID_SPLIT_RATIO',
    severity: 'warning',
    message_i18n_key: 'dataQuality.invalidSplitRatio',
    message_params: {count: 1},
    count: 1,
    affected_asset_ids: [],
    affected_asset_names: [],
    affected_fx_pairs: [],
    cta_action: null,
    cta_target: null,
    group_key: 'invalid_split_ratio',
};

/** The three actions that act on one item at a time, given no item: their one button stands in for the chips. */
const NO_ITEMS: DataQualityIssue[] = [MISSING_PRICE, ADD_FX, MANUAL_FX].map((issue) => ({...issue, affected_asset_ids: [], affected_asset_names: [], affected_fx_pairs: []}));

/** Every category of DQL-06 and its shape, written out — never derived from the action by the rule under test. */
const SHAPES: Array<{issue: DataQualityIssue; shape: Shape}> = [
    {issue: SYNC_FX, shape: 'one button'},
    {issue: STALE, shape: 'one button'},
    {issue: ADD_FX, shape: 'one chip per pair'},
    {issue: MANUAL_FX, shape: 'one chip per pair'},
    {issue: MISSING_PRICE, shape: 'one chip per asset'},
    {issue: INVALID_SPLIT, shape: 'no action'},
];

/** The same issues, mounted in another order: the banner sorts them by severity, so nothing may lean on this list's. */
const MOUNTED: DataQualityIssue[] = [STALE, INVALID_SPLIT, MANUAL_FX, MISSING_PRICE, ADD_FX, SYNC_FX];

// --- Helpers ---------------------------------------------------------------------------------------------------------

/** The text an element shows, each run of whitespace read as one space. */
function shown(element: Element): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** An issue as the messages below name it: its code and its action. */
function nameOf(issue: DataQualityIssue): string {
    return `${issue.code} (${issue.cta_action ?? 'no action'})`;
}

/** The sentence the banner writes for an issue, resolved through the i18n it uses: never written out here. */
function sentenceOf(issue: DataQualityIssue): string {
    const sentence = get(_)(issue.message_i18n_key, {values: issue.message_params ?? {}});
    expect(sentence, `barrier: the catalogue resolves ${issue.message_i18n_key}`).not.toBe(issue.message_i18n_key);
    return sentence.replace(/\s+/g, ' ').trim();
}

/** The label of an action's button, resolved through the i18n the banner uses. */
function labelOf(action: string): string {
    const key = `dataQuality.cta.${action}`;
    const label = get(_)(key);
    expect(label, `barrier: the catalogue resolves ${key}`).not.toBe(key);
    return label;
}

/** `a` comes before `b` in document order, and is not its ancestor. */
function precedes(a: Node, b: Node): boolean {
    return !a.contains(b) && (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/** The `data-testid` of every button in `scope`, sorted: what the user can press there, whatever its order. */
function buttonsIn(scope: Element): string[] {
    return [...scope.querySelectorAll('button')].map((button) => button.getAttribute('data-testid') ?? '(a button with no data-testid)').sort();
}

/** The two codes of a pair slug as the backend writes it, `CHF-SEK`. */
function codesOf(slug: string): [string, string] {
    const [base, quote] = slug.split('-');
    return [base, quote];
}

/** A pair as the banner draws it: its base code, then its quote code, with only flags, an arrow or spaces between. */
function drawnPair(slug: string): RegExp {
    const [base, quote] = codesOf(slug);
    return new RegExp(`${base}[^A-Za-z]*${quote}`);
}

/** Mount the grouped banner and unfold it — it mounts folded —, then return its container. */
async function mountUnfolded(issues: DataQualityIssue[], extra: {onaction?: OnAction; busyCode?: string | null} = {}): Promise<HTMLElement> {
    render(DataQualityBanner, {issues, mode: 'grouped', ...extra});
    const banner = screen.getByTestId('data-quality-banner');
    const toggle = within(banner).getByTestId('data-quality-toggle');
    expect(toggle, 'mounted folded').toHaveAttribute('aria-expanded', 'false');
    await fireEvent.click(toggle);
    expect(toggle, 'unfolded').toHaveAttribute('aria-expanded', 'true');
    return banner;
}

/** The category of an issue: of the containers of its code, the one writing its sentence — two share MISSING_FX_RATES. */
function categoryOf(banner: HTMLElement, issue: DataQualityIssue): HTMLElement {
    const sentence = sentenceOf(issue);
    const writing = within(banner)
        .getAllByTestId(`data-quality-issue-${issue.code}`)
        .filter((container) => shown(container).includes(sentence));
    expect(writing, `${nameOf(issue)}: one category writes its sentence`).toHaveLength(1);
    return writing[0];
}

/** The element writing an issue's sentence: the deepest of `scope` whose text holds it. Found the same way before and after the change. */
function messageIn(scope: Element, issue: DataQualityIssue): Element {
    const sentence = sentenceOf(issue);
    const holding = [...scope.querySelectorAll('*')].filter((element) => shown(element).includes(sentence));
    const deepest = holding.filter((element) => !holding.some((other) => other !== element && element.contains(other)));
    expect(deepest, `${nameOf(issue)}: one element writes the sentence`).toHaveLength(1);
    return deepest[0];
}

/** After the first three items, «+N» closes the line; with three or fewer, nothing is counted. */
function expectMore(line: string, count: number, issue: DataQualityIssue): void {
    if (count <= 3) {
        expect(line, `${nameOf(issue)}: ${count} item(s), nothing more to count`).not.toMatch(/\+\d/);
        return;
    }
    expect(line, `${nameOf(issue)}: «+${count - 3}» after the first three`).toMatch(new RegExp(`\\+${count - 3}$`));
}

/** Shape 1 — one button fixes all of it: the button first; after it, outside it, the block of what it fixes. */
function expectOneButton(category: HTMLElement, issue: DataQualityIssue): Drawn {
    const code = issue.code;
    expect(buttonsIn(category), `${nameOf(issue)}: one button, for the whole category`).toEqual([`data-quality-cta-${code}`]);
    const cta = within(category).getByTestId(`data-quality-cta-${code}`);
    const message = messageIn(category, issue);
    // The decision of 19/10. Red before it: the button followed the message.
    expect(precedes(cta, message), `${nameOf(issue)}: the button comes before the message of what it fixes`).toBe(true);

    const fixes = within(category).getByTestId(`data-quality-fixes-${code}`);
    expect(fixes.contains(cta), `${nameOf(issue)}: the button sits above the block of what it fixes, not inside it`).toBe(false);
    const messageRow = within(fixes).getByTestId(`data-quality-message-${code}`);
    expect(messageRow.contains(message), `${nameOf(issue)}: the message row of the block writes the sentence`).toBe(true);

    const pairs = issue.affected_fx_pairs ?? [];
    const names = issue.affected_asset_names ?? [];
    if (pairs.length === 0 && names.length === 0) {
        // Asked inside the block proven drawn above, message row included.
        expect(within(category).queryByTestId(`data-quality-fixes-items-${code}`), `${nameOf(issue)}: no item, no items line`).toBeNull();
        return {message, items: []};
    }
    const line = within(fixes).getByTestId(`data-quality-fixes-items-${code}`);
    expect(precedes(cta, line), `${nameOf(issue)}: the button comes before the items it fixes`).toBe(true);
    expect(precedes(messageRow, line), `${nameOf(issue)}: the items follow the message`).toBe(true);
    const text = shown(line);
    if (pairs.length > 0) {
        for (const pair of pairs.slice(0, 3)) {
            expect(text, `${nameOf(issue)}: the items line shows ${pair}`).toMatch(drawnPair(pair));
            expect(shown(messageRow), `${nameOf(issue)}: ${pair} listed once, in the items line`).not.toMatch(drawnPair(pair));
        }
        for (const pair of pairs.slice(3)) expect(shown(category), `${nameOf(issue)}: three pairs at most, not ${pair}`).not.toMatch(drawnPair(pair));
        expectMore(text, pairs.length, issue);
    } else {
        expect(text, `${nameOf(issue)}: the first three names, comma-separated`).toContain(names.slice(0, 3).join(', '));
        for (const name of names.slice(3)) expect(shown(category), `${nameOf(issue)}: three names at most, not ${name}`).not.toContain(name);
        expectMore(text, names.length, issue);
    }
    return {message, items: [line]};
}

/** Shape 2 — one chip per asset, unchanged: the message, then a chip per asset, showing its name. */
function expectChipPerAsset(category: HTMLElement, issue: DataQualityIssue): Drawn {
    const ids = issue.affected_asset_ids ?? [];
    const names = issue.affected_asset_names ?? [];
    expect(buttonsIn(category), `${nameOf(issue)}: one button per asset, none for all of them`).toEqual(ids.map((id) => `data-quality-nav-asset-${id}`).sort());
    const message = messageIn(category, issue);
    const line = within(category).getByTestId(`data-quality-nav-assets-${issue.code}`);
    const chips = ids.map((id, index) => {
        const chip = within(line).getByTestId(`data-quality-nav-asset-${id}`);
        expect(precedes(message, chip), `${nameOf(issue)}: the chip of asset ${id} comes after the message`).toBe(true);
        expect(shown(chip), `${nameOf(issue)}: the chip of asset ${id} shows its name`).toContain(names[index]);
        return chip;
    });
    return {message, items: chips};
}

/** Shape 3 — one chip per pair: the message, without the pairs, then one button per pair, named after its action and its pair. */
function expectChipPerPair(category: HTMLElement, issue: DataQualityIssue): Drawn {
    const code = issue.code;
    const pairs = issue.affected_fx_pairs ?? [];
    // Red before the change: one aggregate `data-quality-cta-{code}` stood where a chip per pair is due.
    expect(buttonsIn(category), `${nameOf(issue)}: one button per pair, none for all of them`).toEqual(pairs.map((pair) => `data-quality-fx-pair-${pair}`).sort());
    const message = messageIn(category, issue);
    const messageRow = within(category).getByTestId(`data-quality-message-${code}`);
    expect(messageRow.contains(message), `${nameOf(issue)}: the message row writes the sentence`).toBe(true);
    const line = within(category).getByTestId(`data-quality-fx-pairs-${code}`);
    const label = labelOf(issue.cta_action ?? '');
    const chips = pairs.map((pair) => {
        const [base, quote] = codesOf(pair);
        const chip = within(line).getByTestId(`data-quality-fx-pair-${pair}`);
        expect(chip.tagName, `${nameOf(issue)}: the chip of ${pair} is a button`).toBe('BUTTON');
        expect(precedes(message, chip), `${nameOf(issue)}: the chip of ${pair} comes after the message`).toBe(true);
        expect(shown(chip), `${nameOf(issue)}: the chip of ${pair} shows its pair`).toMatch(drawnPair(pair));
        expect(chip, `${nameOf(issue)}: the chip of ${pair} says what it does, and to which pair`).toHaveAccessibleName(`${label}: ${base}/${quote}`);
        expect(shown(messageRow), `${nameOf(issue)}: ${pair} listed once, on its chip`).not.toMatch(drawnPair(pair));
        return chip;
    });
    return {message, items: chips};
}

/** Shape 4 — no action: the message row alone, nothing to press. */
function expectNoAction(category: HTMLElement, issue: DataQualityIssue): Drawn {
    expect(buttonsIn(category), `${nameOf(issue)}: nothing to press`).toEqual([]);
    const message = messageIn(category, issue);
    const messageRow = within(category).getByTestId(`data-quality-message-${issue.code}`);
    expect(messageRow.contains(message), `${nameOf(issue)}: the message row writes the sentence`).toBe(true);
    return {message, items: []};
}

const EXPECT_SHAPE: Record<Shape, (category: HTMLElement, issue: DataQualityIssue) => Drawn> = {
    'one button': expectOneButton,
    'one chip per asset': expectChipPerAsset,
    'one chip per pair': expectChipPerPair,
    'no action': expectNoAction,
};

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('DataQualityBanner, grouped — the button that fixes sits above what it fixes (19/10)', () => {
    it.each([SYNC_FX, STALE])('DQL-01: $code ($cta_action), one button fixes all of it: the button first, then the message and its items in data-quality-fixes', async (issue) => {
        const onaction = vi.fn<OnAction>();
        const banner = await mountUnfolded([issue], {onaction});
        const category = categoryOf(banner, issue);
        expectOneButton(category, issue);

        // Unchanged: the button acts on the whole category, with the target the backend chose.
        await fireEvent.click(within(category).getByTestId(`data-quality-cta-${issue.code}`));
        expect(onaction).toHaveBeenCalledTimes(1);
        expect(onaction).toHaveBeenCalledWith(issue.cta_action, issue.cta_target, issue);
    });

    it.each(NO_ITEMS)('DQL-02: $code ($cta_action) with no item to act on: its one button, above the message, and no items line', async (issue) => {
        const onaction = vi.fn<OnAction>();
        const banner = await mountUnfolded([issue], {onaction});
        const category = categoryOf(banner, issue);
        expectOneButton(category, issue);

        await fireEvent.click(within(category).getByTestId(`data-quality-cta-${issue.code}`));
        expect(onaction).toHaveBeenCalledTimes(1);
        expect(onaction).toHaveBeenCalledWith(issue.cta_action, issue.cta_target ?? null, issue);
    });

    it('DQL-03: the one button keeps its busy state above the message: disabled while its own code is busy, and only its own', async () => {
        const banner = await mountUnfolded([SYNC_FX, STALE], {busyCode: STALE.code});

        expect(within(categoryOf(banner, SYNC_FX)).getByTestId(`data-quality-cta-${SYNC_FX.code}`), 'control: the other category’s button stays enabled').toBeEnabled();
        const category = categoryOf(banner, STALE);
        const busy = within(category).getByTestId(`data-quality-cta-${STALE.code}`);
        expect(busy, 'busy: disabled until its action ends').toBeDisabled();
        expect(precedes(busy, messageIn(category, STALE)), 'busy, the button still comes before the message of what it fixes').toBe(true);
    });

    it.each([ADD_FX, MANUAL_FX])('DQL-04: $code ($cta_action), acting on one pair at a time: the message, then one chip per pair, each acting on its own pair', async (issue) => {
        const onaction = vi.fn<OnAction>();
        const banner = await mountUnfolded([issue], {onaction});
        const {items: chips} = expectChipPerPair(categoryOf(banner, issue), issue);

        // From the last chip to the first: a chip acting on the backend's target, on null or on the first pair fails at once.
        const pairs = issue.affected_fx_pairs ?? [];
        for (const [k, pair] of [...pairs.entries()].reverse()) {
            await fireEvent.click(chips[k]);
            expect(onaction, `the chip of ${pair} acts on ${pair}`).toHaveBeenLastCalledWith(issue.cta_action, pair, issue);
        }
        expect(onaction).toHaveBeenCalledTimes(pairs.length);
    });

    // Control, green before the change and after it.
    it('DQL-05 (control): MISSING_PRICE (navigate_asset), one chip per asset as before: after the message, each opening its own asset', async () => {
        const onaction = vi.fn<OnAction>();
        const banner = await mountUnfolded([MISSING_PRICE], {onaction});
        const {items: chips} = expectChipPerAsset(categoryOf(banner, MISSING_PRICE), MISSING_PRICE);

        const ids = MISSING_PRICE.affected_asset_ids ?? [];
        for (const [k, id] of [...ids.entries()].reverse()) {
            await fireEvent.click(chips[k]);
            expect(onaction, `the chip of asset ${id} opens asset ${id}`).toHaveBeenLastCalledWith('navigate_asset', String(id), MISSING_PRICE);
        }
        expect(onaction).toHaveBeenCalledTimes(ids.length);
    });

    it('DQL-06: every category in one banner, each in its shape inside its own container, and no aggregate button between a category’s message and its items', async () => {
        const banner = await mountUnfolded(MOUNTED);
        const categories = SHAPES.map(({issue}) => categoryOf(banner, issue));
        const drawn = SHAPES.map(({issue, shape}, k) => EXPECT_SHAPE[shape](categories[k], issue));

        // Every button of the banner but its toggle, and every sentence, in exactly one category: its own.
        const toggle = within(banner).getByTestId('data-quality-toggle');
        for (const button of [...banner.querySelectorAll('button')].filter((element) => element !== toggle)) {
            expect(
                categories.filter((category) => category.contains(button)),
                `${button.getAttribute('data-testid')}: in exactly one category`,
            ).toHaveLength(1);
        }
        drawn.forEach(({message}, k) => {
            expect(
                categories.filter((category) => category.contains(message)),
                `${nameOf(SHAPES[k].issue)}: its sentence in its own category only`,
            ).toHaveLength(1);
        });

        // An aggregate button only where one button fixes all of it…
        const ctas = within(banner).queryAllByTestId(/^data-quality-cta-/);
        expect(ctas.map((cta) => cta.getAttribute('data-testid')).sort(), 'the aggregate buttons: one per one-button category, none elsewhere').toEqual(
            SHAPES.filter(({shape}) => shape === 'one button')
                .map(({issue}) => `data-quality-cta-${issue.code}`)
                .sort(),
        );
        // …and none between what a category says and what it lists: each sits above its own message.
        drawn.forEach(({message, items}, k) => {
            for (const item of items) {
                const between = ctas.filter((cta) => precedes(message, cta) && precedes(cta, item));
                expect(
                    between.map((cta) => cta.getAttribute('data-testid')),
                    `${nameOf(SHAPES[k].issue)}: no aggregate button between its message and its items`,
                ).toEqual([]);
            }
        });
    });
});

// =====================================================================================================================
describe('DataQualityBanner, flat — unchanged', () => {
    // Control, green before the change and after it.
    it.each([ADD_FX, MANUAL_FX])('DQL-07 (control): $code ($cta_action), flat: one button for the issue as before, and no chip per pair', async (issue) => {
        const onaction = vi.fn<OnAction>();
        render(DataQualityBanner, {issues: [issue], mode: 'flat', onaction});

        const banner = screen.getByTestId(`data-quality-issue-${issue.code}`);
        expect(buttonsIn(banner), 'one aggregate button, for every pair').toEqual([`data-quality-cta-${issue.code}`]);
        // Asked once the aggregate button is proven drawn, above.
        expect(screen.queryAllByTestId(/^data-quality-fx-pairs?-/), 'no chip per pair').toEqual([]);

        await fireEvent.click(within(banner).getByTestId(`data-quality-cta-${issue.code}`));
        expect(onaction).toHaveBeenCalledTimes(1);
        expect(onaction).toHaveBeenCalledWith(issue.cta_action, issue.cta_target ?? null, issue);
    });
});
