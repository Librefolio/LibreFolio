<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {onMount} from 'svelte';
    import {Check, ChevronDown, Copy, ExternalLink, Github, Globe, HardDrive, Heart, Monitor, Scale, Tag} from 'lucide-svelte';
    import LoadingSpinner from '$lib/components/ui/LoadingSpinner.svelte';

    const githubUrl = 'https://github.com/Alfystar/LibreFolio';
    const websiteUrl = 'https://librefolio.io'; // Placeholder for now

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
        backend_dependencies: DependencyInfo[];
        frontend_dependencies: DependencyInfo[];
    }

    interface ProviderInfo {
        code: string;
        name: string;
        description?: string;
        icon_url?: string | null;
        provider_help_url?: string | null; // asset providers
        docs_url?: string | null; // fx providers
    }

    let systemInfo: SystemInfo | null = null;
    let isLoading = true;
    let copied = false;

    let assetProviders: ProviderInfo[] = [];
    let fxProviders: ProviderInfo[] = [];
    let importPlugins: ProviderInfo[] = [];

    onMount(async () => {
        try {
            const [sysInfo, assetProv, fxProv, brimPlugins] = await Promise.all([
                zodiosApi.get_system_info_api_v1_system_info_get(),
                zodiosApi.list_providers_api_v1_assets_provider_get().catch(() => []),
                zodiosApi.list_providers_api_v1_fx_providers_get().catch(() => []),
                zodiosApi.list_plugins_api_v1_brokers_import_plugins_get().catch(() => []),
            ]);
            systemInfo = sysInfo as SystemInfo;
            assetProviders = assetProv as ProviderInfo[];
            fxProviders = fxProv as ProviderInfo[];
            importPlugins = brimPlugins as ProviderInfo[];
        } catch (e) {
            console.error('Failed to load system info', e);
        } finally {
            isLoading = false;
        }
    });

    function getDocsUrl(p: ProviderInfo): string | null {
        if (!p.code) return null;
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const prefix = lang !== 'en' ? `${lang}/` : '';
        return `/mkdocs/${prefix}user-guide/import/${p.code}/`;
    }

    function getProviderUrl(p: ProviderInfo): string | null {
        return p.provider_help_url || p.docs_url || null;
    }

    async function copySystemInfo() {
        if (!systemInfo) return;

        const info = `LibreFolio System Info
========================
App Version: ${systemInfo.app_version}
Python: ${systemInfo.python_version}
OS: ${systemInfo.os_name} ${systemInfo.os_version}
Platform: ${systemInfo.platform}
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

        await navigator.clipboard.writeText(info);
        copied = true;
        setTimeout(() => (copied = false), 2000);
    }
</script>

<div class="space-y-8" data-testid="about-tab">
    <!-- App Info -->
    <div class="flex items-center space-x-4">
        <div class="w-14 h-14 rounded-xl shadow-sm flex items-center justify-center p-2" style="background:#fff">
            <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
        </div>
        <div>
            <h3 class="text-xl font-bold text-gray-800" data-testid="about-app-name">LibreFolio</h3>
            <p class="text-gray-500" data-testid="about-version">{$_('settings.version')} {systemInfo?.app_version ?? '...'}</p>
        </div>
    </div>

    <!-- Description -->
    <div class="space-y-2">
        <p class="text-gray-600">
            {$_('settings.aboutDescription')}
        </p>
    </div>

    <!-- Links -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Website -->
        <a class="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all group" href={websiteUrl} rel="noopener noreferrer" target="_blank">
            <Globe class="text-gray-700" size={24} />
            <div class="flex-1">
                <p class="font-medium text-gray-700 flex items-center">
                    {$_('settings.officialWebsite')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14} />
                </p>
                <p class="text-sm text-gray-500">{$_('settings.visitWebsite')}</p>
            </div>
        </a>

        <!-- GitHub -->
        <a class="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all group" href={githubUrl} rel="noopener noreferrer" target="_blank">
            <Github class="text-gray-700" size={24} />
            <div class="flex-1">
                <p class="font-medium text-gray-700 flex items-center">
                    {$_('settings.githubRepo')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14} />
                </p>
                <p class="text-sm text-gray-500">{$_('settings.viewSource')}</p>
            </div>
        </a>

        <!-- License -->
        <a class="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all group md:col-span-2" href={githubUrl + '/blob/main/LICENSE'} rel="noopener noreferrer" target="_blank">
            <Scale class="text-gray-700" size={24} />
            <div class="flex-1">
                <p class="font-medium text-gray-700 flex items-center">
                    {$_('settings.license')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14} />
                </p>
                <p class="text-sm text-gray-500">GNU Affero General Public License v3.0 (AGPL-3.0)</p>
            </div>
        </a>
    </div>

    <!-- System Info with Copy Button -->
    <div class="pt-6 border-t border-gray-200">
        <div class="flex items-center justify-between mb-4">
            <h4 class="text-md font-medium text-gray-700">{$_('settings.systemInfo')}</h4>
            <button class="flex items-center space-x-2 px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed" disabled={!systemInfo} on:click={copySystemInfo}>
                {#if copied}
                    <Check size={16} class="text-green-600" />
                    <span class="text-green-600">{$_('common.copied')}</span>
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
                <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <Tag size={18} class="text-libre-green mt-0.5 shrink-0" />
                    <div>
                        <p class="text-gray-500 text-xs">{$_('settings.appVersion')}</p>
                        <p class="font-medium text-gray-700">{systemInfo.app_version}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <span class="text-lg mt-0.5 shrink-0">🐍</span>
                    <div>
                        <p class="text-gray-500 text-xs">{$_('settings.pythonVersion')}</p>
                        <p class="font-medium text-gray-700">{systemInfo.python_version}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <Monitor size={18} class="text-purple-500 mt-0.5 shrink-0" />
                    <div>
                        <p class="text-gray-500 text-xs">{$_('settings.operatingSystem')}</p>
                        <p class="font-medium text-gray-700">{systemInfo.os_name} {systemInfo.os_version}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <HardDrive size={18} class="text-orange-500 mt-0.5 shrink-0" />
                    <div>
                        <p class="text-gray-500 text-xs">{$_('settings.platform')}</p>
                        <p class="font-medium text-gray-700 text-xs truncate" title={systemInfo.platform}>{systemInfo.platform}</p>
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <!-- Installed Plugins -->
    {#if !isLoading}
        <div class="pt-6 border-t border-gray-200">
            <h4 class="text-md font-medium text-gray-700 mb-4">{$_('settings.installedPlugins')}</h4>

            <!-- Asset Providers -->
            {#if assetProviders.length > 0}
                <details class="mb-3 group">
                    <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                        <span class="text-sm font-medium text-gray-700">{$_('settings.assetProviders')} ({assetProviders.length})</span>
                        <ChevronDown size={16} class="text-gray-400 transition-transform group-open:rotate-180" />
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
                                {#if p.icon_url}
                                    <img src={p.icon_url} alt={p.name} class="w-8 h-8 rounded object-contain shrink-0 bg-gray-50 p-0.5" />
                                {:else}
                                    <div class="w-8 h-8 rounded bg-libre-green/10 text-libre-green flex items-center justify-center text-xs font-bold shrink-0">
                                        {p.code.slice(0, 2).toUpperCase()}
                                    </div>
                                {/if}
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-gray-800 truncate">{p.name}</p>
                                    <p class="text-xs text-gray-400 truncate">{p.code}</p>
                                </div>
                            </svelte:element>
                        {/each}
                    </div>
                </details>
            {/if}

            <!-- FX Providers -->
            {#if fxProviders.length > 0}
                <details class="mb-3 group">
                    <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                        <span class="text-sm font-medium text-gray-700">{$_('settings.fxProviders')} ({fxProviders.length})</span>
                        <ChevronDown size={16} class="text-gray-400 transition-transform group-open:rotate-180" />
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
                                {#if p.icon_url}
                                    <img src={p.icon_url} alt={p.name} class="w-8 h-8 rounded object-contain shrink-0 bg-gray-50 p-0.5" />
                                {:else}
                                    <div class="w-8 h-8 rounded bg-blue-500/10 text-blue-600 flex items-center justify-center text-xs font-bold shrink-0">
                                        {p.code.slice(0, 3).toUpperCase()}
                                    </div>
                                {/if}
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-gray-800 truncate">{p.name}</p>
                                    <p class="text-xs text-gray-400 truncate">{p.code}</p>
                                </div>
                            </svelte:element>
                        {/each}
                    </div>
                </details>
            {/if}

            <!-- Import Plugins -->
            {#if importPlugins.length > 0}
                <details class="mb-3 group">
                    <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                        <span class="text-sm font-medium text-gray-700">{$_('settings.importPlugins')} ({importPlugins.length})</span>
                        <ChevronDown size={16} class="text-gray-400 transition-transform group-open:rotate-180" />
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
                                {#if p.icon_url}
                                    <img src={p.icon_url} alt={p.name} class="w-8 h-8 rounded object-contain shrink-0 bg-gray-50 p-0.5" />
                                {:else}
                                    <div class="w-8 h-8 rounded bg-amber-500/10 text-amber-600 flex items-center justify-center text-xs font-bold shrink-0">
                                        {p.code.slice(0, 2).toUpperCase()}
                                    </div>
                                {/if}
                                <div class="min-w-0">
                                    <p class="text-sm font-medium text-gray-800 truncate">{p.name}</p>
                                    <p class="text-xs text-gray-400 truncate">{p.code}</p>
                                </div>
                            </svelte:element>
                        {/each}
                    </div>
                </details>
            {/if}
        </div>
    {/if}

    <!-- Credits with foldable dependencies -->
    <div class="pt-6 border-t border-gray-200">
        <h4 class="text-md font-medium text-gray-700 mb-4">{$_('settings.credits')}</h4>

        {#if systemInfo}
            <!-- Backend Libraries (foldable) -->
            <details class="mb-3 group">
                <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                    <span class="text-sm font-medium text-gray-700">{$_('settings.backendLibraries')} ({systemInfo.backend_dependencies.length})</span>
                    <ChevronDown size={16} class="text-gray-400 transition-transform group-open:rotate-180" />
                </summary>
                <div class="flex flex-wrap gap-2 mt-3 pl-1">
                    {#each systemInfo.backend_dependencies as dep}
                        <span class="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                            {dep.name} <span class="text-gray-400">{dep.version}</span>
                        </span>
                    {/each}
                </div>
            </details>

            <!-- Frontend Libraries (foldable) -->
            <details class="mb-3 group">
                <summary class="flex items-center justify-between cursor-pointer select-none p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                    <span class="text-sm font-medium text-gray-700">{$_('settings.frontendLibraries')} ({systemInfo.frontend_dependencies.length})</span>
                    <ChevronDown size={16} class="text-gray-400 transition-transform group-open:rotate-180" />
                </summary>
                <div class="flex flex-wrap gap-2 mt-3 pl-1">
                    {#each systemInfo.frontend_dependencies as dep}
                        <span class="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                            {dep.name} <span class="text-gray-400">{dep.version}</span>
                        </span>
                    {/each}
                </div>
            </details>
        {/if}

        <!-- Made with love -->
        <div class="flex items-center justify-center space-x-2 text-gray-500 pt-4 border-t border-gray-100">
            <span>{$_('settings.madeWith')}</span>
            <Heart class="text-red-500" size={16} />
            <span>{$_('settings.inItaly')}</span>
        </div>
    </div>
</div>
