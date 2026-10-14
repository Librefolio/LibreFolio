// @vitest-environment jsdom
/**
 * AssetTypeSelect — the type field of the asset dialog (T7: R14 + R15, with the icons of R16).
 *
 * The real tree (`buildAssetTypeTree()` over the real tables) mounted in the real component: base
 * types at the root, the ETF and crowdfunding families as groups that open, every row and the
 * closed trigger drawn with the icon the rest of the app draws — for a subtype, the composite of
 * its container and its content. What the tables must say is held by `assetTypeTables.test.ts`;
 * what the generic mechanics do, by `TreeSelect.test.ts`. This file pins the assembly, with the
 * literal file names a user's browser actually requests.
 *
 * Needs `src/lib/api/generated.ts` (the module imports the generated client), like the dialog.
 *
 * Nothing here reads a translated word: rows are found by test id, icons by `src`, the search
 * uses an enum value (no label in any language spells `real_estate` with an underscore), and the
 * placeholder is a string this file passes in. The hint of a family's generic member is found by
 * its own test id, `asset-type-tree-hint-{TYPE}`, and only its presence is ever asserted. The bound
 * value sits in a `$state` (`reactiveBox`), as a parent's `bind:value` would: the modal writes it
 * after mount, and the trigger must follow.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {reactiveBox} from '$test/runes.svelte';
import {ASSET_TYPE_FAMILY} from '$lib/utils/assetTypes';
import AssetTypeSelect from './AssetTypeSelect.svelte';

/** The test id the asset dialog gives the field. */
const TEST_ID = 'asset-modal-type';
const PLACEHOLDER = 'Pick an asset type';

const icon = (file: string) => `/icons/asset-types/${file}.png`;

/** Types that specialise nothing: the root of the select. A subset on purpose — a new base type must not break this file. */
const BASE_TYPES = ['STOCK', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'COMMODITY', 'REAL_ESTATE', 'INDEX', 'OTHER'];

/** The six ETF subtypes and the composite each is drawn with: the ETF tag plus the pastille of what it holds. */
const ETF_COMPOSITES: Record<string, string> = {
    ETF_STOCK: 'etf-stock',
    ETF_BOND: 'etf-bond',
    ETF_COMMODITY: 'etf-commodity',
    ETF_REAL_ESTATE: 'etf-real-estate',
    ETF_CRYPTO: 'etf-crypto',
    // D67: a money-market fund contains no base type, and borrows the pastille of the cash bucket.
    ETF_MONETARY: 'etf-liquidity',
};

function mount(value: string) {
    const onchange = vi.fn();
    // The parent's `$state` behind `bind:value`, as in AssetModal: `bind:value={assetType}`.
    const bound = reactiveBox({value});
    render(AssetTypeSelect, {
        testId: TEST_ID,
        placeholder: PLACEHOLDER,
        onchange,
        get value() {
            return bound.value;
        },
        set value(next: string) {
            bound.value = next;
        },
    });
    return {onchange, bound, trigger: screen.getByTestId(`${TEST_ID}-button`)};
}

function root(): HTMLElement {
    return screen.getByTestId(TEST_ID);
}

function group(family: string): HTMLElement {
    return within(root()).getByTestId(`asset-type-tree-group-${family}`);
}

function option(type: string): HTMLElement {
    return within(root()).getByTestId(`asset-type-tree-option-${type}`);
}

function queryOption(type: string): HTMLElement | null {
    return within(root()).queryByTestId(`asset-type-tree-option-${type}`);
}

/** The type of every rendered row, in screen order. */
function rows(): string[] {
    return within(root())
        .queryAllByTestId(/^asset-type-tree-option-/)
        .map((element) => (element.getAttribute('data-testid') ?? '').replace('asset-type-tree-option-', ''));
}

/** Rows at the root of the tree: no `role="group"` between them and the tree. */
function rootRows(): string[] {
    return rows().filter((type) => option(type).closest('[role="group"]') === null);
}

/** Rows inside an open family, in screen order. */
function familyRows(): string[] {
    return rows().filter((type) => option(type).closest('[role="group"]') !== null);
}

/** The type of every row that renders a hint, in screen order. */
function hints(): string[] {
    return within(root())
        .queryAllByTestId(/^asset-type-tree-hint-/)
        .map((element) => (element.getAttribute('data-testid') ?? '').replace('asset-type-tree-hint-', ''));
}

/** The one picture a row or the closed trigger shows. */
function pictureOf(element: HTMLElement): string | null {
    const images = element.querySelectorAll('img');
    expect(images, `${element.getAttribute('data-testid')} must show exactly one picture`).toHaveLength(1);
    return images[0].getAttribute('src');
}

/** The search box held by the open trigger. */
function searchBox(trigger: HTMLElement): HTMLInputElement {
    const input = trigger.querySelector('input');
    if (!input) throw new Error('the trigger holds no search box: the dropdown is not open');
    return input;
}

/** Opens with a click and waits for the deferred step to end (focus lands right after "active entry set"). */
async function openByClick(trigger: HTMLElement): Promise<HTMLInputElement> {
    await fireEvent.click(trigger);
    const input = searchBox(trigger);
    await waitFor(() => expect(input).toHaveFocus());
    return input;
}

describe('AssetTypeSelect', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    describe('the closed field', () => {
        it('shows the chosen type with its own icon, not the placeholder', () => {
            const {trigger} = mount('STOCK');

            expect(pictureOf(trigger)).toBe(icon('stock'));
            expect(trigger).not.toHaveTextContent(PLACEHOLDER);
            expect(trigger.querySelector('input')).toBeNull();
        });

        it('shows the placeholder, and no picture, while no type is chosen', () => {
            const {trigger} = mount('');

            expect(trigger).toHaveTextContent(PLACEHOLDER);
            expect(trigger.querySelector('img')).toBeNull();
        });

        it('follows a value its parent sets while it is closed, as the dialog does when it loads an asset', () => {
            const {trigger, bound, onchange} = mount('STOCK');
            expect(pictureOf(trigger)).toBe(icon('stock'));

            // AssetModal opens on its default type, then writes the stored one once the asset has loaded.
            bound.value = 'CROWDFUND_REAL_ESTATE';
            flushSync();

            expect(pictureOf(trigger)).toBe(icon('crowdfunding-real-estate'));
            // A value written by the parent is not a user's choice: the dialog marks the field as edited on onchange.
            expect(onchange).not.toHaveBeenCalled();
        });
    });

    describe('the open tree', () => {
        it('lists the base types at the root and the families as collapsed groups, each with its own icon', async () => {
            const {trigger} = mount('STOCK');
            await openByClick(trigger);

            expect(within(root()).getByRole('tree')).toBeVisible();
            expect(rootRows()).toEqual(expect.arrayContaining(BASE_TYPES));
            // Nothing that belongs to a family may sit at the root — neither a subtype nor its generic member.
            const containers = [...new Set(Object.values(ASSET_TYPE_FAMILY))];
            expect(rootRows().filter((type) => type in ASSET_TYPE_FAMILY || containers.includes(type))).toEqual([]);

            // STOCK is at the root, so `defaultExpanded: 'selected'` has no family to open.
            for (const family of ['ETF', 'CROWDFUND']) {
                expect(group(family)).toHaveAttribute('aria-expanded', 'false');
            }
            expect(familyRows()).toEqual([]);
            // Every group row is a family, headed by the family's own icon.
            const groupKeys = within(root())
                .queryAllByTestId(/^asset-type-tree-group-/)
                .map((element) => (element.getAttribute('data-testid') ?? '').replace('asset-type-tree-group-', ''));
            expect(groupKeys.filter((key) => !containers.includes(key))).toEqual([]);
            expect(pictureOf(group('ETF'))).toBe(icon('etf'));
            expect(pictureOf(group('CROWDFUND'))).toBe(icon('crowdfunding'));

            expect(pictureOf(option('STOCK'))).toBe(icon('stock'));
            // The hyphen of the file against the underscore of the value: the mismatch that ends in other.png.
            expect(pictureOf(option('REAL_ESTATE'))).toBe(icon('real-estate'));
        });

        it('opens the ETF family on click: its generic member first, every subtype drawn with its composite', async () => {
            const {trigger} = mount('STOCK');
            await openByClick(trigger);

            await fireEvent.click(group('ETF'));

            expect(group('ETF')).toHaveAttribute('aria-expanded', 'true');
            const members = familyRows();
            expect(members[0], 'the generic ETF — mixed or unstated content — heads its family').toBe('ETF');
            expect(members).toEqual(expect.arrayContaining(Object.keys(ETF_COMPOSITES)));
            expect(pictureOf(option('ETF'))).toBe(icon('etf'));
            for (const [type, file] of Object.entries(ETF_COMPOSITES)) {
                expect(pictureOf(option(type)), `${type} must be drawn with ${file}.png`).toBe(icon(file));
            }
            expect(group('CROWDFUND')).toHaveAttribute('aria-expanded', 'false');
        });

        it('emits the subtype picked in the family once, closes, and shows its composite on the trigger', async () => {
            const {trigger, onchange, bound} = mount('STOCK');
            await openByClick(trigger);
            await fireEvent.click(group('ETF'));

            await fireEvent.click(option('ETF_STOCK'));

            expect(onchange).toHaveBeenCalledExactlyOnceWith('ETF_STOCK');
            expect(bound.value).toBe('ETF_STOCK');
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(within(root()).queryByRole('tree')).toBeNull();
            expect(queryOption('ETF_STOCK')).toBeNull();
            expect(pictureOf(trigger)).toBe(icon('etf-stock'));
        });

        it('opens by itself the family of a subtype value, with the highlight on that row', async () => {
            const {trigger} = mount('ETF_STOCK');
            expect(pictureOf(trigger)).toBe(icon('etf-stock'));

            await openByClick(trigger);

            expect(group('ETF')).toHaveAttribute('aria-expanded', 'true');
            expect(group('CROWDFUND')).toHaveAttribute('aria-expanded', 'false');
            const row = option('ETF_STOCK');
            expect(row).toBeVisible();
            expect(row.id).not.toBe('');
            expect(trigger).toHaveAttribute('aria-activedescendant', row.id);
        });

        it('lists the crowdfunding family as its generic member, then real-estate crowdfunding with its composite', async () => {
            const {trigger} = mount('STOCK');
            await openByClick(trigger);

            await fireEvent.click(group('CROWDFUND'));

            expect(group('CROWDFUND')).toHaveAttribute('aria-expanded', 'true');
            expect(familyRows()).toEqual(['CROWDFUND', 'CROWDFUND_REAL_ESTATE']);
            expect(pictureOf(option('CROWDFUND'))).toBe(icon('crowdfunding'));
            expect(pictureOf(option('CROWDFUND_REAL_ESTATE'))).toBe(icon('crowdfunding-real-estate'));
        });

        it('hints at what the generic member of each family stands for, and on no other row', async () => {
            const {trigger} = mount('STOCK');
            await openByClick(trigger);

            await fireEvent.click(group('ETF'));
            await fireEvent.click(group('CROWDFUND'));

            // Presence barrier for the absences below: both families are open and every row is
            // on screen, so a row without a hint is a row that draws none — not one still unmounted.
            expect(group('ETF')).toHaveAttribute('aria-expanded', 'true');
            expect(group('CROWDFUND')).toHaveAttribute('aria-expanded', 'true');
            expect(rows()).toEqual(expect.arrayContaining([...BASE_TYPES, 'ETF', ...Object.keys(ETF_COMPOSITES), 'CROWDFUND', 'CROWDFUND_REAL_ESTATE']));

            // Exactly the two generic members: "an ETF of mixed or unstated content" is a choice of
            // its own, and the hint is what tells it apart from the subtypes listed under it.
            expect([...hints()].sort()).toEqual(['CROWDFUND', 'ETF']);
            for (const generic of ['ETF', 'CROWDFUND']) {
                expect(option(generic), `the hint of ${generic} must sit in the ${generic} row`).toContainElement(within(root()).getByTestId(`asset-type-tree-hint-${generic}`));
            }
            // Named row by row, so a red says which subtype or base type grew a hint.
            const hinted = rows().filter((type) => type !== 'ETF' && type !== 'CROWDFUND' && within(option(type)).queryAllByTestId(/^asset-type-tree-hint-/).length > 0);
            expect(hinted, 'only the generic member of a family carries a hint; subtypes and base types carry none').toEqual([]);
        });
    });

    describe('search', () => {
        it('finds a type by its enum value, at the root and inside both families', async () => {
            const {trigger} = mount('STOCK');
            const input = await openByClick(trigger);

            await fireEvent.input(input, {target: {value: 'real_estate'}});

            expect([...rows()].sort()).toEqual(['CROWDFUND_REAL_ESTATE', 'ETF_REAL_ESTATE', 'REAL_ESTATE']);
        });
    });
});
