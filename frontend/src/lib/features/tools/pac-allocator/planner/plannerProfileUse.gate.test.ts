/**
 * The planner reads its Tool from the profile (F1 of project 67, after the seal): a guard for the components to come
 * (V3, F2, F3a). The frozen surface gate (`plannerSurface.gate.test.ts`) accepts the PAC's literals and the profile's
 * calls alike, and a call without its profile silently gives the PAC; this one refuses both in the planner's product
 * sources (no test, not `profile.ts`, which defines the PAC's values):
 *   - no PAC literal: the test id prefix, the event names, the correlation prefix;
 *   - every `testId` / `storageKey` / `domId` call passes the profile, and so do `contractPolicies`, `defaultPolicy`,
 *     `new PlannerDraft` and `new PlannerRun`.
 */
import {readFileSync, readdirSync} from 'node:fs';
import {join, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

const PLANNER_DIR = fileURLToPath(new URL('.', import.meta.url));
// Written in pieces, so that this file is no instance of what it looks for.
const PAC_LITERALS = [['pac', 'planner'].join('-'), ['tool', 'pac-plan'].join('.'), ['pac', 'rev-'].join('-')];

function sources(dir: string): string[] {
    const files: string[] = [];
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) files.push(...sources(path));
        else if (/\.(svelte|ts)$/.test(entry.name) && !/\.test\.ts$/.test(entry.name) && entry.name !== 'profile.ts') files.push(path);
    }
    return files.sort();
}

/** The argument list of every call of `name` (balanced parentheses), from its opening parenthesis. */
function calls(text: string, name: RegExp): string[] {
    const found: string[] = [];
    for (const match of text.matchAll(name)) {
        let depth = 0;
        const start = (match.index ?? 0) + match[0].length - 1;
        for (let index = start; index < text.length; index += 1) {
            if (text[index] === '(') depth += 1;
            else if (text[index] === ')' && --depth === 0) {
                found.push(text.slice(start + 1, index));
                break;
            }
        }
    }
    return found;
}

/** Splits an argument list at its top-level commas. */
function topLevelArguments(list: string): string[] {
    const parts: string[] = [];
    let depth = 0;
    let quote: string | null = null;
    let current = '';
    for (const character of list) {
        if (quote) {
            if (character === quote) quote = null;
        } else if (character === "'" || character === '"' || character === '`') quote = character;
        else if ('([{'.includes(character)) depth += 1;
        else if (')]}'.includes(character)) depth -= 1;
        else if (character === ',' && depth === 0) {
            parts.push(current.trim());
            current = '';
            continue;
        }
        current += character;
    }
    if (current.trim()) parts.push(current.trim());
    return parts;
}

const PROFILED: [RegExp, number][] = [
    [/\b(?:testId|storageKey|domId)\(/g, 2],
    [/\bcontractPolicies\(/g, 1],
    [/\bdefaultPolicy\(/g, 1],
    [/\bnew PlannerDraft\(/g, 3],
    [/\bnew PlannerRun\(/g, 2],
];

describe('the planner reads its Tool from the profile', () => {
    const files = sources(PLANNER_DIR);

    it('reads the planner product sources', () => {
        expect(files.map((file) => relative(PLANNER_DIR, file))).toContain('PlannerShell.svelte');
        expect(files.length).toBeGreaterThan(40);
    });

    it('no PAC literal is left outside the profile', () => {
        const found = files.flatMap((file) => {
            const text = readFileSync(file, 'utf8');
            return PAC_LITERALS.filter((literal) => text.includes(literal)).map((literal) => `${relative(PLANNER_DIR, file)}: ${literal}`);
        });
        expect(found).toEqual([]);
    });

    it('every call that can take the profile is given one', () => {
        const missing: string[] = [];
        let seen = 0;
        for (const file of files) {
            const text = readFileSync(file, 'utf8');
            for (const [name, position] of PROFILED) {
                for (const list of calls(text, name)) {
                    seen += 1;
                    const argument = topLevelArguments(list)[position - 1] ?? '';
                    if (!/\bprofile\b/.test(argument)) missing.push(`${relative(PLANNER_DIR, file)}: ${name.source}${list})`);
                }
            }
        }
        expect(seen).toBeGreaterThan(400);
        expect(missing).toEqual([]);
    });

    it('sees a call without its profile', () => {
        const text = "data-testid={testId('continue')} const draft = new PlannerDraft('EUR', '') const p = contractPolicies()";
        const lists = PROFILED.flatMap(([name, position]) => calls(text, name).map((list) => topLevelArguments(list)[position - 1] ?? ''));
        expect(lists.filter((argument) => !/\bprofile\b/.test(argument))).toHaveLength(3);
    });
});
