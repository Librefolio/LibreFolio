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
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
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

/**
 * `onboardingGuide` — replaced with a test-owned spy object, the same pattern
 * `OnboardingCoachmark.test.ts` uses for `OnboardingOverlayHost`. The wizard only
 * ever calls `startImportAt` / `setStep` / `suspend` and reads `.active?.flow`; a
 * static-enough fake that flips `active` to the `import_guide` flow the moment
 * `startImportAt` succeeds is sufficient to observe every call the wizard makes
 * without reaching into the real controller/replay/storage machinery (covered
 * end-to-end in `onboarding.test.ts`).
 */
const {guideState, guideMocks} = vi.hoisted(() => ({
    guideState: {
        active: null as {flow: 'import_guide'; version: number; stepId: string; mode: 'automatic' | 'replay'} | null,
    },
    guideMocks: {
        startImportAt: vi.fn((stepId: string) => {
            guideState.active = {flow: 'import_guide', version: 1, stepId, mode: 'automatic'};
            return true;
        }),
        setStep: vi.fn(),
        suspend: vi.fn(),
        finish: vi.fn(async () => undefined as string | undefined),
        skip: vi.fn(async () => false),
    },
}));

vi.mock('$lib/features/onboarding/onboardingGuide.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/onboarding/onboardingGuide.svelte')>();
    return {
        ...actual,
        onboardingGuide: {
            get active() {
                return guideState.active;
            },
            startImportAt: (...args: Parameters<typeof guideMocks.startImportAt>) => guideMocks.startImportAt(...args),
            setStep: (...args: Parameters<typeof guideMocks.setStep>) => guideMocks.setStep(...args),
            suspend: (...args: Parameters<typeof guideMocks.suspend>) => guideMocks.suspend(...args),
            finish: (...args: Parameters<typeof guideMocks.finish>) => guideMocks.finish(...args),
            skip: (...args: Parameters<typeof guideMocks.skip>) => guideMocks.skip(...args),
        },
    };
});

/**
 * `$lib/api` — the same lazily-caching Proxy `AssetModal.test.ts` / `PreferencesTab.test.ts`
 * use: every endpoint becomes a local spy resolving `undefined` unless a test needs a real
 * shape from one. Only `list_files_api_v1_brokers_import_files_get` needs one here — the
 * call `loadBrokerFiles()` fires the moment the wizard reaches Step 2 (select), reachable
 * with zero uploaded files since `step1CanProceed` is true on an empty file list. Every step
 * beyond `select` needs an uploaded, parsed, deduplicated, asset-resolved row before
 * `handleImport()` will call `onImportBatch` — that pipeline is real API/service state this
 * shell-level harness cannot fabricate (see the "guide integration" describe block's
 * closing comment for the reachability boundary this draws).
 */
vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop)) {
                    cache.set(prop, prop === 'list_files_api_v1_brokers_import_files_get' ? vi.fn(async () => [] as unknown[]) : vi.fn(async () => undefined));
                }
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {post: vi.fn(async () => ({data: {}}))}};
});

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

/**
 * ImportWizardModal — onboarding guide integration.
 *
 * Reachability boundary. `handleImport()` — the only place that calls
 * `onImportBatch` and hands the guide off to `import.bulk` — is gated behind
 * `step4SelectedCount > 0`, which in turn requires at least one *newly
 * imported* row (`mergedTransactions` built from a real parsed file, surviving
 * asset resolution and the duplicate/database recheck). `pendingCreateTransactions`
 * looks like a shortcut but is not one: every row it seeds is marked
 * "before-opening" and is explicitly excluded from `step4SelectedCount` /
 * `buildFinalTxList()`, precisely so the wizard can never re-import what the
 * bulk editor already staged. There is no prop or exported hook that produces a
 * post-parse `mergedTransactions` row, so a *successful* handoff — `setStep('import.bulk')`
 * fired from `handleImport()`, and the "does not suspend when open turns false
 * after a completed handoff" half of it — cannot be reached from this shell-level
 * harness without fabricating internal state the real user flow never skips.
 * That half belongs in an E2E spec driving a real upload → parse → resolve →
 * import, asserting the onboarding coachmark reaches `data-step-id="import.bulk"`
 * — see this file's own top-of-file note that Step-4 logic is out of scope here.
 *
 * What *is* reachable and covered below: arming the guide at Step 1 on open,
 * `setStep` following a genuine Step 1 → Step 2 navigation (`goNext`, which only
 * needs `list_files` to resolve — mocked above — since `step1CanProceed` is true
 * with zero pending files), and `setStep` firing again for the *same* step id
 * when the user goes back with the real Step 2 "back" control — a genuine
 * duplicate value, never deduped by the wizard itself (only `onboardingGuide`'s
 * own `setStep` dedupes against its *own* current step, which this suite's fake
 * deliberately does not reproduce, so the wizard's own call is what is observed).
 */
describe('ImportWizardModal — onboarding guide integration', () => {
    beforeEach(() => {
        guideState.active = null;
        guideMocks.startImportAt.mockClear();
        guideMocks.setStep.mockClear();
        guideMocks.suspend.mockClear();
        guideMocks.finish.mockClear();
        guideMocks.skip.mockClear();
    });

    afterEach(() => {
        cleanup();
    });

    it('arms the import guide at the upload step the moment it opens', async () => {
        await setupI18n();
        mount();

        expect(guideMocks.startImportAt).toHaveBeenCalledTimes(1);
        expect(guideMocks.startImportAt).toHaveBeenCalledWith('import.upload');
        expect(guideMocks.setStep).not.toHaveBeenCalled();
    });

    it('advances the guide step on a real Step 1 → Step 2 navigation, and re-emits the same step id on the way back', async () => {
        await setupI18n();
        mount();
        expect(guideMocks.startImportAt).toHaveBeenCalledWith('import.upload');

        // Zero pending files: step1CanProceed is true, so Next uploads nothing and
        // moves straight to Step 2 (select) — a genuine semantic step change, not a
        // simulated one.
        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-2')).toHaveAttribute('data-step-id', 'select'));
        expect(guideMocks.setStep).toHaveBeenCalledWith('import.select');

        // Back to Step 1 through the real "back" control — a semantic step change
        // back to a step id the wizard already visited (via startImportAt, not
        // setStep), so this is the first time *setStep* itself sees 'import.upload'.
        await fireEvent.click(screen.getByTestId('import-wizard-back'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-1')).toHaveAttribute('data-step-id', 'upload'));
        expect(guideMocks.setStep).toHaveBeenLastCalledWith('import.upload');
        expect(guideMocks.setStep).toHaveBeenCalledTimes(2);
    });

    it('suspends the guide with {resetImport: true} once the parent actually closes the modal (open turns false) without a completed handoff', async () => {
        await setupI18n();
        const {onClose, rerender} = mount();
        expect(guideMocks.startImportAt).toHaveBeenCalledTimes(1);

        // `handleClose()` only calls the `onClose` prop — same as the real app, the
        // wizard does not own `open`; the parent reacts to `onClose` by flipping it.
        // That flip is what the guide-suspend effect actually watches, so it is
        // simulated explicitly rather than asserting suspension off a callback alone.
        await fireEvent.click(screen.getByTestId('import-wizard-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
        expect(guideMocks.suspend).not.toHaveBeenCalled();

        await rerender({open: false});

        expect(guideMocks.suspend).toHaveBeenCalledTimes(1);
        expect(guideMocks.suspend).toHaveBeenCalledWith({resetImport: true});
    });

    it('suspends with {resetImport: true} even after navigating to Step 2 before closing', async () => {
        await setupI18n();
        const {onClose, rerender} = mount();
        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-2')).toHaveAttribute('data-step-id', 'select'));
        guideMocks.suspend.mockClear();

        await fireEvent.click(screen.getByTestId('import-wizard-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
        await rerender({open: false});

        expect(guideMocks.suspend).toHaveBeenCalledTimes(1);
        expect(guideMocks.suspend).toHaveBeenCalledWith({resetImport: true});
    });

    it('never finishes or skips the guide, and never commits a transaction batch, on its own', async () => {
        await setupI18n();
        const {onImportBatch, rerender} = mount();

        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-2')).toHaveAttribute('data-step-id', 'select'));
        await fireEvent.click(screen.getByTestId('import-wizard-back'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-1')).toHaveAttribute('data-step-id', 'upload'));
        await fireEvent.click(screen.getByTestId('import-wizard-close'));
        await rerender({open: false});

        expect(guideMocks.finish).not.toHaveBeenCalled();
        expect(guideMocks.skip).not.toHaveBeenCalled();
        expect(onImportBatch).not.toHaveBeenCalled();
    });
});
