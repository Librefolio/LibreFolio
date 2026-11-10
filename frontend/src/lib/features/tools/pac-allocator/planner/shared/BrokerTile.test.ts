// @vitest-environment jsdom
/**
 * BrokerTile (P2): a Broker as a tile pressed to choose it — props in, DOM and callbacks out.
 *
 * The tile is a button with `aria-pressed`; a Broker the user cannot read from is disabled and says why under its name; the optional
 * `detail` is drawn under the name. Read through test ids and ARIA states, never through the translated text.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {createRawSnippet} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import BrokerTile from './BrokerTile.svelte';
import type {ScopeBroker} from '../scope';

beforeAll(async () => {
    await setupI18n();
});

afterEach(cleanup);

const broker = (patch: Partial<ScopeBroker> = {}): ScopeBroker => ({id: 7, name: 'Broker Seven', role: 'OWNER', share: null, active: true, selectable: true, iconUrl: null, portalUrl: null, pluginCode: null, ...patch});
const tile = () => screen.getByTestId('t-check');

describe('BrokerTile', () => {
    it('is a button that says whether it is pressed', () => {
        render(BrokerTile, {broker: broker(), pressed: true, testid: 't', ontoggle: () => {}});
        expect(tile().tagName).toBe('BUTTON');
        expect(tile().getAttribute('aria-pressed')).toBe('true');
        expect(tile().getAttribute('data-pressed')).toBe('true');
    });

    it('asks for the opposite state when pressed', async () => {
        const ontoggle = vi.fn();
        render(BrokerTile, {broker: broker(), pressed: false, testid: 't', ontoggle});
        expect(tile().getAttribute('aria-pressed')).toBe('false');
        await fireEvent.click(tile());
        expect(ontoggle).toHaveBeenCalledWith(true);
    });

    it('is off for a Broker that cannot be read from, with its reason', () => {
        render(BrokerTile, {broker: broker({selectable: false, role: 'VIEWER'}), pressed: false, testid: 't', ontoggle: () => {}});
        // A disabled button takes no click in a browser: the state is what is pinned.
        expect((tile() as HTMLButtonElement).disabled).toBe(true);
        expect(screen.getByTestId('t-blocked')).toBeTruthy();
    });

    it('is off for a reason of the caller, with no reason of its own shown', () => {
        render(BrokerTile, {broker: broker(), pressed: false, testid: 't', disabled: true, ontoggle: () => {}});
        expect((tile() as HTMLButtonElement).disabled).toBe(true);
        expect(screen.queryByTestId('t-blocked')).toBeNull();
    });

    it('draws the detail under the name, and nothing when there is none', () => {
        const detail = createRawSnippet(() => ({render: () => '<span data-testid="the-detail">cash</span>'}));
        const {unmount} = render(BrokerTile, {broker: broker(), pressed: false, testid: 't', ontoggle: () => {}, detail});
        expect(screen.getByTestId('t-detail').querySelector('[data-testid="the-detail"]')).toBeTruthy();
        unmount();
        render(BrokerTile, {broker: broker(), pressed: false, testid: 't', ontoggle: () => {}});
        expect(screen.queryByTestId('t-detail')).toBeNull();
    });
});
