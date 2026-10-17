<script lang="ts">
    import {_} from '$lib/i18n';
    import {LOCALE_NAMES, type SupportedLocale} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {onDestroy, onMount} from 'svelte';
    import {AppWindow, Check, ChevronDown, Container, Copy, ExternalLink, Github, Globe, HardDrive, Heart, Info, Languages, Layers, Maximize2, Monitor, Scale, SunMoon, Tag} from 'lucide-svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SupportActions from '$lib/features/support/SupportActions.svelte';
    import LegalNotice from '$lib/features/legal/LegalNotice.svelte';
    import SocialShareModal from '$lib/features/support/SocialShareModal.svelte';
    import type {SocialPlatform} from '$lib/features/support/supportLinks';
    import ToolAboutPanel from '$lib/features/tools/ToolAboutPanel.svelte';
    import {mapBackendSignalDefinition} from '$lib/charts/signals/catalogMapper';
    import {getRegisteredSignalTypes} from '$lib/charts/signals/registry';
    import type {BackendSignalCatalogResponse, SignalDefinition} from '$lib/charts/signals';
    import {getCurrentResolvedTheme, getStoredThemePreference, type ThemePreference} from '$lib/stores/app/themeStore';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import ChangelogModal from '$lib/components/layout/ChangelogModal.svelte';
    import {brimPluginName} from '$lib/utils/brim/pluginText';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import {toasts} from '$lib/stores/app/toastStore.svelte';

    let changelogOpen = false;
    let toolPanelOpen = false;

    const githubUrl = 'https://github.com/Librefolio/LibreFolio';
    const websiteUrl = 'https://librefolio.github.io/LibreFolio/';

    interface DependencyInfo {
        name: string;
        version: string;
    }

    interface SystemInfo {
        app_version: string;
        python_version: string;
        os_name: string;
        os_version: string;
        platform: string;
        deployment_mode: string;
        backend_dependencies: DependencyInfo[];
        frontend_dependencies: DependencyInfo[];
    }

    // i18n key + English label (for the always-English "Copy for Issue" text) per theme preference
    const THEME_LABELS: Record<ThemePreference, {key: string; en: string}> = {
        light: {key: 'settings.themeLight', en: 'Light'},
        dark: {key: 'settings.themeDark', en: 'Dark'},
        auto: {key: 'settings.themeAuto', en: 'Auto'},
    };

    interface ProviderInfo {
        code: string;
        name: string;
        description?: string;
        icon_url?: string | null;
        provider_help_url?: string | null; // asset providers
        docs_url?: string | null; // fx providers
    }

    interface PluginDiscoveryFailureInfo {
        system: PluginSystem;
        filename: string;
        error: string;
    }

    type PluginSystem = 'asset' | 'fx' | 'brim' | 'signals';

    const PLUGIN_SYSTEMS: Array<{system: PluginSystem; labelKey: string}> = [
        {system: 'asset', labelKey: 'settings.pluginSystemAsset'},
        {system: 'fx', labelKey: 'settings.pluginSystemFx'},
        {system: 'brim', labelKey: 'settings.pluginSystemBrim'},
        {system: 'signals', labelKey: 'settings.pluginSystemSignals'},
    ];

    let systemInfo: SystemInfo | null = null;
    let isLoading = true;
    let copied = false;

    let assetProviders: ProviderInfo[] = [];
    let fxProviders: ProviderInfo[] = [];
    let importPlugins: ProviderInfo[] = [];
    let pluginDiscoveryFailures: PluginDiscoveryFailureInfo[] = [];
    let installedSignals: SignalDefinition[] = [];
    let sharePlatform: SocialPlatform | null = null;

    /** Provider icons that failed to load (CDN blocks, dead URLs) — fall back to the letter tile. */
    let failedIconUrls: Set<string> = new Set();

    function markIconFailed(url: string) {
        failedIconUrls = new Set(failedIconUrls).add(url);
    }

    /** Letter-tile fallback: skip the `broker_`/`broker-` prefix and take the
     *  initials of the remaining words (broker_credit_agricole → "CA"). */
    function codeInitials(code: string): string {
        const words = code
            .replace(/^broker[_-]/, '')
            .split(/[_-]+/)
            .filter(Boolean);
        const letters = (words.length > 1 ? words.map((w) => w[0]) : [code.slice(0, 1), code.slice(1, 2)]).join('');
        return letters.toUpperCase();
    }

    // Client-side diagnostic fields (no backend round-trip needed) — useful for UI bug reports.
    let viewportWidth = 0;
    let viewportHeight = 0;
    let devicePixelRatio = 1;
    let userAgent = '';
    let themePreference: ThemePreference = 'auto';
    let themeResolved: 'light' | 'dark' = 'light';
    let currentLocale: SupportedLocale = 'en';

    function updateViewport() {
        viewportWidth = window.innerWidth;
        viewportHeight = window.innerHeight;
        devicePixelRatio = window.devicePixelRatio;
    }

    onMount(async () => {
        updateViewport();
        window.addEventListener('resize', updateViewport);

        userAgent = navigator.userAgent;
        themePreference = getStoredThemePreference();
        themeResolved = getCurrentResolvedTheme();
        currentLocale = (localStorage.getItem('librefolio-locale') as SupportedLocale) || 'en';

        try {
            const [sysInfo, assetProv, fxProv, brimPlugins, pluginDiagnostics, assetSignalCatalog, fxSignalCatalog] = await Promise.all([
                zodiosApi.get_system_info_api_v1_system_info_get(),
                zodiosApi.list_providers_api_v1_assets_provider_get().catch(() => []),
                zodiosApi.list_providers_api_v1_fx_providers_get().catch(() => []),
                zodiosApi.list_plugins_api_v1_brokers_import_plugins_get().catch(() => []),
                zodiosApi.get_plugin_diagnostics_api_v1_system_plugin_diagnostics_get().catch(() => []),
                zodiosApi.list_asset_signal_catalog_api_v1_assets_prices_signals_get().catch(() => ({items: []})),
                zodiosApi.list_fx_signal_catalog_api_v1_fx_currencies_signals_get().catch(() => ({items: []})),
            ]);
            // Without a valid session the answer is the version only (GET /system/info): no report to show.
            systemInfo = 'python_version' in sysInfo ? (sysInfo as SystemInfo) : null;
            assetProviders = assetProv as ProviderInfo[];
            fxProviders = fxProv as ProviderInfo[];
            importPlugins = brimPlugins as ProviderInfo[];
            pluginDiscoveryFailures = pluginDiagnostics as PluginDiscoveryFailureInfo[];
            installedSignals = buildInstalledSignals(assetSignalCatalog as BackendSignalCatalogResponse, fxSignalCatalog as BackendSignalCatalogResponse);
        } catch (e) {
            console.error('Failed to load system info', e);
        } finally {
            isLoading = false;
        }
    });

    onDestroy(() => {
        if (typeof window !== 'undefined') {
            window.removeEventListener('resize', updateViewport);
        }
    });

    function getDocsUrl(p: ProviderInfo): string | null {
        if (!p.docs_url) return null;
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        if (lang === 'en') return p.docs_url;
        return p.docs_url.replace('/mkdocs/', `/mkdocs/${lang}/`);
    }

    function getProviderUrl(p: ProviderInfo): string | null {
        return p.provider_help_url || p.docs_url || null;
    }

    function mkdocsUrl(path?: string | null): string | null {
        if (!path) return null;
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const cleanPath = path.replace(/^\/?mkdocs\/?/, '').replace(/^\/+/, '');
        const pathWithSlash = cleanPath.endsWith('/') ? cleanPath : `${cleanPath}/`;
        return `/mkdocs/${lang === 'en' ? '' : `${lang}/`}${pathWithSlash}`;
    }

    function buildInstalledSignals(assetCatalog: BackendSignalCatalogResponse, fxCatalog: BackendSignalCatalogResponse): SignalDefinition[] {
        const byType = new Map<string, SignalDefinition>();
        for (const signal of [...(assetCatalog.items ?? []), ...(fxCatalog.items ?? [])].map(mapBackendSignalDefinition)) {
            byType.set(signal.type, signal);
        }
        for (const signal of getRegisteredSignalTypes()) {
            byType.set(signal.type, signal);
        }
        return [...byType.values()].sort((a, b) => {
            const left = a.displayNameKey ?? a.displayName;
            const right = b.displayNameKey ?? b.displayName;
            return left.localeCompare(right);
        });
    }

    function failuresForSystem(system: PluginSystem): PluginDiscoveryFailureInfo[] {
        return pluginDiscoveryFailures.filter((failure) => failure.system === system);
    }

    function openSocialShare(platform: SocialPlatform) {
        sharePlatform = platform;
    }

    function closeSocialShare() {
        sharePlatform = null;
    }

    async function copySystemInfo() {
        if (!systemInfo) return;

        const deploymentModeLabel = systemInfo.deployment_mode === 'docker' ? 'Docker' : 'Local';
        const themeLabel = THEME_LABELS[themePreference].en + (themePreference === 'auto' ? ` (${THEME_LABELS[themeResolved].en})` : '');
        const languageLabel = `${LOCALE_NAMES[currentLocale]} (${currentLocale})`;

        const info = `LibreFolio System Info
========================
App Version: ${systemInfo.app_version}
Python: ${systemInfo.python_version}
OS: ${systemInfo.os_name} ${systemInfo.os_version}
Platform: ${systemInfo.platform}
Deployment Mode: ${deploymentModeLabel}
Browser: ${userAgent}
Viewport: ${viewportWidth}x${viewportHeight}
Device Pixel Ratio: ${devicePixelRatio}x
Theme: ${themeLabel}
Language: ${languageLabel}
========================

Backend Dependencies:
${systemInfo.backend_dependencies.map((d) => `  - ${d.name}: ${d.version}`).join('\n')}

Frontend Dependencies:
${systemInfo.frontend_dependencies.map((d) => `  - ${d.name}: ${d.version}`).join('\n')}

Asset Providers:
${assetProviders.map((p) => `  - ${p.name}`).join('\n')}

FX Providers:
${fxProviders.map((p) => `  - ${p.name}`).join('\n')}

Import Plugins:
${importPlugins.map((p) => `  - ${p.name}`).join('\n')}

Generated: ${new Date().toISOString()}
`;

        try {
            await writeTextToClipboard(info);
        } catch {
            toasts.error($_('support.clipboardUnavailable'));
            return;
        }
        copied = true;
        setTimeout(() => (copied = false), 2000);
    }
</script>

<div class="space-y-8 text-lf-primary" data-testid="about-tab" data-busy={isLoading ? 'true' : 'false'} aria-busy={isLoading}>
    <!-- App Info -->
    <div class="flex items-center space-x-4">
        <div class="w-14 h-14 rounded-xl shadow-sm flex items-center justify-center p-2 bg-lf-logo shadow-lf-shadow-card">
            <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
        </div>
        <div>
            <h3 class="text-xl font-bold text-lf-primary" data-testid="about-app-name">LibreFolio</h3>
            <button type="button" class="text-lf-muted hover:text-lf-secondary transition-colors cursor-pointer text-left" title={$_('changelog.title')} onclick={() => (changelogOpen = true)} data-testid="about-version">{$_('settings.version')} {systemInfo?.app_version ?? '...'}</button>
        </div>
    </div>

    <ChangelogModal open={changelogOpen} onClose={() => (changelogOpen = false)} currentVersion={systemInfo?.app_version ?? ''} />

    <!-- Description -->
    <div class="space-y-2">
        <p class="text-lf-secondary">
            {$_('settings.aboutDescription')}
        </p>
    </div>

    <!-- Links -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Website -->
        <a class="flex items-center space-x-3 p-4 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-all group" href={websiteUrl} rel="noopener noreferrer" target="_blank">
            <Globe class="text-lf-secondary" size={24} />
            <div class="flex-1">
                <p class="font-medium text-lf-secondary flex items-center">
                    {$_('settings.officialWebsite')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14} />
                </p>
                <p class="text-sm text-lf-muted">{$_('settings.visitWebsite')}</p>
            </div>
        </a>

        <!-- GitHub -->
        <a class="flex items-center space-x-3 p-4 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-all group" href={githubUrl} rel="noopener noreferrer" target="_blank">
            <Github class="text-lf-secondary" size={24} />
            <div class="flex-1">
                <p class="font-medium text-lf-secondary flex items-center">
                    {$_('settings.githubRepo')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14} />
                </p>
                <p class="text-sm text-lf-muted">{$_('settings.viewSource')}</p>
            </div>
        </a>

        <!-- License -->
        <a class="flex items-center space-x-3 p-4 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-all group md:col-span-2" href={githubUrl + '/blob/main/LICENSE'} rel="noopener noreferrer" target="_blank">
            <Scale class="text-lf-secondary" size={24} />
            <div class="flex-1">
                <p class="font-medium text-lf-secondary flex items-center">
                    {$_('settings.license')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14} />
                </p>
                <p class="text-sm text-lf-muted">GNU Affero General Public License v3.0 (AGPL-3.0)</p>
            </div>
        </a>
    </div>

    <!-- Support -->
    <div class="rounded-xl border border-lf-subtle bg-lf-panel p-4 shadow-sm shadow-lf-shadow-card" data-testid="about-support-card">
        <div class="mb-4 space-y-1">
            <h4 class="text-md font-semibold text-lf-primary">{$_('support.title')}</h4>
            <p class="text-sm leading-relaxed text-lf-secondary">{$_('support.description')}</p>
        </div>
        <SupportActions onShare={openSocialShare} />
    </div>

    <!-- The legal notice of the instance (F09): not the diagnostics', so it shows when they fail -->
    <div class="rounded-xl border border-lf-subtle bg-lf-panel p-4 shadow-sm shadow-lf-shadow-card" data-testid="about-legal-card">
        <h4 class="mb-2 text-md font-semibold text-lf-primary">{$_('legal.title')}</h4>
        <LegalNotice />
    </div>

    <!-- System Info with Copy Button -->
    <div class="pt-6 border-t border-lf-subtle">
        <div class="flex items-center justify-between mb-4">
            <h4 class="text-md font-medium text-lf-secondary">{$_('settings.systemInfo')}</h4>
            <button class="flex items-center space-x-2 px-3 py-1.5 text-sm bg-lf-panel hover:bg-lf-neutral rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed" data-testid="about-copy-report" disabled={!systemInfo} onclick={copySystemInfo}>
                {#if copied}
                    <Check size={16} class="text-lf-success" />
                    <span class="text-lf-success">{$_('common.copied')}</span>
                {:else}
                    <Copy size={16} />
                    <span>{$_('settings.copyForIssue')}</span>
                {/if}
            </button>
        </div>

        {#if isLoading}
            <LoadingSpinner />
        {:else if systemInfo}
            <div class="grid grid-cols-2 gap-4 text-sm">
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <Tag size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div>
                        <p class="text-lf-muted text-xs">{$_('settings.appVersion')}</p>
                        <p class="font-medium text-lf-secondary">{systemInfo.app_version}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <span class="text-lg mt-0.5 shrink-0">🐍</span>
                    <div>
                        <p class="text-lf-muted text-xs">{$_('settings.pythonVersion')}</p>
                        <p class="font-medium text-lf-secondary">{systemInfo.python_version}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <Monitor size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div>
                        <p class="text-lf-muted text-xs">{$_('settings.operatingSystem')}</p>
                        <p class="font-medium text-lf-secondary">{systemInfo.os_name} {systemInfo.os_version}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <HardDrive size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div class="flex-1 min-w-0">
                        <p class="text-lf-muted text-xs">{$_('settings.platform')}</p>
                        <p use:scrollOnOverflow class="{overflowScrollTextClass} font-medium text-lf-secondary text-xs" title={systemInfo.platform}>{systemInfo.platform}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <Container size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div>
                        <p class="text-lf-muted text-xs">{$_('settings.deploymentMode')}</p>
                        <p class="font-medium text-lf-secondary">
                            {systemInfo.deployment_mode === 'docker' ? $_('settings.deploymentModeDocker') : $_('settings.deploymentModeLocal')}
                        </p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <AppWindow size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div class="flex-1 min-w-0">
                        <p class="text-lf-muted text-xs">{$_('settings.browser')}</p>
                        <p use:scrollOnOverflow class="{overflowScrollTextClass} font-medium text-lf-secondary text-xs" title={userAgent}>{userAgent}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <Maximize2 size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div>
                        <p class="text-lf-muted text-xs">{$_('settings.viewport')}</p>
                        <p class="font-medium text-lf-secondary">{viewportWidth} × {viewportHeight}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <Layers size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div>
                        <p class="text-lf-muted text-xs flex items-center gap-1">
                            {$_('settings.devicePixelRatio')}
                            <Tooltip text={$_('settings.devicePixelRatioHint')} position="top">
                                <Info size={12} class="text-lf-muted hover:text-lf-link cursor-help transition-colors" />
                            </Tooltip>
                        </p>
                        <p class="font-medium text-lf-secondary">{devicePixelRatio}x</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <SunMoon size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div>
                        <p class="text-lf-muted text-xs">{$_('settings.theme')}</p>
                        <p class="font-medium text-lf-secondary">
                            {$_(THEME_LABELS[themePreference].key)}
                            {#if themePreference === 'auto'}
                                <span class="text-lf-muted">({$_(THEME_LABELS[themeResolved].key)})</span>
                            {/if}
                        </p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-lf-panel rounded-lg">
                    <Languages size={18} class="text-lf-link mt-0.5 shrink-0" />
                    <div>
                        <p class="text-lf-muted text-xs">{$_('settings.language')}</p>
                        <p class="font-medium text-lf-secondary">{LOCALE_NAMES[currentLocale]}</p>
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <!-- Installed Plugins -->
    {#if !isLoading}
        <div class="pt-6 border-t border-lf-subtle">
            <h4 class="text-md font-medium text-lf-secondary mb-4">{$_('settings.installedPlugins')}</h4>

            <!-- Asset Providers -->
            {#if assetProviders.length > 0}
                <details class="mb-3 group">
                    <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-colors">
                        <span class="text-sm font-medium text-lf-secondary">{$_('settings.assetProviders')} ({assetProviders.length})</span>
                        <ChevronDown size={16} class="text-lf-muted transition-transform group-open:rotate-180" />
                    </summary>
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3 pl-1">
                        {#each assetProviders as p}
                            <svelte:element
                                this={getProviderUrl(p) ? 'a' : 'div'}
                                href={getProviderUrl(p) || undefined}
                                target={getProviderUrl(p) ? '_blank' : undefined}
                                rel={getProviderUrl(p) ? 'noopener noreferrer' : undefined}
                                class="flex items-center gap-3 p-3 bg-white border border-gray-100 rounded-lg shadow-sm {getProviderUrl(p) ? 'hover:border-libre-green hover:shadow-md cursor-pointer transition-all' : ''}"
                            >
                                {#if p.icon_url && !failedIconUrls.has(p.icon_url)}
                                    <img src={p.icon_url} alt={p.name} class="w-8 h-8 rounded object-contain shrink-0 bg-lf-panel p-0.5" onerror={() => p.icon_url && markIconFailed(p.icon_url)} />
                                {:else}
                                    <div class="w-8 h-8 rounded bg-libre-green/10 text-libre-green flex items-center justify-center text-xs font-bold shrink-0">
                                        {codeInitials(p.code)}
                                    </div>
                                {/if}
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-lf-primary truncate">{p.name}</p>
                                    <p class="text-xs text-lf-muted truncate">{p.code}</p>
                                </div>
                            </svelte:element>
                        {/each}
                    </div>
                </details>
            {/if}

            <!-- FX Providers -->
            {#if fxProviders.length > 0}
                <details class="mb-3 group">
                    <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-colors">
                        <span class="text-sm font-medium text-lf-secondary">{$_('settings.fxProviders')} ({fxProviders.length})</span>
                        <ChevronDown size={16} class="text-lf-muted transition-transform group-open:rotate-180" />
                    </summary>
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3 pl-1">
                        {#each fxProviders as p}
                            <svelte:element
                                this={getProviderUrl(p) ? 'a' : 'div'}
                                href={getProviderUrl(p) || undefined}
                                target={getProviderUrl(p) ? '_blank' : undefined}
                                rel={getProviderUrl(p) ? 'noopener noreferrer' : undefined}
                                class="flex items-center gap-3 p-3 bg-white border border-gray-100 rounded-lg shadow-sm {getProviderUrl(p) ? 'hover:border-blue-400 hover:shadow-md cursor-pointer transition-all' : ''}"
                            >
                                {#if p.icon_url && !failedIconUrls.has(p.icon_url)}
                                    <img src={p.icon_url} alt={p.name} class="w-8 h-8 rounded object-contain shrink-0 bg-lf-panel p-0.5" onerror={() => p.icon_url && markIconFailed(p.icon_url)} />
                                {:else}
                                    <div class="w-8 h-8 rounded bg-blue-500/10 text-blue-600 flex items-center justify-center text-xs font-bold shrink-0">
                                        {p.code.slice(0, 3).toUpperCase()}
                                    </div>
                                {/if}
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-lf-primary truncate">{p.name}</p>
                                    <p class="text-xs text-lf-muted truncate">{p.code}</p>
                                </div>
                            </svelte:element>
                        {/each}
                    </div>
                </details>
            {/if}

            <!-- Import Plugins -->
            {#if importPlugins.length > 0}
                <details class="mb-3 group">
                    <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-colors">
                        <span class="text-sm font-medium text-lf-secondary">{$_('settings.importPlugins')} ({importPlugins.length})</span>
                        <ChevronDown size={16} class="text-lf-muted transition-transform group-open:rotate-180" />
                    </summary>
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3 pl-1">
                        {#each importPlugins as p}
                            <svelte:element
                                this={getDocsUrl(p) ? 'a' : 'div'}
                                href={getDocsUrl(p) || undefined}
                                target={getDocsUrl(p) ? '_blank' : undefined}
                                rel={getDocsUrl(p) ? 'noopener noreferrer' : undefined}
                                class="flex items-center gap-3 p-3 bg-white border border-gray-100 rounded-lg shadow-sm {getDocsUrl(p) ? 'hover:border-amber-400 hover:shadow-md cursor-pointer transition-all' : ''}"
                            >
                                {#if p.icon_url && !failedIconUrls.has(p.icon_url)}
                                    <img src={p.icon_url} alt={brimPluginName(p, $_)} class="w-8 h-8 rounded object-contain shrink-0 bg-lf-panel p-0.5" onerror={() => p.icon_url && markIconFailed(p.icon_url)} />
                                {:else}
                                    <div class="w-8 h-8 rounded bg-amber-500/10 text-amber-600 flex items-center justify-center text-xs font-bold shrink-0">
                                        {codeInitials(p.code)}
                                    </div>
                                {/if}
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-lf-primary truncate">{brimPluginName(p, $_)}</p>
                                    <p class="text-xs text-lf-muted truncate">{p.code}</p>
                                </div>
                            </svelte:element>
                        {/each}
                    </div>
                </details>
            {/if}

            <!-- Installed Signals -->
            <details class="mb-3 group" data-testid="about-installed-signals">
                <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-colors">
                    <span class="text-sm font-medium text-lf-secondary">{$_('settings.installedSignals')} ({installedSignals.length})</span>
                    <ChevronDown size={16} class="text-lf-muted transition-transform group-open:rotate-180" />
                </summary>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3 pl-1">
                    {#each installedSignals as signal}
                        <svelte:element
                            this={mkdocsUrl(signal.docsPath) ? 'a' : 'div'}
                            href={mkdocsUrl(signal.docsPath) || undefined}
                            target={mkdocsUrl(signal.docsPath) ? '_blank' : undefined}
                            rel={mkdocsUrl(signal.docsPath) ? 'noopener noreferrer' : undefined}
                            class="flex items-center gap-3 p-3 bg-white border border-gray-100 rounded-lg shadow-sm {mkdocsUrl(signal.docsPath) ? 'hover:border-purple-400 hover:shadow-md cursor-pointer transition-all' : ''}"
                            data-testid={'about-installed-signal-' + signal.type}
                        >
                            <div class="w-8 h-8 rounded bg-purple-500/10 text-purple-600 flex items-center justify-center text-xs font-bold shrink-0">
                                {signal.icon}
                            </div>
                            <div class="min-w-0">
                                <p class="text-sm font-medium text-lf-primary truncate">{signal.displayNameKey ? $_(signal.displayNameKey) : signal.displayName}</p>
                                <p class="text-xs text-lf-muted truncate">{signal.backendSignalCode ?? signal.type}</p>
                            </div>
                        </svelte:element>
                    {/each}
                </div>
            </details>

            <!-- Plugin Diagnostics -->
            <details bind:open={toolPanelOpen} class="mb-3 group" data-testid="about-plugin-diagnostics">
                <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-colors">
                    <span class="text-sm font-medium text-lf-secondary">{$_('settings.pluginDiagnostics')}</span>
                    <ChevronDown size={16} class="text-lf-muted transition-transform group-open:rotate-180" />
                </summary>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pl-1">
                    {#each PLUGIN_SYSTEMS as definition}
                        <div
                            class="p-3 bg-lf-card border border-lf-subtle rounded-lg shadow-sm shadow-lf-shadow-card"
                            data-testid={'about-plugin-diagnostics-' + definition.system}
                            data-status={failuresForSystem(definition.system).length > 0 ? 'failed' : 'ok'}
                            data-failures={failuresForSystem(definition.system).length}
                        >
                            <p class="text-sm font-medium text-lf-primary mb-2">{$_(definition.labelKey)}</p>
                            {#if failuresForSystem(definition.system).length > 0}
                                <div class="space-y-2">
                                    {#each failuresForSystem(definition.system) as failure}
                                        <div class="rounded-md bg-lf-danger-soft border border-lf-danger-line p-2">
                                            <p class="text-xs font-medium text-lf-danger-on-soft">{failure.filename}</p>
                                            <p use:scrollOnOverflow class="{overflowScrollTextClass} text-xs text-lf-danger" title={failure.error}>{failure.error}</p>
                                        </div>
                                    {/each}
                                </div>
                            {:else}
                                <div class="flex items-center gap-2 text-xs text-lf-success-on-soft bg-lf-success-soft border border-lf-success-line rounded-md p-2">
                                    <Check size={14} class="shrink-0" />
                                    <span>{$_('settings.pluginDiagnosticsAllLoaded')}</span>
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>
                <ToolAboutPanel active={toolPanelOpen} />
            </details>
        </div>
    {/if}

    <SocialShareModal open={sharePlatform !== null} platform={sharePlatform ?? 'x'} onClose={closeSocialShare} />

    <!-- Credits with foldable dependencies -->
    <div class="pt-6 border-t border-lf-subtle">
        <h4 class="text-md font-medium text-lf-secondary mb-4">{$_('settings.credits')}</h4>

        {#if systemInfo}
            <!-- Backend Libraries (foldable) -->
            <details class="mb-3 group">
                <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-colors">
                    <span class="text-sm font-medium text-lf-secondary">{$_('settings.backendLibraries')} ({systemInfo.backend_dependencies.length})</span>
                    <ChevronDown size={16} class="text-lf-muted transition-transform group-open:rotate-180" />
                </summary>
                <div class="flex flex-wrap gap-2 mt-3 pl-1">
                    {#each systemInfo.backend_dependencies as dep}
                        <span class="px-2 py-1 bg-lf-panel text-lf-secondary rounded text-xs">
                            {dep.name} <span class="text-lf-muted">{dep.version}</span>
                        </span>
                    {/each}
                </div>
            </details>

            <!-- Frontend Libraries (foldable) -->
            <details class="mb-3 group">
                <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-lf-panel rounded-lg hover:bg-lf-neutral transition-colors">
                    <span class="text-sm font-medium text-lf-secondary">{$_('settings.frontendLibraries')} ({systemInfo.frontend_dependencies.length})</span>
                    <ChevronDown size={16} class="text-lf-muted transition-transform group-open:rotate-180" />
                </summary>
                <div class="flex flex-wrap gap-2 mt-3 pl-1">
                    {#each systemInfo.frontend_dependencies as dep}
                        <span class="px-2 py-1 bg-lf-panel text-lf-secondary rounded text-xs">
                            {dep.name} <span class="text-lf-muted">{dep.version}</span>
                        </span>
                    {/each}
                </div>
            </details>
        {/if}

        <!-- Made with love -->
        <div class="flex items-center justify-center space-x-2 text-lf-muted pt-4 border-t border-lf-subtle">
            <span>{$_('settings.madeWith')}</span>
            <Heart class="text-red-500" size={16} />
            <span>{$_('settings.inItaly')}</span>
        </div>
    </div>
</div>
