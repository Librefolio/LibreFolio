// @vitest-environment jsdom
/**
 * TransactionFormModal — component test (Vitest + jsdom) for the beta-feedback
 * form-draft fixes.
 *
 * Two behaviors, both decided the moment the draft is seeded:
 *
 *   T1-b — create mode starts with an EMPTY quantity (`emptyDraft().quantity`
 *     is `''`, not `'0'`): a pre-filled zero forced the user to cursor around
 *     it just to type decimals.
 *   T3 — duplicate mode preserves the source row's date. Duplicating is how a
 *     misclassified historical row gets corrected; resetting the date to today
 *     destroyed exactly the field being corrected. The bulk-workspace *clone*
 *     paths (resolveInitialRows / createOpFromClone / cloneRow) preserve the
 *     date too since the real T3 fix — the E2E coverage for those is tx-clone.
 *
 * Duplicate mode is currently not reachable from any page action (rows clone
 * through the bulk workspace), which is exactly why this is a component test
 * and not an E2E: the mode is a prop here.
 *
 * Store modules are the real ones with only their network loaders stubbed
 * (importOriginal spread, same pattern as ImportWizardModal.test.ts): jsdom
 * has no server, and an unhandled rejection from a loader would fail the suite
 * for a reason that has nothing to do with the subject. Type rules are NOT
 * loaded, so every type resolves through FALLBACK_RULE — which renders all
 * fields (quantity/cash optional, no pair) — enough for the draft-seeding
 * assertions here.
 *
 * Asserted: input values keyed by data-testid. Never a translated label.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {render, screen, setupI18n} from '$test/component';

vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});
vi.mock('$lib/stores/reference/brokerStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/brokerStore')>()),
    ensureBrokersLoaded: vi.fn().mockResolvedValue(undefined),
    refreshAllBrokers: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/transactions/transactionTypeStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/transactions/transactionTypeStore')>()),
    ensureTypesLoaded: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/assetStore')>()),
    ensureAssetsLoaded: vi.fn().mockResolvedValue(undefined),
    refreshAllAssets: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));
// CompactCashCell's currency dropdown reads the FX route cache.
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));
// The validate scheduler may fire on a complete duplicate draft; keep the wire out of it.
vi.mock('$lib/utils/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({issues: [], issuesCount: 0})),
}));

import TransactionFormModal from './TransactionFormModal.svelte';
import type {TXReadItem} from '../types';

/** A standalone BUY row, dated deliberately far from "today". */
const SOURCE_ROW: TXReadItem = {
    id: 77,
    broker_id: 1,
    asset_id: 5,
    type: 'BUY',
    date: '2024-03-15',
    quantity: '5',
    cash: {code: 'EUR', amount: '100'},
    related_transaction_id: null,
    tags: [],
    description: 'duplicate source',
};

function mount(props: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    return {onClose, ...render(TransactionFormModal, {open: true, mode: 'create', items: null, onClose, ...props})};
}

describe('TransactionFormModal — draft seeding (T1-b, T3)', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    it('T1-b: create mode starts with an empty quantity field', async () => {
        mount({mode: 'create'});

        const qty = (await screen.findByTestId('tx-form-quantity')) as HTMLInputElement;
        expect(qty.value).toBe('');
    });

    it('T3: duplicate mode preserves the source date (and the rest of the draft)', async () => {
        mount({mode: 'duplicate', items: [SOURCE_ROW]});

        // The date input lives inside the date wrapper; it shows the ISO value as-is.
        const dateWrap = await screen.findByTestId('tx-form-date-wrap');
        const dateInput = dateWrap.querySelector('input') as HTMLInputElement;
        expect(dateInput, 'duplicate mode must render an editable date field').toBeTruthy();
        expect(dateInput.value, 'duplicate must keep the historical date, not reset to today').toBe('2024-03-15');

        // The rest of the draft comes through too (spot-check the two fields the
        // correction workflow edits around).
        const qty = (await screen.findByTestId('tx-form-quantity')) as HTMLInputElement;
        expect(qty.value).toBe('5');
        const cash = (await screen.findByTestId('tx-form-cash-amount')) as HTMLInputElement;
        expect(cash.value).toBe('100');
    });
});
