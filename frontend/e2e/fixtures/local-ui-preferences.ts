import type {BrowserContext} from './playwright';

/**
 * UI preferences are a server-side, per-user setting (`user_settings.ui_preferences`). A spec that runs as a shared user and
 * only wants a chart to draw in a given shape must not write that to the server: every parallel worker signed in as the same
 * user would inherit it. This keeps the choice inside ONE browser context: the settings the page reads (GET /settings/user,
 * and the `user_settings` of the login answer) carry the context's own `ui_preferences`, and a PUT never reaches the server:
 * it is merged here (a key with a value sets, `null` removes, the way the backend does) and answered with the merged body.
 * The app code under test is untouched: it still reads and writes through its store.
 */
export type LocalUiPreferences = {get(): Record<string, string>};

export async function installLocalUiPreferences(context: BrowserContext, initial: Record<string, string> = {}): Promise<LocalUiPreferences> {
    const own: Record<string, string> = {...initial};
    const apply = (settings: Record<string, unknown>) => ({...settings, ui_preferences: {...own}});

    await context.route('**/api/v1/settings/user', async (route) => {
        const method = route.request().method();
        if (method === 'PUT') {
            const sent = (route.request().postDataJSON() ?? {}) as {ui_preferences?: Record<string, string | null>};
            for (const [key, value] of Object.entries(sent.ui_preferences ?? {})) {
                if (value === null) delete own[key];
                else own[key] = value;
            }
            // the real read for the rest of the body, so nothing else the page shows is invented
            const real = await route.fetch({method: 'GET', postData: undefined});
            await route.fulfill({response: real, json: apply((await real.json()) as Record<string, unknown>)});
            return;
        }
        if (method !== 'GET') return route.continue();
        const real = await route.fetch();
        await route.fulfill({response: real, json: apply((await real.json()) as Record<string, unknown>)});
    });

    // the sign-in answer seeds the same store: it must say the same thing
    await context.route('**/api/v1/auth/login', async (route) => {
        const real = await route.fetch();
        const body = (await real.json().catch(() => null)) as Record<string, unknown> | null;
        if (!real.ok() || !body || !body.user_settings) return route.fulfill({response: real});
        const settings = body.user_settings;
        const patched = Array.isArray(settings) ? settings.map((entry) => apply(entry as Record<string, unknown>)) : apply(settings as Record<string, unknown>);
        await route.fulfill({response: real, json: {...body, user_settings: patched}});
    });

    return {get: () => ({...own})};
}
