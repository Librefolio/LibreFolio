/**
 * assetSearchReport — pure unit tests (P20 «Can't find it? Let us know», workstream X sub-lot 3).
 *
 * The report of a search that found nothing useful, and the link that sends it from the user's own client:
 *
 *   - `supportChannel` reads the instance's `support_url` once more — the backend validated it, the frontend
 *     checks it again, so that nothing but an http(s) page, as its normalised absolute address, and `mailto:` with
 *     exactly one address ever becomes a link; anything else (`javascript:` first of all, an address with a user or a
 *     password) is no address: a new GitHub issue when the caller allows that fallback, else no channel at all (X-R37,
 *     N61 — a managed instance has no public fallback);
 *   - `buildSearchReport` writes a fixed English text, pinned here line by line: it is what a maintainer reads,
 *     whatever the language of the user's UI;
 *   - `reportHref` encodes it for its channel: RFC 6068 line breaks (CRLF) for a mail, plain ones for GitHub,
 *     nothing at all for a page (the body goes to the clipboard there, not into the URL).
 *
 * Round-trips are proven by decoding the link (`decodeURIComponent`, `new URL().searchParams`), never by encoding
 * the expected one by hand. Privacy is pinned three ways: the body is exact (nothing but the input's fields can be
 * in it), fields the input type has no place for do not leak when a caller passes them anyway, and neither does
 * the address of the page the app runs on.
 *
 * Inputs are deep-frozen, so an in-place write throws (ES modules run in strict mode).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {GITHUB_NEW_ISSUE_URL, buildSearchReport, reportHref, supportChannel, type SearchReport, type SearchReportContext, type SearchReportInput, type SupportChannel} from './assetSearchReport';

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

/** What `encodeURIComponent` writes: unreserved characters and %XX escapes only — never a raw space, `+`, `&`, `=`, `?` or `#`. */
const URI_COMPONENT = /^(?:[A-Za-z0-9\-_.!~*'()]|%[0-9A-F]{2})*$/;

describe('GITHUB_NEW_ISSUE_URL', () => {
    it('is a new issue of the project', () => {
        expect(GITHUB_NEW_ISSUE_URL).toBe('https://github.com/Librefolio/LibreFolio/issues/new');
    });
});

describe('supportChannel', () => {
    /** No address — missing or refused: the GitHub issue when the caller allows that fallback, else no channel at all. */
    function expectMissing(value: string | null | undefined): void {
        expect(supportChannel(value, {githubFallback: true}), 'with the GitHub fallback').toStrictEqual(GITHUB);
        expect(supportChannel(value, {githubFallback: false}), 'without it: no channel').toBeNull();
    }

    /** A valid address: its own channel, whatever the fallback says. */
    function expectChannel(value: string, channel: SupportChannel): void {
        for (const githubFallback of [true, false]) expect(supportChannel(value, {githubFallback}), `githubFallback: ${githubFallback}`).toStrictEqual(channel);
    }

    it.each<[string, string | null | undefined]>([
        ['null', null],
        ['undefined', undefined],
        ['empty', ''],
        ['blank', '  \t\n '],
    ])('has no address when it is %s: GitHub with the fallback, nothing without', (_label, value) => {
        expectMissing(value);
    });

    it.each<[string, string]>([
        ['mailto:support@example.org', 'support@example.org'],
        ['  mailto:support@example.org \n', 'support@example.org'],
        ['MAILTO:Support@Example.org', 'Support@Example.org'],
        ['MailTo:help.desk+librefolio@sub.example.co.uk', 'help.desk+librefolio@sub.example.co.uk'],
    ])('reads %j as the one address to write to, as given, without its scheme — fallback or not', (value, address) => {
        expectChannel(value, {kind: 'mailto', address});
    });

    it.each<[string, string]>([
        ['a header', 'mailto:support@example.org?cc=boss@example.org'],
        ['a subject of its own', 'mailto:support@example.org?subject=hello'],
        ['two addresses, comma', 'mailto:support@example.org,boss@example.org'],
        ['two addresses, semicolon', 'mailto:support@example.org;boss@example.org'],
        ['no address', 'mailto:'],
        ['only blanks after the scheme', 'mailto:   '],
        ['no @', 'mailto:support.example.org'],
        ['two @', 'mailto:support@help@example.org'],
        ['nothing before the @', 'mailto:@example.org'],
        ['nothing after the @', 'mailto:support@'],
        ['a space inside', 'mailto:sup port@example.org'],
        ['a space after the scheme', 'mailto: support@example.org'],
        ['a tab inside', 'mailto:support@exam\tple.org'],
        ['a fragment', 'mailto:support@example.org#top'],
        ['a percent escape', 'mailto:sup%20port@example.org'],
        ['angle brackets', 'mailto:<support@example.org>'],
        ['quotes', 'mailto:"support"@example.org'],
        ['a slash', 'mailto:support@example.org/help'],
    ])('refuses a mailto: with %s: GitHub with the fallback, nothing without', (_label, value) => {
        expectMissing(value);
    });

    it.each<[string, string]>([
        ['https://help.example.org/assets', 'https://help.example.org/assets'],
        ['http://intranet.lan/support', 'http://intranet.lan/support'],
        ['https://help.example.org/assets?from=librefolio', 'https://help.example.org/assets?from=librefolio'],
        ['  https://help.example.org/assets?from=librefolio#form  ', 'https://help.example.org/assets?from=librefolio#form'],
        ['https://help.example.org:8443/support', 'https://help.example.org:8443/support'],
        // Normalised (X-R37): the URL serialiser's absolute form — scheme and host lower-cased, the root path written
        // out, the default port dropped, a space escaped…
        ['HTTPS://Help.Example.org', 'https://help.example.org/'],
        ['https://help.example.org:443/support', 'https://help.example.org/support'],
        ['https://help.example.org/a b', 'https://help.example.org/a%20b'],
        // …and above all with its two slashes: written without them, as given, it is a path of the instance itself.
        ['https:host', 'https://host/'],
        ['https:/help.example.org/assets', 'https://help.example.org/assets'],
        ['http:help.example.org/support', 'http://help.example.org/support'],
    ])('opens %j as the page %j, its normalised absolute address — fallback or not', (value, url) => {
        expectChannel(value, {kind: 'page', url});
    });

    it.each<[string, string]>([
        ['https:host', 'host'],
        ['https:/help.example.org/assets', 'help.example.org'],
    ])('returns %j as an address that needs no base: as an href on the instance’s own page it opens %s', (value, host) => {
        const instancePage = 'https://librefolio.instance.example/assets';
        expect(new URL(value, instancePage).host, `premise: ${value}, as given, is a path of the instance`).toBe('librefolio.instance.example');

        const channel = supportChannel(value, {githubFallback: false});

        expect(channel?.kind).toBe('page');
        const url = channel?.kind === 'page' ? channel.url : '';
        expect(new URL(url, instancePage).href, 'resolved against the instance, the address is itself').toBe(url);
        expect(new URL(url, instancePage).host).toBe(host);
    });

    it.each<[string, string]>([
        ['a user and a password', 'https://user:pass@help.example.org'],
        ['a user', 'https://user@help.example.org'],
        ['a password alone', 'https://:pass@help.example.org/support'],
        ['a user and an empty password', 'http://user:@intranet.lan/support'],
    ])('counts a page with %s in its address as no address: GitHub with the fallback, nothing without', (_label, value) => {
        expectMissing(value);
    });

    it.each<[string, string]>([
        ['a javascript: URL', 'javascript:alert(1)'],
        ['a javascript: URL in mixed case', 'JavaScript:alert(document.cookie)'],
        ['a javascript: URL after blanks', '   javascript:alert(1)'],
        ['a data: URL', 'data:text/html,<script>alert(1)</script>'],
        ['a vbscript: URL', 'vbscript:msgbox(1)'],
        ['a file: URL', 'file:///etc/passwd'],
        ['an ftp: URL', 'ftp://files.example.org/help'],
        ['a scheme-relative URL', '//help.example.org/assets'],
        ['a bare host', 'help.example.org'],
        ['a bare word', 'support'],
        ['https: with no host', 'https://'],
        ['a malformed host', 'http://exa mple.org/'],
        ['a malformed IPv6 host', 'https://[not-an-ip]/'],
    ])('refuses %s: GitHub with the fallback, nothing without', (_label, value) => {
        expectMissing(value);
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

describe('reportHref', () => {
    /** A report with what a URL could stumble on: & = ? # + % quotes, non-ASCII, line breaks, an empty line. */
    const REPORT = deepFreeze<SearchReport>({
        subject: `${SUBJECT_PREFIX}S&P 500 = 50% + "x"? #1 é`,
        body: [FIRST_LINE, '', 'Search: S&P 500 = 50% + "x"? #1 é', 'Providers: none', 'LibreFolio v1, selfhosted, language en', '', LAST_LINE].join('\n'),
    });

    it('mailto: the address, then the subject and the body as parameters, every line break as CRLF (RFC 6068)', () => {
        const href = reportHref({kind: 'mailto', address: 'support+librefolio@example.org'}, REPORT);

        const parts = /^mailto:support\+librefolio@example\.org\?subject=([^&]*)&body=([^&]*)$/.exec(href);
        expect(parts, `not mailto:<address>?subject=…&body=…: ${href}`).not.toBeNull();
        const [, subject, body] = parts!;
        expect(subject).toMatch(URI_COMPONENT);
        expect(body).toMatch(URI_COMPONENT);
        expect(decodeURIComponent(subject)).toBe(REPORT.subject);
        expect(decodeURIComponent(body)).toBe(REPORT.body.replace(/\n/g, '\r\n'));
    });

    it('github: a new issue, the subject as its title and the body as it is, line breaks LF', () => {
        const href = reportHref(GITHUB, REPORT);

        const url = new URL(href);
        expect(`${url.origin}${url.pathname}`).toBe(GITHUB_NEW_ISSUE_URL);
        expect([...url.searchParams.keys()]).toEqual(['title', 'body']);
        expect(url.searchParams.get('title')).toBe(REPORT.subject);
        expect(url.searchParams.get('body')).toBe(REPORT.body);

        const parts = /^([^?]*)\?title=([^&]*)&body=([^&]*)$/.exec(href);
        expect(parts, `not <url>?title=…&body=…: ${href}`).not.toBeNull();
        const [, base, title, body] = parts!;
        expect(base).toBe(GITHUB_NEW_ISSUE_URL);
        expect(title).toMatch(URI_COMPONENT);
        expect(body).toMatch(URI_COMPONENT);
        expect(decodeURIComponent(title)).toBe(REPORT.subject);
        expect(decodeURIComponent(body), 'LF as the report has them: no CR added').toBe(REPORT.body);
    });

    it('github: the page is the channel’s, not a constant', () => {
        const href = reportHref({kind: 'github', url: 'https://github.com/someone/fork/issues/new'}, REPORT);

        expect(href.startsWith('https://github.com/someone/fork/issues/new?title=')).toBe(true);
        expect(new URL(href).searchParams.get('body')).toBe(REPORT.body);
    });

    it('page: the page itself, nothing added — the report goes to the clipboard there', () => {
        const url = 'https://help.example.org/support?topic=assets#form';

        expect(reportHref({kind: 'page', url}, REPORT)).toBe(url);
    });

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
    function sent(report: SearchReport): string {
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
