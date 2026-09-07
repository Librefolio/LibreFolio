// @vitest-environment jsdom
/**
 * ImportWizardModal — component test (Vitest + jsdom), the *secondary* lane of F1-E.
 *
 * The wizard's dense Step-4 logic is unreachable from props (every later step is
 * gated on the previous one having produced API-driven state), so it was lifted
 * into `importDedup.ts` / `importMerge.ts` / `importCompare.ts` and unit-tested
 * there. What a mount *can* prove cheaply, and what this file covers, is the
 * shell the user always sees first: the modal is gated on `open`, it opens on
 * Step 1 (upload), and its close control reaches `onClose` when there is no
 * unsaved work. Broker/type loading goes through a store that talks to the API,
 * which jsdom has no server for — so nothing here asserts on loaded brokers.
 *
 * Only `data-testid` / `data-*` are asserted; never a translated label.
 */
import {describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import ImportWizardModal from './ImportWizardModal.svelte';

// The wizard's open-effect fire-and-forgets loadBrokers(), which awaits the broker and
// transaction-type stores. Both hit the API through zodios/axios, and in jsdom there is no
// server, so ensureTypesLoaded() re-throws a network error that nothing catches — an
// unhandled rejection that would fail the whole suite. Stub only the two network loaders to
// resolve; every other export of each store stays real (importOriginal spread), so nothing
// else about the store behaviour is faked.
vi.mock('$lib/stores/reference/brokerStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/brokerStore')>()),
    ensureBrokersLoaded: vi.fn().mockResolvedValue(undefined),
    refreshAllBrokers: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/transactions/transactionTypeStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/transactions/transactionTypeStore')>()),
    ensureTypesLoaded: vi.fn().mockResolvedValue(undefined),
}));

function mount(props: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    const onImportBatch = vi.fn();
    return {onClose, onImportBatch, ...render(ImportWizardModal, {open: true, onClose, onImportBatch, ...props})};
}

describe('ImportWizardModal — shell and open gating', () => {
    it('renders the modal on Step 1 (upload) when open', async () => {
        await setupI18n();
        mount();

        expect(screen.getByTestId('import-wizard-modal')).toBeInTheDocument();
        expect(screen.getByTestId('import-wizard-stepper')).toBeInTheDocument();
        expect(screen.getByTestId('import-wizard-step1')).toBeInTheDocument();
        // The first stepper node is the current step, and it is the upload step.
        expect(screen.getByTestId('import-wizard-step-1')).toHaveAttribute('data-step-id', 'upload');
    });

    it('renders nothing while closed', async () => {
        await setupI18n();
        render(ImportWizardModal, {open: false, onClose: vi.fn(), onImportBatch: vi.fn()});

        expect(screen.queryByTestId('import-wizard-modal')).toBeNull();
        expect(screen.queryByTestId('import-wizard-step1')).toBeNull();
    });

    it('accepts the broker-scoped entry props and still opens on Step 1', async () => {
        await setupI18n();
        // Opening from a broker page passes defaultBrokerId + rows staged in the bulk editor;
        // the wizard must still mount to upload, not throw on the extra props.
        mount({defaultBrokerId: 7, pendingCreateTransactions: [], pendingDeleteTxIds: [500]});

        expect(screen.getByTestId('import-wizard-step1')).toBeInTheDocument();
        expect(screen.getByTestId('import-wizard-step-1')).toHaveAttribute('data-step-id', 'upload');
    });
});

describe('ImportWizardModal — closing', () => {
    it('reaches onClose directly when nothing has been uploaded yet', async () => {
        await setupI18n();
        const {onClose} = mount();

        await fireEvent.click(screen.getByTestId('import-wizard-close'));
        // No files, no parse results → no unsaved work → no discard confirmation in the way.
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
