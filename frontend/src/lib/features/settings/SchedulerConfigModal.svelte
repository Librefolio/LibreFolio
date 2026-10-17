<!--
  SchedulerConfigModal.svelte — Svelte 5

  Modal for configuring scheduler settings: frequency, time slots, days, horizon.
  Times and days are stored in the configured scheduler timezone. The backend
  converts local slots to UTC only when deciding if a job is due.
  Uses ModalBase + InfoBanner. Saves each key individually via PUT.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {Clock, Calendar, Search, Lightbulb, Plus, X, Globe} from 'lucide-svelte';

    import {numericArrows} from '$lib/actions/numericArrows';
    interface Props {
        open: boolean;
        serverTz: string;
        serverNowUtc?: string;
        schedulerTimezone?: string;
        currentValues: {
            frequency: number;
            times: string;
            days: string;
            horizon: number;
        };
        onsave: () => void;
    }

    let {open = $bindable(false), serverTz, serverNowUtc = '', schedulerTimezone = '', currentValues, onsave}: Props = $props();

    // Local editable state — reset on open
    let frequency = $state(10);
    let timeSlots: string[] = $state([]);
    let selectedDays: Record<string, boolean> = $state({
        mon: false,
        tue: false,
        wed: false,
        thu: false,
        fri: false,
        sat: false,
        sun: false,
    });
    let horizon = $state(14);
    let newTime = $state('');
    let saving = $state(false);
    let error: string | null = $state(null);
    let selectedTz = $state('UTC');
    let initialTz = $state('UTC');
    let tzSearch = $state('');
    let tzDropdownOpen = $state(false);

    const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

    // Common IANA timezone list
    const TIMEZONES: string[] = (() => {
        try {
            return (Intl as any).supportedValuesOf('timeZone') as string[];
        } catch {
            return ['UTC', 'Europe/Rome', 'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'America/New_York', 'America/Chicago', 'America/Los_Angeles', 'Asia/Tokyo', 'Asia/Shanghai'];
        }
    })();

    let filteredTimezones = $derived(tzSearch.length > 0 ? TIMEZONES.filter((tz) => tz.toLowerCase().includes(tzSearch.toLowerCase())).slice(0, 30) : TIMEZONES.slice(0, 30));

    // Reset local state only on open transition (false → true).
    // untrack(currentValues) prevents re-triggering when parent re-renders the inline object.
    let wasOpen = $state(false);
    $effect(() => {
        const isOpen = open;
        if (isOpen && !wasOpen) {
            untrack(() => {
                frequency = currentValues.frequency;
                selectedTz = schedulerTimezone || 'UTC';
                initialTz = selectedTz;
                timeSlots = currentValues.times ? currentValues.times.split(',').filter(Boolean) : [];
                const activeDays = currentValues.days ? currentValues.days.split(',').map((d: string) => d.trim().toLowerCase()) : [];
                selectedDays = Object.fromEntries(DAY_KEYS.map((d) => [d, activeDays.includes(d)]));
                horizon = currentValues.horizon;
                newTime = '';
                error = null;
                tzSearch = '';
            });
        }
        wasOpen = isOpen;
    });

    function addTimeSlot() {
        if (!newTime) return;
        const normalized = newTime.slice(0, 5); // HH:MM
        if (!timeSlots.includes(normalized)) {
            timeSlots = [...timeSlots, normalized].sort();
        }
        newTime = '';
    }

    function removeTimeSlot(t: string) {
        timeSlots = timeSlots.filter((s) => s !== t);
    }

    function changeTimezone(nextTz: string) {
        if (nextTz === selectedTz) return;
        selectedTz = nextTz;
    }

    function toggleDay(day: string) {
        // Don't allow unchecking the last selected day
        const currentSelected = Object.entries(selectedDays).filter(([, v]) => v);
        if (currentSelected.length === 1 && selectedDays[day]) return;
        selectedDays = {...selectedDays, [day]: !selectedDays[day]};
    }

    let hasAtLeastOneDay = $derived(Object.values(selectedDays).some((v) => v));
    let hasAtLeastOneTime = $derived(timeSlots.length > 0);
    let canSave = $derived(frequency >= 1 && frequency <= 1440 && hasAtLeastOneTime && hasAtLeastOneDay && horizon >= 1 && horizon <= 365);
    let timezoneChanged = $derived(selectedTz !== initialTz);

    async function handleSave() {
        if (!canSave) return;
        saving = true;
        error = null;

        const keysToSave: [string, string][] = [
            ['scheduler_current_price_frequency_minutes', String(frequency)],
            ['scheduler_history_sync_times', timeSlots.join(',')],
            [
                'scheduler_history_sync_days',
                Object.entries(selectedDays)
                    .filter(([, v]) => v)
                    .map(([k]) => k)
                    .join(','),
            ],
            ['scheduler_history_sync_horizon_days', String(horizon)],
            ['scheduler_timezone', selectedTz],
        ];

        try {
            await zodiosApi.axios.patch('/api/v1/settings/global/bulk', {
                items: keysToSave.map(([key, value]) => ({key, value})),
            });
            onsave();
            open = false;
            // The modal closes on success and the schedule it wrote is not shown anywhere
            // else, so without this the user cannot tell a save from a dismiss.
            notify({
                name: 'settings.scheduler.saved',
                detail: {frequencyMinutes: frequency, horizonDays: horizon, timezone: selectedTz, times: timeSlots.length},
                toast: {variant: 'success', message: $_('settings.savedSuccessfully')},
            });
        } catch (e: any) {
            const msg = e?.response?.data?.detail || e?.message || 'Save failed';
            error = msg;
            notify({name: 'settings.scheduler.save.failed', detail: {reason: msg}, toast: {variant: 'error', message: msg}});
        } finally {
            saving = false;
        }
    }

    function getDayLabel(day: string): string {
        const key = `settings.global.scheduler.historyDays${day.charAt(0).toUpperCase() + day.slice(1)}`;
        return $_(key);
    }
</script>

<ModalBase {open} maxWidth="lg" testId="scheduler-config-modal" onRequestClose={() => (open = false)}>
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-lf-subtle">
        <div class="flex items-center gap-2.5">
            <div class="flex items-center justify-center w-9 h-9 rounded-lg bg-lf-success-soft">
                <Clock class="text-lf-success" size={18} />
            </div>
            <h2 class="text-lg font-semibold text-lf-primary">
                {$_('settings.global.scheduler.configTitle')}
            </h2>
        </div>
        <button class="p-1.5 rounded-lg hover:bg-lf-hover text-lf-muted hover:text-lf-secondary transition-colors" onclick={() => (open = false)}>
            <X size={18} />
        </button>
    </div>

    <!-- Body -->
    <div class="px-6 py-4 space-y-5">
        <!-- Server UTC time + Timezone selector -->
        <div class="flex items-center gap-3 text-xs text-lf-muted">
            <span>🕐 Server UTC: <strong>{serverNowUtc || '—'}</strong></span>
        </div>

        <!-- Timezone selector -->
        <section data-testid="scheduler-config-timezone">
            <h3 class="text-sm font-medium text-lf-secondary flex items-center gap-1.5 mb-2">
                <Globe size={14} />
                {$_('settings.global.scheduler.timezone') || 'Timezone'}
            </h3>
            <div class="relative">
                <input
                    type="text"
                    bind:value={tzSearch}
                    placeholder={selectedTz}
                    class="w-full px-3 py-1.5 rounded-lg border border-lf-input bg-lf-field text-sm text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:ring-2 focus:ring-lf-focus/40 focus:border-lf-focus"
                    onfocus={() => {
                        tzDropdownOpen = true;
                    }}
                    onblur={() => {
                        setTimeout(() => {
                            tzDropdownOpen = false;
                        }, 150);
                    }}
                />
                {#if tzDropdownOpen}
                    <div class="absolute z-10 mt-1 w-full max-h-40 overflow-y-auto bg-lf-card border border-lf-raised rounded-lg shadow-lg shadow-lf-shadow">
                        {#each filteredTimezones as tz}
                            <button
                                type="button"
                                class="w-full text-left px-3 py-1.5 text-sm hover:bg-lf-hover {tz === selectedTz ? 'text-lf-link font-medium' : 'text-lf-secondary'}"
                                onmousedown={(e) => e.preventDefault()}
                                onclick={() => {
                                    changeTimezone(tz);
                                    tzSearch = '';
                                    tzDropdownOpen = false;
                                }}>{tz}</button
                            >
                        {/each}
                    </div>
                {/if}
            </div>
            <p class="text-xs text-lf-muted mt-1">{$_('settings.global.scheduler.timezoneHintLocal')}</p>
            {#if timezoneChanged}
                <div data-testid="scheduler-timezone-change-warning" class="mt-2">
                    <InfoBanner variant="warning" message={$_('settings.global.scheduler.timezoneChangeWarning')} />
                </div>
            {/if}
        </section>

        <!-- Error -->
        {#if error}
            <InfoBanner variant="error" message={error} dismissible ondismiss={() => (error = null)} />
        {/if}

        <!-- Current Price Refresh -->
        <section data-testid="scheduler-config-frequency">
            <h3 class="text-sm font-medium text-lf-secondary flex items-center gap-1.5 mb-2">
                💰 {$_('settings.global.scheduler.currentPriceSection')}
            </h3>
            <div class="flex items-center gap-2">
                <label for="scheduler-freq" class="text-sm text-lf-secondary">{$_('settings.global.scheduler.currentPriceFreqLabel')}</label>
                <input id="scheduler-freq" type="number" use:numericArrows bind:value={frequency} min={1} max={1440} class="w-20 px-2 py-1.5 rounded-lg border border-lf-input bg-lf-field text-sm text-lf-primary hover:border-lf-input-hover focus:ring-2 focus:ring-lf-focus/40 focus:border-lf-focus" />
                <span class="text-sm text-lf-muted">{$_('settings.global.scheduler.currentPriceFreqSuffix')}</span>
            </div>
            <p class="text-xs text-lf-muted mt-1">{$_('settings.global.scheduler.currentPriceFreqHint')}</p>
        </section>

        <!-- History Sync Times -->
        <section data-testid="scheduler-config-times">
            <h3 class="text-sm font-medium text-lf-secondary flex items-center gap-1.5 mb-2">
                📊 {$_('settings.global.scheduler.historyTimesLabel')}
            </h3>
            <div class="flex flex-wrap items-center gap-2">
                {#each timeSlots as slot}
                    <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-sm font-mono bg-lf-success-soft text-lf-success-on-soft">
                        {slot}
                        <button type="button" class="ml-0.5 hover:text-lf-danger transition-colors" onclick={() => removeTimeSlot(slot)} aria-label="Remove {slot}">
                            <X size={14} />
                        </button>
                    </span>
                {/each}
                <div class="flex items-center gap-1">
                    <input
                        type="time"
                        bind:value={newTime}
                        class="px-2 py-1 rounded-lg border border-lf-input bg-lf-field text-sm text-lf-primary hover:border-lf-input-hover focus:ring-2 focus:ring-lf-focus/40"
                        data-testid="scheduler-config-time-input"
                        onkeydown={(e) => {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                addTimeSlot();
                            }
                        }}
                    />
                    <button type="button" data-testid="scheduler-config-time-add" class="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-sm text-lf-link hover:bg-lf-selected transition-colors disabled:opacity-40" disabled={!newTime} onclick={addTimeSlot}>
                        <Plus size={14} />
                        {$_('settings.global.scheduler.historyTimesAdd')}
                    </button>
                </div>
            </div>
            <p class="text-xs text-lf-muted mt-1">{$_('settings.global.scheduler.historyTimesHint')}</p>
        </section>

        <!-- History Sync Days -->
        <section data-testid="scheduler-config-days">
            <h3 class="text-sm font-medium text-lf-secondary flex items-center gap-1.5 mb-2">
                <Calendar size={16} />
                {$_('settings.global.scheduler.historyDaysLabel')}
            </h3>
            <div class="flex flex-wrap gap-2">
                {#each DAY_KEYS as day}
                    <button
                        type="button"
                        aria-pressed={selectedDays[day]}
                        data-testid="scheduler-day-{day}"
                        class="px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors {selectedDays[day] ? 'bg-lf-checked text-lf-on-checked border-lf-checked' : 'bg-lf-card text-lf-secondary border-lf-input hover:border-lf-focus'}"
                        onclick={() => toggleDay(day)}
                    >
                        {getDayLabel(day)}
                    </button>
                {/each}
            </div>
            <p class="text-xs text-lf-muted mt-1">{$_('settings.global.scheduler.historyDaysHint')}</p>
        </section>

        <!-- Lookback Horizon -->
        <section data-testid="scheduler-config-horizon">
            <h3 class="text-sm font-medium text-lf-secondary flex items-center gap-1.5 mb-2">
                <Search size={16} />
                {$_('settings.global.scheduler.horizonLabel')}
            </h3>
            <div class="flex items-center gap-2">
                <input type="number" use:numericArrows bind:value={horizon} min={1} max={365} class="w-20 px-2 py-1.5 rounded-lg border border-lf-input bg-lf-field text-sm text-lf-primary hover:border-lf-input-hover focus:ring-2 focus:ring-lf-focus/40 focus:border-lf-focus" />
                <span class="text-sm text-lf-muted">{$_('settings.global.scheduler.horizonSuffix')}</span>
            </div>
            <p class="text-xs text-lf-muted mt-1">{$_('settings.global.scheduler.horizonHint')}</p>
        </section>

        <!-- Tip -->
        <InfoBanner variant="info">
            <span class="font-medium">{$_('settings.global.scheduler.tipTitle')}:</span>
            {$_('settings.global.scheduler.tipBody')}
        </InfoBanner>
    </div>

    <!-- Footer -->
    <div class="flex justify-end gap-2 px-6 py-4 border-t border-lf-subtle">
        <button type="button" data-testid="scheduler-config-cancel" class="px-4 py-2 text-sm font-medium bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors" onclick={() => (open = false)}>
            {$_('common.cancel')}
        </button>
        <button type="button" data-testid="scheduler-config-save" class="px-4 py-2 text-sm font-medium text-lf-on-action bg-lf-action hover:bg-lf-action-hover rounded-lg transition-colors disabled:opacity-50" disabled={!canSave || saving} onclick={handleSave}>
            {#if saving}
                <span class="inline-flex items-center gap-1">
                    <span class="w-3.5 h-3.5 border-2 border-lf-on-action/30 border-t-lf-on-action rounded-full animate-spin"></span>
                    {$_('common.save')}
                </span>
            {:else}
                {$_('common.save')}
            {/if}
        </button>
    </div>
</ModalBase>
