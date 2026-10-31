/**
 * The contract between the two sides of the guides (21-2): the TypeScript catalog `onboardingGuideCatalog.ts` and the
 * Python registry `backend/app/services/accounts/onboarding_service.py`. Neither side imports the other, so nothing
 * but this file notices when one gains a flow, a step or a version and the other does not.
 *
 *   - the flows: the backend's `ONBOARDING_FLOW_VERSIONS` are exactly `welcome` (no guide) plus the catalog's flows, and
 *     `ONBOARDING_FLOWS` of `types/onboarding.ts` (the list the client sends) is the same set;
 *   - the steps: a flow whose completion is managed per step (`completionMode: 'steps'`) has its step ids in the
 *     backend's `ONBOARDING_FLOW_STEPS`, the same ids in the same order, and the backend lists no other flow.
 *
 * The Python file is read as text (the flows and steps are literals), so no backend is started.
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';
import {ONBOARDING_GUIDE_CATALOG, isStepManagedFlow} from './onboardingGuideCatalog';
import {ONBOARDING_FLOWS} from '$lib/types/onboarding';

const SERVICE = new URL('../../../../../backend/app/services/accounts/onboarding_service.py', import.meta.url);

/** `TRANSACTION_BULK_GUIDE` → `transaction_bulk_guide`: the enum member's value is its lower-case name. */
const flowValue = (member: string): string => member.toLowerCase();

/** The text of the literal assigned to `name` in the Python source: from its `= {` to the line that closes it. */
function literalOf(source: string, name: string): string {
    const start = source.indexOf(`${name}:`);
    expect(start, `${name} is in onboarding_service.py`).toBeGreaterThan(-1);
    const open = source.indexOf('{', start);
    const close = source.indexOf('\n}\n', open);
    return source.slice(open, close + 2);
}

function backendVersions(source: string): string[] {
    return [...literalOf(source, 'ONBOARDING_FLOW_VERSIONS').matchAll(/OnboardingFlow\.([A-Z_]+):\s*\d+/g)].map((match) => flowValue(match[1]));
}

function backendSteps(source: string): Record<string, string[]> {
    const steps: Record<string, string[]> = {};
    for (const match of literalOf(source, 'ONBOARDING_FLOW_STEPS').matchAll(/OnboardingFlow\.([A-Z_]+):\s*\(([^)]*)\)/g)) {
        steps[flowValue(match[1])] = [...match[2].matchAll(/"([^"]+)"/g)].map((id) => id[1]);
    }
    return steps;
}

const source = readFileSync(SERVICE, 'utf8');
const catalogFlows = Object.keys(ONBOARDING_GUIDE_CATALOG);

describe('onboarding guides — the TypeScript catalog and the Python registry agree (21-2)', () => {
    it('the scanner reads the registry: it finds flows, and the step literal of the import guide', () => {
        expect(backendVersions(source).length, 'a registry read as empty would make every comparison below pass').toBeGreaterThan(5);
        expect(backendSteps(source).import_guide?.[0], 'the first step of the import guide').toBe('import.upload');
    });

    it('the backend versions exactly welcome and the catalog flows', () => {
        expect([...backendVersions(source)].sort()).toEqual(['welcome', ...catalogFlows].sort());
    });

    it('ONBOARDING_FLOWS, the list the client sends, is the same set', () => {
        expect([...ONBOARDING_FLOWS].sort()).toEqual([...backendVersions(source)].sort());
    });

    it('a step-managed flow has its steps in the backend registry, the same ids in the same order, and the backend lists no other flow', () => {
        const managed = (catalogFlows as Array<keyof typeof ONBOARDING_GUIDE_CATALOG>).filter((flow) => isStepManagedFlow(flow));
        const backend = backendSteps(source);

        expect(Object.keys(backend).sort(), 'the flows whose steps the backend tracks').toEqual([...managed].sort());
        for (const flow of managed) expect(backend[flow], `steps of ${flow}`).toEqual([...ONBOARDING_GUIDE_CATALOG[flow].steps]);
    });
});
