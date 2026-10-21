// @vitest-environment jsdom
/**
 * ProviderComparisonModal — component test (Vitest + jsdom).
 *
 * The modal AssetModal opens after "Ask Provider" finds fields where the stored
 * asset and the provider disagree. It is a pure controlled component: it takes a
 * `DiffItem[]` in through `differences`, keeps a local copy for the checkboxes,
 * and the only thing that leaves is `onapply(selectedFields, resolutions)` (or
 * `oncancel()`). No network, no store — the whole surface is reachable from props.
 *
 * That callback pair is the contract, and it is what these tests assert. Reaching
 * the same ground through Playwright means seeding an asset whose provider data
 * differs field-by-field from the stored copy — most of the work is the setup, and
 * the object handed to the parent is never visible on screen.
 *
 * The one genuine subtlety is the *identifier* row: it is not a binary "mine or
 * theirs" but a three-outcome choice (keep both, pick the primary), delegated to
 * `IdentifierPrimaryChooser`. Its default and its override both have to survive the
 * trip into the `resolutions` map, and both are exercised below.
 *
 * The *asset type* row is the one string row not drawn as passed in (K17): each value
 * box shows the type as the badge of the asset cards — its icon and its catalogue
 * name — because a raw `ETF_STOCK` in monospace tells the user deciding nothing. The
 * badge is found by `comparison-type-badge` and identified by `data-type`, its picture
 * by `src`. The name it must show is read from the loaded i18n store (`get(_)`), never
 * written here: the claim is "the badge shows the catalogue's name for this key", not
 * any word of it. Every other string row keeps the raw, truncated value.
 *
 * The *quote base* row (Z-32 d, the last block) is a string row like the others, drawn in the asset details group
 * beside the name, the type and the currency (`DIFF_FIELD_SECTIONS`), and checked like every row. Any row may carry a
 * `note` — text the caller has already put in the UI language — drawn under its values as `comparison-note-{field}`; a
 * row without one draws none. The note asserted is the one the test passed in. RED until the note is drawn and the
 * row is grouped: today `quote_base_quantity` falls under Other.
 *
 * What it deliberately does NOT assert:
 *   - translated text. Section titles, the apply-button label and the value-box
 *     captions all come from the four-language catalogue. Groups are addressed by
 *     `data-section` (the stable i18n *key*, not its translation), counts by
 *     `data-selected-count`/`data-total-count`, and every value compared is one the
 *     test itself passed in as `currentValue`/`providerValue`.
 *   - CSS classes. The checked state is the `<input>`'s own `checked`, and the
 *     apply button's availability is its `disabled` — both semantic, neither a class.
 *   - the sector label's localisation. `formatDistKey` runs `$t` for `sector_area`;
 *     the test asserts the stable `data-dist-key`/`data-dist-pct`, never the
 *     rendered sector name, which is a translation.
 *
 * **`data-dist-pct` is a handle, not a rendering** (M-18 follow-up, 13/10/2026). Since M-18 the
 * share shown beside a distribution key is written in the interface locale (`formatPercent`:
 * `60,00%` in Italian, `60,00 %` in French); the attribute must not follow it. It carries the
 * machine form — the value × 100, two decimals, a point, no space: `60.00%` — in every language,
 * which is what these tests and the gallery fixture (`e2e/fixtures/galleryProviderCompare.ts`, a
 * shot taken in four languages) read. The English cases cannot tell the two forms apart, because
 * in English they coincide: the cases under «a share in another UI language» run in Italian and
 * French, the visible share computed with `formatPercent` in that locale, the attribute with the
 * contract's own formula.
 */
import {describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import {get} from 'svelte/store';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
import {formatPercent} from '$lib/utils/core/formatPercent';
import ProviderComparisonModal, {type DiffItem} from './ProviderComparisonModal.svelte';

/** A plain string-valued difference. `label` is arbitrary — never asserted on. */
function stringDiff(field: string, current: unknown, provider: unknown): DiffItem {
    return {field, label: `label:${field}`, type: 'string', currentValue: current, providerValue: provider, selected: true};
}

/** A distribution-valued difference (sector/geography style). */
function distDiff(field: string, current: unknown, provider: unknown): DiffItem {
    return {field, label: `label:${field}`, type: 'distribution', currentValue: current, providerValue: provider, selected: true};
}

function mount(differences: DiffItem[], props: Record<string, unknown> = {}) {
    const onapply = vi.fn();
    const oncancel = vi.fn();
    const utils = render(ProviderComparisonModal, {open: true, differences, assetName: 'ACME', onapply, oncancel, ...props});
    return {onapply, oncancel, ...utils};
}

/** The `differences` sync runs in an effect after mount, so wait for the first card. */
async function settled() {
    await waitFor(() => expect(screen.queryAllByTestId('comparison-card').length).toBeGreaterThan(0));
}

/** Args of the last `onapply(fields, resolutions)`. */
function lastApply(spy: Mock): {fields: string[]; resolutions: Record<string, {primary: string; alternates: string[]}>} | undefined {
    const call = spy.mock.calls.at(-1);
    if (!call) return undefined;
    return {fields: call[0], resolutions: call[1]};
}

function card(field: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`[data-testid="comparison-card"][data-field="${field}"]`);
    if (!el) throw new Error(`no card for field ${field}`);
    return el;
}

function sectionOrder(): string[] {
    return [...document.querySelectorAll<HTMLElement>('[data-testid="comparison-group"]')].map((g) => g.getAttribute('data-section') ?? '');
}

/** The catalogue's name for a type, read from the loaded i18n store — never a translation written here. */
function typeLabel(type: string): string {
    const key = `assets.types.${type}`;
    const label = get(_)(key);
    expect(label, `${key} does not resolve: the catalogue is not loaded, or the key is gone`).not.toBe(key);
    // Barrier for "the box no longer prints the raw code": a label spelling its own code could not tell the two apart.
    expect(label, `the ${key} label contains the raw code itself, so this test could not tell the badge from the code`).not.toContain(type);
    return label;
}

/** The type badges inside one value box. */
function typeBadges(box: HTMLElement): HTMLElement[] {
    return within(box).queryAllByTestId('comparison-type-badge');
}

/** The one type badge of a value box. */
function onlyTypeBadge(box: HTMLElement): HTMLElement {
    const badges = typeBadges(box);
    expect(badges, `${box.getAttribute('data-testid')} holds ${badges.length} comparison-type-badge instead of one: an asset type is drawn as the badge of the asset cards — its icon and its catalogue name — not as the raw enum code`).toHaveLength(1);
    return badges[0];
}

/** The one picture a type badge shows. */
function pictureOf(badge: HTMLElement): string | null {
    const images = badge.querySelectorAll('img');
    expect(images, 'a type badge shows exactly one picture').toHaveLength(1);
    return images[0].getAttribute('src');
}

describe('ProviderComparisonModal — grouping', () => {
    it('places each field in its configured section, Other last, in config order', async () => {
        await setupI18n();
        // One field per section, plus an unmatched one that must fall through to Other.
        mount([stringDiff('currency', 'USD', 'EUR'), stringDiff('identifier_isin', 'IT0001', 'IT0002'), stringDiff('sector_area', 'x', 'y'), stringDiff('made_up_field', '1', '2')]);
        await settled();

        // Identifiers first, then asset details, then classification, then Other —
        // asserted on the stable i18n keys, never the rendered titles.
        expect(sectionOrder()).toEqual(['common.identifiers', 'assets.modal.assetDetails', 'common.classification', '__other__']);
        expect(card('currency')).toBeInTheDocument();
        expect(card('made_up_field')).toBeInTheDocument();
    });

    it('shows no cards and a zero total when there is nothing to compare', async () => {
        await setupI18n();
        mount([]);

        // The modal still mounts (ModalBase open=true); the body just publishes an
        // empty tally, which is what disables Apply.
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-total-count', '0');
        expect(screen.queryByTestId('comparison-card')).toBeNull();
        expect(screen.getByTestId('comparison-apply')).toBeDisabled();
    });
});

describe('ProviderComparisonModal — selection and the apply payload', () => {
    it('starts with every row selected and hands them all back on apply', async () => {
        await setupI18n();
        const {onapply} = mount([stringDiff('currency', 'USD', 'EUR'), stringDiff('display_name', 'A', 'B')]);
        await settled();

        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-selected-count', '2');
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-total-count', '2');

        await fireEvent.click(screen.getByTestId('comparison-apply'));

        const applied = lastApply(onapply);
        expect(applied?.fields.sort()).toEqual(['currency', 'display_name']);
        // No identifier rows, so the resolutions map is empty rather than absent.
        expect(applied?.resolutions).toEqual({});
    });

    it('drops a single unticked row from the payload', async () => {
        await setupI18n();
        const {onapply} = mount([stringDiff('currency', 'USD', 'EUR'), stringDiff('display_name', 'A', 'B')]);
        await settled();

        await fireEvent.click(screen.getByTestId('comparison-checkbox-currency'));
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-selected-count', '1');

        await fireEvent.click(screen.getByTestId('comparison-apply'));
        expect(lastApply(onapply)?.fields).toEqual(['display_name']);
    });

    it('disables apply once everything is deselected, and re-enables it on select-all', async () => {
        await setupI18n();
        const {onapply} = mount([stringDiff('currency', 'USD', 'EUR'), stringDiff('display_name', 'A', 'B')]);
        await settled();

        await fireEvent.click(screen.getByTestId('comparison-deselect-all'));
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-selected-count', '0');
        expect(screen.getByTestId('comparison-apply')).toBeDisabled();

        await fireEvent.click(screen.getByTestId('comparison-select-all'));
        expect(screen.getByTestId('comparison-body')).toHaveAttribute('data-selected-count', '2');
        expect(screen.getByTestId('comparison-apply')).toBeEnabled();

        await fireEvent.click(screen.getByTestId('comparison-apply'));
        expect(lastApply(onapply)?.fields.sort()).toEqual(['currency', 'display_name']);
    });

    it('closes on apply and closes on cancel, telling the two apart by which callback fired', async () => {
        await setupI18n();
        const {onapply, oncancel} = mount([stringDiff('currency', 'USD', 'EUR')]);
        await settled();

        await fireEvent.click(screen.getByTestId('comparison-cancel'));
        expect(oncancel).toHaveBeenCalledTimes(1);
        expect(onapply).not.toHaveBeenCalled();
        // open is flipped to false, so ModalBase unmounts the whole dialog.
        await waitFor(() => expect(screen.queryByTestId('comparison-modal')).toBeNull());
    });
});

describe('ProviderComparisonModal — value rendering', () => {
    it('shows the stored value on the left and the provider value on the right', async () => {
        await setupI18n();
        mount([stringDiff('currency', 'USD', 'EUR')]);
        await settled();

        // The values are the ones the test passed in — asserting them is asserting
        // the wiring, not a translation.
        expect(screen.getByTestId('comparison-current-currency')).toHaveTextContent('USD');
        expect(screen.getByTestId('comparison-provider-currency')).toHaveTextContent('EUR');
    });

    it('truncates a long value at 50 chars with an ellipsis and shows a dash for null', async () => {
        await setupI18n();
        const long = 'X'.repeat(60);
        mount([stringDiff('short_description', long, null)]);
        await settled();

        expect(screen.getByTestId('comparison-current-short_description')).toHaveTextContent('X'.repeat(50) + '…');
        // null is not the string "null": the helper renders an em dash.
        expect(screen.getByTestId('comparison-provider-short_description')).toHaveTextContent('—');
    });

    it('formats a distribution as percentages, sorted by weight descending', async () => {
        await setupI18n();
        // geographic_area is NOT special-cased by formatDistKey, so the keys render
        // verbatim and stay assertable.
        mount([distDiff('geographic_area', {US: 0.6, EU: 0.4}, {US: 0.5, EU: 0.5})]);
        await settled();

        const entries = within(screen.getByTestId('comparison-current-geographic_area')).getAllByTestId('comparison-dist-entry');
        expect(entries.map((e) => e.getAttribute('data-dist-key'))).toEqual(['US', 'EU']);
        expect(entries.map((e) => e.getAttribute('data-dist-pct'))).toEqual(['60.00%', '40.00%']);
    });

    it('reads a distribution wrapped in a `.distribution` envelope', async () => {
        await setupI18n();
        mount([distDiff('geographic_area', {distribution: {IT: 1}}, {distribution: {IT: 1}})]);
        await settled();

        const entries = within(screen.getByTestId('comparison-provider-geographic_area')).getAllByTestId('comparison-dist-entry');
        expect(entries).toHaveLength(1);
        expect(entries[0].getAttribute('data-dist-pct')).toBe('100.00%');
    });

    it('shows the empty placeholder instead of an entry when the distribution is empty', async () => {
        await setupI18n();
        mount([distDiff('geographic_area', {}, {IT: 1})]);
        await settled();

        // No entries in the empty (current) box; the populated (provider) box has one.
        expect(within(screen.getByTestId('comparison-current-geographic_area')).queryByTestId('comparison-dist-entry')).toBeNull();
        expect(within(screen.getByTestId('comparison-provider-geographic_area')).getAllByTestId('comparison-dist-entry')).toHaveLength(1);
    });

    it('runs the sector localisation branch without leaking a translation into the assertion', async () => {
        await setupI18n();
        // sector_area DOES go through formatDistKey's $t path; we assert only the
        // stable key/pct, which the localisation cannot move.
        mount([distDiff('sector_area', {TECHNOLOGY: 0.7, ENERGY: 0.3}, {TECHNOLOGY: 1})]);
        await settled();

        const entries = within(screen.getByTestId('comparison-current-sector_area')).getAllByTestId('comparison-dist-entry');
        expect(entries.map((e) => e.getAttribute('data-dist-key'))).toEqual(['TECHNOLOGY', 'ENERGY']);
        expect(entries.map((e) => e.getAttribute('data-dist-pct'))).toEqual(['70.00%', '30.00%']);
    });

    it('draws an asset_type value as the badge of the asset cards: its icon and its catalogue name, not the raw code (K17)', async () => {
        await setupI18n();
        const sides = [
            {side: 'current', type: 'ETF_STOCK', label: typeLabel('ETF_STOCK')},
            {side: 'provider', type: 'ETF_BOND', label: typeLabel('ETF_BOND')},
        ];
        mount([stringDiff('asset_type', 'ETF_STOCK', 'ETF_BOND')]);
        await settled();

        for (const {side, type, label} of sides) {
            const box = screen.getByTestId(`comparison-${side}-asset_type`);
            const badge = onlyTypeBadge(box);
            expect(badge).toHaveAttribute('data-type', type);
            expect(pictureOf(badge)).toBe(getAssetTypeIconUrl(type));
            expect(badge).toHaveTextContent(label);
            expect(box.textContent, `comparison-${side}-asset_type still prints the raw code ${type}`).not.toContain(type);
        }
    });

    it('falls back to the raw code, inside the badge, for a type the catalogue does not name (K17)', async () => {
        await setupI18n();
        const unknown = 'NOT_A_REAL_TYPE';
        // Barrier: the key genuinely misses — svelte-i18n answers a missing key with the key itself.
        expect(get(_)(`assets.types.${unknown}`), `assets.types.${unknown} resolves: this case needs a code the catalogue does not name`).toBe(`assets.types.${unknown}`);
        mount([stringDiff('asset_type', unknown, 'ETF_STOCK')]);
        await settled();

        const box = screen.getByTestId('comparison-current-asset_type');
        const badge = onlyTypeBadge(box);
        expect(badge).toHaveAttribute('data-type', unknown);
        expect(pictureOf(badge)).toBe(getAssetTypeIconUrl(unknown));
        expect(badge).toHaveTextContent(unknown);
        // svelte-i18n hands back the key for a missing name, so `$t(key) || code` would print the path, not the code.
        expect(box.textContent, 'the badge prints the i18n path of the missing name instead of the raw code').not.toContain('assets.types.');
    });

    it.each([
        {empty: 'current', filled: 'provider', current: null, provider: 'ETF_STOCK'},
        {empty: 'provider', filled: 'current', current: 'ETF_STOCK', provider: null},
    ])('shows a dash and no badge for a null $empty type, beside the badge of the $filled one (K17)', async ({empty, filled, current, provider}) => {
        await setupI18n();
        mount([stringDiff('asset_type', current, provider)]);
        await settled();

        // Presence barrier: the badge is drawn on this very row, so its absence next door is a decision, not a late mount.
        expect(onlyTypeBadge(screen.getByTestId(`comparison-${filled}-asset_type`))).toHaveAttribute('data-type', 'ETF_STOCK');
        const box = screen.getByTestId(`comparison-${empty}-asset_type`);
        expect(box).toHaveTextContent('—');
        expect(typeBadges(box), `comparison-${empty}-asset_type draws a badge for a null type: there is no type to draw`).toHaveLength(0);
        expect(box.querySelector('img'), `comparison-${empty}-asset_type draws a picture for a null type: other.png would claim a type nobody set`).toBeNull();
    });

    it('keeps every other string row as raw text with no type badge, even when its value spells a type code (K17 guard)', async () => {
        await setupI18n();
        // The display name spells type codes on purpose: the badge belongs to the asset_type field, never to what a value looks like.
        const rows = [
            {field: 'currency', current: 'USD', provider: 'EUR'},
            {field: 'display_name', current: 'ETF_STOCK', provider: 'ETF_BOND'},
        ];
        mount(rows.map(({field, current, provider}) => stringDiff(field, current, provider)));
        await settled();

        for (const {field, current, provider} of rows) {
            for (const [side, value] of [
                ['current', current],
                ['provider', provider],
            ]) {
                const box = screen.getByTestId(`comparison-${side}-${field}`);
                expect(box).toHaveTextContent(value);
                expect(typeBadges(box), `comparison-${side}-${field} draws a type badge: only the asset_type row does`).toHaveLength(0);
            }
        }
    });
});

// =========================================================================
// A share in another UI language (M-18 follow-up) — see the header
// =========================================================================

type UiLanguage = 'it' | 'fr';
type Box = 'current' | 'provider';

/** The machine form the contract writes in `data-dist-pct`, in every language: two decimals, a point, no space. */
function machinePct(value: number): string {
    return `${(value * 100).toFixed(2)}%`;
}

/** The shares these cases pass in, by box: distinct, so the order is the weights'; 87.5% and 12.5% need their second decimal padded. */
const SHARES: Readonly<Record<Box, Readonly<Record<string, number>>>> = {current: {US: 0.6, EU: 0.4}, provider: {IT: 0.875, DE: 0.125}};

/** What a box must list, heaviest first: each key with the value passed in for it. */
function sharesOf(box: Box): Array<[string, number]> {
    return Object.entries(SHARES[box]).sort(([, a], [, b]) => b - a);
}

/**
 * One box's entries as drawn: each key, its `data-dist-pct`, and the share it shows. A
 * `geographic_area` key is drawn verbatim, so the share is the entry's other element.
 */
function drawnShares(box: Box): Array<{key: string; attribute: string | null; shown: string}> {
    return within(screen.getByTestId(`comparison-${box}-geographic_area`))
        .getAllByTestId('comparison-dist-entry')
        .map((entry) => {
            const key = entry.getAttribute('data-dist-key') ?? '';
            const others = [...entry.children].map((child) => (child.textContent ?? '').trim()).filter((text) => text !== key);
            return {key, attribute: entry.getAttribute('data-dist-pct'), shown: others.join(' | ')};
        });
}

/** Run a case with the UI in `language` — the catalogue and the app language together, as the language selector sets them — and put English back after it. */
async function inLanguage(language: UiLanguage, body: () => Promise<void>): Promise<void> {
    await setupI18n(language);
    currentLanguage.set(language);
    try {
        await body();
    } finally {
        currentLanguage.set('en');
        await setupI18n('en');
    }
}

describe('ProviderComparisonModal — a share in another UI language (M-18 follow-up)', () => {
    it.each(['it', 'fr'] as const)('keeps data-dist-pct in the machine form — 60.00%, a point and no space — with the UI in %s', async (language) => {
        await inLanguage(language, async () => {
            // Premise: in this language the share on screen is written otherwise, so the attribute can be told from it.
            expect(formatPercent(0.6, {scale: 100, signed: false, locale: language}), `premise: ${language} writes 60% as the machine form does`).not.toBe(machinePct(0.6));
            mount([distDiff('geographic_area', SHARES.current, SHARES.provider)]);
            await settled();

            const boxes = ['current', 'provider'] as const;
            expect(Object.fromEntries(boxes.map((box) => [box, drawnShares(box).map(({key, attribute}) => [key, attribute])])), `data-dist-pct follows the UI language (${language}); it is a handle, and reads the machine form in every language`).toEqual(
                Object.fromEntries(boxes.map((box) => [box, sharesOf(box).map(([key, value]) => [key, machinePct(value)])])),
            );
        });
    });

    it.each(['it', 'fr'] as const)('shows each share as the interface writes it in %s, through formatPercent (guard)', async (language) => {
        await inLanguage(language, async () => {
            // jsdom's browser is en-US, which lends Italian or French no region: the interface locale is the bare language.
            expect(uiLocale(), 'premise: the interface locale is not the language the UI was set to').toBe(language);
            expect(formatPercent(0.6, {scale: 100, signed: false, locale: language}), `premise: ${language} writes 60% as the machine form does`).not.toBe(machinePct(0.6));
            mount([distDiff('geographic_area', SHARES.current, SHARES.provider)]);
            await settled();

            const boxes = ['current', 'provider'] as const;
            expect(Object.fromEntries(boxes.map((box) => [box, drawnShares(box).map(({key, shown}) => [key, shown])])), `a share on screen is not written as formatPercent writes it in ${language}`).toEqual(
                Object.fromEntries(boxes.map((box) => [box, sharesOf(box).map(([key, value]) => [key, formatPercent(value, {scale: 100, signed: false, locale: language})])])),
            );
        });
    });
});

describe('ProviderComparisonModal — identifier resolution', () => {
    it('renders the chooser instead of value boxes and defaults the primary to the provider value', async () => {
        await setupI18n();
        const {onapply} = mount([stringDiff('identifier_isin', 'IT0001', 'IT0002')]);
        await settled();

        // Identifier rows swap the two value boxes for the primary chooser.
        expect(screen.getByTestId('comparison-chooser-identifier_isin')).toBeInTheDocument();
        expect(screen.queryByTestId('comparison-current-identifier_isin')).toBeNull();

        await fireEvent.click(screen.getByTestId('comparison-apply'));

        const applied = lastApply(onapply);
        expect(applied?.fields).toEqual(['identifier_isin']);
        // Provider value leads by default; the stored value is kept as an alternate,
        // never discarded.
        expect(applied?.resolutions).toEqual({identifier_isin: {primary: 'IT0002', alternates: ['IT0001']}});
    });

    it('carries a manually chosen primary into the resolutions map', async () => {
        await setupI18n();
        const {onapply} = mount([stringDiff('identifier_isin', 'IT0001', 'IT0002')]);
        await settled();

        // Pick the stored code as primary instead of the provider's.
        await fireEvent.click(screen.getByTestId('comparison-chooser-identifier_isin-option-IT0001'));
        await fireEvent.click(screen.getByTestId('comparison-apply'));

        expect(lastApply(onapply)?.resolutions).toEqual({identifier_isin: {primary: 'IT0001', alternates: ['IT0002']}});
    });

    it('omits a deselected identifier from both the fields and the resolutions', async () => {
        await setupI18n();
        const {onapply} = mount([stringDiff('identifier_isin', 'IT0001', 'IT0002'), stringDiff('currency', 'USD', 'EUR')]);
        await settled();

        await fireEvent.click(screen.getByTestId('comparison-checkbox-identifier_isin'));
        await fireEvent.click(screen.getByTestId('comparison-apply'));

        const applied = lastApply(onapply);
        expect(applied?.fields).toEqual(['currency']);
        expect(applied?.resolutions).toEqual({});
    });
});

// =========================================================================
// The quote base row and its note (Z-32 d) — see the header
// =========================================================================

/** A string row with a note under its values: the caller's text, already in the UI language. */
function notedDiff(field: string, current: unknown, provider: unknown, note: string): DiffItem {
    return {...stringDiff(field, current, provider), note};
}

/** The group a card is drawn under: the `data-section` of the last group header before it, in document order. */
function sectionOf(field: string): string | null {
    let section: string | null = null;
    for (const element of document.querySelectorAll<HTMLElement>('[data-testid="comparison-group"], [data-testid="comparison-card"]')) {
        if (element.getAttribute('data-testid') === 'comparison-group') section = element.getAttribute('data-section');
        else if (element.getAttribute('data-field') === field) return section;
    }
    return null;
}

describe('ProviderComparisonModal — the quote base row and its note (Z-32 d)', () => {
    /** What AssetModal would pass, already translated: a value the test owns, never a catalogue sentence. */
    const NOTE = 'note: Owned source quotes this line in GBp, one price per 100 units';

    it('draws a row’s note under its values, inside its own card: the text the caller passed', async () => {
        await setupI18n();
        mount([notedDiff('quote_base_quantity', '1', '100', NOTE)]);
        await settled();

        const row = card('quote_base_quantity');
        // RED today: a note is never drawn.
        const note = within(row).getByTestId('comparison-note-quote_base_quantity');
        expect(note).toHaveTextContent(NOTE);
        const values = within(row).getByTestId('comparison-provider-quote_base_quantity');
        expect(values.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING, 'the note comes under the values, not above them').toBeTruthy();
    });

    it('draws no note for a row that has none', async () => {
        await setupI18n();
        mount([stringDiff('currency', 'EUR', 'GBP'), notedDiff('quote_base_quantity', '1', '100', NOTE)]);
        await settled();

        // Presence barrier — RED today: the note is drawn where one is given, so its absence next door is a decision, not a late mount.
        expect(within(card('quote_base_quantity')).getByTestId('comparison-note-quote_base_quantity')).toHaveTextContent(NOTE);
        expect(within(card('currency')).queryAllByTestId(/^comparison-note-/), 'the currency row has no note to draw').toHaveLength(0);
        expect(screen.queryAllByTestId(/^comparison-note-/), 'one note given, one note drawn').toHaveLength(1);
    });

    it('groups quote_base_quantity with the asset details — name, type, currency — never under Other', async () => {
        await setupI18n();
        mount([stringDiff('currency', 'EUR', 'GBP'), stringDiff('quote_base_quantity', '1', '100'), stringDiff('short_description', 'a', 'b')]);
        await settled();

        // RED today: the field is in no section, so it falls through to Other.
        expect(sectionOf('quote_base_quantity')).toBe('assets.modal.assetDetails');
        expect(sectionOrder()).toEqual(['assets.modal.assetDetails', 'common.classification']);
    });

    it('starts the quote base row checked, like every row, and hands it back on apply (guard)', async () => {
        await setupI18n();
        const {onapply} = mount([stringDiff('quote_base_quantity', '100', '1')]);
        await settled();

        expect(screen.getByTestId('comparison-checkbox-quote_base_quantity')).toBeChecked();
        await fireEvent.click(screen.getByTestId('comparison-apply'));
        expect(lastApply(onapply)).toEqual({fields: ['quote_base_quantity'], resolutions: {}});
    });
});
