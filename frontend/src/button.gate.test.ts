/**
 * @vitest-environment node
 *
 * Standard button — a gate over the source (project 85, BTN-0), not a test of behaviour.
 *
 * The app moves, area by area, from hand-written `<button>` elements to the standard `Button`
 * (`lib/components/ui/button/`). `scripts/button/button-ratchet.mjs` counts what is left of the old way in every
 * production source and holds it to `src/button.baseline.tsv`:
 *   B1  a file never rises above its line (absent: 0) plus its exception allowance: a new hand-written button fails;
 *   B2  a drop passes and is reported; `--update` tightens the baseline and never widens it;
 *   B4  the `class` of a `<Button>` / `<CloseButton>` carries size and position only, never a colour utility.
 *
 * The synthetic controls come first: a gate whose detector misses a button, or counts a comment, would read green on
 * a tree it never measured.
 */
import {describe, expect, it} from 'vitest';
import {compareWithBaseline, measureSource, readBaseline, scanTree, tightenBaseline} from '../scripts/button/button-ratchet.mjs';

type Measure = ReturnType<typeof measureSource>;

const svelte = (markup: string, script = '') => (script ? `<script lang="ts">\n${script}\n</script>\n\n${markup}` : markup);

describe('measureSource — what counts as a hand-written button', () => {
    it('counts a <button> element of the markup, on its line', () => {
        const measure = measureSource('lib/x/Probe.svelte', '<div>\n<button type="button">Go</button>\n</div>');
        expect(measure.count).toBe(1);
        expect(measure.lines).toEqual([2]);
    });

    it('counts a <button written inside a string of the <script> (a button built as HTML for a table cell)', () => {
        const measure = measureSource('lib/x/Probe.svelte', svelte('<div></div>', '    const cell = \'<button class="x">Go</button>\';'));
        expect(measure.count).toBe(1);
    });

    it('does not count a <button> inside an HTML comment or a script comment', () => {
        const source = svelte('<!-- <button>old</button> -->\n<div></div>', "    // <button> was here\n    /* '<button>' */\n    const x = 1;");
        expect(measureSource('lib/x/Probe.svelte', source).count).toBe(0);
    });

    it('counts a <button inside a string of a .ts file, not inside its comments', () => {
        expect(measureSource('lib/x/cell.ts', 'export const cell = () => \'<button type="button">x</button>\';').count).toBe(1);
        expect(measureSource('lib/x/cell.ts', "// '<button>'\nexport const cell = () => '<span>x</span>';").count).toBe(0);
    });

    it('does not count a standard <Button> component as a hand-written button', () => {
        const measure = measureSource('lib/x/Probe.svelte', svelte('<Button label="Go" />', "    import {Button} from '$lib/components/ui/button';"));
        expect(measure.count).toBe(0);
    });
});

describe('measureSource — the class of a Button carries no colour (B4)', () => {
    const colours = (cls: string, tag = 'Button'): Measure['colourClasses'] => measureSource('lib/x/Probe.svelte', svelte(`<${tag} label="Go" class="${cls}" />`)).colourClasses;

    it.each(['w-full', 'ml-auto shrink-0', 'text-sm', 'border', 'shadow-lg', 'w-full text-sm sm:w-auto'])('passes size and position only: class="%s"', (cls) => {
        expect(colours(cls)).toEqual([]);
    });

    it.each(['bg-lf-card', 'text-gray-500', 'hover:text-lf-primary', 'border-lf-danger-line', 'bg-[#123456]', 'text-white'])('flags a colour utility: class="%s"', (cls) => {
        const hits = colours(cls);
        expect(hits).toHaveLength(1);
        expect(hits[0].value).toContain(cls.replace(/^.*:/, '').slice(0, 4));
        expect(hits[0].line).toBe(1);
    });

    it('reads the class of a CloseButton too, and never the class of an HTML element', () => {
        expect(colours('bg-lf-card', 'CloseButton')).toHaveLength(1);
        expect(measureSource('lib/x/Probe.svelte', '<div class="bg-lf-card"></div>').colourClasses).toEqual([]);
    });
});

describe('the tree', () => {
    // It parses every production component with the Svelte compiler: well over the default 5 s on a busy machine.
    it('has no file above its baseline and no colour in the class of a Button', () => {
        const scan = scanTree();
        // Presence barrier: the scan read the tree. The standard button itself holds the one allowed <button>.
        expect(scan.get('lib/components/ui/button/Button.svelte')?.count, 'the scan must see the <button> of Button.svelte').toBe(1);

        const {rises, drops, colours} = compareWithBaseline(scan, readBaseline());
        for (const drop of drops) console.info(`button ratchet: ${drop.file} ${drop.recorded} → ${drop.count} (tighten with: node frontend/scripts/button/button-ratchet.mjs --update)`);
        expect(
            rises.map((rise) => `${rise.file}: ${rise.count} hand-written <button>, allowed ${rise.allowed} (lines ${rise.lines.join(', ')})`),
            'a new hand-written <button>: use Button from $lib/components/ui/button (a drop is tightened with `node frontend/scripts/button/button-ratchet.mjs --update`, never by raising a line)',
        ).toEqual([]);
        expect(
            colours.map((hit) => `${hit.file}:${hit.line} «${hit.value}»`),
            'the class of a Button takes size and position only: its colours live in buttonClasses()',
        ).toEqual([]);
    }, 60_000);
});

describe('tightenBaseline — never widens', () => {
    const scanOf = (entries: [string, number][]) => new Map(entries.map(([file, count]) => [file, {count, lines: [], colourClasses: []}]));

    it('lowers a line to what dropped, keeps a line that rose, and drops a file that reached zero', () => {
        const baseline = new Map([
            ['lib/a.svelte', {count: 3}],
            ['lib/b.svelte', {count: 2, reason: 'taken as it is'}],
            ['lib/c.svelte', {count: 1}],
        ]);
        const next = tightenBaseline(
            scanOf([
                ['lib/a.svelte', 1],
                ['lib/b.svelte', 5],
                ['lib/new.svelte', 4],
            ]),
            baseline,
        );
        expect(next.get('lib/a.svelte')).toEqual({count: 1});
        expect(next.get('lib/b.svelte'), 'a rise is the gate’s failure, never a wider line').toEqual({count: 2, reason: 'taken as it is'});
        expect(next.has('lib/c.svelte'), 'a file with no button left leaves the baseline').toBe(false);
        expect(next.has('lib/new.svelte'), 'a file with no line never gets one').toBe(false);
    });

    it('subtracts the exception allowance before comparing (the one <button> of Button.svelte is not debt)', () => {
        const next = tightenBaseline(scanOf([['lib/components/ui/button/Button.svelte', 1]]), new Map([['lib/components/ui/button/Button.svelte', {count: 1}]]));
        expect(next.has('lib/components/ui/button/Button.svelte')).toBe(false);
    });
});
