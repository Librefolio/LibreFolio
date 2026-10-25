/**
 * Source-level guard (W5-11): JavaScript's `Date.UTC(y, …)` and `new Date(y, …)` read a year 0..99 as 1900..1999, so a
 * date typed with a short year (`0024-03-01` for `2024-03-01`, the typo D-P4 wants to catch) is rejected or moved a
 * century. The date modules below must reach the calendar through `utcMs` (`$lib/utils/dateOnly`) instead, and the import
 * wizard must write a day with the one `formatIsoDay` of importReportSets, not with a copy of its own.
 *
 * This reads source text on purpose: the behaviour is covered by the specs of each module; this gate stops the
 * constructor from coming back in through a later edit.
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';

const LIB = new URL('../../', import.meta.url);
const read = (relative: string): string => readFileSync(new URL(relative, LIB), 'utf8');

const GUARDED = ['utils/core/parseTypedDate.ts', 'utils/core/dateArrowStep.ts', 'features/transactions/import/importReportSets.ts', 'features/transactions/import/ImportWizardModal.svelte', 'components/ui/date/CalendarMonth.svelte'];

/** `new Date(year, …)`, `new Date(y, …)`, `new Date(parts.year, …)`: a numeric year as the first of several arguments. */
const YEAR_CONSTRUCTORS = [/new Date\(\s*[a-zA-Z_.]*[yY]ear?\s*,/, /new Date\(\s*y\s*,/];

describe('short-year dates — no Date.UTC / numeric-year constructor in the date modules (W5-11)', () => {
    it.each(GUARDED)('%s does not call Date.UTC(', (file) => {
        expect(read(file)).not.toMatch(/Date\.UTC\(/);
    });

    it.each(GUARDED)('%s does not build a Date from a numeric year', (file) => {
        const source = read(file);
        for (const pattern of YEAR_CONSTRUCTORS) expect(source).not.toMatch(pattern);
    });

    it('ImportWizardModal writes a day with formatIsoDay, not with a local formatSetDay', () => {
        const source = read('features/transactions/import/ImportWizardModal.svelte');
        expect(source).not.toMatch(/function\s+formatSetDay\b/);
        expect(source).toMatch(/import\s*\{[^}]*\bformatIsoDay\b[^}]*\}\s*from\s*'[^']*importReportSets'/);
    });
});
