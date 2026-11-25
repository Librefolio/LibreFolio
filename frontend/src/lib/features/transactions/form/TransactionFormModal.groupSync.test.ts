// @vitest-environment jsdom
/**
 * TransactionFormModal — the help line of an all-new group, and the «Save»/«Apply» button while it commits (project 66,
 * lot TL-3b). RED FIRST: the `groupSync` prop and the busy state of `tx-form-save` do not exist yet.
 *
 *   - `groupSync`  the Bulk sets it when the row being edited belongs to an all-new group (`newGroupOf` non-null): the
 *                  form shows a help line under the broker field (`tx-form-group-sync-hint`). Absent without the prop,
 *                  and in a read-only form even with it.
 *   - D2           while `committing`, the button `tx-form-save` shows nothing below `sm` today (its text is
 *                  `hidden sm:inline`, no icon). It must keep an accessible name (`aria-label` non-empty, equal to its
 *                  `title`), publish `aria-busy="true"` and hold a spinner icon. jsdom applies no media query, so the
 *                  «below sm» half is proved by the name and the icon, not by a width.
 *
 * Mount and mocks as `TransactionFormModal.parent.test.ts`. data-testid and ARIA attributes only, never a translated text.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {ensureTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {commitTransactions} from '$lib/features/transactions/txCommitApi';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';

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
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));
vi.mock('$lib/features/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));
// The guide only starts in create mode; a neutral stub keeps the real controller out.
vi.mock('$lib/features/onboarding/onboardingGuide.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/onboarding/onboardingGuide.svelte')>()),
    onboardingGuide: {
        active: null,
        queuedFlow: null,
        queuedFlows: [],
        queuedGuides: [],
        maybeStartContextual: vi.fn(() => false),
        queueContextual: vi.fn(),
        clearQueued: vi.fn(),
        maybeStartQueued: vi.fn(() => false),
        dismissHost: vi.fn(),
    },
}));

import TransactionFormModal from './TransactionFormModal.svelte';

const baseType = {doc_slug: 'x', requires_link: false, event_compatible: false, cost_basis_mode: 'forbidden'} as const;

const TYPES_WITH_CHARGE_ROLES = schemas.TXTypesResponse.parse({
    transaction_types: [
        {...baseType, code: 'BUY', name: 'Buy', description: 'Buy', icon_slug: 'buy', asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'positive', cash_sign: 'negative', charge_role: 'parent'},
        {...baseType, code: 'FEE', name: 'Fee', description: 'Fee', icon_slug: 'fee', asset_mode: 'optional', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'negative', charge_role: 'charge'},
        {...baseType, code: 'TAX', name: 'Tax', description: 'Tax', icon_slug: 'tax', asset_mode: 'optional', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'negative', charge_role: 'charge'},
    ],
    event_types: [],
});

const queryApi = () => vi.mocked(zodiosApi.query_transactions_api_v1_transactions_get);

function mount(props: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    return {onClose, ...render(TransactionFormModal, {open: true, mode: 'edit', items: null, onClose, ...props})};
}

function txRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 10,
        broker_id: 17,
        asset_id: 42,
        type: 'BUY',
        date: '2024-03-10',
        quantity: '1',
        cash: {code: 'EUR', amount: '-100'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: null,
        charges_count: 0,
        tags: [],
        description: '',
        cost_basis_override: null,
        cost_basis_mode: null,
        asset_event_id: null,
        created_at: '2024-03-10T00:00:00Z',
        updated_at: '2024-03-10T00:00:00Z',
        ...overrides,
    };
}

const FEE_ROW = () => txRow({id: 11, type: 'FEE', quantity: '0', cash: {code: 'EUR', amount: '-2'}, parent_transaction_id: 10});

/** The Bulk-hosted form: it pushes its draft to the Bulk instead of committing. */
function bulkHosted(extra: Record<string, unknown> = {}) {
    return mount({mode: 'edit', unlockImmutable: true, commitOnSave: false, allowChargeEdits: true, onPushDraft: vi.fn(), items: [txRow()], ...extra});
}

/** Presence barrier for the absences: the form and its broker field are on screen. */
async function formIsUp() {
    await screen.findByTestId('tx-form-body');
    await screen.findByTestId('tx-form-broker-wrap');
}

/** A promise settled by hand. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
        resolve = res;
    });
    return {promise, resolve};
}

describe('TransactionFormModal — the help line of an all-new group (66 TL-3b)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    it('groupSync on a parent’s form in the Bulk: the help line is shown, inside the broker field’s block', async () => {
        bulkHosted({groupSync: true});
        await formIsUp();
        const hint = await screen.findByTestId('tx-form-group-sync-hint');
        expect(hint).toBeVisible();
        expect(hint.textContent?.trim(), 'the line says something').not.toBe('');
        const broker = screen.getByTestId('tx-form-broker-wrap');
        expect(broker.contains(hint) || Boolean(broker.compareDocumentPosition(hint) & Node.DOCUMENT_POSITION_FOLLOWING), 'under the broker field').toBe(true);
    });

    it('groupSync on a charge’s form in the Bulk (a new row, create mode): the help line is shown', async () => {
        mount({mode: 'create', commitOnSave: false, allowChargeEdits: true, onPushDraft: vi.fn(), items: [FEE_ROW()], groupSync: true});
        await formIsUp();
        expect(await screen.findByTestId('tx-form-group-sync-hint')).toBeVisible();
    });

    it('guard: without groupSync (a row alone, or a group holding a saved row) there is no help line', async () => {
        bulkHosted();
        await formIsUp();
        expect(screen.queryByTestId('tx-form-group-sync-hint')).toBeNull();
    });

    it('guard: a read-only form shows no help line, even with groupSync', async () => {
        mount({mode: 'view', items: [txRow()], groupSync: true});
        await formIsUp();
        expect(screen.queryByTestId('tx-form-group-sync-hint')).toBeNull();
    });
});

describe('TransactionFormModal — «Save» keeps a name and says it is busy while it commits (66 TL-3b, D2)', () => {
    beforeAll(async () => {
        vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_WITH_CHARGE_ROLES);
        await setupI18n();
        await ensureTypesLoaded();
    });

    beforeEach(() => {
        queryApi().mockReset();
        queryApi().mockImplementation(async () => []);
        guideAnchors.clear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    it('while the commit is pending: aria-busy="true", an aria-label equal to its title, and a spinner icon', async () => {
        const pending = deferred<{committed: boolean; results: unknown[]; issues: unknown[]}>();
        vi.mocked(commitTransactions).mockImplementationOnce(() => pending.promise as never);
        mount({mode: 'edit', items: [txRow()]});

        const save = await screen.findByTestId('tx-form-save');
        await waitFor(() => expect(save).toBeEnabled());
        expect(save, 'premise: idle, not busy').not.toHaveAttribute('aria-busy', 'true');
        await fireEvent.click(save);

        try {
            await waitFor(() => expect(commitTransactions).toHaveBeenCalledTimes(1));
            await waitFor(() => expect(save).toBeDisabled());
            expect(save, 'busy while committing').toHaveAttribute('aria-busy', 'true');
            const label = save.getAttribute('aria-label') ?? '';
            expect(label.trim(), 'an accessible name that does not depend on the hidden text').not.toBe('');
            expect(label, 'the name is the title').toBe(save.getAttribute('title'));
            expect(save.querySelector('svg'), 'a spinner icon, shown at every width').not.toBeNull();
        } finally {
            pending.resolve({committed: true, results: [], issues: []});
        }
    });

    it('guard: idle, the button is not busy and keeps its title', async () => {
        mount({mode: 'edit', items: [txRow()]});
        const save = await screen.findByTestId('tx-form-save');
        await waitFor(() => expect(save).toBeEnabled());
        expect(save).not.toHaveAttribute('aria-busy', 'true');
        expect((save.getAttribute('title') ?? '').trim()).not.toBe('');
    });
});
