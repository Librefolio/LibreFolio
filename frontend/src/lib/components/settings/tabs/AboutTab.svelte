<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {onMount} from 'svelte';
    import {Check, Copy, ExternalLink, Github, Globe, HardDrive, Heart, Monitor, Scale, Tag} from 'lucide-svelte';
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

    let systemInfo: SystemInfo | null = null;
    let isLoading = true;
    let copied = false;

    onMount(async () => {
        try {
            systemInfo = await zodiosApi.get_system_info_api_v1_system_info_get() as SystemInfo;
        } catch (e) {
            console.error('Failed to load system info', e);
        } finally {
            isLoading = false;
        }
    });

    async function copySystemInfo() {
        if (!systemInfo) return;

        const info = `LibreFolio System Info
========================
App Version: ${systemInfo.app_version}
Python: ${systemInfo.python_version}
OS: ${systemInfo.os_name} ${systemInfo.os_version}
Platform: ${systemInfo.platform}

Backend Dependencies:
${systemInfo.backend_dependencies.map(d => `  - ${d.name}: ${d.version}`).join('\n')}

Frontend Dependencies:
${systemInfo.frontend_dependencies.map(d => `  - ${d.name}: ${d.version}`).join('\n')}

Generated: ${new Date().toISOString()}
`;

        await navigator.clipboard.writeText(info);
        copied = true;
        setTimeout(() => copied = false, 2000);
    }
</script>

<div class="space-y-8" data-testid="about-tab">
    <!-- App Info -->
    <div class="flex items-center space-x-4">
        <div class="p-4 bg-libre-green rounded-xl">
            <img alt="LibreFolio" class="w-10 h-10" src="/logo.png"/>
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
        <a
                class="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all group"
                href={websiteUrl}
                rel="noopener noreferrer"
                target="_blank"
        >
            <Globe class="text-gray-700" size={24}/>
            <div class="flex-1">
                <p class="font-medium text-gray-700 flex items-center">
                    {$_('settings.officialWebsite')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14}/>
                </p>
                <p class="text-sm text-gray-500">{$_('settings.visitWebsite')}</p>
            </div>
        </a>

        <!-- GitHub -->
        <a
                class="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all group"
                href={githubUrl}
                rel="noopener noreferrer"
                target="_blank"
        >
            <Github class="text-gray-700" size={24}/>
            <div class="flex-1">
                <p class="font-medium text-gray-700 flex items-center">
                    {$_('settings.githubRepo')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14}/>
                </p>
                <p class="text-sm text-gray-500">{$_('settings.viewSource')}</p>
            </div>
        </a>

        <!-- License -->
        <a
                class="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all group md:col-span-2"
                href={githubUrl + '/blob/main/LICENSE'}
                rel="noopener noreferrer"
                target="_blank"
        >
            <Scale class="text-gray-700" size={24}/>
            <div class="flex-1">
                <p class="font-medium text-gray-700 flex items-center">
                    {$_('settings.license')}
                    <ExternalLink class="ml-1 opacity-0 group-hover:opacity-100 transition-opacity" size={14}/>
                </p>
                <p class="text-sm text-gray-500">GNU Affero General Public License v3.0 (AGPL-3.0)</p>
            </div>
        </a>
    </div>

    <!-- System Info with Copy Button -->
    <div class="pt-6 border-t border-gray-200">
        <div class="flex items-center justify-between mb-4">
            <h4 class="text-md font-medium text-gray-700">{$_('settings.systemInfo')}</h4>
            <button
                    class="flex items-center space-x-2 px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={!systemInfo}
                    on:click={copySystemInfo}
            >
                {#if copied}
                    <Check size={16} class="text-green-600"/>
                    <span class="text-green-600">{$_('common.copied')}</span>
                {:else}
                    <Copy size={16}/>
                    <span>{$_('settings.copyForIssue')}</span>
                {/if}
            </button>
        </div>

        {#if isLoading}
            <LoadingSpinner />
        {:else if systemInfo}
            <div class="grid grid-cols-2 gap-4 text-sm">
                <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <Tag size={18} class="text-libre-green mt-0.5 shrink-0"/>
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
                    <Monitor size={18} class="text-purple-500 mt-0.5 shrink-0"/>
                    <div>
                        <p class="text-gray-500 text-xs">{$_('settings.operatingSystem')}</p>
                        <p class="font-medium text-gray-700">{systemInfo.os_name} {systemInfo.os_version}</p>
                    </div>
                </div>
                <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <HardDrive size={18} class="text-orange-500 mt-0.5 shrink-0"/>
                    <div>
                        <p class="text-gray-500 text-xs">{$_('settings.platform')}</p>
                        <p class="font-medium text-gray-700 text-xs truncate" title={systemInfo.platform}>{systemInfo.platform}</p>
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <!-- Credits with detailed dependencies -->
    <div class="pt-6 border-t border-gray-200">
        <h4 class="text-md font-medium text-gray-700 mb-4">{$_('settings.credits')}</h4>

        <!-- Backend Libraries -->
        {#if systemInfo}
            <div class="mb-4">
                <p class="text-sm text-gray-500 mb-2">{$_('settings.backendLibraries')}</p>
                <div class="flex flex-wrap gap-2">
                    {#each systemInfo.backend_dependencies as dep}
                        <span class="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                            {dep.name} <span class="text-gray-400">{dep.version}</span>
                        </span>
                    {/each}
                </div>
            </div>

            <!-- Frontend Libraries -->
            <div class="mb-6">
                <p class="text-sm text-gray-500 mb-2">{$_('settings.frontendLibraries')}</p>
                <div class="flex flex-wrap gap-2">
                    {#each systemInfo.frontend_dependencies as dep}
                        <span class="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                            {dep.name} <span class="text-gray-400">{dep.version}</span>
                        </span>
                    {/each}
                </div>
            </div>
        {/if}

        <!-- Made with love - at the bottom -->
        <div class="flex items-center justify-center space-x-2 text-gray-500 pt-4 border-t border-gray-100">
            <span>{$_('settings.madeWith')}</span>
            <Heart class="text-red-500" size={16}/>
            <span>{$_('settings.inItaly')}</span>
        </div>
    </div>
</div>
