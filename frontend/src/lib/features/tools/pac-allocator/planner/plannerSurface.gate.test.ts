/**
 * The planner's surface gate (F1 of project 67, step 2): the PAC keeps every test id, table `storageKey`, DOM id,
 * chart id, event name and correlation prefix it had before the planner became common to two Tools.
 *
 * What it reads. Every product source of the planner folder (`.svelte`, `.ts`; no test, no `profile.ts`, which only
 * defines the profile), its comments removed, in all the forms a value can take before and after the lot:
 *   - a literal: `pac-planner`, `pac-planner-continue`, `pac-planner-step-${step}`;
 *   - a call of the profile with a literal argument: `testId('continue', profile)`, `storageKey('targets', profile)`,
 *     `domId('step-title', profile)` → `pac-planner-continue`, …;
 *   - a member of the profile, read as the PAC profile's value: `.testIdPrefix` → `pac-planner`,
 *     `.events.completed` / `.events.failed` → `tool.pac-plan.completed` / `.failed`, `.correlationPrefix` → `pac-rev`;
 *   - an event or correlation literal: `tool.pac-plan.completed`, `pac-rev-`.
 * The `${…}` of a template and the `{…}` of a Svelte attribute are kept as written (spaces removed, both as `${…}`), so
 * `pac-planner-ledger-${field}`, `"pac-planner-section-{id}-title"` and `testId(\`section-${id}-title\`, profile)` read
 * the same. A test id built on a `testid` variable (`{testid}-row`, `${testid}-row`: the 81 «derived» ids) is counted
 * apart, by its suffix: its root is the literal or the call that sets the variable. Every value is counted, so a value
 * lost in one place and written twice in another is seen.
 *
 * **Frozen.** From step 2 to the seal neither this file nor `plannerSurface.baseline.json` changes (plan F1, «Fatto
 * quando» 1): a red here is a change of the PAC's DOM, to undo, never a reference to update.
 */
import {readFileSync, readdirSync} from 'node:fs';
import {join, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

const PLANNER_DIR = fileURLToPath(new URL('.', import.meta.url));
const BASELINE = join(PLANNER_DIR, 'plannerSurface.baseline.json');

const REBALANCER_BASELINE = join(PLANNER_DIR, 'plannerSurface.rebalancer.baseline.json');

/** The values a profile gives the calls and members it reads: the PAC's, or the Rebalancer's (F3a of project 67). */
interface SurfaceProfile {
    prefix: string;
    events: Record<string, string>;
    correlation: string;
}

const PAC: SurfaceProfile = {prefix: 'pac-planner', events: {completed: 'tool.pac-plan.completed', failed: 'tool.pac-plan.failed'}, correlation: 'pac-rev'};
const REBALANCER: SurfaceProfile = {prefix: 'rebalancer-planner', events: {completed: 'tool.rebalancer-plan.completed', failed: 'tool.rebalancer-plan.failed'}, correlation: 'reb-rev'};
const EVENTS = PAC.events;
const CORRELATION = PAC.correlation;

export interface PlannerSurface {
    ids: Record<string, number>;
    derived: Record<string, number>;
    events: Record<string, number>;
    correlation: Record<string, number>;
}

const BUCKETS = ['ids', 'derived', 'events', 'correlation'] as const;
const SEGMENT = String.raw`(?:[A-Za-z0-9_]|\$?\{[^}]*\})`;
const ID_LITERAL = new RegExp(String.raw`(?<![A-Za-z0-9_$-])pac-planner(?:-${SEGMENT}(?:-|${SEGMENT})*)?`, 'g');
const PROFILE_CALL = /\b(?:testId|storageKey|domId)\(\s*(['"`])((?:\\.|(?!\1)[^\\])*)\1/g;
const PREFIX_MEMBER = /\.testIdPrefix\b/g;
const EVENT_LITERAL = /tool\.pac-plan\.(completed|failed)\b/g;
const EVENT_MEMBER = /\.events\.(completed|failed)\b/g;
const CORRELATION_LITERAL = /(?<![A-Za-z0-9_-])pac-rev-/g;
const CORRELATION_MEMBER = /\.correlationPrefix\b/g;
const DERIVED = new RegExp(String.raw`\$?\{\s*testid\s*\}((?:-|${SEGMENT})+)`, 'g');

/** Comments say nothing about the DOM: block, HTML and whole-line `//` comments are removed before reading. */
function withoutComments(text: string): string {
    return text
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/<!--[\s\S]*?-->/g, '')
        .replace(/^\s*\/\/.*$/gm, '');
}

/** `${ step }`, `${step}` and Svelte's `{step}` are the same template. */
function normalized(value: string): string {
    return value.replace(/\$?\{([^}]*)\}/g, (_match, expression: string) => `\${${expression.replace(/\s+/g, '')}}`);
}

function count(bucket: Record<string, number>, value: string): void {
    bucket[value] = (bucket[value] ?? 0) + 1;
}

/**
 * The surface one source shows, in every form above, under `profile` (the PAC by default): a call or a member of the
 * profile takes that profile's value; a literal is the same under both, since a shared component shows it to both Tools.
 */
export function extractSurface(source: string, profile: SurfaceProfile = PAC): PlannerSurface {
    const text = withoutComments(source);
    const surface: PlannerSurface = {ids: {}, derived: {}, events: {}, correlation: {}};
    for (const match of text.matchAll(ID_LITERAL)) count(surface.ids, normalized(match[0]));
    for (const match of text.matchAll(DERIVED)) count(surface.derived, normalized(`\${testid}${match[1]}`));
    for (const match of text.matchAll(PROFILE_CALL)) count(surface.ids, normalized(`${profile.prefix}-${match[2]}`));
    for (const _match of text.matchAll(PREFIX_MEMBER)) count(surface.ids, profile.prefix);
    for (const match of text.matchAll(EVENT_LITERAL)) count(surface.events, EVENTS[match[1]]);
    for (const match of text.matchAll(EVENT_MEMBER)) count(surface.events, profile.events[match[1]]);
    for (const _match of text.matchAll(CORRELATION_LITERAL)) count(surface.correlation, CORRELATION);
    for (const _match of text.matchAll(CORRELATION_MEMBER)) count(surface.correlation, profile.correlation);
    return surface;
}

function productSources(dir: string): string[] {
    const files: string[] = [];
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) files.push(...productSources(path));
        else if (/\.(svelte|ts)$/.test(entry.name) && !/\.test\.ts$/.test(entry.name) && entry.name !== 'profile.ts') files.push(path);
    }
    return files.sort();
}

function merged(surfaces: PlannerSurface[]): PlannerSurface {
    const total: PlannerSurface = {ids: {}, derived: {}, events: {}, correlation: {}};
    for (const surface of surfaces) {
        for (const bucket of BUCKETS) {
            for (const [value, n] of Object.entries(surface[bucket])) total[bucket][value] = (total[bucket][value] ?? 0) + n;
        }
    }
    for (const bucket of BUCKETS) total[bucket] = Object.fromEntries(Object.entries(total[bucket]).sort(([a], [b]) => a.localeCompare(b)));
    return total;
}

/** The planner's whole surface, read from its sources, under `profile` (the PAC by default). */
export function plannerSurface(profile: SurfaceProfile = PAC): {surface: PlannerSurface; files: string[]} {
    const files = productSources(PLANNER_DIR);
    return {surface: merged(files.map((file) => extractSurface(readFileSync(file, 'utf8'), profile))), files: files.map((file) => relative(PLANNER_DIR, file))};
}

describe('planner surface', () => {
    it('reads every form a value takes, and no comment', () => {
        const source = [
            '<div data-testid="pac-planner-continue" data-other={`pac-planner-step-${ step }`}></div>',
            "<p data-testid={testId('continue', profile)}></p> <DataTable storageKey={storageKey('targets', profile)} />",
            "<h2 id={domId('step-title', profile)}></h2> <i data-testid={testId(`step-${step}`, profile)}></i>",
            '<section data-testid={profile.testIdPrefix}></section> <section data-testid="pac-planner"></section>',
            "notify({name: 'tool.pac-plan.failed'}); notify({name: profile.events.failed}); notify({name: profile.events.completed});",
            'const id = `pac-rev-${revision}`; const other = `${profile.correlationPrefix}-${revision}`;',
            '// pac-planner-commented-out',
            '<!-- data-testid="pac-planner-html-comment" -->',
            "/* testId('block-comment') */",
            'const unrelated = "xpac-planner-not-ours";',
            '<h3 id="pac-planner-section-{ id }-title"></h3> <h3 id={domId(`section-${id}-title`, profile)}></h3>',
            '<p data-testid="{testid}-row"></p> <p data-testid={`${testid}-row`}></p> <p data-testid="{testid}-cell-{index}"></p>',
        ].join('\n');

        expect(extractSurface(source)).toEqual({
            ids: {
                'pac-planner': 2,
                'pac-planner-continue': 2,
                'pac-planner-step-${step}': 2,
                'pac-planner-targets': 1,
                'pac-planner-step-title': 1,
                'pac-planner-section-${id}-title': 2,
            },
            derived: {'${testid}-row': 2, '${testid}-cell-${index}': 1},
            events: {'tool.pac-plan.failed': 2, 'tool.pac-plan.completed': 1},
            correlation: {'pac-rev': 2},
        });
    });

    // Real lines of the planner (the plan's «forme speciali» and «Punti di codice»), as they are before the lot and as
    // the lot writes them: each pair must read the same.
    const BEFORE_AFTER: [string, string, string][] = [
        [
            'TargetsStep.svelte:64, HTML written by hand',
            'return `<div data-testid="pac-planner-target-bar" data-asset-key="${escapeHtml(asset.key)}" aria-hidden="true"></div>`;',
            'return `<div data-testid="${testId(\'target-bar\', profile)}" data-asset-key="${escapeHtml(asset.key)}" aria-hidden="true"></div>`;',
        ],
        ['TargetsStep.svelte:153, a table cell', "testid: 'pac-planner-target-balance',", "testid: testId('target-balance', profile),"],
        [
            'ProofPanel.svelte:113, a table cell',
            "cell({type: 'label', text: objectiveName(stage.objective_code), sequence: stage.ordinal, testid: 'pac-planner-solver-stage'})",
            "cell({type: 'label', text: objectiveName(stage.objective_code), sequence: stage.ordinal, testid: testId('solver-stage', profile)})",
        ],
        ['LedgerTable.svelte:93, a variable tail', "cell({type: 'money', amount: row[field], currency: row.currency, digits, testid: `pac-planner-ledger-${field}`})", "cell({type: 'money', amount: row[field], currency: row.currency, digits, testid: testId(`ledger-${field}`, profile)})"],
        [
            'ResultView.svelte:96, an inner selector',
            'section.querySelector<HTMLElement>(\'[data-testid="pac-planner-result-section-toggle"]\')?.focus({preventScroll: true});',
            'section.querySelector<HTMLElement>(`[data-testid="${testId(\'result-section-toggle\', profile)}"]`)?.focus({preventScroll: true});',
        ],
        ['TargetsStep.svelte:212, a storageKey', 'storageKey="pac-planner-targets"', "storageKey={storageKey('targets', profile)}"],
        ['PacPlannerTool.svelte:55, a DOM id', "const STEP_TITLE_ID = 'pac-planner-step-title';", "const STEP_TITLE_ID = domId('step-title', profile);"],
        ['PacPlannerTool.svelte:308, the root', '<div data-testid="pac-planner" data-view={view}>', '<div data-testid={profile.testIdPrefix} data-view={view}>'],
        ['ExposureMaps.svelte:63, a chart series id', "const SERIES_ID = 'pac-planner-exposure-map';", "const SERIES_ID = testId('exposure-map', profile);"],
        ['ExposureMaps.svelte:193, chart ready', 'attachChartReady(chart, element, `pac-planner-exposure-map-${side}`);', 'attachChartReady(chart, element, testId(`exposure-map-${side}`, profile));'],
        ['ExposureBars.svelte:80, chart ready', 'attachChartReady(chart, element, `pac-planner-exposure-bars-${dimension}`);', 'attachChartReady(chart, element, testId(`exposure-bars-${dimension}`, profile));'],
        ['ResultSection.svelte:24, a Svelte attribute', '<section aria-labelledby="pac-planner-section-{id}-title" data-testid="pac-planner-result-section">', "<section aria-labelledby={domId(`section-${id}-title`, profile)} data-testid={testId('result-section', profile)}>"],
        ['SummaryPanel.svelte:18, a default prop', "let {draft, testid = 'pac-planner-summary'}: Props = $props();", "let {draft, testid = testId('summary', profile)}: Props = $props();"],
        ['DistributionDialog.svelte:32, a root and its derived ids', 'const testid = \'pac-planner-distribution\';\n<p data-testid="{testid}-row"></p>', 'const testid = testId(\'distribution\', profile);\n<p data-testid="{testid}-row"></p>'],
        ['run.svelte.ts:64, the correlation', 'correlationId: `pac-rev-${built.revision}-${sequence}`,', 'correlationId: `${this.#profile.correlationPrefix}-${built.revision}-${sequence}`,'],
        [
            'run.svelte.ts:73-88, the events',
            "notify({name: 'tool.pac-plan.completed'}); notify({name: 'tool.pac-plan.failed'}); notify({name: 'tool.pac-plan.failed'});",
            'notify({name: this.#profile.events.completed}); notify({name: this.#profile.events.failed}); notify({name: this.#profile.events.failed});',
        ],
    ];

    it.each(BEFORE_AFTER)('reads %s the same before and after the lot', (_where, before, after) => {
        const read = extractSurface(before);
        expect(Object.values(read).some((bucket) => Object.keys(bucket).length > 0)).toBe(true);
        expect(extractSurface(after)).toEqual(read);
    });

    it('test ids, storage keys, DOM ids, events equal the PAC baseline', () => {
        const {surface, files} = plannerSurface();
        const baseline = JSON.parse(readFileSync(BASELINE, 'utf8')) as PlannerSurface;

        // Positive control: the scan reached the planner's files and known values of each kind.
        expect(files).toContain('PacPlannerTool.svelte');
        expect(surface.ids['pac-planner']).toBeGreaterThan(0);
        expect(surface.ids['pac-planner-result-section-toggle']).toBeGreaterThan(0);
        expect(surface.ids['pac-planner-targets']).toBeGreaterThan(0);
        expect(surface.ids['pac-planner-step-title']).toBeGreaterThan(0);
        expect(surface.events['tool.pac-plan.completed']).toBeGreaterThan(0);
        expect(surface.ids['pac-planner-section-${id}-title']).toBeGreaterThan(0);
        expect(surface.derived['${testid}-row']).toBeGreaterThan(0);

        expect(surface).toEqual(baseline);
    });

    /*
     * The Rebalancer's reference (F3a of project 67, step 3): the same sources read under its profile, so `testId(…)` gives
     * `rebalancer-planner-…`. T1a and T1b select by these ids. The scan cannot tell which component each Tool mounts, so
     * the reference lists every id the shared planner can show under that profile; a component of one Tool only adds its
     * own ids here and in the PAC's reference alike.
     */
    it('the Rebalancer reads its own ids, events and correlation, equal to its baseline', () => {
        const {surface} = plannerSurface(REBALANCER);
        const baseline = JSON.parse(readFileSync(REBALANCER_BASELINE, 'utf8')) as PlannerSurface;

        expect(surface.ids['rebalancer-planner']).toBeGreaterThan(0);
        expect(surface.ids['rebalancer-planner-continue']).toBeGreaterThan(0);
        expect(surface.events['tool.rebalancer-plan.completed']).toBeGreaterThan(0);
        expect(surface.correlation['reb-rev']).toBeGreaterThan(0);
        // No PAC id leaks into the Rebalancer's DOM: every id goes through the profile.
        expect(Object.keys(surface.ids).filter((id) => id.startsWith('pac-planner'))).toEqual([]);

        expect(surface).toEqual(baseline);
    });
});
