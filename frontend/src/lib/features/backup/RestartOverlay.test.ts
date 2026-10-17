// @vitest-environment jsdom
/**
 * RestartOverlay — the full-page overlay while the server restarts to apply a restore (component test, Vitest + jsdom;
 * workstream B, lot B5b). Written red first against `b5b-contract.md` §0.2, §0.3, §0.5, §0.6 and §3: the component does
 * not exist yet.
 *
 * The contract under test:
 *   - the root `restart-overlay` publishes `data-outcome` (`waiting`, `restored`, `rolled_back`, `still_pending`) and
 *     `data-slow` (`true` once the server has been gone for a minute, `false` before);
 *   - a success shows no message (§0.2): `restored` keeps the spinner of `waiting` and reads exactly as it does, asks
 *     none of the removed keys (`restart.restored*`, `restart.signIn`, `last.committed`), and offers nothing — the
 *     controller leaves for the sign-in page by itself;
 *   - a failure shows on the same screen (§0.3): `rolled_back` publishes `data-reason` and tells the reason — the overlay
 *     reads differently for each one —, `still_pending` publishes `data-waiting` and tells it with
 *     `backup.restore.waiting.<waiting>` (§0.5, `instance_blocked` included); both offer `restart-back`, which calls
 *     `onBack()` once;
 *   - `restart-sign-in` exists for no outcome (§0.6).
 *
 * Props, the choice of this file where §3 names none: `outcome`, `slow`, `status` (the controller's `outcomeStatus`,
 * which carries the reason or the waiting) and `onBack`. A controlled overlay: it reads what it is given and calls back.
 *
 * The seams. `$lib/i18n` renders every key as itself (with its values, when it has any) and records every key it is
 * asked, so a case proves which keys were asked and never reads a sentence. `$lib/api` throws on any request: the
 * overlay sends nothing.
 *
 * The component is loaded through `import.meta.glob` in a hook: while it does not exist, every case fails on its own and
 * names it.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import type {Component} from 'svelte';
import type {z} from 'zod';
import type {schemas} from '$lib/api';
import {cleanup, fireEvent, render, screen} from '$test/component';

const i18n = vi.hoisted(() => ({asked: [] as string[]}));

vi.mock('$lib/i18n', () => {
    const translate = (key: string, options?: {values?: Record<string, unknown>}) => {
        i18n.asked.push(key);
        return options?.values ? `${key} ${JSON.stringify(options.values)}` : key;
    };
    const translator = readable(translate);
    return {
        _: translator,
        t: translator,
        locale: writable('en'),
        date: readable((value: unknown) => String(value)),
        time: readable((value: unknown) => String(value)),
        number: readable((value: unknown) => String(value)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it', 'fr', 'es'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT', fr: 'FR', es: 'ES'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get: (_target, alias) =>
                typeof alias !== 'string' || alias === 'then'
                    ? undefined
                    : () => {
                          throw new Error(`RestartOverlay.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

type RestoreStatus = z.infer<typeof schemas.RestoreStatus>;
type RollbackReason = NonNullable<RestoreStatus['reason']>;
/** The waiting reasons of §0.5: the generated client does not know `instance_blocked` yet (P7). */
type WaitingReason = NonNullable<RestoreStatus['waiting']> | 'instance_blocked';
type RestartOutcome = 'waiting' | 'restored' | 'rolled_back' | 'still_pending';

const OVERLAY_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./RestartOverlay.svelte');

let loaded: Component<Record<string, unknown>> | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = OVERLAY_MODULES['./RestartOverlay.svelte'];
        if (!load) throw new Error('src/lib/features/backup/RestartOverlay.svelte does not exist yet: nothing covers the page while the server restarts (B5b contract §3)');
        loaded = (await load()).default;
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

function overlayComponent(): Component<Record<string, unknown>> {
    if (loaded === undefined) throw new Error('RestartOverlay was never loaded: its beforeAll did not run');
    if (typeof loaded === 'object' && 'error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded;
}

// --- Fixtures ---------------------------------------------------------------------------------------------------------

const REASONS: RollbackReason[] = ['first_start_failed', 'swap_interrupted', 'swap_failed', 'stage_missing'];
const WAITINGS: WaitingReason[] = ['backup_running', 'other_data_directory', 'server_running', 'instance_blocked'];

type StatusFields = Omit<Partial<RestoreStatus>, 'waiting'> & {waiting?: WaitingReason | null};

function restoreStatus(overrides: StatusFields): RestoreStatus {
    return {
        state: 'pending',
        stage_id: 'fedcba9876543210fedcba9876543210',
        confirmed_at: '2026-10-16T11:20:00Z',
        confirmed_by: 'admin',
        backup_created_at: '2026-10-15T12:00:00Z',
        backup_app_version: '0.9.0',
        action: 'same',
        finished_at: null,
        reason: null,
        waiting: null,
        upload_limit_mb: 500,
        ...overrides,
    } as RestoreStatus;
}

const rolledBack = (reason: RollbackReason) => restoreStatus({state: 'rolled_back', finished_at: '2026-10-16T11:21:00Z', reason});
const stillPending = (waiting: WaitingReason) => restoreStatus({state: 'pending', waiting});

/** The overlay with these props; `onBack` is a spy. */
function mount(outcome: RestartOutcome, status: RestoreStatus | null = null, slow = false) {
    const onBack = vi.fn();
    const view = render(overlayComponent(), {props: {outcome, slow, status, onBack}});
    return {...view, onBack};
}

const overlay = () => screen.getByTestId('restart-overlay');

/** The keys §0.6 removed with the success texts. */
const REMOVED_KEYS = /^backup\.restore\.(restart\.restored|restart\.signIn|last\.committed)/;

beforeEach(() => {
    i18n.asked.length = 0;
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('RestartOverlay — waiting for the server', () => {
    it('waiting: data-outcome waiting, data-slow false, nothing offered', () => {
        mount('waiting');

        expect(overlay()).toHaveAttribute('data-outcome', 'waiting');
        expect(overlay()).toHaveAttribute('data-slow', 'false');
        expect(screen.queryByTestId('restart-back'), 'nothing to go back to while the server restarts').toBeNull();
        expect(screen.queryByTestId('restart-sign-in')).toBeNull();
    });

    it('waiting for more than a minute: data-slow true, still nothing offered', () => {
        mount('waiting', null, true);

        expect(overlay()).toHaveAttribute('data-outcome', 'waiting');
        expect(overlay()).toHaveAttribute('data-slow', 'true');
        expect(screen.queryByTestId('restart-back')).toBeNull();
        expect(screen.queryByTestId('restart-sign-in')).toBeNull();
    });
});

describe('RestartOverlay — a success shows no message (§0.2)', () => {
    it('restored: data-outcome restored, read exactly as waiting, none of the removed keys asked, nothing offered', () => {
        const waiting = mount('waiting');
        const waitingText = overlay().textContent;
        waiting.unmount();
        i18n.asked.length = 0;

        mount('restored');

        expect(overlay()).toHaveAttribute('data-outcome', 'restored');
        expect(overlay().textContent, 'a success added a message: the overlay keeps the spinner of waiting').toBe(waitingText);
        expect(i18n.asked.filter((key) => REMOVED_KEYS.test(key))).toEqual([]);
        expect(screen.queryByTestId('restart-back')).toBeNull();
        expect(screen.queryByTestId('restart-sign-in'), 'restart-sign-in no longer exists (§0.6)').toBeNull();
    });
});

describe('RestartOverlay — a failure shows on the same screen, with the reason (§0.3)', () => {
    it.each(REASONS)('rolled back (%s): data-reason, restart-back, no sign-in', (reason) => {
        mount('rolled_back', rolledBack(reason));

        expect(overlay()).toHaveAttribute('data-outcome', 'rolled_back');
        expect(overlay()).toHaveAttribute('data-reason', reason);
        expect(screen.getByTestId('restart-back')).toBeInTheDocument();
        expect(screen.queryByTestId('restart-sign-in')).toBeNull();
    });

    it('rolled back: the overlay tells each reason its own way', () => {
        const texts = REASONS.map((reason) => {
            const view = mount('rolled_back', rolledBack(reason));
            const text = overlay().textContent;
            view.unmount();
            return text;
        });

        expect(new Set(texts).size, 'two reasons read the same: the reason is not told').toBe(REASONS.length);
    });

    it.each(WAITINGS)('still pending (%s): data-waiting, its reason told with backup.restore.waiting.<waiting>, restart-back, no sign-in', (waiting) => {
        mount('still_pending', stillPending(waiting));

        expect(overlay()).toHaveAttribute('data-outcome', 'still_pending');
        expect(overlay()).toHaveAttribute('data-waiting', waiting);
        expect(i18n.asked).toContain(`backup.restore.waiting.${waiting}`);
        expect(screen.getByTestId('restart-back')).toBeInTheDocument();
        expect(screen.queryByTestId('restart-sign-in')).toBeNull();
    });

    it.each<[string, RestartOutcome, RestoreStatus]>([
        ['rolled back', 'rolled_back', rolledBack('swap_failed')],
        ['still pending', 'still_pending', stillPending('instance_blocked')],
    ])('%s: restart-back calls onBack() once', async (_case, outcome, status) => {
        const {onBack} = mount(outcome, status);

        await fireEvent.click(screen.getByTestId('restart-back'));

        expect(onBack).toHaveBeenCalledTimes(1);
    });
});

// =====================================================================================================================
// B-16 — a server that never stops: the overlay says so, and offers the way back (written red first)
// =====================================================================================================================

/*
 * The contract (B-16 brief §2): a prop `notStopping` (default false), published on the root as `data-not-stopping`
 * (`true`/`false`). In the waiting branch, with it: `restart-not-stopped`, built exactly like `restart-slow` — the same
 * warning roles, the same icon —, worded by `backup.restore.restart.notStopped`; and `restart-back`, as in the failed
 * branch, calling `onBack()`. Nothing else changes: without it neither element, and `slow` alone as before.
 *
 * The roles are read the one way a jsdom test can: as the three role tokens the brief names, and as the same class list
 * and the same lucide glyph as `restart-slow`'s — never to find an element.
 *
 * Red today: the overlay takes no such prop: no `data-not-stopping`, no hint, no way back while waiting.
 */

/** The overlay with these props; `onBack` is a spy. */
function mountWith(props: {outcome: RestartOutcome; slow?: boolean; notStopping?: boolean; status?: RestoreStatus | null}) {
    const onBack = vi.fn();
    const view = render(overlayComponent(), {props: {slow: false, status: null, onBack, ...props}});
    return {...view, onBack};
}

/** The lucide glyph a hint draws, by lucide's name for it: `triangle-alert` for the svg's `lucide-triangle-alert`. */
function glyphOf(element: HTMLElement): string {
    const token = Array.from(element.querySelector('svg')?.classList ?? []).find((name) => name.startsWith('lucide-') && name !== 'lucide-icon');
    return token ? token.slice('lucide-'.length) : '(no lucide glyph)';
}

/** The warning roles of the hints (the brief's three). */
const WARNING_ROLES = ['border-lf-warning-line', 'bg-lf-warning-soft', 'text-lf-warning-on-soft'];

describe('B-16 — RestartOverlay: a server that never stops', () => {
    it('notStopping: data-not-stopping true, still waiting; restart-not-stopped worded by backup.restore.restart.notStopped, built like restart-slow (the warning roles, the same glyph)', () => {
        const slow = mountWith({outcome: 'waiting', slow: true});
        const slowHint = screen.getByTestId('restart-slow');
        const slowLook = {className: slowHint.className, glyph: glyphOf(slowHint)};
        slow.unmount();
        i18n.asked.length = 0;

        mountWith({outcome: 'waiting', notStopping: true});

        expect(overlay()).toHaveAttribute('data-not-stopping', 'true');
        expect(overlay(), 'still waiting for the server').toHaveAttribute('data-outcome', 'waiting');
        expect(i18n.asked, 'the title and the waiting text stay').toEqual(expect.arrayContaining(['backup.restore.restart.waitingTitle', 'backup.restore.restart.waiting']));
        const hint = screen.getByTestId('restart-not-stopped');
        expect(hint).toHaveTextContent(/^\s*backup\.restore\.restart\.notStopped\s*$/);
        expect(hint).toHaveClass(...WARNING_ROLES);
        expect({className: hint.className, glyph: glyphOf(hint)}, 'built exactly like restart-slow').toEqual(slowLook);
        expect(screen.queryByTestId('restart-slow'), 'not slow: the server was never seen down').toBeNull();
    });

    it('notStopping: restart-back, as in the failed branch, worded by backup.restore.restart.back, calls onBack() once', async () => {
        const {onBack} = mountWith({outcome: 'waiting', notStopping: true});

        const back = screen.getByTestId('restart-back');
        expect(back).toHaveTextContent(/^\s*backup\.restore\.restart\.back\s*$/);
        await fireEvent.click(back);

        expect(onBack).toHaveBeenCalledTimes(1);
    });

    it('without notStopping: data-not-stopping false, and neither restart-not-stopped nor restart-back while waiting', () => {
        mountWith({outcome: 'waiting'});

        expect(overlay(), 'precondition: waiting').toHaveAttribute('data-outcome', 'waiting');
        expect(overlay()).toHaveAttribute('data-not-stopping', 'false');
        expect(screen.queryByTestId('restart-not-stopped')).toBeNull();
        expect(screen.queryByTestId('restart-back')).toBeNull();
    });

    it('slow alone, as before: restart-slow, data-not-stopping false, neither restart-not-stopped nor restart-back', () => {
        mountWith({outcome: 'waiting', slow: true});

        expect(screen.getByTestId('restart-slow')).toBeInTheDocument();
        expect(overlay()).toHaveAttribute('data-slow', 'true');
        expect(overlay()).toHaveAttribute('data-not-stopping', 'false');
        expect(screen.queryByTestId('restart-not-stopped')).toBeNull();
        expect(screen.queryByTestId('restart-back')).toBeNull();
    });

    it('a failure with notStopping: the root says it, the failed branch stays as before — one restart-back, no restart-not-stopped', () => {
        mountWith({outcome: 'rolled_back', status: rolledBack('swap_failed'), notStopping: true});

        expect(overlay()).toHaveAttribute('data-not-stopping', 'true');
        expect(screen.getByTestId('restart-detail')).toBeInTheDocument();
        expect(screen.getAllByTestId('restart-back'), 'one way back').toHaveLength(1);
        expect(screen.queryByTestId('restart-not-stopped'), 'the hint belongs to the waiting branch').toBeNull();
    });
});
