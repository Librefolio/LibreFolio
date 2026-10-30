// @vitest-environment jsdom
/**
 * CheckHelp — «guide or support» next to a check (FB-27): who can solve it decides what the user is offered.
 *
 * `checkGuides.json` says, per check id, whether the administrator solves it alone (`guide`: the MkDocs section) or whoever
 * hosts the instance does (`support`). The component `CheckHelp` renders the matching control; Settings › Security uses it
 * for each finding and each passed check (its own cases are in `SecurityTab.test.ts`), and this file pins the component.
 *
 * The contract under test — props `{checkId: string; severity: 'error' | 'warning' | 'info'; passed?: boolean;
 * supportUrl?: string | null}`, `supportUrl` defaulting to `instanceConfig.config.support_url` when that is a string:
 *   - an id with a `guide` entry → the existing `DocsLink` «Guide» button (`security-guide`, opens `/mkdocs/<lang>/<path>` in
 *     a new tab), passed or not; no support control;
 *   - an id with a `support` entry, not passed: with a usable address (`supportChannel(supportUrl, {githubFallback: false})`)
 *     an `<a data-testid="check-support">` named by `settings.securityTab.support`, whose href is
 *     `reportHref(channel, buildCheckReport({checkId, severity, instanceAddress: window.location.origin, appVersion:
 *     APP_VERSION, date: new Date()}))` — `mailto:` with subject and body for a mail address, the page with `title` and `body`
 *     in its query for a page; `target="_blank" rel="noopener noreferrer"` for a page only. Without a usable address NO link:
 *     a `<span data-testid="check-support-missing">` named by `settings.securityTab.supportMissing`, and never a GitHub
 *     fallback;
 *   - an id with a `support` entry and `passed`, or an unknown id → nothing at all;
 *   - the report is only in the href: never in the text, a title or a label.
 * The table is iterated (`checkGuides.json`), so a new check without a decision fails here.
 *
 * Labels: `$lib/i18n` is the real module with a marking translator (`[en] <key>`), as in `SecurityTab.test.ts`; nothing reads a
 * sentence of a catalogue. The date is frozen (only `Date` is faked) so the href can be compared whole against the one the
 * contract builds. `$lib/api` is an inert spy: the instance configuration store (the default address) loads an injected
 * answer, never the network.
 *
 * Red until FB-27: `CheckHelp.svelte`, `checkSupportReport.ts`, `supportChannel.ts` and `CHECK_HELP` do not exist (the file
 * fails to import). Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, within} from '$test/component';
import guides from '$lib/features/instance/checkGuides.json';
import * as checkGuides from '$lib/features/instance/checkGuides';
import {DEFAULT_INSTANCE_CONFIG, instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {buildCheckReport} from '$lib/features/instance/checkSupportReport';
import {reportHref, supportChannel} from '$lib/features/support/supportChannel';
import {currentLanguage} from '$lib/stores/app/language';
import {APP_VERSION} from '$lib/version';
import CheckHelp from './CheckHelp.svelte';

const fake = vi.hoisted(() => ({
    /** `[en] <key>`: the key the component chose, for both call shapes of `$_`. */
    translate(input: unknown, options?: {values?: Record<string, unknown>}): string {
        const asObject = typeof input === 'object' && input !== null ? (input as {id?: unknown}) : null;
        const key = asObject ? String(asObject.id ?? '') : String(input);
        void options;
        return `[en] ${key}`;
    },
}));

vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    const {readable} = await import('svelte/store');
    const marking = readable(fake.translate);
    return {...actual, _: marking, t: marking};
});

// `$lib/api`: every operation an inert spy pending forever (the instance configuration store imports the client).
vi.mock('$lib/api', () => {
    const inert = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (!inert.has(operation))
                    inert.set(
                        operation,
                        vi.fn(() => new Promise(() => {})),
                    );
                return inert.get(operation);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

type Severity = 'error' | 'warning' | 'info';
type Help = {kind: 'guide'; path: string} | {kind: 'support'};

const SUPPORT_KEY = 'settings.securityTab.support';
const MISSING_KEY = 'settings.securityTab.supportMissing';
const GUIDE_KEY = 'settings.securityTab.guide';

const MAILTO = 'mailto:help@example.org';
/** A different, usable address the store holds in the cases about the prop: a link to it means the prop was ignored. */
const STORE_MAILTO = 'mailto:store-support@example.org';
const FROZEN = new Date('2026-10-28T09:30:15.250Z');

/** Every id of the table, read from the JSON as the tab's cases do: the ids exist before the module does. */
const TABLE_IDS = [...Object.keys(guides.server), ...Object.keys(guides.browser)];
const SUPPORT_IDS = ['platform.hosting_panel', 'backup.panel_token', 'accounts.owner_email_change'];
const GUIDE_ID = 'platform.log_level';

const SEVERITIES: readonly Severity[] = ['error', 'warning', 'info'];

/** The href the contract builds for a support check, from the channel of `address`. */
function expectedHref(address: string | null, checkId: string, severity: Severity): string {
    const channel = supportChannel(address, {githubFallback: false});
    if (channel === null) throw new Error(`premise: ${address} is not a usable support address`);
    return reportHref(channel, buildCheckReport({checkId, severity, instanceAddress: window.location.origin, appVersion: APP_VERSION, date: new Date(FROZEN)}));
}

/** A pattern matching `text` anywhere: for an accessible name that may carry an icon's text beside it. */
function containing(text: string): RegExp {
    return new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
}

type Props = {checkId: string; severity: Severity; passed?: boolean; supportUrl?: string | null};

function mount(props: Props) {
    return render(CheckHelp, {props});
}

/** Every text a person can read in the mounted tree: its text and the `title`, `aria-label` and `alt` attributes (the data-* the component publishes are states, not text). */
function visibleText(container: HTMLElement): string {
    const attributes = [container, ...container.querySelectorAll('*')].flatMap((element) => [...element.attributes].filter((attribute) => ['title', 'aria-label', 'alt'].includes(attribute.name)).map((attribute) => attribute.value));
    return [container.textContent ?? '', ...attributes].join('\n');
}

async function useStoreSupportUrl(value: unknown): Promise<void> {
    await instanceConfig.load({force: true, fetchConfig: async () => ({...DEFAULT_INSTANCE_CONFIG, support_url: value as string | null})});
}

beforeEach(async () => {
    currentLanguage.set('en');
    vi.useFakeTimers({toFake: ['Date']});
    vi.setSystemTime(FROZEN);
    await useStoreSupportUrl(STORE_MAILTO);
});

afterEach(async () => {
    cleanup();
    vi.useRealTimers();
    // The store's defaults again (no support address) for whatever runs next
    await instanceConfig.load({force: true, fetchConfig: async () => DEFAULT_INSTANCE_CONFIG});
});

describe('CheckHelp — the table decides', () => {
    it('Barrier: the table has the three support checks and guide checks, and the module exposes CHECK_HELP for exactly its ids', () => {
        const help = (checkGuides as unknown as {CHECK_HELP?: Record<string, Help>}).CHECK_HELP;
        expect(help, 'checkGuides.ts exports CHECK_HELP (red until FB-27)').toBeDefined();
        expect(Object.keys(help ?? {}).sort()).toEqual([...TABLE_IDS].sort());
        expect(
            Object.entries(help ?? {})
                .filter(([, entry]) => entry.kind === 'support')
                .map(([id]) => id)
                .sort(),
        ).toEqual([...SUPPORT_IDS].sort());
        expect(TABLE_IDS.length - SUPPORT_IDS.length, 'the rest are guides').toBeGreaterThan(0);
    });

    it.each(TABLE_IDS.map((id) => [id]))('%s: with a mailto address, a guide check shows the guide button and a support check shows the support link — one of the two, never both', (checkId) => {
        const help = (checkGuides as unknown as {CHECK_HELP?: Record<string, Help>}).CHECK_HELP;
        expect(help, 'checkGuides.ts exports CHECK_HELP (red until FB-27)').toBeDefined();
        const entry = help![checkId];
        expect(entry, `${checkId} has a decision in CHECK_HELP: guide or support`).toBeDefined();

        const {container} = mount({checkId, severity: 'warning', supportUrl: MAILTO});

        if (entry.kind === 'guide') {
            const guide = within(container).getByTestId('security-guide');
            expect(guide.tagName).toBe('BUTTON');
            expect(guide).toHaveAccessibleName(containing(`[en] ${GUIDE_KEY}`));
            expect(within(container).queryByTestId('check-support'), `${checkId} is a guide: no support link`).toBeNull();
            expect(within(container).queryByTestId('check-support-missing')).toBeNull();
        } else {
            const link = within(container).getByTestId('check-support');
            expect(link.tagName).toBe('A');
            expect(link.getAttribute('href')).toBe(expectedHref(MAILTO, checkId, 'warning'));
            expect(within(container).queryByTestId('security-guide'), `${checkId} is support: no guide button`).toBeNull();
        }
    });
});

describe('CheckHelp — a guide check', () => {
    it.each([false, true])('shows the «Guide» button that opens its page and anchor in a new tab, passed: %s', async (passed) => {
        const {container} = mount({checkId: GUIDE_ID, severity: 'info', passed, supportUrl: MAILTO});
        const guide = within(container).getByTestId('security-guide');
        const open = vi.spyOn(window, 'open').mockImplementation(() => null);
        try {
            await fireEvent.click(guide);

            expect(open.mock.calls[0]).toEqual(['/mkdocs/admin/configuration_security/#startup-checks', '_blank', 'noopener']);
        } finally {
            open.mockRestore();
        }
        expect(within(container).queryByTestId('check-support')).toBeNull();
        expect(within(container).queryByTestId('check-support-missing')).toBeNull();
    });

    it('shows the guide button without any support address, and does not ask for one', () => {
        const {container} = mount({checkId: GUIDE_ID, severity: 'warning', supportUrl: null});

        expect(within(container).getByTestId('security-guide')).toBeInTheDocument();
        expect(within(container).queryByTestId('check-support-missing'), 'a guide check never says support is missing').toBeNull();
    });
});

describe('CheckHelp — a support check with an address', () => {
    it.each(SUPPORT_IDS.flatMap((id) => SEVERITIES.map((severity) => [id, severity] as const)))('%s, %s: a link named by the support key, to the mailto with the report', (checkId, severity) => {
        const {container} = mount({checkId, severity, supportUrl: MAILTO});

        const link = within(container).getByTestId('check-support');
        expect(link.tagName).toBe('A');
        expect(link).toHaveAccessibleName(containing(`[en] ${SUPPORT_KEY}`));
        const href = link.getAttribute('href') ?? '';
        expect(href, 'a mailto with the instance’s address').toMatch(/^mailto:help@example\.org\?subject=/);
        expect(href).toBe(expectedHref(MAILTO, checkId, severity));
        // The report is the one of this check, with this severity, written by the contract’s builder
        const parts = /^mailto:help@example\.org\?subject=([^&]*)&body=([^&]*)$/.exec(href);
        expect(parts, `not mailto:<address>?subject=…&body=…: ${href}`).not.toBeNull();
        expect(decodeURIComponent(parts![1])).toContain(checkId);
        const lines = decodeURIComponent(parts![2]).split(/\r\n/);
        expect(lines).toContain(`Check: ${checkId}`);
        expect(lines).toContain(`Severity: ${severity}`);
        expect(lines).toContain(`Instance: ${window.location.origin}`);
        expect(lines).toContain(`LibreFolio ${APP_VERSION}`);
        expect(lines).toContain(`Date: ${FROZEN.toISOString()}`);
    });

    it('a mailto opens in this tab: no target, no rel', () => {
        const {container} = mount({checkId: 'platform.hosting_panel', severity: 'warning', supportUrl: MAILTO});

        const link = within(container).getByTestId('check-support');
        expect(link).not.toHaveAttribute('target');
        expect(link).not.toHaveAttribute('rel');
    });

    it('a support page opens with the report as title and body, in a new tab, without a window.opener nor a referrer', () => {
        const page = 'https://help.example.org/support?lang=it';
        const {container} = mount({checkId: 'backup.panel_token', severity: 'error', supportUrl: page});

        const link = within(container).getByTestId('check-support');
        const href = link.getAttribute('href') ?? '';
        expect(href).toBe(expectedHref(page, 'backup.panel_token', 'error'));
        const url = new URL(href);
        expect(`${url.origin}${url.pathname}`).toBe('https://help.example.org/support');
        expect([...url.searchParams.keys()], 'the page’s own params, then title and body').toEqual(['lang', 'title', 'body']);
        expect(url.searchParams.get('title')).toContain('backup.panel_token');
        expect(url.searchParams.get('body')?.split('\n')).toContain('Check: backup.panel_token');
        expect(link).toHaveAttribute('target', '_blank');
        const rel = (link.getAttribute('rel') ?? '').split(/\s+/);
        expect(rel).toContain('noopener');
        expect(rel).toContain('noreferrer');
    });

    it('the prop wins over the store: the address of the prop, not the one the instance configuration holds', () => {
        const {container} = mount({checkId: 'platform.hosting_panel', severity: 'warning', supportUrl: MAILTO});

        const href = within(container).getByTestId('check-support').getAttribute('href') ?? '';
        expect(href.startsWith('mailto:help@example.org?')).toBe(true);
        expect(href).not.toContain('store-support');
    });

    it('without the prop, reads the instance configuration’s support address (GET /system/instance)', async () => {
        await useStoreSupportUrl('https://help.example.org/librefolio');
        const {container} = mount({checkId: 'platform.hosting_panel', severity: 'warning'});

        const link = within(container).getByTestId('check-support');
        expect(link.getAttribute('href')).toBe(expectedHref('https://help.example.org/librefolio', 'platform.hosting_panel', 'warning'));
        expect(link).toHaveAttribute('target', '_blank');
    });

    it('the report is only in the href: never in the text, a title or a label', () => {
        const {container} = mount({checkId: 'accounts.owner_email_change', severity: 'warning', supportUrl: MAILTO});
        // Presence barrier: the link is there, so the absences below are not "nothing rendered yet"
        expect(within(container).getByTestId('check-support')).toBeInTheDocument();

        const shown = visibleText(container);
        for (const piece of ['Check:', 'Severity:', 'Instance:', 'Date:', FROZEN.toISOString(), 'accounts.owner_email_change']) {
            expect(shown, `«${piece}» belongs to the report, which is only in the href`).not.toContain(piece);
        }
    });
});

describe('CheckHelp — a support check without a usable address', () => {
    const UNUSABLE: ReadonlyArray<readonly [string, string | null]> = [
        ['null', null],
        ['empty', ''],
        ['blank', '   '],
        ['a javascript: URL', 'javascript:alert(1)'],
        ['a mailto with two addresses', 'mailto:help@example.org,other@example.org'],
        ['a page with a password', 'https://user:pass@help.example.org/'],
    ];

    it.each(UNUSABLE)('%s: no link at all, the missing note instead — and no GitHub fallback', (_label, value) => {
        expect(supportChannel(value, {githubFallback: false}), 'premise: the app finds no usable address').toBeNull();
        expect(supportChannel(value, {githubFallback: true})?.kind, 'premise: a GitHub fallback would exist, so its absence means something').toBe('github');

        const {container} = mount({checkId: 'platform.hosting_panel', severity: 'warning', supportUrl: value});

        const missing = within(container).getByTestId('check-support-missing');
        expect(missing.tagName, 'a note, not a link').toBe('SPAN');
        expect(missing).toHaveTextContent(`[en] ${MISSING_KEY}`);
        expect(within(container).queryByTestId('check-support')).toBeNull();
        expect(container.querySelectorAll('a'), 'no link of any kind').toHaveLength(0);
        expect(container.innerHTML, 'no GitHub fallback, ever').not.toContain('github.com');
        expect(within(container).queryByTestId('security-guide')).toBeNull();
    });

    it('the instance configuration holding no address (the default) says the same', async () => {
        await useStoreSupportUrl(null);
        const {container} = mount({checkId: 'backup.panel_token', severity: 'error'});

        expect(within(container).getByTestId('check-support-missing')).toBeInTheDocument();
        expect(container.querySelectorAll('a')).toHaveLength(0);
    });

    it('an address of the configuration that is not a string (the generator’s array quirk) counts as none', async () => {
        await useStoreSupportUrl(['mailto:help@example.org']);
        const {container} = mount({checkId: 'backup.panel_token', severity: 'error'});

        expect(within(container).getByTestId('check-support-missing')).toBeInTheDocument();
        expect(container.querySelectorAll('a')).toHaveLength(0);
    });
});

describe('CheckHelp — nothing to offer', () => {
    it.each(SUPPORT_IDS)('%s passed: nothing at all, with an address or without', (checkId) => {
        for (const supportUrl of [MAILTO, null]) {
            const {container} = mount({checkId, severity: 'info', passed: true, supportUrl});

            expect(container.querySelectorAll('[data-testid]'), `${checkId} passed, support ${supportUrl}: no control`).toHaveLength(0);
            expect(container.textContent?.trim(), 'no text either').toBe('');
            expect(container.querySelectorAll('a, button')).toHaveLength(0);
            cleanup();
        }
    });

    it.each(['plugin.future_check', 'constructor', '__proto__', 'toString'])('an id the table does not know (%s): nothing at all', (checkId) => {
        for (const passed of [false, true]) {
            const {container} = mount({checkId, severity: 'warning', passed, supportUrl: MAILTO});

            expect(container.querySelectorAll('[data-testid]')).toHaveLength(0);
            expect(container.querySelectorAll('a, button')).toHaveLength(0);
            expect(container.textContent?.trim()).toBe('');
            cleanup();
        }
    });
});

describe('CheckHelp — the screen', () => {
    it('shows one control at a time: the guide button or the support link, never two', () => {
        const {container} = mount({checkId: 'platform.hosting_panel', severity: 'warning', supportUrl: MAILTO});

        expect(within(container).getAllByTestId('check-support')).toHaveLength(1);
        expect(screen.queryAllByTestId('security-guide')).toHaveLength(0);
    });
});
