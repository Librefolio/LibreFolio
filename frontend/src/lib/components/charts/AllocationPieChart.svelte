<!--
  AllocationPieChart — Pie chart for allocation distribution (sector or asset type).

  Supports two modes:
  - 'sector' (default): uses emoji from backend AllocationItem; shows emoji inside each slice
  - 'type': translates asset-type keys via assets.types.*; shows the PNG icon
    inside each slice (ECharts rich text), icon + label in legend and tooltip.

  Props:
  - data: AllocationEntry[] — name, value (0-100%), amount (abs), optional emoji
  - height: CSS height (default "280px")
  - mode: 'sector' | 'type' (default 'sector')
  - currency: currency code for absolute value formatting (default 'EUR')

  Used by:
  - Dashboard page (allocation panel, both type and sector tabs)
  - Asset Detail Page (metadata section, sector distribution)
-->
<script lang="ts">
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {CHART_ANIMATION_CONFIG} from '$lib/components/charts/echartsAnimationConfig';
    import {scheduleFirstRenderStabilityFix, tooltipPositionAboveFinger} from '$lib/components/charts/echartsTooltipHelpers';
    import {_ as t} from '$lib/i18n';
    import {assetTypeFamily, sectorI18nKey, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {buildAllocationHierarchy} from '$lib/components/charts/allocationHierarchy';
    import {buildAllocationRingData, buildAllocationRings, type AllocationRingDatum} from '$lib/components/charts/allocationRings';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    // =========================================================================
    // Types & Props
    // =========================================================================

    export interface AllocationEntry {
        name: string;
        /** Percentage share 0-100 */
        value: number;
        /** Absolute amount in base currency */
        amount: number;
        /** Emoji from backend (sectors) */
        emoji?: string | null;
    }

    interface Props {
        /** Allocation data array from backend AllocationItem[] */
        data: AllocationEntry[];
        /** CSS height of the chart container */
        height?: string;
        /** Display mode: 'sector' uses backend emoji + i18n labels; 'type' uses asset type PNG icons */
        mode?: 'sector' | 'type';
        /**
         * Legend placement strategy.
         * - 'auto' (default): legend on the right when wide, below when narrow (<400px)
         * - 'bottom': legend always below the pie (better for constrained-height panels)
         */
        legendPosition?: 'auto' | 'bottom';
        /** Currency code for absolute amount formatting */
        currency?: string;
    }

    let {data = [], height = '280px', mode = 'sector', legendPosition = 'auto', currency = 'EUR'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    const resizeWatcher = createResizeWatcher(() => {
        // Bugfix: chartInstance.resize() is required to make ECharts actually re-measure
        // the container and resize the underlying <canvas> pixel dimensions — setOption()
        // alone re-applies percentage-based geometry (pieCenter/pieRadius) against the
        // STALE canvas size from the last init()/resize(), so the chart appeared "frozen"
        // at the old size/position on window/panel resize (every sibling chart component
        // — GeographyMap, SemiDonutChart, LineChart, etc. — already calls resize() here).
        chartInstance?.resize();
        // Container size ALSO affects layout (pieCenter/pieRadius/legend orientation) which
        // the fast-path below skips — force a full rebuild so resizing actually
        // repositions the chart. Skip the enter/update animation for this specific
        // call: a live window drag-resize can fire the observer many times in rapid
        // succession, and animating every intermediate frame (800ms update transition)
        // would queue up and look janky. Data/dark-mode driven rebuilds still animate
        // smoothly as before.
        chartFullyInitialized = false;
        renderChart({skipAnimation: true});
    });
    let lastDark: boolean | null = null;
    let chartFullyInitialized = false;
    // Tracks the distinct set of raw type keys (mode='type') used to build richStyles
    // during the last FULL render — the fast-path data-only update below must NOT be
    // taken if the current data introduces a type not covered by that set, otherwise its
    // icon (and, previously, its translation via a since-removed name-based fallback)
    // would never be registered until some unrelated full rebuild (dark mode/resize).
    let lastRawTypeKeys = '';
    // Whether the last full build drew the two rings (D72). Switching layout changes the
    // number of series, and `setOption` merges series by index: going from three series
    // back to one would leave the two ring series of the old option on screen. Only that
    // transition asks ECharts to replace the series; every other rebuild merges as before.
    let lastRings = false;
    let needsInitialLayoutStabilityPass = false;

    // Diversified color palette — high chromatic distance
    const PALETTE_LIGHT = ['#1a4031', '#2563eb', '#7c3aed', '#dc2626', '#d97706', '#0d9488', '#be185d', '#4f46e5', '#059669', '#ea580c', '#6366f1', '#0891b2', '#ca8a04', '#9333ea'];
    const PALETTE_DARK = ['#4ade80', '#60a5fa', '#a78bfa', '#f87171', '#fbbf24', '#2dd4bf', '#f472b6', '#818cf8', '#34d399', '#fb923c', '#a5b4fc', '#22d3ee', '#facc15', '#c084fc'];

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        const observer = new MutationObserver(() => renderChart());
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            observer.disconnect();
            cleanup();
        };
    });

    $effect(() => {
        // Read every element synchronously so this effect tracks the CONTENT of
        // `data`, not merely the truthiness of the array reference: an array is
        // always truthy, so the previous `if (chartContainer && data)` guard never
        // re-fired when the parent rebuilt the slices. Same defect that made
        // SemiDonutChart render blank — see its $effect for the reference fix.
        void data.map((slice) => ({...slice}));

        if (chartContainer) {
            tick().then(() => {
                setupResizeObserver();
                renderChart();
            });
        }
    });

    function setupResizeObserver() {
        resizeWatcher.observe(chartContainer);
    }

    function cleanup() {
        resizeWatcher.disconnect();
        chartInstance?.dispose();
        chartInstance = null;
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart(opts: {skipAnimation?: boolean} = {}) {
        if (!chartContainer) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            attachChartReady(chartInstance, chartContainer, 'allocation-pie');
            // ECharts draws to a canvas, so a colour has no DOM an E2E could read.
            // Exposing the instance is the only way a test can assert that the
            // hierarchy actually reached the option — same hook, same name, as
            // PriceChartFull.svelte.
            (chartContainer as unknown as Record<string, unknown>).__lfChart = chartInstance;
            needsInitialLayoutStabilityPass = true;
        }

        const isDark = document.documentElement.classList.contains('dark');
        const tr = $t;
        const palette = isDark ? PALETTE_DARK : PALETTE_LIGHT;

        const entries = data.filter((e) => e.value > 0);
        if (entries.length === 0) return; // Keep old chart visible, don't clear

        // Build chart data with name for ECharts diffing
        const mappedEntries = entries.map((entry) => {
            let displayName: string;
            if (mode === 'sector') {
                const i18nKey = `sectors.${sectorI18nKey(entry.name)}`;
                const translated = tr(i18nKey) !== i18nKey ? tr(i18nKey) : entry.name.replace(/_/g, ' ');
                const emoji = entry.emoji ?? '';
                displayName = emoji ? `${emoji} ${translated}` : translated;
            } else {
                // Bugfix: namespace is plural "assets.types.X" (matches en.json) — the
                // singular "asset.types.X" key does not exist, so this translation was
                // silently failing and falling back to the raw untranslated type string.
                const typeKey = `assets.types.${entry.name.toUpperCase()}`;
                const translated = tr(typeKey);
                displayName = translated !== typeKey ? translated : entry.name;
            }
            return {name: displayName, value: entry.value, amount: entry.amount, rawName: entry.name, emoji: entry.emoji ?? ''};
        });

        // Asset-type subtypes sit inside their family, adjacent to it — ordering and
        // colour are one change, because two similar colours on opposite sides of the
        // circle read as an accident. The family is the **vehicle** (developer's
        // decision of 24/09/2026, R12 option B), as K's taxonomy files it
        // (`assetTypeFamily`): every ETF subtype belongs to ETF, real-estate
        // crowdfunding to Crowdfund.
        //
        // 'type' only, deliberately: the sector dimension has no taxonomy to fold,
        // and this same component draws the Asset Detail sector pie, which is out
        // of scope. With no subtypes present every group is a singleton, so the
        // order and the colours are identical to the plain value sort below.
        const hierarchy =
            mode === 'type'
                ? buildAllocationHierarchy(
                      mappedEntries.map((item) => ({key: item.rawName, weight: item.value, item})),
                      {resolvePrimary: assetTypeFamily, palette},
                  )
                : [];
        const chartData =
            mode === 'type'
                ? hierarchy.map(({item, color, primary, groupSize, primaryTotal}) => ({
                      ...item,
                      itemStyle: {color},
                      primaryKey: primary,
                      groupSize,
                      primaryTotal,
                  }))
                : mappedEntries.sort((a, b) => b.value - a.value);

        // D72: as soon as one family contains a subtype, the relation is drawn as a
        // second ring, separate from the first, instead of a shade (R12). With no
        // subtype on screen the layout says so, and the single legacy ring below is
        // drawn untouched.
        const layout = mode === 'type' ? buildAllocationRings(hierarchy, {weightOf: (item) => item.value}) : null;
        const rings = layout?.rings === true;

        const typeLabel = (key: string) => {
            const i18nKey = `assets.types.${key.toUpperCase()}`;
            const translated = tr(i18nKey);
            return translated !== i18nKey ? translated : key;
        };
        // Percentages arrive with two decimals; a family's sum must not surface as
        // 3.5299999%, and a member and its family are always shown at the same precision.
        const roundedPercent = (value: number) => Math.round(value * 100) / 100;
        const ringData = rings
            ? buildAllocationRingData(layout!, {
                  familyLabel: typeLabel,
                  memberLabel: (item) => item.name,
                  // $t, not the tr alias: the i18n audit only sees $t( and t( call sites.
                  genericCaption: (family) => $t('dashboard.allocationGeneric', {values: {type: family}}),
                  amountOf: (item) => item.amount ?? 0,
                  round: roundedPercent,
              })
            : null;
        const ringItem = ({color, ...datum}: AllocationRingDatum) => ({...datum, itemStyle: {color}});
        // An outer filler is empty space: invisible, silent, and without a border, or the
        // family it spans would show a seam and read as split.
        const transparentStyle = {color: 'transparent', borderWidth: 0};
        const baseRingData = ringData ? ringData.base.map(ringItem) : [];
        const outerRingData = ringData ? ringData.outer.map((datum) => (datum.filler ? {...ringItem(datum), itemStyle: transparentStyle, label: {show: false}, labelLine: {show: false}, emphasis: {disabled: true}, tooltip: {show: false}} : ringItem(datum))) : [];

        // Data-only update when chart is already initialized, dark mode hasn't changed,
        // AND (mode='type' only) no new asset type has appeared since the last full
        // build — a new type needs richStyles/legend/label formatters rebuilt so its
        // icon actually registers (see lastRawTypeKeys declaration above for why).
        const currentRawTypeKeys = mode === 'type' ? [...new Set(chartData.map((d) => d.rawName.toUpperCase()))].sort().join(',') + (rings ? '|rings' : '') : '';
        const sameTypeSet = mode !== 'type' || currentRawTypeKeys === lastRawTypeKeys;
        if (chartFullyInitialized && lastDark === isDark && sameTypeSet) {
            // Bugfix: preserve the FULL data item (not just {name, value}) — formatters
            // (tooltip especially) read params.data.rawName/amount, and stripping them
            // here silently broke the fallback path for any type whose translated name
            // does not equal its raw enum after uppercasing (e.g. IT/FR/ES "Crowdfunding" != "CROWDFUND").
            //
            // With two rings every series has to be refreshed, not the first one: a
            // `[{data}]` here would update the base ring and leave the outer one on the
            // previous numbers — stale arcs, no error, no symptom.
            chartInstance.setOption({
                series: rings
                    ? [
                          {id: 'alloc-base', data: baseRingData},
                          {id: 'alloc-outer', data: outerRingData},
                      ]
                    : [{data: chartData}],
            });
            return;
        }
        lastRawTypeKeys = currentRawTypeKeys;

        // Build ECharts rich-text image styles for type mode (one key per asset type)
        const richStyles: Record<string, any> = {};
        // Bugfix: legend formatter only receives the (already-translated) display name
        // string from ECharts, not the full data item — build a lookup back to the raw
        // backend type key (e.g. "CROWDFUND") so it can re-translate/find the icon
        // correctly instead of re-deriving a key from the translated name itself (which
        // produced a mismatched key for languages whose translation differs from the
        // enum, e.g. IT/FR/ES "Crowdfunding" -> "CROWDFUNDING" != "CROWDFUND").
        const rawKeyByName: Record<string, string> = {};
        if (mode === 'type') {
            for (const {name, rawName} of chartData) {
                const safeKey = `img_${rawName.toUpperCase().replace(/[^A-Z_]/g, '')}`;
                richStyles[safeKey] = {
                    backgroundColor: {image: getAssetTypeIconUrl(rawName)},
                    width: 16,
                    height: 16,
                    align: 'center',
                };
                rawKeyByName[name] = rawName.toUpperCase().replace(/[^A-Z_]/g, '');
            }
            // A family's base arc may name a type that is not in the data at all — a
            // lone `ETF_STOCK` is drawn under "Stock" — so its icon is registered too.
            for (const {name, rawName} of [...baseRingData, ...outerRingData]) {
                const rawKey = rawName.toUpperCase().replace(/[^A-Z_]/g, '');
                richStyles[`img_${rawKey}`] ??= {backgroundColor: {image: getAssetTypeIconUrl(rawName)}, width: 16, height: 16, align: 'center'};
                rawKeyByName[name] ??= rawKey;
            }
        }

        // Responsive: narrow containers → legend below the pie
        const containerWidth = chartContainer.getBoundingClientRect().width;
        const isNarrow = containerWidth < 400;
        const legendBelow = legendPosition === 'bottom' || isNarrow;

        // Legend — always scrollable to avoid 4+ unwrapped rows
        const legendBaseTextStyle: any = {color: isDark ? '#94a3b8' : '#64748b', fontSize: 11};
        const legendTextStyle = mode === 'type' ? {...legendBaseTextStyle, rich: richStyles} : legendBaseTextStyle;

        const legendTypeExtras =
            mode === 'type'
                ? {
                      formatter: (name: string) => {
                          // Bugfix: look up the raw key from the translated name (see
                          // rawKeyByName above) instead of re-deriving it from `name`
                          // itself, which is already translated and would produce a
                          // mismatched key. Defensive fallback for safety.
                          const rawKey = rawKeyByName[name] ?? name.toUpperCase().replace(/[^A-Z_]/g, '');
                          const safeKey = `img_${rawKey}`;
                          const translated = tr(`assets.types.${rawKey}`) || name;
                          return `{${safeKey}|} ${translated}`;
                      },
                      // With two rings the legend lists families only, and stays clickable:
                      // every arc of a family — inner and outer — carries the family's name,
                      // so a click hides all of them at once and the rings still sum alike.
                  }
                : {};

        const legendConfig: any = legendBelow
            ? {
                  ...legendTypeExtras,
                  type: 'scroll',
                  orient: 'horizontal',
                  bottom: 0,
                  left: 'center',
                  width: '95%',
                  textStyle: legendTextStyle,
                  pageTextStyle: {color: isDark ? '#94a3b8' : '#64748b', fontSize: 10},
                  pageIconColor: isDark ? '#94a3b8' : '#64748b',
                  pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
                  pageButtonGap: 4,
              }
            : {
                  ...legendTypeExtras,
                  type: 'scroll',
                  orient: 'vertical',
                  right: 10,
                  top: 20,
                  bottom: 20,
                  textStyle: legendTextStyle,
                  pageTextStyle: {color: isDark ? '#94a3b8' : '#64748b'},
                  pageIconColor: isDark ? '#94a3b8' : '#64748b',
                  pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
              };

        const pieCenter = legendBelow ? ['50%', '40%'] : ['35%', '50%'];
        const pieRadius = legendBelow ? ['25%', '55%'] : ['35%', '70%'];

        // Inner label — sector: emoji only (from data.emoji); type: PNG icon via rich text.
        const labelConfig: any =
            mode === 'sector'
                ? {
                      show: true,
                      position: 'inner',
                      // Show only the emoji (first token before the space in display name)
                      formatter: (params: any) => {
                          const first = (params.name as string).split(' ')[0];
                          // If it looks like an emoji (non-ASCII), use it; otherwise skip
                          return first && first.codePointAt(0)! > 127 ? first : '';
                      },
                      fontSize: 14,
                      backgroundColor: 'rgba(255, 255, 255, 0.75)',
                      borderRadius: 20,
                      padding: [4, 4],
                  }
                : {
                      show: true,
                      position: 'inner',
                      formatter: (params: any) => {
                          // Bugfix: use the raw backend type carried on the data item
                          // (params.data.rawName) instead of re-deriving a key from
                          // params.name (already translated — would produce a mismatched
                          // key for languages whose translation differs from the enum,
                          // e.g. IT/FR/ES "Crowdfunding" -> "CROWDFUNDING" != "CROWDFUND").
                          const rawSource = params.data?.rawName ?? params.name;
                          const rawKey = (rawSource as string).toUpperCase().replace(/[^A-Z_]/g, '');
                          return `{img_${rawKey}|}`;
                      },
                      rich: richStyles,
                      backgroundColor: 'rgba(255, 255, 255, 0.75)',
                      borderRadius: 20,
                      padding: [4, 4],
                  };

        // Build amount lookup by display name for tooltip
        const amountByName: Record<string, number> = {};
        for (const item of chartData) {
            amountByName[item.name] = item.amount;
        }

        // Tooltip — emoji + translated label + percentage + absolute amount (on new line)
        const tooltipFormatter = (params: any) => {
            // The data item carries its own amount. With two rings a family and its pure
            // member share a display name ("Bonds") but not an amount, so a lookup by
            // name would give the family's arc the member's figure or vice versa.
            const absAmount = typeof params.data?.amount === 'number' ? params.data.amount : amountByName[params.name];
            const amountLine = absAmount != null && absAmount > 0 ? `<br/><span style="font-size:11px;opacity:0.8">${escapeHtml(formatCurrencyAmountPlain(absAmount, currency, {showSign: false}))}</span>` : '';
            if (mode === 'type') {
                // Bugfix: same as above — use the raw backend type from the data item
                // rather than re-deriving from the already-translated params.name.
                const rawSource = params.data?.rawName ?? params.name;
                const rawKey = (rawSource as string).toUpperCase().replace(/[^A-Z_]/g, '');
                // On the rings the arc carries its own caption: "ETF azionario", or the
                // generic member of a split family, which must not read as the family.
                const translated = params.data?.caption ?? (tr(`assets.types.${rawKey}`) || params.name);
                // One icon, the type's own: a subtype's is K's composite, which already names
                // its vehicle and its content (the review of R12, 24/09/2026, asked for both).
                const iconUrl = getAssetTypeIconUrl(rawKey);
                const iconHtml = `<img src="${escapeHtml(iconUrl)}" style="width:14px;height:14px;vertical-align:middle;margin-right:5px;">`;
                // The shading says "this belongs to that mass"; this line says how big
                // the mass is. Only when there is actually a sibling — otherwise it
                // would restate the slice's own number.
                const groupSize: number = params.data?.groupSize ?? 1;
                const primaryKey: string | undefined = params.data?.primaryKey;
                // On the outer ring the family is the whole point, even as a family of
                // one. On the inner ring it would restate the arc's own number.
                const onOuterRing = params.data?.ringRole === 'member';
                const showParent = rings ? onOuterRing : groupSize > 1;
                let parentLine = '';
                if (showParent && primaryKey) {
                    const parentI18nKey = `assets.types.${primaryKey}`;
                    const parentTranslated = tr(parentI18nKey);
                    const parentLabel = parentTranslated !== parentI18nKey ? parentTranslated : primaryKey;
                    // Same precision as the member's own figure: two decimals beside one read
                    // as two different quantities (review of R12, 24/09/2026).
                    const parentTotal = roundedPercent(params.data?.primaryTotal ?? 0);
                    parentLine = `<br/><span style="font-size:11px;opacity:0.7">↳ ${parentLabel} ${parentTotal}%</span>`;
                }
                return `${iconHtml}${translated}: ${params.value}%${amountLine}${parentLine}`;
            }
            // Sector: display name already contains the emoji prefix
            return `${escapeHtml(String(params.name ?? ''))}: ${params.value}%${amountLine}`;
        };

        const option: echarts.EChartsOption = {
            ...CHART_ANIMATION_CONFIG,
            ...(opts.skipAnimation ? {animation: false} : {}),
            color: palette,
            tooltip: {
                trigger: 'item',
                formatter: tooltipFormatter,
                position: tooltipPositionAboveFinger,
                backgroundColor: isDark ? '#1e293b' : '#fff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
            },
            legend: legendConfig,
            series: rings
                ? ringSeries()
                : [
                      {
                          type: 'pie',
                          radius: pieRadius,
                          center: pieCenter,
                          avoidLabelOverlap: true,
                          padAngle: 1,
                          itemStyle: {
                              borderRadius: 4,
                              borderColor: isDark ? '#293548' : '#ffffff',
                              borderWidth: 2,
                          },
                          label: labelConfig,
                          labelLayout: {hideOverlap: true},
                          emphasis: {
                              // Tooltip is sufficient on hover — hide inner label instead of replacing it with text
                              label: {show: false},
                              scaleSize: 5,
                          },
                          labelLine: {show: false},
                          data: chartData,
                      },
                  ],
        };

        // The two rings of D72, as the developer chose them on 24/09/2026 (R12, option B):
        //
        // - `alloc-base`, the inner ring: one arc per family, with the family's icon;
        // - `alloc-outer`, a thinner ring **separated** from it by a visible gap: the
        //   members of the split families, each with a caption outside, and an invisible
        //   filler under every other family. A first version drew the outer band glued
        //   to the inner one to avoid a seam; from outside it read as one ring, and on a
        //   small slice the member's icon covered the band — rejected in review.
        //
        // No angular padding on either ring: `padAngle` removes one pad per arc, and the
        // rings do not have the same number of arcs — padded, they would drift apart. The
        // white border separates the slices instead, identically on both rings.
        function ringSeries(): echarts.PieSeriesOption[] {
            const [start, end] = pieRadius.map((value) => Number.parseFloat(value));
            const span = end - start;
            const innerEnd = `${start + span * 0.67}%`;
            const outerStart = `${start + span * 0.8}%`;
            const border = {borderRadius: 4, borderColor: isDark ? '#293548' : '#ffffff', borderWidth: 2};
            const shared = {type: 'pie' as const, center: pieCenter, avoidLabelOverlap: true, padAngle: 0, itemStyle: border, labelLayout: {hideOverlap: true}};
            const captionConfig = {
                show: true,
                position: 'outside' as const,
                formatter: (params: any) => `${params.data?.caption ?? params.name}\n${params.value}%`,
                fontSize: 11,
                lineHeight: 14,
                color: isDark ? '#cbd5e1' : '#374151',
            };
            return [
                // Family icons only where they fit: a 0.01% "Liquidity" arc would otherwise
                // wear an icon wider than itself, drawn across its neighbours. 18° is 5% of
                // the circle, the threshold of the mockup the developer approved.
                {...shared, id: 'alloc-base', radius: [pieRadius[0], innerEnd], label: labelConfig, labelLine: {show: false}, minShowLabelAngle: 18, emphasis: {label: {show: false}, scaleSize: 5}, data: baseRingData},
                {...shared, id: 'alloc-outer', radius: [outerStart, pieRadius[1]], label: captionConfig, labelLine: {show: true, length: 8, length2: 8}, emphasis: {scaleSize: 3}, data: outerRingData},
            ];
        }

        // Replace the series only when the layout switches between one ring and two:
        // merged by index, the old ring series would otherwise stay on screen.
        const layoutSwitched = mode === 'type' && rings !== lastRings;
        chartInstance.setOption(option, layoutSwitched ? {notMerge: false, replaceMerge: ['series']} : {notMerge: false});
        lastRings = mode === 'type' ? rings : false;
        chartFullyInitialized = true;
        lastDark = isDark;
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }
    }
</script>

<div bind:this={chartContainer} class="w-full" style="height: {height};"></div>
