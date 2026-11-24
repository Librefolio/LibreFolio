<!--
  PluginSettingsForm — one plugin's settings, as the caller may see and change them (workstream X, lot CP11b; plan 03
  §4.4, D-X15). Its heading shows the plugin's icon (`icon_url`), or a neutral puzzle piece when it has none or the
  image does not load. A control per declared field, by type. A secret is write-only: «set on …», then «Replace» or
  «Clear»; its text is sent once and dropped. A field an environment variable of the server sets, and an instance field
  for a user who is not an administrator, are read-only with the reason. «Save» writes the plugin's edits all or
  nothing, then the plugin's state is read again and handed to `onsaved`. The rules live in `pluginSettingsForm.ts`;
  colours are roles only (theme-roles skill), every class a whole literal.

  The core's call limits (project 76, U5) are not drawn as generic fields: the «Calls» block (`PluginCallUsage`) draws
  them with the counts, after the plugin's own fields and before Discard / Save; they save with the card. A card whose
  provider a limit variable stops says so at its top (`cardProblem`). A plugin whose calls count on a shared group (the
  group owns the count) says so with «Open», when the page names it in `countGroups`.
-->
<script lang="ts">
    import ProviderAttributionNote from '$lib/features/assets/ProviderAttributionNote.svelte';
    import {Activity, Lock, Puzzle, Share2} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {SimpleSelect} from '$lib/components/ui/select';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import {fetchPluginEntry, savePluginSettings, type PluginSettingsEntry, type SettingField} from './pluginSettingsApi';
    import PluginCallUsage from './PluginCallUsage.svelte';
    import {cardProblem, hasCallBlock, ownFields} from './callUsage';
    import {managedConfirmed} from '$lib/features/instance/profile';
    import {
        chosen,
        cleared,
        displayValue,
        draftOf,
        draftProblems,
        EMPTY_FORM,
        entryTitle,
        fieldDescription,
        fieldLabel,
        INPUT_CLASS,
        LINK_BUTTON_CLASS,
        NOTE_CLASSES,
        optionLabel,
        own,
        PRIMARY_BUTTON_CLASS,
        PROBLEM_KEYS,
        readOnlyReason,
        refusalKey,
        refusalsByField,
        restored,
        SCOPE_KEYS,
        SECONDARY_BUTTON_CLASS,
        secretState,
        shownChoice,
        shownText,
        STATUS_BADGE_CLASSES,
        typed,
        writeItems,
        type FormState,
    } from './pluginSettingsForm';

    interface Props {
        entry: PluginSettingsEntry;
        /** The plugin's state read again after a save (or a conflicting one): show it in place of `entry`. */
        onsaved?: (fresh: PluginSettingsEntry) => void;
        /** The names of the shared groups as their own entries show them, by group code (project 76). */
        groupNames?: Record<string, string>;
        /** Bring a shared group's settings into view: without it, the row names the group and offers no button. */
        onopengroup?: (name: string) => void;
        /** The groups `onopengroup` can bring into view; absent, every group. A group the page does not show gets no button. */
        openableGroups?: readonly string[];
        /** The shared groups that own a call count (a `call_usage` of their own): a plugin that reads one says its calls
         * count there (project 76, U5). Absent, none. */
        countGroups?: readonly string[];
    }

    let {entry, onsaved, groupNames = {}, onopengroup, openableGroups, countGroups = []}: Props = $props();

    const uid = $props.id();
    let form = $state<FormState>(EMPTY_FORM);
    /** The saved secrets whose «Replace» was pressed: their input shows. */
    let replacing = $state<string[]>([]);
    /** The fields the last write refused, with the server's code. */
    let refusals = $state<Record<string, string>>({});
    let saving = $state(false);
    /** The icon address that failed to load: the neutral icon takes its place until the plugin publishes another. */
    let failedIconUrl = $state<string | null>(null);

    const showIcon = $derived(!!entry.icon_url && entry.icon_url !== failedIconUrl);
    const draft = $derived(draftOf(entry, form));
    const problems = $derived(draftProblems(entry, draft));
    const dirty = $derived(Object.keys(draft).length > 0 || replacing.length > 0);
    const savable = $derived(Object.keys(draft).length > 0 && Object.keys(problems).length === 0 && !saving);
    const editable = $derived(entry.fields.some((field) => field.editable));
    /** The plugin's own fields: the call limits are the «Calls» block's. */
    const fields = $derived(ownFields(entry));
    const problemOnTop = $derived(cardProblem(entry, entryTitle(entry, $_), managedConfirmed()));

    function update(key: string, next: FormState): void {
        form = next;
        if (Object.hasOwn(refusals, key)) {
            const rest = {...refusals};
            delete rest[key];
            refusals = rest;
        }
    }

    function startReplace(field: SettingField): void {
        replacing = [...replacing, field.key];
    }

    function stopReplace(field: SettingField): void {
        replacing = replacing.filter((key) => key !== field.key);
        update(field.key, restored(form, field.key));
    }

    function discard(): void {
        form = EMPTY_FORM;
        replacing = [];
        refusals = {};
    }

    async function reload(): Promise<void> {
        try {
            const fresh = await fetchPluginEntry(entry.family, entry.plugin_code);
            if (fresh) onsaved?.(fresh);
        } catch {
            // The write is done either way; the state shown is the one before it until the next read.
        }
    }

    async function save(): Promise<void> {
        if (!savable) return;
        saving = true;
        const items = writeItems(entry, draft);
        // Names only: a value, and above all a secret, never goes into an event or a log.
        const subject = {family: entry.family, plugin_code: entry.plugin_code, fields: items.map((item) => item.field_key)};
        const outcome = await savePluginSettings(items);
        if (outcome.kind === 'saved') {
            discard();
            notify({name: 'pluginSettings.saved', detail: subject});
            await reload();
        } else if (outcome.kind === 'refused') {
            refusals = refusalsByField(outcome.results);
            notify({name: 'pluginSettings.save.refused', detail: {...subject, refused: refusals}, toast: {variant: 'error', message: $_('pluginSettings.form.refused')}});
        } else if (outcome.kind === 'conflict') {
            notify({name: 'pluginSettings.save.failed', detail: {...subject, reason: 'conflict'}, toast: {variant: 'error', message: $_('pluginSettings.form.conflict')}});
            await reload();
        } else {
            const message = outcome.kind === 'keyUnavailable' ? $_('pluginSettings.form.keyUnavailable') : $_('pluginSettings.form.saveFailed');
            notify({name: 'pluginSettings.save.failed', detail: {...subject, reason: outcome.kind}, toast: {variant: 'error', message}});
        }
        saving = false;
    }
</script>

<section
    aria-busy={saving}
    aria-labelledby="{uid}-name"
    class="space-y-4 rounded-lg border border-lf-subtle bg-lf-card p-4 text-lf-primary"
    data-busy={saving ? 'true' : 'false'}
    data-configured={entry.configured ? 'true' : 'false'}
    data-family={entry.family}
    data-testid="plugin-settings-form-{entry.plugin_code}"
>
    <header class="flex flex-wrap items-center justify-between gap-2">
        <!-- tabindex -1: a plugin's «open group» moves the focus here, to the group's heading -->
        <h4 class="flex items-center gap-2 text-base font-semibold focus-visible:outline-2 focus-visible:outline-lf-focus" id="{uid}-name" tabindex="-1">
            {#if showIcon}
                <img alt="" class="h-5 w-5 shrink-0 rounded-sm object-contain" data-testid="plugin-settings-plugin-icon" onerror={() => (failedIconUrl = entry.icon_url)} referrerpolicy="no-referrer" src={entry.icon_url} />
            {:else if entry.family === 'group'}
                <!-- A shared group whose readers have no icon: the icon of its section -->
                <Share2 aria-hidden="true" class="h-5 w-5 shrink-0 text-lf-muted" data-testid="plugin-settings-plugin-icon-fallback" />
            {:else}
                <Puzzle aria-hidden="true" class="h-5 w-5 shrink-0 text-lf-muted" data-testid="plugin-settings-plugin-icon-fallback" />
            {/if}
            {entryTitle(entry, $_)}
        </h4>
        {#if entry.configured}
            <span class={STATUS_BADGE_CLASSES.configured} data-testid="plugin-settings-status" data-configured="true">{$_('pluginSettings.status.configured')}</span>
        {:else}
            <span class={STATUS_BADGE_CLASSES.notConfigured} data-testid="plugin-settings-status" data-configured="false">{$_('pluginSettings.status.notConfigured')}</span>
        {/if}
    </header>

    {#if problemOnTop}
        <!-- The provider is stopped: a real error, red (rule 12); fixed on the server, so no button -->
        <p class="{NOTE_CLASSES.error} [overflow-wrap:anywhere]" data-case={problemOnTop.kind} data-testid="plugin-settings-invalid-env" role="alert">{$_(problemOnTop.key, {values: problemOnTop.values})}</p>
    {/if}
    {#if entry.family === 'asset'}
        <!-- The line a price source's terms ask for (CoinGecko's «Powered by CoinGecko», project 76, P4) -->
        <ProviderAttributionNote providerCodes={[entry.plugin_code]} testId="plugin-settings-attribution" />
    {/if}
    {#if entry.family === 'group' && (entry.used_by ?? []).length > 0}
        <p class="text-sm text-lf-secondary" data-testid="plugin-settings-used-by">
            {$_('pluginSettings.group.usedBy', {values: {plugins: (entry.used_by ?? []).map((user) => user.plugin_name).join(', ')}})}
        </p>
    {/if}
    {#each entry.groups ?? [] as name (name)}
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-lf-secondary" data-group={name} data-testid="plugin-settings-in-group">
            <!-- The icon and its text stay together on a narrow window; the button wraps below them -->
            <span class="flex min-w-0 items-start gap-2">
                <Share2 aria-hidden="true" class="mt-0.5 h-4 w-4 shrink-0 text-lf-muted" />
                <span>{$_('pluginSettings.group.inGroup', {values: {group: groupNames[name] ?? name}})}</span>
            </span>
            {#if onopengroup && (!openableGroups || openableGroups.includes(name))}
                <button class={LINK_BUTTON_CLASS} data-testid="plugin-settings-open-group" onclick={() => onopengroup(name)} type="button">{$_('pluginSettings.group.open')}</button>
            {/if}
        </div>
    {/each}
    {#each (entry.groups ?? []).filter((name) => countGroups.includes(name)) as name (name)}
        <!-- The group owns the count: the counter and the limits are on its card (project 76, U5) -->
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-lf-secondary" data-group={name} data-testid="plugin-settings-calls-on-group">
            <span class="flex min-w-0 items-start gap-2">
                <Activity aria-hidden="true" class="mt-0.5 h-4 w-4 shrink-0 text-lf-muted" />
                <span>{$_('pluginSettings.group.countsOn', {values: {group: groupNames[name] ?? name}})}</span>
            </span>
            {#if onopengroup && (!openableGroups || openableGroups.includes(name))}
                <button class={LINK_BUTTON_CLASS} data-testid="plugin-settings-calls-open-group" onclick={() => onopengroup(name)} type="button">{$_('pluginSettings.group.open')}</button>
            {/if}
        </div>
    {/each}

    {#if fields.length > 0}
        <div class="space-y-4">
            {#each fields as field (field.key)}
                {@const inputId = `${uid}-${field.key}`}
                {@const reason = readOnlyReason(field)}
                {@const edit = own(draft, field.key)}
                {@const problem = own(problems, field.key)}
                {@const refusal = own(refusals, field.key)}
                {@const description = fieldDescription(field, $_)}
                {@const secret = field.secret ? secretState(field) : null}
                {@const replaced = replacing.includes(field.key)}
                <div
                    class="space-y-1"
                    data-edit={edit?.kind ?? ''}
                    data-editable={field.editable ? 'true' : 'false'}
                    data-locked={field.locked ? 'true' : 'false'}
                    data-problem={field.problem ?? ''}
                    data-scope={field.scope}
                    data-source={field.source}
                    data-testid="plugin-setting-{field.key}"
                    data-type={field.type}
                >
                    <div class="flex flex-wrap items-baseline gap-x-2">
                        <label class="text-sm font-medium text-lf-secondary" for={inputId}>
                            {fieldLabel(field, $_)}{#if field.required}<span aria-hidden="true" class="text-lf-danger"> *</span>{/if}
                        </label>
                        <span class="text-xs text-lf-muted">{$_(SCOPE_KEYS[field.scope])}</span>
                    </div>
                    {#if description}
                        <p class="text-xs text-lf-muted">{description}</p>
                    {/if}

                    {#if field.secret}
                        <!-- Write-only: the value never comes back; only whether and since when it is set. -->
                        {#if secret === 'env'}
                            <p class="text-sm text-lf-secondary" data-testid="plugin-setting-secret-state" data-state="env">{$_('pluginSettings.secret.set')}</p>
                        {:else if secret === 'set' && !replaced && edit?.kind !== 'clear'}
                            <p class="text-sm text-lf-secondary" data-testid="plugin-setting-secret-state" data-state="set">
                                {field.updated_at ? $_('pluginSettings.secret.setOn', {values: {date: formatDateTime(field.updated_at)}}) : $_('pluginSettings.secret.set')}
                            </p>
                        {:else if secret === 'unset' && !field.editable}
                            <p class="text-sm text-lf-secondary" data-testid="plugin-setting-secret-state" data-state="unset">{$_('pluginSettings.secret.unset')}</p>
                        {/if}
                        {#if secret === 'unreadable'}
                            <p class={NOTE_CLASSES.warning} data-note="unreadable" data-testid="plugin-setting-note">{$_('pluginSettings.secret.unreadable')}</p>
                        {/if}
                        {#if field.editable}
                            {#if edit?.kind === 'clear'}
                                <div class="flex flex-wrap items-center gap-2">
                                    <p class="text-sm text-lf-secondary" data-testid="plugin-setting-secret-state" data-state="clearing">{$_('pluginSettings.secret.willClear')}</p>
                                    <button class={LINK_BUTTON_CLASS} data-testid="plugin-setting-undo" disabled={saving} onclick={() => update(field.key, restored(form, field.key))} type="button">
                                        {$_('common.undo')}
                                    </button>
                                </div>
                            {:else if secret === 'set' && !replaced}
                                <div class="flex flex-wrap gap-2">
                                    <button class={SECONDARY_BUTTON_CLASS} data-testid="plugin-setting-replace" disabled={saving} onclick={() => startReplace(field)} type="button">
                                        {$_('pluginSettings.secret.replace')}
                                    </button>
                                    <button class={SECONDARY_BUTTON_CLASS} data-testid="plugin-setting-clear" disabled={saving} onclick={() => update(field.key, cleared(form, field.key))} type="button">
                                        {$_('pluginSettings.secret.clear')}
                                    </button>
                                </div>
                            {:else}
                                <div class="flex flex-wrap items-center gap-2">
                                    <div class="min-w-0 flex-1">
                                        <!-- An API key is not an account's password (81 U39): a masked text field, which the browser never offers to save -->
                                        <PasswordInput
                                            neverSaved
                                            bind:value={() => own(form.texts, field.key) ?? '', (text) => update(field.key, typed(form, field.key, text))}
                                            disabled={saving}
                                            hasError={!!problem || !!refusal}
                                            id={inputId}
                                            placeholder={$_('pluginSettings.secret.placeholder')}
                                            testId="plugin-setting-secret-input"
                                        />
                                    </div>
                                    {#if replaced}
                                        <button class={LINK_BUTTON_CLASS} data-testid="plugin-setting-cancel-replace" disabled={saving} onclick={() => stopReplace(field)} type="button">
                                            {$_('common.cancel')}
                                        </button>
                                    {/if}
                                </div>
                                <p class={NOTE_CLASSES.muted}>{$_('pluginSettings.secret.writeOnly')}</p>
                            {/if}
                        {/if}
                    {:else if reason !== null}
                        <!-- Read-only: the value in force, as text (a boolean as a checkbox nobody can tick). -->
                        {#if field.type === 'boolean'}
                            <input checked={field.value === true} class="h-4 w-4 rounded border border-lf-input" data-testid="plugin-setting-toggle" disabled id={inputId} type="checkbox" />
                        {:else}
                            <p class="text-sm text-lf-primary" data-testid="plugin-setting-value" id={inputId}>{displayValue(field, $_)}</p>
                        {/if}
                    {:else if field.type === 'select'}
                        <SimpleSelect
                            ariaLabel={fieldLabel(field, $_)}
                            disabled={saving}
                            dropdownPosition="auto"
                            onchange={(value) => update(field.key, chosen(form, field.key, value))}
                            optionTestId={(option) => `plugin-setting-option-${option.value}`}
                            options={field.options.map((option) => ({value: option.value, label: optionLabel(option, $_)}))}
                            testId="plugin-setting-select"
                            value={String(shownChoice(field, form) ?? '')}
                        />
                    {:else if field.type === 'boolean'}
                        <input
                            checked={shownChoice(field, form) === true}
                            class="h-4 w-4 rounded border border-lf-input"
                            data-testid="plugin-setting-toggle"
                            disabled={saving}
                            id={inputId}
                            onchange={(event) => update(field.key, chosen(form, field.key, event.currentTarget.checked))}
                            type="checkbox"
                        />
                    {:else}
                        <input
                            aria-invalid={problem || refusal ? 'true' : undefined}
                            autocomplete="off"
                            class={INPUT_CLASS}
                            data-testid="plugin-setting-input"
                            disabled={saving}
                            id={inputId}
                            max={field.maximum ?? undefined}
                            maxlength={field.max_length ?? undefined}
                            min={field.minimum ?? undefined}
                            oninput={(event) => update(field.key, typed(form, field.key, event.currentTarget.value))}
                            step={field.type === 'integer' ? 1 : field.type === 'number' ? 'any' : undefined}
                            type={field.type === 'string' ? 'text' : 'number'}
                            value={shownText(field, form)}
                        />
                    {/if}

                    {#if !field.secret && reason === null && field.source === 'db'}
                        {#if edit?.kind === 'clear'}
                            <div class="flex flex-wrap items-center gap-2">
                                <p class={NOTE_CLASSES.muted} data-note="toDefault" data-testid="plugin-setting-note">{$_('pluginSettings.field.willUseDefault')}</p>
                                <button class={LINK_BUTTON_CLASS} data-testid="plugin-setting-undo" disabled={saving} onclick={() => update(field.key, restored(form, field.key))} type="button">
                                    {$_('common.undo')}
                                </button>
                            </div>
                        {:else}
                            <button class={LINK_BUTTON_CLASS} data-testid="plugin-setting-default" disabled={saving} onclick={() => update(field.key, cleared(form, field.key))} type="button">
                                {$_('pluginSettings.field.useDefault')}
                            </button>
                        {/if}
                    {/if}

                    {#if reason === 'locked'}
                        <p class="flex items-center gap-1 text-xs text-lf-muted" data-note="locked" data-testid="plugin-setting-note">
                            <Lock aria-hidden="true" class="h-3 w-3" />
                            <span>{field.env_variable ? $_('pluginSettings.field.lockedBy', {values: {variable: field.env_variable}}) : $_('pluginSettings.field.locked')}</span>
                        </p>
                    {:else if reason === 'adminOnly'}
                        <p class={NOTE_CLASSES.muted} data-note="adminOnly" data-testid="plugin-setting-note">{$_('pluginSettings.field.adminOnly')}</p>
                    {/if}
                    {#if field.problem === 'invalid_env'}
                        <p class={NOTE_CLASSES.error} data-note="invalidEnv" data-testid="plugin-setting-note">
                            {field.env_variable ? $_('pluginSettings.field.invalidEnvBy', {values: {variable: field.env_variable}}) : $_('pluginSettings.field.invalidEnv')}
                        </p>
                    {:else if field.problem === 'invalid_stored'}
                        <p class={NOTE_CLASSES.warning} data-note="invalidStored" data-testid="plugin-setting-note">{$_('pluginSettings.field.invalidStored')}</p>
                    {/if}
                    {#if problem}
                        <p class="text-xs text-lf-danger" data-code={problem.code} data-testid="plugin-setting-problem">{$_(PROBLEM_KEYS[problem.code], {values: {limit: problem.limit ?? ''}})}</p>
                    {/if}
                    {#if refusal}
                        <p class="text-xs text-lf-danger" data-code={refusal} data-testid="plugin-setting-refusal" role="alert">{$_(refusalKey(refusal))}</p>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}

    {#if hasCallBlock(entry)}
        <PluginCallUsage {draft} {entry} {form} ontype={(field, text) => update(field.key, typed(form, field.key, text))} {problems} {refusals} {saving} />
    {/if}

    {#if editable}
        <footer class="flex justify-end gap-2">
            <button class={SECONDARY_BUTTON_CLASS} data-testid="plugin-settings-discard" disabled={!dirty || saving} onclick={discard} type="button">
                {$_('common.discard')}
            </button>
            <button class={PRIMARY_BUTTON_CLASS} data-testid="plugin-settings-save" disabled={!savable} onclick={save} type="button">
                {$_('common.save')}
            </button>
        </footer>
    {/if}
</section>
