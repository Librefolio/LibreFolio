// @vitest-environment jsdom
/**
 * The profile travels by Svelte context (F1 of project 67, step 3): a wrapper sets it, every planner component below it
 * reads it once at birth. Under a profile other than the PAC's the component sees that profile; with no wrapper, the PAC.
 * The fixtures live outside the planner folder (`../__tests__/`), out of the surface gate's reach.
 */
import {afterEach, describe, expect, it} from 'vitest';
import {cleanup, render, screen} from '$test/component';
import ProfileHarness from '../__tests__/ProfileHarness.svelte';
import {PAC_PLANNER_PROFILE, type PlannerProfile} from './profile';

const OTHER: PlannerProfile = Object.freeze({...PAC_PLANNER_PROFILE, toolCode: 'portfolio_rebalancer', correlationPrefix: 'other-rev'});

afterEach(() => cleanup());

describe('the planner profile by context', () => {
    it('a component below a wrapper reads the profile the wrapper set', () => {
        render(ProfileHarness, {props: {profile: OTHER}});
        const probe = screen.getByTestId('profile-probe');
        expect([probe.dataset.tool, probe.dataset.correlation]).toEqual(['portfolio_rebalancer', 'other-rev']);
    });

    it('with no wrapper a component reads the PAC profile', () => {
        render(ProfileHarness, {props: {profile: null}});
        const probe = screen.getByTestId('profile-probe');
        expect([probe.dataset.tool, probe.dataset.correlation]).toEqual(['pac_allocator', 'pac-rev']);
    });
});
