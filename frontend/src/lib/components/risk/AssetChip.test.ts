// @vitest-environment jsdom
/**
 * AssetChip — component test (Vitest + jsdom).
 *
 * The Asset Global laboratory's selection chip, made a component of its own so that the
 * Dashboard's banner can mount the same pill. Two hosts now rely on one contract, and it is
 * pinned here, once, rather than in each of them:
 *
 *   - the variant, published as `data-variant` (`default` when none is given), and what an
 *     excluded asset looks like: its name struck through, its icon faded, nothing else;
 *   - the icon: the asset's own, else its type's, else the `other` one; and a broken one is
 *     hidden without leaving a hole in the pill;
 *   - what the caller hands over: the help cursor, the testid, any `data-*` attribute (the lab
 *     puts its verdict there), and a trailing snippet after the name (the lab's ✕).
 *
 * **Handles.** `data-variant`, `data-testid` and the caller's `data-*`, plus the asset's own name,
 * which is fixture data and never a translation: the chip carries no text of its own. jsdom
 * applies no stylesheet, so three visual properties are read as classes, and only these three:
 * the struck-through name and the faded icon of an excluded asset, and the help cursor, which has
 * no other handle. The variant's colours are not read at all; `data-variant` stands for them.
 *
 * Left elsewhere: the lab's chips end to end — the verdict in `data-level` / `data-reasons`, the ✕
 * that removes an asset — in `e2e/portfolio/risk-lab.spec.ts`.
 */
import {describe, expect, it} from 'vitest';
import {createRawSnippet, type ComponentProps} from 'svelte';

import {fireEvent, render, screen, within} from '$test/component';
import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
import AssetChip from './AssetChip.svelte';

type ChipProps = ComponentProps<typeof AssetChip>;
type ChipAsset = ChipProps['asset'];

const TEST_ID = 'probe-chip';
const VARIANTS = ['default', 'warning', 'excluded'] as const;

// Invented: an asset with an icon of its own and a type whose icon is not the `other` one.
const NAME = 'Invented Holding A';
const OWN_ICON = '/uploads/invented-holding-a.png';
const TYPE = 'ETF';
const ASSET: ChipAsset = {id: 21, display_name: NAME, icon_url: OWN_ICON, asset_type: TYPE};

/** The asset with no usable icon of its own — absent, null or empty — and its type still known. */
const WITHOUT_OWN_ICON: ReadonlyArray<[string, ChipAsset]> = [
    ['has no icon_url', {id: 21, display_name: NAME, asset_type: TYPE}],
    ['has a null icon_url', {...ASSET, icon_url: null}],
    ['has an empty icon_url', {...ASSET, icon_url: ''}],
];

/** The asset with neither an icon of its own nor a type. */
const WITHOUT_ICON_OR_TYPE: ReadonlyArray<[string, ChipAsset]> = [
    ['no type', {id: 21, display_name: NAME}],
    ['a null type', {id: 21, display_name: NAME, icon_url: null, asset_type: null}],
];

/** The chip mounted with the fixture asset and the probe testid, unless told otherwise. */
function mount(overrides: Partial<ChipProps> = {}) {
    const view = render(AssetChip, {props: {asset: ASSET, testId: TEST_ID, ...overrides}});
    return {view, pill: screen.getByTestId(TEST_ID)};
}

/** The pill's icon, which must be exactly one. */
function iconOf(pill: HTMLElement): HTMLImageElement {
    const icons = pill.querySelectorAll('img');
    expect(icons, 'the chip must draw exactly one icon').toHaveLength(1);
    return icons[0];
}

/** The element whose own text is the asset's name. */
function nameOf(pill: HTMLElement, name = NAME): HTMLElement {
    return within(pill).getByText(name);
}

/** What an excluded chip looks like, read as the two classes that draw it. */
function expectExcludedLook(pill: HTMLElement, excluded: boolean): void {
    if (excluded) {
        expect(nameOf(pill), 'an excluded asset keeps its name on screen, struck through').toHaveClass('line-through');
        expect(iconOf(pill), 'an excluded asset keeps its icon, faded').toHaveClass('opacity-50');
    } else {
        expect(nameOf(pill), 'only an excluded asset has its name struck through').not.toHaveClass('line-through');
        expect(iconOf(pill), 'only an excluded asset has its icon faded').not.toHaveClass('opacity-50');
    }
}

describe('AssetChip — the variant', () => {
    it('publishes "default" when no variant is given, and looks like it', () => {
        const {pill} = mount();

        expect(pill).toHaveAttribute('data-variant', 'default');
        expectExcludedLook(pill, false);
    });

    it.each(VARIANTS)('publishes %s as data-variant', (variant) => {
        const {pill} = mount({variant});

        expect(pill).toHaveAttribute('data-variant', variant);
    });

    it.each(VARIANTS)('%s: strikes the name through and fades the icon only for an excluded asset', (variant) => {
        const {pill} = mount({variant});

        expectExcludedLook(pill, variant === 'excluded');
    });

    it('repaints when the variant changes after mount, as a lab chip does when its verdict lands', () => {
        // The lab draws its chips before the eligibility engine answers, then hands them the
        // verdict: a variant read once at mount would leave every chip as it was born.
        const {view, pill} = mount();
        expectExcludedLook(pill, false);

        view.rerender({variant: 'excluded'});
        expect(pill).toHaveAttribute('data-variant', 'excluded');
        expectExcludedLook(pill, true);

        view.rerender({variant: 'warning'});
        expect(pill).toHaveAttribute('data-variant', 'warning');
        expectExcludedLook(pill, false);
    });
});

describe('AssetChip — the icon', () => {
    it("draws the asset's own icon when it has one, as a decoration beside the name", () => {
        const {pill} = mount();
        const icon = iconOf(pill);

        expect(icon).toHaveAttribute('src', OWN_ICON);
        // The name says what the asset is; an alt text would say it a second time.
        expect(icon).toHaveAttribute('alt', '');
    });

    it.each(WITHOUT_OWN_ICON)("draws its type's icon when the asset %s", (_case, asset) => {
        // The premise: the type has an icon of its own, so this case cannot pass on the fallback below.
        expect(getAssetTypeIconUrl(TYPE)).not.toBe(getAssetTypeIconUrl('OTHER'));

        const {pill} = mount({asset});

        expect(iconOf(pill)).toHaveAttribute('src', getAssetTypeIconUrl(TYPE));
    });

    it.each(WITHOUT_ICON_OR_TYPE)('draws the "other" icon for an asset with no icon and %s', (_case, asset) => {
        const {pill} = mount({asset});

        expect(iconOf(pill)).toHaveAttribute('src', getAssetTypeIconUrl('OTHER'));
    });

    it('hides a broken icon, keeping its place in the pill and the name beside it', async () => {
        const {pill} = mount({asset: {...ASSET, icon_url: '/uploads/invented-missing.png'}});
        const icon = iconOf(pill);
        // The premise: the icon is shown until it fails, so hiding it is the failure's doing.
        expect(icon).toBeVisible();

        await fireEvent.error(icon);

        expect(icon, 'a broken icon must not draw the browser broken-image glyph').not.toBeVisible();
        // Hidden, not removed and not `display: none`: it keeps its box, so the pill does not change shape.
        expect(icon).toHaveStyle({visibility: 'hidden'});
        expect(icon).toBeInTheDocument();
        expect(nameOf(pill), 'the chip still names the asset').toBeVisible();
    });
});

describe('AssetChip — what the caller passes', () => {
    it.each([
        {help: true, variant: 'default', cursor: true},
        {help: true, variant: 'warning', cursor: true},
        {help: false, variant: 'warning', cursor: false},
        {help: false, variant: 'excluded', cursor: false},
        {help: undefined, variant: 'default', cursor: false},
    ] as const)('help=$help on a $variant chip: help cursor $cursor — the variant does not imply it', ({help, variant, cursor}) => {
        const {pill} = mount({help, variant});

        if (cursor) expect(pill).toHaveClass('cursor-help');
        else expect(pill).not.toHaveClass('cursor-help');
    });

    it('puts testId on the pill as data-testid', () => {
        const {pill} = mount();

        // The pill itself: the element that publishes the variant and holds the icon and the name.
        expect(pill).toHaveAttribute('data-variant');
        expect(iconOf(pill).parentElement).toBe(pill);
        expect(nameOf(pill).parentElement).toBe(pill);
    });

    it('leaves data-testid off without a testId, rather than writing "undefined"', () => {
        const {container} = render(AssetChip, {props: {asset: ASSET}});
        const pill = container.querySelector<HTMLElement>('[data-variant]');

        expect(pill, 'the chip did not render').not.toBeNull();
        expect(pill).not.toHaveAttribute('data-testid');
    });

    it('passes the data-* attributes it is given to the pill', () => {
        // The lab's own use: the engine's verdict, read by its end-to-end tests.
        const {pill} = mount({'data-level': 'ineligible', 'data-reasons': 'no_prices starts_late'});

        expect(pill).toHaveAttribute('data-level', 'ineligible');
        expect(pill).toHaveAttribute('data-reasons', 'no_prices starts_late');
    });

    it('renders trailing inside the pill, after the name', () => {
        const trailing = createRawSnippet(() => ({render: () => '<button type="button" data-testid="probe-trailing">x</button>'}));
        const {pill} = mount({trailing});

        const after = within(pill).getByTestId('probe-trailing');
        expect([...pill.children], 'the pill reads icon, name, then what the caller put after it').toEqual([iconOf(pill), nameOf(pill), after]);
    });

    it('renders nothing after the name without trailing', () => {
        const {pill} = mount();

        expect([...pill.children]).toEqual([iconOf(pill), nameOf(pill)]);
    });

    it("prints the asset's name as text, never as markup: names are user data", () => {
        const name = 'Holding <b>B</b> & <img src=x> Co';
        const {pill} = mount({asset: {...ASSET, display_name: name}});

        expect(nameOf(pill, name).textContent, 'the name must read exactly as stored').toBe(name);
        expect(pill.querySelector('b'), 'the name was parsed as markup').toBeNull();
        expect(pill.querySelectorAll('img'), 'the name was parsed as markup: it drew an image of its own').toHaveLength(1);
    });
});
