import {describe, expect, it} from 'vitest';

import {isPortfolioAffectingMutation} from './portfolioMutation';

describe('portfolio mutation classification', () => {
    it.each([
        ['POST', '/api/v1/transactions/commit'],
        ['POST', '/api/v1/brokers'],
        ['PATCH', '/api/v1/brokers/42'],
        ['PUT', '/api/v1/brokers/42/access'],
        ['PATCH', '/api/v1/assets'],
        ['POST', '/api/v1/assets/42/market-data/wipe'],
        ['POST', '/api/v1/assets/prices/current'],
        ['POST', '/api/v1/assets/prices/sync'],
        ['DELETE', '/api/v1/assets/events'],
        ['POST', '/api/v1/fx/currencies/sync'],
        ['DELETE', '/api/v1/fx/providers/routes'],
    ])('invalidates after %s %s', (method, path) => {
        expect(isPortfolioAffectingMutation(method, path)).toBe(true);
    });

    it.each([
        ['GET', '/api/v1/transactions'],
        ['POST', '/api/v1/transactions/validate'],
        ['POST', '/api/v1/portfolio/report'],
        ['POST', '/api/v1/assets/prices/query'],
        ['POST', '/api/v1/assets/events/query'],
        ['POST', '/api/v1/assets/provider/probe'],
        ['POST', '/api/v1/fx/currencies/convert'],
        ['POST', '/api/v1/auth/login'],
    ])('preserves cache after read-only %s %s', (method, path) => {
        expect(isPortfolioAffectingMutation(method, path)).toBe(false);
    });
});
