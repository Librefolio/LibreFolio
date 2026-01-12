<script lang="ts">
    import {_} from '$lib/i18n';
    import {api, ApiError} from '$lib/api';
    import {onMount} from 'svelte';
    import {AlertCircle, Lock, Save, ShieldOff, Unlock} from 'lucide-svelte';

    // Props
    export let canEdit: boolean = false;

    interface GlobalSetting {
        key: string;
        value: string;
        value_type: 'str' | 'int' | 'bool' | 'float';
        description: string;
        updated_at: string | null;
        updated_by: number | null;
    }

    let settings: GlobalSetting[] = [];
    let editedValues: Record<string, string> = {};
    let isLocked = true;
    let isLoading = true;
    let isSaving = false;
    let error: string | null = null;
    let success: string | null = null;

    onMount(async () => {
        await loadSettings();
    });

    async function loadSettings() {
        isLoading = true;
        error = null;
        try {
            const response = await api.get<{ settings: GlobalSetting[] }>('/settings/global');
            settings = response.settings;
            // Initialize edited values
            editedValues = {};
            for (const setting of settings) {
                editedValues[setting.key] = setting.value;
            }
        } catch (e) {
            if (e instanceof ApiError) {
                error = e.message;
            } else {
                error = 'Failed to load settings';
            }
        } finally {
            isLoading = false;
        }
    }

    function toggleLock() {
        isLocked = !isLocked;
        if (isLocked) {
            // Reset edited values when locking
            for (const setting of settings) {
                editedValues[setting.key] = setting.value;
            }
        }
    }

    async function saveSetting(key: string) {
        isSaving = true;
        error = null;
        success = null;
        try {
            await api.put(`/settings/global/${key}`, {value: editedValues[key]});
            // Update local state
            const setting = settings.find(s => s.key === key);
            if (setting) {
                setting.value = editedValues[key];
            }
            success = `Setting "${key}" saved successfully`;
            setTimeout(() => success = null, 3000);
        } catch (e) {
            if (e instanceof ApiError) {
                if (e.status === 403) {
                    error = 'Admin access required to modify global settings';
                } else {
                    error = e.message;
                }
            } else {
                error = 'Failed to save setting';
            }
        } finally {
            isSaving = false;
        }
    }

    function getSettingLabel(key: string): string {
        const labels: Record<string, string> = {
            'session_ttl_hours': 'Session TTL (hours)',
            'max_failed_logins': 'Max Failed Login Attempts',
            'allow_registration': 'Allow Registration'
        };
        return labels[key] || key;
    }

    function hasChanges(key: string): boolean {
        const setting = settings.find(s => s.key === key);
        return setting ? setting.value !== editedValues[key] : false;
    }
</script>

<div class="space-y-6">
    <div class="flex items-center justify-between">
        <div>
            <h3 class="text-lg font-semibold text-gray-900">{$_('settings.globalSettings')}</h3>
            <p class="text-sm text-gray-500">{$_('settings.globalSettingsDescription')}</p>
        </div>
        {#if canEdit}
            <button
                    on:click={toggleLock}
                    class="flex items-center space-x-2 px-4 py-2 rounded-lg transition-all
					{isLocked
						? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
						: 'bg-amber-100 text-amber-700 hover:bg-amber-200'}"
                    title={isLocked ? 'Unlock to edit' : 'Lock settings'}
            >
                {#if isLocked}
                    <Lock size={18}/>
                    <span class="text-sm font-medium">{$_('settings.locked')}</span>
                {:else}
                    <Unlock size={18}/>
                    <span class="text-sm font-medium">{$_('settings.unlocked')}</span>
                {/if}
            </button>
        {:else}
            <div class="flex items-center space-x-2 px-4 py-2 bg-gray-50 text-gray-500 rounded-lg">
                <ShieldOff size={18}/>
                <span class="text-sm">{$_('settings.readOnlyMode')}</span>
            </div>
        {/if}
    </div>

    {#if error}
        <div class="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <AlertCircle size={18}/>
            <span>{error}</span>
        </div>
    {/if}

    {#if success}
        <div class="p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
            {success}
        </div>
    {/if}

    {#if isLoading}
        <div class="text-center py-8 text-gray-500">
            {$_('common.loading')}
        </div>
    {:else if settings.length === 0}
        <div class="text-center py-8 text-gray-500">
            {$_('settings.noGlobalSettings')}
        </div>
    {:else}
        <div class="space-y-4">
            {#each settings as setting (setting.key)}
                <div class="bg-gray-50 rounded-lg p-4">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <label for={setting.key} class="block text-sm font-medium text-gray-700">
                                {getSettingLabel(setting.key)}
                            </label>
                            <p class="text-xs text-gray-500 mt-1">{setting.description}</p>
                        </div>
                        <div class="flex items-center space-x-3">
                            {#if setting.value_type === 'bool'}
                                <!-- Toggle Switch for boolean -->
                                <button
                                        type="button"
                                        disabled={isLocked}
                                        aria-label="Toggle {setting.key}"
                                        on:click={() => {
										if (!isLocked) {
											editedValues[setting.key] = editedValues[setting.key] === 'true' ? 'false' : 'true';
										}
									}}
                                        class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors
										{editedValues[setting.key] === 'true' ? 'bg-libre-green' : 'bg-gray-300'}
										{isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}"
                                >
								<span
                                        class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform
										{editedValues[setting.key] === 'true' ? 'translate-x-6' : 'translate-x-1'}"
                                ></span>
                                </button>
                                <span class="text-sm text-gray-600 w-10">
									{editedValues[setting.key] === 'true' ? 'ON' : 'OFF'}
								</span>
                            {:else if setting.value_type === 'int' || setting.value_type === 'float'}
                                <!-- Number input for int/float -->
                                <input
                                        id={setting.key}
                                        type="number"
                                        step={setting.value_type === 'float' ? '0.01' : '1'}
                                        min="0"
                                        bind:value={editedValues[setting.key]}
                                        disabled={isLocked}
                                        class="w-24 px-3 py-2 border rounded-lg text-sm text-right
										{isLocked
											? 'bg-gray-100 text-gray-500 cursor-not-allowed'
											: 'bg-white text-gray-900 border-gray-300 focus:ring-2 focus:ring-libre-green focus:border-libre-green'}"
                                />
                            {:else}
                                <!-- Text input for string -->
                                <input
                                        id={setting.key}
                                        type="text"
                                        bind:value={editedValues[setting.key]}
                                        disabled={isLocked}
                                        class="w-32 px-3 py-2 border rounded-lg text-sm
										{isLocked
											? 'bg-gray-100 text-gray-500 cursor-not-allowed'
											: 'bg-white text-gray-900 border-gray-300 focus:ring-2 focus:ring-libre-green focus:border-libre-green'}"
                                />
                            {/if}
                            {#if !isLocked && hasChanges(setting.key)}
                                <button
                                        on:click={() => saveSetting(setting.key)}
                                        disabled={isSaving}
                                        class="p-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                                        title="Save"
                                >
                                    <Save size={16}/>
                                </button>
                            {/if}
                        </div>
                    </div>
                    {#if setting.updated_at}
                        <p class="text-xs text-gray-400 mt-2">
                            Last updated: {new Date(setting.updated_at).toLocaleString()}
                        </p>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}

    {#if !isLocked}
        <div class="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p class="text-sm text-amber-700">
                <strong>⚠️ {$_('settings.warning')}:</strong> {$_('settings.globalSettingsWarning')}
            </p>
        </div>
    {/if}
</div>

