/**
 * Gate: the colour ratchet and the grammar of the colour roles (colour programme, workstream T, decision D-T8).
 *
 * ## What this protects
 *
 * The interface moves, component by component, from Tailwind palette classes (`bg-white`, `text-gray-500`,
 * `dark:bg-slate-800`) and hand-written colours to the colour roles of `src/lib/theme/tokens.css` (`bg-lf-card`,
 * `text-lf-muted`, `border-lf-input`). Two things must hold while it does: what is left of the old way only ever
 * shrinks — the ratchet — and what is written the new way is written right — the grammar. Both are computed by
 * `frontend/scripts/theme/theme-roles.mjs`, the module behind the command line too, so `--check` and this gate
 * cannot disagree. This file proves the module on synthetic inputs first, then applies it to the tree.
 *
 * ## The rules, as this file checks them
 *
 * The module reads every production source of `src` — `.svelte`, `.ts` and `.js`; not the tests, the mocks, the
 * declarations, the generated API client or the Designer Lab — and never a comment. It measures:
 *   m1  the legacy colour classes, counted: a palette colour with its shade, `white`/`black`, `libre-*`,
 *       `primary-*`, `surface-*`, under any colour utility, variants and opacity included;
 *   m2  the colour literals, as a multiset of normalized values: hex, the colour functions, a CSS colour name in a
 *       style value or an SVG colour attribute, a colour name as a whole script string. A colour function built on
 *       `var()` or `${…}` alone is not a literal; `lib/theme/` is not measured; `LITERAL_EXCEPTIONS` lists, with
 *       their reasons, the literals that stay.
 *
 * The ratchet holds the measures against `src/themeRoles.baseline.tsv`, one line per file:
 *   R1  the total of each metric never rises;
 *   R2  a file never rises: its m1 never grows and its m2 values stay among the recorded ones, so that swapping one
 *       colour for another is a rise. A central table of `lib/theme/` may take in m1 classes moved there, R1
 *       holding;
 *   R3  a new file starts empty, unless a declared split gave it a record;
 *   R4  a file that left the tree pairs with a new file of the same name: a move keeps its record;
 *   R5  a drop passes and is reported; `--update` tightens the baseline to it and never widens it.
 *
 * The grammar, in the same sources:
 *   G1  no `dark:` on a role utility: the role changes value with the theme;
 *   G2  every role utility is in the `@theme inline` table of tokens.css: Tailwind drops an unknown class silently;
 *   G3  no element and no class string mixes role utilities with legacy classes: app.css exempts from its legacy
 *       dark remap every element that carries a role utility, so a half-migrated element would keep half of its
 *       old colours;
 *   G4  no arbitrary colour value (`bg-[#…]`, `shadow-[…_rgba(…)]`) unless it reads roles only (`var(--lf-…)`) or
 *       its file is in `ARBITRARY_ALLOWED`, with its reason.
 *
 * ## How to pass it
 *
 * Move the colours to the roles (skill `.github/skills/design-tools/theme-roles/SKILL.md`). A file split in parts is
 * declared in the commit of the split — `node frontend/scripts/theme/theme-roles.mjs --split OLD:NEW1,NEW2` — and
 * the parts share the old file's budget. A drop is banked with `--update`. Only the module writes the baseline:
 * widening a line to pass switches the gate off for that file.
 *
 * ## What it cannot see
 *
 * The forms are a floor, not a proof:
 *   - a class or a colour assembled at run time: `` `bg-${tone}-500` `` (Tailwind cannot see it either),
 *     `` `rgb(${r}, ${g}, ${b})` ``, `` `#${hex}` ``;
 *   - a colour name anywhere but a style value, an SVG colour attribute or a whole script string;
 *   - the stylesheets: a `.css` file is not a production source here. tokens.css is where the colours live, and the
 *     legacy remap of app.css is frozen — `themeTokens.gate.test.ts` watches both;
 *   - Tailwind v4's variable shorthand (`bg-(--x)`) and arbitrary properties (`[color:#fff]`): G4 reads the `-[…]`
 *     form only — m2 still counts the literal of the second;
 *   - meaning: a hex-looking fragment that is no colour (`href="#add"`) is counted. The ratchet needs the count to
 *     be stable, not to be right about intent.
 * When a rule grows, grow the forms in the same change, and add the new form to the controls below.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {beforeAll, describe, expect, it} from 'vitest';
import {existsSync, readFileSync} from 'node:fs';
import {join, relative} from 'node:path';
import {
    ARBITRARY_ALLOWED,
    BASELINE,
    FRONTEND_DIR,
    LEGACY_CLASS_RE,
    LITERAL_EXCEPTIONS,
    SRC_DIR,
    acceptFile,
    byText,
    compareWithBaseline,
    declareSplit,
    formatBaseline,
    grammarOf,
    grammarOfTree,
    isProductionSource,
    listSources,
    measureSource,
    mergeBaselines,
    parseBaseline,
    readBaseline,
    readTokens,
    roleNames,
    scanTree,
    tightenBaseline,
    totalsOf,
} from '../scripts/theme/theme-roles.mjs';

type Scan = Parameters<typeof compareWithBaseline>[0];
type Baseline = Parameters<typeof compareWithBaseline>[1];
type Measure = ReturnType<typeof measureSource>;
type Violation = ReturnType<typeof compareWithBaseline>['violations'][number];
type GrammarViolation = ReturnType<typeof grammarOf>[number];

/** What a ratchet failure tells the developer to do. */
const RATCHET_FIX = [
    'The legacy colours only ever shrink: R1 a total, R2 a file (a colour swapped for another is a rise), R3 a new file starts empty.',
    'Fix: move these colours to the roles of src/lib/theme/tokens.css (skill .github/skills/design-tools/theme-roles/SKILL.md).',
    'A file split in parts is declared, in the commit of the split: node frontend/scripts/theme/theme-roles.mjs --split OLD:NEW1,NEW2',
    'Never widen the baseline to pass: only theme-roles.mjs writes it, and --update only ever tightens it.',
];

/** What a grammar failure tells the developer to do. */
const GRAMMAR_RULES = [
    'G1 never write dark: on a role utility: the role already changes value with the theme.',
    'G2 a role utility must be in the @theme inline table of src/lib/theme/tokens.css: Tailwind drops an unknown class without a word.',
    'G3 an element migrates whole: never mix role utilities and legacy colour classes on one element or in one class string.',
    'G4 no arbitrary colour value: use a role, or read roles only (var(--lf-…)); a brand colour that is not ours to theme goes in ARBITRARY_ALLOWED with its reason.',
];

// ---------------------------------------------------------------------------
// Synthetic scans and baselines
// ---------------------------------------------------------------------------

/** A measure, its literals sorted as the scanner sorts them: `m(2, '#ffffff')`. */
const m = (m1: number, ...m2: string[]): Measure => ({m1, m2: [...m2].sort(byText)});

/** A scan: the sources that measure something, with their measures, plus `clean` sources that measure nothing. */
const measured = (files: Record<string, Measure>, clean: string[] = []): Scan => ({sources: [...Object.keys(files), ...clean].sort(byText), files: new Map(Object.entries(files))});

/** A baseline: one record per file, and the `~` declarations. */
const recorded = (files: Record<string, Measure>, declarations: string[] = []): Baseline => ({files: new Map(Object.entries(files)), declarations});

/** Records as sorted, readable lines: `lib/a.svelte 2 #ffffff`. */
const linesOf = (files: Map<string, Measure>): string[] => [...files].sort(([a], [b]) => byText(a, b)).map(([file, measure]) => [file, measure.m1, ...measure.m2].join(' '));

const brief = (v: Violation): string => `${v.rule} ${v.metric} ${v.file ?? '(total)'}`;
const verdict = (scan: Scan, baseline: Baseline): string[] => compareWithBaseline(scan, baseline).violations.map(brief);

// ---------------------------------------------------------------------------
// A. The scanner
// ---------------------------------------------------------------------------

describe('the scanner, on synthetic sources', () => {
    const SVELTE = 'lib/components/x/Sample.svelte';
    const TS = 'lib/utils/sample.ts';
    const m1Of = (rel: string, text: string): number => measureSource(rel, text).m1;
    const m2Of = (rel: string, text: string): string[] => measureSource(rel, text).m2;

    it('m1 counts each legacy colour class once: variants, opacity, libre-*, placeholder, ring-offset and Svelte class directives included', () => {
        // The positive control of the ratchet: "nothing rose" is also what a pattern that matches nothing would report.
        const counted: ReadonlyArray<readonly [string, string]> = [
            ['bg-white', '<div class="bg-white"></div>'],
            ['dark:hover:bg-slate-700/50', '<div class="p-2 dark:hover:bg-slate-700/50"></div>'],
            ['text-libre-green/80', '<span class="text-libre-green/80"></span>'],
            ['class:bg-gray-50={x}', '<div class:bg-gray-50={x}></div>'],
            ['placeholder-gray-500', '<input class="placeholder-gray-500" />'],
            ['ring-offset-white', '<button class="ring-offset-white"></button>'],
            ['hover:bg-libre-green-dark', '<button class="hover:bg-libre-green-dark"></button>'],
        ];
        expect(counted.map(([form, source]) => `${form}: ${m1Of(SVELTE, source)}`)).toEqual(counted.map(([form]) => `${form}: 1`));
        expect(m1Of(SVELTE, counted.map(([, source]) => source).join('\n')), 'the seven forms in one file').toBe(7);
        expect(m1Of(TS, "export const cls = 'bg-white text-gray-500 dark:border-slate-700';"), 'in a script string').toBe(3);
        expect(
            [...'<p class="dark:hover:bg-slate-700/50 text-libre-green/80">'.matchAll(LEGACY_CLASS_RE)].map((match) => match[0]),
            'one class, one match: its variants and its opacity belong to it',
        ).toEqual(['dark:hover:bg-slate-700/50', 'text-libre-green/80']);
    });

    it('m1 ignores what is not a legacy colour class: keywords, roles, look-alikes, CSS variables and comments', () => {
        const ignored: ReadonlyArray<readonly [string, string, string]> = [
            ['colour keywords', SVELTE, '<div class="bg-transparent text-current"></div>'],
            ['role utilities', SVELTE, '<div class="bg-lf-card text-lf-muted border-lf-input"></div>'],
            ['a test id that spells a class', SVELTE, '<div data-testid="bg-white-card"></div>'],
            ['a CSS variable', SVELTE, '<style>\n    .brand {\n        color: var(--color-libre-green);\n    }\n</style>'],
            ['script comments', SVELTE, '<script>\n    // bg-white\n    /* bg-white */\n</script>'],
            ['a markup comment', SVELTE, '<!-- <div class="bg-white"></div> -->'],
            ['comments in a .ts file', TS, '// bg-white\n/* text-gray-500 */\nexport const x = 1;'],
        ];
        expect(ignored.map(([what, rel, source]) => `${what}: ${m1Of(rel, source)}`)).toEqual(ignored.map(([what]) => `${what}: 0`));
    });

    it('m2 normalizes the literals: hex expanded and lower-cased, functions without spaces, values sorted', () => {
        expect(m2Of(TS, "const a = '#FFF';\nconst b = '#abcd';\nconst c = 'rgba(0, 0, 0, 0.5)';\nconst d = '#123456';")).toEqual(['#123456', '#aabbccdd', '#ffffff', 'rgba(0,0,0,0.5)']);
    });

    it('m2 does not count a colour function built on var() or ${…} alone', () => {
        expect(m2Of(TS, "const a = 'rgba(var(--x-rgb), var(--stale-opacity, 0.5))';\nconst b = `hsla(${hue}, ${alpha})`;")).toEqual([]);
    });

    it('m2 counts a computed hue with literal numbers, except where LITERAL_EXCEPTIONS keeps it', () => {
        const source = 'export const swatch = (h: number): string => `hsl(${h} 68% 44%)`;';
        expect(m2Of('lib/utils/palette.ts', source)).toEqual(['hsl(${h} 68% 44%)']);
        expect(m2Of('lib/utils/colors.ts', source), 'lib/utils/colors.ts: the hsl() and hsla() generators with a computed hue').toEqual([]);
    });

    it('m2 counts a colour name in a style value, not in a selector or a property name', () => {
        expect(m2Of(SVELTE, '<div></div>\n\n<style>\n    .white {\n        white-space: nowrap;\n        color: white;\n    }\n</style>')).toEqual(['white']);
        expect(m2Of(SVELTE, '<div style="border: 1px solid black"></div>'), 'a style attribute').toEqual(['black']);
    });

    it('m2 counts a colour name in an SVG colour attribute and as a whole script string, not as a word inside one', () => {
        expect(m2Of(SVELTE, '<svg viewBox="0 0 10 10"><path fill="white" stroke="currentColor" d="M0 0h10v10H0z" /></svg>')).toEqual(['white']);
        expect(m2Of(TS, "const a = 'white';\nconst b = 'Black';\nconst c = 'whitespace';\nconst d = 'text-white';")).toEqual(['black', 'white']);
        expect(m2Of(SVELTE, "<script>\n    const ink = 'red';\n</script>\n\n<circle fill={active ? 'white' : 'none'} />"), 'in a Svelte script and in a markup expression').toEqual(['red', 'white']);
    });

    it('m2 is empty for a central table of lib/theme/, whatever it holds', () => {
        const source = "export const ink = '#ff0000';\nexport const paper = 'white';\nexport const veil = 'rgba(0, 0, 0, 0.5)';";
        expect(m2Of('lib/theme/palette.ts', source)).toEqual([]);
        expect(m2Of('lib/utils/palette.ts', source), 'the same source anywhere else').toEqual(['#ff0000', 'rgba(0,0,0,0.5)', 'white']);
    });

    it('m2 ignores comments of every kind', () => {
        expect(m2Of(TS, "// '#ff0000'\n/* rgba(0, 0, 0, 0.5) 'white' */\nexport const x = 1;")).toEqual([]);
        expect(m2Of(SVELTE, "<!-- <div style='color: red'></div> -->\n<script>\n    // const c = 'white';\n    /* const d = '#000'; */\n</script>\n\n<style>\n    /* .x { color: #fff; } */\n</style>")).toEqual([]);
    });

    it('m2 sees a colour inside a Tailwind arbitrary value, where `_` stands for a space', () => {
        // OnboardingCoachmark's glow is written this way: `shadow-[0_0_0_5px_rgba(52,211,153,0.4),…]`. `\b` finds no
        // boundary between `_` and a letter, so a pattern anchored on it reads past the whole value.
        expect(m2Of(SVELTE, '<div class="ring-1 ring-[#ff0000] shadow-[0_0_4px_rgba(0,0,0,0.5)]"></div>\n<div class="shadow-[0_0_0_1px_#fff]"></div>')).toEqual(['#ff0000', '#ffffff', 'rgba(0,0,0,0.5)']);
    });

    it('isProductionSource: .svelte, .ts and .js under src, and no test, mock, declaration, Designer Lab or generated client', () => {
        const read = ['lib/components/ui/ThemeToggle.svelte', 'lib/utils/colors.ts', 'lib/stores/app/notify.svelte.ts', 'hooks.client.js', 'routes/(app)/+layout.svelte', 'lib/dev/tools.ts'];
        const skipped = [
            'lib/utils/colors.test.ts',
            'lib/utils/colors.spec.ts',
            'lib/utils/__tests__/helpers.ts',
            '__mocks__/$app/navigation.ts',
            'app.d.ts',
            'lib/dev/designer-lab/LabPanel.svelte',
            'routes/designer-lab/+page.svelte',
            'lib/api/generated.ts',
            'lib/api/generated-tools.ts',
            'lib/api/tool-contract-map.generated.ts',
            'lib/theme/tokens.css',
            'app.css',
            'app.html',
        ];
        expect(
            read.filter((rel) => !isProductionSource(rel)),
            'production sources the scanner would skip',
        ).toEqual([]);
        expect(
            skipped.filter((rel) => isProductionSource(rel)),
            'files the scanner would read',
        ).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// B. The ratchet
// ---------------------------------------------------------------------------

describe('the ratchet, on synthetic scans and baselines', () => {
    it('R1: the total of a metric never rises, and a central table of lib/theme/ obeys it too', () => {
        const before = recorded({'lib/theme/roles.ts': m(1), 'lib/a.svelte': m(5)});
        expect(verdict(measured({'lib/theme/roles.ts': m(4), 'lib/a.svelte': m(5)}), before), 'a central table took in 3 classes nobody gave up').toEqual(['R1 m1 (total)']);
        expect(verdict(measured({'lib/theme/roles.ts': m(4), 'lib/a.svelte': m(2)}), before), 'a central table took in the 3 classes lib/a.svelte gave up').toEqual([]);
        expect(verdict(measured({'lib/a.svelte': m(0, '#000000'), 'lib/b.svelte': m(0, '#ffffff')}), recorded({'lib/a.svelte': m(0, '#000000')})), 'm2').toEqual(['R1 m2 (total)', 'R3 m2 lib/b.svelte']);
    });

    it('R2: a file never rises, in m1 or in m2, even when a colour is only swapped for another', () => {
        const before = recorded({'lib/a.svelte': m(2, '#dc2626'), 'lib/b.svelte': m(3)});
        expect(verdict(measured({'lib/a.svelte': m(3, '#dc2626'), 'lib/b.svelte': m(2)}), before), 'a class moved from b to a: the total holds, a rose').toEqual(['R2 m1 lib/a.svelte']);
        const swapped = compareWithBaseline(measured({'lib/a.svelte': m(2, '#16a34a'), 'lib/b.svelte': m(3)}), before);
        expect(swapped.violations.map(brief), 'the same count, another colour').toEqual(['R2 m2 lib/a.svelte']);
        expect(swapped.violations[0]?.detail, 'the detail names the literal beyond the record').toContain('#16a34a');
        expect(verdict(measured({'lib/a.svelte': m(2, '#dc2626', '#dc2626'), 'lib/b.svelte': m(3)}), before), 'a multiset, not a set: a second #dc2626 is a rise').toEqual(['R1 m2 (total)', 'R2 m2 lib/a.svelte']);
    });

    it('R3: a new file starts empty, even when the total holds, and a copy is not a move', () => {
        expect(verdict(measured({'lib/a.svelte': m(4), 'lib/new.svelte': m(1, '#000000')}), recorded({'lib/a.svelte': m(5, '#000000')}))).toEqual(['R3 m1 lib/new.svelte', 'R3 m2 lib/new.svelte']);
        // The file of the same name is still there: the new one has no record to inherit.
        expect(verdict(measured({'lib/a/Card.svelte': m(1), 'lib/b/Card.svelte': m(2)}), recorded({'lib/a/Card.svelte': m(3)}))).toEqual(['R3 m1 lib/b/Card.svelte']);
    });

    it('R4: a moved file keeps its record and is reported as a move, and a move does not launder a rise', () => {
        const before = recorded({'lib/components/old/Card.svelte': m(3, '#ffffff')});
        const moved = compareWithBaseline(measured({'lib/components/new/Card.svelte': m(2, '#ffffff')}), before);
        expect(moved.violations).toEqual([]);
        expect(moved.moves).toEqual([{from: 'lib/components/old/Card.svelte', to: 'lib/components/new/Card.svelte'}]);

        const rose = compareWithBaseline(measured({'lib/components/new/Card.svelte': m(4, '#ffffff')}), before);
        expect(rose.violations.map(brief)).toEqual(['R1 m1 (total)', 'R2 m1 lib/components/new/Card.svelte']);
        expect(rose.violations[1]?.from, 'the rise is measured against the record of the file it moved from').toBe('lib/components/old/Card.svelte');

        // Two files of the same name left: the move pairs with the record it fits, whatever their order.
        const paired = compareWithBaseline(measured({'lib/c/Card.svelte': m(4)}), recorded({'lib/a/Card.svelte': m(1), 'lib/b/Card.svelte': m(5)}));
        expect(paired.violations).toEqual([]);
        expect(paired.moves).toEqual([{from: 'lib/b/Card.svelte', to: 'lib/c/Card.svelte'}]);
    });

    it('R5: a drop passes and is reported, a file that left the tree included', () => {
        const result = compareWithBaseline(measured({'lib/a.svelte': m(1, '#ffffff')}), recorded({'lib/a.svelte': m(3, '#000000', '#ffffff'), 'lib/gone.svelte': m(2)}));
        expect(result.violations).toEqual([]);
        expect(result.drops).toEqual([
            {file: 'lib/a.svelte', m1: [3, 1], m2Gone: ['#000000']},
            {file: 'lib/gone.svelte', m1: [2, 0], m2Gone: []},
        ]);
    });
});

// ---------------------------------------------------------------------------
// B'. Writing the baseline: --update, --split, --accept, --resolve, the file format
// ---------------------------------------------------------------------------

describe('writing the baseline, on synthetic scans and baselines', () => {
    it('tightenBaseline never raises a line: it takes the lower m1 and the literals both sides hold', () => {
        const before = recorded({'lib/a.svelte': m(2, '#000000', '#ffffff', '#ffffff'), 'lib/b.svelte': m(5, '#000000')});
        const {baseline, refused} = tightenBaseline(measured({'lib/a.svelte': m(3, '#16a34a', '#ffffff'), 'lib/b.svelte': m(1)}), before);
        expect(linesOf(baseline.files)).toEqual(['lib/a.svelte 2 #ffffff', 'lib/b.svelte 1']);
        expect(refused).toEqual([]);
    });

    it('tightenBaseline drops the lines of files gone, renames moved files and refuses an undeclared new file', () => {
        const before = recorded({'lib/gone.svelte': m(2), 'lib/clean.svelte': m(4), 'lib/old/Card.svelte': m(3, '#ffffff')}, ['~accept\tlib/x.svelte\ta reason on record']);
        const {baseline, refused} = tightenBaseline(measured({'lib/new/Card.svelte': m(2, '#ffffff'), 'lib/brand-new.svelte': m(1)}, ['lib/clean.svelte']), before);
        expect(linesOf(baseline.files)).toEqual(['lib/new/Card.svelte 2 #ffffff']);
        expect(refused).toEqual(['lib/brand-new.svelte']);
        expect(baseline.declarations, 'the declarations are kept').toEqual(before.declarations);
    });

    it('tightenBaseline lets a central table of lib/theme/ take in the classes moved there', () => {
        const before = recorded({'lib/theme/roles.ts': m(1), 'lib/a.svelte': m(5)});
        const {baseline} = tightenBaseline(measured({'lib/theme/roles.ts': m(4), 'lib/a.svelte': m(2)}), before);
        expect(linesOf(baseline.files)).toEqual(['lib/a.svelte 2', 'lib/theme/roles.ts 4']);
        expect(totalsOf(baseline.files.values()).m1, 'the total does not rise').toBeLessThanOrEqual(totalsOf(before.files.values()).m1);
    });

    it('tightenBaseline never turns a rejected tree into an accepted one: --update cannot widen the baseline', () => {
        // `--update` writes what tightenBaseline returns. For a tree the gate rejects, the update must refuse a file or
        // leave the tree rejected. A central table may take in classes only while R1 holds.
        const cases: ReadonlyArray<readonly [string, Scan, Baseline]> = [
            ['a file rose (R2)', measured({'lib/a.svelte': m(3), 'lib/b.svelte': m(2)}), recorded({'lib/a.svelte': m(2), 'lib/b.svelte': m(3)})],
            ['a new file (R3)', measured({'lib/a.svelte': m(4), 'lib/new.svelte': m(1)}), recorded({'lib/a.svelte': m(5)})],
            ['a central table took in classes nobody gave up (R1)', measured({'lib/theme/roles.ts': m(10), 'lib/a.svelte': m(5)}), recorded({'lib/theme/roles.ts': m(1), 'lib/a.svelte': m(5)})],
        ];
        expect(
            cases.filter(([, scan, baseline]) => compareWithBaseline(scan, baseline).violations.length === 0).map(([what]) => what),
            'every case is rejected to begin with',
        ).toEqual([]);
        const widens = ([, scan, baseline]: readonly [string, Scan, Baseline]): boolean => {
            const update = tightenBaseline(scan, baseline);
            return update.refused.length === 0 && compareWithBaseline(scan, update.baseline).violations.length === 0;
        };
        expect(
            cases.filter(widens).map(([what]) => what),
            'tightenBaseline returned a baseline that accepts what the old one rejected, refusing nothing: --update would widen it',
        ).toEqual([]);
    });

    it('declareSplit gives the parts their measures as records, within the budget of the old file, which may survive as a part', () => {
        const before = recorded({'lib/Big.svelte': m(5, '#000000', '#ffffff'), 'lib/Other.svelte': m(1)});
        const after = measured({'lib/Big.svelte': m(1), 'lib/PartA.svelte': m(2, '#ffffff'), 'lib/PartB.svelte': m(2, '#000000'), 'lib/Other.svelte': m(1)});
        expect(verdict(after, before), 'undeclared, the parts are new files').toEqual(['R3 m1 lib/PartA.svelte', 'R3 m2 lib/PartA.svelte', 'R3 m1 lib/PartB.svelte', 'R3 m2 lib/PartB.svelte']);

        const split = declareSplit(after, before, 'lib/Big.svelte', ['lib/PartA.svelte', 'lib/PartB.svelte']);
        expect(linesOf(split.files)).toEqual(['lib/Big.svelte 1', 'lib/Other.svelte 1', 'lib/PartA.svelte 2 #ffffff', 'lib/PartB.svelte 2 #000000']);
        expect(split.declarations).toEqual(['~split\tlib/Big.svelte\tlib/PartA.svelte,lib/PartB.svelte\t5\t#000000\t#ffffff']);
        expect(verdict(after, split), 'declared, the tree passes').toEqual([]);
    });

    it('declareSplit refuses parts holding more classes than the budget, or a literal the old file did not hold', () => {
        const before = recorded({'lib/Big.svelte': m(5, '#000000', '#ffffff')});
        const split = (parts: Record<string, Measure>) => (): unknown => declareSplit(measured(parts), before, 'lib/Big.svelte', Object.keys(parts));
        expect(split({'lib/PartA.svelte': m(3, '#ffffff'), 'lib/PartB.svelte': m(3, '#000000')})).toThrow(/hold 6 legacy colour classes.* had 5/);
        expect(split({'lib/PartA.svelte': m(2, '#ffffff'), 'lib/PartB.svelte': m(2, '#16a34a')})).toThrow(/colour literals .*did not: #16a34a/);
        // The old file kept as a part counts once: its record is the budget, not an addition to it.
        expect(split({'lib/Big.svelte': m(3), 'lib/PartA.svelte': m(3)})).toThrow(/hold 6 legacy colour classes/);
        expect(() => declareSplit(measured({'lib/PartA.svelte': m(1)}), before, 'lib/Nope.svelte', ['lib/PartA.svelte'])).toThrow(/no record/);
        expect(() => declareSplit(measured({'lib/PartA.svelte': m(1)}), before, 'lib/Big.svelte', ['lib/Missing.svelte'])).toThrow(/not a production source/);
    });

    it('acceptFile takes a file as it is with the reason on record, and refuses an empty reason', () => {
        const before = recorded({'lib/a.svelte': m(1)});
        const after = measured({'lib/a.svelte': m(1), 'lib/legacy.svelte': m(4, '#123456')});
        const accepted = acceptFile(after, before, 'lib/legacy.svelte', '  kept as it is until\n  the coordinator decides ');
        expect(linesOf(accepted.files)).toEqual(['lib/a.svelte 1', 'lib/legacy.svelte 4 #123456']);
        expect(accepted.declarations).toEqual(['~accept\tlib/legacy.svelte\tkept as it is until the coordinator decides']);
        expect(verdict(after, accepted)).toEqual([]);
        expect(() => acceptFile(after, before, 'lib/legacy.svelte', ' \n ')).toThrow(/--reason/);
    });

    it('mergeBaselines keeps the tighter side: the lower m1 and the common literals; a removal stays removed, an addition stays', () => {
        const base = recorded({'lib/both.svelte': m(5, '#000000', '#ffffff'), 'lib/removed.svelte': m(2), 'lib/kept.svelte': m(1)});
        const ours = recorded({'lib/both.svelte': m(3, '#000000', '#ffffff'), 'lib/kept.svelte': m(1)}, ['~split\tlib/X.svelte\tlib/Y.svelte\t4']);
        const theirs = recorded({'lib/both.svelte': m(4, '#ffffff'), 'lib/removed.svelte': m(2), 'lib/kept.svelte': m(1), 'lib/added.svelte': m(1, '#000000')}, ['~accept\tlib/added.svelte\ttheir reason', '~split\tlib/X.svelte\tlib/Y.svelte\t4']);
        const merged = mergeBaselines(base, ours, theirs);
        expect(linesOf(merged.files)).toEqual(['lib/added.svelte 1 #000000', 'lib/both.svelte 3 #ffffff', 'lib/kept.svelte 1']);
        expect([...merged.declarations].sort(byText), 'the declarations of both sides, once').toEqual(['~accept\tlib/added.svelte\ttheir reason', '~split\tlib/X.svelte\tlib/Y.svelte\t4']);
        expect(linesOf(mergeBaselines(base, theirs, ours).files), 'the same, whichever side is ours').toEqual(linesOf(merged.files));
    });

    it('formatBaseline writes a header, one sorted line per file that measures anything, then the declarations, and parseBaseline reads it back', () => {
        const baseline = recorded({'lib/z.svelte': m(2, '#ffffff', 'red', '#ffffff', '#ffffff'), 'lib/a.ts': m(0, 'rgba(0,0,0,0.5)'), 'lib/m.svelte': m(7), 'lib/clean.svelte': m(0)}, ['~split\tlib/old.svelte\tlib/m.svelte,lib/z.svelte\t9', '~accept\tlib/a.ts\ta reason on record']);
        const text = formatBaseline(baseline);
        expect(text.endsWith('\n'), 'the file ends with a newline').toBe(true);
        const rows = text.slice(0, -1).split('\n');
        const kind = (row: string): string => (row.startsWith('#') ? 'header' : row.startsWith('~') ? 'declaration' : 'file');
        const headers = rows.filter((row) => kind(row) === 'header').length;
        expect(headers, 'a header').toBeGreaterThan(0);
        expect(rows.map(kind), 'the header first, then the files, then the declarations').toEqual([...Array.from({length: headers}, () => 'header'), 'file', 'file', 'file', 'declaration', 'declaration']);
        expect(
            rows.filter((row) => kind(row) === 'file'),
            'one line per file, sorted by path, ×N for repeats; no line for a clean file and no totals',
        ).toEqual(['lib/a.ts\t0\trgba(0,0,0,0.5)', 'lib/m.svelte\t7', 'lib/z.svelte\t2\t#ffffff×3\tred']);
        expect(rows.filter((row) => kind(row) === 'declaration')).toEqual(['~accept\tlib/a.ts\ta reason on record', '~split\tlib/old.svelte\tlib/m.svelte,lib/z.svelte\t9']);

        const parsed = parseBaseline(text);
        expect(linesOf(parsed.files)).toEqual(['lib/a.ts 0 rgba(0,0,0,0.5)', 'lib/m.svelte 7', 'lib/z.svelte 2 #ffffff #ffffff #ffffff red']);
        expect(parsed.declarations).toEqual(['~accept\tlib/a.ts\ta reason on record', '~split\tlib/old.svelte\tlib/m.svelte,lib/z.svelte\t9']);
        expect(formatBaseline(parsed), 'the round trip is stable').toBe(text);
    });
});

// ---------------------------------------------------------------------------
// C. The grammar of the roles
// ---------------------------------------------------------------------------

describe('the grammar of the roles, on synthetic sources', () => {
    const SVELTE = 'lib/components/x/Sample.svelte';
    const NAMES = new Set(['card', 'muted', 'primary', 'subtle', 'input']);
    const caught = (rel: string, text: string): string[] => grammarOf(rel, text, NAMES).map((g) => `${g.rule} ${g.line}  ${g.text}`);

    it('G1: no dark: on a role utility, wherever it sits among the variants; dark: on a legacy class is not G1', () => {
        expect(caught(SVELTE, '<div class="dark:bg-lf-card text-lf-muted"></div>\n<p class="md:dark:hover:text-lf-primary"></p>\n<span class="bg-white dark:bg-slate-800"></span>')).toEqual(['G1 1  dark:bg-lf-card', 'G1 2  md:dark:hover:text-lf-primary']);
    });

    it('G2: every role utility names a role of the table, in markup and in scripts', () => {
        expect(caught(SVELTE, '<p class="bg-lf-nope text-lf-muted"></p>\n<p class="hover:border-lf-ghost/50"></p>')).toEqual(['G2 1  bg-lf-nope', 'G2 2  hover:border-lf-ghost/50']);
        expect(caught('lib/utils/sample.ts', "export const ring = 'focus-visible:ring-lf-nope';"), 'in a script string').toEqual(['G2 1  focus-visible:ring-lf-nope']);
    });

    it('G3: no element and no class string mixes role utilities with legacy classes; a child may stay legacy', () => {
        const svelte = ["<script>\n    const cls = 'bg-lf-card text-gray-500';\n</script>", '', '<div class="bg-lf-card" class:bg-white={x}></div>', '<div class="bg-lf-card"><span class="bg-white"></span></div>', '<Card tone="bg-lf-card text-gray-500" />'].join('\n');
        expect(caught(SVELTE, svelte)).toEqual(['G3 2  bg-lf-card text-gray-500', 'G3 5  bg-lf-card bg-white', 'G3 7  bg-lf-card text-gray-500']);
        expect(caught('lib/utils/sample.ts', "export const mixed = 'text-lf-muted text-gray-500';\nexport const roles = 'text-lf-muted bg-lf-card';\nexport const legacy = 'text-gray-500 bg-white';")).toEqual(['G3 1  text-lf-muted text-gray-500']);
    });

    it('G4: no arbitrary colour value unless it reads roles only, or its file is in ARBITRARY_ALLOWED', () => {
        const source = ['<div class="bg-[#123456]"></div>', '<div class="bg-[var(--lf-surface-card)] ring-[color-mix(in_oklab,var(--lf-focus)_40%,transparent)]"></div>', '<div class="text-[13px] w-[#123456]"></div>', '<div class="text-[var(--color-libre-green)]"></div>'].join('\n');
        expect(caught(SVELTE, source)).toEqual(['G4 1  bg-[#123456]', 'G4 4  text-[var(--color-libre-green)]']);
        const brand = "export const reddit = 'bg-[#ff4500] hover:bg-[#e03d00]';";
        expect(caught('lib/components/support/supportLinks.ts', brand), 'a file in ARBITRARY_ALLOWED').toEqual([]);
        expect(caught('lib/components/support/otherLinks.ts', brand), 'the same source in any other file').toEqual(['G4 1  bg-[#ff4500]', 'G4 1  hover:bg-[#e03d00]']);
    });

    it('G4 sees a colour inside an arbitrary value written with `_` for spaces', () => {
        // OnboardingCoachmark's glow is written this way. The second form hides a literal behind a role: `rolesOnly` must
        // see the rgb() as well.
        expect(caught(SVELTE, '<div class="shadow-[0_0_4px_rgba(0,0,0,0.5)]"></div>\n<div class="bg-[color-mix(in_oklab,var(--lf-card)_80%,_rgb(0,0,0))]"></div>')).toEqual(['G4 1  shadow-[0_0_4px_rgba(0,0,0,0.5)]', 'G4 2  bg-[color-mix(in_oklab,var(--lf-card)_80%,_rgb(0,0,0))]']);
    });

    it('accepts role utilities written right: opacity, variants, any colour utility, and a legacy child under a migrated parent', () => {
        expect(caught(SVELTE, '<div class="bg-lf-card/90 hover:bg-lf-subtle border border-lf-input focus-visible:ring-lf-primary text-lf-muted">\n    <span class="bg-white text-gray-500"></span>\n</div>')).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// D. The tree: the gates
// ---------------------------------------------------------------------------

describe('the tree: the colour gates', () => {
    let names: Set<string>;
    let scan: Scan;
    let grammar: GrammarViolation[];

    // Two walks of every production source (~8 MB): once, and with a budget of their own.
    beforeAll(() => {
        names = roleNames(readTokens());
        scan = scanTree();
        grammar = grammarOfTree(SRC_DIR, names);
    }, 60_000);

    it('reads every production source of src, and no test, mock or declaration (positive control)', () => {
        const sources = listSources();
        expect(sources.length, 'a walk of the wrong directory finds far fewer').toBeGreaterThan(300);
        expect(sources).toEqual(expect.arrayContaining(['routes/+layout.svelte', 'routes/+error.svelte', 'lib/utils/colors.ts', 'lib/components/support/supportLinks.ts']));
        expect(sources.filter((rel) => /\.(test|spec)\.ts$|(^|\/)__(tests|mocks)__\/|\.d\.ts$/.test(rel))).toEqual([]);
        expect(scan.sources, 'the scan reads what the walk lists').toEqual(sources);
    });

    it('measures legacy classes in more than 100 files and literals in more than 20 (positive control)', () => {
        const measures = [...scan.files.values()];
        expect(measures.filter((measure) => measure.m1 > 0).length, 'm1: a pattern that matches nothing would pass the ratchet in silence').toBeGreaterThan(100);
        expect(measures.filter((measure) => measure.m2.length > 0).length, 'm2: the same, for the literals').toBeGreaterThan(20);
    });

    it('R1–R4: no total and no file rose above src/themeRoles.baseline.tsv', () => {
        expect(existsSync(BASELINE), `${relative(FRONTEND_DIR, BASELINE)} is missing: the first baseline is written by node frontend/scripts/theme/theme-roles.mjs --init`).toBe(true);
        const {violations} = compareWithBaseline(scan, readBaseline());
        const offenders = violations.map((v) => `${v.rule} ${v.metric}  ${v.file ?? '(total)'}${v.from && v.from !== v.file ? ` (was ${v.from})` : ''}: ${v.detail}`);
        expect(offenders, ['', ...RATCHET_FIX, '', `${offenders.length} violation(s):`, '', ...offenders, ''].join('\n  ')).toEqual([]);
    });

    it('G1–G4: every role utility of the tree is written right', () => {
        const offenders = grammar.map((g) => `${g.file}:${g.line}  ${g.rule}  ${g.text}`);
        expect(offenders, ['', ...GRAMMAR_RULES, '', `${offenders.length} violation(s):`, '', ...offenders, ''].join('\n  ')).toEqual([]);
    });

    it('keeps LITERAL_EXCEPTIONS and ARBITRARY_ALLOWED current and explained', () => {
        const sources = new Set(scan.sources);
        const read = (rel: string): string => readFileSync(join(SRC_DIR, rel), 'utf8');
        // Both lists are keyed by path: read under another path, a file shows everything they let through.
        const literals = (rel: string): string[] => measureSource(`unlisted/${rel}`, read(rel)).m2;
        const arbitrary = (rel: string): GrammarViolation[] => grammarOf(`unlisted/${rel}`, read(rel), names).filter((g) => g.rule === 'G4');
        const staleLiterals = LITERAL_EXCEPTIONS.filter((entry) => !sources.has(entry.file) || !literals(entry.file).some((value) => (typeof entry.value === 'string' ? entry.value === value : entry.value.test(value))));
        const staleArbitrary = Object.keys(ARBITRARY_ALLOWED).filter((rel) => !sources.has(rel) || arbitrary(rel).length === 0);
        const stale = [...staleLiterals.map((entry) => `LITERAL_EXCEPTIONS  ${entry.file}  ${String(entry.value)}`), ...staleArbitrary.map((rel) => `ARBITRARY_ALLOWED  ${rel}`)];
        expect(stale, ['', 'These entries let nothing through: delete them. If the colour is still in the file, the scanner no longer sees its form: fix the form.', '', ...stale, ''].join('\n  ')).toEqual([]);

        const reasons = [...LITERAL_EXCEPTIONS.map((entry) => [entry.file, entry.reason] as const), ...Object.entries(ARBITRARY_ALLOWED)];
        expect(
            reasons.filter(([, reason]) => reason.trim().length < 20).map(([file]) => file),
            'an entry needs a reason a reviewer can check',
        ).toEqual([]);
    });
});
