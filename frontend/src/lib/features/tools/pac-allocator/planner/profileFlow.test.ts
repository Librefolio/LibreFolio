/**
 * The profile reaches the draft and the run (F1 of project 67, step 3): under a profile other than the PAC's, the
 * wizard's steps, a run's correlation id and its event names are that profile's; with none, the PAC's.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

const {runTool, notify} = vi.hoisted(() => ({runTool: vi.fn(), notify: vi.fn()}));

vi.mock('../../client', () => ({runTool}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify}));
vi.mock('../../contracts', async (importOriginal) => ({...(await importOriginal<object>()), assertToolAccount: () => undefined}));

import {PlannerDraft} from './draft.svelte';
import {PAC_PLANNER_PROFILE, type PlannerProfile} from './profile';
import type {BuiltRequest} from './request';
import {PlannerRun} from './run.svelte';

const OTHER: PlannerProfile = Object.freeze({
    ...PAC_PLANNER_PROFILE,
    testIdPrefix: 'other-planner',
    correlationPrefix: 'other-rev',
    events: Object.freeze({completed: 'tool.other-plan.completed', failed: 'tool.other-plan.failed'}),
    steps: Object.freeze(['scenario', 'assets', 'fx', 'review'] as const),
});

const BUILT = {request: {}, resolved: {}, ids: {}, revision: 7, fingerprint: 'f', counts: {assets: 0, operativeBrokers: 0, buyRoutes: 0, fxPairs: 0}} as unknown as BuiltRequest;

function success(): unknown {
    return {status: 'success', result: {result_state: 'ready_no_op', issues: []}, metrics: {}, batch: {metrics: {}}, execution_id: 'x'};
}

afterEach(() => {
    runTool.mockReset();
    notify.mockReset();
});

describe('the profile reaches the draft and the run', () => {
    it('the draft carries the profile and shows its steps; the PAC when none is given', () => {
        expect(new PlannerDraft('EUR').profile).toBe(PAC_PLANNER_PROFILE);
        expect(new PlannerDraft('EUR').visibleSteps).toEqual(PAC_PLANNER_PROFILE.steps.filter((step) => step !== 'fx'));
        const draft = new PlannerDraft('EUR', '', OTHER);
        expect(draft.profile).toBe(OTHER);
        expect(draft.visibleSteps).toEqual(['scenario', 'assets', 'review']);
    });

    it("a run uses the profile's correlation prefix and event names", async () => {
        runTool.mockResolvedValueOnce(success());
        await new PlannerRun(() => ({}) as never, OTHER).start(BUILT, 0);
        expect(runTool.mock.calls[0][2].correlationId).toBe('other-rev-7-1');
        expect(notify).toHaveBeenCalledWith(expect.objectContaining({name: 'tool.other-plan.completed'}));

        runTool.mockResolvedValueOnce({status: 'error', error: {code: 'execution_limit', retryable: true, issue_count: 0}, metrics: {}, batch: {metrics: {}}, execution_id: null});
        await new PlannerRun(() => ({}) as never, OTHER).start(BUILT, 0);
        expect(notify).toHaveBeenLastCalledWith(expect.objectContaining({name: 'tool.other-plan.failed'}));
    });

    it("without a profile a run is the PAC's", async () => {
        runTool.mockResolvedValueOnce(success());
        await new PlannerRun(() => ({}) as never).start(BUILT, 0);
        expect(runTool.mock.calls[0][2].correlationId).toBe('pac-rev-7-1');
        expect(notify).toHaveBeenCalledWith(expect.objectContaining({name: 'tool.pac-plan.completed'}));
    });
});
