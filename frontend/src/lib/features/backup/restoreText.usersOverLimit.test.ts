/**
 * restoreText — the restore check's warning `users_over_limit` (lot B5-1k2, workstream B).
 *
 * A check of an archive that holds more active accounts than `LIBREFOLIO_MAX_USERS` warns, with the code
 * `users_over_limit`, before the confirmation: nothing is refused (at the first sign-in the administrator chooses who keeps
 * access, A5-7). The report modal draws it as a notice of its own, not as a line of the warnings box.
 *
 * The contract under test:
 *   - RUL-01: `WARNING_KEYS.users_over_limit` is `'backup.restore.report.usersOverLimit'` and `restoreWarningKey` gives it, not
 *     the `unknown` fallback;
 *   - RUL-02: the code is in `WARNINGS_SHOWN_APART`, beside the two of the accounts, which stay there (GUARD, green today for
 *     them);
 *   - RUL-03: the generated client takes the report: `schemas.RestoreStageReport` parses a report carrying the code in its
 *     warnings and the three numbers, and lists the three fields (red until the client is generated again from the backend's
 *     schema, `./dev.py api sync`).
 *
 * Never a wording. Pure: the node environment, nothing renders.
 */
import {describe, expect, it} from 'vitest';
import type {z} from 'zod';
import {schemas} from '$lib/api/generated';
import {restoreWarningKey, WARNING_KEYS, WARNINGS_SHOWN_APART} from './restoreText';

const CODE = 'users_over_limit';
const KEY = 'backup.restore.report.usersOverLimit';
const FALLBACK = 'backup.restore.report.warning.unknown';

/** A report of a check as the backend sends it (`RestoreStageReport`), carrying these warnings and these extra fields. */
function report(warnings: string[], extra: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        backup_created_at: '2026-10-26T10:15:00Z',
        backup_app_version: 'v0.0.0-b51k2',
        backup_origin: 'cli',
        backup_revision: 'head_b51k2',
        app_version: 'v0.0.0-b51k2',
        head_revision: 'head_b51k2',
        action: 'same',
        migrations: [],
        post_migration_fixes: [],
        tables: {users: {before: 6, after: 6}},
        foreign_key_violations_before: 0,
        foreign_key_violations_after: 0,
        files: 0,
        files_size: 0,
        database_size: 8192,
        instance_key_included: false,
        encrypted: false,
        secrets_rekeyed: 0,
        secrets_unreadable: {system: 0, user: 0},
        administrators: ['anna_k', 'bruno_k'],
        warnings,
        blockers: [],
        control_totals: 'absent',
        control_totals_differences: [],
        control_totals_differences_count: 0,
        restorable: true,
        expires_at: '2026-10-27T10:15:00Z',
        ...extra,
    };
}

const NUMBERS = {users_active: 5, users_limit: 3, users_over_limit: 2};

describe('restoreText — the warning users_over_limit', () => {
    it('RUL-01: restoreWarningKey("users_over_limit") is its own key, in WARNING_KEYS, not the unknown fallback', () => {
        expect(WARNING_KEYS[CODE]).toBe(KEY);
        expect(restoreWarningKey(CODE)).toBe(KEY);
        expect(restoreWarningKey(CODE)).not.toBe(FALLBACK);
    });

    it('RUL-02: the code is shown apart, never a line of the warnings box; the two of the accounts still are', () => {
        expect(WARNINGS_SHOWN_APART.has(CODE), 'the code is a line of the warnings box').toBe(true);
        expect(WARNINGS_SHOWN_APART.has('credentials_from_backup')).toBe(true);
        expect(WARNINGS_SHOWN_APART.has('confirming_account_not_in_backup')).toBe(true);
        expect(WARNINGS_SHOWN_APART.has('rows_changed'), 'a real warning must stay a line of the box').toBe(false);
    });
});

describe('the generated client and the warning', () => {
    it('RUL-03: schemas.RestoreStageReport parses a report carrying users_over_limit and the three numbers, as it parses one without', () => {
        const today = schemas.RestoreStageReport.safeParse(report(['rows_changed', 'credentials_from_backup']));
        expect(today.success, `positive control: a report with today's warnings parses: ${today.success ? '' : today.error.message}`).toBe(true);

        const carrying = schemas.RestoreStageReport.safeParse(report([CODE, 'credentials_from_backup'], NUMBERS));
        expect(carrying.success, `the generated client refuses the warning ${CODE}: run ./dev.py api sync — ${carrying.success ? '' : carrying.error.message}`).toBe(true);
    });

    it('RUL-03b: the generated report lists users_active, users_limit and users_over_limit, and they come back out of a parse', () => {
        const shape = (schemas.RestoreStageReport as unknown as z.AnyZodObject).shape;
        expect(Object.keys(shape), 'run ./dev.py api sync').toEqual(expect.arrayContaining(Object.keys(NUMBERS)));

        const parsed = schemas.RestoreStageReport.safeParse(report([CODE, 'credentials_from_backup'], NUMBERS));
        expect(parsed.success).toBe(true);
        if (parsed.success) expect(parsed.data).toMatchObject(NUMBERS);
    });
});
