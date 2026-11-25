<!--
  ProfileEditModal — the «Modifica i dati» window of the asset profile (plan 68, E10c2).

  A table of the «dry» voices (one row each: a number, a percentage, an amount, a date, a choice, a country, a currency,
  a text), a panel for each map (sectors, countries) and one for the coupon schedule. «Chiedi» (a row, a panel) and
  «Chiedi tutto» ask the asset's enrichers without saving: an empty voice is filled «dalla fonte», an equal one shows
  nothing, a different one goes to the comparison window. The decisions are `profileEditState.ts`'s; this component
  keeps the DOM, the requests and the comparison window.

  Two modes:
  - `keep`: «Tieni le modifiche» hands the pending changes back (`onkeep`); the asset window saves them with the asset
    (E8, E9);
  - `save`: «Salva Tutto» sends `PATCH /assets` with the profile alone, marks the rows the backend refuses, and hands the
    changes back once committed (`onsaved`).

  `ask` and `save` default to the API; a caller (a test, the screenshots) may pass its own.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {onMount, untrack} from 'svelte';
    import {Eraser, PenLine, Plus, Search, Sparkles, Trash2} from 'lucide-svelte';
    import {zodiosApi} from '$lib/api';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import DistributionEditor from '$lib/components/ui/input/DistributionEditor.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {CellContent, ColumnDef, RowAction} from '$lib/components/table/types';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {ensureCurrenciesLoaded, getAllCurrencies} from '$lib/stores/reference/currencyStore';
    import {ensureCountriesLoaded, getAllCountries, getCountryInfo} from '$lib/stores/reference/countryStore';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {currentLanguage} from '$lib/stores/app/language';
    import {fractionToPercent} from '$lib/utils/core/exactDecimal';
    import ProviderComparisonModal from '../ProviderComparisonModal.svelte';
    import type {DiffItem} from '../ProviderComparisonModal.svelte';
    import {patchIssueMessage, type AssetPatchAnswer, type AssetPatchIssue} from '../assetPatchResult';
    import type {ProfileVoice} from './profileStore';
    import {formatProfileValue} from './profileTabState';
    import {applyDifferences, compareAsk, newRow, panelWeights, withPanel, pendingFromRow, profilePatch, rowFromPending, rowIssues, voicePlace, type AskAnswer, type CurrentVoice, type EditRow, type PendingChanges, type PendingVoice, type ProfileDifference, type RowIssue} from './profileEditState';

    /** The body of `POST /assets/profile/ask`: an asset by id, or one not created yet by its type and enrichers. */
    export interface ProfileAskRequest {
        asset_id?: number;
        asset_type?: string;
        enrichers?: Record<string, unknown>;
        keys?: string[];
    }

    /** One item of `PATCH /assets` carrying the profile alone. */
    export interface ProfilePatchItem {
        asset_id: number;
        profile: Record<string, unknown>;
    }

    interface Props {
        open?: boolean;
        /** The asset's name, in the title. */
        assetName: string;
        /** `keep`: hand the changes back to the asset window; `save`: save them here. */
        mode: 'keep' | 'save';
        /** The asset; null for one not created yet (then `askTarget`). Required by `save`. */
        assetId?: number | null;
        /** An asset not created yet: its type and the enrichers it will have. */
        askTarget?: {asset_type: string; enrichers: Record<string, unknown>} | null;
        /** The profile's catalogue (`loadProfileCatalogue()`). */
        catalogue: ProfileVoice[];
        /** «Adesso»: the value of each voice now, and who gave it. */
        current?: Record<string, CurrentVoice>;
        /** The pending changes the window opens with (the asset window's, a broker file's). */
        pending?: PendingChanges;
        /** Enricher code → its name, for «dalla fonte» and the comparison window. */
        sourceNames?: Record<string, string>;
        /** The currencies of an amount or a currency voice; the loaded reference list by default. */
        currencies?: Array<{value: string; label: string}>;
        zIndex?: number;
        onkeep?: (pending: PendingChanges) => void;
        onsaved?: (pending: PendingChanges) => void;
        oncancel?: () => void;
        ask?: (request: ProfileAskRequest) => Promise<AskAnswer>;
        save?: (items: ProfilePatchItem[]) => Promise<AssetPatchAnswer>;
        /** The dry run of `save` (`POST /assets/validate`), asked by «Tieni le modifiche» for an asset that exists. */
        validate?: (items: ProfilePatchItem[]) => Promise<AssetPatchAnswer>;
    }

    let {
        open = $bindable(false),
        assetName,
        mode,
        assetId = null,
        askTarget = null,
        catalogue,
        current = {},
        pending: initialPending = {},
        sourceNames = {},
        currencies,
        zIndex = 60,
        onkeep,
        onsaved,
        oncancel,
        ask = (request) => zodiosApi.ask_profile_api_v1_assets_profile_ask_post(request as never) as Promise<AskAnswer>,
        save = (items) => zodiosApi.patch_assets_bulk_api_v1_assets_patch(items as never) as Promise<AssetPatchAnswer>,
        validate = (items) => zodiosApi.validate_assets_patch_api_v1_assets_validate_post(items as never) as Promise<AssetPatchAnswer>,
    }: Props = $props();

    const GROUP_ORDER = ['classification', 'key_figures', 'fund', 'company', 'bond', 'identity', 'other'];

    let voices = $derived(new Map(catalogue.map((voice) => [voice.key, voice])));
    let rowVoices = $derived(catalogue.filter((voice) => voicePlace(voice) === 'row'));
    let mapVoices = $derived(catalogue.filter((voice) => voicePlace(voice) === 'panel'));
    /** Bumped once the reference lists (currencies, countries) are loaded: they live outside the runes. */
    let referencesLoaded = $state(0);
    let currencyOptions = $derived.by(() => {
        if (currencies) return currencies;
        void referencesLoaded;
        return getAllCurrencies().map((currency) => ({value: currency.code, label: `${currency.code} ${currency.symbol}`}));
    });
    let countryOptions = $derived.by(() => {
        void referencesLoaded;
        return getAllCountries().map((country) => ({value: country.iso3, label: `${country.flag_emoji} ${country.name} (${country.iso3})`}));
    });

    onMount(() => {
        const language = $currentLanguage;
        Promise.allSettled([ensureCountriesLoaded(language), currencies ? Promise.resolve() : ensureCurrenciesLoaded(language)]).then(() => (referencesLoaded += 1));
    });
    let canAsk = $derived(assetId !== null || askTarget !== null);

    // =========================================================================
    // State: the rows (dry voices) and the panels' changes (maps, the coupon schedule)
    // =========================================================================

    let rowCounter = 0;
    let rows = $state<EditRow[]>([]);
    let panelChanges = $state<PendingChanges>({});
    /** Pending changes of voices the catalogue does not list: never shown, handed back as they came. */
    let foreign = $state<PendingChanges>({});
    /** Row id → the backend's reason, after a refused save; cleared when the row changes. */
    let refused = $state<Record<string, string>>({});
    let asking = $state<string | null>(null);
    let summary = $state<{filled: number; different: number; equal: number; missing: string[]; unanswered: string[]} | null>(null);
    let askFailed = $state(false);
    let differences = $state<ProfileDifference[]>([]);
    let comparisonOpen = $state(false);
    let saving = $state(false);
    let saveError = $state<string | null>(null);
    let searchValue = $state('');

    function reset(): void {
        const voiceMap = new Map(catalogue.map((voice) => [voice.key, voice]));
        const nextRows: EditRow[] = [];
        const nextPanels: PendingChanges = {};
        const nextForeign: PendingChanges = {};
        for (const change of Object.values(initialPending)) {
            const voice = voiceMap.get(change.key);
            if (!voice) {
                nextForeign[change.key] = change;
                continue;
            }
            if (voicePlace(voice) === 'row') nextRows.push(rowFromPending(change, voice));
            else nextPanels[change.key] = change;
        }
        rows = nextRows;
        panelChanges = nextPanels;
        foreign = nextForeign;
        refused = {};
        summary = null;
        askFailed = false;
        saveError = null;
    }

    untrack(reset);
    let wasOpen = untrack(() => open);
    $effect(() => {
        const isOpen = open;
        untrack(() => {
            if (isOpen && !wasOpen) reset();
            wasOpen = isOpen;
        });
    });

    /** The pending changes the window stands for: the rows without an issue, the panels', the unknown voices'. */
    let pending = $derived.by(() => {
        const out: PendingChanges = {...foreign, ...panelChanges};
        for (const row of rows) {
            const voice = row.key ? voices.get(row.key) : undefined;
            if (!voice || !row.key) continue;
            const change = pendingFromRow(row, voice);
            if (change) out[row.key] = change;
        }
        return out;
    });
    let issues = $derived(rowIssues(rows, voices));
    let problemCount = $derived(new Set([...Object.keys(issues), ...Object.keys(refused)]).size);
    let valid = $derived(problemCount === 0);

    function clearRefused(id: string): void {
        if (!refused[id]) return;
        refused = Object.fromEntries(Object.entries(refused).filter(([rowId]) => rowId !== id));
    }

    function updateRow(id: string, patch: Partial<EditRow>): void {
        rows = rows.map((row) => (row.id === id ? {...row, ...patch} : row));
        clearRefused(id);
    }

    function addRow(key: string | null): void {
        rowCounter += 1;
        rows = [...rows, newRow(`row-${rowCounter}`, key, '')];
    }

    function removeRow(id: string): void {
        rows = rows.filter((row) => row.id !== id);
        clearRefused(id);
    }

    /** A change from a source (a fill, a difference chosen): its row is replaced in place, or added; a panel's is set. */
    function applyChange(change: PendingVoice): void {
        const voice = voices.get(change.key);
        if (!voice) return;
        if (voicePlace(voice) !== 'row') {
            panelChanges = {...panelChanges, [change.key]: change};
            return;
        }
        const index = rows.findIndex((row) => row.key === change.key);
        const next = rowFromPending(change, voice, index >= 0 ? rows[index].id : change.key);
        rows = index >= 0 ? rows.map((row, i) => (i === index ? next : row)) : [...rows, next];
    }

    // =========================================================================
    // Labels
    // =========================================================================

    function voiceLabel(key: string): string {
        return $t(`assets.profile.voices.${key}`);
    }

    function groupOf(voice: ProfileVoice): string {
        return voice.groups?.[0] ?? 'other';
    }

    function sourceName(code: string): string {
        if (code === 'user') return $t('assets.profile.edit.sourceUser');
        if (code === 'legacy') return $t('assets.profile.edit.sourceLegacy');
        return sourceNames[code] ?? code;
    }

    /** A stored value as the window shows it: as the «Profilo» tab writes it (`formatProfileValue`), one way for the app. */
    function display(key: string, value: unknown): string {
        const voice = voices.get(key);
        if (!voice) return '';
        return formatProfileValue(voice, value, {translate: (label) => $t(label), locale: uiLocale(), countryName: (iso3) => getCountryInfo(iso3).name});
    }

    function issueText(issue: RowIssue): string {
        const keys: Record<RowIssue, string> = {
            no_voice: 'assets.profile.edit.issueNoVoice',
            duplicate: 'assets.profile.edit.issueDuplicate',
            empty: 'assets.profile.edit.issueEmpty',
            not_a_number: 'assets.profile.edit.issueNotANumber',
            not_a_date: 'assets.profile.edit.issueNotADate',
        };
        return $t(keys[issue]);
    }

    // =========================================================================
    // The table
    // =========================================================================

    /** The badge's colours, whole literals: a typed value is news (info), a source's is confirmed (success), a file's is neutral, an emptied voice a warning. */
    function badgeClass(badge: string): string {
        if (badge === 'source') return 'bg-lf-success-soft text-lf-success-on-soft';
        if (badge === 'file') return 'bg-lf-neutral text-lf-secondary';
        if (badge === 'emptied') return 'bg-lf-warning-soft text-lf-warning-on-soft';
        return 'bg-lf-info-soft text-lf-info-on-soft';
    }
    const BADGE_LABEL: Record<string, string> = {
        new: 'assets.profile.edit.stateNew',
        source: 'assets.profile.edit.stateSource',
        file: 'assets.profile.edit.stateFile',
        emptied: 'assets.profile.edit.stateEmptied',
    };

    function stateCell(row: EditRow): CellContent {
        const voice = row.key ? voices.get(row.key) : undefined;
        const change = voice ? pendingFromRow(row, voice) : null;
        const origin = change?.origin ?? 'new';
        const badge = row.emptied ? 'emptied' : origin;
        const issue = issues[row.id];
        const backend = refused[row.id];
        const issueAttribute = backend ? ' data-issue="backend"' : issue ? ` data-issue="${issue}"` : '';
        const reason = backend ? $t('assets.profile.edit.issueBackend', {values: {reason: backend}}) : issue ? issueText(issue) : '';
        return {
            type: 'html',
            html:
                `<span data-testid="profile-row-state-${escapeHtml(row.id)}" data-origin="${origin}" data-state="${row.emptied ? 'emptied' : 'value'}"${issueAttribute} class="inline-flex px-1.5 py-0.5 rounded text-[11px] font-medium whitespace-nowrap ${badgeClass(badge)}">${escapeHtml($t(BADGE_LABEL[badge]))}</span>` +
                (reason ? `<span class="block mt-1 text-[11px] text-lf-danger">${escapeHtml(reason)}</span>` : ''),
        };
    }

    let voiceOptions = $derived.by(() => {
        const options: SelectOption[] = [];
        for (const group of GROUP_ORDER) {
            const inGroup = rowVoices.filter((voice) => groupOf(voice) === group);
            if (!inGroup.length) continue;
            options.push({value: `__group:${group}`, label: $t(`assets.profile.groups.${group}`), header: true});
            options.push(...inGroup.map((voice) => ({value: voice.key, label: voiceLabel(voice.key)})));
        }
        return options;
    });

    function voiceCell(row: EditRow): CellContent {
        return {
            type: 'editable-select',
            value: row.key ?? '',
            options: voiceOptions,
            placeholder: $t('assets.profile.edit.chooseVoice'),
            testId: `profile-row-voice-${row.id}`,
            onchange: (key) => updateRow(row.id, {key: key || null, input: '', amount: null, emptied: false, origin: 'new', base: null}),
        };
    }

    function valueCell(row: EditRow): CellContent {
        const voice = row.key ? voices.get(row.key) : undefined;
        if (!voice) return {type: 'html', html: '<span class="text-lf-muted">—</span>'};
        if (row.emptied) return {type: 'html', html: `<span class="text-lf-muted italic">${escapeHtml($t('assets.profile.edit.stateEmptied'))}</span>`};
        const setInput = (input: string) => updateRow(row.id, {input});
        if (voice.shape === 'amount') {
            return {type: 'editable-amount', amount: row.amount?.amount ?? null, currency: row.amount?.currency ?? null, currencies: currencyOptions, ariaLabel: voiceLabel(voice.key), onchange: (amount) => updateRow(row.id, {amount})};
        }
        if (voice.shape === 'date') return {type: 'editable-date', value: row.input || null, onchange: (date) => setInput(date ?? '')};
        if (voice.shape === 'choice') {
            const options = (voice.choices ?? []).map((code) => ({value: code, label: $t(`assets.profile.choices.${voice.key}.${code}`)}));
            return {type: 'editable-select', value: row.input, options, placeholder: $t('common.select'), testId: `profile-row-value-${row.id}`, onchange: setInput};
        }
        if (voice.shape === 'currency') return {type: 'editable-select', value: row.input, options: currencyOptions, placeholder: $t('common.select'), testId: `profile-row-value-${row.id}`, onchange: setInput};
        if (voice.shape === 'country') return {type: 'editable-select', value: row.input, options: countryOptions, placeholder: $t('common.select'), testId: `profile-row-value-${row.id}`, onchange: setInput};
        // The unit beside the field (E10c3): «0.19» alone reads as 19 % on a TER
        const unit = voice.shape === 'percentage' ? '%' : voice.unit ? $t(`assets.profile.units.${voice.unit}`) : undefined;
        return {type: 'editable-text', value: row.input, unit, onchange: setInput};
    }

    function nowCell(row: EditRow): CellContent {
        const now = row.key ? current[row.key] : undefined;
        const text = now ? display(row.key ?? '', now.value) : '';
        if (!now || text === '') return {type: 'html', html: `<span class="text-lf-muted">${escapeHtml($t('assets.profile.edit.nowNone'))}</span>`};
        return {type: 'html', html: `<span class="text-lf-primary">${escapeHtml(text)}</span> <span class="text-lf-muted">· ${escapeHtml(sourceName(now.source))}</span>`};
    }

    function askCell(row: EditRow): CellContent {
        if (!canAsk || !row.key) return '';
        const key = row.key;
        return {type: 'html', html: `<span class="text-xs font-medium text-lf-link">${escapeHtml($t('assets.profile.edit.ask'))}</span>`, testId: `profile-row-ask-${row.id}`, onClick: () => askKeys([key], key)};
    }

    let columns = $derived<ColumnDef<EditRow>[]>([
        {id: 'state', header: $t('assets.profile.edit.columnStatus'), type: 'text', width: 130, minWidth: 130, cell: stateCell},
        {id: 'voice', header: $t('assets.profile.edit.columnVoice'), type: 'text', width: 220, minWidth: 210, cell: voiceCell},
        {id: 'value', header: $t('assets.profile.edit.columnNewValue'), type: 'text', width: 230, minWidth: 230, cell: valueCell},
        {id: 'now', header: $t('assets.profile.edit.columnNow'), type: 'text', width: 220, minWidth: 200, cell: nowCell},
        {id: 'ask', header: '', type: 'text', width: 80, minWidth: 80, cell: askCell},
    ]);

    const rowActions: RowAction<EditRow>[] = [
        {id: 'empty', icon: Eraser, label: () => $t('assets.profile.edit.leaveEmpty'), testid: (row) => `profile-row-empty-${row.id}`, visible: (row) => !!row.key && !row.emptied, onClick: (row) => updateRow(row.id, {emptied: true, input: '', amount: null})},
        {id: 'write', icon: PenLine, label: () => $t('assets.profile.edit.writeValue'), testid: (row) => `profile-row-write-${row.id}`, visible: (row) => row.emptied, onClick: (row) => updateRow(row.id, {emptied: false})},
        {id: 'remove', icon: Trash2, label: () => $t('assets.profile.edit.removeRow'), testid: (row) => `profile-row-remove-${row.id}`, onClick: (row) => removeRow(row.id)},
    ];

    let searchOptions = $derived(voiceOptions.filter((option) => option.header || !rows.some((row) => row.key === option.value)));

    function pickVoice(key: string): void {
        if (!key || key.startsWith('__group:')) return;
        addRow(key);
        searchValue = '';
    }

    // =========================================================================
    // Asking the sources
    // =========================================================================

    async function askKeys(keys: string[] | null, label: string): Promise<void> {
        if (!canAsk || asking) return;
        asking = label;
        askFailed = false;
        try {
            const request: ProfileAskRequest = assetId !== null ? {asset_id: assetId} : {asset_type: askTarget?.asset_type, enrichers: askTarget?.enrichers};
            if (keys) request.keys = keys;
            const answer = await ask(request);
            const known: AskAnswer = {voices: Object.fromEntries(Object.entries(answer.voices).filter(([key]) => voices.has(key))), outcomes: answer.outcomes};
            const result = compareAsk(known, {keys, pending, current});
            for (const fill of result.fills) applyChange(fill);
            summary = {filled: result.fills.length, different: result.differences.length, equal: result.equal.length, missing: result.missing, unanswered: result.unanswered};
            if (result.differences.length) {
                differences = result.differences;
                comparisonOpen = true;
            }
        } catch {
            askFailed = true;
        } finally {
            asking = null;
        }
    }

    let diffItems = $derived<DiffItem[]>(
        differences.map((difference) => {
            const voice = voices.get(difference.key);
            const isMap = voice?.shape === 'map';
            const group = voice ? groupOf(voice) : 'other';
            return {
                field: difference.key,
                label: voiceLabel(difference.key),
                type: isMap ? 'distribution' : 'string',
                currentValue: isMap ? panelWeights(difference.current) : display(difference.key, difference.current),
                providerValue: isMap ? panelWeights(difference.proposed) : display(difference.key, difference.proposed),
                selected: true,
                group: {key: group, title: $t(`assets.profile.groups.${group}`)},
                sourceLabel: sourceName(difference.source),
                currentLabel: pending[difference.key] ? $t('assets.profile.edit.currentPending') : undefined,
            };
        }),
    );

    function applyComparison(chosen: string[]): void {
        const next = applyDifferences({}, differences, chosen);
        for (const change of Object.values(next)) applyChange(change);
        comparisonOpen = false;
        differences = [];
    }

    // =========================================================================
    // Panels
    // =========================================================================

    function panelValue(key: string): Record<string, number> {
        const change = panelChanges[key];
        if (change) return change.kind === 'emptied' ? {} : (panelWeights(change.value) ?? {});
        return panelWeights(current[key]?.value) ?? {};
    }

    function panelCaption(key: string): string {
        const change = panelChanges[key];
        if (change?.kind === 'source') return $t('assets.profile.edit.panelFromSource', {values: {source: sourceName(change.source ?? '')}});
        if (change) return $t('assets.profile.edit.panelWrittenByYou');
        const now = current[key];
        return now ? `${$t('assets.profile.edit.columnNow')} · ${sourceName(now.source)}` : $t('assets.profile.edit.panelEmpty');
    }

    let schedule = $derived.by(() => {
        const change = panelChanges.coupon_schedule;
        const value = change ? (change.kind === 'emptied' ? null : change.value) : current.coupon_schedule?.value;
        return Array.isArray(value) ? (value as Array<{from: string; to: string; rate: string}>) : null;
    });

    // =========================================================================
    // Footer
    // =========================================================================

    function close(): void {
        open = false;
        oncancel?.();
    }

    /** «Tieni le modifiche»: for an asset that exists, the backend checks the values first (signs, choices, sums). */
    async function keep(): Promise<void> {
        if (!valid || saving) return;
        const kept = pending;
        if (assetId !== null && Object.keys(kept).length) {
            saving = true;
            saveError = null;
            try {
                const answer = await validate([{asset_id: assetId, profile: profilePatch(kept)}]);
                if ((answer.issues ?? []).length) {
                    markRefused(answer.issues ?? []);
                    return;
                }
            } catch {
                saveError = $t('assets.profile.edit.validateFailed');
                return;
            } finally {
                saving = false;
            }
        }
        onkeep?.(kept);
        open = false;
    }

    function markRefused(found: AssetPatchIssue[]): void {
        const next: Record<string, string> = {};
        const others: string[] = [];
        for (const issue of found) {
            const voice = issue.code === 'profileValueInvalid' ? String((issue.params as {voice?: unknown} | undefined)?.voice ?? '') : '';
            const row = voice ? rows.find((candidate) => candidate.key === voice) : undefined;
            if (row) next[row.id] = issue.message;
            else others.push(voice ? `${voiceLabel(voice)}: ${issue.message}` : patchIssueMessage(issue, $t));
        }
        refused = next;
        saveError = others.length ? others.join(' · ') : null;
    }

    async function saveAll(): Promise<void> {
        if (!valid || assetId === null || saving) return;
        saving = true;
        saveError = null;
        const sent = pending;
        try {
            const answer = await save([{asset_id: assetId, profile: profilePatch(sent)}]);
            if (!answer.committed) {
                markRefused(answer.issues ?? []);
                if (!(answer.issues ?? []).length) saveError = $t('assets.profile.edit.saveFailed');
                return;
            }
            for (const warning of answer.warnings ?? []) {
                if (warning.code !== 'profileSourceChanged') continue;
                const params = (warning.params ?? {}) as {voice?: string; seen?: unknown; now?: unknown};
                const key = String(params.voice ?? '');
                notify({
                    name: 'asset.profile.source_changed',
                    detail: {asset_id: assetId, voice: key},
                    toast: {variant: 'warning', message: $t('assets.profile.edit.sourceChanged', {values: {voice: voiceLabel(key), now: display(key, params.now), seen: display(key, params.seen)}})},
                });
            }
            notify({name: 'asset.profile.saved', detail: {asset_id: assetId, voices: Object.keys(sent).length}, toast: {variant: 'success', message: $t('assets.profile.edit.saved')}});
            onsaved?.(sent);
            open = false;
        } catch {
            saveError = $t('assets.profile.edit.saveFailed');
        } finally {
            saving = false;
        }
    }
</script>

<ModalBase {open} maxWidth="5xl" allowOverflow={true} onRequestClose={close} {zIndex} testId="profile-edit-modal" labelledBy="profile-edit-title">
    <div class="flex flex-col max-h-[90vh] text-lf-primary" data-testid="profile-edit" data-busy={asking || saving ? 'true' : 'false'} aria-busy={asking || saving ? 'true' : 'false'}>
        <header class="px-4 sm:px-6 py-4 border-b border-lf-subtle">
            <h2 id="profile-edit-title" class="text-lg font-semibold text-lf-primary truncate">📋 {$t('assets.profile.edit.title')} · {assetName}</h2>
        </header>

        <div class="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                <div class="flex-1 min-w-0 flex items-center gap-2">
                    <Search size={16} class="text-lf-muted shrink-0" aria-hidden="true" />
                    <SearchSelect bind:value={searchValue} options={searchOptions} placeholder={$t('assets.profile.edit.searchVoice')} class="flex-1" testId="profile-edit-search" onchange={pickVoice} />
                </div>
                <!-- On the phone the two buttons take their own row, in equal parts (the developer, round 43) -->
                <div class="grid auto-cols-fr grid-flow-col gap-2 sm:flex">
                    {#if canAsk}
                        <button
                            type="button"
                            class="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border border-lf-input bg-lf-card text-lf-link hover:bg-lf-hover disabled:opacity-50"
                            disabled={asking !== null}
                            onclick={() => askKeys(null, 'all')}
                            data-testid="profile-edit-ask-all"
                        >
                            <Sparkles size={15} aria-hidden="true" />
                            {asking ? $t('assets.profile.edit.asking') : $t('assets.profile.edit.askAll')}
                        </button>
                    {/if}
                    <button type="button" class="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border border-lf-input bg-lf-card text-lf-primary hover:bg-lf-hover" onclick={() => addRow(null)} data-testid="profile-edit-add-row">
                        <Plus size={15} aria-hidden="true" />
                        {$t('assets.profile.edit.addRow')}
                    </button>
                </div>
            </div>

            {#if summary}
                <div data-testid="profile-ask-summary" data-filled={summary.filled} data-different={summary.different} data-equal={summary.equal} data-missing={summary.missing.length} data-unanswered={summary.unanswered.length}>
                    <InfoBanner variant={summary.unanswered.length ? 'warning' : 'info'} dismissible ondismiss={() => (summary = null)}>
                        <p>
                            {summary.filled + summary.different > 0 || summary.equal === 0 ? $t('assets.profile.edit.askDone', {values: {filled: summary.filled, different: summary.different, equal: summary.equal}}) : $t('assets.profile.edit.everythingMatches')}
                        </p>
                        {#if summary.missing.length}
                            <p class="mt-1">{$t('assets.profile.edit.noData', {values: {voices: summary.missing.map(voiceLabel).join(', ')}})}</p>
                        {/if}
                        {#if summary.unanswered.length}
                            <p class="mt-1">{$t('assets.profile.edit.noAnswer', {values: {voices: summary.unanswered.map(voiceLabel).join(', ')}})}</p>
                        {/if}
                        {#if summary.filled + summary.different > 0}
                            <p class="mt-1 text-lf-secondary">{$t('assets.profile.edit.sourceRowsNote')}</p>
                        {/if}
                    </InfoBanner>
                </div>
            {/if}
            {#if askFailed}
                <InfoBanner variant="error" message={$t('assets.profile.edit.askFailed')} dismissible ondismiss={() => (askFailed = false)} />
            {/if}

            <div data-testid="profile-edit-rows">
                <DataTable
                    data={rows}
                    {columns}
                    getRowId={(row) => row.id}
                    storageKey="asset-profile-edit"
                    selectionMode="none"
                    enableSorting={false}
                    enableColumnFilters={false}
                    enablePagination={false}
                    enableColumnVisibility={false}
                    enableColumnResize={false}
                    {rowActions}
                    emptyMessage={$t('assets.profile.edit.searchVoice')}
                />
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {#each mapVoices as voice (voice.key)}
                    <section class="rounded-lg border border-lf-subtle bg-lf-card p-3 space-y-2" data-testid="profile-panel-{voice.key}" data-changed={panelChanges[voice.key] ? panelChanges[voice.key].origin : 'none'}>
                        <!-- The editor titles itself; the line says where the values come from. -->
                        <p class="text-[11px] text-lf-muted truncate" data-testid="profile-panel-caption-{voice.key}">{panelCaption(voice.key)}</p>
                        <DistributionEditor
                            kind={voice.map_keys === 'sector' ? 'sector' : 'geographic'}
                            value={panelValue(voice.key)}
                            onchange={(weights) => (panelChanges = withPanel(panelChanges, voice.key, weights, current))}
                            hasProvider={canAsk}
                            askingProvider={asking === voice.key}
                            onAskProvider={() => askKeys([voice.key], voice.key)}
                            askLabel={$t('assets.profile.edit.askSource')}
                            zIndex={zIndex + 5}
                        />
                    </section>
                {/each}
            </div>

            {#if schedule}
                <section class="rounded-lg border border-lf-subtle bg-lf-card p-3" data-testid="profile-panel-coupon_schedule">
                    <div class="flex items-baseline justify-between gap-2 mb-2">
                        <h3 class="text-sm font-semibold text-lf-primary">{voiceLabel('coupon_schedule')}</h3>
                        <span class="text-[11px] text-lf-muted">{panelCaption('coupon_schedule')}</span>
                    </div>
                    <table class="w-full text-xs">
                        <thead class="text-lf-muted">
                            <tr>
                                <th class="text-left font-medium py-1">{$t('assets.profile.edit.scheduleFrom')}</th>
                                <th class="text-left font-medium py-1">{$t('assets.profile.edit.scheduleTo')}</th>
                                <th class="text-right font-medium py-1">{$t('assets.profile.edit.scheduleRate')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each schedule as period, index (index)}
                                <tr class="border-t border-lf-subtle">
                                    <td class="py-1">{period.from}</td>
                                    <td class="py-1">{period.to}</td>
                                    <td class="py-1 text-right">{fractionToPercent(period.rate) ?? period.rate} %</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </section>
            {/if}

            {#if saveError}
                <InfoBanner variant="error" message={saveError} dismissible ondismiss={() => (saveError = null)} />
            {/if}
        </div>

        <footer class="px-4 sm:px-6 py-3 border-t border-lf-subtle bg-lf-panel flex flex-wrap items-center justify-between gap-2" data-testid="profile-edit-footer">
            <span class="text-xs font-medium {valid ? 'text-lf-success' : 'text-lf-danger'}" data-testid="profile-edit-validity" data-valid={valid ? 'true' : 'false'} data-problems={problemCount}>
                {valid ? `✓ ${$t('assets.profile.edit.valid')}` : $t('assets.profile.edit.invalid', {values: {count: problemCount}})}
            </span>
            <div class="flex gap-2 ml-auto">
                <button type="button" class="px-4 py-2 text-sm font-medium rounded-lg border border-lf-subtle bg-lf-card text-lf-secondary hover:bg-lf-hover" onclick={close} data-testid="profile-edit-cancel">
                    {$t('common.cancel')}
                </button>
                {#if mode === 'keep'}
                    <button type="button" class="px-4 py-2 text-sm font-medium rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed" disabled={!valid || saving} onclick={keep} data-testid="profile-edit-keep">
                        {$t('assets.profile.edit.keep')}
                    </button>
                {:else}
                    <button type="button" class="px-4 py-2 text-sm font-medium rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed" disabled={!valid || saving || assetId === null} onclick={saveAll} data-testid="profile-edit-save">
                        {$t('assets.profile.edit.saveAll')}
                    </button>
                {/if}
            </div>
        </footer>
    </div>
</ModalBase>

<ProviderComparisonModal
    bind:open={comparisonOpen}
    differences={diffItems}
    {assetName}
    zIndex={zIndex + 10}
    title={$t('assets.profile.edit.comparisonTitle')}
    description={$t('assets.profile.edit.comparisonDescription')}
    onapply={(fields) => applyComparison(fields)}
    oncancel={() => (differences = [])}
/>
