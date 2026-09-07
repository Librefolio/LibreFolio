import {describe, it, expect} from 'vitest';
import type {BrimNotice} from '$lib/types';
import {resolveBrimNoticeMessage} from './resolveBrimNotice';

/** Fake `$t`: known keys interpolate {tokens} from values; unknown keys echo the key. */
function makeT(known: Record<string, string> = {}) {
    return (key: string, opts?: {values?: Record<string, any>}): string => {
        const tpl = known[key];
        if (tpl === undefined) return key;
        const values = opts?.values ?? {};
        return tpl.replace(/\{(\w+)\}/g, (_m, k) => (values[k] !== undefined ? String(values[k]) : `{${k}}`));
    };
}

const notice = (partial: Partial<BrimNotice>): BrimNotice => ({code: null, message: '', context: null, ...partial}) as unknown as BrimNotice;

describe('resolveBrimNoticeMessage', () => {
    it('returns the plugin message verbatim when the notice has no code', () => {
        const t = makeT({'importWizard.brimNotice.X': 'never used'});
        expect(resolveBrimNoticeMessage(notice({message: 'raw plugin text'}), t)).toBe('raw plugin text');
    });

    it('translates a known code and interpolates its context', () => {
        const t = makeT({'importWizard.brimNotice.SKIPPED': 'Skipped {n} rows'});
        const msg = resolveBrimNoticeMessage(notice({code: 'SKIPPED', message: 'fallback', context: {n: 3}}), t);
        expect(msg).toBe('Skipped 3 rows');
    });

    it('aliases row_count into the conventional {n} placeholder', () => {
        const t = makeT({'importWizard.brimNotice.SKIPPED': 'Skipped {n} rows'});
        const msg = resolveBrimNoticeMessage(notice({code: 'SKIPPED', message: 'fallback', context: {row_count: 7}}), t);
        expect(msg).toBe('Skipped 7 rows');
    });

    it('does not override an explicit {n} with row_count', () => {
        const t = makeT({'importWizard.brimNotice.SKIPPED': '{n}'});
        const msg = resolveBrimNoticeMessage(notice({code: 'SKIPPED', message: 'fallback', context: {n: 1, row_count: 99}}), t);
        expect(msg).toBe('1');
    });

    it('ignores a non-numeric row_count', () => {
        const t = makeT({'importWizard.brimNotice.SKIPPED': 'n={n}'});
        const msg = resolveBrimNoticeMessage(notice({code: 'SKIPPED', message: 'fallback', context: {row_count: 'many'}}), t);
        // row_count is not a number → {n} stays unresolved
        expect(msg).toBe('n={n}');
    });

    it('falls back to the plugin message when the code has no translation key', () => {
        const t = makeT();
        expect(resolveBrimNoticeMessage(notice({code: 'UNKNOWN_CODE', message: 'plugin default'}), t)).toBe('plugin default');
    });

    it('tolerates a null context bag', () => {
        const t = makeT({'importWizard.brimNotice.OK': 'all good'});
        expect(resolveBrimNoticeMessage(notice({code: 'OK', message: 'fallback', context: null}), t)).toBe('all good');
    });
});
