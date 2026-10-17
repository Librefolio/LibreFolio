// @vitest-environment jsdom
/**
 * ForgotPasswordCard on a managed instance (F05, lot A9 of workstream A): the «forgot password» card shows the server's
 * docker and CLI commands (`forgot-reset-commands`: `docker compose exec … dev.py user reset`, `./dev.py user reset`)
 * only once the configuration is loaded and self-hosted. On a managed instance nobody who reads the card runs the
 * server: in place of the commands, an element `forgot-ask-admin` saying the key `auth.askAdminToResetPassword`. Before
 * the answer, neither: no flash of commands on a managed instance while its `GET /system/instance` is in flight. E's
 * email form (`forgot-email-form`, when `email.links`) does not depend on the profile.
 *
 * The contract under test:
 *   - FPM-01 (positive control, green today): self-hosted, no email links — the commands, under their heading; no
 *     `forgot-ask-admin`. It also proves the text scans below can see a command and the heading;
 *   - FPM-02: managed, no email links — `forgot-ask-admin` on view with its key; no command box, no docker or CLI
 *     command anywhere in the card, and no «run this command on the server» heading over nothing (my reading of
 *     «no docker/CLI hints»: the heading introduces the commands and goes with them);
 *   - FPM-03: before the answer — neither the commands nor `forgot-ask-admin`, no command anywhere, no heading;
 *   - FPM-04: managed with email links — E's form, unchanged; `forgot-ask-admin` in place of the closed panel of
 *     commands (in the document: whether on view or folded is not part of the contract); no command, no heading;
 *   - FPM-05 (positive control, green today): self-hosted with email links — E's form and the panel of commands, as
 *     today (`ForgotPasswordCard.email.test.ts` owns the rest of that branch);
 *   - FPM-06/07: drawn before the answer, the card — a legacy component — follows it in place: `forgot-ask-admin`
 *     appears once the answer says managed, the commands once it says self-hosted, never before.
 * And the key itself (CAT-01/02): `auth.askAdminToResetPassword` is a sentence in the four generated catalogues
 * (`src/lib/i18n/{en,it,fr,es}.json`), and names no docker or CLI command.
 *
 * Mocks, all owned here: `$lib/features/instance/instanceConfig.svelte` is a fake with the real store's shape —
 * enumerable getters over a `$state` box (`reactiveBox`) — so a test lands the server's answer by writing the box, as
 * `load()` does; `load` (the card calls it on mount) is a spy answering nothing of its own. `$lib/i18n`: `_` marks
 * each key (`⟦key⟧`), so the card's text names keys, never a language's prose. `notify` is a spy. The form is E's real
 * `ForgotPasswordEmailForm`.
 *
 * The component is loaded once, in a guarded `beforeAll` with its own budget: its first transform pulls the
 * `lucide-svelte` barrel, which is cold and slow under load (the pattern of `GapFixStep.test.ts`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import type ForgotPasswordCardComponent from './ForgotPasswordCard.svelte';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, render, screen} from '$test/component';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    /** What the real store holds until the server answers: `DEFAULT_INSTANCE_CONFIG`, a self-hosted instance. */
    const BEFORE_ANSWER = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as InstanceConfig;
    return {
        BEFORE_ANSWER,
        instance: reactiveBox<{config: InstanceConfig; loaded: boolean; failed: boolean}>({config: BEFORE_ANSWER, loaded: false, failed: false}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
        notify: vi.fn().mockName('notify'),
    };
});

vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: mocks.BEFORE_ANSWER,
    fetchInstanceConfigFromApi: () => Promise.reject(new Error('no network in this test')),
    instanceConfig: {
        get config() {
            return mocks.instance.config;
        },
        get loaded() {
            return mocks.instance.loaded;
        },
        get failed() {
            return mocks.instance.failed;
        },
        load: mocks.instanceLoad,
    },
}));

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: mocks.notify}));

// Keys, not prose: the card renders `⟦key⟧`, the same in every language.
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const marked = readable((key: string) => `⟦${key}⟧`);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: marked, t: marked};
});

/** The key `forgot-ask-admin` says (the coordinator's contract, 17/10): one place to change if it is renamed. */
const ASK_ADMIN_KEY = 'auth.askAdminToResetPassword';
/** The heading over the commands («Run this command on the server:»). */
const TERMINAL_HEADING_KEY = 'auth.serverTerminalInstructions';
/** The commands of the box, as literal text: neither is translated. */
const COMMAND_TOKENS = [/docker/i, /dev\.py/i];

const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {...SELFHOSTED, profile: 'managed'};
const WITH_LINKS = {available: true, links: true};

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

const COMPONENT_MODULES = import.meta.glob<{default: typeof ForgotPasswordCardComponent}>('./ForgotPasswordCard.svelte');

/** What the loading hook found: the component, or why it could not be loaded. */
let loaded: {ForgotPasswordCard: typeof ForgotPasswordCardComponent} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = COMPONENT_MODULES['./ForgotPasswordCard.svelte'];
        if (!load) throw new Error('ForgotPasswordCard.svelte cannot be found next to this test');
        loaded = {ForgotPasswordCard: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 120_000);

function component(): typeof ForgotPasswordCardComponent {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.ForgotPasswordCard;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** The server's answer lands, as `instanceConfig.load()` lands it. */
async function serverAnswers(config: InstanceConfig): Promise<void> {
    mocks.instance.config = config;
    mocks.instance.loaded = true;
    mocks.instance.failed = false;
    flushSync();
    await tick();
}

/** Draws the card; ends on it drawn, its «back to login» on view — the barrier of every absence below. */
async function mount(): Promise<void> {
    render(component(), {props: {}});
    await tick();
    expect(screen.getByTestId('forgot-modal'), 'premise: the card is drawn').toBeInTheDocument();
    expect(screen.getByTestId('forgot-back-to-login'), 'premise: a sibling control is on view').toBeVisible();
}

function cardText(): string {
    return screen.getByTestId('forgot-modal').textContent ?? '';
}

const commands = () => screen.queryByTestId('forgot-reset-commands');
const askAdmin = () => screen.queryByTestId('forgot-ask-admin');

/** No command box, no docker or CLI command anywhere in the card, no heading announcing one. */
function expectNoServerHint(): void {
    expect(commands(), 'no forgot-reset-commands').toBeNull();
    const text = cardText();
    for (const token of COMMAND_TOKENS) expect(text, `no ${token} anywhere in the card`).not.toMatch(token);
    expect(text, 'no «run this command on the server» heading over nothing').not.toContain(`⟦${TERMINAL_HEADING_KEY}⟧`);
}

beforeEach(() => {
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instance.failed = false;
    flushSync();
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockImplementation(() => Promise.resolve());
    mocks.notify.mockReset();
});

afterEach(() => {
    cleanup();
});

describe('ForgotPasswordCard — the server commands only on a self-hosted instance that has answered (F05)', () => {
    it('FPM-01: answered self-hosted, no email links — the command box under its heading; no forgot-ask-admin (positive control)', async () => {
        await serverAnswers(SELFHOSTED);

        await mount();

        expect(commands()).toBeVisible();
        for (const token of COMMAND_TOKENS) expect(cardText(), `the scan sees ${token}`).toMatch(token);
        expect(cardText(), 'the scan sees the heading').toContain(`⟦${TERMINAL_HEADING_KEY}⟧`);
        expect(askAdmin()).toBeNull();
    });

    // red until A9
    it('FPM-02: answered managed, no email links — forgot-ask-admin on view, saying its key; no command, no heading', async () => {
        await serverAnswers(MANAGED);

        await mount();

        expectNoServerHint();
        expect(askAdmin(), 'forgot-ask-admin in place of the commands').toBeVisible();
        expect(askAdmin()).toHaveTextContent(`⟦${ASK_ADMIN_KEY}⟧`);
    });

    // red until A9
    it('FPM-03: before the answer — neither the commands nor forgot-ask-admin; no command, no heading', async () => {
        await mount();

        expectNoServerHint();
        expect(askAdmin(), 'nothing to say yet: the profile is unknown').toBeNull();
    });
});

describe('ForgotPasswordCard — E’s email form does not depend on the profile', () => {
    // red until A9
    it('FPM-04: answered managed with email links — E’s form, unchanged; forgot-ask-admin in place of the panel of commands; no command, no heading', async () => {
        await serverAnswers({...MANAGED, email: WITH_LINKS});

        await mount();

        expect(screen.getByTestId('forgot-email-form'), 'E’s form, as on a self-hosted instance').toBeInTheDocument();
        expect(screen.getByTestId('forgot-email-identifier')).toBeEnabled();
        expectNoServerHint();
        expect(askAdmin(), 'forgot-ask-admin in place of the commands').toBeInTheDocument();
        expect(askAdmin()).toHaveTextContent(`⟦${ASK_ADMIN_KEY}⟧`);
    });

    it('FPM-05: answered self-hosted with email links — E’s form and the panel of commands, as today (positive control)', async () => {
        await serverAnswers({...SELFHOSTED, email: WITH_LINKS});

        await mount();

        expect(screen.getByTestId('forgot-email-form')).toBeInTheDocument();
        expect(screen.getByTestId('forgot-email-identifier')).toBeEnabled();
        expect(screen.getByTestId('forgot-commands-panel')).toContainElement(commands());
        expect(askAdmin()).toBeNull();
    });
});

describe('ForgotPasswordCard — drawn before the answer, it follows it in place', () => {
    // red until A9
    it('FPM-06: forgot-ask-admin appears once the answer says managed; no command before, none after', async () => {
        await mount();
        expectNoServerHint();
        expect(askAdmin()).toBeNull();

        await serverAnswers(MANAGED);

        expect(askAdmin(), 'the answer said managed').toBeVisible();
        expect(askAdmin()).toHaveTextContent(`⟦${ASK_ADMIN_KEY}⟧`);
        expectNoServerHint();
    });

    // red until A9
    it('FPM-07: the commands appear once the answer says self-hosted, not before', async () => {
        await mount();
        expectNoServerHint();

        await serverAnswers(SELFHOSTED);

        expect(commands(), 'the answer said self-hosted').toBeVisible();
        expect(askAdmin()).toBeNull();
    });
});

// --- The key ---------------------------------------------------------------------------------------------------------

describe('the key of forgot-ask-admin — a sentence in the four generated catalogues', () => {
    const CATALOGUES: Record<'en' | 'it' | 'fr' | 'es', unknown> = {en, it: itCatalogue, fr, es};

    /** The leaf behind a dotted key, read from the catalogue file itself (the generated catalogues are nested). */
    function leaf(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    // red until A9
    it(`CAT-01: ${ASK_ADMIN_KEY} is a sentence in en, it, fr and es`, () => {
        const missing = Object.entries(CATALOGUES)
            .filter(([, catalogue]) => {
                const sentence = leaf(catalogue, ASK_ADMIN_KEY);
                return typeof sentence !== 'string' || sentence.trim() === '';
            })
            .map(([language]) => language);

        expect(missing, `${ASK_ADMIN_KEY} is drawn as the key itself in a catalogue that lacks it`).toEqual([]);
    });

    // red until A9
    it(`CAT-02: ${ASK_ADMIN_KEY} names no docker or CLI command, in any language`, () => {
        const offenders = Object.entries(CATALOGUES).flatMap(([language, catalogue]) => {
            const sentence = leaf(catalogue, ASK_ADMIN_KEY);
            if (typeof sentence !== 'string') return [`${language}: missing`];
            return COMMAND_TOKENS.filter((token) => token.test(sentence)).map((token) => `${language}: ${token}`);
        });

        expect(offenders, 'the sentence of a managed instance sends the user to the administrator, not to a terminal').toEqual([]);
    });
});
