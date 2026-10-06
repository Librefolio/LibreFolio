/**
 * The `risk.warnings` sentences that take ICU arguments, and plausible values for them.
 *
 * Shared by `levels/levelHelpers.test.ts` (through `warningSentence`) and
 * `RiskResultFrame.test.ts` (through a render). Both assert one property over one
 * list — a keyed warning never puts a brace or a key on screen, whether its values
 * arrived or not — so the list and the values live here, once, and the two specs
 * cannot drift apart.
 *
 * Both halves are **read off the shipped catalogue at test time**, never listed:
 *
 *   - the keys: every `risk.warnings` leaf in `en.json` whose sentence has an
 *     argument, so a key added tomorrow is covered the day it lands;
 *   - the values: built from the sentence's own arguments, parsed by the same
 *     formatter svelte-i18n formats with (`getMessageFormatter(...).getAst()`). A
 *     select therefore gets an option it names and a plural or a number gets a
 *     number. A regex cannot do this: `{sector}` inside
 *     `{dimension, select, sector {sector} other {geography}}`, or `{was}` inside a
 *     plural option, look exactly like arguments and are not.
 *
 * The values are plausible, never real: synthetic names only.
 */
import {getMessageFormatter} from 'svelte-i18n';

import en from '$lib/i18n/en.json';

export type WarningParams = Record<string, string | number>;

/** The keys the backend emits under a warning code equal to the key's own name. */
export const CODE_EQUAL_ICU_WARNING_KEYS = ['risk.warnings.hypothetical_metadata_other_fallback', 'risk.warnings.slice_assets_not_held', 'risk.warnings.historical_replay_proxies_used', 'risk.warnings.historical_replay_mostly_excluded'] as const;

/** Node kinds of the ICU AST: `TYPE` in `@formatjs/icu-messageformat-parser`, the parser behind svelte-i18n. */
const ICU = {argument: 1, number: 2, date: 3, time: 4, select: 5, plural: 6, tag: 8} as const;

interface IcuNode {
    type: number;
    value?: string;
    style?: unknown;
    options?: Record<string, {value: IcuNode[]}>;
    children?: IcuNode[];
}

type IcuArgument = {kind: 'text'} | {kind: 'number'; percent: boolean} | {kind: 'date'} | {kind: 'select'; options: string[]};

/** What the backend sends for an argument it names, where the name alone decides the type (`{days}` is text in the sentence, a number on the wire). */
const SAMPLE_NUMBERS: Record<string, number> = {count: 2, days: 45, covered: 0.37, minObservations: 30, minCoverage: 60};
const SAMPLE_TEXTS: Record<string, string> = {names: 'Synthetic Holding A, Synthetic Holding B', pairs: 'AAA/BBB, CCC/DDD'};

function collect(nodes: IcuNode[], into: Map<string, IcuArgument>): void {
    for (const node of nodes) {
        const name = node.value ?? '';
        if (node.type === ICU.argument && !into.has(name)) into.set(name, {kind: 'text'});
        else if (node.type === ICU.number || node.type === ICU.plural) into.set(name, {kind: 'number', percent: node.style === 'percent'});
        else if (node.type === ICU.date || node.type === ICU.time) into.set(name, {kind: 'date'});
        else if (node.type === ICU.select) into.set(name, {kind: 'select', options: Object.keys(node.options ?? {})});
        // Option bodies and tag children can hold arguments of their own.
        for (const option of Object.values(node.options ?? {})) collect(option.value, into);
        if (node.type === ICU.tag && node.children) collect(node.children, into);
    }
}

/** The arguments a sentence takes, by name, as the ICU parser reads them. */
export function icuArguments(sentence: string): Map<string, IcuArgument> {
    const into = new Map<string, IcuArgument>();
    collect(getMessageFormatter(sentence, 'en').getAst() as unknown as IcuNode[], into);
    return into;
}

function enSentence(key: string): string {
    const leaf = key.replace(/^risk\.warnings\./, '');
    const text = (en.risk.warnings as Record<string, unknown>)[leaf];
    if (typeof text !== 'string') throw new Error(`${key} is not a sentence in en.json`);
    return text;
}

/** Every `risk.warnings` key in `en.json` whose sentence takes at least one ICU argument. */
export function icuWarningKeys(): string[] {
    return Object.entries(en.risk.warnings as Record<string, unknown>)
        .filter(([, text]) => typeof text === 'string' && icuArguments(text).size > 0)
        .map(([leaf]) => `risk.warnings.${leaf}`);
}

function plausibleValue(name: string, argument: IcuArgument): string | number {
    if (argument.kind === 'select') return argument.options.find((option) => option !== 'other') ?? 'other';
    if (argument.kind === 'number') return SAMPLE_NUMBERS[name] ?? (argument.percent ? 0.37 : 3);
    if (argument.kind === 'date') return Date.UTC(2020, 0, 15);
    return SAMPLE_NUMBERS[name] ?? SAMPLE_TEXTS[name] ?? `Synthetic ${name}`;
}

/** A plausible value for every argument the `en.json` sentence behind `key` takes. */
export function plausibleParams(key: string): WarningParams {
    const params: WarningParams = {};
    for (const [name, argument] of icuArguments(enSentence(key))) params[name] = plausibleValue(name, argument);
    return params;
}
