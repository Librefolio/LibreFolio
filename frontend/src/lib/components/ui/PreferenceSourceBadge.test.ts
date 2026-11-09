// @vitest-environment jsdom
import {describe, expect, it, vi} from 'vitest';

// Identity translator: the badge renders i18n keys, and the test pins the keys, not a language.
vi.mock('$lib/i18n', async () => {
    const {readable} = await import('svelte/store');
    return {_: readable((key: string) => key)};
});

import {render, screen} from '$test/component';
import PreferenceSourceBadge from './PreferenceSourceBadge.svelte';

describe('PreferenceSourceBadge', () => {
    it('global: carries the testid, data-source and the global keys', () => {
        render(PreferenceSourceBadge, {kind: 'global', testId: 'pref-badge-global'});
        const badge = screen.getByTestId('pref-badge-global');
        expect(badge).toHaveAttribute('data-source', 'global');
        expect(badge).toHaveTextContent('settings.preferenceSource.global');
        expect(badge).toHaveAttribute('title', 'settings.preferenceSource.globalHint');
    });

    it('auto: carries the testid, data-source and the auto keys', () => {
        render(PreferenceSourceBadge, {kind: 'auto', testId: 'pref-badge-auto'});
        const badge = screen.getByTestId('pref-badge-auto');
        expect(badge).toHaveAttribute('data-source', 'auto');
        expect(badge).toHaveTextContent('settings.preferenceSource.auto');
        expect(badge).toHaveAttribute('title', 'settings.preferenceSource.autoHint');
    });
});
