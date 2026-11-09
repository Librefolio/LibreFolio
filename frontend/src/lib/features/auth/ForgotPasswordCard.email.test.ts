// @vitest-environment jsdom
/**
 * ForgotPasswordCard with «forgot password» by email (workstream E, lot E4b): A's card on the sign-in page hosts E's
 * form while emails with a link can go out (`GET /system/instance` → `email.links`), and keeps its warning otherwise.
 *
 * The contract under test:
 *   - without `email.links` — no email part, `links` false or absent —: the warning (`forgot-email-unavailable`, saying
 *     `auth.emailRecoveryNotAvailable`) and no form (`forgot-email-form`);
 *   - with `email.links` true: the form, its identifier field included, and no warning;
 *   - the command box (`forgot-reset-commands`), for whoever runs the server, only without email links: under the warning,
 *     open, as before. With email links the reset link comes by email and the card shows no server command at all — no
 *     box, no panel (`forgot-commands-panel`, `forgot-commands-toggle`), no heading, no docker or CLI text: the
 *     administrator's guide keeps them (developer's decision, 09/11/2026, lot UA1; it replaces the closed panel of P1);
 *   - on mount the card calls `instanceConfig.load()` once, not forced: the sign-in page's request already answered, it
 *     asks the server nothing of its own;
 *   - the page's request still in flight when the card is drawn: the warning and the commands first, then the form in
 *     their place, the commands gone, once the answer says `email.links: true` — the card is a legacy component, and its
 *     `{#if}` must still follow the store —, the request shared, none of the card's own;
 *   - no request yet (or the last one failed): the card's `load()` asks `GET /system/instance` itself, once, and shows the
 *     form when the answer says `email.links: true`;
 *   - «back to login» (`forgot-back-to-login`) dispatches `gotoLogin`, with the form shown or not.
 *
 * Mocks, all owned here: the instance configuration is the real store (`instanceConfig.svelte`), its answer set per test
 * by a forced `load` whose `fetchConfig` the test controls; `instanceConfig.load` is then spied, calling through; the
 * generated alias of `GET /system/instance` is spied and refuses unless a test answers it, so no case reaches a
 * network; `$lib/i18n`: `_` is a writable translator answering `[<language>] <key>`; `notify` a spy. The form is E's real
 * `ForgotPasswordEmailForm`, whose own behaviour is `features/email/ForgotPasswordEmailForm.test.ts`'s subject.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const fake = vi.hoisted(() => {
    function translatorFor(language: string) {
        return (key: string, options?: {values?: Record<string, unknown>}): string => {
            const values = options?.values ?? {};
            const shown = Object.keys(values)
                .sort()
                .map((name) => `${name}=${String(values[name])}`);
            return shown.length > 0 ? `[${language}] ${key} {${shown.join(', ')}}` : `[${language}] ${key}`;
        };
    }
    return {translatorFor, notify: vi.fn().mockName('notify')};
});

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));
vi.mock('$lib/i18n', async () => {
    const {writable} = await import('svelte/store');
    return {_: writable(fake.translatorFor('en'))};
});

import ForgotPasswordCard from './ForgotPasswordCard.svelte';
import {zodiosApi} from '$lib/api';
import {instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

const INSTANCE_ALIAS = 'get_instance_config_api_v1_system_instance_get';
/** The generated client seen through that one alias: spying through the full client type sends TS into an excessively deep instantiation. */
const instanceEndpoint = zodiosApi as unknown as Record<typeof INSTANCE_ALIAS, () => Promise<InstanceConfig>>;
const BASE: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const WITH_LINKS: InstanceConfig = {...BASE, email: {available: true, links: true}};
const WITHOUT_LINKS: Array<{label: string; config: InstanceConfig}> = [
    {label: 'no email part (an older server)', config: BASE},
    {label: 'email available, links false', config: {...BASE, email: {available: true, links: false}}},
    {label: 'email unavailable, links absent', config: {...BASE, email: {available: false}}},
];

function say(key: string, language = 'en'): string {
    return fake.translatorFor(language)(key);
}

const warning = () => screen.queryByTestId('forgot-email-unavailable');
const emailForm = () => screen.queryByTestId('forgot-email-form');
const commands = () => screen.queryByTestId('forgot-reset-commands');
const commandsPanel = () => screen.queryByTestId('forgot-commands-panel');
const commandsToggle = () => screen.queryByTestId('forgot-commands-toggle');
/** The heading over the commands («Run this command on the server:»). */
const TERMINAL_HEADING_KEY = 'auth.serverTerminalInstructions';
/** The commands of the box, as literal text: neither is translated. */
const COMMAND_TOKENS = [/docker/i, /dev\.py/i];

function cardText(): string {
    return screen.getByTestId('forgot-modal').textContent ?? '';
}

/** No server command anywhere in the card: no box, no panel or its summary, no heading, no docker or CLI text. */
function expectNoServerCommands(): void {
    expect(commands(), 'no forgot-reset-commands').toBeNull();
    expect(commandsPanel(), 'no forgot-commands-panel').toBeNull();
    expect(commandsToggle(), 'no forgot-commands-toggle').toBeNull();
    const text = cardText();
    for (const token of COMMAND_TOKENS) expect(text, `no ${token} anywhere in the card`).not.toMatch(token);
    expect(text, 'no «run this command on the server» heading').not.toContain(TERMINAL_HEADING_KEY);
}

/** The configuration in force, as if the sign-in page's own request had answered `config`. */
async function answered(config: InstanceConfig): Promise<void> {
    await instanceConfig.load({force: true, fetchConfig: () => Promise.resolve(config)});
}

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
        resolve = res;
    });
    return {promise, resolve};
}

/** Draw the card, its `load()` spied from now on; `gotoLogin` records each dispatch. */
function mount(): {load: MockInstance<typeof instanceConfig.load>; gotoLogin: ReturnType<typeof vi.fn>} {
    const load = vi.spyOn(instanceConfig, 'load');
    const gotoLogin = vi.fn();
    render(ForgotPasswordCard, {$$events: {gotoLogin: () => gotoLogin()}} as never);
    return {load, gotoLogin};
}

/** Whether each call of `load()` the card made was forced. */
function forced(load: MockInstance<typeof instanceConfig.load>): boolean[] {
    return load.mock.calls.map(([options]) => options?.force === true);
}

let instanceRequest: MockInstance;

beforeAll(() => {
    assertEffectsRun();
});

beforeEach(() => {
    fake.notify.mockReset();
    instanceRequest = vi.spyOn(instanceEndpoint, INSTANCE_ALIAS).mockRejectedValue(new Error('no network in this test'));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('ForgotPasswordCard — what it offers', () => {
    it.each(WITHOUT_LINKS)('FCE-01: $label — the warning and the command box, open, no form', async ({config}) => {
        await answered(config);

        mount();

        expect(warning(), 'the warning tells the user the reset link cannot come by email').toBeVisible();
        expect(warning()).toHaveTextContent(say('auth.emailRecoveryNotAvailable'));
        expect(commands(), 'the commands stay, for whoever runs the server, open as before').toBeVisible();
        expect(commandsPanel(), 'no panel to open: without email nothing changes').toBeNull();
        for (const token of COMMAND_TOKENS) expect(cardText(), `positive control: the scan sees ${token}`).toMatch(token);
        expect(cardText(), 'positive control: the scan sees the heading').toContain(TERMINAL_HEADING_KEY);
        expect(emailForm()).toBeNull();
    });

    it('FCE-02: email.links true — the form, its field included; no server command, no panel, no warning', async () => {
        await answered(WITH_LINKS);

        mount();

        // Presence first — the form and a sibling control on view —, so every absence below is of a drawn card.
        expect(emailForm()).toBeVisible();
        expect(screen.getByTestId('forgot-email-identifier')).toBeEnabled();
        expect(screen.getByTestId('forgot-back-to-login')).toBeVisible();
        expectNoServerCommands();
        expect(warning()).toBeNull();
    });
});

describe('ForgotPasswordCard — the instance configuration', () => {
    it('FCE-03: on mount it calls instanceConfig.load() once, not forced; with the page’s request answered it asks nothing of its own', async () => {
        await answered(WITH_LINKS);

        const {load} = mount();

        await waitFor(() => expect(load).toHaveBeenCalledTimes(1));
        expect(forced(load)).toEqual([false]);
        expect(instanceRequest).not.toHaveBeenCalled();
    });

    it('FCE-04: the page’s request in flight when the card is drawn — the warning first, then the form in its place once the answer says email.links; one request, shared', async () => {
        await answered(BASE);
        const answer = deferred<InstanceConfig>();
        void instanceConfig.load({force: true, fetchConfig: () => answer.promise});

        const {load} = mount();
        await waitFor(() => expect(load).toHaveBeenCalledTimes(1));
        expect(warning(), 'before the answer: the defaults, no email part').not.toBeNull();
        expect(commands(), 'with the warning, the commands').not.toBeNull();
        expect(emailForm()).toBeNull();

        answer.resolve(WITH_LINKS);

        await waitFor(() => expect(emailForm()).not.toBeNull());
        expect(warning()).toBeNull();
        expectNoServerCommands();
        expect(forced(load)).toEqual([false]);
        expect(instanceRequest, 'the card shares the page’s request').not.toHaveBeenCalled();
    });

    it('FCE-05: no request pending — the last one failed — the card asks GET /system/instance itself, once, and shows the form when it says email.links', async () => {
        await answered(BASE);
        await instanceConfig.load({force: true, fetchConfig: () => Promise.reject(new Error('the page’s request failed'))});
        expect(instanceConfig.failed, 'premise: the last request failed, so nothing is pending').toBe(true);
        instanceRequest.mockResolvedValueOnce(WITH_LINKS);

        const {load} = mount();

        await waitFor(() => expect(emailForm()).not.toBeNull());
        expect(warning()).toBeNull();
        expect(forced(load)).toEqual([false]);
        expect(instanceRequest).toHaveBeenCalledTimes(1);
    });
});

describe('ForgotPasswordCard — back to the sign-in', () => {
    it.each([
        {label: 'the form shown', config: WITH_LINKS, form: true},
        {label: 'the warning shown', config: BASE, form: false},
    ])('FCE-06: $label — «back to login» dispatches gotoLogin, once', async ({config, form}) => {
        await answered(config);
        const {gotoLogin} = mount();
        expect(emailForm() !== null, `premise: ${form ? 'the form' : 'no form'}`).toBe(form);

        await fireEvent.click(screen.getByTestId('forgot-back-to-login'));

        expect(gotoLogin).toHaveBeenCalledTimes(1);
    });
});
