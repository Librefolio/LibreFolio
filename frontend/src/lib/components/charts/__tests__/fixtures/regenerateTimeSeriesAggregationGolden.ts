/**
 * Regenerate `timeSeriesAggregation.golden.v1.json`.
 *
 *   cd frontend
 *   node src/lib/components/charts/__tests__/fixtures/regenerateTimeSeriesAggregationGolden.ts
 *   node src/lib/components/charts/__tests__/fixtures/regenerateTimeSeriesAggregationGolden.ts --accept
 *
 * Deliberately NOT reachable from any test command. There is no `vitest -u`
 * path to these values: `vitest --update` rewrites inline/file snapshots in
 * place with no diff shown to anyone, which is exactly the failure mode a
 * pre-refactor golden exists to prevent. Three things stand in the way here:
 *
 *   1. Running this script does nothing without `--accept`. The default is a
 *      report: every key whose recorded behaviour changed, old value next to
 *      new value.
 *   2. Even after `--accept`, the suite stays RED. The expected digest is a
 *      literal in `timeSeriesAggregationGolden.test.ts`, and this script never
 *      touches that file. Accepting new behaviour therefore takes a second,
 *      manual edit, in a second file, in the same commit.
 *   3. The `meta` block of the existing fixture is carried over verbatim rather
 *      than rewritten, so the provenance note ("captured pre-refactor at
 *      <commit>") cannot be quietly re-dated into agreeing with whatever the
 *      code now does. No clock is read, so output is byte-stable.
 */

import {execFileSync} from 'node:child_process';
import {readFileSync, writeFileSync} from 'node:fs';
import process from 'node:process';
import {fileURLToPath} from 'node:url';

import {canonicalStringify, captureGoldenCorpus, goldenDigest, type EncodedValue, type GoldenEntries} from './timeSeriesAggregationGoldenCases.ts';

const GOLDEN_PATH = fileURLToPath(new URL('./timeSeriesAggregation.golden.v1.json', import.meta.url));

const FALLBACK_META = {
    what: 'Recorded output of the four groupPointsByBucket consumers, captured from the implementation BEFORE the grouping refactor.',
    why: 'So the post-refactor assertion compares against a frozen record instead of re-deriving expectations from the refactored code.',
    doNotEdit: 'Never hand-edit a value here. Change the inputs in timeSeriesAggregationGoldenCases.ts, or re-record with the regenerate script and update GOLDEN_DIGEST in timeSeriesAggregationGolden.test.ts by hand.',
};

interface GoldenFile {
    meta?: Record<string, unknown>;
    formatVersion: number;
    entries: GoldenEntries;
}

function readExistingGolden(): GoldenFile | null {
    try {
        return JSON.parse(readFileSync(GOLDEN_PATH, 'utf8')) as GoldenFile;
    } catch {
        return null;
    }
}

/**
 * Render JSON with one line per leaf object, so a behaviour change shows up as a
 * one-line diff on the affected bucket instead of a reflowed block. Objects and
 * arrays holding only primitives are inlined; anything nested stays expanded.
 *
 * This is a first draft only: prettier is run over the result afterwards and has
 * the final say on line breaking, so the committed file always matches
 * `prettier --check` no matter who regenerates it.
 */
function renderJson(value: unknown, indent: string): string {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);

    const pad = `${indent}  `;

    if (Array.isArray(value)) {
        if (value.length === 0) return '[]';
        const inline = `[${value.map((item) => JSON.stringify(item)).join(', ')}]`;
        if (value.every((item) => item === null || typeof item !== 'object') && pad.length + inline.length <= 280) return inline;
        return `[\n${value.map((item) => `${pad}${renderJson(item, pad)}`).join(',\n')}\n${indent}]`;
    }

    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return '{}';
    const inline = `{${entries.map(([key, item]) => `${JSON.stringify(key)}: ${JSON.stringify(item)}`).join(', ')}}`;
    if (entries.every(([, item]) => item === null || typeof item !== 'object') && pad.length + inline.length <= 280) return inline;
    return `{\n${entries.map(([key, item]) => `${pad}${JSON.stringify(key)}: ${renderJson(item, pad)}`).join(',\n')}\n${indent}}`;
}

function describeDrift(previous: GoldenEntries, next: GoldenEntries): string[] {
    const lines: string[] = [];
    const keys = [...new Set([...Object.keys(previous), ...Object.keys(next)])].sort();

    for (const key of keys) {
        const before = previous[key];
        const after = next[key];

        if (before === undefined) {
            lines.push(`  + ADDED    ${key}`);
            continue;
        }
        if (after === undefined) {
            lines.push(`  - REMOVED  ${key}`);
            continue;
        }

        const beforeText = canonicalStringify(before as unknown as EncodedValue);
        const afterText = canonicalStringify(after as unknown as EncodedValue);
        if (beforeText === afterText) continue;

        lines.push(`  ~ CHANGED  ${key}`);
        lines.push(`      recorded: ${beforeText}`);
        lines.push(`      current : ${afterText}`);
    }

    return lines;
}

function main(): void {
    const accept = process.argv.includes('--accept');
    const existing = readExistingGolden();
    const captured = captureGoldenCorpus();
    const drift = existing ? describeDrift(existing.entries, captured.entries) : [];

    if (existing && drift.length === 0) {
        console.log('Golden corpus is unchanged — current behaviour still matches the recorded pre-refactor behaviour.');
        console.log(`Digest: ${goldenDigest(captured.entries)}`);
        return;
    }

    if (existing) {
        console.log(`Current behaviour DIFFERS from the recorded golden in ${drift.filter((line) => !line.startsWith('      ')).length} entr(ies):\n`);
        console.log(drift.join('\n'));
        console.log('');
        console.log('Read every line above before accepting. Each one is a behaviour change,');
        console.log('not a formatting detail — that is the whole point of the record.\n');
    } else {
        console.log(`No golden file at ${GOLDEN_PATH} — this run would create it.\n`);
    }

    const digest = goldenDigest(captured.entries);

    if (!accept) {
        console.log('Nothing written (dry run). Re-run with --accept to overwrite the fixture.');
        console.log(`Digest that would be written: ${digest}`);
        return;
    }

    const file: GoldenFile = {
        meta: (existing?.meta as Record<string, unknown> | undefined) ?? FALLBACK_META,
        formatVersion: captured.formatVersion,
        entries: captured.entries,
    };

    writeFileSync(GOLDEN_PATH, `${renderJson(file, '')}\n`, 'utf8');

    let formatted = false;
    try {
        execFileSync('npx', ['prettier', '--write', GOLDEN_PATH], {stdio: 'ignore'});
        formatted = true;
    } catch {
        formatted = false;
    }

    console.log(`Wrote ${GOLDEN_PATH}`);
    if (!formatted) console.log('WARNING: prettier could not be run. Run `npx prettier --write` on that file before committing.');
    console.log('');
    console.log('The suite is RED until you do this by hand, which is the point:');
    console.log(`  set GOLDEN_DIGEST in timeSeriesAggregationGolden.test.ts to: ${digest}`);
    console.log('Do it only if you have read the drift above and accept every line of it as intended.');
}

main();
