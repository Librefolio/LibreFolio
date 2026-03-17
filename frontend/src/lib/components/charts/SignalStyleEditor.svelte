<!--
  SignalStyleEditor — Reusable signal line style editor.

  Features:
  - Color picker
  - SVG line preview button (opens popover)
  - Popover with: marker grids (start/end), line type selector, line width selector
  - Optional `simplified` mode: hides marker grids (for MeasurePanel)

  Used by: ChartSignalsSection, MeasurePanel.
  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {SignalStyle, MarkerType} from '$lib/charts/signals';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        style: SignalStyle;
        onstylechange: (key: keyof SignalStyle, value: any) => void;
        /** Hide marker grids (start/end) — used for measure signals */
        simplified?: boolean;
    }

    let {
        style,
        onstylechange,
        simplified = false,
    }: Props = $props();

    // =========================================================================
    // Constants
    // =========================================================================

    const LINE_TYPES: ('solid' | 'dashed' | 'dotted')[] = ['solid', 'dashed', 'dotted'];
    const MARKER_OPTIONS: (MarkerType | null)[] = [null, 'arrow', 'circle', 'diamond', 'rect', 'pin'];
    const MARKER_SYMBOLS_START: Record<string, string> = {arrow: '◁', circle: '●', diamond: '◆', rect: '■', pin: '📍'};
    const MARKER_SYMBOLS_END: Record<string, string> = {arrow: '▷', circle: '●', diamond: '◆', rect: '■', pin: '📍'};

    // =========================================================================
    // State
    // =========================================================================

    let popoverOpen = $state(false);

    function togglePopover() {
        popoverOpen = !popoverOpen;
    }

    function closePopover() {
        popoverOpen = false;
    }
</script>

<div class="flex items-center gap-1.5 pt-1.5 border-t border-gray-100 dark:border-slate-700">
    <input
        type="color"
        value={style.color}
        class="w-6 h-6 p-0 border border-gray-200 dark:border-slate-600 rounded cursor-pointer shrink-0"
        title={$t('chartSettings.style.color')}
        oninput={(e) => onstylechange('color', e.currentTarget.value)}
    />
    <div class="flex-1 relative">
        <button
            type="button"
            class="w-full h-7 flex items-center cursor-pointer rounded hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors relative"
            title={$t('chartSettings.style.lineType')}
            onclick={togglePopover}
        >
            <svg width="100%" height="24" class="absolute inset-0">
                <line
                    x1="2%" y1="14" x2="98%" y2="14"
                    stroke={style.color}
                    stroke-width={style.lineWidth}
                    stroke-dasharray={style.lineType === 'dashed' ? '8,4' : style.lineType === 'dotted' ? '2,4' : 'none'}
                />
            </svg>
        </button>

        <!-- Style popover -->
        {#if popoverOpen}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div class="fixed inset-0 z-40" onclick={closePopover}></div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-50
                bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600
                rounded-lg shadow-lg p-3 w-max"
                onclick={(e) => e.stopPropagation()}>
                <div class="flex items-center gap-4">
                    {#if !simplified}
                    <!-- Start marker grid -->
                    <div class="flex flex-col items-center">
                        <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">{$t('chartSettings.style.markerStart')}</span>
                        <div class="grid grid-cols-2 gap-1.5">
                            {#each MARKER_OPTIONS as mk}
                                <button type="button" aria-label={mk ?? 'none'}
                                    class="w-8 h-8 flex items-center justify-center rounded border transition-colors
                                        {style.markerStart === mk ? 'border-libre-green bg-libre-green/10' : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500'}"
                                    onclick={() => onstylechange('markerStart', mk)}>
                                    {#if mk === null}<span class="text-[10px] text-gray-400">✕</span>
                                    {:else}<span style="color: {style.color}" class="text-sm leading-none">{MARKER_SYMBOLS_START[mk]}</span>{/if}
                                </button>
                            {/each}
                        </div>
                    </div>
                    {/if}
                    <!-- Line type + Width -->
                    <div class="flex flex-col items-center {simplified ? '' : 'border-x border-gray-200 dark:border-slate-600 px-4'}">
                        <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">{$t('chartSettings.style.lineType')}</span>
                        <div class="flex gap-1.5 mb-3">
                            {#each LINE_TYPES as lt}
                                <button type="button" aria-label={lt}
                                    class="w-10 h-6 flex items-center justify-center rounded border transition-colors
                                        {style.lineType === lt ? 'border-libre-green bg-libre-green/10' : 'border-gray-200 dark:border-slate-600 hover:border-gray-300'}"
                                    onclick={() => onstylechange('lineType', lt)}>
                                    <svg width="32" height="6"><line x1="2" y1="3" x2="30" y2="3" stroke={style.color} stroke-width="2"
                                        stroke-dasharray={lt === 'dashed' ? '5,3' : lt === 'dotted' ? '2,3' : 'none'} /></svg>
                                </button>
                            {/each}
                        </div>
                        <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">{$t('chartSettings.style.width')}</span>
                        <div class="flex gap-1.5">
                            {#each [1, 2, 3, 4] as w}
                                <button type="button" aria-label="width {w}"
                                    class="w-7 h-6 flex items-center justify-center rounded border transition-colors
                                        {style.lineWidth === w ? 'border-libre-green bg-libre-green/10' : 'border-gray-200 dark:border-slate-600 hover:border-gray-300'}"
                                    onclick={() => onstylechange('lineWidth', w)}>
                                    <svg width="20" height="10"><line x1="2" y1="5" x2="18" y2="5" stroke={style.color} stroke-width={w} /></svg>
                                </button>
                            {/each}
                        </div>
                    </div>
                    {#if !simplified}
                    <!-- End marker grid -->
                    <div class="flex flex-col items-center">
                        <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">{$t('chartSettings.style.markerEnd')}</span>
                        <div class="grid grid-cols-2 gap-1.5">
                            {#each MARKER_OPTIONS as mk}
                                <button type="button" aria-label={mk ?? 'none'}
                                    class="w-8 h-8 flex items-center justify-center rounded border transition-colors
                                        {style.markerEnd === mk ? 'border-libre-green bg-libre-green/10' : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500'}"
                                    onclick={() => onstylechange('markerEnd', mk)}>
                                    {#if mk === null}<span class="text-[10px] text-gray-400">✕</span>
                                    {:else}<span style="color: {style.color}" class="text-sm leading-none">{MARKER_SYMBOLS_END[mk]}</span>{/if}
                                </button>
                            {/each}
                        </div>
                    </div>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
</div>

