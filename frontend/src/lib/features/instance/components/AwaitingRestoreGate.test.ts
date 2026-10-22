// @vitest-environment jsdom
/**
 * AwaitingRestoreGate — the root layout's gate of the «awaiting restore» mode (workstream H, lot H-62).
 *
 * When the hosting panel restores the instance on an empty volume, `GET /api/v1/system/instance` answers
 * `mode: "awaiting_restore"` and every other route answers 423. The customer must then see
 * `InstanceAwaitingRestorePage`, not the app nor the login.
 *
 * The contract under test:
 *   - props `children: Snippet`, `loadConfig?: () => Promise<void>`, `readMode?: () => string | undefined`; the defaults
 *     are `instanceConfig.load()` and `instanceConfig.config.mode` (`$lib/features/instance/instanceConfig.svelte`);
 *   - on mount the gate calls `loadConfig()` once;
 *   - while `readMode()` is `"awaiting_restore"` it renders the page (`instance-awaiting-restore`) and does not mount the
 *     children at all; for any other mode — `"normal"`, `undefined` (a config without the field, the defaults before the
 *     answer), an unknown one — it renders the children and not the page;
 *   - the choice follows the mode: flipping it swaps the page and the children both ways, with no reload.
 *
 * The children are a `createRawSnippet` whose `setup` counts the mounts, so "not rendered" is checked as "never
 * mounted", not only "not visible". The mode is a `reactiveBox` (a `$state` created in a `.svelte.ts`), the way a
 * store's getter is reactive: the gate re-reads it as the app would read `instanceConfig.config.mode`.
 *
 * The page is the real component (its own spec is `InstanceAwaitingRestorePage.test.ts`): only its root testid is read
 * here. `$lib/api` is a mock so that its default poll never reaches the network (30 s: it never fires within a case),
 * and `instanceConfig.svelte` is a fake of the real store's shape (a getter over a `reactiveBox`, a `load` spy) for the
 * cases of the defaults.
 *
 * Red until H-62: neither the gate nor the page exists, so the file fails to import.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, flushSync, tick} from 'svelte';
import {cleanup, render, screen, setupI18n} from '$test/component';
import {assertEffectsRun, reactiveBox} from '$test/runes.svelte';
import AwaitingRestoreGate from './AwaitingRestoreGate.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    return {
        // What the fake `instanceConfig.config` returns: a config with or without `mode`.
        config: reactiveBox<{value: {profile: string; mode?: string}}>({value: {profile: 'managed'}}),
        load: vi.fn(() => Promise.resolve()).mockName('instanceConfig.load'),
        getInstanceConfig: vi.fn(() => new Promise(() => {})).mockName('zodiosApi.get_instance_config_api_v1_system_instance_get'),
    };
});

vi.mock('$lib/api', () => ({zodiosApi: {get_instance_config_api_v1_system_instance_get: mocks.getInstanceConfig}}));
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    instanceConfig: {
        get config() {
            return mocks.config.value;
        },
        get loaded() {
            return true;
        },
        get failed() {
            return false;
        },
        load: mocks.load,
    },
    fetchInstanceConfigFromApi: mocks.getInstanceConfig,
}));

const PAGE = 'instance-awaiting-restore';
const CHILD = 'awaiting-restore-gate-child';

/** The app the gate guards: one element, and a count of how many times it was mounted. */
function childrenProbe() {
    const mounts = {count: 0};
    const children = createRawSnippet(() => ({
        render: () => `<div data-testid="${CHILD}">app</div>`,
        setup: () => {
            mounts.count += 1;
        },
    }));
    return {children, mounts};
}

/** Mount the gate with an injected mode the test flips, and an injected `loadConfig`. */
function mountGate(initialMode: string | undefined) {
    const mode = reactiveBox<{value: string | undefined}>({value: initialMode});
    const loadConfig = vi.fn(() => Promise.resolve()).mockName('loadConfig');
    const {children, mounts} = childrenProbe();
    render(AwaitingRestoreGate, {props: {children, loadConfig, readMode: () => mode.value}});
    flushSync();
    return {mode, loadConfig, mounts};
}

function expectPageOnly(why: string, mounts?: {count: number}): void {
    expect(screen.getByTestId(PAGE), why).toBeInTheDocument();
    expect(screen.queryByTestId(CHILD), `${why}: the app is not on screen`).toBeNull();
    if (mounts) expect(mounts.count, `${why}: the app was never mounted`).toBe(0);
}

function expectChildrenOnly(why: string): void {
    expect(screen.getByTestId(CHILD), why).toBeInTheDocument();
    expect(screen.queryByTestId(PAGE), `${why}: no awaiting-restore page`).toBeNull();
}

beforeAll(async () => {
    await setupI18n('en');
    // The absences below would pass vacuously where effects never run.
    assertEffectsRun();
});

beforeEach(() => {
    mocks.config.value = {profile: 'managed'};
    mocks.load.mockClear();
    mocks.getInstanceConfig.mockClear();
});

afterEach(() => {
    cleanup();
});

describe('AwaitingRestoreGate — injected config', () => {
    it('loads the config once on mount', () => {
        const {loadConfig} = mountGate('normal');

        expect(loadConfig).toHaveBeenCalledTimes(1);
    });

    it('shows the awaiting-restore page, and never mounts the app, while the mode is awaiting_restore', () => {
        const {mounts} = mountGate('awaiting_restore');

        expectPageOnly('awaiting the restore', mounts);
    });

    it.each([
        ['normal', 'normal'],
        ['absent (a config without the field, or the defaults)', undefined],
        ['unknown', 'maintenance'],
    ])('shows the app, not the page, when the mode is %s', (_case, mode) => {
        const {mounts} = mountGate(mode);

        expectChildrenOnly(`mode ${String(mode)}`);
        expect(mounts.count, 'mounted once').toBe(1);
    });

    it('replaces the app with the page when the mode turns awaiting_restore, and gives it back when it turns normal', async () => {
        const {mode} = mountGate('normal');
        expectChildrenOnly('Barrier: the app runs');

        mode.value = 'awaiting_restore';
        await tick();
        expectPageOnly('the mode began after the app had started');

        mode.value = 'normal';
        await tick();
        expectChildrenOnly('the restore is over');
    });
});

describe('AwaitingRestoreGate — defaults: instanceConfig', () => {
    it('calls instanceConfig.load() on mount', () => {
        const {children} = childrenProbe();
        render(AwaitingRestoreGate, {props: {children}});
        flushSync();

        expect(mocks.load).toHaveBeenCalledTimes(1);
    });

    it('reads instanceConfig.config.mode: the page while awaiting_restore, the app once normal', async () => {
        mocks.config.value = {profile: 'managed', mode: 'awaiting_restore'};
        const {children, mounts} = childrenProbe();
        render(AwaitingRestoreGate, {props: {children}});
        flushSync();
        expectPageOnly('instanceConfig says awaiting_restore', mounts);

        mocks.config.value = {profile: 'managed', mode: 'normal'};
        await tick();
        expectChildrenOnly('instanceConfig says normal');
    });

    it('shows the app when the config carries no mode (the defaults before an answer)', () => {
        const {children} = childrenProbe();
        render(AwaitingRestoreGate, {props: {children}});
        flushSync();

        expectChildrenOnly('no mode');
    });
});
