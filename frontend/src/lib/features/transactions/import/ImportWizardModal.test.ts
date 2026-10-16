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
import TransactionBulkModal, {type WorkspaceIntent} from '../bulk/TransactionBulkModal.svelte';
import AssetGroupStep from '$lib/features/transactions/import/AssetGroupStep.svelte';
import {TRANSACTION_BULK_STEP_IDS, type ContextualOnboardingFlow, type GuidedOnboardingFlow} from '$lib/features/onboarding/onboardingGuideCatalog';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import type {AssetGroup} from '$lib/utils/assetGrouping';
import type {TransactionCreateItem} from '$lib/types';
import {zodiosApi} from '$lib/api';
import {ensureBrokersLoaded, getBrokerInfo, getEditableBrokers, refreshAllBrokers} from '$lib/stores/reference/brokerStore';
import {ensureTypesLoaded} from '$lib/features/transactions/transactionTypeStore';
import {txStoreInvalidate, txStoreSetAll} from '$lib/features/transactions/txStore.svelte';
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

const {brokerModalProbe} = vi.hoisted(() => ({
    brokerModalProbe: {props: [] as Record<string, unknown>[]},
}));

/*
 * The wizard keeps its create-mode BrokerModal mounted (`isOpen` only shows it), and that
 * modal's `oncreated` prop is the one door to the broker refresh that follows a broker
 * created from step 1. Recording each mount's props lets a test walk through that door
 * directly, while the real BrokerModal still renders — the same delegation as the
 * ImportWizardModal wrapper above.
 */
vi.mock('$lib/features/brokers/BrokerModal.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/brokers/BrokerModal.svelte')>();
    const renderActual = actual.default as unknown as (...args: unknown[]) => unknown;
    return {
        ...actual,
        default: ((...args: unknown[]) => {
            brokerModalProbe.props.push(args[1] as Record<string, unknown>);
            return renderActual(...args);
        }) as typeof actual.default,
    };
});

vi.mock('../form/TransactionFormModal.svelte', () => ({
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
vi.mock('$lib/features/transactions/transactionTypeStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/transactions/transactionTypeStore')>()),
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
vi.mock('$lib/features/transactions/txCommitApi', () => ({
    commitTransactions: vi.fn(async () => ({committed: true, results: [], issues: []})),
    validateTransactions: vi.fn(async () => ({committed: true, issues: [], rawResponse: {wac_results: []}})),
}));

const {buildMergedTransactionsCalls} = vi.hoisted(() => ({
    buildMergedTransactionsCalls: vi.fn(),
}));

vi.mock('$lib/features/transactions/import/importMerge', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/transactions/import/importMerge')>();
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
                can_delete: true,
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
        // Next answers only once the broker list the wizard loads on open has arrived.
        await waitFor(() => expect(screen.getByTestId('import-wizard-step1')).toHaveAttribute('data-busy', 'false'));

        // Zero pending files: step1CanProceed is true, so Next uploads nothing and
        // moves straight to Step 2. In the real overlay the same target click
        // completes Upload and clears active before this host effect runs.
        guideState.active = null;
        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-2')).toHaveAttribute('data-step-id', 'select'));
        // `data-step-id` names the stepper node, not the current step: the Step 2 content proves Next moved on.
        await waitFor(() => expect(screen.getByTestId('import-wizard-step2')).toBeInTheDocument());
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
        await waitFor(() => expect(screen.getByTestId('import-wizard-step1')).toHaveAttribute('data-busy', 'false'));
        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-2')).toHaveAttribute('data-step-id', 'select'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step2')).toBeInTheDocument());
        guideMocks.dismissHost.mockClear();

        await fireEvent.click(screen.getByTestId('import-wizard-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
        await rerender({open: false});

        expect(guideMocks.dismissHost).toHaveBeenCalledExactlyOnceWith({restartAtFirst: true});
    });

    it('never finishes or skips the guide, and never commits a transaction batch, on its own', async () => {
        await setupI18n();
        const {onImportBatch, rerender} = mount();

        await waitFor(() => expect(screen.getByTestId('import-wizard-step1')).toHaveAttribute('data-busy', 'false'));
        await fireEvent.click(screen.getByTestId('import-wizard-next'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-2')).toHaveAttribute('data-step-id', 'select'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step2')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('import-wizard-back'));
        await waitFor(() => expect(screen.getByTestId('import-wizard-step-1')).toHaveAttribute('data-step-id', 'upload'));
        await fireEvent.click(screen.getByTestId('import-wizard-close'));
        await rerender({open: false});

        expect(guideMocks.finish).not.toHaveBeenCalled();
        expect(guideMocks.skip).not.toHaveBeenCalled();
        expect(onImportBatch).not.toHaveBeenCalled();
    });
});

/**
 * ImportWizardModal — step 1 waits for the broker list.
 *
 * Opening the wizard starts the broker, transaction-type and import-plugin loads without
 * awaiting them, while Step 1 is already on screen. Step 2 asks the server for the files of
 * the brokers the wizard knows the moment Next moves to it, so a Next pressed before that list
 * arrives asks with `broker_ids: []`: every broker panel opens empty and the file the user just
 * uploaded is hidden. Creating a broker from Step 1 reopens the same window, because its
 * `oncreated` refresh replaces the list with nothing on screen saying so.
 *
 * Pinned from the outside only: Step 1 publishes `data-busy="true"` and Next stays disabled for
 * as long as ANY broker load is in flight (the open load, the refresh after a create, or both
 * at once); a Next click that lands anyway leaves the wizard on Step 1 without asking for files;
 * a failed transaction-types load releases Step 1 instead of locking it.
 *
 * Every pending load is a deferred held by the test and released in `afterEach`, so no promise
 * outlives the test that held it.
 */
describe('ImportWizardModal — step 1 waits for the broker list', () => {
    const held: Array<() => void> = [];

    /** A promise this test resolves by hand, tracked so `afterEach` can release it. */
    function hold(): {promise: Promise<void>; resolve: () => void} {
        let resolve!: () => void;
        const promise = new Promise<void>((done) => {
            resolve = done;
        });
        held.push(resolve);
        return {promise, resolve};
    }

    const stepOne = () => screen.getByTestId('import-wizard-step1');
    const nextButton = () => screen.getByTestId('import-wizard-next');
    const listFiles = () => vi.mocked(zodiosApi.list_files_api_v1_brokers_import_files_get);

    /** The `oncreated` prop the wizard handed its create-mode BrokerModal on this mount. */
    function createdBrokerHandler(): (detail: {id: number}) => void {
        const handler = brokerModalProbe.props.filter((props) => props.mode === 'create').at(-1)?.oncreated;
        if (typeof handler !== 'function') throw new Error('ImportWizardModal did not mount its create-mode BrokerModal with an oncreated handler');
        return handler as (detail: {id: number}) => void;
    }

    beforeEach(async () => {
        guideState.active = null;
        brokerModalProbe.props.length = 0;
        vi.mocked(ensureBrokersLoaded).mockClear();
        vi.mocked(refreshAllBrokers).mockClear();
        vi.mocked(ensureTypesLoaded).mockClear();
        vi.mocked(getEditableBrokers).mockClear();
        // The `$lib/api` Proxy caches one spy per endpoint for the whole file.
        listFiles().mockClear();
        await setupI18n();
    });

    afterEach(async () => {
        for (const release of held.splice(0)) release();
        await tick();
        cleanup();
        guideAnchors.clear();
        guideState.active = null;
        brokerModalProbe.props.length = 0;
        // `mockReset()` empties the once-queues but also drops the file-level
        // `mockResolvedValue(undefined)`, so each default is restored explicitly.
        vi.mocked(ensureBrokersLoaded).mockReset().mockResolvedValue(undefined);
        vi.mocked(refreshAllBrokers).mockReset().mockResolvedValue(undefined);
        vi.mocked(ensureTypesLoaded).mockReset().mockResolvedValue(undefined);
        vi.mocked(getEditableBrokers)
            .mockReset()
            .mockImplementation(() => []);
        vi.mocked(getBrokerInfo).mockReset().mockReturnValue(null);
    });

    it('V1 keeps Next disabled and Step 1 busy until the broker list has loaded', async () => {
        const brokersLoad = hold();
        vi.mocked(ensureBrokersLoaded).mockImplementationOnce(() => brokersLoad.promise);
        mount();

        // Precondition: the open load is in flight and Step 1 says so.
        await waitFor(() => expect(stepOne()).toHaveAttribute('data-busy', 'true'));
        expect(ensureBrokersLoaded).toHaveBeenCalled();

        expect(nextButton(), 'V1: Next must stay disabled while Step 1 is busy loading the broker list').toBeDisabled();

        brokersLoad.resolve();
        await waitFor(() => expect(stepOne()).toHaveAttribute('data-busy', 'false'));
        await waitFor(() => expect(nextButton()).toBeEnabled());
    });

    it('V2 ignores a Next click made while the broker list loads and asks for no files until it has arrived', async () => {
        const broker = {
            id: 77,
            name: 'Broker list gate',
            default_import_plugin: 'owned-parser',
            opened_at: '2020-01-01',
            icon_url: null,
            portal_url: null,
        };
        // The store already holds the broker; the wizard only learns it when its load finishes.
        vi.mocked(getEditableBrokers).mockReturnValue([broker]);
        vi.mocked(getBrokerInfo).mockImplementation((id) => (id === broker.id ? broker : null));
        const brokersLoad = hold();
        vi.mocked(ensureBrokersLoaded).mockImplementationOnce(() => brokersLoad.promise);
        mount();
        await waitFor(() => expect(stepOne()).toHaveAttribute('data-busy', 'true'));

        // Svelte's delegated handler can still run when jsdom clicks a disabled button, so the
        // click proves nothing by itself: the outcome below is what is asserted.
        await fireEvent.click(nextButton());
        brokersLoad.resolve();

        // Barrier: the load has finished, and Step 1 is still the step on screen.
        await waitFor(() => {
            const step1 = screen.queryByTestId('import-wizard-step1');
            expect(step1, 'V2: a Next click made while the broker list was loading must leave the wizard on Step 1').not.toBeNull();
            expect(step1).toHaveAttribute('data-busy', 'false');
        });
        expect(screen.queryByTestId('import-wizard-step2')).toBeNull();
        expect(listFiles(), 'V2: no broker files may be requested before the broker list has arrived').not.toHaveBeenCalled();

        // Once the list is in, Next works and asks for the files of the broker it now knows.
        await waitFor(() => expect(nextButton()).toBeEnabled());
        await fireEvent.click(nextButton());
        await waitFor(() => expect(screen.getByTestId('import-wizard-step2')).toHaveAttribute('data-busy', 'false'));
        expect(screen.queryByTestId('import-wizard-step1')).toBeNull();
        expect(listFiles()).toHaveBeenCalledWith({queries: {broker_ids: [broker.id]}});
        expect(listFiles()).not.toHaveBeenCalledWith({queries: {broker_ids: []}});
    });

    it('V3 releases Step 1 and Next when the transaction types fail to load', async () => {
        vi.mocked(ensureTypesLoaded).mockRejectedValueOnce(new Error('V3 synthetic transaction-types failure'));
        mount();
        await waitFor(() => expect(ensureTypesLoaded).toHaveBeenCalled());

        await waitFor(() => expect(stepOne(), 'V3: a failed transaction-types load must not leave Step 1 busy').toHaveAttribute('data-busy', 'false'));
        expect(nextButton()).toBeEnabled();
    });

    it('V4 disables Next again while the broker list refreshes after a broker is created from Step 1', async () => {
        mount();
        await waitFor(() => expect(stepOne()).toHaveAttribute('data-busy', 'false'));
        await waitFor(() => expect(nextButton()).toBeEnabled());

        const refresh = hold();
        vi.mocked(refreshAllBrokers).mockImplementationOnce(() => refresh.promise);
        createdBrokerHandler()({id: 4242});
        await tick();

        // Precondition: the create handler started the one refresh this test holds.
        expect(refreshAllBrokers).toHaveBeenCalledTimes(1);
        expect(nextButton(), 'V4: Next must stay disabled while the broker list refreshes after a create').toBeDisabled();
        expect(stepOne()).toHaveAttribute('data-busy', 'true');

        refresh.resolve();
        await waitFor(() => expect(stepOne()).toHaveAttribute('data-busy', 'false'));
        await waitFor(() => expect(nextButton()).toBeEnabled());
    });

    it('V4b keeps Next disabled until every overlapping broker load has finished', async () => {
        const openLoad = hold();
        const refresh = hold();
        vi.mocked(ensureBrokersLoaded).mockImplementationOnce(() => openLoad.promise);
        vi.mocked(refreshAllBrokers).mockImplementationOnce(() => refresh.promise);
        mount();
        await waitFor(() => expect(stepOne()).toHaveAttribute('data-busy', 'true'));
        expect(nextButton(), 'V4b: Next must stay disabled while the open load is in flight').toBeDisabled();

        createdBrokerHandler()({id: 4343});
        await tick();
        expect(refreshAllBrokers).toHaveBeenCalledTimes(1);
        expect(nextButton(), 'V4b: Next must stay disabled while both loads are in flight').toBeDisabled();

        // The refresh lands first. Barrier: its continuation has read the refreshed list, the one
        // step that follows `refreshAllBrokers()`; only then can its end be judged.
        const readsBefore = vi.mocked(getEditableBrokers).mock.calls.length;
        refresh.resolve();
        await waitFor(() => expect(vi.mocked(getEditableBrokers).mock.calls.length).toBeGreaterThan(readsBefore));
        await tick();
        expect(nextButton(), 'V4b: the refresh ending first must not release Next while the open load is still in flight').toBeDisabled();
        expect(stepOne()).toHaveAttribute('data-busy', 'true');

        openLoad.resolve();
        await waitFor(() => expect(stepOne()).toHaveAttribute('data-busy', 'false'));
        await waitFor(() => expect(nextButton()).toBeEnabled());
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
