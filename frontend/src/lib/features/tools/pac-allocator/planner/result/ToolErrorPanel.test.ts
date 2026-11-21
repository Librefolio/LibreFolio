// @vitest-environment jsdom
/**
 * ToolErrorPanel — «Copy the request» (R1-B of project 67, the developer's answer of 20/11/2026).
 *
 * A failed calculation could not be replayed: the page keeps the draft in memory only and the server logs no input. The
 * panel copies the request the run sent (`built.request`), as it was sent, so it parses back into the same body and can
 * be attached to a report. Nothing goes to the server, a log or an event: only the clipboard, through the shared writer.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {ToolClientError} from '../../../contracts';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, testId, type PlannerProfile} from '../profile';
import type {BuiltRequest} from '../request';
import type {RunOutcome} from '../run.svelte';
import ToolErrorPanel from './ToolErrorPanel.svelte';

const clipboard = vi.hoisted(() => ({writeTextToClipboard: vi.fn<(text: string) => Promise<void>>()}));
vi.mock('$lib/utils/clipboard', () => clipboard);

const toast = vi.hoisted(() => ({success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: toast}));

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

/** A request body as the run sends it: nested objects, decimal strings, a list. Only its shape matters here. */
const REQUEST = {operation: 'plan', valuation_currency: 'EUR', existing_cash: [{broker_id: 'broker:1', selected: {amount: '1234.56', currency: 'EUR'}}], fx_rates: {'EUR/USD': '1.0792'}};
const BUILT = {request: REQUEST, resolved: {}, ids: {}, revision: 3, fingerprint: 'f', counts: {assets: 1, operativeBrokers: 1, buyRoutes: 1, fxPairs: 1}} as unknown as BuiltRequest;
const METRICS = {} as never;

type PanelOutcome = Extract<RunOutcome, {kind: 'tool_error' | 'client_error'}>;
const OUTCOMES: Array<[string, PanelOutcome]> = [
    ['tool_error', {kind: 'tool_error', built: BUILT, error: {code: 'execution_failed', retryable: false, issue_count: 0}, metrics: METRICS, batch: METRICS, executionId: 'exec-1'}],
    ['client_error', {kind: 'client_error', built: BUILT, error: new ToolClientError('internal', 'unexpected_ui_error')}],
];
const PROFILES: Array<[string, PlannerProfile]> = [
    ['PAC', PAC_PLANNER_PROFILE],
    ['Rebalancer', REBALANCER_PLANNER_PROFILE],
];

function renderPanel(outcome: PanelOutcome, profile: PlannerProfile) {
    render(ProfileHarness, {props: {profile, child: ToolErrorPanel, childProps: {outcome, disabled: false, onretry: vi.fn(), onedit: vi.fn()}}});
    return screen.getByTestId(testId('platform-copy-request', profile));
}

describe('ToolErrorPanel copy the request', () => {
    for (const [kind, outcome] of OUTCOMES) {
        for (const [name, profile] of PROFILES) {
            it(`copies the request sent, as it was sent (${kind}, ${name})`, async () => {
                clipboard.writeTextToClipboard.mockResolvedValue();
                await fireEvent.click(renderPanel(outcome, profile));

                expect(clipboard.writeTextToClipboard).toHaveBeenCalledTimes(1);
                expect(JSON.parse(clipboard.writeTextToClipboard.mock.calls[0][0])).toEqual(REQUEST);
                expect(toast.success).toHaveBeenCalledTimes(1);
                expect(toast.error).not.toHaveBeenCalled();
            });
        }
    }

    it('says so when the browser refuses the copy', async () => {
        clipboard.writeTextToClipboard.mockRejectedValue(new Error('refused'));
        await fireEvent.click(renderPanel(OUTCOMES[0][1], PAC_PLANNER_PROFILE));
        await vi.waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
        expect(toast.success).not.toHaveBeenCalled();
    });

    it('says so when the browser has no way to copy at all (the writer throws at once)', async () => {
        clipboard.writeTextToClipboard.mockImplementation(() => {
            throw new Error('no transport');
        });
        await fireEvent.click(renderPanel(OUTCOMES[0][1], PAC_PLANNER_PROFILE));
        await vi.waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
        expect(toast.success).not.toHaveBeenCalled();
    });
});
