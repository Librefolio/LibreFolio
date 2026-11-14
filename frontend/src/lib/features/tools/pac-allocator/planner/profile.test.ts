/**
 * The planner's profile (F1 of project 67): what differs between the Tools that share the planner — tool code,
 * version, test id prefix, correlation prefix, event names, steps, text variant. The PAC is the default profile, so a
 * component mounted alone (a Vitest) or a function called without one still gets the PAC.
 */
import {describe, expect, it} from 'vitest';
import {PLANNER_STEPS} from './types';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, domId, getPlannerProfile, storageKey, testId, type PlannerProfile} from './profile';

describe('planner profile', () => {
    it('the default profile is the PAC profile', () => {
        const profile: PlannerProfile = getPlannerProfile();

        expect(profile).toBe(PAC_PLANNER_PROFILE);
        expect(profile.toolCode).toBe('pac_allocator');
        expect(profile.contractVersion).toBe('2.0.0');
        expect(profile.testIdPrefix).toBe('pac-planner');
        expect(profile.correlationPrefix).toBe('pac-rev');
        expect(profile.events).toEqual({completed: 'tool.pac-plan.completed', failed: 'tool.pac-plan.failed'});
        expect(profile.steps).toEqual(PLANNER_STEPS);
        expect(profile.steps).toHaveLength(9);
        expect(profile.text).toBe('pac');
        // The PAC buys from cash only: it never reads the quantities the user holds.
        expect(profile.positions).toBe(false);
        expect(profile.fundingRoutes).toBe(true);
        // No cash entry in the PAC's targets until step 14 of F3a (limits only, U8).
        expect(profile.cashEntries).toBe('none');
    });

    it('testId joins prefix and suffix', () => {
        expect(testId('continue')).toBe('pac-planner-continue');
        expect(testId('step-review')).toBe('pac-planner-step-review');
        const other: PlannerProfile = {...PAC_PLANNER_PROFILE, testIdPrefix: 'rebalancer-planner'};
        expect(testId('continue', other)).toBe('rebalancer-planner-continue');
    });

    it('storage keys and DOM ids take the same prefix', () => {
        expect(storageKey('targets')).toBe('pac-planner-targets');
        expect(domId('step-title')).toBe('pac-planner-step-title');
        const other: PlannerProfile = {...PAC_PLANNER_PROFILE, testIdPrefix: 'rebalancer-planner'};
        expect(storageKey('targets', other)).toBe('rebalancer-planner-targets');
        expect(domId('step-title', other)).toBe('rebalancer-planner-step-title');
    });

    it('the PAC profile cannot be changed by a caller', () => {
        expect(Object.isFrozen(PAC_PLANNER_PROFILE)).toBe(true);
        expect(Object.isFrozen(PAC_PLANNER_PROFILE.events)).toBe(true);
        expect(Object.isFrozen(PAC_PLANNER_PROFILE.steps)).toBe(true);
    });

    it('the rebalancer profile lists its steps and prefix (F3a of project 67)', () => {
        const profile: PlannerProfile = REBALANCER_PLANNER_PROFILE;

        expect(profile.toolCode).toBe('portfolio_rebalancer');
        expect(profile.contractVersion).toBe('2.0.0');
        expect(profile.testIdPrefix).toBe('rebalancer-planner');
        expect(profile.correlationPrefix).toBe('reb-rev');
        expect(profile.events).toEqual({completed: 'tool.rebalancer-plan.completed', failed: 'tool.rebalancer-plan.failed'});
        // The mockup's order; the «Tax» step comes with F3b, after Strategy.
        expect(profile.steps).toEqual(PLANNER_STEPS);
        expect(profile.text).toBe('rebalancer');
        expect(profile.positions).toBe(true);
        // Every cash reaches every Broker: the Rebalancer declares no funding route (contract §5.4).
        expect(profile.fundingRoutes).toBe(false);
        expect(profile.cashEntries).toBe('full');
        expect(testId('continue', profile)).toBe('rebalancer-planner-continue');
        expect(Object.isFrozen(profile) && Object.isFrozen(profile.events) && Object.isFrozen(profile.steps)).toBe(true);
    });
});
