// @vitest-environment node
/**
 * checkGuides — the guide of each finding in Settings › Security (lot N69d of A, «the guide of each check»; the map is
 * workstream H's: contract §1 and §2, 20/10).
 *
 * The Security tab lists the server's checks (`GET /security/checks`) and the findings only the browser knows. Its
 * «Guide» button (N69d) opens the section of the administrator's documentation that explains a finding. This file pins
 * the map the button reads: one guide per finding, and every guide a section the documentation really has.
 *
 * The contract under test:
 *   - `checkGuides.json`, next to this file, new: `{"server": {<check id>: <guide>}, "browser": {<finding id>:
 *     <guide>}}`. `server`: every check of `GET /security/checks`, the ids of `run_config_checks()` then
 *     `platform.plugin_secrets`, then (H5-7) `platform.instance_key_check`; `browser`: the findings the browser adds, today `OPEN_REGISTRATION_NOTICE_ID` and, since
 *     H-55 v2, `platform.blockedScript`.
 *   - `checkGuides.ts`, next to it, new: `CHECK_GUIDES`, the two halves merged and frozen; `checkGuidePath(checkId)`,
 *     the guide of an own key only (`Object.hasOwn`), so `undefined` for an unknown id and for `constructor`,
 *     `__proto__`, `toString` and `hasOwnProperty`.
 *   - A guide is `admin/<page>/#<anchor>`, matching `^admin/[a-z0-9_]+/#[a-z0-9-]+$`: no language prefix (`DocsLink`
 *     adds it), no leading `/`, no `.md`, a folder URL, an explicit anchor. The 23 guides are `EXPECTED_GUIDES` below.
 *
 * The cases: §2's five — the shape, the anchors exist, the lookup, the browser half, the translation ratchet — and §1's
 * table pinned whole, so that a changed guide is a visible change of this file.
 *
 * How. The module is loaded by a computed specifier and the JSON read from disk, so while they are missing each case
 * fails on its own, naming them. The pages are read with `node:fs` from `mkdocs_src/docs/admin/`, resolved from this
 * file. An anchor is the explicit attribute `{: #<anchor> }`, written exactly so and counted as text: a link to it,
 * `(#<anchor>)`, is not it, nor a longer anchor that starts with it. The two docs cases check the table's guides with
 * the module's: the documentation is checked already, while the module is missing.
 *
 * Controls. «Exactly once» and «missing» are only as true as the reader. Before relying on it, each docs case proves on
 * the real pages that it finds `{: #session-cookie }` once in `connection_checks`, which writes it in the four
 * languages — a reader that finds nothing fails there —, and that it reports an invented anchor missing — so does a
 * reader that finds everything; on a sample page, that a link and a longer anchor are not counted and a repeated anchor
 * counts twice. Each docs case then runs the same two sections through its own check. The shape is first shown refusing
 * a path of each wrong kind; the lookup answers every key before its `undefined`s are read.
 *
 * The ratchet. For each distinct `<page>#<anchor>` and each of it, fr and es whose `<page>.<lang>.md` exists, the pair
 * `<lang>:<page>#<anchor>` is missing when that page does not write `{: #<anchor> }`. The pairs missing must be exactly
 * `TRANSLATION_DEBT`. `email` and `hosting_providers` have no translation: the docs publish their English page in every
 * language (`fallback_to_default`), so they count for nothing.
 *
 * Not pinned: the order of the keys (§3 reads the server half against the checks themselves); the JSON's Prettier form
 * (the format check covers it); the module's TypeScript types (a local interface types the calls here, so `front check`
 * does not wait for the module); a translation that writes an anchor twice (the ratchet asks only whether it is
 * missing); the module's comment.
 *
 * Red today: `checkGuides.ts` and `checkGuides.json` do not exist, and each case fails on its own, naming them. The
 * anchors case also names `frame-protection` and `csp-report-only` for as long as `configuration.en.md` lacks them (the
 * docs step of the lot, §4). Its place in the runner: `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`,
 * action `core-unit`).
 *
 * H-61 (checkpoint 1, contract §5, 20/10): the new startup check of the hosting panel's tokens, `platform.hosting_panel`,
 * has its guide, `admin/hosting_panel_api/#panel-api`, in the table between `platform.log_level` and `platform.test_mode`,
 * its place among the checks. Red until `checkGuides.json` holds it (§1 pinned whole) and `hosting_providers.en.md`
 * writes `{: #panel-api }` (§2.2, the docs step of the lot). `hosting_providers` has no translation, so the ratchet does
 * not move.
 *
 * H5-4 (24/10, A's request A5-1b): the new check `accounts.owner_email_change` (the host changed the owner's email address:
 * pending its confirmation, or blocked by another account) has its guide, `admin/hosting_instances/#owner-email-change`, in
 * the table right after `accounts.login_limit`, its place among the checks. Red until `checkGuides.json` holds it (§1 pinned
 * whole). The anchor already exists in `hosting_providers.en.md` (§2.2 stays green). `hosting_providers` has no translation
 * (the docs publish its English page in every language), so, as for `#panel-api`, the pair joins no ratchet and
 * `TRANSLATION_DEBT` does not move: it would be reported as new the day a translation of the page appears without the anchor.
 *
 * H-55 v2 (step 4, 21/10): the browser's second finding, `platform.blockedScript` — a script the enforced
 * Content-Security-Policy blocked and this instance did not send —, has its guide, `admin/configuration_security/#csp` (`admin/configuration/#csp` until DOC-1 moved it), in the
 * browser half. Red until `checkGuides.json` holds it (§1 pinned whole, §2.4 the browser half), `securityFindings` adds the
 * finding (§2.4's premise, fed `blockedScripts`) and, as the contract says, until `configuration.en.md` writes
 * `{: #csp }` (§2.2, the docs step of the lot): THAT anchor check stays red until the documentation lands. The it, fr and
 * es pages cannot have it yet: the three pairs are translation debt (§2.5), written with their reason below.
 *
 * FB-27 (the «guide or support» help of the checks): each entry says who can solve the check. Every value of `server` and
 * `browser` is now an object: `{"kind":"guide","path":"admin/<page>/#<anchor>"}` (the administrator solves it alone: the
 * MkDocs link) or `{"kind":"support"}` with no path (whoever hosts the instance solves it: «Contact support»). The three
 * `support` entries are `platform.hosting_panel`, `backup.panel_token` and `accounts.owner_email_change`; every other
 * check stays a `guide` with the path it had (`backup.upload_limit` and `backup.restore_limit` too: they also apply to a
 * self-hosted instance). The module exports `CHECK_HELP` (server and browser merged, frozen, id → entry), the type
 * `CheckHelp`, `checkHelp(checkId)` (own keys only) and keeps `CHECK_GUIDES` / `checkGuidePath` for the `guide` entries
 * ONLY (a support check has no path). The shape, anchors and translation-ratchet cases apply to the guide entries only; the
 * table is pinned whole (`EXPECTED_HELP`, kind per id). The removed guide pairs were in no translation debt, so
 * `TRANSLATION_DEBT` does not move. Red until FB-27: `checkGuides.json` still holds plain strings and the module has no
 * `CHECK_HELP` nor `checkHelp`.
 */
import {existsSync, readFileSync} from 'node:fs';
import {describe, expect, it, vi} from 'vitest';
import {OPEN_REGISTRATION_NOTICE_ID} from '$lib/features/auth/openRegistrationNotice.svelte';
import {securityFindings} from '$lib/features/settings/security/securityFindings';

// `$lib/api`: every operation an inert spy pending forever — nothing here may reach the network, nothing may settle
// behind the assertions. The module of `OPEN_REGISTRATION_NOTICE_ID` imports the auth store, which imports the client:
// the shape of `securityFindings.test.ts`.
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

// =============================================================================
//  §1: the map, pinned
// =============================================================================

/** What a check's help is: a guide of the administrator's documentation, or the instance's support. */
type Help = {kind: 'guide'; path: string} | {kind: 'support'};

/**
 * The 23 helps of §1, whole: check id → its help (20 guides, 3 support). A changed guide, or a check that changes who solves
 * it, is a change of this table. Written in the order of the checks (`CONFIG_CHECKS`, then `platform.plugin_secrets`, then
 * `platform.instance_key_check`), then the browser's finding, and compared as a record: the order is pinned by §3, against
 * the checks themselves.
 */
const EXPECTED_HELP: Readonly<Record<string, Help>> = {
    'platform.jwt_secret': {kind: 'guide', path: 'admin/configuration_secrets/#secrets'},
    'platform.secrets_set_twice': {kind: 'guide', path: 'admin/configuration_secrets/#secret-files'},
    'platform.instance_key': {kind: 'guide', path: 'admin/configuration_secrets/#instance-key'},
    'platform.session_cookie': {kind: 'guide', path: 'admin/connection_checks/#session-cookie'},
    'platform.client_address': {kind: 'guide', path: 'admin/connection_proxy/#untrusted-proxy'},
    'platform.frame_protection': {kind: 'guide', path: 'admin/configuration_security/#frame-protection'},
    'platform.csp_report_only': {kind: 'guide', path: 'admin/configuration_security/#csp-report-only'},
    'platform.log_level': {kind: 'guide', path: 'admin/configuration_security/#startup-checks'},
    // H-61: the hosting panel's wake-up and status tokens, right before the test mode check
    'platform.hosting_panel': {kind: 'support'},
    'platform.test_mode': {kind: 'guide', path: 'admin/configuration_security/#startup-checks'},
    'backup.panel_token': {kind: 'support'},
    'backup.upload_limit': {kind: 'guide', path: 'admin/configuration/#main-options'},
    'backup.restore_limit': {kind: 'guide', path: 'admin/cli_backup/#backup-restore-dry-run'},
    // L3 (B, 22/10): the recipients of the hosting panel's sealed backups.
    'backup.recipients': {kind: 'guide', path: 'admin/backup_sealed/#sealed'},
    'accounts.login_limit': {kind: 'guide', path: 'admin/configuration_accounts/#login-limit'},
    // H5-4 (A's request A5-1b): the host-started change of the owner's email, right after the login limit's
    'accounts.owner_email_change': {kind: 'support'},
    'email.smtp': {kind: 'guide', path: 'admin/email/#variables'},
    'email.smtp_encryption': {kind: 'guide', path: 'admin/email/#encryption-modes'},
    'email.links': {kind: 'guide', path: 'admin/email/#links-check'},
    'platform.plugin_secrets': {kind: 'guide', path: 'admin/configuration_secrets/#plugin-secrets'},
    // H5-7 (D6): the instance key check (the key does not match what the data were saved with), right after the plugin secrets'.
    // Not `platform.instance_key`: that id is the key file's own check, mapped above to `#instance-key` (ID COLLISION, see test_instance_key_check.py).
    'platform.instance_key_check': {kind: 'guide', path: 'admin/configuration_secrets/#instance-key-check'},
    // The browser's half: the open-registration warning, `OPEN_REGISTRATION_NOTICE_ID`
    'accounts.openRegistration': {kind: 'guide', path: 'admin/settings/#open-registration-warning'},
    // H-55 v2: a script the enforced policy blocked and this instance did not send (`cspNotice.ts`)
    'platform.blockedScript': {kind: 'guide', path: 'admin/configuration_security/#csp'},
};

/** The guide entries of `EXPECTED_HELP`, id → path: what `CHECK_GUIDES` holds. */
const EXPECTED_GUIDES: Readonly<Record<string, string>> = Object.fromEntries(Object.entries(EXPECTED_HELP).flatMap(([id, help]) => (help.kind === 'guide' ? [[id, help.path]] : [])));

/** The checks whose help is «Contact support», not a guide (FB-27). */
const SUPPORT_IDS: readonly string[] = ['platform.hosting_panel', 'backup.panel_token', 'accounts.owner_email_change'];

/** The findings the browser adds to the Security tab: the open-registration warning and, since H-55 v2, a blocked script. */
const BLOCKED_SCRIPT_ID = 'platform.blockedScript';
const BROWSER_FINDINGS: readonly string[] = [OPEN_REGISTRATION_NOTICE_ID, BLOCKED_SCRIPT_ID];

/**
 * The baseline of the translation ratchet: the `<lang>:<page>#<anchor>` pairs whose it, fr or es page does not write the
 * anchor yet, sorted. Empty since the translation of 1.3. It only shrinks: a pair the ratchet reports gone leaves it in the
 * same change, and a new pair comes in only with its reason written beside it.
 */
const TRANSLATION_DEBT: readonly string[] = [];

// =============================================================================
//  The module under test, and its data
// =============================================================================

/** `checkGuides.ts` as the cases call it: a local interface, so that `front check` does not wait for the module. */
interface CheckGuidesModule {
    CHECK_GUIDES: Readonly<Record<string, string>>;
    checkGuidePath(checkId: string): string | undefined;
    CHECK_HELP: Readonly<Record<string, Help>>;
    checkHelp(checkId: string): Help | undefined;
}

/** A computed specifier: Vite does not resolve it when it transforms this file, so while the module is missing each case fails on its own. */
const MODULE = './checkGuides';

/** The module, loaded by the running case. */
async function checkGuides(): Promise<CheckGuidesModule> {
    let loaded: Record<string, unknown>;
    try {
        loaded = (await import(/* @vite-ignore */ MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/features/instance/checkGuides.ts cannot be loaded (red until N69d §1: the map does not exist yet), so no finding of the Security tab has a guide — ${String(error)}`, {cause: error});
    }
    expect(typeof loaded.CHECK_GUIDES === 'object' && loaded.CHECK_GUIDES !== null, 'checkGuides.ts exports CHECK_GUIDES, an object').toBe(true);
    expect(typeof loaded.checkGuidePath, 'checkGuides.ts exports checkGuidePath()').toBe('function');
    return loaded as unknown as CheckGuidesModule;
}

/** FB-27: the module with its help half too (`CHECK_HELP`, `checkHelp`): the cases about who solves a check load it here. */
async function checkHelpModule(): Promise<CheckGuidesModule> {
    const loaded = await checkGuides();
    expect(typeof loaded.CHECK_HELP === 'object' && loaded.CHECK_HELP !== null, 'checkGuides.ts exports CHECK_HELP, an object (red until FB-27)').toBe(true);
    expect(typeof loaded.checkHelp, 'checkGuides.ts exports checkHelp() (red until FB-27)').toBe('function');
    return loaded;
}

/** The module's guides, or why it cannot give them: the two docs cases check the table's guides either way. */
async function moduleGuides(): Promise<{guides: string[]; problem: string | null}> {
    try {
        return {guides: Object.values((await checkGuides()).CHECK_GUIDES), problem: null};
    } catch (error) {
        return {guides: [], problem: error instanceof Error ? error.message : String(error)};
    }
}

/** The data, next to the module, read from disk as the backend test (§3) reads it. */
const GUIDES_JSON = new URL('./checkGuides.json', import.meta.url);

interface GuidesJson {
    server: Record<string, Help>;
    browser: Record<string, Help>;
}

/** FB-27's shape of one entry: `{kind: 'guide', path: <string>}` or `{kind: 'support'}` with no other key (no path). */
function isHelpEntry(value: unknown): value is Help {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
    const keys = Object.keys(value).sort();
    const entry = value as Record<string, unknown>;
    if (entry.kind === 'guide') return keys.join() === 'kind,path' && typeof entry.path === 'string';
    if (entry.kind === 'support') return keys.join() === 'kind';
    return false;
}

function isHelpRecord(value: unknown): value is Record<string, Help> {
    return typeof value === 'object' && value !== null && !Array.isArray(value) && Object.values(value).every(isHelpEntry);
}

/** `checkGuides.json`: one object, of exactly two halves, each an id → its help. */
function guidesJson(): GuidesJson {
    expect(existsSync(GUIDES_JSON), 'src/lib/features/instance/checkGuides.json does not exist (red until N69d §1: the map is not written yet)').toBe(true);
    const parsed: unknown = JSON.parse(readFileSync(GUIDES_JSON, 'utf8'));
    const halves = typeof parsed === 'object' && parsed !== null ? Object.keys(parsed).sort() : parsed;
    expect(halves, 'checkGuides.json is one object, of exactly two halves: server and browser').toEqual(['browser', 'server']);
    const {server, browser} = parsed as Record<string, unknown>;
    expect([isHelpRecord(server), isHelpRecord(browser)], 'checkGuides.json: server and browser each map an id to {kind: "guide", path} or {kind: "support"} — no plain string, no path on a support entry (red until FB-27)').toEqual([true, true]);
    return {server, browser} as GuidesJson;
}

// =============================================================================
//  The documentation, and its reader
// =============================================================================

/** `mkdocs_src/docs/admin/`, from this file: instance → features → lib → src → frontend → the repository. */
const DOCS_ADMIN = new URL('../../../../../mkdocs_src/docs/admin/', import.meta.url);

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];

/** The translations of a page, which the ratchet reads; English is the source. */
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];

/** §1's shape, `^admin/[a-z0-9_]+/#[a-z0-9-]+$`, with the page and the anchor captured. */
const GUIDE_SHAPE = /^admin\/([a-z0-9_]+)\/#([a-z0-9-]+)$/;

/** The section a guide opens: the page `<page>.<lang>.md`, at `{: #<anchor> }`. */
interface Section {
    page: string;
    anchor: string;
}

function sectionOf(guide: string): Section | null {
    const match = GUIDE_SHAPE.exec(guide);
    return match ? {page: match[1], anchor: match[2]} : null;
}

const guideTo = ({page, anchor}: Section): string => `admin/${page}/#${anchor}`;

const distinct = <T>(values: readonly T[]): T[] => [...new Set(values)];

/** The distinct sections of some guides; a path of another shape is left out, the shape case reports it. */
function sectionsOf(guides: readonly string[]): Section[] {
    const sections: Section[] = [];
    for (const guide of distinct(guides)) {
        const section = sectionOf(guide);
        if (section !== null) sections.push(section);
    }
    return sections;
}

const docFile = (page: string, lang: Lang): URL => new URL(`${page}.${lang}.md`, DOCS_ADMIN);
const docName = (page: string, lang: Lang): string => `mkdocs_src/docs/admin/${page}.${lang}.md`;

/** The reader: how many times a page writes the explicit attribute `{: #<anchor> }`, exactly so. */
function anchorCount(text: string, anchor: string): number {
    return text.split(`{: #${anchor} }`).length - 1;
}

/** §2.2 for one guide: what is wrong with its English page, which must exist and write `{: #<anchor> }` exactly once. */
function englishProblems(guide: string): string[] {
    const section = sectionOf(guide);
    if (section === null) return [`${guide}: not a guide, admin/<page>/#<anchor>`];
    const file = docFile(section.page, 'en');
    if (!existsSync(file)) return [`${guide}: ${docName(section.page, 'en')} does not exist`];
    const count = anchorCount(readFileSync(file, 'utf8'), section.anchor);
    return count === 1 ? [] : [`${guide}: ${docName(section.page, 'en')} writes {: #${section.anchor} } ${count} times, not once`];
}

/** §2.5, the ratchet's pairs: `<lang>:<page>#<anchor>` for each translation that exists and does not write the anchor, sorted. */
function missingTranslations(sections: readonly Section[]): string[] {
    const missing: string[] = [];
    for (const {page, anchor} of sections) {
        for (const lang of TRANSLATIONS) {
            const file = docFile(page, lang);
            if (existsSync(file) && anchorCount(readFileSync(file, 'utf8'), anchor) === 0) missing.push(`${lang}:${page}#${anchor}`);
        }
    }
    return missing.sort();
}

/** What a ratchet failure tells the developer to do. */
function ratchetMessage(added: readonly string[], gone: readonly string[]): string {
    const parts = ['The guide anchors missing from the it, fr and es pages must be exactly TRANSLATION_DEBT.'];
    if (added.length > 0) parts.push(`New: ${added.join(', ')} — translate them, or add them to TRANSLATION_DEBT with a reason.`);
    if (gone.length > 0) parts.push(`Gone: ${gone.join(', ')} — translated since: remove them from TRANSLATION_DEBT.`);
    return parts.join(' ');
}

// =============================================================================
//  The reader's controls
// =============================================================================

/** A section every language has: `{: #session-cookie }`, once, in `connection_checks` (contract §2.5). */
const KNOWN_SECTION: Section = {page: 'connection_checks', anchor: 'session-cookie'};

/** A section no language has: an anchor invented for the controls, on the same page. */
const INVENTED_SECTION: Section = {page: 'connection_checks', anchor: 'n69d-invented-anchor'};

/** A page written for the controls: the anchor twice, a link to it, and a longer anchor that starts with it. */
const SAMPLE_PAGE = `## The Session Cookie {: #session-cookie }

It is marked Secure ([the session cookie](#session-cookie)); see [Configuration](configuration.md#session-cookie-secure).

    {: #session-cookie-secure }

## The Session Cookie, Again {: #session-cookie }
`;

/**
 * The reader, proven before a case relies on it. On the sample: a link and a longer anchor are not the anchor, and a
 * repeated anchor counts twice, so «exactly once» can fail. On the real page, in each language: the known section is
 * found once — a reader that finds nothing fails here —, the invented one is reported missing — so does a reader that
 * finds everything.
 */
function expectReaderSees(languages: readonly Lang[]): void {
    expect(anchorCount(SAMPLE_PAGE, KNOWN_SECTION.anchor), 'Control: the sample writes {: #session-cookie } twice; a link to it and {: #session-cookie-secure } are not it').toBe(2);
    for (const lang of languages) {
        const file = docFile(KNOWN_SECTION.page, lang);
        expect(existsSync(file), `Control: ${docName(KNOWN_SECTION.page, lang)} does not exist — the reader looks in the wrong place, or the page moved`).toBe(true);
        const text = readFileSync(file, 'utf8');
        expect(anchorCount(text, KNOWN_SECTION.anchor), `Control: {: #${KNOWN_SECTION.anchor} } is found once in ${docName(KNOWN_SECTION.page, lang)}`).toBe(1);
        expect(anchorCount(text, INVENTED_SECTION.anchor), `Control: the invented {: #${INVENTED_SECTION.anchor} } is reported missing from ${docName(INVENTED_SECTION.page, lang)}`).toBe(0);
    }
}

// =============================================================================
//  The cases' inputs
// =============================================================================

/** One wrong path for each rule of the shape: the shape refuses every one. */
const NOT_GUIDES = [
    'it/admin/configuration/#secrets', // a language prefix: DocsLink adds it
    '/admin/configuration/#secrets', // a leading slash
    'admin/configuration.md#secrets', // the source file, not the page
    'admin/configuration#secrets', // not a folder URL
    'admin/configuration/', // no anchor
];

/** Ids of no check: an unknown one, and names every object inherits — only an own key has a guide. */
const NOT_CHECKS = ['platform.no_such_check', 'constructor', '__proto__', 'toString', 'hasOwnProperty'];

/** A host outside the local network: an open registration reached through it is a finding of the browser. */
const EXTERNAL_HOST = 'librefolio.example.com';

// =============================================================================
//  The cases
// =============================================================================

describe('checkGuides — the guide of each finding of the Security tab (N69d)', () => {
    // red until N69d §1: checkGuides.ts does not exist
    it('§2.1 the shape: every guide is admin/<page>/#<anchor> — no language, no leading slash, no .md, a folder URL, an explicit anchor', async () => {
        expect(
            NOT_GUIDES.filter((path) => GUIDE_SHAPE.test(path)),
            'Control: the shape refuses a path of each wrong kind',
        ).toEqual([]);
        expect(GUIDE_SHAPE.test(guideTo(KNOWN_SECTION)), 'Control: the shape accepts a guide').toBe(true);

        const entries = Object.entries((await checkGuides()).CHECK_GUIDES);
        // The barrier of «every guide matches»: there are guides
        expect(entries.length, 'CHECK_GUIDES holds the guides').toBeGreaterThan(0);
        expect(
            entries.filter(([, guide]) => !GUIDE_SHAPE.test(guide)),
            `Every guide matches ${GUIDE_SHAPE}`,
        ).toEqual([]);
    });

    // red until N69d §1: checkGuides.ts does not exist — and §4, for as long as configuration.en.md lacks frame-protection and csp-report-only
    // H-55 v2: red until configuration.en.md writes {: #csp } (the docs step of the lot) — the anchor of platform.blockedScript
    // H-61: red until hosting_providers.en.md writes {: #panel-api } (the docs step of contract §5)
    it('§2.2 the anchors exist: the English page of each guide writes its anchor exactly once, as {: #<anchor> }', async () => {
        expectReaderSees(['en']);
        expect(englishProblems(guideTo(KNOWN_SECTION)), 'Control: the check passes a section its page has').toEqual([]);
        expect(englishProblems(guideTo(INVENTED_SECTION)), 'Control: the check reports a section its page does not have').toHaveLength(1);

        const {guides, problem} = await moduleGuides();
        const problems = [...(problem === null ? [] : [problem]), ...distinct([...Object.values(EXPECTED_GUIDES), ...guides]).flatMap(englishProblems)];
        expect(problems, 'Each guide, of the table and of the module, names mkdocs_src/docs/admin/<page>.en.md, which writes {: #<anchor> } exactly once').toEqual([]);
    });

    // red until N69d §1: checkGuides.ts and checkGuides.json do not exist
    it('§2.3 the lookup: checkGuidePath answers each own key and nothing else; CHECK_GUIDES is the two halves merged, frozen', async () => {
        const {CHECK_GUIDES, checkGuidePath} = await checkGuides();
        const entries = Object.entries(CHECK_GUIDES);
        // The barrier of the undefined below: the lookup does answer, for every key
        expect(entries.length, 'CHECK_GUIDES holds the guides').toBeGreaterThan(0);
        for (const [id, guide] of entries) expect(checkGuidePath(id), `checkGuidePath('${id}') is its guide`).toBe(guide);
        for (const id of NOT_CHECKS) expect(checkGuidePath(id), `checkGuidePath('${id}'): only an own key has a guide`).toBeUndefined();
        expect(Object.isFrozen(CHECK_GUIDES), 'CHECK_GUIDES is frozen').toBe(true);

        const {server, browser} = guidesJson();
        // The barrier of «no key in both halves»: both halves hold keys
        expect([Object.keys(server).length > 0, Object.keys(browser).length > 0], 'checkGuides.json: both halves hold guides').toEqual([true, true]);
        expect(
            Object.keys(server).filter((id) => Object.hasOwn(browser, id)),
            'No id is in both halves of checkGuides.json',
        ).toEqual([]);
        // FB-27: the guide entries of both halves, as id → path; a support entry has no guide
        const guideEntries = Object.entries({...server, ...browser}).flatMap(([id, help]) => (help.kind === 'guide' ? [[id, help.path] as const] : []));
        expect(guideEntries.length, 'Barrier: checkGuides.json holds guide entries').toBeGreaterThan(0);
        expect(CHECK_GUIDES, 'CHECK_GUIDES is the guide entries of {...server, ...browser} of checkGuides.json, id → path').toEqual(Object.fromEntries(guideEntries));
        for (const id of SUPPORT_IDS) expect(checkGuidePath(id), `checkGuidePath('${id}'): a support check has no guide path`).toBeUndefined();
    });

    // red until FB-27: checkGuides.json holds plain strings, the module has no CHECK_HELP nor checkHelp
    it('FB-27 the help lookup: checkHelp answers each own key of CHECK_HELP, the two halves merged and frozen, and nothing else', async () => {
        const {CHECK_HELP, checkHelp} = await checkHelpModule();
        const entries = Object.entries(CHECK_HELP);
        // The barrier of the undefined below: the lookup does answer, for every key
        expect(entries.length, 'CHECK_HELP holds the helps').toBeGreaterThan(0);
        for (const [id, help] of entries) expect(checkHelp(id), `checkHelp('${id}') is its help`).toEqual(help);
        for (const id of NOT_CHECKS) expect(checkHelp(id), `checkHelp('${id}'): only an own key has a help`).toBeUndefined();
        expect(Object.isFrozen(CHECK_HELP), 'CHECK_HELP is frozen').toBe(true);

        const {server, browser} = guidesJson();
        expect(CHECK_HELP, 'CHECK_HELP is {...server, ...browser} of checkGuides.json').toEqual({...server, ...browser});
    });

    // red until FB-27
    it('FB-27 who solves a check: the three support checks are support, backup.upload_limit and backup.restore_limit stay guides (they apply to self-hosted too)', async () => {
        const {checkHelp, checkGuidePath} = await checkHelpModule();
        for (const id of SUPPORT_IDS) {
            expect(checkHelp(id), `${id} is solved by whoever hosts the instance`).toEqual({kind: 'support'});
            expect(checkGuidePath(id), `${id} has no guide path`).toBeUndefined();
        }
        for (const [id, path] of [
            ['backup.upload_limit', 'admin/configuration/#main-options'],
            ['backup.restore_limit', 'admin/cli_backup/#backup-restore-dry-run'],
        ] as const) {
            expect(checkHelp(id), `${id} stays a guide: it applies to a self-hosted instance`).toEqual({kind: 'guide', path});
            expect(checkGuidePath(id)).toBe(path);
        }
    });

    // red until N69d §1: checkGuides.json does not exist
    it('§2.4 the browser half: its keys are exactly the ids the browser adds to the Security tab: OPEN_REGISTRATION_NOTICE_ID and platform.blockedScript', () => {
        // Premise: the findings the browser adds to the Security tab — an open registration reached from outside, pinned or not
        const added = new Set<string>();
        for (const registrationLocked of [false, true]) {
            for (const finding of securityFindings([], {registrationMode: 'open', registrationLocked, hostname: EXTERNAL_HOST}).attention) {
                if (finding.source === 'browser') added.add(finding.id);
            }
        }
        // H-55 v2: and a script the policy blocked — a source in the tab's sessionStorage, handed over as `blockedScripts`
        // (a variable, not a literal: the field is the lot's, so the type check does not wait for it)
        const blockedScripts = {registrationMode: 'invite', registrationLocked: false, hostname: EXTERNAL_HOST, blockedScripts: ['inline']};
        for (const finding of securityFindings([], blockedScripts).attention) {
            if (finding.source === 'browser') added.add(finding.id);
        }
        expect([...added].sort(), 'Premise: the findings the browser adds are BROWSER_FINDINGS — a new one needs its guide in checkGuides.json → browser, and its id there').toEqual([...BROWSER_FINDINGS].sort());

        expect(Object.keys(guidesJson().browser).sort(), 'checkGuides.json → browser: exactly the findings the browser adds').toEqual([...BROWSER_FINDINGS].sort());
    });

    // red until N69d §1: checkGuides.ts does not exist (the translations match TRANSLATION_DEBT already)
    it('§2.5 the translation ratchet: the guide anchors missing from the it, fr and es pages are exactly TRANSLATION_DEBT', async () => {
        expect(TRANSLATION_DEBT, 'TRANSLATION_DEBT is sorted, without duplicates').toEqual(distinct(TRANSLATION_DEBT).sort());
        expectReaderSees(LANGUAGES);
        const invented = TRANSLATIONS.map((lang) => `${lang}:${INVENTED_SECTION.page}#${INVENTED_SECTION.anchor}`).sort();
        expect(missingTranslations([KNOWN_SECTION, INVENTED_SECTION]), 'Control: the ratchet reports the invented anchor missing from each translation, session-cookie from none').toEqual(invented);

        const {guides, problem} = await moduleGuides();
        const missing = missingTranslations(sectionsOf([...Object.values(EXPECTED_GUIDES), ...guides]));
        const added = missing.filter((pair) => !TRANSLATION_DEBT.includes(pair));
        const gone = TRANSLATION_DEBT.filter((pair) => !missing.includes(pair));
        expect({new: added, gone}, ratchetMessage(added, gone)).toEqual({new: [], gone: []});
        expect(problem, 'The module’s guides are counted too').toBeNull();
    });

    // red until N69d §1: checkGuides.ts does not exist
    // H-61: red until checkGuides.json holds platform.hosting_panel (contract §5)
    // H-55 v2: red until checkGuides.json holds platform.blockedScript → admin/configuration_security/#csp
    // H5-4: red until checkGuides.json holds accounts.owner_email_change → admin/hosting_instances/#owner-email-change
    // FB-27: red until checkGuides.json holds {kind, path} / {kind: 'support'} entries and the module CHECK_HELP
    it('§1 pinned whole: CHECK_HELP is the table of the 23 helps (20 guides, 3 support), CHECK_GUIDES its 20 guides — a changed help is a change of this file', async () => {
        expect(Object.keys(EXPECTED_HELP).length, 'Control: the table has 23 entries').toBe(23);
        expect(
            Object.entries(EXPECTED_HELP)
                .filter(([, help]) => help.kind === 'support')
                .map(([id]) => id)
                .sort(),
            'Control: the support entries are SUPPORT_IDS',
        ).toEqual([...SUPPORT_IDS].sort());
        const {CHECK_HELP, CHECK_GUIDES} = await checkHelpModule();
        expect(CHECK_HELP, 'CHECK_HELP, check id → {kind, path?}').toEqual(EXPECTED_HELP);
        expect(CHECK_GUIDES, 'CHECK_GUIDES, check id → guide path, the guide entries only').toEqual(EXPECTED_GUIDES);
    });

    // red until FB-27: checkGuides.json holds plain strings
    it('FB-27 the data: checkGuides.json holds, per half, exactly the entries of the table — every guide a path of the shape, no support entry with a path', () => {
        const {server, browser} = guidesJson();
        const serverIds = Object.keys(EXPECTED_HELP).filter((id) => !BROWSER_FINDINGS.includes(id));
        expect(server, 'checkGuides.json → server').toEqual(Object.fromEntries(serverIds.map((id) => [id, EXPECTED_HELP[id]])));
        expect(browser, 'checkGuides.json → browser').toEqual(Object.fromEntries(BROWSER_FINDINGS.map((id) => [id, EXPECTED_HELP[id]])));
        const guideEntries = Object.values({...server, ...browser}).filter((help): help is Extract<Help, {kind: 'guide'}> => help.kind === 'guide');
        expect(guideEntries.length, 'Barrier: guide entries to check').toBe(20);
        expect(
            guideEntries.filter((help) => !GUIDE_SHAPE.test(help.path)),
            `Every guide of the JSON matches ${GUIDE_SHAPE}`,
        ).toEqual([]);
    });
});
