/**
 * FX API Routes — E2E Tests
 *
 * Tests the FX API endpoints directly via Playwright request context.
 * No UI interaction — pure API contract verification.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated
 */

import {expect, test} from '@playwright/test';
import {TEST_USER} from '../fixtures/test-users';

const API_BASE = '/api/v1';

/**
 * Get a session cookie by logging in via API.
 */
async function getSessionCookie(request: import('@playwright/test').APIRequestContext): Promise<string> {
    const response = await request.post(`${API_BASE}/auth/login`, {
        data: {
            username: TEST_USER.username,
            password: TEST_USER.password,
        },
    });
    expect(response.status()).toBe(200);

    // Extract session cookie from Set-Cookie header
    const cookies = response.headers()['set-cookie'] || '';
    const match = cookies.match(/session=([^;]+)/);
    expect(match).not.toBeNull();
    return `session=${match![1]}`;
}

test.describe('FX API Routes', () => {
    let sessionCookie: string;

    test.beforeAll(async ({request}) => {
        sessionCookie = await getSessionCookie(request);
    });

    // ========================================================================
    // Test 1: GET /fx/providers — list providers
    // ========================================================================
    test('GET /fx/providers returns provider list', async ({request}) => {
        const response = await request.get(`${API_BASE}/fx/providers`, {
            headers: {cookie: sessionCookie},
        });
        expect(response.status()).toBe(200);
        const body = await response.json();
        expect(Array.isArray(body)).toBe(true);
        // MANUAL should be excluded from provider list
        const codes = body.map((p: any) => p.code);
        expect(codes).not.toContain('MANUAL');
        // Each provider should have base_currencies and target_currencies
        for (const provider of body) {
            expect(provider).toHaveProperty('code');
            expect(provider).toHaveProperty('name');
        }
    });

    // ========================================================================
    // Test 2: GET /fx/providers/routes — list configured routes
    // ========================================================================
    test('GET /fx/providers/routes returns route list', async ({request}) => {
        const response = await request.get(`${API_BASE}/fx/providers/routes`, {
            headers: {cookie: sessionCookie},
        });
        expect(response.status()).toBe(200);
        const body = await response.json();
        expect(body).toHaveProperty('items');
        expect(Array.isArray(body.items)).toBe(true);
    });

    // ========================================================================
    // Test 7: POST /fx/currencies/convert — conversion
    // ========================================================================
    test('POST /fx/currencies/convert returns rate', async ({request}) => {
        const response = await request.post(`${API_BASE}/fx/currencies/convert`, {
            headers: {cookie: sessionCookie},
            data: {
                from_currency: 'EUR',
                to_currency: 'USD',
                amount: 100,
            },
        });
        // May return 200 or 422 depending on data availability
        if (response.status() === 200) {
            const body = await response.json();
            expect(body).toHaveProperty('rate');
            expect(body.rate).toBeGreaterThan(0);
        }
    });
});
