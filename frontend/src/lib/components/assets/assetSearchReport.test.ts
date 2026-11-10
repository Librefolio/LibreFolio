/**
 * assetSearchReport — pure unit tests (P20 «Can't find it? Let us know», workstream X sub-lot 3).
 *
 * The report of a search that found nothing useful (its channel, `supportChannel`, is tested in `features/support/supportChannel.test.ts`; the
 * bullets below say what each piece does):
 *
 *   - `supportChannel` reads the instance's `support_url` once more — the backend validated it, the frontend
 *     checks it again, so that nothing but an http(s) page, as its normalised absolute address, and `mailto:` with
 *     exactly one address ever becomes a link; anything else (`javascript:` first of all, an address with a user or a
 *     password) is no address: a new GitHub issue when the caller allows that fallback, else no channel at all (X-R37,
 *     N61 — a managed instance has no public fallback);
 *   - `buildSearchReport` writes a fixed English text, pinned here line by line: it is what a maintainer reads,
 *     whatever the language of the user's UI;
 *   - `reportHref` encodes it for its channel: RFC 6068 line breaks (CRLF) for a mail, plain ones for GitHub, and
 *     for a page the same as GitHub's (N61-form): the report's `title` and `body`, each as `encodeURIComponent`
 *     writes it, added to the page's own query after its params, a `title` or a `body` already there replaced, the
 *     page's fragment kept last. The page cases are RED until N61-form: today a page's link is the page alone, and
 *     the body reaches it only through the clipboard (the component's click, which stays as it is).
 *
 * FB-27: the channel (`supportChannel`, `reportHref`, `GITHUB_NEW_ISSUE_URL`, `SupportChannel`) moved to
 * `features/support/supportChannel.ts`, with its cases (`supportChannel.test.ts`): this module keeps `buildSearchReport` and
 * returns a `SupportReport`, and exports none of the moved names (no re-export). Red until the move.
 *
 * Round-trips are proven by decoding the link (`decodeURIComponent`, `new URL().searchParams`), never by encoding
 * the expected one by hand. Privacy is pinned three ways: the body is exact (nothing but the input's fields can be
 * in it), fields the input type has no place for do not leak when a caller passes them anyway, and neither does
 * the address of the page the app runs on.
 *
 * Inputs are deep-frozen, so an in-place write throws (ES modules run in strict mode).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import * as assetSearchReport from './assetSearchReport';
import {buildSearchReport, type SearchReportContext, type SearchReportInput} from './assetSearchReport';
import {GITHUB_NEW_ISSUE_URL, reportHref, supportChannel, type SupportChannel, type SupportReport} from '$lib/features/support/supportChannel';

/** Freezes `value` and everything inside it, so an in-place write throws (ES modules run in strict mode). */
function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
        Object.freeze(value);
    }
    return value;
}

const GITHUB: SupportChannel = {kind: 'github', url: GITHUB_NEW_ISSUE_URL};
const FIRST_LINE = 'I searched LibreFolio for an asset and could not find it.';
const LAST_LINE = "Anything else that helps (the exchange, a link to the asset's page):";
const SUBJECT_PREFIX = 'LibreFolio: asset not found — ';

/** A search with every kind of outcome, a form filled in, and the app that writes the report. */
const INPUT = deepFreeze<SearchReportInput>({
    query: 'Vanguard FTSE All-World',
    providers: [
        {code: 'justetf', status: 'results', count: 1},
        {code: 'yfinance', status: 'results', count: 3},
        {code: 'borsaitaliana', status: 'results', count: 0},
        {code: 'finnhub', status: 'error', errorCode: 'NOT_CONFIGURED'},
        {code: 'stooq', status: 'error', errorCode: null},
        {code: 'morningstar', status: 'error', errorCode: ''},
        {code: 'ariva', status: 'no_answer'},
    ],
    context: {
        currency: 'EUR',
        assetType: 'ETF',
        identifiers: [
            {type: 'ISIN', value: 'IE00BK5BQT80'},
            {type: 'TICKER', value: ' VWCE '},
            {type: 'CUSIP', value: '   '},
        ],
    },
    appVersion: 'v1.2.3-4-gabcdef0',
    profile: 'selfhosted',
    language: 'it',
});

const APP_LINE = 'LibreFolio v1.2.3-4-gabcdef0, selfhosted, language it';

/** The body of INPUT's report, line by line: the contract. */
const BODY = [
    FIRST_LINE,
    '',
    'Search: Vanguard FTSE All-World',
    'Providers:',
    '- justetf: 1 result',
    '- yfinance: 3 results',
    '- borsaitaliana: 0 results',
    '- finnhub: error NOT_CONFIGURED',
    '- stooq: error',
    '- morningstar: error',
    '- ariva: no answer',
    'In the form: currency EUR, type ETF, ISIN IE00BK5BQT80, TICKER VWCE',
    APP_LINE,
    '',
    LAST_LINE,
].join('\n');

describe('assetSearchReport — what stayed here after the channel moved (FB-27)', () => {
    it('exports buildSearchReport and none of the names that moved to features/support/supportChannel.ts: no re-export', () => {
        expect(typeof assetSearchReport.buildSearchReport, 'barrier: the module still has buildSearchReport').toBe('function');
        const moved = ['supportChannel', 'reportHref', 'GITHUB_NEW_ISSUE_URL'];
        expect(
            moved.filter((name) => name in assetSearchReport),
            'moved names still exported from assetSearchReport',
        ).toEqual([]);
    });

    it('buildSearchReport returns a SupportReport: a subject and a body, nothing else', () => {
        const report: SupportReport = buildSearchReport(INPUT);

        expect(Object.keys(report).sort()).toEqual(['body', 'subject']);
    });
});

describe('buildSearchReport', () => {
    it('writes the subject and the body, line by line, with no newline after the last one', () => {
        const report = buildSearchReport(INPUT);

        expect(report.subject).toBe(`${SUBJECT_PREFIX}Vanguard FTSE All-World`);
        expect(report.body.split('\n')).toEqual(BODY.split('\n'));
        expect(report.body).toBe(BODY);
        expect(report.body.endsWith('\n')).toBe(false);
    });

    it('says «Providers: none» on a single line when the search queried no provider', () => {
        const report = buildSearchReport({...INPUT, providers: [], context: null});

        expect(report.body).toBe([FIRST_LINE, '', 'Search: Vanguard FTSE All-World', 'Providers: none', APP_LINE, '', LAST_LINE].join('\n'));
    });

    it('is written in English whatever the language of the UI: only the language line names it', () => {
        expect(buildSearchReport({...INPUT, language: 'fr'}).body).toBe(BODY.replace('language it', 'language fr'));
    });

    it.each<[string, SearchReportContext | null | undefined, string | null]>([
        ['no context (null)', null, null],
        ['no context (undefined)', undefined, null],
        ['an empty context', {}, null],
        ['only null fields', {currency: null, assetType: null, identifiers: null}, null],
        [
            'only blank fields',
            {
                currency: '  ',
                assetType: '',
                identifiers: [
                    {type: 'ISIN', value: ''},
                    {type: 'TICKER', value: '   '},
                ],
            },
            null,
        ],
        ['a currency alone', {currency: 'USD'}, 'In the form: currency USD'],
        ['a type alone', {assetType: 'BOND'}, 'In the form: type BOND'],
        [
            'identifiers alone: values trimmed, blank ones left out',
            {
                identifiers: [
                    {type: 'ISIN', value: ' IT0005557006 '},
                    {type: 'TICKER', value: ' '},
                    {type: 'OTHER', value: 'btp-valore'},
                ],
            },
            'In the form: ISIN IT0005557006, OTHER btp-valore',
        ],
        [
            'every part, whatever the order of the fields: currency, type, then the identifiers in their order',
            {
                identifiers: [
                    {type: 'TICKER', value: 'AAPL'},
                    {type: 'ISIN', value: 'US0378331005'},
                ],
                assetType: 'STOCK',
                currency: 'USD',
            },
            'In the form: currency USD, type STOCK, TICKER AAPL, ISIN US0378331005',
        ],
    ])('the «In the form:» line with %s', (_label, context, line) => {
        const lines = buildSearchReport({...INPUT, context}).body.split('\n');

        expect(lines.filter((l) => l.startsWith('In the form:'))).toEqual(line === null ? [] : [line]);
        // In its place: right after the providers, right before the line of the app.
        expect(lines[lines.indexOf(APP_LINE) - 1]).toBe(line ?? '- ariva: no answer');
    });

    it('leaves the «In the form:» line out when the input has no context field at all', () => {
        const {context: _context, ...withoutContext} = INPUT;
        const lines = buildSearchReport(withoutContext).body.split('\n');

        expect(lines.filter((l) => l.startsWith('In the form:'))).toEqual([]);
    });

    describe('the subject', () => {
        const subjectOf = (query: string): string => buildSearchReport({...INPUT, query}).subject;

        it('trims the query and collapses its inner blanks; the body keeps the query as typed, trimmed only', () => {
            const report = buildSearchReport({...INPUT, query: '  Vanguard   FTSE \t All-World \n'});

            expect(report.subject).toBe(`${SUBJECT_PREFIX}Vanguard FTSE All-World`);
            expect(report.body.split('\n')).toContain('Search: Vanguard   FTSE \t All-World');
        });

        it('keeps a query of exactly 80 characters whole, with no ellipsis', () => {
            const query = 'A'.repeat(80);

            expect(subjectOf(query)).toBe(`${SUBJECT_PREFIX}${query}`);
        });

        it('cuts a longer query to its first 80 characters, followed by …', () => {
            expect(subjectOf('B'.repeat(81))).toBe(`${SUBJECT_PREFIX}${'B'.repeat(80)}…`);
        });

        it('counts the 80 characters once the blanks are collapsed', () => {
            // Trimmed and collapsed: 'Fund ' and 90 letters, 95 characters; the 80th is a letter.
            const collapsed = `Fund ${'ABCDEFGHIJ'.repeat(9)}`;

            expect(subjectOf(`   Fund   ${'ABCDEFGHIJ'.repeat(9)}   `)).toBe(`${SUBJECT_PREFIX}${collapsed.slice(0, 80)}…`);
        });

        it('cuts the subject only: the body keeps the whole query', () => {
            const query = 'C'.repeat(120);

            expect(buildSearchReport({...INPUT, query}).body.split('\n')).toContain(`Search: ${query}`);
        });
    });
});

describe('reportHref after buildSearchReport (the channel is shared: features/support/supportChannel.ts)', () => {
    it('end to end: an address read, a report written, a link that gives that very report back', () => {
        const channel = supportChannel('  MAILTO:Support@Example.org ', {githubFallback: false});
        expect(channel, 'a valid address needs no fallback').toStrictEqual({kind: 'mailto', address: 'Support@Example.org'});
        const href = reportHref(channel!, buildSearchReport(INPUT));

        const parts = /^mailto:Support@Example\.org\?subject=([^&]*)&body=([^&]*)$/.exec(href);
        expect(parts, `not mailto:<address>?subject=…&body=…: ${href}`).not.toBeNull();
        expect(decodeURIComponent(parts![1])).toBe(`${SUBJECT_PREFIX}Vanguard FTSE All-World`);
        expect(decodeURIComponent(parts![2]).split('\r\n')).toEqual(BODY.split('\n'));
    });
});

describe('privacy: the report carries its input, and nothing else', () => {
    const CHANNELS: SupportChannel[] = [{kind: 'mailto', address: 'support@example.org'}, {kind: 'page', url: 'https://help.example.org/assets'}, GITHUB];

    /** Everything a report sends, decoded: its subject, its body, and its link on every channel. */
    function sent(report: SupportReport): string {
        return [report.subject, report.body, ...CHANNELS.map((channel) => decodeURIComponent(reportHref(channel, report)))].join('\n');
    }

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('leaves out the fields its input has no place for, even when a caller passes them', () => {
        const leaky = deepFreeze({
            ...INPUT,
            user: 'alice',
            email: 'alice@example.net',
            instanceUrl: 'https://librefolio.example.net',
            portfolio: {value: 123456.78, broker: 'Fineco'},
            providers: [{code: 'justetf', status: 'error', errorCode: 'HTTP_ERROR', error: 'HTTP 401 for alice at https://api.example.net/?key=SECRET-KEY-42'}],
            context: {currency: 'EUR', assetType: 'ETF', identifiers: [{type: 'ISIN', value: 'IE00BK5BQT80', note: 'bought at 98.765'}], quantity: 4321, broker: 'Fineco'},
        }) as unknown as SearchReportInput;

        const report = buildSearchReport(leaky);

        expect(report.body.split('\n')).toContain('- justetf: error HTTP_ERROR');
        expect(report.body.split('\n')).toContain('In the form: currency EUR, type ETF, ISIN IE00BK5BQT80');
        for (const marker of ['alice', 'example.net', '123456', 'Fineco', 'SECRET-KEY-42', '401', '98.765', '4321']) {
            expect(sent(report), `«${marker}» is no field of the report's input, and reached it`).not.toContain(marker);
        }
    });

    it('never writes the address of the page the app runs on', () => {
        const place = {host: 'librefolio.instance.example', hostname: 'librefolio.instance.example', origin: 'https://librefolio.instance.example', href: 'https://librefolio.instance.example/assets', pathname: '/assets'};
        vi.stubGlobal('location', place);
        vi.stubGlobal('window', {location: place});
        vi.stubGlobal('document', {location: place, domain: place.hostname, URL: place.href, referrer: place.href});

        const report = buildSearchReport(INPUT);

        expect(report.body).toBe(BODY);
        expect(sent(report)).not.toContain('librefolio.instance.example');
    });
});
