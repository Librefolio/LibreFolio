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
 *       its file is in `ARBITRARY_ALLOWED`, with its reason;
 *   G5  one property, one ternary: no element sets one colour utility twice with the same variants, one of the two
 *       always on. Tailwind 4 emits two such utilities sorted by name, so the later name wins whatever the condition
 *       says: the idle and the state colour are the two branches of one ternary. Read through the element's `class`,
 *       its `{…}` and `${…}` (one that branches, `?`, `&&`, `||`, `??`, is a condition), its `class:` directives and
 *       the UPPER_CASE string constants it names, its file's own and those it imports;
 *   G6  a native field on roles names its text: an `<input>` with a text of its own, a `<textarea>` and a `<select>`
 *       that carry a role utility write a base text role, and a placeholder role when they have a placeholder. app.css
 *       colours the text and the placeholder of a native field only while it carries no role utility, so a migrated
 *       field would fall back to the preflight: the inherited colour, the placeholder at half of it.
 *
 * ## How to pass it
 *
 * Move the colours to the roles (skill `.github/skills/design-tools/theme-roles/SKILL.md`). A file split in parts is
 * declared in the commit of the split — `node frontend/scripts/theme/theme-roles.mjs --split OLD:NEW1,NEW2` — and
 * the parts share the old file's budget. A drop is banked with `--update`. A merge conflict on the baseline is settled
 * by `--resolve`, a three-way merge that keeps a file one side accepted (TC-7). Only the module writes the baseline:
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
 *     be stable, not to be right about intent;
 *   - for G5 and G6, a class that reaches an element through anything but its literals and the UPPER_CASE string
 *     constants it names: a class prop, any other variable, an entry of a table of classes (`toneClasses.ts`). A call
 *     or an array with a branch anywhere is read whole as one condition, and G5 never compares two conditions: they
 *     may exclude each other;
 *   - for G6, a ternary that gives a field its text role in one branch only: a role in any branch counts. On purpose:
 *     requiring one always on would flag the right form, `{err ? 'text-lf-danger' : 'text-lf-primary'}`, and push
 *     authors to an always-on role beside a conditional one, which G5 forbids.
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
    FIELD_TYPES_WITHOUT_TEXT,
    FRONTEND_DIR,
    LEGACY_CLASS_RE,
    LITERAL_EXCEPTIONS,
    SRC_DIR,
    acceptFile,
    byText,
    codeOf,
    compareWithBaseline,
    declareSplit,
    formatBaseline,
    grammarOf,
    grammarOfTree,
    isProductionSource,
    lineAt,
    listSources,
    markupOf,
    measureSource,
    mergeBaselines,
    parseBaseline,
    readBaseline,
    readTokens,
    roleNames,
    scanTree,
    startTags,
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
    'G5 never set one colour utility twice on an element with the same variants, one of them always on: Tailwind 4 emits them by name, so the later name wins whatever the condition. Put the idle and the state colour in the two branches of one ternary.',
    'G6 a native field (input, textarea, select) on roles writes its text role, and placeholder:text-lf-placeholder when it has a placeholder: app.css colours a field only while it has no role utility.',
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
            ['comments in a markup expression', SVELTE, '<Panel onpick={() => {\n    // was bg-white\n}} />\n<p>{/* text-gray-500 */ value}</p>'],
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
        expect(m2Of(SVELTE, "<Panel onpick={() => {\n    // was '#ff0000'\n}} />\n<p>{/* rgba(0, 0, 0, 0.5) */ value}</p>"), 'in a markup expression: an attribute value, a text').toEqual([]);
    });

    it('m2 sees a colour inside a Tailwind arbitrary value, where `_` stands for a space', () => {
        // Arbitrary shadows are written this way, as the coachmark's glow was before `--lf-tour-glow`. `\b` finds no
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
// B''. --resolve: the three-way merge of the baseline (TC-7)
// ---------------------------------------------------------------------------

/**
 * The TC-7 regression. On 15/10 R, then X, merged a baseline that carried an `--accept`: `themeStore.ts`, taken as it
 * is with D3's correction of the title-bar pair, which the m2 multiset reads as a swap. Both times `--resolve` took the
 * accepted colour back out of the record — the old mergeBaselines gave a line present on both sides the values both
 * held, blind to the base and to the `~accept` — so the merged baseline no longer allowed what the accepting branch
 * had passed, and the `--accept` had to be given again by hand.
 *
 * mergeBaselines is now a three-way merge. Per file line: a side that left it as the base had it takes the other
 * side's, removal and addition included. Changed on both sides, the side with a NEW `~accept` for the file — one the
 * base does not hold — wins; both sides accepting is refused, since only the merged tree can be accepted; otherwise
 * the tighter side wins, the lower m1 and the literals both hold, and a line one side removed stays removed. The
 * declarations: those of both sides, once.
 */
describe('mergeBaselines, the TC-7 regression: R and X lost an --accept to --resolve on 15/10', () => {
    const FILE = 'lib/x.svelte';
    /** FILE's line in the base, and what a side may make of it: widen it (an accepted file), or tighten it. */
    const AS_IN_BASE = m(2, '#000000', '#ffffff');
    const WIDENED = m(3, '#000000', '#16a34a', '#ffffff');
    const TIGHTENED = m(1, '#ffffff');
    /** The `~accept` lines of FILE: one new on each side, each with its own reason, and one the base already held. */
    const ACCEPT_OURS = `~accept\t${FILE}\ttaken as it is on our side`;
    const ACCEPT_THEIRS = `~accept\t${FILE}\ttaken as it is on their side`;
    const ACCEPT_IN_BASE = `~accept\t${FILE}\ttaken as it is before the sides parted`;

    /** A side of the merge: FILE's line — `null` when the side removed it — beside a line no case touches. */
    const side = (line: Measure | null, declarations: string[] = []): Baseline => recorded({...(line ? {[FILE]: line} : {}), 'lib/kept.svelte': m(1)}, declarations);
    /** The lines a merge must give: FILE's, if any, and the untouched one. */
    const linesWith = (line: Measure | null): string[] => linesOf(side(line).files);

    interface Merge {
        what: string;
        base: Baseline;
        ours: Baseline;
        theirs: Baseline;
        merged: string[];
    }

    /** The cases that merge, (1)–(6) and (8); (7) is refused, (9) swaps the sides of these, (10) reads the declarations. */
    const MERGES: readonly Merge[] = [
        {
            what: "(1) ours accepted a widened line, theirs left it as the base had it: ours' line — the old merge narrowed it back",
            base: side(AS_IN_BASE),
            ours: side(WIDENED, [ACCEPT_OURS]),
            theirs: side(AS_IN_BASE),
            merged: linesWith(WIDENED),
        },
        {what: "(2) ours accepted a widened line, theirs tightened the same line: ours' line", base: side(AS_IN_BASE), ours: side(WIDENED, [ACCEPT_OURS]), theirs: side(TIGHTENED), merged: linesWith(WIDENED)},
        {what: "(3) ours accepted a widened line, theirs removed it: ours' line", base: side(AS_IN_BASE), ours: side(WIDENED, [ACCEPT_OURS]), theirs: side(null), merged: linesWith(WIDENED)},
        {what: "(4) ours left the line as the base had it, theirs tightened it: theirs' line", base: side(AS_IN_BASE), ours: side(AS_IN_BASE), theirs: side(TIGHTENED), merged: linesWith(TIGHTENED)},
        {what: '(5) ours left the line as the base had it, theirs removed it: removed', base: side(AS_IN_BASE), ours: side(AS_IN_BASE), theirs: side(null), merged: linesWith(null)},
        {
            what: '(6) both changed the line, neither accepted it: the lower m1 and the literals both hold — a widening nobody accepted does not survive',
            base: side(AS_IN_BASE),
            ours: side(m(1, '#000000', '#ffffff')),
            theirs: side(m(3, '#16a34a', '#ffffff')),
            merged: linesWith(m(1, '#ffffff')),
        },
        {what: '(6) both changed the line, neither accepted it, one side removed it: removed', base: side(AS_IN_BASE), ours: side(TIGHTENED), theirs: side(null), merged: linesWith(null)},
        {
            what: '(8) an ~accept the base already held is not new: both changed the line, so the tighter side wins, and nothing is refused',
            base: side(AS_IN_BASE, [ACCEPT_IN_BASE]),
            ours: side(WIDENED, [ACCEPT_IN_BASE]),
            theirs: side(TIGHTENED, [ACCEPT_IN_BASE]),
            merged: linesWith(TIGHTENED),
        },
    ];

    for (const {what, base, ours, theirs, merged} of MERGES) {
        it(what, () => {
            expect(linesOf(mergeBaselines(base, ours, theirs).files)).toEqual(merged);
        });
    }

    it('(7) both sides accepted the file anew, each its own way: refused, whichever side is ours — merge the sources, then --accept the merged file', () => {
        const base = side(AS_IN_BASE);
        const ours = side(WIDENED, [ACCEPT_OURS]);
        const theirs = side(m(2, '#000000', '#dc2626', '#ffffff'), [ACCEPT_THEIRS]);
        expect(() => mergeBaselines(base, ours, theirs)).toThrow(/lib\/x\.svelte: accepted on both sides/);
        expect(() => mergeBaselines(base, theirs, ours), 'the sides swapped').toThrow(/lib\/x\.svelte: accepted on both sides/);
    });

    it('(9) each of (1)–(6) and (8) gives the same lines with ours and theirs swapped: whichever branch runs --resolve', () => {
        const asymmetric = MERGES.filter(({base, ours, theirs, merged}) => linesOf(mergeBaselines(base, theirs, ours).files).join('\n') !== merged.join('\n')).map(({what}) => what);
        expect(asymmetric, 'these cases merge to other lines once ours and theirs are swapped').toEqual([]);
    });

    it('(10) an ~accept line carried by both sides is written once, beside the new one', () => {
        const merged = mergeBaselines(side(AS_IN_BASE, [ACCEPT_IN_BASE]), side(WIDENED, [ACCEPT_IN_BASE, ACCEPT_OURS]), side(AS_IN_BASE, [ACCEPT_IN_BASE]));
        expect(linesOf(merged.files), 'theirs left the line as it was: ours, accepted').toEqual(linesWith(WIDENED));
        expect([...merged.declarations].sort(byText), 'the declarations of both sides, each once').toEqual([ACCEPT_IN_BASE, ACCEPT_OURS].sort(byText));
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
        expect(caught('lib/features/support/supportLinks.ts', brand), 'a file in ARBITRARY_ALLOWED').toEqual([]);
        expect(caught('lib/features/support/otherLinks.ts', brand), 'the same source in any other file').toEqual(['G4 1  bg-[#ff4500]', 'G4 1  hover:bg-[#e03d00]']);
    });

    it('G4 sees a colour inside an arbitrary value written with `_` for spaces', () => {
        // Arbitrary shadows and color-mix() are written this way. The second form hides a literal behind a role:
        // `rolesOnly` must see the rgb() as well.
        expect(caught(SVELTE, '<div class="shadow-[0_0_4px_rgba(0,0,0,0.5)]"></div>\n<div class="bg-[color-mix(in_oklab,var(--lf-card)_80%,_rgb(0,0,0))]"></div>')).toEqual(['G4 1  shadow-[0_0_4px_rgba(0,0,0,0.5)]', 'G4 2  bg-[color-mix(in_oklab,var(--lf-card)_80%,_rgb(0,0,0))]']);
    });

    it('accepts role utilities written right: opacity, variants, any colour utility, and a legacy child under a migrated parent', () => {
        expect(caught(SVELTE, '<div class="bg-lf-card/90 hover:bg-lf-subtle border border-lf-input focus-visible:ring-lf-primary text-lf-muted">\n    <span class="bg-white text-gray-500"></span>\n</div>')).toEqual([]);
    });
});

/**
 * G5, one property, one ternary (rule 4 of the skill design-system). Tailwind 4 emits two base utilities that set the
 * same property sorted by name, and the later name wins whatever the condition says: `border-lf-input`, always on, beat
 * `border-lf-focus`, set only while open, and an open select lost its focus border. So the idle and the state colour of
 * one property are the two branches of one ternary.
 *
 * G5 fires on two different role utilities of one element with the same variant chain and the same colour utility
 * (`bg`, `text`, `border`, `border-t`, `ring`…), one of them always on. Always on: the static text of `class="…"`, and an
 * expression that does not branch, read literal by literal — its strings, and each `${…}` of its templates judged on its
 * own, a method after the template included. On a condition: a `{…}` or a `${…}` that branches — `?`, `&&`, `||` or `??`
 * outside its strings, never `?.` — and a `class:` directive. Two conditions are never compared: they may exclude each
 * other. An UPPER_CASE string constant is read as its value: the file's own, or one it imports from a module of src,
 * which `grammarOf` reads from the `modules` it is given. The text names the pair, `<a> always, <b> on a condition`, or
 * two always on in byte order, on the line of the start tag's `<`.
 */
describe('G5, one property, one ternary, on synthetic sources', () => {
    const SVELTE = 'lib/components/x/Sample.svelte';
    const NAMES = new Set(['card', 'hover', 'panel', 'selected', 'input', 'input-hover', 'focus', 'danger', 'field', 'primary', 'muted', 'link', 'placeholder']);
    const caught = (rel: string, text: string, modules: Record<string, string> = {}): string[] => grammarOf(rel, text, NAMES, modules).map((g) => `${g.rule} ${g.line}  ${g.text}`);

    it('an always-on role and a conditional one on one colour utility fire; the same two as the branches of one ternary are silent', () => {
        expect(caught(SVELTE, `<div class="border border-lf-input {open ? 'border-lf-focus' : ''}"></div>`), 'the select that lost its focus border').toEqual(['G5 1  border-lf-input always, border-lf-focus on a condition']);
        expect(caught(SVELTE, `<div class="border {open ? 'border-lf-focus' : 'border-lf-input hover:border-lf-input-hover'}"></div>`), 'the remedy: one ternary, the idle hover in the idle branch').toEqual([]);
    });

    it('two always-on roles of one colour utility fire, named in byte order whatever their order in the class; one class written twice is one', () => {
        expect(caught(SVELTE, '<p class="text-lf-primary text-lf-muted"></p>')).toEqual(['G5 1  text-lf-muted always, text-lf-primary always']);
        expect(caught(SVELTE, '<p class="text-lf-muted text-lf-primary"></p>'), 'the other order').toEqual(['G5 1  text-lf-muted always, text-lf-primary always']);
        expect(caught(SVELTE, '<p class="text-lf-primary text-lf-primary"></p>'), 'one class written twice').toEqual([]);
    });

    it('reads every form of a condition against an always-on role: a class: directive, a template, &&, ||, ??, a template nested in a branch', () => {
        const forms: ReadonlyArray<readonly [string, string, string]> = [
            ['a class: directive', '<div class="bg-lf-card" class:bg-lf-hover={active}></div>', 'bg-lf-card always, bg-lf-hover on a condition'],
            ['a template literal', "<div class={`bg-lf-card ${active ? 'bg-lf-selected' : ''}`}></div>", 'bg-lf-card always, bg-lf-selected on a condition'],
            ['&&', `<div class="bg-lf-card {active && 'bg-lf-selected'}"></div>`, 'bg-lf-card always, bg-lf-selected on a condition'],
            ['||', `<div class="bg-lf-card {tone || 'bg-lf-panel'}"></div>`, 'bg-lf-card always, bg-lf-panel on a condition'],
            ['??', `<div class="bg-lf-card {tone ?? 'bg-lf-panel'}"></div>`, 'bg-lf-card always, bg-lf-panel on a condition'],
            ['a template nested in a branch, its text', '<div class="bg-lf-card {active ? `bg-lf-panel ${size}` : \'\'}"></div>', 'bg-lf-card always, bg-lf-panel on a condition'],
            ['a template nested in a branch, its ${…}', "<div class=\"bg-lf-card {active ? `px-2 ${strong ? 'bg-lf-selected' : ''}` : ''}\"></div>", 'bg-lf-card always, bg-lf-selected on a condition'],
        ];
        expect(forms.map(([form, source]) => `${form}: ${caught(SVELTE, source).join(' | ')}`)).toEqual(forms.map(([form, , text]) => `${form}: G5 1  ${text}`));
    });

    it('the TabBar regression: a template followed by .trim() is read ${…} by ${…}, so the two branches of its ternary are one condition, not two always-on colours', () => {
        // TabBar writes a tab's classes as a template followed by a method. Read whole, that expression does not branch
        // — its `?` sit inside the template — and an earlier reading took every class in it as always on, both branches
        // of the ternary included: `text-lf-link always, text-lf-muted always`, on a tab written right. Each `${…}` of a
        // template is now judged on its own, whatever follows the template. The positive control is the next test.
        const tab = "`px-3 ${fill ? 'flex-1' : ''} ${active ? 'text-lf-link bg-lf-selected' : 'text-lf-muted hover:bg-lf-hover'}`.trim()";
        const source = `<button class={${tab}}></button>`;
        const tags = [...startTags(markupOf(codeOf(SVELTE, source)))].map(({tag, attributes}) => [tag, ...attributes.map(({name, value}) => `${name}=${value}`)]);
        expect(tags, 'the button is read whole, its class expression intact: the silence is not a tag the parser lost').toEqual([['button', `class=${tab}`]]);
        expect(caught(SVELTE, source)).toEqual([]);
    });

    it('reads a template followed by a method as a lone template: an always-on role in its text and a conditional one in its ${…} fire', () => {
        const fires = ['G5 1  text-lf-primary always, text-lf-link on a condition'];
        expect(caught(SVELTE, "<button class={`text-lf-primary ${active ? 'text-lf-link' : ''}`.trim()}></button>")).toEqual(fires);
        expect(caught(SVELTE, "<button class={`text-lf-primary ${active ? 'text-lf-link' : ''}`}></button>"), 'the lone template').toEqual(fires);
    });

    it('compares one variant chain on one colour utility: base, hover:, md: and focus: are four chains, border and border-t two utilities; hover: against hover: fires', () => {
        expect(caught(SVELTE, `<div class="bg-lf-card hover:bg-lf-hover md:bg-lf-panel {open ? 'focus:bg-lf-selected' : ''}"></div>`), 'four variant chains').toEqual([]);
        expect(caught(SVELTE, '<input class="border border-lf-input aria-invalid:border-lf-danger bg-lf-field text-lf-primary" />'), 'a state written as a variant, the way to beat a colour a caller passes in').toEqual([]);
        expect(caught(SVELTE, `<div class="border border-lf-input {open ? 'border-t-lf-focus ring-lf-focus' : ''}"></div>`), 'other colour utilities').toEqual([]);
        expect(caught(SVELTE, `<div class="hover:bg-lf-hover {open ? 'hover:bg-lf-panel' : ''}"></div>`), 'one variant chain').toEqual(['G5 1  hover:bg-lf-hover always, hover:bg-lf-panel on a condition']);
    });

    it('counts an opacity as another class: bg-lf-card always and bg-lf-card/50 on a condition fire', () => {
        expect(caught(SVELTE, `<div class="bg-lf-card {dimmed ? 'bg-lf-card/50' : ''}"></div>`)).toEqual(['G5 1  bg-lf-card always, bg-lf-card/50 on a condition']);
        expect(caught(SVELTE, `<div class="bg-lf-card {selected ? 'bg-lf-card' : ''}"></div>`), 'the same class on a condition is no second colour').toEqual([]);
    });

    it('never compares two conditions, which may exclude each other, and compares each with what is always on', () => {
        expect(caught(SVELTE, `<div class="{a ? 'bg-lf-card' : ''} {b ? 'bg-lf-panel' : ''}" class:bg-lf-hover={c}></div>`)).toEqual([]);
        expect(caught(SVELTE, `<div class="bg-lf-card {b ? 'bg-lf-panel' : ''}" class:bg-lf-hover={c}></div>`), 'the first condition always on').toEqual(['G5 1  bg-lf-card always, bg-lf-panel on a condition', 'G5 1  bg-lf-card always, bg-lf-hover on a condition']);
    });

    it("reads the file's UPPER_CASE string constant as its value, in a {…} of the class and in a template", () => {
        const script = "<script>\n    const BASE = 'px-2 bg-lf-card';\n</script>\n\n";
        const fires = ['G5 5  bg-lf-card always, bg-lf-panel on a condition'];
        expect(caught(SVELTE, `${script}<div class="{BASE} {open ? 'bg-lf-panel' : ''}"></div>`)).toEqual(fires);
        expect(caught(SVELTE, script + "<div class={`${BASE} ${open ? 'bg-lf-panel' : ''}`}></div>"), 'in a template').toEqual(fires);
    });

    it('reads an UPPER_CASE string constant imported from a module of src: through $lib/, ./ and ../, from a .ts, a .js or an index, under an alias', () => {
        const MODULE = "export const BASE = 'rounded bg-lf-card';";
        const imported = (specifier: string, names = 'BASE', used = 'BASE'): string => `<script>\n    import {${names}} from '${specifier}';\n</script>\n\n<div class="{${used}} {open ? 'bg-lf-panel' : ''}"></div>`;
        const forms: ReadonlyArray<readonly [string, string, Record<string, string>]> = [
            ['$lib/ui, a .ts module', imported('$lib/ui'), {'lib/ui.ts': MODULE}],
            ['$lib/ui, a .js module', imported('$lib/ui'), {'lib/ui.js': MODULE}],
            ['$lib/ui, its index.ts', imported('$lib/ui'), {'lib/ui/index.ts': MODULE}],
            ['$lib/ui, its index.js', imported('$lib/ui'), {'lib/ui/index.js': MODULE}],
            ['$lib/ui, under an alias', imported('$lib/ui', 'BASE as TILE', 'TILE'), {'lib/ui.ts': MODULE}],
            ['./styles', imported('./styles'), {'lib/components/x/styles.ts': MODULE}],
            ['./styles.js, a .ts module', imported('./styles.js'), {'lib/components/x/styles.ts': MODULE}],
            ['../shared/styles', imported('../shared/styles'), {'lib/components/shared/styles.ts': MODULE}],
            ['one name of several', imported('./styles', 'RADIUS, BASE'), {'lib/components/x/styles.ts': `export const RADIUS = 'rounded-md';\n${MODULE}`}],
        ];
        expect(forms.map(([form, source, modules]) => `${form}: ${caught(SVELTE, source, modules).join(' | ')}`)).toEqual(forms.map(([form]) => `${form}: G5 5  bg-lf-card always, bg-lf-panel on a condition`));

        const field = `<script>\n    import {INPUT as FIELD} from '$lib/ui';\n</script>\n\n<input class="{FIELD} {invalid ? 'border-lf-danger' : ''}" placeholder="Name" />`;
        const ui = {'lib/ui.ts': "export const INPUT = 'border border-lf-input bg-lf-field text-lf-primary placeholder:text-lf-placeholder';"};
        expect(caught(SVELTE, field, ui), 'the error border of a field whose idle classes come from a shared constant').toEqual(['G5 5  border-lf-input always, border-lf-danger on a condition']);
    });

    it('reads no import whose module it is not given: a module absent from `modules`, one of another path, a bare specifier', () => {
        const source = `<script>\n    import {BASE} from './styles';\n    import {TONE} from 'tones';\n</script>\n\n<div class="{BASE} {TONE} {open ? 'bg-lf-panel' : ''}"></div>`;
        const MODULE = "export const BASE = 'rounded bg-lf-card';";
        expect(caught(SVELTE, source), 'no module given').toEqual([]);
        expect(caught(SVELTE, source, {'lib/components/x/other.ts': MODULE, 'tones.ts': "export const TONE = 'bg-lf-card';"}), 'a module of another path, and a bare specifier: a package, never a file of src').toEqual([]);
        expect(caught(SVELTE, source, {'lib/components/x/styles.ts': MODULE}), 'its module given (positive control)').toEqual(['G5 6  bg-lf-card always, bg-lf-panel on a condition']);
    });

    it('the two-letter constant regression: TH, local or imported as the PAC planner imports it from its ui.ts, is read as its value', () => {
        // The scanner recorded UPPER_CASE constants of any length but looked up only names of three letters or more:
        // the PAC planner's TH and TD (planner/ui.ts) carry role classes, and an element naming one was read without
        // them. A name is now looked up at any length.
        const th = `<th scope="col" class="{TH} {sorted ? 'text-lf-link' : ''}"></th>`;
        const fires = ['G5 5  text-lf-muted always, text-lf-link on a condition'];
        expect(caught(SVELTE, `<script>\n    const TH = 'px-3 py-2 text-lf-muted';\n</script>\n\n${th}`), 'local').toEqual(fires);
        const ui = {'lib/features/x/ui.ts': "export const TABLE = 'w-full text-sm';\nexport const TH = 'px-3 py-2 text-left text-xs text-lf-muted';\nexport const TD = 'px-3 py-2 align-top text-lf-primary';"};
        expect(caught('lib/features/x/steps/Dialog.svelte', `<script>\n    import {TABLE, TH} from '../ui';\n</script>\n\n${th}`, ui), "imported from '../ui'").toEqual(fires);
    });

    it('takes optional chaining, `?.`, for no branch: an expression with it alone keeps its strings always on, and a `?` after it still branches', () => {
        expect(caught(SVELTE, '<div class="bg-lf-card {item?.cls}"></div>'), 'no string to compare').toEqual([]);
        expect(caught(SVELTE, `<div class="bg-lf-card {[item?.cls, 'bg-lf-panel'].join(' ')}"></div>`), 'its strings, always on').toEqual(['G5 1  bg-lf-card always, bg-lf-panel always']);
        expect(caught(SVELTE, `<div class="bg-lf-card {item?.active ? 'bg-lf-panel' : ''}"></div>`), 'a ternary after it').toEqual(['G5 1  bg-lf-card always, bg-lf-panel on a condition']);
    });

    it("reports the line of the start tag's `<`, whatever line its classes sit on", () => {
        const source = ['<p>intro</p>', '<div', '    id="panel"', '    class="border border-lf-input"', '    class:border-lf-focus={open}', '></div>'].join('\n');
        expect(caught(SVELTE, source)).toEqual(['G5 2  border-lf-input always, border-lf-focus on a condition']);
    });

    it('reads elements only: the same classes in a .ts module are no element', () => {
        expect(caught('lib/utils/sample.ts', "export const tile = 'bg-lf-card bg-lf-panel';\nexport const ring = `border-lf-input ${open ? 'border-lf-focus' : ''}`;")).toEqual([]);
        expect(caught(SVELTE, '<div class="bg-lf-card bg-lf-panel"></div>'), 'the same classes on an element (positive control)').toEqual(['G5 1  bg-lf-card always, bg-lf-panel always']);
    });
});

/**
 * G6, a native field on roles names its text (the skill design-system: «A native field names its text and its
 * placeholder»). app.css colours the text and the placeholder of a native field in dark only while it carries no role
 * utility, `html.dark input:where(:not([class*='-lf-']))`: a migrated field falls back to the preflight, the inherited
 * colour and a placeholder at half of it. So an `<input>`, a `<textarea>` or a `<select>` — lower case: `<Input>` is a
 * component — that carries a `-lf-` class in any branch writes a base text role, `text-lf-…` under no variant, and a
 * placeholder role, `placeholder:text-lf-…`, when it has a placeholder: the attribute or the `{placeholder}` shorthand.
 * A select has no placeholder to colour. An input whose literal type has no text of its own, `FIELD_TYPES_WITHOUT_TEXT`,
 * is exempt, `type={'checkbox'}` included; a dynamic type is checked. The text names what is missing, on the line of
 * the field's `<`.
 */
describe('G6, a native field on roles names its text, on synthetic sources', () => {
    const SVELTE = 'lib/components/x/Sample.svelte';
    const NAMES = new Set(['field', 'input', 'primary', 'muted', 'placeholder', 'danger', 'checked']);
    const caught = (rel: string, text: string, modules: Record<string, string> = {}): string[] => grammarOf(rel, text, NAMES, modules).map((g) => `${g.rule} ${g.line}  ${g.text}`);

    it('an input on roles with no text role and a {placeholder} shorthand fires both; the attribute is a placeholder too', () => {
        expect(caught(SVELTE, '<input type="text" class="bg-lf-field border border-lf-input" {placeholder} />')).toEqual(['G6 1  <input> no text role, no placeholder role']);
        expect(caught(SVELTE, '<input class="bg-lf-field border border-lf-input text-lf-primary" placeholder="Search" />'), 'the attribute, the text role written').toEqual(['G6 1  <input> no placeholder role']);
        expect(caught(SVELTE, '<input class="bg-lf-field border border-lf-input" />'), 'no placeholder: the text role alone is due').toEqual(['G6 1  <input> no text role']);
        expect(caught(SVELTE, '<input class="bg-lf-field border border-lf-input text-lf-primary placeholder:text-lf-placeholder" placeholder={label} />'), 'both written').toEqual([]);
    });

    it('exempts every type of FIELD_TYPES_WITHOUT_TEXT, in any case, and checks every type with a text of its own', () => {
        expect(FIELD_TYPES_WITHOUT_TEXT, 'the types with no text of their own: iterated below, an emptied list would let the exemption pass in silence').toEqual(expect.arrayContaining(['checkbox', 'radio', 'range', 'file', 'hidden', 'color', 'submit', 'button', 'reset', 'image']));
        const field = (type: string): string => `<input type="${type}" class="bg-lf-field border border-lf-input" {placeholder} />`;
        const exempt = FIELD_TYPES_WITHOUT_TEXT.flatMap((type) => [type, type.toUpperCase(), type.charAt(0).toUpperCase() + type.slice(1)]);
        expect(
            exempt.filter((type) => caught(SVELTE, field(type)).length > 0),
            'exempt types that fire',
        ).toEqual([]);
        const withText = ['text', 'search', 'email', 'password', 'number', 'date', 'tel', 'url'];
        expect(
            withText.map((type) => `${type}: ${caught(SVELTE, field(type)).join(' | ')}`),
            'the types with a text of their own (positive control)',
        ).toEqual(withText.map((type) => `${type}: G6 1  <input> no text role, no placeholder role`));
    });

    it("reads a lone string literal as a literal type, type={'checkbox'}; a dynamic type is checked", () => {
        expect(caught(SVELTE, `<input type={'checkbox'} class="accent-lf-checked" />\n<input type={"radio"} class="accent-lf-checked" />`)).toEqual([]);
        expect(caught(SVELTE, `<input type={revealed ? 'text' : 'password'} class="bg-lf-field border border-lf-input" />`), 'a password field with its eye').toEqual(['G6 1  <input> no text role']);
        expect(caught(SVELTE, '<input {type} class="bg-lf-field border border-lf-input" />'), 'the {type} shorthand').toEqual(['G6 1  <input> no text role']);
    });

    it('a textarea writes its text role, and its placeholder role when it has a placeholder', () => {
        expect(caught(SVELTE, '<textarea class="bg-lf-field text-lf-primary placeholder:text-lf-placeholder" placeholder="Notes"></textarea>')).toEqual([]);
        expect(caught(SVELTE, '<textarea class="bg-lf-field text-lf-primary"></textarea>'), 'no placeholder').toEqual([]);
        expect(caught(SVELTE, '<textarea class="bg-lf-field text-lf-primary" placeholder="Notes"></textarea>')).toEqual(['G6 1  <textarea> no placeholder role']);
        expect(caught(SVELTE, '<textarea class="bg-lf-field" {placeholder}></textarea>')).toEqual(['G6 1  <textarea> no text role, no placeholder role']);
    });

    it('a select writes its text role, and never needs a placeholder role', () => {
        expect(caught(SVELTE, '<select class="bg-lf-field border border-lf-input"></select>')).toEqual(['G6 1  <select> no text role']);
        expect(caught(SVELTE, '<select class="bg-lf-field border border-lf-input" {placeholder}></select>'), 'a placeholder adds nothing').toEqual(['G6 1  <select> no text role']);
        expect(caught(SVELTE, '<select class="bg-lf-field border border-lf-input text-lf-primary" placeholder="Pick one"></select>')).toEqual([]);
    });

    it('leaves a field with no role utility to app.css: a legacy field, and a field with no class, are silent', () => {
        expect(caught(SVELTE, '<input class="bg-white text-gray-900 border-gray-300" placeholder="Name" />\n<textarea class="bg-white"></textarea>\n<select class="bg-white"></select>')).toEqual([]);
        expect(caught(SVELTE, '<input placeholder="Name" />\n<textarea {placeholder}></textarea>\n<select></select>'), 'no class at all').toEqual([]);
        expect(caught(SVELTE, '<input class="bg-lf-field border border-lf-input" placeholder="Name" />'), 'the same field on roles (positive control)').toEqual(['G6 1  <input> no text role, no placeholder role']);
    });

    it('a role in any branch puts a field on roles: a class: directive, or a conditional {…}, alone', () => {
        expect(caught(SVELTE, '<input class="px-2" class:border-lf-danger={invalid} />')).toEqual(['G6 1  <input> no text role']);
        expect(caught(SVELTE, `<input class="px-2 {invalid ? 'border-lf-danger' : ''}" {placeholder} />`)).toEqual(['G6 1  <input> no text role, no placeholder role']);
    });

    it('a text role under a variant only is no text role, and neither is the placeholder role', () => {
        expect(caught(SVELTE, '<input class="bg-lf-field hover:text-lf-primary focus:text-lf-primary" />')).toEqual(['G6 1  <input> no text role']);
        expect(caught(SVELTE, '<input class="bg-lf-field placeholder:text-lf-placeholder" placeholder="Name" />'), 'the placeholder role').toEqual(['G6 1  <input> no text role']);
    });

    it('takes a placeholder role under any variants, focus:placeholder:text-lf-muted included; a focus: text role is none', () => {
        expect(caught(SVELTE, '<input class="bg-lf-field text-lf-primary focus:placeholder:text-lf-muted" placeholder="Name" />')).toEqual([]);
        expect(caught(SVELTE, '<input class="bg-lf-field text-lf-primary focus:text-lf-muted" placeholder="Name" />'), 'positive control').toEqual(['G6 1  <input> no placeholder role']);
    });

    it('reads the roles from an imported constant, as the PAC planner writes its fields (INPUT of its ui.ts)', () => {
        const EDITOR = 'lib/features/x/steps/Editor.svelte';
        const source = `<script>\n    import {BUTTON, INPUT} from '../ui';\n</script>\n\n<input class={INPUT} placeholder="Name" />\n<input class="{INPUT} text-right" placeholder="Ticker" />`;
        const ui = (input: string): Record<string, string> => ({'lib/features/x/ui.ts': `export const BUTTON = 'rounded-lg px-3 py-2';\nexport const INPUT = '${input}';`});
        expect(caught(EDITOR, source, ui('w-full border border-lf-input bg-lf-field text-lf-primary placeholder:text-lf-placeholder'))).toEqual([]);
        expect(caught(EDITOR, source, ui('w-full border border-lf-input bg-lf-field')), 'the constant without its text roles (positive control)').toEqual(['G6 5  <input> no text role, no placeholder role', 'G6 6  <input> no text role, no placeholder role']);
    });

    it('the two-letter constant regression: a field whose text and placeholder roles come from IN alone is silent', () => {
        // The aria-invalid border puts the field on roles whatever IN gives: with its class reduced to {IN}, a constant
        // the scanner could not read would leave the field silent as well, for the wrong reason. Before names of two
        // letters were looked up, this field was reported with no text role and no placeholder role.
        const field = (roles: string): string => `<script>\n    const IN = '${roles}';\n</script>\n\n<input class="{IN} aria-invalid:border-lf-danger" placeholder="Name" />`;
        expect(caught(SVELTE, field('bg-lf-field text-lf-primary placeholder:text-lf-placeholder'))).toEqual([]);
        expect(caught(SVELTE, field('bg-lf-field')), 'IN without its text roles (positive control)').toEqual(['G6 5  <input> no text role, no placeholder role']);
    });

    it('takes a component for no native field: <Input>, <TextArea> and <Select> are silent', () => {
        expect(caught(SVELTE, '<Input class="bg-lf-field" {placeholder} />\n<TextArea class="bg-lf-field" {placeholder} />\n<Select class="bg-lf-field" />')).toEqual([]);
        expect(caught(SVELTE, '<input class="bg-lf-field" {placeholder} />\n<textarea class="bg-lf-field" {placeholder}></textarea>\n<select class="bg-lf-field"></select>'), 'the native fields (positive control)').toEqual([
            'G6 1  <input> no text role, no placeholder role',
            'G6 2  <textarea> no text role, no placeholder role',
            'G6 3  <select> no text role',
        ]);
    });

    it("reports on the line of the field's `<`, beside G5 on the same element", () => {
        const source = ['<label>', '    <input', '        type="text"', '        class="border border-lf-input bg-lf-field"', '        class:border-lf-danger={invalid}', '        {placeholder}', '    />', '</label>'].join('\n');
        expect(caught(SVELTE, source)).toEqual(['G5 2  border-lf-input always, border-lf-danger on a condition', 'G6 2  <input> no text role, no placeholder role']);
    });
});

// ---------------------------------------------------------------------------
// C'. Comments inside markup expressions: the AF lot 8 regression
// ---------------------------------------------------------------------------

/**
 * The AF lot 8 regression. codeOf blanked the comments of the scripts, of the styles and of the markup, not those inside
 * the markup's `{…}` expressions. In `routes/(app)/assets/+page.svelte` a line comment inside an attribute expression,
 * `onfitperiod={(range) => { // the picker's … }}`, kept its apostrophe and its backticks, and the scanner read them as
 * quotes: the attribute value swallowed the markup after it. G3 fired on the attribute line, which holds no class, and
 * the swallowed elements were never checked one by one — in four files of the tree the scanner read only part of the
 * markup, `AssetSetRiskPanel.svelte` 3 start tags of 56. m1 counted the classes such a comment names, too.
 *
 * codeOf now blanks the line and block comments of every markup expression as it does a script's, the closing `}` found
 * past strings and comments; the script and style blocks keep their own handling. A comment becomes spaces and keeps
 * its newlines: offsets and line numbers do not move.
 */
describe('codeOf, the AF lot 8 regression: a comment inside an attribute expression swallowed the markup after it', () => {
    const SVELTE = 'lib/components/x/Sample.svelte';
    const NAMES = new Set(['card', 'primary', 'link']);
    const caught = (text: string): string[] => grammarOf(SVELTE, text, NAMES).map((g) => `${g.rule} ${g.line}  ${g.text}`);
    /** The one element that mixes a role with a legacy class: line 9 of SOURCE, after the comment. */
    const MIXED = '<div class="bg-lf-card text-gray-500">mixed</div>';
    /** The AF shape: a comment with an apostrophe and backticks inside an attribute expression, then markup to check. */
    const SOURCE = [
        '<script>',
        "    let x = 1; // a script comment's `tick`",
        '</script>',
        '',
        '<Panel onfitperiod={(range) => {',
        "    // the picker's `activePreset` decides, text-gray-500 here is a comment",
        '    apply(range);',
        '}} />',
        MIXED,
        '<div class="bg-lf-card text-lf-primary">roles</div>',
        '<a href={\'https://example.com/x\'} class="text-lf-link">a URL with // inside a string</a>',
        "<p>{/* a block comment's `b` */ value}</p>",
        '<span class="text-red-500">legacy</span>',
        '',
    ].join('\n');
    /** The lines codeOf changed, as `N: what is left of it`, its blanks collapsed. */
    const changedLines = (text: string, code: string): string[] => {
        const lines = text.split('\n');
        return code.split('\n').flatMap((line, i) => (line === lines[i] ? [] : [`${i + 1}: ${line.replace(/\s+/g, ' ').trim() || '(blank)'}`]));
    };

    it('G3 fires once, on the mixed element after the comment, never on the attribute that holds the comment; m1 counts the markup, not a class the comment names', () => {
        expect(caught(SOURCE), 'line 5, the attribute, holds no class: the old scanner reported it, with the markup it had swallowed').toEqual(['G3 9  bg-lf-card text-gray-500']);
        expect(measureSource(SVELTE, SOURCE), 'text-gray-500 on line 9 and text-red-500 on line 13, not the text-gray-500 of the comment').toEqual({m1: 2, m2: []});
    });

    it('the blind spot closed: every element after the comment is read on its own, so the mixed one is reported as itself and the others pass', () => {
        const tags = [...startTags(markupOf(codeOf(SVELTE, SOURCE)))].map(({tag, index}) => `${tag} ${lineAt(SOURCE, index)}`);
        expect(tags, 'the old scanner read two, the script and the Panel, whose attribute held all the rest').toEqual(['script 1', 'Panel 5', 'div 9', 'div 10', 'a 11', 'p 12', 'span 13']);
        expect(caught(SOURCE.replace(`${MIXED}\n`, '')), 'without the mixed element, no G3: each element after the comment is right on its own, where the old scanner reported line 5').toEqual([]);
    });

    it("codeOf blanks a markup expression's comments as it does a script's: the same length and line breaks, the strings and the markup text kept", () => {
        const code = codeOf(SVELTE, SOURCE);
        const lineLengths = (text: string): number[] => text.split('\n').map((line) => line.length);
        expect(code.length, 'the same length').toBe(SOURCE.length);
        expect(lineLengths(code), 'the same line breaks: offsets and line numbers do not move').toEqual(lineLengths(SOURCE));
        expect(code, 'the comment of the attribute expression').not.toContain("picker's");
        expect(code, 'a string of an expression, its // included').toContain("href={'https://example.com/x'}");
        expect(changedLines(SOURCE, code), "line 2 the script's comment, as before; line 6 the attribute expression's; line 12 the text expression's; nothing else, not the // of the link's text").toEqual(['2: let x = 1;', '6: (blank)', '12: <p>{ value}</p>']);
    });

    it('codeOf leaves the script and style blocks to their own handling: a brace in a script string or in a CSS rule opens no expression', () => {
        const blocks = ['<script>', "    const open = '{', home = 'https://example.com'; // it's home", '</script>', '', '<style>', "    .hero { background: url(https://example.com/x.png); } /* it's */", '</style>', ''].join('\n');
        expect(changedLines(blocks, codeOf(SVELTE, blocks)), 'only the comments go: read as an expression, either block would lose the // of its URL').toEqual(["2: const open = '{', home = 'https://example.com';", '6: .hero { background: url(https://example.com/x.png); }']);
    });

    it('a block comment inside a text expression is blanked too, and measures nothing', () => {
        const comment = '/* was text-gray-500 on #ff0000 */';
        const text = `<p>{${comment} value}</p>`;
        expect(codeOf(SVELTE, text)).toBe(`<p>{${' '.repeat(comment.length)} value}</p>`);
        expect(measureSource(SVELTE, text)).toEqual({m1: 0, m2: []});
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
        expect(sources).toEqual(expect.arrayContaining(['routes/+layout.svelte', 'routes/+error.svelte', 'lib/utils/colors.ts', 'lib/features/support/supportLinks.ts']));
        expect(sources.filter((rel) => /\.(test|spec)\.ts$|(^|\/)__(tests|mocks)__\/|\.d\.ts$/.test(rel))).toEqual([]);
        expect(scan.sources, 'the scan reads what the walk lists').toEqual(sources);
    });

    it('measures each metric while the baseline still records it, with no floor on how much is left (positive control)', () => {
        // "Nothing rose" is also what a pattern or a filter that suddenly matches nothing would report: the ratchet would
        // pass in silence. How much legacy colour is left is not the question: it falls wave after wave, down to zero at
        // the clean-up, so there is no floor here and no ratio to the baseline (one lot legitimately moved 95% of the
        // literals into lib/theme/ between two tightenings). The clean-up empties the baseline in the same change: while
        // the baseline still records a metric, a scan that measures none of it is blind, not finished.
        const recordedTotals = totalsOf(readBaseline().files.values());
        const scannedTotals = totalsOf(scan.files.values());
        const metrics = [
            ['m1', 'legacy colour classes'],
            ['m2', 'colour literals'],
        ] as const;
        const blind = metrics
            .filter(([metric]) => recordedTotals[metric] > 0 && !(scannedTotals[metric] > 0))
            .map(
                ([metric, what]) =>
                    `${metric}, the ${what}: a scan that measures ${scannedTotals[metric]} while the baseline still records ${recordedTotals[metric]} is a broken pattern or filter of frontend/scripts/theme/theme-roles.mjs, not a finished migration: the clean-up empties the baseline in the same change.`,
            );
        expect(blind, 'the scan is blind to a metric the baseline still records').toEqual([]);
    });

    it('R1–R4: no total and no file rose above src/themeRoles.baseline.tsv', () => {
        expect(existsSync(BASELINE), `${relative(FRONTEND_DIR, BASELINE)} is missing: the first baseline is written by node frontend/scripts/theme/theme-roles.mjs --init`).toBe(true);
        const {violations} = compareWithBaseline(scan, readBaseline());
        const offenders = violations.map((v) => `${v.rule} ${v.metric}  ${v.file ?? '(total)'}${v.from && v.from !== v.file ? ` (was ${v.from})` : ''}: ${v.detail}`);
        expect(offenders, ['', ...RATCHET_FIX, '', `${offenders.length} violation(s):`, '', ...offenders, ''].join('\n  ')).toEqual([]);
    });

    it('G1–G6: every role utility of the tree is written right', () => {
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
