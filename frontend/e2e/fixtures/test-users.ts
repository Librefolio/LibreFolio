/**
 * Test user credentials
 * These users are created by _ensure_test_users() in test_runner.py
 */

export const TEST_USER = {
    username: 'e2e_test_user',
    email: 'e2e@test.example.com',
    password: 'E2eTestPass123!',
};

export const TEST_ADMIN = {
    username: 'e2e_test_admin',
    email: 'e2eadmin@test.example.com',
    password: 'E2eAdminPass123!',
};

// Second user for multi-user tests
export const TEST_USER_2 = {
    username: 'e2e_test_user2',
    email: 'e2e2@test.example.com',
    password: 'E2eTestPass456!',
};

export const SUPPORTED_LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
export type Language = typeof SUPPORTED_LANGUAGES[number];
