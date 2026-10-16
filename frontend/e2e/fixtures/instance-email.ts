/**
 * The email part of this instance as one page sees it (workstream E, lot E4b): `GET /api/v1/system/instance` answered
 * with the real response and `email` replaced by `{available, links}`, so that a spec can offer or withhold what needs
 * an email with a link — «send by email» in the share dialogs, «forgot password» by email — without an SMTP server on
 * the lane, which has none (`LIBREFOLIO_SMTP_HOST` unset) and must keep none.
 *
 * Modelled on `serveRegistrationMode` (`instance-config.ts`, workstream A): the real response with one field changed,
 * never a hand-built body, and that body checked against the generated schema before it is served. The check matters
 * twice here: the client validates the answer with Zod, and a refused body leaves the page on its defaults — which carry
 * no email part, and read exactly like `links: false`. A broken stub would pass for the hidden case; `problems` says why
 * instead, and a test asserts it empty.
 *
 * `page.route()` binds the browser context that installs it (devWiki, problems/playwright-route-stub-is-per-context):
 * nothing outside this page sees the stub, nothing is written, and any method but `GET` falls through.
 */
import type {APIResponse} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {INSTANCE_CONFIG_PATH} from './instance-config';
import type {Page} from './playwright';

/** What `GET /system/instance` says of email: whether it can go out, and whether it can carry a link. */
export type InstanceEmail = {available: boolean; links: boolean};

export type InstanceEmailStub = {
    /** Reads that reached the stub: the page asked. */
    readonly requested: number;
    /** Reads the stub has finished with, answered or not: compare `problems`. */
    readonly answered: number;
    /** The `email` each answer carried, in order. */
    readonly served: readonly InstanceEmail[];
    /** Why a read was not answered as asked: a broken precondition, reported by name. */
    readonly problems: readonly string[];
    /** Remove the route. Call it in `finally`. */
    dispose(): Promise<void>;
};

const isInstanceConfig = (url: URL): boolean => url.pathname === INSTANCE_CONFIG_PATH;

/** The real answer's headers, without those describing its body as it travelled (see `instance-config.ts`). */
function servableHeaders(response: APIResponse): Record<string, string> {
    const headers = {...response.headers()};
    delete headers['content-encoding'];
    delete headers['content-length'];
    return headers;
}

/**
 * Answer this page's `GET /api/v1/system/instance` — that path only — with the real response and `email` set to `email`.
 * Install it before the page loads: the app reads the configuration once per page load (`instanceConfig.svelte.ts`).
 */
export async function serveInstanceEmail(page: Page, email: InstanceEmail): Promise<InstanceEmailStub> {
    let requested = 0;
    let answered = 0;
    const served: InstanceEmail[] = [];
    const problems: string[] = [];

    const handler: Parameters<Page['route']>[1] = async (route, request) => {
        if (request.method() !== 'GET') {
            await route.fallback();
            return;
        }
        requested += 1;
        try {
            const response = await route.fetch();
            if (!response.ok()) {
                problems.push(`the real GET ${INSTANCE_CONFIG_PATH} answered ${response.status()}`);
                await route.fulfill({status: response.status(), headers: servableHeaders(response), body: await response.body()});
                return;
            }
            const body = {...((await response.json()) as Record<string, unknown>), email: {...email}};
            const checked = schemas.InstanceConfigResponse.safeParse(body);
            if (!checked.success) problems.push(`the answer with email ${JSON.stringify(email)} fails the generated schema: ${checked.error.message}`);
            await route.fulfill({status: response.status(), headers: servableHeaders(response), json: body});
            served.push({...email});
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
