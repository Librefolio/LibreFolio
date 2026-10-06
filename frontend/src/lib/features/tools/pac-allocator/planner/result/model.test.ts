// @vitest-environment node
/**
 * model — the help the proof badge opens, and the catalogue behind every badge (Vitest, node).
 *
 * Subject. `resultBadges` turns a ready result into the badges at the head of the result:
 * availability, the Decimal check when the plan carries it, proof and stop reason, each with the
 * explanation it opens on hover or focus (R11.4). Since S4 (developer decision Q6 (ii)) the help
 * of a `not_proven` proof depends on how the run ended:
 *   - no plan (`no_incumbent`): the state's own explanation, since "the best plan found" would be
 *     false with no plan;
 *   - a plan and a `completed` search: `proof.floatingFinished`. The solver closed its search, so
 *     what keeps the proof from holding is the final exact check (P-c) contradicting the solver's
 *     bounds;
 *   - a plan and a `time_limit` or `node_limit` stop: `proof.floatingUnfinished`, the solver did
 *     not close every stage.
 * Before S4 every `not_proven` proof with a plan opened `floatingUnfinished`, so a search that had
 * completed was told it had stopped early: the first case is the one that pins S4. The help of
 * `optimal_proven` and `infeasibility_proven` is pinned alongside.
 *
 * Expectations. The proof badge is found by its `id`, never by its place in the list, and the
 * assertion is on the help's catalogue key: the key decides the sentence in every locale.
 *
 * Catalogue (P-d). A badge carries an English fallback for its label and for its help, and P-d
 * was about fallbacks and catalogue promising different things. For every badge the cases
 * produce, the stop badge included (its key is built from the stop reason), each fallback must
 * equal the EN catalogue's message at its key, and a key with no message in `en.json` is a
 * failure, not a skip. The check compares two sources and never spells a sentence itself.
 * Controls prove that the resolver finds nothing at a missing key or at a subtree, and that the
 * walk reached all four kinds of badge, the Decimal check and the three stop labels. They name no
 * proof help: which help the proof badge opens is the cases' subject, so a wrong help is red there
 * and only there.
 *
 * Results. Minimal objects cast to `PacReadyResult`: `outcome`, `stop_reason`, `proof.kind`, and
 * `primary_solution.validation` on the cases with a plan. The contract requires a primary
 * solution on `ready_incumbent` and knows its validation only as `decimal_verified`, so there the
 * Decimal-check badge appears and enters the catalogue check too.
 *
 * Environment. `resultBadges` reads plain fields and touches no DOM: node is enough.
 */
import {describe, expect, it, vi} from 'vitest';

// The badges module imports the planner's formatter, which reads the currency catalogue store,
// which imports the API client. Nothing here formats an amount: every call resolves to nothing.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import en from '$lib/i18n/en.json';
import type {PacProof, PacReadyResult} from '../types';
import {resultBadges, type ResultBadge} from './model';

interface ProofCase {
    proof: PacProof['kind'];
    outcome: PacReadyResult['outcome'];
    stop_reason: PacReadyResult['stop_reason'];
    /** The catalogue key of the help the proof badge must open. */
    help: string;
    /** Why that help: the assertion's message when it fails. */
    why: string;
}

/** The states the proof badge's help is decided on. The first is S4's own: a completed search that is still not proven. */
const CASES: ProofCase[] = [
    {proof: 'not_proven', outcome: 'incumbent_found', stop_reason: 'completed', help: 'tools.pacAllocator.planner.result.proof.floatingFinished', why: 'the search completed and is still not proven: the final exact check contradicted the solver bounds'},
    {proof: 'not_proven', outcome: 'incumbent_found', stop_reason: 'time_limit', help: 'tools.pacAllocator.planner.result.proof.floatingUnfinished', why: 'the solver reached its time limit before closing every stage'},
    {proof: 'not_proven', outcome: 'incumbent_found', stop_reason: 'node_limit', help: 'tools.pacAllocator.planner.result.proof.floatingUnfinished', why: 'the solver reached its node limit before closing every stage'},
    {proof: 'not_proven', outcome: 'no_incumbent', stop_reason: 'time_limit', help: 'tools.pacAllocator.planner.result.states.noIncumbent.body', why: 'with no plan, "the best plan found" would be false: the help says what the state says'},
    {proof: 'optimal_proven', outcome: 'incumbent_found', stop_reason: 'completed', help: 'tools.pacAllocator.planner.result.badges.help.optimalProven', why: 'a proven optimum explains its proof'},
    {proof: 'infeasibility_proven', outcome: 'infeasible_proven', stop_reason: 'completed', help: 'tools.pacAllocator.planner.result.proof.solverInfeasibleWitness', why: 'a proven infeasibility names the solver witness'},
];

/** The stop badge builds its key from the stop reason; the cases reach all three. */
const STOP_KEYS = ['tools.pacAllocator.planner.result.stop.completed', 'tools.pacAllocator.planner.result.stop.time_limit', 'tools.pacAllocator.planner.result.stop.node_limit'];
/** The Decimal-check badge, which every case with a plan carries. */
const DECIMAL_CHECK_KEY = 'tools.pacAllocator.planner.result.badges.decimalVerified';

function caseTitle(c: ProofCase): string {
    return `${c.proof} + ${c.outcome} + ${c.stop_reason}`;
}

/** Only what `resultBadges` reads. A plan carries its primary solution, as the contract requires. */
function readyResult(c: ProofCase): PacReadyResult {
    const plan = c.outcome === 'incumbent_found' ? {primary_solution: {validation: 'decimal_verified'}} : {};
    return {outcome: c.outcome, stop_reason: c.stop_reason, proof: {kind: c.proof}, ...plan} as unknown as PacReadyResult;
}

/** The badge with this id, found by what it is and never by its place in the list. */
function badgeById(badges: ResultBadge[], id: string): ResultBadge {
    const matches = badges.filter((badge) => badge.id === id);
    expect(matches, `one '${id}' badge`).toHaveLength(1);
    return matches[0];
}

/** The EN message at a dotted key; undefined when the key is missing or names a subtree. */
function catalogueMessage(key: string): string | undefined {
    const node = key.split('.').reduce<unknown>((parent, part) => (parent !== null && typeof parent === 'object' ? (parent as Record<string, unknown>)[part] : undefined), en);
    return typeof node === 'string' ? node : undefined;
}

describe('resultBadges — the help the proof badge opens', () => {
    for (const c of CASES) {
        it(`${caseTitle(c)} → ${c.help}`, () => {
            expect(badgeById(resultBadges(readyResult(c)), 'proof').help.key, c.why).toBe(c.help);
        });
    }
});

describe('resultBadges — every fallback is the EN catalogue message at its key (P-d)', () => {
    it('reads a message at a key, and nothing at a missing key or at a subtree', () => {
        expect(catalogueMessage('tools.pacAllocator.planner.result.stop.completed')).toEqual(expect.any(String));
        expect(catalogueMessage('tools.pacAllocator.planner.result.proof.noSuchMessage')).toBeUndefined();
        expect(catalogueMessage('tools.pacAllocator.planner.result.proof')).toBeUndefined();
    });

    it('holds for the label and the help of every badge the cases produce, stop badges included', () => {
        const checkedIds = new Set<string>();
        const checkedKeys = new Set<string>();
        const mismatches: string[] = [];
        for (const c of CASES) {
            for (const badge of resultBadges(readyResult(c))) {
                checkedIds.add(badge.id);
                const pairs: {part: string; key: string; fallback: string}[] = [
                    {part: 'label', key: badge.key, fallback: badge.fallback},
                    {part: 'help', key: badge.help.key, fallback: badge.help.fallback},
                ];
                for (const {part, key, fallback} of pairs) {
                    checkedKeys.add(key);
                    const message = catalogueMessage(key);
                    const where = `${caseTitle(c)}, ${badge.id} ${part} at ${key}`;
                    if (message === undefined) mismatches.push(`${where}: en.json has no message there`);
                    else if (message !== fallback) mismatches.push(`${where}: the fallback says ${JSON.stringify(fallback)}, en.json says ${JSON.stringify(message)}`);
                }
            }
        }
        // The walk reached what it claims to cover: all four kinds of badge, the Decimal check and the three stop labels.
        expect([...checkedIds]).toEqual(expect.arrayContaining(['availability', 'validation', 'proof', 'stop']));
        expect([...checkedKeys]).toEqual(expect.arrayContaining([DECIMAL_CHECK_KEY, ...STOP_KEYS]));
        expect(mismatches).toEqual([]);
    });
});
