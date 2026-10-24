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
 * Lot B-33, the start's part (an unreadable restore state serves no data): `GET /api/v1/system/instance` answers
 * `restore_interrupted: true` and the backend refuses every other route with 423 `instance_restore_interrupted`. The
 * gate gains the optional prop `readRestoreInterrupted?: () => boolean`, by default
 * `instanceConfig.config.restore_interrupted === true`; while it is true the gate renders `InstanceRestoreInterruptedPage`
 * (`instance-restore-interrupted`) and neither the children (never mounted) nor the awaiting page: interrupted wins over
 * awaiting. False, absent or anything but `true` leaves the H-62 behaviour as it is, and the choice follows the flag
 * both ways. The interrupted page is the real component (its spec is `InstanceRestoreInterruptedPage.test.ts`); its
 * default poll reads the same `$lib/api` mock, which never answers. Red until B-33: the gate ignores the prop and the
 * field, so the interrupted page never shows (and the awaiting page or the app stays on screen).
 *
 * Lot H5-3: the gate gains the optional prop `readRestoreInterruptedReason?: () => 'restore_state' | 'owner_assignment' |
 * null | undefined`, by default `instanceConfig.config.restore_interrupted_reason ?? null`, and passes it to the page as
 * `reason`. The precedence is unchanged (interrupted wins over awaiting, else the routes); a reason on its own, with
 * `restore_interrupted` false, shows nothing. Which page variant is on screen is read from the docs link
 * (`instance-restore-interrupted-docs`), an untranslated contract: the owner reason links `/mkdocs/admin/hosting_panel_backups/#restore-owner-pending`,
 * the restore-state one (also absent and null) the `#backup-pending-unreadable` anchor. Red until H5-3:
 * the gate ignores the prop and the field, so the owner cases still show the restore-state link.
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
        config: reactiveBox<{value: {profile: string; mode?: string; restore_interrupted?: unknown; restore_interrupted_reason?: unknown}}>({value: {profile: 'managed'}}),
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

describe('AwaitingRestoreGate — an unreadable restore state (B-33)', () => {
    const INTERRUPTED = 'instance-restore-interrupted';

    /** Mount the gate with an injected mode and an injected interrupted flag, both of which the test flips. */
    function mountInterruptedGate(initialMode: string | undefined, initialInterrupted: boolean) {
        const mode = reactiveBox<{value: string | undefined}>({value: initialMode});
        const interrupted = reactiveBox<{value: boolean}>({value: initialInterrupted});
        const loadConfig = vi.fn(() => Promise.resolve()).mockName('loadConfig');
        const {children, mounts} = childrenProbe();
        render(AwaitingRestoreGate, {props: {children, loadConfig, readMode: () => mode.value, readRestoreInterrupted: () => interrupted.value}});
        flushSync();
        return {mode, interrupted, loadConfig, mounts};
    }

    function expectInterruptedOnly(why: string, mounts?: {count: number}): void {
        expect(screen.getByTestId(INTERRUPTED), why).toBeInTheDocument();
        expect(screen.queryByTestId(CHILD), `${why}: the app is not on screen`).toBeNull();
        expect(screen.queryByTestId(PAGE), `${why}: no awaiting-restore page`).toBeNull();
        if (mounts) expect(mounts.count, `${why}: the app was never mounted`).toBe(0);
    }

    describe('injected flag', () => {
        it('shows the interrupted page, and never mounts the app, while the restore is interrupted', () => {
            const {mounts, loadConfig} = mountInterruptedGate('normal', true);

            expectInterruptedOnly('the restore state cannot be read', mounts);
            expect(loadConfig, 'the config is still loaded once on mount').toHaveBeenCalledTimes(1);
        });

        it('prefers the interrupted page over the awaiting page when both hold', () => {
            const {mounts} = mountInterruptedGate('awaiting_restore', true);

            expectInterruptedOnly('interrupted wins over awaiting', mounts);
        });

        it.each([
            ['normal', 'normal', CHILD],
            ['awaiting_restore', 'awaiting_restore', PAGE],
        ])('keeps the H-62 behaviour when not interrupted and the mode is %s', (_case, mode, shown) => {
            mountInterruptedGate(mode, false);

            expect(screen.getByTestId(shown), `mode ${mode}, not interrupted`).toBeInTheDocument();
            expect(screen.queryByTestId(INTERRUPTED), 'no interrupted page').toBeNull();
        });

        it('replaces the app with the interrupted page when the flag turns on, and gives it back when it turns off', async () => {
            const {interrupted} = mountInterruptedGate('normal', false);
            expectChildrenOnly('Barrier: the app runs');
            expect(screen.queryByTestId(INTERRUPTED), 'Barrier: no interrupted page yet').toBeNull();

            interrupted.value = true;
            await tick();
            expectInterruptedOnly('the restore state became unreadable after the app had started');

            interrupted.value = false;
            await tick();
            expectChildrenOnly('the administrator recovered');
            expect(screen.queryByTestId(INTERRUPTED), 'the interrupted page is gone').toBeNull();
        });
    });

    describe('defaults: instanceConfig.config.restore_interrupted', () => {
        it('shows the interrupted page while instanceConfig says restore_interrupted: true, the app once it says false', async () => {
            mocks.config.value = {profile: 'managed', mode: 'normal', restore_interrupted: true};
            const {children, mounts} = childrenProbe();
            render(AwaitingRestoreGate, {props: {children}});
            flushSync();
            expectInterruptedOnly('instanceConfig says restore_interrupted: true', mounts);

            mocks.config.value = {profile: 'managed', mode: 'normal', restore_interrupted: false};
            await tick();
            expectChildrenOnly('instanceConfig says restore_interrupted: false');
        });

        it('prefers the interrupted page over the awaiting page by default too', () => {
            mocks.config.value = {profile: 'managed', mode: 'awaiting_restore', restore_interrupted: true};
            const {children, mounts} = childrenProbe();
            render(AwaitingRestoreGate, {props: {children}});
            flushSync();

            expectInterruptedOnly('both flags from instanceConfig', mounts);
        });

        it.each([
            ['absent (an older server, or the defaults)', undefined],
            ['false', false],
            ['a truthy value that is not true', 'yes'],
        ])('shows the app when restore_interrupted is %s', (_case, value) => {
            mocks.config.value = value === undefined ? {profile: 'managed', mode: 'normal'} : {profile: 'managed', mode: 'normal', restore_interrupted: value};
            const {children} = childrenProbe();
            render(AwaitingRestoreGate, {props: {children}});
            flushSync();

            expectChildrenOnly(`restore_interrupted ${String(value)}`);
            expect(screen.queryByTestId(INTERRUPTED), 'no interrupted page').toBeNull();
        });
    });
});

describe('AwaitingRestoreGate — the reason of an interrupted restore (H5-3)', () => {
    const INTERRUPTED = 'instance-restore-interrupted';
    const DOCS = 'instance-restore-interrupted-docs';
    const RESTORE_STATE_HREF = '/mkdocs/admin/cli_backup/#backup-pending-unreadable';
    const OWNER_HREF = '/mkdocs/admin/hosting_panel_backups/#restore-owner-pending';

    type Reason = 'restore_state' | 'owner_assignment' | null | undefined;

    function docsHref(): string | null {
        return screen.getByTestId(DOCS).getAttribute('href');
    }

    /** Mount the gate with injected mode, interrupted flag and reason, all of which the test flips. */
    function mountReasonGate(initial: {mode?: string; interrupted: boolean; reason: Reason}) {
        const mode = reactiveBox<{value: string | undefined}>({value: initial.mode ?? 'normal'});
        const interrupted = reactiveBox<{value: boolean}>({value: initial.interrupted});
        const reason = reactiveBox<{value: Reason}>({value: initial.reason});
        const {children, mounts} = childrenProbe();
        render(AwaitingRestoreGate, {
            props: {children, loadConfig: vi.fn(() => Promise.resolve()), readMode: () => mode.value, readRestoreInterrupted: () => interrupted.value, readRestoreInterruptedReason: () => reason.value},
        });
        flushSync();
        return {mode, interrupted, reason, mounts};
    }

    describe('injected reason', () => {
        it('passes owner_assignment to the page: the docs link is the owner section of the panel guide', () => {
            const {mounts} = mountReasonGate({interrupted: true, reason: 'owner_assignment'});

            expect(screen.getByTestId(INTERRUPTED), 'the interrupted page').toBeInTheDocument();
            expect(docsHref()).toBe(OWNER_HREF);
            expect(screen.queryByTestId(CHILD), 'the app is not on screen').toBeNull();
            expect(mounts.count, 'the app was never mounted').toBe(0);
        });

        it.each([
            ['restore_state', 'restore_state'],
            ['null', null],
            ['undefined', undefined],
        ] as const)('shows today’s page, with the CLI anchor, for reason %s', (_case, reason) => {
            mountReasonGate({interrupted: true, reason});

            expect(screen.getByTestId(INTERRUPTED)).toBeInTheDocument();
            expect(docsHref()).toBe(RESTORE_STATE_HREF);
        });

        it('follows the reason both ways while the page stays up', async () => {
            const {reason} = mountReasonGate({interrupted: true, reason: 'restore_state'});
            expect(docsHref(), 'Barrier: the restore-state page').toBe(RESTORE_STATE_HREF);

            reason.value = 'owner_assignment';
            await tick();
            expect(docsHref()).toBe(OWNER_HREF);

            reason.value = 'restore_state';
            await tick();
            expect(docsHref()).toBe(RESTORE_STATE_HREF);
        });

        it('keeps the precedence: interrupted wins over awaiting, with either reason', () => {
            const {mounts} = mountReasonGate({mode: 'awaiting_restore', interrupted: true, reason: 'owner_assignment'});

            expect(screen.getByTestId(INTERRUPTED)).toBeInTheDocument();
            expect(docsHref()).toBe(OWNER_HREF);
            expect(screen.queryByTestId(PAGE), 'no awaiting-restore page').toBeNull();
            expect(mounts.count, 'the app was never mounted').toBe(0);
        });

        it.each([
            ['normal', 'normal', CHILD],
            ['awaiting_restore', 'awaiting_restore', PAGE],
        ])('a reason alone, without restore_interrupted, changes nothing: mode %s', (_case, mode, shown) => {
            mountReasonGate({mode, interrupted: false, reason: 'owner_assignment'});

            expect(screen.getByTestId(shown), `mode ${mode}`).toBeInTheDocument();
            expect(screen.queryByTestId(INTERRUPTED), 'no interrupted page').toBeNull();
        });

        it('gives the app back when the flag turns off, whatever the reason', async () => {
            const {interrupted} = mountReasonGate({interrupted: true, reason: 'owner_assignment'});
            expect(docsHref(), 'Barrier: the owner page').toBe(OWNER_HREF);

            interrupted.value = false;
            await tick();

            expectChildrenOnly('the owner exists, the restore is over');
            expect(screen.queryByTestId(INTERRUPTED), 'no interrupted page').toBeNull();
        });
    });

    describe('defaults: instanceConfig.config.restore_interrupted_reason', () => {
        it('reads owner_assignment: the page links the backup and restore guide; flips to restore_state with the config', async () => {
            mocks.config.value = {profile: 'managed', mode: 'normal', restore_interrupted: true, restore_interrupted_reason: 'owner_assignment'};
            const {children, mounts} = childrenProbe();
            render(AwaitingRestoreGate, {props: {children}});
            flushSync();
            expect(screen.getByTestId(INTERRUPTED), 'the interrupted page').toBeInTheDocument();
            expect(docsHref()).toBe(OWNER_HREF);
            expect(mounts.count, 'the app was never mounted').toBe(0);

            mocks.config.value = {profile: 'managed', mode: 'normal', restore_interrupted: true, restore_interrupted_reason: 'restore_state'};
            await tick();
            expect(docsHref()).toBe(RESTORE_STATE_HREF);
        });

        it.each([
            ['restore_state', 'restore_state'],
            ['null', null],
            ['absent (an older server)', undefined],
        ])('shows today’s page when the reason is %s', (_case, value) => {
            mocks.config.value = value === undefined ? {profile: 'managed', mode: 'normal', restore_interrupted: true} : {profile: 'managed', mode: 'normal', restore_interrupted: true, restore_interrupted_reason: value};
            const {children} = childrenProbe();
            render(AwaitingRestoreGate, {props: {children}});
            flushSync();

            expect(screen.getByTestId(INTERRUPTED)).toBeInTheDocument();
            expect(docsHref()).toBe(RESTORE_STATE_HREF);
        });

        it('a reason alone, with restore_interrupted false, shows the app', () => {
            mocks.config.value = {profile: 'managed', mode: 'normal', restore_interrupted: false, restore_interrupted_reason: 'owner_assignment'};
            const {children} = childrenProbe();
            render(AwaitingRestoreGate, {props: {children}});
            flushSync();

            expectChildrenOnly('restore_interrupted false');
            expect(screen.queryByTestId(INTERRUPTED), 'no interrupted page').toBeNull();
        });
    });
});
