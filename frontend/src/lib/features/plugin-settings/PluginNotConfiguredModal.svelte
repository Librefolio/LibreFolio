<!--
  PluginNotConfiguredModal — the common window of a provider that is not configured (project 76, D7, lot N3; mock
  section 1.4). Opened by touching a switched-off search chip, provider option or FX route: it says why the provider
  cannot be used, and what the viewer can do about it.

  The case comes from the provider list's own fields (`notConfigured.ts`): a value to set (A for an administrator, with
  «Configure»; B for another user, with a link to the read-only Settings › Plugins in a new tab, so the open form
  underneath is kept), an invalid server variable (named to an administrator, «stopped» for another user), or the
  managed profile (D, no button). A and B name the missing fields, read once from the catalogue: by the phrase each field
  declares («la chiave API», N3a2), joined as a list of the language, when every one declares it; by their labels
  otherwise; a field that cannot be read leaves its key.

  «Configure» swaps this notice for the plugin's settings (`PluginSettingsModal`, which brings a missing group's form into
  view); a save there reaches `onSaved`, so the caller reads its provider list again. Colours are roles only.
-->
<script lang="ts">
    import {_, locale} from '$lib/i18n';
    import {translateOr} from '$lib/utils/core/translateOr';
    import {SETTINGS_TAB_PATHS} from '$lib/features/settings/settingsPaths';
    import {auth} from '$lib/stores/app/auth';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import PluginSettingsModal from './PluginSettingsModal.svelte';
    import {fetchPluginEntry, type PluginSettingsEntry, type SettingField, type SettingsFamily} from './pluginSettingsApi';
    import {fieldLabel, LINK_BUTTON_CLASS, PRIMARY_BUTTON_CLASS, SECONDARY_BUTTON_CLASS} from './pluginSettingsForm';
    import {notConfiguredCase, type NotConfiguredCase, type ProviderReadiness} from './notConfigured';

    interface Props {
        open: boolean;
        family: SettingsFamily;
        pluginCode: string;
        /** The provider's name, as its list gives it. */
        pluginName?: string;
        /** The provider list's readiness fields for this provider. */
        readiness: ProviderReadiness;
        zIndex?: number;
        onClose: () => void;
        /** After a save in «Configure», with the plugin's state read again. */
        onSaved?: (fresh: PluginSettingsEntry) => void;
    }

    let {open, family, pluginCode, pluginName = '', readiness, zIndex = 80, onClose, onSaved}: Props = $props();

    const uid = $props.id();
    const provider = $derived(pluginName || pluginCode);
    const kase: NotConfiguredCase = $derived(notConfiguredCase(readiness, $auth.user?.is_superuser === true));
    const missing = $derived(readiness.missing_settings ?? []);
    /** The missing fields' labels, by key, once read; a key with no label read stays a key. */
    let labels = $state<Record<string, string>>({});
    /** The missing fields' own phrases, by key, for the fields that declare one (N3a2). */
    let phrases = $state<Record<string, string>>({});
    /** «Configure» opened: the settings replace this notice. */
    let configuring = $state(false);

    let loadGeneration = 0;

    /** The labels of the missing fields: the plugin's own, and those of the groups a `<group>.<field>` key names. */
    async function loadLabels(target: {family: SettingsFamily; pluginCode: string; keys: string[]}): Promise<void> {
        const generation = ++loadGeneration;
        labels = {};
        phrases = {};
        const groups = [...new Set(target.keys.filter((key) => key.includes('.')).map((key) => key.split('.')[0]))];
        try {
            const [plugin, ...groupEntries] = await Promise.all([fetchPluginEntry(target.family, target.pluginCode), ...groups.map((name) => fetchPluginEntry('group', name))]);
            if (generation !== loadGeneration) return;
            const found: Record<string, string> = {};
            const phrased: Record<string, string> = {};
            const take = (key: string, field: SettingField) => {
                found[key] = fieldLabel(field, $_);
                if (field.missing_key) phrased[key] = translateOr($_, field.missing_key, found[key]);
            };
            for (const field of plugin?.fields ?? []) take(field.key, field);
            groupEntries.forEach((group, index) => {
                for (const field of group?.fields ?? []) take(`${groups[index]}.${field.key}`, field);
            });
            labels = found;
            phrases = phrased;
        } catch {
            // The keys say what is missing: the window never waits on the catalogue to say why.
        }
    }

    $effect(() => {
        const keys = missing;
        if (open && (kase === 'missing_admin' || kase === 'missing_member') && keys.length > 0) void loadLabels({family, pluginCode, keys});
        return () => {
            loadGeneration++;
        };
    });

    $effect(() => {
        if (!open) configuring = false;
    });

    /** Every missing field says itself in a sentence (N3a2): the phrases, as a list of the language; else the labels. */
    const phrasedAll = $derived(missing.length > 0 && missing.every((key) => key in phrases));
    const fields = $derived(phrasedAll ? new Intl.ListFormat($locale ?? 'en', {type: 'conjunction'}).format(missing.map((key) => phrases[key])) : missing.map((key) => labels[key] ?? key).join(', '));
    const tone = $derived(kase === 'missing_admin' || kase === 'missing_member' ? 'warning' : 'error');
    const variable = $derived((readiness.invalid_variables ?? []).join(', '));

    const text = $derived.by(() => {
        switch (kase) {
            case 'missing_admin':
                if (missing.length === 0) return $_('pluginSettings.notConfigured.missingAdminGeneric', {values: {provider}});
                return phrasedAll ? $_('pluginSettings.notConfigured.missingAdminPhrase', {values: {provider, count: missing.length, fields}}) : $_('pluginSettings.notConfigured.missingAdmin', {values: {provider, count: missing.length, fields}});
            case 'missing_member':
                if (missing.length === 0) return $_('pluginSettings.notConfigured.missingMemberGeneric', {values: {provider}});
                return phrasedAll ? $_('pluginSettings.notConfigured.missingMemberPhrase', {values: {provider, count: missing.length, fields}}) : $_('pluginSettings.notConfigured.missingMember', {values: {provider, count: missing.length, fields}});
            case 'invalid_admin':
                return $_('pluginSettings.notConfigured.invalidAdmin', {values: {variable}});
            case 'invalid_limit_admin':
                return $_('pluginSettings.notConfigured.invalidLimitAdmin', {values: {provider, variable}});
            case 'invalid_member':
                return $_('pluginSettings.notConfigured.invalidMember', {values: {provider}});
            default:
                return $_('pluginSettings.notConfigured.managed', {values: {provider}});
        }
    });

    function saved(fresh: PluginSettingsEntry): void {
        onSaved?.(fresh);
    }
</script>

{#if configuring}
    <PluginSettingsModal {family} {onClose} onSaved={saved} {open} {pluginCode} {pluginName} {zIndex} />
{:else}
    <ModalBase labelledBy="{uid}-title" maxWidth="md" onRequestClose={onClose} {open} testId="plugin-not-configured-dialog" trapFocus {zIndex}>
        <div class="flex flex-col gap-4 p-5 text-lf-primary" data-case={kase} data-plugin={pluginCode} data-testid="plugin-not-configured-modal">
            <h2 class="text-lg font-semibold" id="{uid}-title">{provider}</h2>
            <div data-testid="plugin-not-configured-message" data-variant={tone}>
                <InfoBanner message={text} variant={tone} />
            </div>
            {#if kase === 'missing_member'}
                <p class="text-xs text-lf-secondary">
                    {$_('pluginSettings.notConfigured.readOnlyIntro')}
                    <a class={LINK_BUTTON_CLASS} data-testid="plugin-not-configured-settings-link" href={SETTINGS_TAB_PATHS.plugins} rel="noopener" target="_blank">{$_('pluginSettings.notConfigured.readOnlyLink')}</a>
                </p>
            {/if}
            {#if kase !== 'managed'}
                <div class="flex justify-end gap-2">
                    <button class={SECONDARY_BUTTON_CLASS} data-testid="plugin-not-configured-close" onclick={onClose} type="button">{$_('common.close')}</button>
                    {#if kase === 'missing_admin'}
                        <button class={PRIMARY_BUTTON_CLASS} data-testid="plugin-not-configured-configure" onclick={() => (configuring = true)} type="button">{$_('pluginSettings.configure')}</button>
                    {/if}
                </div>
            {/if}
        </div>
    </ModalBase>
{/if}
