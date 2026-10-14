// @vitest-environment node
/**
 * pluralCountSites — no ICU plural count of the PAC planner is read off a double (Vitest, node).
 *
 * Subject. The planner keeps every quantity, step and price as exact decimal text and shows it
 * through `format.ts`. When a message picks its noun with `{count, plural, …}`, `count` must be the
 * plural count of the digits shown, read by the twin of the display function
 * (`plannerPlainDecimalCount`, `plannerQuantityCount`, `exactQuantityCount`, pinned by
 * `format.test.ts`): the integer part, plus 0.5 when a fraction is shown, and NaN when the figure is
 * masked or missing. `Number(value)` does not give that count. Twenty fraction digits become the
 * double 1, so the singular appears next to a figure that shows a fraction. `Number(value) || 0`
 * turns an unreadable value into zero. Neither follows the privacy mask. R7 moved `result/text.ts`
 * to the twins. Four sites still pass `Number(…)`, and the fix gives each one
 * `plannerPlainDecimalCount(…)`:
 *   - `modeText.ts`, `modeIncrementText` (`brokers.stepUnits`): `canonical === null ? 0 : Number(canonical)`;
 *   - `steps/AssetsStep.svelte`, `unitsText` (`assets.perUnits`): `Number(price.quoteBaseQuantity)`;
 *   - `steps/AssetsStep.svelte`, the price line (`assets.priceLine`): `Number(asset.price.quoteBaseQuantity)`;
 *   - `shared/ReviewCell.svelte`, a price cell (`review.price`): `Number(value.units) || 0`.
 * Red today with those four; green after the fix.
 *
 * Gate. Every product source of the planner (`.ts`, `.svelte.ts` and `.svelte`, at any depth, tests
 * excluded) is read as text through the bundler, with `import.meta.glob` and `?raw`. The gate knows
 * one form: a `count:` property whose value starts with `Number(` or `parseFloat(`, or contains an
 * operand of a ternary (`?`, `:`) or of a logical operator (`??`, `||`, `&&`) that does. The value
 * may wrap across lines and ends at the first `,`, `;`, `{` or `}`. A failure lists `file:line` of
 * each offender with the matched text. The line is for reporting only, never a key, so nothing has
 * to be re-registered when code moves.
 *
 * Controls. The predicate is proved in both halves on synthetic sources. The forms above are
 * flagged, at the right line. The twin, an integer count (`rows.length`), a conversion under another
 * key (`value: Number(p.close)`, `discount: Number(x)`), a conversion inside a callback, and a
 * conversion that belongs to the next property are not. The scan is not vacuous: it reads `.ts`,
 * `.svelte.ts` and `.svelte` sources in the planner folder and its subfolders, never a test, and it
 * finds `count:` properties in both kinds of source.
 *
 * Limits. The form is a minimum, not a proof. The gate does not see a count converted in another
 * statement (`const n = Number(x)`, then `count: n`), another conversion (`+x`, `parseInt`), a plural
 * argument under another name, or a conversion nested in a call (`Math.max(0, Number(x))`). When the
 * rule grows, grow the form in the same change.
 */
import {describe, expect, it} from 'vitest';

/**
 * The planner's product sources, read as text the way the bundler reads them; the glob arguments
 * must stay literals. Keys are paths relative to this folder (`./steps/AssetsStep.svelte`).
 */
const SOURCES = import.meta.glob<string>(['./**/*.ts', './**/*.svelte', '!./**/*.test.ts'], {query: '?raw', import: 'default', eager: true});

/**
 * A plural count read off a double: `count:`, then `Number(` or `parseFloat(` at the start of the
 * value or of an operand of `?`, `:`, `??`, `||` or `&&` within it. The value may wrap across lines
 * and ends at `,`, `;`, `{` or `}`.
 */
const NUMBER_COUNT = /\bcount:\s*(?:[^,;{}]*?(?:\?\?|\?|:|\|\||&&)\s*)?(?:Number|parseFloat)\(/g;

/** Every `count:` property, whatever its value: the positive control of the scan. */
const COUNT_PROPERTY = /\bcount:/g;

/** An offender of one source: the line of its `count:`, and the matched text with whitespace collapsed. */
interface Hit {
    line: number;
    text: string;
}

/** The 1-based line of an offset. */
function lineAt(source: string, offset: number): number {
    return source.slice(0, offset).split('\n').length;
}

/** Every plural count of a source computed with `Number(` or `parseFloat(`. */
function numberCounts(source: string): Hit[] {
    return [...source.matchAll(NUMBER_COUNT)].map((match) => ({line: lineAt(source, match.index ?? 0), text: match[0].replace(/\s+/g, ' ')}));
}

/** A source key without its `./`, as a failure names the file. */
function fileName(key: string): string {
    return key.replace(/^\.\//, '');
}

describe('pluralCountSites — the predicate, in both halves', () => {
    it.each([
        ['count: Number(x)', 'a direct conversion'],
        ['count: c === null ? 0 : Number(c)', 'the last branch of a ternary'],
        ['count: Number(v) || 0', 'a conversion with a fallback'],
        ['count: parseFloat(x)', 'parseFloat'],
        ['values: {units: u, count: Number(q)}', 'inside the values of a message'],
        ['count: c !== null ? Number(c) : 0', 'the middle branch of a ternary'],
        ['count: x ?? Number(y)', 'an operand of ??'],
        ['count: c === null\n    ? 0\n    : Number(c)', 'a ternary wrapped across lines'],
    ])('flags %j: %s', (source) => {
        expect(numberCounts(source)).toHaveLength(1);
    });

    it.each([
        ['count: plannerPlainDecimalCount(x)', 'the twin of the figure shown'],
        ['count: rows.length', 'an integer count'],
        ['value: Number(p.close)', 'a conversion under another key'],
        ['discount: Number(x)', 'a key that only ends in count'],
        ['count: n, value: Number(p.close)', 'a conversion that belongs to the next property'],
        ['count: rows.filter((r) => Number(r.q) > 0).length', 'a conversion inside a callback, counting rows'],
        ['count: days ?? 0', 'a fallback with no conversion'],
    ])('passes %j: %s', (source) => {
        expect(numberCounts(source)).toEqual([]);
    });

    it('reports each offender at the line of its count, with the matched text', () => {
        const source = ['const a = 1;', "t('k', {values: {count: Number(a)}});", '', 'const values = {', '    step: s,', '    count:', '        c === null ? 0 : Number(c),', '};'].join('\n');
        expect(numberCounts(source)).toEqual([
            {line: 2, text: 'count: Number('},
            {line: 6, text: 'count: c === null ? 0 : Number('},
        ]);
    });
});

describe('pluralCountSites — every plural count in the planner is the twin of its figure, never a double', () => {
    const files = Object.keys(SOURCES).sort();

    it('control: the scan reads the planner sources (.ts, .svelte.ts and .svelte) here and in the subfolders, never a test', () => {
        expect(files.length, 'sources read').toBeGreaterThan(0);
        expect(files, 'the formatter the rule names is read').toContain('./format.ts');
        expect(files.filter((file) => file.endsWith('.svelte')).length, '.svelte sources').toBeGreaterThan(0);
        expect(files.filter((file) => file.endsWith('.svelte.ts')).length, '.svelte.ts sources').toBeGreaterThan(0);
        expect(files.filter((file) => fileName(file).includes('/')).length, 'sources in subfolders').toBeGreaterThan(0);
        expect(
            files.filter((file) => file.endsWith('.test.ts')),
            'no test',
        ).toEqual([]);
        for (const file of files) expect(SOURCES[file], `${file} is read as text`).toEqual(expect.any(String));
    });

    it('control: it finds count properties in both kinds of source', () => {
        const counted = (suffix: string): number => files.filter((file) => file.endsWith(suffix)).reduce((sum, file) => sum + [...SOURCES[file].matchAll(COUNT_PROPERTY)].length, 0);
        expect(counted('.ts'), 'count: in .ts sources').toBeGreaterThan(0);
        expect(counted('.svelte'), 'count: in .svelte sources').toBeGreaterThan(0);
    });

    it('no ICU plural count is computed with Number( or parseFloat(', () => {
        const offenders = files.flatMap((file) => numberCounts(SOURCES[file]).map(({line, text}) => `${fileName(file)}:${line}: ${text}`));
        expect(offenders, 'plural counts read off a double: pass plannerPlainDecimalCount, plannerQuantityCount or exactQuantityCount of the value shown').toEqual([]);
    });
});
