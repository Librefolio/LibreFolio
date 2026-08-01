<script lang="ts">
    import {Info} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {resolveVisualSignalStyle, type SignalConfig, type SignalDefinition, type SignalStyle, type SignalVisualComponent, type SignalVisualPartition} from '$lib/charts/signals';
    import SignalStyleEditor from './SignalStyleEditor.svelte';

    interface Props {
        definition: SignalDefinition;
        signalName: string;
        config: SignalConfig;
        oncomponentstylechange?: (componentKey: string, style: SignalStyle) => void;
        onpartitionstylechange?: (partitionKey: string, style: SignalStyle) => void;
    }

    let {definition, signalName, config, oncomponentstylechange, onpartitionstylechange}: Props = $props();
    let components = $derived(definition.visualComponents ?? []);
    let partitions = $derived(definition.visualPartitions ?? []);
    let visibleComponents = $derived(components.map((component, index) => ({component, index})).filter(({component}) => !component.fullyPartitioned));
    let partitionGroups = $derived.by(() => {
        const groups = new Map<string, {componentLabel: string; partitions: SignalVisualPartition[]}>();
        for (const partition of partitions) {
            const componentKey = componentKeyForPartition(partition);
            const component = components.find((item) => item.key === componentKey);
            const current = groups.get(componentKey) ?? {
                componentLabel: component ? componentLabel(component) : humanize(componentKey),
                partitions: [],
            };
            current.partitions.push(partition);
            groups.set(componentKey, current);
        }
        return Array.from(groups.entries()).map(([componentKey, group]) => ({
            componentKey,
            ...group,
        }));
    });

    function translated(key: string | undefined, fallback: string): string {
        if (!key) return fallback;
        const value = $t(key);
        return value === key ? fallback : value;
    }

    function humanize(value: string): string {
        return value
            .replaceAll('_', ' ')
            .replaceAll('-', ' ')
            .replace(/\b\w/g, (letter) => letter.toUpperCase());
    }

    function componentLabel(component: SignalVisualComponent): string {
        const fallback = components.length === 1 ? signalName : humanize(component.key);
        return translated(component.labelKey, fallback);
    }

    function componentDescription(component: SignalVisualComponent): string {
        const fallback = translated(definition.descriptionKey, componentLabel(component));
        return translated(component.descriptionKey, fallback);
    }

    function partitionLabel(partition: SignalVisualPartition): string {
        return translated(partition.labelKey, humanize(partition.semantic || partition.key));
    }

    function partitionDescription(partition: SignalVisualPartition): string {
        return translated(partition.descriptionKey, partitionLabel(partition));
    }

    function defaultComponentStyle(component: SignalVisualComponent, index: number): SignalStyle {
        return resolveVisualSignalStyle(config.style, component.style, index === 0 && component.kind === 'line');
    }

    function componentStyle(component: SignalVisualComponent, index: number): SignalStyle {
        return config.componentStyles?.[component.key] ?? defaultComponentStyle(component, index);
    }

    function componentKeyForPartition(partition: SignalVisualPartition): string {
        return partition.key.split(':', 1)[0];
    }

    function defaultPartitionStyle(partition: SignalVisualPartition): SignalStyle {
        const componentKey = componentKeyForPartition(partition);
        const componentIndex = components.findIndex((component) => component.key === componentKey);
        const component = componentIndex >= 0 ? components[componentIndex] : undefined;
        const baseStyle = component ? componentStyle(component, componentIndex) : config.style;
        return resolveVisualSignalStyle(baseStyle, partition.style);
    }

    function partitionStyle(partition: SignalVisualPartition): SignalStyle {
        return config.partitionStyles?.[partition.key] ?? defaultPartitionStyle(partition);
    }

    function updateComponentStyle<K extends keyof SignalStyle>(component: SignalVisualComponent, index: number, key: K, value: SignalStyle[K]) {
        oncomponentstylechange?.(component.key, {
            ...componentStyle(component, index),
            [key]: value,
        });
    }

    function updatePartitionStyle<K extends keyof SignalStyle>(partition: SignalVisualPartition, key: K, value: SignalStyle[K]) {
        onpartitionstylechange?.(partition.key, {
            ...partitionStyle(partition),
            [key]: value,
        });
    }

    function dashArray(lineType: SignalStyle['lineType']): string {
        if (lineType === 'dashed') return '7,4';
        if (lineType === 'dotted') return '2,4';
        return 'none';
    }
</script>

{#snippet linePreview(style: SignalStyle)}
    <svg width="34" height="12" viewBox="0 0 34 12" aria-hidden="true" class="shrink-0">
        <line x1="1" x2="33" y1="6" y2="6" stroke={style.color} stroke-width={style.lineWidth} stroke-dasharray={dashArray(style.lineType)} />
    </svg>
{/snippet}

{#snippet componentPreview(component: SignalVisualComponent, style: SignalStyle, customized: boolean)}
    {#if component.kind === 'bar'}
        <svg width="34" height="14" viewBox="0 0 34 14" aria-hidden="true" class="shrink-0">
            <rect x="3" y="5" width="6" height="7" rx="1" fill={customized ? style.color : '#16a34a'} />
            <rect x="14" y="2" width="6" height="10" rx="1" fill={customized ? style.color : '#16a34a'} />
            <rect x="25" y="7" width="6" height="5" rx="1" fill={customized ? style.color : '#dc2626'} />
        </svg>
    {:else if component.kind === 'band'}
        <svg width="34" height="14" viewBox="0 0 34 14" aria-hidden="true" class="shrink-0">
            <path d="M1 3 C9 1, 24 4, 33 2 L33 11 C24 9, 9 13, 1 10 Z" fill={style.color} opacity="0.16" />
            <path d="M1 6 C9 4, 24 8, 33 6" fill="none" stroke={style.color} stroke-width={style.lineWidth} stroke-dasharray={dashArray(style.lineType)} />
        </svg>
    {:else}
        {@render linePreview(style)}
    {/if}
{/snippet}

{#if visibleComponents.length > 0 || partitions.length > 0}
    <div class="space-y-2 border-t border-gray-100 pt-2 dark:border-slate-700" data-testid="signal-visual-legend">
        {#if visibleComponents.length > 0}
            <div class="space-y-1.5">
                <span class="block text-[9px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                    {$t('signals.visual.components')}
                </span>
                <div class="grid gap-2" style="grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));">
                    {#each visibleComponents as { component, index } (component.key)}
                        {@const effectiveStyle = componentStyle(component, index)}
                        {@const customized = Boolean(config.componentStyles?.[component.key])}
                        <div class="min-w-0 rounded-md bg-gray-50 p-2 dark:bg-slate-700/60" data-testid="signal-component-style-{component.key}">
                            <div class="mb-1.5 flex min-w-0 items-center gap-1.5 text-[10px] text-gray-600 dark:text-gray-300">
                                {@render componentPreview(component, effectiveStyle, customized)}
                                <span class="min-w-0 flex-1 truncate font-medium">{componentLabel(component)}</span>
                                <Tooltip text={componentDescription(component)} position="top">
                                    <Info size={11} class="shrink-0 text-gray-400" />
                                </Tooltip>
                            </div>
                            <SignalStyleEditor style={effectiveStyle} simplified={component.kind !== 'line'} hideLineType={component.kind === 'bar'} hideWidth={component.kind === 'bar'} onstylechange={(key, value) => updateComponentStyle(component, index, key, value)} />
                        </div>
                    {/each}
                </div>
            </div>
        {/if}

        {#if partitionGroups.length > 0}
            {#each partitionGroups as group (group.componentKey)}
                <div class="space-y-1.5">
                    <span class="block text-[9px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                        {$t('signals.visual.zonesFor', {values: {component: group.componentLabel}})}
                    </span>
                    <div class="grid gap-2" style="grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));">
                        {#each group.partitions as partition (partition.key)}
                            {@const effectiveStyle = partitionStyle(partition)}
                            <div class="min-w-0 rounded-md bg-gray-50 p-2 dark:bg-slate-700/60" data-testid="signal-partition-style-{partition.key}">
                                <div class="mb-1.5 flex min-w-0 items-center gap-1.5 text-[10px] text-gray-600 dark:text-gray-300">
                                    {@render linePreview(effectiveStyle)}
                                    <span class="min-w-0 flex-1 truncate font-medium">{partitionLabel(partition)}</span>
                                    <Tooltip text={partitionDescription(partition)} position="top">
                                        <Info size={11} class="shrink-0 text-gray-400" />
                                    </Tooltip>
                                </div>
                                <SignalStyleEditor style={effectiveStyle} simplified onstylechange={(key, value) => updatePartitionStyle(partition, key, value)} />
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        {/if}
    </div>
{/if}
