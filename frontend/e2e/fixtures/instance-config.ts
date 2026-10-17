/**
 * The registration mode of this instance as one page sees it: `GET /api/v1/system/instance` answered with the real
 * response and `accounts.registration_mode` replaced (and, on request, `accounts.first_account_open`: lot A6d), or
 * observed untouched.
 *
 * The lane runs `registration_mode` = 'open', a global setting shared by every user and every worker, and no E2E spec
 * changes it. A spec that needs another mode stubs the read its own page makes instead: `page.route()` binds the browser
 * context that installs it (devWiki, problems/playwright-route-stub-is-per-context), so nothing outside this page sees
 * the stub, and nothing is written. The answer is the real response with one field changed, never a hand-built body:
 * the client validates it against the generated schema (Zodios), and a body that drifted from the backend would be
 * refused — the page would keep its defaults, and the test would read them as the mode it asked for.
 *
 * The one hand-built body, `plainInstanceConfig()`, is for specs whose data is entirely synthetic: they let no request
 * reach the shared backend, so there is no real response to change, and nothing they assert depends on this read.
 *
 * `serveInstanceConfig()` (lot A9) is the same stub for the profile (F05) and the legal links (F09): the real response
 * with `profile` replaced and `legal` merged link by link, or observed untouched.
 *
 * Users: auth.spec.ts («Register link and the registration setting», whose A6d case also sets
 * `accounts.first_account_open` with `firstAccountOpen`) and auth-links.spec.ts (valid invitations on an instance by
 * invitation only, and on one whose registration is disabled); `plainInstanceConfig()`: files-uploader.spec.ts and
 * layout/header-scroll.spec.ts; `serveInstanceConfig()`: layout/legal-and-managed.spec.ts.
 */
import type {APIResponse} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import type {Page} from './playwright';

export type RegistrationMode = 'open' | 'invite' | 'disabled';

/** The path the instance configuration is read from (`instanceConfig.svelte.ts`). */
export const INSTANCE_CONFIG_PATH = '/api/v1/system/instance';

/**
 * What the stub saw. Every counter is written by the route handler itself, so a poll on it reads what the handler has
 * done, never a request event that fired before the handler ran (devWiki, problems/request-counter-read-before-the-
 * handler-counted).
 */
export type RegistrationModeStub = {
    /** Reads that reached the stub: the page asked. */
    readonly requested: number;
    /** Reads the stub has finished with, answered or not: compare `problems`. */
    readonly answered: number;
    /** The registration mode each answer carried, in order. */
    readonly served: readonly string[];
    /**
     * The `accounts.first_account_open` each answer carried, in order, beside `served`: the value asked for with
     * `firstAccountOpen`, else the real one passed through — `undefined` where the real answer has none (a backend from
     * before lot A6d).
     */
    readonly servedFirstAccountOpen: readonly (boolean | undefined)[];
    /** Why a read was not answered with the mode — or the flag — asked for: a broken precondition, reported by name. */
    readonly problems: readonly string[];
    /** Deliver the held answers; without `hold` there is nothing to deliver. */
    release(): void;
    /** Release, then remove the route. Call it in `finally`: a held handler must not outlive its test. */
    dispose(): Promise<void>;
};

const isInstanceConfig = (url: URL): boolean => url.pathname === INSTANCE_CONFIG_PATH;

/**
 * The real answer's headers, without the two that describe its body as it travelled. `route.fetch()` hands the body over
 * decoded, and a fulfilled body is served exactly as given: a `content-encoding: gzip` kept from the original would make
 * the browser decode plain JSON (the backend compresses from 1 KB up: auth.spec.ts met it on a catalogue chunk), and its
 * `content-length` would describe a body this stub may have changed. Playwright recomputes the length from the body.
 */
function servableHeaders(response: APIResponse): Record<string, string> {
    const headers = {...response.headers()};
    delete headers['content-encoding'];
    delete headers['content-length'];
    return headers;
}

/**
 * Answer this page's `GET /api/v1/system/instance` — that path only — with the real response and
 * `accounts.registration_mode` set to `mode`; with `mode` null, pass the real answer through untouched and record the
 * mode it carried. With `firstAccountOpen` (accounts lot A6d), `accounts.first_account_open` is set to it too, in the
 * same real response — with `mode` null it is then the one field changed; without it the real flag passes through as
 * it came, so a caller that does not ask for it sees the stub exactly as before. With `hold`, every answer waits for
 * `release()`: the page meanwhile runs on its defaults, which a test can observe before the answer changes them. The
 * real request leaves at once; only its answer is held.
 *
 * Any other method falls through: nothing here writes. A real response without `accounts.registration_mode` is a broken
 * precondition — the backend of lot A5a is missing — and is passed through as it is, with the reason in `problems`. So
 * is one without a boolean `accounts.first_account_open` when `firstAccountOpen` is asked for — the backend of lot A6d
 * is missing: the flag is changed in the real answer, never added to one that lacks it.
 */
export async function serveRegistrationMode(page: Page, mode: RegistrationMode | null, options: {hold?: boolean; firstAccountOpen?: boolean} = {}): Promise<RegistrationModeStub> {
    let requested = 0;
    let answered = 0;
    const served: string[] = [];
    const servedFirstAccountOpen: (boolean | undefined)[] = [];
    const problems: string[] = [];
    const flag = options.firstAccountOpen;
    let deliver = () => {};
    const delivered = options.hold
        ? new Promise<void>((resolve) => {
              deliver = resolve;
          })
        : Promise.resolve();

    const handler: Parameters<Page['route']>[1] = async (route, request) => {
        if (request.method() !== 'GET') {
            await route.fallback();
            return;
        }
        requested += 1;
        try {
            const response = await route.fetch();
            await delivered;
            const asItCame = async () => route.fulfill({status: response.status(), headers: servableHeaders(response), body: await response.body()});
            if (!response.ok()) {
                problems.push(`the real GET ${INSTANCE_CONFIG_PATH} answered ${response.status()}`);
                await asItCame();
                return;
            }
            const body = (await response.json()) as {accounts?: Record<string, unknown>} & Record<string, unknown>;
            const real = body.accounts?.registration_mode;
            if (typeof real !== 'string') {
                problems.push(`the real GET ${INSTANCE_CONFIG_PATH} has no accounts.registration_mode (keys: ${Object.keys(body).join(', ') || 'none'})`);
                await asItCame();
                return;
            }
            const carried = body.accounts?.first_account_open;
            const realFlag = typeof carried === 'boolean' ? carried : undefined;
            if (flag !== undefined && realFlag === undefined) {
                problems.push(`the real GET ${INSTANCE_CONFIG_PATH} has no boolean accounts.first_account_open (accounts keys: ${Object.keys(body.accounts ?? {}).join(', ') || 'none'}): the backend of lot A6d is missing`);
                await asItCame();
                return;
            }
            if (mode === null && flag === undefined) {
                await asItCame();
                served.push(real);
            } else {
                const accounts = {...body.accounts, registration_mode: mode ?? real, ...(flag === undefined ? {} : {first_account_open: flag})};
                await route.fulfill({status: response.status(), headers: servableHeaders(response), json: {...body, accounts}});
                served.push(mode ?? real);
            }
            servedFirstAccountOpen.push(flag ?? realFlag);
        } catch (error) {
            // Nobody awaits a route callback: what it throws would surface as an unhandled rejection on whatever the
            // worker runs next. Recorded instead, and asserted by the test that needed the read.
            problems.push(`the stub failed: ${String(error)}`);
        } finally {
            answered += 1;
        }
    };
    await page.route(isInstanceConfig, handler);

    return {
        get requested() {
            return requested;
        },
        get answered() {
            return answered;
        },
        get served() {
            return served;
        },
        get servedFirstAccountOpen() {
            return servedFirstAccountOpen;
        },
        get problems() {
            return problems;
        },
        release: () => deliver(),
        dispose: async () => {
            deliver();
            await page.unroute(isInstanceConfig, handler);
        },
    };
}

/**
 * The body of `GET /api/v1/system/instance` for a plain instance, as the backend answers it today: self-hosted,
 * anyone may register, the mode not pinned by the environment. For a spec whose data is entirely synthetic and which
 * must still declare this read: the app makes it on every page load (instanceConfig.svelte.ts), and such a spec
 * refuses any request it did not declare.
 *
 * The client validates the answer with Zod (the generated schema, through Zodios): a body that drifted from the backend
 * would be refused, and the page would keep its defaults — the same plain instance, so the drift would go unseen. Hence
 * the check against that schema here: a contract that moves fails by name, in the spec that asked for the body.
 *
 * It answers the read; it cannot test what the configuration changes. A spec that needs real behaviour (the
 * registration mode) uses `serveRegistrationMode()` above: the real response, with one field changed.
 */
export function plainInstanceConfig() {
    const body = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as const;
    schemas.InstanceConfigResponse.parse(body);
    return body;
}

/** What `serveInstanceConfig()` may change in the real answer (lot A9 of workstream A): the profile (F05), the legal links (F09). */
export type InstanceConfigPatch = {
    /** Replaces `profile`. */
    profile?: 'selfhosted' | 'managed';
    /** Merged into the real `legal`, link by link: a link given replaces the real one, a link left out keeps it. */
    legal?: {terms_url?: string | null; privacy_url?: string | null};
};

/** Of one answer `serveInstanceConfig()` served, the parts a patch may change: `profile` and `legal`, as served. */
export type ServedInstanceConfig = {profile: unknown; legal: unknown};

/** What `serveInstanceConfig()` saw. Every counter is written by the route handler itself, as in `RegistrationModeStub`. */
export type InstanceConfigStub = {
    /** Reads that reached the stub: the page asked. */
    readonly requested: number;
    /** Reads the stub has finished with, answered or not: compare `problems`. */
    readonly answered: number;
    /** The `profile` and `legal` each answer carried, in order. */
    readonly served: readonly ServedInstanceConfig[];
    /** Why a read was not answered as asked: a broken precondition, reported by name. */
    readonly problems: readonly string[];
    /** Remove the route. Call it in `finally`. */
    dispose(): Promise<void>;
};

const isPlainObject = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);

/** The entries of `record` whose value is not `undefined`: a key left undefined in a patch changes nothing. */
const definedEntries = (record: Record<string, unknown>): Record<string, unknown> => Object.fromEntries(Object.entries(record).filter(([, value]) => value !== undefined));

/**
 * Answer this page's `GET /api/v1/system/instance` — that path only — with the real response and `patch` applied (lot A9
 * of workstream A): `profile` replaced, `legal` merged link by link. An empty patch passes the real answer through as it
 * came and records what it carried: the lane's own answer, observed. Install it before the page loads: the app reads the
 * configuration once per page load (`instanceConfig.svelte.ts`), and a client-side navigation reads it no more.
 *
 * A field is changed in the real answer, never added to one that lacks it: a real answer without a string `profile` when
 * `profile` is patched, or without a `legal` object when `legal` is (the backend of lot A9 missing), is passed through as
 * it came, with the reason in `problems`. The patched answer is checked against the generated schema before it is
 * served, as the client checks it on arrival: a body its Zod refuses leaves the page on its defaults — self-hosted, no
 * legal link —, which read exactly like some of what a test asks for. The check failing is recorded in `problems` too, so
 * a test asserts `problems` empty. Any other method falls through: nothing here writes.
 */
export async function serveInstanceConfig(page: Page, patch: InstanceConfigPatch): Promise<InstanceConfigStub> {
    let requested = 0;
    let answered = 0;
    const served: ServedInstanceConfig[] = [];
    const problems: string[] = [];
    const asked = JSON.stringify(patch);
    const patchesProfile = patch.profile !== undefined;
    const patchesLegal = patch.legal !== undefined;

    const handler: Parameters<Page['route']>[1] = async (route, request) => {
        if (request.method() !== 'GET') {
            await route.fallback();
            return;
        }
        requested += 1;
        try {
            const response = await route.fetch();
            const asItCame = async () => route.fulfill({status: response.status(), headers: servableHeaders(response), body: await response.body()});
            if (!response.ok()) {
                problems.push(`the real GET ${INSTANCE_CONFIG_PATH} answered ${response.status()}`);
                await asItCame();
                return;
            }
            const real = (await response.json()) as Record<string, unknown>;
            const lacking: string[] = [];
            if (patchesProfile && typeof real.profile !== 'string') lacking.push('string profile');
            if (patchesLegal && !isPlainObject(real.legal)) lacking.push('legal object (the backend of lot A9 is missing)');
            if (lacking.length > 0) {
                problems.push(`the real GET ${INSTANCE_CONFIG_PATH} has no ${lacking.join(' and no ')} to patch with ${asked} (keys: ${Object.keys(real).join(', ') || 'none'})`);
                await asItCame();
                return;
            }
            const body: Record<string, unknown> = {...real};
            if (patch.profile !== undefined) body.profile = patch.profile;
            if (patch.legal !== undefined && isPlainObject(real.legal)) body.legal = {...real.legal, ...definedEntries(patch.legal)};
            const checked = schemas.InstanceConfigResponse.safeParse(body);
            if (!checked.success) problems.push(`the answer ${patchesProfile || patchesLegal ? `patched with ${asked}` : 'as it came'} fails the generated schema: ${checked.error.message}`);
            if (patchesProfile || patchesLegal) await route.fulfill({status: response.status(), headers: servableHeaders(response), json: body});
            else await asItCame();
            served.push({profile: body.profile, legal: body.legal});
        } catch (error) {
            // Nobody awaits a route callback: recorded instead, and asserted by the test that needed the read.
            problems.push(`the stub failed: ${String(error)}`);
        } finally {
            answered += 1;
        }
    };
    await page.route(isInstanceConfig, handler);

    return {
        get requested() {
            return requested;
        },
        get answered() {
            return answered;
        },
        get served() {
            return served;
        },
        get problems() {
            return problems;
        },
        dispose: async () => {
            await page.unroute(isInstanceConfig, handler);
        },
    };
}
