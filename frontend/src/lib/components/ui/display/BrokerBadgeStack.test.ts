// @vitest-environment jsdom
/**
 * BrokerBadgeStack — the brokers a «Globale» row stands for (project 74): one icon each, «+N» past the cap, every name in the
 * tooltip and in the accessible label. Brokers are found by their `broker-badge-<id>` test ids, never by text.
 */
import {beforeAll, beforeEach, describe, expect, it} from 'vitest';

import {render, screen, setupI18n} from '$test/component';
import BrokerBadgeStack from './BrokerBadgeStack.svelte';

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    document.body.innerHTML = '';
});

const brokers = [
    {id: 11, name: 'Alpha'},
    {id: 12, name: 'Beta'},
    {id: 13, name: 'Gamma'},
    {id: 14, name: 'Delta'},
];

describe('BrokerBadgeStack', () => {
    it('draws one icon per broker up to the cap, then «+N»', () => {
        render(BrokerBadgeStack, {props: {brokers, max: 3}});
        const stack = screen.getByTestId('broker-badge-stack');
        expect(stack.getAttribute('data-count')).toBe('4');
        for (const id of [11, 12, 13]) expect(screen.getByTestId(`broker-badge-${id}`)).toBeTruthy();
        expect(screen.queryByTestId('broker-badge-14')).toBeNull();
        expect(screen.getByTestId('broker-badge-stack-more').textContent?.trim()).toBe('+1');
    });

    it('names every broker in the accessible label, the hidden ones too', () => {
        render(BrokerBadgeStack, {props: {brokers, max: 2}});
        expect(screen.getByTestId('broker-badge-stack').getAttribute('aria-label')).toBe('Alpha, Beta, Gamma, Delta');
    });

    it('no «+N» when every broker fits, and the count text only when given', () => {
        render(BrokerBadgeStack, {props: {brokers: brokers.slice(0, 2)}});
        expect(screen.queryByTestId('broker-badge-stack-more')).toBeNull();
        expect(screen.queryByTestId('broker-badge-stack-count')).toBeNull();
        document.body.innerHTML = '';
        render(BrokerBadgeStack, {props: {brokers: brokers.slice(0, 2), countLabel: '2 brokers'}});
        expect(screen.getByTestId('broker-badge-stack-count')).toBeTruthy();
    });
});
