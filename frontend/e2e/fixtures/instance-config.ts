/**
 * The registration mode of this instance as one page sees it: `GET /api/v1/system/instance` answered with the real
 * response and `accounts.registration_mode` replaced, or observed untouched.
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
 * Users: auth.spec.ts («Register link and the registration setting») and auth-links.spec.ts (valid invitations on an
 * instance by invitation only, and on one whose registration is disabled); `plainInstanceConfig()`:
 * files-uploader.spec.ts and layout/header-scroll.spec.ts.
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
    /** Why a read was not answered with the mode asked for: a broken precondition, reported by name. */
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
 * mode it carried. With `hold`, every answer waits for `release()`: the page meanwhile runs on its defaults, which a
 * test can observe before the answer changes them. The real request leaves at once; only its answer is held.
 *
 * Any other method falls through: nothing here writes. A real response without `accounts.registration_mode` is a broken
 * precondition — the backend of lot A5a is missing — and is passed through as it is, with the reason in `problems`.
 */
export async function serveRegistrationMode(page: Page, mode: RegistrationMode | null, options: {hold?: boolean} = {}): Promise<RegistrationModeStub> {
    let requested = 0;
    let answered = 0;
    const served: string[] = [];
    const problems: string[] = [];
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
            if (mode === null) {
                await asItCame();
                served.push(real);
            } else {
                await route.fulfill({status: response.status(), headers: servableHeaders(response), json: {...body, accounts: {...body.accounts, registration_mode: mode}}});
                served.push(mode);
            }
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
