// @vitest-environment jsdom
/**
 * EmailSettingsTab — Settings › Email, for administrators (workstream E, lot E2).
 *
 * The contract under test:
 *   - on mount the tab reads the status once; its root `email-tab` publishes `data-busy` (and `aria-busy`) true while a
 *     request is in flight — a read of the status, or the test email; the header's `email-docs` link opens the
 *     administrators' page `admin/email/`;
 *   - a first read that fails shows `email-load-error` (role alert) and nothing else; a later read that fails shows it
 *     above the last state read, which stays, with the outcome of the test; the next read that lands takes it down;
 *   - `email-state` carries `data-state` (off | invalid | ready) and its `email-state-badge`; off explains itself
 *     (`email-off-explanation`); invalid names the problem and the variable at fault (`email-problem`, `data-problem`,
 *     `data-variable`; the problem's message filled with the variable, an unknown code on the unknown message); ready
 *     shows the hourly budget (`email-budget`, `data-remaining`, `data-max`): what is left, or, once it is spent, the
 *     minutes until the next email fits;
 *   - `email-checks` lists the checks worth a line — not `ok`, and not `email.smtp`, whose problem the state already
 *     explains — in the server's order, each an `email-check` with `data-check-id` and `data-severity`, worded from its
 *     i18n key with its detail as values; with none, there is no list;
 *   - the test email is offered only when email is ready, and offered even with the shown budget spent (the budget is
 *     per server process, and a refusal says so). One request at a time: from the click until the status read again
 *     after the attempt has landed, the button is disabled, a click starts nothing, and `data-busy` stays true without
 *     a break. Then `email-test-outcome` (`data-outcome` sent | failed, role status | alert) says what happened — for a
 *     failure, the message of the failure read from the refusal, in the shape the generated client rejects with (an
 *     `AxiosError`) as in an `ApiError` — and `notify` records it (`email.test.sent` with the language,
 *     `email.test.failed` with the failure) without a toast, since the outcome is on screen; a new attempt takes the
 *     last outcome down while it runs;
 *   - the outcome is worded from state: a change of language rewords it, without a new request.
 *
 * Not pinned here: «an older read answered after a newer one does not overwrite it» (the generation counter of
 * `load()`). Two reads never overlap through the tab's surface: the mount read runs before there is a button to click,
 * and an attempt — the only other way to start a read — starts only when nothing is in flight, which the case «one
 * request at a time» pins. The counter guards a state this surface cannot reach.
 *
 * Mocks, all owned here:
 *   - `./emailApi`: `fetchEmailStatus` and `sendTestEmail` are fakes the test answers — with `EmailStatus` already
 *     normalized, its five keys present, as `fetchEmailStatus()` hands it over; deferreds where "in flight" is the
 *     subject. `readTestFailure` stays the real one, and a refusal is built as the client raises it: axios's own
 *     `AxiosError` carrying the response (as in `stores/app/auth.test.ts`), or an `ApiError`;
 *   - `$lib/i18n`: `_` is a writable translator owned by this file, answering `[<language>] <key> {<values>}`: an
 *     assertion names the key and the values the tab chose, never a sentence of the catalogue, and setting the store's
 *     translator is a change of language;
 *   - `$lib/stores/app/notify.svelte`: a spy (the event, not the toast, is the contract);
 *   - `$lib/stores/app/language`: the docs link's language, English.
 *
 * Every wait is on a state: `data-busy`, an element appearing, a deferred the test resolves. No clock. Whether
 * `data-busy` ever breaks is read from the DOM's own record of its changes (a MutationObserver), not sampled.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import type {Writable} from 'svelte/store';
import {AxiosError, AxiosHeaders, type InternalAxiosRequestConfig} from 'axios';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const fake = vi.hoisted(() => {
    /** The translator of one language: `[it] email.budget.remaining {max=20, remaining=17}`. */
    function translatorFor(language: string) {
        return (key: string, options?: {values?: Record<string, unknown>}): string => {
            const values = options?.values ?? {};
            const shown = Object.keys(values)
                .sort()
                .map((name) => `${name}=${String(values[name])}`);
            return shown.length > 0 ? `[${language}] ${key} {${shown.join(', ')}}` : `[${language}] ${key}`;
        };
    }
    return {
        translatorFor,
        fetchEmailStatus: vi.fn().mockName('fetchEmailStatus'),
        sendTestEmail: vi.fn().mockName('sendTestEmail'),
        notify: vi.fn().mockName('notify'),
    };
});

vi.mock('./emailApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./emailApi')>()),
    fetchEmailStatus: fake.fetchEmailStatus,
    sendTestEmail: fake.sendTestEmail,
}));
vi.mock('$lib/i18n', async () => {
    const {writable} = await import('svelte/store');
    return {_: writable(fake.translatorFor('en'))};
});
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));
vi.mock('$lib/stores/app/language', async () => {
    const {writable} = await import('svelte/store');
    return {currentLanguage: writable('en')};
});

import EmailSettingsTab from './EmailSettingsTab.svelte';
import {_} from '$lib/i18n';
import {ApiError} from '$lib/api';
import type {EmailCheck, EmailStatus, EmailTestResult} from './emailApi';

// --- The translator ------------------------------------------------------------------------------------------------

type Translator = ReturnType<typeof fake.translatorFor>;

/** The mocked `$_` store: setting its translator is a change of language. */
const translator = _ as unknown as Writable<Translator>;

/** What the tab must render for `key` with `values` in `language`: this file's translator, never the catalogue. */
function say(key: string, values?: Record<string, unknown>, language = 'en'): string {
    return fake.translatorFor(language)(key, values ? {values} : undefined);
}

// --- Fixtures: EmailStatus as fetchEmailStatus() hands it over, normalized, its five keys present --------------------

const SMTP_OFF: EmailCheck = {check_id: 'email.smtp', severity: 'ok', i18n_key: 'email.checks.smtp.off', detail: {}};
const SMTP_OK: EmailCheck = {check_id: 'email.smtp', severity: 'ok', i18n_key: 'email.checks.smtp.ok', detail: {}};
const ENCRYPTION_OK: EmailCheck = {check_id: 'email.smtp_encryption', severity: 'ok', i18n_key: 'email.checks.smtpEncryption.ok', detail: {}};
const ENCRYPTION_PLAIN: EmailCheck = {check_id: 'email.smtp_encryption', severity: 'warning', i18n_key: 'email.checks.smtpEncryption.plain', detail: {}};

function smtpInvalid(problem: string, variable: string): EmailCheck {
    return {check_id: 'email.smtp', severity: 'error', i18n_key: 'email.checks.smtp.invalid', detail: {problem, variable}};
}

function offStatus(): EmailStatus {
    return {state: 'off', problem: null, variable: null, checks: [SMTP_OFF, ENCRYPTION_OK], budget: null};
}

function invalidStatus(problem: string | null, variable: string | null): EmailStatus {
    return {state: 'invalid', problem, variable, checks: [smtpInvalid(problem ?? '', variable ?? ''), ENCRYPTION_OK], budget: null};
}

function readyStatus(remaining: number, {max = 20, retryAfterSeconds = 0, checks = [SMTP_OK, ENCRYPTION_OK]}: {max?: number; retryAfterSeconds?: number; checks?: EmailCheck[]} = {}): EmailStatus {
    return {state: 'ready', problem: null, variable: null, checks, budget: {max_per_hour: max, remaining, retry_after_seconds: retryAfterSeconds}};
}

const SENT: EmailTestResult = {language: 'it', message: 'Test email sent'};

/** The config axios attaches to every error it raises. */
const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** A refusal of `POST /email/test` as the generated client rejects with it: axios's own error, carrying the response. */
function axiosRefusal(status: number, detail: Record<string, unknown>): AxiosError {
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, REQUEST, {}, {status, statusText: '', headers: {}, config: REQUEST, data: {detail}});
}

/** The same refusal carried by an ApiError, the other shape `readTestFailure` reads. */
function apiErrorRefusal(status: number, statusText: string, detail: Record<string, unknown>): ApiError {
    return new ApiError(status, statusText, {detail});
}

/** A request that reached no server: axios's own error, without a response. */
function networkError(): AxiosError {
    return new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {});
}

// --- Helpers -------------------------------------------------------------------------------------------------------

/** A promise this test settles by hand, so that "in flight" is a state it controls. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

function text(element: Element): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

const tab = () => screen.getByTestId('email-tab');
const testButton = () => screen.getByTestId('email-test-button');

/** The test email as the tab offers it: not at all, or its button disabled or enabled. */
function offer(): 'not offered' | 'disabled' | 'enabled' {
    const button = screen.queryByTestId('email-test-button') as HTMLButtonElement | null;
    if (button === null) return 'not offered';
    return button.disabled ? 'disabled' : 'enabled';
}

/** Every request the tab started has landed. */
async function settled(): Promise<void> {
    await waitFor(() => expect(tab()).toHaveAttribute('data-busy', 'false'));
}

/** Mount, and wait for the first read to land. */
async function mount(): Promise<void> {
    render(EmailSettingsTab);
    await settled();
}

/**
 * Starts recording the values `data-busy` takes, from the DOM's own record of its changes, and returns the reader: the
 * values in order, the current one last, repeats folded. A break in a busy stretch shows as a `false` between two
 * `true`s; nothing is sampled, so nothing is missed.
 */
function recordBusy(): () => Array<string | null> {
    const element = tab();
    const records: MutationRecord[] = [];
    const observer = new MutationObserver((batch) => {
        records.push(...batch);
    });
    observer.observe(element, {attributes: true, attributeFilter: ['data-busy'], attributeOldValue: true});
    return () => {
        records.push(...observer.takeRecords());
        observer.disconnect();
        const values = [...records.map((record) => record.oldValue), element.getAttribute('data-busy')];
        return values.filter((value, index) => index === 0 || value !== values[index - 1]);
    };
}

beforeAll(() => {
    // The absences asserted below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
});

beforeEach(() => {
    fake.fetchEmailStatus.mockReset();
    fake.sendTestEmail.mockReset();
    fake.notify.mockReset();
    translator.set(fake.translatorFor('en'));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('EmailSettingsTab — reading the status', () => {
    it('reads the status once on mount, and is busy, showing none of it, until the answer lands', async () => {
        const first = deferred<EmailStatus>();
        fake.fetchEmailStatus.mockReturnValueOnce(first.promise);

        render(EmailSettingsTab);

        expect(fake.fetchEmailStatus).toHaveBeenCalledTimes(1);
        expect(tab()).toHaveAttribute('data-busy', 'true');
        expect(tab()).toHaveAttribute('aria-busy', 'true');
        expect(screen.getByTestId('email-docs'), 'the header is drawn meanwhile').toBeInTheDocument();
        expect(screen.queryByTestId('email-state')).toBeNull();
        expect(screen.queryByTestId('email-load-error')).toBeNull();

        first.resolve(readyStatus(17));
        await settled();

        expect(tab()).toHaveAttribute('aria-busy', 'false');
        expect(screen.getByTestId('email-state')).toHaveAttribute('data-state', 'ready');
        expect(fake.fetchEmailStatus, 'one read: nothing polls').toHaveBeenCalledTimes(1);
    });

    it('a first read that fails says so (role alert), and shows nothing else: no state, no notice, no test email', async () => {
        fake.fetchEmailStatus.mockRejectedValueOnce(networkError());
        await mount();

        const error = screen.getByTestId('email-load-error');
        expect(error).toHaveAttribute('role', 'alert');
        expect(text(error)).toBe(say('email.loadError'));
        for (const absent of ['email-state', 'email-budget', 'email-checks', 'email-test', 'email-test-outcome']) {
            expect(screen.queryByTestId(absent), `${absent} is not drawn`).toBeNull();
        }
    });

    it('the documentation link opens the administrators’ page on email', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(offStatus());
        const open = vi.spyOn(window, 'open').mockImplementation(() => null);
        await mount();
        const docs = screen.getByTestId('email-docs');
        expect(docs).toHaveAttribute('aria-label', say('common.documentation'));

        await fireEvent.click(docs);

        expect(open).toHaveBeenCalledTimes(1);
        expect(open).toHaveBeenCalledWith('/mkdocs/admin/email/', '_blank', 'noopener');
    });
});

// =====================================================================================================================
describe('EmailSettingsTab — the state', () => {
    it('off: the off badge and the explanation; no problem, no budget', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(offStatus());
        await mount();

        expect(screen.getByTestId('email-state')).toHaveAttribute('data-state', 'off');
        expect(text(screen.getByTestId('email-state-badge'))).toBe(say('email.state.off'));
        expect(text(screen.getByTestId('email-off-explanation'))).toBe(say('email.off.explanation'));
        expect(screen.queryByTestId('email-problem')).toBeNull();
        expect(screen.queryByTestId('email-budget')).toBeNull();
    });

    it.each([
        {label: 'a known problem', problem: 'SMTP_PORT_INVALID', variable: 'LIBREFOLIO_SMTP_PORT', key: 'email.problems.SMTP_PORT_INVALID'},
        {label: 'a problem this build does not know', problem: 'SMTP_SOMETHING_NEW', variable: 'LIBREFOLIO_SMTP_SOMETHING', key: 'email.problems.unknown'},
        {label: 'neither problem nor variable', problem: null, variable: null, key: 'email.problems.unknown'},
    ])('invalid, $label: the problem and the variable at fault, the message filled with the variable', async ({problem, variable, key}) => {
        fake.fetchEmailStatus.mockResolvedValueOnce(invalidStatus(problem, variable));
        await mount();

        expect(screen.getByTestId('email-state')).toHaveAttribute('data-state', 'invalid');
        expect(text(screen.getByTestId('email-state-badge'))).toBe(say('email.state.invalid'));
        const shown = screen.getByTestId('email-problem');
        expect(shown).toHaveAttribute('data-problem', problem ?? '');
        expect(shown).toHaveAttribute('data-variable', variable ?? '');
        expect(text(shown)).toBe(say(key, {variable: variable ?? ''}));
        expect(screen.queryByTestId('email-off-explanation')).toBeNull();
        expect(screen.queryByTestId('email-budget')).toBeNull();
    });

    it('ready, with emails left: what is left of the hourly budget, out of its maximum', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(17, {max: 20}));
        await mount();

        expect(screen.getByTestId('email-state')).toHaveAttribute('data-state', 'ready');
        expect(text(screen.getByTestId('email-state-badge'))).toBe(say('email.state.ready'));
        const budget = screen.getByTestId('email-budget');
        expect(budget).toHaveAttribute('data-remaining', '17');
        expect(budget).toHaveAttribute('data-max', '20');
        expect(text(budget)).toBe(say('email.budget.remaining', {remaining: 17, max: 20}));
        expect(screen.queryByTestId('email-problem')).toBeNull();
        expect(screen.queryByTestId('email-off-explanation')).toBeNull();
    });

    it('ready, with the budget spent: the limit reached, and the minutes until the next email fits, rounded up', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(0, {max: 20, retryAfterSeconds: 125}));
        await mount();

        const budget = screen.getByTestId('email-budget');
        expect(budget).toHaveAttribute('data-remaining', '0');
        expect(budget).toHaveAttribute('data-max', '20');
        expect(text(budget)).toBe(say('email.budget.spent', {max: 20, minutes: 3}));
    });
});

// =====================================================================================================================
describe('EmailSettingsTab — the configuration notices', () => {
    it('no check worth a line — ok checks, and email.smtp whose problem the state explains — means no list at all', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(invalidStatus('SMTP_PORT_INVALID', 'LIBREFOLIO_SMTP_PORT'));
        await mount();

        expect(screen.getByTestId('email-problem'), 'premise: the state is drawn, its problem named').toBeInTheDocument();
        expect(screen.queryByTestId('email-checks')).toBeNull();
        expect(screen.queryByTestId('email-check')).toBeNull();
    });

    it.each([
        {severity: 'info', key: 'email.checks.smtpEncryption.localPlain'},
        {severity: 'warning', key: 'email.checks.smtpEncryption.plain'},
        {severity: 'error', key: 'email.checks.smtpEncryption.plain'},
    ] as const)('a check of severity $severity is listed, with its id, its severity and its message', async ({severity, key}) => {
        const check: EmailCheck = {check_id: 'email.smtp_encryption', severity, i18n_key: key, detail: {}};
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(17, {checks: [SMTP_OK, check]}));
        await mount();

        const listed = within(screen.getByTestId('email-checks')).getAllByTestId('email-check');
        expect(listed.map((item) => [item.dataset.checkId, item.dataset.severity, text(item)])).toEqual([['email.smtp_encryption', severity, say(key)]]);
    });

    it('lists them in the server’s order, each worded from its own key with its detail as values', async () => {
        const note: EmailCheck = {check_id: 'email.future_note', severity: 'info', i18n_key: 'email.checks.futureNote', detail: {count: 2}};
        const fault: EmailCheck = {check_id: 'email.future_fault', severity: 'error', i18n_key: 'email.checks.futureFault', detail: {variable: 'LIBREFOLIO_SMTP_FROM', code: 550}};
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(17, {checks: [SMTP_OK, note, ENCRYPTION_PLAIN, fault]}));
        await mount();

        const listed = within(screen.getByTestId('email-checks')).getAllByTestId('email-check');
        expect(listed.map((item) => [item.dataset.checkId, item.dataset.severity, text(item)])).toEqual([
            ['email.future_note', 'info', say('email.checks.futureNote', {count: 2})],
            ['email.smtp_encryption', 'warning', say('email.checks.smtpEncryption.plain')],
            ['email.future_fault', 'error', say('email.checks.futureFault', {variable: 'LIBREFOLIO_SMTP_FROM', code: 550})],
        ]);
    });
});

// =====================================================================================================================
/** Each way `POST /email/test` can fail, what the outcome must say, and the status read after it. */
const REFUSED: Array<{label: string; raise: () => unknown; failure: Record<string, unknown>; message: {key: string; values?: Record<string, unknown>}; after: EmailStatus}> = [
    {
        label: '409 EMAIL_UNAVAILABLE',
        raise: () => axiosRefusal(409, {error_code: 'EMAIL_UNAVAILABLE', problem: 'SMTP_PASSWORD_UNREADABLE', message: 'Email is off or cannot be used on this instance'}),
        failure: {errorCode: 'EMAIL_UNAVAILABLE', problem: 'SMTP_PASSWORD_UNREADABLE'},
        message: {key: 'email.test.errors.EMAIL_UNAVAILABLE'},
        after: invalidStatus('SMTP_PASSWORD_UNREADABLE', 'LIBREFOLIO_SMTP_PASSWORD_FILE'),
    },
    {
        label: '429 EMAIL_RATE_LIMITED',
        raise: () => axiosRefusal(429, {error_code: 'EMAIL_RATE_LIMITED', retry_after: 300, message: 'The hourly email limit of the instance is reached'}),
        failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 300},
        message: {key: 'email.test.errors.EMAIL_RATE_LIMITED', values: {minutes: 5}},
        after: readyStatus(0, {retryAfterSeconds: 300}),
    },
    {
        label: '502 EMAIL_DELIVERY_FAILED',
        raise: () => axiosRefusal(502, {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 'AUTH_FAILED', message: 'The SMTP server did not take the message'}),
        failure: {errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode: 'AUTH_FAILED'},
        message: {key: 'email.smtpErrors.AUTH_FAILED'},
        after: readyStatus(16),
    },
    {
        label: '422 EMAIL_RECIPIENT_INVALID',
        raise: () => axiosRefusal(422, {error_code: 'EMAIL_RECIPIENT_INVALID', message: 'The address of this account is not a single email address'}),
        failure: {errorCode: 'EMAIL_RECIPIENT_INVALID'},
        message: {key: 'email.test.errors.EMAIL_RECIPIENT_INVALID'},
        after: readyStatus(17),
    },
    {
        label: '502 EMAIL_DELIVERY_FAILED carried by an ApiError',
        raise: () => apiErrorRefusal(502, 'Bad Gateway', {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 'TLS_FAILED', message: 'The SMTP server did not take the message'}),
        failure: {errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode: 'TLS_FAILED'},
        message: {key: 'email.smtpErrors.TLS_FAILED'},
        after: readyStatus(16),
    },
    {
        label: 'a request that reached no server',
        raise: networkError,
        failure: {errorCode: 'UNKNOWN'},
        message: {key: 'email.test.errors.generic'},
        after: readyStatus(17),
    },
];

describe('EmailSettingsTab — the test email', () => {
    it.each([
        {state: 'off', status: () => offStatus()},
        {state: 'invalid', status: () => invalidStatus('SMTP_FROM_MISSING', 'LIBREFOLIO_SMTP_FROM')},
    ])('is not offered while email is $state', async ({state, status}) => {
        fake.fetchEmailStatus.mockResolvedValueOnce(status());
        await mount();

        expect(screen.getByTestId('email-state'), 'premise: the state is drawn').toHaveAttribute('data-state', state);
        expect(screen.queryByTestId('email-test')).toBeNull();
        expect(offer()).toBe('not offered');
    });

    it('is offered, and can be tried, even with the shown budget spent: the budget is per server process, and a refusal says so', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(0, {retryAfterSeconds: 600}));
        await mount();

        expect(screen.getByTestId('email-budget'), 'premise: the budget shown is spent').toHaveAttribute('data-remaining', '0');
        expect(offer()).toBe('enabled');
    });

    it('sends: busy without a break from the click to the end of the status read again, and the outcome sent (role status), recorded', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(17));
        const sending = deferred<EmailTestResult>();
        fake.sendTestEmail.mockReturnValueOnce(sending.promise);
        const reread = deferred<EmailStatus>();
        fake.fetchEmailStatus.mockReturnValueOnce(reread.promise);
        await mount();
        expect(offer()).toBe('enabled');
        expect(text(testButton())).toBe(say('email.test.button'));
        const busyTrail = recordBusy();

        await fireEvent.click(testButton());

        expect(fake.sendTestEmail).toHaveBeenCalledTimes(1);
        expect(tab(), 'busy while the test email is in flight').toHaveAttribute('data-busy', 'true');
        expect(tab()).toHaveAttribute('aria-busy', 'true');
        expect(offer(), 'one attempt at a time').toBe('disabled');
        expect(text(testButton())).toBe(say('email.test.sending'));
        expect(screen.queryByTestId('email-test-outcome'), 'no outcome while the request is in flight').toBeNull();
        expect(fake.notify).not.toHaveBeenCalled();
        expect(fake.fetchEmailStatus, 'the status is read again only once the attempt is over').toHaveBeenCalledTimes(1);

        sending.resolve(SENT);

        const outcome = await screen.findByTestId('email-test-outcome');
        expect(outcome).toHaveAttribute('data-outcome', 'sent');
        expect(outcome).toHaveAttribute('role', 'status');
        expect(text(outcome)).toBe(say('email.test.sent'));
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify, 'the event with the language of the email, and no toast: the outcome is on screen').toHaveBeenCalledWith({name: 'email.test.sent', detail: {language: 'it'}});
        expect(fake.fetchEmailStatus, 'the status is read again').toHaveBeenCalledTimes(2);
        expect(tab(), 'busy while the status is read again').toHaveAttribute('data-busy', 'true');
        expect(offer(), 'disabled until the status read again has landed').toBe('disabled');

        reread.resolve(readyStatus(16));
        await settled();

        expect(screen.getByTestId('email-budget'), 'the answer of the new read is shown').toHaveAttribute('data-remaining', '16');
        expect(screen.getByTestId('email-test-outcome'), 'the outcome stays').toHaveAttribute('data-outcome', 'sent');
        expect(offer()).toBe('enabled');
        expect(busyTrail(), 'data-busy: true from the click to the end of the read, without a break').toEqual(['false', 'true', 'false']);
    });

    it.each(REFUSED)('$label: the outcome is failed (role alert) with its message, the failure recorded, the status read again', async ({raise, failure, message, after}) => {
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(17));
        const reread = deferred<EmailStatus>();
        fake.fetchEmailStatus.mockReturnValueOnce(reread.promise);
        fake.sendTestEmail.mockRejectedValueOnce(raise());
        await mount();

        await fireEvent.click(testButton());

        const outcome = await screen.findByTestId('email-test-outcome');
        expect(outcome).toHaveAttribute('data-outcome', 'failed');
        expect(outcome).toHaveAttribute('role', 'alert');
        expect(text(outcome)).toBe(say(message.key, message.values));
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify, 'the event with the failure, and no toast: the outcome is on screen').toHaveBeenCalledWith({name: 'email.test.failed', detail: failure});
        expect(fake.fetchEmailStatus, 'the status is read again after the attempt').toHaveBeenCalledTimes(2);
        expect(tab()).toHaveAttribute('data-busy', 'true');
        expect(offer(), 'disabled until the status read again has landed').toBe('disabled');

        reread.resolve(after);
        await settled();

        expect(screen.getByTestId('email-state')).toHaveAttribute('data-state', after.state);
        expect(offer(), 'offered again, enabled, only while email is ready').toBe(after.state === 'ready' ? 'enabled' : 'not offered');
        expect(screen.getByTestId('email-test-outcome'), 'the outcome stays once the status is read again').toHaveAttribute('data-outcome', 'failed');
    });

    it('one request at a time: a click while one is in flight starts nothing, even one that reaches the button before it is drawn disabled', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(17));
        const sending = deferred<EmailTestResult>();
        fake.sendTestEmail.mockReturnValueOnce(sending.promise);
        const reread = deferred<EmailStatus>();
        fake.fetchEmailStatus.mockReturnValueOnce(reread.promise);
        await mount();
        const button = testButton();

        // Two clicks in one task: the DOM is drawn again only after it, so the second click finds the button still
        // enabled and reaches the handler. Only the handler's own check can refuse it.
        button.click();
        expect(button, 'premise: the DOM has not caught up, so the second click reaches the handler').toBeEnabled();
        button.click();
        flushSync();

        expect(fake.sendTestEmail, 'one attempt for the two clicks').toHaveBeenCalledTimes(1);
        expect(offer()).toBe('disabled');

        sending.resolve(SENT);
        await waitFor(() => expect(fake.fetchEmailStatus).toHaveBeenCalledTimes(2));
        expect(offer(), 'premise: the status is being read again').toBe('disabled');

        // A click dispatched on the disabled button: Svelte still hands it to the handler when the button is its target.
        await fireEvent.click(testButton());

        expect(fake.sendTestEmail, 'no attempt while the status is read again').toHaveBeenCalledTimes(1);
        expect(fake.fetchEmailStatus, 'and no second read').toHaveBeenCalledTimes(2);

        reread.resolve(readyStatus(16));
        await settled();

        expect(
            fake.notify.mock.calls.map(([event]) => event.name),
            'one attempt, one event',
        ).toEqual(['email.test.sent']);
        expect(offer()).toBe('enabled');
    });

    it('a status read again that fails keeps the last state and the outcome, with the load error above them; the next read that lands takes it down', async () => {
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(17));
        fake.sendTestEmail.mockResolvedValueOnce(SENT);
        fake.fetchEmailStatus.mockRejectedValueOnce(networkError());
        await mount();

        await fireEvent.click(testButton());
        await waitFor(() => expect(fake.fetchEmailStatus).toHaveBeenCalledTimes(2));
        await settled();

        const error = screen.getByTestId('email-load-error');
        const state = screen.getByTestId('email-state');
        expect(error).toHaveAttribute('role', 'alert');
        expect(text(error)).toBe(say('email.loadError'));
        expect(state, 'the last state read stays').toHaveAttribute('data-state', 'ready');
        expect(screen.getByTestId('email-budget')).toHaveAttribute('data-remaining', '17');
        expect(screen.getByTestId('email-test-outcome'), 'the outcome of the attempt stays').toHaveAttribute('data-outcome', 'sent');
        expect(error.compareDocumentPosition(state) & Node.DOCUMENT_POSITION_FOLLOWING, 'the error stands above the state').not.toBe(0);
        expect(offer(), 'nothing in flight: the test email can be tried again').toBe('enabled');

        fake.sendTestEmail.mockResolvedValueOnce(SENT);
        fake.fetchEmailStatus.mockResolvedValueOnce(readyStatus(15));
        await fireEvent.click(testButton());
        await waitFor(() => expect(fake.fetchEmailStatus).toHaveBeenCalledTimes(3));
        await settled();

        expect(screen.queryByTestId('email-load-error'), 'a read that lands takes the error down').toBeNull();
        expect(screen.getByTestId('email-budget')).toHaveAttribute('data-remaining', '15');
        expect(screen.getByTestId('email-test-outcome')).toHaveAttribute('data-outcome', 'sent');
    });

    it('a new attempt takes the last outcome down while it runs, and puts its own in its place', async () => {
        fake.fetchEmailStatus.mockImplementation(async () => readyStatus(17));
        fake.sendTestEmail.mockRejectedValueOnce(axiosRefusal(502, {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 'TIMEOUT', message: 'The SMTP server did not take the message'}));
        await mount();
        await fireEvent.click(testButton());
        await waitFor(() => expect(screen.getByTestId('email-test-outcome')).toHaveAttribute('data-outcome', 'failed'));
        await waitFor(() => expect(fake.fetchEmailStatus).toHaveBeenCalledTimes(2));
        await settled();

        const second = deferred<EmailTestResult>();
        fake.sendTestEmail.mockReturnValueOnce(second.promise);
        await fireEvent.click(testButton());

        expect(offer(), 'premise: the new attempt is in flight').toBe('disabled');
        expect(screen.queryByTestId('email-test-outcome'), 'the last failure is not shown beside an attempt in flight').toBeNull();

        second.resolve(SENT);

        await waitFor(() => expect(screen.getByTestId('email-test-outcome')).toHaveAttribute('data-outcome', 'sent'));
        expect(fake.notify.mock.calls.map(([event]) => event.name)).toEqual(['email.test.failed', 'email.test.sent']);
        await waitFor(() => expect(fake.fetchEmailStatus).toHaveBeenCalledTimes(3));
        await settled();
    });

    it.each([
        {kind: 'sent', attempt: () => fake.sendTestEmail.mockResolvedValueOnce(SENT), key: 'email.test.sent', values: undefined},
        {
            kind: 'failed',
            attempt: () => fake.sendTestEmail.mockRejectedValueOnce(axiosRefusal(429, {error_code: 'EMAIL_RATE_LIMITED', retry_after: 300, message: 'The hourly email limit of the instance is reached'})),
            key: 'email.test.errors.EMAIL_RATE_LIMITED',
            values: {minutes: 5},
        },
    ])('a $kind outcome is worded again when the language changes, without a new request', async ({kind, attempt, key, values}) => {
        fake.fetchEmailStatus.mockImplementation(async () => readyStatus(17));
        attempt();
        await mount();
        await fireEvent.click(testButton());
        await waitFor(() => expect(screen.getByTestId('email-test-outcome')).toHaveAttribute('data-outcome', kind));
        await waitFor(() => expect(fake.fetchEmailStatus).toHaveBeenCalledTimes(2));
        await settled();
        expect(text(screen.getByTestId('email-test-outcome'))).toBe(say(key, values));

        translator.set(fake.translatorFor('it'));
        flushSync();

        const outcome = screen.getByTestId('email-test-outcome');
        expect(text(outcome)).toBe(say(key, values, 'it'));
        expect(outcome).toHaveAttribute('data-outcome', kind);
        expect(text(screen.getByTestId('email-state-badge')), 'the rest of the tab follows too').toBe(say('email.state.ready', undefined, 'it'));
        expect(fake.sendTestEmail, 'a new wording is not a new attempt').toHaveBeenCalledTimes(1);
        expect(fake.fetchEmailStatus, 'nor a new read').toHaveBeenCalledTimes(2);
    });
});
