/**
 * emailText — the words and the colours of the Email settings tab (workstream E, lot E2).
 *
 * The contract under test:
 *   - `problemKey`: each configuration problem the API names (`GET /email/status` → `problem`, the codes of
 *     `backend/app/config/email.py`) has a message of its own, `email.problems.<CODE>`; no problem, or a code this
 *     build does not know (a newer server), falls back to `email.problems.unknown` — an inherited name such as
 *     `constructor` or `__proto__` included: the maps answer only their own entries;
 *   - `minutesUntil`: whole minutes, rounded up, at least one, so that «the next one can go in N min» never promises
 *     less than the server's wait; no value counts as one minute;
 *   - `testFailureMessage`: exactly one translator call per failure, whose answer it returns untouched —
 *     `email.test.errors.<CODE>` for the API codes, the minutes until the next email fits for a rate limit, the SMTP
 *     reason's `email.smtpErrors.<CODE>` for a refused delivery (`SEND_FAILED` when the reason is missing or
 *     unknown), and `email.test.errors.generic` for anything else;
 *   - every key these produce is in the four catalogues, naming exactly the placeholders the code fills;
 *   - the class maps hold whole class strings of colour roles only (theme-roles skill): no palette class, no colour
 *     literal or arbitrary value, no `dark:`, no important modifier, every role declared in tokens.css; and each state
 *     is drawn in its own family, a tinted box pairing its soft surface with the on-soft text.
 *
 * The translator is a recording fake that answers a marker of its own, so a case reads which key and which values
 * were asked for, never a sentence. The catalogue block reads the generated catalogues (`$lib/i18n/<lang>.json`,
 * built from their sources before every Vitest run, as in `settingsTabs.test.ts`) for the presence of a key and the
 * placeholders it names, never for its wording. The colour block reuses the patterns of
 * `scripts/theme/theme-roles.mjs`, the module behind the colour gate, so that the two cannot disagree on what a
 * palette class or a role is; a positive control proves each detector fires.
 *
 * Node environment: nothing here renders.
 */
import {describe, expect, it, vi} from 'vitest';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {LEGACY_CLASS_RE, ROLE_CLASS_RE, readTokens, roleNames} from '../../../../scripts/theme/theme-roles.mjs';
import type {EmailTestFailure} from './emailApi';
import {minutesUntil, NOTICE_CLASSES, OUTCOME_CLASSES, problemKey, STATE_BADGE_CLASSES, STATE_LABEL_KEYS, testFailureMessage} from './emailText';

/** The problem codes of `backend/app/config/email.py`, each with a message of its own. */
const PROBLEM_CODES = ['SMTP_HOST_INVALID', 'SMTP_TLS_INVALID', 'SMTP_PORT_INVALID', 'SMTP_FROM_MISSING', 'SMTP_FROM_INVALID', 'SMTP_REPLY_TO_INVALID', 'SMTP_MAX_PER_HOUR_INVALID', 'SMTP_PASSWORD_UNREADABLE', 'SMTP_CREDENTIALS_INCOMPLETE'];

/** `SmtpErrorCode` of `backend/app/services/email/smtp.py`: why the SMTP server did not take a message. */
const SMTP_CODES = ['CONNECTION_FAILED', 'TLS_FAILED', 'AUTH_FAILED', 'SENDER_REFUSED', 'RECIPIENT_REFUSED', 'TIMEOUT', 'SEND_FAILED'];

/** Names every object inherits: a lookup that reads more than its own entries answers them with a function or an object. */
const INHERITED_NAMES = ['constructor', '__proto__', 'toString', 'hasOwnProperty', 'valueOf'];

type Translate = Parameters<typeof testFailureMessage>[0];
type Values = Record<string, string | number>;

/** What `testFailureMessage` asked the translator for, how many times, and what it returned. */
function asked(failure: EmailTestFailure): {calls: number; key: string | undefined; values: Values | undefined; answer: string} {
    const translate = vi.fn<Translate>((key) => `«${key}»`);
    const answer = testFailureMessage(translate, failure);
    const [key, options] = translate.mock.calls[0] ?? [];
    return {calls: translate.mock.calls.length, key, values: options?.values, answer};
}

/** `failure` is worded by one call for `key` with exactly `values`, and the translator's answer is returned as is. */
function expectAsked(failure: EmailTestFailure, key: string, values?: Values): void {
    expect(asked(failure)).toEqual({calls: 1, key, values, answer: `«${key}»`});
}

// =====================================================================================================================
describe('problemKey — a configuration problem names its own message', () => {
    it.each(PROBLEM_CODES)('%s has a message of its own', (code) => {
        expect(problemKey(code)).toBe(`email.problems.${code}`);
    });

    it.each([
        ['no problem (null)', null],
        ['no problem (undefined)', undefined],
        ['an empty code', ''],
        ['a code this build does not know (a newer server)', 'SMTP_SOMETHING_NEW'],
        ['a known code in another case', 'smtp_port_invalid'],
    ])('%s falls back to email.problems.unknown', (_label, code) => {
        expect(problemKey(code)).toBe('email.problems.unknown');
    });

    it.each(INHERITED_NAMES)('an inherited name, %s, is no problem this build knows: email.problems.unknown', (code) => {
        expect(problemKey(code)).toBe('email.problems.unknown');
    });
});

// =====================================================================================================================
describe('minutesUntil — whole minutes, rounded up, at least one', () => {
    it.each([
        [1, 1],
        [59, 1],
        [60, 1],
        [61, 2],
        [90.5, 2],
        [119, 2],
        [120, 2],
        [121, 3],
        [300, 5],
        [3599, 60],
        [3600, 60],
    ])('%s s → %s min: never a wait shorter than the server’s', (seconds, minutes) => {
        expect(minutesUntil(seconds)).toBe(minutes);
    });

    it.each([
        ['0 s (an email fits now)', 0],
        ['no value (null), counted as one minute', null],
        ['no value (undefined), counted as one minute', undefined],
        ['a negative count of seconds', -30],
        ['a negative count of minutes', -600],
    ])('%s → 1 min', (_label, seconds) => {
        expect(minutesUntil(seconds)).toBe(1);
    });
});

// =====================================================================================================================
describe('testFailureMessage — one translator call per failure', () => {
    it.each<{label: string; failure: EmailTestFailure; key: string}>([
        {label: 'EMAIL_UNAVAILABLE', failure: {errorCode: 'EMAIL_UNAVAILABLE', problem: 'SMTP_PORT_INVALID'}, key: 'email.test.errors.EMAIL_UNAVAILABLE'},
        {label: 'EMAIL_UNAVAILABLE while email is off', failure: {errorCode: 'EMAIL_UNAVAILABLE', problem: 'EMAIL_NOT_CONFIGURED'}, key: 'email.test.errors.EMAIL_UNAVAILABLE'},
        {label: 'EMAIL_RECIPIENT_INVALID', failure: {errorCode: 'EMAIL_RECIPIENT_INVALID'}, key: 'email.test.errors.EMAIL_RECIPIENT_INVALID'},
        {label: 'UNKNOWN (no answer, or an answer without a detail)', failure: {errorCode: 'UNKNOWN'}, key: 'email.test.errors.generic'},
        {label: 'a code this build does not know', failure: {errorCode: 'EMAIL_SOMETHING_NEW'}, key: 'email.test.errors.generic'},
        {label: 'an empty code', failure: {errorCode: ''}, key: 'email.test.errors.generic'},
        {label: 'an inherited name as the code (constructor)', failure: {errorCode: 'constructor'}, key: 'email.test.errors.generic'},
        {label: 'an inherited name as the code (__proto__)', failure: {errorCode: '__proto__'}, key: 'email.test.errors.generic'},
    ])('$label → $key, with no values', ({failure, key}) => {
        expectAsked(failure, key);
    });

    it.each([
        {retryAfter: 300, minutes: 5},
        {retryAfter: 61, minutes: 2},
        {retryAfter: 1, minutes: 1},
        {retryAfter: 3600, minutes: 60},
        {retryAfter: undefined, minutes: 1},
    ])('EMAIL_RATE_LIMITED, retryAfter $retryAfter → the rate-limit message with {minutes: $minutes}', ({retryAfter, minutes}) => {
        expectAsked({errorCode: 'EMAIL_RATE_LIMITED', retryAfter}, 'email.test.errors.EMAIL_RATE_LIMITED', {minutes});
    });

    it.each(SMTP_CODES)('EMAIL_DELIVERY_FAILED, smtpCode %s → its own email.smtpErrors message', (smtpCode) => {
        expectAsked({errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode}, `email.smtpErrors.${smtpCode}`);
    });

    it.each([
        ['an SMTP reason this build does not know', 'SMTP_SOMETHING_NEW'],
        ['no SMTP reason', undefined],
        ['an empty SMTP reason', ''],
    ])('EMAIL_DELIVERY_FAILED with %s → email.smtpErrors.SEND_FAILED', (_label, smtpCode) => {
        expectAsked({errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode}, 'email.smtpErrors.SEND_FAILED');
    });

    it.each(INHERITED_NAMES)('EMAIL_DELIVERY_FAILED with an inherited name as its SMTP reason, %s → email.smtpErrors.SEND_FAILED', (smtpCode) => {
        expectAsked({errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode}, 'email.smtpErrors.SEND_FAILED');
    });

    it('reads only the field of its own code', () => {
        expectAsked({errorCode: 'EMAIL_UNAVAILABLE', smtpCode: 'AUTH_FAILED', retryAfter: 600}, 'email.test.errors.EMAIL_UNAVAILABLE');
        expectAsked({errorCode: 'EMAIL_RATE_LIMITED', smtpCode: 'AUTH_FAILED', retryAfter: 600}, 'email.test.errors.EMAIL_RATE_LIMITED', {minutes: 10});
        expectAsked({errorCode: 'EMAIL_DELIVERY_FAILED', problem: 'SMTP_PORT_INVALID', retryAfter: 600}, 'email.smtpErrors.SEND_FAILED');
    });
});

// =====================================================================================================================
const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

/** The message of `key` in a catalogue: the leaf at its dotted path, or undefined. */
function messageOf(catalogue: unknown, key: string): unknown {
    let node = catalogue;
    for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
    return node;
}

/** The ICU arguments a message names: `minutes` for «try again in {minutes} min». */
function placeholdersOf(message: string): string[] {
    return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
}

/** `key` is a message in all four catalogues, naming exactly the values the code fills. */
function expectInEveryCatalogue(key: string, filled: string[]): void {
    for (const [language, catalogue] of Object.entries(CATALOGUES)) {
        const message = messageOf(catalogue, key);
        expect(typeof message, `${language}: ${key} is a message of the catalogue`).toBe('string');
        expect(placeholdersOf(message as string), `${language}: ${key} names exactly the values the code fills`).toEqual([...filled].sort());
    }
}

/** One failure of each kind `testFailureMessage` words: every message it can produce. */
const EVERY_FAILURE: Array<{label: string; failure: EmailTestFailure}> = [
    {label: 'EMAIL_UNAVAILABLE', failure: {errorCode: 'EMAIL_UNAVAILABLE'}},
    {label: 'EMAIL_RECIPIENT_INVALID', failure: {errorCode: 'EMAIL_RECIPIENT_INVALID'}},
    {label: 'EMAIL_RATE_LIMITED', failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 120}},
    ...SMTP_CODES.map((smtpCode) => ({label: `EMAIL_DELIVERY_FAILED ${smtpCode}`, failure: {errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode}})),
    {label: 'UNKNOWN', failure: {errorCode: 'UNKNOWN'}},
];

describe('every key is in the four catalogues, naming the placeholders the code fills', () => {
    it.each(Object.entries(STATE_LABEL_KEYS))('the %s badge, %s: no placeholder', (_state, key) => {
        expectInEveryCatalogue(key, []);
    });

    it.each([...PROBLEM_CODES, null])('the problem %s: its message takes {variable}, which the tab fills', (code) => {
        expectInEveryCatalogue(problemKey(code), ['variable']);
    });

    it.each(EVERY_FAILURE)('the message of $label, with the values it is asked with', ({failure}) => {
        const {key, values} = asked(failure);
        expectInEveryCatalogue(key ?? '', Object.keys(values ?? {}));
    });
});

// =====================================================================================================================
/** The role names tokens.css declares (`card` for `bg-lf-card`), read as the colour gate reads them. */
const ROLES = roleNames(readTokens());
const STATUS_FAMILIES = ['success', 'warning', 'danger', 'info'];

const tokensOf = (classes: string) => classes.split(/\s+/).filter(Boolean);
/** Palette and legacy colour classes, variants and opacity included (the gate's m1). */
const legacyClasses = (classes: string) => [...classes.matchAll(new RegExp(LEGACY_CLASS_RE.source, 'g'))].map((match) => match[0]);
/** Role utilities: the class, its variants, its role. */
const roleUtilities = (classes: string) => [...classes.matchAll(new RegExp(ROLE_CLASS_RE.source, 'g'))].map((match) => ({utility: match[0], variants: match[1], role: match[2]}));
const darkVariants = (classes: string) => tokensOf(classes).filter((token) => /(?:^|:)dark:/.test(token));
const importantModifiers = (classes: string) => tokensOf(classes).filter((token) => token.startsWith('!') || token.endsWith('!') || token.includes('important'));
/** A hex, a colour function, an arbitrary value or a variable: anything but a named utility. */
const literals = (classes: string) => tokensOf(classes).filter((token) => /[#[(]/.test(token));
const undeclaredRoles = (classes: string) =>
    roleUtilities(classes)
        .filter(({role}) => !ROLES.has(role))
        .map(({utility}) => utility);
/** The status families a class string draws with: `danger` for `bg-lf-danger-soft`. */
const familiesOf = (classes: string) => [
    ...new Set(
        roleUtilities(classes)
            .map(({role}) => role.split('-')[0])
            .filter((family) => STATUS_FAMILIES.includes(family)),
    ),
];

const CLASS_STRINGS = Object.entries({STATE_BADGE_CLASSES, NOTICE_CLASSES, OUTCOME_CLASSES}).flatMap(([map, entries]) => Object.entries(entries).map(([entry, classes]) => ({name: `${map}.${entry}`, classes})));

describe('the class maps — whole strings of colour roles (theme-roles skill)', () => {
    it('cover exactly the values they are read with', () => {
        expect(STATE_LABEL_KEYS).toEqual({off: 'email.state.off', ready: 'email.state.ready', invalid: 'email.state.invalid'});
        expect(Object.keys(STATE_BADGE_CLASSES).sort()).toEqual(['invalid', 'off', 'ready']);
        expect(Object.keys(NOTICE_CLASSES).sort()).toEqual(['error', 'info', 'warning']);
        expect(Object.keys(OUTCOME_CLASSES).sort()).toEqual(['failed', 'sent']);
    });

    it('positive control: each detector finds what it rejects, and tokens.css was read', () => {
        const rejected = 'text-red-500 bg-gray-100 dark:bg-slate-800 text-white bg-lf-card! !text-lf-primary dark:text-lf-primary bg-[#1a4031] border-[rgb(0,0,0)] bg-(--x) bg-lf-nonexistent';

        expect(legacyClasses(rejected)).toEqual(['text-red-500', 'bg-gray-100', 'dark:bg-slate-800', 'text-white']);
        expect(darkVariants(rejected)).toEqual(['dark:bg-slate-800', 'dark:text-lf-primary']);
        expect(importantModifiers(rejected)).toEqual(['bg-lf-card!', '!text-lf-primary']);
        expect(literals(rejected)).toEqual(['bg-[#1a4031]', 'border-[rgb(0,0,0)]', 'bg-(--x)']);
        expect(undeclaredRoles(rejected)).toEqual(['bg-lf-nonexistent']);
        expect(familiesOf('bg-lf-danger-soft text-lf-danger-on-soft text-lf-primary')).toEqual(['danger']);
        expect([...ROLES]).toEqual(expect.arrayContaining(['card', 'neutral', 'danger-soft', 'danger-on-soft', 'danger-line']));
    });

    it.each(CLASS_STRINGS)('$name: roles only — no palette class, no literal, no dark:, no important modifier', ({classes}) => {
        expect(legacyClasses(classes), 'palette and legacy colour classes').toEqual([]);
        expect(literals(classes), 'colour literals, arbitrary values and variables').toEqual([]);
        expect(darkVariants(classes), 'dark: variants: a role already changes with the theme').toEqual([]);
        expect(importantModifiers(classes), 'important modifiers').toEqual([]);
        expect(roleUtilities(classes).length, 'the string draws its colours with roles').toBeGreaterThan(0);
        expect(undeclaredRoles(classes), 'roles tokens.css does not declare: Tailwind would drop them without a word').toEqual([]);
    });

    it.each([
        {name: 'STATE_BADGE_CLASSES.ready', classes: STATE_BADGE_CLASSES.ready, family: 'success', parts: ['soft', 'on-soft']},
        {name: 'STATE_BADGE_CLASSES.invalid', classes: STATE_BADGE_CLASSES.invalid, family: 'danger', parts: ['soft', 'on-soft']},
        {name: 'NOTICE_CLASSES.info', classes: NOTICE_CLASSES.info, family: 'info', parts: ['soft', 'on-soft', 'line']},
        {name: 'NOTICE_CLASSES.warning', classes: NOTICE_CLASSES.warning, family: 'warning', parts: ['soft', 'on-soft', 'line']},
        {name: 'NOTICE_CLASSES.error', classes: NOTICE_CLASSES.error, family: 'danger', parts: ['soft', 'on-soft', 'line']},
        {name: 'OUTCOME_CLASSES.sent', classes: OUTCOME_CLASSES.sent, family: 'success', parts: ['soft', 'on-soft', 'line']},
        {name: 'OUTCOME_CLASSES.failed', classes: OUTCOME_CLASSES.failed, family: 'danger', parts: ['soft', 'on-soft', 'line']},
    ])('$name is drawn in the $family family only, its soft surface with the on-soft text paired with it', ({classes, family, parts}) => {
        expect(familiesOf(classes)).toEqual([family]);
        expect(roleUtilities(classes).map(({role}) => role)).toEqual(expect.arrayContaining(parts.map((part) => `${family}-${part}`)));
    });

    it('STATE_BADGE_CLASSES.off takes no status colour: off is neither good nor bad', () => {
        expect(familiesOf(STATE_BADGE_CLASSES.off)).toEqual([]);
    });
});
