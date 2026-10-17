/**
 * restoreText — the restore check's new warning `non_iso_currencies` (lot E-19b1, workstream E, item 4).
 *
 * A check of an archive for a restore warns, with the code `non_iso_currencies`, that the restored copy holds stored
 * currency values that are not ISO 4217 codes; like every warning, it lets the restore go on. The report modal shows a
 * warning as `$_(restoreWarningKey(code))`, so the code needs its key, and the key its message.
 *
 * The contract under test:
 *   - RTN-01: `restoreWarningKey('non_iso_currencies')` is `'backup.restore.report.warning.non_iso_currencies'`, not the
 *     `unknown` fallback;
 *   - RTN-02 (GUARD, green today): the function itself works: a warning of today gives its own key, an unknown code the
 *     fallback (the positive control of RTN-01);
 *   - RTN-03: that key is a message of the four catalogues, naming the same placeholders in each, so the modal never
 *     shows a raw key (read from the contract's key);
 *   - RTN-04: the generated client accepts a report carrying the warning: `schemas.RestoreStageReport` parses one, as it
 *     parses a report with today's warnings (red until the client is generated again from the backend's schema,
 *     `./dev.py api sync`: today zod refuses the code, and the whole check's answer with it);
 *   - RTN-05 (GUARD, green today, stays green): every warning the generated client's `RestoreStageReport` lists has its
 *     own key in `WARNING_KEYS`, so no warning the backend sends falls back to `unknown`.
 *
 * Never a wording: a key's presence and its placeholders only. Pure: the node environment, nothing renders.
 */
import {describe, expect, it} from 'vitest';
import type {z} from 'zod';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {schemas} from '$lib/api/generated';
import {restoreWarningKey, WARNING_KEYS} from './restoreText';

const CODE = 'non_iso_currencies';
const KEY = 'backup.restore.report.warning.non_iso_currencies';
const FALLBACK = 'backup.restore.report.warning.unknown';

const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

/** The node at a dotted path of a catalogue, or undefined. */
function messageOf(catalogue: unknown, key: string): unknown {
    let node = catalogue;
    for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
    return node;
}

/** The ICU arguments a message names. */
function placeholdersOf(message: string): string[] {
    return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
}

/** A report of a check as the backend sends it (`RestoreStageReport`), carrying these warnings. */
function report(warnings: string[]): Record<string, unknown> {
    return {
        backup_created_at: '2026-10-15T10:15:00Z',
        backup_app_version: 'v0.0.0-e19b1',
        backup_origin: 'cli',
        backup_revision: 'head_e19b1',
        app_version: 'v0.0.0-e19b1',
        head_revision: 'head_e19b1',
        action: 'same',
        migrations: [],
        post_migration_fixes: [],
        tables: {users: {before: 3, after: 3}},
        foreign_key_violations_before: 0,
        foreign_key_violations_after: 0,
        files: 0,
        files_size: 0,
        database_size: 8192,
        instance_key_included: false,
        encrypted: false,
        secrets_rekeyed: 0,
        secrets_unreadable: {system: 0, user: 0},
        administrators: ['ada_admin'],
        warnings,
        blockers: [],
        control_totals: 'absent',
        control_totals_differences: [],
        control_totals_differences_count: 0,
        restorable: true,
        expires_at: '2026-10-16T10:15:00Z',
    };
}

/** The codes the generated client's `RestoreStageReport.warnings` takes: a `z.array` of a `z.enum`. */
function generatedWarningCodes(): string[] {
    const shape = (schemas.RestoreStageReport as unknown as z.AnyZodObject).shape;
    const warnings = shape.warnings as z.ZodArray<z.ZodEnum<[string, ...string[]]>>;
    return [...warnings.element.options];
}

// =====================================================================================================================
describe('restoreWarningKey — the warning non_iso_currencies', () => {
    // red until E-19b1
    it('RTN-01: restoreWarningKey("non_iso_currencies") is its own key, not the unknown fallback', () => {
        expect(restoreWarningKey(CODE)).toBe(KEY);
    });

    it('RTN-02 GUARD (green today): a warning of today gives its own key, an unknown code the fallback', () => {
        expect(restoreWarningKey('rows_changed')).toBe('backup.restore.report.warning.rows_changed');
        expect(restoreWarningKey('no_such_warning_e19b1')).toBe(FALLBACK);
    });

    // red until E-19b1
    it.each(Object.keys(CATALOGUES))('RTN-03: %s — backup.restore.report.warning.non_iso_currencies is a message, naming the placeholders it names in en', (language) => {
        const english = messageOf(en, KEY);
        expect(typeof english, `en: ${KEY} is not a message of the catalogue`).toBe('string');
        const message = messageOf(CATALOGUES[language], KEY);
        expect(typeof message, `${language}: ${KEY} is not a message of the catalogue`).toBe('string');
        expect(placeholdersOf(message as string), `${language}: ${KEY} names other placeholders than in en`).toEqual(placeholdersOf(english as string));
    });
});

// =====================================================================================================================
describe('the generated client and the warning', () => {
    // red until E-19b1 (until the client is generated again: ./dev.py api sync)
    it('RTN-04: schemas.RestoreStageReport parses a report carrying non_iso_currencies, as it parses one with the warnings of today', () => {
        const today = schemas.RestoreStageReport.safeParse(report(['rows_changed', 'control_totals_changed']));
        expect(today.success, `positive control: a report with today's warnings parses: ${today.success ? '' : today.error.message}`).toBe(true);

        const carrying = schemas.RestoreStageReport.safeParse(report(['rows_changed', CODE]));
        expect(carrying.success, `the generated client refuses the warning ${CODE}: run ./dev.py api sync — ${carrying.success ? '' : carrying.error.message}`).toBe(true);
    });

    it('RTN-05 GUARD (green today): every warning the generated client lists has its own key in WARNING_KEYS', () => {
        const codes = generatedWarningCodes();
        expect(codes, 'positive control: the generated client lists the warnings of today').toContain('rows_changed');

        const withoutKey = codes.filter((code) => !Object.hasOwn(WARNING_KEYS, code));
        expect(withoutKey, 'warnings the report modal would show as the unknown fallback').toEqual([]);
    });
});
