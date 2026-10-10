/**
 * pluginKind — which import plugins are generic fallbacks (the generic CSV), as the backend ranks them.
 *
 * `BRIMProvider.detection_priority` (backend/app/services/brim_provider.py) suggests 100 and up for a
 * plugin made for one broker, 50-99 for a semi-generic one and 0-49 for a generic fallback; the generic
 * CSV answers 0. `isFallbackPlugin` draws that line once, at `FALLBACK_PLUGIN_PRIORITY_LIMIT`, for the
 * two places where a plugin made for the broker must win over a generic one: the import wizard's
 * wrong-broker check and the broker icon chain, where the generic CSV's icon — the same for every
 * broker — comes after the portal's favicon.
 *
 * The boundary is pinned with literals, never with the constant: a limit moved by one would otherwise
 * move the expectations with it. The backend half — the registered plugins below the limit are exactly
 * the generic ones, with the limit read from this module's source — is `TestFallbackPluginPriorityLimit`
 * in backend/test_scripts/test_external/test_brim_providers.py.
 */

import {describe, expect, it} from 'vitest';
import {FALLBACK_PLUGIN_PRIORITY_LIMIT, isFallbackPlugin, type PluginPriority} from './pluginKind';

describe('FALLBACK_PLUGIN_PRIORITY_LIMIT', () => {
    it('is 50: the lowest priority the backend no longer ranks as a generic fallback (0-49)', () => {
        expect(FALLBACK_PLUGIN_PRIORITY_LIMIT).toBe(50);
    });
});

describe('isFallbackPlugin', () => {
    it.each<[priority: number, fallback: boolean, what: string]>([
        [0, true, 'the generic CSV'],
        [49, true, 'the top of the generic range'],
        [50, false, 'the bottom of the semi-generic range'],
        [100, false, 'a plugin made for one broker'],
    ])('detection_priority %i → fallback %s (%s)', (priority, fallback) => {
        expect(isFallbackPlugin({detection_priority: priority})).toBe(fallback);
    });

    it.each<{label: string; plugin: PluginPriority}>([
        {label: 'missing', plugin: {}},
        {label: 'undefined', plugin: {detection_priority: undefined}},
        {label: 'null', plugin: {detection_priority: null}},
    ])('a plugin without a priority ($label) is made for a broker: the backend default is 100', ({plugin}) => {
        expect(isFallbackPlugin(plugin)).toBe(false);
    });

    it('as a filter callback keeps exactly the generic plugins of a list, as the import wizard builds its fallback set', () => {
        const plugins = [{code: 'broker_directa', detection_priority: 100}, {code: 'broker_generic_csv', detection_priority: 0}, {code: 'broker_unranked'}, {code: 'broker_semi_generic', detection_priority: 50}];

        expect(plugins.filter(isFallbackPlugin).map((plugin) => plugin.code)).toEqual(['broker_generic_csv']);
    });
});
