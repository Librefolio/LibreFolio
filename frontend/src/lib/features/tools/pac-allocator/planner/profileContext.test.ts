// @vitest-environment jsdom
/**
 * The profile travels by Svelte context (F1 of project 67, step 3): a wrapper sets it, every planner component below it
 * reads it once at birth. Under a profile other than the PAC's the component sees that profile; with no wrapper, the PAC.
 * The fixtures live outside the planner folder (`../__tests__/`), out of the surface gate's reach.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {SvelteSet} from 'svelte/reactivity';
import {cleanup, render, screen, setupI18n} from '$test/component';
import ProfileHarness from '../__tests__/ProfileHarness.svelte';
import {PlannerDraft} from './draft.svelte';
import {PAC_PLANNER_PROFILE, type PlannerProfile} from './profile';
import BusyPanel from './result/BusyPanel.svelte';
import StepNav from './shell/StepNav.svelte';
import TargetsStep from './steps/TargetsStep.svelte';
import type {PlannerStep} from './types';

const OTHER: PlannerProfile = Object.freeze({...PAC_PLANNER_PROFILE, toolCode: 'portfolio_rebalancer', correlationPrefix: 'other-rev'});

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

const OTHER_PREFIX = ['other', 'planner'].join('-');
const PAC_PREFIX = ['pac', 'planner'].join('-');
const OTHER_IDS: PlannerProfile = Object.freeze({...PAC_PLANNER_PROFILE, testIdPrefix: OTHER_PREFIX});

/** Every test id, id and aria reference the mounted tree carries. */
function names(): string[] {
    const values: string[] = [];
    for (const element of document.body.querySelectorAll('*')) {
        for (const attribute of element.getAttributeNames()) {
            if (attribute === 'data-testid' || attribute === 'id' || attribute.startsWith('aria-')) values.push(element.getAttribute(attribute) ?? '');
        }
    }
    return values;
}

function draftWithAnAsset(): PlannerDraft {
    const draft = new PlannerDraft('EUR', '', OTHER_IDS);
    draft.addAsset({
        key: 'asset:1',
        origin: 'manual',
        sourceAssetId: null,
        name: 'Probe Asset',
        ticker: 'PRB',
        assetClass: 'equity',
        iconUrl: null,
        active: true,
        price: null,
        priceManual: false,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: '2026-11-13T10:00:00Z',
    } as never);
    return draft;
}

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

    // Real planner components below a wrapper with another prefix: none of their test ids, ids or aria references keeps
    // the PAC's prefix, and they carry the other one — the step's table (a DataTable with custom cells) included.
    it.each([
        ['StepNav', () => ({child: StepNav, childProps: {current: 'scenario' as PlannerStep, visited: new SvelteSet<PlannerStep>(['scenario']), problemSteps: new Set<PlannerStep>(), variant: 'compact', onselect: () => {}}})],
        ['BusyPanel', () => ({child: BusyPanel, childProps: {timeoutMs: 60_000, onstop: () => {}}})],
        ['TargetsStep', () => ({child: TargetsStep, childProps: {draft: draftWithAnAsset(), accountGeneration: 0}})],
    ])('%s reads the prefix the wrapper set', (_name, props) => {
        render(ProfileHarness, {props: {profile: OTHER_IDS, ...props()}});
        const values = names();
        expect(values.filter((value) => value.startsWith(PAC_PREFIX))).toEqual([]);
        expect(values.some((value) => value.startsWith(OTHER_PREFIX))).toBe(true);
    });
});
