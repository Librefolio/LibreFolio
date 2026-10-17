// @vitest-environment jsdom
/**
 * ForgotPasswordCard with «forgot password» by email (workstream E, lot E4b): A's card on the sign-in page hosts E's
 * form while emails with a link can go out (`GET /system/instance` → `email.links`), and keeps its warning otherwise.
 *
 * The contract under test:
 *   - without `email.links` — no email part, `links` false or absent —: the warning (`forgot-email-unavailable`, saying
 *     `auth.emailRecoveryNotAvailable`) and no form (`forgot-email-form`);
 *   - with `email.links` true: the form, its identifier field included, and no warning;
 *   - the command box (`forgot-reset-commands`) is there in both cases, for whoever runs the server: under the warning
 *     open, as before, no panel around it; under the form inside a native `<details>` closed by default
 *     (`forgot-commands-panel`), hidden until a click on its `<summary>` (`forgot-commands-toggle`) opens it — the
 *     developer's decision P1, 16/10;
 *   - on mount the card calls `instanceConfig.load()` once, not forced: the sign-in page's request already answered, it
 *     asks the server nothing of its own;
 *   - the page's request still in flight when the card is drawn: the warning first, then the form in its place once the
 *     answer says `email.links: true` — the card is a legacy component, and its `{#if}` must still follow the store —,
 *     the request shared, none of the card's own;
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
    instanceRequest = vi.spyOn(zodiosApi, INSTANCE_ALIAS).mockRejectedValue(new Error('no network in this test'));
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
        expect(emailForm()).toBeNull();
    });

    it('FCE-02: email.links true — the form, its field included, and the command box in a panel closed by default; no warning', async () => {
        await answered(WITH_LINKS);

        mount();

        expect(emailForm()).not.toBeNull();
        expect(screen.getByTestId('forgot-email-identifier')).toBeEnabled();
        expect(commandsPanel(), 'the commands stay below the form, in a panel').not.toBeNull();
        expect(commandsPanel(), 'closed by default: the developer’s decision P1').not.toHaveAttribute('open');
        // jest-dom's `toBeVisible` reads a closed <details> as a browser draws its content — the <summary> on view, the rest
        // hidden — but, unlike a browser, counts the closed <details> itself as hidden too: the barrier is the summary.
        expect(screen.getByTestId('forgot-commands-toggle'), 'the panel’s summary, on view').toBeVisible();
        expect(commandsPanel()).toContainElement(commands());
        expect(commands(), 'in the panel, hidden while it is closed').not.toBeVisible();
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
        expect(emailForm()).toBeNull();

        answer.resolve(WITH_LINKS);

        await waitFor(() => expect(emailForm()).not.toBeNull());
        expect(warning()).toBeNull();
        expect(commandsPanel(), 'the command box follows the form, into its panel').toContainElement(commands());
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

describe('ForgotPasswordCard — the panel of server commands', () => {
    it('FCE-07: email.links true — a click on the panel’s summary opens it and shows the command box, still open once the card has heard toggle', async () => {
        await answered(WITH_LINKS);
        mount();
        const panel = screen.getByTestId('forgot-commands-panel');
        expect(panel, 'premise: closed by default').not.toHaveAttribute('open');
        expect(commands(), 'premise: the box hidden while the panel is closed').not.toBeVisible();
        const toggles = vi.fn();
        panel.addEventListener('toggle', toggles);

        // Opened by a click, as the user opens it: no `open` set by hand, no `toggle` dispatched by the test. jsdom 30 gives
        // <summary> its activation behaviour, so a click on the first <summary> of a <details> adds or removes `open` there
        // and then (`HTMLElement-impl.js`), and the <details> fires `toggle` — what `bind:open` listens to — one task later
        // (`HTMLDetailsElement-impl.js`, a `setTimeout` of 0).
        await fireEvent.click(screen.getByTestId('forgot-commands-toggle'));
        expect(panel, 'the click opened it').toHaveAttribute('open');

        await waitFor(() => expect(toggles, 'the toggle that follows the click').toHaveBeenCalledTimes(1));
        expect(panel, 'still open once the card has heard toggle').toHaveAttribute('open');
        expect(commands(), 'the commands, on view').toBeVisible();
    });
});
