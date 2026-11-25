<!--
  PluginCallUsage — the «Calls» block of a plugin's card (project 76, lot U5; plan §3.5, mock section 2): the five
  windows of the call counter, each «count / limit» or «count» and «No limit», in a row from 640 px and one under the
  other on a phone. An administrator types each limit (empty: no limit); the limits are fields of the card, so they save
  with it (`PluginSettingsForm` owns the edits and the write). Another user reads them. A limit a server variable sets
  shows its value with a lock; a hidden one (the managed profile) shows the count only, never «No limit».

  Under the grid: a full window's note (amber, rule 12: the calls start again by themselves), a limit of 0's «stopped»,
  the locks, an invalid variable (red, named to administrators only), the group's own note, and the UTC note. The counts
  are read when the page loads and after a save: no polling. The rules live in `callUsage.ts`; colours are roles only.
-->
<script lang="ts">
    import {Activity, Lock} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import type {PluginSettingsEntry, SettingField} from './pluginSettingsApi';
    import {NOTE_CLASSES, own, PROBLEM_KEYS, refusalKey, SCOPE_KEYS, shownText, type FormState, type InputProblem, type PluginDraft} from './pluginSettingsForm';
    import {CALL_BOX_CLASSES, CALL_COUNT_CLASSES, CALL_INPUT_CLASS, CALL_LABEL_CLASSES, CALL_LOCKED_CLASSES, CALL_SMALL_CLASSES, CALL_WINDOW_KEYS, callBoxes, callNote, callTone, formatCount, groupCallNoteKey, invalidNotes, limitsAdminOnly, lockNotes} from './callUsage';

    interface Props {
        entry: PluginSettingsEntry;
        /** The card's unsaved state, its draft, the problems and the refusals of its last write. */
        form: FormState;
        draft: PluginDraft;
        problems: Readonly<Record<string, InputProblem>>;
        refusals: Readonly<Record<string, string>>;
        saving: boolean;
        /** A limit typed: the card records it as any field's edit. */
        ontype: (field: SettingField, text: string) => void;
    }

    let {entry, form, draft, problems, refusals, saving, ontype}: Props = $props();

    const uid = $props.id();
    const boxes = $derived(callBoxes(entry));
    const managed = $derived(boxes.some((box) => box.hidden));
    const locale = $derived(uiLocale());
    const notes = $derived(
        boxes.flatMap((box) => {
            const note = callNote(box, locale);
            return note ? [{box, note}] : [];
        }),
    );
    const locks = $derived(lockNotes(boxes));
    const invalid = $derived(invalidNotes(boxes));
    const adminOnly = $derived(limitsAdminOnly(boxes));
    const groupNoteKey = $derived(groupCallNoteKey(entry));
</script>

<section aria-labelledby="{uid}-title" class="@container space-y-2 text-lf-primary" data-managed={managed ? 'true' : 'false'} data-testid="plugin-settings-calls">
    <div class="flex flex-wrap items-baseline gap-x-2">
        <h5 class="flex items-center gap-1.5 self-center text-sm font-medium text-lf-secondary" id="{uid}-title">
            <Activity aria-hidden="true" class="h-3.5 w-3.5 shrink-0 text-lf-muted" />
            {$_('pluginSettings.calls.title')}
        </h5>
        <span class="text-xs text-lf-muted">{$_(SCOPE_KEYS.system)}</span>
    </div>

    <!-- By the width of this block (S1c): one per line; from 24rem three and two; from 40rem five in a row -->
    <div class="grid grid-cols-1 gap-1.5 @sm:grid-cols-3 @sm:gap-2 @min-[40rem]:grid-cols-5">
        {#each boxes as box (box.window)}
            {@const tone = callTone(box)}
            {@const name = $_(CALL_WINDOW_KEYS[box.window])}
            {@const field = box.field}
            {@const edit = field ? own(draft, field.key) : undefined}
            {@const problem = field ? own(problems, field.key) : undefined}
            {@const refusal = field ? own(refusals, field.key) : undefined}
            <div
                class={CALL_BOX_CLASSES[tone]}
                data-control={box.control}
                data-count={box.count ?? ''}
                data-edit={edit?.kind ?? ''}
                data-full={box.state === 'full' || box.state === 'stopped' ? 'true' : 'false'}
                data-limit={box.limit ?? ''}
                data-state={box.state}
                data-testid="plugin-settings-calls-window"
                data-window={box.window}
            >
                <span class={CALL_LABEL_CLASSES[tone]}>{name}</span>
                <span class={CALL_COUNT_CLASSES[tone]} data-testid="plugin-settings-calls-count">
                    {box.count === null ? '—' : formatCount(box.count, locale)}
                    {#if box.limit !== null}
                        <span class={CALL_SMALL_CLASSES[tone]} data-testid="plugin-settings-calls-limit">/ {formatCount(box.limit, locale)}</span>
                    {:else if box.control === 'text' && box.state === 'invalid'}
                        <span class={CALL_SMALL_CLASSES[tone]} data-testid="plugin-settings-calls-invalid">{$_('pluginSettings.calls.invalid')}</span>
                    {:else if box.control === 'text'}
                        <span class="text-xs font-normal text-lf-muted" data-testid="plugin-settings-calls-no-limit">{$_('pluginSettings.calls.noLimitInline')}</span>
                    {/if}
                </span>
                {#if field && box.control === 'input'}
                    <input
                        aria-invalid={problem || refusal ? 'true' : undefined}
                        aria-label={$_('pluginSettings.calls.limitOf', {values: {window: name}})}
                        autocomplete="off"
                        class={CALL_INPUT_CLASS}
                        data-testid="plugin-settings-calls-input"
                        disabled={saving}
                        inputmode="numeric"
                        min={field.minimum ?? 0}
                        oninput={(event) => ontype(field, event.currentTarget.value)}
                        placeholder={$_('pluginSettings.calls.noLimit')}
                        step="1"
                        type="number"
                        value={shownText(field, form)}
                    />
                    {#if problem}
                        <p class="basis-full text-xs text-lf-danger" data-code={problem.code} data-testid="plugin-setting-problem">{$_(PROBLEM_KEYS[problem.code], {values: {limit: problem.limit ?? ''}})}</p>
                    {/if}
                    {#if refusal}
                        <p class="basis-full text-xs text-lf-danger" data-code={refusal} data-testid="plugin-setting-refusal" role="alert">{$_(refusalKey(refusal))}</p>
                    {/if}
                {:else if box.control === 'locked'}
                    <div class="@sm:min-w-0 @sm:flex-none @sm:basis-full {CALL_LOCKED_CLASSES[tone]}" data-testid="plugin-settings-calls-locked">
                        <Lock aria-hidden="true" class="h-3 w-3 shrink-0" />
                        {#if box.state === 'invalid'}
                            <span data-testid="plugin-settings-calls-invalid">{$_('pluginSettings.calls.invalid')}</span>
                        {:else if box.limit !== null}
                            <span>{formatCount(box.limit, locale)}</span>
                        {:else}
                            <span>{$_('pluginSettings.calls.noLimit')}</span>
                        {/if}
                    </div>
                {/if}
            </div>
        {/each}
    </div>

    {#each notes as { box, note } (box.window)}
        <p class={NOTE_CLASSES.warning} data-kind={box.state === 'stopped' ? 'stopped' : box.limit === null ? 'managed' : 'full'} data-testid="plugin-settings-calls-full" data-window={box.window}>
            {$_(note.key, {values: note.values})}
        </p>
    {/each}
    {#each locks as lock (lock.window)}
        <p class="flex items-center gap-1 text-xs text-lf-muted [overflow-wrap:anywhere]" data-testid="plugin-settings-calls-lock-note" data-window={lock.window}>
            <Lock aria-hidden="true" class="h-3 w-3 shrink-0" />
            <span>{$_(CALL_WINDOW_KEYS[lock.window])} — {lock.variable ? $_('pluginSettings.field.lockedBy', {values: {variable: lock.variable}}) : $_('pluginSettings.field.locked')}</span>
        </p>
    {/each}
    {#each invalid as wrong (wrong.window)}
        <p class="flex items-center gap-1 text-xs text-lf-danger [overflow-wrap:anywhere]" data-testid="plugin-settings-calls-invalid-note" data-window={wrong.window}>
            <Lock aria-hidden="true" class="h-3 w-3 shrink-0" />
            <span>{$_(CALL_WINDOW_KEYS[wrong.window])} — {$_('pluginSettings.calls.invalidBy', {values: {variable: wrong.variable}})}</span>
        </p>
    {/each}
    {#if adminOnly}
        <p class={NOTE_CLASSES.muted} data-testid="plugin-settings-calls-admin-only">{$_('pluginSettings.calls.adminOnly')}</p>
    {/if}
    {#if groupNoteKey}
        <p class={NOTE_CLASSES.muted} data-testid="plugin-settings-calls-group-note">{$_(groupNoteKey)}</p>
    {/if}
    <p class={NOTE_CLASSES.muted} data-testid="plugin-settings-calls-utc">{$_('pluginSettings.calls.utcNote')}</p>
</section>
