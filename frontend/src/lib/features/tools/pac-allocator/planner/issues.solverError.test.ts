/**
 * Lot SE of project 67: `allocation.solver_numerical_error`, the warning a result carries when SCIP failed inside a stage
 * after a plan was held. The plan is shown, not proven, and the stop reads «time limit»; this note names the real cause.
 * The result's notes already list every warning through `presentIssue`; what the code needs is its message, in each of the
 * four languages. Nothing reads the translated text: the message must resolve (not fall back to its key) and differ from
 * the English one outside English.
 */
import {get} from 'svelte/store';
import {locale, t, waitLocale} from 'svelte-i18n';
import {beforeAll, describe, expect, it} from 'vitest';

import {setupI18n} from '$test/component';
import {issueMessageKey} from './issues';

const CODE = 'allocation.solver_numerical_error';

beforeAll(async () => {
    await setupI18n('en');
});

async function messageIn(language: string): Promise<string> {
    locale.set(language);
    await waitLocale(language);
    return get(t)(issueMessageKey(CODE));
}

describe('the solver numerical error note', () => {
    it('has its message in the four languages', async () => {
        const english = await messageIn('en');
        expect(english).not.toBe(issueMessageKey(CODE));
        for (const language of ['it', 'fr', 'es']) {
            const message = await messageIn(language);
            expect(message, language).not.toBe(issueMessageKey(CODE));
            expect(message, language).not.toBe(english);
        }
    });
});
