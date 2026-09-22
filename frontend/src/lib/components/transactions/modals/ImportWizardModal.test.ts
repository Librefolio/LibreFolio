// @vitest-environment jsdom
/**
 * ImportWizardModal — component test (Vitest + jsdom), the *secondary* lane of F1-E.
 *
 * Most dense Step-4 logic was lifted into `importDedup.ts` / `importMerge.ts` /
 * `importCompare.ts` and unit-tested there. This mount covers the shell the user
 * always sees first plus one controlled upload→select→analyze→assets pipeline
 * whose synthetic API payload reaches the Confirm All parent callback without a
 * server. Broker/type loading is stubbed at the network boundary.
 *
 * Only `data-testid` / `data-*` are asserted; never a translated label.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import ImportWizardModal from './ImportWizardModal.svelte';
import TransactionBulkModal, {type WorkspaceIntent} from './TransactionBulkModal.svelte';
import AssetGroupStep from '$lib/components/transactions/import/AssetGroupStep.svelte';
import {TRANSACTION_BULK_STEP_IDS, type ContextualOnboardingFlow, type GuidedOnboardingFlow} from '$lib/features/onboarding/onboardingGuideCatalog';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import type {AssetGroup} from '$lib/utils/assetGrouping';
import type {TransactionCreateItem} from '$lib/types';
import {zodiosApi} from '$lib/api';
import {getBrokerInfo, getEditableBrokers} from '$lib/stores/reference/brokerStore';
import {txStoreInvalidate, txStoreSetAll} from '$lib/stores/transactions/txStore.svelte';
import type {TXReadItem} from '../types';

const {bulkChildProbe} = vi.hoisted(() => ({
    bulkChildProbe: {
        interceptImportWizard: false,
        importProps: null as Record<string, unknown> | null,
        formProps: null as Record<string, unknown> | null,
    },
}));

/*
 * Keep this file's real ImportWizard coverage intact, but expose the child
 * callback boundary while TransactionBulkModal is the component under test.
 * The parent owns both `open` and the success-only `onImportBatch` signal; a
 * no-DOM probe is enough to exercise that orchestration without repeating the
 * conditional seven-step wizard in every workspace-origin case.
 */
vi.mock('./ImportWizardModal.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('./ImportWizardModal.svelte')>();
    const renderActual = actual.default as unknown as (...args: unknown[]) => unknown;
    return {
        ...actual,
        default: ((...args: unknown[]) => {
            if (bulkChildProbe.interceptImportWizard) {
                bulkChildProbe.importProps = args[1] as Record<string, unknown>;
                return {};
            }
            return renderActual(...args);
        }) as typeof actual.default,
    };
});

vi.mock('./TransactionFormModal.svelte', () => ({
    default: (...args: unknown[]) => {
        if (bulkChildProbe.interceptImportWizard) {
            bulkChildProbe.formProps = args[1] as Record<string, unknown>;
        }
        return {};
    },
}));

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
    getEditableBrokers: vi.fn(() => []),
    getBrokerInfo: vi.fn(() => null),
}));
vi.mock('$lib/stores/transactions/transactionTypeStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/transactions/transactionTypeStore')>()),
    ensureTypesLoaded: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/assetStore')>()),
    refreshAllAssets: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('$lib/utils/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));

const {buildMergedTransactionsCalls} = vi.hoisted(() => ({
    buildMergedTransactionsCalls: vi.fn(),
}));

vi.mock('$lib/utils/transactions/importMerge', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/utils/transactions/importMerge')>();
    return {
        ...actual,
        buildMergedTransactions: (...args: Parameters<typeof actual.buildMergedTransactions>) => {
            buildMergedTransactionsCalls(...args);
            return actual.buildMergedTransactions(...args);
        },
    };
});

/**
 * `onboardingGuide` — replaced with a test-owned spy object, the same pattern
 * `OnboardingCoachmark.test.ts` uses for `OnboardingOverlayHost`. The wizard
 * calls `startImportAt` / `setStep` / `dismissHost`, and preempts an active Bulk
 * flow by queueing it first. A static-enough fake that flips `active` to the
 * `import_guide` flow the moment `startImportAt` succeeds is sufficient to
 * observe every call without reaching into the real controller/replay/storage
 * machinery (covered end-to-end in `onboarding.test.ts`).
 */
const {guideState, guideMocks} = vi.hoisted(() => ({
    guideState: {
        active: null as {flow: GuidedOnboardingFlow; version: number; stepId: string; mode: 'automatic' | 'replay'} | null,
    },
    guideMocks: {
        startImportAt: vi.fn((stepId: string) => {
            guideState.active = {flow: 'import_guide', version: 1, stepId, mode: 'automatic'};
            return true;
        }),
        setStep: vi.fn(),
        queueContextual: vi.fn((_flow: ContextualOnboardingFlow, _stepId?: string) => undefined),
        clearQueued: vi.fn((_flow: ContextualOnboardingFlow, _stepId?: string) => undefined),
        maybeStartQueued: vi.fn((_flow: ContextualOnboardingFlow, _stepId?: string) => false),
        dismissHost: vi.fn((_options?: {restartAtFirst?: boolean}) => {
            guideState.active = null;
        }),
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
            get queuedGuides() {
                return [];
            },
            startImportAt: (...args: Parameters<typeof guideMocks.startImportAt>) => guideMocks.startImportAt(...args),
            setStep: (...args: Parameters<typeof guideMocks.setStep>) => guideMocks.setStep(...args),
            queueContextual: (...args: Parameters<typeof guideMocks.queueContextual>) => guideMocks.queueContextual(...args),
            clearQueued: (...args: Parameters<typeof guideMocks.clearQueued>) => guideMocks.clearQueued(...args),
            maybeStartQueued: (...args: Parameters<typeof guideMocks.maybeStartQueued>) => guideMocks.maybeStartQueued(...args),
            dismissHost: (...args: Parameters<typeof guideMocks.dismissHost>) => guideMocks.dismissHost(...args),
            finish: (...args: Parameters<typeof guideMocks.finish>) => guideMocks.finish(...args),
            skip: (...args: Parameters<typeof guideMocks.skip>) => guideMocks.skip(...args),
        },
    };
});

/**
 * `$lib/api` — the same lazily-caching Proxy `AssetModal.test.ts` / `PreferencesTab.test.ts`
 * use: every endpoint becomes a local spy resolving `undefined` unless a test needs a real
 * shape from one. The shell cases keep the default empty file list; the Confirm All case
 * configures one synthetic file, parse response and empty candidate result so it can cross
 * the same public UI gates as the real wizard without fabricating component internals.
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

function assetGroup(groupId: string, state: AssetGroup['state'], fakeId: number): AssetGroup {
    const members = [
        {
            fakeAssetId: fakeId,
            fileId: `file-${fakeId}`,
            fileName: `file-${fakeId}.csv`,
            name: `Asset ${fakeId}`,
            isin: `ISIN-${fakeId}`,
            symbol: null,
        },
        ...(state === 'single'
            ? []
            : [
                  {
                      fakeAssetId: fakeId + 1,
                      fileId: `file-${fakeId + 1}`,
                      fileName: `file-${fakeId + 1}.csv`,
                      name: `Asset ${fakeId}`,
                      isin: `ISIN-${fakeId + 1}`,
                      symbol: null,
                  },
              ]),
    ];
    return {groupId, state, members, links: [], userTouched: false};
}

function assetGroupStepProps(groups: AssetGroup[], onconfirmall = vi.fn()) {
    return {
        groups,
        onpartition: vi.fn(),
        onconfirm: vi.fn(),
        onconfirmall,
        onprimary: vi.fn(),
        onreset: vi.fn(),
    };
}

describe('AssetGroupStep — Confirm All proposals', () => {
    afterEach(() => {
        cleanup();
    });

    it('appears only for at least two open proposals, invokes the parent once, and disappears when they settle', async () => {
        await setupI18n();
        const onconfirmall = vi.fn();
        const stable = assetGroup('stable', 'confirmed', 100);
        const alreadyConfirmed = assetGroup('already-confirmed', 'confirmed', 200);
        const firstProposal = assetGroup('proposal-a', 'proposed', 300);
        const secondProposal = assetGroup('proposal-b', 'proposed', 400);
        const single = assetGroup('single', 'single', 500);
        const callbacks = assetGroupStepProps([stable, alreadyConfirmed, firstProposal, single], onconfirmall);
        const view = render(AssetGroupStep, callbacks);

        expect(screen.queryByTestId('asset-group-confirm-all')).toBeNull();

        await view.rerender({...callbacks, groups: [stable, alreadyConfirmed, firstProposal, secondProposal, single]});
        const confirmAll = screen.getByTestId('asset-group-confirm-all');
        expect(confirmAll).toBeVisible();

        await fireEvent.click(confirmAll);
        expect(onconfirmall).toHaveBeenCalledTimes(1);
        expect(callbacks.onconfirm).not.toHaveBeenCalled();
        expect(callbacks.onpartition).not.toHaveBeenCalled();
        expect(callbacks.onprimary).not.toHaveBeenCalled();

        await view.rerender({
            ...callbacks,
            groups: [stable, alreadyConfirmed, {...firstProposal, state: 'confirmed'}, {...secondProposal, state: 'confirmed'}, single],
        });
        expect(screen.queryByTestId('asset-group-confirm-all')).toBeNull();
    });
});

describe('ImportWizardModal — Confirm All parent merge', () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        guideAnchors.clear();
        guideState.active = null;
        const broker = {
            id: 77,
            name: 'Owned confirm-all broker',
            default_import_plugin: 'owned-parser',
            opened_at: '2020-01-01',
            icon_url: null,
            portal_url: null,
        };
        vi.mocked(getEditableBrokers).mockReturnValue([broker]);
        vi.mocked(getBrokerInfo).mockImplementation((id) => (id === broker.id ? broker : null));
        vi.mocked(zodiosApi.list_files_api_v1_brokers_import_files_get).mockResolvedValue([
            {
                file_id: 'confirm-all-file',
                filename: 'confirm-all.csv',
                size_bytes: 512,
                status: 'uploaded',
                uploaded_at: '2026-09-14T08:00:00Z',
                compatible_plugins: ['owned-parser'],
                target_broker_id: broker.id,
            },
        ]);
        const mappings = [
            {fake_asset_id: 2_147_483_647, extracted_name: 'BTP 30-35 2.50% CUM', extracted_isin: 'IT0000000101'},
            {fake_asset_id: 2_147_483_646, extracted_name: 'BTP 30-35 2.50%', extracted_isin: 'IT0000000102'},
            {fake_asset_id: 2_147_483_645, extracted_name: 'BTP 40-45 3.50% EX', extracted_isin: 'IT0000000201'},
            {fake_asset_id: 2_147_483_644, extracted_name: 'BTP 40-45 3.50%', extracted_isin: 'IT0000000202'},
        ];
        vi.mocked(zodiosApi.parse_file_api_v1_brokers_import_files__file_id__parse_post).mockResolvedValue({
            file_id: 'confirm-all-file',
            plugin_code: 'owned-parser',
            broker_id: broker.id,
            transactions: mappings.map((mapping, index) => ({
                broker_id: broker.id,
                type: 'BUY',
                date: `2025-01-0${index + 1}`,
                asset_id: mapping.fake_asset_id,
                quantity: '1',
                cash: {code: 'EUR', amount: '-10'},
                description: `owned-row-${index + 1}`,
            })),
            asset_mappings: mappings.map((mapping) => ({
                ...mapping,
                extracted_symbol: null,
                candidates: [],
                selected_asset_id: null,
                notices: [],
            })),
            duplicates: null,
            warnings: [],
            validation_issues: [],
            field_todos: [],
        });
        vi.mocked(zodiosApi.get_asset_candidates_api_v1_brokers_import_asset_candidates_post).mockResolvedValue([]);
        await setupI18n();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
        guideState.active = null;
        vi.mocked(getEditableBrokers).mockReturnValue([]);
        vi.mocked(getBrokerInfo).mockReturnValue(null);
        vi.mocked(zodiosApi.list_files_api_v1_brokers_import_files_get).mockResolvedValue([]);
        vi.mocked(zodiosApi.get_asset_candidates_api_v1_brokers_import_asset_candidates_post).mockResolvedValue([]);
    });

    it('adds every open proposal in one state transition and runs exactly one downstream merge', async () => {
        mount();
        await waitFor(() => expect(screen.getByTestId('import-wizard-step1')).toHaveAttribute('data-busy', 'false'));
        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step2')).toHaveAttribute('data-busy', 'false'));

        const checkbox = screen.getByTestId('dt-row-checkbox-confirm-all-file');
        expect(checkbox).toHaveAttribute('data-state', 'unchecked');
        await fireEvent.click(checkbox);
        await waitFor(() => expect(screen.getByTestId('import-wizard-parse')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('import-wizard-parse'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-continue')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('import-wizard-continue'));

        await waitFor(() => expect(screen.getByTestId('asset-group-confirm-all')).toBeVisible());
        const proposedBefore = document.querySelectorAll('[data-testid^="asset-group-grp-"][data-state="proposed"]');
        expect(proposedBefore).toHaveLength(2);
        const mergeCountBefore = buildMergedTransactionsCalls.mock.calls.length;

        await fireEvent.click(screen.getByTestId('asset-group-confirm-all'));

        await waitFor(() => expect(screen.queryByTestId('asset-group-confirm-all')).toBeNull());
        expect(document.querySelectorAll('[data-testid^="asset-group-grp-"][data-state="proposed"]')).toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="asset-group-grp-"][data-state="confirmed"]')).toHaveLength(2);
        expect(buildMergedTransactionsCalls).toHaveBeenCalledTimes(mergeCountBefore + 1);
        expect(screen.getByTestId('import-wizard-content')).toHaveAttribute('data-busy', 'false');
        expect(screen.getByTestId('import-wizard-assets-continue')).toBeEnabled();
    });
});

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
 * Reachability boundary. The synthetic parse above intentionally stops at the
 * asset-group decision. A successful `handleImport()` handoff still depends on
 * selected rows surviving asset resolution and the duplicate/database recheck;
 * `pendingCreateTransactions` is explicitly excluded so the wizard cannot
 * re-import drafts the bulk editor already staged. That complete handoff stays
 * in E2E, where a real upload → parse → resolve → import can assert the
 * `import.bulk` coachmark.
 *
 * What *is* reachable and covered below: arming the guide at Step 1 on open,
 * each newly mounted host asking `startImportAt` for its semantic step after
 * the prior target click has completed and cleared the old active step.
 */
describe('ImportWizardModal — onboarding guide integration', () => {
    beforeEach(() => {
        guideState.active = null;
        guideMocks.startImportAt.mockClear();
        guideMocks.setStep.mockClear();
        guideMocks.queueContextual.mockClear();
        guideMocks.dismissHost.mockClear();
        guideMocks.finish.mockClear();
        guideMocks.skip.mockClear();
    });

    afterEach(() => {
        cleanup();
        guideAnchors.clear();
    });

    it('arms the import guide at the upload step the moment it opens', async () => {
        await setupI18n();
        mount();

        expect(guideMocks.startImportAt).toHaveBeenCalledTimes(1);
        expect(guideMocks.startImportAt).toHaveBeenCalledWith('import.upload', {current: 1, total: 4});
        expect(guideMocks.setStep).not.toHaveBeenCalled();
    });

    it('registers the first-mount footer CTA directly without Back/Next or scroll repair', async () => {
        await setupI18n();
        const scrollSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
        const windowScrollBefore = window.scrollY;
        mount();

        const content = screen.getByTestId('import-wizard-content');
        content.scrollTop = 37;
        const contentScrollBefore = content.scrollTop;
        const next = screen.getByTestId('import-wizard-next');

        await waitFor(() => expect(guideAnchors.get('import.action.upload')).toBe(next));
        expect(screen.queryByTestId('import-wizard-back')).toBeNull();
        expect(guideMocks.startImportAt).toHaveBeenCalledExactlyOnceWith('import.upload', {current: 1, total: 4});
        expect(window.scrollY).toBe(windowScrollBefore);
        expect(content.scrollTop).toBe(contentScrollBefore);
        expect(scrollSpy).not.toHaveBeenCalled();
    });

    it.each(TRANSACTION_BULK_STEP_IDS)('preempts active Bulk step %s and preserves that exact (flow, step) queue key', async (stepId) => {
        await setupI18n();
        guideState.active = {
            flow: 'transaction_bulk_guide',
            version: 1,
            stepId,
            mode: 'automatic',
        };

        mount();

        expect(guideMocks.queueContextual).toHaveBeenCalledExactlyOnceWith('transaction_bulk_guide' as ContextualOnboardingFlow, stepId);
        expect(guideMocks.dismissHost).toHaveBeenCalledTimes(1);
        expect(guideMocks.startImportAt).toHaveBeenCalledExactlyOnceWith('import.upload', {current: 1, total: 4});
        expect(guideMocks.queueContextual.mock.invocationCallOrder.at(0) ?? 0).toBeLessThan(guideMocks.dismissHost.mock.invocationCallOrder.at(0) ?? 0);
        expect(guideMocks.dismissHost.mock.invocationCallOrder.at(0) ?? 0).toBeLessThan(guideMocks.startImportAt.mock.invocationCallOrder.at(0) ?? 0);
        expect(guideState.active).toMatchObject({flow: 'import_guide', stepId: 'import.upload'});
    });

    it('asks the controller to start each host step after the prior target action completes', async () => {
        await setupI18n();
        mount();
        expect(guideMocks.startImportAt).toHaveBeenCalledWith('import.upload', {current: 1, total: 4});

        // Zero pending files: step1CanProceed is true, so Next uploads nothing and
        // moves straight to Step 2. In the real overlay the same target click
        // completes Upload and clears active before this host effect runs.
        guideState.active = null;
        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-2')).toHaveAttribute('data-step-id', 'select'));
        expect(guideMocks.startImportAt).toHaveBeenLastCalledWith('import.select', {current: 2, total: 4});

        // The host still reports Upload when the user goes back. The real guide
        // then decides from persisted due/replay state whether it should show.
        guideState.active = null;
        await fireEvent.click(screen.getByTestId('import-wizard-back'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-1')).toHaveAttribute('data-step-id', 'upload'));
        expect(guideMocks.startImportAt).toHaveBeenLastCalledWith('import.upload', {current: 1, total: 4});
        expect(guideMocks.setStep).not.toHaveBeenCalled();
    });

    it('dismisses the current guide host once the parent closes without a completed handoff', async () => {
        await setupI18n();
        const {onClose, rerender} = mount();
        expect(guideMocks.startImportAt).toHaveBeenCalledTimes(1);

        // `handleClose()` only calls the `onClose` prop — same as the real app, the
        // wizard does not own `open`; the parent reacts to `onClose` by flipping it.
        // That flip is what the guide-dismiss effect actually watches, so it is
        // simulated explicitly rather than asserting dismissal off a callback alone.
        await fireEvent.click(screen.getByTestId('import-wizard-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
        expect(guideMocks.dismissHost).not.toHaveBeenCalled();

        await rerender({open: false});

        expect(guideMocks.dismissHost).toHaveBeenCalledExactlyOnceWith({restartAtFirst: true});
    });

    it('dismisses the current guide host even after navigating to Step 2 before closing', async () => {
        await setupI18n();
        const {onClose, rerender} = mount();
        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-2')).toHaveAttribute('data-step-id', 'select'));
        guideMocks.dismissHost.mockClear();

        await fireEvent.click(screen.getByTestId('import-wizard-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
        await rerender({open: false});

        expect(guideMocks.dismissHost).toHaveBeenCalledExactlyOnceWith({restartAtFirst: true});
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

type CapturedImportWizardProps = {
    readonly open: boolean;
    onClose: () => void;
    onImportBatch: (creates: Array<{tx: TransactionCreateItem; todos: []}>, guideProgress?: {current: number; total: number}) => void;
};

type CapturedFormProps = {
    readonly open: boolean;
    onClose: () => void;
};

const WORKSPACE_ORIGIN_TX: TXReadItem = {
    id: 91_001,
    broker_id: 77,
    asset_id: 101,
    type: 'BUY',
    date: '2026-09-13',
    quantity: '1',
    cash: {code: 'EUR', amount: '-10'},
    related_transaction_id: null,
    tags: [],
    description: 'handoff-origin',
};

const BULK_HANDOFF_ORIGINS = [
    {origin: 'edit', intent: {action: 'edit', txIds: [WORKSPACE_ORIGIN_TX.id]}, opensImportOnMount: false},
    {origin: 'clone', intent: {action: 'clone', txIds: [WORKSPACE_ORIGIN_TX.id]}, opensImportOnMount: false},
    {origin: 'create', intent: {action: 'create'}, opensImportOnMount: false},
    // The transactions-page toolbar maps its top-level Import action to this intent.
    {origin: 'toolbar', intent: {action: 'import'}, opensImportOnMount: true},
] satisfies ReadonlyArray<{origin: string; intent: WorkspaceIntent; opensImportOnMount: boolean}>;

function capturedImportWizard(): CapturedImportWizardProps {
    if (!bulkChildProbe.importProps) throw new Error('TransactionBulkModal did not mount its ImportWizard child');
    return bulkChildProbe.importProps as unknown as CapturedImportWizardProps;
}

function capturedForm(): CapturedFormProps {
    if (!bulkChildProbe.formProps) throw new Error('TransactionBulkModal did not mount its TransactionForm child');
    return bulkChildProbe.formProps as unknown as CapturedFormProps;
}

function importedBatch(origin: string): Array<{tx: TransactionCreateItem; todos: []}> {
    return [
        {
            tx: {
                broker_id: 77,
                type: 'BUY',
                date: '2026-09-14',
                asset_id: 101,
                quantity: '1',
                cash: {code: 'EUR', amount: '-10'},
                tags: [],
                description: `handoff-${origin}`,
            } as TransactionCreateItem,
            todos: [],
        },
    ];
}

async function openImportFromBulkOrigin(origin: (typeof BULK_HANDOFF_ORIGINS)[number]) {
    render(TransactionBulkModal, {open: true, intent: origin.intent, onClose: vi.fn()});

    if (!origin.opensImportOnMount) {
        await waitFor(() => expect(capturedForm().open).toBe(true));
        capturedForm().onClose();
        await tick();
        await waitFor(() => expect(capturedForm().open).toBe(false));
        await fireEvent.click(screen.getByTestId('tx-bulk-import'));
    }

    await waitFor(() => expect(capturedImportWizard().open).toBe(true));
    return capturedImportWizard();
}

describe('TransactionBulkModal — Import success-only handoff', () => {
    beforeEach(async () => {
        cleanup();
        vi.clearAllMocks();
        guideAnchors.clear();
        guideState.active = null;
        bulkChildProbe.interceptImportWizard = true;
        bulkChildProbe.importProps = null;
        bulkChildProbe.formProps = null;
        vi.mocked(getEditableBrokers).mockReturnValue([]);
        vi.mocked(getBrokerInfo).mockReturnValue(null);
        txStoreSetAll([WORKSPACE_ORIGIN_TX], []);
        await setupI18n();
    });

    afterEach(() => {
        cleanup();
        txStoreInvalidate();
        guideAnchors.clear();
        guideState.active = null;
        bulkChildProbe.interceptImportWizard = false;
        bulkChildProbe.importProps = null;
        bulkChildProbe.formProps = null;
    });

    it('does not start import.bulk when top-level toolbar Import closes without onImportBatch', async () => {
        const toolbar = BULK_HANDOFF_ORIGINS.find((entry) => entry.origin === 'toolbar');
        if (!toolbar) throw new Error('toolbar Import origin is missing from the handoff matrix');
        const wizard = await openImportFromBulkOrigin(toolbar);

        wizard.onClose();
        await tick();
        await waitFor(() => expect(capturedImportWizard().open).toBe(false));

        expect(screen.getByTestId('tx-bulk-modal-root')).toBeInTheDocument();
        expect(guideMocks.startImportAt).not.toHaveBeenCalled();
    });

    it.each(BULK_HANDOFF_ORIGINS)('starts import.bulk after onImportBatch succeeds from the $origin workspace origin', async (origin) => {
        const wizard = await openImportFromBulkOrigin(origin);
        const progress = {current: 8, total: 8};

        wizard.onImportBatch(importedBatch(origin.origin), progress);
        await tick();

        await waitFor(() => expect(capturedImportWizard().open).toBe(false));
        await waitFor(() => expect(guideMocks.startImportAt).toHaveBeenCalledExactlyOnceWith('import.bulk', progress));
    });
});
