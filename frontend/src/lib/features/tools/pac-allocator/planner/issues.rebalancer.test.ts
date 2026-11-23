// @vitest-environment jsdom
/**
 * The Rebalancer's issues and their step (F3a of project 67, step 12).
 *
 * The codes of the closed universe all have their message already; what the Rebalancer adds is where its paths lead
 * and whom they name:
 *   - a position (`holding`) is named as the user knows it, «Asset · Broker», and leads to the Assets step;
 *   - a cash entry of the targets (`broker:N:EUR`, the engine's cell id) is named «Broker · EUR» and leads to Targets;
 *   - a wire path under `target_fidelity` (or the «Custom» euros) leads to the Strategy step.
 * Drafts are built through the real `PlannerDraft` API and the real copies; nothing reads translated text.
 */
import {describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {applyOwnedPositions, newCopyRecord, ownedAssets} from './copies';
import {PlannerDraft} from './draft.svelte';
import {presentIssue} from './issues';
import {defaultPolicy} from './policies';
import {REBALANCER_PLANNER_PROFILE} from './profile';
import {stepOfWirePath} from './request';
import type {PlannerSource} from './source';
import type {PlannerIssue} from './types';

const AS_OF = '2026-11-14';

function heldSource(): PlannerSource {
    const generatedAt = `${AS_OF}T09:30:00Z`;
    return {
        asOf: AS_OF,
        targetCurrency: 'EUR',
        generatedAt,
        provenance: [
            {provenance_id: 'source:portfolio-ledger', domain: 'portfolio', source_ref: 'transactions', source_label: null, captured_at: generatedAt},
            {provenance_id: 'source:broker-domain', domain: 'broker', source_ref: 'brokers', source_label: null, captured_at: generatedAt},
        ],
        assets: [{asset_id: 'asset:11', source_asset_id: 11, name: 'Held probe', ticker: null, asset_class: 'etf', icon_url: null, active: true, provenance_id: 'source:portfolio-ledger'}],
        brokers: [
            {
                broker_id: 'broker:9',
                source_broker_id: 9,
                name: 'Held broker probe',
                icon_url: null,
                access_role: 'OWNER',
                ownership_share: '1',
                observed_currencies: ['EUR'],
                active: true,
                operating_profile_status: 'not_available',
                operating_profile: null,
                provenance_id: 'source:broker-domain',
            },
        ],
        holdings: [{holding_id: 'holding:asset:11:broker:9', asset_id: 'asset:11', broker_id: 'broker:9', provenance_id: 'source:portfolio-ledger', quantity: {custody: '12', ownershipShare: '0.5', economic: '6'}}],
        cash: [],
        prices: [],
        classifications: [],
        fxQuotes: [],
        currentDistribution: null,
        issues: [],
    };
}

function scenario() {
    const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
    draft.data.asOf = AS_OF;
    const broker = draft.addManualBroker('Broker probe');
    const source = heldSource();
    applyOwnedPositions(draft, source, newCopyRecord(draft, 'positions', source), ownedAssets(source).rows);
    draft.addCashEntry(broker.key, 'EUR');
    return {draft, brokerKey: broker.key, position: draft.data.positions[0]};
}

function issue(path: PlannerIssue['path'], code = 'allocation.bounds_unsatisfiable'): PlannerIssue {
    return {code, kind: 'invalid', severity: 'error', message_key: code, params: [], path} as unknown as PlannerIssue;
}

describe('the Rebalancer issues and their step', () => {
    it('an issue on a position names «Asset · Broker» and leads to the Assets step', () => {
        const {draft, position} = scenario();
        const presented = presentIssue(issue({kind: 'field', section: 'holdings', entity_kind: 'holding', entity_id: position.key, field: 'planning_quantity'} as PlannerIssue['path']), draft);
        expect([presented.step, presented.entity]).toEqual(['assets', 'Held probe · Held broker probe']);
    });

    it('an issue on a cash entry of the targets names «Broker · currency» and leads to Targets', () => {
        const {draft, brokerKey} = scenario();
        const presented = presentIssue(issue({kind: 'field', section: 'targets', entity_kind: 'cash', entity_id: `${brokerKey}:EUR`, field: 'maximum'} as PlannerIssue['path']), draft);
        expect([presented.step, presented.entity]).toEqual(['targets', 'Broker probe · EUR']);
    });

    it('a wire path under the target fidelity leads to the Strategy step', () => {
        expect(stepOfWirePath(['target_fidelity', 'lambda'])).toBe('strategy');
    });
});
