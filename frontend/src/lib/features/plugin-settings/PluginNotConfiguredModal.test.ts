// @vitest-environment jsdom
/**
 * PluginNotConfiguredModal — the common window of a provider that is not configured (project 76, D7, lot N3a; mock
 * section 1.4, completed with section 2.4's texts).
 *
 * The contract under test:
 *   - props `{open, family, pluginCode, pluginName?, readiness, zIndex? = 80, onClose, onSaved?}`; root
 *     `plugin-not-configured-modal` (ModalBase), drawn only while open, publishing `data-case` (the case of
 *     `notConfiguredCase`) and `data-plugin`; the title names the provider;
 *   - the message (`plugin-not-configured-message`) is an InfoBanner: warning for a value to set (A, B), error for an
 *     invalid variable or the managed profile (a real stop, rule 12);
 *   - A, `missing_admin`: the message names the missing fields by their labels, read once from the catalogue
 *     (`fetchPluginEntry`, the plugin and the groups a `<group>.<field>` key names); «Configure»
 *     (`plugin-not-configured-configure`) closes the notice and opens the plugin's settings (`plugin-settings-modal`);
 *     a save there hands the fresh entry to `onSaved`;
 *   - B, `missing_member`: the same names, no «Configure», a link to the read-only Settings › Plugins
 *     (`plugin-not-configured-settings-link`, `/settings/plugins`, a new tab: the open form underneath is kept);
 *   - a field whose label cannot be read is named by its key: the window never waits on the catalogue to say why;
 *   - C, `invalid_admin` and `invalid_limit_admin`: the variable named, no «Configure» (the field is locked);
 *   - `invalid_member` and D, `managed`: no variable, no «Configure», no link; D has no button at all;
 *   - «Close» (`plugin-not-configured-close`, every case but D) and Escape ask `onClose`.
 *
 * Mocks: `./pluginSettingsApi` (`fetchPluginEntry` a fake), `$lib/i18n` (`_` answering `key {name=value}`: the text is
 * read as its key and parameters, never as a translation), `$lib/stores/app/auth` (the viewer's role).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

const fake = vi.hoisted(() => ({
    translate(key: string, options?: {values?: Record<string, unknown>}): string {
        // A field's own phrase (N3a2) has a translation: `phrase:<field>`, so the test sees it was used
        if (key.includes('.missing.') && !options) return `phrase:${key.split('.').pop()}`;
        const values = options?.values ?? {};
        const shown = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return shown.length > 0 ? `${key} {${shown.join(', ')}}` : key;
    },
    fetchEntry: vi.fn(),
    admin: true,
}));

vi.mock('./pluginSettingsApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./pluginSettingsApi')>()),
    fetchPluginEntry: fake.fetchEntry,
}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: readable(fake.translate), t: readable(fake.translate)};
});
vi.mock('$lib/stores/app/auth', async () => {
    const {readable} = await import('svelte/store');
    return {auth: {subscribe: (run: (value: unknown) => void) => readable({user: {is_superuser: fake.admin}}).subscribe(run)}};
});

import PluginNotConfiguredModal from './PluginNotConfiguredModal.svelte';
import type {ProviderReadiness} from './notConfigured';

function field(key: string, label: string, missingKey: string | null = null) {
    return {key, label, label_key: null, missing_key: missingKey, description: '', description_key: null, type: 'string', scope: 'system', secret: true, required: true, value: null, is_set: false, locked: false, locked_by: null, options: [], admin_only: true};
}

function entry(family: string, code: string, fields: ReturnType<typeof field>[], groups: string[] = []) {
    return {family, plugin_code: code, plugin_name: code, icon_url: null, configured: false, fields, groups, used_by: [], name_key: null};
}

const MISSING: ProviderReadiness = {configured: false, missing_settings: ['api_key', 'coingecko.plan'], missing_reason: 'missing_fields', invalid_variables: []};
const INVALID: ProviderReadiness = {configured: false, missing_settings: ['api_key'], missing_reason: 'invalid_locked_setting', invalid_variables: ['LIBREFOLIO_PLUGIN_ASSET_KEYED_API_KEY']};
const INVALID_LIMIT: ProviderReadiness = {configured: false, missing_settings: [], missing_reason: 'invalid_locked_setting', invalid_variables: ['LIBREFOLIO_PLUGIN_ASSET_KEYED_CALL_LIMIT_DAY']};
const MANAGED: ProviderReadiness = {configured: false, missing_settings: [], missing_reason: 'invalid_locked_setting', invalid_variables: []};

function mount(readiness: ProviderReadiness, extra: Record<string, unknown> = {}) {
    const onClose = vi.fn();
    const onSaved = vi.fn();
    render(PluginNotConfiguredModal, {props: {open: true, family: 'asset', pluginCode: 'keyed', pluginName: 'Keyed', readiness, onClose, onSaved, ...extra}});
    return {onClose, onSaved};
}

const root = () => screen.getByTestId('plugin-not-configured-modal');
const message = () => screen.getByTestId('plugin-not-configured-message');

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    fake.admin = true;
    fake.fetchEntry.mockReset();
    fake.fetchEntry.mockImplementation(async (family: string, code: string) => {
        if (family === 'asset' && code === 'keyed') return entry('asset', 'keyed', [field('api_key', 'API key')], ['coingecko']);
        if (family === 'group' && code === 'coingecko') return entry('group', 'coingecko', [field('plan', 'Plan')]);
        return null;
    });
});

afterEach(() => cleanup());

describe('A — missing fields, administrator', () => {
    it('names the missing fields by their labels, plugin and group, and offers «Configure»', async () => {
        mount(MISSING);
        expect(root()).toHaveAttribute('data-case', 'missing_admin');
        expect(root()).toHaveAttribute('data-plugin', 'keyed');
        await waitFor(() => expect(message().textContent).toContain('pluginSettings.notConfigured.missingAdmin {count=2, fields=API key, Plan, provider=Keyed}'));
        expect(message()).toHaveAttribute('data-variant', 'warning');
        expect(screen.getByTestId('plugin-not-configured-configure')).toBeInTheDocument();
        expect(screen.queryByTestId('plugin-not-configured-settings-link')).toBeNull();
        expect(fake.fetchEntry).toHaveBeenCalledWith('asset', 'keyed');
        expect(fake.fetchEntry).toHaveBeenCalledWith('group', 'coingecko');
    });

    it('«Configure» closes the notice and opens the plugin settings', async () => {
        mount(MISSING);
        await fireEvent.click(screen.getByTestId('plugin-not-configured-configure'));
        await waitFor(() => expect(screen.getByTestId('plugin-settings-modal')).toBeInTheDocument());
        expect(screen.queryByTestId('plugin-not-configured-modal')).toBeNull();
    });

    it('a label that cannot be read leaves the key: the window still says what is missing', async () => {
        fake.fetchEntry.mockRejectedValue(new Error('down'));
        mount(MISSING);
        await waitFor(() => expect(message().textContent).toContain('fields=api_key, coingecko.plan'));
    });
});

describe("N3a2 — the fields' own phrases", () => {
    function phrased(plan: string | null) {
        fake.fetchEntry.mockImplementation(async (family: string, code: string) => {
            if (family === 'asset' && code === 'keyed') return entry('asset', 'keyed', [field('api_key', 'API key', 'pluginSettings.asset.keyed.missing.api_key')], ['coingecko']);
            if (family === 'group' && code === 'coingecko') return entry('group', 'coingecko', [field('plan', 'Plan', plan)]);
            return null;
        });
    }

    it('every missing field declares a phrase: the phrase text, the phrases joined as a list of the language', async () => {
        phrased('pluginSettings.group.coingecko.missing.plan');
        mount(MISSING);
        await waitFor(() => expect(message().textContent).toContain('pluginSettings.notConfigured.missingAdminPhrase {count=2, fields=phrase:api_key and phrase:plan, provider=Keyed}'));
    });

    it('another user reads the phrase too', async () => {
        fake.admin = false;
        phrased('pluginSettings.group.coingecko.missing.plan');
        mount(MISSING);
        await waitFor(() => expect(message().textContent).toContain('pluginSettings.notConfigured.missingMemberPhrase {count=2, fields=phrase:api_key and phrase:plan, provider=Keyed}'));
    });

    it('one field without a phrase: the labels, for every field', async () => {
        phrased(null);
        mount(MISSING);
        await waitFor(() => expect(message().textContent).toContain('pluginSettings.notConfigured.missingAdmin {count=2, fields=API key, Plan, provider=Keyed}'));
    });
});

describe('B — missing fields, another user', () => {
    it('names the fields, offers no «Configure», links the read-only settings in a new tab', async () => {
        fake.admin = false;
        mount(MISSING);
        expect(root()).toHaveAttribute('data-case', 'missing_member');
        await waitFor(() => expect(message().textContent).toContain('pluginSettings.notConfigured.missingMember {count=2, fields=API key, Plan, provider=Keyed}'));
        expect(screen.queryByTestId('plugin-not-configured-configure')).toBeNull();
        const link = screen.getByTestId('plugin-not-configured-settings-link');
        expect(link).toHaveAttribute('href', '/settings/plugins');
        expect(link).toHaveAttribute('target', '_blank');
    });
});

describe('an invalid variable', () => {
    it('C: the administrator reads the variable, in red, without «Configure»', () => {
        mount(INVALID);
        expect(root()).toHaveAttribute('data-case', 'invalid_admin');
        expect(message().textContent).toContain('pluginSettings.notConfigured.invalidAdmin {variable=LIBREFOLIO_PLUGIN_ASSET_KEYED_API_KEY}');
        expect(message()).toHaveAttribute('data-variant', 'error');
        expect(screen.queryByTestId('plugin-not-configured-configure')).toBeNull();
        expect(fake.fetchEntry).not.toHaveBeenCalled();
    });

    it('a call-limit variable: the limit text, naming the provider too', () => {
        mount(INVALID_LIMIT);
        expect(root()).toHaveAttribute('data-case', 'invalid_limit_admin');
        expect(message().textContent).toContain('pluginSettings.notConfigured.invalidLimitAdmin {provider=Keyed, variable=LIBREFOLIO_PLUGIN_ASSET_KEYED_CALL_LIMIT_DAY}');
    });

    it('another user: the provider is stopped, no variable, no link, «Close» only', () => {
        fake.admin = false;
        mount(INVALID);
        expect(root()).toHaveAttribute('data-case', 'invalid_member');
        expect(message().textContent).toContain('pluginSettings.notConfigured.invalidMember {provider=Keyed}');
        expect(message().textContent).not.toContain('LIBREFOLIO_');
        expect(screen.queryByTestId('plugin-not-configured-settings-link')).toBeNull();
        expect(screen.getByTestId('plugin-not-configured-close')).toBeInTheDocument();
    });

    it('D, the managed profile: no variable, no button at all', () => {
        mount(MANAGED);
        expect(root()).toHaveAttribute('data-case', 'managed');
        expect(message().textContent).toContain('pluginSettings.notConfigured.managed {provider=Keyed}');
        expect(within(root()).queryAllByRole('button')).toHaveLength(0);
    });
});

describe('closing', () => {
    it('«Close» and Escape ask onClose; nothing is drawn while closed', async () => {
        const {onClose} = mount(INVALID);
        await fireEvent.click(screen.getByTestId('plugin-not-configured-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
        await fireEvent.keyDown(root(), {key: 'Escape'});
        expect(onClose).toHaveBeenCalledTimes(2);
        cleanup();
        mount(INVALID, {open: false});
        expect(screen.queryByTestId('plugin-not-configured-modal')).toBeNull();
    });
});
