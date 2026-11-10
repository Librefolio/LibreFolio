/**
 * securityChecksApi — the seam of Settings › Security with `GET /api/v1/security/checks` (accounts lot A8b).
 *
 * The contract under test (approved for A8b):
 *   - `fetchSecurityChecks()` asks the generated client's `list_security_checks_api_v1_security_checks_get` — the
 *     administrators' `GET /api/v1/security/checks` — and resolves to the `items` of its answer as they came: the
 *     platform's order, every field, the numbers of `detail` still numbers;
 *   - an answer without a check is an empty list;
 *   - a failure propagates: it rejects with the very error the client raised, so the store decides what it means.
 *
 * `$lib/api` is a mock owned here: its `zodiosApi` answers the one operation this module may call, and any other
 * operation rejects, loudly. That the mocked name is the generated client's own — the same alias, on `GET
 * /api/v1/security/checks` — is read from `generated.ts`'s endpoint list (`api.api`), so a misspelt operation fails
 * here instead of in the browser.
 *
 * Not pinned: what becomes of a check the server sends without `detail` — the generated schema allows it, the backend
 * never does it (`Field(default_factory=dict)`), and the contract's `SecurityCheck` declares `detail` required.
 *
 * Red until A8b: `securityChecksApi.ts` does not exist yet. It is loaded by a computed specifier, so each case fails on
 * its own with the contract in its message rather than the whole file at import, and the type check does not depend
 * on the module landing first. Pure: the node environment.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {api as generatedClient} from '$lib/api/generated';

const mocks = vi.hoisted(() => ({
    operation: 'list_security_checks_api_v1_security_checks_get',
    listSecurityChecks: vi.fn().mockName('zodiosApi.list_security_checks_api_v1_security_checks_get'),
}));

vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (operation === mocks.operation) return mocks.listSecurityChecks;
                return vi.fn(async () => {
                    throw new Error(`fetchSecurityChecks() reached zodiosApi.${operation}: it may only ask ${mocks.operation}`);
                });
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

// --- The module under test, by a computed specifier: Vite does not resolve it when it transforms this file ----------

const API_MODULE = './securityChecksApi';

type Severity = 'ok' | 'info' | 'warning' | 'error';

/** One check as the contract hands it over. */
interface SecurityCheck {
    check_id: string;
    severity: Severity;
    i18n_key: string;
    detail: Record<string, string | number>;
}

interface SecurityChecksApi {
    fetchSecurityChecks(): Promise<SecurityCheck[]>;
}

async function loadApi(): Promise<SecurityChecksApi> {
    let module: Record<string, unknown>;
    try {
        module = (await import(/* @vite-ignore */ API_MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/features/settings/security/securityChecksApi.ts cannot be loaded (red until A8b: it does not exist yet): nothing asks GET /api/v1/security/checks for the Security tab — ${String(error)}`);
    }
    expect(typeof module.fetchSecurityChecks, 'securityChecksApi.ts exports no fetchSecurityChecks()').toBe('function');
    return module as unknown as SecurityChecksApi;
}

// --- Fixtures: the answer of GET /security/checks, in the platform's order ---------------------------------------------

function check(check_id: string, severity: Severity, i18n_key: string, detail: Record<string, string | number> = {}): SecurityCheck {
    return {check_id, severity, i18n_key, detail};
}

/** The ten checks of today, each in a state it can really be in, with numbers and strings in `detail`. */
const ANSWERED: SecurityCheck[] = [
    check('platform.jwt_secret', 'warning', 'instance.checks.jwtSecret.short', {source: 'JWT_SECRET', length: 12, minimum: 32}),
    check('platform.secrets_set_twice', 'ok', 'instance.checks.secretsSetTwice.ok'),
    check('platform.instance_key', 'error', 'instance.checks.instanceKey.unusable', {source: 'LIBREFOLIO_INSTANCE_KEY_FILE', reason: 'the file cannot be read'}),
    check('platform.session_cookie', 'ok', 'instance.checks.sessionCookie.ok'),
    check('platform.log_level', 'info', 'instance.checks.logLevel.verbose', {log_level: 'DEBUG'}),
    check('accounts.login_limit', 'warning', 'auth.checks.loginLimit.off'),
    check('email.smtp', 'ok', 'email.checks.smtp.ok'),
    check('email.smtp_encryption', 'warning', 'email.checks.smtpEncryption.plain'),
    check('email.links', 'info', 'email.checks.links.missing'),
    check('platform.plugin_secrets', 'error', 'instance.checks.pluginSecrets.unreadable', {count: 2}),
];

beforeEach(() => {
    mocks.listSecurityChecks.mockReset();
});

describe('fetchSecurityChecks — GET /api/v1/security/checks', () => {
    // red until A8b
    it('asks the generated client’s list_security_checks_api_v1_security_checks_get once, and resolves to the items of its answer as they came', async () => {
        const {fetchSecurityChecks} = await loadApi();
        mocks.listSecurityChecks.mockResolvedValueOnce({items: structuredClone(ANSWERED)});

        const checks = await fetchSecurityChecks();

        expect(mocks.listSecurityChecks).toHaveBeenCalledTimes(1);
        expect(checks, 'the platform’s order, every field, the numbers of detail still numbers').toEqual(ANSWERED);
        expect(checks.map((item) => item.check_id)).toEqual(ANSWERED.map((item) => item.check_id));
        expect(typeof checks.at(-1)?.detail.count, 'a count stays a number for the ICU plural').toBe('number');

        // The mocked operation is the generated client's own: the same alias, on the administrators' route.
        const route = generatedClient.api.find((endpoint) => endpoint.alias === mocks.operation);
        expect(route, `generated.ts has no operation ${mocks.operation}: run ./dev.py api sync`).toBeDefined();
        expect([route?.method, route?.path]).toEqual(['get', '/api/v1/security/checks']);
    });

    // red until A8b
    it('an answer without a check is an empty list', async () => {
        const {fetchSecurityChecks} = await loadApi();
        mocks.listSecurityChecks.mockResolvedValueOnce({items: []});

        await expect(fetchSecurityChecks()).resolves.toEqual([]);
        expect(mocks.listSecurityChecks).toHaveBeenCalledTimes(1);
    });

    // red until A8b
    it('a failure propagates: it rejects with the very error the client raised', async () => {
        const {fetchSecurityChecks} = await loadApi();
        const refused = Object.assign(new Error('Request failed with status code 403'), {isAxiosError: true, response: {status: 403, data: {detail: 'Admin privileges required'}}});
        mocks.listSecurityChecks.mockRejectedValueOnce(refused);

        await expect(fetchSecurityChecks(), 'the store decides what a failure means: it must see the error itself').rejects.toBe(refused);
        expect(mocks.listSecurityChecks).toHaveBeenCalledTimes(1);
    });
});
