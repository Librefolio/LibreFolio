// @vitest-environment node
/**
 * checkSupportReport — the report a «Contact support» link carries for one check (FB-27, «guide or support»).
 *
 * Some checks of Settings › Security cannot be solved by the administrator of the instance alone: whoever hosts it must act
 * (`platform.hosting_panel`, `backup.panel_token`, `accounts.owner_email_change`), and the restore-interrupted page is the
 * same case. For them the app offers «Contact support»: a `mailto:` or a support page that opens with a prepared report
 * (`reportHref(channel, report)`, `features/support/supportChannel.ts`). `buildCheckReport` writes that report.
 *
 * The contract under test, `buildCheckReport(input): SupportReport` with
 * `input = {checkId, severity: 'error' | 'warning' | 'info', instanceAddress, appVersion, date}`:
 *   - English, whatever the language of the UI (the maintainer reads it): the function takes no language and no translator;
 *   - the subject names `LibreFolio` and the check id and is shorter than 120 characters;
 *   - the body holds, each on its own line, `Check: <checkId>`, `Severity: <severity>`, `Instance: <instanceAddress>`,
 *     `LibreFolio <appVersion>` and `Date: <date.toISOString()>`;
 *   - nothing else personal: the input has no field for a user, an email address or a secret, and the body is a function of
 *     the input alone — the same input gives the same report, and the page the code runs on is never read.
 *
 * Inputs are deep-frozen, so an in-place write throws (ES modules run in strict mode). The cases iterate every check of the
 * table (`checkGuides.json`) for the subject, so a new check with a long id cannot break the limit unnoticed.
 *
 * Red until FB-27: `checkSupportReport.ts` does not exist (the file fails to import).
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import guides from './checkGuides.json';
import {buildCheckReport} from './checkSupportReport';

/** Freezes `value` and everything inside it, so an in-place write throws (ES modules run in strict mode). */
function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
        Object.freeze(value);
    }
    return value;
}

type Severity = 'error' | 'warning' | 'info';

interface Input {
    checkId: string;
    severity: Severity;
    instanceAddress: string;
    appVersion: string;
    date: Date;
}

const WHEN = new Date('2026-10-28T09:30:15.250Z');

/** An input with a check id that names nothing personal: the privacy cases read the body for such words. */
const INPUT: Input = {checkId: 'platform.hosting_panel', severity: 'warning', instanceAddress: 'https://folio.example.org', appVersion: 'v1.3.0-4-gabcdef0', date: WHEN};

const linesOf = (body: string): string[] => body.split(/\r?\n/);

describe('buildCheckReport — the subject', () => {
    it('names LibreFolio and the check id', () => {
        const {subject} = buildCheckReport(deepFreeze({...INPUT}));

        expect(subject).toContain('LibreFolio');
        expect(subject).toContain('platform.hosting_panel');
    });

    it('is shorter than 120 characters for every check of the table and for the restore-interrupted page', () => {
        const ids = [...Object.keys(guides.server), ...Object.keys(guides.browser), 'platform.restore_interrupted'];
        // Barrier: there are checks to try, and the longest real ids are among them
        expect(ids.length).toBeGreaterThan(20);
        for (const checkId of ids) {
            const {subject} = buildCheckReport(deepFreeze({...INPUT, checkId}));
            expect(subject, `the subject of ${checkId} names the check`).toContain(checkId);
            expect(subject, `the subject of ${checkId} names LibreFolio`).toContain('LibreFolio');
            expect(subject.length, `the subject of ${checkId} is ${subject.length} characters`).toBeLessThan(120);
        }
    });

    it('is one line: no line break', () => {
        expect(buildCheckReport(deepFreeze({...INPUT})).subject).not.toMatch(/[\r\n]/);
    });
});

describe('buildCheckReport — the body', () => {
    it.each<Severity>(['error', 'warning', 'info'])('writes each fact on its own line, severity %s', (severity) => {
        const {body} = buildCheckReport(deepFreeze({...INPUT, severity}));
        const lines = linesOf(body);

        expect(lines).toContain('Check: platform.hosting_panel');
        expect(lines).toContain(`Severity: ${severity}`);
        expect(lines).toContain('Instance: https://folio.example.org');
        expect(lines).toContain('LibreFolio v1.3.0-4-gabcdef0');
        expect(lines).toContain('Date: 2026-10-28T09:30:15.250Z');
    });

    it('writes the date as the ISO 8601 text of the Date it is given, in UTC, to the millisecond', () => {
        const date = new Date(Date.UTC(2031, 0, 2, 3, 4, 5, 6));
        expect(linesOf(buildCheckReport(deepFreeze({...INPUT, date: new Date(date)})).body)).toContain(`Date: ${date.toISOString()}`);
        expect(date.toISOString(), 'control: the ISO text is what the contract says').toBe('2031-01-02T03:04:05.006Z');
    });

    it('writes the check id, the address and the version as given, never trimmed or reshaped', () => {
        const lines = linesOf(buildCheckReport(deepFreeze({...INPUT, checkId: 'accounts.owner_email_change', instanceAddress: 'http://192.168.1.20:6040', appVersion: 'unknown'})).body);

        expect(lines).toContain('Check: accounts.owner_email_change');
        expect(lines).toContain('Instance: http://192.168.1.20:6040');
        expect(lines).toContain('LibreFolio unknown');
    });
});

describe('buildCheckReport — nothing else personal', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('carries no email address, no user, no secret: an input of only its five fields gives a body without @ and without those words', () => {
        const {subject, body} = buildCheckReport(deepFreeze({...INPUT}));

        expect(body, 'no address with @').not.toContain('@');
        expect(subject, 'no address with @ in the subject').not.toContain('@');
        for (const word of ['user', 'email', 'e-mail', 'password', 'secret']) {
            expect(body.toLowerCase(), `the body names no «${word}»`).not.toContain(word);
        }
    });

    it('is the same for the same input: a pure function, call after call', () => {
        const first = buildCheckReport(deepFreeze({...INPUT}));
        const second = buildCheckReport(deepFreeze({...INPUT, date: new Date(WHEN)}));

        expect(second).toEqual(first);
        expect(first.body).toBe(second.body);
    });

    it('changes with the input and only with it: another date changes the date line and no other', () => {
        const a = linesOf(buildCheckReport(deepFreeze({...INPUT})).body);
        const b = linesOf(buildCheckReport(deepFreeze({...INPUT, date: new Date('2027-01-01T00:00:00.000Z')})).body);

        expect(b.length).toBe(a.length);
        const differing = a.flatMap((line, index) => (line === b[index] ? [] : [line]));
        expect(differing, 'only the date line differs').toEqual(['Date: 2026-10-28T09:30:15.250Z']);
    });

    it('never reads the page it runs on: the address of the place is not in the report', () => {
        const place = {host: 'librefolio.elsewhere.example', hostname: 'librefolio.elsewhere.example', origin: 'https://librefolio.elsewhere.example', href: 'https://librefolio.elsewhere.example/settings', pathname: '/settings'};
        vi.stubGlobal('location', place);
        vi.stubGlobal('window', {location: place});
        vi.stubGlobal('document', {location: place, domain: place.hostname, URL: place.href, referrer: place.href});

        const {subject, body} = buildCheckReport(deepFreeze({...INPUT}));

        expect(`${subject}\n${body}`).not.toContain('librefolio.elsewhere.example');
        expect(linesOf(body)).toContain('Instance: https://folio.example.org');
    });
});
