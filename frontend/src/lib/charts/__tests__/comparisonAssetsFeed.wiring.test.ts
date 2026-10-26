/**
 * X5-F4b wiring: every page that opens the chart's comparison-asset picker feeds it the asset's currency and its benchmark flag.
 *
 * The comparison-asset field of the Signals panel and of the chart settings is the risk comparison's `AssetPickerPanel` (Y5-F4):
 * its currency filter reads `currency`, and its «Benchmarks» section is made of the assets whose `is_benchmark` is true. The
 * panel can only show what the page gives it in `availableAssets`, so a page whose list leaves a key out shows a flat list
 * (no benchmarks first) or an empty currency chip, with no error anywhere. That is how the FX pair detail page went without
 * `is_benchmark` after Y5-F4 had fixed the other three.
 *
 * Mounting four pages loads dozens of endpoints, so, like the «Y-41 wiring» blocks of `chartPageSignals.test.ts`, the feed is
 * proven from the source with its comments blanked: a floor, not a proof. What the panel does with the two keys is pinned by
 * `ChartSignalsSection.test.ts` and `AssetPickerPanel.test.ts`.
 */
import {describe, expect, it} from 'vitest';
import {readFileSync} from 'node:fs';

const ROUTES = '../../../routes/(app)/';

interface FeedPage {
    name: string;
    file: string;
    /** The attribute `availableAssets={…}` the page gives to the component that opens the picker. */
    attribute: true;
    /** The variable the list is built into, when the attribute names it instead of building the list in place. */
    listVariable?: string;
}

const PAGES: FeedPage[] = [
    {name: 'assets list', file: `${ROUTES}assets/+page.svelte`, attribute: true},
    {name: 'asset detail', file: `${ROUTES}assets/[id]/+page.svelte`, attribute: true, listVariable: 'allAssets'},
    {name: 'FX list', file: `${ROUTES}fx/+page.svelte`, attribute: true, listVariable: 'availableAssetsList'},
    {name: 'FX pair detail', file: `${ROUTES}fx/[pair]/+page.svelte`, attribute: true, listVariable: 'allAssets'},
];

/** A source with its comments blanked, the way the gate blanks them: a name in a comment is no code. `//` after `:` stays (`https://`). */
function withoutComments(source: string): string {
    const blank = (text: string, pattern: RegExp): string => text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
    return blank(blank(blank(source, /<!--[\s\S]*?-->/g), /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);
}

/** The text from `open` (an opening bracket of `code`) to its closing one, brackets included; `null` when it never closes. */
function balanced(code: string, open: number): string | null {
    const pairs: Record<string, string> = {'(': ')', '{': '}', '[': ']'};
    const closer = pairs[code[open]];
    if (!closer) return null;
    let depth = 0;
    for (let index = open; index < code.length; index++) {
        if (code[index] === code[open]) depth++;
        else if (code[index] === closer && --depth === 0) return code.slice(open, index + 1);
    }
    return null;
}

/** The expression of the first `availableAssets={…}` attribute of `code`. */
function availableAssetsAttribute(code: string): string | null {
    const found = /availableAssets=\{/.exec(code);
    return found ? balanced(code, found.index + found[0].length - 1) : null;
}

/** The `.map(…)` call that builds `variable` (`variable = … .map(…)`), or `null`. */
function mapBuilding(code: string, variable: string): string | null {
    // The declaration (`variable = $state(…)`) is no build: the list is the assignment whose value is a `.map(` call.
    for (const assignment of code.matchAll(new RegExp(`(?<![\\w$.])${variable}\\s*=\\s*`, 'g'))) {
        const rest = code.slice(assignment.index + assignment[0].length);
        const map = /^[^;{]{0,60}?\.map\(/.exec(rest);
        if (map) return balanced(rest, map[0].length - 1);
    }
    return null;
}

/** Whether `object` writes `key:` (or the shorthand `key,`) as a property. */
const writesKey = (object: string, key: string): boolean => new RegExp(`(?<![\\w$.])${key}\\s*[:,}]`).test(object);

describe('X5-F4b · the pages feed the comparison picker the currency and the benchmark flag', () => {
    for (const page of PAGES) {
        describe(page.name, () => {
            const code = withoutComments(readFileSync(new URL(page.file, import.meta.url), 'utf8'));
            const attribute = availableAssetsAttribute(code);
            // The expression that describes one asset: built in place by the attribute, or by the variable it names.
            const builder = page.listVariable ? mapBuilding(code, page.listVariable) : attribute;

            it('gives `availableAssets` to the component that opens the picker', () => {
                expect(attribute, `${page.file} has no availableAssets={…}`).not.toBeNull();
                if (page.listVariable) expect(attribute, 'the attribute no longer names the list the page builds').toContain(page.listVariable);
            });

            it('builds the list of assets in a place the test can read', () => {
                expect(builder, `${page.file}: no ${page.listVariable ?? 'availableAssets'} = … .map(…) found`).not.toBeNull();
            });

            it('writes the currency of every asset (the picker’s currency filter)', () => {
                expect(writesKey(builder ?? '', 'currency'), `${page.file}: the asset list leaves out \`currency\``).toBe(true);
            });

            it('writes the benchmark flag of every asset (the picker’s «Benchmarks» section)', () => {
                expect(writesKey(builder ?? '', 'is_benchmark'), `${page.file}: the asset list leaves out \`is_benchmark\`, so the picker shows no benchmarks first`).toBe(true);
            });
        });
    }
});
