// @vitest-environment jsdom
/**
 * AutomaticConversionNote (F2 of project 67, developer's answer of 13/11, point 1): a Broker that converts currency by
 * itself does it at each purchase, while the plan counts one conversion per currency pair, so the Broker's own rounding
 * may differ by a few cents per order. An info note (not a warning) at the top of the operational plan says so, naming
 * the Brokers, whenever the plan has at least one conversion with `mode == "automatic"`; none with manual conversions only.
 * Read through test ids and data attributes, never through the translated text.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {cleanup, render, screen, setupI18n} from '$test/component';
import type {PlannerConversion} from '../types';
import type {ResultNames} from './model';
import AutomaticConversionNote from './AutomaticConversionNote.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(cleanup);

const BROKERS: Record<string, string> = {'broker-auto': 'Auto Broker probe', 'broker-two': 'Second Auto probe', 'broker-manual': 'Manual Broker probe'};
const names: ResultNames = {asset: (id) => id, ticker: () => null, broker: (id) => BROKERS[id] ?? id};

function conversion(conversion_id: string, broker_id: string, mode: 'automatic' | 'manual'): PlannerConversion {
    return {conversion_id, broker_id, mode} as unknown as PlannerConversion;
}

const note = () => screen.queryByTestId('pac-planner-plan-auto-conversion-note');

describe('AutomaticConversionNote', () => {
    it('is shown, as an info status, when the plan has an automatic conversion, naming each Broker once', () => {
        render(AutomaticConversionNote, {
            conversions: [conversion('c1', 'broker-auto', 'automatic'), conversion('c2', 'broker-manual', 'manual'), conversion('c3', 'broker-auto', 'automatic'), conversion('c4', 'broker-two', 'automatic')],
            names,
        });

        const shown = note();
        expect(shown).not.toBeNull();
        expect(shown!.getAttribute('role')).toBe('status');
        expect(shown!.getAttribute('data-brokers')).toBe('broker-auto broker-two');
        expect(shown!.textContent).toContain('Auto Broker probe, Second Auto probe');
        expect(shown!.textContent).not.toContain('Manual Broker probe');
    });

    it('is absent when every conversion is manual', () => {
        render(AutomaticConversionNote, {conversions: [conversion('c1', 'broker-manual', 'manual')], names});
        expect(note()).toBeNull();
    });

    it('is absent when the plan converts nothing', () => {
        render(AutomaticConversionNote, {conversions: [], names});
        expect(note()).toBeNull();
    });
});
