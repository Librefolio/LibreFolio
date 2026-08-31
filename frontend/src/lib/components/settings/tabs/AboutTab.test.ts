// @vitest-environment jsdom
/**
 * AboutTab — component test (Vitest + jsdom).
 *
 * The diagnostics page: version and platform facts, the installed plugin
 * inventory, the per-plugin-system discovery report, and the "copy for issue"
 * payload a user pastes into a bug report.
 *
 * Why a component test and not an E2E. Almost everything interesting here is a
 * *shape* question — what the clipboard string contains, whether an empty
 * provider list hides its section, whether a signal without a docs path degrades
 * from a link to a plain box — and the shapes come from seven endpoints that are
 * each `.catch()`-guarded independently. Making the real backend return "FX
 * providers listed, asset providers 500" is not something an E2E can ask for;
 * here it is one line. The same goes for the client-side facts (`devicePixelRatio`,
 * the stored theme, the stored locale), which a browser test would have to accept
 * rather than choose.
 *
 * On not asserting translated text. `$lib/i18n` is mocked with an identity
 * translator, so every label renders as its own i18n key. Two places are asserted
 * on literal English anyway, and deliberately: the clipboard payload is
 * *specified* to be always-English (`THEME_LABELS[…].en`, `'Docker'`/`'Local'`)
 * because it is meant to be pasted into an issue read by maintainers, so the
 * English words are the contract, not a translation.
 *
 * What it deliberately does NOT assert:
 *   - the layout of the two dependency tables beyond "the rows I supplied are
 *     listed"; the grid is presentation.
 *   - `scrollOnOverflow` / `Tooltip` behaviour — separate components, separate lane.
 *   - the exact `Generated:` timestamp, which is `new Date().toISOString()`; the
 *     assertion is that the line is present, not what it says.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {fireEvent, render, screen, waitFor, within} from '$test/component';

// --- Mocks --------------------------------------------------------------

vi.mock('$lib/i18n', () => {
    const identity = readable((key: string) => key);
    return {
        _: identity,
        t: identity,
        locale: writable('en'),
        date: readable((v: unknown) => String(v)),
        time: readable((v: unknown) => String(v)),
        number: readable((v: unknown) => String(v)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

const storedTheme = vi.fn<() => 'light' | 'dark' | 'auto'>(() => 'light');
const resolvedTheme = vi.fn<() => 'light' | 'dark'>(() => 'light');
vi.mock('$lib/stores/app/themeStore', () => ({
    getStoredThemePreference: () => storedTheme(),
    getCurrentResolvedTheme: () => resolvedTheme(),
    applyTheme: vi.fn(),
}));

const registeredSignals = vi.fn<() => unknown[]>(() => []);
vi.mock('$lib/charts/signals/registry', () => ({getRegisteredSignalTypes: () => registeredSignals()}));

// The catalogue mapper is a strict translator with its own rules and its own
// tests; what AboutTab owns is what it does with the *result*. Mocking it to a
// pass-through keeps this file honest about which contract it is checking.
vi.mock('$lib/charts/signals/catalogMapper', () => ({mapBackendSignalDefinition: (raw: unknown) => raw}));

import AboutTab from './AboutTab.svelte';
import {zodiosApi} from '$lib/api';

// --- Fixtures -----------------------------------------------------------

const SYSTEM_INFO = {
    app_version: '2.4.1',
    python_version: '3.12.2',
    os_name: 'Linux',
    os_version: '6.8.0',
    platform: 'Linux-6.8.0-x86_64',
    deployment_mode: 'local',
    backend_dependencies: [{name: 'fastapi', version: '0.115.0'}],
    frontend_dependencies: [{name: 'svelte', version: '5.0.0'}],
};

const api = {
    sys: () => vi.mocked(zodiosApi.get_system_info_api_v1_system_info_get as never) as ReturnType<typeof vi.fn>,
    asset: () => vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get as never) as ReturnType<typeof vi.fn>,
    fx: () => vi.mocked(zodiosApi.list_providers_api_v1_fx_providers_get as never) as ReturnType<typeof vi.fn>,
    brim: () => vi.mocked(zodiosApi.list_plugins_api_v1_brokers_import_plugins_get as never) as ReturnType<typeof vi.fn>,
    diag: () => vi.mocked(zodiosApi.get_plugin_diagnostics_api_v1_system_plugin_diagnostics_get as never) as ReturnType<typeof vi.fn>,
    assetSignals: () => vi.mocked(zodiosApi.list_asset_signal_catalog_api_v1_assets_prices_signals_get as never) as ReturnType<typeof vi.fn>,
    fxSignals: () => vi.mocked(zodiosApi.list_fx_signal_catalog_api_v1_fx_currencies_signals_get as never) as ReturnType<typeof vi.fn>,
};

/** A catalogue entry as AboutTab sees it, i.e. already through the mapper. */
function backendSignal(type: string, extra: Record<string, unknown> = {}) {
    return {type, displayName: type.toUpperCase(), icon: type.slice(0, 1).toUpperCase(), category: 'trend', ...extra};
}

const writeText = vi.fn(async (_text: string) => undefined);

/**
 * A local-storage stand-in. jsdom under this Node build exposes no usable
 * `localStorage`, and the component reads `librefolio-locale` from it in three
 * different places, so the test owns one rather than skipping those branches.
 */
const stored = new Map<string, string>();
const localStorageStub = {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => void stored.set(key, String(value)),
    removeItem: (key: string) => void stored.delete(key),
    clear: () => stored.clear(),
    key: (index: number) => [...stored.keys()][index] ?? null,
    get length() {
        return stored.size;
    },
};
const setLocale = (locale: string) => stored.set('librefolio-locale', locale);

/** Mount and wait for the seven-call `Promise.all` on mount to have settled. */
async function mount() {
    const utils = render(AboutTab);
    await waitFor(() => expect(screen.queryByTestId('about-plugin-diagnostics')).not.toBeNull());
    return utils;
}

const copyButton = () => screen.getByRole('button', {name: /settings\.copyForIssue|common\.copied/});
const diagnosticsFor = (system: string) => screen.getByTestId(`about-plugin-diagnostics-${system}`);

beforeEach(() => {
    vi.clearAllMocks();
    stored.clear();
    Object.defineProperty(globalThis, 'localStorage', {value: localStorageStub, configurable: true, writable: true});
    Object.defineProperty(window, 'localStorage', {value: localStorageStub, configurable: true, writable: true});
    api.sys().mockResolvedValue(SYSTEM_INFO as never);
    api.asset().mockResolvedValue([] as never);
    api.fx().mockResolvedValue([] as never);
    api.brim().mockResolvedValue([] as never);
    api.diag().mockResolvedValue([] as never);
    api.assetSignals().mockResolvedValue({items: []} as never);
    api.fxSignals().mockResolvedValue({items: []} as never);
    registeredSignals.mockReturnValue([]);
    storedTheme.mockReturnValue('light');
    resolvedTheme.mockReturnValue('light');
    Object.defineProperty(navigator, 'clipboard', {value: {writeText}, configurable: true, writable: true});
});

afterEach(() => {
    vi.useRealTimers();
});

// =========================================================================
describe('AboutTab — loading and the version header', () => {
    it('shows an ellipsis for the version until the server answers', async () => {
        // The header is rendered outside the loading gate, so it needs its own
        // placeholder — this pins that it has one rather than rendering "undefined".
        let release!: (v: unknown) => void;
        api.sys().mockReturnValue(new Promise((res) => (release = res)) as never);
        render(AboutTab);

        expect(screen.getByTestId('about-version')).toHaveTextContent('...');

        release(SYSTEM_INFO);
        await waitFor(() => expect(screen.getByTestId('about-version')).toHaveTextContent('2.4.1'));
    });

    it('keeps the copy button unusable while there is nothing to copy', async () => {
        let release!: (v: unknown) => void;
        api.sys().mockReturnValue(new Promise((res) => (release = res)) as never);
        render(AboutTab);

        expect(copyButton()).toBeDisabled();

        release(SYSTEM_INFO);
        await waitFor(() => expect(copyButton()).toBeEnabled());
    });

    it('leaves the diagnostics grid out entirely when the system call fails', async () => {
        // `get_system_info` is the one call in the `Promise.all` with no
        // per-call `.catch()`, so its rejection aborts the whole block: no
        // system facts, no plugin inventory, and a permanently disabled button.
        api.sys().mockRejectedValue(new Error('boom'));
        await mount();

        expect(copyButton()).toBeDisabled();
        expect(screen.getByTestId('about-version')).toHaveTextContent('...');
        // No system facts at all: the whole `{:else if systemInfo}` grid is gone.
        expect(screen.queryByText('settings.appVersion')).toBeNull();
        expect(screen.queryByText('settings.deploymentMode')).toBeNull();
        // The page itself still renders: the links and the credits are static.
        expect(screen.getByTestId('about-tab')).toBeInTheDocument();
    });

    it('still shows the system facts when only the provider lists fail', async () => {
        // Each secondary call carries its own `.catch(() => [])`, which is what
        // makes a half-broken backend degrade instead of blanking the page.
        api.asset().mockRejectedValue(new Error('no assets'));
        api.fx().mockRejectedValue(new Error('no fx'));
        api.brim().mockRejectedValue(new Error('no brim'));
        api.diag().mockRejectedValue(new Error('no diagnostics'));
        api.assetSignals().mockRejectedValue(new Error('no signals'));
        api.fxSignals().mockRejectedValue(new Error('no fx signals'));

        await mount();

        expect(screen.getByTestId('about-version')).toHaveTextContent('2.4.1');
        expect(copyButton()).toBeEnabled();
        // All four systems report "ok", because a failed *diagnostics* call is
        // not the same as a failed plugin.
        for (const system of ['asset', 'fx', 'brim', 'signals']) {
            expect(diagnosticsFor(system)).toHaveAttribute('data-status', 'ok');
        }
    });
});

// =========================================================================
describe('AboutTab — the system facts it reports', () => {
    it('names the deployment mode by its own label, not by the raw enum', async () => {
        await mount();

        expect(screen.getByText('settings.deploymentMode').closest('div')!.parentElement).toHaveTextContent('settings.deploymentModeLocal');
    });

    it('switches the deployment label for a container install', async () => {
        api.sys().mockResolvedValue({...SYSTEM_INFO, deployment_mode: 'docker'} as never);
        await mount();

        expect(screen.getByText('settings.deploymentMode').closest('div')!.parentElement).toHaveTextContent('settings.deploymentModeDocker');
    });

    it('reports the stored theme preference on its own', async () => {
        storedTheme.mockReturnValue('dark');
        resolvedTheme.mockReturnValue('dark');
        await mount();

        const row = screen.getByText('settings.theme').closest('div')!.parentElement!;
        expect(row).toHaveTextContent('settings.themeDark');
        // "auto" is the only preference that also names what it resolved to.
        expect(row).not.toHaveTextContent('(');
    });

    it('adds the resolved theme in brackets when the preference is automatic', async () => {
        storedTheme.mockReturnValue('auto');
        resolvedTheme.mockReturnValue('dark');
        await mount();

        const row = screen.getByText('settings.theme').closest('div')!.parentElement!;
        expect(row).toHaveTextContent('settings.themeAuto');
        expect(row).toHaveTextContent('(settings.themeDark)');
    });

    it('falls back to English when no locale was ever stored', async () => {
        await mount();

        expect(screen.getByText('settings.language').closest('div')!.parentElement).toHaveTextContent('English');
    });

    it('reports the stored locale by its display name', async () => {
        setLocale('it');
        await mount();

        expect(screen.getByText('settings.language').closest('div')!.parentElement).toHaveTextContent('Italiano');
    });

    it('lists the dependencies the server sent, both sides', async () => {
        await mount();

        expect(screen.getByText('fastapi')).toBeInTheDocument();
        expect(screen.getByText('svelte')).toBeInTheDocument();
    });
});

// =========================================================================
describe('AboutTab — copy for issue', () => {
    it('puts the facts on the clipboard in the always-English report form', async () => {
        setLocale('it');
        api.asset().mockResolvedValue([{code: 'yf', name: 'Yahoo Finance'}] as never);
        api.fx().mockResolvedValue([{code: 'ecb', name: 'European Central Bank'}] as never);
        api.brim().mockResolvedValue([{code: 'degiro', name: 'DEGIRO'}] as never);
        await mount();

        await fireEvent.click(copyButton());

        await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
        const payload = writeText.mock.calls[0][0];
        expect(payload).toContain('App Version: 2.4.1');
        expect(payload).toContain('Python: 3.12.2');
        expect(payload).toContain('OS: Linux 6.8.0');
        expect(payload).toContain('Platform: Linux-6.8.0-x86_64');
        // Always English, on purpose: this text is pasted into a GitHub issue.
        expect(payload).toContain('Deployment Mode: Local');
        expect(payload).toContain('Theme: Light');
        expect(payload).toContain('Language: Italiano (it)');
        expect(payload).toContain('  - fastapi: 0.115.0');
        expect(payload).toContain('  - svelte: 5.0.0');
        expect(payload).toContain('  - Yahoo Finance');
        expect(payload).toContain('  - European Central Bank');
        expect(payload).toContain('  - DEGIRO');
        expect(payload).toContain('Generated: ');
    });

    it('says Docker in the report when that is how it runs', async () => {
        api.sys().mockResolvedValue({...SYSTEM_INFO, deployment_mode: 'docker'} as never);
        await mount();

        await fireEvent.click(copyButton());

        await waitFor(() => expect(writeText).toHaveBeenCalled());
        expect(writeText.mock.calls[0][0]).toContain('Deployment Mode: Docker');
    });

    it('spells out both halves of an automatic theme', async () => {
        storedTheme.mockReturnValue('auto');
        resolvedTheme.mockReturnValue('dark');
        await mount();

        await fireEvent.click(copyButton());

        await waitFor(() => expect(writeText).toHaveBeenCalled());
        expect(writeText.mock.calls[0][0]).toContain('Theme: Auto (Dark)');
    });

    it('names a fixed preference without brackets', async () => {
        storedTheme.mockReturnValue('dark');
        resolvedTheme.mockReturnValue('light');
        await mount();

        await fireEvent.click(copyButton());

        await waitFor(() => expect(writeText).toHaveBeenCalled());
        const payload = writeText.mock.calls[0][0];
        expect(payload).toContain('Theme: Dark\n');
    });

    it('confirms the copy, then takes the confirmation back after two seconds', async () => {
        vi.useFakeTimers();
        render(AboutTab);
        await vi.waitFor(() => expect(screen.queryByTestId('about-plugin-diagnostics')).not.toBeNull());

        await fireEvent.click(copyButton());
        await vi.waitFor(() => expect(screen.queryByRole('button', {name: 'common.copied'})).not.toBeNull());

        await vi.advanceTimersByTimeAsync(1_900);
        expect(screen.queryByRole('button', {name: 'common.copied'})).not.toBeNull();

        await vi.advanceTimersByTimeAsync(200);
        await vi.waitFor(() => expect(screen.queryByRole('button', {name: 'settings.copyForIssue'})).not.toBeNull());
    });
});

// =========================================================================
describe('AboutTab — the installed plugin inventory', () => {
    it('omits a provider section entirely when nothing is installed', async () => {
        await mount();

        expect(screen.queryByText('settings.assetProviders')).toBeNull();
        expect(screen.queryByText('settings.fxProviders')).toBeNull();
        expect(screen.queryByText('settings.importPlugins')).toBeNull();
    });

    it('shows each section only when its own list has something in it', async () => {
        api.fx().mockResolvedValue([{code: 'ecb', name: 'European Central Bank'}] as never);
        await mount();

        expect(screen.getByText('European Central Bank')).toBeInTheDocument();
        // The other two are still empty and still absent: the three sections are
        // independent, not one block.
        expect(screen.queryByText('settings.assetProviders')).toBeNull();
        expect(screen.queryByText('settings.importPlugins')).toBeNull();
    });

    it('links an asset provider to its help page when it declares one', async () => {
        api.asset().mockResolvedValue([{code: 'yf', name: 'Yahoo Finance', provider_help_url: 'https://help.test/yf'}] as never);
        await mount();

        expect(screen.getByText('Yahoo Finance').closest('a')).toHaveAttribute('href', 'https://help.test/yf');
    });

    it('falls back to the docs url when there is no dedicated help page', async () => {
        api.asset().mockResolvedValue([{code: 'yf', name: 'Yahoo Finance', docs_url: 'https://docs.test/yf'}] as never);
        await mount();

        expect(screen.getByText('Yahoo Finance').closest('a')).toHaveAttribute('href', 'https://docs.test/yf');
    });

    it('renders a provider with neither url as a plain box, not a dead link', async () => {
        api.asset().mockResolvedValue([{code: 'yf', name: 'Yahoo Finance'}] as never);
        await mount();

        expect(screen.getByText('Yahoo Finance').closest('a')).toBeNull();
    });

    it('shows the provider icon when one is published and a letter tile otherwise', async () => {
        api.asset().mockResolvedValue([
            {code: 'yf', name: 'Yahoo Finance', icon_url: 'https://cdn.test/yf.png'},
            {code: 'st', name: 'Stooq'},
        ] as never);
        await mount();

        const withIcon = screen.getByText('Yahoo Finance').closest('div')!.parentElement!;
        expect(within(withIcon).getByRole('img')).toHaveAttribute('src', 'https://cdn.test/yf.png');
        const withoutIcon = screen.getByText('Stooq').closest('div')!.parentElement!;
        expect(within(withoutIcon).queryByRole('img')).toBeNull();
    });

    it('localises an import plugin docs link, and leaves English alone', async () => {
        // `getDocsUrl` injects the locale segment into the mkdocs path — except
        // for English, whose pages live at the un-prefixed root.
        api.brim().mockResolvedValue([{code: 'degiro', name: 'DEGIRO', docs_url: '/mkdocs/plugins/degiro/'}] as never);
        await mount();
        expect(screen.getByText('DEGIRO').closest('a')).toHaveAttribute('href', '/mkdocs/plugins/degiro/');

        setLocale('fr');
        await mount();
        const links = screen.getAllByText('DEGIRO').map((n) => n.closest('a')!.getAttribute('href'));
        expect(links).toContain('/mkdocs/fr/plugins/degiro/');
    });

    it('offers no link for an import plugin without docs', async () => {
        api.brim().mockResolvedValue([{code: 'degiro', name: 'DEGIRO'}] as never);
        await mount();

        expect(screen.getByText('DEGIRO').closest('a')).toBeNull();
    });
});

// =========================================================================
describe('AboutTab — the installed signals', () => {
    it('lists what the two catalogues returned, once each', async () => {
        api.assetSignals().mockResolvedValue({items: [backendSignal('sma')]} as never);
        api.fxSignals().mockResolvedValue({items: [backendSignal('ema')]} as never);
        await mount();

        expect(screen.getByTestId('about-installed-signal-sma')).toBeInTheDocument();
        expect(screen.getByTestId('about-installed-signal-ema')).toBeInTheDocument();
    });

    it('keeps one entry when the same signal comes back from both catalogues', async () => {
        // The map is keyed by type precisely so a signal offered for both assets
        // and currencies is not listed twice.
        api.assetSignals().mockResolvedValue({items: [backendSignal('sma')]} as never);
        api.fxSignals().mockResolvedValue({items: [backendSignal('sma')]} as never);
        await mount();

        expect(screen.getAllByTestId('about-installed-signal-sma')).toHaveLength(1);
    });

    it('treats a catalogue with no items array as empty', async () => {
        api.assetSignals().mockResolvedValue({} as never);
        api.fxSignals().mockResolvedValue({} as never);
        await mount();

        expect(screen.getByTestId('about-installed-signals')).toHaveTextContent('(0)');
    });

    it('sorts by the key when there is one and by the display name otherwise', async () => {
        registeredSignals.mockReturnValue([
            {type: 'zeta', displayName: 'Alpha', icon: 'A', category: 'trend'},
            {type: 'alpha', displayNameKey: 'signals.zulu', displayName: 'Zulu', icon: 'Z', category: 'trend'},
        ]);
        await mount();

        const order = screen.getAllByTestId(/^about-installed-signal-/).map((n) => n.getAttribute('data-testid'));
        // 'Alpha' < 'signals.zulu' — the key wins over the display name when present.
        expect(order).toEqual(['about-installed-signal-zeta', 'about-installed-signal-alpha']);
    });

    it('lets a locally registered signal override the backend one of the same type', async () => {
        api.assetSignals().mockResolvedValue({items: [backendSignal('sma')]} as never);
        registeredSignals.mockReturnValue([{type: 'sma', displayName: 'Locally registered', icon: 'S', category: 'trend'}]);
        await mount();

        expect(screen.getAllByTestId('about-installed-signal-sma')).toHaveLength(1);
        expect(screen.getByTestId('about-installed-signal-sma')).toHaveTextContent('Locally registered');
    });

    it('links a signal that documents itself and leaves the rest as plain boxes', async () => {
        registeredSignals.mockReturnValue([
            {type: 'documented', displayName: 'Documented', icon: 'D', category: 'trend', docsPath: 'mkdocs/signals/documented'},
            {type: 'bare', displayName: 'Bare', icon: 'B', category: 'trend'},
        ]);
        await mount();

        expect(screen.getByTestId('about-installed-signal-documented').tagName).toBe('A');
        expect(screen.getByTestId('about-installed-signal-documented')).toHaveAttribute('href', '/mkdocs/signals/documented/');
        expect(screen.getByTestId('about-installed-signal-bare').tagName).toBe('DIV');
        expect(screen.getByTestId('about-installed-signal-bare')).not.toHaveAttribute('href');
    });

    it('prefixes the signal docs path with the stored locale', async () => {
        setLocale('es');
        registeredSignals.mockReturnValue([{type: 'documented', displayName: 'Documented', icon: 'D', category: 'trend', docsPath: '/mkdocs/signals/documented/'}]);
        await mount();

        expect(screen.getByTestId('about-installed-signal-documented')).toHaveAttribute('href', '/mkdocs/es/signals/documented/');
    });

    it('prefers the backend code over the type as the secondary line', async () => {
        // `{signal.backendSignalCode ?? signal.type}` — the code the server knows
        // it by is more useful in a bug report than the front-end slug.
        api.assetSignals().mockResolvedValue({items: [backendSignal('sma', {backendSignalCode: 'SMA_20'})]} as never);
        await mount();

        expect(screen.getByTestId('about-installed-signal-sma')).toHaveTextContent('SMA_20');
    });
});

// =========================================================================
describe('AboutTab — the plugin discovery report', () => {
    it('reports all four systems as healthy when nothing failed to load', async () => {
        await mount();

        for (const system of ['asset', 'fx', 'brim', 'signals']) {
            expect(diagnosticsFor(system)).toHaveAttribute('data-status', 'ok');
            expect(diagnosticsFor(system)).toHaveAttribute('data-failures', '0');
            expect(diagnosticsFor(system)).toHaveTextContent('settings.pluginDiagnosticsAllLoaded');
        }
    });

    it('marks only the system that failed, and counts its failures', async () => {
        api.diag().mockResolvedValue([
            {system: 'brim', filename: 'broken_broker.py', error: 'ImportError: no module named pandas'},
            {system: 'brim', filename: 'other.py', error: 'SyntaxError: line 3'},
        ] as never);
        await mount();

        expect(diagnosticsFor('brim')).toHaveAttribute('data-status', 'failed');
        expect(diagnosticsFor('brim')).toHaveAttribute('data-failures', '2');
        expect(diagnosticsFor('asset')).toHaveAttribute('data-status', 'ok');
        expect(diagnosticsFor('fx')).toHaveAttribute('data-status', 'ok');
        expect(diagnosticsFor('signals')).toHaveAttribute('data-status', 'ok');
    });

    it('names the file and the reason, so the report is actionable', async () => {
        api.diag().mockResolvedValue([{system: 'asset', filename: 'my_provider.py', error: 'ImportError: no module named yfinance'}] as never);
        await mount();

        const card = diagnosticsFor('asset');
        expect(card).toHaveTextContent('my_provider.py');
        expect(card).toHaveTextContent('ImportError: no module named yfinance');
    });

    it('keeps each system to its own failures', async () => {
        api.diag().mockResolvedValue([
            {system: 'fx', filename: 'fx_one.py', error: 'boom'},
            {system: 'signals', filename: 'sig_one.py', error: 'bang'},
        ] as never);
        await mount();

        expect(diagnosticsFor('fx')).toHaveTextContent('fx_one.py');
        expect(diagnosticsFor('fx')).not.toHaveTextContent('sig_one.py');
        expect(diagnosticsFor('signals')).toHaveTextContent('sig_one.py');
        expect(diagnosticsFor('signals')).not.toHaveTextContent('fx_one.py');
    });
});
