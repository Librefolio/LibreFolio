// @vitest-environment jsdom
/**
 * donations.svelte.ts — the one rule behind every donation invitation of the app (F05, the managed profile; lot A9 of
 * workstream A): `donationsVisible()` is true only once the server has answered (`instanceConfig.loaded`) **and** said
 * `profile: 'selfhosted'`.
 *
 * The contract under test (approved by the coordinator, 17/10):
 *   - DON-01: the module sits next to this test and exports `donationsVisible` as a function;
 *   - DON-02: visible = loaded && profile === 'selfhosted', whatever else the store says. Before the answer it is false
 *     although the defaults the store holds until then (`DEFAULT_INSTANCE_CONFIG`) say self-hosted: a managed instance
 *     never flashes a donation while its `GET /system/instance` is in flight. A request that failed before any answer
 *     leaves it false; a forced reload that fails after an answer leaves the answer in force, so `failed` changes
 *     nothing;
 *   - DON-03: it is reactive — read inside an effect (a template, a `$derived`), it follows `instanceConfig` without a
 *     reload: false before the answer, true once it says self-hosted, false again when a forced reload says managed.
 *
 * Mocks, all owned here: `$lib/features/instance/instanceConfig.svelte` is a fake with the real store's shape —
 * enumerable getters over a `$state` box (`reactiveBox`) — so a test lands the server's answer by writing the box, as
 * `load()` does; `load` is a spy that answers nothing of its own.
 *
 * Written red-first, before `donations.svelte.ts` exists: the module is loaded lazily through a glob, in a guarded
 * `beforeAll` (the pattern of `GapFixStep.test.ts`), so every case fails on its own, naming the missing module.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {assertEffectsRun, recordReads} from '$test/runes.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    /** What the real store holds until the server answers: `DEFAULT_INSTANCE_CONFIG`, a self-hosted instance. */
    const BEFORE_ANSWER = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as InstanceConfig;
    return {
        BEFORE_ANSWER,
        instance: reactiveBox<{config: InstanceConfig; loaded: boolean; failed: boolean}>({config: BEFORE_ANSWER, loaded: false, failed: false}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
    };
});

vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: mocks.BEFORE_ANSWER,
    fetchInstanceConfigFromApi: () => Promise.reject(new Error('no network in this test')),
    instanceConfig: {
        get config() {
            return mocks.instance.config;
        },
        get loaded() {
            return mocks.instance.loaded;
        },
        get failed() {
            return mocks.instance.failed;
        },
        load: mocks.instanceLoad,
    },
}));

const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {...SELFHOSTED, profile: 'managed'};

// ---------------------------------------------------------------------------
// Loading the module under test
// ---------------------------------------------------------------------------

interface DonationsModule {
    donationsVisible(): boolean;
}

// A lazy glob rather than a literal import: the module does not exist yet, and a missing file must fail each case on
// its own, naming it, instead of failing the whole file at collection.
const DONATIONS_MODULES = import.meta.glob<Partial<DonationsModule>>('./donations.svelte.ts');

/** What the loading hook found: the module, or why it could not be loaded. */
let loaded: DonationsModule | {error: unknown} | undefined;

beforeAll(async () => {
    assertEffectsRun();
    try {
        const load = DONATIONS_MODULES['./donations.svelte.ts'];
        if (!load) throw new Error('donations.svelte.ts cannot be found next to this test (src/lib/features/support/)');
        const mod = await load();
        if (typeof mod.donationsVisible !== 'function') throw new Error('donations.svelte.ts does not export donationsVisible() as a function');
        loaded = mod as DonationsModule;
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

function subject(): DonationsModule {
    if (loaded === undefined) throw new Error('the module under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded;
}

/** The store as `load()` leaves it: the configuration in force, whether the server answered, whether the last request failed. */
function storeSays(state: {config: InstanceConfig; loaded: boolean; failed: boolean}): void {
    mocks.instance.config = state.config;
    mocks.instance.loaded = state.loaded;
    mocks.instance.failed = state.failed;
    flushSync();
}

beforeEach(() => {
    storeSays({config: mocks.BEFORE_ANSWER, loaded: false, failed: false});
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockImplementation(() => Promise.resolve());
});

describe('donationsVisible() — the server has answered, and it said self-hosted', () => {
    // red until A9
    it('DON-01: the module exports donationsVisible() as a function', () => {
        expect(typeof subject().donationsVisible).toBe('function');
    });

    const CASES: Array<{label: string; config: InstanceConfig; loaded: boolean; failed: boolean; visible: boolean}> = [
        {label: 'before the answer — the defaults say self-hosted, but nobody asked the server yet', config: mocks.BEFORE_ANSWER, loaded: false, failed: false, visible: false},
        {label: 'the request failed before any answer', config: mocks.BEFORE_ANSWER, loaded: false, failed: true, visible: false},
        {label: 'answered: managed', config: MANAGED, loaded: true, failed: false, visible: false},
        {label: 'answered: self-hosted', config: SELFHOSTED, loaded: true, failed: false, visible: true},
        {label: 'answered self-hosted, then a forced reload failed — the answer in force is still self-hosted', config: SELFHOSTED, loaded: true, failed: true, visible: true},
        {label: 'answered managed, then a forced reload failed', config: MANAGED, loaded: true, failed: true, visible: false},
    ];

    // red until A9
    it.each(CASES)('DON-02: $label → $visible', ({config, loaded, failed, visible}) => {
        const {donationsVisible} = subject();

        storeSays({config, loaded, failed});

        expect(donationsVisible()).toBe(visible);
    });
});

describe('donationsVisible() — reactive: read inside an effect, it follows instanceConfig', () => {
    // red until A9
    it('DON-03: false before the answer, true once it says self-hosted, false again when a forced reload says managed', () => {
        const {donationsVisible} = subject();
        const reads = recordReads(() => donationsVisible());
        try {
            expect(reads.values.at(-1), 'before the answer: nothing to show yet').toBe(false);

            storeSays({config: SELFHOSTED, loaded: true, failed: false});
            expect(reads.values.at(-1), 'the answer said self-hosted: the effect read it again').toBe(true);

            storeSays({config: MANAGED, loaded: true, failed: false});
            expect(reads.values.at(-1), 'a forced reload said managed: the effect read it again').toBe(false);

            expect(
                reads.values.every((value) => typeof value === 'boolean'),
                'every read answered a boolean',
            ).toBe(true);
        } finally {
            reads.stop();
        }
    });
});
