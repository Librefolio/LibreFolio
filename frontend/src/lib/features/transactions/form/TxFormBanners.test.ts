// @vitest-environment jsdom
/**
 * TxFormBanners — component test (Vitest + jsdom), lot J-57 complete of workstream J («Numeri e analisi»).
 *
 * The form's inline banners list the issues of a refused save or of a validation: each field issue as a
 * `tx-form-issue` item, each balance issue as a `tx-form-balance-issue` item. Two banners hold them: the error
 * banner of a refused save (`commitFailed`) and the warning banner of a validation (`showIssuesBanner`), where a
 * missing exchange rate (`wacFxUnavailable`) has an item of its own, with the FX sync link. Five items in all
 * in the template: three `tx-form-issue`, two `tx-form-balance-issue`.
 *
 * The contract (plan J, «J-57 completo — esecuzione», step 1): every one of them carries `data-code` equal to its
 * issue's `code`, as the bulk editor's `tx-bulk-issue` already does, so that a test can tell which refusal the form
 * shows — an Auto cost with nothing to average (`autoCostEmptyPool`, `autoCostUnknownPool`) among the others —
 * without reading its text.
 *
 * RED, both tests: today no item carries `data-code`, so each reads null. Presence comes first in each test, green
 * today: the banner of the state, its two lists, one item per issue passed and none elsewhere, and in the warning
 * banner the FX item with its sync link beside a generic one. So a red names the attribute, never a banner that did
 * not render; between the two tests all five items of the template are read.
 *
 * On text. `$lib/i18n` is replaced by a translator that renders a key with its values (`key(name=value)`), as in
 * `bulk/PromoteMergeModal.test.ts`, and `$lib/api` by an inert client. Nothing here reads a label or a message: the
 * items are found by test id, counted against the issues this file passes, and read by attribute. The issues carry
 * no params, so no figure or currency is formatted.
 */
import {describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {readable, writable} from 'svelte/store';

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

vi.mock('$lib/i18n', async (importOriginal) => {
    const shown = (key: string, options?: {values?: Record<string, unknown>}) => {
        const values = options?.values;
        if (!values) return key;
        const listed = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return `${key}(${listed.join(', ')})`;
    };
    const translator = readable(shown);
    // The module's other exports stay real (the supported locales, the default language), for the interface-locale store
    // the issue formatter imports.
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator, locale: writable('en')};
});

import {render, screen, within} from '$test/component';
import TxFormBanners from './TxFormBanners.svelte';
import type {ValidationIssue} from './txFormTypes';

type Props = ComponentProps<typeof TxFormBanners>;

/** A field issue of `code` on create 0, as POST /transactions/validate reports one. */
function fieldIssue(code: string, field: string): ValidationIssue {
    return {operation: 'create', index: 0, error: `invented ${code}`, code, params: null, field};
}

/** A balance issue of `code`: a broker's end of day, index -1, as the form sorts it into its balance list. */
function balanceIssue(code: string): ValidationIssue {
    return {operation: 'create', index: -1, error: `invented ${code}`, code, params: null, field: null};
}

/** The banners' props with every banner off: a test turns on the state it renders. */
function props(overrides: Partial<Props>): Props {
    return {
        getBulkContext: undefined,
        commitFailed: false,
        formError: null,
        issues: [],
        issuesDismissed: false,
        loadingPartner: false,
        balanceIssues: [],
        dualValidationError: null,
        fieldIssues: [],
        resolverCtx: {},
        showIssuesBanner: false,
        handleSyncFx: vi.fn(async () => {}),
        ...overrides,
    };
}

interface BannerItems {
    field: HTMLElement[];
    balance: HTMLElement[];
}

/**
 * The items of `banner`, after the presence checks: its list of field issues and its list of balance issues, one item
 * per issue passed, in the order of the issues, and no item of either kind outside the banner.
 */
function itemsOf(banner: HTMLElement, field: readonly ValidationIssue[], balance: readonly ValidationIssue[]): BannerItems {
    const fieldItems = within(within(banner).getByTestId('tx-form-issues')).queryAllByTestId('tx-form-issue');
    const balanceItems = within(within(banner).getByTestId('tx-form-balance-issues')).queryAllByTestId('tx-form-balance-issue');
    expect(fieldItems, 'presence: one tx-form-issue per field issue, in the banner').toHaveLength(field.length);
    expect(balanceItems, 'presence: one tx-form-balance-issue per balance issue, in the banner').toHaveLength(balance.length);
    expect(screen.queryAllByTestId('tx-form-issue'), 'presence: no tx-form-issue outside the banner').toHaveLength(field.length);
    expect(screen.queryAllByTestId('tx-form-balance-issue'), 'presence: no tx-form-balance-issue outside the banner').toHaveLength(balance.length);
    return {field: fieldItems, balance: balanceItems};
}

/** The `data-code` of each item, in their order: null where an item carries none. */
const codesOf = (items: readonly HTMLElement[]): Array<string | null> => items.map((item) => item.getAttribute('data-code'));

describe('TxFormBanners — every issue item carries its code, data-code (J-57 complete)', () => {
    it('a refused save: each tx-form-issue and tx-form-balance-issue of the error banner carries its issue’s code', () => {
        // RED: today each item reads null.
        const field = [fieldIssue('autoCostUnknownPool', 'cost_basis_override'), fieldIssue('costBasisRequired', 'cost_basis_override')];
        const balance = [balanceIssue('balanceCashNegative'), balanceIssue('balanceAssetNegative')];
        render(TxFormBanners, props({commitFailed: true, showIssuesBanner: true, issues: [...field, ...balance], fieldIssues: field, balanceIssues: balance}));

        expect(screen.queryByTestId('info-banner-warning'), 'presence: a refused save shows the error banner alone').toBeNull();
        const items = itemsOf(screen.getByTestId('info-banner-error'), field, balance);

        expect.soft(codesOf(items.field), 'tx-form-issue: data-code of each item, in the order of the field issues').toEqual(field.map((issue) => issue.code));
        expect(codesOf(items.balance), 'tx-form-balance-issue: data-code of each item, in the order of the balance issues').toEqual(balance.map((issue) => issue.code));
    });

    it('a validation: each item of the warning banner carries its issue’s code, the FX item with its sync link included', () => {
        // RED: today each item reads null.
        const field = [fieldIssue('wacFxUnavailable', 'cost_basis_override'), fieldIssue('autoCostEmptyPool', 'cost_basis_override')];
        const balance = [balanceIssue('balanceAssetNegative'), balanceIssue('balanceCashNegative')];
        render(TxFormBanners, props({showIssuesBanner: true, issues: [...field, ...balance], fieldIssues: field, balanceIssues: balance}));

        expect(screen.queryByTestId('info-banner-error'), 'presence: no refused save, so no error banner').toBeNull();
        const items = itemsOf(screen.getByTestId('info-banner-warning'), field, balance);
        const syncLinks = items.field.map((item) => within(item).queryAllByTestId('tx-form-sync-fx-link').length);
        expect(syncLinks, 'presence: the wacFxUnavailable item is the one with the FX sync link, the autoCostEmptyPool item the generic one').toEqual([1, 0]);

        expect.soft(codesOf(items.field), 'tx-form-issue: data-code of each item, in the order of the field issues').toEqual(field.map((issue) => issue.code));
        expect(codesOf(items.balance), 'tx-form-balance-issue: data-code of each item, in the order of the balance issues').toEqual(balance.map((issue) => issue.code));
    });
});
